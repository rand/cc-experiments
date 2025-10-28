#!/usr/bin/env python3
"""
Feature Flag Usage Analysis Tool

Comprehensive tool for analyzing feature flag usage, identifying stale flags,
measuring impact, detecting flag debt, and recommending retirement.

Capabilities:
- Track flag evaluations and usage patterns
- Identify stale/unused flags
- Measure flag impact on performance
- Detect flag technical debt
- Recommend flag retirement
- Generate usage reports and dashboards
- Analyze flag dependencies
- Cost analysis of flag infrastructure

Usage:
    analyze_flag_usage.py track --flag feature-x --days 30
    analyze_flag_usage.py stale --threshold 90
    analyze_flag_usage.py impact --flag feature-x
    analyze_flag_usage.py debt --severity high
    analyze_flag_usage.py recommend-retire --confidence 0.8
    analyze_flag_usage.py report --format html --output report.html
"""

import argparse
import json
import sys
import os
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, Counter
import statistics
import re
import hashlib


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FlagStatus(Enum):
    """Flag status categories"""
    ACTIVE = "active"
    STALE = "stale"
    UNUSED = "unused"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class DebtSeverity(Enum):
    """Technical debt severity"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactLevel(Enum):
    """Impact level"""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FlagEvaluation:
    """Single flag evaluation event"""
    flag_key: str
    timestamp: datetime
    variation: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'flag_key': self.flag_key,
            'timestamp': self.timestamp.isoformat(),
            'variation': self.variation,
            'user_id': self.user_id,
            'context': self.context,
            'duration_ms': self.duration_ms
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlagEvaluation':
        """Create from dictionary"""
        return cls(
            flag_key=data['flag_key'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            variation=data['variation'],
            user_id=data.get('user_id'),
            context=data.get('context'),
            duration_ms=data.get('duration_ms')
        )


@dataclass
class UsageMetrics:
    """Flag usage metrics"""
    flag_key: str
    total_evaluations: int
    unique_users: int
    variation_distribution: Dict[str, int]
    first_seen: datetime
    last_seen: datetime
    avg_evaluation_time_ms: float
    p95_evaluation_time_ms: float
    p99_evaluation_time_ms: float
    evaluation_rate: float  # evaluations per hour
    active_days: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'flag_key': self.flag_key,
            'total_evaluations': self.total_evaluations,
            'unique_users': self.unique_users,
            'variation_distribution': self.variation_distribution,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'avg_evaluation_time_ms': self.avg_evaluation_time_ms,
            'p95_evaluation_time_ms': self.p95_evaluation_time_ms,
            'p99_evaluation_time_ms': self.p99_evaluation_time_ms,
            'evaluation_rate': self.evaluation_rate,
            'active_days': self.active_days
        }


@dataclass
class FlagDebt:
    """Technical debt associated with a flag"""
    flag_key: str
    severity: DebtSeverity
    description: str
    created_at: datetime
    age_days: int
    code_locations: List[str] = field(default_factory=list)
    estimated_removal_effort_hours: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    risk_level: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'flag_key': self.flag_key,
            'severity': self.severity.value,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'age_days': self.age_days,
            'code_locations': self.code_locations,
            'estimated_removal_effort_hours': self.estimated_removal_effort_hours,
            'dependencies': self.dependencies,
            'risk_level': self.risk_level
        }


@dataclass
class RetirementRecommendation:
    """Flag retirement recommendation"""
    flag_key: str
    confidence: float  # 0-1
    reason: str
    impact_level: ImpactLevel
    prerequisites: List[str] = field(default_factory=list)
    rollback_plan: Optional[str] = None
    estimated_savings: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'flag_key': self.flag_key,
            'confidence': self.confidence,
            'reason': self.reason,
            'impact_level': self.impact_level.value,
            'prerequisites': self.prerequisites,
            'rollback_plan': self.rollback_plan,
            'estimated_savings': self.estimated_savings
        }


@dataclass
class FlagImpact:
    """Flag impact analysis"""
    flag_key: str
    performance_impact_ms: float
    error_rate_impact: float
    user_count_affected: int
    revenue_impact: Optional[float] = None
    conversion_rate_change: Optional[float] = None
    engagement_change: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class UsageTracker:
    """Track flag usage patterns"""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def _get_file_path(self, date: datetime) -> str:
        """Get file path for date"""
        return os.path.join(
            self.storage_path,
            f"evaluations-{date.strftime('%Y-%m-%d')}.jsonl"
        )

    def record_evaluation(self, evaluation: FlagEvaluation):
        """Record a flag evaluation"""
        file_path = self._get_file_path(evaluation.timestamp)
        with open(file_path, 'a') as f:
            f.write(json.dumps(evaluation.to_dict()) + '\n')

    def get_evaluations(
        self,
        flag_key: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[FlagEvaluation]:
        """Get evaluations with optional filters"""
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        evaluations = []
        current_date = start_date

        while current_date <= end_date:
            file_path = self._get_file_path(current_date)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    for line in f:
                        eval_data = json.loads(line.strip())
                        evaluation = FlagEvaluation.from_dict(eval_data)

                        if flag_key and evaluation.flag_key != flag_key:
                            continue

                        evaluations.append(evaluation)

            current_date += timedelta(days=1)

        return evaluations

    def compute_metrics(self, flag_key: str, days: int = 30) -> Optional[UsageMetrics]:
        """Compute usage metrics for a flag"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        evaluations = self.get_evaluations(flag_key, start_date, end_date)

        if not evaluations:
            return None

        variation_counts = Counter(e.variation for e in evaluations)
        user_ids = {e.user_id for e in evaluations if e.user_id}
        timestamps = [e.timestamp for e in evaluations]
        durations = [e.duration_ms for e in evaluations if e.duration_ms]

        first_seen = min(timestamps)
        last_seen = max(timestamps)
        active_days = (last_seen - first_seen).days + 1

        hours = (last_seen - first_seen).total_seconds() / 3600
        evaluation_rate = len(evaluations) / hours if hours > 0 else 0

        avg_time = statistics.mean(durations) if durations else 0
        p95_time = statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else avg_time
        p99_time = statistics.quantiles(durations, n=100)[98] if len(durations) > 100 else p95_time

        return UsageMetrics(
            flag_key=flag_key,
            total_evaluations=len(evaluations),
            unique_users=len(user_ids),
            variation_distribution=dict(variation_counts),
            first_seen=first_seen,
            last_seen=last_seen,
            avg_evaluation_time_ms=avg_time,
            p95_evaluation_time_ms=p95_time,
            p99_evaluation_time_ms=p99_time,
            evaluation_rate=evaluation_rate,
            active_days=active_days
        )


class DebtDetector:
    """Detect flag technical debt"""

    def __init__(self, code_path: str):
        self.code_path = code_path

    def scan_code_locations(self, flag_key: str) -> List[str]:
        """Scan code for flag references"""
        locations = []

        for root, dirs, files in os.walk(self.code_path):
            # Skip common non-code directories
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', 'venv'}]

            for file in files:
                if not file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rb')):
                    continue

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if flag_key in content:
                            # Count occurrences
                            count = content.count(flag_key)
                            locations.append(f"{file_path}:{count} occurrences")
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {e}")

        return locations

    def detect_debt(
        self,
        flag_key: str,
        created_at: datetime,
        usage_metrics: Optional[UsageMetrics] = None
    ) -> List[FlagDebt]:
        """Detect technical debt for a flag"""
        debts = []
        age_days = (datetime.now() - created_at).days

        # Age-based debt
        if age_days > 365:
            severity = DebtSeverity.HIGH
            description = f"Flag is {age_days} days old and may be stale"
        elif age_days > 180:
            severity = DebtSeverity.MEDIUM
            description = f"Flag is {age_days} days old, consider cleanup"
        elif age_days > 90:
            severity = DebtSeverity.LOW
            description = f"Flag is {age_days} days old"
        else:
            severity = None
            description = None

        if severity:
            code_locations = self.scan_code_locations(flag_key)
            estimated_effort = len(code_locations) * 0.5  # 30 min per location

            debt = FlagDebt(
                flag_key=flag_key,
                severity=severity,
                description=description,
                created_at=created_at,
                age_days=age_days,
                code_locations=code_locations,
                estimated_removal_effort_hours=estimated_effort
            )
            debts.append(debt)

        # Usage-based debt
        if usage_metrics:
            if usage_metrics.total_evaluations == 0:
                debts.append(FlagDebt(
                    flag_key=flag_key,
                    severity=DebtSeverity.HIGH,
                    description="Flag has no evaluations",
                    created_at=created_at,
                    age_days=age_days
                ))
            elif usage_metrics.evaluation_rate < 1:  # Less than 1 per hour
                debts.append(FlagDebt(
                    flag_key=flag_key,
                    severity=DebtSeverity.MEDIUM,
                    description=f"Low usage rate: {usage_metrics.evaluation_rate:.2f}/hour",
                    created_at=created_at,
                    age_days=age_days
                ))

            # Single variation dominance
            if usage_metrics.variation_distribution:
                max_variation = max(usage_metrics.variation_distribution.values())
                total = sum(usage_metrics.variation_distribution.values())
                if max_variation / total > 0.99:
                    dominant = [k for k, v in usage_metrics.variation_distribution.items() if v == max_variation][0]
                    debts.append(FlagDebt(
                        flag_key=flag_key,
                        severity=DebtSeverity.MEDIUM,
                        description=f"Single variation '{dominant}' dominates (>99%)",
                        created_at=created_at,
                        age_days=age_days
                    ))

        return debts


class ImpactAnalyzer:
    """Analyze flag impact"""

    def __init__(self, tracker: UsageTracker):
        self.tracker = tracker

    def analyze_performance_impact(
        self,
        flag_key: str,
        days: int = 30
    ) -> FlagImpact:
        """Analyze performance impact of a flag"""
        metrics = self.tracker.compute_metrics(flag_key, days)

        if not metrics:
            return FlagImpact(
                flag_key=flag_key,
                performance_impact_ms=0,
                error_rate_impact=0,
                user_count_affected=0
            )

        # Calculate performance impact
        performance_impact = metrics.avg_evaluation_time_ms

        # Estimate error rate impact (simplified)
        error_rate_impact = 0.0

        return FlagImpact(
            flag_key=flag_key,
            performance_impact_ms=performance_impact,
            error_rate_impact=error_rate_impact,
            user_count_affected=metrics.unique_users
        )

    def compare_variations(
        self,
        flag_key: str,
        metric_name: str,
        days: int = 30
    ) -> Dict[str, float]:
        """Compare metrics across flag variations"""
        evaluations = self.tracker.get_evaluations(
            flag_key,
            start_date=datetime.now() - timedelta(days=days)
        )

        variation_metrics = defaultdict(list)

        for eval in evaluations:
            if eval.context and metric_name in eval.context:
                variation_metrics[eval.variation].append(
                    eval.context[metric_name]
                )

        results = {}
        for variation, values in variation_metrics.items():
            if values:
                results[variation] = statistics.mean(values)

        return results


class RetirementAnalyzer:
    """Analyze flags for retirement"""

    def __init__(self, tracker: UsageTracker, debt_detector: DebtDetector):
        self.tracker = tracker
        self.debt_detector = debt_detector

    def recommend_retirement(
        self,
        flag_key: str,
        created_at: datetime,
        min_confidence: float = 0.7
    ) -> Optional[RetirementRecommendation]:
        """Generate retirement recommendation"""
        metrics = self.tracker.compute_metrics(flag_key, days=90)

        if not metrics:
            return RetirementRecommendation(
                flag_key=flag_key,
                confidence=0.9,
                reason="No usage data in last 90 days",
                impact_level=ImpactLevel.MINIMAL,
                prerequisites=["Verify flag is not used in production"]
            )

        confidence = 0.0
        reasons = []

        # Age factor
        age_days = (datetime.now() - created_at).days
        if age_days > 365:
            confidence += 0.3
            reasons.append(f"Flag is {age_days} days old")

        # Usage factor
        if metrics.evaluation_rate < 0.1:
            confidence += 0.3
            reasons.append(f"Very low usage: {metrics.evaluation_rate:.3f}/hour")

        # Variation dominance
        if metrics.variation_distribution:
            max_count = max(metrics.variation_distribution.values())
            total = sum(metrics.variation_distribution.values())
            dominance = max_count / total

            if dominance > 0.99:
                confidence += 0.4
                dominant = [k for k, v in metrics.variation_distribution.items()
                          if v == max_count][0]
                reasons.append(f"Single variation '{dominant}' used {dominance*100:.1f}% of time")

        if confidence < min_confidence:
            return None

        # Determine impact level
        if metrics.unique_users == 0:
            impact_level = ImpactLevel.MINIMAL
        elif metrics.unique_users < 10:
            impact_level = ImpactLevel.LOW
        elif metrics.unique_users < 100:
            impact_level = ImpactLevel.MODERATE
        else:
            impact_level = ImpactLevel.HIGH

        # Generate prerequisites
        prerequisites = [
            "Review all code references",
            "Verify flag can be safely removed",
            "Plan rollback strategy"
        ]

        if metrics.unique_users > 0:
            prerequisites.append("Notify affected users")

        # Estimate savings
        code_locations = self.debt_detector.scan_code_locations(flag_key)
        estimated_savings = {
            'engineering_hours': len(code_locations) * 0.5,
            'maintenance_cost_per_month': 10.0  # Rough estimate
        }

        return RetirementRecommendation(
            flag_key=flag_key,
            confidence=confidence,
            reason="; ".join(reasons),
            impact_level=impact_level,
            prerequisites=prerequisites,
            rollback_plan="Keep flag disabled for 30 days before removal",
            estimated_savings=estimated_savings
        )

    def batch_analyze(
        self,
        flags: List[Dict[str, Any]],
        min_confidence: float = 0.7
    ) -> List[RetirementRecommendation]:
        """Analyze multiple flags for retirement"""
        recommendations = []

        for flag in flags:
            flag_key = flag['key']
            created_at = datetime.fromisoformat(flag['created_at'])

            rec = self.recommend_retirement(flag_key, created_at, min_confidence)
            if rec:
                recommendations.append(rec)

        # Sort by confidence
        recommendations.sort(key=lambda r: r.confidence, reverse=True)

        return recommendations


class ReportGenerator:
    """Generate usage reports"""

    def __init__(self, tracker: UsageTracker):
        self.tracker = tracker

    def generate_summary_report(
        self,
        flags: List[Dict[str, Any]],
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate summary report"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'period_days': days,
            'total_flags': len(flags),
            'flags': []
        }

        for flag in flags:
            flag_key = flag['key']
            metrics = self.tracker.compute_metrics(flag_key, days)

            flag_report = {
                'key': flag_key,
                'name': flag.get('name', flag_key),
                'status': self._determine_status(metrics, flag)
            }

            if metrics:
                flag_report.update({
                    'total_evaluations': metrics.total_evaluations,
                    'unique_users': metrics.unique_users,
                    'evaluation_rate': metrics.evaluation_rate,
                    'last_seen': metrics.last_seen.isoformat()
                })

            report['flags'].append(flag_report)

        # Add statistics
        active_flags = sum(1 for f in report['flags'] if f['status'] == 'active')
        stale_flags = sum(1 for f in report['flags'] if f['status'] == 'stale')
        unused_flags = sum(1 for f in report['flags'] if f['status'] == 'unused')

        report['statistics'] = {
            'active_flags': active_flags,
            'stale_flags': stale_flags,
            'unused_flags': unused_flags
        }

        return report

    def _determine_status(
        self,
        metrics: Optional[UsageMetrics],
        flag: Dict[str, Any]
    ) -> str:
        """Determine flag status"""
        if not metrics:
            return 'unused'

        if metrics.evaluation_rate < 0.1:
            return 'stale'

        days_since_last = (datetime.now() - metrics.last_seen).days
        if days_since_last > 30:
            return 'stale'

        return 'active'

    def generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Feature Flag Usage Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f0f0f0; padding: 15px; margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .active {{ color: green; }}
        .stale {{ color: orange; }}
        .unused {{ color: red; }}
    </style>
</head>
<body>
    <h1>Feature Flag Usage Report</h1>

    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Generated:</strong> {report['generated_at']}</p>
        <p><strong>Period:</strong> {report['period_days']} days</p>
        <p><strong>Total Flags:</strong> {report['total_flags']}</p>
        <p><strong>Active:</strong> {report['statistics']['active_flags']}</p>
        <p><strong>Stale:</strong> {report['statistics']['stale_flags']}</p>
        <p><strong>Unused:</strong> {report['statistics']['unused_flags']}</p>
    </div>

    <h2>Flags</h2>
    <table>
        <tr>
            <th>Key</th>
            <th>Name</th>
            <th>Status</th>
            <th>Evaluations</th>
            <th>Users</th>
            <th>Rate/Hour</th>
            <th>Last Seen</th>
        </tr>
"""

        for flag in report['flags']:
            status_class = flag['status']
            html += f"""
        <tr>
            <td>{flag['key']}</td>
            <td>{flag['name']}</td>
            <td class="{status_class}">{flag['status']}</td>
            <td>{flag.get('total_evaluations', 0)}</td>
            <td>{flag.get('unique_users', 0)}</td>
            <td>{flag.get('evaluation_rate', 0):.2f}</td>
            <td>{flag.get('last_seen', 'N/A')}</td>
        </tr>
"""

        html += """
    </table>
</body>
</html>
"""
        return html


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Feature Flag Usage Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--storage', default='./flag-usage',
                       help='Storage path for usage data')
    parser.add_argument('--code-path', default='.',
                       help='Code path for scanning')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Track command
    track_parser = subparsers.add_parser('track', help='Track flag usage')
    track_parser.add_argument('--flag', required=True, help='Flag key')
    track_parser.add_argument('--days', type=int, default=30,
                             help='Days to analyze')

    # Stale command
    stale_parser = subparsers.add_parser('stale', help='Find stale flags')
    stale_parser.add_argument('--threshold', type=int, default=90,
                             help='Days threshold')
    stale_parser.add_argument('--flags-file', help='JSON file with flags')

    # Impact command
    impact_parser = subparsers.add_parser('impact', help='Analyze flag impact')
    impact_parser.add_argument('--flag', required=True, help='Flag key')
    impact_parser.add_argument('--days', type=int, default=30,
                              help='Days to analyze')

    # Debt command
    debt_parser = subparsers.add_parser('debt', help='Detect flag debt')
    debt_parser.add_argument('--flag', help='Specific flag key')
    debt_parser.add_argument('--severity',
                            choices=['low', 'medium', 'high', 'critical'],
                            help='Filter by severity')
    debt_parser.add_argument('--flags-file', help='JSON file with flags')

    # Recommend retire command
    retire_parser = subparsers.add_parser('recommend-retire',
                                          help='Recommend flags for retirement')
    retire_parser.add_argument('--confidence', type=float, default=0.7,
                              help='Minimum confidence (0-1)')
    retire_parser.add_argument('--flags-file', required=True,
                              help='JSON file with flags')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate usage report')
    report_parser.add_argument('--flags-file', required=True,
                              help='JSON file with flags')
    report_parser.add_argument('--days', type=int, default=30,
                              help='Days to analyze')
    report_parser.add_argument('--format', choices=['json', 'html'],
                              default='json', help='Report format')
    report_parser.add_argument('--output', help='Output file')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        tracker = UsageTracker(args.storage)
        debt_detector = DebtDetector(args.code_path)
        impact_analyzer = ImpactAnalyzer(tracker)
        retirement_analyzer = RetirementAnalyzer(tracker, debt_detector)
        report_generator = ReportGenerator(tracker)

        result = None

        if args.command == 'track':
            metrics = tracker.compute_metrics(args.flag, args.days)
            if metrics:
                result = metrics.to_dict()
            else:
                result = {'error': f'No data for flag {args.flag}'}

        elif args.command == 'stale':
            if not args.flags_file:
                print("Error: --flags-file required", file=sys.stderr)
                return 1

            with open(args.flags_file, 'r') as f:
                flags = json.load(f)

            stale_flags = []
            for flag in flags:
                metrics = tracker.compute_metrics(flag['key'], days=args.threshold)
                if not metrics or (datetime.now() - metrics.last_seen).days > args.threshold:
                    stale_flags.append(flag['key'])

            result = {'stale_flags': stale_flags, 'count': len(stale_flags)}

        elif args.command == 'impact':
            impact = impact_analyzer.analyze_performance_impact(
                args.flag, args.days
            )
            result = impact.to_dict()

        elif args.command == 'debt':
            if args.flag:
                # Single flag analysis
                created_at = datetime.now() - timedelta(days=365)  # Default
                metrics = tracker.compute_metrics(args.flag)
                debts = debt_detector.detect_debt(args.flag, created_at, metrics)
                result = [debt.to_dict() for debt in debts]
            elif args.flags_file:
                # Multiple flags
                with open(args.flags_file, 'r') as f:
                    flags = json.load(f)

                all_debts = []
                for flag in flags:
                    created_at = datetime.fromisoformat(flag['created_at'])
                    metrics = tracker.compute_metrics(flag['key'])
                    debts = debt_detector.detect_debt(flag['key'], created_at, metrics)

                    if args.severity:
                        debts = [d for d in debts
                               if d.severity.value == args.severity]

                    all_debts.extend(debts)

                result = [debt.to_dict() for debt in all_debts]
            else:
                print("Error: --flag or --flags-file required", file=sys.stderr)
                return 1

        elif args.command == 'recommend-retire':
            with open(args.flags_file, 'r') as f:
                flags = json.load(f)

            recommendations = retirement_analyzer.batch_analyze(
                flags, args.confidence
            )
            result = [rec.to_dict() for rec in recommendations]

        elif args.command == 'report':
            with open(args.flags_file, 'r') as f:
                flags = json.load(f)

            report = report_generator.generate_summary_report(flags, args.days)

            if args.format == 'html':
                html_report = report_generator.generate_html_report(report)
                if args.output:
                    with open(args.output, 'w') as f:
                        f.write(html_report)
                    result = {'status': 'written', 'file': args.output}
                else:
                    print(html_report)
                    return 0
            else:
                result = report

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
