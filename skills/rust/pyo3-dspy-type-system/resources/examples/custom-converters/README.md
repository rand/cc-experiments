# Custom Type Converters Example

This example demonstrates how to build custom type converters for domain-specific types in PyO3, enabling seamless conversion between Rust and Python for complex data structures.

## Overview

The example implements custom converters for academic document processing types:
- **Document**: Represents a document with metadata (title, content, source, timestamp)
- **Citation**: Represents a citation with references to other documents
- Custom datetime handling with `chrono`
- Bidirectional conversion (Rust ↔ Python)

## Key Concepts

### Custom Conversion Traits

**ToPyDict**: Convert Rust types to Python dictionaries
```rust
trait ToPyDict {
    fn to_py_dict(&self, py: Python) -> PyResult<PyObject>;
}
```

**FromPyAny**: Convert Python objects to Rust types
```rust
trait FromPyAny: Sized {
    fn from_py_any(obj: &PyAny) -> PyResult<Self>;
}
```

### DateTime Handling

Uses `chrono` for datetime manipulation:
- Store as `DateTime<Utc>` in Rust
- Convert to ISO 8601 strings for Python
- Parse from various Python formats (string, float timestamp)

### Nested Custom Types

Citations contain references to Documents, demonstrating:
- Recursive type conversion
- Nested struct handling
- Complex object graphs

## Building and Running

### Quick Start (Python Standalone)

To see the concepts in action without building the Rust extension:

```bash
# Run the Python-only demonstration
python3 test_standalone.py
```

This demonstrates the same type conversions and operations that the Rust implementation provides, showing the expected behavior.

### Building the Rust Library

The library requires building as a Python extension module:

```bash
# Check that the library compiles
cargo check --lib

# Build as Python extension (requires maturin)
pip install maturin
maturin develop

# Then use from Python
python3 -c "
import custom_converters
doc = custom_converters.create_sample_document()
print(f'Document: {doc}')
citation = custom_converters.create_citation_from_doc(doc)
print(f'Citation: {citation}')
"
```

### Building with Maturin

For a production-ready Python package:

```bash
# Install maturin
pip install maturin

# Build wheel
maturin build --release

# Or install directly into current environment
maturin develop --release
```

## Code Structure

### Document Type

```rust
pub struct Document {
    pub title: String,
    pub content: String,
    pub source: String,
    pub timestamp: DateTime<Utc>,
    pub metadata: HashMap<String, String>,
}
```

**Features**:
- Rich metadata storage
- UTC timestamp tracking
- Source attribution
- Extensible metadata map

### Citation Type

```rust
pub struct Citation {
    pub text: String,
    pub documents: Vec<Document>,
    pub citation_style: String,
    pub page_numbers: Option<Vec<u32>>,
}
```

**Features**:
- Multiple document references
- Style specification (APA, MLA, etc.)
- Optional page number tracking
- Nested Document conversion

## Conversion Examples

### Rust to Python

```rust
// Convert Document to Python dict
impl ToPyDict for Document {
    fn to_py_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("title", &self.title)?;
        dict.set_item("content", &self.content)?;
        dict.set_item("source", &self.source)?;
        dict.set_item("timestamp", self.timestamp.to_rfc3339())?;
        dict.set_item("metadata", self.metadata.clone())?;
        Ok(dict.into())
    }
}
```

### Python to Rust

```rust
// Convert Python dict to Document
impl FromPyAny for Document {
    fn from_py_any(obj: &PyAny) -> PyResult<Self> {
        let title = obj.get_item("title")?.extract::<String>()?;
        let content = obj.get_item("content")?.extract::<String>()?;
        let source = obj.get_item("source")?.extract::<String>()?;

        // Parse timestamp from string or float
        let timestamp_obj = obj.get_item("timestamp")?;
        let timestamp = parse_timestamp(timestamp_obj)?;

        let metadata = obj.get_item("metadata")?
            .extract::<HashMap<String, String>>()?;

        Ok(Document {
            title,
            content,
            source,
            timestamp,
            metadata,
        })
    }
}
```

## Error Handling

The converters implement robust error handling:

```rust
fn parse_timestamp(obj: &PyAny) -> PyResult<DateTime<Utc>> {
    if let Ok(s) = obj.extract::<String>() {
        // Try parsing ISO 8601
        DateTime::parse_from_rfc3339(&s)
            .map(|dt| dt.with_timezone(&Utc))
            .map_err(|e| PyErr::new::<PyValueError, _>(
                format!("Invalid ISO 8601 timestamp: {}", e)
            ))
    } else if let Ok(timestamp) = obj.extract::<f64>() {
        // Parse Unix timestamp
        let secs = timestamp.trunc() as i64;
        let nsecs = ((timestamp.fract() * 1_000_000_000.0) as u32);
        DateTime::from_timestamp(secs, nsecs)
            .ok_or_else(|| PyErr::new::<PyValueError, _>(
                "Invalid Unix timestamp"
            ))
    } else {
        Err(PyErr::new::<PyTypeError, _>(
            "timestamp must be string (ISO 8601) or float (Unix)"
        ))
    }
}
```

## Extensibility

### Adding New Domain Types

1. Define the Rust struct
2. Implement `ToPyDict` for Rust → Python
3. Implement `FromPyAny` for Python → Rust
4. Add PyO3 wrapper functions for creation/manipulation

### Supporting New Formats

Extend the converters to handle additional formats:
- JSON serialization via `serde_json`
- Binary formats via `bincode`
- Custom wire protocols

### Type Validation

Add validation logic in `FromPyAny`:
```rust
impl FromPyAny for Document {
    fn from_py_any(obj: &PyAny) -> PyResult<Self> {
        // ... extract fields ...

        // Validate
        if title.is_empty() {
            return Err(PyErr::new::<PyValueError, _>(
                "Document title cannot be empty"
            ));
        }

        if content.len() > 1_000_000 {
            return Err(PyErr::new::<PyValueError, _>(
                "Document content exceeds maximum length"
            ));
        }

        Ok(Document { /* ... */ })
    }
}
```

## Performance Considerations

### Zero-Copy Operations

Where possible, use references instead of cloning:
```rust
// Efficient: borrow the string
dict.set_item("title", self.title.as_str())?;

// Less efficient: clone the string
dict.set_item("title", self.title.clone())?;
```

### Lazy Conversion

Convert nested types only when accessed:
```rust
#[pyclass]
pub struct LazyDocument {
    inner: Document,
    cached_dict: OnceCell<PyObject>,
}

#[pymethods]
impl LazyDocument {
    fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.cached_dict
            .get_or_try_init(|| self.inner.to_py_dict(py))
            .cloned()
    }
}
```

### Bulk Operations

For collections, use iterators efficiently:
```rust
pub fn process_documents(docs: Vec<Document>) -> Vec<ProcessedDoc> {
    docs.into_par_iter()  // Parallel iterator
        .map(|doc| process(doc))
        .collect()
}
```

## Testing Strategies

### Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_document_roundtrip() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let doc = create_sample_document();
            let py_dict = doc.to_py_dict(py).unwrap();
            let py_any = py_dict.as_ref(py);
            let roundtrip = Document::from_py_any(py_any).unwrap();

            assert_eq!(doc.title, roundtrip.title);
            assert_eq!(doc.content, roundtrip.content);
        });
    }
}
```

### Integration Tests

```python
# tests/test_converters.py
import custom_converters
import datetime

def test_document_creation():
    doc = custom_converters.create_sample_document()
    assert doc['title'] == 'Sample Document'
    assert 'timestamp' in doc

def test_citation_with_documents():
    doc = custom_converters.create_sample_document()
    citation = custom_converters.create_citation_from_doc(doc)
    assert len(citation['documents']) == 1
    assert citation['documents'][0]['title'] == doc['title']
```

## Use Cases

### Academic Document Processing
- Parse and validate research papers
- Extract and manage citations
- Build document graphs

### Content Management Systems
- Store document metadata
- Track revisions and timestamps
- Maintain source attribution

### Data Pipeline Integration
- Convert between storage formats
- Validate incoming data
- Transform for ML processing

## Related Examples

- **basic-types**: Foundation type conversion patterns
- **collections**: Converting collections of custom types
- **async-conversion**: Async conversion for I/O-bound operations
- **validation**: Advanced validation patterns

## Further Reading

- [PyO3 Type Conversion Guide](https://pyo3.rs/latest/conversions)
- [chrono Documentation](https://docs.rs/chrono/latest/chrono/)
- [Python datetime Documentation](https://docs.python.org/3/library/datetime.html)
- [Rust to Python Type Mapping](https://pyo3.rs/latest/conversions/tables)
