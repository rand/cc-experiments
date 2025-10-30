"""Test collection conversion functionality."""

import collection_conversion


def test_list_roundtrip():
    """Test list conversion roundtrip."""
    converter = collection_conversion.ListConverter()
    original = [1, 2, 3, 4, 5]
    result = converter.roundtrip(original)
    assert result == original


def test_list_processing():
    """Test list processing operations."""
    converter = collection_conversion.ListConverter()

    # Filter evens and double
    result = converter.process_list([1, 2, 3, 4, 5, 6])
    assert result == [4, 8, 12]


def test_nested_lists():
    """Test nested list creation."""
    converter = collection_conversion.ListConverter()
    result = converter.create_nested()
    assert result == [["a", "b"], ["c", "d"], ["e"]]


def test_dict_roundtrip():
    """Test dictionary conversion roundtrip."""
    converter = collection_conversion.DictConverter()
    original = {"a": 1, "b": 2, "c": 3}
    result = converter.roundtrip(original)
    assert result == original


def test_dict_invert():
    """Test dictionary inversion."""
    converter = collection_conversion.DictConverter()
    original = {"a": 1, "b": 2, "c": 3}
    result = converter.invert(original)
    assert result == {1: "a", 2: "b", 3: "c"}


def test_dict_merge():
    """Test dictionary merging with sum."""
    converter = collection_conversion.DictConverter()
    dict1 = {"a": 1, "b": 2}
    dict2 = {"b": 3, "c": 4}
    result = converter.merge_sum(dict1, dict2)
    assert result == {"a": 1, "b": 5, "c": 4}


def test_dict_filter():
    """Test dictionary filtering."""
    converter = collection_conversion.DictConverter()
    data = {"a": 5, "b": 10, "c": 15, "d": 3}
    result = converter.filter_values(data, 7)
    assert result == {"b": 10, "c": 15}


def test_set_roundtrip():
    """Test set conversion roundtrip."""
    converter = collection_conversion.SetConverter()
    original = {"a", "b", "c"}
    result = converter.roundtrip(original)
    assert result == original


def test_set_operations():
    """Test set operations."""
    converter = collection_conversion.SetConverter()

    set1 = {1, 2, 3, 4}
    set2 = {3, 4, 5, 6}

    # Union
    union = converter.union(set1, set2)
    assert union == {1, 2, 3, 4, 5, 6}

    # Intersection
    intersection = converter.intersection(set1, set2)
    assert intersection == {3, 4}

    # Difference
    difference = converter.difference(set1, set2)
    assert difference == {1, 2}


def test_set_deduplicate():
    """Test deduplication using sets."""
    converter = collection_conversion.SetConverter()
    duplicates = [1, 2, 2, 3, 3, 3, 4, 5, 5]
    result = converter.deduplicate(duplicates)
    assert result == [1, 2, 3, 4, 5]


def test_tuple_operations():
    """Test tuple processing."""
    data = [
        ("alice", 3, 100.0),
        ("bob", 7, 200.0),
        ("charlie", 10, 150.0),
        ("dave", 2, 300.0),
    ]

    result = collection_conversion.tuple_operations(data)

    # Should filter count > 5 and transform
    expected = [
        ("BOB", 14, 300.0),
        ("CHARLIE", 20, 225.0),
    ]

    assert len(result) == 2
    assert result[0] == expected[0]
    assert result[1] == expected[1]


def test_mixed_collections():
    """Test mixed collection types."""
    result = collection_conversion.mixed_collections()

    # Check structure
    assert "numbers" in result
    assert "tags" in result
    assert "metadata" in result

    # Check values
    assert list(result["numbers"]) == [1, 2, 3, 4, 5]
    assert result["tags"] == {"rust", "python", "pyo3"}
    assert result["metadata"]["version"] == "1.0"
    assert result["metadata"]["author"] == "PyO3"


def test_empty_collections():
    """Test handling of empty collections."""
    list_conv = collection_conversion.ListConverter()
    dict_conv = collection_conversion.DictConverter()
    set_conv = collection_conversion.SetConverter()

    assert list_conv.process_list([]) == []
    assert dict_conv.merge_sum({}, {}) == {}
    assert set_conv.union(set(), set()) == set()


if __name__ == "__main__":
    test_list_roundtrip()
    test_list_processing()
    test_nested_lists()
    test_dict_roundtrip()
    test_dict_invert()
    test_dict_merge()
    test_dict_filter()
    test_set_roundtrip()
    test_set_operations()
    test_set_deduplicate()
    test_tuple_operations()
    test_mixed_collections()
    test_empty_collections()
    print("All tests passed!")
