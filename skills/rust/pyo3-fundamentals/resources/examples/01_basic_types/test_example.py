"""
Test suite for basic_types PyO3 module.

Run with: pytest test_example.py -v
Build first: maturin develop
"""

import pytest
import basic_types


def test_double_integer():
    """Test integer conversion and arithmetic."""
    assert basic_types.double_integer(5) == 10
    assert basic_types.double_integer(-3) == -6
    assert basic_types.double_integer(0) == 0


def test_increment_unsigned():
    """Test unsigned integer handling."""
    assert basic_types.increment_unsigned(10) == 11
    assert basic_types.increment_unsigned(0) == 1

    # Test overflow detection
    with pytest.raises(OverflowError):
        basic_types.increment_unsigned(2**64 - 1)


def test_square_float():
    """Test floating point operations."""
    assert basic_types.square_float(4.0) == 16.0
    assert basic_types.square_float(-3.0) == 9.0
    assert abs(basic_types.square_float(1.5) - 2.25) < 1e-10


def test_greet():
    """Test string conversion and formatting."""
    assert basic_types.greet("Alice") == "Hello, Alice!"
    assert basic_types.greet("") == "Hello, !"


def test_get_language():
    """Test static string return."""
    assert basic_types.get_language() == "Rust"


def test_negate_bool():
    """Test boolean operations."""
    assert basic_types.negate_bool(True) is False
    assert basic_types.negate_bool(False) is True


def test_optional_double():
    """Test Option<T> conversion (None handling)."""
    assert basic_types.optional_double(5) == 10
    assert basic_types.optional_double(None) is None
    assert basic_types.optional_double(0) == 0


def test_always_none():
    """Test explicit None return."""
    assert basic_types.always_none() is None


def test_format_info():
    """Test multiple parameter types."""
    result = basic_types.format_info("Bob", 30, 95.5, True)
    assert result == "Name: Bob, Age: 30, Score: 95.50, Active: true"

    result = basic_types.format_info("Alice", 25, 88.3, False)
    assert result == "Name: Alice, Age: 25, Score: 88.30, Active: false"


def test_validate_positive():
    """Test value validation and error handling."""
    assert basic_types.validate_positive(1) == 1
    assert basic_types.validate_positive(100) == 100

    with pytest.raises(ValueError, match="Value must be positive"):
        basic_types.validate_positive(0)

    with pytest.raises(ValueError, match="Value must be positive"):
        basic_types.validate_positive(-5)


def test_sum_different_sizes():
    """Test mixed integer size handling."""
    assert basic_types.sum_different_sizes(10, 20, 30) == 60
    assert basic_types.sum_different_sizes(-5, 10, 5) == 10


def test_precision_comparison():
    """Test f32 vs f64 precision."""
    f32_val, f64_val = basic_types.precision_comparison(3.14159265358979323846)
    assert isinstance(f32_val, float)
    assert isinstance(f64_val, float)
    # f32 should have less precision than f64
    assert abs(f32_val - 3.14159265) < 1e-6
    assert abs(f64_val - 3.14159265358979323846) < 1e-15


def test_bytes_to_string():
    """Test bytes to string conversion."""
    assert basic_types.bytes_to_string(b"Hello") == "Hello"
    assert basic_types.bytes_to_string(b"") == ""

    # Test invalid UTF-8
    with pytest.raises(ValueError, match="Invalid UTF-8"):
        basic_types.bytes_to_string(b"\xff\xfe")


def test_logical_and():
    """Test boolean logic."""
    assert basic_types.logical_and(True, True) is True
    assert basic_types.logical_and(True, False) is False
    assert basic_types.logical_and(False, True) is False
    assert basic_types.logical_and(False, False) is False


def test_complex_calculation():
    """Test comprehensive type handling."""
    # Enabled with offset
    result = basic_types.complex_calculation(10, 2.0, 5, True)
    assert result == 25.0

    # Enabled without offset
    result = basic_types.complex_calculation(10, 2.0, None, True)
    assert result == 20.0

    # Disabled returns None
    result = basic_types.complex_calculation(10, 2.0, 5, False)
    assert result is None


def test_type_errors():
    """Test that incorrect types raise appropriate errors."""
    with pytest.raises(TypeError):
        basic_types.double_integer("not an int")

    with pytest.raises(TypeError):
        basic_types.square_float("not a float")

    with pytest.raises(TypeError):
        basic_types.negate_bool(1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
