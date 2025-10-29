# Production Debugging Reference

Comprehensive reference for production debugging practices, tools, and techniques.

**Version**: 1.0
**Last Updated**: 2025-10-29
**Lines**: ~3,500

---

## Table of Contents

1. [Production Debugging Philosophy](#1-production-debugging-philosophy)
2. [Safety and Risk Assessment](#2-safety-and-risk-assessment)
3. [Distributed Tracing](#3-distributed-tracing)
4. [Memory Debugging](#4-memory-debugging)
5. [Core Dump Analysis](#5-core-dump-analysis)
6. [Network Debugging](#6-network-debugging)
7. [Database Debugging](#7-database-debugging)
8. [Container Debugging](#8-container-debugging)
9. [Live Debugging Tools](#9-live-debugging-tools)
10. [Performance Profiling](#10-performance-profiling)
11. [APM Integration](#11-apm-integration)
12. [Common Production Issues](#12-common-production-issues)
13. [Anti-Patterns](#13-anti-patterns)

---

## 1. Production Debugging Philosophy

### 1.1 Core Principles

**Minimal Impact Principle**
```
Every debug action must minimize customer impact:
├─ Use read-only operations when possible
├─ Debug replicas, not primary instances
├─ Sample data instead of collecting everything
├─ Set strict timeouts on debug operations
└─ Monitor impact of debug tools themselves
```

**Non-Invasive Monitoring**
```
Observe system without modifying behavior:
├─ Use existing logs and metrics first
├─ Add instrumentation through deployment, not live
├─ Leverage passive monitoring (metrics, traces)
├─ Avoid stopping or pausing processes
└─ Use sampling for profiling
```

**Data-Driven Investigation**
```
Make decisions based on data, not assumptions:
├─ Collect objective evidence (metrics, logs, traces)
├─ Use statistical analysis for patterns
├─ Correlate events across time and services
├─ Validate hypotheses with experiments
└─ Document findings systematically
```

### 1.2 Production Debugging Lifecycle

**Phase 1: Detection and Triage (0-5 minutes)**
```
1. Alert fires or user report received
2. Verify issue is real (not false positive)
3. Assess severity and customer impact
4. Check for recent changes (deployments, configs)
5. Review existing metrics and dashboards
6. Decide: Can fix without deep debugging?
```

**Phase 2: Data Collection (5-30 minutes)**
```
1. Gather baseline data:
   - Current metrics vs normal baseline
   - Error logs from affected timeframe
   - Distributed traces for failing requests
   - Resource utilization (CPU, memory, disk, network)

2. Identify patterns:
   - Is it specific to certain requests/users?
   - Does it correlate with specific services?
   - Is it time-based (cron job, traffic pattern)?
   - Are there cascading failures?

3. Prioritize investigation targets:
   - Services with highest error rates
   - Slowest components in trace spans
   - Resources approaching limits
   - Recently changed components
```

**Phase 3: Hypothesis and Testing (30 minutes - 2 hours)**
```
1. Form hypotheses based on data:
   - Resource exhaustion (memory leak, connection pool)
   - Configuration error (wrong limit, bad connection string)
   - External dependency failure (database, API)
   - Code bug (null pointer, race condition)

2. Test hypotheses safely:
   - In staging/test environment first
   - On single replica, not entire fleet
   - With feature flags for controlled rollout
   - With rollback plan ready

3. Collect additional data:
   - Heap dumps if memory suspected
   - Core dumps if crashes occurring
   - Detailed traces with high sampling
   - Network captures if connectivity suspected
```

**Phase 4: Resolution and Validation (varies)**
```
1. Implement fix:
   - Rollback if recent deployment
   - Configuration change if misconfigured
   - Scale resources if exhaustion
   - Code fix if bug identified

2. Validate fix:
   - Metrics return to baseline
   - Error rates drop to acceptable
   - Latency within SLOs
   - No new issues introduced

3. Monitor stability:
   - Watch for regression (15+ minutes)
   - Check related services
   - Verify customer reports resolved
```

**Phase 5: Postmortem and Prevention (24-72 hours)**
```
1. Document findings:
   - Root cause analysis
   - Timeline of events
   - Debug techniques used
   - Resolution steps

2. Create preventions:
   - Automated alerts for early detection
   - Runbooks for faster resolution
   - Code fixes to prevent recurrence
   - Infrastructure improvements

3. Share learnings:
   - Team postmortem meeting
   - Update documentation
   - Create training materials
```

### 1.3 Debugging Decision Trees

**Decision Tree: Which Debug Approach?**
```
Issue detected
├─ Logs/metrics show root cause?
│  └─ YES → Use existing observability
│  └─ NO → Need deeper investigation
│     ├─ High error rate, specific service?
│     │  └─ YES → Distributed tracing
│     ├─ Memory growing over time?
│     │  └─ YES → Memory profiling
│     ├─ Process crashing?
│     │  └─ YES → Core dump analysis
│     ├─ Network timeouts/errors?
│     │  └─ YES → Network debugging
│     ├─ Slow database queries?
│     │  └─ YES → Database profiling
│     └─ Performance degradation?
│        └─ YES → CPU profiling
```

**Decision Tree: Debug in Production vs Staging?**
```
Can reproduce in staging?
├─ YES → Debug in staging (safer)
│  └─ Validate fix in staging
│     └─ Deploy to production with monitoring
├─ NO → Must debug in production
   ├─ Assess risk level:
   │  ├─ High (can cause outage) → Wait for maintenance window
   │  ├─ Medium (may impact performance) → Debug replica, set limits
   │  └─ Low (read-only, sampling) → Proceed with monitoring
   └─ Set safety measures:
      ├─ Timeout on all operations
      ├─ Resource limits (CPU, memory)
      ├─ Team awareness
      └─ Rollback plan ready
```

**Decision Tree: Immediate Fix vs Deep Root Cause?**
```
Customer impact severe?
├─ YES (SEV-1/SEV-2) → MITIGATE FIRST
│  ├─ Rollback recent deployment
│  ├─ Scale resources
│  ├─ Enable circuit breaker
│  ├─ Route around failing component
│  └─ Then investigate root cause offline
├─ NO (SEV-3/SEV-4) → Can investigate thoroughly
   ├─ Collect comprehensive data
   ├─ Test hypotheses carefully
   └─ Implement proper fix
```

### 1.4 Debugging Mindset

**Systematic Investigation**
```
1. Observe: What is actually happening? (not what you think)
2. Hypothesize: What could cause this?
3. Predict: If hypothesis is true, what else would be true?
4. Test: Does evidence support or contradict?
5. Refine: Update hypothesis based on results
6. Repeat: Until root cause found
```

**Avoid Cognitive Biases**
```
Confirmation Bias:
├─ Don't just look for evidence supporting your theory
├─ Actively seek contradicting evidence
└─ Consider alternative explanations

Availability Bias:
├─ Don't assume recent or memorable issues
├─ Look at actual data and patterns
└─ Consider rare but possible causes

Anchoring Bias:
├─ Don't fixate on first hypothesis
├─ Re-evaluate as new data arrives
└─ Be willing to change direction
```

**Effective Communication**
```
During investigation:
├─ Update stakeholders regularly (every 15-30 min)
├─ Share what you've tried and ruled out
├─ Ask for help when stuck
└─ Document findings in real-time

In postmortem:
├─ Focus on timeline and facts
├─ Explain debugging process used
├─ Share what worked and didn't
└─ Document lessons learned
```

---

## 2. Safety and Risk Assessment

### 2.1 Risk Categories

**High Risk Operations** (avoid in production or use extreme caution)
```
Debugger Attachment:
├─ Pauses process execution
├─ Can cause timeouts and cascading failures
├─ Risk: CRITICAL
└─ Alternative: Use profiling tools, not debuggers

Heap Dumps on Large Processes:
├─ Can pause process for seconds
├─ Generates multi-GB files
├─ Risk: HIGH
└─ Alternative: Use sampling profilers, jemalloc heap profiling

Full Traffic Tracing:
├─ High CPU and network overhead
├─ Can overwhelm tracing backend
├─ Risk: HIGH
└─ Alternative: Sample 1-10% of requests

Modifying Code/Config Live:
├─ Unpredictable behavior
├─ No version control
├─ Risk: CRITICAL
└─ Alternative: Deploy changes properly
```

**Medium Risk Operations** (acceptable with safeguards)
```
System Call Tracing (strace):
├─ Significant performance impact (2-10x slowdown)
├─ Risk: MEDIUM
├─ Safeguards:
│  ├─ Only trace one replica
│  ├─ Set timeout (30-60 seconds max)
│  ├─ Monitor replica health
│  └─ Have team ready to kill if needed

Live Profiling (py-spy, pprof):
├─ Moderate CPU overhead (5-15%)
├─ Risk: MEDIUM
├─ Safeguards:
│  ├─ Use sampling (50-100 Hz)
│  ├─ Limit duration (60 seconds)
│  ├─ Monitor replica load
│  └─ Profile during low traffic if possible

Core Dump Analysis:
├─ Requires keeping crashed process memory
├─ May contain sensitive data
├─ Risk: MEDIUM
├─ Safeguards:
│  ├─ Encrypt core dumps
│  ├─ Limit retention (7-30 days)
│  ├─ Restrict access
│  └─ Sanitize before sharing
```

**Low Risk Operations** (safe for production)
```
Metrics Collection:
├─ Minimal overhead (<1%)
├─ Risk: LOW
└─ Already running continuously

Log Analysis:
├─ Read-only operation
├─ Risk: LOW
└─ Analyze offline, no production impact

Distributed Tracing (sampled):
├─ Low overhead with sampling
├─ Risk: LOW
├─ Keep sampling rate reasonable (1-10%)

Network Packet Capture (filtered):
├─ Minimal overhead with filters
├─ Risk: LOW
├─ Filter to specific hosts/ports
```

### 2.2 Pre-Debug Safety Checklist

**Before Any Production Debug Session**:
```yaml
environment:
  - [ ] Confirmed issue exists in production
  - [ ] Checked if reproducible in staging
  - [ ] Verified production instance (not development)
  - [ ] Noted current load and traffic patterns

safety:
  - [ ] Selected replica, not primary/leader
  - [ ] Confirmed replica can be taken out of rotation
  - [ ] Set timeout for all debug operations
  - [ ] Configured resource limits (CPU, memory)
  - [ ] Have rollback/abort plan

communication:
  - [ ] Notified team in war room or chat
  - [ ] IC aware and approved (if SEV-1/SEV-2)
  - [ ] On-call engineer available if needed
  - [ ] Documented what will be done

data:
  - [ ] Exported relevant logs for offline analysis
  - [ ] Captured baseline metrics
  - [ ] Saved example failing requests
  - [ ] Identified time window of interest
```

### 2.3 Safety Patterns

**Pattern: Debug Replica, Not Primary**
```bash
# Identify primary/leader
kubectl get pods -l app=myapp -o wide
# Look for leader annotation or check service discovery

# For databases, use read replica
# For stateless services, pick specific replica

# Remove from load balancer
kubectl label pod myapp-replica-2 debug=true
# Update service selector to exclude debug=true

# Now safe to debug this replica
py-spy record --pid $(pgrep -f myapp)

# When done, restore
kubectl label pod myapp-replica-2 debug-
```

**Pattern: Automatic Timeout**
```bash
# Always use timeout for debug operations
timeout 30s strace -p 12345

# Or built into script
#!/bin/bash
set -e
TIMEOUT=60

timeout $TIMEOUT py-spy record \
  --pid "$PID" \
  --output profile.svg \
  --rate 100

if [ $? -eq 124 ]; then
  echo "Timeout reached, profiling stopped safely"
fi
```

**Pattern: Resource-Limited Debugging**
```bash
# Limit CPU usage
nice -n 19 strace -p 12345  # Lowest priority
taskset -c 0 strace -p 12345  # Pin to one core

# Limit memory usage with cgroups
cgcreate -g memory:/debug
echo 512M > /sys/fs/cgroup/memory/debug/memory.limit_in_bytes
cgexec -g memory:debug strace -p 12345

# Or use ulimit
ulimit -m 512000  # 512MB
ulimit -t 60      # 60 seconds CPU time
```

**Pattern: Circuit Breaker for Debug Tools**
```python
import psutil
import time
from typing import Optional

class DebugSafetyMonitor:
    """Monitor system health during debug operations."""

    def __init__(
        self,
        max_cpu_percent: float = 80.0,
        max_memory_percent: float = 85.0,
        check_interval: float = 1.0
    ):
        self.max_cpu = max_cpu_percent
        self.max_memory = max_memory_percent
        self.check_interval = check_interval
        self.violations = 0
        self.max_violations = 3

    def is_safe_to_continue(self) -> tuple[bool, Optional[str]]:
        """Check if it's safe to continue debugging."""
        cpu_percent = psutil.cpu_percent(interval=self.check_interval)
        memory_percent = psutil.virtual_memory().percent

        if cpu_percent > self.max_cpu:
            self.violations += 1
            if self.violations >= self.max_violations:
                return False, f"CPU usage too high: {cpu_percent}%"

        if memory_percent > self.max_memory:
            self.violations += 1
            if self.violations >= self.max_violations:
                return False, f"Memory usage too high: {memory_percent}%"

        if cpu_percent < self.max_cpu and memory_percent < self.max_memory:
            self.violations = max(0, self.violations - 1)

        return True, None

    def monitor_operation(self, operation_func, *args, **kwargs):
        """Run operation with continuous safety monitoring."""
        import threading
        import signal

        stop_event = threading.Event()
        error_msg = None

        def safety_check():
            nonlocal error_msg
            while not stop_event.is_set():
                safe, msg = self.is_safe_to_continue()
                if not safe:
                    error_msg = msg
                    # Send SIGTERM to main thread
                    signal.pthread_kill(
                        threading.main_thread().ident,
                        signal.SIGTERM
                    )
                    break
                time.sleep(self.check_interval)

        monitor_thread = threading.Thread(target=safety_check, daemon=True)
        monitor_thread.start()

        try:
            result = operation_func(*args, **kwargs)
            return result
        finally:
            stop_event.set()
            monitor_thread.join(timeout=2)
            if error_msg:
                raise RuntimeError(f"Debug operation aborted: {error_msg}")
```

### 2.4 Incident Escalation

**When to Escalate Debug Session**:
```
Escalate immediately if:
├─ Debug tool causes performance degradation
├─ Error rates increase during debug session
├─ Customer complaints about slowness
├─ System becomes unstable
└─ Can't safely continue investigation

Escalation steps:
1. STOP all debug operations immediately
2. REMOVE debug tools and restore replica
3. NOTIFY IC and team
4. ASSESS if debug contributed to instability
5. DOCUMENT what was attempted
6. REGROUP with team to plan safer approach
```

---

## 3. Distributed Tracing

### 3.1 Tracing Fundamentals

**Trace Components**:
```
Trace: End-to-end request path
├─ Trace ID: Unique identifier (e.g., 5f3c8d2e9a1b4f7c)
├─ Spans: Individual operations
│  ├─ Span ID: Unique identifier
│  ├─ Parent Span ID: Forms tree structure
│  ├─ Start/End timestamps
│  ├─ Service name
│  ├─ Operation name
│  ├─ Tags: Key-value metadata
│  └─ Logs: Timestamped events
└─ Context: Propagated across services
   ├─ Trace ID (same for entire request)
   ├─ Parent Span ID
   └─ Sampling decision
```

**Example Trace Structure**:
```
Trace ID: 5f3c8d2e9a1b4f7c
Total Duration: 245ms

Span 1: api-gateway.handle_request (245ms)
├─ service: api-gateway
├─ http.method: GET
├─ http.url: /api/users/123
├─ http.status_code: 200
│
├─ Span 2: auth.validate_token (12ms)
│  ├─ service: auth-service
│  ├─ cache.hit: true
│  └─ user.id: 123
│
├─ Span 3: user-service.get_user (180ms) ← SLOW
│  ├─ service: user-service
│  │
│  ├─ Span 4: postgres.query (170ms) ← BOTTLENECK
│  │  ├─ service: user-service
│  │  ├─ db.system: postgresql
│  │  ├─ db.statement: SELECT * FROM users WHERE id = $1
│  │  ├─ db.rows_affected: 1
│  │  └─ NOTE: Missing index on users table!
│  │
│  └─ Span 5: cache.set (8ms)
│     ├─ service: user-service
│     └─ cache.key: user:123
│
└─ Span 6: response.serialize (3ms)
   └─ service: api-gateway
```

### 3.2 OpenTelemetry Setup

**Automatic Instrumentation (Python)**:
```python
# install: pip install opentelemetry-distro opentelemetry-exporter-otlp
# automatic: opentelemetry-bootstrap -a install

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

def initialize_tracing(service_name: str, otlp_endpoint: str):
    """Initialize OpenTelemetry tracing with automatic instrumentation."""

    # Create resource with service information
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": "production",
    })

    # Set up tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter (sends to Jaeger, Zipkin, etc.)
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=False,  # Use TLS in production
    )

    # Batch processor for better performance
    span_processor = BatchSpanProcessor(
        otlp_exporter,
        max_queue_size=2048,
        max_export_batch_size=512,
        export_timeout_millis=30000,
    )
    provider.add_span_processor(span_processor)

    # Set as global tracer
    trace.set_tracer_provider(provider)

    # Auto-instrument frameworks
    FlaskInstrumentor().instrument()  # Flask endpoints
    RequestsInstrumentor().instrument()  # HTTP requests
    Psycopg2Instrumentor().instrument()  # Database queries

    return trace.get_tracer(__name__)


# Usage in Flask app
from flask import Flask

app = Flask(__name__)
tracer = initialize_tracing("user-api", "otelcol:4317")

@app.route("/users/<int:user_id>")
def get_user(user_id):
    # Automatically traced by Flask instrumentation
    user = fetch_user_from_db(user_id)
    return {"user": user}
```

**Manual Instrumentation**:
```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

def process_order(order_id: str):
    """Process order with manual tracing."""

    # Create span for this operation
    with tracer.start_as_current_span("process_order") as span:
        # Add attributes (tags) to span
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.priority", "high")

        try:
            # Validate order
            with tracer.start_as_current_span("validate_order") as validate_span:
                is_valid = validate_order(order_id)
                validate_span.set_attribute("order.valid", is_valid)

                if not is_valid:
                    validate_span.set_status(Status(StatusCode.ERROR, "Invalid order"))
                    raise ValueError("Order validation failed")

            # Process payment
            with tracer.start_as_current_span("process_payment") as payment_span:
                payment_span.set_attribute("payment.method", "credit_card")

                result = charge_payment(order_id)

                payment_span.set_attribute("payment.amount", result.amount)
                payment_span.set_attribute("payment.currency", result.currency)

                if result.declined:
                    payment_span.add_event("payment_declined", {
                        "reason": result.decline_reason,
                        "retry_allowed": result.can_retry
                    })
                    raise PaymentError("Payment declined")

            # Update inventory
            with tracer.start_as_current_span("update_inventory"):
                update_inventory(order_id)

            # Mark span as successful
            span.set_status(Status(StatusCode.OK))
            span.set_attribute("order.status", "completed")

        except Exception as e:
            # Record exception in span
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
```

**Sampling Configuration**:
```python
from opentelemetry.sdk.trace.sampling import (
    ParentBasedTraceIdRatioBased,
    ALWAYS_OFF,
    ALWAYS_ON,
    TraceIdRatioBased,
)

# Sample 10% of traces
sampler = ParentBasedTraceIdRatioBased(
    root=TraceIdRatioBased(0.1),  # 10% sampling
    # If parent span is sampled, sample this one too
)

provider = TracerProvider(
    resource=resource,
    sampler=sampler,
)

# More sophisticated: sample based on attributes
from opentelemetry.sdk.trace.sampling import Sampler, SamplingResult, Decision

class CustomSampler(Sampler):
    """Sample based on request attributes."""

    def should_sample(self, context, trace_id, name, kind, attributes, links, trace_state):
        # Always sample errors
        if attributes and attributes.get("http.status_code", 0) >= 400:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        # Always sample slow requests
        if attributes and attributes.get("http.duration_ms", 0) > 1000:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        # Sample 1% of successful requests
        if trace_id % 100 == 0:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        return SamplingResult(Decision.DROP)
```

### 3.3 Trace Analysis Techniques

**Identifying Latency Bottlenecks**:
```python
def analyze_trace_latency(trace: dict) -> dict:
    """Identify slowest spans in a trace."""

    spans = trace["spans"]
    total_duration = trace["duration_ms"]

    # Calculate each span's contribution to total latency
    span_analysis = []
    for span in spans:
        duration = span["duration_ms"]
        percentage = (duration / total_duration) * 100

        span_analysis.append({
            "span_id": span["span_id"],
            "operation": span["operation_name"],
            "service": span["service_name"],
            "duration_ms": duration,
            "percentage": percentage,
            "is_bottleneck": percentage > 20,  # >20% of total time
        })

    # Sort by duration
    span_analysis.sort(key=lambda x: x["duration_ms"], reverse=True)

    # Identify critical path (longest sequential chain)
    critical_path = find_critical_path(spans)

    return {
        "total_duration_ms": total_duration,
        "span_count": len(spans),
        "span_analysis": span_analysis,
        "critical_path": critical_path,
        "bottlenecks": [s for s in span_analysis if s["is_bottleneck"]],
    }


def find_critical_path(spans: list[dict]) -> list[dict]:
    """Find the longest sequential path through the trace."""

    # Build span tree
    span_map = {s["span_id"]: s for s in spans}
    root_spans = [s for s in spans if not s.get("parent_span_id")]

    def find_longest_path(span_id: str) -> list[dict]:
        span = span_map[span_id]
        children = [s for s in spans if s.get("parent_span_id") == span_id]

        if not children:
            return [span]

        # Find longest child path
        child_paths = [find_longest_path(c["span_id"]) for c in children]
        longest_child_path = max(child_paths, key=lambda p: sum(s["duration_ms"] for s in p))

        return [span] + longest_child_path

    # Find longest path from each root
    all_paths = [find_longest_path(r["span_id"]) for r in root_spans]
    critical_path = max(all_paths, key=lambda p: sum(s["duration_ms"] for s in p))

    return critical_path
```

**Error Correlation**:
```python
def correlate_errors(traces: list[dict]) -> dict:
    """Find common patterns in failing traces."""

    failing_traces = [t for t in traces if t["has_error"]]

    if not failing_traces:
        return {"error_rate": 0, "patterns": []}

    # Group errors by service
    errors_by_service = defaultdict(list)
    for trace in failing_traces:
        for span in trace["spans"]:
            if span.get("error"):
                errors_by_service[span["service_name"]].append({
                    "trace_id": trace["trace_id"],
                    "error": span["error"],
                    "timestamp": span["timestamp"],
                })

    # Find common error messages
    error_patterns = []
    for service, errors in errors_by_service.items():
        error_messages = [e["error"]["message"] for e in errors]
        unique_errors = set(error_messages)

        for error_msg in unique_errors:
            count = error_messages.count(error_msg)
            error_patterns.append({
                "service": service,
                "error_message": error_msg,
                "count": count,
                "percentage": (count / len(failing_traces)) * 100,
                "example_trace_ids": [
                    e["trace_id"] for e in errors
                    if e["error"]["message"] == error_msg
                ][:5],
            })

    # Sort by frequency
    error_patterns.sort(key=lambda x: x["count"], reverse=True)

    return {
        "total_traces": len(traces),
        "failing_traces": len(failing_traces),
        "error_rate": (len(failing_traces) / len(traces)) * 100,
        "patterns": error_patterns,
    }
```

**Service Dependency Mapping**:
```python
def build_service_dependency_graph(traces: list[dict]) -> dict:
    """Build service dependency graph from traces."""

    dependencies = defaultdict(lambda: defaultdict(int))
    service_metrics = defaultdict(lambda: {
        "call_count": 0,
        "total_duration_ms": 0,
        "error_count": 0,
    })

    for trace in traces:
        spans_by_id = {s["span_id"]: s for s in trace["spans"]}

        for span in trace["spans"]:
            service = span["service_name"]

            # Update service metrics
            service_metrics[service]["call_count"] += 1
            service_metrics[service]["total_duration_ms"] += span["duration_ms"]
            if span.get("error"):
                service_metrics[service]["error_count"] += 1

            # Track dependencies (calls from parent service)
            parent_id = span.get("parent_span_id")
            if parent_id and parent_id in spans_by_id:
                parent_service = spans_by_id[parent_id]["service_name"]
                if parent_service != service:  # Cross-service call
                    dependencies[parent_service][service] += 1

    # Calculate metrics
    for service, metrics in service_metrics.items():
        metrics["avg_duration_ms"] = metrics["total_duration_ms"] / metrics["call_count"]
        metrics["error_rate"] = (metrics["error_count"] / metrics["call_count"]) * 100

    return {
        "services": dict(service_metrics),
        "dependencies": {
            from_svc: dict(to_svcs)
            for from_svc, to_svcs in dependencies.items()
        },
    }
```

### 3.4 Jaeger and Zipkin

**Jaeger Deployment**:
```yaml
# docker-compose.yml for Jaeger all-in-one
version: '3'
services:
  jaeger:
    image: jaegertracing/all-in-one:1.50
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "5775:5775/udp"   # Zipkin compact thrift
      - "6831:6831/udp"   # Jaeger thrift compact
      - "6832:6832/udp"   # Jaeger thrift binary
      - "5778:5778"       # Config endpoint
      - "16686:16686"     # UI
      - "14268:14268"     # Jaeger collector
      - "14250:14250"     # gRPC
      - "9411:9411"       # Zipkin
      - "4317:4317"       # OTLP gRPC
      - "4318:4318"       # OTLP HTTP
```

**Jaeger Query API**:
```python
import requests
from typing import Optional

class JaegerClient:
    """Client for Jaeger Query API."""

    def __init__(self, jaeger_url: str = "http://localhost:16686"):
        self.base_url = jaeger_url
        self.api_url = f"{jaeger_url}/api"

    def search_traces(
        self,
        service: str,
        operation: Optional[str] = None,
        tags: Optional[dict] = None,
        min_duration: Optional[str] = None,
        max_duration: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Search for traces matching criteria."""

        params = {
            "service": service,
            "limit": limit,
        }

        if operation:
            params["operation"] = operation

        if tags:
            # Tags format: key1=value1 key2=value2
            params["tags"] = " ".join(f"{k}={v}" for k, v in tags.items())

        if min_duration:
            params["minDuration"] = min_duration  # e.g., "100ms"

        if max_duration:
            params["maxDuration"] = max_duration

        response = requests.get(f"{self.api_url}/traces", params=params)
        response.raise_for_status()

        return response.json()["data"]

    def get_trace(self, trace_id: str) -> dict:
        """Get specific trace by ID."""

        response = requests.get(f"{self.api_url}/traces/{trace_id}")
        response.raise_for_status()

        return response.json()["data"][0]

    def get_services(self) -> list[str]:
        """Get list of all services."""

        response = requests.get(f"{self.api_url}/services")
        response.raise_for_status()

        return response.json()["data"]

    def get_operations(self, service: str) -> list[str]:
        """Get operations for a service."""

        response = requests.get(
            f"{self.api_url}/services/{service}/operations"
        )
        response.raise_for_status()

        return response.json()["data"]
```

---

## 4. Memory Debugging

### 4.1 Memory Issue Types

**Memory Leak**:
```
Characteristics:
├─ Gradual memory growth over time
├─ Never returns to baseline
├─ Eventually causes OOM
└─ Often related to: unclosed resources, circular refs, unbounded caches

Detection:
├─ Monitor heap size over days/weeks
├─ Compare heap snapshots over time
├─ Look for objects that keep growing
└─ Check for resources not being freed

Tools:
├─ Python: tracemalloc, memory_profiler, py-spy, memray
├─ Go: pprof heap profiling
├─ Java: VisualVM, Eclipse MAT, jmap
├─ Node.js: Chrome DevTools, heapdump
└─ Native: Valgrind (dev only), AddressSanitizer, tcmalloc
```

**Memory Exhaustion** (not a leak):
```
Characteristics:
├─ Sudden OOM under specific conditions
├─ Memory returns to normal after event
├─ Related to: large allocations, memory spikes
└─ Example: Loading large file, processing big batch

Detection:
├─ Monitor memory during specific operations
├─ Check for correlation with workload
├─ Profile allocations during peak
└─ Look at allocation size distribution

Resolution:
├─ Stream data instead of loading all
├─ Process in batches
├─ Increase memory limits
└─ Optimize data structures
```

**Excessive GC/Allocation Churn**:
```
Characteristics:
├─ High CPU in GC
├─ Latency spikes during GC pauses
├─ Many short-lived objects
└─ Memory usage looks fine, but performance suffers

Detection:
├─ Monitor GC metrics (frequency, pause time)
├─ Profile object allocations
├─ Check allocation rate (MB/sec)
└─ Look at object lifetime distribution

Resolution:
├─ Object pooling for short-lived objects
├─ Reduce allocations in hot paths
├─ Use value types instead of references (where applicable)
└─ Tune GC parameters
```

### 4.2 Python Memory Debugging

**tracemalloc (built-in)**:
```python
import tracemalloc
import linecache

def start_memory_tracking():
    """Start tracking memory allocations."""
    tracemalloc.start()

def take_memory_snapshot() -> tracemalloc.Snapshot:
    """Take snapshot of current memory."""
    return tracemalloc.take_snapshot()

def compare_snapshots(snapshot1: tracemalloc.Snapshot, snapshot2: tracemalloc.Snapshot):
    """Compare two snapshots to find memory leaks."""

    # Get differences
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')

    print("Top 10 memory increases:")
    for stat in top_stats[:10]:
        print(f"{stat.size_diff / 1024 / 1024:.1f} MB: {stat}")

        # Show code context
        for line in stat.traceback.format():
            print(f"  {line}")

def display_top_allocations(snapshot: tracemalloc.Snapshot, key_type='lineno', limit=10):
    """Display top memory allocations."""

    top_stats = snapshot.statistics(key_type)

    print(f"Top {limit} allocations:")
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        filename = frame.filename
        lineno = frame.lineno

        # Get source code line
        line = linecache.getline(filename, lineno).strip()

        print(f"#{index}: {filename}:{lineno}: {stat.size / 1024 / 1024:.1f} MB")
        print(f"  {line}")
        print(f"  Count: {stat.count} blocks")

# Usage
start_memory_tracking()

# Take baseline
snapshot1 = take_memory_snapshot()

# Run workload
process_data()

# Take second snapshot
snapshot2 = take_memory_snapshot()

# Compare
compare_snapshots(snapshot1, snapshot2)
```

**py-spy (production-safe profiler)**:
```bash
# Install
pip install py-spy

# Top functions by memory (sampling)
py-spy top --pid 12345

# Record flame graph
py-spy record --pid 12345 --output profile.svg --duration 60

# Dump stack traces for all threads
py-spy dump --pid 12345

# Record with native stack traces (C extensions)
py-spy record --pid 12345 --native --output profile.svg

# Monitor specific function
py-spy top --pid 12345 --function my_module.my_function
```

**memray (comprehensive memory profiler)**:
```bash
# Install
pip install memray

# Record memory usage
memray run --live app.py
# Or attach to running process
memray attach 12345

# Generate flame graph
memray flamegraph memray-output.bin

# Generate table
memray table memray-output.bin

# Show peak memory
memray stats memray-output.bin

# Filter to specific function
memray flamegraph memray-output.bin --filter my_function
```

**memory_profiler (line-by-line)**:
```python
# Install: pip install memory_profiler

from memory_profiler import profile

@profile
def process_large_data(data):
    """Process data with line-by-line memory profiling."""

    # Each line's memory usage will be tracked
    result = []
    temp = data.copy()  # Memory spike here

    for item in temp:
        processed = expensive_operation(item)
        result.append(processed)

    return result

# Run with: python -m memory_profiler script.py
# Output shows memory usage per line
```

### 4.3 Go Memory Debugging

**pprof Heap Profiling**:
```go
package main

import (
    "fmt"
    "net/http"
    _ "net/http/pprof"
    "runtime"
)

func main() {
    // Enable pprof endpoints
    go func() {
        http.ListenAndServe("localhost:6060", nil)
    }()

    // Your application logic
    runApp()
}

// Available endpoints:
// http://localhost:6060/debug/pprof/         - Index
// http://localhost:6060/debug/pprof/heap     - Heap profile
// http://localhost:6060/debug/pprof/allocs   - Allocations
// http://localhost:6060/debug/pprof/goroutine - Goroutines
```

**Analyzing Heap Profile**:
```bash
# Get heap profile (current allocations)
curl http://localhost:6060/debug/pprof/heap > heap.prof

# Get allocation profile (all allocations)
curl http://localhost:6060/debug/pprof/allocs > allocs.prof

# Analyze with pprof
go tool pprof heap.prof

# pprof commands:
# top - Show top functions by memory
# list <function> - Show source code
# web - Generate SVG graph (requires graphviz)
# peek - Show callers and callees

# Compare two profiles to find leaks
go tool pprof -base heap1.prof heap2.prof

# Generate flame graph
go tool pprof -http=:8080 heap.prof
```

**Memory Stats Monitoring**:
```go
package main

import (
    "fmt"
    "runtime"
    "time"
)

func printMemStats() {
    var m runtime.MemStats
    runtime.ReadMemStats(&m)

    fmt.Printf("Alloc = %v MB", bToMb(m.Alloc))
    fmt.Printf("\tTotalAlloc = %v MB", bToMb(m.TotalAlloc))
    fmt.Printf("\tSys = %v MB", bToMb(m.Sys))
    fmt.Printf("\tNumGC = %v\n", m.NumGC)
}

func bToMb(b uint64) uint64 {
    return b / 1024 / 1024
}

func monitorMemory(interval time.Duration) {
    ticker := time.NewTicker(interval)
    defer ticker.Stop()

    for range ticker.C {
        printMemStats()
    }
}

// Usage
go monitorMemory(10 * time.Second)
```

### 4.4 Java Memory Debugging

**jmap and jhat**:
```bash
# List Java processes
jps -l

# Get heap histogram
jmap -histo $PID

# Get heap histogram for live objects (forces GC)
jmap -histo:live $PID

# Dump heap
jmap -dump:live,format=b,file=heap.hprof $PID

# Analyze with jhat (built-in)
jhat heap.hprof
# Browse to http://localhost:7000
```

**Eclipse Memory Analyzer (MAT)**:
```bash
# Download from: https://eclipse.org/mat/

# Open heap dump
# MAT provides:
# - Leak suspects report
# - Dominator tree (what's keeping objects alive)
# - Histogram by class
# - Path to GC roots
# - OQL (object query language)

# Example OQL query to find large strings
SELECT * FROM java.lang.String s WHERE s.count > 1000

# Find objects by class
SELECT * FROM com.example.MyClass

# Find objects with specific field value
SELECT * FROM com.example.User WHERE name.toString() LIKE ".*admin.*"
```

**JVM Flags for Debugging**:
```bash
# Dump heap on OOM
java -XX:+HeapDumpOnOutOfMemoryError \
     -XX:HeapDumpPath=/var/log/heap_dumps \
     -jar app.jar

# Enable GC logging
java -Xlog:gc*:file=/var/log/gc.log:time,uptime,level,tags \
     -jar app.jar

# Track native memory
java -XX:NativeMemoryTracking=detail \
     -jar app.jar

# Check native memory
jcmd $PID VM.native_memory summary
jcmd $PID VM.native_memory detail
```

### 4.5 Node.js Memory Debugging

**Chrome DevTools**:
```javascript
// Start Node with inspector
node --inspect=0.0.0.0:9229 app.js

// Or attach to running process
kill -USR1 $PID  // Sends SIGUSR1 to enable inspector

// Connect with Chrome DevTools:
// chrome://inspect
```

**heapdump Module**:
```javascript
// Install: npm install heapdump

const heapdump = require('heapdump');

// Take heap snapshot
heapdump.writeSnapshot('/tmp/heap-' + Date.now() + '.heapsnapshot');

// Or trigger on signal
process.on('SIGUSR2', () => {
    heapdump.writeSnapshot((err, filename) => {
        console.log('Heap dump written to', filename);
    });
});

// Then: kill -USR2 $PID
```

**memory-usage Module**:
```javascript
// Install: npm install memory-usage

const memoryUsage = require('memory-usage');

// Monitor memory
setInterval(() => {
    const usage = process.memoryUsage();

    console.log({
        rss: `${Math.round(usage.rss / 1024 / 1024)} MB`,          // Total
        heapTotal: `${Math.round(usage.heapTotal / 1024 / 1024)} MB`,  // Heap allocated
        heapUsed: `${Math.round(usage.heapUsed / 1024 / 1024)} MB`,    // Heap used
        external: `${Math.round(usage.external / 1024 / 1024)} MB`,     // C++ objects
    });
}, 10000);
```

---

## 5. Core Dump Analysis

### 5.1 Core Dump Collection

**Enable Core Dumps**:
```bash
# Check current limit
ulimit -c

# Enable unlimited core dumps
ulimit -c unlimited

# Make persistent in /etc/security/limits.conf
echo "* soft core unlimited" >> /etc/security/limits.conf
echo "* hard core unlimited" >> /etc/security/limits.conf

# Configure core pattern (where dumps are saved)
echo "/var/crash/core.%e.%p.%t" > /proc/sys/kernel/core_pattern

# Make persistent in /etc/sysctl.conf
echo "kernel.core_pattern=/var/crash/core.%e.%p.%t" >> /etc/sysctl.conf

# Create crash directory
mkdir -p /var/crash
chmod 777 /var/crash  # Or set appropriate permissions

# Patterns:
# %e - executable name
# %p - PID
# %t - timestamp
# %h - hostname
# %E - pathname (/ becomes !)
```

**systemd coredumpctl**:
```bash
# List core dumps
coredumpctl list

# Show info about most recent
coredumpctl info

# Show specific PID
coredumpctl info $PID

# Dump core file
coredumpctl dump $PID > /tmp/core.dump

# Debug with gdb
coredumpctl debug $PID

# Clean old dumps
coredumpctl vacuum --keep-free=1G
```

**Docker Container Core Dumps**:
```yaml
# docker-compose.yml
version: '3'
services:
  app:
    image: myapp:latest
    ulimits:
      core:
        soft: -1
        hard: -1
    volumes:
      - /var/crash:/var/crash
    security_opt:
      - apparmor=unconfined
```

### 5.2 GDB Analysis (C/C++)

**Basic GDB Commands**:
```bash
# Load core dump
gdb /path/to/binary /path/to/core

# Or if symbols separate
gdb -s /path/to/symbols /path/to/binary /path/to/core

# Commands:
(gdb) bt              # Backtrace (call stack)
(gdb) bt full         # Backtrace with local variables
(gdb) frame 3         # Switch to frame 3
(gdb) info locals     # Show local variables in current frame
(gdb) info args       # Show function arguments
(gdb) print variable  # Print variable value
(gdb) print *pointer  # Dereference pointer
(gdb) x/16xw addr     # Examine memory (16 hex words)
(gdb) info registers  # Show CPU registers
(gdb) info threads    # List all threads
(gdb) thread 5        # Switch to thread 5
(gdb) thread apply all bt  # Backtrace for all threads
(gdb) quit            # Exit
```

**Automated Core Dump Script**:
```bash
#!/bin/bash
# analyze_core.sh

set -e

BINARY=$1
CORE=$2
OUTPUT=${3:-analysis.txt}

if [ -z "$BINARY" ] || [ -z "$CORE" ]; then
    echo "Usage: $0 <binary> <core> [output]"
    exit 1
fi

# Generate GDB commands
cat > /tmp/gdb_commands.txt <<'EOF'
# Print basic info
echo === CORE DUMP ANALYSIS ===\n
info program

# Backtrace of crashing thread
echo \n=== BACKTRACE ===\n
bt full

# All thread backtraces
echo \n=== ALL THREADS ===\n
info threads
thread apply all bt

# Registers
echo \n=== REGISTERS ===\n
info registers

# Check for common crash patterns
echo \n=== CRASH ANALYSIS ===\n

# Check if segfault
if $_siginfo
    printf "Signal: %d\n", $_siginfo.si_signo
    printf "Address: 0x%lx\n", $_siginfo.si_addr
end

# Print suspect variables
echo \n=== LOCAL VARIABLES (frame 0) ===\n
frame 0
info locals

echo \n=== ARGUMENTS (frame 0) ===\n
info args

quit
EOF

# Run GDB with commands
gdb -batch -x /tmp/gdb_commands.txt "$BINARY" "$CORE" > "$OUTPUT" 2>&1

echo "Analysis written to $OUTPUT"

# Clean up
rm /tmp/gdb_commands.txt
```

**Crash Pattern Detection**:
```python
#!/usr/bin/env python3
"""Analyze core dump and identify crash patterns."""

import re
import subprocess
from typing import Optional

class CoreDumpAnalyzer:
    """Analyze core dumps for common patterns."""

    def __init__(self, binary: str, core: str):
        self.binary = binary
        self.core = core

    def run_gdb_command(self, command: str) -> str:
        """Run GDB command and return output."""
        gdb_cmd = f'gdb -batch -ex "{command}" {self.binary} {self.core}'
        result = subprocess.run(
            gdb_cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout

    def get_crash_signal(self) -> Optional[str]:
        """Identify crash signal."""
        info = self.run_gdb_command("info program")

        if "SIGSEGV" in info:
            return "SIGSEGV (Segmentation Fault)"
        elif "SIGABRT" in info:
            return "SIGABRT (Abort)"
        elif "SIGFPE" in info:
            return "SIGFPE (Floating Point Exception)"
        elif "SIGILL" in info:
            return "SIGILL (Illegal Instruction)"

        return None

    def get_crash_address(self) -> Optional[str]:
        """Get address that caused crash."""
        info = self.run_gdb_command("info program")
        match = re.search(r"at address (0x[0-9a-fA-F]+)", info)
        return match.group(1) if match else None

    def analyze_null_pointer(self) -> bool:
        """Check if crash was null pointer dereference."""
        addr = self.get_crash_address()
        if addr:
            # Null or near-null address
            return int(addr, 16) < 0x1000
        return False

    def get_stack_trace(self) -> list[str]:
        """Get stack trace."""
        bt = self.run_gdb_command("bt")
        frames = []
        for line in bt.splitlines():
            if line.startswith("#"):
                frames.append(line)
        return frames

    def check_stack_overflow(self) -> bool:
        """Check for stack overflow."""
        bt = self.get_stack_trace()
        # Stack overflow often shows deep recursion
        return len(bt) > 1000

    def analyze(self) -> dict:
        """Perform comprehensive analysis."""
        return {
            "signal": self.get_crash_signal(),
            "crash_address": self.get_crash_address(),
            "null_pointer": self.analyze_null_pointer(),
            "stack_overflow": self.check_stack_overflow(),
            "stack_trace": self.get_stack_trace()[:10],  # Top 10 frames
        }
```

### 5.3 Delve Analysis (Go)

**Delve for Go Core Dumps**:
```bash
# Install delve
go install github.com/go-delve/delve/cmd/dlv@latest

# Load core dump
dlv core /path/to/binary /path/to/core

# Commands:
(dlv) goroutines                   # List all goroutines
(dlv) goroutine 1                  # Switch to goroutine 1
(dlv) bt                           # Backtrace
(dlv) locals                       # Local variables
(dlv) print variable               # Print variable
(dlv) stack 10                     # Show 10 stack frames
(dlv) goroutine 1 bt               # Backtrace for specific goroutine
(dlv) goroutines -t                # Show goroutine locations
```

**Go Crash Analysis**:
```go
package main

import (
    "fmt"
    "os"
    "os/signal"
    "runtime"
    "runtime/debug"
    "syscall"
)

func setupCrashHandler() {
    // Capture panics
    defer func() {
        if r := recover(); err != nil {
            fmt.Fprintf(os.Stderr, "Panic: %v\n", r)
            fmt.Fprintf(os.Stderr, "Stack trace:\n%s\n", debug.Stack())

            // Write to file
            f, _ := os.Create("/var/log/app-crash.log")
            defer f.Close()

            fmt.Fprintf(f, "Panic: %v\n", r)
            fmt.Fprintf(f, "Goroutines: %d\n", runtime.NumGoroutine())
            fmt.Fprintf(f, "Stack trace:\n%s\n", debug.Stack())

            // Exit
            os.Exit(1)
        }
    }()

    // Capture signals
    sigChan := make(chan os.Signal, 1)
    signal.Notify(sigChan, syscall.SIGQUIT, syscall.SIGTERM, syscall.SIGINT)

    go func() {
        sig := <-sigChan
        fmt.Fprintf(os.Stderr, "Received signal: %v\n", sig)

        // Print goroutine stacks
        buf := make([]byte, 1<<20)  // 1MB buffer
        stackSize := runtime.Stack(buf, true)

        f, _ := os.Create("/var/log/app-signal.log")
        defer f.Close()

        fmt.Fprintf(f, "Signal: %v\n", sig)
        fmt.Fprintf(f, "Goroutines: %d\n", runtime.NumGoroutine())
        fmt.Fprintf(f, "Stack traces:\n%s\n", buf[:stackSize])

        os.Exit(0)
    }()
}
```

### 5.4 LLDB Analysis (Rust/Swift)

**LLDB Commands**:
```bash
# Load core dump
lldb -c /path/to/core /path/to/binary

# Commands:
(lldb) bt all                      # Backtrace all threads
(lldb) frame variable              # Variables in current frame
(lldb) frame select 3              # Switch to frame 3
(lldb) thread list                 # List threads
(lldb) thread select 2             # Switch to thread 2
(lldb) register read               # Show registers
(lldb) memory read addr            # Read memory
(lldb) image list                  # Show loaded libraries
```

**Rust Panic Analysis**:
```rust
use std::panic;
use std::fs::File;
use std::io::Write;

fn setup_panic_handler() {
    panic::set_hook(Box::new(|panic_info| {
        let location = panic_info.location()
            .map(|l| format!("{}:{}:{}", l.file(), l.line(), l.column()))
            .unwrap_or_else(|| "unknown location".to_string());

        let message = if let Some(s) = panic_info.payload().downcast_ref::<&str>() {
            s.to_string()
        } else if let Some(s) = panic_info.payload().downcast_ref::<String>() {
            s.clone()
        } else {
            "unknown panic".to_string()
        };

        let panic_report = format!(
            "Panic occurred:\nLocation: {}\nMessage: {}\nBacktrace:\n{:?}\n",
            location,
            message,
            backtrace::Backtrace::new()
        );

        eprintln!("{}", panic_report);

        // Write to file
        if let Ok(mut file) = File::create("/var/log/app-panic.log") {
            let _ = file.write_all(panic_report.as_bytes());
        }
    }));
}
```

---

## 6. Network Debugging

### 6.1 Packet Capture with tcpdump

**Basic tcpdump Usage**:
```bash
# Capture all traffic on interface
tcpdump -i eth0

# Capture to file
tcpdump -i eth0 -w capture.pcap

# Read from file
tcpdump -r capture.pcap

# Capture with snaplen (packet size limit)
tcpdump -i eth0 -s 65535 -w capture.pcap  # Full packets

# Display options
tcpdump -i eth0 -n              # Don't resolve hostnames
tcpdump -i eth0 -nn             # Don't resolve hosts or ports
tcpdump -i eth0 -v              # Verbose
tcpdump -i eth0 -vv             # More verbose
tcpdump -i eth0 -X              # Show packet contents in hex/ASCII
tcpdump -i eth0 -A              # Show packet contents in ASCII only

# Timestamp options
tcpdump -i eth0 -tttt           # Human-readable timestamps
```

**Filtering**:
```bash
# By host
tcpdump -i eth0 host 192.168.1.100
tcpdump -i eth0 src host 192.168.1.100
tcpdump -i eth0 dst host 192.168.1.100

# By network
tcpdump -i eth0 net 192.168.1.0/24

# By port
tcpdump -i eth0 port 443
tcpdump -i eth0 port 443 or port 80
tcpdump -i eth0 portrange 8000-9000

# By protocol
tcpdump -i eth0 tcp
tcpdump -i eth0 udp
tcpdump -i eth0 icmp

# Complex filters
tcpdump -i eth0 'tcp port 443 and host 192.168.1.100'
tcpdump -i eth0 'tcp port 80 and (src host 192.168.1.100 or src host 192.168.1.101)'

# HTTP traffic
tcpdump -i eth0 -A 'tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)'

# SYN packets (connection attempts)
tcpdump -i eth0 'tcp[tcpflags] & tcp-syn != 0'

# FIN packets (connection closes)
tcpdump -i eth0 'tcp[tcpflags] & tcp-fin != 0'

# RST packets (connection resets)
tcpdump -i eth0 'tcp[tcpflags] & tcp-rst != 0'
```

**Production-Safe Capture**:
```bash
# Limit capture size
tcpdump -i eth0 -c 1000 -w capture.pcap  # Only 1000 packets

# Limit duration
timeout 30s tcpdump -i eth0 -w capture.pcap  # 30 seconds

# Limit file size
tcpdump -i eth0 -W 5 -C 100 -w capture.pcap
# -W 5: Keep max 5 files
# -C 100: Rotate at 100MB

# Rotate by time
tcpdump -i eth0 -G 300 -w 'capture-%Y%m%d-%H%M%S.pcap'
# New file every 300 seconds
```

**Service-Specific Captures**:
```bash
# PostgreSQL
tcpdump -i any -s 65535 -w postgres.pcap 'port 5432'

# Redis
tcpdump -i any -s 65535 -w redis.pcap 'port 6379'

# MySQL
tcpdump -i any -s 65535 -w mysql.pcap 'port 3306'

# Elasticsearch
tcpdump -i any -s 65535 -w elasticsearch.pcap 'port 9200 or port 9300'

# RabbitMQ
tcpdump -i any -s 65535 -w rabbitmq.pcap 'port 5672'

# Between specific services
tcpdump -i any -s 65535 -w api-to-db.pcap \
  'host 10.0.1.5 and host 10.0.2.3 and port 5432'
```

### 6.2 Wireshark Analysis

**Command-Line Analysis with tshark**:
```bash
# Display packets
tshark -r capture.pcap

# Filter by protocol
tshark -r capture.pcap -Y "http"
tshark -r capture.pcap -Y "tcp.port == 443"

# Extract HTTP requests
tshark -r capture.pcap -Y "http.request" -T fields \
  -e http.request.method \
  -e http.host \
  -e http.request.uri

# Extract HTTP responses
tshark -r capture.pcap -Y "http.response" -T fields \
  -e http.response.code \
  -e http.content_length

# Show TCP conversations
tshark -r capture.pcap -q -z conv,tcp

# Show HTTP statistics
tshark -r capture.pcap -q -z http,stat

# Export HTTP objects
tshark -r capture.pcap --export-objects http,/tmp/http_objects

# Follow TCP stream
tshark -r capture.pcap -q -z follow,tcp,ascii,0
```

**Analysis Script**:
```python
#!/usr/bin/env python3
"""Analyze network capture for issues."""

import subprocess
import json
from collections import defaultdict

class NetworkCaptureAnalyzer:
    """Analyze packet captures for patterns."""

    def __init__(self, pcap_file: str):
        self.pcap_file = pcap_file

    def run_tshark(self, *args) -> str:
        """Run tshark command."""
        cmd = ["tshark", "-r", self.pcap_file] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    def analyze_retransmissions(self) -> dict:
        """Find TCP retransmissions."""
        output = self.run_tshark(
            "-Y", "tcp.analysis.retransmission",
            "-T", "fields",
            "-e", "ip.src",
            "-e", "ip.dst",
            "-e", "tcp.srcport",
            "-e", "tcp.dstport"
        )

        retransmissions = defaultdict(int)
        for line in output.strip().split('\n'):
            if line:
                retransmissions[line] += 1

        return dict(retransmissions)

    def analyze_connection_resets(self) -> list:
        """Find TCP RST packets."""
        output = self.run_tshark(
            "-Y", "tcp.flags.reset == 1",
            "-T", "fields",
            "-e", "frame.time",
            "-e", "ip.src",
            "-e", "ip.dst",
            "-e", "tcp.srcport",
            "-e", "tcp.dstport"
        )

        resets = []
        for line in output.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) == 5:
                    resets.append({
                        "time": parts[0],
                        "src": f"{parts[1]}:{parts[3]}",
                        "dst": f"{parts[2]}:{parts[4]}",
                    })

        return resets

    def analyze_latency(self) -> dict:
        """Analyze TCP handshake latency."""
        output = self.run_tshark(
            "-Y", "tcp.connection.syn",
            "-T", "fields",
            "-e", "tcp.time_relative"
        )

        latencies = [float(l) * 1000 for l in output.strip().split('\n') if l]

        if latencies:
            return {
                "count": len(latencies),
                "avg_ms": sum(latencies) / len(latencies),
                "min_ms": min(latencies),
                "max_ms": max(latencies),
            }

        return {}

    def analyze(self) -> dict:
        """Comprehensive analysis."""
        return {
            "retransmissions": self.analyze_retransmissions(),
            "connection_resets": self.analyze_connection_resets(),
            "latency": self.analyze_latency(),
        }
```

### 6.3 TLS/SSL Debugging

**OpenSSL Testing**:
```bash
# Test TLS connection
openssl s_client -connect api.example.com:443

# Show certificate chain
openssl s_client -connect api.example.com:443 -showcerts

# Test specific TLS version
openssl s_client -connect api.example.com:443 -tls1_2
openssl s_client -connect api.example.com:443 -tls1_3

# Test cipher suite
openssl s_client -connect api.example.com:443 -cipher 'ECDHE-RSA-AES128-GCM-SHA256'

# Verify certificate
openssl s_client -connect api.example.com:443 -CAfile /etc/ssl/certs/ca-certificates.crt

# Check certificate expiration
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -dates

# Check certificate details
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -text
```

**TLS Capture with Keys**:
```bash
# Set SSLKEYLOGFILE environment variable (must be set before starting application)
export SSLKEYLOGFILE=/tmp/sslkeys.log

# Start application (browser, curl, etc.)
# This only works with applications that support SSLKEYLOGFILE

# Capture traffic
tcpdump -i any -s 65535 -w tls.pcap 'port 443'

# In Wireshark:
# Edit -> Preferences -> Protocols -> TLS
# -> (Pre)-Master-Secret log filename: /tmp/sslkeys.log
# Now you can see decrypted TLS traffic
```

**Certificate Validation Script**:
```python
#!/usr/bin/env python3
"""Validate TLS certificates."""

import ssl
import socket
from datetime import datetime
from typing import Optional

class CertificateValidator:
    """Validate TLS certificates."""

    def __init__(self, host: str, port: int = 443):
        self.host = host
        self.port = port

    def get_certificate(self) -> dict:
        """Retrieve certificate from server."""
        context = ssl.create_default_context()

        with socket.create_connection((self.host, self.port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=self.host) as ssock:
                cert = ssock.getpeercert()
                return cert

    def check_expiration(self, cert: dict) -> dict:
        """Check if certificate is expired or expiring soon."""
        not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
        now = datetime.now()

        days_until_expiration = (not_after - now).days

        return {
            "expires": not_after.isoformat(),
            "days_remaining": days_until_expiration,
            "is_expired": days_until_expiration < 0,
            "expires_soon": 0 < days_until_expiration < 30,
        }

    def check_hostname(self, cert: dict) -> dict:
        """Verify hostname in certificate."""
        san = cert.get('subjectAltName', [])
        hostnames = [name for typ, name in san if typ == 'DNS']

        return {
            "hostnames": hostnames,
            "matches": self.host in hostnames,
        }

    def validate(self) -> dict:
        """Comprehensive validation."""
        try:
            cert = self.get_certificate()

            return {
                "success": True,
                "subject": dict(x[0] for x in cert['subject']),
                "issuer": dict(x[0] for x in cert['issuer']),
                "expiration": self.check_expiration(cert),
                "hostname": self.check_hostname(cert),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
```

### 6.4 HTTP Debugging

**mitmproxy**:
```bash
# Install
pip install mitmproxy

# Interactive proxy
mitmproxy --listen-port 8080

# Web interface
mitmweb --listen-port 8080
# Browse to http://localhost:8081

# Reverse proxy mode (for debugging backend)
mitmproxy --mode reverse:https://backend-api:443 --listen-port 8080

# Save traffic to file
mitmdump --save-stream-file traffic.mitm

# Replay traffic
mitmdump --server-replay traffic.mitm

# Filter traffic
mitmdump --intercept '~u /api/users'

# Modify requests/responses with Python script
mitmproxy -s modify_script.py
```

**HTTP/2 Debugging**:
```bash
# curl with HTTP/2
curl --http2 -v https://api.example.com

# Force HTTP/2 prior knowledge (no upgrade)
curl --http2-prior-knowledge -v https://api.example.com

# nghttp (HTTP/2 client)
nghttp -v https://api.example.com

# Show HTTP/2 frames
nghttp -v --no-dep https://api.example.com
```

### 6.5 Connection Analysis

**ss (socket statistics)**:
```bash
# Show all TCP connections
ss -tan

# Show listening sockets
ss -tln

# Show connection state
ss -tan state established
ss -tan state time-wait
ss -tan state close-wait

# Show by port
ss -tan 'sport = :8080'
ss -tan 'dport = :5432'

# Show with process info (requires root)
ss -tanp

# Show timer information
ss -tano

# Show memory usage
ss -tanm

# Statistics summary
ss -s
```

**netstat**:
```bash
# Show all connections
netstat -an

# Show with process names
netstat -anp

# Show listening ports
netstat -tln

# Show routing table
netstat -rn

# Show interface statistics
netstat -i
```

**Connection State Analysis**:
```bash
#!/bin/bash
# analyze_connections.sh

echo "Connection state summary:"
ss -tan | awk '{print $1}' | sort | uniq -c | sort -rn

echo -e "\nTop 10 external connections:"
ss -tan state established | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -10

echo -e "\nConnections by local port:"
ss -tan | awk '{print $4}' | cut -d: -f2 | sort | uniq -c | sort -rn | head -10

echo -e "\nTIME_WAIT accumulation:"
ss -tan state time-wait | wc -l
```

---

## 7. Database Debugging

### 7.1 PostgreSQL Debugging

**Slow Query Log**:
```sql
-- Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- 1 second
SELECT pg_reload_conf();

-- Or in postgresql.conf:
-- log_min_duration_statement = 1000

-- View slow queries
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;
```

**EXPLAIN ANALYZE**:
```sql
-- Show query plan
EXPLAIN SELECT * FROM users WHERE email = 'test@example.com';

-- Show query plan with execution stats
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';

-- Show more details
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, TIMING)
SELECT u.*, o.total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.created_at > '2024-01-01';

-- Common issues in EXPLAIN output:
-- Seq Scan -> Missing index
-- Nested Loop with high cost -> Join order problem
-- Hash Join with large hash tables -> Memory issue
-- High "Buffers: shared read" -> Disk I/O problem
```

**Active Queries**:
```sql
-- Show currently running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds'
  AND state = 'active'
ORDER BY duration DESC;

-- Kill long-running query
SELECT pg_cancel_backend(pid);  -- Graceful
SELECT pg_terminate_backend(pid);  -- Force

-- Show locks
SELECT
  l.pid,
  l.mode,
  l.granted,
  a.query
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE NOT l.granted;
```

**Connection Pool Debugging**:
```sql
-- Show connection count by state
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;

-- Show connection count by application
SELECT application_name, count(*) FROM pg_stat_activity GROUP BY application_name;

-- Show idle connections
SELECT pid, now() - state_change AS idle_duration, query
FROM pg_stat_activity
WHERE state = 'idle'
ORDER BY idle_duration DESC;

-- Show max connections
SHOW max_connections;

-- Show current connections vs max
SELECT count(*) AS current, setting::int AS max
FROM pg_stat_activity, pg_settings
WHERE name = 'max_connections';
```

**Index Analysis**:
```sql
-- Find unused indexes
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch,
  pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_relation_size(indexrelid) DESC;

-- Find missing indexes (tables with high seq scans)
SELECT
  schemaname,
  tablename,
  seq_scan,
  seq_tup_read,
  idx_scan,
  seq_tup_read / seq_scan AS avg_seq_tup,
  pg_size_pretty(pg_relation_size(relid)) AS size
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC
LIMIT 20;

-- Show index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch,
  idx_scan::float / NULLIF((seq_scan + idx_scan), 0) AS idx_scan_ratio
FROM pg_stat_user_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY idx_scan DESC;
```

**Bloat Analysis**:
```sql
-- Table bloat
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
  pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
  n_dead_tup,
  n_live_tup,
  round(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_tup_ratio
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;

-- When to VACUUM
-- Run VACUUM when dead_tup_ratio > 20%
VACUUM ANALYZE tablename;

-- Or auto-vacuum settings
SHOW autovacuum;
SHOW autovacuum_vacuum_scale_factor;
SHOW autovacuum_vacuum_threshold;
```

### 7.2 MySQL Debugging

**Slow Query Log**:
```sql
-- Enable slow query log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;  -- 1 second
SET GLOBAL log_queries_not_using_indexes = 'ON';

-- Analyze slow query log with mysqldumpslow
-- Shell command:
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log
# -s t: Sort by time
# -t 10: Top 10
```

**EXPLAIN**:
```sql
-- Show query plan
EXPLAIN SELECT * FROM users WHERE email = 'test@example.com';

-- Extended info
EXPLAIN EXTENDED SELECT * FROM users WHERE email = 'test@example.com';
SHOW WARNINGS;

-- JSON format (more details)
EXPLAIN FORMAT=JSON SELECT * FROM users WHERE email = 'test@example.com';

-- Common issues:
-- type: ALL -> Full table scan, need index
-- type: index -> Index scan, better but may need optimization
-- rows: high number -> Too many rows examined
-- Extra: Using filesort -> Need index for ORDER BY
-- Extra: Using temporary -> Need optimization
```

**Process List**:
```sql
-- Show running queries
SHOW FULL PROCESSLIST;

-- Kill query
KILL QUERY process_id;
KILL CONNECTION process_id;

-- Show by time
SELECT *
FROM information_schema.PROCESSLIST
WHERE COMMAND != 'Sleep'
  AND TIME > 5
ORDER BY TIME DESC;
```

**InnoDB Status**:
```sql
-- Show InnoDB engine status
SHOW ENGINE INNODB STATUS\G

-- Key sections:
-- TRANSACTIONS: Lock waits, deadlocks
-- BUFFER POOL AND MEMORY: Buffer pool hit rate
-- ROW OPERATIONS: Insert/update/delete rate
-- LOG: Log write rate

-- Deadlock example:
-- Shows last deadlock and involved transactions
```

### 7.3 Redis Debugging

**SLOWLOG**:
```bash
# Get slow commands (> 10ms by default)
redis-cli SLOWLOG GET 10

# Set slowlog threshold (microseconds)
redis-cli CONFIG SET slowlog-log-slower-than 10000  # 10ms

# Clear slowlog
redis-cli SLOWLOG RESET
```

**Monitor Commands**:
```bash
# Real-time command monitoring (use sparingly in production!)
redis-cli MONITOR

# Get stats
redis-cli INFO stats

# Get memory info
redis-cli INFO memory

# Show connected clients
redis-cli CLIENT LIST

# Kill client
redis-cli CLIENT KILL <ip>:<port>
```

**Memory Analysis**:
```bash
# Memory usage by key pattern
redis-cli --bigkeys

# Memory usage by key (requires Redis 4.0+)
redis-cli MEMORY USAGE mykey

# Debug memory for specific key
redis-cli DEBUG OBJECT mykey
```

### 7.4 MongoDB Debugging

**Profiler**:
```javascript
// Enable profiler (level 2 = all operations)
db.setProfilingLevel(2, { slowms: 100 });

// Level 0 = off, 1 = slow only, 2 = all

// View slow queries
db.system.profile.find().sort({ ts: -1 }).limit(10).pretty();

// Find slow queries
db.system.profile.find({
  millis: { $gt: 100 }
}).sort({ millis: -1 }).pretty();
```

**Explain**:
```javascript
// Explain query
db.users.find({ email: "test@example.com" }).explain("executionStats");

// Fields to check:
// - executionStats.totalDocsExamined: How many documents scanned
// - executionStats.totalKeysExamined: How many index keys scanned
// - executionStats.executionTimeMillis: Time taken
// - winningPlan.stage: IXSCAN (index) vs COLLSCAN (full scan)
```

**Current Operations**:
```javascript
// Show current operations
db.currentOp();

// Show long-running operations
db.currentOp({ "active": true, "secs_running": { "$gt": 5 } });

// Kill operation
db.killOp(opid);
```

**Index Stats**:
```javascript
// Show index usage
db.users.aggregate([
  { $indexStats: {} }
]);

// Find unused indexes
db.users.aggregate([
  { $indexStats: {} },
  { $match: { "accesses.ops": { $lt: 10 } } }
]);
```

---

## 8. Container Debugging

### 8.1 Docker Debugging

**Container Inspection**:
```bash
# Show running containers
docker ps

# Show all containers (including stopped)
docker ps -a

# Inspect container details
docker inspect <container_id>

# Show container logs
docker logs <container_id>
docker logs -f <container_id>  # Follow
docker logs --tail 100 <container_id>  # Last 100 lines
docker logs --since 10m <container_id>  # Last 10 minutes

# Show container stats
docker stats <container_id>

# Show container processes
docker top <container_id>
```

**Exec into Container**:
```bash
# Run shell in container
docker exec -it <container_id> /bin/bash
docker exec -it <container_id> /bin/sh

# Run specific command
docker exec <container_id> ps aux
docker exec <container_id> netstat -tan

# Run as specific user
docker exec -u root -it <container_id> /bin/bash
```

**Network Debugging**:
```bash
# Show container network settings
docker inspect --format='{{json .NetworkSettings}}' <container_id> | jq

# Show container IP
docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <container_id>

# Test connectivity from container
docker exec <container_id> ping other-container
docker exec <container_id> curl http://other-service:8080

# Show port mappings
docker port <container_id>
```

**Copy Files**:
```bash
# Copy from container
docker cp <container_id>:/path/to/file /local/path

# Copy to container
docker cp /local/path <container_id>:/path/to/file
```

**Debug Crashed Container**:
```bash
# Get logs from crashed container
docker logs <container_id>

# Commit crashed container to image
docker commit <container_id> debug-image

# Run new container from that image
docker run -it debug-image /bin/bash

# Or change entrypoint
docker run -it --entrypoint /bin/bash debug-image
```

### 8.2 Kubernetes Debugging

**Pod Inspection**:
```bash
# List pods
kubectl get pods
kubectl get pods -A  # All namespaces

# Show pod details
kubectl describe pod <pod_name>

# Show pod logs
kubectl logs <pod_name>
kubectl logs <pod_name> -c <container_name>  # Specific container
kubectl logs <pod_name> --previous  # Previous container (if crashed)
kubectl logs -f <pod_name>  # Follow

# Show pod events
kubectl get events --sort-by='.lastTimestamp' | grep <pod_name>
```

**Exec into Pod**:
```bash
# Run shell in pod
kubectl exec -it <pod_name> -- /bin/bash

# Specific container
kubectl exec -it <pod_name> -c <container_name> -- /bin/bash

# Run command
kubectl exec <pod_name> -- ps aux
kubectl exec <pod_name> -- curl http://other-service:8080
```

**Debug with Ephemeral Container** (Kubernetes 1.18+):
```bash
# Add ephemeral debug container to running pod
kubectl debug -it <pod_name> --image=busybox --target=<container_name>

# With more tools
kubectl debug -it <pod_name> --image=nicolaka/netshoot

# Copy pod for debugging (doesn't affect original)
kubectl debug <pod_name> -it --copy-to=<pod_name>-debug --container=<container_name> -- sh
```

**Network Debugging**:
```bash
# Show service endpoints
kubectl get endpoints <service_name>

# Show service details
kubectl describe service <service_name>

# Test connectivity from pod
kubectl exec <pod_name> -- nslookup <service_name>
kubectl exec <pod_name> -- curl http://<service_name>:8080

# Port forward
kubectl port-forward <pod_name> 8080:8080
kubectl port-forward service/<service_name> 8080:80
```

**Resource Inspection**:
```bash
# Show resource usage
kubectl top pods
kubectl top nodes

# Show pod resource requests/limits
kubectl describe pod <pod_name> | grep -A 5 "Limits:\|Requests:"

# Show events
kubectl get events --sort-by='.lastTimestamp'
kubectl get events --field-selector involvedObject.name=<pod_name>
```

**Troubleshooting Common Issues**:
```bash
# Pod stuck in Pending
kubectl describe pod <pod_name>
# Check: Insufficient resources, volume mount issues, node selectors

# Pod stuck in ContainerCreating
kubectl describe pod <pod_name>
# Check: Image pull issues, volume mount issues, init container failures

# Pod CrashLoopBackOff
kubectl logs <pod_name> --previous
# Check previous container logs for crash reason

# ImagePullBackOff
kubectl describe pod <pod_name>
# Check: Image name, registry authentication, network access

# Pod Evicted
kubectl get pod <pod_name> -o yaml | grep -A 10 status
# Check: Resource pressure, pod priority
```

**Node Debugging**:
```bash
# Show node details
kubectl describe node <node_name>

# Show node conditions
kubectl get node <node_name> -o jsonpath='{.status.conditions}'

# SSH to node (if accessible)
# Or use kubectl node-shell plugin
kubectl node-shell <node_name>
```

### 8.3 Container Resource Limits

**Memory Limits**:
```yaml
# Pod with memory limits
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: app
    image: myapp:latest
    resources:
      requests:
        memory: "256Mi"
      limits:
        memory: "512Mi"
```

**Check OOMKilled**:
```bash
# Check if container was OOM killed
kubectl get pod <pod_name> -o jsonpath='{.status.containerStatuses[*].lastState.terminated.reason}'

# Show OOMKilled pods
kubectl get pods -A -o json | jq -r '
  .items[] |
  select(.status.containerStatuses[]?.lastState.terminated.reason == "OOMKilled") |
  "\(.metadata.namespace)/\(.metadata.name)"
'
```

**CPU Throttling**:
```bash
# Check CPU throttling (requires metrics-server)
kubectl top pod <pod_name>

# Inside container, check throttling
cat /sys/fs/cgroup/cpu/cpu.stat
# throttled_time increases when CPU throttled
```

---

## 9. Live Debugging Tools

### 9.1 Python Live Debugging

**py-spy**:
```bash
# Already covered in Memory section, but more features:

# Top functions (live)
py-spy top --pid 12345

# Record flame graph
py-spy record --pid 12345 --output profile.svg --duration 60

# Dump stack traces
py-spy dump --pid 12345

# Profile specific function
py-spy record --pid 12345 --function my_module.my_function

# Profile with subprocesses
py-spy record --pid 12345 --subprocesses

# Show idle threads
py-spy dump --pid 12345 --idle

# Native extensions (C)
py-spy record --pid 12345 --native
```

**austin**:
```bash
# Install
pip install austin-python

# Profile application
austin python script.py

# Profile running process
austin --pid 12345

# Generate flame graph
austin --format speedscope python script.py > profile.json
# View at https://www.speedscope.app/
```

### 9.2 Go Live Debugging

**pprof**:
```go
// Enable pprof in application
import (
    "net/http"
    _ "net/http/pprof"
)

go func() {
    http.ListenAndServe("localhost:6060", nil)
}()
```

```bash
# Get CPU profile
curl http://localhost:6060/debug/pprof/profile?seconds=30 > cpu.prof

# Get heap profile
curl http://localhost:6060/debug/pprof/heap > heap.prof

# Get goroutine profile
curl http://localhost:6060/debug/pprof/goroutine > goroutine.prof

# Get blocking profile
curl http://localhost:6060/debug/pprof/block > block.prof

# Get mutex profile
curl http://localhost:6060/debug/pprof/mutex > mutex.prof

# Analyze
go tool pprof cpu.prof

# Or interactive web UI
go tool pprof -http=:8080 cpu.prof
```

**Execution Tracer**:
```go
import (
    "os"
    "runtime/trace"
)

func main() {
    f, _ := os.Create("trace.out")
    defer f.Close()

    trace.Start(f)
    defer trace.Stop()

    // Your code
}
```

```bash
# View trace
go tool trace trace.out
```

### 9.3 Java Live Debugging

**jstack** (thread dumps):
```bash
# Get thread dump
jstack $PID

# Get thread dump with locks
jstack -l $PID

# Multiple dumps for deadlock detection
for i in {1..5}; do
    echo "=== Dump $i ==="
    jstack $PID
    sleep 5
done
```

**jstat** (JVM statistics):
```bash
# GC statistics
jstat -gc $PID 1000  # Every 1 second

# Heap statistics
jstat -gccapacity $PID

# Class loading
jstat -class $PID

# JIT compilation
jstat -compiler $PID
```

**jcmd**:
```bash
# List available commands
jcmd $PID help

# Thread dump
jcmd $PID Thread.print

# Heap summary
jcmd $PID GC.heap_info

# GC stats
jcmd $PID GC.class_histogram

# VM flags
jcmd $PID VM.flags

# System properties
jcmd $PID VM.system_properties

# Diagnose commands
jcmd $PID VM.info
jcmd $PID VM.uptime
jcmd $PID VM.command_line
```

### 9.4 Node.js Live Debugging

**Inspector Protocol**:
```bash
# Start with inspector
node --inspect=0.0.0.0:9229 app.js

# Or enable on running process
kill -USR1 $PID

# Connect with Chrome DevTools
# Open chrome://inspect
# Click "inspect" on your process
```

**CPU Profiling**:
```javascript
const profiler = require('v8-profiler-next');

// Start profiling
profiler.startProfiling('CPU Profile', true);

// ... run workload ...

// Stop and save
const profile = profiler.stopProfiling();
profile.export((error, result) => {
    fs.writeFileSync('profile.cpuprofile', result);
    profile.delete();
});

// View in Chrome DevTools
```

**Heap Snapshot**:
```javascript
const v8 = require('v8');
const fs = require('fs');

// Take heap snapshot
const snapshot = v8.writeHeapSnapshot();
console.log('Heap snapshot written to:', snapshot);

// Or on signal
process.on('SIGUSR2', () => {
    const snapshot = v8.writeHeapSnapshot();
    console.log('Heap snapshot:', snapshot);
});
```

---

## 10. Performance Profiling

### 10.1 CPU Profiling

**Flame Graphs**:
```bash
# Using perf (Linux)
# Record
perf record -F 99 -p $PID -g -- sleep 60

# Generate flame graph
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg

# Scripts from: https://github.com/brendangregg/FlameGraph
```

**Language-Specific**:
```bash
# Python: py-spy (already covered)
py-spy record --pid $PID --output flame.svg

# Go: pprof
curl http://localhost:6060/debug/pprof/profile?seconds=30 > cpu.prof
go tool pprof -http=:8080 cpu.prof

# Java: async-profiler
./profiler.sh -d 60 -f flame.svg $PID

# Node.js: 0x
npx 0x app.js
```

### 10.2 Off-CPU Analysis

**What is Off-CPU**:
```
Off-CPU time = Time thread is NOT on CPU
├─ Blocked on I/O (disk, network)
├─ Waiting for locks
├─ Sleeping
└─ Swapped out

Off-CPU profiling shows where threads are waiting, not just where they're busy.
```

**Off-CPU Profiling**:
```bash
# Using perf + BPF
# Install bcc-tools
apt install bpftrace

# Off-CPU flame graph
offcputime -df -p $PID 60 > offcpu.svg

# Or specific thread state
wakeuptime -p $PID 60  # What woke threads up
```

### 10.3 I/O Profiling

**iotop**:
```bash
# Install
apt install iotop

# Show I/O by process
iotop

# Batch mode (for logging)
iotop -b -n 10
```

**iostat**:
```bash
# Install
apt install sysstat

# Show I/O statistics
iostat -x 1

# Key metrics:
# %util: Percentage of time device was busy
# await: Average time for requests (ms)
# svctm: Service time (deprecated, ignore)
```

**Disk Latency**:
```bash
# Using bcc-tools
biolatency 10  # 10 second summary

# Histogram of disk I/O latency
```

---

## 11. APM Integration

### 11.1 Datadog

**Agent Installation**:
```bash
# Install Datadog agent
DD_API_KEY=<your_api_key> DD_SITE="datadoghq.com" \
  bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"

# Configure
vi /etc/datadog-agent/datadog.yaml

# Start
systemctl start datadog-agent
systemctl enable datadog-agent
```

**Application Instrumentation** (Python):
```python
# Install
pip install ddtrace

# Run with automatic instrumentation
ddtrace-run python app.py

# Or manual
from ddtrace import tracer

@tracer.wrap()
def my_function():
    pass

# Custom metrics
from datadog import statsd

statsd.increment('my.metric')
statsd.gauge('my.gauge', 42)
statsd.histogram('my.histogram', 123)
```

**Custom Checks**:
```yaml
# /etc/datadog-agent/conf.d/custom_check.yaml
instances:
  - name: my_service

init_config:
```

```python
# /etc/datadog-agent/checks.d/custom_check.py
from datadog_checks.base import AgentCheck

class CustomCheck(AgentCheck):
    def check(self, instance):
        # Your logic here
        self.gauge('custom.metric', value)
```

### 11.2 New Relic

**Agent Installation**:
```bash
# Install New Relic infrastructure agent
curl -Ls https://download.newrelic.com/install/newrelic-cli/scripts/install.sh | bash
sudo NEW_RELIC_API_KEY=<your_key> NEW_RELIC_ACCOUNT_ID=<account_id> /usr/local/bin/newrelic install
```

**Application Instrumentation** (Python):
```python
# Install
pip install newrelic

# Configure
newrelic-admin generate-config <license_key> newrelic.ini

# Run
newrelic-admin run-program python app.py

# Or in code
import newrelic.agent
newrelic.agent.initialize('newrelic.ini')

# Custom instrumentation
@newrelic.agent.function_trace()
def my_function():
    pass

# Custom events
newrelic.agent.record_custom_event('MyEvent', {
    'key': 'value'
})
```

### 11.3 Dynatrace

**OneAgent Installation**:
```bash
# Download and install
wget -O Dynatrace-OneAgent.sh "https://your-environment.live.dynatrace.com/api/v1/deployment/installer/agent/unix/default/latest?Api-Token=<token>&arch=x86"
/bin/sh Dynatrace-OneAgent.sh APP_LOG_CONTENT_ACCESS=1
```

**Application Instrumentation**:
```
Dynatrace uses automatic instrumentation for most technologies.
No code changes required in most cases.

For custom metrics:
```

```python
# Python
import oneagent

sdk = oneagent.initialize()

with sdk.trace_incoming_remote_call('method', 'service', 'endpoint'):
    # Your code
    pass
```

---

## 12. Common Production Issues

### 12.1 Memory Leaks

**Symptoms**:
```
├─ Memory usage steadily increases
├─ Never returns to baseline after GC
├─ Eventually OOMKilled
└─ Performance degrades over time
```

**Diagnosis Steps**:
```
1. Confirm it's a leak (not just high usage):
   - Monitor heap over days
   - Check if memory released after workload stops
   - Compare heap snapshots over time

2. Identify leaking objects:
   - Take heap snapshots at intervals
   - Compare snapshots (what's growing?)
   - Analyze references to leaked objects

3. Find root cause:
   - Unclosed file handles/connections
   - Event listeners not removed
   - Circular references
   - Unbounded caches
   - Global collections growing
```

**Prevention**:
```python
# Bad: Unbounded cache
cache = {}

def get_user(user_id):
    if user_id not in cache:
        cache[user_id] = fetch_user(user_id)
    return cache[user_id]

# Good: Bounded cache with LRU
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user(user_id):
    return fetch_user(user_id)
```

### 12.2 Connection Pool Exhaustion

**Symptoms**:
```
├─ "Connection timeout" errors
├─ "Connection pool exhausted"
├─ Requests start failing suddenly
└─ Many connections in CLOSE_WAIT or TIME_WAIT
```

**Diagnosis**:
```bash
# Check connection counts
ss -tan | grep :5432 | wc -l  # PostgreSQL

# Check connection states
ss -tan state established 'dport = :5432' | wc -l
ss -tan state close-wait | wc -l

# Check application pool
# PostgreSQL:
SELECT count(*) FROM pg_stat_activity;

# Check for leaked connections (long-idle)
SELECT pid, now() - state_change AS idle, query
FROM pg_stat_activity
WHERE state = 'idle'
ORDER BY idle DESC;
```

**Fixes**:
```python
# Ensure connections are closed
# Bad:
conn = pool.getconn()
cursor = conn.cursor()
cursor.execute(query)
result = cursor.fetchall()
# Connection never returned!

# Good: Use context manager
with pool.getconn() as conn:
    with conn.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()
# Connection automatically returned

# Or explicitly:
conn = pool.getconn()
try:
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
finally:
    pool.putconn(conn)
```

**Tune Pool Size**:
```python
# Formula: connections = ((core_count * 2) + effective_spindle_count)
# For 4 cores, 1 disk: (4 * 2) + 1 = 9 connections per instance

# Don't over-provision!
# 100 app instances * 50 connections = 5000 connections
# But database max_connections = 500 -> Problem!

# Better:
# 100 app instances * 5 connections = 500 connections
# Leaves headroom for admin connections
```

### 12.3 Deadlocks

**Database Deadlock**:
```sql
-- PostgreSQL deadlock detection
-- Check pg_stat_activity for waiting queries

SELECT
  blocked_locks.pid AS blocked_pid,
  blocked_activity.usename AS blocked_user,
  blocking_locks.pid AS blocking_pid,
  blocking_activity.usename AS blocking_user,
  blocked_activity.query AS blocked_query,
  blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
  ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
  AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
  AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
  AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
  AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
  AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
  AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
  AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
  AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

**Prevention**:
```
1. Always acquire locks in same order
   - Transaction A: Lock table1, then table2
   - Transaction B: Lock table1, then table2 (NOT table2, then table1)

2. Use lock timeouts
   - PostgreSQL: SET lock_timeout = '5s';
   - MySQL: SET innodb_lock_wait_timeout = 5;

3. Keep transactions short
   - Don't hold locks while doing external API calls
   - Don't hold locks while processing data

4. Use appropriate isolation levels
   - READ COMMITTED often sufficient
   - SERIALIZABLE increases deadlock risk
```

### 12.4 CPU Saturation

**Symptoms**:
```
├─ CPU usage at 100%
├─ Latency increases
├─ Request queue builds up
└─ Load average > core count
```

**Diagnosis**:
```bash
# Check CPU usage
top
htop

# Check load average
uptime
# Load average: 8.5, 7.2, 6.1 on 4-core system = overloaded

# Profile CPU usage
perf top -p $PID

# Or language-specific
py-spy top --pid $PID
go tool pprof http://localhost:6060/debug/pprof/profile
```

**Common Causes**:
```
├─ Inefficient algorithms (O(n²) where O(n) possible)
├─ Tight loops without yielding
├─ Excessive GC (too many allocations)
├─ Regex on large strings
├─ Serialization/deserialization
└─ Cryptographic operations
```

**Fixes**:
```python
# Bad: O(n²) in loop
for item in items:
    if item in large_list:  # O(n) check
        process(item)

# Good: O(n) with set
large_set = set(large_list)  # O(n) to build
for item in items:
    if item in large_set:  # O(1) check
        process(item)

# Bad: Excessive allocations
result = ""
for item in items:
    result += str(item)  # Creates new string each time

# Good: Join
result = "".join(str(item) for item in items)
```

### 12.5 Cascading Failures

**Symptoms**:
```
├─ Failure in one service causes failures in others
├─ Rapid spreading of issues
├─ Complete system outage
└─ Services can't recover when dependency recovers
```

**Circuit Breaker Pattern**:
```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)

            # Success
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
            self.failure_count = 0

            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

            raise

# Usage
circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

def call_external_api():
    return circuit_breaker.call(requests.get, "https://api.example.com")
```

**Bulkhead Pattern**:
```python
# Isolate resources so failure in one doesn't affect others

from concurrent.futures import ThreadPoolExecutor

# Bad: Single thread pool for all operations
executor = ThreadPoolExecutor(max_workers=10)

executor.submit(critical_operation)
executor.submit(non_critical_operation)
# If non-critical operations saturate pool, critical ones can't run

# Good: Separate pools
critical_executor = ThreadPoolExecutor(max_workers=5)
non_critical_executor = ThreadPoolExecutor(max_workers=5)

critical_executor.submit(critical_operation)
non_critical_executor.submit(non_critical_operation)
# Critical operations always have resources
```

---

## 13. Anti-Patterns

**Safety Anti-Patterns**:
```
❌ Attach debugger to production process
   → Pauses execution, causes timeouts
   ✓ Use profiling tools that sample, not pause

❌ No timeout on debug operations
   → Can run indefinitely
   ✓ Always set timeout: timeout 30s command

❌ Debug primary database instance
   → Risk to critical instance
   ✓ Debug read replica instead

❌ 100% trace sampling
   → Overwhelms system and backend
   ✓ Sample 1-10% of requests

❌ Leave debug tools running
   → Continuous performance impact
   ✓ Only run during active investigation

❌ No resource limits on debug tools
   → Can consume all CPU/memory
   ✓ Set limits: nice, taskset, cgroups

❌ Modify production code to add logging
   → Unsafe, no version control
   ✓ Deploy instrumentation properly
```

**Analysis Anti-Patterns**:
```
❌ Guess root cause without data
   → Waste time on wrong issues
   ✓ Collect objective data first

❌ Look at logs/metrics in isolation
   → Miss connections between events
   ✓ Correlate across time and services

❌ Debug serially in distributed system
   → Can't see cross-service issues
   ✓ Use distributed tracing

❌ Only look at code
   → Infrastructure issues are common
   ✓ Check all layers: app, runtime, OS, network

❌ Restart without collecting diagnostics
   → Lose valuable debugging information
   ✓ Collect dumps, logs, metrics first

❌ Focus only on averages
   → Miss tail latency issues
   ✓ Look at p95, p99, max
```

**Communication Anti-Patterns**:
```
❌ Don't notify team of debug session
   → Confusion during incident
   ✓ Announce in war room / chat

❌ Don't document findings
   → Others can't learn
   ✓ Document in real-time

❌ Keep knowledge to yourself
   → Repeat work when issue recurs
   ✓ Share and create runbooks
```

---

## Conclusion

Production debugging requires a safety-first mindset, comprehensive tooling knowledge, and systematic investigation practices. Key principles:

1. **Safety First**: Always assess risk before debugging production systems
2. **Data-Driven**: Make decisions based on metrics, logs, and traces, not assumptions
3. **Minimal Impact**: Use non-invasive tools and techniques when possible
4. **Systematic**: Follow a structured investigation process
5. **Document**: Capture findings for future reference and team learning

The best production debugging is the kind you don't have to do - invest in observability, monitoring, and preventive measures.
