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

## Related Skills

- `dspy-optimizers.md` - Using metrics for optimization
- `dspy-modules.md` - Programs to evaluate
- `dspy-assertions.md` - Runtime validation
- `llm-dataset-preparation.md` - Creating evaluation datasets

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
