---
name: dspy-modules
description: Building composable prediction modules with Predict, ChainOfThought, ReAct, and custom modules
---

# DSPy Modules

**Scope**: Predict, ChainOfThought, ReAct, ProgramOfThought, custom modules, composition
**Lines**: ~450
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Building prediction pipelines with DSPy
- Choosing between Predict, ChainOfThought, and ReAct modules
- Creating custom DSPy modules
- Composing multiple modules into complex workflows
- Implementing multi-step reasoning systems
- Optimizing module selection for specific tasks

## Core Concepts

### What are Modules?

**Definition**: Modules are composable building blocks that replace hand-written prompts

**Purpose**:
- **Abstraction**: Encapsulate prompting strategies
- **Reusability**: Use same module across different tasks
- **Optimization**: Modules can be automatically tuned
- **Composition**: Chain modules for complex workflows

**Key insight**: Modules separate strategy (how to prompt) from task (what to ask)

### Built-in Module Types

**Predict**: Basic prediction
- Simplest module
- Direct signature → output mapping
- No intermediate reasoning
- Fast, efficient

**ChainOfThought**: Multi-step reasoning
- Adds reasoning step before answer
- Better for complex tasks
- Shows work/explanation
- Slightly slower but more accurate

**ReAct**: Reasoning + Acting
- Iterative thought-action-observation loops
- Can call tools/retrieve information
- Good for multi-step tasks requiring external data
- Most complex, most powerful

**ProgramOfThought**: Code generation + execution
- Generates Python code to solve problems
- Executes code for precise computations
- Excellent for math, data analysis
- Requires code execution environment

### Module Composition

**Pattern**: Small modules → Complex systems
- Each module has focused responsibility
- Modules pass data through signatures
- Compose modules in `forward()` method
- Create reusable module libraries

---

## Patterns

### Pattern 1: Basic Predict Module

```python
import dspy

# Configure LM
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

# Simple prediction
predictor = dspy.Predict("question -> answer")

# Use module
result = predictor(question="What is the capital of France?")
print(result.answer)  # "Paris"

# With typed signature
classifier = dspy.Predict("text -> category, confidence: float")
result = classifier(text="This movie was amazing!")
print(f"{result.category} ({result.confidence})")
```

**When to use**:
- Simple classification tasks
- Direct question answering
- Fast prototyping
- Tasks that don't need reasoning

### Pattern 2: ChainOfThought Module

```python
import dspy

class QASignature(dspy.Signature):
    """Answer questions with reasoning."""
    question = dspy.InputField(desc="Question to answer")
    answer = dspy.OutputField(desc="Answer to the question")

# Add chain-of-thought reasoning
cot = dspy.ChainOfThought(QASignature)

# Module automatically adds reasoning step
result = cot(question="If it takes 5 machines 5 minutes to make 5 widgets, how long for 100 machines to make 100 widgets?")

print("Reasoning:", result.reasoning)  # Shows step-by-step thinking
print("Answer:", result.answer)        # "5 minutes"
```

**When to use**:
- Complex reasoning tasks
- Math problems
- Multi-step questions
- When you need explanations

**How it works**:
- DSPy adds `reasoning` field to signature
- LM generates reasoning before answer
- More accurate for complex tasks

### Pattern 3: ReAct Module (with Tools)

```python
import dspy

class SearchQA(dspy.Signature):
    """Answer questions using search results."""
    question = dspy.InputField()
    answer = dspy.OutputField()

# Define tools that ReAct can use
def search(query: str) -> str:
    """Search for information."""
    # Implement actual search (e.g., Google, Wikipedia)
    return f"Search results for: {query}"

def calculate(expression: str) -> float:
    """Evaluate mathematical expressions."""
    return eval(expression)  # Use safely in production!

# Create ReAct module with tools
react = dspy.ReAct(
    SearchQA,
    tools=[search, calculate],
    max_iters=5,  # Maximum thought-action cycles
)

# ReAct will:
# 1. Think about the question
# 2. Decide which tool to use
# 3. Execute the tool
# 4. Observe results
# 5. Repeat until answer found

result = react(question="What is the population of the capital of France?")
print(result.answer)
```

**When to use**:
- Questions requiring external information
- Multi-step tasks with tool use
- Information retrieval + reasoning
- Agent-like behavior

**How it works**:
- Iterative Thought → Action → Observation loop
- Selects and executes tools
- Stops when answer is confident

### Pattern 4: ProgramOfThought Module

```python
import dspy

class MathProblem(dspy.Signature):
    """Solve math problems by generating Python code."""
    problem = dspy.InputField(desc="Math problem to solve")
    solution = dspy.OutputField(desc="Numerical solution")

# ProgramOfThought generates and executes code
pot = dspy.ProgramOfThought(MathProblem)

result = pot(problem="What is 15% of 240 plus 30% of 150?")

print("Code:", result.code)      # Generated Python code
print("Solution:", result.solution)  # Executed result
```

**When to use**:
- Mathematical computations
- Data analysis tasks
- Precise numerical answers
- Complex calculations

**Benefits**:
- More accurate than text-based reasoning for math
- Shows executable code
- Verifiable results

### Pattern 5: Custom Module

```python
import dspy

class RAGModule(dspy.Module):
    """Custom Retrieval-Augmented Generation module."""

    def __init__(self, num_passages=3):
        super().__init__()
        self.num_passages = num_passages

        # Sub-modules
        self.retrieve = dspy.Retrieve(k=num_passages)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        # Step 1: Retrieve relevant passages
        passages = self.retrieve(question).passages

        # Step 2: Format context
        context = "\n\n".join(passages)

        # Step 3: Generate answer with context
        result = self.generate(context=context, question=question)

        return result

# Use custom module
rag = RAGModule(num_passages=5)
result = rag(question="What is DSPy?")
print(result.answer)
```

**When to use**:
- Custom workflows not covered by built-in modules
- Complex multi-step pipelines
- Reusable domain-specific logic
- Production systems

**Structure**:
- Inherit from `dspy.Module`
- Define sub-modules in `__init__()`
- Implement `forward()` method
- Return results (or dspy.Prediction)

### Pattern 6: Module Composition

```python
import dspy

class MultiStepQA(dspy.Module):
    """Answer questions using multi-step reasoning."""

    def __init__(self):
        super().__init__()

        # Step 1: Break down question
        self.decompose = dspy.Predict("question -> sub_questions: list[str]")

        # Step 2: Answer sub-questions
        self.answer_sub = dspy.ChainOfThought("question -> answer")

        # Step 3: Synthesize final answer
        self.synthesize = dspy.ChainOfThought("question, sub_answers -> final_answer")

    def forward(self, question):
        # Decompose into sub-questions
        decomp = self.decompose(question=question)

        # Answer each sub-question
        sub_answers = []
        for sub_q in decomp.sub_questions:
            ans = self.answer_sub(question=sub_q)
            sub_answers.append(f"Q: {sub_q}\nA: {ans.answer}")

        # Synthesize final answer
        result = self.synthesize(
            question=question,
            sub_answers="\n\n".join(sub_answers)
        )

        return dspy.Prediction(
            sub_questions=decomp.sub_questions,
            sub_answers=sub_answers,
            answer=result.final_answer
        )

# Use composed module
qa = MultiStepQA()
result = qa(question="Compare and contrast Python and JavaScript")

print("Sub-questions:", result.sub_questions)
print("Final answer:", result.answer)
```

**Benefits**:
- Break complex tasks into manageable steps
- Each sub-module optimizable independently
- Clear separation of concerns
- Easier debugging

### Pattern 7: Module with Retry Logic

```python
import dspy

class RobustPredictor(dspy.Module):
    """Predictor with automatic retry on failure."""

    def __init__(self, signature, max_retries=3):
        super().__init__()
        self.predictor = dspy.ChainOfThought(signature)
        self.max_retries = max_retries

    def forward(self, **kwargs):
        last_error = None

        for attempt in range(self.max_retries):
            try:
                result = self.predictor(**kwargs)

                # Validate result (example: check if answer is non-empty)
                if hasattr(result, 'answer') and result.answer.strip():
                    return result

            except Exception as e:
                last_error = e
                print(f"Attempt {attempt + 1} failed: {e}")

        # All retries failed
        raise Exception(f"All {self.max_retries} attempts failed. Last error: {last_error}")

# Use robust predictor
predictor = RobustPredictor("question -> answer")
result = predictor(question="What is DSPy?")
```

**When to use**:
- Production systems requiring reliability
- Handling transient API failures
- Quality-critical applications

### Pattern 8: Parallel Module Execution

```python
import dspy
from concurrent.futures import ThreadPoolExecutor

class EnsemblePredictor(dspy.Module):
    """Run multiple predictors in parallel and combine results."""

    def __init__(self, signature, num_predictors=3):
        super().__init__()
        # Create multiple predictor instances
        self.predictors = [
            dspy.ChainOfThought(signature)
            for _ in range(num_predictors)
        ]
        self.vote = dspy.Predict("answers: list[str] -> best_answer: str")

    def forward(self, **kwargs):
        # Execute predictors in parallel
        with ThreadPoolExecutor(max_workers=len(self.predictors)) as executor:
            futures = [
                executor.submit(pred, **kwargs)
                for pred in self.predictors
            ]
            results = [f.result() for f in futures]

        # Extract answers
        answers = [r.answer for r in results]

        # Vote on best answer
        best = self.vote(answers=answers)

        return dspy.Prediction(
            all_answers=answers,
            answer=best.best_answer
        )

# Use ensemble
ensemble = EnsemblePredictor("question -> answer", num_predictors=5)
result = ensemble(question="What is the meaning of life?")
print("All answers:", result.all_answers)
print("Best answer:", result.answer)
```

**When to use**:
- Improve prediction quality through voting
- Reduce variance in outputs
- Critical decisions requiring consensus

---

## Quick Reference

### Module Comparison

| Module | Reasoning | Speed | Accuracy | Use Case |
|--------|-----------|-------|----------|----------|
| Predict | None | Fastest | Good | Simple tasks |
| ChainOfThought | Sequential | Fast | Better | Complex reasoning |
| ReAct | Iterative + Tools | Slow | Best (with tools) | Multi-step + retrieval |
| ProgramOfThought | Code gen | Medium | Excellent (math) | Computations |

### Creating Custom Modules

```python
class MyModule(dspy.Module):
    def __init__(self):
        super().__init__()
        # Define sub-modules

    def forward(self, **kwargs):
        # Implement logic
        return dspy.Prediction(...)
```

### Module Best Practices

```
✅ DO: Use Predict for simple tasks
✅ DO: Use ChainOfThought for complex reasoning
✅ DO: Use ReAct when you need external information
✅ DO: Compose small modules into larger systems
✅ DO: Return dspy.Prediction from custom modules

❌ DON'T: Use ChainOfThought for all tasks (overkill for simple ones)
❌ DON'T: Use ReAct without proper tools
❌ DON'T: Create monolithic custom modules
❌ DON'T: Forget to call super().__init__() in custom modules
```

### Quick Module Templates

```python
# Simple predictor
pred = dspy.Predict("input -> output")

# Reasoning predictor
cot = dspy.ChainOfThought("question -> answer")

# With tools
react = dspy.ReAct(signature, tools=[tool1, tool2])

# Custom module
class Custom(dspy.Module):
    def __init__(self):
        super().__init__()
        self.pred = dspy.Predict(sig)

    def forward(self, x):
        return self.pred(input=x)
```

---

## Anti-Patterns

❌ **Using ChainOfThought for everything**: Slower and more expensive
```python
# Bad - overkill for simple classification
classifier = dspy.ChainOfThought("text -> category")
```
✅ Use Predict for simple tasks:
```python
# Good
classifier = dspy.Predict("text -> category")
```

❌ **Not composing modules**: Monolithic, hard to optimize
```python
# Bad - everything in one module
class Monolith(dspy.Module):
    def forward(self, x):
        # 100 lines of complex logic
        pass
```
✅ Compose smaller modules:
```python
# Good
class Pipeline(dspy.Module):
    def __init__(self):
        super().__init__()
        self.step1 = Module1()
        self.step2 = Module2()
        self.step3 = Module3()
```

❌ **Ignoring module return format**: Breaks composition
```python
# Bad
def forward(self, x):
    result = self.pred(x)
    return result.answer  # Returns string, not Prediction
```
✅ Return Prediction objects:
```python
# Good
def forward(self, x):
    result = self.pred(x)
    return dspy.Prediction(answer=result.answer, confidence=0.9)
```

---

## Related Skills

- `dspy-signatures.md` - Defining signatures for modules
- `dspy-optimizers.md` - Optimizing module parameters
- `dspy-rag.md` - Building RAG pipelines with modules
- `dspy-assertions.md` - Adding validation to modules
- `dspy-evaluation.md` - Evaluating module performance

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
