---
name: observability-production-incident-debugging
description: Debugging production incidents using observability data (logs, metrics, traces)
---

# Production Incident Debugging

**Scope**: Incident triage workflow, root cause analysis, distributed tracing for debugging, correlation IDs, runbook creation, blameless postmortems

**Lines**: 440

**Last Updated**: 2025-10-26

---

## When to Use This Skill

Use this skill when:
- Triaging production incidents with observability data
- Performing root cause analysis (RCA) for system failures
- Debugging distributed systems with multiple microservices
- Correlating logs, metrics, and traces to diagnose issues
- Creating runbooks from past incidents
- Conducting blameless postmortems
- Implementing time-travel debugging with distributed tracing

**Don't use** for:
- Local development debugging (use IDE debugger)
- Performance optimization (use profiling tools)
- Security incident response (use security-specific tools)

**Context**:
- **Mean Time to Detect (MTTD)**: Average 15-30 minutes for mature teams
- **Mean Time to Resolve (MTTR)**: Reduced by 50% with proper observability
- **Root cause accuracy**: 80%+ with correlated telemetry vs 40% with logs alone

---

## Core Concepts

### Incident Triage Workflow

```
1. DETECT: Alert fires or user reports issue
   ↓
2. ASSESS: Check dashboards (RED metrics: Rate, Errors, Duration)
   ↓
3. INVESTIGATE: Logs → Metrics → Traces (in that order)
   ↓
4. ISOLATE: Identify failing component/service
   ↓
5. MITIGATE: Rollback, scale, or patch
   ↓
6. RESOLVE: Fix root cause
   ↓
7. LEARN: Postmortem, runbook updates
```

### RED Method (Request-Driven Systems)

**Rate**: Requests per second
- Sudden drop? Upstream failure or routing issue
- Sudden spike? Traffic surge or DDoS

**Errors**: Error rate (percentage)
- Increase in 5xx errors? Backend failure
- Increase in 4xx errors? Client or API contract issue

**Duration**: Latency (p50, p95, p99)
- Increased latency? Database slow, network congestion, resource exhaustion

### USE Method (Resource-Driven Systems)

**Utilization**: % time resource is busy
**Saturation**: Degree of queued work
**Errors**: Error count

### The Three Pillars

**Logs** → What happened?
- Discrete events with context
- Use: Error messages, stack traces, business events

**Metrics** → How much/many?
- Aggregated measurements
- Use: Trends, thresholds, alerting

**Traces** → Where is the bottleneck?
- Request flows across services
- Use: Latency breakdown, dependency mapping

---

## Patterns

### Pattern 1: Incident Triage with RED Metrics

```promql
# 1. CHECK RATE: Sudden drop or spike?
sum(rate(http_requests_total[5m])) by (service)

# 2. CHECK ERRORS: Error rate increase?
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
/
sum(rate(http_requests_total[5m])) by (service)
* 100  # Percentage

# 3. CHECK DURATION: Latency spike?
histogram_quantile(0.95,
  sum by (le, service) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)

# 4. IDENTIFY FAILING SERVICE
# Look for:
# - Service with highest error rate
# - Service with highest latency increase
# - Service with rate drop (if upstream)
```

### Pattern 2: Logs → Metrics → Traces Workflow

**Step 1: Start with Logs (What happened?)**

```bash
# Find errors around incident time
kubectl logs -l app=order-service --since=30m | grep -i error

# Example output:
# 2025-10-26 10:15:32 ERROR [trace_id=abc123] Database connection timeout
# 2025-10-26 10:15:45 ERROR [trace_id=def456] Payment gateway unreachable
# 2025-10-26 10:16:12 ERROR [trace_id=ghi789] Order processing failed
```

**Step 2: Check Metrics (How widespread?)**

```promql
# How many errors?
sum(rate(logs_total{level="error", service="order-service"}[5m]))

# Which endpoint?
sum by (endpoint) (rate(http_requests_total{status="500", service="order-service"}[5m]))

# When did it start?
delta(http_requests_total{status="500", service="order-service"}[1h])
```

**Step 3: Trace Deep Dive (Where is the bottleneck?)**

```
# Use trace_id from logs (abc123)
# Open Jaeger/Tempo UI → Search trace_id=abc123

Trace View:
order-service           [200ms]
  ├─ validate-order      [10ms]
  ├─ check-inventory     [50ms]
  ├─ process-payment     [5000ms]  ← SLOW!
  │   ├─ call-payment-gateway [4950ms] ← BOTTLENECK!
  │   └─ update-ledger   [50ms]
  └─ send-confirmation   [20ms]
```

**Diagnosis**: Payment gateway timeout (4950ms vs expected 100ms)

### Pattern 3: Correlation IDs for Request Tracking

```python
import uuid
import logging
from flask import Flask, request, g

app = Flask(__name__)

@app.before_request
def set_correlation_id():
    # Extract or generate correlation ID
    correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
    g.correlation_id = correlation_id

@app.after_request
def add_correlation_header(response):
    response.headers['X-Correlation-ID'] = g.correlation_id
    return response

# Configure logger with correlation ID
class CorrelationFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = getattr(g, 'correlation_id', 'N/A')
        return True

logging.basicConfig(
    format='%(asctime)s [correlation_id=%(correlation_id)s] %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)
logger.addFilter(CorrelationFilter())

@app.route('/api/orders', methods=['POST'])
def create_order():
    logger.info("Creating order")

    # Pass correlation ID to downstream services
    headers = {'X-Correlation-ID': g.correlation_id}
    response = requests.post('http://inventory-service/check', headers=headers)

    logger.info("Order created successfully")
    return {"order_id": "12345"}

# Log output:
# 2025-10-26 10:30:15 [correlation_id=abc-123-def] INFO Creating order
# 2025-10-26 10:30:16 [correlation_id=abc-123-def] INFO Order created successfully
```

### Pattern 4: Time-Travel Debugging with Traces

**Scenario**: User reports checkout failed at 10:15 AM

```
1. Find user's trace:
   - Search by user_id in Jaeger: user_id=user_789 timestamp>2025-10-26T10:10:00
   - Or search by correlation_id if logged

2. Examine trace timeline:
   checkout-service    [10:15:32 - 10:15:37]  5s
     ├─ cart-service   [10:15:32 - 10:15:33]  1s
     ├─ payment        [10:15:33 - 10:15:38]  5s  ← TIMEOUT!
     └─ inventory      [not reached]

3. Drill into payment span:
   - Status: ERROR
   - Error message: "Connection refused: payment-gateway:8080"
   - Attributes:
     - payment.amount: 99.99
     - payment.method: credit_card
     - retry.count: 3

4. Cross-reference with logs:
   grep "correlation_id=trace_xyz" logs/payment-service.log
   → "2025-10-26 10:15:33 ERROR Failed to connect to payment gateway after 3 retries"

5. Check metrics at 10:15:
   - payment_gateway_connections{state="failed"} → spike at 10:15
   - payment_gateway_health → DOWN at 10:14

6. Root cause: Payment gateway crash at 10:14, user checkout at 10:15 failed
```

### Pattern 5: Database Query Debugging

```python
import logging
from opentelemetry import trace
from sqlalchemy import event, create_engine

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

engine = create_engine('postgresql://localhost/mydb')

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    # Start span for SQL query
    span = tracer.start_span("db.query")
    span.set_attribute("db.statement", statement)
    span.set_attribute("db.system", "postgresql")
    context._span = span
    context._query_start_time = time.time()

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    duration = time.time() - context._query_start_time
    context._span.set_attribute("db.duration_ms", duration * 1000)
    context._span.end()

    # Log slow queries
    if duration > 1.0:
        logger.warning(f"Slow query ({duration:.2f}s): {statement[:100]}")

# Usage
with tracer.start_as_current_span("get_user_orders"):
    user = session.query(User).filter_by(id=user_id).first()  # Auto-traced
    orders = session.query(Order).filter_by(user_id=user_id).all()  # Auto-traced

# Trace shows:
# get_user_orders [150ms]
#   ├─ db.query [10ms] "SELECT * FROM users WHERE id = ?"
#   └─ db.query [140ms] "SELECT * FROM orders WHERE user_id = ?"  ← SLOW!
```

### Pattern 6: Runbook Creation from Incidents

**Runbook Template**:

```markdown
# Incident: Payment Gateway Timeout (2025-10-26)

## Symptoms
- Users unable to complete checkout
- Error: "Payment processing failed, please try again"
- Alert: `payment_errors_rate > 5%`

## Detection
- Alert fired: `payment_gateway_health == 0`
- Dashboard: RED metrics show 50% error rate on `/api/checkout`

## Investigation
1. Check RED metrics:
   ```promql
   sum(rate(http_requests_total{service="payment", status="500"}[5m]))
   ```

2. Find failing requests in logs:
   ```bash
   kubectl logs -l app=payment-service --since=30m | grep ERROR
   ```

3. Trace sample failed request:
   - Search Jaeger: service=payment status=error time>now-30m
   - Identify span with error

## Diagnosis
- Payment gateway connection timeout (5s)
- Root cause: Payment gateway service crash

## Mitigation (Immediate)
1. Check payment gateway health:
   ```bash
   kubectl get pods -l app=payment-gateway
   ```

2. Restart payment gateway:
   ```bash
   kubectl rollout restart deployment/payment-gateway
   ```

3. Monitor recovery:
   ```promql
   payment_gateway_health
   ```

## Resolution (Long-term)
- Implement circuit breaker pattern
- Add retry with exponential backoff
- Set up redundant payment gateway instances
- Add alerting for payment gateway health

## Prevention
- Deploy Istio circuit breaker config
- Add PodDisruptionBudget for payment gateway
- Implement graceful degradation (queue payments for retry)

## Related Incidents
- [2025-09-15] Payment gateway timeout (similar root cause)
- [2025-08-22] Database connection pool exhaustion

## Postmortem
- [Link to postmortem doc]
```

### Pattern 7: Blameless Postmortem

**Postmortem Template**:

```markdown
# Postmortem: Payment Gateway Outage (2025-10-26)

## Incident Summary
- **Date**: 2025-10-26 10:14 - 10:45 UTC
- **Duration**: 31 minutes
- **Severity**: SEV-2 (Revenue impact)
- **Impact**: 15% of checkout attempts failed (~$50k revenue at risk)

## Timeline
- **10:14**: Payment gateway pod crash (OOM)
- **10:15**: First user reports checkout failure
- **10:16**: Alert fired: `payment_errors_rate > 5%`
- **10:18**: On-call engineer paged
- **10:22**: Investigation started
- **10:28**: Payment gateway restarted
- **10:30**: Health check passed
- **10:35**: Error rate returned to normal
- **10:45**: Incident marked resolved

## Root Cause
Payment gateway pod exceeded memory limit (2GB) due to connection leak in payment provider SDK v1.2.3. Under high load, SDK failed to close idle connections, leading to OOM crash.

## What Went Well
- Alert fired within 2 minutes of first error
- Correlation IDs enabled quick trace lookup
- Distributed tracing pinpointed exact failing span
- Runbook had clear mitigation steps

## What Went Wrong
- No memory usage alerting for payment gateway
- Single replica of payment gateway (no redundancy)
- Circuit breaker not configured (cascading failures)
- SDK version not pinned (auto-updated to buggy version)

## Action Items
1. **[P0]** Add memory usage alerts for all critical services (Owner: @alice, Due: 2025-10-28)
2. **[P0]** Scale payment gateway to 3 replicas with PDB (Owner: @bob, Due: 2025-10-27)
3. **[P1]** Implement circuit breaker with 10s timeout (Owner: @charlie, Due: 2025-11-02)
4. **[P1]** Pin SDK versions in requirements.txt (Owner: @alice, Due: 2025-10-27)
5. **[P2]** Add integration tests for payment flow (Owner: @bob, Due: 2025-11-10)
6. **[P2]** Update runbook with memory debugging steps (Owner: @charlie, Due: 2025-10-30)

## Lessons Learned
- **Observability gap**: Missing memory metrics for critical services
- **Architecture gap**: Single point of failure (payment gateway)
- **Process gap**: SDK updates without testing

## Follow-up
- Review all critical services for similar gaps
- Implement mandatory testing for dependency updates
```

---

## Quick Reference

### Incident Response Commands

```bash
# Check pod health
kubectl get pods -l app=service-name

# View recent logs
kubectl logs -l app=service-name --since=30m --tail=100

# Stream logs
kubectl logs -f -l app=service-name

# Get pod metrics
kubectl top pods -l app=service-name

# Describe pod (events)
kubectl describe pod service-name-abc123

# Execute into pod
kubectl exec -it service-name-abc123 -- /bin/bash

# Port forward for debugging
kubectl port-forward service-name-abc123 8080:8080
```

### Useful PromQL Queries

```promql
# Error rate (percentage)
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
/
sum(rate(http_requests_total[5m])) by (service)
* 100

# Latency increase (current vs 1h ago)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
/
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m] offset 1h))

# Request rate change
sum(rate(http_requests_total[5m])) by (service)
/
sum(rate(http_requests_total[5m] offset 1h)) by (service)

# Memory usage
container_memory_usage_bytes{pod=~"service-.*"} / 1024 / 1024  # MB

# CPU usage
rate(container_cpu_usage_seconds_total{pod=~"service-.*"}[5m]) * 100  # %
```

### Jaeger Search Queries

```
# By service and status
service=order-service status=error

# By tag
http.status_code=500
user_id=user_789

# By time range
service=payment minDuration=1s maxDuration=10s

# By operation
service=checkout operation=/api/checkout
```

---

## Anti-Patterns

### ❌ Starting with Traces Instead of Metrics

```
# WRONG: Jump straight to traces
1. Alert fires → 2. Search traces for errors

# CORRECT: Follow workflow
1. Alert fires → 2. Check RED metrics → 3. Find pattern → 4. Sample traces
```

### ❌ No Correlation IDs

```python
# WRONG: No request tracking across services
def call_service_a():
    requests.post('http://service-a/api')

def call_service_b():
    requests.post('http://service-b/api')

# CORRECT: Propagate correlation ID
def call_service(url):
    headers = {'X-Correlation-ID': g.correlation_id}
    requests.post(url, headers=headers)
```

### ❌ Blaming Individuals in Postmortems

```markdown
# WRONG: Blame-focused
## Root Cause
Bob deployed buggy code without testing.

# CORRECT: System-focused
## Root Cause
Deployment pipeline lacked integration tests, allowing buggy SDK update to reach production.

## Action Items
- Add integration tests to CI/CD pipeline
- Implement mandatory code review for dependency updates
```

### ❌ No Follow-up on Action Items

```markdown
# WRONG: No ownership or deadlines
## Action Items
- Add alerts
- Fix bug
- Update runbook

# CORRECT: Clear ownership and deadlines
## Action Items
1. **[P0]** Add memory alerts (Owner: @alice, Due: 2025-10-28)
2. **[P1]** Fix connection leak (Owner: @bob, Due: 2025-11-02)
3. **[P2]** Update runbook (Owner: @charlie, Due: 2025-10-30)
```

---

## Related Skills

- **distributed-tracing.md** - Deep dive into distributed tracing
- **metrics-instrumentation.md** - Setting up RED metrics
- **structured-logging.md** - Effective log formatting for debugging
- **opentelemetry-integration.md** - Correlating traces, metrics, logs
- **alerting-strategy.md** - Setting up effective alerts

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
