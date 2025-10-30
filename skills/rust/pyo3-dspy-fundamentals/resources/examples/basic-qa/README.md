# Basic Question Answering with ChainOfThought

This example demonstrates how to use DSPy's ChainOfThought module from Rust via PyO3 to perform question answering with explicit reasoning steps.

## Overview

ChainOfThought is a DSPy module that prompts the language model to show its reasoning process before producing a final answer. This leads to more accurate and explainable predictions compared to direct prediction.

## Features

- **ChainOfThought reasoning**: Explicit intermediate reasoning steps
- **Structured input/output**: Type-safe Rust structs with serde serialization
- **Multiple queries**: Demonstrates batch processing
- **Error handling**: Comprehensive error handling with anyhow
- **GIL management**: Proper Python GIL acquisition/release

## Architecture

```
Input (question + context)
    ↓
ChainOfThought Module
    ↓
LM generates reasoning steps
    ↓
LM generates final answer
    ↓
Structured Output (answer + reasoning)
```

## Key Differences: ChainOfThought vs Predict

### Predict (Direct)
```python
# Input -> Output directly
signature = "question, context -> answer"
predictor = dspy.Predict(signature)
```

### ChainOfThought (Reasoning)
```python
# Input -> Reasoning -> Output
signature = "question, context -> answer, reasoning"
predictor = dspy.ChainOfThought(signature)
```

**Benefits of ChainOfThought**:
1. More accurate answers through step-by-step reasoning
2. Explainable results (see the "why")
3. Better handling of complex multi-hop questions
4. Helps debug when answers are incorrect

## Dependencies

```toml
pyo3 = { version = "0.22", features = ["auto-initialize"] }
anyhow = "1.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```

## Building and Running

```bash
# Build the project
cargo build --release

# Run the example
cargo run --release

# With verbose output
RUST_LOG=debug cargo run --release
```

## Example Output

```
Question Answering with DSPy ChainOfThought
==========================================

Query #1:
  Question: What is the capital of France?
  Context: France is a country in Western Europe. Paris is its capital and largest city.

  Answer: Paris
  Reasoning: The context explicitly states that Paris is the capital of France...

Query #2:
  Question: What is photosynthesis?
  Context: Photosynthesis is the process by which plants use sunlight, water, and CO2 to produce oxygen and glucose.

  Answer: A process where plants convert light energy into chemical energy
  Reasoning: The context describes photosynthesis as using sunlight, water, and CO2...
```

## Code Structure

### Input/Output Types

```rust
#[derive(Serialize)]
struct QAInput {
    question: String,
    context: String,
}

#[derive(Deserialize)]
struct QAOutput {
    answer: String,
    reasoning: String,
}
```

### Main Processing Flow

1. **Initialize DSPy**: Configure LM (defaults to GPT-3.5-turbo)
2. **Create ChainOfThought**: Define signature and create module
3. **Process queries**: For each question:
   - Serialize input to Python dict
   - Call ChainOfThought module
   - Extract answer and reasoning
   - Display results

### Error Handling

The example demonstrates proper error handling for:
- Python module import failures
- DSPy configuration errors
- Prediction failures
- Type conversion errors
- JSON serialization/deserialization

## Extending the Example

### Custom Signatures

```rust
// Multi-hop reasoning
let signature = "question, context1, context2 -> answer, reasoning, sources";

// Classification with explanation
let signature = "text -> category, confidence, explanation";

// Summarization with key points
let signature = "document -> summary, key_points";
```

### Custom LM Configuration

```python
import dspy
from dspy.teleprompt import BootstrapFewShot

# Use different model
lm = dspy.OpenAI(model="gpt-4", max_tokens=500)
dspy.settings.configure(lm=lm)

# Add few-shot examples
optimizer = BootstrapFewShot(metric=validate_answer)
optimized_cot = optimizer.compile(cot_module, trainset=examples)
```

### Adding Validation

```rust
fn validate_answer(output: &QAOutput) -> Result<bool> {
    // Check answer length
    if output.answer.len() < 5 {
        return Ok(false);
    }

    // Verify reasoning exists
    if output.reasoning.is_empty() {
        return Ok(false);
    }

    // Custom validation logic
    Ok(true)
}
```

## Real-World Applications

1. **Customer Support**: Answer questions using documentation context
2. **Research Assistant**: Answer scientific questions with paper excerpts
3. **Legal Analysis**: Extract answers from legal documents with citations
4. **Medical Q&A**: Answer health questions with medical literature context
5. **Education**: Tutoring systems that explain reasoning steps

## Performance Notes

- **Latency**: ChainOfThought adds ~20-30% overhead vs Predict due to reasoning generation
- **Accuracy**: Typically 10-25% improvement on complex questions
- **Cost**: Roughly 1.5-2x token usage (reasoning + answer)
- **Trade-off**: Use ChainOfThought for quality, Predict for speed

## Troubleshooting

### "No module named 'dspy'"
```bash
pip install dspy-ai
```

### "OpenAI API key not found"
```bash
export OPENAI_API_KEY="sk-..."
```

### Timeout errors
```python
lm = dspy.OpenAI(model="gpt-3.5-turbo", timeout=60)
```

## Related Examples

- `signature-basics/`: Learn DSPy signature syntax
- `typed-predictions/`: Advanced type handling
- `optimization/`: Fine-tune ChainOfThought with examples

## References

- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [ChainOfThought Paper](https://arxiv.org/abs/2201.11903)
- [PyO3 Guide](https://pyo3.rs/)
