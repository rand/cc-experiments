use anyhow::{Context, Result};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use std::time::Instant;

/// Document in the corpus
#[derive(Debug, Clone, Serialize, Deserialize)]
struct Document {
    id: String,
    text: String,
    metadata: Option<serde_json::Value>,
}

/// Initial retrieval result from Stage 1
#[derive(Debug, Clone)]
struct InitialResult {
    doc: Document,
    score: f64,
}

/// Reranked result from Stage 2
#[derive(Debug, Clone)]
struct RerankedResult {
    doc: Document,
    initial_score: f64,
    rerank_score: f64,
    rank_change: i32,
}

/// Two-stage retrieval pipeline with cross-encoder reranking
struct RerankingPipeline {
    py: Python<'static>,
    embedder: Py<PyAny>,
    reranker: Py<PyAny>,
    corpus: Vec<Document>,
}

impl RerankingPipeline {
    /// Initialize the pipeline with embedding and reranking models
    fn new() -> Result<Self> {
        pyo3::prepare_freethreaded_python();
        let py = unsafe { Python::assume_gil_acquired() };

        // Import sentence-transformers
        let sentence_transformers = py
            .import_bound("sentence_transformers")
            .context("Failed to import sentence_transformers - install with: pip install sentence-transformers")?;

        println!("Loading embedding model (bi-encoder)...");
        // Bi-encoder for fast initial retrieval
        let embedder = sentence_transformers
            .call_method1("SentenceTransformer", ("all-MiniLM-L6-v2",))
            .context("Failed to load embedding model")?;

        println!("Loading reranking model (cross-encoder)...");
        // Cross-encoder for accurate reranking
        let cross_encoder = py
            .import_bound("sentence_transformers")
            .context("Failed to import for cross-encoder")?;
        let reranker = cross_encoder
            .call_method1("CrossEncoder", ("cross-encoder/ms-marco-MiniLM-L-6-v2",))
            .context("Failed to load cross-encoder model")?;

        // Create sample corpus
        let corpus = Self::create_sample_corpus();
        println!("Loaded {} documents in corpus\n", corpus.len());

        Ok(Self {
            py: unsafe { std::mem::transmute(py) },
            embedder: embedder.into(),
            reranker: reranker.into(),
            corpus,
        })
    }

    /// Create a sample document corpus for demonstration
    fn create_sample_corpus() -> Vec<Document> {
        vec![
            Document {
                id: "doc1".to_string(),
                text: "Python is a high-level programming language with dynamic typing and garbage collection.".to_string(),
                metadata: None,
            },
            Document {
                id: "doc2".to_string(),
                text: "Rust is a systems programming language focused on safety, speed, and concurrency.".to_string(),
                metadata: None,
            },
            Document {
                id: "doc3".to_string(),
                text: "Machine learning models can be deployed using various frameworks and tools.".to_string(),
                metadata: None,
            },
            Document {
                id: "doc4".to_string(),
                text: "Cross-encoders provide more accurate relevance scoring than bi-encoders for reranking tasks.".to_string(),
                metadata: None,
            },
            Document {
                id: "doc5".to_string(),
                text: "Rust's ownership system prevents data races and ensures memory safety without garbage collection.".to_string(),
                metadata: None,
            },
            Document {
                id: "doc6".to_string(),
                text: "Natural language processing involves understanding and generating human language with computers.".to_string(),
                metadata: None,
            },
            Document {
                id: "doc7".to_string(),
                text: "Embedding models convert text into dense vector representations for semantic search.".to_string(),
                metadata: None,
            },
            Document {
                id: "doc8".to_string(),
                text: "Rust has zero-cost abstractions, meaning high-level features compile down to efficient machine code.".to_string(),
                metadata: None,
            },
            Document {
                id: "doc9".to_string(),
                text: "Two-stage retrieval combines fast approximate search with precise reranking for optimal results.".to_string(),
                metadata: None,
            },
            Document {
                id: "doc10".to_string(),
                text: "Python's simplicity and extensive libraries make it popular for rapid prototyping.".to_string(),
                metadata: None,
            },
        ]
    }

    /// Stage 1: Fast bi-encoder retrieval (top-K candidates)
    fn stage1_retrieval(&self, query: &str, top_k: usize) -> Result<Vec<InitialResult>> {
        let start = Instant::now();

        // Encode query and documents
        let query_embedding = self
            .embedder
            .call_method1(self.py, "encode", (query,))
            .context("Failed to encode query")?;

        let corpus_texts: Vec<&str> = self.corpus.iter().map(|d| d.text.as_str()).collect();
        let corpus_embeddings = self
            .embedder
            .call_method1(self.py, "encode", (corpus_texts,))
            .context("Failed to encode corpus")?;

        // Compute cosine similarity
        let util = self
            .py
            .import_bound("sentence_transformers.util")
            .context("Failed to import util")?;

        let kwargs = PyDict::new_bound(self.py);
        kwargs.set_item("top_k", top_k)?;

        let hits = util
            .call_method(
                "semantic_search",
                (query_embedding, corpus_embeddings),
                Some(&kwargs),
            )
            .context("Failed to compute semantic search")?;

        // Extract results
        let hits_list = hits
            .downcast::<PyList>()
            .map_err(|e| anyhow::anyhow!("Failed to downcast hits: {}", e))?;
        let first_hits_item = hits_list.get_item(0)?;
        let first_hits = first_hits_item
            .downcast::<PyList>()
            .map_err(|e| anyhow::anyhow!("Failed to get first hits: {}", e))?;

        let mut results = Vec::new();
        for hit in first_hits.iter() {
            let hit_dict = hit
                .downcast::<PyDict>()
                .map_err(|e| anyhow::anyhow!("Failed to downcast hit: {}", e))?;
            let corpus_id: usize = hit_dict
                .get_item("corpus_id")?
                .ok_or_else(|| anyhow::anyhow!("Missing corpus_id"))?
                .extract()?;
            let score: f64 = hit_dict
                .get_item("score")?
                .ok_or_else(|| anyhow::anyhow!("Missing score"))?
                .extract()?;

            results.push(InitialResult {
                doc: self.corpus[corpus_id].clone(),
                score,
            });
        }

        let duration = start.elapsed();
        println!("Stage 1 (Bi-encoder): Retrieved {} candidates in {:?}", results.len(), duration);

        Ok(results)
    }

    /// Stage 2: Cross-encoder reranking for precise scoring
    fn stage2_reranking(&self, query: &str, candidates: Vec<InitialResult>, top_k: usize) -> Result<Vec<RerankedResult>> {
        let start = Instant::now();

        // Store original positions for rank change calculation
        let original_order: Vec<String> = candidates.iter().map(|r| r.doc.id.clone()).collect();

        // Create query-document pairs
        let pairs: Vec<(String, String)> = candidates
            .iter()
            .map(|r| (query.to_string(), r.doc.text.clone()))
            .collect();

        // Compute cross-encoder scores
        let pairs_py: Vec<(&str, &str)> = pairs
            .iter()
            .map(|(q, d)| (q.as_str(), d.as_str()))
            .collect();

        let scores = self
            .reranker
            .call_method1(self.py, "predict", (pairs_py,))
            .context("Failed to compute cross-encoder scores")?;

        let scores_list: Vec<f64> = scores.extract(self.py)?;

        // Combine with initial results
        let mut reranked: Vec<RerankedResult> = candidates
            .into_iter()
            .zip(scores_list.into_iter())
            .map(|(initial_result, rerank_score)| RerankedResult {
                doc: initial_result.doc,
                initial_score: initial_result.score,
                rerank_score,
                rank_change: 0, // Will be calculated after sorting
            })
            .collect();

        // Sort by rerank score
        reranked.sort_by(|a, b| b.rerank_score.partial_cmp(&a.rerank_score).unwrap());

        // Calculate rank changes
        for (new_rank, result) in reranked.iter_mut().enumerate() {
            let old_rank = original_order
                .iter()
                .position(|id| id == &result.doc.id)
                .unwrap();
            result.rank_change = old_rank as i32 - new_rank as i32;
        }

        // Keep only top-K
        reranked.truncate(top_k);

        let duration = start.elapsed();
        println!("Stage 2 (Cross-encoder): Reranked to {} results in {:?}\n", reranked.len(), duration);

        Ok(reranked)
    }

    /// Full two-stage pipeline
    fn search(&self, query: &str, stage1_k: usize, stage2_k: usize) -> Result<Vec<RerankedResult>> {
        println!("Query: \"{}\"\n", query);

        // Stage 1: Fast retrieval
        let candidates = self.stage1_retrieval(query, stage1_k)?;

        // Stage 2: Precise reranking
        let results = self.stage2_reranking(query, candidates, stage2_k)?;

        Ok(results)
    }

    /// Display results with comparison
    fn display_results(&self, results: &[RerankedResult]) {
        println!("=== Final Results (After Reranking) ===\n");

        for (rank, result) in results.iter().enumerate() {
            let rank_symbol = if result.rank_change > 0 {
                format!("↑{}", result.rank_change)
            } else if result.rank_change < 0 {
                format!("↓{}", result.rank_change.abs())
            } else {
                "→".to_string()
            };

            println!("Rank {}: {} [{}]", rank + 1, result.doc.id, rank_symbol);
            println!("  Text: {}", result.doc.text);
            println!(
                "  Scores: Initial={:.4}, Rerank={:.4} (Δ={:.4})",
                result.initial_score,
                result.rerank_score,
                result.rerank_score - result.initial_score
            );
            println!();
        }
    }

    /// Demonstrate the reranking improvement
    fn demonstrate_improvement(&self) -> Result<()> {
        println!("╔════════════════════════════════════════════════════════╗");
        println!("║   Two-Stage Retrieval with Cross-Encoder Reranking   ║");
        println!("╚════════════════════════════════════════════════════════╝\n");

        // Example query about Rust's safety features
        let query = "How does Rust ensure memory safety?";
        let results = self.search(query, 10, 5)?;
        self.display_results(&results);

        println!("─────────────────────────────────────────────────────────\n");

        // Example query about reranking
        let query = "What is the difference between bi-encoders and cross-encoders?";
        let results = self.search(query, 10, 5)?;
        self.display_results(&results);

        println!("─────────────────────────────────────────────────────────\n");
        println!("Key Observations:");
        println!("  • Stage 1 uses fast bi-encoder for broad recall");
        println!("  • Stage 2 uses cross-encoder for precise relevance");
        println!("  • Rank changes (↑/↓) show reranking improvements");
        println!("  • Score deltas reveal which docs benefited most");
        println!("\nLatency vs Quality Tradeoff:");
        println!("  • Stage 1: Fast (~50ms), good recall, approximate");
        println!("  • Stage 2: Slower (~200ms), excellent precision");
        println!("  • Combined: Optimal balance for production systems");

        Ok(())
    }
}

fn main() -> Result<()> {
    println!("Initializing two-stage retrieval pipeline...\n");

    let pipeline = RerankingPipeline::new()
        .context("Failed to initialize pipeline")?;

    pipeline.demonstrate_improvement()
        .context("Failed to run demonstration")?;

    Ok(())
}
