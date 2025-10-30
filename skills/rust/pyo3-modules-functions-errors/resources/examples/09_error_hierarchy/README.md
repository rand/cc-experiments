# Example 09: Complete Error Hierarchy with Context

Demonstrates professional error handling with hierarchical exceptions and context.

## Error Hierarchy

```
AppError (base)
├── DatabaseError
│   ├── ConnectionError
│   ├── QueryError
│   └── TransactionError
├── NetworkError
│   ├── TimeoutError
│   └── HttpError
└── ValidationError
    ├── SchemaError
    └── ConstraintError
```

## Features

- Multi-level exception hierarchies
- Context-aware errors with additional information
- Error codes for programmatic handling
- Catching base exceptions catches all derived types

## Usage

```python
import error_hierarchy as eh

try:
    eh.connect_database("localhost", 9999)
except eh.ConnectionError as e:
    print(f"Connection failed: {e}")
except eh.DatabaseError as e:
    print(f"Database error: {e}")
except eh.AppError as e:
    print(f"Application error: {e}")
```

Build: `maturin develop && pytest test_example.py -v`
