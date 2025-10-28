-- UNSAFE Migration: Creating index without CONCURRENTLY
-- This BLOCKS all writes to the table

-- ❌ BAD: Locks table, blocks writes
-- CREATE INDEX idx_users_email ON users(email);

-- Why this is unsafe:
-- 1. Takes ShareLock which blocks INSERT, UPDATE, DELETE
-- 2. Can take minutes on large tables
-- 3. Blocks application during creation
-- 4. Can cause downtime or timeouts

-- Lock behavior:
-- ShareLock: Allows SELECT, but blocks INSERT, UPDATE, DELETE, DDL

-- ✅ SAFE ALTERNATIVE: Use CONCURRENTLY

-- NOTE: Cannot run inside transaction
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);

-- Trade-offs:
-- - Takes 2-3x longer than regular CREATE INDEX
-- - Cannot run in transaction (must be in separate migration file)
-- - Can fail and leave invalid index
-- - But: doesn't block writes!

-- Check for invalid indexes after creation:
-- SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;

-- If invalid, drop and retry:
-- DROP INDEX CONCURRENTLY idx_users_email;
-- CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- Rollback:
-- DROP INDEX CONCURRENTLY IF EXISTS idx_users_email;
