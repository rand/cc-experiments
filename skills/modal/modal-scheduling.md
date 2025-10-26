---
name: modal-scheduling
description: Running periodic tasks on Modal
---



# Modal Scheduling

**Use this skill when:**
- Running periodic tasks on Modal
- Implementing cron jobs
- Scheduling batch processing
- Creating automated workflows
- Building recurring data pipelines

## Periodic Schedules

### Simple Period

Run functions at fixed intervals:

```python
import modal

app = modal.App("scheduled-app")

# Every 5 minutes
@app.function(schedule=modal.Period(minutes=5))
def every_five_minutes():
    print("Running every 5 minutes")
    return process_data()

# Every hour
@app.function(schedule=modal.Period(hours=1))
def hourly_task():
    print("Running hourly")
    return cleanup_temp_files()

# Every day
@app.function(schedule=modal.Period(days=1))
def daily_task():
    print("Running daily")
    return generate_report()
```

### Multiple Time Units

Combine time units:

```python
# Every 1 hour 30 minutes
@app.function(schedule=modal.Period(hours=1, minutes=30))
def every_ninety_minutes():
    return sync_data()

# Every week (7 days)
@app.function(schedule=modal.Period(days=7))
def weekly_cleanup():
    return archive_old_data()
```

## Cron Schedules

### Cron Syntax

Use cron expressions for precise timing:

```python
# Every day at 2:30 AM UTC
@app.function(schedule=modal.Cron("30 2 * * *"))
def daily_at_230am():
    return generate_daily_report()

# Every Monday at 9:00 AM UTC
@app.function(schedule=modal.Cron("0 9 * * MON"))
def monday_morning():
    return send_weekly_summary()

# Every weekday at 8:00 AM UTC
@app.function(schedule=modal.Cron("0 8 * * MON-FRI"))
def weekday_morning():
    return business_day_tasks()

# First day of month at midnight UTC
@app.function(schedule=modal.Cron("0 0 1 * *"))
def monthly_billing():
    return process_monthly_invoices()

# Every 15 minutes
@app.function(schedule=modal.Cron("*/15 * * * *"))
def every_fifteen_min():
    return poll_external_api()
```

### Cron Format Reference

```
# Format: minute hour day month weekday
# ┌───────── minute (0 - 59)
# │ ┌───────── hour (0 - 23)
# │ │ ┌───────── day of month (1 - 31)
# │ │ │ ┌───────── month (1 - 12)
# │ │ │ │ ┌───────── day of week (0 - 6) (Sunday=0 or 7)
# │ │ │ │ │
# * * * * *

# Examples:
# "0 0 * * *"        # Daily at midnight
# "0 */6 * * *"      # Every 6 hours
# "30 3 * * 0"       # Sundays at 3:30 AM
# "0 0 1,15 * *"     # 1st and 15th of month
# "0 9-17 * * *"     # Every hour from 9 AM to 5 PM
```

## Scheduled Data Processing

### ETL Pipeline

Schedule data extraction and processing:

```python
image = modal.Image.debian_slim().uv_pip_install(
    "pandas",
    "sqlalchemy",
    "psycopg2-binary"
)

@app.function(
    schedule=modal.Cron("0 1 * * *"),  # 1 AM daily
    image=image,
    timeout=3600  # 1 hour max
)
def etl_pipeline():
    import pandas as pd
    from sqlalchemy import create_engine

    print("Starting ETL pipeline")

    # Extract
    source_data = extract_from_source()

    # Transform
    df = pd.DataFrame(source_data)
    df = transform_data(df)

    # Load
    engine = create_engine(DATABASE_URL)
    df.to_sql("analytics", engine, if_exists="replace")

    print(f"Loaded {len(df)} rows")
    return {"rows": len(df), "status": "complete"}

def extract_from_source():
    # Fetch from API, S3, etc.
    return data

def transform_data(df):
    # Clean and transform
    return df
```

### Batch Processing

Process batches on schedule:

```python
@app.function(
    schedule=modal.Period(hours=6),
    timeout=7200  # 2 hours
)
def process_pending_jobs():
    jobs = get_pending_jobs()

    print(f"Processing {len(jobs)} jobs")

    # Process in parallel
    results = list(process_job.map(jobs))

    successful = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - successful

    print(f"Completed: {successful} success, {failed} failed")

    return {
        "total": len(jobs),
        "successful": successful,
        "failed": failed
    }

@app.function()
def process_job(job):
    try:
        result = execute_job(job)
        return {"job_id": job["id"], "status": "success"}
    except Exception as e:
        return {"job_id": job["id"], "status": "failed", "error": str(e)}
```

## Monitoring and Alerts

### Health Checks

Schedule health monitoring:

```python
@app.function(schedule=modal.Period(minutes=5))
def health_check():
    services = ["api", "database", "cache"]
    results = {}

    for service in services:
        try:
            status = check_service(service)
            results[service] = "healthy"
        except Exception as e:
            results[service] = f"unhealthy: {e}"
            send_alert(f"Service {service} is down: {e}")

    return results

def check_service(service_name):
    # Ping service
    pass

def send_alert(message):
    # Send to Slack, PagerDuty, etc.
    pass
```

### Metric Collection

Collect metrics periodically:

```python
@app.function(schedule=modal.Cron("*/5 * * * *"))  # Every 5 min
def collect_metrics():
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "cpu_usage": get_cpu_usage(),
        "memory_usage": get_memory_usage(),
        "active_users": count_active_users(),
        "request_count": get_request_count()
    }

    # Store in time-series database
    store_metrics(metrics)

    return metrics
```

## Data Cleanup

### Automated Cleanup

Schedule data cleanup tasks:

```python
from datetime import datetime, timedelta

@app.function(schedule=modal.Cron("0 2 * * *"))  # 2 AM daily
def cleanup_old_data():
    cutoff_date = datetime.now() - timedelta(days=90)

    # Delete old records
    deleted_count = delete_records_before(cutoff_date)

    # Clean up temporary files
    temp_files_deleted = cleanup_temp_files()

    # Archive old logs
    logs_archived = archive_old_logs(cutoff_date)

    return {
        "records_deleted": deleted_count,
        "temp_files_deleted": temp_files_deleted,
        "logs_archived": logs_archived
    }
```

### Cache Warming

Pre-warm caches on schedule:

```python
@app.function(schedule=modal.Cron("0 6 * * *"))  # 6 AM daily
def warm_caches():
    # Pre-compute popular queries
    popular_items = get_popular_items()

    for item in popular_items:
        cache_item_details(item)

    print(f"Warmed cache for {len(popular_items)} items")
    return {"items_cached": len(popular_items)}
```

## Backup and Archival

### Automated Backups

Schedule database backups:

```python
@app.function(
    schedule=modal.Cron("0 0 * * *"),  # Midnight daily
    timeout=3600
)
def backup_database():
    import subprocess
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{timestamp}.sql"

    # Create backup
    subprocess.run([
        "pg_dump",
        "-h", DB_HOST,
        "-U", DB_USER,
        "-d", DB_NAME,
        "-f", backup_file
    ])

    # Upload to S3
    upload_to_s3(backup_file, f"backups/{backup_file}")

    # Clean up local file
    os.remove(backup_file)

    return {"backup_file": backup_file, "status": "complete"}
```

## Retries and Error Handling

### Retry Failed Jobs

Handle failures gracefully:

```python
@app.function(
    schedule=modal.Period(hours=1),
    retries=3  # Retry up to 3 times
)
def resilient_task():
    try:
        result = perform_task()
        return {"status": "success", "result": result}
    except Exception as e:
        print(f"Task failed: {e}")
        # Log error for monitoring
        log_error(e)
        raise  # Will trigger retry
```

### Error Notifications

Send alerts on failures:

```python
@app.function(schedule=modal.Cron("0 * * * *"))  # Hourly
def monitored_task():
    try:
        result = critical_operation()
        return {"status": "success"}
    except Exception as e:
        # Send alert
        send_slack_alert(f"Hourly task failed: {e}")

        # Log to monitoring service
        log_to_datadog("task.failed", tags=["critical"])

        # Re-raise to show as failed in Modal dashboard
        raise
```

## Conditional Execution

### Skip on Conditions

Run only when needed:

```python
@app.function(schedule=modal.Cron("0 */4 * * *"))  # Every 4 hours
def conditional_sync():
    # Check if sync is needed
    if not should_sync():
        print("Sync not needed, skipping")
        return {"status": "skipped"}

    # Perform sync
    result = sync_data()

    return {"status": "completed", "items": result}

def should_sync():
    # Check conditions (e.g., data staleness)
    return check_data_age() > 4 * 3600
```

## Chaining Scheduled Functions

### Sequential Processing

Chain multiple scheduled tasks:

```python
@app.function(schedule=modal.Cron("0 1 * * *"))  # 1 AM
def step1_extract():
    data = extract_data()
    save_to_temp(data)
    # Trigger next step
    step2_transform.spawn()
    return {"status": "extracted"}

@app.function()
def step2_transform():
    data = load_from_temp()
    transformed = transform(data)
    save_to_temp(transformed)
    # Trigger next step
    step3_load.spawn()

@app.function()
def step3_load():
    data = load_from_temp()
    load_to_warehouse(data)
    cleanup_temp()
```

## Testing Scheduled Functions

### Manual Triggering

Test scheduled functions manually:

```python
@app.function(schedule=modal.Cron("0 2 * * *"))
def scheduled_task():
    return process_data()

# Can still call directly for testing
@app.local_entrypoint()
def test():
    result = scheduled_task.remote()
    print(f"Test result: {result}")
```

## Anti-Patterns to Avoid

**DON'T use short periods for expensive operations:**
```python
# ❌ BAD - Expensive GPU task every minute
@app.function(
    schedule=modal.Period(minutes=1),
    gpu="a100"
)
def expensive_every_minute():
    return train_model()  # Costs $8/hour constantly!

# ✅ GOOD - Appropriate frequency
@app.function(
    schedule=modal.Period(hours=6),
    gpu="a100"
)
def reasonable_schedule():
    return train_model()
```

**DON'T forget timeouts:**
```python
# ❌ BAD - Could run forever
@app.function(schedule=modal.Cron("0 0 * * *"))
def no_timeout():
    while True:
        process()

# ✅ GOOD - Bounded execution
@app.function(
    schedule=modal.Cron("0 0 * * *"),
    timeout=3600  # 1 hour max
)
def with_timeout():
    process_for_limited_time()
```

**DON'T ignore errors silently:**
```python
# ❌ BAD - Swallows errors
@app.function(schedule=modal.Period(hours=1))
def silent_failures():
    try:
        critical_task()
    except:
        pass  # No one knows it failed!

# ✅ GOOD - Log and alert
@app.function(schedule=modal.Period(hours=1))
def monitored():
    try:
        critical_task()
    except Exception as e:
        log_error(e)
        send_alert(e)
        raise
```

## Related Skills

- **modal-functions-basics.md** - Basic Modal patterns
- **modal-volumes-secrets.md** - Persisting scheduled task data
- **modal-web-endpoints.md** - Triggering tasks via webhooks
