# Two-Stage Retrieval with Cross-Encoder Reranking

A production-ready example demonstrating two-stage retrieval architecture that combines fast bi-encoder search with precise cross-encoder reranking.

## Architecture

```
Query
  ↓
┌─────────────────────────────────────┐
│ Stage 1: Bi-Encoder Retrieval      │
│  • Fast vector similarity search    │
│  • Retrieve top-100 candidates      │
│  • ~50ms latency                    │
│  • High recall, approximate         │
└─────────────────────────────────────┘
  ↓ (100 candidates)
┌─────────────────────────────────────┐
│ Stage 2: Cross-Encoder Reranking   │
│  • Precise relevance scoring        │
│  • Rerank to top-10 results         │
│  • ~200ms latency                   │
│  • High precision, exact            │
└─────────────────────────────────────┘
  ↓ (10 results)
Final Results
```

## Key Concepts

### Bi-Encoder (Stage 1)
- **Architecture**: Separate encoders for query and documents
- **Computation**: Pre-compute document embeddings, encode query at runtime
- **Similarity**: Cosine similarity in vector space
- **Speed**: Very fast (~50ms for 10K docs)
- **Accuracy**: Good but approximate
- **Use Case**: Initial broad retrieval

### Cross-Encoder (Stage 2)
- **Architecture**: Joint encoder for query-document pairs
- **Computation**: Encode each pair together (query + doc)
- **Similarity**: Direct relevance classification
- **Speed**: Slower (~20ms per doc)
- **Accuracy**: Excellent precision
- **Use Case**: Rerank top candidates

## Features Demonstrated

1. **Two-Stage Architecture**
   - Fast initial retrieval
   - Precise reranking
   - Optimal latency/quality balance

2. **Score Comparison**
   - Initial bi-encoder scores
   - Cross-encoder rerank scores
   - Score deltas and improvements

3. **Rank Change Tracking**
   - Visual rank movement (↑/↓/→)
   - Identifies most improved results
   - Quantifies reranking impact

4. **Performance Metrics**
   - Stage timing breakdown
   - Total pipeline latency
   - Throughput characteristics

## Installation

```bash
# Install Python dependencies
pip install sentence-transformers torch

# Build and run
cargo run
```

## Models Used

### Bi-Encoder: `all-MiniLM-L6-v2`
- **Purpose**: Fast semantic search
- **Dimensions**: 384
- **Speed**: Very fast
- **Size**: ~80MB

### Cross-Encoder: `ms-marco-MiniLM-L-6-v2`
- **Purpose**: Precise reranking
- **Training**: MS MARCO passage ranking
- **Output**: Relevance score
- **Size**: ~90MB

## Example Output

```
Query: "How does Rust ensure memory safety?"

Stage 1 (Bi-encoder): Retrieved 10 candidates in 45ms
Stage 2 (Cross-encoder): Reranked to 5 results in 187ms

=== Final Results (After Reranking) ===

Rank 1: doc5 [↑3]
  Text: Rust's ownership system prevents data races and ensures memory safety...
  Scores: Initial=0.6234, Rerank=0.9123 (Δ=0.2889)

Rank 2: doc2 [↑1]
  Text: Rust is a systems programming language focused on safety...
  Scores: Initial=0.7012, Rerank=0.8567 (Δ=0.1555)

Rank 3: doc8 [↓1]
  Text: Rust has zero-cost abstractions...
  Scores: Initial=0.7234, Rerank=0.7891 (Δ=0.0657)
```

## Code Structure

```rust
// Core types
struct Document { id, text, metadata }
struct InitialResult { doc, score }
struct RerankedResult { doc, initial_score, rerank_score, rank_change }

// Pipeline implementation
impl RerankingPipeline {
    fn stage1_retrieval()  // Fast bi-encoder search
    fn stage2_reranking()  // Cross-encoder reranking
    fn search()            // Full two-stage pipeline
    fn display_results()   // Score comparison
}
```

## Configuration Options

### Stage 1 Parameters
- `top_k`: Number of candidates (default: 100)
- Tradeoff: More candidates = better recall, slower stage 2

### Stage 2 Parameters
- `top_k`: Final results (default: 10)
- Tradeoff: More results = more compute time

### Score Thresholds
```rust
// Filter low-quality candidates before reranking
let candidates: Vec<_> = candidates
    .into_iter()
    .filter(|r| r.score > 0.3)  // Skip clearly irrelevant
    .collect();

// Apply minimum rerank score
results.retain(|r| r.rerank_score > 0.5);
```

## Performance Characteristics

### Latency Breakdown
| Stage | Time | Operation |
|-------|------|-----------|
| Stage 1 | ~50ms | Retrieve 100 candidates |
| Stage 2 | ~200ms | Rerank to 10 results |
| **Total** | **~250ms** | End-to-end query |

### Scaling Considerations
- **Corpus size**: Stage 1 scales logarithmically with vector index
- **Candidates**: Stage 2 scales linearly with candidate count
- **Batch size**: Rerank in batches for better GPU utilization

## Production Optimizations

### 1. Candidate Filtering
```rust
// Skip obvious non-matches before expensive reranking
let candidates = candidates
    .into_iter()
    .filter(|r| r.score > threshold)
    .take(stage2_limit)
    .collect();
```

### 2. Batch Reranking
```rust
// Process candidates in batches for GPU efficiency
const BATCH_SIZE: usize = 32;
for batch in candidates.chunks(BATCH_SIZE) {
    let scores = reranker.predict(batch)?;
    // Process batch...
}
```

### 3. Async Pipeline
```rust
// Parallelize independent operations
let (embeddings, metadata) = tokio::join!(
    embed_query(query),
    fetch_metadata(doc_ids)
);
```

### 4. Caching
```rust
// Cache cross-encoder scores for popular queries
let cache_key = format!("{}:{}", query_hash, doc_id);
if let Some(score) = cache.get(&cache_key) {
    return score;
}
```

## When to Use Reranking

### Good Use Cases
- Large corpus (>10K documents)
- Precision critical (search, recommendations)
- Can tolerate 200-300ms latency
- Budget for GPU inference

### Skip Reranking When
- Small corpus (<1K documents)
- Latency critical (<100ms SLA)
- Bi-encoder already sufficient
- Limited compute budget

## Evaluation Metrics

### Recall@K (Stage 1)
```
Recall@100 = Relevant docs in top-100 / Total relevant docs
Target: >95% to catch most relevant documents
```

### Precision@K (Stage 2)
```
Precision@10 = Relevant docs in top-10 / 10
Target: >80% after reranking
```

### Rank Improvement
```
Average Rank Improvement = Σ(old_rank - new_rank) / N
Positive values indicate successful reranking
```

## Rust-Specific Optimizations

### 1. Zero-Copy Document Access
```rust
// Use references to avoid cloning documents
struct InitialResult<'a> {
    doc: &'a Document,
    score: f64,
}
```

### 2. Parallel Batch Processing
```rust
use rayon::prelude::*;

// Process batches in parallel
batches.par_iter()
    .map(|batch| rerank_batch(batch))
    .collect()
```

### 3. Memory Pooling
```rust
// Reuse allocations across queries
struct Pipeline {
    buffer: Vec<f32>,  // Reusable embedding buffer
    results: Vec<Result>,  // Reusable results buffer
}
```

## Integration with RAG Pipelines

### DSPy Integration
```rust
// Use reranking as a DSPy module
#[derive(DSPySignature)]
struct Rerank {
    query: Input<String>,
    passages: Input<Vec<String>>,
    ranked_passages: Output<Vec<String>>,
}
```

### LangChain Integration
```rust
// Implement as a custom retriever
impl Retriever for RerankingPipeline {
    fn retrieve(&self, query: &str) -> Vec<Document> {
        self.search(query, 100, 10)
    }
}
```

## Troubleshooting

### Issue: Reranking doesn't improve results
- Check bi-encoder quality (may already be optimal)
- Verify cross-encoder model matches domain
- Increase stage 1 candidates (more options to rerank)

### Issue: High latency
- Reduce stage 2 candidates
- Use smaller cross-encoder model
- Batch reranking requests
- Cache popular queries

### Issue: Poor recall
- Increase stage 1 top-K
- Check bi-encoder model quality
- Verify document preprocessing

## References

- [Sentence-BERT Paper](https://arxiv.org/abs/1908.10084)
- [MS MARCO Dataset](https://microsoft.github.io/msmarco/)
- [Cross-Encoder Guide](https://www.sbert.net/examples/applications/cross-encoder/README.html)
- [Two-Stage Retrieval Best Practices](https://arxiv.org/abs/2104.08663)

## License

MIT
