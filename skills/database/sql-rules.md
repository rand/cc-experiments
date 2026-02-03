---
name: database-sql-rules
description: 30+ opinionated SQL and database rules for query safety, indexing, migrations, and performance. Actionable best practices.
---

# SQL & Database Rules

Opinionated, high-density rules for relational databases (PostgreSQL-focused, mostly applicable to MySQL/SQLite). These are prescriptive — follow them unless you have a specific, articulated reason not to. Not a tutorial; assumes working SQL knowledge.

---

## Safety

**1. Always use parameterized queries.**
No exceptions. No "just this one time." String interpolation into SQL is how you get SQLi. Every ORM and driver supports parameters.

```sql
-- Bad (any language)
query(f"SELECT * FROM users WHERE id = {user_id}")

-- Good
query("SELECT * FROM users WHERE id = $1", [user_id])
```

**2. Never `SELECT *` in application code.**
Select the columns you need. `SELECT *` breaks when columns are added, wastes bandwidth, defeats covering indexes, and leaks sensitive columns.

```sql
-- Bad
SELECT * FROM users WHERE id = $1

-- Good
SELECT id, name, email FROM users WHERE id = $1
```

**3. Set statement timeouts.**
Every database connection should have a statement timeout. A missing WHERE clause on a full-table scan shouldn't bring down your app.

```sql
-- PostgreSQL
SET statement_timeout = '5s';
```

**4. Use transactions for multi-step writes.**
If two writes must succeed or fail together, wrap them in a transaction. Don't rely on application-level rollback logic.

```sql
BEGIN;
  INSERT INTO orders (user_id, total) VALUES ($1, $2);
  UPDATE inventory SET quantity = quantity - $3 WHERE product_id = $4;
COMMIT;
```

**5. Don't run DDL inside transactions in PostgreSQL.**
`ALTER TABLE`, `CREATE INDEX` — these acquire heavy locks. In Postgres, some DDL is transactional but can cause long lock waits. Keep DDL operations separate and brief.

**6. Audit sensitive tables.**
Tables with PII, financial data, or access controls need audit trails. Use trigger-based audit logging or CDC. Know who changed what, when.

---

## Indexing

**7. Index every foreign key.**
Unindexed foreign keys cause full table scans on JOINs and CASCADE deletes. This is the single most common performance mistake.

```sql
-- If orders.user_id references users.id:
CREATE INDEX idx_orders_user_id ON orders (user_id);
```

**8. Composite index column order matters.**
The leftmost column is used for equality lookups. Put high-selectivity equality columns first, range columns last.

```sql
-- For: WHERE tenant_id = $1 AND created_at > $2
CREATE INDEX idx_orders_tenant_created ON orders (tenant_id, created_at);

-- NOT: (created_at, tenant_id) — can't use index for tenant_id equality
```

**9. Use covering indexes for hot queries.**
Include all selected columns in the index to avoid heap lookups. Dramatic speedup for read-heavy queries.

```sql
-- Query: SELECT name, email FROM users WHERE tenant_id = $1
CREATE INDEX idx_users_tenant_covering ON users (tenant_id) INCLUDE (name, email);
```

**10. Don't over-index.**
Every index slows down writes and consumes storage. If an index isn't used by any query plan, drop it. Monitor with `pg_stat_user_indexes`.

**11. Use partial indexes for filtered queries.**
If you frequently query a subset, index only that subset.

```sql
-- Only 5% of orders are active; most queries filter on active
CREATE INDEX idx_orders_active ON orders (created_at) WHERE status = 'active';
```

---

## Migrations

**12. Every migration must be reversible.**
Write both `up` and `down`. If you can't reverse it, document why and get explicit approval.

**13. Never destroy data in a migration.**
Dropping columns or tables deletes data. Rename first, keep for a release cycle, then drop. Back up before destructive migrations.

**14. Separate schema migrations from data migrations.**
Schema changes (ADD COLUMN, CREATE TABLE) and data backfills are different concerns. Run them separately. Data migrations can be slow and shouldn't block deploys.

**15. Test rollback in staging.**
Run `up`, verify, run `down`, verify. Every time. Broken rollbacks are discovered at 3 AM in production.

**16. Add columns as NULL or with defaults — never lock the table.**
In PostgreSQL, `ALTER TABLE ADD COLUMN` with a volatile default rewrites the table and locks it. Add as NULL, backfill, then add constraint.

```sql
-- Safe
ALTER TABLE users ADD COLUMN phone TEXT;

-- Unsafe on large tables (Postgres < 11)
ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT 'unknown';
```

---

## Performance

**17. Run `EXPLAIN ANALYZE` before optimizing.**
Don't guess. Read the query plan. Look for sequential scans on large tables, nested loops with high row counts, and sort operations on unindexed columns.

```sql
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10;
```

**18. Avoid N+1 queries.**
If you fetch a list then query each item individually, you have N+1. Use JOINs, subqueries, or `WHERE id IN (...)` to batch.

```sql
-- Bad: 1 query for orders + N queries for users
-- Good: single query
SELECT o.*, u.name FROM orders o JOIN users u ON o.user_id = u.id WHERE o.status = 'pending';
```

**19. Use connection pooling.**
Don't open a new connection per request. Use PgBouncer, pgpool, or your framework's pool. Set pool size to roughly `(2 * CPU cores) + disk spindles`.

**20. Batch inserts.**
Inserting 1,000 rows one at a time means 1,000 round trips. Use multi-row INSERT or COPY.

```sql
-- Good
INSERT INTO events (type, data) VALUES
  ('click', '{}'),
  ('view', '{}'),
  ('purchase', '{}');
```

**21. Always LIMIT result sets.**
Every query that returns a list must have a LIMIT. Even internal/admin queries. An unbounded query on a growing table will eventually OOM your app.

**22. Use materialized views for expensive aggregations.**
Dashboard queries that aggregate millions of rows shouldn't run on every page load. Materialize and refresh on a schedule or trigger.

```sql
CREATE MATERIALIZED VIEW monthly_revenue AS
  SELECT date_trunc('month', created_at) AS month, SUM(total) AS revenue
  FROM orders WHERE status = 'completed'
  GROUP BY 1;

REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue;
```

---

## Schema

**23. Use appropriate types — never store money as float.**
Floats have rounding errors. Use `NUMERIC(19,4)` or `BIGINT` (store cents). Use `TIMESTAMPTZ` not `TIMESTAMP`. Use `UUID` for external-facing IDs.

```sql
-- Bad
price FLOAT

-- Good
price NUMERIC(19, 4)
```

**24. Default to NOT NULL.**
Nullable columns require special handling everywhere (IS NULL, COALESCE, three-valued logic). Only allow NULL when absence of value is semantically meaningful.

**25. Use enums or check constraints for fixed value sets.**
Status fields, types, categories with a known set of values should be constrained at the database level.

```sql
CREATE TYPE order_status AS ENUM ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled');
-- Or:
ALTER TABLE orders ADD CONSTRAINT chk_status CHECK (status IN ('pending', 'confirmed', 'shipped'));
```

**26. Always use `TIMESTAMPTZ`, never `TIMESTAMP`.**
`TIMESTAMP` loses timezone info. `TIMESTAMPTZ` stores UTC and converts on display. This prevents an entire class of timezone bugs.

**27. Use soft deletes only when you have a real requirement.**
Soft deletes (`deleted_at`) add complexity to every query (WHERE deleted_at IS NULL). Use them for audit requirements, not as a "just in case" pattern. Hard delete + audit log is often simpler.

---

## Operations

**28. Monitor slow queries.**
Enable `pg_stat_statements`. Set `log_min_duration_statement` to catch queries over 100ms. Review weekly. The slowest query today is tomorrow's outage.

**29. Run VACUUM and ANALYZE regularly.**
Autovacuum handles most cases, but monitor it. Dead tuples bloat tables and slow queries. `ANALYZE` keeps the query planner's statistics accurate.

**30. Set connection limits.**
Don't let a traffic spike exhaust your connection limit. Set `max_connections` appropriately, use pooling, and monitor active connections. A queued connection is better than a rejected one.

**31. Use read replicas for read-heavy workloads.**
Route reporting, search, and dashboard queries to replicas. Keep the primary for writes. Accept eventual consistency where appropriate.

**32. Back up continuously, test restores regularly.**
WAL archiving or streaming replication for point-in-time recovery. A backup you've never restored is not a backup. Test monthly.

**33. Use advisory locks for application-level coordination.**
When you need distributed locking without an external system, PostgreSQL advisory locks are lightweight and reliable.

```sql
SELECT pg_advisory_lock(hashtext('process-payments'));
-- ... do work ...
SELECT pg_advisory_unlock(hashtext('process-payments'));
```
