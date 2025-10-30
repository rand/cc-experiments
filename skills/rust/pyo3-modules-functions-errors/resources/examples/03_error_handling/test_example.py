"""Tests for error_handling example."""

import pytest
import error_handling as eh


def test_divide_success():
    """Test successful division."""
    assert eh.divide(10.0, 2.0) == 5.0
    assert eh.divide(7.0, 2.0) == 3.5
    assert eh.divide(-10.0, 5.0) == -2.0


def test_divide_by_zero():
    """Test division by zero raises ZeroDivisionError."""
    with pytest.raises(ZeroDivisionError) as exc_info:
        eh.divide(10.0, 0.0)
    assert "Cannot divide by zero" in str(exc_info.value)


def test_sqrt_success():
    """Test successful square root."""
    assert eh.sqrt(4.0) == 2.0
    assert eh.sqrt(9.0) == 3.0
    assert eh.sqrt(0.0) == 0.0


def test_sqrt_negative():
    """Test square root of negative raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        eh.sqrt(-4.0)
    assert "negative number" in str(exc_info.value).lower()
    assert "-4" in str(exc_info.value)


def test_parse_int_success():
    """Test successful integer parsing."""
    assert eh.parse_int("42") == 42
    assert eh.parse_int("-10") == -10
    assert eh.parse_int("0") == 0


def test_parse_int_invalid():
    """Test invalid integer parsing raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        eh.parse_int("not a number")
    assert "Invalid integer" in str(exc_info.value)

    with pytest.raises(ValueError):
        eh.parse_int("12.34")


def test_get_at_index_success():
    """Test successful index access."""
    items = ["a", "b", "c"]
    assert eh.get_at_index(items, 0) == "a"
    assert eh.get_at_index(items, 2) == "c"


def test_get_at_index_out_of_bounds():
    """Test out of bounds index raises IndexError."""
    items = ["a", "b", "c"]
    with pytest.raises(IndexError) as exc_info:
        eh.get_at_index(items, 10)
    assert "out of bounds" in str(exc_info.value).lower()
    assert "10" in str(exc_info.value)


def test_validate_age_success():
    """Test valid age values."""
    assert eh.validate_age(0) == 0
    assert eh.validate_age(25) == 25
    assert eh.validate_age(100) == 100


def test_validate_age_negative():
    """Test negative age raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        eh.validate_age(-1)
    assert "negative" in str(exc_info.value).lower()


def test_validate_age_too_large():
    """Test unreasonably large age raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        eh.validate_age(200)
    assert "unreasonably large" in str(exc_info.value).lower()


def test_validate_string_success():
    """Test successful string validation."""
    result = eh.validate_string("  hello  ", 3, 10)
    assert result == "hello"

    result = eh.validate_string("test", 1, 20)
    assert result == "test"


def test_validate_string_too_short():
    """Test string too short raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        eh.validate_string("hi", 5, 10)
    assert "too short" in str(exc_info.value).lower()


def test_validate_string_too_long():
    """Test string too long raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        eh.validate_string("this is a very long string", 1, 10)
    assert "too long" in str(exc_info.value).lower()


def test_validate_string_invalid_range():
    """Test invalid range raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        eh.validate_string("test", 10, 5)
    assert "invalid range" in str(exc_info.value).lower()


def test_risky_operation_success():
    """Test successful risky operation."""
    result = eh.risky_operation(False)
    assert result == "Operation succeeded"


def test_risky_operation_failure():
    """Test risky operation failure raises RuntimeError."""
    with pytest.raises(RuntimeError) as exc_info:
        eh.risky_operation(True)
    assert "failed" in str(exc_info.value).lower()


def test_parse_and_divide_success():
    """Test successful parse and divide."""
    assert eh.parse_and_divide("10", "2") == 5.0
    assert eh.parse_and_divide("7.5", "2.5") == 3.0


def test_parse_and_divide_parse_error():
    """Test parse error in parse_and_divide."""
    with pytest.raises(ValueError) as exc_info:
        eh.parse_and_divide("not_a_number", "2")
    assert "Cannot parse" in str(exc_info.value)

    with pytest.raises(ValueError):
        eh.parse_and_divide("10", "invalid")


def test_parse_and_divide_zero_division():
    """Test division by zero in parse_and_divide."""
    with pytest.raises(ZeroDivisionError):
        eh.parse_and_divide("10", "0")


def test_safe_get_success():
    """Test successful dictionary access."""
    data = {"name": "Alice", "age": "30"}
    assert eh.safe_get("name", data) == "Alice"
    assert eh.safe_get("age", data) == "30"


def test_safe_get_key_error():
    """Test missing key raises KeyError."""
    data = {"name": "Alice"}
    with pytest.raises(KeyError) as exc_info:
        eh.safe_get("age", data)
    assert "not found" in str(exc_info.value).lower()
    assert "age" in str(exc_info.value)


def test_process_value_float():
    """Test processing float value."""
    assert eh.process_value(42.5) == 42.5
    assert eh.process_value(0.0) == 0.0


def test_process_value_int():
    """Test processing int value (converts to float)."""
    assert eh.process_value(42) == 42.0


def test_process_value_string():
    """Test processing string value."""
    assert eh.process_value("3.14") == 3.14
    assert eh.process_value("100") == 100.0


def test_process_value_invalid_string():
    """Test processing invalid string raises TypeError."""
    with pytest.raises(TypeError) as exc_info:
        eh.process_value("not a number")
    assert "Cannot convert" in str(exc_info.value)


def test_process_value_invalid_type():
    """Test processing invalid type raises TypeError."""
    with pytest.raises(TypeError) as exc_info:
        eh.process_value([1, 2, 3])
    assert "Expected float or string" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
