//! Comprehensive evaluation framework for DSPy models
//!
//! This module provides a flexible, extensible evaluation harness supporting
//! multiple metrics, statistical analysis, and model comparison.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::File;
use std::io::BufReader;
use std::path::Path;

/// Trait for evaluation metrics
///
/// Implement this trait to create custom metrics for specific evaluation needs.
pub trait Metric: Send + Sync {
    /// Name of the metric (e.g., "accuracy", "f1_score")
    fn name(&self) -> &str;

    /// Compute metric score for a single prediction
    ///
    /// # Arguments
    /// * `predicted` - Model's predicted output
    /// * `expected` - Ground truth expected output
    ///
    /// # Returns
    /// Score in range [0.0, 1.0] where higher is better
    fn compute(&self, predicted: &str, expected: &str) -> f64;
}

/// Test example with input, expected output, and optional metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestExample {
    pub input: String,
    pub expected_output: String,
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Collection of test examples
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestSet {
    pub examples: Vec<TestExample>,
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl TestSet {
    /// Create empty test set
    pub fn new() -> Self {
        Self {
            examples: Vec::new(),
            metadata: HashMap::new(),
        }
    }

    /// Load test set from JSON file
    pub fn from_json<P: AsRef<Path>>(path: P) -> Result<Self> {
        let file = File::open(path.as_ref())
            .context("Failed to open test set JSON file")?;
        let reader = BufReader::new(file);
        let examples: Vec<TestExample> = serde_json::from_reader(reader)
            .context("Failed to parse test set JSON")?;

        Ok(Self {
            examples,
            metadata: HashMap::new(),
        })
    }

    /// Load test set from CSV file
    pub fn from_csv<P: AsRef<Path>>(path: P) -> Result<Self> {
        let file = File::open(path.as_ref())
            .context("Failed to open test set CSV file")?;
        let mut reader = csv::Reader::from_reader(file);
        let mut examples = Vec::new();

        for result in reader.deserialize() {
            let record: TestExample = result
                .context("Failed to parse CSV record")?;
            examples.push(record);
        }

        Ok(Self {
            examples,
            metadata: HashMap::new(),
        })
    }

    /// Add example to test set
    pub fn add_example(&mut self, example: TestExample) {
        self.examples.push(example);
    }

    /// Number of examples in test set
    pub fn len(&self) -> usize {
        self.examples.len()
    }

    /// Check if test set is empty
    pub fn is_empty(&self) -> bool {
        self.examples.is_empty()
    }

    /// Filter examples by metadata criteria
    pub fn filter<F>(&self, predicate: F) -> Self
    where
        F: Fn(&TestExample) -> bool,
    {
        Self {
            examples: self.examples.iter()
                .filter(|ex| predicate(ex))
                .cloned()
                .collect(),
            metadata: self.metadata.clone(),
        }
    }

    /// Split test set into train/validation sets
    pub fn split(&self, train_ratio: f64) -> (Self, Self) {
        let split_idx = (self.examples.len() as f64 * train_ratio) as usize;

        let train = Self {
            examples: self.examples[..split_idx].to_vec(),
            metadata: self.metadata.clone(),
        };

        let val = Self {
            examples: self.examples[split_idx..].to_vec(),
            metadata: self.metadata.clone(),
        };

        (train, val)
    }
}

impl Default for TestSet {
    fn default() -> Self {
        Self::new()
    }
}

/// Result of evaluating a model on a test set
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluationResult {
    pub model_name: String,
    pub metric_name: String,
    pub num_examples: usize,
    pub mean: f64,
    pub std_dev: f64,
    pub min: f64,
    pub max: f64,
    pub percentile_25: f64,
    pub percentile_50: f64,
    pub percentile_75: f64,
    pub percentile_95: f64,
    pub individual_scores: Vec<f64>,
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl EvaluationResult {
    /// Create evaluation result from individual scores
    pub fn from_scores(
        model_name: String,
        metric_name: String,
        scores: Vec<f64>,
    ) -> Self {
        let num_examples = scores.len();
        let mean = calculate_mean(&scores);
        let std_dev = calculate_std_dev(&scores, mean);
        let min = scores.iter().cloned().fold(f64::INFINITY, f64::min);
        let max = scores.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

        let mut sorted_scores = scores.clone();
        sorted_scores.sort_by(|a, b| a.partial_cmp(b).unwrap());

        let percentile_25 = calculate_percentile(&sorted_scores, 0.25);
        let percentile_50 = calculate_percentile(&sorted_scores, 0.50);
        let percentile_75 = calculate_percentile(&sorted_scores, 0.75);
        let percentile_95 = calculate_percentile(&sorted_scores, 0.95);

        Self {
            model_name,
            metric_name,
            num_examples,
            mean,
            std_dev,
            min,
            max,
            percentile_25,
            percentile_50,
            percentile_75,
            percentile_95,
            individual_scores: scores,
            metadata: HashMap::new(),
        }
    }

    /// Print summary to stdout
    pub fn print_summary(&self) {
        println!("Evaluation Report: {}", self.model_name);
        println!("================================");
        println!("Metric: {}", self.metric_name);
        println!("Total Examples: {}", self.num_examples);
        println!("Mean: {:.4}", self.mean);
        println!("Std Dev: {:.4}", self.std_dev);
        println!("Min: {:.4}", self.min);
        println!("Max: {:.4}", self.max);
        println!("Percentiles:");
        println!("  25th: {:.4}", self.percentile_25);
        println!("  50th: {:.4}", self.percentile_50);
        println!("  75th: {:.4}", self.percentile_75);
        println!("  95th: {:.4}", self.percentile_95);
    }

    /// Save results to JSON file
    pub fn save_json<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let file = File::create(path.as_ref())
            .context("Failed to create results JSON file")?;
        serde_json::to_writer_pretty(file, self)
            .context("Failed to write results JSON")?;
        Ok(())
    }
}

/// Comparison report for multiple models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComparisonReport {
    pub metric_name: String,
    pub models: Vec<ModelSummary>,
    pub comparisons: Vec<PairwiseComparison>,
    pub best_model: String,
    pub improvement_over_baseline: f64,
}

/// Summary statistics for a single model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelSummary {
    pub name: String,
    pub mean: f64,
    pub std_dev: f64,
    pub num_examples: usize,
}

/// Statistical comparison between two models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PairwiseComparison {
    pub model_a: String,
    pub model_b: String,
    pub mean_diff: f64,
    pub p_value: f64,
    pub significant: bool,
    pub effect_size: f64,
}

impl ComparisonReport {
    /// Compare multiple evaluation results
    pub fn compare(
        results: Vec<EvaluationResult>,
        significance_threshold: f64,
    ) -> Result<Self> {
        if results.is_empty() {
            anyhow::bail!("Cannot compare empty results");
        }

        let metric_name = results[0].metric_name.clone();

        // Build model summaries
        let mut models: Vec<ModelSummary> = results.iter().map(|r| {
            ModelSummary {
                name: r.model_name.clone(),
                mean: r.mean,
                std_dev: r.std_dev,
                num_examples: r.num_examples,
            }
        }).collect();

        // Sort by mean descending
        models.sort_by(|a, b| b.mean.partial_cmp(&a.mean).unwrap());

        // Pairwise comparisons
        let mut comparisons = Vec::new();
        for i in 0..results.len() {
            for j in (i + 1)..results.len() {
                let comp = Self::pairwise_comparison(
                    &results[i],
                    &results[j],
                    significance_threshold,
                );
                comparisons.push(comp);
            }
        }

        // Find best model
        let best_model = models[0].name.clone();

        // Calculate improvement over baseline (assume first result is baseline)
        let baseline_mean = results[0].mean;
        let best_mean = models[0].mean;
        let improvement_over_baseline = if baseline_mean > 0.0 {
            ((best_mean - baseline_mean) / baseline_mean) * 100.0
        } else {
            0.0
        };

        Ok(Self {
            metric_name,
            models,
            comparisons,
            best_model,
            improvement_over_baseline,
        })
    }

    /// Perform pairwise statistical comparison
    fn pairwise_comparison(
        result_a: &EvaluationResult,
        result_b: &EvaluationResult,
        threshold: f64,
    ) -> PairwiseComparison {
        let mean_diff = result_b.mean - result_a.mean;

        // Welch's t-test
        let (t_stat, df) = welch_t_test(
            &result_a.individual_scores,
            &result_b.individual_scores,
        );

        // Approximate p-value (simplified)
        let p_value = estimate_p_value(t_stat.abs(), df);
        let significant = p_value < threshold;

        // Cohen's d effect size
        let pooled_std = ((result_a.std_dev.powi(2) + result_b.std_dev.powi(2)) / 2.0).sqrt();
        let effect_size = if pooled_std > 0.0 {
            mean_diff / pooled_std
        } else {
            0.0
        };

        PairwiseComparison {
            model_a: result_a.model_name.clone(),
            model_b: result_b.model_name.clone(),
            mean_diff,
            p_value,
            significant,
            effect_size,
        }
    }

    /// Print comparison summary
    pub fn print_summary(&self) {
        println!("Model Comparison Report");
        println!("======================");
        println!("Metric: {}\n", self.metric_name);

        println!("Models Evaluated: {}", self.models.len());
        for model in &self.models {
            println!("- {}: {:.4} ± {:.4}", model.name, model.mean, model.std_dev);
        }

        println!("\nStatistical Significance (p < 0.05):");
        for comp in &self.comparisons {
            if comp.significant {
                let symbol = if comp.mean_diff > 0.0 { ">" } else { "<" };
                println!(
                    "✓ {} {} {} (p={:.3}, d={:.2})",
                    comp.model_b, symbol, comp.model_a, comp.p_value, comp.effect_size
                );
            }
        }

        println!("\nBest Model: {}", self.best_model);
        println!("Improvement: {:.2}%", self.improvement_over_baseline);
    }

    /// Save report to JSON file
    pub fn save_json<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let file = File::create(path.as_ref())
            .context("Failed to create comparison JSON file")?;
        serde_json::to_writer_pretty(file, self)
            .context("Failed to write comparison JSON")?;
        Ok(())
    }
}

/// Main evaluation harness
pub struct EvaluationHarness {
    metric: Box<dyn Metric>,
}

impl EvaluationHarness {
    /// Create new harness with given metric
    pub fn new(metric: Box<dyn Metric>) -> Self {
        Self { metric }
    }

    /// Evaluate model on test set
    pub async fn evaluate<F>(
        &self,
        test_set: &TestSet,
        model_name: &str,
        mut predictor: F,
    ) -> Result<EvaluationResult>
    where
        F: FnMut(&TestExample) -> String,
    {
        let mut scores = Vec::new();

        for example in &test_set.examples {
            let predicted = predictor(example);
            let score = self.metric.compute(&predicted, &example.expected_output);
            scores.push(score);
        }

        Ok(EvaluationResult::from_scores(
            model_name.to_string(),
            self.metric.name().to_string(),
            scores,
        ))
    }

    /// Evaluate model on test set with batch processing
    pub async fn evaluate_batch<F>(
        &self,
        test_set: &TestSet,
        model_name: &str,
        batch_size: usize,
        mut batch_predictor: F,
    ) -> Result<EvaluationResult>
    where
        F: FnMut(&[TestExample]) -> Vec<String>,
    {
        let mut scores = Vec::new();

        for chunk in test_set.examples.chunks(batch_size) {
            let predictions = batch_predictor(chunk);

            for (example, predicted) in chunk.iter().zip(predictions.iter()) {
                let score = self.metric.compute(predicted, &example.expected_output);
                scores.push(score);
            }
        }

        Ok(EvaluationResult::from_scores(
            model_name.to_string(),
            self.metric.name().to_string(),
            scores,
        ))
    }
}

// Built-in Metrics

/// Accuracy metric: proportion of exact matches
pub struct Accuracy;

impl Metric for Accuracy {
    fn name(&self) -> &str {
        "accuracy"
    }

    fn compute(&self, predicted: &str, expected: &str) -> f64 {
        if predicted.trim() == expected.trim() {
            1.0
        } else {
            0.0
        }
    }
}

/// Exact match metric with case sensitivity option
pub struct ExactMatch {
    case_sensitive: bool,
}

impl ExactMatch {
    pub fn new(case_sensitive: bool) -> Self {
        Self { case_sensitive }
    }
}

impl Metric for ExactMatch {
    fn name(&self) -> &str {
        "exact_match"
    }

    fn compute(&self, predicted: &str, expected: &str) -> f64 {
        let pred = predicted.trim();
        let exp = expected.trim();

        let matches = if self.case_sensitive {
            pred == exp
        } else {
            pred.to_lowercase() == exp.to_lowercase()
        };

        if matches { 1.0 } else { 0.0 }
    }
}

/// F1 score metric for token-based comparison
pub struct F1Score;

impl Metric for F1Score {
    fn name(&self) -> &str {
        "f1_score"
    }

    fn compute(&self, predicted: &str, expected: &str) -> f64 {
        let pred_tokens: Vec<&str> = predicted.split_whitespace().collect();
        let exp_tokens: Vec<&str> = expected.split_whitespace().collect();

        if pred_tokens.is_empty() && exp_tokens.is_empty() {
            return 1.0;
        }

        if pred_tokens.is_empty() || exp_tokens.is_empty() {
            return 0.0;
        }

        // Calculate overlap
        let mut tp = 0;
        for token in &pred_tokens {
            if exp_tokens.contains(token) {
                tp += 1;
            }
        }

        let precision = tp as f64 / pred_tokens.len() as f64;
        let recall = tp as f64 / exp_tokens.len() as f64;

        if precision + recall == 0.0 {
            0.0
        } else {
            2.0 * (precision * recall) / (precision + recall)
        }
    }
}

/// BLEU score metric for n-gram overlap
pub struct BLEU {
    n: usize,
}

impl BLEU {
    pub fn new(n: usize) -> Self {
        Self { n }
    }

    fn calculate_ngram_overlap(&self, predicted: &str, expected: &str) -> f64 {
        let pred_tokens: Vec<&str> = predicted.split_whitespace().collect();
        let exp_tokens: Vec<&str> = expected.split_whitespace().collect();

        if pred_tokens.len() < self.n || exp_tokens.len() < self.n {
            return 0.0;
        }

        let mut matches = 0;
        let mut total = 0;

        for i in 0..=(pred_tokens.len() - self.n) {
            let pred_ngram = &pred_tokens[i..i + self.n];
            total += 1;

            for j in 0..=(exp_tokens.len() - self.n) {
                let exp_ngram = &exp_tokens[j..j + self.n];
                if pred_ngram == exp_ngram {
                    matches += 1;
                    break;
                }
            }
        }

        if total == 0 {
            0.0
        } else {
            matches as f64 / total as f64
        }
    }
}

impl Metric for BLEU {
    fn name(&self) -> &str {
        "bleu"
    }

    fn compute(&self, predicted: &str, expected: &str) -> f64 {
        self.calculate_ngram_overlap(predicted, expected)
    }
}

/// ROUGE score metric for recall-based evaluation
pub struct ROUGE {
    variant: String,
}

impl ROUGE {
    pub fn new(variant: &str) -> Self {
        Self {
            variant: variant.to_string(),
        }
    }

    fn calculate_rouge_l(&self, predicted: &str, expected: &str) -> f64 {
        let pred_tokens: Vec<&str> = predicted.split_whitespace().collect();
        let exp_tokens: Vec<&str> = expected.split_whitespace().collect();

        if pred_tokens.is_empty() || exp_tokens.is_empty() {
            return 0.0;
        }

        // Longest common subsequence
        let lcs_length = lcs(&pred_tokens, &exp_tokens);

        let recall = lcs_length as f64 / exp_tokens.len() as f64;
        let precision = lcs_length as f64 / pred_tokens.len() as f64;

        if recall + precision == 0.0 {
            0.0
        } else {
            2.0 * (recall * precision) / (recall + precision)
        }
    }
}

impl Metric for ROUGE {
    fn name(&self) -> &str {
        "rouge"
    }

    fn compute(&self, predicted: &str, expected: &str) -> f64 {
        match self.variant.as_str() {
            "rouge-l" => self.calculate_rouge_l(predicted, expected),
            _ => 0.0, // Default to 0 for unsupported variants
        }
    }
}

// Statistical helper functions

fn calculate_mean(values: &[f64]) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    values.iter().sum::<f64>() / values.len() as f64
}

fn calculate_std_dev(values: &[f64], mean: f64) -> f64 {
    if values.len() <= 1 {
        return 0.0;
    }

    let variance = values.iter()
        .map(|v| (v - mean).powi(2))
        .sum::<f64>() / (values.len() - 1) as f64;

    variance.sqrt()
}

fn calculate_percentile(sorted_values: &[f64], percentile: f64) -> f64 {
    if sorted_values.is_empty() {
        return 0.0;
    }

    let idx = (percentile * (sorted_values.len() - 1) as f64) as usize;
    sorted_values[idx]
}

fn welch_t_test(sample_a: &[f64], sample_b: &[f64]) -> (f64, f64) {
    let mean_a = calculate_mean(sample_a);
    let mean_b = calculate_mean(sample_b);
    let var_a = calculate_std_dev(sample_a, mean_a).powi(2);
    let var_b = calculate_std_dev(sample_b, mean_b).powi(2);
    let n_a = sample_a.len() as f64;
    let n_b = sample_b.len() as f64;

    let t_stat = (mean_a - mean_b) / ((var_a / n_a) + (var_b / n_b)).sqrt();

    // Welch-Satterthwaite degrees of freedom
    let numerator = ((var_a / n_a) + (var_b / n_b)).powi(2);
    let denominator = (var_a / n_a).powi(2) / (n_a - 1.0)
        + (var_b / n_b).powi(2) / (n_b - 1.0);
    let df = numerator / denominator;

    (t_stat, df)
}

fn estimate_p_value(t_stat: f64, _df: f64) -> f64 {
    // Simplified p-value estimation (not exact, but reasonable approximation)
    // For production use, consider integrating a proper statistics library
    let critical_values = vec![
        (1.0, 0.10),
        (1.645, 0.05),
        (2.0, 0.025),
        (2.576, 0.01),
        (3.0, 0.001),
    ];

    for (t_crit, p) in critical_values.iter().rev() {
        if t_stat >= *t_crit {
            return *p;
        }
    }

    0.10 // Default for small t-statistics
}

fn lcs<T: PartialEq>(a: &[T], b: &[T]) -> usize {
    let m = a.len();
    let n = b.len();
    let mut dp = vec![vec![0; n + 1]; m + 1];

    for i in 1..=m {
        for j in 1..=n {
            if a[i - 1] == b[j - 1] {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = dp[i - 1][j].max(dp[i][j - 1]);
            }
        }
    }

    dp[m][n]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_accuracy_metric() {
        let metric = Accuracy;
        assert_eq!(metric.compute("hello", "hello"), 1.0);
        assert_eq!(metric.compute("hello", "world"), 0.0);
        assert_eq!(metric.compute("  hello  ", "hello"), 1.0);
    }

    #[test]
    fn test_f1_score() {
        let metric = F1Score;
        assert_eq!(metric.compute("hello world", "hello world"), 1.0);
        assert!(metric.compute("hello world", "hello") > 0.0);
        assert_eq!(metric.compute("", ""), 1.0);
    }

    #[test]
    fn test_test_set_filtering() {
        let mut test_set = TestSet::new();
        test_set.add_example(TestExample {
            input: "q1".to_string(),
            expected_output: "a1".to_string(),
            metadata: [("category".to_string(), serde_json::json!("easy"))]
                .iter().cloned().collect(),
        });

        let filtered = test_set.filter(|ex| {
            ex.metadata.get("category")
                .and_then(|v| v.as_str())
                .map(|s| s == "easy")
                .unwrap_or(false)
        });

        assert_eq!(filtered.len(), 1);
    }

    #[tokio::test]
    async fn test_evaluation_harness() {
        let mut test_set = TestSet::new();
        test_set.add_example(TestExample {
            input: "test".to_string(),
            expected_output: "test".to_string(),
            metadata: HashMap::new(),
        });

        let harness = EvaluationHarness::new(Box::new(Accuracy));
        let result = harness.evaluate(
            &test_set,
            "test_model",
            |ex| ex.input.clone(),
        ).await.unwrap();

        assert_eq!(result.mean, 1.0);
        assert_eq!(result.num_examples, 1);
    }
}
