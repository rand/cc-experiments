"""
FastAPI Rate Limiter

Production-ready rate limiting for FastAPI applications using
Redis for distributed rate limiting.

Features:
- Async Redis operations
- Configurable per-route limits
- Dependency injection
- Standard rate limit headers
- Graceful error handling

Usage:
    from fastapi import Depends

    @app.get("/api/resource")
    async def get_resource(
        _: None = Depends(rate_limit(limit=100, window=60))
    ):
        return {"data": "value"}
"""

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import time
from typing import Callable, Optional
from functools import wraps


# Global Redis client (initialize in app startup)
redis_client: Optional[redis.Redis] = None


async def init_redis(redis_url: str = "redis://localhost:6379/0"):
    """Initialize Redis connection"""
    global redis_client
    redis_client = await redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True
    )


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()


# Lua script for atomic fixed window rate limiting
FIXED_WINDOW_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local window_id = math.floor(now / window)
local redis_key = key .. ":" .. window_id

local count = redis.call('INCR', redis_key)
if count == 1 then
    redis.call('EXPIRE', redis_key, window * 2)
end

local allowed = count <= limit
local remaining = math.max(0, limit - count)
local reset = (window_id + 1) * window

return {allowed and 1 or 0, remaining, reset}
"""


def get_client_identifier(request: Request) -> str:
    """Get client identifier for rate limiting

    Args:
        request: FastAPI request

    Returns:
        Client identifier (API key, user ID, or IP)
    """
    # Try API key
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"api_key:{api_key}"

    # Try authenticated user (if using auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Fall back to IP
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host

    return f"ip:{ip}"


async def check_rate_limit(
    key: str,
    limit: int,
    window: int
) -> tuple[bool, int, int]:
    """Check rate limit using Redis

    Args:
        key: Rate limit key
        limit: Maximum requests per window
        window: Window duration in seconds

    Returns:
        Tuple of (allowed, remaining, reset_time)
    """
    if not redis_client:
        # Fail open if Redis not available
        return True, limit, int(time.time() + window)

    now = int(time.time())

    try:
        result = await redis_client.eval(
            FIXED_WINDOW_SCRIPT,
            1,
            f"rate_limit:{key}",
            limit,
            window,
            now
        )

        allowed = bool(result[0])
        remaining = int(result[1])
        reset = int(result[2])

        return allowed, remaining, reset

    except redis.RedisError as e:
        # Fail open on Redis errors
        print(f"Redis error: {e}")
        return True, limit, int(time.time() + window)


def rate_limit(
    limit: int = 100,
    window: int = 60,
    key_func: Optional[Callable[[Request], str]] = None
):
    """Rate limit dependency for FastAPI routes

    Args:
        limit: Maximum requests per window
        window: Window duration in seconds
        key_func: Optional custom key generator function

    Returns:
        FastAPI dependency

    Usage:
        @app.get("/api/resource")
        async def get_resource(
            _: None = Depends(rate_limit(limit=100, window=60))
        ):
            return {"data": "value"}
    """
    async def dependency(request: Request):
        # Get rate limit key
        if key_func:
            key = key_func(request)
        else:
            key = get_client_identifier(request)

        # Check rate limit
        allowed, remaining, reset = await check_rate_limit(key, limit, window)

        # Store in request state for response headers
        request.state.rate_limit = {
            "limit": limit,
            "remaining": remaining,
            "reset": reset
        }

        if not allowed:
            retry_after = reset - int(time.time())

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Retry after {retry_after} seconds.",
                    "retry_after": retry_after
                },
                headers={
                    "Retry-After": str(max(0, retry_after)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset)
                }
            )

    return dependency


# Example FastAPI application
app = FastAPI()


@app.on_event("startup")
async def startup():
    """Initialize Redis on startup"""
    await init_redis()


@app.on_event("shutdown")
async def shutdown():
    """Close Redis on shutdown"""
    await close_redis()


@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    """Add rate limit headers to all responses"""
    response = await call_next(request)

    # Add rate limit headers if available
    if hasattr(request.state, "rate_limit"):
        rl = request.state.rate_limit
        response.headers["X-RateLimit-Limit"] = str(rl["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rl["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rl["reset"])

    return response


# Routes with different rate limits

@app.get("/health")
async def health():
    """Health check (no rate limit)"""
    return {"status": "ok"}


@app.get("/api/posts")
async def get_posts(
    _: None = Depends(rate_limit(limit=100, window=60))
):
    """Get posts (100 requests per minute)"""
    return {"posts": []}


@app.post("/api/posts")
async def create_post(
    _: None = Depends(rate_limit(limit=50, window=60))
):
    """Create post (50 requests per minute)"""
    return {"id": 1, "created": True}


@app.get("/api/expensive")
async def expensive_operation(
    _: None = Depends(rate_limit(limit=5, window=60))
):
    """Expensive operation (5 requests per minute)"""
    return {"result": "computed"}


@app.get("/api/user-specific")
async def user_specific_resource(
    request: Request,
    _: None = Depends(
        rate_limit(
            limit=50,
            window=60,
            key_func=lambda req: f"user:{req.state.user.id if hasattr(req.state, 'user') else 'anonymous'}"
        )
    )
):
    """User-specific resource with per-user rate limit"""
    return {"data": "user resource"}


# Custom rate limit decorator (alternative to dependency)
def rate_limited(limit: int = 100, window: int = 60):
    """Decorator for rate limiting endpoints

    Usage:
        @app.get("/api/resource")
        @rate_limited(limit=100, window=60)
        async def get_resource():
            return {"data": "value"}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if not request:
                # No request found, skip rate limiting
                return await func(*args, **kwargs)

            # Check rate limit
            key = get_client_identifier(request)
            allowed, remaining, reset = await check_rate_limit(key, limit, window)

            request.state.rate_limit = {
                "limit": limit,
                "remaining": remaining,
                "reset": reset
            }

            if not allowed:
                retry_after = reset - int(time.time())
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Too many requests. Retry after {retry_after} seconds."
                    }
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


@app.get("/api/decorated")
@rate_limited(limit=200, window=60)
async def decorated_endpoint(request: Request):
    """Endpoint using decorator instead of dependency"""
    return {"message": "Success"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
