---
name: dspy-advanced-patterns
description: Advanced DSPy patterns including typed predictors with Pydantic, streaming, batch processing, prompt versioning, and meta-programming
---

# DSPy Advanced Patterns

**Scope**: Typed predictors, streaming responses, batch processing, parallel execution, prompt versioning, context management, custom signatures, meta-programming
**Lines**: ~500
**Last Updated**: 2025-10-30

## When to Use This Skill

Activate this skill when:
- Implementing type-safe DSPy programs with Pydantic
- Building streaming response systems
- Processing large batches efficiently
- Executing DSPy modules in parallel
- Managing prompt versions across deployments
- Implementing advanced context management
- Creating dynamic signatures programmatically
- Building meta-programming abstractions for DSPy

## Core Concepts

### Type Safety with Pydantic

**Benefits**:
- Compile-time type checking
- Runtime validation
- Better IDE support
- Self-documenting code
- Easier debugging

**Integration**:
- Use Pydantic models as signature fields
- Automatic validation of inputs/outputs
- Rich error messages
- Schema generation

### Streaming Patterns

**Use cases**:
- Real-time user feedback
- Long-running generations
- Improved perceived latency
- Token-by-token processing

**Challenges**:
- State management
- Error handling mid-stream
- Backpressure control
- Client compatibility

### Batch Processing

**Strategies**:
- Static batching (fixed size)
- Dynamic batching (time window)
- Adaptive batching (load-based)
- Priority batching (QoS)

**Optimization**:
- Reduce API calls
- Better GPU utilization
- Lower per-request cost
- Higher throughput

---

## Patterns

### Pattern 1: Typed Predictors with Pydantic

```python
import dspy
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum

# Define Pydantic models for strong typing
class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class AnalysisResult(BaseModel):
    """Structured output for text analysis."""
    sentiment: Sentiment
    confidence: float = Field(ge=0.0, le=1.0)
    key_phrases: List[str] = Field(max_items=5)
    summary: str = Field(max_length=200)

    @validator("confidence")
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
        return v

class TextAnalysisInput(BaseModel):
    """Input for text analysis."""
    text: str = Field(min_length=1, max_length=5000)
    language: Optional[str] = "en"

class TypedTextAnalyzer(dspy.Module):
    """Type-safe text analyzer using Pydantic."""

    def __init__(self):
        super().__init__()
        # DSPy signature with Pydantic models
        self.analyzer = dspy.Predict(
            "text: str, language: str -> "
            "sentiment: str, confidence: float, key_phrases: list[str], summary: str"
        )

    def forward(self, input_data: TextAnalysisInput) -> AnalysisResult:
        """Execute with type validation."""
        # Execute DSPy module
        result = self.analyzer(
            text=input_data.text,
            language=input_data.language,
        )

        # Parse and validate output with Pydantic
        analysis = AnalysisResult(
            sentiment=result.sentiment,
            confidence=float(result.confidence),
            key_phrases=result.key_phrases if isinstance(result.key_phrases, list) else [],
            summary=result.summary,
        )

        return analysis

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

analyzer = TypedTextAnalyzer()

# Type-safe input
try:
    input_data = TextAnalysisInput(
        text="This product exceeded my expectations!",
        language="en",
    )

    result = analyzer(input_data)
    print(f"Sentiment: {result.sentiment.value}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Key phrases: {result.key_phrases}")
    print(f"Summary: {result.summary}")

except ValueError as e:
    print(f"Validation error: {e}")

# Invalid input will raise error
try:
    invalid_input = TextAnalysisInput(text="")  # Too short
except ValueError as e:
    print(f"Input validation failed: {e}")
```

**Benefits**:
- Type safety at runtime
- Automatic validation
- Clear error messages
- IDE autocomplete
- Self-documenting APIs

**When to use**:
- Production systems
- APIs with external clients
- Complex data structures
- Team collaboration

### Pattern 2: Streaming Responses

```python
import dspy
from typing import Iterator, AsyncIterator
import asyncio

class StreamingPredictor:
    """DSPy predictor with streaming support."""

    def __init__(self, signature: str):
        self.signature = signature
        # Note: Streaming requires LM provider support
        self.lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
        dspy.configure(lm=self.lm)

    def stream(self, **kwargs) -> Iterator[str]:
        """Stream response tokens."""
        # Simplified streaming simulation
        # In practice, use LM provider's streaming API

        prompt = self._build_prompt(**kwargs)

        # Simulate streaming (replace with actual streaming)
        response = "This is a sample response that will be streamed word by word."
        words = response.split()

        for word in words:
            yield word + " "
            # In real implementation, yield actual tokens from LM

    async def stream_async(self, **kwargs) -> AsyncIterator[str]:
        """Async streaming response."""
        prompt = self._build_prompt(**kwargs)

        # Simulate async streaming
        response = "This is an async streamed response."
        words = response.split()

        for word in words:
            await asyncio.sleep(0.1)  # Simulate LM latency
            yield word + " "

    def _build_prompt(self, **kwargs) -> str:
        """Build prompt from signature and inputs."""
        # Simplified prompt building
        return f"Signature: {self.signature}, Inputs: {kwargs}"

class StreamingQA(dspy.Module):
    """Question answering with streaming."""

    def __init__(self):
        super().__init__()
        self.predictor = StreamingPredictor("question -> answer")

    def forward_stream(self, question: str) -> Iterator[str]:
        """Stream answer tokens."""
        return self.predictor.stream(question=question)

    async def forward_stream_async(self, question: str) -> AsyncIterator[str]:
        """Async stream answer tokens."""
        async for token in self.predictor.stream_async(question=question):
            yield token

# Synchronous streaming
qa = StreamingQA()
print("Streaming answer:")
for token in qa.forward_stream("What is DSPy?"):
    print(token, end="", flush=True)
print("\n")

# Async streaming
async def async_example():
    print("Async streaming answer:")
    async for token in qa.forward_stream_async("What is DSPy?"):
        print(token, end="", flush=True)
    print("\n")

asyncio.run(async_example())

# Web framework integration (FastAPI)
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/stream")
async def stream_answer(question: str):
    """Stream answer via HTTP."""
    qa = StreamingQA()

    async def generate():
        async for token in qa.forward_stream_async(question):
            yield token

    return StreamingResponse(generate(), media_type="text/plain")
```

**When to use**:
- Long-form content generation
- Real-time user experience
- Progressive rendering
- Low perceived latency

**Considerations**:
- LM provider support
- Error handling complexity
- Client compatibility
- State management

### Pattern 3: Batch Processing

```python
import dspy
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

class BatchProcessor(dspy.Module):
    """Efficient batch processing for DSPy modules."""

    def __init__(self, signature: str, batch_size: int = 10):
        super().__init__()
        self.predictor = dspy.Predict(signature)
        self.batch_size = batch_size

    def process_batch(self, inputs: List[Dict[str, Any]]) -> List[Any]:
        """Process batch of inputs."""
        results = []

        # Process in chunks
        for i in range(0, len(inputs), self.batch_size):
            batch = inputs[i:i + self.batch_size]

            # Execute batch
            batch_results = [
                self.predictor(**item)
                for item in batch
            ]

            results.extend(batch_results)

        return results

    def process_batch_parallel(
        self,
        inputs: List[Dict[str, Any]],
        max_workers: int = 4,
    ) -> List[Any]:
        """Process batch in parallel."""
        results = [None] * len(inputs)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_idx = {
                executor.submit(self.predictor, **item): idx
                for idx, item in enumerate(inputs)
            }

            # Collect results
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    print(f"Item {idx} failed: {e}")
                    results[idx] = None

        return results

class AdaptiveBatchProcessor(dspy.Module):
    """Adaptive batch processing with dynamic sizing."""

    def __init__(self, signature: str):
        super().__init__()
        self.predictor = dspy.Predict(signature)
        self.performance_history = []

    def process_adaptive(self, inputs: List[Dict[str, Any]]) -> List[Any]:
        """Process with adaptive batch sizing."""
        import time

        # Determine optimal batch size from history
        batch_size = self._get_optimal_batch_size()

        results = []
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i:i + batch_size]

            start = time.time()
            batch_results = [self.predictor(**item) for item in batch]
            duration = time.time() - start

            # Record performance
            throughput = len(batch) / duration
            self.performance_history.append({
                "batch_size": len(batch),
                "duration": duration,
                "throughput": throughput,
            })

            results.extend(batch_results)

            # Adapt batch size based on performance
            batch_size = self._adapt_batch_size(batch_size, throughput)

        return results

    def _get_optimal_batch_size(self) -> int:
        """Get optimal batch size from history."""
        if not self.performance_history:
            return 10  # Default

        # Find batch size with best throughput
        best = max(self.performance_history, key=lambda x: x["throughput"])
        return best["batch_size"]

    def _adapt_batch_size(self, current_size: int, throughput: float) -> int:
        """Adapt batch size based on performance."""
        if not self.performance_history or len(self.performance_history) < 2:
            return current_size

        # Compare with previous throughput
        prev_throughput = self.performance_history[-2]["throughput"]

        if throughput > prev_throughput * 1.1:  # 10% improvement
            return min(current_size * 2, 100)  # Increase
        elif throughput < prev_throughput * 0.9:  # 10% degradation
            return max(current_size // 2, 1)  # Decrease
        else:
            return current_size  # Keep same

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Basic batch processing
batch_qa = BatchProcessor("question -> answer", batch_size=5)

questions = [
    {"question": f"What is {i} + {i}?"}
    for i in range(20)
]

results = batch_qa.process_batch(questions)
print(f"Processed {len(results)} questions")

# Parallel batch processing
parallel_results = batch_qa.process_batch_parallel(questions, max_workers=4)
print(f"Processed {len(parallel_results)} questions in parallel")

# Adaptive batch processing
adaptive_qa = AdaptiveBatchProcessor("question -> answer")
adaptive_results = adaptive_qa.process_adaptive(questions)
print(f"Adaptive processing complete")
print(f"Performance history: {adaptive_qa.performance_history[-3:]}")
```

**Strategies**:
- Static batching (fixed size)
- Dynamic batching (adaptive)
- Parallel execution
- Queue-based processing

**Benefits**:
- Higher throughput
- Lower cost per request
- Better resource utilization
- Reduced API calls

### Pattern 4: Prompt Versioning

```python
import dspy
from typing import Dict, Optional
from datetime import datetime
import json

class VersionedPrompt:
    """Versioned prompt management."""

    def __init__(self, name: str, version: str, template: str, metadata: dict = None):
        self.name = name
        self.version = version
        self.template = template
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()

class PromptRegistry:
    """Registry for managing prompt versions."""

    def __init__(self):
        self.prompts: Dict[str, Dict[str, VersionedPrompt]] = {}

    def register(self, prompt: VersionedPrompt):
        """Register a prompt version."""
        if prompt.name not in self.prompts:
            self.prompts[prompt.name] = {}

        self.prompts[prompt.name][prompt.version] = prompt
        print(f"Registered {prompt.name} v{prompt.version}")

    def get(self, name: str, version: Optional[str] = None) -> VersionedPrompt:
        """Get prompt by name and version."""
        if name not in self.prompts:
            raise ValueError(f"Prompt {name} not found")

        if version is None:
            # Get latest version
            versions = self.prompts[name]
            latest = max(versions.keys())
            return versions[latest]

        if version not in self.prompts[name]:
            raise ValueError(f"Version {version} not found for {name}")

        return self.prompts[name][version]

    def list_versions(self, name: str) -> list:
        """List all versions of a prompt."""
        if name not in self.prompts:
            return []
        return list(self.prompts[name].keys())

class VersionedModule(dspy.Module):
    """DSPy module with prompt versioning."""

    def __init__(
        self,
        registry: PromptRegistry,
        prompt_name: str,
        prompt_version: Optional[str] = None,
    ):
        super().__init__()
        self.registry = registry
        self.prompt_name = prompt_name
        self.prompt_version = prompt_version

        # Load prompt
        self.prompt = self.registry.get(prompt_name, prompt_version)

        # Create predictor with versioned prompt
        self.predictor = dspy.Predict("question -> answer")

    def forward(self, **kwargs):
        """Execute with versioned prompt."""
        # Add prompt metadata to result
        result = self.predictor(**kwargs)

        # Attach version info
        result.prompt_version = self.prompt.version
        result.prompt_name = self.prompt.name

        return result

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create registry
registry = PromptRegistry()

# Register prompt versions
registry.register(VersionedPrompt(
    name="qa_prompt",
    version="1.0.0",
    template="Answer the question: {question}",
    metadata={"author": "team", "purpose": "baseline"},
))

registry.register(VersionedPrompt(
    name="qa_prompt",
    version="1.1.0",
    template="Answer the question clearly and concisely: {question}",
    metadata={"author": "team", "purpose": "improved clarity"},
))

registry.register(VersionedPrompt(
    name="qa_prompt",
    version="2.0.0",
    template="Think step by step and answer: {question}",
    metadata={"author": "team", "purpose": "chain of thought"},
))

# Use specific version
qa_v1 = VersionedModule(registry, "qa_prompt", "1.0.0")
result_v1 = qa_v1(question="What is DSPy?")
print(f"v1.0.0 answer: {result_v1.answer}")

# Use latest version
qa_latest = VersionedModule(registry, "qa_prompt")
result_latest = qa_latest(question="What is DSPy?")
print(f"Latest ({result_latest.prompt_version}) answer: {result_latest.answer}")

# List versions
versions = registry.list_versions("qa_prompt")
print(f"Available versions: {versions}")

# A/B testing with versions
def ab_test_versions(question: str, version_a: str, version_b: str):
    """Compare two prompt versions."""
    qa_a = VersionedModule(registry, "qa_prompt", version_a)
    qa_b = VersionedModule(registry, "qa_prompt", version_b)

    result_a = qa_a(question=question)
    result_b = qa_b(question=question)

    print(f"\nVersion {version_a}:")
    print(result_a.answer)

    print(f"\nVersion {version_b}:")
    print(result_b.answer)

ab_test_versions("What is DSPy?", "1.0.0", "2.0.0")
```

**Benefits**:
- Track prompt evolution
- A/B test prompts
- Rollback capability
- Audit trail
- Team collaboration

### Pattern 5: Context Management

```python
import dspy
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variables for thread-safe state
current_user = ContextVar("current_user", default=None)
request_id = ContextVar("request_id", default=None)
execution_context = ContextVar("execution_context", default=None)

class ContextAwareModule(dspy.Module):
    """DSPy module with context awareness."""

    def __init__(self, signature: str):
        super().__init__()
        self.predictor = dspy.Predict(signature)

    def forward(self, **kwargs):
        """Execute with context."""
        # Get context
        user = current_user.get()
        req_id = request_id.get()
        ctx = execution_context.get() or {}

        # Add context to inputs
        enriched_kwargs = {
            **kwargs,
            "_user": user,
            "_request_id": req_id,
            "_context": ctx,
        }

        # Execute
        result = self.predictor(**kwargs)  # Don't pass internal fields to LM

        # Add context to result
        result._user = user
        result._request_id = req_id

        return result

class ContextManager:
    """Manage execution context."""

    def __init__(
        self,
        user: Optional[str] = None,
        request_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ):
        self.user = user
        self.request_id = request_id
        self.extra_context = extra_context or {}

        self.tokens = {}

    def __enter__(self):
        """Enter context."""
        self.tokens["user"] = current_user.set(self.user)
        self.tokens["request_id"] = request_id.set(self.request_id)
        self.tokens["context"] = execution_context.set(self.extra_context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        for token in self.tokens.values():
            try:
                token.var.reset(token)
            except Exception:
                pass

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

qa = ContextAwareModule("question -> answer")

# Use with context
with ContextManager(user="alice", request_id="req-123"):
    result = qa(question="What is DSPy?")
    print(f"User: {result._user}")
    print(f"Request ID: {result._request_id}")
    print(f"Answer: {result.answer}")

# Different context
with ContextManager(user="bob", request_id="req-456", extra_context={"tenant": "acme"}):
    result = qa(question="What is DSPy?")
    print(f"User: {result._user}")
    print(f"Request ID: {result._request_id}")
```

**Use cases**:
- Multi-tenant systems
- Request tracing
- User personalization
- Feature flags
- A/B testing

### Pattern 6: Dynamic Signatures

```python
import dspy
from typing import Dict, Any, List

class DynamicSignatureBuilder:
    """Build DSPy signatures dynamically."""

    @staticmethod
    def build_signature(
        inputs: List[str],
        outputs: List[str],
        input_types: Dict[str, str] = None,
        output_types: Dict[str, str] = None,
    ) -> str:
        """Build signature string from components."""
        input_types = input_types or {}
        output_types = output_types or {}

        # Build input fields
        input_parts = []
        for inp in inputs:
            type_str = input_types.get(inp, "")
            if type_str:
                input_parts.append(f"{inp}: {type_str}")
            else:
                input_parts.append(inp)

        # Build output fields
        output_parts = []
        for out in outputs:
            type_str = output_types.get(out, "")
            if type_str:
                output_parts.append(f"{out}: {type_str}")
            else:
                output_parts.append(out)

        return f"{', '.join(input_parts)} -> {', '.join(output_parts)}"

class DynamicModule(dspy.Module):
    """DSPy module with dynamic signature."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config

        # Build signature from config
        signature = DynamicSignatureBuilder.build_signature(
            inputs=config["inputs"],
            outputs=config["outputs"],
            input_types=config.get("input_types"),
            output_types=config.get("output_types"),
        )

        self.predictor = dspy.ChainOfThought(signature)

    def forward(self, **kwargs):
        """Execute with dynamic inputs."""
        # Validate inputs match config
        expected_inputs = set(self.config["inputs"])
        provided_inputs = set(kwargs.keys())

        if not provided_inputs.issubset(expected_inputs):
            raise ValueError(
                f"Unexpected inputs: {provided_inputs - expected_inputs}"
            )

        return self.predictor(**kwargs)

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Define module configuration
qa_config = {
    "inputs": ["question", "context"],
    "outputs": ["answer", "confidence"],
    "input_types": {},
    "output_types": {"confidence": "float"},
}

# Create dynamic module
qa = DynamicModule(qa_config)

result = qa(
    question="What is DSPy?",
    context="DSPy is a framework for programming language models.",
)
print(f"Answer: {result.answer}")
print(f"Confidence: {result.confidence}")

# Different configuration
classifier_config = {
    "inputs": ["text"],
    "outputs": ["category", "subcategory", "confidence"],
    "output_types": {"confidence": "float"},
}

classifier = DynamicModule(classifier_config)
result = classifier(text="This movie is amazing!")
print(f"Category: {result.category}")
print(f"Subcategory: {result.subcategory}")
print(f"Confidence: {result.confidence}")
```

**When to use**:
- Configuration-driven systems
- Multi-tenant applications
- Flexible APIs
- Rapid prototyping

### Pattern 7: Meta-Programming

```python
import dspy
from typing import Type, Callable, Any
import inspect

class ModuleFactory:
    """Factory for creating DSPy modules programmatically."""

    @staticmethod
    def create_module(
        name: str,
        signature: str,
        module_type: str = "ChainOfThought",
        **kwargs,
    ) -> Type[dspy.Module]:
        """Create module class dynamically."""

        # Get module class
        module_class = getattr(dspy, module_type)

        # Define forward method
        def forward(self, **inputs):
            return self.predictor(**inputs)

        # Create class dynamically
        module_cls = type(
            name,
            (dspy.Module,),
            {
                "__init__": lambda self: (
                    super(type(self), self).__init__(),
                    setattr(self, "predictor", module_class(signature, **kwargs)),
                ),
                "forward": forward,
            },
        )

        return module_cls

class MetaOptimizer:
    """Meta-optimizer that learns how to optimize."""

    def __init__(self):
        self.optimization_history = []

    def optimize(
        self,
        program: dspy.Module,
        trainset: list,
        strategies: list,
    ):
        """Try multiple optimization strategies and learn best."""
        best_program = program
        best_score = 0.0

        for strategy in strategies:
            print(f"Trying strategy: {strategy['name']}")

            # Create optimizer
            optimizer_class = getattr(dspy, strategy["optimizer"])
            optimizer = optimizer_class(**strategy.get("params", {}))

            # Optimize
            try:
                optimized = optimizer.compile(program, trainset=trainset)

                # Evaluate
                metric = lambda ex, pred: float(ex.answer in pred.answer)
                score = sum(
                    metric(ex, optimized(**ex.inputs()))
                    for ex in trainset
                ) / len(trainset)

                print(f"  Score: {score:.2%}")

                # Record
                self.optimization_history.append({
                    "strategy": strategy["name"],
                    "score": score,
                })

                # Update best
                if score > best_score:
                    best_score = score
                    best_program = optimized

            except Exception as e:
                print(f"  Failed: {e}")

        print(f"\nBest strategy: {max(self.optimization_history, key=lambda x: x['score'])['strategy']}")
        print(f"Best score: {best_score:.2%}")

        return best_program

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create module dynamically
QAModule = ModuleFactory.create_module(
    name="DynamicQA",
    signature="question -> answer",
    module_type="ChainOfThought",
)

qa = QAModule()
result = qa(question="What is DSPy?")
print(f"Answer: {result.answer}")

# Meta-optimization
trainset = [
    dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
    dspy.Example(question="What is 3+3?", answer="6").with_inputs("question"),
]

meta_optimizer = MetaOptimizer()

strategies = [
    {
        "name": "Bootstrap Few-Shot",
        "optimizer": "BootstrapFewShot",
        "params": {"metric": lambda ex, pred: float(ex.answer in pred.answer)},
    },
    # Add more strategies
]

program = dspy.ChainOfThought("question -> answer")
best = meta_optimizer.optimize(program, trainset, strategies)
```

**Advanced techniques**:
- Dynamic class generation
- Reflection and introspection
- Strategy pattern
- Factory pattern
- Template methods

### Pattern 8: Function Composition

```python
import dspy
from typing import Callable, Any
from functools import wraps

def compose(*modules):
    """Compose multiple DSPy modules."""
    def composed(input_data):
        result = input_data
        for module in modules:
            result = module(**result._asdict() if hasattr(result, "_asdict") else {"input": result})
        return result
    return composed

def cache_results(cache_dict: dict):
    """Decorator to cache module results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = str(kwargs)

            if key in cache_dict:
                print(f"Cache hit: {key[:50]}")
                return cache_dict[key]

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache_dict[key] = result

            return result
        return wrapper
    return decorator

def retry(max_attempts: int = 3):
    """Decorator to retry on failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    print(f"Attempt {attempt + 1} failed: {e}")

            raise last_error
        return wrapper
    return decorator

class ComposableModule(dspy.Module):
    """Module with functional composition support."""

    def __init__(self, signature: str):
        super().__init__()
        self.predictor = dspy.Predict(signature)
        self.middleware = []

    def use(self, middleware: Callable):
        """Add middleware."""
        self.middleware.append(middleware)
        return self

    def forward(self, **kwargs):
        """Execute with middleware."""
        # Apply middleware
        for mw in self.middleware:
            kwargs = mw(kwargs)

        # Execute predictor
        return self.predictor(**kwargs)

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Module composition
step1 = dspy.Predict("question -> simplified_question: str")
step2 = dspy.ChainOfThought("simplified_question -> answer")

# Compose modules
pipeline = compose(step1, step2)
# result = pipeline({"question": "Complex question here"})

# Decorators
cache = {}

@cache_results(cache)
@retry(max_attempts=3)
def cached_qa(question: str):
    qa = dspy.Predict("question -> answer")
    return qa(question=question)

# Use cached function
result1 = cached_qa("What is DSPy?")
result2 = cached_qa("What is DSPy?")  # Cache hit

# Middleware pattern
def logging_middleware(kwargs):
    print(f"Input: {kwargs}")
    return kwargs

def validation_middleware(kwargs):
    if "question" not in kwargs or not kwargs["question"]:
        raise ValueError("Question required")
    return kwargs

qa = ComposableModule("question -> answer")
qa.use(logging_middleware).use(validation_middleware)

result = qa(question="What is DSPy?")
```

**Composition patterns**:
- Pipeline composition
- Middleware chains
- Decorator stacking
- Higher-order modules
- Functional transforms

---

## Quick Reference

### Advanced Patterns Summary

| Pattern | Use Case | Complexity |
|---------|----------|------------|
| Typed Predictors | Type-safe APIs | Medium |
| Streaming | Real-time UX | High |
| Batch Processing | High throughput | Medium |
| Prompt Versioning | A/B testing | Low |
| Context Management | Multi-tenant | Medium |
| Dynamic Signatures | Config-driven | Medium |
| Meta-Programming | Flexible abstractions | High |
| Function Composition | Modular pipelines | Medium |

### Best Practices

```
Type Safety:
✅ Use Pydantic for production
✅ Validate at boundaries
✅ Document types clearly
✅ Handle validation errors

Performance:
✅ Batch similar requests
✅ Use parallel execution
✅ Cache when possible
✅ Profile bottlenecks

Maintainability:
✅ Version prompts
✅ Use context managers
✅ Compose small modules
✅ Document signatures
```

---

## Anti-Patterns

❌ **Over-engineering**: Unnecessary complexity
```python
# Bad - complex for simple task
class OverEngineeredModule(TypedStreamingBatchedCachedModule):
    pass
```
✅ Start simple:
```python
# Good
module = dspy.Predict("input -> output")
```

❌ **Ignoring types**: Runtime errors
```python
# Bad
result = module(question="test")
# What fields does result have?
```
✅ Use typed models:
```python
# Good
result: AnalysisResult = module(input_data)
result.sentiment  # IDE autocomplete works
```

❌ **No versioning**: Breaking changes
```python
# Bad - modify prompts directly in code
```
✅ Version prompts:
```python
# Good
registry.register(VersionedPrompt("qa", "2.0.0", template))
```

---

## Related Skills

- `dspy-production.md` - Production deployment
- `dspy-testing.md` - Testing advanced patterns
- `dspy-debugging.md` - Debugging complex systems
- `pydantic-advanced.md` - Advanced Pydantic patterns
- `python-async.md` - Async programming

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
