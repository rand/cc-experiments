use anyhow::{anyhow, Context, Result};
use chrono::{DateTime, Duration, Utc};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use rand::distributions::WeightedIndex;
use rand::prelude::*;
use serde::{Deserialize, Serialize};
use statrs::distribution::{ChiSquared, ContinuousCDF, StudentsT};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Traffic splitting strategy for routing requests
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum TrafficStrategy {
    /// Random routing based on variant weights
    WeightedRandom,
    /// Consistent routing per user (sticky sessions)
    StickySession,
    /// Progressive traffic shifting
    GradualRollout {
        initial_treatment_weight: f64,
        target_treatment_weight: f64,
        step_size: f64,
        step_duration_hours: u32,
    },
    /// Geographic-based routing
    Geographic {
        region_mapping: HashMap<String, String>,
    },
}

/// Model variant configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelVariant {
    pub name: String,
    pub model_path: String,
    pub weight: f64,
}

/// A/B test configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ABTestConfig {
    pub name: String,
    pub variants: Vec<ModelVariant>,
    pub traffic_strategy: TrafficStrategy,
    pub min_sample_size: usize,
    pub confidence_level: f64,
    pub duration_hours: u32,
}

impl ABTestConfig {
    pub fn validate(&self) -> Result<()> {
        if self.variants.is_empty() {
            return Err(anyhow!("At least one variant required"));
        }

        let total_weight: f64 = self.variants.iter().map(|v| v.weight).sum();
        if (total_weight - 1.0).abs() > 0.001 {
            return Err(anyhow!("Variant weights must sum to 1.0, got {}", total_weight));
        }

        if self.confidence_level <= 0.0 || self.confidence_level >= 1.0 {
            return Err(anyhow!("Confidence level must be between 0 and 1"));
        }

        if self.min_sample_size == 0 {
            return Err(anyhow!("Minimum sample size must be > 0"));
        }

        Ok(())
    }
}

/// Request metrics collected during prediction
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestMetrics {
    pub variant_name: String,
    pub user_id: String,
    pub latency_ms: f64,
    pub success: bool,
    pub quality_score: Option<f64>,
    pub user_feedback: Option<f64>,
    pub tokens_used: usize,
    pub cost: f64,
    pub timestamp: DateTime<Utc>,
}

/// Aggregated metrics for a variant
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VariantMetrics {
    pub variant_name: String,
    pub request_count: usize,
    pub latencies: Vec<f64>,
    pub success_count: usize,
    pub failure_count: usize,
    pub quality_scores: Vec<f64>,
    pub user_feedback: Vec<f64>,
    pub total_tokens: usize,
    pub total_cost: f64,
}

impl VariantMetrics {
    pub fn new(variant_name: String) -> Self {
        Self {
            variant_name,
            request_count: 0,
            latencies: Vec::new(),
            success_count: 0,
            failure_count: 0,
            quality_scores: Vec::new(),
            user_feedback: Vec::new(),
            total_tokens: 0,
            total_cost: 0.0,
        }
    }

    pub fn add_request(&mut self, metrics: &RequestMetrics) {
        self.request_count += 1;
        self.latencies.push(metrics.latency_ms);

        if metrics.success {
            self.success_count += 1;
        } else {
            self.failure_count += 1;
        }

        if let Some(score) = metrics.quality_score {
            self.quality_scores.push(score);
        }

        if let Some(feedback) = metrics.user_feedback {
            self.user_feedback.push(feedback);
        }

        self.total_tokens += metrics.tokens_used;
        self.total_cost += metrics.cost;
    }

    pub fn success_rate(&self) -> f64 {
        if self.request_count == 0 {
            return 0.0;
        }
        self.success_count as f64 / self.request_count as f64
    }

    pub fn mean_latency(&self) -> f64 {
        if self.latencies.is_empty() {
            return 0.0;
        }
        self.latencies.iter().sum::<f64>() / self.latencies.len() as f64
    }

    pub fn percentile_latency(&self, percentile: f64) -> f64 {
        if self.latencies.is_empty() {
            return 0.0;
        }
        let mut sorted = self.latencies.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let idx = (percentile * sorted.len() as f64).ceil() as usize;
        sorted[idx.min(sorted.len() - 1)]
    }

    pub fn mean_quality(&self) -> f64 {
        if self.quality_scores.is_empty() {
            return 0.0;
        }
        self.quality_scores.iter().sum::<f64>() / self.quality_scores.len() as f64
    }

    pub fn mean_feedback(&self) -> f64 {
        if self.user_feedback.is_empty() {
            return 0.0;
        }
        self.user_feedback.iter().sum::<f64>() / self.user_feedback.len() as f64
    }

    pub fn cost_per_request(&self) -> f64 {
        if self.request_count == 0 {
            return 0.0;
        }
        self.total_cost / self.request_count as f64
    }
}

/// Statistical test result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatisticalTest {
    pub test_name: String,
    pub statistic: f64,
    pub p_value: f64,
    pub significant: bool,
    pub confidence_level: f64,
}

/// Effect size measurement
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EffectSize {
    pub cohens_d: f64,
    pub interpretation: String,
}

impl EffectSize {
    pub fn new(cohens_d: f64) -> Self {
        let interpretation = if cohens_d.abs() < 0.2 {
            "negligible"
        } else if cohens_d.abs() < 0.5 {
            "small"
        } else if cohens_d.abs() < 0.8 {
            "medium"
        } else {
            "large"
        }
        .to_string();

        Self {
            cohens_d,
            interpretation,
        }
    }
}

/// Confidence interval
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceInterval {
    pub lower: f64,
    pub upper: f64,
    pub confidence_level: f64,
}

/// Statistical analyzer for comparing variants
pub struct StatisticalAnalyzer {
    pub confidence_level: f64,
}

impl StatisticalAnalyzer {
    pub fn new(confidence_level: f64) -> Self {
        Self { confidence_level }
    }

    /// Perform t-test for continuous metrics (e.g., latency)
    pub fn t_test(
        &self,
        control: &[f64],
        treatment: &[f64],
    ) -> Result<StatisticalTest> {
        if control.is_empty() || treatment.is_empty() {
            return Err(anyhow!("Cannot perform t-test on empty data"));
        }

        let n_control = control.len() as f64;
        let n_treatment = treatment.len() as f64;

        // Calculate means
        let mean_control = control.iter().sum::<f64>() / n_control;
        let mean_treatment = treatment.iter().sum::<f64>() / n_treatment;

        // Calculate variances
        let var_control = control
            .iter()
            .map(|x| (x - mean_control).powi(2))
            .sum::<f64>()
            / (n_control - 1.0);

        let var_treatment = treatment
            .iter()
            .map(|x| (x - mean_treatment).powi(2))
            .sum::<f64>()
            / (n_treatment - 1.0);

        // Welch's t-test (unequal variances)
        let se = ((var_control / n_control) + (var_treatment / n_treatment)).sqrt();
        let t_statistic = (mean_treatment - mean_control) / se;

        // Degrees of freedom (Welch-Satterthwaite equation)
        let df_numerator = ((var_control / n_control) + (var_treatment / n_treatment)).powi(2);
        let df_denominator = (var_control / n_control).powi(2) / (n_control - 1.0)
            + (var_treatment / n_treatment).powi(2) / (n_treatment - 1.0);
        let df = df_numerator / df_denominator;

        let t_dist = StudentsT::new(0.0, 1.0, df)
            .map_err(|e| anyhow!("Failed to create t-distribution: {}", e))?;

        // Two-tailed p-value
        let p_value = 2.0 * (1.0 - t_dist.cdf(t_statistic.abs()));

        let significant = p_value < (1.0 - self.confidence_level);

        Ok(StatisticalTest {
            test_name: "Welch's t-test".to_string(),
            statistic: t_statistic,
            p_value,
            significant,
            confidence_level: self.confidence_level,
        })
    }

    /// Perform chi-square test for categorical metrics (e.g., success rate)
    pub fn chi_square_test(
        &self,
        control_success: usize,
        control_total: usize,
        treatment_success: usize,
        treatment_total: usize,
    ) -> Result<StatisticalTest> {
        if control_total == 0 || treatment_total == 0 {
            return Err(anyhow!("Cannot perform chi-square test with zero total"));
        }

        let control_failure = control_total - control_success;
        let treatment_failure = treatment_total - treatment_success;

        let total = (control_total + treatment_total) as f64;
        let success_total = (control_success + treatment_success) as f64;
        let failure_total = (control_failure + treatment_failure) as f64;

        // Expected frequencies
        let expected_control_success = (control_total as f64) * success_total / total;
        let expected_control_failure = (control_total as f64) * failure_total / total;
        let expected_treatment_success = (treatment_total as f64) * success_total / total;
        let expected_treatment_failure = (treatment_total as f64) * failure_total / total;

        // Chi-square statistic
        let chi_square = ((control_success as f64 - expected_control_success).powi(2)
            / expected_control_success)
            + ((control_failure as f64 - expected_control_failure).powi(2)
                / expected_control_failure)
            + ((treatment_success as f64 - expected_treatment_success).powi(2)
                / expected_treatment_success)
            + ((treatment_failure as f64 - expected_treatment_failure).powi(2)
                / expected_treatment_failure);

        let df = 1.0; // (rows - 1) * (cols - 1) = (2 - 1) * (2 - 1)
        let chi_dist = ChiSquared::new(df)
            .map_err(|e| anyhow!("Failed to create chi-square distribution: {}", e))?;

        let p_value = 1.0 - chi_dist.cdf(chi_square);
        let significant = p_value < (1.0 - self.confidence_level);

        Ok(StatisticalTest {
            test_name: "Chi-square test".to_string(),
            statistic: chi_square,
            p_value,
            significant,
            confidence_level: self.confidence_level,
        })
    }

    /// Calculate Cohen's d effect size
    pub fn cohens_d(&self, control: &[f64], treatment: &[f64]) -> Result<EffectSize> {
        if control.is_empty() || treatment.is_empty() {
            return Err(anyhow!("Cannot calculate Cohen's d on empty data"));
        }

        let n_control = control.len() as f64;
        let n_treatment = treatment.len() as f64;

        // Calculate means
        let mean_control = control.iter().sum::<f64>() / n_control;
        let mean_treatment = treatment.iter().sum::<f64>() / n_treatment;

        // Calculate variances
        let var_control = control
            .iter()
            .map(|x| (x - mean_control).powi(2))
            .sum::<f64>()
            / (n_control - 1.0);

        let var_treatment = treatment
            .iter()
            .map(|x| (x - mean_treatment).powi(2))
            .sum::<f64>()
            / (n_treatment - 1.0);

        // Pooled standard deviation
        let pooled_var = ((n_control - 1.0) * var_control + (n_treatment - 1.0) * var_treatment)
            / (n_control + n_treatment - 2.0);
        let pooled_sd = pooled_var.sqrt();

        let cohens_d = (mean_treatment - mean_control) / pooled_sd;

        Ok(EffectSize::new(cohens_d))
    }

    /// Calculate confidence interval for mean difference
    pub fn confidence_interval_mean_diff(
        &self,
        control: &[f64],
        treatment: &[f64],
    ) -> Result<ConfidenceInterval> {
        if control.is_empty() || treatment.is_empty() {
            return Err(anyhow!("Cannot calculate confidence interval on empty data"));
        }

        let n_control = control.len() as f64;
        let n_treatment = treatment.len() as f64;

        // Calculate means
        let mean_control = control.iter().sum::<f64>() / n_control;
        let mean_treatment = treatment.iter().sum::<f64>() / n_treatment;

        // Calculate variances
        let var_control = control
            .iter()
            .map(|x| (x - mean_control).powi(2))
            .sum::<f64>()
            / (n_control - 1.0);

        let var_treatment = treatment
            .iter()
            .map(|x| (x - mean_treatment).powi(2))
            .sum::<f64>()
            / (n_treatment - 1.0);

        let se = ((var_control / n_control) + (var_treatment / n_treatment)).sqrt();
        let mean_diff = mean_treatment - mean_control;

        // Degrees of freedom
        let df_numerator = ((var_control / n_control) + (var_treatment / n_treatment)).powi(2);
        let df_denominator = (var_control / n_control).powi(2) / (n_control - 1.0)
            + (var_treatment / n_treatment).powi(2) / (n_treatment - 1.0);
        let df = df_numerator / df_denominator;

        let t_dist = StudentsT::new(0.0, 1.0, df)
            .map_err(|e| anyhow!("Failed to create t-distribution: {}", e))?;

        // Critical value for two-tailed test
        let alpha = 1.0 - self.confidence_level;
        let t_critical = t_dist.inverse_cdf(1.0 - alpha / 2.0);

        let margin_of_error = t_critical * se;

        Ok(ConfidenceInterval {
            lower: mean_diff - margin_of_error,
            upper: mean_diff + margin_of_error,
            confidence_level: self.confidence_level,
        })
    }
}

/// Experiment report with analysis and recommendations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentReport {
    pub experiment_name: String,
    pub start_time: DateTime<Utc>,
    pub end_time: DateTime<Utc>,
    pub duration_hours: f64,
    pub total_requests: usize,
    pub variants: HashMap<String, VariantSummary>,
    pub statistical_analysis: StatisticalAnalysis,
    pub promotion_decision: PromotionDecision,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VariantSummary {
    pub request_count: usize,
    pub latency_p50: f64,
    pub latency_p95: f64,
    pub latency_p99: f64,
    pub mean_latency: f64,
    pub success_rate: f64,
    pub mean_quality: f64,
    pub mean_feedback: f64,
    pub cost_per_request: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatisticalAnalysis {
    pub latency_t_test: StatisticalTest,
    pub success_rate_chi_square: StatisticalTest,
    pub effect_size: EffectSize,
    pub confidence_interval: ConfidenceInterval,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromotionDecision {
    pub should_promote: bool,
    pub winner: Option<String>,
    pub confidence: f64,
    pub reasoning: String,
}

/// A/B test runner
pub struct ABTestRunner {
    config: ABTestConfig,
    start_time: DateTime<Utc>,
    metrics: Arc<Mutex<HashMap<String, VariantMetrics>>>,
    user_assignments: Arc<Mutex<HashMap<String, String>>>,
    rng: Mutex<StdRng>,
}

impl ABTestRunner {
    pub fn new(config: ABTestConfig) -> Result<Self> {
        config.validate()?;

        let mut metrics = HashMap::new();
        for variant in &config.variants {
            metrics.insert(variant.name.clone(), VariantMetrics::new(variant.name.clone()));
        }

        Ok(Self {
            config,
            start_time: Utc::now(),
            metrics: Arc::new(Mutex::new(metrics)),
            user_assignments: Arc::new(Mutex::new(HashMap::new())),
            rng: Mutex::new(StdRng::from_entropy()),
        })
    }

    /// Route traffic to a variant based on strategy
    pub fn route_traffic(&self, user_id: &str) -> String {
        match &self.config.traffic_strategy {
            TrafficStrategy::WeightedRandom => self.weighted_random_routing(),
            TrafficStrategy::StickySession => self.sticky_session_routing(user_id),
            TrafficStrategy::GradualRollout { .. } => {
                self.gradual_rollout_routing(user_id)
            }
            TrafficStrategy::Geographic { region_mapping } => {
                self.geographic_routing(user_id, region_mapping)
            }
        }
    }

    fn weighted_random_routing(&self) -> String {
        let weights: Vec<f64> = self.config.variants.iter().map(|v| v.weight).collect();
        let dist = WeightedIndex::new(&weights).unwrap();
        let mut rng = self.rng.lock().unwrap();
        let idx = dist.sample(&mut *rng);
        self.config.variants[idx].name.clone()
    }

    fn sticky_session_routing(&self, user_id: &str) -> String {
        let mut assignments = self.user_assignments.lock().unwrap();

        if let Some(variant) = assignments.get(user_id) {
            return variant.clone();
        }

        // First time user - assign using weighted random
        let variant = self.weighted_random_routing();
        assignments.insert(user_id.to_string(), variant.clone());
        variant
    }

    fn gradual_rollout_routing(&self, user_id: &str) -> String {
        // For gradual rollout, use sticky sessions with current weights
        self.sticky_session_routing(user_id)
    }

    fn geographic_routing(&self, user_id: &str, _region_mapping: &HashMap<String, String>) -> String {
        // In a real implementation, extract region from user_id or context
        // For now, use sticky sessions as fallback
        self.sticky_session_routing(user_id)
    }

    /// Record metrics for a request
    pub fn record_metrics(&self, metrics: RequestMetrics) {
        let mut all_metrics = self.metrics.lock().unwrap();
        if let Some(variant_metrics) = all_metrics.get_mut(&metrics.variant_name) {
            variant_metrics.add_request(&metrics);
        }
    }

    /// Get current metrics snapshot
    pub fn get_metrics(&self) -> HashMap<String, VariantMetrics> {
        self.metrics.lock().unwrap().clone()
    }

    /// Analyze experiment results
    pub fn analyze(&self) -> Result<ExperimentReport> {
        let end_time = Utc::now();
        let duration = end_time.signed_duration_since(self.start_time);
        let duration_hours = duration.num_seconds() as f64 / 3600.0;

        let metrics = self.get_metrics();

        // Ensure we have at least 2 variants (control and treatment)
        if metrics.len() < 2 {
            return Err(anyhow!("Need at least 2 variants for analysis"));
        }

        // Get control (first variant) and best treatment
        let control_name = &self.config.variants[0].name;
        let control = metrics
            .get(control_name)
            .ok_or_else(|| anyhow!("Control variant not found"))?;

        // Find best treatment by success rate
        let treatment = metrics
            .iter()
            .filter(|(name, _)| *name != control_name)
            .max_by(|(_, a), (_, b)| {
                a.success_rate()
                    .partial_cmp(&b.success_rate())
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .map(|(_, m)| m)
            .ok_or_else(|| anyhow!("No treatment variant found"))?;

        let analyzer = StatisticalAnalyzer::new(self.config.confidence_level);

        // Perform statistical tests
        let latency_t_test = analyzer.t_test(&control.latencies, &treatment.latencies)?;
        let success_rate_chi_square = analyzer.chi_square_test(
            control.success_count,
            control.request_count,
            treatment.success_count,
            treatment.request_count,
        )?;
        let effect_size = analyzer.cohens_d(&control.latencies, &treatment.latencies)?;
        let confidence_interval =
            analyzer.confidence_interval_mean_diff(&control.latencies, &treatment.latencies)?;

        // Build variant summaries
        let mut variant_summaries = HashMap::new();
        let mut total_requests = 0;

        for (name, m) in &metrics {
            total_requests += m.request_count;
            variant_summaries.insert(
                name.clone(),
                VariantSummary {
                    request_count: m.request_count,
                    latency_p50: m.percentile_latency(0.5),
                    latency_p95: m.percentile_latency(0.95),
                    latency_p99: m.percentile_latency(0.99),
                    mean_latency: m.mean_latency(),
                    success_rate: m.success_rate(),
                    mean_quality: m.mean_quality(),
                    mean_feedback: m.mean_feedback(),
                    cost_per_request: m.cost_per_request(),
                },
            );
        }

        // Make promotion decision
        let promotion_decision = self.make_promotion_decision(
            control,
            treatment,
            &latency_t_test,
            &success_rate_chi_square,
            &effect_size,
        );

        Ok(ExperimentReport {
            experiment_name: self.config.name.clone(),
            start_time: self.start_time,
            end_time,
            duration_hours,
            total_requests,
            variants: variant_summaries,
            statistical_analysis: StatisticalAnalysis {
                latency_t_test,
                success_rate_chi_square,
                effect_size,
                confidence_interval,
            },
            promotion_decision,
        })
    }

    fn make_promotion_decision(
        &self,
        control: &VariantMetrics,
        treatment: &VariantMetrics,
        latency_test: &StatisticalTest,
        success_test: &StatisticalTest,
        effect_size: &EffectSize,
    ) -> PromotionDecision {
        let mut should_promote = true;
        let mut reasoning_parts = Vec::new();

        // Check minimum sample size
        if control.request_count < self.config.min_sample_size
            || treatment.request_count < self.config.min_sample_size
        {
            should_promote = false;
            reasoning_parts.push(format!(
                "Insufficient sample size (min: {}, control: {}, treatment: {})",
                self.config.min_sample_size, control.request_count, treatment.request_count
            ));
        }

        // Check for regressions
        let latency_regression = treatment.mean_latency() > control.mean_latency() * 1.05;
        let success_regression = treatment.success_rate() < control.success_rate() * 0.95;

        if latency_regression {
            should_promote = false;
            reasoning_parts.push(format!(
                "Latency regression detected (control: {:.2}ms, treatment: {:.2}ms)",
                control.mean_latency(),
                treatment.mean_latency()
            ));
        }

        if success_regression {
            should_promote = false;
            reasoning_parts.push(format!(
                "Success rate regression detected (control: {:.2}%, treatment: {:.2}%)",
                control.success_rate() * 100.0,
                treatment.success_rate() * 100.0
            ));
        }

        // Check statistical significance
        if !latency_test.significant && !success_test.significant {
            should_promote = false;
            reasoning_parts.push("No statistically significant improvement detected".to_string());
        } else {
            if latency_test.significant {
                reasoning_parts.push(format!(
                    "Latency improvement is statistically significant (p={:.4})",
                    latency_test.p_value
                ));
            }
            if success_test.significant {
                reasoning_parts.push(format!(
                    "Success rate improvement is statistically significant (p={:.4})",
                    success_test.p_value
                ));
            }
        }

        // Check effect size
        if effect_size.cohens_d.abs() < 0.2 {
            should_promote = false;
            reasoning_parts.push(format!(
                "Effect size too small (d={:.2}, interpretation: {})",
                effect_size.cohens_d, effect_size.interpretation
            ));
        } else {
            reasoning_parts.push(format!(
                "Effect size is {} (d={:.2})",
                effect_size.interpretation, effect_size.cohens_d
            ));
        }

        let winner = if should_promote {
            Some(treatment.variant_name.clone())
        } else {
            None
        };

        let confidence = if should_promote {
            self.config.confidence_level
        } else {
            1.0 - latency_test.p_value.max(success_test.p_value)
        };

        let reasoning = reasoning_parts.join(". ");

        PromotionDecision {
            should_promote,
            winner,
            confidence,
            reasoning,
        }
    }
}
