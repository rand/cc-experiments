"""
Sliding Window Rate Limiter with Redis

Production-ready sliding window implementation using Redis sorted sets
for smooth rate limiting without boundary bursts.

Features:
- No boundary burst vulnerability
- Accurate request tracking
- Atomic operations with Lua scripts
- Memory-efficient with automatic cleanup

Usage:
    limiter = SlidingWindow(redis_client, "user:123", limit=100, window_seconds=60)
    if limiter.allow_request():
        response = handle_request()
    else:
        return error_429()
"""

import redis
import time
import uuid
from typing import Tuple


class SlidingWindow:
    """Sliding window rate limiter with Redis backend

    Provides smooth rate limiting without boundary bursts.
    More accurate than fixed window but higher memory usage.
    """

    def __init__(self, redis_client: redis.Redis, key: str,
                 limit: int, window_seconds: int):
        """Initialize sliding window rate limiter

        Args:
            redis_client: Redis connection
            key: Unique key for this rate limiter
            limit: Maximum requests in window
            window_seconds: Rolling window duration in seconds
        """
        self.redis = redis_client
        self.key = f"rate_limit:sliding_window:{key}"
        self.limit = limit
        self.window_seconds = window_seconds

        # Lua script for atomic sliding window operations
        # Uses Redis sorted set with timestamps as scores
        self.script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local request_id = ARGV[4]

        local window_start = now - window

        -- Remove requests outside the window
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

        -- Count requests in window
        local count = redis.call('ZCARD', key)

        if count < limit then
            -- Add current request
            redis.call('ZADD', key, now, request_id)
            -- Set expiration to prevent memory leak
            redis.call('EXPIRE', key, window * 2)
            return {1, limit - count - 1}  -- allowed, remaining
        else
            -- Limit exceeded
            return {0, 0}  -- denied, no remaining
        end
        """

        try:
            self.script_sha = self.redis.script_load(self.script)
        except redis.RedisError:
            self.script_sha = None

    def allow_request(self) -> bool:
        """Check if request is allowed

        Returns:
            True if request allowed, False if rate limited
        """
        allowed, _ = self.allow_request_with_remaining()
        return allowed

    def allow_request_with_remaining(self) -> Tuple[bool, int]:
        """Check if request allowed and return remaining count

        Returns:
            Tuple of (allowed, remaining_requests)
        """
        now = time.time()
        # Generate unique ID for this request
        request_id = str(uuid.uuid4())

        try:
            result = self.redis.evalsha(
                self.script_sha,
                1,
                self.key,
                self.limit,
                self.window_seconds,
                now,
                request_id
            )

            allowed = bool(result[0])
            remaining = int(result[1])

            return allowed, remaining

        except redis.exceptions.NoScriptError:
            self.script_sha = self.redis.script_load(self.script)
            return self.allow_request_with_remaining()

        except redis.RedisError as e:
            print(f"Redis error in sliding window: {e}")
            return True, self.limit

    def get_remaining(self) -> int:
        """Get remaining requests in window

        Returns:
            Number of requests remaining
        """
        try:
            now = time.time()
            window_start = now - self.window_seconds

            # Clean old requests
            self.redis.zremrangebyscore(self.key, 0, window_start)

            # Count remaining
            count = self.redis.zcard(self.key)

            return max(0, self.limit - count)

        except redis.RedisError:
            return self.limit

    def get_oldest_request_time(self) -> float:
        """Get timestamp of oldest request in window

        Returns:
            Timestamp of oldest request (or current time if none)
        """
        try:
            now = time.time()
            window_start = now - self.window_seconds

            # Clean old requests
            self.redis.zremrangebyscore(self.key, 0, window_start)

            # Get oldest request
            oldest = self.redis.zrange(self.key, 0, 0, withscores=True)

            if oldest:
                return float(oldest[0][1])

            return now

        except redis.RedisError:
            return time.time()

    def get_reset_time(self) -> int:
        """Get timestamp when oldest request expires

        Returns:
            Unix timestamp when a slot becomes available
        """
        oldest = self.get_oldest_request_time()
        return int(oldest + self.window_seconds)


# Example usage
if __name__ == '__main__':
    # Create Redis connection
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )

    # Create sliding window rate limiter
    # Limit: 100 requests per 60 seconds (rolling window)
    limiter = SlidingWindow(
        redis_client,
        key="user:123",
        limit=100,
        window_seconds=60
    )

    # Check rate limit
    allowed, remaining = limiter.allow_request_with_remaining()

    if allowed:
        print(f"Request allowed. {remaining} remaining")
    else:
        reset = limiter.get_reset_time()
        retry_after = reset - int(time.time())
        print(f"Rate limited. Reset in {retry_after} seconds")

    # Check remaining without consuming
    remaining = limiter.get_remaining()
    print(f"Current remaining: {remaining}")
