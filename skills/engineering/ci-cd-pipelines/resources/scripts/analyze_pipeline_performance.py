#!/usr/bin/env python3
"""
Pipeline Performance Analyzer

Analyzes CI/CD pipeline performance, identifies bottlenecks, tracks flaky tests,
and provides optimization recommendations across multiple platforms.

Usage:
    ./analyze_pipeline_performance.py --platform github-actions --repo owner/repo
    ./analyze_pipeline_performance.py --platform github-actions --runs 100 --compare
    ./analyze_pipeline_performance.py --platform gitlab --project-id 12345 --json
    ./analyze_pipeline_performance.py --file pipeline-data.json --analyze

Features:
    - Multi-platform support (GitHub Actions, GitLab CI, Jenkins, CircleCI)
    - Build time analysis and trend detection
    - Bottleneck identification
    - Flaky test tracking
    - Cost analysis and optimization recommendations
    - JSON output for dashboards
    - Historical trend analysis
    - Detailed performance reports

Author: Skills Team
Version: 1.0.0
"""

import argparse
import json
import sys
import os
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import subprocess


@dataclass
class JobMetrics:
    """Metrics for a single job"""
    name: str
    duration_seconds: float
    success: bool
    runner: Optional[str] = None
    queue_time_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineRun:
    """Represents a single pipeline run"""
    id: str
    number: int
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    jobs: List[JobMetrics]
    trigger: str
    branch: str
    commit_sha: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data


@dataclass
class PerformanceReport:
    """Performance analysis report"""
    total_runs: int
    success_rate: float
    average_duration: float
    median_duration: float
    p95_duration: float
    p99_duration: float
    slowest_jobs: List[Dict[str, Any]]
    bottlenecks: List[Dict[str, Any]]
    flaky_tests: List[Dict[str, Any]]
    cost_estimate: Optional[Dict[str, Any]]
    recommendations: List[str]
    trends: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PlatformAPI:
    """Base class for platform-specific API interactions"""

    def fetch_runs(self, limit: int = 100) -> List[PipelineRun]:
        """Fetch pipeline runs from platform"""
        raise NotImplementedError

    def fetch_job_details(self, run_id: str) -> List[JobMetrics]:
        """Fetch detailed job metrics for a run"""
        raise NotImplementedError


class GitHubActionsAPI(PlatformAPI):
    """GitHub Actions API client"""

    def __init__(self, repo: str, token: Optional[str] = None):
        self.repo = repo
        self.token = token or os.environ.get('GITHUB_TOKEN')
        if not self.token:
            print("Warning: No GitHub token provided. Rate limits will apply.", file=sys.stderr)

    def _gh_api(self, endpoint: str) -> Dict:
        """Call GitHub API using gh CLI"""
        cmd = ['gh', 'api', endpoint]
        if self.token:
            cmd.extend(['--header', f'Authorization: token {self.token}'])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error calling GitHub API: {e.stderr}", file=sys.stderr)
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing GitHub API response: {e}", file=sys.stderr)
            return {}

    def fetch_runs(self, limit: int = 100) -> List[PipelineRun]:
        """Fetch workflow runs from GitHub Actions"""
        runs = []
        page = 1
        per_page = min(100, limit)

        while len(runs) < limit:
            data = self._gh_api(f'/repos/{self.repo}/actions/runs?page={page}&per_page={per_page}')
            workflow_runs = data.get('workflow_runs', [])

            if not workflow_runs:
                break

            for run_data in workflow_runs:
                created_at = datetime.fromisoformat(run_data['created_at'].replace('Z', '+00:00'))
                started_at = datetime.fromisoformat(run_data['run_started_at'].replace('Z', '+00:00')) if run_data.get('run_started_at') else None
                completed_at = datetime.fromisoformat(run_data['updated_at'].replace('Z', '+00:00')) if run_data.get('updated_at') else None

                duration = None
                if started_at and completed_at:
                    duration = (completed_at - started_at).total_seconds()

                # Fetch job details
                jobs = self.fetch_job_details(run_data['id'])

                run = PipelineRun(
                    id=str(run_data['id']),
                    number=run_data['run_number'],
                    status=run_data['conclusion'] or run_data['status'],
                    created_at=created_at,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_seconds=duration,
                    jobs=jobs,
                    trigger=run_data.get('event', 'unknown'),
                    branch=run_data.get('head_branch', 'unknown'),
                    commit_sha=run_data['head_sha']
                )
                runs.append(run)

                if len(runs) >= limit:
                    break

            page += 1

        return runs

    def fetch_job_details(self, run_id: str) -> List[JobMetrics]:
        """Fetch job details for a workflow run"""
        data = self._gh_api(f'/repos/{self.repo}/actions/runs/{run_id}/jobs')
        jobs = []

        for job_data in data.get('jobs', []):
            started_at = datetime.fromisoformat(job_data['started_at'].replace('Z', '+00:00')) if job_data.get('started_at') else None
            completed_at = datetime.fromisoformat(job_data['completed_at'].replace('Z', '+00:00')) if job_data.get('completed_at') else None

            duration = None
            if started_at and completed_at:
                duration = (completed_at - started_at).total_seconds()

            job = JobMetrics(
                name=job_data['name'],
                duration_seconds=duration if duration else 0,
                success=job_data['conclusion'] == 'success',
                runner=job_data.get('runner_name')
            )
            jobs.append(job)

        return jobs


class GitLabCIAPI(PlatformAPI):
    """GitLab CI API client"""

    def __init__(self, project_id: str, token: Optional[str] = None, gitlab_url: str = 'https://gitlab.com'):
        self.project_id = project_id
        self.token = token or os.environ.get('GITLAB_TOKEN')
        self.gitlab_url = gitlab_url
        if not self.token:
            print("Warning: No GitLab token provided. Authentication required.", file=sys.stderr)

    def _gitlab_api(self, endpoint: str) -> Any:
        """Call GitLab API using curl"""
        url = f"{self.gitlab_url}/api/v4{endpoint}"
        headers = []
        if self.token:
            headers = ['-H', f'PRIVATE-TOKEN: {self.token}']

        cmd = ['curl', '-s'] + headers + [url]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error calling GitLab API: {e.stderr}", file=sys.stderr)
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing GitLab API response: {e}", file=sys.stderr)
            return {}

    def fetch_runs(self, limit: int = 100) -> List[PipelineRun]:
        """Fetch pipeline runs from GitLab CI"""
        runs = []
        page = 1
        per_page = min(100, limit)

        while len(runs) < limit:
            data = self._gitlab_api(f'/projects/{self.project_id}/pipelines?page={page}&per_page={per_page}')

            if not isinstance(data, list) or not data:
                break

            for pipeline_data in data:
                created_at = datetime.fromisoformat(pipeline_data['created_at'].replace('Z', '+00:00'))
                started_at = datetime.fromisoformat(pipeline_data.get('started_at', pipeline_data['created_at']).replace('Z', '+00:00'))
                completed_at = datetime.fromisoformat(pipeline_data['updated_at'].replace('Z', '+00:00')) if pipeline_data.get('updated_at') else None

                duration = pipeline_data.get('duration')

                # Fetch job details
                jobs = self.fetch_job_details(pipeline_data['id'])

                run = PipelineRun(
                    id=str(pipeline_data['id']),
                    number=pipeline_data['iid'],
                    status=pipeline_data['status'],
                    created_at=created_at,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_seconds=duration,
                    jobs=jobs,
                    trigger=pipeline_data.get('source', 'unknown'),
                    branch=pipeline_data.get('ref', 'unknown'),
                    commit_sha=pipeline_data['sha']
                )
                runs.append(run)

                if len(runs) >= limit:
                    break

            page += 1

        return runs

    def fetch_job_details(self, pipeline_id: str) -> List[JobMetrics]:
        """Fetch job details for a pipeline"""
        data = self._gitlab_api(f'/projects/{self.project_id}/pipelines/{pipeline_id}/jobs')
        jobs = []

        if isinstance(data, list):
            for job_data in data:
                duration = job_data.get('duration', 0)

                job = JobMetrics(
                    name=job_data['name'],
                    duration_seconds=duration if duration else 0,
                    success=job_data['status'] == 'success',
                    runner=job_data.get('runner', {}).get('description') if job_data.get('runner') else None
                )
                jobs.append(job)

        return jobs


class PerformanceAnalyzer:
    """Analyzes pipeline performance metrics"""

    def __init__(self, runs: List[PipelineRun], verbose: bool = False):
        self.runs = runs
        self.verbose = verbose

    def analyze(self) -> PerformanceReport:
        """Perform complete performance analysis"""
        if not self.runs:
            print("No pipeline runs to analyze", file=sys.stderr)
            return self._empty_report()

        # Calculate basic metrics
        total_runs = len(self.runs)
        successful_runs = [r for r in self.runs if r.status in ['success', 'completed']]
        success_rate = len(successful_runs) / total_runs if total_runs > 0 else 0

        # Duration statistics
        durations = [r.duration_seconds for r in self.runs if r.duration_seconds]
        avg_duration = statistics.mean(durations) if durations else 0
        median_duration = statistics.median(durations) if durations else 0
        p95_duration = self._percentile(durations, 95) if durations else 0
        p99_duration = self._percentile(durations, 99) if durations else 0

        # Identify slowest jobs
        slowest_jobs = self._find_slowest_jobs()

        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks()

        # Track flaky tests
        flaky_tests = self._find_flaky_tests()

        # Estimate costs
        cost_estimate = self._estimate_costs()

        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_duration, slowest_jobs, bottlenecks, flaky_tests
        )

        # Analyze trends
        trends = self._analyze_trends()

        return PerformanceReport(
            total_runs=total_runs,
            success_rate=success_rate * 100,
            average_duration=avg_duration,
            median_duration=median_duration,
            p95_duration=p95_duration,
            p99_duration=p99_duration,
            slowest_jobs=slowest_jobs,
            bottlenecks=bottlenecks,
            flaky_tests=flaky_tests,
            cost_estimate=cost_estimate,
            recommendations=recommendations,
            trends=trends
        )

    def _empty_report(self) -> PerformanceReport:
        """Return empty report"""
        return PerformanceReport(
            total_runs=0,
            success_rate=0,
            average_duration=0,
            median_duration=0,
            p95_duration=0,
            p99_duration=0,
            slowest_jobs=[],
            bottlenecks=[],
            flaky_tests=[],
            cost_estimate=None,
            recommendations=[],
            trends={}
        )

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _find_slowest_jobs(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Identify slowest jobs across all runs"""
        job_durations = defaultdict(list)

        for run in self.runs:
            for job in run.jobs:
                if job.duration_seconds > 0:
                    job_durations[job.name].append(job.duration_seconds)

        # Calculate average duration for each job
        job_stats = []
        for job_name, durations in job_durations.items():
            avg_duration = statistics.mean(durations)
            max_duration = max(durations)
            min_duration = min(durations)

            job_stats.append({
                'name': job_name,
                'average_duration': avg_duration,
                'max_duration': max_duration,
                'min_duration': min_duration,
                'runs': len(durations),
                'variability': max_duration - min_duration
            })

        # Sort by average duration
        job_stats.sort(key=lambda x: x['average_duration'], reverse=True)

        return job_stats[:top_n]

    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify pipeline bottlenecks"""
        bottlenecks = []

        # Analyze job dependencies and serial execution
        for run in self.runs:
            if not run.jobs:
                continue

            # Find jobs that take >50% of total pipeline time
            total_duration = run.duration_seconds or sum(j.duration_seconds for j in run.jobs)

            for job in run.jobs:
                if job.duration_seconds > 0:
                    percentage = (job.duration_seconds / total_duration * 100) if total_duration > 0 else 0
                    if percentage > 50:
                        bottlenecks.append({
                            'run_id': run.id,
                            'job_name': job.name,
                            'duration': job.duration_seconds,
                            'percentage_of_total': percentage,
                            'issue': f'Job takes {percentage:.1f}% of pipeline time'
                        })

        # Deduplicate by job name and return unique bottlenecks
        unique_bottlenecks = {}
        for bn in bottlenecks:
            job_name = bn['job_name']
            if job_name not in unique_bottlenecks or bn['percentage_of_total'] > unique_bottlenecks[job_name]['percentage_of_total']:
                unique_bottlenecks[job_name] = bn

        return list(unique_bottlenecks.values())

    def _find_flaky_tests(self) -> List[Dict[str, Any]]:
        """Identify flaky tests (jobs that fail intermittently)"""
        job_outcomes = defaultdict(list)

        for run in self.runs:
            for job in run.jobs:
                job_outcomes[job.name].append(job.success)

        flaky_tests = []
        for job_name, outcomes in job_outcomes.items():
            if len(outcomes) < 3:
                continue

            successes = sum(outcomes)
            failures = len(outcomes) - successes

            # Consider flaky if has both successes and failures
            if successes > 0 and failures > 0:
                failure_rate = failures / len(outcomes) * 100
                flaky_tests.append({
                    'name': job_name,
                    'total_runs': len(outcomes),
                    'failures': failures,
                    'failure_rate': failure_rate,
                    'severity': 'high' if failure_rate > 20 else 'medium' if failure_rate > 5 else 'low'
                })

        # Sort by failure rate
        flaky_tests.sort(key=lambda x: x['failure_rate'], reverse=True)

        return flaky_tests

    def _estimate_costs(self) -> Dict[str, Any]:
        """Estimate compute costs"""
        # Rough cost estimates (GitHub Actions pricing as example)
        COST_PER_MINUTE_LINUX = 0.008  # $0.008 per minute for Linux runners
        COST_PER_MINUTE_WINDOWS = 0.016  # $0.016 per minute for Windows runners
        COST_PER_MINUTE_MACOS = 0.08  # $0.08 per minute for macOS runners

        total_minutes = sum(r.duration_seconds / 60 for r in self.runs if r.duration_seconds)

        # Assume mostly Linux runners
        estimated_monthly_cost = total_minutes * COST_PER_MINUTE_LINUX

        # Calculate potential savings with optimizations (assume 20% reduction possible)
        potential_savings = estimated_monthly_cost * 0.20

        return {
            'total_compute_minutes': total_minutes,
            'estimated_monthly_cost_usd': estimated_monthly_cost,
            'potential_monthly_savings_usd': potential_savings,
            'note': 'Costs based on GitHub Actions Linux runner pricing'
        }

    def _generate_recommendations(
        self,
        avg_duration: float,
        slowest_jobs: List[Dict],
        bottlenecks: List[Dict],
        flaky_tests: List[Dict]
    ) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []

        # Duration-based recommendations
        if avg_duration > 1800:  # > 30 minutes
            recommendations.append(
                "Pipeline average duration is high (>30 min). Consider:\n"
                "  - Parallelizing independent jobs\n"
                "  - Adding caching for dependencies\n"
                "  - Sharding large test suites"
            )

        # Slowest jobs recommendations
        if slowest_jobs:
            slowest = slowest_jobs[0]
            recommendations.append(
                f"Slowest job '{slowest['name']}' takes {slowest['average_duration']:.1f}s on average. Consider:\n"
                f"  - Profiling this job for optimization opportunities\n"
                f"  - Splitting into smaller parallel jobs\n"
                f"  - Optimizing test execution"
            )

        # Bottleneck recommendations
        if bottlenecks:
            recommendations.append(
                f"Found {len(bottlenecks)} bottleneck(s) where single jobs dominate pipeline time. Consider:\n"
                "  - Running more jobs in parallel\n"
                "  - Using matrix strategies for parallelization\n"
                "  - Optimizing serial dependencies"
            )

        # Flaky test recommendations
        if flaky_tests:
            high_flake = [t for t in flaky_tests if t['severity'] == 'high']
            if high_flake:
                recommendations.append(
                    f"Found {len(high_flake)} highly flaky test(s) with >20% failure rate. Consider:\n"
                    "  - Investigating and fixing root causes\n"
                    "  - Adding retries for E2E tests\n"
                    "  - Increasing timeouts if timing-related"
                )

        # Cache recommendations
        recommendations.append(
            "Performance optimization checklist:\n"
            "  - Enable dependency caching (npm, pip, maven, etc.)\n"
            "  - Use Docker layer caching for container builds\n"
            "  - Cache build artifacts between jobs\n"
            "  - Consider self-hosted runners for better performance"
        )

        if not recommendations:
            recommendations.append("Pipeline performance looks good! No major issues detected.")

        return recommendations

    def _analyze_trends(self) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        if len(self.runs) < 10:
            return {'note': 'Insufficient data for trend analysis (need 10+ runs)'}

        # Sort runs by date
        sorted_runs = sorted(self.runs, key=lambda r: r.created_at)

        # Split into first half and second half
        mid_point = len(sorted_runs) // 2
        first_half = sorted_runs[:mid_point]
        second_half = sorted_runs[mid_point:]

        # Calculate average durations
        first_half_avg = statistics.mean([r.duration_seconds for r in first_half if r.duration_seconds])
        second_half_avg = statistics.mean([r.duration_seconds for r in second_half if r.duration_seconds])

        # Calculate success rates
        first_half_success = sum(1 for r in first_half if r.status in ['success', 'completed']) / len(first_half) * 100
        second_half_success = sum(1 for r in second_half if r.status in ['success', 'completed']) / len(second_half) * 100

        # Determine trends
        duration_trend = 'improving' if second_half_avg < first_half_avg else 'degrading' if second_half_avg > first_half_avg else 'stable'
        success_trend = 'improving' if second_half_success > first_half_success else 'degrading' if second_half_success < first_half_success else 'stable'

        return {
            'duration_trend': duration_trend,
            'duration_change_seconds': second_half_avg - first_half_avg,
            'duration_change_percent': ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0,
            'success_rate_trend': success_trend,
            'success_rate_change_percent': second_half_success - first_half_success,
            'first_period_avg_duration': first_half_avg,
            'second_period_avg_duration': second_half_avg,
            'first_period_success_rate': first_half_success,
            'second_period_success_rate': second_half_success
        }


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.2f}h"


def print_report(report: PerformanceReport):
    """Print performance report to console"""
    print("\n" + "=" * 80)
    print("PIPELINE PERFORMANCE REPORT")
    print("=" * 80)

    print(f"\n📊 OVERALL METRICS")
    print(f"  Total Runs:       {report.total_runs}")
    print(f"  Success Rate:     {report.success_rate:.1f}%")
    print(f"  Average Duration: {format_duration(report.average_duration)}")
    print(f"  Median Duration:  {format_duration(report.median_duration)}")
    print(f"  P95 Duration:     {format_duration(report.p95_duration)}")
    print(f"  P99 Duration:     {format_duration(report.p99_duration)}")

    if report.slowest_jobs:
        print(f"\n🐌 SLOWEST JOBS (Top {min(5, len(report.slowest_jobs))})")
        for i, job in enumerate(report.slowest_jobs[:5], 1):
            print(f"  {i}. {job['name']}")
            print(f"     Average: {format_duration(job['average_duration'])}, Max: {format_duration(job['max_duration'])}, Runs: {job['runs']}")

    if report.bottlenecks:
        print(f"\n⚠️  BOTTLENECKS DETECTED ({len(report.bottlenecks)})")
        for bn in report.bottlenecks[:5]:
            print(f"  • {bn['job_name']}: {bn['issue']}")

    if report.flaky_tests:
        print(f"\n🔄 FLAKY TESTS ({len(report.flaky_tests)})")
        for test in report.flaky_tests[:5]:
            print(f"  • {test['name']}: {test['failure_rate']:.1f}% failure rate ({test['failures']}/{test['total_runs']} runs)")

    if report.cost_estimate:
        print(f"\n💰 COST ESTIMATE")
        print(f"  Compute Minutes:     {report.cost_estimate['total_compute_minutes']:.1f}")
        print(f"  Monthly Cost:        ${report.cost_estimate['estimated_monthly_cost_usd']:.2f}")
        print(f"  Potential Savings:   ${report.cost_estimate['potential_monthly_savings_usd']:.2f}")

    if report.trends and 'duration_trend' in report.trends:
        print(f"\n📈 TRENDS")
        trends = report.trends
        print(f"  Duration Trend:    {trends['duration_trend'].upper()}")
        print(f"  Duration Change:   {format_duration(abs(trends['duration_change_seconds']))} ({trends['duration_change_percent']:+.1f}%)")
        print(f"  Success Rate:      {trends['success_rate_trend'].upper()} ({trends['success_rate_change_percent']:+.1f}%)")

    if report.recommendations:
        print(f"\n💡 RECOMMENDATIONS")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"\n  {i}. {rec}")

    print("\n" + "=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze CI/CD pipeline performance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --platform github-actions --repo owner/repo
  %(prog)s --platform github-actions --repo owner/repo --runs 50 --verbose
  %(prog)s --platform gitlab --project-id 12345 --json
  %(prog)s --file pipeline-data.json --analyze

Supported platforms:
  github-actions  GitHub Actions workflows
  gitlab          GitLab CI pipelines
        """
    )

    parser.add_argument(
        '--platform',
        choices=['github-actions', 'gitlab'],
        help='CI/CD platform'
    )
    parser.add_argument(
        '--repo',
        help='GitHub repository (format: owner/repo)'
    )
    parser.add_argument(
        '--project-id',
        help='GitLab project ID'
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=100,
        help='Number of runs to analyze (default: 100)'
    )
    parser.add_argument(
        '--file',
        type=Path,
        help='Load pipeline data from JSON file'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Save analysis report to file'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Load or fetch pipeline runs
    runs = []

    if args.file:
        # Load from file
        with open(args.file, 'r') as f:
            data = json.load(f)
            # Convert back to PipelineRun objects
            runs = []
            for run_data in data.get('runs', []):
                jobs = [JobMetrics(**job) for job in run_data.get('jobs', [])]
                run = PipelineRun(
                    id=run_data['id'],
                    number=run_data['number'],
                    status=run_data['status'],
                    created_at=datetime.fromisoformat(run_data['created_at']),
                    started_at=datetime.fromisoformat(run_data['started_at']) if run_data.get('started_at') else None,
                    completed_at=datetime.fromisoformat(run_data['completed_at']) if run_data.get('completed_at') else None,
                    duration_seconds=run_data.get('duration_seconds'),
                    jobs=jobs,
                    trigger=run_data.get('trigger', 'unknown'),
                    branch=run_data.get('branch', 'unknown'),
                    commit_sha=run_data.get('commit_sha', '')
                )
                runs.append(run)
    else:
        # Fetch from platform
        if args.platform == 'github-actions':
            if not args.repo:
                parser.error('--repo required for GitHub Actions')
            api = GitHubActionsAPI(args.repo)
            runs = api.fetch_runs(limit=args.runs)
        elif args.platform == 'gitlab':
            if not args.project_id:
                parser.error('--project-id required for GitLab CI')
            api = GitLabCIAPI(args.project_id)
            runs = api.fetch_runs(limit=args.runs)
        else:
            parser.error('Either --platform or --file must be specified')

    if not runs:
        print("No pipeline runs found to analyze", file=sys.stderr)
        return 1

    # Perform analysis
    analyzer = PerformanceAnalyzer(runs, verbose=args.verbose)
    report = analyzer.analyze()

    # Output results
    if args.json:
        output_data = report.to_dict()
        output_json = json.dumps(output_data, indent=2)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_json)
            print(f"Report saved to {args.output}")
        else:
            print(output_json)
    else:
        print_report(report)

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report.to_dict(), f, indent=2)
            print(f"\nDetailed report saved to {args.output}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
