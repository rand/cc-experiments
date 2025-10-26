# Database Skills

Comprehensive skills for database design, optimization, and implementation across SQL, NoSQL, and in-memory databases.

## Category Overview

**Total Skills**: 8 core skills (+ 3 specialized data skills at root level)
**Focus**: PostgreSQL, MongoDB, Redis, query optimization, schema design, migrations, ORMs
**Use Cases**: Database architecture, performance tuning, data modeling, caching

## Skills in This Category

### postgres-schema-design.md
**Description**: Designing schemas, modeling relationships, choosing data types
**Lines**: ~320
**Use When**:
- Designing new database schemas
- Modeling entity relationships
- Choosing appropriate data types
- Deciding on normalization vs denormalization
- Planning indexes and constraints
- Designing for scalability

**Key Concepts**: Tables, columns, primary keys, foreign keys, constraints, normalization, indexes, data types

---

### postgres-query-optimization.md
**Description**: Debugging slow queries, analyzing EXPLAIN plans, designing indexes
**Lines**: ~350
**Use When**:
- Debugging slow queries
- Analyzing EXPLAIN and EXPLAIN ANALYZE output
- Designing and optimizing indexes
- Query plan analysis
- Performance tuning
- Identifying N+1 queries
- Table statistics and vacuuming

**Key Concepts**: EXPLAIN, EXPLAIN ANALYZE, indexes (B-tree, Hash, GiST, GIN), query plans, table scans, index scans, join strategies

---

### postgres-migrations.md
**Description**: Schema changes, zero-downtime deployments, rollback strategies
**Lines**: ~280
**Use When**:
- Planning schema changes
- Implementing zero-downtime migrations
- Handling data migrations
- Rolling back failed migrations
- Managing migration tools (Alembic, Flyway, migrate)
- Coordinating migrations with deployments

**Key Concepts**: DDL changes, data migrations, zero-downtime, rollback procedures, migration tools, backward compatibility

---

### mongodb-document-design.md
**Description**: MongoDB schemas, embedding vs referencing, document modeling
**Lines**: ~280
**Use When**:
- Designing MongoDB document structures
- Choosing between embedding and referencing
- Modeling one-to-many and many-to-many relationships
- Schema versioning in document databases
- Index design for documents
- Aggregation pipeline optimization

**Key Concepts**: Document modeling, embedding, referencing, subdocuments, arrays, schema flexibility, aggregation

---

### redis-data-structures.md
**Description**: Caching, sessions, rate limiting, leaderboards with Redis
**Lines**: ~270
**Use When**:
- Implementing caching layers
- Storing session data
- Implementing rate limiting
- Building leaderboards or counters
- Real-time analytics
- Pub/sub messaging
- Distributed locking

**Key Concepts**: Strings, hashes, lists, sets, sorted sets, TTL, expiration, persistence, pub/sub, transactions

---

### database-connection-pooling.md
**Description**: Configuring connection pools, debugging pool exhaustion
**Lines**: ~220
**Use When**:
- Configuring database connection pools
- Debugging "too many connections" errors
- Optimizing pool size for workload
- Implementing connection retry logic
- Managing connections in web applications
- Handling connection leaks

**Key Concepts**: Pool size, max connections, idle timeout, connection lifecycle, pooling libraries (HikariCP, pgBouncer, SQLAlchemy)

---

### orm-patterns.md
**Description**: ORM usage, N+1 prevention, eager loading, transactions
**Lines**: ~300
**Use When**:
- Using ORMs (SQLAlchemy, Prisma, Diesel, GORM)
- Preventing N+1 query problems
- Choosing between lazy and eager loading
- Managing transactions
- Deciding when to use raw SQL
- Migration generation with ORMs

**Key Concepts**: Active Record, Data Mapper, N+1 queries, eager loading, lazy loading, transactions, relationships, raw SQL

---

### database-selection.md
**Description**: Choosing databases, SQL vs NoSQL, architecture decisions
**Lines**: ~280
**Use When**:
- Starting new projects
- Evaluating database options
- Choosing between SQL and NoSQL
- Deciding on database architecture
- Selecting specialized databases (time-series, graph, search)
- Planning for scalability and growth

**Key Concepts**: SQL vs NoSQL, ACID, CAP theorem, consistency models, use case matching, polyglot persistence

---

## Related Root-Level Skills

These specialized database skills are at the root level:

- **redpanda-streaming.md** (390 lines) - Kafka-compatible streaming with Redpanda
- **apache-iceberg.md** (615 lines) - Table format, time travel, schema evolution
- **duckdb-analytics.md** (886 lines) - Embedded analytics database

```bash
cat skills/redpanda-streaming.md
cat skills/apache-iceberg.md
cat skills/duckdb-analytics.md
```

---

## Common Workflows

### New Database Project
**Goal**: Set up database for new application

**Sequence**:
1. `database-selection.md` - Choose database type
2. `postgres-schema-design.md` or `mongodb-document-design.md` - Design schema
3. `database-connection-pooling.md` - Configure connection pooling
4. `postgres-migrations.md` - Set up migration system

**Example**: E-commerce application with relational data

---

### Query Performance Debugging
**Goal**: Fix slow database queries

**Sequence**:
1. `postgres-query-optimization.md` - Analyze EXPLAIN plans
2. `database-connection-pooling.md` - Check pool configuration
3. `orm-patterns.md` - Fix N+1 queries if using ORM

**Example**: API endpoints timing out due to slow queries

---

### Schema Evolution
**Goal**: Safely change database schema in production

**Sequence**:
1. `postgres-schema-design.md` - Design schema changes
2. `postgres-migrations.md` - Plan and execute migrations
3. `postgres-query-optimization.md` - Verify query performance after changes

**Example**: Adding new features requiring schema changes

---

### Caching Layer Implementation
**Goal**: Add caching to improve performance

**Sequence**:
1. `redis-data-structures.md` - Choose appropriate Redis structures
2. Load caching skills via `discover-caching` gateway
3. `database-connection-pooling.md` - Optimize database connections

**Example**: Reducing database load with Redis cache

---

### ORM Integration
**Goal**: Integrate ORM into application

**Sequence**:
1. `orm-patterns.md` - Learn ORM best practices
2. `postgres-schema-design.md` - Design ORM-friendly schema
3. `database-connection-pooling.md` - Configure ORM connection pool
4. `postgres-migrations.md` - Use ORM migration tools

**Example**: Using SQLAlchemy with FastAPI or Prisma with Next.js

---

## Skill Combinations

### With API Skills (`discover-api`)
- Database-backed API endpoints
- Query optimization for API performance
- Connection pooling for API servers
- Transaction management for mutations
- Migrations alongside API versioning

**Common combos**:
- `rest-api-design.md` + `postgres-schema-design.md`
- `api-authentication.md` + `database-connection-pooling.md`
- `graphql-schema-design.md` + `postgres-query-optimization.md`

---

### With Backend Skills (`discover-backend`)
- Language-specific database drivers
- Async database operations
- Connection management
- Error handling

**Common combos**:
- Python: `postgres-schema-design.md` + SQLAlchemy patterns
- Zig: `postgres-schema-design.md` + libpq C bindings
- Rust: `postgres-schema-design.md` + SQLx or Diesel
- Go: `postgres-schema-design.md` + database/sql

---

### With Testing Skills (`discover-testing`)
- Integration tests with test databases
- Migration testing
- Query performance testing
- Data fixture management
- Test isolation and cleanup

**Common combos**:
- `integration-testing.md` + `postgres-migrations.md`
- `performance-testing.md` + `postgres-query-optimization.md`

---

### With Data Skills (`discover-data`)
- ETL from databases
- Database as data source
- Bulk data operations
- Streaming database changes (CDC)
- Data validation

**Common combos**:
- `etl-patterns.md` + `postgres-query-optimization.md`
- `stream-processing.md` + `redpanda-streaming.md`

---

### With Caching Skills (`discover-caching`)
- Multi-tier caching strategies
- Cache-aside patterns
- Write-through caching
- Cache invalidation
- Redis as cache backend

**Common combos**:
- `redis-data-structures.md` + `caching-fundamentals.md`
- `cache-invalidation-strategies.md` + `postgres-migrations.md`

---

## Quick Selection Guide

**Use PostgreSQL when**:
- Need ACID transactions
- Complex queries with JOINs
- Strong data consistency
- Relational data model fits well
- Mature ecosystem and tools

**Use MongoDB when**:
- Schema flexibility needed
- Rapid iteration and prototyping
- Nested/hierarchical data
- Horizontal scaling priority
- Document-oriented data model

**Use Redis when**:
- Speed is critical (in-memory)
- Caching layer needed
- Session storage
- Rate limiting
- Real-time features (leaderboards, counters)
- Pub/sub messaging

**Start with database-selection.md** if unsure:
```bash
cat skills/database/database-selection.md
```

---

## PostgreSQL Deep Dive

**Schema Design** → `postgres-schema-design.md`:
- Entity-relationship modeling
- Normalization (1NF, 2NF, 3NF, BCNF)
- Denormalization for performance
- Data types (integer, text, jsonb, arrays, enums)
- Constraints (NOT NULL, UNIQUE, CHECK, foreign keys)
- Index strategies (B-tree, GiST, GIN, BRIN)

**Query Optimization** → `postgres-query-optimization.md`:
- Reading EXPLAIN output
- Understanding query plans (Seq Scan, Index Scan, Bitmap Scan)
- Join strategies (Nested Loop, Hash Join, Merge Join)
- Index selection and creation
- Table statistics and ANALYZE
- Vacuuming and bloat management
- Query rewriting for performance

**Migrations** → `postgres-migrations.md`:
- Safe DDL patterns
- Adding columns (with/without defaults)
- Creating indexes concurrently
- Dropping columns safely
- Data backfills
- Zero-downtime techniques
- Rollback procedures
- Migration tools (Alembic, Flyway, golang-migrate)

---

## MongoDB Deep Dive

**Document Design** → `mongodb-document-design.md`:
- Embedding vs referencing decision tree
- One-to-many patterns (embed, reference, bucketing)
- Many-to-many patterns (two-way references, lookup)
- Schema versioning strategies
- Index design for queries
- Aggregation pipeline performance
- Sharding considerations

**When to embed**:
- Data is accessed together
- Data has one-to-few cardinality
- Data doesn't change frequently
- Document size stays under 16MB

**When to reference**:
- Large unbounded arrays
- Data accessed separately
- Data changes frequently
- Many-to-many relationships

---

## Redis Deep Dive

**Data Structures** → `redis-data-structures.md`:

**Strings**: Cache values, counters, flags
**Hashes**: Objects, user sessions, rate limit buckets
**Lists**: Queues, activity feeds, recent items
**Sets**: Unique items, tags, membership tests
**Sorted Sets**: Leaderboards, time-series, priority queues

**Common Patterns**:
- **Caching**: SET with TTL, cache-aside pattern
- **Sessions**: HASH per session, expire entire session
- **Rate Limiting**: INCR with EXPIRE, sliding window with sorted sets
- **Leaderboards**: ZADD for scores, ZRANGE for rankings
- **Pub/Sub**: PUBLISH/SUBSCRIBE for real-time messaging

---

## ORM Considerations

**Before using ORMs** → `orm-patterns.md`:

**Pros**:
- Productivity and developer experience
- Type safety
- Automatic migrations
- Cross-database compatibility

**Cons**:
- N+1 query problems
- Complex query generation
- Performance overhead
- Impedance mismatch

**Best Practices**:
- Use eager loading to prevent N+1
- Profile generated SQL
- Use raw SQL for complex queries
- Understand lazy vs eager loading
- Manage transactions explicitly
- Batch operations when possible

**Supported ORMs**:
- **SQLAlchemy** (Python) - Core + ORM, powerful, flexible
- **Prisma** (TypeScript) - Type-safe, modern, great DX
- **Diesel** (Rust) - Compile-time query checking
- **GORM** (Go) - Simple, idiomatic Go patterns
- **ActiveRecord** (Ruby) - Rails default, convention over configuration
- **Entity Framework** (C#) - .NET standard, LINQ integration

---

## Performance Optimization Checklist

**Schema Level**:
- [ ] Appropriate data types chosen
- [ ] Indexes on foreign keys
- [ ] Indexes on frequently queried columns
- [ ] Avoid over-indexing (write penalty)
- [ ] Partitioning for large tables

**Query Level**:
- [ ] EXPLAIN plans analyzed
- [ ] N+1 queries eliminated
- [ ] Eager loading used appropriately
- [ ] Joins optimized
- [ ] Subqueries avoided when possible
- [ ] Appropriate use of LIMIT/OFFSET

**Connection Level**:
- [ ] Connection pooling configured
- [ ] Pool size appropriate for workload
- [ ] Timeouts set correctly
- [ ] Connection leaks prevented
- [ ] Monitoring in place

**Application Level**:
- [ ] Caching implemented where appropriate
- [ ] Batch operations used for bulk data
- [ ] Transactions used correctly
- [ ] Query result pagination
- [ ] Prepared statements used

---

## Loading Skills

All skills are available in the `skills/database/` directory:

```bash
# PostgreSQL
cat skills/database/postgres-schema-design.md
cat skills/database/postgres-query-optimization.md
cat skills/database/postgres-migrations.md

# NoSQL
cat skills/database/mongodb-document-design.md
cat skills/database/redis-data-structures.md

# Cross-database
cat skills/database/database-connection-pooling.md
cat skills/database/orm-patterns.md
cat skills/database/database-selection.md
```

**Pro tip**: Start with `database-selection.md` for new projects, then load database-specific skills as needed.

---

**Related Categories**:
- `discover-api` - Building database-backed APIs
- `discover-backend` - Database drivers and integration
- `discover-testing` - Database testing strategies
- `discover-data` - ETL and data pipelines
- `discover-caching` - Caching strategies with Redis
- `discover-observability` - Database monitoring and metrics
