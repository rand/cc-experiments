#!/usr/bin/env python3
"""
PostgreSQL Index Recommendation Engine

Analyzes query patterns and suggests optimal indexes based on WHERE clauses,
JOIN conditions, and ORDER BY clauses.

Usage:
    python suggest_indexes.py --query "SELECT * FROM users WHERE email = 'foo@example.com' ORDER BY created_at"
    python suggest_indexes.py --query-file queries.sql --json
    python suggest_indexes.py --connection "postgresql://localhost/mydb" --analyze-workload
"""

import argparse
import json
import re
import sys
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class IndexRecommendation:
    """Represents a recommended index"""
    table: str
    columns: List[str]
    index_type: str = 'btree'
    reason: str = ''
    priority: int = 1  # 1=high, 2=medium, 3=low
    partial_condition: Optional[str] = None
    include_columns: List[str] = None
    example_sql: str = ''

    def __post_init__(self):
        if self.include_columns is None:
            self.include_columns = []


@dataclass
class QueryPattern:
    """Represents a parsed query pattern"""
    tables: Set[str]
    where_conditions: Dict[str, List[str]]  # table -> [columns]
    join_conditions: Dict[str, List[str]]   # table -> [columns]
    order_by: Dict[str, List[str]]          # table -> [columns]
    select_columns: Dict[str, List[str]]    # table -> [columns]


def parse_sql_query(query: str) -> QueryPattern:
    """Parse SQL query to extract optimization opportunities"""
    query = query.strip()
    query_upper = query.upper()

    # Simple parsing (not a full SQL parser, but handles common cases)
    tables = set()
    where_conditions = defaultdict(list)
    join_conditions = defaultdict(list)
    order_by = defaultdict(list)
    select_columns = defaultdict(list)

    # Extract table names from FROM clause
    from_match = re.search(r'\bFROM\s+([\w\s,]+?)(?:\bWHERE\b|\bJOIN\b|\bORDER\b|\bGROUP\b|$)', query, re.IGNORECASE)
    if from_match:
        from_clause = from_match.group(1)
        # Handle aliases (e.g., "users u" or "users AS u")
        for table_part in from_clause.split(','):
            table_match = re.match(r'\s*(\w+)(?:\s+(?:AS\s+)?(\w+))?\s*', table_part.strip())
            if table_match:
                tables.add(table_match.group(1))

    # Extract JOIN conditions
    join_matches = re.finditer(
        r'\bJOIN\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?\s+ON\s+([\w.]+)\s*=\s*([\w.]+)',
        query,
        re.IGNORECASE
    )
    for match in join_matches:
        joined_table = match.group(1)
        tables.add(joined_table)

        # Parse join columns
        left_col = match.group(3)
        right_col = match.group(4)

        for col in [left_col, right_col]:
            if '.' in col:
                table, column = col.split('.', 1)
                join_conditions[table].append(column)

    # Extract WHERE conditions
    where_match = re.search(r'\bWHERE\s+(.+?)(?:\bORDER\b|\bGROUP\b|\bLIMIT\b|$)', query, re.IGNORECASE)
    if where_match:
        where_clause = where_match.group(1)

        # Find column references (simple pattern matching)
        # Handles: table.column = value, column = value, table.column IN (...)
        column_patterns = [
            r'(\w+)\.(\w+)\s*(?:=|<|>|<=|>=|!=|IN|LIKE)',  # table.column
            r'\b(?:AND|OR|WHERE)\s+(\w+)\s*(?:=|<|>|<=|>=|!=|IN|LIKE)',  # column
        ]

        for pattern in column_patterns:
            for match in re.finditer(pattern, where_clause, re.IGNORECASE):
                if match.lastindex == 2:
                    table, column = match.group(1), match.group(2)
                    where_conditions[table].append(column)
                else:
                    column = match.group(1)
                    # Try to infer table (use first table if ambiguous)
                    if tables:
                        inferred_table = list(tables)[0]
                        where_conditions[inferred_table].append(column)

    # Extract ORDER BY
    order_match = re.search(r'\bORDER\s+BY\s+([\w.,\s]+?)(?:\bLIMIT\b|$)', query, re.IGNORECASE)
    if order_match:
        order_clause = order_match.group(1)
        for col_part in order_clause.split(','):
            col_match = re.match(r'\s*(\w+)\.(\w+)', col_part.strip())
            if col_match:
                table, column = col_match.group(1), col_match.group(2)
                order_by[table].append(column)
            else:
                col_match = re.match(r'\s*(\w+)', col_part.strip())
                if col_match and tables:
                    column = col_match.group(1)
                    inferred_table = list(tables)[0]
                    order_by[inferred_table].append(column)

    # Extract SELECT columns (for covering indexes)
    select_match = re.search(r'\bSELECT\s+(.+?)\s+FROM', query, re.IGNORECASE)
    if select_match:
        select_clause = select_match.group(1)
        if select_clause.strip() != '*':
            for col_part in select_clause.split(','):
                col_match = re.match(r'\s*(\w+)\.(\w+)', col_part.strip())
                if col_match:
                    table, column = col_match.group(1), col_match.group(2)
                    select_columns[table].append(column)
                else:
                    col_match = re.match(r'\s*(\w+)', col_part.strip())
                    if col_match and tables:
                        column = col_match.group(1)
                        inferred_table = list(tables)[0]
                        select_columns[inferred_table].append(column)

    return QueryPattern(
        tables=tables,
        where_conditions=dict(where_conditions),
        join_conditions=dict(join_conditions),
        order_by=dict(order_by),
        select_columns=dict(select_columns)
    )


def generate_index_recommendations(pattern: QueryPattern) -> List[IndexRecommendation]:
    """Generate index recommendations based on query pattern"""
    recommendations = []

    for table in pattern.tables:
        where_cols = pattern.where_conditions.get(table, [])
        join_cols = pattern.join_conditions.get(table, [])
        order_cols = pattern.order_by.get(table, [])
        select_cols = pattern.select_columns.get(table, [])

        # Recommendation 1: Index on WHERE columns
        if where_cols:
            unique_where = list(dict.fromkeys(where_cols))  # Remove duplicates, preserve order
            index_cols = unique_where[:3]  # Limit to 3 columns for composite index

            # Check if we can add ORDER BY columns
            if order_cols:
                for col in order_cols:
                    if col not in index_cols and len(index_cols) < 4:
                        index_cols.append(col)

            # Check for covering index opportunity
            include_cols = []
            if select_cols:
                for col in select_cols:
                    if col not in index_cols:
                        include_cols.append(col)

            reason = f"Optimize WHERE clause on {', '.join(unique_where)}"
            if order_cols:
                reason += f" and ORDER BY {', '.join(order_cols)}"

            rec = IndexRecommendation(
                table=table,
                columns=index_cols,
                index_type='btree',
                reason=reason,
                priority=1,
                include_columns=include_cols[:3] if include_cols else []
            )

            # Generate example SQL
            index_name = f"idx_{table}_{'_'.join(index_cols[:3])}"
            cols_str = ', '.join(index_cols)
            if rec.include_columns:
                include_str = ', '.join(rec.include_columns)
                rec.example_sql = f"CREATE INDEX {index_name} ON {table}({cols_str}) INCLUDE ({include_str});"
            else:
                rec.example_sql = f"CREATE INDEX {index_name} ON {table}({cols_str});"

            recommendations.append(rec)

        # Recommendation 2: Index on JOIN columns
        if join_cols:
            unique_join = list(dict.fromkeys(join_cols))
            index_cols = unique_join[:2]

            rec = IndexRecommendation(
                table=table,
                columns=index_cols,
                index_type='btree',
                reason=f"Optimize JOIN on {', '.join(unique_join)}",
                priority=1
            )

            index_name = f"idx_{table}_{'_'.join(index_cols)}"
            cols_str = ', '.join(index_cols)
            rec.example_sql = f"CREATE INDEX {index_name} ON {table}({cols_str});"

            recommendations.append(rec)

        # Recommendation 3: Index for ORDER BY only (if not covered above)
        if order_cols and not where_cols:
            unique_order = list(dict.fromkeys(order_cols))
            index_cols = unique_order[:2]

            rec = IndexRecommendation(
                table=table,
                columns=index_cols,
                index_type='btree',
                reason=f"Optimize ORDER BY {', '.join(unique_order)}",
                priority=2
            )

            index_name = f"idx_{table}_{'_'.join(index_cols)}"
            cols_str = ', '.join(index_cols)
            rec.example_sql = f"CREATE INDEX {index_name} ON {table}({cols_str});"

            recommendations.append(rec)

    return recommendations


def deduplicate_recommendations(recommendations: List[IndexRecommendation]) -> List[IndexRecommendation]:
    """Remove duplicate or redundant index recommendations"""
    # Group by table
    by_table = defaultdict(list)
    for rec in recommendations:
        by_table[rec.table].append(rec)

    deduplicated = []

    for table, table_recs in by_table.items():
        seen = set()

        for rec in sorted(table_recs, key=lambda r: r.priority):
            # Create signature for this index
            sig = (rec.table, tuple(rec.columns), rec.index_type)

            if sig not in seen:
                seen.add(sig)
                deduplicated.append(rec)

    return sorted(deduplicated, key=lambda r: (r.priority, r.table))


def analyze_workload(connection_string: str) -> List[IndexRecommendation]:
    """Analyze query workload from pg_stat_statements"""
    try:
        import psycopg2
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()

        # Get top queries by execution time
        cur.execute("""
            SELECT query, calls, total_exec_time, mean_exec_time
            FROM pg_stat_statements
            WHERE query NOT LIKE '%pg_stat_statements%'
            ORDER BY total_exec_time DESC
            LIMIT 20
        """)

        all_recommendations = []
        for row in cur.fetchall():
            query = row[0]
            try:
                pattern = parse_sql_query(query)
                recommendations = generate_index_recommendations(pattern)
                all_recommendations.extend(recommendations)
            except Exception as e:
                # Skip queries that fail to parse
                continue

        cur.close()
        conn.close()

        return deduplicate_recommendations(all_recommendations)

    except ImportError:
        print("Error: psycopg2 is required for --analyze-workload. Install with: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error analyzing workload: {e}", file=sys.stderr)
        sys.exit(1)


def format_output(recommendations: List[IndexRecommendation], output_format: str) -> str:
    """Format recommendations for output"""
    if output_format == 'json':
        return json.dumps([asdict(rec) for rec in recommendations], indent=2)

    # Text format
    lines = []
    lines.append("=" * 80)
    lines.append("PostgreSQL Index Recommendations")
    lines.append("=" * 80)

    if not recommendations:
        lines.append("\nNo index recommendations generated.")
        lines.append("\nEither the query is already optimal or couldn't be parsed.")
    else:
        lines.append(f"\nFound {len(recommendations)} index recommendation(s):\n")

        # Group by priority
        high_priority = [r for r in recommendations if r.priority == 1]
        medium_priority = [r for r in recommendations if r.priority == 2]
        low_priority = [r for r in recommendations if r.priority == 3]

        if high_priority:
            lines.append("HIGH PRIORITY:")
            for i, rec in enumerate(high_priority, 1):
                lines.append(f"\n  {i}. Table: {rec.table}")
                lines.append(f"     Columns: {', '.join(rec.columns)}")
                lines.append(f"     Reason: {rec.reason}")
                if rec.include_columns:
                    lines.append(f"     Include: {', '.join(rec.include_columns)} (covering index)")
                lines.append(f"     SQL: {rec.example_sql}")

        if medium_priority:
            lines.append("\n\nMEDIUM PRIORITY:")
            for i, rec in enumerate(medium_priority, 1):
                lines.append(f"\n  {i}. Table: {rec.table}")
                lines.append(f"     Columns: {', '.join(rec.columns)}")
                lines.append(f"     Reason: {rec.reason}")
                lines.append(f"     SQL: {rec.example_sql}")

        if low_priority:
            lines.append("\n\nLOW PRIORITY:")
            for i, rec in enumerate(low_priority, 1):
                lines.append(f"\n  {i}. Table: {rec.table}")
                lines.append(f"     Columns: {', '.join(rec.columns)}")
                lines.append(f"     Reason: {rec.reason}")
                lines.append(f"     SQL: {rec.example_sql}")

    lines.append("\n" + "=" * 80)
    lines.append("\nNOTE: Always test index performance in a staging environment first.")
    lines.append("      Use EXPLAIN ANALYZE to verify improvements before production deployment.")
    lines.append("=" * 80)

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Recommend PostgreSQL indexes based on query patterns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single query
  python suggest_indexes.py --query "SELECT * FROM users WHERE email = 'foo@example.com'"

  # Analyze queries from file
  python suggest_indexes.py --query-file queries.sql

  # JSON output
  python suggest_indexes.py --query "SELECT * FROM users WHERE status = 'active'" --json

  # Analyze workload from pg_stat_statements
  python suggest_indexes.py --connection "postgresql://localhost/mydb" --analyze-workload
        """
    )

    parser.add_argument('--query', help='SQL query to analyze')
    parser.add_argument('--query-file', help='File containing SQL queries (one per line or semicolon-separated)')
    parser.add_argument('--connection', help='PostgreSQL connection string')
    parser.add_argument('--analyze-workload', action='store_true', help='Analyze query workload from pg_stat_statements')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')

    args = parser.parse_args()

    output_format = 'json' if args.json else args.format

    recommendations = []

    if args.analyze_workload:
        if not args.connection:
            print("Error: --connection required with --analyze-workload", file=sys.stderr)
            sys.exit(1)
        recommendations = analyze_workload(args.connection)
    elif args.query:
        pattern = parse_sql_query(args.query)
        recommendations = generate_index_recommendations(pattern)
    elif args.query_file:
        with open(args.query_file, 'r') as f:
            content = f.read()
            # Split by semicolon or newline
            queries = [q.strip() for q in re.split(r'[;\n]+', content) if q.strip()]

            all_recs = []
            for query in queries:
                try:
                    pattern = parse_sql_query(query)
                    recs = generate_index_recommendations(pattern)
                    all_recs.extend(recs)
                except Exception as e:
                    continue

            recommendations = deduplicate_recommendations(all_recs)
    else:
        parser.print_help()
        sys.exit(1)

    recommendations = deduplicate_recommendations(recommendations)
    output = format_output(recommendations, output_format)
    print(output)


if __name__ == '__main__':
    main()
