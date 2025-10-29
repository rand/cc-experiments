# Distributed Trace Analysis Workflow

End-to-end workflow for analyzing distributed traces to diagnose performance and reliability issues.

## Overview

This workflow demonstrates how to use distributed tracing to:
1. Identify latency bottlenecks
2. Find error patterns
3. Map service dependencies
4. Optimize critical paths

## Prerequisites

- OpenTelemetry instrumented services
- Traces exported to Jaeger/Zipkin
- analyze_traces.py script from this skill

## Workflow Steps

### Step 1: Identify Issue Scope

**Symptoms:**
- API latency increased from 100ms (p95) to 500ms (p95)
- Error rate increased from 0.1% to 2%
- User complaints about slow response times

**Initial Questions:**
- Is it affecting all requests or specific endpoints?
- Did it start at a specific time?
- Were there recent deployments?

### Step 2: Query Traces

```bash
# Export traces from Jaeger API
curl "http://jaeger:16686/api/traces?service=api-gateway&start=1698336000000000&limit=100" \
  > traces.json

# Or use analyze_traces.py to fetch
./analyze_traces.py traces.json --time-range 1h --verbose
```

### Step 3: Filter to Problematic Traces

```bash
# Filter slow traces (>500ms)
./analyze_traces.py traces.json \
  --latency-threshold 500 \
  --service api-gateway \
  --output slow-traces-analysis.json \
  --json

# Filter error traces
./analyze_traces.py traces.json \
  --errors-only \
  --output error-traces-analysis.json \
  --json
```

**Example Output:**
```json
{
  "summary": {
    "trace_count": 25,
    "error_rate": 100.0,
    "duration_stats": {
      "mean_ms": 1250.5,
      "p95_ms": 2100.0,
      "p99_ms": 3500.0
    }
  }
}
```

### Step 4: Identify Bottlenecks

```bash
# Analyze latency bottlenecks
./analyze_traces.py traces.json \
  --bottlenecks \
  --verbose
```

**Example Output:**
```
Bottlenecks (>20% of trace time):

1. user-service.database_query
   - Duration: 1,850ms (74% of trace)
   - Occurrences: 23/25 traces
   - Pattern: SELECT * FROM users JOIN orders

2. recommendation-service.fetch_recommendations
   - Duration: 650ms (26% of trace)
   - Occurrences: 25/25 traces
   - Pattern: External API call timeout
```

**Analysis:**
- Database query is primary bottleneck (74% of time)
- No index on join columns causing full table scan
- Recommendation service timing out (likely cascade effect)

### Step 5: Analyze Critical Paths

```bash
# Find longest sequential paths
./analyze_traces.py traces.json \
  --critical-path \
  --json
```

**Example Output:**
```json
{
  "critical_paths": [
    {
      "trace_id": "abc123",
      "total_duration_ms": 2500,
      "critical_path_duration_ms": 2450,
      "spans": [
        {"service": "api-gateway", "operation": "handle_request", "duration_ms": 2500},
        {"service": "user-service", "operation": "get_user", "duration_ms": 2200},
        {"service": "user-service", "operation": "database_query", "duration_ms": 2100},
        {"service": "recommendation-service", "operation": "fetch", "duration_ms": 250}
      ]
    }
  ]
}
```

**Insight:**
- Critical path dominated by database query (2100ms / 2500ms = 84%)
- Little parallelization happening
- User service making sequential calls instead of parallel

### Step 6: Correlate Errors

```bash
# Analyze error patterns
./analyze_traces.py traces.json \
  --errors \
  --verbose
```

**Example Output:**
```
Error Analysis:

Error Rate: 8% (8/100 traces)

Top Error Patterns:
1. recommendation-service: "Connection timeout" (6 occurrences, 75%)
2. user-service: "Database query timeout" (2 occurrences, 25%)

Errors by Service:
- recommendation-service: 6 errors
  - Connection timeout: 6 (100%)
  - Example traces: trace-001, trace-002, trace-003

- user-service: 2 errors
  - Database query timeout: 2 (100%)
  - Example traces: trace-010, trace-015
```

**Insight:**
- Slow database queries causing cascading timeouts
- Recommendation service timing out waiting for user-service
- Need to address root cause (database performance)

### Step 7: Map Service Dependencies

```bash
# Build dependency graph
./analyze_traces.py traces.json \
  --dependencies \
  --json
```

**Example Output:**
```json
{
  "dependencies": {
    "services": {
      "api-gateway": {
        "call_count": 100,
        "avg_duration_ms": 1250.5,
        "error_rate": 8.0
      },
      "user-service": {
        "call_count": 100,
        "avg_duration_ms": 1150.0,
        "error_rate": 10.0
      },
      "recommendation-service": {
        "call_count": 85,
        "avg_duration_ms": 350.0,
        "error_rate": 7.0
      }
    },
    "dependencies": {
      "api-gateway": {
        "user-service": 100,
        "recommendation-service": 85
      },
      "user-service": {
        "database": 100
      }
    }
  }
}
```

**Insight:**
- Linear dependency chain: gateway -> user-service -> database
- No parallel execution opportunities being used
- High error rates in user-service affecting downstream

### Step 8: Diagnose Root Cause

Based on analysis:

1. **Root Cause**: Inefficient database query
   - Missing index on `users.id` and `orders.user_id` join
   - Query scanning full tables (millions of rows)
   - Causing 2+ second latency

2. **Cascade Effect**:
   - Slow database → slow user-service
   - Slow user-service → timeouts in recommendation-service
   - Timeouts → increased error rate

3. **Missing Optimization**:
   - User data and recommendations fetched sequentially
   - Could be parallelized to save time

### Step 9: Implement Fixes

**Fix 1: Add Database Index**
```sql
-- Add composite index for join
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- Add covering index if possible
CREATE INDEX idx_users_orders ON users(id) INCLUDE (name, email);
```

**Fix 2: Parallelize Calls**
```python
# Before: Sequential
user = get_user(user_id)  # 2000ms
recommendations = get_recommendations(user_id)  # 200ms
# Total: 2200ms

# After: Parallel
import asyncio

async def get_user_data(user_id):
    user, recommendations = await asyncio.gather(
        get_user_async(user_id),
        get_recommendations_async(user_id)
    )
    return user, recommendations

# Total: max(2000ms, 200ms) = 2000ms
# Savings: 200ms
```

**Fix 3: Add Caching**
```python
from functools import lru_cache

@lru_cache(maxsize=10000)
def get_user(user_id):
    # Cache user data for 5 minutes
    return fetch_from_database(user_id)
```

**Fix 4: Add Timeouts and Circuit Breakers**
```python
# Add timeout to prevent cascade
@timeout(seconds=1.0)
def get_recommendations(user_id):
    try:
        return recommendation_service.fetch(user_id)
    except TimeoutError:
        # Return defaults instead of propagating error
        return default_recommendations()
```

### Step 10: Verify Fix

**After deploying fixes, reanalyze:**

```bash
# Capture new traces
curl "http://jaeger:16686/api/traces?service=api-gateway&start=1698340000000000&limit=100" \
  > traces-after-fix.json

# Compare
./analyze_traces.py traces-after-fix.json --verbose
```

**Results:**
```
Summary:
- Trace count: 100
- Error rate: 0.5% (down from 8%)
- Mean duration: 250ms (down from 1,250ms)
- P95 duration: 380ms (down from 2,100ms)
- P99 duration: 450ms (down from 3,500ms)

Bottlenecks:
- user-service.database_query: 150ms (60% of trace)
  - Improved from 1,850ms (88% reduction)
  - Index working as expected

- recommendation-service: 80ms (32% of trace)
  - Improved from 650ms (87% reduction)
  - Parallel execution reducing impact
```

**Verification:**
- ✅ Latency reduced by 80% (1,250ms → 250ms)
- ✅ Error rate reduced by 93% (8% → 0.5%)
- ✅ Database query 88% faster (index effective)
- ✅ No more timeout cascades

### Step 11: Monitor for Regressions

Set up alerts:

```yaml
# Prometheus alert rules
groups:
  - name: trace_performance
    rules:
      - alert: HighTraceLatency
        expr: histogram_quantile(0.95, sum(rate(trace_duration_ms_bucket[5m])) by (le, service)) > 500
        for: 5m
        annotations:
          summary: "High trace latency detected"

      - alert: HighErrorRate
        expr: sum(rate(trace_errors_total[5m])) by (service) / sum(rate(trace_total[5m])) by (service) > 0.02
        for: 5m
        annotations:
          summary: "High trace error rate detected"
```

---

## Key Takeaways

1. **Use Traces to Find Root Cause**
   - Bottleneck analysis identifies where time is spent
   - Critical path shows sequential dependencies
   - Error correlation reveals cascade effects

2. **Optimize Based on Data**
   - Focus on highest impact bottlenecks first
   - Consider both reducing latency and parallelizing
   - Add caching for frequently accessed data

3. **Prevent Cascades**
   - Use timeouts on all external calls
   - Implement circuit breakers
   - Have fallback/default responses

4. **Verify and Monitor**
   - Re-analyze traces after fixes
   - Set up alerts for regressions
   - Continuously monitor trends

## Tools Used

- `analyze_traces.py`: Automated trace analysis
- Jaeger API: Trace collection and querying
- Database EXPLAIN: Query optimization
- Metrics dashboards: Verification

## Related Resources

- OpenTelemetry documentation
- Jaeger UI for visual analysis
- Database slow query logs
- Service dependency graphs
