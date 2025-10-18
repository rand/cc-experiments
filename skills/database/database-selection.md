---
name: database-database-selection
description: Starting new projects and choosing database technology
---



# Database Selection

**Scope**: Choosing the right database, SQL vs NoSQL, database comparison
**Lines**: ~280
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Starting new projects and choosing database technology
- Evaluating database options for specific use cases
- Migrating from one database to another
- Architecting multi-database systems
- Scaling existing database infrastructure
- Comparing SQL vs NoSQL tradeoffs
- Selecting database for specific workload patterns

## Core Concepts

### SQL vs NoSQL Decision Criteria

**SQL (Relational)**:
- Structured data with fixed schema
- Complex relationships between entities
- ACID transactions required
- Complex queries with JOINs
- Data integrity is critical

**NoSQL (Non-Relational)**:
- Flexible/dynamic schema
- Simple relationships or denormalized data
- High scalability requirements
- Simple queries on large datasets
- Performance over strict consistency

---

## Database Comparison Matrix

### PostgreSQL

**Type**: Relational (SQL)
**Best For**: General-purpose applications, complex queries, data integrity

**Strengths**:
- Full ACID compliance
- Rich data types (JSON, arrays, ranges)
- Advanced features (CTEs, window functions, full-text search)
- Excellent for complex queries and JOINs
- Strong consistency
- Mature ecosystem

**Weaknesses**:
- Vertical scaling easier than horizontal
- Complex sharding setup
- Writes can be slower than NoSQL

**Use Cases**:
- E-commerce platforms
- Financial systems
- SaaS applications
- Admin dashboards
- CMS platforms

**Example**:
```sql
-- Complex query with JOINs, aggregations, CTEs
WITH top_customers AS (
  SELECT user_id, SUM(total) as spent
  FROM orders
  WHERE created_at > NOW() - INTERVAL '1 year'
  GROUP BY user_id
  ORDER BY spent DESC
  LIMIT 100
)
SELECT u.email, tc.spent, COUNT(o.id) as order_count
FROM top_customers tc
JOIN users u ON tc.user_id = u.id
JOIN orders o ON o.user_id = u.id
GROUP BY u.email, tc.spent;
```

### MySQL

**Type**: Relational (SQL)
**Best For**: Web applications, read-heavy workloads, simple transactions

**Strengths**:
- Fast read performance
- Wide hosting support
- Simple replication
- Mature ecosystem
- Lower resource usage than PostgreSQL

**Weaknesses**:
- Less advanced features than PostgreSQL
- Weaker for complex queries
- Less strict data integrity by default

**Use Cases**:
- WordPress/Drupal sites
- Read-heavy web apps
- Simple CRUD applications
- Shared hosting environments

**When to choose over PostgreSQL**:
- Need maximum read performance
- Simpler queries (fewer JOINs)
- Constrained resources
- Existing MySQL ecosystem

### MongoDB

**Type**: Document (NoSQL)
**Best For**: Flexible schemas, hierarchical data, rapid development

**Strengths**:
- Flexible schema (JSON documents)
- Horizontal scaling (sharding)
- Fast reads/writes
- Embedding reduces JOINs
- Developer-friendly (JSON)

**Weaknesses**:
- No multi-document ACID (before v4.0)
- Joins ($lookup) are expensive
- Data duplication common
- 16MB document limit

**Use Cases**:
- Content management
- Catalogs (products, articles)
- Real-time analytics
- User profiles
- Event logging

**Example**:
```javascript
// Embedded document (no JOIN needed)
{
  "_id": ObjectId("..."),
  "user": "alice",
  "cart": {
    "items": [
      { "product": "Widget", "price": 29.99, "qty": 2 },
      { "product": "Gadget", "price": 49.99, "qty": 1 }
    ],
    "total": 109.97
  }
}
```

### Redis

**Type**: In-memory key-value (NoSQL)
**Best For**: Caching, sessions, real-time analytics, queues

**Strengths**:
- Extremely fast (in-memory)
- Rich data structures (lists, sets, sorted sets, hashes)
- Pub/Sub messaging
- TTL (auto-expiration)
- Atomic operations

**Weaknesses**:
- Limited by RAM
- Not durable by default (persistence optional)
- No complex queries
- Single-threaded (one CPU core)

**Use Cases**:
- Session storage
- Caching layer
- Rate limiting
- Leaderboards
- Real-time analytics
- Job queues

**Example**:
```bash
# Cache user session
SET session:abc123 '{"user_id": 42, "email": "alice@example.com"}' EX 3600

# Rate limiting
INCR ratelimit:user:42
EXPIRE ratelimit:user:42 60

# Leaderboard
ZADD leaderboard 9500 "alice"
ZREVRANGE leaderboard 0 9 WITHSCORES
```

### DynamoDB

**Type**: Key-value/Document (NoSQL, AWS)
**Best For**: Serverless apps, high-scale key-value, event-driven

**Strengths**:
- Fully managed (auto-scaling)
- Single-digit millisecond latency
- Global tables (multi-region)
- Pay-per-request pricing
- Integrated with AWS ecosystem

**Weaknesses**:
- Expensive at high throughput
- Limited query patterns (no ad-hoc queries)
- Vendor lock-in (AWS)
- Complex pricing model

**Use Cases**:
- Serverless applications (Lambda)
- Mobile backends
- Gaming leaderboards
- IoT data
- Session storage

**When to choose**:
- Using AWS ecosystem
- Need auto-scaling
- Predictable access patterns (partition key design)

### SQLite

**Type**: Relational (SQL, embedded)
**Best For**: Local storage, embedded apps, development

**Strengths**:
- Zero configuration
- Single file database
- Full SQL support
- Lightweight (small footprint)
- Cross-platform

**Weaknesses**:
- No multi-user concurrency (writes lock database)
- No network access (local only)
- Limited scalability

**Use Cases**:
- Mobile apps (iOS, Android)
- Desktop applications
- Local development
- Embedded systems
- Configuration storage

**When to choose**:
- Single-user applications
- Embedded use cases
- Local-first apps
- Development/testing

---

## ACID vs BASE Tradeoffs

### ACID (SQL Databases)

**Atomicity**: Transaction succeeds completely or fails completely
**Consistency**: Data moves from one valid state to another
**Isolation**: Concurrent transactions don't interfere
**Durability**: Committed data is permanent

**Example** (PostgreSQL):
```sql
BEGIN;
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;
  UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;  -- Both succeed or both fail
```

**Best for**:
- Financial transactions
- Inventory management
- Order processing
- Any system where data integrity is critical

### BASE (NoSQL Databases)

**Basically Available**: System remains operational
**Soft state**: State may change over time (eventual consistency)
**Eventual consistency**: System will become consistent eventually

**Example** (MongoDB):
```javascript
// Write may return before replication completes
db.users.updateOne(
  { _id: ObjectId("...") },
  { $inc: { post_count: 1 } }
)
// Other replicas may see stale data temporarily
```

**Best for**:
- Social media feeds
- Analytics dashboards
- Content delivery
- Systems prioritizing availability over consistency

---

## Consistency Models

### Strong Consistency

**Guarantee**: All reads return most recent write

**Databases**: PostgreSQL, MySQL (default), MongoDB (with read concern "linearizable")

**Use case**: Banking, inventory systems

**Tradeoff**: Higher latency, lower availability

### Eventual Consistency

**Guarantee**: Reads will eventually reflect writes (may be stale temporarily)

**Databases**: DynamoDB (default), Cassandra, MongoDB (with read concern "local")

**Use case**: Social feeds, product catalogs, analytics

**Tradeoff**: Lower latency, higher availability, potential stale reads

### Causal Consistency

**Guarantee**: Reads respect causality (if A caused B, all see A before B)

**Databases**: MongoDB (with causal consistency sessions)

**Use case**: Chat applications, collaborative editing

**Tradeoff**: Balance between strong and eventual

---

## Read vs Write Optimization

### Read-Optimized Databases

**Characteristics**:
- Denormalized schemas
- Materialized views
- Aggressive caching
- Read replicas

**Databases**: MySQL (with read replicas), Elasticsearch, ClickHouse

**Patterns**:
```sql
-- Denormalized for reads (PostgreSQL)
CREATE MATERIALIZED VIEW user_stats AS
SELECT
  user_id,
  COUNT(DISTINCT order_id) as order_count,
  SUM(total) as lifetime_value
FROM orders
GROUP BY user_id;

-- Refresh periodically
REFRESH MATERIALIZED VIEW user_stats;
```

**Use cases**:
- Analytics dashboards
- Reporting systems
- Content delivery

### Write-Optimized Databases

**Characteristics**:
- Append-only logs
- Eventual consistency
- Horizontal partitioning

**Databases**: Cassandra, ClickHouse (for inserts), Kafka (event streaming)

**Patterns**:
```javascript
// Append-only event log (MongoDB)
db.events.insertOne({
  event_type: "page_view",
  user_id: 42,
  page: "/products/123",
  timestamp: new Date()
})
// No updates, only inserts
```

**Use cases**:
- Event logging
- Time-series data
- Metrics collection

---

## Scaling Considerations

### Vertical Scaling (Scale Up)

**Approach**: Increase resources (CPU, RAM, disk) on single server

**Best for**: SQL databases, simple setups

**Limits**: Hardware limits (expensive at high end)

**Databases**: PostgreSQL, MySQL, SQLite

### Horizontal Scaling (Scale Out)

**Approach**: Add more servers, distribute data

**Strategies**:

#### Replication (Read Scaling)
```
Write → Primary
Reads → Replicas (multiple)
```

**Databases**: PostgreSQL, MySQL, MongoDB

**Use case**: Read-heavy workloads (10:1 read/write ratio)

#### Sharding (Write Scaling)
```
Data partitioned across multiple servers by key
Users A-M → Shard 1
Users N-Z → Shard 2
```

**Databases**: MongoDB (built-in), PostgreSQL (Citus extension), Cassandra

**Use case**: Massive datasets, write-heavy workloads

**Complexity**: Application-level sharding logic, cross-shard queries expensive

### Decision Tree: Scaling Strategy

```
What's the bottleneck?
│
├─ Reads → Add read replicas
│  └─ Still slow? → Add caching (Redis)
│
├─ Writes → Vertical scaling first
│  └─ Hit limits? → Horizontal sharding
│
└─ Data size → Sharding or partitioning
```

---

## Use Case → Database Mapping

### E-commerce Platform

**Requirements**: Transactions, inventory, complex queries

**Primary**: PostgreSQL
- Orders, products, users (relational)
- ACID transactions for checkout
- Complex reporting queries

**Secondary**: Redis
- Session storage
- Cart caching
- Rate limiting

**Example architecture**:
```
PostgreSQL: Orders, products, users, inventory
Redis: Sessions, cart cache, product cache
S3/CloudFlare: Product images, static assets
```

### Real-Time Analytics

**Requirements**: High write throughput, time-series data

**Primary**: ClickHouse or TimescaleDB (PostgreSQL extension)
- Event logging
- Metrics aggregation
- Fast analytical queries

**Secondary**: Redis
- Real-time counters
- Recent data caching

**Alternative**: MongoDB (with time-series collections)

### Social Media Application

**Requirements**: Flexible schema, high scale, denormalized data

**Primary**: MongoDB
- User profiles
- Posts (with embedded comments)
- Activity feeds

**Secondary**: Redis
- Timeline caching
- Real-time notifications
- Rate limiting

**Tertiary**: PostgreSQL
- User authentication
- Billing/payments

### Content Management System

**Requirements**: Flexible content types, full-text search

**Primary**: PostgreSQL
- Content storage
- User management
- Full-text search (built-in)

**Alternative**: MongoDB + Elasticsearch
- MongoDB for content
- Elasticsearch for search

### Mobile Application

**Requirements**: Offline-first, sync, embedded database

**Primary**: SQLite (local)
- Local data storage
- Offline-first

**Backend**: PostgreSQL or MongoDB
- Server-side sync
- User data

**Sync**: Conflict resolution (last-write-wins or CRDTs)

### High-Frequency Trading

**Requirements**: Ultra-low latency, strong consistency

**Primary**: In-memory database (Redis or custom)
- Sub-millisecond latency
- Atomic operations

**Backup**: PostgreSQL or TimescaleDB
- Audit trail
- Historical data

---

## Decision Tree: Database Selection

```
Start: What's your primary requirement?
│
├─ Strong consistency + ACID?
│  ├─ Yes → SQL (PostgreSQL or MySQL)
│  │   └─ Complex queries? → PostgreSQL
│  │   └─ Read-heavy? → MySQL
│  └─ No → Continue
│
├─ Flexible schema?
│  ├─ Yes → MongoDB
│  └─ No → SQL
│
├─ Key-value access patterns?
│  ├─ Yes + In-memory → Redis
│  ├─ Yes + Persistent → DynamoDB or PostgreSQL
│  └─ No → Continue
│
├─ Time-series data?
│  ├─ Yes → TimescaleDB, ClickHouse, or InfluxDB
│  └─ No → Continue
│
├─ Full-text search?
│  ├─ Primary feature → Elasticsearch
│  ├─ Secondary → PostgreSQL (built-in) or MongoDB
│  └─ No → Continue
│
├─ Graph relationships?
│  ├─ Yes → Neo4j or PostgreSQL (recursive CTEs)
│  └─ No → Continue
│
├─ Embedded/Local?
│  └─ Yes → SQLite
│
└─ Default → PostgreSQL (most versatile)
```

---

## Multi-Database Architectures

### When to Use Multiple Databases

**Polyglot persistence**: Using different databases for different parts of the system.

**Example architecture**:
```
PostgreSQL: Core business data (users, orders, products)
MongoDB: User-generated content (posts, comments, reviews)
Redis: Caching, sessions, rate limiting
Elasticsearch: Full-text search
S3: File storage (images, videos)
```

### Common Patterns

#### Pattern 1: Cache-Aside (PostgreSQL + Redis)

```python
def get_user(user_id):
    # Try cache first
    cached = redis.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)

    # Cache miss, query database
    user = db.query("SELECT * FROM users WHERE id = %s", [user_id])

    # Cache result
    redis.setex(f"user:{user_id}", 3600, json.dumps(user))
    return user
```

#### Pattern 2: Search Index (PostgreSQL + Elasticsearch)

```python
# Write to PostgreSQL
db.execute("INSERT INTO products (name, description) VALUES (%s, %s)", [name, desc])

# Async sync to Elasticsearch
elasticsearch.index(
    index="products",
    document={"name": name, "description": desc}
)

# Search via Elasticsearch
results = elasticsearch.search(
    index="products",
    query={"match": {"description": "laptop"}}
)
```

#### Pattern 3: Event Sourcing (PostgreSQL + MongoDB)

```python
# Write events to MongoDB (append-only log)
events.insert_one({
    "event_type": "order_placed",
    "order_id": 123,
    "user_id": 42,
    "timestamp": datetime.now()
})

# Aggregate to PostgreSQL (current state)
db.execute("UPDATE orders SET status = 'placed' WHERE id = 123")
```

---

## Migration Considerations

### SQL → SQL (PostgreSQL → MySQL)

**Difficulty**: Low to Medium

**Challenges**:
- Syntax differences (AUTO_INCREMENT vs SERIAL)
- Feature gaps (CTEs, window functions)
- Data type differences

**Tools**: pgloader, AWS DMS

### SQL → NoSQL (PostgreSQL → MongoDB)

**Difficulty**: High

**Challenges**:
- Schema redesign (normalization → denormalization)
- Relationship mapping (JOINs → embedded or references)
- Transaction changes (ACID → eventual consistency)

**Strategy**:
1. Identify access patterns
2. Denormalize for reads
3. Embed related data when accessed together
4. Reference when data is large or changes frequently

**Example**:
```sql
-- Before (PostgreSQL)
SELECT u.name, p.title, p.content
FROM users u
JOIN posts p ON p.user_id = u.id
WHERE u.id = 42;
```

```javascript
// After (MongoDB, embedded)
{
  "_id": ObjectId("..."),
  "title": "My Post",
  "content": "...",
  "author": {
    "name": "Alice"  // Embedded
  }
}
```

### NoSQL → SQL (MongoDB → PostgreSQL)

**Difficulty**: Medium

**Challenges**:
- Schema definition (flexible → fixed)
- Normalizing embedded data
- Relationship extraction

**Strategy**:
1. Analyze document structure
2. Extract entities (normalize)
3. Define relationships (foreign keys)
4. Add constraints and indexes

---

## Quick Reference Table

| Database | Type | Best For | Scaling | Consistency |
|----------|------|----------|---------|-------------|
| **PostgreSQL** | SQL | General-purpose, complex queries | Vertical + Read replicas | Strong |
| **MySQL** | SQL | Web apps, read-heavy | Vertical + Read replicas | Strong |
| **MongoDB** | Document | Flexible schema, hierarchical data | Horizontal (sharding) | Tunable |
| **Redis** | Key-value | Caching, sessions, real-time | Vertical + Clustering | Eventual |
| **DynamoDB** | Key-value | Serverless, AWS apps | Horizontal (auto) | Tunable |
| **SQLite** | SQL | Embedded, local apps | Single-user | Strong |
| **Elasticsearch** | Search | Full-text search | Horizontal | Eventual |
| **Cassandra** | Wide-column | High writes, time-series | Horizontal | Tunable |
| **ClickHouse** | Columnar | Analytics, OLAP | Horizontal | Eventual |

---

## Related Skills

- `postgres-schema-design.md` - Designing PostgreSQL schemas
- `mongodb-document-design.md` - Designing MongoDB documents
- `redis-data-structures.md` - Using Redis effectively
- `database-connection-pooling.md` - Optimizing database connections
- `postgres-query-optimization.md` - Optimizing PostgreSQL queries

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
