use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Document with text content and embeddings
#[derive(Debug, Clone, Serialize, Deserialize)]
struct Document {
    id: String,
    text: String,
    embedding: Vec<f32>,
}

/// Search result with multiple scores
#[derive(Debug, Clone)]
struct SearchResult {
    doc_id: String,
    text: String,
    vector_score: f32,
    bm25_score: f32,
    combined_score: f32,
    rank: usize,
}

/// BM25 parameters
#[derive(Debug, Clone)]
struct BM25Params {
    k1: f32,  // Term saturation parameter (typically 1.2-2.0)
    b: f32,   // Length normalization (typically 0.75)
}

impl Default for BM25Params {
    fn default() -> Self {
        Self { k1: 1.5, b: 0.75 }
    }
}

/// Fusion strategy for combining scores
#[derive(Debug, Clone, Copy)]
enum FusionStrategy {
    WeightedSum { vector_weight: f32, bm25_weight: f32 },
    ReciprocalRankFusion { k: f32 },
}

/// Hybrid search engine
struct HybridSearchEngine {
    documents: Vec<Document>,
    bm25_params: BM25Params,
    idf_cache: HashMap<String, f32>,
    avg_doc_length: f32,
}

impl HybridSearchEngine {
    fn new(documents: Vec<Document>, bm25_params: BM25Params) -> Self {
        let avg_doc_length = documents.iter()
            .map(|d| tokenize(&d.text).len() as f32)
            .sum::<f32>() / documents.len() as f32;

        let mut engine = Self {
            documents,
            bm25_params,
            idf_cache: HashMap::new(),
            avg_doc_length,
        };

        engine.compute_idf();
        engine
    }

    /// Compute IDF (Inverse Document Frequency) for all terms
    fn compute_idf(&mut self) {
        let n = self.documents.len() as f32;
        let mut term_doc_freq: HashMap<String, usize> = HashMap::new();

        // Count documents containing each term
        for doc in &self.documents {
            let tokens: std::collections::HashSet<_> = tokenize(&doc.text).into_iter().collect();
            for term in tokens {
                *term_doc_freq.entry(term).or_insert(0) += 1;
            }
        }

        // Compute IDF for each term
        for (term, df) in term_doc_freq {
            let idf = ((n - df as f32 + 0.5) / (df as f32 + 0.5) + 1.0).ln();
            self.idf_cache.insert(term, idf);
        }
    }

    /// Vector similarity search using cosine similarity
    fn vector_search(&self, query_embedding: &[f32], top_k: usize) -> Vec<(usize, f32)> {
        let mut scores: Vec<(usize, f32)> = self.documents
            .iter()
            .enumerate()
            .map(|(idx, doc)| {
                let score = cosine_similarity(query_embedding, &doc.embedding);
                (idx, score)
            })
            .collect();

        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        scores.truncate(top_k);
        scores
    }

    /// BM25 keyword search
    fn bm25_search(&self, query: &str, top_k: usize) -> Vec<(usize, f32)> {
        let query_tokens = tokenize(query);
        let mut scores: Vec<(usize, f32)> = self.documents
            .iter()
            .enumerate()
            .map(|(idx, doc)| {
                let score = self.compute_bm25_score(&query_tokens, doc);
                (idx, score)
            })
            .collect();

        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        scores.truncate(top_k);
        scores
    }

    /// Compute BM25 score for a document given query tokens
    fn compute_bm25_score(&self, query_tokens: &[String], doc: &Document) -> f32 {
        let doc_tokens = tokenize(&doc.text);
        let doc_length = doc_tokens.len() as f32;
        let mut term_freq: HashMap<String, usize> = HashMap::new();

        // Count term frequencies in document
        for token in &doc_tokens {
            *term_freq.entry(token.clone()).or_insert(0) += 1;
        }

        // Compute BM25 score
        let mut score = 0.0;
        for query_term in query_tokens {
            let tf = *term_freq.get(query_term).unwrap_or(&0) as f32;
            let idf = self.idf_cache.get(query_term).unwrap_or(&0.0);

            // BM25 formula
            let numerator = tf * (self.bm25_params.k1 + 1.0);
            let denominator = tf + self.bm25_params.k1 * (1.0 - self.bm25_params.b +
                self.bm25_params.b * (doc_length / self.avg_doc_length));

            score += idf * (numerator / denominator);
        }

        score
    }

    /// Hybrid search with configurable fusion strategy
    fn hybrid_search(
        &self,
        query: &str,
        query_embedding: &[f32],
        top_k: usize,
        strategy: FusionStrategy,
    ) -> Vec<SearchResult> {
        // Get results from both search methods
        let vector_results = self.vector_search(query_embedding, top_k * 2);
        let bm25_results = self.bm25_search(query, top_k * 2);

        // Create score maps
        let vector_scores: HashMap<usize, f32> = vector_results.iter()
            .map(|(idx, score)| (*idx, *score))
            .collect();

        let bm25_scores: HashMap<usize, f32> = bm25_results.iter()
            .map(|(idx, score)| (*idx, *score))
            .collect();

        // Combine all document indices
        let mut all_indices: std::collections::HashSet<usize> =
            vector_scores.keys().chain(bm25_scores.keys()).copied().collect();

        // Compute combined scores based on strategy
        let mut combined_results: Vec<SearchResult> = all_indices
            .drain()
            .map(|idx| {
                let vector_score = *vector_scores.get(&idx).unwrap_or(&0.0);
                let bm25_score = *bm25_scores.get(&idx).unwrap_or(&0.0);

                let combined_score = match strategy {
                    FusionStrategy::WeightedSum { vector_weight, bm25_weight } => {
                        self.weighted_sum_fusion(
                            vector_score,
                            bm25_score,
                            vector_weight,
                            bm25_weight,
                            &vector_scores,
                            &bm25_scores,
                        )
                    }
                    FusionStrategy::ReciprocalRankFusion { k } => {
                        self.rrf_fusion(idx, &vector_results, &bm25_results, k)
                    }
                };

                let doc = &self.documents[idx];
                SearchResult {
                    doc_id: doc.id.clone(),
                    text: doc.text.clone(),
                    vector_score,
                    bm25_score,
                    combined_score,
                    rank: 0, // Will be set after sorting
                }
            })
            .collect();

        // Sort by combined score
        combined_results.sort_by(|a, b| b.combined_score.partial_cmp(&a.combined_score).unwrap());

        // Set ranks
        for (rank, result) in combined_results.iter_mut().enumerate() {
            result.rank = rank + 1;
        }

        combined_results.truncate(top_k);
        combined_results
    }

    /// Weighted sum fusion with normalization
    fn weighted_sum_fusion(
        &self,
        vector_score: f32,
        bm25_score: f32,
        vector_weight: f32,
        bm25_weight: f32,
        all_vector_scores: &HashMap<usize, f32>,
        all_bm25_scores: &HashMap<usize, f32>,
    ) -> f32 {
        // Normalize scores to [0, 1]
        let max_vector = all_vector_scores.values().fold(0.0f32, |a, &b| a.max(b));
        let max_bm25 = all_bm25_scores.values().fold(0.0f32, |a, &b| a.max(b));

        let norm_vector = if max_vector > 0.0 { vector_score / max_vector } else { 0.0 };
        let norm_bm25 = if max_bm25 > 0.0 { bm25_score / max_bm25 } else { 0.0 };

        vector_weight * norm_vector + bm25_weight * norm_bm25
    }

    /// Reciprocal Rank Fusion (RRF)
    fn rrf_fusion(
        &self,
        doc_idx: usize,
        vector_results: &[(usize, f32)],
        bm25_results: &[(usize, f32)],
        k: f32,
    ) -> f32 {
        let vector_rank = vector_results.iter()
            .position(|(idx, _)| *idx == doc_idx)
            .map(|pos| 1.0 / (k + pos as f32 + 1.0))
            .unwrap_or(0.0);

        let bm25_rank = bm25_results.iter()
            .position(|(idx, _)| *idx == doc_idx)
            .map(|pos| 1.0 / (k + pos as f32 + 1.0))
            .unwrap_or(0.0);

        vector_rank + bm25_rank
    }
}

/// Cosine similarity between two vectors
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    let dot_product: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let mag_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let mag_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();

    if mag_a == 0.0 || mag_b == 0.0 {
        0.0
    } else {
        dot_product / (mag_a * mag_b)
    }
}

/// Simple tokenization (lowercase + split on whitespace)
fn tokenize(text: &str) -> Vec<String> {
    text.to_lowercase()
        .split_whitespace()
        .map(|s| s.trim_matches(|c: char| !c.is_alphanumeric()))
        .filter(|s| !s.is_empty())
        .map(String::from)
        .collect()
}

/// Create sample documents with embeddings
fn create_sample_documents() -> Vec<Document> {
    vec![
        Document {
            id: "doc1".to_string(),
            text: "Machine learning algorithms for natural language processing".to_string(),
            embedding: vec![0.8, 0.3, 0.1, 0.6, 0.2],
        },
        Document {
            id: "doc2".to_string(),
            text: "Deep learning neural networks and backpropagation".to_string(),
            embedding: vec![0.7, 0.4, 0.2, 0.5, 0.3],
        },
        Document {
            id: "doc3".to_string(),
            text: "Natural language understanding with transformers".to_string(),
            embedding: vec![0.75, 0.35, 0.15, 0.55, 0.25],
        },
        Document {
            id: "doc4".to_string(),
            text: "Computer vision and image recognition techniques".to_string(),
            embedding: vec![0.2, 0.8, 0.7, 0.1, 0.4],
        },
        Document {
            id: "doc5".to_string(),
            text: "Reinforcement learning for game playing agents".to_string(),
            embedding: vec![0.5, 0.5, 0.5, 0.4, 0.6],
        },
        Document {
            id: "doc6".to_string(),
            text: "Statistical methods in machine learning and data science".to_string(),
            embedding: vec![0.6, 0.2, 0.3, 0.7, 0.1],
        },
        Document {
            id: "doc7".to_string(),
            text: "Neural architecture search and autoML techniques".to_string(),
            embedding: vec![0.65, 0.45, 0.25, 0.5, 0.35],
        },
        Document {
            id: "doc8".to_string(),
            text: "Text generation using large language models".to_string(),
            embedding: vec![0.78, 0.32, 0.12, 0.58, 0.22],
        },
    ]
}

/// Display search results in a formatted table
fn display_results(query: &str, results: &[SearchResult], strategy_name: &str) {
    println!("\n{}", "=".repeat(80));
    println!("Query: \"{}\"", query);
    println!("Strategy: {}", strategy_name);
    println!("{}", "-".repeat(80));
    println!("{:<6} {:<8} {:<10} {:<10} {:<10} {:<40}",
        "Rank", "Doc ID", "Vector", "BM25", "Combined", "Text");
    println!("{}", "-".repeat(80));

    for result in results {
        let text_preview = if result.text.len() > 37 {
            format!("{}...", &result.text[..37])
        } else {
            result.text.clone()
        };

        println!("{:<6} {:<8} {:<10.4} {:<10.4} {:<10.4} {:<40}",
            result.rank,
            result.doc_id,
            result.vector_score,
            result.bm25_score,
            result.combined_score,
            text_preview,
        );
    }
    println!("{}", "-".repeat(80));
}

/// Compare different fusion strategies
fn compare_strategies(
    engine: &HybridSearchEngine,
    query: &str,
    query_embedding: &[f32],
    top_k: usize,
) {
    println!("\n{:=^80}", " FUSION STRATEGY COMPARISON ");

    // Weighted Sum with different weights
    let strategies = vec![
        (
            "Weighted Sum (0.7 vector, 0.3 BM25)",
            FusionStrategy::WeightedSum { vector_weight: 0.7, bm25_weight: 0.3 },
        ),
        (
            "Weighted Sum (0.5 vector, 0.5 BM25)",
            FusionStrategy::WeightedSum { vector_weight: 0.5, bm25_weight: 0.5 },
        ),
        (
            "Weighted Sum (0.3 vector, 0.7 BM25)",
            FusionStrategy::WeightedSum { vector_weight: 0.3, bm25_weight: 0.7 },
        ),
        (
            "Reciprocal Rank Fusion (k=60)",
            FusionStrategy::ReciprocalRankFusion { k: 60.0 },
        ),
    ];

    for (name, strategy) in strategies {
        let results = engine.hybrid_search(query, query_embedding, top_k, strategy);
        display_results(query, &results, name);
    }
}

fn main() -> Result<()> {
    println!("{:=^80}", " HYBRID SEARCH DEMONSTRATION ");
    println!("\nCombining vector similarity and BM25 keyword search");
    println!("Demonstrating score fusion strategies and reranking\n");

    // Initialize documents and search engine
    let documents = create_sample_documents();
    let bm25_params = BM25Params::default();
    let engine = HybridSearchEngine::new(documents, bm25_params);

    println!("Indexed {} documents", engine.documents.len());
    println!("Average document length: {:.2} tokens", engine.avg_doc_length);
    println!("Unique terms in IDF cache: {}", engine.idf_cache.len());

    // Example 1: NLP query (should favor semantic similarity)
    let query1 = "natural language processing";
    let query1_embedding = vec![0.82, 0.28, 0.08, 0.62, 0.18];
    compare_strategies(&engine, query1, &query1_embedding, 5);

    // Example 2: Machine learning query (balanced relevance)
    let query2 = "machine learning algorithms";
    let query2_embedding = vec![0.75, 0.25, 0.2, 0.65, 0.15];
    compare_strategies(&engine, query2, &query2_embedding, 5);

    // Example 3: Specific term query (should favor keyword match)
    let query3 = "neural architecture search";
    let query3_embedding = vec![0.6, 0.4, 0.3, 0.5, 0.4];
    compare_strategies(&engine, query3, &query3_embedding, 5);

    // Detailed analysis of one query
    println!("\n{:=^80}", " DETAILED ANALYSIS ");
    let analysis_query = "transformers for text generation";
    let analysis_embedding = vec![0.77, 0.33, 0.13, 0.57, 0.23];

    println!("\nQuery: \"{}\"", analysis_query);
    println!("\n{:-^80}", " Vector Search Only ");
    let vector_only = engine.vector_search(&analysis_embedding, 5);
    for (rank, (idx, score)) in vector_only.iter().enumerate() {
        println!("{}: {} - {:.4}", rank + 1, engine.documents[*idx].id, score);
    }

    println!("\n{:-^80}", " BM25 Search Only ");
    let bm25_only = engine.bm25_search(analysis_query, 5);
    for (rank, (idx, score)) in bm25_only.iter().enumerate() {
        println!("{}: {} - {:.4}", rank + 1, engine.documents[*idx].id, score);
    }

    println!("\n{:-^80}", " Hybrid Search (RRF) ");
    let hybrid = engine.hybrid_search(
        analysis_query,
        &analysis_embedding,
        5,
        FusionStrategy::ReciprocalRankFusion { k: 60.0 },
    );
    for result in &hybrid {
        println!("{}: {} - combined: {:.4} (vec: {:.4}, bm25: {:.4})",
            result.rank, result.doc_id, result.combined_score,
            result.vector_score, result.bm25_score);
    }

    println!("\n{:=^80}", " PERFORMANCE INSIGHTS ");
    println!("\nFusion Strategy Guidelines:");
    println!("  • Weighted Sum: Simple, interpretable, allows direct control");
    println!("  • RRF: Rank-based, less sensitive to score magnitude differences");
    println!("\nWeight Tuning Tips:");
    println!("  • Higher vector weight: Better for semantic/conceptual queries");
    println!("  • Higher BM25 weight: Better for specific term/phrase queries");
    println!("  • Equal weights (0.5/0.5): Balanced approach for general use");
    println!("\nBM25 Parameter Tuning:");
    println!("  • k1 (1.2-2.0): Controls term frequency saturation");
    println!("  • b (0.75): Controls length normalization impact");
    println!("\nAdvanced Techniques:");
    println!("  • Query-dependent weight adjustment");
    println!("  • Learning-to-rank reranking");
    println!("  • Multi-stage retrieval pipelines");
    println!("  • Field-specific BM25 (title vs content)");

    Ok(())
}
