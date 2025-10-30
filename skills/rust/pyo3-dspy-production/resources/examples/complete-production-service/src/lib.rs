//! Complete Production DSpy Service
//!
//! A production-ready service integrating all patterns:
//! - Multi-level caching (memory + Redis)
//! - Circuit breakers
//! - Prometheus metrics
//! - Structured logging
//! - Cost tracking
//! - Health checks
//! - Configuration management
//! - A/B testing support

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use failsafe::{CircuitBreaker, Config as CircuitConfig, Error as CircuitError};
use lazy_static::lazy_static;
use moka::future::Cache;
use parking_lot::RwLock;
use prometheus::{
    register_counter_vec, register_gauge_vec, register_histogram_vec, CounterVec, Encoder,
    GaugeVec, HistogramVec, TextEncoder,
};
use pyo3::prelude::*;
use redis::aio::ConnectionManager;
use redis::AsyncCommands;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tracing::{debug, error, info, instrument, warn};
use uuid::Uuid;

// =============================================================================
// Metrics
// =============================================================================

lazy_static! {
    /// Total predictions counter by model variant
    static ref PREDICTIONS_TOTAL: CounterVec = register_counter_vec!(
        "dspy_predictions_total",
        "Total number of predictions",
        &["model", "variant", "status"]
    )
    .unwrap();

    /// Prediction latency histogram by model variant
    static ref PREDICTION_LATENCY: HistogramVec = register_histogram_vec!(
        "dspy_prediction_duration_seconds",
        "Prediction duration in seconds",
        &["model", "variant"],
        vec![0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    .unwrap();

    /// Cache hit/miss counter
    static ref CACHE_OPERATIONS: CounterVec = register_counter_vec!(
        "dspy_cache_operations_total",
        "Cache operations",
        &["level", "operation"]
    )
    .unwrap();

    /// Circuit breaker state
    static ref CIRCUIT_BREAKER_STATE: GaugeVec = register_gauge_vec!(
        "dspy_circuit_breaker_state",
        "Circuit breaker state (0=closed, 1=open, 2=half-open)",
        &["model"]
    )
    .unwrap();

    /// Cost tracking
    static ref PREDICTION_COST: CounterVec = register_counter_vec!(
        "dspy_prediction_cost_total",
        "Total prediction cost in USD",
        &["model", "variant"]
    )
    .unwrap();

    /// Token usage
    static ref TOKEN_USAGE: CounterVec = register_counter_vec!(
        "dspy_token_usage_total",
        "Total tokens used",
        &["model", "variant", "type"]
    )
    .unwrap();

    /// Active predictions
    static ref ACTIVE_PREDICTIONS: GaugeVec = register_gauge_vec!(
        "dspy_active_predictions",
        "Number of predictions in flight",
        &["model"]
    )
    .unwrap();

    /// Error counter
    static ref ERRORS_TOTAL: CounterVec = register_counter_vec!(
        "dspy_errors_total",
        "Total errors",
        &["model", "error_type"]
    )
    .unwrap();
}

// =============================================================================
// Configuration
// =============================================================================

#[derive(Debug, Clone, Deserialize)]
pub struct ServiceConfig {
    /// Service name
    pub service_name: String,

    /// Service version
    pub service_version: String,

    /// Redis connection URL
    pub redis_url: String,

    /// Memory cache size
    #[serde(default = "default_cache_size")]
    pub memory_cache_size: u64,

    /// Memory cache TTL in seconds
    #[serde(default = "default_cache_ttl")]
    pub memory_cache_ttl_secs: u64,

    /// Redis cache TTL in seconds
    #[serde(default = "default_redis_ttl")]
    pub redis_cache_ttl_secs: u64,

    /// Circuit breaker failure threshold
    #[serde(default = "default_failure_threshold")]
    pub circuit_breaker_failure_threshold: u32,

    /// Circuit breaker success threshold
    #[serde(default = "default_success_threshold")]
    pub circuit_breaker_success_threshold: u32,

    /// Circuit breaker timeout in seconds
    #[serde(default = "default_circuit_timeout")]
    pub circuit_breaker_timeout_secs: u64,

    /// Model configurations
    pub models: HashMap<String, ModelConfig>,

    /// A/B testing enabled
    #[serde(default)]
    pub ab_testing_enabled: bool,

    /// Default model variant
    #[serde(default = "default_variant")]
    pub default_variant: String,
}

fn default_cache_size() -> u64 {
    10_000
}
fn default_cache_ttl() -> u64 {
    300
}
fn default_redis_ttl() -> u64 {
    3600
}
fn default_failure_threshold() -> u32 {
    5
}
fn default_success_threshold() -> u32 {
    2
}
fn default_circuit_timeout() -> u64 {
    60
}
fn default_variant() -> String {
    "baseline".to_string()
}

#[derive(Debug, Clone, Deserialize)]
pub struct ModelConfig {
    /// Model name (e.g., "gpt-4", "gpt-3.5-turbo")
    pub name: String,

    /// Cost per 1K input tokens
    pub cost_per_1k_input_tokens: f64,

    /// Cost per 1K output tokens
    pub cost_per_1k_output_tokens: f64,

    /// Max retries
    #[serde(default = "default_max_retries")]
    pub max_retries: u32,

    /// Request timeout in seconds
    #[serde(default = "default_request_timeout")]
    pub request_timeout_secs: u64,
}

fn default_max_retries() -> u32 {
    3
}
fn default_request_timeout() -> u64 {
    30
}

// =============================================================================
// Data Types
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictionRequest {
    pub request_id: String,
    pub model: String,
    pub variant: Option<String>,
    pub input: String,
    pub parameters: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub use_cache: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictionResponse {
    pub request_id: String,
    pub model: String,
    pub variant: String,
    pub output: String,
    pub metadata: PredictionMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictionMetadata {
    pub latency_ms: u64,
    pub cached: bool,
    pub cache_level: Option<String>,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub cost_usd: f64,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct CachedPrediction {
    output: String,
    input_tokens: u64,
    output_tokens: u64,
    timestamp: DateTime<Utc>,
}

// =============================================================================
// Cost Tracking
// =============================================================================

#[derive(Debug)]
pub struct CostTracker {
    costs: Arc<RwLock<HashMap<String, CostMetrics>>>,
}

#[derive(Debug, Clone, Default, Serialize)]
pub struct CostMetrics {
    pub total_requests: u64,
    pub total_input_tokens: u64,
    pub total_output_tokens: u64,
    pub total_cost_usd: f64,
    pub last_updated: Option<DateTime<Utc>>,
}

impl CostTracker {
    pub fn new() -> Self {
        Self {
            costs: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn record_prediction(
        &self,
        model: &str,
        variant: &str,
        input_tokens: u64,
        output_tokens: u64,
        cost: f64,
    ) {
        let key = format!("{}:{}", model, variant);
        let mut costs = self.costs.write();
        let metrics = costs.entry(key).or_default();

        metrics.total_requests += 1;
        metrics.total_input_tokens += input_tokens;
        metrics.total_output_tokens += output_tokens;
        metrics.total_cost_usd += cost;
        metrics.last_updated = Some(Utc::now());

        // Update Prometheus metrics
        TOKEN_USAGE
            .with_label_values(&[model, variant, "input"])
            .inc_by(input_tokens as f64);
        TOKEN_USAGE
            .with_label_values(&[model, variant, "output"])
            .inc_by(output_tokens as f64);
        PREDICTION_COST
            .with_label_values(&[model, variant])
            .inc_by(cost);
    }

    pub fn get_metrics(&self, model: &str, variant: &str) -> Option<CostMetrics> {
        let key = format!("{}:{}", model, variant);
        self.costs.read().get(&key).cloned()
    }

    pub fn get_all_metrics(&self) -> HashMap<String, CostMetrics> {
        self.costs.read().clone()
    }
}

impl Default for CostTracker {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// Health Check
// =============================================================================

#[derive(Debug, Clone, Serialize)]
pub struct HealthStatus {
    pub status: String,
    pub version: String,
    pub uptime_secs: u64,
    pub redis_connected: bool,
    pub python_initialized: bool,
    pub cache_size: u64,
    pub circuit_breakers: HashMap<String, String>,
}

// =============================================================================
// Production DSpy Service
// =============================================================================

pub struct ProductionDSpyService {
    config: ServiceConfig,
    memory_cache: Cache<String, CachedPrediction>,
    redis_client: redis::Client,
    redis_conn: Arc<tokio::sync::Mutex<Option<ConnectionManager>>>,
    circuit_breakers: Arc<RwLock<HashMap<String, Arc<CircuitBreaker>>>>,
    cost_tracker: Arc<CostTracker>,
    start_time: Instant,
}

impl ProductionDSpyService {
    /// Create a new production service
    #[instrument(skip(config))]
    pub async fn new(config: ServiceConfig) -> Result<Self> {
        info!(
            service_name = %config.service_name,
            service_version = %config.service_version,
            "Initializing production DSpy service"
        );

        // Initialize Python
        pyo3::prepare_freethreaded_python();
        info!("Python interpreter initialized");

        // Build memory cache
        let memory_cache = Cache::builder()
            .max_capacity(config.memory_cache_size)
            .time_to_live(Duration::from_secs(config.memory_cache_ttl_secs))
            .build();
        info!(
            size = config.memory_cache_size,
            ttl_secs = config.memory_cache_ttl_secs,
            "Memory cache initialized"
        );

        // Connect to Redis
        let redis_client = redis::Client::open(config.redis_url.clone())
            .context("Failed to create Redis client")?;

        let redis_conn = match ConnectionManager::new(redis_client.clone()).await {
            Ok(conn) => {
                info!("Redis connection established");
                Some(conn)
            }
            Err(e) => {
                warn!("Failed to connect to Redis: {}. Running without Redis cache.", e);
                None
            }
        };

        // Initialize circuit breakers for each model
        let mut circuit_breakers = HashMap::new();
        for (model_key, _) in &config.models {
            let cb_config = CircuitConfig::new()
                .failure_threshold(config.circuit_breaker_failure_threshold)
                .success_threshold(config.circuit_breaker_success_threshold)
                .timeout(Duration::from_secs(config.circuit_breaker_timeout_secs));

            let circuit_breaker = Arc::new(CircuitBreaker::new(cb_config));
            circuit_breakers.insert(model_key.clone(), circuit_breaker);

            info!(
                model = %model_key,
                failure_threshold = config.circuit_breaker_failure_threshold,
                "Circuit breaker initialized"
            );
        }

        let cost_tracker = Arc::new(CostTracker::new());

        Ok(Self {
            config,
            memory_cache,
            redis_client,
            redis_conn: Arc::new(tokio::sync::Mutex::new(redis_conn)),
            circuit_breakers: Arc::new(RwLock::new(circuit_breakers)),
            cost_tracker,
            start_time: Instant::now(),
        })
    }

    /// Make a prediction with full production features
    #[instrument(skip(self, request), fields(request_id = %request.request_id, model = %request.model))]
    pub async fn predict(&self, request: PredictionRequest) -> Result<PredictionResponse> {
        let start = Instant::now();
        let variant = request
            .variant
            .clone()
            .unwrap_or_else(|| self.config.default_variant.clone());

        info!(
            request_id = %request.request_id,
            model = %request.model,
            variant = %variant,
            "Processing prediction request"
        );

        // Increment active predictions gauge
        ACTIVE_PREDICTIONS
            .with_label_values(&[&request.model])
            .inc();

        let result = self.predict_internal(request, variant.clone()).await;

        // Decrement active predictions gauge
        ACTIVE_PREDICTIONS
            .with_label_values(&[&result.as_ref().map(|r| r.model.as_str()).unwrap_or("")])
            .dec();

        match &result {
            Ok(response) => {
                let latency = start.elapsed();
                PREDICTIONS_TOTAL
                    .with_label_values(&[&response.model, &variant, "success"])
                    .inc();
                PREDICTION_LATENCY
                    .with_label_values(&[&response.model, &variant])
                    .observe(latency.as_secs_f64());

                info!(
                    request_id = %response.request_id,
                    model = %response.model,
                    variant = %variant,
                    latency_ms = response.metadata.latency_ms,
                    cached = response.metadata.cached,
                    cost_usd = response.metadata.cost_usd,
                    "Prediction completed successfully"
                );
            }
            Err(e) => {
                PREDICTIONS_TOTAL
                    .with_label_values(&["", &variant, "error"])
                    .inc();
                ERRORS_TOTAL
                    .with_label_values(&["", "prediction_error"])
                    .inc();

                error!(
                    error = %e,
                    "Prediction failed"
                );
            }
        }

        result
    }

    async fn predict_internal(
        &self,
        request: PredictionRequest,
        variant: String,
    ) -> Result<PredictionResponse> {
        let start = Instant::now();

        // Check cache if enabled
        if request.use_cache {
            if let Some(cached) = self.check_cache(&request).await? {
                info!(
                    request_id = %request.request_id,
                    cache_level = %cached.1,
                    "Cache hit"
                );

                let model_config = self
                    .config
                    .models
                    .get(&request.model)
                    .context("Model not configured")?;

                let cost = self.calculate_cost(
                    model_config,
                    cached.0.input_tokens,
                    cached.0.output_tokens,
                );

                return Ok(PredictionResponse {
                    request_id: request.request_id.clone(),
                    model: request.model.clone(),
                    variant: variant.clone(),
                    output: cached.0.output,
                    metadata: PredictionMetadata {
                        latency_ms: start.elapsed().as_millis() as u64,
                        cached: true,
                        cache_level: Some(cached.1),
                        input_tokens: cached.0.input_tokens,
                        output_tokens: cached.0.output_tokens,
                        cost_usd: cost,
                        timestamp: Utc::now(),
                    },
                });
            }
        }

        // Get circuit breaker
        let circuit_breaker = {
            let breakers = self.circuit_breakers.read();
            breakers
                .get(&request.model)
                .cloned()
                .context("Circuit breaker not found for model")?
        };

        // Update circuit breaker state metric
        let state_value = match circuit_breaker.state() {
            failsafe::State::Closed => 0.0,
            failsafe::State::Open => 1.0,
            failsafe::State::HalfOpen => 2.0,
        };
        CIRCUIT_BREAKER_STATE
            .with_label_values(&[&request.model])
            .set(state_value);

        // Execute prediction with circuit breaker
        let prediction_result = circuit_breaker
            .call(|| self.execute_prediction(&request, &variant))
            .await;

        let (output, input_tokens, output_tokens) = match prediction_result {
            Ok(result) => result,
            Err(CircuitError::Inner(e)) => {
                ERRORS_TOTAL
                    .with_label_values(&[&request.model, "execution_error"])
                    .inc();
                return Err(e);
            }
            Err(CircuitError::Rejected) => {
                ERRORS_TOTAL
                    .with_label_values(&[&request.model, "circuit_breaker_open"])
                    .inc();
                anyhow::bail!("Circuit breaker open for model {}", request.model);
            }
        };

        // Calculate cost
        let model_config = self
            .config
            .models
            .get(&request.model)
            .context("Model not configured")?;
        let cost = self.calculate_cost(model_config, input_tokens, output_tokens);

        // Record cost
        self.cost_tracker.record_prediction(
            &request.model,
            &variant,
            input_tokens,
            output_tokens,
            cost,
        );

        // Cache the result
        if request.use_cache {
            let cached = CachedPrediction {
                output: output.clone(),
                input_tokens,
                output_tokens,
                timestamp: Utc::now(),
            };
            self.store_in_cache(&request, &cached).await?;
        }

        Ok(PredictionResponse {
            request_id: request.request_id,
            model: request.model,
            variant,
            output,
            metadata: PredictionMetadata {
                latency_ms: start.elapsed().as_millis() as u64,
                cached: false,
                cache_level: None,
                input_tokens,
                output_tokens,
                cost_usd: cost,
                timestamp: Utc::now(),
            },
        })
    }

    async fn execute_prediction(
        &self,
        request: &PredictionRequest,
        variant: &str,
    ) -> Result<(String, u64, u64)> {
        debug!(
            request_id = %request.request_id,
            model = %request.model,
            variant = %variant,
            "Executing Python prediction"
        );

        // Execute Python code
        let output = Python::with_gil(|py| {
            // Simulate DSpy prediction
            // In production, this would call actual DSpy code
            let result = format!(
                "Prediction for input '{}' using model {} ({})",
                request.input, request.model, variant
            );

            Ok::<String, anyhow::Error>(result)
        })?;

        // Simulate token counting
        let input_tokens = (request.input.len() / 4) as u64;
        let output_tokens = (output.len() / 4) as u64;

        debug!(
            request_id = %request.request_id,
            input_tokens = input_tokens,
            output_tokens = output_tokens,
            "Prediction executed"
        );

        Ok((output, input_tokens, output_tokens))
    }

    fn calculate_cost(&self, model_config: &ModelConfig, input_tokens: u64, output_tokens: u64) -> f64 {
        let input_cost = (input_tokens as f64 / 1000.0) * model_config.cost_per_1k_input_tokens;
        let output_cost = (output_tokens as f64 / 1000.0) * model_config.cost_per_1k_output_tokens;
        input_cost + output_cost
    }

    fn make_cache_key(&self, request: &PredictionRequest) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        request.model.hash(&mut hasher);
        request.input.hash(&mut hasher);
        format!("{:x}", hasher.finish())
    }

    async fn check_cache(
        &self,
        request: &PredictionRequest,
    ) -> Result<Option<(CachedPrediction, String)>> {
        let cache_key = self.make_cache_key(request);

        // Check memory cache first
        if let Some(cached) = self.memory_cache.get(&cache_key).await {
            CACHE_OPERATIONS
                .with_label_values(&["memory", "hit"])
                .inc();
            debug!(cache_key = %cache_key, "Memory cache hit");
            return Ok(Some((cached, "memory".to_string())));
        }
        CACHE_OPERATIONS
            .with_label_values(&["memory", "miss"])
            .inc();

        // Check Redis cache
        let mut conn_guard = self.redis_conn.lock().await;
        if let Some(conn) = conn_guard.as_mut() {
            match conn.get::<_, String>(&cache_key).await {
                Ok(data) => {
                    if let Ok(cached) = serde_json::from_str::<CachedPrediction>(&data) {
                        // Store in memory cache for future hits
                        self.memory_cache
                            .insert(cache_key.clone(), cached.clone())
                            .await;

                        CACHE_OPERATIONS
                            .with_label_values(&["redis", "hit"])
                            .inc();
                        debug!(cache_key = %cache_key, "Redis cache hit");
                        return Ok(Some((cached, "redis".to_string())));
                    }
                }
                Err(_) => {
                    CACHE_OPERATIONS
                        .with_label_values(&["redis", "miss"])
                        .inc();
                }
            }
        }

        Ok(None)
    }

    async fn store_in_cache(&self, request: &PredictionRequest, cached: &CachedPrediction) -> Result<()> {
        let cache_key = self.make_cache_key(request);

        // Store in memory cache
        self.memory_cache
            .insert(cache_key.clone(), cached.clone())
            .await;
        debug!(cache_key = %cache_key, "Stored in memory cache");

        // Store in Redis cache
        let mut conn_guard = self.redis_conn.lock().await;
        if let Some(conn) = conn_guard.as_mut() {
            let data = serde_json::to_string(cached)?;
            let ttl_secs = self.config.redis_cache_ttl_secs as usize;

            if let Err(e) = conn
                .set_ex::<_, _, ()>(&cache_key, data, ttl_secs)
                .await
            {
                warn!(error = %e, "Failed to store in Redis cache");
            } else {
                debug!(cache_key = %cache_key, ttl_secs = ttl_secs, "Stored in Redis cache");
            }
        }

        Ok(())
    }

    /// Get health status
    pub async fn health(&self) -> HealthStatus {
        let redis_connected = {
            let conn_guard = self.redis_conn.lock().await;
            conn_guard.is_some()
        };

        let cache_size = self.memory_cache.entry_count();

        let circuit_breakers: HashMap<String, String> = {
            let breakers = self.circuit_breakers.read();
            breakers
                .iter()
                .map(|(k, v)| {
                    let state = match v.state() {
                        failsafe::State::Closed => "closed",
                        failsafe::State::Open => "open",
                        failsafe::State::HalfOpen => "half-open",
                    };
                    (k.clone(), state.to_string())
                })
                .collect()
        };

        HealthStatus {
            status: "healthy".to_string(),
            version: self.config.service_version.clone(),
            uptime_secs: self.start_time.elapsed().as_secs(),
            redis_connected,
            python_initialized: true,
            cache_size,
            circuit_breakers,
        }
    }

    /// Get readiness status
    pub async fn ready(&self) -> bool {
        // Check if critical components are ready
        let redis_ok = {
            let mut conn_guard = self.redis_conn.lock().await;
            if let Some(conn) = conn_guard.as_mut() {
                conn.get::<_, Option<String>>("__health_check__")
                    .await
                    .is_ok()
            } else {
                true // Redis is optional
            }
        };

        redis_ok
    }

    /// Get Prometheus metrics
    pub fn metrics(&self) -> Result<String> {
        let encoder = TextEncoder::new();
        let metric_families = prometheus::gather();
        let mut buffer = vec![];
        encoder
            .encode(&metric_families, &mut buffer)
            .context("Failed to encode metrics")?;
        String::from_utf8(buffer).context("Failed to convert metrics to string")
    }

    /// Get cost metrics
    pub fn cost_metrics(&self) -> HashMap<String, CostMetrics> {
        self.cost_tracker.get_all_metrics()
    }

    /// Get configuration
    pub fn config(&self) -> &ServiceConfig {
        &self.config
    }
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn test_config() -> ServiceConfig {
        let mut models = HashMap::new();
        models.insert(
            "gpt-3.5-turbo".to_string(),
            ModelConfig {
                name: "gpt-3.5-turbo".to_string(),
                cost_per_1k_input_tokens: 0.0015,
                cost_per_1k_output_tokens: 0.002,
                max_retries: 3,
                request_timeout_secs: 30,
            },
        );

        ServiceConfig {
            service_name: "test-service".to_string(),
            service_version: "0.1.0".to_string(),
            redis_url: "redis://localhost:6379".to_string(),
            memory_cache_size: 100,
            memory_cache_ttl_secs: 60,
            redis_cache_ttl_secs: 300,
            circuit_breaker_failure_threshold: 5,
            circuit_breaker_success_threshold: 2,
            circuit_breaker_timeout_secs: 60,
            models,
            ab_testing_enabled: false,
            default_variant: "baseline".to_string(),
        }
    }

    #[tokio::test]
    async fn test_cost_tracker() {
        let tracker = CostTracker::new();

        tracker.record_prediction("gpt-4", "baseline", 100, 50, 0.005);
        tracker.record_prediction("gpt-4", "baseline", 200, 100, 0.010);

        let metrics = tracker.get_metrics("gpt-4", "baseline").unwrap();
        assert_eq!(metrics.total_requests, 2);
        assert_eq!(metrics.total_input_tokens, 300);
        assert_eq!(metrics.total_output_tokens, 150);
        assert_eq!(metrics.total_cost_usd, 0.015);
    }

    #[tokio::test]
    async fn test_cache_key_generation() {
        let config = test_config();
        let service = ProductionDSpyService::new(config)
            .await
            .expect("Failed to create service");

        let request = PredictionRequest {
            request_id: Uuid::new_v4().to_string(),
            model: "gpt-3.5-turbo".to_string(),
            variant: None,
            input: "test input".to_string(),
            parameters: HashMap::new(),
            use_cache: true,
        };

        let key1 = service.make_cache_key(&request);
        let key2 = service.make_cache_key(&request);

        assert_eq!(key1, key2);
    }
}
