//! Model Versioning System for Compiled DSPy Models
//!
//! This library provides a comprehensive versioning system for managing
//! compiled DSPy models through their lifecycle: development, staging,
//! production, and deprecation.

use anyhow::{Context, Result, anyhow};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use semver::Version;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

/// Model lifecycle status
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModelStatus {
    /// Under active development
    Development,
    /// In staging environment for testing
    Staging,
    /// Deployed in production
    Production,
    /// No longer in use
    Deprecated,
}

impl ModelStatus {
    /// Check if status allows promotion to production
    pub fn can_promote_to_production(&self) -> bool {
        matches!(self, ModelStatus::Staging)
    }

    /// Check if status allows promotion to staging
    pub fn can_promote_to_staging(&self) -> bool {
        matches!(self, ModelStatus::Development)
    }

    /// Get status as string
    pub fn as_str(&self) -> &str {
        match self {
            ModelStatus::Development => "development",
            ModelStatus::Staging => "staging",
            ModelStatus::Production => "production",
            ModelStatus::Deprecated => "deprecated",
        }
    }
}

/// Comprehensive metadata for a model version
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelMetadata {
    /// Unique model identifier
    pub model_id: String,

    /// Semantic version string
    pub version: String,

    /// Creation timestamp (ISO 8601)
    pub created_at: String,

    /// Updated timestamp (ISO 8601)
    pub updated_at: String,

    /// Optimizer used for compilation
    pub optimizer: String,

    /// Base LLM model
    pub base_model: String,

    /// Number of training examples
    pub num_training_examples: usize,

    /// Validation score (0.0-1.0)
    pub validation_score: f64,

    /// Test score (0.0-1.0)
    pub test_score: Option<f64>,

    /// Hyperparameters used
    pub hyperparameters: serde_json::Value,

    /// Creator/author
    pub created_by: String,

    /// Description of changes
    pub description: String,

    /// Git commit hash (if applicable)
    pub git_commit: Option<String>,

    /// Training duration in seconds
    pub training_duration_secs: Option<u64>,

    /// Model size in bytes
    pub model_size_bytes: Option<u64>,
}

impl ModelMetadata {
    /// Create new metadata with required fields
    pub fn new(
        model_id: String,
        version: String,
        optimizer: String,
        base_model: String,
        num_training_examples: usize,
        validation_score: f64,
    ) -> Self {
        let now = Utc::now().to_rfc3339();
        Self {
            model_id,
            version,
            created_at: now.clone(),
            updated_at: now,
            optimizer,
            base_model,
            num_training_examples,
            validation_score,
            test_score: None,
            hyperparameters: serde_json::json!({}),
            created_by: "unknown".to_string(),
            description: String::new(),
            git_commit: None,
            training_duration_secs: None,
            model_size_bytes: None,
        }
    }

    /// Update the updated_at timestamp
    pub fn touch(&mut self) {
        self.updated_at = Utc::now().to_rfc3339();
    }

    /// Save metadata to JSON file
    pub fn save(&self, path: &Path) -> Result<()> {
        let json = serde_json::to_string_pretty(self)?;
        fs::write(path, json)?;
        Ok(())
    }

    /// Load metadata from JSON file
    pub fn load(path: &Path) -> Result<Self> {
        let json = fs::read_to_string(path)?;
        let metadata = serde_json::from_str(&json)?;
        Ok(metadata)
    }
}

/// A specific version of a model
#[derive(Debug, Clone)]
pub struct ModelVersion {
    /// Semantic version
    pub version: Version,

    /// Path to model directory
    pub path: PathBuf,

    /// Model metadata
    pub metadata: ModelMetadata,

    /// Current status
    pub status: ModelStatus,

    /// Status history (timestamp, old_status, new_status)
    pub status_history: Vec<StatusChange>,
}

/// Record of a status change
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatusChange {
    pub timestamp: String,
    pub from_status: String,
    pub to_status: String,
    pub reason: String,
    pub changed_by: String,
}

impl ModelVersion {
    /// Create a new model version
    pub fn new(
        version: Version,
        path: PathBuf,
        metadata: ModelMetadata,
    ) -> Self {
        let status_change = StatusChange {
            timestamp: Utc::now().to_rfc3339(),
            from_status: "none".to_string(),
            to_status: "development".to_string(),
            reason: "Initial registration".to_string(),
            changed_by: metadata.created_by.clone(),
        };

        Self {
            version,
            path,
            metadata,
            status: ModelStatus::Development,
            status_history: vec![status_change],
        }
    }

    /// Change status and record history
    pub fn change_status(&mut self, new_status: ModelStatus, reason: String, changed_by: String) {
        let change = StatusChange {
            timestamp: Utc::now().to_rfc3339(),
            from_status: self.status.as_str().to_string(),
            to_status: new_status.as_str().to_string(),
            reason,
            changed_by,
        };

        self.status_history.push(change);
        self.status = new_status;
        self.metadata.touch();
    }

    /// Get the path to the metadata file
    pub fn metadata_path(&self) -> PathBuf {
        self.path.join("metadata.json")
    }

    /// Get the path to the model file
    pub fn model_path(&self) -> PathBuf {
        self.path.join("model.pkl")
    }

    /// Save version metadata to disk
    pub fn save_metadata(&self) -> Result<()> {
        self.metadata.save(&self.metadata_path())
    }

    /// Get age of version in days
    pub fn age_days(&self) -> Option<i64> {
        let created: DateTime<Utc> = self.metadata.created_at.parse().ok()?;
        let now = Utc::now();
        Some((now - created).num_days())
    }
}

/// Comparison result between two model versions
#[derive(Debug)]
pub struct VersionComparison {
    pub model_id: String,
    pub version_a: Version,
    pub version_b: Version,
    pub score_diff: f64,
    pub training_examples_diff: i64,
    pub winner: ComparisonWinner,
    pub details: Vec<String>,
}

#[derive(Debug, PartialEq)]
pub enum ComparisonWinner {
    VersionA,
    VersionB,
    Tie,
}

/// Central registry for managing model versions
#[derive(Debug)]
pub struct ModelRegistry {
    /// Base directory for all models
    base_dir: PathBuf,

    /// Models organized by ID and versions
    models: HashMap<String, Vec<ModelVersion>>,

    /// Registry metadata
    metadata: RegistryMetadata,
}

/// Metadata about the registry itself
#[derive(Debug, Serialize, Deserialize)]
pub struct RegistryMetadata {
    pub created_at: String,
    pub updated_at: String,
    pub total_models: usize,
    pub total_versions: usize,
}

impl RegistryMetadata {
    pub fn new() -> Self {
        let now = Utc::now().to_rfc3339();
        Self {
            created_at: now.clone(),
            updated_at: now,
            total_models: 0,
            total_versions: 0,
        }
    }

    pub fn touch(&mut self) {
        self.updated_at = Utc::now().to_rfc3339();
    }
}

impl ModelRegistry {
    /// Create a new registry
    pub fn new(base_dir: PathBuf) -> Result<Self> {
        fs::create_dir_all(&base_dir)
            .context("Failed to create registry base directory")?;

        let metadata_path = base_dir.join("registry.json");
        let metadata = if metadata_path.exists() {
            let json = fs::read_to_string(&metadata_path)?;
            serde_json::from_str(&json)?
        } else {
            RegistryMetadata::new()
        };

        Ok(Self {
            base_dir,
            models: HashMap::new(),
            metadata,
        })
    }

    /// Register a new model version
    pub fn register_model(
        &mut self,
        model_id: &str,
        version: Version,
        metadata: ModelMetadata,
    ) -> Result<PathBuf> {
        // Create version directory
        let model_dir = self.base_dir
            .join(model_id)
            .join(version.to_string());

        fs::create_dir_all(&model_dir)
            .context("Failed to create model version directory")?;

        // Create model version
        let version_entry = ModelVersion::new(
            version.clone(),
            model_dir.clone(),
            metadata,
        );

        // Save metadata
        version_entry.save_metadata()?;

        // Add to registry
        self.models
            .entry(model_id.to_string())
            .or_insert_with(Vec::new)
            .push(version_entry);

        // Update registry metadata
        self.metadata.total_versions += 1;
        self.metadata.total_models = self.models.len();
        self.metadata.touch();
        self.save_metadata()?;

        Ok(model_dir)
    }

    /// Promote a model version to staging
    pub fn promote_to_staging(
        &mut self,
        model_id: &str,
        version: &Version,
        reason: String,
        promoted_by: String,
    ) -> Result<()> {
        let versions = self.models.get_mut(model_id)
            .context("Model not found")?;

        let version_entry = versions.iter_mut()
            .find(|v| &v.version == version)
            .context("Version not found")?;

        if !version_entry.status.can_promote_to_staging() {
            return Err(anyhow!(
                "Cannot promote from {:?} to staging",
                version_entry.status
            ));
        }

        version_entry.change_status(ModelStatus::Staging, reason, promoted_by);
        version_entry.save_metadata()?;

        println!("✓ Promoted {} v{} to staging", model_id, version);
        Ok(())
    }

    /// Promote a model version to production
    pub fn promote_to_production(
        &mut self,
        model_id: &str,
        version: &Version,
        reason: String,
        promoted_by: String,
    ) -> Result<()> {
        let versions = self.models.get_mut(model_id)
            .context("Model not found")?;

        // Find the version to promote
        let version_entry = versions.iter()
            .find(|v| &v.version == version)
            .context("Version not found")?;

        if !version_entry.status.can_promote_to_production() {
            return Err(anyhow!(
                "Cannot promote from {:?} to production. Must be in staging first.",
                version_entry.status
            ));
        }

        // Demote current production version
        let mut demoted = Vec::new();
        for v in versions.iter_mut() {
            if v.status == ModelStatus::Production {
                v.change_status(
                    ModelStatus::Deprecated,
                    format!("Superseded by v{}", version),
                    promoted_by.clone(),
                );
                v.save_metadata()?;
                demoted.push(v.version.clone());
            }
        }

        // Promote new version
        let version_entry = versions.iter_mut()
            .find(|v| &v.version == version)
            .context("Version not found")?;

        version_entry.change_status(ModelStatus::Production, reason, promoted_by);
        version_entry.save_metadata()?;

        if !demoted.is_empty() {
            println!("✓ Deprecated production versions: {:?}", demoted);
        }
        println!("✓ Promoted {} v{} to production", model_id, version);

        Ok(())
    }

    /// Rollback to a previous version
    pub fn rollback_to_version(
        &mut self,
        model_id: &str,
        target_version: &Version,
        reason: String,
        rolled_back_by: String,
    ) -> Result<()> {
        let versions = self.models.get_mut(model_id)
            .context("Model not found")?;

        // Verify target version exists and is suitable for rollback
        let target = versions.iter()
            .find(|v| &v.version == target_version)
            .context("Target version not found")?;

        if target.status == ModelStatus::Development {
            return Err(anyhow!("Cannot rollback to development version"));
        }

        // Demote current production
        for v in versions.iter_mut() {
            if v.status == ModelStatus::Production {
                v.change_status(
                    ModelStatus::Deprecated,
                    format!("Rolled back to v{}: {}", target_version, reason),
                    rolled_back_by.clone(),
                );
                v.save_metadata()?;
            }
        }

        // Promote target version
        let target_entry = versions.iter_mut()
            .find(|v| &v.version == target_version)
            .context("Target version not found")?;

        target_entry.change_status(
            ModelStatus::Production,
            format!("Rollback: {}", reason),
            rolled_back_by,
        );
        target_entry.save_metadata()?;

        println!("✓ Rolled back {} to v{}", model_id, target_version);
        Ok(())
    }

    /// Get the production model version
    pub fn get_production_model(&self, model_id: &str) -> Option<&ModelVersion> {
        self.models.get(model_id)?
            .iter()
            .find(|v| v.status == ModelStatus::Production)
    }

    /// Get the latest version (by semver)
    pub fn get_latest_version(&self, model_id: &str) -> Option<&ModelVersion> {
        self.models.get(model_id)?
            .iter()
            .max_by_key(|v| &v.version)
    }

    /// List all versions for a model
    pub fn list_versions(&self, model_id: &str) -> Option<Vec<&ModelVersion>> {
        let versions = self.models.get(model_id)?;
        let mut sorted: Vec<&ModelVersion> = versions.iter().collect();
        sorted.sort_by(|a, b| b.version.cmp(&a.version));
        Some(sorted)
    }

    /// List all models
    pub fn list_models(&self) -> Vec<&str> {
        let mut models: Vec<&str> = self.models.keys().map(|s| s.as_str()).collect();
        models.sort();
        models
    }

    /// Get versions by status
    pub fn get_versions_by_status(
        &self,
        model_id: &str,
        status: ModelStatus,
    ) -> Option<Vec<&ModelVersion>> {
        let versions = self.models.get(model_id)?;
        let filtered: Vec<&ModelVersion> = versions
            .iter()
            .filter(|v| v.status == status)
            .collect();

        if filtered.is_empty() {
            None
        } else {
            Some(filtered)
        }
    }

    /// Compare two versions
    pub fn compare_versions(
        &self,
        model_id: &str,
        version_a: &Version,
        version_b: &Version,
    ) -> Result<VersionComparison> {
        let versions = self.models.get(model_id)
            .context("Model not found")?;

        let ver_a = versions.iter()
            .find(|v| &v.version == version_a)
            .context("Version A not found")?;

        let ver_b = versions.iter()
            .find(|v| &v.version == version_b)
            .context("Version B not found")?;

        let score_diff = ver_b.metadata.validation_score - ver_a.metadata.validation_score;
        let training_examples_diff =
            ver_b.metadata.num_training_examples as i64 -
            ver_a.metadata.num_training_examples as i64;

        let mut details = Vec::new();

        // Score comparison
        if score_diff.abs() > 0.001 {
            details.push(format!(
                "Validation score: {:.3} → {:.3} ({:+.3})",
                ver_a.metadata.validation_score,
                ver_b.metadata.validation_score,
                score_diff
            ));
        }

        // Training data comparison
        if training_examples_diff != 0 {
            details.push(format!(
                "Training examples: {} → {} ({:+})",
                ver_a.metadata.num_training_examples,
                ver_b.metadata.num_training_examples,
                training_examples_diff
            ));
        }

        // Optimizer comparison
        if ver_a.metadata.optimizer != ver_b.metadata.optimizer {
            details.push(format!(
                "Optimizer: {} → {}",
                ver_a.metadata.optimizer,
                ver_b.metadata.optimizer
            ));
        }

        // Base model comparison
        if ver_a.metadata.base_model != ver_b.metadata.base_model {
            details.push(format!(
                "Base model: {} → {}",
                ver_a.metadata.base_model,
                ver_b.metadata.base_model
            ));
        }

        // Determine winner
        let winner = if score_diff > 0.01 {
            ComparisonWinner::VersionB
        } else if score_diff < -0.01 {
            ComparisonWinner::VersionA
        } else {
            ComparisonWinner::Tie
        };

        Ok(VersionComparison {
            model_id: model_id.to_string(),
            version_a: version_a.clone(),
            version_b: version_b.clone(),
            score_diff,
            training_examples_diff,
            winner,
            details,
        })
    }

    /// Get registry statistics
    pub fn statistics(&self) -> RegistryStatistics {
        let mut stats = RegistryStatistics {
            total_models: self.models.len(),
            total_versions: 0,
            development: 0,
            staging: 0,
            production: 0,
            deprecated: 0,
            avg_versions_per_model: 0.0,
        };

        for versions in self.models.values() {
            stats.total_versions += versions.len();
            for version in versions {
                match version.status {
                    ModelStatus::Development => stats.development += 1,
                    ModelStatus::Staging => stats.staging += 1,
                    ModelStatus::Production => stats.production += 1,
                    ModelStatus::Deprecated => stats.deprecated += 1,
                }
            }
        }

        if stats.total_models > 0 {
            stats.avg_versions_per_model =
                stats.total_versions as f64 / stats.total_models as f64;
        }

        stats
    }

    /// Save registry metadata
    fn save_metadata(&self) -> Result<()> {
        let metadata_path = self.base_dir.join("registry.json");
        let json = serde_json::to_string_pretty(&self.metadata)?;
        fs::write(metadata_path, json)?;
        Ok(())
    }

    /// Load all model versions from disk
    pub fn load_from_disk(&mut self) -> Result<()> {
        let entries = fs::read_dir(&self.base_dir)?;

        for entry in entries {
            let entry = entry?;
            let model_path = entry.path();

            if !model_path.is_dir() {
                continue;
            }

            let model_id = model_path.file_name()
                .and_then(|n| n.to_str())
                .context("Invalid model directory name")?;

            if model_id == "registry.json" {
                continue;
            }

            // Load versions
            let version_entries = fs::read_dir(&model_path)?;

            for version_entry in version_entries {
                let version_entry = version_entry?;
                let version_path = version_entry.path();

                if !version_path.is_dir() {
                    continue;
                }

                let version_str = version_path.file_name()
                    .and_then(|n| n.to_str())
                    .context("Invalid version directory name")?;

                let version = Version::parse(version_str)
                    .context("Invalid semver version")?;

                let metadata_path = version_path.join("metadata.json");
                if !metadata_path.exists() {
                    continue;
                }

                let metadata = ModelMetadata::load(&metadata_path)?;

                let model_version = ModelVersion::new(
                    version,
                    version_path,
                    metadata,
                );

                self.models
                    .entry(model_id.to_string())
                    .or_insert_with(Vec::new)
                    .push(model_version);
            }
        }

        Ok(())
    }
}

/// Statistics about the registry
#[derive(Debug)]
pub struct RegistryStatistics {
    pub total_models: usize,
    pub total_versions: usize,
    pub development: usize,
    pub staging: usize,
    pub production: usize,
    pub deprecated: usize,
    pub avg_versions_per_model: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_model_status() {
        assert!(ModelStatus::Development.can_promote_to_staging());
        assert!(ModelStatus::Staging.can_promote_to_production());
        assert!(!ModelStatus::Production.can_promote_to_staging());
    }

    #[test]
    fn test_registry_creation() {
        let temp_dir = std::env::temp_dir().join("test_registry");
        let registry = ModelRegistry::new(temp_dir.clone());
        assert!(registry.is_ok());
        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_version_comparison() {
        let v1 = Version::parse("1.0.0").unwrap();
        let v2 = Version::parse("2.0.0").unwrap();
        assert!(v2 > v1);
    }
}
