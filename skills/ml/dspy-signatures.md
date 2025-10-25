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

- `dspy-setup.md` - Setting up DSPy and LM configuration
- `dspy-modules.md` - Using signatures with Predict, ChainOfThought, ReAct
- `dspy-assertions.md` - Adding constraints and validation to signatures
- `dspy-optimizers.md` - Optimizing signatures with demonstrations
- `dspy-evaluation.md` - Evaluating signature-based programs

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
