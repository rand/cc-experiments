#!/usr/bin/env python3
"""
LM API Cost Tracker

Track token usage, calculate costs, enforce budgets, and generate reports
for language model API usage across models and endpoints.

Usage:
    python cost_tracker.py track --model gpt-4 --tokens 1500 --type completion
    python cost_tracker.py report --period week --format json
    python cost_tracker.py budget --set 100.00 --period month
    python cost_tracker.py alert --threshold 80 --notify email
    python cost_tracker.py analyze --breakdown model --period month
"""

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum


class TokenType(Enum):
    """Token usage type"""
    PROMPT = "prompt"
    COMPLETION = "completion"
    EMBEDDING = "embedding"


class Period(Enum):
    """Time period for reports"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


# Model pricing per 1K tokens (input/output)
MODEL_PRICING = {
    # OpenAI GPT-4
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-32k": {"input": 0.06, "output": 0.12},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},

    # OpenAI GPT-3.5
    "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
    "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},

    # Anthropic Claude
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-3.5-sonnet": {"input": 0.003, "output": 0.015},

    # Embeddings
    "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
    "text-embedding-3-large": {"input": 0.00013, "output": 0.0},
    "text-embedding-ada-002": {"input": 0.0001, "output": 0.0},
}


@dataclass
class UsageRecord:
    """Single usage record"""
    timestamp: str
    model: str
    tokens: int
    token_type: str
    cost: float
    endpoint: Optional[str] = None
    user: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class Budget:
    """Budget configuration"""
    amount: float
    period: str
    start_date: str
    alert_threshold: float = 80.0  # Percentage


class CostTracker:
    """Track and analyze LM API costs"""

    def __init__(self, db_path: str = "cost_tracker.db"):
        self.db_path = Path(db_path)
        self.conn = self._init_db()

    def _init_db(self) -> sqlite3.Connection:
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Usage table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens INTEGER NOT NULL,
                token_type TEXT NOT NULL,
                cost REAL NOT NULL,
                endpoint TEXT,
                user TEXT,
                metadata TEXT
            )
        """)

        # Budgets table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                period TEXT NOT NULL,
                start_date TEXT NOT NULL,
                alert_threshold REAL NOT NULL
            )
        """)

        # Alerts table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                budget_id INTEGER NOT NULL,
                current_spend REAL NOT NULL,
                threshold_percent REAL NOT NULL,
                message TEXT NOT NULL,
                FOREIGN KEY (budget_id) REFERENCES budgets(id)
            )
        """)

        conn.commit()
        return conn

    def track_usage(
        self,
        model: str,
        tokens: int,
        token_type: TokenType,
        endpoint: Optional[str] = None,
        user: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> UsageRecord:
        """Track a single usage event"""
        if model not in MODEL_PRICING:
            print(f"Warning: Unknown model '{model}', using default pricing", file=sys.stderr)
            cost = 0.0
        else:
            pricing = MODEL_PRICING[model]
            if token_type == TokenType.PROMPT or token_type.value == "prompt":
                cost = (tokens / 1000) * pricing["input"]
            elif token_type == TokenType.COMPLETION or token_type.value == "completion":
                cost = (tokens / 1000) * pricing["output"]
            else:  # embedding
                cost = (tokens / 1000) * pricing.get("input", 0.0)

        timestamp = datetime.utcnow().isoformat()
        record = UsageRecord(
            timestamp=timestamp,
            model=model,
            tokens=tokens,
            token_type=token_type.value if isinstance(token_type, TokenType) else token_type,
            cost=cost,
            endpoint=endpoint,
            user=user,
            metadata=metadata
        )

        self.conn.execute(
            """
            INSERT INTO usage (timestamp, model, tokens, token_type, cost, endpoint, user, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.timestamp,
                record.model,
                record.tokens,
                record.token_type,
                record.cost,
                record.endpoint,
                record.user,
                json.dumps(metadata) if metadata else None
            )
        )
        self.conn.commit()

        # Check budget alerts
        self._check_budget_alerts()

        return record

    def set_budget(self, amount: float, period: Period, alert_threshold: float = 80.0) -> int:
        """Set a new budget"""
        start_date = datetime.utcnow().isoformat()
        cursor = self.conn.execute(
            """
            INSERT INTO budgets (amount, period, start_date, alert_threshold)
            VALUES (?, ?, ?, ?)
            """,
            (amount, period.value if isinstance(period, Period) else period, start_date, alert_threshold)
        )
        self.conn.commit()
        return cursor.lastrowid

    def _check_budget_alerts(self):
        """Check if any budgets have exceeded alert thresholds"""
        budgets = self.conn.execute("SELECT * FROM budgets").fetchall()

        for budget_row in budgets:
            budget_id = budget_row["id"]
            amount = budget_row["amount"]
            period = budget_row["period"]
            start_date = datetime.fromisoformat(budget_row["start_date"])
            threshold = budget_row["alert_threshold"]

            # Calculate period end
            if period == "day":
                period_end = start_date + timedelta(days=1)
            elif period == "week":
                period_end = start_date + timedelta(weeks=1)
            elif period == "month":
                period_end = start_date + timedelta(days=30)
            else:  # year
                period_end = start_date + timedelta(days=365)

            # If period expired, skip
            if datetime.utcnow() > period_end:
                continue

            # Get current spend for period
            current_spend = self._get_spend_for_period(start_date, period_end)
            percent_used = (current_spend / amount) * 100 if amount > 0 else 0

            # Check if threshold exceeded
            if percent_used >= threshold:
                # Check if alert already sent
                existing = self.conn.execute(
                    """
                    SELECT id FROM alerts
                    WHERE budget_id = ? AND current_spend = ?
                    """,
                    (budget_id, current_spend)
                ).fetchone()

                if not existing:
                    message = f"Budget alert: {percent_used:.1f}% of ${amount:.2f} budget used (${current_spend:.2f})"
                    self.conn.execute(
                        """
                        INSERT INTO alerts (timestamp, budget_id, current_spend, threshold_percent, message)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (datetime.utcnow().isoformat(), budget_id, current_spend, percent_used, message)
                    )
                    self.conn.commit()
                    print(f"⚠️  {message}", file=sys.stderr)

    def _get_spend_for_period(self, start: datetime, end: datetime) -> float:
        """Get total spend for a time period"""
        result = self.conn.execute(
            """
            SELECT SUM(cost) as total
            FROM usage
            WHERE timestamp >= ? AND timestamp < ?
            """,
            (start.isoformat(), end.isoformat())
        ).fetchone()
        return result["total"] or 0.0

    def generate_report(self, period: Period, format: str = "text") -> str:
        """Generate cost report for period"""
        # Calculate date range
        end_date = datetime.utcnow()
        if period == Period.DAY:
            start_date = end_date - timedelta(days=1)
        elif period == Period.WEEK:
            start_date = end_date - timedelta(weeks=1)
        elif period == Period.MONTH:
            start_date = end_date - timedelta(days=30)
        else:  # year
            start_date = end_date - timedelta(days=365)

        # Get usage data
        rows = self.conn.execute(
            """
            SELECT model, token_type, SUM(tokens) as total_tokens, SUM(cost) as total_cost, COUNT(*) as count
            FROM usage
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY model, token_type
            ORDER BY total_cost DESC
            """,
            (start_date.isoformat(), end_date.isoformat())
        ).fetchall()

        total_cost = sum(row["total_cost"] for row in rows)
        total_tokens = sum(row["total_tokens"] for row in rows)

        if format == "json":
            report = {
                "period": period.value,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_cost": round(total_cost, 4),
                "total_tokens": total_tokens,
                "breakdown": [
                    {
                        "model": row["model"],
                        "token_type": row["token_type"],
                        "tokens": row["total_tokens"],
                        "cost": round(row["total_cost"], 4),
                        "count": row["count"]
                    }
                    for row in rows
                ]
            }
            return json.dumps(report, indent=2)
        else:
            lines = [
                f"Cost Report - {period.value.title()}",
                f"Period: {start_date.date()} to {end_date.date()}",
                "=" * 80,
                f"Total Cost: ${total_cost:.4f}",
                f"Total Tokens: {total_tokens:,}",
                "",
                "Breakdown by Model and Type:",
                "-" * 80,
            ]

            for row in rows:
                lines.append(
                    f"  {row['model']:30s} {row['token_type']:12s} "
                    f"{row['total_tokens']:10,} tokens  ${row['total_cost']:8.4f}  ({row['count']} calls)"
                )

            return "\n".join(lines)

    def analyze(self, breakdown: str, period: Period) -> Dict:
        """Analyze costs with specific breakdown"""
        end_date = datetime.utcnow()
        if period == Period.DAY:
            start_date = end_date - timedelta(days=1)
        elif period == Period.WEEK:
            start_date = end_date - timedelta(weeks=1)
        elif period == Period.MONTH:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=365)

        if breakdown == "model":
            rows = self.conn.execute(
                """
                SELECT model, SUM(tokens) as total_tokens, SUM(cost) as total_cost, COUNT(*) as count
                FROM usage
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY model
                ORDER BY total_cost DESC
                """,
                (start_date.isoformat(), end_date.isoformat())
            ).fetchall()
            key = "model"

        elif breakdown == "endpoint":
            rows = self.conn.execute(
                """
                SELECT endpoint, SUM(tokens) as total_tokens, SUM(cost) as total_cost, COUNT(*) as count
                FROM usage
                WHERE timestamp >= ? AND timestamp < ? AND endpoint IS NOT NULL
                GROUP BY endpoint
                ORDER BY total_cost DESC
                """,
                (start_date.isoformat(), end_date.isoformat())
            ).fetchall()
            key = "endpoint"

        elif breakdown == "user":
            rows = self.conn.execute(
                """
                SELECT user, SUM(tokens) as total_tokens, SUM(cost) as total_cost, COUNT(*) as count
                FROM usage
                WHERE timestamp >= ? AND timestamp < ? AND user IS NOT NULL
                GROUP BY user
                ORDER BY total_cost DESC
                """,
                (start_date.isoformat(), end_date.isoformat())
            ).fetchall()
            key = "user"

        else:
            raise ValueError(f"Unknown breakdown type: {breakdown}")

        return {
            "breakdown": breakdown,
            "period": period.value,
            "data": [
                {
                    key: row[key] or "unknown",
                    "tokens": row["total_tokens"],
                    "cost": round(row["total_cost"], 4),
                    "count": row["count"]
                }
                for row in rows
            ]
        }

    def get_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts"""
        rows = self.conn.execute(
            """
            SELECT a.*, b.amount, b.period
            FROM alerts a
            JOIN budgets b ON a.budget_id = b.id
            ORDER BY a.timestamp DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return [
            {
                "timestamp": row["timestamp"],
                "budget_amount": row["amount"],
                "budget_period": row["period"],
                "current_spend": row["current_spend"],
                "threshold_percent": row["threshold_percent"],
                "message": row["message"]
            }
            for row in rows
        ]

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    parser = argparse.ArgumentParser(description="LM API Cost Tracker")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Track command
    track_parser = subparsers.add_parser("track", help="Track usage")
    track_parser.add_argument("--model", required=True, help="Model name")
    track_parser.add_argument("--tokens", type=int, required=True, help="Token count")
    track_parser.add_argument("--type", required=True, choices=["prompt", "completion", "embedding"], help="Token type")
    track_parser.add_argument("--endpoint", help="Endpoint name")
    track_parser.add_argument("--user", help="User identifier")
    track_parser.add_argument("--db", default="cost_tracker.db", help="Database path")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate report")
    report_parser.add_argument("--period", required=True, choices=["day", "week", "month", "year"], help="Time period")
    report_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    report_parser.add_argument("--db", default="cost_tracker.db", help="Database path")

    # Budget command
    budget_parser = subparsers.add_parser("budget", help="Set budget")
    budget_parser.add_argument("--set", type=float, required=True, help="Budget amount")
    budget_parser.add_argument("--period", required=True, choices=["day", "week", "month", "year"], help="Budget period")
    budget_parser.add_argument("--threshold", type=float, default=80.0, help="Alert threshold percentage")
    budget_parser.add_argument("--db", default="cost_tracker.db", help="Database path")

    # Alert command
    alert_parser = subparsers.add_parser("alert", help="View alerts")
    alert_parser.add_argument("--limit", type=int, default=10, help="Number of alerts to show")
    alert_parser.add_argument("--db", default="cost_tracker.db", help="Database path")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze costs")
    analyze_parser.add_argument("--breakdown", required=True, choices=["model", "endpoint", "user"], help="Breakdown type")
    analyze_parser.add_argument("--period", required=True, choices=["day", "week", "month", "year"], help="Time period")
    analyze_parser.add_argument("--db", default="cost_tracker.db", help="Database path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    tracker = CostTracker(args.db)

    try:
        if args.command == "track":
            record = tracker.track_usage(
                model=args.model,
                tokens=args.tokens,
                token_type=TokenType(args.type),
                endpoint=args.endpoint,
                user=args.user
            )
            print(f"Tracked: {record.tokens} {record.token_type} tokens for {record.model} (${record.cost:.6f})")

        elif args.command == "report":
            report = tracker.generate_report(Period(args.period), args.format)
            print(report)

        elif args.command == "budget":
            budget_id = tracker.set_budget(args.set, Period(args.period), args.threshold)
            print(f"Budget set: ${args.set:.2f} per {args.period} (alert at {args.threshold}%) [ID: {budget_id}]")

        elif args.command == "alert":
            alerts = tracker.get_alerts(args.limit)
            if alerts:
                print(f"Recent Alerts ({len(alerts)}):")
                print("-" * 80)
                for alert in alerts:
                    print(f"[{alert['timestamp']}] {alert['message']}")
            else:
                print("No alerts found")

        elif args.command == "analyze":
            analysis = tracker.analyze(args.breakdown, Period(args.period))
            print(json.dumps(analysis, indent=2))

        return 0

    finally:
        tracker.close()


if __name__ == "__main__":
    sys.exit(main())
