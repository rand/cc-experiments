#!/usr/bin/env python3
"""
Error Pattern Analysis and Triage

This script analyzes error tracking data to identify patterns, detect regressions,
assess impact, and generate triage recommendations.

Features:
- Error pattern detection and clustering
- Regression detection across releases
- Impact assessment (frequency + user count)
- Priority scoring and triage recommendations
- Trend analysis over time
- Report generation (text, JSON, HTML)

Usage:
    analyze_errors.py --org myorg --project backend-api --days 7
    analyze_errors.py --org myorg --project api --report-type priority --json
    analyze_errors.py --org myorg --project api --detect-regressions

Examples:
    # Analyze last 7 days
    analyze_errors.py --org acme --project api --days 7

    # Generate priority report
    analyze_errors.py --org acme --project api --report-type priority --json

    # Detect regressions
    analyze_errors.py --org acme --project api --detect-regressions --verbose

    # Generate HTML report
    analyze_errors.py --org acme --project api --days 30 --output report.html
"""

import argparse
import json
import sys
import os
import requests
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ErrorIssue:
    """Sentry issue data."""
    id: str
    title: str
    culprit: str
    level: str
    status: str
    first_seen: datetime
    last_seen: datetime
    count: int
    user_count: int
    project: str
    platform: str
    metadata: Dict[str, Any]
    tags: Dict[str, str]


@dataclass
class ErrorPattern:
    """Detected error pattern."""
    pattern_id: str
    pattern_type: str
    issues: List[str]
    description: str
    frequency: int
    user_impact: int
    confidence: float


@dataclass
class PriorityScore:
    """Issue priority assessment."""
    issue_id: str
    score: int
    priority: str
    factors: Dict[str, int]
    recommendation: str


class SentryAnalyzer:
    """Analyze Sentry error data."""

    def __init__(self, api_token: str, base_url: str = "https://sentry.io/api/0"):
        self.api_token = api_token
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make API request with error handling."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"API request failed: {e}")
            logger.error(f"Response: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def get_issues(
        self,
        org_slug: str,
        project_slug: str,
        query: str = "",
        statsPeriod: str = "24h"
    ) -> List[ErrorIssue]:
        """Fetch issues from Sentry."""
        endpoint = f"/projects/{org_slug}/{project_slug}/issues/"

        params = {
            "statsPeriod": statsPeriod,
            "query": query
        }

        response = self._request("GET", endpoint, params=params)
        issues_data = response.json()

        issues = []
        for issue_data in issues_data:
            issue = ErrorIssue(
                id=issue_data['id'],
                title=issue_data['title'],
                culprit=issue_data.get('culprit', ''),
                level=issue_data['level'],
                status=issue_data['status'],
                first_seen=datetime.fromisoformat(issue_data['firstSeen'].replace('Z', '+00:00')),
                last_seen=datetime.fromisoformat(issue_data['lastSeen'].replace('Z', '+00:00')),
                count=issue_data.get('count', 0),
                user_count=issue_data.get('userCount', 0),
                project=issue_data['project']['slug'],
                platform=issue_data.get('platform', ''),
                metadata=issue_data.get('metadata', {}),
                tags=self._extract_tags(issue_data.get('tags', []))
            )
            issues.append(issue)

        return issues

    def _extract_tags(self, tags_list: List[Dict]) -> Dict[str, str]:
        """Extract tags from Sentry format."""
        tags = {}
        for tag in tags_list:
            tags[tag['key']] = tag['value']
        return tags

    def get_issue_events(
        self,
        org_slug: str,
        issue_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch events for specific issue."""
        endpoint = f"/issues/{issue_id}/events/"

        params = {"limit": limit}

        response = self._request("GET", endpoint, params=params)
        return response.json()


class ErrorAnalyzer:
    """Analyze error patterns and trends."""

    def __init__(self, analyzer: SentryAnalyzer):
        self.analyzer = analyzer

    def calculate_priority_score(self, issue: ErrorIssue) -> PriorityScore:
        """Calculate priority score for issue."""
        factors = {}
        score = 0

        # Frequency (0-30 points)
        if issue.count > 1000:
            factors['frequency'] = 30
        elif issue.count > 100:
            factors['frequency'] = 20
        elif issue.count > 10:
            factors['frequency'] = 10
        else:
            factors['frequency'] = 5

        score += factors['frequency']

        # User impact (0-30 points)
        if issue.user_count > 100:
            factors['user_impact'] = 30
        elif issue.user_count > 10:
            factors['user_impact'] = 20
        elif issue.user_count > 1:
            factors['user_impact'] = 10
        else:
            factors['user_impact'] = 5

        score += factors['user_impact']

        # Environment (0-15 points)
        env = issue.tags.get('environment', '')
        if env == 'production':
            factors['environment'] = 15
        elif env == 'staging':
            factors['environment'] = 5
        else:
            factors['environment'] = 0

        score += factors['environment']

        # Error level (0-10 points)
        if issue.level == 'fatal':
            factors['level'] = 10
        elif issue.level == 'error':
            factors['level'] = 7
        elif issue.level == 'warning':
            factors['level'] = 3
        else:
            factors['level'] = 0

        score += factors['level']

        # Status (0-10 points)
        if issue.status == 'regression':
            factors['status'] = 10
        elif issue.status == 'unresolved':
            factors['status'] = 5
        else:
            factors['status'] = 0

        score += factors['status']

        # Recency (0-5 points)
        hours_since_first = (datetime.now(issue.first_seen.tzinfo) - issue.first_seen).total_seconds() / 3600
        if hours_since_first < 24:
            factors['recency'] = 5
        elif hours_since_first < 168:  # 1 week
            factors['recency'] = 3
        else:
            factors['recency'] = 0

        score += factors['recency']

        # Determine priority level
        if score >= 70:
            priority = 'P0'
            recommendation = 'CRITICAL - Immediate action required. Page on-call engineer.'
        elif score >= 50:
            priority = 'P1'
            recommendation = 'HIGH - Fix within same business day. Notify team immediately.'
        elif score >= 30:
            priority = 'P2'
            recommendation = 'MEDIUM - Create ticket. Fix within current sprint.'
        else:
            priority = 'P3'
            recommendation = 'LOW - Add to backlog. Fix when convenient.'

        return PriorityScore(
            issue_id=issue.id,
            score=score,
            priority=priority,
            factors=factors,
            recommendation=recommendation
        )

    def detect_patterns(self, issues: List[ErrorIssue]) -> List[ErrorPattern]:
        """Detect common error patterns."""
        patterns = []

        # Group by exception type
        by_type = defaultdict(list)
        for issue in issues:
            exc_type = self._extract_exception_type(issue)
            by_type[exc_type].append(issue.id)

        for exc_type, issue_ids in by_type.items():
            if len(issue_ids) >= 3:  # Pattern threshold
                total_freq = sum(i.count for i in issues if i.id in issue_ids)
                total_users = sum(i.user_count for i in issues if i.id in issue_ids)

                patterns.append(ErrorPattern(
                    pattern_id=f"type_{exc_type}",
                    pattern_type="exception_type",
                    issues=issue_ids,
                    description=f"Multiple issues with {exc_type} exception",
                    frequency=total_freq,
                    user_impact=total_users,
                    confidence=0.9
                ))

        # Group by culprit (source location)
        by_culprit = defaultdict(list)
        for issue in issues:
            culprit = self._normalize_culprit(issue.culprit)
            if culprit:
                by_culprit[culprit].append(issue.id)

        for culprit, issue_ids in by_culprit.items():
            if len(issue_ids) >= 2:
                total_freq = sum(i.count for i in issues if i.id in issue_ids)
                total_users = sum(i.user_count for i in issues if i.id in issue_ids)

                patterns.append(ErrorPattern(
                    pattern_id=f"culprit_{culprit}",
                    pattern_type="source_location",
                    issues=issue_ids,
                    description=f"Multiple issues in {culprit}",
                    frequency=total_freq,
                    user_impact=total_users,
                    confidence=0.8
                ))

        # Group by error message pattern
        by_message = defaultdict(list)
        for issue in issues:
            message_pattern = self._extract_message_pattern(issue.title)
            if message_pattern:
                by_message[message_pattern].append(issue.id)

        for pattern, issue_ids in by_message.items():
            if len(issue_ids) >= 2:
                total_freq = sum(i.count for i in issues if i.id in issue_ids)
                total_users = sum(i.user_count for i in issues if i.id in issue_ids)

                patterns.append(ErrorPattern(
                    pattern_id=f"message_{pattern}",
                    pattern_type="error_message",
                    issues=issue_ids,
                    description=f"Similar error messages: {pattern}",
                    frequency=total_freq,
                    user_impact=total_users,
                    confidence=0.7
                ))

        return patterns

    def _extract_exception_type(self, issue: ErrorIssue) -> str:
        """Extract exception type from issue."""
        if 'type' in issue.metadata:
            return issue.metadata['type']

        # Try to parse from title
        match = re.match(r'^(\w+Error|\w+Exception):', issue.title)
        if match:
            return match.group(1)

        return 'Unknown'

    def _normalize_culprit(self, culprit: str) -> str:
        """Normalize culprit for pattern matching."""
        if not culprit:
            return ''

        # Extract module/function
        parts = culprit.split(' in ')
        if len(parts) > 1:
            return parts[1].split('(')[0].strip()

        return culprit.split('(')[0].strip()

    def _extract_message_pattern(self, message: str) -> str:
        """Extract pattern from error message."""
        # Remove numbers and IDs
        pattern = re.sub(r'\d+', 'N', message)

        # Remove UUIDs
        pattern = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            'UUID',
            pattern,
            flags=re.IGNORECASE
        )

        # Remove common variable parts
        pattern = re.sub(r"'[^']*'", "'X'", pattern)
        pattern = re.sub(r'"[^"]*"', '"X"', pattern)

        return pattern

    def detect_regressions(self, issues: List[ErrorIssue]) -> List[ErrorIssue]:
        """Detect regression issues."""
        regressions = []

        for issue in issues:
            if issue.status == 'regression' or issue.status == 'regressed':
                regressions.append(issue)

        return regressions

    def analyze_trends(
        self,
        issues: List[ErrorIssue],
        days: int = 7
    ) -> Dict[str, Any]:
        """Analyze error trends over time."""
        now = datetime.now()
        cutoff = now - timedelta(days=days)

        # Filter to time range
        recent_issues = [i for i in issues if i.first_seen >= cutoff]

        # Group by day
        by_day = defaultdict(lambda: {'count': 0, 'user_count': 0, 'issues': 0})

        for issue in recent_issues:
            day = issue.first_seen.date()
            by_day[day]['count'] += issue.count
            by_day[day]['user_count'] += issue.user_count
            by_day[day]['issues'] += 1

        # Calculate trends
        days_sorted = sorted(by_day.keys())

        if len(days_sorted) >= 2:
            # Compare first half vs second half
            midpoint = len(days_sorted) // 2
            first_half = days_sorted[:midpoint]
            second_half = days_sorted[midpoint:]

            first_avg = sum(by_day[d]['count'] for d in first_half) / len(first_half)
            second_avg = sum(by_day[d]['count'] for d in second_half) / len(second_half)

            if first_avg > 0:
                trend_pct = ((second_avg - first_avg) / first_avg) * 100
            else:
                trend_pct = 0

            trend = 'increasing' if trend_pct > 10 else 'decreasing' if trend_pct < -10 else 'stable'
        else:
            trend_pct = 0
            trend = 'insufficient_data'

        return {
            'period_days': days,
            'total_issues': len(recent_issues),
            'total_events': sum(i.count for i in recent_issues),
            'total_users': sum(i.user_count for i in recent_issues),
            'by_day': {str(k): v for k, v in by_day.items()},
            'trend': trend,
            'trend_percentage': round(trend_pct, 1)
        }

    def generate_triage_report(
        self,
        issues: List[ErrorIssue],
        include_patterns: bool = True
    ) -> Dict[str, Any]:
        """Generate comprehensive triage report."""
        # Calculate priorities
        priorities = {}
        for issue in issues:
            priority = self.calculate_priority_score(issue)
            priorities[issue.id] = priority

        # Group by priority
        by_priority = {
            'P0': [],
            'P1': [],
            'P2': [],
            'P3': []
        }

        for issue in issues:
            priority = priorities[issue.id]
            by_priority[priority.priority].append({
                'id': issue.id,
                'title': issue.title,
                'score': priority.score,
                'count': issue.count,
                'user_count': issue.user_count,
                'status': issue.status,
                'recommendation': priority.recommendation
            })

        # Sort within each priority by score
        for p in by_priority.values():
            p.sort(key=lambda x: x['score'], reverse=True)

        report = {
            'generated_at': datetime.now().isoformat(),
            'total_issues': len(issues),
            'by_priority': {
                'P0': {
                    'count': len(by_priority['P0']),
                    'issues': by_priority['P0']
                },
                'P1': {
                    'count': len(by_priority['P1']),
                    'issues': by_priority['P1']
                },
                'P2': {
                    'count': len(by_priority['P2']),
                    'issues': by_priority['P2']
                },
                'P3': {
                    'count': len(by_priority['P3']),
                    'issues': by_priority['P3']
                }
            }
        }

        # Add patterns if requested
        if include_patterns:
            patterns = self.detect_patterns(issues)
            report['patterns'] = [asdict(p) for p in patterns]

        # Add regressions
        regressions = self.detect_regressions(issues)
        report['regressions'] = {
            'count': len(regressions),
            'issues': [{'id': i.id, 'title': i.title, 'count': i.count} for i in regressions]
        }

        return report


def format_text_report(report: Dict[str, Any]) -> str:
    """Format report as text."""
    lines = []

    lines.append("=" * 80)
    lines.append("ERROR TRIAGE REPORT")
    lines.append("=" * 80)
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Total Issues: {report['total_issues']}")
    lines.append("")

    # Priority breakdown
    for priority in ['P0', 'P1', 'P2', 'P3']:
        data = report['by_priority'][priority]
        count = data['count']

        if priority == 'P0':
            icon = '🚨'
            label = 'CRITICAL'
        elif priority == 'P1':
            icon = '⚠️'
            label = 'HIGH'
        elif priority == 'P2':
            icon = '📌'
            label = 'MEDIUM'
        else:
            icon = '📝'
            label = 'LOW'

        lines.append(f"{icon} {priority} - {label} ({count} issues)")
        lines.append("-" * 80)

        for i, issue in enumerate(data['issues'][:5], 1):  # Top 5
            lines.append(f"{i}. {issue['title']}")
            lines.append(f"   Score: {issue['score']} | Events: {issue['count']} | Users: {issue['user_count']}")
            lines.append(f"   → {issue['recommendation']}")
            lines.append("")

        if count > 5:
            lines.append(f"   ... and {count - 5} more")
            lines.append("")

    # Regressions
    if report['regressions']['count'] > 0:
        lines.append("🔄 REGRESSIONS")
        lines.append("-" * 80)
        for issue in report['regressions']['issues']:
            lines.append(f"- {issue['title']} ({issue['count']} events)")
        lines.append("")

    # Patterns
    if 'patterns' in report and report['patterns']:
        lines.append("🔍 DETECTED PATTERNS")
        lines.append("-" * 80)
        for pattern in report['patterns'][:5]:
            lines.append(f"- {pattern['description']}")
            lines.append(f"  Type: {pattern['pattern_type']} | Issues: {len(pattern['issues'])} | Confidence: {pattern['confidence']:.0%}")
            lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Error pattern analysis and triage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--sentry-token',
        default=os.getenv('SENTRY_AUTH_TOKEN'),
        help='Sentry API token (or set SENTRY_AUTH_TOKEN env var)'
    )

    parser.add_argument(
        '--org',
        required=True,
        help='Sentry organization slug'
    )

    parser.add_argument(
        '--project',
        required=True,
        help='Project slug'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to analyze (default: 7)'
    )

    parser.add_argument(
        '--query',
        default='is:unresolved',
        help='Issue query filter (default: is:unresolved)'
    )

    parser.add_argument(
        '--report-type',
        choices=['priority', 'patterns', 'regressions', 'trends', 'full'],
        default='full',
        help='Report type (default: full)'
    )

    parser.add_argument(
        '--detect-regressions',
        action='store_true',
        help='Only show regressions'
    )

    parser.add_argument(
        '--output',
        help='Output file path'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
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

    # Validate token
    if not args.sentry_token:
        logger.error("Sentry API token required (--sentry-token or SENTRY_AUTH_TOKEN)")
        sys.exit(1)

    # Create analyzer
    sentry = SentryAnalyzer(args.sentry_token)
    analyzer = ErrorAnalyzer(sentry)

    # Fetch issues
    logger.info(f"Fetching issues from {args.org}/{args.project}...")

    stats_period = f"{args.days}d"
    issues = sentry.get_issues(args.org, args.project, args.query, stats_period)

    logger.info(f"Found {len(issues)} issues")

    if not issues:
        logger.warning("No issues found")
        sys.exit(0)

    # Generate report based on type
    if args.detect_regressions or args.report_type == 'regressions':
        regressions = analyzer.detect_regressions(issues)

        report = {
            'regressions': {
                'count': len(regressions),
                'issues': [
                    {
                        'id': i.id,
                        'title': i.title,
                        'count': i.count,
                        'user_count': i.user_count,
                        'first_seen': i.first_seen.isoformat(),
                        'last_seen': i.last_seen.isoformat()
                    }
                    for i in regressions
                ]
            }
        }

    elif args.report_type == 'patterns':
        patterns = analyzer.detect_patterns(issues)

        report = {
            'patterns': [asdict(p) for p in patterns]
        }

    elif args.report_type == 'trends':
        report = analyzer.analyze_trends(issues, args.days)

    else:
        # Full triage report
        report = analyzer.generate_triage_report(issues, include_patterns=True)

        # Add trends
        report['trends'] = analyzer.analyze_trends(issues, args.days)

    # Output report
    if args.json:
        output = json.dumps(report, indent=2)
    else:
        output = format_text_report(report)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        logger.info(f"Report written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
