-- Non-Sargable Query Examples
--
-- PROBLEM: Functions on indexed columns prevent index usage
-- "Sargable" = Search ARGument ABLE (can use index)

-- Example 1: Function on indexed column (DATE)
-- BAD: Can't use index
EXPLAIN ANALYZE
SELECT * FROM events WHERE DATE(created_at) = '2025-01-15';

-- EXPLAIN output:
-- Seq Scan on events  (cost=0.00..2345.67 rows=50 width=128) (actual time=45.123..89.456 rows=1234 loops=1)
--   Filter: (date(created_at) = '2025-01-15'::date)
--   Rows Removed by Filter: 98766

-- GOOD: Range query uses index
CREATE INDEX idx_events_created_at ON events(created_at);

EXPLAIN ANALYZE
SELECT * FROM events
WHERE created_at >= '2025-01-15'
  AND created_at < '2025-01-16';

-- EXPLAIN output:
-- Index Scan using idx_events_created_at on events  (cost=0.42..45.67 rows=1234 width=128) (actual time=0.012..1.234 rows=1234 loops=1)
--   Index Cond: ((created_at >= '2025-01-15') AND (created_at < '2025-01-16'))

-- ALTERNATIVE: Functional index
CREATE INDEX idx_events_created_date ON events(DATE(created_at));

SELECT * FROM events WHERE DATE(created_at) = '2025-01-15';
-- Now uses idx_events_created_date

-- Example 2: LOWER() function on indexed column
-- BAD: Can't use index
EXPLAIN ANALYZE
SELECT * FROM users WHERE LOWER(email) = 'foo@example.com';

-- Seq Scan on users  (cost=0.00..1234.56 rows=5 width=64) (actual time=23.456..45.678 rows=1 loops=1)
--   Filter: (lower(email) = 'foo@example.com')

-- SOLUTION 1: Functional index
CREATE INDEX idx_users_email_lower ON users(LOWER(email));

SELECT * FROM users WHERE LOWER(email) = 'foo@example.com';
-- Uses idx_users_email_lower

-- SOLUTION 2: Store normalized data (preferred)
-- Add generated column
ALTER TABLE users ADD COLUMN email_lower TEXT GENERATED ALWAYS AS (LOWER(email)) STORED;
CREATE INDEX idx_users_email_lower ON users(email_lower);

SELECT * FROM users WHERE email_lower = 'foo@example.com';

-- Example 3: Arithmetic on indexed column
-- BAD
SELECT * FROM products WHERE price * 0.9 < 100;
-- Seq Scan (function on indexed column)

-- GOOD
SELECT * FROM products WHERE price < 100 / 0.9;
-- Index Scan using idx_products_price

-- Example 4: LIKE with leading wildcard
-- BAD: Can't use B-tree index
SELECT * FROM users WHERE email LIKE '%@example.com';
-- Seq Scan (no B-tree index can help)

-- SOLUTION: Trigram index (pg_trgm extension)
CREATE EXTENSION pg_trgm;
CREATE INDEX idx_users_email_trgm ON users USING GIN (email gin_trgm_ops);

SELECT * FROM users WHERE email LIKE '%@example.com';
-- Bitmap Heap Scan on users  (cost=12.34..234.56 rows=10 width=64)
--   Recheck Cond: (email ~~ '%@example.com')
--   ->  Bitmap Index Scan on idx_users_email_trgm  (cost=0.00..12.34 rows=10 width=0)
--         Index Cond: (email ~~ '%@example.com')

-- Example 5: OR conditions with different columns
-- BAD: Can't efficiently use indexes
SELECT * FROM orders WHERE user_id = 123 OR vendor_id = 456;
-- May use Bitmap Scan, but inefficient

-- GOOD: UNION with separate index scans
SELECT * FROM orders WHERE user_id = 123
UNION
SELECT * FROM orders WHERE vendor_id = 456;

-- Each part uses its own index efficiently

-- Example 6: NOT NULL check on nullable column
-- BAD: Sequential scan
SELECT * FROM orders WHERE total IS NOT NULL;

-- GOOD: Partial index for non-null values
CREATE INDEX idx_orders_total_not_null ON orders(total) WHERE total IS NOT NULL;

-- Or better: Use constraint to eliminate nulls at data level
ALTER TABLE orders ALTER COLUMN total SET NOT NULL;
ALTER TABLE orders ALTER COLUMN total SET DEFAULT 0;
