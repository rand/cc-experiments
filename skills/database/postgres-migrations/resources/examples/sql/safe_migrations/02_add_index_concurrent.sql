-- Safe Migration: Adding index concurrently
-- CONCURRENTLY prevents blocking writes

-- NOTE: CONCURRENTLY cannot run inside a transaction block
-- This migration should NOT be wrapped in BEGIN/COMMIT

-- Create index without blocking writes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);

-- Why this is safe:
-- 1. CONCURRENTLY allows concurrent reads and writes
-- 2. IF NOT EXISTS makes it idempotent
-- 3. Takes longer but doesn't block traffic
-- 4. Can fail and leave invalid index (check with query below)

-- Check for invalid indexes:
-- SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;

-- If invalid index found, drop and retry:
-- DROP INDEX CONCURRENTLY IF EXISTS idx_users_email;
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);

-- Rollback:
-- DROP INDEX CONCURRENTLY IF EXISTS idx_users_email;
