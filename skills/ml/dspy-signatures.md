---
name: dspy-signatures
description: Defining input/output signatures for DSPy modules and language model tasks
---

# DSPy Signatures

**Scope**: Signature syntax, field types, typed signatures, inline vs class-based
**Lines**: ~380
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Defining task structure for DSPy modules
- Specifying input and output fields for LM calls
- Creating typed signatures with field constraints
- Adding descriptions and hints to guide LM behavior
- Troubleshooting signature parsing errors
- Designing multi-field inputs or outputs

## Core Concepts

### What are Signatures?

**Definition**: Signatures specify the input/output interface for a language model task

**Purpose**:
- **Abstract prompts**: Define "what" not "how"
- **Type safety**: Specify expected field types
- **Documentation**: Describe field semantics
- **Composability**: Reuse signatures across modules

**Key insight**: Signatures are like function signatures, but for LM tasks

### Signature Syntax

**Three formats**:

1. **String format**: `"input1, input2 -> output"`
   - Quick and simple
   - No type annotations
   - Good for prototyping

2. **Expanded string**: `"question: str, context: str -> answer: str, confidence: float"`
   - Includes type hints
   - More explicit
   - Better for complex tasks

3. **Class-based**: Python class with `dspy.InputField` and `dspy.OutputField`
   - Maximum control
   - Field descriptions and constraints
   - Best for production

### Field Types and Constraints

**Supported types**:
- `str` - Text fields (most common)
- `int` - Integer values
- `float` - Floating point numbers
- `bool` - Boolean values
- `list[str]` - Lists of strings
- Custom types (validated with Pydantic)

**Field metadata**:
- `desc` - Description shown to LM
- `prefix` - Custom field label
- `format` - Output formatting hints

---

## Patterns

### Pattern 1: Simple String Signatures

```python
import dspy

# Basic question answering
signature = "question -> answer"

# Classification
signature = "text -> category"

# Summarization
signature = "document -> summary"

# Use with Predict module
qa = dspy.Predict("question -> answer")
result = qa(question="What is DSPy?")
print(result.answer)
```

**When to use**:
- Quick prototyping
- Simple single-input, single-output tasks
- Exploratory development

### Pattern 2: Multi-Field Signatures

```python
import dspy

# Multiple inputs
signature = "question, context -> answer"

# Multiple outputs
signature = "text -> category, confidence"

# Complex task
signature = "title, author, year -> summary, genre, rating"

# Example usage
classifier = dspy.Predict("text, hint -> label, confidence")
result = classifier(
    text="This is a great product!",
    hint="Classify sentiment as positive, negative, or neutral"
)
print(f"Label: {result.label}, Confidence: {result.confidence}")
```

**When to use**:
- Tasks requiring multiple inputs (context + question)
- Structured outputs (category + confidence)
- Rich information extraction

### Pattern 3: Typed Signatures

```python
import dspy

# Explicit type annotations
signature = "question: str, context: str -> answer: str, confidence: float"

# Using with module
rag = dspy.Predict("question: str, context: str -> answer: str")

# Types help DSPy format outputs correctly
result = rag(
    question="What is the capital of France?",
    context="France is a country in Europe. Paris is its capital."
)
```

**When to use**:
- Need numeric outputs (scores, ratings)
- Want type validation
- Building production systems
- Working with structured data

### Pattern 4: Class-Based Signatures

```python
import dspy

class QASignature(dspy.Signature):
    """Answer questions based on provided context."""

    # Input fields
    question = dspy.InputField(desc="User's question")
    context = dspy.InputField(desc="Relevant context for answering")

    # Output fields
    answer = dspy.OutputField(desc="Concise answer to the question")
    confidence = dspy.OutputField(
        desc="Confidence score between 0 and 1",
        prefix="Confidence:"
    )

# Use class-based signature
qa = dspy.ChainOfThought(QASignature)
result = qa(
    question="What is DSPy?",
    context="DSPy is a framework for programming language models."
)

print(result.answer)
print(result.confidence)
```

**Benefits**:
- Clear field descriptions (guide LM behavior)
- Docstring provides task context
- Reusable across modules
- Better IDE support

### Pattern 5: Signatures with Hints and Constraints

```python
import dspy

class SentimentAnalysis(dspy.Signature):
    """Analyze sentiment of text with confidence scoring."""

    text = dspy.InputField(desc="Text to analyze for sentiment")

    # Provide hint about expected values
    sentiment = dspy.OutputField(
        desc="Sentiment label: positive, negative, or neutral"
    )

    # Constrain output format
    score = dspy.OutputField(
        desc="Sentiment score from -1.0 (negative) to 1.0 (positive)",
        prefix="Score (between -1.0 and 1.0):"
    )

    explanation = dspy.OutputField(
        desc="Brief explanation of the sentiment classification"
    )

# Use signature
analyzer = dspy.Predict(SentimentAnalysis)
result = analyzer(text="This product exceeded my expectations!")

print(f"Sentiment: {result.sentiment}")
print(f"Score: {result.score}")
print(f"Explanation: {result.explanation}")
```

**When to use**:
- Need to guide LM output format
- Want explanations alongside predictions
- Complex structured outputs
- Quality-critical applications

### Pattern 6: Signatures for Multi-Step Reasoning

```python
import dspy

class ComplexQA(dspy.Signature):
    """Answer complex questions that require reasoning."""

    question = dspy.InputField(desc="Complex question requiring reasoning")
    context = dspy.InputField(desc="Background context", prefix="Context:")

    # Intermediate reasoning step
    reasoning = dspy.OutputField(
        desc="Step-by-step reasoning process",
        prefix="Let's think step by step:"
    )

    # Final answer
    answer = dspy.OutputField(desc="Final answer based on reasoning")

# Use with ChainOfThought module
cot = dspy.ChainOfThought(ComplexQA)
result = cot(
    question="If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?",
    context="Each machine works independently at a constant rate."
)

print("Reasoning:", result.reasoning)
print("Answer:", result.answer)
```

**When to use**:
- Complex reasoning tasks
- Need to show work/explanation
- Debugging LM behavior
- Educational applications

### Pattern 7: List-Based Signatures

```python
import dspy

class MultipleChoice(dspy.Signature):
    """Select best answer from multiple choices."""

    question = dspy.InputField(desc="Question to answer")
    choices = dspy.InputField(desc="List of possible answers")

    selected = dspy.OutputField(desc="Selected answer from choices")
    reasoning = dspy.OutputField(desc="Why this answer was chosen")

# Usage
mc = dspy.Predict(MultipleChoice)
result = mc(
    question="What is the capital of France?",
    choices=["London", "Paris", "Berlin", "Madrid"]
)

print(f"Selected: {result.selected}")
print(f"Reasoning: {result.reasoning}")
```

**When to use**:
- Multiple choice questions
- Selection from constrained set
- Ranking tasks

### Pattern 8: Custom Formatting with Prefix

```python
import dspy

class CodeReview(dspy.Signature):
    """Review code and provide structured feedback."""

    code = dspy.InputField(desc="Code to review")
    language = dspy.InputField(desc="Programming language")

    # Custom prefixes for clear output structure
    bugs = dspy.OutputField(
        desc="List of potential bugs",
        prefix="BUGS:"
    )

    improvements = dspy.OutputField(
        desc="Suggested improvements",
        prefix="IMPROVEMENTS:"
    )

    rating = dspy.OutputField(
        desc="Code quality rating (1-10)",
        prefix="RATING:"
    )

# Use signature
reviewer = dspy.ChainOfThought(CodeReview)
result = reviewer(
    code="def add(a,b): return a+b",
    language="Python"
)
```

**Benefits**:
- Clear output structure
- Easy parsing
- Better LM understanding of desired format

---

## Advanced Patterns

### Pattern 9: Conditional Signatures with Dynamic Fields

```python
import dspy
from typing import Optional

class ConditionalQA(dspy.Module):
    """QA with context-dependent output fields."""

    def __init__(self):
        super().__init__()
        # Base signature can be modified dynamically
        self.qa_with_context = dspy.ChainOfThought("question, context -> answer, sources: list[int]")
        self.qa_without_context = dspy.ChainOfThought("question -> answer")

    def forward(self, question, context: Optional[str] = None):
        if context:
            # Use signature with context and sources
            return self.qa_with_context(question=question, context=context)
        else:
            # Use simpler signature without context
            return self.qa_without_context(question=question)

# Usage
qa = ConditionalQA()

# With context
result1 = qa(question="What is DSPy?", context="DSPy is a framework...")
print(result1.answer, result1.sources)

# Without context
result2 = qa(question="What is 2+2?")
print(result2.answer)
```

**When to use**:
- Signatures need to adapt based on available data
- Optional context or metadata
- Varying output requirements

### Pattern 10: Pydantic-Validated Signatures

```python
import dspy
from pydantic import BaseModel, Field, validator
from typing import List

class SentimentOutput(BaseModel):
    """Structured output with validation."""
    sentiment: str = Field(..., regex="^(positive|negative|neutral)$")
    score: float = Field(..., ge=0.0, le=1.0)
    keywords: List[str] = Field(..., min_items=1, max_items=10)

    @validator('keywords')
    def validate_keywords(cls, v):
        """Ensure keywords are lowercase and unique."""
        return list(set(kw.lower() for kw in v))

class SentimentSignature(dspy.Signature):
    """Analyze sentiment with Pydantic validation."""
    text = dspy.InputField(desc="Text to analyze")

    # Output as Pydantic model
    result: SentimentOutput = dspy.OutputField(
        desc="Sentiment analysis result with validation"
    )

# Usage
analyzer = dspy.Predict(SentimentSignature)
result = analyzer(text="This product is amazing!")

# result.result is a validated Pydantic object
print(result.result.sentiment)  # "positive"
print(result.result.score)      # 0.95
print(result.result.keywords)   # ["amazing", "product"]
```

**Benefits**:
- Automatic validation of LM outputs
- Type safety with Pydantic
- Schema documentation
- API integration ready

### Pattern 11: Signature Inheritance and Reuse

```python
import dspy

# Base signature for classification
class BaseClassification(dspy.Signature):
    """Base classification signature."""
    text = dspy.InputField(desc="Text to classify")
    category = dspy.OutputField(desc="Classification category")
    confidence = dspy.OutputField(desc="Confidence score 0-1")

# Extend with additional outputs
class DetailedClassification(BaseClassification):
    """Classification with reasoning."""
    reasoning = dspy.OutputField(desc="Explanation for classification")
    keywords = dspy.OutputField(desc="Key terms that influenced decision")

# Further specialization
class SentimentClassification(DetailedClassification):
    """Sentiment-specific classification."""
    # Override docstring for specialized task
    """Classify sentiment of text with detailed reasoning."""

    # Add sentiment-specific field
    emotion = dspy.OutputField(desc="Primary emotion: joy, anger, sadness, fear, surprise")

# Use specialized signature
sentiment_classifier = dspy.ChainOfThought(SentimentClassification)
result = sentiment_classifier(text="I'm thrilled with this purchase!")

print(result.category)    # "positive"
print(result.confidence)  # 0.95
print(result.reasoning)   # "Strong positive language..."
print(result.emotion)     # "joy"
```

**When to use**:
- Building signature hierarchies
- Sharing common fields across tasks
- Progressive enhancement of outputs
- Domain-specific specializations

---

## Production Considerations

### Schema Evolution and Versioning

```python
import dspy
from typing import Optional

class QASignatureV1(dspy.Signature):
    """Version 1: Basic QA."""
    question = dspy.InputField()
    answer = dspy.OutputField()

class QASignatureV2(dspy.Signature):
    """Version 2: Add confidence."""
    question = dspy.InputField()
    answer = dspy.OutputField()
    confidence: float = dspy.OutputField(desc="0-1 confidence score")

class QASignatureV3(dspy.Signature):
    """Version 3: Add sources and reasoning."""
    question = dspy.InputField()
    context: Optional[str] = dspy.InputField(desc="Optional context")
    answer = dspy.OutputField()
    confidence: float = dspy.OutputField(desc="0-1 confidence score")
    sources: list[int] = dspy.OutputField(desc="Citation indices")
    reasoning = dspy.OutputField(desc="Step-by-step reasoning")

# Version-aware module
class VersionedQA(dspy.Module):
    def __init__(self, version="v3"):
        super().__init__()
        signatures = {
            "v1": QASignatureV1,
            "v2": QASignatureV2,
            "v3": QASignatureV3,
        }
        self.predictor = dspy.ChainOfThought(signatures[version])
        self.version = version

    def forward(self, question, context=None):
        if self.version == "v3" and context:
            return self.predictor(question=question, context=context)
        else:
            return self.predictor(question=question)

# Use specific version
qa_v2 = VersionedQA(version="v2")
qa_v3 = VersionedQA(version="v3")
```

**Benefits**:
- Gradual migration between signature versions
- A/B testing different signature designs
- Backward compatibility
- Rollback capability

### Type Safety and Runtime Validation

```python
import dspy
from typing import Literal, get_args

CategoryType = Literal["news", "sports", "technology", "entertainment"]

class StrictClassifier(dspy.Signature):
    """Classifier with strict type constraints."""
    text = dspy.InputField(desc="Text to classify")
    category: CategoryType = dspy.OutputField(
        desc=f"Category must be one of: {', '.join(get_args(CategoryType))}"
    )
    confidence: float = dspy.OutputField(desc="Confidence between 0.0 and 1.0")

class ValidatedClassifier(dspy.Module):
    def __init__(self):
        super().__init__()
        self.classifier = dspy.Predict(StrictClassifier)

    def forward(self, text):
        result = self.classifier(text=text)

        # Runtime validation
        valid_categories = get_args(CategoryType)
        if result.category not in valid_categories:
            raise ValueError(
                f"Invalid category '{result.category}'. "
                f"Must be one of: {valid_categories}"
            )

        # Validate confidence range
        try:
            conf = float(result.confidence)
            if not 0.0 <= conf <= 1.0:
                raise ValueError(f"Confidence {conf} out of range [0, 1]")
        except ValueError:
            conf = 0.5  # Default fallback

        return dspy.Prediction(
            category=result.category,
            confidence=conf
        )

# Use validated classifier
classifier = ValidatedClassifier()
result = classifier(text="Breaking: New technology announced")
```

**Production checklist**:
- Validate all numeric outputs are in expected ranges
- Ensure categorical outputs match allowed values
- Handle parsing errors gracefully
- Provide fallback values for critical fields

### Performance Optimization for Signatures

```python
import dspy

# Verbose signature (slower, more accurate)
class VerboseQA(dspy.Signature):
    """Answer questions with detailed reasoning and multiple checks."""

    question = dspy.InputField(
        desc="Question to answer. Consider all aspects and edge cases."
    )
    context = dspy.InputField(
        desc="Relevant context. Review carefully for all pertinent information."
    )

    # Multiple intermediate fields
    key_facts = dspy.OutputField(desc="Extract 3-5 key facts from context")
    reasoning = dspy.OutputField(desc="Step-by-step reasoning process")
    answer = dspy.OutputField(desc="Final answer based on reasoning")
    confidence = dspy.OutputField(desc="Confidence score with justification")
    sources = dspy.OutputField(desc="Specific context passages supporting answer")

# Concise signature (faster, good for simple cases)
class ConciseQA(dspy.Signature):
    """Answer questions concisely."""
    question = dspy.InputField()
    context = dspy.InputField()
    answer = dspy.OutputField()

# Adaptive module
class AdaptiveQA(dspy.Module):
    def __init__(self, complexity_threshold=0.5):
        super().__init__()
        self.verbose = dspy.ChainOfThought(VerboseQA)
        self.concise = dspy.Predict(ConciseQA)
        self.threshold = complexity_threshold

    def forward(self, question, context):
        # Estimate complexity
        is_complex = (
            len(question.split()) > 20 or
            len(context.split()) > 500 or
            "compare" in question.lower() or
            "analyze" in question.lower()
        )

        if is_complex:
            return self.verbose(question=question, context=context)
        else:
            return self.concise(question=question, context=context)
```

**Performance guidelines**:
- Fewer fields = faster inference
- Shorter descriptions = less prompt overhead
- Use `Predict` instead of `ChainOfThought` when reasoning not needed
- Cache compiled signatures for reuse

### Signature Documentation and Testing

```python
import dspy

class DocumentedSignature(dspy.Signature):
    """
    Well-documented signature for team collaboration.

    This signature implements entity extraction with validation.
    Expected accuracy: 85%+ on benchmark dataset.

    Example:
        Input: "Apple Inc. was founded by Steve Jobs in California."
        Output:
            entities: ["Apple Inc.", "Steve Jobs", "California"]
            types: ["Organization", "Person", "Location"]

    Validation:
        - Lists must have equal length
        - Types must be from allowed set
        - At least one entity required
    """

    text = dspy.InputField(
        desc="Text for entity extraction. Length: 10-5000 characters."
    )

    entities: list[str] = dspy.OutputField(
        desc="Extracted entities. Format: ['Entity 1', 'Entity 2', ...]"
    )

    entity_types: list[str] = dspy.OutputField(
        desc=(
            "Entity types matching entities. "
            "Allowed: Person, Organization, Location, Date, Other"
        )
    )

# Test signature behavior
def test_signature():
    """Test signature with example data."""
    extractor = dspy.Predict(DocumentedSignature)

    test_cases = [
        "Apple Inc. was founded by Steve Jobs.",
        "The meeting is on January 15th in New York.",
    ]

    for text in test_cases:
        result = extractor(text=text)
        print(f"Text: {text}")
        print(f"Entities: {result.entities}")
        print(f"Types: {result.entity_types}")
        print("---")

# Run tests
test_signature()
```

**Documentation best practices**:
- Include example inputs and outputs
- Specify expected accuracy/performance
- List validation rules
- Document allowed values for categorical fields
- Provide testing examples

---

## Quick Reference

### Signature Format Comparison

| Format | Syntax | Use Case |
|--------|--------|----------|
| Simple | `"input -> output"` | Prototyping, simple tasks |
| Multi-field | `"in1, in2 -> out1, out2"` | Multiple inputs/outputs |
| Typed | `"in: str -> out: float"` | Type validation |
| Class-based | `class Sig(dspy.Signature)` | Production, complex tasks |

### Common Field Types

```python
# Text
question = dspy.InputField(desc="Question text")

# Numeric
score: float = dspy.OutputField(desc="Score from 0 to 1")

# Boolean
is_valid: bool = dspy.OutputField(desc="True if valid")

# List
options: list[str] = dspy.InputField(desc="List of choices")
```

### Signature Best Practices

```
✅ DO: Use descriptive field names (question, not q)
✅ DO: Add field descriptions for clarity
✅ DO: Use class-based signatures for production
✅ DO: Include type hints for structured outputs
✅ DO: Provide examples in descriptions when needed

❌ DON'T: Use vague field names (input, output)
❌ DON'T: Omit descriptions for complex tasks
❌ DON'T: Mix too many unrelated outputs in one signature
❌ DON'T: Forget to specify expected output format
```

### Quick Signature Templates

```python
# Classification
"text -> category, confidence: float"

# QA
"question, context -> answer"

# Summarization
"document: str -> summary: str, key_points: list[str]"

# Sentiment
"text -> sentiment, score: float, explanation"

# Extraction
"text, entity_type -> entities: list[str]"
```

---

## Anti-Patterns

❌ **Vague signatures**: LM doesn't know what to do
```python
# Bad
signature = "input -> output"
```
✅ Use descriptive names:
```python
# Good
signature = "customer_review -> sentiment_label, confidence_score: float"
```

❌ **Missing field descriptions**: LM guesses intent
```python
# Bad
class BadSig(dspy.Signature):
    text = dspy.InputField()
    result = dspy.OutputField()
```
✅ Add clear descriptions:
```python
# Good
class GoodSig(dspy.Signature):
    """Classify text into categories."""
    text = dspy.InputField(desc="Text to classify")
    category = dspy.OutputField(desc="Category: news, sports, or tech")
```

❌ **Too many outputs**: Unfocused task
```python
# Bad - asking for too much at once
signature = "text -> sentiment, category, summary, keywords, language, toxicity"
```
✅ Split into focused signatures:
```python
# Good - focused tasks
classify_sig = "text -> category, confidence: float"
sentiment_sig = "text -> sentiment, score: float"
```

❌ **No type hints for structured data**: Parsing issues
```python
# Bad - LM might return text instead of number
signature = "text -> score"
```
✅ Specify types:
```python
# Good
signature = "text -> score: float, max_score: int"
```

---

## Related Skills

### Core DSPy Skills
- `dspy-setup.md` - Setting up DSPy and LM configuration
- `dspy-modules.md` - Using signatures with Predict, ChainOfThought, ReAct
- `dspy-assertions.md` - Adding constraints and validation to signatures
- `dspy-optimizers.md` - Optimizing signatures with demonstrations
- `dspy-evaluation.md` - Evaluating signature-based programs
- `dspy-rag.md` - Signatures for RAG pipelines

### Advanced DSPy Skills
- `dspy-structured-outputs.md` - Advanced structured output generation
- `dspy-prompt-engineering.md` - Signature design patterns
- `dspy-agents.md` - Signatures for agent workflows
- `dspy-testing.md` - Testing signature behavior
- `dspy-finetuning.md` - Fine-tuning with custom signatures

### Resources
- `resources/dspy/level1-quickstart.md` - Getting started guide
- `resources/dspy/level2-architecture.md` - Signature architecture patterns
- `resources/dspy/level3-production.md` - Production signature best practices

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
