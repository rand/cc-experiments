---
name: database-redis-data-structures
description: Implementing caching layers
---



# Redis Data Structures and Patterns

**Scope**: Redis data types, caching patterns, use cases
**Lines**: ~270
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Implementing caching layers
- Using Redis for sessions, queues, or pub/sub
- Choosing appropriate Redis data structures
- Designing rate limiters or leaderboards
- Planning real-time features
- Optimizing Redis memory usage

## Core Concepts

### What is Redis?

**Redis** (REmote DIctionary Server) is an in-memory data store used as:
- **Cache**: Fast temporary storage
- **Database**: Persistent key-value store
- **Message broker**: Pub/sub, queues
- **Session store**: User sessions

**Key characteristics**:
- In-memory (microsecond latency)
- Single-threaded (atomic operations)
- Persistent (optional: RDB snapshots, AOF logs)
- Supports complex data types

---

## Data Structures

### 1. String (Most Common)

**Use case**: Caching, counters, simple key-value

```bash
# Set/Get
SET user:123:name "Alice"
GET user:123:name  # "Alice"

# With expiration (TTL)
SETEX session:abc123 3600 "user_data"  # Expires in 3600 seconds

# Increment (atomic counter)
INCR page:views  # 1
INCR page:views  # 2

# Decrement
DECR inventory:item:5  # Atomic decrease
```

**Commands**:
- `SET key value` - Store string
- `GET key` - Retrieve string
- `SETEX key seconds value` - Set with TTL
- `INCR key` / `DECR key` - Atomic increment/decrement
- `APPEND key value` - Append to string
- `STRLEN key` - Get string length

**Example: Cache API response**

```python
import redis
import json

r = redis.Redis()

# Cache miss: fetch from API and cache
def get_user(user_id):
    cache_key = f"user:{user_id}"
    cached = r.get(cache_key)

    if cached:
        return json.loads(cached)

    # Fetch from database
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)

    # Cache for 1 hour
    r.setex(cache_key, 3600, json.dumps(user))
    return user
```

### 2. Hash (Object Storage)

**Use case**: Storing objects, user profiles

```bash
# Set multiple fields
HSET user:123 name "Alice" email "alice@example.com" age 30

# Get single field
HGET user:123 name  # "Alice"

# Get all fields
HGETALL user:123  # {name: "Alice", email: "alice@example.com", age: 30}

# Increment field
HINCRBY user:123 age 1  # 31
```

**Commands**:
- `HSET key field value [field value ...]` - Set fields
- `HGET key field` - Get field
- `HGETALL key` - Get all fields
- `HDEL key field` - Delete field
- `HEXISTS key field` - Check if field exists
- `HINCRBY key field increment` - Increment field

**Why use Hash over String?**
- **Hash**: `HGET user:123 name` (get one field)
- **String**: `GET user:123` (must deserialize entire JSON)

**Memory efficient** for objects with many fields.

### 3. List (Ordered Collection)

**Use case**: Queues, activity feeds, recent items

```bash
# Push to left (prepend)
LPUSH queue:tasks "task1"
LPUSH queue:tasks "task2"

# Push to right (append)
RPUSH queue:tasks "task3"

# Pop from left (FIFO queue)
LPOP queue:tasks  # "task2"

# Pop from right (LIFO stack)
RPOP queue:tasks  # "task3"

# Get range
LRANGE queue:tasks 0 9  # First 10 items

# Trim to size (keep only first 100)
LTRIM recent:posts 0 99
```

**Commands**:
- `LPUSH key value` - Prepend
- `RPUSH key value` - Append
- `LPOP key` - Remove first
- `RPOP key` - Remove last
- `LRANGE key start stop` - Get range
- `LLEN key` - Get length
- `LTRIM key start stop` - Keep only range

**Example: Recent activity feed (capped)**

```python
# Add new activity, keep last 100
def add_activity(user_id, activity):
    key = f"feed:{user_id}"
    r.lpush(key, activity)
    r.ltrim(key, 0, 99)  # Keep only 100 most recent

# Get recent 20 activities
def get_feed(user_id):
    key = f"feed:{user_id}"
    return r.lrange(key, 0, 19)
```

### 4. Set (Unordered Unique Collection)

**Use case**: Tags, followers, unique visitors

```bash
# Add members
SADD tags:post:123 "python" "redis" "tutorial"

# Check membership
SISMEMBER tags:post:123 "python"  # 1 (true)

# Get all members
SMEMBERS tags:post:123  # ["python", "redis", "tutorial"]

# Set operations
SINTER tags:post:123 tags:post:456  # Intersection
SUNION tags:post:123 tags:post:456  # Union
SDIFF tags:post:123 tags:post:456   # Difference

# Remove member
SREM tags:post:123 "tutorial"

# Count members
SCARD tags:post:123  # 2
```

**Commands**:
- `SADD key member` - Add member
- `SISMEMBER key member` - Check membership
- `SMEMBERS key` - Get all members
- `SCARD key` - Count members
- `SREM key member` - Remove member
- `SINTER key1 key2` - Intersection
- `SUNION key1 key2` - Union

**Example: Common friends**

```python
# Find mutual friends
user1_friends = r.smembers("friends:user1")
user2_friends = r.smembers("friends:user2")
common = r.sinter("friends:user1", "friends:user2")
```

### 5. Sorted Set (Ordered by Score)

**Use case**: Leaderboards, priority queues, time-series

```bash
# Add members with scores
ZADD leaderboard 100 "alice" 200 "bob" 150 "charlie"

# Get rank (0-based, ascending)
ZRANK leaderboard "alice"  # 0 (lowest score)

# Get reverse rank (descending)
ZREVRANK leaderboard "alice"  # 2 (highest to lowest)

# Get top N (descending)
ZREVRANGE leaderboard 0 9 WITHSCORES  # Top 10 with scores

# Get by score range
ZRANGEBYSCORE leaderboard 100 200  # Scores between 100-200

# Increment score
ZINCRBY leaderboard 50 "alice"  # alice now has 150

# Remove member
ZREM leaderboard "bob"

# Count in range
ZCOUNT leaderboard 100 200
```

**Commands**:
- `ZADD key score member` - Add with score
- `ZRANGE key start stop [WITHSCORES]` - Get range (ascending)
- `ZREVRANGE key start stop [WITHSCORES]` - Get range (descending)
- `ZRANK key member` - Get rank (0-based)
- `ZSCORE key member` - Get score
- `ZINCRBY key increment member` - Increment score
- `ZREM key member` - Remove
- `ZCOUNT key min max` - Count in score range

**Example: Leaderboard**

```python
# Add player score
def add_score(player, score):
    r.zadd("leaderboard", {player: score})

# Get top 10
def get_top_10():
    return r.zrevrange("leaderboard", 0, 9, withscores=True)

# Get player rank
def get_rank(player):
    return r.zrevrank("leaderboard", player) + 1  # 1-based rank
```

---

## Caching Patterns

### Pattern 1: Cache-Aside (Lazy Loading)

**Most common**: Application manages cache.

```python
def get_user(user_id):
    cache_key = f"user:{user_id}"

    # 1. Try cache
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    # 2. Cache miss: fetch from DB
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)

    # 3. Store in cache
    r.setex(cache_key, 3600, json.dumps(user))
    return user
```

**Pros**: Simple, cache only what's needed
**Cons**: Cache miss penalty (extra query)

### Pattern 2: Write-Through

**Write**: Update cache + database together.

```python
def update_user(user_id, data):
    # 1. Update database
    db.execute("UPDATE users SET ... WHERE id = ?", user_id, data)

    # 2. Update cache
    cache_key = f"user:{user_id}"
    r.setex(cache_key, 3600, json.dumps(data))
```

**Pros**: Cache always fresh
**Cons**: Write penalty (two writes)

### Pattern 3: Write-Behind (Write-Back)

**Write**: Update cache immediately, async write to database.

```python
def update_user(user_id, data):
    # 1. Update cache immediately
    cache_key = f"user:{user_id}"
    r.setex(cache_key, 3600, json.dumps(data))

    # 2. Queue database write (background worker)
    queue.enqueue("update_user_db", user_id, data)
```

**Pros**: Fast writes
**Cons**: Risk of data loss if Redis crashes before DB write

### Pattern 4: Refresh-Ahead

**Preload**: Refresh cache before expiration.

```python
def get_user(user_id):
    cache_key = f"user:{user_id}"
    cached = r.get(cache_key)

    if cached:
        ttl = r.ttl(cache_key)
        if ttl < 600:  # Less than 10 min left
            # Refresh in background
            queue.enqueue("refresh_user_cache", user_id)
        return json.loads(cached)

    # ...fetch and cache
```

**Pros**: Avoids cache miss penalty
**Cons**: Complex, may cache unused data

---

## Common Use Cases

### Use Case 1: Session Store

```python
import uuid

def create_session(user_id):
    session_id = str(uuid.uuid4())
    session_key = f"session:{session_id}"

    session_data = {"user_id": user_id, "created_at": time.time()}
    r.setex(session_key, 86400, json.dumps(session_data))  # 24h TTL

    return session_id

def get_session(session_id):
    session_key = f"session:{session_id}"
    data = r.get(session_key)
    return json.loads(data) if data else None
```

### Use Case 2: Rate Limiting (Sliding Window)

```python
def is_rate_limited(user_id, limit=100, window=60):
    key = f"rate_limit:{user_id}"
    now = time.time()

    # Remove old entries outside window
    r.zremrangebyscore(key, 0, now - window)

    # Count requests in window
    count = r.zcard(key)

    if count >= limit:
        return True

    # Add current request
    r.zadd(key, {str(uuid.uuid4()): now})
    r.expire(key, window)
    return False
```

### Use Case 3: Leaderboard

```python
def update_score(player, score):
    r.zadd("leaderboard", {player: score})

def get_top_10():
    return r.zrevrange("leaderboard", 0, 9, withscores=True)

def get_player_rank(player):
    rank = r.zrevrank("leaderboard", player)
    return rank + 1 if rank is not None else None
```

### Use Case 4: Pub/Sub (Real-Time Messaging)

```python
# Publisher
def send_notification(channel, message):
    r.publish(channel, message)

# Subscriber
def listen_notifications(channel):
    pubsub = r.pubsub()
    pubsub.subscribe(channel)

    for message in pubsub.listen():
        if message['type'] == 'message':
            print(f"Received: {message['data']}")
```

### Use Case 5: Distributed Lock

```python
def acquire_lock(resource, timeout=10):
    lock_key = f"lock:{resource}"
    lock_value = str(uuid.uuid4())

    # SET NX (only if not exists) EX (with expiration)
    acquired = r.set(lock_key, lock_value, nx=True, ex=timeout)
    return lock_value if acquired else None

def release_lock(resource, lock_value):
    lock_key = f"lock:{resource}"

    # Only release if we own the lock (Lua script for atomicity)
    lua = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    return r.eval(lua, 1, lock_key, lock_value)
```

---

## TTL Strategies

### Set Expiration

```bash
# Set with expiration
SETEX key 3600 "value"

# Set expiration on existing key
EXPIRE key 3600

# Check TTL
TTL key  # Returns seconds remaining, -1 if no expiration, -2 if key doesn't exist

# Remove expiration
PERSIST key
```

### Choosing TTL Values

| Use Case | TTL | Reasoning |
|----------|-----|-----------|
| API responses | 5-15 min | Balance freshness and cache hits |
| User sessions | 24 hours | Standard session duration |
| Static content | Days/weeks | Rarely changes |
| Real-time data | 10-60 sec | Needs to be fresh |
| Rate limiting | Window size | 60 sec, 1 hour, etc. |

**Trade-offs**:
- **Shorter TTL**: Fresher data, more database queries
- **Longer TTL**: Fewer queries, stale data risk

---

## Memory Optimization

### Eviction Policies

When Redis reaches max memory, it evicts keys based on policy:

| Policy | Behavior |
|--------|----------|
| `noeviction` | Return errors, no eviction |
| `allkeys-lru` | Evict least recently used (any key) |
| `volatile-lru` | Evict LRU (only keys with TTL) |
| `allkeys-random` | Evict random key |
| `volatile-ttl` | Evict key with shortest TTL |

**Recommendation**: `allkeys-lru` for cache, `noeviction` for persistent data.

```bash
# Set in redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### Memory Efficiency Tips

```bash
# Use Hashes for objects (more compact)
HSET user:123 name "Alice" email "alice@example.com"  # Better than JSON string

# Use short key names
# ❌ user:profile:123:details
# ✅ u:123

# Compress large values
# Use gzip/zlib before storing

# Use smaller data types
# INT instead of string for numbers
```

---

## Quick Reference

### Data Structure Selection

```
Need:                           Use:
────────────────────────────────────────
Cache/simple value             String
Object/multiple fields         Hash
Queue/feed/recent items        List
Unique items/set operations    Set
Ordered by score/leaderboard   Sorted Set
```

### Common Commands

```bash
# General
KEYS pattern        # Find keys (avoid in production)
SCAN cursor         # Iterate keys (production-safe)
EXISTS key          # Check existence
DEL key             # Delete key
EXPIRE key seconds  # Set TTL
TTL key             # Check TTL
TYPE key            # Get data type

# Transactions
MULTI               # Start transaction
EXEC                # Execute transaction
DISCARD             # Cancel transaction
```

---

## Common Pitfalls

❌ **Using KEYS in production** - Blocks Redis (O(N))
✅ Use SCAN for iteration

❌ **No expiration on cache keys** - Memory leak
✅ Always set TTL with SETEX or EXPIRE

❌ **Storing large values** - Slow, memory-inefficient
✅ Compress large values, or use hash for objects

❌ **Using Redis as primary database without persistence** - Data loss on crash
✅ Enable RDB/AOF for persistent data

❌ **Not monitoring memory usage** - OOM errors
✅ Set maxmemory and monitor with INFO memory

---

## Level 3: Resources

### Comprehensive Reference

**`resources/REFERENCE.md`** (1,800+ lines)
Comprehensive guide covering:
- All Redis data structures (String, List, Set, Sorted Set, Hash, Stream, Bitmap, HyperLogLog, Geospatial)
- Time complexity for every operation
- Memory optimization techniques and encodings
- Persistence strategies (RDB, AOF, hybrid)
- Replication and clustering architectures
- Pub/Sub patterns and limitations
- Transactions and pipelining
- Lua scripting patterns
- Caching strategies (cache-aside, write-through, write-behind)
- Common patterns (rate limiting, locks, leaderboards, queues)
- Production best practices and troubleshooting

### Executable Scripts

**`resources/scripts/analyze_redis.py`**
Analyze Redis memory usage and key patterns:
```bash
# Analyze all keys
./analyze_redis.py

# Analyze specific pattern
./analyze_redis.py --pattern "user:*"

# Find large keys
./analyze_redis.py --large-keys --threshold 5

# Detailed pattern analysis
./analyze_redis.py --analyze-pattern "session:*"

# JSON output
./analyze_redis.py --json
```

Features:
- Memory usage analysis with pattern detection
- Key pattern extraction (replaces IDs with placeholders)
- Type and encoding distribution
- TTL analysis
- Optimization recommendations
- Large key detection

**`resources/scripts/benchmark_operations.py`**
Benchmark Redis operations:
```bash
# Run all benchmarks
./benchmark_operations.py

# Benchmark specific data structure
./benchmark_operations.py --benchmark strings

# More iterations
./benchmark_operations.py --iterations 10000

# JSON output
./benchmark_operations.py --json
```

Benchmarks:
- String operations (SET, GET, INCR)
- List operations (LPUSH, RPUSH, LPOP, LRANGE)
- Set operations (SADD, SISMEMBER, SINTER)
- Sorted set operations (ZADD, ZSCORE, ZRANGE, ZRANK)
- Hash operations (HSET, HGET, HINCRBY, HGETALL)
- Pipelining vs individual commands
- Different data sizes (64B to 16KB)

Output includes ops/sec, avg/p50/p95/p99 latency.

**`resources/scripts/test_patterns.sh`**
Test common Redis patterns:
```bash
# Test all patterns
./test_patterns.sh

# Test specific pattern
./test_patterns.sh --pattern cache

# JSON output
./test_patterns.sh --json
```

Tests:
- Cache pattern (cache-aside with TTL)
- Queue pattern (FIFO, reliable queue with BRPOPLPUSH)
- Pub/Sub pattern (publish, subscribe, pattern matching)
- Distributed lock pattern (acquire, release with Lua)
- Leaderboard pattern (ZADD, rankings, increments)
- Rate limiting (counter-based, sliding window)

### Runnable Examples

**Python Examples:**

1. **`examples/python/caching_patterns.py`** - Caching strategies:
   - Cache-aside (lazy loading)
   - Write-through (sync cache + DB)
   - Write-behind (async DB writes)
   - Performance comparison
   - Mock database for demonstration

2. **`examples/python/rate_limiter.py`** - Rate limiting algorithms:
   - Sliding window (sorted set based)
   - Token bucket (Lua script based)
   - Fixed window (simple counter)
   - Comparison across algorithms
   - API tier simulation (free vs premium)

3. **`examples/python/session_store.py`** - Session management:
   - Basic session CRUD operations
   - Multiple sessions per user
   - Shopping cart integration
   - Session expiration handling
   - User session statistics

**Node.js Examples:**

1. **`examples/node/leaderboard.js`** - Leaderboard implementation:
   - Basic leaderboard operations
   - Time-based leaderboards (daily, weekly, monthly)
   - Score range queries
   - Players around position
   - Multiple leaderboards (casual, ranked, tournament)

2. **`examples/node/pubsub_example.js`** - Pub/Sub messaging:
   - Basic publish/subscribe
   - Pattern subscriptions
   - Chat room implementation
   - Notification system
   - Multiple subscribers demonstration
   - Cache invalidation via pub/sub

**Docker Examples:**

**`examples/docker/`** - Complete Docker Compose configurations:

Configurations provided:
- **Basic Redis**: Simple instance with persistence
- **Configured Redis**: Password, memory limits, custom config
- **Master-Replica**: Replication setup (1 master + 2 replicas)
- **Redis Sentinel**: High availability (master + replicas + 3 sentinels)
- **Redis Cluster**: Sharded setup (6 nodes with replicas)
- **Management UIs**: Redis Commander and Redis Insight

Quick start:
```bash
# Basic Redis
docker-compose up redis

# Redis with replication
docker-compose up redis-master redis-replica-1 redis-replica-2

# Redis Cluster
docker-compose up redis-cluster-1 redis-cluster-2 redis-cluster-3 \
                  redis-cluster-4 redis-cluster-5 redis-cluster-6

# Create cluster
docker exec -it redis-cluster-1 redis-cli --cluster create \
  redis-cluster-1:7000 redis-cluster-2:7001 redis-cluster-3:7002 \
  redis-cluster-4:7003 redis-cluster-5:7004 redis-cluster-6:7005 \
  --cluster-replicas 1 --cluster-yes

# Web UI
docker-compose up redis redis-commander
# Access at http://localhost:8081
```

Includes:
- Production-ready configurations
- Persistence setup (RDB + AOF)
- Networking configuration
- Volume management
- Health checks
- README with troubleshooting

### Usage

All scripts support:
- `--help` flag for detailed usage
- `--json` flag for machine-readable output
- Connection parameters (`--host`, `--port`, `--password`, `--db`)
- Verbose mode (`--verbose` or `-v`)

All examples are self-contained and runnable with minimal setup.

---

## Related Skills

- `postgres-query-optimization.md` - When to cache database queries
- `database-connection-pooling.md` - Redis connection pooling
- `api-rate-limiting.md` - Implementing rate limits with Redis
- `database-selection.md` - When to use Redis vs other databases

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
