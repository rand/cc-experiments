-- PostgreSQL Query Optimization Test Database
-- Initializes sample schema and data for testing optimization techniques

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    vendor_id INTEGER,
    total DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create events table (time-series data)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    event_type VARCHAR(100) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Insert sample data
-- Users (10,000 records)
INSERT INTO users (email, name, status, created_at)
SELECT
    'user' || n || '@example.com',
    'User ' || n,
    CASE WHEN random() < 0.9 THEN 'active' ELSE 'inactive' END,
    NOW() - (random() * INTERVAL '365 days')
FROM generate_series(1, 10000) AS n;

-- Orders (100,000 records)
INSERT INTO orders (user_id, vendor_id, total, status, created_at)
SELECT
    1 + floor(random() * 10000)::INTEGER,
    1 + floor(random() * 100)::INTEGER,
    10 + (random() * 990)::DECIMAL(10, 2),
    CASE
        WHEN random() < 0.05 THEN 'pending'
        WHEN random() < 0.15 THEN 'processing'
        WHEN random() < 0.90 THEN 'completed'
        ELSE 'cancelled'
    END,
    NOW() - (random() * INTERVAL '365 days')
FROM generate_series(1, 100000) AS n;

-- Products (1,000 records)
INSERT INTO products (name, price, category, created_at)
SELECT
    'Product ' || n,
    10 + (random() * 490)::DECIMAL(10, 2),
    CASE
        WHEN random() < 0.3 THEN 'Electronics'
        WHEN random() < 0.6 THEN 'Clothing'
        WHEN random() < 0.8 THEN 'Books'
        ELSE 'Home & Garden'
    END,
    NOW() - (random() * INTERVAL '365 days')
FROM generate_series(1, 1000) AS n;

-- Events (500,000 records - time-series)
INSERT INTO events (user_id, event_type, metadata, created_at)
SELECT
    1 + floor(random() * 10000)::INTEGER,
    CASE
        WHEN random() < 0.4 THEN 'page_view'
        WHEN random() < 0.7 THEN 'click'
        WHEN random() < 0.9 THEN 'purchase'
        ELSE 'signup'
    END,
    jsonb_build_object(
        'page', '/page' || floor(random() * 100),
        'session_id', md5(random()::TEXT),
        'user_agent', 'Mozilla/5.0'
    ),
    NOW() - (random() * INTERVAL '30 days')
FROM generate_series(1, 500000) AS n;

-- Analyze tables to generate statistics
ANALYZE users;
ANALYZE orders;
ANALYZE products;
ANALYZE events;

-- Print summary
DO $$
BEGIN
    RAISE NOTICE 'Database initialized successfully!';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - users: % records', (SELECT COUNT(*) FROM users);
    RAISE NOTICE '  - orders: % records', (SELECT COUNT(*) FROM orders);
    RAISE NOTICE '  - products: % records', (SELECT COUNT(*) FROM products);
    RAISE NOTICE '  - events: % records', (SELECT COUNT(*) FROM events);
    RAISE NOTICE '';
    RAISE NOTICE 'Extensions enabled:';
    RAISE NOTICE '  - pg_stat_statements (query statistics)';
    RAISE NOTICE '  - pg_trgm (trigram indexes for LIKE queries)';
    RAISE NOTICE '';
    RAISE NOTICE 'Connection string:';
    RAISE NOTICE '  postgresql://testuser:testpass@localhost:5432/testdb';
END $$;
