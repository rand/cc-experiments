---
name: pyo3-dspy-optimization
description: DSPy optimization workflows from Rust - running teleprompters, compiled model management, versioning, evaluation
skill_id: rust-pyo3-dspy-optimization
title: PyO3 DSPy Optimization Workflows
category: rust
subcategory: pyo3-dspy
complexity: intermediate
prerequisites:
  - rust-pyo3-dspy-fundamentals
  - rust-pyo3-dspy-type-system
  - ml-dspy-optimization
  - ml-dspy-teleprompters
tags:
  - rust
  - python
  - pyo3
  - dspy
  - optimization
  - teleprompters
  - evaluation
  - model-versioning
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Run DSPy teleprompters (BootstrapFewShot, MIPROv2, COPRO) from Rust
  - Save and load compiled DSPy models with proper versioning
  - Build evaluation workflows in Rust
  - Implement A/B testing for model comparison
  - Design automated optimization pipelines
  - Manage model artifacts and deployment
  - Monitor optimization progress from Rust
related_skills:
  - rust-pyo3-dspy-fundamentals
  - rust-pyo3-dspy-production
  - ml-dspy-optimization
  - ml-dspy-evaluation
resources:
  - REFERENCE.md (800+ lines): Complete optimization guide
  - 4 Python scripts (1,000+ lines): Teleprompter runners, evaluation harness
  - 8 Rust+Python examples (1,500+ lines): End-to-end optimization workflows
---

# PyO3 DSPy Optimization Workflows

## Overview

Master running DSPy optimization workflows from Rust. Learn to execute teleprompters (BootstrapFewShot, MIPROv2, COPRO), save and version compiled models, build evaluation harnesses, implement A/B testing frameworks, and design automated optimization pipelines—all from type-safe Rust code.

This skill bridges DSPy's powerful optimization capabilities with Rust's production-ready infrastructure, enabling automated model improvement, systematic evaluation, and controlled deployment of optimized models.

## Prerequisites

**Required**:
- PyO3 DSPy fundamentals (module calls, error handling)
- DSPy optimization concepts (teleprompters, metrics, compilers)
- Rust async programming (Tokio)
- Understanding of model evaluation and versioning

**Recommended**:
- Production deployment experience
- CI/CD pipeline knowledge
- Metrics and observability systems
- A/B testing frameworks

## When to Use

**Ideal for**:
- **Production optimization pipelines** running automated model improvement
- **Systematic evaluation** of DSPy modules with version control
- **A/B testing** different model versions in production
- **Automated retraining** workflows triggered by performance degradation
- **Model lifecycle management** from optimization to deployment
- **Performance monitoring** and quality gates

**Not ideal for**:
- Quick manual experiments (use Python directly)
- One-off optimizations (overhead not justified)
- Prototyping (slower iteration cycle)

## Learning Path

### 1. Running Teleprompters from Rust

Execute DSPy optimizers from Rust with progress tracking.

**BootstrapFewShot Example**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule};
use serde::{Deserialize, Serialize};
use anyhow::{Context, Result};

#[derive(Debug, Serialize, Deserialize)]
struct TrainingExample {
    question: String,
    answer: String,
}

#[derive(Debug)]
struct OptimizationResult {
    compiled_model: Py<PyAny>,
    num_examples: usize,
    optimization_score: f64,
}

fn run_bootstrap_fewshot(
    py: Python,
    module: &PyAny,
    trainset: Vec<TrainingExample>,
    metric_fn: &PyAny,
) -> PyResult<OptimizationResult> {
    let dspy = PyModule::import(py, "dspy")?;
    let teleprompter_mod = dspy.getattr("teleprompt")?;

    // Create BootstrapFewShot
    let bootstrap = teleprompter_mod
        .getattr("BootstrapFewShot")?
        .call((), Some({
            let kwargs = PyDict::new(py);
            kwargs.set_item("metric", metric_fn)?;
            kwargs.set_item("max_bootstrapped_demos", 4)?;
            kwargs.set_item("max_labeled_demos", 8)?;
            kwargs
        }))?;

    // Convert trainset to Python list
    let py_trainset = PyList::empty(py);
    for example in &trainset {
        let ex_dict = PyDict::new(py);
        ex_dict.set_item("question", &example.question)?;
        ex_dict.set_item("answer", &example.answer)?;
        py_trainset.append(ex_dict)?;
    }

    // Compile the module
    println!("Starting BootstrapFewShot optimization...");
    let compiled = bootstrap.call_method1(
        "compile",
        ((module, py_trainset),)
    )?;

    // Extract optimization metrics
    let score = compiled
        .getattr("optimization_score")
        .ok()
        .and_then(|s| s.extract::<f64>().ok())
        .unwrap_or(0.0);

    Ok(OptimizationResult {
        compiled_model: compiled.into(),
        num_examples: trainset.len(),
        optimization_score: score,
    })
}

fn main() -> Result<()> {
    Python::with_gil(|py| {
        // Configure DSPy
        configure_lm(py)?;

        // Create module to optimize
        let module = create_qa_module(py)?;

        // Load training data
        let trainset = load_training_data()?;

        // Define metric function
        let metric = create_accuracy_metric(py)?;

        // Run optimization
        let result = run_bootstrap_fewshot(
            py,
            module.as_ref(py),
            trainset,
            metric.as_ref(py),
        )?;

        println!("Optimization complete!");
        println!("  Examples used: {}", result.num_examples);
        println!("  Score: {:.2}", result.optimization_score);

        Ok(())
    })
}
```

**MIPROv2 Optimization**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[derive(Debug, Clone)]
struct MIPROConfig {
    num_candidates: usize,
    init_temperature: f64,
    prompt_model: String,
    task_model: String,
}

fn run_miprov2(
    py: Python,
    module: &PyAny,
    trainset: &PyAny,
    devset: &PyAny,
    metric: &PyAny,
    config: MIPROConfig,
) -> PyResult<Py<PyAny>> {
    let dspy = PyModule::import(py, "dspy")?;
    let teleprompter_mod = dspy.getattr("teleprompt")?;

    // Create MIPROv2 teleprompter
    let kwargs = PyDict::new(py);
    kwargs.set_item("metric", metric)?;
    kwargs.set_item("num_candidates", config.num_candidates)?;
    kwargs.set_item("init_temperature", config.init_temperature)?;
    kwargs.set_item("prompt_model", config.prompt_model)?;
    kwargs.set_item("task_model", config.task_model)?;

    let mipro = teleprompter_mod
        .getattr("MIPROv2")?
        .call((), Some(kwargs))?;

    println!("Running MIPROv2 optimization...");
    println!("  Candidates: {}", config.num_candidates);
    println!("  Temperature: {}", config.init_temperature);

    // Compile with progress tracking
    let compiled = mipro.call_method(
        "compile",
        ((module, trainset),),
        Some({
            let kwargs = PyDict::new(py);
            kwargs.set_item("devset", devset)?;
            kwargs.set_item("requires_permission_to_run", false)?;
            kwargs
        })
    )?;

    Ok(compiled.into())
}
```

### 2. Compiled Model Management

Save and load optimized models with metadata.

**Save Compiled Model**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Serialize, Deserialize)]
struct ModelMetadata {
    model_id: String,
    version: String,
    created_at: String,
    optimizer: String,
    base_model: String,
    num_training_examples: usize,
    validation_score: f64,
    hyperparameters: serde_json::Value,
}

fn save_compiled_model(
    py: Python,
    compiled_model: &PyAny,
    metadata: ModelMetadata,
    output_dir: &Path,
) -> Result<()> {
    // Create output directory
    fs::create_dir_all(output_dir)?;

    // Save model using DSPy's save method
    let model_path = output_dir.join("model.json");
    compiled_model.call_method1(
        "save",
        ((model_path.to_str().unwrap(),),)
    ).context("Failed to save DSPy model")?;

    // Save metadata
    let metadata_path = output_dir.join("metadata.json");
    let metadata_json = serde_json::to_string_pretty(&metadata)?;
    fs::write(&metadata_path, metadata_json)?;

    println!("Model saved to: {}", output_dir.display());
    println!("  Model: {}", model_path.display());
    println!("  Metadata: {}", metadata_path.display());

    Ok(())
}

fn load_compiled_model(
    py: Python,
    model_dir: &Path,
) -> Result<(Py<PyAny>, ModelMetadata)> {
    // Load metadata
    let metadata_path = model_dir.join("metadata.json");
    let metadata_json = fs::read_to_string(&metadata_path)?;
    let metadata: ModelMetadata = serde_json::from_str(&metadata_json)?;

    // Load model
    let model_path = model_dir.join("model.json");
    let dspy = PyModule::import(py, "dspy")?;

    let model = dspy.call_method1(
        "load",
        ((model_path.to_str().unwrap(),),)
    ).context("Failed to load DSPy model")?;

    println!("Model loaded: {} v{}", metadata.model_id, metadata.version);
    println!("  Score: {:.2}", metadata.validation_score);

    Ok((model.into(), metadata))
}
```

### 3. Model Versioning

Implement semantic versioning for compiled models.

**Version Management System**:

```rust
use semver::Version;
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug)]
struct ModelRegistry {
    base_dir: PathBuf,
    models: HashMap<String, Vec<ModelVersion>>,
}

#[derive(Debug, Clone)]
struct ModelVersion {
    version: Version,
    path: PathBuf,
    metadata: ModelMetadata,
    status: ModelStatus,
}

#[derive(Debug, Clone, PartialEq)]
enum ModelStatus {
    Development,
    Staging,
    Production,
    Deprecated,
}

impl ModelRegistry {
    fn new(base_dir: PathBuf) -> Result<Self> {
        fs::create_dir_all(&base_dir)?;
        Ok(Self {
            base_dir,
            models: HashMap::new(),
        })
    }

    fn register_model(
        &mut self,
        model_id: &str,
        version: Version,
        metadata: ModelMetadata,
    ) -> Result<PathBuf> {
        let model_dir = self.base_dir
            .join(model_id)
            .join(version.to_string());

        fs::create_dir_all(&model_dir)?;

        let version_entry = ModelVersion {
            version: version.clone(),
            path: model_dir.clone(),
            metadata,
            status: ModelStatus::Development,
        };

        self.models
            .entry(model_id.to_string())
            .or_insert_with(Vec::new)
            .push(version_entry);

        Ok(model_dir)
    }

    fn promote_to_production(
        &mut self,
        model_id: &str,
        version: &Version,
    ) -> Result<()> {
        let versions = self.models.get_mut(model_id)
            .context("Model not found")?;

        // Demote current production version
        for v in versions.iter_mut() {
            if v.status == ModelStatus::Production {
                v.status = ModelStatus::Deprecated;
            }
        }

        // Promote new version
        let version_entry = versions.iter_mut()
            .find(|v| &v.version == version)
            .context("Version not found")?;

        version_entry.status = ModelStatus::Production;

        println!("Promoted {} v{} to production", model_id, version);
        Ok(())
    }

    fn get_production_model(
        &self,
        model_id: &str,
    ) -> Option<&ModelVersion> {
        self.models.get(model_id)?
            .iter()
            .find(|v| v.status == ModelStatus::Production)
    }

    fn get_latest_version(
        &self,
        model_id: &str,
    ) -> Option<&ModelVersion> {
        self.models.get(model_id)?
            .iter()
            .max_by_key(|v| &v.version)
    }
}

// Usage example
fn version_workflow() -> Result<()> {
    let mut registry = ModelRegistry::new("./models".into())?;

    Python::with_gil(|py| {
        // Train new model
        let compiled = train_model(py)?;

        let metadata = ModelMetadata {
            model_id: "qa-model".to_string(),
            version: "1.2.0".to_string(),
            created_at: chrono::Utc::now().to_rfc3339(),
            optimizer: "MIPROv2".to_string(),
            base_model: "gpt-3.5-turbo".to_string(),
            num_training_examples: 1000,
            validation_score: 0.87,
            hyperparameters: serde_json::json!({
                "num_candidates": 10,
                "temperature": 0.7,
            }),
        };

        // Register new version
        let version = Version::parse("1.2.0")?;
        let model_dir = registry.register_model(
            "qa-model",
            version.clone(),
            metadata,
        )?;

        // Save model
        save_compiled_model(py, compiled.as_ref(py), metadata, &model_dir)?;

        // After validation, promote to production
        registry.promote_to_production("qa-model", &version)?;

        Ok(())
    })
}
```

### 4. Evaluation Workflows

Build evaluation harnesses in Rust.

**Evaluation Framework**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyList;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct EvaluationResult {
    model_id: String,
    version: String,
    total_examples: usize,
    correct: usize,
    accuracy: f64,
    average_latency_ms: f64,
    per_example_results: Vec<ExampleResult>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ExampleResult {
    input: String,
    expected: String,
    predicted: String,
    correct: bool,
    latency_ms: f64,
}

async fn evaluate_model(
    model_path: &Path,
    test_set: Vec<TrainingExample>,
    metric_fn: Py<PyAny>,
) -> Result<EvaluationResult> {
    Python::with_gil(|py| {
        // Load model
        let (model, metadata) = load_compiled_model(py, model_path)?;

        let mut results = Vec::new();
        let mut correct_count = 0;
        let mut total_latency = 0.0;

        for example in &test_set {
            let start = std::time::Instant::now();

            // Run prediction
            let prediction = model.as_ref(py).call_method1(
                "forward",
                ((example.question.as_str(),),)
            )?;

            let latency = start.elapsed().as_secs_f64() * 1000.0;

            // Extract answer
            let predicted: String = prediction
                .getattr("answer")?
                .extract()?;

            // Compute metric
            let is_correct: bool = metric_fn.as_ref(py).call1((
                (predicted.as_str(), example.answer.as_str()),
            ))?.extract()?;

            if is_correct {
                correct_count += 1;
            }

            total_latency += latency;

            results.push(ExampleResult {
                input: example.question.clone(),
                expected: example.answer.clone(),
                predicted,
                correct: is_correct,
                latency_ms: latency,
            });
        }

        let accuracy = correct_count as f64 / test_set.len() as f64;
        let avg_latency = total_latency / test_set.len() as f64;

        Ok(EvaluationResult {
            model_id: metadata.model_id,
            version: metadata.version,
            total_examples: test_set.len(),
            correct: correct_count,
            accuracy,
            average_latency_ms: avg_latency,
            per_example_results: results,
        })
    })
}

fn save_evaluation_report(
    result: &EvaluationResult,
    output_path: &Path,
) -> Result<()> {
    let report_json = serde_json::to_string_pretty(result)?;
    fs::write(output_path, report_json)?;

    println!("\nEvaluation Report");
    println!("================");
    println!("Model: {} v{}", result.model_id, result.version);
    println!("Accuracy: {:.2}%", result.accuracy * 100.0);
    println!("Avg Latency: {:.2}ms", result.average_latency_ms);
    println!("Correct: {}/{}", result.correct, result.total_examples);
    println!("\nReport saved to: {}", output_path.display());

    Ok(())
}
```

### 5. A/B Testing Framework

Compare model versions in production.

**A/B Testing Implementation**:

```rust
use rand::Rng;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Debug, Clone)]
struct ABTestConfig {
    model_a_id: String,
    model_b_id: String,
    traffic_split: f64, // 0.5 = 50/50 split
    sample_size: usize,
}

struct ABTestRunner {
    model_a: Arc<RwLock<Py<PyAny>>>,
    model_b: Arc<RwLock<Py<PyAny>>>,
    config: ABTestConfig,
    model_a_requests: Arc<AtomicUsize>,
    model_b_requests: Arc<AtomicUsize>,
    model_a_successes: Arc<AtomicUsize>,
    model_b_successes: Arc<AtomicUsize>,
}

impl ABTestRunner {
    fn new(
        py: Python,
        model_a_path: &Path,
        model_b_path: &Path,
        config: ABTestConfig,
    ) -> Result<Self> {
        let (model_a, _) = load_compiled_model(py, model_a_path)?;
        let (model_b, _) = load_compiled_model(py, model_b_path)?;

        Ok(Self {
            model_a: Arc::new(RwLock::new(model_a)),
            model_b: Arc::new(RwLock::new(model_b)),
            config,
            model_a_requests: Arc::new(AtomicUsize::new(0)),
            model_b_requests: Arc::new(AtomicUsize::new(0)),
            model_a_successes: Arc::new(AtomicUsize::new(0)),
            model_b_successes: Arc::new(AtomicUsize::new(0)),
        })
    }

    async fn predict(&self, input: &str, metric_fn: &PyAny) -> Result<String> {
        let mut rng = rand::thread_rng();
        let use_model_a = rng.gen::<f64>() < self.config.traffic_split;

        let (result, model_id) = if use_model_a {
            let model = self.model_a.read().await;
            let res = Python::with_gil(|py| {
                model.as_ref(py).call_method1("forward", ((input,),))
            })?;
            self.model_a_requests.fetch_add(1, Ordering::SeqCst);
            (res, &self.config.model_a_id)
        } else {
            let model = self.model_b.read().await;
            let res = Python::with_gil(|py| {
                model.as_ref(py).call_method1("forward", ((input,),))
            })?;
            self.model_b_requests.fetch_add(1, Ordering::SeqCst);
            (res, &self.config.model_b_id)
        };

        let answer = Python::with_gil(|py| {
            result.as_ref(py).getattr("answer")?.extract::<String>()
        })?;

        // Track success based on metric (if available)
        // This would typically be done asynchronously

        Ok(answer)
    }

    fn get_statistics(&self) -> ABTestStats {
        let a_requests = self.model_a_requests.load(Ordering::SeqCst);
        let b_requests = self.model_b_requests.load(Ordering::SeqCst);
        let a_successes = self.model_a_successes.load(Ordering::SeqCst);
        let b_successes = self.model_b_successes.load(Ordering::SeqCst);

        ABTestStats {
            model_a_id: self.config.model_a_id.clone(),
            model_b_id: self.config.model_b_id.clone(),
            model_a_requests: a_requests,
            model_b_requests: b_requests,
            model_a_success_rate: if a_requests > 0 {
                a_successes as f64 / a_requests as f64
            } else {
                0.0
            },
            model_b_success_rate: if b_requests > 0 {
                b_successes as f64 / b_requests as f64
            } else {
                0.0
            },
            total_requests: a_requests + b_requests,
        }
    }
}

#[derive(Debug, Serialize)]
struct ABTestStats {
    model_a_id: String,
    model_b_id: String,
    model_a_requests: usize,
    model_b_requests: usize,
    model_a_success_rate: f64,
    model_b_success_rate: f64,
    total_requests: usize,
}
```

### 6. Deployment Pipelines

Automated optimization and deployment workflows.

**Complete Pipeline**:

```rust
use tokio::process::Command;
use std::process::Stdio;

#[derive(Debug)]
struct OptimizationPipeline {
    registry: ModelRegistry,
    config: PipelineConfig,
}

#[derive(Debug, Clone)]
struct PipelineConfig {
    model_id: String,
    base_model: String,
    optimizer: String,
    training_data_path: PathBuf,
    validation_data_path: PathBuf,
    min_accuracy: f64,
    auto_promote: bool,
}

impl OptimizationPipeline {
    async fn run(&mut self) -> Result<ModelVersion> {
        println!("Starting optimization pipeline for {}", self.config.model_id);

        // Step 1: Load training data
        println!("[1/6] Loading training data...");
        let trainset = self.load_training_data().await?;
        let valset = self.load_validation_data().await?;

        // Step 2: Run optimization
        println!("[2/6] Running {} optimization...", self.config.optimizer);
        let compiled_model = Python::with_gil(|py| {
            self.run_optimizer(py, &trainset, &valset)
        })?;

        // Step 3: Evaluate model
        println!("[3/6] Evaluating model...");
        let eval_result = self.evaluate_model(&compiled_model).await?;

        // Step 4: Check quality gate
        println!("[4/6] Checking quality gate...");
        if eval_result.accuracy < self.config.min_accuracy {
            anyhow::bail!(
                "Model accuracy {:.2}% below threshold {:.2}%",
                eval_result.accuracy * 100.0,
                self.config.min_accuracy * 100.0
            );
        }

        // Step 5: Version and save
        println!("[5/6] Saving model...");
        let new_version = self.determine_version()?;
        let model_dir = self.save_versioned_model(
            &compiled_model,
            &new_version,
            &eval_result,
        )?;

        // Step 6: Promote if auto-promote enabled
        if self.config.auto_promote {
            println!("[6/6] Promoting to production...");
            self.registry.promote_to_production(
                &self.config.model_id,
                &new_version,
            )?;
        } else {
            println!("[6/6] Skipping auto-promotion");
        }

        println!("\n✅ Pipeline complete!");
        println!("   Model: {} v{}", self.config.model_id, new_version);
        println!("   Accuracy: {:.2}%", eval_result.accuracy * 100.0);

        Ok(self.registry.get_latest_version(&self.config.model_id)
            .unwrap()
            .clone())
    }

    fn run_optimizer(
        &self,
        py: Python,
        trainset: &[TrainingExample],
        valset: &[TrainingExample],
    ) -> Result<Py<PyAny>> {
        // Create module
        let module = create_module(py)?;

        // Create metric
        let metric = create_metric(py)?;

        // Convert datasets to Python
        let py_trainset = convert_to_python_list(py, trainset)?;
        let py_valset = convert_to_python_list(py, valset)?;

        // Run appropriate optimizer
        let compiled = match self.config.optimizer.as_str() {
            "BootstrapFewShot" => {
                run_bootstrap_fewshot(
                    py,
                    module.as_ref(py),
                    trainset.to_vec(),
                    metric.as_ref(py),
                )?.compiled_model
            },
            "MIPROv2" => {
                let config = MIPROConfig {
                    num_candidates: 10,
                    init_temperature: 1.0,
                    prompt_model: self.config.base_model.clone(),
                    task_model: self.config.base_model.clone(),
                };
                run_miprov2(
                    py,
                    module.as_ref(py),
                    py_trainset.as_ref(py),
                    py_valset.as_ref(py),
                    metric.as_ref(py),
                    config,
                )?
            },
            _ => anyhow::bail!("Unsupported optimizer: {}", self.config.optimizer),
        };

        Ok(compiled)
    }
}

// CLI for pipeline execution
#[tokio::main]
async fn main() -> Result<()> {
    let config = PipelineConfig {
        model_id: "qa-model".to_string(),
        base_model: "gpt-3.5-turbo".to_string(),
        optimizer: "MIPROv2".to_string(),
        training_data_path: "data/train.jsonl".into(),
        validation_data_path: "data/val.jsonl".into(),
        min_accuracy: 0.85,
        auto_promote: false,
    };

    let registry = ModelRegistry::new("./models".into())?;
    let mut pipeline = OptimizationPipeline { registry, config };

    let version = pipeline.run().await?;

    println!("\nModel ready for deployment:");
    println!("  Path: {}", version.path.display());
    println!("  Status: {:?}", version.status);

    Ok(())
}
```

### 7. Progress Monitoring

Track optimization progress from Rust.

**Progress Tracker**:

```rust
use std::sync::mpsc::{channel, Sender, Receiver};
use std::thread;

#[derive(Debug, Clone)]
enum OptimizationEvent {
    Started { optimizer: String, total_steps: usize },
    Progress { step: usize, message: String },
    Completed { score: f64 },
    Error { error: String },
}

struct ProgressMonitor {
    tx: Sender<OptimizationEvent>,
    rx: Receiver<OptimizationEvent>,
}

impl ProgressMonitor {
    fn new() -> Self {
        let (tx, rx) = channel();
        Self { tx, rx }
    }

    fn run_with_monitoring<F>(&self, f: F) -> Result<()>
    where
        F: FnOnce(Sender<OptimizationEvent>) -> Result<()> + Send + 'static,
    {
        let tx = self.tx.clone();

        // Spawn optimization in background
        thread::spawn(move || {
            if let Err(e) = f(tx.clone()) {
                let _ = tx.send(OptimizationEvent::Error {
                    error: e.to_string(),
                });
            }
        });

        // Monitor progress
        while let Ok(event) = self.rx.recv() {
            match event {
                OptimizationEvent::Started { optimizer, total_steps } => {
                    println!("🚀 Started {} ({} steps)", optimizer, total_steps);
                },
                OptimizationEvent::Progress { step, message } => {
                    println!("   [{}] {}", step, message);
                },
                OptimizationEvent::Completed { score } => {
                    println!("✅ Completed! Score: {:.2}", score);
                    break;
                },
                OptimizationEvent::Error { error } => {
                    eprintln!("❌ Error: {}", error);
                    break;
                },
            }
        }

        Ok(())
    }
}
```

### 8. Complete Example: End-to-End Workflow

Full optimization, evaluation, and deployment workflow.

```rust
use clap::Parser;

#[derive(Parser)]
#[clap(name = "dspy-optimizer")]
struct Args {
    #[clap(subcommand)]
    command: Command,
}

#[derive(Parser)]
enum Command {
    /// Optimize a model
    Optimize {
        #[clap(long)]
        model_id: String,
        #[clap(long)]
        optimizer: String,
        #[clap(long)]
        train_data: PathBuf,
    },
    /// Evaluate a model
    Evaluate {
        #[clap(long)]
        model_path: PathBuf,
        #[clap(long)]
        test_data: PathBuf,
    },
    /// Start A/B test
    AbTest {
        #[clap(long)]
        model_a: PathBuf,
        #[clap(long)]
        model_b: PathBuf,
        #[clap(long, default_value = "0.5")]
        split: f64,
    },
    /// Promote model to production
    Promote {
        #[clap(long)]
        model_id: String,
        #[clap(long)]
        version: String,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    match args.command {
        Command::Optimize { model_id, optimizer, train_data } => {
            let config = PipelineConfig {
                model_id,
                optimizer,
                training_data_path: train_data,
                validation_data_path: "data/val.jsonl".into(),
                base_model: "gpt-3.5-turbo".to_string(),
                min_accuracy: 0.80,
                auto_promote: false,
            };

            let registry = ModelRegistry::new("./models".into())?;
            let mut pipeline = OptimizationPipeline { registry, config };
            pipeline.run().await?;
        },
        Command::Evaluate { model_path, test_data } => {
            let test_set = load_test_data(&test_data)?;
            let metric = Python::with_gil(|py| create_metric(py))?;

            let result = evaluate_model(&model_path, test_set, metric).await?;
            save_evaluation_report(&result, &model_path.join("eval_report.json"))?;
        },
        Command::AbTest { model_a, model_b, split } => {
            let config = ABTestConfig {
                model_a_id: "model-a".to_string(),
                model_b_id: "model-b".to_string(),
                traffic_split: split,
                sample_size: 1000,
            };

            let runner = Python::with_gil(|py| {
                ABTestRunner::new(py, &model_a, &model_b, config)
            })?;

            println!("A/B test started. Serving traffic...");
            // In production, this would be integrated with your API
        },
        Command::Promote { model_id, version } => {
            let mut registry = ModelRegistry::new("./models".into())?;
            let ver = Version::parse(&version)?;
            registry.promote_to_production(&model_id, &ver)?;
        },
    }

    Ok(())
}
```

## Best Practices

### DO

✅ **Version all optimized models** with semantic versioning
✅ **Save optimization metadata** (hyperparameters, scores, timestamps)
✅ **Validate before promotion** using quality gates
✅ **Track evaluation metrics** across versions
✅ **Use A/B testing** before full production rollout
✅ **Monitor optimization progress** with structured events
✅ **Automate pipelines** with CI/CD integration
✅ **Keep training data versioned** alongside models

### DON'T

❌ **Skip evaluation** before deployment
❌ **Overwrite production models** without versioning
❌ **Ignore quality gates** when results are poor
❌ **Mix optimization environments** (dev/staging/prod)
❌ **Forget to track hyperparameters**
❌ **Deploy without A/B testing** critical models
❌ **Leave optimization running indefinitely** without timeouts
❌ **Skip model metadata** (makes debugging impossible)

## Common Pitfalls

### 1. Optimization Timeout

**Problem**: Teleprompters run indefinitely
```rust
// ❌ Bad: No timeout
let compiled = run_miprov2(py, module, trainset, devset, metric, config)?;
```

**Solution**: Set timeout and handle gracefully
```rust
// ✅ Good: Timeout protection
use tokio::time::{timeout, Duration};

let result = timeout(
    Duration::from_secs(3600), // 1 hour max
    run_optimization_async(config)
).await??;
```

### 2. Missing Quality Gates

**Problem**: Deploying poorly performing models
```rust
// ❌ Bad: No validation
save_model(compiled)?;
promote_to_production()?;
```

**Solution**: Enforce quality gates
```rust
// ✅ Good: Validate before promotion
let eval = evaluate_model(&compiled, &test_set).await?;
if eval.accuracy < 0.85 {
    anyhow::bail!("Model below quality threshold");
}
promote_to_production()?;
```

### 3. Version Conflicts

**Problem**: Concurrent optimizations overwriting models
**Solution**: Use atomic operations and locking for version management

## Troubleshooting

### Issue: Optimization Fails Silently

**Symptom**: Teleprompter completes but model performs poorly

**Solution**: Check optimization logs and validate training data
```python
# Enable DSPy logging
python resources/scripts/debug_optimizer.py --verbose
```

### Issue: Model Load Failure

**Symptom**: `Failed to load DSPy model`

**Solution**: Verify model format and DSPy version compatibility
```rust
// Check model compatibility
let metadata = load_metadata(model_path)?;
println!("Model DSPy version: {}", metadata.dspy_version);
```

### Issue: A/B Test Bias

**Symptom**: Uneven traffic distribution

**Solution**: Verify randomization and traffic splitting logic
```rust
// Add traffic distribution logging
println!("A: {}, B: {}", a_requests, b_requests);
assert!((a_requests as f64 / total as f64 - 0.5).abs() < 0.05);
```

## Next Steps

**After mastering optimization**:
1. **pyo3-dspy-production**: Production deployment patterns
2. **pyo3-dspy-monitoring**: Observability and metrics
3. **pyo3-dspy-rag-pipelines**: RAG optimization workflows
4. **pyo3-dspy-agents**: Agent optimization strategies
5. **ml-dspy-advanced-optimization**: Advanced teleprompter techniques

## References

- [DSPy Teleprompters](https://dspy-docs.vercel.app/docs/building-blocks/teleprompters)
- [DSPy Evaluation](https://dspy-docs.vercel.app/docs/building-blocks/metrics)
- [Model Versioning Best Practices](https://ml-ops.org/content/model-versioning)
- [A/B Testing for ML](https://netflixtechblog.com/a-b-testing-and-beyond-8e19c23dfccc)

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Maintainer**: DSPy-PyO3 Integration Team
