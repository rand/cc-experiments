---
name: rag-reranking-techniques
description: Multi-stage retrieval pipelines with cross-encoder and LLM-based reranking for improved RAG precision
---

# RAG Reranking Techniques

**Scope**: Multi-stage retrieval, cross-encoders, tensor reranking, LLM-as-reranker, evaluation metrics
**Lines**: ~450
**Last Updated**: 2025-10-26

## When to Use This Skill

Activate this skill when:
- Initial retrieval returns too many irrelevant passages (low precision)
- Need to improve top-3 or top-5 accuracy (where most users read)
- Working with large knowledge bases (>100K documents)
- First-stage retrieval is fast but noisy (bi-encoder limitations)
- Implementing production RAG requiring >85% precision@5
- Using cross-encoder models (Cohere, BGE, ms-marco rerankers)
- Leveraging LLMs for contextual reranking (Claude, GPT-4)
- Measuring reranking impact with nDCG, MAP, MRR metrics
- Integrating Arize Phoenix for reranking observability

## Core Concepts

### Multi-Stage Retrieval Architecture

**Stage 1: Fast Retrieval** (bi-encoder, vector search)
- Retrieve top-K candidates (K = 20-100)
- Fast: ~10-50ms for millions of docs
- Trade-off: Lower precision, higher recall

**Stage 2: Reranking** (cross-encoder or LLM)
- Rerank top-K to select best-N (N = 3-10)
- Slower: ~100-500ms per query
- Trade-off: Higher precision, lower throughput

**Stage 3: Generation** (LLM with reranked context)
- Generate answer from top-N passages
- Quality: Better context → better answers

**Why multi-stage**:
- Bi-encoders: Encode query and document separately (fast, but misses interaction)
- Cross-encoders: Encode query+document together (slow, but captures interaction)
- Two-stage: Fast retrieval + slow reranking = best of both worlds

### Reranking Methods (2024-2025)

**1. Cross-Encoder Reranking** (traditional, 2020-2024)
- Models: `ms-marco-MiniLM`, `cross-encoder/ms-marco-electra-base`
- Score: Direct relevance score for (query, passage) pair
- Speed: 50-200ms per passage

**2. Tensor-Based Reranking** (emerging, 2024-2025)
- Models: ColBERT, ColBERTv2, Token-level reranking
- Score: Late interaction (query token × doc token similarity)
- Speed: 20-100ms per passage
- Trend: Gaining adoption for cost/quality balance

**3. LLM-as-Reranker** (state-of-art, 2024-2025)
- Models: GPT-4, Claude Sonnet/Opus, fine-tuned LLMs
- Score: Contextual relevance judgment
- Speed: 200-1000ms per batch
- Trend: Best quality, highest cost

**4. Lightweight Rerankers** (efficiency-focused, 2024)
- Models: BGE-reranker-base, mxbai-rerank-xsmall
- Score: Optimized cross-encoder variants
- Speed: 10-50ms per passage
- Trend: Edge deployment, mobile RAG

### Improvement Studies (2024-2025 Benchmarks)

**nDCG@10 improvements** (BEIR benchmark):
- Bi-encoder only: 0.52 nDCG
- Bi-encoder + cross-encoder: 0.62 nDCG (+19%)
- Bi-encoder + LLM reranker: 0.67 nDCG (+29%)

**Top-5 precision improvements** (MS MARCO):
- Retrieval only: 72% P@5
- + Cross-encoder: 84% P@5 (+17%)
- + GPT-4 reranker: 89% P@5 (+24%)

**Typical gains**: 15-30% improvement in top-k metrics

### Evaluation Metrics

**nDCG@k** (Normalized Discounted Cumulative Gain):
```
DCG@k = Σ (rel_i / log2(i+1))  # i from 1 to k
nDCG@k = DCG@k / ideal_DCG@k
```
- Measures: Graded relevance + position
- Range: 0-1 (higher is better)
- Use: Main metric for ranking quality

**MAP** (Mean Average Precision):
```
AP = (1/num_relevant) * Σ (P@k * rel(k))
MAP = mean(AP across queries)
```
- Measures: Precision across all positions
- Range: 0-1 (higher is better)
- Use: Overall retrieval quality

**MRR** (Mean Reciprocal Rank):
```
RR = 1 / rank_of_first_relevant
MRR = mean(RR across queries)
```
- Measures: Position of first relevant result
- Range: 0-1 (higher is better)
- Use: First-result quality (e.g., search)

---

## Implementation Patterns

### Pattern 1: Cross-Encoder Reranking with DSPy

```python
import dspy
from sentence_transformers import CrossEncoder

class CrossEncoderReranker(dspy.Module):
    """Two-stage retrieval with cross-encoder reranking."""

    def __init__(self, retrieve_k=20, rerank_k=5, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        super().__init__()
        self.retrieve_k = retrieve_k
        self.rerank_k = rerank_k

        # Stage 1: Fast bi-encoder retrieval
        self.retrieve = dspy.Retrieve(k=retrieve_k)

        # Stage 2: Cross-encoder reranker
        self.cross_encoder = CrossEncoder(model_name)

    def forward(self, question: str):
        # Stage 1: Retrieve candidates
        retrieval = self.retrieve(question)
        candidates = retrieval.passages

        if len(candidates) == 0:
            return dspy.Prediction(passages=[])

        # Stage 2: Rerank with cross-encoder
        pairs = [(question, passage) for passage in candidates]
        scores = self.cross_encoder.predict(pairs)

        # Sort by score and take top-k
        ranked_pairs = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True
        )

        reranked_passages = [passage for passage, _ in ranked_pairs[:self.rerank_k]]
        reranked_scores = [score for _, score in ranked_pairs[:self.rerank_k]]

        return dspy.Prediction(
            passages=reranked_passages,
            scores=reranked_scores
        )


class RerankedRAG(dspy.Module):
    """RAG with cross-encoder reranking."""

    def __init__(self):
        super().__init__()
        self.retrieve = CrossEncoderReranker(retrieve_k=20, rerank_k=5)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question: str):
        retrieval = self.retrieve(question)
        context = "\n\n".join(retrieval.passages)
        return self.generate(context=context, question=question)


# Use reranked RAG
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

rag = RerankedRAG()
result = rag(question="What is DSPy?")
print(result.answer)
```

**When to use**:
- Need 15-20% improvement in top-5 accuracy
- Can afford 100-300ms additional latency
- Working with MS MARCO-trained models

### Pattern 2: ColBERT-style Tensor Reranking

```python
import dspy
from colbert.modeling.checkpoint import Checkpoint
from colbert.infra import ColBERTConfig

class ColBERTReranker(dspy.Module):
    """Tensor-based late interaction reranking."""

    def __init__(self, retrieve_k=30, rerank_k=5, checkpoint="colbertv2.0"):
        super().__init__()
        self.retrieve_k = retrieve_k
        self.rerank_k = rerank_k

        # Stage 1: Fast retrieval
        self.retrieve = dspy.Retrieve(k=retrieve_k)

        # Stage 2: ColBERT reranker
        config = ColBERTConfig(checkpoint=checkpoint)
        self.colbert = Checkpoint(checkpoint, colbert_config=config)

    def forward(self, question: str):
        # Stage 1: Retrieve candidates
        candidates = self.retrieve(question).passages

        if len(candidates) == 0:
            return dspy.Prediction(passages=[])

        # Stage 2: Token-level reranking
        query_embedding = self.colbert.queryFromText([question])[0]

        scores = []
        for passage in candidates:
            doc_embedding = self.colbert.docFromText([passage])[0]

            # Late interaction: max-sim aggregation
            similarity = self._maxsim(query_embedding, doc_embedding)
            scores.append(similarity)

        # Sort and select top-k
        ranked = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True
        )

        reranked_passages = [p for p, _ in ranked[:self.rerank_k]]

        return dspy.Prediction(passages=reranked_passages)

    def _maxsim(self, query_emb, doc_emb):
        """MaxSim operation for late interaction."""
        import torch

        # For each query token, find max similarity with doc tokens
        similarity_matrix = torch.matmul(query_emb, doc_emb.T)
        max_sims = similarity_matrix.max(dim=1).values

        # Sum max similarities
        return max_sims.sum().item()
```

**When to use** (2024-2025 trend):
- Need better quality than cross-encoders
- Want faster inference than full cross-encoders
- Have GPU available for reranking
- Working with token-level relevance signals

### Pattern 3: LLM-as-Reranker (GPT-4/Claude)

```python
import dspy

class LLMReranker(dspy.Module):
    """LLM-based contextual reranking."""

    def __init__(self, retrieve_k=20, rerank_k=5):
        super().__init__()
        self.retrieve_k = retrieve_k
        self.rerank_k = rerank_k

        # Stage 1: Fast retrieval
        self.retrieve = dspy.Retrieve(k=retrieve_k)

        # Stage 2: LLM reranker
        self.rerank = dspy.ChainOfThought(
            "question, passages -> ranked_indices: list[int], reasoning"
        )

    def forward(self, question: str):
        # Stage 1: Retrieve candidates
        candidates = self.retrieve(question).passages

        if len(candidates) == 0:
            return dspy.Prediction(passages=[])

        # Format passages for LLM
        passages_text = "\n\n".join([
            f"[{i}] {passage}"
            for i, passage in enumerate(candidates)
        ])

        # Stage 2: LLM reranking
        rerank_result = self.rerank(
            question=question,
            passages=passages_text
        )

        # Extract top indices
        try:
            top_indices = rerank_result.ranked_indices[:self.rerank_k]
            reranked_passages = [candidates[i] for i in top_indices]
        except:
            # Fallback: use first k passages
            reranked_passages = candidates[:self.rerank_k]

        return dspy.Prediction(
            passages=reranked_passages,
            reasoning=rerank_result.reasoning
        )


class LLMRerankedRAG(dspy.Module):
    """RAG with LLM-based reranking."""

    def __init__(self):
        super().__init__()
        self.retrieve = LLMReranker(retrieve_k=15, rerank_k=5)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question: str):
        retrieval = self.retrieve(question)
        context = "\n\n".join(retrieval.passages)

        result = self.generate(context=context, question=question)
        result.rerank_reasoning = retrieval.reasoning

        return result
```

**When to use** (2024-2025 state-of-art):
- Need highest quality reranking (best top-5 precision)
- Can afford higher cost and latency
- Want explainable reranking decisions
- Working with complex queries requiring contextual judgment

### Pattern 4: Cohere Reranker API

```python
import dspy
import cohere

class CohereReranker(dspy.Module):
    """Production reranking with Cohere API."""

    def __init__(self, api_key: str, retrieve_k=30, rerank_k=5, model="rerank-english-v2.0"):
        super().__init__()
        self.retrieve_k = retrieve_k
        self.rerank_k = rerank_k

        self.retrieve = dspy.Retrieve(k=retrieve_k)
        self.cohere = cohere.Client(api_key)
        self.model = model

    def forward(self, question: str):
        # Stage 1: Retrieve candidates
        candidates = self.retrieve(question).passages

        if len(candidates) == 0:
            return dspy.Prediction(passages=[])

        # Stage 2: Cohere reranking
        rerank_response = self.cohere.rerank(
            query=question,
            documents=candidates,
            top_n=self.rerank_k,
            model=self.model
        )

        # Extract reranked passages
        reranked_passages = [
            result.document['text']
            for result in rerank_response.results
        ]

        reranked_scores = [
            result.relevance_score
            for result in rerank_response.results
        ]

        return dspy.Prediction(
            passages=reranked_passages,
            scores=reranked_scores
        )


# Use with RAG
class CohereRerankedRAG(dspy.Module):
    def __init__(self, cohere_api_key: str):
        super().__init__()
        self.retrieve = CohereReranker(cohere_api_key, retrieve_k=30, rerank_k=5)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question: str):
        retrieval = self.retrieve(question)
        context = "\n\n".join(retrieval.passages)
        return self.generate(context=context, question=question)
```

**When to use**:
- Want production-ready reranking API
- Need multilingual support (Cohere supports 100+ languages)
- Prefer managed service over self-hosted models
- Can afford API costs (~$0.002 per 1K reranks)

### Pattern 5: Arize Phoenix Reranking Observability

```python
import dspy
from phoenix.trace import dsl as trace_dsl
from phoenix.evals import RetrievalEvaluator
import numpy as np

class ObservableReranker(dspy.Module):
    """Reranking with Phoenix observability."""

    def __init__(self, retrieve_k=20, rerank_k=5):
        super().__init__()
        self.retrieve_k = retrieve_k
        self.rerank_k = rerank_k

        self.retrieve = dspy.Retrieve(k=retrieve_k)
        self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def forward(self, question: str):
        # Trace retrieval stage
        with trace_dsl.span("stage1_retrieval"):
            candidates = self.retrieve(question).passages
            trace_dsl.log_attribute("num_candidates", len(candidates))

        # Trace reranking stage
        with trace_dsl.span("stage2_reranking"):
            pairs = [(question, p) for p in candidates]
            scores = self.cross_encoder.predict(pairs)

            ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
            reranked = [p for p, _ in ranked[:self.rerank_k]]

            # Log reranking metrics
            trace_dsl.log_attribute("top_score", float(ranked[0][1]))
            trace_dsl.log_attribute("score_drop", float(ranked[0][1] - ranked[-1][1]))
            trace_dsl.log_attribute("num_reranked", len(reranked))

        return dspy.Prediction(
            passages=reranked,
            before_rerank=candidates,
            after_rerank=reranked
        )


def evaluate_reranking_impact(reranker, test_set):
    """Measure reranking impact with nDCG, MAP, MRR."""
    from sklearn.metrics import ndcg_score

    ndcg_before = []
    ndcg_after = []
    mrr_before = []
    mrr_after = []

    for example in test_set:
        result = reranker(question=example.question)

        # Calculate relevance labels (1 if relevant, 0 otherwise)
        before_relevance = [
            1 if p in example.relevant_docs else 0
            for p in result.before_rerank
        ]
        after_relevance = [
            1 if p in example.relevant_docs else 0
            for p in result.after_rerank
        ]

        # nDCG@k
        if sum(before_relevance) > 0:  # Has relevant docs
            ndcg_b = ndcg_score([before_relevance], [list(range(len(before_relevance), 0, -1))])
            ndcg_a = ndcg_score([after_relevance], [list(range(len(after_relevance), 0, -1))])
            ndcg_before.append(ndcg_b)
            ndcg_after.append(ndcg_a)

        # MRR
        mrr_b = 1.0 / (before_relevance.index(1) + 1) if 1 in before_relevance else 0
        mrr_a = 1.0 / (after_relevance.index(1) + 1) if 1 in after_relevance else 0
        mrr_before.append(mrr_b)
        mrr_after.append(mrr_a)

    print(f"nDCG before: {np.mean(ndcg_before):.3f}")
    print(f"nDCG after:  {np.mean(ndcg_after):.3f}")
    print(f"Improvement: +{(np.mean(ndcg_after) - np.mean(ndcg_before)) / np.mean(ndcg_before) * 100:.1f}%")

    print(f"\nMRR before: {np.mean(mrr_before):.3f}")
    print(f"MRR after:  {np.mean(mrr_after):.3f}")
    print(f"Improvement: +{(np.mean(mrr_after) - np.mean(mrr_before)) / np.mean(mrr_before) * 100:.1f}%")
```

**Metrics to track**:
- nDCG@5, nDCG@10 (overall ranking quality)
- MRR (first relevant result position)
- Precision@5 (top-5 accuracy)
- Latency (retrieval vs reranking time)

---

## Quick Reference

### Reranking Method Selection
```
Need best quality? → LLM reranker (GPT-4, Claude)
Need cost efficiency? → Cross-encoder (ms-marco)
Need speed? → Tensor reranking (ColBERT)
Need production API? → Cohere reranker
```

### Typical k Values
```
retrieve_k: 20-100 (cast wide net)
rerank_k: 3-10 (focus on best)

Common: retrieve_k=30, rerank_k=5
```

### Performance Benchmarks (2024)
```
Cross-encoder: 100-300ms/query, +17% P@5
ColBERT: 50-150ms/query, +20% P@5
LLM reranker: 500-2000ms/query, +24% P@5
Cohere API: 200-400ms/query, +18% P@5
```

### Evaluation Priority
```
1. nDCG@10 (primary metric)
2. MRR (user experience)
3. Precision@5 (practical accuracy)
```

---

## Anti-Patterns

❌ **Reranking without enough candidates**:
```python
# Bad - too few candidates to rerank
retrieve = dspy.Retrieve(k=5)  # Not enough!
reranker = CrossEncoderReranker(retrieve_k=5, rerank_k=3)
```
✅ Retrieve more, rerank to top-k:
```python
# Good - cast wide net, then rerank
reranker = CrossEncoderReranker(retrieve_k=30, rerank_k=5)
```

❌ **Using slow reranker for all passages**:
```python
# Bad - reranking 100 passages with LLM
for passage in all_100_passages:
    score = llm_rerank(query, passage)  # Expensive!
```
✅ Two-stage: fast retrieval, then rerank top-k:
```python
# Good - rerank only top candidates
candidates = fast_retrieve(query, k=30)
reranked = llm_rerank(query, candidates[:10])
```

❌ **Not measuring reranking impact**:
```python
# Bad - deploy reranker without evaluation
reranker = CrossEncoderReranker()
# Hope it works better?
```
✅ Measure before/after:
```python
# Good - evaluate impact
results = evaluate_reranking_impact(reranker, test_set)
# nDCG improved by 18%
```

❌ **Ignoring latency budget**:
```python
# Bad - LLM reranker for real-time app
reranker = LLMReranker(retrieve_k=50, rerank_k=10)  # 2-3 seconds!
```
✅ Match reranker to latency requirements:
```python
# Good - cross-encoder for <500ms latency
reranker = CrossEncoderReranker(retrieve_k=30, rerank_k=5)  # 200ms
```

---

## Related Skills

- `dspy-rag.md` - Basic RAG patterns and vector retrieval
- `hybrid-search-rag.md` - Combining vector and BM25 retrieval
- `graph-rag.md` - Graph-based multihop retrieval
- `hierarchical-rag.md` - Multi-level document structures
- `dspy-evaluation.md` - Evaluating RAG pipelines

---

## Summary

Reranking improves RAG precision by adding a second-stage ranking step:
- **Multi-stage architecture**: Fast retrieval (k=20-100) → Slow reranking (k=3-10)
- **Cross-encoders**: Traditional, effective, moderate cost (ms-marco models)
- **Tensor reranking**: Emerging 2024-2025 trend (ColBERT, token-level)
- **LLM rerankers**: State-of-art quality, highest cost (GPT-4, Claude)
- **Typical gains**: 15-30% improvement in nDCG@10, P@5
- **Evaluation**: Use nDCG, MAP, MRR with Arize Phoenix observability
- **Best practice**: Start with cross-encoder, measure impact, upgrade if needed

Production RAG systems commonly achieve 84-89% Precision@5 with reranking vs 72-78% without.

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
