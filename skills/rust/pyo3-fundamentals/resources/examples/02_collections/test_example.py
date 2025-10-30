"""
Test suite for collections PyO3 module.

Run with: pytest test_example.py -v
Build first: maturin develop
"""

import pytest
import collections as col


def test_sum_list():
    """Test list summing."""
    assert col.sum_list([1, 2, 3, 4, 5]) == 15
    assert col.sum_list([]) == 0
    assert col.sum_list([-1, 1]) == 0


def test_double_list():
    """Test list transformation."""
    assert col.double_list([1, 2, 3]) == [2, 4, 6]
    assert col.double_list([]) == []
    assert col.double_list([-2, 0, 2]) == [-4, 0, 4]


def test_join_strings():
    """Test string list operations."""
    assert col.join_strings(["Hello", "World"], " ") == "Hello World"
    assert col.join_strings(["a", "b", "c"], ",") == "a,b,c"
    assert col.join_strings([], "-") == ""


def test_filter_positive():
    """Test list filtering."""
    assert col.filter_positive([1, -2, 3, -4, 5]) == [1, 3, 5]
    assert col.filter_positive([-1, -2, -3]) == []
    assert col.filter_positive([1, 2, 3]) == [1, 2, 3]


def test_sum_dict_values():
    """Test dictionary value operations."""
    assert col.sum_dict_values({"a": 1, "b": 2, "c": 3}) == 6
    assert col.sum_dict_values({}) == 0


def test_invert_dict():
    """Test dictionary inversion."""
    result = col.invert_dict({"a": "x", "b": "y"})
    assert result == {"x": "a", "y": "b"}


def test_get_with_default():
    """Test dictionary access with defaults."""
    data = {"a": 10, "b": 20}
    assert col.get_with_default(data, "a", 0) == 10
    assert col.get_with_default(data, "c", 99) == 99


def test_min_max():
    """Test tuple return values."""
    assert col.min_max([3, 1, 4, 1, 5]) == (1, 5)
    assert col.min_max([42]) == (42, 42)

    with pytest.raises(ValueError, match="List cannot be empty"):
        col.min_max([])


def test_tuple_sum():
    """Test tuple input."""
    assert col.tuple_sum((10, 20)) == 30
    assert col.tuple_sum((-5, 5)) == 0


def test_create_person():
    """Test creating tuples."""
    person = col.create_person("Alice", 30, 95.5)
    assert person == ("Alice", 30, 95.5)
    assert isinstance(person, tuple)


def test_unique_elements():
    """Test set creation from list."""
    result = col.unique_elements([1, 2, 2, 3, 3, 3])
    assert result == {1, 2, 3}


def test_set_intersection():
    """Test set intersection."""
    result = col.set_intersection({1, 2, 3}, {2, 3, 4})
    assert result == {2, 3}


def test_set_union():
    """Test set union."""
    result = col.set_union({"a", "b"}, {"b", "c"})
    assert result == {"a", "b", "c"}


def test_set_difference():
    """Test set difference."""
    result = col.set_difference({1, 2, 3}, {2, 3, 4})
    assert result == {1}


def test_sum_tuples():
    """Test nested collection - list of tuples."""
    result = col.sum_tuples([(1, 2), (3, 4), (5, 6)])
    assert result == [3, 7, 11]


def test_flatten_dict_lists():
    """Test nested collection - dict of lists."""
    data = {"a": [1, 2], "b": [3, 4, 5], "c": [6]}
    result = col.flatten_dict_lists(data)
    assert sorted(result) == [1, 2, 3, 4, 5, 6]


def test_reverse_in_place():
    """Test PyList creation."""
    result = col.reverse_in_place([1, 2, 3, 4, 5])
    assert result == [5, 4, 3, 2, 1]
    assert isinstance(result, list)


def test_merge_dicts():
    """Test PyDict creation and merging."""
    result = col.merge_dicts({"a": 1, "b": 2}, {"c": 3, "b": 99})
    # Second dict values should overwrite
    assert result["a"] == 1
    assert result["b"] == 99
    assert result["c"] == 3


def test_transpose_data():
    """Test complex data transformation."""
    records = [
        {"name": 1, "age": 25, "score": 90},
        {"name": 2, "age": 30, "score": 85},
        {"name": 3, "age": 28, "score": 95},
    ]
    result = col.transpose_data(records)
    assert result == {
        "name": [1, 2, 3],
        "age": [25, 30, 28],
        "score": [90, 85, 95],
    }


def test_group_by_first_letter():
    """Test grouping operations."""
    words = ["apple", "apricot", "banana", "blueberry", "cherry"]
    result = col.group_by_first_letter(words)
    assert result["a"] == ["apple", "apricot"]
    assert result["b"] == ["banana", "blueberry"]
    assert result["c"] == ["cherry"]


def test_empty_collections():
    """Test handling of empty collections."""
    assert col.sum_list([]) == 0
    assert col.double_list([]) == []
    assert col.join_strings([], ",") == ""
    assert col.sum_dict_values({}) == 0
    assert col.flatten_dict_lists({}) == []


def test_type_errors():
    """Test that incorrect types raise appropriate errors."""
    with pytest.raises(TypeError):
        col.sum_list("not a list")

    with pytest.raises(TypeError):
        col.sum_dict_values([1, 2, 3])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
