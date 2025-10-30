"""
Test suite for fastapi_basic PyO3 module.

Run with: pytest test_example.py -v
Build first: maturin develop
"""

import pytest
import fastapi_basic


def test_compute_magnitude():
    """Test vector magnitude computation."""
    assert abs(fastapi_basic.compute_magnitude([3.0, 4.0]) - 5.0) < 1e-10
    assert abs(fastapi_basic.compute_magnitude([1.0, 1.0, 1.0]) - 1.732050808) < 1e-6

    with pytest.raises(ValueError, match="Data cannot be empty"):
        fastapi_basic.compute_magnitude([])


def test_process_batch():
    """Test batch processing with filtering and transformation."""
    filtered, sum_val, count = fastapi_basic.process_batch([1.0, 2.0, 3.0, 4.0], 2.0)
    assert filtered == [6.0, 8.0]  # 3*2, 4*2
    assert sum_val == 14.0
    assert count == 2

    # All values below threshold
    filtered, sum_val, count = fastapi_basic.process_batch([1.0, 2.0], 5.0)
    assert filtered == []
    assert sum_val == 0.0
    assert count == 0


def test_normalize_email():
    """Test email normalization."""
    assert fastapi_basic.normalize_email("  Test@Example.COM  ") == "test@example.com"
    assert fastapi_basic.normalize_email("user@domain.org") == "user@domain.org"

    with pytest.raises(ValueError, match="missing @"):
        fastapi_basic.normalize_email("notanemail")

    with pytest.raises(ValueError, match="too short"):
        fastapi_basic.normalize_email("a@")


def test_compute_stats():
    """Test statistical computations."""
    mean, std_dev, min_val, max_val = fastapi_basic.compute_stats([1.0, 2.0, 3.0, 4.0, 5.0])
    assert mean == 3.0
    assert abs(std_dev - 1.4142135) < 1e-6
    assert min_val == 1.0
    assert max_val == 5.0

    with pytest.raises(ValueError, match="empty data"):
        fastapi_basic.compute_stats([])


def test_analyze_text():
    """Test text analysis."""
    char_count, word_count, line_count = fastapi_basic.analyze_text("Hello world\nTest line")
    assert char_count == 21  # Including newline
    assert word_count == 4
    assert line_count == 2

    # Empty string
    char_count, word_count, line_count = fastapi_basic.analyze_text("")
    assert char_count == 0
    assert word_count == 0
    assert line_count == 0


def test_hash_string():
    """Test string hashing."""
    hash1 = fastapi_basic.hash_string("test")
    hash2 = fastapi_basic.hash_string("test")
    hash3 = fastapi_basic.hash_string("different")

    assert hash1 == hash2  # Same input, same hash
    assert hash1 != hash3  # Different input, different hash
    assert isinstance(hash1, int)


def test_validate_user_id():
    """Test user ID validation."""
    assert fastapi_basic.validate_user_id("user123") is True
    assert fastapi_basic.validate_user_id("abc") is True
    assert fastapi_basic.validate_user_id("ab") is False  # Too short
    assert fastapi_basic.validate_user_id("a" * 21) is False  # Too long
    assert fastapi_basic.validate_user_id("user@123") is False  # Invalid chars


def test_celsius_to_fahrenheit():
    """Test temperature conversion."""
    assert fastapi_basic.celsius_to_fahrenheit(0.0) == 32.0
    assert fastapi_basic.celsius_to_fahrenheit(100.0) == 212.0
    assert abs(fastapi_basic.celsius_to_fahrenheit(37.0) - 98.6) < 0.1


def test_factorial():
    """Test factorial computation."""
    assert fastapi_basic.factorial(0) == 1
    assert fastapi_basic.factorial(1) == 1
    assert fastapi_basic.factorial(5) == 120
    assert fastapi_basic.factorial(10) == 3628800

    with pytest.raises(ValueError, match="too large"):
        fastapi_basic.factorial(21)


def test_is_prime():
    """Test primality testing."""
    assert fastapi_basic.is_prime(2) is True
    assert fastapi_basic.is_prime(3) is True
    assert fastapi_basic.is_prime(17) is True
    assert fastapi_basic.is_prime(4) is False
    assert fastapi_basic.is_prime(1) is False
    assert fastapi_basic.is_prime(0) is False


def test_fastapi_integration():
    """Test integration pattern with FastAPI."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.post("/compute")
    async def compute_endpoint(data: list[float]):
        result = fastapi_basic.compute_magnitude(data)
        return {"magnitude": result}

    @app.post("/stats")
    async def stats_endpoint(data: list[float]):
        mean, std_dev, min_val, max_val = fastapi_basic.compute_stats(data)
        return {
            "mean": mean,
            "std_dev": std_dev,
            "min": min_val,
            "max": max_val
        }

    client = TestClient(app)

    # Test compute endpoint
    response = client.post("/compute", json=[3.0, 4.0])
    assert response.status_code == 200
    assert abs(response.json()["magnitude"] - 5.0) < 1e-10

    # Test stats endpoint
    response = client.post("/stats", json=[1.0, 2.0, 3.0, 4.0, 5.0])
    assert response.status_code == 200
    data = response.json()
    assert data["mean"] == 3.0
    assert abs(data["std_dev"] - 1.4142135) < 1e-6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
