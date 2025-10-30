"""Test suite for jwt_auth."""

import pytest
import jwt_auth


def test_sign_verify_token():
    """Test token signing and verification."""
    payload = "user_id=123"
    secret = "my_secret_key"

    signature = jwt_auth.sign_token(payload, secret)
    assert isinstance(signature, str)
    assert len(signature) > 0

    assert jwt_auth.verify_token(payload, signature, secret) is True
    assert jwt_auth.verify_token(payload, signature, "wrong_key") is False


def test_hash_verify_password():
    """Test password hashing and verification."""
    password = "SecurePassword123!"

    hash_value = jwt_auth.hash_password(password)
    assert isinstance(hash_value, str)
    assert len(hash_value) > 0

    assert jwt_auth.verify_password(password, hash_value) is True
    assert jwt_auth.verify_password("wrong", hash_value) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
