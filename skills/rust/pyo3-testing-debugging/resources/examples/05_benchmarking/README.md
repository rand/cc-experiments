# Example 05: Performance Benchmarking

Benchmark PyO3 extensions using criterion (Rust) and pytest-benchmark (Python).

## What You'll Learn

- Benchmarking with criterion
- Python benchmarking with pytest-benchmark
- Comparing Rust vs Python performance
- Detecting performance regressions
- Profiling bottlenecks

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install maturin pytest pytest-benchmark
maturin develop --release
```

## Running Benchmarks

```bash
# Rust benchmarks
cargo bench

# Python benchmarks
pytest tests/test_benchmarks.py --benchmark-only

# Compare with baseline
pytest tests/test_benchmarks.py --benchmark-compare --benchmark-autosave
```

## Expected Output

```
Rust:
sum_1000     time: [2.156 µs 2.178 µs 2.203 µs]
sum_100000   time: [201.45 µs 203.12 µs 204.89 µs]

Python:
test_benchmark_sum         Mean: 5.23 µs
test_benchmark_vs_python   Mean Rust: 2.18 µs, Python: 45.67 µs (20.9x faster)
```
