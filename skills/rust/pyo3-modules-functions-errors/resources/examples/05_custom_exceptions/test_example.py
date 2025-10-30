"""Tests for custom_exceptions example."""

import pytest
import custom_exceptions as ce


def test_exception_hierarchy():
    """Test custom exception inheritance."""
    # ValidationError is base
    assert issubclass(ce.RangeError, ce.ValidationError)
    assert issubclass(ce.FormatError, ce.ValidationError)
    assert issubclass(ce.LengthError, ce.ValidationError)
    
    # ProcessingError is base
    assert issubclass(ce.ParseError, ce.ProcessingError)
    assert issubclass(ce.TransformError, ce.ProcessingError)
    assert issubclass(ce.ComputationError, ce.ProcessingError)


def test_validate_range_success():
    """Test successful range validation."""
    assert ce.validate_range(5, 0, 10) == 5
    assert ce.validate_range(0, 0, 10) == 0
    assert ce.validate_range(10, 0, 10) == 10


def test_validate_range_error():
    """Test range validation error."""
    with pytest.raises(ce.RangeError) as exc_info:
        ce.validate_range(15, 0, 10)
    assert "outside valid range" in str(exc_info.value).lower()


def test_validate_email_success():
    """Test successful email validation."""
    assert ce.validate_email("user@example.com") == "user@example.com"
    assert ce.validate_email("test.user@domain.co.uk") == "test.user@domain.co.uk"


def test_validate_email_error():
    """Test email validation errors."""
    with pytest.raises(ce.FormatError):
        ce.validate_email("notanemail")
    
    with pytest.raises(ce.FormatError):
        ce.validate_email("@example.com")


def test_validate_length_success():
    """Test successful length validation."""
    result = ce.validate_length("hello", 3, 10)
    assert result == "hello"


def test_validate_length_error():
    """Test length validation errors."""
    with pytest.raises(ce.LengthError) as exc_info:
        ce.validate_length("hi", 5, 10)
    assert "too short" in str(exc_info.value).lower()
    
    with pytest.raises(ce.LengthError) as exc_info:
        ce.validate_length("very long string", 1, 5)
    assert "too long" in str(exc_info.value).lower()


def test_parse_key_value_success():
    """Test successful parsing."""
    key, value = ce.parse_key_value("name:Alice")
    assert key == "name"
    assert value == "Alice"


def test_parse_key_value_error():
    """Test parsing errors."""
    with pytest.raises(ce.ParseError):
        ce.parse_key_value("nocolon")
    
    with pytest.raises(ce.ParseError):
        ce.parse_key_value("::multiple")


def test_transform_title_case():
    """Test title case transformation."""
    assert ce.transform_title_case("hello world") == "Hello World"
    assert ce.transform_title_case("LOUD WORDS") == "Loud Words"


def test_transform_error():
    """Test transformation error."""
    with pytest.raises(ce.TransformError):
        ce.transform_title_case("")


def test_safe_factorial_success():
    """Test successful factorial."""
    assert ce.safe_factorial(5) == 120
    assert ce.safe_factorial(0) == 1


def test_safe_factorial_overflow():
    """Test factorial overflow error."""
    with pytest.raises(ce.ComputationError):
        ce.safe_factorial(25)


def test_detailed_error():
    """Test detailed error with attributes."""
    with pytest.raises(ce.DetailedError) as exc_info:
        ce.raise_detailed_error("Something failed", 500, "In production")
    
    error = exc_info.value
    assert error.code == 500
    assert error.context == "In production"


def test_catch_base_exception():
    """Test catching base exception catches derived."""
    with pytest.raises(ce.ValidationError):
        ce.validate_range(100, 0, 10)  # Raises RangeError
    
    with pytest.raises(ce.ProcessingError):
        ce.parse_key_value("invalid")  # Raises ParseError


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
