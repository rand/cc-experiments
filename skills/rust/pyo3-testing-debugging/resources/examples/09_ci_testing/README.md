# Example 09: Complete CI/CD Test Pipeline

Production-ready CI/CD pipeline with comprehensive testing across platforms.

## What You'll Learn

- GitHub Actions workflow setup
- Multi-platform testing (Linux, macOS, Windows)
- Multi-Python version testing
- Code coverage reporting
- Automated benchmarking
- Release automation

## Project Structure

```
09_ci_testing/
├── .github/
│   └── workflows/
│       ├── test.yml        # Main test workflow
│       ├── benchmark.yml   # Benchmark workflow
│       └── release.yml     # Release workflow
├── src/
│   └── lib.rs
├── tests/
│   └── test_ci.py
├── Cargo.toml
├── pyproject.toml
└── README.md
```

## Local Testing

```bash
# Test like CI does
python -m venv .venv
source .venv/bin/activate
pip install maturin pytest pytest-cov
maturin develop --release
cargo test
cargo fmt -- --check
cargo clippy -- -D warnings
pytest tests/ --cov=ci_testing --cov-report=xml
```

## CI Features

- Matrix testing: Python 3.8-3.12, Linux/macOS/Windows
- Rust linting: rustfmt, clippy
- Python linting: mypy, pytest
- Coverage: codecov integration
- Benchmarks: Performance tracking
- Release: Automated PyPI publishing
