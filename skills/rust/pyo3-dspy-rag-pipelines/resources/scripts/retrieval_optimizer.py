#!/usr/bin/env python3
"""
Retrieval Optimizer - Grid search optimization for RAG retrieval parameters.

Optimizes top-k, reranking threshold, chunk size, and overlap with evaluation metrics.
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import itertools

import click
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class RetrievalConfig:
    """Retrieval configuration parameters."""
    top_k: int
    rerank_threshold: float
    chunk_size: int
    chunk_overlap: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetrievalConfig':
        return cls(**data)


@dataclass
class RetrievalMetrics:
    """Retrieval evaluation metrics."""
    precision_at_k: float
    recall_at_k: float
    mrr: float
    avg_latency_ms: float
    estimated_cost: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RetrieverEvaluator:
    """Evaluate retrieval quality metrics."""

    def __init__(self, cost_per_1k_tokens: float = 0.0001):
        self.cost_per_1k_tokens = cost_per_1k_tokens

    def precision_at_k(self, retrieved: List[str], relevant: List[str], k: int) -> float:
        """Calculate Precision@k."""
        if not retrieved or k == 0:
            return 0.0

        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)
        hits = sum(1 for doc_id in retrieved_k if doc_id in relevant_set)
        return hits / k

    def recall_at_k(self, retrieved: List[str], relevant: List[str], k: int) -> float:
        """Calculate Recall@k."""
        if not relevant:
            return 0.0

        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)
        hits = sum(1 for doc_id in retrieved_k if doc_id in relevant_set)
        return hits / len(relevant)

    def mean_reciprocal_rank(self, retrieved: List[str], relevant: List[str]) -> float:
        """Calculate Mean Reciprocal Rank (MRR)."""
        relevant_set = set(relevant)
        for rank, doc_id in enumerate(retrieved, start=1):
            if doc_id in relevant_set:
                return 1.0 / rank
        return 0.0

    def estimate_cost(self, config: RetrievalConfig, num_queries: int,
                     avg_doc_tokens: int = 500) -> float:
        """Estimate retrieval cost based on configuration."""
        tokens_per_query = config.top_k * avg_doc_tokens
        total_tokens = tokens_per_query * num_queries
        return (total_tokens / 1000) * self.cost_per_1k_tokens

    def evaluate_query(self, retrieved: List[str], relevant: List[str],
                      config: RetrievalConfig, latency_ms: float = 100.0) -> RetrievalMetrics:
        """Evaluate metrics for a single query."""
        return RetrievalMetrics(
            precision_at_k=self.precision_at_k(retrieved, relevant, config.top_k),
            recall_at_k=self.recall_at_k(retrieved, relevant, config.top_k),
            mrr=self.mean_reciprocal_rank(retrieved, relevant),
            avg_latency_ms=latency_ms,
            estimated_cost=self.estimate_cost(config, num_queries=1)
        )

    def evaluate_batch(self, results: List[Dict[str, List[str]]],
                      config: RetrievalConfig) -> RetrievalMetrics:
        """Evaluate metrics across multiple queries."""
        metrics_list = []

        for result in results:
            retrieved = result.get('retrieved', [])
            relevant = result.get('relevant', [])
            latency = result.get('latency_ms', 100.0)

            metrics = self.evaluate_query(retrieved, relevant, config, latency)
            metrics_list.append(metrics)

        # Aggregate metrics
        avg_precision = np.mean([m.precision_at_k for m in metrics_list])
        avg_recall = np.mean([m.recall_at_k for m in metrics_list])
        avg_mrr = np.mean([m.mrr for m in metrics_list])
        avg_latency = np.mean([m.avg_latency_ms for m in metrics_list])
        total_cost = sum(m.estimated_cost for m in metrics_list)

        return RetrievalMetrics(
            precision_at_k=avg_precision,
            recall_at_k=avg_recall,
            mrr=avg_mrr,
            avg_latency_ms=avg_latency,
            estimated_cost=total_cost
        )


class GridSearchOptimizer:
    """Grid search over retrieval parameters."""

    def __init__(self, evaluator: RetrieverEvaluator):
        self.evaluator = evaluator

    def generate_grid(self, param_ranges: Dict[str, List[Any]]) -> List[RetrievalConfig]:
        """Generate parameter grid from ranges."""
        keys = ['top_k', 'rerank_threshold', 'chunk_size', 'chunk_overlap']

        # Use provided ranges or defaults
        top_k_values = param_ranges.get('top_k', [3, 5, 10, 20])
        rerank_values = param_ranges.get('rerank_threshold', [0.5, 0.6, 0.7, 0.8])
        chunk_sizes = param_ranges.get('chunk_size', [256, 512, 1024])
        chunk_overlaps = param_ranges.get('chunk_overlap', [0, 64, 128])

        configs = []
        for top_k, threshold, chunk_size, overlap in itertools.product(
            top_k_values, rerank_values, chunk_sizes, chunk_overlaps
        ):
            # Validate overlap < chunk_size
            if overlap < chunk_size:
                configs.append(RetrievalConfig(top_k, threshold, chunk_size, overlap))

        return configs

    def optimize(self, test_data: List[Dict[str, List[str]]],
                param_ranges: Dict[str, List[Any]],
                metric: str = 'mrr') -> Tuple[RetrievalConfig, RetrievalMetrics, pd.DataFrame]:
        """
        Run grid search optimization.

        Args:
            test_data: List of {retrieved, relevant, latency_ms}
            param_ranges: Parameter ranges for grid
            metric: Optimization metric (mrr, precision_at_k, recall_at_k)

        Returns:
            (best_config, best_metrics, results_df)
        """
        configs = self.generate_grid(param_ranges)
        logger.info(f"Testing {len(configs)} configurations")

        results = []
        best_score = -1.0
        best_config = None
        best_metrics = None

        for config in tqdm(configs, desc="Grid search"):
            metrics = self.evaluator.evaluate_batch(test_data, config)

            # Get optimization target
            score = getattr(metrics, metric)

            results.append({
                'top_k': config.top_k,
                'rerank_threshold': config.rerank_threshold,
                'chunk_size': config.chunk_size,
                'chunk_overlap': config.chunk_overlap,
                'precision_at_k': metrics.precision_at_k,
                'recall_at_k': metrics.recall_at_k,
                'mrr': metrics.mrr,
                'latency_ms': metrics.avg_latency_ms,
                'cost': metrics.estimated_cost
            })

            if score > best_score:
                best_score = score
                best_config = config
                best_metrics = metrics

        results_df = pd.DataFrame(results)
        logger.info(f"Best {metric}: {best_score:.4f}")

        return best_config, best_metrics, results_df


class CostQualityAnalyzer:
    """Analyze cost-quality tradeoffs."""

    def __init__(self):
        pass

    def pareto_frontier(self, results_df: pd.DataFrame,
                       quality_col: str = 'mrr',
                       cost_col: str = 'cost') -> pd.DataFrame:
        """Find Pareto frontier for cost-quality tradeoff."""
        pareto_points = []

        for idx, row in results_df.iterrows():
            is_pareto = True
            for _, other in results_df.iterrows():
                # Check if other point dominates this point
                if (other[quality_col] >= row[quality_col] and
                    other[cost_col] <= row[cost_col] and
                    (other[quality_col] > row[quality_col] or
                     other[cost_col] < row[cost_col])):
                    is_pareto = False
                    break

            if is_pareto:
                pareto_points.append(row)

        return pd.DataFrame(pareto_points)

    def recommend_config(self, results_df: pd.DataFrame,
                        budget: float,
                        quality_target: float,
                        quality_metric: str = 'mrr') -> Optional[Dict[str, Any]]:
        """Recommend configuration based on budget and quality constraints."""
        # Filter by budget
        within_budget = results_df[results_df['cost'] <= budget]

        if within_budget.empty:
            logger.warning("No configurations within budget")
            return None

        # Filter by quality target
        meets_quality = within_budget[within_budget[quality_metric] >= quality_target]

        if meets_quality.empty:
            # Return best quality within budget
            best = within_budget.loc[within_budget[quality_metric].idxmax()]
            logger.warning(f"No config meets quality target. Best available: {best[quality_metric]:.4f}")
            return best.to_dict()

        # Return lowest cost that meets quality
        best = meets_quality.loc[meets_quality['cost'].idxmin()]
        return best.to_dict()

    def visualize_tradeoff(self, results_df: pd.DataFrame,
                          output_path: Path,
                          quality_metric: str = 'mrr'):
        """Visualize cost-quality tradeoff with Pareto frontier."""
        pareto = self.pareto_frontier(results_df, quality_col=quality_metric)

        fig, ax = plt.subplots(figsize=(10, 6))

        # All points
        ax.scatter(results_df['cost'], results_df[quality_metric],
                  alpha=0.5, label='All configs', s=50)

        # Pareto frontier
        pareto_sorted = pareto.sort_values('cost')
        ax.plot(pareto_sorted['cost'], pareto_sorted[quality_metric],
               'r--', linewidth=2, label='Pareto frontier')
        ax.scatter(pareto['cost'], pareto[quality_metric],
                  color='red', s=100, zorder=5, label='Pareto optimal')

        ax.set_xlabel('Estimated Cost ($)')
        ax.set_ylabel(quality_metric.upper())
        ax.set_title('Cost-Quality Tradeoff Analysis')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        logger.info(f"Saved tradeoff visualization to {output_path}")


# CLI Commands

@click.group()
def cli():
    """Retrieval Optimizer - Optimize RAG retrieval parameters."""
    pass


@cli.command()
@click.option('--queries', type=click.Path(exists=True), required=True,
              help='Path to queries JSON file')
@click.option('--param-ranges', type=click.Path(exists=True),
              help='Path to parameter ranges JSON')
@click.option('--metric', default='mrr',
              type=click.Choice(['mrr', 'precision_at_k', 'recall_at_k']),
              help='Optimization metric')
@click.option('--output', type=click.Path(), default='optimization_results.json',
              help='Output path for results')
def optimize(queries: str, param_ranges: Optional[str], metric: str, output: str):
    """Run grid search optimization."""
    # Load test data
    with open(queries) as f:
        test_data = json.load(f)

    # Load parameter ranges
    if param_ranges:
        with open(param_ranges) as f:
            ranges = json.load(f)
    else:
        ranges = {}  # Use defaults

    # Run optimization
    evaluator = RetrieverEvaluator()
    optimizer = GridSearchOptimizer(evaluator)

    best_config, best_metrics, results_df = optimizer.optimize(test_data, ranges, metric)

    # Save results
    output_path = Path(output)
    results = {
        'best_config': best_config.to_dict(),
        'best_metrics': best_metrics.to_dict(),
        'optimization_metric': metric,
        'num_configs_tested': len(results_df)
    }

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Save detailed results
    csv_path = output_path.with_suffix('.csv')
    results_df.to_csv(csv_path, index=False)

    click.echo(f"Best config: {best_config}")
    click.echo(f"Best {metric}: {getattr(best_metrics, metric):.4f}")
    click.echo(f"Results saved to {output_path}")


@cli.command()
@click.option('--config', type=click.Path(exists=True), required=True,
              help='Path to retrieval config JSON')
@click.option('--testset', type=click.Path(exists=True), required=True,
              help='Path to test set JSON')
@click.option('--output', type=click.Path(), default='evaluation_results.json',
              help='Output path for results')
def evaluate(config: str, testset: str, output: str):
    """Evaluate a specific configuration."""
    # Load config
    with open(config) as f:
        config_dict = json.load(f)

    retrieval_config = RetrievalConfig.from_dict(config_dict)

    # Load test data
    with open(testset) as f:
        test_data = json.load(f)

    # Evaluate
    evaluator = RetrieverEvaluator()
    metrics = evaluator.evaluate_batch(test_data, retrieval_config)

    # Save results
    results = {
        'config': retrieval_config.to_dict(),
        'metrics': metrics.to_dict()
    }

    with open(output, 'w') as f:
        json.dump(results, f, indent=2)

    click.echo(f"Evaluation results:")
    click.echo(f"  Precision@k: {metrics.precision_at_k:.4f}")
    click.echo(f"  Recall@k: {metrics.recall_at_k:.4f}")
    click.echo(f"  MRR: {metrics.mrr:.4f}")
    click.echo(f"  Cost: ${metrics.estimated_cost:.6f}")
    click.echo(f"Results saved to {output}")


@cli.command()
@click.option('--results', type=click.Path(exists=True), required=True,
              help='Path to optimization results CSV')
@click.option('--budget', type=float, required=True,
              help='Cost budget constraint')
@click.option('--quality-target', type=float, required=True,
              help='Minimum quality target')
@click.option('--quality-metric', default='mrr',
              type=click.Choice(['mrr', 'precision_at_k', 'recall_at_k']),
              help='Quality metric to optimize')
@click.option('--output', type=click.Path(), default='recommended_config.json',
              help='Output path for recommendation')
def recommend(results: str, budget: float, quality_target: float,
              quality_metric: str, output: str):
    """Recommend configuration based on constraints."""
    results_df = pd.read_csv(results)

    analyzer = CostQualityAnalyzer()
    recommendation = analyzer.recommend_config(
        results_df, budget, quality_target, quality_metric
    )

    if recommendation:
        with open(output, 'w') as f:
            json.dump(recommendation, f, indent=2)

        click.echo(f"Recommended configuration:")
        click.echo(f"  top_k: {recommendation['top_k']}")
        click.echo(f"  rerank_threshold: {recommendation['rerank_threshold']}")
        click.echo(f"  chunk_size: {recommendation['chunk_size']}")
        click.echo(f"  chunk_overlap: {recommendation['chunk_overlap']}")
        click.echo(f"  {quality_metric}: {recommendation[quality_metric]:.4f}")
        click.echo(f"  cost: ${recommendation['cost']:.6f}")
        click.echo(f"Saved to {output}")
    else:
        click.echo("No configuration meets constraints", err=True)


@cli.command()
@click.option('--configs', required=True,
              help='Comma-separated paths to config JSONs')
@click.option('--testset', type=click.Path(exists=True), required=True,
              help='Path to test set JSON')
@click.option('--output', type=click.Path(), default='comparison_results.json',
              help='Output path for comparison')
def compare(configs: str, testset: str, output: str):
    """Compare multiple configurations."""
    config_paths = [p.strip() for p in configs.split(',')]

    # Load test data
    with open(testset) as f:
        test_data = json.load(f)

    evaluator = RetrieverEvaluator()
    results = []

    for config_path in config_paths:
        with open(config_path) as f:
            config_dict = json.load(f)

        retrieval_config = RetrievalConfig.from_dict(config_dict)
        metrics = evaluator.evaluate_batch(test_data, retrieval_config)

        results.append({
            'config_path': config_path,
            'config': retrieval_config.to_dict(),
            'metrics': metrics.to_dict()
        })

    # Save comparison
    with open(output, 'w') as f:
        json.dump(results, f, indent=2)

    # Display comparison
    click.echo("\nConfiguration Comparison:")
    click.echo("-" * 80)
    for result in results:
        click.echo(f"\n{result['config_path']}:")
        metrics = result['metrics']
        click.echo(f"  Precision@k: {metrics['precision_at_k']:.4f}")
        click.echo(f"  Recall@k: {metrics['recall_at_k']:.4f}")
        click.echo(f"  MRR: {metrics['mrr']:.4f}")
        click.echo(f"  Cost: ${metrics['estimated_cost']:.6f}")

    click.echo(f"\nComparison saved to {output}")


if __name__ == '__main__':
    cli()
