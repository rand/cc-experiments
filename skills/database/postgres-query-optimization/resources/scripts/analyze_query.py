#!/usr/bin/env python3
"""
PostgreSQL Query Analyzer

Analyzes EXPLAIN output and suggests optimizations for slow queries.
Parses EXPLAIN (ANALYZE, BUFFERS) output and provides actionable recommendations.

Usage:
    python analyze_query.py --query "SELECT * FROM users WHERE email = 'foo@example.com'" --connection "postgresql://localhost/mydb"
    python analyze_query.py --explain-file explain_output.txt --json
    cat explain.json | python analyze_query.py --stdin --format json
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ScanNode:
    """Represents a scan node in the query plan"""
    node_type: str
    relation: Optional[str]
    startup_cost: float
    total_cost: float
    plan_rows: int
    plan_width: int
    actual_time_start: Optional[float] = None
    actual_time_end: Optional[float] = None
    actual_rows: Optional[int] = None
    loops: Optional[int] = None
    filter_text: Optional[str] = None
    rows_removed: Optional[int] = None
    index_cond: Optional[str] = None
    heap_fetches: Optional[int] = None


@dataclass
class QueryAnalysis:
    """Results of query analysis"""
    issues: List[Dict[str, str]]
    suggestions: List[Dict[str, str]]
    metrics: Dict[str, Any]
    scan_nodes: List[ScanNode]


def parse_explain_text(explain_output: str) -> List[ScanNode]:
    """Parse text-format EXPLAIN output into scan nodes"""
    nodes = []
    lines = explain_output.strip().split('\n')

    for line in lines:
        # Parse scan node lines
        # Example: "Seq Scan on users  (cost=0.00..1234.56 rows=10000 width=64) (actual time=0.012..12.345 rows=9998 loops=1)"
        scan_match = re.search(
            r'(Seq Scan|Index Scan|Index Only Scan|Bitmap Heap Scan|Bitmap Index Scan)\s+(?:using\s+\w+\s+)?on\s+(\w+)',
            line
        )

        if scan_match:
            node_type = scan_match.group(1)
            relation = scan_match.group(2)

            # Parse costs
            cost_match = re.search(r'cost=([\d.]+)\.\.([\d.]+)', line)
            startup_cost = float(cost_match.group(1)) if cost_match else 0.0
            total_cost = float(cost_match.group(2)) if cost_match else 0.0

            # Parse plan estimates
            rows_match = re.search(r'rows=(\d+)', line)
            width_match = re.search(r'width=(\d+)', line)
            plan_rows = int(rows_match.group(1)) if rows_match else 0
            plan_width = int(width_match.group(1)) if width_match else 0

            # Parse actual timing (if ANALYZE was used)
            actual_match = re.search(r'actual time=([\d.]+)\.\.([\d.]+)', line)
            actual_rows_match = re.search(r'rows=(\d+)', line.split('actual')[1]) if 'actual' in line else None
            loops_match = re.search(r'loops=(\d+)', line)

            actual_time_start = float(actual_match.group(1)) if actual_match else None
            actual_time_end = float(actual_match.group(2)) if actual_match else None
            actual_rows = int(actual_rows_match.group(1)) if actual_rows_match else None
            loops = int(loops_match.group(1)) if loops_match else None

            node = ScanNode(
                node_type=node_type,
                relation=relation,
                startup_cost=startup_cost,
                total_cost=total_cost,
                plan_rows=plan_rows,
                plan_width=plan_width,
                actual_time_start=actual_time_start,
                actual_time_end=actual_time_end,
                actual_rows=actual_rows,
                loops=loops
            )

            nodes.append(node)

        # Parse filter information
        if 'Filter:' in line and nodes:
            filter_match = re.search(r'Filter:\s+(.+)', line)
            if filter_match:
                nodes[-1].filter_text = filter_match.group(1)

        # Parse rows removed by filter
        if 'Rows Removed by Filter:' in line and nodes:
            removed_match = re.search(r'Rows Removed by Filter:\s+(\d+)', line)
            if removed_match:
                nodes[-1].rows_removed = int(removed_match.group(1))

        # Parse index condition
        if 'Index Cond:' in line and nodes:
            cond_match = re.search(r'Index Cond:\s+(.+)', line)
            if cond_match:
                nodes[-1].index_cond = cond_match.group(1)

        # Parse heap fetches (Index Only Scan)
        if 'Heap Fetches:' in line and nodes:
            fetches_match = re.search(r'Heap Fetches:\s+(\d+)', line)
            if fetches_match:
                nodes[-1].heap_fetches = int(fetches_match.group(1))

    return nodes


def analyze_scan_nodes(nodes: List[ScanNode]) -> QueryAnalysis:
    """Analyze scan nodes and identify issues/suggestions"""
    issues = []
    suggestions = []
    metrics = {}

    for node in nodes:
        # Issue: Sequential scan on potentially large table
        if node.node_type == 'Seq Scan':
            if node.actual_rows and node.actual_rows > 10000:
                issues.append({
                    'severity': 'high',
                    'type': 'seq_scan',
                    'table': node.relation,
                    'message': f'Sequential scan on large table {node.relation} ({node.actual_rows:,} rows)'
                })
                suggestions.append({
                    'type': 'index',
                    'table': node.relation,
                    'message': f'Consider creating an index on {node.relation} for WHERE/JOIN conditions',
                    'example': f'CREATE INDEX idx_{node.relation}_<column> ON {node.relation}(<column>);'
                })
            elif node.plan_rows > 10000:
                issues.append({
                    'severity': 'medium',
                    'type': 'seq_scan',
                    'table': node.relation,
                    'message': f'Sequential scan on table {node.relation} (estimated {node.plan_rows:,} rows)'
                })

        # Issue: Large row estimate mismatch
        if node.actual_rows is not None and node.plan_rows > 0:
            estimate_ratio = node.actual_rows / node.plan_rows
            if estimate_ratio > 10 or estimate_ratio < 0.1:
                issues.append({
                    'severity': 'high',
                    'type': 'estimate_mismatch',
                    'table': node.relation,
                    'message': f'Row estimate mismatch on {node.relation}: planned {node.plan_rows}, actual {node.actual_rows} (ratio: {estimate_ratio:.2f}x)'
                })
                suggestions.append({
                    'type': 'statistics',
                    'table': node.relation,
                    'message': f'Run ANALYZE on {node.relation} to update statistics',
                    'example': f'ANALYZE {node.relation};'
                })

        # Issue: Filter removing many rows
        if node.rows_removed and node.actual_rows is not None:
            total_scanned = node.actual_rows + node.rows_removed
            if total_scanned > 0:
                filter_ratio = node.rows_removed / total_scanned
                if filter_ratio > 0.9:
                    issues.append({
                        'severity': 'high',
                        'type': 'inefficient_filter',
                        'table': node.relation,
                        'message': f'Filter on {node.relation} removes {filter_ratio*100:.1f}% of rows ({node.rows_removed:,} / {total_scanned:,})'
                    })
                    suggestions.append({
                        'type': 'index',
                        'table': node.relation,
                        'message': f'Create index on filter column to avoid scanning filtered rows',
                        'example': f'CREATE INDEX idx_{node.relation}_filter ON {node.relation}(<filter_column>);'
                    })

        # Issue: Index scan with many heap fetches
        if node.node_type == 'Index Only Scan' and node.heap_fetches:
            if node.actual_rows and node.heap_fetches > node.actual_rows * 0.1:
                issues.append({
                    'severity': 'medium',
                    'type': 'heap_fetches',
                    'table': node.relation,
                    'message': f'Index Only Scan on {node.relation} performing {node.heap_fetches} heap fetches'
                })
                suggestions.append({
                    'type': 'vacuum',
                    'table': node.relation,
                    'message': f'Run VACUUM on {node.relation} to update visibility map',
                    'example': f'VACUUM {node.relation};'
                })

        # Issue: Nested loop with high iteration count
        if node.loops and node.loops > 100:
            if node.actual_time_end and node.actual_time_start:
                time_per_loop = (node.actual_time_end - node.actual_time_start) / node.loops
                total_time = (node.actual_time_end - node.actual_time_start) * node.loops
                if total_time > 100:  # ms
                    issues.append({
                        'severity': 'high',
                        'type': 'nested_loop',
                        'table': node.relation,
                        'message': f'Nested loop on {node.relation} executed {node.loops} times ({total_time:.2f}ms total)'
                    })
                    suggestions.append({
                        'type': 'join',
                        'table': node.relation,
                        'message': f'Consider hash join or merge join instead of nested loop',
                        'example': 'SET enable_nestloop = off; -- Test alternative join strategies'
                    })

    # Calculate overall metrics
    if nodes:
        total_cost = sum(node.total_cost for node in nodes)
        total_time = sum(
            (node.actual_time_end or 0) * (node.loops or 1)
            for node in nodes
            if node.actual_time_end
        )
        total_rows = sum(
            (node.actual_rows or 0) * (node.loops or 1)
            for node in nodes
            if node.actual_rows
        )

        metrics = {
            'total_cost': total_cost,
            'total_time_ms': total_time,
            'total_rows': total_rows,
            'num_scans': len(nodes),
            'seq_scans': sum(1 for n in nodes if n.node_type == 'Seq Scan'),
            'index_scans': sum(1 for n in nodes if 'Index' in n.node_type)
        }

    return QueryAnalysis(
        issues=issues,
        suggestions=suggestions,
        metrics=metrics,
        scan_nodes=nodes
    )


def format_output(analysis: QueryAnalysis, output_format: str) -> str:
    """Format analysis results"""
    if output_format == 'json':
        return json.dumps({
            'issues': analysis.issues,
            'suggestions': analysis.suggestions,
            'metrics': analysis.metrics
        }, indent=2)

    # Text format
    lines = []
    lines.append("=" * 80)
    lines.append("PostgreSQL Query Analysis")
    lines.append("=" * 80)

    # Metrics
    if analysis.metrics:
        lines.append("\nMetrics:")
        lines.append(f"  Total Cost: {analysis.metrics.get('total_cost', 0):.2f}")
        if 'total_time_ms' in analysis.metrics:
            lines.append(f"  Total Time: {analysis.metrics['total_time_ms']:.2f} ms")
        if 'total_rows' in analysis.metrics:
            lines.append(f"  Total Rows: {analysis.metrics['total_rows']:,}")
        lines.append(f"  Sequential Scans: {analysis.metrics.get('seq_scans', 0)}")
        lines.append(f"  Index Scans: {analysis.metrics.get('index_scans', 0)}")

    # Issues
    if analysis.issues:
        lines.append("\nIssues Found:")
        for i, issue in enumerate(analysis.issues, 1):
            severity = issue['severity'].upper()
            lines.append(f"\n  [{severity}] {issue['message']}")
    else:
        lines.append("\nNo issues found.")

    # Suggestions
    if analysis.suggestions:
        lines.append("\nSuggestions:")
        for i, suggestion in enumerate(analysis.suggestions, 1):
            lines.append(f"\n  {i}. {suggestion['message']}")
            if 'example' in suggestion:
                lines.append(f"     Example: {suggestion['example']}")

    lines.append("\n" + "=" * 80)
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze PostgreSQL EXPLAIN output and suggest optimizations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze from file
  python analyze_query.py --explain-file explain_output.txt

  # Analyze from stdin
  cat explain.txt | python analyze_query.py --stdin

  # JSON output
  python analyze_query.py --explain-file explain.txt --json

  # Analyze query directly (requires psycopg2)
  python analyze_query.py --query "SELECT * FROM users" --connection "postgresql://localhost/mydb"
        """
    )

    parser.add_argument('--explain-file', help='Path to EXPLAIN output file')
    parser.add_argument('--stdin', action='store_true', help='Read EXPLAIN output from stdin')
    parser.add_argument('--query', help='SQL query to analyze (requires --connection)')
    parser.add_argument('--connection', help='PostgreSQL connection string')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format (default: text)')

    args = parser.parse_args()

    # Determine output format
    output_format = 'json' if args.json else args.format

    # Get EXPLAIN output
    explain_output = None

    if args.explain_file:
        with open(args.explain_file, 'r') as f:
            explain_output = f.read()
    elif args.stdin:
        explain_output = sys.stdin.read()
    elif args.query and args.connection:
        try:
            import psycopg2
            conn = psycopg2.connect(args.connection)
            cur = conn.cursor()
            # SECURITY: User-provided query is directly embedded in EXPLAIN
            # Only use with trusted queries from trusted sources
            cur.execute(f"EXPLAIN (ANALYZE, BUFFERS) {args.query}")
            rows = cur.fetchall()
            explain_output = '\n'.join(row[0] for row in rows)
            cur.close()
            conn.close()
        except ImportError:
            print("Error: psycopg2 is required for --query option. Install with: pip install psycopg2-binary", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error executing query: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    if not explain_output:
        print("Error: No EXPLAIN output provided", file=sys.stderr)
        sys.exit(1)

    # Parse and analyze
    nodes = parse_explain_text(explain_output)
    analysis = analyze_scan_nodes(nodes)

    # Output results
    output = format_output(analysis, output_format)
    print(output)

    # Exit with error code if high-severity issues found
    high_severity_count = sum(1 for issue in analysis.issues if issue['severity'] == 'high')
    sys.exit(1 if high_severity_count > 0 else 0)


if __name__ == '__main__':
    main()
