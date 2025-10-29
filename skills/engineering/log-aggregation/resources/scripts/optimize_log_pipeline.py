#!/usr/bin/env python3
"""
Optimize Log Pipeline

This script analyzes log pipeline performance and costs, then provides
optimization recommendations including sampling strategies, retention policies,
and performance tuning.

Usage:
    optimize_log_pipeline.py --backend elasticsearch
    optimize_log_pipeline.py --backend loki --analyze-costs
    optimize_log_pipeline.py --backend elasticsearch --recommend-sampling --json
    optimize_log_pipeline.py --backend elasticsearch --validate-retention --verbose
"""

import argparse
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import requests


@dataclass
class OptimizationResult:
    """Result of pipeline optimization analysis."""
    backend: str
    current_metrics: Dict[str, Any]
    cost_analysis: Dict[str, Any]
    performance_analysis: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    estimated_savings: Dict[str, Any]


class LogPipelineOptimizer:
    """Optimize log pipeline for cost and performance."""

    def __init__(
        self,
        backend: str,
        backend_url: str,
        verbose: bool = False
    ):
        self.backend = backend
        self.backend_url = backend_url
        self.verbose = verbose

        # Cost assumptions (USD)
        self.storage_cost_per_gb = 0.10  # Per GB per month
        self.elasticsearch_compute_cost = 0.50  # Per hour for medium instance
        self.loki_compute_cost = 0.20  # Per hour for medium instance

    def optimize(
        self,
        analyze_costs: bool = False,
        recommend_sampling: bool = False,
        validate_retention: bool = False
    ) -> OptimizationResult:
        """Run optimization analysis."""
        self.log("Starting pipeline optimization...")

        # Collect current metrics
        current_metrics = self._collect_metrics()
        self.log(f"Collected metrics: {json.dumps(current_metrics, indent=2)}")

        # Analyses
        cost_analysis = {}
        performance_analysis = {}
        recommendations = []

        if analyze_costs:
            cost_analysis = self._analyze_costs(current_metrics)
            recommendations.extend(self._generate_cost_recommendations(cost_analysis))

        if recommend_sampling:
            sampling_recs = self._recommend_sampling(current_metrics)
            recommendations.extend(sampling_recs)

        if validate_retention:
            retention_recs = self._validate_retention(current_metrics)
            recommendations.extend(retention_recs)

        # Performance analysis (always run)
        performance_analysis = self._analyze_performance(current_metrics)
        recommendations.extend(self._generate_performance_recommendations(performance_analysis))

        # Calculate estimated savings
        estimated_savings = self._calculate_savings(
            current_metrics, cost_analysis, recommendations
        )

        return OptimizationResult(
            backend=self.backend,
            current_metrics=current_metrics,
            cost_analysis=cost_analysis,
            performance_analysis=performance_analysis,
            recommendations=recommendations,
            estimated_savings=estimated_savings
        )

    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current pipeline metrics."""
        if self.backend == "elasticsearch":
            return self._collect_elasticsearch_metrics()
        elif self.backend == "loki":
            return self._collect_loki_metrics()
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def _collect_elasticsearch_metrics(self) -> Dict[str, Any]:
        """Collect Elasticsearch metrics."""
        metrics = {
            "backend": "elasticsearch",
            "indices": [],
            "total_docs": 0,
            "total_size_bytes": 0,
            "index_count": 0,
            "ingestion_rate": 0,
            "query_rate": 0
        }

        try:
            # Get cluster stats
            response = requests.get(f"{self.backend_url}/_cluster/stats", timeout=10)
            response.raise_for_status()
            cluster_stats = response.json()

            metrics["total_docs"] = cluster_stats.get("indices", {}).get("count", 0)
            metrics["total_size_bytes"] = cluster_stats.get("indices", {}).get("store", {}).get("size_in_bytes", 0)
            metrics["index_count"] = cluster_stats.get("indices", {}).get("count", 0)

            # Get index stats
            response = requests.get(f"{self.backend_url}/_stats", timeout=10)
            response.raise_for_status()
            stats = response.json()

            # Calculate rates
            all_stats = stats.get("_all", {}).get("total", {})
            indexing = all_stats.get("indexing", {})
            search = all_stats.get("search", {})

            metrics["ingestion_rate"] = indexing.get("index_total", 0)
            metrics["query_rate"] = search.get("query_total", 0)

            # Get per-index stats
            for index_name, index_data in stats.get("indices", {}).items():
                if index_name.startswith("."):  # Skip system indices
                    continue

                index_stats = index_data.get("total", {})
                metrics["indices"].append({
                    "name": index_name,
                    "docs": index_stats.get("docs", {}).get("count", 0),
                    "size_bytes": index_stats.get("store", {}).get("size_in_bytes", 0),
                    "indexing_rate": index_stats.get("indexing", {}).get("index_total", 0),
                    "query_rate": index_stats.get("search", {}).get("query_total", 0)
                })

            # Get node stats for performance metrics
            response = requests.get(f"{self.backend_url}/_nodes/stats", timeout=10)
            response.raise_for_status()
            node_stats = response.json()

            nodes = node_stats.get("nodes", {})
            if nodes:
                first_node = list(nodes.values())[0]
                jvm = first_node.get("jvm", {})
                metrics["heap_used_percent"] = jvm.get("mem", {}).get("heap_used_percent", 0)
                metrics["gc_time_ms"] = jvm.get("gc", {}).get("collectors", {}).get("old", {}).get("collection_time_in_millis", 0)

        except Exception as e:
            self.log(f"Failed to collect Elasticsearch metrics: {e}", error=True)

        return metrics

    def _collect_loki_metrics(self) -> Dict[str, Any]:
        """Collect Loki metrics."""
        metrics = {
            "backend": "loki",
            "streams": 0,
            "total_size_bytes": 0,
            "ingestion_rate": 0,
            "query_rate": 0
        }

        try:
            # Get metrics from Loki
            response = requests.get(f"{self.backend_url}/metrics", timeout=10)
            response.raise_for_status()
            metrics_text = response.text

            # Parse Prometheus-style metrics
            for line in metrics_text.split('\n'):
                if line.startswith('#'):
                    continue

                if 'loki_ingester_streams' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        metrics["streams"] = int(float(parts[1]))

                elif 'loki_ingester_chunk_stored_total' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        metrics["total_size_bytes"] = int(float(parts[1]))

                elif 'loki_distributor_lines_received_total' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        metrics["ingestion_rate"] = int(float(parts[1]))

                elif 'loki_query_frontend_queries_total' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        metrics["query_rate"] = int(float(parts[1]))

        except Exception as e:
            self.log(f"Failed to collect Loki metrics: {e}", error=True)

        return metrics

    def _analyze_costs(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current costs."""
        total_size_gb = metrics.get("total_size_bytes", 0) / (1024**3)

        cost_analysis = {
            "storage_gb": total_size_gb,
            "storage_cost_monthly": total_size_gb * self.storage_cost_per_gb,
            "compute_cost_monthly": 0,
            "total_cost_monthly": 0,
            "cost_per_gb": 0,
            "breakdown": {}
        }

        # Compute costs
        if self.backend == "elasticsearch":
            # Assume 3 nodes for redundancy
            hours_per_month = 730
            cost_analysis["compute_cost_monthly"] = self.elasticsearch_compute_cost * 3 * hours_per_month
        elif self.backend == "loki":
            hours_per_month = 730
            cost_analysis["compute_cost_monthly"] = self.loki_compute_cost * hours_per_month

        cost_analysis["total_cost_monthly"] = (
            cost_analysis["storage_cost_monthly"] +
            cost_analysis["compute_cost_monthly"]
        )

        if total_size_gb > 0:
            cost_analysis["cost_per_gb"] = cost_analysis["total_cost_monthly"] / total_size_gb

        # Breakdown by component
        cost_analysis["breakdown"] = {
            "storage": {
                "cost": cost_analysis["storage_cost_monthly"],
                "percentage": cost_analysis["storage_cost_monthly"] / cost_analysis["total_cost_monthly"] * 100
                if cost_analysis["total_cost_monthly"] > 0 else 0
            },
            "compute": {
                "cost": cost_analysis["compute_cost_monthly"],
                "percentage": cost_analysis["compute_cost_monthly"] / cost_analysis["total_cost_monthly"] * 100
                if cost_analysis["total_cost_monthly"] > 0 else 0
            }
        }

        return cost_analysis

    def _recommend_sampling(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recommend sampling strategies."""
        recommendations = []

        total_docs = metrics.get("total_docs", 0)
        ingestion_rate = metrics.get("ingestion_rate", 0)

        if total_docs == 0:
            return recommendations

        # Estimate daily log volume
        daily_logs = ingestion_rate  # This is cumulative, need to calculate rate

        # High volume threshold: > 1M logs/day
        if daily_logs > 1_000_000:
            sampling_rate = min(10, daily_logs / 1_000_000)  # 10% at 10M logs/day

            recommendations.append({
                "type": "sampling",
                "priority": "high",
                "title": "Implement log sampling for high-volume logs",
                "description": f"Current volume: {daily_logs:,.0f} logs/day. Recommend {sampling_rate:.0f}% sampling for INFO logs.",
                "implementation": {
                    "strategy": "level-based",
                    "sample_rate": {
                        "DEBUG": 0,  # Drop all debug
                        "INFO": sampling_rate / 100,
                        "WARN": 1.0,  # Keep all warnings
                        "ERROR": 1.0  # Keep all errors
                    }
                },
                "estimated_reduction": f"{100 - sampling_rate:.0f}%"
            })

        # Check for debug logs (if we have index-level data)
        if self.backend == "elasticsearch" and "indices" in metrics:
            # Estimate debug log percentage (assume 30% are debug if no level filter)
            debug_percentage = 30  # Conservative estimate

            recommendations.append({
                "type": "sampling",
                "priority": "high",
                "title": "Filter debug logs in production",
                "description": f"Estimated {debug_percentage}% of logs are DEBUG level. Drop debug logs in production.",
                "implementation": {
                    "strategy": "drop-debug",
                    "filter": "level != 'DEBUG'"
                },
                "estimated_reduction": f"{debug_percentage}%"
            })

        # Recommend sampling for specific services if possible
        if self.backend == "elasticsearch" and "indices" in metrics:
            large_indices = [
                idx for idx in metrics["indices"]
                if idx["size_bytes"] > metrics["total_size_bytes"] * 0.2  # > 20% of total
            ]

            for idx in large_indices:
                recommendations.append({
                    "type": "sampling",
                    "priority": "medium",
                    "title": f"Sample logs for {idx['name']}",
                    "description": f"{idx['name']} accounts for {idx['size_bytes'] / metrics['total_size_bytes'] * 100:.0f}% of total storage.",
                    "implementation": {
                        "strategy": "tail-sampling",
                        "sample_rate": 0.1,  # 10%
                        "preserve_errors": True
                    },
                    "estimated_reduction": "10-20%"
                })

        return recommendations

    def _validate_retention(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate retention policies."""
        recommendations = []

        # Check if retention is too long
        if self.backend == "elasticsearch" and "indices" in metrics:
            # Check for old indices
            old_indices = []
            now = datetime.utcnow()

            for idx in metrics["indices"]:
                # Try to parse date from index name (format: logs-2025.10.29)
                parts = idx["name"].split("-")
                if len(parts) >= 2:
                    date_str = parts[-1]
                    try:
                        index_date = datetime.strptime(date_str, "%Y.%m.%d")
                        age_days = (now - index_date).days

                        if age_days > 90:
                            old_indices.append({
                                "name": idx["name"],
                                "age_days": age_days,
                                "size_bytes": idx["size_bytes"]
                            })
                    except:
                        pass

            if old_indices:
                total_old_size = sum(idx["size_bytes"] for idx in old_indices)
                recommendations.append({
                    "type": "retention",
                    "priority": "medium",
                    "title": "Delete old indices",
                    "description": f"{len(old_indices)} indices older than 90 days ({total_old_size / (1024**3):.1f} GB).",
                    "implementation": {
                        "action": "delete",
                        "indices": [idx["name"] for idx in old_indices[:5]]  # Show first 5
                    },
                    "estimated_savings": f"${total_old_size / (1024**3) * self.storage_cost_per_gb:.2f}/month"
                })

        # Recommend tiered storage
        if self.backend == "elasticsearch":
            recommendations.append({
                "type": "retention",
                "priority": "high",
                "title": "Implement Index Lifecycle Management (ILM)",
                "description": "Move old data to cheaper storage tiers.",
                "implementation": {
                    "hot_phase": "0-7 days (SSD, full search)",
                    "warm_phase": "7-30 days (HDD, read-only)",
                    "cold_phase": "30-90 days (compressed, frozen)",
                    "delete_phase": "90+ days"
                },
                "estimated_savings": "30-50% storage costs"
            })

        # Loki retention
        elif self.backend == "loki":
            recommendations.append({
                "type": "retention",
                "priority": "medium",
                "title": "Configure Loki retention",
                "description": "Set retention period to automatically delete old data.",
                "implementation": {
                    "config": {
                        "limits_config": {
                            "retention_period": "336h"  # 14 days
                        },
                        "table_manager": {
                            "retention_deletes_enabled": True,
                            "retention_period": "336h"
                        }
                    }
                },
                "estimated_savings": "Depends on current retention"
            })

        return recommendations

    def _analyze_performance(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance metrics."""
        performance = {
            "issues": [],
            "bottlenecks": [],
            "recommendations": []
        }

        if self.backend == "elasticsearch":
            heap_used = metrics.get("heap_used_percent", 0)

            if heap_used > 85:
                performance["issues"].append({
                    "type": "high_heap_usage",
                    "severity": "critical",
                    "value": heap_used,
                    "description": f"Heap usage at {heap_used}% (critical threshold: 85%)"
                })

            elif heap_used > 75:
                performance["issues"].append({
                    "type": "high_heap_usage",
                    "severity": "warning",
                    "value": heap_used,
                    "description": f"Heap usage at {heap_used}% (warning threshold: 75%)"
                })

            # Check GC time
            gc_time = metrics.get("gc_time_ms", 0)
            if gc_time > 10000:  # > 10 seconds cumulative
                performance["issues"].append({
                    "type": "high_gc_time",
                    "severity": "warning",
                    "value": gc_time,
                    "description": f"High GC time: {gc_time}ms"
                })

            # Check query load
            query_rate = metrics.get("query_rate", 0)
            if query_rate > 1000:
                performance["bottlenecks"].append({
                    "type": "high_query_load",
                    "value": query_rate,
                    "description": "High query rate may impact performance"
                })

        elif self.backend == "loki":
            streams = metrics.get("streams", 0)

            # High cardinality warning
            if streams > 10000:
                performance["issues"].append({
                    "type": "high_cardinality",
                    "severity": "warning",
                    "value": streams,
                    "description": f"High number of streams ({streams}). Reduce label cardinality."
                })

        return performance

    def _generate_cost_recommendations(self, cost_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cost optimization recommendations."""
        recommendations = []

        total_cost = cost_analysis.get("total_cost_monthly", 0)
        storage_cost = cost_analysis.get("storage_cost_monthly", 0)

        # High cost warning
        if total_cost > 1000:
            recommendations.append({
                "type": "cost",
                "priority": "high",
                "title": "High monthly costs",
                "description": f"Total cost: ${total_cost:.2f}/month. Consider optimization strategies.",
                "implementation": {
                    "actions": [
                        "Implement sampling (reduce volume by 50%)",
                        "Reduce retention (90 days → 30 days)",
                        "Use Loki instead of Elasticsearch (70% cheaper)",
                        "Archive to S3 for long-term storage"
                    ]
                },
                "estimated_savings": f"${total_cost * 0.5:.2f}/month"
            })

        # Storage-heavy warning
        if storage_cost / total_cost > 0.4:  # > 40% storage
            recommendations.append({
                "type": "cost",
                "priority": "medium",
                "title": "Storage costs are high",
                "description": f"Storage accounts for {storage_cost / total_cost * 100:.0f}% of costs.",
                "implementation": {
                    "actions": [
                        "Enable compression",
                        "Implement ILM with warm/cold tiers",
                        "Reduce retention period",
                        "Archive to object storage"
                    ]
                },
                "estimated_savings": f"${storage_cost * 0.3:.2f}/month"
            })

        # Consider Loki
        if self.backend == "elasticsearch" and total_cost > 500:
            loki_cost = total_cost * 0.3  # Loki is ~70% cheaper
            recommendations.append({
                "type": "cost",
                "priority": "low",
                "title": "Consider migrating to Loki",
                "description": "Loki offers 70% cost reduction for simple use cases.",
                "implementation": {
                    "action": "Evaluate Loki for cost savings",
                    "trade_offs": [
                        "Less powerful query language",
                        "Label-based indexing only",
                        "Good for simple filtering"
                    ]
                },
                "estimated_savings": f"${total_cost - loki_cost:.2f}/month"
            })

        return recommendations

    def _generate_performance_recommendations(
        self,
        performance: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate performance recommendations."""
        recommendations = []

        for issue in performance.get("issues", []):
            if issue["type"] == "high_heap_usage":
                recommendations.append({
                    "type": "performance",
                    "priority": "high" if issue["severity"] == "critical" else "medium",
                    "title": "Reduce heap usage",
                    "description": issue["description"],
                    "implementation": {
                        "actions": [
                            "Increase heap size (max 50% of RAM, max 32GB)",
                            "Reduce shard count",
                            "Disable unnecessary features",
                            "Optimize queries"
                        ]
                    }
                })

            elif issue["type"] == "high_gc_time":
                recommendations.append({
                    "type": "performance",
                    "priority": "medium",
                    "title": "Reduce GC pressure",
                    "description": issue["description"],
                    "implementation": {
                        "actions": [
                            "Increase heap size",
                            "Tune GC settings",
                            "Reduce indexing rate"
                        ]
                    }
                })

            elif issue["type"] == "high_cardinality":
                recommendations.append({
                    "type": "performance",
                    "priority": "high",
                    "title": "Reduce label cardinality",
                    "description": issue["description"],
                    "implementation": {
                        "actions": [
                            "Remove high-cardinality labels (user_id, trace_id)",
                            "Use static labels only (service, environment)",
                            "Move dynamic data to log message"
                        ]
                    }
                })

        for bottleneck in performance.get("bottlenecks", []):
            if bottleneck["type"] == "high_query_load":
                recommendations.append({
                    "type": "performance",
                    "priority": "medium",
                    "title": "Optimize query load",
                    "description": bottleneck["description"],
                    "implementation": {
                        "actions": [
                            "Add query caching",
                            "Optimize slow queries",
                            "Add more nodes",
                            "Use index patterns"
                        ]
                    }
                })

        return recommendations

    def _calculate_savings(
        self,
        metrics: Dict[str, Any],
        cost_analysis: Dict[str, Any],
        recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate estimated savings from recommendations."""
        current_cost = cost_analysis.get("total_cost_monthly", 0)
        potential_savings = 0

        for rec in recommendations:
            if rec["type"] == "sampling" and "estimated_reduction" in rec:
                reduction_pct = float(rec["estimated_reduction"].rstrip('%')) / 100
                savings = current_cost * reduction_pct * 0.5  # Conservative estimate
                potential_savings += savings

            elif rec["type"] == "cost" and "estimated_savings" in rec:
                savings_str = rec["estimated_savings"]
                if "/month" in savings_str:
                    savings = float(savings_str.replace("$", "").replace("/month", ""))
                    potential_savings += savings

        return {
            "current_cost_monthly": current_cost,
            "potential_savings_monthly": potential_savings,
            "optimized_cost_monthly": max(0, current_cost - potential_savings),
            "savings_percentage": (potential_savings / current_cost * 100) if current_cost > 0 else 0
        }

    def log(self, message: str, error: bool = False) -> None:
        """Log a message."""
        if self.verbose or error:
            prefix = "ERROR" if error else "INFO"
            print(f"[{prefix}] {message}", file=sys.stderr if error else sys.stdout)


def generate_report(result: OptimizationResult, format: str = "text") -> str:
    """Generate optimization report."""
    if format == "json":
        return json.dumps(asdict(result), indent=2, default=str)

    # Text report
    lines = []
    lines.append("=" * 80)
    lines.append("LOG PIPELINE OPTIMIZATION REPORT")
    lines.append("=" * 80)
    lines.append("")

    lines.append(f"Backend: {result.backend}")
    lines.append("")

    # Current Metrics
    lines.append("-" * 80)
    lines.append("CURRENT METRICS")
    lines.append("-" * 80)
    for key, value in result.current_metrics.items():
        if key != "indices":  # Skip detailed index list
            if isinstance(value, float):
                lines.append(f"{key}: {value:.2f}")
            elif isinstance(value, int) and value > 1000:
                lines.append(f"{key}: {value:,}")
            else:
                lines.append(f"{key}: {value}")

    # Cost Analysis
    if result.cost_analysis:
        lines.append("")
        lines.append("-" * 80)
        lines.append("COST ANALYSIS")
        lines.append("-" * 80)
        ca = result.cost_analysis
        lines.append(f"Storage: {ca.get('storage_gb', 0):.2f} GB")
        lines.append(f"Storage Cost: ${ca.get('storage_cost_monthly', 0):.2f}/month")
        lines.append(f"Compute Cost: ${ca.get('compute_cost_monthly', 0):.2f}/month")
        lines.append(f"Total Cost: ${ca.get('total_cost_monthly', 0):.2f}/month")
        lines.append(f"Cost per GB: ${ca.get('cost_per_gb', 0):.2f}")

    # Performance Analysis
    if result.performance_analysis:
        pa = result.performance_analysis
        if pa.get("issues"):
            lines.append("")
            lines.append("-" * 80)
            lines.append("PERFORMANCE ISSUES")
            lines.append("-" * 80)
            for issue in pa["issues"]:
                severity = issue.get("severity", "info").upper()
                lines.append(f"[{severity}] {issue['description']}")

    # Recommendations
    if result.recommendations:
        lines.append("")
        lines.append("-" * 80)
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)

        # Group by priority
        by_priority = defaultdict(list)
        for rec in result.recommendations:
            by_priority[rec.get("priority", "low")].append(rec)

        for priority in ["high", "medium", "low"]:
            recs = by_priority.get(priority, [])
            if not recs:
                continue

            lines.append(f"\n{priority.upper()} PRIORITY:")
            for i, rec in enumerate(recs, 1):
                lines.append(f"\n{i}. {rec['title']}")
                lines.append(f"   {rec['description']}")

                if "implementation" in rec:
                    impl = rec["implementation"]
                    if isinstance(impl, dict):
                        if "actions" in impl:
                            lines.append("   Actions:")
                            for action in impl["actions"]:
                                lines.append(f"   - {action}")
                        elif "strategy" in impl:
                            lines.append(f"   Strategy: {impl['strategy']}")

                if "estimated_savings" in rec:
                    lines.append(f"   Estimated Savings: {rec['estimated_savings']}")

    # Estimated Savings
    if result.estimated_savings:
        lines.append("")
        lines.append("-" * 80)
        lines.append("ESTIMATED SAVINGS")
        lines.append("-" * 80)
        es = result.estimated_savings
        lines.append(f"Current Cost: ${es.get('current_cost_monthly', 0):.2f}/month")
        lines.append(f"Potential Savings: ${es.get('potential_savings_monthly', 0):.2f}/month ({es.get('savings_percentage', 0):.1f}%)")
        lines.append(f"Optimized Cost: ${es.get('optimized_cost_monthly', 0):.2f}/month")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Optimize log pipeline for cost and performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze costs
  optimize_log_pipeline.py --backend elasticsearch --analyze-costs

  # Recommend sampling strategies
  optimize_log_pipeline.py --backend elasticsearch --recommend-sampling

  # Validate retention policies
  optimize_log_pipeline.py --backend elasticsearch --validate-retention

  # Full optimization analysis
  optimize_log_pipeline.py --backend elasticsearch \\
    --analyze-costs --recommend-sampling --validate-retention

  # JSON output
  optimize_log_pipeline.py --backend elasticsearch --json
        """
    )

    parser.add_argument("--backend", required=True, choices=["elasticsearch", "loki"],
                        help="Log backend")
    parser.add_argument("--backend-url",
                        help="Backend URL (default: http://localhost:9200 for ES, http://localhost:3100 for Loki)")
    parser.add_argument("--analyze-costs", action="store_true",
                        help="Analyze costs")
    parser.add_argument("--recommend-sampling", action="store_true",
                        help="Recommend sampling strategies")
    parser.add_argument("--validate-retention", action="store_true",
                        help="Validate retention policies")
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
    if not (args.analyze_costs or args.recommend_sampling or args.validate_retention):
        args.analyze_costs = True
        args.recommend_sampling = True
        args.validate_retention = True

    # Create optimizer
    optimizer = LogPipelineOptimizer(
        backend=args.backend,
        backend_url=args.backend_url,
        verbose=args.verbose
    )

    # Run optimization
    try:
        result = optimizer.optimize(
            analyze_costs=args.analyze_costs,
            recommend_sampling=args.recommend_sampling,
            validate_retention=args.validate_retention
        )

        # Generate report
        report = generate_report(result, format="json" if args.json else "text")
        print(report)

        sys.exit(0)

    except Exception as e:
        print(f"Optimization failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
