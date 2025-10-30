"""Tests for callback_functions example."""
import pytest
import callback_functions as cf

def test_map_with_callback():
    """Test mapping with callback."""
    items = [1, 2, 3, 4, 5]
    result = cf.map_with_callback(items, lambda x: x * 2)
    assert result == [2, 4, 6, 8, 10]

def test_filter_with_callback():
    """Test filtering with predicate."""
    items = [1, 2, 3, 4, 5, 6]
    result = cf.filter_with_callback(items, lambda x: x % 2 == 0)
    assert result == [2, 4, 6]

def test_reduce_with_callback():
    """Test reducing with callback."""
    items = [1, 2, 3, 4, 5]
    result = cf.reduce_with_callback(items, lambda acc, x: acc + x, 0)
    assert result == 15

def test_process_with_error_callback():
    """Test processing with error handling."""
    items = [1, 2, 3, 4, 5]
    errors = []
    
    def processor(x):
        if x == 3:
            raise ValueError("Bad value")
        return x * 2
    
    def error_handler(x):
        errors.append(x)
    
    result = cf.process_with_error_callback(items, processor, error_handler)
    assert result == [2, 4, 8, 10]
    assert errors == [3]

def test_sort_with_callback():
    """Test sorting with key function."""
    items = [5, 2, 8, 1, 9]
    result = cf.sort_with_callback(items, lambda x: -x)  # Reverse sort
    assert result == [9, 8, 5, 2, 1]

def test_chain_callbacks():
    """Test chaining multiple callbacks."""
    callbacks = [
        lambda x: x + 10,
        lambda x: x * 2,
        lambda x: x - 5,
    ]
    result = cf.chain_callbacks(5, callbacks)
    assert result == 25  # (5 + 10) * 2 - 5 = 25

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
