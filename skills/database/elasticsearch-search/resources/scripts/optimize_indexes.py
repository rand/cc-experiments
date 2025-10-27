#!/usr/bin/env python3
"""
Elasticsearch Index Optimizer

Analyzes Elasticsearch indices and provides optimization recommendations
for mappings, shard sizing, and performance improvements.

Usage:
    ./optimize_indexes.py --index products
    ./optimize_indexes.py --index products --endpoint http://localhost:9200
    ./optimize_indexes.py --index products --json
    ./optimize_indexes.py --all-indices
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class IndexStats:
    """Index statistics"""
    name: str
    doc_count: int
    store_size_bytes: int
    primary_shards: int
    replica_shards: int
    total_shards: int
    avg_doc_size: float
    shard_size_bytes: float


@dataclass
class Recommendation:
    """Optimization recommendation"""
    category: str
    priority: str  # high, medium, low
    issue: str
    recommendation: str
    impact: str
    implementation: Optional[str] = None


@dataclass
class OptimizationResult:
    """Optimization analysis results"""
    index_name: str
    stats: IndexStats
    recommendations: List[Recommendation] = field(default_factory=list)
    mapping_issues: List[Recommendation] = field(default_factory=list)
    health_score: int = 100


class ElasticsearchClient:
    """Simple Elasticsearch HTTP client"""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")

    def request(self, path: str, method: str = "GET") -> Dict[str, Any]:
        """Make HTTP request to Elasticsearch"""
        url = f"{self.endpoint}{path}"
        try:
            req = urllib.request.Request(url, method=method)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise Exception(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {e.reason}")

    def get_index_stats(self, index: str) -> Dict[str, Any]:
        """Get index statistics"""
        return self.request(f"/{index}/_stats")

    def get_index_settings(self, index: str) -> Dict[str, Any]:
        """Get index settings"""
        return self.request(f"/{index}/_settings")

    def get_index_mappings(self, index: str) -> Dict[str, Any]:
        """Get index mappings"""
        return self.request(f"/{index}/_mapping")

    def list_indices(self) -> List[str]:
        """List all indices"""
        cat_indices = self.request("/_cat/indices?format=json")
        return [idx["index"] for idx in cat_indices if not idx["index"].startswith(".")]


class IndexOptimizer:
    """Analyzes and optimizes Elasticsearch indices"""

    def __init__(self, client: ElasticsearchClient):
        self.client = client

    def analyze_index(self, index_name: str) -> OptimizationResult:
        """Analyze an index and provide recommendations"""
        # Get index data
        stats_data = self.client.get_index_stats(index_name)
        settings_data = self.client.get_index_settings(index_name)
        mappings_data = self.client.get_index_mappings(index_name)

        # Extract stats
        index_stats = self._extract_stats(index_name, stats_data, settings_data)

        # Create result
        result = OptimizationResult(
            index_name=index_name,
            stats=index_stats
        )

        # Analyze various aspects
        self._analyze_shard_sizing(result)
        self._analyze_refresh_interval(result, settings_data)
        self._analyze_replicas(result)
        self._analyze_mappings(result, mappings_data)
        self._analyze_index_settings(result, settings_data)

        # Calculate health score
        self._calculate_health_score(result)

        return result

    def _extract_stats(self, index_name: str, stats_data: Dict,
                       settings_data: Dict) -> IndexStats:
        """Extract index statistics"""
        index_stats = stats_data["indices"][index_name]
        total_stats = index_stats["total"]

        # Get shard counts from settings
        settings = settings_data[index_name]["settings"]["index"]
        primary_shards = int(settings.get("number_of_shards", 1))
        replica_shards = int(settings.get("number_of_replicas", 1))

        doc_count = total_stats["docs"]["count"]
        store_size = total_stats["store"]["size_in_bytes"]

        avg_doc_size = store_size / doc_count if doc_count > 0 else 0
        shard_size = store_size / primary_shards if primary_shards > 0 else 0

        return IndexStats(
            name=index_name,
            doc_count=doc_count,
            store_size_bytes=store_size,
            primary_shards=primary_shards,
            replica_shards=replica_shards,
            total_shards=primary_shards * (1 + replica_shards),
            avg_doc_size=avg_doc_size,
            shard_size_bytes=shard_size
        )

    def _analyze_shard_sizing(self, result: OptimizationResult):
        """Analyze shard sizing"""
        stats = result.stats
        shard_size_gb = stats.shard_size_bytes / (1024**3)

        # Optimal shard size: 10-50 GB
        if shard_size_gb < 1 and stats.doc_count > 10000:
            result.recommendations.append(Recommendation(
                category="shard_sizing",
                priority="medium",
                issue=f"Shards are very small ({shard_size_gb:.2f} GB each)",
                recommendation=f"Consider reducing number of primary shards from {stats.primary_shards}",
                impact="Reduces cluster overhead, improves query performance",
                implementation=f"Shrink index or reindex with fewer shards (e.g., {max(1, stats.primary_shards // 2)} shards)"
            ))

        elif shard_size_gb > 50:
            result.recommendations.append(Recommendation(
                category="shard_sizing",
                priority="high",
                issue=f"Shards are very large ({shard_size_gb:.2f} GB each)",
                recommendation=f"Increase number of primary shards from {stats.primary_shards}",
                impact="Improves shard distribution, faster recovery, better performance",
                implementation=f"Reindex with more shards (recommend {int(stats.store_size_bytes / (30 * 1024**3)) + 1} shards for 30GB target)"
            ))

        elif shard_size_gb > 30:
            result.recommendations.append(Recommendation(
                category="shard_sizing",
                priority="medium",
                issue=f"Shards are moderately large ({shard_size_gb:.2f} GB each)",
                recommendation="Monitor shard growth and consider splitting if exceeding 50 GB",
                impact="Prevents future performance degradation",
                implementation="Plan reindexing with more shards when size approaches 50 GB"
            ))

        # Check for over-sharding
        if stats.primary_shards > 10 and shard_size_gb < 5:
            result.recommendations.append(Recommendation(
                category="shard_sizing",
                priority="high",
                issue=f"Over-sharded: {stats.primary_shards} shards with only {shard_size_gb:.2f} GB each",
                recommendation=f"Reduce to {max(1, int(stats.store_size_bytes / (20 * 1024**3)) + 1)} shards",
                impact="Reduces cluster overhead, improves query performance significantly",
                implementation="Shrink index or reindex with fewer shards"
            ))

    def _analyze_refresh_interval(self, result: OptimizationResult, settings_data: Dict):
        """Analyze refresh interval settings"""
        settings = settings_data[result.index_name]["settings"]["index"]
        refresh_interval = settings.get("refresh_interval", "1s")

        if refresh_interval == "1s" and result.stats.doc_count > 1000000:
            result.recommendations.append(Recommendation(
                category="indexing_performance",
                priority="medium",
                issue="Using default 1s refresh interval for large index",
                recommendation="Increase refresh_interval to 30s or higher for better indexing performance",
                impact="Improves indexing throughput by 20-50%, reduces segment creation",
                implementation='PUT /{index}/_settings {"index": {"refresh_interval": "30s"}}'
            ))

    def _analyze_replicas(self, result: OptimizationResult):
        """Analyze replica configuration"""
        stats = result.stats

        if stats.replica_shards == 0:
            result.recommendations.append(Recommendation(
                category="availability",
                priority="high",
                issue="No replica shards configured",
                recommendation="Add at least 1 replica for availability and read throughput",
                impact="Prevents data loss on node failure, improves query throughput",
                implementation='PUT /{index}/_settings {"index": {"number_of_replicas": 1}}'
            ))

        elif stats.replica_shards > 2:
            result.recommendations.append(Recommendation(
                category="resource_usage",
                priority="low",
                issue=f"High replica count: {stats.replica_shards}",
                recommendation="Consider if more than 2 replicas are necessary",
                impact="Reduces storage usage and indexing overhead",
                implementation=f"Review cluster size and reduce replicas if not needed"
            ))

    def _analyze_mappings(self, result: OptimizationResult, mappings_data: Dict):
        """Analyze index mappings"""
        mappings = mappings_data[result.index_name]["mappings"]
        properties = mappings.get("properties", {})

        # Count fields
        field_count = self._count_fields(properties)

        if field_count > 1000:
            result.mapping_issues.append(Recommendation(
                category="mapping_explosion",
                priority="critical",
                issue=f"Very high field count: {field_count}",
                recommendation="Reduce field count using nested objects, flattened type, or dynamic mapping restrictions",
                impact="High memory usage, slow cluster operations, potential cluster instability",
                implementation="Refactor mappings to use nested/flattened types"
            ))
        elif field_count > 500:
            result.mapping_issues.append(Recommendation(
                category="mapping_complexity",
                priority="medium",
                issue=f"High field count: {field_count}",
                recommendation="Monitor field count growth and consider mapping optimizations",
                impact="Increased memory usage, slower indexing",
                implementation="Review and optimize field mappings"
            ))

        # Check for missing multi-fields
        text_fields = self._find_text_fields(properties)
        for field_path in text_fields:
            field_def = self._get_field_definition(properties, field_path)
            if "fields" not in field_def:
                result.mapping_issues.append(Recommendation(
                    category="mapping_optimization",
                    priority="low",
                    issue=f"Text field '{field_path}' has no keyword multi-field",
                    recommendation="Add .keyword multi-field for aggregations and sorting",
                    impact="Enables aggregations and exact matching on text fields",
                    implementation=f'Add "fields": {{"keyword": {{"type": "keyword"}}}} to {field_path} mapping'
                ))

        # Check for dynamic mapping
        dynamic = mappings.get("dynamic", "true")
        if dynamic == "true" and field_count > 100:
            result.mapping_issues.append(Recommendation(
                category="mapping_control",
                priority="medium",
                issue="Dynamic mapping enabled with large field count",
                recommendation="Set dynamic to 'strict' or 'false' to prevent mapping explosion",
                impact="Prevents accidental field creation, controls mapping growth",
                implementation='PUT /{index}/_mapping {"dynamic": "strict"}'
            ))

    def _analyze_index_settings(self, result: OptimizationResult, settings_data: Dict):
        """Analyze index settings"""
        settings = settings_data[result.index_name]["settings"]["index"]

        # Check for index sorting
        if "sort" not in settings and result.stats.doc_count > 100000:
            result.recommendations.append(Recommendation(
                category="query_performance",
                priority="low",
                issue="No index sorting configured",
                recommendation="Consider index sorting for frequently used sort fields",
                impact="Improves query performance for sorted queries, enables early termination",
                implementation="Reindex with index.sort.field and index.sort.order settings"
            ))

        # Check for codec
        codec = settings.get("codec", "default")
        if codec == "default" and result.stats.store_size_bytes > 10 * (1024**3):
            result.recommendations.append(Recommendation(
                category="storage",
                priority="low",
                issue="Using default codec for large index",
                recommendation="Consider 'best_compression' codec to reduce storage",
                impact="Reduces storage by 20-30%, slightly slower indexing",
                implementation='PUT /{index}/_settings {"index": {"codec": "best_compression"}}'
            ))

    def _count_fields(self, properties: Dict, prefix: str = "") -> int:
        """Recursively count fields in mappings"""
        count = 0
        for field_name, field_def in properties.items():
            count += 1
            if "properties" in field_def:
                count += self._count_fields(field_def["properties"], f"{prefix}{field_name}.")
            if "fields" in field_def:
                count += len(field_def["fields"])
        return count

    def _find_text_fields(self, properties: Dict, prefix: str = "") -> List[str]:
        """Find all text fields"""
        text_fields = []
        for field_name, field_def in properties.items():
            field_path = f"{prefix}{field_name}"
            if field_def.get("type") == "text":
                text_fields.append(field_path)
            if "properties" in field_def:
                text_fields.extend(
                    self._find_text_fields(field_def["properties"], f"{field_path}.")
                )
        return text_fields

    def _get_field_definition(self, properties: Dict, field_path: str) -> Dict:
        """Get field definition by path"""
        parts = field_path.split(".")
        current = properties
        for part in parts:
            if part in current:
                current = current[part]
                if "properties" in current:
                    current = current["properties"]
            else:
                return {}
        return current

    def _calculate_health_score(self, result: OptimizationResult):
        """Calculate index health score (0-100)"""
        score = 100

        for rec in result.recommendations:
            if rec.priority == "critical":
                score -= 30
            elif rec.priority == "high":
                score -= 15
            elif rec.priority == "medium":
                score -= 8
            else:
                score -= 3

        for rec in result.mapping_issues:
            if rec.priority == "critical":
                score -= 25
            elif rec.priority == "high":
                score -= 12
            elif rec.priority == "medium":
                score -= 6
            else:
                score -= 2

        result.health_score = max(0, score)


def format_bytes(bytes_val: int) -> str:
    """Format bytes as human-readable string"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} PB"


def format_text_output(results: List[OptimizationResult]) -> str:
    """Format results as human-readable text"""
    output = []

    for result in results:
        output.append(f"\n{'='*80}")
        output.append(f"Index: {result.index_name}")
        output.append(f"Health Score: {result.health_score}/100")
        output.append(f"{'='*80}\n")

        # Stats
        stats = result.stats
        output.append("INDEX STATISTICS:")
        output.append(f"  Documents: {stats.doc_count:,}")
        output.append(f"  Total Size: {format_bytes(stats.store_size_bytes)}")
        output.append(f"  Primary Shards: {stats.primary_shards}")
        output.append(f"  Replica Shards: {stats.replica_shards}")
        output.append(f"  Total Shards: {stats.total_shards}")
        output.append(f"  Average Doc Size: {format_bytes(stats.avg_doc_size)}")
        output.append(f"  Average Shard Size: {format_bytes(stats.shard_size_bytes)}")
        output.append("")

        # Recommendations
        all_recommendations = result.recommendations + result.mapping_issues

        if not all_recommendations:
            output.append("✓ No optimization recommendations. Index is well-configured!\n")
            continue

        # Group by priority
        critical = [r for r in all_recommendations if r.priority == "critical"]
        high = [r for r in all_recommendations if r.priority == "high"]
        medium = [r for r in all_recommendations if r.priority == "medium"]
        low = [r for r in all_recommendations if r.priority == "low"]

        if critical:
            output.append(f"CRITICAL ISSUES ({len(critical)}):")
            output.append("-" * 80)
            for rec in critical:
                output.append(f"\n  Category: {rec.category}")
                output.append(f"  Issue: {rec.issue}")
                output.append(f"  Recommendation: {rec.recommendation}")
                output.append(f"  Impact: {rec.impact}")
                if rec.implementation:
                    output.append(f"  Implementation: {rec.implementation}")
                output.append("")

        if high:
            output.append(f"\nHIGH PRIORITY ({len(high)}):")
            output.append("-" * 80)
            for rec in high:
                output.append(f"\n  Category: {rec.category}")
                output.append(f"  Issue: {rec.issue}")
                output.append(f"  Recommendation: {rec.recommendation}")
                output.append(f"  Impact: {rec.impact}")
                if rec.implementation:
                    output.append(f"  Implementation: {rec.implementation}")
                output.append("")

        if medium:
            output.append(f"\nMEDIUM PRIORITY ({len(medium)}):")
            output.append("-" * 80)
            for rec in medium:
                output.append(f"\n  Category: {rec.category}")
                output.append(f"  Issue: {rec.issue}")
                output.append(f"  Recommendation: {rec.recommendation}")
                if rec.implementation:
                    output.append(f"  Implementation: {rec.implementation}")
                output.append("")

        if low:
            output.append(f"\nLOW PRIORITY ({len(low)}):")
            output.append("-" * 80)
            for rec in low:
                output.append(f"\n  Category: {rec.category}")
                output.append(f"  Recommendation: {rec.recommendation}")
                output.append("")

    return "\n".join(output)


def format_json_output(results: List[OptimizationResult]) -> str:
    """Format results as JSON"""
    output = []
    for result in results:
        output.append({
            "index_name": result.index_name,
            "health_score": result.health_score,
            "statistics": {
                "doc_count": result.stats.doc_count,
                "store_size_bytes": result.stats.store_size_bytes,
                "store_size": format_bytes(result.stats.store_size_bytes),
                "primary_shards": result.stats.primary_shards,
                "replica_shards": result.stats.replica_shards,
                "total_shards": result.stats.total_shards,
                "avg_doc_size_bytes": result.stats.avg_doc_size,
                "avg_shard_size_bytes": result.stats.shard_size_bytes,
                "avg_shard_size": format_bytes(result.stats.shard_size_bytes)
            },
            "recommendations": [
                {
                    "category": rec.category,
                    "priority": rec.priority,
                    "issue": rec.issue,
                    "recommendation": rec.recommendation,
                    "impact": rec.impact,
                    "implementation": rec.implementation
                }
                for rec in result.recommendations
            ],
            "mapping_issues": [
                {
                    "category": rec.category,
                    "priority": rec.priority,
                    "issue": rec.issue,
                    "recommendation": rec.recommendation,
                    "impact": rec.impact,
                    "implementation": rec.implementation
                }
                for rec in result.mapping_issues
            ]
        })
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze and optimize Elasticsearch indices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single index
  ./optimize_indexes.py --index products

  # Analyze with specific endpoint
  ./optimize_indexes.py --index products --endpoint http://localhost:9200

  # JSON output
  ./optimize_indexes.py --index products --json

  # Analyze all indices
  ./optimize_indexes.py --all-indices

  # Analyze specific indices
  ./optimize_indexes.py --index products --index orders
        """
    )

    parser.add_argument(
        "--index",
        action="append",
        dest="indices",
        help="Index name to analyze (can be specified multiple times)"
    )
    parser.add_argument(
        "--all-indices",
        action="store_true",
        help="Analyze all indices"
    )
    parser.add_argument(
        "--endpoint",
        default="http://localhost:9200",
        help="Elasticsearch endpoint (default: http://localhost:9200)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    if not args.indices and not args.all_indices:
        parser.error("Either --index or --all-indices must be specified")

    try:
        client = ElasticsearchClient(args.endpoint)
        optimizer = IndexOptimizer(client)

        # Determine indices to analyze
        if args.all_indices:
            indices = client.list_indices()
        else:
            indices = args.indices

        if not indices:
            print("No indices found to analyze", file=sys.stderr)
            sys.exit(1)

        # Analyze indices
        results = []
        for index in indices:
            try:
                result = optimizer.analyze_index(index)
                results.append(result)
            except Exception as e:
                print(f"Error analyzing index {index}: {e}", file=sys.stderr)

        if not results:
            print("No results to display", file=sys.stderr)
            sys.exit(1)

        # Output results
        if args.json:
            print(format_json_output(results))
        else:
            print(format_text_output(results))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
