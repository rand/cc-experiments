---
name: dspy-evaluation
description: Evaluating DSPy programs with metrics, Evaluate class, and performance analysis
---

# DSPy Evaluation

**Scope**: Metrics, Evaluate class, performance measurement, A/B testing, debugging
**Lines**: ~380
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Measuring DSPy program accuracy and performance
- Comparing different modules or optimizations
- Setting up automated evaluation pipelines
- Debugging module failures
- Running A/B tests on prompt variations
- Validating program quality before production

## Core Concepts

### Evaluation in DSPy

**Purpose**: Measure how well your program performs
- **Quantitative**: Accuracy, F1, BLEU scores
- **Qualitative**: Inspect specific predictions
- **Comparative**: Before vs after optimization
- **Continuous**: Monitor production performance

**Key insight**: Good evaluation drives good optimization

### Metrics

**Definition**: Functions that score predictions

**Types**:
1. **Binary**: True/False (correct/incorrect)
2. **Continuous**: 0.0 to 1.0 (partial credit)
3. **Multi-metric**: Combine multiple factors

**Requirements**:
```python
def metric(example, pred, trace=None) -> bool | float:
    """
    Args:
        example: Ground truth example with .answer, etc.
        pred: Prediction object with .answer, .reasoning, etc.
        trace: Optional execution trace

    Returns:
        bool: True if correct, False otherwise
        OR
        float: Score between 0.0 and 1.0
    """
    pass
```

### Evaluate Class

**Purpose**: Run systematic evaluation on datasets

**Features**:
- Parallel execution (multi-threading)
- Progress tracking
- Error handling
- Statistical aggregation
- Display modes (table, summary)

---

## Patterns

### Pattern 1: Simple Accuracy Metric

```python
import dspy

# Binary metric: exact match
def exact_match(example, pred, trace=None):
    """Return True if prediction exactly matches answer."""
    return example.answer.lower().strip() == pred.answer.lower().strip()

# Usage
program = dspy.Predict("question -> answer")

# Manual evaluation
result = program(question="What is 2+2?")
example = dspy.Example(question="What is 2+2?", answer="4")

is_correct = exact_match(example, result)
print(f"Correct: {is_correct}")
```

**When to use**:
- Classification tasks
- QA with definite answers
- Quick validation

### Pattern 2: Partial Credit Metric

```python
import dspy

def fuzzy_match(example, pred, trace=None):
    """Return score based on answer overlap."""
    answer = pred.answer.lower()
    gold = example.answer.lower()

    # Exact match
    if answer == gold:
        return 1.0

    # Partial match: gold answer appears in prediction
    if gold in answer:
        return 0.7

    # Weak match: any word overlap
    answer_words = set(answer.split())
    gold_words = set(gold.split())
    overlap = len(answer_words & gold_words)

    if overlap > 0:
        return 0.3 * (overlap / len(gold_words))

    return 0.0

# Use with optimizer
optimizer = dspy.BootstrapFewShot(metric=fuzzy_match, metric_threshold=0.7)
```

**When to use**:
- Open-ended text generation
- Summarization
- Tasks where partial correctness matters

### Pattern 3: Using Evaluate Class

```python
import dspy
from dspy.evaluate import Evaluate

# Define program
program = dspy.ChainOfThought("question -> answer")

# Prepare test set
testset = [
    dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
    dspy.Example(question="Capital of France?", answer="Paris").with_inputs("question"),
    dspy.Example(question="Who wrote Hamlet?", answer="Shakespeare").with_inputs("question"),
]

# Define metric
def accuracy(example, pred, trace=None):
    return example.answer.lower() in pred.answer.lower()

# Create evaluator
evaluator = Evaluate(
    devset=testset,
    metric=accuracy,
    num_threads=4,  # Parallel evaluation
    display_progress=True,
    display_table=5,  # Show first 5 results
)

# Run evaluation
score = evaluator(program)
print(f"Accuracy: {score:.1%}")
```

**Output example**:
```
Question                    | Predicted Answer | Correct
----------------------------|------------------|--------
What is 2+2?               | 4                | ✓
Capital of France?         | Paris            | ✓
Who wrote Hamlet?          | William Shakespeare | ✓

Accuracy: 100.0%
```

### Pattern 4: Multi-Metric Evaluation

```python
import dspy
from dspy.evaluate import Evaluate

# Multiple metrics for comprehensive evaluation
def accuracy(example, pred, trace=None):
    return example.answer.lower() in pred.answer.lower()

def has_reasoning(example, pred, trace=None):
    """Check if reasoning is provided and non-trivial."""
    if not hasattr(pred, 'reasoning'):
        return 0.0
    return 1.0 if len(pred.reasoning.split()) > 5 else 0.0

def confidence_calibration(example, pred, trace=None):
    """Check if confidence matches correctness."""
    is_correct = accuracy(example, pred)
    if hasattr(pred, 'confidence'):
        conf = float(pred.confidence) if pred.confidence else 0.5
        # High confidence + correct = good
        # Low confidence + incorrect = good
        # Mismatch = bad
        if is_correct and conf > 0.7:
            return 1.0
        if not is_correct and conf < 0.3:
            return 1.0
        return 0.5
    return 0.5

# Evaluate each metric separately
eval_accuracy = Evaluate(devset=testset, metric=accuracy)
eval_reasoning = Evaluate(devset=testset, metric=has_reasoning)
eval_calibration = Evaluate(devset=testset, metric=confidence_calibration)

# Run all evaluations
acc_score = eval_accuracy(program)
reasoning_score = eval_reasoning(program)
calib_score = eval_calibration(program)

print(f"Accuracy: {acc_score:.1%}")
print(f"Reasoning Quality: {reasoning_score:.1%}")
print(f"Calibration: {calib_score:.1%}")

# Composite score
overall = 0.6 * acc_score + 0.2 * reasoning_score + 0.2 * calib_score
print(f"Overall Score: {overall:.1%}")
```

**When to use**:
- Production systems with multiple quality factors
- Need comprehensive quality assessment
- Balancing multiple objectives

### Pattern 5: A/B Testing Programs

```python
import dspy
from dspy.evaluate import Evaluate

# Program A: Simple Predict
program_a = dspy.Predict("question -> answer")

# Program B: ChainOfThought
program_b = dspy.ChainOfThought("question -> answer")

# Prepare test set
testset = [...]

# Define metric
def accuracy(example, pred, trace=None):
    return example.answer.lower() in pred.answer.lower()

# Create evaluator
evaluator = Evaluate(devset=testset, metric=accuracy, num_threads=4)

# Evaluate both programs
score_a = evaluator(program_a)
score_b = evaluator(program_b)

# Compare results
print(f"Program A (Predict): {score_a:.1%}")
print(f"Program B (ChainOfThought): {score_b:.1%}")
print(f"Winner: {'B' if score_b > score_a else 'A'}")
print(f"Improvement: {abs(score_b - score_a):.1%}")
```

**When to use**:
- Comparing module types (Predict vs ChainOfThought)
- Comparing optimizations (before vs after)
- Choosing between LMs (GPT-4 vs Claude)

### Pattern 6: Error Analysis

```python
import dspy
from dspy.evaluate import Evaluate

program = dspy.ChainOfThought("question -> answer")
testset = [...]

# Track errors for analysis
errors = []

def accuracy_with_logging(example, pred, trace=None):
    """Metric that logs errors for analysis."""
    correct = example.answer.lower() in pred.answer.lower()

    if not correct:
        errors.append({
            'question': example.question,
            'expected': example.answer,
            'predicted': pred.answer,
            'reasoning': getattr(pred, 'reasoning', 'N/A'),
        })

    return correct

# Run evaluation
evaluator = Evaluate(devset=testset, metric=accuracy_with_logging)
score = evaluator(program)

# Analyze errors
print(f"\nAccuracy: {score:.1%}")
print(f"\nErrors ({len(errors)}):")
for i, err in enumerate(errors[:5], 1):  # Show first 5 errors
    print(f"\n{i}. Question: {err['question']}")
    print(f"   Expected: {err['expected']}")
    print(f"   Predicted: {err['predicted']}")
    print(f"   Reasoning: {err['reasoning']}")
```

**Benefits**:
- Identify common failure patterns
- Guide optimization efforts
- Improve training data

### Pattern 7: LM-as-Judge Metric

```python
import dspy

# Use LM to evaluate predictions
judge = dspy.ChainOfThought("question, answer, predicted_answer -> score: float, explanation")

def llm_judge_metric(example, pred, trace=None):
    """Use language model to evaluate answer quality."""
    result = judge(
        question=example.question,
        answer=example.answer,
        predicted_answer=pred.answer
    )

    try:
        score = float(result.score)
        return max(0.0, min(1.0, score))  # Clamp to [0, 1]
    except:
        # Fallback to simple match if LM fails
        return 1.0 if example.answer.lower() in pred.answer.lower() else 0.0

# Use LM-as-judge for nuanced evaluation
evaluator = Evaluate(devset=testset, metric=llm_judge_metric, num_threads=1)  # Sequential for LM calls
score = evaluator(program)
```

**When to use**:
- Open-ended generation tasks
- Nuanced quality assessment
- When exact match is too strict

**Caution**:
- Slower (requires LM calls)
- More expensive
- LM judge can be wrong

### Pattern 8: Production Monitoring

```python
import dspy
from dspy.evaluate import Evaluate
import time

# Production program
program = dspy.ChainOfThought("question -> answer")

# Metrics for monitoring
def response_quality(example, pred, trace=None):
    """Monitor prediction quality."""
    return example.answer.lower() in pred.answer.lower()

def response_time(example, pred, trace=None):
    """Monitor latency (tracked separately)."""
    # This is illustrative; actual timing would be external
    return 1.0  # Placeholder

# Sample production traffic for evaluation
sample_size = 100
production_samples = [...]  # Collect from production logs

# Periodic evaluation
evaluator = Evaluate(
    devset=production_samples,
    metric=response_quality,
    num_threads=4,
)

# Run evaluation
score = evaluator(program)

# Alert if quality drops
if score < 0.85:
    print(f"⚠️ Quality degradation detected: {score:.1%}")
    # Send alert, trigger investigation
else:
    print(f"✓ Quality maintained: {score:.1%}")
```

**When to use**:
- Production monitoring
- Detecting model drift
- Continuous quality assurance

---

## Quick Reference

### Metric Function Template

```python
def my_metric(example, pred, trace=None):
    """
    Evaluate prediction quality.

    Args:
        example: dspy.Example with ground truth
        pred: Prediction object from module
        trace: Optional execution trace

    Returns:
        bool: True/False for binary metrics
        float: 0.0-1.0 for continuous metrics
    """
    # Implement evaluation logic
    return score
```

### Common Metrics

```python
# Exact match
def exact_match(ex, pred, trace=None):
    return ex.answer == pred.answer

# Contains
def contains(ex, pred, trace=None):
    return ex.answer.lower() in pred.answer.lower()

# Fuzzy match
def fuzzy(ex, pred, trace=None):
    from difflib import SequenceMatcher
    ratio = SequenceMatcher(None, ex.answer, pred.answer).ratio()
    return ratio

# F1 score
def f1_score(ex, pred, trace=None):
    ex_words = set(ex.answer.lower().split())
    pred_words = set(pred.answer.lower().split())
    overlap = len(ex_words & pred_words)
    precision = overlap / len(pred_words) if pred_words else 0
    recall = overlap / len(ex_words) if ex_words else 0
    return 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
```

### Evaluation Checklist

```
✅ DO: Use separate test set (never seen during training)
✅ DO: Evaluate baseline before optimization
✅ DO: Use multiple metrics for comprehensive view
✅ DO: Run error analysis on failures
✅ DO: Report confidence intervals if dataset is small

❌ DON'T: Evaluate on training data (overfitting!)
❌ DON'T: Rely on single metric
❌ DON'T: Ignore errors (analyze them!)
❌ DON'T: Skip baseline comparison
```

---

## Anti-Patterns

❌ **Evaluating on training data**: Overfitting, invalid results
```python
# Bad
evaluator = Evaluate(devset=trainset, metric=accuracy)  # WRONG!
```
✅ Use held-out test set:
```python
# Good
evaluator = Evaluate(devset=testset, metric=accuracy)
```

❌ **Single metric only**: Misses important quality factors
```python
# Bad - only accuracy
score = evaluate(program, accuracy)
```
✅ Use multiple metrics:
```python
# Good - comprehensive evaluation
acc = evaluate(program, accuracy)
f1 = evaluate(program, f1_score)
reasoning = evaluate(program, has_reasoning)
```

❌ **No error analysis**: Don't learn from failures
```python
# Bad - just get score, don't investigate
score = evaluator(program)
print(score)  # Done, but learned nothing
```
✅ Analyze errors:
```python
# Good - investigate failures
score = evaluator(program)
errors = [ex for ex in testset if not metric(ex, program(ex.question))]
analyze_common_patterns(errors)
```

---

## Advanced Patterns

### Pattern 9: Continuous Evaluation Pipeline

```python
import dspy
from dspy.evaluate import Evaluate
from typing import List, Dict
import json
from datetime import datetime
from pathlib import Path

class ContinuousEvaluator:
    """Automated evaluation pipeline for production monitoring."""

    def __init__(self, program: dspy.Module, metrics: Dict[str, callable], testset: List[dspy.Example]):
        self.program = program
        self.metrics = metrics
        self.testset = testset
        self.history = []

    def evaluate_snapshot(self) -> Dict:
        """Run full evaluation suite."""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'scores': {},
        }

        for metric_name, metric_fn in self.metrics.items():
            evaluator = Evaluate(
                devset=self.testset,
                metric=metric_fn,
                num_threads=4,
                display_progress=False,
            )

            score = evaluator(self.program)
            snapshot['scores'][metric_name] = score

        self.history.append(snapshot)
        return snapshot

    def save_history(self, filepath: str):
        """Save evaluation history."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.history, f, indent=2)

    def check_degradation(self, threshold: float = 0.05) -> List[str]:
        """Check for performance degradation."""
        if len(self.history) < 2:
            return []

        current = self.history[-1]['scores']
        previous = self.history[-2]['scores']

        alerts = []
        for metric_name in current:
            curr_score = current[metric_name]
            prev_score = previous[metric_name]

            if curr_score < prev_score - threshold:
                alerts.append(
                    f"{metric_name}: {prev_score:.2%} → {curr_score:.2%} "
                    f"(degraded by {(prev_score - curr_score):.2%})"
                )

        return alerts

# Set up continuous evaluation
program = dspy.ChainOfThought("question -> answer")
program.load("models/production_v1.json")

testset = [...]  # Production test set

metrics = {
    'accuracy': lambda ex, pred, trace: ex.answer.lower() in pred.answer.lower(),
    'precision': lambda ex, pred, trace: compute_precision(ex, pred),
    'recall': lambda ex, pred, trace: compute_recall(ex, pred),
}

evaluator = ContinuousEvaluator(program, metrics, testset)

# Run periodic evaluation (e.g., daily)
snapshot = evaluator.evaluate_snapshot()
print(f"Evaluation snapshot: {snapshot}")

# Check for degradation
alerts = evaluator.check_degradation(threshold=0.03)
if alerts:
    print("⚠️ Performance degradation detected:")
    for alert in alerts:
        print(f"  - {alert}")
    # Send alerts to monitoring system

# Save history
evaluator.save_history("monitoring/eval_history.json")
```

**When to use**:
- Production systems requiring continuous monitoring
- Detecting model drift or degradation
- Automated quality assurance

### Pattern 10: Stratified Evaluation

```python
import dspy
from dspy.evaluate import Evaluate
from typing import List, Dict, Callable
from collections import defaultdict

class StratifiedEvaluator:
    """Evaluate performance across different data strata."""

    def __init__(self, metric: Callable, stratify_fn: Callable):
        self.metric = metric
        self.stratify_fn = stratify_fn

    def evaluate(self, program: dspy.Module, testset: List[dspy.Example]) -> Dict:
        """Evaluate with stratification."""

        # Group examples by strata
        strata = defaultdict(list)
        for example in testset:
            stratum = self.stratify_fn(example)
            strata[stratum].append(example)

        # Evaluate each stratum
        results = {}
        for stratum_name, stratum_examples in strata.items():
            if not stratum_examples:
                continue

            evaluator = Evaluate(
                devset=stratum_examples,
                metric=self.metric,
                num_threads=4,
                display_progress=False,
            )

            score = evaluator(program)
            results[stratum_name] = {
                'score': score,
                'count': len(stratum_examples),
            }

        # Overall score
        total_examples = sum(r['count'] for r in results.values())
        overall_score = sum(
            r['score'] * r['count'] for r in results.values()
        ) / total_examples

        results['overall'] = {
            'score': overall_score,
            'count': total_examples,
        }

        return results

# Define stratification function
def stratify_by_difficulty(example: dspy.Example) -> str:
    """Stratify by question length (proxy for difficulty)."""
    word_count = len(example.question.split())

    if word_count < 10:
        return 'easy'
    elif word_count < 20:
        return 'medium'
    else:
        return 'hard'

# Use stratified evaluator
def accuracy(ex, pred, trace=None):
    return ex.answer.lower() in pred.answer.lower()

evaluator = StratifiedEvaluator(accuracy, stratify_by_difficulty)

program = dspy.ChainOfThought("question -> answer")
results = evaluator.evaluate(program, testset)

# Print results by stratum
print("\n=== Stratified Results ===")
for stratum, data in results.items():
    print(f"{stratum:10} | Score: {data['score']:.1%} | Count: {data['count']:3}")
```

**When to use**:
- Identify performance gaps across data segments
- Ensure fairness across different input types
- Debug systematic failures

### Pattern 11: Cost-Performance Tradeoff Analysis

```python
import dspy
from dspy.evaluate import Evaluate
from typing import List, Tuple
import matplotlib.pyplot as plt

class CostPerformanceAnalyzer:
    """Analyze cost vs performance tradeoffs."""

    def __init__(self, testset: List[dspy.Example], metric: callable):
        self.testset = testset
        self.metric = metric

    def analyze_models(
        self,
        program_factory: callable,
        model_configs: List[dict]
    ) -> List[dict]:
        """Evaluate multiple model configurations."""

        results = []

        for config in model_configs:
            print(f"\nEvaluating {config['name']}...")

            # Create program with this config
            lm = dspy.LM(
                config['model'],
                max_tokens=config.get('max_tokens', 500),
            )
            dspy.configure(lm=lm)

            program = program_factory()

            # Evaluate
            evaluator = Evaluate(
                devset=self.testset,
                metric=self.metric,
                num_threads=4,
            )

            score = evaluator(program)

            results.append({
                'name': config['name'],
                'model': config['model'],
                'score': score,
                'cost_per_1k': config.get('cost_per_1k', 0),
            })

        return results

    def plot_tradeoff(self, results: List[dict]):
        """Visualize cost-performance tradeoff."""
        names = [r['name'] for r in results]
        scores = [r['score'] * 100 for r in results]
        costs = [r['cost_per_1k'] for r in results]

        plt.figure(figsize=(10, 6))
        plt.scatter(costs, scores, s=100)

        for i, name in enumerate(names):
            plt.annotate(name, (costs[i], scores[i]), xytext=(5, 5),
                        textcoords='offset points')

        plt.xlabel('Cost per 1K tokens (USD)')
        plt.ylabel('Accuracy (%)')
        plt.title('Cost vs Performance Tradeoff')
        plt.grid(True, alpha=0.3)
        plt.savefig('cost_performance_tradeoff.png')
        print("\nPlot saved to cost_performance_tradeoff.png")

# Define model configurations
model_configs = [
    {'name': 'GPT-4o-mini', 'model': 'openai/gpt-4o-mini', 'cost_per_1k': 0.15},
    {'name': 'GPT-4o', 'model': 'openai/gpt-4o', 'cost_per_1k': 2.50},
    {'name': 'Claude Haiku', 'model': 'anthropic/claude-3-haiku-20240307', 'cost_per_1k': 0.25},
    {'name': 'Claude Sonnet', 'model': 'anthropic/claude-3-5-sonnet-20241022', 'cost_per_1k': 3.00},
]

# Analyze
def program_factory():
    return dspy.ChainOfThought("question -> answer")

def accuracy(ex, pred, trace=None):
    return ex.answer.lower() in pred.answer.lower()

analyzer = CostPerformanceAnalyzer(testset, accuracy)
results = analyzer.analyze_models(program_factory, model_configs)

# Display results
print("\n=== Cost-Performance Analysis ===")
for r in sorted(results, key=lambda x: x['score'], reverse=True):
    print(f"{r['name']:15} | Accuracy: {r['score']:.1%} | Cost: ${r['cost_per_1k']:.2f}/1K")

# Plot
analyzer.plot_tradeoff(results)
```

**When to use**:
- Optimize deployment costs
- Choose appropriate model for use case
- Justify infrastructure spending

---

## Production Considerations

### Deployment Strategy

**Evaluation in CI/CD**:
```yaml
# .github/workflows/evaluate.yml
name: Model Evaluation

on:
  pull_request:
    paths:
      - 'models/**'
      - 'prompts/**'

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install dspy-ai

      - name: Run evaluation
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python scripts/evaluate_model.py --threshold 0.80

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: evaluation-results
          path: results/evaluation_*.json
```

**Evaluation script**:
```python
# scripts/evaluate_model.py
import dspy
import argparse
import json
from dspy.evaluate import Evaluate
from pathlib import Path

def load_program(model_path: str) -> dspy.Module:
    """Load model from path."""
    program = dspy.ChainOfThought("question -> answer")
    program.load(model_path)
    return program

def load_testset(testset_path: str) -> list:
    """Load test set."""
    with open(testset_path) as f:
        data = json.load(f)

    return [
        dspy.Example(**item).with_inputs("question")
        for item in data
    ]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='models/latest.json')
    parser.add_argument('--testset', default='data/testset.json')
    parser.add_argument('--threshold', type=float, default=0.80)
    args = parser.parse_args()

    # Load
    program = load_program(args.model)
    testset = load_testset(args.testset)

    # Evaluate
    def accuracy(ex, pred, trace=None):
        return ex.answer.lower() in pred.answer.lower()

    evaluator = Evaluate(devset=testset, metric=accuracy, num_threads=4)
    score = evaluator(program)

    # Save results
    results = {
        'model': args.model,
        'score': score,
        'threshold': args.threshold,
        'passed': score >= args.threshold,
    }

    Path('results').mkdir(exist_ok=True)
    with open('results/evaluation_latest.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n=== Evaluation Results ===")
    print(f"Score: {score:.1%}")
    print(f"Threshold: {args.threshold:.1%}")
    print(f"Status: {'✓ PASS' if results['passed'] else '✗ FAIL'}")

    if not results['passed']:
        exit(1)  # Fail CI if below threshold

if __name__ == '__main__':
    main()
```

### Real-time Performance Monitoring

```python
import dspy
from typing import Dict, Optional
from datetime import datetime, timedelta
import threading
import time

class RealTimeMonitor:
    """Monitor DSPy program performance in real-time."""

    def __init__(self, program: dspy.Module, window_size: int = 100):
        self.program = program
        self.window_size = window_size
        self.metrics = {
            'total_calls': 0,
            'recent_latencies': [],
            'recent_successes': [],
            'error_count': 0,
        }
        self.lock = threading.Lock()

    def __call__(self, *args, **kwargs):
        """Wrapped call with monitoring."""
        start = time.time()

        with self.lock:
            self.metrics['total_calls'] += 1

        try:
            result = self.program(*args, **kwargs)

            latency = time.time() - start
            with self.lock:
                self.metrics['recent_latencies'].append(latency)
                self.metrics['recent_successes'].append(True)

                # Keep only recent data
                if len(self.metrics['recent_latencies']) > self.window_size:
                    self.metrics['recent_latencies'].pop(0)
                    self.metrics['recent_successes'].pop(0)

            return result

        except Exception as e:
            with self.lock:
                self.metrics['error_count'] += 1
                self.metrics['recent_successes'].append(False)
                if len(self.metrics['recent_successes']) > self.window_size:
                    self.metrics['recent_successes'].pop(0)
            raise

    def get_stats(self) -> Dict:
        """Get current statistics."""
        with self.lock:
            if not self.metrics['recent_latencies']:
                avg_latency = 0.0
                p95_latency = 0.0
            else:
                avg_latency = sum(self.metrics['recent_latencies']) / len(self.metrics['recent_latencies'])
                sorted_latencies = sorted(self.metrics['recent_latencies'])
                p95_idx = int(len(sorted_latencies) * 0.95)
                p95_latency = sorted_latencies[p95_idx] if sorted_latencies else 0.0

            if not self.metrics['recent_successes']:
                success_rate = 1.0
            else:
                success_rate = sum(self.metrics['recent_successes']) / len(self.metrics['recent_successes'])

            return {
                'total_calls': self.metrics['total_calls'],
                'avg_latency_ms': avg_latency * 1000,
                'p95_latency_ms': p95_latency * 1000,
                'success_rate': success_rate,
                'error_count': self.metrics['error_count'],
            }

# Use monitor
program = dspy.ChainOfThought("question -> answer")
program.load("models/production.json")

monitored = RealTimeMonitor(program, window_size=100)

# Use in production
result = monitored(question="What is DSPy?")

# Check stats periodically
stats = monitored.get_stats()
print(f"Avg latency: {stats['avg_latency_ms']:.1f}ms")
print(f"P95 latency: {stats['p95_latency_ms']:.1f}ms")
print(f"Success rate: {stats['success_rate']:.1%}")
```

### Shadow Evaluation

```python
import dspy
from typing import Dict
import logging

class ShadowEvaluator:
    """Run new model in shadow mode alongside production."""

    def __init__(self, production: dspy.Module, shadow: dspy.Module):
        self.production = production
        self.shadow = shadow
        self.comparison_data = []

    def __call__(self, *args, **kwargs):
        """Run both models, return production result."""

        # Production call (synchronous, user-facing)
        prod_result = self.production(*args, **kwargs)

        # Shadow call (async, logged for analysis)
        try:
            shadow_result = self.shadow(*args, **kwargs)

            # Compare results
            comparison = {
                'production': prod_result.answer if hasattr(prod_result, 'answer') else str(prod_result),
                'shadow': shadow_result.answer if hasattr(shadow_result, 'answer') else str(shadow_result),
                'match': self._compare(prod_result, shadow_result),
            }

            self.comparison_data.append(comparison)

            # Log significant differences
            if not comparison['match']:
                logging.info(f"Shadow divergence: {comparison}")

        except Exception as e:
            logging.error(f"Shadow evaluation failed: {e}")

        # Always return production result
        return prod_result

    def _compare(self, prod_result, shadow_result) -> bool:
        """Compare results."""
        if hasattr(prod_result, 'answer') and hasattr(shadow_result, 'answer'):
            return prod_result.answer.lower() == shadow_result.answer.lower()
        return str(prod_result) == str(shadow_result)

    def get_analysis(self) -> Dict:
        """Analyze shadow performance."""
        if not self.comparison_data:
            return {'match_rate': 0.0, 'total_comparisons': 0}

        matches = sum(1 for c in self.comparison_data if c['match'])
        return {
            'match_rate': matches / len(self.comparison_data),
            'total_comparisons': len(self.comparison_data),
            'divergences': [c for c in self.comparison_data if not c['match']],
        }

# Load models
production = dspy.ChainOfThought("question -> answer")
production.load("models/production_v1.json")

shadow = dspy.ChainOfThought("question -> answer")
shadow.load("models/candidate_v2.json")

# Use shadow evaluator
evaluator = ShadowEvaluator(production, shadow)

# Production traffic
result = evaluator(question="What is DSPy?")

# Analyze after N requests
if len(evaluator.comparison_data) >= 1000:
    analysis = evaluator.get_analysis()
    print(f"Shadow match rate: {analysis['match_rate']:.1%}")

    if analysis['match_rate'] >= 0.95:
        print("✓ Shadow model ready for promotion")
    else:
        print("✗ Shadow model needs more work")
```

### Best Practices Checklist

```
Development:
✅ DO: Use separate test set (never seen during training)
✅ DO: Evaluate baseline before optimization
✅ DO: Use multiple metrics for comprehensive assessment
✅ DO: Run error analysis on failures
✅ DO: Version control evaluation datasets
✅ DO: Document metric definitions clearly

Production:
✅ DO: Integrate evaluation into CI/CD pipeline
✅ DO: Set quality thresholds for deployment
✅ DO: Monitor performance continuously
✅ DO: Use shadow evaluation for new models
✅ DO: Track cost alongside performance
✅ DO: Alert on performance degradation

Scaling:
✅ DO: Parallelize evaluation (num_threads)
✅ DO: Sample for large-scale evaluation
✅ DO: Cache evaluation results
✅ DO: Use stratified evaluation for fairness

❌ DON'T: Evaluate on training data (overfitting)
❌ DON'T: Rely on single metric only
❌ DON'T: Skip baseline comparison
❌ DON'T: Deploy without evaluation
❌ DON'T: Ignore systematic error patterns
```

---

## Related Skills

### Core DSPy Skills
- `dspy-optimizers.md` - Using metrics for optimization
- `dspy-modules.md` - Programs to evaluate
- `dspy-assertions.md` - Runtime validation
- `dspy-signatures.md` - Signature quality evaluation
- `dspy-setup.md` - LM configuration for evaluation

### Advanced DSPy Skills
- `dspy-agents.md` - Evaluating agent performance
- `dspy-multi-agent.md` - Multi-agent evaluation strategies
- `dspy-production.md` - Production monitoring and evaluation
- `dspy-testing.md` - Testing methodologies
- `dspy-debugging.md` - Debugging evaluation failures
- `dspy-advanced-patterns.md` - Advanced evaluation patterns

### Infrastructure Skills
- `modal-functions-basics.md` - Running large-scale evaluation on Modal
- `llm-dataset-preparation.md` - Creating evaluation datasets

### Resources
- `resources/dspy/level2-evaluation.md` - Evaluation deep dive
- `resources/dspy/level3-production.md` - Production evaluation guide
- `resources/dspy/evaluation-cookbook.md` - Evaluation recipes

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
