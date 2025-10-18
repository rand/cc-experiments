---
name: deployment-heroku-troubleshooting
description: Application crashes on Heroku with H10, H12, H13, H14 errors
---



# Heroku Troubleshooting

**Scope**: Debugging Heroku apps, log analysis, crashes, performance issues, scaling strategies
**Lines**: ~320
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Application crashes on Heroku with H10, H12, H13, H14 errors
- Debugging slow response times or timeout errors (H12)
- Investigating memory issues or R14/R15 errors
- Troubleshooting deployment failures or build errors
- Analyzing application logs for error patterns
- Optimizing dyno performance and resource usage
- Resolving database connection errors or pool exhaustion
- Fixing failed release phase or migration errors

## Core Concepts

### Heroku Error Codes

**HTTP Status Errors (H-codes)**:
- `H10`: App crashed (code error, missing dependency)
- `H12`: Request timeout (>30s for web requests)
- `H13`: Connection closed without response
- `H14`: No web dynos running
- `H18`: Server request interrupted (client disconnect)
- `H20`: App boot timeout (>60s to bind to $PORT)
- `H21`: Backend connection timeout
- `H22`: Connection limit reached
- `H23`: Endpoint exhaustion (all dynos busy)
- `H27`: Client request timeout (10s connection, 55s idle)

**Runtime Errors (R-codes)**:
- `R10`: Boot timeout (app didn't bind to $PORT in 60s)
- `R12`: Exit timeout (graceful shutdown exceeded 30s)
- `R13`: Attach error (couldn't attach to process)
- `R14`: Memory quota exceeded (swap usage)
- `R15`: Memory quota vastly exceeded (killed immediately)
- `R16`: Detached (dyno receiving traffic but not running)

### Log Aggregation

**Log sources**:
- App logs: `stdout`/`stderr` from application code
- System logs: Heroku platform events (dyno start/stop, deploy)
- Router logs: HTTP request routing (path, status, duration)
- Dyno logs: Process management events

**Log structure** (Heroku format):
```
timestamp source[process]: message
2025-10-18T12:34:56.789Z app[web.1]: Starting application...
2025-10-18T12:34:57.123Z heroku[web.1]: State changed from starting to up
2025-10-18T12:35:00.456Z heroku[router]: at=info method=GET path="/" host=myapp.herokuapp.com
```

### Performance Metrics

**Response time components**:
- Queue time: Time waiting for available dyno
- Service time: Dyno processing time
- Connect time: Time establishing connection

**Key metrics**:
- Request throughput (requests/second)
- Average response time (ms)
- Error rate (%)
- Dyno memory usage (MB)
- Dyno CPU usage (%)

---

## Patterns

### Pattern 1: Debugging Application Crashes (H10)

**View recent logs**:
```bash
# Tail logs (follow)
heroku logs --tail --app myapp

# Last 1000 lines
heroku logs -n 1000

# Filter by process
heroku logs --dyno=web.1

# Search for errors
heroku logs --tail | grep -i error
```

**Common H10 causes and fixes**:

**1. Missing dependencies**:
```bash
# Error in logs:
# ModuleNotFoundError: No module named 'requests'

# Fix: Add to requirements.txt
echo "requests==2.31.0" >> requirements.txt
git commit -am "Add missing dependency"
git push heroku main
```

**2. Port binding error**:
```python
# ❌ Wrong: Hardcoded port
app.run(host='0.0.0.0', port=5000)

# ✅ Correct: Use $PORT environment variable
import os
port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port)
```

**3. Syntax error or import error**:
```bash
# Test locally first
heroku local web

# Or run bash on dyno to debug
heroku run bash
python manage.py check
```

**4. Database connection failure**:
```bash
# Check DATABASE_URL is set
heroku config:get DATABASE_URL

# Test connection
heroku run python manage.py dbshell
```

### Pattern 2: Fixing Request Timeouts (H12)

**Identify slow requests** (router logs):
```bash
# Filter for slow requests (>5000ms)
heroku logs --tail | grep 'service=[5-9][0-9][0-9][0-9]ms'

# Example output:
# at=info method=GET path="/slow-endpoint" service=12000ms status=200
```

**Common timeout causes**:

**1. Slow database queries**:
```python
# Diagnose with query logging
import logging
logging.getLogger('django.db.backends').setLevel(logging.DEBUG)

# Or use Django Debug Toolbar locally
# Install: pip install django-debug-toolbar
```

**2. Missing database indexes**:
```sql
-- Check slow queries (Postgres)
SELECT * FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

-- Add index
CREATE INDEX idx_users_email ON users(email);
```

**3. External API calls**:
```python
# ❌ Wrong: Blocking synchronous call
response = requests.get('https://slow-api.com/data')

# ✅ Correct: Timeout + async processing
import requests

try:
    response = requests.get('https://api.com/data', timeout=5)
except requests.Timeout:
    # Fall back or retry later
    logger.error("API timeout")
    return default_response

# Or move to background worker
from celery import shared_task

@shared_task
def fetch_api_data():
    response = requests.get('https://slow-api.com/data', timeout=30)
    # Process response
```

**4. Heavy computation in request cycle**:
```python
# ❌ Wrong: CPU-intensive in request
def report_view(request):
    data = generate_complex_report()  # Takes 45 seconds
    return JsonResponse(data)

# ✅ Correct: Async job with status polling
from celery import shared_task

@shared_task
def generate_report(report_id):
    data = generate_complex_report()
    Report.objects.filter(id=report_id).update(data=data, status='complete')

def report_view(request):
    report = Report.objects.create(status='pending')
    generate_report.delay(report.id)
    return JsonResponse({'status': 'pending', 'report_id': report.id})

def report_status_view(request, report_id):
    report = Report.objects.get(id=report_id)
    return JsonResponse({'status': report.status, 'data': report.data})
```

### Pattern 3: Memory Issues (R14/R15)

**Check dyno memory usage**:
```bash
# View metrics in dashboard
heroku logs --tail | grep 'R14\|R15'

# Example output:
# Error R14 (Memory quota exceeded)
# Error R15 (Memory quota vastly exceeded)
```

**Diagnose memory leaks**:

**Python (memory_profiler)**:
```python
# Install: pip install memory_profiler

from memory_profiler import profile

@profile
def problematic_function():
    # This decorator logs memory usage line-by-line
    large_list = [i for i in range(10000000)]
    return process_data(large_list)

# Run locally to identify leaks
python -m memory_profiler script.py
```

**Common memory issues**:

**1. Loading large datasets into memory**:
```python
# ❌ Wrong: Load entire dataset
users = User.objects.all()  # Fetches all rows
for user in users:
    process_user(user)

# ✅ Correct: Use iterator
users = User.objects.all().iterator(chunk_size=1000)
for user in users:
    process_user(user)
```

**2. Not closing database connections**:
```python
# ❌ Wrong: Connection leak
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()
cursor.execute("SELECT * FROM users")
# Missing conn.close()

# ✅ Correct: Context manager
import psycopg2
from contextlib import closing

with closing(psycopg2.connect(DATABASE_URL)) as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users")
        results = cursor.fetchall()
```

**3. Caching too much data**:
```python
# ❌ Wrong: Unbounded cache
cache = {}
def get_user(user_id):
    if user_id not in cache:
        cache[user_id] = fetch_user(user_id)
    return cache[user_id]

# ✅ Correct: Use Redis or LRU cache
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user(user_id):
    return fetch_user(user_id)
```

**Fix: Upgrade dyno type**:
```bash
# Check current dyno type
heroku ps

# Upgrade to more memory
# Basic: 512MB → Standard-1X: 512MB → Standard-2X: 1GB
heroku ps:type standard-2x
```

### Pattern 4: Boot Timeout (R10)

**Common causes**:

**1. Not binding to $PORT**:
```javascript
// ❌ Wrong: Hardcoded port
app.listen(3000);

// ✅ Correct: Use PORT environment variable
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

**2. Slow initialization**:
```python
# ❌ Wrong: Database migrations on startup
# This can exceed 60s boot timeout
def app_startup():
    run_migrations()  # 90 seconds
    app.run()

# ✅ Correct: Use release phase in Procfile
# Procfile:
# release: python manage.py migrate
# web: gunicorn myapp.wsgi
```

**3. Cold start with large dependencies**:
```bash
# Optimize build time
# Cache dependencies, use pre-built wheels

# Python: Use specific versions (faster resolution)
# requirements.txt:
Django==4.2.7  # Not Django>=4.0
psycopg2-binary==2.9.9  # Use binary (not source)
```

### Pattern 5: Database Connection Pool Exhaustion

**Symptom**:
```bash
# Error in logs:
# OperationalError: FATAL: remaining connection slots are reserved
# Or: psycopg2.pool.PoolError: connection pool exhausted
```

**Diagnose**:
```bash
# Check current connections
heroku pg:info

# Connections: 18/20 (Essential plan has 20 max)

# Find long-running queries
heroku pg:ps
```

**Fixes**:

**1. Enable connection pooling**:
```bash
# Increases effective connection limit
heroku pg:connection-pooling:attach DATABASE --as DATABASE_CONNECTION_POOL

# Update DATABASE_URL to use pooled connection
heroku config:set DATABASE_URL=$(heroku config:get DATABASE_CONNECTION_POOL_URL)
```

**2. Reduce connection timeout**:
```python
# Django: Close connections after request
DATABASES = {
    'default': {
        # ... other settings
        'CONN_MAX_AGE': 60,  # Close idle connections after 60s
    }
}
```

**3. Use connection pooler in app**:
```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,              # Max connections per worker
    max_overflow=10,          # Extra connections when pool full
    pool_recycle=3600,        # Recycle connections after 1 hour
    pool_pre_ping=True        # Verify connections before use
)
```

### Pattern 6: Failed Migrations

**Symptom**:
```bash
# Release phase failed
# Error: relation "new_table" already exists
```

**Rollback failed release**:
```bash
# View releases
heroku releases

# Rollback to previous version
heroku rollback v123
```

**Fix migration**:
```bash
# Run migration manually to diagnose
heroku run python manage.py migrate --fake-initial

# Or reset migration
heroku run python manage.py migrate app_name zero
heroku run python manage.py migrate
```

**Prevent future issues**:
```python
# Use idempotent migrations
from django.db import migrations

class Migration(migrations.Migration):
    def forwards(self, apps, schema_editor):
        # Check if table exists before creating
        if not schema_editor.table_exists('new_table'):
            # Create table
            pass
```

### Pattern 7: High Dyno Load (H23)

**Symptom**:
```bash
# Error H23 (Endpoint exhaustion)
# All dynos busy, requests queuing
```

**Diagnose**:
```bash
# Check dyno metrics (requires app metrics add-on or dashboard)
heroku logs --tail | grep 'at=info'

# Look for high service times and queue times
# at=info method=GET path="/" service=5000ms queue=2000ms
```

**Fixes**:

**1. Scale dynos horizontally**:
```bash
# Add more web dynos
heroku ps:scale web=3

# Or enable autoscaling (requires Performance dynos)
heroku ps:autoscale:enable web --min=2 --max=5 --p95=200
```

**2. Optimize slow endpoints**:
```python
# Add caching
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def homepage(request):
    return render(request, 'home.html')
```

**3. Move work to background**:
```python
# Use Celery for async processing
from celery import shared_task

@shared_task
def send_notification_email(user_id):
    # Offload email sending to worker dyno
    user = User.objects.get(id=user_id)
    send_email(user.email, "Welcome!")

def signup_view(request):
    user = create_user(request.POST)
    send_notification_email.delay(user.id)  # Async
    return redirect('home')
```

### Pattern 8: Log Analysis for Patterns

**Extract key metrics**:
```bash
# Average response time for endpoint
heroku logs -n 10000 | grep 'path="/api/users"' | \
  awk '{print $11}' | sed 's/service=//;s/ms//' | \
  awk '{sum+=$1; count++} END {print sum/count}'

# Count errors by type
heroku logs -n 10000 | grep -i error | \
  awk '{print $5}' | sort | uniq -c | sort -rn

# Top slowest endpoints
heroku logs -n 10000 | grep 'at=info' | \
  awk '{print $8, $11}' | sed 's/path=//;s/service=//' | \
  sort -t' ' -k2 -rn | head -20
```

**Set up structured logging**:
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "user_login",
    user_id=user.id,
    ip=request.META['REMOTE_ADDR'],
    duration_ms=elapsed_time * 1000
)

# Search in Papertrail: user_login user_id=123
```

---

## Quick Reference

### Error Code Quick Lookup

```
Code  | Meaning                        | Common Fix
------|--------------------------------|--------------------------------
H10   | App crashed                    | Check logs for error, fix code
H12   | Request timeout                | Optimize query, add timeout
H13   | Connection closed              | Check dyno health
H14   | No web dynos running           | heroku ps:scale web=1
H18   | Request interrupted            | Client issue, not server
R10   | Boot timeout                   | Bind to $PORT, speed up init
R14   | Memory quota exceeded          | Optimize memory, upgrade dyno
R15   | Memory killed immediately      | Fix memory leak urgently
```

### Essential Debugging Commands

```
Command                              | Purpose
-------------------------------------|----------------------------------------
heroku logs --tail                   | Follow live logs
heroku logs -n 5000                  | Last 5000 log lines
heroku logs --dyno=web.1             | Filter by dyno
heroku logs --source=app             | Filter by source
heroku ps                            | Check dyno status
heroku ps:restart                    | Restart all dynos
heroku run bash                      | Open shell on dyno
heroku run python manage.py shell    | Django shell
heroku pg:ps                         | Active database queries
heroku pg:kill 1234                  | Kill query by PID
heroku releases                      | View deploy history
heroku rollback v123                 | Rollback to version
heroku maintenance:on                | Enable maintenance mode
```

### Performance Optimization Checklist

```
✅ DO: Use database connection pooling
✅ DO: Add indexes for frequent queries
✅ DO: Cache expensive computations (Redis)
✅ DO: Move long tasks to worker dynos (Celery)
✅ DO: Set request timeouts on external APIs
✅ DO: Use CDN for static assets (Cloudflare)
✅ DO: Monitor memory usage over time
✅ DO: Scale horizontally for traffic spikes

❌ DON'T: Run CPU-intensive tasks in web dynos
❌ DON'T: Load large datasets into memory
❌ DON'T: Skip database indexes
❌ DON'T: Leave connections open (use context managers)
❌ DON'T: Ignore H12 timeout errors
❌ DON'T: Run migrations in app startup code
❌ DON'T: Deploy without testing locally first
```

---

## Anti-Patterns

❌ **Ignoring H12 timeouts**: Accepting slow responses as normal
✅ Profile and optimize slow endpoints, move work to background

❌ **No structured logging**: Unstructured logs are hard to search/analyze
✅ Use JSON logging with context (user_id, request_id, duration)

❌ **Not monitoring memory usage**: Only notice when R15 kills app
✅ Track memory metrics, optimize before hitting limits

❌ **Deploying on Friday afternoon**: Risk of weekend outage
✅ Deploy early in week, monitor for 24h before weekend

❌ **No rollback plan**: Broken deploy with no quick fix
✅ Test deploys in staging, keep rollback command ready

❌ **Running database queries in loops**: N+1 query problem
✅ Use select_related/prefetch_related (Django) or JOIN queries

❌ **Hardcoded timeouts**: External API outages cascade
✅ Set aggressive timeouts (5-10s), fail fast with retries

❌ **Single dyno for production**: No redundancy, downtime on deploy
✅ Run 2+ web dynos for zero-downtime deploys

❌ **No error tracking**: Unaware of user-facing errors
✅ Add Sentry or similar for exception monitoring

❌ **Guessing at problems**: Trying random fixes
✅ Use logs, metrics, and profiling to diagnose root cause

---

## Related Skills

- `heroku-deployment.md` - Deploying apps and configuring Procfile
- `heroku-addons.md` - Using Postgres, Redis, monitoring add-ons
- `postgres-query-optimization.md` - Optimizing slow database queries
- `structured-logging.md` - Best practices for application logging
- `performance-profiling.md` - Profiling CPU and memory usage
- `celery-background-jobs.md` - Moving work to background workers

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
