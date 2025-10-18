---
name: data-pipeline-orchestration
description: Coordinating complex multi-step data workflows
---



# Pipeline Orchestration

**Scope**: Workflow engines, error handling, retries, monitoring
**Lines**: 383
**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)

## When to Use This Skill

Use this skill when:
- Coordinating complex multi-step data workflows
- Managing dependencies between pipeline stages
- Implementing robust error handling and retries
- Monitoring pipeline health and performance
- Handling partial failures and recovery
- Setting up alerting for pipeline failures
- Building idempotent and resumable pipelines

## Core Concepts

### Orchestration vs Execution
```
Orchestration (Control Plane)
  → Defines workflow, dependencies, schedules
  → Tools: Airflow, Prefect, Dagster, Step Functions
  → Manages: What runs, when, in what order

Execution (Data Plane)
  → Actual data processing work
  → Tools: Spark, dbt, custom Python/SQL
  → Manages: How data transforms
```

### Orchestration Patterns
```
Static DAG
  → Fixed workflow structure
  → Use when: Predictable pipeline steps
  → Example: Daily ETL with known tables

Dynamic DAG
  → Generate tasks at runtime
  → Use when: Data-driven workflows
  → Example: Process all partitions found in S3

Event-Driven
  → Trigger on external events
  → Use when: Real-time or on-demand processing
  → Example: Process file on S3 upload

Hybrid Batch + Stream
  → Combine scheduled and event-triggered
  → Use when: Lambda architecture
  → Example: Hourly batch + real-time stream
```

### Error Handling Strategies
```
Retry with Backoff
  → Exponential delays between retries
  → Use when: Transient failures expected

Circuit Breaker
  → Stop calling failing service
  → Use when: Cascading failures possible

Dead Letter Queue (DLQ)
  → Route failed items for later analysis
  → Use when: Partial processing acceptable

Compensating Transaction
  → Rollback on failure
  → Use when: Transactional consistency required
```

### Idempotency
```
Why Important: Retries shouldn't duplicate data

Techniques:
  → Upsert instead of insert
  → Write to temp, then swap atomically
  → Use execution_date as partition key
  → Check watermarks before processing
```

## Patterns

### Pattern 1: Prefect Workflow with Error Handling

```python
from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Configure retry behavior
@task(
    retries=3,
    retry_delay_seconds=60,
    timeout_seconds=3600,
    log_prints=True
)
def extract_data(source: str, date: str):
    """Extract data with automatic retries"""
    logger.info(f"Extracting from {source} for {date}")

    try:
        # Extraction logic
        data = perform_extraction(source, date)

        if not data:
            raise ValueError("No data extracted")

        return data

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise

@task(
    retries=2,
    retry_delay_seconds=30
)
def validate_data(data):
    """Validate extracted data"""
    logger.info(f"Validating {len(data)} records")

    # Validation logic
    if len(data) < 100:
        raise ValueError("Insufficient data volume")

    return data

@task(retries=3)
def transform_data(data):
    """Transform data"""
    logger.info("Transforming data")

    # Transformation logic
    transformed = apply_transformations(data)

    return transformed

@task(
    retries=5,
    retry_delay_seconds=[60, 120, 300, 600, 1200]  # Custom backoff
)
def load_data(data, target: str):
    """Load to target with aggressive retries"""
    logger.info(f"Loading to {target}")

    # Load logic
    load_to_warehouse(data, target)

    return {"status": "success", "rows": len(data)}

# Main flow
@flow(
    name="etl_pipeline",
    task_runner=ConcurrentTaskRunner(),
    retries=1,
    retry_delay_seconds=600
)
def etl_pipeline(date: str, sources: list[str]):
    """Main ETL pipeline with parallel extraction"""
    results = []

    # Extract from multiple sources in parallel
    extract_futures = []
    for source in sources:
        future = extract_data.submit(source, date)
        extract_futures.append(future)

    # Wait for all extractions
    extracted_data = [f.result() for f in extract_futures]

    # Combine and validate
    combined_data = combine_datasets(extracted_data)
    validated_data = validate_data(combined_data)

    # Transform and load sequentially
    transformed_data = transform_data(validated_data)
    result = load_data(transformed_data, "warehouse")

    return result

# Deploy with schedule
deployment = Deployment.build_from_flow(
    flow=etl_pipeline,
    name="daily_etl",
    schedule=CronSchedule(cron="0 2 * * *"),  # 2 AM daily
    parameters={"sources": ["db1", "db2", "api"]},
    work_queue_name="data-pipelines"
)

if __name__ == "__main__":
    deployment.apply()
```

### Pattern 2: State Management and Recovery

```python
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

class PipelineState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"

class StateManager:
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file"""
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())

        return {
            "runs": {},
            "checkpoints": {},
            "watermarks": {}
        }

    def _save_state(self):
        """Persist state to file"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(self.state, indent=2, default=str)
        )

    def start_run(self, run_id: str, metadata: Dict[str, Any]) -> None:
        """Mark run as started"""
        self.state["runs"][run_id] = {
            "state": PipelineState.RUNNING.value,
            "started_at": datetime.now().isoformat(),
            "metadata": metadata,
            "checkpoints": []
        }
        self._save_state()

    def checkpoint(self, run_id: str, stage: str, data: Any = None) -> None:
        """Save checkpoint for recovery"""
        if run_id not in self.state["runs"]:
            raise ValueError(f"Run {run_id} not found")

        checkpoint = {
            "stage": stage,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        self.state["runs"][run_id]["checkpoints"].append(checkpoint)
        self.state["checkpoints"][f"{run_id}:{stage}"] = checkpoint
        self._save_state()

    def complete_run(self, run_id: str, result: Any = None) -> None:
        """Mark run as complete"""
        self.state["runs"][run_id]["state"] = PipelineState.SUCCESS.value
        self.state["runs"][run_id]["completed_at"] = datetime.now().isoformat()
        self.state["runs"][run_id]["result"] = result
        self._save_state()

    def fail_run(self, run_id: str, error: str) -> None:
        """Mark run as failed"""
        self.state["runs"][run_id]["state"] = PipelineState.FAILED.value
        self.state["runs"][run_id]["failed_at"] = datetime.now().isoformat()
        self.state["runs"][run_id]["error"] = error
        self._save_state()

    def get_last_checkpoint(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get last checkpoint for recovery"""
        if run_id not in self.state["runs"]:
            return None

        checkpoints = self.state["runs"][run_id].get("checkpoints", [])
        return checkpoints[-1] if checkpoints else None

    def set_watermark(self, key: str, value: Any) -> None:
        """Update watermark for incremental processing"""
        self.state["watermarks"][key] = {
            "value": value,
            "updated_at": datetime.now().isoformat()
        }
        self._save_state()

    def get_watermark(self, key: str) -> Optional[Any]:
        """Get watermark value"""
        watermark = self.state["watermarks"].get(key)
        return watermark["value"] if watermark else None

# Resumable pipeline
class ResumablePipeline:
    def __init__(self, name: str, state_file: Path):
        self.name = name
        self.state_mgr = StateManager(state_file)
        self.run_id = None

    def run(self, params: Dict[str, Any], resume: bool = True):
        """Run pipeline with checkpointing"""
        self.run_id = f"{self.name}_{datetime.now().isoformat()}"

        try:
            # Check for existing run to resume
            if resume:
                last_checkpoint = self.state_mgr.get_last_checkpoint(self.run_id)
                if last_checkpoint:
                    print(f"Resuming from {last_checkpoint['stage']}")
                    return self._resume(last_checkpoint, params)

            # Start new run
            self.state_mgr.start_run(self.run_id, params)

            # Stage 1: Extract
            print("Stage 1: Extract")
            data = self.extract(params)
            self.state_mgr.checkpoint(self.run_id, "extract", {"row_count": len(data)})

            # Stage 2: Transform
            print("Stage 2: Transform")
            transformed = self.transform(data)
            self.state_mgr.checkpoint(self.run_id, "transform", {"row_count": len(transformed)})

            # Stage 3: Load
            print("Stage 3: Load")
            result = self.load(transformed)
            self.state_mgr.checkpoint(self.run_id, "load", result)

            # Complete
            self.state_mgr.complete_run(self.run_id, result)

            return result

        except Exception as e:
            self.state_mgr.fail_run(self.run_id, str(e))
            raise

    def _resume(self, checkpoint: Dict[str, Any], params: Dict[str, Any]):
        """Resume from last checkpoint"""
        stage = checkpoint["stage"]

        if stage == "extract":
            # Re-extract (could load from checkpoint if saved)
            data = self.extract(params)
            transformed = self.transform(data)
            result = self.load(transformed)

        elif stage == "transform":
            # Would need to restore data from checkpoint
            # For simplicity, re-running from extract
            data = self.extract(params)
            transformed = self.transform(data)
            result = self.load(transformed)

        elif stage == "load":
            # Transform complete, retry load only
            # Would restore transformed data
            result = checkpoint["data"]

        self.state_mgr.complete_run(self.run_id, result)
        return result

    def extract(self, params):
        # Extraction logic
        return []

    def transform(self, data):
        # Transformation logic
        return data

    def load(self, data):
        # Load logic
        return {"status": "success"}

# Usage
pipeline = ResumablePipeline("sales_etl", Path("/tmp/pipeline_state.json"))
result = pipeline.run({"date": "2025-10-18"}, resume=True)
```

### Pattern 3: Circuit Breaker for External Services

```python
from datetime import datetime, timedelta
from typing import Callable, Any
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Rejecting calls
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Reset on successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Increment failure count and open if threshold reached"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try again"""
        return (
            self.last_failure_time is not None and
            datetime.now() - self.last_failure_time >= timedelta(seconds=self.recovery_timeout)
        )

# Usage in pipeline
class APIExtractor:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=300,  # 5 minutes
            expected_exception=requests.RequestException
        )

    def extract(self, params: dict):
        """Extract with circuit breaker protection"""
        def _extract():
            response = requests.get(self.api_url, params=params)
            response.raise_for_status()
            return response.json()

        try:
            return self.circuit_breaker.call(_extract)
        except Exception as e:
            # Fallback to cached data or alternative source
            logger.error(f"Circuit breaker prevented call: {e}")
            return self._get_fallback_data(params)

    def _get_fallback_data(self, params: dict):
        """Fallback strategy when circuit is open"""
        # Could return cached data, empty dataset, or raise
        return []
```

### Pattern 4: Pipeline Monitoring and Alerting

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage

@dataclass
class PipelineMetrics:
    run_id: str
    pipeline_name: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    rows_processed: int
    rows_failed: int
    state: str
    error: Optional[str]

class PipelineMonitor:
    def __init__(
        self,
        alert_email: str,
        sla_minutes: int = 60,
        min_rows_expected: int = 1000
    ):
        self.alert_email = alert_email
        self.sla_minutes = sla_minutes
        self.min_rows_expected = min_rows_expected
        self.metrics_history: List[PipelineMetrics] = []

    def record_run(self, metrics: PipelineMetrics):
        """Record pipeline run metrics"""
        self.metrics_history.append(metrics)

        # Check SLAs and alert
        self._check_sla(metrics)
        self._check_data_volume(metrics)
        self._check_error_rate()

    def _check_sla(self, metrics: PipelineMetrics):
        """Alert if pipeline exceeded SLA"""
        if metrics.duration_seconds is None:
            return

        if metrics.duration_seconds > self.sla_minutes * 60:
            self._send_alert(
                subject=f"SLA Violation: {metrics.pipeline_name}",
                body=f"Pipeline took {metrics.duration_seconds/60:.1f} minutes "
                     f"(SLA: {self.sla_minutes} minutes)"
            )

    def _check_data_volume(self, metrics: PipelineMetrics):
        """Alert if data volume is unexpectedly low"""
        if metrics.rows_processed < self.min_rows_expected:
            self._send_alert(
                subject=f"Low Data Volume: {metrics.pipeline_name}",
                body=f"Only {metrics.rows_processed} rows processed "
                     f"(expected: {self.min_rows_expected})"
            )

    def _check_error_rate(self):
        """Alert if error rate is high"""
        recent_runs = [
            m for m in self.metrics_history[-10:]
            if m.pipeline_name == self.metrics_history[-1].pipeline_name
        ]

        if not recent_runs:
            return

        failed_runs = sum(1 for m in recent_runs if m.state == "failed")
        error_rate = failed_runs / len(recent_runs)

        if error_rate > 0.3:  # 30% failure rate
            self._send_alert(
                subject=f"High Error Rate: {recent_runs[0].pipeline_name}",
                body=f"Error rate: {error_rate*100:.1f}% over last {len(recent_runs)} runs"
            )

    def _send_alert(self, subject: str, body: str):
        """Send email alert"""
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = 'pipeline-alerts@company.com'
        msg['To'] = self.alert_email
        msg.set_content(body)

        # Would use actual SMTP server
        print(f"ALERT: {subject}\n{body}")

    def get_stats(self, pipeline_name: str, days: int = 7) -> dict:
        """Get pipeline statistics"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            m for m in self.metrics_history
            if m.pipeline_name == pipeline_name and m.started_at >= cutoff
        ]

        if not recent:
            return {}

        total_runs = len(recent)
        successful_runs = sum(1 for m in recent if m.state == "success")
        avg_duration = sum(
            m.duration_seconds for m in recent if m.duration_seconds
        ) / len([m for m in recent if m.duration_seconds])

        return {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "success_rate": successful_runs / total_runs,
            "avg_duration_minutes": avg_duration / 60,
            "avg_rows_processed": sum(m.rows_processed for m in recent) / total_runs
        }

# Usage
monitor = PipelineMonitor(
    alert_email="team@company.com",
    sla_minutes=30,
    min_rows_expected=5000
)

# After pipeline run
metrics = PipelineMetrics(
    run_id="run123",
    pipeline_name="daily_sales",
    started_at=datetime.now() - timedelta(minutes=45),
    completed_at=datetime.now(),
    duration_seconds=2700,  # 45 minutes
    rows_processed=10000,
    rows_failed=50,
    state="success",
    error=None
)

monitor.record_run(metrics)
stats = monitor.get_stats("daily_sales", days=7)
print(stats)
```

## Quick Reference

### Common Orchestration Tools
```
Apache Airflow
  → Mature, Python-based, largest community
  → Use when: Complex dependencies, scheduling

Prefect
  → Modern, Python-native, better error handling
  → Use when: Dynamic workflows, developer-friendly

Dagster
  → Asset-oriented, testing-first
  → Use when: Data assets, strong typing

AWS Step Functions
  → Serverless, AWS-native
  → Use when: AWS ecosystem, event-driven

Temporal
  → Durable execution, microservices
  → Use when: Long-running workflows, reliability
```

### Retry Strategies
```python
# Exponential backoff
retry_delays = [60, 120, 300, 600, 1200]  # 1m, 2m, 5m, 10m, 20m

# Linear backoff
retry_delays = [60] * 5  # 1m each time

# Fibonacci backoff
retry_delays = [60, 60, 120, 180, 300]  # 1m, 1m, 2m, 3m, 5m
```

### Monitoring Metrics
```
Pipeline Metrics:
  - Duration (p50, p95, p99)
  - Rows processed
  - Success rate
  - Error rate
  - SLA compliance

Data Quality Metrics:
  - Null rate
  - Duplicate rate
  - Schema validation failures
  - Data freshness
```

## Anti-Patterns

```
❌ NEVER: Run pipelines without idempotency
   → Use upserts, check watermarks, enable safe retries

❌ NEVER: Ignore partial failures
   → Track failed records, implement DLQ

❌ NEVER: Skip monitoring and alerting
   → Monitor duration, volume, errors

❌ NEVER: Use unbounded retries
   → Set max retries, implement circuit breakers

❌ NEVER: Hardcode dependencies
   → Use orchestrator's dependency management

❌ NEVER: Skip state persistence
   → Save checkpoints for resumability

❌ NEVER: Run long tasks in orchestrator
   → Offload heavy compute to workers

❌ NEVER: Ignore SLA requirements
   → Set timeouts, monitor compliance

❌ NEVER: Deploy without backfill strategy
   → Plan for historical data reprocessing

❌ NEVER: Skip testing failure scenarios
   → Test retries, timeouts, recovery paths
```

## Related Skills

- `batch-processing.md` - Airflow DAG patterns
- `etl-patterns.md` - Data pipeline logic
- `stream-processing.md` - Real-time orchestration
- `data-validation.md` - Quality gates in pipelines

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
