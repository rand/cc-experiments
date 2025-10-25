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

## Related Skills

- `dspy-modules.md` - Building RAG modules
- `dspy-optimizers.md` - Optimizing RAG pipelines
- `dspy-evaluation.md` - Evaluating RAG quality
- `database/mongodb-basics.md` - Document storage
- `database/postgres-query-optimization.md` - Metadata storage

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
