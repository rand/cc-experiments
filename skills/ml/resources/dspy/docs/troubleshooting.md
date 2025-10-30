# DSPy Troubleshooting Guide

Common issues, error messages, debugging techniques, and solutions for DSPy applications.

## Table of Contents
- [Common Error Messages](#common-error-messages)
- [Performance Issues](#performance-issues)
- [Optimization Problems](#optimization-problems)
- [Integration Issues](#integration-issues)
- [Production Issues](#production-issues)
- [Debugging Techniques](#debugging-techniques)
- [FAQ](#faq)

---

## Common Error Messages

### Error: "No LM configured"

**Message**:
```
AttributeError: 'Settings' object has no attribute 'lm'
```

**Cause**: Forgot to configure language model before using DSPy modules.

**Solution**:
```python
import dspy

# Configure LM
lm = dspy.OpenAI(model="gpt-3.5-turbo", api_key="...")
dspy.settings.configure(lm=lm)

# Now you can use modules
qa = dspy.ChainOfThought("question -> answer")
result = qa(question="What is AI?")
```

**Prevention**: Always configure LM at the start of your script or application.

---

### Error: "Assertion failed"

**Message**:
```
dspy.primitives.assertions.AssertionError: Assertion failed: Answer too short
Suggestions: ['Try rephrasing', 'Provide more context']
```

**Cause**: Output didn't meet assertion constraints.

**Solution 1: Adjust Assertion**
```python
# Too strict
dspy.Assert(len(answer) > 100, "Answer too short")

# More lenient
dspy.Assert(len(answer) > 20, "Answer too short")
```

**Solution 2: Use Suggest Instead**
```python
# Suggest allows backtracking
dspy.Suggest(
    len(answer) > 50,
    "Answer should be detailed",
    target_module=generate_answer
)
```

**Solution 3: Increase Max Retries**
```python
from dspy.primitives.program import Program

Program.max_retry_attempts = 5  # Default is 3
```

---

### Error: "Module has no attribute 'passages'"

**Message**:
```
AttributeError: 'Prediction' object has no attribute 'passages'
```

**Cause**: Trying to access retrieval results incorrectly.

**Solution**:
```python
# WRONG
passages = retrieve(query)
for p in passages:  # ❌ passages is Prediction object
    print(p)

# CORRECT
prediction = retrieve(query)
for p in prediction.passages:  # ✅ Access via .passages
    print(p)

# OR
passages = retrieve(query).passages  # Extract directly
```

---

### Error: "Metric returned None"

**Message**:
```
ValueError: Metric returned None for example: {...}
```

**Cause**: Metric function didn't return a score.

**Solution**:
```python
# WRONG
def accuracy(example, prediction):
    if example.answer == prediction.answer:
        return True  # ❌ Should return number

# CORRECT
def accuracy(example, prediction):
    return 1.0 if example.answer == prediction.answer else 0.0

# OR use built-in metrics
from dspy.evaluate import answer_exact_match

score = answer_exact_match(example, prediction)
```

---

### Error: "Rate limit exceeded"

**Message**:
```
openai.RateLimitError: Rate limit exceeded. Please retry after 20 seconds.
```

**Cause**: Too many API calls too quickly.

**Solution 1: Add Retry Logic**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
def call_lm(question):
    return lm(prompt=question)
```

**Solution 2: Implement Rate Limiting**
```python
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_calls, period):
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove old calls
            while self.calls and self.calls[0] < now - self.period:
                self.calls.popleft()

            # Wait if limit reached
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                time.sleep(sleep_time)

            result = func(*args, **kwargs)
            self.calls.append(time.time())
            return result
        return wrapper

# Limit to 60 calls per minute
@RateLimiter(max_calls=60, period=60)
def call_lm(question):
    return lm(prompt=question)
```

**Solution 3: Batch Requests**
```python
# Instead of individual calls
for question in questions:
    answer = qa(question=question)  # ❌ Many API calls

# Batch them
from dspy.primitives import batch

answers = batch(qa, questions=questions, batch_size=10)  # ✅ Fewer calls
```

---

### Error: "Context length exceeded"

**Message**:
```
openai.InvalidRequestError: This model's maximum context length is 4096 tokens, however you requested 5000 tokens.
```

**Cause**: Input + generated output exceeds model's context window.

**Solution 1: Reduce Retrieved Context**
```python
# Retrieve fewer passages
retrieve = dspy.Retrieve(k=3)  # Instead of k=10

# Truncate passages
def truncate_passages(passages, max_length=200):
    return [p[:max_length] for p in passages]
```

**Solution 2: Summarize Context**
```python
class RAGWithSummary(dspy.Module):
    def __init__(self):
        self.retrieve = dspy.Retrieve(k=10)
        self.summarize = dspy.ChainOfThought("passages -> summary")
        self.answer = dspy.ChainOfThought("summary, question -> answer")

    def forward(self, question):
        passages = self.retrieve(question).passages
        summary = self.summarize(passages=passages).summary
        return self.answer(summary=summary, question=question)
```

**Solution 3: Use Model with Larger Context**
```python
# Switch to larger context model
lm = dspy.OpenAI(model="gpt-4-turbo")  # 128k context
# or
lm = dspy.Anthropic(model="claude-3-opus")  # 200k context
```

---

### Error: "Teleprompter not converging"

**Message**:
```
Warning: Optimizer did not converge after 100 iterations.
Best score: 0.42 (target: 0.80)
```

**Cause**: Training data insufficient, metric too strict, or model not capable.

**Solution 1: More Training Data**
```python
# Need 50+ examples for BootstrapFewShot
# Need 500+ for MIPROv2
trainset = load_more_examples()  # Get more data
```

**Solution 2: Relax Metric**
```python
# Too strict
def strict_metric(example, pred):
    return 1.0 if example.answer == pred.answer else 0.0

# More lenient
def lenient_metric(example, pred):
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, example.answer, pred.answer).ratio()
    return similarity  # 0.0 to 1.0
```

**Solution 3: Tune Hyperparameters**
```python
from dspy.teleprompt import MIPROv2

optimizer = MIPROv2(
    metric=accuracy,
    num_candidates=20,  # Increase from default 10
    init_temperature=1.0,  # Higher temperature for exploration
    verbose=True
)

optimized = optimizer.compile(
    program,
    trainset=train,
    max_bootstrapped_demos=6,  # More demos
    max_labeled_demos=3
)
```

---

## Performance Issues

### Issue: Slow Inference

**Symptoms**: Requests taking >5 seconds.

**Diagnosis**:
```python
import time

def profile_forward(program, inputs):
    """Profile forward pass."""
    start = time.time()
    result = program(**inputs)
    duration = time.time() - start
    print(f"Total time: {duration:.2f}s")

    # Profile each module
    for name, module in program.named_predictors():
        start = time.time()
        _ = module(**inputs)
        duration = time.time() - start
        print(f"  {name}: {duration:.2f}s")

    return result
```

**Solutions**:

**1. Enable Caching**
```python
import dspy
from dspy.utils import DiskCache

# Cache LM calls
cache = DiskCache(cache_dir=".cache/lm")
lm = dspy.OpenAI(model="gpt-3.5-turbo", cache=cache)
```

**2. Use Faster Model**
```python
# Slow
lm = dspy.OpenAI(model="gpt-4")

# Fast
lm = dspy.OpenAI(model="gpt-3.5-turbo")
# or
lm = dspy.OpenAI(model="gpt-4-turbo")  # 2x faster than gpt-4
```

**3. Reduce Retrieved Passages**
```python
# Slow: Many passages = large prompt
retrieve = dspy.Retrieve(k=20)

# Fast: Fewer passages
retrieve = dspy.Retrieve(k=3)
```

**4. Batch Requests**
```python
# Slow: Sequential
results = [qa(question=q) for q in questions]

# Fast: Parallel batching
from dspy.primitives import batch
results = batch(qa, questions=questions, batch_size=10)
```

---

### Issue: High Memory Usage

**Symptoms**: OOM errors, memory growing unbounded.

**Diagnosis**:
```python
import tracemalloc
import psutil

# Start tracking
tracemalloc.start()
process = psutil.Process()

# Run code
for i in range(100):
    result = qa(question=f"Question {i}")

    # Check memory every 10 iterations
    if i % 10 == 0:
        current, peak = tracemalloc.get_traced_memory()
        print(f"Current: {current / 1024**2:.2f} MB")
        print(f"Peak: {peak / 1024**2:.2f} MB")
        print(f"RSS: {process.memory_info().rss / 1024**2:.2f} MB")
```

**Solutions**:

**1. Clear Cache Periodically**
```python
from dspy.utils import DiskCache

cache = DiskCache(cache_dir=".cache", max_size_mb=500)  # Limit cache size

# Or clear manually
if iteration % 100 == 0:
    cache.clear()
```

**2. Limit Context**
```python
# Large context accumulates
class ChatBot(dspy.Module):
    def __init__(self):
        self.history = []  # ❌ Grows unbounded

    def forward(self, message):
        self.history.append(message)
        # ...

# Fixed: Limit history
class ChatBot(dspy.Module):
    def __init__(self, max_history=10):
        self.history = []
        self.max_history = max_history

    def forward(self, message):
        self.history.append(message)
        self.history = self.history[-self.max_history:]  # ✅ Bounded
        # ...
```

**3. Use Generators**
```python
# Memory-heavy: Load all at once
trainset = [dspy.Example(**ex) for ex in load_all_examples()]

# Memory-efficient: Stream
def trainset_generator():
    for ex in load_examples_stream():
        yield dspy.Example(**ex)

trainset = trainset_generator()
```

---

### Issue: High Costs

**Symptoms**: Unexpected high API bills.

**Diagnosis**:
```python
from dspy.utils import CostTracker

tracker = CostTracker()
lm = dspy.OpenAI(model="gpt-4", tracker=tracker)

# Run program
result = qa(question="...")

# Check costs
print(f"Tokens: {tracker.total_tokens}")
print(f"Cost: ${tracker.total_cost:.4f}")
print(f"Cost per request: ${tracker.avg_cost:.4f}")
```

**Solutions**:

**1. Use Cheaper Model**
```python
# Expensive
lm = dspy.OpenAI(model="gpt-4")  # $0.03/1k tokens

# Cheaper
lm = dspy.OpenAI(model="gpt-3.5-turbo")  # $0.001/1k tokens
```

**2. Reduce Optimization Budget**
```python
from dspy.teleprompt import MIPROv2

# Expensive: 100 candidates × 500 examples = 50k calls
optimizer = MIPROv2(num_candidates=100)

# Cheaper: 10 candidates × 50 examples = 500 calls
optimizer = MIPROv2(num_candidates=10)
optimized = optimizer.compile(program, trainset=train[:50])
```

**3. Enable Aggressive Caching**
```python
from dspy.utils import DiskCache

cache = DiskCache(
    cache_dir=".cache",
    ttl=86400 * 7  # Cache for 7 days
)
lm = dspy.OpenAI(model="gpt-4", cache=cache)
```

**4. Sample Evaluation Set**
```python
# Expensive: Evaluate on 1000 examples
evaluate = dspy.Evaluate(devset=dev, metric=accuracy)

# Cheaper: Evaluate on 100 random samples
import random
sample = random.sample(dev, 100)
evaluate = dspy.Evaluate(devset=sample, metric=accuracy)
```

---

## Optimization Problems

### Issue: Optimization Hangs

**Symptoms**: Optimizer runs for hours without progress.

**Cause**: Infinite loop in metric, slow LM, or too many candidates.

**Diagnosis**:
```python
# Add timeouts
from dspy.teleprompt import MIPROv2
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Optimization timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(3600)  # 1 hour timeout

try:
    optimizer = MIPROv2(metric=accuracy, verbose=True)
    optimized = optimizer.compile(program, trainset=train)
except TimeoutError:
    print("Optimization timed out, using best so far")
finally:
    signal.alarm(0)
```

**Solutions**:

**1. Reduce Candidates**
```python
# Slow: Many candidates
optimizer = MIPROv2(num_candidates=50)

# Faster: Fewer candidates
optimizer = MIPROv2(num_candidates=5)
```

**2. Smaller Training Set**
```python
# Use subset for initial optimization
small_train = train[:50]
optimizer = MIPROv2(metric=accuracy)
optimized = optimizer.compile(program, trainset=small_train)

# Then fine-tune on full dataset
optimizer2 = BootstrapFewShot(metric=accuracy)
optimized = optimizer2.compile(optimized, trainset=train)
```

**3. Debug Metric**
```python
def debug_metric(example, prediction, trace=None):
    """Metric with debugging."""
    try:
        score = accuracy(example, prediction)
        print(f"Example: {example.question[:50]}...")
        print(f"Score: {score}")
        return score
    except Exception as e:
        print(f"Metric error: {e}")
        return 0.0  # Don't crash optimizer
```

---

### Issue: Poor Optimization Results

**Symptoms**: Optimized model worse than baseline.

**Cause**: Bad training data, wrong metric, or overfitting.

**Diagnosis**:
```python
# Compare baseline vs optimized
baseline_score = evaluate(baseline, devset=dev)
optimized_score = evaluate(optimized, devset=dev)

print(f"Baseline: {baseline_score:.2%}")
print(f"Optimized: {optimized_score:.2%}")

# Check train vs dev scores
train_score = evaluate(optimized, devset=train)
dev_score = evaluate(optimized, devset=dev)

if train_score - dev_score > 0.1:
    print("WARNING: Possible overfitting")
```

**Solutions**:

**1. Check Training Data Quality**
```python
# Review examples
for ex in train[:10]:
    print(f"Q: {ex.question}")
    print(f"A: {ex.answer}")
    print()

# Check for duplicates
questions = [ex.question for ex in train]
if len(questions) != len(set(questions)):
    print("WARNING: Duplicate examples found")
```

**2. Verify Metric Alignment**
```python
# Metric should match business goal
def business_metric(example, prediction):
    """What actually matters to users."""
    # Example: Answer must be correct AND concise
    correct = example.answer.lower() in prediction.answer.lower()
    concise = len(prediction.answer) < 100
    return 1.0 if correct and concise else 0.0
```

**3. Prevent Overfitting**
```python
from dspy.teleprompt import BootstrapFewShot

optimizer = BootstrapFewShot(
    metric=accuracy,
    max_bootstrapped_demos=3,  # Fewer demos = less overfitting
    max_rounds=1  # Single pass
)

# Use separate validation set
optimized = optimizer.compile(program, trainset=train)
val_score = evaluate(optimized, devset=validation)

if val_score < baseline_score:
    print("Optimization didn't help, using baseline")
    optimized = program
```

---

## Integration Issues

### Issue: Vector Database Connection Fails

**Symptoms**:
```
chromadb.errors.ChromaError: Connection refused
```

**Solutions**:

**1. Check Database Running**
```bash
# For ChromaDB
docker ps | grep chroma

# Start if not running
docker run -p 8000:8000 chromadb/chroma
```

**2. Verify Connection**
```python
import chromadb

# Test connection
try:
    client = chromadb.HttpClient(host="localhost", port=8000)
    client.heartbeat()  # Check if alive
    print("✅ ChromaDB connected")
except Exception as e:
    print(f"❌ ChromaDB connection failed: {e}")
```

**3. Use Persistent Client (Local)**
```python
# Instead of HTTP client
from chromadb import PersistentClient

client = PersistentClient(path="./chroma_db")  # Local storage
```

---

### Issue: Modal Deployment Fails

**Symptoms**:
```
modal.exception.AuthError: No API token found
```

**Solutions**:

**1. Authenticate**
```bash
modal token new
```

**2. Check Token**
```bash
modal token list
```

**3. Set Explicitly**
```python
import os
os.environ["MODAL_TOKEN_ID"] = "your-token-id"
os.environ["MODAL_TOKEN_SECRET"] = "your-token-secret"
```

---

## Production Issues

### Issue: Intermittent Failures

**Symptoms**: Requests succeed sometimes, fail others.

**Cause**: Network issues, rate limiting, or timeout.

**Solutions**:

**1. Add Retries**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def robust_forward(program, inputs):
    return program(**inputs)
```

**2. Add Circuit Breaker**
```python
from pybreaker import CircuitBreaker

breaker = CircuitBreaker(fail_max=5, timeout_duration=60)

@breaker
def call_program(inputs):
    return program(**inputs)

# Fallback when circuit open
try:
    result = call_program(inputs)
except CircuitBreakerError:
    result = fallback_response(inputs)
```

---

### Issue: Stale Cache

**Symptoms**: Updates not reflected in responses.

**Cause**: Cached responses from old version.

**Solutions**:

**1. Invalidate Cache**
```python
from dspy.utils import DiskCache

cache = DiskCache(cache_dir=".cache")
cache.clear()  # Clear all

# Or invalidate specific keys
cache.delete(key="...")
```

**2. Version Cache Keys**
```python
MODEL_VERSION = "v2"

def versioned_cache_key(inputs):
    return f"{MODEL_VERSION}:{hash(str(inputs))}"
```

---

## Debugging Techniques

### Technique 1: Inspect Outputs

```python
result = qa(question="What is AI?")

# Print full prediction
print(result)

# Access specific fields
print(f"Answer: {result.answer}")
print(f"Reasoning: {result.reasoning}")

# Check metadata
print(f"Tokens used: {result.metadata.get('tokens', 'N/A')}")
```

### Technique 2: Inspect Prompts

```python
# Enable prompt logging
import dspy
dspy.settings.configure(trace=[])

result = qa(question="What is AI?")

# View prompts sent to LM
for call in dspy.settings.trace:
    print("="*50)
    print("PROMPT:")
    print(call['prompt'])
    print("\nRESPONSE:")
    print(call['response'])
```

### Technique 3: Step Through Pipeline

```python
class DebugRAG(dspy.Module):
    def __init__(self):
        self.retrieve = dspy.Retrieve(k=5)
        self.answer = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        # Step 1: Retrieve
        passages = self.retrieve(question).passages
        print(f"Retrieved {len(passages)} passages")
        for i, p in enumerate(passages):
            print(f"{i+1}. {p[:100]}...")

        # Step 2: Answer
        result = self.answer(context=passages, question=question)
        print(f"Reasoning: {result.reasoning}")
        print(f"Answer: {result.answer}")

        return result
```

### Technique 4: Profile Performance

```python
from dspy.utils import Profiler

profiler = Profiler()

with profiler:
    result = qa(question="What is AI?")

profiler.report()
# Output:
# Module         Calls  Time (s)  Time (%)
# retrieve       1      0.15      30%
# answer         1      0.35      70%
# TOTAL                 0.50      100%
```

---

## FAQ

### Q: How do I debug "assertion failed" errors?

**A**: Temporarily disable assertions to see raw outputs:
```python
import dspy
dspy.settings.configure(bypass_assert=True)

# Or catch assertion errors
try:
    result = program(question="...")
except dspy.AssertionError as e:
    print(f"Assertion failed: {e}")
    print(f"Suggestions: {e.suggestions}")
```

### Q: Why is optimization so expensive?

**A**: Optimization requires many LM calls (candidates × examples × rounds). To reduce costs:
- Use smaller training set (50-100 examples)
- Fewer candidates (5-10 instead of 20-50)
- Use cheaper model (GPT-3.5 instead of GPT-4)
- Enable caching

### Q: How do I handle long documents?

**A**: Options:
1. **Chunking**: Split documents into passages, retrieve relevant chunks
2. **Summarization**: Summarize document before processing
3. **Hierarchical**: Multi-stage processing (coarse → fine)
4. **Long-context models**: Use models with large context (Claude, GPT-4 Turbo)

### Q: Can I use DSPy without internet?

**A**: Yes, with local models:
```python
lm = dspy.OllamaLocal(model="llama2")
dspy.settings.configure(lm=lm)
```

### Q: How do I version control compiled models?

**A**: Save models as JSON and commit:
```bash
# Save model
program.save("models/qa_v1.json")

# Commit
git add models/qa_v1.json
git commit -m "Add QA model v1"

# Tag
git tag -a v1.0 -m "Release v1.0"
```

### Q: What's the difference between Assert and Suggest?

**A**:
- **Assert**: Hard constraint, fails request if violated
- **Suggest**: Soft constraint, backtracks and retries if violated

Use Assert for critical requirements, Suggest for preferences.

### Q: How do I test DSPy programs?

**A**: See [testing-checklist.md](../checklists/testing-checklist.md). Key points:
- Mock LM calls in unit tests
- Use fixtures for test data
- Test with real LM in integration tests
- Measure evaluation metrics in CI/CD

### Q: Should I commit compiled models to git?

**A**:
- **Yes** for small models (<1MB) and reproducibility
- **No** for large models (use artifact storage like S3)
- **Alternative**: Save training config and re-compile on deploy

---

**Version**: 1.0
**Last Updated**: 2025-10-30
