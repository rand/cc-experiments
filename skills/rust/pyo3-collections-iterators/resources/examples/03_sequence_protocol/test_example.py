"""Test sequence protocol functionality."""

import sequence_protocol


def test_int_vector_basic():
    """Test basic IntVector operations."""
    vec = sequence_protocol.IntVector([1, 2, 3, 4, 5])

    # Test length
    assert len(vec) == 5

    # Test indexing
    assert vec[0] == 1
    assert vec[2] == 3
    assert vec[-1] == 5
    assert vec[-2] == 4


def test_int_vector_setitem():
    """Test setting items in IntVector."""
    vec = sequence_protocol.IntVector([1, 2, 3])

    vec[0] = 10
    assert vec[0] == 10

    vec[-1] = 30
    assert vec[2] == 30


def test_int_vector_delitem():
    """Test deleting items from IntVector."""
    vec = sequence_protocol.IntVector([1, 2, 3, 4, 5])

    del vec[2]
    assert len(vec) == 4
    assert vec[2] == 4

    del vec[-1]
    assert len(vec) == 3


def test_int_vector_iteration():
    """Test iterating over IntVector."""
    vec = sequence_protocol.IntVector([1, 2, 3, 4, 5])

    result = list(vec)
    assert result == [1, 2, 3, 4, 5]

    # Test iteration multiple times
    result2 = [x * 2 for x in vec]
    assert result2 == [2, 4, 6, 8, 10]


def test_int_vector_reversed():
    """Test reversed iteration."""
    vec = sequence_protocol.IntVector([1, 2, 3, 4, 5])

    result = list(reversed(vec))
    assert result == [5, 4, 3, 2, 1]


def test_int_vector_contains():
    """Test 'in' operator."""
    vec = sequence_protocol.IntVector([1, 2, 3, 4, 5])

    assert 3 in vec
    assert 10 not in vec


def test_int_vector_append():
    """Test appending to IntVector."""
    vec = sequence_protocol.IntVector([1, 2, 3])

    vec.append(4)
    vec.append(5)

    assert len(vec) == 5
    assert vec[-1] == 5


def test_int_vector_index_errors():
    """Test index error handling."""
    vec = sequence_protocol.IntVector([1, 2, 3])

    try:
        _ = vec[10]
        assert False, "Should raise IndexError"
    except IndexError:
        pass

    try:
        vec[10] = 100
        assert False, "Should raise IndexError"
    except IndexError:
        pass


def test_string_list_basic():
    """Test basic StringList operations."""
    lst = sequence_protocol.StringList(["a", "b", "c", "d"])

    assert len(lst) == 4
    assert lst[0] == "a"
    assert lst[-1] == "d"


def test_string_list_slicing():
    """Test StringList slicing."""
    lst = sequence_protocol.StringList(["a", "b", "c", "d", "e"])

    # Basic slice
    assert lst[1:3] == ["b", "c"]

    # Slice with negative indices
    assert lst[-3:-1] == ["c", "d"]

    # Slice with step
    assert lst[::2] == ["a", "c", "e"]

    # Slice all
    assert lst[:] == ["a", "b", "c", "d", "e"]


def test_string_list_contains():
    """Test 'in' operator for StringList."""
    lst = sequence_protocol.StringList(["apple", "banana", "cherry"])

    assert "banana" in lst
    assert "grape" not in lst


def test_string_list_append():
    """Test appending to StringList."""
    lst = sequence_protocol.StringList(["a", "b"])

    lst.append("c")
    assert len(lst) == 3
    assert lst[-1] == "c"


def test_string_list_extend():
    """Test extending StringList."""
    lst = sequence_protocol.StringList(["a", "b"])

    lst.extend(["c", "d", "e"])
    assert len(lst) == 5
    assert lst[-1] == "e"


def test_empty_collections():
    """Test empty collections."""
    vec = sequence_protocol.IntVector([])
    assert len(vec) == 0

    lst = sequence_protocol.StringList([])
    assert len(lst) == 0


def test_repr():
    """Test string representation."""
    vec = sequence_protocol.IntVector([1, 2, 3])
    assert "IntVector" in repr(vec)
    assert "1, 2, 3" in repr(vec)

    lst = sequence_protocol.StringList(["a", "b"])
    assert "StringList" in repr(lst)


def test_comprehensions():
    """Test list comprehensions."""
    vec = sequence_protocol.IntVector([1, 2, 3, 4, 5])

    # Filter
    evens = [x for x in vec if x % 2 == 0]
    assert evens == [2, 4]

    # Map
    doubled = [x * 2 for x in vec]
    assert doubled == [2, 4, 6, 8, 10]

    # Combined
    result = [x * 2 for x in vec if x > 2]
    assert result == [6, 8, 10]


if __name__ == "__main__":
    test_int_vector_basic()
    test_int_vector_setitem()
    test_int_vector_delitem()
    test_int_vector_iteration()
    test_int_vector_reversed()
    test_int_vector_contains()
    test_int_vector_append()
    test_int_vector_index_errors()
    test_string_list_basic()
    test_string_list_slicing()
    test_string_list_contains()
    test_string_list_append()
    test_string_list_extend()
    test_empty_collections()
    test_repr()
    test_comprehensions()
    print("All tests passed!")
