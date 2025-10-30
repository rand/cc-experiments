#!/usr/bin/env python3
"""
PyO3 Performance Analyzer - Comprehensive performance analysis for PyO3 extensions
"""
import argparse, json, logging, sys, time, statistics, traceback
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MetricType(Enum):
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    CPU = "cpu"

@dataclass
class PerformanceMetric:
    name: str
    value: float
    unit: str
    timestamp: float
    metadata: Dict[str, Any] = None

    def to_dict(self): return asdict(self)

@dataclass
class AnalysisResult:
    metrics: List[PerformanceMetric]
    summary: Dict[str, Any]
    recommendations: List[str]
    bottlenecks: List[str]

    def to_dict(self):
        return {
            'metrics': [m.to_dict() for m in self.metrics],
            'summary': self.summary,
            'recommendations': self.recommendations,
            'bottlenecks': self.bottlenecks
        }

class PerformanceAnalyzer:
    def __init__(self):
        self.metrics = []
        self.baseline = None

    def record_metric(self, name: str, value: float, unit: str, metadata=None):
        metric = PerformanceMetric(name, value, unit, time.time(), metadata)
        self.metrics.append(metric)
        return metric

    def analyze_latency(self, timings: List[float]) -> Dict[str, float]:
        if not timings: return {}
        return {
            'mean': statistics.mean(timings),
            'median': statistics.median(timings),
            'std': statistics.stdev(timings) if len(timings) > 1 else 0,
            'min': min(timings),
            'max': max(timings),
            'p95': sorted(timings)[int(len(timings) * 0.95)] if timings else 0,
            'p99': sorted(timings)[int(len(timings) * 0.99)] if timings else 0,
        }

    def analyze_throughput(self, operations: int, duration: float) -> float:
        return operations / duration if duration > 0 else 0

    def detect_bottlenecks(self) -> List[str]:
        bottlenecks = []
        latency_metrics = [m for m in self.metrics if 'latency' in m.name.lower()]
        
        for metric in latency_metrics:
            if metric.value > 1000:  # > 1 second
                bottlenecks.append(f"High latency in {metric.name}: {metric.value:.2f}{metric.unit}")
        
        return bottlenecks

    def generate_recommendations(self) -> List[str]:
        recs = []
        bottlenecks = self.detect_bottlenecks()
        
        if bottlenecks:
            recs.append("Release GIL for CPU-bound operations")
            recs.append("Consider parallel execution with Rayon")
        
        memory_metrics = [m for m in self.metrics if m.name.lower().startswith('memory')]
        if memory_metrics and any(m.value > 1000 for m in memory_metrics):
            recs.append("High memory usage detected - review allocations")
        
        return recs

    def analyze(self) -> AnalysisResult:
        summary = {
            'total_metrics': len(self.metrics),
            'metric_types': list(set(m.name for m in self.metrics)),
        }

        # Aggregate metrics by name
        by_name = {}
        for m in self.metrics:
            if m.name not in by_name:
                by_name[m.name] = []
            by_name[m.name].append(m.value)

        for name, values in by_name.items():
            summary[f'{name}_avg'] = statistics.mean(values)

        bottlenecks = self.detect_bottlenecks()
        recommendations = self.generate_recommendations()

        return AnalysisResult(self.metrics, summary, recommendations, bottlenecks)

    def compare_with_baseline(self, current: AnalysisResult) -> Dict[str, Any]:
        if not self.baseline:
            return {'status': 'no_baseline'}
        
        comparison = {}
        for key in self.baseline.summary:
            if key in current.summary and isinstance(current.summary[key], (int, float)):
                baseline_val = self.baseline.summary[key]
                current_val = current.summary[key]
                if baseline_val:
                    change = ((current_val - baseline_val) / baseline_val) * 100
                    comparison[key] = {'baseline': baseline_val, 'current': current_val, 'change_pct': change}
        
        return comparison

class ReportGenerator:
    @staticmethod
    def generate_text(result: AnalysisResult) -> str:
        lines = ["=== Performance Analysis Report ===\n", "\nSummary:"]
        for k, v in result.summary.items():
            if isinstance(v, float):
                lines.append(f"  {k}: {v:.2f}")
            else:
                lines.append(f"  {k}: {v}")

        if result.bottlenecks:
            lines.append("\nBottlenecks:")
            for b in result.bottlenecks:
                lines.append(f"  • {b}")

        if result.recommendations:
            lines.append("\nRecommendations:")
            for r in result.recommendations:
                lines.append(f"  • {r}")

        return "\n".join(lines)

    @staticmethod
    def generate_json(result: AnalysisResult) -> str:
        return json.dumps(result.to_dict(), indent=2)

def main():
    parser = argparse.ArgumentParser(description='PyO3 Performance Analyzer')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--json', action='store_true')
    
    subparsers = parser.add_subparsers(dest='command')
    
    analyze_parser = subparsers.add_parser('analyze', help='Analyze performance')
    analyze_parser.add_argument('--iterations', type=int, default=1000)
    analyze_parser.add_argument('--output', '-o', type=Path)
    
    compare_parser = subparsers.add_parser('compare', help='Compare with baseline')
    compare_parser.add_argument('baseline', type=Path)
    compare_parser.add_argument('current', type=Path)
    
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.add_argument('input', type=Path)
    report_parser.add_argument('--format', choices=['text', 'json', 'html'], default='text')

    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    analyzer = PerformanceAnalyzer()
    report_gen = ReportGenerator()

    try:
        if args.command == 'analyze':
            # Simulate analysis
            logger.info(f"Running analysis with {args.iterations} iterations...")
            
            timings = []
            for i in range(args.iterations):
                start = time.perf_counter()
                # Simulate work
                _ = sum(range(1000))
                elapsed = time.perf_counter() - start
                timings.append(elapsed * 1000)
                
                if i % 100 == 0:
                    analyzer.record_metric(f"iteration_{i}", elapsed * 1000, "ms")

            latency_stats = analyzer.analyze_latency(timings)
            for stat, value in latency_stats.items():
                analyzer.record_metric(f"latency_{stat}", value, "ms")

            result = analyzer.analyze()

            if args.json:
                output = report_gen.generate_json(result)
            else:
                output = report_gen.generate_text(result)

            if args.output:
                args.output.write_text(output)
                print(f"Report saved to {args.output}")
            else:
                print(output)

        elif args.command == 'compare':
            with open(args.baseline) as f:
                baseline_data = json.load(f)
            with open(args.current) as f:
                current_data = json.load(f)

            print("\nPerformance Comparison:")
            print(f"Baseline: {args.baseline}")
            print(f"Current:  {args.current}")
            print("\nChanges:")
            
            for key in baseline_data.get('summary', {}):
                if key in current_data.get('summary', {}):
                    b = baseline_data['summary'][key]
                    c = current_data['summary'][key]
                    if isinstance(b, (int, float)) and isinstance(c, (int, float)):
                        change = ((c - b) / b * 100) if b else 0
                        symbol = "↑" if change > 0 else "↓" if change < 0 else "="
                        print(f"  {key}: {b:.2f} → {c:.2f} ({symbol} {abs(change):.1f}%)")

        elif args.command == 'report':
            with open(args.input) as f:
                data = json.load(f)
            
            result = AnalysisResult(
                metrics=[],
                summary=data.get('summary', {}),
                recommendations=data.get('recommendations', []),
                bottlenecks=data.get('bottlenecks', [])
            )

            if args.format == 'json':
                print(report_gen.generate_json(result))
            else:
                print(report_gen.generate_text(result))

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()
