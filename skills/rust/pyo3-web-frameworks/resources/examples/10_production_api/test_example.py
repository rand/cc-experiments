"""Test suite for production_api."""

import pytest
import json
import production_api


def test_database_crud():
    """Test complete CRUD operations."""
    db = production_api.Database()

    # Create
    user_json = db.create_user("testuser", "test@example.com")
    user = json.loads(user_json)
    assert user["username"] == "testuser"
    assert user["email"] == "test@example.com"
    user_id = user["id"]

    # Read
    retrieved = db.get_user(user_id)
    assert retrieved is not None
    assert "testuser" in retrieved

    # Update
    assert db.update_user(user_id, "newname", None) is True

    # Delete
    assert db.delete_user(user_id) is True
    assert db.get_user(user_id) is None


def test_auth_manager():
    """Test authentication."""
    auth = production_api.AuthManager(ttl_seconds=3600)

    # Create token
    token = auth.create_token(123)
    assert isinstance(token, str)
    assert len(token) > 0

    # Verify token
    user_id = auth.verify_token(token)
    assert user_id == 123

    # Revoke token
    assert auth.revoke_token(token) is True
    assert auth.verify_token(token) is None


def test_validation():
    """Test input validation."""
    errors = production_api.validate_user_input("ab", "invalid")
    assert len(errors) > 0

    errors = production_api.validate_user_input("validuser", "valid@example.com")
    assert len(errors) == 0


def test_rate_limiter():
    """Test rate limiting."""
    limiter = production_api.ProductionRateLimiter(limit=2, window_seconds=10)

    assert limiter.check_limit("user1") is True
    assert limiter.check_limit("user1") is True
    assert limiter.check_limit("user1") is False


def test_cache():
    """Test caching."""
    cache = production_api.ProductionCache(ttl_seconds=60)

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    cache.invalidate("key1")
    assert cache.get("key1") is None


def test_production_api_integration():
    """Test complete production API workflow."""
    from fastapi import FastAPI, HTTPException, Header
    from fastapi.testclient import TestClient
    from pydantic import BaseModel

    app = FastAPI()

    # Initialize components
    db = production_api.Database()
    auth = production_api.AuthManager(ttl_seconds=3600)
    limiter = production_api.ProductionRateLimiter(limit=10, window_seconds=60)
    cache = production_api.ProductionCache(ttl_seconds=300)

    class UserCreate(BaseModel):
        username: str
        email: str

    @app.post("/users")
    async def create_user(user: UserCreate, authorization: str = Header(None)):
        # Rate limit
        if not limiter.check_limit(authorization or "anonymous"):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Validate
        errors = production_api.validate_user_input(user.username, user.email)
        if errors:
            raise HTTPException(status_code=400, detail={"errors": errors})

        # Create user
        user_json = db.create_user(user.username, user.email)
        return json.loads(user_json)

    @app.get("/users/{user_id}")
    async def get_user(user_id: int):
        # Check cache
        cache_key = f"user:{user_id}"
        cached = cache.get(cache_key)
        if cached:
            return json.loads(cached)

        # Get from DB
        user_json = db.get_user(user_id)
        if user_json is None:
            raise HTTPException(status_code=404, detail="User not found")

        # Cache result
        cache.set(cache_key, user_json)
        return json.loads(user_json)

    @app.post("/auth/login")
    async def login(user_id: int):
        token = auth.create_token(user_id)
        return {"token": token}

    client = TestClient(app)

    # Test user creation
    response = client.post("/users", json={"username": "testuser", "email": "test@example.com"})
    assert response.status_code == 200
    user_id = response.json()["id"]

    # Test user retrieval
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200

    # Test login
    response = client.post(f"/auth/login?user_id={user_id}")
    assert response.status_code == 200
    assert "token" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
