---
name: dspy-optimizers
description: Optimizing DSPy programs with teleprompters, BootstrapFewShot, MIPROv2, and compilation
---

# DSPy Optimizers

**Scope**: Teleprompters, BootstrapFewShot, MIPROv2, COPRO, compilation, metrics
**Lines**: ~440
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Improving DSPy program accuracy with automatic optimization
- Compiling modules with training examples
- Generating optimized few-shot demonstrations
- Tuning prompts and LM weights programmatically
- Bootstrapping training data from small seed sets
- Evaluating and iterating on DSPy programs

## Core Concepts

### What are Optimizers (Teleprompters)?

**Definition**: Optimizers automatically improve DSPy programs by finding better prompts, demonstrations, and parameters

**Original term**: "Teleprompters" (legacy name, now called optimizers)

**Purpose**:
- **Auto-tune**: Find optimal prompts without manual engineering
- **Few-shot learning**: Generate effective demonstrations
- **Weight tuning**: Fine-tune model weights (if supported)
- **Metric optimization**: Maximize custom metrics

**Key insight**: Instead of manually tweaking prompts, define a metric and let DSPy optimize

### Optimization Process

**Compilation workflow**:
1. **Define metric**: Function that scores predictions
2. **Prepare dataset**: Training/validation examples
3. **Choose optimizer**: BootstrapFewShot, MIPROv2, etc.
4. **Compile**: `optimizer.compile(module, trainset=data, metric=metric)`
5. **Evaluate**: Test on held-out data

### Common Optimizers

**BootstrapFewShot**: Generate few-shot examples
- Simplest optimizer
- Creates demonstrations from successful predictions
- Works with any module
- Fast, effective

**MIPROv2**: Multi-prompt instruction optimization
- Optimizes instructions AND demonstrations
- More sophisticated than BootstrapFewShot
- Better for complex tasks
- Slower but higher quality

**COPRO**: Coordinate prompt optimization
- Optimizes prompts across multiple modules
- Good for multi-stage pipelines
- Considers module interactions

**BootstrapFinetune**: Generate data for fine-tuning
- Creates training data for model fine-tuning
- Requires fine-tunable model
- Best accuracy but most expensive

---

## Patterns

### Pattern 1: Basic BootstrapFewShot

```python
import dspy

# Configure LM
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

# Define module
qa = dspy.ChainOfThought("question -> answer")

# Prepare training data
trainset = [
    dspy.Example(question="What is the capital of France?", answer="Paris").with_inputs("question"),
    dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
    dspy.Example(question="Who wrote Hamlet?", answer="William Shakespeare").with_inputs("question"),
]

# Define metric (validation function)
def validate_answer(example, pred, trace=None):
    """Return True if prediction is correct."""
    return example.answer.lower() == pred.answer.lower()

# Create optimizer
optimizer = dspy.BootstrapFewShot(metric=validate_answer)

# Compile (optimize) the module
compiled_qa = optimizer.compile(
    student=qa,
    trainset=trainset,
)

# Use optimized module
result = compiled_qa(question="What is the capital of Germany?")
print(result.answer)
```

**What happens**:
- Runs module on training examples
- Keeps successful predictions as demonstrations
- Optimized module uses these as few-shot examples
- Better accuracy on similar tasks

### Pattern 2: MIPROv2 Optimization

```python
import dspy

# More sophisticated optimization
qa = dspy.ChainOfThought("question, context -> answer")

trainset = [
    dspy.Example(
        question="What is DSPy?",
        context="DSPy is a framework for programming language models.",
        answer="A framework for programming language models"
    ).with_inputs("question", "context"),
    # ... more examples
]

devset = [
    # Validation examples (separate from training)
]

# Define metric with partial credit
def qa_metric(example, pred, trace=None):
    """Score prediction quality (0.0 to 1.0)."""
    answer = pred.answer.lower()
    gold = example.answer.lower()

    # Exact match
    if answer == gold:
        return 1.0

    # Partial match (contains key words)
    if gold in answer or answer in gold:
        return 0.5

    return 0.0

# MIPROv2 optimizer
optimizer = dspy.MIPROv2(
    metric=qa_metric,
    auto="light",  # or "medium", "heavy" for more optimization
    num_candidates=10,  # Number of prompt variations to try
)

# Compile with training and validation sets
compiled_qa = optimizer.compile(
    student=qa,
    trainset=trainset,
    valset=devset,  # Used for selecting best prompts
    max_bootstrapped_demos=4,  # Max few-shot examples
    max_labeled_demos=2,  # Max examples from trainset
)

# Optimized module now has better prompts and demonstrations
result = compiled_qa(question="What is DSPy?", context="...")
```

**Benefits over BootstrapFewShot**:
- Optimizes instruction text, not just examples
- Tries multiple prompt variations
- Uses validation set to pick best prompts
- Higher quality but slower

### Pattern 3: Custom Metric Functions

```python
import dspy

# Metric with detailed scoring
def complex_metric(example, pred, trace=None):
    """Multi-factor metric for comprehensive evaluation."""
    score = 0.0

    # Factor 1: Answer correctness (0.5 weight)
    if example.answer.lower() in pred.answer.lower():
        score += 0.5

    # Factor 2: Confidence (0.2 weight)
    if hasattr(pred, 'confidence'):
        try:
            conf = float(pred.confidence)
            if 0.7 <= conf <= 1.0:
                score += 0.2
        except:
            pass

    # Factor 3: Reasoning quality (0.3 weight)
    if hasattr(pred, 'reasoning'):
        if len(pred.reasoning.split()) > 10:  # Detailed reasoning
            score += 0.15
        if "because" in pred.reasoning.lower():  # Causal reasoning
            score += 0.15

    return score

# Use metric with optimizer
optimizer = dspy.BootstrapFewShot(
    metric=complex_metric,
    metric_threshold=0.7,  # Only keep examples scoring >= 0.7
)
```

**When to use**:
- Multi-factor quality assessment
- Domain-specific requirements
- Nuanced evaluation beyond exact match

### Pattern 4: Optimizing Multi-Module Pipelines

```python
import dspy

class RAGPipeline(dspy.Module):
    """Retrieval-Augmented Generation pipeline."""

    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        passages = self.retrieve(question).passages
        context = "\n".join(passages)
        return self.generate(context=context, question=question)

# Prepare data
trainset = [
    dspy.Example(
        question="What is DSPy?",
        answer="A framework for programming language models"
    ).with_inputs("question"),
]

# Metric for RAG
def rag_metric(example, pred, trace=None):
    # Check if answer is in prediction
    return example.answer.lower() in pred.answer.lower()

# COPRO optimizer (coordinates across modules)
optimizer = dspy.COPRO(
    metric=rag_metric,
    breadth=10,  # Number of prompt variations per module
    depth=3,  # Optimization iterations
)

# Compile entire pipeline
pipeline = RAGPipeline()
compiled_pipeline = optimizer.compile(
    student=pipeline,
    trainset=trainset,
)
```

**When to use**:
- Multi-stage pipelines (RAG, agents, etc.)
- Need to optimize module interactions
- Complex workflows

### Pattern 5: BootstrapFinetune (Model Fine-tuning)

```python
import dspy

# Requires fine-tunable model
teacher = dspy.ChainOfThought("question -> answer")

# Large training dataset
trainset = [
    # Hundreds or thousands of examples
]

# Generate fine-tuning data
optimizer = dspy.BootstrapFinetune(
    metric=lambda ex, pred, trace: ex.answer == pred.answer,
)

# Creates fine-tuning dataset
compiled_teacher = optimizer.compile(
    student=teacher,
    trainset=trainset,
    target="openai/gpt-4o-mini-finetuned",  # Your fine-tuned model
)

# Now use fine-tuned model
finetuned_lm = dspy.LM("openai/gpt-4o-mini-finetuned")
dspy.configure(lm=finetuned_lm)
```

**When to use**:
- Have large training dataset (1000+ examples)
- Need maximum accuracy
- Can afford fine-tuning cost
- Task is well-defined and stable

### Pattern 6: Evaluation-Driven Optimization

```python
import dspy
from dspy.evaluate import Evaluate

# Define program
program = dspy.ChainOfThought("question -> answer")

# Prepare datasets
trainset = [...]  # Training examples
valset = [...]    # Validation examples
testset = [...]   # Test examples (never use for optimization!)

# Define metric
def accuracy(example, pred, trace=None):
    return example.answer.lower() == pred.answer.lower()

# Baseline evaluation
evaluator = Evaluate(
    devset=testset,
    metric=accuracy,
    num_threads=4,  # Parallel evaluation
)

baseline_score = evaluator(program)
print(f"Baseline accuracy: {baseline_score:.2%}")

# Optimize
optimizer = dspy.MIPROv2(metric=accuracy, auto="medium")
optimized = optimizer.compile(
    student=program,
    trainset=trainset,
    valset=valset,
)

# Evaluate optimized version
optimized_score = evaluator(optimized)
print(f"Optimized accuracy: {optimized_score:.2%}")
print(f"Improvement: {(optimized_score - baseline_score):.2%}")
```

**Best practice workflow**:
1. Baseline evaluation
2. Optimize on train/val sets
3. Final evaluation on test set
4. Compare before/after

### Pattern 7: Saving and Loading Compiled Programs

```python
import dspy

# Compile program
optimizer = dspy.MIPROv2(metric=my_metric)
compiled = optimizer.compile(student=program, trainset=trainset)

# Save compiled program
compiled.save("optimized_qa.json")

# Later, load compiled program
loaded_program = dspy.ChainOfThought("question -> answer")
loaded_program.load("optimized_qa.json")

# Use loaded program (has optimized prompts/demos)
result = loaded_program(question="What is DSPy?")
```

**When to use**:
- Production deployment
- Avoid re-optimizing every run
- Share optimized programs with team
- Version control for prompts

### Pattern 8: Iterative Optimization

```python
import dspy

program = dspy.ChainOfThought("question -> answer")

# Start with simple optimizer
optimizer1 = dspy.BootstrapFewShot(metric=my_metric)
v1 = optimizer1.compile(student=program, trainset=trainset)
score_v1 = evaluate(v1)

# If not good enough, try more sophisticated optimizer
if score_v1 < 0.8:
    optimizer2 = dspy.MIPROv2(metric=my_metric, auto="medium")
    v2 = optimizer2.compile(student=v1, trainset=trainset, valset=valset)
    score_v2 = evaluate(v2)

    # If still not good enough, use heavy optimization
    if score_v2 < 0.9:
        optimizer3 = dspy.MIPROv2(metric=my_metric, auto="heavy")
        v3 = optimizer3.compile(student=v2, trainset=trainset, valset=valset)
        score_v3 = evaluate(v3)

# Use best version
best = max([(score_v1, v1), (score_v2, v2), (score_v3, v3)], key=lambda x: x[0])
print(f"Best score: {best[0]:.2%}")
final_program = best[1]
```

**Strategy**: Progressive optimization
- Start fast and simple
- Increase sophistication if needed
- Compare results at each stage

---

## Quick Reference

### Optimizer Comparison

| Optimizer | Speed | Quality | Use Case |
|-----------|-------|---------|----------|
| BootstrapFewShot | Fast | Good | Simple tasks, quick iteration |
| MIPROv2 | Medium | Better | Complex tasks, production |
| COPRO | Slow | Best (pipelines) | Multi-module workflows |
| BootstrapFinetune | Slowest | Best (single module) | Large datasets, max accuracy |

### Optimization Workflow

```
1. Define metric function
2. Prepare trainset (and valset)
3. Choose optimizer
4. Compile: optimizer.compile(student, trainset)
5. Evaluate on testset
6. Save optimized program
```

### Metric Function Template

```python
def my_metric(example, pred, trace=None):
    """
    Args:
        example: Ground truth example
        pred: Model prediction
        trace: Execution trace (optional)

    Returns:
        float: Score between 0.0 and 1.0
        OR
        bool: True if correct, False otherwise
    """
    # Implement scoring logic
    return score
```

### Best Practices

```
✅ DO: Start with BootstrapFewShot for quick iteration
✅ DO: Use separate train/val/test sets
✅ DO: Define clear, measurable metrics
✅ DO: Save optimized programs for production
✅ DO: Evaluate baseline before optimizing

❌ DON'T: Optimize on test set (data leakage!)
❌ DON'T: Use tiny training sets (<10 examples)
❌ DON'T: Ignore metric design (affects optimization)
❌ DON'T: Re-optimize in production (pre-compile)
```

---

## Anti-Patterns

❌ **Optimizing on test set**: Data leakage, inflated scores
```python
# Bad
optimizer.compile(student=program, trainset=testset)  # WRONG!
```
✅ Use separate train/val/test splits:
```python
# Good
compiled = optimizer.compile(student=program, trainset=trainset, valset=valset)
final_score = evaluate(compiled, testset)  # Honest evaluation
```

❌ **Vague metrics**: Optimizer can't improve what it can't measure
```python
# Bad
def bad_metric(example, pred, trace=None):
    return True  # Always returns True, useless!
```
✅ Define clear, discriminative metrics:
```python
# Good
def good_metric(example, pred, trace=None):
    return example.answer.lower() == pred.answer.lower()
```

❌ **Not evaluating baseline**: Don't know if optimization helped
```python
# Bad - skip straight to optimization
optimized = optimizer.compile(...)  # Did it improve? Unknown!
```
✅ Always evaluate baseline first:
```python
# Good
baseline_score = evaluate(program, testset)
optimized = optimizer.compile(program, trainset)
optimized_score = evaluate(optimized, testset)
print(f"Improvement: {optimized_score - baseline_score}")
```

❌ **Tiny training sets**: Not enough signal for optimization
```python
# Bad
trainset = [example1, example2]  # Only 2 examples
```
✅ Use adequate training data:
```python
# Good
trainset = [...]  # 50+ examples for BootstrapFewShot, 500+ for MIPROv2
```

---

## Related Skills

- `dspy-evaluation.md` - Evaluating DSPy programs with metrics
- `dspy-modules.md` - Modules to optimize
- `dspy-signatures.md` - Signatures affected by optimization
- `llm-dataset-preparation.md` - Preparing training datasets

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
