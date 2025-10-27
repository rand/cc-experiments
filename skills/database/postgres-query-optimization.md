---
name: database-postgres-query-optimization
description: Debugging slow queries in PostgreSQL
---



# PostgreSQL Query Optimization

**Scope**: Query analysis, EXPLAIN plans, index strategies, query rewriting
**Lines**: ~350
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Debugging slow queries in PostgreSQL
- Analyzing EXPLAIN ANALYZE output
- Designing index strategies
- Optimizing JOIN operations
- Investigating performance degradation
- Planning database capacity

## Core Concepts

### Query Execution Stages

1. **Parsing** - SQL syntax validation
2. **Planning** - Query optimizer creates execution plan
3. **Execution** - Plan executed, data retrieved
4. **Results** - Data returned to client

The planner's goal: find the lowest-cost plan.

### Cost Model

PostgreSQL uses a cost-based optimizer:
- **Startup cost**: Time before first row returned
- **Total cost**: Time to return all rows
- **Sequential scan cost**: Reading full table
- **Index scan cost**: Reading index + table lookups

```sql
-- Cost units are arbitrary (not milliseconds)
-- Lower cost = better plan (usually)
Seq Scan on users  (cost=0.00..1234.56 rows=10000 width=64)
Index Scan using idx_users_email  (cost=0.29..8.31 rows=1 width=64)
```

---

## Reading EXPLAIN ANALYZE Output

### Basic EXPLAIN

```sql
EXPLAIN SELECT * FROM users WHERE email = 'user@example.com';
```

Output shows the **planned** execution (no actual execution).

### EXPLAIN ANALYZE

```sql
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'user@example.com';
```

Output shows **planned + actual** execution with real timing.

**CRITICAL**: EXPLAIN ANALYZE actually runs the query (including writes!). Use with caution on production.

### Key Metrics to Watch

```
Seq Scan on users  (cost=0.00..1234.56 rows=10000 width=64) (actual time=0.012..12.345 rows=1 loops=1)
                    ^^^^^^^^^^^^^^^^^^^^                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                    PLANNED cost/rows                          ACTUAL time/rows/loops
```

**Red flags**:
- `actual rows >> estimated rows` - Statistics out of date
- `actual time >> expected` - I/O bottleneck or missing index
- `Seq Scan` on large tables - Usually needs index
- `loops > 1` on expensive operations - Nested loop inefficiency

---

## Scan Types

### Sequential Scan

```
Seq Scan on orders  (cost=0.00..15234.56 rows=500000 width=128)
```

**When it happens**:
- No usable index
- Table too small (faster to scan than use index)
- Query reads >5-10% of table (index overhead not worth it)

**Good for**:
- Small tables (<1000 rows typically)
- Reading most/all of table
- Analytics queries on warehouses

**Bad for**:
- Large tables with selective filters
- OLTP lookups
- Real-time queries

### Index Scan

```
Index Scan using idx_orders_user_id on orders  (cost=0.42..8.44 rows=1 width=128)
  Index Cond: (user_id = 12345)
```

**How it works**:
1. Traverse B-tree index to find entries
2. Fetch heap tuples (actual table rows) via pointers
3. Return results

**Good for**:
- Selective queries (<5% of rows)
- Equality comparisons (`=`, `IN`)
- Range scans on indexed columns
- ORDER BY on indexed columns

**Cost factors**:
- Random I/O to fetch heap tuples (expensive)
- Multiple index lookups if fetching many rows

### Index Only Scan

```
Index Only Scan using idx_orders_user_created on orders  (cost=0.42..4.44 rows=1 width=8)
  Index Cond: (user_id = 12345)
  Heap Fetches: 0
```

**How it works**:
1. Traverse index
2. Return data DIRECTLY from index (no heap lookup)
3. Check visibility map to verify row visibility

**Requirements**:
- All query columns in index (covering index)
- Table must be vacuumed (visibility map current)

**BEST PERFORMANCE**: No random I/O to heap.

```sql
-- Create covering index for this query
CREATE INDEX idx_orders_user_created ON orders(user_id) INCLUDE (created_at);

-- Query can now use Index Only Scan
SELECT created_at FROM orders WHERE user_id = 12345;
```

### Bitmap Index Scan

```
Bitmap Heap Scan on orders  (cost=123.45..5678.90 rows=5000 width=128)
  Recheck Cond: (status = 'pending' OR status = 'processing')
  ->  BitmapOr  (cost=123.45..123.45 rows=5000 width=0)
        ->  Bitmap Index Scan on idx_orders_status  (cost=0.00..61.00 rows=2500 width=0)
              Index Cond: (status = 'pending')
        ->  Bitmap Index Scan on idx_orders_status  (cost=0.00..61.00 rows=2500 width=0)
              Index Cond: (status = 'processing')
```

**How it works**:
1. Build in-memory bitmap of matching rows
2. Combine bitmaps (OR, AND operations)
3. Sort row locations
4. Fetch heap tuples in sequential order (reduces random I/O)

**Good for**:
- Combining multiple indexes (`OR` conditions)
- Fetching moderate number of rows (5-25% of table)
- Reducing random I/O

**Better than**:
- Multiple Index Scans → merge results
- Full Seq Scan when filtered set is small enough

---

## Index Strategies

### Index Types

#### B-tree (Default, 95% of use cases)

```sql
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_orders_composite ON orders(user_id, created_at);
```

**Good for**:
- Equality: `email = 'foo@example.com'`
- Range: `created_at > '2024-01-01'`
- Sorting: `ORDER BY created_at`
- Prefix matching: `email LIKE 'foo%'` (NOT `LIKE '%foo'`)

**Multi-column indexes** (composite):
- Order matters: `(user_id, created_at)` can be used for:
  - `user_id = X`
  - `user_id = X AND created_at > Y`
  - NOT efficient for `created_at > Y` alone

#### Hash (Rare, equality only)

```sql
CREATE INDEX idx_users_email_hash ON users USING HASH (email);
```

**Good for**:
- Equality ONLY: `email = 'foo@example.com'`
- Slightly smaller than B-tree

**Cannot**:
- Range queries
- Sorting
- Prefix matching

**Usually not needed** - B-tree handles equality well.

#### GiST (Geometric/Full-text)

```sql
CREATE INDEX idx_locations_geom ON locations USING GIST (geom);
CREATE INDEX idx_documents_fts ON documents USING GIST (to_tsvector('english', content));
```

**Good for**:
- Geometric data (PostGIS)
- Full-text search
- Range types
- Custom data types

#### GIN (Full-text, JSONB, arrays)

```sql
CREATE INDEX idx_documents_fts ON documents USING GIN (to_tsvector('english', content));
CREATE INDEX idx_users_tags ON users USING GIN (tags); -- array column
CREATE INDEX idx_metadata_json ON events USING GIN (metadata); -- jsonb column
```

**Good for**:
- Full-text search (faster than GiST for static data)
- JSONB queries: `metadata @> '{"status": "active"}'`
- Array containment: `tags @> ARRAY['postgres']`

**Trade-offs**:
- Larger than GiST
- Slower writes
- Faster reads for containment queries

#### BRIN (Block Range Index)

```sql
CREATE INDEX idx_logs_created_brin ON logs USING BRIN (created_at);
```

**Good for**:
- Very large tables with natural clustering (e.g., time-series)
- Append-only data
- Low-selectivity queries acceptable

**Extremely small index** (1000x smaller than B-tree).

**Trade-off**: Less precise, may scan extra blocks.

---

### Index Selection Decision Tree

```
Start: Do I need an index?
│
├─ Table < 1000 rows? → NO (Seq Scan is fine)
├─ Query reads >10% of table? → MAYBE (test both)
└─ Query is selective? → YES
   │
   ├─ What type of query?
   │  ├─ Equality (=, IN) → B-tree
   │  ├─ Range (<, >, BETWEEN) → B-tree
   │  ├─ Sorting (ORDER BY) → B-tree on sort columns
   │  ├─ Full-text search → GIN or GiST
   │  ├─ JSONB queries → GIN
   │  ├─ Geometric queries → GiST
   │  ├─ Time-series append-only → BRIN
   │  └─ Array containment → GIN
   │
   ├─ Multiple columns in WHERE?
   │  ├─ Always used together → Composite index (user_id, created_at)
   │  ├─ Used independently → Separate indexes (or partial indexes)
   │  └─ OR conditions → Bitmap scan or separate indexes
   │
   └─ Can I cover the query? → Add INCLUDE columns for Index Only Scan
```

---

## Common Query Anti-Patterns

### 1. N+1 Query Problem

```sql
-- Anti-pattern: Load users, then loop and query orders for each
SELECT * FROM users;
-- In application loop:
--   SELECT * FROM orders WHERE user_id = ?

-- Solution: JOIN or batch query
SELECT u.*, o.*
FROM users u
LEFT JOIN orders o ON o.user_id = u.id;
```

### 2. SELECT * Instead of Specific Columns

```sql
-- Anti-pattern
SELECT * FROM orders WHERE user_id = 123;

-- Better: Select only needed columns
SELECT id, total, created_at FROM orders WHERE user_id = 123;
```

**Why it matters**:
- Enables Index Only Scans (covering indexes)
- Reduces network transfer
- Lower memory usage

### 3. Non-Sargable Queries (Can't Use Index)

```sql
-- Anti-pattern: Function on indexed column
SELECT * FROM users WHERE LOWER(email) = 'foo@example.com';

-- Solution: Functional index
CREATE INDEX idx_users_email_lower ON users(LOWER(email));
-- Or store email in lowercase always
```

```sql
-- Anti-pattern: Wildcard at start
SELECT * FROM users WHERE email LIKE '%@example.com';

-- Solution: Full-text search or trigram index
CREATE EXTENSION pg_trgm;
CREATE INDEX idx_users_email_trgm ON users USING GIN (email gin_trgm_ops);
```

### 4. Unnecessary DISTINCT

```sql
-- Anti-pattern: DISTINCT when not needed
SELECT DISTINCT user_id FROM orders WHERE status = 'pending';

-- Better if user_id is already unique per status:
SELECT user_id FROM orders WHERE status = 'pending';
```

### 5. OR Conditions Across Tables

```sql
-- Anti-pattern: OR across tables
SELECT * FROM orders WHERE user_id = 123 OR vendor_id = 456;

-- Better: UNION
SELECT * FROM orders WHERE user_id = 123
UNION
SELECT * FROM orders WHERE vendor_id = 456;
```

---

## Query Rewriting Patterns

### Pattern 1: Subquery → JOIN

```sql
-- Slower: Correlated subquery
SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > 100);

-- Faster: JOIN with DISTINCT
SELECT DISTINCT u.* FROM users u INNER JOIN orders o ON o.user_id = u.id WHERE o.total > 100;

-- Or EXISTS (often better for large datasets)
SELECT * FROM users u WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id AND o.total > 100);
```

### Pattern 2: JOIN → Semi-Join (EXISTS)

```sql
-- When you only need to check existence:
SELECT * FROM users u WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id);

-- NOT:
SELECT DISTINCT u.* FROM users u INNER JOIN orders o ON o.user_id = u.id;
```

**EXISTS is faster** when you don't need order data, just existence check.

### Pattern 3: Partial Index for Filtered Queries

```sql
-- Common query:
SELECT * FROM orders WHERE status = 'pending';

-- Create partial index
CREATE INDEX idx_orders_pending ON orders(created_at) WHERE status = 'pending';
```

**Benefits**:
- Smaller index (only pending orders)
- Faster writes (only updated when status = pending)
- Perfect for skewed data (e.g., 1% pending, 99% completed)

### Pattern 4: Materialized View for Complex Aggregations

```sql
-- Slow query run frequently:
SELECT user_id, COUNT(*), SUM(total) FROM orders GROUP BY user_id;

-- Create materialized view
CREATE MATERIALIZED VIEW user_order_stats AS
SELECT user_id, COUNT(*) as order_count, SUM(total) as total_spent
FROM orders
GROUP BY user_id;

CREATE UNIQUE INDEX idx_user_order_stats_user ON user_order_stats(user_id);

-- Refresh periodically
REFRESH MATERIALIZED VIEW CONCURRENTLY user_order_stats;
```

---

## Index Maintenance

### Statistics

PostgreSQL uses table statistics to estimate row counts and plan queries.

```sql
-- Outdated statistics cause bad plans
-- Fix: Analyze the table
ANALYZE users;
ANALYZE orders;

-- Auto-vacuum should handle this, but manual ANALYZE helps after bulk changes
```

### Reindexing

Indexes can become bloated over time.

```sql
-- Check index bloat
SELECT schemaname, tablename, indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;

-- Rebuild index
REINDEX INDEX idx_users_email;
REINDEX TABLE users; -- All indexes on table

-- Or recreate index (allows CONCURRENTLY, less locking)
CREATE INDEX CONCURRENTLY idx_users_email_new ON users(email);
DROP INDEX CONCURRENTLY idx_users_email;
ALTER INDEX idx_users_email_new RENAME TO idx_users_email;
```

### Monitoring Index Usage

```sql
-- Find unused indexes
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- Drop unused indexes to improve write performance
DROP INDEX idx_never_used;
```

---

## Optimization Workflow

### Step 1: Identify Slow Query

```sql
-- Enable slow query logging in postgresql.conf
log_min_duration_statement = 1000  -- Log queries > 1 second

-- Or use pg_stat_statements extension
CREATE EXTENSION pg_stat_statements;

SELECT query, calls, total_exec_time, mean_exec_time, rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Step 2: Analyze with EXPLAIN ANALYZE

```sql
EXPLAIN ANALYZE <your slow query>;
```

Look for:
- Seq Scan on large tables
- Nested Loop with high actual rows
- Hash Join with large temp spills
- Sort operations with large work_mem usage

### Step 3: Check Statistics

```sql
-- When was table last analyzed?
SELECT schemaname, tablename, last_analyze, last_autoanalyze
FROM pg_stat_user_tables
WHERE tablename = 'orders';

-- If stale, analyze
ANALYZE orders;
```

### Step 4: Add/Modify Index

```sql
-- Based on WHERE, JOIN, ORDER BY clauses
CREATE INDEX idx_orders_user_created ON orders(user_id, created_at);
```

### Step 5: Re-run EXPLAIN ANALYZE

```sql
EXPLAIN ANALYZE <your slow query>;
```

Compare before/after:
- Total cost reduced?
- Seq Scan → Index Scan?
- Actual time improved?

### Step 6: Test in Production-like Data Volume

**CRITICAL**: Optimizer chooses plans based on table size.

- 1K rows → Seq Scan might be optimal
- 1M rows → Index Scan needed

Test with realistic data volume.

---

## Quick Reference

### EXPLAIN Options

```sql
EXPLAIN SELECT ...;                    -- Plan only, no execution
EXPLAIN ANALYZE SELECT ...;            -- Plan + actual execution
EXPLAIN (ANALYZE, BUFFERS) SELECT ...; -- Include I/O stats
EXPLAIN (ANALYZE, BUFFERS, VERBOSE) SELECT ...; -- Full details
```

### Index Syntax

```sql
-- B-tree (default)
CREATE INDEX idx_name ON table(column);

-- Composite
CREATE INDEX idx_name ON table(col1, col2);

-- Covering (Index Only Scan)
CREATE INDEX idx_name ON table(col1) INCLUDE (col2, col3);

-- Partial
CREATE INDEX idx_name ON table(col) WHERE condition;

-- Functional
CREATE INDEX idx_name ON table(LOWER(email));

-- Concurrent (no table lock)
CREATE INDEX CONCURRENTLY idx_name ON table(column);

-- Other types
CREATE INDEX idx_name ON table USING HASH (column);
CREATE INDEX idx_name ON table USING GIN (jsonb_column);
CREATE INDEX idx_name ON table USING GIST (geometry_column);
CREATE INDEX idx_name ON table USING BRIN (timestamp_column);
```

### Optimization Checklist

```
Query Performance Issues:
[ ] Run EXPLAIN ANALYZE to see actual execution
[ ] Check for Seq Scan on large tables
[ ] Verify statistics are current (ANALYZE table)
[ ] Look for missing indexes on WHERE/JOIN columns
[ ] Check if index is being used (Index Cond vs Filter)
[ ] Consider composite index for multi-column queries
[ ] Use covering index (INCLUDE) for Index Only Scan
[ ] Check for N+1 queries (use JOIN or batch)
[ ] Verify query is sargable (no functions on indexed columns)
[ ] Consider partial index for filtered queries
[ ] Test with production-like data volume
[ ] Monitor index usage (drop unused indexes)
```

---

## Level 3 Resources

This skill includes Level 3 Resources (executable tools, reference materials, examples):

### Reference Materials
- **[REFERENCE.md](./postgres-query-optimization/resources/REFERENCE.md)** - Deep dive into EXPLAIN output, query planner internals, all index types, and optimization patterns

### Executable Scripts
Located in `./postgres-query-optimization/resources/scripts/`:

- **analyze_query.py** - Parses EXPLAIN ANALYZE output, detects issues (seq scans, stale statistics, inefficient filters), suggests optimizations
- **suggest_indexes.py** - Recommends indexes based on query patterns (WHERE, JOIN, ORDER BY), supports covering indexes and workload analysis
- **benchmark_queries.sh** - Benchmarks query performance with statistical analysis, compares before/after optimization

See [scripts/README.md](./postgres-query-optimization/resources/scripts/README.md) for usage examples.

### Examples
- **slow-queries/** - Real-world slow query examples with fixes (N+1 problem, missing indexes, non-sargable queries)
- **docker/** - Pre-configured PostgreSQL test environment with sample data (10K users, 100K orders, 500K events)

**Quick Start**:
```bash
# Analyze EXPLAIN output
python postgres-query-optimization/resources/scripts/analyze_query.py --explain-file explain.txt

# Get index recommendations
python postgres-query-optimization/resources/scripts/suggest_indexes.py --query "SELECT * FROM orders WHERE user_id = 123"

# Benchmark query
./postgres-query-optimization/resources/scripts/benchmark_queries.sh --query "SELECT ..." --iterations 20

# Start test environment
cd postgres-query-optimization/resources/examples/docker && docker-compose up -d
```

---

## Related Skills

- `postgres-migrations.md` - Safe schema changes, adding indexes without downtime
- `postgres-schema-design.md` - Table design affects query performance
- `orm-patterns.md` - ORM-specific N+1 prevention, eager loading
- `database-connection-pooling.md` - Connection limits affect query concurrency
- `database-selection.md` - When to use Postgres vs other databases

---

## Common Pitfalls

❌ **Running EXPLAIN ANALYZE on writes in production** - It executes the query (including DELETE!)
✅ Use EXPLAIN (no ANALYZE) for writes, or test on staging

❌ **Creating too many indexes** - Slows down writes, wastes space
✅ Monitor index usage, drop unused indexes

❌ **Ignoring statistics** - Planner makes bad decisions with stale stats
✅ Run ANALYZE after bulk changes, ensure auto-vacuum is working

❌ **Not testing with realistic data volume** - Plans change with table size
✅ Test on production-like dataset

❌ **Using DISTINCT when not needed** - Adds expensive sort/dedup
✅ Only use when actually needed

❌ **Assuming index always helps** - Small tables are faster with Seq Scan
✅ Test before/after, trust the planner for small tables

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
