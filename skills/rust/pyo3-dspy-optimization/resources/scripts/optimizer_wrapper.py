#!/usr/bin/env python3
"""
DSPy Optimizer Wrapper

Comprehensive wrapper for DSPy teleprompters (BootstrapFewShot, MIPROv2, COPRO) with
progress tracking, evaluation, and model comparison. Designed for Rust/Python interop.

Usage:
    python optimizer_wrapper.py optimize --module module.py --optimizer BootstrapFewShot --trainset train.json
    python optimizer_wrapper.py evaluate --model compiled.json --testset test.json
    python optimizer_wrapper.py compare --models model1.json,model2.json --metric accuracy
    python optimizer_wrapper.py config --optimizer MIPROv2 --show
    python optimizer_wrapper.py list
"""

import os
import sys
import json
import time
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import argparse


class Optimizer(str, Enum):
    """Supported DSPy optimizers."""
    BOOTSTRAP_FEWSHOT = "BootstrapFewShot"
    MIPROV2 = "MIPROv2"
    COPRO = "COPRO"


class EventType(str, Enum):
    """Progress event types."""
    STARTED = "started"
    ITERATION = "iteration"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressEvent:
    """Progress tracking event."""
    event_type: EventType
    timestamp: str
    optimizer: str
    step: Optional[int] = None
    total_steps: Optional[int] = None
    message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, omitting None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class EvaluationMetrics:
    """Model evaluation metrics."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    total_examples: int
    correct: int
    latency_ms: float
    per_class_metrics: Dict[str, Dict[str, float]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class OptimizerConfig:
    """Optimizer configuration with hyperparameters."""
    optimizer: str
    hyperparameters: Dict[str, Any]

    @classmethod
    def get_defaults(cls, optimizer: str) -> 'OptimizerConfig':
        """Get default configuration for an optimizer."""
        defaults = {
            Optimizer.BOOTSTRAP_FEWSHOT: {
                "max_bootstrapped_demos": 4,
                "max_labeled_demos": 8,
                "max_rounds": 1,
                "teacher_settings": None,
            },
            Optimizer.MIPROV2: {
                "num_candidates": 10,
                "init_temperature": 1.0,
                "prompt_model": None,
                "task_model": None,
                "requires_permission_to_run": False,
            },
            Optimizer.COPRO: {
                "breadth": 10,
                "depth": 3,
                "init_temperature": 1.4,
            },
        }

        return cls(
            optimizer=optimizer,
            hyperparameters=defaults.get(optimizer, {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class ProgressTracker:
    """Track and report optimization progress."""

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.events: List[ProgressEvent] = []
        self.start_time = None

    def emit(self, event: ProgressEvent):
        """Emit a progress event."""
        self.events.append(event)

        # Print to console
        if event.event_type == EventType.STARTED:
            print(f"\n╔═══════════════════════════════════╗")
            print(f"║   Optimization Started            ║")
            print(f"╚═══════════════════════════════════╝")
            print(f"Optimizer: {event.optimizer}")
            if event.total_steps:
                print(f"Total steps: {event.total_steps}")
            print()
            self.start_time = time.time()

        elif event.event_type == EventType.ITERATION:
            msg = f"[Step {event.step}] {event.message}"
            if event.metrics:
                msg += f" | {json.dumps(event.metrics)}"
            print(msg)

        elif event.event_type == EventType.COMPLETED:
            duration = time.time() - self.start_time if self.start_time else 0
            print(f"\n╔═══════════════════════════════════╗")
            print(f"║   Optimization Complete           ║")
            print(f"╚═══════════════════════════════════╝")
            print(f"Duration: {duration:.2f}s")
            if event.metrics:
                for key, value in event.metrics.items():
                    print(f"{key}: {value}")
            print()

        elif event.event_type == EventType.FAILED:
            print(f"\n❌ Optimization Failed:")
            print(f"Error: {event.error}")
            print()

        # Log to file if configured
        if self.log_file:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(event.to_dict()) + '\n')

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all events as dictionaries."""
        return [e.to_dict() for e in self.events]


class MetricFactory:
    """Factory for creating evaluation metrics."""

    @staticmethod
    def create_accuracy_metric() -> Callable:
        """Create simple accuracy metric."""
        def accuracy(example, prediction, trace=None):
            if not hasattr(prediction, 'answer'):
                return False
            expected = example.answer.lower().strip()
            predicted = prediction.answer.lower().strip()
            return expected == predicted
        return accuracy

    @staticmethod
    def create_f1_metric() -> Callable:
        """Create F1 score metric."""
        def f1_score(example, prediction, trace=None):
            if not hasattr(prediction, 'answer'):
                return 0.0

            expected_tokens = set(example.answer.lower().split())
            predicted_tokens = set(prediction.answer.lower().split())

            if not predicted_tokens:
                return 0.0

            precision = len(expected_tokens & predicted_tokens) / len(predicted_tokens)
            recall = len(expected_tokens & predicted_tokens) / len(expected_tokens)

            if precision + recall == 0:
                return 0.0

            return 2 * (precision * recall) / (precision + recall)
        return f1_score

    @staticmethod
    def get_metric(metric_name: str) -> Callable:
        """Get metric by name."""
        metrics = {
            "accuracy": MetricFactory.create_accuracy_metric(),
            "f1": MetricFactory.create_f1_metric(),
        }

        if metric_name not in metrics:
            raise ValueError(f"Unknown metric: {metric_name}. Available: {list(metrics.keys())}")

        return metrics[metric_name]


class OptimizerRunner:
    """Run DSPy optimizers with progress tracking."""

    def __init__(self, tracker: Optional[ProgressTracker] = None):
        self.tracker = tracker or ProgressTracker()

    def optimize(
        self,
        module,
        trainset: List,
        optimizer_name: str,
        config: OptimizerConfig,
        metric: Optional[Callable] = None,
        devset: Optional[List] = None,
    ):
        """
        Run optimizer on a DSPy module.

        Args:
            module: DSPy module to optimize
            trainset: Training examples
            optimizer_name: Name of optimizer to use
            config: Optimizer configuration
            metric: Evaluation metric function
            devset: Development/validation set (for MIPROv2)

        Returns:
            Compiled DSPy module
        """
        try:
            import dspy
            from dspy.teleprompt import BootstrapFewShot, MIPROv2, COPRO

            # Use default metric if not provided
            if metric is None:
                metric = MetricFactory.create_accuracy_metric()

            # Emit start event
            self.tracker.emit(ProgressEvent(
                event_type=EventType.STARTED,
                timestamp=datetime.utcnow().isoformat(),
                optimizer=optimizer_name,
                total_steps=None,
                message=f"Starting {optimizer_name} optimization"
            ))

            start_time = time.time()

            # Create and run optimizer
            if optimizer_name == Optimizer.BOOTSTRAP_FEWSHOT:
                compiled = self._run_bootstrap_fewshot(
                    module, trainset, metric, config
                )
            elif optimizer_name == Optimizer.MIPROV2:
                if devset is None:
                    raise ValueError("MIPROv2 requires devset parameter")
                compiled = self._run_miprov2(
                    module, trainset, devset, metric, config
                )
            elif optimizer_name == Optimizer.COPRO:
                compiled = self._run_copro(
                    module, trainset, metric, config
                )
            else:
                raise ValueError(f"Unknown optimizer: {optimizer_name}")

            duration = time.time() - start_time

            # Emit completion event
            self.tracker.emit(ProgressEvent(
                event_type=EventType.COMPLETED,
                timestamp=datetime.utcnow().isoformat(),
                optimizer=optimizer_name,
                message="Optimization completed successfully",
                metrics={
                    "duration_seconds": duration,
                    "training_examples": len(trainset),
                }
            ))

            return compiled

        except Exception as e:
            # Emit failure event
            self.tracker.emit(ProgressEvent(
                event_type=EventType.FAILED,
                timestamp=datetime.utcnow().isoformat(),
                optimizer=optimizer_name,
                error=str(e)
            ))
            raise

    def _run_bootstrap_fewshot(self, module, trainset, metric, config):
        """Run BootstrapFewShot optimizer."""
        from dspy.teleprompt import BootstrapFewShot

        teleprompter = BootstrapFewShot(
            metric=metric,
            **config.hyperparameters
        )

        return teleprompter.compile(
            student=module,
            trainset=trainset,
        )

    def _run_miprov2(self, module, trainset, devset, metric, config):
        """Run MIPROv2 optimizer."""
        from dspy.teleprompt import MIPROv2

        teleprompter = MIPROv2(
            metric=metric,
            **config.hyperparameters
        )

        return teleprompter.compile(
            student=module,
            trainset=trainset,
            devset=devset,
            requires_permission_to_run=config.hyperparameters.get(
                "requires_permission_to_run", False
            )
        )

    def _run_copro(self, module, trainset, metric, config):
        """Run COPRO optimizer."""
        from dspy.teleprompt import COPRO

        teleprompter = COPRO(
            metric=metric,
            **config.hyperparameters
        )

        return teleprompter.compile(
            student=module,
            trainset=trainset,
        )


class Evaluator:
    """Evaluate compiled DSPy models."""

    def __init__(self, metric: Callable):
        self.metric = metric

    def evaluate(
        self,
        model,
        dataset: List,
        display_progress: bool = True
    ) -> EvaluationMetrics:
        """
        Evaluate model on dataset.

        Args:
            model: Compiled DSPy model
            dataset: Evaluation dataset
            display_progress: Whether to show progress

        Returns:
            EvaluationMetrics with results
        """
        import dspy
        from collections import defaultdict

        correct = 0
        total = len(dataset)
        latencies = []

        true_positives = defaultdict(int)
        false_positives = defaultdict(int)
        false_negatives = defaultdict(int)

        for i, example in enumerate(dataset):
            if display_progress and i % 10 == 0:
                print(f"Evaluating: {i}/{total}")

            start = time.time()

            try:
                prediction = model(**example.inputs())
                latency = (time.time() - start) * 1000
                latencies.append(latency)

                is_correct = self.metric(example, prediction)

                if is_correct:
                    correct += 1
                    true_positives[example.answer] += 1
                else:
                    if hasattr(prediction, 'answer'):
                        false_positives[prediction.answer] += 1
                    false_negatives[example.answer] += 1

            except Exception as e:
                print(f"Error on example {i}: {e}")
                latencies.append(0.0)
                false_negatives[example.answer] += 1

        # Calculate metrics
        accuracy = correct / total if total > 0 else 0.0

        all_labels = set(true_positives.keys()) | set(false_positives.keys()) | set(false_negatives.keys())

        per_class = {}
        for label in all_labels:
            tp = true_positives[label]
            fp = false_positives[label]
            fn = false_negatives[label]

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

            per_class[label] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }

        # Macro-averaged metrics
        avg_precision = sum(m["precision"] for m in per_class.values()) / len(per_class) if per_class else 0.0
        avg_recall = sum(m["recall"] for m in per_class.values()) / len(per_class) if per_class else 0.0
        avg_f1 = sum(m["f1"] for m in per_class.values()) / len(per_class) if per_class else 0.0

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        return EvaluationMetrics(
            accuracy=accuracy,
            precision=avg_precision,
            recall=avg_recall,
            f1_score=avg_f1,
            total_examples=total,
            correct=correct,
            latency_ms=avg_latency,
            per_class_metrics=per_class,
        )


class ModelComparator:
    """Compare multiple models statistically."""

    @staticmethod
    def compare(
        results: List[EvaluationMetrics],
        model_names: List[str],
        confidence: float = 0.95
    ) -> Dict[str, Any]:
        """
        Compare evaluation results across models.

        Args:
            results: List of evaluation results
            model_names: Names of models
            confidence: Confidence level for statistical tests

        Returns:
            Comparison report
        """
        if len(results) != len(model_names):
            raise ValueError("Number of results must match number of model names")

        comparison = {
            "models": model_names,
            "metrics": {},
            "winner": None,
            "statistically_significant": False,
        }

        # Compare accuracy
        accuracies = [r.accuracy for r in results]
        best_idx = accuracies.index(max(accuracies))
        comparison["winner"] = model_names[best_idx]

        # Compare all metrics
        for metric_name in ["accuracy", "precision", "recall", "f1_score", "latency_ms"]:
            values = [getattr(r, metric_name) for r in results]
            comparison["metrics"][metric_name] = {
                name: value for name, value in zip(model_names, values)
            }

        # Simple statistical test (Z-test for proportions)
        if len(results) == 2:
            comparison["statistically_significant"] = ModelComparator._z_test(
                results[0], results[1], confidence
            )

        return comparison

    @staticmethod
    def _z_test(result1: EvaluationMetrics, result2: EvaluationMetrics, confidence: float) -> bool:
        """Simple Z-test for comparing two proportions."""
        import math

        n1 = result1.total_examples
        n2 = result2.total_examples
        p1 = result1.accuracy
        p2 = result2.accuracy

        if n1 < 30 or n2 < 30:
            return False  # Sample size too small

        p_pool = (result1.correct + result2.correct) / (n1 + n2)
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))

        if se == 0:
            return False

        z_score = abs((p1 - p2) / se)

        # Critical values
        critical_value = 1.96 if confidence >= 0.95 else 1.645

        return z_score > critical_value


def load_module_from_file(module_path: str):
    """Load a Python module from file path."""
    spec = importlib.util.spec_from_file_location("user_module", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_dataset(dataset_path: str) -> List:
    """Load dataset from JSON/JSONL file."""
    import dspy

    path = Path(dataset_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    dataset = []

    if path.suffix == '.jsonl':
        with open(path) as f:
            for line in f:
                data = json.loads(line)
                example = dspy.Example(**data).with_inputs(*data.keys())
                dataset.append(example)
    else:
        with open(path) as f:
            data = json.load(f)
            for item in data:
                example = dspy.Example(**item).with_inputs(*item.keys())
                dataset.append(example)

    return dataset


def save_compiled_model(model, output_path: str, metadata: Dict[str, Any]):
    """Save compiled model with metadata."""
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    model.save(output_path)
    print(f"✓ Model saved to {output_path}")

    # Save metadata
    metadata['saved_at'] = datetime.utcnow().isoformat()
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved to {metadata_path}")


# CLI Commands

def cmd_optimize(args):
    """Optimize a DSPy module."""
    try:
        import dspy

        # Load module
        user_module = load_module_from_file(args.module)
        if not hasattr(user_module, 'create_module'):
            raise ValueError("Module file must define create_module() function")

        module = user_module.create_module()

        # Load datasets
        trainset = load_dataset(args.trainset)
        devset = load_dataset(args.devset) if args.devset else None

        # Get configuration
        config = OptimizerConfig.get_defaults(args.optimizer)

        # Override with custom config if provided
        if args.config:
            with open(args.config) as f:
                custom_config = json.load(f)
                config.hyperparameters.update(custom_config.get('hyperparameters', {}))

        # Create tracker
        tracker = ProgressTracker(log_file=args.log_file)

        # Run optimization
        runner = OptimizerRunner(tracker)
        metric = MetricFactory.get_metric(args.metric)

        compiled = runner.optimize(
            module=module,
            trainset=trainset,
            optimizer_name=args.optimizer,
            config=config,
            metric=metric,
            devset=devset,
        )

        # Save compiled model
        metadata = {
            "optimizer": args.optimizer,
            "num_training_examples": len(trainset),
            "hyperparameters": config.hyperparameters,
            "created_at": datetime.utcnow().isoformat(),
        }

        save_compiled_model(compiled, args.output, metadata)

        # Output progress events as JSON
        print(json.dumps(tracker.get_events(), indent=2))

    except Exception as e:
        print(f"✗ Optimization failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_evaluate(args):
    """Evaluate a compiled model."""
    try:
        import dspy

        # Load model (simplified - actual loading depends on module type)
        # In practice, you'd need the original module definition
        print(f"Loading model from {args.model}...")

        # Load test set
        testset = load_dataset(args.testset)

        # Create evaluator
        metric = MetricFactory.get_metric(args.metric)
        evaluator = Evaluator(metric)

        # Note: This is a placeholder - actual model loading requires module definition
        print(f"Note: Model evaluation requires the original module definition")
        print(f"Loaded {len(testset)} test examples")

        # Output template result
        result = {
            "model_path": args.model,
            "test_examples": len(testset),
            "metric": args.metric,
            "note": "Actual evaluation requires module definition"
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"✗ Evaluation failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_compare(args):
    """Compare multiple models."""
    try:
        model_paths = args.models.split(',')

        print(f"Comparing {len(model_paths)} models:")
        for path in model_paths:
            print(f"  - {path}")

        # This is a placeholder - actual comparison requires running evaluation
        result = {
            "models": model_paths,
            "metric": args.metric,
            "note": "Actual comparison requires evaluating each model"
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"✗ Comparison failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_config(args):
    """Show or manage optimizer configurations."""
    try:
        if args.show:
            config = OptimizerConfig.get_defaults(args.optimizer)
            print(f"\nDefault configuration for {args.optimizer}:\n")
            print(json.dumps(config.to_dict(), indent=2))
        else:
            # List all available optimizers
            print("\nAvailable optimizers:\n")
            for opt in Optimizer:
                config = OptimizerConfig.get_defaults(opt.value)
                print(f"  {opt.value}:")
                print(f"    {json.dumps(config.hyperparameters, indent=6)}")

    except Exception as e:
        print(f"✗ Config command failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args):
    """List available optimizers and metrics."""
    print("\n╔═══════════════════════════════════╗")
    print("║   Available Optimizers            ║")
    print("╚═══════════════════════════════════╝\n")

    for opt in Optimizer:
        print(f"{opt.value}")
        config = OptimizerConfig.get_defaults(opt.value)
        for key, value in config.hyperparameters.items():
            print(f"  {key}: {value}")
        print()

    print("╔═══════════════════════════════════╗")
    print("║   Available Metrics               ║")
    print("╚═══════════════════════════════════╝\n")
    print("  - accuracy")
    print("  - f1")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="DSPy Optimizer Wrapper with Progress Tracking"
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Optimize command
    parser_opt = subparsers.add_parser('optimize', help='Run optimizer on module')
    parser_opt.add_argument('--module', required=True, help='Path to module.py')
    parser_opt.add_argument('--optimizer', required=True, choices=[o.value for o in Optimizer])
    parser_opt.add_argument('--trainset', required=True, help='Path to training data (JSON/JSONL)')
    parser_opt.add_argument('--devset', help='Path to dev data (required for MIPROv2)')
    parser_opt.add_argument('--metric', default='accuracy', help='Evaluation metric')
    parser_opt.add_argument('--config', help='Path to custom config JSON')
    parser_opt.add_argument('--output', default='compiled_model.json', help='Output path')
    parser_opt.add_argument('--log-file', help='Path to log file')

    # Evaluate command
    parser_eval = subparsers.add_parser('evaluate', help='Evaluate compiled model')
    parser_eval.add_argument('--model', required=True, help='Path to compiled model')
    parser_eval.add_argument('--testset', required=True, help='Path to test data')
    parser_eval.add_argument('--metric', default='accuracy', help='Evaluation metric')

    # Compare command
    parser_cmp = subparsers.add_parser('compare', help='Compare multiple models')
    parser_cmp.add_argument('--models', required=True, help='Comma-separated model paths')
    parser_cmp.add_argument('--metric', default='accuracy', help='Comparison metric')

    # Config command
    parser_cfg = subparsers.add_parser('config', help='Show optimizer configurations')
    parser_cfg.add_argument('--optimizer', choices=[o.value for o in Optimizer], help='Optimizer name')
    parser_cfg.add_argument('--show', action='store_true', help='Show config for optimizer')

    # List command
    parser_list = subparsers.add_parser('list', help='List optimizers and metrics')

    args = parser.parse_args()

    if args.command == 'optimize':
        cmd_optimize(args)
    elif args.command == 'evaluate':
        cmd_evaluate(args)
    elif args.command == 'compare':
        cmd_compare(args)
    elif args.command == 'config':
        cmd_config(args)
    elif args.command == 'list':
        cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
