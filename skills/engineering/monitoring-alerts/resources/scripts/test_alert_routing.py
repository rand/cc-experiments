#!/usr/bin/env python3
"""
Test Alert Routing and Escalation

This script tests alert routing through Alertmanager to verify that alerts
are routed to the correct receivers and escalation paths work as expected.

Usage:
    test_alert_routing.py --alertmanager http://localhost:9093
    test_alert_routing.py --alertmanager http://localhost:9093 --config alertmanager.yml
    test_alert_routing.py --alertmanager http://localhost:9093 --test-alert '{"alertname":"TestAlert","severity":"critical"}'
    test_alert_routing.py --alertmanager http://localhost:9093 --json
"""

import argparse
import sys
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
import yaml


class AlertRoutingTester:
    """Tests alert routing and escalation paths."""

    def __init__(self, alertmanager_url: str):
        self.alertmanager_url = alertmanager_url.rstrip('/')
        self.config = None

    def load_config(self, config_path: str) -> bool:
        """Load Alertmanager configuration."""
        try:
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
            return True
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return False

    def test_routing(self, alert_labels: Dict[str, str]) -> Dict[str, Any]:
        """Test routing for a given set of alert labels."""
        if not self.config:
            # Fetch config from Alertmanager API
            try:
                response = requests.get(f'{self.alertmanager_url}/api/v1/status')
                response.raise_for_status()
                data = response.json()
                self.config = data.get('data', {}).get('config', {})
            except Exception as e:
                return {'error': f'Failed to fetch config: {e}'}

        # Determine which receiver would handle this alert
        route = self.config.get('route', {})
        matched_route = self._match_route(alert_labels, route)

        return {
            'alert_labels': alert_labels,
            'matched_receiver': matched_route['receiver'],
            'route_path': matched_route['path'],
            'group_by': matched_route.get('group_by', []),
            'group_wait': matched_route.get('group_wait', 'default'),
            'group_interval': matched_route.get('group_interval', 'default'),
            'repeat_interval': matched_route.get('repeat_interval', 'default'),
            'receiver_config': self._get_receiver_config(matched_route['receiver'])
        }

    def _match_route(self, labels: Dict[str, str], route: Dict, path: List[str] = None) -> Dict:
        """Recursively match labels against routing tree."""
        if path is None:
            path = ['root']

        # Check if this route matches
        if 'match' in route:
            if not self._matches(labels, route['match']):
                return None

        if 'match_re' in route:
            if not self._matches_re(labels, route['match_re']):
                return None

        # Check child routes
        if 'routes' in route:
            for idx, child_route in enumerate(route['routes']):
                child_path = path + [f'routes[{idx}]']
                matched = self._match_route(labels, child_route, child_path)
                if matched:
                    # Check if we should continue to other routes
                    if not child_route.get('continue', False):
                        return matched

        # This route matches (or is the default)
        result = {
            'receiver': route.get('receiver', 'default'),
            'path': ' → '.join(path),
            'group_by': route.get('group_by'),
            'group_wait': route.get('group_wait'),
            'group_interval': route.get('group_interval'),
            'repeat_interval': route.get('repeat_interval')
        }

        return result

    def _matches(self, labels: Dict[str, str], matchers: Dict[str, str]) -> bool:
        """Check if labels match exact matchers."""
        for key, value in matchers.items():
            if labels.get(key) != value:
                return False
        return True

    def _matches_re(self, labels: Dict[str, str], matchers: Dict[str, str]) -> bool:
        """Check if labels match regex matchers."""
        import re
        for key, pattern in matchers.items():
            label_value = labels.get(key, '')
            if not re.match(pattern, label_value):
                return False
        return True

    def _get_receiver_config(self, receiver_name: str) -> Dict[str, Any]:
        """Get receiver configuration."""
        receivers = self.config.get('receivers', [])
        for receiver in receivers:
            if receiver.get('name') == receiver_name:
                # Sanitize sensitive data
                sanitized = receiver.copy()
                for config_type in ['pagerduty_configs', 'slack_configs', 'email_configs',
                                     'webhook_configs', 'opsgenie_configs']:
                    if config_type in sanitized:
                        for config in sanitized[config_type]:
                            # Mask sensitive fields
                            for key in ['service_key', 'api_key', 'api_url', 'auth_password',
                                        'auth_token', 'bearer_token']:
                                if key in config:
                                    config[key] = '***REDACTED***'
                return sanitized
        return {'error': f'Receiver "{receiver_name}" not found'}

    def send_test_alert(self, labels: Dict[str, str], annotations: Dict[str, str] = None) -> Dict[str, Any]:
        """Send a test alert to Alertmanager."""
        if annotations is None:
            annotations = {
                'summary': 'Test alert',
                'description': 'This is a test alert generated by test_alert_routing.py'
            }

        # Add test label
        labels['test'] = 'true'

        # Build alert payload
        alert = {
            'labels': labels,
            'annotations': annotations,
            'startsAt': datetime.utcnow().isoformat() + 'Z',
            'endsAt': (datetime.utcnow() + timedelta(minutes=5)).isoformat() + 'Z'
        }

        try:
            response = requests.post(
                f'{self.alertmanager_url}/api/v1/alerts',
                json=[alert],
                timeout=10
            )
            response.raise_for_status()

            # Wait a moment for processing
            time.sleep(2)

            # Query to see if alert was received
            status_response = requests.get(f'{self.alertmanager_url}/api/v1/alerts')
            status_response.raise_for_status()
            alerts_data = status_response.json()

            # Find our test alert
            received_alerts = alerts_data.get('data', [])
            test_alert = None
            for alert_item in received_alerts:
                if alert_item.get('labels', {}).get('test') == 'true':
                    if all(alert_item.get('labels', {}).get(k) == v for k, v in labels.items()):
                        test_alert = alert_item
                        break

            return {
                'sent': True,
                'received': test_alert is not None,
                'alert': test_alert,
                'receiver': test_alert.get('receivers', [{}])[0].get('name') if test_alert else None
            }

        except requests.RequestException as e:
            return {
                'sent': False,
                'error': str(e)
            }

    def test_inhibition(self, source_labels: Dict[str, str], target_labels: Dict[str, str]) -> Dict[str, Any]:
        """Test if source alert would inhibit target alert."""
        inhibit_rules = self.config.get('inhibit_rules', [])

        inhibited = False
        matching_rules = []

        for idx, rule in enumerate(inhibit_rules):
            # Check if source matches
            source_match = rule.get('source_match', {})
            source_match_re = rule.get('source_match_re', {})

            if source_match and not self._matches(source_labels, source_match):
                continue
            if source_match_re and not self._matches_re(source_labels, source_match_re):
                continue

            # Check if target matches
            target_match = rule.get('target_match', {})
            target_match_re = rule.get('target_match_re', {})

            if target_match and not self._matches(target_labels, target_match):
                continue
            if target_match_re and not self._matches_re(target_labels, target_match_re):
                continue

            # Check equal labels
            equal = rule.get('equal', [])
            if equal:
                if not all(source_labels.get(label) == target_labels.get(label) for label in equal):
                    continue

            # This rule matches
            inhibited = True
            matching_rules.append({
                'rule_index': idx,
                'source_match': source_match or source_match_re,
                'target_match': target_match or target_match_re,
                'equal': equal
            })

        return {
            'inhibited': inhibited,
            'matching_rules': matching_rules,
            'source_labels': source_labels,
            'target_labels': target_labels
        }

    def test_silences(self, labels: Dict[str, str]) -> Dict[str, Any]:
        """Check if alert with given labels would be silenced."""
        try:
            response = requests.get(f'{self.alertmanager_url}/api/v1/silences')
            response.raise_for_status()
            data = response.json()
            silences = data.get('data', [])

            matching_silences = []
            for silence in silences:
                if silence.get('status', {}).get('state') != 'active':
                    continue

                matchers = silence.get('matchers', [])
                matches = True

                for matcher in matchers:
                    name = matcher.get('name')
                    value = matcher.get('value')
                    is_regex = matcher.get('isRegex', False)

                    label_value = labels.get(name, '')

                    if is_regex:
                        import re
                        if not re.match(value, label_value):
                            matches = False
                            break
                    else:
                        if label_value != value:
                            matches = False
                            break

                if matches:
                    matching_silences.append({
                        'id': silence.get('id'),
                        'comment': silence.get('comment'),
                        'createdBy': silence.get('createdBy'),
                        'endsAt': silence.get('endsAt'),
                        'matchers': matchers
                    })

            return {
                'silenced': len(matching_silences) > 0,
                'matching_silences': matching_silences,
                'labels': labels
            }

        except Exception as e:
            return {'error': f'Failed to query silences: {e}'}

    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive routing tests."""
        test_cases = [
            {
                'name': 'Critical production alert',
                'labels': {'severity': 'critical', 'environment': 'production', 'service': 'api'}
            },
            {
                'name': 'Warning staging alert',
                'labels': {'severity': 'warning', 'environment': 'staging', 'service': 'api'}
            },
            {
                'name': 'Database team alert',
                'labels': {'severity': 'critical', 'team': 'database', 'service': 'postgres'}
            },
            {
                'name': 'Development environment alert',
                'labels': {'severity': 'warning', 'environment': 'dev', 'service': 'api'}
            }
        ]

        results = []
        for test_case in test_cases:
            routing = self.test_routing(test_case['labels'])
            silence = self.test_silences(test_case['labels'])

            results.append({
                'test_name': test_case['name'],
                'labels': test_case['labels'],
                'routing': routing,
                'silences': silence
            })

        return {
            'test_cases': results,
            'summary': {
                'total': len(results),
                'passed': sum(1 for r in results if 'error' not in r['routing'])
            }
        }


def print_results(results: Dict[str, Any], json_output: bool = False):
    """Print test results."""
    if json_output:
        print(json.dumps(results, indent=2))
        return

    # Human-readable output
    if 'test_cases' in results:
        # Comprehensive test results
        print(f"\n{'='*80}")
        print("ALERT ROUTING TEST RESULTS")
        print(f"{'='*80}")

        for test in results['test_cases']:
            print(f"\n{'-'*80}")
            print(f"Test: {test['test_name']}")
            print(f"{'-'*80}")

            print(f"\nLabels:")
            for key, value in test['labels'].items():
                print(f"  {key}: {value}")

            routing = test['routing']
            if 'error' in routing:
                print(f"\n✗ Error: {routing['error']}")
            else:
                print(f"\n✓ Routing:")
                print(f"  Receiver: {routing['matched_receiver']}")
                print(f"  Route path: {routing['route_path']}")
                print(f"  Group by: {routing.get('group_by', 'default')}")
                print(f"  Group wait: {routing.get('group_wait', 'default')}")
                print(f"  Repeat interval: {routing.get('repeat_interval', 'default')}")

                receiver_config = routing.get('receiver_config', {})
                if 'error' not in receiver_config:
                    print(f"\n  Receiver configuration:")
                    for config_type in receiver_config:
                        if config_type != 'name' and receiver_config[config_type]:
                            print(f"    {config_type}: {len(receiver_config[config_type])} config(s)")

            silence = test.get('silences', {})
            if silence.get('silenced'):
                print(f"\n⚠ Alert would be SILENCED:")
                for s in silence['matching_silences']:
                    print(f"  • Silence ID: {s['id']}")
                    print(f"    Comment: {s['comment']}")
                    print(f"    Created by: {s['createdBy']}")
            else:
                print(f"\n✓ Alert would NOT be silenced")

        print(f"\n{'='*80}")
        summary = results['summary']
        print(f"SUMMARY: {summary['passed']}/{summary['total']} tests passed")
        print(f"{'='*80}\n")

    elif 'matched_receiver' in results:
        # Single routing test
        print(f"\n{'='*80}")
        print("ROUTING TEST")
        print(f"{'='*80}")

        print(f"\nAlert labels:")
        for key, value in results['alert_labels'].items():
            print(f"  {key}: {value}")

        print(f"\nRouting result:")
        print(f"  ✓ Receiver: {results['matched_receiver']}")
        print(f"  Path: {results['route_path']}")
        print(f"  Group by: {results.get('group_by', 'default')}")
        print(f"  Repeat interval: {results.get('repeat_interval', 'default')}")

        receiver_config = results.get('receiver_config', {})
        if 'error' not in receiver_config:
            print(f"\nReceiver configuration:")
            print(f"  Name: {receiver_config.get('name')}")
            for config_type in receiver_config:
                if config_type != 'name' and receiver_config[config_type]:
                    print(f"  {config_type}: ✓ configured")

        print(f"\n{'='*80}\n")

    elif 'sent' in results:
        # Send test alert results
        print(f"\n{'='*80}")
        print("TEST ALERT")
        print(f"{'='*80}")

        if results['sent']:
            print(f"\n✓ Alert sent successfully")
            if results['received']:
                print(f"✓ Alert received by Alertmanager")
                print(f"  Routed to: {results.get('receiver')}")
            else:
                print(f"⚠ Alert not found in Alertmanager (may have been processed)")
        else:
            print(f"\n✗ Failed to send alert")
            print(f"  Error: {results.get('error')}")

        print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Test alert routing and escalation paths',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run comprehensive routing tests
  test_alert_routing.py --alertmanager http://localhost:9093

  # Test specific alert labels
  test_alert_routing.py --alertmanager http://localhost:9093 \\
    --labels '{"severity":"critical","service":"api"}'

  # Load config from file
  test_alert_routing.py --alertmanager http://localhost:9093 \\
    --config alertmanager.yml

  # Send test alert
  test_alert_routing.py --alertmanager http://localhost:9093 \\
    --send-test --labels '{"severity":"warning","service":"test"}'

  # Test inhibition
  test_alert_routing.py --alertmanager http://localhost:9093 \\
    --test-inhibition \\
    --source '{"alertname":"NodeDown","instance":"node1"}' \\
    --target '{"alertname":"HighCPU","instance":"node1"}'

  # JSON output
  test_alert_routing.py --alertmanager http://localhost:9093 --json
        """
    )

    parser.add_argument(
        '--alertmanager', '-a',
        required=True,
        help='Alertmanager URL (e.g., http://localhost:9093)'
    )

    parser.add_argument(
        '--config', '-c',
        help='Path to alertmanager.yml configuration file'
    )

    parser.add_argument(
        '--labels', '-l',
        help='Alert labels as JSON (e.g., \'{"severity":"critical"}\')'
    )

    parser.add_argument(
        '--send-test',
        action='store_true',
        help='Send a test alert'
    )

    parser.add_argument(
        '--test-inhibition',
        action='store_true',
        help='Test inhibition rules'
    )

    parser.add_argument(
        '--source',
        help='Source alert labels for inhibition test (JSON)'
    )

    parser.add_argument(
        '--target',
        help='Target alert labels for inhibition test (JSON)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Validate Alertmanager URL
    try:
        response = requests.get(f'{args.alertmanager}/api/v1/status', timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: Cannot connect to Alertmanager at {args.alertmanager}", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize tester
    tester = AlertRoutingTester(args.alertmanager)

    # Load config if provided
    if args.config:
        if not tester.load_config(args.config):
            sys.exit(1)

    try:
        # Test inhibition
        if args.test_inhibition:
            if not args.source or not args.target:
                parser.error('--test-inhibition requires both --source and --target')

            source_labels = json.loads(args.source)
            target_labels = json.loads(args.target)
            results = tester.test_inhibition(source_labels, target_labels)

        # Send test alert
        elif args.send_test:
            if not args.labels:
                parser.error('--send-test requires --labels')

            labels = json.loads(args.labels)
            results = tester.send_test_alert(labels)

        # Test routing for specific labels
        elif args.labels:
            labels = json.loads(args.labels)
            results = tester.test_routing(labels)

        # Run comprehensive tests
        else:
            results = tester.run_comprehensive_tests()

        print_results(results, json_output=args.json)

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in labels: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error during testing: {e}", file=sys.stderr)
        if args.json:
            print(json.dumps({'error': str(e)}))
        sys.exit(1)


if __name__ == '__main__':
    main()
