---
name: dspy-rag
description: Building Retrieval-Augmented Generation pipelines with DSPy and vector databases
---

# DSPy RAG

**Scope**: RAG patterns, retrieval modules, vector databases, context optimization
**Lines**: ~420
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Building RAG (Retrieval-Augmented Generation) systems with DSPy
- Integrating vector databases (ChromaDB, Weaviate, Qdrant) with DSPy
- Optimizing retrieval quality and context selection
- Implementing multi-hop reasoning over documents
- Creating question-answering systems over custom knowledge bases
- Reducing hallucinations with grounded generation

## Core Concepts

### What is RAG?

**Retrieval-Augmented Generation**: Combine retrieval + generation
1. **Retrieve**: Find relevant documents from knowledge base
2. **Augment**: Add retrieved context to prompt
3. **Generate**: LM produces answer based on context

**Benefits**:
- Reduce hallucinations (grounded in facts)
- Access up-to-date information
- Domain-specific knowledge
- Transparent (can cite sources)

### DSPy RAG Components

**dspy.Retrieve**: Built-in retrieval module
- Queries vector database or search API
- Returns top-k relevant passages
- Integrates with ChromaDB, Weaviate, Qdrant, etc.

**Custom RAG modules**: Combine retrieval + generation
- Control retrieval strategy
- Format context
- Cite sources
- Handle multi-hop reasoning

### Vector Database Integration

**Supported**:
- ChromaDB (local, simple)
- Weaviate (production, scalable)
- Qdrant (high performance)
- Pinecone (managed cloud)
- Custom retrievers (API-based)

---

## Patterns

### Pattern 1: Simple RAG with ChromaDB

```python
import dspy
import chromadb

# Set up ChromaDB
chroma_client = chromadb.Client()
collection = chroma_client.create_collection("knowledge_base")

# Add documents
documents = [
    "DSPy is a framework for programming language models.",
    "Paris is the capital of France.",
    "Python is a popular programming language.",
]

collection.add(
    documents=documents,
    ids=[str(i) for i in range(len(documents))],
)

# Configure DSPy with retriever
retriever = dspy.Retrieve(k=3)
rm = dspy.chromadb_rm.ChromadbRM(
    collection_name="knowledge_base",
    persist_directory="./chroma_db"
)
dspy.settings.configure(rm=rm)

# Simple RAG module
class SimpleRAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        # Retrieve relevant passages
        context = self.retrieve(question).passages

        # Generate answer
        return self.generate(context=context, question=question)

# Use RAG
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

rag = SimpleRAG()
result = rag(question="What is DSPy?")
print(result.answer)
```

**When to use**:
- Small knowledge bases (<10K documents)
- Local development
- Quick prototyping

### Pattern 2: RAG with Citations

```python
import dspy

class CitedRAG(dspy.Module):
    """RAG system that cites sources."""

    def __init__(self, k=5):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=k)

        # Signature includes citations
        self.generate = dspy.ChainOfThought(
            "context, question -> answer, citations: list[int]"
        )

    def forward(self, question):
        # Retrieve passages
        retrieval_result = self.retrieve(question)
        passages = retrieval_result.passages

        # Format context with passage numbers
        context_parts = []
        for i, passage in enumerate(passages):
            context_parts.append(f"[{i+1}] {passage}")

        context = "\n\n".join(context_parts)

        # Generate with citations
        result = self.generate(context=context, question=question)

        # Attach retrieved passages for reference
        result.retrieved_passages = passages

        return result

# Use RAG with citations
rag = CitedRAG(k=5)
result = rag(question="What is DSPy?")

print("Answer:", result.answer)
print("Citations:", result.citations)
print("\nSources:")
for citation_idx in result.citations:
    print(f"[{citation_idx}] {result.retrieved_passages[citation_idx-1][:100]}...")
```

**Benefits**:
- Verifiable answers
- Transparent reasoning
- User can check sources

### Pattern 3: Multi-Hop RAG

```python
import dspy

class MultiHopRAG(dspy.Module):
    """RAG with multiple retrieval rounds for complex questions."""

    def __init__(self, max_hops=2):
        super().__init__()
        self.max_hops = max_hops
        self.retrieve = dspy.Retrieve(k=3)

        # Generate follow-up queries
        self.gen_query = dspy.ChainOfThought(
            "question, context -> needs_more_info: bool, follow_up_query"
        )

        # Final answer generation
        self.generate_answer = dspy.ChainOfThought(
            "question, all_context -> answer"
        )

    def forward(self, question):
        all_passages = []
        current_question = question

        # Multi-hop retrieval
        for hop in range(self.max_hops):
            # Retrieve for current query
            passages = self.retrieve(current_question).passages
            all_passages.extend(passages)

            # Check if we need more information
            context = "\n".join(all_passages)
            query_result = self.gen_query(question=question, context=context)

            if not query_result.needs_more_info:
                break

            # Generate follow-up query
            current_question = query_result.follow_up_query

        # Generate final answer with all context
        all_context = "\n\n".join(all_passages)
        result = self.generate_answer(question=question, all_context=all_context)

        result.num_hops = hop + 1
        result.all_passages = all_passages

        return result

# Use multi-hop RAG
rag = MultiHopRAG(max_hops=3)
result = rag(question="What programming languages are used in DSPy development?")

print(f"Answer: {result.answer}")
print(f"Required {result.num_hops} retrieval hops")
```

**When to use**:
- Complex questions requiring multiple pieces of information
- Questions with implicit dependencies
- Deep knowledge base exploration

### Pattern 4: RAG with Weaviate

```python
import dspy
import weaviate

# Connect to Weaviate
weaviate_client = weaviate.Client("http://localhost:8080")

# Create schema
schema = {
    "class": "Document",
    "properties": [
        {"name": "content", "dataType": ["text"]},
        {"name": "title", "dataType": ["string"]},
    ],
}

weaviate_client.schema.create_class(schema)

# Add documents
documents = [
    {"content": "DSPy is a framework...", "title": "DSPy Overview"},
    # ... more documents
]

for doc in documents:
    weaviate_client.data_object.create(doc, "Document")

# Configure DSPy with Weaviate
rm = dspy.WeaviateRM("Document", weaviate_client=weaviate_client)
dspy.settings.configure(rm=rm)

# Use retriever
class WeaviateRAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=5)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        passages = self.retrieve(question).passages
        context = "\n\n".join(passages)
        return self.generate(context=context, question=question)

# Use RAG
rag = WeaviateRAG()
result = rag(question="What is DSPy?")
```

**When to use**:
- Production RAG systems
- Large knowledge bases (>100K documents)
- Need for scalability and performance

### Pattern 5: RAG with Reranking

```python
import dspy

class RerankedRAG(dspy.Module):
    """RAG with passage reranking for better quality."""

    def __init__(self, retrieve_k=10, use_k=3):
        super().__init__()
        self.retrieve_k = retrieve_k
        self.use_k = use_k

        self.retrieve = dspy.Retrieve(k=retrieve_k)

        # Reranker: score each passage for relevance
        self.rerank = dspy.Predict(
            "question, passage -> relevance_score: float"
        )

        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        # Initial retrieval (over-fetch)
        passages = self.retrieve(question).passages

        # Rerank passages
        scored_passages = []
        for passage in passages:
            score_result = self.rerank(question=question, passage=passage)
            try:
                score = float(score_result.relevance_score)
            except:
                score = 0.5

            scored_passages.append((score, passage))

        # Sort by score and take top-k
        scored_passages.sort(reverse=True, key=lambda x: x[0])
        top_passages = [p for _, p in scored_passages[:self.use_k]]

        # Generate answer with reranked context
        context = "\n\n".join(top_passages)
        return self.generate(context=context, question=question)

# Use reranked RAG
rag = RerankedRAG(retrieve_k=10, use_k=3)
result = rag(question="What is DSPy?")
```

**Benefits**:
- Better context quality
- Reduce noise from irrelevant passages
- Improved answer accuracy

**Trade-off**: More LM calls (one per passage for reranking)

### Pattern 6: RAG Optimization with BootstrapFewShot

```python
import dspy

# Define RAG module
class SimpleRAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = self.retrieve(question).passages
        return self.generate(context=context, question=question)

# Prepare training data
trainset = [
    dspy.Example(
        question="What is DSPy?",
        answer="A framework for programming language models"
    ).with_inputs("question"),
    # ... more examples
]

# Define metric
def rag_metric(example, pred, trace=None):
    """Check if answer is correct."""
    return example.answer.lower() in pred.answer.lower()

# Optimize RAG pipeline
optimizer = dspy.BootstrapFewShot(metric=rag_metric)

rag = SimpleRAG()
optimized_rag = optimizer.compile(student=rag, trainset=trainset)

# Optimized RAG now has better prompts for generation
result = optimized_rag(question="What is DSPy?")
```

**What gets optimized**:
- Generation module prompts
- Few-shot examples for generation
- Context formatting (implicitly)

### Pattern 7: RAG with Modal-Hosted Models

```python
import dspy
import modal

# Deploy retrieval-optimized model on Modal
app = modal.App("dspy-rag")

@app.function(
    image=modal.Image.debian_slim().pip_install("vllm", "sentence-transformers"),
    gpu="L40S",
)
@modal.web_endpoint(method="POST")
def embed_documents(request: dict):
    """Embedding endpoint for RAG retrieval."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = request.get("texts", [])
    embeddings = model.encode(texts)

    return {"embeddings": embeddings.tolist()}

# Configure DSPy with Modal-hosted LM for generation
lm = dspy.LM(
    "openai/meta-llama/Meta-Llama-3.1-8B-Instruct",
    api_base="https://your-app--serve.modal.run/v1",
    api_key="EMPTY",
)

dspy.configure(lm=lm)

# Use with RAG
class ModalRAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=5)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        passages = self.retrieve(question).passages
        context = "\n\n".join(passages)
        return self.generate(context=context, question=question)

# Use Modal-powered RAG
rag = ModalRAG()
result = rag(question="What is DSPy?")
```

**Benefits**:
- Cost-effective GPU inference
- Serverless scaling
- Custom model deployment

### Pattern 8: Production RAG Pipeline

```python
import dspy
from typing import List, Optional

class ProductionRAG(dspy.Module):
    """Production-ready RAG with error handling and logging."""

    def __init__(self, k=5, min_relevance=0.3):
        super().__init__()
        self.k = k
        self.min_relevance = min_relevance

        self.retrieve = dspy.Retrieve(k=k)
        self.generate = dspy.ChainOfThought(
            "context, question -> answer, confidence: float"
        )

    def forward(self, question: str) -> dspy.Prediction:
        try:
            # Retrieve passages
            retrieval_result = self.retrieve(question)
            passages = retrieval_result.passages

            if not passages:
                # Fallback: no retrieval results
                return dspy.Prediction(
                    answer="I don't have enough information to answer this question.",
                    confidence=0.0,
                    error="No passages retrieved"
                )

            # Format context
            context = "\n\n".join(passages)

            # Generate answer
            result = self.generate(context=context, question=question)

            # Validate confidence
            try:
                confidence = float(result.confidence)
            except:
                confidence = 0.5

            # Low confidence warning
            if confidence < self.min_relevance:
                result.warning = "Low confidence answer"

            result.num_passages = len(passages)
            return result

        except Exception as e:
            # Error handling
            return dspy.Prediction(
                answer="An error occurred while processing your question.",
                confidence=0.0,
                error=str(e)
            )

# Use production RAG
rag = ProductionRAG(k=5, min_relevance=0.6)
result = rag(question="What is DSPy?")

print(f"Answer: {result.answer}")
print(f"Confidence: {result.confidence}")
if hasattr(result, 'warning'):
    print(f"Warning: {result.warning}")
```

**Production features**:
- Error handling
- Confidence scoring
- Validation
- Fallback responses
- Logging/monitoring hooks

---

## Quick Reference

### Basic RAG Pattern

```python
class SimpleRAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=3)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        passages = self.retrieve(question).passages
        context = "\n\n".join(passages)
        return self.generate(context=context, question=question)
```

### Vector DB Setup

```python
# ChromaDB (local)
import chromadb
client = chromadb.Client()
collection = client.create_collection("docs")
rm = dspy.chromadb_rm.ChromadbRM("docs")

# Weaviate (production)
import weaviate
client = weaviate.Client("http://localhost:8080")
rm = dspy.WeaviateRM("Document", weaviate_client=client)

# Configure DSPy
dspy.settings.configure(rm=rm)
```

### RAG Best Practices

```
✅ DO: Use reranking for better quality
✅ DO: Include citations for transparency
✅ DO: Optimize retrieval (k value, chunking strategy)
✅ DO: Handle empty retrieval results
✅ DO: Monitor retrieval quality

❌ DON'T: Retrieve too many passages (context overflow)
❌ DON'T: Skip passage deduplication
❌ DON'T: Ignore retrieval failures
❌ DON'T: Use RAG when LM already has knowledge
```

---

## Anti-Patterns

❌ **Too many retrieved passages**: Context overflow, slow generation
```python
# Bad
self.retrieve = dspy.Retrieve(k=50)  # Too many!
```
✅ Use reasonable k and rerank:
```python
# Good
self.retrieve = dspy.Retrieve(k=10)
# Rerank to top 3
```

❌ **No error handling**: Crashes on retrieval failure
```python
# Bad
passages = self.retrieve(question).passages  # May fail!
context = "\n".join(passages)
```
✅ Handle errors:
```python
# Good
try:
    passages = self.retrieve(question).passages
    if not passages:
        return fallback_response()
except Exception as e:
    log_error(e)
    return error_response()
```

❌ **Ignoring retrieval quality**: Using irrelevant passages
```python
# Bad - use all retrieved passages blindly
passages = self.retrieve(question).passages
context = "\n".join(passages)  # May include irrelevant content
```
✅ Filter or rerank:
```python
# Good - rerank or filter
passages = self.retrieve(question).passages
relevant = [p for p in passages if is_relevant(question, p)]
context = "\n".join(relevant)
```

---

## Advanced Patterns

### Pattern 9: Adaptive Retrieval (Self-RAG)

```python
import dspy

class AdaptiveRAG(dspy.Module):
    """RAG that adapts retrieval strategy based on query complexity."""

    def __init__(self):
        super().__init__()

        # Query analyzer
        self.analyze_query = dspy.ChainOfThought(
            "question -> needs_retrieval: bool, complexity: str, reasoning"
        )

        # Retrieval modules
        self.retrieve = dspy.Retrieve(k=5)

        # Generation with different strategies
        self.direct_answer = dspy.ChainOfThought("question -> answer")
        self.rag_answer = dspy.ChainOfThought("context, question -> answer, confidence: float")

    def forward(self, question):
        # Analyze query
        analysis = self.analyze_query(question=question)

        # Simple queries: answer directly without retrieval
        if not analysis.needs_retrieval:
            result = self.direct_answer(question=question)
            result.retrieval_used = False
            result.complexity = analysis.complexity
            return result

        # Complex queries: use RAG
        passages = self.retrieve(question).passages
        context = "\n\n".join(passages)

        result = self.rag_answer(context=context, question=question)
        result.retrieval_used = True
        result.complexity = analysis.complexity
        result.num_passages = len(passages)

        return result

# Use adaptive RAG
rag = AdaptiveRAG()

# Simple query (likely no retrieval needed)
result1 = rag(question="What is 2+2?")
print(f"Answer: {result1.answer}")
print(f"Used retrieval: {result1.retrieval_used}")

# Complex query (needs retrieval)
result2 = rag(question="What are the latest advances in RAG systems for DSPy?")
print(f"Answer: {result2.answer}")
print(f"Used retrieval: {result2.retrieval_used}")
```

**Benefits**:
- Reduce unnecessary retrieval costs
- Faster responses for simple queries
- Better quality for complex queries

### Pattern 10: Hierarchical RAG

```python
import dspy
from typing import List

class HierarchicalRAG(dspy.Module):
    """Multi-level RAG: coarse retrieval → fine retrieval → generation."""

    def __init__(self):
        super().__init__()

        # Coarse retrieval (document level)
        self.retrieve_docs = dspy.Retrieve(k=10)

        # Reranker for documents
        self.rerank_docs = dspy.Predict("question, document -> relevance_score: float")

        # Fine retrieval (chunk level)
        self.retrieve_chunks = dspy.Retrieve(k=5)

        # Generation
        self.generate = dspy.ChainOfThought("context, question -> answer, sources: list[int]")

    def forward(self, question):
        # Step 1: Coarse retrieval (broad search)
        doc_results = self.retrieve_docs(question)
        documents = doc_results.passages

        # Step 2: Rerank documents
        scored_docs = []
        for doc in documents:
            score_result = self.rerank_docs(question=question, document=doc)
            try:
                score = float(score_result.relevance_score)
            except:
                score = 0.5
            scored_docs.append((score, doc))

        # Keep top-3 documents
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        top_docs = [doc for _, doc in scored_docs[:3]]

        # Step 3: Fine retrieval within top documents
        # (In practice, would search chunks within these docs)
        chunk_results = self.retrieve_chunks(question)
        chunks = chunk_results.passages[:5]

        # Step 4: Generate with refined context
        context = "\n\n".join(chunks)
        result = self.generate(context=context, question=question)

        result.num_docs_retrieved = len(documents)
        result.num_chunks_used = len(chunks)

        return result

# Use hierarchical RAG
rag = HierarchicalRAG()
result = rag(question="How does DSPy optimize RAG pipelines?")

print(f"Answer: {result.answer}")
print(f"Documents retrieved: {result.num_docs_retrieved}")
print(f"Chunks used: {result.num_chunks_used}")
```

**When to use**:
- Large document collections (>100K docs)
- Need balance between recall and precision
- Two-stage retrieval improves quality

### Pattern 11: RAG with Query Expansion

```python
import dspy
from typing import List

class QueryExpansionRAG(dspy.Module):
    """RAG with automatic query expansion for better retrieval."""

    def __init__(self):
        super().__init__()

        # Query expander
        self.expand_query = dspy.ChainOfThought(
            "original_question -> expanded_queries: list[str]"
        )

        # Retrieval
        self.retrieve = dspy.Retrieve(k=3)

        # Deduplication and reranking
        self.rerank = dspy.Predict("question, passage -> relevance_score: float")

        # Generation
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        # Expand query
        expansion = self.expand_query(original_question=question)

        # Parse expanded queries
        if isinstance(expansion.expanded_queries, str):
            queries = [q.strip() for q in expansion.expanded_queries.split('\n') if q.strip()]
        else:
            queries = expansion.expanded_queries

        # Add original query
        all_queries = [question] + queries[:2]  # Original + top 2 expansions

        # Retrieve for all queries
        all_passages = []
        seen_passages = set()

        for query in all_queries:
            passages = self.retrieve(query).passages

            # Deduplicate
            for passage in passages:
                passage_hash = hash(passage[:100])  # Hash first 100 chars
                if passage_hash not in seen_passages:
                    seen_passages.add(passage_hash)
                    all_passages.append(passage)

        # Rerank all passages
        scored_passages = []
        for passage in all_passages:
            score_result = self.rerank(question=question, passage=passage)
            try:
                score = float(score_result.relevance_score)
            except:
                score = 0.5
            scored_passages.append((score, passage))

        # Take top-5 after reranking
        scored_passages.sort(reverse=True, key=lambda x: x[0])
        top_passages = [p for _, p in scored_passages[:5]]

        # Generate with expanded+reranked context
        context = "\n\n".join(top_passages)
        result = self.generate(context=context, question=question)

        result.expanded_queries = all_queries
        result.passages_retrieved = len(all_passages)

        return result

# Use query expansion RAG
rag = QueryExpansionRAG()
result = rag(question="DSPy optimization")

print(f"Original question: DSPy optimization")
print(f"Expanded queries: {result.expanded_queries}")
print(f"Answer: {result.answer}")
```

**Benefits**:
- Better recall (find more relevant docs)
- Handle ambiguous queries
- Improve retrieval quality

---

## Production Considerations

### Deployment Architecture

**Scalable RAG deployment**:
```python
import dspy
import modal
from typing import List
import asyncio

app = modal.App("production-rag")

# Vector database volume (persistent)
vector_db_volume = modal.Volume.from_name("vector-db", create_if_missing=True)

# Model cache volume
model_cache = modal.Volume.from_name("model-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim()
    .pip_install("dspy-ai", "chromadb", "sentence-transformers", "vllm")
)

@app.function(
    image=image,
    gpu="L40S",
    volumes={
        "/vector-db": vector_db_volume,
        "/models": model_cache,
    },
    timeout=300,
    concurrency_limit=10,
)
@modal.web_endpoint(method="POST")
def rag_endpoint(request: dict):
    """Production RAG endpoint."""
    import chromadb
    from chromadb.utils import embedding_functions

    # Initialize vector DB
    client = chromadb.PersistentClient(path="/vector-db")
    collection = client.get_or_create_collection(
        name="knowledge_base",
        embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
            device="cuda"
        )
    )

    # Configure DSPy with cached LM
    lm = dspy.LM(
        "openai/meta-llama/Meta-Llama-3.1-8B-Instruct",
        api_base="http://localhost:8000/v1",
        api_key="EMPTY",
    )
    dspy.configure(lm=lm)

    # Set up retriever
    rm = dspy.chromadb_rm.ChromadbRM(
        collection_name="knowledge_base",
        persist_directory="/vector-db"
    )
    dspy.settings.configure(rm=rm)

    # RAG pipeline
    class ProductionRAG(dspy.Module):
        def __init__(self):
            super().__init__()
            self.retrieve = dspy.Retrieve(k=5)
            self.generate = dspy.ChainOfThought("context, question -> answer, confidence: float")

        def forward(self, question):
            passages = self.retrieve(question).passages
            context = "\n\n".join(passages)
            return self.generate(context=context, question=question)

    # Process request
    question = request.get("question", "")
    if not question:
        return {"error": "No question provided"}

    rag = ProductionRAG()
    result = rag(question=question)

    return {
        "answer": result.answer,
        "confidence": result.confidence if hasattr(result, 'confidence') else 0.5,
    }

# Deploy: modal deploy rag_production.py
```

### Caching Strategy

```python
import dspy
from typing import Dict, Optional
from functools import lru_cache
import hashlib
import json
from pathlib import Path

class CachedRAG(dspy.Module):
    """RAG with multi-level caching."""

    def __init__(self, cache_dir: str = ".cache"):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=5)
        self.generate = dspy.ChainOfThought("context, question -> answer")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # In-memory cache (LRU)
        self._memory_cache: Dict[str, str] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def _hash_question(self, question: str) -> str:
        """Generate cache key."""
        return hashlib.md5(question.lower().strip().encode()).hexdigest()

    def _get_from_memory(self, cache_key: str) -> Optional[str]:
        """Check in-memory cache."""
        return self._memory_cache.get(cache_key)

    def _get_from_disk(self, cache_key: str) -> Optional[str]:
        """Check disk cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                data = json.load(f)
                return data.get('answer')
        return None

    def _save_to_cache(self, cache_key: str, answer: str):
        """Save to both memory and disk."""
        # Memory cache (keep last 1000 entries)
        if len(self._memory_cache) >= 1000:
            # Remove oldest entry (simple FIFO)
            self._memory_cache.pop(next(iter(self._memory_cache)))

        self._memory_cache[cache_key] = answer

        # Disk cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump({'answer': answer}, f)

    def forward(self, question: str):
        cache_key = self._hash_question(question)

        # Try memory cache
        cached = self._get_from_memory(cache_key)
        if cached:
            self._cache_hits += 1
            return dspy.Prediction(answer=cached, cached=True, cache_type='memory')

        # Try disk cache
        cached = self._get_from_disk(cache_key)
        if cached:
            self._cache_hits += 1
            # Promote to memory cache
            self._memory_cache[cache_key] = cached
            return dspy.Prediction(answer=cached, cached=True, cache_type='disk')

        # Cache miss - compute answer
        self._cache_misses += 1

        passages = self.retrieve(question).passages
        context = "\n\n".join(passages)
        result = self.generate(context=context, question=question)

        # Cache result
        self._save_to_cache(cache_key, result.answer)

        result.cached = False
        return result

    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0

        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': hit_rate,
            'memory_entries': len(self._memory_cache),
        }

# Use cached RAG
rag = CachedRAG(cache_dir=".rag_cache")

# First call (cache miss)
result1 = rag(question="What is DSPy?")
print(f"Cached: {result1.cached}")

# Second call (cache hit)
result2 = rag(question="What is DSPy?")
print(f"Cached: {result2.cached}")

# Check cache stats
stats = rag.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.1%}")
```

### Monitoring and Observability

```python
import dspy
from typing import Dict
import logging
import time
from datetime import datetime

class ObservableRAG(dspy.Module):
    """RAG with comprehensive observability."""

    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=5)
        self.generate = dspy.ChainOfThought("context, question -> answer, confidence: float")

        # Metrics
        self.metrics = {
            'total_queries': 0,
            'avg_retrieval_time': 0.0,
            'avg_generation_time': 0.0,
            'avg_confidence': 0.0,
            'low_confidence_count': 0,
        }

    def forward(self, question: str):
        start_time = time.time()
        self.metrics['total_queries'] += 1

        # Log request
        logging.info(f"RAG query: {question[:100]}")

        # Retrieval with timing
        retrieval_start = time.time()
        try:
            retrieval_result = self.retrieve(question)
            passages = retrieval_result.passages
            retrieval_time = time.time() - retrieval_start

            # Update metrics
            self.metrics['avg_retrieval_time'] = (
                (self.metrics['avg_retrieval_time'] * (self.metrics['total_queries'] - 1) +
                 retrieval_time) / self.metrics['total_queries']
            )

            logging.info(f"Retrieved {len(passages)} passages in {retrieval_time:.2f}s")

        except Exception as e:
            logging.error(f"Retrieval failed: {e}")
            raise

        # Generation with timing
        generation_start = time.time()
        try:
            context = "\n\n".join(passages)
            result = self.generate(context=context, question=question)
            generation_time = time.time() - generation_start

            # Update metrics
            self.metrics['avg_generation_time'] = (
                (self.metrics['avg_generation_time'] * (self.metrics['total_queries'] - 1) +
                 generation_time) / self.metrics['total_queries']
            )

            # Track confidence
            try:
                confidence = float(result.confidence)
                self.metrics['avg_confidence'] = (
                    (self.metrics['avg_confidence'] * (self.metrics['total_queries'] - 1) +
                     confidence) / self.metrics['total_queries']
                )

                if confidence < 0.5:
                    self.metrics['low_confidence_count'] += 1
                    logging.warning(f"Low confidence answer: {confidence:.2f}")

            except:
                confidence = 0.5

            logging.info(f"Generated answer in {generation_time:.2f}s, confidence: {confidence:.2f}")

        except Exception as e:
            logging.error(f"Generation failed: {e}")
            raise

        total_time = time.time() - start_time

        # Attach metadata
        result.timing = {
            'retrieval_ms': retrieval_time * 1000,
            'generation_ms': generation_time * 1000,
            'total_ms': total_time * 1000,
        }
        result.num_passages = len(passages)

        return result

    def get_metrics(self) -> Dict:
        """Get performance metrics."""
        return {
            **self.metrics,
            'low_confidence_rate': (
                self.metrics['low_confidence_count'] / self.metrics['total_queries']
                if self.metrics['total_queries'] > 0 else 0.0
            ),
        }

# Use observable RAG
logging.basicConfig(level=logging.INFO)
rag = ObservableRAG()

result = rag(question="What is DSPy?")
print(f"Answer: {result.answer}")
print(f"Timing: {result.timing}")

# Check metrics
metrics = rag.get_metrics()
print(f"\nMetrics:")
print(f"  Total queries: {metrics['total_queries']}")
print(f"  Avg retrieval: {metrics['avg_retrieval_time']*1000:.1f}ms")
print(f"  Avg generation: {metrics['avg_generation_time']*1000:.1f}ms")
print(f"  Avg confidence: {metrics['avg_confidence']:.2f}")
```

### Best Practices Checklist

```
Architecture:
✅ DO: Use serverless (Modal) for scalable RAG
✅ DO: Persist vector DB in volumes
✅ DO: Cache models and embeddings
✅ DO: Use GPU for embedding generation
✅ DO: Set appropriate concurrency limits

Performance:
✅ DO: Implement multi-level caching (memory + disk)
✅ DO: Monitor retrieval and generation latency
✅ DO: Track cache hit rates
✅ DO: Use reranking to improve quality
✅ DO: Batch retrieval requests where possible

Quality:
✅ DO: Monitor answer confidence scores
✅ DO: Alert on low confidence responses
✅ DO: Track retrieval coverage metrics
✅ DO: Log failed retrievals
✅ DO: Version control vector DB schemas

Cost Optimization:
✅ DO: Cache frequent queries aggressively
✅ DO: Use adaptive retrieval (skip when not needed)
✅ DO: Monitor token usage per query
✅ DO: Set k (retrieval count) appropriately
✅ DO: Use cheaper models for reranking

❌ DON'T: Retrieve too many passages (context overflow)
❌ DON'T: Skip error handling in production
❌ DON'T: Ignore retrieval quality metrics
❌ DON'T: Hard-code vector DB endpoints
❌ DON'T: Deploy without load testing
```

---

## Related Skills

### Core DSPy Skills
- `dspy-modules.md` - Building RAG modules
- `dspy-optimizers.md` - Optimizing RAG pipelines
- `dspy-evaluation.md` - Evaluating RAG quality
- `dspy-signatures.md` - RAG signature design
- `dspy-setup.md` - LM configuration for RAG

### Advanced DSPy Skills
- `dspy-agents.md` - RAG-powered agents
- `dspy-multi-agent.md` - Multi-agent RAG systems
- `dspy-production.md` - Production RAG deployment
- `dspy-testing.md` - Testing RAG pipelines
- `dspy-debugging.md` - Debugging retrieval issues
- `dspy-caching.md` - Advanced caching strategies
- `dspy-advanced-patterns.md` - Advanced RAG patterns

### Infrastructure Skills
- `modal-functions-basics.md` - Deploying RAG on Modal
- `modal-gpu-workloads.md` - GPU optimization for embeddings
- `modal-web-endpoints.md` - RAG API endpoints
- `database-vector-search.md` - Vector database optimization

### Resources
- `resources/dspy/level2-rag.md` - RAG deep dive
- `resources/dspy/level3-production.md` - Production RAG guide
- `resources/dspy/rag-cookbook.md` - RAG recipes
- `resources/dspy/vector-db-comparison.md` - Vector DB selection guide

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
