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

## Advanced Patterns

### Pattern 9: Multi-Stage Optimization Pipeline

```python
import dspy
from typing import List

class OptimizationPipeline:
    """Progressively optimize with multiple optimizers."""

    def __init__(self, trainset, valset, metric):
        self.trainset = trainset
        self.valset = valset
        self.metric = metric
        self.history = []

    def optimize(self, program, stages: List[dict]) -> dspy.Module:
        """Run multi-stage optimization."""
        current = program

        for i, stage in enumerate(stages):
            print(f"\nStage {i+1}: {stage['name']}")

            optimizer = stage['optimizer']
            compiled = optimizer.compile(
                student=current,
                trainset=self.trainset,
                valset=self.valset if stage.get('use_val') else None,
            )

            # Evaluate stage
            from dspy.evaluate import Evaluate
            evaluator = Evaluate(devset=self.valset, metric=self.metric)
            score = evaluator(compiled)

            print(f"Score: {score:.2%}")
            self.history.append({
                'stage': stage['name'],
                'score': score,
                'optimizer': type(optimizer).__name__,
            })

            # Only keep if improvement
            if not self.history or score >= self.history[-1]['score']:
                current = compiled
                print("✓ Improvement - keeping optimized version")
            else:
                print("✗ No improvement - reverting to previous")

        return current

# Define optimization stages
trainset = [...]
valset = [...]

def accuracy(ex, pred, trace=None):
    return ex.answer.lower() in pred.answer.lower()

pipeline = OptimizationPipeline(trainset, valset, accuracy)

# Progressive optimization strategy
stages = [
    {
        'name': 'Quick bootstrap',
        'optimizer': dspy.BootstrapFewShot(metric=accuracy),
        'use_val': False,
    },
    {
        'name': 'Medium optimization',
        'optimizer': dspy.MIPROv2(metric=accuracy, auto="light", num_candidates=5),
        'use_val': True,
    },
    {
        'name': 'Heavy optimization',
        'optimizer': dspy.MIPROv2(metric=accuracy, auto="medium", num_candidates=10),
        'use_val': True,
    },
]

program = dspy.ChainOfThought("question -> answer")
optimized = pipeline.optimize(program, stages)
```

**When to use**:
- Production systems requiring best possible accuracy
- Have budget for extensive optimization
- Want to compare optimization strategies

### Pattern 10: Optimization with Data Augmentation

```python
import dspy
from typing import List

class AugmentedOptimizer:
    """Optimize with augmented training data."""

    def __init__(self, base_optimizer, augmenter):
        self.base_optimizer = base_optimizer
        self.augmenter = augmenter

    def augment_data(self, trainset: List[dspy.Example]) -> List[dspy.Example]:
        """Augment training data."""
        augmented = list(trainset)  # Start with original

        for example in trainset:
            # Generate variations
            variations = self.augmenter(example)
            augmented.extend(variations)

        return augmented

    def compile(self, student, trainset, **kwargs):
        """Compile with augmented data."""
        print(f"Original training size: {len(trainset)}")

        augmented_trainset = self.augment_data(trainset)
        print(f"Augmented training size: {len(augmented_trainset)}")

        return self.base_optimizer.compile(
            student=student,
            trainset=augmented_trainset,
            **kwargs
        )

# Define augmenter
augmenter = dspy.ChainOfThought(
    "question, answer -> paraphrased_question, answer"
)

def augment_example(example: dspy.Example) -> List[dspy.Example]:
    """Generate paraphrased variations."""
    result = augmenter(question=example.question, answer=example.answer)

    return [
        dspy.Example(
            question=result.paraphrased_question,
            answer=example.answer
        ).with_inputs("question")
    ]

# Use augmented optimizer
base_opt = dspy.MIPROv2(metric=accuracy, auto="medium")
aug_opt = AugmentedOptimizer(base_opt, augment_example)

compiled = aug_opt.compile(student=program, trainset=trainset, valset=valset)
```

**Benefits**:
- Improve optimization with limited training data
- More robust to input variations
- Better generalization

### Pattern 11: Hyperparameter Grid Search

```python
import dspy
from itertools import product
from dspy.evaluate import Evaluate

def grid_search_optimizer(
    program,
    trainset,
    valset,
    metric,
    param_grid: dict
):
    """Grid search over optimizer hyperparameters."""

    best_score = 0.0
    best_config = None
    best_program = None

    evaluator = Evaluate(devset=valset, metric=metric, num_threads=4)

    # Generate all combinations
    keys = param_grid.keys()
    values = param_grid.values()

    for combo in product(*values):
        config = dict(zip(keys, combo))
        print(f"\nTrying config: {config}")

        # Create optimizer with config
        optimizer = dspy.MIPROv2(
            metric=metric,
            auto=config.get('auto', 'light'),
            num_candidates=config.get('num_candidates', 10),
        )

        # Compile
        compiled = optimizer.compile(
            student=program,
            trainset=trainset,
            valset=valset,
            max_bootstrapped_demos=config.get('max_demos', 4),
        )

        # Evaluate
        score = evaluator(compiled)
        print(f"Score: {score:.2%}")

        if score > best_score:
            best_score = score
            best_config = config
            best_program = compiled
            print("✓ New best!")

    print(f"\n=== Best Configuration ===")
    print(f"Config: {best_config}")
    print(f"Score: {best_score:.2%}")

    return best_program, best_config, best_score

# Define search space
param_grid = {
    'auto': ['light', 'medium'],
    'num_candidates': [5, 10, 20],
    'max_demos': [2, 4, 6],
}

# Run grid search
program = dspy.ChainOfThought("question -> answer")
best_program, best_config, best_score = grid_search_optimizer(
    program=program,
    trainset=trainset,
    valset=valset,
    metric=accuracy,
    param_grid=param_grid
)
```

**When to use**:
- Have computational budget for search
- Optimize critical production systems
- Unknown optimal hyperparameters

---

## Production Considerations

### Deployment Strategy

**Pre-compilation workflow**:
```bash
# 1. Optimize offline
python optimize_program.py --output optimized_v1.json

# 2. Version control optimized prompts
git add models/optimized_v1.json
git commit -m "Add optimized model v1"

# 3. Load in production (no re-optimization)
python -c "
import dspy
program = dspy.ChainOfThought('question -> answer')
program.load('models/optimized_v1.json')
"
```

**Never optimize in production**:
- Optimization is expensive (time, API calls, compute)
- Results are non-deterministic
- May degrade performance unexpectedly
- Version control is impossible

### Monitoring Optimized Programs

```python
import dspy
import logging
from datetime import datetime
from typing import Dict

class MonitoredProgram(dspy.Module):
    """Wrapper for production monitoring."""

    def __init__(self, program: dspy.Module, version: str):
        super().__init__()
        self.program = program
        self.version = version
        self.metrics = {
            'total_calls': 0,
            'successes': 0,
            'failures': 0,
        }

    def forward(self, *args, **kwargs):
        self.metrics['total_calls'] += 1
        start_time = datetime.now()

        try:
            result = self.program(*args, **kwargs)
            self.metrics['successes'] += 1

            latency = (datetime.now() - start_time).total_seconds()
            logging.info(f"Success (v{self.version}): {latency:.2f}s")

            return result

        except Exception as e:
            self.metrics['failures'] += 1
            logging.error(f"Failure (v{self.version}): {str(e)}")
            raise

    def get_stats(self) -> Dict:
        """Get performance statistics."""
        total = self.metrics['total_calls']
        if total == 0:
            success_rate = 0.0
        else:
            success_rate = self.metrics['successes'] / total

        return {
            'version': self.version,
            'total_calls': total,
            'success_rate': success_rate,
            'failures': self.metrics['failures'],
        }

# Load optimized program
program = dspy.ChainOfThought("question -> answer")
program.load("models/optimized_v2.json")

# Wrap for monitoring
monitored = MonitoredProgram(program, version="v2")

# Use in production
result = monitored(question="What is DSPy?")

# Check stats periodically
print(monitored.get_stats())
```

### A/B Testing Optimizations

```python
import dspy
import random
from typing import Dict

class ABTestFramework:
    """A/B test multiple optimized versions."""

    def __init__(self, variants: Dict[str, dspy.Module], weights: Dict[str, float]):
        self.variants = variants
        self.weights = weights
        self.stats = {name: {'calls': 0, 'successes': 0} for name in variants}

    def select_variant(self) -> tuple[str, dspy.Module]:
        """Select variant based on weights."""
        names = list(self.variants.keys())
        weights = [self.weights[name] for name in names]

        name = random.choices(names, weights=weights)[0]
        return name, self.variants[name]

    def __call__(self, *args, **kwargs):
        variant_name, variant = self.select_variant()
        self.stats[variant_name]['calls'] += 1

        try:
            result = variant(*args, **kwargs)
            self.stats[variant_name]['successes'] += 1
            return result
        except Exception as e:
            # Log error but don't update success count
            raise

    def get_performance(self) -> Dict:
        """Get variant performance."""
        perf = {}
        for name, stats in self.stats.items():
            if stats['calls'] > 0:
                perf[name] = {
                    'calls': stats['calls'],
                    'success_rate': stats['successes'] / stats['calls'],
                }
            else:
                perf[name] = {'calls': 0, 'success_rate': 0.0}
        return perf

# Load variants
baseline = dspy.ChainOfThought("question -> answer")
baseline.load("models/baseline.json")

optimized_v1 = dspy.ChainOfThought("question -> answer")
optimized_v1.load("models/optimized_v1.json")

optimized_v2 = dspy.ChainOfThought("question -> answer")
optimized_v2.load("models/optimized_v2.json")

# Set up A/B test (70% baseline, 15% v1, 15% v2)
ab_test = ABTestFramework(
    variants={
        'baseline': baseline,
        'optimized_v1': optimized_v1,
        'optimized_v2': optimized_v2,
    },
    weights={
        'baseline': 0.70,
        'optimized_v1': 0.15,
        'optimized_v2': 0.15,
    }
)

# Use in production
result = ab_test(question="What is DSPy?")

# Analyze after N calls
if sum(s['calls'] for s in ab_test.stats.values()) >= 1000:
    print(ab_test.get_performance())
    # Decide winner, adjust weights, or promote to 100%
```

### Cost Tracking

```python
import dspy
from dataclasses import dataclass
from typing import Optional

@dataclass
class OptimizationCost:
    """Track optimization costs."""
    total_prompts: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def add_call(self, input_tokens: int, output_tokens: int, model: str):
        """Track API call cost."""
        self.total_prompts += 1
        self.total_tokens += input_tokens + output_tokens

        # Rough cost estimates (as of 2025)
        costs = {
            'gpt-4o-mini': {'input': 0.15 / 1e6, 'output': 0.60 / 1e6},
            'gpt-4o': {'input': 2.50 / 1e6, 'output': 10.00 / 1e6},
            'claude-3-5-sonnet': {'input': 3.00 / 1e6, 'output': 15.00 / 1e6},
        }

        if model in costs:
            cost = (
                input_tokens * costs[model]['input'] +
                output_tokens * costs[model]['output']
            )
            self.estimated_cost_usd += cost

class CostAwareOptimizer:
    """Wrapper to track optimization costs."""

    def __init__(self, optimizer, model_name: str):
        self.optimizer = optimizer
        self.model_name = model_name
        self.cost = OptimizationCost()

    def compile(self, student, trainset, **kwargs):
        """Compile with cost tracking."""
        # Estimate: ~10 tokens/input, ~100 tokens/output per example
        # Multiple rounds depending on optimizer

        if isinstance(self.optimizer, dspy.BootstrapFewShot):
            rounds = 1
        elif isinstance(self.optimizer, dspy.MIPROv2):
            rounds = kwargs.get('num_candidates', 10) * 2
        else:
            rounds = 5

        for _ in range(len(trainset) * rounds):
            self.cost.add_call(
                input_tokens=200,
                output_tokens=150,
                model=self.model_name
            )

        print(f"\n=== Optimization Cost Estimate ===")
        print(f"Total prompts: {self.cost.total_prompts}")
        print(f"Total tokens: {self.cost.total_tokens:,}")
        print(f"Estimated cost: ${self.cost.estimated_cost_usd:.2f}")

        return self.optimizer.compile(student=student, trainset=trainset, **kwargs)

# Use cost-aware optimizer
base_optimizer = dspy.MIPROv2(metric=accuracy, auto="medium", num_candidates=10)
cost_aware = CostAwareOptimizer(base_optimizer, model_name="gpt-4o-mini")

compiled = cost_aware.compile(student=program, trainset=trainset, valset=valset)
```

### Best Practices Checklist

```
Optimization:
✅ DO: Optimize offline, deploy compiled programs
✅ DO: Use separate train/val/test splits
✅ DO: Version control optimized programs (git)
✅ DO: Track optimization costs and set budgets
✅ DO: Start with BootstrapFewShot for fast iteration
✅ DO: Save intermediate optimization results

Production:
✅ DO: Load pre-compiled programs (never optimize in prod)
✅ DO: Monitor success rates and latency
✅ DO: A/B test optimization improvements
✅ DO: Have rollback plan for failed optimizations
✅ DO: Log variant performance for analysis

Scaling:
✅ DO: Use Modal for large-scale optimization runs
✅ DO: Cache optimization results
✅ DO: Parallelize evaluation where possible
✅ DO: Set timeouts for optimization jobs

❌ DON'T: Optimize in production (too expensive)
❌ DON'T: Skip version control for optimized prompts
❌ DON'T: Deploy without A/B testing first
❌ DON'T: Ignore cost tracking during optimization
❌ DON'T: Use test set for optimization (data leakage)
```

---

## Related Skills

### Core DSPy Skills
- `dspy-evaluation.md` - Evaluating DSPy programs with metrics
- `dspy-modules.md` - Modules to optimize
- `dspy-signatures.md` - Signatures affected by optimization
- `dspy-setup.md` - LM configuration for optimization

### Advanced DSPy Skills
- `dspy-agents.md` - Optimizing agent systems
- `dspy-multi-agent.md` - Multi-agent optimization strategies
- `dspy-production.md` - Production deployment of optimized programs
- `dspy-testing.md` - Testing optimization improvements
- `dspy-debugging.md` - Debugging optimization failures
- `dspy-compilation.md` - Understanding compilation process
- `dspy-advanced-patterns.md` - Advanced optimization patterns

### Infrastructure Skills
- `modal-functions-basics.md` - Running optimization on Modal
- `modal-gpu-workloads.md` - GPU optimization for large-scale training
- `llm-dataset-preparation.md` - Preparing training datasets

### Resources
- `resources/dspy/level2-optimization.md` - Optimization deep dive
- `resources/dspy/level3-production.md` - Production optimization guide
- `resources/dspy/optimization-cookbook.md` - Optimization recipes

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
