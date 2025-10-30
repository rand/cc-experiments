"""
Memory leak detection tests
"""
import gc
import sys
import pytest
from memory_testing import (
    process_list,
    create_and_process,
    create_dict,
    get_refcount,
)


class TestReferenceCount:
    """Test reference counting"""

    def test_list_refcount_preserved(self):
        """Test that processing doesn't leak references."""
        data = [1, 2, 3, 4, 5]
        initial_refcount = sys.getrefcount(data)

        process_list(data)

        final_refcount = sys.getrefcount(data)
        assert final_refcount == initial_refcount

    def test_multiple_calls_no_leak(self):
        """Test repeated calls don't accumulate references."""
        data = [1, 2, 3]
        initial_refcount = sys.getrefcount(data)

        for _ in range(100):
            process_list(data)

        gc.collect()
        final_refcount = sys.getrefcount(data)
        assert final_refcount == initial_refcount

    def test_dict_creation(self):
        """Test dictionary creation and reference count."""
        d = create_dict()
        assert isinstance(d, dict)
        assert d["key"] == "value"

        refcount = sys.getrefcount(d)
        assert refcount >= 1


class TestMemoryPatterns:
    """Test common memory patterns"""

    def test_create_and_discard(self):
        """Test creating and discarding objects."""
        for _ in range(1000):
            result = create_and_process()
            assert result == 5

    def test_large_objects(self):
        """Test with large objects."""
        large_list = list(range(100000))
        initial_refcount = sys.getrefcount(large_list)

        process_list(large_list)

        final_refcount = sys.getrefcount(large_list)
        assert final_refcount == initial_refcount

    def test_gc_cleanup(self):
        """Test that GC properly cleans up."""
        objects = []
        for _ in range(100):
            d = create_dict()
            objects.append(d)

        objects.clear()
        gc.collect()
