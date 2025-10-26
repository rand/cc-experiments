---
name: debugging-production-debugging
description: Non-intrusive debugging in production environments with feature flags, dynamic logging, and observability correlation
---

# Production Debugging

**Scope**: Non-intrusive debugging, dynamic logging, feature flags, sampling profilers, trace correlation, production debugging checklist

**Lines**: 430

**Last Updated**: 2025-10-26

---

## When to Use This Skill

Use this skill when:
- Debugging issues that only occur in production
- Investigating intermittent failures or race conditions
- Analyzing performance degradation in live systems
- Troubleshooting issues without disrupting users
- Correlating application behavior with infrastructure metrics
- Debugging third-party integrations or external dependencies
- Investigating issues in high-traffic or mission-critical systems
- Collecting diagnostic data without deploying code changes

**Don't use** for:
- Local development debugging (use IDE debuggers)
- Pre-production testing (use breakpoints, step debugging)
- Controlled environments with low traffic (standard debugging tools work)

---

## Core Concepts

### Non-Intrusive Debugging Principles

**Why**: Production systems require debugging without:
- Service restarts or downtime
- User-facing disruptions
- Performance degradation
- Breaking SLAs or SLOs

**Key Principles**:
1. **Minimal overhead**: Use sampling, not continuous monitoring
2. **Dynamic control**: Enable/disable debugging without deploys
3. **Targeted investigation**: Debug specific users, requests, or code paths
4. **Correlation**: Link application logs to traces, metrics, infrastructure events
5. **Safe rollback**: Disable debugging immediately if issues arise

### Production Debugging Layers

```
Layer 1: Observability (always-on)
├─ Structured logs with trace IDs
├─ Metrics (RED: Rate, Errors, Duration)
└─ Distributed traces (sampled)

Layer 2: Dynamic Debugging (on-demand)
├─ Feature flags for debug mode
├─ Dynamic log level changes
├─ Sampling profilers (CPU, memory)
└─ Targeted verbose logging

Layer 3: Advanced Diagnostics (rare)
├─ Traffic shadowing/replay
├─ Core dumps (post-crash analysis)
└─ Heap dumps (memory leaks)
```

---

## Patterns

### Pattern 1: Feature Flags for Debug Mode

```python
from launchdarkly import LDClient, Config, Context
from opentelemetry import trace
import logging

# Initialize LaunchDarkly client
ld_client = LDClient(sdk_key="your-sdk-key")

# Get tracer
tracer = trace.get_tracer(__name__)

@app.get("/api/orders/{order_id}")
async def get_order(order_id: str, user_id: str):
    # Create context for feature flag
    context = Context.builder(user_id).set("order_id", order_id).build()

    # Check if debug mode enabled for this user
    debug_enabled = ld_client.variation(
        "debug-mode",
        context,
        False  # Default: disabled
    )

    with tracer.start_as_current_span("get_order") as span:
        span.set_attribute("debug_enabled", debug_enabled)

        if debug_enabled:
            # Enhanced logging for debugging
            logging.info(
                "DEBUG: Fetching order",
                extra={
                    "order_id": order_id,
                    "user_id": user_id,
                    "trace_id": span.get_span_context().trace_id,
                }
            )

        try:
            order = await fetch_order(order_id, debug=debug_enabled)

            if debug_enabled:
                # Log intermediate state
                logging.debug(
                    "DEBUG: Order fetched successfully",
                    extra={
                        "order": order.dict(),
                        "cache_hit": order.from_cache,
                    }
                )

            return order

        except Exception as e:
            if debug_enabled:
                # Detailed error context
                logging.error(
                    "DEBUG: Order fetch failed",
                    extra={
                        "order_id": order_id,
                        "error": str(e),
                        "stack_trace": traceback.format_exc(),
                    },
                    exc_info=True
                )
            raise
```

**Feature Flag Configuration** (LaunchDarkly):
```json
{
  "key": "debug-mode",
  "name": "Production Debug Mode",
  "variations": [true, false],
  "defaultVariation": false,
  "rules": [
    {
      "clauses": [
        {"attribute": "email", "op": "contains", "values": ["@yourcompany.com"]}
      ],
      "variation": true
    },
    {
      "clauses": [
        {"attribute": "user_id", "op": "in", "values": ["user_123", "user_456"]}
      ],
      "variation": true
    }
  ]
}
```

### Pattern 2: Dynamic Log Level Changes

```python
import logging
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class LogLevelUpdate(BaseModel):
    module: str
    level: str  # DEBUG, INFO, WARNING, ERROR

@app.post("/admin/log-level")
async def update_log_level(update: LogLevelUpdate, admin_token: str):
    """
    Dynamically change log level without restart.
    Protected by admin token.
    """
    if admin_token != os.getenv("ADMIN_TOKEN"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Validate log level
    level = getattr(logging, update.level.upper(), None)
    if level is None:
        raise HTTPException(status_code=400, detail="Invalid log level")

    # Update logger level
    target_logger = logging.getLogger(update.module)
    target_logger.setLevel(level)

    logger.info(
        "Log level updated",
        module=update.module,
        new_level=update.level,
        admin=True
    )

    return {
        "module": update.module,
        "level": update.level,
        "message": f"Log level for {update.module} set to {update.level}"
    }

# Usage example
@app.get("/api/users")
async def list_users():
    # This will only log if module level >= DEBUG
    logger.debug("Fetching users from database", cache_check=True)

    users = await db.get_users()

    logger.info("Users fetched", count=len(users))

    return users
```

**Dynamic log level via curl**:
```bash
# Enable DEBUG logging for specific module
curl -X POST http://api.example.com/admin/log-level \
  -H "Content-Type: application/json" \
  -d '{"module": "app.services.user", "level": "DEBUG"}' \
  --header "admin_token: secret"

# Revert to INFO after debugging
curl -X POST http://api.example.com/admin/log-level \
  -H "Content-Type: application/json" \
  -d '{"module": "app.services.user", "level": "INFO"}' \
  --header "admin_token: secret"
```

### Pattern 3: Sampling Profiler (Minimal Overhead)

```python
import cProfile
import pstats
from py_spy import SpyProfiler
import asyncio
from datetime import datetime, timedelta

class ProductionProfiler:
    """
    Sampling profiler with minimal overhead.
    Use py-spy (sampling) instead of cProfile (instrumentation).
    """

    def __init__(self, sample_rate_hz: int = 100):
        self.sample_rate_hz = sample_rate_hz
        self.profiler = None
        self.profiling_active = False

    async def start_profiling(self, duration_seconds: int = 30):
        """
        Profile for a limited duration.
        """
        if self.profiling_active:
            raise RuntimeError("Profiling already active")

        self.profiling_active = True

        # Use py-spy for sampling (low overhead)
        # Install: pip install py-spy
        # Run: py-spy record -o profile.svg --pid <pid> --duration 30

        # For in-process profiling (higher overhead):
        profiler = cProfile.Profile()
        profiler.enable()

        try:
            # Profile for duration
            await asyncio.sleep(duration_seconds)
        finally:
            profiler.disable()
            self.profiling_active = False

            # Save profile data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/tmp/profile_{timestamp}.pstats"
            profiler.dump_stats(filename)

            # Generate human-readable report
            stats = pstats.Stats(filename)
            stats.sort_stats('cumulative')
            stats.print_stats(50)  # Top 50 functions

            return filename

# FastAPI endpoint for on-demand profiling
from fastapi import BackgroundTasks

profiler = ProductionProfiler()

@app.post("/admin/profile")
async def start_profiling(
    duration: int = 30,
    admin_token: str = None,
    background_tasks: BackgroundTasks = None
):
    """
    Start profiling for specified duration.
    Returns profile file location.
    """
    if admin_token != os.getenv("ADMIN_TOKEN"):
        raise HTTPException(status_code=403)

    if profiler.profiling_active:
        return {"status": "already_profiling"}

    # Run profiling in background
    background_tasks.add_task(profiler.start_profiling, duration)

    return {
        "status": "profiling_started",
        "duration_seconds": duration,
        "message": "Profile data will be available in /tmp/"
    }
```

**Using py-spy externally** (recommended for production):
```bash
# Install py-spy
pip install py-spy

# Profile running Python process (by PID)
py-spy record -o profile.svg --pid 12345 --duration 30

# Profile with higher sample rate
py-spy record -o profile.svg --pid 12345 --rate 200 --duration 30

# Profile specific subprocesses
py-spy record -o profile.svg --pid 12345 --subprocesses --duration 30

# Generate flamegraph
py-spy record -o flamegraph.svg --format flamegraph --pid 12345 --duration 30
```

### Pattern 4: Correlation with Observability Data

```python
from opentelemetry import trace
from opentelemetry.trace import SpanKind
import structlog
import httpx

# Configure structured logging with trace correlation
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)

@app.get("/api/process")
async def process_request(request_id: str):
    # Create span
    with tracer.start_as_current_span(
        "process_request",
        kind=SpanKind.SERVER
    ) as span:
        # Get trace context
        trace_id = format(span.get_span_context().trace_id, '032x')
        span_id = format(span.get_span_context().span_id, '016x')

        # Add trace context to all logs
        log = logger.bind(
            trace_id=trace_id,
            span_id=span_id,
            request_id=request_id
        )

        log.info("Processing request started")

        try:
            # Call external service
            with tracer.start_as_current_span("external_api_call") as child_span:
                external_trace_id = format(
                    child_span.get_span_context().trace_id, '032x'
                )

                log.debug(
                    "Calling external API",
                    external_trace_id=external_trace_id
                )

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.example.com/data",
                        headers={
                            "X-Request-ID": request_id,
                            "X-Trace-ID": trace_id
                        }
                    )

                child_span.set_attribute("http.status_code", response.status_code)

                log.info(
                    "External API response",
                    status_code=response.status_code,
                    response_time_ms=child_span.get_attribute("duration_ms")
                )

            log.info("Processing completed successfully")
            return {"status": "success", "trace_id": trace_id}

        except Exception as e:
            log.error(
                "Processing failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            span.record_exception(e)
            raise
```

**Correlation Query** (Grafana Loki + Tempo):
```promql
# Find all logs for a specific trace
{app="api-service"} | json | trace_id="a1b2c3d4e5f6g7h8"

# Find errors with trace context
{app="api-service"} | json | level="error" | trace_id!=""

# Correlate slow requests (logs + traces)
{app="api-service"} | json | duration_ms > 1000
```

### Pattern 5: Production Debugging Checklist

```python
import asyncio
from typing import Dict, Any
from datetime import datetime
from opentelemetry import trace
import structlog

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)

class ProductionDebugger:
    """
    Comprehensive production debugging toolkit.
    """

    def __init__(self):
        self.debug_sessions = {}

    async def debug_request(
        self,
        request_id: str,
        user_id: str = None,
        enable_verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Debug a specific request with full context.
        """
        with tracer.start_as_current_span("debug_session") as span:
            trace_id = format(span.get_span_context().trace_id, '032x')

            log = logger.bind(
                trace_id=trace_id,
                request_id=request_id,
                user_id=user_id,
                debug_session=True
            )

            debug_data = {
                "trace_id": trace_id,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {}
            }

            # Check 1: Database connectivity
            try:
                await db.execute("SELECT 1")
                debug_data["checks"]["database"] = "OK"
                log.info("Database check passed")
            except Exception as e:
                debug_data["checks"]["database"] = f"FAILED: {str(e)}"
                log.error("Database check failed", error=str(e))

            # Check 2: Cache connectivity
            try:
                await redis.ping()
                debug_data["checks"]["cache"] = "OK"
                log.info("Cache check passed")
            except Exception as e:
                debug_data["checks"]["cache"] = f"FAILED: {str(e)}"
                log.error("Cache check failed", error=str(e))

            # Check 3: External API reachability
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.example.com/health",
                        timeout=5.0
                    )
                    debug_data["checks"]["external_api"] = {
                        "status": "OK",
                        "status_code": response.status_code,
                        "latency_ms": response.elapsed.total_seconds() * 1000
                    }
                    log.info("External API check passed")
            except Exception as e:
                debug_data["checks"]["external_api"] = f"FAILED: {str(e)}"
                log.error("External API check failed", error=str(e))

            # Check 4: Feature flag status
            if user_id:
                debug_data["feature_flags"] = await get_user_flags(user_id)
                log.info("Feature flags retrieved", flags=debug_data["feature_flags"])

            # Check 5: Recent errors for this user
            if user_id:
                recent_errors = await get_recent_errors(user_id, limit=5)
                debug_data["recent_errors"] = recent_errors
                log.info("Recent errors retrieved", count=len(recent_errors))

            if enable_verbose:
                # Additional verbose checks
                debug_data["system"] = {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage('/').percent
                }
                log.debug("System metrics collected", system=debug_data["system"])

            return debug_data
```

---

## Quick Reference

### Production Debugging Checklist

```markdown
## Pre-Investigation
- [ ] Identify trace ID from error logs
- [ ] Check if issue is user-specific or global
- [ ] Verify recent deployments or config changes
- [ ] Check infrastructure metrics (CPU, memory, network)

## Investigation
- [ ] Enable debug logging for specific user/request
- [ ] Correlate logs with distributed traces
- [ ] Check for errors in dependent services
- [ ] Review recent alerts or anomalies
- [ ] Compare current behavior to baseline

## Data Collection
- [ ] Capture trace IDs for failed requests
- [ ] Export relevant log entries
- [ ] Collect profiling data (if performance issue)
- [ ] Screenshot error state in monitoring dashboards

## Debugging Actions
- [ ] Enable feature flag for targeted users
- [ ] Increase log level for specific modules
- [ ] Run sampling profiler for 30-60 seconds
- [ ] Replay request in staging (if possible)

## Resolution
- [ ] Disable debug mode after investigation
- [ ] Revert log level changes
- [ ] Document findings in incident report
- [ ] Create follow-up tasks for permanent fixes
```

### Feature Flag Providers

| Provider | Use Case | Integration |
|----------|----------|-------------|
| **LaunchDarkly** | Enterprise, full-featured | Python, Go, Node.js SDKs |
| **Split.io** | A/B testing + feature flags | All major languages |
| **Unleash** | Open source, self-hosted | Docker, Kubernetes |
| **Flagsmith** | Open source, SaaS option | REST API, SDKs |

### Sampling Profilers by Language

```bash
# Python: py-spy (recommended)
py-spy record -o flamegraph.svg --pid <pid> --duration 30

# Go: pprof (built-in)
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# Node.js: 0x
npx 0x --output-dir ./profile node server.js

# Rust: perf + flamegraph
perf record -F 99 -p <pid> -g -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > flamegraph.svg
```

---

## Anti-Patterns

### ❌ Using Breakpoints in Production

```python
# WRONG: Breakpoint stops production server
import pdb; pdb.set_trace()  # NEVER in production!

# CORRECT: Use logging and tracing
logger.debug("Debugging checkpoint", state=current_state)
```

### ❌ Enabling Verbose Logging Globally

```python
# WRONG: Global DEBUG logging kills performance
logging.basicConfig(level=logging.DEBUG)  # Generates GB of logs!

# CORRECT: Targeted debug logging
if debug_enabled_for_user(user_id):
    logger.debug("User-specific debug info", user_id=user_id)
```

### ❌ Profiling Without Time Limits

```python
# WRONG: Profiler runs indefinitely
profiler.enable()
# No stop condition!

# CORRECT: Time-limited profiling
profiler.enable()
await asyncio.sleep(30)  # Profile for 30 seconds
profiler.disable()
```

### ❌ Forgetting Trace Correlation

```python
# WRONG: Logs without trace context
logger.error("Request failed")  # Can't correlate with trace!

# CORRECT: Include trace ID in logs
logger.error(
    "Request failed",
    trace_id=trace_id,
    span_id=span_id
)
```

---

## Related Skills

- **observability/distributed-tracing.md** - Trace context and correlation
- **observability/structured-logging.md** - Production-ready logging
- **testing/performance-testing.md** - Load testing to reproduce issues
- **debugging/distributed-systems-debugging.md** - Cross-service debugging

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
