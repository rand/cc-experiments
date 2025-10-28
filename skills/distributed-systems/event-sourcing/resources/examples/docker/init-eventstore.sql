-- Event Store Database Initialization Script
-- Creates all necessary tables, indexes, and triggers for event sourcing

-- Events table: Core event storage
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(255) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    version INTEGER NOT NULL,
    data JSONB NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (aggregate_id, version)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_events_aggregate ON events(aggregate_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_id_version ON events(id, version);
CREATE INDEX IF NOT EXISTS idx_events_aggregate_type ON events(aggregate_type);

-- Streams table: Track aggregate metadata
CREATE TABLE IF NOT EXISTS streams (
    aggregate_id VARCHAR(255) PRIMARY KEY,
    aggregate_type VARCHAR(100) NOT NULL,
    current_version INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Snapshots table: Optimize aggregate loading
CREATE TABLE IF NOT EXISTS snapshots (
    aggregate_id VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL,
    data JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (aggregate_id, version)
);

-- Index for latest snapshot
CREATE INDEX IF NOT EXISTS idx_snapshots_aggregate_version
ON snapshots(aggregate_id, version DESC);

-- Projections checkpoint table
CREATE TABLE IF NOT EXISTS projection_checkpoints (
    projection_name VARCHAR(255) PRIMARY KEY,
    last_event_id BIGINT NOT NULL,
    last_processed_at TIMESTAMPTZ NOT NULL
);

-- Saga state table (for saga pattern)
CREATE TABLE IF NOT EXISTS saga_state (
    saga_id VARCHAR(255) PRIMARY KEY,
    saga_type VARCHAR(100) NOT NULL,
    state JSONB NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Function to notify on new events (for real-time projections)
CREATE OR REPLACE FUNCTION notify_new_event()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('new_event', json_build_object(
        'id', NEW.id,
        'event_type', NEW.event_type,
        'aggregate_id', NEW.aggregate_id
    )::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to send notification on new events
DROP TRIGGER IF EXISTS events_notify_trigger ON events;
CREATE TRIGGER events_notify_trigger
AFTER INSERT ON events
FOR EACH ROW
EXECUTE FUNCTION notify_new_event();

-- Grants (adjust as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO eventuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO eventuser;

-- Sample data for testing (optional)
-- INSERT INTO events (event_id, event_type, aggregate_id, aggregate_type, version, data, metadata)
-- VALUES (
--     'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
--     'AccountOpened',
--     'account-test-1',
--     'BankAccount',
--     1,
--     '{"accountId": "account-test-1", "owner": "Test User", "initialDeposit": "1000.00", "currency": "USD"}',
--     '{"userId": "admin-1"}'
-- );

-- INSERT INTO streams (aggregate_id, aggregate_type, current_version, created_at, updated_at)
-- VALUES ('account-test-1', 'BankAccount', 1, NOW(), NOW());
