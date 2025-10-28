-- ksqlDB Query Examples
--
-- Run these queries in ksqlDB CLI:
--   docker-compose exec ksqldb-cli ksql http://ksqldb-server:8088
--
-- Or via REST API:
--   curl -X POST http://localhost:8088/ksql \
--     -H "Content-Type: application/vnd.ksql.v1+json" \
--     -d '{"ksql":"SHOW TOPICS;","streamsProperties":{}}'

-- ============================================================================
-- 1. BASIC STREAMS AND TABLES
-- ============================================================================

-- List topics
SHOW TOPICS;

-- Create stream from Kafka topic
CREATE STREAM user_events (
  user_id VARCHAR,
  action VARCHAR,
  timestamp BIGINT,
  metadata MAP<VARCHAR, VARCHAR>
) WITH (
  KAFKA_TOPIC='user-events',
  VALUE_FORMAT='JSON',
  PARTITIONS=3,
  TIMESTAMP='timestamp'
);

-- Query stream (continuous query)
SELECT * FROM user_events EMIT CHANGES;

-- Create table (materialized view)
CREATE TABLE user_event_counts AS
SELECT
  user_id,
  COUNT(*) AS event_count,
  COLLECT_LIST(action) AS actions
FROM user_events
GROUP BY user_id
EMIT CHANGES;

-- Query table (pull query - point-in-time)
SELECT * FROM user_event_counts WHERE user_id='user123';

-- ============================================================================
-- 2. FILTERING AND TRANSFORMATIONS
-- ============================================================================

-- Filter events
CREATE STREAM login_events AS
SELECT *
FROM user_events
WHERE action = 'login'
EMIT CHANGES;

-- Transform values
CREATE STREAM enriched_events AS
SELECT
  user_id,
  action,
  UCASE(action) AS action_upper,
  timestamp,
  FROM_UNIXTIME(timestamp) AS event_time,
  TIMESTAMPTOSTRING(timestamp, 'yyyy-MM-dd HH:mm:ss') AS formatted_time
FROM user_events
EMIT CHANGES;

-- Multiple conditions
CREATE STREAM important_events AS
SELECT *
FROM user_events
WHERE
  action IN ('purchase', 'signup', 'payment')
  AND timestamp > UNIX_TIMESTAMP() - 3600000  -- Last hour
EMIT CHANGES;

-- ============================================================================
-- 3. AGGREGATIONS
-- ============================================================================

-- Count events per user
CREATE TABLE user_totals AS
SELECT
  user_id,
  COUNT(*) AS total_events,
  COUNT_DISTINCT(action) AS unique_actions,
  LATEST_BY_OFFSET(action) AS last_action
FROM user_events
GROUP BY user_id
EMIT CHANGES;

-- Sum and average
CREATE STREAM purchase_events (
  user_id VARCHAR,
  product_id VARCHAR,
  amount DOUBLE,
  timestamp BIGINT
) WITH (
  KAFKA_TOPIC='purchases',
  VALUE_FORMAT='JSON'
);

CREATE TABLE purchase_stats AS
SELECT
  user_id,
  COUNT(*) AS purchase_count,
  SUM(amount) AS total_spent,
  AVG(amount) AS avg_purchase,
  MIN(amount) AS min_purchase,
  MAX(amount) AS max_purchase
FROM purchase_events
GROUP BY user_id
EMIT CHANGES;

-- ============================================================================
-- 4. WINDOWING
-- ============================================================================

-- Tumbling window (5 minutes, non-overlapping)
CREATE TABLE event_counts_5min AS
SELECT
  user_id,
  COUNT(*) AS event_count,
  WINDOWSTART AS window_start,
  WINDOWEND AS window_end
FROM user_events
WINDOW TUMBLING (SIZE 5 MINUTES)
GROUP BY user_id
EMIT CHANGES;

-- Hopping window (10 minutes, advance 5 minutes)
CREATE TABLE event_counts_hopping AS
SELECT
  user_id,
  COUNT(*) AS event_count,
  WINDOWSTART,
  WINDOWEND
FROM user_events
WINDOW HOPPING (SIZE 10 MINUTES, ADVANCE BY 5 MINUTES)
GROUP BY user_id
EMIT CHANGES;

-- Session window (30-minute inactivity gap)
CREATE TABLE user_sessions AS
SELECT
  user_id,
  COUNT(*) AS event_count,
  WINDOWSTART AS session_start,
  WINDOWEND AS session_end,
  (WINDOWEND - WINDOWSTART) / 60000 AS session_duration_minutes
FROM user_events
WINDOW SESSION (30 MINUTES)
GROUP BY user_id
EMIT CHANGES;

-- ============================================================================
-- 5. JOINS
-- ============================================================================

-- Stream-stream join (within time window)
CREATE STREAM orders (
  order_id VARCHAR KEY,
  user_id VARCHAR,
  amount DOUBLE,
  timestamp BIGINT
) WITH (
  KAFKA_TOPIC='orders',
  VALUE_FORMAT='JSON',
  TIMESTAMP='timestamp'
);

CREATE STREAM payments (
  payment_id VARCHAR,
  order_id VARCHAR,
  status VARCHAR,
  timestamp BIGINT
) WITH (
  KAFKA_TOPIC='payments',
  VALUE_FORMAT='JSON',
  TIMESTAMP='timestamp'
);

-- Join orders with payments (within 1 hour)
CREATE STREAM order_payments AS
SELECT
  o.order_id AS order_id,
  o.user_id AS user_id,
  o.amount AS order_amount,
  p.payment_id AS payment_id,
  p.status AS payment_status
FROM orders o
INNER JOIN payments p WITHIN 1 HOUR
ON o.order_id = p.order_id
EMIT CHANGES;

-- Stream-table join (enrichment)
CREATE TABLE users (
  user_id VARCHAR PRIMARY KEY,
  name VARCHAR,
  email VARCHAR,
  tier VARCHAR
) WITH (
  KAFKA_TOPIC='users',
  VALUE_FORMAT='JSON'
);

-- Enrich orders with user data
CREATE STREAM enriched_orders AS
SELECT
  o.order_id,
  o.amount,
  u.name AS user_name,
  u.email AS user_email,
  u.tier AS user_tier
FROM orders o
LEFT JOIN users u ON o.user_id = u.user_id
EMIT CHANGES;

-- Table-table join
CREATE TABLE user_profiles (
  user_id VARCHAR PRIMARY KEY,
  bio VARCHAR,
  avatar_url VARCHAR
) WITH (
  KAFKA_TOPIC='user-profiles',
  VALUE_FORMAT='JSON'
);

CREATE TABLE complete_users AS
SELECT
  u.user_id AS user_id,
  u.name AS name,
  u.email AS email,
  p.bio AS bio,
  p.avatar_url AS avatar
FROM users u
LEFT JOIN user_profiles p ON u.user_id = p.user_id
EMIT CHANGES;

-- ============================================================================
-- 6. ADVANCED FUNCTIONS
-- ============================================================================

-- String functions
CREATE STREAM processed_events AS
SELECT
  user_id,
  CONCAT('User: ', user_id) AS user_label,
  SUBSTRING(user_id, 1, 5) AS user_prefix,
  UCASE(action) AS action_upper,
  LCASE(action) AS action_lower,
  SPLIT(user_id, '-')[1] AS user_number
FROM user_events
EMIT CHANGES;

-- Date/time functions
CREATE STREAM timestamped_events AS
SELECT
  user_id,
  action,
  timestamp,
  FROM_UNIXTIME(timestamp) AS event_datetime,
  TIMESTAMPTOSTRING(timestamp, 'yyyy-MM-dd') AS event_date,
  TIMESTAMPTOSTRING(timestamp, 'HH:mm:ss') AS event_time,
  DATETOSTRING(FROM_UNIXTIME(timestamp), 'EEEE') AS day_of_week
FROM user_events
EMIT CHANGES;

-- Conditional logic
CREATE STREAM categorized_purchases AS
SELECT
  user_id,
  amount,
  CASE
    WHEN amount < 10 THEN 'small'
    WHEN amount < 100 THEN 'medium'
    WHEN amount < 1000 THEN 'large'
    ELSE 'very_large'
  END AS purchase_category,
  IF(amount > 100, 'premium', 'standard') AS customer_type
FROM purchase_events
EMIT CHANGES;

-- ============================================================================
-- 7. EXACTLY-ONCE PROCESSING
-- ============================================================================

-- Enable exactly-once semantics
SET 'processing.guarantee' = 'exactly_once';

-- Create stream with exactly-once
CREATE STREAM deduplicated_events AS
SELECT *
FROM user_events
EMIT CHANGES;

-- ============================================================================
-- 8. PUSH AND PULL QUERIES
-- ============================================================================

-- Push query (continuous, real-time)
SELECT * FROM user_events EMIT CHANGES;

-- Pull query (point-in-time, like SQL)
SELECT * FROM user_event_counts WHERE user_id = 'user123';

-- Pull query with limit
SELECT * FROM user_event_counts LIMIT 10;

-- ============================================================================
-- 9. DATA TYPES AND FORMATS
-- ============================================================================

-- JSON format
CREATE STREAM json_events (
  id VARCHAR,
  data MAP<VARCHAR, VARCHAR>
) WITH (
  KAFKA_TOPIC='json-topic',
  VALUE_FORMAT='JSON'
);

-- Avro format (requires Schema Registry)
CREATE STREAM avro_events (
  id VARCHAR,
  name VARCHAR,
  age INT
) WITH (
  KAFKA_TOPIC='avro-topic',
  VALUE_FORMAT='AVRO'
);

-- Protobuf format
CREATE STREAM protobuf_events (
  id VARCHAR,
  payload STRUCT<field1 VARCHAR, field2 INT>
) WITH (
  KAFKA_TOPIC='protobuf-topic',
  VALUE_FORMAT='PROTOBUF'
);

-- ============================================================================
-- 10. MANAGEMENT COMMANDS
-- ============================================================================

-- Show all streams
SHOW STREAMS;

-- Show all tables
SHOW TABLES;

-- Describe stream
DESCRIBE user_events;

-- Describe table (extended)
DESCRIBE EXTENDED user_event_counts;

-- Show queries
SHOW QUERIES;

-- Terminate query
TERMINATE query_id;

-- Drop stream
DROP STREAM IF EXISTS user_events DELETE TOPIC;

-- Drop table
DROP TABLE IF EXISTS user_event_counts DELETE TOPIC;

-- Explain query (see execution plan)
EXPLAIN query_id;

-- ============================================================================
-- 11. INSERTING DATA
-- ============================================================================

-- Insert values into stream
INSERT INTO user_events (user_id, action, timestamp) VALUES ('user1', 'login', 1698432000000);
INSERT INTO user_events (user_id, action, timestamp) VALUES ('user2', 'signup', 1698432100000);
INSERT INTO user_events (user_id, action, timestamp) VALUES ('user1', 'purchase', 1698432200000);

-- ============================================================================
-- 12. EXPORTING DATA
-- ============================================================================

-- Export aggregated data to new topic
CREATE STREAM user_summary_export AS
SELECT
  user_id,
  event_count,
  actions
FROM user_event_counts
EMIT CHANGES;

-- ============================================================================
-- 13. REAL-TIME ANALYTICS EXAMPLE
-- ============================================================================

-- Real-time dashboard: events per minute
CREATE TABLE events_per_minute AS
SELECT
  action,
  COUNT(*) AS event_count,
  WINDOWSTART AS minute_start
FROM user_events
WINDOW TUMBLING (SIZE 1 MINUTE)
GROUP BY action
EMIT CHANGES;

-- Active users in last 5 minutes
CREATE TABLE active_users_5min AS
SELECT
  COUNT_DISTINCT(user_id) AS active_user_count,
  WINDOWSTART AS window_start
FROM user_events
WINDOW TUMBLING (SIZE 5 MINUTES)
GROUP BY 1
EMIT CHANGES;

-- High-value customers (total purchases > $1000)
CREATE TABLE high_value_customers AS
SELECT
  user_id,
  SUM(amount) AS total_spent,
  COUNT(*) AS purchase_count
FROM purchase_events
GROUP BY user_id
HAVING SUM(amount) > 1000
EMIT CHANGES;

-- ============================================================================
-- END OF EXAMPLES
-- ============================================================================

-- Cleanup (optional)
-- DROP STREAM user_events DELETE TOPIC;
-- DROP TABLE user_event_counts DELETE TOPIC;
