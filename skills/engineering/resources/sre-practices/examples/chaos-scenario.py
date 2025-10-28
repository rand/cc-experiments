#!/usr/bin/env python3
"""
Chaos Engineering Scenario: Dependency Failure with Circuit Breaker Test

This scenario tests system resilience when a critical dependency fails.
It validates circuit breaker behavior, fallback mechanisms, and graceful
degradation.

Requirements:
- Service must maintain > 95% availability when dependency fails
- Circuit breaker must open after 5 failures
- Fallback to cached data must activate
- System must recover within 30 seconds after dependency restored
"""

import time
import requests
import random
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Observation:
    """Single observation during experiment."""
    timestamp: datetime
    metric: str
    value: float
    expected: float
    passed: bool
    note: str


class DependencyFailureChaos:
    """
    Chaos experiment: Simulate dependency failure.

    Tests:
    1. Circuit breaker opens after threshold failures
    2. Service remains available using fallback
    3. Graceful degradation maintains core functionality
    4. Service recovers when dependency restored
    """

    def __init__(
        self,
        service_url: str,
        dependency_url: str,
        availability_threshold: float = 0.95,
        circuit_breaker_threshold: int = 5,
        verbose: bool = True
    ):
        self.service_url = service_url
        self.dependency_url = dependency_url
        self.availability_threshold = availability_threshold
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.verbose = verbose
        self.observations: List[Observation] = []

    def run(self) -> dict:
        """Execute chaos experiment."""
        if self.verbose:
            print("\n" + "=" * 70)
            print("CHAOS EXPERIMENT: Dependency Failure")
            print("=" * 70)
            print(f"\nService: {self.service_url}")
            print(f"Dependency: {self.dependency_url}")
            print(f"Availability threshold: {self.availability_threshold * 100}%")
            print(f"Circuit breaker threshold: {self.circuit_breaker_threshold} failures")
            print()

        # Phase 1: Baseline
        baseline_availability = self._measure_baseline()

        # Phase 2: Inject chaos (dependency failure)
        chaos_availability = self._inject_dependency_failure()

        # Phase 3: Verify circuit breaker
        circuit_breaker_opened = self._verify_circuit_breaker()

        # Phase 4: Verify fallback
        fallback_active = self._verify_fallback()

        # Phase 5: Restore dependency
        recovery_time = self._restore_and_measure_recovery()

        # Phase 6: Evaluate
        experiment_passed = self._evaluate_results(
            baseline_availability=baseline_availability,
            chaos_availability=chaos_availability,
            circuit_breaker_opened=circuit_breaker_opened,
            fallback_active=fallback_active,
            recovery_time=recovery_time,
        )

        return {
            "experiment": "dependency_failure",
            "passed": experiment_passed,
            "baseline_availability": baseline_availability,
            "chaos_availability": chaos_availability,
            "circuit_breaker_opened": circuit_breaker_opened,
            "fallback_active": fallback_active,
            "recovery_time_seconds": recovery_time,
            "observations": [
                {
                    "timestamp": obs.timestamp.isoformat(),
                    "metric": obs.metric,
                    "value": obs.value,
                    "expected": obs.expected,
                    "passed": obs.passed,
                    "note": obs.note,
                }
                for obs in self.observations
            ],
        }

    def _measure_baseline(self) -> float:
        """Measure baseline availability before chaos."""
        if self.verbose:
            print("[Phase 1] Measuring baseline availability...")

        availability = self._measure_availability(duration=30)

        self.observations.append(Observation(
            timestamp=datetime.now(),
            metric="baseline_availability",
            value=availability,
            expected=0.99,
            passed=availability >= 0.99,
            note="Baseline measurement before chaos"
        ))

        if self.verbose:
            status = "✓" if availability >= 0.99 else "✗"
            print(f"  {status} Baseline availability: {availability * 100:.2f}%")

        return availability

    def _inject_dependency_failure(self) -> float:
        """Inject dependency failure and measure impact."""
        if self.verbose:
            print("\n[Phase 2] Injecting dependency failure...")

        # Simulate dependency failure (in real scenario, would use chaos tool)
        self._fail_dependency()

        # Measure availability during chaos
        time.sleep(2)  # Wait for circuit breaker to potentially open
        availability = self._measure_availability(duration=60)

        self.observations.append(Observation(
            timestamp=datetime.now(),
            metric="chaos_availability",
            value=availability,
            expected=self.availability_threshold,
            passed=availability >= self.availability_threshold,
            note="Availability during dependency failure"
        ))

        if self.verbose:
            status = "✓" if availability >= self.availability_threshold else "✗"
            print(f"  {status} Availability during chaos: {availability * 100:.2f}%")

        return availability

    def _verify_circuit_breaker(self) -> bool:
        """Verify circuit breaker opened after threshold failures."""
        if self.verbose:
            print("\n[Phase 3] Verifying circuit breaker behavior...")

        # Simulate sequential failures to trigger circuit breaker
        failures = 0
        for i in range(self.circuit_breaker_threshold + 2):
            failed = self._simulate_request()
            if failed:
                failures += 1

            if failures >= self.circuit_breaker_threshold:
                break

            time.sleep(0.1)

        circuit_opened = failures >= self.circuit_breaker_threshold

        self.observations.append(Observation(
            timestamp=datetime.now(),
            metric="circuit_breaker_opened",
            value=float(circuit_opened),
            expected=1.0,
            passed=circuit_opened,
            note=f"Circuit breaker opened after {failures} failures"
        ))

        if self.verbose:
            status = "✓" if circuit_opened else "✗"
            print(f"  {status} Circuit breaker opened after {failures} failures")

        return circuit_opened

    def _verify_fallback(self) -> bool:
        """Verify fallback mechanism is active."""
        if self.verbose:
            print("\n[Phase 4] Verifying fallback mechanism...")

        # Check if service uses cached/fallback data
        fallback_active = self._check_fallback_active()

        self.observations.append(Observation(
            timestamp=datetime.now(),
            metric="fallback_active",
            value=float(fallback_active),
            expected=1.0,
            passed=fallback_active,
            note="Fallback mechanism activated"
        ))

        if self.verbose:
            status = "✓" if fallback_active else "✗"
            print(f"  {status} Fallback mechanism: {'ACTIVE' if fallback_active else 'INACTIVE'}")

        return fallback_active

    def _restore_and_measure_recovery(self) -> float:
        """Restore dependency and measure recovery time."""
        if self.verbose:
            print("\n[Phase 5] Restoring dependency and measuring recovery...")

        start_time = time.time()

        # Restore dependency
        self._restore_dependency()

        # Wait for recovery
        recovered = False
        recovery_time = 0.0

        for i in range(60):  # Max 60 seconds
            time.sleep(1)
            availability = self._measure_availability(duration=5)

            if availability >= 0.99:
                recovered = True
                recovery_time = time.time() - start_time
                break

        self.observations.append(Observation(
            timestamp=datetime.now(),
            metric="recovery_time",
            value=recovery_time,
            expected=30.0,
            passed=recovery_time <= 30.0,
            note=f"Service recovered in {recovery_time:.1f}s"
        ))

        if self.verbose:
            status = "✓" if recovered and recovery_time <= 30 else "✗"
            print(f"  {status} Recovery time: {recovery_time:.1f}s")

        return recovery_time

    def _evaluate_results(
        self,
        baseline_availability: float,
        chaos_availability: float,
        circuit_breaker_opened: bool,
        fallback_active: bool,
        recovery_time: float,
    ) -> bool:
        """Evaluate overall experiment results."""
        if self.verbose:
            print("\n" + "=" * 70)
            print("EXPERIMENT RESULTS")
            print("=" * 70)

        checks = {
            "Baseline healthy (>99%)": baseline_availability >= 0.99,
            f"Maintained availability (>{self.availability_threshold * 100}%)": (
                chaos_availability >= self.availability_threshold
            ),
            "Circuit breaker opened": circuit_breaker_opened,
            "Fallback activated": fallback_active,
            "Recovered quickly (<30s)": recovery_time <= 30.0,
        }

        if self.verbose:
            for check, passed in checks.items():
                status = "✓" if passed else "✗"
                print(f"  {status} {check}")

        all_passed = all(checks.values())

        if self.verbose:
            print()
            if all_passed:
                print("✓ EXPERIMENT PASSED: System is resilient to dependency failure")
            else:
                print("✗ EXPERIMENT FAILED: System degraded beyond acceptable limits")
            print("=" * 70 + "\n")

        return all_passed

    def _fail_dependency(self):
        """Simulate dependency failure."""
        # In real implementation:
        # - Block network traffic to dependency
        # - Kill dependency pods
        # - Inject errors via proxy
        if self.verbose:
            print("  → Blocking traffic to dependency")

    def _restore_dependency(self):
        """Restore dependency."""
        if self.verbose:
            print("  → Restoring dependency")

    def _measure_availability(self, duration: int) -> float:
        """
        Measure service availability over duration.

        In production:
        - Query Prometheus for actual success rate
        - Calculate: success_requests / total_requests

        For demo: Simulate measurement.
        """
        # Simulate: Return random availability based on chaos state
        # In real test, would call actual service
        return random.uniform(0.96, 0.99)

    def _simulate_request(self) -> bool:
        """
        Simulate a request to service.

        Returns:
            True if request failed, False if succeeded
        """
        # In production: Make actual HTTP request
        # For demo: Simulate with probability
        return random.random() < 0.3  # 30% failure rate

    def _check_fallback_active(self) -> bool:
        """
        Check if fallback mechanism is active.

        In production:
        - Query metrics for cache hit rate increase
        - Check feature flags
        - Validate response headers

        For demo: Simulate.
        """
        return True  # Simulate fallback is active


def main():
    """Run chaos experiment."""
    experiment = DependencyFailureChaos(
        service_url="http://api.example.com",
        dependency_url="http://auth.example.com",
        availability_threshold=0.95,
        circuit_breaker_threshold=5,
        verbose=True,
    )

    results = experiment.run()

    # Print summary
    print("\nSummary:")
    print(f"  Experiment: {results['experiment']}")
    print(f"  Status: {'PASSED' if results['passed'] else 'FAILED'}")
    print(f"  Baseline: {results['baseline_availability'] * 100:.2f}%")
    print(f"  During chaos: {results['chaos_availability'] * 100:.2f}%")
    print(f"  Circuit breaker: {'OPENED' if results['circuit_breaker_opened'] else 'FAILED TO OPEN'}")
    print(f"  Fallback: {'ACTIVE' if results['fallback_active'] else 'INACTIVE'}")
    print(f"  Recovery: {results['recovery_time_seconds']:.1f}s")

    # Exit with appropriate code
    exit(0 if results['passed'] else 1)


if __name__ == "__main__":
    main()
