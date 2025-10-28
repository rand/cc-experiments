-- UNSAFE Migration: Large UPDATE in single transaction
-- This LOCKS millions of rows and can timeout

-- ❌ BAD: Updates all rows at once
-- UPDATE users SET status = 'active' WHERE status IS NULL;
-- Problems:
-- 1. Locks all matching rows (millions?)
-- 2. Can timeout (statement_timeout)
-- 3. Blocks concurrent updates
-- 4. Can fill up WAL (write-ahead log)

-- Why this is unsafe:
-- 1. Long-running lock blocks other transactions
-- 2. Can cause deadlocks with other queries
-- 3. Difficult to monitor progress
-- 4. If fails, must restart from beginning

-- ✅ SAFE ALTERNATIVE: Batch updates

-- DO $$
-- DECLARE
--     batch_size INT := 1000;
--     rows_updated INT;
--     total_updated INT := 0;
-- BEGIN
--     LOOP
--         -- Update in batches
--         UPDATE users
--         SET status = 'active'
--         WHERE id IN (
--             SELECT id
--             FROM users
--             WHERE status IS NULL
--             LIMIT batch_size
--         );
--
--         GET DIAGNOSTICS rows_updated = ROW_COUNT;
--         total_updated := total_updated + rows_updated;
--
--         RAISE NOTICE 'Updated % rows (total: %)', rows_updated, total_updated;
--
--         EXIT WHEN rows_updated = 0;
--
--         -- Commit batch and release locks
--         COMMIT;
--
--         -- Small pause to avoid overwhelming database
--         PERFORM pg_sleep(0.1);
--     END LOOP;
-- END $$;

-- Benefits:
-- 1. Smaller batches = shorter locks
-- 2. Can monitor progress (RAISE NOTICE)
-- 3. Doesn't block other queries for long
-- 4. Can pause/resume if needed

-- Alternative: External script with batching
-- See examples/python/batch_update.py

-- For very large tables (100M+ rows):
-- 1. Consider partitioning
-- 2. Run during maintenance window
-- 3. Use parallel workers if possible
-- 4. Monitor locks and contention
