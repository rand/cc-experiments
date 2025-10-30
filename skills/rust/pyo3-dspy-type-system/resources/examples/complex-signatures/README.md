# Complex Signatures Example

Multi-field signatures with nested types for RAG-style applications.

## Signature

```
"question: str, context: List[str], metadata: Dict[str, float] -> answer: str, sources: List[int], confidence: float"
```

## Features

- **Nested Collections**: `Vec<String>` for context lists
- **Complex Maps**: `HashMap<String, f64>` for metadata
- **Type Safety**: Serde serialization/deserialization
- **RAG Pattern**: Question + context + metadata → answer + sources + confidence

## Types

### Input Structure
```rust
struct RAGInput {
    question: String,
    context: Vec<String>,
    metadata: HashMap<String, f64>,
}
```

### Output Structure
```rust
struct RAGOutput {
    answer: String,
    sources: Vec<i64>,
    confidence: f64,
}
```

## Usage

```bash
cargo run
```

## Example Queries

### Scientific Query
```rust
RAGInput {
    question: "What is quantum entanglement?",
    context: vec![
        "Quantum entanglement is a physical phenomenon...",
        "Einstein called it 'spooky action at a distance'...",
        "Entangled particles share quantum states..."
    ],
    metadata: {
        "relevance": 0.95,
        "recency": 0.87,
        "authority": 0.92
    }
}
```

### Historical Query
```rust
RAGInput {
    question: "When did the Renaissance begin?",
    context: vec![
        "The Renaissance began in 14th century Italy...",
        "Florence was a major center of Renaissance culture..."
    ],
    metadata: {
        "relevance": 0.88,
        "recency": 0.45,
        "authority": 0.91
    }
}
```

## Implementation Details

### Input Conversion
Converts Rust structs to Python dictionaries:
```rust
fn to_py_dict(&self, py: Python) -> PyResult<PyObject> {
    // Convert Vec<String> to PyList
    // Convert HashMap to PyDict
    // Return as Python object
}
```

### Output Extraction
Extracts typed fields from Python predictions:
```rust
fn from_py_prediction(py: Python, prediction: &PyAny) -> PyResult<Self> {
    // Extract string field
    // Extract list of integers
    // Extract float field
    // Validate types
}
```

### Error Handling
- Type mismatches in nested structures
- Missing fields in predictions
- Invalid collection elements
- Serialization failures

## Key Patterns

1. **Collection Handling**: Iterate and convert each element
2. **Map Serialization**: Use PyDict for HashMap representation
3. **Type Validation**: Check element types in collections
4. **Graceful Degradation**: Default values for missing optional fields

## Testing

The example demonstrates:
- Multiple complex queries
- Nested type conversions
- Error handling for malformed data
- Field extraction from structured predictions

## Dependencies

- `pyo3`: Python bindings
- `anyhow`: Error handling
- `serde`: Serialization
- `serde_json`: JSON utilities
