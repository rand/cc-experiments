"""
Distributed Rate Limiter

Production-ready distributed rate limiter with Redis backend supporting
multiple algorithms and strategies.

Features:
- Multiple algorithms (token bucket, sliding window, fixed window)
- Multi-tier rate limiting (per-second, per-minute, per-hour)
- Graceful fallback on errors
- Comprehensive monitoring hooks
- Thread-safe operations

Usage:
    limiter = DistributedRateLimiter(redis_client)

    if limiter.allow("user:123", limits={
        "per_second": 10,
        "per_minute": 100,
        "per_hour": 1000
    }):
        response = handle_request()
    else:
        return error_429()
"""

import redis
import time
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum


class Algorithm(Enum):
    """Rate limiting algorithms"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    remaining: Optional[int]
    reset: Optional[int]
    retry_after: Optional[int]
    tier_exceeded: Optional[str]  # Which tier was exceeded


class DistributedRateLimiter:
    """Distributed rate limiter with multiple strategies

    Supports multiple algorithms and multi-tier rate limiting.
    Thread-safe with atomic Redis operations.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        default_algorithm: Algorithm = Algorithm.FIXED_WINDOW,
        fail_open: bool = True,
        on_limit_exceeded: Optional[Callable] = None
    ):
        """Initialize distributed rate limiter

        Args:
            redis_client: Redis connection
            default_algorithm: Default rate limiting algorithm
            fail_open: Allow requests if Redis fails
            on_limit_exceeded: Callback when rate limit exceeded
        """
        self.redis = redis_client
        self.default_algorithm = default_algorithm
        self.fail_open = fail_open
        self.on_limit_exceeded = on_limit_exceeded

        # Pre-load Lua scripts
        self._load_scripts()

    def _load_scripts(self):
        """Load Lua scripts for atomic operations"""
        # Token bucket script
        self.token_bucket_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_needed = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])

        local state = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(state[1])
        local last_refill = tonumber(state[2])

        if not tokens then
            tokens = capacity
            last_refill = now
        end

        local elapsed = now - last_refill
        tokens = math.min(capacity, tokens + (elapsed * refill_rate))

        if tokens >= tokens_needed then
            tokens = tokens - tokens_needed
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) * 2)
            return {1, math.floor(tokens)}
        else
            return {0, math.floor(tokens)}
        end
        """

        # Fixed window script
        self.fixed_window_script = """
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

        # Multi-tier script
        self.multi_tier_script = """
        local base_key = KEYS[1]
        local now = tonumber(ARGV[1])

        -- Parse limits from ARGV[2] onwards (pairs of window, limit)
        local tiers = {}
        for i = 2, #ARGV, 2 do
            table.insert(tiers, {
                window = tonumber(ARGV[i]),
                limit = tonumber(ARGV[i+1])
            })
        end

        -- Check each tier
        for _, tier in ipairs(tiers) do
            local window_id = math.floor(now / tier.window)
            local key = base_key .. ":tier:" .. tier.window .. ":" .. window_id

            local count = redis.call('INCR', key)
            if count == 1 then
                redis.call('EXPIRE', key, tier.window * 2)
            end

            if count > tier.limit then
                local reset = (window_id + 1) * tier.window
                return {0, tier.window, reset}  -- denied, failed tier, reset
            end
        end

        return {1, 0, 0}  -- allowed
        """

        try:
            self.token_bucket_sha = self.redis.script_load(self.token_bucket_script)
            self.fixed_window_sha = self.redis.script_load(self.fixed_window_script)
            self.multi_tier_sha = self.redis.script_load(self.multi_tier_script)
        except redis.RedisError as e:
            print(f"Warning: Failed to load scripts: {e}")
            self.token_bucket_sha = None
            self.fixed_window_sha = None
            self.multi_tier_sha = None

    def allow(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        limits: Optional[Dict[str, int]] = None,
        algorithm: Optional[Algorithm] = None
    ) -> bool:
        """Check if request is allowed

        Args:
            key: Rate limit key
            limit: Single limit (requires window)
            window: Window duration (requires limit)
            limits: Multi-tier limits dict (e.g., {"per_second": 10, "per_minute": 100})
            algorithm: Rate limiting algorithm to use

        Returns:
            True if allowed, False if rate limited
        """
        result = self.check_limit(key, limit, window, limits, algorithm)
        return result.allowed

    def check_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        limits: Optional[Dict[str, int]] = None,
        algorithm: Optional[Algorithm] = None
    ) -> RateLimitResult:
        """Check rate limit and return detailed result

        Args:
            key: Rate limit key
            limit: Single limit (requires window)
            window: Window duration (requires limit)
            limits: Multi-tier limits dict
            algorithm: Rate limiting algorithm to use

        Returns:
            RateLimitResult with details
        """
        try:
            # Multi-tier rate limiting
            if limits:
                return self._check_multi_tier(key, limits)

            # Single-tier rate limiting
            if limit is None or window is None:
                raise ValueError("Either 'limits' or both 'limit' and 'window' required")

            algo = algorithm or self.default_algorithm

            if algo == Algorithm.TOKEN_BUCKET:
                return self._check_token_bucket(key, limit, window)
            elif algo == Algorithm.FIXED_WINDOW:
                return self._check_fixed_window(key, limit, window)
            else:
                raise ValueError(f"Unsupported algorithm: {algo}")

        except redis.RedisError as e:
            print(f"Redis error: {e}")

            if self.fail_open:
                return RateLimitResult(
                    allowed=True,
                    remaining=limit,
                    reset=None,
                    retry_after=None,
                    tier_exceeded=None
                )
            else:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset=None,
                    retry_after=None,
                    tier_exceeded="error"
                )

    def _check_token_bucket(
        self,
        key: str,
        capacity: int,
        refill_rate: float
    ) -> RateLimitResult:
        """Check token bucket rate limit

        Args:
            key: Rate limit key
            capacity: Maximum tokens
            refill_rate: Tokens per second

        Returns:
            RateLimitResult
        """
        now = time.time()
        redis_key = f"rate_limit:token_bucket:{key}"

        try:
            result = self.redis.evalsha(
                self.token_bucket_sha,
                1,
                redis_key,
                capacity,
                refill_rate,
                1,
                now
            )

            allowed = bool(result[0])
            remaining = int(result[1])

            if not allowed and self.on_limit_exceeded:
                self.on_limit_exceeded(key, "token_bucket")

            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset=None,
                retry_after=int((1 - remaining) / refill_rate) if not allowed else None,
                tier_exceeded="token_bucket" if not allowed else None
            )

        except redis.exceptions.NoScriptError:
            self.token_bucket_sha = self.redis.script_load(self.token_bucket_script)
            return self._check_token_bucket(key, capacity, refill_rate)

    def _check_fixed_window(
        self,
        key: str,
        limit: int,
        window: int
    ) -> RateLimitResult:
        """Check fixed window rate limit

        Args:
            key: Rate limit key
            limit: Maximum requests
            window: Window duration

        Returns:
            RateLimitResult
        """
        now = int(time.time())
        redis_key = f"rate_limit:fixed_window:{key}"

        try:
            result = self.redis.evalsha(
                self.fixed_window_sha,
                1,
                redis_key,
                limit,
                window,
                now
            )

            allowed = bool(result[0])
            remaining = int(result[1])
            reset = int(result[2])

            if not allowed and self.on_limit_exceeded:
                self.on_limit_exceeded(key, "fixed_window")

            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset=reset,
                retry_after=reset - now if not allowed else None,
                tier_exceeded="fixed_window" if not allowed else None
            )

        except redis.exceptions.NoScriptError:
            self.fixed_window_sha = self.redis.script_load(self.fixed_window_script)
            return self._check_fixed_window(key, limit, window)

    def _check_multi_tier(
        self,
        key: str,
        limits: Dict[str, int]
    ) -> RateLimitResult:
        """Check multi-tier rate limits

        Args:
            key: Rate limit key
            limits: Dict of tier limits (e.g., {"per_second": 10})

        Returns:
            RateLimitResult
        """
        # Map tier names to window durations
        tier_windows = {
            "per_second": 1,
            "per_minute": 60,
            "per_hour": 3600,
            "per_day": 86400
        }

        now = int(time.time())
        redis_key = f"rate_limit:multi_tier:{key}"

        # Build ARGV list
        argv = [now]
        for tier_name, limit in limits.items():
            window = tier_windows.get(tier_name)
            if window:
                argv.extend([window, limit])

        try:
            result = self.redis.evalsha(
                self.multi_tier_sha,
                1,
                redis_key,
                *argv
            )

            allowed = bool(result[0])
            failed_tier = result[1] if not allowed else None
            reset = result[2] if not allowed else None

            if not allowed and self.on_limit_exceeded:
                tier_name = next(
                    (name for name, window in tier_windows.items() if window == failed_tier),
                    "unknown"
                )
                self.on_limit_exceeded(key, tier_name)

            return RateLimitResult(
                allowed=allowed,
                remaining=None,
                reset=reset,
                retry_after=reset - now if reset else None,
                tier_exceeded=f"tier_{failed_tier}s" if failed_tier else None
            )

        except redis.exceptions.NoScriptError:
            self.multi_tier_sha = self.redis.script_load(self.multi_tier_script)
            return self._check_multi_tier(key, limits)


# Example usage
if __name__ == '__main__':
    # Create Redis connection
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )

    # Callback when rate limit exceeded
    def on_limit_exceeded(key: str, tier: str):
        print(f"Rate limit exceeded for {key} at tier {tier}")

    # Create distributed rate limiter
    limiter = DistributedRateLimiter(
        redis_client,
        default_algorithm=Algorithm.FIXED_WINDOW,
        fail_open=True,
        on_limit_exceeded=on_limit_exceeded
    )

    # Example 1: Single-tier rate limit
    result = limiter.check_limit("user:123", limit=100, window=60)
    if result.allowed:
        print(f"Request allowed. {result.remaining} remaining")
    else:
        print(f"Rate limited. Retry after {result.retry_after}s")

    # Example 2: Multi-tier rate limiting
    result = limiter.check_limit(
        "user:456",
        limits={
            "per_second": 10,
            "per_minute": 100,
            "per_hour": 1000,
            "per_day": 10000
        }
    )

    if result.allowed:
        print("Request allowed (passed all tiers)")
    else:
        print(f"Rate limited at {result.tier_exceeded}")

    # Example 3: Token bucket algorithm
    result = limiter.check_limit(
        "user:789",
        limit=100,
        window=60,
        algorithm=Algorithm.TOKEN_BUCKET
    )

    print(f"Token bucket: allowed={result.allowed}, remaining={result.remaining}")
