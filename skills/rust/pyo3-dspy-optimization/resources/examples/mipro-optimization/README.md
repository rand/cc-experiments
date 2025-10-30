# MIPROv2 Optimization - Multi-Prompt Instruction Optimization

A comprehensive example demonstrating how to run DSPy's MIPROv2 teleprompter from Rust. This example shows advanced optimization techniques including multi-prompt instruction optimization, train/dev split handling, candidate generation tracking, and hyperparameter configuration.

## What You'll Learn

- How to configure and run the MIPROv2 teleprompter from Rust
- Multi-prompt instruction optimization strategies
- Train/dev split handling for proper evaluation
- Candidate generation and selection tracking
- Temperature scheduling for exploration vs exploitation
- Multiple model configuration (prompt model vs task model)
- Baseline vs optimized model comparison
- Saving and loading optimized artifacts

## MIPROv2 Methodology

MIPROv2 (Multi-prompt Instruction Proposal Optimizer v2) is an advanced teleprompter that optimizes both instructions and few-shot examples simultaneously. Unlike simpler optimizers, MIPROv2:

1. **Generates Multiple Instruction Candidates**: Uses a prompt model to propose diverse instruction variations
2. **Evaluates Each Candidate**: Tests candidates on a development set
3. **Selects Best Performers**: Chooses instructions that maximize the evaluation metric
4. **Iterates with Temperature**: Starts with high temperature (exploration) and gradually decreases (exploitation)
5. **Optimizes Few-Shot Examples**: Simultaneously selects optimal demonstration examples

### Key Hyperparameters

- **num_candidates**: Number of instruction variations to generate per iteration (default: 10-30)
- **init_temperature**: Starting temperature for candidate generation (default: 1.0-1.4)
- **prompt_model**: Model used to generate instruction candidates (can be smaller/faster)
- **task_model**: Model used to evaluate candidates on the actual task (typically more capable)

### When to Use MIPROv2

Use MIPROv2 when:
- You have a clear evaluation metric
- You have separate train and dev datasets (50-200 examples each)
- You want automated prompt engineering
- Task performance is critical and worth optimization time
- You need reproducible prompt optimization

## Prerequisites

1. **Rust toolchain** (1.70 or later)
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

2. **Python 3.8+** with DSPy installed
   ```bash
   pip install dspy-ai
   ```

3. **OpenAI API Key**
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

## Setup

1. Navigate to this directory:
   ```bash
   cd skills/rust/pyo3-dspy-optimization/resources/examples/mipro-optimization
   ```

2. Ensure your OpenAI API key is set:
   ```bash
   echo $OPENAI_API_KEY  # Should display your key
   ```

3. Review the sample datasets:
   ```bash
   cat data/trainset.json
   cat data/devset.json
   ```

## Running

Build and run the example:

```bash
cargo run
```

Or run with release optimizations (recommended for production):

```bash
cargo run --release
```

## Expected Output

```
=== MIPROv2 Optimization Example ===

Loading datasets...
  Train set: 50 examples
  Dev set: 20 examples

Configuring language models...
  Prompt model: gpt-3.5-turbo (for candidate generation)
  Task model: gpt-4 (for evaluation)

Creating baseline QA module...

Evaluating baseline performance...
  Baseline accuracy: 0.65

Configuring MIPROv2 optimizer...
  Candidates per iteration: 20
  Initial temperature: 1.2
  Train set size: 50
  Dev set size: 20

Running MIPROv2 optimization...
  Iteration 1/5: Generating 20 candidates...
  Iteration 1/5: Best accuracy: 0.72 (+0.07)
  Iteration 2/5: Generating 20 candidates...
  Iteration 2/5: Best accuracy: 0.78 (+0.06)
  Iteration 3/5: Generating 20 candidates...
  Iteration 3/5: Best accuracy: 0.81 (+0.03)
  Iteration 4/5: Generating 20 candidates...
  Iteration 4/5: Best accuracy: 0.82 (+0.01)
  Iteration 5/5: Generating 20 candidates...
  Iteration 5/5: Best accuracy: 0.83 (+0.01)

Optimization complete!
  Final accuracy: 0.83
  Improvement: +0.18 (+27.7%)
  Total candidates evaluated: 100
  Best candidate selected at iteration: 5

Saving optimized model...
  Saved to: optimized_model.json

Comparing instructions:

Baseline instruction:
  "Answer the question based on the given context."

Optimized instruction:
  "Carefully read the provided context and use only the information
   explicitly stated to answer the question. If the answer cannot be
   determined from the context, state that clearly."

Done!
```

## Code Walkthrough

### 1. Dataset Loading (`src/main.rs`)

```rust
let trainset = load_dataset(py, "data/trainset.json")?;
let devset = load_dataset(py, "data/devset.json")?;
```

Loads JSON datasets into DSPy Example objects. Each example contains:
- `question`: The input question
- `context`: Background information
- `answer`: The expected answer

### 2. Language Model Configuration

```rust
let prompt_lm = configure_lm(py, dspy, "gpt-3.5-turbo")?;
let task_lm = configure_lm(py, dspy, "gpt-4")?;
```

Configures two separate models:
- **Prompt model**: Fast, inexpensive model for generating candidate instructions
- **Task model**: More capable model for actual task evaluation

### 3. Baseline Creation

```rust
let baseline_module = create_qa_module(py, dspy)?;
let baseline_accuracy = evaluate_module(
    py,
    &baseline_module,
    &devset,
    &accuracy_metric
)?;
```

Creates and evaluates an unoptimized module to establish a performance baseline.

### 4. MIPROv2 Configuration (`src/lib.rs`)

```rust
let config = MIPROConfig {
    num_candidates: 20,
    init_temperature: 1.2,
    prompt_model: "gpt-3.5-turbo".to_string(),
    task_model: "gpt-4".to_string(),
};
```

Configures the optimization process with:
- **num_candidates**: How many instruction variations to try per iteration
- **init_temperature**: Controls randomness (higher = more exploration)
- **prompt_model**: Model for generating candidates
- **task_model**: Model for evaluating candidates

### 5. Running Optimization

```rust
let optimized_module = run_miprov2(
    py,
    &baseline_module,
    &trainset,
    &devset,
    &accuracy_metric,
    config,
)?;
```

Executes the MIPROv2 algorithm:
1. Generate `num_candidates` instruction variations
2. Evaluate each on the training set
3. Select top performers
4. Evaluate on dev set
5. Repeat for multiple iterations with decreasing temperature

### 6. Candidate Tracking

```rust
pub struct CandidateTracker {
    candidates: Vec<Candidate>,
    best_score: f64,
    iteration: usize,
}

impl CandidateTracker {
    pub fn track_candidate(&mut self, instruction: String, score: f64) {
        self.candidates.push(Candidate {
            instruction,
            score,
            iteration: self.iteration,
        });
    }
}
```

Tracks all generated candidates for analysis and debugging.

### 7. Temperature Scheduling

```rust
pub fn compute_temperature(iteration: usize, init_temp: f64) -> f64 {
    let decay_rate = 0.1;
    init_temp * (-decay_rate * iteration as f64).exp()
}
```

Gradually reduces temperature to shift from exploration to exploitation:
- **Early iterations**: High temperature → diverse candidates
- **Later iterations**: Low temperature → refinements of best candidates

### 8. Model Comparison

```rust
let improvement = optimized_accuracy - baseline_accuracy;
let improvement_pct = (improvement / baseline_accuracy) * 100.0;

println!("\nOptimization complete!");
println!("  Final accuracy: {:.2}", optimized_accuracy);
println!("  Improvement: +{:.2} (+{:.1}%)", improvement, improvement_pct);
```

Quantifies the improvement from optimization.

### 9. Saving Optimized Model

```rust
save_optimized_model(
    py,
    &optimized_module,
    "optimized_model.json",
)?;
```

Persists the optimized module for deployment.

## Dataset Format

The example uses JSON datasets with this structure:

```json
[
  {
    "question": "What is the capital of France?",
    "context": "France is a country in Western Europe. Its capital and largest city is Paris.",
    "answer": "Paris"
  },
  {
    "question": "Who wrote Romeo and Juliet?",
    "context": "Romeo and Juliet is a tragedy written by William Shakespeare early in his career.",
    "answer": "William Shakespeare"
  }
]
```

### Creating Your Own Datasets

1. **Train set** (50-200 examples): Used for instruction optimization
2. **Dev set** (20-100 examples): Used for evaluation and selection
3. **Test set** (optional): Used for final evaluation (not shown in this example)

Best practices:
- Keep dev set separate from train set (no overlap)
- Ensure examples are representative of production use cases
- Include diverse, challenging examples
- Validate data quality before optimization

## Hyperparameter Tuning

### `num_candidates`

- **Low (5-10)**: Faster, less thorough exploration
- **Medium (10-30)**: Good balance for most tasks
- **High (30-50)**: Thorough exploration, slower

### `init_temperature`

- **Low (0.5-0.8)**: Conservative, incremental improvements
- **Medium (0.9-1.2)**: Balanced exploration/exploitation
- **High (1.3-1.5)**: Aggressive exploration, more diversity

### Model Selection

**Prompt Model** (for candidate generation):
- Can be smaller/faster (e.g., `gpt-3.5-turbo`, `claude-instant`)
- Needs to understand instruction writing
- Cost-sensitive choice (generates many candidates)

**Task Model** (for evaluation):
- Should be capable for the actual task
- Higher quality = better optimization signal
- Can be same as prompt model for simpler tasks

## Performance Considerations

### API Cost

MIPROv2 makes many API calls:
- Candidate generation: `num_candidates * iterations * train_size`
- Evaluation: `num_candidates * dev_size`

Typical costs for this example:
- 20 candidates × 5 iterations × 50 train = 5,000 prompt model calls
- 20 candidates × 20 dev = 400 task model calls

### Runtime

Optimization can take 5-30 minutes depending on:
- Dataset sizes
- Number of candidates
- Model speeds
- API rate limits

### Memory

Rust manages memory efficiently:
- Python objects are reference-counted
- GIL released during long operations
- Candidate history stored in memory (minimal overhead)

## Troubleshooting

### "Optimization stalled at low accuracy"

**Possible causes**:
- Train/dev split mismatch
- Evaluation metric doesn't reflect task goals
- Too few candidates per iteration
- Temperature too low (not exploring enough)

**Solutions**:
- Increase `num_candidates`
- Increase `init_temperature`
- Check dataset quality and diversity
- Try a more capable task model

### "High variance between iterations"

**Possible causes**:
- Temperature too high
- Small dev set
- Noisy evaluation metric

**Solutions**:
- Decrease `init_temperature`
- Increase dev set size
- Use a more stable metric (e.g., exact match vs. contains)

### "API rate limit errors"

**Solutions**:
- Add retry logic with exponential backoff
- Reduce `num_candidates`
- Use a prompt model with higher rate limits
- Batch evaluations where possible

### "Out of memory"

**Solutions**:
- Process candidates in smaller batches
- Clear candidate history periodically
- Reduce train/dev set sizes
- Use streaming evaluation

## Advanced Usage

### Custom Metrics

```rust
pub fn create_custom_metric(py: Python) -> PyResult<Py<PyAny>> {
    let dspy = py.import("dspy")?;

    // Define custom metric function
    let metric_fn = py.eval(
        "lambda example, pred, trace: custom_logic(example, pred)",
        None,
        None,
    )?;

    Ok(metric_fn.into())
}
```

### Multi-Stage Optimization

```rust
// Stage 1: Optimize with fast model
let stage1 = run_miprov2(py, module, trainset, devset, metric, config1)?;

// Stage 2: Refine with better model
let config2 = MIPROConfig {
    task_model: "gpt-4-turbo".to_string(),
    ..config1
};
let stage2 = run_miprov2(py, &stage1, trainset, devset, metric, config2)?;
```

### Parallel Evaluation

```rust
// Evaluate candidates in parallel using tokio
let handles: Vec<_> = candidates
    .iter()
    .map(|candidate| {
        tokio::spawn(async move {
            evaluate_candidate(candidate).await
        })
    })
    .collect();

let results = futures::future::join_all(handles).await;
```

## Next Steps

After running this example, explore:

1. **BootstrapFewShot** - Simpler optimizer for few-shot examples only
2. **COPRO** - Coordinate multiple prompts in a pipeline
3. **Ensemble Methods** - Combine multiple optimized modules
4. **Production Deployment** - Load optimized models in production
5. **Custom Teleprompters** - Build domain-specific optimizers

## References

- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [MIPROv2 Paper](https://arxiv.org/abs/2406.11695)
- [PyO3 Guide](https://pyo3.rs/)
- [Prompt Optimization Best Practices](https://dspy-docs.vercel.app/docs/building-blocks/optimizers)

## License

This example is part of the pyo3-dspy-optimization skill module.
