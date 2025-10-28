# PostgreSQL Test Environment for Query Optimization

This Docker environment provides a pre-configured PostgreSQL database with sample data for testing query optimization techniques.

## Quick Start

```bash
# Start PostgreSQL
docker-compose up -d

# Wait for initialization (check logs)
docker-compose logs -f postgres

# Connect to database
psql postgresql://testuser:testpass@localhost:5432/testdb

# Stop and remove
docker-compose down

# Stop and remove with data cleanup
docker-compose down -v
```

## Database Schema

### Tables

1. **users** (10,000 records)
   - id, email, name, status, created_at, updated_at
   - 90% active, 10% inactive

2. **orders** (100,000 records)
   - id, user_id, vendor_id, total, status, created_at, updated_at
   - Status distribution: 5% pending, 10% processing, 75% completed, 10% cancelled

3. **products** (1,000 records)
   - id, name, price, category, created_at
   - Categories: Electronics, Clothing, Books, Home & Garden

4. **events** (500,000 records - time-series)
   - id, user_id, event_type, metadata (JSONB), created_at
   - Event types: page_view (40%), click (30%), purchase (20%), signup (10%)
   - Last 30 days of data

### Extensions

- **pg_stat_statements**: Track query execution statistics
- **pg_trgm**: Trigram indexes for pattern matching

## Testing Query Optimization

### Test 1: Sequential Scan vs Index Scan

```sql
-- Before: Sequential scan
EXPLAIN ANALYZE
SELECT * FROM orders WHERE user_id = 123;

-- Create index
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- After: Index scan
EXPLAIN ANALYZE
SELECT * FROM orders WHERE user_id = 123;
```

### Test 2: Composite Index

```sql
-- Multi-column query
EXPLAIN ANALYZE
SELECT * FROM orders WHERE user_id = 123 AND status = 'pending';

-- Create composite index
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- Verify improvement
EXPLAIN ANALYZE
SELECT * FROM orders WHERE user_id = 123 AND status = 'pending';
```

### Test 3: Covering Index (Index Only Scan)

```sql
-- Query with specific columns
EXPLAIN ANALYZE
SELECT id, total, created_at FROM orders WHERE user_id = 123;

-- Create covering index
CREATE INDEX idx_orders_user_covering ON orders(user_id) INCLUDE (id, total, created_at);

-- Verify Index Only Scan
EXPLAIN ANALYZE
SELECT id, total, created_at FROM orders WHERE user_id = 123;
```

### Test 4: Partial Index

```sql
-- Query on skewed data (only 5% pending)
EXPLAIN ANALYZE
SELECT * FROM orders WHERE status = 'pending';

-- Create partial index
CREATE INDEX idx_orders_pending ON orders(user_id, created_at) WHERE status = 'pending';

-- Verify smaller, faster index
EXPLAIN ANALYZE
SELECT * FROM orders WHERE status = 'pending' AND user_id = 123;
```

### Test 5: JSONB Index

```sql
-- JSONB query
EXPLAIN ANALYZE
SELECT * FROM events WHERE metadata @> '{"page": "/page42"}';

-- Create GIN index
CREATE INDEX idx_events_metadata ON events USING GIN (metadata);

-- Verify improvement
EXPLAIN ANALYZE
SELECT * FROM events WHERE metadata @> '{"page": "/page42"}';
```

### Test 6: Full-Text Search

```sql
-- Pattern matching with LIKE
EXPLAIN ANALYZE
SELECT * FROM users WHERE email LIKE '%example.com';

-- Create trigram index
CREATE INDEX idx_users_email_trgm ON users USING GIN (email gin_trgm_ops);

-- Verify improvement
EXPLAIN ANALYZE
SELECT * FROM users WHERE email LIKE '%example.com';
```

### Test 7: N+1 Query Problem

```sql
-- Bad: N+1 queries
SELECT * FROM users WHERE status = 'active';
-- Then in loop: SELECT * FROM orders WHERE user_id = ?

-- Good: Single JOIN
SELECT u.*, o.*
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.status = 'active';
```

### Test 8: Workload Analysis

```sql
-- View query statistics
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Reset statistics
SELECT pg_stat_statements_reset();
```

## Using the Optimization Scripts

```bash
# Analyze query
psql postgresql://testuser:testpass@localhost:5432/testdb -c "EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 123" | python ../../scripts/analyze_query.py --stdin

# Get index recommendations
python ../../scripts/suggest_indexes.py --query "SELECT * FROM orders WHERE user_id = 123 AND status = 'pending'" --connection "postgresql://testuser:testpass@localhost:5432/testdb"

# Benchmark query
./../../scripts/benchmark_queries.sh --query "SELECT * FROM orders WHERE user_id = 123" --connection "postgresql://testuser:testpass@localhost:5432/testdb" --iterations 20
```

## Test Scenarios

### Scenario 1: Slow JOIN Query

```sql
-- Slow query
EXPLAIN ANALYZE
SELECT u.name, COUNT(o.id) as order_count, SUM(o.total) as total_spent
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE u.status = 'active'
GROUP BY u.id, u.name;

-- Recommended indexes
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- Re-run and compare
```

### Scenario 2: Time-Series Query

```sql
-- Query last 7 days of events
EXPLAIN ANALYZE
SELECT event_type, COUNT(*)
FROM events
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY event_type;

-- BRIN index for time-series data
CREATE INDEX idx_events_created_brin ON events USING BRIN (created_at);

-- Re-run and compare
```

### Scenario 3: Inefficient Filtering

```sql
-- Many rows filtered out
EXPLAIN ANALYZE
SELECT * FROM orders WHERE DATE(created_at) = '2025-01-15';

-- Better: Range query
EXPLAIN ANALYZE
SELECT * FROM orders
WHERE created_at >= '2025-01-15'
  AND created_at < '2025-01-16';

-- Create index
CREATE INDEX idx_orders_created ON orders(created_at);
```

## Cleanup

```bash
# Stop containers
docker-compose down

# Remove containers and volumes (deletes data)
docker-compose down -v

# Remove all indexes for fresh start
psql postgresql://testuser:testpass@localhost:5432/testdb << EOF
DROP INDEX IF EXISTS idx_orders_user_id;
DROP INDEX IF EXISTS idx_orders_user_status;
DROP INDEX IF EXISTS idx_orders_user_covering;
DROP INDEX IF EXISTS idx_orders_pending;
DROP INDEX IF EXISTS idx_events_metadata;
DROP INDEX IF EXISTS idx_users_email_trgm;
DROP INDEX IF EXISTS idx_users_status;
DROP INDEX IF EXISTS idx_events_created_brin;
DROP INDEX IF EXISTS idx_orders_created;
EOF
```

## Connection Details

- **Host**: localhost
- **Port**: 5432
- **Database**: testdb
- **User**: testuser
- **Password**: testpass
- **Connection String**: `postgresql://testuser:testpass@localhost:5432/testdb`

## Troubleshooting

### Container won't start

```bash
# Check if port 5432 is already in use
lsof -i :5432

# Use different port in docker-compose.yml
ports:
  - "5433:5432"
```

### Database not initialized

```bash
# Check logs
docker-compose logs postgres

# Restart with clean slate
docker-compose down -v
docker-compose up -d
```

### Connection refused

```bash
# Wait for healthcheck
docker-compose ps

# Check if container is healthy
docker-compose exec postgres pg_isready -U testuser -d testdb
```

---

**Last Updated**: 2025-10-27
