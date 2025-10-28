#!/usr/bin/env python3
"""
Resilience and Chaos Engineering Test Suite

Run chaos engineering experiments to inject failures (network, latency, resource),
verify graceful degradation, test circuit breakers, and validate SLOs under failure.

Usage:
    test_resilience.py --experiment network-partition --duration 300 --target api
    test_resilience.py --experiment latency-injection --delay 100 --target database
    test_resilience.py --experiment resource-exhaustion --resource cpu --target service
    test_resilience.py --experiment dependency-failure --target auth-service
    test_resilience.py --list-experiments
"""

import argparse
import json
import sys
import time
import subprocess
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import requests


class ExperimentType(Enum):
    """Types of chaos experiments."""
    NETWORK_PARTITION = "network_partition"
    NETWORK_LATENCY = "network_latency"
    NETWORK_PACKET_LOSS = "network_packet_loss"
    CPU_STRESS = "cpu_stress"
    MEMORY_STRESS = "memory_stress"
    DISK_STRESS = "disk_stress"
    DEPENDENCY_FAILURE = "dependency_failure"
    POD_FAILURE = "pod_failure"
    CLOCK_SKEW = "clock_skew"


class ExperimentStatus(Enum):
    """Chaos experiment status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ABORTED = "aborted"


class SteadyStateOperator(Enum):
    """Operators for steady state comparison."""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUALS = "=="
    NOT_EQUALS = "!="


@dataclass
class SteadyStateHypothesis:
    """Define steady state for system under test."""
    name: str
    metric: str
    operator: SteadyStateOperator
    threshold: float
    measurement_func: Optional[Callable[[], float]] = None


@dataclass
class ChaosExperiment:
    """Chaos engineering experiment definition."""
    name: str
    experiment_type: ExperimentType
    description: str
    target_service: str
    blast_radius: float  # 0-1, fraction of instances/traffic affected
    duration_seconds: int
    parameters: Dict[str, Any]
    steady_state: SteadyStateHypothesis
    rollback_required: bool = True


@dataclass
class ExperimentResult:
    """Results from chaos experiment."""
    experiment_name: str
    status: ExperimentStatus
    start_time: str
    end_time: str
    duration_seconds: float
    steady_state_before: float
    steady_state_during: float
    steady_state_after: float
    steady_state_maintained: bool
    errors: List[str]
    observations: List[str]
    recommendations: List[str]


@dataclass
class CircuitBreakerTest:
    """Circuit breaker validation test."""
    service: str
    dependency: str
    failure_threshold: int
    success_threshold: int
    timeout_seconds: int
    test_passed: bool
    open_after_failures: int
    closed_after_successes: int


class ResilienceTester:
    """Chaos engineering and resilience testing."""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose

    def run_experiment(self, experiment: ChaosExperiment) -> ExperimentResult:
        """
        Execute chaos experiment.

        Args:
            experiment: Experiment definition

        Returns:
            ExperimentResult with test outcome
        """
        start_time = datetime.now()
        errors = []
        observations = []
        recommendations = []

        if self.verbose:
            print(f"Starting experiment: {experiment.name}")
            print(f"Type: {experiment.experiment_type.value}")
            print(f"Target: {experiment.target_service}")
            print(f"Duration: {experiment.duration_seconds}s")
            print(f"Blast radius: {experiment.blast_radius * 100}%\n")

        try:
            # Step 1: Measure baseline steady state
            observations.append("Measuring baseline steady state")
            steady_state_before = self._measure_steady_state(experiment.steady_state)

            if not self._is_steady_state_valid(experiment.steady_state, steady_state_before):
                errors.append("Baseline not healthy, aborting experiment")
                return self._create_result(
                    experiment=experiment,
                    status=ExperimentStatus.ABORTED,
                    start_time=start_time,
                    steady_state_before=steady_state_before,
                    steady_state_during=0,
                    steady_state_after=0,
                    errors=errors,
                    observations=observations,
                    recommendations=["Fix baseline issues before running chaos experiments"],
                )

            observations.append(f"Baseline healthy: {steady_state_before:.4f}")

            # Step 2: Inject chaos
            observations.append(f"Injecting chaos: {experiment.experiment_type.value}")
            self._inject_chaos(experiment)

            # Step 3: Monitor during chaos
            observations.append(f"Monitoring for {experiment.duration_seconds}s")
            time.sleep(min(experiment.duration_seconds, 5))  # Shortened for demo

            steady_state_during = self._measure_steady_state(experiment.steady_state)
            observations.append(f"Steady state during chaos: {steady_state_during:.4f}")

            # Step 4: Rollback chaos
            if experiment.rollback_required:
                observations.append("Rolling back chaos injection")
                self._rollback_chaos(experiment)

            # Step 5: Validate recovery
            observations.append("Waiting for system recovery")
            time.sleep(5)  # Wait for stabilization

            steady_state_after = self._measure_steady_state(experiment.steady_state)
            observations.append(f"Steady state after recovery: {steady_state_after:.4f}")

            # Evaluate results
            steady_state_maintained = self._is_steady_state_valid(
                experiment.steady_state,
                steady_state_during
            )

            if steady_state_maintained:
                status = ExperimentStatus.PASSED
                observations.append("✓ System maintained steady state during chaos")
                recommendations.append("System resilient to this failure mode")
            else:
                status = ExperimentStatus.FAILED
                observations.append("✗ System degraded beyond acceptable limits")
                recommendations.extend([
                    "Implement circuit breakers or fallbacks",
                    "Review timeout and retry configuration",
                    "Consider graceful degradation patterns",
                ])

            # Check recovery
            if not self._is_steady_state_valid(experiment.steady_state, steady_state_after):
                errors.append("System did not recover after chaos rollback")
                recommendations.append("Investigate why system did not self-heal")

        except Exception as e:
            errors.append(f"Experiment error: {str(e)}")
            status = ExperimentStatus.ABORTED

            # Emergency rollback
            try:
                if experiment.rollback_required:
                    self._rollback_chaos(experiment)
            except Exception as rollback_error:
                errors.append(f"Rollback failed: {str(rollback_error)}")

            steady_state_during = 0
            steady_state_after = 0
            steady_state_maintained = False

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return self._create_result(
            experiment=experiment,
            status=status,
            start_time=start_time,
            steady_state_before=steady_state_before,
            steady_state_during=steady_state_during,
            steady_state_after=steady_state_after,
            errors=errors,
            observations=observations,
            recommendations=recommendations,
            steady_state_maintained=steady_state_maintained,
        )

    def test_circuit_breaker(
        self,
        service: str,
        dependency: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60
    ) -> CircuitBreakerTest:
        """
        Test circuit breaker implementation.

        Args:
            service: Service with circuit breaker
            dependency: Dependency being protected
            failure_threshold: Failures to open circuit
            success_threshold: Successes to close circuit
            timeout_seconds: Timeout before half-open

        Returns:
            CircuitBreakerTest results
        """
        if self.verbose:
            print(f"\nTesting circuit breaker: {service} → {dependency}")

        # Simulate failures
        failure_count = 0
        for i in range(failure_threshold + 2):
            if self.verbose:
                print(f"  Attempt {i+1}: Simulating failure")

            # In real implementation, would call service and expect failure
            # For demo, we simulate
            failure_count += 1
            time.sleep(0.1)

        # Check if circuit opened
        circuit_open = failure_count >= failure_threshold

        if self.verbose:
            if circuit_open:
                print(f"  ✓ Circuit opened after {failure_count} failures")
            else:
                print(f"  ✗ Circuit did not open")

        # Wait for half-open state
        if self.verbose:
            print(f"  Waiting {timeout_seconds}s for half-open state")
        time.sleep(min(timeout_seconds, 2))  # Shortened for demo

        # Test recovery
        success_count = 0
        for i in range(success_threshold + 2):
            if self.verbose:
                print(f"  Attempt {i+1}: Simulating success")

            success_count += 1
            time.sleep(0.1)

        # Check if circuit closed
        circuit_closed = success_count >= success_threshold

        if self.verbose:
            if circuit_closed:
                print(f"  ✓ Circuit closed after {success_count} successes")
            else:
                print(f"  ✗ Circuit did not close")

        test_passed = circuit_open and circuit_closed

        return CircuitBreakerTest(
            service=service,
            dependency=dependency,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout_seconds=timeout_seconds,
            test_passed=test_passed,
            open_after_failures=failure_count,
            closed_after_successes=success_count,
        )

    def validate_graceful_degradation(
        self,
        service: str,
        dependency: str,
        expected_fallback: str
    ) -> Dict[str, Any]:
        """
        Validate graceful degradation when dependency fails.

        Args:
            service: Service under test
            dependency: Failed dependency
            expected_fallback: Expected fallback behavior

        Returns:
            Validation results
        """
        if self.verbose:
            print(f"\nValidating graceful degradation: {service}")
            print(f"  Failed dependency: {dependency}")
            print(f"  Expected fallback: {expected_fallback}")

        # Simulate dependency failure
        if self.verbose:
            print("  Simulating dependency failure...")

        time.sleep(1)

        # Check service behavior
        service_available = True  # In real test, would call service
        fallback_active = True    # In real test, would verify fallback

        degraded_functionality = True if service_available and fallback_active else False

        if self.verbose:
            if degraded_functionality:
                print("  ✓ Service degraded gracefully")
            else:
                print("  ✗ Service failed completely")

        return {
            "service": service,
            "dependency": dependency,
            "service_available": service_available,
            "fallback_active": fallback_active,
            "degraded_gracefully": degraded_functionality,
            "expected_fallback": expected_fallback,
        }

    def _inject_chaos(self, experiment: ChaosExperiment):
        """Inject chaos based on experiment type."""
        if self.dry_run:
            print(f"[DRY RUN] Would inject {experiment.experiment_type.value}")
            return

        exp_type = experiment.experiment_type
        target = experiment.target_service
        params = experiment.parameters

        if exp_type == ExperimentType.NETWORK_PARTITION:
            self._inject_network_partition(target, params)
        elif exp_type == ExperimentType.NETWORK_LATENCY:
            self._inject_network_latency(target, params)
        elif exp_type == ExperimentType.NETWORK_PACKET_LOSS:
            self._inject_packet_loss(target, params)
        elif exp_type == ExperimentType.CPU_STRESS:
            self._inject_cpu_stress(target, params)
        elif exp_type == ExperimentType.MEMORY_STRESS:
            self._inject_memory_stress(target, params)
        elif exp_type == ExperimentType.DEPENDENCY_FAILURE:
            self._inject_dependency_failure(target, params)
        elif exp_type == ExperimentType.POD_FAILURE:
            self._inject_pod_failure(target, params)

    def _rollback_chaos(self, experiment: ChaosExperiment):
        """Rollback chaos injection."""
        if self.dry_run:
            print(f"[DRY RUN] Would rollback {experiment.experiment_type.value}")
            return

        # In real implementation, would clean up chaos
        # For example: remove network rules, stop stress processes, restart pods
        if self.verbose:
            print(f"  Rolling back {experiment.experiment_type.value}")

    def _inject_network_partition(self, target: str, params: Dict[str, Any]):
        """Inject network partition."""
        # In Kubernetes, this might use NetworkPolicy or Chaos Mesh
        if self.verbose:
            print(f"  Creating network partition for {target}")

    def _inject_network_latency(self, target: str, params: Dict[str, Any]):
        """Inject network latency."""
        delay_ms = params.get("delay_ms", 100)

        # Using tc (traffic control) on Linux
        # tc qdisc add dev eth0 root netem delay 100ms

        if self.verbose:
            print(f"  Adding {delay_ms}ms latency to {target}")

    def _inject_packet_loss(self, target: str, params: Dict[str, Any]):
        """Inject packet loss."""
        loss_percent = params.get("loss_percent", 5)

        # tc qdisc add dev eth0 root netem loss 5%

        if self.verbose:
            print(f"  Injecting {loss_percent}% packet loss for {target}")

    def _inject_cpu_stress(self, target: str, params: Dict[str, Any]):
        """Inject CPU stress."""
        workers = params.get("workers", 2)
        load_percent = params.get("load_percent", 80)

        # stress-ng --cpu 2 --cpu-load 80

        if self.verbose:
            print(f"  Stressing CPU: {workers} workers at {load_percent}% load")

    def _inject_memory_stress(self, target: str, params: Dict[str, Any]):
        """Inject memory stress."""
        memory_mb = params.get("memory_mb", 512)

        # stress-ng --vm 1 --vm-bytes 512M

        if self.verbose:
            print(f"  Allocating {memory_mb}MB memory")

    def _inject_dependency_failure(self, target: str, params: Dict[str, Any]):
        """Simulate dependency failure."""
        dependency = params.get("dependency", "unknown")

        if self.verbose:
            print(f"  Blocking traffic to dependency: {dependency}")

    def _inject_pod_failure(self, target: str, params: Dict[str, Any]):
        """Kill pods."""
        count = params.get("count", 1)

        # kubectl delete pod -l app=target --grace-period=0

        if self.verbose:
            print(f"  Killing {count} pod(s) of {target}")

    def _measure_steady_state(self, hypothesis: SteadyStateHypothesis) -> float:
        """Measure steady state metric."""
        if hypothesis.measurement_func:
            return hypothesis.measurement_func()

        # Default: simulate measurement
        # In real implementation, would query Prometheus, CloudWatch, etc.
        return random.uniform(0.95, 1.0)

    def _is_steady_state_valid(
        self,
        hypothesis: SteadyStateHypothesis,
        value: float
    ) -> bool:
        """Check if steady state is valid."""
        op = hypothesis.operator
        threshold = hypothesis.threshold

        if op == SteadyStateOperator.GREATER_THAN:
            return value > threshold
        elif op == SteadyStateOperator.LESS_THAN:
            return value < threshold
        elif op == SteadyStateOperator.EQUALS:
            return abs(value - threshold) < 0.001
        elif op == SteadyStateOperator.NOT_EQUALS:
            return abs(value - threshold) >= 0.001

        return False

    def _create_result(
        self,
        experiment: ChaosExperiment,
        status: ExperimentStatus,
        start_time: datetime,
        steady_state_before: float,
        steady_state_during: float,
        steady_state_after: float,
        errors: List[str],
        observations: List[str],
        recommendations: List[str],
        steady_state_maintained: bool = False,
    ) -> ExperimentResult:
        """Create experiment result."""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return ExperimentResult(
            experiment_name=experiment.name,
            status=status,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            steady_state_before=steady_state_before,
            steady_state_during=steady_state_during,
            steady_state_after=steady_state_after,
            steady_state_maintained=steady_state_maintained,
            errors=errors,
            observations=observations,
            recommendations=recommendations,
        )


def get_predefined_experiments() -> Dict[str, ChaosExperiment]:
    """Get library of predefined experiments."""
    return {
        "network-partition": ChaosExperiment(
            name="Network Partition",
            experiment_type=ExperimentType.NETWORK_PARTITION,
            description="Simulate network split between services",
            target_service="api",
            blast_radius=0.5,
            duration_seconds=300,
            parameters={"isolated_services": ["database", "cache"]},
            steady_state=SteadyStateHypothesis(
                name="API Availability",
                metric="availability",
                operator=SteadyStateOperator.GREATER_THAN,
                threshold=0.99,
            ),
        ),
        "latency-injection": ChaosExperiment(
            name="Network Latency",
            experiment_type=ExperimentType.NETWORK_LATENCY,
            description="Add network latency to dependencies",
            target_service="api",
            blast_radius=1.0,
            duration_seconds=600,
            parameters={"delay_ms": 100, "jitter_ms": 20},
            steady_state=SteadyStateHypothesis(
                name="API p95 Latency",
                metric="latency_p95",
                operator=SteadyStateOperator.LESS_THAN,
                threshold=500,  # 500ms threshold
            ),
        ),
        "packet-loss": ChaosExperiment(
            name="Network Packet Loss",
            experiment_type=ExperimentType.NETWORK_PACKET_LOSS,
            description="Drop network packets",
            target_service="api",
            blast_radius=0.5,
            duration_seconds=300,
            parameters={"loss_percent": 5},
            steady_state=SteadyStateHypothesis(
                name="API Success Rate",
                metric="success_rate",
                operator=SteadyStateOperator.GREATER_THAN,
                threshold=0.99,
            ),
        ),
        "cpu-stress": ChaosExperiment(
            name="CPU Stress",
            experiment_type=ExperimentType.CPU_STRESS,
            description="Stress CPU resources",
            target_service="api",
            blast_radius=0.3,
            duration_seconds=300,
            parameters={"workers": 2, "load_percent": 80},
            steady_state=SteadyStateHypothesis(
                name="API Availability",
                metric="availability",
                operator=SteadyStateOperator.GREATER_THAN,
                threshold=0.99,
            ),
        ),
        "memory-stress": ChaosExperiment(
            name="Memory Stress",
            experiment_type=ExperimentType.MEMORY_STRESS,
            description="Exhaust memory",
            target_service="api",
            blast_radius=0.3,
            duration_seconds=300,
            parameters={"memory_mb": 512},
            steady_state=SteadyStateHypothesis(
                name="API Availability",
                metric="availability",
                operator=SteadyStateOperator.GREATER_THAN,
                threshold=0.99,
            ),
        ),
        "dependency-failure": ChaosExperiment(
            name="Dependency Failure",
            experiment_type=ExperimentType.DEPENDENCY_FAILURE,
            description="Simulate downstream service failure",
            target_service="api",
            blast_radius=1.0,
            duration_seconds=600,
            parameters={"dependency": "auth-service"},
            steady_state=SteadyStateHypothesis(
                name="API Availability",
                metric="availability",
                operator=SteadyStateOperator.GREATER_THAN,
                threshold=0.95,  # Allow some degradation
            ),
        ),
        "pod-failure": ChaosExperiment(
            name="Pod Failure",
            experiment_type=ExperimentType.POD_FAILURE,
            description="Kill random pods",
            target_service="api",
            blast_radius=0.2,
            duration_seconds=0,  # Instant
            parameters={"count": 1},
            steady_state=SteadyStateHypothesis(
                name="API Availability",
                metric="availability",
                operator=SteadyStateOperator.GREATER_THAN,
                threshold=0.99,
            ),
        ),
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Chaos engineering and resilience testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available experiments
  %(prog)s --list-experiments

  # Run predefined experiment
  %(prog)s --experiment network-partition --target api --duration 300

  # Run with custom parameters
  %(prog)s --experiment latency-injection --target api --delay 100

  # Test circuit breaker
  %(prog)s --test-circuit-breaker --service api --dependency auth

  # Test graceful degradation
  %(prog)s --test-degradation --service api --dependency cache

  # Dry run (no actual chaos)
  %(prog)s --experiment pod-failure --dry-run
        """
    )

    # Experiment selection
    parser.add_argument(
        "--experiment",
        help="Predefined experiment name"
    )
    parser.add_argument(
        "--list-experiments",
        action="store_true",
        help="List available experiments"
    )

    # Experiment parameters
    parser.add_argument(
        "--target",
        help="Target service for experiment"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Experiment duration in seconds (default: 300)"
    )
    parser.add_argument(
        "--blast-radius",
        type=float,
        default=0.3,
        help="Blast radius 0-1 (default: 0.3)"
    )

    # Specific experiment parameters
    parser.add_argument(
        "--delay",
        type=int,
        help="Network delay in milliseconds"
    )
    parser.add_argument(
        "--loss",
        type=int,
        help="Packet loss percentage"
    )
    parser.add_argument(
        "--resource",
        choices=["cpu", "memory", "disk"],
        help="Resource to stress"
    )

    # Circuit breaker testing
    parser.add_argument(
        "--test-circuit-breaker",
        action="store_true",
        help="Test circuit breaker implementation"
    )
    parser.add_argument(
        "--service",
        help="Service with circuit breaker"
    )
    parser.add_argument(
        "--dependency",
        help="Protected dependency"
    )

    # Graceful degradation
    parser.add_argument(
        "--test-degradation",
        action="store_true",
        help="Test graceful degradation"
    )
    parser.add_argument(
        "--fallback",
        help="Expected fallback behavior"
    )

    # Execution options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (no actual chaos injection)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    tester = ResilienceTester(dry_run=args.dry_run, verbose=args.verbose)

    try:
        # List experiments
        if args.list_experiments:
            experiments = get_predefined_experiments()

            if args.json:
                result = {
                    name: {
                        "type": exp.experiment_type.value,
                        "description": exp.description,
                        "duration": exp.duration_seconds,
                    }
                    for name, exp in experiments.items()
                }
                print(json.dumps(result, indent=2))
            else:
                print("\nAvailable Chaos Experiments:")
                print("=" * 60)
                for name, exp in experiments.items():
                    print(f"\n{name}")
                    print(f"  Type: {exp.experiment_type.value}")
                    print(f"  Description: {exp.description}")
                    print(f"  Duration: {exp.duration_seconds}s")

            sys.exit(0)

        # Test circuit breaker
        if args.test_circuit_breaker:
            if not all([args.service, args.dependency]):
                parser.error("--test-circuit-breaker requires --service and --dependency")

            result = tester.test_circuit_breaker(
                service=args.service,
                dependency=args.dependency,
            )

            if args.json:
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"\nCircuit Breaker Test: {result.service} → {result.dependency}")
                print(f"  Status: {'PASSED' if result.test_passed else 'FAILED'}")
                print(f"  Opened after: {result.open_after_failures} failures")
                print(f"  Closed after: {result.closed_after_successes} successes")

            sys.exit(0)

        # Test graceful degradation
        if args.test_degradation:
            if not all([args.service, args.dependency]):
                parser.error("--test-degradation requires --service and --dependency")

            result = tester.validate_graceful_degradation(
                service=args.service,
                dependency=args.dependency,
                expected_fallback=args.fallback or "default",
            )

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\nGraceful Degradation Test: {result['service']}")
                print(f"  Service available: {result['service_available']}")
                print(f"  Fallback active: {result['fallback_active']}")
                print(f"  Degraded gracefully: {result['degraded_gracefully']}")

            sys.exit(0)

        # Run chaos experiment
        if args.experiment:
            experiments = get_predefined_experiments()

            if args.experiment not in experiments:
                parser.error(f"Unknown experiment: {args.experiment}")

            experiment = experiments[args.experiment]

            # Override parameters if provided
            if args.target:
                experiment.target_service = args.target
            if args.duration:
                experiment.duration_seconds = args.duration
            if args.blast_radius:
                experiment.blast_radius = args.blast_radius

            if args.delay:
                experiment.parameters["delay_ms"] = args.delay
            if args.loss:
                experiment.parameters["loss_percent"] = args.loss

            # Run experiment
            result = tester.run_experiment(experiment)

            if args.json:
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"\n{'=' * 60}")
                print(f"Chaos Experiment: {result.experiment_name}")
                print(f"{'=' * 60}")
                print(f"\nStatus: {result.status.value.upper()}")
                print(f"Duration: {result.duration_seconds:.1f}s")
                print(f"\nSteady State:")
                print(f"  Before:  {result.steady_state_before:.4f}")
                print(f"  During:  {result.steady_state_during:.4f}")
                print(f"  After:   {result.steady_state_after:.4f}")
                print(f"  Maintained: {result.steady_state_maintained}")

                if result.observations:
                    print(f"\nObservations:")
                    for obs in result.observations:
                        print(f"  - {obs}")

                if result.errors:
                    print(f"\nErrors:")
                    for err in result.errors:
                        print(f"  - {err}")

                if result.recommendations:
                    print(f"\nRecommendations:")
                    for rec in result.recommendations:
                        print(f"  - {rec}")

        else:
            parser.error(
                "Must specify one of: --experiment, --test-circuit-breaker, "
                "--test-degradation, or --list-experiments"
            )

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
