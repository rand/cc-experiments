# Module State Example

This example demonstrates how to wrap DSPy modules in stateful Rust structs that maintain query history and state across multiple invocations.

## Purpose

Shows patterns for:
- Wrapping DSPy modules with `Py<PyAny>`
- Maintaining query history in Rust
- State serialization/deserialization
- GIL management for stateful operations
- Building persistent conversational AI systems

## Architecture

```
┌─────────────────────────────────────┐
│     Stateful Module Wrapper         │
│  (Rust struct with Py<PyAny>)       │
├─────────────────────────────────────┤
│  • Module reference (Py<PyAny>)     │
│  • Query history (Vec<QueryRecord>) │
│  • State metadata                   │
│  • Serialization support            │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│      Python GIL Context             │
│  (Acquired for each query)          │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│      DSPy Module Instance           │
│  (Python-side stateful object)      │
└─────────────────────────────────────┘
```

## Key Patterns

### 1. Storing Python Objects in Rust

```rust
pub struct StatefulModule {
    module: Py<PyAny>,           // Python object reference
    history: Vec<QueryRecord>,    // Rust-side state
}
```

The `Py<PyAny>` type allows holding Python objects across GIL acquisition boundaries. It's:
- Thread-safe (can be sent between threads)
- GIL-independent (doesn't require active GIL)
- Reference-counted on Python side

### 2. GIL Management Pattern

```rust
// Acquire GIL for Python interaction
Python::with_gil(|py| {
    // Access module through .bind(py)
    let result = self.module.bind(py).call_method1("forward", (query,))?;
    // ... process result ...
    Ok(())
})
```

Always use `with_gil` for scoped GIL acquisition and `bind(py)` to access the wrapped Python object.

### 3. State Tracking

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryRecord {
    pub timestamp: String,
    pub query: String,
    pub response: String,
    pub metadata: HashMap<String, String>,
}
```

Maintain Rust-side history separate from Python object state.

### 4. Serialization for Persistence

```rust
pub fn save_state(&self, path: &str) -> Result<()> {
    let state = ModuleState {
        history: self.history.clone(),
        created_at: self.created_at.clone(),
        query_count: self.query_count,
    };
    let json = serde_json::to_string_pretty(&state)?;
    std::fs::write(path, json)?;
    Ok(())
}
```

Serialize Rust-side state to JSON for persistence across sessions.

## Building and Running

```bash
# Build the example
cargo build --release

# Run with default DSPy setup
cargo run

# The program will:
# 1. Initialize a DSPy module
# 2. Execute multiple queries
# 3. Track history
# 4. Save state to JSON
# 5. Demonstrate state loading
```

## Output Example

```
Initializing stateful DSPy module...
Module initialized with signature: question -> answer

Query 1: What is machine learning?
Response: Machine learning is a subset of artificial intelligence...
History entries: 1

Query 2: What are neural networks?
Response: Neural networks are computing systems inspired by biological...
History entries: 2

Saving module state...
State saved to: module_state.json

Loading state from file...
Loaded state with 2 history entries
```

## State File Format

```json
{
  "history": [
    {
      "timestamp": "2025-10-30T10:30:45Z",
      "query": "What is machine learning?",
      "response": "Machine learning is...",
      "metadata": {
        "model": "gpt-3.5-turbo",
        "tokens": "150"
      }
    }
  ],
  "created_at": "2025-10-30T10:30:40Z",
  "query_count": 2
}
```

## Advanced Usage

### Custom Metadata

```rust
let mut metadata = HashMap::new();
metadata.insert("model".to_string(), "gpt-4".to_string());
metadata.insert("temperature".to_string(), "0.7".to_string());

stateful_module.query_with_metadata("question", metadata)?;
```

### State Filtering

```rust
// Get recent queries
let recent = stateful_module.get_history(5);

// Search history
let results = stateful_module.search_history("neural networks");
```

### State Reset

```rust
// Clear history while keeping module
stateful_module.clear_history();

// Full reset
stateful_module.reset();
```

## Error Handling

The example demonstrates comprehensive error handling:

```rust
pub enum ModuleError {
    PythonError(PyErr),
    SerializationError(serde_json::Error),
    IoError(std::io::Error),
    StateError(String),
}
```

All operations return `Result<T, ModuleError>` for safe error propagation.

## GIL Safety Notes

1. **Never hold GIL across await points** - This example is synchronous by design
2. **Use `Py<PyAny>` for storage** - Don't try to store `&PyAny` references
3. **Acquire GIL only when needed** - Keep GIL acquisition scoped
4. **Clone data out of GIL** - Extract Rust data before releasing GIL

## Performance Considerations

- **GIL overhead**: Each query acquires GIL once
- **History growth**: Consider trimming old entries
- **Serialization cost**: JSON encoding scales with history size
- **Memory**: `Py<PyAny>` keeps Python object alive

## Integration Patterns

### Web Server

```rust
// Store StatefulModule in web application state
struct AppState {
    module: Arc<Mutex<StatefulModule>>,
}

// Handle requests with state preservation
async fn handle_query(state: Arc<AppState>, query: String) -> Result<String> {
    let mut module = state.module.lock().await;
    module.query(&query)
}
```

### Background Processing

```rust
// Process queries in background with periodic state saves
loop {
    if let Some(query) = queue.pop() {
        module.query(&query)?;
    }

    if module.query_count % 10 == 0 {
        module.save_state("checkpoint.json")?;
    }
}
```

## References

- [PyO3 Documentation on Py<T>](https://pyo3.rs/latest/class.html#pyt-and-pyref)
- [DSPy Module Documentation](https://dspy-docs.vercel.app/)
- [Serde JSON Serialization](https://docs.serde.rs/serde_json/)

## Troubleshooting

### "GIL was already acquired"

Ensure you're not nesting `with_gil` calls:

```rust
// Bad
Python::with_gil(|py| {
    Python::with_gil(|py2| { ... })  // Error!
});

// Good
Python::with_gil(|py| {
    self.module.bind(py).call_method(...)?;
});
```

### Module state not persisting

Verify serialization includes all necessary fields:

```rust
#[derive(Serialize, Deserialize)]
pub struct ModuleState {
    pub history: Vec<QueryRecord>,
    pub created_at: String,
    pub query_count: usize,
    // Add any custom fields here
}
```

### Memory growth

Implement history trimming:

```rust
pub fn trim_history(&mut self, max_entries: usize) {
    if self.history.len() > max_entries {
        self.history.drain(0..self.history.len() - max_entries);
    }
}
```
