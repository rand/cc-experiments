//! BootstrapFewShot Optimization Library
//!
//! Core functionality for running DSPy's BootstrapFewShot teleprompter from Rust.
//! Provides training data structures, optimization workflows, progress tracking,
//! and model persistence.

use anyhow::{Context, Result};
use pyo3::prelude::*;
use pyo3::types::{PyAnyMethods, PyDict, PyList, PyModule};
use serde::{Deserialize, Serialize};
use std::path::Path;
use std::time::{Duration, Instant};

// ============================================================================
// Training Data Types
// ============================================================================

/// A single training example for question-answering tasks
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingExample {
    /// The input question
    pub question: String,
    /// The expected answer
    pub answer: String,
}

/// A collection of training examples with metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingDataset {
    /// All training examples
    pub examples: Vec<TrainingExample>,
    /// Dataset name or identifier
    pub name: String,
    /// Optional description
    pub description: Option<String>,
}

impl TrainingDataset {
    /// Create a new training dataset
    pub fn new(name: String, examples: Vec<TrainingExample>) -> Self {
        Self {
            examples,
            name,
            description: None,
        }
    }

    /// Load training dataset from JSON file
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let content = std::fs::read_to_string(path.as_ref())
            .context("Failed to read training data file")?;

        let examples: Vec<TrainingExample> = serde_json::from_str(&content)
            .context("Failed to parse training data JSON")?;

        Ok(Self {
            examples,
            name: path
                .as_ref()
                .file_stem()
                .and_then(|s| s.to_str())
                .unwrap_or("unknown")
                .to_string(),
            description: None,
        })
    }

    /// Save training dataset to JSON file
    pub fn save<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let json = serde_json::to_string_pretty(&self.examples)
            .context("Failed to serialize training data")?;

        std::fs::write(path.as_ref(), json)
            .context("Failed to write training data file")?;

        Ok(())
    }

    /// Split dataset into train and validation sets
    pub fn split(&self, train_ratio: f64) -> (Self, Self) {
        let split_idx = (self.examples.len() as f64 * train_ratio) as usize;

        let train_examples = self.examples[..split_idx].to_vec();
        let val_examples = self.examples[split_idx..].to_vec();

        let train = Self {
            examples: train_examples,
            name: format!("{}_train", self.name),
            description: Some("Training split".to_string()),
        };

        let val = Self {
            examples: val_examples,
            name: format!("{}_val", self.name),
            description: Some("Validation split".to_string()),
        };

        (train, val)
    }

    /// Get number of examples
    pub fn len(&self) -> usize {
        self.examples.len()
    }

    /// Check if dataset is empty
    pub fn is_empty(&self) -> bool {
        self.examples.is_empty()
    }
}

// ============================================================================
// Optimization Configuration
// ============================================================================

/// Configuration for BootstrapFewShot optimization
#[derive(Debug, Clone)]
pub struct OptimizationConfig {
    /// Maximum number of bootstrapped demonstrations to select
    pub max_bootstrapped_demos: usize,
    /// Maximum number of labeled demonstrations to include
    pub max_labeled_demos: usize,
    /// Minimum metric score for demonstration selection
    pub metric_threshold: f64,
    /// Enable verbose logging during optimization
    pub verbose: bool,
    /// Random seed for reproducibility
    pub random_seed: Option<u64>,
}

impl Default for OptimizationConfig {
    fn default() -> Self {
        Self {
            max_bootstrapped_demos: 4,
            max_labeled_demos: 8,
            metric_threshold: 0.7,
            verbose: true,
            random_seed: None,
        }
    }
}

impl OptimizationConfig {
    /// Create a new configuration with defaults
    pub fn new() -> Self {
        Self::default()
    }

    /// Set max bootstrapped demonstrations
    pub fn with_max_bootstrapped_demos(mut self, max: usize) -> Self {
        self.max_bootstrapped_demos = max;
        self
    }

    /// Set max labeled demonstrations
    pub fn with_max_labeled_demos(mut self, max: usize) -> Self {
        self.max_labeled_demos = max;
        self
    }

    /// Set metric threshold
    pub fn with_metric_threshold(mut self, threshold: f64) -> Self {
        self.metric_threshold = threshold;
        self
    }

    /// Enable or disable verbose logging
    pub fn with_verbose(mut self, verbose: bool) -> Self {
        self.verbose = verbose;
        self
    }

    /// Set random seed
    pub fn with_random_seed(mut self, seed: u64) -> Self {
        self.random_seed = Some(seed);
        self
    }
}

// ============================================================================
// Optimization Results
// ============================================================================

/// Result of BootstrapFewShot optimization
#[derive(Debug)]
pub struct OptimizationResult {
    /// The compiled, optimized model
    pub compiled_model: Py<PyAny>,
    /// Number of training examples used
    pub num_examples: usize,
    /// Number of demonstrations selected and embedded
    pub num_demonstrations: usize,
    /// Final optimization score
    pub optimization_score: f64,
    /// Time taken for optimization
    pub duration: Duration,
}

impl OptimizationResult {
    /// Create a new optimization result
    pub fn new(
        compiled_model: Py<PyAny>,
        num_examples: usize,
        num_demonstrations: usize,
        optimization_score: f64,
        duration: Duration,
    ) -> Self {
        Self {
            compiled_model,
            num_examples,
            num_demonstrations,
            optimization_score,
            duration,
        }
    }

    /// Get optimization score as percentage
    pub fn score_percent(&self) -> f64 {
        self.optimization_score * 100.0
    }

    /// Get duration in seconds
    pub fn duration_secs(&self) -> f64 {
        self.duration.as_secs_f64()
    }
}

// ============================================================================
// Progress Tracking
// ============================================================================

/// Callback function type for progress updates
pub type ProgressCallback = Box<dyn Fn(ProgressEvent) + Send>;

/// Events emitted during optimization
#[derive(Debug, Clone)]
pub enum ProgressEvent {
    /// Optimization started
    Started {
        total_examples: usize,
        config: String,
    },
    /// Processing a single example
    ExampleProcessed {
        step: usize,
        total: usize,
        score: f64,
    },
    /// Selection phase started
    SelectionStarted {
        candidate_count: usize,
    },
    /// Demonstrations selected
    DemonstrationsSelected {
        bootstrapped: usize,
        labeled: usize,
    },
    /// Compilation started
    CompilationStarted,
    /// Optimization completed
    Completed {
        score: f64,
        duration_secs: f64,
    },
    /// Error occurred
    Error {
        message: String,
    },
}

// ============================================================================
// Model Metadata
// ============================================================================

/// Metadata for saved compiled models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelMetadata {
    /// Unique model identifier
    pub model_id: String,
    /// Semantic version string
    pub version: String,
    /// ISO 8601 timestamp of creation
    pub created_at: String,
    /// Optimizer used (e.g., "BootstrapFewShot")
    pub optimizer: String,
    /// Base LLM model name
    pub base_model: String,
    /// Number of training examples used
    pub num_training_examples: usize,
    /// Number of demonstrations embedded
    pub num_demonstrations: usize,
    /// Final validation score
    pub validation_score: f64,
    /// Optimization duration in seconds
    pub optimization_duration_secs: f64,
    /// Hyperparameters used
    pub hyperparameters: serde_json::Value,
}

impl ModelMetadata {
    /// Create metadata from optimization result and config
    pub fn from_optimization(
        model_id: String,
        version: String,
        base_model: String,
        result: &OptimizationResult,
        config: &OptimizationConfig,
    ) -> Self {
        Self {
            model_id,
            version,
            created_at: chrono::Utc::now().to_rfc3339(),
            optimizer: "BootstrapFewShot".to_string(),
            base_model,
            num_training_examples: result.num_examples,
            num_demonstrations: result.num_demonstrations,
            validation_score: result.optimization_score,
            optimization_duration_secs: result.duration_secs(),
            hyperparameters: serde_json::json!({
                "max_bootstrapped_demos": config.max_bootstrapped_demos,
                "max_labeled_demos": config.max_labeled_demos,
                "metric_threshold": config.metric_threshold,
                "random_seed": config.random_seed,
            }),
        }
    }
}

// ============================================================================
// Core Optimization Function
// ============================================================================

/// Run BootstrapFewShot optimization from Rust
///
/// # Arguments
/// * `py` - Python interpreter handle
/// * `module` - DSPy module to optimize
/// * `trainset` - Training examples
/// * `metric_fn` - Python metric function for evaluation
/// * `config` - Optimization configuration
///
/// # Returns
/// OptimizationResult containing compiled model and metadata
pub fn run_bootstrap_fewshot(
    py: Python,
    module: &Bound<'_, PyAny>,
    trainset: Vec<TrainingExample>,
    metric_fn: &Bound<'_, PyAny>,
    config: OptimizationConfig,
) -> PyResult<OptimizationResult> {
    let start_time = Instant::now();

    if config.verbose {
        println!("Starting BootstrapFewShot optimization...");
        println!("  Training examples: {}", trainset.len());
        println!("  Max bootstrapped demos: {}", config.max_bootstrapped_demos);
        println!("  Max labeled demos: {}", config.max_labeled_demos);
        println!("  Metric threshold: {:.2}", config.metric_threshold);
    }

    // Import DSPy
    let dspy = PyModule::import_bound(py, "dspy")?;

    let teleprompter_mod = dspy.getattr("teleprompt")?;

    // Create BootstrapFewShot teleprompter
    let kwargs = PyDict::new_bound(py);
    kwargs.set_item("metric", metric_fn)?;
    kwargs.set_item("max_bootstrapped_demos", config.max_bootstrapped_demos)?;
    kwargs.set_item("max_labeled_demos", config.max_labeled_demos)?;

    let bootstrap = teleprompter_mod
        .getattr("BootstrapFewShot")?
        .call((), Some(&kwargs))?;

    // Convert training set to Python list of dspy.Example objects
    let py_trainset = convert_trainset_to_python(py, &trainset)?;

    if config.verbose {
        println!("\nRunning optimization (this may take several minutes)...");
    }

    // Compile the module
    let compiled = bootstrap
        .call_method1("compile", (module, py_trainset))?;

    // Extract optimization metrics
    let score = compiled
        .getattr("optimization_score")
        .ok()
        .and_then(|s| s.extract::<f64>().ok())
        .unwrap_or(0.0);

    let num_demos = compiled
        .getattr("num_demonstrations")
        .ok()
        .and_then(|n| n.extract::<usize>().ok())
        .unwrap_or(config.max_bootstrapped_demos + config.max_labeled_demos);

    let duration = start_time.elapsed();

    if config.verbose {
        println!("\nOptimization complete!");
        println!("  Duration: {:.2}s", duration.as_secs_f64());
        println!("  Score: {:.2}%", score * 100.0);
        println!("  Demonstrations: {}", num_demos);
    }

    Ok(OptimizationResult::new(
        compiled.into(),
        trainset.len(),
        num_demos,
        score,
        duration,
    ))
}

/// Run BootstrapFewShot with progress callback
pub fn run_bootstrap_fewshot_with_progress(
    py: Python,
    module: &Bound<'_, PyAny>,
    trainset: Vec<TrainingExample>,
    metric_fn: &Bound<'_, PyAny>,
    config: OptimizationConfig,
    callback: ProgressCallback,
) -> PyResult<OptimizationResult> {
    // Emit started event
    callback(ProgressEvent::Started {
        total_examples: trainset.len(),
        config: format!("{:?}", config),
    });

    // Run optimization (in production, would wrap Python calls to emit progress)
    let result = run_bootstrap_fewshot(py, module, trainset, metric_fn, config)?;

    // Emit completion event
    callback(ProgressEvent::Completed {
        score: result.optimization_score,
        duration_secs: result.duration_secs(),
    });

    Ok(result)
}

// ============================================================================
// Model Persistence
// ============================================================================

/// Save compiled model with metadata to directory
///
/// Creates two files:
/// - model.json: Serialized DSPy model
/// - metadata.json: Model metadata and hyperparameters
pub fn save_compiled_model<P: AsRef<Path>>(
    _py: Python,
    compiled_model: &Bound<'_, PyAny>,
    metadata: ModelMetadata,
    output_dir: P,
) -> Result<()> {
    let output_path = output_dir.as_ref();

    // Create output directory
    std::fs::create_dir_all(output_path)
        .context("Failed to create output directory")?;

    // Save model using DSPy's save method
    let model_path = output_path.join("model.json");
    compiled_model
        .call_method1("save", (model_path.to_str().unwrap(),))
        .context("Failed to save DSPy model")?;

    // Save metadata
    let metadata_path = output_path.join("metadata.json");
    let metadata_json = serde_json::to_string_pretty(&metadata)
        .context("Failed to serialize metadata")?;
    std::fs::write(&metadata_path, metadata_json)
        .context("Failed to write metadata file")?;

    println!("\nModel saved successfully:");
    println!("  Directory: {}", output_path.display());
    println!("  Model: {}", model_path.display());
    println!("  Metadata: {}", metadata_path.display());

    Ok(())
}

/// Load compiled model with metadata from directory
pub fn load_compiled_model<P: AsRef<Path>>(
    py: Python,
    model_dir: P,
) -> Result<(Py<PyAny>, ModelMetadata)> {
    let model_path = model_dir.as_ref();

    // Load metadata
    let metadata_path = model_path.join("metadata.json");
    let metadata_json = std::fs::read_to_string(&metadata_path)
        .context("Failed to read metadata file")?;
    let metadata: ModelMetadata = serde_json::from_str(&metadata_json)
        .context("Failed to parse metadata JSON")?;

    // Load model
    let model_file = model_path.join("model.json");
    let dspy = PyModule::import_bound(py, "dspy")
        .context("Failed to import dspy")?;

    let model = dspy
        .call_method1("load", (model_file.to_str().unwrap(),))
        .context("Failed to load DSPy model")?;

    println!("Model loaded: {} v{}", metadata.model_id, metadata.version);
    println!("  Score: {:.2}%", metadata.validation_score * 100.0);
    println!("  Demonstrations: {}", metadata.num_demonstrations);

    Ok((model.into(), metadata))
}

// ============================================================================
// Metric Functions
// ============================================================================

/// Create a simple accuracy metric function
pub fn create_accuracy_metric(py: Python) -> PyResult<Py<PyAny>> {
    let code = r#"
def accuracy_metric(example, prediction, trace=None):
    """Check if prediction matches expected answer (case-insensitive)"""
    if hasattr(prediction, 'answer'):
        pred = prediction.answer.lower().strip()
    else:
        pred = str(prediction).lower().strip()

    if hasattr(example, 'answer'):
        expected = example.answer.lower().strip()
    else:
        expected = str(example).lower().strip()

    return pred == expected
"#;

    py.run_bound(code, None, None)?;
    let locals = py.eval_bound("locals()", None, None)?;
    let metric = locals.get_item("accuracy_metric")?;
    Ok(metric.unbind())
}

/// Create an exact match metric (stricter than accuracy)
pub fn create_exact_match_metric(py: Python) -> PyResult<Py<PyAny>> {
    let code = r#"
def exact_match_metric(example, prediction, trace=None):
    """Check if prediction exactly matches expected answer"""
    if hasattr(prediction, 'answer'):
        pred = prediction.answer.strip()
    else:
        pred = str(prediction).strip()

    if hasattr(example, 'answer'):
        expected = example.answer.strip()
    else:
        expected = str(example).strip()

    return pred == expected
"#;

    py.run_bound(code, None, None)?;
    let locals = py.eval_bound("locals()", None, None)?;
    let metric = locals.get_item("exact_match_metric")?;
    Ok(metric.unbind())
}

// ============================================================================
// Helper Functions
// ============================================================================

/// Convert Rust training examples to Python list of dspy.Example objects
fn convert_trainset_to_python(
    py: Python,
    trainset: &[TrainingExample],
) -> PyResult<Py<PyList>> {
    let dspy = PyModule::import_bound(py, "dspy")?;
    let example_class = dspy.getattr("Example")?;

    let py_list = PyList::empty_bound(py);

    for example in trainset {
        let kwargs = PyDict::new_bound(py);
        kwargs.set_item("question", &example.question)?;
        kwargs.set_item("answer", &example.answer)?;

        let py_example = example_class.call((), Some(&kwargs))?;
        py_list.append(py_example)?;
    }

    Ok(py_list.unbind())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_training_dataset_split() {
        let examples = vec![
            TrainingExample {
                question: "Q1".to_string(),
                answer: "A1".to_string(),
            },
            TrainingExample {
                question: "Q2".to_string(),
                answer: "A2".to_string(),
            },
            TrainingExample {
                question: "Q3".to_string(),
                answer: "A3".to_string(),
            },
            TrainingExample {
                question: "Q4".to_string(),
                answer: "A4".to_string(),
            },
        ];

        let dataset = TrainingDataset::new("test".to_string(), examples);
        let (train, val) = dataset.split(0.75);

        assert_eq!(train.len(), 3);
        assert_eq!(val.len(), 1);
    }

    #[test]
    fn test_optimization_config_builder() {
        let config = OptimizationConfig::new()
            .with_max_bootstrapped_demos(8)
            .with_max_labeled_demos(4)
            .with_metric_threshold(0.85)
            .with_verbose(false)
            .with_random_seed(42);

        assert_eq!(config.max_bootstrapped_demos, 8);
        assert_eq!(config.max_labeled_demos, 4);
        assert_eq!(config.metric_threshold, 0.85);
        assert!(!config.verbose);
        assert_eq!(config.random_seed, Some(42));
    }
}
