# Example 02: Python Integration Tests with pytest

Learn to write comprehensive Python tests for PyO3 extensions using pytest, fixtures, and parameterized tests.

## What You'll Learn

- Writing pytest tests for PyO3 extensions
- Using fixtures for test data
- Parameterized testing with @pytest.mark.parametrize
- Testing edge cases and type errors
- Coverage reporting

## Project Structure

```
02_python_tests/
├── src/
│   └── lib.rs          # PyO3 implementation
├── tests/
│   ├── conftest.py     # pytest fixtures
│   ├── test_basic.py   # Basic functionality tests
│   └── test_parametrized.py  # Parameterized tests
├── Cargo.toml
├── pyproject.toml
└── README.md
```

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install maturin pytest pytest-cov

# Build and install
maturin develop
```

## Running Tests

```bash
# Run all Python tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=python_tests --cov-report=html

# Run specific test file
pytest tests/test_basic.py

# Run specific test
pytest tests/test_basic.py::test_statistics_basic -v

# Run tests matching pattern
pytest tests/ -k "edge_cases"
```

## Key Concepts

### 1. Fixtures

Reusable test data:

```python
@pytest.fixture
def sample_data():
    return [1.0, 2.0, 3.0, 4.0, 5.0]

def test_with_fixture(sample_data):
    result = compute_stats(sample_data)
    assert result["count"] == 5
```

### 2. Parameterized Tests

Test multiple inputs efficiently:

```python
@pytest.mark.parametrize("input_data,expected", [
    ([1, 2, 3], {"sum": 6}),
    ([0], {"sum": 0}),
    ([], {"sum": 0}),
])
def test_multiple_cases(input_data, expected):
    result = compute_stats(input_data)
    assert result["sum"] == expected["sum"]
```

### 3. Exception Testing

Verify error handling:

```python
def test_type_error():
    with pytest.raises(TypeError):
        compute_stats("invalid")
```

## Expected Output

```
tests/test_basic.py::test_statistics_basic PASSED                [ 10%]
tests/test_basic.py::test_statistics_empty PASSED                [ 20%]
tests/test_basic.py::test_statistics_single PASSED               [ 30%]
tests/test_basic.py::test_type_error PASSED                      [ 40%]
tests/test_parametrized.py::test_sum_cases[case0] PASSED         [ 50%]
tests/test_parametrized.py::test_sum_cases[case1] PASSED         [ 60%]
tests/test_parametrized.py::test_sum_cases[case2] PASSED         [ 70%]
tests/test_parametrized.py::test_edge_cases[case0] PASSED        [ 80%]
tests/test_parametrized.py::test_edge_cases[case1] PASSED        [ 90%]
tests/test_parametrized.py::test_edge_cases[case2] PASSED        [100%]

---------- coverage: platform darwin, python 3.11.5 -----------
Name                   Stmts   Miss  Cover
------------------------------------------
python_tests.py            0      0   100%
------------------------------------------
TOTAL                      0      0   100%

========== 10 passed in 0.42s ==========
```

## Next Steps

- Move to example 03 for error handling and exception testing
- Learn about property-based testing with hypothesis
- Explore benchmarking with pytest-benchmark
