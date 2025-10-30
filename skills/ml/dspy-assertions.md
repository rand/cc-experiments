---
name: dspy-assertions
description: Adding constraints and validation to DSPy programs with assertions and suggestions
---

# DSPy Assertions

**Scope**: dspy.Assert, dspy.Suggest, output validation, constraints, retry logic
**Lines**: ~380
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Validating DSPy module outputs meet specific criteria
- Enforcing constraints on generated content (length, format, values)
- Implementing automatic retry with feedback
- Reducing invalid or low-quality predictions
- Adding guardrails to LM behavior
- Debugging module failures with better error messages

## Core Concepts

### Assertions in DSPy

**Definition**: Runtime checks that validate module outputs

**Purpose**:
- **Quality control**: Ensure outputs meet requirements
- **Constraint enforcement**: Length limits, format requirements, value ranges
- **Self-correction**: Automatic retry with feedback
- **Debugging**: Clear error messages when validation fails

**Key insight**: Assertions make LM programs more reliable by catching and fixing errors

### Assertion Types

**dspy.Assert**: Hard constraint (must pass)
- Raises error if validation fails
- Stops execution
- Use for critical requirements

**dspy.Suggest**: Soft constraint (should pass)
- Logs warning if validation fails
- Continues execution
- Attempts retry with feedback
- Use for quality improvements

### How Assertions Work

**Workflow**:
1. Module produces output
2. Assertion validates output
3. If validation fails:
   - **Assert**: Raises error
   - **Suggest**: Provides feedback and retries
4. If validation passes: Continue

**Retry mechanism**:
- Failed suggestion triggers automatic retry
- Feedback message added to prompt
- LM gets chance to self-correct
- Configurable max retries

---

## Patterns

### Pattern 1: Basic Assertion

```python
import dspy

class ValidatedQA(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought("question -> answer")

    def forward(self, question):
        result = self.generate(question=question)

        # Assert answer is non-empty
        dspy.Assert(
            len(result.answer.strip()) > 0,
            "Answer cannot be empty"
        )

        # Assert answer is not too long
        dspy.Assert(
            len(result.answer.split()) <= 100,
            "Answer must be 100 words or less"
        )

        return result

# Use validated module
qa = ValidatedQA()

try:
    result = qa(question="What is DSPy?")
    print(result.answer)
except AssertionError as e:
    print(f"Validation failed: {e}")
```

**When to use**:
- Critical constraints that cannot be violated
- Hard format requirements
- Safety checks

### Pattern 2: Suggestion with Retry

```python
import dspy

class SuggestedQA(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought("question -> answer")

    def forward(self, question):
        result = self.generate(question=question)

        # Suggest (not require) concise answer
        dspy.Suggest(
            len(result.answer.split()) <= 50,
            "Please provide a more concise answer (50 words or less)"
        )

        # Suggest answer includes specific keyword (if applicable)
        if "framework" in question.lower():
            dspy.Suggest(
                "framework" in result.answer.lower(),
                "Answer should mention 'framework' since question asks about it"
            )

        return result

# Use with suggestions
qa = SuggestedQA()
result = qa(question="What is DSPy?")
print(result.answer)
# If suggestions fail, DSPy automatically retries with feedback
```

**How it works**:
1. First attempt produces answer
2. Suggestion validates answer
3. If validation fails, DSPy retries with feedback message
4. LM sees feedback and adjusts output
5. Process repeats until validation passes or max retries reached

### Pattern 3: Format Validation

```python
import dspy
import json

class JSONGenerator(dspy.Module):
    """Generate valid JSON output."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(
            "description -> json_output: str"
        )

    def forward(self, description):
        result = self.generate(description=description)

        # Assert output is valid JSON
        try:
            parsed = json.loads(result.json_output)
            is_valid_json = True
        except json.JSONDecodeError:
            is_valid_json = False

        dspy.Assert(
            is_valid_json,
            "Output must be valid JSON"
        )

        # Suggest specific structure
        dspy.Suggest(
            isinstance(parsed, dict),
            "JSON should be an object (not array or primitive)"
        )

        dspy.Suggest(
            "name" in parsed and "value" in parsed,
            "JSON should contain 'name' and 'value' fields"
        )

        return dspy.Prediction(
            json_output=result.json_output,
            parsed=parsed
        )

# Use JSON generator
gen = JSONGenerator()
result = gen(description="Create a person object with name John and age 30")
print(result.parsed)  # {'name': 'John', 'value': 30}
```

**When to use**:
- Generating structured outputs (JSON, XML, CSV)
- Parsing validation
- Schema compliance

### Pattern 4: Value Range Constraints

```python
import dspy

class ScoringModule(dspy.Module):
    """Generate scores with validation."""

    def __init__(self):
        super().__init__()
        self.score = dspy.ChainOfThought(
            "text -> score: float, explanation"
        )

    def forward(self, text):
        result = self.score(text=text)

        # Convert score to float
        try:
            score_value = float(result.score)
        except:
            score_value = 0.0

        # Assert score is in valid range
        dspy.Assert(
            0.0 <= score_value <= 1.0,
            "Score must be between 0.0 and 1.0"
        )

        # Suggest explanation is provided
        dspy.Suggest(
            len(result.explanation.split()) >= 5,
            "Provide a more detailed explanation (at least 5 words)"
        )

        return dspy.Prediction(
            score=score_value,
            explanation=result.explanation
        )

# Use scoring module
scorer = ScoringModule()
result = scorer(text="This is a great product!")
print(f"Score: {result.score}")
print(f"Explanation: {result.explanation}")
```

**When to use**:
- Numeric outputs with valid ranges
- Ratings, scores, percentages
- Confidence values

### Pattern 5: Content Validation

```python
import dspy

class SafeContentGenerator(dspy.Module):
    """Generate content with safety checks."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought("topic -> content")

    def forward(self, topic):
        result = self.generate(topic=topic)

        # List of banned words/topics
        banned_words = ["inappropriate", "offensive", "harmful"]

        # Assert no banned content
        contains_banned = any(
            word in result.content.lower()
            for word in banned_words
        )

        dspy.Assert(
            not contains_banned,
            "Content contains inappropriate language"
        )

        # Suggest minimum quality
        dspy.Suggest(
            len(result.content.split()) >= 20,
            "Content should be at least 20 words for good quality"
        )

        # Suggest proper punctuation
        dspy.Suggest(
            result.content.strip().endswith(('.', '!', '?')),
            "Content should end with proper punctuation"
        )

        return result

# Use safe generator
gen = SafeContentGenerator()
result = gen(topic="artificial intelligence")
print(result.content)
```

**When to use**:
- Content moderation
- Safety filters
- Quality guidelines

### Pattern 6: Multi-Field Validation

```python
import dspy

class EntityExtractor(dspy.Module):
    """Extract entities with validation."""

    def __init__(self):
        super().__init__()
        self.extract = dspy.ChainOfThought(
            "text -> entities: list[str], entity_types: list[str], confidence: float"
        )

    def forward(self, text):
        result = self.extract(text=text)

        # Parse list fields (may be comma-separated strings)
        if isinstance(result.entities, str):
            entities = [e.strip() for e in result.entities.split(",")]
        else:
            entities = result.entities

        if isinstance(result.entity_types, str):
            entity_types = [t.strip() for t in result.entity_types.split(",")]
        else:
            entity_types = result.entity_types

        # Assert lists have same length
        dspy.Assert(
            len(entities) == len(entity_types),
            "Number of entities must match number of entity types"
        )

        # Suggest at least one entity found
        dspy.Suggest(
            len(entities) > 0,
            "Try to find at least one entity in the text"
        )

        # Validate confidence
        try:
            conf = float(result.confidence)
        except:
            conf = 0.5

        dspy.Suggest(
            0.0 <= conf <= 1.0,
            "Confidence should be between 0 and 1"
        )

        return dspy.Prediction(
            entities=entities,
            entity_types=entity_types,
            confidence=conf
        )

# Use entity extractor
extractor = EntityExtractor()
result = extractor(text="Apple Inc. was founded by Steve Jobs in California.")
print(f"Entities: {result.entities}")
print(f"Types: {result.entity_types}")
```

**When to use**:
- Multi-field outputs with dependencies
- List/array outputs
- Structured extraction tasks

### Pattern 7: Custom Validation Functions

```python
import dspy

def is_valid_email(email: str) -> bool:
    """Simple email validation."""
    return "@" in email and "." in email.split("@")[1]

def is_valid_phone(phone: str) -> bool:
    """Simple phone validation."""
    digits = "".join(c for c in phone if c.isdigit())
    return len(digits) >= 10

class ContactExtractor(dspy.Module):
    """Extract contact information with validation."""

    def __init__(self):
        super().__init__()
        self.extract = dspy.ChainOfThought(
            "text -> email, phone, name"
        )

    def forward(self, text):
        result = self.extract(text=text)

        # Validate email format
        dspy.Suggest(
            is_valid_email(result.email),
            "Email should be in valid format (user@domain.com)"
        )

        # Validate phone format
        dspy.Suggest(
            is_valid_phone(result.phone),
            "Phone should contain at least 10 digits"
        )

        # Validate name is not empty
        dspy.Assert(
            len(result.name.strip()) > 0,
            "Name cannot be empty"
        )

        return result

# Use contact extractor
extractor = ContactExtractor()
result = extractor(text="Contact John Doe at john@example.com or (555) 123-4567")
print(f"Name: {result.name}")
print(f"Email: {result.email}")
print(f"Phone: {result.phone}")
```

**Benefits**:
- Reusable validation logic
- Domain-specific checks
- Clear separation of concerns

### Pattern 8: Assertion with Backoff

```python
import dspy

class RobustGenerator(dspy.Module):
    """Generator with configurable assertion retries."""

    def __init__(self, max_retries=3):
        super().__init__()
        self.max_retries = max_retries
        self.generate = dspy.ChainOfThought("prompt -> response")

    def forward(self, prompt):
        for attempt in range(self.max_retries):
            try:
                result = self.generate(prompt=prompt)

                # Validations
                dspy.Assert(
                    len(result.response.strip()) > 0,
                    "Response cannot be empty"
                )

                dspy.Suggest(
                    len(result.response.split()) >= 10,
                    "Response should be at least 10 words"
                )

                # If we get here, validation passed
                return result

            except AssertionError as e:
                if attempt == self.max_retries - 1:
                    # Last attempt failed, re-raise
                    raise
                # Otherwise, retry (DSPy handles this automatically for Suggest)
                print(f"Attempt {attempt + 1} failed: {e}")

        # Should not reach here
        raise AssertionError("All retries exhausted")

# Use robust generator
gen = RobustGenerator(max_retries=3)
result = gen(prompt="Explain quantum computing")
```

**When to use**:
- Production systems requiring reliability
- Handling transient validation failures
- Custom retry logic

---

## Quick Reference

### Assertion Syntax

```python
# Assert (hard requirement)
dspy.Assert(
    condition,
    "Error message if condition is False"
)

# Suggest (soft requirement with retry)
dspy.Suggest(
    condition,
    "Feedback message for retry if condition is False"
)
```

### Common Validations

```python
# Non-empty
dspy.Assert(len(output.strip()) > 0, "Output cannot be empty")

# Length constraint
dspy.Suggest(len(output.split()) <= 100, "Keep under 100 words")

# Numeric range
dspy.Assert(0.0 <= score <= 1.0, "Score must be 0-1")

# Format check
dspy.Assert(is_valid_json(output), "Must be valid JSON")

# Content safety
dspy.Assert(is_safe(output), "Contains inappropriate content")

# List length
dspy.Assert(len(list1) == len(list2), "Lists must match")
```

### Best Practices

```
✅ DO: Use Assert for critical constraints
✅ DO: Use Suggest for quality improvements
✅ DO: Provide clear, actionable error messages
✅ DO: Validate early (before expensive operations)
✅ DO: Use custom validation functions for reusability

❌ DON'T: Over-constrain (too many assertions = failures)
❌ DON'T: Use vague error messages ("invalid output")
❌ DON'T: Assert on things LM can't control
❌ DON'T: Forget to handle validation failures in production
```

---

## Anti-Patterns

❌ **Too many assertions**: Over-constrained, frequent failures
```python
# Bad - too restrictive
dspy.Assert(len(output) == 42, "Must be exactly 42 characters")
dspy.Assert("the" in output, "Must contain 'the'")
dspy.Assert(output.startswith("Answer:"), "Must start with 'Answer:'")
# ... 10 more assertions
```
✅ Use only essential constraints:
```python
# Good - essential constraints only
dspy.Assert(len(output.strip()) > 0, "Output required")
dspy.Suggest(len(output.split()) <= 100, "Prefer concise answers")
```

❌ **Vague error messages**: Don't help LM self-correct
```python
# Bad
dspy.Suggest(condition, "Invalid")
```
✅ Provide actionable feedback:
```python
# Good
dspy.Suggest(condition, "Answer should be 2-3 sentences with specific examples")
```

❌ **No error handling**: Crashes in production
```python
# Bad
result = module(input)  # May raise AssertionError
return result.output
```
✅ Handle validation failures:
```python
# Good
try:
    result = module(input)
    return result.output
except AssertionError as e:
    log_error(e)
    return fallback_response()
```

---

## Advanced Patterns

### Pattern 9: Conditional Assertions

```python
import dspy
from typing import Optional

class ConditionalValidator(dspy.Module):
    """Assertions that adapt based on context."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(
            "question, context -> answer, answer_type: str, confidence: float"
        )

    def forward(self, question: str, context: Optional[str] = None):
        # Generate answer
        if context:
            result = self.generate(question=question, context=context)
        else:
            result = self.generate(question=question, context="No context provided")

        # Conditional validation based on answer type
        answer_type = result.answer_type.lower()

        if answer_type == "factual":
            # Strict validation for facts
            dspy.Assert(
                len(result.answer.strip()) > 0,
                "Factual answers must not be empty"
            )

            dspy.Suggest(
                len(result.answer.split()) <= 50,
                "Factual answers should be concise (under 50 words)"
            )

        elif answer_type == "explanatory":
            # Detailed validation for explanations
            dspy.Suggest(
                len(result.answer.split()) >= 20,
                "Explanatory answers should be detailed (at least 20 words)"
            )

            dspy.Suggest(
                any(word in result.answer.lower() for word in ["because", "since", "therefore", "thus"]),
                "Explanatory answers should include causal reasoning"
            )

        elif answer_type == "unknown":
            # Validate uncertainty handling
            dspy.Suggest(
                any(phrase in result.answer.lower() for phrase in ["don't know", "uncertain", "unclear"]),
                "Unknown answers should express uncertainty clearly"
            )

        # Universal validation (applies to all types)
        try:
            confidence = float(result.confidence)
        except:
            confidence = 0.5

        dspy.Suggest(
            0.0 <= confidence <= 1.0,
            "Confidence must be between 0 and 1"
        )

        return result

# Use conditional validator
validator = ConditionalValidator()

# Factual question
result1 = validator(question="What is 2+2?")
print(f"Type: {result1.answer_type}, Answer: {result1.answer}")

# Explanatory question
result2 = validator(question="Why does DSPy use typed holes?")
print(f"Type: {result2.answer_type}, Answer: {result2.answer}")
```

**When to use**:
- Different validation rules for different output types
- Context-dependent quality requirements
- Adaptive quality control

### Pattern 10: Assertion Chaining

```python
import dspy
from typing import List, Callable

class AssertionChain:
    """Chain multiple assertions with early exit."""

    def __init__(self):
        self.assertions: List[tuple[Callable, str, bool]] = []

    def add(self, condition: Callable, message: str, required: bool = True):
        """Add assertion to chain."""
        self.assertions.append((condition, message, required))
        return self  # Enable chaining

    def validate(self, prediction) -> bool:
        """Run all assertions."""
        for condition_fn, message, required in self.assertions:
            try:
                passed = condition_fn(prediction)

                if not passed:
                    if required:
                        dspy.Assert(False, message)
                    else:
                        dspy.Suggest(False, message)

            except Exception as e:
                if required:
                    raise AssertionError(f"{message}: {e}")

        return True

class ValidatedModule(dspy.Module):
    """Module with assertion chain."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(
            "question -> answer, reasoning, confidence: float"
        )

    def forward(self, question: str):
        result = self.generate(question=question)

        # Build assertion chain
        chain = AssertionChain()

        # Required assertions
        chain.add(
            lambda p: len(p.answer.strip()) > 0,
            "Answer must not be empty",
            required=True
        ).add(
            lambda p: len(p.answer.split()) <= 200,
            "Answer must not exceed 200 words",
            required=True
        )

        # Optional suggestions
        chain.add(
            lambda p: len(p.reasoning.split()) >= 10,
            "Reasoning should be detailed (at least 10 words)",
            required=False
        ).add(
            lambda p: 0.0 <= float(p.confidence) <= 1.0 if hasattr(p, 'confidence') else True,
            "Confidence should be between 0 and 1",
            required=False
        )

        # Validate
        chain.validate(result)

        return result

# Use module with assertion chain
module = ValidatedModule()
result = module(question="What is DSPy?")
```

**Benefits**:
- Organize complex validation logic
- Reusable assertion chains
- Clear separation of required vs optional checks

### Pattern 11: Statistical Assertions

```python
import dspy
from typing import List
from collections import Counter

class StatisticalValidator(dspy.Module):
    """Validate based on statistical properties."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(
            "question -> answer, keywords: list[str]"
        )

    def forward(self, question: str):
        result = self.generate(question=question)

        # Parse keywords
        if isinstance(result.keywords, str):
            keywords = [k.strip() for k in result.keywords.split(',')]
        else:
            keywords = result.keywords

        # Statistical validations

        # 1. Vocabulary diversity (unique words / total words)
        words = result.answer.lower().split()
        unique_ratio = len(set(words)) / len(words) if words else 0

        dspy.Suggest(
            unique_ratio >= 0.4,
            f"Answer should have more vocabulary diversity (current: {unique_ratio:.1%}, target: 40%+)"
        )

        # 2. Sentence length distribution
        sentences = [s.strip() for s in result.answer.split('.') if s.strip()]
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)

            dspy.Suggest(
                5 <= avg_sentence_length <= 30,
                f"Sentences should be moderate length (current avg: {avg_sentence_length:.1f} words)"
            )

        # 3. Keyword coverage
        answer_lower = result.answer.lower()
        keyword_coverage = sum(1 for kw in keywords if kw.lower() in answer_lower) / len(keywords) if keywords else 0

        dspy.Suggest(
            keyword_coverage >= 0.5,
            f"Answer should cover more keywords (current: {keyword_coverage:.1%}, target: 50%+)"
        )

        # 4. Readability (simple heuristic: avg word length)
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0

        dspy.Suggest(
            avg_word_length <= 7,
            f"Answer should be readable (current avg word length: {avg_word_length:.1f}, target: ≤7)"
        )

        return result

# Use statistical validator
validator = StatisticalValidator()
result = validator(question="Explain DSPy signatures")
print(f"Answer: {result.answer}")
```

**When to use**:
- Quality metrics based on text statistics
- Readability requirements
- Content diversity checks

---

## Production Considerations

### Deployment Strategy

**Assertion levels in production**:
```python
import dspy
import os
from enum import Enum

class AssertionLevel(Enum):
    """Assertion strictness levels."""
    STRICT = "strict"      # All assertions enabled
    MODERATE = "moderate"  # Only critical assertions
    LENIENT = "lenient"    # Log warnings only, no failures

class ProductionModule(dspy.Module):
    """Module with environment-aware assertions."""

    def __init__(self, assertion_level: AssertionLevel = AssertionLevel.MODERATE):
        super().__init__()
        self.generate = dspy.ChainOfThought("question -> answer")
        self.assertion_level = assertion_level

    def _check_assertion(self, condition: bool, message: str, critical: bool = False):
        """Check assertion based on level."""
        if self.assertion_level == AssertionLevel.STRICT:
            # Strict: Fail on any violation
            dspy.Assert(condition, message)

        elif self.assertion_level == AssertionLevel.MODERATE:
            # Moderate: Fail only on critical violations
            if critical:
                dspy.Assert(condition, message)
            else:
                dspy.Suggest(condition, message)

        elif self.assertion_level == AssertionLevel.LENIENT:
            # Lenient: Just log warnings
            if not condition:
                import logging
                logging.warning(f"Assertion warning: {message}")

    def forward(self, question: str):
        result = self.generate(question=question)

        # Critical assertion (always enforced unless lenient)
        self._check_assertion(
            len(result.answer.strip()) > 0,
            "Answer cannot be empty",
            critical=True
        )

        # Non-critical suggestions (only in strict mode)
        self._check_assertion(
            len(result.answer.split()) <= 100,
            "Answer should be concise (under 100 words)",
            critical=False
        )

        return result

# Configure based on environment
env = os.getenv("ENVIRONMENT", "development")

if env == "production":
    level = AssertionLevel.MODERATE  # Balance quality and reliability
elif env == "staging":
    level = AssertionLevel.STRICT     # Catch issues before prod
else:
    level = AssertionLevel.LENIENT    # Fast iteration in dev

module = ProductionModule(assertion_level=level)
```

### Monitoring Assertion Failures

```python
import dspy
from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime
import json

@dataclass
class AssertionFailure:
    """Record of assertion failure."""
    timestamp: str
    message: str
    input_data: Dict
    output_data: Dict
    stack_trace: str = ""

class MonitoredModule(dspy.Module):
    """Module that tracks assertion failures."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought("question -> answer")
        self.failures: List[AssertionFailure] = []

    def _log_failure(self, message: str, question: str, result):
        """Log assertion failure."""
        failure = AssertionFailure(
            timestamp=datetime.now().isoformat(),
            message=message,
            input_data={'question': question},
            output_data={
                'answer': result.answer if hasattr(result, 'answer') else str(result)
            },
        )

        self.failures.append(failure)

        # Also log to file for persistence
        with open('assertion_failures.jsonl', 'a') as f:
            json.dump(failure.__dict__, f)
            f.write('\n')

    def forward(self, question: str):
        result = self.generate(question=question)

        # Validation with failure tracking
        try:
            dspy.Assert(
                len(result.answer.strip()) > 0,
                "Answer cannot be empty"
            )
        except AssertionError as e:
            self._log_failure(str(e), question, result)
            raise

        try:
            dspy.Suggest(
                len(result.answer.split()) <= 100,
                "Answer should be under 100 words"
            )
        except AssertionError as e:
            self._log_failure(str(e), question, result)
            # Suggestions don't re-raise by default

        return result

    def get_failure_stats(self) -> Dict:
        """Get failure statistics."""
        if not self.failures:
            return {'total_failures': 0}

        # Aggregate by failure message
        from collections import Counter
        failure_counts = Counter(f.message for f in self.failures)

        return {
            'total_failures': len(self.failures),
            'unique_failures': len(failure_counts),
            'most_common': failure_counts.most_common(5),
            'failure_rate': len(self.failures) / max(1, self._total_calls) if hasattr(self, '_total_calls') else 0,
        }

# Use monitored module
module = MonitoredModule()

# Simulate calls
for q in ["What is DSPy?", "Short q", "Another question here"]:
    try:
        result = module(question=q)
    except AssertionError:
        pass  # Continue despite failures

# Check failure stats
stats = module.get_failure_stats()
print(f"Assertion failures: {stats}")
```

### Graceful Degradation

```python
import dspy
from typing import Optional

class ResilientModule(dspy.Module):
    """Module that degrades gracefully on assertion failures."""

    def __init__(self):
        super().__init__()
        self.primary = dspy.ChainOfThought("question -> answer, confidence: float")
        self.fallback = dspy.Predict("question -> answer")

    def _validate_result(self, result) -> bool:
        """Validate result against all assertions."""
        try:
            # Critical validations
            dspy.Assert(
                len(result.answer.strip()) > 0,
                "Answer cannot be empty"
            )

            # Quality checks
            dspy.Suggest(
                len(result.answer.split()) >= 5,
                "Answer should be at least 5 words"
            )

            try:
                conf = float(result.confidence)
                dspy.Suggest(
                    conf >= 0.3,
                    "Confidence should be at least 0.3"
                )
            except:
                pass

            return True

        except AssertionError:
            return False

    def forward(self, question: str, max_retries: int = 2):
        """Try primary, fallback to simpler model on failure."""

        # Try primary with retries
        for attempt in range(max_retries):
            try:
                result = self.primary(question=question)

                if self._validate_result(result):
                    result.source = "primary"
                    result.attempts = attempt + 1
                    return result

            except Exception as e:
                if attempt == max_retries - 1:
                    # Last attempt failed, use fallback
                    break

        # Fallback: simpler model without strict assertions
        try:
            result = self.fallback(question=question)
            result.source = "fallback"
            result.warning = "Primary model failed validation, using fallback"
            return result

        except Exception as e:
            # Ultimate fallback: error response
            return dspy.Prediction(
                answer="I apologize, but I'm unable to generate a reliable answer.",
                source="error",
                error=str(e)
            )

# Use resilient module
module = ResilientModule()
result = module(question="What is DSPy?")

print(f"Answer: {result.answer}")
print(f"Source: {result.source}")
if hasattr(result, 'warning'):
    print(f"Warning: {result.warning}")
```

### Best Practices Checklist

```
Development:
✅ DO: Use Assert for critical requirements
✅ DO: Use Suggest for quality improvements
✅ DO: Provide clear, actionable error messages
✅ DO: Test assertion logic thoroughly
✅ DO: Document why each assertion exists

Production:
✅ DO: Configure assertion levels by environment
✅ DO: Monitor assertion failure rates
✅ DO: Log failures for analysis
✅ DO: Implement graceful degradation
✅ DO: Set reasonable retry limits
✅ DO: Have fallback strategies

Quality:
✅ DO: Balance strictness and reliability
✅ DO: Use conditional assertions when appropriate
✅ DO: Track statistical properties
✅ DO: Validate incrementally (fail fast)
✅ DO: Test edge cases extensively

❌ DON'T: Over-constrain with too many assertions
❌ DON'T: Use vague error messages
❌ DON'T: Assert on things LM can't control
❌ DON'T: Ignore assertion failures in logs
❌ DON'T: Skip graceful degradation
❌ DON'T: Use same strictness in all environments
```

---

## Related Skills

### Core DSPy Skills
- `dspy-modules.md` - Adding assertions to modules
- `dspy-evaluation.md` - Validation vs evaluation
- `dspy-optimizers.md` - Optimizing with constraints
- `dspy-signatures.md` - Signature validation
- `dspy-setup.md` - Configuration for assertion handling

### Advanced DSPy Skills
- `dspy-agents.md` - Assertions in agent systems
- `dspy-multi-agent.md` - Multi-agent validation
- `dspy-production.md` - Production assertion strategies
- `dspy-testing.md` - Testing assertion logic
- `dspy-debugging.md` - Debugging assertion failures
- `dspy-advanced-patterns.md` - Advanced validation patterns

### Infrastructure Skills
- `api-error-handling.md` - Error handling patterns
- `observability-logging.md` - Logging and monitoring

### Resources
- `resources/dspy/level2-validation.md` - Validation deep dive
- `resources/dspy/level3-production.md` - Production validation guide
- `resources/dspy/assertion-cookbook.md` - Assertion recipes

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
