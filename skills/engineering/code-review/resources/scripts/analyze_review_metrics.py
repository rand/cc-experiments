#!/usr/bin/env python3
"""
Analyze PR review metrics from GitHub.

Tracks key code review metrics:
- Review turnaround time (time to first review)
- Review depth (comments per 100 lines)
- Approval time (time to approval)
- Iteration count (review cycles)
- Reviewer activity
- PR size distribution

Usage:
    ./analyze_review_metrics.py --repo owner/repo --token YOUR_TOKEN
    ./analyze_review_metrics.py --repo owner/repo --days 30
    ./analyze_review_metrics.py --repo owner/repo --json
    ./analyze_review_metrics.py --repo owner/repo --reviewer alice
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

try:
    from github import Github
    from github.PullRequest import PullRequest
except ImportError:
    print("Error: PyGithub not installed. Run: pip install PyGithub", file=sys.stderr)
    sys.exit(1)


@dataclass
class PRMetrics:
    """Metrics for a single PR."""
    number: int
    title: str
    author: str
    created_at: datetime
    merged_at: Optional[datetime]
    lines_changed: int
    files_changed: int
    comments_count: int
    review_count: int
    iteration_count: int
    first_review_hours: Optional[float]
    approval_hours: Optional[float]
    reviewers: List[str] = field(default_factory=list)


@dataclass
class AggregateMetrics:
    """Aggregate metrics across multiple PRs."""
    total_prs: int
    total_lines: int
    avg_pr_size: float
    avg_turnaround_hours: float
    avg_approval_hours: float
    avg_comments_per_100_lines: float
    avg_iteration_count: float
    median_turnaround_hours: float
    median_approval_hours: float
    reviewer_stats: Dict[str, Dict[str, Any]]
    pr_size_distribution: Dict[str, int]
    status_counts: Dict[str, int]


class GitHubMetricsCollector:
    """Collects review metrics from GitHub."""

    def __init__(self, repo_name: str, token: str):
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_name)

    def collect_metrics(
        self,
        days: int = 7,
        state: str = "closed",
        reviewer: Optional[str] = None
    ) -> List[PRMetrics]:
        """Collect metrics for PRs in the specified time period."""
        since = datetime.now() - timedelta(days=days)
        prs = self.repo.get_pulls(state=state, sort="updated", direction="desc")

        metrics = []
        for pr in prs:
            # Stop when we've gone back far enough
            if pr.updated_at < since:
                break

            # Filter by reviewer if specified
            if reviewer:
                reviewers = [r.user.login for r in pr.get_reviews()]
                if reviewer not in reviewers:
                    continue

            pr_metrics = self._analyze_pr(pr)
            if pr_metrics:
                metrics.append(pr_metrics)

        return metrics

    def _analyze_pr(self, pr: PullRequest) -> Optional[PRMetrics]:
        """Analyze a single PR."""
        try:
            # Basic info
            lines_changed = pr.additions + pr.deletions
            files_changed = pr.changed_files

            # Reviews
            reviews = list(pr.get_reviews())
            review_count = len(reviews)

            # Comments
            review_comments = list(pr.get_review_comments())
            issue_comments = list(pr.get_issue_comments())
            comments_count = len(review_comments) + len(issue_comments)

            # Reviewers
            reviewers = list(set(r.user.login for r in reviews if r.user))

            # Time to first review
            first_review_hours = None
            if reviews:
                first_review = min(reviews, key=lambda r: r.submitted_at)
                delta = first_review.submitted_at - pr.created_at
                first_review_hours = delta.total_seconds() / 3600

            # Time to approval
            approval_hours = None
            approved_reviews = [r for r in reviews if r.state == "APPROVED"]
            if approved_reviews:
                first_approval = min(approved_reviews, key=lambda r: r.submitted_at)
                delta = first_approval.submitted_at - pr.created_at
                approval_hours = delta.total_seconds() / 3600

            # Iteration count (rough estimate based on commits after first review)
            iteration_count = 1
            if reviews and pr.commits > 1:
                # Count commits after first review
                first_review_time = reviews[0].submitted_at
                commits = list(pr.get_commits())
                commits_after_review = [
                    c for c in commits
                    if c.commit.author.date > first_review_time
                ]
                # Each batch of commits is an iteration
                iteration_count = 1 + len(commits_after_review)

            return PRMetrics(
                number=pr.number,
                title=pr.title,
                author=pr.user.login if pr.user else "unknown",
                created_at=pr.created_at,
                merged_at=pr.merged_at,
                lines_changed=lines_changed,
                files_changed=files_changed,
                comments_count=comments_count,
                review_count=review_count,
                iteration_count=iteration_count,
                first_review_hours=first_review_hours,
                approval_hours=approval_hours,
                reviewers=reviewers,
            )

        except Exception as e:
            print(f"Error analyzing PR #{pr.number}: {e}", file=sys.stderr)
            return None


class MetricsAnalyzer:
    """Analyzes collected metrics."""

    def __init__(self, metrics: List[PRMetrics]):
        self.metrics = metrics

    def aggregate(self) -> AggregateMetrics:
        """Compute aggregate statistics."""
        if not self.metrics:
            return self._empty_metrics()

        total_prs = len(self.metrics)
        total_lines = sum(m.lines_changed for m in self.metrics)
        avg_pr_size = total_lines / total_prs

        # Turnaround time (time to first review)
        turnaround_times = [m.first_review_hours for m in self.metrics if m.first_review_hours]
        avg_turnaround = sum(turnaround_times) / len(turnaround_times) if turnaround_times else 0
        median_turnaround = self._median(turnaround_times) if turnaround_times else 0

        # Approval time
        approval_times = [m.approval_hours for m in self.metrics if m.approval_hours]
        avg_approval = sum(approval_times) / len(approval_times) if approval_times else 0
        median_approval = self._median(approval_times) if approval_times else 0

        # Comments per 100 lines
        total_comments = sum(m.comments_count for m in self.metrics)
        avg_comments_per_100 = (total_comments / total_lines * 100) if total_lines > 0 else 0

        # Iteration count
        avg_iterations = sum(m.iteration_count for m in self.metrics) / total_prs

        # Reviewer stats
        reviewer_stats = self._compute_reviewer_stats()

        # PR size distribution
        size_distribution = self._compute_size_distribution()

        # Status counts
        status_counts = {
            "merged": sum(1 for m in self.metrics if m.merged_at),
            "not_merged": sum(1 for m in self.metrics if not m.merged_at),
        }

        return AggregateMetrics(
            total_prs=total_prs,
            total_lines=total_lines,
            avg_pr_size=avg_pr_size,
            avg_turnaround_hours=avg_turnaround,
            avg_approval_hours=avg_approval,
            avg_comments_per_100_lines=avg_comments_per_100,
            avg_iteration_count=avg_iterations,
            median_turnaround_hours=median_turnaround,
            median_approval_hours=median_approval,
            reviewer_stats=reviewer_stats,
            pr_size_distribution=size_distribution,
            status_counts=status_counts,
        )

    def _compute_reviewer_stats(self) -> Dict[str, Dict[str, Any]]:
        """Compute per-reviewer statistics."""
        reviewer_data = defaultdict(lambda: {
            "review_count": 0,
            "total_turnaround": 0,
            "total_comments": 0,
            "prs_reviewed": [],
        })

        for pr_metrics in self.metrics:
            for reviewer in pr_metrics.reviewers:
                data = reviewer_data[reviewer]
                data["review_count"] += 1
                data["prs_reviewed"].append(pr_metrics.number)

                if pr_metrics.first_review_hours:
                    data["total_turnaround"] += pr_metrics.first_review_hours

                # Approximate comments per reviewer (evenly distributed)
                if pr_metrics.reviewers:
                    comments_per_reviewer = pr_metrics.comments_count / len(pr_metrics.reviewers)
                    data["total_comments"] += comments_per_reviewer

        # Compute averages
        stats = {}
        for reviewer, data in reviewer_data.items():
            count = data["review_count"]
            stats[reviewer] = {
                "review_count": count,
                "avg_turnaround_hours": data["total_turnaround"] / count if count > 0 else 0,
                "avg_comments": data["total_comments"] / count if count > 0 else 0,
                "prs_reviewed": data["prs_reviewed"][:5],  # Sample of PRs
            }

        # Sort by review count
        return dict(sorted(stats.items(), key=lambda x: x[1]["review_count"], reverse=True))

    def _compute_size_distribution(self) -> Dict[str, int]:
        """Compute PR size distribution."""
        distribution = {
            "tiny": 0,      # <50 lines
            "small": 0,     # 50-200 lines
            "medium": 0,    # 200-500 lines
            "large": 0,     # 500-1000 lines
            "huge": 0,      # >1000 lines
        }

        for pr_metrics in self.metrics:
            lines = pr_metrics.lines_changed
            if lines < 50:
                distribution["tiny"] += 1
            elif lines < 200:
                distribution["small"] += 1
            elif lines < 500:
                distribution["medium"] += 1
            elif lines < 1000:
                distribution["large"] += 1
            else:
                distribution["huge"] += 1

        return distribution

    def _median(self, values: List[float]) -> float:
        """Compute median of values."""
        if not values:
            return 0
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            return sorted_values[n // 2]

    def _empty_metrics(self) -> AggregateMetrics:
        """Return empty metrics when no data available."""
        return AggregateMetrics(
            total_prs=0,
            total_lines=0,
            avg_pr_size=0,
            avg_turnaround_hours=0,
            avg_approval_hours=0,
            avg_comments_per_100_lines=0,
            avg_iteration_count=0,
            median_turnaround_hours=0,
            median_approval_hours=0,
            reviewer_stats={},
            pr_size_distribution={},
            status_counts={},
        )


def format_metrics_human(metrics: AggregateMetrics) -> str:
    """Format metrics for human reading."""
    lines = []

    lines.append("=" * 70)
    lines.append("CODE REVIEW METRICS REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Overall stats
    lines.append("Overall Statistics:")
    lines.append(f"  Total PRs analyzed: {metrics.total_prs}")
    lines.append(f"  Total lines changed: {metrics.total_lines:,}")
    lines.append(f"  Average PR size: {metrics.avg_pr_size:.0f} lines")
    lines.append("")

    # Review timing
    lines.append("Review Timing:")
    lines.append(f"  Avg time to first review: {metrics.avg_turnaround_hours:.1f} hours "
                 f"(median: {metrics.median_turnaround_hours:.1f}h)")
    lines.append(f"  Avg time to approval: {metrics.avg_approval_hours:.1f} hours "
                 f"(median: {metrics.median_approval_hours:.1f}h)")
    lines.append(f"  Avg iteration count: {metrics.avg_iteration_count:.1f}")
    lines.append("")

    # Review depth
    lines.append("Review Depth:")
    lines.append(f"  Avg comments per 100 lines: {metrics.avg_comments_per_100_lines:.1f}")
    lines.append("")

    # PR size distribution
    lines.append("PR Size Distribution:")
    for size, count in metrics.pr_size_distribution.items():
        percentage = (count / metrics.total_prs * 100) if metrics.total_prs > 0 else 0
        lines.append(f"  {size.capitalize():8s}: {count:3d} PRs ({percentage:5.1f}%)")
    lines.append("")

    # Status
    lines.append("PR Status:")
    for status, count in metrics.status_counts.items():
        percentage = (count / metrics.total_prs * 100) if metrics.total_prs > 0 else 0
        lines.append(f"  {status.replace('_', ' ').capitalize():12s}: {count:3d} PRs ({percentage:5.1f}%)")
    lines.append("")

    # Top reviewers
    if metrics.reviewer_stats:
        lines.append("Top Reviewers (by review count):")
        for i, (reviewer, stats) in enumerate(list(metrics.reviewer_stats.items())[:10], 1):
            lines.append(f"  {i:2d}. {reviewer:20s} - "
                        f"{stats['review_count']:3d} reviews, "
                        f"avg turnaround: {stats['avg_turnaround_hours']:5.1f}h, "
                        f"avg comments: {stats['avg_comments']:4.1f}")
    lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


def format_metrics_json(metrics: AggregateMetrics) -> str:
    """Format metrics as JSON."""
    data = {
        "overall": {
            "total_prs": metrics.total_prs,
            "total_lines": metrics.total_lines,
            "avg_pr_size": metrics.avg_pr_size,
        },
        "timing": {
            "avg_turnaround_hours": metrics.avg_turnaround_hours,
            "median_turnaround_hours": metrics.median_turnaround_hours,
            "avg_approval_hours": metrics.avg_approval_hours,
            "median_approval_hours": metrics.median_approval_hours,
            "avg_iteration_count": metrics.avg_iteration_count,
        },
        "depth": {
            "avg_comments_per_100_lines": metrics.avg_comments_per_100_lines,
        },
        "size_distribution": metrics.pr_size_distribution,
        "status_counts": metrics.status_counts,
        "reviewer_stats": metrics.reviewer_stats,
    }
    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze PR review metrics from GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --repo owner/repo --token YOUR_TOKEN
  %(prog)s --repo owner/repo --days 30
  %(prog)s --repo owner/repo --json
  %(prog)s --repo owner/repo --reviewer alice

Environment Variables:
  GITHUB_TOKEN: GitHub personal access token (can be used instead of --token)
        """
    )

    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repository in format owner/repo"
    )
    parser.add_argument(
        "--token",
        help="GitHub personal access token (or set GITHUB_TOKEN env var)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to analyze (default: 7)"
    )
    parser.add_argument(
        "--state",
        default="closed",
        choices=["open", "closed", "all"],
        help="PR state to analyze (default: closed)"
    )
    parser.add_argument(
        "--reviewer",
        help="Filter by specific reviewer"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    args = parser.parse_args()

    # Get token
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GitHub token required. Use --token or set GITHUB_TOKEN env var.",
              file=sys.stderr)
        sys.exit(1)

    # Collect metrics
    print(f"Collecting metrics for {args.repo} (last {args.days} days)...", file=sys.stderr)
    collector = GitHubMetricsCollector(args.repo, token)
    pr_metrics = collector.collect_metrics(
        days=args.days,
        state=args.state,
        reviewer=args.reviewer
    )

    if not pr_metrics:
        print("No PRs found in the specified time period.", file=sys.stderr)
        sys.exit(0)

    print(f"Analyzed {len(pr_metrics)} PRs.", file=sys.stderr)

    # Analyze metrics
    analyzer = MetricsAnalyzer(pr_metrics)
    aggregate = analyzer.aggregate()

    # Output
    if args.json:
        print(format_metrics_json(aggregate))
    else:
        print(format_metrics_human(aggregate))


if __name__ == "__main__":
    main()
