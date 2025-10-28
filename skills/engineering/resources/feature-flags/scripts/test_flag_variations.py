#!/usr/bin/env python3
"""
Feature Flag Variation Testing Tool

Comprehensive tool for testing feature flag variations, targeting rules,
override mechanisms, and integration testing.

Capabilities:
- Test all flag variations
- Verify targeting rules
- Test override mechanisms
- Validate default values
- Integration testing with flag providers
- Load testing flag evaluation
- Shadow testing (compare providers)
- Generate test reports

Usage:
    test_flag_variations.py test --flag feature-x --all-variations
    test_flag_variations.py targeting --flag feature-x --rules rules.json
    test_flag_variations.py override --flag feature-x --variation on
    test_flag_variations.py integration --provider launchdarkly
    test_flag_variations.py load --flag feature-x --requests 10000
    test_flag_variations.py shadow --flag feature-x --providers provider1,provider2
"""

import argparse
import json
import sys
import os
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import re


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class AssertionType(Enum):
    """Assertion types"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    MATCHES = "matches"
    TYPE_CHECK = "type_check"


@dataclass
class TestContext:
    """Test evaluation context"""
    user_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    overrides: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'attributes': self.attributes,
            'overrides': self.overrides
        }


@dataclass
class TestAssertion:
    """Test assertion"""
    assertion_type: AssertionType
    expected: Any
    actual: Optional[Any] = None
    passed: Optional[bool] = None
    message: Optional[str] = None

    def evaluate(self, actual_value: Any) -> bool:
        """Evaluate assertion"""
        self.actual = actual_value

        try:
            if self.assertion_type == AssertionType.EQUALS:
                self.passed = actual_value == self.expected
            elif self.assertion_type == AssertionType.NOT_EQUALS:
                self.passed = actual_value != self.expected
            elif self.assertion_type == AssertionType.IN:
                self.passed = actual_value in self.expected
            elif self.assertion_type == AssertionType.NOT_IN:
                self.passed = actual_value not in self.expected
            elif self.assertion_type == AssertionType.GREATER_THAN:
                self.passed = actual_value > self.expected
            elif self.assertion_type == AssertionType.LESS_THAN:
                self.passed = actual_value < self.expected
            elif self.assertion_type == AssertionType.MATCHES:
                self.passed = bool(re.match(self.expected, str(actual_value)))
            elif self.assertion_type == AssertionType.TYPE_CHECK:
                self.passed = type(actual_value).__name__ == self.expected
            else:
                self.passed = False
                self.message = f"Unknown assertion type: {self.assertion_type}"

            if not self.passed and not self.message:
                self.message = f"Expected {self.expected}, got {actual_value}"

        except Exception as e:
            self.passed = False
            self.message = f"Assertion error: {e}"

        return self.passed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'type': self.assertion_type.value,
            'expected': self.expected,
            'actual': self.actual,
            'passed': self.passed,
            'message': self.message
        }


@dataclass
class TestCase:
    """Feature flag test case"""
    name: str
    flag_key: str
    context: TestContext
    assertions: List[TestAssertion]
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    timeout_ms: int = 5000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'flag_key': self.flag_key,
            'context': self.context.to_dict(),
            'assertions': [a.to_dict() for a in self.assertions],
            'description': self.description,
            'tags': self.tags,
            'timeout_ms': self.timeout_ms
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create from dictionary"""
        context = TestContext(
            user_id=data['context'].get('user_id'),
            attributes=data['context'].get('attributes', {}),
            overrides=data['context'].get('overrides', {})
        )

        assertions = [
            TestAssertion(
                assertion_type=AssertionType(a['type']),
                expected=a['expected']
            )
            for a in data['assertions']
        ]

        return cls(
            name=data['name'],
            flag_key=data['flag_key'],
            context=context,
            assertions=assertions,
            description=data.get('description'),
            tags=data.get('tags', []),
            timeout_ms=data.get('timeout_ms', 5000)
        )


@dataclass
class TestResult:
    """Test result"""
    test_name: str
    flag_key: str
    status: TestStatus
    duration_ms: float
    assertions: List[TestAssertion]
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'test_name': self.test_name,
            'flag_key': self.flag_key,
            'status': self.status.value,
            'duration_ms': self.duration_ms,
            'assertions': [a.to_dict() for a in self.assertions],
            'error': self.error,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class TestSuite:
    """Test suite"""
    name: str
    test_cases: List[TestCase]
    description: Optional[str] = None
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'test_cases': [tc.to_dict() for tc in self.test_cases],
            'description': self.description
        }


class FlagEvaluator:
    """Flag evaluator interface"""

    def evaluate(
        self,
        flag_key: str,
        context: TestContext,
        default: Any
    ) -> Any:
        """Evaluate flag"""
        raise NotImplementedError


class MockEvaluator(FlagEvaluator):
    """Mock evaluator for testing"""

    def __init__(self, flag_values: Dict[str, Any]):
        self.flag_values = flag_values

    def evaluate(
        self,
        flag_key: str,
        context: TestContext,
        default: Any
    ) -> Any:
        """Evaluate flag from mock values"""
        # Check overrides first
        if flag_key in context.overrides:
            return context.overrides[flag_key]

        # Check mock values
        if flag_key in self.flag_values:
            return self.flag_values[flag_key]

        return default


class LaunchDarklyEvaluator(FlagEvaluator):
    """LaunchDarkly evaluator"""

    def __init__(self, sdk_key: str):
        self.sdk_key = sdk_key
        logger.info("LaunchDarkly evaluator initialized")

    def evaluate(
        self,
        flag_key: str,
        context: TestContext,
        default: Any
    ) -> Any:
        """Evaluate flag using LaunchDarkly SDK"""
        # Check overrides first
        if flag_key in context.overrides:
            return context.overrides[flag_key]

        # In production, would use actual LaunchDarkly SDK
        logger.info(f"Evaluating {flag_key} with LaunchDarkly")
        return default


class UnleashEvaluator(FlagEvaluator):
    """Unleash evaluator"""

    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url
        self.api_token = api_token
        logger.info("Unleash evaluator initialized")

    def evaluate(
        self,
        flag_key: str,
        context: TestContext,
        default: Any
    ) -> Any:
        """Evaluate flag using Unleash SDK"""
        # Check overrides first
        if flag_key in context.overrides:
            return context.overrides[flag_key]

        # In production, would use actual Unleash SDK
        logger.info(f"Evaluating {flag_key} with Unleash")
        return default


class TestRunner:
    """Test runner"""

    def __init__(self, evaluator: FlagEvaluator):
        self.evaluator = evaluator

    def run_test(self, test_case: TestCase, default: Any = False) -> TestResult:
        """Run a single test case"""
        start_time = time.time()

        try:
            # Evaluate flag
            value = self.evaluator.evaluate(
                test_case.flag_key,
                test_case.context,
                default
            )

            # Run assertions
            all_passed = True
            for assertion in test_case.assertions:
                passed = assertion.evaluate(value)
                if not passed:
                    all_passed = False

            status = TestStatus.PASSED if all_passed else TestStatus.FAILED

        except Exception as e:
            logger.error(f"Test error: {e}")
            status = TestStatus.ERROR
            for assertion in test_case.assertions:
                assertion.passed = False
                assertion.message = str(e)

        duration_ms = (time.time() - start_time) * 1000

        return TestResult(
            test_name=test_case.name,
            flag_key=test_case.flag_key,
            status=status,
            duration_ms=duration_ms,
            assertions=test_case.assertions
        )

    def run_suite(self, suite: TestSuite, default: Any = False) -> List[TestResult]:
        """Run a test suite"""
        results = []

        # Run setup
        if suite.setup:
            suite.setup()

        try:
            for test_case in suite.test_cases:
                result = self.run_test(test_case, default)
                results.append(result)
        finally:
            # Run teardown
            if suite.teardown:
                suite.teardown()

        return results

    def run_parallel(
        self,
        test_cases: List[TestCase],
        default: Any = False,
        max_workers: int = 10
    ) -> List[TestResult]:
        """Run tests in parallel"""
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.run_test, tc, default): tc
                for tc in test_cases
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Parallel test error: {e}")

        return results


class VariationTester:
    """Test all variations of a flag"""

    def __init__(self, evaluator: FlagEvaluator):
        self.evaluator = evaluator

    def test_all_variations(
        self,
        flag_key: str,
        variations: List[str],
        contexts: Optional[List[TestContext]] = None
    ) -> List[TestResult]:
        """Test all flag variations"""
        if not contexts:
            contexts = [TestContext()]

        test_cases = []

        for variation in variations:
            for i, context in enumerate(contexts):
                # Create override for this variation
                test_context = TestContext(
                    user_id=context.user_id,
                    attributes=context.attributes.copy(),
                    overrides={flag_key: variation}
                )

                assertion = TestAssertion(
                    assertion_type=AssertionType.EQUALS,
                    expected=variation
                )

                test_case = TestCase(
                    name=f"{flag_key}_variation_{variation}_context_{i}",
                    flag_key=flag_key,
                    context=test_context,
                    assertions=[assertion]
                )

                test_cases.append(test_case)

        runner = TestRunner(self.evaluator)
        return runner.run_parallel(test_cases)


class TargetingTester:
    """Test targeting rules"""

    def __init__(self, evaluator: FlagEvaluator):
        self.evaluator = evaluator

    def test_targeting_rules(
        self,
        flag_key: str,
        rules: List[Dict[str, Any]]
    ) -> List[TestResult]:
        """Test targeting rules"""
        test_cases = []

        for i, rule in enumerate(rules):
            # Create context matching the rule
            context = TestContext(
                user_id=rule.get('user_id'),
                attributes=rule.get('attributes', {})
            )

            assertion = TestAssertion(
                assertion_type=AssertionType.EQUALS,
                expected=rule['expected_variation']
            )

            test_case = TestCase(
                name=f"{flag_key}_rule_{i}",
                flag_key=flag_key,
                context=context,
                assertions=[assertion],
                description=rule.get('description')
            )

            test_cases.append(test_case)

        runner = TestRunner(self.evaluator)
        return runner.run_parallel(test_cases)


class OverrideTester:
    """Test override mechanisms"""

    def __init__(self, evaluator: FlagEvaluator):
        self.evaluator = evaluator

    def test_overrides(
        self,
        flag_key: str,
        override_value: Any
    ) -> TestResult:
        """Test flag override"""
        context = TestContext(overrides={flag_key: override_value})

        assertion = TestAssertion(
            assertion_type=AssertionType.EQUALS,
            expected=override_value
        )

        test_case = TestCase(
            name=f"{flag_key}_override",
            flag_key=flag_key,
            context=context,
            assertions=[assertion]
        )

        runner = TestRunner(self.evaluator)
        return runner.run_test(test_case)


class LoadTester:
    """Load test flag evaluation"""

    def __init__(self, evaluator: FlagEvaluator):
        self.evaluator = evaluator

    def run_load_test(
        self,
        flag_key: str,
        num_requests: int,
        default: Any = False,
        max_workers: int = 10
    ) -> Dict[str, Any]:
        """Run load test"""
        contexts = [
            TestContext(user_id=f"user_{i}")
            for i in range(num_requests)
        ]

        start_time = time.time()
        durations = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for context in contexts:
                future = executor.submit(
                    self._evaluate_with_timing,
                    flag_key,
                    context,
                    default
                )
                futures.append(future)

            for future in as_completed(futures):
                try:
                    duration = future.result()
                    durations.append(duration)
                except Exception as e:
                    logger.error(f"Load test error: {e}")

        total_time = time.time() - start_time

        return {
            'flag_key': flag_key,
            'total_requests': num_requests,
            'successful_requests': len(durations),
            'failed_requests': num_requests - len(durations),
            'total_time_s': total_time,
            'requests_per_second': num_requests / total_time,
            'avg_duration_ms': statistics.mean(durations) if durations else 0,
            'p50_duration_ms': statistics.median(durations) if durations else 0,
            'p95_duration_ms': statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else 0,
            'p99_duration_ms': statistics.quantiles(durations, n=100)[98] if len(durations) > 100 else 0,
            'min_duration_ms': min(durations) if durations else 0,
            'max_duration_ms': max(durations) if durations else 0
        }

    def _evaluate_with_timing(
        self,
        flag_key: str,
        context: TestContext,
        default: Any
    ) -> float:
        """Evaluate flag and return duration"""
        start = time.time()
        self.evaluator.evaluate(flag_key, context, default)
        return (time.time() - start) * 1000


class ShadowTester:
    """Shadow test between providers"""

    def __init__(self, evaluators: Dict[str, FlagEvaluator]):
        self.evaluators = evaluators

    def compare_providers(
        self,
        flag_key: str,
        contexts: List[TestContext],
        default: Any = False
    ) -> Dict[str, Any]:
        """Compare flag evaluation across providers"""
        results = {}

        for provider_name, evaluator in self.evaluators.items():
            provider_results = []

            for context in contexts:
                value = evaluator.evaluate(flag_key, context, default)
                provider_results.append({
                    'context': context.to_dict(),
                    'value': value
                })

            results[provider_name] = provider_results

        # Compare results
        mismatches = []
        if len(self.evaluators) > 1:
            provider_names = list(self.evaluators.keys())
            primary = provider_names[0]

            for i, context in enumerate(contexts):
                primary_value = results[primary][i]['value']

                for provider_name in provider_names[1:]:
                    provider_value = results[provider_name][i]['value']

                    if primary_value != provider_value:
                        mismatches.append({
                            'context_index': i,
                            'primary_provider': primary,
                            'primary_value': primary_value,
                            'provider': provider_name,
                            'provider_value': provider_value
                        })

        return {
            'flag_key': flag_key,
            'num_contexts': len(contexts),
            'results': results,
            'mismatches': mismatches,
            'mismatch_rate': len(mismatches) / len(contexts) if contexts else 0
        }


class ReportGenerator:
    """Generate test reports"""

    def generate_summary(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate test summary"""
        total = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

        durations = [r.duration_ms for r in results]

        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'skipped': skipped,
            'pass_rate': passed / total if total > 0 else 0,
            'total_duration_ms': sum(durations),
            'avg_duration_ms': statistics.mean(durations) if durations else 0,
            'results': [r.to_dict() for r in results]
        }

    def generate_html_report(self, summary: Dict[str, Any]) -> str:
        """Generate HTML report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Feature Flag Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f0f0f0; padding: 15px; margin: 20px 0; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .error {{ color: orange; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Feature Flag Test Report</h1>

    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Tests:</strong> {summary['total_tests']}</p>
        <p class="passed"><strong>Passed:</strong> {summary['passed']}</p>
        <p class="failed"><strong>Failed:</strong> {summary['failed']}</p>
        <p class="error"><strong>Errors:</strong> {summary['errors']}</p>
        <p><strong>Pass Rate:</strong> {summary['pass_rate']*100:.1f}%</p>
        <p><strong>Total Duration:</strong> {summary['total_duration_ms']:.2f}ms</p>
    </div>

    <h2>Test Results</h2>
    <table>
        <tr>
            <th>Test</th>
            <th>Flag</th>
            <th>Status</th>
            <th>Duration (ms)</th>
            <th>Assertions</th>
        </tr>
"""

        for result in summary['results']:
            status_class = result['status']
            passed_assertions = sum(1 for a in result['assertions'] if a['passed'])
            total_assertions = len(result['assertions'])

            html += f"""
        <tr>
            <td>{result['test_name']}</td>
            <td>{result['flag_key']}</td>
            <td class="{status_class}">{result['status']}</td>
            <td>{result['duration_ms']:.2f}</td>
            <td>{passed_assertions}/{total_assertions}</td>
        </tr>
"""

        html += """
    </table>
</body>
</html>
"""
        return html


def get_evaluator(provider: str, config: Dict[str, Any]) -> FlagEvaluator:
    """Get evaluator instance"""
    if provider == 'mock':
        return MockEvaluator(config.get('flag_values', {}))
    elif provider == 'launchdarkly':
        return LaunchDarklyEvaluator(
            sdk_key=config.get('sdk_key', os.getenv('LAUNCHDARKLY_SDK_KEY', ''))
        )
    elif provider == 'unleash':
        return UnleashEvaluator(
            api_url=config.get('api_url', os.getenv('UNLEASH_API_URL', '')),
            api_token=config.get('api_token', os.getenv('UNLEASH_API_TOKEN', ''))
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Feature Flag Variation Testing Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--provider', default='mock',
                       help='Flag provider')
    parser.add_argument('--config', help='Provider config file')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Test variations command
    test_parser = subparsers.add_parser('test', help='Test flag variations')
    test_parser.add_argument('--flag', required=True, help='Flag key')
    test_parser.add_argument('--variations', required=True,
                            help='Comma-separated variations')
    test_parser.add_argument('--contexts', help='JSON file with contexts')

    # Targeting command
    targeting_parser = subparsers.add_parser('targeting',
                                            help='Test targeting rules')
    targeting_parser.add_argument('--flag', required=True, help='Flag key')
    targeting_parser.add_argument('--rules', required=True,
                                 help='JSON file with rules')

    # Override command
    override_parser = subparsers.add_parser('override',
                                           help='Test override mechanism')
    override_parser.add_argument('--flag', required=True, help='Flag key')
    override_parser.add_argument('--value', required=True,
                                help='Override value')

    # Load test command
    load_parser = subparsers.add_parser('load', help='Run load test')
    load_parser.add_argument('--flag', required=True, help='Flag key')
    load_parser.add_argument('--requests', type=int, default=1000,
                            help='Number of requests')
    load_parser.add_argument('--workers', type=int, default=10,
                            help='Max workers')

    # Shadow test command
    shadow_parser = subparsers.add_parser('shadow',
                                         help='Shadow test providers')
    shadow_parser.add_argument('--flag', required=True, help='Flag key')
    shadow_parser.add_argument('--providers', required=True,
                              help='Comma-separated providers')
    shadow_parser.add_argument('--contexts', help='JSON file with contexts')

    # Report command
    report_parser = subparsers.add_parser('report',
                                         help='Generate test report')
    report_parser.add_argument('--results', required=True,
                              help='JSON file with results')
    report_parser.add_argument('--format', choices=['json', 'html'],
                              default='json', help='Report format')
    report_parser.add_argument('--output', help='Output file')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        # Load provider config
        provider_config = {}
        if args.config and os.path.exists(args.config):
            with open(args.config, 'r') as f:
                provider_config = json.load(f)

        result = None

        if args.command == 'test':
            evaluator = get_evaluator(args.provider, provider_config)
            tester = VariationTester(evaluator)

            variations = args.variations.split(',')
            contexts = None
            if args.contexts and os.path.exists(args.contexts):
                with open(args.contexts, 'r') as f:
                    contexts_data = json.load(f)
                    contexts = [
                        TestContext(**ctx) for ctx in contexts_data
                    ]

            results = tester.test_all_variations(
                args.flag, variations, contexts
            )
            result = [r.to_dict() for r in results]

        elif args.command == 'targeting':
            evaluator = get_evaluator(args.provider, provider_config)
            tester = TargetingTester(evaluator)

            with open(args.rules, 'r') as f:
                rules = json.load(f)

            results = tester.test_targeting_rules(args.flag, rules)
            result = [r.to_dict() for r in results]

        elif args.command == 'override':
            evaluator = get_evaluator(args.provider, provider_config)
            tester = OverrideTester(evaluator)

            # Parse value
            try:
                value = json.loads(args.value)
            except:
                value = args.value

            test_result = tester.test_overrides(args.flag, value)
            result = test_result.to_dict()

        elif args.command == 'load':
            evaluator = get_evaluator(args.provider, provider_config)
            tester = LoadTester(evaluator)

            result = tester.run_load_test(
                args.flag,
                args.requests,
                max_workers=args.workers
            )

        elif args.command == 'shadow':
            providers = args.providers.split(',')
            evaluators = {}

            for provider in providers:
                evaluators[provider] = get_evaluator(provider, provider_config)

            tester = ShadowTester(evaluators)

            contexts = [TestContext(user_id=f"user_{i}") for i in range(100)]
            if args.contexts and os.path.exists(args.contexts):
                with open(args.contexts, 'r') as f:
                    contexts_data = json.load(f)
                    contexts = [
                        TestContext(**ctx) for ctx in contexts_data
                    ]

            result = tester.compare_providers(args.flag, contexts)

        elif args.command == 'report':
            with open(args.results, 'r') as f:
                results_data = json.load(f)

            generator = ReportGenerator()
            summary = generator.generate_summary([
                TestResult(**r) for r in results_data
            ])

            if args.format == 'html':
                html_report = generator.generate_html_report(summary)
                if args.output:
                    with open(args.output, 'w') as f:
                        f.write(html_report)
                    result = {'status': 'written', 'file': args.output}
                else:
                    print(html_report)
                    return 0
            else:
                result = summary

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result, indent=2))

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        if args.json:
            print(json.dumps({'error': str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
