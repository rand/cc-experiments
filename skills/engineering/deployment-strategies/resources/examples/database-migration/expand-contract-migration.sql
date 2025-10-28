-- Expand-Contract Database Migration Pattern
--
-- This example demonstrates the expand-contract pattern for zero-downtime
-- database schema changes during deployments.
--
-- Pattern: EXPAND → MIGRATE → CONTRACT
--
-- Use case: Rename column 'status' (int) to 'status_name' (varchar)
-- in the orders table without downtime.

-- ============================================================================
-- PHASE 1: EXPAND (Deploy v1.1 application)
-- ============================================================================
-- Add new schema alongside old schema.
-- Application v1.1 writes to BOTH old and new columns.

BEGIN;

-- Step 1: Add new column (nullable initially)
ALTER TABLE orders
ADD COLUMN status_name VARCHAR(50) NULL;

-- Step 2: Add index for new column
CREATE INDEX idx_orders_status_name ON orders(status_name);

-- Step 3: Create trigger to keep columns in sync (PostgreSQL example)
CREATE OR REPLACE FUNCTION sync_order_status()
RETURNS TRIGGER AS $$
BEGIN
  -- When old column is updated, update new column
  IF NEW.status IS DISTINCT FROM OLD.status THEN
    NEW.status_name := CASE NEW.status
      WHEN 0 THEN 'pending'
      WHEN 1 THEN 'processing'
      WHEN 2 THEN 'shipped'
      WHEN 3 THEN 'delivered'
      WHEN 4 THEN 'cancelled'
      ELSE 'unknown'
    END;
  END IF;

  -- When new column is updated, update old column
  IF NEW.status_name IS DISTINCT FROM OLD.status_name THEN
    NEW.status := CASE NEW.status_name
      WHEN 'pending' THEN 0
      WHEN 'processing' THEN 1
      WHEN 'shipped' THEN 2
      WHEN 'delivered' THEN 3
      WHEN 'cancelled' THEN 4
      ELSE -1
    END;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER orders_status_sync
BEFORE INSERT OR UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION sync_order_status();

COMMIT;

-- Application v1.1 code changes:
-- - Dual writes to both status and status_name
-- - Reads from old column (status) still work
-- - Gradual migration can begin

-- ============================================================================
-- PHASE 2: MIGRATE (Background data migration)
-- ============================================================================
-- Backfill new column with data from old column.
-- Do this in batches to avoid locking the table.

DO $$
DECLARE
  batch_size INTEGER := 10000;
  rows_updated INTEGER;
  total_updated INTEGER := 0;
BEGIN
  LOOP
    -- Update in batches
    UPDATE orders
    SET status_name = CASE status
      WHEN 0 THEN 'pending'
      WHEN 1 THEN 'processing'
      WHEN 2 THEN 'shipped'
      WHEN 3 THEN 'delivered'
      WHEN 4 THEN 'cancelled'
      ELSE 'unknown'
    END
    WHERE status_name IS NULL
    AND id IN (
      SELECT id FROM orders
      WHERE status_name IS NULL
      LIMIT batch_size
    );

    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    total_updated := total_updated + rows_updated;

    RAISE NOTICE 'Updated % rows (total: %)', rows_updated, total_updated;

    EXIT WHEN rows_updated = 0;

    -- Small delay between batches to reduce load
    PERFORM pg_sleep(0.1);
  END LOOP;

  RAISE NOTICE 'Migration complete. Total rows updated: %', total_updated;
END $$;

-- Verify migration completeness
SELECT
  COUNT(*) as total_rows,
  COUNT(status_name) as migrated_rows,
  COUNT(*) - COUNT(status_name) as remaining_rows
FROM orders;

-- ============================================================================
-- INTERMEDIATE: Deploy v1.2 application
-- ============================================================================
-- Application v1.2 changes:
-- - Reads from NEW column (status_name)
-- - Still writes to BOTH columns (maintains compatibility)
--
-- At this point:
-- - Old application (v1.0) can still read from old column
-- - New application (v1.2) reads from new column
-- - Both versions can coexist during rolling deployment

-- Monitor application after v1.2 deployment
-- Check that no errors occur with new column

-- ============================================================================
-- PHASE 3: CONTRACT (Deploy v1.3 application, cleanup)
-- ============================================================================
-- Remove old schema after all application instances are upgraded.
-- Wait for rollback window to pass (e.g., 1-2 weeks).

BEGIN;

-- Step 1: Remove trigger (no longer needed)
DROP TRIGGER IF EXISTS orders_status_sync ON orders;
DROP FUNCTION IF EXISTS sync_order_status();

-- Step 2: Make new column NOT NULL (after verifying all data migrated)
ALTER TABLE orders
ALTER COLUMN status_name SET NOT NULL;

-- Step 3: Drop old column
ALTER TABLE orders
DROP COLUMN status;

-- Step 4: Rename new column to final name (optional)
ALTER TABLE orders
RENAME COLUMN status_name TO status;

-- Step 5: Add constraints
ALTER TABLE orders
ADD CONSTRAINT orders_status_check
CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled'));

COMMIT;

-- ============================================================================
-- Alternative: Shadow Table Pattern (for major schema changes)
-- ============================================================================

-- Create new table with desired schema
CREATE TABLE orders_v2 (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  status VARCHAR(50) NOT NULL,
  total_amount DECIMAL(10, 2) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT orders_v2_status_check
  CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled'))
);

-- Create indexes
CREATE INDEX idx_orders_v2_user_id ON orders_v2(user_id);
CREATE INDEX idx_orders_v2_status ON orders_v2(status);
CREATE INDEX idx_orders_v2_created_at ON orders_v2(created_at);

-- Migrate data
INSERT INTO orders_v2 (id, user_id, status, total_amount, created_at, updated_at)
SELECT
  id,
  user_id,
  CASE status
    WHEN 0 THEN 'pending'
    WHEN 1 THEN 'processing'
    WHEN 2 THEN 'shipped'
    WHEN 3 THEN 'delivered'
    WHEN 4 THEN 'cancelled'
    ELSE 'unknown'
  END,
  total_amount,
  created_at,
  updated_at
FROM orders;

-- Application does dual writes during transition period
-- After rollback window, swap tables:

BEGIN;

-- Rename old table
ALTER TABLE orders RENAME TO orders_old;

-- Rename new table
ALTER TABLE orders_v2 RENAME TO orders;

-- Update sequence
ALTER SEQUENCE orders_v2_id_seq RENAME TO orders_id_seq;

COMMIT;

-- Keep orders_old for a while, then drop when safe

-- ============================================================================
-- Backward Compatible Column Addition
-- ============================================================================

-- Adding a new column (safe, no downtime needed)
ALTER TABLE orders
ADD COLUMN tracking_number VARCHAR(100) NULL;

-- Adding with default (can lock table on large tables)
-- Better to add nullable first, backfill, then set default
ALTER TABLE orders
ADD COLUMN priority INTEGER DEFAULT 0 NOT NULL;

-- Better approach for large tables:
BEGIN;
  -- Add column without default
  ALTER TABLE orders ADD COLUMN priority INTEGER NULL;

  -- Set default for new rows only
  ALTER TABLE orders ALTER COLUMN priority SET DEFAULT 0;

  -- Backfill in batches (see PHASE 2 example above)
  -- Then set NOT NULL
  ALTER TABLE orders ALTER COLUMN priority SET NOT NULL;
COMMIT;

-- ============================================================================
-- View-Based Compatibility Layer
-- ============================================================================

-- Provide backward compatibility for old code via views
CREATE VIEW orders_legacy AS
SELECT
  id,
  user_id,
  CASE status
    WHEN 'pending' THEN 0
    WHEN 'processing' THEN 1
    WHEN 'shipped' THEN 2
    WHEN 'delivered' THEN 3
    WHEN 'cancelled' THEN 4
  END as status,
  total_amount,
  created_at,
  updated_at
FROM orders;

-- Old code can query orders_legacy
-- New code queries orders directly

-- ============================================================================
-- Online Schema Change Tools
-- ============================================================================

-- GitHub's gh-ost (MySQL)
/*
gh-ost \
  --user=root \
  --password=secret \
  --host=mysql.example.com \
  --database=myapp \
  --table=orders \
  --alter="ADD COLUMN priority INT NOT NULL DEFAULT 0" \
  --exact-rowcount \
  --concurrent-rowcount \
  --default-retries=120 \
  --chunk-size=1000 \
  --max-load=Threads_running=25 \
  --critical-load=Threads_running=1000 \
  --execute
*/

-- Percona pt-online-schema-change (MySQL)
/*
pt-online-schema-change \
  --alter="ADD COLUMN priority INT NOT NULL DEFAULT 0" \
  --execute \
  D=myapp,t=orders \
  --chunk-size=1000 \
  --max-load="Threads_running=50" \
  --critical-load="Threads_running=100"
*/

-- ============================================================================
-- Rollback Strategy
-- ============================================================================

-- If something goes wrong during migration, rollback:

-- PHASE 1 Rollback (if issues found after EXPAND)
BEGIN;
  DROP TRIGGER IF EXISTS orders_status_sync ON orders;
  DROP FUNCTION IF EXISTS sync_order_status();
  DROP INDEX IF EXISTS idx_orders_status_name;
  ALTER TABLE orders DROP COLUMN IF EXISTS status_name;
COMMIT;

-- PHASE 2 Rollback (data corruption)
-- Re-run migration from old column
UPDATE orders
SET status_name = CASE status
  WHEN 0 THEN 'pending'
  WHEN 1 THEN 'processing'
  WHEN 2 THEN 'shipped'
  WHEN 3 THEN 'delivered'
  WHEN 4 THEN 'cancelled'
END
WHERE id IN (SELECT id FROM corrupted_rows);

-- PHASE 3 Rollback (after CONTRACT - requires restore)
-- This is why we wait before dropping old columns!
-- If you dropped too early, you need to:
-- 1. Rollback application to v1.1
-- 2. Re-add old column
-- 3. Backfill from new column
BEGIN;
  ALTER TABLE orders ADD COLUMN status_old INTEGER;

  UPDATE orders
  SET status_old = CASE status
    WHEN 'pending' THEN 0
    WHEN 'processing' THEN 1
    WHEN 'shipped' THEN 2
    WHEN 'delivered' THEN 3
    WHEN 'cancelled' THEN 4
  END;

  ALTER TABLE orders ALTER COLUMN status_old SET NOT NULL;
  ALTER TABLE orders RENAME COLUMN status_old TO status;
COMMIT;

-- ============================================================================
-- Best Practices Summary
-- ============================================================================

-- 1. Always add columns as nullable first
-- 2. Backfill data in batches (avoid table locks)
-- 3. Use triggers or dual writes during transition
-- 4. Keep old and new schema for rollback window
-- 5. Monitor application health during each phase
-- 6. Use transactions for atomic changes
-- 7. Test rollback procedures before production
-- 8. Document migration steps and timing
-- 9. Consider using online schema change tools for large tables
-- 10. Wait appropriate time before final cleanup (CONTRACT phase)
