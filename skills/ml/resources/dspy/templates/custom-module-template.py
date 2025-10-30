"""
Custom DSPy Module Template

Use this template to create custom DSPy modules with proper structure,
error handling, and best practices.
"""

import dspy
from typing import Optional, List, Any, Dict


# ============================================================================
# SIGNATURE DEFINITIONS
# ============================================================================

class YourSignature(dspy.Signature):
    """[Brief description of what this signature does]

    Examples:
        - Input: [example input]
          Output: [example output]
    """

    # Input fields
    input_field: str = dspy.InputField(
        desc="Description of input field"
    )

    # Optional input with default
    optional_input: Optional[str] = dspy.InputField(
        desc="Optional input field",
        default=None
    )

    # Output fields
    output_field: str = dspy.OutputField(
        desc="Description of output field"
    )

    # Additional output (reasoning, confidence, etc.)
    reasoning: str = dspy.OutputField(
        desc="Step-by-step reasoning",
        prefix="Reasoning:"
    )


# ============================================================================
# CUSTOM MODULE
# ============================================================================

class YourModule(dspy.Module):
    """[Brief description of your module]

    This module [what it does and why it's useful].

    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2
        max_retries: Maximum retries on assertion failure

    Example:
        ```python
        module = YourModule(param1="value")
        result = module(input_field="example")
        print(result.output_field)
        ```

    Attributes:
        component1: Description of internal component
        component2: Description of internal component
    """

    def __init__(
        self,
        param1: str,
        param2: int = 10,
        max_retries: int = 3,
        cache_enabled: bool = True
    ):
        """Initialize the module.

        Args:
            param1: Description
            param2: Description with default
            max_retries: Retry attempts for assertions
            cache_enabled: Whether to cache LM calls
        """
        super().__init__()

        # Store configuration
        self.param1 = param1
        self.param2 = param2
        self.max_retries = max_retries
        self.cache_enabled = cache_enabled

        # Initialize internal components
        self.predictor = dspy.ChainOfThought(YourSignature)

        # Optional: Add additional predictors
        self.preprocessor = dspy.Predict("input -> processed_input")
        self.postprocessor = dspy.Predict("output -> refined_output")

        # Optional: Initialize cache
        if cache_enabled:
            from functools import lru_cache
            self._cached_forward = lru_cache(maxsize=100)(self._forward_impl)

    def forward(
        self,
        input_field: str,
        optional_input: Optional[str] = None,
        **kwargs
    ) -> dspy.Prediction:
        """Execute the module's forward pass.

        Args:
            input_field: Primary input
            optional_input: Optional additional input
            **kwargs: Additional parameters passed to predictors

        Returns:
            dspy.Prediction containing:
                - output_field: Primary output
                - reasoning: Step-by-step reasoning
                - metadata: Additional information

        Raises:
            ValueError: If input validation fails
            dspy.AssertionError: If output assertions fail

        Example:
            ```python
            result = module(input_field="example")
            print(result.output_field)
            ```
        """
        # Validate inputs
        self._validate_inputs(input_field, optional_input)

        # Use cache if enabled
        if self.cache_enabled:
            return self._cached_forward(input_field, optional_input, **kwargs)
        else:
            return self._forward_impl(input_field, optional_input, **kwargs)

    def _forward_impl(
        self,
        input_field: str,
        optional_input: Optional[str],
        **kwargs
    ) -> dspy.Prediction:
        """Internal forward implementation (potentially cached).

        Separate from forward() to allow caching while preserving
        validation logic.
        """
        # Step 1: Preprocessing (optional)
        processed = self._preprocess(input_field, optional_input)

        # Step 2: Main prediction
        prediction = self.predictor(
            input_field=processed,
            optional_input=optional_input,
            **kwargs
        )

        # Step 3: Validate outputs with assertions
        self._validate_outputs(prediction)

        # Step 4: Postprocessing (optional)
        refined = self._postprocess(prediction)

        # Step 5: Add metadata
        refined.metadata = self._create_metadata(prediction)

        return refined

    def _preprocess(
        self,
        input_field: str,
        optional_input: Optional[str]
    ) -> str:
        """Preprocess inputs before main prediction.

        Override this method for custom preprocessing logic.
        """
        # Example: Clean, normalize, or transform input
        processed = input_field.strip()

        if optional_input:
            processed = f"{processed} | {optional_input}"

        return processed

    def _postprocess(self, prediction: dspy.Prediction) -> dspy.Prediction:
        """Postprocess outputs after main prediction.

        Override this method for custom postprocessing logic.
        """
        # Example: Clean, format, or refine output
        prediction.output_field = prediction.output_field.strip()

        return prediction

    def _validate_inputs(
        self,
        input_field: str,
        optional_input: Optional[str]
    ) -> None:
        """Validate input parameters.

        Raises:
            ValueError: If validation fails
        """
        if not input_field:
            raise ValueError("input_field cannot be empty")

        if len(input_field) > 10000:
            raise ValueError("input_field exceeds maximum length (10000)")

        # Add custom validation logic here

    def _validate_outputs(self, prediction: dspy.Prediction) -> None:
        """Validate outputs with DSPy assertions.

        Raises:
            dspy.AssertionError: If assertions fail
        """
        # Hard assertion: Must be satisfied
        dspy.Assert(
            len(prediction.output_field) > 0,
            "Output cannot be empty"
        )

        # Soft suggestion: Preferred but not required
        dspy.Suggest(
            len(prediction.output_field) > 10,
            "Output should be detailed (>10 chars)",
            target_module=self.predictor
        )

        # Example: Check for specific patterns
        dspy.Assert(
            prediction.output_field not in ["I don't know", "N/A"],
            "Output must be informative"
        )

        # Add custom validation logic here

    def _create_metadata(self, prediction: dspy.Prediction) -> Dict[str, Any]:
        """Create metadata dictionary for prediction.

        Returns:
            Dictionary with metadata fields
        """
        return {
            "module_name": self.__class__.__name__,
            "param1": self.param1,
            "param2": self.param2,
            "output_length": len(prediction.output_field),
            "has_reasoning": hasattr(prediction, "reasoning"),
            # Add custom metadata fields here
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"param1={self.param1!r}, "
            f"param2={self.param2}, "
            f"cache_enabled={self.cache_enabled})"
        )


# ============================================================================
# STATEFUL MODULE (WITH MEMORY)
# ============================================================================

class StatefulYourModule(YourModule):
    """Stateful variant with conversation memory.

    Extends YourModule with conversation history tracking.

    Example:
        ```python
        module = StatefulYourModule(param1="value", max_history=5)

        result1 = module(input_field="First query")
        result2 = module(input_field="Follow-up query")  # Has context

        module.clear_history()  # Reset state
        ```
    """

    def __init__(self, *args, max_history: int = 10, **kwargs):
        """Initialize with history tracking.

        Args:
            max_history: Maximum conversation turns to remember
            *args, **kwargs: Passed to parent YourModule
        """
        super().__init__(*args, **kwargs)
        self.history: List[Dict[str, str]] = []
        self.max_history = max_history

    def forward(self, input_field: str, **kwargs) -> dspy.Prediction:
        """Forward pass with history context."""
        # Add history to context (if any)
        if self.history:
            context = self._format_history()
            input_field = f"Context:\n{context}\n\nCurrent: {input_field}"

        # Call parent forward
        result = super().forward(input_field=input_field, **kwargs)

        # Update history
        self._update_history(input_field, result.output_field)

        return result

    def _format_history(self) -> str:
        """Format conversation history as context string."""
        lines = []
        for turn in self.history[-self.max_history:]:
            lines.append(f"Q: {turn['input']}")
            lines.append(f"A: {turn['output']}")
        return "\n".join(lines)

    def _update_history(self, input_field: str, output: str) -> None:
        """Add turn to history and maintain max length."""
        self.history.append({
            "input": input_field,
            "output": output
        })

        # Trim to max_history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.history = []


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_basic_usage():
    """Example: Basic module usage."""
    import dspy

    # Configure LM
    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    # Create module
    module = YourModule(param1="example", param2=5)

    # Run
    result = module(input_field="Test input")

    print(f"Output: {result.output_field}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Metadata: {result.metadata}")


def example_stateful_usage():
    """Example: Stateful module with history."""
    import dspy

    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    # Create stateful module
    module = StatefulYourModule(param1="example", max_history=5)

    # Conversation
    result1 = module(input_field="What is AI?")
    print(f"Answer 1: {result1.output_field}")

    result2 = module(input_field="Can you elaborate?")  # Has context
    print(f"Answer 2: {result2.output_field}")

    # Clear history
    module.clear_history()


def example_optimization():
    """Example: Optimize module with BootstrapFewShot."""
    import dspy
    from dspy.teleprompt import BootstrapFewShot

    # Load training data
    trainset = [
        dspy.Example(input_field="example 1", output_field="answer 1").with_inputs("input_field"),
        dspy.Example(input_field="example 2", output_field="answer 2").with_inputs("input_field"),
        # ... more examples
    ]

    # Define metric
    def accuracy(example, prediction, trace=None):
        return float(example.output_field.lower() in prediction.output_field.lower())

    # Optimize
    module = YourModule(param1="example")
    optimizer = BootstrapFewShot(metric=accuracy, max_bootstrapped_demos=3)
    optimized = optimizer.compile(module, trainset=trainset)

    # Save
    optimized.save("optimized_module.json")


if __name__ == "__main__":
    # Uncomment to run examples
    # example_basic_usage()
    # example_stateful_usage()
    # example_optimization()
    pass
