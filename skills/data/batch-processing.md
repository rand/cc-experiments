---
name: data-batch-processing
description: Orchestrating complex data pipelines with dependencies
---



# Batch Processing

**Scope**: Airflow, DAGs, scheduling, dependency management, backfills
**Lines**: 391
**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)

## When to Use This Skill

Use this skill when:
- Orchestrating complex data pipelines with dependencies
- Scheduling batch jobs (hourly, daily, weekly)
- Managing task retries and failure handling
- Performing historical backfills of data
- Coordinating multi-step ETL workflows
- Monitoring pipeline health and SLAs
- Working with Apache Airflow or similar orchestrators

## Core Concepts

### DAG (Directed Acyclic Graph)
```
DAG Structure
  → Nodes: Tasks (Python functions, SQL, Bash)
  → Edges: Dependencies (task1 >> task2)
  → Properties: schedule, start_date, catchup, retries

Key Principle: No cycles allowed
  → Ensures deterministic execution order
```

### Task Dependencies
```
Linear: task1 >> task2 >> task3
  → Sequential execution

Parallel: task1 >> [task2, task3] >> task4
  → task2 and task3 run in parallel

Cross-depends: [task1, task2] >> task3
  → task3 waits for both

Dynamic: task1 >> TaskGroup([...])
  → Generate tasks programmatically
```

### Execution Concepts
```
Execution Date (logical date)
  → Data interval being processed (NOT run time)
  → Example: 2025-10-18 DAG processes 2025-10-17 data

Schedule Interval
  → @daily, @hourly, cron expressions
  → 0 0 * * * = daily at midnight

Catchup
  → True: Run missed intervals on deploy
  → False: Skip to present (default for new DAGs)

Backfill
  → Reprocess historical data intervals
  → airflow dags backfill -s START -e END dag_id
```

### Task States
```
success: Completed successfully
failed: Error occurred
upstream_failed: Dependency failed
skipped: Condition not met (BranchOperator)
running: Currently executing
queued: Waiting for executor slot
retry: Failed, will retry
```

## Patterns

### Pattern 1: Basic Airflow DAG Structure

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Default arguments for all tasks
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,  # Don't wait for previous interval
    'email': ['alerts@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),  # Kill if exceeds
}

# Define DAG
with DAG(
    'daily_sales_pipeline',
    default_args=default_args,
    description='Process daily sales data',
    schedule_interval='0 2 * * *',  # 2 AM daily
    start_date=datetime(2025, 1, 1),
    catchup=False,  # Don't backfill automatically
    tags=['sales', 'daily'],
    max_active_runs=1,  # Only one run at a time
) as dag:

    # Task 1: Extract data
    def extract_sales(**context):
        """Extract sales from previous day"""
        execution_date = context['execution_date']
        data_date = execution_date - timedelta(days=1)

        print(f"Extracting sales for {data_date.date()}")

        # Extract logic here
        sales_count = 1250

        # Push to XCom for downstream tasks
        context['task_instance'].xcom_push(
            key='sales_count',
            value=sales_count
        )

        return f"Extracted {sales_count} sales"

    extract = PythonOperator(
        task_id='extract_sales',
        python_callable=extract_sales,
        provide_context=True
    )

    # Task 2: Validate data
    def validate_sales(**context):
        """Validate extracted data"""
        ti = context['task_instance']
        sales_count = ti.xcom_pull(
            task_ids='extract_sales',
            key='sales_count'
        )

        if sales_count < 100:
            raise ValueError(f"Too few sales: {sales_count}")

        print(f"Validation passed: {sales_count} sales")
        return True

    validate = PythonOperator(
        task_id='validate_sales',
        python_callable=validate_sales,
        provide_context=True
    )

    # Task 3: Transform
    transform = BashOperator(
        task_id='transform_sales',
        bash_command='python /path/to/transform.py {{ ds }}',  # ds = YYYY-MM-DD
    )

    # Task 4: Load to warehouse
    def load_sales(**context):
        """Load to data warehouse"""
        execution_date = context['execution_date']

        print(f"Loading sales for {execution_date.date()}")

        # Load logic here
        return "Load complete"

    load = PythonOperator(
        task_id='load_sales',
        python_callable=load_sales,
        provide_context=True
    )

    # Task 5: Update metadata
    metadata = BashOperator(
        task_id='update_metadata',
        bash_command='echo "Updated metadata for {{ ds }}"'
    )

    # Define dependencies
    extract >> validate >> transform >> load >> metadata
```

### Pattern 2: Dynamic Task Generation

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def process_partition(partition_id: str, **context):
    """Process a single partition"""
    print(f"Processing partition {partition_id}")
    # Processing logic
    return f"Partition {partition_id} complete"

with DAG(
    'parallel_partition_processing',
    start_date=datetime(2025, 1, 1),
    schedule_interval='@daily',
    catchup=False
) as dag:

    # Get partitions dynamically
    partitions = ['2025-01', '2025-02', '2025-03', '2025-04']

    start = PythonOperator(
        task_id='start',
        python_callable=lambda: print("Starting processing")
    )

    # Create task for each partition
    partition_tasks = []
    for partition in partitions:
        task = PythonOperator(
            task_id=f'process_{partition}',
            python_callable=process_partition,
            op_kwargs={'partition_id': partition},
            provide_context=True
        )
        partition_tasks.append(task)

    end = PythonOperator(
        task_id='end',
        python_callable=lambda: print("All partitions processed")
    )

    # Dependencies: start >> all partitions >> end
    start >> partition_tasks >> end
```

### Pattern 3: TaskGroups for Organization

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from datetime import datetime

with DAG(
    'grouped_pipeline',
    start_date=datetime(2025, 1, 1),
    schedule_interval='@daily',
    catchup=False
) as dag:

    # Group 1: Extraction tasks
    with TaskGroup('extraction', tooltip='Extract from multiple sources') as extract_group:
        extract_db = PythonOperator(
            task_id='extract_database',
            python_callable=lambda: print("Extract from DB")
        )

        extract_api = PythonOperator(
            task_id='extract_api',
            python_callable=lambda: print("Extract from API")
        )

        extract_files = PythonOperator(
            task_id='extract_files',
            python_callable=lambda: print("Extract from files")
        )

    # Group 2: Transformation tasks
    with TaskGroup('transformation', tooltip='Transform data') as transform_group:
        clean = PythonOperator(
            task_id='clean_data',
            python_callable=lambda: print("Clean data")
        )

        enrich = PythonOperator(
            task_id='enrich_data',
            python_callable=lambda: print("Enrich data")
        )

        aggregate = PythonOperator(
            task_id='aggregate_data',
            python_callable=lambda: print("Aggregate data")
        )

        clean >> enrich >> aggregate

    # Group 3: Loading tasks
    with TaskGroup('loading', tooltip='Load to destinations') as load_group:
        load_warehouse = PythonOperator(
            task_id='load_warehouse',
            python_callable=lambda: print("Load to warehouse")
        )

        load_cache = PythonOperator(
            task_id='load_cache',
            python_callable=lambda: print("Load to cache")
        )

    # Dependencies between groups
    extract_group >> transform_group >> load_group
```

### Pattern 4: Sensor for External Dependencies

```python
from airflow import DAG
from airflow.sensors.filesystem import FileSensor
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.sensors.python import PythonSensor
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def check_data_ready(**context):
    """Custom check for data availability"""
    execution_date = context['execution_date']

    # Check if data exists for this date
    # Return True if ready, False otherwise

    import random
    return random.choice([True, False])

with DAG(
    'sensor_pipeline',
    start_date=datetime(2025, 1, 1),
    schedule_interval='@hourly',
    catchup=False
) as dag:

    # Wait for file to appear
    wait_for_file = FileSensor(
        task_id='wait_for_input_file',
        filepath='/data/input/{{ ds }}/data.csv',
        poke_interval=60,  # Check every 60 seconds
        timeout=3600,  # Fail after 1 hour
        mode='poke'  # or 'reschedule' to free worker slot
    )

    # Wait for upstream DAG to complete
    wait_for_upstream = ExternalTaskSensor(
        task_id='wait_for_extraction_dag',
        external_dag_id='daily_extraction',
        external_task_id='extract_complete',
        execution_delta=timedelta(hours=1),  # Adjust for schedule difference
        timeout=7200,
        mode='reschedule'
    )

    # Custom Python sensor
    wait_for_data = PythonSensor(
        task_id='wait_for_data_ready',
        python_callable=check_data_ready,
        provide_context=True,
        poke_interval=300,
        timeout=3600
    )

    # Process after all sensors succeed
    process = PythonOperator(
        task_id='process_data',
        python_callable=lambda: print("Processing data")
    )

    [wait_for_file, wait_for_upstream, wait_for_data] >> process
```

### Pattern 5: Branching and Conditional Logic

```python
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime

def decide_branch(**context):
    """Choose execution path based on conditions"""
    execution_date = context['execution_date']

    # Example: Different processing for weekends
    if execution_date.weekday() >= 5:  # Saturday or Sunday
        return 'weekend_processing'
    else:
        return 'weekday_processing'

def check_data_quality(**context):
    """Return task ID based on data quality"""
    # Simulate quality check
    quality_score = 95

    if quality_score >= 90:
        return 'high_quality_path'
    elif quality_score >= 70:
        return 'medium_quality_path'
    else:
        return 'low_quality_path'

with DAG(
    'branching_pipeline',
    start_date=datetime(2025, 1, 1),
    schedule_interval='@daily',
    catchup=False
) as dag:

    start = EmptyOperator(task_id='start')

    # Branch based on day of week
    branch_day = BranchPythonOperator(
        task_id='check_day_of_week',
        python_callable=decide_branch,
        provide_context=True
    )

    weekday = PythonOperator(
        task_id='weekday_processing',
        python_callable=lambda: print("Weekday processing")
    )

    weekend = PythonOperator(
        task_id='weekend_processing',
        python_callable=lambda: print("Weekend processing")
    )

    join = EmptyOperator(
        task_id='join',
        trigger_rule='none_failed_min_one_success'  # Continue if any branch succeeded
    )

    # Quality-based branching
    branch_quality = BranchPythonOperator(
        task_id='check_quality',
        python_callable=check_data_quality,
        provide_context=True
    )

    high_quality = PythonOperator(
        task_id='high_quality_path',
        python_callable=lambda: print("High quality - full processing")
    )

    medium_quality = PythonOperator(
        task_id='medium_quality_path',
        python_callable=lambda: print("Medium quality - partial processing")
    )

    low_quality = PythonOperator(
        task_id='low_quality_path',
        python_callable=lambda: print("Low quality - alert only")
    )

    end = EmptyOperator(
        task_id='end',
        trigger_rule='none_failed_min_one_success'
    )

    # Dependencies
    start >> branch_day >> [weekday, weekend] >> join
    join >> branch_quality >> [high_quality, medium_quality, low_quality] >> end
```

### Pattern 6: Backfill with Error Handling

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def process_date_range(start_date: str, end_date: str, **context):
    """Process data for date range with error handling"""
    from datetime import datetime

    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    current = start
    failures = []

    while current <= end:
        try:
            # Process single date
            logger.info(f"Processing {current.date()}")

            # Your processing logic here
            # Could call extract, transform, load functions

            logger.info(f"Successfully processed {current.date()}")

        except Exception as e:
            logger.error(f"Failed to process {current.date()}: {e}")
            failures.append((current.date(), str(e)))

        current += timedelta(days=1)

    if failures:
        failure_msg = "\n".join([f"{date}: {error}" for date, error in failures])
        raise AirflowException(f"Backfill had {len(failures)} failures:\n{failure_msg}")

    return f"Successfully processed {(end - start).days + 1} dates"

with DAG(
    'backfill_pipeline',
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,  # Manual trigger only
    catchup=False
) as dag:

    backfill = PythonOperator(
        task_id='backfill_data',
        python_callable=process_date_range,
        op_kwargs={
            'start_date': '2025-01-01',
            'end_date': '2025-01-31'
        },
        provide_context=True
    )

# Run with: airflow dags trigger backfill_pipeline
```

## Quick Reference

### Airflow CLI Commands
```bash
# List DAGs
airflow dags list

# Trigger DAG
airflow dags trigger my_dag

# Trigger with config
airflow dags trigger my_dag --conf '{"key": "value"}'

# Test task
airflow tasks test my_dag my_task 2025-10-18

# Backfill
airflow dags backfill my_dag \
  --start-date 2025-01-01 \
  --end-date 2025-01-31

# Clear task instances
airflow tasks clear my_dag --start-date 2025-10-18

# Pause/unpause DAG
airflow dags pause my_dag
airflow dags unpause my_dag

# Show DAG structure
airflow dags show my_dag

# List task instances
airflow tasks list my_dag --tree
```

### Schedule Intervals
```python
# Presets
'@once'      # Run once
'@hourly'    # 0 * * * *
'@daily'     # 0 0 * * *
'@weekly'    # 0 0 * * 0
'@monthly'   # 0 0 1 * *
'@yearly'    # 0 0 1 1 *

# Cron expressions
'0 */4 * * *'     # Every 4 hours
'0 2 * * *'       # Daily at 2 AM
'0 0 * * 1-5'     # Weekdays at midnight
'0 0 1 * *'       # First of month
'0 0 1 */3 *'     # First day of quarter

# Timedelta
timedelta(hours=6)  # Every 6 hours
```

### Trigger Rules
```python
'all_success'               # All parents succeeded (default)
'all_failed'                # All parents failed
'all_done'                  # All parents completed
'one_success'               # At least one parent succeeded
'one_failed'                # At least one parent failed
'none_failed'               # No parents failed (some may be skipped)
'none_failed_min_one_success'  # At least one succeeded, none failed
'none_skipped'              # No parents skipped
'always'                    # Always run
```

### XCom Patterns
```python
# Push value
ti.xcom_push(key='my_key', value=my_value)

# Pull value
value = ti.xcom_pull(task_ids='upstream_task', key='my_key')

# Pull from multiple tasks
values = ti.xcom_pull(task_ids=['task1', 'task2'])

# Return value (auto-pushed to 'return_value' key)
return my_value
```

## Anti-Patterns

```
❌ NEVER: Set depends_on_past=True without understanding
   → Can cause cascading failures across intervals

❌ NEVER: Use catchup=True for new DAGs with old start_date
   → Will trigger hundreds of backfill runs

❌ NEVER: Store large data in XCom
   → XCom for metadata only (<1MB), use external storage

❌ NEVER: Use sleep() in tasks
   → Use Sensors for waiting on conditions

❌ NEVER: Hardcode dates in tasks
   → Use {{ ds }}, {{ execution_date }}, context variables

❌ NEVER: Run tasks longer than schedule interval
   → Set execution_timeout, optimize task duration

❌ NEVER: Skip error handling in PythonOperator
   → Always wrap in try-except, raise AirflowException

❌ NEVER: Create tasks outside DAG context
   → All tasks must be defined within 'with DAG()' block

❌ NEVER: Use mutable default_args
   → Use new dict for each DAG

❌ NEVER: Ignore SLA monitoring
   → Set sla parameter for time-sensitive pipelines
```

## Related Skills

- `etl-patterns.md` - Data extraction and loading logic
- `stream-processing.md` - Real-time alternative to batch
- `pipeline-orchestration.md` - Advanced workflow patterns
- `data-validation.md` - Quality checks in pipelines

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
