# Evaluation Framework

A comprehensive evaluation harness for DSPy models supporting multiple metrics, statistical analysis, and model comparison.

## Features

- **Multiple Metric Types**: Accuracy, Exact Match, F1 Score, BLEU, ROUGE
- **Custom Metrics**: Trait-based system for defining custom evaluation metrics
- **Test Set Management**: Load test sets from JSON or CSV formats
- **Statistical Analysis**: Mean, std dev, min, max, percentiles
- **Model Comparison**: Compare multiple models with statistical significance testing
- **Batch Evaluation**: Efficient batch processing of test examples

## Architecture

### Core Components

1. **EvaluationHarness**: Main orchestrator for running evaluations
2. **Metric Trait**: Interface for implementing custom metrics
3. **TestSet**: Management and loading of test examples
4. **EvaluationResult**: Detailed statistics and results
5. **ComparisonReport**: Multi-model comparison with significance testing

### Built-in Metrics

- **Accuracy**: Proportion of correct predictions
- **ExactMatch**: Binary exact string matching
- **F1Score**: Harmonic mean of precision and recall
- **BLEU**: BiLingual Evaluation Understudy (n-gram overlap)
- **ROUGE**: Recall-Oriented Understudy for Gisting Evaluation

## Usage

### Basic Evaluation

```rust
use evaluation_framework::{EvaluationHarness, TestSet, Accuracy};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Load test set
    let test_set = TestSet::from_json("data/testset.json")?;

    // Create harness with accuracy metric
    let mut harness = EvaluationHarness::new(Box::new(Accuracy));

    // Evaluate model
    let result = harness.evaluate(&test_set, |example| {
        // Your model prediction logic
        predict(example)
    }).await?;

    // Print results
    println!("Accuracy: {:.2}%", result.mean * 100.0);
    println!("Std Dev: {:.4}", result.std_dev);

    Ok(())
}
```

### Multi-Metric Evaluation

```rust
use evaluation_framework::{EvaluationHarness, F1Score, BLEU, ROUGE};

let metrics = vec![
    Box::new(F1Score) as Box<dyn Metric>,
    Box::new(BLEU::new(4)),
    Box::new(ROUGE::new("rouge-l")),
];

for metric in metrics {
    let mut harness = EvaluationHarness::new(metric);
    let result = harness.evaluate(&test_set, predictor).await?;
    println!("{}: {:.4}", result.metric_name, result.mean);
}
```

### Model Comparison

```rust
use evaluation_framework::{ComparisonReport, EvaluationResult};

let baseline = evaluate_model("baseline", &test_set).await?;
let optimized = evaluate_model("optimized", &test_set).await?;

let comparison = ComparisonReport::compare(
    vec![baseline, optimized],
    0.05, // p-value threshold
)?;

comparison.print_summary();
```

### Custom Metrics

```rust
use evaluation_framework::Metric;

struct CustomMetric;

impl Metric for CustomMetric {
    fn name(&self) -> &str {
        "custom_metric"
    }

    fn compute(&self, predicted: &str, expected: &str) -> f64 {
        // Your metric logic
        if predicted.len() == expected.len() {
            1.0
        } else {
            0.0
        }
    }
}
```

## Test Set Format

### JSON Format

```json
[
    {
        "input": "What is the capital of France?",
        "expected_output": "Paris",
        "metadata": {
            "category": "geography",
            "difficulty": "easy"
        }
    },
    {
        "input": "Explain quantum entanglement",
        "expected_output": "Quantum entanglement is...",
        "metadata": {
            "category": "physics",
            "difficulty": "hard"
        }
    }
]
```

### CSV Format

```csv
input,expected_output,category,difficulty
"What is the capital of France?","Paris","geography","easy"
"Explain quantum entanglement","Quantum entanglement is...","physics","hard"
```

## Evaluation Reports

### Single Model Report

```
Evaluation Report: baseline_model
================================
Metric: accuracy
Total Examples: 100
Mean: 0.8500
Std Dev: 0.0234
Min: 0.7800
Max: 0.9200
Percentiles:
  25th: 0.8100
  50th: 0.8500
  75th: 0.8900
  95th: 0.9100
```

### Comparison Report

```
Model Comparison Report
======================
Metric: f1_score

Models Evaluated: 3
- baseline: 0.7500 ± 0.0150
- optimized_v1: 0.8200 ± 0.0120
- optimized_v2: 0.8500 ± 0.0110

Statistical Significance (p < 0.05):
✓ optimized_v2 > baseline (p=0.001)
✓ optimized_v2 > optimized_v1 (p=0.023)
✓ optimized_v1 > baseline (p=0.005)

Best Model: optimized_v2
Improvement over baseline: +13.33%
```

## Statistical Analysis

The framework provides comprehensive statistical analysis:

- **Descriptive Statistics**: Mean, median, std dev, min, max
- **Distribution Analysis**: Percentiles (25th, 50th, 75th, 95th)
- **Significance Testing**: Paired t-tests for model comparison
- **Effect Size**: Cohen's d for practical significance

## Best Practices

### Test Set Design

1. **Representative Sampling**: Ensure test set reflects real-world distribution
2. **Stratification**: Balance across categories and difficulty levels
3. **Size**: Aim for 100+ examples for reliable statistics
4. **Independence**: Avoid data leakage from training set

### Metric Selection

1. **Task-Appropriate**: Choose metrics aligned with task objectives
2. **Multiple Metrics**: Use complementary metrics (e.g., accuracy + F1)
3. **Domain-Specific**: Consider custom metrics for specialized domains
4. **Interpretability**: Prefer metrics stakeholders can understand

### Evaluation Protocol

1. **Reproducibility**: Set random seeds, version test sets
2. **Batch Processing**: Use batch evaluation for efficiency
3. **Error Analysis**: Examine failures, not just aggregate scores
4. **Statistical Rigor**: Report confidence intervals, significance tests

### Comparison Guidelines

1. **Baseline First**: Establish baseline before optimization
2. **Controlled Testing**: Change one variable at a time
3. **Multiple Runs**: Average over multiple evaluation runs
4. **Significance Testing**: Verify improvements are statistically significant

## Implementation Details

### Metric Computation

All metrics implement the `Metric` trait:

```rust
pub trait Metric: Send + Sync {
    fn name(&self) -> &str;
    fn compute(&self, predicted: &str, expected: &str) -> f64;
}
```

Scores are normalized to [0.0, 1.0] range for consistency.

### Statistical Calculations

- **Mean**: Arithmetic mean of individual scores
- **Std Dev**: Sample standard deviation (n-1 denominator)
- **Percentiles**: Linear interpolation between data points
- **T-Test**: Welch's t-test for unequal variances

### Batch Processing

The harness supports efficient batch evaluation:

```rust
let results = harness.evaluate_batch(&test_set, batch_size).await?;
```

This processes examples in parallel while maintaining deterministic ordering.

## Performance Considerations

- **Parallelization**: Batch evaluation uses tokio for concurrent processing
- **Memory**: Streaming for large test sets (use iterators, not full load)
- **Caching**: Cache model predictions to avoid redundant computation
- **Incremental**: Support checkpointing for long evaluations

## Extensions

### Custom Metrics

Implement the `Metric` trait for domain-specific evaluation:

- Factual accuracy for QA systems
- Coherence scores for generation tasks
- Task-specific constraints (e.g., format compliance)

### Advanced Analysis

- Learning curves (performance vs. training data)
- Error categorization and analysis
- Per-category performance breakdown
- Confidence calibration plots

### Integration

- CI/CD pipeline integration for regression testing
- A/B testing framework for production models
- Real-time monitoring dashboards
- Experiment tracking (MLflow, Weights & Biases)

## Examples

Run the example evaluations:

```bash
# Single model evaluation
cargo run --bin eval -- \
  --test-set data/testset.json \
  --model baseline \
  --metric accuracy

# Multi-model comparison
cargo run --bin eval -- \
  --test-set data/testset.json \
  --models baseline,optimized_v1,optimized_v2 \
  --metrics accuracy,f1,bleu \
  --compare

# Batch evaluation with statistics
cargo run --bin eval -- \
  --test-set data/testset.json \
  --model production \
  --batch-size 10 \
  --report detailed
```

## References

- BLEU: Papineni et al. (2002) - "BLEU: a Method for Automatic Evaluation of Machine Translation"
- ROUGE: Lin (2004) - "ROUGE: A Package for Automatic Evaluation of Summaries"
- F1 Score: Van Rijsbergen (1979) - "Information Retrieval"
- Statistical Testing: Dror et al. (2018) - "The Hitchhiker's Guide to Testing Statistical Significance"

## License

MIT
