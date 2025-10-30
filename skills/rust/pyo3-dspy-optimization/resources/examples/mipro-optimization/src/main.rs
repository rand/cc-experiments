//! MIPROv2 Optimization Example
//!
//! This example demonstrates how to use MIPROv2 optimization from Rust to
//! automatically improve DSPy module prompts through multi-candidate evaluation
//! and selection.

use anyhow::{Context, Result};
use mipro_optimization::{
    compare_modules, run_miprov2, save_optimization_results, CandidateTracker, MIPROConfig,
    ModuleComparison,
};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde_json::Value;
use std::fs;
use std::path::Path;

/// Load a dataset from a JSON file
///
/// # Arguments
///
/// * `py` - Python interpreter handle
/// * `path` - Path to JSON dataset file
///
/// # Returns
///
/// Returns a PyList of DSPy Example objects
fn load_dataset(py: Python, path: &str) -> PyResult<Py<PyList>> {
    println!("Loading dataset: {}", path);

    // Read JSON file
    let json_str = fs::read_to_string(path)
        .map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
                "Failed to read {}: {}",
                path, e
            ))
        })?;

    // Parse JSON
    let examples: Vec<Value> = serde_json::from_str(&json_str)
        .map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Failed to parse JSON: {}",
                e
            ))
        })?;

    println!("  Loaded {} examples", examples.len());

    // Import dspy
    let dspy = py.import("dspy")?;

    // Create PyList for examples
    let py_examples = PyList::empty(py);

    // Convert each JSON example to a DSPy Example
    for example in examples {
        let kwargs = PyDict::new(py);

        if let Some(obj) = example.as_object() {
            for (key, value) in obj {
                match value {
                    Value::String(s) => {
                        kwargs.set_item(key.as_str(), s.as_str())?;
                    }
                    Value::Number(n) => {
                        if let Some(i) = n.as_i64() {
                            kwargs.set_item(key.as_str(), i)?;
                        } else if let Some(f) = n.as_f64() {
                            kwargs.set_item(key.as_str(), f)?;
                        }
                    }
                    Value::Bool(b) => {
                        kwargs.set_item(key.as_str(), b)?;
                    }
                    _ => {}
                }
            }
        }

        let example = dspy.call_method("Example", (), Some(kwargs))?;
        py_examples.append(example)?;
    }

    Ok(py_examples.into())
}

/// Configure a language model
fn configure_lm(py: Python, dspy: &PyAny, model: &str) -> PyResult<Py<PyAny>> {
    println!("Configuring language model: {}", model);

    let kwargs = PyDict::new(py);
    kwargs.set_item("model", model)?;

    let lm = dspy.call_method("OpenAI", (), Some(kwargs))?;

    Ok(lm.into())
}

/// Create a simple QA module
fn create_qa_module(_py: Python, dspy: &PyAny) -> PyResult<Py<PyAny>> {
    // Create a signature: question, context -> answer
    let signature = "question, context -> answer";

    // Create a ChainOfThought module with this signature
    let cot = dspy.call_method1("ChainOfThought", (signature,))?;

    Ok(cot.into())
}

/// Evaluate a module on a dataset
fn evaluate_module(
    py: Python,
    module: &PyAny,
    dataset: &PyAny,
    metric: &PyAny,
) -> PyResult<f64> {
    let dspy = py.import("dspy")?;

    // Create Evaluate object
    let kwargs = PyDict::new(py);
    kwargs.set_item("devset", dataset)?;
    kwargs.set_item("metric", metric)?;
    kwargs.set_item("display_progress", true)?;

    let evaluate = dspy.call_method("Evaluate", (), Some(kwargs))?;

    // Run evaluation
    let result = evaluate.call1((module,))?;

    // Extract score (typically a float or dict with scores)
    let score: f64 = if let Ok(s) = result.extract() {
        s
    } else if let Ok(dict) = result.downcast::<PyDict>() {
        // Try to get 'metric' or 'score' key
        if let Ok(Some(metric_val)) = dict.get_item("metric") {
            metric_val.extract().unwrap_or(0.0)
        } else if let Ok(Some(score_val)) = dict.get_item("score") {
            score_val.extract().unwrap_or(0.0)
        } else {
            0.0
        }
    } else {
        0.0
    };

    Ok(score)
}

/// Create an accuracy metric function
fn create_accuracy_metric(py: Python) -> PyResult<Py<PyAny>> {
    // Define a Python function for accuracy
    let code = r#"
def accuracy_metric(example, pred, trace=None):
    """
    Simple accuracy metric that checks if the prediction matches the gold answer.
    """
    if not hasattr(pred, 'answer'):
        return 0.0

    pred_answer = str(pred.answer).strip().lower()
    gold_answer = str(example.answer).strip().lower()

    # Exact match
    if pred_answer == gold_answer:
        return 1.0

    # Partial match (gold answer is contained in prediction)
    if gold_answer in pred_answer:
        return 0.8

    # No match
    return 0.0
"#;

    // Execute the code to define the function
    let locals = PyDict::new(py);
    py.run(code, None, Some(locals))?;

    // Extract the function
    let metric = match locals.get_item("accuracy_metric")? {
        Some(m) => m,
        None => {
            return Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(
                "accuracy_metric not found",
            ));
        }
    };

    Ok(metric.into())
}

/// Save a compiled module to disk
fn save_compiled_module(_py: Python, module: &PyAny, path: &str) -> PyResult<()> {
    println!("\nSaving compiled module to: {}", path);

    // DSPy modules can be saved using save()
    let path_str = path.to_string();
    module.call_method1("save", (path_str,))?;

    println!("  Module saved successfully");

    Ok(())
}

/// Load a compiled module from disk
fn load_compiled_module(_py: Python, dspy: &PyAny, path: &str) -> PyResult<Py<PyAny>> {
    println!("Loading compiled module from: {}", path);

    let path_str = path.to_string();
    let module = dspy.call_method1("load", (path_str,))?;

    println!("  Module loaded successfully");

    Ok(module.into())
}

/// Print comparison between baseline and optimized modules
fn print_comparison(
    baseline_accuracy: f64,
    optimized_accuracy: f64,
    comparison: &ModuleComparison,
) {
    let improvement = optimized_accuracy - baseline_accuracy;
    let improvement_pct = if baseline_accuracy > 0.0 {
        (improvement / baseline_accuracy) * 100.0
    } else {
        0.0
    };

    println!("\n╔═══════════════════════════════════════════════════╗");
    println!("║           OPTIMIZATION RESULTS                    ║");
    println!("╠═══════════════════════════════════════════════════╣");
    println!("║ Baseline Accuracy:  {:>6.2}%                      ║", baseline_accuracy * 100.0);
    println!("║ Optimized Accuracy: {:>6.2}%                      ║", optimized_accuracy * 100.0);
    println!("║ Improvement:        {:>+6.2}% ({:>+5.1}%)           ║", improvement * 100.0, improvement_pct);
    println!("╚═══════════════════════════════════════════════════╝");

    comparison.print_comparison();
}

/// Run the complete optimization workflow
fn run_optimization_workflow() -> Result<()> {
    println!("╔════════════════════════════════════════════════════════╗");
    println!("║       MIPROv2 Optimization Example                    ║");
    println!("║       Multi-Prompt Instruction Optimization           ║");
    println!("╚════════════════════════════════════════════════════════╝\n");

    // Initialize Python interpreter
    pyo3::prepare_freethreaded_python();

    Python::with_gil(|py| {
        // Step 1: Load datasets
        println!("═══ Step 1: Loading Datasets ═══");
        let trainset = load_dataset(py, "data/trainset.json")
            .context("Failed to load training set")?;
        let devset = load_dataset(py, "data/devset.json")
            .context("Failed to load development set")?;

        // Step 2: Configure language models
        println!("\n═══ Step 2: Configuring Language Models ═══");
        let dspy = py.import("dspy")
            .context("Failed to import dspy")?;

        let _prompt_lm = configure_lm(py, dspy, "gpt-3.5-turbo")
            .context("Failed to configure prompt model")?;
        let task_lm = configure_lm(py, dspy, "gpt-4")
            .context("Failed to configure task model")?;

        // Set default LM to task model
        let kwargs = PyDict::new(py);
        kwargs.set_item("lm", task_lm.as_ref(py))?;
        dspy.call_method("configure", (), Some(kwargs))?;

        // Step 3: Create metric
        println!("\n═══ Step 3: Creating Evaluation Metric ═══");
        let metric = create_accuracy_metric(py)
            .context("Failed to create metric")?;
        println!("  Using accuracy metric with partial match support");

        // Step 4: Create baseline module
        println!("\n═══ Step 4: Creating Baseline Module ═══");
        let baseline_module = create_qa_module(py, dspy)
            .context("Failed to create baseline module")?;
        println!("  Created ChainOfThought QA module");

        // Step 5: Evaluate baseline
        println!("\n═══ Step 5: Evaluating Baseline ═══");
        let baseline_accuracy = evaluate_module(
            py,
            baseline_module.as_ref(py),
            devset.as_ref(py),
            metric.as_ref(py),
        )
        .context("Failed to evaluate baseline")?;
        println!("  Baseline accuracy: {:.2}%", baseline_accuracy * 100.0);

        // Step 6: Configure MIPROv2
        println!("\n═══ Step 6: Configuring MIPROv2 ═══");
        let config = MIPROConfig {
            num_candidates: 20,
            init_temperature: 1.2,
            prompt_model: "gpt-3.5-turbo".to_string(),
            task_model: "gpt-4".to_string(),
        };
        println!("  Candidates per iteration: {}", config.num_candidates);
        println!("  Initial temperature: {:.2}", config.init_temperature);
        println!("  Prompt model: {}", config.prompt_model);
        println!("  Task model: {}", config.task_model);

        // Step 7: Run optimization
        println!("\n═══ Step 7: Running Optimization ═══");
        println!("This will take several minutes...\n");

        let optimized_module = run_miprov2(
            py,
            baseline_module.as_ref(py),
            trainset.as_ref(py),
            devset.as_ref(py),
            metric.as_ref(py),
            config.clone(),
        )
        .context("MIPROv2 optimization failed")?;

        // Step 8: Evaluate optimized module
        println!("\n═══ Step 8: Evaluating Optimized Module ═══");
        let optimized_accuracy = evaluate_module(
            py,
            optimized_module.as_ref(py),
            devset.as_ref(py),
            metric.as_ref(py),
        )
        .context("Failed to evaluate optimized module")?;
        println!("  Optimized accuracy: {:.2}%", optimized_accuracy * 100.0);

        // Step 9: Compare modules
        println!("\n═══ Step 9: Comparing Modules ═══");
        let comparison = compare_modules(
            py,
            baseline_module.as_ref(py),
            optimized_module.as_ref(py),
        )
        .context("Failed to compare modules")?;

        print_comparison(baseline_accuracy, optimized_accuracy, &comparison);

        // Step 10: Save results
        println!("\n═══ Step 10: Saving Results ═══");

        // Save the optimized module
        save_compiled_module(py, optimized_module.as_ref(py), "optimized_model.json")
            .context("Failed to save optimized module")?;

        // Create a tracker for results (in a real implementation, this would be
        // populated during optimization)
        let tracker = CandidateTracker::new();

        // Save optimization results
        save_optimization_results("optimization_results.json", &tracker, &config)
            .context("Failed to save optimization results")?;

        println!("\n╔════════════════════════════════════════════════════════╗");
        println!("║                  SUCCESS!                              ║");
        println!("║                                                        ║");
        println!("║  Optimization complete. Results saved to:              ║");
        println!("║    - optimized_model.json (compiled module)            ║");
        println!("║    - optimization_results.json (metrics)               ║");
        println!("╚════════════════════════════════════════════════════════╝\n");

        Ok(())
    })
}

/// Demonstrate loading and using a saved model
fn demonstrate_saved_model() -> Result<()> {
    let model_path = "optimized_model.json";

    if !Path::new(model_path).exists() {
        println!("No saved model found. Run optimization first.");
        return Ok(());
    }

    println!("\n═══ Demonstrating Saved Model Usage ═══");

    pyo3::prepare_freethreaded_python();

    Python::with_gil(|py| {
        let dspy = py.import("dspy")
            .context("Failed to import dspy")?;

        // Load the model
        let model = load_compiled_module(py, dspy, model_path)
            .context("Failed to load model")?;

        // Configure LM
        let lm = configure_lm(py, dspy, "gpt-4")?;
        let kwargs = PyDict::new(py);
        kwargs.set_item("lm", lm.as_ref(py))?;
        dspy.call_method("configure", (), Some(kwargs))?;

        // Make a test prediction
        println!("\nMaking test prediction...");
        let test_kwargs = PyDict::new(py);
        test_kwargs.set_item(
            "question",
            "What is the capital of France?",
        )?;
        test_kwargs.set_item(
            "context",
            "France is a country in Western Europe. Paris is its capital and largest city.",
        )?;

        let result = model.as_ref(py).call((), Some(test_kwargs))?;
        let answer: String = result.getattr("answer")?.extract()?;

        println!("  Question: What is the capital of France?");
        println!("  Answer: {}", answer);

        Ok(())
    })
}

fn main() -> Result<()> {
    // Check for API key
    if std::env::var("OPENAI_API_KEY").is_err() {
        eprintln!("Error: OPENAI_API_KEY environment variable not set");
        eprintln!("Please set it with: export OPENAI_API_KEY='your-api-key'");
        return Err(anyhow::anyhow!("OPENAI_API_KEY not set"));
    }

    // Run the optimization workflow
    match run_optimization_workflow() {
        Ok(_) => {
            // Optionally demonstrate loading the saved model
            if std::env::var("DEMO_LOAD").is_ok() {
                demonstrate_saved_model()?;
            }
        }
        Err(e) => {
            eprintln!("\n╔════════════════════════════════════════════════════════╗");
            eprintln!("║                    ERROR                               ║");
            eprintln!("╚════════════════════════════════════════════════════════╝");
            eprintln!("\nOptimization failed: {}", e);
            eprintln!("\nCause chain:");
            for (i, cause) in e.chain().enumerate() {
                eprintln!("  {}: {}", i, cause);
            }
            return Err(e);
        }
    }

    Ok(())
}
