# Example 07: Testing GIL Release and Thread Safety

Test GIL release patterns and thread safety in PyO3 extensions.

## What You'll Learn

- Testing GIL release with `allow_threads`
- Thread safety verification
- Parallel execution testing
- Deadlock prevention
- Race condition detection

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install maturin pytest
maturin develop
```

## Running Tests

```bash
cargo test
pytest tests/ -v
```

## Key Concepts

### GIL Release Testing

```rust
#[test]
fn test_gil_released() {
    Python::with_gil(|py| {
        py.allow_threads(|| {
            // GIL is released here
            std::thread::sleep(Duration::from_millis(100));
        });
    });
}
```
