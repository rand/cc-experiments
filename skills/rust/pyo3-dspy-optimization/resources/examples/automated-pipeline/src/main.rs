//! Automated pipeline CLI and scheduler
//!
//! This binary provides:
//! - Manual pipeline execution
//! - Scheduled execution via cron
//! - Pipeline monitoring
//! - Configuration management

use anyhow::{Context, Result};
use automated_pipeline::{
    OptimizationPipeline, PipelineConfig, PipelineStage, QualityGate,
};
use std::path::PathBuf;
use tokio_cron_scheduler::{Job, JobScheduler};
use tracing::{error, info};
use tracing_subscriber::EnvFilter;

/// CLI commands
#[derive(Debug)]
enum Command {
    /// Run pipeline once
    Run,
    /// Start scheduler
    Schedule { cron: String },
    /// Show pipeline status
    Status,
    /// Show pipeline history
    History { limit: usize },
    /// Initialize configuration
    Init,
    /// Validate configuration
    Validate,
}

impl Command {
    /// Parse from command line arguments
    fn parse() -> Result<Self> {
        let args: Vec<String> = std::env::args().collect();

        if args.len() < 2 {
            return Ok(Self::Run);
        }

        match args[1].as_str() {
            "run" => Ok(Self::Run),
            "schedule" => {
                let cron = args
                    .get(2)
                    .ok_or_else(|| anyhow::anyhow!("Cron expression required"))?
                    .clone();
                Ok(Self::Schedule { cron })
            }
            "status" => Ok(Self::Status),
            "history" => {
                let limit = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(10);
                Ok(Self::History { limit })
            }
            "init" => Ok(Self::Init),
            "validate" => Ok(Self::Validate),
            _ => Err(anyhow::anyhow!("Unknown command: {}", args[1])),
        }
    }
}

/// Pipeline runner
struct PipelineRunner {
    config_path: PathBuf,
    state_path: PathBuf,
}

impl PipelineRunner {
    /// Create new runner
    fn new() -> Self {
        Self {
            config_path: PathBuf::from("pipeline.yaml"),
            state_path: PathBuf::from(".pipeline_state.json"),
        }
    }

    /// Load pipeline configuration
    fn load_config(&self) -> Result<PipelineConfig> {
        PipelineConfig::from_yaml(&self.config_path)
            .context("Failed to load pipeline configuration")
    }

    /// Create pipeline instance
    async fn create_pipeline(&self) -> Result<OptimizationPipeline> {
        let config = self.load_config()?;
        OptimizationPipeline::new(config, self.state_path.clone())
    }

    /// Execute pipeline
    async fn run(&self) -> Result<()> {
        info!("Starting pipeline execution...");

        let pipeline = self.create_pipeline().await?;
        let result = pipeline.execute().await?;

        // Print summary
        println!("\n=== Pipeline Execution Summary ===");
        println!("Run ID: {}", result.run_id);
        println!("Status: {}", if result.success { "SUCCESS" } else { "FAILURE" });
        println!("Started: {}", result.started_at);
        if let Some(completed) = result.completed_at {
            let duration = (completed - result.started_at).num_seconds();
            println!("Duration: {}s", duration);
        }

        println!("\nStage Results:");
        for stage in PipelineStage::all_stages() {
            if let Some(stage_result) = result.stage_results.get(&stage) {
                println!(
                    "  {:?}: {} ({:.2}s)",
                    stage,
                    if stage_result.success { "✓" } else { "✗" },
                    stage_result.duration_secs
                );

                if !stage_result.metrics.is_empty() {
                    println!("    Metrics:");
                    for (metric, value) in &stage_result.metrics {
                        println!("      {}: {:.4}", metric, value);
                    }
                }

                if let Some(error) = &stage_result.error {
                    println!("    Error: {}", error);
                }

                if !stage_result.artifacts.is_empty() {
                    println!("    Artifacts:");
                    for artifact in &stage_result.artifacts {
                        println!("      {}", artifact.display());
                    }
                }
            }
        }

        if let Some(model_path) = &result.deployed_model {
            println!("\nDeployed Model: {}", model_path.display());
        }

        if !result.success {
            return Err(anyhow::anyhow!("Pipeline failed"));
        }

        Ok(())
    }

    /// Start scheduled execution
    async fn schedule(&self, cron_expr: String) -> Result<()> {
        info!("Starting pipeline scheduler with cron: {}", cron_expr);

        let mut scheduler = JobScheduler::new().await?;

        // Clone paths for job closure
        let config_path = self.config_path.clone();
        let state_path = self.state_path.clone();

        // Create scheduled job
        let job = Job::new_async(cron_expr.as_str(), move |_uuid, _lock| {
            let config_path = config_path.clone();
            let state_path = state_path.clone();

            Box::pin(async move {
                info!("Scheduled pipeline run starting...");

                match execute_scheduled_run(&config_path, &state_path).await {
                    Ok(_) => info!("Scheduled pipeline run completed successfully"),
                    Err(e) => error!("Scheduled pipeline run failed: {}", e),
                }
            })
        })?;

        scheduler.add(job).await?;
        scheduler.start().await?;

        println!("Pipeline scheduler started with cron: {}", cron_expr);
        println!("Press Ctrl+C to stop");

        // Keep scheduler running
        tokio::signal::ctrl_c().await?;

        info!("Stopping scheduler...");
        scheduler.shutdown().await?;

        Ok(())
    }

    /// Show pipeline status
    async fn status(&self) -> Result<()> {
        let pipeline = self.create_pipeline().await?;
        let state = pipeline.get_state().await;
        let config = pipeline.get_config();

        println!("\n=== Pipeline Status ===");
        println!("Name: {}", config.name);
        println!("Optimizer: {}", config.optimizer);

        if let Some(run_id) = &state.current_run_id {
            println!("\nCurrent Run:");
            println!("  Run ID: {}", run_id);
            if let Some(stage) = state.current_stage {
                println!("  Stage: {:?}", stage);
            }
        } else {
            println!("\nStatus: Idle");
        }

        println!("\nStatistics:");
        println!("  Total Runs: {}", state.total_runs);
        println!("  Successful: {}", state.successful_runs);
        println!("  Failed: {}", state.failed_runs);

        if state.total_runs > 0 {
            let success_rate =
                (state.successful_runs as f64 / state.total_runs as f64) * 100.0;
            println!("  Success Rate: {:.1}%", success_rate);
        }

        if let Some(last_success) = state.last_success {
            println!("\nLast Success: {}", last_success);
        }

        if let Some(last_failure) = state.last_failure {
            println!("Last Failure: {}", last_failure);
        }

        if let Some(model_path) = &state.deployed_model {
            println!("\nDeployed Model: {}", model_path.display());
        }

        println!("\nQuality Gates:");
        for gate in &config.quality_gates {
            println!("  {} ({})", gate.name, gate.metric);
            if let Some(min) = gate.min_value {
                println!("    Min: {}", min);
            }
            if let Some(max) = gate.max_value {
                println!("    Max: {}", max);
            }
            println!("    Required: {}", gate.required);
        }

        println!("\nConfiguration:");
        println!("  Auto-deploy: {}", config.auto_deploy);
        println!("  Rollback enabled: {}", config.enable_rollback);
        println!("  Max trials: {}", config.max_trials);
        println!("  Deploy directory: {}", config.deploy_dir.display());
        println!("  Artifact directory: {}", config.artifact_dir.display());

        Ok(())
    }

    /// Show pipeline history
    async fn history(&self, limit: usize) -> Result<()> {
        println!("\n=== Pipeline History (last {}) ===", limit);

        // Scan artifact directory for past runs
        let config = self.load_config()?;
        let artifact_dir = &config.artifact_dir;

        if !artifact_dir.exists() {
            println!("No history found");
            return Ok(());
        }

        let mut runs = Vec::new();
        let mut entries = tokio::fs::read_dir(artifact_dir).await?;

        while let Some(entry) = entries.next_entry().await? {
            if entry.file_type().await?.is_dir() {
                if let Some(name) = entry.file_name().to_str() {
                    if name.starts_with("run_") {
                        runs.push(name.to_string());
                    }
                }
            }
        }

        runs.sort();
        runs.reverse();

        for (i, run_id) in runs.iter().take(limit).enumerate() {
            println!("\n{}. {}", i + 1, run_id);

            // Check which stages completed
            let run_dir = artifact_dir.join(run_id);

            for stage in PipelineStage::all_stages() {
                let stage_dir = run_dir.join(stage.name());
                if stage_dir.exists() {
                    println!("   {:?}: ✓", stage);
                } else {
                    println!("   {:?}: ✗", stage);
                }
            }
        }

        Ok(())
    }

    /// Initialize configuration
    async fn init(&self) -> Result<()> {
        if self.config_path.exists() {
            println!("Configuration already exists at {}", self.config_path.display());
            return Ok(());
        }

        println!("Initializing pipeline configuration...");

        let config = PipelineConfig::new("my_pipeline")
            .add_quality_gate(
                QualityGate::new("accuracy_threshold", "accuracy")
                    .with_min(0.7),
            )
            .add_quality_gate(
                QualityGate::new("f1_threshold", "f1_score")
                    .with_min(0.65),
            );

        config.to_yaml(&self.config_path)?;

        println!("Configuration created at {}", self.config_path.display());
        println!("\nDefault configuration:");
        println!("  Name: {}", config.name);
        println!("  Optimizer: {}", config.optimizer);
        println!("  Quality Gates: {}", config.quality_gates.len());
        println!("\nEdit {} to customize", self.config_path.display());

        Ok(())
    }

    /// Validate configuration
    async fn validate(&self) -> Result<()> {
        println!("Validating pipeline configuration...");

        let config = self.load_config()?;

        // Check files exist
        println!("\nChecking data files...");
        if config.train_data.exists() {
            println!("  ✓ Training data: {}", config.train_data.display());
        } else {
            println!("  ✗ Training data not found: {}", config.train_data.display());
        }

        if config.val_data.exists() {
            println!("  ✓ Validation data: {}", config.val_data.display());
        } else {
            println!("  ✗ Validation data not found: {}", config.val_data.display());
        }

        // Check directories
        println!("\nChecking directories...");
        for (name, path) in [
            ("Deploy", &config.deploy_dir),
            ("Artifact", &config.artifact_dir),
        ] {
            if path.exists() {
                println!("  ✓ {} directory exists: {}", name, path.display());
            } else {
                println!("  → {} directory will be created: {}", name, path.display());
            }
        }

        // Validate quality gates
        println!("\nValidating quality gates...");
        for gate in &config.quality_gates {
            println!("  {} ({})", gate.name, gate.metric);
            if gate.min_value.is_none() && gate.max_value.is_none() {
                println!("    ⚠ Warning: No thresholds set");
            }
        }

        // Check notifications
        println!("\nNotification configuration:");
        let notif = &config.notifications;
        if notif.webhook_url.is_some() {
            println!("  ✓ Webhook configured");
        }
        if notif.slack_webhook.is_some() {
            println!("  ✓ Slack webhook configured");
        }
        if !notif.email_addresses.is_empty() {
            println!("  ✓ {} email addresses configured", notif.email_addresses.len());
        }
        if notif.webhook_url.is_none()
            && notif.slack_webhook.is_none()
            && notif.email_addresses.is_empty()
        {
            println!("  → No notifications configured");
        }

        println!("\n✓ Configuration is valid");

        Ok(())
    }
}

/// Execute a scheduled pipeline run
async fn execute_scheduled_run(config_path: &PathBuf, state_path: &PathBuf) -> Result<()> {
    let config = PipelineConfig::from_yaml(config_path)?;
    let pipeline = OptimizationPipeline::new(config, state_path.clone())?;

    let result = pipeline.execute().await?;

    if !result.success {
        error!("Scheduled pipeline run failed");
    }

    Ok(())
}

/// Print usage information
fn print_usage() {
    println!("Automated DSPy Pipeline");
    println!("\nUsage:");
    println!("  automated-pipeline run                 Run pipeline once");
    println!("  automated-pipeline schedule <cron>     Start scheduler");
    println!("  automated-pipeline status              Show pipeline status");
    println!("  automated-pipeline history [limit]     Show pipeline history");
    println!("  automated-pipeline init                Initialize configuration");
    println!("  automated-pipeline validate            Validate configuration");
    println!("\nExamples:");
    println!("  automated-pipeline schedule \"0 0 * * *\"    Run daily at midnight");
    println!("  automated-pipeline schedule \"0 */6 * * *\"  Run every 6 hours");
    println!("  automated-pipeline history 5              Show last 5 runs");
    println!("\nEnvironment Variables:");
    println!("  RUST_LOG=info    Enable logging");
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .init();

    // Parse command
    let command = match Command::parse() {
        Ok(cmd) => cmd,
        Err(e) => {
            eprintln!("Error: {}", e);
            print_usage();
            std::process::exit(1);
        }
    };

    let runner = PipelineRunner::new();

    // Execute command
    let result = match command {
        Command::Run => runner.run().await,
        Command::Schedule { cron } => runner.schedule(cron).await,
        Command::Status => runner.status().await,
        Command::History { limit } => runner.history(limit).await,
        Command::Init => runner.init().await,
        Command::Validate => runner.validate().await,
    };

    if let Err(e) = result {
        error!("Command failed: {}", e);
        std::process::exit(1);
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_runner_creation() {
        let runner = PipelineRunner::new();
        assert_eq!(runner.config_path, PathBuf::from("pipeline.yaml"));
    }

    #[tokio::test]
    async fn test_command_parsing() {
        // Test is basic since we can't easily mock std::env::args
        assert!(Command::parse().is_ok());
    }
}
