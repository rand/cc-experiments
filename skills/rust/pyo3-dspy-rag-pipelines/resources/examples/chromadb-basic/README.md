# ChromaDB Basic Example

A complete example demonstrating ChromaDB vector database integration with DSPy from Rust using PyO3.

## Overview

This example shows how to:
- Initialize ChromaDB client from Rust
- Create and manage collections
- Add documents with embeddings
- Perform similarity search queries
- Integrate with DSPy's Retrieve module
- Handle errors in vector database operations

## Prerequisites

- Rust 1.70+
- Python 3.8+
- ChromaDB installed
- OpenAI API key (for embeddings)

## Setup

1. Install ChromaDB and dependencies:
```bash
./setup.sh
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-key-here"
```

3. Build and run:
```bash
cargo build
cargo run
```

## What This Example Demonstrates

### 1. ChromaDB Client Initialization
Creates a ChromaDB client that persists data locally:
```rust
let chromadb = py.import("chromadb")?;
let client = chromadb.call_method0("Client")?;
```

### 2. Collection Management
Creates collections with embedding functions:
```rust
let collection = client.call_method(
    "get_or_create_collection",
    (collection_name,),
    Some(kwargs)
)?;
```

### 3. Document Ingestion
Adds documents with metadata and automatic embedding generation:
```rust
collection.call_method(
    "add",
    (),
    Some(kwargs.into())
)?;
```

### 4. Similarity Search
Queries the collection to find relevant documents:
```rust
let results = collection.call_method(
    "query",
    (),
    Some(kwargs.into())
)?;
```

### 5. DSPy Integration
Wraps ChromaDB in a DSPy-compatible retriever:
```rust
let retrieve_module = dspy.call_method(
    "Retrieve",
    (),
    Some(kwargs.into())
)?;
```

## Architecture

```
Rust Application
    |
    v
PyO3 Bindings
    |
    +-- ChromaDB Client (Python)
    |       |
    |       +-- Collection Management
    |       +-- Embedding Generation (OpenAI)
    |       +-- Vector Storage
    |       +-- Similarity Search
    |
    +-- DSPy Retrieve Module
            |
            +-- Query Interface
            +-- Result Formatting
```

## Code Structure

### Main Components

1. **ChromaDB Setup** (`setup_chromadb`)
   - Client initialization
   - Collection creation
   - Document ingestion

2. **Similarity Search** (`query_chromadb`)
   - Query execution
   - Result extraction
   - Distance/score parsing

3. **DSPy Integration** (`create_dspy_retriever`)
   - Retriever module creation
   - Custom retriever wrapping
   - Query interface

4. **Result Processing**
   - Document extraction
   - Metadata handling
   - Score normalization

## Example Output

```
ChromaDB Basic Example
=====================

Setting up ChromaDB with sample documents...
Collection 'rust_docs' created with 5 documents

Querying: "How do I handle errors in Rust?"

Top 3 Results:
--------------

Result 1 (Score: 0.82):
Document: Rust provides the Result<T, E> type for recoverable errors...
Metadata: {"topic": "error_handling", "difficulty": "intermediate"}

Result 2 (Score: 0.76):
Document: The ? operator provides a concise way to propagate errors...
Metadata: {"topic": "error_handling", "difficulty": "intermediate"}

Result 3 (Score: 0.68):
Document: For unrecoverable errors, use the panic! macro...
Metadata: {"topic": "error_handling", "difficulty": "beginner"}

Testing DSPy Integration
-----------------------

DSPy Retrieve Results:
1. Rust provides the Result<T, E> type for recoverable errors...
2. The ? operator provides a concise way to propagate errors...
3. For unrecoverable errors, use the panic! macro...

Example completed successfully!
```

## Key Concepts

### Vector Embeddings
ChromaDB automatically generates embeddings for text using OpenAI's embedding models. These embeddings capture semantic meaning, enabling similarity search.

### Similarity Search
Uses cosine similarity to find documents closest to the query in embedding space. Lower distances indicate higher similarity.

### Collection Configuration
Collections can be configured with:
- Custom embedding functions
- Metadata schemas
- Distance metrics (L2, cosine, inner product)

### DSPy Integration
The DSPy Retrieve module provides:
- Standardized query interface
- Result formatting
- Integration with DSPy pipelines

## Error Handling

The example demonstrates comprehensive error handling:
- PyO3 conversion errors
- ChromaDB initialization failures
- Collection operation errors
- Query execution failures
- Result parsing errors

## Extending This Example

### Add Custom Embeddings
Replace OpenAI with custom embedding functions:
```python
from chromadb.utils import embedding_functions
custom_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
```

### Filter by Metadata
Add metadata filters to queries:
```rust
let where_clause = vec![
    ("topic", "error_handling"),
    ("difficulty", "intermediate")
];
```

### Update Documents
Modify existing documents:
```rust
collection.call_method("update", (ids, documents), None)?;
```

### Delete Documents
Remove documents from collection:
```rust
collection.call_method("delete", (ids,), None)?;
```

## Performance Considerations

- **Batch Operations**: Add documents in batches for better performance
- **Embedding Cache**: Embeddings are cached to avoid redundant API calls
- **Collection Size**: ChromaDB scales well to millions of documents
- **Query Optimization**: Use metadata filters to reduce search space

## Troubleshooting

### ChromaDB Not Found
```bash
pip install chromadb
```

### OpenAI API Errors
Verify your API key is set and valid:
```bash
echo $OPENAI_API_KEY
```

### Collection Already Exists
Use `get_or_create_collection` instead of `create_collection`, or delete existing collection:
```python
client.delete_collection(name="collection_name")
```

## References

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [PyO3 Guide](https://pyo3.rs/)

## Next Steps

After mastering this example, explore:
- `chromadb-advanced/` - Custom embeddings, filters, and collection management
- `dspy-retrieve/` - Advanced DSPy retrieval patterns
- `multi-vector-dbs/` - Comparing ChromaDB with other vector databases
