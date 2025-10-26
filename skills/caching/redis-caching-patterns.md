---
name: caching-redis-caching-patterns
description: Application-level caching with Redis - patterns, distributed caching, cache stampede prevention, and integration strategies for high-performance applications.
---
# Redis Caching Patterns

**Last Updated**: 2025-10-25

## When to Use This Skill

Use this skill when:
- Building applications that need fast, distributed in-memory caching
- Implementing session storage, rate limiting, or leaderboards
- Preventing database overload with application-level caching
- Needing cache with data structure support (lists, sets, sorted sets, hashes)
- Scaling beyond single-server caching (Redis Cluster)
- Implementing cache invalidation strategies with pub/sub
- Migrating from Memcached to Redis (2024-2025 standard)

**Prerequisites**: Understanding of `caching-fundamentals.md` (Cache-Aside, Write-Through, Write-Behind patterns)

## Core Concepts

### Redis vs Memcached (2024-2025 Decision Matrix)

| Feature | Redis | Memcached |
|---------|-------|-----------|
| **Data Structures** | Strings, Lists, Sets, Sorted Sets, Hashes, Bitmaps, HyperLogLog, Streams | Key-value only (strings) |
| **Persistence** | RDB snapshots + AOF log (optional) | None (pure in-memory) |
| **Replication** | Built-in primary-replica | None |
| **Clustering** | Redis Cluster (automatic sharding) | Client-side sharding |
| **Use Case** | General-purpose caching, sessions, queues, pub/sub, real-time analytics | Simple key-value caching only |
| **Performance** | ~110K ops/sec (single-threaded) | ~150K ops/sec (multi-threaded) |
| **Industry Standard (2024)** | ✅ Default choice | ⚠️ Legacy systems only |

**2024-2025 Recommendation**: Use Redis unless you have a very specific use case requiring Memcached's slight performance edge for simple key-value operations.

### Redis Connection Patterns

```python
# redis-py (Python standard library for Redis)
import redis
from redis.connection import ConnectionPool

# Single connection (development)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Connection pooling (production)
pool = ConnectionPool(host='localhost', port=6379, db=0,
                      max_connections=50, decode_responses=True)
r = redis.Redis(connection_pool=pool)

# Async support (redis-py 4.2+)
import redis.asyncio as aioredis

async def async_cache():
    r = await aioredis.from_url("redis://localhost:6379", decode_responses=True)
    await r.set("key", "value")
    value = await r.get("key")
    await r.close()
```

## Pattern Implementations

### 1. Cache-Aside (Lazy Loading)

**Most common pattern** - application manages both cache and database.

```python
import redis
import json
from typing import Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class User:
    id: int
    username: str
    email: str

class CacheAsidePattern:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client
        self.ttl = 3600  # 1 hour

    def get_user(self, user_id: int) -> Optional[User]:
        """Cache-Aside read pattern"""
        # 1. Try cache first
        cache_key = f"user:{user_id}"
        cached_data = self.cache.get(cache_key)

        if cached_data:
            print(f"Cache HIT: {cache_key}")
            return User(**json.loads(cached_data))

        # 2. Cache miss - load from database
        print(f"Cache MISS: {cache_key}")
        user = self._load_from_db(user_id)

        if user:
            # 3. Populate cache for next request
            self.cache.setex(cache_key, self.ttl, json.dumps(asdict(user)))

        return user

    def update_user(self, user: User) -> None:
        """Cache-Aside write pattern"""
        # 1. Update database
        self._save_to_db(user)

        # 2. Invalidate cache (let next read repopulate)
        cache_key = f"user:{user.id}"
        self.cache.delete(cache_key)

        # Alternative: Update cache immediately
        # self.cache.setex(cache_key, self.ttl, json.dumps(asdict(user)))

    def _load_from_db(self, user_id: int) -> Optional[User]:
        # Simulate database load
        return User(id=user_id, username=f"user{user_id}", email=f"user{user_id}@example.com")

    def _save_to_db(self, user: User):
        # Simulate database save
        pass
```

### 2. Write-Through Pattern

**Synchronous cache + database writes** - guarantees consistency.

```python
class WriteThroughCache:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client
        self.ttl = 3600

    def save_product(self, product_id: int, product_data: dict) -> None:
        """Write to cache and database simultaneously"""
        cache_key = f"product:{product_id}"

        # 1. Write to cache
        self.cache.setex(cache_key, self.ttl, json.dumps(product_data))

        # 2. Write to database (synchronously)
        self._save_to_db(product_id, product_data)

        print(f"Write-Through: {cache_key} saved to cache + DB")

    def get_product(self, product_id: int) -> Optional[dict]:
        """Read from cache (always up-to-date due to write-through)"""
        cache_key = f"product:{product_id}"
        cached = self.cache.get(cache_key)

        if cached:
            return json.loads(cached)

        # Fallback to database if cache expired
        return self._load_from_db(product_id)

    def _save_to_db(self, product_id: int, data: dict):
        # Database write
        pass

    def _load_from_db(self, product_id: int) -> Optional[dict]:
        # Database read
        return None
```

### 3. Write-Behind (Write-Back) Pattern

**Asynchronous database writes** - fast writes, eventual consistency.

```python
import asyncio
from collections import deque

class WriteBehindCache:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client
        self.write_queue = deque()
        self.batch_size = 100
        self.flush_interval = 5  # seconds

    def save_event(self, event_id: str, event_data: dict) -> None:
        """Write to cache immediately, queue database write"""
        cache_key = f"event:{event_id}"

        # 1. Write to cache immediately
        self.cache.setex(cache_key, 3600, json.dumps(event_data))

        # 2. Queue database write
        self.write_queue.append((event_id, event_data))
        print(f"Write-Behind: {cache_key} cached, queued for DB")

    async def flush_worker(self):
        """Background worker to flush queue to database"""
        while True:
            await asyncio.sleep(self.flush_interval)

            if not self.write_queue:
                continue

            # Batch writes
            batch = []
            while self.write_queue and len(batch) < self.batch_size:
                batch.append(self.write_queue.popleft())

            # Write batch to database
            await self._batch_save_to_db(batch)
            print(f"Flushed {len(batch)} items to database")

    async def _batch_save_to_db(self, batch):
        # Simulate batch database write
        await asyncio.sleep(0.1)
```

## Cache Key Design

### Naming Conventions

```python
class CacheKeyDesign:
    """Best practices for Redis key naming"""

    # Hierarchical keys with colons
    USER_KEY = "user:{user_id}"                    # user:123
    USER_PROFILE = "user:{user_id}:profile"        # user:123:profile
    USER_POSTS = "user:{user_id}:posts"            # user:123:posts

    # Multi-level hierarchies
    PRODUCT_KEY = "product:{category}:{product_id}"  # product:electronics:456

    # Versioned keys
    API_RESPONSE = "api:v1:users:{user_id}"        # api:v1:users:123

    # Namespaced keys
    SESSION_KEY = "session:web:{session_id}"       # session:web:abc123
    RATE_LIMIT = "ratelimit:{ip}:{endpoint}"       # ratelimit:1.2.3.4:/api/data

    @staticmethod
    def build_key(pattern: str, **kwargs) -> str:
        """Safe key building with validation"""
        return pattern.format(**kwargs)

# Usage
key = CacheKeyDesign.build_key(CacheKeyDesign.USER_PROFILE, user_id=123)
# Returns: "user:123:profile"
```

### Key Namespacing Best Practices

```python
# Use environment-specific prefixes
ENV = "prod"  # or "dev", "staging"

def namespaced_key(key: str) -> str:
    return f"{ENV}:{key}"

# prod:user:123 vs dev:user:123
```

## TTL Strategies

### Sliding Expiration

```python
class SlidingExpirationCache:
    def __init__(self, redis_client: redis.Redis, ttl: int = 1800):
        self.cache = redis_client
        self.ttl = ttl  # 30 minutes

    def get_with_sliding_expiration(self, key: str) -> Optional[str]:
        """Reset TTL on every access (sliding window)"""
        value = self.cache.get(key)

        if value:
            # Reset expiration on access
            self.cache.expire(key, self.ttl)
            print(f"Sliding expiration: {key} TTL reset to {self.ttl}s")

        return value

    def set_sliding(self, key: str, value: str) -> None:
        self.cache.setex(key, self.ttl, value)
```

### Probabilistic Early Expiration

Prevents cache stampede by refreshing before expiration.

```python
import random
import time

class ProbabilisticExpiration:
    def __init__(self, redis_client: redis.Redis, ttl: int = 3600):
        self.cache = redis_client
        self.ttl = ttl
        self.beta = 1.0  # Tuning parameter

    def get_with_early_refresh(self, key: str, refresh_fn) -> Any:
        """XFetch algorithm - probabilistic early refresh"""
        cached = self.cache.get(key)
        ttl_remaining = self.cache.ttl(key)

        if cached and ttl_remaining > 0:
            # Calculate refresh probability
            delta = time.time() - random.random()
            if delta * self.beta * math.log(random.random()) >= ttl_remaining:
                # Refresh early
                print(f"Early refresh triggered for {key}")
                return self._refresh_cache(key, refresh_fn)

            return json.loads(cached)

        # Cache miss or expired
        return self._refresh_cache(key, refresh_fn)

    def _refresh_cache(self, key: str, refresh_fn) -> Any:
        value = refresh_fn()
        self.cache.setex(key, self.ttl, json.dumps(value))
        return value
```

## Cache Stampede Prevention

### Locking Pattern

```python
import time
import uuid

class CacheStampedePrevention:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    def get_with_lock(self, key: str, refresh_fn, ttl: int = 3600) -> Any:
        """Prevent stampede with distributed lock"""
        cached = self.cache.get(key)
        if cached:
            return json.loads(cached)

        # Try to acquire lock
        lock_key = f"lock:{key}"
        lock_value = str(uuid.uuid4())
        lock_acquired = self.cache.set(lock_key, lock_value, nx=True, ex=10)  # 10s lock

        if lock_acquired:
            try:
                # This thread refreshes the cache
                print(f"Lock acquired for {key}, refreshing...")
                value = refresh_fn()
                self.cache.setex(key, ttl, json.dumps(value))
                return value
            finally:
                # Release lock
                self._release_lock(lock_key, lock_value)
        else:
            # Another thread is refreshing, wait and retry
            print(f"Lock held by another thread for {key}, waiting...")
            time.sleep(0.1)
            return self.get_with_lock(key, refresh_fn, ttl)

    def _release_lock(self, lock_key: str, lock_value: str):
        """Safely release lock (only if we own it)"""
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self.cache.eval(lua_script, 1, lock_key, lock_value)
```

## Session Storage Patterns

```python
import hashlib
from datetime import datetime, timedelta

class RedisSessionStore:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client
        self.session_ttl = 86400  # 24 hours

    def create_session(self, user_id: int) -> str:
        """Create new session with unique ID"""
        session_id = self._generate_session_id(user_id)
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat()
        }

        session_key = f"session:{session_id}"
        self.cache.setex(session_key, self.session_ttl, json.dumps(session_data))
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session and extend TTL"""
        session_key = f"session:{session_id}"
        session_data = self.cache.get(session_key)

        if session_data:
            # Extend session TTL on access
            self.cache.expire(session_key, self.session_ttl)
            data = json.loads(session_data)
            data["last_accessed"] = datetime.utcnow().isoformat()
            self.cache.setex(session_key, self.session_ttl, json.dumps(data))
            return data

        return None

    def destroy_session(self, session_id: str) -> None:
        """Logout - delete session"""
        session_key = f"session:{session_id}"
        self.cache.delete(session_key)

    def _generate_session_id(self, user_id: int) -> str:
        """Generate secure session ID"""
        data = f"{user_id}:{datetime.utcnow().isoformat()}:{uuid.uuid4()}"
        return hashlib.sha256(data.encode()).hexdigest()
```

## Rate Limiting Patterns

### Fixed Window Rate Limiting

```python
class FixedWindowRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    def is_allowed(self, user_id: int, limit: int = 100, window: int = 60) -> bool:
        """Allow 'limit' requests per 'window' seconds"""
        key = f"ratelimit:{user_id}"

        # Increment counter
        current = self.cache.incr(key)

        if current == 1:
            # First request in window - set expiration
            self.cache.expire(key, window)

        if current > limit:
            print(f"Rate limit exceeded for user {user_id}: {current}/{limit}")
            return False

        print(f"Request allowed for user {user_id}: {current}/{limit}")
        return True
```

### Sliding Window Rate Limiting

```python
import time

class SlidingWindowRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    def is_allowed(self, user_id: int, limit: int = 100, window: int = 60) -> bool:
        """Sliding window using sorted set"""
        key = f"ratelimit:sliding:{user_id}"
        now = time.time()
        window_start = now - window

        # Remove old entries
        self.cache.zremrangebyscore(key, 0, window_start)

        # Count requests in current window
        count = self.cache.zcard(key)

        if count >= limit:
            return False

        # Add current request
        self.cache.zadd(key, {str(uuid.uuid4()): now})
        self.cache.expire(key, window)

        return True
```

## Distributed Caching with Redis Cluster

```python
from rediscluster import RedisCluster

class DistributedCache:
    def __init__(self):
        # Connect to Redis Cluster
        startup_nodes = [
            {"host": "127.0.0.1", "port": "7000"},
            {"host": "127.0.0.1", "port": "7001"},
            {"host": "127.0.0.1", "port": "7002"}
        ]
        self.cache = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=True,
            skip_full_coverage_check=True
        )

    def set_distributed(self, key: str, value: str, ttl: int = 3600):
        """Set key in cluster (automatically sharded)"""
        self.cache.setex(key, ttl, value)

    def get_distributed(self, key: str) -> Optional[str]:
        """Get key from cluster"""
        return self.cache.get(key)

    def get_cluster_info(self) -> dict:
        """Get cluster node information"""
        return self.cache.cluster_info()
```

## Integration with Web Frameworks

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
import redis.asyncio as aioredis

app = FastAPI()

# Dependency injection for Redis
async def get_redis():
    redis = await aioredis.from_url("redis://localhost:6379", decode_responses=True)
    try:
        yield redis
    finally:
        await redis.close()

@app.get("/users/{user_id}")
async def get_user(user_id: int, redis: aioredis.Redis = Depends(get_redis)):
    """Cache-Aside pattern with FastAPI"""
    cache_key = f"user:{user_id}"

    # Try cache
    cached = await redis.get(cache_key)
    if cached:
        return {"source": "cache", "data": json.loads(cached)}

    # Load from database
    user_data = {"id": user_id, "name": f"User {user_id}"}

    # Populate cache
    await redis.setex(cache_key, 3600, json.dumps(user_data))

    return {"source": "database", "data": user_data}
```

### Flask Integration

```python
from flask import Flask
import redis

app = Flask(__name__)

# Initialize Redis connection pool
redis_pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)

def get_redis():
    return redis.Redis(connection_pool=redis_pool)

@app.route('/products/<int:product_id>')
def get_product(product_id):
    r = get_redis()
    cache_key = f"product:{product_id}"

    cached = r.get(cache_key)
    if cached:
        return {"source": "cache", "data": json.loads(cached)}

    product_data = {"id": product_id, "name": f"Product {product_id}"}
    r.setex(cache_key, 3600, json.dumps(product_data))

    return {"source": "database", "data": product_data}
```

## Anti-Patterns

### ❌ Not Using Connection Pooling

```python
# WRONG: Creating new connection for each request
def bad_cache_usage():
    r = redis.Redis(host='localhost', port=6379)  # New connection each time
    return r.get("key")

# CORRECT: Use connection pool
pool = ConnectionPool(host='localhost', port=6379, max_connections=50)
r = redis.Redis(connection_pool=pool)
```

### ❌ Ignoring Cache Stampede

```python
# WRONG: No protection against stampede
def bad_cache_refresh(key):
    cached = cache.get(key)
    if not cached:
        # Many threads will hit database simultaneously
        return expensive_db_query()

# CORRECT: Use locking or probabilistic expiration
```

### ❌ Using Redis as a Database

```python
# WRONG: Treating Redis as durable storage without persistence
def bad_critical_data():
    cache.set("critical_order", order_data)  # No persistence configured!
    # Data lost on Redis restart

# CORRECT: Use Redis with AOF persistence + RDB, or use proper database
```

### ❌ Not Setting TTL

```python
# WRONG: Keys without expiration fill up memory
cache.set("user:123", data)  # No TTL - lives forever

# CORRECT: Always set appropriate TTL
cache.setex("user:123", 3600, data)  # 1 hour TTL
```

## Quick Reference

| Pattern | Use Case | Consistency | Latency |
|---------|----------|-------------|---------|
| Cache-Aside | Read-heavy workloads | Eventual | Low (cache hit) |
| Write-Through | Read-heavy, strong consistency | Strong | Medium (sync writes) |
| Write-Behind | Write-heavy, eventual consistency OK | Eventual | Very Low (async writes) |
| Read-Through | Transparent caching | Eventual | Low |

**Cache Stampede Prevention**:
- Locking: Distributed lock with 10s timeout
- Probabilistic: XFetch algorithm with beta=1.0
- Refresh ahead: Background job refreshes before expiration

**TTL Strategies**:
- Fixed: `setex(key, ttl, value)` - expires after TTL
- Sliding: `expire(key, ttl)` on each access
- No expiration: Only for permanent data (use sparingly)

**Rate Limiting**:
- Fixed window: Simple counter with INCR + EXPIRE
- Sliding window: Sorted set with ZADD + ZREMRANGEBYSCORE

## Related Skills

- `caching-fundamentals.md` - Core caching concepts and patterns
- `cache-invalidation-strategies.md` - Time-based, event-based, version-based invalidation
- `database-connection-pooling.md` - Connection pool sizing for cache + DB
- `api-rate-limiting.md` - API rate limiting strategies

## Summary

Redis caching patterns are essential for high-performance applications in 2024-2025:

**Key Takeaways**:
1. **Redis is the standard** - Use Redis over Memcached for new projects
2. **Cache-Aside is most common** - Simple, flexible, works for 80% of use cases
3. **Always use connection pooling** - Critical for production performance
4. **Prevent cache stampede** - Use locking or probabilistic expiration
5. **Design cache keys carefully** - Hierarchical, namespaced, versioned
6. **Set TTL on everything** - Prevent unbounded memory growth
7. **Use Redis for more than caching** - Sessions, rate limiting, pub/sub, leaderboards

Redis provides the foundation for application-level performance optimization. Combine with HTTP caching and CDN edge caching for a complete caching strategy.
