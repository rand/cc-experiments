# Example 06: Memory Leak Detection

Learn to detect and prevent memory leaks in PyO3 extensions using reference counting and valgrind.

## What You'll Learn

- Reference counting in PyO3
- Detecting memory leaks
- Testing with valgrind
- Using AddressSanitizer
- Reference cycle detection

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install maturin pytest
maturin develop

# Install valgrind (Linux/macOS)
# Linux: sudo apt-get install valgrind
# macOS: brew install valgrind
```

## Running Tests

```bash
# Run tests with reference counting checks
cargo test

# Run under valgrind (Linux)
valgrind --leak-check=full python -c "import memory_testing; memory_testing.run_tests()"

# Run with AddressSanitizer
RUSTFLAGS="-Z sanitizer=address" cargo +nightly build
```

## Key Concepts

### 1. Reference Counting

```rust
#[test]
fn test_no_refcount_leak() {
    Python::with_gil(|py| {
        let obj = PyList::new(py, &[1, 2, 3]);
        let initial = obj.get_refcnt();
        process(obj);
        assert_eq!(obj.get_refcnt(), initial);
    });
}
```

## Expected Output

```
test test_no_leak_simple ... ok
test test_no_leak_complex ... ok
test test_refcount_preserved ... ok
```
