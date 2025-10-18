---
name: duckdb-analytics
description: Skill for duckdb analytics
---



# DuckDB Analytics

**Skill**: duckdb-analytics
**Category**: Data/Analytics
**Related**: Python, SQL, Parquet, data pipelines

## When to Use This Skill

### Triggers
- "analyze this dataset"
- "query Parquet files"
- "embedded analytics database"
- "fast SQL on CSV/JSON"
- "convert Pandas to SQL"
- "OLAP queries"
- "aggregate large files"
- "analytical workload"
- "columnar database"
- "serverless analytics"

### Use Cases
- **Ad-hoc analysis**: Query CSV/Parquet files without loading into database
- **ETL pipelines**: Transform data with SQL, export to various formats
- **Data science**: Bridge between Pandas/Polars and SQL analytics
- **Embedded analytics**: Add SQL engine to Python/Node.js applications
- **Data exploration**: Fast aggregations and window functions on large datasets
- **Prototyping**: Replace complex data pipelines with SQL queries
- **Local development**: Test analytics queries before deploying to warehouse

### When NOT to Use
- Need distributed/clustered database (use ClickHouse, Spark)
- Multi-user concurrent writes (use PostgreSQL, MySQL)
- Real-time transactional workload (use PostgreSQL, OLTP database)
- Gigantic datasets (>1TB single-node) (use BigQuery, Snowflake)

---

## Core Concepts

### Architecture

**In-Process Embedded Database**:
```
Application Process
├─ DuckDB Engine (embedded library)
├─ Columnar Storage
├─ Vectorized Execution
└─ Direct File Access (Parquet, CSV, JSON)

NO separate server process required
```

**Key Characteristics**:
- **Embedded**: Runs inside application process (like SQLite)
- **Columnar**: Stores data in columns (OLAP-optimized)
- **Vectorized**: Processes data in batches (SIMD-accelerated)
- **Zero-copy**: Query files directly without import
- **ACID**: Full transactional support

### Columnar Storage

```
Row-Oriented (OLTP):          Columnar (OLAP):
ID | Name  | Age | City       ID:   [1, 2, 3, 4]
1  | Alice | 30  | NYC        Name: ['Alice', 'Bob', ...]
2  | Bob   | 25  | LA         Age:  [30, 25, 28, 35]
3  | Carol | 28  | SF         City: ['NYC', 'LA', 'SF', ...]

Access pattern: Full rows      Access pattern: Specific columns
Use case: CRUD operations      Use case: Aggregations, analytics
```

**Benefits**:
- Better compression (similar values grouped)
- Faster aggregations (scan only needed columns)
- Efficient analytics (skip irrelevant columns)

### SQL Dialect

**PostgreSQL-Compatible**:
- Standard SQL-92/99/2003 features
- Window functions, CTEs, LATERAL joins
- JSON operators, full-text search
- Array/struct types, nested data
- Extensions via SQL (like PostgreSQL)

---

## Patterns

### Installation & Setup

```bash
# Python
pip install duckdb
# or with uv
uv add duckdb

# CLI
brew install duckdb
# or
curl -OL https://github.com/duckdb/duckdb/releases/latest/download/duckdb_cli-linux-amd64.zip
unzip duckdb_cli-linux-amd64.zip
```

### Pattern 1: Direct File Querying

**Query CSV Without Import**:
```sql
-- No CREATE TABLE needed!
SELECT city, COUNT(*), AVG(age)
FROM 'data/users.csv'
GROUP BY city
ORDER BY COUNT(*) DESC;
```

**Query Parquet Files**:
```sql
-- Single file
SELECT * FROM 'sales.parquet' WHERE year = 2024;

-- Multiple files (glob pattern)
SELECT product_id, SUM(revenue)
FROM 'sales/*.parquet'
GROUP BY product_id;

-- S3/HTTP files (requires httpfs extension)
INSTALL httpfs;
LOAD httpfs;

SELECT * FROM 's3://mybucket/data/*.parquet'
WHERE date >= '2024-01-01';
```

**Query JSON/JSONL**:
```sql
-- JSON array
SELECT * FROM 'data.json';

-- JSON Lines (newline-delimited)
SELECT event_type, COUNT(*)
FROM read_json_auto('events.jsonl')
GROUP BY event_type;
```

### Pattern 2: Python Integration

**Basic Usage**:
```python
import duckdb

# In-memory database
con = duckdb.connect()

# Persistent database
con = duckdb.connect('analytics.db')

# Execute query
result = con.execute("SELECT 42 AS answer").fetchall()
print(result)  # [(42,)]

# Fetch as DataFrame
df = con.execute("SELECT * FROM 'data.csv'").df()
```

**Query Pandas DataFrames Directly**:
```python
import pandas as pd
import duckdb

# Create DataFrame
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Carol'],
    'age': [30, 25, 28],
    'city': ['NYC', 'LA', 'SF']
})

# Query DataFrame as if it's a table
result = duckdb.query("""
    SELECT city, AVG(age) as avg_age
    FROM df
    GROUP BY city
""").df()

print(result)
```

**Pandas/Polars/Arrow Integration**:
```python
import duckdb
import pandas as pd
import polars as pl

# Pandas
df_pandas = pd.read_csv('data.csv')
result = duckdb.query("SELECT * FROM df_pandas WHERE age > 25").df()

# Polars
df_polars = pl.read_csv('data.csv')
result = duckdb.query("SELECT * FROM df_polars WHERE age > 25").pl()

# Arrow
result_arrow = duckdb.query("SELECT * FROM 'data.parquet'").arrow()
```

### Pattern 3: ETL and Transformations

**Load Data**:
```python
import duckdb

con = duckdb.connect('warehouse.db')

# Create table from CSV
con.execute("""
    CREATE TABLE users AS
    SELECT * FROM read_csv_auto('users.csv')
""")

# Create table from Parquet
con.execute("""
    CREATE TABLE sales AS
    SELECT * FROM 'sales.parquet'
""")

# Create table from DataFrame
import pandas as pd
df = pd.read_json('events.json')
con.execute("CREATE TABLE events AS SELECT * FROM df")
```

**Export Data**:
```python
# Export to Parquet
con.execute("""
    COPY (SELECT * FROM users WHERE active = true)
    TO 'active_users.parquet' (FORMAT PARQUET)
""")

# Export to CSV
con.execute("""
    COPY users TO 'users.csv' (HEADER, DELIMITER ',')
""")

# Export to JSON
con.execute("""
    COPY (SELECT * FROM events WHERE date >= '2024-01-01')
    TO 'recent_events.json' (ARRAY true)
""")
```

**Complex Transformations**:
```python
# Multi-stage ETL
con.execute("""
    -- Stage 1: Clean data
    CREATE TABLE clean_users AS
    SELECT
        LOWER(TRIM(email)) AS email,
        name,
        age,
        created_at::DATE AS signup_date
    FROM 'raw_users.csv'
    WHERE email IS NOT NULL;

    -- Stage 2: Aggregate
    CREATE TABLE user_stats AS
    SELECT
        DATE_TRUNC('month', signup_date) AS month,
        COUNT(*) AS signups,
        AVG(age) AS avg_age
    FROM clean_users
    GROUP BY month
    ORDER BY month;
""")

# Export final result
result = con.execute("SELECT * FROM user_stats").df()
```

### Pattern 4: Advanced Analytics

**Window Functions**:
```sql
SELECT
    user_id,
    order_date,
    amount,
    -- Running total
    SUM(amount) OVER (
        PARTITION BY user_id
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total,
    -- Moving average
    AVG(amount) OVER (
        PARTITION BY user_id
        ORDER BY order_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS moving_avg_7d,
    -- Rank within partition
    ROW_NUMBER() OVER (
        PARTITION BY user_id
        ORDER BY amount DESC
    ) AS amount_rank
FROM orders;
```

**CTEs and Complex Queries**:
```sql
WITH monthly_sales AS (
    SELECT
        DATE_TRUNC('month', order_date) AS month,
        product_id,
        SUM(quantity) AS units_sold,
        SUM(revenue) AS total_revenue
    FROM sales
    GROUP BY month, product_id
),
ranked_products AS (
    SELECT
        month,
        product_id,
        total_revenue,
        ROW_NUMBER() OVER (
            PARTITION BY month
            ORDER BY total_revenue DESC
        ) AS revenue_rank
    FROM monthly_sales
)
SELECT
    month,
    product_id,
    total_revenue,
    revenue_rank
FROM ranked_products
WHERE revenue_rank <= 10
ORDER BY month DESC, revenue_rank;
```

**Pivot and Unpivot**:
```sql
-- Pivot
PIVOT (
    SELECT category, year, revenue
    FROM sales
) ON year
USING SUM(revenue);

-- Unpivot
UNPIVOT (
    SELECT * FROM quarterly_sales
) ON q1, q2, q3, q4
INTO NAME quarter VALUE revenue;
```

### Pattern 5: Extensions

**Installing Extensions**:
```sql
-- HTTP/S3 file access
INSTALL httpfs;
LOAD httpfs;

-- PostgreSQL scanner
INSTALL postgres_scanner;
LOAD postgres_scanner;

-- Spatial/GIS
INSTALL spatial;
LOAD spatial;

-- Full-text search
INSTALL fts;
LOAD fts;

-- Excel files
INSTALL spatial;  -- Includes Excel support
LOAD spatial;
```

**Using Extensions**:
```python
import duckdb

con = duckdb.connect()

# Read from PostgreSQL
con.execute("INSTALL postgres_scanner")
con.execute("LOAD postgres_scanner")

result = con.execute("""
    SELECT * FROM postgres_scan(
        'host=localhost port=5432 dbname=mydb user=user password=pass',
        'public',
        'users'
    )
""").df()

# Read from S3
con.execute("INSTALL httpfs")
con.execute("LOAD httpfs")
con.execute("""
    SET s3_access_key_id='YOUR_KEY';
    SET s3_secret_access_key='YOUR_SECRET';
""")

df = con.execute("SELECT * FROM 's3://bucket/data.parquet'").df()

# Spatial queries
con.execute("INSTALL spatial")
con.execute("LOAD spatial")

con.execute("""
    SELECT
        city,
        ST_Distance(
            ST_Point(lon, lat),
            ST_Point(-74.006, 40.7128)  -- NYC coordinates
        ) AS distance_from_nyc
    FROM cities
    ORDER BY distance_from_nyc
    LIMIT 10;
""")
```

### Pattern 6: Performance Optimization

**Persistent Database with Indexes**:
```python
import duckdb

con = duckdb.connect('analytics.db')

# Create table
con.execute("""
    CREATE TABLE events (
        event_id INTEGER,
        user_id INTEGER,
        event_type VARCHAR,
        timestamp TIMESTAMP,
        data JSON
    )
""")

# Load data
con.execute("INSERT INTO events SELECT * FROM 'events.parquet'")

# Create indexes (ART - Adaptive Radix Tree)
con.execute("CREATE INDEX idx_user ON events(user_id)")
con.execute("CREATE INDEX idx_timestamp ON events(timestamp)")
```

**Query Optimization**:
```python
# Use EXPLAIN to analyze query plan
plan = con.execute("EXPLAIN SELECT * FROM events WHERE user_id = 123").fetchall()
print(plan)

# Use PRAGMA for optimization settings
con.execute("PRAGMA threads=8")  # Use 8 threads
con.execute("PRAGMA memory_limit='4GB'")  # Set memory limit
```

**Partitioned Data**:
```sql
-- Export partitioned by date
COPY (SELECT * FROM events)
TO 'events_partitioned'
(FORMAT PARQUET, PARTITION_BY (DATE_TRUNC('day', timestamp)));

-- Query specific partitions
SELECT * FROM 'events_partitioned/timestamp=2024-01-*/*.parquet';
```

### Pattern 7: WASM/Browser Deployment

**DuckDB in Browser**:
```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@latest/dist/duckdb-mvp.wasm.js"></script>
</head>
<body>
    <script type="module">
        import * as duckdb from 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@latest/dist/duckdb-mvp.wasm.js';

        const WASM_URL = 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@latest/dist/duckdb-mvp.wasm';
        const worker = new Worker('duckdb-browser.worker.js');
        const logger = new duckdb.ConsoleLogger();
        const db = new duckdb.AsyncDuckDB(logger, worker);
        await db.instantiate(WASM_URL);

        const conn = await db.connect();

        // Query CSV from URL
        await conn.query(`
            SELECT * FROM 'https://example.com/data.csv'
            LIMIT 10
        `);

        const result = await conn.query(`
            SELECT COUNT(*) as count FROM 'https://example.com/data.csv'
        `);
        console.log(result.toArray());
    </script>
</body>
</html>
```

### Pattern 8: Full-Text Search

```python
import duckdb

con = duckdb.connect()
con.execute("INSTALL fts")
con.execute("LOAD fts")

# Create FTS index
con.execute("""
    CREATE TABLE documents (
        id INTEGER,
        title VARCHAR,
        content VARCHAR
    )
""")

con.execute("INSERT INTO documents VALUES (1, 'DuckDB Guide', 'DuckDB is an analytics database')")
con.execute("INSERT INTO documents VALUES (2, 'SQL Tutorial', 'Learn SQL with examples')")

# Create full-text search index
con.execute("""
    PRAGMA create_fts_index('documents', 'id', 'title', 'content')
""")

# Search
results = con.execute("""
    SELECT * FROM (
        SELECT *, fts_main_documents.match_bm25(id, 'analytics') AS score
        FROM documents
    ) sq
    WHERE score IS NOT NULL
    ORDER BY score DESC
""").fetchall()
```

---

## Quick Reference

### CLI Commands

```bash
# Start interactive shell
duckdb

# Open database file
duckdb analytics.db

# Execute query and exit
duckdb -c "SELECT * FROM 'data.csv'" analytics.db

# Run SQL file
duckdb analytics.db < script.sql

# Export to CSV
duckdb -c "COPY (SELECT * FROM table) TO 'output.csv' (HEADER)" analytics.db
```

### Python API

```python
import duckdb

# Connect
con = duckdb.connect()  # In-memory
con = duckdb.connect('file.db')  # Persistent

# Execute
con.execute("SELECT 42")
result = con.execute("SELECT * FROM table").fetchall()
df = con.execute("SELECT * FROM table").df()  # Pandas
pl_df = con.execute("SELECT * FROM table").pl()  # Polars
arrow = con.execute("SELECT * FROM table").arrow()  # Arrow

# Query shorthand
duckdb.query("SELECT * FROM df").df()  # df is Pandas DataFrame

# Close
con.close()
```

### Common Functions

```sql
-- Date/Time
DATE_TRUNC('month', timestamp_col)
EXTRACT(year FROM date_col)
AGE(end_date, start_date)

-- String
CONCAT(str1, str2)
LOWER(str), UPPER(str)
REGEXP_MATCHES(str, pattern)

-- Aggregate
COUNT(*), SUM(col), AVG(col), MIN(col), MAX(col)
STDDEV(col), VARIANCE(col)
STRING_AGG(col, ',')  -- Concatenate strings
ARRAY_AGG(col)  -- Collect into array

-- Window
ROW_NUMBER(), RANK(), DENSE_RANK()
LAG(col, 1), LEAD(col, 1)
FIRST_VALUE(col), LAST_VALUE(col)

-- JSON
json_col->'key'  -- Extract JSON field
json_col->>'key'  -- Extract as text
JSON_EXTRACT(json_col, '$.path')
```

### Data Import/Export

```sql
-- CSV
CREATE TABLE t AS SELECT * FROM read_csv_auto('file.csv');
COPY table TO 'output.csv' (HEADER, DELIMITER ',');

-- Parquet
CREATE TABLE t AS SELECT * FROM 'file.parquet';
COPY table TO 'output.parquet' (FORMAT PARQUET);

-- JSON
CREATE TABLE t AS SELECT * FROM read_json_auto('file.json');
COPY table TO 'output.json' (ARRAY true);

-- Excel
INSTALL spatial;
LOAD spatial;
SELECT * FROM st_read('file.xlsx');
```

### Configuration

```sql
-- Threads
PRAGMA threads=8;

-- Memory limit
PRAGMA memory_limit='4GB';

-- Progress bar
PRAGMA enable_progress_bar;

-- Show settings
PRAGMA database_size;
PRAGMA table_info('table_name');
```

---

## Anti-Patterns

### Don't Use DuckDB for OLTP
```python
# WRONG: High-frequency transactional updates
for user_id in range(10000):
    con.execute(f"UPDATE users SET last_active = NOW() WHERE id = {user_id}")

# RIGHT: Use PostgreSQL/MySQL for OLTP, or batch updates
con.execute("""
    UPDATE users
    SET last_active = NOW()
    WHERE id IN (SELECT id FROM active_users)
""")
```

### Don't Import Data Unnecessarily
```sql
-- WRONG: Import before querying
CREATE TABLE data AS SELECT * FROM 'large_file.parquet';
SELECT AVG(value) FROM data;

-- RIGHT: Query directly
SELECT AVG(value) FROM 'large_file.parquet';
```

### Don't Ignore Query Plans
```python
# WRONG: Run slow query without investigation
result = con.execute("SELECT * FROM huge_table WHERE col = 'value'").fetchall()

# RIGHT: Analyze and optimize
plan = con.execute("EXPLAIN SELECT * FROM huge_table WHERE col = 'value'").fetchall()
# Create index if needed
con.execute("CREATE INDEX idx_col ON huge_table(col)")
```

### Don't Mix Multiple Connections Unsafely
```python
# WRONG: Multiple connections to same file without coordination
con1 = duckdb.connect('db.db')
con2 = duckdb.connect('db.db')
con1.execute("INSERT INTO table VALUES (1)")
con2.execute("INSERT INTO table VALUES (2)")  # Potential conflict

# RIGHT: Use single connection or read-only mode
con = duckdb.connect('db.db')
# Or
con_readonly = duckdb.connect('db.db', read_only=True)
```

### Don't Forget to Close Connections
```python
# WRONG: Leave connections open
con = duckdb.connect('file.db')
con.execute("SELECT * FROM table")
# ... never close

# RIGHT: Use context manager
with duckdb.connect('file.db') as con:
    result = con.execute("SELECT * FROM table").df()
```

### Don't Use SELECT * in Production
```sql
-- WRONG: Fetch unnecessary columns
SELECT * FROM 'huge_file.parquet' WHERE id = 123;

-- RIGHT: Select only needed columns (columnar optimization)
SELECT id, name, email FROM 'huge_file.parquet' WHERE id = 123;
```

---

## Related Skills

- **python** - DuckDB Python API integration
- **sql** - SQL fundamentals, query optimization
- **pandas-data-analysis** - DataFrame integration patterns
- **parquet-columnar** - Parquet file format, columnar storage
- **modal-functions-basics** - Deploy DuckDB analytics on Modal
- **data-pipeline-design** - ETL patterns, data workflows
- **postgresql** - PostgreSQL scanner, SQL compatibility
- **arrow-interop** - Apache Arrow integration

---

## Examples

### Example 1: Sales Analytics Pipeline
```python
import duckdb
import pandas as pd

# Connect to persistent database
con = duckdb.connect('sales_analytics.db')

# Load raw data from multiple sources
con.execute("""
    CREATE OR REPLACE TABLE raw_sales AS
    SELECT * FROM 's3://mybucket/sales/*.parquet'
""")

con.execute("""
    CREATE OR REPLACE TABLE raw_customers AS
    SELECT * FROM postgres_scan(
        'host=db.example.com dbname=prod',
        'public',
        'customers'
    )
""")

# Transform and aggregate
con.execute("""
    CREATE OR REPLACE TABLE sales_summary AS
    WITH daily_sales AS (
        SELECT
            s.customer_id,
            c.customer_name,
            c.segment,
            DATE_TRUNC('day', s.order_date) AS sale_date,
            SUM(s.amount) AS daily_revenue,
            COUNT(*) AS num_orders
        FROM raw_sales s
        JOIN raw_customers c ON s.customer_id = c.id
        GROUP BY s.customer_id, c.customer_name, c.segment, sale_date
    )
    SELECT
        customer_id,
        customer_name,
        segment,
        sale_date,
        daily_revenue,
        num_orders,
        SUM(daily_revenue) OVER (
            PARTITION BY customer_id
            ORDER BY sale_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_revenue
    FROM daily_sales
    ORDER BY customer_id, sale_date
""")

# Export results
con.execute("""
    COPY sales_summary TO 'sales_summary.parquet' (FORMAT PARQUET)
""")

# Get insights as DataFrame for visualization
insights = con.execute("""
    SELECT
        segment,
        COUNT(DISTINCT customer_id) AS customers,
        SUM(daily_revenue) AS total_revenue,
        AVG(daily_revenue) AS avg_daily_revenue
    FROM sales_summary
    GROUP BY segment
    ORDER BY total_revenue DESC
""").df()

print(insights)
```

### Example 2: Log Analysis
```python
import duckdb

con = duckdb.connect()

# Query logs directly (JSON Lines format)
con.execute("""
    CREATE VIEW parsed_logs AS
    SELECT
        timestamp::TIMESTAMP AS ts,
        level,
        message,
        user_id,
        request_path
    FROM read_json_auto('logs/*.jsonl')
    WHERE timestamp IS NOT NULL
""")

# Find error patterns
errors = con.execute("""
    SELECT
        DATE_TRUNC('hour', ts) AS hour,
        level,
        COUNT(*) AS count,
        STRING_AGG(DISTINCT request_path, ', ') AS paths
    FROM parsed_logs
    WHERE level IN ('ERROR', 'CRITICAL')
    GROUP BY hour, level
    ORDER BY hour DESC, count DESC
    LIMIT 20
""").df()

print("Error Summary:")
print(errors)

# User activity analysis
activity = con.execute("""
    SELECT
        user_id,
        COUNT(*) AS requests,
        COUNT(DISTINCT request_path) AS unique_paths,
        MIN(ts) AS first_seen,
        MAX(ts) AS last_seen
    FROM parsed_logs
    WHERE user_id IS NOT NULL
    GROUP BY user_id
    HAVING requests > 100
    ORDER BY requests DESC
    LIMIT 10
""").df()

print("\nTop Active Users:")
print(activity)
```

---

**End of Skill: duckdb-analytics**
