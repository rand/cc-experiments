use ab_testing::*;
use anyhow::{Context, Result};
use chrono::Utc;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use rand::Rng;
use serde_json;
use std::collections::HashMap;
use std::fs;
use std::iter::repeat;
use std::path::Path;
use std::time::{Duration, Instant};
use tokio::time::sleep;

/// Mock DSPy predictor for demonstration
struct MockPredictor {
    model_path: String,
    base_latency_ms: f64,
    base_success_rate: f64,
}

impl MockPredictor {
    fn new(model_path: &str, base_latency_ms: f64, base_success_rate: f64) -> Self {
        Self {
            model_path: model_path.to_string(),
            base_latency_ms,
            base_success_rate,
        }
    }

    async fn predict(&self, input: &str) -> Result<PredictionResult> {
        let start = Instant::now();

        // Simulate variable latency
        let mut rng = rand::thread_rng();
        let latency_variance = rng.gen_range(-10.0..20.0);
        let latency_ms = (self.base_latency_ms + latency_variance).max(5.0);

        // Simulate processing time
        sleep(Duration::from_millis(latency_ms as u64)).await;

        // Simulate success/failure
        let success = rng.gen::<f64>() < self.base_success_rate;

        // Simulate quality score
        let quality_score = if success {
            rng.gen_range(0.7..1.0)
        } else {
            rng.gen_range(0.0..0.5)
        };

        // Simulate token usage
        let tokens_used = (input.len() / 4) + rng.gen_range(50..150);

        let actual_latency = start.elapsed().as_secs_f64() * 1000.0;

        Ok(PredictionResult {
            output: if success {
                format!("Response from {}: {}", self.model_path, input)
            } else {
                "Error: Failed to generate response".to_string()
            },
            success,
            quality_score,
            tokens_used,
            latency_ms: actual_latency,
            cost: tokens_used as f64 * 0.00002, // $0.02 per 1K tokens
        })
    }
}

struct PredictionResult {
    output: String,
    success: bool,
    quality_score: f64,
    tokens_used: usize,
    latency_ms: f64,
    cost: f64,
}

/// Simulate user requests
struct RequestSimulator {
    user_count: usize,
    requests_per_user: usize,
}

impl RequestSimulator {
    fn new(user_count: usize, requests_per_user: usize) -> Self {
        Self {
            user_count,
            requests_per_user,
        }
    }

    fn generate_requests(&self) -> Vec<(String, String)> {
        let mut requests = Vec::new();
        let queries = vec![
            "What is the capital of France?",
            "Explain quantum computing",
            "Write a Python function to sort a list",
            "What are the benefits of exercise?",
            "How does photosynthesis work?",
            "Translate 'hello' to Spanish",
            "What is machine learning?",
            "Explain the theory of relativity",
            "How to bake a chocolate cake?",
            "What causes climate change?",
        ];

        for user_id in 0..self.user_count {
            for req_id in 0..self.requests_per_user {
                let query = queries[req_id % queries.len()];
                requests.push((format!("user_{}", user_id), query.to_string()));
            }
        }

        requests
    }
}

/// Load configuration from file
fn load_config(path: &Path) -> Result<ABTestConfig> {
    let content = fs::read_to_string(path)
        .context(format!("Failed to read config file: {:?}", path))?;
    let config: ABTestConfig = serde_json::from_str(&content)
        .context("Failed to parse config JSON")?;
    Ok(config)
}

/// Save experiment report to file
fn save_report(report: &ExperimentReport, path: &Path) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .context("Failed to serialize report")?;
    fs::write(path, json)
        .context(format!("Failed to write report to {:?}", path))?;
    Ok(())
}

/// Run A/B test experiment
async fn run_experiment(
    config: ABTestConfig,
    requests: Vec<(String, String)>,
) -> Result<ExperimentReport> {
    println!("Starting A/B test: {}", config.name);
    println!("Variants:");
    for variant in &config.variants {
        println!("  - {} (weight: {:.2})", variant.name, variant.weight);
    }
    println!("Traffic strategy: {:?}", config.traffic_strategy);
    println!("Total requests: {}", requests.len());
    println!();

    // Create runner
    let runner = ABTestRunner::new(config.clone())?;

    // Create mock predictors for each variant
    let mut predictors = HashMap::new();
    for (i, variant) in config.variants.iter().enumerate() {
        // Vary performance characteristics for demonstration
        let base_latency = 50.0 + (i as f64 * 10.0);
        let base_success_rate = 0.90 + (i as f64 * 0.03);
        predictors.insert(
            variant.name.clone(),
            MockPredictor::new(&variant.model_path, base_latency, base_success_rate),
        );
    }

    println!("Processing requests...");
    let total_requests = requests.len();
    let progress_interval = total_requests / 20;

    for (idx, (user_id, query)) in requests.iter().enumerate() {
        // Route traffic
        let variant_name = runner.route_traffic(user_id);

        // Get predictor
        let predictor = predictors
            .get(&variant_name)
            .expect("Predictor not found for variant");

        // Make prediction
        let result = predictor.predict(query).await?;

        // Simulate user feedback (70% chance of providing feedback)
        let mut rng = rand::thread_rng();
        let user_feedback = if rng.gen::<f64>() < 0.7 {
            Some(if result.success {
                rng.gen_range(3.0..5.0) // Good feedback for success
            } else {
                rng.gen_range(1.0..3.0) // Poor feedback for failure
            })
        } else {
            None
        };

        // Record metrics
        let metrics = RequestMetrics {
            variant_name: variant_name.clone(),
            user_id: user_id.clone(),
            latency_ms: result.latency_ms,
            success: result.success,
            quality_score: Some(result.quality_score),
            user_feedback,
            tokens_used: result.tokens_used,
            cost: result.cost,
            timestamp: Utc::now(),
        };

        runner.record_metrics(metrics);

        // Progress indicator
        if (idx + 1) % progress_interval == 0 {
            let progress = ((idx + 1) as f64 / total_requests as f64) * 100.0;
            println!("  Progress: {:.0}%", progress);
        }
    }

    println!("All requests processed.\n");

    // Analyze results
    println!("Analyzing results...");
    let report = runner.analyze()?;

    println!("Analysis complete.\n");
    Ok(report)
}

/// Print experiment report
fn print_report(report: &ExperimentReport) {
    println!("{}", "=".repeat(80));
    println!("EXPERIMENT REPORT: {}", report.experiment_name);
    println!("{}", "=".repeat(80));
    println!();

    println!("Duration: {:.2} hours", report.duration_hours);
    println!("Total requests: {}", report.total_requests);
    println!();

    println!("VARIANT PERFORMANCE");
    println!("{}", "-".repeat(80));
    println!(
        "{:<15} {:>10} {:>10} {:>10} {:>10} {:>10}",
        "Variant", "Requests", "Success%", "p50 (ms)", "p95 (ms)", "p99 (ms)"
    );
    println!("{}", "-".repeat(80));

    for (name, summary) in &report.variants {
        println!(
            "{:<15} {:>10} {:>9.2}% {:>10.2} {:>10.2} {:>10.2}",
            name,
            summary.request_count,
            summary.success_rate * 100.0,
            summary.latency_p50,
            summary.latency_p95,
            summary.latency_p99,
        );
    }
    println!();

    println!("QUALITY METRICS");
    println!("{}", "-".repeat(80));
    println!(
        "{:<15} {:>12} {:>12} {:>12}",
        "Variant", "Mean Latency", "Mean Quality", "User Rating"
    );
    println!("{}", "-".repeat(80));

    for (name, summary) in &report.variants {
        println!(
            "{:<15} {:>11.2}ms {:>12.2} {:>12.2}",
            name, summary.mean_latency, summary.mean_quality, summary.mean_feedback
        );
    }
    println!();

    println!("COST ANALYSIS");
    println!("{}", "-".repeat(80));
    println!("{:<15} {:>15}", "Variant", "Cost/Request");
    println!("{}", "-".repeat(80));

    for (name, summary) in &report.variants {
        println!(
            "{:<15} ${:>14.6}",
            name, summary.cost_per_request
        );
    }
    println!();

    println!("STATISTICAL ANALYSIS");
    println!("{}", "-".repeat(80));

    let analysis = &report.statistical_analysis;

    println!("Latency T-Test:");
    println!("  Test: {}", analysis.latency_t_test.test_name);
    println!("  t-statistic: {:.4}", analysis.latency_t_test.statistic);
    println!("  p-value: {:.6}", analysis.latency_t_test.p_value);
    println!(
        "  Significant: {}",
        if analysis.latency_t_test.significant {
            "YES"
        } else {
            "NO"
        }
    );
    println!();

    println!("Success Rate Chi-Square Test:");
    println!("  Test: {}", analysis.success_rate_chi_square.test_name);
    println!(
        "  χ² statistic: {:.4}",
        analysis.success_rate_chi_square.statistic
    );
    println!("  p-value: {:.6}", analysis.success_rate_chi_square.p_value);
    println!(
        "  Significant: {}",
        if analysis.success_rate_chi_square.significant {
            "YES"
        } else {
            "NO"
        }
    );
    println!();

    println!("Effect Size:");
    println!("  Cohen's d: {:.4}", analysis.effect_size.cohens_d);
    println!("  Interpretation: {}", analysis.effect_size.interpretation);
    println!();

    println!("Confidence Interval (Mean Difference):");
    println!(
        "  {:.0}% CI: [{:.4}, {:.4}]",
        analysis.confidence_interval.confidence_level * 100.0,
        analysis.confidence_interval.lower,
        analysis.confidence_interval.upper
    );
    println!();

    println!("{}", "=".repeat(80));
    println!("PROMOTION DECISION");
    println!("{}", "=".repeat(80));

    let decision = &report.promotion_decision;

    println!(
        "Should Promote: {}",
        if decision.should_promote {
            "YES"
        } else {
            "NO"
        }
    );

    if let Some(winner) = &decision.winner {
        println!("Winner: {}", winner);
    }

    println!("Confidence: {:.2}%", decision.confidence * 100.0);
    println!();
    println!("Reasoning:");
    println!("  {}", decision.reasoning);
    println!();

    println!("{}", "=".repeat(80));
}

/// Create default experiment config
fn create_default_config() -> ABTestConfig {
    ABTestConfig {
        name: "model-comparison-test".to_string(),
        variants: vec![
            ModelVariant {
                name: "control".to_string(),
                model_path: "models/production/v1".to_string(),
                weight: 0.5,
            },
            ModelVariant {
                name: "treatment".to_string(),
                model_path: "models/production/v2".to_string(),
                weight: 0.5,
            },
        ],
        traffic_strategy: TrafficStrategy::WeightedRandom,
        min_sample_size: 100,
        confidence_level: 0.95,
        duration_hours: 1,
    }
}

/// Create multi-variant test config
fn create_multi_variant_config() -> ABTestConfig {
    ABTestConfig {
        name: "multi-model-comparison".to_string(),
        variants: vec![
            ModelVariant {
                name: "baseline".to_string(),
                model_path: "models/baseline".to_string(),
                weight: 0.4,
            },
            ModelVariant {
                name: "optimized".to_string(),
                model_path: "models/optimized".to_string(),
                weight: 0.3,
            },
            ModelVariant {
                name: "experimental".to_string(),
                model_path: "models/experimental".to_string(),
                weight: 0.3,
            },
        ],
        traffic_strategy: TrafficStrategy::StickySession,
        min_sample_size: 200,
        confidence_level: 0.95,
        duration_hours: 2,
    }
}

/// Create gradual rollout config
fn create_gradual_rollout_config() -> ABTestConfig {
    ABTestConfig {
        name: "gradual-rollout-test".to_string(),
        variants: vec![
            ModelVariant {
                name: "stable".to_string(),
                model_path: "models/stable".to_string(),
                weight: 0.9,
            },
            ModelVariant {
                name: "canary".to_string(),
                model_path: "models/canary".to_string(),
                weight: 0.1,
            },
        ],
        traffic_strategy: TrafficStrategy::GradualRollout {
            initial_treatment_weight: 0.1,
            target_treatment_weight: 0.5,
            step_size: 0.1,
            step_duration_hours: 1,
        },
        min_sample_size: 50,
        confidence_level: 0.95,
        duration_hours: 1,
    }
}

/// Demo: Basic A/B test
async fn demo_basic_ab_test() -> Result<()> {
    println!("\n");
    println!("{}", "=".repeat(80));
    println!("DEMO 1: Basic A/B Test");
    println!("{}", "=".repeat(80));
    println!();

    let config = create_default_config();

    // Generate requests
    let simulator = RequestSimulator::new(50, 10); // 50 users, 10 requests each
    let requests = simulator.generate_requests();

    // Run experiment
    let report = run_experiment(config, requests).await?;

    // Print report
    print_report(&report);

    // Save report
    save_report(&report, Path::new("ab_test_report.json"))?;
    println!("Report saved to: ab_test_report.json");

    Ok(())
}

/// Demo: Multi-variant test
async fn demo_multi_variant_test() -> Result<()> {
    println!("\n");
    println!("{}", "=".repeat(80));
    println!("DEMO 2: Multi-Variant Test");
    println!("{}", "=".repeat(80));
    println!();

    let config = create_multi_variant_config();

    // Generate requests
    let simulator = RequestSimulator::new(60, 15); // 60 users, 15 requests each
    let requests = simulator.generate_requests();

    // Run experiment
    let report = run_experiment(config, requests).await?;

    // Print report
    print_report(&report);

    // Save report
    save_report(&report, Path::new("multi_variant_report.json"))?;
    println!("Report saved to: multi_variant_report.json");

    Ok(())
}

/// Demo: Gradual rollout
async fn demo_gradual_rollout() -> Result<()> {
    println!("\n");
    println!("{}", "=".repeat(80));
    println!("DEMO 3: Gradual Rollout");
    println!("{}", "=".repeat(80));
    println!();

    let config = create_gradual_rollout_config();

    // Generate requests
    let simulator = RequestSimulator::new(30, 10); // 30 users, 10 requests each
    let requests = simulator.generate_requests();

    // Run experiment
    let report = run_experiment(config, requests).await?;

    // Print report
    print_report(&report);

    // Save report
    save_report(&report, Path::new("gradual_rollout_report.json"))?;
    println!("Report saved to: gradual_rollout_report.json");

    Ok(())
}

/// Demo: Statistical power analysis
async fn demo_statistical_analysis() -> Result<()> {
    println!("\n");
    println!("{}", "=".repeat(80));
    println!("DEMO 4: Statistical Analysis Deep Dive");
    println!("{}", "=".repeat(80));
    println!();

    println!("Demonstrating statistical significance with varying sample sizes...\n");

    for sample_size in [50, 100, 200, 500, 1000] {
        println!("Sample size: {} per variant", sample_size);

        let config = ABTestConfig {
            name: format!("statistical-test-n{}", sample_size),
            variants: vec![
                ModelVariant {
                    name: "control".to_string(),
                    model_path: "models/control".to_string(),
                    weight: 0.5,
                },
                ModelVariant {
                    name: "treatment".to_string(),
                    model_path: "models/treatment".to_string(),
                    weight: 0.5,
                },
            ],
            traffic_strategy: TrafficStrategy::WeightedRandom,
            min_sample_size: sample_size,
            confidence_level: 0.95,
            duration_hours: 1,
        };

        let simulator = RequestSimulator::new(sample_size, 2);
        let requests = simulator.generate_requests();

        let report = run_experiment(config, requests).await?;

        println!(
            "  Latency p-value: {:.6} (significant: {})",
            report.statistical_analysis.latency_t_test.p_value,
            report.statistical_analysis.latency_t_test.significant
        );
        println!(
            "  Success rate p-value: {:.6} (significant: {})",
            report.statistical_analysis.success_rate_chi_square.p_value,
            report.statistical_analysis.success_rate_chi_square.significant
        );
        println!(
            "  Effect size: {:.4} ({})",
            report.statistical_analysis.effect_size.cohens_d,
            report.statistical_analysis.effect_size.interpretation
        );
        println!(
            "  Promotion: {}",
            if report.promotion_decision.should_promote {
                "YES"
            } else {
                "NO"
            }
        );
        println!();
    }

    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    println!("DSPy A/B Testing Infrastructure Demo");
    println!("=====================================");

    // Check for config file
    let config_path = Path::new("experiment_config.json");
    if config_path.exists() {
        println!("Loading config from: {:?}", config_path);
        let config = load_config(config_path)?;

        let simulator = RequestSimulator::new(100, 10);
        let requests = simulator.generate_requests();

        let report = run_experiment(config, requests).await?;
        print_report(&report);

        save_report(&report, Path::new("experiment_report.json"))?;
        println!("Report saved to: experiment_report.json");
    } else {
        println!("No config file found. Running demo scenarios...\n");

        // Run all demos
        demo_basic_ab_test().await?;
        demo_multi_variant_test().await?;
        demo_gradual_rollout().await?;
        demo_statistical_analysis().await?;

        println!("\n");
        println!("{}", "=".repeat(80));
        println!("All demos completed!");
        println!("{}", "=".repeat(80));
        println!();
        println!("To run a custom experiment, create experiment_config.json and run again.");
    }

    Ok(())
}
