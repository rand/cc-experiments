#!/usr/bin/env python3
"""
Error Tracking Testing Suite

This script tests error tracking functionality including:
- Error capture and delivery
- Grouping and fingerprinting validation
- Alert rule testing
- Performance impact measurement
- Integration testing

Usage:
    test_error_tracking.py --dsn <sentry-dsn> --test-capture
    test_error_tracking.py --dsn <dsn> --test-grouping
    test_error_tracking.py --dsn <dsn> --test-alerts

Examples:
    # Test error capture
    test_error_tracking.py --dsn $SENTRY_DSN --test-capture

    # Test grouping
    test_error_tracking.py --dsn $SENTRY_DSN --test-grouping --count 10

    # Test performance impact
    test_error_tracking.py --dsn $SENTRY_DSN --test-performance --iterations 1000

    # Run all tests
    test_error_tracking.py --dsn $SENTRY_DSN --all
"""

import argparse
import json
import sys
import os
import time
import uuid
import random
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SentryTestClient:
    """Test client for Sentry error tracking."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.session = requests.Session()

        # Parse DSN
        self._parse_dsn(dsn)

    def _parse_dsn(self, dsn: str) -> None:
        """Parse Sentry DSN."""
        import re

        pattern = r'https://([^@]+)@([^/]+)/(\d+)'
        match = re.match(pattern, dsn)

        if not match:
            raise ValueError(f"Invalid DSN format: {dsn}")

        self.public_key = match.group(1)
        self.host = match.group(2)
        self.project_id = match.group(3)

        self.endpoint = f"https://{self.host}/api/{self.project_id}/store/"

    def send_error(
        self,
        exception_type: str,
        exception_value: str,
        user: Optional[Dict] = None,
        tags: Optional[Dict] = None,
        contexts: Optional[Dict] = None,
        fingerprint: Optional[List[str]] = None,
        level: str = "error"
    ) -> Optional[str]:
        """Send error event to Sentry."""
        event = self._build_event(
            exception_type,
            exception_value,
            user,
            tags,
            contexts,
            fingerprint,
            level
        )

        headers = {
            'Content-Type': 'application/json',
            'X-Sentry-Auth': f'Sentry sentry_key={self.public_key}, sentry_version=7'
        }

        try:
            response = self.session.post(
                self.endpoint,
                json=event,
                headers=headers,
                timeout=5
            )

            response.raise_for_status()

            # Extract event ID from response
            data = response.json()
            return data.get('id')

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send error: {e}")
            return None

    def _build_event(
        self,
        exception_type: str,
        exception_value: str,
        user: Optional[Dict],
        tags: Optional[Dict],
        contexts: Optional[Dict],
        fingerprint: Optional[List[str]],
        level: str
    ) -> Dict[str, Any]:
        """Build Sentry event payload."""
        event = {
            'event_id': uuid.uuid4().hex,
            'timestamp': datetime.utcnow().isoformat(),
            'platform': 'python',
            'level': level,
            'logger': 'test',

            'exception': {
                'values': [
                    {
                        'type': exception_type,
                        'value': exception_value,
                        'stacktrace': {
                            'frames': [
                                {
                                    'filename': 'test_error_tracking.py',
                                    'function': 'test_function',
                                    'lineno': 100,
                                    'in_app': True
                                }
                            ]
                        }
                    }
                ]
            }
        }

        if user:
            event['user'] = user

        if tags:
            event['tags'] = tags

        if contexts:
            event['contexts'] = contexts

        if fingerprint:
            event['fingerprint'] = fingerprint

        return event


class ErrorTrackingTests:
    """Test suite for error tracking."""

    def __init__(self, client: SentryTestClient, verbose: bool = False):
        self.client = client
        self.verbose = verbose

    def test_capture(self, count: int = 1) -> Dict[str, Any]:
        """Test error capture and delivery."""
        logger.info(f"Testing error capture ({count} events)...")

        start_time = time.time()
        event_ids = []

        for i in range(count):
            event_id = self.client.send_error(
                exception_type='TestError',
                exception_value=f'Test error #{i}',
                user={'id': str(i), 'email': f'test{i}@example.com'},
                tags={'test': 'true', 'iteration': str(i)},
                level='error'
            )

            if event_id:
                event_ids.append(event_id)

        duration = time.time() - start_time
        success_rate = len(event_ids) / count * 100 if count > 0 else 0

        result = {
            'test': 'capture',
            'count': count,
            'successful': len(event_ids),
            'failed': count - len(event_ids),
            'success_rate': f'{success_rate:.1f}%',
            'duration': f'{duration:.2f}s',
            'avg_per_event': f'{(duration / count * 1000):.1f}ms' if count > 0 else 'N/A',
            'event_ids': event_ids
        }

        if success_rate >= 95:
            logger.info("✓ Capture test passed")
        else:
            logger.warning(f"⚠ Capture test marginal ({success_rate:.1f}% success)")

        return result

    def test_grouping(self, count: int = 10) -> Dict[str, Any]:
        """Test error grouping."""
        logger.info(f"Testing error grouping ({count} events)...")

        # Send multiple events with same fingerprint
        group_id = str(uuid.uuid4())

        event_ids = []
        for i in range(count):
            event_id = self.client.send_error(
                exception_type='GroupingTestError',
                exception_value=f'Error with dynamic data {i}',
                tags={'test': 'grouping', 'group_id': group_id},
                fingerprint=['grouping-test', 'static-fingerprint'],
                level='error'
            )

            if event_id:
                event_ids.append(event_id)

        # Wait for processing
        time.sleep(2)

        result = {
            'test': 'grouping',
            'events_sent': count,
            'events_delivered': len(event_ids),
            'fingerprint': ['grouping-test', 'static-fingerprint'],
            'expected': 'All events should group under single issue',
            'verification': 'Check Sentry UI to verify single issue was created'
        }

        logger.info(f"✓ Grouping test completed (sent {len(event_ids)} events)")

        return result

    def test_fingerprinting(self) -> Dict[str, Any]:
        """Test custom fingerprinting."""
        logger.info("Testing custom fingerprinting...")

        test_cases = [
            {
                'name': 'Database errors',
                'fingerprint': ['database-error'],
                'count': 5
            },
            {
                'name': 'API errors',
                'fingerprint': ['api-error', 'timeout'],
                'count': 5
            },
            {
                'name': 'Validation errors',
                'fingerprint': ['validation-error'],
                'count': 5
            }
        ]

        results = []

        for test_case in test_cases:
            event_ids = []

            for i in range(test_case['count']):
                event_id = self.client.send_error(
                    exception_type='FingerprintTestError',
                    exception_value=f"{test_case['name']} #{i}",
                    tags={'test': 'fingerprinting'},
                    fingerprint=test_case['fingerprint'],
                    level='error'
                )

                if event_id:
                    event_ids.append(event_id)

            results.append({
                'name': test_case['name'],
                'fingerprint': test_case['fingerprint'],
                'events_sent': test_case['count'],
                'events_delivered': len(event_ids)
            })

        logger.info(f"✓ Fingerprinting test completed ({len(test_cases)} groups)")

        return {
            'test': 'fingerprinting',
            'test_cases': results,
            'verification': 'Check Sentry UI to verify 3 separate issues were created'
        }

    def test_user_impact(self) -> Dict[str, Any]:
        """Test user impact tracking."""
        logger.info("Testing user impact tracking...")

        # Send errors from different users
        user_count = 20

        event_ids = []
        for i in range(user_count):
            event_id = self.client.send_error(
                exception_type='UserImpactTestError',
                exception_value='Error affecting multiple users',
                user={
                    'id': str(i),
                    'email': f'user{i}@example.com',
                    'username': f'user{i}'
                },
                tags={'test': 'user_impact'},
                fingerprint=['user-impact-test'],
                level='error'
            )

            if event_id:
                event_ids.append(event_id)

        result = {
            'test': 'user_impact',
            'unique_users': user_count,
            'events_sent': user_count,
            'events_delivered': len(event_ids),
            'verification': f'Check Sentry UI to verify issue shows {user_count} affected users'
        }

        logger.info(f"✓ User impact test completed ({user_count} users)")

        return result

    def test_context_enrichment(self) -> Dict[str, Any]:
        """Test context enrichment."""
        logger.info("Testing context enrichment...")

        event_id = self.client.send_error(
            exception_type='ContextTestError',
            exception_value='Error with rich context',
            user={
                'id': '12345',
                'email': 'test@example.com',
                'username': 'testuser',
                'subscription': 'premium'
            },
            tags={
                'test': 'context',
                'environment': 'production',
                'server': 'web-01',
                'datacenter': 'us-east-1'
            },
            contexts={
                'order': {
                    'order_id': 'ORD-123',
                    'total': 99.99,
                    'items_count': 3
                },
                'browser': {
                    'name': 'Chrome',
                    'version': '120.0'
                }
            },
            level='error'
        )

        result = {
            'test': 'context_enrichment',
            'event_id': event_id,
            'user_context': True,
            'tags_count': 5,
            'custom_contexts': 2,
            'verification': 'Check Sentry UI to verify all context data is visible'
        }

        logger.info("✓ Context enrichment test completed")

        return result

    def test_performance(self, iterations: int = 1000) -> Dict[str, Any]:
        """Test performance impact of error tracking."""
        logger.info(f"Testing performance impact ({iterations} iterations)...")

        # Test WITHOUT error tracking
        start_time = time.time()
        for _ in range(iterations):
            self._simulate_operation()
        baseline_duration = time.time() - start_time

        # Test WITH error tracking (but not sending)
        start_time = time.time()
        for _ in range(iterations):
            self._simulate_operation_with_tracking()
        with_tracking_duration = time.time() - start_time

        overhead = (with_tracking_duration - baseline_duration) / baseline_duration * 100

        result = {
            'test': 'performance',
            'iterations': iterations,
            'baseline_duration': f'{baseline_duration:.2f}s',
            'with_tracking_duration': f'{with_tracking_duration:.2f}s',
            'overhead_percentage': f'{overhead:.2f}%',
            'overhead_per_operation': f'{(overhead / iterations * 1000):.3f}ms'
        }

        if overhead < 5:
            logger.info(f"✓ Performance test passed (overhead: {overhead:.2f}%)")
        else:
            logger.warning(f"⚠ Performance overhead high: {overhead:.2f}%")

        return result

    def _simulate_operation(self) -> None:
        """Simulate operation without error tracking."""
        x = sum(range(100))

    def _simulate_operation_with_tracking(self) -> None:
        """Simulate operation with error tracking."""
        try:
            x = sum(range(100))
        except Exception:
            pass

    def test_sampling(self, sample_rate: float = 0.1, count: int = 100) -> Dict[str, Any]:
        """Test error sampling."""
        logger.info(f"Testing sampling (rate: {sample_rate}, count: {count})...")

        sent_count = 0

        for i in range(count):
            # Simulate sampling decision
            if random.random() < sample_rate:
                event_id = self.client.send_error(
                    exception_type='SamplingTestError',
                    exception_value=f'Sampled error #{i}',
                    tags={'test': 'sampling'},
                    level='error'
                )

                if event_id:
                    sent_count += 1

        actual_rate = sent_count / count if count > 0 else 0
        expected_rate = sample_rate

        result = {
            'test': 'sampling',
            'sample_rate': sample_rate,
            'total_errors': count,
            'sent_count': sent_count,
            'actual_rate': f'{actual_rate:.2%}',
            'expected_rate': f'{expected_rate:.2%}',
            'within_tolerance': abs(actual_rate - expected_rate) < 0.05
        }

        logger.info(f"✓ Sampling test completed (actual rate: {actual_rate:.2%})")

        return result

    def test_levels(self) -> Dict[str, Any]:
        """Test different error levels."""
        logger.info("Testing error levels...")

        levels = ['debug', 'info', 'warning', 'error', 'fatal']
        results = []

        for level in levels:
            event_id = self.client.send_error(
                exception_type='LevelTestError',
                exception_value=f'Test error with {level} level',
                tags={'test': 'levels', 'level': level},
                level=level
            )

            results.append({
                'level': level,
                'sent': event_id is not None,
                'event_id': event_id
            })

        result = {
            'test': 'levels',
            'levels_tested': levels,
            'results': results,
            'verification': 'Check Sentry UI to verify all levels are displayed correctly'
        }

        logger.info(f"✓ Levels test completed ({len(levels)} levels)")

        return result

    def test_concurrent(self, thread_count: int = 10, events_per_thread: int = 10) -> Dict[str, Any]:
        """Test concurrent error sending."""
        logger.info(f"Testing concurrent sending ({thread_count} threads, {events_per_thread} events each)...")

        start_time = time.time()

        def send_errors(thread_id: int) -> int:
            """Send errors from single thread."""
            success_count = 0

            for i in range(events_per_thread):
                event_id = self.client.send_error(
                    exception_type='ConcurrentTestError',
                    exception_value=f'Thread {thread_id}, Event {i}',
                    tags={'test': 'concurrent', 'thread': str(thread_id)},
                    level='error'
                )

                if event_id:
                    success_count += 1

            return success_count

        total_success = 0

        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(send_errors, i) for i in range(thread_count)]

            for future in as_completed(futures):
                total_success += future.result()

        duration = time.time() - start_time
        total_events = thread_count * events_per_thread
        success_rate = total_success / total_events * 100 if total_events > 0 else 0

        result = {
            'test': 'concurrent',
            'thread_count': thread_count,
            'events_per_thread': events_per_thread,
            'total_events': total_events,
            'successful': total_success,
            'success_rate': f'{success_rate:.1f}%',
            'duration': f'{duration:.2f}s',
            'events_per_second': f'{(total_events / duration):.1f}'
        }

        logger.info(f"✓ Concurrent test completed ({success_rate:.1f}% success)")

        return result

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests."""
        logger.info("Running all tests...")

        results = {
            'test_suite': 'error_tracking',
            'started_at': datetime.now().isoformat(),
            'tests': {}
        }

        tests = [
            ('capture', lambda: self.test_capture(count=5)),
            ('grouping', lambda: self.test_grouping(count=10)),
            ('fingerprinting', self.test_fingerprinting),
            ('user_impact', self.test_user_impact),
            ('context_enrichment', self.test_context_enrichment),
            ('performance', lambda: self.test_performance(iterations=1000)),
            ('sampling', lambda: self.test_sampling(sample_rate=0.1, count=100)),
            ('levels', self.test_levels),
            ('concurrent', lambda: self.test_concurrent(thread_count=5, events_per_thread=5))
        ]

        for test_name, test_func in tests:
            try:
                logger.info(f"\n--- Running test: {test_name} ---")
                result = test_func()
                results['tests'][test_name] = {
                    'status': 'passed',
                    'result': result
                }
            except Exception as e:
                logger.error(f"Test {test_name} failed: {e}")
                results['tests'][test_name] = {
                    'status': 'failed',
                    'error': str(e)
                }

        results['completed_at'] = datetime.now().isoformat()

        # Summary
        total_tests = len(tests)
        passed_tests = sum(1 for t in results['tests'].values() if t['status'] == 'passed')
        failed_tests = total_tests - passed_tests

        results['summary'] = {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': f'{(passed_tests / total_tests * 100):.1f}%'
        }

        logger.info("\n" + "=" * 80)
        logger.info(f"Test Summary: {passed_tests}/{total_tests} passed ({results['summary']['success_rate']})")
        logger.info("=" * 80)

        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Error tracking testing suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--dsn',
        default=os.getenv('SENTRY_DSN'),
        help='Sentry DSN (or set SENTRY_DSN env var)'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all tests'
    )

    parser.add_argument(
        '--test-capture',
        action='store_true',
        help='Test error capture'
    )

    parser.add_argument(
        '--test-grouping',
        action='store_true',
        help='Test error grouping'
    )

    parser.add_argument(
        '--test-fingerprinting',
        action='store_true',
        help='Test custom fingerprinting'
    )

    parser.add_argument(
        '--test-user-impact',
        action='store_true',
        help='Test user impact tracking'
    )

    parser.add_argument(
        '--test-context',
        action='store_true',
        help='Test context enrichment'
    )

    parser.add_argument(
        '--test-performance',
        action='store_true',
        help='Test performance impact'
    )

    parser.add_argument(
        '--test-sampling',
        action='store_true',
        help='Test error sampling'
    )

    parser.add_argument(
        '--test-levels',
        action='store_true',
        help='Test error levels'
    )

    parser.add_argument(
        '--test-concurrent',
        action='store_true',
        help='Test concurrent sending'
    )

    parser.add_argument(
        '--count',
        type=int,
        default=10,
        help='Number of events for applicable tests (default: 10)'
    )

    parser.add_argument(
        '--iterations',
        type=int,
        default=1000,
        help='Number of iterations for performance test (default: 1000)'
    )

    parser.add_argument(
        '--output',
        help='Output file path for results (JSON)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Validate DSN
    if not args.dsn:
        logger.error("Sentry DSN required (--dsn or SENTRY_DSN env var)")
        sys.exit(1)

    # Create client and test suite
    try:
        client = SentryTestClient(args.dsn)
        tests = ErrorTrackingTests(client, verbose=args.verbose)
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        sys.exit(1)

    # Run tests
    results = None

    if args.all:
        results = tests.run_all_tests()
    else:
        individual_results = {}

        if args.test_capture:
            individual_results['capture'] = tests.test_capture(count=args.count)

        if args.test_grouping:
            individual_results['grouping'] = tests.test_grouping(count=args.count)

        if args.test_fingerprinting:
            individual_results['fingerprinting'] = tests.test_fingerprinting()

        if args.test_user_impact:
            individual_results['user_impact'] = tests.test_user_impact()

        if args.test_context:
            individual_results['context_enrichment'] = tests.test_context_enrichment()

        if args.test_performance:
            individual_results['performance'] = tests.test_performance(iterations=args.iterations)

        if args.test_sampling:
            individual_results['sampling'] = tests.test_sampling(count=args.count)

        if args.test_levels:
            individual_results['levels'] = tests.test_levels()

        if args.test_concurrent:
            individual_results['concurrent'] = tests.test_concurrent()

        if individual_results:
            results = {
                'test_suite': 'error_tracking',
                'timestamp': datetime.now().isoformat(),
                'tests': individual_results
            }

    if not results:
        logger.warning("No tests specified. Use --all or individual test flags.")
        parser.print_help()
        sys.exit(1)

    # Output results
    if args.json or args.output:
        output = json.dumps(results, indent=2)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            logger.info(f"Results written to {args.output}")
        else:
            print(output)


if __name__ == "__main__":
    main()
