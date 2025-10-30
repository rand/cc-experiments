#!/bin/bash
set -e

echo "=== Production Test Suite ==="
echo

echo "1. Running Rust unit tests..."
cargo test --quiet
echo "   ✓ Rust tests passed"
echo

echo "2. Running Rust property tests..."
cargo test proptest --quiet
echo "   ✓ Property tests passed"
echo

echo "3. Checking Rust formatting..."
cargo fmt -- --check
echo "   ✓ Formatting check passed"
echo

echo "4. Running Clippy..."
cargo clippy --quiet -- -D warnings
echo "   ✓ Clippy passed"
echo

echo "5. Running Python unit tests..."
pytest tests/test_unit.py -v -m unit
echo "   ✓ Unit tests passed"
echo

echo "6. Running Python integration tests..."
pytest tests/test_integration.py -v -m integration
echo "   ✓ Integration tests passed"
echo

echo "7. Generating coverage report..."
pytest tests/ --cov=production_suite --cov-report=term-missing --cov-report=html
echo "   ✓ Coverage report generated"
echo

echo "=== All tests passed! ==="
