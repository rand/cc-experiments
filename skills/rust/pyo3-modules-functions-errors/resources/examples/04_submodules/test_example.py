"""Tests for submodules example."""

import pytest
import submodules


def test_module_structure():
    """Test that submodules exist."""
    assert hasattr(submodules, "math")
    assert hasattr(submodules, "strings")
    assert hasattr(submodules, "collections")


def test_module_metadata():
    """Test module metadata."""
    assert hasattr(submodules, "__version__")
    assert submodules.get_version() == submodules.__version__


def test_list_submodules():
    """Test listing submodules."""
    modules = submodules.list_submodules()
    assert "math" in modules
    assert "strings" in modules
    assert "collections" in modules


# Math submodule tests
def test_math_add():
    """Test math.add function."""
    assert submodules.math.add(2, 3) == 5
    assert submodules.math.add(-1, 1) == 0


def test_math_subtract():
    """Test math.subtract function."""
    assert submodules.math.subtract(10, 3) == 7
    assert submodules.math.subtract(5, 10) == -5


def test_math_multiply():
    """Test math.multiply function."""
    assert submodules.math.multiply(4, 5) == 20
    assert submodules.math.multiply(-2, 3) == -6


def test_math_divide():
    """Test math.divide function."""
    assert submodules.math.divide(10.0, 2.0) == 5.0
    assert submodules.math.divide(7.0, 2.0) == 3.5


def test_math_divide_by_zero():
    """Test math.divide raises error on zero division."""
    with pytest.raises(ZeroDivisionError):
        submodules.math.divide(10.0, 0.0)


# Strings submodule tests
def test_strings_to_upper():
    """Test strings.to_upper function."""
    assert submodules.strings.to_upper("hello") == "HELLO"
    assert submodules.strings.to_upper("HeLLo") == "HELLO"


def test_strings_to_lower():
    """Test strings.to_lower function."""
    assert submodules.strings.to_lower("HELLO") == "hello"
    assert submodules.strings.to_lower("HeLLo") == "hello"


def test_strings_reverse():
    """Test strings.reverse function."""
    assert submodules.strings.reverse("hello") == "olleh"
    assert submodules.strings.reverse("abc") == "cba"


def test_strings_char_count():
    """Test strings.char_count function."""
    assert submodules.strings.char_count("hello") == 5
    assert submodules.strings.char_count("") == 0
    assert submodules.strings.char_count("hello world") == 11


def test_strings_is_palindrome():
    """Test strings.is_palindrome function."""
    assert submodules.strings.is_palindrome("racecar") is True
    assert submodules.strings.is_palindrome("hello") is False
    assert submodules.strings.is_palindrome("A man a plan a canal Panama") is True
    assert submodules.strings.is_palindrome("Was it a rat I saw") is True


# Collections submodule tests
def test_collections_sum_list():
    """Test collections.sum_list function."""
    assert submodules.collections.sum_list([1, 2, 3, 4]) == 10
    assert submodules.collections.sum_list([]) == 0
    assert submodules.collections.sum_list([-1, 1]) == 0


def test_collections_max_value():
    """Test collections.max_value function."""
    assert submodules.collections.max_value([1, 5, 3, 9, 2]) == 9
    assert submodules.collections.max_value([-10, -5, -20]) == -5


def test_collections_max_value_empty():
    """Test collections.max_value with empty list."""
    with pytest.raises(ValueError) as exc_info:
        submodules.collections.max_value([])
    assert "empty list" in str(exc_info.value).lower()


def test_collections_min_value():
    """Test collections.min_value function."""
    assert submodules.collections.min_value([1, 5, 3, 9, 2]) == 1
    assert submodules.collections.min_value([-10, -5, -20]) == -20


def test_collections_min_value_empty():
    """Test collections.min_value with empty list."""
    with pytest.raises(ValueError) as exc_info:
        submodules.collections.min_value([])
    assert "empty list" in str(exc_info.value).lower()


def test_collections_unique():
    """Test collections.unique function."""
    assert submodules.collections.unique([1, 2, 2, 3, 1, 4]) == [1, 2, 3, 4]
    assert submodules.collections.unique([]) == []
    assert submodules.collections.unique([1, 1, 1]) == [1]


def test_collections_average():
    """Test collections.average function."""
    assert submodules.collections.average([1.0, 2.0, 3.0, 4.0]) == 2.5
    assert submodules.collections.average([10.0]) == 10.0


def test_collections_average_empty():
    """Test collections.average with empty list."""
    with pytest.raises(ValueError) as exc_info:
        submodules.collections.average([])
    assert "empty list" in str(exc_info.value).lower()


def test_submodule_independence():
    """Test that submodules work independently."""
    # Can use functions from different submodules together
    numbers = [1, 2, 3, 4, 5]
    total = submodules.collections.sum_list(numbers)
    assert total == 15

    text = "hello"
    upper = submodules.strings.to_upper(text)
    assert upper == "HELLO"

    result = submodules.math.multiply(total, 2)
    assert result == 30


def test_import_patterns():
    """Test different import patterns work."""
    # Direct module import (already done)
    import submodules
    assert submodules.math.add(1, 2) == 3

    # Import specific submodule
    from submodules import math
    assert math.add(1, 2) == 3

    # Import specific function (note: requires parent module)
    from submodules.math import add
    assert add(1, 2) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
