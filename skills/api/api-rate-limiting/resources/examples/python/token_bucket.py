"""
Token Bucket Rate Limiter with Redis

Production-ready token bucket implementation using Redis for distributed
rate limiting.

Features:
- Atomic operations with Lua scripts
- Configurable capacity and refill rate
- Thread-safe distributed implementation
- Graceful error handling

Usage:
    limiter = TokenBucket(redis_client, "user:123", capacity=100, refill_rate=10)
    if limiter.consume():
        # Process request
        response = handle_request()
    else:
        # Rate limited
        return error_429()
"""

import redis
import time
from typing import Tuple


class TokenBucket:
    """Token bucket rate limiter with Redis backend

    Allows bursts while maintaining average rate over time.
    """

    def __init__(self, redis_client: redis.Redis, key: str,
                 capacity: int, refill_rate: float):
        """Initialize token bucket

        Args:
            redis_client: Redis connection
            key: Unique key for this rate limiter
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self.redis = redis_client
        self.key = f"rate_limit:token_bucket:{key}"
        self.capacity = capacity
        self.refill_rate = refill_rate

        # Lua script for atomic token bucket operations
        # This ensures consistency in distributed environments
        self.script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_needed = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])

        -- Get current state
        local state = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(state[1])
        local last_refill = tonumber(state[2])

        -- Initialize if this is the first request
        if not tokens then
            tokens = capacity
            last_refill = now
        end

        -- Refill tokens based on elapsed time
        local elapsed = now - last_refill
        local tokens_to_add = elapsed * refill_rate
        tokens = math.min(capacity, tokens + tokens_to_add)

        -- Check if enough tokens available
        if tokens >= tokens_needed then
            -- Consume tokens
            tokens = tokens - tokens_needed
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            -- Set expiration to prevent memory leak
            redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) * 2)
            return {1, tokens}  -- allowed, remaining
        else
            -- Not enough tokens
            return {0, tokens}  -- denied, remaining
        end
        """

        # Pre-load script for better performance
        try:
            self.script_sha = self.redis.script_load(self.script)
        except redis.RedisError:
            self.script_sha = None

    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens

        Args:
            tokens: Number of tokens to consume (default: 1)

        Returns:
            True if tokens consumed successfully, False if insufficient
        """
        allowed, _ = self.consume_with_remaining(tokens)
        return allowed

    def consume_with_remaining(self, tokens: int = 1) -> Tuple[bool, float]:
        """Attempt to consume tokens and return remaining count

        Args:
            tokens: Number of tokens to consume

        Returns:
            Tuple of (allowed, remaining_tokens)
        """
        now = time.time()

        try:
            # Execute Lua script atomically
            result = self.redis.evalsha(
                self.script_sha,
                1,  # number of keys
                self.key,
                self.capacity,
                self.refill_rate,
                tokens,
                now
            )

            allowed = bool(result[0])
            remaining = float(result[1])

            return allowed, remaining

        except redis.exceptions.NoScriptError:
            # Script not cached, reload and retry
            self.script_sha = self.redis.script_load(self.script)
            return self.consume_with_remaining(tokens)

        except redis.RedisError as e:
            # Log error and fail open (allow request)
            print(f"Redis error in token bucket: {e}")
            return True, float(self.capacity)

    def get_tokens(self) -> float:
        """Get current token count without consuming

        Returns:
            Current number of tokens
        """
        try:
            state = self.redis.hmget(self.key, 'tokens', 'last_refill')

            if not state[0]:
                return float(self.capacity)

            tokens = float(state[0])
            last_refill = float(state[1])
            now = time.time()

            # Calculate refilled tokens
            elapsed = now - last_refill
            tokens = min(self.capacity, tokens + (elapsed * self.refill_rate))

            return tokens

        except redis.RedisError:
            return float(self.capacity)

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time for tokens to be available

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds to wait until tokens available (0 if already available)
        """
        current = self.get_tokens()

        if current >= tokens:
            return 0.0

        # Calculate time to accumulate needed tokens
        deficit = tokens - current
        return deficit / self.refill_rate


# Example usage
if __name__ == '__main__':
    # Create Redis connection
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )

    # Create token bucket rate limiter
    # Capacity: 100 tokens (burst capacity)
    # Refill rate: 10 tokens/second (600 tokens/minute average)
    limiter = TokenBucket(
        redis_client,
        key="user:123",
        capacity=100,
        refill_rate=10
    )

    # Check rate limit
    if limiter.consume():
        print("Request allowed")
        print(f"Remaining tokens: {limiter.get_tokens():.2f}")
    else:
        wait = limiter.wait_time()
        print(f"Rate limited. Try again in {wait:.2f} seconds")

    # Consume multiple tokens (e.g., for expensive operations)
    if limiter.consume(tokens=5):
        print("Expensive operation allowed (5 tokens)")
    else:
        print("Not enough tokens for expensive operation")
