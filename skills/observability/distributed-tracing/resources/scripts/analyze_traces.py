#!/usr/bin/env python3
"""
Distributed Tracing Analysis Tool

Analyze trace data to identify slow spans, errors, and performance bottlenecks.
Supports JSON trace format (Jaeger, Zipkin, OTLP) and provides detailed insights.

Usage:
    analyze_traces.py --file traces.json
    analyze_traces.py --file traces.json --slow-threshold 1000
    analyze_traces.py --file traces.json --json
    analyze_traces.py --file traces.json --service user-service
"""

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Span:
    """Represents a span in a distributed trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    service_name: str
    start_time: int  # nanoseconds
    end_time: int    # nanoseconds
    duration_ms: float
    status: str
    kind: str
    attributes: Dict[str, Any]
    events: List[Dict[str, Any]]

    @property
    def is_error(self) -> bool:
        """Check if span represents an error."""
        return self.status.upper() in ["ERROR", "FAILED"]

    @property
    def is_root(self) -> bool:
        """Check if span is a root span (no parent)."""
        return not self.parent_span_id or self.parent_span_id == "0" * 16


@dataclass
class TraceAnalysis:
    """Analysis results for a single trace."""
    trace_id: str
    root_span: Span
    total_spans: int
    total_duration_ms: float
    critical_path_ms: float
    error_count: int
    slow_spans: List[Span]
    error_spans: List[Span]
    services_involved: List[str]
    span_breakdown: Dict[str, int]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze distributed trace data for performance and errors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze traces from file
  %(prog)s --file traces.json

  # Find spans slower than 500ms
  %(prog)s --file traces.json --slow-threshold 500

  # Filter by service
  %(prog)s --file traces.json --service user-service

  # JSON output for automation
  %(prog)s --file traces.json --json

  # Show detailed span breakdown
  %(prog)s --file traces.json --detailed
        """
    )

    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="Path to trace data file (JSON format)"
    )

    parser.add_argument(
        "--slow-threshold",
        type=float,
        default=1000.0,
        help="Threshold in milliseconds for slow spans (default: 1000ms)"
    )

    parser.add_argument(
        "--service",
        type=str,
        help="Filter analysis to specific service name"
    )

    parser.add_argument(
        "--trace-id",
        type=str,
        help="Analyze specific trace by ID"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed span-by-span breakdown"
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of slowest spans to show (default: 10)"
    )

    return parser.parse_args()


def load_traces(file_path: Path) -> List[Dict[str, Any]]:
    """Load trace data from JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Handle different formats
        if isinstance(data, dict):
            # OTLP format
            if "resourceSpans" in data:
                return extract_otlp_spans(data)
            # Jaeger format
            elif "data" in data:
                return extract_jaeger_spans(data)
            # Single trace
            else:
                return [data]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError(f"Unsupported trace format: {type(data)}")

    except Exception as e:
        print(f"Error loading traces: {e}", file=sys.stderr)
        sys.exit(1)


def extract_otlp_spans(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract spans from OTLP format."""
    spans = []
    for resource_span in data.get("resourceSpans", []):
        resource = resource_span.get("resource", {})
        service_name = None

        # Extract service name from resource attributes
        for attr in resource.get("attributes", []):
            if attr.get("key") == "service.name":
                service_name = attr.get("value", {}).get("stringValue")

        for scope_span in resource_span.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                span["service_name"] = service_name
                spans.append(span)

    return spans


def extract_jaeger_spans(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract spans from Jaeger format."""
    spans = []
    for trace in data.get("data", []):
        for span in trace.get("spans", []):
            span["service_name"] = trace.get("processes", {}).get(
                span.get("processID"), {}
            ).get("serviceName")
            spans.append(span)

    return spans


def parse_span(span_data: Dict[str, Any]) -> Span:
    """Parse span from JSON data."""
    # Handle different formats
    span_id = span_data.get("spanId") or span_data.get("span_id")
    parent_span_id = span_data.get("parentSpanId") or span_data.get("parent_span_id")
    trace_id = span_data.get("traceId") or span_data.get("trace_id")

    # Extract timestamps
    start_time = span_data.get("startTimeUnixNano") or span_data.get("start_time")
    end_time = span_data.get("endTimeUnixNano") or span_data.get("end_time")

    # Handle different time formats
    if isinstance(start_time, str):
        start_time = int(start_time)
    if isinstance(end_time, str):
        end_time = int(end_time)

    # Calculate duration in milliseconds
    duration_ns = end_time - start_time if end_time and start_time else 0
    duration_ms = duration_ns / 1_000_000

    # Extract status
    status = span_data.get("status", {})
    if isinstance(status, dict):
        status_code = status.get("code", "UNSET")
    else:
        status_code = status or "UNSET"

    # Extract attributes
    attributes = {}
    for attr in span_data.get("attributes", []):
        key = attr.get("key")
        value = attr.get("value", {})
        # Handle different value types
        for value_type in ["stringValue", "intValue", "boolValue", "doubleValue"]:
            if value_type in value:
                attributes[key] = value[value_type]
                break

    # Extract events
    events = span_data.get("events", [])

    return Span(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        name=span_data.get("name", "unknown"),
        service_name=span_data.get("service_name", "unknown"),
        start_time=start_time,
        end_time=end_time,
        duration_ms=duration_ms,
        status=status_code,
        kind=span_data.get("kind", "INTERNAL"),
        attributes=attributes,
        events=events
    )


def analyze_trace(spans: List[Span], slow_threshold: float) -> TraceAnalysis:
    """Analyze a single trace."""
    if not spans:
        raise ValueError("No spans to analyze")

    # Find root span
    root_span = next((s for s in spans if s.is_root), spans[0])

    # Identify slow and error spans
    slow_spans = [s for s in spans if s.duration_ms >= slow_threshold]
    error_spans = [s for s in spans if s.is_error]

    # Calculate critical path (longest chain)
    critical_path_ms = calculate_critical_path(spans)

    # Get unique services
    services = list(set(s.service_name for s in spans))

    # Span breakdown by type
    span_breakdown = defaultdict(int)
    for span in spans:
        span_breakdown[span.kind] += 1

    return TraceAnalysis(
        trace_id=root_span.trace_id,
        root_span=root_span,
        total_spans=len(spans),
        total_duration_ms=root_span.duration_ms,
        critical_path_ms=critical_path_ms,
        error_count=len(error_spans),
        slow_spans=sorted(slow_spans, key=lambda s: s.duration_ms, reverse=True),
        error_spans=error_spans,
        services_involved=sorted(services),
        span_breakdown=dict(span_breakdown)
    )


def calculate_critical_path(spans: List[Span]) -> float:
    """Calculate the critical path (longest sequential chain) in the trace."""
    # Build parent-child relationships
    children = defaultdict(list)
    span_map = {s.span_id: s for s in spans}

    for span in spans:
        if span.parent_span_id and span.parent_span_id in span_map:
            children[span.parent_span_id].append(span)

    def dfs(span: Span) -> float:
        """Find longest path from this span."""
        if span.span_id not in children:
            return span.duration_ms

        max_child_path = max(
            (dfs(child) for child in children[span.span_id]),
            default=0
        )
        return span.duration_ms + max_child_path

    # Find root and calculate from there
    root = next((s for s in spans if s.is_root), spans[0])
    return dfs(root)


def format_analysis(analysis: TraceAnalysis, detailed: bool, top_n: int) -> str:
    """Format analysis results as human-readable text."""
    output = []
    output.append("=" * 80)
    output.append(f"Trace Analysis: {analysis.trace_id}")
    output.append("=" * 80)
    output.append("")

    # Summary
    output.append("Summary:")
    output.append(f"  Total Spans: {analysis.total_spans}")
    output.append(f"  Total Duration: {analysis.total_duration_ms:.2f}ms")
    output.append(f"  Critical Path: {analysis.critical_path_ms:.2f}ms")
    output.append(f"  Error Count: {analysis.error_count}")
    output.append(f"  Services: {', '.join(analysis.services_involved)}")
    output.append("")

    # Span breakdown
    output.append("Span Breakdown by Kind:")
    for kind, count in sorted(analysis.span_breakdown.items()):
        output.append(f"  {kind}: {count}")
    output.append("")

    # Root span
    output.append("Root Span:")
    output.append(f"  Name: {analysis.root_span.name}")
    output.append(f"  Service: {analysis.root_span.service_name}")
    output.append(f"  Duration: {analysis.root_span.duration_ms:.2f}ms")
    output.append(f"  Status: {analysis.root_span.status}")
    output.append("")

    # Slow spans
    if analysis.slow_spans:
        output.append(f"Top {top_n} Slowest Spans:")
        for span in analysis.slow_spans[:top_n]:
            output.append(f"  [{span.duration_ms:.2f}ms] {span.service_name}/{span.name}")
            if detailed:
                output.append(f"    Span ID: {span.span_id}")
                output.append(f"    Kind: {span.kind}")
                output.append(f"    Status: {span.status}")
                if span.attributes:
                    output.append(f"    Attributes: {json.dumps(span.attributes, indent=6)}")
        output.append("")

    # Error spans
    if analysis.error_spans:
        output.append("Error Spans:")
        for span in analysis.error_spans:
            output.append(f"  [{span.service_name}] {span.name}")
            output.append(f"    Duration: {span.duration_ms:.2f}ms")
            output.append(f"    Status: {span.status}")
            if span.events:
                output.append("    Events:")
                for event in span.events:
                    output.append(f"      - {event.get('name')}: {event.get('attributes', {})}")
            if detailed and span.attributes:
                output.append(f"    Attributes: {json.dumps(span.attributes, indent=6)}")
        output.append("")

    return "\n".join(output)


def format_json(analysis: TraceAnalysis, top_n: int) -> str:
    """Format analysis results as JSON."""
    result = {
        "trace_id": analysis.trace_id,
        "summary": {
            "total_spans": analysis.total_spans,
            "total_duration_ms": analysis.total_duration_ms,
            "critical_path_ms": analysis.critical_path_ms,
            "error_count": analysis.error_count,
            "services_involved": analysis.services_involved
        },
        "span_breakdown": analysis.span_breakdown,
        "root_span": {
            "name": analysis.root_span.name,
            "service": analysis.root_span.service_name,
            "duration_ms": analysis.root_span.duration_ms,
            "status": analysis.root_span.status
        },
        "slow_spans": [
            {
                "name": span.name,
                "service": span.service_name,
                "duration_ms": span.duration_ms,
                "span_id": span.span_id,
                "kind": span.kind,
                "status": span.status,
                "attributes": span.attributes
            }
            for span in analysis.slow_spans[:top_n]
        ],
        "error_spans": [
            {
                "name": span.name,
                "service": span.service_name,
                "duration_ms": span.duration_ms,
                "span_id": span.span_id,
                "status": span.status,
                "events": span.events,
                "attributes": span.attributes
            }
            for span in analysis.error_spans
        ]
    }

    return json.dumps(result, indent=2)


def main():
    """Main entry point."""
    args = parse_args()

    # Load traces
    trace_data = load_traces(args.file)

    # Parse spans
    spans = [parse_span(span_data) for span_data in trace_data]

    # Filter by service if specified
    if args.service:
        spans = [s for s in spans if s.service_name == args.service]
        if not spans:
            print(f"No spans found for service: {args.service}", file=sys.stderr)
            sys.exit(1)

    # Filter by trace_id if specified
    if args.trace_id:
        spans = [s for s in spans if s.trace_id == args.trace_id]
        if not spans:
            print(f"No spans found for trace: {args.trace_id}", file=sys.stderr)
            sys.exit(1)

    # Group spans by trace
    traces = defaultdict(list)
    for span in spans:
        traces[span.trace_id].append(span)

    # Analyze each trace
    analyses = []
    for trace_id, trace_spans in traces.items():
        try:
            analysis = analyze_trace(trace_spans, args.slow_threshold)
            analyses.append(analysis)
        except Exception as e:
            print(f"Error analyzing trace {trace_id}: {e}", file=sys.stderr)
            continue

    # Output results
    if args.json:
        # JSON output
        results = [format_json(analysis, args.top_n) for analysis in analyses]
        print(json.dumps([json.loads(r) for r in results], indent=2))
    else:
        # Human-readable output
        for analysis in analyses:
            print(format_analysis(analysis, args.detailed, args.top_n))
            print()

    # Exit with error code if any errors found
    total_errors = sum(a.error_count for a in analyses)
    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
