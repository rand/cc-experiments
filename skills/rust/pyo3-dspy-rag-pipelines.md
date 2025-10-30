---
skill_id: rust-pyo3-dspy-rag-pipelines
title: PyO3 DSPy RAG Pipelines
category: rust
subcategory: pyo3-dspy
complexity: advanced
prerequisites:
  - rust-pyo3-dspy-fundamentals
  - rust-pyo3-dspy-type-system
  - ml-dspy-rag
  - ml-dspy-retrieval
tags:
  - rust
  - python
  - pyo3
  - dspy
  - rag
  - retrieval
  - vector-db
  - chromadb
  - qdrant
  - embeddings
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Build RAG pipelines with DSPy from Rust
  - Integrate vector databases (ChromaDB, Qdrant, Pinecone)
  - Implement retrieval modules with type safety
  - Manage context windows and chunking strategies
  - Apply hybrid search patterns
  - Implement cross-encoder reranking
  - Design production RAG architectures
  - Optimize retrieval performance
related_skills:
  - rust-pyo3-dspy-fundamentals
  - rust-pyo3-dspy-type-system
  - ml-dspy-rag
  - database-postgres
resources:
  - REFERENCE.md (900+ lines): Complete RAG reference
  - 4 Python scripts (1,200+ lines): Vector DB, retrieval, reranking tools
  - 8 examples (1,500+ lines): Production RAG patterns
---

# PyO3 DSPy RAG Pipelines

## Overview

Master building Retrieval-Augmented Generation (RAG) pipelines with DSPy from Rust. Learn to integrate vector databases, implement retrieval modules, manage context windows, apply hybrid search patterns, and design production-ready RAG systems that combine Rust's performance with DSPy's intelligent retrieval abstractions.

RAG systems enhance LLM outputs by retrieving relevant context from knowledge bases. This skill teaches you to build high-performance, type-safe RAG pipelines that leverage Rust's speed for data processing and DSPy's powerful retrieval abstractions for intelligent context selection.

## Prerequisites

**Required**:
- PyO3 DSPy fundamentals (module calling, error handling)
- PyO3 DSPy type system (signature mapping, prediction handling)
- DSPy RAG basics (Retrieve module, context patterns)
- Vector database concepts (embeddings, similarity search)

**Recommended**:
- Experience with ChromaDB, Qdrant, or Pinecone
- Text chunking and preprocessing strategies
- Embedding models (OpenAI, HuggingFace)
- SQL and database optimization

## When to Use

**Ideal for**:
- **Production RAG systems** requiring high throughput and low latency
- **Enterprise knowledge bases** with millions of documents
- **Real-time Q&A services** over large corpora
- **Hybrid search systems** combining vector and keyword search
- **Multi-stage retrieval pipelines** with reranking
- **RAG-as-a-Service** APIs in Rust microservices

**Not ideal for**:
- Simple in-memory retrieval (overhead not justified)
- Static document collections (pre-compute contexts)
- Prototype RAG experiments (use pure Python DSPy)

## Learning Path

### 1. Vector Database Integration

**ChromaDB from Rust**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    pub id: String,
    pub text: String,
    pub metadata: Option<serde_json::Value>,
}

pub struct ChromaDBClient {
    client: Py<PyAny>,
    collection: Py<PyAny>,
}

impl ChromaDBClient {
    pub fn new(collection_name: &str) -> PyResult<Self> {
        Python::with_gil(|py| {
            // Import ChromaDB
            let chromadb = PyModule::import(py, "chromadb")?;

            // Create client
            let client = chromadb
                .getattr("Client")?
                .call0()?;

            // Get or create collection
            let collection = client
                .call_method1(
                    "get_or_create_collection",
                    ((collection_name,),)
                )?;

            Ok(Self {
                client: client.into(),
                collection: collection.into(),
            })
        })
    }

    pub fn add_documents(&self, documents: Vec<Document>) -> PyResult<()> {
        Python::with_gil(|py| {
            let collection = self.collection.as_ref(py);

            // Prepare data
            let ids: Vec<String> = documents.iter()
                .map(|d| d.id.clone())
                .collect();

            let texts: Vec<String> = documents.iter()
                .map(|d| d.text.clone())
                .collect();

            let metadatas: Vec<Option<serde_json::Value>> = documents.iter()
                .map(|d| d.metadata.clone())
                .collect();

            // Convert to Python lists
            let py_ids = PyList::new(py, &ids);
            let py_texts = PyList::new(py, &texts);

            // Add to collection
            let kwargs = PyDict::new(py);
            kwargs.set_item("ids", py_ids)?;
            kwargs.set_item("documents", py_texts)?;

            if !metadatas.is_empty() {
                let py_metadatas = PyList::new(py, &metadatas);
                kwargs.set_item("metadatas", py_metadatas)?;
            }

            collection.call_method("add", (), Some(kwargs))?;

            Ok(())
        })
    }

    pub fn query(
        &self,
        query_text: &str,
        n_results: usize,
    ) -> PyResult<Vec<Document>> {
        Python::with_gil(|py| {
            let collection = self.collection.as_ref(py);

            let kwargs = PyDict::new(py);
            kwargs.set_item("query_texts", vec![query_text])?;
            kwargs.set_item("n_results", n_results)?;

            let results = collection
                .call_method("query", (), Some(kwargs))?;

            // Extract results
            let ids: Vec<Vec<String>> = results
                .getattr("ids")?
                .extract()?;

            let documents: Vec<Vec<String>> = results
                .getattr("documents")?
                .extract()?;

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
}
```

**Qdrant Integration**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

pub struct QdrantClient {
    client: Py<PyAny>,
}

impl QdrantClient {
    pub fn new(url: &str, collection_name: &str) -> PyResult<Self> {
        Python::with_gil(|py| {
            let qdrant = PyModule::import(py, "qdrant_client")?;

            // Create client
            let client = qdrant
                .getattr("QdrantClient")?
                .call1(((url,),))?;

            // Ensure collection exists
            let collections = client.call_method0("get_collections")?;
            let collection_names: Vec<String> = collections
                .getattr("collections")?
                .extract()?;

            if !collection_names.contains(&collection_name.to_string()) {
                // Create collection
                let models = PyModule::import(py, "qdrant_client.models")?;
                let vector_params = models
                    .getattr("VectorParams")?
                    .call1((
                        (1536, "Cosine"),  // OpenAI embedding dimension
                    ))?;

                client.call_method1(
                    "create_collection",
                    ((collection_name, vector_params),)
                )?;
            }

            Ok(Self {
                client: client.into(),
            })
        })
    }

    pub fn upsert_documents(
        &self,
        collection_name: &str,
        documents: Vec<Document>,
        embeddings: Vec<Vec<f32>>,
    ) -> PyResult<()> {
        Python::with_gil(|py| {
            let client = self.client.as_ref(py);
            let models = PyModule::import(py, "qdrant_client.models")?;

            // Create points
            let points = documents.iter()
                .zip(embeddings.iter())
                .map(|(doc, embedding)| {
                    let point_class = models.getattr("PointStruct")?;

                    let payload = PyDict::new(py);
                    payload.set_item("text", &doc.text)?;
                    if let Some(metadata) = &doc.metadata {
                        payload.set_item("metadata", metadata.to_string())?;
                    }

                    point_class.call1((
                        (&doc.id, embedding.clone(), payload),
                    ))
                })
                .collect::<PyResult<Vec<_>>>()?;

            client.call_method1(
                "upsert",
                ((collection_name, points),)
            )?;

            Ok(())
        })
    }

    pub fn search(
        &self,
        collection_name: &str,
        query_vector: Vec<f32>,
        limit: usize,
    ) -> PyResult<Vec<Document>> {
        Python::with_gil(|py| {
            let client = self.client.as_ref(py);

            let results = client.call_method1(
                "search",
                ((collection_name, query_vector, limit),)
            )?;

            // Extract results
            let mut documents = Vec::new();

            for result in results.iter()? {
                let result = result?;
                let id: String = result.getattr("id")?.extract()?;
                let payload = result.getattr("payload")?;
                let text: String = payload.getattr("text")?.extract()?;

                documents.push(Document {
                    id,
                    text,
                    metadata: None,
                });
            }

            Ok(documents)
        })
    }
}
```

### 2. DSPy Retrieval Modules

**Wrapping DSPy Retrieve**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyList;

pub struct DSpyRetriever {
    retrieve_module: Py<PyAny>,
}

impl DSpyRetriever {
    pub fn new(k: usize) -> PyResult<Self> {
        Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;

            // Create Retrieve module
            let retrieve = dspy
                .getattr("Retrieve")?
                .call1(((k,),))?;

            Ok(Self {
                retrieve_module: retrieve.into(),
            })
        })
    }

    pub fn retrieve(&self, query: &str) -> PyResult<Vec<String>> {
        Python::with_gil(|py| {
            let retrieve = self.retrieve_module.as_ref(py);

            // Call retrieve
            let result = retrieve.call1(((query,),))?;

            // Extract passages
            let passages = result.getattr("passages")?;
            let passages_list: Vec<String> = passages.extract()?;

            Ok(passages_list)
        })
    }
}

// Custom retriever function for DSPy
pub fn create_custom_retriever(
    vector_db: ChromaDBClient,
    k: usize,
) -> PyResult<Py<PyAny>> {
    Python::with_gil(|py| {
        // Define Python function that wraps Rust retriever
        let code = format!(
            r#"
def custom_retrieve(query, k={}):
    # This will be called by DSPy
    # Implement bridge to Rust here
    pass
"#,
            k
        );

        let module = PyModule::from_code(
            py,
            &code,
            "custom_retriever.py",
            "custom_retriever",
        )?;

        let func = module.getattr("custom_retrieve")?;
        Ok(func.into())
    })
}
```

**Configuring DSPy with Custom Retriever**:

```rust
use pyo3::prelude::*;

pub fn configure_dspy_with_retriever(
    collection_name: &str,
    k: usize,
) -> PyResult<()> {
    Python::with_gil(|py| {
        let dspy = PyModule::import(py, "dspy")?;

        // Create ChromaDB retriever
        let chromadb = PyModule::import(py, "chromadb")?;
        let client = chromadb.getattr("Client")?.call0()?;
        let collection = client.call_method1(
            "get_or_create_collection",
            ((collection_name,),)
        )?;

        // Define retriever function
        let retriever_code = format!(
            r#"
def chroma_retriever(query, k={}):
    results = collection.query(
        query_texts=[query],
        n_results=k
    )
    return results['documents'][0]
"#,
            k
        );

        let locals = pyo3::types::PyDict::new(py);
        locals.set_item("collection", collection)?;

        py.run(&retriever_code, None, Some(locals))?;
        let retriever = locals.get_item("chroma_retriever")?.unwrap();

        // Configure DSPy settings
        let rm = dspy
            .getattr("Retrieve")?
            .call1(((k,),))?;

        // Set retriever function
        rm.setattr("retriever_fn", retriever)?;

        dspy.getattr("settings")?
            .call_method1("configure", ((rm,),))?;

        Ok(())
    })
}
```

### 3. RAG Pipeline Architecture

**Basic RAG Pipeline**:

```rust
use pyo3::prelude::*;
use anyhow::Result;

pub struct RAGPipeline {
    vector_db: ChromaDBClient,
    retriever: DSpyRetriever,
    qa_module: Py<PyAny>,
}

impl RAGPipeline {
    pub fn new(collection_name: &str, k: usize) -> Result<Self> {
        let vector_db = ChromaDBClient::new(collection_name)?;
        let retriever = DSpyRetriever::new(k)?;

        let qa_module = Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;

            // Create RAG module
            let code = r#"
import dspy

class RAG(dspy.Module):
    def __init__(self, k=3):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=k)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = self.retrieve(question).passages
        prediction = self.generate(context=context, question=question)
        return prediction
"#;

            let module = PyModule::from_code(
                py,
                code,
                "rag_module.py",
                "rag_module",
            )?;

            let rag_class = module.getattr("RAG")?;
            let rag_instance = rag_class.call1(((k,),))?;

            Ok::<_, PyErr>(rag_instance.into())
        })?;

        Ok(Self {
            vector_db,
            retriever,
            qa_module,
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

    pub fn query_with_context(
        &self,
        question: &str,
    ) -> Result<(String, Vec<String>)> {
        // Retrieve context
        let context = self.retriever.retrieve(question)?;

        // Generate answer with context
        let answer = Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;
            let generate = dspy
                .getattr("ChainOfThought")?
                .call1((("context, question -> answer",),))?;

            let context_str = context.join("\n\n");
            let prediction = generate.call_method(
                "__call__",
                (),
                Some({
                    let kwargs = pyo3::types::PyDict::new(py);
                    kwargs.set_item("context", context_str)?;
                    kwargs.set_item("question", question)?;
                    kwargs
                }),
            )?;

            let answer: String = prediction.getattr("answer")?.extract()?;
            Ok::<_, anyhow::Error>(answer)
        })?;

        Ok((answer, context))
    }
}
```

**Advanced RAG with Reranking**:

```rust
use pyo3::prelude::*;

pub struct RerankingRAGPipeline {
    vector_db: ChromaDBClient,
    reranker: Py<PyAny>,
    qa_module: Py<PyAny>,
    initial_k: usize,
    final_k: usize,
}

impl RerankingRAGPipeline {
    pub fn new(
        collection_name: &str,
        initial_k: usize,
        final_k: usize,
    ) -> PyResult<Self> {
        let vector_db = ChromaDBClient::new(collection_name)?;

        let reranker = Python::with_gil(|py| {
            // Load cross-encoder for reranking
            let sentence_transformers = PyModule::import(
                py,
                "sentence_transformers"
            )?;

            let model = sentence_transformers
                .getattr("CrossEncoder")?
                .call1((
                    ("cross-encoder/ms-marco-MiniLM-L-6-v2",),
                ))?;

            Ok::<_, PyErr>(model.into())
        })?;

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

    pub fn query(&self, question: &str) -> PyResult<String> {
        Python::with_gil(|py| {
            // Step 1: Retrieve initial candidates
            let candidates = self.vector_db.query(question, self.initial_k)?;

            // Step 2: Rerank
            let reranker = self.reranker.as_ref(py);

            let pairs: Vec<(String, String)> = candidates.iter()
                .map(|doc| (question.to_string(), doc.text.clone()))
                .collect();

            let scores = reranker.call_method1("predict", ((pairs,),))?;
            let scores: Vec<f32> = scores.extract()?;

            // Sort by score and take top K
            let mut ranked: Vec<_> = candidates.into_iter()
                .zip(scores.into_iter())
                .collect();

            ranked.sort_by(|a, b| {
                b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
            });

            let top_docs: Vec<String> = ranked.iter()
                .take(self.final_k)
                .map(|(doc, _)| doc.text.clone())
                .collect();

            // Step 3: Generate answer
            let qa = self.qa_module.as_ref(py);
            let context = top_docs.join("\n\n");

            let kwargs = pyo3::types::PyDict::new(py);
            kwargs.set_item("context", context)?;
            kwargs.set_item("question", question)?;

            let prediction = qa.call_method("forward", (), Some(kwargs))?;
            let answer: String = prediction.getattr("answer")?.extract()?;

            Ok(answer)
        })
    }
}
```

### 4. Hybrid Search Patterns

**Combining Vector and Keyword Search**:

```rust
use pyo3::prelude::*;
use std::collections::HashMap;

pub struct HybridSearchRetriever {
    vector_db: ChromaDBClient,
    keyword_index: HashMap<String, Vec<String>>, // Simple keyword index
    alpha: f32, // Weight for vector search (1-alpha for keyword)
}

impl HybridSearchRetriever {
    pub fn new(
        collection_name: &str,
        alpha: f32,
    ) -> PyResult<Self> {
        Ok(Self {
            vector_db: ChromaDBClient::new(collection_name)?,
            keyword_index: HashMap::new(),
            alpha: alpha.clamp(0.0, 1.0),
        })
    }

    pub fn build_keyword_index(&mut self, documents: Vec<Document>) {
        for doc in documents {
            // Simple tokenization
            let tokens: Vec<String> = doc.text
                .split_whitespace()
                .map(|s| s.to_lowercase())
                .collect();

            for token in tokens {
                self.keyword_index
                    .entry(token)
                    .or_insert_with(Vec::new)
                    .push(doc.id.clone());
            }
        }
    }

    pub fn hybrid_search(
        &self,
        query: &str,
        k: usize,
    ) -> PyResult<Vec<Document>> {
        // Vector search
        let vector_results = self.vector_db.query(query, k * 2)?;

        // Keyword search
        let query_tokens: Vec<String> = query
            .split_whitespace()
            .map(|s| s.to_lowercase())
            .collect();

        let mut keyword_scores: HashMap<String, f32> = HashMap::new();
        for token in query_tokens {
            if let Some(doc_ids) = self.keyword_index.get(&token) {
                for doc_id in doc_ids {
                    *keyword_scores.entry(doc_id.clone()).or_insert(0.0) += 1.0;
                }
            }
        }

        // Combine scores
        let mut combined: Vec<(Document, f32)> = vector_results
            .into_iter()
            .enumerate()
            .map(|(idx, doc)| {
                let vector_score = 1.0 / (idx as f32 + 1.0); // Reciprocal rank
                let keyword_score = keyword_scores
                    .get(&doc.id)
                    .copied()
                    .unwrap_or(0.0);

                let combined_score = self.alpha * vector_score
                    + (1.0 - self.alpha) * keyword_score;

                (doc, combined_score)
            })
            .collect();

        // Sort and return top K
        combined.sort_by(|a, b| {
            b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
        });

        Ok(combined.into_iter().take(k).map(|(doc, _)| doc).collect())
    }
}
```

### 5. Context Window Management

**Intelligent Context Building**:

```rust
use pyo3::prelude::*;

pub struct ContextWindowManager {
    max_tokens: usize,
    token_counter: Py<PyAny>,
}

impl ContextWindowManager {
    pub fn new(max_tokens: usize) -> PyResult<Self> {
        let token_counter = Python::with_gil(|py| {
            // Use tiktoken for accurate token counting
            let tiktoken = PyModule::import(py, "tiktoken")?;
            let encoding = tiktoken
                .call_method1("encoding_for_model", (("gpt-3.5-turbo",),))?;

            Ok::<_, PyErr>(encoding.into())
        })?;

        Ok(Self {
            max_tokens,
            token_counter,
        })
    }

    pub fn count_tokens(&self, text: &str) -> PyResult<usize> {
        Python::with_gil(|py| {
            let encoding = self.token_counter.as_ref(py);
            let tokens = encoding.call_method1("encode", ((text,),))?;
            let count: usize = tokens.len()?;
            Ok(count)
        })
    }

    pub fn build_context(
        &self,
        documents: Vec<Document>,
        query: &str,
    ) -> PyResult<String> {
        let query_tokens = self.count_tokens(query)?;
        let mut available_tokens = self.max_tokens.saturating_sub(query_tokens);

        let mut context_parts = Vec::new();

        for doc in documents {
            let doc_tokens = self.count_tokens(&doc.text)?;

            if doc_tokens <= available_tokens {
                // Document fits entirely
                context_parts.push(doc.text);
                available_tokens -= doc_tokens;
            } else if available_tokens > 100 {
                // Truncate document
                let truncated = self.truncate_to_tokens(
                    &doc.text,
                    available_tokens,
                )?;
                context_parts.push(truncated);
                break;
            } else {
                // No more space
                break;
            }
        }

        Ok(context_parts.join("\n\n"))
    }

    fn truncate_to_tokens(
        &self,
        text: &str,
        max_tokens: usize,
    ) -> PyResult<String> {
        Python::with_gil(|py| {
            let encoding = self.token_counter.as_ref(py);
            let tokens = encoding.call_method1("encode", ((text,),))?;

            // Take first N tokens
            let truncated_tokens = tokens
                .call_method1("__getitem__", ((
                    pyo3::types::PySlice::new(py, 0, max_tokens as isize, 1),
                ),))?;

            // Decode back to text
            let truncated_text: String = encoding
                .call_method1("decode", ((truncated_tokens,),))?
                .extract()?;

            Ok(truncated_text)
        })
    }
}
```

**Chunking Strategy**:

```rust
use pyo3::prelude::*;

pub struct DocumentChunker {
    chunk_size: usize,
    overlap: usize,
    token_counter: Py<PyAny>,
}

impl DocumentChunker {
    pub fn new(chunk_size: usize, overlap: usize) -> PyResult<Self> {
        let token_counter = Python::with_gil(|py| {
            let tiktoken = PyModule::import(py, "tiktoken")?;
            let encoding = tiktoken
                .call_method1("encoding_for_model", (("gpt-3.5-turbo",),))?;
            Ok::<_, PyErr>(encoding.into())
        })?;

        Ok(Self {
            chunk_size,
            overlap,
            token_counter,
        })
    }

    pub fn chunk_document(&self, doc: &Document) -> PyResult<Vec<Document>> {
        Python::with_gil(|py| {
            let encoding = self.token_counter.as_ref(py);

            // Encode text to tokens
            let tokens = encoding.call_method1("encode", ((&doc.text,),))?;
            let token_list: Vec<i32> = tokens.extract()?;

            let mut chunks = Vec::new();
            let mut start = 0;
            let mut chunk_idx = 0;

            while start < token_list.len() {
                let end = (start + self.chunk_size).min(token_list.len());
                let chunk_tokens = &token_list[start..end];

                // Decode chunk
                let chunk_py = pyo3::types::PyList::new(py, chunk_tokens);
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
                        "original_metadata": doc.metadata,
                    })),
                };

                chunks.push(chunk_doc);

                // Move to next chunk with overlap
                start += self.chunk_size - self.overlap;
                chunk_idx += 1;

                if end >= token_list.len() {
                    break;
                }
            }

            Ok(chunks)
        })
    }
}
```

### 6. Production RAG System

**Complete Production Pipeline**:

```rust
use pyo3::prelude::*;
use anyhow::Result;
use std::sync::Arc;
use tokio::sync::RwLock;

pub struct ProductionRAGSystem {
    vector_db: Arc<ChromaDBClient>,
    context_manager: Arc<ContextWindowManager>,
    reranker: Option<Arc<RwLock<Py<PyAny>>>>,
    qa_module: Arc<RwLock<Py<PyAny>>>,
    config: RAGConfig,
}

#[derive(Debug, Clone)]
pub struct RAGConfig {
    pub initial_k: usize,
    pub final_k: usize,
    pub max_context_tokens: usize,
    pub use_reranking: bool,
    pub hybrid_alpha: f32,
}

impl ProductionRAGSystem {
    pub fn new(
        collection_name: &str,
        config: RAGConfig,
    ) -> Result<Self> {
        let vector_db = Arc::new(ChromaDBClient::new(collection_name)?);
        let context_manager = Arc::new(
            ContextWindowManager::new(config.max_context_tokens)?
        );

        let reranker = if config.use_reranking {
            let reranker = Python::with_gil(|py| {
                let st = PyModule::import(py, "sentence_transformers")?;
                let model = st
                    .getattr("CrossEncoder")?
                    .call1((("cross-encoder/ms-marco-MiniLM-L-6-v2",),))?;
                Ok::<_, PyErr>(model.into())
            })?;
            Some(Arc::new(RwLock::new(reranker)))
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

        Ok(Self {
            vector_db,
            context_manager,
            reranker,
            qa_module,
            config,
        })
    }

    pub async fn query(&self, question: &str) -> Result<RAGResponse> {
        // Step 1: Retrieve candidates
        let candidates = self.vector_db.query(
            question,
            self.config.initial_k,
        )?;

        // Step 2: Rerank if enabled
        let final_docs = if self.config.use_reranking {
            if let Some(reranker) = &self.reranker {
                self.rerank_documents(question, candidates, reranker).await?
            } else {
                candidates
            }
        } else {
            candidates.into_iter().take(self.config.final_k).collect()
        };

        // Step 3: Build context
        let context = self.context_manager.build_context(
            final_docs.clone(),
            question,
        )?;

        // Step 4: Generate answer
        let answer = self.generate_answer(question, &context).await?;

        Ok(RAGResponse {
            answer,
            context_docs: final_docs,
            context_text: context,
        })
    }

    async fn rerank_documents(
        &self,
        question: &str,
        candidates: Vec<Document>,
        reranker: &Arc<RwLock<Py<PyAny>>>,
    ) -> Result<Vec<Document>> {
        let reranker_lock = reranker.read().await;

        let ranked = Python::with_gil(|py| {
            let reranker = reranker_lock.as_ref(py);

            let pairs: Vec<(String, String)> = candidates.iter()
                .map(|doc| (question.to_string(), doc.text.clone()))
                .collect();

            let scores = reranker.call_method1("predict", ((pairs,),))?;
            let scores: Vec<f32> = scores.extract()?;

            let mut ranked: Vec<_> = candidates.into_iter()
                .zip(scores.into_iter())
                .collect();

            ranked.sort_by(|a, b| {
                b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
            });

            Ok::<_, anyhow::Error>(
                ranked.into_iter()
                    .take(self.config.final_k)
                    .map(|(doc, _)| doc)
                    .collect()
            )
        })?;

        Ok(ranked)
    }

    async fn generate_answer(
        &self,
        question: &str,
        context: &str,
    ) -> Result<String> {
        let qa_lock = self.qa_module.read().await;

        let answer = Python::with_gil(|py| {
            let qa = qa_lock.as_ref(py);

            let kwargs = pyo3::types::PyDict::new(py);
            kwargs.set_item("context", context)?;
            kwargs.set_item("question", question)?;

            let prediction = qa.call_method("forward", (), Some(kwargs))?;
            let answer: String = prediction.getattr("answer")?.extract()?;

            Ok::<_, anyhow::Error>(answer)
        })?;

        Ok(answer)
    }
}

#[derive(Debug, Clone)]
pub struct RAGResponse {
    pub answer: String,
    pub context_docs: Vec<Document>,
    pub context_text: String,
}
```

## Resources

### REFERENCE.md

Comprehensive 900+ line guide covering:
- Complete vector database setup (ChromaDB, Qdrant, Pinecone, Weaviate)
- Embedding generation and management
- DSPy retrieval module patterns
- Context window optimization strategies
- Hybrid search implementations
- Reranking algorithms and models
- Chunking strategies for different document types
- Production RAG architectures
- Performance benchmarking
- Memory management for large corpora
- Distributed retrieval patterns

**Load**: `cat skills/rust/pyo3-dspy-rag-pipelines/resources/REFERENCE.md`

### Scripts

**1. vector_db_manager.py** (~350 lines)
- Manage multiple vector database backends
- Bulk document ingestion
- Index optimization
- Migration between databases

**2. retrieval_evaluator.py** (~300 lines)
- Evaluate retrieval quality
- Measure recall@K, precision@K
- Compare retrieval strategies
- Generate evaluation reports

**3. reranking_benchmark.py** (~250 lines)
- Benchmark reranking models
- Compare cross-encoders
- Measure latency impact
- A/B test reranking strategies

**4. context_optimizer.py** (~300 lines)
- Analyze context window usage
- Optimize chunking parameters
- Test different token limits
- Generate optimization reports

### Examples

**1. basic-rag/** - Simple RAG pipeline
**2. chromadb-integration/** - ChromaDB from Rust
**3. qdrant-integration/** - Qdrant from Rust
**4. hybrid-search/** - Vector + keyword search
**5. reranking-pipeline/** - Cross-encoder reranking
**6. context-management/** - Context window optimization
**7. production-rag/** - Complete production system
**8. benchmarking/** - Performance evaluation

## Best Practices

### DO

✅ **Chunk documents** appropriately for your domain
✅ **Use reranking** for improved relevance
✅ **Monitor context window** usage
✅ **Cache embeddings** to reduce API calls
✅ **Implement fallback** strategies for retrieval failures
✅ **Test retrieval quality** with evaluation metrics
✅ **Use hybrid search** for better recall

### DON'T

❌ **Retrieve too many documents** (diminishing returns)
❌ **Ignore token limits** (truncation loses context)
❌ **Skip chunking** for long documents
❌ **Use single retrieval strategy** without testing alternatives
❌ **Forget metadata** in documents (needed for filtering)
❌ **Hardcode chunk sizes** (tune for your use case)

## Common Pitfalls

### 1. Context Window Overflow

**Problem**: Retrieved context exceeds model limits
**Solution**: Implement intelligent truncation and token counting

### 2. Poor Chunking Strategy

**Problem**: Important information split across chunks
**Solution**: Use semantic chunking or larger overlaps

### 3. Retrieval Quality Issues

**Problem**: Irrelevant documents retrieved
**Solution**: Implement reranking and hybrid search

## Troubleshooting

### Issue: Slow Retrieval

**Solution**: Use approximate nearest neighbors, optimize vector dimensions

### Issue: Poor Answer Quality

**Solution**: Increase K, improve chunking, add reranking

### Issue: High Memory Usage

**Solution**: Use memory-mapped indexes, implement pagination

## Next Steps

After mastering RAG pipelines:
1. **pyo3-dspy-agents**: Multi-hop reasoning agents
2. **pyo3-dspy-async-streaming**: Streaming RAG responses
3. **pyo3-dspy-production**: Caching and monitoring
4. **pyo3-dspy-optimization**: Fine-tune retrieval

## References

- [DSPy RAG Documentation](https://dspy-docs.vercel.app/docs/building-blocks/retrievers)
- [ChromaDB Documentation](https://docs.trychroma.com)
- [Qdrant Documentation](https://qdrant.tech/documentation)
- [RAG Best Practices](https://www.anthropic.com/research/retrieval-augmented-generation)

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Maintainer**: DSPy-PyO3 Integration Team
