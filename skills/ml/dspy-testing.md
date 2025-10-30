---
name: dspy-testing
description: Testing patterns for DSPy programs including unit, integration, property-based, and regression testing
---

# DSPy Testing

**Scope**: Unit testing, integration testing, test data generation, mocking, regression testing, coverage
**Lines**: ~500
**Last Updated**: 2025-10-30

## When to Use This Skill

Activate this skill when:
- Writing tests for DSPy modules and pipelines
- Setting up test infrastructure for DSPy projects
- Creating test data for optimization and evaluation
- Implementing regression testing for model changes
- Mocking LM responses for faster tests
- Measuring test coverage for DSPy code
- Testing production deployments
- Implementing property-based testing for invariants

## Core Concepts

### Testing Pyramid for DSPy

**Unit Tests** (70%):
- Test individual modules in isolation
- Mock LM responses
- Fast execution (milliseconds)
- Focus on logic and composition

**Integration Tests** (20%):
- Test module interactions
- Use real LMs with small models
- Test data flow and transformations
- Validate optimized programs

**End-to-End Tests** (10%):
- Test complete workflows
- Use production-like setup
- Slower but comprehensive
- Validate user scenarios

### Test Data Strategy

**Synthetic data**:
- Generate programmatically
- Cover edge cases
- Consistent and reproducible
- Fast iteration

**Real data**:
- Sample from production
- Capture actual patterns
- Better confidence
- Privacy considerations

**Adversarial data**:
- Edge cases
- Known failure modes
- Stress testing
- Robustness validation

### Testing Challenges

**Non-determinism**:
- LM outputs vary with temperature > 0
- Use temperature=0 for deterministic tests
- Test output structure, not exact text
- Use fuzzy matching for assertions

**Cost**:
- Every test calls LM API
- Mock responses for unit tests
- Use cheaper models for integration tests
- Cache responses during development

**Speed**:
- LM calls are slow (100ms-2s)
- Parallelize test execution
- Mock for fast feedback
- Use small test datasets

---

## Patterns

### Pattern 1: Basic Unit Testing with pytest

```python
import dspy
import pytest

# Configure test LM
@pytest.fixture(scope="session")
def test_lm():
    """Create test LM with deterministic settings."""
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0, max_tokens=100)
    dspy.configure(lm=lm)
    return lm

@pytest.fixture
def qa_module(test_lm):
    """Create QA module for testing."""
    return dspy.ChainOfThought("question -> answer")

def test_qa_module_basic(qa_module):
    """Test basic QA functionality."""
    result = qa_module(question="What is 2+2?")

    assert hasattr(result, "answer")
    assert result.answer is not None
    assert len(result.answer) > 0

def test_qa_module_reasoning(qa_module):
    """Test that reasoning is generated."""
    result = qa_module(question="Why is the sky blue?")

    assert hasattr(result, "reasoning")
    assert result.reasoning is not None
    assert len(result.reasoning) > 10  # Should have some explanation

def test_qa_module_numeric(qa_module):
    """Test numeric reasoning."""
    result = qa_module(question="What is 15 * 8?")

    # Check that answer contains the correct number
    assert "120" in result.answer

def test_qa_module_empty_input(qa_module):
    """Test handling of empty input."""
    with pytest.raises(Exception):
        qa_module(question="")

def test_qa_module_long_input(qa_module):
    """Test handling of long input."""
    long_question = "word " * 1000  # Very long question
    result = qa_module(question=long_question)

    # Should handle gracefully (might truncate)
    assert hasattr(result, "answer")

# Run with: pytest test_dspy_module.py -v
```

**When to use**:
- Testing module logic
- Validating output structure
- Quick feedback during development
- CI/CD pipelines

**Best practices**:
- Use fixtures for setup
- Test edge cases
- Use descriptive test names
- Keep tests isolated

### Pattern 2: Mocking LM Responses

```python
import dspy
import pytest
from unittest.mock import Mock, patch

class MockLM:
    """Mock LM for testing without API calls."""

    def __init__(self, responses: dict):
        """
        Args:
            responses: Dict mapping input substrings to response text
        """
        self.responses = responses
        self.calls = []

    def __call__(self, prompt, **kwargs):
        """Return mocked response based on prompt."""
        self.calls.append(prompt)

        # Find matching response
        for key, value in self.responses.items():
            if key in prompt:
                return value

        return "Mock response"

def test_with_mock_lm():
    """Test module with mocked LM responses."""
    # Create mock LM
    mock_lm = MockLM({
        "What is 2+2": "The answer is 4.",
        "capital of France": "The capital of France is Paris.",
    })

    # Configure DSPy with mock
    dspy.configure(lm=mock_lm)

    # Create and test module
    qa = dspy.Predict("question -> answer")

    result = qa(question="What is 2+2?")
    assert "4" in result.answer

    result = qa(question="What is the capital of France?")
    assert "Paris" in result.answer

    # Verify LM was called
    assert len(mock_lm.calls) == 2

def test_custom_module_with_mock():
    """Test custom module composition with mocks."""

    class MultiStepQA(dspy.Module):
        def __init__(self):
            super().__init__()
            self.decompose = dspy.Predict("question -> sub_questions: list[str]")
            self.answer = dspy.Predict("question -> answer")

        def forward(self, question):
            decomp = self.decompose(question=question)
            answers = [
                self.answer(question=sq).answer
                for sq in decomp.sub_questions
            ]
            return dspy.Prediction(
                sub_questions=decomp.sub_questions,
                answers=answers,
            )

    # Mock with structured responses
    mock_lm = MockLM({
        "sub_questions": '["What is A?", "What is B?"]',
        "What is A": "Answer A",
        "What is B": "Answer B",
    })

    dspy.configure(lm=mock_lm)

    qa = MultiStepQA()
    result = qa(question="Complex question")

    assert len(result.sub_questions) >= 1
    assert len(result.answers) >= 1

# Run with: pytest test_mocked.py -v
```

**Benefits**:
- No API costs
- Fast execution (milliseconds)
- Deterministic outputs
- Test edge cases easily

**When to use**:
- Unit testing module logic
- CI/CD with limited quota
- Testing error handling
- Rapid iteration

### Pattern 3: Integration Testing with Real LMs

```python
import dspy
import pytest

@pytest.fixture(scope="module")
def real_lm():
    """Configure real LM for integration tests."""
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)
    return lm

@pytest.mark.integration  # Mark as integration test
@pytest.mark.slow  # Mark as slow test
def test_rag_pipeline_integration(real_lm):
    """Test complete RAG pipeline with real LM."""

    class RAGPipeline(dspy.Module):
        def __init__(self):
            super().__init__()
            self.retrieve = dspy.Retrieve(k=3)
            self.generate = dspy.ChainOfThought("context, question -> answer")

        def forward(self, question):
            passages = self.retrieve(question).passages
            context = "\n".join(passages)
            return self.generate(context=context, question=question)

    # Configure retriever (you'd use real retriever here)
    rm = dspy.Retrieve(k=3)  # Assuming ColBERTv2 or similar configured

    pipeline = RAGPipeline()
    result = pipeline(question="What is DSPy?")

    # Validate output structure
    assert hasattr(result, "answer")
    assert len(result.answer) > 50  # Should be substantive

    # Validate reasoning was performed
    assert hasattr(result, "reasoning")

@pytest.mark.integration
def test_optimized_program_integration(real_lm, tmp_path):
    """Test saving and loading optimized programs."""

    # Create and optimize program
    program = dspy.ChainOfThought("question -> answer")

    # Simulate optimization (normally use BootstrapFewShot, etc.)
    # program = optimizer.compile(program, trainset=trainset)

    # Save to file
    save_path = tmp_path / "program.json"
    program.save(str(save_path))

    # Load from file
    loaded_program = dspy.ChainOfThought("question -> answer")
    loaded_program.load(str(save_path))

    # Test loaded program
    result = loaded_program(question="What is 10 * 10?")
    assert "100" in result.answer

# Run integration tests: pytest -m integration
# Skip slow tests: pytest -m "not slow"
```

**Configuration** (`pytest.ini`):
```ini
[pytest]
markers =
    integration: Integration tests (use real LMs)
    slow: Slow tests (may take minutes)
    unit: Fast unit tests
```

**When to use**:
- Testing complete workflows
- Validating optimized programs
- Pre-deployment verification
- Smoke testing

### Pattern 4: Property-Based Testing

```python
import dspy
import pytest
from hypothesis import given, strategies as st

# Configure deterministic LM
@pytest.fixture(scope="module")
def test_lm():
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)
    return lm

@given(question=st.text(min_size=1, max_size=100))
def test_qa_answer_not_empty(test_lm, question):
    """Property: QA module should always return non-empty answer."""
    qa = dspy.Predict("question -> answer")
    result = qa(question=question)

    assert hasattr(result, "answer")
    assert result.answer is not None
    assert len(result.answer.strip()) > 0

@given(question=st.text(min_size=1, max_size=100))
def test_qa_deterministic(test_lm, question):
    """Property: Same question should give same answer (temperature=0)."""
    qa = dspy.Predict("question -> answer")

    result1 = qa(question=question)
    result2 = qa(question=question)

    assert result1.answer == result2.answer

@given(
    questions=st.lists(
        st.text(min_size=1, max_size=50),
        min_size=2,
        max_size=5,
    )
)
def test_batch_processing_consistency(test_lm, questions):
    """Property: Batch processing should be consistent with individual."""
    qa = dspy.Predict("question -> answer")

    # Process individually
    individual_results = [qa(question=q).answer for q in questions]

    # Process as batch (if supported)
    # batch_results = qa.batch(questions=[questions])

    # For now, just verify all returned valid answers
    assert all(len(ans.strip()) > 0 for ans in individual_results)

def test_classifier_coverage():
    """Property: Classifier should handle all expected categories."""
    classifier = dspy.Predict("text -> category, confidence: float")

    test_cases = {
        "This movie is amazing!": "positive",
        "This movie is terrible.": "negative",
        "The movie was okay.": "neutral",
    }

    for text, expected_sentiment in test_cases.items():
        result = classifier(text=text)

        assert hasattr(result, "category")
        assert hasattr(result, "confidence")
        assert 0.0 <= result.confidence <= 1.0

# Run with: pytest test_properties.py -v
```

**Properties to test**:
- Output structure consistency
- Non-empty responses
- Confidence bounds (0-1)
- Determinism at temperature=0
- Error handling for edge cases
- Idempotency
- Commutativity (where applicable)

### Pattern 5: Regression Testing

```python
import dspy
import pytest
import json
from pathlib import Path

class RegressionTestSuite:
    """Manage regression test cases."""

    def __init__(self, test_file: Path):
        self.test_file = test_file
        self.test_cases = self._load_test_cases()

    def _load_test_cases(self):
        """Load test cases from file."""
        if self.test_file.exists():
            with open(self.test_file) as f:
                return json.load(f)
        return []

    def save_test_cases(self):
        """Save test cases to file."""
        with open(self.test_file, "w") as f:
            json.dump(self.test_cases, f, indent=2)

    def add_test_case(self, inputs: dict, expected_output: dict):
        """Add a new test case."""
        self.test_cases.append({
            "inputs": inputs,
            "expected": expected_output,
        })
        self.save_test_cases()

    def run_regression_tests(self, module: dspy.Module) -> list:
        """Run all regression tests and return failures."""
        failures = []

        for i, test_case in enumerate(self.test_cases):
            try:
                result = module(**test_case["inputs"])

                # Compare outputs
                for key, expected_value in test_case["expected"].items():
                    actual_value = getattr(result, key)

                    if actual_value != expected_value:
                        failures.append({
                            "test_index": i,
                            "field": key,
                            "expected": expected_value,
                            "actual": actual_value,
                        })

            except Exception as e:
                failures.append({
                    "test_index": i,
                    "error": str(e),
                })

        return failures

# Usage
@pytest.fixture
def regression_suite(tmp_path):
    """Create regression test suite."""
    test_file = tmp_path / "regression_tests.json"
    return RegressionTestSuite(test_file)

def test_regression_suite(regression_suite):
    """Test with regression suite."""
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)

    qa = dspy.Predict("question -> answer")

    # Add test cases (normally done during development)
    regression_suite.add_test_case(
        inputs={"question": "What is 2+2?"},
        expected={"answer": "4"},
    )

    regression_suite.add_test_case(
        inputs={"question": "What is the capital of France?"},
        expected={"answer": "Paris"},
    )

    # Run regression tests
    failures = regression_suite.run_regression_tests(qa)

    # Assert no regressions
    if failures:
        pytest.fail(f"Regression tests failed: {failures}")

def test_model_version_comparison():
    """Compare outputs between model versions."""
    lm_v1 = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    lm_v2 = dspy.LM("openai/gpt-4o", temperature=0.0)

    test_questions = [
        "What is 2+2?",
        "Explain quantum computing.",
        "What is the capital of France?",
    ]

    dspy.configure(lm=lm_v1)
    qa_v1 = dspy.ChainOfThought("question -> answer")
    results_v1 = [qa_v1(question=q).answer for q in test_questions]

    dspy.configure(lm=lm_v2)
    qa_v2 = dspy.ChainOfThought("question -> answer")
    results_v2 = [qa_v2(question=q).answer for q in test_questions]

    # Compare results
    for q, r1, r2 in zip(test_questions, results_v1, results_v2):
        print(f"\nQuestion: {q}")
        print(f"V1: {r1}")
        print(f"V2: {r2}")
        print(f"Same: {r1 == r2}")

    # You can add assertions based on expected behavior
    # e.g., assert similarity score > threshold
```

**When to use**:
- After model updates
- After optimization changes
- Before production deployment
- Continuous monitoring

### Pattern 6: Test Data Generation

```python
import dspy
import random
from typing import List, Dict

class TestDataGenerator:
    """Generate synthetic test data for DSPy programs."""

    @staticmethod
    def generate_qa_pairs(
        num_pairs: int = 10,
        domains: List[str] = None,
    ) -> List[Dict[str, str]]:
        """Generate question-answer pairs."""
        domains = domains or ["math", "geography", "science"]

        templates = {
            "math": [
                ("What is {a} + {b}?", lambda a, b: str(a + b)),
                ("What is {a} * {b}?", lambda a, b: str(a * b)),
            ],
            "geography": [
                ("What is the capital of {country}?", lambda c: f"The capital is {c}_capital"),
            ],
            "science": [
                ("What is the atomic number of {element}?", lambda e: f"Atomic number of {e}"),
            ],
        }

        test_data = []
        for _ in range(num_pairs):
            domain = random.choice(domains)
            template, answer_fn = random.choice(templates[domain])

            if domain == "math":
                a, b = random.randint(1, 20), random.randint(1, 20)
                question = template.format(a=a, b=b)
                answer = answer_fn(a, b)
            elif domain == "geography":
                countries = ["France", "Germany", "Japan"]
                country = random.choice(countries)
                question = template.format(country=country)
                answer = answer_fn(country)
            else:
                elements = ["Hydrogen", "Helium", "Carbon"]
                element = random.choice(elements)
                question = template.format(element=element)
                answer = answer_fn(element)

            test_data.append({"question": question, "answer": answer})

        return test_data

    @staticmethod
    def generate_classification_data(
        num_samples: int = 10,
        categories: List[str] = None,
    ) -> List[Dict[str, str]]:
        """Generate classification test data."""
        categories = categories or ["positive", "negative", "neutral"]

        templates = {
            "positive": [
                "This is amazing!",
                "I love this product!",
                "Excellent service!",
            ],
            "negative": [
                "This is terrible.",
                "I hate this.",
                "Worst experience ever.",
            ],
            "neutral": [
                "This is okay.",
                "It's average.",
                "Nothing special.",
            ],
        }

        test_data = []
        for _ in range(num_samples):
            category = random.choice(categories)
            text = random.choice(templates[category])

            test_data.append({
                "text": text,
                "category": category,
            })

        return test_data

# Usage in tests
def test_with_generated_data():
    """Test QA module with generated data."""
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)

    qa = dspy.Predict("question -> answer")

    # Generate test data
    generator = TestDataGenerator()
    test_data = generator.generate_qa_pairs(num_pairs=5, domains=["math"])

    # Test each pair
    for item in test_data:
        result = qa(question=item["question"])
        print(f"Q: {item['question']}")
        print(f"Expected: {item['answer']}")
        print(f"Got: {result.answer}")
        print()

def test_classifier_with_generated_data():
    """Test classifier with generated data."""
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)

    classifier = dspy.Predict("text -> category")

    generator = TestDataGenerator()
    test_data = generator.generate_classification_data(num_samples=10)

    correct = 0
    for item in test_data:
        result = classifier(text=item["text"])
        if result.category.lower() == item["category"].lower():
            correct += 1

    accuracy = correct / len(test_data)
    print(f"Accuracy: {accuracy:.2%}")

    assert accuracy > 0.5  # Should get more than random
```

**Benefits**:
- Consistent test data
- Cover edge cases systematically
- No manual data creation
- Reproducible tests

### Pattern 7: Coverage Analysis

```python
import dspy
import pytest
from typing import Set, List

class DSPyModuleCoverage:
    """Track which modules and signatures are tested."""

    def __init__(self):
        self.tested_modules: Set[str] = set()
        self.tested_signatures: Set[str] = set()
        self.module_calls: List[dict] = []

    def record_module_call(self, module_name: str, signature: str, inputs: dict):
        """Record a module call for coverage tracking."""
        self.tested_modules.add(module_name)
        self.tested_signatures.add(signature)
        self.module_calls.append({
            "module": module_name,
            "signature": signature,
            "inputs": inputs,
        })

    def get_coverage_report(self, all_modules: Set[str], all_signatures: Set[str]):
        """Generate coverage report."""
        module_coverage = len(self.tested_modules) / len(all_modules) if all_modules else 0
        signature_coverage = len(self.tested_signatures) / len(all_signatures) if all_signatures else 0

        return {
            "module_coverage": module_coverage,
            "signature_coverage": signature_coverage,
            "tested_modules": list(self.tested_modules),
            "tested_signatures": list(self.tested_signatures),
            "total_calls": len(self.module_calls),
            "untested_modules": list(all_modules - self.tested_modules),
            "untested_signatures": list(all_signatures - self.tested_signatures),
        }

# Instrumented module for coverage tracking
class InstrumentedModule(dspy.Module):
    """Wrapper that tracks coverage."""

    def __init__(self, module: dspy.Module, coverage_tracker: DSPyModuleCoverage):
        super().__init__()
        self.module = module
        self.coverage_tracker = coverage_tracker
        self.module_name = module.__class__.__name__

    def forward(self, **kwargs):
        """Execute module and track coverage."""
        # Extract signature if available
        signature = getattr(self.module, "signature", "unknown")

        # Record call
        self.coverage_tracker.record_module_call(
            module_name=self.module_name,
            signature=str(signature),
            inputs=kwargs,
        )

        # Execute module
        return self.module(**kwargs)

# Usage
@pytest.fixture
def coverage_tracker():
    """Create coverage tracker."""
    return DSPyModuleCoverage()

def test_with_coverage(coverage_tracker):
    """Test with coverage tracking."""
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)

    # Create modules
    qa = dspy.Predict("question -> answer")
    cot = dspy.ChainOfThought("question -> answer")

    # Instrument modules
    qa_instrumented = InstrumentedModule(qa, coverage_tracker)
    cot_instrumented = InstrumentedModule(cot, coverage_tracker)

    # Run tests
    qa_instrumented(question="What is 2+2?")
    cot_instrumented(question="Why is sky blue?")

    # Get coverage report
    all_modules = {"Predict", "ChainOfThought", "ReAct"}
    all_signatures = {"question -> answer", "context, question -> answer"}

    report = coverage_tracker.get_coverage_report(all_modules, all_signatures)

    print(f"Module coverage: {report['module_coverage']:.1%}")
    print(f"Signature coverage: {report['signature_coverage']:.1%}")
    print(f"Untested modules: {report['untested_modules']}")

    # Assert minimum coverage
    assert report['module_coverage'] >= 0.5  # At least 50% module coverage
```

**Metrics to track**:
- Module coverage (which modules tested)
- Signature coverage (which signatures tested)
- Branch coverage (different code paths)
- Input space coverage (range of inputs tested)

### Pattern 8: Performance Testing

```python
import dspy
import pytest
import time
from statistics import mean, stdev

def test_module_latency():
    """Test module latency performance."""
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)

    qa = dspy.Predict("question -> answer")

    # Warm up
    qa(question="Warm up")

    # Measure latency
    latencies = []
    num_runs = 10

    for _ in range(num_runs):
        start = time.time()
        qa(question="What is DSPy?")
        latency = time.time() - start
        latencies.append(latency)

    avg_latency = mean(latencies)
    std_latency = stdev(latencies)

    print(f"Average latency: {avg_latency:.3f}s")
    print(f"Std dev: {std_latency:.3f}s")
    print(f"Min: {min(latencies):.3f}s")
    print(f"Max: {max(latencies):.3f}s")

    # Assert performance requirements
    assert avg_latency < 5.0  # Should be under 5 seconds
    assert max(latencies) < 10.0  # No request over 10 seconds

def test_throughput():
    """Test throughput (requests per second)."""
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)

    qa = dspy.Predict("question -> answer")

    num_requests = 100
    start = time.time()

    for i in range(num_requests):
        qa(question=f"Question {i}")

    duration = time.time() - start
    throughput = num_requests / duration

    print(f"Throughput: {throughput:.2f} requests/second")
    print(f"Total duration: {duration:.2f}s")

    # Assert minimum throughput
    assert throughput > 1.0  # At least 1 request per second

@pytest.mark.benchmark
def test_optimized_vs_baseline(benchmark):
    """Benchmark optimized vs baseline program."""
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)

    baseline = dspy.Predict("question -> answer")

    # Benchmark baseline
    result = benchmark(baseline, question="What is DSPy?")

    print(f"Benchmark results: {benchmark.stats}")

def test_memory_usage():
    """Test memory usage of DSPy programs."""
    import tracemalloc

    tracemalloc.start()

    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)

    qa = dspy.Predict("question -> answer")

    # Execute
    qa(question="What is DSPy?")

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Current memory: {current / 1024 / 1024:.2f} MB")
    print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")

    # Assert reasonable memory usage
    assert peak / 1024 / 1024 < 500  # Under 500 MB

# Run benchmarks: pytest test_performance.py --benchmark-only
```

**Performance metrics**:
- Latency (p50, p95, p99)
- Throughput (requests/second)
- Memory usage
- Token usage
- Cost per request

---

## Quick Reference

### pytest Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest test_dspy_module.py

# Run with verbose output
pytest -v

# Run specific test
pytest test_dspy_module.py::test_qa_module_basic

# Run tests by marker
pytest -m integration  # Only integration tests
pytest -m "not slow"   # Skip slow tests

# Run with coverage
pytest --cov=src --cov-report=html

# Run in parallel
pytest -n 4  # 4 parallel workers

# Show print statements
pytest -s

# Stop at first failure
pytest -x
```

### Test Organization

```
tests/
├── unit/              # Fast unit tests with mocks
│   ├── test_modules.py
│   ├── test_signatures.py
│   └── conftest.py   # Shared fixtures
├── integration/       # Integration tests with real LMs
│   ├── test_rag.py
│   └── test_optimization.py
├── regression/        # Regression test data
│   └── test_cases.json
└── performance/       # Performance benchmarks
    └── test_latency.py
```

### Common Fixtures

```python
# conftest.py
import pytest
import dspy

@pytest.fixture(scope="session")
def test_lm():
    """Deterministic test LM."""
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)
    return lm

@pytest.fixture
def mock_lm():
    """Mock LM for fast tests."""
    return MockLM(responses={"default": "Mock response"})

@pytest.fixture
def sample_questions():
    """Sample test questions."""
    return [
        "What is 2+2?",
        "What is the capital of France?",
        "Explain quantum computing.",
    ]
```

---

## Anti-Patterns

❌ **Testing with high temperature**: Non-deterministic failures
```python
# Bad - tests will randomly fail
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.7)
```
✅ Use temperature=0 for tests:
```python
# Good - deterministic
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
```

❌ **Not mocking LM calls**: Slow, expensive tests
```python
# Bad - every test calls API
def test_module():
    qa = dspy.Predict("question -> answer")
    result = qa(question="Test")  # Real API call
```
✅ Mock for unit tests:
```python
# Good - fast, free
def test_module(mock_lm):
    dspy.configure(lm=mock_lm)
    qa = dspy.Predict("question -> answer")
    result = qa(question="Test")  # Mocked
```

❌ **No regression tests**: Breaking changes go unnoticed
```python
# Bad - no baseline to compare against
```
✅ Maintain regression test suite:
```python
# Good - track expected outputs
regression_suite.add_test_case(inputs, expected_output)
```

❌ **Testing exact text matches**: Brittle tests
```python
# Bad - will break with minor wording changes
assert result.answer == "The capital of France is Paris."
```
✅ Test structure and key content:
```python
# Good - flexible matching
assert "Paris" in result.answer
assert len(result.answer) > 10
```

---

## Related Skills

- `dspy-evaluation.md` - Evaluating DSPy program quality
- `dspy-debugging.md` - Debugging failing tests
- `dspy-production.md` - Production testing strategies
- `pytest-advanced.md` - Advanced pytest patterns
- `hypothesis-property-testing.md` - Property-based testing

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
