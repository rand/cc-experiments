"""Tests for production_api example."""
import pytest
import production_api as api

def test_version_and_constants():
    """Test version and constants."""
    assert hasattr(api, "VERSION")
    assert hasattr(api, "MAX_BATCH_SIZE")
    assert api.get_version() == api.VERSION
    assert api.get_max_batch_size() == api.MAX_BATCH_SIZE

def test_config_creation():
    """Test configuration creation."""
    config = api.Config()
    assert config.debug is False
    assert config.max_retries == 3
    assert config.timeout == 30
    
    config = api.create_default_config()
    assert "Config" in repr(config)

def test_config_settings():
    """Test configuration settings."""
    config = api.Config()
    config.set_setting("key", "value")
    assert config.get_setting("key") == "value"
    assert config.get_setting("missing") is None

def test_config_validation():
    """Test configuration validation."""
    config = api.Config()
    config.validate()  # Should pass
    
    config.max_retries = 20
    with pytest.raises(api.ConfigurationError):
        config.validate()

def test_process_batch():
    """Test batch processing."""
    items = ["item1", "item2", "item3"]
    config = api.Config()
    result = api.processing.process_batch(items, config)
    
    assert result.total == 3
    assert result.success_count == 3
    assert result.error_count == 0
    assert result.success_rate() == 1.0

def test_process_batch_with_errors():
    """Test batch processing with validation errors."""
    items = ["valid", "", "also valid", "x" * 101]  # Empty and too long
    config = api.Config()
    result = api.processing.process_batch(items, config)
    
    assert result.total == 4
    assert result.success_count == 2
    assert result.error_count == 2

def test_process_batch_size_limit():
    """Test batch size limit."""
    items = ["x"] * (api.MAX_BATCH_SIZE + 1)
    config = api.Config()
    
    with pytest.raises(api.ProcessingError):
        api.processing.process_batch(items, config)

def test_transform_operations():
    """Test transformation operations."""
    items = ["Hello", "World"]
    
    result = api.processing.transform(items, "uppercase")
    assert result == ["HELLO", "WORLD"]
    
    result = api.processing.transform(items, "lowercase")
    assert result == ["hello", "world"]
    
    result = api.processing.transform(items, "reverse")
    assert result == ["olleH", "dlroW"]

def test_transform_invalid_operation():
    """Test invalid transformation operation."""
    with pytest.raises(ValueError):
        api.processing.transform(["test"], "invalid_op")

def test_filter_by_length():
    """Test filtering by length."""
    items = ["a", "bb", "ccc", "dddd", "eeeee"]
    result = api.processing.filter_by_length(items, 2, 4)
    assert result == ["bb", "ccc", "dddd"]

def test_filter_invalid_range():
    """Test filter with invalid range."""
    with pytest.raises(ValueError):
        api.processing.filter_by_length(["test"], 10, 5)

def test_compute_stats():
    """Test statistics computation."""
    numbers = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = api.stats.compute_stats(numbers)
    
    assert stats["mean"] == 3.0
    assert stats["median"] == 3.0
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0
    assert stats["count"] == 5

def test_compute_stats_empty():
    """Test stats with empty list."""
    with pytest.raises(ValueError):
        api.stats.compute_stats([])

def test_exception_hierarchy():
    """Test exception inheritance."""
    assert issubclass(api.ConfigurationError, api.ApiError)
    assert issubclass(api.ProcessingError, api.ApiError)

def test_process_result_methods():
    """Test ProcessResult methods."""
    items = ["a", "b", "", "d"]
    config = api.Config()
    result = api.processing.process_batch(items, config)
    
    errors = result.get_errors()
    assert len(errors) > 0
    assert isinstance(result.success_rate(), float)
    assert "ProcessResult" in repr(result)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
