#!/usr/bin/env python3
"""
Analyze MTTR (Mean Time To Repair) and incident patterns.

This script provides comprehensive analysis of incident metrics including MTTR,
MTTD, MTTA, incident trends, and actionable insights for improvement.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import statistics


class IncidentMetrics:
    """Calculate and analyze incident metrics."""

    def __init__(self, incidents: List[Dict[str, Any]]):
        """
        Initialize with incident data.

        Args:
            incidents: List of incident records
        """
        self.incidents = incidents
        self.resolved_incidents = [
            inc for inc in incidents
            if inc["timestamps"].get("resolved_at")
        ]

    def calculate_mttr(
        self,
        severity: Optional[str] = None,
        service: Optional[str] = None,
        time_period_days: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Calculate Mean Time To Repair.

        Args:
            severity: Filter by severity
            service: Filter by service
            time_period_days: Only include incidents from last N days

        Returns:
            Dictionary with MTTR statistics (mean, median, p95, p99)
        """
        filtered = self._filter_incidents(
            self.resolved_incidents,
            severity=severity,
            service=service,
            time_period_days=time_period_days
        )

        if not filtered:
            return {"mean": 0, "median": 0, "p95": 0, "p99": 0, "count": 0}

        durations = []
        for inc in filtered:
            started = datetime.fromisoformat(inc["timestamps"]["created_at"])
            resolved = datetime.fromisoformat(inc["timestamps"]["resolved_at"])
            duration_minutes = (resolved - started).total_seconds() / 60
            durations.append(duration_minutes)

        return {
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
            "p95": self._percentile(durations, 95),
            "p99": self._percentile(durations, 99),
            "min": min(durations),
            "max": max(durations),
            "count": len(durations)
        }

    def calculate_mttd(
        self,
        severity: Optional[str] = None,
        time_period_days: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Calculate Mean Time To Detect.

        Args:
            severity: Filter by severity
            time_period_days: Only include incidents from last N days

        Returns:
            Dictionary with MTTD statistics
        """
        filtered = self._filter_incidents(
            self.incidents,
            severity=severity,
            time_period_days=time_period_days
        )

        durations = []
        for inc in filtered:
            created = datetime.fromisoformat(inc["timestamps"]["created_at"])
            detected = datetime.fromisoformat(inc["timestamps"]["detected_at"])
            duration_minutes = (detected - created).total_seconds() / 60
            durations.append(duration_minutes)

        if not durations:
            return {"mean": 0, "median": 0, "count": 0}

        return {
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
            "p95": self._percentile(durations, 95),
            "count": len(durations)
        }

    def calculate_mtta(
        self,
        severity: Optional[str] = None,
        time_period_days: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Calculate Mean Time To Acknowledge.

        Args:
            severity: Filter by severity
            time_period_days: Only include incidents from last N days

        Returns:
            Dictionary with MTTA statistics
        """
        filtered = self._filter_incidents(
            self.incidents,
            severity=severity,
            time_period_days=time_period_days
        )

        acknowledged = [
            inc for inc in filtered
            if inc["timestamps"].get("acknowledged_at")
        ]

        if not acknowledged:
            return {"mean": 0, "median": 0, "count": 0}

        durations = []
        for inc in acknowledged:
            detected = datetime.fromisoformat(inc["timestamps"]["detected_at"])
            ack = datetime.fromisoformat(inc["timestamps"]["acknowledged_at"])
            duration_minutes = (ack - detected).total_seconds() / 60
            durations.append(duration_minutes)

        return {
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
            "p95": self._percentile(durations, 95),
            "count": len(durations)
        }

    def calculate_mtbf(self, time_period_days: int = 30) -> float:
        """
        Calculate Mean Time Between Failures.

        Args:
            time_period_days: Time period for calculation

        Returns:
            MTBF in hours
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=time_period_days)
        recent = [
            inc for inc in self.incidents
            if datetime.fromisoformat(inc["timestamps"]["created_at"]) > cutoff
        ]

        if len(recent) <= 1:
            return float('inf')

        total_hours = time_period_days * 24
        return total_hours / len(recent)

    def incidents_by_severity(
        self,
        time_period_days: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Count incidents by severity.

        Args:
            time_period_days: Only include incidents from last N days

        Returns:
            Dictionary mapping severity to count
        """
        filtered = self._filter_incidents(
            self.incidents,
            time_period_days=time_period_days
        )

        counts = defaultdict(int)
        for inc in filtered:
            counts[inc["severity"]] += 1

        return dict(counts)

    def incidents_by_service(
        self,
        time_period_days: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Count incidents by service.

        Args:
            time_period_days: Only include incidents from last N days

        Returns:
            Dictionary mapping service to count
        """
        filtered = self._filter_incidents(
            self.incidents,
            time_period_days=time_period_days
        )

        counts = defaultdict(int)
        for inc in filtered:
            counts[inc["service"]] += 1

        # Sort by count descending
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def hourly_distribution(self) -> Dict[int, int]:
        """
        Get distribution of incidents by hour of day (UTC).

        Returns:
            Dictionary mapping hour (0-23) to incident count
        """
        distribution = defaultdict(int)
        for inc in self.incidents:
            created = datetime.fromisoformat(inc["timestamps"]["created_at"])
            hour = created.hour
            distribution[hour] += 1

        return dict(sorted(distribution.items()))

    def daily_distribution(self) -> Dict[str, int]:
        """
        Get distribution of incidents by day of week.

        Returns:
            Dictionary mapping day name to incident count
        """
        distribution = defaultdict(int)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for inc in self.incidents:
            created = datetime.fromisoformat(inc["timestamps"]["created_at"])
            day_name = days[created.weekday()]
            distribution[day_name] += 1

        # Return in week order
        return {day: distribution[day] for day in days}

    def monthly_trend(self, months: int = 6) -> List[Dict[str, Any]]:
        """
        Calculate monthly incident trends.

        Args:
            months: Number of months to include

        Returns:
            List of monthly statistics
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
        recent = [
            inc for inc in self.incidents
            if datetime.fromisoformat(inc["timestamps"]["created_at"]) > cutoff
        ]

        # Group by month
        monthly = defaultdict(list)
        for inc in recent:
            created = datetime.fromisoformat(inc["timestamps"]["created_at"])
            month_key = created.strftime("%Y-%m")
            monthly[month_key].append(inc)

        # Calculate stats per month
        trends = []
        for month_key in sorted(monthly.keys()):
            incidents = monthly[month_key]
            resolved = [
                inc for inc in incidents
                if inc["timestamps"].get("resolved_at")
            ]

            # Calculate MTTR for month
            if resolved:
                durations = []
                for inc in resolved:
                    started = datetime.fromisoformat(inc["timestamps"]["created_at"])
                    resolved_at = datetime.fromisoformat(inc["timestamps"]["resolved_at"])
                    duration_minutes = (resolved_at - started).total_seconds() / 60
                    durations.append(duration_minutes)
                avg_mttr = statistics.mean(durations)
            else:
                avg_mttr = 0

            trends.append({
                "month": month_key,
                "total_incidents": len(incidents),
                "sev1_count": len([i for i in incidents if i["severity"] == "SEV-1"]),
                "sev2_count": len([i for i in incidents if i["severity"] == "SEV-2"]),
                "avg_mttr_minutes": avg_mttr
            })

        return trends

    def identify_patterns(self) -> Dict[str, Any]:
        """
        Identify patterns and anomalies in incident data.

        Returns:
            Dictionary with identified patterns
        """
        patterns = {}

        # Services with most incidents
        service_counts = self.incidents_by_service(time_period_days=30)
        if service_counts:
            top_service = max(service_counts.items(), key=lambda x: x[1])
            patterns["most_incident_prone_service"] = {
                "service": top_service[0],
                "count": top_service[1]
            }

        # Peak incident hours
        hourly = self.hourly_distribution()
        if hourly:
            peak_hour = max(hourly.items(), key=lambda x: x[1])
            patterns["peak_incident_hour"] = {
                "hour_utc": peak_hour[0],
                "count": peak_hour[1]
            }

        # Peak incident days
        daily = self.daily_distribution()
        if daily:
            peak_day = max(daily.items(), key=lambda x: x[1])
            patterns["peak_incident_day"] = {
                "day": peak_day[0],
                "count": peak_day[1]
            }

        # Severity trends
        sev_counts = self.incidents_by_severity(time_period_days=30)
        patterns["severity_distribution_30d"] = sev_counts

        return patterns

    def generate_recommendations(self) -> List[str]:
        """
        Generate actionable recommendations based on metrics.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Check MTTR
        mttr = self.calculate_mttr(time_period_days=30)
        if mttr["mean"] > 120:  # > 2 hours
            recommendations.append(
                f"MTTR is high ({mttr['mean']:.0f} minutes). Consider: "
                "improving runbooks, adding automation, or training responders."
            )

        # Check MTTD
        mttd = self.calculate_mttd(time_period_days=30)
        if mttd["mean"] > 10:  # > 10 minutes
            recommendations.append(
                f"MTTD is high ({mttd['mean']:.0f} minutes). Consider: "
                "better monitoring, synthetic checks, or alert tuning."
            )

        # Check MTTA
        mtta = self.calculate_mtta(time_period_days=30)
        if mtta["mean"] > 15:  # > 15 minutes
            recommendations.append(
                f"MTTA is high ({mtta['mean']:.0f} minutes). Consider: "
                "improving on-call schedules, alert clarity, or escalation policies."
            )

        # Check SEV-1 frequency
        sev_counts = self.incidents_by_severity(time_period_days=30)
        if sev_counts.get("SEV-1", 0) > 4:
            recommendations.append(
                f"{sev_counts['SEV-1']} SEV-1 incidents in 30 days is high. "
                "Focus on preventing recurrence through postmortem action items."
            )

        # Check service concentration
        service_counts = self.incidents_by_service(time_period_days=30)
        if service_counts:
            top_service, count = max(service_counts.items(), key=lambda x: x[1])
            if count > len(self.incidents) * 0.4:  # One service > 40% of incidents
                recommendations.append(
                    f"Service '{top_service}' has {count} incidents ({count/len(self.incidents)*100:.0f}% of total). "
                    "Consider architectural review or dedicated reliability improvements."
                )

        # Check patterns
        patterns = self.identify_patterns()
        if "peak_incident_hour" in patterns:
            peak = patterns["peak_incident_hour"]
            if peak["count"] > len(self.incidents) * 0.2:
                recommendations.append(
                    f"Incidents cluster around {peak['hour_utc']}:00 UTC. "
                    "Investigate if this correlates with deployments, batch jobs, or traffic patterns."
                )

        if not recommendations:
            recommendations.append("Incident metrics look healthy. Continue monitoring trends.")

        return recommendations

    def _filter_incidents(
        self,
        incidents: List[Dict[str, Any]],
        severity: Optional[str] = None,
        service: Optional[str] = None,
        time_period_days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Filter incidents by criteria."""
        filtered = incidents

        if severity:
            filtered = [inc for inc in filtered if inc["severity"] == severity]

        if service:
            filtered = [inc for inc in filtered if inc["service"] == service]

        if time_period_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=time_period_days)
            filtered = [
                inc for inc in filtered
                if datetime.fromisoformat(inc["timestamps"]["created_at"]) > cutoff
            ]

        return filtered

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class MetricsAnalyzer:
    """Analyze and report on incident metrics."""

    def __init__(self, incidents_path: Path):
        """
        Initialize analyzer.

        Args:
            incidents_path: Path to incidents directory
        """
        self.incidents_path = incidents_path
        self.incidents = self._load_incidents()
        self.metrics = IncidentMetrics(self.incidents)

    def _load_incidents(self) -> List[Dict[str, Any]]:
        """Load all incidents from storage."""
        incidents = []
        if not self.incidents_path.exists():
            return incidents

        for incident_file in self.incidents_path.glob("*.json"):
            try:
                incident = json.loads(incident_file.read_text())
                incidents.append(incident)
            except Exception as e:
                print(f"Warning: Failed to load {incident_file}: {e}", file=sys.stderr)

        return incidents

    def generate_report(
        self,
        time_period_days: int = 30,
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive metrics report.

        Args:
            time_period_days: Time period for analysis
            include_recommendations: Include recommendations

        Returns:
            Complete metrics report
        """
        report = {
            "period": {
                "days": time_period_days,
                "start_date": (
                    datetime.now(timezone.utc) - timedelta(days=time_period_days)
                ).isoformat(),
                "end_date": datetime.now(timezone.utc).isoformat()
            },
            "summary": {
                "total_incidents": len(self.incidents),
                "incidents_in_period": len(
                    self.metrics._filter_incidents(
                        self.incidents,
                        time_period_days=time_period_days
                    )
                ),
                "resolved_incidents": len(self.metrics.resolved_incidents)
            },
            "mttr": self.metrics.calculate_mttr(time_period_days=time_period_days),
            "mttd": self.metrics.calculate_mttd(time_period_days=time_period_days),
            "mtta": self.metrics.calculate_mtta(time_period_days=time_period_days),
            "mtbf_hours": self.metrics.calculate_mtbf(time_period_days=time_period_days),
            "by_severity": self.metrics.incidents_by_severity(time_period_days=time_period_days),
            "by_service": self.metrics.incidents_by_service(time_period_days=time_period_days),
            "hourly_distribution": self.metrics.hourly_distribution(),
            "daily_distribution": self.metrics.daily_distribution(),
            "patterns": self.metrics.identify_patterns()
        }

        if include_recommendations:
            report["recommendations"] = self.metrics.generate_recommendations()

        return report

    def generate_trend_report(self, months: int = 6) -> Dict[str, Any]:
        """
        Generate monthly trend report.

        Args:
            months: Number of months to analyze

        Returns:
            Trend report with monthly data
        """
        trends = self.metrics.monthly_trend(months=months)

        # Calculate trend direction
        if len(trends) >= 2:
            recent_count = sum(t["total_incidents"] for t in trends[-2:]) / 2
            older_count = sum(t["total_incidents"] for t in trends[:2]) / 2
            trend_direction = "improving" if recent_count < older_count else "worsening"
        else:
            trend_direction = "insufficient_data"

        return {
            "months_analyzed": months,
            "monthly_data": trends,
            "trend_direction": trend_direction,
            "total_incidents": sum(t["total_incidents"] for t in trends),
            "avg_incidents_per_month": statistics.mean(
                [t["total_incidents"] for t in trends]
            ) if trends else 0
        }

    def compare_services(self) -> List[Dict[str, Any]]:
        """
        Compare metrics across services.

        Returns:
            List of service comparisons
        """
        service_counts = self.metrics.incidents_by_service(time_period_days=30)
        comparisons = []

        for service in service_counts.keys():
            mttr = self.metrics.calculate_mttr(service=service, time_period_days=30)
            sev_counts = self.metrics.incidents_by_severity(time_period_days=30)

            service_incidents = [
                inc for inc in self.incidents
                if inc["service"] == service
            ]
            sev1_count = len([i for i in service_incidents if i["severity"] == "SEV-1"])

            comparisons.append({
                "service": service,
                "incident_count": service_counts[service],
                "avg_mttr_minutes": mttr["mean"],
                "sev1_count": sev1_count,
                "reliability_score": self._calculate_reliability_score(
                    service_counts[service],
                    mttr["mean"],
                    sev1_count
                )
            })

        # Sort by reliability score (lower is better)
        comparisons.sort(key=lambda x: x["reliability_score"])

        return comparisons

    @staticmethod
    def _calculate_reliability_score(
        incident_count: int,
        avg_mttr: float,
        sev1_count: int
    ) -> float:
        """
        Calculate reliability score for a service.

        Lower score = more reliable
        """
        # Weight: incident count (1x), MTTR (0.5x), SEV-1 count (3x)
        return incident_count + (avg_mttr * 0.5) + (sev1_count * 3)


def format_report(report: Dict[str, Any], verbose: bool = False) -> str:
    """Format report for display."""
    lines = []

    # Summary
    lines.append("=== INCIDENT METRICS REPORT ===\n")
    lines.append(f"Period: {report['period']['days']} days")
    lines.append(f"Total Incidents: {report['summary']['total_incidents']}")
    lines.append(f"Incidents in Period: {report['summary']['incidents_in_period']}")
    lines.append(f"Resolved: {report['summary']['resolved_incidents']}\n")

    # Key metrics
    lines.append("=== KEY METRICS ===")
    lines.append(f"MTTR (Mean Time To Repair):")
    lines.append(f"  Mean: {report['mttr']['mean']:.1f} minutes")
    lines.append(f"  Median: {report['mttr']['median']:.1f} minutes")
    lines.append(f"  P95: {report['mttr']['p95']:.1f} minutes")
    lines.append(f"  P99: {report['mttr']['p99']:.1f} minutes\n")

    lines.append(f"MTTD (Mean Time To Detect):")
    lines.append(f"  Mean: {report['mttd']['mean']:.1f} minutes")
    lines.append(f"  Median: {report['mttd']['median']:.1f} minutes\n")

    lines.append(f"MTTA (Mean Time To Acknowledge):")
    lines.append(f"  Mean: {report['mtta']['mean']:.1f} minutes")
    lines.append(f"  Median: {report['mtta']['median']:.1f} minutes\n")

    mtbf = report['mtbf_hours']
    if mtbf == float('inf'):
        lines.append(f"MTBF (Mean Time Between Failures): N/A (insufficient data)\n")
    else:
        lines.append(f"MTBF (Mean Time Between Failures): {mtbf:.1f} hours\n")

    # By severity
    lines.append("=== BY SEVERITY ===")
    for sev, count in sorted(report['by_severity'].items()):
        lines.append(f"{sev}: {count}")
    lines.append("")

    # By service
    lines.append("=== BY SERVICE (Top 10) ===")
    for i, (service, count) in enumerate(list(report['by_service'].items())[:10], 1):
        lines.append(f"{i}. {service}: {count}")
    lines.append("")

    if verbose:
        # Hourly distribution
        lines.append("=== HOURLY DISTRIBUTION (UTC) ===")
        for hour, count in sorted(report['hourly_distribution'].items()):
            bar = "█" * count
            lines.append(f"{hour:02d}:00 | {bar} {count}")
        lines.append("")

        # Daily distribution
        lines.append("=== DAILY DISTRIBUTION ===")
        for day, count in report['daily_distribution'].items():
            bar = "█" * count
            lines.append(f"{day:9s} | {bar} {count}")
        lines.append("")

        # Patterns
        if report.get('patterns'):
            lines.append("=== IDENTIFIED PATTERNS ===")
            patterns = report['patterns']

            if "most_incident_prone_service" in patterns:
                svc = patterns["most_incident_prone_service"]
                lines.append(f"Most Incident-Prone Service: {svc['service']} ({svc['count']} incidents)")

            if "peak_incident_hour" in patterns:
                peak = patterns["peak_incident_hour"]
                lines.append(f"Peak Incident Hour: {peak['hour_utc']:02d}:00 UTC ({peak['count']} incidents)")

            if "peak_incident_day" in patterns:
                peak = patterns["peak_incident_day"]
                lines.append(f"Peak Incident Day: {peak['day']} ({peak['count']} incidents)")

            lines.append("")

    # Recommendations
    if report.get('recommendations'):
        lines.append("=== RECOMMENDATIONS ===")
        for i, rec in enumerate(report['recommendations'], 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    return "\n".join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze MTTR and incident patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 30-day metrics report
  %(prog)s --incidents-path ./incidents --period 30

  # Generate report with verbose output
  %(prog)s --incidents-path ./incidents --verbose

  # Generate 6-month trend report
  %(prog)s --incidents-path ./incidents --trends --months 6

  # Compare services
  %(prog)s --incidents-path ./incidents --compare-services

  # Get specific metric
  %(prog)s --incidents-path ./incidents --metric mttr --severity SEV-1

  # JSON output for integration
  %(prog)s --incidents-path ./incidents --json
        """
    )

    parser.add_argument(
        "--incidents-path",
        type=Path,
        default=Path("./incidents"),
        help="Path to incidents directory (default: ./incidents/)"
    )

    parser.add_argument(
        "--period",
        type=int,
        default=30,
        help="Time period in days for analysis (default: 30)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Include detailed distributions and patterns"
    )

    parser.add_argument(
        "--trends",
        action="store_true",
        help="Generate monthly trend report"
    )

    parser.add_argument(
        "--months",
        type=int,
        default=6,
        help="Number of months for trend analysis (default: 6)"
    )

    parser.add_argument(
        "--compare-services",
        action="store_true",
        help="Compare metrics across services"
    )

    parser.add_argument(
        "--metric",
        choices=["mttr", "mttd", "mtta", "mtbf"],
        help="Get specific metric only"
    )

    parser.add_argument(
        "--severity",
        choices=["SEV-1", "SEV-2", "SEV-3", "SEV-4"],
        help="Filter by severity"
    )

    parser.add_argument(
        "--service",
        help="Filter by service"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    parser.add_argument("--help", action="help", help="Show this help message and exit")

    args = parser.parse_args()

    try:
        analyzer = MetricsAnalyzer(incidents_path=args.incidents_path)

        if not analyzer.incidents:
            print("No incidents found", file=sys.stderr)
            sys.exit(1)

        if args.metric:
            # Get specific metric
            metrics = IncidentMetrics(analyzer.incidents)

            if args.metric == "mttr":
                result = metrics.calculate_mttr(
                    severity=args.severity,
                    service=args.service,
                    time_period_days=args.period
                )
            elif args.metric == "mttd":
                result = metrics.calculate_mttd(
                    severity=args.severity,
                    time_period_days=args.period
                )
            elif args.metric == "mtta":
                result = metrics.calculate_mtta(
                    severity=args.severity,
                    time_period_days=args.period
                )
            elif args.metric == "mtbf":
                result = {"mtbf_hours": metrics.calculate_mtbf(time_period_days=args.period)}

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                for key, value in result.items():
                    print(f"{key}: {value:.2f}" if isinstance(value, float) else f"{key}: {value}")

        elif args.trends:
            # Generate trend report
            report = analyzer.generate_trend_report(months=args.months)

            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(f"=== MONTHLY TRENDS ({args.months} months) ===\n")
                print(f"Trend Direction: {report['trend_direction']}")
                print(f"Total Incidents: {report['total_incidents']}")
                print(f"Avg Per Month: {report['avg_incidents_per_month']:.1f}\n")

                print("Month      | Total | SEV-1 | SEV-2 | Avg MTTR")
                print("-" * 50)
                for month_data in report['monthly_data']:
                    print(
                        f"{month_data['month']} | "
                        f"{month_data['total_incidents']:5d} | "
                        f"{month_data['sev1_count']:5d} | "
                        f"{month_data['sev2_count']:5d} | "
                        f"{month_data['avg_mttr_minutes']:8.1f}m"
                    )

        elif args.compare_services:
            # Compare services
            comparisons = analyzer.compare_services()

            if args.json:
                print(json.dumps(comparisons, indent=2))
            else:
                print("=== SERVICE COMPARISON (30 days) ===\n")
                print("Service              | Incidents | Avg MTTR | SEV-1 | Score")
                print("-" * 65)
                for comp in comparisons:
                    print(
                        f"{comp['service']:20s} | "
                        f"{comp['incident_count']:9d} | "
                        f"{comp['avg_mttr_minutes']:8.1f}m | "
                        f"{comp['sev1_count']:5d} | "
                        f"{comp['reliability_score']:5.1f}"
                    )
                print("\nNote: Lower reliability score = more reliable")

        else:
            # Generate full report
            report = analyzer.generate_report(
                time_period_days=args.period,
                include_recommendations=True
            )

            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(format_report(report, verbose=args.verbose))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
