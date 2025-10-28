#!/usr/bin/env python3
"""
SLO Error Budget Calculator

Calculate error budgets from SLOs, track burn rate, predict budget exhaustion,
and generate alerts. Supports multiple SLI types including availability, latency,
and throughput.

Usage:
    calculate_slo_budget.py --slo 99.9 --window 30
    calculate_slo_budget.py --config slo-config.yaml --json
    calculate_slo_budget.py --calculate-burn-rate --current-consumption 0.15
    calculate_slo_budget.py --predict-exhaustion --consumption 0.35 --elapsed-hours 360
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import yaml


class SLIType(Enum):
    """Types of Service Level Indicators."""
    AVAILABILITY = "availability"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    FRESHNESS = "freshness"
    CORRECTNESS = "correctness"


class BurnRateLevel(Enum):
    """Error budget burn rate severity levels."""
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


class WindowType(Enum):
    """SLO measurement window types."""
    ROLLING = "rolling"
    CALENDAR = "calendar"
    REQUEST_BASED = "request_based"


@dataclass
class SLODefinition:
    """Service Level Objective definition."""
    name: str
    sli_type: SLIType
    target: float  # 0-1 (e.g., 0.999 for 99.9%)
    window_days: int
    window_type: WindowType
    description: str


@dataclass
class ErrorBudget:
    """Error budget calculation results."""
    slo_name: str
    slo_target: float
    window_days: int
    total_budget_minutes: float
    consumed_minutes: float
    remaining_minutes: float
    consumption_percent: float
    status: str
    time_remaining_days: float


@dataclass
class BurnRateAlert:
    """Error budget burn rate alert."""
    level: BurnRateLevel
    burn_rate: float
    window: str
    threshold: float
    message: str
    should_page: bool
    runbook_url: Optional[str] = None


@dataclass
class BudgetPrediction:
    """Error budget exhaustion prediction."""
    will_exhaust: bool
    hours_until_exhaustion: Optional[float]
    exhaustion_date: Optional[str]
    current_burn_rate: float
    recommendation: str


@dataclass
class MultiWindowSLO:
    """Multi-window SLO configuration."""
    service: str
    sli_type: SLIType
    windows: List[Dict[str, Any]]


class SLOCalculator:
    """Calculate and analyze SLO error budgets."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def calculate_time_based_budget(
        self,
        slo_target: float,
        window_days: int,
        current_availability: Optional[float] = None
    ) -> ErrorBudget:
        """
        Calculate error budget for time-based SLO.

        Args:
            slo_target: Target SLO (e.g., 0.999 for 99.9%)
            window_days: Window size in days
            current_availability: Current measured availability (optional)

        Returns:
            ErrorBudget with calculation results
        """
        if not 0 < slo_target < 1:
            raise ValueError("SLO target must be between 0 and 1")

        # Calculate total budget
        total_minutes = window_days * 24 * 60
        budget_minutes = total_minutes * (1 - slo_target)

        # Calculate consumption if current availability provided
        if current_availability is not None:
            if current_availability > slo_target:
                consumed_minutes = 0
                consumption_percent = 0
            else:
                downtime = 1 - current_availability
                consumed_minutes = total_minutes * downtime
                consumption_percent = (consumed_minutes / budget_minutes) * 100
        else:
            consumed_minutes = 0
            consumption_percent = 0

        remaining_minutes = budget_minutes - consumed_minutes
        status = self._determine_budget_status(consumption_percent)
        time_remaining_days = remaining_minutes / (24 * 60)

        return ErrorBudget(
            slo_name="time_based_slo",
            slo_target=slo_target,
            window_days=window_days,
            total_budget_minutes=budget_minutes,
            consumed_minutes=consumed_minutes,
            remaining_minutes=remaining_minutes,
            consumption_percent=consumption_percent,
            status=status,
            time_remaining_days=time_remaining_days,
        )

    def calculate_request_based_budget(
        self,
        slo_target: float,
        total_requests: int,
        failed_requests: int
    ) -> Dict[str, Any]:
        """
        Calculate error budget for request-based SLO.

        Args:
            slo_target: Target success rate (e.g., 0.999)
            total_requests: Total requests in window
            failed_requests: Number of failed requests

        Returns:
            Error budget calculation results
        """
        if total_requests == 0:
            return {
                "error": "No requests in window",
                "total_requests": 0,
                "failed_requests": 0,
                "budget_consumption": 0,
            }

        # Calculate current success rate
        current_success_rate = (total_requests - failed_requests) / total_requests

        # Calculate budget
        allowed_failures = total_requests * (1 - slo_target)
        remaining_failures = allowed_failures - failed_requests
        consumption_percent = (failed_requests / allowed_failures) * 100

        status = self._determine_budget_status(consumption_percent)

        return {
            "slo_target": slo_target,
            "total_requests": total_requests,
            "failed_requests": failed_requests,
            "current_success_rate": current_success_rate,
            "allowed_failures": allowed_failures,
            "remaining_failures": max(0, remaining_failures),
            "consumption_percent": consumption_percent,
            "status": status,
        }

    def calculate_latency_budget(
        self,
        slo_target_ms: float,
        percentile: int,
        current_latency_ms: float,
        window_days: int
    ) -> Dict[str, Any]:
        """
        Calculate error budget for latency-based SLO.

        Args:
            slo_target_ms: Target latency in milliseconds
            percentile: Percentile (e.g., 95 for p95)
            current_latency_ms: Current measured latency
            window_days: Window size in days

        Returns:
            Latency budget analysis
        """
        # For latency, "budget" is how much we can exceed target
        # Calculate based on deviation from target
        if current_latency_ms <= slo_target_ms:
            consumption_percent = 0
            status = "healthy"
        else:
            # Simple model: consumption proportional to excess latency
            excess = current_latency_ms - slo_target_ms
            # Allow up to 50% excess before full budget consumption
            consumption_percent = min((excess / (slo_target_ms * 0.5)) * 100, 100)
            status = self._determine_budget_status(consumption_percent)

        return {
            "slo_target_ms": slo_target_ms,
            "percentile": percentile,
            "current_latency_ms": current_latency_ms,
            "within_slo": current_latency_ms <= slo_target_ms,
            "excess_ms": max(0, current_latency_ms - slo_target_ms),
            "consumption_percent": consumption_percent,
            "status": status,
            "window_days": window_days,
        }

    def calculate_burn_rate(
        self,
        error_budget_consumed: float,
        time_elapsed_hours: float,
        window_hours: float
    ) -> float:
        """
        Calculate error budget burn rate.

        Args:
            error_budget_consumed: Fraction of budget consumed (0-1)
            time_elapsed_hours: Hours elapsed in window
            window_hours: Total window duration in hours

        Returns:
            Burn rate multiplier (1.0 = normal, > 1.0 = burning fast)
        """
        if time_elapsed_hours == 0:
            return 0.0

        expected_consumption = time_elapsed_hours / window_hours
        if expected_consumption == 0:
            return 0.0

        burn_rate = error_budget_consumed / expected_consumption
        return burn_rate

    def generate_burn_rate_alerts(
        self,
        burn_rate: float,
        time_window_hours: float
    ) -> List[BurnRateAlert]:
        """
        Generate burn rate alerts based on multi-window burn rate.

        Uses Google SRE multi-window multi-burn-rate alerting:
        - Fast burn: 14.4x over 1 hour (5% budget in 1 hour)
        - Medium burn: 6x over 6 hours (5% budget in 6 hours)
        - Slow burn: 3x over 24 hours (5% budget in 24 hours)

        Args:
            burn_rate: Current burn rate multiplier
            time_window_hours: Time window for measurement

        Returns:
            List of applicable alerts
        """
        alerts = []

        # Define thresholds based on window
        if time_window_hours <= 1.5:
            # Fast burn window (1 hour)
            if burn_rate > 14.4:
                alerts.append(BurnRateAlert(
                    level=BurnRateLevel.CRITICAL,
                    burn_rate=burn_rate,
                    window="1h",
                    threshold=14.4,
                    message=f"CRITICAL: Fast burn rate {burn_rate:.1f}x (threshold 14.4x)",
                    should_page=True,
                    runbook_url="https://runbooks/slo-fast-burn",
                ))

        elif time_window_hours <= 8:
            # Medium burn window (6 hours)
            if burn_rate > 6.0:
                alerts.append(BurnRateAlert(
                    level=BurnRateLevel.HIGH,
                    burn_rate=burn_rate,
                    window="6h",
                    threshold=6.0,
                    message=f"HIGH: Medium burn rate {burn_rate:.1f}x (threshold 6x)",
                    should_page=True,
                    runbook_url="https://runbooks/slo-medium-burn",
                ))

        else:
            # Slow burn window (24 hours)
            if burn_rate > 3.0:
                alerts.append(BurnRateAlert(
                    level=BurnRateLevel.ELEVATED,
                    burn_rate=burn_rate,
                    window="24h",
                    threshold=3.0,
                    message=f"ELEVATED: Slow burn rate {burn_rate:.1f}x (threshold 3x)",
                    should_page=False,
                    runbook_url="https://runbooks/slo-slow-burn",
                ))
            elif burn_rate > 1.5:
                alerts.append(BurnRateAlert(
                    level=BurnRateLevel.NORMAL,
                    burn_rate=burn_rate,
                    window="24h",
                    threshold=1.5,
                    message=f"INFO: Elevated burn rate {burn_rate:.1f}x",
                    should_page=False,
                ))

        return alerts

    def predict_budget_exhaustion(
        self,
        current_consumption: float,
        time_elapsed_hours: float,
        window_hours: float
    ) -> BudgetPrediction:
        """
        Predict when error budget will be exhausted.

        Args:
            current_consumption: Current budget consumption (0-1)
            time_elapsed_hours: Hours elapsed in window
            window_hours: Total window duration

        Returns:
            Budget exhaustion prediction
        """
        if time_elapsed_hours == 0:
            return BudgetPrediction(
                will_exhaust=False,
                hours_until_exhaustion=None,
                exhaustion_date=None,
                current_burn_rate=0.0,
                recommendation="Insufficient data for prediction",
            )

        # Calculate current burn rate
        burn_rate = current_consumption / time_elapsed_hours
        remaining_budget = 1.0 - current_consumption

        if burn_rate <= 0:
            return BudgetPrediction(
                will_exhaust=False,
                hours_until_exhaustion=None,
                exhaustion_date=None,
                current_burn_rate=0.0,
                recommendation="Budget not being consumed",
            )

        # Calculate hours until exhaustion
        hours_until_exhaustion = remaining_budget / burn_rate

        # Check if will exhaust within window
        will_exhaust = hours_until_exhaustion <= (window_hours - time_elapsed_hours)

        exhaustion_date = None
        if will_exhaust:
            exhaustion_datetime = datetime.now() + timedelta(hours=hours_until_exhaustion)
            exhaustion_date = exhaustion_datetime.isoformat()

        # Generate recommendation
        if will_exhaust:
            if hours_until_exhaustion < 24:
                recommendation = "URGENT: Budget will exhaust within 24 hours. Implement feature freeze and focus on reliability."
            elif hours_until_exhaustion < 72:
                recommendation = "WARNING: Budget will exhaust within 3 days. Defer non-critical changes and prioritize stability."
            else:
                recommendation = "CAUTION: Budget trending toward exhaustion. Monitor closely and consider reliability improvements."
        else:
            if current_consumption < 0.5:
                recommendation = "HEALTHY: Budget consumption normal. Continue standard operations."
            elif current_consumption < 0.75:
                recommendation = "MONITORING: Budget consumption elevated. Increase monitoring and risk assessment."
            else:
                recommendation = "ATTENTION: High budget consumption. Consider deferring risky changes."

        return BudgetPrediction(
            will_exhaust=will_exhaust,
            hours_until_exhaustion=hours_until_exhaustion if will_exhaust else None,
            exhaustion_date=exhaustion_date,
            current_burn_rate=burn_rate,
            recommendation=recommendation,
        )

    def calculate_multi_window_slo(
        self,
        config: MultiWindowSLO,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate SLO across multiple time windows.

        Args:
            config: Multi-window SLO configuration
            metrics: Metrics for each window

        Returns:
            Multi-window SLO analysis
        """
        results = {
            "service": config.service,
            "sli_type": config.sli_type.value,
            "windows": [],
            "overall_status": "healthy",
        }

        for window in config.windows:
            window_duration = window["duration"]
            target = window["target"]
            window_metrics = metrics.get(window_duration, {})

            current = window_metrics.get("current", target)
            met = current >= target

            # Calculate budget remaining
            if current >= target:
                budget_remaining = 1.0  # Fully within budget
            else:
                budget_used = target - current
                budget_total = 1 - target
                budget_remaining = 1 - (budget_used / budget_total)

            window_result = {
                "duration": window_duration,
                "target": target,
                "current": current,
                "met": met,
                "budget_remaining": budget_remaining,
                "alert_level": window.get("alert", "none") if not met else "none",
            }

            results["windows"].append(window_result)

            # Update overall status
            if not met:
                if window.get("alert") == "page":
                    results["overall_status"] = "critical"
                elif results["overall_status"] == "healthy":
                    results["overall_status"] = "warning"

        return results

    def calculate_composite_error_budget(
        self,
        slis: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Calculate composite error budget across multiple SLIs.

        Args:
            slis: Dictionary of SLI data with current, target, and weight

        Example:
            {
                "availability": {"current": 0.9995, "target": 0.999, "weight": 0.6},
                "latency": {"current": 0.998, "target": 0.995, "weight": 0.4},
            }

        Returns:
            Composite budget calculation
        """
        total_budget_consumed = 0.0
        sli_details = []

        for sli_name, sli_data in slis.items():
            current = sli_data["current"]
            target = sli_data["target"]
            weight = sli_data["weight"]

            # Calculate consumption for this SLI
            if current >= target:
                consumption = 0.0
                status = "healthy"
            else:
                budget = 1 - target
                used = target - current
                consumption = min(used / budget, 1.0)  # Cap at 100%
                status = self._determine_budget_status(consumption * 100)

            # Weight the consumption
            weighted_consumption = consumption * weight
            total_budget_consumed += weighted_consumption

            sli_details.append({
                "name": sli_name,
                "current": current,
                "target": target,
                "weight": weight,
                "consumption": consumption,
                "weighted_consumption": weighted_consumption,
                "status": status,
            })

        # Cap total at 100%
        total_budget_consumed = min(total_budget_consumed, 1.0)
        overall_status = self._determine_budget_status(total_budget_consumed * 100)

        return {
            "total_consumption": total_budget_consumed,
            "total_consumption_percent": total_budget_consumed * 100,
            "overall_status": overall_status,
            "sli_breakdown": sli_details,
        }

    def _determine_budget_status(self, consumption_percent: float) -> str:
        """Determine budget health status based on consumption."""
        if consumption_percent < 25:
            return "healthy"
        elif consumption_percent < 50:
            return "concerning"
        elif consumption_percent < 75:
            return "critical"
        else:
            return "exhausted"

    def generate_budget_report(
        self,
        slo_name: str,
        budget: ErrorBudget,
        burn_rate: Optional[float] = None,
        prediction: Optional[BudgetPrediction] = None
    ) -> str:
        """Generate human-readable error budget report."""
        report = [
            f"\n{'=' * 60}",
            f"Error Budget Report: {slo_name}",
            f"{'=' * 60}",
            f"\nSLO Target: {budget.slo_target * 100:.3f}%",
            f"Window: {budget.window_days} days",
            f"\nError Budget:",
            f"  Total: {budget.total_budget_minutes:.2f} minutes",
            f"  Consumed: {budget.consumed_minutes:.2f} minutes",
            f"  Remaining: {budget.remaining_minutes:.2f} minutes",
            f"  Consumption: {budget.consumption_percent:.2f}%",
            f"\nStatus: {budget.status.upper()}",
        ]

        if burn_rate is not None:
            report.extend([
                f"\nBurn Rate: {burn_rate:.2f}x",
                f"  Normal burn rate is 1.0x",
                f"  Current rate: {'ELEVATED' if burn_rate > 1.5 else 'NORMAL'}",
            ])

        if prediction is not None:
            report.append(f"\nPrediction:")
            if prediction.will_exhaust:
                report.extend([
                    f"  Will exhaust: YES",
                    f"  Hours until exhaustion: {prediction.hours_until_exhaustion:.1f}",
                    f"  Exhaustion date: {prediction.exhaustion_date}",
                ])
            else:
                report.append(f"  Will exhaust: NO (current trajectory)")

            report.append(f"  Recommendation: {prediction.recommendation}")

        report.append(f"\n{'=' * 60}\n")
        return "\n".join(report)


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load SLO configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate SLO error budgets and analyze burn rates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate basic error budget
  %(prog)s --slo 99.9 --window 30

  # Calculate with current availability
  %(prog)s --slo 99.95 --window 30 --current-availability 99.85

  # Calculate burn rate
  %(prog)s --calculate-burn-rate --current-consumption 0.15 --elapsed-hours 360 --window-hours 720

  # Predict exhaustion
  %(prog)s --predict-exhaustion --consumption 0.35 --elapsed-hours 360 --window-hours 720

  # Load from config file
  %(prog)s --config slo-config.yaml --json

  # Request-based budget
  %(prog)s --request-based --total 1000000 --failed 1500 --target 99.9

  # Latency budget
  %(prog)s --latency-budget --target-ms 200 --current-ms 180 --percentile 95
        """
    )

    # Basic SLO parameters
    parser.add_argument(
        "--slo",
        type=float,
        help="SLO target percentage (e.g., 99.9 for 99.9%%)"
    )
    parser.add_argument(
        "--window",
        type=int,
        default=30,
        help="SLO window in days (default: 30)"
    )
    parser.add_argument(
        "--current-availability",
        type=float,
        help="Current measured availability percentage"
    )

    # Request-based budget
    parser.add_argument(
        "--request-based",
        action="store_true",
        help="Calculate request-based budget"
    )
    parser.add_argument(
        "--total",
        type=int,
        help="Total requests in window"
    )
    parser.add_argument(
        "--failed",
        type=int,
        help="Failed requests"
    )
    parser.add_argument(
        "--target",
        type=float,
        help="Target success rate percentage"
    )

    # Latency budget
    parser.add_argument(
        "--latency-budget",
        action="store_true",
        help="Calculate latency budget"
    )
    parser.add_argument(
        "--target-ms",
        type=float,
        help="Target latency in milliseconds"
    )
    parser.add_argument(
        "--current-ms",
        type=float,
        help="Current latency in milliseconds"
    )
    parser.add_argument(
        "--percentile",
        type=int,
        default=95,
        help="Latency percentile (default: 95)"
    )

    # Burn rate calculation
    parser.add_argument(
        "--calculate-burn-rate",
        action="store_true",
        help="Calculate error budget burn rate"
    )
    parser.add_argument(
        "--current-consumption",
        type=float,
        help="Current budget consumption (0-1)"
    )
    parser.add_argument(
        "--elapsed-hours",
        type=float,
        help="Hours elapsed in window"
    )
    parser.add_argument(
        "--window-hours",
        type=float,
        help="Total window duration in hours"
    )

    # Prediction
    parser.add_argument(
        "--predict-exhaustion",
        action="store_true",
        help="Predict when budget will be exhausted"
    )
    parser.add_argument(
        "--consumption",
        type=float,
        help="Current budget consumption (0-1)"
    )

    # Configuration
    parser.add_argument(
        "--config",
        help="Load configuration from YAML file"
    )

    # Output
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

    calculator = SLOCalculator(verbose=args.verbose)

    try:
        result = {}

        # Load from config file
        if args.config:
            config = load_config_file(args.config)

            if "slo_target" in config:
                budget = calculator.calculate_time_based_budget(
                    slo_target=config["slo_target"] / 100,
                    window_days=config.get("window_days", 30),
                    current_availability=config.get("current_availability", None)
                    and config["current_availability"] / 100
                )
                result["error_budget"] = asdict(budget)

            if "burn_rate" in config:
                burn_rate = calculator.calculate_burn_rate(
                    error_budget_consumed=config["burn_rate"]["consumption"],
                    time_elapsed_hours=config["burn_rate"]["elapsed_hours"],
                    window_hours=config["burn_rate"]["window_hours"],
                )
                result["burn_rate"] = burn_rate

                alerts = calculator.generate_burn_rate_alerts(
                    burn_rate=burn_rate,
                    time_window_hours=config["burn_rate"]["elapsed_hours"],
                )
                result["alerts"] = [asdict(a) for a in alerts]

        # Calculate time-based budget
        elif args.slo is not None:
            slo_target = args.slo / 100
            current_availability = None
            if args.current_availability is not None:
                current_availability = args.current_availability / 100

            budget = calculator.calculate_time_based_budget(
                slo_target=slo_target,
                window_days=args.window,
                current_availability=current_availability,
            )

            if args.json:
                result = asdict(budget)
            else:
                report = calculator.generate_budget_report("SLO", budget)
                print(report)
                sys.exit(0)

        # Calculate request-based budget
        elif args.request_based:
            if not all([args.total, args.failed, args.target]):
                parser.error("--request-based requires --total, --failed, and --target")

            result = calculator.calculate_request_based_budget(
                slo_target=args.target / 100,
                total_requests=args.total,
                failed_requests=args.failed,
            )

        # Calculate latency budget
        elif args.latency_budget:
            if not all([args.target_ms, args.current_ms]):
                parser.error("--latency-budget requires --target-ms and --current-ms")

            result = calculator.calculate_latency_budget(
                slo_target_ms=args.target_ms,
                percentile=args.percentile,
                current_latency_ms=args.current_ms,
                window_days=args.window,
            )

        # Calculate burn rate
        elif args.calculate_burn_rate:
            if not all([args.current_consumption, args.elapsed_hours, args.window_hours]):
                parser.error(
                    "--calculate-burn-rate requires --current-consumption, "
                    "--elapsed-hours, and --window-hours"
                )

            burn_rate = calculator.calculate_burn_rate(
                error_budget_consumed=args.current_consumption,
                time_elapsed_hours=args.elapsed_hours,
                window_hours=args.window_hours,
            )

            alerts = calculator.generate_burn_rate_alerts(
                burn_rate=burn_rate,
                time_window_hours=args.elapsed_hours,
            )

            result = {
                "burn_rate": burn_rate,
                "alerts": [asdict(alert) for alert in alerts],
            }

        # Predict exhaustion
        elif args.predict_exhaustion:
            if not all([args.consumption, args.elapsed_hours, args.window_hours]):
                parser.error(
                    "--predict-exhaustion requires --consumption, "
                    "--elapsed-hours, and --window-hours"
                )

            prediction = calculator.predict_budget_exhaustion(
                current_consumption=args.consumption,
                time_elapsed_hours=args.elapsed_hours,
                window_hours=args.window_hours,
            )

            result = asdict(prediction)

        else:
            parser.error("Must specify one of: --slo, --request-based, --latency-budget, "
                        "--calculate-burn-rate, --predict-exhaustion, or --config")

        # Output result
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            # Pretty print result
            print(yaml.dump(result, default_flow_style=False))

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
