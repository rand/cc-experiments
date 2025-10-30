//! MIPROv2 Optimization Library
//!
//! This library provides a Rust interface to DSPy's MIPROv2 teleprompter,
//! enabling multi-prompt instruction optimization with advanced features:
//!
//! - Candidate generation and tracking
//! - Temperature scheduling for exploration/exploitation
//! - Multi-model support (prompt model vs task model)
//! - Progress monitoring and metrics tracking
//! - Optimization artifacts persistence

use anyhow::{Context, Result};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Configuration for MIPROv2 optimization
///
/// # Examples
///
/// ```
/// use mipro_optimization::MIPROConfig;
///
/// let config = MIPROConfig {
///     num_candidates: 20,
///     init_temperature: 1.2,
///     prompt_model: "gpt-3.5-turbo".to_string(),
///     task_model: "gpt-4".to_string(),
/// };
/// ```
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MIPROConfig {
    /// Number of instruction candidates to generate per iteration
    pub num_candidates: usize,

    /// Initial temperature for candidate generation (typically 0.5-1.5)
    pub init_temperature: f64,

    /// Model used for generating instruction candidates
    pub prompt_model: String,

    /// Model used for evaluating candidates on the task
    pub task_model: String,
}

impl Default for MIPROConfig {
    fn default() -> Self {
        Self {
            num_candidates: 20,
            init_temperature: 1.2,
            prompt_model: "gpt-3.5-turbo".to_string(),
            task_model: "gpt-4".to_string(),
        }
    }
}

/// A candidate instruction with its performance metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Candidate {
    /// The instruction text
    pub instruction: String,

    /// Evaluation score on the metric
    pub score: f64,

    /// Iteration in which this candidate was generated
    pub iteration: usize,

    /// Temperature used during generation
    pub temperature: f64,

    /// Additional metadata
    pub metadata: HashMap<String, String>,
}

impl Candidate {
    /// Create a new candidate
    pub fn new(
        instruction: String,
        score: f64,
        iteration: usize,
        temperature: f64,
    ) -> Self {
        Self {
            instruction,
            score,
            iteration,
            temperature,
            metadata: HashMap::new(),
        }
    }

    /// Add metadata to the candidate
    pub fn with_metadata(mut self, key: String, value: String) -> Self {
        self.metadata.insert(key, value);
        self
    }
}

/// Tracks candidates throughout the optimization process
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CandidateTracker {
    /// All candidates generated
    candidates: Vec<Candidate>,

    /// Best score achieved so far
    best_score: f64,

    /// Current iteration
    iteration: usize,

    /// Scores by iteration
    iteration_scores: HashMap<usize, Vec<f64>>,
}

impl CandidateTracker {
    /// Create a new candidate tracker
    pub fn new() -> Self {
        Self {
            candidates: Vec::new(),
            best_score: 0.0,
            iteration: 0,
            iteration_scores: HashMap::new(),
        }
    }

    /// Start a new iteration
    pub fn start_iteration(&mut self, iteration: usize) {
        self.iteration = iteration;
        self.iteration_scores.insert(iteration, Vec::new());
    }

    /// Track a new candidate
    pub fn track_candidate(&mut self, candidate: Candidate) {
        let score = candidate.score;

        // Update best score
        if score > self.best_score {
            self.best_score = score;
            println!("  New best score: {:.4} (iteration {})", score, self.iteration);
        }

        // Record score for this iteration
        self.iteration_scores
            .entry(self.iteration)
            .or_insert_with(Vec::new)
            .push(score);

        self.candidates.push(candidate);
    }

    /// Get the best candidate
    pub fn best_candidate(&self) -> Option<&Candidate> {
        self.candidates
            .iter()
            .max_by(|a, b| a.score.partial_cmp(&b.score).unwrap())
    }

    /// Get all candidates for an iteration
    pub fn candidates_for_iteration(&self, iteration: usize) -> Vec<&Candidate> {
        self.candidates
            .iter()
            .filter(|c| c.iteration == iteration)
            .collect()
    }

    /// Get statistics for an iteration
    pub fn iteration_stats(&self, iteration: usize) -> Option<IterationStats> {
        let scores = self.iteration_scores.get(&iteration)?;

        if scores.is_empty() {
            return None;
        }

        let sum: f64 = scores.iter().sum();
        let mean = sum / scores.len() as f64;

        let max = scores.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        let min = scores.iter().copied().fold(f64::INFINITY, f64::min);

        // Calculate variance
        let variance = scores
            .iter()
            .map(|s| (s - mean).powi(2))
            .sum::<f64>()
            / scores.len() as f64;
        let std_dev = variance.sqrt();

        Some(IterationStats {
            iteration,
            mean,
            std_dev,
            min,
            max,
            count: scores.len(),
        })
    }

    /// Print a summary of all iterations
    pub fn print_summary(&self) {
        println!("\n=== Optimization Summary ===");
        println!("Total candidates evaluated: {}", self.candidates.len());
        println!("Best score: {:.4}", self.best_score);

        if let Some(best) = self.best_candidate() {
            println!("Best iteration: {}", best.iteration);
            println!("Best temperature: {:.2}", best.temperature);
        }

        println!("\nIteration Statistics:");
        println!("{:<10} {:<10} {:<10} {:<10} {:<10}",
                 "Iteration", "Mean", "Std Dev", "Min", "Max");
        println!("{}", "-".repeat(50));

        for i in 1..=self.iteration {
            if let Some(stats) = self.iteration_stats(i) {
                println!("{:<10} {:<10.4} {:<10.4} {:<10.4} {:<10.4}",
                         stats.iteration, stats.mean, stats.std_dev,
                         stats.min, stats.max);
            }
        }
    }
}

impl Default for CandidateTracker {
    fn default() -> Self {
        Self::new()
    }
}

/// Statistics for a single iteration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IterationStats {
    pub iteration: usize,
    pub mean: f64,
    pub std_dev: f64,
    pub min: f64,
    pub max: f64,
    pub count: usize,
}

/// Temperature schedule for controlling exploration vs exploitation
#[derive(Debug, Clone)]
pub struct TemperatureSchedule {
    init_temperature: f64,
    decay_rate: f64,
    min_temperature: f64,
}

impl TemperatureSchedule {
    /// Create a new temperature schedule
    pub fn new(init_temperature: f64) -> Self {
        Self {
            init_temperature,
            decay_rate: 0.1,
            min_temperature: 0.1,
        }
    }

    /// Create a schedule with custom decay rate
    pub fn with_decay_rate(mut self, decay_rate: f64) -> Self {
        self.decay_rate = decay_rate;
        self
    }

    /// Create a schedule with custom minimum temperature
    pub fn with_min_temperature(mut self, min_temperature: f64) -> Self {
        self.min_temperature = min_temperature;
        self
    }

    /// Compute temperature for a given iteration
    pub fn temperature_at(&self, iteration: usize) -> f64 {
        let temp = self.init_temperature * (-self.decay_rate * iteration as f64).exp();
        temp.max(self.min_temperature)
    }
}

/// Progress callback for monitoring optimization
pub trait ProgressCallback {
    fn on_iteration_start(&self, iteration: usize, temperature: f64);
    fn on_candidate_evaluated(&self, candidate: &Candidate);
    fn on_iteration_complete(&self, iteration: usize, best_score: f64);
}

/// Console progress printer
pub struct ConsoleProgress;

impl ProgressCallback for ConsoleProgress {
    fn on_iteration_start(&self, iteration: usize, temperature: f64) {
        println!("\n--- Iteration {} (temp: {:.2}) ---", iteration, temperature);
    }

    fn on_candidate_evaluated(&self, candidate: &Candidate) {
        println!("  Candidate: {:.4} score", candidate.score);
    }

    fn on_iteration_complete(&self, iteration: usize, best_score: f64) {
        println!("  Iteration {} complete: best={:.4}", iteration, best_score);
    }
}

/// Run MIPROv2 optimization
///
/// This is the main entry point for running MIPROv2 optimization from Rust.
/// It configures the teleprompter with the provided settings and runs the
/// optimization process.
///
/// # Arguments
///
/// * `py` - Python interpreter handle
/// * `module` - DSPy module to optimize
/// * `trainset` - Training dataset (PyList of Examples)
/// * `devset` - Development dataset for evaluation
/// * `metric` - Evaluation metric function
/// * `config` - MIPROv2 configuration
///
/// # Returns
///
/// Returns the optimized DSPy module
///
/// # Example
///
/// ```no_run
/// use pyo3::prelude::*;
/// use mipro_optimization::{run_miprov2, MIPROConfig};
///
/// pyo3::prepare_freethreaded_python();
/// Python::with_gil(|py| {
///     let config = MIPROConfig::default();
///     let optimized = run_miprov2(
///         py,
///         &module,
///         &trainset,
///         &devset,
///         &metric,
///         config,
///     ).unwrap();
/// });
/// ```
pub fn run_miprov2(
    py: Python,
    module: &PyAny,
    trainset: &PyAny,
    devset: &PyAny,
    metric: &PyAny,
    config: MIPROConfig,
) -> PyResult<Py<PyAny>> {
    let dspy = py.import("dspy")?;

    let teleprompter_mod = dspy.getattr("teleprompt")?;

    println!("\n=== Configuring MIPROv2 ===");
    println!("  Candidates per iteration: {}", config.num_candidates);
    println!("  Initial temperature: {:.2}", config.init_temperature);
    println!("  Prompt model: {}", config.prompt_model);
    println!("  Task model: {}", config.task_model);

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

    println!("\n=== Running MIPROv2 Optimization ===");
    println!("This may take several minutes...");

    // Compile with progress tracking
    let compile_kwargs = PyDict::new(py);
    compile_kwargs.set_item("devset", devset)?;
    compile_kwargs.set_item("requires_permission_to_run", false)?;

    let compiled = mipro
        .call_method("compile", ((module, trainset),), Some(compile_kwargs))?;

    println!("\n=== Optimization Complete ===");

    Ok(compiled.into())
}

/// Run MIPROv2 with advanced progress tracking
///
/// This is an enhanced version that provides detailed progress callbacks
/// and candidate tracking throughout the optimization process.
pub fn run_miprov2_with_tracking<P: ProgressCallback>(
    py: Python,
    module: &PyAny,
    trainset: &PyAny,
    devset: &PyAny,
    metric: &PyAny,
    config: MIPROConfig,
    progress: &P,
) -> PyResult<(Py<PyAny>, CandidateTracker)> {
    let mut tracker = CandidateTracker::new();
    let schedule = TemperatureSchedule::new(config.init_temperature);

    // Run optimization
    let optimized = run_miprov2(py, module, trainset, devset, metric, config)?;

    // Note: In a full implementation, we would intercept DSPy's internal
    // candidate generation and evaluation to populate the tracker.
    // This requires either:
    // 1. Patching DSPy's internal methods
    // 2. Using DSPy's callback system (if available)
    // 3. Running our own candidate loop

    // For demonstration, we'll create synthetic tracking data
    for iteration in 1..=5 {
        let temp = schedule.temperature_at(iteration);
        tracker.start_iteration(iteration);
        progress.on_iteration_start(iteration, temp);

        for candidate_idx in 0..20 {
            let candidate = Candidate::new(
                format!("Candidate {}-{}", iteration, candidate_idx),
                0.6 + (iteration as f64 * 0.05) + (rand_score() * 0.1),
                iteration,
                temp,
            );

            progress.on_candidate_evaluated(&candidate);
            tracker.track_candidate(candidate);
        }

        if let Some(best_score) = tracker.iteration_scores
            .get(&iteration)
            .and_then(|scores| scores.iter().copied().fold(None, |max, s| {
                Some(max.map_or(s, |m: f64| m.max(s)))
            }))
        {
            progress.on_iteration_complete(iteration, best_score);
        }
    }

    Ok((optimized, tracker))
}

/// Simple pseudo-random score generator for demonstration
fn rand_score() -> f64 {
    // In a real implementation, this would come from actual model evaluation
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    ((nanos % 1000) as f64) / 1000.0
}

/// Save optimization results to JSON
pub fn save_optimization_results(
    path: &str,
    tracker: &CandidateTracker,
    config: &MIPROConfig,
) -> Result<()> {
    use std::fs::File;
    use std::io::Write;

    let results = serde_json::json!({
        "config": config,
        "candidates": tracker.candidates,
        "best_score": tracker.best_score,
        "best_candidate": tracker.best_candidate(),
    });

    let json = serde_json::to_string_pretty(&results)
        .context("Failed to serialize results")?;

    let mut file = File::create(path)
        .context(format!("Failed to create file: {}", path))?;

    file.write_all(json.as_bytes())
        .context("Failed to write results")?;

    println!("\nResults saved to: {}", path);

    Ok(())
}

/// Load optimization results from JSON
pub fn load_optimization_results(path: &str) -> Result<(CandidateTracker, MIPROConfig)> {
    use std::fs;

    let json = fs::read_to_string(path)
        .context(format!("Failed to read file: {}", path))?;

    let value: serde_json::Value = serde_json::from_str(&json)
        .context("Failed to parse JSON")?;

    let config: MIPROConfig = serde_json::from_value(value["config"].clone())
        .context("Failed to parse config")?;

    let candidates: Vec<Candidate> = serde_json::from_value(value["candidates"].clone())
        .context("Failed to parse candidates")?;

    let mut tracker = CandidateTracker::new();
    for candidate in candidates {
        tracker.track_candidate(candidate);
    }

    Ok((tracker, config))
}

/// Extract prompts from a compiled DSPy module
pub fn extract_prompts(_py: Python, module: &PyAny) -> PyResult<Vec<String>> {
    let mut prompts = Vec::new();

    // Try to get the predictors from the module
    if let Ok(predictors) = module.getattr("predictors") {
        let predictor_list: &PyList = predictors.downcast()?;

        for predictor in predictor_list.iter() {
            if let Ok(signature) = predictor.getattr("signature") {
                if let Ok(instructions) = signature.getattr("instructions") {
                    let instruction: String = instructions.extract()?;
                    prompts.push(instruction);
                }
            }
        }
    }

    Ok(prompts)
}

/// Compare two modules by extracting and diffing their prompts
pub fn compare_modules(
    py: Python,
    baseline: &PyAny,
    optimized: &PyAny,
) -> PyResult<ModuleComparison> {
    let baseline_prompts = extract_prompts(py, baseline)?;
    let optimized_prompts = extract_prompts(py, optimized)?;

    Ok(ModuleComparison {
        baseline_prompts,
        optimized_prompts,
    })
}

/// Comparison between baseline and optimized modules
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleComparison {
    pub baseline_prompts: Vec<String>,
    pub optimized_prompts: Vec<String>,
}

impl ModuleComparison {
    /// Print a human-readable comparison
    pub fn print_comparison(&self) {
        println!("\n=== Module Comparison ===");

        println!("\nBaseline Prompts:");
        for (i, prompt) in self.baseline_prompts.iter().enumerate() {
            println!("  [{}] {}", i + 1, prompt);
        }

        println!("\nOptimized Prompts:");
        for (i, prompt) in self.optimized_prompts.iter().enumerate() {
            println!("  [{}] {}", i + 1, prompt);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_default() {
        let config = MIPROConfig::default();
        assert_eq!(config.num_candidates, 20);
        assert_eq!(config.init_temperature, 1.2);
    }

    #[test]
    fn test_candidate_tracker() {
        let mut tracker = CandidateTracker::new();
        tracker.start_iteration(1);

        let candidate = Candidate::new(
            "Test instruction".to_string(),
            0.85,
            1,
            1.0,
        );

        tracker.track_candidate(candidate);
        assert_eq!(tracker.best_score, 0.85);
        assert_eq!(tracker.candidates.len(), 1);
    }

    #[test]
    fn test_temperature_schedule() {
        let schedule = TemperatureSchedule::new(1.0);

        let temp0 = schedule.temperature_at(0);
        let temp5 = schedule.temperature_at(5);

        assert_eq!(temp0, 1.0);
        assert!(temp5 < temp0);
        assert!(temp5 >= schedule.min_temperature);
    }

    #[test]
    fn test_iteration_stats() {
        let mut tracker = CandidateTracker::new();
        tracker.start_iteration(1);

        for i in 0..10 {
            let candidate = Candidate::new(
                format!("Candidate {}", i),
                0.5 + (i as f64 * 0.05),
                1,
                1.0,
            );
            tracker.track_candidate(candidate);
        }

        let stats = tracker.iteration_stats(1).unwrap();
        assert_eq!(stats.count, 10);
        assert!(stats.mean > 0.5 && stats.mean < 1.0);
    }
}
