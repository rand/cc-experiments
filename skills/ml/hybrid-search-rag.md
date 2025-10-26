---
name: hybrid-search-rag
description: Combining vector search with BM25 sparse retrieval using fusion algorithms for improved RAG accuracy
---

# Hybrid Search RAG

**Scope**: Vector + sparse retrieval, RRF fusion, parallel architectures, score normalization, metrics
**Lines**: ~450
**Last Updated**: 2025-10-26

## When to Use This Skill

Activate this skill when:
- Vector-only search misses exact keyword matches (e.g., product codes, technical terms)
- Need to balance semantic similarity with lexical precision
- Implementing production RAG requiring >90% retrieval accuracy
- Working with domain-specific terminology or rare entities
- Combining dense (vector) and sparse (BM25/TF-IDF) retrieval strategies
- Using Elasticsearch, Weaviate, Qdrant, or Pinecone with hybrid capabilities
- Measuring retrieval quality with Arize Phoenix or similar observability tools

## Core Concepts

### What is Hybrid Search?

**Hybrid Search**: Combine dense (vector) + sparse (keyword) retrieval
- **Dense retrieval**: Semantic similarity via embeddings (e.g., sentence transformers)
- **Sparse retrieval**: Lexical matching via BM25, TF-IDF (exact terms, n-grams)
- **Fusion**: Merge results using algorithms like Reciprocal Rank Fusion (RRF)

**Why hybrid beats single-method**:
- Vector search: Captures semantics but misses exact matches
- BM25: Captures keywords but misses paraphrases
- Hybrid: Best of both worlds (2024 studies show 15-30% improvement)

### Reciprocal Rank Fusion (RRF)

**RRF Algorithm** (Cormack et al., 2009; widely adopted in 2024 RAG systems):
```
RRF(d) = Σ (1 / (k + rank_i(d)))
```
- `d`: Document
- `rank_i(d)`: Rank of document in result set i
- `k`: Constant (typically 60)

**Benefits**:
- No score normalization needed
- Handles different score scales naturally
- Simple, effective, widely benchmarked

### Fusion Architectures

**Parallel retrieval** (recommended 2024-2025):
```
Query → [Vector Search] → Results_V
      → [BM25 Search]   → Results_B
      → RRF Fusion      → Final Rankings
```

**Sequential retrieval** (less common):
```
Query → Vector Search → Top-K → BM25 Rerank → Final Results
```

**Weighted fusion** (advanced):
```
Score = α * vector_score + (1-α) * bm25_score
# α tuned via evaluation (typically 0.5-0.7)
```

### Vector Database Support (2024-2025)

| Platform | Hybrid Support | Method |
|----------|----------------|--------|
| Elasticsearch | Native | Dense vector + BM25 fusion |
| Weaviate | Native (v1.19+) | Hybrid search API |
| Qdrant | Native (v1.7+) | Sparse vector support |
| Pinecone | Beta (2024) | Hybrid search indexes |
| ChromaDB | Manual | Separate queries + RRF |

### Score Normalization

**Min-Max normalization**:
```python
norm_score = (score - min_score) / (max_score - min_score)
```

**Z-score normalization**:
```python
norm_score = (score - mean) / std_dev
```

**Softmax normalization**:
```python
norm_score = exp(score) / Σ exp(all_scores)
```

**When needed**: Weighted fusion (not RRF, which is rank-based)

---

## Implementation Patterns

### Pattern 1: RRF Hybrid Search with DSPy

```python
import dspy
from typing import List, Dict, Tuple
from collections import defaultdict

class RRFHybridRetriever(dspy.Module):
    """Hybrid retrieval using Reciprocal Rank Fusion."""

    def __init__(self, k=10, rrf_k=60):
        super().__init__()
        self.k = k
        self.rrf_k = rrf_k

        # Two separate retrievers
        self.vector_retrieve = dspy.Retrieve(k=k)
        # BM25 retriever (custom implementation)
        self.bm25_retrieve = BM25Retriever(k=k)

    def reciprocal_rank_fusion(
        self,
        vector_results: List[str],
        bm25_results: List[str]
    ) -> List[str]:
        """Apply RRF to merge two ranked lists."""
        scores = defaultdict(float)

        # Score from vector results
        for rank, doc in enumerate(vector_results, start=1):
            scores[doc] += 1.0 / (self.rrf_k + rank)

        # Score from BM25 results
        for rank, doc in enumerate(bm25_results, start=1):
            scores[doc] += 1.0 / (self.rrf_k + rank)

        # Sort by combined score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in ranked[:self.k]]

    def forward(self, question: str):
        # Parallel retrieval
        vector_passages = self.vector_retrieve(question).passages
        bm25_passages = self.bm25_retrieve(question)

        # Apply RRF fusion
        fused_passages = self.reciprocal_rank_fusion(
            vector_passages, bm25_passages
        )

        return dspy.Prediction(passages=fused_passages)


class HybridRAG(dspy.Module):
    """RAG with hybrid retrieval."""

    def __init__(self, k=10):
        super().__init__()
        self.retrieve = RRFHybridRetriever(k=k)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question: str):
        retrieval = self.retrieve(question)
        context = "\n\n".join(retrieval.passages)
        return self.generate(context=context, question=question)


# Custom BM25 retriever (example using rank_bm25)
from rank_bm25 import BM25Okapi

class BM25Retriever:
    """Simple BM25 retriever for hybrid search."""

    def __init__(self, corpus: List[str], k=10):
        self.k = k
        self.corpus = corpus

        # Tokenize corpus
        tokenized = [doc.lower().split() for doc in corpus]
        self.bm25 = BM25Okapi(tokenized)

    def __call__(self, query: str) -> List[str]:
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)

        # Get top-k indices
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:self.k]

        return [self.corpus[i] for i in top_indices]
```

**When to use**:
- Need simple, effective fusion
- Working with medium-sized corpora (<1M docs)
- Want deterministic, parameter-free fusion

### Pattern 2: Elasticsearch Hybrid Search

```python
import dspy
from elasticsearch import Elasticsearch

class ElasticsearchHybridRetriever:
    """Hybrid retrieval using Elasticsearch native capabilities."""

    def __init__(self, es_client: Elasticsearch, index: str, k=10):
        self.es = es_client
        self.index = index
        self.k = k

    def __call__(self, query: str) -> List[str]:
        # Hybrid query: BM25 + dense vector
        search_body = {
            "query": {
                "bool": {
                    "should": [
                        # BM25 component
                        {
                            "match": {
                                "content": {
                                    "query": query,
                                    "boost": 0.5  # Weight for BM25
                                }
                            }
                        },
                        # Dense vector component
                        {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                    "params": {
                                        "query_vector": self._embed(query)
                                    }
                                },
                                "boost": 0.5  # Weight for vector
                            }
                        }
                    ]
                }
            },
            "size": self.k
        }

        response = self.es.search(index=self.index, body=search_body)

        passages = [hit["_source"]["content"] for hit in response["hits"]["hits"]]
        return passages

    def _embed(self, text: str) -> List[float]:
        """Generate embedding for text (use your embedding model)."""
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(text).tolist()


# Use with DSPy
class ESHybridRAG(dspy.Module):
    def __init__(self, es_client: Elasticsearch, index: str):
        super().__init__()
        self.retrieve = ElasticsearchHybridRetriever(es_client, index, k=5)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question: str):
        passages = self.retrieve(question)
        context = "\n\n".join(passages)
        return self.generate(context=context, question=question)
```

**When to use**:
- Already using Elasticsearch infrastructure
- Need production-scale hybrid search (millions of docs)
- Want built-in relevance tuning and analytics

### Pattern 3: Weaviate Hybrid Search

```python
import dspy
import weaviate

class WeaviateHybridRetriever:
    """Hybrid retrieval using Weaviate native hybrid search."""

    def __init__(self, client: weaviate.Client, class_name: str, k=10, alpha=0.5):
        self.client = client
        self.class_name = class_name
        self.k = k
        self.alpha = alpha  # 0 = pure BM25, 1 = pure vector

    def __call__(self, query: str) -> List[str]:
        result = (
            self.client.query
            .get(self.class_name, ["content"])
            .with_hybrid(
                query=query,
                alpha=self.alpha,  # Balance vector vs BM25
                fusion_type="relativeScoreFusion"  # or "rankedFusion"
            )
            .with_limit(self.k)
            .do()
        )

        passages = [
            item["content"]
            for item in result["data"]["Get"][self.class_name]
        ]
        return passages


# Use with DSPy
class WeaviateHybridRAG(dspy.Module):
    def __init__(self, weaviate_client: weaviate.Client, class_name: str):
        super().__init__()
        self.retrieve = WeaviateHybridRetriever(weaviate_client, class_name, k=5)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question: str):
        passages = self.retrieve(question)
        context = "\n\n".join(passages)
        return self.generate(context=context, question=question)
```

**When to use**:
- Want managed hybrid search (no manual RRF)
- Need GraphQL query flexibility
- Building with Weaviate v1.19+

### Pattern 4: Qdrant Sparse Vector Hybrid Search

```python
import dspy
from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector, NamedSparseVector

class QdrantHybridRetriever:
    """Hybrid retrieval using Qdrant sparse + dense vectors."""

    def __init__(self, client: QdrantClient, collection: str, k=10):
        self.client = client
        self.collection = collection
        self.k = k

    def __call__(self, query: str) -> List[str]:
        # Generate dense and sparse vectors
        dense_vector = self._embed_dense(query)
        sparse_vector = self._embed_sparse(query)

        # Hybrid search
        results = self.client.search(
            collection_name=self.collection,
            query_vector=dense_vector,
            query_filter=None,
            sparse_vector=NamedSparseVector(
                name="sparse",
                vector=sparse_vector
            ),
            limit=self.k
        )

        passages = [hit.payload["content"] for hit in results]
        return passages

    def _embed_dense(self, text: str):
        """Dense embedding (e.g., sentence-transformers)."""
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(text).tolist()

    def _embed_sparse(self, text: str) -> SparseVector:
        """Sparse embedding (e.g., BM25-style)."""
        # Use SPLADE or similar sparse encoder
        # Simplified example: TF-IDF style
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(max_features=1000)
        # Fit on corpus (do this once, not per query)
        sparse_vec = vectorizer.transform([text])

        indices = sparse_vec.indices.tolist()
        values = sparse_vec.data.tolist()

        return SparseVector(indices=indices, values=values)
```

**When to use**:
- Need fine-grained control over sparse/dense balance
- Working with Qdrant v1.7+ infrastructure
- Want to use SPLADE or custom sparse encoders

### Pattern 5: Weighted Fusion with Score Normalization

```python
import dspy
import numpy as np
from typing import List, Tuple

class WeightedHybridRetriever(dspy.Module):
    """Hybrid retrieval with weighted score fusion."""

    def __init__(self, k=10, alpha=0.6):
        super().__init__()
        self.k = k
        self.alpha = alpha  # Weight for vector scores

        self.vector_retrieve = dspy.Retrieve(k=k)
        self.bm25_retrieve = BM25Retriever(k=k)

    def normalize_scores(self, scores: List[float]) -> List[float]:
        """Min-max normalization to [0, 1]."""
        scores = np.array(scores)
        min_score = scores.min()
        max_score = scores.max()

        if max_score == min_score:
            return [1.0] * len(scores)

        return ((scores - min_score) / (max_score - min_score)).tolist()

    def forward(self, question: str):
        # Get results with scores
        vector_results = self.vector_retrieve(question)
        bm25_results = self.bm25_retrieve.search_with_scores(question)

        # Normalize scores separately
        vector_scores = self.normalize_scores([r.score for r in vector_results])
        bm25_scores = self.normalize_scores([r.score for r in bm25_results])

        # Create combined score dict
        combined = {}

        for doc, score in zip(vector_results.passages, vector_scores):
            combined[doc] = self.alpha * score

        for doc, score in zip(bm25_results.passages, bm25_scores):
            if doc in combined:
                combined[doc] += (1 - self.alpha) * score
            else:
                combined[doc] = (1 - self.alpha) * score

        # Sort and return top-k
        ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        passages = [doc for doc, _ in ranked[:self.k]]

        return dspy.Prediction(passages=passages)
```

**When to use**:
- Need to tune vector vs sparse balance (alpha parameter)
- Have evaluation set to optimize weights
- Want interpretable score contributions

### Pattern 6: Arize Phoenix Retrieval Observability

```python
import dspy
from phoenix.trace import dsl as trace_dsl
from phoenix.evals import RetrievalEvaluator

class ObservableHybridRAG(dspy.Module):
    """Hybrid RAG with Phoenix observability."""

    def __init__(self, k=10):
        super().__init__()
        self.retrieve = RRFHybridRetriever(k=k)
        self.generate = dspy.ChainOfThought("context, question -> answer")

        # Initialize Phoenix evaluator
        self.evaluator = RetrievalEvaluator()

    def forward(self, question: str):
        # Trace retrieval
        with trace_dsl.span("hybrid_retrieval"):
            retrieval = self.retrieve(question)

            # Log retrieval metrics
            trace_dsl.log_attribute("num_passages", len(retrieval.passages))
            trace_dsl.log_attribute("fusion_method", "RRF")

        context = "\n\n".join(retrieval.passages)

        # Trace generation
        with trace_dsl.span("generation"):
            result = self.generate(context=context, question=question)

        # Attach retrieved passages for evaluation
        result.retrieved_passages = retrieval.passages

        return result


# Evaluate retrieval quality
def evaluate_hybrid_retrieval(rag_system, test_set):
    """Evaluate hybrid RAG with Phoenix metrics."""
    from phoenix.evals import RetrievalEvaluator, HitRate, MRR, NDCG

    evaluator = RetrievalEvaluator(
        metrics=[
            HitRate(k=5),      # Hit rate @ 5
            MRR(),             # Mean Reciprocal Rank
            NDCG(k=10)         # Normalized Discounted Cumulative Gain
        ]
    )

    results = []
    for example in test_set:
        prediction = rag_system(question=example.question)

        # Evaluate retrieval
        metrics = evaluator.evaluate(
            retrieved_docs=prediction.retrieved_passages,
            relevant_docs=example.relevant_docs,
            query=example.question
        )

        results.append(metrics)

    # Aggregate metrics
    avg_hit_rate = np.mean([r["hit_rate@5"] for r in results])
    avg_mrr = np.mean([r["mrr"] for r in results])
    avg_ndcg = np.mean([r["ndcg@10"] for r in results])

    print(f"Hit Rate@5: {avg_hit_rate:.3f}")
    print(f"MRR: {avg_mrr:.3f}")
    print(f"NDCG@10: {avg_ndcg:.3f}")

    return results
```

**Metrics explained**:
- **Hit Rate@k**: % of queries with at least one relevant doc in top-k
- **MRR**: Mean Reciprocal Rank (1/rank of first relevant doc)
- **NDCG@k**: Normalized Discounted Cumulative Gain (graded relevance)

---

## Quick Reference

### RRF Formula
```python
def rrf_score(rank, k=60):
    return 1.0 / (k + rank)
```

### Hybrid Retrieval Decision Tree
```
Query has rare entities/codes? → Increase BM25 weight (alpha < 0.5)
Query is semantic/paraphrased? → Increase vector weight (alpha > 0.7)
Balanced query? → Use RRF or alpha = 0.5
```

### Platform Selection
```
Elasticsearch: Best for large-scale production (>10M docs)
Weaviate: Best for managed hybrid + GraphQL
Qdrant: Best for custom sparse encoders (SPLADE)
ChromaDB: Use manual RRF (no native hybrid)
```

### Evaluation Metrics Priority
```
1. NDCG@10 (overall quality)
2. MRR (first relevant result)
3. Hit Rate@5 (basic coverage)
```

---

## Anti-Patterns

❌ **Using only vector search for technical queries**:
```python
# Bad - misses exact product codes
retrieve = dspy.Retrieve(k=5)  # Vector only
result = retrieve("Find part number ABC-12345")
```
✅ Use hybrid:
```python
# Good - combines semantic + exact match
retrieve = RRFHybridRetriever(k=5)
result = retrieve("Find part number ABC-12345")
```

❌ **Ignoring score normalization with weighted fusion**:
```python
# Bad - raw scores have different scales
combined_score = vector_score + bm25_score  # Invalid!
```
✅ Normalize first:
```python
# Good - normalize then combine
norm_vector = normalize(vector_score)
norm_bm25 = normalize(bm25_score)
combined_score = 0.6 * norm_vector + 0.4 * norm_bm25
```

❌ **Not tuning alpha parameter**:
```python
# Bad - using default without evaluation
retriever = WeaviateHybridRetriever(alpha=0.5)  # Is 0.5 optimal?
```
✅ Evaluate and tune:
```python
# Good - grid search for optimal alpha
for alpha in [0.3, 0.5, 0.7, 0.9]:
    retriever = WeaviateHybridRetriever(alpha=alpha)
    score = evaluate(retriever, test_set)
    # Choose best alpha
```

❌ **Skipping BM25 for specialized domains**:
```python
# Bad - vector search alone for medical/legal/technical
retrieve = dspy.Retrieve(k=5)  # Misses terminology
```
✅ Use hybrid for domain-specific:
```python
# Good - hybrid catches exact medical terms
retrieve = RRFHybridRetriever(k=5)
```

---

## Related Skills

- `dspy-rag.md` - Basic RAG patterns and vector retrieval
- `rag-reranking-techniques.md` - Multi-stage retrieval with reranking
- `graph-rag.md` - Graph-based retrieval for multihop reasoning
- `hierarchical-rag.md` - Multi-level document structures
- `database/postgres-query-optimization.md` - Metadata filtering
- `database/redis-basics.md` - Caching retrieval results

---

## Summary

Hybrid search combines the strengths of vector (semantic) and BM25 (lexical) retrieval:
- **RRF fusion**: Simple, effective, parameter-free (recommended default)
- **Weighted fusion**: Tunable balance, requires score normalization
- **Platform support**: Elasticsearch, Weaviate, Qdrant have native hybrid search
- **Evaluation**: Use NDCG@k, MRR, Hit Rate@k with Arize Phoenix
- **Best practice**: Start with RRF, tune alpha if needed, always measure retrieval quality

Hybrid search typically achieves 15-30% improvement over single-method retrieval in production RAG systems (2024-2025 benchmarks).

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
