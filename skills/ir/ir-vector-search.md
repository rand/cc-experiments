---
name: ir-vector-search
description: Dense retrieval using embeddings, vector databases, approximate nearest neighbors, and hybrid search
---

# Information Retrieval: Vector Search

**Scope**: Semantic search with embeddings, vector databases (Pinecone, Weaviate, Qdrant, Chroma), ANN algorithms, and hybrid retrieval
**Lines**: ~360
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building semantic search that understands meaning, not just keywords
- Implementing similarity search for documents, images, or products
- Choosing between vector database options (Pinecone, Weaviate, Qdrant, Chroma)
- Optimizing approximate nearest neighbor (ANN) search performance
- Combining lexical and semantic search (hybrid retrieval)
- Scaling vector search to millions or billions of embeddings
- Selecting embedding models for specific domains
- Troubleshooting vector search relevance or speed issues

## Core Concepts

### Concept 1: Embeddings and Dense Retrieval

**Dense Retrieval**: Encode queries and documents as dense vectors, retrieve by similarity

**Key Points**:
- Embeddings capture semantic meaning in vector space
- Similar concepts have similar vectors (cosine similarity)
- Pre-trained models: sentence-transformers, OpenAI, Cohere
- Domain-specific models often outperform general models

```python
from sentence_transformers import SentenceTransformer
import numpy as np

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions

# Encode documents
documents = [
    "Machine learning algorithms for classification",
    "Deep neural networks for image recognition",
    "Natural language processing with transformers",
    "Supervised learning techniques"
]

doc_embeddings = model.encode(documents, convert_to_numpy=True)

# Encode query
query = "classification algorithms"
query_embedding = model.encode(query, convert_to_numpy=True)

# Compute cosine similarity
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Rank documents by similarity
scores = [cosine_similarity(query_embedding, doc_emb) for doc_emb in doc_embeddings]
ranked_indices = np.argsort(scores)[::-1]

for idx in ranked_indices:
    print(f"Doc {idx}: {documents[idx]}")
    print(f"  Score: {scores[idx]:.4f}\n")
```

### Concept 2: Vector Databases

**Comparison**:

| Database | Hosted | Open Source | Best For |
|----------|--------|-------------|----------|
| Pinecone | Yes | No | Fully managed, scale to billions |
| Weaviate | Yes | Yes | GraphQL, hybrid search, modules |
| Qdrant | Yes | Yes | High performance, on-prem option |
| Chroma | No | Yes | Embeddings + metadata, local dev |

**Key Features**:
- Approximate nearest neighbors (ANN) for fast search
- Metadata filtering alongside vector search
- Horizontal scaling for large datasets
- Different distance metrics (cosine, dot product, L2)

```python
import chromadb
from chromadb.config import Settings

# Initialize Chroma (local, persistent)
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./chroma_db"
))

# Create collection
collection = client.create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}  # Cosine similarity
)

# Add documents with embeddings and metadata
collection.add(
    ids=["doc1", "doc2", "doc3"],
    embeddings=doc_embeddings.tolist(),
    documents=documents,
    metadatas=[
        {"category": "ml", "date": "2024-01-15"},
        {"category": "dl", "date": "2024-02-20"},
        {"category": "nlp", "date": "2024-03-10"}
    ]
)

# Query with metadata filtering
results = collection.query(
    query_embeddings=[query_embedding.tolist()],
    n_results=3,
    where={"category": "ml"}  # Filter by metadata
)

print(results['documents'])
print(results['distances'])
```

### Concept 3: Approximate Nearest Neighbors (ANN)

**Algorithms**:

**HNSW (Hierarchical Navigable Small World)**:
- Graph-based search with hierarchical layers
- Fast queries (log n), moderate memory
- Default in Chroma, Qdrant, Weaviate

**IVF (Inverted File Index)**:
- Partition vectors into clusters (Voronoi cells)
- Search nearest clusters only
- Used in FAISS, Pinecone

**LSH (Locality Sensitive Hashing)**:
- Hash similar vectors to same buckets
- Fast but lower recall than HNSW/IVF

```python
import faiss
import numpy as np

# Build IVF index with FAISS
dimension = 384
nlist = 100  # Number of clusters

# Create index
quantizer = faiss.IndexFlatL2(dimension)  # L2 distance
index = faiss.IndexIVFFlat(quantizer, dimension, nlist)

# Train index on data (required for IVF)
index.train(doc_embeddings.astype('float32'))

# Add vectors
index.add(doc_embeddings.astype('float32'))

# Search (k=3 nearest neighbors)
k = 3
distances, indices = index.search(
    query_embedding.reshape(1, -1).astype('float32'),
    k
)

print("Nearest neighbors:", indices)
print("Distances:", distances)

# HNSW index (no training needed)
hnsw_index = faiss.IndexHNSWFlat(dimension, 32)  # 32 = M parameter
hnsw_index.add(doc_embeddings.astype('float32'))
distances_hnsw, indices_hnsw = hnsw_index.search(
    query_embedding.reshape(1, -1).astype('float32'),
    k
)
```

### Concept 4: Distance Metrics

**Cosine Similarity**: Angle between vectors (range: -1 to 1)
- Best for: Text embeddings (normalized)
- Formula: `cos(θ) = A·B / (||A|| ||B||)`

**Dot Product**: Inner product (unnormalized)
- Best for: When magnitude matters
- Formula: `A·B = Σ(ai × bi)`

**Euclidean (L2)**: Straight-line distance
- Best for: Spatial data, images
- Formula: `||A-B|| = √(Σ(ai-bi)²)`

```python
# Configure metric in Pinecone
import pinecone

pinecone.init(api_key="your-api-key")

# Cosine similarity (most common for text)
pinecone.create_index(
    "documents",
    dimension=384,
    metric="cosine"
)

# Dot product (if embeddings are normalized)
pinecone.create_index(
    "normalized-docs",
    dimension=384,
    metric="dotproduct"
)

# Euclidean distance
pinecone.create_index(
    "spatial-data",
    dimension=384,
    metric="euclidean"
)
```

---

## Patterns

### Pattern 1: Batch Encoding for Performance

**When to use**: Encoding many documents or queries

```python
# ❌ Bad: Encode one at a time (slow)
embeddings = []
for doc in documents:
    emb = model.encode(doc)
    embeddings.append(emb)

# ✅ Good: Batch encoding (10-100x faster)
embeddings = model.encode(
    documents,
    batch_size=32,        # Process in batches
    show_progress_bar=True,
    convert_to_numpy=True
)

# ✅ Better: Use GPU if available
embeddings = model.encode(
    documents,
    batch_size=128,       # Larger batches on GPU
    device='cuda',        # Use GPU
    show_progress_bar=True
)
```

**Benefits**:
- 10-100x speedup via batching
- GPU acceleration for large datasets
- Progress tracking for long jobs

### Pattern 2: Hybrid Search (Lexical + Semantic)

**Use case**: Combine keyword matching (BM25) with semantic similarity

```python
from weaviate import Client

client = Client("http://localhost:8080")

# Create schema with hybrid search enabled
schema = {
    "class": "Article",
    "vectorizer": "text2vec-transformers",
    "properties": [
        {"name": "title", "dataType": ["text"]},
        {"name": "content", "dataType": ["text"]}
    ]
}

client.schema.create_class(schema)

# Hybrid search: combines BM25 + vector search
results = (
    client.query
    .get("Article", ["title", "content"])
    .with_hybrid(
        query="machine learning",
        alpha=0.5  # 0.5 = equal weight, 0 = pure BM25, 1 = pure vector
    )
    .with_limit(10)
    .do()
)

# Tune alpha based on query type
# alpha=0.2 for keyword queries ("product SKU 12345")
# alpha=0.8 for semantic queries ("comfortable running shoes")
```

**Benefits**:
- Best of both worlds: exact matching + semantic understanding
- Configurable weighting (alpha parameter)
- Better recall and precision

### Pattern 3: Metadata Filtering

**When to use**: Combine semantic search with structured constraints

```python
import qdrant_client
from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition

# Initialize Qdrant
client = qdrant_client.QdrantClient(host="localhost", port=6333)

# Create collection
client.create_collection(
    collection_name="products",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)

# Upsert with metadata
client.upsert(
    collection_name="products",
    points=[
        {
            "id": 1,
            "vector": embedding1.tolist(),
            "payload": {"category": "electronics", "price": 599, "brand": "Apple"}
        },
        {
            "id": 2,
            "vector": embedding2.tolist(),
            "payload": {"category": "electronics", "price": 299, "brand": "Samsung"}
        }
    ]
)

# Search with filters
results = client.search(
    collection_name="products",
    query_vector=query_embedding.tolist(),
    query_filter=Filter(
        must=[
            FieldCondition(key="category", match={"value": "electronics"}),
            FieldCondition(key="price", range={"gte": 200, "lte": 600})
        ]
    ),
    limit=10
)
```

### Pattern 4: Embedding Model Selection

**Use case**: Choose appropriate model for domain and requirements

```python
from sentence_transformers import SentenceTransformer

# ✅ General purpose, fast (384 dim)
model_general = SentenceTransformer('all-MiniLM-L6-v2')

# ✅ High quality, slower (768 dim)
model_quality = SentenceTransformer('all-mpnet-base-v2')

# ✅ Multilingual (768 dim, 50+ languages)
model_multilingual = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

# ✅ Domain-specific: scientific papers
model_scientific = SentenceTransformer('allenai-specter')

# ✅ Asymmetric search (different query/doc encoders)
# For Q&A, search queries vs passages
from sentence_transformers import SentenceTransformer, util

model_qa = SentenceTransformer('multi-qa-mpnet-base-dot-v1')

# Encode differently
queries = ["What is machine learning?"]
passages = ["Machine learning is a subset of AI..."]

query_embeddings = model_qa.encode(queries, convert_to_tensor=True)
passage_embeddings = model_qa.encode(passages, convert_to_tensor=True)

# Use dot product for asymmetric models
scores = util.dot_score(query_embeddings, passage_embeddings)
```

**Selection Criteria**:
- Speed vs quality: MiniLM (fast) vs MPNet (quality)
- Languages: Use multilingual models for non-English
- Domain: Scientific, legal, medical → use domain models
- Query type: Symmetric (search) vs asymmetric (Q&A)

### Pattern 5: Incremental Updates

**When to use**: Add/update/delete vectors without rebuilding entire index

```python
# Pinecone incremental updates
import pinecone

pinecone.init(api_key="your-key", environment="us-west1-gcp")
index = pinecone.Index("documents")

# Upsert new vectors (inserts or updates)
index.upsert(
    vectors=[
        ("doc1", embedding1.tolist(), {"text": "...", "category": "tech"}),
        ("doc2", embedding2.tolist(), {"text": "...", "category": "science"})
    ]
)

# Update metadata only (no re-embedding)
index.update(
    id="doc1",
    set_metadata={"category": "ai", "updated": "2024-10-25"}
)

# Delete vectors
index.delete(ids=["doc3", "doc4"])

# Delete by metadata filter
index.delete(filter={"category": {"$eq": "deprecated"}})
```

### Pattern 6: Query Optimization

**Use case**: Improve search quality and speed

```python
# ✅ Query expansion: add related terms
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')

def expand_query(query, corpus_embeddings, corpus_docs, top_k=3):
    """Expand query with similar documents from corpus"""
    query_emb = model.encode(query, convert_to_tensor=True)
    scores = util.cos_sim(query_emb, corpus_embeddings)[0]
    top_indices = scores.argsort(descending=True)[:top_k]

    # Combine original query with top results
    expanded = [query] + [corpus_docs[i] for i in top_indices]
    return " ".join(expanded)

# ✅ Multi-vector search: aggregate results
def multi_vector_search(queries, index, top_k=10):
    """Search with multiple query formulations"""
    all_results = {}

    for query in queries:
        query_emb = model.encode(query)
        results = index.search(query_emb, top_k=top_k)

        # Aggregate scores
        for doc_id, score in results:
            all_results[doc_id] = all_results.get(doc_id, 0) + score

    # Rank by aggregated score
    ranked = sorted(all_results.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]

# Example: search with original + reformulations
queries = [
    "machine learning classification",
    "supervised learning algorithms",
    "classification models"
]
results = multi_vector_search(queries, index)
```

### Pattern 7: Approximate vs Exact Search

**When to use**: Trade accuracy for speed

```python
import faiss

# ✅ Exact search (brute force)
index_exact = faiss.IndexFlatL2(dimension)
index_exact.add(embeddings.astype('float32'))

# Search all vectors (slow but 100% accurate)
distances, indices = index_exact.search(query_emb, k=10)

# ✅ Approximate search (HNSW)
index_approx = faiss.IndexHNSWFlat(dimension, 32)
index_approx.add(embeddings.astype('float32'))

# Much faster, ~95-99% recall
distances, indices = index_approx.search(query_emb, k=10)

# ✅ Tune recall vs speed
index_approx.hnsw.efSearch = 64  # Higher = better recall, slower
# efSearch = 16: fast, ~90% recall
# efSearch = 64: balanced, ~95% recall
# efSearch = 256: slow, ~99% recall
```

---

## Quick Reference

### Embedding Model Comparison

```
Model                    | Dimensions | Speed   | Quality | Use Case
-------------------------|------------|---------|---------|----------
all-MiniLM-L6-v2         | 384        | Fast    | Good    | General, speed critical
all-mpnet-base-v2        | 768        | Medium  | Best    | General, quality critical
multi-qa-mpnet-base      | 768        | Medium  | Best    | Q&A, asymmetric search
paraphrase-multilingual  | 768        | Medium  | Good    | 50+ languages
allenai-specter          | 768        | Medium  | Best    | Scientific papers
```

### Vector Database Features

```
Feature            | Pinecone | Weaviate | Qdrant | Chroma
-------------------|----------|----------|--------|--------
Managed hosting    | ✅       | ✅       | ✅     | ❌
Open source        | ❌       | ✅       | ✅     | ✅
Hybrid search      | ❌       | ✅       | ✅     | ❌
Metadata filtering | ✅       | ✅       | ✅     | ✅
Horizontal scaling | ✅       | ✅       | ✅     | Limited
GraphQL API        | ❌       | ✅       | ❌     | ❌
```

### Key Guidelines

```
✅ DO: Normalize embeddings if using dot product metric
✅ DO: Batch encode for 10-100x speedup
✅ DO: Use hybrid search for best results
✅ DO: Filter metadata before vector search when possible
✅ DO: Monitor index size and query latency
✅ DO: Test different embedding models for your domain

❌ DON'T: Use high-dimensional embeddings without need (768 vs 384)
❌ DON'T: Encode one document at a time
❌ DON'T: Ignore metadata filtering capabilities
❌ DON'T: Use exact search for >100k vectors (too slow)
❌ DON'T: Mix distance metrics (cosine vs L2) carelessly
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Store raw text in vector DB without chunking
long_document = "..." * 10000  # 50k words
embedding = model.encode(long_document)  # Loses information, poor quality

# ✅ CORRECT: Chunk documents before embedding
def chunk_document(text, chunk_size=512, overlap=50):
    """Split into overlapping chunks"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

chunks = chunk_document(long_document)
embeddings = model.encode(chunks, batch_size=32)

# Store each chunk separately with document ID
for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
    index.upsert(
        id=f"doc1_chunk{i}",
        vector=emb.tolist(),
        metadata={"doc_id": "doc1", "chunk_id": i, "text": chunk}
    )
```

❌ **Long document embedding**: Information loss, poor retrieval quality
✅ **Correct approach**: Chunk documents (256-512 tokens), embed separately

### Common Mistakes

```python
# ❌ Don't: Use wrong metric for normalized embeddings
# Sentence-transformers normalize embeddings by default
index = faiss.IndexFlatL2(dimension)  # L2 distance (wrong for normalized)

# ✅ Correct: Use dot product or cosine for normalized embeddings
index = faiss.IndexFlatIP(dimension)  # Inner product (correct)

# Verify normalization
norms = np.linalg.norm(embeddings, axis=1)
print(f"Norms: {norms}")  # Should be ~1.0 for normalized
```

❌ **Metric mismatch**: Wrong distance metric gives poor results
✅ **Better**: Match metric to embedding properties (normalized → dot product/cosine)

```python
# ❌ Don't: Rebuild entire index for small updates
# Bad: Re-embed and rebuild for every new document
all_docs.append(new_doc)
all_embeddings = model.encode(all_docs)  # Re-encodes everything
index = build_index(all_embeddings)      # Rebuilds entire index

# ✅ Correct: Incremental updates
new_embedding = model.encode([new_doc])
index.upsert(id="new_doc_id", vector=new_embedding[0].tolist())
```

❌ **Full rebuilds**: Wastes compute, increases latency
✅ **Better**: Use incremental upsert/delete operations

```python
# ❌ Don't: Ignore query-document asymmetry
# Same encoder for "What is ML?" and "Machine learning is..."
model = SentenceTransformer('all-MiniLM-L6-v2')
query_emb = model.encode("What is ML?")
doc_emb = model.encode("Machine learning is a subset of AI...")

# ✅ Correct: Use asymmetric model for Q&A
model = SentenceTransformer('multi-qa-mpnet-base-dot-v1')
query_emb = model.encode("What is ML?")
doc_emb = model.encode("Machine learning is a subset of AI...")
# Model trained to map questions → answers in same space
```

❌ **Symmetric models for Q&A**: Lower quality question-answer matching
✅ **Better**: Use models trained for asymmetric retrieval (multi-qa-*)

```python
# ❌ Don't: Store embeddings without metadata
index.upsert(id="doc1", vector=embedding.tolist())
# Later: No way to filter by category, date, etc.

# ✅ Correct: Always include useful metadata
index.upsert(
    id="doc1",
    vector=embedding.tolist(),
    metadata={
        "text": doc_text,      # Original text
        "title": doc_title,
        "category": "tech",
        "date": "2024-10-25",
        "author": "Alice",
        "url": "https://..."
    }
)

# Enables filtered search
results = index.query(
    vector=query_emb,
    filter={"category": "tech", "date": {"$gte": "2024-01-01"}}
)
```

❌ **No metadata**: Can't filter results by attributes
✅ **Better**: Store rich metadata for filtering and display

---

## Related Skills

- `ir-search-fundamentals.md` - Lexical search (BM25) to combine with vector search (hybrid)
- `ir-ranking-reranking.md` - Rerank vector search results with cross-encoders for better quality
- `ir-query-understanding.md` - Process queries before embedding (expansion, correction)
- `ml/dspy-rag.md` - Use vector search for retrieval in RAG pipelines
- `database-postgres.md` - pgvector extension for vector search in Postgres

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
