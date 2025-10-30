# Example 06: Custom Collection

Build custom collection types that combine features from multiple data structures.

## Components

- **HybridCollection**: Combines list-like indexing with dict-like key lookup and set-like uniqueness
- **PriorityQueue**: Priority-based queue with automatic sorting
- **CircularBuffer**: Fixed-size ring buffer that overwrites oldest data

## Usage

```python
import custom_collection

# Hybrid collection
hc = custom_collection.HybridCollection()
hc.add("item1")
hc.get_by_index(0)      # List-like access
hc.get_index("item1")   # Dict-like lookup
"item1" in hc           # Set-like membership

# Priority queue
pq = custom_collection.PriorityQueue()
pq.push(10, "important")
pq.push(1, "not urgent")
pq.pop()  # Returns (10, "important")

# Circular buffer
cb = custom_collection.CircularBuffer(capacity=100)
cb.push(value)
```

Build: `maturin develop && python test_example.py`
