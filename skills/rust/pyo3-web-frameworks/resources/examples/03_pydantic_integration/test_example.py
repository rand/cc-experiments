"""
Test suite for pydantic_integration PyO3 module.

Run with: pytest test_example.py -v
Build first: maturin develop
"""

import pytest
from pydantic import BaseModel
import pydantic_integration


class User(BaseModel):
    username: str
    email: str
    age: int


class APIRequest(BaseModel):
    action: str
    resource: str
    user_id: int


def test_validate_email():
    """Test email validation."""
    result = pydantic_integration.validate_email("user@example.com")
    assert result.valid is True
    assert len(result.errors) == 0

    result = pydantic_integration.validate_email("invalid")
    assert result.valid is False
    assert len(result.errors) > 0

    result = pydantic_integration.validate_email("User@Example.COM")
    assert len(result.warnings) > 0  # Should warn about case


def test_validate_user_model():
    """Test Pydantic user model validation."""
    user = User(username="john_doe", email="john@example.com", age=25)
    result = pydantic_integration.validate_user_model(user)
    assert result.valid is True
    assert len(result.errors) == 0

    user = User(username="ab", email="invalid", age=200)
    result = pydantic_integration.validate_user_model(user)
    assert result.valid is False
    assert len(result.errors) > 0


def test_validate_password():
    """Test password strength validation."""
    result = pydantic_integration.validate_password("Str0ng!Pass")
    assert result.valid is True

    result = pydantic_integration.validate_password("weak")
    assert result.valid is False
    assert any("8 characters" in e for e in result.errors)


def test_validate_request():
    """Test API request validation."""
    request = APIRequest(action="create", resource="users", user_id=123)
    result = pydantic_integration.validate_request(request)
    assert result.valid is True

    request = APIRequest(action="invalid", resource="", user_id=-1)
    result = pydantic_integration.validate_request(request)
    assert result.valid is False


def test_sanitize_input():
    """Test input sanitization."""
    sanitized = pydantic_integration.sanitize_input("Hello<script>World</script>")
    assert "<script>" not in sanitized
    assert "HelloscriptWorldscript" == sanitized or "Hello World" in sanitized


def test_normalize_phone():
    """Test phone number normalization."""
    normalized = pydantic_integration.normalize_phone("(555) 123-4567")
    assert "+1-555-123-4567" == normalized

    with pytest.raises(ValueError):
        pydantic_integration.normalize_phone("123")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
