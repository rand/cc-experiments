"""
DSPy Test Suite Template

Comprehensive testing template for DSPy programs including:
- Unit tests with mocking
- Integration tests
- Property-based tests
- Performance tests
- Regression tests
"""

import pytest
import dspy
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import time
import json
from hypothesis import given, strategies as st


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_lm():
    """Mock language model for unit tests.

    Returns:
        Mock LM that returns predefined responses
    """
    mock = Mock()
    mock.return_value = dspy.Prediction(
        answer="Mock answer",
        reasoning="Mock reasoning"
    )
    return mock


@pytest.fixture
def configured_dspy(mock_lm):
    """Configure DSPy with mock LM.

    Args:
        mock_lm: Mock language model fixture

    Yields:
        Configured DSPy settings
    """
    # Save original settings
    original_lm = dspy.settings.lm if hasattr(dspy.settings, 'lm') else None

    # Configure with mock
    dspy.settings.configure(lm=mock_lm)

    yield dspy.settings

    # Restore original settings
    if original_lm:
        dspy.settings.configure(lm=original_lm)


@pytest.fixture
def sample_examples() -> List[dspy.Example]:
    """Sample examples for testing.

    Returns:
        List of example instances
    """
    return [
        dspy.Example(
            question="What is 2+2?",
            answer="4"
        ).with_inputs("question"),
        dspy.Example(
            question="What is the capital of France?",
            answer="Paris"
        ).with_inputs("question"),
        dspy.Example(
            question="What is Python?",
            answer="A programming language"
        ).with_inputs("question"),
    ]


@pytest.fixture
def sample_trainset() -> List[dspy.Example]:
    """Larger training set for optimization tests."""
    examples = []
    for i in range(50):
        examples.append(
            dspy.Example(
                question=f"Question {i}",
                answer=f"Answer {i}"
            ).with_inputs("question")
        )
    return examples


# ============================================================================
# EXAMPLE MODULE TO TEST
# ============================================================================

class QAModule(dspy.Module):
    """Example QA module for testing."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought("question -> answer")

    def forward(self, question: str) -> dspy.Prediction:
        result = self.generate(question=question)

        # Assertion
        dspy.Assert(len(result.answer) > 0, "Answer cannot be empty")

        return result


# ============================================================================
# UNIT TESTS
# ============================================================================

class TestQAModule:
    """Unit tests for QA module."""

    def test_module_initialization(self):
        """Test module can be initialized."""
        module = QAModule()
        assert module is not None
        assert hasattr(module, 'generate')

    def test_forward_with_mock_lm(self, configured_dspy):
        """Test forward pass with mocked LM."""
        module = QAModule()

        # Mock LM response
        configured_dspy.lm.return_value = dspy.Prediction(
            answer="Paris",
            reasoning="Paris is the capital of France"
        )

        # Execute
        result = module(question="What is the capital of France?")

        # Assertions
        assert result.answer == "Paris"
        assert hasattr(result, 'reasoning')
        configured_dspy.lm.assert_called_once()

    def test_empty_answer_assertion(self, configured_dspy):
        """Test assertion failure for empty answer."""
        module = QAModule()

        # Mock empty answer
        configured_dspy.lm.return_value = dspy.Prediction(
            answer="",
            reasoning="No answer"
        )

        # Should raise assertion error
        with pytest.raises(dspy.AssertionError):
            module(question="Test question")

    @pytest.mark.parametrize("question,expected_contains", [
        ("What is 2+2?", "4"),
        ("What is Python?", "language"),
        ("What is the capital of France?", "Paris"),
    ])
    def test_multiple_questions(self, configured_dspy, question, expected_contains):
        """Test module with multiple questions."""
        module = QAModule()

        configured_dspy.lm.return_value = dspy.Prediction(
            answer=expected_contains,
            reasoning="Mock reasoning"
        )

        result = module(question=question)
        assert expected_contains.lower() in result.answer.lower()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not hasattr(dspy.settings, 'lm'),
    reason="No LM configured for integration tests"
)
class TestQAIntegration:
    """Integration tests with real LM."""

    def test_real_lm_call(self):
        """Test with real language model."""
        module = QAModule()

        result = module(question="What is 2+2?")

        assert result.answer is not None
        assert len(result.answer) > 0
        assert "4" in result.answer or "four" in result.answer.lower()

    def test_multiple_calls(self):
        """Test multiple sequential calls."""
        module = QAModule()

        questions = [
            "What is 2+2?",
            "What is 3+3?",
            "What is 5+5?"
        ]

        for question in questions:
            result = module(question=question)
            assert result.answer is not None
            assert len(result.answer) > 0

    def test_with_retrieval(self, configured_dspy):
        """Test RAG pipeline integration."""
        # Skip if no retriever configured
        if not hasattr(dspy.settings, 'rm'):
            pytest.skip("No retriever configured")

        class RAGModule(dspy.Module):
            def __init__(self):
                super().__init__()
                self.retrieve = dspy.Retrieve(k=3)
                self.generate = dspy.ChainOfThought("context, question -> answer")

            def forward(self, question):
                context = self.retrieve(question).passages
                return self.generate(context=context, question=question)

        module = RAGModule()
        result = module(question="What is Python?")

        assert result.answer is not None
        assert len(result.answer) > 0


# ============================================================================
# PROPERTY-BASED TESTS
# ============================================================================

@pytest.mark.property
class TestQAProperties:
    """Property-based tests using Hypothesis."""

    @given(question=st.text(min_size=1, max_size=100))
    def test_any_nonempty_question_produces_answer(self, configured_dspy, question):
        """Property: Any non-empty question should produce non-empty answer."""
        module = QAModule()

        configured_dspy.lm.return_value = dspy.Prediction(
            answer="Test answer",
            reasoning="Test reasoning"
        )

        try:
            result = module(question=question)
            assert len(result.answer) > 0
        except dspy.AssertionError:
            # Expected for invalid inputs
            pass

    @given(
        question=st.text(min_size=10, max_size=200),
        answer=st.text(min_size=1, max_size=100)
    )
    def test_answer_reproducibility(self, configured_dspy, question, answer):
        """Property: Same question should produce same answer (with mocking)."""
        module = QAModule()

        configured_dspy.lm.return_value = dspy.Prediction(
            answer=answer,
            reasoning="Test"
        )

        result1 = module(question=question)
        result2 = module(question=question)

        assert result1.answer == result2.answer


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.performance
class TestQAPerformance:
    """Performance and load tests."""

    def test_latency_under_threshold(self, configured_dspy):
        """Test latency is under acceptable threshold."""
        module = QAModule()

        configured_dspy.lm.return_value = dspy.Prediction(
            answer="Test answer",
            reasoning="Test reasoning"
        )

        start = time.time()
        result = module(question="Test question")
        duration = time.time() - start

        # Assert under 100ms for mocked call
        assert duration < 0.1, f"Call took {duration:.3f}s, expected <0.1s"

    def test_throughput(self, configured_dspy):
        """Test throughput under load."""
        module = QAModule()

        configured_dspy.lm.return_value = dspy.Prediction(
            answer="Test answer",
            reasoning="Test reasoning"
        )

        num_requests = 100
        start = time.time()

        for i in range(num_requests):
            module(question=f"Question {i}")

        duration = time.time() - start
        throughput = num_requests / duration

        # Assert >50 req/s for mocked calls
        assert throughput > 50, f"Throughput: {throughput:.1f} req/s, expected >50 req/s"

    @pytest.mark.slow
    def test_memory_usage(self, configured_dspy):
        """Test memory doesn't grow unbounded."""
        import psutil
        import os

        module = QAModule()
        process = psutil.Process(os.getpid())

        configured_dspy.lm.return_value = dspy.Prediction(
            answer="Test answer",
            reasoning="Test reasoning"
        )

        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run many requests
        for i in range(1000):
            module(question=f"Question {i}")

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Assert <50MB growth
        assert memory_growth < 50, f"Memory grew by {memory_growth:.1f}MB"


# ============================================================================
# EVALUATION TESTS
# ============================================================================

@pytest.mark.evaluation
class TestQAEvaluation:
    """Evaluation metric tests."""

    def test_evaluation_metric(self, sample_examples):
        """Test custom evaluation metric."""
        def accuracy(example, prediction, trace=None):
            expected = example.answer.lower()
            predicted = prediction.answer.lower()
            return 1.0 if expected in predicted else 0.0

        # Test metric
        example = sample_examples[0]
        prediction = dspy.Prediction(answer="The answer is 4")

        score = accuracy(example, prediction)
        assert score == 1.0

    def test_evaluation_on_devset(self, configured_dspy, sample_examples):
        """Test evaluation on development set."""
        module = QAModule()

        configured_dspy.lm.return_value = dspy.Prediction(
            answer="Correct answer",
            reasoning="Test"
        )

        def metric(example, prediction, trace=None):
            return 1.0  # Always correct for test

        from dspy.evaluate import Evaluate
        evaluator = Evaluate(
            devset=sample_examples[:5],
            metric=metric,
            display_progress=False
        )

        score = evaluator(module)
        assert score == 1.0  # 100% with mock


# ============================================================================
# OPTIMIZATION TESTS
# ============================================================================

@pytest.mark.optimization
@pytest.mark.slow
class TestQAOptimization:
    """Tests for optimization/compilation."""

    def test_bootstrap_compilation(self, configured_dspy, sample_trainset):
        """Test BootstrapFewShot optimization."""
        from dspy.teleprompt import BootstrapFewShot

        module = QAModule()

        # Mock LM for bootstrap
        configured_dspy.lm.return_value = dspy.Prediction(
            answer="Bootstrapped answer",
            reasoning="Bootstrapped reasoning"
        )

        def metric(example, prediction, trace=None):
            return 1.0

        optimizer = BootstrapFewShot(
            metric=metric,
            max_bootstrapped_demos=2,
            max_rounds=1
        )

        optimized = optimizer.compile(
            module,
            trainset=sample_trainset[:10]  # Small subset for speed
        )

        assert optimized is not None

    def test_compiled_model_serialization(self, configured_dspy, sample_trainset):
        """Test saving and loading compiled models."""
        from dspy.teleprompt import BootstrapFewShot
        import tempfile
        import os

        module = QAModule()

        configured_dspy.lm.return_value = dspy.Prediction(
            answer="Test",
            reasoning="Test"
        )

        def metric(example, prediction, trace=None):
            return 1.0

        optimizer = BootstrapFewShot(metric=metric, max_rounds=1)
        optimized = optimizer.compile(module, trainset=sample_trainset[:5])

        # Save
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
            optimized.save(temp_path)

        # Load
        loaded = QAModule()
        loaded.load(temp_path)

        # Cleanup
        os.unlink(temp_path)

        assert loaded is not None


# ============================================================================
# REGRESSION TESTS
# ============================================================================

@pytest.mark.regression
class TestQARegression:
    """Regression tests for known issues."""

    def test_empty_question_handling(self, configured_dspy):
        """Regression: Empty questions should be handled."""
        module = QAModule()

        configured_dspy.lm.return_value = dspy.Prediction(
            answer="Cannot answer empty question",
            reasoning="No question provided"
        )

        # Should not crash
        result = module(question="")
        assert result is not None

    def test_very_long_question(self, configured_dspy):
        """Regression: Long questions should be handled."""
        module = QAModule()

        configured_dspy.lm.return_value = dspy.Prediction(
            answer="Answer",
            reasoning="Reasoning"
        )

        long_question = "What is " + "very " * 100 + "long question?"
        result = module(question=long_question)

        assert result is not None
        assert len(result.answer) > 0

    def test_special_characters(self, configured_dspy):
        """Regression: Special characters should be handled."""
        module = QAModule()

        configured_dspy.lm.return_value = dspy.Prediction(
            answer="Answer",
            reasoning="Reasoning"
        )

        special_question = "What is <>&\"'?"
        result = module(question=special_question)

        assert result is not None


# ============================================================================
# TEST UTILITIES
# ============================================================================

class TestHelpers:
    """Helper functions for testing."""

    @staticmethod
    def create_mock_prediction(answer: str, **kwargs) -> dspy.Prediction:
        """Create mock prediction with defaults.

        Args:
            answer: Answer text
            **kwargs: Additional fields

        Returns:
            Mock prediction
        """
        fields = {"answer": answer, "reasoning": "Mock reasoning"}
        fields.update(kwargs)
        return dspy.Prediction(**fields)

    @staticmethod
    def assert_prediction_valid(prediction: dspy.Prediction):
        """Assert prediction has required fields.

        Args:
            prediction: Prediction to validate
        """
        assert hasattr(prediction, 'answer')
        assert prediction.answer is not None
        assert len(prediction.answer) > 0


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: Integration tests (require LM)")
    config.addinivalue_line("markers", "property: Property-based tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "evaluation: Evaluation tests")
    config.addinivalue_line("markers", "optimization: Optimization tests (slow)")
    config.addinivalue_line("markers", "regression: Regression tests")
    config.addinivalue_line("markers", "slow: Slow tests (>1s)")


# ============================================================================
# USAGE
# ============================================================================

"""
Run tests with:

# All tests
pytest test_suite.py -v

# Only unit tests (fast)
pytest test_suite.py -v -m "not integration and not slow"

# Only integration tests
pytest test_suite.py -v -m integration

# With coverage
pytest test_suite.py --cov=your_module --cov-report=html

# Parallel execution
pytest test_suite.py -n auto

# Stop on first failure
pytest test_suite.py -x

# Run specific test class
pytest test_suite.py::TestQAModule -v

# Run with hypothesis verbose output
pytest test_suite.py -v --hypothesis-show-statistics
"""

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
