#!/usr/bin/env python3
"""
Elasticsearch Query Analyzer

Analyzes Elasticsearch Query DSL queries for performance issues and anti-patterns.
Provides actionable recommendations for optimization.

Usage:
    ./analyze_queries.py --query-file queries.json
    ./analyze_queries.py --query '{"query": {"match": {"field": "value"}}}'
    ./analyze_queries.py --query-file queries.json --json
    ./analyze_queries.py --query-file queries.json --endpoint http://localhost:9200
"""

import argparse
import json
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    """Represents a query issue"""
    severity: Severity
    category: str
    message: str
    location: str
    suggestion: str
    impact: str


@dataclass
class AnalysisResult:
    """Analysis results for a query"""
    query_name: str
    issues: List[Issue] = field(default_factory=list)
    score: int = 100
    complexity: str = "low"
    estimated_cost: str = "low"


class QueryAnalyzer:
    """Analyzes Elasticsearch queries for performance issues"""

    def __init__(self):
        self.result = None

    def analyze(self, query: Dict[str, Any], name: str = "query") -> AnalysisResult:
        """Analyze a query and return results"""
        self.result = AnalysisResult(query_name=name)

        # Analyze query structure
        if "query" in query:
            self._analyze_query(query["query"], "query")

        # Analyze aggregations
        if "aggs" in query or "aggregations" in query:
            aggs = query.get("aggs") or query.get("aggregations")
            self._analyze_aggregations(aggs, "aggs")

        # Analyze pagination
        self._analyze_pagination(query)

        # Analyze source filtering
        self._analyze_source(query)

        # Analyze sorting
        if "sort" in query:
            self._analyze_sort(query["sort"])

        # Calculate overall score and complexity
        self._calculate_score()
        self._assess_complexity(query)

        return self.result

    def _analyze_query(self, query: Dict[str, Any], path: str):
        """Analyze query clause"""
        if not query:
            return

        query_type = list(query.keys())[0] if query else None

        if query_type == "bool":
            self._analyze_bool_query(query["bool"], f"{path}.bool")
        elif query_type == "wildcard":
            self._analyze_wildcard(query["wildcard"], f"{path}.wildcard")
        elif query_type == "prefix":
            self._analyze_prefix(query["prefix"], f"{path}.prefix")
        elif query_type == "regexp":
            self._add_issue(
                Severity.WARNING,
                "expensive_query",
                "Regular expression queries are expensive",
                f"{path}.regexp",
                "Use prefix, wildcard, or match queries when possible",
                "High CPU usage, slow query performance"
            )
        elif query_type == "fuzzy":
            self._analyze_fuzzy(query["fuzzy"], f"{path}.fuzzy")
        elif query_type == "match_all":
            self._add_issue(
                Severity.INFO,
                "match_all",
                "Using match_all query",
                f"{path}.match_all",
                "Consider adding filters to reduce result set",
                "Processes all documents in index"
            )
        elif query_type == "nested":
            self._analyze_nested(query["nested"], f"{path}.nested")
        elif query_type == "term":
            self._check_term_on_text(query["term"], f"{path}.term")

    def _analyze_bool_query(self, bool_query: Dict[str, Any], path: str):
        """Analyze bool query structure"""
        # Check if using must instead of filter
        if "must" in bool_query and "filter" not in bool_query:
            # Check if must clauses are exact matches
            must_clauses = bool_query["must"]
            if isinstance(must_clauses, list):
                for i, clause in enumerate(must_clauses):
                    if self._is_exact_match(clause):
                        self._add_issue(
                            Severity.WARNING,
                            "scoring_overhead",
                            "Using 'must' for exact match queries adds scoring overhead",
                            f"{path}.must[{i}]",
                            "Move exact match queries to 'filter' clause for caching and better performance",
                            "Unnecessary scoring calculation, no query caching"
                        )

        # Analyze nested queries
        for clause_type in ["must", "filter", "should", "must_not"]:
            if clause_type in bool_query:
                clauses = bool_query[clause_type]
                if isinstance(clauses, list):
                    for i, clause in enumerate(clauses):
                        self._analyze_query(clause, f"{path}.{clause_type}[{i}]")
                else:
                    self._analyze_query(clauses, f"{path}.{clause_type}")

        # Check should clause optimization
        if "should" in bool_query and "minimum_should_match" not in bool_query:
            if len(bool_query.get("should", [])) > 3:
                self._add_issue(
                    Severity.INFO,
                    "missing_minimum_should_match",
                    "Consider adding 'minimum_should_match' to should clauses",
                    f"{path}.should",
                    "Add 'minimum_should_match' parameter to control matching behavior",
                    "Potentially too many results, unclear matching semantics"
                )

    def _analyze_wildcard(self, wildcard: Dict[str, Any], path: str):
        """Analyze wildcard query"""
        for field, value in wildcard.items():
            if isinstance(value, dict):
                pattern = value.get("value", "")
            else:
                pattern = value

            # Check for leading wildcard
            if pattern.startswith("*") or pattern.startswith("?"):
                self._add_issue(
                    Severity.CRITICAL,
                    "leading_wildcard",
                    f"Leading wildcard in pattern '{pattern}'",
                    f"{path}.{field}",
                    "Avoid leading wildcards or use reverse field indexing with prefix query",
                    "Extremely expensive, scans all terms in field"
                )

            # Check for multiple wildcards
            if pattern.count("*") + pattern.count("?") > 2:
                self._add_issue(
                    Severity.WARNING,
                    "complex_wildcard",
                    f"Complex wildcard pattern with multiple wildcards: '{pattern}'",
                    f"{path}.{field}",
                    "Simplify pattern or use match query with analyzer",
                    "High CPU usage, slower query execution"
                )

    def _analyze_prefix(self, prefix: Dict[str, Any], path: str):
        """Analyze prefix query"""
        for field, value in prefix.items():
            if isinstance(value, dict):
                prefix_val = value.get("value", "")
            else:
                prefix_val = value

            # Check for very short prefix
            if len(prefix_val) < 2:
                self._add_issue(
                    Severity.WARNING,
                    "short_prefix",
                    f"Very short prefix '{prefix_val}' may match too many terms",
                    f"{path}.{field}",
                    "Use longer prefix (3+ characters) or add additional filters",
                    "Large result set, high memory usage"
                )

    def _analyze_fuzzy(self, fuzzy: Dict[str, Any], path: str):
        """Analyze fuzzy query"""
        for field, value in fuzzy.items():
            if isinstance(value, dict):
                fuzziness = value.get("fuzziness", "AUTO")
                if fuzziness not in ["AUTO", "0", "1", "2", 0, 1, 2]:
                    self._add_issue(
                        Severity.WARNING,
                        "high_fuzziness",
                        f"High fuzziness value: {fuzziness}",
                        f"{path}.{field}",
                        "Use 'AUTO' or limit fuzziness to 0-2",
                        "Matches too many unrelated terms, slow execution"
                    )

    def _analyze_nested(self, nested: Dict[str, Any], path: str):
        """Analyze nested query"""
        if "path" in nested and "query" in nested:
            self._add_issue(
                Severity.INFO,
                "nested_query",
                "Nested queries have performance overhead",
                path,
                "Ensure nested queries are necessary; consider flattening if possible",
                "Higher memory usage, slower than regular queries"
            )
            self._analyze_query(nested["query"], f"{path}.query")

    def _check_term_on_text(self, term: Dict[str, Any], path: str):
        """Check if term query might be on a text field"""
        for field, value in term.items():
            # Heuristic: if field doesn't end with .keyword and value contains spaces or mixed case
            if not field.endswith(".keyword"):
                if isinstance(value, str) and (" " in value or any(c.isupper() for c in value)):
                    self._add_issue(
                        Severity.WARNING,
                        "term_on_text",
                        f"Term query on field '{field}' with value '{value}' may not work on text fields",
                        path,
                        "Use 'match' query for text fields or query '{field}.keyword' for exact match",
                        "Query may not match expected documents"
                    )

    def _analyze_aggregations(self, aggs: Dict[str, Any], path: str):
        """Analyze aggregations"""
        for agg_name, agg_def in aggs.items():
            agg_type = next((k for k in agg_def.keys() if k != "aggs" and k != "aggregations"), None)

            if agg_type == "terms":
                self._analyze_terms_agg(agg_def["terms"], f"{path}.{agg_name}")
            elif agg_type == "cardinality":
                self._add_issue(
                    Severity.INFO,
                    "cardinality_aggregation",
                    f"Cardinality aggregation '{agg_name}' is approximate",
                    f"{path}.{agg_name}",
                    "Understand that cardinality uses HyperLogLog (approximate)",
                    "Results are approximate, not exact counts"
                )

            # Check for nested aggregations
            if "aggs" in agg_def or "aggregations" in agg_def:
                nested_aggs = agg_def.get("aggs") or agg_def.get("aggregations")
                self._analyze_aggregations(nested_aggs, f"{path}.{agg_name}")

    def _analyze_terms_agg(self, terms: Dict[str, Any], path: str):
        """Analyze terms aggregation"""
        size = terms.get("size", 10)

        if size > 1000:
            self._add_issue(
                Severity.CRITICAL,
                "large_terms_agg",
                f"Terms aggregation with very large size: {size}",
                path,
                "Use composite aggregation for paginated results or reduce size",
                "High memory usage, potential OOM, slow execution"
            )
        elif size > 100:
            self._add_issue(
                Severity.WARNING,
                "large_terms_agg",
                f"Terms aggregation with large size: {size}",
                path,
                "Consider if you need all {size} buckets or use composite aggregation",
                "Increased memory usage, slower execution"
            )

        # Check for missing field or field type
        field = terms.get("field", "")
        if field and not field.endswith(".keyword") and "." not in field:
            self._add_issue(
                Severity.WARNING,
                "terms_agg_on_text",
                f"Terms aggregation on field '{field}' may be on text field",
                path,
                f"Use '{field}.keyword' for aggregations on text fields",
                "Unexpected results, high memory usage"
            )

    def _analyze_pagination(self, query: Dict[str, Any]):
        """Analyze pagination parameters"""
        from_param = query.get("from", 0)
        size = query.get("size", 10)

        total_fetch = from_param + size

        if total_fetch > 10000:
            self._add_issue(
                Severity.CRITICAL,
                "deep_pagination",
                f"Deep pagination detected: from={from_param}, size={size} (total={total_fetch})",
                "root.pagination",
                "Use 'search_after' for deep pagination or Point In Time (PIT) API",
                "Expensive coordination, high memory usage, slow performance"
            )
        elif total_fetch > 1000:
            self._add_issue(
                Severity.WARNING,
                "deep_pagination",
                f"Moderate pagination depth: from={from_param}, size={size}",
                "root.pagination",
                "Consider using 'search_after' for better performance",
                "Increased memory usage and coordination overhead"
            )

        if size > 100:
            self._add_issue(
                Severity.WARNING,
                "large_page_size",
                f"Large page size: {size}",
                "root.size",
                "Reduce page size to 10-50 for better performance",
                "Large result set processing, high network transfer"
            )

    def _analyze_source(self, query: Dict[str, Any]):
        """Analyze _source filtering"""
        if "_source" not in query:
            if "fields" not in query and "stored_fields" not in query:
                self._add_issue(
                    Severity.INFO,
                    "no_source_filtering",
                    "No source filtering specified",
                    "root._source",
                    "Consider specifying '_source' with specific fields if you don't need all fields",
                    "Larger result payloads, higher network transfer"
                )
        elif query["_source"] is True:
            self._add_issue(
                Severity.INFO,
                "full_source",
                "Fetching full document _source",
                "root._source",
                "Consider limiting to specific fields if not all fields are needed",
                "Larger result payloads"
            )

    def _analyze_sort(self, sort: Any):
        """Analyze sorting"""
        if isinstance(sort, list):
            for i, sort_field in enumerate(sort):
                if isinstance(sort_field, dict):
                    for field in sort_field.keys():
                        if field == "_score":
                            continue
                        if not field.endswith(".keyword"):
                            self._add_issue(
                                Severity.INFO,
                                "sort_on_analyzed",
                                f"Sorting on field '{field}' which may be analyzed",
                                f"root.sort[{i}]",
                                f"Use '{field}.keyword' for sorting on text fields",
                                "Unexpected sort order, higher memory usage"
                            )

    def _is_exact_match(self, clause: Dict[str, Any]) -> bool:
        """Check if a clause is an exact match query"""
        if not clause:
            return False
        query_type = list(clause.keys())[0]
        return query_type in ["term", "terms", "range", "exists", "ids"]

    def _add_issue(self, severity: Severity, category: str, message: str,
                   location: str, suggestion: str, impact: str):
        """Add an issue to results"""
        issue = Issue(
            severity=severity,
            category=category,
            message=message,
            location=location,
            suggestion=suggestion,
            impact=impact
        )
        self.result.issues.append(issue)

    def _calculate_score(self):
        """Calculate overall query score (0-100)"""
        score = 100
        for issue in self.result.issues:
            if issue.severity == Severity.CRITICAL:
                score -= 25
            elif issue.severity == Severity.WARNING:
                score -= 10
            else:
                score -= 2
        self.result.score = max(0, score)

    def _assess_complexity(self, query: Dict[str, Any]):
        """Assess query complexity"""
        complexity_score = 0

        # Count nested bool queries
        complexity_score += self._count_nested_bools(query.get("query", {})) * 2

        # Count aggregations
        if "aggs" in query or "aggregations" in query:
            aggs = query.get("aggs") or query.get("aggregations")
            complexity_score += self._count_aggregations(aggs) * 3

        # Check for nested queries
        if self._has_nested_query(query.get("query", {})):
            complexity_score += 5

        # Assess complexity
        if complexity_score >= 15:
            self.result.complexity = "high"
            self.result.estimated_cost = "high"
        elif complexity_score >= 8:
            self.result.complexity = "medium"
            self.result.estimated_cost = "medium"
        else:
            self.result.complexity = "low"
            self.result.estimated_cost = "low"

    def _count_nested_bools(self, query: Dict[str, Any], depth: int = 0) -> int:
        """Count nested bool queries"""
        if not query or depth > 10:
            return 0

        count = 0
        query_type = list(query.keys())[0] if query else None

        if query_type == "bool":
            count = 1
            bool_query = query["bool"]
            for clause_type in ["must", "filter", "should", "must_not"]:
                if clause_type in bool_query:
                    clauses = bool_query[clause_type]
                    if isinstance(clauses, list):
                        for clause in clauses:
                            count += self._count_nested_bools(clause, depth + 1)
                    else:
                        count += self._count_nested_bools(clauses, depth + 1)

        return count

    def _count_aggregations(self, aggs: Dict[str, Any]) -> int:
        """Count total aggregations including nested"""
        count = len(aggs)
        for agg_def in aggs.values():
            if "aggs" in agg_def or "aggregations" in agg_def:
                nested_aggs = agg_def.get("aggs") or agg_def.get("aggregations")
                count += self._count_aggregations(nested_aggs)
        return count

    def _has_nested_query(self, query: Dict[str, Any]) -> bool:
        """Check if query contains nested queries"""
        if not query:
            return False
        query_type = list(query.keys())[0] if query else None
        return query_type == "nested"


def format_text_output(results: List[AnalysisResult]) -> str:
    """Format results as human-readable text"""
    output = []

    for result in results:
        output.append(f"\n{'='*80}")
        output.append(f"Query: {result.query_name}")
        output.append(f"Score: {result.score}/100")
        output.append(f"Complexity: {result.complexity}")
        output.append(f"Estimated Cost: {result.estimated_cost}")
        output.append(f"Issues Found: {len(result.issues)}")
        output.append(f"{'='*80}\n")

        if not result.issues:
            output.append("✓ No issues found. Query looks good!\n")
            continue

        # Group by severity
        critical = [i for i in result.issues if i.severity == Severity.CRITICAL]
        warnings = [i for i in result.issues if i.severity == Severity.WARNING]
        info = [i for i in result.issues if i.severity == Severity.INFO]

        if critical:
            output.append(f"CRITICAL ISSUES ({len(critical)}):")
            output.append("-" * 80)
            for issue in critical:
                output.append(f"\n  Location: {issue.location}")
                output.append(f"  Issue: {issue.message}")
                output.append(f"  Impact: {issue.impact}")
                output.append(f"  Suggestion: {issue.suggestion}\n")

        if warnings:
            output.append(f"\nWARNINGS ({len(warnings)}):")
            output.append("-" * 80)
            for issue in warnings:
                output.append(f"\n  Location: {issue.location}")
                output.append(f"  Issue: {issue.message}")
                output.append(f"  Impact: {issue.impact}")
                output.append(f"  Suggestion: {issue.suggestion}\n")

        if info:
            output.append(f"\nINFORMATIONAL ({len(info)}):")
            output.append("-" * 80)
            for issue in info:
                output.append(f"\n  Location: {issue.location}")
                output.append(f"  Issue: {issue.message}")
                output.append(f"  Suggestion: {issue.suggestion}\n")

    return "\n".join(output)


def format_json_output(results: List[AnalysisResult]) -> str:
    """Format results as JSON"""
    output = []
    for result in results:
        output.append({
            "query_name": result.query_name,
            "score": result.score,
            "complexity": result.complexity,
            "estimated_cost": result.estimated_cost,
            "issues": [
                {
                    "severity": issue.severity.value,
                    "category": issue.category,
                    "message": issue.message,
                    "location": issue.location,
                    "suggestion": issue.suggestion,
                    "impact": issue.impact
                }
                for issue in result.issues
            ]
        })
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Elasticsearch queries for performance issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze query from file
  ./analyze_queries.py --query-file queries.json

  # Analyze single query
  ./analyze_queries.py --query '{"query": {"match": {"title": "test"}}}'

  # JSON output
  ./analyze_queries.py --query-file queries.json --json

  # Specify Elasticsearch endpoint
  ./analyze_queries.py --query-file queries.json --endpoint http://localhost:9200
        """
    )

    parser.add_argument(
        "--query",
        help="Query JSON string to analyze"
    )
    parser.add_argument(
        "--query-file",
        help="Path to file containing query or queries (JSON)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--endpoint",
        default="http://localhost:9200",
        help="Elasticsearch endpoint (default: http://localhost:9200)"
    )

    args = parser.parse_args()

    if not args.query and not args.query_file:
        parser.error("Either --query or --query-file must be specified")

    # Load queries
    queries = []
    try:
        if args.query:
            query_data = json.loads(args.query)
            queries.append(("command_line_query", query_data))
        elif args.query_file:
            with open(args.query_file, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for i, q in enumerate(data):
                        queries.append((f"query_{i+1}", q))
                elif isinstance(data, dict):
                    if "query" in data or "aggs" in data or "aggregations" in data:
                        queries.append(("query", data))
                    else:
                        for name, query in data.items():
                            queries.append((name, query))
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File not found: {args.query_file}", file=sys.stderr)
        sys.exit(1)

    # Analyze queries
    analyzer = QueryAnalyzer()
    results = []

    for name, query in queries:
        result = analyzer.analyze(query, name)
        results.append(result)

    # Output results
    if args.json:
        print(format_json_output(results))
    else:
        print(format_text_output(results))

    # Exit with error code if critical issues found
    has_critical = any(
        any(issue.severity == Severity.CRITICAL for issue in result.issues)
        for result in results
    )
    sys.exit(1 if has_critical else 0)


if __name__ == "__main__":
    main()
