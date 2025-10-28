# PostgreSQL Query Optimization Reference

**Scope**: Deep dive into EXPLAIN, query planner internals, index types, and optimization patterns
**Lines**: ~300
**Last Updated**: 2025-10-27

## Table of Contents

1. [EXPLAIN Output Deep Dive](#explain-output-deep-dive)
2. [Scan Types Reference](#scan-types-reference)
3. [Index Types Deep Dive](#index-types-deep-dive)
4. [Query Planner Internals](#query-planner-internals)
5. [Statistics and ANALYZE](#statistics-and-analyze)
6. [Common Optimization Patterns](#common-optimization-patterns)
7. [Anti-Patterns and Fixes](#anti-patterns-and-fixes)

---

## EXPLAIN Output Deep Dive

### EXPLAIN Format Options

```sql
-- Text format (default)
EXPLAIN SELECT * FROM users;

-- JSON format (machine-readable)
EXPLAIN (FORMAT JSON) SELECT * FROM users;

-- YAML format
EXPLAIN (FORMAT YAML) SELECT * FROM users;

-- XML format
EXPLAIN (FORMAT XML) SELECT * FROM users;
```

### EXPLAIN Options

```sql
-- ANALYZE: Actually execute the query, show real timing
EXPLAIN (ANALYZE) SELECT * FROM users;

-- BUFFERS: Show buffer cache hit/miss statistics
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM users;

-- VERBOSE: Show output column list for each node
EXPLAIN (VERBOSE) SELECT * FROM users;

-- COSTS: Show startup/total cost (default ON)
EXPLAIN (COSTS OFF) SELECT * FROM users;

-- TIMING: Show actual timing per node (default ON with ANALYZE)
EXPLAIN (ANALYZE, TIMING OFF) SELECT * FROM users;

-- SUMMARY: Show planning/execution time summary (default ON with ANALYZE)
EXPLAIN (ANALYZE, SUMMARY) SELECT * FROM users;

-- WAL: Show WAL generation stats (PG 13+)
EXPLAIN (ANALYZE, WAL) INSERT INTO users VALUES (...);
```

### Reading EXPLAIN Output

```
Seq Scan on users  (cost=0.00..1234.56 rows=10000 width=64) (actual time=0.012..12.345 rows=9998 loops=1)
  Filter: (status = 'active')
  Rows Removed by Filter: 2
Planning Time: 0.123 ms
Execution Time: 12.456 ms
```

**Field Breakdown**:

- **cost=0.00..1234.56**: Startup cost..Total cost (arbitrary units)
  - Startup cost: Time before first row returned
  - Total cost: Time to return all rows
  - Units are NOT milliseconds (relative comparison only)

- **rows=10000**: Estimated number of rows returned

- **width=64**: Estimated average row size in bytes

- **actual time=0.012..12.345**: Actual startup time..total time (milliseconds)

- **rows=9998**: Actual number of rows returned

- **loops=1**: How many times this node executed
  - loops>1 indicates nested loop iteration
  - Multiply actual time by loops for total time

- **Filter**: Post-scan filtering applied

- **Rows Removed by Filter**: Rows scanned but filtered out

- **Planning Time**: Time spent planning query

- **Execution Time**: Time spent executing query

### Cost Calculation

PostgreSQL uses cost units based on configuration parameters:

```sql
-- Show cost parameters
SHOW seq_page_cost;      -- Default: 1.0
SHOW random_page_cost;   -- Default: 4.0
SHOW cpu_tuple_cost;     -- Default: 0.01
SHOW cpu_index_tuple_cost; -- Default: 0.005
SHOW cpu_operator_cost;  -- Default: 0.0025
```

**Sequential Scan Cost**:
```
cost = (pages_read * seq_page_cost) + (rows * cpu_tuple_cost)
```

**Index Scan Cost**:
```
cost = (index_pages * random_page_cost) +
       (heap_pages * random_page_cost) +
       (rows * cpu_index_tuple_cost)
```

**Why random_page_cost > seq_page_cost**:
- Random I/O requires disk seeks (slow)
- Sequential I/O reads contiguous blocks (fast)
- SSD users often set random_page_cost=1.1 (less penalty)

---

## Scan Types Reference

### Sequential Scan

```
Seq Scan on orders  (cost=0.00..15234.56 rows=500000 width=128)
  Filter: (status = 'pending')
```

**Mechanics**:
1. Read all pages from disk sequentially
2. Check each row against filter conditions
3. Return matching rows

**When Chosen**:
- No usable index exists
- Query accesses >5-10% of table (index overhead not worth it)
- Table is small (<1000 rows typically)
- Cost estimate shows Seq Scan is cheaper

**Performance Characteristics**:
- Good sequential I/O
- Predictable read-ahead by OS
- CPU-bound for large tables
- All rows scanned, even if only 1 matches

### Index Scan

```
Index Scan using idx_orders_user_id on orders  (cost=0.42..8.44 rows=1 width=128)
  Index Cond: (user_id = 12345)
  Filter: (status = 'pending')
```

**Mechanics**:
1. Traverse B-tree index to find matching entries
2. For each index entry, fetch heap tuple via TID (tuple identifier)
3. Apply any additional filters
4. Return matching rows

**Index Cond vs Filter**:
- **Index Cond**: Conditions used to traverse index (efficient)
- **Filter**: Conditions applied after fetching heap tuple (less efficient)

**Performance Characteristics**:
- Random I/O to fetch heap tuples (expensive)
- Good for highly selective queries (<5% of rows)
- Bad for fetching many rows (random I/O overhead)

**Direction**:
```
Index Scan Backward using idx_orders_created on orders
```
- B-tree indexes can be scanned backward for `ORDER BY ... DESC`

### Index Only Scan

```
Index Only Scan using idx_orders_user_created on orders  (cost=0.42..4.44 rows=1 width=8)
  Index Cond: (user_id = 12345)
  Heap Fetches: 0
```

**Mechanics**:
1. Traverse B-tree index
2. Check visibility map to see if heap tuple is visible
3. If visible, return data directly from index (no heap fetch)
4. If not visible, fetch heap tuple for visibility check

**Requirements**:
- All query columns must be in index (covering index)
- Table must be vacuumed (visibility map current)

**Heap Fetches**:
- `Heap Fetches: 0` - Perfect, all data from index
- `Heap Fetches: 1234` - Some rows needed visibility check

**Best Performance**: No random I/O to heap.

### Bitmap Index Scan + Bitmap Heap Scan

```
Bitmap Heap Scan on orders  (cost=123.45..5678.90 rows=5000 width=128)
  Recheck Cond: (status = 'pending' OR status = 'processing')
  Heap Blocks: exact=1234
  ->  BitmapOr  (cost=123.45..123.45 rows=5000 width=0)
        ->  Bitmap Index Scan on idx_orders_status  (cost=0.00..61.00 rows=2500 width=0)
              Index Cond: (status = 'pending')
        ->  Bitmap Index Scan on idx_orders_status  (cost=0.00..61.00 rows=2500 width=0)
              Index Cond: (status = 'processing')
```

**Mechanics**:
1. **Bitmap Index Scan**: Scan index, build in-memory bitmap of matching TIDs
2. **BitmapOr/BitmapAnd**: Combine multiple bitmaps using boolean operations
3. **Bitmap Heap Scan**: Sort TIDs, fetch heap tuples in sequential order

**Why Sequential Order**:
- Reduces random I/O by fetching nearby rows together
- Better cache locality
- Predictable I/O pattern

**Recheck Cond**:
- If bitmap doesn't fit in `work_mem`, it becomes lossy (page-level, not row-level)
- "Recheck Cond" means rows must be rechecked after heap fetch

**Good For**:
- Combining multiple indexes (OR/AND conditions)
- Fetching moderate number of rows (5-25% of table)
- Queries that benefit from sorted heap access

---

## Index Types Deep Dive

### B-tree Index (Default)

**Structure**:
- Balanced tree with sorted keys
- Internal nodes contain keys + pointers
- Leaf nodes contain keys + TIDs (tuple identifiers)
- All leaf nodes at same depth (balanced)

**Properties**:
- Supports: `<`, `<=`, `=`, `>=`, `>`, `BETWEEN`, `IN`, `IS NULL`, `IS NOT NULL`
- Supports: `LIKE 'foo%'` (prefix matching)
- Supports: `ORDER BY` (forward and backward scan)
- Does NOT support: `LIKE '%foo'` (suffix matching)

**Multi-Column Indexes**:
```sql
CREATE INDEX idx_orders_user_created ON orders(user_id, created_at);
```

**Ordering Rules**:
- Can use index for: `user_id = X`
- Can use index for: `user_id = X AND created_at > Y`
- Can use index for: `user_id = X AND created_at = Y AND status = Z` (if 3 columns)
- **Cannot** efficiently use for: `created_at > Y` alone (without user_id)

**Column Order Matters**:
```sql
-- Index on (a, b, c)
-- Usable for:
WHERE a = 1                          -- YES
WHERE a = 1 AND b = 2                -- YES
WHERE a = 1 AND b = 2 AND c = 3      -- YES
WHERE a = 1 AND c = 3                -- PARTIAL (only a used)
WHERE b = 2                          -- NO
WHERE c = 3                          -- NO
```

**Covering Indexes (INCLUDE)**:
```sql
-- PostgreSQL 11+
CREATE INDEX idx_orders_user_created ON orders(user_id, created_at) INCLUDE (status, total);
```
- Indexed columns: `user_id, created_at` (can be used in WHERE, ORDER BY)
- Included columns: `status, total` (stored in index for Index Only Scan, not searchable)

### Hash Index

**Structure**:
- Hash table mapping hash(key) → TID
- Not ordered
- Smaller than B-tree

**Properties**:
- Supports: `=` only
- Does NOT support: `<`, `>`, `LIKE`, `ORDER BY`
- Slightly faster than B-tree for equality (marginal)
- Not WAL-logged before PG 10 (unsafe for replication)

**When to Use**:
- Rarely needed (B-tree handles equality well)
- Extremely large keys where hash is smaller
- Equality-only queries with no sorting

```sql
CREATE INDEX idx_users_uuid_hash ON users USING HASH (uuid);
```

### GiST Index (Generalized Search Tree)

**Structure**:
- Balanced tree (like B-tree)
- Supports custom data types via operator classes
- Lossy (may return false positives, requires recheck)

**Use Cases**:
- Geometric data (PostGIS): `ST_Contains`, `ST_Intersects`
- Full-text search: `@@` operator
- Range types: `int4range`, `tstzrange`
- Custom data types

**Example**:
```sql
-- Geometric index
CREATE INDEX idx_locations_geom ON locations USING GIST (geom);

-- Full-text search
CREATE INDEX idx_documents_fts ON documents USING GIST (to_tsvector('english', content));

-- Range types
CREATE INDEX idx_events_period ON events USING GIST (period);
```

**Performance**:
- Slower inserts than B-tree (more complex structure)
- Good for complex queries (geometric, full-text)
- May require recheck (lossy compression)

### GIN Index (Generalized Inverted Index)

**Structure**:
- Inverted index: maps values → TIDs
- Optimized for cases where single key appears in many rows
- Larger than GiST (stores all values)

**Use Cases**:
- Full-text search (faster than GiST for static data)
- JSONB queries: `@>`, `@?`, `@@`
- Array queries: `@>`, `<@`, `&&`
- tsvector queries

**Example**:
```sql
-- JSONB index
CREATE INDEX idx_events_metadata ON events USING GIN (metadata);
-- Query: WHERE metadata @> '{"user_id": 123}'

-- Array index
CREATE INDEX idx_users_tags ON users USING GIN (tags);
-- Query: WHERE tags @> ARRAY['postgres', 'performance']

-- Full-text search
CREATE INDEX idx_documents_fts ON documents USING GIN (to_tsvector('english', content));
-- Query: WHERE to_tsvector('english', content) @@ to_tsquery('postgres & performance')
```

**GIN vs GiST**:
- **GIN**: Larger index, faster lookups, slower inserts
- **GiST**: Smaller index, slower lookups, faster inserts
- Use **GIN** for mostly-read data (full-text search, static JSONB)
- Use **GiST** for frequently-updated data

### BRIN Index (Block Range Index)

**Structure**:
- Stores min/max values for ranges of pages (blocks)
- Extremely small (1000x smaller than B-tree)
- Lossy (may scan extra pages)

**How It Works**:
```
Table Pages: [1-128] [129-256] [257-384] ...
BRIN Entry:  min=1    min=500   min=1000
             max=499  max=999   max=1500
```

**Use Cases**:
- Very large tables (>1GB)
- Natural clustering (e.g., time-series data, append-only logs)
- WHERE queries on clustered column
- Acceptable to scan extra pages

**Example**:
```sql
-- Time-series data
CREATE INDEX idx_logs_created_brin ON logs USING BRIN (created_at);
-- Query: WHERE created_at > '2025-01-01'
```

**Trade-offs**:
- **Pros**: Tiny index size, minimal write overhead
- **Cons**: Less precise, may scan irrelevant pages

**When to Use**:
- Table is huge and naturally ordered by indexed column
- Column has good correlation with physical order
- Query selectivity is acceptable even with extra scans

---

## Query Planner Internals

### Planning Process

1. **Parsing**: SQL → Parse tree
2. **Rewriting**: Apply rules, views, etc.
3. **Planning**: Generate optimal execution plan
4. **Execution**: Execute plan, return results

### Planner Statistics

Planner relies on statistics to estimate costs:

```sql
-- Check statistics for a table
SELECT * FROM pg_stats WHERE tablename = 'users';
```

**Key Statistics**:
- `n_distinct`: Estimated distinct values in column
- `most_common_vals`: Most frequent values
- `most_common_freqs`: Frequencies of most common values
- `histogram_bounds`: Value distribution histogram
- `correlation`: Physical order correlation (-1 to 1)

**Correlation**:
- `1.0`: Perfect correlation (values match physical order)
- `0.0`: No correlation (random order)
- `-1.0`: Perfect inverse correlation

High correlation → Index Scan is cheaper (sequential I/O)
Low correlation → Index Scan is expensive (random I/O)

### Configuration Parameters

```sql
-- Cost parameters
SET seq_page_cost = 1.0;         -- Sequential page read cost
SET random_page_cost = 4.0;      -- Random page read cost (1.1 for SSD)
SET cpu_tuple_cost = 0.01;       -- Cost to process one row
SET cpu_index_tuple_cost = 0.005; -- Cost to process one index entry
SET cpu_operator_cost = 0.0025;  -- Cost to execute an operator

-- Memory parameters
SET work_mem = '16MB';           -- Memory for sorts, hashes (per operation)
SET shared_buffers = '256MB';    -- Shared buffer cache
SET effective_cache_size = '4GB'; -- OS cache size (for planning)

-- Planner settings
SET enable_seqscan = on;         -- Allow sequential scans
SET enable_indexscan = on;       -- Allow index scans
SET enable_bitmapscan = on;      -- Allow bitmap scans
SET enable_hashjoin = on;        -- Allow hash joins
SET enable_nestloop = on;        -- Allow nested loop joins
SET enable_mergejoin = on;       -- Allow merge joins
```

**Tuning for SSD**:
```sql
-- Random I/O is much cheaper on SSD
SET random_page_cost = 1.1;  -- Down from 4.0
```

### Join Algorithms

#### Nested Loop Join

```
Nested Loop  (cost=0.42..1234.56 rows=100 width=128)
  ->  Seq Scan on users  (cost=0.00..10.00 rows=10 width=64)
  ->  Index Scan using idx_orders_user_id on orders  (cost=0.42..122.45 rows=10 width=64)
        Index Cond: (user_id = users.id)
```

**How It Works**:
- For each row in outer table (users)
- Scan inner table (orders) for matches

**Good For**:
- Small outer table
- Inner table has index on join key
- Selective join condition

**Bad For**:
- Large outer table (becomes O(N*M))

#### Hash Join

```
Hash Join  (cost=123.45..5678.90 rows=10000 width=128)
  Hash Cond: (orders.user_id = users.id)
  ->  Seq Scan on orders  (cost=0.00..4567.89 rows=100000 width=64)
  ->  Hash  (cost=100.00..100.00 rows=1000 width=64)
        ->  Seq Scan on users  (cost=0.00..100.00 rows=1000 width=64)
```

**How It Works**:
1. Build hash table from smaller table (users)
2. Scan larger table (orders), probe hash table for matches

**Good For**:
- Large tables without suitable indexes
- Equality joins (`=`)

**Bad For**:
- Hash table doesn't fit in `work_mem` (spills to disk)
- Non-equality joins

#### Merge Join

```
Merge Join  (cost=1234.56..5678.90 rows=10000 width=128)
  Merge Cond: (orders.user_id = users.id)
  ->  Index Scan using idx_orders_user_id on orders  (cost=0.42..3456.78 rows=100000 width=64)
  ->  Index Scan using idx_users_id on users  (cost=0.42..1234.56 rows=10000 width=64)
```

**How It Works**:
1. Sort both tables by join key (or use existing indexes)
2. Merge sorted lists, matching rows

**Good For**:
- Both tables already sorted (via index)
- Large tables with good indexes

**Bad For**:
- Sorting required (expensive for large unsorted tables)

---

## Statistics and ANALYZE

### Running ANALYZE

```sql
-- Analyze specific table
ANALYZE users;

-- Analyze specific column
ANALYZE users (email);

-- Analyze all tables in database
ANALYZE;

-- Verbose output
ANALYZE VERBOSE users;
```

### Auto-Vacuum and Auto-Analyze

PostgreSQL automatically analyzes tables via autovacuum daemon:

```sql
-- Check autovacuum settings
SHOW autovacuum;
SHOW autovacuum_analyze_threshold;
SHOW autovacuum_analyze_scale_factor;

-- Check last analyze time
SELECT schemaname, tablename, last_analyze, last_autoanalyze, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables;
```

**When to Manual ANALYZE**:
- After bulk INSERT/UPDATE/DELETE
- After significant data distribution change
- When EXPLAIN shows wildly incorrect row estimates

### Statistics Target

Controls how many histogram bins and most-common-values to store:

```sql
-- Default: 100
-- Higher = more accurate statistics, slower ANALYZE
ALTER TABLE users ALTER COLUMN email SET STATISTICS 1000;

-- Analyze after changing statistics target
ANALYZE users;
```

---

## Common Optimization Patterns

### Pattern 1: Covering Index for Index Only Scan

```sql
-- Slow: Index Scan + heap fetches
CREATE INDEX idx_orders_user ON orders(user_id);
SELECT user_id, created_at FROM orders WHERE user_id = 123;

-- Fast: Index Only Scan
CREATE INDEX idx_orders_user_created ON orders(user_id) INCLUDE (created_at);
SELECT user_id, created_at FROM orders WHERE user_id = 123;
```

### Pattern 2: Partial Index for Skewed Data

```sql
-- Most orders are 'completed', few are 'pending'
-- Slow: Index on status (large, low selectivity)
CREATE INDEX idx_orders_status ON orders(status);

-- Fast: Partial index on pending only
CREATE INDEX idx_orders_pending ON orders(created_at) WHERE status = 'pending';

-- Query automatically uses partial index
SELECT * FROM orders WHERE status = 'pending' AND created_at > '2025-01-01';
```

### Pattern 3: Functional Index for Transformed Columns

```sql
-- Slow: Function on indexed column (can't use index)
SELECT * FROM users WHERE LOWER(email) = 'foo@example.com';

-- Fast: Functional index
CREATE INDEX idx_users_email_lower ON users(LOWER(email));
SELECT * FROM users WHERE LOWER(email) = 'foo@example.com';
```

### Pattern 4: Index for ORDER BY

```sql
-- Slow: Sort step required
SELECT * FROM orders WHERE user_id = 123 ORDER BY created_at DESC;

-- Fast: Index matches ORDER BY
CREATE INDEX idx_orders_user_created_desc ON orders(user_id, created_at DESC);
SELECT * FROM orders WHERE user_id = 123 ORDER BY created_at DESC;
```

### Pattern 5: Multivariate Statistics

```sql
-- When columns are correlated, planner may misestimate
-- Example: (zipcode, state) are correlated
CREATE STATISTICS stats_location ON zipcode, state FROM addresses;
ANALYZE addresses;

-- Planner now understands correlation
SELECT * FROM addresses WHERE zipcode = '94103' AND state = 'CA';
```

---

## Anti-Patterns and Fixes

### Anti-Pattern 1: SELECT * When Only Few Columns Needed

```sql
-- Bad: Fetches all columns
SELECT * FROM orders WHERE user_id = 123;

-- Good: Fetches only needed columns (enables Index Only Scan)
SELECT id, total, created_at FROM orders WHERE user_id = 123;
```

### Anti-Pattern 2: Function on Indexed Column

```sql
-- Bad: Can't use index
SELECT * FROM events WHERE DATE(created_at) = '2025-01-01';

-- Good: Range query uses index
SELECT * FROM events WHERE created_at >= '2025-01-01' AND created_at < '2025-01-02';
```

### Anti-Pattern 3: OR Across Different Columns

```sql
-- Bad: May require multiple scans
SELECT * FROM orders WHERE user_id = 123 OR vendor_id = 456;

-- Good: UNION uses indexes efficiently
SELECT * FROM orders WHERE user_id = 123
UNION
SELECT * FROM orders WHERE vendor_id = 456;
```

### Anti-Pattern 4: Unanchored LIKE

```sql
-- Bad: Can't use B-tree index
SELECT * FROM users WHERE email LIKE '%@example.com';

-- Good: Use trigram index
CREATE EXTENSION pg_trgm;
CREATE INDEX idx_users_email_trgm ON users USING GIN (email gin_trgm_ops);
SELECT * FROM users WHERE email LIKE '%@example.com';
```

### Anti-Pattern 5: Correlated Subquery

```sql
-- Bad: Subquery executed for each row
SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > 100);

-- Good: JOIN or EXISTS
SELECT DISTINCT u.* FROM users u INNER JOIN orders o ON o.user_id = u.id WHERE o.total > 100;
-- Or
SELECT * FROM users u WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id AND o.total > 100);
```

---

## Quick Reference

### EXPLAIN Cheat Sheet

```sql
-- Basic plan
EXPLAIN SELECT ...;

-- Plan + execution
EXPLAIN ANALYZE SELECT ...;

-- Plan + execution + buffer stats
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;

-- JSON format
EXPLAIN (FORMAT JSON, ANALYZE) SELECT ...;
```

### Index Creation Patterns

```sql
-- Standard B-tree
CREATE INDEX idx_name ON table(column);

-- Composite
CREATE INDEX idx_name ON table(col1, col2, col3);

-- Covering (Index Only Scan)
CREATE INDEX idx_name ON table(col1) INCLUDE (col2, col3);

-- Partial
CREATE INDEX idx_name ON table(col) WHERE condition;

-- Functional
CREATE INDEX idx_name ON table(LOWER(col));

-- Concurrent (no locks)
CREATE INDEX CONCURRENTLY idx_name ON table(col);
```

### Monitoring Queries

```sql
-- Find slow queries
SELECT query, calls, total_exec_time, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;

-- Find unused indexes
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexname NOT LIKE 'pg_%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Check index bloat
SELECT schemaname, tablename, indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

**Last Updated**: 2025-10-27
