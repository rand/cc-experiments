# Model Comparison Example

Systematic comparison of multiple DSPy models with statistical significance testing and visual reporting.

## Overview

This example demonstrates how to:
- Compare 2-5 DSPy models simultaneously
- Run side-by-side evaluation on multiple test sets
- Perform statistical significance testing
- Generate visual comparison reports (ASCII tables and HTML)
- Determine winners based on configurable criteria
- Export detailed comparison results

## Comparison Methodology

### 1. Model Selection

Choose models to compare based on:
- **Same task**: All models should solve the same problem
- **Different approaches**: Compare architectures, optimizers, or hyperparameters
- **Baseline inclusion**: Always include a baseline model for reference

### 2. Test Set Selection

Use multiple test sets to ensure robust comparison:
- **Development set**: For initial validation (not used in final metrics)
- **Test set**: Primary evaluation dataset
- **Held-out set**: Additional validation to check generalization
- **Stratified sampling**: Ensure representative coverage of edge cases

### 3. Evaluation Metrics

The comparison framework tracks:
- **Accuracy**: Percentage of correct predictions
- **Latency**: Mean, median, p95, p99 response times
- **Token usage**: Total tokens consumed (cost proxy)
- **Error rate**: Percentage of failed predictions
- **Consistency**: Variance in predictions across runs

### 4. Statistical Testing

#### T-Test (Parametric)
- **Use when**: Comparing means of continuous metrics (accuracy, latency)
- **Assumptions**: Normally distributed data, equal variances
- **Interpretation**: p < 0.05 indicates significant difference

#### Chi-Square Test (Non-Parametric)
- **Use when**: Comparing categorical outcomes (correct/incorrect)
- **Assumptions**: Sufficient sample size (expected count ≥ 5)
- **Interpretation**: p < 0.05 indicates significant association

#### Effect Size (Cohen's d)
- **Small**: d = 0.2
- **Medium**: d = 0.5
- **Large**: d = 0.8
- **Interpretation**: Quantifies practical significance beyond statistical significance

### 5. Winner Determination

Models are ranked by weighted criteria:

```rust
// Example configuration
ComparisonConfig {
    criteria: vec![
        Criterion { name: "accuracy", weight: 0.4, higher_is_better: true },
        Criterion { name: "latency_p95", weight: 0.3, higher_is_better: false },
        Criterion { name: "token_usage", weight: 0.2, higher_is_better: false },
        Criterion { name: "error_rate", weight: 0.1, higher_is_better: false },
    ],
    require_significance: true, // Winner must be statistically significant
    min_effect_size: 0.3, // Minimum practical significance
}
```

Winner selection process:
1. **Calculate weighted scores** for each model
2. **Filter by significance**: Remove models without significant improvements
3. **Check effect size**: Ensure practical significance (not just statistical)
4. **Rank by total score**: Highest weighted score wins
5. **Tie-breaking**: Use secondary criteria (consistency, cost)

### 6. Report Generation

#### ASCII Tables
- Quick terminal-based comparison
- Sortable columns
- Color-coded significance indicators
- Portable for logs and documentation

#### HTML Reports
- Interactive visualizations
- Embedded charts (latency distributions, accuracy trends)
- Statistical test details
- Drill-down into individual predictions

## Usage

### Basic Comparison

```bash
cargo run --release -- \
  --models model1.json model2.json baseline.json \
  --test-set data/test.jsonl \
  --output comparison-report
```

### Advanced Configuration

```bash
cargo run --release -- \
  --models gpt4_optimized.json gpt35_fast.json baseline.json \
  --test-sets data/test.jsonl data/holdout.jsonl \
  --criteria "accuracy:0.4,latency_p95:0.3,cost:0.2,error_rate:0.1" \
  --require-significance \
  --min-effect-size 0.3 \
  --format html \
  --output reports/comparison_2024_01_15.html
```

### Programmatic Usage

```rust
use model_comparison::{ModelComparator, ComparisonConfig, Criterion};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let config = ComparisonConfig {
        test_sets: vec!["data/test.jsonl".into()],
        criteria: vec![
            Criterion::new("accuracy", 0.4, true),
            Criterion::new("latency_p95", 0.3, false),
        ],
        require_significance: true,
        min_effect_size: 0.3,
        num_runs: 3,
    };

    let comparator = ModelComparator::new(config);
    let results = comparator.compare_models(&model_paths).await?;

    // Generate report
    let table = results.to_ascii_table();
    println!("{}", table);

    // Determine winner
    let winner = results.determine_winner()?;
    println!("Winner: {} (score: {:.3})", winner.model_name, winner.total_score);

    // Export detailed results
    results.export_json("comparison-results.json")?;
    results.export_html("comparison-report.html")?;

    Ok(())
}
```

## Interpreting Results

### Statistical Significance

- **p < 0.05**: Strong evidence of difference
- **p < 0.01**: Very strong evidence
- **p ≥ 0.05**: No significant difference (models are equivalent)

**Important**: Statistical significance doesn't guarantee practical importance. Always check effect size.

### Effect Size

- **d < 0.2**: Trivial difference (not worth deploying)
- **0.2 ≤ d < 0.5**: Small but noticeable improvement
- **0.5 ≤ d < 0.8**: Medium improvement (worth considering)
- **d ≥ 0.8**: Large improvement (strong candidate for deployment)

### Winner Interpretation

The winner is determined by:
1. **Weighted score**: Combination of all criteria
2. **Statistical confidence**: p-value indicates reliability
3. **Practical impact**: Effect size shows real-world difference

Example output:
```
Winner: gpt4_optimized (score: 0.847)
  - Accuracy: 94.2% (vs 89.1% baseline, p=0.003, d=0.65)
  - Latency P95: 1.2s (vs 1.8s baseline, p=0.012, d=0.52)
  - Token usage: 450 avg (vs 520 baseline, p=0.087, d=0.31)

Recommendation: Deploy with confidence
  - Medium-to-large effect sizes across key metrics
  - Statistically significant improvements in accuracy and latency
  - 13% cost reduction in token usage (approaching significance)
```

## Best Practices

### 1. Multiple Test Sets
Always validate on multiple datasets to ensure generalization:
```rust
config.test_sets = vec![
    "data/test.jsonl",
    "data/holdout.jsonl",
    "data/edge_cases.jsonl",
];
```

### 2. Repeated Runs
Run evaluations multiple times to account for variance:
```rust
config.num_runs = 5; // Reduces noise in latency/consistency metrics
```

### 3. Fair Comparison
- Use identical test data for all models
- Run comparisons on same hardware
- Control for external factors (time of day, API rate limits)

### 4. Criteria Weighting
Align weights with business priorities:
```rust
// Production system (latency-critical)
Criterion::new("latency_p99", 0.5, false),
Criterion::new("accuracy", 0.3, true),
Criterion::new("cost", 0.2, false),

// Research system (accuracy-critical)
Criterion::new("accuracy", 0.7, true),
Criterion::new("latency_p95", 0.2, false),
Criterion::new("cost", 0.1, false),
```

### 5. Document Decisions
Export detailed reports for reproducibility:
```rust
results.export_json("results.json")?;
results.export_html("report.html")?;
// Include git hash, timestamp, configuration
```

## Output Files

- `comparison-results.json`: Machine-readable results for further analysis
- `comparison-report.html`: Human-friendly visual report
- `comparison-table.txt`: ASCII table for quick reference
- `statistical-tests.json`: Detailed test statistics

## Requirements

- Rust 1.70+
- Python 3.8+ with DSPy installed
- Test datasets in JSONL format

## Related Examples

- **Example 1**: Benchmark suite - Single model performance testing
- **Example 3**: Hyperparameter tuning - Optimize before comparing
- **Example 5**: Regression detection - Track performance over time
