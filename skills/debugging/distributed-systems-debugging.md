---
name: debugging-distributed-systems-debugging
description: Debugging distributed systems with trace correlation, cross-service workflows, request replay, clock skew handling, and chaos engineering
---

# Distributed Systems Debugging

**Scope**: Distributed tracing correlation, cross-service debugging, request replay, traffic shadowing, clock skew, chaos engineering, cascading failures

**Lines**: 440

**Last Updated**: 2025-10-26

---

## When to Use This Skill

Use this skill when:
- Debugging failures that span multiple services
- Investigating request flows across microservices
- Tracking down distributed deadlocks or race conditions
- Analyzing cascading failures or circuit breaker trips
- Debugging eventual consistency issues
- Troubleshooting distributed transactions (saga patterns)
- Investigating clock skew or time synchronization problems
- Using chaos engineering to reproduce production issues

**Don't use** for:
- Single-service debugging (use standard debugging)
- Monolithic applications (use IDE debuggers)
- Local development (use breakpoints)

---

## Core Concepts

### Distributed Systems Debugging Challenges

**Unique challenges**:
1. **No global state**: Each service has partial view
2. **Asynchronous communication**: Request/response not always paired
3. **Network unreliability**: Packets drop, timeout, reorder
4. **Clock skew**: Timestamps from different hosts diverge
5. **Emergent behavior**: Bugs appear only under specific interaction patterns
6. **Partial failures**: Some services succeed, others fail
7. **Cascading failures**: One slow service affects entire system

### Debugging Layers in Distributed Systems

```
Layer 1: Request Tracing (follow single request)
├─ Trace ID correlation across services
├─ Span hierarchy (parent-child relationships)
└─ Timing analysis (latency breakdown)

Layer 2: Cross-Service Analysis (multi-request patterns)
├─ Request replay/shadowing
├─ Dependency mapping
└─ Circuit breaker states

Layer 3: System-Wide Behavior (emergent issues)
├─ Clock skew detection
├─ Distributed deadlock analysis
└─ Cascading failure patterns

Layer 4: Chaos Engineering (controlled failure injection)
├─ Network partition simulation
├─ Latency injection
└─ Service failure scenarios
```

### Common Distributed Failure Patterns

| Pattern | Symptom | Debugging Approach |
|---------|---------|-------------------|
| **Cascading failure** | One slow service causes timeouts everywhere | Trace latency, check circuit breakers |
| **Distributed deadlock** | Services waiting on each other indefinitely | Analyze request dependencies, check for cycles |
| **Split brain** | Multiple nodes think they're leader | Check consensus logs, clock skew |
| **Thundering herd** | Simultaneous requests overwhelm service | Analyze request timestamps, check for jitter |
| **Data inconsistency** | Different services see different data | Check event ordering, compare timestamps |

---

## Patterns

### Pattern 1: Trace ID Correlation Across Services

```python
import uuid
from opentelemetry import trace
from opentelemetry.propagate import inject, extract
from fastapi import FastAPI, Request, HTTPException
import httpx
import structlog

app = FastAPI()
tracer = trace.get_tracer(__name__)
logger = structlog.get_logger()

# Service A: Gateway
@app.post("/api/orders")
async def create_order(request: Request, order_data: dict):
    # Extract trace context from incoming request (if exists)
    ctx = extract(request.headers)

    with tracer.start_as_current_span("create_order", context=ctx) as span:
        # Get trace ID for logging
        trace_id = format(span.get_span_context().trace_id, '032x')
        span_id = format(span.get_span_context().span_id, '016x')

        log = logger.bind(trace_id=trace_id, span_id=span_id)
        log.info("Order creation started", order_data=order_data)

        # Propagate trace context to downstream services
        headers = {}
        inject(headers)  # Injects traceparent, tracestate headers

        try:
            # Call Service B (Inventory)
            async with httpx.AsyncClient() as client:
                inventory_response = await client.post(
                    "http://inventory-service/api/reserve",
                    json={"product_id": order_data["product_id"]},
                    headers=headers  # Propagate trace context
                )

                if inventory_response.status_code != 200:
                    log.error(
                        "Inventory reservation failed",
                        status_code=inventory_response.status_code,
                        response=inventory_response.text
                    )
                    raise HTTPException(
                        status_code=503,
                        detail="Inventory service unavailable"
                    )

                # Call Service C (Payment)
                payment_response = await client.post(
                    "http://payment-service/api/charge",
                    json={"amount": order_data["amount"]},
                    headers=headers  # Same trace context
                )

                if payment_response.status_code != 200:
                    # Compensating transaction: release inventory
                    await client.post(
                        "http://inventory-service/api/release",
                        json={"product_id": order_data["product_id"]},
                        headers=headers
                    )
                    log.error("Payment failed, inventory released")
                    raise HTTPException(
                        status_code=402,
                        detail="Payment processing failed"
                    )

                log.info("Order created successfully", trace_id=trace_id)
                return {
                    "order_id": str(uuid.uuid4()),
                    "trace_id": trace_id,
                    "status": "success"
                }

        except httpx.RequestError as e:
            log.error("HTTP request failed", error=str(e), exc_info=True)
            span.record_exception(e)
            raise HTTPException(status_code=503, detail="Service unavailable")

# Service B: Inventory Service
@app.post("/api/reserve")
async def reserve_inventory(request: Request, data: dict):
    # Extract trace context from upstream service
    ctx = extract(request.headers)

    with tracer.start_as_current_span("reserve_inventory", context=ctx) as span:
        trace_id = format(span.get_span_context().trace_id, '032x')
        log = logger.bind(trace_id=trace_id, service="inventory")

        log.info("Inventory reservation", product_id=data["product_id"])

        # Simulate inventory check
        if data["product_id"] == "out-of-stock":
            log.error("Product out of stock", product_id=data["product_id"])
            return {"status": "out_of_stock"}, 409

        log.info("Inventory reserved", product_id=data["product_id"])
        return {"status": "reserved"}

# Service C: Payment Service
@app.post("/api/charge")
async def charge_payment(request: Request, data: dict):
    ctx = extract(request.headers)

    with tracer.start_as_current_span("charge_payment", context=ctx) as span:
        trace_id = format(span.get_span_context().trace_id, '032x')
        log = logger.bind(trace_id=trace_id, service="payment")

        log.info("Payment processing", amount=data["amount"])

        # Simulate payment processing
        if data["amount"] > 10000:
            log.error("Payment amount exceeds limit", amount=data["amount"])
            return {"status": "declined"}, 402

        log.info("Payment successful", amount=data["amount"])
        return {"status": "charged"}
```

**Query traces across services** (Grafana Tempo):
```promql
# Find all spans for trace ID
{trace_id="a1b2c3d4e5f6g7h8"}

# Find traces with errors in any service
{status.code="ERROR"}

# Find slow traces (>1s)
{duration > 1s}

# Find traces involving specific service
{service.name="payment-service"}
```

### Pattern 2: Request Replay for Debugging

```python
import json
import asyncio
from typing import Dict, Any
from datetime import datetime
import httpx

class RequestRecorder:
    """
    Record requests for later replay.
    """

    def __init__(self, storage_path: str = "/tmp/requests.jsonl"):
        self.storage_path = storage_path

    async def record_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Any,
        response_status: int,
        response_body: Any
    ):
        """
        Record request/response for replay.
        """
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "request": {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body
            },
            "response": {
                "status": response_status,
                "body": response_body
            }
        }

        with open(self.storage_path, "a") as f:
            f.write(json.dumps(record) + "\n")

class RequestReplayer:
    """
    Replay recorded requests against test environment.
    """

    def __init__(self, storage_path: str = "/tmp/requests.jsonl"):
        self.storage_path = storage_path

    async def replay_all(self, target_url: str):
        """
        Replay all recorded requests.
        """
        with open(self.storage_path, "r") as f:
            for line in f:
                record = json.loads(line)
                await self.replay_request(record, target_url)

    async def replay_request(self, record: Dict, target_url: str):
        """
        Replay single request.
        """
        req = record["request"]

        # Replace production URL with target URL
        url = req["url"].replace("https://api.example.com", target_url)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=req["method"],
                    url=url,
                    headers=req["headers"],
                    json=req["body"]
                )

                # Compare response with recorded response
                original_status = record["response"]["status"]
                if response.status_code != original_status:
                    print(f"MISMATCH: Expected {original_status}, got {response.status_code}")
                    print(f"URL: {url}")
                    print(f"Response: {response.text}")

            except Exception as e:
                print(f"ERROR replaying request: {e}")
                print(f"URL: {url}")

# Middleware to record requests
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

recorder = RequestRecorder()

class RecordingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Record request
        body = await request.body()

        response = await call_next(request)

        # Record response
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        await recorder.record_request(
            method=request.method,
            url=str(request.url),
            headers=request.headers,
            body=body.decode() if body else None,
            response_status=response.status_code,
            response_body=response_body.decode()
        )

        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers)
        )

# Usage
app.add_middleware(RecordingMiddleware)

# Replay requests in test environment
# python replay.py --target http://localhost:8000
```

### Pattern 3: Traffic Shadowing (Dark Traffic)

```yaml
# Kubernetes: Shadow traffic to debug environment
apiVersion: v1
kind: Service
metadata:
  name: api-service
spec:
  selector:
    app: api
  ports:
  - port: 80
    targetPort: 8080

---
# Envoy/Istio: Mirror traffic to debug instance
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: api-service
spec:
  hosts:
  - api-service
  http:
  - match:
    - headers:
        x-debug:
          exact: "true"
    route:
    - destination:
        host: api-service
        subset: production
      weight: 100
    mirror:
      host: api-service
      subset: debug  # Mirror to debug instance
    mirrorPercentage:
      value: 100  # Mirror 100% of matching requests

---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: api-service
spec:
  host: api-service
  subsets:
  - name: production
    labels:
      version: v1
  - name: debug
    labels:
      version: debug
```

**Application-level traffic shadowing**:
```python
from fastapi import Request, BackgroundTasks
import httpx

@app.post("/api/orders")
async def create_order(
    request: Request,
    order_data: dict,
    background_tasks: BackgroundTasks
):
    # Process request normally
    result = await process_order(order_data)

    # Shadow request to debug environment (async)
    if should_shadow_request(request):
        background_tasks.add_task(
            shadow_request,
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers),
            body=order_data
        )

    return result

async def shadow_request(method: str, url: str, headers: dict, body: dict):
    """
    Send request to debug environment in background.
    """
    # Replace production URL with debug URL
    debug_url = url.replace("api.example.com", "debug.example.com")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=debug_url,
                headers=headers,
                json=body,
                timeout=5.0  # Don't block production traffic
            )

            # Log differences
            logger.info(
                "Shadow request completed",
                status_code=response.status_code,
                url=debug_url
            )

        except Exception as e:
            # Don't fail production traffic
            logger.error("Shadow request failed", error=str(e))

def should_shadow_request(request: Request) -> bool:
    """
    Determine if request should be shadowed.
    """
    # Shadow 10% of traffic
    import random
    return random.random() < 0.10

    # Or shadow specific users
    # user_id = request.headers.get("X-User-ID")
    # return user_id in ["debug_user_1", "debug_user_2"]
```

### Pattern 4: Clock Skew Detection and Handling

```python
import time
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()

class ClockSkewDetector:
    """
    Detect and handle clock skew in distributed systems.
    """

    def __init__(self, max_skew_seconds: int = 300):  # 5 minutes
        self.max_skew_seconds = max_skew_seconds

    def check_timestamp(
        self,
        remote_timestamp: str,
        service_name: str
    ) -> bool:
        """
        Check if remote timestamp is within acceptable range.
        """
        try:
            remote_time = datetime.fromisoformat(remote_timestamp)
            local_time = datetime.utcnow()
            skew = abs((remote_time - local_time).total_seconds())

            if skew > self.max_skew_seconds:
                logger.warning(
                    "Clock skew detected",
                    service=service_name,
                    remote_timestamp=remote_timestamp,
                    local_timestamp=local_time.isoformat(),
                    skew_seconds=skew
                )
                return False

            return True

        except Exception as e:
            logger.error("Invalid timestamp format", error=str(e))
            return False

    def sync_with_ntp(self):
        """
        Sync local clock with NTP server.
        """
        import ntplib
        from datetime import datetime

        ntp_client = ntplib.NTPClient()

        try:
            response = ntp_client.request('pool.ntp.org', version=3)
            local_time = time.time()
            ntp_time = response.tx_time
            offset = ntp_time - local_time

            logger.info(
                "NTP sync completed",
                offset_ms=offset * 1000,
                ntp_server="pool.ntp.org"
            )

            return offset

        except Exception as e:
            logger.error("NTP sync failed", error=str(e))
            return None

# Middleware to check clock skew
from fastapi import Request, HTTPException

clock_detector = ClockSkewDetector()

@app.middleware("http")
async def check_clock_skew(request: Request, call_next):
    # Check if request has timestamp header
    remote_timestamp = request.headers.get("X-Timestamp")

    if remote_timestamp:
        if not clock_detector.check_timestamp(
            remote_timestamp,
            request.headers.get("X-Service-Name", "unknown")
        ):
            raise HTTPException(
                status_code=400,
                detail="Clock skew detected. Check NTP sync."
            )

    response = await call_next(request)
    return response
```

**NTP sync commands**:
```bash
# Check NTP status
timedatectl status

# Sync with NTP server (Linux)
sudo ntpdate pool.ntp.org

# Enable NTP sync (systemd)
sudo timedatectl set-ntp true

# Check clock offset
ntpq -p
```

### Pattern 5: Chaos Engineering for Debugging

```python
import random
import asyncio
from fastapi import HTTPException

class ChaosMonkey:
    """
    Inject controlled failures for debugging.
    """

    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    async def inject_latency(
        self,
        min_ms: int = 100,
        max_ms: int = 1000,
        probability: float = 0.1
    ):
        """
        Inject random latency.
        """
        if not self.enabled:
            return

        if random.random() < probability:
            delay = random.randint(min_ms, max_ms) / 1000
            logger.warning("CHAOS: Injecting latency", delay_seconds=delay)
            await asyncio.sleep(delay)

    def inject_error(
        self,
        probability: float = 0.05,
        error_code: int = 503
    ):
        """
        Inject random errors.
        """
        if not self.enabled:
            return

        if random.random() < probability:
            logger.warning("CHAOS: Injecting error", error_code=error_code)
            raise HTTPException(
                status_code=error_code,
                detail="Chaos engineering: simulated failure"
            )

    def inject_timeout(
        self,
        probability: float = 0.05,
        timeout_seconds: int = 30
    ):
        """
        Inject timeout by sleeping indefinitely.
        """
        if not self.enabled:
            return

        if random.random() < probability:
            logger.warning("CHAOS: Injecting timeout", timeout_seconds=timeout_seconds)
            import time
            time.sleep(timeout_seconds)

# Enable chaos in specific environment
import os
chaos = ChaosMonkey(enabled=os.getenv("CHAOS_ENABLED") == "true")

@app.get("/api/users")
async def get_users():
    # Inject chaos
    await chaos.inject_latency(probability=0.1)
    chaos.inject_error(probability=0.05)

    users = await db.get_users()
    return users
```

**Using Chaos Mesh** (Kubernetes):
```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
spec:
  action: delay
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: api-service
  delay:
    latency: "100ms"
    jitter: "50ms"
  duration: "30s"

---
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-failure
spec:
  action: pod-failure
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: payment-service
  duration: "60s"
```

---

## Quick Reference

### Distributed Debugging Checklist

```markdown
## Step 1: Identify Trace
- [ ] Extract trace ID from error logs
- [ ] Find all spans in trace (Grafana Tempo, Jaeger)
- [ ] Identify failed span and service

## Step 2: Analyze Dependencies
- [ ] Check which services were called
- [ ] Verify trace context propagation
- [ ] Look for missing spans (broken propagation)

## Step 3: Check Timing
- [ ] Compare timestamps across services
- [ ] Look for clock skew (>5min difference)
- [ ] Identify slow spans (>1s)

## Step 4: Correlate with Infrastructure
- [ ] Check CPU/memory on affected services
- [ ] Review network metrics (latency, packet loss)
- [ ] Check for recent deployments

## Step 5: Reproduce
- [ ] Replay request in staging
- [ ] Use traffic shadowing
- [ ] Inject chaos (latency, errors)
```

### Trace Correlation Queries

```promql
# Grafana Loki + Tempo

# Find logs for trace
{app="api-service"} | json | trace_id="abc123"

# Find errors in trace
{trace_id="abc123"} | json | level="error"

# Find slow requests
{app="api-service"} | json | duration_ms > 1000 | trace_id!=""
```

---

## Anti-Patterns

### ❌ Not Propagating Trace Context

```python
# WRONG: Breaks trace chain
requests.get("http://service-b/api/data")

# CORRECT: Propagate trace context
headers = {}
inject(headers)
requests.get("http://service-b/api/data", headers=headers)
```

### ❌ Using Local Timestamps

```python
# WRONG: Clock skew causes issues
event_time = datetime.now()  # Local clock!

# CORRECT: Use monotonic clock or logical timestamps
event_time = time.monotonic()  # Monotonic clock
# Or: Use Lamport/Vector clocks for ordering
```

### ❌ Ignoring Compensating Transactions

```python
# WRONG: Leaves system in inconsistent state
await reserve_inventory()
await charge_payment()  # Fails, but inventory not released!

# CORRECT: Compensate on failure
try:
    await reserve_inventory()
    await charge_payment()
except:
    await release_inventory()  # Compensating transaction
    raise
```

---

## Related Skills

- **observability/distributed-tracing.md** - Trace context propagation
- **debugging/production-debugging.md** - Non-intrusive debugging
- **testing/chaos-engineering.md** - Controlled failure injection
- **database/distributed-transactions.md** - Saga patterns

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
