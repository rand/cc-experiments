"""
Redis Rate Limiter Examples

Implements sliding window and token bucket rate limiting algorithms.
"""

import time
import uuid
from typing import Tuple

import redis


class SlidingWindowRateLimiter:
    """
    Sliding Window Rate Limiter using Sorted Set

    Maintains a sliding time window of requests using timestamps as scores.
    """

    def __init__(self, redis_client: redis.Redis, limit: int, window: int):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis connection
            limit: Maximum requests allowed in window
            window: Time window in seconds
        """
        self.redis = redis_client
        self.limit = limit
        self.window = window

    def is_allowed(self, user_id: str) -> Tuple[bool, dict]:
        """
        Check if request is allowed.

        Args:
            user_id: User identifier

        Returns:
            Tuple of (allowed, info_dict)
        """
        key = f"rate:sliding:{user_id}"
        now = time.time()
        window_start = now - self.window

        # Start pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count requests in current window
        pipe.zcard(key)

        # Execute pipeline
        results = pipe.execute()
        current_count = results[1]

        if current_count < self.limit:
            # Add new request
            request_id = str(uuid.uuid4())
            self.redis.zadd(key, {request_id: now})
            self.redis.expire(key, self.window)

            return True, {
                "allowed": True,
                "current": current_count + 1,
                "limit": self.limit,
                "remaining": self.limit - current_count - 1,
                "reset_in": self.window
            }
        else:
            # Get oldest request timestamp
            oldest = self.redis.zrange(key, 0, 0, withscores=True)
            reset_in = int(oldest[0][1] + self.window - now) if oldest else self.window

            return False, {
                "allowed": False,
                "current": current_count,
                "limit": self.limit,
                "remaining": 0,
                "reset_in": reset_in
            }


class TokenBucketRateLimiter:
    """
    Token Bucket Rate Limiter using Lua Script

    Refills tokens at a constant rate, allows bursts up to capacity.
    """

    def __init__(self, redis_client: redis.Redis, rate: float, capacity: int):
        """
        Initialize token bucket rate limiter.

        Args:
            redis_client: Redis connection
            rate: Token refill rate (tokens per second)
            capacity: Maximum tokens in bucket
        """
        self.redis = redis_client
        self.rate = rate
        self.capacity = capacity

        # Lua script for atomic token bucket
        self.lua_script = """
        local tokens_key = KEYS[1]
        local timestamp_key = KEYS[2]
        local rate = tonumber(ARGV[1])
        local capacity = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local requested = tonumber(ARGV[4])

        local last_tokens = tonumber(redis.call('GET', tokens_key))
        if last_tokens == nil then
            last_tokens = capacity
        end

        local last_refreshed = tonumber(redis.call('GET', timestamp_key))
        if last_refreshed == nil then
            last_refreshed = 0
        end

        local delta = math.max(0, now - last_refreshed)
        local filled_tokens = math.min(capacity, last_tokens + (delta * rate))
        local allowed = filled_tokens >= requested
        local new_tokens = filled_tokens

        if allowed then
            new_tokens = filled_tokens - requested
        end

        redis.call('SETEX', tokens_key, 86400, new_tokens)
        redis.call('SETEX', timestamp_key, 86400, now)

        return {
            allowed and 1 or 0,
            new_tokens,
            capacity
        }
        """

        self.script_sha = self.redis.script_load(self.lua_script)

    def is_allowed(self, user_id: str, tokens: int = 1) -> Tuple[bool, dict]:
        """
        Check if request is allowed and consume tokens.

        Args:
            user_id: User identifier
            tokens: Number of tokens to consume (default: 1)

        Returns:
            Tuple of (allowed, info_dict)
        """
        tokens_key = f"rate:tokens:{user_id}"
        timestamp_key = f"rate:timestamp:{user_id}"
        now = time.time()

        # Execute Lua script
        result = self.redis.evalsha(
            self.script_sha,
            2,
            tokens_key,
            timestamp_key,
            self.rate,
            self.capacity,
            now,
            tokens
        )

        allowed = bool(result[0])
        current_tokens = float(result[1])
        capacity = int(result[2])

        return allowed, {
            "allowed": allowed,
            "tokens_remaining": current_tokens,
            "capacity": capacity,
            "refill_rate": self.rate
        }


class FixedWindowRateLimiter:
    """
    Fixed Window Rate Limiter using String Counter

    Simple counter-based rate limiting with fixed time windows.
    """

    def __init__(self, redis_client: redis.Redis, limit: int, window: int):
        """
        Initialize fixed window rate limiter.

        Args:
            redis_client: Redis connection
            limit: Maximum requests allowed in window
            window: Time window in seconds
        """
        self.redis = redis_client
        self.limit = limit
        self.window = window

    def is_allowed(self, user_id: str) -> Tuple[bool, dict]:
        """
        Check if request is allowed.

        Args:
            user_id: User identifier

        Returns:
            Tuple of (allowed, info_dict)
        """
        # Create key with current time window
        now = int(time.time())
        window_id = now // self.window
        key = f"rate:fixed:{user_id}:{window_id}"

        # Increment counter
        current = self.redis.incr(key)

        if current == 1:
            # Set expiration on first request in window
            self.redis.expire(key, self.window * 2)  # Extra time for safety

        allowed = current <= self.limit
        reset_in = self.window - (now % self.window)

        return allowed, {
            "allowed": allowed,
            "current": current,
            "limit": self.limit,
            "remaining": max(0, self.limit - current),
            "reset_in": reset_in
        }


def demo_sliding_window():
    """Demonstrate sliding window rate limiter."""
    print("\n" + "=" * 60)
    print("Sliding Window Rate Limiter Demo")
    print("=" * 60)

    redis_client = redis.Redis()
    limiter = SlidingWindowRateLimiter(redis_client, limit=5, window=10)

    user_id = "user:1000"

    print(f"\nLimit: 5 requests per 10 seconds")
    print(f"User: {user_id}\n")

    # Make 7 requests
    for i in range(1, 8):
        allowed, info = limiter.is_allowed(user_id)

        status = "✓ ALLOWED" if allowed else "✗ DENIED"
        print(f"Request {i}: {status}")
        print(f"  Current: {info['current']}/{info['limit']}")
        print(f"  Remaining: {info['remaining']}")
        print(f"  Reset in: {info['reset_in']}s")

        if i == 3:
            print("\n  [Pausing 2 seconds...]")
            time.sleep(2)

    # Wait and try again
    print("\n  [Waiting 10 seconds for window to slide...]")
    time.sleep(10)

    print("\nAfter waiting 10 seconds:")
    allowed, info = limiter.is_allowed(user_id)
    status = "✓ ALLOWED" if allowed else "✗ DENIED"
    print(f"Request: {status}")
    print(f"  Current: {info['current']}/{info['limit']}")

    # Cleanup
    redis_client.delete(f"rate:sliding:{user_id}")


def demo_token_bucket():
    """Demonstrate token bucket rate limiter."""
    print("\n" + "=" * 60)
    print("Token Bucket Rate Limiter Demo")
    print("=" * 60)

    redis_client = redis.Redis()
    # 2 tokens per second, capacity of 10
    limiter = TokenBucketRateLimiter(redis_client, rate=2.0, capacity=10)

    user_id = "user:2000"

    print(f"\nRate: 2 tokens/second")
    print(f"Capacity: 10 tokens")
    print(f"User: {user_id}\n")

    # Burst: consume 10 tokens quickly
    print("--- Burst scenario (10 requests immediately) ---")
    for i in range(1, 11):
        allowed, info = limiter.is_allowed(user_id)
        status = "✓ ALLOWED" if allowed else "✗ DENIED"
        print(f"Request {i}: {status} (tokens: {info['tokens_remaining']:.1f})")

    # 11th request should be denied
    print("\n--- 11th request (should be denied) ---")
    allowed, info = limiter.is_allowed(user_id)
    status = "✓ ALLOWED" if allowed else "✗ DENIED"
    print(f"Request: {status} (tokens: {info['tokens_remaining']:.1f})")

    # Wait for refill
    print("\n  [Waiting 2 seconds for token refill...]")
    time.sleep(2)

    # Should have ~4 tokens now (2 tokens/sec * 2 sec)
    print("\n--- After 2 seconds (should have ~4 tokens) ---")
    allowed, info = limiter.is_allowed(user_id)
    status = "✓ ALLOWED" if allowed else "✗ DENIED"
    print(f"Request: {status} (tokens: {info['tokens_remaining']:.1f})")

    # Cleanup
    redis_client.delete(f"rate:tokens:{user_id}", f"rate:timestamp:{user_id}")


def demo_fixed_window():
    """Demonstrate fixed window rate limiter."""
    print("\n" + "=" * 60)
    print("Fixed Window Rate Limiter Demo")
    print("=" * 60)

    redis_client = redis.Redis()
    limiter = FixedWindowRateLimiter(redis_client, limit=3, window=5)

    user_id = "user:3000"

    print(f"\nLimit: 3 requests per 5 seconds")
    print(f"User: {user_id}\n")

    # Make 5 requests
    for i in range(1, 6):
        allowed, info = limiter.is_allowed(user_id)

        status = "✓ ALLOWED" if allowed else "✗ DENIED"
        print(f"Request {i}: {status}")
        print(f"  Current: {info['current']}/{info['limit']}")
        print(f"  Remaining: {info['remaining']}")
        print(f"  Reset in: {info['reset_in']}s")

        if i == 4:
            print(f"\n  [Waiting {info['reset_in']} seconds for window reset...]")
            time.sleep(info['reset_in'] + 1)
            print()


def demo_rate_limiter_comparison():
    """Compare different rate limiters."""
    print("\n" + "=" * 60)
    print("Rate Limiter Comparison")
    print("=" * 60)

    redis_client = redis.Redis()

    sliding = SlidingWindowRateLimiter(redis_client, limit=10, window=10)
    token = TokenBucketRateLimiter(redis_client, rate=1.0, capacity=10)
    fixed = FixedWindowRateLimiter(redis_client, limit=10, window=10)

    print("\nScenario: 15 requests immediately, then wait 5 seconds, then 5 more\n")

    for name, limiter, user_base in [
        ("Sliding Window", sliding, "user:sliding:"),
        ("Token Bucket", token, "user:token:"),
        ("Fixed Window", fixed, "user:fixed:")
    ]:
        print(f"\n--- {name} ---")
        user_id = f"{user_base}test"

        allowed_count = 0

        # First burst
        print("Burst 1 (15 requests):")
        for _ in range(15):
            allowed, _ = limiter.is_allowed(user_id)
            if allowed:
                allowed_count += 1

        print(f"  Allowed: {allowed_count}/15")

        # Wait
        time.sleep(5)

        # Second burst
        print("After 5 seconds (5 more requests):")
        burst2_allowed = 0
        for _ in range(5):
            allowed, _ = limiter.is_allowed(user_id)
            if allowed:
                burst2_allowed += 1

        print(f"  Allowed: {burst2_allowed}/5")
        print(f"  Total: {allowed_count + burst2_allowed}/20")

        # Cleanup
        redis_client.delete(f"rate:*:{user_id}*")


def demo_api_rate_limiting():
    """Simulate API rate limiting."""
    print("\n" + "=" * 60)
    print("API Rate Limiting Simulation")
    print("=" * 60)

    redis_client = redis.Redis()

    # Different tiers
    free_tier = SlidingWindowRateLimiter(redis_client, limit=10, window=60)
    premium_tier = SlidingWindowRateLimiter(redis_client, limit=100, window=60)

    users = {
        "free_user": free_tier,
        "premium_user": premium_tier
    }

    print("\nFree tier: 10 requests/minute")
    print("Premium tier: 100 requests/minute\n")

    for user_id, limiter in users.items():
        print(f"--- {user_id} ---")

        # Simulate API requests
        requests_made = 0
        requests_denied = 0

        for i in range(15):
            allowed, info = limiter.is_allowed(user_id)

            if allowed:
                requests_made += 1
            else:
                requests_denied += 1

        print(f"Requests made: {requests_made}")
        print(f"Requests denied: {requests_denied}")
        print(f"Success rate: {requests_made / 15 * 100:.1f}%\n")

        # Cleanup
        redis_client.delete(f"rate:sliding:{user_id}")


def main():
    """Run all demos."""
    try:
        demo_sliding_window()
        demo_token_bucket()
        demo_fixed_window()
        demo_rate_limiter_comparison()
        demo_api_rate_limiting()

        print("\n" + "=" * 60)
        print("All demos completed!")
        print("=" * 60)
    except redis.exceptions.ConnectionError:
        print("Error: Cannot connect to Redis. Make sure Redis is running.")
        print("Start Redis with: redis-server")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
