-- Safe Migration: Adding nullable column
-- This is safe for zero-downtime deployment

-- Add nullable column with default
-- In PostgreSQL 11+, adding column with DEFAULT is fast (metadata-only operation)
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20) DEFAULT 'unknown';

-- Optionally, remove default after initial deployment
-- This prevents default from being applied to future inserts
-- ALTER TABLE users ALTER COLUMN phone DROP DEFAULT;

-- Why this is safe:
-- 1. IF NOT EXISTS makes it idempotent
-- 2. Nullable column doesn't require backfilling
-- 3. Default value (in PG 11+) doesn't rewrite table
-- 4. Old code ignores new column
-- 5. New code can read/write new column

-- Rollback:
-- ALTER TABLE users DROP COLUMN IF EXISTS phone;
