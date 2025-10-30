//! Evaluation framework CLI
//!
//! Command-line interface for evaluating DSPy models with multiple metrics,
//! comparing models, and generating detailed reports.

use anyhow::{Context, Result};
use evaluation_framework::{
    Accuracy, BLEU, ComparisonReport, EvaluationHarness, EvaluationResult,
    ExactMatch, F1Score, Metric, ROUGE, TestExample, TestSet,
};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

/// Configuration for evaluation run
#[derive(Debug, Clone)]
struct EvalConfig {
    test_set_path: PathBuf,
    models: Vec<String>,
    metrics: Vec<String>,
    batch_size: usize,
    compare_models: bool,
    output_dir: PathBuf,
    python_module: String,
    python_class: String,
}

impl Default for EvalConfig {
    fn default() -> Self {
        Self {
            test_set_path: PathBuf::from("data/testset.json"),
            models: vec!["baseline".to_string()],
            metrics: vec!["accuracy".to_string()],
            batch_size: 10,
            compare_models: false,
            output_dir: PathBuf::from("results"),
            python_module: "dspy".to_string(),
            python_class: "Predict".to_string(),
        }
    }
}

/// DSPy model wrapper for evaluation
struct DSPyModel {
    predictor: Py<PyAny>,
}

impl DSPyModel {
    /// Load DSPy model from Python module
    fn load(
        module_name: &str,
        class_name: &str,
        model_path: Option<&str>,
    ) -> Result<Self> {
        Python::with_gil(|py| {
            // Import module
            let py_module = PyModule::import_bound(py, module_name)
                .context("Failed to import Python module")?;

            // Get predictor class
            let predictor_class = py_module.getattr(class_name)
                .context("Failed to get predictor class")?;

            // Create predictor instance
            let predictor = if let Some(path) = model_path {
                // Load from saved model
                let kwargs = PyDict::new_bound(py);
                kwargs.set_item("model_path", path)?;
                predictor_class.call((), Some(&kwargs))?
            } else {
                // Create new predictor
                predictor_class.call0()?
            };

            Ok(Self {
                predictor: predictor.unbind(),
            })
        })
    }

    /// Predict for single example
    fn predict(&self, input: &str) -> Result<String> {
        Python::with_gil(|py| {
            let predictor = self.predictor.bind(py);

            // Call predictor
            let result = predictor.call_method1("__call__", (input,))
                .context("Failed to call predictor")?;

            // Extract output
            let output = if let Ok(dict) = result.downcast::<PyDict>() {
                // If result is dict, try to get 'answer' or 'output' field
                if let Some(answer) = dict.get_item("answer")? {
                    answer.extract::<String>()?
                } else if let Some(output) = dict.get_item("output")? {
                    output.extract::<String>()?
                } else {
                    anyhow::bail!("No 'answer' or 'output' field in result");
                }
            } else {
                // Otherwise, convert to string
                result.str()?.extract::<String>()?
            };

            Ok(output)
        })
    }

    /// Batch predict for multiple examples
    fn predict_batch(&self, inputs: &[String]) -> Result<Vec<String>> {
        let mut outputs = Vec::new();
        for input in inputs {
            let output = self.predict(input)?;
            outputs.push(output);
        }
        Ok(outputs)
    }
}

/// Create metric from string name
fn create_metric(name: &str) -> Result<Box<dyn Metric>> {
    match name.to_lowercase().as_str() {
        "accuracy" => Ok(Box::new(Accuracy)),
        "exact_match" | "exact-match" => Ok(Box::new(ExactMatch::new(true))),
        "exact_match_ci" | "exact-match-ci" => Ok(Box::new(ExactMatch::new(false))),
        "f1" | "f1_score" | "f1-score" => Ok(Box::new(F1Score)),
        "bleu" => Ok(Box::new(BLEU::new(4))),
        "bleu-1" => Ok(Box::new(BLEU::new(1))),
        "bleu-2" => Ok(Box::new(BLEU::new(2))),
        "bleu-3" => Ok(Box::new(BLEU::new(3))),
        "bleu-4" => Ok(Box::new(BLEU::new(4))),
        "rouge" | "rouge-l" => Ok(Box::new(ROUGE::new("rouge-l"))),
        _ => anyhow::bail!("Unknown metric: {}", name),
    }
}

/// Evaluate single model with single metric
async fn evaluate_model(
    model: &DSPyModel,
    model_name: &str,
    test_set: &TestSet,
    metric: Box<dyn Metric>,
    batch_size: usize,
) -> Result<EvaluationResult> {
    let harness = EvaluationHarness::new(metric);

    // Use batch evaluation for efficiency
    let result = harness.evaluate_batch(
        test_set,
        model_name,
        batch_size,
        |examples| {
            let inputs: Vec<String> = examples.iter()
                .map(|ex| ex.input.clone())
                .collect();

            match model.predict_batch(&inputs) {
                Ok(outputs) => outputs,
                Err(e) => {
                    eprintln!("Batch prediction error: {}", e);
                    vec!["".to_string(); inputs.len()]
                }
            }
        },
    ).await?;

    Ok(result)
}

/// Evaluate single model with multiple metrics
async fn evaluate_model_multi_metric(
    model: &DSPyModel,
    model_name: &str,
    test_set: &TestSet,
    metric_names: &[String],
    batch_size: usize,
    output_dir: &PathBuf,
) -> Result<Vec<EvaluationResult>> {
    let mut results = Vec::new();

    println!("\nEvaluating model: {}", model_name);
    println!("Test set size: {}", test_set.len());
    println!("Metrics: {}", metric_names.join(", "));
    println!("Batch size: {}\n", batch_size);

    for metric_name in metric_names {
        println!("Computing {}...", metric_name);

        let metric = create_metric(metric_name)?;
        let result = evaluate_model(
            model,
            model_name,
            test_set,
            metric,
            batch_size,
        ).await?;

        println!("  Mean: {:.4}", result.mean);
        println!("  Std Dev: {:.4}", result.std_dev);

        // Save individual result
        let result_path = output_dir.join(format!(
            "{}_{}.json",
            model_name,
            metric_name
        ));
        result.save_json(&result_path)?;
        println!("  Saved to: {}\n", result_path.display());

        results.push(result);
    }

    Ok(results)
}

/// Compare multiple models
async fn compare_models(
    test_set: &TestSet,
    model_names: &[String],
    metric_names: &[String],
    batch_size: usize,
    output_dir: &PathBuf,
    python_module: &str,
    python_class: &str,
) -> Result<()> {
    println!("\n=== Model Comparison ===\n");

    for metric_name in metric_names {
        println!("Metric: {}", metric_name);
        println!("{}", "=".repeat(40));

        let mut all_results = Vec::new();

        // Evaluate each model
        for model_name in model_names {
            println!("\nEvaluating: {}", model_name);

            // Load model
            let model_path = format!("models/{}.pkl", model_name);
            let model = DSPyModel::load(
                python_module,
                python_class,
                Some(&model_path),
            )?;

            // Evaluate
            let metric = create_metric(metric_name)?;
            let result = evaluate_model(
                &model,
                model_name,
                test_set,
                metric,
                batch_size,
            ).await?;

            println!("  Mean: {:.4} ± {:.4}", result.mean, result.std_dev);

            all_results.push(result);
        }

        // Generate comparison report
        let comparison = ComparisonReport::compare(all_results, 0.05)?;

        println!("\n");
        comparison.print_summary();

        // Save comparison
        let comparison_path = output_dir.join(format!(
            "comparison_{}.json",
            metric_name
        ));
        comparison.save_json(&comparison_path)?;
        println!("\nComparison saved to: {}\n", comparison_path.display());
    }

    Ok(())
}

/// Run single model evaluation
async fn run_single_evaluation(config: &EvalConfig) -> Result<()> {
    println!("Loading test set from: {}", config.test_set_path.display());
    let test_set = TestSet::from_json(&config.test_set_path)?;
    println!("Loaded {} examples", test_set.len());

    // Create output directory
    fs::create_dir_all(&config.output_dir)
        .context("Failed to create output directory")?;

    for model_name in &config.models {
        println!("\n{}", "=".repeat(60));
        println!("Model: {}", model_name);
        println!("{}", "=".repeat(60));

        // Load model
        let model_path = format!("models/{}.pkl", model_name);
        let model = DSPyModel::load(
            &config.python_module,
            &config.python_class,
            Some(&model_path),
        )?;

        // Evaluate with all metrics
        let results = evaluate_model_multi_metric(
            &model,
            model_name,
            &test_set,
            &config.metrics,
            config.batch_size,
            &config.output_dir,
        ).await?;

        // Print summary for each metric
        for result in results {
            println!("\n{}", "-".repeat(40));
            result.print_summary();
        }
    }

    Ok(())
}

/// Run model comparison
async fn run_comparison(config: &EvalConfig) -> Result<()> {
    if config.models.len() < 2 {
        anyhow::bail!("Need at least 2 models for comparison");
    }

    println!("Loading test set from: {}", config.test_set_path.display());
    let test_set = TestSet::from_json(&config.test_set_path)?;
    println!("Loaded {} examples", test_set.len());

    // Create output directory
    fs::create_dir_all(&config.output_dir)
        .context("Failed to create output directory")?;

    compare_models(
        &test_set,
        &config.models,
        &config.metrics,
        config.batch_size,
        &config.output_dir,
        &config.python_module,
        &config.python_class,
    ).await?;

    Ok(())
}

/// Interactive demo with mock model
async fn run_demo() -> Result<()> {
    println!("=== Evaluation Framework Demo ===\n");

    // Create demo test set
    let mut test_set = TestSet::new();

    let examples = vec![
        ("What is 2+2?", "4"),
        ("What is the capital of France?", "Paris"),
        ("What color is the sky?", "Blue"),
        ("How many days in a week?", "7"),
        ("What is H2O?", "Water"),
    ];

    for (input, output) in examples {
        test_set.add_example(TestExample {
            input: input.to_string(),
            expected_output: output.to_string(),
            metadata: HashMap::new(),
        });
    }

    println!("Created test set with {} examples\n", test_set.len());

    // Mock predictor (simulates model with 80% accuracy)
    let mut predictor = |ex: &TestExample| {
        // Simulate some correct and some incorrect predictions
        match ex.input.as_str() {
            "What is 2+2?" => "4".to_string(),
            "What is the capital of France?" => "Paris".to_string(),
            "What color is the sky?" => "Green".to_string(), // Wrong!
            "How many days in a week?" => "7".to_string(),
            "What is H2O?" => "Water".to_string(),
            _ => "Unknown".to_string(),
        }
    };

    // Evaluate with multiple metrics
    let metrics: Vec<(&str, Box<dyn Metric>)> = vec![
        ("Accuracy", Box::new(Accuracy)),
        ("F1 Score", Box::new(F1Score)),
        ("BLEU-4", Box::new(BLEU::new(4))),
    ];

    for (metric_name, metric) in metrics {
        println!("{}", "=".repeat(40));
        println!("Metric: {}", metric_name);
        println!("{}", "=".repeat(40));

        let harness = EvaluationHarness::new(metric);
        let result = harness.evaluate(
            &test_set,
            "demo_model",
            &mut predictor,
        ).await?;

        result.print_summary();
        println!();
    }

    // Demonstrate comparison
    println!("\n{}", "=".repeat(60));
    println!("Model Comparison Demo");
    println!("{}", "=".repeat(60));

    // Create two mock results
    let baseline_scores = vec![0.6, 0.7, 0.8, 0.7, 0.9];
    let optimized_scores = vec![0.8, 0.85, 0.9, 0.88, 0.95];

    let baseline = EvaluationResult::from_scores(
        "baseline".to_string(),
        "accuracy".to_string(),
        baseline_scores,
    );

    let optimized = EvaluationResult::from_scores(
        "optimized".to_string(),
        "accuracy".to_string(),
        optimized_scores,
    );

    let comparison = ComparisonReport::compare(
        vec![baseline, optimized],
        0.05,
    )?;

    comparison.print_summary();

    Ok(())
}

/// Parse command line arguments (simplified)
fn parse_args() -> Result<EvalConfig> {
    let args: Vec<String> = std::env::args().collect();

    if args.len() == 1 {
        // No arguments, run demo
        return Ok(EvalConfig::default());
    }

    let mut config = EvalConfig::default();

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--test-set" => {
                config.test_set_path = PathBuf::from(&args[i + 1]);
                i += 2;
            }
            "--models" => {
                config.models = args[i + 1].split(',').map(|s| s.to_string()).collect();
                i += 2;
            }
            "--metrics" => {
                config.metrics = args[i + 1].split(',').map(|s| s.to_string()).collect();
                i += 2;
            }
            "--batch-size" => {
                config.batch_size = args[i + 1].parse()?;
                i += 2;
            }
            "--compare" => {
                config.compare_models = true;
                i += 1;
            }
            "--output-dir" => {
                config.output_dir = PathBuf::from(&args[i + 1]);
                i += 2;
            }
            "--python-module" => {
                config.python_module = args[i + 1].clone();
                i += 2;
            }
            "--python-class" => {
                config.python_class = args[i + 1].clone();
                i += 2;
            }
            "--demo" => {
                // Special flag for demo mode
                config.models.clear();
                i += 1;
            }
            "--help" => {
                print_help();
                std::process::exit(0);
            }
            _ => {
                eprintln!("Unknown argument: {}", args[i]);
                print_help();
                std::process::exit(1);
            }
        }
    }

    Ok(config)
}

/// Print usage help
fn print_help() {
    println!("Evaluation Framework CLI");
    println!("\nUsage:");
    println!("  eval [OPTIONS]");
    println!("\nOptions:");
    println!("  --test-set PATH          Path to test set JSON file");
    println!("  --models MODEL1,MODEL2   Comma-separated model names");
    println!("  --metrics M1,M2          Comma-separated metric names");
    println!("  --batch-size N           Batch size for evaluation (default: 10)");
    println!("  --compare                Compare multiple models");
    println!("  --output-dir PATH        Output directory (default: results)");
    println!("  --python-module NAME     Python module name (default: dspy)");
    println!("  --python-class NAME      Python class name (default: Predict)");
    println!("  --demo                   Run interactive demo");
    println!("  --help                   Print this help");
    println!("\nMetrics:");
    println!("  accuracy, exact-match, f1-score, bleu, rouge");
    println!("\nExamples:");
    println!("  # Run demo");
    println!("  eval --demo");
    println!();
    println!("  # Single model evaluation");
    println!("  eval --test-set data/testset.json --models baseline --metrics accuracy,f1");
    println!();
    println!("  # Compare multiple models");
    println!("  eval --test-set data/testset.json --models baseline,optimized --metrics accuracy --compare");
}

#[tokio::main]
async fn main() -> Result<()> {
    let config = parse_args()?;

    if config.models.is_empty() {
        // Run demo
        run_demo().await?;
    } else if config.compare_models {
        // Run comparison
        run_comparison(&config).await?;
    } else {
        // Run single evaluation
        run_single_evaluation(&config).await?;
    }

    Ok(())
}
