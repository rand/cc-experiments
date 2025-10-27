-- Safe Migration: Adding constraint without blocking
-- Use NOT VALID then VALIDATE to avoid locking

-- Step 1: Add constraint without validation (fast, no full table scan)
ALTER TABLE users
ADD CONSTRAINT check_username_length
CHECK (LENGTH(username) >= 3) NOT VALID;

-- Step 2: Validate constraint (slow, but allows concurrent reads/writes)
ALTER TABLE users VALIDATE CONSTRAINT check_username_length;

-- Why this is safe:
-- 1. NOT VALID adds constraint without scanning existing rows
-- 2. VALIDATE scans rows but allows concurrent reads/writes
-- 3. Two-step process avoids long exclusive lock
-- 4. New rows must satisfy constraint immediately after step 1

-- Lock behavior:
-- Step 1: ShareUpdateExclusiveLock (allows SELECT, INSERT, UPDATE, DELETE)
-- Step 2: ShareUpdateExclusiveLock (allows SELECT, INSERT, UPDATE, DELETE)

-- Alternative for foreign keys:
-- ALTER TABLE orders
-- ADD CONSTRAINT fk_orders_user_id
-- FOREIGN KEY (user_id) REFERENCES users(id)
-- NOT VALID;
--
-- ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_user_id;

-- Rollback:
-- ALTER TABLE users DROP CONSTRAINT IF EXISTS check_username_length;
