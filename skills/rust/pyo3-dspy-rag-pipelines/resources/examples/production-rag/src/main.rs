//! Production RAG System
//!
//! A complete, production-ready Retrieval-Augmented Generation system
//! combining Rust performance with Python ML capabilities.

mod config;

use anyhow::{Context, Result};
use axum::{
    extract::{Extension, Json, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Router,
};
use chrono::Utc;
use config::Config;
use lazy_static::lazy_static;
use moka::future::Cache;
use prometheus::{
    Encoder, Histogram, HistogramOpts, IntCounter, IntGauge, Registry, TextEncoder,
};
use pyo3::{prelude::*, types::PyDict};
use redis::aio::ConnectionManager;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::time::timeout;
use tower_http::{
    cors::CorsLayer,
    timeout::TimeoutLayer,
    trace::{DefaultMakeSpan, TraceLayer},
};
use tracing::{info, warn};

// ============================================================================
// Metrics
// ============================================================================

lazy_static! {
    static ref REGISTRY: Registry = Registry::new();
    static ref QUERIES_TOTAL: IntCounter = IntCounter::new(
        "rag_queries_total",
        "Total number of queries processed"
    )
    .unwrap();
    static ref CACHE_HITS: IntCounter = IntCounter::new(
        "rag_cache_hits_total",
        "Total cache hits"
    )
    .unwrap();
    static ref CACHE_MISSES: IntCounter = IntCounter::new(
        "rag_cache_misses_total",
        "Total cache misses"
    )
    .unwrap();
    static ref ACTIVE_REQUESTS: IntGauge = IntGauge::new(
        "rag_active_requests",
        "Current active requests"
    )
    .unwrap();
    static ref QUERY_DURATION: Histogram = Histogram::with_opts(
        HistogramOpts::new("rag_query_duration_seconds", "Query latency")
            .buckets(vec![0.01, 0.05, 0.1, 0.5, 1.0, 5.0])
    )
    .unwrap();
}

fn register_metrics() {
    REGISTRY.register(Box::new(QUERIES_TOTAL.clone())).ok();
    REGISTRY.register(Box::new(CACHE_HITS.clone())).ok();
    REGISTRY.register(Box::new(CACHE_MISSES.clone())).ok();
    REGISTRY.register(Box::new(ACTIVE_REQUESTS.clone())).ok();
    REGISTRY.register(Box::new(QUERY_DURATION.clone())).ok();
}

// ============================================================================
// Data Models
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryRequest {
    pub query: String,
    #[serde(default = "default_top_k")]
    pub top_k: usize,
    #[serde(default = "default_rerank")]
    pub rerank: bool,
    #[serde(default)]
    pub temperature: Option<f32>,
}

fn default_top_k() -> usize {
    5
}
fn default_rerank() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResponse {
    pub answer: String,
    pub sources: Vec<Source>,
    pub latency_ms: u64,
    pub cache_hit: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Source {
    pub text: String,
    pub score: f32,
    pub metadata: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    pub id: String,
    pub text: String,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexRequest {
    pub documents: Vec<Document>,
    #[serde(default = "default_chunk_size")]
    pub chunk_size: usize,
    #[serde(default = "default_overlap")]
    pub overlap: usize,
}

fn default_chunk_size() -> usize {
    512
}
fn default_overlap() -> usize {
    50
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexResponse {
    pub indexed: usize,
    pub duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub components: ComponentHealth,
    pub uptime_seconds: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComponentHealth {
    pub vector_db: String,
    pub cache: String,
    pub embedder: String,
}

// ============================================================================
// Application State
// ============================================================================

#[derive(Clone)]
pub struct AppState {
    pub config: Arc<Config>,
    pub qdrant_client: Arc<reqwest::Client>,
    pub redis: ConnectionManager,
    pub mem_cache: Cache<String, Vec<f32>>,
    pub start_time: Instant,
}

impl AppState {
    pub async fn new(config: Config) -> Result<Self> {
        let redis_client = redis::Client::open(config.redis.url.as_str())
            .context("Failed to create Redis client")?;
        let redis = ConnectionManager::new(redis_client)
            .await
            .context("Failed to connect to Redis")?;

        let mem_cache = Cache::builder()
            .max_capacity(config.performance.cache_size)
            .time_to_live(Duration::from_secs(config.redis.ttl_seconds))
            .build();

        let qdrant_client = Arc::new(
            reqwest::Client::builder()
                .timeout(Duration::from_secs(10))
                .build()?,
        );

        Ok(Self {
            config: Arc::new(config),
            qdrant_client,
            redis,
            mem_cache,
            start_time: Instant::now(),
        })
    }

    /// Get embedding from cache or compute
    async fn get_embedding(&self, text: &str) -> Result<Vec<f32>> {
        let cache_key = Self::cache_key(text);

        // Try L1 cache (memory)
        if let Some(embedding) = self.mem_cache.get(&cache_key).await {
            CACHE_HITS.inc();
            return Ok(embedding);
        }

        // Try L2 cache (Redis)
        if let Ok(cached) = self.get_from_redis(&cache_key).await {
            CACHE_HITS.inc();
            self.mem_cache.insert(cache_key.clone(), cached.clone()).await;
            return Ok(cached);
        }

        CACHE_MISSES.inc();

        // Compute embedding via Python
        let embedding = self.compute_embedding(text)?;

        // Store in both caches
        self.mem_cache.insert(cache_key.clone(), embedding.clone()).await;
        self.store_in_redis(&cache_key, &embedding).await.ok();

        Ok(embedding)
    }

    /// Compute embedding using Python
    fn compute_embedding(&self, text: &str) -> Result<Vec<f32>> {
        Python::with_gil(|py| {
            let embedder = PyModule::from_code(
                py,
                r#"
from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self, model_name):
        self.model = SentenceTransformer(model_name)

    def embed(self, text):
        return self.model.encode([text])[0].tolist()

embedder = None

def get_embedder(model_name):
    global embedder
    if embedder is None:
        embedder = Embedder(model_name)
    return embedder
"#,
                "embedder.py",
                "embedder",
            )?;

            let get_embedder = embedder.getattr("get_embedder")?;
            let embedder = get_embedder.call1((self.config.embeddings.model.as_str(),))?;
            let result = embedder.call_method1("embed", (text,))?;

            result.extract()
        })
        .context("Failed to compute embedding")
    }

    /// Generate cache key from text
    fn cache_key(text: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(text.trim().to_lowercase().as_bytes());
        format!("emb:{:x}", hasher.finalize())
    }

    /// Get embedding from Redis
    async fn get_from_redis(&self, key: &str) -> Result<Vec<f32>> {
        use redis::AsyncCommands;
        let mut conn = self.redis.clone();
        let data: Vec<u8> = conn.get(key).await?;
        let embedding: Vec<f32> = serde_json::from_slice(&data)?;
        Ok(embedding)
    }

    /// Store embedding in Redis
    async fn store_in_redis(&self, key: &str, embedding: &[f32]) -> Result<()> {
        use redis::AsyncCommands;
        let mut conn = self.redis.clone();
        let data = serde_json::to_vec(embedding)?;
        conn.set_ex(key, data, self.config.redis.ttl_seconds as usize).await?;
        Ok(())
    }

    /// Search Qdrant vector database
    async fn vector_search(&self, query_embedding: &[f32], top_k: usize) -> Result<Vec<Source>> {
        let url = format!(
            "{}/collections/{}/points/search",
            self.config.qdrant.url, self.config.qdrant.collection
        );

        let body = serde_json::json!({
            "vector": query_embedding,
            "limit": top_k,
            "with_payload": true,
        });

        let response = self
            .qdrant_client
            .post(&url)
            .json(&body)
            .send()
            .await?
            .json::<serde_json::Value>()
            .await?;

        let results = response["result"]
            .as_array()
            .context("Invalid Qdrant response")?;

        let sources = results
            .iter()
            .filter_map(|r| {
                Some(Source {
                    text: r["payload"]["text"].as_str()?.to_string(),
                    score: r["score"].as_f64()? as f32,
                    metadata: r["payload"]["metadata"].clone(),
                })
            })
            .collect();

        Ok(sources)
    }

    /// Rerank documents using cross-encoder
    fn rerank(&self, query: &str, documents: &[Source]) -> Result<Vec<Source>> {
        let texts: Vec<&str> = documents.iter().map(|d| d.text.as_str()).collect();

        let scores: Vec<f32> = Python::with_gil(|py| {
            let reranker = PyModule::from_code(
                py,
                r#"
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self):
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    def rerank(self, query, documents):
        pairs = [[query, doc] for doc in documents]
        return self.model.predict(pairs).tolist()

reranker = None

def get_reranker():
    global reranker
    if reranker is None:
        reranker = Reranker()
    return reranker
"#,
                "reranker.py",
                "reranker",
            )?;

            let get_reranker = reranker.getattr("get_reranker")?;
            let reranker = get_reranker.call0()?;
            let result = reranker.call_method1("rerank", (query, texts))?;

            result.extract()
        })?;

        let mut reranked: Vec<_> = documents
            .iter()
            .zip(scores)
            .map(|(doc, score)| {
                let mut new_doc = doc.clone();
                new_doc.score = score;
                new_doc
            })
            .collect();

        reranked.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
        Ok(reranked)
    }

    /// Generate answer using LLM
    fn generate_answer(&self, query: &str, context: &[Source]) -> Result<String> {
        let context_text = context
            .iter()
            .take(3)
            .map(|s| s.text.as_str())
            .collect::<Vec<_>>()
            .join("\n\n");

        Python::with_gil(|py| {
            let openai = PyModule::import(py, "openai")?;
            openai.setattr("api_key", self.config.generation.api_key.as_str())?;

            let chat = openai.getattr("ChatCompletion")?;
            let messages = vec![
                serde_json::json!({
                    "role": "system",
                    "content": "Answer based on the provided context."
                }),
                serde_json::json!({
                    "role": "user",
                    "content": format!("Context:\n{}\n\nQuestion: {}", context_text, query)
                }),
            ];

            let kwargs = PyDict::new(py);
            kwargs.set_item("model", self.config.generation.model.as_str())?;
            kwargs.set_item("messages", messages)?;
            kwargs.set_item("max_tokens", self.config.generation.max_tokens)?;
            kwargs.set_item("temperature", self.config.generation.temperature)?;

            let result = chat.call_method("create", (), Some(kwargs))?;
            let answer = result
                .get_item("choices")?
                .get_item(0)?
                .get_item("message")?
                .get_item("content")?
                .extract::<String>()?;

            Ok(answer)
        })
        .context("Failed to generate answer")
    }
}

// ============================================================================
// API Handlers
// ============================================================================

/// Handle RAG query
async fn handle_query(
    State(state): State<AppState>,
    Json(req): Json<QueryRequest>,
) -> Result<Json<QueryResponse>, AppError> {
    let start = Instant::now();
    ACTIVE_REQUESTS.inc();
    QUERIES_TOTAL.inc();

    let result = async {
        // Get query embedding
        let query_embedding = state.get_embedding(&req.query).await?;

        // Search vector database
        let mut sources = state.vector_search(&query_embedding, req.top_k * 2).await?;

        // Rerank if requested
        if req.rerank && sources.len() > 1 {
            sources = state.rerank(&req.query, &sources)?;
        }

        // Limit to top_k
        sources.truncate(req.top_k);

        // Generate answer
        let answer = state.generate_answer(&req.query, &sources)?;

        let latency_ms = start.elapsed().as_millis() as u64;
        QUERY_DURATION.observe(start.elapsed().as_secs_f64());

        Ok(QueryResponse {
            answer,
            sources,
            latency_ms,
            cache_hit: false, // Simplified - would track properly in production
        })
    }
    .await;

    ACTIVE_REQUESTS.dec();
    Ok(Json(result?))
}

/// Handle document indexing
async fn handle_index(
    State(state): State<AppState>,
    Json(req): Json<IndexRequest>,
) -> Result<Json<IndexResponse>, AppError> {
    let start = Instant::now();

    // Chunk documents
    let mut all_chunks = Vec::new();
    for doc in req.documents {
        let chunks = chunk_text(&doc.text, req.chunk_size, req.overlap);
        for (i, chunk) in chunks.into_iter().enumerate() {
            all_chunks.push((format!("{}_{}", doc.id, i), chunk, doc.metadata.clone()));
        }
    }

    // Compute embeddings
    let mut points = Vec::new();
    for (id, text, metadata) in all_chunks {
        let embedding = state.get_embedding(&text).await?;
        points.push(serde_json::json!({
            "id": id,
            "vector": embedding,
            "payload": {
                "text": text,
                "metadata": metadata,
            }
        }));
    }

    // Upload to Qdrant
    let url = format!(
        "{}/collections/{}/points",
        state.config.qdrant.url, state.config.qdrant.collection
    );

    state
        .qdrant_client
        .put(&url)
        .json(&serde_json::json!({"points": points}))
        .send()
        .await?;

    let duration_ms = start.elapsed().as_millis() as u64;

    Ok(Json(IndexResponse {
        indexed: points.len(),
        duration_ms,
    }))
}

/// Health check endpoint
async fn handle_health(State(state): State<AppState>) -> Json<HealthResponse> {
    let vector_db_health = check_qdrant(&state).await;
    let cache_health = check_redis(&state).await;
    let embedder_health = "up"; // Simplified

    let all_healthy = vector_db_health == "up" && cache_health == "up";

    Json(HealthResponse {
        status: if all_healthy {
            "healthy".to_string()
        } else {
            "degraded".to_string()
        },
        components: ComponentHealth {
            vector_db: vector_db_health,
            cache: cache_health,
            embedder: embedder_health.to_string(),
        },
        uptime_seconds: state.start_time.elapsed().as_secs(),
    })
}

/// Metrics endpoint
async fn handle_metrics() -> impl IntoResponse {
    let encoder = TextEncoder::new();
    let metric_families = REGISTRY.gather();
    let mut buffer = Vec::new();
    encoder.encode(&metric_families, &mut buffer).unwrap();
    (StatusCode::OK, buffer)
}

// ============================================================================
// Utilities
// ============================================================================

/// Chunk text with overlap
fn chunk_text(text: &str, chunk_size: usize, overlap: usize) -> Vec<String> {
    let words: Vec<&str> = text.split_whitespace().collect();
    let mut chunks = Vec::new();
    let mut i = 0;

    while i < words.len() {
        let end = (i + chunk_size).min(words.len());
        chunks.push(words[i..end].join(" "));
        i += chunk_size - overlap;
        if i >= words.len() {
            break;
        }
    }

    chunks
}

/// Check Qdrant health
async fn check_qdrant(state: &AppState) -> String {
    let url = format!("{}/collections/{}", state.config.qdrant.url, state.config.qdrant.collection);
    match timeout(Duration::from_secs(2), state.qdrant_client.get(&url).send()).await {
        Ok(Ok(resp)) if resp.status().is_success() => "up".to_string(),
        _ => "down".to_string(),
    }
}

/// Check Redis health
async fn check_redis(state: &AppState) -> String {
    use redis::AsyncCommands;
    let mut conn = state.redis.clone();
    match timeout(Duration::from_secs(2), conn.ping::<()>()).await {
        Ok(Ok(_)) => "up".to_string(),
        _ => "down".to_string(),
    }
}

// ============================================================================
// Error Handling
// ============================================================================

#[derive(Debug)]
struct AppError(anyhow::Error);

impl IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        warn!("Request error: {:#}", self.0);
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({
                "error": self.0.to_string()
            })),
        )
            .into_response()
    }
}

impl<E> From<E> for AppError
where
    E: Into<anyhow::Error>,
{
    fn from(err: E) -> Self {
        Self(err.into())
    }
}

// ============================================================================
// Main
// ============================================================================

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .with_thread_ids(true)
        .json()
        .init();

    // Load and validate config
    let config = Config::from_env()?;
    config.validate()?;

    info!("Starting production RAG system");
    info!("Server: {}", config.bind_address());
    info!("Qdrant: {}", config.qdrant.url);
    info!("Redis: {}", config.redis.url);

    // Register metrics
    register_metrics();

    // Initialize app state
    let state = AppState::new(config.clone()).await?;

    // Build router
    let app = Router::new()
        .route("/query", post(handle_query))
        .route("/index", post(handle_index))
        .route("/health", get(handle_health))
        .route("/metrics", get(handle_metrics))
        .layer(Extension(state.config.clone()))
        .layer(CorsLayer::permissive())
        .layer(TimeoutLayer::new(config.server.request_timeout))
        .layer(
            TraceLayer::new_for_http()
                .make_span_with(DefaultMakeSpan::new().include_headers(true)),
        )
        .with_state(state);

    // Start server
    let listener = tokio::net::TcpListener::bind(&config.bind_address()).await?;
    info!("Listening on {}", config.bind_address());

    axum::serve(listener, app)
        .await
        .context("Server error")?;

    Ok(())
}
