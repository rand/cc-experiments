"""
Complete REST API Example with FastAPI

Demonstrates:
- Resource-based URLs
- Proper HTTP methods
- Status codes
- Pagination
- Filtering and sorting
- Error handling
- Authentication
- Caching
- Rate limiting
- OpenAPI documentation
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
import time


# Models
class UserBase(BaseModel):
    """User base model"""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    role: str = Field(default="user", pattern="^(user|admin|editor)$")


class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """User update model"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, pattern="^(user|admin|editor)$")


class UserResponse(UserBase):
    """User response model"""
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    limit: int
    offset: int
    total: int
    has_more: bool


class UserListResponse(BaseModel):
    """User list response"""
    data: List[UserResponse]
    pagination: PaginationMeta
    links: dict


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    message: str
    details: Optional[List[dict]] = None
    request_id: Optional[str] = None


# App setup
app = FastAPI(
    title="User Management API",
    version="1.0.0",
    description="Example REST API with best practices"
)

security = HTTPBearer()


# In-memory database (replace with real database)
users_db = [
    {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com",
        "role": "admin",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "is_active": True
    },
    {
        "id": 2,
        "name": "Jane Smith",
        "email": "jane@example.com",
        "role": "user",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "is_active": True
    }
]

# Rate limiting storage
rate_limit_storage = {}


# Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID"""
    request_id = f"req-{int(time.time() * 1000)}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Dependencies
def rate_limiter(request: Request):
    """Rate limiting"""
    client_ip = request.client.host
    now = time.time()

    # Clean old entries
    if client_ip in rate_limit_storage:
        rate_limit_storage[client_ip] = [
            ts for ts in rate_limit_storage[client_ip]
            if now - ts < 60  # 1 minute window
        ]
    else:
        rate_limit_storage[client_ip] = []

    # Check limit
    if len(rate_limit_storage[client_ip]) >= 100:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Rate limit exceeded. Try again later.",
                "retry_after": 60
            }
        )

    # Record request
    rate_limit_storage[client_ip].append(now)

    # Add rate limit headers to request state
    request.state.rate_limit = {
        "limit": 100,
        "remaining": 100 - len(rate_limit_storage[client_ip]),
        "reset": int(now) + 60
    }


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify authentication token"""
    # In production, verify JWT token
    token = credentials.credentials

    if token != "valid-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "Invalid authentication token"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    return {"user_id": 1, "role": "admin"}


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": getattr(exc.detail, "error", "error") if isinstance(exc.detail, dict) else "error",
            "message": getattr(exc.detail, "message", str(exc.detail)) if isinstance(exc.detail, dict) else str(exc.detail),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# Endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get(
    "/api/users",
    response_model=UserListResponse,
    tags=["Users"],
    summary="List users",
    description="Retrieve a paginated list of users with optional filtering and sorting"
)
async def list_users(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    status: Optional[str] = Query(None, description="Filter by status (active, inactive)"),
    role: Optional[str] = Query(None, description="Filter by role"),
    sort: Optional[str] = Query(None, description="Sort field (created_at, name)"),
    current_user: dict = Depends(verify_token),
    _: None = Depends(rate_limiter)
):
    """List users with pagination, filtering, and sorting"""
    # Filter
    filtered_users = users_db.copy()

    if status:
        is_active = status == "active"
        filtered_users = [u for u in filtered_users if u["is_active"] == is_active]

    if role:
        filtered_users = [u for u in filtered_users if u["role"] == role]

    # Sort
    if sort:
        reverse = sort.startswith("-")
        field = sort.lstrip("-")
        filtered_users.sort(key=lambda x: x.get(field, ""), reverse=reverse)

    # Paginate
    total = len(filtered_users)
    paginated_users = filtered_users[offset:offset + limit]

    # Build response
    base_url = str(request.url).split("?")[0]
    query_params = f"limit={limit}"
    if status:
        query_params += f"&status={status}"
    if role:
        query_params += f"&role={role}"
    if sort:
        query_params += f"&sort={sort}"

    response = UserListResponse(
        data=paginated_users,
        pagination=PaginationMeta(
            limit=limit,
            offset=offset,
            total=total,
            has_more=offset + limit < total
        ),
        links={
            "self": f"{base_url}?{query_params}&offset={offset}",
            "first": f"{base_url}?{query_params}&offset=0",
            "last": f"{base_url}?{query_params}&offset={max(0, total - limit)}"
        }
    )

    if offset > 0:
        response.links["prev"] = f"{base_url}?{query_params}&offset={max(0, offset - limit)}"

    if offset + limit < total:
        response.links["next"] = f"{base_url}?{query_params}&offset={offset + limit}"

    # Add rate limit headers
    return JSONResponse(
        content=response.model_dump(),
        headers={
            "X-RateLimit-Limit": str(request.state.rate_limit["limit"]),
            "X-RateLimit-Remaining": str(request.state.rate_limit["remaining"]),
            "X-RateLimit-Reset": str(request.state.rate_limit["reset"]),
            "Cache-Control": "private, max-age=60"
        }
    )


@app.get(
    "/api/users/{user_id}",
    response_model=UserResponse,
    tags=["Users"],
    summary="Get user",
    description="Retrieve a single user by ID"
)
async def get_user(
    user_id: int,
    current_user: dict = Depends(verify_token),
    _: None = Depends(rate_limiter)
):
    """Get single user"""
    user = next((u for u in users_db if u["id"] == user_id), None)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"User with id {user_id} not found"
            }
        )

    # Add ETag header
    etag = f'"{user["updated_at"].timestamp()}"'

    return JSONResponse(
        content=UserResponse(**user).model_dump(mode="json"),
        headers={
            "ETag": etag,
            "Cache-Control": "private, max-age=300"
        }
    )


@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
    summary="Create user",
    description="Create a new user"
)
async def create_user(
    user: UserCreate,
    current_user: dict = Depends(verify_token),
    _: None = Depends(rate_limiter)
):
    """Create new user"""
    # Check if email already exists
    if any(u["email"] == user.email for u in users_db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "conflict",
                "message": f"User with email {user.email} already exists"
            }
        )

    # Create user
    new_user = {
        "id": max(u["id"] for u in users_db) + 1 if users_db else 1,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "is_active": True
    }

    users_db.append(new_user)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=UserResponse(**new_user).model_dump(mode="json"),
        headers={
            "Location": f"/api/users/{new_user['id']}"
        }
    )


@app.put(
    "/api/users/{user_id}",
    response_model=UserResponse,
    tags=["Users"],
    summary="Update user",
    description="Replace a user (full update)"
)
async def update_user(
    user_id: int,
    user: UserBase,
    current_user: dict = Depends(verify_token),
    _: None = Depends(rate_limiter)
):
    """Update user (full replacement)"""
    existing_user = next((u for u in users_db if u["id"] == user_id), None)

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"User with id {user_id} not found"
            }
        )

    # Update all fields
    existing_user.update({
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "updated_at": datetime.now()
    })

    return UserResponse(**existing_user)


@app.patch(
    "/api/users/{user_id}",
    response_model=UserResponse,
    tags=["Users"],
    summary="Partial update user",
    description="Update specific fields of a user"
)
async def partial_update_user(
    user_id: int,
    user: UserUpdate,
    current_user: dict = Depends(verify_token),
    _: None = Depends(rate_limiter)
):
    """Partially update user"""
    existing_user = next((u for u in users_db if u["id"] == user_id), None)

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"User with id {user_id} not found"
            }
        )

    # Update only provided fields
    update_data = user.model_dump(exclude_unset=True)
    existing_user.update(update_data)
    existing_user["updated_at"] = datetime.now()

    return UserResponse(**existing_user)


@app.delete(
    "/api/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Users"],
    summary="Delete user",
    description="Delete a user"
)
async def delete_user(
    user_id: int,
    current_user: dict = Depends(verify_token),
    _: None = Depends(rate_limiter)
):
    """Delete user"""
    user_index = next((i for i, u in enumerate(users_db) if u["id"] == user_id), None)

    if user_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"User with id {user_id} not found"
            }
        )

    users_db.pop(user_index)

    return None  # 204 No Content


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
