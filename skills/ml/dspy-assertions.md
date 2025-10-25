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

## Related Skills

- `dspy-modules.md` - Adding assertions to modules
- `dspy-evaluation.md` - Validation vs evaluation
- `dspy-optimizers.md` - Optimizing with constraints
- `api/api-error-handling.md` - Error handling patterns

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
