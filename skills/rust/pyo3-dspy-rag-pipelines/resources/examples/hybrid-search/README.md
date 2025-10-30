# Hybrid Search Example

Advanced retrieval combining vector similarity search with BM25 keyword scoring, demonstrating multiple fusion strategies and reranking approaches.

## Overview

Hybrid search addresses limitations of pure vector or keyword search by combining:
- **Vector Search**: Semantic similarity using embeddings (cosine similarity)
- **BM25 Search**: Statistical keyword relevance (term frequency, inverse document frequency)
- **Score Fusion**: Weighted combination or rank-based merging

This approach provides robust retrieval across different query types.

## Features

### Search Methods
- **Vector Similarity**: Cosine similarity between query and document embeddings
- **BM25 Scoring**: Probabilistic keyword relevance with configurable parameters
- **Hybrid Fusion**: Multiple strategies for combining scores

### Fusion Strategies

#### 1. Weighted Sum
```rust
FusionStrategy::WeightedSum {
    vector_weight: 0.7,
    bm25_weight: 0.3,
}
```
- Normalizes scores to [0, 1]
- Applies linear combination with configurable weights
- Best when you understand relative importance of semantic vs keyword match

#### 2. Reciprocal Rank Fusion (RRF)
```rust
FusionStrategy::ReciprocalRankFusion { k: 60.0 }
```
- Combines based on ranking position, not raw scores
- Formula: `score = 1/(k + rank)` for each method
- Less sensitive to score magnitude differences
- `k` parameter (typically 60) controls fusion smoothness

### BM25 Implementation

Full BM25 scoring with tunable parameters:

```rust
BM25Params {
    k1: 1.5,  // Term saturation (1.2-2.0)
    b: 0.75,  // Length normalization (0.0-1.0)
}
```

**Formula**:
```
score = Σ IDF(term) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_doc_len)))
```

Where:
- `IDF`: Inverse document frequency
- `tf`: Term frequency in document
- `k1`: Controls term frequency saturation
- `b`: Controls document length normalization

## Building and Running

```bash
# Build the example
cargo build --release

# Run the demonstration
cargo run --release

# Run with detailed output
RUST_LOG=debug cargo run --release
```

## Code Structure

### Core Components

```rust
// Document with text and embedding
struct Document {
    id: String,
    text: String,
    embedding: Vec<f32>,
}

// Search result with multiple scores
struct SearchResult {
    doc_id: String,
    text: String,
    vector_score: f32,
    bm25_score: f32,
    combined_score: f32,
    rank: usize,
}

// Hybrid search engine
struct HybridSearchEngine {
    documents: Vec<Document>,
    bm25_params: BM25Params,
    idf_cache: HashMap<String, f32>,
    avg_doc_length: f32,
}
```

### Key Methods

```rust
impl HybridSearchEngine {
    // Vector similarity search
    fn vector_search(&self, query_embedding: &[f32], top_k: usize) -> Vec<(usize, f32)>;

    // BM25 keyword search
    fn bm25_search(&self, query: &str, top_k: usize) -> Vec<(usize, f32)>;

    // Hybrid search with fusion
    fn hybrid_search(
        &self,
        query: &str,
        query_embedding: &[f32],
        top_k: usize,
        strategy: FusionStrategy,
    ) -> Vec<SearchResult>;
}
```

## Example Output

```
========================= HYBRID SEARCH DEMONSTRATION =========================

Combining vector similarity and BM25 keyword search
Demonstrating score fusion strategies and reranking

Indexed 8 documents
Average document length: 6.25 tokens
Unique terms in IDF cache: 32

======================== FUSION STRATEGY COMPARISON =========================

================================================================================
Query: "natural language processing"
Strategy: Weighted Sum (0.7 vector, 0.3 BM25)
--------------------------------------------------------------------------------
Rank   Doc ID   Vector     BM25       Combined   Text
--------------------------------------------------------------------------------
1      doc1     0.9876     8.5432     0.7834     Machine learning algorithms for natu...
2      doc3     0.9654     6.2341     0.7123     Natural language understanding with...
3      doc8     0.8765     4.1234     0.6543     Text generation using large language...
...
```

## Usage Patterns

### Basic Hybrid Search

```rust
use anyhow::Result;

fn main() -> Result<()> {
    // Create documents with embeddings
    let documents = vec![
        Document {
            id: "doc1".to_string(),
            text: "Machine learning for NLP".to_string(),
            embedding: vec![0.8, 0.3, 0.1],
        },
        // ... more documents
    ];

    // Initialize engine
    let engine = HybridSearchEngine::new(
        documents,
        BM25Params::default(),
    );

    // Search with weighted sum
    let query = "natural language processing";
    let query_embedding = vec![0.82, 0.28, 0.08];

    let results = engine.hybrid_search(
        query,
        &query_embedding,
        5,
        FusionStrategy::WeightedSum {
            vector_weight: 0.7,
            bm25_weight: 0.3,
        },
    );

    for result in results {
        println!("{}: {} (score: {:.4})",
            result.rank, result.text, result.combined_score);
    }

    Ok(())
}
```

### Comparing Fusion Strategies

```rust
fn compare_fusion_strategies(
    engine: &HybridSearchEngine,
    query: &str,
    query_embedding: &[f32],
) {
    let strategies = vec![
        FusionStrategy::WeightedSum {
            vector_weight: 0.7,
            bm25_weight: 0.3
        },
        FusionStrategy::WeightedSum {
            vector_weight: 0.5,
            bm25_weight: 0.5
        },
        FusionStrategy::ReciprocalRankFusion { k: 60.0 },
    ];

    for strategy in strategies {
        let results = engine.hybrid_search(query, query_embedding, 10, strategy);
        analyze_results(&results);
    }
}
```

### Custom BM25 Parameters

```rust
// Tune for different content types
let params = BM25Params {
    k1: 2.0,   // Higher saturation for longer documents
    b: 0.5,    // Less length normalization
};

let engine = HybridSearchEngine::new(documents, params);
```

## Advanced Techniques

### 1. Query-Dependent Weight Adjustment

```rust
fn adaptive_weights(query: &str) -> (f32, f32) {
    let tokens = tokenize(query);

    if tokens.len() > 5 {
        // Long queries: favor BM25 (more specific)
        (0.4, 0.6)
    } else {
        // Short queries: favor vectors (more semantic)
        (0.7, 0.3)
    }
}
```

### 2. Multi-Stage Retrieval

```rust
// Stage 1: Fast broad retrieval with BM25
let candidates = engine.bm25_search(query, 100);

// Stage 2: Rerank with vectors
let reranked = rerank_with_vectors(&candidates, query_embedding);

// Stage 3: Final fusion
let final_results = apply_fusion(&reranked, strategy);
```

### 3. Field-Specific BM25

```rust
struct FieldedDocument {
    title: String,
    content: String,
    title_embedding: Vec<f32>,
    content_embedding: Vec<f32>,
}

// Different BM25 weights for title vs content
let title_score = compute_bm25(&doc.title, query, &title_params);
let content_score = compute_bm25(&doc.content, query, &content_params);
let combined = 2.0 * title_score + content_score;
```

### 4. Learning-to-Rank Integration

```rust
struct RankingFeatures {
    vector_score: f32,
    bm25_score: f32,
    query_length: usize,
    doc_length: usize,
    term_overlap: f32,
}

// Use ML model to combine features
let final_score = ranker.predict(&features);
```

## Performance Characteristics

### Time Complexity
- **Vector Search**: O(n × d) where n = docs, d = embedding dim
- **BM25 Search**: O(n × t) where t = avg tokens per doc
- **Hybrid Search**: O(n × (d + t))

### Space Complexity
- **Documents**: O(n × (d + t))
- **IDF Cache**: O(v) where v = vocabulary size
- **Result Storage**: O(k) where k = top_k

### Optimization Strategies
1. **Approximate Vector Search**: Use HNSW/IVF for large collections
2. **Inverted Index**: Build posting lists for BM25 efficiency
3. **Early Termination**: Stop scoring when top-k stabilizes
4. **Caching**: Cache frequent query results

## When to Use Each Strategy

### Weighted Sum
- **Use when**: You understand relative importance of methods
- **Pros**: Simple, interpretable, direct control
- **Cons**: Sensitive to score scale differences
- **Best for**: Domain-specific applications with known preferences

### Reciprocal Rank Fusion
- **Use when**: Score magnitudes vary significantly
- **Pros**: Robust, rank-based, less tuning needed
- **Cons**: Loses fine-grained score information
- **Best for**: General-purpose search, combining diverse methods

## Tuning Guidelines

### Vector Weight Higher (0.6-0.8)
- Conceptual/semantic queries
- Short queries (1-3 words)
- Cross-lingual search
- Fuzzy matching needs

### BM25 Weight Higher (0.6-0.8)
- Specific term queries
- Technical/exact match needs
- Long queries (5+ words)
- Known vocabulary

### Balanced (0.5/0.5)
- General-purpose search
- Unknown query distribution
- Starting point for tuning

## Integration with RAG

```rust
// Use hybrid search for context retrieval
let contexts = engine.hybrid_search(
    &question,
    &question_embedding,
    5,
    FusionStrategy::ReciprocalRankFusion { k: 60.0 },
);

// Pass to LLM for generation
let prompt = format!(
    "Context: {}\n\nQuestion: {}\n\nAnswer:",
    contexts.iter().map(|r| &r.text).collect::<Vec<_>>().join("\n"),
    question,
);
```

## Further Reading

- **BM25**: Robertson & Zaragoza (2009) "The Probabilistic Relevance Framework: BM25 and Beyond"
- **Fusion**: Cormack et al. (2009) "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"
- **Hybrid Search**: Best practices from Elasticsearch, Weaviate, Pinecone documentation
- **Learning-to-Rank**: Liu (2011) "Learning to Rank for Information Retrieval"

## License

MIT OR Apache-2.0
