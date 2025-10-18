---
name: network-resilience-patterns
description: Building robust network applications
---



# Network Resilience Patterns

**Use this skill when:**
- Building robust network applications
- Handling unreliable connections
- Implementing retry and backoff strategies
- Creating fault-tolerant distributed systems
- Preventing cascading failures

## Retry Patterns

### Exponential Backoff

```python
import time
import random

def exponential_backoff_retry(func, max_retries=5, base_delay=1, max_delay=60):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)
            sleep_time = delay + jitter

            print(f"Attempt {attempt + 1} failed: {e}")
            print(f"Retrying in {sleep_time:.2f}s...")
            time.sleep(sleep_time)

# Usage
result = exponential_backoff_retry(lambda: api_call())
```

### Async Retry with Tenacity

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import httpx

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=retry_if_exception_type(httpx.HTTPError)
)
async def fetch_with_retry(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

# Usage
data = await fetch_with_retry("https://api.example.com/data")
```

## Circuit Breaker

### Basic Circuit Breaker

```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failures = 0

            return result

        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN

            raise

# Usage
breaker = CircuitBreaker(failure_threshold=3, timeout=30)

try:
    result = breaker.call(api_call, param1, param2)
except Exception as e:
    print(f"Call failed: {e}")
```

## Timeout Patterns

### Request Timeout

```python
import httpx

async def fetch_with_timeout(url, timeout_seconds=10):
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url)
            return response.json()
    except httpx.TimeoutException:
        print(f"Request timed out after {timeout_seconds}s")
        raise

# Different timeouts for different operations
async def fetch_with_custom_timeouts(url):
    timeout = httpx.Timeout(
        connect=5.0,    # Connection timeout
        read=10.0,      # Read timeout
        write=5.0,      # Write timeout
        pool=None       # Pool timeout
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.get(url)
```

## Fallback Strategies

### Graceful Degradation

```python
async def get_user_data(user_id):
    # Try primary source
    try:
        return await fetch_from_primary_api(user_id)
    except Exception as e:
        print(f"Primary failed: {e}")

        # Try cache
        try:
            cached = await get_from_cache(user_id)
            if cached:
                return cached
        except Exception:
            pass

        # Try secondary source
        try:
            return await fetch_from_secondary_api(user_id)
        except Exception as e2:
            print(f"Secondary failed: {e2}")

            # Return minimal default data
            return {"id": user_id, "name": "Unknown", "status": "unavailable"}
```

## Connection Pooling

### HTTP Connection Pool

```python
import httpx

# Reuse connections
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100
    ),
    timeout=30.0
)

async def make_requests():
    # All requests reuse connections
    results = []
    for i in range(100):
        response = await client.get(f"https://api.example.com/item/{i}")
        results.append(response.json())

    return results

# Remember to close client
await client.aclose()
```

## Rate Limiting

### Token Bucket

```python
import time
import asyncio

class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()

    async def acquire(self, tokens=1):
        while True:
            now = time.time()
            elapsed = now - self.last_refill

            # Refill tokens
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return

            # Wait for more tokens
            await asyncio.sleep(0.1)

# Usage
bucket = TokenBucket(capacity=10, refill_rate=1)  # 1 token/second

async def rate_limited_request(url):
    await bucket.acquire()
    return await fetch(url)
```

## Health Checks

### Service Health Monitoring

```python
import asyncio
from dataclasses import dataclass
from typing import Dict

@dataclass
class HealthStatus:
    healthy: bool
    latency_ms: float
    last_check: float

class HealthMonitor:
    def __init__(self, check_interval=30):
        self.check_interval = check_interval
        self.services: Dict[str, HealthStatus] = {}

    async def check_service(self, name, check_func):
        start = time.time()
        try:
            await asyncio.wait_for(check_func(), timeout=5)
            latency = (time.time() - start) * 1000

            self.services[name] = HealthStatus(
                healthy=True,
                latency_ms=latency,
                last_check=time.time()
            )
        except Exception as e:
            self.services[name] = HealthStatus(
                healthy=False,
                latency_ms=0,
                last_check=time.time()
            )

    async def monitor(self, services):
        while True:
            for name, check_func in services.items():
                await self.check_service(name, check_func)

            await asyncio.sleep(self.check_interval)

# Usage
monitor = HealthMonitor()

services = {
    "api": lambda: fetch("https://api.example.com/health"),
    "database": lambda: check_db_connection(),
    "cache": lambda: check_redis()
}

asyncio.create_task(monitor.monitor(services))
```

## Anti-Patterns to Avoid

**DON'T retry indefinitely:**
```python
# ❌ BAD
while True:
    try:
        return api_call()
    except:
        pass  # Infinite loop!

# ✅ GOOD
for attempt in range(max_retries):
    try:
        return api_call()
    except Exception as e:
        if attempt == max_retries - 1:
            raise
```

**DON'T ignore timeout configuration:**
```python
# ❌ BAD - Default timeout might be too long
response = requests.get(url)

# ✅ GOOD
response = requests.get(url, timeout=10)
```

## Related Skills

- **tailscale-vpn.md** - Reliable network layer
- **mosh-resilient-ssh.md** - Connection resilience
- **mtls-implementation.md** - Secure resilient connections
