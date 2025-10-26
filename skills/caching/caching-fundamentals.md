---
name: caching-caching-fundamentals
description: Core caching concepts, patterns, eviction policies, and cache design principles for optimizing application performance
---

# Caching Fundamentals

**Last Updated**: 2025-10-25

## When to Use This Skill

**Activate when**:
- Designing caching strategies for applications
- Optimizing application performance and reducing latency
- Reducing database load and API calls
- Understanding cache behavior and tradeoffs
- Choosing appropriate caching patterns
- Implementing cache eviction policies
- Debugging cache-related issues

**Prerequisites**: Basic understanding of databases, APIs, and application architecture

**Related Skills**: `http-caching.md`, `cdn-edge-caching.md`, `redis-caching-patterns.md`, `cache-invalidation-strategies.md`

---

## Core Concepts

### What is Caching?

**Cache**: Temporary storage layer that stores frequently accessed data for fast retrieval

**Purpose**:
- Reduce latency (faster data access)
- Decrease load on backend systems (databases, APIs)
- Improve scalability (handle more requests)
- Reduce costs (fewer database queries, API calls)

**Cache Hierarchy**:
```
Browser Cache → CDN/Edge Cache → Application Cache → Database Cache
    (ms)            (10-50ms)         (1-10ms)          (μs)
```

### Cache Types

```python
from enum import Enum
from typing import Optional, Dict, Any

class CacheType(Enum):
    """Different cache deployment types"""
    LOCAL = "local"           # In-process memory
    DISTRIBUTED = "distributed"  # Shared across instances
    EDGE = "edge"             # CDN, geographically distributed

class CacheLocation:
    """Cache location characteristics"""

    @staticmethod
    def local_cache():
        """
        Local/In-Process Cache

        Pros: Fastest access, no network overhead
        Cons: Not shared, limited by process memory
        Use: Computation results, configuration
        """
        return {
            "latency": "1-10 μs",
            "shared": False,
            "persistence": False,
            "examples": ["@lru_cache", "dict", "Redis in same host"]
        }

    @staticmethod
    def distributed_cache():
        """
        Distributed Cache

        Pros: Shared across instances, scalable
        Cons: Network latency, complexity
        Use: Session data, API responses
        """
        return {
            "latency": "1-10 ms",
            "shared": True,
            "persistence": "optional",
            "examples": ["Redis Cluster", "Memcached"]
        }

    @staticmethod
    def edge_cache():
        """
        Edge/CDN Cache

        Pros: Global distribution, reduce origin load
        Cons: Invalidation complexity
        Use: Static assets, public content
        """
        return {
            "latency": "10-50 ms",
            "shared": True,
            "persistence": True,
            "examples": ["Cloudflare", "Fastly", "CloudFront"]
        }
```

---

## Caching Patterns

### 1. Cache-Aside (Lazy Loading)

**Concept**: Application checks cache first, loads from source on miss, then populates cache

**Flow**:
```
1. Check cache for data
2. If HIT → return cached data
3. If MISS → query source (DB/API)
4. Store result in cache
5. Return data
```

**Implementation**:
```python
from functools import wraps
from typing import Callable, Any
import time

class CacheAside:
    """Cache-Aside (Lazy Loading) pattern"""

    def __init__(self):
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.ttl = 300  # 5 minutes

    def get(self, key: str) -> Optional[Any]:
        """Get from cache if not expired"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                # Expired
                del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        """Set value in cache with timestamp"""
        self.cache[key] = (value, time.time())

    def decorator(self, key_func: Callable = None):
        """Decorator for cache-aside pattern"""
        def decorator_wrapper(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{args}:{kwargs}"

                # Check cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # Cache miss - call function
                result = func(*args, **kwargs)

                # Store in cache
                self.set(cache_key, result)

                return result
            return wrapper
        return decorator_wrapper

# Usage
cache = CacheAside()

@cache.decorator(key_func=lambda user_id: f"user:{user_id}")
def get_user(user_id: int):
    """Fetch user from database (expensive operation)"""
    print(f"Database query for user {user_id}")
    # Simulate DB query
    time.sleep(0.1)
    return {"id": user_id, "name": f"User {user_id}"}

# First call - cache miss
user1 = get_user(1)  # Prints "Database query..."

# Second call - cache hit
user1_again = get_user(1)  # No print, returns from cache
```

**Pros**:
- Only caches requested data (efficient memory use)
- Application controls caching logic
- Resilient (cache failures don't block requests)

**Cons**:
- Initial request latency (cache miss penalty)
- Potential cache stampede on popular keys
- Stale data during TTL window

### 2. Write-Through

**Concept**: Write to cache and source simultaneously

**Flow**:
```
1. Write data to cache
2. Write data to source (DB/API)
3. Return success only when both complete
```

**Implementation**:
```python
class WriteThroughCache:
    """Write-Through caching pattern"""

    def __init__(self, database):
        self.cache: Dict[str, Any] = {}
        self.db = database

    def get(self, key: str) -> Optional[Any]:
        """Read from cache, fall back to DB"""
        if key in self.cache:
            return self.cache[key]

        # Cache miss - load from DB
        value = self.db.get(key)
        if value is not None:
            self.cache[key] = value
        return value

    def set(self, key: str, value: Any):
        """Write to both cache and DB"""
        # Write to cache first
        self.cache[key] = value

        # Then write to database
        self.db.set(key, value)

        # Both must succeed for consistency

# Usage
class MockDatabase:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

db = MockDatabase()
cache = WriteThroughCache(db)

# Write
cache.set("user:1", {"name": "Alice"})
# Cache and DB both updated

# Read
user = cache.get("user:1")  # From cache
```

**Pros**:
- Data consistency (cache always matches source)
- No cache miss penalty on reads
- Simplifies cache warming

**Cons**:
- Write latency (two operations)
- Wasted cache space (all writes cached, even if never read)
- Write failures affect both layers

### 3. Write-Behind (Write-Back)

**Concept**: Write to cache immediately, asynchronously write to source

**Flow**:
```
1. Write data to cache
2. Return success immediately
3. Asynchronously batch writes to source
```

**Implementation**:
```python
import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Deque

@dataclass
class WriteOperation:
    """Pending write operation"""
    key: str
    value: Any
    timestamp: float

class WriteBehindCache:
    """Write-Behind (Write-Back) caching pattern"""

    def __init__(self, database, batch_size=10, flush_interval=5.0):
        self.cache: Dict[str, Any] = {}
        self.db = database
        self.write_queue: Deque[WriteOperation] = deque()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.running = False

    async def start(self):
        """Start background flushing"""
        self.running = True
        while self.running:
            await asyncio.sleep(self.flush_interval)
            await self.flush()

    async def flush(self):
        """Flush pending writes to database"""
        if not self.write_queue:
            return

        # Batch writes
        batch = []
        while self.write_queue and len(batch) < self.batch_size:
            batch.append(self.write_queue.popleft())

        # Write batch to database
        for op in batch:
            self.db.set(op.key, op.value)

        print(f"Flushed {len(batch)} writes to database")

    def get(self, key: str) -> Optional[Any]:
        """Read from cache"""
        return self.cache.get(key)

    def set(self, key: str, value: Any):
        """Write to cache, queue for DB write"""
        # Immediate write to cache
        self.cache[key] = value

        # Queue for async DB write
        self.write_queue.append(
            WriteOperation(key, value, time.time())
        )
```

**Pros**:
- Fast writes (no wait for DB)
- Batching reduces DB load
- Better write throughput

**Cons**:
- Risk of data loss (if cache crashes before flush)
- Complexity (background jobs, retry logic)
- Eventual consistency

### 4. Read-Through

**Concept**: Cache automatically loads data from source on miss

**Implementation**:
```python
class ReadThroughCache:
    """Read-Through caching pattern"""

    def __init__(self, loader_func: Callable[[str], Any]):
        self.cache: Dict[str, Any] = {}
        self.loader = loader_func  # Function to load from source

    def get(self, key: str) -> Any:
        """
        Get value, automatically loading on miss

        Cache handles loading - application doesn't know about source
        """
        if key in self.cache:
            return self.cache[key]

        # Cache miss - load from source
        value = self.loader(key)

        # Store in cache
        self.cache[key] = value

        return value

# Usage
def load_user_from_db(user_id: str):
    """Loader function"""
    print(f"Loading user {user_id} from database")
    return {"id": user_id, "name": f"User {user_id}"}

cache = ReadThroughCache(loader_func=load_user_from_db)

# Application doesn't handle cache misses
user = cache.get("user:1")  # Automatically loads if not cached
```

---

## Eviction Policies

### LRU (Least Recently Used)

**Concept**: Evict least recently accessed item when cache is full

**Implementation**:
```python
from collections import OrderedDict

class LRUCache:
    """LRU Cache with O(1) get and set"""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """Get value and mark as recently used"""
        if key not in self.cache:
            return None

        # Move to end (most recent)
        self.cache.move_to_end(key)
        return self.cache[key]

    def set(self, key: str, value: Any):
        """Set value, evict LRU if at capacity"""
        if key in self.cache:
            # Update existing
            self.cache.move_to_end(key)
        else:
            # New key
            if len(self.cache) >= self.capacity:
                # Evict least recently used (first item)
                self.cache.popitem(last=False)

        self.cache[key] = value

    def __len__(self):
        return len(self.cache)

# Usage
lru = LRUCache(capacity=3)

lru.set("a", 1)
lru.set("b", 2)
lru.set("c", 3)

lru.get("a")  # Access 'a', now most recent

lru.set("d", 4)  # Evicts 'b' (least recently used)

print("b" in lru.cache)  # False
print("a" in lru.cache)  # True
```

**Use when**: Access patterns favor recent items (temporal locality)

### LFU (Least Frequently Used)

**Concept**: Evict least frequently accessed item

**Implementation**:
```python
from collections import defaultdict
import heapq

class LFUCache:
    """LFU Cache with frequency tracking"""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache: Dict[str, Any] = {}
        self.frequency: Dict[str, int] = defaultdict(int)
        self.access_time: Dict[str, int] = {}
        self.time = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value and increment frequency"""
        if key not in self.cache:
            return None

        self.frequency[key] += 1
        self.time += 1
        self.access_time[key] = self.time

        return self.cache[key]

    def set(self, key: str, value: Any):
        """Set value, evict LFU if at capacity"""
        if self.capacity == 0:
            return

        if key in self.cache:
            self.cache[key] = value
            self.frequency[key] += 1
            self.time += 1
            self.access_time[key] = self.time
            return

        if len(self.cache) >= self.capacity:
            # Find least frequently used
            # Break ties by least recently used
            lfu_key = min(
                self.cache.keys(),
                key=lambda k: (self.frequency[k], self.access_time[k])
            )

            del self.cache[lfu_key]
            del self.frequency[lfu_key]
            del self.access_time[lfu_key]

        self.cache[key] = value
        self.frequency[key] = 1
        self.time += 1
        self.access_time[key] = self.time
```

**Use when**: Some items accessed much more frequently than others

### TTL (Time To Live)

**Concept**: Evict items after fixed time period

```python
import time

class TTLCache:
    """TTL-based cache with automatic expiration"""

    def __init__(self, default_ttl: float = 300):
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value if not expired"""
        if key not in self.cache:
            return None

        value, expiry = self.cache[key]

        if time.time() > expiry:
            # Expired
            del self.cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set value with TTL"""
        if ttl is None:
            ttl = self.default_ttl

        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)

    def cleanup(self):
        """Remove all expired entries"""
        now = time.time()
        expired = [k for k, (_, exp) in self.cache.items() if now > exp]
        for k in expired:
            del self.cache[k]
```

**Use when**: Data has natural expiration (sessions, temporary tokens)

---

## Cache Key Design

### Best Practices

```python
class CacheKeyDesign:
    """Cache key naming best practices"""

    @staticmethod
    def hierarchical_key(namespace: str, entity: str, id: str) -> str:
        """
        Hierarchical naming for organization

        Pattern: namespace:entity:id
        Example: app:user:123, api:product:456
        """
        return f"{namespace}:{entity}:{id}"

    @staticmethod
    def composite_key(*parts) -> str:
        """
        Composite key from multiple values

        Example: user_posts(user_id, page) → "posts:user:123:page:1"
        """
        return ":".join(str(p) for p in parts)

    @staticmethod
    def hash_key(data: str) -> str:
        """
        Hash long or complex keys

        Use for: Query strings, JSON, URLs
        """
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    @staticmethod
    def version_key(key: str, version: int) -> str:
        """
        Versioned keys for invalidation

        Increment version to invalidate all old keys
        """
        return f"{key}:v{version}"

# Examples
keys = CacheKeyDesign()

# User data
user_key = keys.hierarchical_key("app", "user", "123")
# "app:user:123"

# Paginated results
posts_key = keys.composite_key("posts", "user", 123, "page", 1)
# "posts:user:123:page:1"

# Complex query
query = "SELECT * FROM users WHERE age > 25 AND city = 'NYC'"
query_key = f"query:{keys.hash_key(query)}"

# Versioned cache
config_key = keys.version_key("app:config", version=2)
# "app:config:v2"
```

---

## When to Cache vs Not Cache

### Cache These
```python
class GoodCacheCandidates:
    """Data that benefits from caching"""

    EXAMPLES = {
        "Expensive computations": {
            "example": "ML model inference, complex calculations",
            "ttl": "hours to days",
            "pattern": "Cache-Aside"
        },
        "Frequently accessed data": {
            "example": "User profiles, product catalogs",
            "ttl": "minutes to hours",
            "pattern": "Read-Through"
        },
        "Slow external API calls": {
            "example": "Third-party APIs, microservices",
            "ttl": "minutes",
            "pattern": "Cache-Aside"
        },
        "Static or rarely changing": {
            "example": "Configuration, reference data",
            "ttl": "hours to days",
            "pattern": "Write-Through"
        },
        "High read-to-write ratio": {
            "example": "News articles, blog posts",
            "ttl": "minutes to hours",
            "pattern": "Cache-Aside"
        }
    }
```

### Don't Cache These
```python
class PoorCacheCandidates:
    """Data that should NOT be cached"""

    EXAMPLES = [
        "Highly personalized data (unless user-keyed)",
        "Rapidly changing data (stock prices, live scores)",
        "Large objects (>1MB, unless CDN)",
        "Data accessed once (no reuse benefit)",
        "Security-sensitive data (PII, passwords)",
        "Already fast queries (<10ms)",
    ]
```

---

## Common Anti-Patterns

### ❌ No Cache Expiration
```python
# WRONG: Cache lives forever
cache = {}
cache[key] = value  # Never expires

# CORRECT: Set TTL
cache.set(key, value, ttl=300)
```

### ❌ Caching Failures
```python
# WRONG: Cache error responses
result = api_call()
cache.set(key, result)  # What if result is error?

# CORRECT: Only cache successful responses
result = api_call()
if result.success:
    cache.set(key, result)
```

### ❌ Cache Stampede
```python
# WRONG: All requests miss simultaneously
# (e.g., cache expires at exact time)

# CORRECT: Probabilistic early expiration
import random

def get_with_early_expiration(key, ttl):
    value, expiry = cache.get_with_expiry(key)

    # Probabilistically refresh before expiry
    time_left = expiry - time.time()
    if time_left < ttl * random.random():
        # Refresh cache
        value = fetch_fresh_data(key)
        cache.set(key, value, ttl)

    return value
```

---

## Quick Reference

### Cache Pattern Selection
| Pattern | Read Speed | Write Speed | Consistency | Use Case |
|---------|-----------|-------------|-------------|----------|
| Cache-Aside | Medium (miss penalty) | Fast | Eventual | General purpose, read-heavy |
| Write-Through | Fast | Slow | Strong | Consistent reads required |
| Write-Behind | Fast | Very Fast | Eventual | High write throughput |
| Read-Through | Fast | N/A | Eventual | Simplified read logic |

### Eviction Policy Selection
| Policy | Best For | Worst For |
|--------|----------|-----------|
| LRU | Temporal locality | Scanning workloads |
| LFU | Skewed access patterns | Changing patterns |
| TTL | Time-sensitive data | Static data |
| FIFO | Fair eviction | Performance optimization |

---

## Related Skills

**Next Steps**:
- `http-caching.md` → Browser and HTTP cache layer
- `cdn-edge-caching.md` → CDN and edge caching
- `redis-caching-patterns.md` → Distributed caching with Redis
- `cache-invalidation-strategies.md` → Invalidation patterns
- `cache-performance-monitoring.md` → Metrics and monitoring

**Foundations**:
- `database-connection-pooling.md` → Database optimization
- `redis-data-structures.md` → Redis basics

---

## Summary

Caching fundamentals provide the foundation for performance optimization:
- **Cache Types**: Local (fastest), distributed (shared), edge (global)
- **Patterns**: Cache-Aside, Write-Through, Write-Behind, Read-Through
- **Eviction**: LRU (recency), LFU (frequency), TTL (time-based)
- **Key Design**: Hierarchical, composite, hashed, versioned

**Key takeaways**:
1. Choose caching pattern based on consistency and performance needs
2. Set appropriate TTL values to balance freshness and hit rate
3. Design cache keys for organization and invalidation
4. Cache expensive, frequently accessed, slow-changing data
5. Avoid caching errors, personalized data, or one-time requests

**Next**: Move to `http-caching.md` for browser and HTTP caching.
