---
name: database-database-connection-pooling
description: Configuring database connections for applications
---



# Database Connection Pooling

**Scope**: Connection pool configuration, sizing, ORM-specific patterns
**Lines**: ~220
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Configuring database connections for applications
- Debugging connection pool exhaustion
- Optimizing connection pool settings
- Choosing pool sizes for different workloads
- Troubleshooting connection timeouts or leaks
- Configuring ORMs (SQLAlchemy, Prisma, GORM, Diesel)

## Core Concepts

### What is Connection Pooling?

**Problem**: Creating new database connections is expensive (TCP handshake, authentication, initialization).

**Solution**: Reuse connections via a **pool**.

**How it works**:
1. Application requests connection from pool
2. Pool provides idle connection (or creates new one if available)
3. Application uses connection for query
4. Application returns connection to pool (not closed)
5. Connection waits idle for next request

**Benefits**:
- Faster queries (no connection overhead)
- Limits concurrent connections to database
- Handles connection lifecycle automatically

---

## Key Parameters

### Pool Size

**`pool_size`** (or `max_connections`): Maximum number of connections in pool.

```python
# SQLAlchemy example
engine = create_engine(
    "postgresql://...",
    pool_size=10  # Max 10 connections
)
```

**How to choose**:
```
pool_size = (num_threads or num_workers) × N

Where N = 1-3 connections per thread/worker
```

**Examples**:
- Web server with 10 workers → pool_size = 10-30
- Single-threaded app → pool_size = 1-5
- High-concurrency async app → pool_size = 20-50

**Too small**: Connection exhaustion, queries wait
**Too large**: Database overload, memory waste

### Max Overflow

**`max_overflow`**: Additional connections beyond pool_size (temporary).

```python
engine = create_engine(
    "postgresql://...",
    pool_size=10,
    max_overflow=5  # Up to 15 total connections
)
```

**Total connections** = pool_size + max_overflow

**Use case**: Handle traffic spikes without exhausting pool.

### Pool Timeout

**`pool_timeout`**: Seconds to wait for available connection.

```python
engine = create_engine(
    "postgresql://...",
    pool_timeout=30  # Wait up to 30 seconds
)
```

**What happens on timeout**:
- Raise exception (e.g., `TimeoutError`)
- Application can retry or return error to user

**Recommended**: 10-30 seconds

### Idle Timeout (Pool Recycle)

**`pool_recycle`**: Seconds before recycling idle connections.

```python
engine = create_engine(
    "postgresql://...",
    pool_recycle=3600  # Recycle after 1 hour
)
```

**Why recycle**:
- Database may close idle connections (e.g., MySQL `wait_timeout`)
- Prevents "connection has been closed" errors
- Clears stale connections

**Recommended**: Slightly less than database's `wait_timeout` (typically 1-8 hours).

### Pre-Ping

**`pool_pre_ping`**: Test connection before use (detect closed connections).

```python
engine = create_engine(
    "postgresql://...",
    pool_pre_ping=True  # Test connection before use
)
```

**How it works**: Issues lightweight query (`SELECT 1`) before returning connection.

**Pros**: Prevents "connection closed" errors
**Cons**: Slight overhead per query

**Recommended**: Enable for production reliability.

---

## Calculating Pool Size

### Formula

```
Optimal pool size = (Tn × (Cm - 1)) + 1

Where:
  Tn = Number of threads/workers
  Cm = Average number of concurrent queries per request
```

**Example 1**: Web app with 20 workers, 1 query per request
```
pool_size = (20 × (1 - 1)) + 1 = 1
pool_size = 20 (add buffer) → Use 20-30
```

**Example 2**: API with 10 workers, 3 queries per request (joining tables)
```
pool_size = (10 × (3 - 1)) + 1 = 21
pool_size = 21 → Use 25-30
```

### HikariCP Formula (Java)

```
connections = ((core_count × 2) + effective_spindle_count)

For SSDs (no spindles):
connections = (core_count × 2)
```

**Example**: 4-core server with SSD
```
connections = 4 × 2 = 8
```

### Conservative Approach

**Start small, increase if needed**:
1. Start with `pool_size = num_workers`
2. Monitor for pool exhaustion warnings
3. Increase by 25% if exhaustion occurs
4. Repeat until stable

**Database limits**: PostgreSQL default `max_connections = 100`, MySQL default `151`.

**Leave headroom**: Don't use all available connections (reserve for admin, monitoring).

---

## ORM-Specific Configuration

### SQLAlchemy (Python)

```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://user:pass@localhost/db",
    pool_size=10,            # Base pool size
    max_overflow=5,          # Burst capacity
    pool_timeout=30,         # Wait time for connection
    pool_recycle=3600,       # Recycle after 1 hour
    pool_pre_ping=True,      # Test before use
    echo_pool=True           # Log pool events (debug only)
)
```

**Pool types**:
- `QueuePool` (default): Thread-safe, multiple threads
- `NullPool`: No pooling (creates new connection each time)
- `StaticPool`: Single connection (SQLite)

### Prisma (Node.js/TypeScript)

```typescript
// In schema.prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// Connection string with pool params
DATABASE_URL="postgresql://user:pass@localhost/db?schema=public&connection_limit=10"

// Or in PrismaClient
const prisma = new PrismaClient({
  datasources: {
    db: {
      url: process.env.DATABASE_URL + "?connection_limit=10&pool_timeout=20"
    }
  }
})
```

**Parameters**:
- `connection_limit`: Max connections (default: `num_cpus × 2 + 1`)
- `pool_timeout`: Wait time in seconds (default: 10)

### GORM (Go)

```go
import (
    "gorm.io/driver/postgres"
    "gorm.io/gorm"
)

dsn := "host=localhost user=postgres password=pass dbname=db"
db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})

sqlDB, err := db.DB()

// Configure pool
sqlDB.SetMaxOpenConns(25)           // Max connections
sqlDB.SetMaxIdleConns(5)            // Idle connections
sqlDB.SetConnMaxLifetime(time.Hour) // Max lifetime
sqlDB.SetConnMaxIdleTime(10 * time.Minute) // Max idle time
```

**Parameters**:
- `SetMaxOpenConns`: Total max connections
- `SetMaxIdleConns`: Idle connections in pool
- `SetConnMaxLifetime`: Max connection age
- `SetConnMaxIdleTime`: Max idle duration before close

### Diesel (Rust)

```rust
use diesel::r2d2::{self, ConnectionManager};
use diesel::pg::PgConnection;

let manager = ConnectionManager::<PgConnection>::new(database_url);

let pool = r2d2::Pool::builder()
    .max_size(10)                        // Max connections
    .min_idle(Some(2))                   // Min idle connections
    .connection_timeout(Duration::from_secs(30))
    .idle_timeout(Some(Duration::from_secs(600)))
    .build(manager)?;
```

### Django (Python)

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'db',
        'USER': 'user',
        'PASSWORD': 'pass',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # Connection lifetime (seconds), 0 = no pooling
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

**Note**: Django doesn't have true pooling by default. Use `django-db-pool` or `pgbouncer` for pooling.

---

## Connection Pool Exhaustion

### Symptoms

```
Error: QueuePool limit of size 10 overflow 5 reached
Error: FATAL: too many connections for role "user"
Error: Timeout waiting for connection from pool
```

### Causes

1. **Too many concurrent requests**: Traffic spike exceeds pool size
2. **Connection leaks**: Connections not returned to pool
3. **Long-running queries**: Connections held for too long
4. **Incorrect pool sizing**: Pool too small for workload

### Debugging

```python
# SQLAlchemy: Check pool status
print(engine.pool.status())
# Output: Pool size: 10  Connections in pool: 2 Current Overflow: 0 Current Checked out connections: 8

# Log pool events
engine = create_engine("...", echo_pool=True)
```

### Solutions

**1. Increase pool size**:
```python
engine = create_engine("...", pool_size=20, max_overflow=10)
```

**2. Fix connection leaks**:
```python
# ❌ BAD: Connection leak
conn = engine.connect()
result = conn.execute(query)
# Connection never returned!

# ✅ GOOD: Use context manager
with engine.connect() as conn:
    result = conn.execute(query)
# Connection automatically returned
```

**3. Optimize slow queries**: Use `postgres-query-optimization.md`

**4. Use external pooler**: PgBouncer, AWS RDS Proxy

---

## External Connection Poolers

### PgBouncer

**What**: External connection pooler for PostgreSQL.

**Use case**: Multiple applications share database, need more than 100 connections.

```ini
# pgbouncer.ini
[databases]
mydb = host=localhost dbname=mydb

[pgbouncer]
pool_mode = transaction  # Or session, statement
max_client_conn = 1000   # Client connections
default_pool_size = 20   # Connections to database per user/database pair
reserve_pool_size = 5
```

**Pool modes**:
- **session**: Hold connection for session (safest, default)
- **transaction**: Release connection after transaction (most efficient)
- **statement**: Release after each statement (dangerous, breaks transactions)

**Recommended**: `transaction` mode for web apps.

### AWS RDS Proxy

**What**: Managed connection pooler for RDS/Aurora.

**Benefits**:
- Automatic failover
- IAM authentication
- Handles connection spikes

**Configuration**:
```
Max connections: 100
Idle timeout: 1800 seconds
```

---

## Monitoring

### Key Metrics

| Metric | What to Monitor | Threshold |
|--------|----------------|-----------|
| Pool size | Current active connections | < pool_size × 0.8 |
| Wait time | Time waiting for connection | < 100ms |
| Timeout errors | Connection timeout rate | 0% |
| Connection age | Average connection lifetime | < pool_recycle |

### Tools

**PostgreSQL**:
```sql
-- Check current connections
SELECT count(*), state
FROM pg_stat_activity
WHERE datname = 'mydb'
GROUP BY state;

-- Check connection age
SELECT now() - backend_start AS age, query
FROM pg_stat_activity
ORDER BY age DESC;
```

**MySQL**:
```sql
SHOW PROCESSLIST;
SHOW STATUS LIKE 'Threads_connected';
```

---

## Best Practices

### Do's

✅ **Start with conservative pool size** (num_workers)
✅ **Enable pool_pre_ping** for reliability
✅ **Set pool_recycle** < database timeout
✅ **Use context managers** to return connections
✅ **Monitor pool metrics** in production
✅ **Use external pooler** for high concurrency

### Don'ts

❌ **Don't set pool_size = max_connections** (leave headroom)
❌ **Don't leak connections** (always close/return)
❌ **Don't ignore timeout errors** (sign of undersized pool)
❌ **Don't use same pool across processes** (each process needs its own)

---

## Quick Reference

### Pool Sizing Cheatsheet

```
Workload                     Pool Size
────────────────────────────────────────
Web app (10 workers)        10-20
API (20 workers)            20-40
Background jobs (5 workers) 5-10
Single-threaded app         1-5
High-concurrency async      30-50
Database limit              < max_connections - 10
```

### Configuration Template (SQLAlchemy)

```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://user:pass@host/db",
    pool_size=20,               # Base pool
    max_overflow=10,            # Burst capacity
    pool_timeout=30,            # Wait timeout
    pool_recycle=3600,          # Recycle after 1h
    pool_pre_ping=True,         # Test before use
)
```

---

## Common Pitfalls

❌ **Pool size too large** - Database overload, memory waste
✅ Calculate based on workers/threads, not arbitrary large number

❌ **No pool recycling** - Stale connections, timeout errors
✅ Set pool_recycle < database timeout

❌ **Connection leaks** - Pool exhaustion
✅ Always use context managers or explicit close

❌ **One pool for all apps** - Contention, hard to debug
✅ Each application instance has its own pool

---

## Related Skills

- `postgres-query-optimization.md` - Optimize queries to reduce connection time
- `database-selection.md` - Connection pooling considerations per database
- `orm-patterns.md` - ORM best practices for connection management

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
