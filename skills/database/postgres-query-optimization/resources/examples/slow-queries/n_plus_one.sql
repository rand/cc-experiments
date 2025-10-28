-- N+1 Query Problem Example
--
-- PROBLEM: Application loads users, then queries orders for each user in a loop
-- This creates N+1 queries (1 for users + N for orders)

-- Anti-pattern: Separate queries
-- Query 1: Load users
SELECT id, name, email FROM users WHERE status = 'active';

-- Query 2: In application loop, for EACH user:
-- SELECT * FROM orders WHERE user_id = ?;
-- If you have 100 users, this creates 100 additional queries (101 total)

-- EXPLAIN for the repeated query:
-- Seq Scan on orders  (cost=0.00..1234.56 rows=50 width=128)
--   Filter: (user_id = 123)
--   Rows Removed by Filter: 9950

-- SOLUTION 1: Use JOIN to fetch all data at once
SELECT
    u.id,
    u.name,
    u.email,
    o.id as order_id,
    o.total,
    o.created_at
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.status = 'active';

-- Result: 1 query instead of 101

-- SOLUTION 2: Batch query with IN clause
SELECT * FROM orders WHERE user_id IN (1, 2, 3, 4, 5, ...);
-- Then match orders to users in application code

-- SOLUTION 3: Use array aggregate for nested results
SELECT
    u.id,
    u.name,
    u.email,
    json_agg(json_build_object(
        'id', o.id,
        'total', o.total,
        'created_at', o.created_at
    )) as orders
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.status = 'active'
GROUP BY u.id, u.name, u.email;

-- Returns nested JSON structure in single query

-- RECOMMENDED INDEX:
CREATE INDEX idx_orders_user_id ON orders(user_id);
-- Dramatically speeds up JOIN performance
