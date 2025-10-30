---
name: dspy-modules
description: Building composable prediction modules with Predict, ChainOfThought, ReAct, and custom modules
---

# DSPy Modules

**Scope**: Predict, ChainOfThought, ReAct, ProgramOfThought, custom modules, composition
**Lines**: ~450
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Building prediction pipelines with DSPy
- Choosing between Predict, ChainOfThought, and ReAct modules
- Creating custom DSPy modules
- Composing multiple modules into complex workflows
- Implementing multi-step reasoning systems
- Optimizing module selection for specific tasks

## Core Concepts

### What are Modules?

**Definition**: Modules are composable building blocks that replace hand-written prompts

**Purpose**:
- **Abstraction**: Encapsulate prompting strategies
- **Reusability**: Use same module across different tasks
- **Optimization**: Modules can be automatically tuned
- **Composition**: Chain modules for complex workflows

**Key insight**: Modules separate strategy (how to prompt) from task (what to ask)

### Built-in Module Types

**Predict**: Basic prediction
- Simplest module
- Direct signature → output mapping
- No intermediate reasoning
- Fast, efficient

**ChainOfThought**: Multi-step reasoning
- Adds reasoning step before answer
- Better for complex tasks
- Shows work/explanation
- Slightly slower but more accurate

**ReAct**: Reasoning + Acting
- Iterative thought-action-observation loops
- Can call tools/retrieve information
- Good for multi-step tasks requiring external data
- Most complex, most powerful

**ProgramOfThought**: Code generation + execution
- Generates Python code to solve problems
- Executes code for precise computations
- Excellent for math, data analysis
- Requires code execution environment

### Module Composition

**Pattern**: Small modules → Complex systems
- Each module has focused responsibility
- Modules pass data through signatures
- Compose modules in `forward()` method
- Create reusable module libraries

---

## Patterns

### Pattern 1: Basic Predict Module

```python
import dspy

# Configure LM
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

# Simple prediction
predictor = dspy.Predict("question -> answer")

# Use module
result = predictor(question="What is the capital of France?")
print(result.answer)  # "Paris"

# With typed signature
classifier = dspy.Predict("text -> category, confidence: float")
result = classifier(text="This movie was amazing!")
print(f"{result.category} ({result.confidence})")
```

**When to use**:
- Simple classification tasks
- Direct question answering
- Fast prototyping
- Tasks that don't need reasoning

### Pattern 2: ChainOfThought Module

```python
import dspy

class QASignature(dspy.Signature):
    """Answer questions with reasoning."""
    question = dspy.InputField(desc="Question to answer")
    answer = dspy.OutputField(desc="Answer to the question")

# Add chain-of-thought reasoning
cot = dspy.ChainOfThought(QASignature)

# Module automatically adds reasoning step
result = cot(question="If it takes 5 machines 5 minutes to make 5 widgets, how long for 100 machines to make 100 widgets?")

print("Reasoning:", result.reasoning)  # Shows step-by-step thinking
print("Answer:", result.answer)        # "5 minutes"
```

**When to use**:
- Complex reasoning tasks
- Math problems
- Multi-step questions
- When you need explanations

**How it works**:
- DSPy adds `reasoning` field to signature
- LM generates reasoning before answer
- More accurate for complex tasks

### Pattern 3: ReAct Module (with Tools)

```python
import dspy

class SearchQA(dspy.Signature):
    """Answer questions using search results."""
    question = dspy.InputField()
    answer = dspy.OutputField()

# Define tools that ReAct can use
def search(query: str) -> str:
    """Search for information."""
    # Implement actual search (e.g., Google, Wikipedia)
    return f"Search results for: {query}"

def calculate(expression: str) -> float:
    """Evaluate mathematical expressions."""
    return eval(expression)  # Use safely in production!

# Create ReAct module with tools
react = dspy.ReAct(
    SearchQA,
    tools=[search, calculate],
    max_iters=5,  # Maximum thought-action cycles
)

# ReAct will:
# 1. Think about the question
# 2. Decide which tool to use
# 3. Execute the tool
# 4. Observe results
# 5. Repeat until answer found

result = react(question="What is the population of the capital of France?")
print(result.answer)
```

**When to use**:
- Questions requiring external information
- Multi-step tasks with tool use
- Information retrieval + reasoning
- Agent-like behavior

**How it works**:
- Iterative Thought → Action → Observation loop
- Selects and executes tools
- Stops when answer is confident

### Pattern 4: ProgramOfThought Module

```python
import dspy

class MathProblem(dspy.Signature):
    """Solve math problems by generating Python code."""
    problem = dspy.InputField(desc="Math problem to solve")
    solution = dspy.OutputField(desc="Numerical solution")

# ProgramOfThought generates and executes code
pot = dspy.ProgramOfThought(MathProblem)

result = pot(problem="What is 15% of 240 plus 30% of 150?")

print("Code:", result.code)      # Generated Python code
print("Solution:", result.solution)  # Executed result
```

**When to use**:
- Mathematical computations
- Data analysis tasks
- Precise numerical answers
- Complex calculations

**Benefits**:
- More accurate than text-based reasoning for math
- Shows executable code
- Verifiable results

### Pattern 5: Custom Module

```python
import dspy

class RAGModule(dspy.Module):
    """Custom Retrieval-Augmented Generation module."""

    def __init__(self, num_passages=3):
        super().__init__()
        self.num_passages = num_passages

        # Sub-modules
        self.retrieve = dspy.Retrieve(k=num_passages)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        # Step 1: Retrieve relevant passages
        passages = self.retrieve(question).passages

        # Step 2: Format context
        context = "\n\n".join(passages)

        # Step 3: Generate answer with context
        result = self.generate(context=context, question=question)

        return result

# Use custom module
rag = RAGModule(num_passages=5)
result = rag(question="What is DSPy?")
print(result.answer)
```

**When to use**:
- Custom workflows not covered by built-in modules
- Complex multi-step pipelines
- Reusable domain-specific logic
- Production systems

**Structure**:
- Inherit from `dspy.Module`
- Define sub-modules in `__init__()`
- Implement `forward()` method
- Return results (or dspy.Prediction)

### Pattern 6: Module Composition

```python
import dspy

class MultiStepQA(dspy.Module):
    """Answer questions using multi-step reasoning."""

    def __init__(self):
        super().__init__()

        # Step 1: Break down question
        self.decompose = dspy.Predict("question -> sub_questions: list[str]")

        # Step 2: Answer sub-questions
        self.answer_sub = dspy.ChainOfThought("question -> answer")

        # Step 3: Synthesize final answer
        self.synthesize = dspy.ChainOfThought("question, sub_answers -> final_answer")

    def forward(self, question):
        # Decompose into sub-questions
        decomp = self.decompose(question=question)

        # Answer each sub-question
        sub_answers = []
        for sub_q in decomp.sub_questions:
            ans = self.answer_sub(question=sub_q)
            sub_answers.append(f"Q: {sub_q}\nA: {ans.answer}")

        # Synthesize final answer
        result = self.synthesize(
            question=question,
            sub_answers="\n\n".join(sub_answers)
        )

        return dspy.Prediction(
            sub_questions=decomp.sub_questions,
            sub_answers=sub_answers,
            answer=result.final_answer
        )

# Use composed module
qa = MultiStepQA()
result = qa(question="Compare and contrast Python and JavaScript")

print("Sub-questions:", result.sub_questions)
print("Final answer:", result.answer)
```

**Benefits**:
- Break complex tasks into manageable steps
- Each sub-module optimizable independently
- Clear separation of concerns
- Easier debugging

### Pattern 7: Module with Retry Logic

```python
import dspy

class RobustPredictor(dspy.Module):
    """Predictor with automatic retry on failure."""

    def __init__(self, signature, max_retries=3):
        super().__init__()
        self.predictor = dspy.ChainOfThought(signature)
        self.max_retries = max_retries

    def forward(self, **kwargs):
        last_error = None

        for attempt in range(self.max_retries):
            try:
                result = self.predictor(**kwargs)

                # Validate result (example: check if answer is non-empty)
                if hasattr(result, 'answer') and result.answer.strip():
                    return result

            except Exception as e:
                last_error = e
                print(f"Attempt {attempt + 1} failed: {e}")

        # All retries failed
        raise Exception(f"All {self.max_retries} attempts failed. Last error: {last_error}")

# Use robust predictor
predictor = RobustPredictor("question -> answer")
result = predictor(question="What is DSPy?")
```

**When to use**:
- Production systems requiring reliability
- Handling transient API failures
- Quality-critical applications

### Pattern 8: Parallel Module Execution

```python
import dspy
from concurrent.futures import ThreadPoolExecutor

class EnsemblePredictor(dspy.Module):
    """Run multiple predictors in parallel and combine results."""

    def __init__(self, signature, num_predictors=3):
        super().__init__()
        # Create multiple predictor instances
        self.predictors = [
            dspy.ChainOfThought(signature)
            for _ in range(num_predictors)
        ]
        self.vote = dspy.Predict("answers: list[str] -> best_answer: str")

    def forward(self, **kwargs):
        # Execute predictors in parallel
        with ThreadPoolExecutor(max_workers=len(self.predictors)) as executor:
            futures = [
                executor.submit(pred, **kwargs)
                for pred in self.predictors
            ]
            results = [f.result() for f in futures]

        # Extract answers
        answers = [r.answer for r in results]

        # Vote on best answer
        best = self.vote(answers=answers)

        return dspy.Prediction(
            all_answers=answers,
            answer=best.best_answer
        )

# Use ensemble
ensemble = EnsemblePredictor("question -> answer", num_predictors=5)
result = ensemble(question="What is the meaning of life?")
print("All answers:", result.all_answers)
print("Best answer:", result.answer)
```

**When to use**:
- Improve prediction quality through voting
- Reduce variance in outputs
- Critical decisions requiring consensus

---

## Advanced Patterns

### Pattern 9: Module with Caching and Memoization

```python
import dspy
from functools import lru_cache
from typing import Tuple
import hashlib

class CachedModule(dspy.Module):
    """Module with intelligent caching for expensive operations."""

    def __init__(self, cache_size=128):
        super().__init__()
        self.predictor = dspy.ChainOfThought("question -> answer")
        self.cache_size = cache_size
        self._setup_cache()

    def _setup_cache(self):
        """Setup LRU cache for predictions."""
        @lru_cache(maxsize=self.cache_size)
        def cached_predict(question_hash: str, question: str) -> str:
            result = self.predictor(question=question)
            return result.answer

        self._cached_predict = cached_predict

    def _hash_input(self, question: str) -> str:
        """Create hash of input for cache key."""
        return hashlib.md5(question.encode()).hexdigest()

    def forward(self, question):
        question_hash = self._hash_input(question)
        answer = self._cached_predict(question_hash, question)

        return dspy.Prediction(
            answer=answer,
            cached=question_hash in [
                arg[0] for arg in self._cached_predict.cache_info()._asdict().values()
            ]
        )

    def cache_stats(self):
        """Return cache statistics."""
        return self._cached_predict.cache_info()

# Usage
cached_qa = CachedModule(cache_size=256)
result1 = cached_qa(question="What is DSPy?")  # Cache miss
result2 = cached_qa(question="What is DSPy?")  # Cache hit

print(cached_qa.cache_stats())  # CacheInfo(hits=1, misses=1, ...)
```

**Benefits**:
- Avoid redundant LM calls for repeated inputs
- Significant cost reduction (60-90% with high cache hit rate)
- Reduced latency for cached queries
- Configurable cache size

### Pattern 10: Hierarchical Module Decomposition

```python
import dspy

class DocumentProcessor(dspy.Module):
    """Process documents through hierarchical pipeline."""

    def __init__(self):
        super().__init__()
        # Level 1: Document understanding
        self.extract_topics = dspy.Predict("document -> topics: list[str]")
        self.extract_entities = dspy.Predict("document -> entities: list[str]")

        # Level 2: Analysis
        self.analyze_sentiment = dspy.ChainOfThought("document, topics -> sentiment, score: float")
        self.generate_summary = dspy.ChainOfThought("document, topics, entities -> summary")

        # Level 3: Synthesis
        self.generate_report = dspy.ChainOfThought(
            "document, topics, entities, sentiment, summary -> report"
        )

    def forward(self, document):
        # Level 1: Extract features
        topics = self.extract_topics(document=document)
        entities = self.extract_entities(document=document)

        # Level 2: Analyze
        sentiment = self.analyze_sentiment(
            document=document,
            topics=", ".join(topics.topics)
        )

        summary = self.generate_summary(
            document=document,
            topics=", ".join(topics.topics),
            entities=", ".join(entities.entities)
        )

        # Level 3: Synthesize
        report = self.generate_report(
            document=document,
            topics=", ".join(topics.topics),
            entities=", ".join(entities.entities),
            sentiment=f"{sentiment.sentiment} ({sentiment.score})",
            summary=summary.summary
        )

        return dspy.Prediction(
            topics=topics.topics,
            entities=entities.entities,
            sentiment=sentiment.sentiment,
            sentiment_score=sentiment.score,
            summary=summary.summary,
            report=report.report
        )

# Use hierarchical processor
processor = DocumentProcessor()
result = processor(document="Long document text...")
```

**When to use**:
- Complex multi-stage pipelines
- Clear separation of concerns
- Independent optimization of each level
- Reusable sub-modules

### Pattern 11: Adaptive Module Selection

```python
import dspy
from typing import Dict, Callable

class AdaptiveRouter(dspy.Module):
    """Route inputs to appropriate specialized modules."""

    def __init__(self, modules: Dict[str, dspy.Module],
                 router_fn: Callable[[str], str]):
        """
        Args:
            modules: Dict of {module_name: module_instance}
            router_fn: Function that returns module name given input
        """
        super().__init__()
        self.modules = modules
        self.router_fn = router_fn

    def forward(self, **kwargs):
        # Determine which module to use
        module_name = self.router_fn(str(kwargs))
        selected_module = self.modules.get(module_name)

        if not selected_module:
            raise ValueError(f"No module found for: {module_name}")

        # Execute selected module
        result = selected_module(**kwargs)

        # Add routing metadata
        result.selected_module = module_name

        return result

# Define specialized modules
qa_module = dspy.ChainOfThought("question -> answer")
summarize_module = dspy.ChainOfThought("document -> summary")
translate_module = dspy.Predict("text, target_lang -> translation")

# Define routing logic
def route_request(input_str: str) -> str:
    """Simple keyword-based routing."""
    if "summarize" in input_str.lower():
        return "summarize"
    elif "translate" in input_str.lower():
        return "translate"
    else:
        return "qa"

# Create adaptive router
router = AdaptiveRouter(
    modules={
        "qa": qa_module,
        "summarize": summarize_module,
        "translate": translate_module,
    },
    router_fn=route_request
)

# Use router
result1 = router(question="What is DSPy?")  # Routes to QA
result2 = router(document="Long text...", task="summarize")  # Routes to summarize
```

**Benefits**:
- Single entry point for multiple task types
- Specialized modules for each task
- Easy to add new modules
- Automatic routing based on input

---

## Production Considerations

### Module Performance Optimization

```python
import dspy
import time
from typing import Optional

class PerformanceOptimizedModule(dspy.Module):
    """Module with performance monitoring and optimization."""

    def __init__(self):
        super().__init__()
        self.fast_path = dspy.Predict("question -> answer")
        self.accurate_path = dspy.ChainOfThought("question -> answer, reasoning")

        # Performance tracking
        self.fast_count = 0
        self.accurate_count = 0
        self.total_time = 0.0

    def forward(self, question, require_reasoning=False, max_latency_ms=1000):
        start_time = time.time()

        # Choose path based on requirements
        if require_reasoning or len(question.split()) > 50:
            # Use accurate but slower path
            result = self.accurate_path(question=question)
            self.accurate_count += 1
        else:
            # Use fast path
            result = self.fast_path(question=question)
            self.fast_count += 1

            # Check latency budget
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms > max_latency_ms:
                # Log latency violation
                print(f"Warning: Latency {elapsed_ms:.0f}ms exceeded budget {max_latency_ms}ms")

        self.total_time += time.time() - start_time

        return result

    def performance_stats(self):
        """Return performance statistics."""
        total_calls = self.fast_count + self.accurate_count
        return {
            "total_calls": total_calls,
            "fast_path_calls": self.fast_count,
            "accurate_path_calls": self.accurate_count,
            "fast_path_percentage": (self.fast_count / total_calls * 100) if total_calls > 0 else 0,
            "avg_latency_ms": (self.total_time / total_calls * 1000) if total_calls > 0 else 0,
        }

# Usage
module = PerformanceOptimizedModule()

# Fast path
result1 = module(question="What is 2+2?")

# Accurate path
result2 = module(question="What is 2+2?", require_reasoning=True)

print(module.performance_stats())
```

### Module Testing and Validation

```python
import dspy
from typing import List, Tuple

class TestableModule(dspy.Module):
    """Module with built-in testing and validation."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought("question -> answer")
        self.test_cases = []

    def forward(self, question):
        return self.predictor(question=question)

    def add_test_case(self, question: str, expected_answer: str):
        """Add test case for validation."""
        self.test_cases.append((question, expected_answer))

    def run_tests(self, similarity_threshold=0.7) -> Tuple[int, int, List[dict]]:
        """
        Run all test cases.

        Returns:
            (passed_count, total_count, failures)
        """
        passed = 0
        failures = []

        for question, expected in self.test_cases:
            result = self(question=question)
            predicted = result.answer.lower()
            expected_lower = expected.lower()

            # Simple containment check (can be more sophisticated)
            if expected_lower in predicted or predicted in expected_lower:
                passed += 1
            else:
                failures.append({
                    "question": question,
                    "expected": expected,
                    "predicted": result.answer,
                })

        return passed, len(self.test_cases), failures

# Usage
module = TestableModule()

# Add test cases
module.add_test_case("What is the capital of France?", "Paris")
module.add_test_case("What is 2+2?", "4")
module.add_test_case("Who wrote Hamlet?", "Shakespeare")

# Run tests
passed, total, failures = module.run_tests()
print(f"Tests: {passed}/{total} passed")

if failures:
    print("\nFailures:")
    for f in failures:
        print(f"  Q: {f['question']}")
        print(f"  Expected: {f['expected']}")
        print(f"  Got: {f['predicted']}")
```

### Production Deployment Patterns

```python
import dspy
import logging
from typing import Optional
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionModule(dspy.Module):
    """Production-ready module with comprehensive error handling."""

    def __init__(self, fallback_response: Optional[str] = None):
        super().__init__()
        self.predictor = dspy.ChainOfThought("question -> answer, confidence: float")
        self.fallback_response = fallback_response or "I'm unable to answer that question."

        # Metrics
        self.success_count = 0
        self.error_count = 0
        self.fallback_count = 0

    def forward(self, question, user_id: Optional[str] = None):
        """
        Production-ready forward pass with full error handling.

        Args:
            question: User question
            user_id: Optional user identifier for logging

        Returns:
            Prediction with answer and metadata
        """
        try:
            # Log request
            logger.info(f"Request from user={user_id}: {question[:100]}")

            # Validate input
            if not question or len(question.strip()) == 0:
                raise ValueError("Empty question")

            if len(question) > 5000:
                raise ValueError("Question too long (>5000 chars)")

            # Make prediction
            result = self.predictor(question=question)

            # Validate output
            if not hasattr(result, 'answer') or not result.answer:
                raise ValueError("Empty answer from model")

            # Parse confidence
            try:
                confidence = float(result.confidence)
            except:
                confidence = 0.5
                logger.warning("Invalid confidence value, using default 0.5")

            # Check confidence threshold
            if confidence < 0.3:
                logger.warning(f"Low confidence ({confidence}) for question: {question[:100]}")
                self.fallback_count += 1
                return dspy.Prediction(
                    answer=self.fallback_response,
                    confidence=0.0,
                    status="fallback",
                    reason="low_confidence"
                )

            # Success
            self.success_count += 1
            logger.info(f"Success: confidence={confidence:.2f}")

            return dspy.Prediction(
                answer=result.answer,
                confidence=confidence,
                status="success"
            )

        except Exception as e:
            # Error handling
            self.error_count += 1
            logger.error(f"Error processing question: {e}", exc_info=True)

            return dspy.Prediction(
                answer=self.fallback_response,
                confidence=0.0,
                status="error",
                error=str(e)
            )

    def health_check(self) -> dict:
        """Return health status for monitoring."""
        total_requests = self.success_count + self.error_count + self.fallback_count
        error_rate = (self.error_count / total_requests) if total_requests > 0 else 0

        return {
            "status": "healthy" if error_rate < 0.1 else "degraded",
            "total_requests": total_requests,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "fallback_count": self.fallback_count,
            "error_rate": error_rate,
        }

# Usage
module = ProductionModule(fallback_response="I don't have enough information to answer that.")

# Process request
result = module(question="What is DSPy?", user_id="user123")
print(f"Answer: {result.answer}")
print(f"Status: {result.status}")

# Check health
health = module.health_check()
print(f"Health: {json.dumps(health, indent=2)}")
```

---

## Quick Reference

### Module Comparison

| Module | Reasoning | Speed | Accuracy | Use Case |
|--------|-----------|-------|----------|----------|
| Predict | None | Fastest | Good | Simple tasks |
| ChainOfThought | Sequential | Fast | Better | Complex reasoning |
| ReAct | Iterative + Tools | Slow | Best (with tools) | Multi-step + retrieval |
| ProgramOfThought | Code gen | Medium | Excellent (math) | Computations |

### Creating Custom Modules

```python
class MyModule(dspy.Module):
    def __init__(self):
        super().__init__()
        # Define sub-modules

    def forward(self, **kwargs):
        # Implement logic
        return dspy.Prediction(...)
```

### Module Best Practices

```
✅ DO: Use Predict for simple tasks
✅ DO: Use ChainOfThought for complex reasoning
✅ DO: Use ReAct when you need external information
✅ DO: Compose small modules into larger systems
✅ DO: Return dspy.Prediction from custom modules

❌ DON'T: Use ChainOfThought for all tasks (overkill for simple ones)
❌ DON'T: Use ReAct without proper tools
❌ DON'T: Create monolithic custom modules
❌ DON'T: Forget to call super().__init__() in custom modules
```

### Quick Module Templates

```python
# Simple predictor
pred = dspy.Predict("input -> output")

# Reasoning predictor
cot = dspy.ChainOfThought("question -> answer")

# With tools
react = dspy.ReAct(signature, tools=[tool1, tool2])

# Custom module
class Custom(dspy.Module):
    def __init__(self):
        super().__init__()
        self.pred = dspy.Predict(sig)

    def forward(self, x):
        return self.pred(input=x)
```

---

## Anti-Patterns

❌ **Using ChainOfThought for everything**: Slower and more expensive
```python
# Bad - overkill for simple classification
classifier = dspy.ChainOfThought("text -> category")
```
✅ Use Predict for simple tasks:
```python
# Good
classifier = dspy.Predict("text -> category")
```

❌ **Not composing modules**: Monolithic, hard to optimize
```python
# Bad - everything in one module
class Monolith(dspy.Module):
    def forward(self, x):
        # 100 lines of complex logic
        pass
```
✅ Compose smaller modules:
```python
# Good
class Pipeline(dspy.Module):
    def __init__(self):
        super().__init__()
        self.step1 = Module1()
        self.step2 = Module2()
        self.step3 = Module3()
```

❌ **Ignoring module return format**: Breaks composition
```python
# Bad
def forward(self, x):
    result = self.pred(x)
    return result.answer  # Returns string, not Prediction
```
✅ Return Prediction objects:
```python
# Good
def forward(self, x):
    result = self.pred(x)
    return dspy.Prediction(answer=result.answer, confidence=0.9)
```

---

## Related Skills

### Core DSPy Skills
- `dspy-signatures.md` - Defining signatures for modules
- `dspy-setup.md` - LM configuration for modules
- `dspy-optimizers.md` - Optimizing module parameters
- `dspy-rag.md` - Building RAG pipelines with modules
- `dspy-assertions.md` - Adding validation to modules
- `dspy-evaluation.md` - Evaluating module performance

### Advanced DSPy Skills
- `dspy-agents.md` - Building agent modules with tool use
- `dspy-caching.md` - Implementing module-level caching
- `dspy-streaming.md` - Streaming module outputs
- `dspy-testing.md` - Testing modules comprehensively
- `dspy-deployment.md` - Deploying modules to production
- `dspy-prompt-engineering.md` - Advanced module patterns

### Resources
- `resources/dspy/level1-quickstart.md` - Getting started with modules
- `resources/dspy/level2-architecture.md` - Module architecture patterns
- `resources/dspy/level3-production.md` - Production module deployment

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
