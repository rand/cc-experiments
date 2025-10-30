"""
Test input validation and error propagation
"""
import pytest
from error_testing import (
    process_validated_data,
    process_user_age,
    ValidationError,
    RangeError,
)


class TestDataValidation:
    """Test data validation functions"""

    def test_validate_positive_data(self):
        """Test processing valid data."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = process_validated_data(data, 0.0, 10.0)

        # Result should be squared values
        expected = [1.0, 4.0, 9.0, 16.0, 25.0]
        assert result == expected

    def test_validate_empty_data(self):
        """Test empty data raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            process_validated_data([], 0.0, 10.0)

    def test_validate_invalid_range(self):
        """Test invalid range raises error."""
        data = [5.0]
        with pytest.raises(ValueError, match="cannot exceed max_val"):
            process_validated_data(data, 10.0, 5.0)

    def test_validate_out_of_range(self):
        """Test out-of-range value raises RangeError."""
        data = [1.0, 2.0, 15.0, 4.0]  # 15.0 is out of range
        with pytest.raises(RangeError, match="outside range"):
            process_validated_data(data, 0.0, 10.0)

    def test_validate_range_boundary(self):
        """Test values at range boundaries."""
        data = [0.0, 5.0, 10.0]
        result = process_validated_data(data, 0.0, 10.0)
        assert result == [0.0, 25.0, 100.0]


class TestErrorPropagation:
    """Test error propagation through function calls"""

    def test_process_valid_age(self):
        """Test processing valid ages."""
        assert process_user_age("25") == "adult"
        assert process_user_age("10") == "minor"
        assert process_user_age("70") == "senior"

    def test_process_invalid_format(self):
        """Test invalid format propagates error."""
        with pytest.raises(ValueError, match="Invalid integer"):
            process_user_age("abc")

    def test_process_negative_age(self):
        """Test negative age propagates ValidationError."""
        with pytest.raises(ValueError, match="must be positive"):
            process_user_age("-5")

    def test_process_excessive_age(self):
        """Test excessive age propagates ValidationError."""
        with pytest.raises(ValidationError, match="exceeds maximum"):
            process_user_age("200")

    @pytest.mark.parametrize("age_str,expected_category", [
        ("0", "minor"),
        ("17", "minor"),
        ("18", "adult"),
        ("64", "adult"),
        ("65", "senior"),
        ("100", "senior"),
    ])
    def test_age_categories(self, age_str, expected_category):
        """Test age category classification."""
        assert process_user_age(age_str) == expected_category


class TestMultipleValidations:
    """Test scenarios with multiple validation steps"""

    @pytest.mark.parametrize("data,min_val,max_val", [
        ([1.0, 2.0, 3.0], 0.0, 5.0),
        ([0.0, 0.0, 0.0], 0.0, 0.0),
        ([-5.0, 0.0, 5.0], -10.0, 10.0),
        ([100.0, 200.0], 0.0, 1000.0),
    ])
    def test_valid_data_ranges(self, data, min_val, max_val):
        """Test various valid data and range combinations."""
        result = process_validated_data(data, min_val, max_val)
        assert len(result) == len(data)
        # Verify squared values
        for i, val in enumerate(data):
            assert result[i] == val * val

    @pytest.mark.parametrize("data,min_val,max_val,error_type,error_pattern", [
        ([], 0.0, 10.0, ValueError, "cannot be empty"),
        ([5.0], 10.0, 5.0, ValueError, "cannot exceed max_val"),
        ([15.0], 0.0, 10.0, RangeError, "outside range"),
        ([-1.0], 0.0, 10.0, RangeError, "outside range"),
    ])
    def test_invalid_data_ranges(self, data, min_val, max_val, error_type, error_pattern):
        """Test various invalid data and range combinations."""
        with pytest.raises(error_type, match=error_pattern):
            process_validated_data(data, min_val, max_val)


class TestEdgeCases:
    """Test edge cases in error handling"""

    def test_boundary_age_values(self):
        """Test age at exact boundaries."""
        assert process_user_age("0") == "minor"
        assert process_user_age("18") == "adult"
        assert process_user_age("65") == "senior"
        assert process_user_age("150") == "senior"

    def test_boundary_range_values(self):
        """Test values at exact range boundaries."""
        # Minimum boundary
        result = process_validated_data([0.0], 0.0, 10.0)
        assert result == [0.0]

        # Maximum boundary
        result = process_validated_data([10.0], 0.0, 10.0)
        assert result == [100.0]

    def test_zero_range(self):
        """Test zero-width range."""
        result = process_validated_data([5.0], 5.0, 5.0)
        assert result == [25.0]
