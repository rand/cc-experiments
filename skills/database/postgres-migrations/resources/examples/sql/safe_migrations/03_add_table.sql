-- Safe Migration: Adding new table
-- Safe for zero-downtime deployment

BEGIN;

-- Create table with IF NOT EXISTS for idempotency
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    total DECIMAL(10,2) NOT NULL CHECK (total >= 0),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'cancelled')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add foreign key constraint
-- Using IF NOT EXISTS requires PostgreSQL 12+, otherwise check manually
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_orders_user_id'
    ) THEN
        ALTER TABLE orders ADD CONSTRAINT fk_orders_user_id
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Add indexes (within transaction is fine for new table)
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

COMMIT;

-- Why this is safe:
-- 1. New table doesn't affect existing code
-- 2. IF NOT EXISTS makes it idempotent
-- 3. All operations in transaction (atomic)
-- 4. Old code ignores new table
-- 5. Foreign key ensures referential integrity

-- Rollback:
-- DROP TABLE IF EXISTS orders;
