# Runbook: Database Connection Pool Exhausted

**Service**: API Service
**Component**: Database Layer
**Owner**: Database Team (@database-team)
**Last Updated**: 2025-10-27
**Severity**: Usually SEV-2, can escalate to SEV-1

---

## Overview

This runbook covers diagnosis and mitigation when the database connection pool is exhausted, preventing the application from acquiring new database connections.

## Symptoms

### Alerts
- **Alert Name**: `DatabaseConnectionPoolHigh`
- **Condition**: Connection pool utilization > 85%
- **Alert Name**: `DatabaseConnectionPoolExhausted`
- **Condition**: Connection pool at 100% capacity for > 2 minutes

### User-Visible Symptoms
- API requests timing out
- "Service Unavailable" (503) errors
- Login failures
- Slow page loads (> 10 seconds)
- Database transaction failures

### Metric Thresholds
- Connection pool active connections: >= max_connections
- Connection pool wait time: > 5 seconds
- Application error rate: > 5% with database connection errors
- API latency p95: > 5000ms

### Log Patterns
```
ERROR: Could not acquire connection from pool
ERROR: Timeout waiting for database connection
WARN: Connection pool exhausted, waiting for available connection
ERROR: FATAL: sorry, too many clients already
```

## Impact

### User-Facing Features Affected
- All features requiring database access
- Login/authentication
- Data reads and writes
- Transaction processing

### Business Processes Impacted
- Payment processing may fail
- User registration blocked
- Order processing delayed
- Real-time data sync stopped

### Dependencies Affected
- API service (primary)
- Background workers (may be blocked)
- Reporting service (read replicas may help)

## Diagnosis

### Step 1: Verify Pool Exhaustion

```bash
# Check application metrics
curl http://api.example.com:9090/metrics | grep -E 'connection_pool_(active|idle|max)'

# Expected output showing exhaustion:
# connection_pool_active 100
# connection_pool_idle 0
# connection_pool_max 100

# Check via database directly (PostgreSQL)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
  SELECT count(*) as active_connections,
         current_setting('max_connections')::int as max_connections
  FROM pg_stat_activity
  WHERE state = 'active';
"

# If active_connections >= max_connections * 0.9, pool is near exhaustion
```

### Step 2: Identify Long-Running Queries

```sql
-- PostgreSQL: Find long-running queries
SELECT
  pid,
  now() - query_start AS duration,
  state,
  query,
  client_addr
FROM pg_stat_activity
WHERE state = 'active'
  AND query_start < now() - interval '5 minutes'
ORDER BY duration DESC
LIMIT 20;

-- MySQL: Find long-running queries
SELECT
  id,
  user,
  host,
  db,
  command,
  time,
  state,
  info
FROM information_schema.processlist
WHERE command != 'Sleep'
  AND time > 300  -- 5 minutes
ORDER BY time DESC
LIMIT 20;
```

### Step 3: Check for Connection Leaks

```bash
# Check application logs for unclosed connections
kubectl logs -l app=api-service --tail=1000 | \
  grep -i "connection.*not.*closed\|connection.*leak"

# Check connection acquire/release patterns
# Look for imbalance (more acquires than releases)
kubectl logs -l app=api-service --tail=10000 | \
  grep -E "acquired|released" | \
  awk '{print $5}' | sort | uniq -c

# Check specific endpoints holding connections
curl http://api.example.com:9090/metrics | \
  grep -E 'connection_pool_active.*endpoint'
```

### Step 4: Identify Traffic Patterns

```bash
# Check if traffic spike correlates with pool exhaustion
curl "http://prometheus:9090/api/v1/query?query=rate(http_requests_total[5m])"

# Check for slow queries correlating with pool pressure
curl "http://prometheus:9090/api/v1/query?query=rate(database_query_duration_seconds_sum[5m])"

# Check for specific endpoint causing issues
curl http://api.example.com:9090/metrics | \
  grep -E 'http_requests.*duration' | \
  awk '{print $1, $2}' | sort -k2 -rn | head -10
```

## Mitigation

### Option 1: Kill Long-Running Queries (< 2 minutes)

**When to use**: Long-running queries identified holding connections

```sql
-- PostgreSQL: Kill specific query by PID
SELECT pg_terminate_backend(12345);

-- Kill all queries running > 5 minutes (be careful!)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'active'
  AND query_start < now() - interval '5 minutes'
  AND query NOT LIKE '%pg_stat_activity%'  -- Don't kill this query
  AND query NOT LIKE '%VACUUM%';           -- Preserve maintenance

-- Verify connections freed
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
```

```sql
-- MySQL: Kill specific query
KILL 12345;

-- Kill long-running queries
SELECT CONCAT('KILL ', id, ';') AS kill_command
FROM information_schema.processlist
WHERE command != 'Sleep'
  AND time > 300
  AND user != 'system user'
INTO OUTFILE '/tmp/kill_commands.sql';

SOURCE /tmp/kill_commands.sql;
```

**Expected Result**: Connection pool utilization should drop within 30 seconds

### Option 2: Increase Pool Size (< 5 minutes)

**When to use**: Pool size insufficient for legitimate traffic

```bash
# Temporary increase via environment variable
kubectl set env deployment/api-service DB_POOL_SIZE=200

# Or edit config directly
kubectl edit configmap api-config
# Update: DB_POOL_SIZE: "200"

# Restart to apply
kubectl rollout restart deployment/api-service

# Monitor for improvement
watch 'curl -s http://api.example.com:9090/metrics | grep connection_pool_active'
```

**Caution**: Don't exceed database max_connections. If app pool size * num_replicas > DB max_connections, you'll create a different problem.

```bash
# Check database max_connections
psql -c "SHOW max_connections;"

# Safe pool size calculation:
# app_pool_size * num_app_replicas + buffer < database_max_connections
# Example: 50 * 10 + 100 = 600 < 1000 (safe)
```

### Option 3: Restart Application (< 5 minutes)

**When to use**: Connection leak suspected, forcing pool recreation

```bash
# Rolling restart to avoid downtime
kubectl rollout restart deployment/api-service

# Monitor restart progress
kubectl rollout status deployment/api-service

# Verify connections cleared
psql -c "SELECT count(*) FROM pg_stat_activity WHERE application_name = 'api-service';"

# Check new pool is healthy
curl http://api.example.com:9090/metrics | grep connection_pool
```

**Expected Result**: Connection count should reset to baseline (idle connections only)

### Option 4: Scale Application Horizontally (< 10 minutes)

**When to use**: Legitimate traffic spike, need more capacity

```bash
# Scale up replicas
kubectl scale deployment/api-service --replicas=20

# Monitor distribution of connections
watch 'kubectl get pods -l app=api-service -o wide'

# Verify traffic distributed
for pod in $(kubectl get pods -l app=api-service -o name); do
  echo "$pod: $(kubectl exec $pod -- curl -s localhost:9090/metrics | grep connection_pool_active)"
done
```

**Caution**: Ensure total connection pool capacity doesn't exceed database limits

### Option 5: Optimize Problematic Queries (15-30 minutes)

**When to use**: Specific query pattern identified as slow

```sql
-- Identify expensive queries
SELECT
  queryid,
  calls,
  mean_exec_time,
  query
FROM pg_stat_statements
ORDER BY mean_exec_time * calls DESC
LIMIT 10;

-- Add index if missing
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- Analyze query plan
EXPLAIN ANALYZE
SELECT * FROM users WHERE email = 'user@example.com';
```

### Option 6: Enable Connection Multiplexing (30+ minutes)

**When to use**: Long-term solution, requires config change

```bash
# Deploy PgBouncer in front of database
kubectl apply -f pgbouncer-deployment.yaml

# Update app to connect to PgBouncer instead of direct DB
kubectl set env deployment/api-service \
  DB_HOST=pgbouncer.database.svc.cluster.local \
  DB_PORT=6432

# PgBouncer pools connections effectively
# App can have large pool, PgBouncer maintains smaller pool to DB
```

## Escalation

### When to Escalate

| Condition | Escalate To | Response SLA |
|-----------|-------------|--------------|
| Pool exhaustion persists > 15 min after mitigation | Database Team (@database-team) | 15 minutes |
| Caused by specific query pattern | Team owning that code | 30 minutes |
| Database CPU > 80% | Infrastructure Team (@infra) | 15 minutes |
| Suspected database failure | On-call Manager | Immediate |
| Customer data at risk | Security Team (@security) | Immediate |

### Escalation Commands

```bash
# Page database team
pagerduty incident create \
  --service database-service \
  --title "DB Connection Pool Exhausted" \
  --urgency high \
  --body "Pool at 100%, app unable to acquire connections. Incident: $INCIDENT_ID"

# Page team owning slow query
# (determine from query pattern)
pagerduty incident create \
  --service payments-service \
  --title "Slow payment query exhausting DB pool"
```

## Prevention

### Short-term Actions (1-2 weeks)

- [ ] Add connection pool utilization alerts at 70% (warn) and 85% (critical)
- [ ] Implement query timeouts to prevent long-running queries
- [ ] Add connection leak detection in application (warn if connection held > 30s)
- [ ] Document current pool sizing in runbook

### Medium-term Actions (1 month)

- [ ] Review and optimize top 10 slowest queries
- [ ] Implement connection pooling middleware (PgBouncer/PgPool)
- [ ] Add automated pool size adjustment based on replica count
- [ ] Load test to validate pool sizing under peak traffic

### Long-term Actions (3 months)

- [ ] Implement read replicas for read-heavy queries
- [ ] Add query performance monitoring in APM
- [ ] Review ORM usage for N+1 query patterns
- [ ] Implement circuit breaker for database calls
- [ ] Add automatic remediation (scale app on pool pressure)

### Code Review Checklist

When reviewing database-related code:
- [ ] Connections properly closed in finally blocks or using context managers
- [ ] No long-running queries without timeouts
- [ ] Bulk operations use batching (not one connection per item)
- [ ] Read operations use read replicas where possible
- [ ] Transactions kept as short as possible

### Monitoring Improvements

```yaml
# Prometheus alerts to add
groups:
  - name: database_connection_pool
    rules:
      - alert: DatabaseConnectionPoolHigh
        expr: connection_pool_active / connection_pool_max > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Connection pool utilization high"
          description: "Pool at {{ $value | humanizePercentage }}"

      - alert: DatabaseConnectionPoolExhausted
        expr: connection_pool_active / connection_pool_max > 0.95
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Connection pool nearly exhausted"
          runbook: "https://runbooks.example.com/db-pool-exhausted"

      - alert: DatabaseSlowQueries
        expr: rate(database_query_duration_seconds_sum[5m]) > 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Database queries running slowly"
```

## Related Documentation

### Runbooks
- [Database High CPU](database-high-cpu.md)
- [Application High Latency](application-high-latency.md)
- [Database Replication Lag](database-replication-lag.md)

### Dashboards
- [Database Overview](https://grafana.example.com/d/database-overview)
- [Connection Pool Metrics](https://grafana.example.com/d/connection-pool)
- [Application Performance](https://grafana.example.com/d/app-performance)

### Postmortems
- [2025-09-15: Connection Pool Exhaustion](../postmortems/2025-09-15-connection-pool.md)
- [2025-06-22: Slow Query Impact](../postmortems/2025-06-22-slow-query.md)

### Configuration
- [Database Connection Settings](../docs/database-config.md)
- [Pool Sizing Guidelines](../docs/pool-sizing.md)

## Testing and Validation

### How to Test This Runbook

```bash
# Staging environment test
# 1. Reduce pool size artificially
kubectl set env deployment/api-service-staging DB_POOL_SIZE=5

# 2. Generate load
hey -n 1000 -c 50 https://api-staging.example.com/api/v1/health

# 3. Verify alert fires
# 4. Follow runbook steps
# 5. Verify mitigation works
# 6. Restore normal pool size

# Verify alert fires within expected time
# Verify mitigation reduces pool pressure within expected time
```

### Validation Checklist

- [ ] Alert fires when pool reaches 85%
- [ ] Runbook steps are clear and actionable
- [ ] Commands work as written (tested in staging)
- [ ] Escalation contacts are current
- [ ] Metric thresholds are accurate
- [ ] Expected outcomes documented

## Appendix: Reference Commands

### Quick Reference Card

```bash
# Check pool status
curl http://api:9090/metrics | grep connection_pool

# Check DB connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE state='active';"

# Kill long query
psql -c "SELECT pg_terminate_backend(PID);"

# Scale app
kubectl scale deployment/api-service --replicas=N

# Restart app
kubectl rollout restart deployment/api-service

# Increase pool size
kubectl set env deployment/api-service DB_POOL_SIZE=N
```

### Common Queries

```sql
-- Active connections by state (PostgreSQL)
SELECT state, count(*)
FROM pg_stat_activity
GROUP BY state;

-- Longest running queries
SELECT pid, now() - query_start as duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC
LIMIT 5;

-- Connections by application
SELECT application_name, count(*)
FROM pg_stat_activity
GROUP BY application_name
ORDER BY count DESC;

-- Connection wait time (if tracked in app)
SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY wait_time_ms)
FROM connection_pool_wait_times
WHERE timestamp > now() - interval '5 minutes';
```
