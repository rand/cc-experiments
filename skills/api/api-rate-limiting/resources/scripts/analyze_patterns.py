#!/usr/bin/env python3
"""
Analyze Patterns - API Traffic Pattern Analysis Tool

Analyzes API access logs to identify traffic patterns and recommend
optimal rate limit configurations.

Usage:
    ./analyze_patterns.py --log-file access.log
    ./analyze_patterns.py --log-file access.log --json
    ./analyze_patterns.py --log-file access.log --time-window 3600
    ./analyze_patterns.py --help

Features:
- Parse API access logs (common formats)
- Identify traffic patterns (burst, steady, abuse)
- Recommend rate limit thresholds
- Detect potential abuse patterns
- Calculate optimal limits per tier
"""

import argparse
import re
import json
import sys
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from statistics import mean, median, stdev, quantiles
import ipaddress


@dataclass
class LogEntry:
    """Parsed log entry"""
    timestamp: datetime
    ip: str
    method: str
    endpoint: str
    status: int
    response_time: float
    user_agent: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class TrafficPattern:
    """Identified traffic pattern"""
    pattern_type: str  # burst, steady, abuse, scraping
    client_id: str
    request_count: int
    time_span: float
    requests_per_second: float
    endpoints: List[str]
    confidence: float


@dataclass
class RateLimitRecommendation:
    """Rate limit configuration recommendation"""
    endpoint: str
    per_second: int
    per_minute: int
    per_hour: int
    per_day: int
    burst_capacity: int
    reasoning: str


@dataclass
class AnalysisSummary:
    """Complete analysis summary"""
    log_file: str
    total_requests: int
    unique_ips: int
    unique_endpoints: int
    time_span: float
    overall_rps: float
    patterns: List[TrafficPattern]
    recommendations: List[RateLimitRecommendation]
    abuse_detected: List[Dict]
    top_endpoints: List[Tuple[str, int]]
    top_clients: List[Tuple[str, int]]


class LogParser:
    """Parse API access logs"""

    # Common log formats
    NGINX_COMBINED = re.compile(
        r'(?P<ip>[\d.]+) - - \[(?P<timestamp>[^\]]+)\] "(?P<method>\w+) (?P<endpoint>[^\s]+) HTTP/[\d.]+" '
        r'(?P<status>\d+) (?P<size>\d+) "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)"'
    )

    APACHE_COMBINED = re.compile(
        r'(?P<ip>[\d.]+) - - \[(?P<timestamp>[^\]]+)\] "(?P<method>\w+) (?P<endpoint>[^\s]+) HTTP/[\d.]+" '
        r'(?P<status>\d+) (?P<size>\d+)'
    )

    JSON_FORMAT = re.compile(r'\{.*\}')

    def __init__(self):
        """Initialize parser"""
        self.entries: List[LogEntry] = []

    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp from log

        Args:
            timestamp_str: Timestamp string

        Returns:
            Parsed datetime
        """
        # Try common formats
        formats = [
            '%d/%b/%Y:%H:%M:%S %z',  # Nginx/Apache
            '%Y-%m-%d %H:%M:%S',      # ISO-like
            '%Y-%m-%dT%H:%M:%S',      # ISO
            '%Y-%m-%dT%H:%M:%S.%f',   # ISO with microseconds
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # Try parsing as Unix timestamp
        try:
            return datetime.fromtimestamp(float(timestamp_str))
        except (ValueError, OSError):
            pass

        raise ValueError(f"Unable to parse timestamp: {timestamp_str}")

    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse single log line

        Args:
            line: Log line

        Returns:
            Parsed entry or None
        """
        line = line.strip()
        if not line:
            return None

        # Try JSON format
        if line.startswith('{'):
            try:
                data = json.loads(line)
                return LogEntry(
                    timestamp=self.parse_timestamp(data.get('timestamp', data.get('time', ''))),
                    ip=data.get('ip', data.get('remote_addr', '')),
                    method=data.get('method', ''),
                    endpoint=data.get('endpoint', data.get('uri', data.get('path', ''))),
                    status=int(data.get('status', 0)),
                    response_time=float(data.get('response_time', 0.0)),
                    user_agent=data.get('user_agent'),
                    user_id=data.get('user_id')
                )
            except (json.JSONDecodeError, ValueError, KeyError):
                pass

        # Try Nginx combined format
        match = self.NGINX_COMBINED.match(line)
        if match:
            return LogEntry(
                timestamp=self.parse_timestamp(match.group('timestamp')),
                ip=match.group('ip'),
                method=match.group('method'),
                endpoint=match.group('endpoint'),
                status=int(match.group('status')),
                response_time=0.0,
                user_agent=match.group('user_agent')
            )

        # Try Apache combined format
        match = self.APACHE_COMBINED.match(line)
        if match:
            return LogEntry(
                timestamp=self.parse_timestamp(match.group('timestamp')),
                ip=match.group('ip'),
                method=match.group('method'),
                endpoint=match.group('endpoint'),
                status=int(match.group('status')),
                response_time=0.0
            )

        return None

    def parse_file(self, file_path: str) -> List[LogEntry]:
        """Parse entire log file

        Args:
            file_path: Path to log file

        Returns:
            List of parsed entries
        """
        entries = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        entry = self.parse_line(line)
                        if entry:
                            entries.append(entry)
                    except Exception as e:
                        print(f"Warning: Failed to parse line {line_num}: {e}",
                              file=sys.stderr)
                        continue

        except FileNotFoundError:
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

        self.entries = entries
        return entries


class TrafficAnalyzer:
    """Analyze traffic patterns"""

    def __init__(self, entries: List[LogEntry]):
        """Initialize analyzer

        Args:
            entries: List of log entries
        """
        self.entries = sorted(entries, key=lambda e: e.timestamp)

    def get_time_span(self) -> float:
        """Get time span of logs in seconds

        Returns:
            Time span in seconds
        """
        if not self.entries:
            return 0.0

        start = self.entries[0].timestamp
        end = self.entries[-1].timestamp
        return (end - start).total_seconds()

    def get_client_id(self, entry: LogEntry) -> str:
        """Get client identifier

        Args:
            entry: Log entry

        Returns:
            Client ID (user_id or IP)
        """
        if entry.user_id:
            return f"user:{entry.user_id}"
        return f"ip:{entry.ip}"

    def analyze_client_pattern(self, client_id: str,
                               time_window: int = 60) -> List[TrafficPattern]:
        """Analyze traffic pattern for specific client

        Args:
            client_id: Client identifier
            time_window: Time window for analysis (seconds)

        Returns:
            List of identified patterns
        """
        # Get client entries
        client_entries = [e for e in self.entries if self.get_client_id(e) == client_id]

        if not client_entries:
            return []

        patterns = []

        # Analyze in time windows
        if len(client_entries) > 1:
            start_time = client_entries[0].timestamp
            end_time = client_entries[-1].timestamp
            total_time = (end_time - start_time).total_seconds()

            if total_time > 0:
                rps = len(client_entries) / total_time

                # Identify pattern type
                if rps > 10:
                    # High rate - potential abuse or burst
                    pattern_type = "burst" if total_time < 10 else "abuse"
                    confidence = 0.9
                elif rps > 1:
                    pattern_type = "steady"
                    confidence = 0.7
                else:
                    pattern_type = "normal"
                    confidence = 0.5

                # Check for scraping behavior
                endpoints = [e.endpoint for e in client_entries]
                unique_endpoints = len(set(endpoints))
                if unique_endpoints > 20 and rps > 2:
                    pattern_type = "scraping"
                    confidence = 0.8

                patterns.append(TrafficPattern(
                    pattern_type=pattern_type,
                    client_id=client_id,
                    request_count=len(client_entries),
                    time_span=total_time,
                    requests_per_second=rps,
                    endpoints=list(set(endpoints))[:10],
                    confidence=confidence
                ))

        return patterns

    def detect_abuse(self, threshold_rps: float = 5.0) -> List[Dict]:
        """Detect potential abuse patterns

        Args:
            threshold_rps: RPS threshold for abuse detection

        Returns:
            List of abuse patterns
        """
        abuse_patterns = []

        # Group by client
        by_client = defaultdict(list)
        for entry in self.entries:
            by_client[self.get_client_id(entry)].append(entry)

        # Analyze each client
        for client_id, entries in by_client.items():
            if len(entries) < 10:
                continue

            start = entries[0].timestamp
            end = entries[-1].timestamp
            duration = (end - start).total_seconds()

            if duration > 0:
                rps = len(entries) / duration

                if rps > threshold_rps:
                    # Check for additional abuse indicators
                    status_codes = [e.status for e in entries]
                    error_rate = sum(1 for s in status_codes if s >= 400) / len(status_codes)

                    endpoints = [e.endpoint for e in entries]
                    unique_endpoints = len(set(endpoints))

                    abuse_patterns.append({
                        'client_id': client_id,
                        'request_count': len(entries),
                        'rps': rps,
                        'duration': duration,
                        'error_rate': error_rate,
                        'unique_endpoints': unique_endpoints,
                        'severity': 'high' if rps > threshold_rps * 2 else 'medium'
                    })

        return sorted(abuse_patterns, key=lambda x: x['rps'], reverse=True)

    def calculate_percentiles(self, values: List[float],
                             percentiles: List[float] = [0.5, 0.9, 0.95, 0.99]) -> Dict[str, float]:
        """Calculate percentiles

        Args:
            values: List of values
            percentiles: Percentiles to calculate

        Returns:
            Dict of percentile values
        """
        if not values:
            return {}

        sorted_values = sorted(values)
        result = {}

        for p in percentiles:
            key = f"p{int(p*100)}"
            idx = int(len(sorted_values) * p)
            result[key] = sorted_values[min(idx, len(sorted_values)-1)]

        return result

    def recommend_rate_limits(self) -> List[RateLimitRecommendation]:
        """Recommend rate limits based on traffic patterns

        Returns:
            List of recommendations
        """
        recommendations = []

        # Group by endpoint
        by_endpoint = defaultdict(list)
        for entry in self.entries:
            by_endpoint[entry.endpoint].append(entry)

        for endpoint, entries in sorted(by_endpoint.items(),
                                       key=lambda x: len(x[1]),
                                       reverse=True)[:20]:
            # Calculate RPS distribution
            by_client = defaultdict(list)
            for entry in entries:
                by_client[self.get_client_id(entry)].append(entry)

            client_rps = []
            for client_id, client_entries in by_client.items():
                if len(client_entries) > 1:
                    start = client_entries[0].timestamp
                    end = client_entries[-1].timestamp
                    duration = (end - start).total_seconds()
                    if duration > 0:
                        client_rps.append(len(client_entries) / duration)

            if not client_rps:
                continue

            # Calculate percentiles
            percentiles = self.calculate_percentiles(client_rps)

            # Recommend limits based on percentiles
            # Most users should be under p95, with headroom for bursts
            p95 = percentiles.get('p95', 1.0)
            p99 = percentiles.get('p99', p95 * 2)

            per_second = int(p95 * 1.5)  # 50% headroom
            per_minute = int(p95 * 60 * 1.5)
            per_hour = int(p95 * 3600 * 1.2)  # Less headroom for longer periods
            per_day = int(p95 * 86400 * 1.1)
            burst_capacity = int(p99 * 2)  # Allow 2x p99 burst

            reasoning = (
                f"Based on {len(by_client)} clients. "
                f"P95 RPS: {p95:.2f}, P99 RPS: {p99:.2f}. "
                f"Limits set to accommodate 95% of traffic with burst tolerance."
            )

            recommendations.append(RateLimitRecommendation(
                endpoint=endpoint,
                per_second=per_second,
                per_minute=per_minute,
                per_hour=per_hour,
                per_day=per_day,
                burst_capacity=burst_capacity,
                reasoning=reasoning
            ))

        return recommendations

    def get_top_endpoints(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get top N endpoints by request count

        Args:
            n: Number of endpoints to return

        Returns:
            List of (endpoint, count) tuples
        """
        endpoint_counts = Counter(e.endpoint for e in self.entries)
        return endpoint_counts.most_common(n)

    def get_top_clients(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get top N clients by request count

        Args:
            n: Number of clients to return

        Returns:
            List of (client_id, count) tuples
        """
        client_counts = Counter(self.get_client_id(e) for e in self.entries)
        return client_counts.most_common(n)

    def analyze(self, time_window: int = 60) -> AnalysisSummary:
        """Perform complete analysis

        Args:
            time_window: Time window for pattern analysis (seconds)

        Returns:
            Analysis summary
        """
        # Basic statistics
        total_requests = len(self.entries)
        unique_ips = len(set(e.ip for e in self.entries))
        unique_endpoints = len(set(e.endpoint for e in self.entries))
        time_span = self.get_time_span()
        overall_rps = total_requests / time_span if time_span > 0 else 0.0

        # Identify patterns
        patterns = []
        clients = set(self.get_client_id(e) for e in self.entries)
        for client_id in clients:
            patterns.extend(self.analyze_client_pattern(client_id, time_window))

        # Detect abuse
        abuse_detected = self.detect_abuse()

        # Generate recommendations
        recommendations = self.recommend_rate_limits()

        # Top endpoints and clients
        top_endpoints = self.get_top_endpoints()
        top_clients = self.get_top_clients()

        return AnalysisSummary(
            log_file="",  # Set by caller
            total_requests=total_requests,
            unique_ips=unique_ips,
            unique_endpoints=unique_endpoints,
            time_span=time_span,
            overall_rps=overall_rps,
            patterns=patterns,
            recommendations=recommendations,
            abuse_detected=abuse_detected,
            top_endpoints=top_endpoints,
            top_clients=top_clients
        )


def format_human_readable(summary: AnalysisSummary) -> str:
    """Format summary for human-readable output

    Args:
        summary: Analysis summary

    Returns:
        Formatted string
    """
    lines = [
        "=" * 70,
        "API Traffic Pattern Analysis",
        "=" * 70,
        f"Log File: {summary.log_file}",
        "",
        "Traffic Statistics:",
        f"  Total Requests:     {summary.total_requests:,}",
        f"  Unique IPs:         {summary.unique_ips:,}",
        f"  Unique Endpoints:   {summary.unique_endpoints:,}",
        f"  Time Span:          {summary.time_span/3600:.2f} hours",
        f"  Overall RPS:        {summary.overall_rps:.2f}",
        "",
        "Top Endpoints:",
    ]

    for i, (endpoint, count) in enumerate(summary.top_endpoints[:5], 1):
        pct = (count / summary.total_requests * 100) if summary.total_requests > 0 else 0
        lines.append(f"  {i}. {endpoint}: {count:,} ({pct:.1f}%)")

    lines.extend([
        "",
        "Top Clients:",
    ])

    for i, (client, count) in enumerate(summary.top_clients[:5], 1):
        pct = (count / summary.total_requests * 100) if summary.total_requests > 0 else 0
        lines.append(f"  {i}. {client}: {count:,} ({pct:.1f}%)")

    # Abuse detection
    if summary.abuse_detected:
        lines.extend([
            "",
            f"Potential Abuse Detected ({len(summary.abuse_detected)} clients):",
        ])

        for i, abuse in enumerate(summary.abuse_detected[:5], 1):
            lines.append(
                f"  {i}. {abuse['client_id']}: {abuse['rps']:.2f} RPS "
                f"({abuse['request_count']:,} requests, {abuse['severity']} severity)"
            )

    # Pattern analysis
    burst_patterns = [p for p in summary.patterns if p.pattern_type == 'burst']
    scraping_patterns = [p for p in summary.patterns if p.pattern_type == 'scraping']

    if burst_patterns or scraping_patterns:
        lines.extend([
            "",
            "Traffic Patterns:",
            f"  Burst Patterns:    {len(burst_patterns)}",
            f"  Scraping Patterns: {len(scraping_patterns)}",
        ])

    # Recommendations
    if summary.recommendations:
        lines.extend([
            "",
            "Rate Limit Recommendations:",
            "",
        ])

        for i, rec in enumerate(summary.recommendations[:5], 1):
            lines.extend([
                f"{i}. {rec.endpoint}",
                f"   Per Second: {rec.per_second}",
                f"   Per Minute: {rec.per_minute}",
                f"   Per Hour:   {rec.per_hour}",
                f"   Per Day:    {rec.per_day}",
                f"   Burst:      {rec.burst_capacity}",
                f"   Reasoning:  {rec.reasoning}",
                ""
            ])

    lines.append("=" * 70)

    return "\n".join(lines)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Analyze API traffic patterns and recommend rate limits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze access log
  %(prog)s --log-file /var/log/nginx/access.log

  # JSON output
  %(prog)s --log-file access.log --json

  # Custom time window
  %(prog)s --log-file access.log --time-window 3600

  # Custom abuse threshold
  %(prog)s --log-file access.log --abuse-threshold 10
        """
    )

    parser.add_argument('--log-file', required=True,
                       help='Path to access log file')
    parser.add_argument('--time-window', type=int, default=60,
                       help='Time window for pattern analysis in seconds (default: 60)')
    parser.add_argument('--abuse-threshold', type=float, default=5.0,
                       help='RPS threshold for abuse detection (default: 5.0)')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')

    args = parser.parse_args()

    # Parse log file
    if not args.json:
        print(f"Parsing log file: {args.log_file}...")

    parser = LogParser()
    entries = parser.parse_file(args.log_file)

    if not entries:
        print("Error: No valid log entries found", file=sys.stderr)
        sys.exit(1)

    if not args.json:
        print(f"Parsed {len(entries):,} log entries")
        print()

    # Analyze traffic
    analyzer = TrafficAnalyzer(entries)
    summary = analyzer.analyze(args.time_window)
    summary.log_file = args.log_file

    # Output results
    if args.json:
        # Convert to dict, handling complex types
        result = asdict(summary)
        print(json.dumps(result, indent=2, default=str))
    else:
        print(format_human_readable(summary))


if __name__ == '__main__':
    main()
