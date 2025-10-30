"""Test suite for type_validation PyO3 module."""

import pytest
import type_validation as tv


class TestEmail:
    def test_valid_email(self):
        email = tv.Email("user@example.com")
        assert email.address == "user@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValueError, match="Invalid email"):
            tv.Email("notanemail")
        with pytest.raises(ValueError, match="Invalid email"):
            tv.Email("@example.com")


class TestPositiveInt:
    def test_positive_value(self):
        p = tv.PositiveInt(5)
        assert p.value == 5

    def test_zero_invalid(self):
        with pytest.raises(ValueError, match="must be positive"):
            tv.PositiveInt(0)

    def test_negative_invalid(self):
        with pytest.raises(ValueError, match="must be positive"):
            tv.PositiveInt(-5)


class TestBoundedInt:
    def test_valid_value(self):
        b = tv.BoundedInt(50, 0, 100)
        assert b.value == 50

    def test_out_of_range(self):
        with pytest.raises(ValueError, match="outside range"):
            tv.BoundedInt(150, 0, 100)

    def test_set_value(self):
        b = tv.BoundedInt(50, 0, 100)
        b.set_value(75)
        assert b.value == 75

    def test_set_invalid_value(self):
        b = tv.BoundedInt(50, 0, 100)
        with pytest.raises(ValueError, match="outside range"):
            b.set_value(150)


class TestPercentage:
    def test_valid_percentage(self):
        p = tv.Percentage(75.5)
        assert p.value == 75.5

    def test_as_decimal(self):
        p = tv.Percentage(75.0)
        assert abs(p.as_decimal() - 0.75) < 1e-10

    def test_invalid_percentage(self):
        with pytest.raises(ValueError, match="between 0 and 100"):
            tv.Percentage(150.0)


class TestNonEmptyString:
    def test_valid_string(self):
        s = tv.NonEmptyString("  hello  ")
        assert s.value == "hello"

    def test_empty_string(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            tv.NonEmptyString("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            tv.NonEmptyString("   ")


class TestPhoneNumber:
    def test_valid_phone(self):
        p = tv.PhoneNumber("(555) 123-4567")
        assert "5551234567" in p.number

    def test_short_phone(self):
        with pytest.raises(ValueError, match="at least 10 digits"):
            tv.PhoneNumber("123")


class TestUsername:
    def test_valid_username(self):
        u = tv.Username("user_123")
        assert u.name == "user_123"

    def test_too_short(self):
        with pytest.raises(ValueError, match="at least 3 characters"):
            tv.Username("ab")

    def test_invalid_chars(self):
        with pytest.raises(ValueError, match="letters, numbers, and underscores"):
            tv.Username("user@name")


class TestUrl:
    def test_valid_http(self):
        u = tv.Url("http://example.com")
        assert u.url == "http://example.com"

    def test_valid_https(self):
        u = tv.Url("https://example.com")
        assert u.url == "https://example.com"

    def test_missing_protocol(self):
        with pytest.raises(ValueError, match="must start with http"):
            tv.Url("example.com")


class TestHexColor:
    def test_valid_6_digit(self):
        c = tv.HexColor("#ff5733")
        assert c.code == "#FF5733"

    def test_valid_3_digit(self):
        c = tv.HexColor("#f57")
        assert c.code == "#F57"

    def test_missing_hash(self):
        with pytest.raises(ValueError, match="must start with #"):
            tv.HexColor("ff5733")

    def test_invalid_length(self):
        with pytest.raises(ValueError, match="#RGB or #RRGGBB"):
            tv.HexColor("#ff")


def test_send_email():
    email = tv.Email("test@example.com")
    msg = tv.NonEmptyString("Hello")
    result = tv.send_email(email, msg)
    assert "test@example.com" in result


def test_calculate_grade():
    assert "A" in tv.calculate_grade(tv.Percentage(95.0))
    assert "B" in tv.calculate_grade(tv.Percentage(85.0))
    assert "C" in tv.calculate_grade(tv.Percentage(75.0))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
