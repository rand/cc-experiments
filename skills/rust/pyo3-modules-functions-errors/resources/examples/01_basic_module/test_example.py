"""Tests for basic_module example."""

import pytest
import basic_module


def test_add():
    """Test addition function."""
    assert basic_module.add(2, 3) == 5
    assert basic_module.add(-1, 1) == 0
    assert basic_module.add(0, 0) == 0
    assert basic_module.add(100, 200) == 300


def test_multiply():
    """Test multiplication function."""
    assert basic_module.multiply(2, 3) == 6
    assert basic_module.multiply(-2, 3) == -6
    assert basic_module.multiply(0, 100) == 0
    assert basic_module.multiply(7, 8) == 56


def test_greet():
    """Test greeting function."""
    assert basic_module.greet("Alice") == "Hello, Alice!"
    assert basic_module.greet("Bob") == "Hello, Bob!"
    assert basic_module.greet("") == "Hello, !"


def test_is_even():
    """Test even number checker."""
    assert basic_module.is_even(2) is True
    assert basic_module.is_even(3) is False
    assert basic_module.is_even(0) is True
    assert basic_module.is_even(-4) is True
    assert basic_module.is_even(-3) is False


def test_repeat_string():
    """Test string repetition function."""
    assert basic_module.repeat_string("ab", 3) == "ababab"
    assert basic_module.repeat_string("x", 5) == "xxxxx"
    assert basic_module.repeat_string("hello", 0) == ""
    assert basic_module.repeat_string("", 10) == ""


def test_module_metadata():
    """Test module metadata."""
    assert hasattr(basic_module, "__version__")
    assert hasattr(basic_module, "__author__")
    assert basic_module.__author__ == "PyO3 Examples"


def test_function_docstrings():
    """Test that functions have proper docstrings."""
    assert basic_module.add.__doc__ is not None
    assert "sum" in basic_module.add.__doc__.lower()
    assert basic_module.greet.__doc__ is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
