"""
DSPy Metric Function Templates

Collection of metric templates for evaluating DSPy programs during
optimization and evaluation.
"""

import dspy
from typing import Optional, List, Dict, Any
import re
from difflib import SequenceMatcher
from collections import Counter


# ============================================================================
# BASIC METRICS
# ============================================================================

def exact_match(example: dspy.Example, prediction: dspy.Prediction, trace: Optional[Any] = None) -> float:
    """Exact string match metric.

    Returns 1.0 if prediction exactly matches expected answer, 0.0 otherwise.

    Args:
        example: Ground truth example
        prediction: Model prediction
        trace: Optional execution trace (unused)

    Returns:
        1.0 if exact match, 0.0 otherwise

    Example:
        ```python
        metric = exact_match
        optimizer = BootstrapFewShot(metric=metric)
        ```
    """
    expected = example.answer.strip().lower()
    predicted = prediction.answer.strip().lower()
    return 1.0 if expected == predicted else 0.0


def contains_match(example: dspy.Example, prediction: dspy.Prediction, trace: Optional[Any] = None) -> float:
    """Substring containment metric.

    Returns 1.0 if expected answer is contained in prediction.

    Args:
        example: Ground truth example
        prediction: Model prediction
        trace: Optional execution trace

    Returns:
        1.0 if expected is in predicted, 0.0 otherwise
    """
    expected = example.answer.strip().lower()
    predicted = prediction.answer.strip().lower()
    return 1.0 if expected in predicted else 0.0


def similarity_score(example: dspy.Example, prediction: dspy.Prediction, trace: Optional[Any] = None) -> float:
    """String similarity metric using SequenceMatcher.

    Returns similarity ratio between 0.0 and 1.0.

    Args:
        example: Ground truth example
        prediction: Model prediction
        trace: Optional execution trace

    Returns:
        Similarity score between 0.0 and 1.0
    """
    expected = example.answer.strip().lower()
    predicted = prediction.answer.strip().lower()
    return SequenceMatcher(None, expected, predicted).ratio()


# ============================================================================
# CLASSIFICATION METRICS
# ============================================================================

def classification_accuracy(example: dspy.Example, prediction: dspy.Prediction, trace: Optional[Any] = None) -> float:
    """Classification accuracy for single-label classification.

    Args:
        example: Example with 'label' field
        prediction: Prediction with 'label' field

    Returns:
        1.0 if labels match, 0.0 otherwise

    Example:
        ```python
        example = dspy.Example(text="...", label="positive")
        prediction = classifier(text=example.text)
        score = classification_accuracy(example, prediction)
        ```
    """
    expected_label = example.label.strip().lower()
    predicted_label = prediction.label.strip().lower()
    return 1.0 if expected_label == predicted_label else 0.0


def multi_label_f1(example: dspy.Example, prediction: dspy.Prediction, trace: Optional[Any] = None) -> float:
    """F1 score for multi-label classification.

    Args:
        example: Example with 'labels' field (list)
        prediction: Prediction with 'labels' field (list)

    Returns:
        F1 score between 0.0 and 1.0

    Example:
        ```python
        example = dspy.Example(text="...", labels=["tech", "ai"])
        prediction = classifier(text=example.text)
        score = multi_label_f1(example, prediction)
        ```
    """
    expected = set(label.lower() for label in example.labels)
    predicted = set(label.lower() for label in prediction.labels)

    if not expected and not predicted:
        return 1.0

    if not expected or not predicted:
        return 0.0

    # Calculate precision and recall
    true_positives = len(expected & predicted)
    precision = true_positives / len(predicted) if predicted else 0.0
    recall = true_positives / len(expected) if expected else 0.0

    # F1 score
    if precision + recall == 0:
        return 0.0

    f1 = 2 * (precision * recall) / (precision + recall)
    return f1


# ============================================================================
# QA METRICS
# ============================================================================

def qa_accuracy(example: dspy.Example, prediction: dspy.Prediction, trace: Optional[Any] = None) -> float:
    """QA accuracy with multiple acceptable answers.

    Args:
        example: Example with 'answers' field (list of acceptable answers)
        prediction: Prediction with 'answer' field

    Returns:
        1.0 if prediction matches any acceptable answer, 0.0 otherwise

    Example:
        ```python
        example = dspy.Example(
            question="What is 2+2?",
            answers=["4", "four", "Four"]
        )
        ```
    """
    predicted = prediction.answer.strip().lower()

    # Check if matches any acceptable answer
    for acceptable in example.answers:
        if predicted == acceptable.strip().lower():
            return 1.0

    return 0.0


def qa_f1(example: dspy.Example, prediction: dspy.Prediction, trace: Optional[Any] = None) -> float:
    """Token-level F1 score for QA (SQuAD-style).

    Args:
        example: Example with 'answer' field
        prediction: Prediction with 'answer' field

    Returns:
        F1 score between 0.0 and 1.0

    Example:
        ```python
        example = dspy.Example(answer="The capital of France is Paris")
        prediction = qa_system(question="What is the capital of France?")
        score = qa_f1(example, prediction)
        ```
    """
    expected_tokens = example.answer.lower().split()
    predicted_tokens = prediction.answer.lower().split()

    # Count token frequencies
    expected_counts = Counter(expected_tokens)
    predicted_counts = Counter(predicted_tokens)

    # Calculate overlap
    overlap = sum((expected_counts & predicted_counts).values())

    if overlap == 0:
        return 0.0

    # Precision and recall
    precision = overlap / len(predicted_tokens) if predicted_tokens else 0.0
    recall = overlap / len(expected_tokens) if expected_tokens else 0.0

    # F1 score
    if precision + recall == 0:
        return 0.0

    f1 = 2 * (precision * recall) / (precision + recall)
    return f1


# ============================================================================
# COMPOSITE METRICS
# ============================================================================

def correctness_and_length(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace: Optional[Any] = None,
    min_length: int = 50,
    max_length: int = 200
) -> float:
    """Composite metric: Correctness AND appropriate length.

    Args:
        example: Ground truth example
        prediction: Model prediction
        trace: Optional trace
        min_length: Minimum acceptable length
        max_length: Maximum acceptable length

    Returns:
        1.0 if correct AND length is appropriate, 0.0 otherwise

    Example:
        ```python
        metric = lambda ex, pred, trace: correctness_and_length(
            ex, pred, trace, min_length=30, max_length=150
        )
        ```
    """
    # Check correctness
    correct = example.answer.lower() in prediction.answer.lower()

    # Check length
    length = len(prediction.answer)
    length_ok = min_length <= length <= max_length

    # Both must be satisfied
    return 1.0 if correct and length_ok else 0.0


def weighted_metric(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace: Optional[Any] = None,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """Weighted combination of multiple criteria.

    Args:
        example: Ground truth example
        prediction: Model prediction
        trace: Optional trace
        weights: Dictionary of criterion weights (must sum to 1.0)

    Returns:
        Weighted score between 0.0 and 1.0

    Example:
        ```python
        metric = lambda ex, pred, trace: weighted_metric(
            ex, pred, trace,
            weights={
                "correctness": 0.6,
                "conciseness": 0.2,
                "fluency": 0.2
            }
        )
        ```
    """
    if weights is None:
        weights = {
            "correctness": 0.5,
            "length": 0.3,
            "fluency": 0.2
        }

    scores = {}

    # Correctness
    expected = example.answer.lower()
    predicted = prediction.answer.lower()
    scores["correctness"] = 1.0 if expected in predicted else 0.0

    # Conciseness (shorter is better, up to a point)
    length = len(prediction.answer)
    target_length = 100  # Adjust based on task
    scores["conciseness"] = max(0.0, 1.0 - abs(length - target_length) / target_length)

    # Fluency (basic check: no incomplete sentences)
    ends_with_punct = prediction.answer.strip()[-1] in ".!?"
    scores["fluency"] = 1.0 if ends_with_punct else 0.5

    # Weighted sum
    total = sum(scores.get(k, 0.0) * w for k, w in weights.items())
    return total


# ============================================================================
# CONSTRAINT-BASED METRICS
# ============================================================================

def constraint_satisfaction(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace: Optional[Any] = None,
    constraints: Optional[List[callable]] = None
) -> float:
    """Metric based on constraint satisfaction.

    Args:
        example: Ground truth example
        prediction: Model prediction
        trace: Optional trace
        constraints: List of constraint functions (pred -> bool)

    Returns:
        Fraction of constraints satisfied (0.0 to 1.0)

    Example:
        ```python
        constraints = [
            lambda p: len(p.answer) > 20,
            lambda p: "because" in p.answer.lower(),
            lambda p: not any(word in p.answer.lower() for word in ["maybe", "perhaps"])
        ]
        metric = lambda ex, pred, trace: constraint_satisfaction(
            ex, pred, trace, constraints=constraints
        )
        ```
    """
    if constraints is None:
        # Default constraints
        constraints = [
            lambda p: len(p.answer) > 0,
            lambda p: len(p.answer) < 1000,
        ]

    satisfied = sum(1 for constraint in constraints if constraint(prediction))
    total = len(constraints)

    return satisfied / total if total > 0 else 0.0


# ============================================================================
# RETRIEVAL METRICS
# ============================================================================

def retrieval_precision_at_k(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace: Optional[Any] = None,
    k: int = 5
) -> float:
    """Precision@k for retrieval tasks.

    Args:
        example: Example with 'relevant_ids' field (list of relevant doc IDs)
        prediction: Prediction with 'retrieved_ids' field (list of retrieved doc IDs)
        trace: Optional trace
        k: Number of top results to consider

    Returns:
        Precision@k score between 0.0 and 1.0

    Example:
        ```python
        example = dspy.Example(
            query="...",
            relevant_ids=["doc1", "doc3", "doc5"]
        )
        prediction = retriever(query=example.query)
        score = retrieval_precision_at_k(example, prediction, k=5)
        ```
    """
    relevant = set(example.relevant_ids)
    retrieved = prediction.retrieved_ids[:k]

    if not retrieved:
        return 0.0

    relevant_retrieved = sum(1 for doc_id in retrieved if doc_id in relevant)
    return relevant_retrieved / len(retrieved)


def retrieval_recall_at_k(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace: Optional[Any] = None,
    k: int = 5
) -> float:
    """Recall@k for retrieval tasks.

    Args:
        example: Example with 'relevant_ids' field
        prediction: Prediction with 'retrieved_ids' field
        trace: Optional trace
        k: Number of top results to consider

    Returns:
        Recall@k score between 0.0 and 1.0
    """
    relevant = set(example.relevant_ids)
    retrieved = prediction.retrieved_ids[:k]

    if not relevant:
        return 0.0

    relevant_retrieved = sum(1 for doc_id in retrieved if doc_id in relevant)
    return relevant_retrieved / len(relevant)


# ============================================================================
# CUSTOM METRIC FACTORY
# ============================================================================

class MetricFactory:
    """Factory for creating custom metrics with configurable parameters.

    Example:
        ```python
        factory = MetricFactory()

        # Create metric with custom thresholds
        metric = factory.create_threshold_metric(
            field="answer",
            min_length=50,
            max_length=200,
            required_keywords=["because", "therefore"]
        )

        # Use in optimization
        optimizer = BootstrapFewShot(metric=metric)
        ```
    """

    @staticmethod
    def create_threshold_metric(
        field: str = "answer",
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        required_keywords: Optional[List[str]] = None,
        forbidden_keywords: Optional[List[str]] = None
    ) -> callable:
        """Create metric with length and keyword constraints.

        Args:
            field: Field name to evaluate
            min_length: Minimum length requirement
            max_length: Maximum length requirement
            required_keywords: Keywords that must appear
            forbidden_keywords: Keywords that must not appear

        Returns:
            Metric function
        """
        def metric(example, prediction, trace=None):
            text = getattr(prediction, field, "")

            # Check correctness first
            if not hasattr(example, field):
                return 0.0

            expected = getattr(example, field).lower()
            if expected not in text.lower():
                return 0.0

            # Check length constraints
            if min_length and len(text) < min_length:
                return 0.0
            if max_length and len(text) > max_length:
                return 0.0

            # Check required keywords
            if required_keywords:
                text_lower = text.lower()
                if not all(kw.lower() in text_lower for kw in required_keywords):
                    return 0.0

            # Check forbidden keywords
            if forbidden_keywords:
                text_lower = text.lower()
                if any(kw.lower() in text_lower for kw in forbidden_keywords):
                    return 0.0

            return 1.0

        return metric

    @staticmethod
    def create_regex_metric(
        field: str = "answer",
        pattern: str = r".*",
        match_required: bool = True
    ) -> callable:
        """Create metric based on regex pattern matching.

        Args:
            field: Field name to evaluate
            pattern: Regex pattern
            match_required: Whether match is required (True) or forbidden (False)

        Returns:
            Metric function

        Example:
            ```python
            # Require answer to start with number
            metric = MetricFactory.create_regex_metric(
                field="answer",
                pattern=r"^\d+",
                match_required=True
            )
            ```
        """
        compiled_pattern = re.compile(pattern)

        def metric(example, prediction, trace=None):
            text = getattr(prediction, field, "")
            matches = bool(compiled_pattern.search(text))

            # If match required, return 1 if matches
            # If match forbidden, return 1 if doesn't match
            return 1.0 if matches == match_required else 0.0

        return metric


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_basic_metrics():
    """Example: Using basic metrics."""
    import dspy

    example = dspy.Example(
        question="What is 2+2?",
        answer="4"
    )

    prediction = dspy.Prediction(
        question="What is 2+2?",
        answer="The answer is 4"
    )

    # Test metrics
    print(f"Exact match: {exact_match(example, prediction)}")
    print(f"Contains: {contains_match(example, prediction)}")
    print(f"Similarity: {similarity_score(example, prediction):.2f}")


def example_composite_metric():
    """Example: Using composite metrics in optimization."""
    import dspy
    from dspy.teleprompt import BootstrapFewShot

    # Define composite metric
    def my_metric(example, prediction, trace=None):
        return correctness_and_length(
            example, prediction, trace,
            min_length=30,
            max_length=150
        )

    # Use in optimization
    # optimizer = BootstrapFewShot(metric=my_metric)
    # optimized = optimizer.compile(program, trainset=train)


def example_custom_metric():
    """Example: Creating custom metric with factory."""
    factory = MetricFactory()

    # Create metric with specific requirements
    metric = factory.create_threshold_metric(
        field="answer",
        min_length=50,
        required_keywords=["because", "therefore"],
        forbidden_keywords=["maybe", "I think"]
    )

    # Use metric
    # optimizer = BootstrapFewShot(metric=metric)


if __name__ == "__main__":
    # Uncomment to run examples
    # example_basic_metrics()
    # example_composite_metric()
    # example_custom_metric()
    pass
