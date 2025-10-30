"""Test suite for caching_layer."""

import pytest
import time
import caching_layer


def test_cache_basic():
    """Test basic cache operations."""
    cache = caching_layer.Cache(ttl_seconds=60)

    cache.set("key1", b"value1")
    assert cache.get("key1") == b"value1"
    assert cache.get("key2") is None

    cache.delete("key1")
    assert cache.get("key1") is None


def test_cache_expiration():
    """Test cache expiration."""
    cache = caching_layer.Cache(ttl_seconds=1)

    cache.set("key", b"value")
    assert cache.get("key") == b"value"

    time.sleep(1.1)
    assert cache.get("key") is None


def test_lru_cache():
    """Test LRU cache."""
    cache = caching_layer.LRUCache(capacity=2)

    cache.set("key1", b"value1")
    cache.set("key2", b"value2")
    cache.set("key3", b"value3")

    assert cache.get("key1") is None  # Evicted
    assert cache.get("key2") == b"value2"
    assert cache.get("key3") == b"value3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
