-- Missing Index Example
--
-- PROBLEM: Sequential scan on large table for selective query

-- Slow query (Sequential Scan)
EXPLAIN ANALYZE
SELECT * FROM orders WHERE user_id = 123 AND status = 'pending';

-- EXPLAIN output:
-- Seq Scan on orders  (cost=0.00..15234.56 rows=5 width=128) (actual time=123.456..234.567 rows=5 loops=1)
--   Filter: ((user_id = 123) AND (status = 'pending'))
--   Rows Removed by Filter: 99995
-- Planning Time: 0.123 ms
-- Execution Time: 234.890 ms

-- PROBLEM ANALYSIS:
-- 1. Scans all 100,000 rows to find 5 matches
-- 2. Removes 99,995 rows via filter
-- 3. Takes 234ms for highly selective query

-- SOLUTION: Create composite index on filtered columns
CREATE INDEX idx_orders_user_id_status ON orders(user_id, status);

-- After index creation:
EXPLAIN ANALYZE
SELECT * FROM orders WHERE user_id = 123 AND status = 'pending';

-- EXPLAIN output:
-- Index Scan using idx_orders_user_id_status on orders  (cost=0.42..8.44 rows=5 width=128) (actual time=0.012..0.015 rows=5 loops=1)
--   Index Cond: ((user_id = 123) AND (status = 'pending'))
-- Planning Time: 0.098 ms
-- Execution Time: 0.045 ms

-- RESULT: 234ms → 0.045ms (5000x faster!)

-- ALTERNATIVE: Partial index if most orders are NOT pending
CREATE INDEX idx_orders_pending ON orders(user_id, created_at) WHERE status = 'pending';
-- Smaller index, faster writes, perfect for skewed data

-- COVERING INDEX: If query only needs specific columns
CREATE INDEX idx_orders_user_status_covering ON orders(user_id, status) INCLUDE (id, total, created_at);

-- Enables Index Only Scan (no heap lookups):
SELECT id, total, created_at FROM orders WHERE user_id = 123 AND status = 'pending';

-- Index Only Scan using idx_orders_user_status_covering on orders  (cost=0.42..4.44 rows=5 width=16) (actual time=0.010..0.012 rows=5 loops=1)
--   Index Cond: ((user_id = 123) AND (status = 'pending'))
--   Heap Fetches: 0
-- Execution Time: 0.025 ms
