# PostgreSQL Query Optimization Scripts

This directory contains executable scripts for analyzing, optimizing, and benchmarking PostgreSQL queries.

## Scripts Overview

### analyze_query.py
Parses EXPLAIN ANALYZE output and provides actionable optimization suggestions.

**Usage**:
```bash
# Analyze from file
python analyze_query.py --explain-file explain_output.txt

# Analyze from stdin
cat explain.txt | python analyze_query.py --stdin

# JSON output
python analyze_query.py --explain-file explain.txt --json

# Analyze query directly (requires psycopg2)
python analyze_query.py --query "SELECT * FROM users WHERE email = 'foo@example.com'" --connection "postgresql://localhost/mydb"
```

**Features**:
- Detects sequential scans on large tables
- Identifies row estimate mismatches (stale statistics)
- Finds inefficient filters removing many rows
- Detects excessive heap fetches in Index Only Scans
- Identifies expensive nested loops
- Provides specific index recommendations

### suggest_indexes.py
Recommends optimal indexes based on query patterns (WHERE, JOIN, ORDER BY clauses).

**Usage**:
```bash
# Analyze single query
python suggest_indexes.py --query "SELECT * FROM users WHERE email = 'foo@example.com' ORDER BY created_at"

# Analyze queries from file
python suggest_indexes.py --query-file queries.sql

# JSON output
python suggest_indexes.py --query "SELECT * FROM users WHERE status = 'active'" --json

# Analyze workload from pg_stat_statements (requires psycopg2)
python suggest_indexes.py --connection "postgresql://localhost/mydb" --analyze-workload
```

**Features**:
- Parses WHERE, JOIN, and ORDER BY clauses
- Recommends composite indexes for multi-column queries
- Suggests covering indexes (with INCLUDE) for Index Only Scans
- Prioritizes recommendations by impact
- Deduplicates redundant index suggestions
- Analyzes entire workload from pg_stat_statements

### benchmark_queries.sh
Benchmarks query performance with statistical analysis.

**Usage**:
```bash
# Benchmark single query
./benchmark_queries.sh --query "SELECT * FROM users WHERE id = 123" --iterations 20

# Benchmark from file
./benchmark_queries.sh --query-file query.sql

# Compare before/after optimization
./benchmark_queries.sh --compare slow_query.sql fast_query.sql

# JSON output
./benchmark_queries.sh --query "SELECT COUNT(*) FROM orders" --json --connection "postgresql://localhost/mydb"
```

**Features**:
- Runs warmup iterations to prime cache
- Reports mean, median, min, max, and standard deviation
- Compares two queries and calculates improvement percentage
- JSON output for CI/CD integration

## Prerequisites

### Python Dependencies
```bash
# For analyze_query.py and suggest_indexes.py
pip install psycopg2-binary  # Optional, for direct database queries

# Or using uv
uv pip install psycopg2-binary
```

### System Tools
```bash
# PostgreSQL client tools (required for benchmark_queries.sh)
# Ubuntu/Debian
sudo apt-get install postgresql-client

# macOS
brew install postgresql

# jq (required for benchmark_queries.sh)
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq
```

## Workflow Examples

### Example 1: Analyze Slow Query

```bash
# Step 1: Get EXPLAIN output
psql mydb -c "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE user_id = 123" > explain.txt

# Step 2: Analyze for issues
python analyze_query.py --explain-file explain.txt

# Output:
# ================================================================================
# PostgreSQL Query Analysis
# ================================================================================
#
# Metrics:
#   Total Cost: 1234.56
#   Total Time: 123.45 ms
#   Total Rows: 9,998
#   Sequential Scans: 1
#   Index Scans: 0
#
# Issues Found:
#
#   [HIGH] Sequential scan on large table orders (9,998 rows)
#
# Suggestions:
#
#   1. Consider creating an index on orders for WHERE/JOIN conditions
#      Example: CREATE INDEX idx_orders_user_id ON orders(user_id);
#
# ================================================================================
```

### Example 2: Get Index Recommendations

```bash
# Analyze query
python suggest_indexes.py --query "SELECT id, total, created_at FROM orders WHERE user_id = 123 AND status = 'pending' ORDER BY created_at DESC"

# Output:
# ================================================================================
# PostgreSQL Index Recommendations
# ================================================================================
#
# Found 1 index recommendation(s):
#
# HIGH PRIORITY:
#
#   1. Table: orders
#      Columns: user_id, status, created_at
#      Reason: Optimize WHERE clause on user_id, status and ORDER BY created_at
#      Include: id, total (covering index)
#      SQL: CREATE INDEX idx_orders_user_id_status_created_at ON orders(user_id, status, created_at) INCLUDE (id, total);
#
# ================================================================================
```

### Example 3: Benchmark Before/After Optimization

```bash
# Create query files
echo "SELECT * FROM orders WHERE user_id = 123" > before.sql
echo "SELECT * FROM orders WHERE user_id = 123" > after.sql

# Create the recommended index
psql mydb -c "CREATE INDEX idx_orders_user_id ON orders(user_id);"

# Benchmark comparison
./benchmark_queries.sh --compare before.sql after.sql --iterations 20

# Output:
# ================================================================================
# Query Comparison Results
# ================================================================================
#
# BEFORE (Query 1):
#   Mean: 125.34ms
#
# AFTER (Query 2):
#   Mean: 2.45ms
#
# Improvement: 98.05% faster (51.16x speedup)
#
# ================================================================================
```

### Example 4: Full Optimization Workflow

```bash
# 1. Get slow query from pg_stat_statements
psql mydb -c "SELECT query FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 1" -t > slow_query.sql

# 2. Analyze query for issues
psql mydb -c "EXPLAIN (ANALYZE, BUFFERS) $(cat slow_query.sql)" | python analyze_query.py --stdin

# 3. Get index recommendations
python suggest_indexes.py --query-file slow_query.sql

# 4. Create recommended indexes
psql mydb -c "CREATE INDEX idx_orders_user_id ON orders(user_id);"

# 5. Benchmark improvement
./benchmark_queries.sh --query-file slow_query.sql --iterations 20
```

### Example 5: Analyze Entire Workload

```bash
# Requires pg_stat_statements extension
psql mydb -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# Analyze top queries and get recommendations
python suggest_indexes.py --connection "postgresql://localhost/mydb" --analyze-workload --json > recommendations.json

# Review recommendations
cat recommendations.json | jq '.[] | select(.priority == 1) | .example_sql'
```

## Output Formats

All scripts support JSON output for easy integration with CI/CD pipelines and monitoring dashboards.

```bash
# JSON output
python analyze_query.py --explain-file explain.txt --json
python suggest_indexes.py --query "SELECT ..." --json
./benchmark_queries.sh --query "SELECT ..." --json
```

## CI/CD Integration

```yaml
# .github/workflows/query-optimization.yml
name: Query Optimization Check

on: [pull_request]

jobs:
  analyze-queries:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Analyze query performance
        run: |
          python analyze_query.py --explain-file tests/explain_output.txt --json > analysis.json
          # Fail if high-severity issues found
          if jq -e '.issues[] | select(.severity == "high")' analysis.json > /dev/null; then
            echo "High-severity query issues detected"
            exit 1
          fi
```

## Safety Notes

**IMPORTANT**:

1. **EXPLAIN ANALYZE executes queries**: Use with caution on production databases, especially for writes (INSERT/UPDATE/DELETE).

2. **Test indexes in staging first**: Always test index creation in a staging environment before production.

3. **Monitor index usage**: Unused indexes slow down writes. Drop indexes that aren't being used.

4. **Connection strings**: Protect database credentials. Use environment variables or secret management.

5. **Benchmark in production-like environment**: Query performance depends on data volume and distribution.

## Troubleshooting

### Error: psycopg2 not found

```bash
pip install psycopg2-binary
# or
uv pip install psycopg2-binary
```

### Error: jq not found

```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq
```

### Error: Connection refused

Check that PostgreSQL is running and connection string is correct:

```bash
psql "postgresql://localhost/mydb" -c "SELECT version();"
```

### Error: pg_stat_statements not available

Enable the extension:

```sql
-- Add to postgresql.conf
shared_preload_libraries = 'pg_stat_statements'

-- Restart PostgreSQL, then:
CREATE EXTENSION pg_stat_statements;
```

## Related Resources

- [REFERENCE.md](../REFERENCE.md) - Deep dive into EXPLAIN, planner internals, and index types
- [examples/](../examples/) - Example slow queries and optimizations
- Main skill: [postgres-query-optimization.md](../../postgres-query-optimization.md)

---

**Last Updated**: 2025-10-27
