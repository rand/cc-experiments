---
name: api-api-rate-limiting
description: Implementing rate limiting for APIs
---



# API Rate Limiting

**Use this skill when:**
- Implementing rate limiting for APIs
- Protecting services from abuse or overload
- Choosing rate limiting algorithms
- Setting up tiered access controls
- Designing fair resource allocation
- Handling rate limit responses

## When to Use Rate Limiting

### Protection Scenarios

Apply rate limiting to prevent:

```
SCENARIO                     → SOLUTION
─────────────────────────────────────────────────
DDoS attacks                → Per-IP rate limits
API abuse                   → Per-user + per-IP limits
Cost control                → Tiered limits by plan
Resource exhaustion         → Global rate limits
Brute force attacks         → Aggressive limits on auth endpoints
Scraping prevention         → Low limits on list endpoints
Fair usage                  → Per-user quotas
```

### Endpoint Classification

Different endpoints need different limits:

```python
# Critical/Auth endpoints - strictest limits
POST /login              # 5 requests/minute per IP
POST /signup             # 3 requests/hour per IP
POST /password-reset     # 3 requests/hour per user

# Read endpoints - moderate limits
GET /users               # 100 requests/minute per user
GET /posts               # 200 requests/minute per user

# Write endpoints - lower limits
POST /posts              # 50 requests/minute per user
PUT /posts/:id           # 30 requests/minute per user

# Expensive operations - very low limits
POST /reports/generate   # 5 requests/hour per user
POST /exports/csv        # 10 requests/day per user

# Public endpoints - IP-based limits
GET /public/feed         # 60 requests/minute per IP
```

## Rate Limiting Algorithms

### Token Bucket

Best for allowing bursts while maintaining average rate.

**How it works:**
1. Bucket holds tokens (up to capacity)
2. Tokens added at fixed rate
3. Each request consumes tokens
4. Request rejected if insufficient tokens

**Implementation:**
```python
import time
import redis

class TokenBucket:
    def __init__(self, redis_client: redis.Redis, key: str,
                 capacity: int, refill_rate: float):
        """
        capacity: Maximum tokens in bucket
        refill_rate: Tokens added per second
        """
        self.redis = redis_client
        self.key = f"rate_limit:token_bucket:{key}"
        self.capacity = capacity
        self.refill_rate = refill_rate

    def allow_request(self, tokens_needed: int = 1) -> bool:
        """Check if request is allowed and consume tokens"""
        now = time.time()

        # Lua script for atomic operation
        script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_needed = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])

        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now

        -- Refill tokens based on time elapsed
        local elapsed = now - last_refill
        tokens = math.min(capacity, tokens + (elapsed * refill_rate))

        -- Check if enough tokens
        if tokens >= tokens_needed then
            tokens = tokens - tokens_needed
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)
            return 1
        else
            return 0
        end
        """

        result = self.redis.eval(
            script,
            1,
            self.key,
            self.capacity,
            self.refill_rate,
            tokens_needed,
            now
        )

        return bool(result)

    def get_remaining(self) -> int:
        """Get remaining tokens"""
        bucket = self.redis.hmget(self.key, 'tokens', 'last_refill')
        if not bucket[0]:
            return self.capacity

        tokens = float(bucket[0])
        last_refill = float(bucket[1])
        now = time.time()

        elapsed = now - last_refill
        tokens = min(self.capacity, tokens + (elapsed * self.refill_rate))

        return int(tokens)

# Usage
limiter = TokenBucket(redis_client, user_id, capacity=100, refill_rate=10)
if limiter.allow_request():
    # Process request
    return response
else:
    # Rate limited
    return 429
```

**Best for:** APIs with bursty traffic patterns, credit-based systems

### Leaky Bucket

Best for smoothing traffic to constant rate.

**How it works:**
1. Requests enter queue (bucket)
2. Processed at fixed rate (leak)
3. New requests rejected if bucket full

**Implementation:**
```python
class LeakyBucket:
    def __init__(self, redis_client: redis.Redis, key: str,
                 capacity: int, leak_rate: float):
        """
        capacity: Maximum queue size
        leak_rate: Requests processed per second
        """
        self.redis = redis_client
        self.key = f"rate_limit:leaky_bucket:{key}"
        self.capacity = capacity
        self.leak_rate = leak_rate

    def allow_request(self) -> bool:
        """Check if request can be queued"""
        now = time.time()

        script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local leak_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])

        local bucket = redis.call('HMGET', key, 'size', 'last_leak')
        local size = tonumber(bucket[1]) or 0
        local last_leak = tonumber(bucket[2]) or now

        -- Leak based on time elapsed
        local elapsed = now - last_leak
        local leaked = elapsed * leak_rate
        size = math.max(0, size - leaked)

        -- Check if space available
        if size < capacity then
            size = size + 1
            redis.call('HMSET', key, 'size', size, 'last_leak', now)
            redis.call('EXPIRE', key, 3600)
            return 1
        else
            return 0
        end
        """

        result = self.redis.eval(
            script,
            1,
            self.key,
            self.capacity,
            self.leak_rate,
            now
        )

        return bool(result)

# Usage
limiter = LeakyBucket(redis_client, user_id, capacity=50, leak_rate=5)
```

**Best for:** Protecting downstream services, guaranteed constant load

### Fixed Window

Best for simple per-period limits.

**How it works:**
1. Time divided into fixed windows
2. Counter increments per request
3. Counter resets at window boundary

**Implementation:**
```python
class FixedWindow:
    def __init__(self, redis_client: redis.Redis, key: str,
                 limit: int, window_seconds: int):
        self.redis = redis_client
        self.key = f"rate_limit:fixed_window:{key}"
        self.limit = limit
        self.window_seconds = window_seconds

    def allow_request(self) -> bool:
        """Check if request is allowed"""
        now = time.time()
        window = int(now // self.window_seconds)
        key = f"{self.key}:{window}"

        # Increment counter
        count = self.redis.incr(key)

        # Set expiration on first request
        if count == 1:
            self.redis.expire(key, self.window_seconds * 2)

        return count <= self.limit

    def get_remaining(self) -> int:
        """Get remaining requests in window"""
        now = time.time()
        window = int(now // self.window_seconds)
        key = f"{self.key}:{window}"

        count = int(self.redis.get(key) or 0)
        return max(0, self.limit - count)

    def get_reset_time(self) -> int:
        """Get timestamp when window resets"""
        now = time.time()
        window = int(now // self.window_seconds)
        return int((window + 1) * self.window_seconds)

# Usage
limiter = FixedWindow(redis_client, user_id, limit=100, window_seconds=60)
```

**Best for:** Simple quotas, easy to understand for users

**Downside:** Burst at window boundaries (200 requests at 11:59 + 12:00)

### Sliding Window

Best for smooth rate limiting without boundary bursts.

**How it works:**
1. Track request timestamps
2. Count requests in rolling time window
3. Remove old requests outside window

**Implementation:**
```python
class SlidingWindow:
    def __init__(self, redis_client: redis.Redis, key: str,
                 limit: int, window_seconds: int):
        self.redis = redis_client
        self.key = f"rate_limit:sliding_window:{key}"
        self.limit = limit
        self.window_seconds = window_seconds

    def allow_request(self) -> bool:
        """Check if request is allowed"""
        now = time.time()
        window_start = now - self.window_seconds

        pipe = self.redis.pipeline()

        # Remove old requests
        pipe.zremrangebyscore(self.key, 0, window_start)

        # Count requests in window
        pipe.zcard(self.key)

        # Add current request (temporarily)
        pipe.zadd(self.key, {str(now): now})

        # Set expiration
        pipe.expire(self.key, self.window_seconds)

        results = pipe.execute()
        count = results[1]

        # Remove current request if over limit
        if count >= self.limit:
            self.redis.zrem(self.key, str(now))
            return False

        return True

    def get_remaining(self) -> int:
        """Get remaining requests in window"""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean and count
        self.redis.zremrangebyscore(self.key, 0, window_start)
        count = self.redis.zcard(self.key)

        return max(0, self.limit - count)

# Usage
limiter = SlidingWindow(redis_client, user_id, limit=100, window_seconds=60)
```

**Best for:** Fair rate limiting, preventing boundary bursts

**Downside:** Higher memory usage (stores timestamps)

## Storage Backends

### Redis (Recommended)

Best for distributed systems:

```python
import redis

# Single instance
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

# Redis Cluster
from redis.cluster import RedisCluster

redis_client = RedisCluster(
    host='redis-cluster',
    port=6379,
    decode_responses=True
)

# With connection pooling
pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50
)
redis_client = redis.Redis(connection_pool=pool)
```

**Pros:** Fast, atomic operations, distributed, persistence
**Cons:** Extra dependency, network latency

### In-Memory

Best for single-instance applications:

```python
import time
from collections import defaultdict
from threading import Lock

class InMemoryRateLimiter:
    def __init__(self):
        self.limits = defaultdict(lambda: {'count': 0, 'reset': 0})
        self.lock = Lock()

    def check_limit(self, key: str, limit: int, window: int) -> bool:
        now = time.time()

        with self.lock:
            if now > self.limits[key]['reset']:
                self.limits[key] = {'count': 0, 'reset': now + window}

            if self.limits[key]['count'] < limit:
                self.limits[key]['count'] += 1
                return True

            return False

# Usage
limiter = InMemoryRateLimiter()
if limiter.check_limit(user_id, limit=100, window=60):
    # Process request
    pass
```

**Pros:** No external dependencies, zero latency
**Cons:** Not distributed, lost on restart, memory growth

### Database

Best for long-term quota tracking:

```python
# PostgreSQL example
import psycopg2
from datetime import datetime, timedelta

def check_rate_limit(user_id: int, limit: int, window_minutes: int) -> bool:
    conn = psycopg2.connect("dbname=myapp")
    cursor = conn.cursor()

    window_start = datetime.utcnow() - timedelta(minutes=window_minutes)

    # Clean old requests
    cursor.execute("""
        DELETE FROM rate_limit_requests
        WHERE user_id = %s AND timestamp < %s
    """, (user_id, window_start))

    # Count recent requests
    cursor.execute("""
        SELECT COUNT(*) FROM rate_limit_requests
        WHERE user_id = %s AND timestamp >= %s
    """, (user_id, window_start))

    count = cursor.fetchone()[0]

    if count < limit:
        cursor.execute("""
            INSERT INTO rate_limit_requests (user_id, timestamp)
            VALUES (%s, %s)
        """, (user_id, datetime.utcnow()))
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False
```

**Pros:** Persistent, queryable, good for analytics
**Cons:** Slower, higher load on DB

## Rate Limit Headers

### Standard Headers

Return rate limit info to clients:

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

def add_rate_limit_headers(response, limiter, key: str):
    """Add rate limit headers to response"""
    response.headers['X-RateLimit-Limit'] = str(limiter.limit)
    response.headers['X-RateLimit-Remaining'] = str(limiter.get_remaining())
    response.headers['X-RateLimit-Reset'] = str(limiter.get_reset_time())

    return response

@app.route('/api/posts')
def get_posts():
    user_id = request.headers.get('X-User-ID')
    limiter = FixedWindow(redis_client, user_id, limit=100, window_seconds=60)

    if not limiter.allow_request():
        response = jsonify({'error': 'Rate limit exceeded'})
        response.status_code = 429
        response.headers['Retry-After'] = str(
            limiter.get_reset_time() - int(time.time())
        )
        return add_rate_limit_headers(response, limiter, user_id)

    # Process request
    data = {'posts': [...]}
    response = jsonify(data)
    return add_rate_limit_headers(response, limiter, user_id)
```

### Header Meanings

```
X-RateLimit-Limit: 100
  → Maximum requests allowed in window

X-RateLimit-Remaining: 45
  → Requests remaining in current window

X-RateLimit-Reset: 1234567890
  → Unix timestamp when limit resets

Retry-After: 30
  → Seconds until client can retry (429 response)
```

## Limiting Strategies

### Per-User Limiting

Identify users by authentication:

```python
def get_rate_limit_key(request) -> str:
    # Authenticated users
    if request.user.is_authenticated:
        return f"user:{request.user.id}"

    # API key users
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return f"api_key:{api_key}"

    # Fallback to IP
    return f"ip:{request.remote_addr}"
```

### Per-IP Limiting

Protect against anonymous abuse:

```python
def get_client_ip(request) -> str:
    """Get real client IP (behind proxy)"""
    # Check proxy headers
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()

    if request.headers.get('X-Real-IP'):
        return request.headers['X-Real-IP']

    return request.remote_addr

# Use IP as key
limiter = FixedWindow(redis_client, get_client_ip(request), limit=60, window_seconds=60)
```

### Tiered Rate Limits

Different limits by user tier:

```python
RATE_LIMITS = {
    'free': {'requests_per_minute': 60, 'requests_per_day': 1000},
    'basic': {'requests_per_minute': 300, 'requests_per_day': 10000},
    'premium': {'requests_per_minute': 1000, 'requests_per_day': 100000},
    'enterprise': {'requests_per_minute': 5000, 'requests_per_day': 1000000},
}

def check_user_rate_limit(user_id: int, tier: str) -> bool:
    limits = RATE_LIMITS[tier]

    # Check per-minute limit
    minute_limiter = FixedWindow(
        redis_client,
        f"user:{user_id}:minute",
        limit=limits['requests_per_minute'],
        window_seconds=60
    )

    # Check per-day limit
    day_limiter = FixedWindow(
        redis_client,
        f"user:{user_id}:day",
        limit=limits['requests_per_day'],
        window_seconds=86400
    )

    return minute_limiter.allow_request() and day_limiter.allow_request()
```

## Graceful Degradation

### Progressive Rate Limiting

Gradually restrict rather than hard stop:

```python
def get_priority_level(request) -> int:
    """Determine request priority (higher = more important)"""
    if request.user.tier == 'enterprise':
        return 3
    elif request.user.tier == 'premium':
        return 2
    elif request.user.tier == 'basic':
        return 1
    else:
        return 0

def adaptive_rate_limit(request) -> bool:
    """Allow high-priority requests during high load"""
    load = get_system_load()  # 0-100
    priority = get_priority_level(request)

    # Increase rate limits under heavy load
    if load > 80:
        # Only allow enterprise
        return priority >= 3
    elif load > 60:
        # Block free tier
        return priority >= 1
    else:
        # Normal operation
        return True
```

### Queue-Based Handling

Queue requests instead of rejecting:

```python
import asyncio
from collections import deque

class RateLimitQueue:
    def __init__(self, rate: int):
        self.rate = rate
        self.queue = deque()
        self.processing = False

    async def add_request(self, request_handler, *args):
        """Add request to queue"""
        future = asyncio.Future()
        self.queue.append((request_handler, args, future))

        if not self.processing:
            asyncio.create_task(self.process_queue())

        return await future

    async def process_queue(self):
        """Process queue at fixed rate"""
        self.processing = True
        interval = 1.0 / self.rate

        while self.queue:
            handler, args, future = self.queue.popleft()

            try:
                result = await handler(*args)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

            await asyncio.sleep(interval)

        self.processing = False

# Usage
queue = RateLimitQueue(rate=10)  # 10 requests/second
result = await queue.add_request(process_request, data)
```

## Algorithm Comparison Matrix

```
ALGORITHM      | BURST | SMOOTH | MEMORY | COMPLEXITY | USE CASE
──────────────────────────────────────────────────────────────────
Token Bucket   | Yes   | No     | Low    | Medium     | Bursty APIs
Leaky Bucket   | No    | Yes    | Low    | Medium     | Constant load
Fixed Window   | Yes   | No     | Low    | Low        | Simple quotas
Sliding Window | No    | Yes    | High   | High       | Fair limiting
```

## Response Patterns

### Standard 429 Response

```python
from flask import jsonify

def rate_limit_exceeded_response(limiter, key: str):
    reset_time = limiter.get_reset_time()
    retry_after = reset_time - int(time.time())

    response = jsonify({
        'error': 'Rate limit exceeded',
        'message': f'Try again in {retry_after} seconds',
        'retry_after': retry_after,
        'limit': limiter.limit,
        'reset': reset_time
    })

    response.status_code = 429
    response.headers['Retry-After'] = str(retry_after)
    response.headers['X-RateLimit-Limit'] = str(limiter.limit)
    response.headers['X-RateLimit-Remaining'] = '0'
    response.headers['X-RateLimit-Reset'] = str(reset_time)

    return response
```

## Anti-Patterns to Avoid

**DON'T use fixed window for critical endpoints:**
```python
# ❌ BAD - Allows 200 requests in 1 second (burst at boundary)
limiter = FixedWindow(redis_client, key, limit=100, window_seconds=60)

# ✅ GOOD - Use sliding window or token bucket
limiter = SlidingWindow(redis_client, key, limit=100, window_seconds=60)
```

**DON'T forget to handle Redis failures:**
```python
# ❌ BAD - Crashes on Redis failure
if limiter.allow_request():
    return response

# ✅ GOOD - Fail open (allow request) on errors
try:
    if not limiter.allow_request():
        return rate_limit_exceeded_response(limiter, key)
except redis.RedisError:
    # Log error but allow request
    logger.error("Rate limiter unavailable")
```

**DON'T rate limit health checks:**
```python
# ✅ GOOD - Exempt monitoring endpoints
EXEMPT_PATHS = ['/health', '/metrics', '/status']

@app.before_request
def check_rate_limit():
    if request.path in EXEMPT_PATHS:
        return None  # Skip rate limiting

    # Apply rate limiting
    ...
```

## Related Skills

- **api-authentication.md** - User identification for per-user limits
- **redis-patterns.md** - Redis optimization for rate limiting
- **api-error-handling.md** - Proper 429 response patterns
- **api-caching.md** - Reduce load to avoid rate limits

---

## Level 3: Resources

### Overview

The **api-rate-limiting** skill includes comprehensive resources for implementing production-grade rate limiting:

- **REFERENCE.md**: 3,100+ line technical reference covering algorithms, implementations, and standards
- **3 Scripts**: Testing, analysis, and benchmarking tools
- **8 Examples**: Production-ready code in Python, Node.js, Go, and configuration examples

### REFERENCE.md

**Location**: `skills/api/api-rate-limiting/resources/REFERENCE.md`

Comprehensive technical reference (3,100+ lines) covering:

**Core Topics**:
- Rate limiting fundamentals and algorithms (token bucket, leaky bucket, fixed/sliding window)
- Distributed rate limiting with Redis and Lua scripts
- HTTP headers and RFC 6585 compliance
- Storage backends (Redis, Memcached, in-memory, PostgreSQL)
- Implementation patterns for Flask, FastAPI, Express, Echo

**Advanced Topics**:
- Multi-tier rate limiting (per-second, per-minute, per-hour, per-day)
- Limiting strategies (per-user, per-IP, per-endpoint, tiered)
- Error handling and graceful degradation
- Performance optimization and scalability
- Security considerations and DDoS protection

**Language Implementations**:
- Python (FastAPI + Redis with async)
- Go (Echo + Redis with golang.org/x/time/rate)
- Node.js (Express + Redis with Lua scripts)

**References**:
- RFC 6585 (429 Too Many Requests)
- RFC 7231 (Retry-After header)
- IETF Draft: RateLimit Headers
- Industry standards (GitHub, Twitter, Stripe)

### Scripts

**1. test_rate_limits.py** - API Rate Limiting Testing Tool

Tests API rate limiting behavior by sending requests and analyzing responses.

```bash
# Test with burst
./test_rate_limits.py --endpoint https://api.example.com/resource

# Sustained load test
./test_rate_limits.py --endpoint https://api.example.com --rps 10 --duration 60

# Test boundary burst vulnerability
./test_rate_limits.py --endpoint https://api.example.com --boundary-test --limit 100 --window 60

# JSON output
./test_rate_limits.py --endpoint https://api.example.com --json
```

Features:
- Send burst or sustained requests
- Measure thresholds and reset times
- Validate rate limit headers (X-RateLimit-*, Retry-After)
- Detect algorithm (token bucket, sliding window, fixed window)
- Check RFC 6585 compliance
- Detect boundary burst vulnerability

**2. analyze_patterns.py** - Traffic Pattern Analysis Tool

Analyzes API access logs to recommend optimal rate limit configurations.

```bash
# Analyze access log
./analyze_patterns.py --log-file /var/log/nginx/access.log

# JSON output
./analyze_patterns.py --log-file access.log --json

# Custom time window
./analyze_patterns.py --log-file access.log --time-window 3600
```

Features:
- Parse common log formats (Nginx, Apache, JSON)
- Identify traffic patterns (burst, steady, abuse, scraping)
- Detect potential abuse (high RPS, error rates)
- Calculate percentiles (P50, P90, P95, P99)
- Recommend rate limits per endpoint
- Top endpoints and clients analysis

**3. benchmark_throughput.py** - Performance Benchmarking Tool

Benchmarks rate limiter implementation performance and compares algorithms.

```bash
# Benchmark single algorithm
./benchmark_throughput.py --algorithm token_bucket

# Compare all algorithms
./benchmark_throughput.py --algorithm all

# Custom load parameters
./benchmark_throughput.py --algorithm sliding_window --concurrent-users 100 --requests 50

# JSON output
./benchmark_throughput.py --algorithm all --json
```

Features:
- Test throughput (requests/second)
- Measure latency (avg, median, P95, P99)
- Compare algorithms (token bucket, sliding window, fixed window)
- Test concurrent users
- Measure Redis overhead
- Generate performance report

### Examples

**Location**: `skills/api/api-rate-limiting/resources/examples/`

**1. python/token_bucket.py** - Token Bucket with Redis

Production-ready token bucket implementation using Redis and Lua scripts.

Features:
- Atomic operations with Lua
- Configurable capacity and refill rate
- Thread-safe distributed implementation
- Graceful error handling (fail open)

```python
limiter = TokenBucket(redis_client, "user:123", capacity=100, refill_rate=10)
if limiter.consume():
    response = handle_request()
else:
    wait = limiter.wait_time()
    return error_response(f"Rate limited. Retry in {wait:.1f}s", 429)
```

**2. python/sliding_window.py** - Sliding Window with Redis

Sliding window implementation using Redis sorted sets for smooth rate limiting.

Features:
- No boundary burst vulnerability
- Accurate request tracking with timestamps
- Atomic operations with Lua
- Memory-efficient with automatic cleanup

```python
limiter = SlidingWindow(redis_client, "user:123", limit=100, window_seconds=60)
allowed, remaining = limiter.allow_request_with_remaining()
if allowed:
    print(f"Request allowed. {remaining} remaining")
```

**3. nodejs/express-rate-limiter.js** - Express Middleware

Complete Express middleware for rate limiting with Redis backend.

Features:
- Fixed window rate limiting
- Configurable per-route limits
- Standard rate limit headers
- Custom key generators
- Graceful error handling (fail open)

```javascript
const rateLimiter = createRateLimiter(redisClient);
app.use('/api', rateLimiter({ limit: 100, window: 60 }));
```

**4. go/rate_limiter.go** - Go Implementation

Go rate limiter using golang.org/x/time/rate with Redis backend.

Features:
- Token bucket algorithm with burst support
- Redis-backed distributed limiting
- Thread-safe operations
- Local in-memory option for single-instance apps

```go
limiter := NewRedisRateLimiter(redisClient, 100, 10)
if limiter.Allow("user:123") {
    // Process request
}
```

**5. python/fastapi-limiter.py** - FastAPI Integration

FastAPI rate limiting with async Redis operations and dependency injection.

Features:
- Async Redis operations
- Dependency injection pattern
- Configurable per-route limits
- Standard rate limit headers
- Middleware for global limits

```python
@app.get("/api/resource")
async def get_resource(
    _: None = Depends(rate_limit(limit=100, window=60))
):
    return {"data": "value"}
```

**6. redis/lua-rate-limiter.lua** - Lua Scripts Collection

Complete collection of Lua scripts for atomic rate limiting in Redis.

Includes:
- Token bucket algorithm
- Sliding window algorithm
- Fixed window algorithm
- Leaky bucket algorithm
- Multi-tier rate limiting
- Distributed lock operations

**7. config/nginx-rate-limit.conf** - Nginx Configuration

Production-ready Nginx configuration using limit_req module.

Features:
- Multiple rate limit zones
- Per-endpoint limits
- Burst handling (burst, nodelay, delay)
- Custom error responses
- IP whitelisting
- Multi-tier limiting

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;

location /api/ {
    limit_req zone=api burst=200 delay=100;
    proxy_pass http://backend;
}
```

**8. python/distributed-limiter.py** - Advanced Distributed Limiter

Complete distributed rate limiter supporting multiple algorithms and strategies.

Features:
- Multiple algorithms (token bucket, sliding window, fixed window)
- Multi-tier limiting (per-second, per-minute, per-hour, per-day)
- Graceful fallback on errors
- Monitoring hooks
- Thread-safe operations

```python
limiter = DistributedRateLimiter(redis_client)

result = limiter.check_limit("user:123", limits={
    "per_second": 10,
    "per_minute": 100,
    "per_hour": 1000
})
```

### Quick Start

1. **Read REFERENCE.md** for comprehensive algorithm explanations and best practices
2. **Choose algorithm**: Token bucket (bursts), Sliding window (smooth), Fixed window (simple)
3. **Pick example**: Start with your language/framework
4. **Test with scripts**: Use test_rate_limits.py to validate behavior
5. **Tune limits**: Use analyze_patterns.py on production logs
6. **Benchmark**: Use benchmark_throughput.py to compare algorithms

### Algorithm Selection Guide

```
NEED BURSTS?
├─ Yes → Token Bucket (python/token_bucket.py)
└─ No  → Need smooth limiting?
         ├─ Yes → Sliding Window (python/sliding_window.py)
         └─ No  → Fixed Window (simplest, nginx-rate-limit.conf)

DISTRIBUTED?
├─ Yes → Use Redis examples (all Python/Node.js/Go examples)
└─ No  → Use in-memory (go/rate_limiter.go LocalRateLimiter)

LANGUAGE?
├─ Python  → fastapi-limiter.py or distributed-limiter.py
├─ Node.js → express-rate-limiter.js
├─ Go      → rate_limiter.go
└─ Nginx   → nginx-rate-limit.conf
```

### Related Resources

- **api-authentication.md** - User identification for per-user limits
- **redis-patterns.md** - Redis optimization and Lua scripting
- **api-error-handling.md** - Proper 429 response handling
