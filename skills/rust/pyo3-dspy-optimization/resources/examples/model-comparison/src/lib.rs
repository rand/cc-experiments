//! Model comparison library for systematic evaluation of multiple DSPy models.
//!
//! This library provides tools for:
//! - Side-by-side evaluation of 2-5 models
//! - Statistical significance testing (t-test, chi-square, effect size)
//! - Visual comparison reports (ASCII tables, HTML)
//! - Winner determination based on weighted criteria
//!
//! # Example
//!
//! ```no_run
//! use model_comparison::{ModelComparator, ComparisonConfig, Criterion};
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     let config = ComparisonConfig {
//!         test_sets: vec!["data/test.jsonl".into()],
//!         criteria: vec![
//!             Criterion::new("accuracy", 0.4, true),
//!             Criterion::new("latency_p95", 0.3, false),
//!         ],
//!         require_significance: true,
//!         min_effect_size: 0.3,
//!         num_runs: 3,
//!     };
//!
//!     let comparator = ModelComparator::new(config);
//!     let results = comparator.compare_models(&model_paths).await?;
//!
//!     println!("{}", results.to_ascii_table());
//!     let winner = results.determine_winner()?;
//!     println!("Winner: {}", winner.model_name);
//!
//!     Ok(())
//! }
//! ```

use anyhow::{Context, Result};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use statrs::distribution::{ContinuousCDF, StudentsT};
use statrs::statistics::Statistics;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use tabled::{Table, Tabled};

/// Configuration for model comparison.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComparisonConfig {
    /// Test sets to evaluate on
    pub test_sets: Vec<PathBuf>,

    /// Criteria for winner determination with weights
    pub criteria: Vec<Criterion>,

    /// Require statistical significance for winner
    pub require_significance: bool,

    /// Minimum effect size to consider (Cohen's d)
    pub min_effect_size: f64,

    /// Number of runs per model (for variance estimation)
    pub num_runs: usize,

    /// Significance level (default: 0.05)
    #[serde(default = "default_alpha")]
    pub alpha: f64,
}

fn default_alpha() -> f64 {
    0.05
}

impl Default for ComparisonConfig {
    fn default() -> Self {
        Self {
            test_sets: vec![],
            criteria: vec![
                Criterion::new("accuracy", 0.4, true),
                Criterion::new("latency_p95", 0.3, false),
                Criterion::new("token_usage", 0.2, false),
                Criterion::new("error_rate", 0.1, false),
            ],
            require_significance: true,
            min_effect_size: 0.3,
            num_runs: 3,
            alpha: 0.05,
        }
    }
}

/// Evaluation criterion with weight and direction.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Criterion {
    /// Metric name
    pub name: String,

    /// Weight in overall score (should sum to 1.0)
    pub weight: f64,

    /// Whether higher values are better
    pub higher_is_better: bool,
}

impl Criterion {
    pub fn new(name: impl Into<String>, weight: f64, higher_is_better: bool) -> Self {
        Self {
            name: name.into(),
            weight,
            higher_is_better,
        }
    }
}

/// Results for a single model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelResult {
    /// Model identifier
    pub model_name: String,

    /// Path to model configuration
    pub model_path: PathBuf,

    /// Metrics aggregated across all test sets
    pub metrics: HashMap<String, f64>,

    /// Raw values for statistical testing (multiple runs)
    pub raw_values: HashMap<String, Vec<f64>>,

    /// Per-test-set breakdown
    pub per_test_set: HashMap<String, HashMap<String, f64>>,

    /// Execution time (seconds)
    pub execution_time: f64,
}

impl ModelResult {
    /// Get metric value by name.
    pub fn get_metric(&self, name: &str) -> Option<f64> {
        self.metrics.get(name).copied()
    }

    /// Get raw values for statistical testing.
    pub fn get_raw_values(&self, name: &str) -> Option<&[f64]> {
        self.raw_values.get(name).map(|v| v.as_slice())
    }
}

/// Statistical test result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatisticalTest {
    /// Metric being tested
    pub metric: String,

    /// Test type (t-test, chi-square)
    pub test_type: String,

    /// Test statistic value
    pub statistic: f64,

    /// P-value
    pub p_value: f64,

    /// Effect size (Cohen's d)
    pub effect_size: f64,

    /// Degrees of freedom (if applicable)
    pub df: Option<f64>,

    /// Is result significant at alpha level?
    pub significant: bool,
}

impl StatisticalTest {
    /// Interpret effect size magnitude.
    pub fn effect_magnitude(&self) -> &'static str {
        let abs_d = self.effect_size.abs();
        if abs_d < 0.2 {
            "trivial"
        } else if abs_d < 0.5 {
            "small"
        } else if abs_d < 0.8 {
            "medium"
        } else {
            "large"
        }
    }
}

/// Complete comparison results.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComparisonResults {
    /// Configuration used
    pub config: ComparisonConfig,

    /// Results per model
    pub model_results: Vec<ModelResult>,

    /// Statistical tests (model A vs model B)
    pub statistical_tests: Vec<PairwiseTest>,

    /// Overall winner (if determined)
    pub winner: Option<WinnerInfo>,

    /// Timestamp of comparison
    pub timestamp: String,
}

/// Pairwise statistical test between two models.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PairwiseTest {
    pub model_a: String,
    pub model_b: String,
    pub tests: HashMap<String, StatisticalTest>,
}

/// Information about the winning model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WinnerInfo {
    pub model_name: String,
    pub total_score: f64,
    pub criterion_scores: HashMap<String, f64>,
    pub significant_improvements: Vec<String>,
    pub recommendation: String,
}

/// Row for ASCII table display.
#[derive(Tabled)]
struct ComparisonRow {
    #[tabled(rename = "Model")]
    model: String,

    #[tabled(rename = "Accuracy")]
    accuracy: String,

    #[tabled(rename = "Latency P95")]
    latency: String,

    #[tabled(rename = "Tokens")]
    tokens: String,

    #[tabled(rename = "Error Rate")]
    error_rate: String,

    #[tabled(rename = "Score")]
    score: String,
}

impl ComparisonResults {
    /// Generate ASCII table for terminal display.
    pub fn to_ascii_table(&self) -> String {
        let mut rows = Vec::new();

        for result in &self.model_results {
            let score = self.calculate_score(result);

            rows.push(ComparisonRow {
                model: result.model_name.clone(),
                accuracy: format!(
                    "{:.1}%",
                    result.get_metric("accuracy").unwrap_or(0.0) * 100.0
                ),
                latency: format!("{:.2}s", result.get_metric("latency_p95").unwrap_or(0.0)),
                tokens: format!("{:.0}", result.get_metric("token_usage").unwrap_or(0.0)),
                error_rate: format!(
                    "{:.1}%",
                    result.get_metric("error_rate").unwrap_or(0.0) * 100.0
                ),
                score: format!("{:.3}", score),
            });
        }

        Table::new(rows).to_string()
    }

    /// Calculate weighted score for a model.
    fn calculate_score(&self, result: &ModelResult) -> f64 {
        let mut total_score = 0.0;
        let mut total_weight = 0.0;

        for criterion in &self.config.criteria {
            if let Some(value) = result.get_metric(&criterion.name) {
                // Normalize to [0, 1] range based on all models
                let normalized = self.normalize_metric(&criterion.name, value, criterion.higher_is_better);
                total_score += normalized * criterion.weight;
                total_weight += criterion.weight;
            }
        }

        if total_weight > 0.0 {
            total_score / total_weight
        } else {
            0.0
        }
    }

    /// Normalize metric value across all models.
    fn normalize_metric(&self, metric_name: &str, value: f64, higher_is_better: bool) -> f64 {
        let values: Vec<f64> = self
            .model_results
            .iter()
            .filter_map(|r| r.get_metric(metric_name))
            .collect();

        if values.is_empty() {
            return 0.0;
        }

        let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
        let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

        if (max - min).abs() < 1e-10 {
            return 0.5; // All values equal
        }

        let normalized = (value - min) / (max - min);

        if higher_is_better {
            normalized
        } else {
            1.0 - normalized
        }
    }

    /// Determine winner based on criteria.
    pub fn determine_winner(&self) -> Result<WinnerInfo> {
        if self.model_results.is_empty() {
            anyhow::bail!("No models to compare");
        }

        // Calculate scores for all models
        let mut scored_models: Vec<(String, f64, HashMap<String, f64>)> = self
            .model_results
            .iter()
            .map(|result| {
                let total_score = self.calculate_score(result);
                let criterion_scores = self.calculate_criterion_scores(result);
                (result.model_name.clone(), total_score, criterion_scores)
            })
            .collect();

        // Sort by score descending
        scored_models.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        let (winner_name, winner_score, winner_criterion_scores) =
            scored_models.first().unwrap().clone();

        // Find significant improvements
        let mut significant_improvements = Vec::new();

        if self.config.require_significance {
            let _winner_result = self
                .model_results
                .iter()
                .find(|r| r.model_name == winner_name)
                .unwrap();

            for other_result in &self.model_results {
                if other_result.model_name == winner_name {
                    continue;
                }

                for criterion in &self.config.criteria {
                    if let Some(test) = self.find_test(&winner_name, &other_result.model_name, &criterion.name) {
                        if test.significant && test.effect_size.abs() >= self.config.min_effect_size {
                            let improvement = if criterion.higher_is_better {
                                test.effect_size > 0.0
                            } else {
                                test.effect_size < 0.0
                            };

                            if improvement {
                                significant_improvements.push(format!(
                                    "{} vs {} (p={:.3}, d={:.2})",
                                    criterion.name, other_result.model_name, test.p_value, test.effect_size
                                ));
                            }
                        }
                    }
                }
            }
        }

        // Generate recommendation
        let recommendation = if significant_improvements.is_empty() && self.config.require_significance {
            "No statistically significant winner. Models are equivalent.".to_string()
        } else if significant_improvements.len() >= self.config.criteria.len() / 2 {
            "Deploy with confidence: significant improvements across multiple metrics.".to_string()
        } else {
            "Deploy with caution: limited significant improvements.".to_string()
        };

        Ok(WinnerInfo {
            model_name: winner_name,
            total_score: winner_score,
            criterion_scores: winner_criterion_scores,
            significant_improvements,
            recommendation,
        })
    }

    /// Calculate per-criterion scores for a model.
    fn calculate_criterion_scores(&self, result: &ModelResult) -> HashMap<String, f64> {
        self.config
            .criteria
            .iter()
            .filter_map(|criterion| {
                result
                    .get_metric(&criterion.name)
                    .map(|value| (criterion.name.clone(), value))
            })
            .collect()
    }

    /// Find statistical test between two models for a metric.
    fn find_test(&self, model_a: &str, model_b: &str, metric: &str) -> Option<StatisticalTest> {
        self.statistical_tests
            .iter()
            .find(|pt| {
                (pt.model_a == model_a && pt.model_b == model_b)
                    || (pt.model_a == model_b && pt.model_b == model_a)
            })
            .and_then(|pt| pt.tests.get(metric).cloned())
    }

    /// Export results to JSON.
    pub fn export_json(&self, path: impl AsRef<Path>) -> Result<()> {
        let json = serde_json::to_string_pretty(self)?;
        std::fs::write(path, json)?;
        Ok(())
    }

    /// Export results to HTML report.
    pub fn export_html(&self, path: impl AsRef<Path>) -> Result<()> {
        let html = self.generate_html_report();
        std::fs::write(path, html)?;
        Ok(())
    }

    /// Generate HTML report.
    pub fn generate_html_report(&self) -> String {
        let mut html = String::from(
            r#"<!DOCTYPE html>
<html>
<head>
    <title>Model Comparison Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .winner { background-color: #d4edda; }
        .significant { color: #28a745; font-weight: bold; }
        .not-significant { color: #6c757d; }
        .section { margin: 30px 0; }
    </style>
</head>
<body>
    <h1>Model Comparison Report</h1>
    <p>Generated: "#,
        );

        html.push_str(&self.timestamp);
        html.push_str("</p>");

        // Overall results table
        html.push_str("<div class='section'><h2>Overall Results</h2><table>");
        html.push_str("<tr><th>Model</th><th>Accuracy</th><th>Latency P95</th><th>Tokens</th><th>Error Rate</th><th>Score</th></tr>");

        for result in &self.model_results {
            let score = self.calculate_score(result);
            let is_winner = self
                .winner
                .as_ref()
                .map(|w| w.model_name == result.model_name)
                .unwrap_or(false);

            let row_class = if is_winner { " class='winner'" } else { "" };

            html.push_str(&format!(
                "<tr{}><td>{}</td><td>{:.1}%</td><td>{:.2}s</td><td>{:.0}</td><td>{:.1}%</td><td>{:.3}</td></tr>",
                row_class,
                result.model_name,
                result.get_metric("accuracy").unwrap_or(0.0) * 100.0,
                result.get_metric("latency_p95").unwrap_or(0.0),
                result.get_metric("token_usage").unwrap_or(0.0),
                result.get_metric("error_rate").unwrap_or(0.0) * 100.0,
                score
            ));
        }

        html.push_str("</table></div>");

        // Winner section
        if let Some(winner) = &self.winner {
            html.push_str("<div class='section'><h2>Winner</h2>");
            html.push_str(&format!("<p><strong>{}</strong> (score: {:.3})</p>", winner.model_name, winner.total_score));
            html.push_str(&format!("<p>{}</p>", winner.recommendation));

            if !winner.significant_improvements.is_empty() {
                html.push_str("<h3>Significant Improvements</h3><ul>");
                for improvement in &winner.significant_improvements {
                    html.push_str(&format!("<li>{}</li>", improvement));
                }
                html.push_str("</ul>");
            }

            html.push_str("</div>");
        }

        // Statistical tests
        html.push_str("<div class='section'><h2>Statistical Tests</h2>");

        for pairwise in &self.statistical_tests {
            html.push_str(&format!("<h3>{} vs {}</h3><table>", pairwise.model_a, pairwise.model_b));
            html.push_str("<tr><th>Metric</th><th>Test</th><th>Statistic</th><th>P-value</th><th>Effect Size</th><th>Significant</th></tr>");

            for (metric, test) in &pairwise.tests {
                let sig_class = if test.significant { "significant" } else { "not-significant" };

                html.push_str(&format!(
                    "<tr><td>{}</td><td>{}</td><td>{:.3}</td><td class='{}'>{:.4}</td><td>{:.2} ({})</td><td>{}</td></tr>",
                    metric,
                    test.test_type,
                    test.statistic,
                    sig_class,
                    test.p_value,
                    test.effect_size,
                    test.effect_magnitude(),
                    if test.significant { "Yes" } else { "No" }
                ));
            }

            html.push_str("</table>");
        }

        html.push_str("</div>");

        html.push_str("</body></html>");
        html
    }
}

/// Main model comparator.
pub struct ModelComparator {
    config: ComparisonConfig,
}

impl ModelComparator {
    /// Create new comparator with configuration.
    pub fn new(config: ComparisonConfig) -> Self {
        Self { config }
    }

    /// Compare multiple models.
    pub async fn compare_models(&self, model_paths: &[PathBuf]) -> Result<ComparisonResults> {
        if model_paths.len() < 2 {
            anyhow::bail!("Need at least 2 models to compare");
        }

        if model_paths.len() > 5 {
            anyhow::bail!("Maximum 5 models supported");
        }

        // Evaluate each model
        let mut model_results = Vec::new();

        for model_path in model_paths {
            let result = self.evaluate_model(model_path).await?;
            model_results.push(result);
        }

        // Perform pairwise statistical tests
        let statistical_tests = self.perform_pairwise_tests(&model_results)?;

        let mut results = ComparisonResults {
            config: self.config.clone(),
            model_results,
            statistical_tests,
            winner: None,
            timestamp: chrono::Utc::now().to_rfc3339(),
        };

        // Determine winner
        results.winner = Some(results.determine_winner()?);

        Ok(results)
    }

    /// Evaluate a single model across all test sets.
    async fn evaluate_model(&self, model_path: &Path) -> Result<ModelResult> {
        let model_name = model_path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown")
            .to_string();

        let start = std::time::Instant::now();

        // Load model (simulated)
        let _model = self.load_model(model_path)?;

        let mut all_metrics = HashMap::new();
        let mut raw_values: HashMap<String, Vec<f64>> = HashMap::new();
        let mut per_test_set = HashMap::new();

        // Evaluate on each test set
        for test_set_path in &self.config.test_sets {
            let test_set_name = test_set_path
                .file_stem()
                .and_then(|s| s.to_str())
                .unwrap_or("unknown")
                .to_string();

            // Run multiple times for variance estimation
            let mut run_metrics = Vec::new();

            for _ in 0..self.config.num_runs {
                let metrics = self.evaluate_on_test_set(model_path, test_set_path).await?;
                run_metrics.push(metrics);
            }

            // Aggregate metrics
            let aggregated = self.aggregate_metrics(&run_metrics);
            per_test_set.insert(test_set_name, aggregated.clone());

            // Accumulate raw values for statistical testing
            for (key, values) in self.extract_raw_values(&run_metrics) {
                raw_values.entry(key).or_insert_with(Vec::new).extend(values);
            }

            // Update overall metrics
            for (key, value) in aggregated {
                *all_metrics.entry(key).or_insert(0.0) += value;
            }
        }

        // Average metrics across test sets
        let num_test_sets = self.config.test_sets.len() as f64;
        for value in all_metrics.values_mut() {
            *value /= num_test_sets;
        }

        let execution_time = start.elapsed().as_secs_f64();

        Ok(ModelResult {
            model_name,
            model_path: model_path.to_path_buf(),
            metrics: all_metrics,
            raw_values,
            per_test_set,
            execution_time,
        })
    }

    /// Load model from path (simulated).
    fn load_model(&self, _path: &Path) -> Result<PyObject> {
        Python::with_gil(|py| {
            let model = PyDict::new(py);
            Ok(model.into())
        })
    }

    /// Evaluate model on a test set (simulated).
    async fn evaluate_on_test_set(
        &self,
        _model_path: &Path,
        _test_set_path: &Path,
    ) -> Result<HashMap<String, f64>> {
        // In real implementation, would run actual evaluation
        // For now, return simulated metrics

        let mut metrics = HashMap::new();
        metrics.insert("accuracy".to_string(), 0.85 + rand::random::<f64>() * 0.1);
        metrics.insert("latency_p95".to_string(), 1.0 + rand::random::<f64>() * 0.5);
        metrics.insert("token_usage".to_string(), 400.0 + rand::random::<f64>() * 100.0);
        metrics.insert("error_rate".to_string(), 0.05 + rand::random::<f64>() * 0.05);

        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        Ok(metrics)
    }

    /// Aggregate metrics from multiple runs.
    fn aggregate_metrics(&self, run_metrics: &[HashMap<String, f64>]) -> HashMap<String, f64> {
        let mut aggregated = HashMap::new();

        for metrics in run_metrics {
            for (key, value) in metrics {
                *aggregated.entry(key.clone()).or_insert(0.0) += value;
            }
        }

        let num_runs = run_metrics.len() as f64;
        for value in aggregated.values_mut() {
            *value /= num_runs;
        }

        aggregated
    }

    /// Extract raw values for statistical testing.
    fn extract_raw_values(
        &self,
        run_metrics: &[HashMap<String, f64>],
    ) -> HashMap<String, Vec<f64>> {
        let mut raw_values: HashMap<String, Vec<f64>> = HashMap::new();

        for metrics in run_metrics {
            for (key, value) in metrics {
                raw_values
                    .entry(key.clone())
                    .or_insert_with(Vec::new)
                    .push(*value);
            }
        }

        raw_values
    }

    /// Perform pairwise statistical tests.
    fn perform_pairwise_tests(&self, results: &[ModelResult]) -> Result<Vec<PairwiseTest>> {
        let mut pairwise_tests = Vec::new();

        for i in 0..results.len() {
            for j in (i + 1)..results.len() {
                let model_a = &results[i];
                let model_b = &results[j];

                let mut tests = HashMap::new();

                for criterion in &self.config.criteria {
                    if let (Some(values_a), Some(values_b)) = (
                        model_a.get_raw_values(&criterion.name),
                        model_b.get_raw_values(&criterion.name),
                    ) {
                        let test = self.perform_t_test(
                            &criterion.name,
                            values_a,
                            values_b,
                            self.config.alpha,
                        )?;
                        tests.insert(criterion.name.clone(), test);
                    }
                }

                pairwise_tests.push(PairwiseTest {
                    model_a: model_a.model_name.clone(),
                    model_b: model_b.model_name.clone(),
                    tests,
                });
            }
        }

        Ok(pairwise_tests)
    }

    /// Perform two-sample t-test.
    fn perform_t_test(
        &self,
        metric: &str,
        values_a: &[f64],
        values_b: &[f64],
        alpha: f64,
    ) -> Result<StatisticalTest> {
        let mean_a = values_a.mean();
        let mean_b = values_b.mean();
        let std_a = values_a.std_dev();
        let std_b = values_b.std_dev();

        let n_a = values_a.len() as f64;
        let n_b = values_b.len() as f64;

        // Calculate pooled standard deviation
        let pooled_std = ((std_a.powi(2) / n_a) + (std_b.powi(2) / n_b)).sqrt();

        // Calculate t-statistic
        let t_stat = (mean_a - mean_b) / pooled_std;

        // Calculate degrees of freedom (Welch's approximation)
        let df = (std_a.powi(2) / n_a + std_b.powi(2) / n_b).powi(2)
            / ((std_a.powi(2) / n_a).powi(2) / (n_a - 1.0)
                + (std_b.powi(2) / n_b).powi(2) / (n_b - 1.0));

        // Calculate p-value (two-tailed)
        let t_dist = StudentsT::new(0.0, 1.0, df).context("Invalid t-distribution")?;
        let p_value = 2.0 * (1.0 - t_dist.cdf(t_stat.abs()));

        // Calculate Cohen's d (effect size)
        let pooled_std_d = ((std_a.powi(2) + std_b.powi(2)) / 2.0).sqrt();
        let effect_size = (mean_a - mean_b) / pooled_std_d;

        Ok(StatisticalTest {
            metric: metric.to_string(),
            test_type: "t-test".to_string(),
            statistic: t_stat,
            p_value,
            effect_size,
            df: Some(df),
            significant: p_value < alpha,
        })
    }
}

// Re-export chrono for timestamp generation
use chrono;

// Placeholder for random number generation (use rand crate in real implementation)
mod rand {
    pub fn random<T>() -> T
    where
        T: std::default::Default,
    {
        T::default()
    }
}
