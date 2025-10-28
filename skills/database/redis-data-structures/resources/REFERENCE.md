# Redis Data Structures - Comprehensive Reference

## Table of Contents

1. [Core Data Structures](#core-data-structures)
2. [String Operations](#string-operations)
3. [List Operations](#list-operations)
4. [Set Operations](#set-operations)
5. [Sorted Set Operations](#sorted-set-operations)
6. [Hash Operations](#hash-operations)
7. [Stream Operations](#stream-operations)
8. [Bitmap Operations](#bitmap-operations)
9. [HyperLogLog Operations](#hyperloglog-operations)
10. [Geospatial Operations](#geospatial-operations)
11. [Time Complexity Reference](#time-complexity-reference)
12. [Memory Optimization](#memory-optimization)
13. [Persistence Strategies](#persistence-strategies)
14. [Replication and Clustering](#replication-and-clustering)
15. [Pub/Sub Patterns](#pubsub-patterns)
16. [Transactions and Pipelining](#transactions-and-pipelining)
17. [Lua Scripting](#lua-scripting)
18. [Caching Strategies](#caching-strategies)
19. [Common Patterns](#common-patterns)
20. [Production Best Practices](#production-best-practices)

---

## Core Data Structures

### Overview

Redis supports multiple data structures, each optimized for specific use cases:

1. **String**: Binary-safe strings (up to 512MB)
2. **List**: Linked lists of strings
3. **Set**: Unordered collections of unique strings
4. **Sorted Set**: Sets ordered by score
5. **Hash**: Maps of field-value pairs
6. **Stream**: Log data structure (append-only)
7. **Bitmap**: Bit arrays
8. **HyperLogLog**: Probabilistic cardinality estimator
9. **Geospatial**: Geographic coordinates

### Data Structure Selection Guide

```
Use Case                          → Recommended Structure
─────────────────────────────────────────────────────────
Cache key-value pairs             → String
User session data                 → Hash
Message queue (FIFO)              → List
Message queue (priority)          → Sorted Set
Unique item tracking              → Set
Set operations (union, intersect) → Set
Leaderboards/rankings             → Sorted Set
Time-series data                  → Sorted Set or Stream
Event log/audit trail             → Stream
Real-time analytics               → Bitmap or HyperLogLog
Rate limiting                     → String (counter) or Sorted Set
Location-based queries            → Geospatial
Task queue                        → List or Stream
Pub/Sub messaging                 → Pub/Sub or Stream
Approximate counting              → HyperLogLog
```

---

## String Operations

### Basic Commands

```redis
# Set and get
SET key value [EX seconds] [PX milliseconds] [NX|XX]
GET key
MSET key1 value1 key2 value2 ...
MGET key1 key2 ...

# Examples
SET user:1000:name "Alice"
SET session:abc123 "data" EX 3600  # Expire in 1 hour
SET lock:resource "locked" NX EX 10  # Set only if not exists
GET user:1000:name
```

### Numeric Operations

```redis
# Increment/decrement
INCR key                    # Increment by 1
INCRBY key increment        # Increment by amount
INCRBYFLOAT key increment   # Increment by float
DECR key                    # Decrement by 1
DECRBY key decrement        # Decrement by amount

# Examples
INCR page:views             # Returns new value
INCRBY user:1000:score 10
INCRBYFLOAT temperature 0.5
```

### String Manipulation

```redis
# Append and length
APPEND key value            # Append to string
STRLEN key                  # Get length
GETRANGE key start end      # Get substring
SETRANGE key offset value   # Overwrite part of string

# Examples
APPEND log:2024 "new entry\n"
STRLEN user:1000:bio
GETRANGE message 0 100      # First 100 chars
```

### Advanced String Operations

```redis
# Bit operations on strings
SETBIT key offset value     # Set bit at offset
GETBIT key offset           # Get bit at offset
BITCOUNT key [start end]    # Count set bits
BITPOS key bit [start end]  # Find first bit set/unset

# Examples
SETBIT online:2024-01-15 1000 1  # User 1000 online
GETBIT online:2024-01-15 1000
BITCOUNT online:2024-01-15
```

### String Use Cases

**1. Simple Cache**
```redis
SET cache:user:1000 '{"name":"Alice","email":"alice@example.com"}' EX 300
GET cache:user:1000
```

**2. Distributed Counter**
```redis
INCR global:page:views
INCRBY api:calls:2024-01-15 1
```

**3. Rate Limiting (Simple)**
```redis
SET rate:user:1000:2024-01-15:14 1 EX 3600 NX
INCR rate:user:1000:2024-01-15:14
GET rate:user:1000:2024-01-15:14
```

**4. Feature Flags**
```redis
SET feature:new_ui:enabled "true"
GET feature:new_ui:enabled
```

**5. Distributed Lock**
```redis
SET lock:resource "uuid-token" NX EX 10
# ... do work ...
DEL lock:resource  # Release (with Lua script for safety)
```

---

## List Operations

### Basic Commands

```redis
# Push/pop operations
LPUSH key value [value ...]  # Push to left (head)
RPUSH key value [value ...]  # Push to right (tail)
LPOP key [count]             # Pop from left
RPOP key [count]             # Pop from right
LLEN key                     # Get list length

# Examples
LPUSH queue:tasks "task1" "task2"
RPUSH queue:tasks "task3"
LPOP queue:tasks
LLEN queue:tasks
```

### Blocking Operations

```redis
# Blocking pop (wait until element available)
BLPOP key [key ...] timeout  # Block until left pop
BRPOP key [key ...] timeout  # Block until right pop
BRPOPLPUSH source dest timeout

# Examples
BRPOP queue:tasks 30         # Wait up to 30 seconds
BLPOP queue:priority queue:normal 0  # Wait indefinitely
```

### List Access and Manipulation

```redis
# Access elements
LINDEX key index             # Get element at index
LRANGE key start stop        # Get range of elements
LSET key index value         # Set element at index

# Manipulation
LTRIM key start stop         # Trim list to range
LINSERT key BEFORE|AFTER pivot value
LREM key count value         # Remove elements

# Examples
LRANGE queue:tasks 0 10      # First 10 tasks
LINDEX queue:tasks 0         # First task
LTRIM queue:recent 0 999     # Keep last 1000 items
LREM notifications 1 "old"   # Remove first occurrence
```

### Advanced List Operations

```redis
# Atomic operations
RPOPLPUSH source destination  # Pop from one, push to another
LMOVE source dest LEFT|RIGHT LEFT|RIGHT
LPOS key element [options]    # Find position of element

# Examples
RPOPLPUSH queue:pending queue:processing
LMOVE queue:tasks queue:archive RIGHT LEFT
```

### List Use Cases

**1. Message Queue (FIFO)**
```redis
# Producer
LPUSH queue:emails '{"to":"user@example.com","subject":"Hello"}'

# Consumer
BRPOP queue:emails 30
```

**2. Activity Feed**
```redis
# Add activity
LPUSH feed:user:1000 '{"action":"liked","post_id":42}'
LTRIM feed:user:1000 0 99  # Keep last 100 items

# Get recent activity
LRANGE feed:user:1000 0 9  # Last 10 items
```

**3. Reliable Queue Pattern**
```redis
# Move task to processing
BRPOPLPUSH queue:pending queue:processing 30

# On success, remove from processing
LREM queue:processing 1 "task-data"

# On failure, move back
RPOPLPUSH queue:processing queue:pending
```

**4. Capped Collection**
```redis
LPUSH logs:errors "error message"
LTRIM logs:errors 0 9999  # Keep last 10,000 errors
```

**5. Timeline**
```redis
LPUSH timeline:global "event-1"
LPUSH timeline:global "event-2"
LRANGE timeline:global 0 49  # Last 50 events
```

---

## Set Operations

### Basic Commands

```redis
# Add and remove
SADD key member [member ...]   # Add members
SREM key member [member ...]   # Remove members
SISMEMBER key member           # Check membership
SMEMBERS key                   # Get all members
SCARD key                      # Get set size

# Examples
SADD tags:post:1 "redis" "database" "nosql"
SREM tags:post:1 "nosql"
SISMEMBER tags:post:1 "redis"
SCARD tags:post:1
```

### Set Operations

```redis
# Mathematical set operations
SINTER key [key ...]           # Intersection
SUNION key [key ...]           # Union
SDIFF key [key ...]            # Difference
SINTERSTORE dest key [key ...]
SUNIONSTORE dest key [key ...]
SDIFFSTORE dest key [key ...]

# Examples
SADD skills:user:1 "python" "redis" "sql"
SADD skills:user:2 "python" "redis" "java"
SINTER skills:user:1 skills:user:2  # Common skills
SUNION skills:user:1 skills:user:2  # All unique skills
```

### Random Operations

```redis
# Random element operations
SRANDMEMBER key [count]        # Get random member(s)
SPOP key [count]               # Pop random member(s)

# Examples
SRANDMEMBER lottery:entries    # Random winner
SPOP deck:cards 5              # Draw 5 cards
```

### Scanning Sets

```redis
# Iterate through large sets
SSCAN key cursor [MATCH pattern] [COUNT count]

# Example
SSCAN users:online 0 MATCH "user:*" COUNT 100
```

### Set Use Cases

**1. Tags System**
```redis
SADD tags:post:100 "redis" "tutorial" "database"
SADD posts:tag:redis 100 101 102
SINTER posts:tag:redis posts:tag:tutorial  # Posts with both tags
```

**2. Unique Visitor Tracking**
```redis
SADD visitors:2024-01-15 "user:1000" "user:1001"
SCARD visitors:2024-01-15  # Count unique visitors
SISMEMBER visitors:2024-01-15 "user:1000"  # Check if visited
```

**3. Friend Relationships**
```redis
SADD friends:user:1000 "user:1001" "user:1002"
SADD friends:user:1001 "user:1000" "user:1003"
SINTER friends:user:1000 friends:user:1001  # Mutual friends
```

**4. Online Users**
```redis
SADD users:online "user:1000"
SREM users:online "user:1000"
SMEMBERS users:online
```

**5. Product Recommendation**
```redis
SADD viewed:user:1000 "product:1" "product:2"
SADD viewed:user:1001 "product:2" "product:3"

# Users who viewed similar products
SINTER viewed:user:1000 viewed:user:1001
```

---

## Sorted Set Operations

### Basic Commands

```redis
# Add and remove
ZADD key score member [score member ...]
ZREM key member [member ...]
ZSCORE key member              # Get member's score
ZINCRBY key increment member   # Increment score
ZCARD key                      # Get set size

# Examples
ZADD leaderboard 1000 "player1" 1500 "player2"
ZINCRBY leaderboard 50 "player1"
ZSCORE leaderboard "player1"
```

### Range Operations

```redis
# By rank (position)
ZRANGE key start stop [WITHSCORES] [REV]
ZREVRANGE key start stop [WITHSCORES]
ZRANK key member               # Get rank (0-based)
ZREVRANK key member            # Get reverse rank

# By score
ZRANGEBYSCORE key min max [WITHSCORES] [LIMIT offset count]
ZREVRANGEBYSCORE key max min [WITHSCORES] [LIMIT offset count]
ZCOUNT key min max             # Count in score range

# Examples
ZRANGE leaderboard 0 9 WITHSCORES  # Top 10
ZREVRANGE leaderboard 0 9          # Top 10 (descending)
ZRANK leaderboard "player1"        # Position
ZRANGEBYSCORE leaderboard 1000 2000  # Score range
```

### Lexicographic Operations

```redis
# Range by member name (when scores are same)
ZRANGEBYLEX key min max [LIMIT offset count]
ZREVRANGEBYLEX key max min [LIMIT offset count]
ZLEXCOUNT key min max

# Examples
ZADD names 0 "alice" 0 "bob" 0 "charlie"
ZRANGEBYLEX names [a [c  # alice, bob
ZRANGEBYLEX names [b +   # bob, charlie
```

### Set Operations on Sorted Sets

```redis
# Union and intersection
ZUNIONSTORE dest numkeys key [key ...] [WEIGHTS weight ...] [AGGREGATE SUM|MIN|MAX]
ZINTERSTORE dest numkeys key [key ...] [WEIGHTS weight ...] [AGGREGATE SUM|MIN|MAX]

# Examples
ZUNIONSTORE total:score 2 math:scores english:scores WEIGHTS 2 1
ZINTERSTORE common:friends 2 friends:user:1 friends:user:2
```

### Removing by Rank or Score

```redis
ZREMRANGEBYRANK key start stop
ZREMRANGEBYSCORE key min max
ZREMRANGEBYLEX key min max

# Examples
ZREMRANGEBYRANK leaderboard 100 -1  # Remove all except top 100
ZREMRANGEBYSCORE old:scores -inf 100  # Remove low scores
```

### Scanning Sorted Sets

```redis
ZSCAN key cursor [MATCH pattern] [COUNT count]

# Example
ZSCAN leaderboard 0 MATCH "player:*" COUNT 100
```

### Sorted Set Use Cases

**1. Leaderboard**
```redis
# Update scores
ZADD leaderboard 1500 "player1" 2000 "player2"
ZINCRBY leaderboard 50 "player1"

# Get rankings
ZREVRANGE leaderboard 0 9 WITHSCORES  # Top 10
ZREVRANK leaderboard "player1"        # Player's rank
ZSCORE leaderboard "player1"          # Player's score

# Get players in score range
ZREVRANGEBYSCORE leaderboard +inf 1000
```

**2. Priority Queue**
```redis
# Add tasks with priority
ZADD tasks:priority 1 "high-priority-task"
ZADD tasks:priority 5 "low-priority-task"

# Get next task
ZPOPMIN tasks:priority  # Lowest score (highest priority)
```

**3. Rate Limiting (Sliding Window)**
```redis
# Add request with timestamp
ZADD rate:user:1000 1705334400 "req1"
ZADD rate:user:1000 1705334401 "req2"

# Remove old requests (older than 60 seconds)
ZREMRANGEBYSCORE rate:user:1000 0 1705334340

# Count requests in window
ZCARD rate:user:1000
```

**4. Time-Series Data**
```redis
# Store metrics with timestamp scores
ZADD metrics:cpu 1705334400 "cpu:50.5"
ZADD metrics:cpu 1705334460 "cpu:55.2"

# Get range by time
ZRANGEBYSCORE metrics:cpu 1705334400 1705334500

# Keep last N entries
ZREMRANGEBYRANK metrics:cpu 0 -1001  # Keep last 1000
```

**5. Autocomplete**
```redis
# Store prefixes with same score
ZADD autocomplete 0 "redis" 0 "react" 0 "python"

# Find matches
ZRANGEBYLEX autocomplete [re [rf  # "redis", "react"
```

**6. Scheduled Tasks**
```redis
# Schedule with Unix timestamp
ZADD scheduled:tasks 1705334400 '{"task":"send_email","id":1}'

# Get due tasks
ZRANGEBYSCORE scheduled:tasks 0 1705334400

# Remove processed tasks
ZREM scheduled:tasks '{"task":"send_email","id":1}'
```

---

## Hash Operations

### Basic Commands

```redis
# Set and get fields
HSET key field value [field value ...]
HGET key field
HMSET key field value [field value ...]  # Deprecated, use HSET
HMGET key field [field ...]
HGETALL key
HDEL key field [field ...]
HEXISTS key field
HLEN key                       # Number of fields

# Examples
HSET user:1000 name "Alice" email "alice@example.com" age 30
HGET user:1000 name
HMGET user:1000 name email
HGETALL user:1000
HEXISTS user:1000 email
```

### Numeric Operations

```redis
HINCRBY key field increment
HINCRBYFLOAT key field increment

# Examples
HINCRBY user:1000 login_count 1
HINCRBYFLOAT user:1000 balance 50.25
```

### Field Operations

```redis
HKEYS key                      # Get all field names
HVALS key                      # Get all values
HSETNX key field value         # Set if field doesn't exist
HSTRLEN key field              # Get value length

# Examples
HKEYS user:1000                # ["name", "email", "age"]
HVALS user:1000                # ["Alice", "alice@example.com", "30"]
HSETNX user:1000 role "admin"
```

### Scanning Hashes

```redis
HSCAN key cursor [MATCH pattern] [COUNT count]

# Example
HSCAN user:1000 0 MATCH "pref:*" COUNT 100
```

### Hash Use Cases

**1. User Profile**
```redis
HSET user:1000 \
  name "Alice" \
  email "alice@example.com" \
  joined "2024-01-15" \
  verified "true"

HGET user:1000 email
HINCRBY user:1000 posts_count 1
HGETALL user:1000
```

**2. Session Store**
```redis
HSET session:abc123 \
  user_id 1000 \
  ip "192.168.1.1" \
  created 1705334400 \
  last_activity 1705334500

EXPIRE session:abc123 3600

HGET session:abc123 user_id
HSET session:abc123 last_activity 1705334600
```

**3. Product Catalog**
```redis
HSET product:42 \
  name "Redis Book" \
  price 29.99 \
  stock 100 \
  category "books"

HINCRBY product:42 stock -1
HGET product:42 price
```

**4. Configuration Storage**
```redis
HSET config:app \
  db_host "localhost" \
  db_port 5432 \
  cache_ttl 300 \
  debug "false"

HGET config:app db_host
HMGET config:app db_host db_port
```

**5. Rate Limiting (Multiple Limits)**
```redis
HSET rate:user:1000:2024-01-15 \
  api_calls 150 \
  uploads 10 \
  downloads 50

HINCRBY rate:user:1000:2024-01-15 api_calls 1
HGETALL rate:user:1000:2024-01-15
```

**6. Real-Time Counters**
```redis
HSET stats:page:100 \
  views 1500 \
  likes 50 \
  shares 10

HINCRBY stats:page:100 views 1
HGETALL stats:page:100
```

---

## Stream Operations

### Basic Commands

```redis
# Add to stream
XADD key [MAXLEN ~ length] * field value [field value ...]
XADD key ID field value [field value ...]

# Read from stream
XREAD [COUNT count] [BLOCK milliseconds] STREAMS key [key ...] ID [ID ...]
XRANGE key start end [COUNT count]
XREVRANGE key end start [COUNT count]
XLEN key

# Examples
XADD events * action "login" user_id 1000
XADD events:logs MAXLEN ~ 10000 * level "info" message "User logged in"
XRANGE events - +               # All entries
XRANGE events - + COUNT 10      # First 10 entries
XREAD STREAMS events 0          # Read from beginning
```

### Consumer Groups

```redis
# Create consumer group
XGROUP CREATE key groupname id [MKSTREAM]

# Read as consumer
XREADGROUP GROUP group consumer [COUNT count] [BLOCK ms] STREAMS key [key ...] ID [ID ...]

# Acknowledge messages
XACK key group ID [ID ...]

# Pending messages
XPENDING key group [start end count] [consumer]

# Claim messages
XCLAIM key group consumer min-idle-time ID [ID ...]

# Examples
XGROUP CREATE events group1 0
XREADGROUP GROUP group1 consumer1 COUNT 10 STREAMS events >
XACK events group1 1705334400000-0
XPENDING events group1
```

### Stream Information

```redis
XINFO STREAM key [FULL]
XINFO GROUPS key
XINFO CONSUMERS key groupname

# Examples
XINFO STREAM events
XINFO GROUPS events
```

### Trimming Streams

```redis
XTRIM key MAXLEN ~ length
XTRIM key MINID ~ id

# Examples
XTRIM events MAXLEN ~ 10000     # Keep ~10,000 entries
XTRIM events MINID ~ 1705334400000-0
```

### Stream Use Cases

**1. Event Log**
```redis
# Add events
XADD events:user:1000 * action "login" ip "192.168.1.1" timestamp 1705334400
XADD events:user:1000 * action "purchase" product_id 42 amount 29.99

# Read event history
XRANGE events:user:1000 - +
XREVRANGE events:user:1000 + - COUNT 10  # Last 10 events
```

**2. Message Queue with Consumer Groups**
```redis
# Create stream and group
XGROUP CREATE tasks group1 0 MKSTREAM

# Producer adds tasks
XADD tasks * task "process_image" image_id 42

# Consumer reads and processes
XREADGROUP GROUP group1 worker1 COUNT 1 BLOCK 5000 STREAMS tasks >
# ... process task ...
XACK tasks group1 1705334400000-0

# Handle failed messages
XPENDING tasks group1 - + 10
XCLAIM tasks group1 worker2 3600000 1705334400000-0
```

**3. Activity Tracking**
```redis
XADD activity:global * \
  user_id 1000 \
  action "comment" \
  post_id 42 \
  timestamp 1705334400

# Keep last 100,000 activities
XADD activity:global MAXLEN ~ 100000 * ...

# Read recent activity
XREVRANGE activity:global + - COUNT 50
```

**4. Real-Time Analytics**
```redis
# Store metrics
XADD metrics:api * \
  endpoint "/api/users" \
  method "GET" \
  duration_ms 45 \
  status 200

# Read metrics for analysis
XRANGE metrics:api 1705334400000 1705338000000  # Last hour
```

**5. Audit Trail**
```redis
XADD audit:changes * \
  table "users" \
  operation "UPDATE" \
  user_id 1000 \
  changed_by "admin" \
  old_value "alice@old.com" \
  new_value "alice@new.com"

# Query audit log
XRANGE audit:changes - +
```

---

## Bitmap Operations

### Basic Commands

```redis
SETBIT key offset value
GETBIT key offset
BITCOUNT key [start end]
BITPOS key bit [start] [end]

# Examples
SETBIT online:2024-01-15 1000 1  # User 1000 online
GETBIT online:2024-01-15 1000
BITCOUNT online:2024-01-15         # Count online users
BITPOS online:2024-01-15 1         # First online user
```

### Bit Operations

```redis
BITOP AND destkey key [key ...]
BITOP OR destkey key [key ...]
BITOP XOR destkey key [key ...]
BITOP NOT destkey key

# Examples
BITOP AND result online:2024-01-15 premium:users
BITOP OR all_active active:today active:yesterday
```

### Bitmap Use Cases

**1. User Online Status**
```redis
# Set user online (user_id = bit offset)
SETBIT online:2024-01-15 1000 1
SETBIT online:2024-01-15 1001 1

# Check if user online
GETBIT online:2024-01-15 1000

# Count online users
BITCOUNT online:2024-01-15

# Set offline
SETBIT online:2024-01-15 1000 0
```

**2. Feature Flags per User**
```redis
# User 1000: bit 0=dark_mode, bit 1=notifications, bit 2=beta
SETBIT features:1000 0 1  # Enable dark mode
SETBIT features:1000 1 0  # Disable notifications
SETBIT features:1000 2 1  # Enable beta features

# Check feature
GETBIT features:1000 0
```

**3. Daily Active Users**
```redis
# Mark user active each day
SETBIT dau:2024-01-15 1000 1
SETBIT dau:2024-01-16 1000 1
SETBIT dau:2024-01-17 1000 1

# Count DAU
BITCOUNT dau:2024-01-15

# Users active on both days
BITOP AND active:both dau:2024-01-15 dau:2024-01-16
BITCOUNT active:both
```

**4. Permissions System**
```redis
# Permissions for role (bit = permission_id)
SETBIT permissions:admin 0 1   # Read
SETBIT permissions:admin 1 1   # Write
SETBIT permissions:admin 2 1   # Delete

SETBIT permissions:user 0 1    # Read only

# Check permission
GETBIT permissions:admin 2
```

**5. AB Testing**
```redis
# Assign users to test groups
SETBIT test:variant_a 1000 1
SETBIT test:variant_a 1001 1
SETBIT test:variant_b 1002 1

# Count users in each variant
BITCOUNT test:variant_a
BITCOUNT test:variant_b
```

---

## HyperLogLog Operations

### Basic Commands

```redis
PFADD key element [element ...]    # Add elements
PFCOUNT key [key ...]               # Get cardinality estimate
PFMERGE destkey sourcekey [sourcekey ...]

# Examples
PFADD visitors:2024-01-15 "user:1000" "user:1001"
PFCOUNT visitors:2024-01-15
PFMERGE visitors:week visitors:2024-01-15 visitors:2024-01-16
```

### HyperLogLog Use Cases

**1. Unique Visitor Counting**
```redis
# Track unique visitors (memory efficient)
PFADD visitors:2024-01-15 "user:1000"
PFADD visitors:2024-01-15 "user:1001"
PFADD visitors:2024-01-15 "user:1000"  # Duplicate

# Get unique count (0.81% error rate)
PFCOUNT visitors:2024-01-15  # Returns 2

# Weekly unique visitors
PFMERGE visitors:week \
  visitors:2024-01-15 \
  visitors:2024-01-16 \
  visitors:2024-01-17
PFCOUNT visitors:week
```

**2. Unique Page Views**
```redis
PFADD views:page:100 "user:1000" "user:1001"
PFCOUNT views:page:100

# Total unique viewers across pages
PFMERGE views:total views:page:100 views:page:101
PFCOUNT views:total
```

**3. Search Query Tracking**
```redis
PFADD queries:2024-01 "redis tutorial"
PFADD queries:2024-01 "python redis"
PFADD queries:2024-01 "redis tutorial"  # Duplicate

PFCOUNT queries:2024-01  # Unique queries
```

**4. IP Address Tracking**
```redis
PFADD ips:2024-01-15 "192.168.1.1"
PFADD ips:2024-01-15 "192.168.1.2"
PFCOUNT ips:2024-01-15  # Unique IPs
```

**5. Product View Tracking**
```redis
PFADD product:42:viewers "user:1000"
PFADD product:42:viewers "user:1001"
PFCOUNT product:42:viewers  # Unique viewers
```

---

## Geospatial Operations

### Basic Commands

```redis
# Add locations
GEOADD key longitude latitude member [longitude latitude member ...]

# Get distance
GEODIST key member1 member2 [m|km|ft|mi]

# Get position
GEOPOS key member [member ...]

# Get geohash
GEOHASH key member [member ...]

# Examples
GEOADD locations -122.4194 37.7749 "San Francisco"
GEOADD locations -118.2437 34.0522 "Los Angeles"
GEODIST locations "San Francisco" "Los Angeles" km
GEOPOS locations "San Francisco"
```

### Radius Searches

```redis
# Search by radius from coordinates
GEORADIUS key longitude latitude radius m|km|ft|mi [WITHCOORD] [WITHDIST] [WITHHASH] [COUNT count] [ASC|DESC]

# Search by radius from member
GEORADIUSBYMEMBER key member radius m|km|ft|mi [options]

# Modern alternatives (Redis 6.2+)
GEOSEARCH key FROMMEMBER member | FROMLONLAT longitude latitude BYRADIUS radius | BYBOX width height m|km|ft|mi [options]
GEOSEARCHSTORE dest source [options]

# Examples
GEORADIUS locations -122.4 37.7 100 km WITHDIST COUNT 5
GEORADIUSBYMEMBER locations "San Francisco" 200 km WITHCOORD

# Modern syntax
GEOSEARCH locations FROMLONLAT -122.4 37.7 BYRADIUS 100 km
GEOSEARCH locations FROMMEMBER "San Francisco" BYBOX 200 200 km
```

### Geospatial Use Cases

**1. Store Locator**
```redis
# Add store locations
GEOADD stores -122.4194 37.7749 "store:1"
GEOADD stores -122.4083 37.7833 "store:2"
GEOADD stores -118.2437 34.0522 "store:3"

# Find nearby stores
GEORADIUS stores -122.4 37.8 10 km WITHDIST ASC COUNT 5

# Find stores near a specific store
GEORADIUSBYMEMBER stores "store:1" 5 km WITHDIST
```

**2. Ride-Sharing**
```redis
# Add available drivers
GEOADD drivers -122.4194 37.7749 "driver:100"
GEOADD drivers -122.4083 37.7833 "driver:101"

# Find nearby drivers for passenger
GEORADIUS drivers -122.42 37.78 2 km WITHDIST ASC COUNT 3

# Remove driver when matched
ZREM drivers "driver:100"
```

**3. Restaurant Delivery**
```redis
# Add restaurants
GEOADD restaurants -122.4194 37.7749 "restaurant:1"

# Check if restaurant can deliver
GEODIST restaurants "restaurant:1" "customer:1000" km

# Find restaurants that deliver to location
GEORADIUS restaurants -122.42 37.78 5 km WITHDIST
```

**4. Real Estate Search**
```redis
# Add properties
GEOADD properties -122.4194 37.7749 "property:100"

# Search in area
GEORADIUS properties -122.4 37.7 3 km WITHDIST WITHCOORD

# Get distance from landmark
GEODIST properties "property:100" "landmark:downtown" km
```

**5. Event Discovery**
```redis
# Add events
GEOADD events -122.4194 37.7749 "event:concert:100"
GEOADD events -122.4083 37.7833 "event:sports:101"

# Find nearby events
GEORADIUS events -122.42 37.78 10 km WITHDIST ASC
```

---

## Time Complexity Reference

### String Operations
```
Command         Time Complexity
─────────────────────────────────
GET             O(1)
SET             O(1)
MGET            O(N) - N keys
MSET            O(N) - N keys
INCR            O(1)
APPEND          O(1)
GETRANGE        O(N) - N is length
SETRANGE        O(N) - N is length
STRLEN          O(1)
```

### List Operations
```
Command         Time Complexity
─────────────────────────────────
LPUSH/RPUSH     O(1)
LPOP/RPOP       O(1)
LLEN            O(1)
LINDEX          O(N) - N is traversal
LRANGE          O(S+N) - S=start, N=elements
LSET            O(N) - N is traversal
LTRIM           O(N) - N is removed
LINSERT         O(N) - N is traversal
LREM            O(N+M) - scan + remove
```

### Set Operations
```
Command         Time Complexity
─────────────────────────────────
SADD            O(1)
SREM            O(1)
SISMEMBER       O(1)
SMEMBERS        O(N) - N members
SCARD           O(1)
SINTER          O(N*M) - smallest set * members
SUNION          O(N) - all members
SDIFF           O(N) - all members
SRANDMEMBER     O(1) or O(N)
SPOP            O(1)
```

### Sorted Set Operations
```
Command         Time Complexity
─────────────────────────────────────
ZADD            O(log(N))
ZREM            O(M*log(N)) - M members
ZSCORE          O(1)
ZINCRBY         O(log(N))
ZCARD           O(1)
ZCOUNT          O(log(N))
ZRANGE          O(log(N)+M) - M returned
ZRANK           O(log(N))
ZRANGEBYSCORE   O(log(N)+M)
ZREMRANGEBYRANK O(log(N)+M)
ZUNIONSTORE     O(N)+O(M*log(M))
```

### Hash Operations
```
Command         Time Complexity
─────────────────────────────────
HSET            O(1)
HGET            O(1)
HMGET           O(N) - N fields
HGETALL         O(N) - N fields
HDEL            O(N) - N fields
HEXISTS         O(1)
HLEN            O(1)
HINCRBY         O(1)
HKEYS/HVALS     O(N) - N fields
```

### Stream Operations
```
Command         Time Complexity
─────────────────────────────────────
XADD            O(1) or O(N) with MAXLEN
XREAD           O(N) - N messages
XRANGE          O(N) - N messages
XLEN            O(1)
XREADGROUP      O(M) - M messages
XACK            O(1)
XPENDING        O(N) - N pending
XCLAIM          O(log(N)) - N pending
```

### Bitmap Operations
```
Command         Time Complexity
─────────────────────────────────
SETBIT          O(1)
GETBIT          O(1)
BITCOUNT        O(N) - N bytes
BITPOS          O(N) - N bytes
BITOP           O(N) - N bytes
```

### HyperLogLog Operations
```
Command         Time Complexity
─────────────────────────────────
PFADD           O(1)
PFCOUNT         O(1) single, O(N) multiple
PFMERGE         O(N) - N HLLs
```

### Geospatial Operations
```
Command         Time Complexity
─────────────────────────────────────
GEOADD          O(log(N)) per item
GEODIST         O(log(N))
GEOPOS          O(log(N))
GEORADIUS       O(N+log(M)) - N in radius, M total
GEOSEARCH       O(N+log(M))
```

---

## Memory Optimization

### Data Structure Encoding

Redis uses different encodings for memory efficiency:

**String Encodings:**
```
int:    Integers stored as long (8 bytes)
embstr: Strings ≤ 44 bytes (embedded)
raw:    Strings > 44 bytes (separate allocation)

# Check encoding
OBJECT ENCODING key
```

**List Encodings:**
```
quicklist: Combination of ziplist and linked list
           (default since Redis 3.2)

# Config
list-max-ziplist-size -2        # Max size per node
list-compress-depth 0           # Compress depth
```

**Set Encodings:**
```
intset:  All integer members, ≤ 512 elements
hashtable: Otherwise

# Config
set-max-intset-entries 512
```

**Sorted Set Encodings:**
```
ziplist: ≤ 128 elements, each ≤ 64 bytes
skiplist: Otherwise

# Config
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
```

**Hash Encodings:**
```
ziplist: ≤ 512 fields, each ≤ 64 bytes
hashtable: Otherwise

# Config
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
```

### Memory Optimization Techniques

**1. Use Hashes for Multiple Fields**
```redis
# Inefficient: 100 bytes per key overhead
SET user:1000:name "Alice"
SET user:1000:email "alice@example.com"
SET user:1000:age "30"

# Efficient: Single hash, less overhead
HSET user:1000 name "Alice" email "alice@example.com" age 30
```

**2. Compress Field Names**
```redis
# Inefficient
HSET user:1000 username "alice" email_address "alice@example.com"

# Efficient
HSET user:1000 u "alice" e "alice@example.com"
```

**3. Use Appropriate Data Types**
```redis
# Inefficient: JSON string
SET data:1000 '{"views":100,"likes":50}'

# Efficient: Hash
HSET data:1000 v 100 l 50
```

**4. Leverage Ziplist Encoding**
```redis
# Keep hashes small to use ziplist
# Split large hashes if needed
HSET user:1000:profile name "Alice" email "alice@example.com"
HSET user:1000:stats views 100 likes 50
```

**5. Use Integers for Scores**
```redis
# Sorted set with integer scores uses less memory
ZADD leaderboard 1000 "player1"  # Good
ZADD leaderboard 1000.5 "player2"  # Uses more memory
```

**6. Set Expiration on Temporary Data**
```redis
SET session:abc123 "data" EX 3600
SETEX cache:user:1000 300 "data"
```

**7. Use Bitmaps for Boolean Flags**
```redis
# Inefficient: One key per user
SET online:user:1000 1
SET online:user:1001 1

# Efficient: Single bitmap
SETBIT online 1000 1
SETBIT online 1001 1
```

**8. Use HyperLogLog for Cardinality**
```redis
# Inefficient: Set grows with cardinality
SADD visitors "user:1000" "user:1001" ...

# Efficient: Fixed 12KB memory
PFADD visitors "user:1000" "user:1001" ...
```

### Memory Analysis

```redis
# Get memory usage
MEMORY USAGE key

# Memory stats
INFO memory

# Sample memory usage
MEMORY DOCTOR

# Key analysis
MEMORY STATS
```

### Configuration for Memory

```redis
# Maximum memory
maxmemory 2gb

# Eviction policy
maxmemory-policy allkeys-lru

# Eviction policies:
# noeviction: Return errors
# allkeys-lru: Evict least recently used
# allkeys-lfu: Evict least frequently used
# volatile-lru: Evict LRU with TTL
# volatile-lfu: Evict LFU with TTL
# volatile-ttl: Evict shortest TTL
# volatile-random: Evict random with TTL
# allkeys-random: Evict random
```

---

## Persistence Strategies

### RDB (Redis Database Backup)

**Mechanism**: Point-in-time snapshots

**Configuration:**
```redis
# Save after time and changes
save 900 1      # After 900s if ≥1 change
save 300 10     # After 300s if ≥10 changes
save 60 10000   # After 60s if ≥10,000 changes

# Disable
save ""

# Compression
rdbcompression yes

# Checksum
rdbchecksum yes

# Filename
dbfilename dump.rdb

# Directory
dir /var/lib/redis
```

**Manual Snapshot:**
```redis
SAVE         # Synchronous (blocks)
BGSAVE       # Asynchronous (forks)
LASTSAVE     # Get last save timestamp
```

**Advantages:**
- Compact single file
- Good for backups
- Faster restarts
- Better for disaster recovery

**Disadvantages:**
- Data loss between snapshots
- Fork can be expensive
- Not suitable for write-heavy workloads

### AOF (Append-Only File)

**Mechanism**: Log of write operations

**Configuration:**
```redis
# Enable AOF
appendonly yes

# Filename
appendfilename "appendonly.aof"

# Fsync policy
appendfsync always      # Every write (slow, safest)
appendfsync everysec    # Every second (balanced)
appendfsync no          # OS decides (fast, least safe)

# Rewrite
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
```

**Manual Rewrite:**
```redis
BGREWRITEAOF   # Compact AOF file
```

**Advantages:**
- More durable
- Can replay operations
- Automatic rewrite
- Better for write-heavy

**Disadvantages:**
- Larger file size
- Slower restarts
- Potential performance impact

### Hybrid Persistence (RDB + AOF)

**Configuration:**
```redis
# Use both RDB and AOF
save 900 1
appendonly yes
appendfsync everysec

# Load AOF on startup (more complete)
aof-use-rdb-preamble yes
```

**Strategy:**
- RDB for base snapshot
- AOF for recent changes
- Best durability and recovery

### Persistence Strategies by Use Case

**1. Cache (No Persistence)**
```redis
save ""
appendonly no
```

**2. Session Store (AOF)**
```redis
appendonly yes
appendfsync everysec
```

**3. Analytics (RDB)**
```redis
save 900 1
save 300 10
appendonly no
```

**4. Critical Data (Hybrid)**
```redis
save 900 1
appendonly yes
appendfsync everysec
aof-use-rdb-preamble yes
```

**5. Write-Heavy (AOF)**
```redis
appendonly yes
appendfsync everysec
auto-aof-rewrite-percentage 100
```

### Backup and Restore

**Backup:**
```bash
# RDB backup
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /backup/

# AOF backup
cp /var/lib/redis/appendonly.aof /backup/

# Both
redis-cli --rdb /backup/dump.rdb
```

**Restore:**
```bash
# Stop Redis
systemctl stop redis

# Copy backup
cp /backup/dump.rdb /var/lib/redis/
cp /backup/appendonly.aof /var/lib/redis/

# Set permissions
chown redis:redis /var/lib/redis/*

# Start Redis
systemctl start redis
```

---

## Replication and Clustering

### Replication

**Master-Replica Setup:**

**Master Configuration:**
```redis
# redis.conf
bind 0.0.0.0
protected-mode yes
requirepass masterpassword
```

**Replica Configuration:**
```redis
# redis.conf
replicaof master-host 6379
masterauth masterpassword
replica-read-only yes

# Dynamic
REPLICAOF host port
REPLICAOF NO ONE  # Promote to master
```

**Replication Info:**
```redis
INFO replication

# Returns:
# role:master
# connected_slaves:2
# slave0:ip=10.0.0.2,port=6379,state=online
```

**Replication Features:**
- Asynchronous by default
- One master, multiple replicas
- Replicas can have replicas
- Non-blocking on master
- Automatic reconnection

**Sentinel for HA:**
```redis
# sentinel.conf
sentinel monitor mymaster 127.0.0.1 6379 2
sentinel auth-pass mymaster masterpassword
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 10000
sentinel parallel-syncs mymaster 1
```

**Start Sentinel:**
```bash
redis-sentinel /etc/redis/sentinel.conf
```

### Redis Cluster

**Cluster Setup:**

**Configuration (each node):**
```redis
# redis.conf
port 7000
cluster-enabled yes
cluster-config-file nodes-7000.conf
cluster-node-timeout 5000
appendonly yes
```

**Create Cluster:**
```bash
redis-cli --cluster create \
  127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \
  127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 \
  --cluster-replicas 1
```

**Cluster Operations:**
```redis
CLUSTER INFO
CLUSTER NODES
CLUSTER SLOTS
CLUSTER MEET ip port
CLUSTER FORGET node-id
CLUSTER REPLICATE node-id
CLUSTER FAILOVER
```

**Cluster Features:**
- 16,384 hash slots
- Automatic sharding
- Multi-master
- Automatic failover
- Horizontal scaling

**Hash Tags for Multi-Key Ops:**
```redis
# Same slot for related keys
SET {user:1000}:profile "data"
SET {user:1000}:preferences "data"

# Multi-key operations work
MGET {user:1000}:profile {user:1000}:preferences
```

**Cluster Limitations:**
- No database selection (single DB 0)
- Limited multi-key operations
- Requires cluster-aware clients
- No cross-slot transactions

### Scaling Strategies

**1. Vertical Scaling**
- More RAM
- Faster CPU
- Better network

**2. Read Scaling (Replication)**
- Add read replicas
- Distribute read load
- Geographic distribution

**3. Write Scaling (Cluster)**
- Shard across nodes
- Horizontal scaling
- More write capacity

**4. Hybrid Approach**
- Cluster + replicas
- Scale reads and writes
- High availability

---

## Pub/Sub Patterns

### Basic Pub/Sub

**Subscribe:**
```redis
SUBSCRIBE channel [channel ...]
PSUBSCRIBE pattern [pattern ...]
UNSUBSCRIBE [channel ...]
PUNSUBSCRIBE [pattern ...]

# Examples
SUBSCRIBE notifications
SUBSCRIBE chat:room:100
PSUBSCRIBE chat:*
```

**Publish:**
```redis
PUBLISH channel message

# Examples
PUBLISH notifications "New message"
PUBLISH chat:room:100 "Hello!"
```

**Pub/Sub Info:**
```redis
PUBSUB CHANNELS [pattern]       # List channels
PUBSUB NUMSUB [channel ...]     # Subscriber count
PUBSUB NUMPAT                   # Pattern count
```

### Pub/Sub Use Cases

**1. Real-Time Notifications**
```redis
# Publisher
PUBLISH notifications '{"type":"order","order_id":100}'

# Subscriber
SUBSCRIBE notifications
# Receives: {"type":"order","order_id":100}
```

**2. Chat Application**
```redis
# User joins room
SUBSCRIBE chat:room:100

# User sends message
PUBLISH chat:room:100 "Hello everyone!"

# User leaves
UNSUBSCRIBE chat:room:100
```

**3. Event Broadcasting**
```redis
# Broadcast to all listeners
PUBLISH events:global '{"event":"user_signup","user_id":1000}'

# Pattern subscription for all events
PSUBSCRIBE events:*
```

**4. Cache Invalidation**
```redis
# When data changes
PUBLISH cache:invalidate:user:1000 "update"

# Cache services listen
SUBSCRIBE cache:invalidate:*
# Clear local cache on message
```

**5. Task Distribution**
```redis
# Publish task
PUBLISH tasks:process '{"task":"thumbnail","image_id":42}'

# Workers subscribe
SUBSCRIBE tasks:process
# Process task when received
```

### Pub/Sub Limitations

**Fire-and-Forget:**
- No message persistence
- If no subscribers, message lost
- Subscribers must be active

**No Acknowledgment:**
- Can't confirm delivery
- No retry mechanism
- Subscribers can miss messages

**Solutions:**

**1. Use Streams for Persistence:**
```redis
# Instead of PUBLISH
XADD tasks * task "process" data "value"

# Instead of SUBSCRIBE
XREADGROUP GROUP workers worker1 STREAMS tasks >
```

**2. Hybrid Approach:**
```redis
# Pub/Sub for real-time + Stream for persistence
PUBLISH notifications "new_message"
XADD notifications:log * message "new_message"
```

---

## Transactions and Pipelining

### Transactions (MULTI/EXEC)

**Basic Transaction:**
```redis
MULTI
SET key1 value1
SET key2 value2
EXEC

# Returns: [OK, OK]
```

**Discard Transaction:**
```redis
MULTI
SET key1 value1
SET key2 value2
DISCARD  # Cancel transaction
```

**Watch for Optimistic Locking:**
```redis
WATCH key1
val = GET key1
MULTI
SET key1 newval
EXEC  # Fails if key1 changed since WATCH
```

**Transaction Example:**
```redis
# Transfer balance
WATCH account:1000 account:1001

balance1 = GET account:1000
balance2 = GET account:1001

MULTI
DECRBY account:1000 100
INCRBY account:1001 100
EXEC
```

**Transaction Characteristics:**
- All commands queued
- Executed atomically
- No partial execution
- WATCH for optimistic locking
- Commands not executed until EXEC
- Syntax errors abort
- Runtime errors continue

### Pipelining

**Without Pipelining:**
```python
# RTT per command
r.set("key1", "value1")  # RTT 1
r.set("key2", "value2")  # RTT 2
r.set("key3", "value3")  # RTT 3
# Total: 3 RTTs
```

**With Pipelining:**
```python
# Single RTT for all
pipe = r.pipeline(transaction=False)
pipe.set("key1", "value1")
pipe.set("key2", "value2")
pipe.set("key3", "value3")
pipe.execute()
# Total: 1 RTT
```

**Pipelining Use Cases:**

**1. Bulk Operations**
```python
pipe = r.pipeline(transaction=False)
for i in range(10000):
    pipe.set(f"key:{i}", f"value:{i}")
pipe.execute()
```

**2. Multiple Reads**
```python
pipe = r.pipeline(transaction=False)
pipe.get("user:1000:name")
pipe.get("user:1000:email")
pipe.hgetall("user:1000:prefs")
results = pipe.execute()
```

**3. Complex Operations**
```python
pipe = r.pipeline(transaction=False)
pipe.incr("counter")
pipe.lpush("events", event_data)
pipe.expire("session:123", 3600)
pipe.execute()
```

**Pipelining vs Transactions:**
- Pipeline: Just batching (performance)
- Transaction: Atomic execution (consistency)
- Can combine: `pipeline(transaction=True)`

### Lua Scripting for Atomicity

```redis
EVAL script numkeys key [key ...] arg [arg ...]
EVALSHA sha1 numkeys key [key ...] arg [arg ...]
SCRIPT LOAD script
SCRIPT EXISTS sha1 [sha1 ...]
SCRIPT FLUSH
```

**Lua Script Example:**
```lua
-- Atomic increment with limit
local current = redis.call('GET', KEYS[1])
if not current then
  current = 0
end
if tonumber(current) < tonumber(ARGV[1]) then
  return redis.call('INCR', KEYS[1])
else
  return current
end
```

**Execute:**
```redis
EVAL "local current = redis.call('GET', KEYS[1])..." 1 counter 100
```

---

## Lua Scripting

### Lua Basics in Redis

**Script Structure:**
```lua
-- Access Redis commands
redis.call('command', ...) -- Errors propagate
redis.pcall('command', ...) -- Errors returned

-- Return values
return value

-- KEYS and ARGV
KEYS[1], KEYS[2], ...  -- Key arguments
ARGV[1], ARGV[2], ...  -- Other arguments
```

**Execution:**
```redis
EVAL "return redis.call('GET', KEYS[1])" 1 mykey

# Load and execute by SHA
SCRIPT LOAD "return redis.call('GET', KEYS[1])"
EVALSHA sha1 1 mykey
```

### Common Lua Patterns

**1. Atomic Increment with Limit**
```lua
local current = tonumber(redis.call('GET', KEYS[1]) or 0)
if current < tonumber(ARGV[1]) then
  return redis.call('INCR', KEYS[1])
else
  return -1
end
```

**2. Rate Limiting (Token Bucket)**
```lua
local tokens_key = KEYS[1]
local timestamp_key = KEYS[2]
local rate = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local last_tokens = tonumber(redis.call('GET', tokens_key) or capacity)
local last_refreshed = tonumber(redis.call('GET', timestamp_key) or 0)

local delta = math.max(0, now - last_refreshed)
local filled_tokens = math.min(capacity, last_tokens + (delta * rate))

if filled_tokens >= 1 then
  redis.call('SET', tokens_key, filled_tokens - 1)
  redis.call('SET', timestamp_key, now)
  return 1
else
  return 0
end
```

**3. Distributed Lock**
```lua
-- Acquire lock
if redis.call('EXISTS', KEYS[1]) == 0 then
  redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
  return 1
else
  return 0
end

-- Release lock (check ownership)
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
else
  return 0
end
```

**4. Dequeue with Priority**
```lua
-- Try multiple queues in priority order
for i = 1, #KEYS do
  local result = redis.call('RPOP', KEYS[i])
  if result then
    return {i, result}
  end
end
return nil
```

**5. Atomic List Move**
```lua
local value = redis.call('RPOP', KEYS[1])
if value then
  redis.call('LPUSH', KEYS[2], value)
  return value
else
  return nil
end
```

**6. Complex Counter**
```lua
-- Increment multiple counters atomically
redis.call('HINCRBY', KEYS[1], 'views', 1)
redis.call('HINCRBY', KEYS[1], 'daily', 1)
redis.call('ZADD', KEYS[2], ARGV[1], ARGV[2])
return redis.call('HGET', KEYS[1], 'views')
```

### Lua Scripting Best Practices

1. **Keep Scripts Short**: Blocks server
2. **Avoid Loops with External Data**: Use Redis data
3. **Use ARGV for Values**: KEYS for keys only
4. **Cache Script SHA**: Load once, execute many
5. **Error Handling**: Use pcall for non-critical
6. **Deterministic**: No random, no time
7. **Test Thoroughly**: Hard to debug in production

---

## Caching Strategies

### Cache-Aside (Lazy Loading)

**Pattern:**
```
1. Check cache
2. If miss: Load from DB
3. Write to cache
4. Return data
```

**Implementation:**
```python
def get_user(user_id):
    # Check cache
    cache_key = f"user:{user_id}"
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Cache miss: Load from DB
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)

    # Write to cache
    redis.setex(cache_key, 300, json.dumps(user))

    return user
```

**Advantages:**
- Only cache requested data
- Cache failure not fatal
- Simple implementation

**Disadvantages:**
- Cache miss penalty
- Stale data possible
- Three round trips on miss

### Write-Through

**Pattern:**
```
1. Write to cache
2. Write to DB
3. Return success
```

**Implementation:**
```python
def update_user(user_id, data):
    # Update cache
    cache_key = f"user:{user_id}"
    redis.setex(cache_key, 300, json.dumps(data))

    # Update DB
    db.query("UPDATE users SET ... WHERE id = ?", user_id)

    return True
```

**Advantages:**
- Cache always fresh
- No stale reads
- Read performance

**Disadvantages:**
- Write latency
- Unused data cached
- Cache failure impacts writes

### Write-Behind (Write-Back)

**Pattern:**
```
1. Write to cache
2. Return success
3. Async write to DB
```

**Implementation:**
```python
def update_user(user_id, data):
    # Update cache
    cache_key = f"user:{user_id}"
    redis.setex(cache_key, 300, json.dumps(data))

    # Queue for async DB write
    redis.lpush("write_queue", json.dumps({
        "table": "users",
        "id": user_id,
        "data": data
    }))

    return True

# Background worker
def write_worker():
    while True:
        item = redis.brpop("write_queue", timeout=1)
        if item:
            write_to_db(item)
```

**Advantages:**
- Fast writes
- Batch DB operations
- Resilient to DB issues

**Disadvantages:**
- Complex implementation
- Data loss risk
- Consistency challenges

### Cache Invalidation

**1. TTL-Based**
```python
# Set expiration
redis.setex("user:1000", 300, data)

# Touch to extend
redis.expire("user:1000", 300)
```

**2. Event-Based**
```python
# Invalidate on update
def update_user(user_id):
    db.update_user(user_id)
    redis.delete(f"user:{user_id}")
```

**3. Pub/Sub Invalidation**
```python
# Publisher (on update)
redis.publish("cache:invalidate", f"user:{user_id}")

# Subscriber
pubsub = redis.pubsub()
pubsub.subscribe("cache:invalidate")
for message in pubsub.listen():
    redis.delete(message['data'])
```

**4. Version-Based**
```python
# Include version in key
version = redis.incr("user:1000:version")
redis.set(f"user:1000:v{version}", data)
```

### Cache Patterns

**1. Memoization**
```python
def expensive_computation(arg):
    cache_key = f"result:{arg}"
    cached = redis.get(cache_key)
    if cached:
        return cached

    result = compute(arg)
    redis.setex(cache_key, 3600, result)
    return result
```

**2. Materialized Views**
```python
# Pre-compute and cache
def update_user_stats(user_id):
    stats = compute_user_stats(user_id)
    redis.hmset(f"stats:{user_id}", stats)
    redis.expire(f"stats:{user_id}", 3600)
```

**3. Fragment Caching**
```python
# Cache HTML fragments
def render_sidebar(user_id):
    cache_key = f"fragment:sidebar:{user_id}"
    cached = redis.get(cache_key)
    if cached:
        return cached

    html = generate_sidebar(user_id)
    redis.setex(cache_key, 300, html)
    return html
```

**4. Database Query Result Cache**
```python
def query_cache(sql, params):
    cache_key = f"query:{hash(sql+str(params))}"
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    result = db.query(sql, params)
    redis.setex(cache_key, 60, json.dumps(result))
    return result
```

**5. Session Cache**
```python
# Store session in Redis
def save_session(session_id, data):
    redis.setex(f"session:{session_id}", 3600, json.dumps(data))

def get_session(session_id):
    data = redis.get(f"session:{session_id}")
    return json.loads(data) if data else None
```

---

## Common Patterns

### Rate Limiting

**1. Simple Counter**
```python
def is_allowed(user_id, limit=100):
    key = f"rate:{user_id}:{int(time.time() // 60)}"
    count = redis.incr(key)
    redis.expire(key, 60)
    return count <= limit
```

**2. Sliding Window (Sorted Set)**
```python
def is_allowed_sliding(user_id, limit=100, window=60):
    key = f"rate:{user_id}"
    now = time.time()

    # Remove old entries
    redis.zremrangebyscore(key, 0, now - window)

    # Count requests in window
    count = redis.zcard(key)

    if count < limit:
        redis.zadd(key, {str(uuid.uuid4()): now})
        redis.expire(key, window)
        return True
    return False
```

**3. Token Bucket (Lua)**
```lua
-- See Lua Scripting section
```

### Distributed Lock

**Simple Lock:**
```python
def acquire_lock(resource, timeout=10):
    lock_key = f"lock:{resource}"
    identifier = str(uuid.uuid4())

    # Try to acquire
    if redis.set(lock_key, identifier, nx=True, ex=timeout):
        return identifier
    return None

def release_lock(resource, identifier):
    lock_key = f"lock:{resource}"

    # Lua script for atomic check-and-delete
    script = """
    if redis.call('GET', KEYS[1]) == ARGV[1] then
        return redis.call('DEL', KEYS[1])
    else
        return 0
    end
    """
    return redis.eval(script, 1, lock_key, identifier)
```

**Redlock Algorithm:**
```python
# Use multiple Redis instances
# Acquire lock on majority
# More complex, more reliable
```

### Leaderboard

**Implementation:**
```python
# Update score
redis.zadd("leaderboard", {f"player:{player_id}": score})

# Get top 10
top_10 = redis.zrevrange("leaderboard", 0, 9, withscores=True)

# Get player rank
rank = redis.zrevrank("leaderboard", f"player:{player_id}")

# Get player score
score = redis.zscore("leaderboard", f"player:{player_id}")

# Get players around user
rank = redis.zrevrank("leaderboard", f"player:{player_id}")
nearby = redis.zrevrange("leaderboard", max(0, rank-2), rank+2, withscores=True)
```

**Time-Based Leaderboard:**
```python
# Weekly leaderboard
week = datetime.now().isocalendar()[1]
key = f"leaderboard:week:{week}"
redis.zadd(key, {f"player:{player_id}": score})
redis.expire(key, 7 * 24 * 3600)
```

### Session Store

**Implementation:**
```python
def create_session(user_id, data):
    session_id = str(uuid.uuid4())
    session_key = f"session:{session_id}"

    session_data = {
        "user_id": user_id,
        "created": time.time(),
        **data
    }

    redis.hmset(session_key, session_data)
    redis.expire(session_key, 3600)
    return session_id

def get_session(session_id):
    session_key = f"session:{session_id}"
    data = redis.hgetall(session_key)

    if data:
        # Extend expiration on access
        redis.expire(session_key, 3600)

    return data

def destroy_session(session_id):
    redis.delete(f"session:{session_id}")
```

### Message Queue

**Simple Queue:**
```python
# Producer
redis.lpush("queue:tasks", json.dumps(task))

# Consumer
while True:
    task = redis.brpop("queue:tasks", timeout=1)
    if task:
        process_task(json.loads(task[1]))
```

**Reliable Queue:**
```python
# Producer
redis.lpush("queue:pending", json.dumps(task))

# Consumer
while True:
    # Move to processing
    task = redis.brpoplpush("queue:pending", "queue:processing", timeout=1)
    if task:
        try:
            process_task(json.loads(task))
            # Success: Remove from processing
            redis.lrem("queue:processing", 1, task)
        except Exception as e:
            # Failure: Move back to pending
            redis.rpoplpush("queue:processing", "queue:pending")
```

**Priority Queue:**
```python
# Add with priority (lower score = higher priority)
redis.zadd("queue:priority", {json.dumps(task): priority})

# Get next task
result = redis.zpopmin("queue:priority")
if result:
    task = json.loads(result[0])
    process_task(task)
```

### Task Scheduler

**Implementation:**
```python
# Schedule task
redis.zadd("scheduled:tasks", {
    json.dumps({"task": "send_email", "user_id": 1000}):
    time.time() + 3600  # Execute in 1 hour
})

# Worker polls for due tasks
while True:
    now = time.time()

    # Get due tasks
    tasks = redis.zrangebyscore("scheduled:tasks", 0, now)

    for task_data in tasks:
        task = json.loads(task_data)
        execute_task(task)

        # Remove from schedule
        redis.zrem("scheduled:tasks", task_data)

    time.sleep(1)
```

---

## Production Best Practices

### Performance

**1. Use Pipelining**
```python
# Batch commands
pipe = redis.pipeline(transaction=False)
for i in range(1000):
    pipe.set(f"key:{i}", f"value:{i}")
pipe.execute()
```

**2. Avoid KEYS Command**
```redis
# Bad: O(N) blocks server
KEYS user:*

# Good: Use SCAN
SCAN 0 MATCH user:* COUNT 100
```

**3. Use Connection Pooling**
```python
# Reuse connections
pool = redis.ConnectionPool(host='localhost', port=6379, max_connections=10)
r = redis.Redis(connection_pool=pool)
```

**4. Monitor Slow Queries**
```redis
CONFIG SET slowlog-log-slower-than 10000  # 10ms
SLOWLOG GET 10
```

**5. Use Appropriate Data Structures**
```redis
# Use hash for objects
# Use sorted set for rankings
# Use bitmap for flags
# See "Memory Optimization" section
```

### Monitoring

**Key Metrics:**
```redis
INFO stats
INFO memory
INFO clients
INFO replication

# Specific metrics
INFO keyspace
INFO commandstats
```

**Monitor in Real-Time:**
```redis
MONITOR  # Shows all commands (performance impact!)
```

**Client List:**
```redis
CLIENT LIST
CLIENT KILL ip:port
```

### Security

**1. Require Password**
```redis
# redis.conf
requirepass strongpassword

# Client
redis-cli -a strongpassword
AUTH strongpassword
```

**2. Bind to Specific IP**
```redis
# redis.conf
bind 127.0.0.1 10.0.0.1
protected-mode yes
```

**3. Rename Dangerous Commands**
```redis
# redis.conf
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG "CONFIG_abc123"
```

**4. Use TLS**
```redis
# redis.conf
tls-port 6380
tls-cert-file /path/to/cert.pem
tls-key-file /path/to/key.pem
tls-ca-cert-file /path/to/ca.pem
```

**5. ACL (Redis 6+)**
```redis
# Create user with limited permissions
ACL SETUSER alice on >password ~cache:* +get +set

# List users
ACL LIST

# Show current user
ACL WHOAMI
```

### High Availability

**1. Persistence**
```redis
# Enable both RDB and AOF
save 900 1
appendonly yes
appendfsync everysec
```

**2. Replication**
```redis
# Set up replicas
replicaof master-host 6379
```

**3. Sentinel**
```redis
# Configure Sentinel for automatic failover
sentinel monitor mymaster 127.0.0.1 6379 2
sentinel down-after-milliseconds mymaster 5000
```

**4. Cluster**
```redis
# Use Redis Cluster for sharding
cluster-enabled yes
```

**5. Backup Strategy**
```bash
# Regular backups
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /backup/
```

### Troubleshooting

**1. Memory Issues**
```redis
# Analyze memory
MEMORY DOCTOR
MEMORY STATS
INFO memory

# Find large keys
redis-cli --bigkeys

# Set eviction policy
CONFIG SET maxmemory-policy allkeys-lru
```

**2. Performance Issues**
```redis
# Check slow queries
SLOWLOG GET 10

# Monitor latency
redis-cli --latency
redis-cli --latency-history

# Check stats
INFO stats
INFO commandstats
```

**3. Connection Issues**
```redis
# Check clients
CLIENT LIST

# Check max connections
CONFIG GET maxclients
CONFIG SET maxclients 10000
```

**4. Persistence Issues**
```redis
# Check last save
LASTSAVE

# Force save
BGSAVE

# Check AOF status
INFO persistence
```

### Optimization Checklist

**Configuration:**
- [ ] Set appropriate `maxmemory`
- [ ] Configure eviction policy
- [ ] Enable persistence if needed
- [ ] Set connection limits
- [ ] Configure timeout values
- [ ] Enable AOF rewrite

**Data Modeling:**
- [ ] Use appropriate data structures
- [ ] Keep keys short
- [ ] Use hashes for objects
- [ ] Set TTL on temporary data
- [ ] Avoid large values
- [ ] Use pipelining

**Operations:**
- [ ] Use SCAN instead of KEYS
- [ ] Batch operations
- [ ] Monitor slow queries
- [ ] Set up alerting
- [ ] Regular backups
- [ ] Test failover

**Security:**
- [ ] Require password
- [ ] Bind to specific IPs
- [ ] Use TLS in production
- [ ] Rename dangerous commands
- [ ] Set up ACLs
- [ ] Regular security audits

---

## Summary

This comprehensive reference covers all major Redis data structures, operations, and patterns. Key takeaways:

1. **Choose the Right Data Structure**: Each structure optimized for specific use cases
2. **Understand Time Complexity**: Critical for performance at scale
3. **Optimize Memory**: Use appropriate encodings and techniques
4. **Plan Persistence**: Balance durability and performance
5. **Scale Appropriately**: Replication for reads, clustering for writes
6. **Monitor and Maintain**: Proactive monitoring prevents issues
7. **Secure Properly**: Defense in depth for production
8. **Use Patterns**: Leverage proven solutions for common problems

Redis is a versatile tool - mastering its data structures and patterns enables building high-performance, scalable applications.
