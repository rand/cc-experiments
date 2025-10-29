#!/usr/bin/env python3
"""
Analyze distributed traces for performance bottlenecks and errors.

This script provides comprehensive analysis of OpenTelemetry traces including:
- Latency bottleneck identification
- Error correlation and patterns
- Service dependency mapping
- Critical path analysis
- Span performance statistics
"""

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import statistics


@dataclass
class Span:
    """Represents a single span in a trace."""

    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    service_name: str
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    tags: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def has_error(self) -> bool:
        """Check if span has error."""
        return self.error is not None or self.tags.get("error", False)


@dataclass
class Trace:
    """Represents a complete trace with multiple spans."""

    trace_id: str
    spans: List[Span]
    start_time: datetime
    end_time: datetime
    duration_ms: float
    root_span: Optional[Span] = None

    @property
    def has_error(self) -> bool:
        """Check if trace has any errors."""
        return any(span.has_error for span in self.spans)

    @property
    def span_count(self) -> int:
        """Get total span count."""
        return len(self.spans)

    @property
    def service_count(self) -> int:
        """Get unique service count."""
        return len({span.service_name for span in self.spans})


class TraceAnalyzer:
    """Analyze distributed traces for patterns and issues."""

    def __init__(self, traces: List[Trace]):
        """
        Initialize analyzer with traces.

        Args:
            traces: List of trace objects to analyze
        """
        self.traces = traces
        self.all_spans = []
        for trace in traces:
            self.all_spans.extend(trace.spans)

    def analyze_latency_bottlenecks(
        self,
        min_percentage: float = 20.0
    ) -> List[Dict[str, Any]]:
        """
        Identify spans that contribute significantly to total latency.

        Args:
            min_percentage: Minimum percentage of trace duration to be considered bottleneck

        Returns:
            List of bottleneck information dictionaries
        """
        bottlenecks = []

        for trace in self.traces:
            if trace.duration_ms == 0:
                continue

            for span in trace.spans:
                percentage = (span.duration_ms / trace.duration_ms) * 100

                if percentage >= min_percentage:
                    bottlenecks.append({
                        "trace_id": trace.trace_id,
                        "span_id": span.span_id,
                        "service": span.service_name,
                        "operation": span.operation_name,
                        "duration_ms": span.duration_ms,
                        "percentage": round(percentage, 2),
                        "trace_duration_ms": trace.duration_ms,
                        "has_error": span.has_error,
                    })

        # Sort by duration
        bottlenecks.sort(key=lambda x: x["duration_ms"], reverse=True)

        return bottlenecks

    def analyze_critical_paths(self) -> List[Dict[str, Any]]:
        """
        Find the longest sequential path (critical path) through each trace.

        Returns:
            List of critical path analyses
        """
        critical_paths = []

        for trace in self.traces:
            # Build span tree
            span_map = {s.span_id: s for s in trace.spans}
            children_map = defaultdict(list)

            for span in trace.spans:
                if span.parent_span_id:
                    children_map[span.parent_span_id].append(span)

            # Find root spans (no parent)
            root_spans = [s for s in trace.spans if not s.parent_span_id]

            if not root_spans:
                continue

            def find_longest_path(span_id: str) -> Tuple[List[Span], float]:
                """Find longest path from this span."""
                span = span_map[span_id]
                children = children_map.get(span_id, [])

                if not children:
                    return [span], span.duration_ms

                # Find longest child path
                child_paths = [find_longest_path(c.span_id) for c in children]
                longest_child_path, child_duration = max(
                    child_paths,
                    key=lambda p: p[1]
                )

                return [span] + longest_child_path, span.duration_ms + child_duration

            # Find longest path from each root
            paths = [find_longest_path(r.span_id) for r in root_spans]
            critical_path, total_duration = max(paths, key=lambda p: p[1])

            critical_paths.append({
                "trace_id": trace.trace_id,
                "total_duration_ms": trace.duration_ms,
                "critical_path_duration_ms": total_duration,
                "span_count": len(critical_path),
                "spans": [
                    {
                        "service": s.service_name,
                        "operation": s.operation_name,
                        "duration_ms": s.duration_ms,
                        "has_error": s.has_error,
                    }
                    for s in critical_path
                ],
            })

        return critical_paths

    def analyze_errors(self) -> Dict[str, Any]:
        """
        Correlate errors across traces and find patterns.

        Returns:
            Dictionary with error analysis
        """
        failing_traces = [t for t in self.traces if t.has_error]

        if not failing_traces:
            return {
                "error_rate": 0,
                "total_traces": len(self.traces),
                "failing_traces": 0,
                "patterns": [],
            }

        # Group errors by service and message
        errors_by_service = defaultdict(list)
        error_patterns = defaultdict(int)

        for trace in failing_traces:
            for span in trace.spans:
                if span.has_error:
                    error_msg = (
                        span.error.get("message", "Unknown error")
                        if span.error
                        else "Error flag set"
                    )

                    errors_by_service[span.service_name].append({
                        "trace_id": trace.trace_id,
                        "span_id": span.span_id,
                        "operation": span.operation_name,
                        "error_message": error_msg,
                        "timestamp": span.start_time.isoformat(),
                    })

                    pattern_key = f"{span.service_name}::{error_msg}"
                    error_patterns[pattern_key] += 1

        # Sort patterns by frequency
        patterns = [
            {
                "service": key.split("::")[0],
                "error_message": key.split("::")[1],
                "count": count,
                "percentage": round((count / len(failing_traces)) * 100, 2),
            }
            for key, count in error_patterns.items()
        ]
        patterns.sort(key=lambda x: x["count"], reverse=True)

        return {
            "error_rate": round((len(failing_traces) / len(self.traces)) * 100, 2),
            "total_traces": len(self.traces),
            "failing_traces": len(failing_traces),
            "errors_by_service": {
                service: {
                    "count": len(errors),
                    "examples": errors[:5],
                }
                for service, errors in errors_by_service.items()
            },
            "patterns": patterns,
        }

    def build_service_dependency_graph(self) -> Dict[str, Any]:
        """
        Build service dependency graph from traces.

        Returns:
            Dictionary with service dependencies and metrics
        """
        dependencies = defaultdict(lambda: defaultdict(int))
        service_metrics = defaultdict(lambda: {
            "call_count": 0,
            "total_duration_ms": 0,
            "error_count": 0,
            "operations": defaultdict(int),
        })

        for trace in self.traces:
            spans_by_id = {s.span_id: s for s in trace.spans}

            for span in trace.spans:
                service = span.service_name

                # Update service metrics
                service_metrics[service]["call_count"] += 1
                service_metrics[service]["total_duration_ms"] += span.duration_ms
                if span.has_error:
                    service_metrics[service]["error_count"] += 1

                service_metrics[service]["operations"][span.operation_name] += 1

                # Track dependencies (parent -> child service calls)
                if span.parent_span_id and span.parent_span_id in spans_by_id:
                    parent = spans_by_id[span.parent_span_id]
                    if parent.service_name != service:
                        dependencies[parent.service_name][service] += 1

        # Calculate averages
        for service, metrics in service_metrics.items():
            metrics["avg_duration_ms"] = round(
                metrics["total_duration_ms"] / metrics["call_count"], 2
            )
            metrics["error_rate"] = round(
                (metrics["error_count"] / metrics["call_count"]) * 100, 2
            )

            # Convert operations to list
            metrics["top_operations"] = sorted(
                [
                    {"operation": op, "count": count}
                    for op, count in metrics["operations"].items()
                ],
                key=lambda x: x["count"],
                reverse=True,
            )[:5]
            del metrics["operations"]

        return {
            "services": dict(service_metrics),
            "dependencies": {
                from_svc: dict(to_svcs)
                for from_svc, to_svcs in dependencies.items()
            },
        }

    def analyze_span_performance(self) -> Dict[str, Any]:
        """
        Analyze performance statistics for each operation.

        Returns:
            Dictionary with operation performance statistics
        """
        operations = defaultdict(list)

        for span in self.all_spans:
            key = f"{span.service_name}::{span.operation_name}"
            operations[key].append(span.duration_ms)

        stats = {}
        for key, durations in operations.items():
            service, operation = key.split("::")

            stats[key] = {
                "service": service,
                "operation": operation,
                "count": len(durations),
                "mean_ms": round(statistics.mean(durations), 2),
                "median_ms": round(statistics.median(durations), 2),
                "min_ms": round(min(durations), 2),
                "max_ms": round(max(durations), 2),
                "p95_ms": round(self._percentile(durations, 95), 2),
                "p99_ms": round(self._percentile(durations, 99), 2),
                "stddev_ms": round(statistics.stdev(durations), 2) if len(durations) > 1 else 0,
            }

        # Sort by mean duration
        sorted_stats = sorted(
            stats.values(),
            key=lambda x: x["mean_ms"],
            reverse=True,
        )

        return {
            "operation_count": len(stats),
            "operations": sorted_stats,
        }

    def filter_traces(
        self,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        min_duration_ms: Optional[float] = None,
        max_duration_ms: Optional[float] = None,
        has_error: Optional[bool] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> List[Trace]:
        """
        Filter traces by various criteria.

        Args:
            service: Filter by service name
            operation: Filter by operation name
            min_duration_ms: Minimum trace duration
            max_duration_ms: Maximum trace duration
            has_error: Filter by error presence
            time_range: Tuple of (start_time, end_time)

        Returns:
            Filtered list of traces
        """
        filtered = self.traces

        if service:
            filtered = [
                t for t in filtered
                if any(s.service_name == service for s in t.spans)
            ]

        if operation:
            filtered = [
                t for t in filtered
                if any(s.operation_name == operation for s in t.spans)
            ]

        if min_duration_ms is not None:
            filtered = [t for t in filtered if t.duration_ms >= min_duration_ms]

        if max_duration_ms is not None:
            filtered = [t for t in filtered if t.duration_ms <= max_duration_ms]

        if has_error is not None:
            filtered = [t for t in filtered if t.has_error == has_error]

        if time_range:
            start_time, end_time = time_range
            filtered = [
                t for t in filtered
                if start_time <= t.start_time <= end_time
            ]

        return filtered

    def get_summary(self) -> Dict[str, Any]:
        """
        Get high-level summary of all traces.

        Returns:
            Summary statistics dictionary
        """
        if not self.traces:
            return {
                "trace_count": 0,
                "span_count": 0,
                "service_count": 0,
                "error_rate": 0,
            }

        durations = [t.duration_ms for t in self.traces]
        failing_count = len([t for t in self.traces if t.has_error])

        services = set()
        for span in self.all_spans:
            services.add(span.service_name)

        return {
            "trace_count": len(self.traces),
            "span_count": len(self.all_spans),
            "service_count": len(services),
            "services": sorted(list(services)),
            "error_rate": round((failing_count / len(self.traces)) * 100, 2),
            "duration_stats": {
                "mean_ms": round(statistics.mean(durations), 2),
                "median_ms": round(statistics.median(durations), 2),
                "min_ms": round(min(durations), 2),
                "max_ms": round(max(durations), 2),
                "p95_ms": round(self._percentile(durations, 95), 2),
                "p99_ms": round(self._percentile(durations, 99), 2),
            },
            "time_range": {
                "start": min(t.start_time for t in self.traces).isoformat(),
                "end": max(t.end_time for t in self.traces).isoformat(),
            },
        }

    @staticmethod
    def _percentile(data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        weight = index - lower

        if upper >= len(sorted_data):
            return sorted_data[-1]

        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight


class TraceLoader:
    """Load traces from various sources."""

    @staticmethod
    def load_from_json_file(file_path: str) -> List[Trace]:
        """
        Load traces from JSON file.

        Args:
            file_path: Path to JSON file containing traces

        Returns:
            List of Trace objects

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file isn't valid JSON
            ValueError: If trace format is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path) as f:
            data = json.load(f)

        if isinstance(data, dict) and "traces" in data:
            data = data["traces"]

        if not isinstance(data, list):
            raise ValueError("Expected list of traces or dict with 'traces' key")

        return [TraceLoader._parse_trace(t) for t in data]

    @staticmethod
    def _parse_trace(trace_data: Dict[str, Any]) -> Trace:
        """Parse trace from dictionary."""
        spans = []

        for span_data in trace_data.get("spans", []):
            span = Span(
                span_id=span_data["span_id"],
                trace_id=span_data["trace_id"],
                parent_span_id=span_data.get("parent_span_id"),
                service_name=span_data["service_name"],
                operation_name=span_data["operation_name"],
                start_time=datetime.fromisoformat(
                    span_data["start_time"].replace("Z", "+00:00")
                ),
                end_time=datetime.fromisoformat(
                    span_data["end_time"].replace("Z", "+00:00")
                ),
                duration_ms=span_data["duration_ms"],
                tags=span_data.get("tags", {}),
                error=span_data.get("error"),
                logs=span_data.get("logs", []),
            )
            spans.append(span)

        if not spans:
            raise ValueError("Trace has no spans")

        start_time = min(s.start_time for s in spans)
        end_time = max(s.end_time for s in spans)
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Find root span
        root_span = next((s for s in spans if not s.parent_span_id), None)

        return Trace(
            trace_id=trace_data["trace_id"],
            spans=spans,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            root_span=root_span,
        )


def parse_time_range(time_range_str: str) -> Tuple[datetime, datetime]:
    """
    Parse time range string.

    Args:
        time_range_str: Time range in format "1h", "30m", "2d"

    Returns:
        Tuple of (start_time, end_time)
    """
    now = datetime.now()

    if time_range_str.endswith("m"):
        minutes = int(time_range_str[:-1])
        start_time = now - timedelta(minutes=minutes)
    elif time_range_str.endswith("h"):
        hours = int(time_range_str[:-1])
        start_time = now - timedelta(hours=hours)
    elif time_range_str.endswith("d"):
        days = int(time_range_str[:-1])
        start_time = now - timedelta(days=days)
    else:
        raise ValueError(f"Invalid time range format: {time_range_str}")

    return start_time, now


def format_output(data: Any, output_format: str) -> str:
    """
    Format output data.

    Args:
        data: Data to format
        output_format: Format type ('json' or 'text')

    Returns:
        Formatted string
    """
    if output_format == "json":
        return json.dumps(data, indent=2, default=str)

    # Text format
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"\n{key}:")
                lines.append(format_output(value, "text"))
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    elif isinstance(data, list):
        lines = []
        for item in data:
            lines.append(format_output(item, "text"))
            lines.append("---")
        return "\n".join(lines)
    else:
        return str(data)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze distributed traces for performance and errors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze traces from file
  %(prog)s traces.json

  # Filter by service
  %(prog)s traces.json --service user-api

  # Find slow traces
  %(prog)s traces.json --latency-threshold 500

  # Analyze errors only
  %(prog)s traces.json --errors-only

  # JSON output
  %(prog)s traces.json --json

  # Full analysis
  %(prog)s traces.json --verbose --bottlenecks --critical-path --dependencies
        """,
    )

    parser.add_argument(
        "trace_file",
        help="JSON file containing traces",
    )

    # Filtering options
    filter_group = parser.add_argument_group("filtering options")
    filter_group.add_argument(
        "--service",
        help="Filter by service name",
    )
    filter_group.add_argument(
        "--operation",
        help="Filter by operation name",
    )
    filter_group.add_argument(
        "--latency-threshold",
        type=float,
        metavar="MS",
        help="Minimum trace duration in milliseconds",
    )
    filter_group.add_argument(
        "--time-range",
        metavar="RANGE",
        help="Time range to analyze (e.g., '1h', '30m', '2d')",
    )
    filter_group.add_argument(
        "--errors-only",
        action="store_true",
        help="Only analyze traces with errors",
    )

    # Analysis options
    analysis_group = parser.add_argument_group("analysis options")
    analysis_group.add_argument(
        "--bottlenecks",
        action="store_true",
        help="Identify latency bottlenecks",
    )
    analysis_group.add_argument(
        "--critical-path",
        action="store_true",
        help="Analyze critical paths",
    )
    analysis_group.add_argument(
        "--errors",
        action="store_true",
        help="Analyze error patterns",
    )
    analysis_group.add_argument(
        "--dependencies",
        action="store_true",
        help="Build service dependency graph",
    )
    analysis_group.add_argument(
        "--performance",
        action="store_true",
        help="Analyze operation performance",
    )

    # Output options
    output_group = parser.add_argument_group("output options")
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    output_group.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    output_group.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Write output to file",
    )

    args = parser.parse_args()

    try:
        # Load traces
        if args.verbose:
            print(f"Loading traces from {args.trace_file}...", file=sys.stderr)

        traces = TraceLoader.load_from_json_file(args.trace_file)

        if args.verbose:
            print(f"Loaded {len(traces)} traces", file=sys.stderr)

        # Create analyzer
        analyzer = TraceAnalyzer(traces)

        # Apply filters
        time_range = None
        if args.time_range:
            time_range = parse_time_range(args.time_range)

        filtered_traces = analyzer.filter_traces(
            service=args.service,
            operation=args.operation,
            min_duration_ms=args.latency_threshold,
            has_error=True if args.errors_only else None,
            time_range=time_range,
        )

        if args.verbose:
            print(f"Analyzing {len(filtered_traces)} traces after filtering", file=sys.stderr)

        # Create filtered analyzer
        filtered_analyzer = TraceAnalyzer(filtered_traces)

        # Perform analysis
        results = {
            "summary": filtered_analyzer.get_summary(),
        }

        # If no specific analysis requested, do all
        do_all = not any([
            args.bottlenecks,
            args.critical_path,
            args.errors,
            args.dependencies,
            args.performance,
        ])

        if args.bottlenecks or do_all:
            if args.verbose:
                print("Analyzing bottlenecks...", file=sys.stderr)
            results["bottlenecks"] = filtered_analyzer.analyze_latency_bottlenecks()

        if args.critical_path or do_all:
            if args.verbose:
                print("Analyzing critical paths...", file=sys.stderr)
            results["critical_paths"] = filtered_analyzer.analyze_critical_paths()

        if args.errors or do_all:
            if args.verbose:
                print("Analyzing errors...", file=sys.stderr)
            results["errors"] = filtered_analyzer.analyze_errors()

        if args.dependencies or do_all:
            if args.verbose:
                print("Building dependency graph...", file=sys.stderr)
            results["dependencies"] = filtered_analyzer.build_service_dependency_graph()

        if args.performance or do_all:
            if args.verbose:
                print("Analyzing performance...", file=sys.stderr)
            results["performance"] = filtered_analyzer.analyze_span_performance()

        # Format output
        output_format = "json" if args.json else "text"
        output = format_output(results, output_format)

        # Write output
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            if args.verbose:
                print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
