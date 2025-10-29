#!/usr/bin/env python3
"""
Analyze Logs

This script analyzes log patterns, detects anomalies, correlates errors,
and generates reports with actionable recommendations.

Usage:
    analyze_logs.py --backend elasticsearch --days 7
    analyze_logs.py --backend loki --analyze-errors
    analyze_logs.py --backend elasticsearch --days 7 --analyze-patterns --json
    analyze_logs.py --backend loki --detect-anomalies --verbose
"""

import argparse
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
import requests
import re


@dataclass
class LogAnalysisResult:
    """Result of log analysis."""
    backend: str
    time_range: str
    total_logs: int
    error_count: int
    error_rate: float
    patterns: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    correlations: List[Dict[str, Any]]
    recommendations: List[str]


class LogAnalyzer:
    """Analyze logs from various backends."""

    def __init__(
        self,
        backend: str,
        backend_url: str,
        days: int = 7,
        verbose: bool = False
    ):
        self.backend = backend
        self.backend_url = backend_url
        self.days = days
        self.verbose = verbose

    def analyze(
        self,
        analyze_patterns: bool = False,
        analyze_errors: bool = False,
        detect_anomalies: bool = False
    ) -> LogAnalysisResult:
        """Run log analysis."""
        self.log("Starting log analysis...")

        # Fetch logs
        logs = self._fetch_logs()
        self.log(f"Fetched {len(logs)} log entries")

        # Calculate metrics
        total_logs = len(logs)
        error_count = sum(1 for log in logs if self._is_error(log))
        error_rate = (error_count / total_logs * 100) if total_logs > 0 else 0

        self.log(f"Total logs: {total_logs}, Errors: {error_count}, Error rate: {error_rate:.2f}%")

        # Run analyses
        patterns = []
        anomalies = []
        correlations = []

        if analyze_patterns:
            patterns = self._analyze_patterns(logs)
            self.log(f"Found {len(patterns)} patterns")

        if analyze_errors:
            correlations = self._correlate_errors(logs)
            self.log(f"Found {len(correlations)} error correlations")

        if detect_anomalies:
            anomalies = self._detect_anomalies(logs)
            self.log(f"Detected {len(anomalies)} anomalies")

        # Generate recommendations
        recommendations = self._generate_recommendations(
            total_logs, error_count, error_rate, patterns, anomalies, correlations
        )

        return LogAnalysisResult(
            backend=self.backend,
            time_range=f"last {self.days} days",
            total_logs=total_logs,
            error_count=error_count,
            error_rate=error_rate,
            patterns=patterns,
            anomalies=anomalies,
            correlations=correlations,
            recommendations=recommendations
        )

    def _fetch_logs(self) -> List[Dict[str, Any]]:
        """Fetch logs from backend."""
        if self.backend == "elasticsearch":
            return self._fetch_elasticsearch_logs()
        elif self.backend == "loki":
            return self._fetch_loki_logs()
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def _fetch_elasticsearch_logs(self) -> List[Dict[str, Any]]:
        """Fetch logs from Elasticsearch."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=self.days)

        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": start_time.isoformat(),
                        "lte": end_time.isoformat()
                    }
                }
            },
            "size": 10000,  # Max logs to fetch
            "sort": [{"@timestamp": "desc"}]
        }

        try:
            response = requests.post(
                f"{self.backend_url}/logs-*/_search",
                json=query,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            hits = data.get("hits", {}).get("hits", [])

            logs = []
            for hit in hits:
                source = hit.get("_source", {})
                logs.append(source)

            return logs

        except Exception as e:
            self.log(f"Failed to fetch Elasticsearch logs: {e}", error=True)
            return []

    def _fetch_loki_logs(self) -> List[Dict[str, Any]]:
        """Fetch logs from Loki."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=self.days)

        query = '{job!=""}'
        params = {
            "query": query,
            "start": int(start_time.timestamp() * 1e9),  # nanoseconds
            "end": int(end_time.timestamp() * 1e9),
            "limit": 10000
        }

        try:
            response = requests.get(
                f"{self.backend_url}/loki/api/v1/query_range",
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            result = data.get("data", {}).get("result", [])

            logs = []
            for stream in result:
                for value in stream.get("values", []):
                    timestamp_ns, log_line = value
                    timestamp = datetime.fromtimestamp(int(timestamp_ns) / 1e9)

                    # Try to parse JSON log
                    try:
                        log_data = json.loads(log_line)
                        log_data["@timestamp"] = timestamp.isoformat()
                        logs.append(log_data)
                    except json.JSONDecodeError:
                        # Plain text log
                        logs.append({
                            "@timestamp": timestamp.isoformat(),
                            "message": log_line
                        })

            return logs

        except Exception as e:
            self.log(f"Failed to fetch Loki logs: {e}", error=True)
            return []

    def _is_error(self, log: Dict[str, Any]) -> bool:
        """Check if log is an error."""
        level = log.get("level", "").upper()
        if level in ["ERROR", "FATAL", "CRITICAL"]:
            return True

        message = log.get("message", "").lower()
        if any(keyword in message for keyword in ["error", "exception", "failed", "fatal"]):
            return True

        return False

    def _analyze_patterns(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze common log patterns."""
        patterns = []

        # Pattern 1: Most common log levels
        level_counts = Counter(log.get("level", "UNKNOWN") for log in logs)
        patterns.append({
            "type": "log_levels",
            "description": "Distribution of log levels",
            "data": dict(level_counts.most_common(10))
        })

        # Pattern 2: Most common services
        service_counts = Counter(log.get("service", "unknown") for log in logs)
        patterns.append({
            "type": "services",
            "description": "Logs by service",
            "data": dict(service_counts.most_common(10))
        })

        # Pattern 3: Most common error types
        error_logs = [log for log in logs if self._is_error(log)]
        error_types = []
        for log in error_logs:
            error_type = log.get("error", {}).get("type") or \
                         log.get("error_type") or \
                         self._extract_error_type(log.get("message", ""))
            if error_type:
                error_types.append(error_type)

        if error_types:
            error_type_counts = Counter(error_types)
            patterns.append({
                "type": "error_types",
                "description": "Most common error types",
                "data": dict(error_type_counts.most_common(10))
            })

        # Pattern 4: Logs by hour of day
        hour_counts = Counter()
        for log in logs:
            timestamp = log.get("@timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hour_counts[dt.hour] += 1
                except:
                    pass

        if hour_counts:
            patterns.append({
                "type": "hourly_distribution",
                "description": "Logs by hour of day",
                "data": dict(sorted(hour_counts.items()))
            })

        # Pattern 5: Slowest operations
        durations = []
        for log in logs:
            duration = log.get("duration_ms") or log.get("duration") or log.get("elapsed_ms")
            if duration:
                try:
                    durations.append({
                        "service": log.get("service", "unknown"),
                        "endpoint": log.get("endpoint") or log.get("path", "unknown"),
                        "duration_ms": float(duration)
                    })
                except:
                    pass

        if durations:
            durations.sort(key=lambda x: x["duration_ms"], reverse=True)
            patterns.append({
                "type": "slowest_operations",
                "description": "Top 10 slowest operations",
                "data": durations[:10]
            })

        return patterns

    def _correlate_errors(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Correlate errors across services and time."""
        error_logs = [log for log in logs if self._is_error(log)]

        correlations = []

        # Correlation 1: Errors by service and type
        service_error_map = defaultdict(Counter)
        for log in error_logs:
            service = log.get("service", "unknown")
            error_type = log.get("error", {}).get("type") or \
                        log.get("error_type") or \
                        self._extract_error_type(log.get("message", ""))
            if error_type:
                service_error_map[service][error_type] += 1

        for service, error_counts in service_error_map.items():
            correlations.append({
                "type": "service_errors",
                "service": service,
                "errors": dict(error_counts.most_common(5))
            })

        # Correlation 2: Error bursts (spikes in error rate)
        error_timeline = defaultdict(int)
        for log in error_logs:
            timestamp = log.get("@timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    # Round to 5-minute buckets
                    bucket = dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)
                    error_timeline[bucket] += 1
                except:
                    pass

        if error_timeline:
            avg_errors = sum(error_timeline.values()) / len(error_timeline)
            bursts = []
            for timestamp, count in error_timeline.items():
                if count > avg_errors * 2:  # 2x average is a burst
                    bursts.append({
                        "timestamp": timestamp.isoformat(),
                        "error_count": count,
                        "threshold": avg_errors * 2
                    })

            if bursts:
                correlations.append({
                    "type": "error_bursts",
                    "description": "Periods with abnormally high error rates",
                    "bursts": sorted(bursts, key=lambda x: x["error_count"], reverse=True)[:10]
                })

        # Correlation 3: Common error messages
        error_messages = Counter()
        for log in error_logs:
            message = log.get("message", "")
            if message:
                # Normalize message (remove numbers, IDs, etc.)
                normalized = re.sub(r'\d+', 'N', message)
                normalized = re.sub(r'[a-f0-9]{8,}', 'ID', normalized)
                error_messages[normalized] += 1

        if error_messages:
            correlations.append({
                "type": "common_error_messages",
                "description": "Most frequent error messages",
                "messages": [
                    {"message": msg, "count": count}
                    for msg, count in error_messages.most_common(10)
                ]
            })

        return correlations

    def _detect_anomalies(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in log data."""
        anomalies = []

        # Anomaly 1: Sudden traffic drop
        timeline = defaultdict(int)
        for log in logs:
            timestamp = log.get("@timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    # Round to 15-minute buckets
                    bucket = dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)
                    timeline[bucket] += 1
                except:
                    pass

        if len(timeline) > 10:
            counts = list(timeline.values())
            avg_count = sum(counts) / len(counts)

            for timestamp, count in timeline.items():
                if count < avg_count * 0.3:  # Less than 30% of average
                    anomalies.append({
                        "type": "traffic_drop",
                        "severity": "warning",
                        "timestamp": timestamp.isoformat(),
                        "log_count": count,
                        "expected": avg_count,
                        "description": f"Log volume dropped to {count} (expected ~{avg_count:.0f})"
                    })

        # Anomaly 2: New error types
        recent_cutoff = datetime.utcnow() - timedelta(days=1)
        historical_errors = set()
        recent_errors = set()

        for log in logs:
            timestamp_str = log.get("@timestamp")
            if not timestamp_str:
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                continue

            if self._is_error(log):
                error_type = log.get("error", {}).get("type") or \
                            log.get("error_type") or \
                            self._extract_error_type(log.get("message", ""))

                if error_type:
                    if timestamp > recent_cutoff:
                        recent_errors.add(error_type)
                    else:
                        historical_errors.add(error_type)

        new_errors = recent_errors - historical_errors
        if new_errors:
            anomalies.append({
                "type": "new_error_types",
                "severity": "warning",
                "description": "New error types appeared in last 24 hours",
                "errors": list(new_errors)
            })

        # Anomaly 3: High latency operations
        durations = []
        for log in logs:
            duration = log.get("duration_ms") or log.get("duration") or log.get("elapsed_ms")
            if duration:
                try:
                    durations.append({
                        "service": log.get("service", "unknown"),
                        "endpoint": log.get("endpoint") or log.get("path", "unknown"),
                        "duration_ms": float(duration),
                        "timestamp": log.get("@timestamp")
                    })
                except:
                    pass

        if len(durations) > 100:
            duration_values = [d["duration_ms"] for d in durations]
            avg_duration = sum(duration_values) / len(duration_values)
            p95_duration = sorted(duration_values)[int(len(duration_values) * 0.95)]

            high_latency = [
                d for d in durations
                if d["duration_ms"] > p95_duration * 2  # 2x P95
            ]

            if high_latency:
                anomalies.append({
                    "type": "high_latency",
                    "severity": "warning",
                    "description": f"Operations with >2x P95 latency (P95={p95_duration:.0f}ms)",
                    "operations": sorted(
                        high_latency,
                        key=lambda x: x["duration_ms"],
                        reverse=True
                    )[:10]
                })

        # Anomaly 4: Missing expected logs
        services = set(log.get("service") for log in logs if log.get("service"))

        # Check for services with no recent logs
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_services = set()

        for log in logs:
            timestamp_str = log.get("@timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if timestamp > recent_cutoff:
                        service = log.get("service")
                        if service:
                            recent_services.add(service)
                except:
                    pass

        missing_services = services - recent_services
        if missing_services:
            anomalies.append({
                "type": "missing_logs",
                "severity": "warning",
                "description": "Services with no logs in last hour",
                "services": list(missing_services)
            })

        return anomalies

    def _extract_error_type(self, message: str) -> Optional[str]:
        """Extract error type from message."""
        # Common patterns
        patterns = [
            r'(\w+Error)',
            r'(\w+Exception)',
            r'(\w+Failure)',
            r'(\w+Timeout)',
        ]

        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(1)

        return None

    def _generate_recommendations(
        self,
        total_logs: int,
        error_count: int,
        error_rate: float,
        patterns: List[Dict[str, Any]],
        anomalies: List[Dict[str, Any]],
        correlations: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # High error rate
        if error_rate > 5.0:
            recommendations.append(
                f"Error rate is high ({error_rate:.2f}%). Investigate top error types and implement fixes."
            )

        # Log volume
        daily_logs = total_logs / self.days
        if daily_logs > 10_000_000:  # > 10M logs/day
            recommendations.append(
                f"High log volume ({daily_logs:,.0f} logs/day). Consider implementing sampling to reduce costs."
            )

        # Debug logs in production
        for pattern in patterns:
            if pattern["type"] == "log_levels":
                debug_count = pattern["data"].get("DEBUG", 0)
                if debug_count > total_logs * 0.1:  # > 10% debug logs
                    recommendations.append(
                        f"High volume of DEBUG logs ({debug_count:,} = {debug_count/total_logs*100:.1f}%). "
                        "Consider disabling debug logs in production."
                    )

        # Slow operations
        for pattern in patterns:
            if pattern["type"] == "slowest_operations":
                slowest = pattern["data"][0] if pattern["data"] else None
                if slowest and slowest["duration_ms"] > 5000:  # > 5 seconds
                    recommendations.append(
                        f"Slow operations detected (up to {slowest['duration_ms']:.0f}ms). "
                        f"Optimize {slowest['service']}:{slowest['endpoint']}."
                    )

        # Error bursts
        for corr in correlations:
            if corr["type"] == "error_bursts" and corr.get("bursts"):
                recommendations.append(
                    "Error bursts detected. Review deployment history and monitor for similar patterns."
                )
                break

        # New error types
        for anomaly in anomalies:
            if anomaly["type"] == "new_error_types":
                recommendations.append(
                    f"New error types appeared: {', '.join(anomaly['errors'][:3])}. "
                    "Investigate recent changes."
                )

        # Missing logs
        for anomaly in anomalies:
            if anomaly["type"] == "missing_logs":
                recommendations.append(
                    f"Services with no recent logs: {', '.join(list(anomaly['services'])[:3])}. "
                    "Check if services are running."
                )

        # Traffic drop
        traffic_drops = [a for a in anomalies if a["type"] == "traffic_drop"]
        if len(traffic_drops) > 3:
            recommendations.append(
                "Multiple traffic drops detected. Investigate logging pipeline health."
            )

        # General recommendations
        if not recommendations:
            recommendations.append("No critical issues detected. Continue monitoring.")

        # Always add best practices
        recommendations.append("Best practice: Implement structured logging (JSON) for easier analysis.")
        recommendations.append("Best practice: Add trace IDs to correlate logs across services.")
        recommendations.append("Best practice: Set up log-based alerts for critical errors.")

        return recommendations

    def log(self, message: str, error: bool = False) -> None:
        """Log a message."""
        if self.verbose or error:
            prefix = "ERROR" if error else "INFO"
            print(f"[{prefix}] {message}", file=sys.stderr if error else sys.stdout)


def generate_report(result: LogAnalysisResult, format: str = "text") -> str:
    """Generate analysis report."""
    if format == "json":
        return json.dumps(asdict(result), indent=2, default=str)

    # Text report
    lines = []
    lines.append("=" * 80)
    lines.append("LOG ANALYSIS REPORT")
    lines.append("=" * 80)
    lines.append("")

    lines.append(f"Backend:     {result.backend}")
    lines.append(f"Time Range:  {result.time_range}")
    lines.append(f"Total Logs:  {result.total_logs:,}")
    lines.append(f"Error Count: {result.error_count:,}")
    lines.append(f"Error Rate:  {result.error_rate:.2f}%")
    lines.append("")

    # Patterns
    if result.patterns:
        lines.append("-" * 80)
        lines.append("PATTERNS")
        lines.append("-" * 80)
        for pattern in result.patterns:
            lines.append(f"\n{pattern['description']}:")
            if isinstance(pattern["data"], dict):
                for key, value in list(pattern["data"].items())[:10]:
                    lines.append(f"  {key}: {value}")
            elif isinstance(pattern["data"], list):
                for item in pattern["data"][:10]:
                    if isinstance(item, dict):
                        lines.append(f"  {json.dumps(item)}")
                    else:
                        lines.append(f"  {item}")

    # Correlations
    if result.correlations:
        lines.append("")
        lines.append("-" * 80)
        lines.append("ERROR CORRELATIONS")
        lines.append("-" * 80)
        for corr in result.correlations:
            lines.append(f"\n{corr.get('description', corr['type'])}:")
            if corr["type"] == "service_errors":
                lines.append(f"  Service: {corr['service']}")
                for error_type, count in corr["errors"].items():
                    lines.append(f"    {error_type}: {count}")
            elif corr["type"] == "error_bursts":
                for burst in corr.get("bursts", [])[:5]:
                    lines.append(f"  {burst['timestamp']}: {burst['error_count']} errors")
            elif corr["type"] == "common_error_messages":
                for msg in corr.get("messages", [])[:5]:
                    lines.append(f"  [{msg['count']}x] {msg['message'][:60]}...")

    # Anomalies
    if result.anomalies:
        lines.append("")
        lines.append("-" * 80)
        lines.append("ANOMALIES")
        lines.append("-" * 80)
        for anomaly in result.anomalies:
            severity = anomaly.get("severity", "info").upper()
            lines.append(f"\n[{severity}] {anomaly['description']}")
            if anomaly["type"] == "traffic_drop":
                lines.append(f"  Timestamp: {anomaly['timestamp']}")
                lines.append(f"  Log count: {anomaly['log_count']} (expected: {anomaly['expected']:.0f})")
            elif anomaly["type"] == "new_error_types":
                lines.append(f"  Errors: {', '.join(anomaly['errors'])}")
            elif anomaly["type"] == "high_latency":
                for op in anomaly.get("operations", [])[:5]:
                    lines.append(f"  {op['service']}:{op['endpoint']} = {op['duration_ms']:.0f}ms")
            elif anomaly["type"] == "missing_logs":
                lines.append(f"  Services: {', '.join(anomaly['services'])}")

    # Recommendations
    if result.recommendations:
        lines.append("")
        lines.append("-" * 80)
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        for i, rec in enumerate(result.recommendations, 1):
            lines.append(f"\n{i}. {rec}")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze logs for patterns, anomalies, and errors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze logs from Elasticsearch (last 7 days)
  analyze_logs.py --backend elasticsearch --days 7

  # Analyze patterns and detect anomalies
  analyze_logs.py --backend elasticsearch --analyze-patterns --detect-anomalies

  # Focus on error analysis
  analyze_logs.py --backend loki --analyze-errors

  # JSON output
  analyze_logs.py --backend elasticsearch --days 7 --json

  # Full analysis with verbose output
  analyze_logs.py --backend elasticsearch --days 7 \\
    --analyze-patterns --analyze-errors --detect-anomalies --verbose
        """
    )

    parser.add_argument("--backend", required=True, choices=["elasticsearch", "loki"],
                        help="Log backend")
    parser.add_argument("--backend-url",
                        help="Backend URL (default: http://localhost:9200 for ES, http://localhost:3100 for Loki)")
    parser.add_argument("--days", type=int, default=7,
                        help="Number of days to analyze (default: 7)")
    parser.add_argument("--analyze-patterns", action="store_true",
                        help="Analyze log patterns")
    parser.add_argument("--analyze-errors", action="store_true",
                        help="Correlate errors")
    parser.add_argument("--detect-anomalies", action="store_true",
                        help="Detect anomalies")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose output")

    args = parser.parse_args()

    # Default backend URLs
    if not args.backend_url:
        if args.backend == "elasticsearch":
            args.backend_url = "http://localhost:9200"
        elif args.backend == "loki":
            args.backend_url = "http://localhost:3100"

    # If no specific analysis requested, run all
    if not (args.analyze_patterns or args.analyze_errors or args.detect_anomalies):
        args.analyze_patterns = True
        args.analyze_errors = True
        args.detect_anomalies = True

    # Create analyzer
    analyzer = LogAnalyzer(
        backend=args.backend,
        backend_url=args.backend_url,
        days=args.days,
        verbose=args.verbose
    )

    # Run analysis
    try:
        result = analyzer.analyze(
            analyze_patterns=args.analyze_patterns,
            analyze_errors=args.analyze_errors,
            detect_anomalies=args.detect_anomalies
        )

        # Generate report
        report = generate_report(result, format="json" if args.json else "text")
        print(report)

        sys.exit(0)

    except Exception as e:
        print(f"Analysis failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
