-- UNSAFE Migration: Renaming column directly
-- This BREAKS old code immediately

-- ❌ BAD: Direct rename breaks running code
-- ALTER TABLE users RENAME COLUMN email TO email_address;

-- Why this is unsafe:
-- 1. Old code still references "email" column → ERROR
-- 2. Zero-downtime deployment impossible
-- 3. Rollback is easy but damage may be done
-- 4. Requires coordinated code + migration deployment

-- ✅ SAFE ALTERNATIVE: Expand-Contract Pattern (multi-phase)

-- PHASE 1: Add new column
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS email_address VARCHAR(255);

-- Create trigger for dual-write (sync old → new)
-- CREATE OR REPLACE FUNCTION sync_email_columns()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     NEW.email_address := NEW.email;
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;
--
-- CREATE TRIGGER sync_email_to_email_address
-- BEFORE INSERT OR UPDATE ON users
-- FOR EACH ROW
-- EXECUTE FUNCTION sync_email_columns();

-- PHASE 2: Backfill existing data
-- UPDATE users SET email_address = email WHERE email_address IS NULL;

-- PHASE 3: Deploy code that reads from email_address (still writes to email)
-- Old code: reads/writes email (trigger syncs to email_address)
-- New code: reads email_address, writes email (trigger syncs to email_address)

-- PHASE 4: Deploy code that writes to email_address
-- All code now uses email_address

-- PHASE 5: Drop old column and trigger
-- DROP TRIGGER IF EXISTS sync_email_to_email_address ON users;
-- DROP FUNCTION IF EXISTS sync_email_columns();
-- ALTER TABLE users DROP COLUMN IF EXISTS email;

-- Timeline:
-- Week 1: Phase 1 + 2 (add column, backfill)
-- Week 2: Phase 3 (app reads new column)
-- Week 3: Phase 4 (app writes new column)
-- Week 4: Phase 5 (drop old column)

-- Alternative: Keep both columns with constraint
-- ALTER TABLE users ADD CONSTRAINT email_sync CHECK (email = email_address);
-- This enforces synchronization without trigger
