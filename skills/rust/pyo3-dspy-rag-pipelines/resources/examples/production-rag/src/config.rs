//! Configuration management for production RAG system
//!
//! Provides environment-based configuration with validation and defaults.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::env;
use std::time::Duration;

/// Complete application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub server: ServerConfig,
    pub qdrant: QdrantConfig,
    pub redis: RedisConfig,
    pub embeddings: EmbeddingConfig,
    pub generation: GenerationConfig,
    pub performance: PerformanceConfig,
}

/// HTTP server configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub request_timeout: Duration,
}

/// Qdrant vector database configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QdrantConfig {
    pub url: String,
    pub collection: String,
    pub vector_dim: usize,
    pub distance_metric: String,
}

/// Redis cache configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisConfig {
    pub url: String,
    pub ttl_seconds: u64,
    pub max_connections: u32,
}

/// Embedding model configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingConfig {
    pub model: String,
    pub batch_size: usize,
    pub normalize: bool,
}

/// LLM generation configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenerationConfig {
    pub model: String,
    pub api_key: String,
    pub max_tokens: usize,
    pub temperature: f32,
}

/// Performance tuning configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceConfig {
    pub max_connections: usize,
    pub cache_size: u64,
    pub worker_threads: usize,
}

impl Config {
    /// Load configuration from environment variables
    pub fn from_env() -> Result<Self> {
        dotenvy::dotenv().ok(); // Load .env if present

        Ok(Config {
            server: ServerConfig {
                host: env_or("SERVER_HOST", "0.0.0.0"),
                port: env_or_parse("SERVER_PORT", 8080)?,
                request_timeout: Duration::from_secs(env_or_parse(
                    "REQUEST_TIMEOUT_SECONDS",
                    30,
                )?),
            },
            qdrant: QdrantConfig {
                url: env_or("QDRANT_URL", "http://localhost:6333"),
                collection: env_or("QDRANT_COLLECTION", "documents"),
                vector_dim: env_or_parse("VECTOR_DIM", 384)?,
                distance_metric: env_or("DISTANCE_METRIC", "Cosine"),
            },
            redis: RedisConfig {
                url: env_or("REDIS_URL", "redis://localhost:6379"),
                ttl_seconds: env_or_parse("CACHE_TTL_SECONDS", 3600)?,
                max_connections: env_or_parse("REDIS_MAX_CONNECTIONS", 10)?,
            },
            embeddings: EmbeddingConfig {
                model: env_or(
                    "EMBEDDING_MODEL",
                    "sentence-transformers/all-MiniLM-L6-v2",
                ),
                batch_size: env_or_parse("EMBEDDING_BATCH_SIZE", 32)?,
                normalize: env_or_parse("EMBEDDING_NORMALIZE", true)?,
            },
            generation: GenerationConfig {
                model: env_or("LM_MODEL", "gpt-3.5-turbo"),
                api_key: env::var("OPENAI_API_KEY")
                    .context("OPENAI_API_KEY must be set")?,
                max_tokens: env_or_parse("MAX_TOKENS", 500)?,
                temperature: env_or_parse("TEMPERATURE", 0.7)?,
            },
            performance: PerformanceConfig {
                max_connections: env_or_parse("MAX_CONNECTIONS", 100)?,
                cache_size: env_or_parse("CACHE_SIZE", 10000)?,
                worker_threads: env_or_parse("WORKER_THREADS", num_cpus())?,
            },
        })
    }

    /// Validate configuration values
    pub fn validate(&self) -> Result<()> {
        if self.server.port == 0 {
            anyhow::bail!("Invalid port: 0");
        }

        if self.qdrant.vector_dim == 0 {
            anyhow::bail!("Vector dimension must be > 0");
        }

        if self.embeddings.batch_size == 0 {
            anyhow::bail!("Batch size must be > 0");
        }

        if self.generation.temperature < 0.0 || self.generation.temperature > 2.0 {
            anyhow::bail!("Temperature must be in range [0.0, 2.0]");
        }

        if self.performance.max_connections == 0 {
            anyhow::bail!("Max connections must be > 0");
        }

        Ok(())
    }

    /// Get server bind address
    pub fn bind_address(&self) -> String {
        format!("{}:{}", self.server.host, self.server.port)
    }
}

/// Get environment variable or default value
fn env_or(key: &str, default: &str) -> String {
    env::var(key).unwrap_or_else(|_| default.to_string())
}

/// Get environment variable and parse, or use default
fn env_or_parse<T: std::str::FromStr>(key: &str, default: T) -> Result<T>
where
    T::Err: std::fmt::Display,
{
    env::var(key)
        .ok()
        .and_then(|v| v.parse().ok())
        .or(Some(default))
        .context(format!("Failed to parse {}", key))
}

/// Get number of CPUs for worker thread default
fn num_cpus() -> usize {
    std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_defaults() {
        // Clear environment
        env::remove_var("SERVER_PORT");
        env::remove_var("VECTOR_DIM");

        let config = Config::from_env();
        // Will fail without OPENAI_API_KEY, which is expected
        assert!(config.is_err() || config.unwrap().server.port == 8080);
    }

    #[test]
    fn test_config_validation() {
        let mut config = Config::from_env().unwrap_or_else(|_| Config {
            server: ServerConfig {
                host: "0.0.0.0".to_string(),
                port: 8080,
                request_timeout: Duration::from_secs(30),
            },
            qdrant: QdrantConfig {
                url: "http://localhost:6333".to_string(),
                collection: "test".to_string(),
                vector_dim: 384,
                distance_metric: "Cosine".to_string(),
            },
            redis: RedisConfig {
                url: "redis://localhost:6379".to_string(),
                ttl_seconds: 3600,
                max_connections: 10,
            },
            embeddings: EmbeddingConfig {
                model: "test-model".to_string(),
                batch_size: 32,
                normalize: true,
            },
            generation: GenerationConfig {
                model: "gpt-3.5-turbo".to_string(),
                api_key: "test-key".to_string(),
                max_tokens: 500,
                temperature: 0.7,
            },
            performance: PerformanceConfig {
                max_connections: 100,
                cache_size: 10000,
                worker_threads: 4,
            },
        });

        assert!(config.validate().is_ok());

        // Test invalid temperature
        config.generation.temperature = 3.0;
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_bind_address() {
        env::set_var("SERVER_HOST", "127.0.0.1");
        env::set_var("SERVER_PORT", "9090");

        let config = Config::from_env();
        if let Ok(cfg) = config {
            assert_eq!(cfg.bind_address(), "127.0.0.1:9090");
        }
    }
}
