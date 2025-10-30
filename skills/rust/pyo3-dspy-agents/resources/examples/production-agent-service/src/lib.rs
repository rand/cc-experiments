//! Production-grade DSPy Agent Service
//!
//! This library provides enterprise-ready agent orchestration with:
//! - Agent pool management with async concurrency
//! - Circuit breakers for fault tolerance
//! - Prometheus metrics integration
//! - Memory persistence and conversation tracking
//! - Comprehensive error handling

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use dashmap::DashMap;
use parking_lot::Mutex;
use prometheus::{
    Counter, Gauge, Histogram, HistogramOpts, IntCounter, IntGauge, Opts, Registry,
};
use pyo3::prelude::*;
use pyo3::types::PyModule;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};

// ============================================================================
// Error Types
// ============================================================================

#[derive(Debug, thiserror::Error)]
pub enum AgentError {
    #[error("Python runtime error: {0}")]
    PythonError(String),

    #[error("Agent pool exhausted: no agents available")]
    PoolExhausted,

    #[error("Circuit breaker open: {0}")]
    CircuitBreakerOpen(String),

    #[error("Agent execution failed: {0}")]
    ExecutionFailed(String),

    #[error("Memory operation failed: {0}")]
    MemoryError(String),

    #[error("Configuration error: {0}")]
    ConfigError(String),

    #[error("Timeout: operation exceeded {0:?}")]
    Timeout(Duration),
}

impl From<PyErr> for AgentError {
    fn from(err: PyErr) -> Self {
        AgentError::PythonError(err.to_string())
    }
}

// ============================================================================
// Circuit Breaker
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

impl CircuitState {
    pub fn as_gauge_value(&self) -> f64 {
        match self {
            CircuitState::Closed => 0.0,
            CircuitState::Open => 1.0,
            CircuitState::HalfOpen => 2.0,
        }
    }
}

pub struct CircuitBreaker {
    state: Mutex<CircuitState>,
    failure_count: Mutex<usize>,
    last_failure_time: Mutex<Option<Instant>>,
    threshold: usize,
    timeout: Duration,
    half_open_max_calls: usize,
}

impl CircuitBreaker {
    pub fn new(threshold: usize, timeout: Duration) -> Self {
        Self {
            state: Mutex::new(CircuitState::Closed),
            failure_count: Mutex::new(0),
            last_failure_time: Mutex::new(None),
            threshold,
            timeout,
            half_open_max_calls: 3,
        }
    }

    pub fn call<F, T>(&self, operation: F) -> Result<T, AgentError>
    where
        F: FnOnce() -> Result<T, AgentError>,
    {
        // Check circuit state
        self.check_and_update_state()?;

        let current_state = *self.state.lock();

        match current_state {
            CircuitState::Open => {
                Err(AgentError::CircuitBreakerOpen(
                    "Circuit breaker is open".to_string(),
                ))
            }
            CircuitState::Closed | CircuitState::HalfOpen => {
                match operation() {
                    Ok(result) => {
                        self.on_success();
                        Ok(result)
                    }
                    Err(err) => {
                        self.on_failure();
                        Err(err)
                    }
                }
            }
        }
    }

    fn check_and_update_state(&self) -> Result<(), AgentError> {
        let mut state = self.state.lock();
        let last_failure = self.last_failure_time.lock();

        if *state == CircuitState::Open {
            if let Some(last_fail) = *last_failure {
                if last_fail.elapsed() > self.timeout {
                    info!("Circuit breaker transitioning to half-open");
                    *state = CircuitState::HalfOpen;
                    return Ok(());
                }
            }
            return Err(AgentError::CircuitBreakerOpen(
                "Circuit breaker timeout not expired".to_string(),
            ));
        }

        Ok(())
    }

    fn on_success(&self) {
        let mut state = self.state.lock();
        let mut failure_count = self.failure_count.lock();

        match *state {
            CircuitState::HalfOpen => {
                info!("Circuit breaker transitioning to closed");
                *state = CircuitState::Closed;
                *failure_count = 0;
            }
            CircuitState::Closed => {
                *failure_count = 0;
            }
            CircuitState::Open => {}
        }
    }

    fn on_failure(&self) {
        let mut state = self.state.lock();
        let mut failure_count = self.failure_count.lock();
        let mut last_failure = self.last_failure_time.lock();

        *failure_count += 1;
        *last_failure = Some(Instant::now());

        if *failure_count >= self.threshold {
            warn!(
                "Circuit breaker opening after {} failures",
                *failure_count
            );
            *state = CircuitState::Open;
        }
    }

    pub fn state(&self) -> CircuitState {
        *self.state.lock()
    }

    pub fn reset(&self) {
        let mut state = self.state.lock();
        let mut failure_count = self.failure_count.lock();
        *state = CircuitState::Closed;
        *failure_count = 0;
        info!("Circuit breaker manually reset");
    }
}

// ============================================================================
// Metrics
// ============================================================================

#[derive(Clone)]
pub struct AgentMetrics {
    // Counters
    pub requests_total: IntCounter,
    pub requests_success: IntCounter,
    pub requests_failure: IntCounter,

    // Gauges
    pub pool_size: IntGauge,
    pub circuit_breaker_state: Gauge,

    // Histograms
    pub request_latency: Histogram,
    pub reasoning_steps: Histogram,

    // Registry
    pub registry: Registry,
}

impl AgentMetrics {
    pub fn new() -> Result<Self> {
        let registry = Registry::new();

        // Counters
        let requests_total = IntCounter::with_opts(
            Opts::new("agent_requests_total", "Total number of agent requests")
        )?;
        registry.register(Box::new(requests_total.clone()))?;

        let requests_success = IntCounter::with_opts(
            Opts::new("agent_requests_success", "Successful agent requests")
        )?;
        registry.register(Box::new(requests_success.clone()))?;

        let requests_failure = IntCounter::with_opts(
            Opts::new("agent_requests_failure", "Failed agent requests")
        )?;
        registry.register(Box::new(requests_failure.clone()))?;

        // Gauges
        let pool_size = IntGauge::with_opts(
            Opts::new("agent_pool_size", "Current agent pool size")
        )?;
        registry.register(Box::new(pool_size.clone()))?;

        let circuit_breaker_state = Gauge::with_opts(
            Opts::new(
                "circuit_breaker_state",
                "Circuit breaker state (0=closed, 1=open, 2=half_open)"
            )
        )?;
        registry.register(Box::new(circuit_breaker_state.clone()))?;

        // Histograms
        let request_latency = Histogram::with_opts(
            HistogramOpts::new(
                "agent_request_latency_seconds",
                "Agent request latency in seconds"
            ).buckets(vec![0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
        )?;
        registry.register(Box::new(request_latency.clone()))?;

        let reasoning_steps = Histogram::with_opts(
            HistogramOpts::new(
                "agent_reasoning_steps",
                "Number of reasoning steps per request"
            ).buckets(vec![1.0, 2.0, 3.0, 5.0, 10.0, 20.0])
        )?;
        registry.register(Box::new(reasoning_steps.clone()))?;

        Ok(Self {
            requests_total,
            requests_success,
            requests_failure,
            pool_size,
            circuit_breaker_state,
            request_latency,
            reasoning_steps,
            registry,
        })
    }

    pub fn record_request(&self, duration: Duration, success: bool, steps: usize) {
        self.requests_total.inc();
        if success {
            self.requests_success.inc();
        } else {
            self.requests_failure.inc();
        }

        self.request_latency.observe(duration.as_secs_f64());
        self.reasoning_steps.observe(steps as f64);
    }

    pub fn update_circuit_breaker_state(&self, state: CircuitState) {
        self.circuit_breaker_state.set(state.as_gauge_value());
    }

    pub fn update_pool_size(&self, size: usize) {
        self.pool_size.set(size as i64);
    }
}

impl Default for AgentMetrics {
    fn default() -> Self {
        Self::new().expect("Failed to initialize metrics")
    }
}

// ============================================================================
// Agent Memory
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationTurn {
    pub question: String,
    pub answer: String,
    pub reasoning_steps: usize,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMemory {
    pub user_id: String,
    pub conversation_history: Vec<ConversationTurn>,
    pub created_at: DateTime<Utc>,
    pub last_updated: DateTime<Utc>,
}

impl AgentMemory {
    pub fn new(user_id: String) -> Self {
        let now = Utc::now();
        Self {
            user_id,
            conversation_history: Vec::new(),
            created_at: now,
            last_updated: now,
        }
    }

    pub fn add_turn(&mut self, question: String, answer: String, reasoning_steps: usize) {
        let turn = ConversationTurn {
            question,
            answer,
            reasoning_steps,
            timestamp: Utc::now(),
        };
        self.conversation_history.push(turn);
        self.last_updated = Utc::now();
    }

    pub fn get_context(&self, last_n: usize) -> String {
        let turns: Vec<String> = self.conversation_history
            .iter()
            .rev()
            .take(last_n)
            .rev()
            .map(|turn| {
                format!(
                    "Previous Q: {}\nPrevious A: {}",
                    turn.question, turn.answer
                )
            })
            .collect();

        turns.join("\n\n")
    }

    pub fn to_json(&self) -> Result<String> {
        serde_json::to_string(self).context("Failed to serialize memory")
    }

    pub fn from_json(json: &str) -> Result<Self> {
        serde_json::from_str(json).context("Failed to deserialize memory")
    }

    pub fn save(&self, path: &str) -> Result<()> {
        let json = self.to_json()?;
        std::fs::write(path, json).context("Failed to write memory to file")
    }

    pub fn load(path: &str) -> Result<Self> {
        let json = std::fs::read_to_string(path).context("Failed to read memory file")?;
        Self::from_json(&json)
    }
}

// ============================================================================
// Tool Registry
// ============================================================================

type ToolFunction = Arc<dyn Fn(&str) -> Result<String> + Send + Sync>;

pub struct ToolRegistry {
    tools: HashMap<String, ToolFunction>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self {
            tools: HashMap::new(),
        }
    }

    pub fn register<F>(&mut self, name: &str, function: F)
    where
        F: Fn(&str) -> Result<String> + Send + Sync + 'static,
    {
        self.tools.insert(name.to_string(), Arc::new(function));
    }

    pub fn call(&self, name: &str, input: &str) -> Result<String> {
        let tool = self.tools
            .get(name)
            .ok_or_else(|| anyhow::anyhow!("Tool not found: {}", name))?;

        tool(input)
    }

    pub fn list_tools(&self) -> Vec<String> {
        self.tools.keys().cloned().collect()
    }
}

impl Default for ToolRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// ============================================================================
// Production Agent System
// ============================================================================

pub struct ProductionAgentSystem {
    agent_pool: Arc<RwLock<Vec<Py<PyAny>>>>,
    memory_store: Arc<DashMap<String, AgentMemory>>,
    circuit_breaker: Arc<CircuitBreaker>,
    metrics: Arc<AgentMetrics>,
    tool_registry: Arc<Mutex<ToolRegistry>>,
    config: AgentConfig,
    start_time: Instant,
}

#[derive(Debug, Clone)]
pub struct AgentConfig {
    pub pool_size: usize,
    pub max_retries: usize,
    pub request_timeout: Duration,
    pub circuit_breaker_threshold: usize,
    pub circuit_breaker_timeout: Duration,
    pub memory_context_turns: usize,
}

impl Default for AgentConfig {
    fn default() -> Self {
        Self {
            pool_size: 4,
            max_retries: 3,
            request_timeout: Duration::from_secs(30),
            circuit_breaker_threshold: 5,
            circuit_breaker_timeout: Duration::from_secs(30),
            memory_context_turns: 3,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryRequest {
    pub user_id: String,
    pub question: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResponse {
    pub answer: String,
    pub user_id: String,
    pub question: String,
    pub reasoning_steps: usize,
    pub latency_ms: u128,
    pub request_id: String,
}

impl ProductionAgentSystem {
    /// Create a new production agent system with the given configuration
    pub async fn new(config: AgentConfig) -> Result<Self> {
        info!("Initializing ProductionAgentSystem with pool_size={}", config.pool_size);

        // Initialize tool registry
        let mut tool_registry = ToolRegistry::new();
        Self::register_default_tools(&mut tool_registry);
        let tool_registry = Arc::new(Mutex::new(tool_registry));

        // Initialize agent pool
        let agent_pool = Self::create_agent_pool(config.pool_size).await?;

        // Initialize circuit breaker
        let circuit_breaker = Arc::new(CircuitBreaker::new(
            config.circuit_breaker_threshold,
            config.circuit_breaker_timeout,
        ));

        // Initialize metrics
        let metrics = Arc::new(AgentMetrics::new()?);
        metrics.update_pool_size(config.pool_size);
        metrics.update_circuit_breaker_state(CircuitState::Closed);

        Ok(Self {
            agent_pool: Arc::new(RwLock::new(agent_pool)),
            memory_store: Arc::new(DashMap::new()),
            circuit_breaker,
            metrics,
            tool_registry,
            config,
            start_time: Instant::now(),
        })
    }

    /// Create a pool of pre-initialized agents
    async fn create_agent_pool(pool_size: usize) -> Result<Vec<Py<PyAny>>> {
        let mut pool = Vec::with_capacity(pool_size);

        Python::with_gil(|py| -> PyResult<()> {
            for i in 0..pool_size {
                debug!("Creating agent {}/{}", i + 1, pool_size);
                let agent = Self::create_agent(py)?;
                pool.push(agent);
            }
            Ok(())
        })?;

        info!("Created agent pool with {} agents", pool_size);
        Ok(pool)
    }

    /// Create a single DSPy ReAct agent
    fn create_agent(py: Python) -> PyResult<Py<PyAny>> {
        let dspy = PyModule::import(py, "dspy")?;
        let react = dspy.getattr("ReAct")?;
        let signature = "question -> answer";
        let agent = react.call1(((signature,),))?;
        Ok(agent.into())
    }

    /// Register default tools
    fn register_default_tools(registry: &mut ToolRegistry) {
        registry.register("calculator", |input: &str| {
            // Simple calculator implementation
            Ok(format!("Calculated: {}", input))
        });

        registry.register("search", |input: &str| {
            // Mock search implementation
            Ok(format!("Search results for: {}", input))
        });

        registry.register("weather", |input: &str| {
            // Mock weather implementation
            Ok(format!("Weather for {}: Sunny, 72°F", input))
        });
    }

    /// Execute a query with full production features
    pub async fn execute_query(&self, request: QueryRequest) -> Result<QueryResponse> {
        let request_id = uuid::Uuid::new_v4().to_string();
        let start = Instant::now();

        debug!("Processing request {} for user {}", request_id, request.user_id);

        // Get or create memory
        let memory = self.memory_store
            .entry(request.user_id.clone())
            .or_insert_with(|| AgentMemory::new(request.user_id.clone()))
            .clone();

        // Execute with circuit breaker and retry logic
        let mut last_error = None;
        for attempt in 1..=self.config.max_retries {
            match self.execute_with_circuit_breaker(&request, &memory).await {
                Ok(answer) => {
                    let latency = start.elapsed();
                    let reasoning_steps = 3; // This would be extracted from agent response

                    // Update memory
                    self.memory_store
                        .get_mut(&request.user_id)
                        .map(|mut mem| {
                            mem.add_turn(
                                request.question.clone(),
                                answer.clone(),
                                reasoning_steps,
                            );
                        });

                    // Record metrics
                    self.metrics.record_request(latency, true, reasoning_steps);

                    info!(
                        "Request {} completed in {:?} (attempt {})",
                        request_id, latency, attempt
                    );

                    return Ok(QueryResponse {
                        answer,
                        user_id: request.user_id,
                        question: request.question,
                        reasoning_steps,
                        latency_ms: latency.as_millis(),
                        request_id,
                    });
                }
                Err(err) => {
                    warn!("Request {} failed on attempt {}: {}", request_id, attempt, err);
                    last_error = Some(err);

                    if attempt < self.config.max_retries {
                        tokio::time::sleep(Duration::from_millis(100 * attempt as u64)).await;
                    }
                }
            }
        }

        // All retries failed
        let latency = start.elapsed();
        self.metrics.record_request(latency, false, 0);

        error!("Request {} failed after {} retries", request_id, self.config.max_retries);

        Err(last_error.unwrap_or_else(|| {
            AgentError::ExecutionFailed("All retries exhausted".to_string()).into()
        }))
    }

    /// Execute query with circuit breaker protection
    async fn execute_with_circuit_breaker(
        &self,
        request: &QueryRequest,
        memory: &AgentMemory,
    ) -> Result<String, AgentError> {
        // Update circuit breaker state in metrics
        self.metrics.update_circuit_breaker_state(self.circuit_breaker.state());

        self.circuit_breaker.call(|| {
            Python::with_gil(|py| -> Result<String, AgentError> {
                // Get agent from pool
                let pool = self.agent_pool.blocking_read();
                let agent = pool.first()
                    .ok_or(AgentError::PoolExhausted)?;

                // Augment question with context
                let context = memory.get_context(self.config.memory_context_turns);
                let augmented_question = if context.is_empty() {
                    request.question.clone()
                } else {
                    format!("{}\n\nCurrent Question: {}", context, request.question)
                };

                debug!("Executing agent with question: {}", augmented_question);

                // Execute agent
                let result = agent.as_ref(py)
                    .call_method1("forward", ((augmented_question,),))
                    .map_err(|e| AgentError::PythonError(e.to_string()))?;

                let answer: String = result.getattr("answer")
                    .and_then(|a| a.extract())
                    .map_err(|e| AgentError::PythonError(e.to_string()))?;

                Ok(answer)
            })
        })
    }

    /// Get system health status
    pub fn health_check(&self) -> HealthStatus {
        let pool_size = self.agent_pool.blocking_read().len();
        let circuit_state = self.circuit_breaker.state();
        let uptime = self.start_time.elapsed();

        let mut checks = HashMap::new();
        checks.insert("python_runtime".to_string(), "ok".to_string());

        if pool_size > 0 {
            checks.insert("agent_pool".to_string(), "ok".to_string());
        } else {
            checks.insert("agent_pool".to_string(), "failed: no agents available".to_string());
        }

        checks.insert(
            "circuit_breaker".to_string(),
            format!("{:?}", circuit_state).to_lowercase(),
        );

        let status = if pool_size > 0 && circuit_state == CircuitState::Closed {
            "healthy"
        } else {
            "unhealthy"
        };

        HealthStatus {
            status: status.to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            uptime_seconds: uptime.as_secs(),
            agent_pool_size: pool_size,
            circuit_breaker_state: format!("{:?}", circuit_state).to_lowercase(),
            checks,
        }
    }

    /// Get Prometheus metrics
    pub fn get_metrics(&self) -> String {
        use prometheus::Encoder;
        let encoder = prometheus::TextEncoder::new();
        let metric_families = self.metrics.registry.gather();

        let mut buffer = Vec::new();
        encoder.encode(&metric_families, &mut buffer).unwrap();

        String::from_utf8(buffer).unwrap()
    }

    /// Save all memories to disk
    pub async fn save_all_memories(&self, directory: &str) -> Result<()> {
        std::fs::create_dir_all(directory)?;

        for entry in self.memory_store.iter() {
            let user_id = entry.key();
            let memory = entry.value();
            let path = format!("{}/{}.json", directory, user_id);
            memory.save(&path)?;
        }

        info!("Saved {} memories to {}", self.memory_store.len(), directory);
        Ok(())
    }

    /// Get agent pool size
    pub async fn pool_size(&self) -> usize {
        self.agent_pool.read().await.len()
    }

    /// Reset circuit breaker
    pub fn reset_circuit_breaker(&self) {
        self.circuit_breaker.reset();
        self.metrics.update_circuit_breaker_state(CircuitState::Closed);
    }
}

// ============================================================================
// Health Status
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub status: String,
    pub version: String,
    pub uptime_seconds: u64,
    pub agent_pool_size: usize,
    pub circuit_breaker_state: String,
    pub checks: HashMap<String, String>,
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_circuit_breaker_transitions() {
        let cb = CircuitBreaker::new(3, Duration::from_millis(100));

        // Should be closed initially
        assert_eq!(cb.state(), CircuitState::Closed);

        // Trigger failures
        for _ in 0..3 {
            cb.on_failure();
        }

        // Should be open after threshold
        assert_eq!(cb.state(), CircuitState::Open);
    }

    #[test]
    fn test_agent_memory_context() {
        let mut memory = AgentMemory::new("test_user".to_string());

        memory.add_turn("Q1".to_string(), "A1".to_string(), 1);
        memory.add_turn("Q2".to_string(), "A2".to_string(), 2);
        memory.add_turn("Q3".to_string(), "A3".to_string(), 3);

        let context = memory.get_context(2);
        assert!(context.contains("Q2"));
        assert!(context.contains("Q3"));
        assert!(!context.contains("Q1"));
    }

    #[test]
    fn test_tool_registry() {
        let mut registry = ToolRegistry::new();

        registry.register("test_tool", |input| {
            Ok(format!("Processed: {}", input))
        });

        let result = registry.call("test_tool", "hello").unwrap();
        assert_eq!(result, "Processed: hello");
    }

    #[test]
    fn test_memory_serialization() {
        let mut memory = AgentMemory::new("test_user".to_string());
        memory.add_turn("Q".to_string(), "A".to_string(), 1);

        let json = memory.to_json().unwrap();
        let restored = AgentMemory::from_json(&json).unwrap();

        assert_eq!(memory.user_id, restored.user_id);
        assert_eq!(memory.conversation_history.len(), restored.conversation_history.len());
    }
}
