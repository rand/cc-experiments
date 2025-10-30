"""Test suite for flask_extension PyO3 module."""

import pytest
import flask_extension


def test_compress_decompress():
    """Test compression and decompression."""
    data = b"Hello World" * 100
    compressed = flask_extension.compress_response(data, 6)
    assert len(compressed) < len(data)

    decompressed = flask_extension.decompress_request(compressed)
    assert decompressed == data


def test_query_string():
    """Test query string parsing and building."""
    query = "key1=value1&key2=value%202"
    parsed = flask_extension.parse_query_string(query)
    assert len(parsed) == 2
    assert parsed[0] == ("key1", "value1")
    assert parsed[1] == ("key2", "value 2")

    built = flask_extension.build_query_string(parsed)
    assert "key1=value1" in built
    assert "key2=value" in built


def test_hash_request():
    """Test request hashing."""
    hash1 = flask_extension.hash_request("GET", "/api/test", b"body")
    hash2 = flask_extension.hash_request("GET", "/api/test", b"body")
    hash3 = flask_extension.hash_request("POST", "/api/test", b"body")

    assert hash1 == hash2
    assert hash1 != hash3


def test_rate_limiter():
    """Test rate limiting."""
    limiter = flask_extension.RateLimiter(limit=3, window_seconds=1)

    assert limiter.check_limit("user1") is True
    assert limiter.check_limit("user1") is True
    assert limiter.check_limit("user1") is True
    assert limiter.check_limit("user1") is False

    limiter.reset("user1")
    assert limiter.check_limit("user1") is True


def test_response_timer():
    """Test response timing."""
    import time

    timer = flask_extension.ResponseTimer()
    timer.start(1)
    time.sleep(0.1)
    duration = timer.stop(1)

    assert duration >= 0.1
    assert duration < 0.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
