---
name: dspy-compilation
description: Advanced compilation patterns for DSPy including custom compilers, multi-stage optimization, and compilation pipelines
---

# DSPy Compilation

**Scope**: Program transformation, custom compilers, optimization pipelines, multi-stage compilation, compilation caching
**Lines**: ~500
**Last Updated**: 2025-10-30

## When to Use This Skill

Activate this skill when:
- Building custom optimization strategies beyond built-in teleprompters
- Creating domain-specific compilation pipelines
- Implementing multi-stage optimization workflows
- Developing intermediate representations for DSPy programs
- Optimizing across multiple modules simultaneously
- Creating reusable compilation artifacts
- Implementing incremental compilation
- Building compilation caching systems

## Core Concepts

### What is Compilation in DSPy?

**Definition**: Compilation transforms a DSPy program into an optimized version

**Transformation types**:
- **Prompt optimization**: Improve prompt templates
- **Example selection**: Choose best few-shot examples
- **Parameter tuning**: Adjust model weights (if applicable)
- **Structure optimization**: Reorganize module composition
- **Ensemble creation**: Combine multiple strategies

**DSPy compilation stages**:
1. **Parse**: Analyze program structure
2. **Collect**: Gather training data
3. **Optimize**: Apply optimization strategy
4. **Validate**: Test optimized program
5. **Serialize**: Save compiled artifacts

### Built-in vs Custom Compilers

**Built-in teleprompters**:
- `BootstrapFewShot` - Few-shot learning
- `BootstrapFewShotWithRandomSearch` - Random search over examples
- `MIPRO` - Multi-stage optimization
- `COPRO` - Coordinate ascent prompt optimization

**Custom compilers** for:
- Domain-specific optimization
- Novel optimization algorithms
- Complex multi-module systems
- Specialized constraints
- Integration with external systems

### Compilation Pipeline Architecture

**Modular compilation**:
```
Program → Analyzer → Optimizer → Validator → Serializer → Optimized Program
```

**Multi-stage compilation**:
```
Stage 1: Coarse optimization (fast, broad search)
Stage 2: Fine tuning (slower, focused search)
Stage 3: Ensemble (combine best variants)
```

---

## Patterns

### Pattern 1: Basic Custom Compiler

```python
import dspy
from typing import List, Dict

class SimpleCompiler:
    """Basic custom compiler for DSPy programs."""

    def __init__(self, metric):
        """
        Args:
            metric: Function to evaluate program quality
        """
        self.metric = metric

    def compile(
        self,
        program: dspy.Module,
        trainset: List[dspy.Example],
        num_trials: int = 10,
    ):
        """Compile program using simple random search."""
        best_program = None
        best_score = float('-inf')

        print(f"Compiling with {num_trials} trials...")

        for trial in range(num_trials):
            # Create program variant (simplified - normally modify prompts/examples)
            variant = program.deepcopy()

            # Evaluate on training set
            scores = []
            for example in trainset:
                try:
                    prediction = variant(**example.inputs())
                    score = self.metric(example, prediction)
                    scores.append(score)
                except Exception as e:
                    print(f"Trial {trial} failed: {e}")
                    scores.append(0.0)

            avg_score = sum(scores) / len(scores) if scores else 0.0

            print(f"Trial {trial}: score = {avg_score:.3f}")

            # Update best
            if avg_score > best_score:
                best_score = avg_score
                best_program = variant

        print(f"\nBest score: {best_score:.3f}")
        return best_program

# Usage
def accuracy_metric(example, prediction):
    """Simple accuracy metric."""
    return float(example.answer.lower() in prediction.answer.lower())

# Create training data
trainset = [
    dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
    dspy.Example(question="What is 3+3?", answer="6").with_inputs("question"),
    dspy.Example(question="What is 5+5?", answer="10").with_inputs("question"),
]

# Configure LM
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create program
program = dspy.ChainOfThought("question -> answer")

# Compile
compiler = SimpleCompiler(metric=accuracy_metric)
optimized_program = compiler.compile(program, trainset, num_trials=5)

# Test optimized program
test_result = optimized_program(question="What is 7+7?")
print(f"Test result: {test_result.answer}")
```

**When to use**:
- Learning compilation basics
- Simple optimization needs
- Prototyping new compilers
- Debugging compilation issues

### Pattern 2: Multi-Stage Compilation Pipeline

```python
import dspy
from typing import List, Callable

class CompilationStage:
    """Single compilation stage."""

    def __init__(
        self,
        name: str,
        optimizer: Callable,
        metric: Callable,
        budget: int,
    ):
        self.name = name
        self.optimizer = optimizer
        self.metric = metric
        self.budget = budget

class MultiStageCompiler:
    """Multi-stage compilation pipeline."""

    def __init__(self, stages: List[CompilationStage]):
        self.stages = stages
        self.compilation_history = []

    def compile(
        self,
        program: dspy.Module,
        trainset: List[dspy.Example],
        valset: List[dspy.Example] = None,
    ):
        """Execute multi-stage compilation."""
        current_program = program
        valset = valset or trainset

        for i, stage in enumerate(self.stages):
            print(f"\n{'='*80}")
            print(f"Stage {i+1}: {stage.name}")
            print("="*80)

            # Run stage optimizer
            try:
                optimized = stage.optimizer(
                    program=current_program,
                    trainset=trainset,
                    metric=stage.metric,
                    budget=stage.budget,
                )

                # Evaluate on validation set
                val_scores = []
                for example in valset:
                    pred = optimized(**example.inputs())
                    score = stage.metric(example, pred)
                    val_scores.append(score)

                avg_score = sum(val_scores) / len(val_scores)
                print(f"Stage {i+1} validation score: {avg_score:.3f}")

                # Record history
                self.compilation_history.append({
                    "stage": stage.name,
                    "score": avg_score,
                    "program": optimized,
                })

                current_program = optimized

            except Exception as e:
                print(f"Stage {i+1} failed: {e}")
                print("Using previous program")

        return current_program

    def get_best_program(self):
        """Get best program from compilation history."""
        if not self.compilation_history:
            return None

        best = max(self.compilation_history, key=lambda x: x["score"])
        return best["program"]

# Define stage optimizers
def coarse_optimizer(program, trainset, metric, budget):
    """Fast, broad search optimizer."""
    # Use built-in BootstrapFewShot for coarse optimization
    optimizer = dspy.BootstrapFewShot(metric=metric, max_bootstrapped_demos=2)
    return optimizer.compile(program, trainset=trainset[:budget])

def fine_optimizer(program, trainset, metric, budget):
    """Slower, focused optimizer."""
    # Use more examples and iterations
    optimizer = dspy.BootstrapFewShot(metric=metric, max_bootstrapped_demos=5)
    return optimizer.compile(program, trainset=trainset[:budget])

def ensemble_optimizer(program, trainset, metric, budget):
    """Create ensemble of best variants."""
    # Simplified - normally would create actual ensemble
    return program

# Create pipeline
stages = [
    CompilationStage(
        name="Coarse Search",
        optimizer=coarse_optimizer,
        metric=lambda ex, pred: float(ex.answer in pred.answer),
        budget=10,
    ),
    CompilationStage(
        name="Fine Tuning",
        optimizer=fine_optimizer,
        metric=lambda ex, pred: float(ex.answer in pred.answer),
        budget=20,
    ),
]

# Compile
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

trainset = [
    dspy.Example(question=f"What is {i}+{i}?", answer=str(i*2)).with_inputs("question")
    for i in range(1, 11)
]

program = dspy.ChainOfThought("question -> answer")

compiler = MultiStageCompiler(stages)
optimized = compiler.compile(program, trainset)

# Get best program from all stages
best = compiler.get_best_program()
```

**Benefits**:
- Progressive refinement
- Different optimization strategies per stage
- Better final quality
- Controllable computation budget

**When to use**:
- Complex optimization problems
- Large training sets
- Production deployments
- Research experiments

### Pattern 3: Compilation Caching

```python
import dspy
import hashlib
import json
import pickle
from pathlib import Path
from typing import List, Optional

class CachedCompiler:
    """Compiler with caching support."""

    def __init__(
        self,
        base_compiler,
        cache_dir: str = ".dspy_cache",
    ):
        self.base_compiler = base_compiler
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _compute_cache_key(
        self,
        program: dspy.Module,
        trainset: List[dspy.Example],
        config: dict,
    ) -> str:
        """Compute cache key from inputs."""
        # Serialize inputs
        program_str = str(program.__class__.__name__)
        trainset_str = json.dumps([
            {**ex.inputs(), **ex.labels()}
            for ex in trainset
        ], sort_keys=True)
        config_str = json.dumps(config, sort_keys=True)

        # Hash
        combined = f"{program_str}:{trainset_str}:{config_str}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path."""
        return self.cache_dir / f"{cache_key}.pkl"

    def _load_from_cache(self, cache_key: str) -> Optional[dspy.Module]:
        """Load compiled program from cache."""
        cache_path = self._get_cache_path(cache_key)

        if cache_path.exists():
            print(f"Loading from cache: {cache_key[:8]}...")
            with open(cache_path, "rb") as f:
                return pickle.load(f)

        return None

    def _save_to_cache(self, cache_key: str, program: dspy.Module):
        """Save compiled program to cache."""
        cache_path = self._get_cache_path(cache_key)
        print(f"Saving to cache: {cache_key[:8]}...")

        with open(cache_path, "wb") as f:
            pickle.dump(program, f)

    def compile(
        self,
        program: dspy.Module,
        trainset: List[dspy.Example],
        config: dict = None,
        force_recompile: bool = False,
    ):
        """Compile with caching."""
        config = config or {}

        # Compute cache key
        cache_key = self._compute_cache_key(program, trainset, config)

        # Try cache first
        if not force_recompile:
            cached_program = self._load_from_cache(cache_key)
            if cached_program is not None:
                return cached_program

        # Cache miss - compile
        print("Cache miss - compiling...")
        optimized = self.base_compiler.compile(
            program=program,
            trainset=trainset,
            **config,
        )

        # Save to cache
        self._save_to_cache(cache_key, optimized)

        return optimized

    def clear_cache(self):
        """Clear compilation cache."""
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
        print(f"Cache cleared: {self.cache_dir}")

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create base compiler
def simple_metric(example, prediction):
    return float(example.answer in prediction.answer)

base_compiler = dspy.BootstrapFewShot(metric=simple_metric)

# Wrap with caching
cached_compiler = CachedCompiler(base_compiler, cache_dir=".dspy_cache")

# Create training data
trainset = [
    dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
    dspy.Example(question="What is 3+3?", answer="6").with_inputs("question"),
]

# First compilation - cache miss
program = dspy.ChainOfThought("question -> answer")
optimized1 = cached_compiler.compile(program, trainset)

# Second compilation - cache hit (instant)
program2 = dspy.ChainOfThought("question -> answer")
optimized2 = cached_compiler.compile(program2, trainset)

# Clear cache
# cached_compiler.clear_cache()
```

**Benefits**:
- Avoid expensive recompilation
- Fast iteration during development
- Share compiled programs across team
- Consistent results

**When to use**:
- Development workflows
- CI/CD pipelines
- Shared development environments
- Expensive compilation

### Pattern 4: Incremental Compilation

```python
import dspy
from typing import List, Dict, Set

class IncrementalCompiler:
    """Compiler that only recompiles changed modules."""

    def __init__(self, base_compiler):
        self.base_compiler = base_compiler
        self.module_cache: Dict[str, dspy.Module] = {}
        self.module_signatures: Dict[str, str] = {}

    def _compute_module_signature(self, module: dspy.Module) -> str:
        """Compute signature for module (simplified)."""
        return f"{module.__class__.__name__}:{str(module)}"

    def _has_module_changed(self, module_name: str, module: dspy.Module) -> bool:
        """Check if module has changed since last compilation."""
        current_sig = self._compute_module_signature(module)

        if module_name not in self.module_signatures:
            return True

        return self.module_signatures[module_name] != current_sig

    def compile(
        self,
        program: dspy.Module,
        trainset: List[dspy.Example],
        module_map: Dict[str, dspy.Module],
    ):
        """Incrementally compile only changed modules."""
        changed_modules: Set[str] = set()
        unchanged_modules: Set[str] = set()

        print("Analyzing module changes...")

        # Check which modules changed
        for name, module in module_map.items():
            if self._has_module_changed(name, module):
                changed_modules.add(name)
                print(f"  {name}: CHANGED")
            else:
                unchanged_modules.add(name)
                print(f"  {name}: unchanged")

        # Recompile only changed modules
        if changed_modules:
            print(f"\nRecompiling {len(changed_modules)} changed modules...")

            for name in changed_modules:
                module = module_map[name]

                # Compile module
                optimized = self.base_compiler.compile(
                    program=module,
                    trainset=trainset,
                )

                # Update cache
                self.module_cache[name] = optimized
                self.module_signatures[name] = self._compute_module_signature(module)

                print(f"  {name}: compiled")

        else:
            print("\nNo changes detected - using cached compilation")

        # Reconstruct program with optimized modules
        optimized_program = self._reconstruct_program(program, module_map)

        return optimized_program

    def _reconstruct_program(
        self,
        program: dspy.Module,
        module_map: Dict[str, dspy.Module],
    ) -> dspy.Module:
        """Reconstruct program with cached optimized modules."""
        # Simplified - in practice would properly reconstruct
        # using self.module_cache
        return program

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create base compiler
base_compiler = dspy.BootstrapFewShot(
    metric=lambda ex, pred: float(ex.answer in pred.answer),
)

# Create incremental compiler
incremental_compiler = IncrementalCompiler(base_compiler)

# Define modules
module_a = dspy.Predict("question -> answer")
module_b = dspy.ChainOfThought("question -> reasoning, answer")

module_map = {
    "module_a": module_a,
    "module_b": module_b,
}

trainset = [
    dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
]

# First compilation - all modules compiled
program = dspy.ChainOfThought("question -> answer")
optimized1 = incremental_compiler.compile(program, trainset, module_map)

# Second compilation - only changed modules compiled
# (if module_map unchanged, uses cache)
optimized2 = incremental_compiler.compile(program, trainset, module_map)
```

**Benefits**:
- Faster recompilation
- Efficient development workflow
- Selective optimization
- Reduced computation cost

### Pattern 5: Cross-Module Optimization

```python
import dspy
from typing import List, Dict, Tuple

class CrossModuleOptimizer:
    """Optimize multiple modules jointly."""

    def __init__(self, metric):
        self.metric = metric

    def compile(
        self,
        modules: Dict[str, dspy.Module],
        trainset: List[dspy.Example],
        dependencies: List[Tuple[str, str]],
    ):
        """Jointly optimize modules considering dependencies."""
        print("Analyzing module dependencies...")
        self._print_dependencies(dependencies)

        # Topological sort of modules by dependencies
        sorted_modules = self._topological_sort(modules, dependencies)

        print(f"\nOptimization order: {' -> '.join(sorted_modules)}")

        # Optimize in dependency order
        optimized_modules = {}

        for module_name in sorted_modules:
            print(f"\nOptimizing {module_name}...")
            module = modules[module_name]

            # Get upstream optimized modules
            upstream_modules = {
                name: optimized_modules[name]
                for name in optimized_modules
                if (name, module_name) in dependencies
            }

            # Optimize considering upstream context
            optimized = self._optimize_module(
                module=module,
                trainset=trainset,
                upstream_modules=upstream_modules,
            )

            optimized_modules[module_name] = optimized

        return optimized_modules

    def _topological_sort(
        self,
        modules: Dict[str, dspy.Module],
        dependencies: List[Tuple[str, str]],
    ) -> List[str]:
        """Sort modules by dependencies."""
        # Simplified topological sort
        from collections import defaultdict, deque

        in_degree = defaultdict(int)
        graph = defaultdict(list)

        for from_module, to_module in dependencies:
            graph[from_module].append(to_module)
            in_degree[to_module] += 1

        # Ensure all modules in graph
        for module_name in modules:
            if module_name not in in_degree:
                in_degree[module_name] = 0

        # BFS topological sort
        queue = deque([name for name in modules if in_degree[name] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def _optimize_module(
        self,
        module: dspy.Module,
        trainset: List[dspy.Example],
        upstream_modules: Dict[str, dspy.Module],
    ):
        """Optimize single module considering upstream context."""
        # Simplified - use standard optimization
        optimizer = dspy.BootstrapFewShot(metric=self.metric)
        return optimizer.compile(module, trainset=trainset[:5])

    def _print_dependencies(self, dependencies: List[Tuple[str, str]]):
        """Print module dependencies."""
        print("Dependencies:")
        for from_mod, to_mod in dependencies:
            print(f"  {from_mod} -> {to_mod}")

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Define modules
modules = {
    "decompose": dspy.Predict("question -> sub_questions: list[str]"),
    "answer": dspy.ChainOfThought("question -> answer"),
    "synthesize": dspy.Predict("answers: list[str] -> final_answer: str"),
}

# Define dependencies
dependencies = [
    ("decompose", "answer"),      # answer depends on decompose
    ("answer", "synthesize"),     # synthesize depends on answer
]

trainset = [
    dspy.Example(
        question="Compare Python and JavaScript",
        sub_questions=["What is Python?", "What is JavaScript?"],
        answer="...",
        final_answer="...",
    ).with_inputs("question"),
]

# Optimize jointly
metric = lambda ex, pred: 1.0  # Simplified metric
optimizer = CrossModuleOptimizer(metric=metric)
optimized_modules = optimizer.compile(modules, trainset, dependencies)

print("\nOptimized modules:")
for name in optimized_modules:
    print(f"  {name}: optimized")
```

**Benefits**:
- Consider module interactions
- Optimize end-to-end performance
- Respect data dependencies
- Better final quality

### Pattern 6: Compilation Validation

```python
import dspy
from typing import List, Dict, Callable

class ValidatedCompiler:
    """Compiler with extensive validation."""

    def __init__(self, base_compiler, validators: List[Callable]):
        self.base_compiler = base_compiler
        self.validators = validators

    def compile(
        self,
        program: dspy.Module,
        trainset: List[dspy.Example],
        valset: List[dspy.Example] = None,
    ):
        """Compile with validation."""
        print("Compiling program...")
        optimized = self.base_compiler.compile(program, trainset=trainset)

        print("\nValidating compiled program...")
        valset = valset or trainset

        validation_results = {}

        for i, validator in enumerate(self.validators):
            validator_name = validator.__name__
            print(f"\nValidator {i+1}: {validator_name}")

            try:
                result = validator(optimized, valset)
                validation_results[validator_name] = result

                if result["passed"]:
                    print(f"  ✓ PASSED: {result.get('message', '')}")
                else:
                    print(f"  ✗ FAILED: {result.get('message', '')}")

            except Exception as e:
                print(f"  ✗ ERROR: {e}")
                validation_results[validator_name] = {
                    "passed": False,
                    "error": str(e),
                }

        # Check if all validators passed
        all_passed = all(r["passed"] for r in validation_results.values())

        if all_passed:
            print("\n✓ All validations passed!")
            return optimized
        else:
            print("\n✗ Some validations failed")
            raise ValueError(f"Validation failed: {validation_results}")

# Define validators
def accuracy_validator(program, valset) -> Dict:
    """Validate accuracy on validation set."""
    correct = 0
    for example in valset:
        pred = program(**example.inputs())
        if example.answer.lower() in pred.answer.lower():
            correct += 1

    accuracy = correct / len(valset)

    return {
        "passed": accuracy >= 0.7,  # 70% threshold
        "message": f"Accuracy: {accuracy:.1%}",
        "accuracy": accuracy,
    }

def latency_validator(program, valset) -> Dict:
    """Validate latency requirements."""
    import time

    latencies = []
    for example in valset[:5]:  # Sample
        start = time.time()
        program(**example.inputs())
        latency = time.time() - start
        latencies.append(latency)

    avg_latency = sum(latencies) / len(latencies)

    return {
        "passed": avg_latency < 5.0,  # 5s threshold
        "message": f"Avg latency: {avg_latency:.2f}s",
        "latency": avg_latency,
    }

def consistency_validator(program, valset) -> Dict:
    """Validate output consistency (temperature=0)."""
    for example in valset[:3]:  # Sample
        pred1 = program(**example.inputs())
        pred2 = program(**example.inputs())

        if pred1.answer != pred2.answer:
            return {
                "passed": False,
                "message": "Inconsistent outputs detected",
            }

    return {
        "passed": True,
        "message": "Outputs consistent",
    }

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

trainset = [
    dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
    dspy.Example(question="What is 3+3?", answer="6").with_inputs("question"),
]

base_compiler = dspy.BootstrapFewShot(
    metric=lambda ex, pred: float(ex.answer in pred.answer),
)

# Create validated compiler
validated_compiler = ValidatedCompiler(
    base_compiler=base_compiler,
    validators=[
        accuracy_validator,
        latency_validator,
        consistency_validator,
    ],
)

# Compile with validation
program = dspy.ChainOfThought("question -> answer")
try:
    optimized = validated_compiler.compile(program, trainset)
    print("\nCompilation successful!")
except ValueError as e:
    print(f"\nCompilation failed: {e}")
```

**Validators to include**:
- Accuracy threshold
- Latency requirements
- Output consistency
- Format compliance
- Cost constraints
- Safety checks

### Pattern 7: Compilation Visualization

```python
import dspy
from typing import List, Dict
import json

class VisualizingCompiler:
    """Compiler that visualizes optimization process."""

    def __init__(self, base_compiler):
        self.base_compiler = base_compiler
        self.optimization_history = []

    def compile(
        self,
        program: dspy.Module,
        trainset: List[dspy.Example],
        metric,
    ):
        """Compile with visualization."""
        print("Starting compilation...\n")

        # Baseline evaluation
        baseline_score = self._evaluate(program, trainset, metric)
        self._record_iteration(0, baseline_score, "baseline")

        # Run optimization
        optimized = self.base_compiler.compile(
            program=program,
            trainset=trainset,
        )

        # Final evaluation
        final_score = self._evaluate(optimized, trainset, metric)
        self._record_iteration(1, final_score, "optimized")

        # Generate visualization
        self._visualize()

        return optimized

    def _evaluate(
        self,
        program: dspy.Module,
        dataset: List[dspy.Example],
        metric,
    ) -> float:
        """Evaluate program on dataset."""
        scores = []
        for example in dataset:
            try:
                pred = program(**example.inputs())
                score = metric(example, pred)
                scores.append(score)
            except Exception:
                scores.append(0.0)

        return sum(scores) / len(scores) if scores else 0.0

    def _record_iteration(self, iteration: int, score: float, label: str):
        """Record optimization iteration."""
        self.optimization_history.append({
            "iteration": iteration,
            "score": score,
            "label": label,
        })

    def _visualize(self):
        """Visualize optimization history."""
        print("\n" + "="*80)
        print("COMPILATION RESULTS")
        print("="*80)

        for entry in self.optimization_history:
            bar_length = int(entry["score"] * 50)
            bar = "█" * bar_length
            print(f"{entry['label']:15} | {bar} {entry['score']:.2%}")

        baseline = self.optimization_history[0]["score"]
        final = self.optimization_history[-1]["score"]
        improvement = ((final - baseline) / baseline * 100) if baseline > 0 else 0

        print(f"\nImprovement: {improvement:+.1f}%")
        print("="*80)

    def save_history(self, filepath: str):
        """Save optimization history."""
        with open(filepath, "w") as f:
            json.dump(self.optimization_history, f, indent=2)

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

trainset = [
    dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
    dspy.Example(question="What is 3+3?", answer="6").with_inputs("question"),
]

metric = lambda ex, pred: float(ex.answer in pred.answer)

base_compiler = dspy.BootstrapFewShot(metric=metric)
viz_compiler = VisualizingCompiler(base_compiler)

program = dspy.ChainOfThought("question -> answer")
optimized = viz_compiler.compile(program, trainset, metric)

# Save history
viz_compiler.save_history("compilation_history.json")
```

**Visualization types**:
- Score progression charts
- Before/after comparisons
- Performance heatmaps
- Cost analysis graphs

### Pattern 8: Distributed Compilation

```python
import dspy
from typing import List
from concurrent.futures import ProcessPoolExecutor, as_completed

class DistributedCompiler:
    """Compile program variants in parallel."""

    def __init__(self, base_compiler, num_workers: int = 4):
        self.base_compiler = base_compiler
        self.num_workers = num_workers

    def compile(
        self,
        program: dspy.Module,
        trainset: List[dspy.Example],
        num_variants: int = 10,
    ):
        """Compile multiple variants in parallel."""
        print(f"Compiling {num_variants} variants using {self.num_workers} workers...")

        # Create compilation tasks
        tasks = [
            (program, trainset, i)
            for i in range(num_variants)
        ]

        # Execute in parallel
        best_program = None
        best_score = float('-inf')

        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit tasks
            futures = {
                executor.submit(self._compile_variant, task): task
                for task in tasks
            }

            # Collect results
            for future in as_completed(futures):
                task = futures[future]
                variant_id = task[2]

                try:
                    optimized, score = future.result()
                    print(f"Variant {variant_id}: score = {score:.3f}")

                    if score > best_score:
                        best_score = score
                        best_program = optimized

                except Exception as e:
                    print(f"Variant {variant_id} failed: {e}")

        print(f"\nBest score: {best_score:.3f}")
        return best_program

    def _compile_variant(self, task):
        """Compile single variant (runs in separate process)."""
        program, trainset, variant_id = task

        # Re-configure LM in subprocess
        lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
        dspy.configure(lm=lm)

        # Compile
        optimized = self.base_compiler.compile(
            program=program,
            trainset=trainset,
        )

        # Evaluate
        metric = lambda ex, pred: float(ex.answer in pred.answer)
        score = sum(
            metric(ex, optimized(**ex.inputs()))
            for ex in trainset
        ) / len(trainset)

        return optimized, score

# Note: This is a simplified example. In practice, need to handle
# serialization of DSPy modules properly for multiprocessing.
```

**Benefits**:
- Faster compilation
- Explore more variants
- Better final quality
- Efficient resource use

**Considerations**:
- Serialization overhead
- Memory per worker
- API rate limits
- Result aggregation

---

## Quick Reference

### Compilation Checklist

```
Before compilation:
✅ Prepare training dataset
✅ Define evaluation metric
✅ Set optimization budget
✅ Configure validation set

During compilation:
✅ Monitor optimization progress
✅ Track scores per iteration
✅ Watch for overfitting
✅ Validate on held-out set

After compilation:
✅ Save compiled program
✅ Document optimization results
✅ Test on new examples
✅ Measure improvements
```

### Common Compilation Metrics

```python
# Exact match
exact_match = lambda ex, pred: float(ex.answer == pred.answer)

# Contains match
contains = lambda ex, pred: float(ex.answer in pred.answer)

# F1 score
def f1_score(ex, pred):
    # Implementation...
    pass

# Custom domain metric
def domain_metric(ex, pred):
    # Domain-specific logic
    pass
```

### Compilation Commands

```python
# Basic compilation
optimized = compiler.compile(program, trainset)

# With validation
optimized = compiler.compile(program, trainset, valset=valset)

# Save/load compiled program
optimized.save("optimized_program.json")
program.load("optimized_program.json")
```

---

## Anti-Patterns

❌ **No validation set**: Overfitting to training data
```python
# Bad
optimized = compiler.compile(program, trainset)
# Test on trainset - artificially high scores
```
✅ Use separate validation set:
```python
# Good
optimized = compiler.compile(program, trainset, valset=valset)
```

❌ **Ignoring compilation costs**: Expensive, wasteful
```python
# Bad - recompile on every run
optimized = compiler.compile(program, trainset)
```
✅ Cache compiled programs:
```python
# Good
if not cached:
    optimized = compiler.compile(program, trainset)
    save_cache(optimized)
else:
    optimized = load_cache()
```

❌ **No progress monitoring**: Can't debug issues
```python
# Bad
optimized = compiler.compile(program, trainset)  # Black box
```
✅ Monitor compilation:
```python
# Good
viz_compiler = VisualizingCompiler(compiler)
optimized = viz_compiler.compile(program, trainset)
# See optimization progress
```

---

## Related Skills

- `dspy-optimizers.md` - Built-in optimization strategies
- `dspy-evaluation.md` - Program evaluation
- `dspy-production.md` - Deploying compiled programs
- `dspy-testing.md` - Testing compilation results

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
