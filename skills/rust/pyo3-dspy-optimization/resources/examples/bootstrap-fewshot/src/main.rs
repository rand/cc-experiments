//! BootstrapFewShot Optimization CLI
//!
//! Command-line interface for running BootstrapFewShot optimization workflows.
//! Demonstrates complete workflow: data loading, module creation, optimization,
//! evaluation, and model persistence.

use anyhow::{Context, Result};
use bootstrap_fewshot::{
    create_accuracy_metric, run_bootstrap_fewshot, save_compiled_model, ModelMetadata,
    OptimizationConfig, TrainingDataset, TrainingExample,
};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};
use std::path::{Path, PathBuf};
use std::time::Instant;

// ============================================================================
// Configuration
// ============================================================================

/// CLI configuration
struct Config {
    train_data_path: PathBuf,
    output_dir: PathBuf,
    max_bootstrapped_demos: usize,
    max_labeled_demos: usize,
    metric_threshold: f64,
    base_model: String,
    evaluate_baseline: bool,
    verbose: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            train_data_path: PathBuf::from("data/trainset.json"),
            output_dir: PathBuf::from("./output"),
            max_bootstrapped_demos: 4,
            max_labeled_demos: 8,
            metric_threshold: 0.7,
            base_model: "gpt-3.5-turbo".to_string(),
            evaluate_baseline: true,
            verbose: true,
        }
    }
}

impl Config {
    /// Parse configuration from command-line arguments or use defaults
    fn from_args() -> Self {
        // In production, would use clap or similar for proper arg parsing
        // For this example, using defaults
        Self::default()
    }
}

// ============================================================================
// DSPy Module Creation
// ============================================================================

/// Create a simple QA module for optimization
fn create_qa_module(py: Python) -> PyResult<Py<PyAny>> {
    // Define a simple ChainOfThought QA module
    let code = r#"
import dspy

class SimpleQA(dspy.Module):
    """Simple question-answering module using ChainOfThought"""

    def __init__(self):
        super().__init__()
        self.generate_answer = dspy.ChainOfThought("question -> answer")

    def forward(self, question):
        """Process question and generate answer"""
        result = self.generate_answer(question=question)
        return result
"#;

    py.run_bound(code, None, None)?;

    // Instantiate the module
    let locals = py.eval_bound("locals()", None, None)?;
    let qa_class = locals.get_item("SimpleQA")?;
    let qa_module = qa_class.call0()?;

    Ok(qa_module.unbind())
}

/// Create a more complex multi-hop QA module
#[allow(dead_code)]
fn create_multihop_qa_module(py: Python) -> PyResult<Py<PyAny>> {
    let code = r#"
import dspy

class MultiHopQA(dspy.Module):
    """Multi-hop reasoning QA module"""

    def __init__(self):
        super().__init__()
        self.generate_query = dspy.ChainOfThought("question -> search_query")
        self.generate_answer = dspy.ChainOfThought("question, context -> answer")

    def forward(self, question):
        """Multi-step reasoning to answer question"""
        # Generate search query
        query_result = self.generate_query(question=question)
        search_query = query_result.search_query

        # In real scenario, would retrieve context here
        # For demo, using question as context
        context = f"Context for: {search_query}"

        # Generate final answer
        answer_result = self.generate_answer(
            question=question,
            context=context
        )

        return answer_result
"#;

    py.run_bound(code, None, None)?;

    let locals = py.eval_bound("locals()", None, None)?;
    let qa_class = locals.get_item("MultiHopQA")?;
    let qa_module = qa_class.call0()?;

    Ok(qa_module.unbind())
}

// ============================================================================
// DSPy Configuration
// ============================================================================

/// Configure DSPy with language model
fn configure_dspy(py: Python, model_name: &str) -> PyResult<()> {
    let dspy = PyModule::import_bound(py, "dspy")?;

    // Check for API key
    let has_api_key = std::env::var("OPENAI_API_KEY").is_ok();

    if !has_api_key {
        eprintln!("Warning: OPENAI_API_KEY not set - using mock LM for demo");

        // Configure with DummyLM for testing without API key
        let dummy_lm = dspy.call_method1("LM", ((model_name, true),))?;
        dspy.call_method1("configure", ((),))?
            .set_item("lm", dummy_lm)?;
    } else {
        // Configure with OpenAI
        let kwargs = PyDict::new_bound(py);
        kwargs.set_item("model", model_name)?;

        let openai_lm = dspy.call_method("OpenAI", (), Some(&kwargs))?;

        let config_kwargs = PyDict::new_bound(py);
        config_kwargs.set_item("lm", openai_lm)?;

        dspy.call_method("configure", (), Some(&config_kwargs))?;

        println!("Configured DSPy with {}", model_name);
    }

    Ok(())
}

// ============================================================================
// Evaluation
// ============================================================================

/// Evaluation result for a single example
#[derive(Debug)]
struct ExampleEvaluation {
    question: String,
    expected: String,
    predicted: String,
    correct: bool,
    latency_ms: f64,
}

/// Aggregate evaluation results
#[derive(Debug)]
struct EvaluationResults {
    total: usize,
    correct: usize,
    accuracy: f64,
    avg_latency_ms: f64,
    examples: Vec<ExampleEvaluation>,
}

impl EvaluationResults {
    /// Print evaluation summary
    fn print_summary(&self) {
        println!("\n=== Evaluation Results ===");
        println!("Total examples: {}", self.total);
        println!("Correct: {}", self.correct);
        println!("Accuracy: {:.2}%", self.accuracy * 100.0);
        println!("Avg latency: {:.2}ms", self.avg_latency_ms);

        // Print some example predictions
        println!("\nSample predictions:");
        for (i, ex) in self.examples.iter().take(3).enumerate() {
            let status = if ex.correct { "✓" } else { "✗" };
            println!("\n  [{}] {}", i + 1, status);
            println!("    Q: {}", ex.question);
            println!("    Expected: {}", ex.expected);
            println!("    Predicted: {}", ex.predicted);
            println!("    Latency: {:.2}ms", ex.latency_ms);
        }
    }

    /// Save results to JSON file
    fn save<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let json = serde_json::json!({
            "total": self.total,
            "correct": self.correct,
            "accuracy": self.accuracy,
            "avg_latency_ms": self.avg_latency_ms,
            "examples": self.examples.iter().map(|ex| {
                serde_json::json!({
                    "question": ex.question,
                    "expected": ex.expected,
                    "predicted": ex.predicted,
                    "correct": ex.correct,
                    "latency_ms": ex.latency_ms,
                })
            }).collect::<Vec<_>>()
        });

        let json_str = serde_json::to_string_pretty(&json)?;
        std::fs::write(path.as_ref(), json_str)?;

        Ok(())
    }
}

/// Evaluate a model on test examples
fn evaluate_model(
    _py: Python,
    module: &Bound<'_, PyAny>,
    test_set: &[TrainingExample],
    _metric_fn: &Bound<'_, PyAny>,
) -> PyResult<EvaluationResults> {
    let mut results = Vec::new();
    let mut correct_count = 0;
    let mut total_latency = 0.0;

    println!("\nEvaluating model on {} examples...", test_set.len());

    for (i, example) in test_set.iter().enumerate() {
        let start = Instant::now();

        // Run prediction
        let prediction = module.call_method1("forward", (&example.question,))?;

        let latency_ms = start.elapsed().as_secs_f64() * 1000.0;

        // Extract answer from prediction
        let predicted: String = if let Ok(answer) = prediction.getattr("answer") {
            answer.extract()?
        } else {
            prediction.to_string()
        };

        // Check correctness using metric
        let is_correct = predicted.to_lowercase().trim() == example.answer.to_lowercase().trim();

        if is_correct {
            correct_count += 1;
        }

        total_latency += latency_ms;

        results.push(ExampleEvaluation {
            question: example.question.clone(),
            expected: example.answer.clone(),
            predicted,
            correct: is_correct,
            latency_ms,
        });

        // Progress indicator
        if (i + 1) % 10 == 0 {
            println!("  Processed {}/{} examples", i + 1, test_set.len());
        }
    }

    let accuracy = correct_count as f64 / test_set.len() as f64;
    let avg_latency = total_latency / test_set.len() as f64;

    Ok(EvaluationResults {
        total: test_set.len(),
        correct: correct_count,
        accuracy,
        avg_latency_ms: avg_latency,
        examples: results,
    })
}

// Note: Progress callback functionality moved to lib.rs

// ============================================================================
// Main Workflow
// ============================================================================

fn main() -> Result<()> {
    println!("BootstrapFewShot Optimization Example");
    println!("======================================\n");

    // Load configuration
    let config = Config::from_args();

    // Run workflow
    Python::with_gil(|py| {
        // Step 1: Configure DSPy
        println!("[1/7] Configuring DSPy...");
        configure_dspy(py, &config.base_model)
            .context("Failed to configure DSPy")?;

        // Step 2: Load training data
        println!("[2/7] Loading training data...");
        let dataset = TrainingDataset::from_file(&config.train_data_path)
            .context("Failed to load training data")?;

        println!("  Loaded {} examples", dataset.len());

        // Split into train/validation
        let (train_dataset, val_dataset) = dataset.split(0.8);
        println!(
            "  Split: {} train, {} validation",
            train_dataset.len(),
            val_dataset.len()
        );

        // Step 3: Create module
        println!("[3/7] Creating QA module...");
        let module = create_qa_module(py).context("Failed to create QA module")?;

        // Step 4: Evaluate baseline (optional)
        let baseline_results = if config.evaluate_baseline {
            println!("[4/7] Evaluating baseline model...");
            let metric = create_accuracy_metric(py)?;
            let results = evaluate_model(
                py,
                &module.bind(py),
                &val_dataset.examples,
                &metric.bind(py),
            )?;
            results.print_summary();
            Some(results)
        } else {
            println!("[4/7] Skipping baseline evaluation");
            None
        };

        // Step 5: Run optimization
        println!("\n[5/7] Running BootstrapFewShot optimization...");

        let opt_config = OptimizationConfig::new()
            .with_max_bootstrapped_demos(config.max_bootstrapped_demos)
            .with_max_labeled_demos(config.max_labeled_demos)
            .with_metric_threshold(config.metric_threshold)
            .with_verbose(config.verbose);

        let metric = create_accuracy_metric(py)?;

        let opt_result = run_bootstrap_fewshot(
            py,
            &module.bind(py),
            train_dataset.examples,
            &metric.bind(py),
            opt_config.clone(),
        )
        .context("Optimization failed")?;

        println!("\nOptimization succeeded!");
        println!("  Score: {:.2}%", opt_result.score_percent());
        println!("  Duration: {:.2}s", opt_result.duration_secs());
        println!("  Demonstrations: {}", opt_result.num_demonstrations);

        // Step 6: Evaluate optimized model
        println!("\n[6/7] Evaluating optimized model...");
        let optimized_results = evaluate_model(
            py,
            &opt_result.compiled_model.bind(py),
            &val_dataset.examples,
            &metric.bind(py),
        )?;
        optimized_results.print_summary();

        // Compare results
        if let Some(baseline) = baseline_results {
            let improvement = (optimized_results.accuracy - baseline.accuracy) * 100.0;
            println!("\n=== Comparison ===");
            println!("Baseline accuracy:  {:.2}%", baseline.accuracy * 100.0);
            println!("Optimized accuracy: {:.2}%", optimized_results.accuracy * 100.0);
            println!("Improvement:        {:+.2}%", improvement);
        }

        // Step 7: Save model
        println!("\n[7/7] Saving compiled model...");

        let metadata = ModelMetadata::from_optimization(
            "bootstrap-fewshot-qa".to_string(),
            "1.0.0".to_string(),
            config.base_model.clone(),
            &opt_result,
            &opt_config,
        );

        save_compiled_model(
            py,
            &opt_result.compiled_model.bind(py),
            metadata,
            &config.output_dir,
        )
        .context("Failed to save model")?;

        // Save evaluation results
        let eval_path = config.output_dir.join("evaluation.json");
        optimized_results
            .save(&eval_path)
            .context("Failed to save evaluation results")?;
        println!("  Evaluation results: {}", eval_path.display());

        println!("\n✓ Workflow complete!");

        Ok(())
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_defaults() {
        let config = Config::default();
        assert_eq!(config.train_data_path, PathBuf::from("data/trainset.json"));
        assert_eq!(config.max_bootstrapped_demos, 4);
        assert_eq!(config.max_labeled_demos, 8);
        assert_eq!(config.base_model, "gpt-3.5-turbo");
    }

    #[test]
    fn test_evaluation_results_accuracy() {
        let results = EvaluationResults {
            total: 10,
            correct: 8,
            accuracy: 0.8,
            avg_latency_ms: 250.0,
            examples: vec![],
        };

        assert_eq!(results.total, 10);
        assert_eq!(results.correct, 8);
        assert_eq!(results.accuracy, 0.8);
    }
}
