# RAG Pipeline Evaluation Framework

A comprehensive evaluation framework for RAG (Retrieval-Augmented Generation) pipelines, measuring both retrieval quality and generation accuracy.

## Overview

This example demonstrates:
- **Retrieval metrics**: Precision@k, Recall@k, MRR (Mean Reciprocal Rank), NDCG (Normalized Discounted Cumulative Gain)
- **Generation metrics**: BLEU score, ROUGE scores, Answer relevance
- **End-to-end pipeline evaluation** with test sets
- **Statistical aggregation** across queries
- **HTML report generation** for visualization

## Metrics Explained

### Retrieval Metrics

#### Precision@k
Measures what fraction of the top-k retrieved documents are relevant:
```
precision@k = (relevant documents in top-k) / k
```

#### Recall@k
Measures what fraction of all relevant documents are in the top-k:
```
recall@k = (relevant documents in top-k) / (total relevant documents)
```

#### Mean Reciprocal Rank (MRR)
Measures how high the first relevant document appears:
```
MRR = 1 / (rank of first relevant document)
```

#### NDCG (Normalized Discounted Cumulative Gain)
Measures ranking quality with position-based discounting:
```
DCG@k = Σ (rel_i / log2(i + 1)) for i=1 to k
NDCG@k = DCG@k / IDCG@k (normalized by ideal ranking)
```

### Generation Metrics

#### BLEU Score
Measures n-gram overlap between generated and reference answers:
```
BLEU = brevity_penalty × exp(Σ log(precision_n) / N)
```

#### ROUGE Scores
- **ROUGE-1**: Unigram overlap
- **ROUGE-2**: Bigram overlap
- **ROUGE-L**: Longest common subsequence

#### Answer Relevance
Simple overlap-based relevance score (0.0 to 1.0).

## Test Set Format

The `testset.json` file contains evaluation queries:

```json
{
  "queries": [
    {
      "id": "q1",
      "query": "What is machine learning?",
      "relevant_docs": ["doc1", "doc3", "doc7"],
      "ground_truth_answer": "Machine learning is a subset of AI...",
      "keywords": ["machine learning", "AI", "algorithms"]
    }
  ]
}
```

## Usage

### Run Evaluation

```bash
cargo run
```

### Output

The framework generates:
1. **Console output**: Per-query and aggregate metrics
2. **HTML report**: `evaluation_report.html` with visualizations

### Sample Output

```
=== RAG Pipeline Evaluation ===

Query: What is machine learning?
Retrieved: 5 documents
Relevant in results: 2

Retrieval Metrics:
  Precision@5: 0.400
  Recall@5: 0.667
  MRR: 0.500
  NDCG@5: 0.613

Generated Answer: Machine learning is a field of AI that enables systems to learn...

Generation Metrics:
  BLEU: 0.524
  ROUGE-1: 0.714
  ROUGE-2: 0.500
  ROUGE-L: 0.667
  Answer Relevance: 0.750

---

Aggregate Statistics (5 queries):
  Avg Precision@5: 0.560
  Avg Recall@5: 0.747
  Avg MRR: 0.683
  Avg NDCG@5: 0.721
  Avg BLEU: 0.612
  Avg ROUGE-1: 0.768
  Avg ROUGE-2: 0.601
  Avg ROUGE-L: 0.724
  Avg Relevance: 0.800

Report saved to: evaluation_report.html
```

## Integration with Real RAG Systems

### Custom Retriever

```rust
struct CustomRetriever {
    // Your retriever implementation
}

impl CustomRetriever {
    fn retrieve(&self, query: &str, k: usize) -> Vec<String> {
        // Implement your retrieval logic
        // Return document IDs
        vec![]
    }
}
```

### Custom Generator

```rust
struct CustomGenerator {
    // Your generator implementation
}

impl CustomGenerator {
    fn generate(&self, query: &str, context: &[String]) -> String {
        // Implement your generation logic
        String::new()
    }
}
```

### Evaluation Pipeline

```rust
let evaluator = RagEvaluator::new();
let test_set = evaluator.load_test_set("testset.json")?;

for query in test_set.queries {
    // Retrieve
    let retrieved_docs = retriever.retrieve(&query.query, 5);

    // Generate
    let generated_answer = generator.generate(&query.query, &retrieved_docs);

    // Evaluate
    let metrics = evaluator.evaluate_query(
        &retrieved_docs,
        &query.relevant_docs,
        &generated_answer,
        &query.ground_truth_answer,
        &query.keywords,
    );

    // Aggregate
    evaluator.add_result(metrics);
}

// Generate report
evaluator.generate_report("evaluation_report.html")?;
```

## Extending the Framework

### Add Custom Metrics

```rust
impl QueryMetrics {
    fn custom_metric(&self, custom_data: &CustomData) -> f64 {
        // Implement your metric
        0.0
    }
}
```

### Add Semantic Similarity

For production use, integrate with sentence transformers:

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')

# Calculate cosine similarity
def semantic_similarity(text1, text2):
    emb1 = model.encode(text1)
    emb2 = model.encode(text2)
    return cosine_similarity(emb1, emb2)
```

Then call from Rust via PyO3:

```rust
let similarity: f64 = py.eval(
    "semantic_similarity(text1, text2)",
    Some([("text1", &text1), ("text2", &text2)].into_py_dict(py)),
    None,
)?
.extract()?;
```

### Add Statistical Tests

```rust
// T-test for comparing two systems
fn compare_systems(
    metrics_a: &[QueryMetrics],
    metrics_b: &[QueryMetrics],
) -> TTestResult {
    // Implement statistical comparison
    TTestResult::default()
}
```

## Best Practices

### Test Set Design

1. **Diversity**: Cover different query types (factual, analytical, comparative)
2. **Difficulty**: Mix easy and hard queries
3. **Coverage**: Represent real user queries
4. **Size**: Minimum 50-100 queries for statistical significance

### Metric Selection

1. **Retrieval-focused**: Emphasize precision@k and NDCG
2. **Generation-focused**: Emphasize ROUGE and answer relevance
3. **User-facing**: Consider custom metrics aligned with user satisfaction

### Interpretation

1. **Precision vs Recall**: High precision = fewer false positives, high recall = fewer misses
2. **MRR**: Critical for single-answer systems
3. **NDCG**: Best for ranking quality assessment
4. **BLEU/ROUGE**: Best as relative metrics (compare systems)

### Continuous Evaluation

```bash
# Run on every deployment
cargo run --release > metrics.txt

# Compare with baseline
diff baseline_metrics.txt metrics.txt

# Automated alerts on regression
if [ $NDCG_DROP > 0.05 ]; then
    echo "ALERT: NDCG dropped by 5%"
fi
```

## Dependencies

- **pyo3**: Python integration for advanced metrics
- **anyhow**: Error handling
- **serde/serde_json**: JSON parsing
- **Rust 1.70+**: Required

## Architecture

```
┌─────────────────────────────────────────┐
│         RagEvaluator                     │
│  ┌────────────────────────────────────┐ │
│  │  Test Set Loader                   │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │  Retrieval Metrics Calculator       │ │
│  │  - precision@k, recall@k           │ │
│  │  - MRR, NDCG                       │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │  Generation Metrics Calculator      │ │
│  │  - BLEU, ROUGE                     │ │
│  │  - Answer relevance                │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │  Aggregation Engine                │ │
│  │  - Statistical summaries           │ │
│  │  - Distribution analysis           │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │  Report Generator                  │ │
│  │  - HTML output                     │ │
│  │  - Visualization                   │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## References

- [BLEU: a Method for Automatic Evaluation of Machine Translation](https://aclanthology.org/P02-1040.pdf)
- [ROUGE: A Package for Automatic Evaluation of Summaries](https://aclanthology.org/W04-1013.pdf)
- [Normalized Discounted Cumulative Gain](https://en.wikipedia.org/wiki/Discounted_cumulative_gain)
- [RAG Survey Paper](https://arxiv.org/abs/2312.10997)

## License

MIT
