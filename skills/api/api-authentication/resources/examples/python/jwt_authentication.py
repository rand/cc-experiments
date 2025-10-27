"""
JWT Authentication Example for FastAPI

Complete JWT authentication implementation with access/refresh tokens,
password hashing, and secure token management.

Usage:
    uv pip install fastapi pyjwt passlib python-multipart argon2-cffi
    uv run uvicorn jwt_authentication:app --reload
"""

from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import jwt
from datetime import datetime, timedelta
from typing import Optional
import secrets

# Configuration
SECRET_KEY = secrets.token_urlsafe(32)  # Generate secure secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

app = FastAPI(title="JWT Authentication Example")
security = HTTPBearer()
ph = PasswordHasher()

# In-memory user database (use real database in production)
users_db = {}
refresh_tokens_db = {}


# Models
class UserRegistration(BaseModel):
    username: str
    password: str
    email: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class User(BaseModel):
    id: int
    username: str
    email: str


# Token functions
def create_access_token(user_id: int, username: str) -> str:
    """Create JWT access token"""
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Create JWT refresh token"""
    token = secrets.token_urlsafe(32)

    # Store refresh token (in production, store in database with hash)
    refresh_tokens_db[token] = {
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    }

    return token


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "require": ["exp", "sub", "type"]
            }
        )

        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


# Dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> User:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    payload = verify_token(token)

    user_id = int(payload["sub"])
    username = payload["username"]

    # Get user from database
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return User(id=user_id, username=username, email=user["email"])


# Endpoints
@app.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegistration):
    """Register new user"""

    # Check if user exists
    if any(u["username"] == user.username for u in users_db.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Hash password with Argon2
    password_hash = ph.hash(user.password)

    # Create user
    user_id = len(users_db) + 1
    users_db[user_id] = {
        "username": user.username,
        "password_hash": password_hash,
        "email": user.email,
        "created_at": datetime.utcnow()
    }

    # Generate tokens
    access_token = create_access_token(user_id, user.username)
    refresh_token = create_refresh_token(user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login and get access token"""

    # Find user
    user = None
    user_id = None
    for uid, u in users_db.items():
        if u["username"] == credentials.username:
            user = u
            user_id = uid
            break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Verify password
    try:
        ph.verify(user["password_hash"], credentials.password)
    except VerifyMismatchError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Check if password needs rehashing (params changed)
    if ph.check_needs_rehash(user["password_hash"]):
        user["password_hash"] = ph.hash(credentials.password)

    # Generate tokens
    access_token = create_access_token(user_id, user["username"])
    refresh_token = create_refresh_token(user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(refresh_token: str):
    """Refresh access token using refresh token"""

    # Validate refresh token
    token_data = refresh_tokens_db.get(refresh_token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Check expiration
    if datetime.utcnow() > token_data["expires_at"]:
        # Clean up expired token
        del refresh_tokens_db[refresh_token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )

    # Get user
    user_id = token_data["user_id"]
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Generate new access token
    access_token = create_access_token(user_id, user["username"])

    # Token rotation: generate new refresh token
    del refresh_tokens_db[refresh_token]
    new_refresh_token = create_refresh_token(user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/logout")
async def logout(
    refresh_token: str,
    current_user: User = Depends(get_current_user)
):
    """Logout and revoke refresh token"""

    # Revoke refresh token
    if refresh_token in refresh_tokens_db:
        del refresh_tokens_db[refresh_token]

    return {"message": "Logged out successfully"}


@app.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    """Example protected route"""
    return {
        "message": f"Hello, {current_user.username}!",
        "user_id": current_user.id
    }


if __name__ == "__main__":
    import uvicorn
    print("Starting JWT Authentication Example")
    print(f"Access token expires in: {ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    print(f"Refresh token expires in: {REFRESH_TOKEN_EXPIRE_DAYS} days")
    print("\nTest with:")
    print("  POST /register - Register new user")
    print("  POST /login - Login and get tokens")
    print("  POST /refresh - Refresh access token")
    print("  GET /me - Get current user info (requires auth)")
    print("  GET /protected - Protected route (requires auth)")
    print("\nAuthorization header: Bearer <access_token>")
    uvicorn.run(app, host="0.0.0.0", port=8000)
