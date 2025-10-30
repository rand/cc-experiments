# Example 05: Concurrent Tasks

Demonstrates concurrent task execution patterns including parallel execution, racing, error handling, work stealing, and concurrency limiting.

## Building
```bash
maturin develop
```

## Running
```bash
pytest test_example.py
```

## Key Concepts
- Parallel task execution with `join_all`
- Task racing with `select_all`
- Error handling with `try_join_all`
- Work-stealing pattern
- Semaphore-based concurrency limiting
