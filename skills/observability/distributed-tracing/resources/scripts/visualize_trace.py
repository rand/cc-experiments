#!/usr/bin/env python3
"""
Distributed Tracing Visualization Tool

Generate visualizations of distributed traces including Gantt charts and flame graphs.
Supports JSON trace format and outputs HTML or SVG.

Usage:
    visualize_trace.py --file traces.json --output trace.html
    visualize_trace.py --file traces.json --type flamegraph --output flame.svg
    visualize_trace.py --file traces.json --trace-id abc123 --output trace.html
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

    @property
    def is_root(self) -> bool:
        """Check if span is a root span."""
        return not self.parent_span_id or self.parent_span_id == "0" * 16

    @property
    def is_error(self) -> bool:
        """Check if span has error status."""
        return self.status.upper() in ["ERROR", "FAILED"]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Visualize distributed traces as Gantt charts or flame graphs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate HTML Gantt chart
  %(prog)s --file traces.json --output trace.html

  # Generate flame graph SVG
  %(prog)s --file traces.json --type flamegraph --output flame.svg

  # Visualize specific trace
  %(prog)s --file traces.json --trace-id abc123 --output trace.html

  # Interactive HTML with zoom/pan
  %(prog)s --file traces.json --interactive --output trace.html
        """
    )

    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="Path to trace data file (JSON format)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output file path (.html or .svg)"
    )

    parser.add_argument(
        "--type",
        choices=["gantt", "flamegraph", "timeline"],
        default="gantt",
        help="Visualization type (default: gantt)"
    )

    parser.add_argument(
        "--trace-id",
        type=str,
        help="Specific trace ID to visualize"
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Generate interactive HTML (zoom, pan, tooltips)"
    )

    parser.add_argument(
        "--width",
        type=int,
        default=1200,
        help="Output width in pixels (default: 1200)"
    )

    parser.add_argument(
        "--height",
        type=int,
        default=800,
        help="Output height in pixels (default: 800)"
    )

    return parser.parse_args()


def load_traces(file_path: Path) -> List[Dict[str, Any]]:
    """Load trace data from JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Handle different formats
        if isinstance(data, dict):
            if "resourceSpans" in data:
                return extract_otlp_spans(data)
            elif "data" in data:
                return extract_jaeger_spans(data)
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
    span_id = span_data.get("spanId") or span_data.get("span_id")
    parent_span_id = span_data.get("parentSpanId") or span_data.get("parent_span_id")
    trace_id = span_data.get("traceId") or span_data.get("trace_id")

    start_time = span_data.get("startTimeUnixNano") or span_data.get("start_time")
    end_time = span_data.get("endTimeUnixNano") or span_data.get("end_time")

    if isinstance(start_time, str):
        start_time = int(start_time)
    if isinstance(end_time, str):
        end_time = int(end_time)

    duration_ns = end_time - start_time if end_time and start_time else 0
    duration_ms = duration_ns / 1_000_000

    status = span_data.get("status", {})
    if isinstance(status, dict):
        status_code = status.get("code", "UNSET")
    else:
        status_code = status or "UNSET"

    attributes = {}
    for attr in span_data.get("attributes", []):
        key = attr.get("key")
        value = attr.get("value", {})
        for value_type in ["stringValue", "intValue", "boolValue", "doubleValue"]:
            if value_type in value:
                attributes[key] = value[value_type]
                break

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
        attributes=attributes
    )


def generate_gantt_chart(spans: List[Span], width: int, height: int, interactive: bool) -> str:
    """Generate HTML Gantt chart visualization."""
    # Calculate time bounds
    min_time = min(s.start_time for s in spans)
    max_time = max(s.end_time for s in spans)
    total_duration_ns = max_time - min_time

    # Build tree structure
    children = defaultdict(list)
    span_map = {s.span_id: s for s in spans}

    for span in spans:
        if span.parent_span_id and span.parent_span_id in span_map:
            children[span.parent_span_id].append(span)

    # Assign depth (y-position) to each span
    depth_map = {}

    def assign_depth(span: Span, depth: int = 0):
        depth_map[span.span_id] = depth
        for child in children.get(span.span_id, []):
            assign_depth(child, depth + 1)

    # Find root and assign depths
    root = next((s for s in spans if s.is_root), spans[0])
    assign_depth(root)

    # Generate HTML
    html_parts = []

    # HTML header
    html_parts.append(f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Trace Visualization - {root.trace_id}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: {width}px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            margin-top: 0;
        }}
        .metadata {{
            background: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .metadata-item {{
            margin: 5px 0;
        }}
        svg {{
            border: 1px solid #ddd;
            background: white;
        }}
        .span-bar {{
            cursor: pointer;
            transition: opacity 0.2s;
        }}
        .span-bar:hover {{
            opacity: 0.8;
        }}
        .span-ok {{
            fill: #4caf50;
        }}
        .span-error {{
            fill: #f44336;
        }}
        .span-unset {{
            fill: #2196f3;
        }}
        .span-text {{
            font-size: 11px;
            fill: white;
            pointer-events: none;
        }}
        .timeline-label {{
            font-size: 10px;
            fill: #666;
        }}
        .service-label {{
            font-size: 12px;
            fill: #333;
            font-weight: 500;
        }}
        .tooltip {{
            position: absolute;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 10px;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            z-index: 1000;
            max-width: 400px;
        }}
        .tooltip.visible {{
            opacity: 1;
        }}
        .legend {{
            margin-top: 20px;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 4px;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
            font-size: 14px;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 12px;
            margin-right: 5px;
            vertical-align: middle;
            border-radius: 2px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Trace Visualization</h1>
        <div class="metadata">
            <div class="metadata-item"><strong>Trace ID:</strong> {root.trace_id}</div>
            <div class="metadata-item"><strong>Root Span:</strong> {root.name}</div>
            <div class="metadata-item"><strong>Total Spans:</strong> {len(spans)}</div>
            <div class="metadata-item"><strong>Total Duration:</strong> {total_duration_ns / 1_000_000:.2f}ms</div>
            <div class="metadata-item"><strong>Services:</strong> {', '.join(sorted(set(s.service_name for s in spans)))}</div>
        </div>
""")

    # SVG canvas
    margin_left = 200
    margin_top = 40
    margin_bottom = 40
    row_height = 30
    chart_height = len(spans) * row_height + margin_top + margin_bottom

    html_parts.append(f'<svg width="{width}" height="{chart_height}" id="gantt-chart">')

    # Draw timeline axis
    num_ticks = 10
    for i in range(num_ticks + 1):
        x = margin_left + (width - margin_left - 50) * i / num_ticks
        time_ms = (total_duration_ns / 1_000_000) * i / num_ticks
        html_parts.append(f'<line x1="{x}" y1="{margin_top}" x2="{x}" y2="{chart_height - margin_bottom}" stroke="#eee" stroke-width="1"/>')
        html_parts.append(f'<text x="{x}" y="{margin_top - 5}" text-anchor="middle" class="timeline-label">{time_ms:.1f}ms</text>')

    # Draw spans
    for idx, span in enumerate(sorted(spans, key=lambda s: depth_map.get(s.span_id, 0))):
        y = margin_top + idx * row_height
        depth = depth_map.get(span.span_id, 0)

        # Calculate position
        start_offset = (span.start_time - min_time) / total_duration_ns
        duration_ratio = (span.end_time - span.start_time) / total_duration_ns

        x = margin_left + start_offset * (width - margin_left - 50)
        bar_width = max(duration_ratio * (width - margin_left - 50), 2)

        # Color based on status
        if span.is_error:
            color_class = "span-error"
        elif span.status.upper() == "OK":
            color_class = "span-ok"
        else:
            color_class = "span-unset"

        # Service label
        label_x = margin_left - 10
        html_parts.append(f'<text x="{label_x}" y="{y + 15}" text-anchor="end" class="service-label">{span.service_name[:20]}</text>')

        # Span bar
        indent = depth * 15
        html_parts.append(f'''<rect
            x="{x + indent}"
            y="{y}"
            width="{bar_width}"
            height="{row_height - 5}"
            class="span-bar {color_class}"
            data-span-id="{span.span_id}"
            data-name="{span.name}"
            data-service="{span.service_name}"
            data-duration="{span.duration_ms:.2f}"
            data-status="{span.status}"
            data-kind="{span.kind}"
        />''')

        # Span text (if wide enough)
        if bar_width > 50:
            text_x = x + indent + 5
            html_parts.append(f'<text x="{text_x}" y="{y + 17}" class="span-text">{span.name[:30]}</text>')

    html_parts.append('</svg>')

    # Legend
    html_parts.append("""
        <div class="legend">
            <div class="legend-item">
                <span class="legend-color" style="background: #4caf50;"></span>
                <span>OK</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #f44336;"></span>
                <span>Error</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #2196f3;"></span>
                <span>Unset</span>
            </div>
        </div>
    """)

    # Interactive tooltip
    if interactive:
        html_parts.append("""
        <div id="tooltip" class="tooltip"></div>
        <script>
            const tooltip = document.getElementById('tooltip');
            const bars = document.querySelectorAll('.span-bar');

            bars.forEach(bar => {
                bar.addEventListener('mouseenter', (e) => {
                    const name = e.target.dataset.name;
                    const service = e.target.dataset.service;
                    const duration = e.target.dataset.duration;
                    const status = e.target.dataset.status;
                    const kind = e.target.dataset.kind;

                    tooltip.innerHTML = `
                        <strong>${name}</strong><br>
                        Service: ${service}<br>
                        Duration: ${duration}ms<br>
                        Status: ${status}<br>
                        Kind: ${kind}
                    `;
                    tooltip.classList.add('visible');
                });

                bar.addEventListener('mousemove', (e) => {
                    tooltip.style.left = e.pageX + 10 + 'px';
                    tooltip.style.top = e.pageY + 10 + 'px';
                });

                bar.addEventListener('mouseleave', () => {
                    tooltip.classList.remove('visible');
                });
            });
        </script>
        """)

    html_parts.append("""
    </div>
</body>
</html>
""")

    return "".join(html_parts)


def generate_flamegraph(spans: List[Span], width: int, height: int) -> str:
    """Generate SVG flame graph visualization."""
    # Build tree structure
    children = defaultdict(list)
    span_map = {s.span_id: s for s in spans}

    for span in spans:
        if span.parent_span_id and span.parent_span_id in span_map:
            children[span.parent_span_id].append(span)

    # Find root
    root = next((s for s in spans if s.is_root), spans[0])

    # Assign positions
    positions = []

    def assign_positions(span: Span, depth: int, x_start: float, x_width: float):
        """Recursively assign x,y positions for flame graph."""
        y = height - (depth + 1) * 25
        positions.append((span, x_start, y, x_width, 25))

        # Divide width among children based on duration
        child_spans = children.get(span.span_id, [])
        if child_spans:
            total_child_duration = sum(c.duration_ms for c in child_spans)
            x_offset = x_start

            for child in child_spans:
                child_width = x_width * (child.duration_ms / total_child_duration)
                assign_positions(child, depth + 1, x_offset, child_width)
                x_offset += child_width

    assign_positions(root, 0, 0, width)

    # Generate SVG
    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">')
    svg_parts.append('<style>')
    svg_parts.append('''
        .flame-rect { stroke: white; stroke-width: 1; cursor: pointer; }
        .flame-rect:hover { stroke: black; stroke-width: 2; }
        .flame-text { font-size: 11px; font-family: monospace; fill: white; pointer-events: none; }
    ''')
    svg_parts.append('</style>')

    # Draw rectangles
    for span, x, y, w, h in positions:
        if w < 1:  # Skip tiny spans
            continue

        # Color by service
        color = f"hsl({hash(span.service_name) % 360}, 70%, 50%)"
        if span.is_error:
            color = "#f44336"

        svg_parts.append(f'<rect class="flame-rect" x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}">')
        svg_parts.append(f'<title>{span.service_name}/{span.name} - {span.duration_ms:.2f}ms</title>')
        svg_parts.append('</rect>')

        # Add text if wide enough
        if w > 50:
            text = f"{span.name[:30]} ({span.duration_ms:.1f}ms)"
            svg_parts.append(f'<text class="flame-text" x="{x + 5}" y="{y + 17}">{text}</text>')

    svg_parts.append('</svg>')

    return "".join(svg_parts)


def main():
    """Main entry point."""
    args = parse_args()

    # Load traces
    trace_data = load_traces(args.file)
    spans = [parse_span(span_data) for span_data in trace_data]

    # Filter by trace_id if specified
    if args.trace_id:
        spans = [s for s in spans if s.trace_id == args.trace_id]
        if not spans:
            print(f"No spans found for trace: {args.trace_id}", file=sys.stderr)
            sys.exit(1)

    # Group by trace (use first trace if multiple)
    traces = defaultdict(list)
    for span in spans:
        traces[span.trace_id].append(span)

    if len(traces) > 1 and not args.trace_id:
        print(f"Warning: Multiple traces found ({len(traces)}), using first trace", file=sys.stderr)

    trace_spans = list(traces.values())[0]

    # Generate visualization
    if args.type == "gantt" or args.type == "timeline":
        output = generate_gantt_chart(trace_spans, args.width, args.height, args.interactive)
    elif args.type == "flamegraph":
        output = generate_flamegraph(trace_spans, args.width, args.height)
    else:
        print(f"Unknown visualization type: {args.type}", file=sys.stderr)
        sys.exit(1)

    # Write output
    try:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Visualization saved to: {args.output}")
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
