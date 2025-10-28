#!/usr/bin/env python3
"""
Toil Analysis and Automation ROI Calculator

Identify toil from logs and tickets, categorize work types, measure automation ROI,
prioritize automation candidates, and track toil reduction over time.

Usage:
    analyze_toil.py --work-logs work.jsonl --analyze
    analyze_toil.py --work-logs work.jsonl --automation-candidates --top 10 --json
    analyze_toil.py --track-toil --days 30 --report
    analyze_toil.py --calculate-roi --task "Manual deployments" --frequency 50 --duration 0.5
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any
from collections import defaultdict
import statistics


class WorkType(Enum):
    """Categories of work."""
    TOIL = "toil"
    ENGINEERING = "engineering"
    INCIDENT = "incident"
    MEETING = "meeting"
    ONCALL = "oncall"
    UNKNOWN = "unknown"


class ToilCategory(Enum):
    """Subcategories of toil."""
    MANUAL_DEPLOYMENT = "manual_deployment"
    MANUAL_REMEDIATION = "manual_remediation"
    MANUAL_SCALING = "manual_scaling"
    LOG_ANALYSIS = "log_analysis"
    ALERT_RESPONSE = "alert_response"
    MANUAL_TESTING = "manual_testing"
    DATA_MIGRATION = "data_migration"
    MANUAL_CONFIGURATION = "manual_configuration"
    FILE_OPERATIONS = "file_operations"
    OTHER = "other"


@dataclass
class WorkLog:
    """Work log entry."""
    timestamp: datetime
    duration_hours: float
    work_type: WorkType
    category: Optional[ToilCategory]
    description: str
    automatable: bool
    automated: bool
    repetitive: bool
    engineer: str


@dataclass
class ToilMetrics:
    """Toil metrics for a time period."""
    total_hours: float
    toil_hours: float
    engineering_hours: float
    toil_percentage: float
    top_toil_categories: List[Dict[str, Any]]
    engineers_affected: int
    period_days: int


@dataclass
class AutomationCandidate:
    """Automation opportunity candidate."""
    task: str
    category: ToilCategory
    occurrences: int
    total_hours: float
    monthly_hours: float
    annual_hours: float
    automation_cost_hours: float
    payback_months: float
    roi: float
    priority: str
    automatable: bool
    already_automated: bool


@dataclass
class AutomationROI:
    """Automation return on investment calculation."""
    task: str
    frequency_per_month: int
    duration_hours: float
    monthly_cost_hours: float
    annual_cost_hours: float
    automation_effort_hours: float
    payback_months: float
    roi_3_year: float
    decision: str
    reasoning: str


@dataclass
class ToilTrend:
    """Toil trend over time."""
    period: str
    toil_percentage: float
    toil_hours: float
    total_hours: float
    change_from_previous: Optional[float]


class ToilAnalyzer:
    """Analyze toil and identify automation opportunities."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.work_logs: List[WorkLog] = []

    def load_work_logs(self, logs_data: List[Dict[str, Any]]):
        """Load work logs from data."""
        for log_data in logs_data:
            # Parse timestamp
            if isinstance(log_data["timestamp"], str):
                timestamp = datetime.fromisoformat(log_data["timestamp"])
            else:
                timestamp = log_data["timestamp"]

            # Parse enums
            work_type = WorkType(log_data["work_type"])
            category = None
            if log_data.get("category"):
                category = ToilCategory(log_data["category"])

            work_log = WorkLog(
                timestamp=timestamp,
                duration_hours=log_data["duration_hours"],
                work_type=work_type,
                category=category,
                description=log_data["description"],
                automatable=log_data.get("automatable", False),
                automated=log_data.get("automated", False),
                repetitive=log_data.get("repetitive", False),
                engineer=log_data.get("engineer", "unknown"),
            )
            self.work_logs.append(work_log)

    def calculate_toil_metrics(self, days: int = 30) -> ToilMetrics:
        """
        Calculate toil metrics for recent period.

        Args:
            days: Number of days to analyze

        Returns:
            ToilMetrics with analysis
        """
        cutoff = datetime.now() - timedelta(days=days)
        recent_logs = [log for log in self.work_logs if log.timestamp >= cutoff]

        if not recent_logs:
            return ToilMetrics(
                total_hours=0,
                toil_hours=0,
                engineering_hours=0,
                toil_percentage=0,
                top_toil_categories=[],
                engineers_affected=0,
                period_days=days,
            )

        # Calculate totals
        total_hours = sum(log.duration_hours for log in recent_logs)
        toil_hours = sum(
            log.duration_hours for log in recent_logs
            if log.work_type == WorkType.TOIL
        )
        engineering_hours = sum(
            log.duration_hours for log in recent_logs
            if log.work_type == WorkType.ENGINEERING
        )

        toil_percentage = (toil_hours / total_hours * 100) if total_hours > 0 else 0

        # Categorize toil
        toil_by_category = defaultdict(float)
        for log in recent_logs:
            if log.work_type == WorkType.TOIL and log.category:
                toil_by_category[log.category.value] += log.duration_hours

        # Sort by hours
        top_categories = [
            {"category": cat, "hours": hours}
            for cat, hours in sorted(
                toil_by_category.items(),
                key=lambda x: x[1],
                reverse=True
            )
        ]

        # Count unique engineers
        engineers = set(log.engineer for log in recent_logs)

        return ToilMetrics(
            total_hours=total_hours,
            toil_hours=toil_hours,
            engineering_hours=engineering_hours,
            toil_percentage=toil_percentage,
            top_toil_categories=top_categories,
            engineers_affected=len(engineers),
            period_days=days,
        )

    def identify_automation_candidates(
        self,
        min_occurrences: int = 3,
        automation_cost_hours: float = 40
    ) -> List[AutomationCandidate]:
        """
        Identify high-impact automation opportunities.

        Args:
            min_occurrences: Minimum occurrences to consider
            automation_cost_hours: Estimated hours to automate

        Returns:
            List of automation candidates sorted by ROI
        """
        toil_logs = [log for log in self.work_logs if log.work_type == WorkType.TOIL]

        if not toil_logs:
            return []

        # Group by description (task)
        task_frequency = defaultdict(lambda: {
            "count": 0,
            "total_hours": 0,
            "category": None,
            "automatable": False,
            "automated": False,
        })

        for log in toil_logs:
            task_frequency[log.description]["count"] += 1
            task_frequency[log.description]["total_hours"] += log.duration_hours
            task_frequency[log.description]["category"] = log.category
            task_frequency[log.description]["automatable"] = log.automatable
            task_frequency[log.description]["automated"] = log.automated

        # Calculate ROI for each task
        candidates = []
        total_days = (
            (max(log.timestamp for log in toil_logs) -
             min(log.timestamp for log in toil_logs)).days
            if len(toil_logs) > 1 else 30
        )
        total_days = max(total_days, 1)

        for task, stats in task_frequency.items():
            if stats["count"] < min_occurrences:
                continue

            # Calculate monthly and annual hours
            monthly_hours = (stats["total_hours"] / total_days) * 30
            annual_hours = monthly_hours * 12

            # Calculate payback period
            if monthly_hours > 0:
                payback_months = automation_cost_hours / monthly_hours
            else:
                payback_months = float('inf')

            # Calculate ROI (3-year horizon)
            roi = (annual_hours * 3) / automation_cost_hours if automation_cost_hours > 0 else 0

            # Determine priority
            priority = self._calculate_priority(
                payback_months=payback_months,
                roi=roi,
                automatable=stats["automatable"],
                automated=stats["automated"],
            )

            candidate = AutomationCandidate(
                task=task,
                category=stats["category"] or ToilCategory.OTHER,
                occurrences=stats["count"],
                total_hours=stats["total_hours"],
                monthly_hours=monthly_hours,
                annual_hours=annual_hours,
                automation_cost_hours=automation_cost_hours,
                payback_months=payback_months,
                roi=roi,
                priority=priority,
                automatable=stats["automatable"],
                already_automated=stats["automated"],
            )
            candidates.append(candidate)

        # Sort by ROI (descending)
        candidates.sort(key=lambda c: c.roi, reverse=True)
        return candidates

    def calculate_automation_roi(
        self,
        task: str,
        frequency_per_month: int,
        duration_hours: float,
        automation_effort_hours: float,
        complexity: str = "medium"
    ) -> AutomationROI:
        """
        Calculate ROI for automating a specific task.

        Args:
            task: Task description
            frequency_per_month: How often task occurs per month
            duration_hours: How long task takes
            automation_effort_hours: Estimated automation effort
            complexity: Task complexity (simple, medium, complex)

        Returns:
            AutomationROI with decision recommendation
        """
        # Calculate costs
        monthly_cost = frequency_per_month * duration_hours
        annual_cost = monthly_cost * 12

        # Calculate payback
        if monthly_cost > 0:
            payback_months = automation_effort_hours / monthly_cost
        else:
            payback_months = float('inf')

        # Calculate 3-year ROI
        three_year_savings = annual_cost * 3
        roi_3_year = three_year_savings / automation_effort_hours if automation_effort_hours > 0 else 0

        # Make decision
        decision, reasoning = self._make_automation_decision(
            payback_months=payback_months,
            roi=roi_3_year,
            frequency=frequency_per_month,
            complexity=complexity,
        )

        return AutomationROI(
            task=task,
            frequency_per_month=frequency_per_month,
            duration_hours=duration_hours,
            monthly_cost_hours=monthly_cost,
            annual_cost_hours=annual_cost,
            automation_effort_hours=automation_effort_hours,
            payback_months=payback_months,
            roi_3_year=roi_3_year,
            decision=decision,
            reasoning=reasoning,
        )

    def track_toil_trend(self, period_days: int = 7) -> List[ToilTrend]:
        """
        Track toil percentage over time.

        Args:
            period_days: Size of each period in days

        Returns:
            List of ToilTrend showing changes over time
        """
        if not self.work_logs:
            return []

        # Find date range
        min_date = min(log.timestamp for log in self.work_logs)
        max_date = max(log.timestamp for log in self.work_logs)

        # Create periods
        trends = []
        current_date = min_date
        previous_percentage = None

        while current_date < max_date:
            period_end = current_date + timedelta(days=period_days)

            # Filter logs for this period
            period_logs = [
                log for log in self.work_logs
                if current_date <= log.timestamp < period_end
            ]

            if period_logs:
                total_hours = sum(log.duration_hours for log in period_logs)
                toil_hours = sum(
                    log.duration_hours for log in period_logs
                    if log.work_type == WorkType.TOIL
                )
                toil_percentage = (toil_hours / total_hours * 100) if total_hours > 0 else 0

                # Calculate change
                change = None
                if previous_percentage is not None:
                    change = toil_percentage - previous_percentage

                trends.append(ToilTrend(
                    period=current_date.strftime("%Y-%m-%d"),
                    toil_percentage=toil_percentage,
                    toil_hours=toil_hours,
                    total_hours=total_hours,
                    change_from_previous=change,
                ))

                previous_percentage = toil_percentage

            current_date = period_end

        return trends

    def generate_toil_report(
        self,
        metrics: ToilMetrics,
        candidates: Optional[List[AutomationCandidate]] = None
    ) -> str:
        """Generate human-readable toil report."""
        report = [
            f"\n{'=' * 60}",
            f"Toil Analysis Report",
            f"{'=' * 60}",
            f"\nPeriod: Last {metrics.period_days} days",
            f"Engineers affected: {metrics.engineers_affected}",
            f"\nTime Allocation:",
            f"  Total hours: {metrics.total_hours:.1f}",
            f"  Toil hours: {metrics.toil_hours:.1f} ({metrics.toil_percentage:.1f}%)",
            f"  Engineering hours: {metrics.engineering_hours:.1f}",
            f"\nToil Status: {self._get_toil_status(metrics.toil_percentage)}",
        ]

        # Top categories
        if metrics.top_toil_categories:
            report.append(f"\nTop Toil Categories:")
            for i, cat in enumerate(metrics.top_toil_categories[:5], 1):
                report.append(
                    f"  {i}. {cat['category']}: {cat['hours']:.1f} hours"
                )

        # Automation candidates
        if candidates:
            report.extend([
                f"\n{'=' * 60}",
                f"Top Automation Candidates",
                f"{'=' * 60}",
            ])

            for i, candidate in enumerate(candidates[:10], 1):
                report.extend([
                    f"\n{i}. {candidate.task}",
                    f"   Priority: {candidate.priority}",
                    f"   Occurrences: {candidate.occurrences}",
                    f"   Annual hours: {candidate.annual_hours:.1f}",
                    f"   ROI: {candidate.roi:.1f}x (3-year)",
                    f"   Payback: {candidate.payback_months:.1f} months",
                ])

        report.append(f"\n{'=' * 60}\n")
        return "\n".join(report)

    def _calculate_priority(
        self,
        payback_months: float,
        roi: float,
        automatable: bool,
        automated: bool
    ) -> str:
        """Calculate automation priority."""
        if automated:
            return "DONE"
        if not automatable:
            return "NOT_AUTOMATABLE"
        if payback_months < 3:
            return "P0_IMMEDIATE"
        elif payback_months < 6 and roi > 3:
            return "P1_HIGH"
        elif payback_months < 12:
            return "P2_MEDIUM"
        else:
            return "P3_LOW"

    def _make_automation_decision(
        self,
        payback_months: float,
        roi: float,
        frequency: int,
        complexity: str
    ) -> tuple[str, str]:
        """Make automation decision with reasoning."""
        if payback_months < 3:
            return "AUTOMATE_NOW", "Quick payback (<3 months)"
        elif payback_months < 6 and roi > 3:
            return "AUTOMATE_NOW", "High ROI and reasonable payback"
        elif frequency > 20 and payback_months < 12:
            return "AUTOMATE_SOON", "High frequency justifies automation"
        elif payback_months < 12 and complexity == "simple":
            return "AUTOMATE_SOON", "Simple task with reasonable payback"
        elif roi > 2.0:
            return "CONSIDER", "Positive ROI but longer payback"
        else:
            return "DONT_AUTOMATE", "Low ROI or high complexity"

    def _get_toil_status(self, toil_percentage: float) -> str:
        """Get toil status description."""
        if toil_percentage < 25:
            return "EXCELLENT (< 25%)"
        elif toil_percentage < 40:
            return "GOOD (25-40%)"
        elif toil_percentage < 50:
            return "ACCEPTABLE (40-50%)"
        elif toil_percentage < 65:
            return "CONCERNING (50-65%)"
        else:
            return "CRITICAL (> 65%)"


def load_work_logs_file(file_path: str) -> List[Dict[str, Any]]:
    """Load work logs from JSONL file."""
    logs = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))
    return logs


def generate_sample_work_logs() -> List[Dict[str, Any]]:
    """Generate sample work logs for testing."""
    now = datetime.now()
    logs = []

    # Sample tasks
    tasks = [
        ("Manual deployment", ToilCategory.MANUAL_DEPLOYMENT, True, False, 30),
        ("Restart failed service", ToilCategory.MANUAL_REMEDIATION, True, False, 20),
        ("Manual scaling", ToilCategory.MANUAL_SCALING, True, False, 15),
        ("Analyze error logs", ToilCategory.LOG_ANALYSIS, True, False, 25),
        ("Respond to alerts", ToilCategory.ALERT_RESPONSE, True, True, 10),
        ("Code review", None, False, False, 0),  # Engineering, not toil
        ("Architecture design", None, False, False, 0),
    ]

    engineers = ["alice", "bob", "charlie"]

    for day in range(60):
        date = now - timedelta(days=day)

        for task, category, automatable, automated, frequency in tasks:
            # Determine if this task occurs today (probabilistic)
            import random
            if random.random() < (frequency / 100):
                duration = random.uniform(0.25, 2.0)

                work_type = WorkType.TOIL if category else WorkType.ENGINEERING

                logs.append({
                    "timestamp": date.isoformat(),
                    "duration_hours": duration,
                    "work_type": work_type.value,
                    "category": category.value if category else None,
                    "description": task,
                    "automatable": automatable,
                    "automated": automated,
                    "repetitive": True,
                    "engineer": random.choice(engineers),
                })

    return logs


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze toil and identify automation opportunities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze toil from work logs
  %(prog)s --work-logs work.jsonl --analyze --days 30

  # Find automation candidates
  %(prog)s --work-logs work.jsonl --automation-candidates --top 10

  # Calculate ROI for specific task
  %(prog)s --calculate-roi --task "Manual deployments" --frequency 50 --duration 0.5 --effort 40

  # Track toil trend
  %(prog)s --work-logs work.jsonl --track-toil --period 7 --json

  # Generate sample data
  %(prog)s --generate-sample --output work.jsonl
        """
    )

    # Input
    parser.add_argument(
        "--work-logs",
        help="Work logs file (JSONL format)"
    )
    parser.add_argument(
        "--generate-sample",
        action="store_true",
        help="Generate sample work logs"
    )
    parser.add_argument(
        "--output",
        help="Output file for generated samples"
    )

    # Analysis
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze toil metrics"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to analyze (default: 30)"
    )

    # Automation candidates
    parser.add_argument(
        "--automation-candidates",
        action="store_true",
        help="Identify automation candidates"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top candidates (default: 10)"
    )
    parser.add_argument(
        "--min-occurrences",
        type=int,
        default=3,
        help="Minimum occurrences to consider (default: 3)"
    )

    # ROI calculation
    parser.add_argument(
        "--calculate-roi",
        action="store_true",
        help="Calculate automation ROI"
    )
    parser.add_argument(
        "--task",
        help="Task description"
    )
    parser.add_argument(
        "--frequency",
        type=int,
        help="Task frequency per month"
    )
    parser.add_argument(
        "--duration",
        type=float,
        help="Task duration in hours"
    )
    parser.add_argument(
        "--effort",
        type=float,
        default=40,
        help="Automation effort in hours (default: 40)"
    )
    parser.add_argument(
        "--complexity",
        choices=["simple", "medium", "complex"],
        default="medium",
        help="Task complexity"
    )

    # Trend tracking
    parser.add_argument(
        "--track-toil",
        action="store_true",
        help="Track toil trend over time"
    )
    parser.add_argument(
        "--period",
        type=int,
        default=7,
        help="Period in days for trend tracking (default: 7)"
    )

    # Output
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate full report"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    analyzer = ToilAnalyzer(verbose=args.verbose)

    try:
        # Generate sample data
        if args.generate_sample:
            logs = generate_sample_work_logs()
            output_file = args.output or "work.jsonl"

            with open(output_file, 'w') as f:
                for log in logs:
                    f.write(json.dumps(log) + "\n")

            print(f"Generated {len(logs)} sample work logs → {output_file}")
            sys.exit(0)

        # Load work logs
        if args.work_logs:
            logs_data = load_work_logs_file(args.work_logs)
            analyzer.load_work_logs(logs_data)

            if args.verbose:
                print(f"Loaded {len(logs_data)} work logs", file=sys.stderr)

        # Analyze toil
        if args.analyze:
            metrics = analyzer.calculate_toil_metrics(days=args.days)

            if args.json:
                print(json.dumps(asdict(metrics), indent=2))
            else:
                report = analyzer.generate_toil_report(metrics)
                print(report)

        # Find automation candidates
        elif args.automation_candidates:
            if not args.work_logs:
                parser.error("--automation-candidates requires --work-logs")

            candidates = analyzer.identify_automation_candidates(
                min_occurrences=args.min_occurrences,
            )

            # Limit to top N
            candidates = candidates[:args.top]

            if args.json:
                result = [asdict(c) for c in candidates]
                print(json.dumps(result, indent=2))
            else:
                if args.report:
                    metrics = analyzer.calculate_toil_metrics(days=args.days)
                    report = analyzer.generate_toil_report(metrics, candidates)
                    print(report)
                else:
                    for i, candidate in enumerate(candidates, 1):
                        print(f"\n{i}. {candidate.task}")
                        print(f"   Priority: {candidate.priority}")
                        print(f"   ROI: {candidate.roi:.1f}x")
                        print(f"   Payback: {candidate.payback_months:.1f} months")

        # Calculate ROI
        elif args.calculate_roi:
            if not all([args.task, args.frequency, args.duration]):
                parser.error("--calculate-roi requires --task, --frequency, and --duration")

            roi = analyzer.calculate_automation_roi(
                task=args.task,
                frequency_per_month=args.frequency,
                duration_hours=args.duration,
                automation_effort_hours=args.effort,
                complexity=args.complexity,
            )

            if args.json:
                print(json.dumps(asdict(roi), indent=2))
            else:
                print(f"\nAutomation ROI: {args.task}")
                print(f"  Decision: {roi.decision}")
                print(f"  Reasoning: {roi.reasoning}")
                print(f"  Payback: {roi.payback_months:.1f} months")
                print(f"  ROI (3-year): {roi.roi_3_year:.1f}x")
                print(f"  Annual savings: {roi.annual_cost_hours:.1f} hours")

        # Track toil trend
        elif args.track_toil:
            if not args.work_logs:
                parser.error("--track-toil requires --work-logs")

            trends = analyzer.track_toil_trend(period_days=args.period)

            if args.json:
                result = [asdict(t) for t in trends]
                print(json.dumps(result, indent=2))
            else:
                print(f"\nToil Trend (period: {args.period} days)")
                print(f"{'Period':<12} {'Toil %':<10} {'Change':<10}")
                print("-" * 35)

                for trend in trends:
                    change_str = ""
                    if trend.change_from_previous is not None:
                        sign = "+" if trend.change_from_previous > 0 else ""
                        change_str = f"{sign}{trend.change_from_previous:.1f}%"

                    print(f"{trend.period:<12} {trend.toil_percentage:>6.1f}%    {change_str:<10}")

        else:
            parser.error(
                "Must specify one of: --analyze, --automation-candidates, "
                "--calculate-roi, --track-toil, or --generate-sample"
            )

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
