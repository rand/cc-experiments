---
name: ir-ranking-reranking
description: Learning to rank, cross-encoder reranking, ranking features, and evaluation metrics (nDCG, MAP, MRR)
---

# Information Retrieval: Ranking and Reranking

**Scope**: Learning to rank algorithms, cross-encoder reranking, ranking features, evaluation metrics, and two-stage retrieval
**Lines**: ~320
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Improving search result quality beyond initial retrieval
- Implementing two-stage retrieval (fast retrieve, accurate rerank)
- Training custom ranking models with user feedback
- Using cross-encoders for semantic reranking
- Evaluating ranking quality with nDCG, MAP, or MRR
- Combining multiple relevance signals into final ranking
- Balancing retrieval speed vs ranking accuracy
- Personalizing search results based on user behavior

## Core Concepts

### Concept 1: Learning to Rank (LTR)

**Three Approaches**:

**Pointwise**: Predict relevance score for each document independently
- Treat as regression/classification: predict score for (query, document)
- Simple but ignores relative ordering

**Pairwise**: Learn which document should rank higher
- Classify pairs: is doc A > doc B?
- Examples: RankNet, LambdaRank
- Better than pointwise for ranking tasks

**Listwise**: Optimize entire ranking directly
- Loss function considers full ranked list
- Examples: LambdaMART, ListNet
- Best performance but more complex

```python
from sklearn.ensemble import GradientBoostingRegressor
import numpy as np

# Pointwise LTR (regression)
class PointwiseRanker:
    def __init__(self):
        self.model = GradientBoostingRegressor(n_estimators=100)

    def train(self, features, relevance_scores):
        """
        features: (n_samples, n_features) - query-doc features
        relevance_scores: (n_samples,) - relevance labels (0-4)
        """
        self.model.fit(features, relevance_scores)

    def rank(self, query_features):
        """Predict scores and rank documents"""
        scores = self.model.predict(query_features)
        ranked_indices = np.argsort(scores)[::-1]
        return ranked_indices, scores[ranked_indices]

# Example features: BM25, embeddings similarity, freshness, etc.
features = np.array([
    [0.8, 0.6, 1.0],  # doc1: high BM25, medium semantic, fresh
    [0.3, 0.9, 0.5],  # doc2: low BM25, high semantic, old
    [0.9, 0.7, 0.8],  # doc3: high BM25, high semantic, recent
])
relevance = np.array([3, 2, 4])  # Ground truth ratings

ranker = PointwiseRanker()
ranker.train(features, relevance)
ranked_indices, scores = ranker.rank(features)
print(f"Ranked order: {ranked_indices}")  # [2, 0, 1]
```

### Concept 2: Cross-Encoder Reranking

**Bi-encoder vs Cross-encoder**:

- **Bi-encoder**: Separate encoders for query and document (fast, scalable)
  - Encode once, search millions of vectors
  - Example: sentence-transformers for vector search

- **Cross-encoder**: Joint encoding of query + document (slow, accurate)
  - Process query and document together
  - Captures interaction between terms
  - 10-100x slower but much better quality

**Two-Stage Retrieval**:
1. **Stage 1**: Bi-encoder retrieves top-k candidates (k=100-1000)
2. **Stage 2**: Cross-encoder reranks top-n (n=10-50)

```python
from sentence_transformers import CrossEncoder

# Load cross-encoder for reranking
cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def two_stage_retrieval(query, documents, bi_encoder, cross_encoder, top_k=100, rerank_top=10):
    """
    Stage 1: Fast bi-encoder retrieval
    Stage 2: Accurate cross-encoder reranking
    """
    # Stage 1: Retrieve top_k with bi-encoder
    query_emb = bi_encoder.encode(query, convert_to_tensor=True)
    doc_embs = bi_encoder.encode(documents, convert_to_tensor=True)

    from sentence_transformers import util
    scores = util.cos_sim(query_emb, doc_embs)[0]
    top_indices = scores.argsort(descending=True)[:top_k]

    # Stage 2: Rerank top_k with cross-encoder
    candidates = [documents[i] for i in top_indices]
    pairs = [[query, doc] for doc in candidates]

    cross_scores = cross_encoder.predict(pairs)
    rerank_indices = np.argsort(cross_scores)[::-1][:rerank_top]

    # Map back to original indices
    final_indices = [top_indices[i] for i in rerank_indices]
    final_scores = [cross_scores[i] for i in rerank_indices]

    return final_indices, final_scores

# Example
from sentence_transformers import SentenceTransformer

bi_encoder = SentenceTransformer('all-MiniLM-L6-v2')
query = "machine learning classification algorithms"
documents = [...]  # Large corpus

top_docs, scores = two_stage_retrieval(query, documents, bi_encoder, cross_encoder)
```

### Concept 3: Ranking Features

**Categories**:

**Query-Document Features**:
- TF-IDF/BM25 score
- Vector similarity (cosine, dot product)
- Exact match signals (title, URL)
- Proximity (terms close in document)

**Document Features**:
- PageRank, authority score
- Freshness (recency)
- Length (too short/long)
- Click-through rate (CTR)
- Engagement metrics (time on page, bounce rate)

**Query Features**:
- Query length
- Query type (navigational, informational)
- User history, personalization

```python
def extract_features(query, document, metadata):
    """Extract features for ranking"""
    features = {}

    # Lexical features
    features['bm25_score'] = compute_bm25(query, document)
    features['exact_match_title'] = int(query.lower() in document['title'].lower())
    features['term_overlap'] = compute_term_overlap(query, document['content'])

    # Semantic features
    query_emb = model.encode(query)
    doc_emb = model.encode(document['content'])
    features['semantic_similarity'] = cosine_similarity(query_emb, doc_emb)

    # Document quality features
    features['page_rank'] = metadata.get('page_rank', 0)
    features['freshness_days'] = (today - metadata['publish_date']).days
    features['avg_time_on_page'] = metadata.get('avg_time_on_page', 0)
    features['ctr'] = metadata.get('ctr', 0)

    # Document length
    features['doc_length'] = len(document['content'].split())
    features['title_length'] = len(document['title'].split())

    # User personalization (if available)
    features['user_clicked_similar'] = check_user_history(query, document)

    return list(features.values())
```

### Concept 4: Evaluation Metrics

**nDCG (Normalized Discounted Cumulative Gain)**:
- Considers both relevance and position
- Discounts lower positions (log discount)
- Range: 0 to 1 (1 = perfect ranking)

**MAP (Mean Average Precision)**:
- Average precision across queries
- Emphasizes precision at each relevant item
- Binary relevance (relevant vs not)

**MRR (Mean Reciprocal Rank)**:
- Inverse rank of first relevant result
- Good for "find one answer" tasks
- Range: 0 to 1

```python
import numpy as np

def dcg_at_k(relevance_scores, k):
    """Discounted Cumulative Gain at rank k"""
    relevance = np.array(relevance_scores)[:k]
    gains = 2**relevance - 1
    discounts = np.log2(np.arange(2, k + 2))
    return np.sum(gains / discounts)

def ndcg_at_k(predicted_order, ground_truth_scores, k):
    """Normalized DCG at rank k"""
    # DCG for predicted ranking
    predicted_relevance = [ground_truth_scores[i] for i in predicted_order[:k]]
    dcg = dcg_at_k(predicted_relevance, k)

    # IDCG (ideal ranking)
    ideal_relevance = sorted(ground_truth_scores, reverse=True)
    idcg = dcg_at_k(ideal_relevance, k)

    return dcg / idcg if idcg > 0 else 0.0

def mean_average_precision(predicted_orders, ground_truth_binary):
    """MAP across queries (binary relevance)"""
    aps = []
    for predicted, relevant_indices in zip(predicted_orders, ground_truth_binary):
        precisions = []
        num_relevant = 0

        for k, doc_id in enumerate(predicted, 1):
            if doc_id in relevant_indices:
                num_relevant += 1
                precisions.append(num_relevant / k)

        ap = np.mean(precisions) if precisions else 0.0
        aps.append(ap)

    return np.mean(aps)

def mean_reciprocal_rank(predicted_orders, ground_truth_binary):
    """MRR across queries"""
    rrs = []
    for predicted, relevant_indices in zip(predicted_orders, ground_truth_binary):
        for rank, doc_id in enumerate(predicted, 1):
            if doc_id in relevant_indices:
                rrs.append(1.0 / rank)
                break
        else:
            rrs.append(0.0)

    return np.mean(rrs)

# Example evaluation
predicted_order = [2, 0, 3, 1]  # doc IDs
ground_truth_scores = [3, 1, 4, 2]  # relevance scores (0-4)

ndcg = ndcg_at_k(predicted_order, ground_truth_scores, k=10)
print(f"nDCG@10: {ndcg:.4f}")
```

---

## Patterns

### Pattern 1: Hybrid Ranking (Combine Multiple Signals)

**When to use**: Multiple relevance signals available (BM25, semantic, popularity)

```python
def hybrid_rank(query, documents, weights={'lexical': 0.3, 'semantic': 0.5, 'popularity': 0.2}):
    """Combine multiple ranking signals"""
    scores = np.zeros(len(documents))

    # Lexical score (BM25)
    bm25_scores = np.array([compute_bm25(query, doc) for doc in documents])
    bm25_normalized = bm25_scores / bm25_scores.max() if bm25_scores.max() > 0 else bm25_scores

    # Semantic score (embeddings)
    query_emb = model.encode(query)
    doc_embs = model.encode([doc['content'] for doc in documents])
    semantic_scores = [cosine_similarity(query_emb, doc_emb) for doc_emb in doc_embs]
    semantic_normalized = np.array(semantic_scores)

    # Popularity score
    popularity_scores = np.array([doc.get('popularity', 0) for doc in documents])
    popularity_normalized = popularity_scores / popularity_scores.max() if popularity_scores.max() > 0 else popularity_scores

    # Weighted combination
    scores = (
        weights['lexical'] * bm25_normalized +
        weights['semantic'] * semantic_normalized +
        weights['popularity'] * popularity_normalized
    )

    ranked_indices = np.argsort(scores)[::-1]
    return ranked_indices, scores[ranked_indices]
```

### Pattern 2: LambdaMART Training with LightGBM

**Use case**: Train listwise ranking model with user feedback data

```python
import lightgbm as lgb

# Prepare data in LightGBM ranking format
# features: (n_samples, n_features)
# labels: relevance scores (0-4)
# qids: query IDs (group by query)

train_data = lgb.Dataset(
    features,
    label=labels,
    group=query_groups  # Number of docs per query
)

params = {
    'objective': 'lambdarank',
    'metric': 'ndcg',
    'ndcg_eval_at': [1, 3, 5, 10],
    'learning_rate': 0.1,
    'num_leaves': 31,
    'min_data_in_leaf': 50
}

ranker = lgb.train(
    params,
    train_data,
    num_boost_round=100,
    valid_sets=[valid_data],
    callbacks=[lgb.early_stopping(10)]
)

# Predict and rank
predictions = ranker.predict(test_features)
ranked_indices = np.argsort(predictions)[::-1]
```

### Pattern 3: Personalized Ranking

**When to use**: User history available for personalization

```python
def personalized_rank(query, documents, user_profile, base_scores):
    """Adjust ranking based on user preferences"""
    personalized_scores = base_scores.copy()

    for i, doc in enumerate(documents):
        # Boost based on user's preferred categories
        if doc['category'] in user_profile.get('preferred_categories', []):
            personalized_scores[i] *= 1.2

        # Boost based on user's interaction history
        if doc['id'] in user_profile.get('clicked_docs', []):
            personalized_scores[i] *= 1.3

        # Boost based on similar documents user engaged with
        similarity = compute_user_doc_similarity(user_profile, doc)
        personalized_scores[i] *= (1 + similarity * 0.5)

        # Penalize recently viewed
        if doc['id'] in user_profile.get('recent_views', []):
            personalized_scores[i] *= 0.8

    ranked_indices = np.argsort(personalized_scores)[::-1]
    return ranked_indices, personalized_scores[ranked_indices]
```

### Pattern 4: Diversity-Aware Ranking

**Use case**: Avoid redundant results, show diverse perspectives

```python
def diverse_rerank(candidates, scores, diversity_penalty=0.3):
    """Rerank to promote diversity (MMR-style)"""
    ranked = []
    remaining = list(range(len(candidates)))
    doc_embeddings = model.encode([c['content'] for c in candidates])

    while remaining and len(ranked) < 10:
        best_idx = None
        best_score = -float('inf')

        for i in remaining:
            # Original relevance score
            relevance = scores[i]

            # Diversity penalty: similarity to already ranked docs
            if ranked:
                ranked_embeddings = doc_embeddings[ranked]
                similarities = [cosine_similarity(doc_embeddings[i], emb) for emb in ranked_embeddings]
                diversity_penalty_value = max(similarities)
            else:
                diversity_penalty_value = 0

            # MMR score: balance relevance and diversity
            mmr_score = relevance - diversity_penalty * diversity_penalty_value

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i

        ranked.append(best_idx)
        remaining.remove(best_idx)

    return ranked
```

### Pattern 5: A/B Testing Ranking Models

**When to use**: Validate ranking improvements with real users

```python
import random

def ab_test_ranker(query, documents, ranker_a, ranker_b, user_id):
    """Route user to control or test ranker"""
    # Assign user to variant (deterministic based on user_id)
    variant = 'b' if hash(user_id) % 2 == 0 else 'a'

    if variant == 'a':
        results = ranker_a.rank(query, documents)
        variant_label = 'control'
    else:
        results = ranker_b.rank(query, documents)
        variant_label = 'test'

    # Log for analysis
    log_experiment(
        user_id=user_id,
        query=query,
        variant=variant_label,
        results=results
    )

    return results

# Analyze A/B test results
def analyze_ab_test(logs):
    """Compare metrics between variants"""
    control_ndcg = []
    test_ndcg = []

    for log in logs:
        if log['variant'] == 'control':
            control_ndcg.append(log['ndcg'])
        else:
            test_ndcg.append(log['ndcg'])

    print(f"Control nDCG: {np.mean(control_ndcg):.4f}")
    print(f"Test nDCG: {np.mean(test_ndcg):.4f}")
    print(f"Lift: {(np.mean(test_ndcg) / np.mean(control_ndcg) - 1) * 100:.2f}%")
```

### Pattern 6: Real-Time Ranking with Caching

**When to use**: Reduce latency for repeated queries

```python
from functools import lru_cache
import hashlib

class CachedRanker:
    def __init__(self, ranker, cache_size=1000):
        self.ranker = ranker
        self.cache = {}
        self.cache_size = cache_size

    def _cache_key(self, query, doc_ids):
        """Generate cache key from query and document set"""
        key_str = f"{query}:{sorted(doc_ids)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def rank(self, query, documents):
        """Rank with caching"""
        doc_ids = tuple(doc['id'] for doc in documents)
        cache_key = self._cache_key(query, doc_ids)

        if cache_key in self.cache:
            return self.cache[cache_key]

        # Compute ranking
        results = self.ranker.rank(query, documents)

        # Cache results (LRU eviction if needed)
        if len(self.cache) >= self.cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[cache_key] = results
        return results
```

---

## Quick Reference

### Ranking Approaches

```
Approach      | Training Data              | Complexity | Quality
--------------|----------------------------|------------|--------
Pointwise     | (query, doc) → score       | Low        | Good
Pairwise      | (query, docA, docB) → A>B  | Medium     | Better
Listwise      | (query, docs) → ranking    | High       | Best
Cross-encoder | (query, doc) → score       | Very High  | Excellent
```

### Evaluation Metrics

```
Metric   | Formula                          | Use Case
---------|----------------------------------|----------
nDCG@k   | DCG / IDCG (log discount)        | Graded relevance, position matters
MAP      | Mean of Precision@k              | Binary relevance, all relevant items
MRR      | 1 / rank of first relevant       | Single answer tasks
P@k      | Relevant in top k / k            | Binary relevance, top-k quality
```

### Key Guidelines

```
✅ DO: Use two-stage retrieval (fast retrieve, accurate rerank)
✅ DO: Combine multiple signals (lexical, semantic, popularity)
✅ DO: Evaluate with nDCG for graded relevance
✅ DO: A/B test ranking changes with real users
✅ DO: Cache ranking results for popular queries
✅ DO: Promote diversity to avoid redundant results

❌ DON'T: Use cross-encoder for initial retrieval (too slow)
❌ DON'T: Ignore position in ranking evaluation
❌ DON'T: Deploy ranking changes without A/B testing
❌ DON'T: Use only lexical or only semantic (hybrid is better)
❌ DON'T: Forget to normalize scores before combining
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Use cross-encoder for full corpus search
for doc in million_documents:
    score = cross_encoder.predict([[query, doc['content']]])
    # This takes hours!

# ✅ CORRECT: Two-stage retrieval
# Stage 1: Retrieve top 100 with bi-encoder (fast)
candidates = bi_encoder_retrieve(query, million_documents, top_k=100)

# Stage 2: Rerank with cross-encoder (accurate)
reranked = cross_encoder_rerank(query, candidates, top_k=10)
```

❌ **Cross-encoder on full corpus**: Hours of compute, unacceptable latency
✅ **Correct approach**: Fast retrieval, then accurate reranking

### Common Mistakes

```python
# ❌ Don't: Combine scores without normalization
combined_score = bm25_score + semantic_score + popularity_score
# Problem: Scales differ (BM25: 0-100, semantic: 0-1, popularity: 0-1M)

# ✅ Correct: Normalize before combining
bm25_norm = bm25_score / max_bm25
semantic_norm = semantic_score  # Already 0-1
popularity_norm = popularity_score / max_popularity

combined_score = 0.4 * bm25_norm + 0.4 * semantic_norm + 0.2 * popularity_norm
```

❌ **Unnormalized score combination**: Dominant signal overwhelms others
✅ **Better**: Normalize to same range, then weighted combination

```python
# ❌ Don't: Ignore query groups in LTR training
ranker.fit(features, labels)  # Treats as independent samples

# ✅ Correct: Specify query groups
ranker.fit(features, labels, group=query_groups)
# Ensures ranking loss considers docs within same query
```

❌ **Missing query groups**: Model learns wrong objective
✅ **Better**: Always specify query groupings in LTR

```python
# ❌ Don't: Use only top-1 accuracy
accuracy = int(predicted_order[0] == best_doc_id)

# ✅ Correct: Use ranking metrics
ndcg = ndcg_at_k(predicted_order, ground_truth_scores, k=10)
map_score = mean_average_precision([predicted_order], [relevant_docs])
```

❌ **Top-1 only**: Ignores quality of full ranking
✅ **Better**: Use nDCG, MAP, or MRR for ranking evaluation

---

## Related Skills

- `ir-search-fundamentals.md` - BM25 and lexical features for ranking
- `ir-vector-search.md` - Bi-encoders for initial retrieval stage
- `ir-query-understanding.md` - Query expansion before ranking
- `ir-recommendation-systems.md` - Similar ranking techniques for recommendations
- `test-unit-testing.md` - Testing ranking models and metrics

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
