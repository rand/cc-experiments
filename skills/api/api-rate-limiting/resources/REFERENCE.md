# API Rate Limiting Reference

> **Comprehensive technical reference for rate limiting algorithms, implementations, and best practices**

## Table of Contents

1. [Fundamentals](#fundamentals)
2. [Rate Limiting Algorithms](#rate-limiting-algorithms)
3. [Distributed Rate Limiting](#distributed-rate-limiting)
4. [HTTP Headers and Standards](#http-headers-and-standards)
5. [Storage Backends](#storage-backends)
6. [Implementation Patterns](#implementation-patterns)
7. [Limiting Strategies](#limiting-strategies)
8. [Error Handling and Responses](#error-handling-and-responses)
9. [Performance and Scalability](#performance-and-scalability)
10. [Security Considerations](#security-considerations)
11. [Testing and Monitoring](#testing-and-monitoring)
12. [Common Anti-Patterns](#common-anti-patterns)
13. [Language-Specific Implementations](#language-specific-implementations)
14. [References and Standards](#references-and-standards)

---

## Fundamentals

### What is Rate Limiting?

**Rate limiting** is a technique for controlling the rate at which clients can make requests to an API or service. It prevents abuse, ensures fair resource allocation, and protects services from being overwhelmed.

### Why Rate Limit?

**Primary objectives**:
1. **Prevent abuse**: Stop malicious actors from overwhelming your service
2. **Ensure fair usage**: Distribute resources equitably among users
3. **Control costs**: Limit expensive operations (database queries, external API calls)
4. **Maintain stability**: Prevent cascading failures under high load
5. **Business monetization**: Differentiate service tiers

### Rate Limiting vs Throttling

```
RATE LIMITING
├─ Hard limits enforced
├─ Requests rejected when exceeded
├─ Clear quotas communicated
└─ 429 Too Many Requests response

THROTTLING
├─ Soft limits enforced
├─ Requests slowed/delayed
├─ Queuing mechanisms
└─ May not return errors
```

### Key Metrics

**Requests Per Second (RPS)**:
```
RPS = Total Requests / Time Period (seconds)

Example: 100 requests in 10 seconds = 10 RPS
```

**Burst Capacity**:
- Maximum requests allowed in short time window
- Important for handling traffic spikes
- Typically higher than sustained rate

**Window Duration**:
- Time period for counting requests
- Common: 1 second, 1 minute, 1 hour, 1 day
- Trade-off: Shorter = smoother, Longer = simpler

---

## Rate Limiting Algorithms

### Token Bucket Algorithm

**Description**: Tokens added to bucket at fixed rate. Each request consumes tokens. Request rejected if insufficient tokens available.

**Characteristics**:
- Allows bursts (up to bucket capacity)
- Smooth average rate over time
- Good for credit-based systems

**Parameters**:
- `capacity`: Maximum tokens in bucket
- `refill_rate`: Tokens added per second
- `tokens_per_request`: Tokens consumed per request (usually 1)

**Mathematical Model**:
```
tokens(t) = min(capacity, tokens(t-1) + refill_rate * Δt)

allowed = tokens(t) >= tokens_needed
if allowed:
    tokens(t) = tokens(t) - tokens_needed
```

**Python Implementation**:
```python
import time
from typing import Optional

class TokenBucket:
    """Token bucket rate limiter

    Allows bursts while maintaining average rate.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens for time elapsed
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens consumed, False if insufficient
        """
        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def get_tokens(self) -> float:
        """Get current token count"""
        with self._lock:
            self._refill()
            return self.tokens

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time for tokens

        Returns:
            Seconds to wait until tokens available
        """
        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                return 0.0

            deficit = tokens - self.tokens
            return deficit / self.refill_rate

# Usage example
limiter = TokenBucket(capacity=100, refill_rate=10)  # 10 tokens/sec

if limiter.consume():
    # Process request
    response = handle_request()
else:
    # Rate limited
    wait = limiter.wait_time()
    return error_response(f"Rate limited. Try again in {wait:.1f} seconds", 429)
```

**Distributed Implementation (Redis + Lua)**:
```python
import redis
import time

class DistributedTokenBucket:
    """Distributed token bucket using Redis"""

    def __init__(self, redis_client: redis.Redis, key: str,
                 capacity: int, refill_rate: float):
        self.redis = redis_client
        self.key = f"rate_limit:token_bucket:{key}"
        self.capacity = capacity
        self.refill_rate = refill_rate

        # Lua script for atomic token bucket operations
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

        -- Initialize if needed
        if not tokens then
            tokens = capacity
            last_refill = now
        end

        -- Refill tokens
        local elapsed = now - last_refill
        tokens = math.min(capacity, tokens + (elapsed * refill_rate))

        -- Check if enough tokens
        if tokens >= tokens_needed then
            tokens = tokens - tokens_needed
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) * 2)
            return {1, tokens}  -- allowed, remaining
        else
            return {0, tokens}  -- denied, remaining
        end
        """

        self.script_sha = self.redis.script_load(self.script)

    def consume(self, tokens: int = 1) -> tuple[bool, float]:
        """Attempt to consume tokens

        Returns:
            (allowed, remaining_tokens)
        """
        now = time.time()

        try:
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
            # Script not cached, reload
            self.script_sha = self.redis.script_load(self.script)
            return self.consume(tokens)

# Usage
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
limiter = DistributedTokenBucket(redis_client, "user:123", capacity=100, refill_rate=10)

allowed, remaining = limiter.consume()
if allowed:
    print(f"Request allowed. {remaining:.1f} tokens remaining")
else:
    print(f"Rate limited. {remaining:.1f} tokens available")
```

**Best For**:
- APIs with bursty traffic patterns
- Credit-based systems
- Flexible rate limiting with burst tolerance

**Pros**:
- Simple to understand and implement
- Allows bursts while maintaining average rate
- Low memory footprint
- Fast operations

**Cons**:
- Allows bursts (may not be desired)
- Slightly more complex than fixed window

---

### Leaky Bucket Algorithm

**Description**: Requests enter a queue (bucket). Processed at fixed rate (leak). Requests rejected if queue full.

**Characteristics**:
- Smooths traffic to constant rate
- No bursts allowed
- Queue-based approach

**Parameters**:
- `capacity`: Maximum queue size
- `leak_rate`: Requests processed per second

**Mathematical Model**:
```
queue_size(t) = max(0, queue_size(t-1) - leak_rate * Δt)

if queue_size(t) < capacity:
    queue_size(t) = queue_size(t) + 1
    allowed = true
else:
    allowed = false
```

**Python Implementation**:
```python
import time
import threading
from collections import deque

class LeakyBucket:
    """Leaky bucket rate limiter

    Processes requests at constant rate.
    """

    def __init__(self, capacity: int, leak_rate: float):
        """
        Args:
            capacity: Maximum queue size
            leak_rate: Requests processed per second
        """
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.queue_size = 0.0
        self.last_leak = time.time()
        self._lock = threading.Lock()

    def _leak(self) -> None:
        """Process (leak) requests based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_leak

        # Leak (process) requests
        leaked = elapsed * self.leak_rate
        self.queue_size = max(0.0, self.queue_size - leaked)
        self.last_leak = now

    def allow_request(self) -> bool:
        """Check if request can be queued

        Returns:
            True if space available in queue
        """
        with self._lock:
            self._leak()

            if self.queue_size < self.capacity:
                self.queue_size += 1.0
                return True

            return False

    def get_queue_size(self) -> float:
        """Get current queue size"""
        with self._lock:
            self._leak()
            return self.queue_size

# Usage
limiter = LeakyBucket(capacity=50, leak_rate=5)  # 5 requests/sec

if limiter.allow_request():
    # Queue request
    response = handle_request()
else:
    # Queue full
    return error_response("Rate limited. Queue full.", 429)
```

**Distributed Implementation (Redis)**:
```python
import redis
import time

class DistributedLeakyBucket:
    """Distributed leaky bucket using Redis"""

    def __init__(self, redis_client: redis.Redis, key: str,
                 capacity: int, leak_rate: float):
        self.redis = redis_client
        self.key = f"rate_limit:leaky_bucket:{key}"
        self.capacity = capacity
        self.leak_rate = leak_rate

        self.script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local leak_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])

        local state = redis.call('HMGET', key, 'size', 'last_leak')
        local size = tonumber(state[1]) or 0
        local last_leak = tonumber(state[2]) or now

        -- Leak based on time elapsed
        local elapsed = now - last_leak
        local leaked = elapsed * leak_rate
        size = math.max(0, size - leaked)

        -- Check if space available
        if size < capacity then
            size = size + 1
            redis.call('HMSET', key, 'size', size, 'last_leak', now)
            redis.call('EXPIRE', key, math.ceil(capacity / leak_rate) * 2)
            return {1, capacity - size}  -- allowed, remaining
        else
            return {0, 0}  -- denied
        end
        """

        self.script_sha = self.redis.script_load(self.script)

    def allow_request(self) -> tuple[bool, float]:
        """Check if request can be queued

        Returns:
            (allowed, remaining_capacity)
        """
        now = time.time()

        try:
            result = self.redis.evalsha(
                self.script_sha,
                1,
                self.key,
                self.capacity,
                self.leak_rate,
                now
            )

            return bool(result[0]), float(result[1])

        except redis.exceptions.NoScriptError:
            self.script_sha = self.redis.script_load(self.script)
            return self.allow_request()
```

**Best For**:
- Protecting downstream services
- Guaranteed constant load
- Queue-based processing

**Pros**:
- Smooth, predictable rate
- No bursts
- Protects downstream services

**Cons**:
- No burst tolerance
- May delay requests
- More complex than token bucket

---

### Fixed Window Algorithm

**Description**: Time divided into fixed windows. Counter increments per request. Counter resets at window boundary.

**Characteristics**:
- Simple to implement
- Easy to understand
- Allows bursts at boundaries

**Parameters**:
- `limit`: Maximum requests per window
- `window_duration`: Length of time window (seconds)

**Mathematical Model**:
```
window_id = floor(timestamp / window_duration)
count[window_id] = count[window_id] + 1

allowed = count[window_id] <= limit
```

**Problem: Boundary Burst**:
```
Window 1 (11:59:00 - 11:59:59): 100 requests at 11:59:59
Window 2 (12:00:00 - 12:00:59): 100 requests at 12:00:00

Result: 200 requests in 1 second (burst at boundary)
```

**Python Implementation**:
```python
import time
import threading
from collections import defaultdict

class FixedWindow:
    """Fixed window rate limiter

    Simple per-period limits with boundary bursts.
    """

    def __init__(self, limit: int, window_seconds: int):
        """
        Args:
            limit: Maximum requests per window
            window_seconds: Duration of window in seconds
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.counters = defaultdict(int)
        self._lock = threading.Lock()

    def _get_window_id(self) -> int:
        """Get current window identifier"""
        return int(time.time() // self.window_seconds)

    def allow_request(self) -> bool:
        """Check if request is allowed

        Returns:
            True if under limit, False otherwise
        """
        with self._lock:
            window_id = self._get_window_id()

            # Clean old windows (optional optimization)
            old_windows = [wid for wid in self.counters if wid < window_id - 1]
            for wid in old_windows:
                del self.counters[wid]

            # Check limit
            if self.counters[window_id] < self.limit:
                self.counters[window_id] += 1
                return True

            return False

    def get_remaining(self) -> int:
        """Get remaining requests in current window"""
        with self._lock:
            window_id = self._get_window_id()
            count = self.counters[window_id]
            return max(0, self.limit - count)

    def get_reset_time(self) -> int:
        """Get timestamp when window resets"""
        window_id = self._get_window_id()
        return int((window_id + 1) * self.window_seconds)

# Usage
limiter = FixedWindow(limit=100, window_seconds=60)  # 100 req/min

if limiter.allow_request():
    response = handle_request()
else:
    reset_time = limiter.get_reset_time()
    retry_after = reset_time - int(time.time())
    return error_response(f"Rate limited. Try in {retry_after}s", 429)
```

**Distributed Implementation (Redis)**:
```python
import redis
import time

class DistributedFixedWindow:
    """Distributed fixed window using Redis"""

    def __init__(self, redis_client: redis.Redis, key: str,
                 limit: int, window_seconds: int):
        self.redis = redis_client
        self.key_prefix = f"rate_limit:fixed_window:{key}"
        self.limit = limit
        self.window_seconds = window_seconds

    def _get_window_key(self) -> str:
        """Get Redis key for current window"""
        window_id = int(time.time() // self.window_seconds)
        return f"{self.key_prefix}:{window_id}"

    def allow_request(self) -> tuple[bool, int, int]:
        """Check if request is allowed

        Returns:
            (allowed, remaining, reset_time)
        """
        key = self._get_window_key()

        # Increment counter atomically
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window_seconds * 2)  # TTL safety margin
        results = pipe.execute()

        count = results[0]
        allowed = count <= self.limit
        remaining = max(0, self.limit - count)

        # Calculate reset time
        window_id = int(time.time() // self.window_seconds)
        reset_time = int((window_id + 1) * self.window_seconds)

        return allowed, remaining, reset_time

    def get_remaining(self) -> int:
        """Get remaining requests in current window"""
        key = self._get_window_key()
        count = int(self.redis.get(key) or 0)
        return max(0, self.limit - count)

# Usage
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
limiter = DistributedFixedWindow(redis_client, "user:123", limit=100, window_seconds=60)

allowed, remaining, reset_time = limiter.allow_request()
if allowed:
    # Add headers
    response.headers['X-RateLimit-Limit'] = str(limiter.limit)
    response.headers['X-RateLimit-Remaining'] = str(remaining)
    response.headers['X-RateLimit-Reset'] = str(reset_time)
else:
    retry_after = reset_time - int(time.time())
    return error_response(f"Rate limited. Reset in {retry_after}s", 429)
```

**Best For**:
- Simple quota enforcement
- Easy user communication
- Low complexity requirements

**Pros**:
- Extremely simple
- Low memory usage
- Fast operations
- Easy to explain to users

**Cons**:
- Allows boundary bursts (2x limit in 1 second)
- Not smooth rate limiting

---

### Sliding Window Algorithm

**Description**: Track request timestamps. Count requests in rolling time window. Remove old requests outside window.

**Characteristics**:
- Smooth rate limiting
- No boundary bursts
- Higher memory usage

**Parameters**:
- `limit`: Maximum requests in window
- `window_duration`: Rolling window size (seconds)

**Mathematical Model**:
```
window_start = current_time - window_duration
requests_in_window = count(requests where timestamp >= window_start)

allowed = requests_in_window < limit
```

**Python Implementation**:
```python
import time
import threading
from collections import deque

class SlidingWindow:
    """Sliding window rate limiter

    Smooth rate limiting without boundary bursts.
    """

    def __init__(self, limit: int, window_seconds: int):
        """
        Args:
            limit: Maximum requests in window
            window_seconds: Rolling window duration
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests = deque()
        self._lock = threading.Lock()

    def _clean_old_requests(self, now: float) -> None:
        """Remove requests outside window"""
        window_start = now - self.window_seconds

        while self.requests and self.requests[0] < window_start:
            self.requests.popleft()

    def allow_request(self) -> bool:
        """Check if request is allowed

        Returns:
            True if under limit, False otherwise
        """
        with self._lock:
            now = time.time()
            self._clean_old_requests(now)

            if len(self.requests) < self.limit:
                self.requests.append(now)
                return True

            return False

    def get_remaining(self) -> int:
        """Get remaining requests in window"""
        with self._lock:
            now = time.time()
            self._clean_old_requests(now)
            return max(0, self.limit - len(self.requests))

    def get_oldest_request_time(self) -> float:
        """Get timestamp of oldest request in window"""
        with self._lock:
            now = time.time()
            self._clean_old_requests(now)

            if self.requests:
                return self.requests[0]
            return now

# Usage
limiter = SlidingWindow(limit=100, window_seconds=60)

if limiter.allow_request():
    response = handle_request()
else:
    # Calculate when next request allowed
    oldest = limiter.get_oldest_request_time()
    retry_after = int(oldest + limiter.window_seconds - time.time())
    return error_response(f"Rate limited. Try in {retry_after}s", 429)
```

**Distributed Implementation (Redis Sorted Sets)**:
```python
import redis
import time
import uuid

class DistributedSlidingWindow:
    """Distributed sliding window using Redis sorted sets"""

    def __init__(self, redis_client: redis.Redis, key: str,
                 limit: int, window_seconds: int):
        self.redis = redis_client
        self.key = f"rate_limit:sliding_window:{key}"
        self.limit = limit
        self.window_seconds = window_seconds

        # Lua script for atomic operations
        self.script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local request_id = ARGV[4]

        local window_start = now - window

        -- Remove old requests
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

        -- Count requests in window
        local count = redis.call('ZCARD', key)

        if count < limit then
            -- Add current request
            redis.call('ZADD', key, now, request_id)
            redis.call('EXPIRE', key, window * 2)
            return {1, limit - count - 1}  -- allowed, remaining
        else
            return {0, 0}  -- denied
        end
        """

        self.script_sha = self.redis.script_load(self.script)

    def allow_request(self) -> tuple[bool, int]:
        """Check if request is allowed

        Returns:
            (allowed, remaining)
        """
        now = time.time()
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

            return bool(result[0]), int(result[1])

        except redis.exceptions.NoScriptError:
            self.script_sha = self.redis.script_load(self.script)
            return self.allow_request()

    def get_remaining(self) -> int:
        """Get remaining requests in window"""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests
        self.redis.zremrangebyscore(self.key, 0, window_start)

        # Count remaining
        count = self.redis.zcard(self.key)
        return max(0, self.limit - count)

    def get_oldest_request(self) -> float:
        """Get timestamp of oldest request in window"""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests
        self.redis.zremrangebyscore(self.key, 0, window_start)

        # Get oldest
        oldest = self.redis.zrange(self.key, 0, 0, withscores=True)
        if oldest:
            return float(oldest[0][1])
        return now

# Usage
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
limiter = DistributedSlidingWindow(redis_client, "user:123", limit=100, window_seconds=60)

allowed, remaining = limiter.allow_request()
if allowed:
    print(f"Request allowed. {remaining} remaining")
else:
    oldest = limiter.get_oldest_request()
    retry_after = int(oldest + limiter.window_seconds - time.time())
    print(f"Rate limited. Try in {retry_after} seconds")
```

**Best For**:
- Fair rate limiting
- Preventing boundary bursts
- High-accuracy requirements

**Pros**:
- No boundary bursts
- Smooth rate limiting
- Fair to all users
- Accurate limiting

**Cons**:
- Higher memory usage (stores timestamps)
- More complex implementation
- Slower than fixed window

---

### Sliding Window Counter (Hybrid)

**Description**: Combines fixed window simplicity with sliding window accuracy. Uses weighted counts from current and previous windows.

**Mathematical Model**:
```
current_window_count = requests in current window
previous_window_count = requests in previous window

window_progress = (current_time % window_duration) / window_duration
estimated_count = (previous_window_count * (1 - window_progress)) + current_window_count

allowed = estimated_count < limit
```

**Python Implementation**:
```python
import time
import threading
from collections import defaultdict

class SlidingWindowCounter:
    """Sliding window counter (hybrid approach)

    Approximates sliding window with fixed window simplicity.
    """

    def __init__(self, limit: int, window_seconds: int):
        """
        Args:
            limit: Maximum requests in window
            window_seconds: Window duration
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.counters = defaultdict(int)
        self._lock = threading.Lock()

    def _get_window_id(self, timestamp: float) -> int:
        """Get window ID for timestamp"""
        return int(timestamp // self.window_seconds)

    def _estimate_count(self, now: float) -> float:
        """Estimate request count in sliding window"""
        current_window = self._get_window_id(now)
        previous_window = current_window - 1

        # Get counts
        current_count = self.counters[current_window]
        previous_count = self.counters[previous_window]

        # Calculate weight for previous window
        window_progress = (now % self.window_seconds) / self.window_seconds
        previous_weight = 1.0 - window_progress

        # Weighted sum
        return (previous_count * previous_weight) + current_count

    def allow_request(self) -> bool:
        """Check if request is allowed

        Returns:
            True if under limit, False otherwise
        """
        with self._lock:
            now = time.time()
            estimated = self._estimate_count(now)

            if estimated < self.limit:
                current_window = self._get_window_id(now)
                self.counters[current_window] += 1

                # Clean old windows
                old_window = current_window - 2
                if old_window in self.counters:
                    del self.counters[old_window]

                return True

            return False

    def get_remaining(self) -> int:
        """Get remaining requests (approximate)"""
        with self._lock:
            now = time.time()
            estimated = self._estimate_count(now)
            return max(0, int(self.limit - estimated))

# Usage
limiter = SlidingWindowCounter(limit=100, window_seconds=60)

if limiter.allow_request():
    response = handle_request()
else:
    return error_response("Rate limited", 429)
```

**Best For**:
- Balance between accuracy and simplicity
- Lower memory than pure sliding window
- Better than fixed window for boundary cases

**Pros**:
- More accurate than fixed window
- Less memory than pure sliding window
- Good balance of trade-offs

**Cons**:
- Approximate (not exact)
- Still allows some boundary bursts (reduced)

---

## Distributed Rate Limiting

### Redis-Based Rate Limiting

**Why Redis?**
- Atomic operations (INCR, ZADD, Lua scripts)
- Fast in-memory storage
- Built-in expiration (TTL)
- Distributed consistency
- High availability (Redis Sentinel, Cluster)

**Connection Patterns**:
```python
import redis
from redis.cluster import RedisCluster
from redis.sentinel import Sentinel

# Single Redis instance
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True,
    socket_timeout=1.0,
    socket_connect_timeout=1.0,
    retry_on_timeout=True
)

# Redis Sentinel (high availability)
sentinel = Sentinel(
    [('sentinel1', 26379), ('sentinel2', 26379)],
    socket_timeout=1.0
)
redis_client = sentinel.master_for('mymaster', socket_timeout=1.0)

# Redis Cluster (sharding)
redis_client = RedisCluster(
    host='redis-cluster',
    port=6379,
    decode_responses=True
)

# Connection pooling
pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,
    decode_responses=True
)
redis_client = redis.Redis(connection_pool=pool)
```

**Lua Scripts for Atomicity**:
```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Token bucket Lua script
token_bucket_script = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local tokens_needed = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

local state = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(state[1]) or capacity
local last_refill = tonumber(state[2]) or now

-- Refill
local elapsed = now - last_refill
tokens = math.min(capacity, tokens + (elapsed * refill_rate))

-- Consume
if tokens >= tokens_needed then
    tokens = tokens - tokens_needed
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return {1, tokens}
else
    return {0, tokens}
end
"""

# Load script
script_sha = redis_client.script_load(token_bucket_script)

# Execute atomically
def check_rate_limit(user_id: str, capacity: int, refill_rate: float, tokens: int = 1):
    import time
    now = time.time()

    result = redis_client.evalsha(
        script_sha,
        1,  # number of keys
        f"rate_limit:{user_id}",  # KEYS[1]
        capacity,  # ARGV[1]
        refill_rate,  # ARGV[2]
        tokens,  # ARGV[3]
        now  # ARGV[4]
    )

    allowed = bool(result[0])
    remaining = float(result[1])

    return allowed, remaining

# Usage
allowed, remaining = check_rate_limit("user:123", capacity=100, refill_rate=10)
```

**Error Handling**:
```python
import redis
import logging

logger = logging.getLogger(__name__)

def rate_limit_with_fallback(limiter_func, *args, **kwargs):
    """Rate limit with fallback on Redis failure

    Fail-open strategy: Allow requests if Redis unavailable
    """
    try:
        return limiter_func(*args, **kwargs)

    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        return True  # Fail open (allow request)

    except redis.exceptions.TimeoutError as e:
        logger.error(f"Redis timeout: {e}")
        return True  # Fail open

    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error: {e}")
        return True  # Fail open

    except Exception as e:
        logger.exception(f"Unexpected error in rate limiter: {e}")
        return True  # Fail open

# Usage
allowed = rate_limit_with_fallback(limiter.allow_request)
if allowed:
    response = handle_request()
else:
    return error_response("Rate limited", 429)
```

---

### Multi-Tier Rate Limiting

**Hierarchical Limits**:
```python
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class RateLimit:
    """Rate limit configuration"""
    limit: int
    window_seconds: int
    name: str

class MultiTierRateLimiter:
    """Multi-tier rate limiter with multiple time windows"""

    def __init__(self, redis_client: redis.Redis, key: str,
                 limits: List[RateLimit]):
        """
        Args:
            redis_client: Redis connection
            key: Base key for rate limiting
            limits: List of rate limits to enforce
        """
        self.redis = redis_client
        self.key = key
        self.limits = limits
        self.limiters = []

        # Create limiter for each tier
        for limit_config in limits:
            limiter = DistributedFixedWindow(
                redis_client,
                f"{key}:{limit_config.name}",
                limit_config.limit,
                limit_config.window_seconds
            )
            self.limiters.append((limit_config, limiter))

    def allow_request(self) -> tuple[bool, Dict]:
        """Check all rate limit tiers

        Returns:
            (allowed, details)
        """
        details = {}

        for limit_config, limiter in self.limiters:
            allowed, remaining, reset_time = limiter.allow_request()

            details[limit_config.name] = {
                'limit': limit_config.limit,
                'remaining': remaining,
                'reset': reset_time,
                'window': limit_config.window_seconds
            }

            if not allowed:
                # First tier that fails
                return False, details

        return True, details

# Usage
limits = [
    RateLimit(limit=10, window_seconds=1, name='per_second'),
    RateLimit(limit=100, window_seconds=60, name='per_minute'),
    RateLimit(limit=1000, window_seconds=3600, name='per_hour'),
    RateLimit(limit=10000, window_seconds=86400, name='per_day'),
]

limiter = MultiTierRateLimiter(redis_client, "user:123", limits)

allowed, details = limiter.allow_request()
if allowed:
    # Add all tier details to headers
    for tier_name, tier_info in details.items():
        response.headers[f'X-RateLimit-{tier_name}-Limit'] = str(tier_info['limit'])
        response.headers[f'X-RateLimit-{tier_name}-Remaining'] = str(tier_info['remaining'])
else:
    # Find most restrictive tier
    return error_response("Rate limit exceeded", 429, details)
```

---

## HTTP Headers and Standards

### RFC 6585: Additional HTTP Status Codes

**429 Too Many Requests** (RFC 6585, Section 4):
```
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 60

{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please retry after 60 seconds."
}
```

**Specification**:
- Status code `429` indicates client has sent too many requests
- SHOULD include `Retry-After` header indicating when to retry
- MAY include details about rate limiting in response body

**Reference**: [RFC 6585](https://tools.ietf.org/html/rfc6585#section-4)

---

### Rate Limit Headers

**De facto standard headers** (based on GitHub, Twitter, Stripe):
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1234567890
```

**Header Definitions**:
- `X-RateLimit-Limit`: Maximum requests allowed in time window
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

**Retry-After Header** (RFC 7231):
```
Retry-After: 60          # Seconds to wait
Retry-After: Wed, 21 Oct 2025 07:28:00 GMT  # Absolute time
```

**Implementation**:
```python
from flask import Flask, jsonify, make_response
import time

app = Flask(__name__)

def add_rate_limit_headers(response, limit: int, remaining: int, reset: int):
    """Add standard rate limit headers"""
    response.headers['X-RateLimit-Limit'] = str(limit)
    response.headers['X-RateLimit-Remaining'] = str(remaining)
    response.headers['X-RateLimit-Reset'] = str(reset)
    return response

def rate_limit_exceeded_response(limit: int, reset: int):
    """Create 429 response with proper headers"""
    retry_after = reset - int(time.time())

    response = make_response(jsonify({
        'error': 'rate_limit_exceeded',
        'message': f'Too many requests. Please retry after {retry_after} seconds.',
        'retry_after': retry_after,
        'limit': limit,
        'reset': reset
    }), 429)

    response.headers['Retry-After'] = str(max(0, retry_after))
    response.headers['X-RateLimit-Limit'] = str(limit)
    response.headers['X-RateLimit-Remaining'] = '0'
    response.headers['X-RateLimit-Reset'] = str(reset)

    return response

@app.route('/api/resource')
def get_resource():
    user_id = get_user_id()
    limiter = DistributedFixedWindow(redis_client, user_id, limit=100, window_seconds=60)

    allowed, remaining, reset = limiter.allow_request()

    if not allowed:
        return rate_limit_exceeded_response(limiter.limit, reset)

    # Process request
    data = {'resource': 'data'}
    response = make_response(jsonify(data), 200)
    return add_rate_limit_headers(response, limiter.limit, remaining, reset)
```

**IETF Draft: RateLimit Headers**:

A more recent standard is being developed:
```
RateLimit-Limit: 100
RateLimit-Remaining: 45
RateLimit-Reset: 60
```

**Reference**: [draft-ietf-httpapi-ratelimit-headers](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-ratelimit-headers)

---

## Storage Backends

### Redis

**Best For**: Distributed systems, high throughput, atomic operations

**Setup**:
```bash
# Install Redis
brew install redis  # macOS
apt-get install redis-server  # Ubuntu

# Start Redis
redis-server

# Connect
redis-cli
```

**Python Client**:
```python
import redis

# Basic connection
client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

# Test connection
client.ping()  # Returns True if connected
```

**Key Patterns**:
```python
# Fixed window
key = f"rate_limit:fixed:{user_id}:{window_id}"
redis.incr(key)
redis.expire(key, window_seconds * 2)

# Sliding window (sorted set)
key = f"rate_limit:sliding:{user_id}"
redis.zadd(key, {request_id: timestamp})
redis.zremrangebyscore(key, 0, window_start)
redis.expire(key, window_seconds)

# Token bucket (hash)
key = f"rate_limit:token:{user_id}"
redis.hmset(key, {'tokens': tokens, 'last_refill': timestamp})
redis.expire(key, 3600)
```

---

### Memcached

**Best For**: Simple counters, low memory overhead

**Setup**:
```bash
# Install
brew install memcached  # macOS
apt-get install memcached  # Ubuntu

# Start
memcached -d -m 64 -p 11211
```

**Python Client**:
```python
import pymemcache.client.base

client = pymemcache.client.base.Client(('localhost', 11211))

def fixed_window_memcached(user_id: str, limit: int, window_seconds: int) -> bool:
    """Fixed window rate limiting with Memcached"""
    now = int(time.time())
    window_id = now // window_seconds
    key = f"rate_limit:{user_id}:{window_id}"

    # Increment counter
    try:
        count = client.incr(key, 1)
    except pymemcache.exceptions.MemcacheError:
        # Key doesn't exist, create it
        client.set(key, 1, expire=window_seconds * 2)
        count = 1

    return count <= limit
```

---

### In-Memory (Local)

**Best For**: Single-instance applications, no external dependencies

**Implementation**:
```python
import time
import threading
from collections import defaultdict
from typing import Dict

class InMemoryRateLimiter:
    """Thread-safe in-memory rate limiter"""

    def __init__(self):
        self.limits: Dict[str, Dict] = defaultdict(dict)
        self._lock = threading.Lock()

    def check_fixed_window(self, key: str, limit: int, window_seconds: int) -> bool:
        """Fixed window rate limiting"""
        now = time.time()
        window_id = int(now // window_seconds)

        with self._lock:
            # Initialize if needed
            if window_id not in self.limits[key]:
                self.limits[key][window_id] = 0

            # Clean old windows
            old_windows = [wid for wid in self.limits[key] if wid < window_id]
            for wid in old_windows:
                del self.limits[key][wid]

            # Check limit
            if self.limits[key][window_id] < limit:
                self.limits[key][window_id] += 1
                return True

            return False

    def check_token_bucket(self, key: str, capacity: int, refill_rate: float) -> bool:
        """Token bucket rate limiting"""
        now = time.time()

        with self._lock:
            # Initialize if needed
            if key not in self.limits:
                self.limits[key] = {
                    'tokens': capacity,
                    'last_refill': now
                }

            # Refill tokens
            elapsed = now - self.limits[key]['last_refill']
            tokens = min(capacity, self.limits[key]['tokens'] + (elapsed * refill_rate))

            # Consume token
            if tokens >= 1:
                self.limits[key] = {
                    'tokens': tokens - 1,
                    'last_refill': now
                }
                return True

            return False

# Usage
limiter = InMemoryRateLimiter()

if limiter.check_fixed_window("user:123", limit=100, window_seconds=60):
    response = handle_request()
else:
    return error_response("Rate limited", 429)
```

---

### Database (PostgreSQL)

**Best For**: Long-term quota tracking, analytics, audit logs

**Schema**:
```sql
CREATE TABLE rate_limit_requests (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_endpoint_timestamp (endpoint, timestamp)
);

-- Partitioning for performance
CREATE TABLE rate_limit_requests_2025_01 PARTITION OF rate_limit_requests
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

**Implementation**:
```python
import psycopg2
from datetime import datetime, timedelta
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    """Database connection context manager"""
    conn = psycopg2.connect(
        host='localhost',
        database='myapp',
        user='postgres',
        password='password'
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def check_rate_limit_db(user_id: int, endpoint: str,
                       limit: int, window_minutes: int) -> bool:
    """Database-based rate limiting"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)

        # Clean old requests (optional, can use TTL job)
        cursor.execute("""
            DELETE FROM rate_limit_requests
            WHERE user_id = %s AND endpoint = %s AND timestamp < %s
        """, (user_id, endpoint, window_start))

        # Count recent requests
        cursor.execute("""
            SELECT COUNT(*) FROM rate_limit_requests
            WHERE user_id = %s AND endpoint = %s AND timestamp >= %s
        """, (user_id, endpoint, window_start))

        count = cursor.fetchone()[0]

        if count < limit:
            # Record new request
            cursor.execute("""
                INSERT INTO rate_limit_requests (user_id, endpoint, timestamp)
                VALUES (%s, %s, %s)
            """, (user_id, endpoint, datetime.utcnow()))

            return True

        return False

# Usage
if check_rate_limit_db(user_id=123, endpoint='/api/posts',
                       limit=100, window_minutes=1):
    response = handle_request()
else:
    return error_response("Rate limited", 429)
```

---

## Implementation Patterns

### Middleware Pattern (Flask)

```python
from flask import Flask, request, g, jsonify, make_response
from functools import wraps
import redis
import time

app = Flask(__name__)
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

class RateLimiter:
    """Flask rate limiter middleware"""

    def __init__(self, redis_client: redis.Redis,
                 default_limit: int = 100,
                 default_window: int = 60):
        self.redis = redis_client
        self.default_limit = default_limit
        self.default_window = default_window

    def get_rate_limit_key(self) -> str:
        """Get rate limit key for current request"""
        # Try authenticated user
        if hasattr(g, 'user') and g.user:
            return f"user:{g.user.id}"

        # Try API key
        api_key = request.headers.get('X-API-Key')
        if api_key:
            return f"api_key:{api_key}"

        # Fall back to IP
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip:
            ip = ip.split(',')[0].strip()
        return f"ip:{ip}"

    def check_rate_limit(self, limit: int, window: int) -> tuple[bool, int, int, int]:
        """Check rate limit

        Returns:
            (allowed, remaining, reset, limit)
        """
        key = self.get_rate_limit_key()
        now = int(time.time())
        window_id = now // window
        redis_key = f"rate_limit:{key}:{window_id}"

        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window * 2)
        results = pipe.execute()

        count = results[0]
        allowed = count <= limit
        remaining = max(0, limit - count)
        reset = (window_id + 1) * window

        return allowed, remaining, reset, limit

# Global rate limiter
rate_limiter = RateLimiter(redis_client)

def rate_limit(limit: int = None, window: int = None):
    """Rate limit decorator

    Usage:
        @app.route('/api/resource')
        @rate_limit(limit=100, window=60)
        def get_resource():
            return {'data': 'value'}
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Use provided or default limits
            req_limit = limit or rate_limiter.default_limit
            req_window = window or rate_limiter.default_window

            # Check rate limit
            allowed, remaining, reset, total = rate_limiter.check_rate_limit(
                req_limit, req_window
            )

            # Store for after_request
            g.rate_limit = {
                'allowed': allowed,
                'remaining': remaining,
                'reset': reset,
                'limit': total
            }

            if not allowed:
                retry_after = reset - int(time.time())
                response = make_response(jsonify({
                    'error': 'rate_limit_exceeded',
                    'message': f'Too many requests. Retry after {retry_after} seconds.',
                    'retry_after': retry_after
                }), 429)

                response.headers['Retry-After'] = str(max(0, retry_after))
                response.headers['X-RateLimit-Limit'] = str(total)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(reset)

                return response

            # Process request
            return f(*args, **kwargs)

        return decorated_function
    return decorator

@app.after_request
def add_rate_limit_headers(response):
    """Add rate limit headers to all responses"""
    if hasattr(g, 'rate_limit'):
        rl = g.rate_limit
        response.headers['X-RateLimit-Limit'] = str(rl['limit'])
        response.headers['X-RateLimit-Remaining'] = str(rl['remaining'])
        response.headers['X-RateLimit-Reset'] = str(rl['reset'])

    return response

# Usage
@app.route('/api/posts')
@rate_limit(limit=100, window=60)
def get_posts():
    return jsonify({'posts': []})

@app.route('/api/expensive')
@rate_limit(limit=5, window=60)
def expensive_operation():
    return jsonify({'result': 'computed'})
```

---

### Middleware Pattern (FastAPI)

```python
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis
import time
from typing import Callable

app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

class RateLimitMiddleware:
    """FastAPI rate limiting middleware"""

    def __init__(self, redis_client: redis.Redis,
                 default_limit: int = 100,
                 default_window: int = 60):
        self.redis = redis_client
        self.default_limit = default_limit
        self.default_window = default_window

    def get_rate_limit_key(self, request: Request) -> str:
        """Get rate limit key for request"""
        # Try API key header
        api_key = request.headers.get('x-api-key')
        if api_key:
            return f"api_key:{api_key}"

        # Fall back to IP
        forwarded = request.headers.get('x-forwarded-for')
        if forwarded:
            ip = forwarded.split(',')[0].strip()
        else:
            ip = request.client.host

        return f"ip:{ip}"

    async def check_rate_limit(self, request: Request,
                               limit: int, window: int) -> dict:
        """Check rate limit for request"""
        key = self.get_rate_limit_key(request)
        now = int(time.time())
        window_id = now // window
        redis_key = f"rate_limit:{key}:{window_id}"

        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window * 2)
        results = pipe.execute()

        count = results[0]
        allowed = count <= limit
        remaining = max(0, limit - count)
        reset = (window_id + 1) * window

        return {
            'allowed': allowed,
            'remaining': remaining,
            'reset': reset,
            'limit': limit
        }

# Global middleware
rate_limiter = RateLimitMiddleware(redis_client)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Callable):
    """Apply rate limiting to all requests"""
    # Skip rate limiting for health checks
    if request.url.path in ['/health', '/metrics']:
        return await call_next(request)

    # Check rate limit
    rl = await rate_limiter.check_rate_limit(
        request,
        rate_limiter.default_limit,
        rate_limiter.default_window
    )

    if not rl['allowed']:
        retry_after = rl['reset'] - int(time.time())
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                'error': 'rate_limit_exceeded',
                'message': f'Too many requests. Retry after {retry_after} seconds.',
                'retry_after': retry_after
            },
            headers={
                'Retry-After': str(max(0, retry_after)),
                'X-RateLimit-Limit': str(rl['limit']),
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(rl['reset'])
            }
        )

    # Process request
    response = await call_next(request)

    # Add rate limit headers
    response.headers['X-RateLimit-Limit'] = str(rl['limit'])
    response.headers['X-RateLimit-Remaining'] = str(rl['remaining'])
    response.headers['X-RateLimit-Reset'] = str(rl['reset'])

    return response

# Usage
@app.get('/api/posts')
async def get_posts():
    return {'posts': []}
```

---

### Decorator Pattern (Node.js/Express)

```javascript
const redis = require('redis');
const express = require('express');

const app = express();
const redisClient = redis.createClient({
    host: 'localhost',
    port: 6379
});

/**
 * Rate limiter middleware factory
 * @param {number} limit - Maximum requests per window
 * @param {number} windowSeconds - Time window in seconds
 * @returns {Function} Express middleware
 */
function rateLimiter(limit, windowSeconds) {
    return async (req, res, next) => {
        const key = getRateLimitKey(req);
        const now = Math.floor(Date.now() / 1000);
        const windowId = Math.floor(now / windowSeconds);
        const redisKey = `rate_limit:${key}:${windowId}`;

        try {
            // Increment counter
            const count = await redisClient.incr(redisKey);

            // Set expiration on first request
            if (count === 1) {
                await redisClient.expire(redisKey, windowSeconds * 2);
            }

            const allowed = count <= limit;
            const remaining = Math.max(0, limit - count);
            const reset = (windowId + 1) * windowSeconds;

            // Add headers
            res.setHeader('X-RateLimit-Limit', limit);
            res.setHeader('X-RateLimit-Remaining', remaining);
            res.setHeader('X-RateLimit-Reset', reset);

            if (!allowed) {
                const retryAfter = reset - now;
                res.setHeader('Retry-After', retryAfter);

                return res.status(429).json({
                    error: 'rate_limit_exceeded',
                    message: `Too many requests. Retry after ${retryAfter} seconds.`,
                    retry_after: retryAfter
                });
            }

            next();

        } catch (error) {
            console.error('Rate limiter error:', error);
            // Fail open (allow request) on errors
            next();
        }
    };
}

/**
 * Get rate limit key from request
 */
function getRateLimitKey(req) {
    // Try API key
    const apiKey = req.headers['x-api-key'];
    if (apiKey) {
        return `api_key:${apiKey}`;
    }

    // Fall back to IP
    const ip = req.headers['x-forwarded-for']?.split(',')[0].trim() || req.ip;
    return `ip:${ip}`;
}

// Usage
app.get('/api/posts', rateLimiter(100, 60), (req, res) => {
    res.json({ posts: [] });
});

app.get('/api/expensive', rateLimiter(5, 60), (req, res) => {
    res.json({ result: 'computed' });
});
```

---

## Limiting Strategies

### Per-User Rate Limiting

**Identify users by authentication**:
```python
def get_user_rate_limit_key(request) -> str:
    """Get rate limit key based on user identity"""

    # 1. Authenticated user (highest priority)
    if hasattr(request, 'user') and request.user.is_authenticated:
        return f"user:{request.user.id}"

    # 2. API key
    api_key = request.headers.get('X-API-Key')
    if api_key:
        # Validate API key
        user_id = validate_api_key(api_key)
        if user_id:
            return f"api_key:{api_key}:{user_id}"

    # 3. OAuth token
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header[7:]
        user_id = validate_oauth_token(token)
        if user_id:
            return f"oauth:{user_id}"

    # 4. Session ID (fallback, less secure)
    session_id = request.cookies.get('session_id')
    if session_id:
        return f"session:{session_id}"

    # 5. IP address (last resort)
    return f"ip:{get_client_ip(request)}"
```

---

### Per-IP Rate Limiting

**Handle proxies and load balancers correctly**:
```python
def get_client_ip(request) -> str:
    """Get real client IP address

    Handles common proxy headers:
    - X-Forwarded-For
    - X-Real-IP
    - CF-Connecting-IP (Cloudflare)
    - True-Client-IP (Akamai)
    """
    # Cloudflare
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip:
        return cf_ip

    # Akamai
    true_client_ip = request.headers.get('True-Client-IP')
    if true_client_ip:
        return true_client_ip

    # Standard proxy header
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Take first IP (client IP, not proxy)
        return forwarded_for.split(',')[0].strip()

    # Another common header
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip

    # Direct connection
    return request.remote_addr

# Usage
ip = get_client_ip(request)
limiter = DistributedFixedWindow(redis_client, f"ip:{ip}", limit=60, window_seconds=60)
```

**IP Range Limiting** (for CIDR blocks):
```python
import ipaddress

def get_ip_range_key(ip: str, prefix_length: int = 24) -> str:
    """Get rate limit key for IP range

    Args:
        ip: IP address
        prefix_length: CIDR prefix length (24 = /24 subnet)

    Returns:
        Rate limit key for IP range
    """
    try:
        ip_obj = ipaddress.ip_address(ip)

        if ip_obj.version == 4:
            # IPv4: Use /24 (256 addresses)
            network = ipaddress.ip_network(f"{ip}/{prefix_length}", strict=False)
        else:
            # IPv6: Use /64
            network = ipaddress.ip_network(f"{ip}/64", strict=False)

        return f"ip_range:{network}"

    except ValueError:
        # Invalid IP, fall back to string key
        return f"ip:{ip}"

# Usage
ip = get_client_ip(request)
range_key = get_ip_range_key(ip)
limiter = DistributedFixedWindow(redis_client, range_key, limit=1000, window_seconds=60)
```

---

### Tiered Rate Limiting

**Different limits by subscription tier**:
```python
from enum import Enum
from dataclasses import dataclass
from typing import List

class UserTier(Enum):
    """User subscription tiers"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

@dataclass
class TierLimits:
    """Rate limits for a tier"""
    requests_per_second: int
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_capacity: int

# Configure limits per tier
TIER_LIMITS = {
    UserTier.FREE: TierLimits(
        requests_per_second=1,
        requests_per_minute=60,
        requests_per_hour=500,
        requests_per_day=1000,
        burst_capacity=5
    ),
    UserTier.BASIC: TierLimits(
        requests_per_second=5,
        requests_per_minute=300,
        requests_per_hour=5000,
        requests_per_day=10000,
        burst_capacity=20
    ),
    UserTier.PREMIUM: TierLimits(
        requests_per_second=20,
        requests_per_minute=1000,
        requests_per_hour=50000,
        requests_per_day=100000,
        burst_capacity=100
    ),
    UserTier.ENTERPRISE: TierLimits(
        requests_per_second=100,
        requests_per_minute=5000,
        requests_per_hour=500000,
        requests_per_day=1000000,
        burst_capacity=500
    ),
}

class TieredRateLimiter:
    """Rate limiter with tiered limits"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def check_limit(self, user_id: str, tier: UserTier) -> tuple[bool, dict]:
        """Check all rate limits for user tier

        Returns:
            (allowed, details)
        """
        limits = TIER_LIMITS[tier]
        details = {}

        # Check each time window
        checks = [
            ('per_second', limits.requests_per_second, 1),
            ('per_minute', limits.requests_per_minute, 60),
            ('per_hour', limits.requests_per_hour, 3600),
            ('per_day', limits.requests_per_day, 86400),
        ]

        for name, limit, window in checks:
            limiter = DistributedFixedWindow(
                self.redis,
                f"{user_id}:{name}",
                limit,
                window
            )

            allowed, remaining, reset = limiter.allow_request()

            details[name] = {
                'limit': limit,
                'remaining': remaining,
                'reset': reset,
                'window': window
            }

            if not allowed:
                return False, details

        return True, details

# Usage
def handle_request(user_id: str, user_tier: UserTier):
    limiter = TieredRateLimiter(redis_client)
    allowed, details = limiter.check_limit(user_id, user_tier)

    if not allowed:
        # Find most restrictive limit
        for tier_name, tier_info in details.items():
            if tier_info['remaining'] == 0:
                retry_after = tier_info['reset'] - int(time.time())
                return error_response(
                    f"Rate limit exceeded for {tier_name}. "
                    f"Retry in {retry_after} seconds.",
                    429,
                    details
                )

    # Process request
    return success_response(details)
```

---

### Per-Endpoint Rate Limiting

**Different limits for different endpoints**:
```python
from typing import Dict, Tuple

# Configure per-endpoint limits
ENDPOINT_LIMITS: Dict[str, Tuple[int, int]] = {
    # Authentication endpoints (strictest)
    '/auth/login': (5, 60),           # 5 requests per minute
    '/auth/signup': (3, 3600),        # 3 requests per hour
    '/auth/password-reset': (3, 3600),

    # Read endpoints (moderate)
    '/api/users': (100, 60),          # 100 requests per minute
    '/api/posts': (200, 60),
    '/api/comments': (200, 60),

    # Write endpoints (stricter)
    '/api/posts': (50, 60),           # 50 requests per minute (POST)
    '/api/comments': (30, 60),        # 30 requests per minute (POST)

    # Expensive operations (very strict)
    '/api/reports/generate': (5, 3600),    # 5 per hour
    '/api/exports/csv': (10, 86400),       # 10 per day
    '/api/search': (20, 60),               # 20 per minute
}

def get_endpoint_limit(endpoint: str, method: str) -> Tuple[int, int]:
    """Get rate limit for endpoint

    Returns:
        (limit, window_seconds)
    """
    # Try exact match with method
    key = f"{endpoint}:{method}"
    if key in ENDPOINT_LIMITS:
        return ENDPOINT_LIMITS[key]

    # Try endpoint without method
    if endpoint in ENDPOINT_LIMITS:
        return ENDPOINT_LIMITS[endpoint]

    # Default limits
    if method in ['GET', 'HEAD', 'OPTIONS']:
        return (1000, 60)  # 1000 reads per minute
    else:
        return (100, 60)   # 100 writes per minute

def check_endpoint_rate_limit(user_id: str, endpoint: str, method: str) -> bool:
    """Check rate limit for specific endpoint"""
    limit, window = get_endpoint_limit(endpoint, method)

    key = f"{user_id}:{endpoint}:{method}"
    limiter = DistributedFixedWindow(redis_client, key, limit, window)

    allowed, remaining, reset = limiter.allow_request()
    return allowed
```

---

## Error Handling and Responses

### Standard 429 Response

**Complete implementation**:
```python
from flask import jsonify, make_response
from typing import Optional, Dict
import time

def create_429_response(
    limit: int,
    reset: int,
    message: Optional[str] = None,
    details: Optional[Dict] = None
) -> tuple:
    """Create standard 429 Too Many Requests response

    Args:
        limit: Rate limit value
        reset: Unix timestamp when limit resets
        message: Custom error message
        details: Additional details (e.g., multi-tier info)

    Returns:
        Flask response tuple
    """
    retry_after = max(0, reset - int(time.time()))

    if message is None:
        message = f"Rate limit exceeded. Please retry after {retry_after} seconds."

    response_data = {
        'error': {
            'code': 'rate_limit_exceeded',
            'message': message,
            'status': 429
        },
        'rate_limit': {
            'limit': limit,
            'remaining': 0,
            'reset': reset,
            'retry_after': retry_after
        }
    }

    # Add additional details if provided
    if details:
        response_data['rate_limit']['details'] = details

    response = make_response(jsonify(response_data), 429)

    # Standard headers
    response.headers['Retry-After'] = str(retry_after)
    response.headers['X-RateLimit-Limit'] = str(limit)
    response.headers['X-RateLimit-Remaining'] = '0'
    response.headers['X-RateLimit-Reset'] = str(reset)

    # CORS headers (if needed)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Expose-Headers'] = 'X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After'

    return response

# Usage
if not limiter.allow_request():
    return create_429_response(
        limit=limiter.limit,
        reset=limiter.get_reset_time(),
        message="You've made too many requests. Please slow down."
    )
```

---

### Error Response Formats

**JSON API Format**:
```json
{
  "errors": [
    {
      "status": "429",
      "code": "rate_limit_exceeded",
      "title": "Rate Limit Exceeded",
      "detail": "You have exceeded the rate limit of 100 requests per minute.",
      "meta": {
        "limit": 100,
        "remaining": 0,
        "reset": 1234567890,
        "retry_after": 45
      }
    }
  ]
}
```

**Problem Details (RFC 7807)**:
```json
{
  "type": "https://example.com/problems/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "You have made too many requests. Please retry after 45 seconds.",
  "instance": "/api/posts",
  "rate_limit": {
    "limit": 100,
    "remaining": 0,
    "reset": 1234567890,
    "retry_after": 45
  }
}
```

---

## Performance and Scalability

### Redis Performance Optimization

**Connection Pooling**:
```python
import redis

# Configure connection pool
pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,        # Maximum connections in pool
    socket_timeout=1.0,        # Socket timeout (seconds)
    socket_connect_timeout=1.0, # Connect timeout
    retry_on_timeout=True,     # Retry on timeout
    decode_responses=True
)

redis_client = redis.Redis(connection_pool=pool)
```

**Pipeline for Batch Operations**:
```python
def check_multiple_rate_limits(keys: List[str], limit: int, window: int) -> List[bool]:
    """Check rate limits for multiple keys efficiently"""
    now = int(time.time())
    window_id = now // window

    pipe = redis_client.pipeline()

    # Batch increment all keys
    for key in keys:
        redis_key = f"rate_limit:{key}:{window_id}"
        pipe.incr(redis_key)
        pipe.expire(redis_key, window * 2)

    results = pipe.execute()

    # Check results (every 2nd result is expire command)
    allowed = []
    for i in range(0, len(results), 2):
        count = results[i]
        allowed.append(count <= limit)

    return allowed
```

---

### Monitoring and Metrics

**Metrics to Track**:
```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Prometheus metrics
rate_limit_requests = Counter(
    'rate_limit_requests_total',
    'Total rate limit checks',
    ['status']  # allowed, denied, error
)

rate_limit_latency = Histogram(
    'rate_limit_latency_seconds',
    'Rate limit check latency',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

rate_limit_remaining = Gauge(
    'rate_limit_remaining',
    'Remaining requests in rate limit',
    ['key']
)

def check_rate_limit_with_metrics(key: str, limit: int, window: int) -> bool:
    """Rate limit check with metrics"""
    start = time.time()

    try:
        limiter = DistributedFixedWindow(redis_client, key, limit, window)
        allowed, remaining, reset = limiter.allow_request()

        # Record metrics
        status = 'allowed' if allowed else 'denied'
        rate_limit_requests.labels(status=status).inc()
        rate_limit_remaining.labels(key=key).set(remaining)

        return allowed

    except Exception as e:
        rate_limit_requests.labels(status='error').inc()
        logger.error(f"Rate limit error: {e}")
        return True  # Fail open

    finally:
        duration = time.time() - start
        rate_limit_latency.observe(duration)
```

---

## Security Considerations

### Distributed Denial of Service (DDoS) Protection

**Layer 7 DDoS Mitigation**:
```python
class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts limits based on load"""

    def __init__(self, redis_client: redis.Redis,
                 normal_limit: int,
                 high_load_limit: int,
                 load_threshold: float = 0.8):
        self.redis = redis_client
        self.normal_limit = normal_limit
        self.high_load_limit = high_load_limit
        self.load_threshold = load_threshold

    def get_system_load(self) -> float:
        """Get current system load (0.0 - 1.0)"""
        # Implement based on your metrics
        # Example: CPU usage, request queue length, etc.
        import psutil
        return psutil.cpu_percent() / 100.0

    def get_current_limit(self) -> int:
        """Get current rate limit based on system load"""
        load = self.get_system_load()

        if load > self.load_threshold:
            # Under high load, reduce limits
            return self.high_load_limit

        return self.normal_limit

    def allow_request(self, key: str) -> bool:
        """Check if request allowed with adaptive limits"""
        current_limit = self.get_current_limit()
        limiter = DistributedFixedWindow(
            self.redis,
            key,
            current_limit,
            window_seconds=60
        )

        allowed, _, _ = limiter.allow_request()
        return allowed
```

---

### Bypass Techniques Prevention

**Prevent key manipulation**:
```python
import hashlib
import hmac

def create_secure_rate_limit_key(user_id: str, secret_key: bytes) -> str:
    """Create tamper-proof rate limit key

    Args:
        user_id: User identifier
        secret_key: Server-side secret key

    Returns:
        HMAC-signed rate limit key
    """
    # Create HMAC signature
    signature = hmac.new(
        secret_key,
        user_id.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()[:16]

    return f"rate_limit:{user_id}:{signature}"

# Usage
SECRET_KEY = b'your-secret-key-here'  # Store securely

def get_rate_limit_key(user_id: str) -> str:
    return create_secure_rate_limit_key(user_id, SECRET_KEY)

limiter = DistributedFixedWindow(
    redis_client,
    get_rate_limit_key(user_id),
    limit=100,
    window_seconds=60
)
```

---

## Testing and Monitoring

### Load Testing Rate Limiters

**Script to test rate limit behavior**:
```python
import asyncio
import aiohttp
import time
from typing import List, Dict

async def send_request(session: aiohttp.ClientSession, url: str,
                       headers: Dict) -> Dict:
    """Send single request and record result"""
    start = time.time()

    try:
        async with session.get(url, headers=headers) as response:
            latency = time.time() - start

            return {
                'status': response.status,
                'latency': latency,
                'headers': dict(response.headers),
                'timestamp': time.time()
            }

    except Exception as e:
        return {
            'status': 0,
            'error': str(e),
            'timestamp': time.time()
        }

async def load_test_rate_limit(url: str, headers: Dict,
                               requests_per_second: int,
                               duration_seconds: int) -> List[Dict]:
    """Load test rate limiting behavior

    Args:
        url: API endpoint to test
        headers: Request headers (auth, etc.)
        requests_per_second: Target RPS
        duration_seconds: Test duration

    Returns:
        List of request results
    """
    results = []
    interval = 1.0 / requests_per_second

    async with aiohttp.ClientSession() as session:
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            request_start = time.time()

            # Send request
            result = await send_request(session, url, headers)
            results.append(result)

            # Wait for next interval
            elapsed = time.time() - request_start
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)

    return results

def analyze_results(results: List[Dict]) -> Dict:
    """Analyze load test results"""
    total = len(results)
    success = sum(1 for r in results if r['status'] == 200)
    rate_limited = sum(1 for r in results if r['status'] == 429)
    errors = sum(1 for r in results if r['status'] not in [200, 429])

    latencies = [r['latency'] for r in results if 'latency' in r]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    # Check rate limit headers
    headers_sample = next(
        (r['headers'] for r in results if 'headers' in r),
        {}
    )

    return {
        'total_requests': total,
        'successful': success,
        'rate_limited': rate_limited,
        'errors': errors,
        'success_rate': success / total if total > 0 else 0,
        'avg_latency': avg_latency,
        'rate_limit_headers': {
            'limit': headers_sample.get('x-ratelimit-limit'),
            'remaining': headers_sample.get('x-ratelimit-remaining'),
            'reset': headers_sample.get('x-ratelimit-reset')
        }
    }

# Usage
async def main():
    url = 'https://api.example.com/resource'
    headers = {'Authorization': 'Bearer your-token'}

    # Send 150 requests at 100 RPS (should hit 100/min limit)
    results = await load_test_rate_limit(
        url,
        headers,
        requests_per_second=100,
        duration_seconds=1.5
    )

    analysis = analyze_results(results)
    print(f"Total requests: {analysis['total_requests']}")
    print(f"Successful: {analysis['successful']}")
    print(f"Rate limited: {analysis['rate_limited']}")
    print(f"Success rate: {analysis['success_rate']:.2%}")

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Common Anti-Patterns

### Anti-Pattern 1: Fixed Window for Critical Endpoints

**Problem**: Fixed window allows boundary bursts (2x limit in 1 second).

**Bad**:
```python
# Allows 200 requests in 1 second at window boundary
limiter = FixedWindow(redis_client, key, limit=100, window_seconds=60)
```

**Good**:
```python
# Use sliding window or token bucket for critical endpoints
limiter = SlidingWindow(redis_client, key, limit=100, window_seconds=60)
# OR
limiter = TokenBucket(capacity=100, refill_rate=100/60)  # 100 per minute
```

---

### Anti-Pattern 2: Ignoring Redis Failures

**Problem**: Rate limiter crashes entire application when Redis fails.

**Bad**:
```python
if limiter.allow_request():
    return handle_request()
else:
    return rate_limit_exceeded()
# Crashes if Redis unavailable
```

**Good**:
```python
try:
    allowed = limiter.allow_request()
except redis.RedisError as e:
    logger.error(f"Rate limiter unavailable: {e}")
    # Fail open (allow request) or fail closed (deny request)
    allowed = True  # Fail open for availability
    # allowed = False  # Fail closed for security

if not allowed:
    return rate_limit_exceeded()

return handle_request()
```

---

### Anti-Pattern 3: Rate Limiting Health Checks

**Problem**: Health checks get rate limited, causing monitoring to fail.

**Bad**:
```python
@app.before_request
def rate_limit():
    # Applies to ALL requests including health checks
    if not check_rate_limit():
        return error_429()
```

**Good**:
```python
EXEMPT_PATHS = ['/health', '/metrics', '/status', '/ready', '/alive']

@app.before_request
def rate_limit():
    if request.path in EXEMPT_PATHS:
        return None  # Skip rate limiting

    if not check_rate_limit():
        return error_429()
```

---

### Anti-Pattern 4: Not Communicating Limits to Users

**Problem**: Users don't know why they're being rate limited or how long to wait.

**Bad**:
```python
return jsonify({'error': 'Too many requests'}), 429
```

**Good**:
```python
retry_after = limiter.get_reset_time() - int(time.time())

response = jsonify({
    'error': 'rate_limit_exceeded',
    'message': f'You have exceeded the rate limit of {limiter.limit} requests per minute.',
    'limit': limiter.limit,
    'retry_after': retry_after,
    'documentation': 'https://api.example.com/docs/rate-limiting'
})

response.headers['X-RateLimit-Limit'] = str(limiter.limit)
response.headers['X-RateLimit-Remaining'] = '0'
response.headers['X-RateLimit-Reset'] = str(limiter.get_reset_time())
response.headers['Retry-After'] = str(retry_after)

return response, 429
```

---

### Anti-Pattern 5: Same Limits for All Endpoints

**Problem**: Expensive operations have same limits as cheap ones.

**Bad**:
```python
# All endpoints limited to 100/minute
@app.before_request
def rate_limit():
    if not limiter.check_limit('user:123', 100, 60):
        return error_429()
```

**Good**:
```python
# Different limits per endpoint type
ENDPOINT_LIMITS = {
    '/api/posts': (100, 60),          # 100/min (read)
    '/api/posts:POST': (50, 60),      # 50/min (write)
    '/api/reports': (5, 3600),        # 5/hour (expensive)
    '/api/search': (20, 60),          # 20/min (database-heavy)
}

@app.before_request
def rate_limit():
    endpoint = request.path
    method = request.method
    key = f"{endpoint}:{method}"

    limit, window = ENDPOINT_LIMITS.get(key, (1000, 60))

    if not limiter.check_limit(f"user:123:{key}", limit, window):
        return error_429()
```

---

## Language-Specific Implementations

### Python (FastAPI + Redis)

Complete production-ready implementation:

```python
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import time
from typing import Optional

app = FastAPI()

# Redis connection
redis_client = redis.from_url(
    "redis://localhost:6379/0",
    encoding="utf-8",
    decode_responses=True
)

class DistributedRateLimiter:
    """Production-ready distributed rate limiter"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

        # Lua script for atomic fixed window
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

    async def check_limit(self, key: str, limit: int, window: int) -> tuple[bool, int, int]:
        """Check rate limit

        Returns:
            (allowed, remaining, reset_time)
        """
        now = int(time.time())

        try:
            result = await self.redis.eval(
                self.fixed_window_script,
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
            # Log error, fail open (allow request)
            print(f"Rate limiter error: {e}")
            return True, limit, now + window

# Global rate limiter
rate_limiter = DistributedRateLimiter(redis_client)

def get_client_id(request: Request) -> str:
    """Get client identifier for rate limiting"""
    # Try API key
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"api_key:{api_key}"

    # Fall back to IP
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host

    return f"ip:{ip}"

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Global rate limiting middleware"""
    # Skip health checks
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)

    # Check rate limit
    client_id = get_client_id(request)
    allowed, remaining, reset = await rate_limiter.check_limit(
        client_id,
        limit=100,
        window=60
    )

    if not allowed:
        retry_after = reset - int(time.time())
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Retry after {retry_after} seconds.",
                "retry_after": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset)
            }
        )

    # Process request
    response = await call_next(request)

    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset)

    return response

@app.get("/api/resource")
async def get_resource():
    return {"data": "value"}
```

---

### Go (Echo + Redis)

```go
package main

import (
    "context"
    "fmt"
    "net/http"
    "strconv"
    "time"

    "github.com/go-redis/redis/v8"
    "github.com/labstack/echo/v4"
)

type RateLimiter struct {
    client *redis.Client
    script *redis.Script
}

func NewRateLimiter(redisURL string) *RateLimiter {
    client := redis.NewClient(&redis.Options{
        Addr: redisURL,
    })

    script := redis.NewScript(`
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
    `)

    return &RateLimiter{
        client: client,
        script: script,
    }
}

func (rl *RateLimiter) CheckLimit(ctx context.Context, key string, limit int, window int) (bool, int, int64, error) {
    now := time.Now().Unix()

    result, err := rl.script.Run(
        ctx,
        rl.client,
        []string{fmt.Sprintf("rate_limit:%s", key)},
        limit,
        window,
        now,
    ).Result()

    if err != nil {
        // Fail open on error
        return true, limit, now + int64(window), err
    }

    values := result.([]interface{})
    allowed := values[0].(int64) == 1
    remaining := int(values[1].(int64))
    reset := values[2].(int64)

    return allowed, remaining, reset, nil
}

func RateLimitMiddleware(limiter *RateLimiter) echo.MiddlewareFunc {
    return func(next echo.HandlerFunc) echo.HandlerFunc {
        return func(c echo.Context) error {
            // Skip health checks
            if c.Path() == "/health" {
                return next(c)
            }

            // Get client ID
            clientID := c.Request().Header.Get("X-API-Key")
            if clientID == "" {
                clientID = c.RealIP()
            }

            // Check rate limit
            allowed, remaining, reset, err := limiter.CheckLimit(
                c.Request().Context(),
                clientID,
                100,  // limit
                60,   // window (seconds)
            )

            // Add headers
            c.Response().Header().Set("X-RateLimit-Limit", "100")
            c.Response().Header().Set("X-RateLimit-Remaining", strconv.Itoa(remaining))
            c.Response().Header().Set("X-RateLimit-Reset", strconv.FormatInt(reset, 10))

            if !allowed {
                retryAfter := reset - time.Now().Unix()
                c.Response().Header().Set("Retry-After", strconv.FormatInt(retryAfter, 10))

                return c.JSON(http.StatusTooManyRequests, map[string]interface{}{
                    "error":       "rate_limit_exceeded",
                    "message":     fmt.Sprintf("Too many requests. Retry after %d seconds.", retryAfter),
                    "retry_after": retryAfter,
                })
            }

            return next(c)
        }
    }
}

func main() {
    e := echo.New()

    limiter := NewRateLimiter("localhost:6379")
    e.Use(RateLimitMiddleware(limiter))

    e.GET("/api/resource", func(c echo.Context) error {
        return c.JSON(http.StatusOK, map[string]string{"data": "value"})
    })

    e.Start(":8080")
}
```

---

### Node.js (Express + Redis)

```javascript
const express = require('express');
const redis = require('redis');
const { promisify } = require('util');

const app = express();

// Redis client
const redisClient = redis.createClient({
    host: 'localhost',
    port: 6379
});

const evalAsync = promisify(redisClient.eval).bind(redisClient);

// Lua script for atomic rate limiting
const FIXED_WINDOW_SCRIPT = `
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
`;

async function checkRateLimit(key, limit, window) {
    const now = Math.floor(Date.now() / 1000);

    try {
        const result = await evalAsync(
            FIXED_WINDOW_SCRIPT,
            1,
            `rate_limit:${key}`,
            limit,
            window,
            now
        );

        return {
            allowed: result[0] === 1,
            remaining: result[1],
            reset: result[2]
        };
    } catch (error) {
        console.error('Rate limiter error:', error);
        // Fail open
        return {
            allowed: true,
            remaining: limit,
            reset: now + window
        };
    }
}

function getClientId(req) {
    // Try API key
    const apiKey = req.headers['x-api-key'];
    if (apiKey) {
        return `api_key:${apiKey}`;
    }

    // Fall back to IP
    const ip = req.headers['x-forwarded-for']?.split(',')[0].trim() || req.ip;
    return `ip:${ip}`;
}

// Rate limit middleware
async function rateLimitMiddleware(req, res, next) {
    // Skip health checks
    if (req.path === '/health') {
        return next();
    }

    const clientId = getClientId(req);
    const { allowed, remaining, reset } = await checkRateLimit(clientId, 100, 60);

    // Add headers
    res.setHeader('X-RateLimit-Limit', '100');
    res.setHeader('X-RateLimit-Remaining', String(remaining));
    res.setHeader('X-RateLimit-Reset', String(reset));

    if (!allowed) {
        const retryAfter = reset - Math.floor(Date.now() / 1000);
        res.setHeader('Retry-After', String(retryAfter));

        return res.status(429).json({
            error: 'rate_limit_exceeded',
            message: `Too many requests. Retry after ${retryAfter} seconds.`,
            retry_after: retryAfter
        });
    }

    next();
}

app.use(rateLimitMiddleware);

app.get('/api/resource', (req, res) => {
    res.json({ data: 'value' });
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
```

---

## References and Standards

### RFCs and Specifications

**RFC 6585: Additional HTTP Status Codes**
- Section 4: 429 Too Many Requests
- https://tools.ietf.org/html/rfc6585#section-4

**RFC 7231: HTTP/1.1 Semantics and Content**
- Section 7.1.3: Retry-After header
- https://tools.ietf.org/html/rfc7231#section-7.1.3

**IETF Draft: RateLimit Header Fields for HTTP**
- Standardized rate limit headers
- https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-ratelimit-headers

---

### Industry Standards

**GitHub Rate Limiting**:
- https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting

**Twitter Rate Limiting**:
- https://developer.twitter.com/en/docs/twitter-api/rate-limits

**Stripe Rate Limiting**:
- https://stripe.com/docs/rate-limits

---

### Academic References

**Token Bucket Algorithm**:
- Original paper: "A Token-Bucket Algorithm for Packet Switching Networks" (1986)
- https://dl.acm.org/doi/10.1145/319838.319858

**Leaky Bucket Algorithm**:
- "The Leaky Bucket Algorithm for Congestion Control" (1987)
- Used in ATM networks, adapted for HTTP rate limiting

---

### Further Reading

**Books**:
- "Designing Data-Intensive Applications" by Martin Kleppmann (Chapter on Rate Limiting)
- "Site Reliability Engineering" by Google (Chapter on Load Shedding)

**Articles**:
- "How to Design a Scalable Rate Limiting Algorithm" (Figma Engineering Blog)
- "Rate Limiting at Scale" (Cloudflare Blog)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: ~3,100
**Maintainer**: API Rate Limiting Skill Team
