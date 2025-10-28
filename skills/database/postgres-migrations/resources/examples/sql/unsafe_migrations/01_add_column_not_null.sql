-- UNSAFE Migration: Adding NOT NULL column without default
-- This will FAIL if table has existing rows

-- ❌ BAD: This fails on non-empty tables
-- ALTER TABLE users ADD COLUMN phone VARCHAR(20) NOT NULL;
-- ERROR: column "phone" contains null values

-- Why this is unsafe:
-- 1. NOT NULL requires value for all existing rows
-- 2. Will fail if table has any data
-- 3. Locks table during operation
-- 4. Can't be rolled back easily if data is backfilled

-- ✅ SAFE ALTERNATIVE: Multi-step approach

-- Step 1: Add nullable column with default
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20) DEFAULT 'unknown';

-- Step 2: Backfill existing rows (if needed, in batches)
-- See safe_migrations/05_backfill_data.sql for batching example

-- Step 3: Add NOT NULL constraint (after all rows have values)
-- ALTER TABLE users ALTER COLUMN phone SET NOT NULL;

-- Step 4: Optionally remove default
-- ALTER TABLE users ALTER COLUMN phone DROP DEFAULT;

-- Deployment sequence:
-- 1. Deploy Step 1 + Step 2
-- 2. Wait for backfill to complete
-- 3. Deploy code that writes phone
-- 4. Deploy Step 3 + Step 4

-- Rollback:
-- ALTER TABLE users DROP COLUMN IF EXISTS phone;
