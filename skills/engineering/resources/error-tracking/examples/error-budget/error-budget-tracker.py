#!/usr/bin/env python3
"""
Error Budget Tracker

Track error budget consumption and enforce sampling based on remaining budget.

Error Budget Concept:
- Define acceptable error rate (e.g., 0.1% = 99.9% success rate)
- Track errors against budget over time period (e.g., monthly)
- Implement sampling when budget running low

Usage:
    error_budget_tracker.py --org myorg --project api --threshold 0.001
"""

import argparse
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import requests


class ErrorBudgetTracker:
    """Track and enforce error budget."""

    def __init__(
        self,
        api_token: str,
        org_slug: str,
        project_slug: str,
        error_threshold: float = 0.001,  # 0.1% error budget
        period_days: int = 30
    ):
        self.api_token = api_token
        self.org_slug = org_slug
        self.project_slug = project_slug
        self.error_threshold = error_threshold
        self.period_days = period_days

        self.base_url = "https://sentry.io/api/0"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        })

    def get_project_stats(self) -> Dict[str, Any]:
        """Fetch project statistics from Sentry."""
        end = datetime.now()
        start = end - timedelta(days=self.period_days)

        params = {
            'stat': 'received',
            'since': int(start.timestamp()),
            'until': int(end.timestamp()),
            'resolution': '1d'
        }

        response = self.session.get(
            f"{self.base_url}/organizations/{self.org_slug}/stats/",
            params=params
        )
        response.raise_for_status()

        return response.json()

    def calculate_error_budget(self) -> Dict[str, Any]:
        """Calculate current error budget status."""

        # Get total requests (from your metrics system)
        # This is simplified - in production, fetch from your metrics
        total_requests = self._get_total_requests()

        # Get error count from Sentry
        stats = self.get_project_stats()
        total_errors = sum(point[1] for point in stats)

        # Calculate error rate
        error_rate = total_errors / total_requests if total_requests > 0 else 0

        # Calculate budget consumption
        budget_consumed = error_rate / self.error_threshold if self.error_threshold > 0 else 0
        budget_remaining = max(0, 1.0 - budget_consumed)

        # Determine sampling rate based on budget
        if budget_remaining > 0.5:
            sample_rate = 1.0  # 100% - plenty of budget
        elif budget_remaining > 0.25:
            sample_rate = 0.5  # 50% - budget getting low
        elif budget_remaining > 0.1:
            sample_rate = 0.1  # 10% - budget critical
        else:
            sample_rate = 0.01  # 1% - budget exhausted

        return {
            'period_days': self.period_days,
            'error_threshold': self.error_threshold,
            'total_requests': total_requests,
            'total_errors': total_errors,
            'error_rate': error_rate,
            'budget_consumed': budget_consumed,
            'budget_remaining': budget_remaining,
            'recommended_sample_rate': sample_rate,
            'status': self._get_budget_status(budget_remaining),
            'alerts': self._generate_alerts(budget_remaining)
        }

    def _get_total_requests(self) -> int:
        """Get total request count from metrics system."""
        # In production, fetch from Prometheus, CloudWatch, etc.
        # For demo, return estimated value
        return 1000000

    def _get_budget_status(self, budget_remaining: float) -> str:
        """Get human-readable budget status."""
        if budget_remaining > 0.75:
            return 'HEALTHY'
        elif budget_remaining > 0.5:
            return 'WARNING'
        elif budget_remaining > 0.25:
            return 'CRITICAL'
        else:
            return 'EXHAUSTED'

    def _generate_alerts(self, budget_remaining: float) -> list:
        """Generate alerts based on budget status."""
        alerts = []

        if budget_remaining < 0.1:
            alerts.append({
                'severity': 'critical',
                'message': 'Error budget exhausted! Reduce error rate immediately.'
            })
        elif budget_remaining < 0.25:
            alerts.append({
                'severity': 'warning',
                'message': 'Error budget critical. Investigation required.'
            })
        elif budget_remaining < 0.5:
            alerts.append({
                'severity': 'info',
                'message': 'Error budget consumption elevated. Monitor closely.'
            })

        return alerts

    def get_sampling_config(self, budget: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Sentry sampling configuration based on budget."""
        sample_rate = budget['recommended_sample_rate']

        return {
            'traces_sample_rate': sample_rate,
            'before_send': self._generate_before_send_function(sample_rate),
            'rationale': f"Sampling at {sample_rate:.0%} based on error budget consumption"
        }

    def _generate_before_send_function(self, sample_rate: float) -> str:
        """Generate before_send function code for sampling."""
        return f"""
def before_send(event, hint):
    import random

    # Sample based on error budget
    if random.random() > {sample_rate}:
        return None  # Drop event

    return event

sentry_sdk.init(
    dsn="...",
    before_send=before_send
)
"""


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Error budget tracker"
    )

    parser.add_argument(
        '--sentry-token',
        default=os.getenv('SENTRY_AUTH_TOKEN'),
        help='Sentry API token'
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
        '--threshold',
        type=float,
        default=0.001,
        help='Error threshold (default: 0.001 = 0.1%% = 99.9%% SLA)'
    )

    parser.add_argument(
        '--period',
        type=int,
        default=30,
        help='Budget period in days (default: 30)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    args = parser.parse_args()

    if not args.sentry_token:
        print("Error: Sentry API token required", file=sys.stderr)
        sys.exit(1)

    # Create tracker
    tracker = ErrorBudgetTracker(
        args.sentry_token,
        args.org,
        args.project,
        args.threshold,
        args.period
    )

    # Calculate budget
    try:
        budget = tracker.calculate_error_budget()
    except Exception as e:
        print(f"Error calculating budget: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.json:
        print(json.dumps(budget, indent=2))
    else:
        # Formatted output
        print("=" * 60)
        print("ERROR BUDGET REPORT")
        print("=" * 60)
        print(f"Project: {args.org}/{args.project}")
        print(f"Period: {budget['period_days']} days")
        print(f"Threshold: {budget['error_threshold']:.2%}")
        print()
        print(f"Total Requests: {budget['total_requests']:,}")
        print(f"Total Errors: {budget['total_errors']:,}")
        print(f"Error Rate: {budget['error_rate']:.4%}")
        print()
        print(f"Budget Consumed: {budget['budget_consumed']:.1%}")
        print(f"Budget Remaining: {budget['budget_remaining']:.1%}")
        print(f"Status: {budget['status']}")
        print()
        print(f"Recommended Sample Rate: {budget['recommended_sample_rate']:.0%}")
        print()

        if budget['alerts']:
            print("ALERTS:")
            for alert in budget['alerts']:
                icon = '🚨' if alert['severity'] == 'critical' else '⚠️' if alert['severity'] == 'warning' else 'ℹ️'
                print(f"  {icon} {alert['message']}")
        else:
            print("✓ No alerts - error budget healthy")

        print("=" * 60)


if __name__ == "__main__":
    main()
