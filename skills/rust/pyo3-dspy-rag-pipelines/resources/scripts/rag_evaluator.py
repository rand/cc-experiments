#!/usr/bin/env python3
"""
RAG Pipeline Evaluator

Comprehensive evaluation framework for RAG pipelines with retrieval and generation metrics.
Supports comparative analysis, cost tracking, and detailed reporting.

Usage:
    python rag_evaluator.py evaluate --pipeline pipeline.py --testset test.json
    python rag_evaluator.py compare --pipelines pipe1.py,pipe2.py --testset test.json
    python rag_evaluator.py report --results results.json --format html
    python rag_evaluator.py analyze --results results.json --metric retrieval_precision
"""

import argparse
import json
import time
import statistics
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import importlib.util
import sys


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval quality."""
    precision: float
    recall: float
    f1_score: float
    mrr: float  # Mean Reciprocal Rank
    ndcg: float  # Normalized Discounted Cumulative Gain
    avg_latency_ms: float


@dataclass
class GenerationMetrics:
    """Metrics for generation quality."""
    bleu_score: float
    rouge_1: float
    rouge_2: float
    rouge_l: float
    answer_relevance: float
    faithfulness: float
    avg_latency_ms: float


@dataclass
class RAGMetrics:
    """Combined RAG evaluation metrics."""
    retrieval: RetrievalMetrics
    generation: GenerationMetrics
    end_to_end_latency_ms: float
    cost_usd: float
    timestamp: str


@dataclass
class TestCase:
    """Individual test case for RAG evaluation."""
    query: str
    expected_answer: str
    relevant_doc_ids: List[str]
    context: Optional[Dict[str, Any]] = None


class RetrievalEvaluator:
    """Evaluator for retrieval metrics."""

    @staticmethod
    def calculate_precision(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
        """Calculate precision: relevant retrieved / total retrieved."""
        if not retrieved_ids:
            return 0.0
        relevant_retrieved = set(retrieved_ids) & set(relevant_ids)
        return len(relevant_retrieved) / len(retrieved_ids)

    @staticmethod
    def calculate_recall(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
        """Calculate recall: relevant retrieved / total relevant."""
        if not relevant_ids:
            return 0.0
        relevant_retrieved = set(retrieved_ids) & set(relevant_ids)
        return len(relevant_retrieved) / len(relevant_ids)

    @staticmethod
    def calculate_f1(precision: float, recall: float) -> float:
        """Calculate F1 score from precision and recall."""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    @staticmethod
    def calculate_mrr(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
        """Calculate Mean Reciprocal Rank."""
        relevant_set = set(relevant_ids)
        for idx, doc_id in enumerate(retrieved_ids, 1):
            if doc_id in relevant_set:
                return 1.0 / idx
        return 0.0

    @staticmethod
    def calculate_ndcg(retrieved_ids: List[str], relevant_ids: List[str], k: int = 10) -> float:
        """Calculate Normalized Discounted Cumulative Gain at k."""
        relevant_set = set(relevant_ids)

        # DCG
        dcg = 0.0
        for idx, doc_id in enumerate(retrieved_ids[:k], 1):
            relevance = 1.0 if doc_id in relevant_set else 0.0
            dcg += relevance / (idx.bit_length())  # log2(idx + 1)

        # IDCG (ideal DCG)
        idcg = sum(1.0 / (i + 1).bit_length() for i in range(min(len(relevant_ids), k)))

        return dcg / idcg if idcg > 0 else 0.0

    @classmethod
    def evaluate(cls, retrieved_ids: List[str], relevant_ids: List[str], latency_ms: float) -> RetrievalMetrics:
        """Evaluate retrieval results."""
        precision = cls.calculate_precision(retrieved_ids, relevant_ids)
        recall = cls.calculate_recall(retrieved_ids, relevant_ids)
        f1 = cls.calculate_f1(precision, recall)
        mrr = cls.calculate_mrr(retrieved_ids, relevant_ids)
        ndcg = cls.calculate_ndcg(retrieved_ids, relevant_ids)

        return RetrievalMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1,
            mrr=mrr,
            ndcg=ndcg,
            avg_latency_ms=latency_ms
        )


class GenerationEvaluator:
    """Evaluator for generation metrics."""

    @staticmethod
    def calculate_bleu(generated: str, reference: str, n: int = 4) -> float:
        """Calculate BLEU score (simplified n-gram overlap)."""
        gen_tokens = generated.lower().split()
        ref_tokens = reference.lower().split()

        if not gen_tokens or not ref_tokens:
            return 0.0

        # Simplified BLEU: unigram precision
        matches = sum(1 for token in gen_tokens if token in ref_tokens)
        return matches / len(gen_tokens)

    @staticmethod
    def calculate_rouge(generated: str, reference: str) -> Tuple[float, float, float]:
        """Calculate ROUGE-1, ROUGE-2, ROUGE-L scores."""
        gen_tokens = generated.lower().split()
        ref_tokens = reference.lower().split()

        if not gen_tokens or not ref_tokens:
            return 0.0, 0.0, 0.0

        # ROUGE-1: unigram overlap
        gen_unigrams = set(gen_tokens)
        ref_unigrams = set(ref_tokens)
        rouge_1 = len(gen_unigrams & ref_unigrams) / len(ref_unigrams)

        # ROUGE-2: bigram overlap
        gen_bigrams = set(zip(gen_tokens[:-1], gen_tokens[1:]))
        ref_bigrams = set(zip(ref_tokens[:-1], ref_tokens[1:]))
        rouge_2 = len(gen_bigrams & ref_bigrams) / len(ref_bigrams) if ref_bigrams else 0.0

        # ROUGE-L: longest common subsequence (simplified)
        lcs_length = GenerationEvaluator._lcs_length(gen_tokens, ref_tokens)
        rouge_l = lcs_length / len(ref_tokens)

        return rouge_1, rouge_2, rouge_l

    @staticmethod
    def _lcs_length(seq1: List[str], seq2: List[str]) -> int:
        """Calculate longest common subsequence length."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        return dp[m][n]

    @staticmethod
    def calculate_answer_relevance(generated: str, query: str) -> float:
        """Calculate answer relevance to query (token overlap)."""
        gen_tokens = set(generated.lower().split())
        query_tokens = set(query.lower().split())

        if not query_tokens:
            return 0.0

        overlap = gen_tokens & query_tokens
        return len(overlap) / len(query_tokens)

    @staticmethod
    def calculate_faithfulness(generated: str, context: str) -> float:
        """Calculate faithfulness to retrieved context (token overlap)."""
        gen_tokens = set(generated.lower().split())
        ctx_tokens = set(context.lower().split())

        if not gen_tokens:
            return 0.0

        overlap = gen_tokens & ctx_tokens
        return len(overlap) / len(gen_tokens)

    @classmethod
    def evaluate(cls, generated: str, reference: str, query: str, context: str, latency_ms: float) -> GenerationMetrics:
        """Evaluate generation results."""
        bleu = cls.calculate_bleu(generated, reference)
        rouge_1, rouge_2, rouge_l = cls.calculate_rouge(generated, reference)
        relevance = cls.calculate_answer_relevance(generated, query)
        faithfulness = cls.calculate_faithfulness(generated, context)

        return GenerationMetrics(
            bleu_score=bleu,
            rouge_1=rouge_1,
            rouge_2=rouge_2,
            rouge_l=rouge_l,
            answer_relevance=relevance,
            faithfulness=faithfulness,
            avg_latency_ms=latency_ms
        )


class RAGPipelineEvaluator:
    """End-to-end RAG pipeline evaluator."""

    def __init__(self, pipeline_module_path: str):
        """Load RAG pipeline from module."""
        self.pipeline = self._load_pipeline(pipeline_module_path)
        self.pipeline_name = Path(pipeline_module_path).stem

    def _load_pipeline(self, module_path: str) -> Any:
        """Dynamically load pipeline module."""
        spec = importlib.util.spec_from_file_location("pipeline", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load pipeline from {module_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules["pipeline"] = module
        spec.loader.exec_module(module)

        # Assume pipeline has a 'run' function or a Pipeline class
        if hasattr(module, 'Pipeline'):
            return module.Pipeline()
        elif hasattr(module, 'run'):
            return module
        else:
            raise AttributeError("Pipeline module must have 'Pipeline' class or 'run' function")

    def evaluate_testset(self, testset_path: str) -> RAGMetrics:
        """Evaluate pipeline on a testset."""
        with open(testset_path) as f:
            test_cases = [TestCase(**case) for case in json.load(f)]

        retrieval_results = []
        generation_results = []
        latencies = []
        costs = []

        for test_case in test_cases:
            start_time = time.perf_counter()

            # Run pipeline
            result = self._run_pipeline(test_case)

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

            # Evaluate retrieval
            retrieval_latency = result.get('retrieval_latency_ms', latency_ms * 0.3)
            retrieval_metrics = RetrievalEvaluator.evaluate(
                result['retrieved_doc_ids'],
                test_case.relevant_doc_ids,
                retrieval_latency
            )
            retrieval_results.append(retrieval_metrics)

            # Evaluate generation
            generation_latency = result.get('generation_latency_ms', latency_ms * 0.7)
            generation_metrics = GenerationEvaluator.evaluate(
                result['generated_answer'],
                test_case.expected_answer,
                test_case.query,
                result['retrieved_context'],
                generation_latency
            )
            generation_results.append(generation_metrics)

            # Track cost
            costs.append(result.get('cost_usd', 0.0))

        # Aggregate metrics
        avg_retrieval = self._aggregate_retrieval_metrics(retrieval_results)
        avg_generation = self._aggregate_generation_metrics(generation_results)

        return RAGMetrics(
            retrieval=avg_retrieval,
            generation=avg_generation,
            end_to_end_latency_ms=statistics.mean(latencies),
            cost_usd=sum(costs),
            timestamp=datetime.now().isoformat()
        )

    def _run_pipeline(self, test_case: TestCase) -> Dict[str, Any]:
        """Run pipeline on a single test case."""
        if hasattr(self.pipeline, 'run'):
            return self.pipeline.run(test_case.query, test_case.context)
        elif hasattr(self.pipeline, '__call__'):
            return self.pipeline(test_case.query, test_case.context)
        else:
            raise AttributeError("Pipeline must have 'run' method or be callable")

    def _aggregate_retrieval_metrics(self, results: List[RetrievalMetrics]) -> RetrievalMetrics:
        """Aggregate retrieval metrics across test cases."""
        return RetrievalMetrics(
            precision=statistics.mean(r.precision for r in results),
            recall=statistics.mean(r.recall for r in results),
            f1_score=statistics.mean(r.f1_score for r in results),
            mrr=statistics.mean(r.mrr for r in results),
            ndcg=statistics.mean(r.ndcg for r in results),
            avg_latency_ms=statistics.mean(r.avg_latency_ms for r in results)
        )

    def _aggregate_generation_metrics(self, results: List[GenerationMetrics]) -> GenerationMetrics:
        """Aggregate generation metrics across test cases."""
        return GenerationMetrics(
            bleu_score=statistics.mean(r.bleu_score for r in results),
            rouge_1=statistics.mean(r.rouge_1 for r in results),
            rouge_2=statistics.mean(r.rouge_2 for r in results),
            rouge_l=statistics.mean(r.rouge_l for r in results),
            answer_relevance=statistics.mean(r.answer_relevance for r in results),
            faithfulness=statistics.mean(r.faithfulness for r in results),
            avg_latency_ms=statistics.mean(r.avg_latency_ms for r in results)
        )


class ComparativeAnalyzer:
    """Compare multiple RAG pipeline configurations."""

    @staticmethod
    def compare_pipelines(results: Dict[str, RAGMetrics]) -> Dict[str, Any]:
        """Compare multiple pipeline results."""
        comparison = {
            'pipelines': list(results.keys()),
            'best_retrieval_precision': max(results.items(), key=lambda x: x[1].retrieval.precision),
            'best_retrieval_recall': max(results.items(), key=lambda x: x[1].retrieval.recall),
            'best_generation_bleu': max(results.items(), key=lambda x: x[1].generation.bleu_score),
            'fastest_pipeline': min(results.items(), key=lambda x: x[1].end_to_end_latency_ms),
            'cheapest_pipeline': min(results.items(), key=lambda x: x[1].cost_usd),
            'detailed_comparison': {
                name: asdict(metrics) for name, metrics in results.items()
            }
        }
        return comparison

    @staticmethod
    def generate_html_report(comparison: Dict[str, Any], output_path: str):
        """Generate HTML comparison report."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>RAG Pipeline Comparison</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .metric {{ font-weight: bold; }}
                .best {{ background-color: #c8e6c9; }}
            </style>
        </head>
        <body>
            <h1>RAG Pipeline Evaluation Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <h2>Summary</h2>
            <p><span class="metric">Best Retrieval Precision:</span> {comparison['best_retrieval_precision'][0]} ({comparison['best_retrieval_precision'][1].retrieval.precision:.4f})</p>
            <p><span class="metric">Best Generation BLEU:</span> {comparison['best_generation_bleu'][0]} ({comparison['best_generation_bleu'][1].generation.bleu_score:.4f})</p>
            <p><span class="metric">Fastest Pipeline:</span> {comparison['fastest_pipeline'][0]} ({comparison['fastest_pipeline'][1].end_to_end_latency_ms:.2f}ms)</p>
            <p><span class="metric">Cheapest Pipeline:</span> {comparison['cheapest_pipeline'][0]} (${comparison['cheapest_pipeline'][1].cost_usd:.4f})</p>

            <h2>Detailed Metrics</h2>
            <table>
                <tr>
                    <th>Pipeline</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>BLEU</th>
                    <th>Latency (ms)</th>
                    <th>Cost ($)</th>
                </tr>
        """

        for name, metrics in comparison['detailed_comparison'].items():
            html += f"""
                <tr>
                    <td>{name}</td>
                    <td>{metrics['retrieval']['precision']:.4f}</td>
                    <td>{metrics['retrieval']['recall']:.4f}</td>
                    <td>{metrics['generation']['bleu_score']:.4f}</td>
                    <td>{metrics['end_to_end_latency_ms']:.2f}</td>
                    <td>${metrics['cost_usd']:.4f}</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """

        with open(output_path, 'w') as f:
            f.write(html)


def cmd_evaluate(args):
    """Evaluate a single pipeline."""
    evaluator = RAGPipelineEvaluator(args.pipeline)
    metrics = evaluator.evaluate_testset(args.testset)

    output = args.output or f"{evaluator.pipeline_name}_results.json"
    with open(output, 'w') as f:
        json.dump(asdict(metrics), f, indent=2)

    print(f"Evaluation complete. Results saved to {output}")
    print(f"Retrieval Precision: {metrics.retrieval.precision:.4f}")
    print(f"Generation BLEU: {metrics.generation.bleu_score:.4f}")
    print(f"Latency: {metrics.end_to_end_latency_ms:.2f}ms")
    print(f"Cost: ${metrics.cost_usd:.4f}")


def cmd_compare(args):
    """Compare multiple pipelines."""
    pipeline_paths = args.pipelines.split(',')
    results = {}

    for pipeline_path in pipeline_paths:
        evaluator = RAGPipelineEvaluator(pipeline_path.strip())
        metrics = evaluator.evaluate_testset(args.testset)
        results[evaluator.pipeline_name] = metrics

    comparison = ComparativeAnalyzer.compare_pipelines(results)

    output = args.output or "comparison_results.json"
    with open(output, 'w') as f:
        json.dump(comparison, f, indent=2, default=str)

    print(f"Comparison complete. Results saved to {output}")


def cmd_report(args):
    """Generate report from results."""
    with open(args.results) as f:
        data = json.load(f)

    if 'detailed_comparison' in data:
        # Comparison results
        comparison = data
    else:
        # Single pipeline results - wrap it
        comparison = {
            'pipelines': ['pipeline'],
            'detailed_comparison': {'pipeline': data}
        }

    if args.format == 'html':
        output = args.output or "report.html"
        ComparativeAnalyzer.generate_html_report(comparison, output)
        print(f"HTML report generated: {output}")
    else:
        output = args.output or "report.json"
        with open(output, 'w') as f:
            json.dump(comparison, f, indent=2, default=str)
        print(f"JSON report generated: {output}")


def cmd_analyze(args):
    """Analyze specific metric from results."""
    with open(args.results) as f:
        data = json.load(f)

    metric_path = args.metric.split('.')

    if 'detailed_comparison' in data:
        for pipeline, metrics in data['detailed_comparison'].items():
            value = metrics
            for key in metric_path:
                value = value[key]
            print(f"{pipeline}: {value}")
    else:
        value = data
        for key in metric_path:
            value = value[key]
        print(f"Value: {value}")


def main():
    parser = argparse.ArgumentParser(description='RAG Pipeline Evaluator')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Evaluate command
    evaluate_parser = subparsers.add_parser('evaluate', help='Evaluate a pipeline')
    evaluate_parser.add_argument('--pipeline', required=True, help='Path to pipeline module')
    evaluate_parser.add_argument('--testset', required=True, help='Path to testset JSON')
    evaluate_parser.add_argument('--output', help='Output path for results')
    evaluate_parser.set_defaults(func=cmd_evaluate)

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare multiple pipelines')
    compare_parser.add_argument('--pipelines', required=True, help='Comma-separated pipeline paths')
    compare_parser.add_argument('--testset', required=True, help='Path to testset JSON')
    compare_parser.add_argument('--output', help='Output path for comparison results')
    compare_parser.set_defaults(func=cmd_compare)

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate report from results')
    report_parser.add_argument('--results', required=True, help='Path to results JSON')
    report_parser.add_argument('--format', choices=['html', 'json'], default='html', help='Report format')
    report_parser.add_argument('--output', help='Output path for report')
    report_parser.set_defaults(func=cmd_report)

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze specific metric')
    analyze_parser.add_argument('--results', required=True, help='Path to results JSON')
    analyze_parser.add_argument('--metric', required=True, help='Metric path (e.g., retrieval.precision)')
    analyze_parser.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
