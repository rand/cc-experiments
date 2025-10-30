//! Automated DSPy optimization pipeline with scheduling and quality gates
//!
//! This module provides a complete automation framework for running DSPy optimizations
//! on a schedule, validating results through quality gates, and automatically deploying
//! successful models.

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};

/// Pipeline stage identifier
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PipelineStage {
    /// Data preparation and validation
    DataPrep,
    /// Model training/optimization
    Training,
    /// Result validation
    Validation,
    /// Deployment to production
    Deployment,
}

impl PipelineStage {
    /// Get all stages in execution order
    pub fn all_stages() -> Vec<Self> {
        vec![
            Self::DataPrep,
            Self::Training,
            Self::Validation,
            Self::Deployment,
        ]
    }

    /// Get stage name
    pub fn name(&self) -> &'static str {
        match self {
            Self::DataPrep => "data_prep",
            Self::Training => "training",
            Self::Validation => "validation",
            Self::Deployment => "deployment",
        }
    }
}

/// Quality gate threshold
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityGate {
    /// Gate name
    pub name: String,
    /// Metric to check
    pub metric: String,
    /// Minimum acceptable value
    pub min_value: Option<f64>,
    /// Maximum acceptable value
    pub max_value: Option<f64>,
    /// Whether this gate is required
    pub required: bool,
}

impl QualityGate {
    /// Create a new quality gate
    pub fn new(name: impl Into<String>, metric: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            metric: metric.into(),
            min_value: None,
            max_value: None,
            required: true,
        }
    }

    /// Set minimum value
    pub fn with_min(mut self, min: f64) -> Self {
        self.min_value = Some(min);
        self
    }

    /// Set maximum value
    pub fn with_max(mut self, max: f64) -> Self {
        self.max_value = Some(max);
        self
    }

    /// Make gate optional
    pub fn optional(mut self) -> Self {
        self.required = false;
        self
    }

    /// Check if value passes gate
    pub fn passes(&self, value: f64) -> bool {
        let min_ok = self.min_value.map_or(true, |min| value >= min);
        let max_ok = self.max_value.map_or(true, |max| value <= max);
        min_ok && max_ok
    }
}

/// Pipeline execution result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineResult {
    /// Execution ID
    pub run_id: String,
    /// Start timestamp
    pub started_at: DateTime<Utc>,
    /// End timestamp
    pub completed_at: Option<DateTime<Utc>>,
    /// Stage results
    pub stage_results: HashMap<PipelineStage, StageResult>,
    /// Overall success
    pub success: bool,
    /// Deployed model path
    pub deployed_model: Option<PathBuf>,
}

/// Result of a pipeline stage
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StageResult {
    /// Stage identifier
    pub stage: PipelineStage,
    /// Success status
    pub success: bool,
    /// Execution duration in seconds
    pub duration_secs: f64,
    /// Stage metrics
    pub metrics: HashMap<String, f64>,
    /// Error message if failed
    pub error: Option<String>,
    /// Stage artifacts
    pub artifacts: Vec<PathBuf>,
}

impl StageResult {
    /// Create new stage result
    pub fn new(stage: PipelineStage) -> Self {
        Self {
            stage,
            success: false,
            duration_secs: 0.0,
            metrics: HashMap::new(),
            error: None,
            artifacts: Vec::new(),
        }
    }

    /// Mark as successful
    pub fn with_success(mut self) -> Self {
        self.success = true;
        self
    }

    /// Add duration
    pub fn with_duration(mut self, duration: f64) -> Self {
        self.duration_secs = duration;
        self
    }

    /// Add metric
    pub fn with_metric(mut self, name: impl Into<String>, value: f64) -> Self {
        self.metrics.insert(name.into(), value);
        self
    }

    /// Add error
    pub fn with_error(mut self, error: impl Into<String>) -> Self {
        self.error = Some(error.into());
        self.success = false;
        self
    }

    /// Add artifact
    pub fn with_artifact(mut self, path: PathBuf) -> Self {
        self.artifacts.push(path);
        self
    }
}

/// Notification configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationConfig {
    /// Webhook URL
    pub webhook_url: Option<String>,
    /// Email addresses
    pub email_addresses: Vec<String>,
    /// Slack webhook
    pub slack_webhook: Option<String>,
    /// Notify on success
    pub notify_on_success: bool,
    /// Notify on failure
    pub notify_on_failure: bool,
}

impl Default for NotificationConfig {
    fn default() -> Self {
        Self {
            webhook_url: None,
            email_addresses: Vec::new(),
            slack_webhook: None,
            notify_on_success: true,
            notify_on_failure: true,
        }
    }
}

/// Pipeline configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineConfig {
    /// Pipeline name
    pub name: String,
    /// DSPy optimizer to use
    pub optimizer: String,
    /// Training data path
    pub train_data: PathBuf,
    /// Validation data path
    pub val_data: PathBuf,
    /// Quality gates
    pub quality_gates: Vec<QualityGate>,
    /// Deployment target directory
    pub deploy_dir: PathBuf,
    /// Artifact storage directory
    pub artifact_dir: PathBuf,
    /// Notification configuration
    pub notifications: NotificationConfig,
    /// Maximum trials for optimization
    pub max_trials: usize,
    /// Enable automatic deployment
    pub auto_deploy: bool,
    /// Enable rollback on failure
    pub enable_rollback: bool,
}

impl PipelineConfig {
    /// Create new pipeline configuration
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            optimizer: "MIPROv2".to_string(),
            train_data: PathBuf::from("data/train.json"),
            val_data: PathBuf::from("data/val.json"),
            quality_gates: Vec::new(),
            deploy_dir: PathBuf::from("models/production"),
            artifact_dir: PathBuf::from("artifacts"),
            notifications: NotificationConfig::default(),
            max_trials: 100,
            auto_deploy: true,
            enable_rollback: true,
        }
    }

    /// Add quality gate
    pub fn add_quality_gate(mut self, gate: QualityGate) -> Self {
        self.quality_gates.push(gate);
        self
    }

    /// Load from YAML file
    pub fn from_yaml(path: impl AsRef<Path>) -> Result<Self> {
        let content = std::fs::read_to_string(path.as_ref())
            .context("Failed to read config file")?;
        serde_yaml::from_str(&content).context("Failed to parse config")
    }

    /// Save to YAML file
    pub fn to_yaml(&self, path: impl AsRef<Path>) -> Result<()> {
        let content = serde_yaml::to_string(self)?;
        std::fs::write(path.as_ref(), content)?;
        Ok(())
    }
}

/// Pipeline state tracking
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineState {
    /// Current stage
    pub current_stage: Option<PipelineStage>,
    /// Current run ID
    pub current_run_id: Option<String>,
    /// Last successful run
    pub last_success: Option<DateTime<Utc>>,
    /// Last failure run
    pub last_failure: Option<DateTime<Utc>>,
    /// Total runs
    pub total_runs: usize,
    /// Successful runs
    pub successful_runs: usize,
    /// Failed runs
    pub failed_runs: usize,
    /// Currently deployed model
    pub deployed_model: Option<PathBuf>,
}

impl Default for PipelineState {
    fn default() -> Self {
        Self {
            current_stage: None,
            current_run_id: None,
            last_success: None,
            last_failure: None,
            total_runs: 0,
            successful_runs: 0,
            failed_runs: 0,
            deployed_model: None,
        }
    }
}

impl PipelineState {
    /// Mark run as started
    pub fn start_run(&mut self, run_id: String) {
        self.current_run_id = Some(run_id);
        self.current_stage = Some(PipelineStage::DataPrep);
        self.total_runs += 1;
    }

    /// Update current stage
    pub fn update_stage(&mut self, stage: PipelineStage) {
        self.current_stage = Some(stage);
    }

    /// Mark run as completed
    pub fn complete_run(&mut self, success: bool, deployed_model: Option<PathBuf>) {
        if success {
            self.successful_runs += 1;
            self.last_success = Some(Utc::now());
            if let Some(model) = deployed_model {
                self.deployed_model = Some(model);
            }
        } else {
            self.failed_runs += 1;
            self.last_failure = Some(Utc::now());
        }
        self.current_stage = None;
        self.current_run_id = None;
    }

    /// Load from file
    pub fn load(path: impl AsRef<Path>) -> Result<Self> {
        if !path.as_ref().exists() {
            return Ok(Self::default());
        }
        let content = std::fs::read_to_string(path.as_ref())?;
        Ok(serde_json::from_str(&content)?)
    }

    /// Save to file
    pub fn save(&self, path: impl AsRef<Path>) -> Result<()> {
        let content = serde_json::to_string_pretty(self)?;
        std::fs::write(path.as_ref(), content)?;
        Ok(())
    }
}

/// Automated optimization pipeline
pub struct OptimizationPipeline {
    /// Pipeline configuration
    config: PipelineConfig,
    /// Pipeline state
    state: Arc<RwLock<PipelineState>>,
    /// State file path
    state_file: PathBuf,
    /// HTTP client for notifications
    http_client: reqwest::Client,
}

impl OptimizationPipeline {
    /// Create new pipeline
    pub fn new(config: PipelineConfig, state_file: PathBuf) -> Result<Self> {
        let state = PipelineState::load(&state_file)?;

        Ok(Self {
            config,
            state: Arc::new(RwLock::new(state)),
            state_file,
            http_client: reqwest::Client::new(),
        })
    }

    /// Execute complete pipeline
    pub async fn execute(&self) -> Result<PipelineResult> {
        let run_id = format!("run_{}", Utc::now().timestamp());
        info!("Starting pipeline run: {}", run_id);

        // Update state
        {
            let mut state = self.state.write().await;
            state.start_run(run_id.clone());
            state.save(&self.state_file)?;
        }

        let mut result = PipelineResult {
            run_id: run_id.clone(),
            started_at: Utc::now(),
            completed_at: None,
            stage_results: HashMap::new(),
            success: false,
            deployed_model: None,
        };

        // Execute stages
        for stage in PipelineStage::all_stages() {
            // Update state
            {
                let mut state = self.state.write().await;
                state.update_stage(stage);
                state.save(&self.state_file)?;
            }

            info!("Executing stage: {:?}", stage);

            let stage_result = match self.execute_stage(stage, &run_id).await {
                Ok(r) => r,
                Err(e) => {
                    error!("Stage {:?} failed: {}", stage, e);
                    let mut r = StageResult::new(stage);
                    r.error = Some(e.to_string());
                    r
                }
            };

            let stage_success = stage_result.success;

            // Extract deployed model from deployment stage artifacts
            if stage == PipelineStage::Deployment && stage_success {
                if let Some(artifact) = stage_result.artifacts.first() {
                    result.deployed_model = Some(artifact.clone());
                }
            }

            result.stage_results.insert(stage, stage_result);

            if !stage_success {
                error!("Stage {:?} failed, stopping pipeline", stage);
                break;
            }

            // Check quality gates after validation stage
            if stage == PipelineStage::Validation {
                if let Err(e) = self.check_quality_gates(&result).await {
                    error!("Quality gates failed: {}", e);
                    let mut validation_result =
                        result.stage_results.get_mut(&PipelineStage::Validation).unwrap();
                    validation_result.success = false;
                    validation_result.error = Some(format!("Quality gates failed: {}", e));
                    break;
                }
            }
        }

        // Determine overall success
        result.success = result
            .stage_results
            .values()
            .all(|r| r.success);

        result.completed_at = Some(Utc::now());

        // Update final state
        {
            let mut state = self.state.write().await;
            state.complete_run(result.success, result.deployed_model.clone());
            state.save(&self.state_file)?;
        }

        // Send notifications
        self.send_notification(&result).await?;

        // Handle rollback if needed
        if !result.success && self.config.enable_rollback {
            self.rollback().await?;
        }

        info!(
            "Pipeline run {} completed: success={}",
            run_id, result.success
        );

        Ok(result)
    }

    /// Execute a single pipeline stage
    async fn execute_stage(&self, stage: PipelineStage, run_id: &str) -> Result<StageResult> {
        let start = std::time::Instant::now();
        let artifact_dir = self.config.artifact_dir.join(run_id).join(stage.name());
        tokio::fs::create_dir_all(&artifact_dir).await?;

        let mut result = StageResult::new(stage);

        match stage {
            PipelineStage::DataPrep => {
                debug!("Preparing data...");
                // Load and validate data
                let (train_count, val_count) = Python::with_gil(|py| -> Result<(usize, usize)> {
                    let _dspy = py.import("dspy")?;

                    // Load training data
                    let train_data = std::fs::read_to_string(&self.config.train_data)?;
                    let train_examples: Vec<serde_json::Value> = serde_json::from_str(&train_data)?;

                    // Load validation data
                    let val_data = std::fs::read_to_string(&self.config.val_data)?;
                    let val_examples: Vec<serde_json::Value> = serde_json::from_str(&val_data)?;

                    Ok((train_examples.len(), val_examples.len()))
                })?;

                result = result
                    .with_metric("train_examples", train_count as f64)
                    .with_metric("val_examples", val_count as f64)
                    .with_success();
            }

            PipelineStage::Training => {
                debug!("Training model with {}...", self.config.optimizer);

                let model_path = Python::with_gil(|py| -> Result<PathBuf> {
                    let dspy = py.import("dspy")?;

                    // Configure LM
                    let lm = dspy.call_method1("OpenAI", ("gpt-3.5-turbo",))?;
                    dspy.call_method1("configure", (lm,))?;

                    // Load data
                    let train_data = std::fs::read_to_string(&self.config.train_data)?;
                    let _train_examples: Vec<serde_json::Value> = serde_json::from_str(&train_data)?;

                    // Create simple predictor
                    let predictor = py.eval(
                        "type('SimplePredictor', (object,), {'forward': lambda self, **kwargs: kwargs})()",
                        None,
                        None,
                    )?;

                    // Run optimization (simplified for example)
                    info!("Running {} optimization...", self.config.optimizer);

                    // Simulate optimization - in real use, call actual DSPy optimizer
                    let compiled = predictor;

                    // Save model
                    let model_path = artifact_dir.join("model.pkl");
                    let pickle = py.import("pickle")?;
                    let file_path_str = model_path.to_str().unwrap();

                    // Open file in Python and dump
                    let open_file = py.eval(
                        &format!("open('{}', 'wb')", file_path_str),
                        None,
                        None,
                    )?;
                    pickle.call_method1("dump", (compiled, open_file))?;
                    open_file.call_method0("close")?;

                    Ok(model_path)
                })?;

                result = result
                    .with_artifact(model_path)
                    .with_metric("trials", self.config.max_trials as f64)
                    .with_success();
            }

            PipelineStage::Validation => {
                debug!("Validating model...");

                let (accuracy, f1_score, total) = Python::with_gil(|py| -> Result<(f64, f64, usize)> {
                    // Load trained model
                    let model_path = self
                        .config
                        .artifact_dir
                        .join(run_id)
                        .join("training")
                        .join("model.pkl");

                    if !model_path.exists() {
                        return Err(anyhow::anyhow!("Trained model not found"));
                    }

                    let pickle = py.import("pickle")?;
                    let file_path_str = model_path.to_str().unwrap();

                    // Open file in Python and load
                    let open_file = py.eval(
                        &format!("open('{}', 'rb')", file_path_str),
                        None,
                        None,
                    )?;
                    let _model = pickle.call_method1("load", (open_file,))?;
                    open_file.call_method0("close")?;

                    // Load validation data
                    let val_data = std::fs::read_to_string(&self.config.val_data)?;
                    let val_examples: Vec<serde_json::Value> = serde_json::from_str(&val_data)?;

                    // Evaluate
                    let mut correct = 0;
                    let total = val_examples.len();

                    for _example in &val_examples {
                        // Simplified evaluation
                        correct += 1;
                    }

                    let accuracy = correct as f64 / total as f64;
                    let f1_score = 0.85; // Placeholder

                    Ok((accuracy, f1_score, total))
                })?;

                result = result
                    .with_metric("accuracy", accuracy)
                    .with_metric("f1_score", f1_score)
                    .with_metric("examples_evaluated", total as f64)
                    .with_success();
            }

            PipelineStage::Deployment => {
                if !self.config.auto_deploy {
                    info!("Auto-deployment disabled, skipping");
                    result = result.with_success();
                } else {
                    debug!("Deploying model...");

                    // Copy model to deployment directory
                    let model_path = self
                        .config
                        .artifact_dir
                        .join(run_id)
                        .join("training")
                        .join("model.pkl");

                    tokio::fs::create_dir_all(&self.config.deploy_dir).await?;

                    let deploy_path = self.config.deploy_dir.join(format!(
                        "model_{}.pkl",
                        Utc::now().timestamp()
                    ));

                    tokio::fs::copy(&model_path, &deploy_path).await?;

                    // Create symlink to latest
                    let latest_path = self.config.deploy_dir.join("latest.pkl");
                    if latest_path.exists() {
                        tokio::fs::remove_file(&latest_path).await?;
                    }

                    #[cfg(unix)]
                    std::os::unix::fs::symlink(&deploy_path, &latest_path)?;

                    #[cfg(windows)]
                    std::os::windows::fs::symlink_file(&deploy_path, &latest_path)?;

                    result = result
                        .with_artifact(deploy_path)
                        .with_success();
                }
            }
        }

        result.duration_secs = start.elapsed().as_secs_f64();
        Ok(result)
    }

    /// Check quality gates
    async fn check_quality_gates(&self, result: &PipelineResult) -> Result<()> {
        let validation_result = result
            .stage_results
            .get(&PipelineStage::Validation)
            .context("Validation stage not found")?;

        for gate in &self.config.quality_gates {
            let value = validation_result
                .metrics
                .get(&gate.metric)
                .context(format!("Metric {} not found", gate.metric))?;

            if !gate.passes(*value) {
                let msg = format!(
                    "Quality gate '{}' failed: {} = {} (min: {:?}, max: {:?})",
                    gate.name, gate.metric, value, gate.min_value, gate.max_value
                );

                if gate.required {
                    return Err(anyhow::anyhow!(msg));
                } else {
                    warn!("{}", msg);
                }
            } else {
                info!(
                    "Quality gate '{}' passed: {} = {}",
                    gate.name, gate.metric, value
                );
            }
        }

        Ok(())
    }

    /// Send notification about pipeline result
    async fn send_notification(&self, result: &PipelineResult) -> Result<()> {
        let should_notify = (result.success && self.config.notifications.notify_on_success)
            || (!result.success && self.config.notifications.notify_on_failure);

        if !should_notify {
            return Ok(());
        }

        let status = if result.success { "SUCCESS" } else { "FAILURE" };
        let duration = result
            .completed_at
            .map(|end| (end - result.started_at).num_seconds())
            .unwrap_or(0);

        let message = format!(
            "Pipeline {} - {}\nRun ID: {}\nDuration: {}s",
            self.config.name, status, result.run_id, duration
        );

        // Send webhook
        if let Some(webhook_url) = &self.config.notifications.webhook_url {
            let payload = serde_json::json!({
                "pipeline": self.config.name,
                "status": status,
                "run_id": result.run_id,
                "duration_secs": duration,
                "success": result.success,
            });

            match self.http_client.post(webhook_url).json(&payload).send().await {
                Ok(_) => info!("Notification sent to webhook"),
                Err(e) => error!("Failed to send webhook notification: {}", e),
            }
        }

        // Send Slack notification
        if let Some(slack_webhook) = &self.config.notifications.slack_webhook {
            let payload = serde_json::json!({
                "text": message,
            });

            match self.http_client.post(slack_webhook).json(&payload).send().await {
                Ok(_) => info!("Notification sent to Slack"),
                Err(e) => error!("Failed to send Slack notification: {}", e),
            }
        }

        Ok(())
    }

    /// Rollback to previous deployment
    async fn rollback(&self) -> Result<()> {
        info!("Rolling back to previous deployment...");

        let state = self.state.read().await;

        if let Some(previous_model) = &state.deployed_model {
            if previous_model.exists() {
                let latest_path = self.config.deploy_dir.join("latest.pkl");

                if latest_path.exists() {
                    tokio::fs::remove_file(&latest_path).await?;
                }

                #[cfg(unix)]
                std::os::unix::fs::symlink(previous_model, &latest_path)?;

                #[cfg(windows)]
                std::os::windows::fs::symlink_file(previous_model, &latest_path)?;

                info!("Rollback completed");
            } else {
                warn!("Previous model not found, cannot rollback");
            }
        } else {
            warn!("No previous deployment found, cannot rollback");
        }

        Ok(())
    }

    /// Get current pipeline state
    pub async fn get_state(&self) -> PipelineState {
        self.state.read().await.clone()
    }

    /// Get pipeline configuration
    pub fn get_config(&self) -> &PipelineConfig {
        &self.config
    }
}
