"""
Test error handling and exceptions
"""
import pytest
from error_testing import (
    divide,
    validate_age,
    validate_email,
    validate_range,
    parse_positive_int,
    ValidationError,
    RangeError,
)


class TestDivideErrors:
    """Test division error cases"""

    def test_division_by_zero(self):
        """Test division by zero raises ValueError."""
        with pytest.raises(ValueError, match="Division by zero"):
            divide(10.0, 0.0)

    def test_divide_nan(self):
        """Test dividing NaN raises ValueError."""
        with pytest.raises(ValueError, match="Cannot divide NaN"):
            divide(float('nan'), 5.0)

        with pytest.raises(ValueError, match="Cannot divide NaN"):
            divide(5.0, float('nan'))

    def test_divide_infinity(self):
        """Test dividing infinity raises ValueError."""
        with pytest.raises(ValueError, match="Cannot divide infinite"):
            divide(float('inf'), 5.0)

        with pytest.raises(ValueError, match="Cannot divide infinite"):
            divide(5.0, float('inf'))

    def test_divide_normal(self):
        """Test normal division works."""
        assert divide(10.0, 2.0) == 5.0
        assert divide(7.5, 2.5) == 3.0


class TestValidationErrors:
    """Test validation error cases"""

    def test_negative_age(self):
        """Test negative age raises ValidationError."""
        with pytest.raises(ValidationError, match="Age cannot be negative"):
            validate_age(-1)

    def test_excessive_age(self):
        """Test excessive age raises ValidationError."""
        with pytest.raises(ValidationError, match="exceeds maximum"):
            validate_age(200)

    def test_valid_age(self):
        """Test valid age passes."""
        validate_age(25)
        validate_age(0)
        validate_age(150)

    def test_invalid_email_empty(self):
        """Test empty email raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_email("")

    def test_invalid_email_no_at(self):
        """Test email without @ raises ValidationError."""
        with pytest.raises(ValidationError, match="must contain @"):
            validate_email("notanemail.com")

    def test_invalid_email_no_domain(self):
        """Test email without domain raises ValidationError."""
        with pytest.raises(ValidationError, match="must contain a domain"):
            validate_email("user@domain")

    def test_valid_email(self):
        """Test valid email passes."""
        validate_email("user@example.com")
        validate_email("test.user@sub.domain.org")


class TestRangeErrors:
    """Test range validation errors"""

    def test_value_below_min(self):
        """Test value below minimum raises RangeError."""
        with pytest.raises(RangeError, match="below minimum"):
            validate_range(5.0, 10.0, 20.0)

    def test_value_above_max(self):
        """Test value above maximum raises RangeError."""
        with pytest.raises(RangeError, match="exceeds maximum"):
            validate_range(25.0, 10.0, 20.0)

    def test_invalid_range(self):
        """Test invalid range (min > max) raises ValueError."""
        with pytest.raises(ValueError, match="Min cannot be greater than max"):
            validate_range(15.0, 20.0, 10.0)

    def test_value_in_range(self):
        """Test value in range passes."""
        validate_range(15.0, 10.0, 20.0)
        validate_range(10.0, 10.0, 20.0)  # At minimum
        validate_range(20.0, 10.0, 20.0)  # At maximum


class TestParsingErrors:
    """Test parsing and conversion errors"""

    def test_parse_invalid_format(self):
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid integer"):
            parse_positive_int("abc")

        with pytest.raises(ValueError, match="Invalid integer"):
            parse_positive_int("12.5")

    def test_parse_negative(self):
        """Test negative number raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            parse_positive_int("-5")

    def test_parse_valid(self):
        """Test parsing valid positive integers."""
        assert parse_positive_int("42") == 42
        assert parse_positive_int("0") == 0
        assert parse_positive_int("1000") == 1000


@pytest.mark.parametrize("value,expected_error,match_pattern", [
    (float('nan'), ValueError, "NaN"),
    (float('inf'), ValueError, "infinite"),
    (0.0, ValueError, "Division by zero"),
])
def test_divide_error_cases(value, expected_error, match_pattern):
    """Parameterized test for various division errors."""
    with pytest.raises(expected_error, match=match_pattern):
        if value == 0.0:
            divide(10.0, value)
        else:
            divide(value, 5.0)
