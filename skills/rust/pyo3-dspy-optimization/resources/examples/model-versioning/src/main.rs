//! Model Versioning Demonstration
//!
//! This example demonstrates:
//! - Creating multiple model versions
//! - Promotion workflow (dev → staging → production)
//! - Version comparison
//! - Rollback scenarios
//! - Version history display

use anyhow::Result;
use model_versioning::{
    ComparisonWinner, ModelMetadata, ModelRegistry, ModelStatus,
};
use semver::Version;
use std::path::PathBuf;

fn main() -> Result<()> {
    println!("==============================================");
    println!("   DSPy Model Versioning System Demo");
    println!("==============================================\n");

    // Create registry
    let base_dir = PathBuf::from("./demo_models");
    let mut registry = ModelRegistry::new(base_dir)?;

    println!("📁 Registry created at: ./demo_models\n");

    // Scenario 1: Register initial versions
    println!("=== Scenario 1: Creating Model Versions ===\n");
    create_model_versions(&mut registry)?;
    print_separator();

    // Scenario 2: Promotion workflow
    println!("=== Scenario 2: Promotion Workflow ===\n");
    promotion_workflow(&mut registry)?;
    print_separator();

    // Scenario 3: Compare versions
    println!("=== Scenario 3: Version Comparison ===\n");
    compare_versions(&registry)?;
    print_separator();

    // Scenario 4: Rollback scenario
    println!("=== Scenario 4: Rollback Scenario ===\n");
    rollback_scenario(&mut registry)?;
    print_separator();

    // Scenario 5: Display version history
    println!("=== Scenario 5: Version History ===\n");
    display_version_history(&registry)?;
    print_separator();

    // Scenario 6: Registry statistics
    println!("=== Scenario 6: Registry Statistics ===\n");
    display_statistics(&registry);
    print_separator();

    println!("✅ Demo completed successfully!\n");
    println!("Registry location: ./demo_models");
    println!("Explore the directory structure to see generated files.\n");

    Ok(())
}

/// Create multiple model versions
fn create_model_versions(registry: &mut ModelRegistry) -> Result<()> {
    println!("Creating model versions for 'qa-model'...\n");

    // Version 1.0.0 - Initial release
    let v1_metadata = ModelMetadata {
        model_id: "qa-model".to_string(),
        version: "1.0.0".to_string(),
        created_at: "2025-01-01T10:00:00Z".to_string(),
        updated_at: "2025-01-01T10:00:00Z".to_string(),
        optimizer: "BootstrapFewShot".to_string(),
        base_model: "gpt-3.5-turbo".to_string(),
        num_training_examples: 1000,
        validation_score: 0.82,
        test_score: Some(0.80),
        hyperparameters: serde_json::json!({
            "max_bootstrapped_demos": 4,
            "max_labeled_demos": 16,
            "temperature": 0.7,
        }),
        created_by: "data-team".to_string(),
        description: "Initial baseline model".to_string(),
        git_commit: Some("abc123".to_string()),
        training_duration_secs: Some(3600),
        model_size_bytes: Some(1024 * 1024 * 10), // 10 MB
    };

    let v1 = Version::parse("1.0.0")?;
    let v1_path = registry.register_model("qa-model", v1.clone(), v1_metadata)?;
    println!("✓ Registered qa-model v1.0.0");
    println!("  Path: {:?}", v1_path);
    println!("  Validation score: 0.82");
    println!("  Status: Development\n");

    // Version 1.1.0 - Improved with more data
    let v1_1_metadata = ModelMetadata {
        model_id: "qa-model".to_string(),
        version: "1.1.0".to_string(),
        created_at: "2025-01-15T10:00:00Z".to_string(),
        updated_at: "2025-01-15T10:00:00Z".to_string(),
        optimizer: "MIPROv2".to_string(),
        base_model: "gpt-3.5-turbo".to_string(),
        num_training_examples: 1500,
        validation_score: 0.87,
        test_score: Some(0.85),
        hyperparameters: serde_json::json!({
            "num_candidates": 10,
            "init_temperature": 1.0,
            "temperature": 0.7,
        }),
        created_by: "ml-team".to_string(),
        description: "Improved accuracy with MIPRO optimizer and more training data".to_string(),
        git_commit: Some("def456".to_string()),
        training_duration_secs: Some(7200),
        model_size_bytes: Some(1024 * 1024 * 12), // 12 MB
    };

    let v1_1 = Version::parse("1.1.0")?;
    let v1_1_path = registry.register_model("qa-model", v1_1.clone(), v1_1_metadata)?;
    println!("✓ Registered qa-model v1.1.0");
    println!("  Path: {:?}", v1_1_path);
    println!("  Validation score: 0.87 (+0.05)");
    println!("  Status: Development\n");

    // Version 2.0.0 - Major upgrade with GPT-4
    let v2_metadata = ModelMetadata {
        model_id: "qa-model".to_string(),
        version: "2.0.0".to_string(),
        created_at: "2025-02-01T10:00:00Z".to_string(),
        updated_at: "2025-02-01T10:00:00Z".to_string(),
        optimizer: "MIPROv2".to_string(),
        base_model: "gpt-4-turbo".to_string(),
        num_training_examples: 2000,
        validation_score: 0.93,
        test_score: Some(0.91),
        hyperparameters: serde_json::json!({
            "num_candidates": 15,
            "init_temperature": 1.2,
            "temperature": 0.6,
        }),
        created_by: "ml-team".to_string(),
        description: "Major upgrade with GPT-4 base model and enhanced training".to_string(),
        git_commit: Some("ghi789".to_string()),
        training_duration_secs: Some(14400),
        model_size_bytes: Some(1024 * 1024 * 15), // 15 MB
    };

    let v2 = Version::parse("2.0.0")?;
    let v2_path = registry.register_model("qa-model", v2.clone(), v2_metadata)?;
    println!("✓ Registered qa-model v2.0.0");
    println!("  Path: {:?}", v2_path);
    println!("  Validation score: 0.93 (+0.06)");
    println!("  Status: Development");
    println!("  ⚠️  Breaking change: Upgraded to GPT-4\n");

    // Create a summarization model for comparison
    let summ_metadata = ModelMetadata {
        model_id: "summarization-model".to_string(),
        version: "1.0.0".to_string(),
        created_at: "2025-01-20T10:00:00Z".to_string(),
        updated_at: "2025-01-20T10:00:00Z".to_string(),
        optimizer: "BootstrapFewShot".to_string(),
        base_model: "gpt-3.5-turbo".to_string(),
        num_training_examples: 800,
        validation_score: 0.78,
        test_score: Some(0.76),
        hyperparameters: serde_json::json!({
            "max_bootstrapped_demos": 3,
            "temperature": 0.8,
        }),
        created_by: "nlp-team".to_string(),
        description: "Document summarization model".to_string(),
        git_commit: Some("jkl012".to_string()),
        training_duration_secs: Some(2400),
        model_size_bytes: Some(1024 * 1024 * 8), // 8 MB
    };

    let summ_v = Version::parse("1.0.0")?;
    registry.register_model("summarization-model", summ_v, summ_metadata)?;
    println!("✓ Registered summarization-model v1.0.0");
    println!("  Validation score: 0.78\n");

    Ok(())
}

/// Demonstrate promotion workflow
fn promotion_workflow(registry: &mut ModelRegistry) -> Result<()> {
    println!("Promoting qa-model v1.0.0 through lifecycle...\n");

    let v1_0_0 = Version::parse("1.0.0")?;
    let v1_1_0 = Version::parse("1.1.0")?;

    // Promote v1.0.0 to staging
    println!("Step 1: Development → Staging");
    registry.promote_to_staging(
        "qa-model",
        &v1_0_0,
        "Passed initial validation tests".to_string(),
        "ci-bot".to_string(),
    )?;
    println!("  ✓ v1.0.0 now in staging\n");

    // Promote v1.0.0 to production
    println!("Step 2: Staging → Production");
    registry.promote_to_production(
        "qa-model",
        &v1_0_0,
        "Passed staging tests and load testing".to_string(),
        "deployment-team".to_string(),
    )?;
    println!("  ✓ v1.0.0 now in production\n");

    // Promote v1.1.0 to staging
    println!("Step 3: Promote v1.1.0 to staging");
    registry.promote_to_staging(
        "qa-model",
        &v1_1_0,
        "Better validation scores, ready for staging".to_string(),
        "ml-team".to_string(),
    )?;
    println!("  ✓ v1.1.0 now in staging\n");

    // Show current status
    println!("Current status:");
    if let Some(prod_version) = registry.get_production_model("qa-model") {
        println!("  Production: v{} (score: {:.3})",
            prod_version.version,
            prod_version.metadata.validation_score
        );
    }

    if let Some(staging_versions) = registry.get_versions_by_status(
        "qa-model",
        ModelStatus::Staging,
    ) {
        for version in staging_versions {
            println!("  Staging: v{} (score: {:.3})",
                version.version,
                version.metadata.validation_score
            );
        }
    }

    println!();
    Ok(())
}

/// Compare model versions
fn compare_versions(registry: &ModelRegistry) -> Result<()> {
    let v1_0_0 = Version::parse("1.0.0")?;
    let v1_1_0 = Version::parse("1.1.0")?;
    let v2_0_0 = Version::parse("2.0.0")?;

    // Compare v1.0.0 vs v1.1.0
    println!("Comparing qa-model v1.0.0 vs v1.1.0:\n");
    let comparison = registry.compare_versions("qa-model", &v1_0_0, &v1_1_0)?;

    println!("  Version A: v{}", comparison.version_a);
    println!("  Version B: v{}", comparison.version_b);
    println!("  Score difference: {:+.3}", comparison.score_diff);
    println!("  Winner: {:?}", comparison.winner);
    println!("\n  Changes:");
    for detail in &comparison.details {
        println!("    • {}", detail);
    }

    match comparison.winner {
        ComparisonWinner::VersionB => {
            println!("\n  ✅ Version B shows improvement");
        }
        ComparisonWinner::VersionA => {
            println!("\n  ⚠️  Version B shows degradation");
        }
        ComparisonWinner::Tie => {
            println!("\n  ➖ Versions are comparable");
        }
    }

    println!();

    // Compare v1.1.0 vs v2.0.0
    println!("Comparing qa-model v1.1.0 vs v2.0.0:\n");
    let comparison2 = registry.compare_versions("qa-model", &v1_1_0, &v2_0_0)?;

    println!("  Version A: v{}", comparison2.version_a);
    println!("  Version B: v{}", comparison2.version_b);
    println!("  Score difference: {:+.3}", comparison2.score_diff);
    println!("  Winner: {:?}", comparison2.winner);
    println!("\n  Changes:");
    for detail in &comparison2.details {
        println!("    • {}", detail);
    }

    if comparison2.score_diff > 0.05 {
        println!("\n  ✅ Significant improvement! Consider promoting to production.");
    }

    println!();
    Ok(())
}

/// Demonstrate rollback scenario
fn rollback_scenario(registry: &mut ModelRegistry) -> Result<()> {
    let v1_0_0 = Version::parse("1.0.0")?;
    let v1_1_0 = Version::parse("1.1.0")?;

    println!("Simulating production incident requiring rollback...\n");

    // First, promote v1.1.0 to production
    println!("Step 1: Promote v1.1.0 to production");
    registry.promote_to_production(
        "qa-model",
        &v1_1_0,
        "Better performance metrics observed".to_string(),
        "deployment-team".to_string(),
    )?;
    println!();

    // Simulate incident
    println!("⚠️  INCIDENT DETECTED!");
    println!("  • Error rate increased from 0.5% to 3.2%");
    println!("  • P99 latency increased from 200ms to 850ms");
    println!("  • Customer complaints about incorrect answers\n");

    println!("Step 2: Emergency rollback to v1.0.0");
    registry.rollback_to_version(
        "qa-model",
        &v1_0_0,
        "High error rate in production - emergency rollback".to_string(),
        "incident-commander".to_string(),
    )?;

    println!("\n✅ Rollback completed");
    println!("  • Production: v1.0.0 (stable)");
    println!("  • Deprecated: v1.1.0 (investigation required)\n");

    println!("Post-incident analysis:");
    println!("  • Root cause: Hyperparameter tuning issue in v1.1.0");
    println!("  • Action item: Add regression tests for error rate");
    println!("  • Follow-up: Re-train v1.1.1 with corrected hyperparameters\n");

    Ok(())
}

/// Display version history
fn display_version_history(registry: &ModelRegistry) -> Result<()> {
    println!("Displaying complete version history for all models:\n");

    for model_id in registry.list_models() {
        println!("Model: {}", model_id);
        println!("{}", "─".repeat(60));

        if let Some(versions) = registry.list_versions(model_id) {
            for version in versions {
                display_version_info(version);
            }
        }
        println!();
    }

    Ok(())
}

/// Display detailed version information
fn display_version_info(version: &model_versioning::ModelVersion) {
    let status_icon = match version.status {
        ModelStatus::Development => "🔨",
        ModelStatus::Staging => "🧪",
        ModelStatus::Production => "🚀",
        ModelStatus::Deprecated => "⛔",
    };

    println!("\n  {} Version: v{}", status_icon, version.version);
    println!("     Status: {:?}", version.status);
    println!("     Validation score: {:.3}", version.metadata.validation_score);

    if let Some(test_score) = version.metadata.test_score {
        println!("     Test score: {:.3}", test_score);
    }

    println!("     Optimizer: {}", version.metadata.optimizer);
    println!("     Base model: {}", version.metadata.base_model);
    println!("     Training examples: {}", version.metadata.num_training_examples);
    println!("     Created: {}", version.metadata.created_at);
    println!("     Created by: {}", version.metadata.created_by);

    if !version.metadata.description.is_empty() {
        println!("     Description: {}", version.metadata.description);
    }

    if let Some(commit) = &version.metadata.git_commit {
        println!("     Git commit: {}", commit);
    }

    if let Some(duration) = version.metadata.training_duration_secs {
        println!("     Training time: {}s ({:.1}h)", duration, duration as f64 / 3600.0);
    }

    if let Some(size) = version.metadata.model_size_bytes {
        println!("     Model size: {:.2} MB", size as f64 / (1024.0 * 1024.0));
    }

    if let Some(age) = version.age_days() {
        println!("     Age: {} days", age);
    }

    // Show status history
    if version.status_history.len() > 1 {
        println!("     Status history:");
        for change in &version.status_history {
            println!("       • {} → {} ({})",
                change.from_status,
                change.to_status,
                change.changed_by
            );
            if !change.reason.is_empty() {
                println!("         Reason: {}", change.reason);
            }
        }
    }
}

/// Display registry statistics
fn display_statistics(registry: &ModelRegistry) {
    let stats = registry.statistics();

    println!("Registry Statistics:");
    println!("{}", "═".repeat(60));
    println!("  Total models: {}", stats.total_models);
    println!("  Total versions: {}", stats.total_versions);
    println!("  Average versions per model: {:.1}", stats.avg_versions_per_model);
    println!();
    println!("  Status breakdown:");
    println!("    🔨 Development: {}", stats.development);
    println!("    🧪 Staging: {}", stats.staging);
    println!("    🚀 Production: {}", stats.production);
    println!("    ⛔ Deprecated: {}", stats.deprecated);
    println!();

    // Calculate percentages
    if stats.total_versions > 0 {
        let dev_pct = (stats.development as f64 / stats.total_versions as f64) * 100.0;
        let staging_pct = (stats.staging as f64 / stats.total_versions as f64) * 100.0;
        let prod_pct = (stats.production as f64 / stats.total_versions as f64) * 100.0;
        let dep_pct = (stats.deprecated as f64 / stats.total_versions as f64) * 100.0;

        println!("  Distribution:");
        println!("    Development: {:.1}%", dev_pct);
        println!("    Staging: {:.1}%", staging_pct);
        println!("    Production: {:.1}%", prod_pct);
        println!("    Deprecated: {:.1}%", dep_pct);
    }
}

/// Print visual separator
fn print_separator() {
    println!("\n{}\n", "=".repeat(60));
}
