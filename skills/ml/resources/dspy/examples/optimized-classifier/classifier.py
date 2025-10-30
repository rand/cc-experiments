"""Optimized Text Classifier with DSPy."""

import dspy
from typing import List
import json


# ============================================================================
# CLASSIFIER
# ============================================================================

class TicketClassifier(dspy.Module):
    """Classify support tickets."""

    def __init__(self):
        super().__init__()
        self.classify = dspy.ChainOfThought(
            "text -> category, confidence, reasoning"
        )

        self.categories = ["technical", "billing", "feature_request", "general"]

    def forward(self, text: str) -> dspy.Prediction:
        result = self.classify(text=text)

        # Validate category
        dspy.Assert(
            result.category.lower() in self.categories,
            f"Category must be one of {self.categories}"
        )

        return result


# ============================================================================
# OPTIMIZATION
# ============================================================================

def optimize_classifier(trainset: List[dspy.Example]) -> TicketClassifier:
    """Optimize classifier with MIPROv2."""
    from dspy.teleprompt import MIPROv2

    classifier = TicketClassifier()

    def accuracy(example, prediction, trace=None):
        return float(
            example.category.lower() == prediction.category.lower()
        )

    optimizer = MIPROv2(
        metric=accuracy,
        num_candidates=20,
        init_temperature=1.0,
        verbose=True
    )

    optimized = optimizer.compile(
        classifier,
        trainset=trainset,
        max_bootstrapped_demos=3
    )

    return optimized


# ============================================================================
# EVALUATION
# ============================================================================

def evaluate_classifier(classifier: TicketClassifier, testset: List[dspy.Example]):
    """Evaluate classifier."""
    from dspy.evaluate import Evaluate

    def accuracy(example, prediction, trace=None):
        return float(example.category.lower() == prediction.category.lower())

    evaluator = Evaluate(
        devset=testset,
        metric=accuracy,
        display_progress=True,
        display_table=True
    )

    score = evaluator(classifier)

    print(f"\nAccuracy: {score:.2%}")

    return score


# ============================================================================
# DATA LOADING
# ============================================================================

def load_data(path: str) -> List[dspy.Example]:
    """Load training/test data."""
    with open(path) as f:
        data = json.load(f)

    examples = []
    for item in data:
        examples.append(
            dspy.Example(
                text=item["text"],
                category=item["category"]
            ).with_inputs("text")
        )

    return examples


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["baseline", "optimize", "evaluate"], required=True)
    parser.add_argument("--model", default=None, help="Model path for evaluation")
    parser.add_argument("--num-candidates", type=int, default=10)
    args = parser.parse_args()

    # Configure
    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    if args.mode == "baseline":
        print("Training baseline classifier...")

        trainset = load_data("data/train.json")
        testset = load_data("data/test.json")

        classifier = TicketClassifier()

        print("\nEvaluating baseline...")
        evaluate_classifier(classifier, testset)

    elif args.mode == "optimize":
        print("Optimizing classifier...")

        trainset = load_data("data/train.json")
        testset = load_data("data/test.json")

        optimized = optimize_classifier(trainset)

        print("\nEvaluating optimized classifier...")
        evaluate_classifier(optimized, testset)

        # Save
        optimized.save("models/optimized.json")
        print("\n✓ Saved to models/optimized.json")

    elif args.mode == "evaluate":
        print("Evaluating model...")

        testset = load_data("data/test.json")

        classifier = TicketClassifier()
        if args.model:
            classifier.load(args.model)

        evaluate_classifier(classifier, testset)


if __name__ == "__main__":
    main()
