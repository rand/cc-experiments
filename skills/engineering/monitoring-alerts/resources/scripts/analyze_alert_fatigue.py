#!/usr/bin/env python3
"""
Analyze Alert Fatigue

This script analyzes alert frequency, flapping, and actionability to identify
and prevent alert fatigue.

Usage:
    analyze_alert_fatigue.py --prometheus http://localhost:9090
    analyze_alert_fatigue.py --prometheus http://localhost:9090 --days 7
    analyze_alert_fatigue.py --prometheus http://localhost:9090 --json
    analyze_alert_fatigue.py --prometheus http://localhost:9090 --threshold 10
"""

import argparse
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from collections import defaultdict


class AlertFatigueAnalyzer:
    """Analyzes alert patterns to identify alert fatigue."""

    def __init__(self, prometheus_url: str, days: int = 7):
        self.prometheus_url = prometheus_url.rstrip('/')
        self.days = days
        self.now = datetime.now()
        self.start_time = self.now - timedelta(days=days)

    def analyze(self) -> Dict[str, Any]:
        """Run complete alert fatigue analysis."""
        return {
            'analysis_period': {
                'days': self.days,
                'start': self.start_time.isoformat(),
                'end': self.now.isoformat()
            },
            'alert_frequency': self._analyze_frequency(),
            'alert_flapping': self._analyze_flapping(),
            'alert_duration': self._analyze_duration(),
            'notification_load': self._analyze_notification_load(),
            'recommendations': self._generate_recommendations()
        }

    def _query_prometheus(self, query: str, time: Optional[str] = None) -> Dict:
        """Execute Prometheus query."""
        try:
            endpoint = f'{self.prometheus_url}/api/v1/query'
            params = {'query': query}
            if time:
                params['time'] = time

            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f'Failed to query Prometheus: {e}')

    def _query_range(self, query: str, start: str, end: str, step: str = '1h') -> Dict:
        """Execute Prometheus range query."""
        try:
            endpoint = f'{self.prometheus_url}/api/v1/query_range'
            params = {
                'query': query,
                'start': start,
                'end': end,
                'step': step
            }

            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f'Failed to query Prometheus: {e}')

    def _analyze_frequency(self) -> Dict[str, Any]:
        """Analyze alert firing frequency."""
        # Query for alerts that fired in the analysis period
        query = f'count_over_time(ALERTS{{alertstate="firing"}}[{self.days}d])'

        result = self._query_prometheus(query)
        if result.get('status') != 'success':
            return {'error': 'Failed to query alert frequency'}

        data = result.get('data', {}).get('result', [])

        alerts = []
        for item in data:
            metric = item.get('metric', {})
            value = float(item.get('value', [0, 0])[1])

            alerts.append({
                'alertname': metric.get('alertname', 'unknown'),
                'severity': metric.get('severity', 'unknown'),
                'service': metric.get('service', 'unknown'),
                'fire_count': int(value),
                'avg_per_day': round(value / self.days, 2)
            })

        # Sort by frequency
        alerts.sort(key=lambda x: x['fire_count'], reverse=True)

        # Categorize
        high_frequency = [a for a in alerts if a['avg_per_day'] > 10]
        medium_frequency = [a for a in alerts if 1 < a['avg_per_day'] <= 10]
        low_frequency = [a for a in alerts if a['avg_per_day'] <= 1]

        return {
            'total_alerts': len(alerts),
            'high_frequency': high_frequency[:10],  # Top 10
            'medium_frequency_count': len(medium_frequency),
            'low_frequency_count': len(low_frequency),
            'summary': {
                'high': len(high_frequency),
                'medium': len(medium_frequency),
                'low': len(low_frequency)
            }
        }

    def _analyze_flapping(self) -> Dict[str, Any]:
        """Analyze alert flapping (rapid firing/resolving cycles)."""
        # Query for alerts that changed state frequently
        query = f'changes(ALERTS[{self.days}d]) > 5'

        result = self._query_prometheus(query)
        if result.get('status') != 'success':
            return {'error': 'Failed to query alert flapping'}

        data = result.get('data', {}).get('result', [])

        flapping_alerts = []
        for item in data:
            metric = item.get('metric', {})
            changes = float(item.get('value', [0, 0])[1])

            # Query for more details
            alertname = metric.get('alertname', 'unknown')
            instance = metric.get('instance', 'unknown')

            flapping_alerts.append({
                'alertname': alertname,
                'instance': instance,
                'severity': metric.get('severity', 'unknown'),
                'state_changes': int(changes),
                'avg_changes_per_day': round(changes / self.days, 2)
            })

        # Sort by change frequency
        flapping_alerts.sort(key=lambda x: x['state_changes'], reverse=True)

        return {
            'flapping_alerts': flapping_alerts[:20],  # Top 20
            'total_flapping': len(flapping_alerts),
            'severity': {
                'critical': len([a for a in flapping_alerts if a['severity'] == 'critical']),
                'warning': len([a for a in flapping_alerts if a['severity'] == 'warning']),
                'info': len([a for a in flapping_alerts if a['severity'] == 'info'])
            }
        }

    def _analyze_duration(self) -> Dict[str, Any]:
        """Analyze alert duration patterns."""
        # Query for currently firing alerts and their duration
        query = 'time() - ALERTS_FOR_STATE'

        result = self._query_prometheus(query)
        if result.get('status') != 'success':
            return {'error': 'Failed to query alert duration'}

        data = result.get('data', {}).get('result', [])

        durations = []
        for item in data:
            metric = item.get('metric', {})
            duration_seconds = float(item.get('value', [0, 0])[1])

            durations.append({
                'alertname': metric.get('alertname', 'unknown'),
                'instance': metric.get('instance', 'unknown'),
                'severity': metric.get('severity', 'unknown'),
                'duration_seconds': int(duration_seconds),
                'duration_hours': round(duration_seconds / 3600, 2)
            })

        # Categorize by duration
        short_lived = [d for d in durations if d['duration_hours'] < 1]
        medium_lived = [d for d in durations if 1 <= d['duration_hours'] < 24]
        long_lived = [d for d in durations if d['duration_hours'] >= 24]

        # Sort long-lived alerts
        long_lived.sort(key=lambda x: x['duration_hours'], reverse=True)

        return {
            'currently_firing': len(durations),
            'duration_distribution': {
                'short_lived': len(short_lived),  # < 1h
                'medium_lived': len(medium_lived),  # 1-24h
                'long_lived': len(long_lived)  # > 24h
            },
            'long_lived_alerts': long_lived[:10],  # Top 10 longest
            'avg_duration_hours': round(
                sum(d['duration_hours'] for d in durations) / len(durations), 2
            ) if durations else 0
        }

    def _analyze_notification_load(self) -> Dict[str, Any]:
        """Analyze notification load and patterns."""
        # Query Alertmanager metrics if available
        queries = {
            'notifications_sent': f'sum(increase(alertmanager_notifications_total[{self.days}d])) by (integration)',
            'notifications_failed': f'sum(increase(alertmanager_notifications_failed_total[{self.days}d])) by (integration)',
            'alerts_received': f'sum(increase(alertmanager_alerts_received_total[{self.days}d]))',
            'silences_active': 'alertmanager_silences{state="active"}'
        }

        results = {}
        for name, query in queries.items():
            result = self._query_prometheus(query)
            if result.get('status') == 'success':
                data = result.get('data', {}).get('result', [])
                results[name] = data

        # Process notifications by integration
        notifications_by_integration = []
        if 'notifications_sent' in results:
            for item in results['notifications_sent']:
                integration = item.get('metric', {}).get('integration', 'unknown')
                count = float(item.get('value', [0, 0])[1])
                notifications_by_integration.append({
                    'integration': integration,
                    'notifications': int(count),
                    'avg_per_day': round(count / self.days, 2)
                })

        # Calculate failure rate
        notification_health = []
        if 'notifications_sent' in results and 'notifications_failed' in results:
            sent_by_integration = {
                item['metric']['integration']: float(item['value'][1])
                for item in results['notifications_sent']
            }
            failed_by_integration = {
                item['metric']['integration']: float(item['value'][1])
                for item in results['notifications_failed']
            }

            for integration, sent in sent_by_integration.items():
                failed = failed_by_integration.get(integration, 0)
                total = sent + failed
                failure_rate = (failed / total * 100) if total > 0 else 0

                notification_health.append({
                    'integration': integration,
                    'sent': int(sent),
                    'failed': int(failed),
                    'failure_rate': round(failure_rate, 2)
                })

        # Total alerts received
        total_alerts = 0
        if 'alerts_received' in results and results['alerts_received']:
            total_alerts = int(float(results['alerts_received'][0].get('value', [0, 0])[1]))

        # Active silences
        active_silences = 0
        if 'silences_active' in results:
            active_silences = len(results['silences_active'])

        return {
            'total_alerts_received': total_alerts,
            'avg_alerts_per_day': round(total_alerts / self.days, 2),
            'notifications_by_integration': notifications_by_integration,
            'notification_health': notification_health,
            'active_silences': active_silences
        }

    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate recommendations based on analysis."""
        recommendations = []

        # Get current data for analysis
        frequency = self._analyze_frequency()
        flapping = self._analyze_flapping()
        duration = self._analyze_duration()

        # High frequency alerts
        high_freq = frequency.get('high_frequency', [])
        if high_freq:
            recommendations.append({
                'severity': 'high',
                'category': 'alert_frequency',
                'issue': f'{len(high_freq)} alerts fire > 10 times per day',
                'impact': 'Alert fatigue, important alerts may be missed',
                'recommendation': 'Increase alert thresholds or "for" duration for high-frequency alerts',
                'alerts': [a['alertname'] for a in high_freq[:5]]
            })

        # Flapping alerts
        flapping_count = flapping.get('total_flapping', 0)
        if flapping_count > 0:
            flapping_alerts = flapping.get('flapping_alerts', [])
            recommendations.append({
                'severity': 'high',
                'category': 'alert_flapping',
                'issue': f'{flapping_count} alerts are flapping (rapid state changes)',
                'impact': 'Notification spam, alert fatigue',
                'recommendation': 'Add or increase "for" duration, adjust thresholds, or use recording rules',
                'alerts': [a['alertname'] for a in flapping_alerts[:5]]
            })

        # Long-lived alerts
        long_lived = duration.get('long_lived_alerts', [])
        if long_lived:
            recommendations.append({
                'severity': 'medium',
                'category': 'alert_duration',
                'issue': f'{len(long_lived)} alerts have been firing for > 24 hours',
                'impact': 'Either not actionable or action not being taken',
                'recommendation': 'Review if alerts are actionable, if not remove or reduce severity',
                'alerts': [a['alertname'] for a in long_lived[:5]]
            })

        # Notification failures
        try:
            notification_load = self._analyze_notification_load()
            notification_health = notification_load.get('notification_health', [])
            failing = [n for n in notification_health if n['failure_rate'] > 10]

            if failing:
                recommendations.append({
                    'severity': 'high',
                    'category': 'notification_reliability',
                    'issue': f'{len(failing)} notification channels have > 10% failure rate',
                    'impact': 'Alerts not reaching oncall, incidents may go unnoticed',
                    'recommendation': 'Fix notification channel configuration or credentials',
                    'integrations': [n['integration'] for n in failing]
                })
        except:
            pass

        # No recommendations
        if not recommendations:
            recommendations.append({
                'severity': 'info',
                'category': 'overall',
                'issue': 'No major alert fatigue issues detected',
                'impact': 'N/A',
                'recommendation': 'Continue monitoring alert patterns and review monthly'
            })

        return recommendations


def print_results(analysis: Dict[str, Any], json_output: bool = False):
    """Print analysis results."""
    if json_output:
        print(json.dumps(analysis, indent=2))
        return

    # Human-readable output
    print(f"\n{'='*80}")
    print("ALERT FATIGUE ANALYSIS")
    print(f"{'='*80}")

    period = analysis['analysis_period']
    print(f"\nAnalysis Period: {period['days']} days")
    print(f"From: {period['start']}")
    print(f"To:   {period['end']}")

    # Frequency
    print(f"\n{'-'*80}")
    print("ALERT FREQUENCY")
    print(f"{'-'*80}")

    freq = analysis['alert_frequency']
    if 'error' in freq:
        print(f"Error: {freq['error']}")
    else:
        summary = freq['summary']
        print(f"\nTotal unique alerts: {freq['total_alerts']}")
        print(f"  High frequency (>10/day):   {summary['high']}")
        print(f"  Medium frequency (1-10/day): {summary['medium']}")
        print(f"  Low frequency (<1/day):      {summary['low']}")

        if freq['high_frequency']:
            print(f"\nTop High-Frequency Alerts:")
            for alert in freq['high_frequency'][:5]:
                print(f"  • {alert['alertname']}")
                print(f"    Fired {alert['fire_count']} times ({alert['avg_per_day']}/day)")
                print(f"    Severity: {alert['severity']}, Service: {alert['service']}")

    # Flapping
    print(f"\n{'-'*80}")
    print("ALERT FLAPPING")
    print(f"{'-'*80}")

    flap = analysis['alert_flapping']
    if 'error' in flap:
        print(f"Error: {flap['error']}")
    else:
        print(f"\nTotal flapping alerts: {flap['total_flapping']}")
        print(f"  Critical: {flap['severity']['critical']}")
        print(f"  Warning:  {flap['severity']['warning']}")
        print(f"  Info:     {flap['severity']['info']}")

        if flap['flapping_alerts']:
            print(f"\nTop Flapping Alerts:")
            for alert in flap['flapping_alerts'][:5]:
                print(f"  • {alert['alertname']} ({alert['instance']})")
                print(f"    State changes: {alert['state_changes']} ({alert['avg_changes_per_day']}/day)")

    # Duration
    print(f"\n{'-'*80}")
    print("ALERT DURATION")
    print(f"{'-'*80}")

    dur = analysis['alert_duration']
    if 'error' in dur:
        print(f"Error: {dur['error']}")
    else:
        print(f"\nCurrently firing: {dur['currently_firing']} alerts")
        dist = dur['duration_distribution']
        print(f"  Short-lived (<1h):   {dist['short_lived']}")
        print(f"  Medium-lived (1-24h): {dist['medium_lived']}")
        print(f"  Long-lived (>24h):    {dist['long_lived']}")

        if dur['long_lived_alerts']:
            print(f"\nLongest Running Alerts:")
            for alert in dur['long_lived_alerts'][:5]:
                print(f"  • {alert['alertname']} ({alert['instance']})")
                print(f"    Duration: {alert['duration_hours']} hours")

    # Notifications
    print(f"\n{'-'*80}")
    print("NOTIFICATION LOAD")
    print(f"{'-'*80}")

    notif = analysis['notification_load']
    print(f"\nTotal alerts received: {notif['total_alerts_received']}")
    print(f"Average per day: {notif['avg_alerts_per_day']}")
    print(f"Active silences: {notif['active_silences']}")

    if notif['notifications_by_integration']:
        print(f"\nNotifications by Integration:")
        for n in notif['notifications_by_integration']:
            print(f"  • {n['integration']}: {n['notifications']} ({n['avg_per_day']}/day)")

    if notif['notification_health']:
        print(f"\nNotification Health:")
        for n in notif['notification_health']:
            status = "✓" if n['failure_rate'] < 1 else "⚠" if n['failure_rate'] < 10 else "✗"
            print(f"  {status} {n['integration']}: {n['sent']} sent, {n['failed']} failed ({n['failure_rate']}%)")

    # Recommendations
    print(f"\n{'-'*80}")
    print("RECOMMENDATIONS")
    print(f"{'-'*80}")

    for i, rec in enumerate(analysis['recommendations'], 1):
        severity_icon = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢',
            'info': 'ℹ️'
        }.get(rec['severity'], '•')

        print(f"\n{i}. {severity_icon} [{rec['severity'].upper()}] {rec['category']}")
        print(f"   Issue: {rec['issue']}")
        print(f"   Impact: {rec['impact']}")
        print(f"   Recommendation: {rec['recommendation']}")

        if 'alerts' in rec:
            print(f"   Affected alerts: {', '.join(rec['alerts'])}")
        if 'integrations' in rec:
            print(f"   Affected integrations: {', '.join(rec['integrations'])}")

    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze alert fatigue patterns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze last 7 days
  analyze_alert_fatigue.py --prometheus http://localhost:9090

  # Analyze last 30 days
  analyze_alert_fatigue.py --prometheus http://localhost:9090 --days 30

  # JSON output
  analyze_alert_fatigue.py --prometheus http://localhost:9090 --json

  # Custom thresholds
  analyze_alert_fatigue.py --prometheus http://localhost:9090 --threshold 5
        """
    )

    parser.add_argument(
        '--prometheus', '-p',
        required=True,
        help='Prometheus URL (e.g., http://localhost:9090)'
    )

    parser.add_argument(
        '--days', '-d',
        type=int,
        default=7,
        help='Number of days to analyze (default: 7)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    parser.add_argument(
        '--threshold',
        type=int,
        default=10,
        help='High frequency threshold (alerts per day, default: 10)'
    )

    args = parser.parse_args()

    # Validate Prometheus URL
    try:
        response = requests.get(f'{args.prometheus}/api/v1/status/config', timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: Cannot connect to Prometheus at {args.prometheus}", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)

    # Run analysis
    try:
        analyzer = AlertFatigueAnalyzer(args.prometheus, args.days)
        analysis = analyzer.analyze()
        print_results(analysis, json_output=args.json)
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        if args.json:
            print(json.dumps({'error': str(e)}))
        sys.exit(1)


if __name__ == '__main__':
    main()
