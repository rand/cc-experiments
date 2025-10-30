# PyO3 DSPy RAG Pipelines - Complete Reference

Comprehensive guide to building production Retrieval-Augmented Generation (RAG) pipelines with DSPy from Rust using PyO3. Covers vector database integration, retrieval modules, context management, hybrid search, reranking, and production architectures.

## Table of Contents

1. [Vector Database Integration](#vector-database-integration)
2. [Embedding Management](#embedding-management)
3. [DSPy Retrieval Modules](#dspy-retrieval-modules)
4. [RAG Pipeline Patterns](#rag-pipeline-patterns)
5. [Hybrid Search Implementation](#hybrid-search-implementation)
6. [Reranking Strategies](#reranking-strategies)
7. [Context Window Management](#context-window-management)
8. [Document Chunking](#document-chunking)
9. [Production RAG Systems](#production-rag-systems)
10. [Performance Optimization](#performance-optimization)

---

## Vector Database Integration

### ChromaDB Setup

**Cargo.toml**:
```toml
[dependencies]
pyo3 = { version = "0.20", features = ["auto-initialize"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
anyhow = "1.0"
tokio = { version = "1.35", features = ["full"] }
```

**Complete ChromaDB Client**:
```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use anyhow::{Context, Result};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    pub id: String,
    pub text: String,
    pub metadata: Option<serde_json::Value>,
}

#[derive(Debug, Clone)]
pub struct ChromaDBConfig {
    pub persist_directory: Option<String>,
    pub collection_name: String,
    pub embedding_function: Option<String>,
}

pub struct ChromaDBClient {
    client: Py<PyAny>,
    collection: Py<PyAny>,
    config: ChromaDBConfig,
}

impl ChromaDBClient {
    /// Create new ChromaDB client with optional persistence
    pub fn new(config: ChromaDBConfig) -> Result<Self> {
        Python::with_gil(|py| {
            let chromadb = PyModule::import(py, "chromadb")
                .context("Failed to import chromadb")?;

            // Create client
            let client = if let Some(persist_dir) = &config.persist_directory {
                let settings = chromadb.getattr("Settings")?.call1(((),))?;
                settings.setattr("persist_directory", persist_dir)?;
                settings.setattr("anonymized_telemetry", false)?;

                chromadb
                    .getattr("Client")?
                    .call1(((settings,),))?
            } else {
                chromadb.getattr("Client")?.call0()?
            };

            // Get or create collection
            let collection = client.call_method1(
                "get_or_create_collection",
                ((config.collection_name.as_str(),),)
            )?;

            Ok(Self {
                client: client.into(),
                collection: collection.into(),
                config,
            })
        })
    }

    /// Add documents to collection
    pub fn add_documents(&self, documents: Vec<Document>) -> Result<()> {
        Python::with_gil(|py| {
            let collection = self.collection.as_ref(py);

            // Prepare data
            let ids: Vec<String> = documents.iter()
                .map(|d| d.id.clone())
                .collect();

            let texts: Vec<String> = documents.iter()
                .map(|d| d.text.clone())
                .collect();

            let metadatas: Vec<serde_json::Value> = documents.iter()
                .map(|d| d.metadata.clone().unwrap_or_else(|| serde_json::json!({})))
                .collect();

            // Convert to Python
            let py_ids = PyList::new(py, &ids);
            let py_texts = PyList::new(py, &texts);
            let py_metadatas = PyList::new(py, &metadatas.iter()
                .map(|m| m.to_string())
                .collect::<Vec<_>>());

            // Call add method
            let kwargs = PyDict::new(py);
            kwargs.set_item("ids", py_ids)?;
            kwargs.set_item("documents", py_texts)?;
            kwargs.set_item("metadatas", py_metadatas)?;

            collection.call_method("add", (), Some(kwargs))?;

            Ok(())
        })
    }

    /// Query for similar documents
    pub fn query(
        &self,
        query_text: &str,
        n_results: usize,
    ) -> Result<Vec<Document>> {
        Python::with_gil(|py| {
            let collection = self.collection.as_ref(py);

            let kwargs = PyDict::new(py);
            kwargs.set_item("query_texts", vec![query_text])?;
            kwargs.set_item("n_results", n_results)?;

            let results = collection.call_method("query", (), Some(kwargs))?;

            // Extract results
            let ids: Vec<Vec<String>> = results.getattr("ids")?.extract()?;
            let documents: Vec<Vec<String>> = results.getattr("documents")?.extract()?;
            let metadatas: Option<Vec<Vec<serde_json::Value>>> = results
                .getattr("metadatas")
                .ok()
                .and_then(|m| m.extract().ok());

            // Convert to Document structs
            let mut result_docs = Vec::new();

            for (i, id) in ids[0].iter().enumerate() {
                let doc = Document {
                    id: id.clone(),
                    text: documents[0][i].clone(),
                    metadata: metadatas
                        .as_ref()
                        .and_then(|m| m[0].get(i).cloned()),
                };
                result_docs.push(doc);
            }

            Ok(result_docs)
        })
    }

    /// Query with custom embeddings
    pub fn query_with_embeddings(
        &self,
        query_embedding: Vec<f32>,
        n_results: usize,
        filter: Option<serde_json::Value>,
    ) -> Result<Vec<Document>> {
        Python::with_gil(|py| {
            let collection = self.collection.as_ref(py);

            let kwargs = PyDict::new(py);
            kwargs.set_item("query_embeddings", vec![query_embedding])?;
            kwargs.set_item("n_results", n_results)?;

            if let Some(filter_obj) = filter {
                kwargs.set_item("where", filter_obj.to_string())?;
            }

            let results = collection.call_method("query", (), Some(kwargs))?;

            // Extract and convert results
            let ids: Vec<Vec<String>> = results.getattr("ids")?.extract()?;
            let documents: Vec<Vec<String>> = results.getattr("documents")?.extract()?;

            let mut result_docs = Vec::new();
            for (i, id) in ids[0].iter().enumerate() {
                result_docs.push(Document {
                    id: id.clone(),
                    text: documents[0][i].clone(),
                    metadata: None,
                });
            }

            Ok(result_docs)
        })
    }

    /// Delete documents by ID
    pub fn delete(&self, ids: Vec<String>) -> Result<()> {
        Python::with_gil(|py| {
            let collection = self.collection.as_ref(py);
            let py_ids = PyList::new(py, &ids);

            let kwargs = PyDict::new(py);
            kwargs.set_item("ids", py_ids)?;

            collection.call_method("delete", (), Some(kwargs))?;
            Ok(())
        })
    }

    /// Get collection count
    pub fn count(&self) -> Result<usize> {
        Python::with_gil(|py| {
            let collection = self.collection.as_ref(py);
            let count: usize = collection.call_method0("count")?.extract()?;
            Ok(count)
        })
    }
}

// Usage example
fn example_chromadb() -> Result<()> {
    let config = ChromaDBConfig {
        persist_directory: Some("./chroma_db".to_string()),
        collection_name: "documents".to_string(),
        embedding_function: None,
    };

    let client = ChromaDBClient::new(config)?;

    // Add documents
    let docs = vec![
        Document {
            id: "doc1".to_string(),
            text: "Rust is a systems programming language.".to_string(),
            metadata: Some(serde_json::json!({"source": "rust-book"})),
        },
        Document {
            id: "doc2".to_string(),
            text: "Python is great for data science.".to_string(),
            metadata: Some(serde_json::json!({"source": "python-guide"})),
        },
    ];

    client.add_documents(docs)?;

    // Query
    let results = client.query("What is Rust?", 3)?;
    for doc in results {
        println!("Found: {} - {}", doc.id, doc.text);
    }

    Ok(())
}
```

**Best Practice**: Always use persistent storage for production systems. In-memory ChromaDB loses all data on restart.

---

### Qdrant Integration

**Install Qdrant client**:
```bash
pip install qdrant-client
```

**Complete Qdrant Client**:
```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use anyhow::{Context, Result};

#[derive(Debug, Clone)]
pub struct QdrantConfig {
    pub url: String,
    pub collection_name: String,
    pub vector_size: usize,
    pub distance: String, // "Cosine", "Euclid", "Dot"
}

pub struct QdrantClient {
    client: Py<PyAny>,
    config: QdrantConfig,
}

impl QdrantClient {
    pub fn new(config: QdrantConfig) -> Result<Self> {
        Python::with_gil(|py| {
            let qdrant = PyModule::import(py, "qdrant_client")
                .context("Failed to import qdrant_client")?;

            // Create client
            let client = qdrant
                .getattr("QdrantClient")?
                .call1(((config.url.as_str(),),))?;

            // Check if collection exists
            let collections_result = client.call_method0("get_collections")?;
            let collections = collections_result.getattr("collections")?;

            let mut collection_exists = false;
            for collection in collections.iter()? {
                let name: String = collection?.getattr("name")?.extract()?;
                if name == config.collection_name {
                    collection_exists = true;
                    break;
                }
            }

            // Create collection if it doesn't exist
            if !collection_exists {
                let models = PyModule::import(py, "qdrant_client.models")?;

                let distance_enum = models.getattr("Distance")?;
                let distance_value = distance_enum.getattr(config.distance.as_str())?;

                let vector_params = models
                    .getattr("VectorParams")?
                    .call((), Some({
                        let kwargs = PyDict::new(py);
                        kwargs.set_item("size", config.vector_size)?;
                        kwargs.set_item("distance", distance_value)?;
                        kwargs
                    }))?;

                client.call_method1(
                    "create_collection",
                    ((config.collection_name.as_str(), vector_params),)
                )?;
            }

            Ok(Self {
                client: client.into(),
                config,
            })
        })
    }

    /// Upsert documents with embeddings
    pub fn upsert_documents(
        &self,
        documents: Vec<Document>,
        embeddings: Vec<Vec<f32>>,
    ) -> Result<()> {
        if documents.len() != embeddings.len() {
            anyhow::bail!("Documents and embeddings length mismatch");
        }

        Python::with_gil(|py| {
            let client = self.client.as_ref(py);
            let models = PyModule::import(py, "qdrant_client.models")?;
            let point_struct = models.getattr("PointStruct")?;

            // Create points
            let mut points = Vec::new();
            for (doc, embedding) in documents.iter().zip(embeddings.iter()) {
                let payload = PyDict::new(py);
                payload.set_item("text", &doc.text)?;
                payload.set_item("id", &doc.id)?;

                if let Some(metadata) = &doc.metadata {
                    payload.set_item("metadata", metadata.to_string())?;
                }

                let py_embedding = PyList::new(py, embedding);

                let point = point_struct.call((), Some({
                    let kwargs = PyDict::new(py);
                    kwargs.set_item("id", &doc.id)?;
                    kwargs.set_item("vector", py_embedding)?;
                    kwargs.set_item("payload", payload)?;
                    kwargs
                }))?;

                points.push(point);
            }

            let py_points = PyList::new(py, &points);

            client.call_method(
                "upsert",
                (self.config.collection_name.as_str(), py_points),
                None
            )?;

            Ok(())
        })
    }

    /// Search for similar vectors
    pub fn search(
        &self,
        query_vector: Vec<f32>,
        limit: usize,
        filter: Option<serde_json::Value>,
    ) -> Result<Vec<(Document, f32)>> {
        Python::with_gil(|py| {
            let client = self.client.as_ref(py);
            let py_vector = PyList::new(py, &query_vector);

            let kwargs = PyDict::new(py);
            kwargs.set_item("collection_name", self.config.collection_name.as_str())?;
            kwargs.set_item("query_vector", py_vector)?;
            kwargs.set_item("limit", limit)?;

            if let Some(filter_obj) = filter {
                let models = PyModule::import(py, "qdrant_client.models")?;
                // Convert filter to Qdrant filter format
                // This is simplified - production needs proper filter conversion
                kwargs.set_item("query_filter", filter_obj.to_string())?;
            }

            let results = client.call_method("search", (), Some(kwargs))?;

            // Extract results
            let mut documents = Vec::new();

            for result in results.iter()? {
                let result = result?;
                let score: f32 = result.getattr("score")?.extract()?;
                let payload = result.getattr("payload")?;
                let text: String = payload.getattr("text")?.extract()?;
                let id: String = payload.getattr("id")?.extract()?;

                documents.push((
                    Document {
                        id,
                        text,
                        metadata: None,
                    },
                    score,
                ));
            }

            Ok(documents)
        })
    }

    /// Delete documents by filter
    pub fn delete_by_filter(&self, filter: serde_json::Value) -> Result<()> {
        Python::with_gil(|py| {
            let client = self.client.as_ref(py);

            client.call_method(
                "delete",
                (self.config.collection_name.as_str(),),
                Some({
                    let kwargs = PyDict::new(py);
                    kwargs.set_item("points_selector", filter.to_string())?;
                    kwargs
                })
            )?;

            Ok(())
        })
    }

    /// Get collection info
    pub fn get_collection_info(&self) -> Result<serde_json::Value> {
        Python::with_gil(|py| {
            let client = self.client.as_ref(py);

            let info = client.call_method1(
                "get_collection",
                ((self.config.collection_name.as_str(),),)
            )?;

            // Convert to JSON for easier handling in Rust
            let info_str = info.call_method0("__str__")?.extract::<String>()?;

            Ok(serde_json::json!({
                "collection_name": self.config.collection_name,
                "info": info_str
            }))
        })
    }
}
```

**Best Practice**: Use Qdrant for production RAG systems requiring high throughput and advanced filtering capabilities.

---

### Pinecone Integration

**Install Pinecone client**:
```bash
pip install pinecone-client
```

**Pinecone Client**:
```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;
use anyhow::{Context, Result};

#[derive(Debug, Clone)]
pub struct PineconeConfig {
    pub api_key: String,
    pub environment: String,
    pub index_name: String,
    pub dimension: usize,
    pub metric: String, // "cosine", "euclidean", "dotproduct"
}

pub struct PineconeClient {
    index: Py<PyAny>,
    config: PineconeConfig,
}

impl PineconeClient {
    pub fn new(config: PineconeConfig) -> Result<Self> {
        Python::with_gil(|py| {
            let pinecone = PyModule::import(py, "pinecone")
                .context("Failed to import pinecone")?;

            // Initialize Pinecone
            pinecone.call_method(
                "init",
                (),
                Some({
                    let kwargs = PyDict::new(py);
                    kwargs.set_item("api_key", &config.api_key)?;
                    kwargs.set_item("environment", &config.environment)?;
                    kwargs
                })
            )?;

            // Check if index exists
            let list_indexes = pinecone.call_method0("list_indexes")?;
            let indexes: Vec<String> = list_indexes.extract()?;

            if !indexes.contains(&config.index_name) {
                // Create index
                pinecone.call_method(
                    "create_index",
                    (),
                    Some({
                        let kwargs = PyDict::new(py);
                        kwargs.set_item("name", &config.index_name)?;
                        kwargs.set_item("dimension", config.dimension)?;
                        kwargs.set_item("metric", &config.metric)?;
                        kwargs
                    })
                )?;
            }

            // Get index
            let index = pinecone.call_method1(
                "Index",
                ((config.index_name.as_str(),),)
            )?;

            Ok(Self {
                index: index.into(),
                config,
            })
        })
    }

    /// Upsert vectors
    pub fn upsert(
        &self,
        documents: Vec<Document>,
        embeddings: Vec<Vec<f32>>,
    ) -> Result<()> {
        Python::with_gil(|py| {
            let index = self.index.as_ref(py);

            // Prepare vectors
            let vectors: Vec<(String, Vec<f32>, serde_json::Value)> = documents
                .into_iter()
                .zip(embeddings.into_iter())
                .map(|(doc, emb)| {
                    let metadata = serde_json::json!({
                        "text": doc.text,
                        "metadata": doc.metadata.unwrap_or_else(|| serde_json::json!({}))
                    });
                    (doc.id, emb, metadata)
                })
                .collect();

            // Convert to Python format
            let py_vectors: Vec<Py<PyAny>> = vectors
                .into_iter()
                .map(|(id, values, metadata)| {
                    let tuple = PyDict::new(py);
                    tuple.set_item("id", id).unwrap();
                    tuple.set_item("values", values).unwrap();
                    tuple.set_item("metadata", metadata.to_string()).unwrap();
                    tuple.into()
                })
                .collect();

            index.call_method1("upsert", ((py_vectors,),))?;

            Ok(())
        })
    }

    /// Query similar vectors
    pub fn query(
        &self,
        query_vector: Vec<f32>,
        top_k: usize,
        filter: Option<serde_json::Value>,
    ) -> Result<Vec<(Document, f32)>> {
        Python::with_gil(|py| {
            let index = self.index.as_ref(py);

            let kwargs = PyDict::new(py);
            kwargs.set_item("vector", query_vector)?;
            kwargs.set_item("top_k", top_k)?;
            kwargs.set_item("include_metadata", true)?;

            if let Some(filter_obj) = filter {
                kwargs.set_item("filter", filter_obj.to_string())?;
            }

            let results = index.call_method("query", (), Some(kwargs))?;
            let matches = results.getattr("matches")?;

            let mut documents = Vec::new();

            for match_item in matches.iter()? {
                let match_item = match_item?;
                let score: f32 = match_item.getattr("score")?.extract()?;
                let id: String = match_item.getattr("id")?.extract()?;
                let metadata = match_item.getattr("metadata")?;
                let text: String = metadata.getattr("text")?.extract()?;

                documents.push((
                    Document {
                        id,
                        text,
                        metadata: None,
                    },
                    score,
                ));
            }

            Ok(documents)
        })
    }
}
```

**Best Practice**: Use Pinecone for cloud-native RAG systems requiring minimal operational overhead and automatic scaling.

---

## Embedding Management

### Embedding Generation

**OpenAI Embeddings**:
```rust
use pyo3::prelude::*;
use pyo3::types::PyList;
use anyhow::Result;

pub struct OpenAIEmbedder {
    client: Py<PyAny>,
    model: String,
}

impl OpenAIEmbedder {
    pub fn new(model: Option<&str>) -> Result<Self> {
        Python::with_gil(|py| {
            let openai = PyModule::import(py, "openai")?;
            let client = openai.getattr("OpenAI")?.call0()?;

            Ok(Self {
                client: client.into(),
                model: model.unwrap_or("text-embedding-3-small").to_string(),
            })
        })
    }

    pub fn embed(&self, text: &str) -> Result<Vec<f32>> {
        Python::with_gil(|py| {
            let client = self.client.as_ref(py);
            let embeddings = client.getattr("embeddings")?;

            let response = embeddings.call_method(
                "create",
                (),
                Some({
                    let kwargs = PyDict::new(py);
                    kwargs.set_item("input", text)?;
                    kwargs.set_item("model", &self.model)?;
                    kwargs
                })
            )?;

            let data = response.getattr("data")?;
            let first = data.call_method1("__getitem__", ((0,),))?;
            let embedding: Vec<f32> = first.getattr("embedding")?.extract()?;

            Ok(embedding)
        })
    }

    pub fn embed_batch(&self, texts: Vec<String>) -> Result<Vec<Vec<f32>>> {
        Python::with_gil(|py| {
            let client = self.client.as_ref(py);
            let embeddings = client.getattr("embeddings")?;

            let py_texts = PyList::new(py, &texts);

            let response = embeddings.call_method(
                "create",
                (),
                Some({
                    let kwargs = PyDict::new(py);
                    kwargs.set_item("input", py_texts)?;
                    kwargs.set_item("model", &self.model)?;
                    kwargs
                })
            )?;

            let data = response.getattr("data")?;
            let mut embeddings_vec = Vec::new();

            for item in data.iter()? {
                let embedding: Vec<f32> = item?.getattr("embedding")?.extract()?;
                embeddings_vec.push(embedding);
            }

            Ok(embeddings_vec)
        })
    }
}
```

**HuggingFace Embeddings**:
```rust
use pyo3::prelude::*;
use anyhow::Result;

pub struct HuggingFaceEmbedder {
    model: Py<PyAny>,
}

impl HuggingFaceEmbedder {
    pub fn new(model_name: Option<&str>) -> Result<Self> {
        Python::with_gil(|py| {
            let sentence_transformers = PyModule::import(
                py,
                "sentence_transformers"
            )?;

            let model_str = model_name.unwrap_or("all-MiniLM-L6-v2");
            let model = sentence_transformers
                .getattr("SentenceTransformer")?
                .call1(((model_str,),))?;

            Ok(Self {
                model: model.into(),
            })
        })
    }

    pub fn embed(&self, text: &str) -> Result<Vec<f32>> {
        Python::with_gil(|py| {
            let model = self.model.as_ref(py);
            let embedding = model.call_method1("encode", ((text,),))?;
            let embedding_vec: Vec<f32> = embedding.call_method0("tolist")?.extract()?;
            Ok(embedding_vec)
        })
    }

    pub fn embed_batch(&self, texts: Vec<String>) -> Result<Vec<Vec<f32>>> {
        Python::with_gil(|py| {
            let model = self.model.as_ref(py);
            let embeddings = model.call_method1("encode", ((texts,),))?;
            let embeddings_list = embeddings.call_method0("tolist")?;
            let embeddings_vec: Vec<Vec<f32>> = embeddings_list.extract()?;
            Ok(embeddings_vec)
        })
    }
}
```

### Embedding Cache

**Redis-backed embedding cache**:
```rust
use redis::{Commands, Connection};
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::hash::{Hash, Hasher};
use std::collections::hash_map::DefaultHasher;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct CachedEmbedding {
    text: String,
    embedding: Vec<f32>,
    model: String,
    timestamp: i64,
}

pub struct EmbeddingCache {
    redis_conn: Connection,
    embedder: OpenAIEmbedder,
    ttl_seconds: usize,
}

impl EmbeddingCache {
    pub fn new(redis_url: &str, embedder: OpenAIEmbedder, ttl_seconds: usize) -> Result<Self> {
        let client = redis::Client::open(redis_url)?;
        let redis_conn = client.get_connection()?;

        Ok(Self {
            redis_conn,
            embedder,
            ttl_seconds,
        })
    }

    fn cache_key(&self, text: &str, model: &str) -> String {
        let mut hasher = DefaultHasher::new();
        text.hash(&mut hasher);
        model.hash(&mut hasher);
        format!("embedding:{}", hasher.finish())
    }

    pub fn get_or_embed(&mut self, text: &str) -> Result<Vec<f32>> {
        let key = self.cache_key(text, &self.embedder.model);

        // Try cache first
        if let Ok(cached_json) = self.redis_conn.get::<_, String>(&key) {
            if let Ok(cached) = serde_json::from_str::<CachedEmbedding>(&cached_json) {
                return Ok(cached.embedding);
            }
        }

        // Generate embedding
        let embedding = self.embedder.embed(text)?;

        // Cache it
        let cached = CachedEmbedding {
            text: text.to_string(),
            embedding: embedding.clone(),
            model: self.embedder.model.clone(),
            timestamp: chrono::Utc::now().timestamp(),
        };

        let cached_json = serde_json::to_string(&cached)?;
        let _: () = self.redis_conn.set_ex(&key, cached_json, self.ttl_seconds)?;

        Ok(embedding)
    }

    pub fn get_or_embed_batch(&mut self, texts: Vec<String>) -> Result<Vec<Vec<f32>>> {
        let mut results = Vec::new();
        let mut to_embed = Vec::new();
        let mut to_embed_indices = Vec::new();

        // Check cache for each text
        for (i, text) in texts.iter().enumerate() {
            let key = self.cache_key(text, &self.embedder.model);

            if let Ok(cached_json) = self.redis_conn.get::<_, String>(&key) {
                if let Ok(cached) = serde_json::from_str::<CachedEmbedding>(&cached_json) {
                    results.push(Some(cached.embedding));
                    continue;
                }
            }

            results.push(None);
            to_embed.push(text.clone());
            to_embed_indices.push(i);
        }

        // Embed missing texts
        if !to_embed.is_empty() {
            let embeddings = self.embedder.embed_batch(to_embed.clone())?;

            // Cache and insert
            for (idx, embedding) in to_embed_indices.iter().zip(embeddings.iter()) {
                let text = &to_embed[*idx];
                let key = self.cache_key(text, &self.embedder.model);

                let cached = CachedEmbedding {
                    text: text.clone(),
                    embedding: embedding.clone(),
                    model: self.embedder.model.clone(),
                    timestamp: chrono::Utc::now().timestamp(),
                };

                let cached_json = serde_json::to_string(&cached)?;
                let _: () = self.redis_conn.set_ex(&key, cached_json, self.ttl_seconds)?;

                results[*idx] = Some(embedding.clone());
            }
        }

        Ok(results.into_iter().map(|r| r.unwrap()).collect())
    }
}
```

**Best Practice**: Always cache embeddings to reduce API costs and improve response times. Use Redis for distributed caching.

---

## DSPy Retrieval Modules

### Basic DSPy Retrieve

**Wrapping DSPy Retrieve module**:
```rust
use pyo3::prelude::*;
use pyo3::types::PyList;
use anyhow::Result;

pub struct DSpyRetriever {
    retrieve_module: Py<PyAny>,
    k: usize,
}

impl DSpyRetriever {
    pub fn new(k: usize) -> Result<Self> {
        Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;

            let retrieve = dspy.getattr("Retrieve")?.call1(((k,),))?;

            Ok(Self {
                retrieve_module: retrieve.into(),
                k,
            })
        })
    }

    pub fn retrieve(&self, query: &str) -> Result<Vec<String>> {
        Python::with_gil(|py| {
            let retrieve = self.retrieve_module.as_ref(py);

            let result = retrieve.call1(((query,),))?;
            let passages = result.getattr("passages")?;
            let passages_list: Vec<String> = passages.extract()?;

            Ok(passages_list)
        })
    }

    pub fn retrieve_with_scores(&self, query: &str) -> Result<Vec<(String, f32)>> {
        Python::with_gil(|py| {
            let retrieve = self.retrieve_module.as_ref(py);

            let result = retrieve.call1(((query,),))?;

            // Get passages
            let passages = result.getattr("passages")?;
            let passages_list: Vec<String> = passages.extract()?;

            // Get scores if available
            let scores = if let Ok(scores_attr) = result.getattr("scores") {
                scores_attr.extract::<Vec<f32>>()?
            } else {
                // Default scores if not available
                (0..passages_list.len())
                    .map(|i| 1.0 / (i as f32 + 1.0))
                    .collect()
            };

            Ok(passages_list.into_iter().zip(scores.into_iter()).collect())
        })
    }
}
```

### Custom Retriever Function

**Bridge Rust retriever to DSPy**:
```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};
use anyhow::Result;
use std::sync::Arc;

pub fn create_rust_retriever_for_dspy(
    vector_db: Arc<ChromaDBClient>,
    k: usize,
) -> Result<Py<PyAny>> {
    Python::with_gil(|py| {
        // Create Python module with retriever function
        let code = format!(
            r#"
import threading

# Shared state
_vector_db_id = None
_k = {}

def set_vector_db(db_id):
    global _vector_db_id
    _vector_db_id = db_id

def retrieve(query, k=None):
    # This will call back to Rust
    # For now, placeholder implementation
    return []
"#,
            k
        );

        let module = PyModule::from_code(py, &code, "rust_retriever.py", "rust_retriever")?;

        // Store vector_db reference (simplified - production needs proper bridging)
        let retrieve_fn = module.getattr("retrieve")?;

        Ok(retrieve_fn.into())
    })
}

pub fn configure_dspy_with_rust_retriever(
    retriever_fn: Py<PyAny>,
) -> Result<()> {
    Python::with_gil(|py| {
        let dspy = PyModule::import(py, "dspy")?;

        // Create custom RM class
        let code = r#"
import dspy

class RustRetriever(dspy.Retrieve):
    def __init__(self, retrieve_fn, k=3):
        self.retrieve_fn = retrieve_fn
        self.k = k

    def forward(self, query_or_queries, k=None):
        if k is None:
            k = self.k

        # Call Rust retriever
        passages = self.retrieve_fn(query_or_queries, k)

        return dspy.Prediction(passages=passages)
"#;

        let locals = PyDict::new(py);
        locals.set_item("dspy", dspy)?;
        py.run(code, None, Some(locals))?;

        let rust_retriever_class = locals.get_item("RustRetriever")?.unwrap();
        let retriever_instance = rust_retriever_class.call1((
            (retriever_fn.as_ref(py), 3),
        ))?;

        // Configure DSPy to use this retriever
        dspy.getattr("settings")?
            .call_method1("configure", ((retriever_instance,),))?;

        Ok(())
    })
}
```

**Best Practice**: Use custom retrievers when you need to integrate with non-standard vector databases or implement custom retrieval logic.

---

## RAG Pipeline Patterns

### Basic RAG Pipeline

**Simple end-to-end RAG**:
```rust
use pyo3::prelude::*;
use anyhow::Result;
use std::sync::Arc;

pub struct BasicRAGPipeline {
    vector_db: Arc<ChromaDBClient>,
    embedder: OpenAIEmbedder,
    qa_module: Py<PyAny>,
    k: usize,
}

impl BasicRAGPipeline {
    pub fn new(collection_name: &str, k: usize) -> Result<Self> {
        let vector_db = Arc::new(ChromaDBClient::new(ChromaDBConfig {
            persist_directory: None,
            collection_name: collection_name.to_string(),
            embedding_function: None,
        })?);

        let embedder = OpenAIEmbedder::new(None)?;

        let qa_module = Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;

            let code = r#"
import dspy

class BasicRAG(dspy.Module):
    def __init__(self, k=3):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=k)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = self.retrieve(question).passages
        prediction = self.generate(context=context, question=question)
        return prediction
"#;

            let module = PyModule::from_code(py, code, "basic_rag.py", "basic_rag")?;
            let rag_class = module.getattr("BasicRAG")?;
            let rag_instance = rag_class.call1(((k,),))?;

            Ok::<_, PyErr>(rag_instance.into())
        })?;

        Ok(Self {
            vector_db,
            embedder,
            qa_module,
            k,
        })
    }

    pub fn add_documents(&self, documents: Vec<Document>) -> Result<()> {
        self.vector_db.add_documents(documents)
    }

    pub fn query(&self, question: &str) -> Result<String> {
        Python::with_gil(|py| {
            let qa = self.qa_module.as_ref(py);

            let prediction = qa.call_method1("forward", ((question,),))?;
            let answer: String = prediction.getattr("answer")?.extract()?;

            Ok(answer)
        })
    }

    pub fn query_with_context(&self, question: &str) -> Result<(String, Vec<String>)> {
        // Retrieve context
        let docs = self.vector_db.query(question, self.k)?;
        let context: Vec<String> = docs.iter().map(|d| d.text.clone()).collect();

        // Generate answer
        let answer = Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;
            let generate = dspy
                .getattr("ChainOfThought")?
                .call1((("context, question -> answer",),))?;

            let context_str = context.join("\n\n");

            let kwargs = PyDict::new(py);
            kwargs.set_item("context", context_str)?;
            kwargs.set_item("question", question)?;

            let prediction = generate.call_method("__call__", (), Some(kwargs))?;
            let answer: String = prediction.getattr("answer")?.extract()?;

            Ok::<_, anyhow::Error>(answer)
        })?;

        Ok((answer, context))
    }
}
```

### Multi-Hop RAG

**RAG with iterative retrieval**:
```rust
use pyo3::prelude::*;
use anyhow::Result;

pub struct MultiHopRAG {
    vector_db: Arc<ChromaDBClient>,
    qa_module: Py<PyAny>,
    max_hops: usize,
    k_per_hop: usize,
}

impl MultiHopRAG {
    pub fn new(collection_name: &str, max_hops: usize, k_per_hop: usize) -> Result<Self> {
        let vector_db = Arc::new(ChromaDBClient::new(ChromaDBConfig {
            persist_directory: None,
            collection_name: collection_name.to_string(),
            embedding_function: None,
        })?);

        let qa_module = Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;

            let code = r#"
import dspy

class MultiHopRAG(dspy.Module):
    def __init__(self, max_hops=2, k=3):
        super().__init__()
        self.max_hops = max_hops
        self.retrieve = dspy.Retrieve(k=k)
        self.generate_query = dspy.ChainOfThought("context, question -> search_query")
        self.generate_answer = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = []
        current_query = question

        for hop in range(self.max_hops):
            # Retrieve for current query
            passages = self.retrieve(current_query).passages
            context.extend(passages)

            # Generate next search query
            if hop < self.max_hops - 1:
                context_str = "\n\n".join(context)
                next_query = self.generate_query(
                    context=context_str,
                    question=question
                )
                current_query = next_query.search_query

        # Final answer generation
        context_str = "\n\n".join(context)
        prediction = self.generate_answer(context=context_str, question=question)

        return prediction
"#;

            let module = PyModule::from_code(py, code, "multihop_rag.py", "multihop_rag")?;
            let class = module.getattr("MultiHopRAG")?;
            let instance = class.call1(((max_hops, k_per_hop),))?;

            Ok::<_, PyErr>(instance.into())
        })?;

        Ok(Self {
            vector_db,
            qa_module,
            max_hops,
            k_per_hop,
        })
    }

    pub fn query(&self, question: &str) -> Result<String> {
        Python::with_gil(|py| {
            let qa = self.qa_module.as_ref(py);

            let prediction = qa.call_method1("forward", ((question,),))?;
            let answer: String = prediction.getattr("answer")?.extract()?;

            Ok(answer)
        })
    }
}
```

**Best Practice**: Use multi-hop RAG for complex questions requiring information synthesis from multiple sources.

---

## Hybrid Search Implementation

### Combining Vector and Keyword Search

**Complete hybrid search system**:
```rust
use std::collections::HashMap;
use anyhow::Result;

pub struct HybridSearchRetriever {
    vector_db: Arc<ChromaDBClient>,
    keyword_index: HashMap<String, Vec<String>>,
    alpha: f32, // Weight for vector search (1-alpha for keyword)
}

impl HybridSearchRetriever {
    pub fn new(collection_name: &str, alpha: f32) -> Result<Self> {
        let vector_db = Arc::new(ChromaDBClient::new(ChromaDBConfig {
            persist_directory: None,
            collection_name: collection_name.to_string(),
            embedding_function: None,
        })?);

        Ok(Self {
            vector_db,
            keyword_index: HashMap::new(),
            alpha: alpha.clamp(0.0, 1.0),
        })
    }

    /// Build inverted index for keyword search
    pub fn build_keyword_index(&mut self, documents: &[Document]) {
        self.keyword_index.clear();

        for doc in documents {
            // Tokenize and normalize
            let tokens: Vec<String> = doc.text
                .to_lowercase()
                .split_whitespace()
                .filter(|s| s.len() > 2) // Filter short tokens
                .map(|s| s.trim_matches(|c: char| !c.is_alphanumeric()))
                .filter(|s| !s.is_empty())
                .map(|s| s.to_string())
                .collect();

            for token in tokens {
                self.keyword_index
                    .entry(token)
                    .or_insert_with(Vec::new)
                    .push(doc.id.clone());
            }
        }
    }

    /// Perform BM25-style keyword search
    fn keyword_search(&self, query: &str) -> HashMap<String, f32> {
        let query_tokens: Vec<String> = query
            .to_lowercase()
            .split_whitespace()
            .map(|s| s.to_string())
            .collect();

        let mut scores: HashMap<String, f32> = HashMap::new();

        for token in query_tokens {
            if let Some(doc_ids) = self.keyword_index.get(&token) {
                let idf = (self.keyword_index.len() as f32 / doc_ids.len() as f32).ln();

                for doc_id in doc_ids {
                    *scores.entry(doc_id.clone()).or_insert(0.0) += idf;
                }
            }
        }

        scores
    }

    /// Hybrid search combining vector and keyword
    pub fn search(&self, query: &str, k: usize) -> Result<Vec<Document>> {
        // Vector search
        let vector_results = self.vector_db.query(query, k * 2)?;

        // Keyword search
        let keyword_scores = self.keyword_search(query);

        // Normalize vector scores (reciprocal rank)
        let mut combined_scores: HashMap<String, f32> = HashMap::new();

        for (rank, doc) in vector_results.iter().enumerate() {
            let vector_score = 1.0 / (rank as f32 + 1.0);
            combined_scores.insert(doc.id.clone(), self.alpha * vector_score);
        }

        // Add keyword scores
        for (doc_id, keyword_score) in keyword_scores {
            *combined_scores.entry(doc_id).or_insert(0.0) +=
                (1.0 - self.alpha) * keyword_score;
        }

        // Sort by combined score
        let mut doc_map: HashMap<String, Document> = vector_results
            .into_iter()
            .map(|d| (d.id.clone(), d))
            .collect();

        let mut scored_docs: Vec<(String, f32)> = combined_scores
            .into_iter()
            .collect();

        scored_docs.sort_by(|a, b| {
            b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
        });

        // Return top K
        Ok(scored_docs
            .into_iter()
            .take(k)
            .filter_map(|(id, _)| doc_map.remove(&id))
            .collect())
    }
}
```

**Best Practice**: Use hybrid search for domains where exact keyword matches are important (e.g., legal, medical).

---

## Reranking Strategies

### Cross-Encoder Reranking

**Complete reranking implementation**:
```rust
use pyo3::prelude::*;
use pyo3::types::PyList;
use anyhow::Result;
use std::sync::Arc;

pub struct CrossEncoderReranker {
    model: Py<PyAny>,
}

impl CrossEncoderReranker {
    pub fn new(model_name: Option<&str>) -> Result<Self> {
        Python::with_gil(|py| {
            let sentence_transformers = PyModule::import(py, "sentence_transformers")?;

            let model_str = model_name.unwrap_or("cross-encoder/ms-marco-MiniLM-L-6-v2");
            let model = sentence_transformers
                .getattr("CrossEncoder")?
                .call1(((model_str,),))?;

            Ok(Self {
                model: model.into(),
            })
        })
    }

    pub fn rerank(
        &self,
        query: &str,
        documents: Vec<Document>,
        top_k: usize,
    ) -> Result<Vec<(Document, f32)>> {
        Python::with_gil(|py| {
            let model = self.model.as_ref(py);

            // Create query-document pairs
            let pairs: Vec<(String, String)> = documents
                .iter()
                .map(|doc| (query.to_string(), doc.text.clone()))
                .collect();

            let py_pairs = PyList::new(py, &pairs);

            // Get scores
            let scores_obj = model.call_method1("predict", ((py_pairs,),))?;
            let scores: Vec<f32> = scores_obj.extract()?;

            // Combine and sort
            let mut scored: Vec<(Document, f32)> = documents
                .into_iter()
                .zip(scores.into_iter())
                .collect();

            scored.sort_by(|a, b| {
                b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
            });

            Ok(scored.into_iter().take(top_k).collect())
        })
    }

    pub fn rerank_batch(
        &self,
        queries: Vec<String>,
        documents_per_query: Vec<Vec<Document>>,
        top_k: usize,
    ) -> Result<Vec<Vec<(Document, f32)>>> {
        let mut results = Vec::new();

        for (query, docs) in queries.iter().zip(documents_per_query.into_iter()) {
            let reranked = self.rerank(query, docs, top_k)?;
            results.push(reranked);
        }

        Ok(results)
    }
}

/// Two-stage retrieval with reranking
pub struct TwoStageRAG {
    vector_db: Arc<ChromaDBClient>,
    reranker: CrossEncoderReranker,
    qa_module: Py<PyAny>,
    initial_k: usize,
    final_k: usize,
}

impl TwoStageRAG {
    pub fn new(
        collection_name: &str,
        initial_k: usize,
        final_k: usize,
    ) -> Result<Self> {
        let vector_db = Arc::new(ChromaDBClient::new(ChromaDBConfig {
            persist_directory: None,
            collection_name: collection_name.to_string(),
            embedding_function: None,
        })?);

        let reranker = CrossEncoderReranker::new(None)?;

        let qa_module = Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;
            let cot = dspy
                .getattr("ChainOfThought")?
                .call1((("context, question -> answer",),))?;
            Ok::<_, PyErr>(cot.into())
        })?;

        Ok(Self {
            vector_db,
            reranker,
            qa_module,
            initial_k,
            final_k,
        })
    }

    pub fn query(&self, question: &str) -> Result<(String, Vec<Document>)> {
        // Stage 1: Fast retrieval (over-retrieve)
        let candidates = self.vector_db.query(question, self.initial_k)?;

        // Stage 2: Rerank with cross-encoder
        let reranked = self.reranker.rerank(question, candidates, self.final_k)?;

        // Extract documents and context
        let docs: Vec<Document> = reranked.iter()
            .map(|(doc, _)| doc.clone())
            .collect();

        let context = docs.iter()
            .map(|d| d.text.clone())
            .collect::<Vec<_>>()
            .join("\n\n");

        // Stage 3: Generate answer
        let answer = Python::with_gil(|py| {
            let qa = self.qa_module.as_ref(py);

            let kwargs = PyDict::new(py);
            kwargs.set_item("context", &context)?;
            kwargs.set_item("question", question)?;

            let prediction = qa.call_method("__call__", (), Some(kwargs))?;
            let answer: String = prediction.getattr("answer")?.extract()?;

            Ok::<_, anyhow::Error>(answer)
        })?;

        Ok((answer, docs))
    }
}
```

**Best Practice**: Always use reranking in production RAG systems. The performance improvement typically justifies the latency cost.

---

## Context Window Management

### Token Counting and Context Building

**Complete context window manager**:
```rust
use pyo3::prelude::*;
use pyo3::types::PySlice;
use anyhow::Result;

pub struct ContextWindowManager {
    max_tokens: usize,
    token_counter: Py<PyAny>,
    model_name: String,
}

impl ContextWindowManager {
    pub fn new(max_tokens: usize, model_name: Option<&str>) -> Result<Self> {
        let model_str = model_name.unwrap_or("gpt-3.5-turbo").to_string();

        let token_counter = Python::with_gil(|py| {
            let tiktoken = PyModule::import(py, "tiktoken")?;
            let encoding = tiktoken.call_method1(
                "encoding_for_model",
                ((model_str.as_str(),),)
            )?;
            Ok::<_, PyErr>(encoding.into())
        })?;

        Ok(Self {
            max_tokens,
            token_counter,
            model_name: model_str,
        })
    }

    pub fn count_tokens(&self, text: &str) -> Result<usize> {
        Python::with_gil(|py| {
            let encoding = self.token_counter.as_ref(py);
            let tokens = encoding.call_method1("encode", ((text,),))?;
            let count: usize = tokens.len()?;
            Ok(count)
        })
    }

    pub fn truncate_to_tokens(&self, text: &str, max_tokens: usize) -> Result<String> {
        Python::with_gil(|py| {
            let encoding = self.token_counter.as_ref(py);
            let tokens = encoding.call_method1("encode", ((text,),))?;

            // Slice tokens
            let slice = PySlice::new(py, 0, max_tokens as isize, 1);
            let truncated_tokens = tokens.call_method1("__getitem__", ((slice,),))?;

            // Decode
            let truncated_text: String = encoding
                .call_method1("decode", ((truncated_tokens,),))?
                .extract()?;

            Ok(truncated_text)
        })
    }

    pub fn build_context(
        &self,
        documents: Vec<Document>,
        query: &str,
        reserve_for_output: usize,
    ) -> Result<(String, Vec<usize>)> {
        let query_tokens = self.count_tokens(query)?;
        let available = self.max_tokens
            .saturating_sub(query_tokens)
            .saturating_sub(reserve_for_output);

        let mut context_parts = Vec::new();
        let mut included_indices = Vec::new();
        let mut used_tokens = 0;

        for (i, doc) in documents.iter().enumerate() {
            let doc_tokens = self.count_tokens(&doc.text)?;

            if used_tokens + doc_tokens <= available {
                // Document fits entirely
                context_parts.push(doc.text.clone());
                included_indices.push(i);
                used_tokens += doc_tokens;
            } else if available - used_tokens > 100 {
                // Truncate document to fit
                let remaining = available - used_tokens;
                let truncated = self.truncate_to_tokens(&doc.text, remaining)?;
                context_parts.push(truncated);
                included_indices.push(i);
                break;
            } else {
                // No more space
                break;
            }
        }

        Ok((context_parts.join("\n\n"), included_indices))
    }

    pub fn smart_truncate_preserving_structure(
        &self,
        text: &str,
        max_tokens: usize,
    ) -> Result<String> {
        let total_tokens = self.count_tokens(text)?;

        if total_tokens <= max_tokens {
            return Ok(text.to_string());
        }

        // Try to preserve paragraph boundaries
        let paragraphs: Vec<&str> = text.split("\n\n").collect();
        let mut result_paras = Vec::new();
        let mut used_tokens = 0;

        for para in paragraphs {
            let para_tokens = self.count_tokens(para)?;

            if used_tokens + para_tokens <= max_tokens {
                result_paras.push(para);
                used_tokens += para_tokens;
            } else if used_tokens < max_tokens && max_tokens - used_tokens > 50 {
                // Truncate last paragraph
                let remaining = max_tokens - used_tokens;
                let truncated = self.truncate_to_tokens(para, remaining)?;
                result_paras.push(&truncated);
                break;
            } else {
                break;
            }
        }

        Ok(result_paras.join("\n\n"))
    }
}
```

**Best Practice**: Always reserve tokens for the output. A good rule of thumb is to reserve 25-30% of the context window for generation.

---

## Document Chunking

### Intelligent Chunking Strategies

**Token-based chunking with overlap**:
```rust
use pyo3::prelude::*;
use anyhow::Result;

pub struct DocumentChunker {
    chunk_size: usize,
    overlap: usize,
    token_counter: Py<PyAny>,
}

impl DocumentChunker {
    pub fn new(chunk_size: usize, overlap: usize, model: Option<&str>) -> Result<Self> {
        let model_str = model.unwrap_or("gpt-3.5-turbo");

        let token_counter = Python::with_gil(|py| {
            let tiktoken = PyModule::import(py, "tiktoken")?;
            let encoding = tiktoken.call_method1(
                "encoding_for_model",
                ((model_str,),)
            )?;
            Ok::<_, PyErr>(encoding.into())
        })?;

        Ok(Self {
            chunk_size,
            overlap,
            token_counter,
        })
    }

    pub fn chunk_document(&self, doc: &Document) -> Result<Vec<Document>> {
        Python::with_gil(|py| {
            let encoding = self.token_counter.as_ref(py);

            // Encode to tokens
            let tokens = encoding.call_method1("encode", ((&doc.text,),))?;
            let token_list: Vec<i32> = tokens.extract()?;

            if token_list.len() <= self.chunk_size {
                // No need to chunk
                return Ok(vec![doc.clone()]);
            }

            let mut chunks = Vec::new();
            let mut start = 0;
            let mut chunk_idx = 0;

            while start < token_list.len() {
                let end = (start + self.chunk_size).min(token_list.len());
                let chunk_tokens = &token_list[start..end];

                // Decode chunk
                let chunk_py = PyList::new(py, chunk_tokens);
                let chunk_text: String = encoding
                    .call_method1("decode", ((chunk_py,),))?
                    .extract()?;

                // Create chunk document
                let chunk_doc = Document {
                    id: format!("{}-chunk-{}", doc.id, chunk_idx),
                    text: chunk_text,
                    metadata: Some(serde_json::json!({
                        "parent_id": doc.id,
                        "chunk_index": chunk_idx,
                        "start_token": start,
                        "end_token": end,
                        "original_metadata": doc.metadata,
                    })),
                };

                chunks.push(chunk_doc);

                // Move with overlap
                start += self.chunk_size - self.overlap;
                chunk_idx += 1;

                if end >= token_list.len() {
                    break;
                }
            }

            Ok(chunks)
        })
    }

    pub fn chunk_batch(&self, documents: Vec<Document>) -> Result<Vec<Document>> {
        let mut all_chunks = Vec::new();

        for doc in documents {
            let chunks = self.chunk_document(&doc)?;
            all_chunks.extend(chunks);
        }

        Ok(all_chunks)
    }
}

/// Semantic chunking based on sentence boundaries
pub struct SemanticChunker {
    max_chunk_size: usize,
    min_chunk_size: usize,
    token_counter: Py<PyAny>,
}

impl SemanticChunker {
    pub fn new(
        max_chunk_size: usize,
        min_chunk_size: usize,
        model: Option<&str>,
    ) -> Result<Self> {
        let model_str = model.unwrap_or("gpt-3.5-turbo");

        let token_counter = Python::with_gil(|py| {
            let tiktoken = PyModule::import(py, "tiktoken")?;
            let encoding = tiktoken.call_method1(
                "encoding_for_model",
                ((model_str,),)
            )?;
            Ok::<_, PyErr>(encoding.into())
        })?;

        Ok(Self {
            max_chunk_size,
            min_chunk_size,
            token_counter,
        })
    }

    fn count_tokens(&self, text: &str) -> Result<usize> {
        Python::with_gil(|py| {
            let encoding = self.token_counter.as_ref(py);
            let tokens = encoding.call_method1("encode", ((text,),))?;
            Ok(tokens.len()?)
        })
    }

    pub fn chunk_document(&self, doc: &Document) -> Result<Vec<Document>> {
        // Split into sentences (simplified - use proper sentence splitter)
        let sentences: Vec<&str> = doc.text
            .split(|c| c == '.' || c == '!' || c == '?')
            .filter(|s| !s.trim().is_empty())
            .collect();

        let mut chunks = Vec::new();
        let mut current_chunk = String::new();
        let mut chunk_idx = 0;

        for sentence in sentences {
            let sentence = sentence.trim();
            let test_chunk = if current_chunk.is_empty() {
                sentence.to_string()
            } else {
                format!("{}. {}", current_chunk, sentence)
            };

            let token_count = self.count_tokens(&test_chunk)?;

            if token_count > self.max_chunk_size {
                // Save current chunk if it meets minimum
                if self.count_tokens(&current_chunk)? >= self.min_chunk_size {
                    chunks.push(Document {
                        id: format!("{}-chunk-{}", doc.id, chunk_idx),
                        text: current_chunk.clone(),
                        metadata: Some(serde_json::json!({
                            "parent_id": doc.id,
                            "chunk_index": chunk_idx,
                        })),
                    });
                    chunk_idx += 1;
                }

                // Start new chunk
                current_chunk = sentence.to_string();
            } else {
                current_chunk = test_chunk;
            }
        }

        // Add final chunk
        if !current_chunk.is_empty() {
            chunks.push(Document {
                id: format!("{}-chunk-{}", doc.id, chunk_idx),
                text: current_chunk,
                metadata: Some(serde_json::json!({
                    "parent_id": doc.id,
                    "chunk_index": chunk_idx,
                })),
            });
        }

        Ok(chunks)
    }
}
```

**Best Practice**: Use semantic chunking for narrative text, fixed-size chunking for code or structured data.

---

## Production RAG Systems

### Complete Production Pipeline

**Production-ready RAG system with all optimizations**:
```rust
use tokio::sync::RwLock;
use std::sync::Arc;
use anyhow::Result;

#[derive(Debug, Clone)]
pub struct RAGConfig {
    pub collection_name: String,
    pub initial_k: usize,
    pub final_k: usize,
    pub max_context_tokens: usize,
    pub use_reranking: bool,
    pub use_hybrid_search: bool,
    pub hybrid_alpha: f32,
    pub chunk_size: usize,
    pub chunk_overlap: usize,
}

impl Default for RAGConfig {
    fn default() -> Self {
        Self {
            collection_name: "documents".to_string(),
            initial_k: 20,
            final_k: 5,
            max_context_tokens: 4000,
            use_reranking: true,
            use_hybrid_search: false,
            hybrid_alpha: 0.7,
            chunk_size: 512,
            chunk_overlap: 50,
        }
    }
}

pub struct ProductionRAGSystem {
    vector_db: Arc<ChromaDBClient>,
    context_manager: Arc<ContextWindowManager>,
    reranker: Option<Arc<CrossEncoderReranker>>,
    hybrid_retriever: Option<Arc<RwLock<HybridSearchRetriever>>>,
    qa_module: Arc<RwLock<Py<PyAny>>>,
    chunker: Arc<DocumentChunker>,
    config: RAGConfig,
}

impl ProductionRAGSystem {
    pub async fn new(config: RAGConfig) -> Result<Self> {
        let vector_db = Arc::new(ChromaDBClient::new(ChromaDBConfig {
            persist_directory: Some("./chroma_db".to_string()),
            collection_name: config.collection_name.clone(),
            embedding_function: None,
        })?);

        let context_manager = Arc::new(ContextWindowManager::new(
            config.max_context_tokens,
            Some("gpt-3.5-turbo"),
        )?);

        let reranker = if config.use_reranking {
            Some(Arc::new(CrossEncoderReranker::new(None)?))
        } else {
            None
        };

        let hybrid_retriever = if config.use_hybrid_search {
            let retriever = HybridSearchRetriever::new(
                &config.collection_name,
                config.hybrid_alpha,
            )?;
            Some(Arc::new(RwLock::new(retriever)))
        } else {
            None
        };

        let qa_module = Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;
            let cot = dspy
                .getattr("ChainOfThought")?
                .call1((("context, question -> answer",),))?;
            Ok::<_, PyErr>(Arc::new(RwLock::new(cot.into())))
        })?;

        let chunker = Arc::new(DocumentChunker::new(
            config.chunk_size,
            config.chunk_overlap,
            Some("gpt-3.5-turbo"),
        )?);

        Ok(Self {
            vector_db,
            context_manager,
            reranker,
            hybrid_retriever,
            qa_module,
            chunker,
            config,
        })
    }

    /// Ingest documents with chunking
    pub async fn ingest_documents(&self, documents: Vec<Document>) -> Result<()> {
        // Chunk documents
        let chunks = self.chunker.chunk_batch(documents)?;

        // Add to vector DB
        self.vector_db.add_documents(chunks.clone())?;

        // Build keyword index if using hybrid search
        if let Some(hybrid) = &self.hybrid_retriever {
            let mut hybrid_lock = hybrid.write().await;
            hybrid_lock.build_keyword_index(&chunks);
        }

        Ok(())
    }

    /// Query with full pipeline
    pub async fn query(&self, question: &str) -> Result<RAGResponse> {
        // Step 1: Retrieve candidates
        let candidates = if let Some(hybrid) = &self.hybrid_retriever {
            let hybrid_lock = hybrid.read().await;
            hybrid_lock.search(question, self.config.initial_k)?
        } else {
            self.vector_db.query(question, self.config.initial_k)?
        };

        // Step 2: Rerank if enabled
        let final_docs = if self.config.use_reranking {
            if let Some(reranker) = &self.reranker {
                let reranked = reranker.rerank(
                    question,
                    candidates,
                    self.config.final_k,
                )?;
                reranked.into_iter().map(|(doc, _)| doc).collect()
            } else {
                candidates.into_iter().take(self.config.final_k).collect()
            }
        } else {
            candidates.into_iter().take(self.config.final_k).collect()
        };

        // Step 3: Build context
        let (context, included_indices) = self.context_manager.build_context(
            final_docs.clone(),
            question,
            1000, // Reserve for output
        )?;

        // Step 4: Generate answer
        let answer = self.generate_answer(question, &context).await?;

        // Build response
        let context_docs = included_indices
            .into_iter()
            .map(|i| final_docs[i].clone())
            .collect();

        Ok(RAGResponse {
            answer,
            context_docs,
            context_text: context,
        })
    }

    async fn generate_answer(&self, question: &str, context: &str) -> Result<String> {
        let qa_lock = self.qa_module.read().await;

        let answer = Python::with_gil(|py| {
            let qa = qa_lock.as_ref(py);

            let kwargs = PyDict::new(py);
            kwargs.set_item("context", context)?;
            kwargs.set_item("question", question)?;

            let prediction = qa.call_method("__call__", (), Some(kwargs))?;
            let answer: String = prediction.getattr("answer")?.extract()?;

            Ok::<_, anyhow::Error>(answer)
        })?;

        Ok(answer)
    }

    /// Get system statistics
    pub fn stats(&self) -> Result<RAGStats> {
        let doc_count = self.vector_db.count()?;

        Ok(RAGStats {
            document_count: doc_count,
            collection_name: self.config.collection_name.clone(),
            reranking_enabled: self.config.use_reranking,
            hybrid_search_enabled: self.config.use_hybrid_search,
        })
    }
}

#[derive(Debug, Clone)]
pub struct RAGResponse {
    pub answer: String,
    pub context_docs: Vec<Document>,
    pub context_text: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RAGStats {
    pub document_count: usize,
    pub collection_name: String,
    pub reranking_enabled: bool,
    pub hybrid_search_enabled: bool,
}
```

**Best Practice**: Always use production-ready architecture with proper error handling, monitoring, and configurability.

---

## Performance Optimization

### Batching and Caching

**Optimized batch retrieval**:
```rust
use tokio::task;
use futures::future::join_all;
use std::time::Instant;

pub struct OptimizedRAG {
    system: Arc<ProductionRAGSystem>,
}

impl OptimizedRAG {
    pub fn new(system: ProductionRAGSystem) -> Self {
        Self {
            system: Arc::new(system),
        }
    }

    /// Process multiple queries in parallel
    pub async fn batch_query(&self, questions: Vec<String>) -> Result<Vec<RAGResponse>> {
        let start = Instant::now();

        let mut handles = Vec::new();

        for question in questions {
            let system = Arc::clone(&self.system);
            let handle = task::spawn(async move {
                system.query(&question).await
            });
            handles.push(handle);
        }

        let results: Vec<Result<RAGResponse>> = join_all(handles)
            .await
            .into_iter()
            .map(|r| r?)
            .collect();

        let duration = start.elapsed();
        println!("Batch processed {} queries in {:?}", results.len(), duration);

        results.into_iter().collect()
    }

    /// Streaming responses for large result sets
    pub async fn stream_query(
        &self,
        question: &str,
    ) -> Result<tokio::sync::mpsc::Receiver<String>> {
        let (tx, rx) = tokio::sync::mpsc::channel(100);
        let system = Arc::clone(&self.system);
        let question = question.to_string();

        task::spawn(async move {
            if let Ok(response) = system.query(&question).await {
                // Stream answer in chunks
                let words: Vec<&str> = response.answer.split_whitespace().collect();
                for word in words {
                    if tx.send(word.to_string()).await.is_err() {
                        break;
                    }
                    tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
                }
            }
        });

        Ok(rx)
    }
}
```

### Benchmarking

**Complete benchmarking suite**:
```rust
use std::time::{Duration, Instant};

#[derive(Debug, Clone)]
pub struct BenchmarkResults {
    pub total_queries: usize,
    pub total_duration: Duration,
    pub avg_latency: Duration,
    pub p50_latency: Duration,
    pub p95_latency: Duration,
    pub p99_latency: Duration,
    pub throughput: f64, // queries per second
}

pub async fn benchmark_rag(
    system: &ProductionRAGSystem,
    queries: Vec<String>,
) -> Result<BenchmarkResults> {
    let mut latencies = Vec::new();
    let start = Instant::now();

    for query in &queries {
        let query_start = Instant::now();
        let _ = system.query(query).await?;
        let query_duration = query_start.elapsed();
        latencies.push(query_duration);
    }

    let total_duration = start.elapsed();

    // Sort for percentiles
    latencies.sort();

    let p50_idx = latencies.len() / 2;
    let p95_idx = (latencies.len() as f64 * 0.95) as usize;
    let p99_idx = (latencies.len() as f64 * 0.99) as usize;

    let avg_latency = Duration::from_nanos(
        (latencies.iter().map(|d| d.as_nanos()).sum::<u128>() / latencies.len() as u128) as u64
    );

    let throughput = queries.len() as f64 / total_duration.as_secs_f64();

    Ok(BenchmarkResults {
        total_queries: queries.len(),
        total_duration,
        avg_latency,
        p50_latency: latencies[p50_idx],
        p95_latency: latencies[p95_idx],
        p99_latency: latencies[p99_idx],
        throughput,
    })
}
```

**Best Practice**: Always benchmark your RAG system with realistic queries and loads before production deployment.

---

## Best Practices Summary

### Configuration
- ✅ Use persistent storage for vector databases
- ✅ Configure appropriate chunk sizes for your domain
- ✅ Set reasonable K values (initial_k=20, final_k=5)
- ✅ Reserve 25-30% of context window for generation

### Retrieval
- ✅ Always use reranking in production
- ✅ Consider hybrid search for keyword-sensitive domains
- ✅ Over-retrieve then rerank (retrieve 20, rerank to 5)
- ✅ Cache embeddings to reduce API costs

### Performance
- ✅ Use async/await for concurrent operations
- ✅ Batch document ingestion
- ✅ Monitor and optimize retrieval latency
- ✅ Profile GIL acquisition overhead

### Error Handling
- ✅ Implement graceful degradation
- ✅ Log all retrieval failures
- ✅ Provide fallback responses
- ✅ Monitor API rate limits

### Testing
- ✅ Benchmark with realistic queries
- ✅ Test with various document sizes
- ✅ Validate chunking strategies
- ✅ Measure end-to-end latency

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
