---
name: dspy-production
description: Production deployment patterns for DSPy including serverless, containers, monitoring, caching, and cost optimization
---

# DSPy Production Deployment

**Scope**: Production deployment, caching, monitoring, error handling, versioning, cost optimization
**Lines**: ~500
**Last Updated**: 2025-10-30

## When to Use This Skill

Activate this skill when:
- Deploying DSPy programs to production environments
- Setting up monitoring and observability for DSPy applications
- Implementing caching strategies for cost optimization
- Configuring error handling and fallback mechanisms
- Setting up A/B testing and model versioning
- Implementing rate limiting and load balancing
- Optimizing production costs and performance
- Creating rollback and disaster recovery strategies

## Core Concepts

### Production Readiness Checklist

**Infrastructure**:
- Deployment strategy (serverless, containers, VMs)
- Auto-scaling and load balancing
- Health checks and readiness probes
- SSL/TLS configuration

**Reliability**:
- Error handling and circuit breakers
- Fallback mechanisms
- Retry policies with exponential backoff
- Timeout configuration

**Performance**:
- Caching layers (Redis, in-memory)
- Request batching
- Connection pooling
- Response streaming

**Observability**:
- Structured logging
- Metrics and alerts
- Distributed tracing
- Cost tracking

**Security**:
- API key management
- Rate limiting
- Input validation
- Output filtering

### Deployment Strategies

**Serverless** (Modal, AWS Lambda, Cloud Run):
- Pay-per-use pricing
- Automatic scaling
- Cold start considerations
- Stateless by default

**Containerized** (Docker, Kubernetes):
- Consistent environments
- Resource control
- Orchestration capabilities
- State management options

**Hybrid**:
- Serverless for inference
- Stateful services for caching/monitoring
- Best of both worlds

---

## Patterns

### Pattern 1: Modal Serverless Deployment

```python
import modal
import dspy
from datetime import datetime

app = modal.App("dspy-production")

# Create persistent cache volume
cache_volume = modal.Volume.from_name("dspy-cache", create_if_missing=True)

# Create image with dependencies
image = modal.Image.debian_slim().pip_install(
    "dspy-ai",
    "openai",
    "redis",
    "prometheus-client",
)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("openai-api-key")],
    volumes={"/cache": cache_volume},
    timeout=300,
    retries=2,  # Automatic retry on failure
    container_idle_timeout=60,  # Keep warm for 1 minute
)
@modal.web_endpoint(method="POST")
def predict(request: dict):
    """Production DSPy endpoint with caching and monitoring."""
    import os
    import json
    from pathlib import Path

    # Initialize DSPy (cached across warm starts)
    lm = dspy.LM("openai/gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"])
    dspy.configure(lm=lm)

    # Load cached program if available
    cache_path = Path("/cache/program.json")
    if cache_path.exists():
        program = dspy.ChainOfThought("question -> answer")
        # Load optimized parameters
        program.load(str(cache_path))
    else:
        program = dspy.ChainOfThought("question -> answer")

    # Extract request data
    question = request.get("question")
    if not question:
        return {"error": "Missing 'question' field"}, 400

    # Execute prediction with error handling
    try:
        start_time = datetime.now()
        result = program(question=question)
        duration = (datetime.now() - start_time).total_seconds()

        # Log metrics
        print(json.dumps({
            "event": "prediction",
            "duration_seconds": duration,
            "question_length": len(question),
            "answer_length": len(result.answer),
            "timestamp": datetime.utcnow().isoformat(),
        }))

        return {
            "answer": result.answer,
            "reasoning": getattr(result, "reasoning", None),
            "duration_seconds": duration,
        }

    except Exception as e:
        # Log error
        print(json.dumps({
            "event": "error",
            "error": str(e),
            "question": question[:100],  # Truncate for privacy
            "timestamp": datetime.utcnow().isoformat(),
        }))
        return {"error": "Prediction failed"}, 500

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("openai-api-key")],
    volumes={"/cache": cache_volume},
    schedule=modal.Cron("0 2 * * *"),  # Daily at 2 AM
)
def update_model():
    """Scheduled task to update cached model."""
    import os
    from pathlib import Path

    # Re-optimize model with latest data
    lm = dspy.LM("openai/gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"])
    dspy.configure(lm=lm)

    program = dspy.ChainOfThought("question -> answer")
    # Add optimization logic here

    # Save to cache volume
    cache_path = Path("/cache/program.json")
    program.save(str(cache_path))
    cache_volume.commit()  # Persist changes

    print(f"Model updated at {datetime.utcnow().isoformat()}")
```

**When to use**:
- Low to medium traffic applications
- Unpredictable load patterns
- Cost optimization priority
- No infrastructure management desired

**Benefits**:
- Zero infrastructure management
- Automatic scaling
- Pay only for compute time
- Built-in retries and timeouts

### Pattern 2: Redis Caching Layer

```python
import dspy
import redis
import hashlib
import json
from typing import Optional

class CachedDSPyModule(dspy.Module):
    """DSPy module with Redis caching."""

    def __init__(
        self,
        signature: str,
        redis_url: str = "redis://localhost:6379",
        ttl_seconds: int = 3600,
        cache_enabled: bool = True,
    ):
        super().__init__()
        self.predictor = dspy.ChainOfThought(signature)
        self.cache_enabled = cache_enabled
        self.ttl_seconds = ttl_seconds

        if cache_enabled:
            self.redis_client = redis.from_url(redis_url)

    def _get_cache_key(self, **kwargs) -> str:
        """Generate deterministic cache key from inputs."""
        key_data = json.dumps(kwargs, sort_keys=True)
        return f"dspy:{hashlib.sha256(key_data.encode()).hexdigest()}"

    def _get_from_cache(self, cache_key: str) -> Optional[dict]:
        """Retrieve from cache."""
        if not self.cache_enabled:
            return None

        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"Cache read error: {e}")

        return None

    def _set_cache(self, cache_key: str, value: dict):
        """Store in cache with TTL."""
        if not self.cache_enabled:
            return

        try:
            self.redis_client.setex(
                cache_key,
                self.ttl_seconds,
                json.dumps(value),
            )
        except Exception as e:
            print(f"Cache write error: {e}")

    def forward(self, **kwargs):
        """Execute with caching."""
        cache_key = self._get_cache_key(**kwargs)

        # Try cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            print(f"Cache hit: {cache_key}")
            return dspy.Prediction(**cached_result)

        # Cache miss - execute prediction
        print(f"Cache miss: {cache_key}")
        result = self.predictor(**kwargs)

        # Store in cache
        result_dict = {
            field: getattr(result, field)
            for field in result._fields
        }
        self._set_cache(cache_key, result_dict)

        return result

# Usage
cached_qa = CachedDSPyModule(
    "question -> answer",
    redis_url="redis://localhost:6379",
    ttl_seconds=3600,  # 1 hour
)

# First call - cache miss
result1 = cached_qa(question="What is DSPy?")

# Second call - cache hit (no LM API call)
result2 = cached_qa(question="What is DSPy?")
```

**When to use**:
- High traffic with repeated queries
- Cost reduction priority
- Fast response times required
- Deterministic outputs

**Benefits**:
- Reduce LM API costs by 60-90%
- Sub-millisecond response times for cached results
- Scales horizontally with Redis cluster
- TTL for cache invalidation

### Pattern 3: Circuit Breaker Pattern

```python
import dspy
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Circuit breaker for DSPy LM calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""

        # Check if circuit should transition to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if (datetime.now() - self.last_failure_time).seconds >= self.recovery_timeout:
                print("Circuit transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")

        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful execution."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                print("Circuit transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            print(f"Circuit transitioning to OPEN (failures: {self.failure_count})")
            self.state = CircuitState.OPEN

class ResilientDSPyModule(dspy.Module):
    """DSPy module with circuit breaker and fallback."""

    def __init__(self, signature: str, fallback_response: str = "Service temporarily unavailable"):
        super().__init__()
        self.predictor = dspy.ChainOfThought(signature)
        self.circuit_breaker = CircuitBreaker()
        self.fallback_response = fallback_response

    def forward(self, **kwargs):
        """Execute with circuit breaker protection."""
        try:
            return self.circuit_breaker.call(self.predictor, **kwargs)
        except Exception as e:
            print(f"Circuit breaker activated: {e}")
            return dspy.Prediction(answer=self.fallback_response, error=str(e))

# Usage
resilient_qa = ResilientDSPyModule("question -> answer")

# Will use circuit breaker to protect against cascading failures
try:
    result = resilient_qa(question="What is DSPy?")
    print(result.answer)
except Exception as e:
    print(f"Request failed: {e}")
```

**When to use**:
- External API dependencies (LM providers)
- Preventing cascading failures
- Production systems requiring high availability
- Rate limit protection

**Benefits**:
- Fail fast during outages
- Automatic recovery testing
- Prevents resource exhaustion
- Graceful degradation

### Pattern 4: Prometheus Metrics and Monitoring

```python
import dspy
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Define metrics
prediction_counter = Counter(
    "dspy_predictions_total",
    "Total number of predictions",
    ["status", "module"],
)

prediction_duration = Histogram(
    "dspy_prediction_duration_seconds",
    "Prediction duration in seconds",
    ["module"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

lm_tokens = Counter(
    "dspy_lm_tokens_total",
    "Total LM tokens used",
    ["model", "type"],  # type: prompt or completion
)

lm_cost = Counter(
    "dspy_lm_cost_usd",
    "Estimated LM cost in USD",
    ["model"],
)

active_requests = Gauge(
    "dspy_active_requests",
    "Number of active requests",
)

class MonitoredDSPyModule(dspy.Module):
    """DSPy module with Prometheus metrics."""

    def __init__(self, signature: str, module_name: str = "default"):
        super().__init__()
        self.predictor = dspy.ChainOfThought(signature)
        self.module_name = module_name

    def forward(self, **kwargs):
        """Execute with metrics tracking."""
        active_requests.inc()
        start_time = time.time()

        try:
            result = self.predictor(**kwargs)

            # Record success metrics
            duration = time.time() - start_time
            prediction_counter.labels(status="success", module=self.module_name).inc()
            prediction_duration.labels(module=self.module_name).observe(duration)

            # Estimate token usage (if available)
            if hasattr(result, "_trace"):
                # DSPy traces include token info
                prompt_tokens = result._trace.get("prompt_tokens", 0)
                completion_tokens = result._trace.get("completion_tokens", 0)

                lm_tokens.labels(model="gpt-4o-mini", type="prompt").inc(prompt_tokens)
                lm_tokens.labels(model="gpt-4o-mini", type="completion").inc(completion_tokens)

                # Estimate cost (GPT-4o-mini pricing)
                cost = (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)
                lm_cost.labels(model="gpt-4o-mini").inc(cost)

            return result

        except Exception as e:
            prediction_counter.labels(status="error", module=self.module_name).inc()
            raise e

        finally:
            active_requests.dec()

# Start metrics server
start_http_server(8000)  # Metrics available at http://localhost:8000/metrics

# Usage
monitored_qa = MonitoredDSPyModule("question -> answer", module_name="qa_system")

# Metrics automatically tracked
result = monitored_qa(question="What is DSPy?")
```

**When to use**:
- Production deployments
- Cost tracking and optimization
- Performance monitoring
- SLA compliance verification

**Metrics to track**:
- Request rate (requests/second)
- Error rate (errors/total)
- Latency percentiles (p50, p95, p99)
- Token usage and cost
- Cache hit rate
- Active requests

### Pattern 5: A/B Testing and Model Versioning

```python
import dspy
import random
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ModelVersion:
    """Model version metadata."""
    name: str
    weight: float  # Traffic percentage (0.0 to 1.0)
    program: dspy.Module
    metrics: Dict[str, float]

class ABTestingRouter(dspy.Module):
    """Route requests to different model versions for A/B testing."""

    def __init__(self, versions: List[ModelVersion]):
        super().__init__()
        self.versions = versions
        self._validate_weights()

    def _validate_weights(self):
        """Ensure weights sum to 1.0."""
        total = sum(v.weight for v in self.versions)
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            raise ValueError(f"Version weights must sum to 1.0, got {total}")

    def _select_version(self) -> ModelVersion:
        """Select version based on weights."""
        rand = random.random()
        cumulative = 0.0

        for version in self.versions:
            cumulative += version.weight
            if rand <= cumulative:
                return version

        return self.versions[-1]  # Fallback

    def forward(self, **kwargs):
        """Route to selected version and track metrics."""
        version = self._select_version()

        start_time = datetime.now()
        try:
            result = version.program(**kwargs)
            duration = (datetime.now() - start_time).total_seconds()

            # Update metrics
            version.metrics["total_requests"] = version.metrics.get("total_requests", 0) + 1
            version.metrics["total_duration"] = version.metrics.get("total_duration", 0.0) + duration
            version.metrics["success_count"] = version.metrics.get("success_count", 0) + 1

            # Add version info to result
            result.model_version = version.name
            return result

        except Exception as e:
            version.metrics["error_count"] = version.metrics.get("error_count", 0) + 1
            raise e

    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get metrics for all versions."""
        return {
            v.name: {
                **v.metrics,
                "avg_duration": v.metrics.get("total_duration", 0) / max(v.metrics.get("total_requests", 1), 1),
                "error_rate": v.metrics.get("error_count", 0) / max(v.metrics.get("total_requests", 1), 1),
            }
            for v in self.versions
        }

# Create versions
baseline = ModelVersion(
    name="baseline",
    weight=0.7,  # 70% of traffic
    program=dspy.ChainOfThought("question -> answer"),
    metrics={},
)

optimized = ModelVersion(
    name="optimized_v2",
    weight=0.3,  # 30% of traffic
    program=dspy.ChainOfThought("question -> answer"),  # Load optimized version
    metrics={},
)

# Create A/B testing router
router = ABTestingRouter(versions=[baseline, optimized])

# Use router (automatically distributes traffic)
for _ in range(100):
    result = router(question="What is DSPy?")
    print(f"Used version: {result.model_version}")

# Check metrics
print("\nA/B Test Metrics:")
for version, metrics in router.get_metrics().items():
    print(f"{version}: {metrics}")
```

**When to use**:
- Testing new model versions
- Gradual rollouts
- Comparing optimization strategies
- Risk mitigation for changes

**Best practices**:
- Start with small traffic percentage (5-10%)
- Monitor error rates closely
- Use statistical significance tests
- Have rollback plan ready

### Pattern 6: Request Batching for Efficiency

```python
import dspy
from typing import List, Dict, Any
import asyncio
from collections import defaultdict
import time

class BatchProcessor(dspy.Module):
    """Batch multiple requests for efficient processing."""

    def __init__(
        self,
        signature: str,
        batch_size: int = 10,
        batch_timeout: float = 0.5,
    ):
        super().__init__()
        self.predictor = dspy.ChainOfThought(signature)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout

        self.pending_requests: List[Dict[str, Any]] = []
        self.request_futures: Dict[str, asyncio.Future] = {}

    async def process_batch(self):
        """Process accumulated batch."""
        if not self.pending_requests:
            return

        batch = self.pending_requests[:self.batch_size]
        self.pending_requests = self.pending_requests[self.batch_size:]

        # Process batch in parallel
        results = []
        for req in batch:
            try:
                result = self.predictor(**req["kwargs"])
                results.append({"id": req["id"], "result": result})
            except Exception as e:
                results.append({"id": req["id"], "error": str(e)})

        # Resolve futures
        for res in results:
            future = self.request_futures.pop(res["id"], None)
            if future:
                if "error" in res:
                    future.set_exception(Exception(res["error"]))
                else:
                    future.set_result(res["result"])

    async def predict_async(self, request_id: str, **kwargs):
        """Add request to batch and wait for result."""
        # Create future for this request
        future = asyncio.Future()
        self.request_futures[request_id] = future

        # Add to pending batch
        self.pending_requests.append({
            "id": request_id,
            "kwargs": kwargs,
        })

        # Trigger batch processing if full
        if len(self.pending_requests) >= self.batch_size:
            await self.process_batch()

        return await future

    async def batch_daemon(self):
        """Background task to process batches periodically."""
        while True:
            await asyncio.sleep(self.batch_timeout)
            await self.process_batch()

# Usage
batch_processor = BatchProcessor(
    "question -> answer",
    batch_size=10,
    batch_timeout=0.5,
)

async def main():
    # Start batch daemon
    asyncio.create_task(batch_processor.batch_daemon())

    # Send multiple requests
    tasks = [
        batch_processor.predict_async(f"req_{i}", question=f"Question {i}")
        for i in range(50)
    ]

    # Wait for all results
    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        print(f"Request {i}: {result.answer}")

# Run
asyncio.run(main())
```

**When to use**:
- High request volumes
- Latency tolerance (batch_timeout)
- Cost optimization (batch API pricing)
- GPU utilization improvement

**Benefits**:
- Reduce API calls by batching
- Better GPU utilization
- Lower per-request cost
- Throughput optimization

### Pattern 7: Blue-Green Deployment

```python
import dspy
from typing import Optional
from enum import Enum

class Environment(Enum):
    BLUE = "blue"
    GREEN = "green"

class BlueGreenDeployment:
    """Manage blue-green deployment of DSPy programs."""

    def __init__(
        self,
        blue_program: dspy.Module,
        green_program: Optional[dspy.Module] = None,
    ):
        self.blue = blue_program
        self.green = green_program or blue_program
        self.active = Environment.BLUE

    def switch_environment(self):
        """Switch active environment."""
        self.active = Environment.GREEN if self.active == Environment.BLUE else Environment.BLUE
        print(f"Switched to {self.active.value} environment")

    def rollback(self):
        """Rollback to previous environment."""
        self.switch_environment()
        print("Rolled back to previous version")

    def update_inactive(self, new_program: dspy.Module):
        """Update inactive environment with new program."""
        if self.active == Environment.BLUE:
            self.green = new_program
            print("Updated GREEN environment (inactive)")
        else:
            self.blue = new_program
            print("Updated BLUE environment (inactive)")

    def predict(self, **kwargs):
        """Route to active environment."""
        active_program = self.blue if self.active == Environment.BLUE else self.green
        return active_program(**kwargs)

    def health_check(self) -> bool:
        """Check health of active environment."""
        try:
            test_result = self.predict(question="Health check")
            return test_result is not None
        except Exception as e:
            print(f"Health check failed: {e}")
            return False

# Usage
# Current production model
blue_program = dspy.ChainOfThought("question -> answer")

# Create blue-green deployment
deployment = BlueGreenDeployment(blue_program=blue_program)

# Serve traffic from BLUE
result = deployment.predict(question="What is DSPy?")

# Deploy new version to GREEN (inactive)
new_program = dspy.ChainOfThought("question -> answer")
# ... load optimized parameters ...
deployment.update_inactive(new_program)

# Test GREEN environment
# ... run smoke tests ...

# Switch traffic to GREEN
deployment.switch_environment()

# If issues detected, rollback to BLUE
if not deployment.health_check():
    deployment.rollback()
```

**When to use**:
- Zero-downtime deployments
- Easy rollback requirements
- Testing in production-like environment
- Risk-averse deployments

**Benefits**:
- Instant rollback capability
- Test new version with real traffic
- No downtime during deployment
- Safe production updates

### Pattern 8: Comprehensive Production Setup

```python
import dspy
import modal
from datetime import datetime
import json

app = modal.App("dspy-production-complete")

# Production image with all dependencies
image = modal.Image.debian_slim().pip_install(
    "dspy-ai",
    "openai",
    "redis",
    "prometheus-client",
    "structlog",
)

# Persistent volumes
cache_volume = modal.Volume.from_name("dspy-cache", create_if_missing=True)
model_volume = modal.Volume.from_name("dspy-models", create_if_missing=True)

@app.cls(
    image=image,
    secrets=[
        modal.Secret.from_name("openai-api-key"),
        modal.Secret.from_name("redis-url"),
    ],
    volumes={
        "/cache": cache_volume,
        "/models": model_volume,
    },
    container_idle_timeout=300,  # Keep warm for 5 minutes
    allow_concurrent_inputs=10,  # Handle multiple requests
)
class ProductionDSPyService:
    """Production-ready DSPy service with all features."""

    def __init__(self):
        """Initialize service components."""
        import os
        import redis

        # Initialize DSPy
        self.lm = dspy.LM(
            "openai/gpt-4o-mini",
            api_key=os.environ["OPENAI_API_KEY"],
        )
        dspy.configure(lm=self.lm)

        # Load program
        self.program = self._load_program()

        # Initialize Redis
        self.redis_client = redis.from_url(os.environ["REDIS_URL"])

        # Circuit breaker
        self.failure_count = 0
        self.circuit_open = False

    def _load_program(self):
        """Load program from volume or create new."""
        from pathlib import Path

        program_path = Path("/models/optimized_program.json")
        if program_path.exists():
            program = dspy.ChainOfThought("question -> answer")
            program.load(str(program_path))
            print("Loaded optimized program")
        else:
            program = dspy.ChainOfThought("question -> answer")
            print("Created new program")

        return program

    def _get_cache(self, key: str):
        """Get from Redis cache."""
        try:
            cached = self.redis_client.get(f"dspy:{key}")
            return json.loads(cached) if cached else None
        except Exception as e:
            print(f"Cache read error: {e}")
            return None

    def _set_cache(self, key: str, value: dict, ttl: int = 3600):
        """Set Redis cache with TTL."""
        try:
            self.redis_client.setex(
                f"dspy:{key}",
                ttl,
                json.dumps(value),
            )
        except Exception as e:
            print(f"Cache write error: {e}")

    @modal.method()
    def predict(self, question: str) -> dict:
        """Make prediction with full production features."""
        request_id = datetime.utcnow().isoformat()

        # Check circuit breaker
        if self.circuit_open:
            return {
                "error": "Service temporarily unavailable",
                "request_id": request_id,
            }

        # Try cache
        cached_result = self._get_cache(question)
        if cached_result:
            return {
                **cached_result,
                "cached": True,
                "request_id": request_id,
            }

        # Execute prediction
        try:
            start_time = datetime.now()
            result = self.program(question=question)
            duration = (datetime.now() - start_time).total_seconds()

            # Reset failure count on success
            self.failure_count = 0

            response = {
                "answer": result.answer,
                "reasoning": getattr(result, "reasoning", None),
                "duration_seconds": duration,
                "cached": False,
                "request_id": request_id,
            }

            # Cache result
            self._set_cache(question, response)

            # Log metrics
            print(json.dumps({
                "event": "prediction_success",
                "duration": duration,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            }))

            return response

        except Exception as e:
            self.failure_count += 1

            # Open circuit if too many failures
            if self.failure_count >= 5:
                self.circuit_open = True

            # Log error
            print(json.dumps({
                "event": "prediction_error",
                "error": str(e),
                "failure_count": self.failure_count,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            }))

            return {
                "error": "Prediction failed",
                "request_id": request_id,
            }

    @modal.method()
    def health_check(self) -> dict:
        """Service health check."""
        return {
            "status": "healthy" if not self.circuit_open else "degraded",
            "failure_count": self.failure_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

@app.function(schedule=modal.Period(hours=1))
def reset_circuit_breaker():
    """Periodically reset circuit breaker."""
    service = ProductionDSPyService()
    service.circuit_open = False
    service.failure_count = 0
    print(f"Circuit breaker reset at {datetime.utcnow().isoformat()}")

# Deploy: modal deploy dspy_production.py
```

**Features**:
- Redis caching
- Circuit breaker
- Persistent volumes
- Health checks
- Structured logging
- Error handling
- Warm containers
- Concurrent requests

---

## Quick Reference

### Production Deployment Checklist

```
Infrastructure:
✅ Choose deployment strategy (serverless/containers)
✅ Configure auto-scaling
✅ Set up health checks
✅ Configure SSL/TLS

Reliability:
✅ Implement error handling
✅ Add retry logic
✅ Configure circuit breakers
✅ Set appropriate timeouts

Performance:
✅ Add caching layer
✅ Configure connection pooling
✅ Enable request batching
✅ Optimize batch sizes

Observability:
✅ Set up structured logging
✅ Export Prometheus metrics
✅ Configure alerts
✅ Track costs

Security:
✅ Secure API keys
✅ Implement rate limiting
✅ Validate inputs
✅ Filter outputs
```

### Cost Optimization Strategies

| Strategy | Savings | Complexity | Use When |
|----------|---------|------------|----------|
| Redis caching | 60-90% | Low | Repeated queries |
| Request batching | 30-50% | Medium | High volume |
| Smaller models | 80-95% | Low | Simple tasks |
| Prompt optimization | 20-40% | High | Any production use |
| Modal L40S GPU | 50-70% vs H100 | Low | Custom models |

### Modal Deployment Commands

```bash
# Deploy application
modal deploy dspy_production.py

# View logs
modal app logs dspy-production

# Stop application
modal app stop dspy-production

# Monitor usage
modal app list

# Update secret
modal secret create openai-api-key OPENAI_API_KEY=sk-...
```

---

## Anti-Patterns

❌ **No caching**: Wasteful costs, slow responses
```python
# Bad - Every request hits LM API
def predict(question):
    return program(question=question)
```
✅ Add caching layer:
```python
# Good
def predict(question):
    cached = get_cache(question)
    if cached:
        return cached
    result = program(question=question)
    set_cache(question, result)
    return result
```

❌ **No error handling**: Cascading failures
```python
# Bad
def predict(question):
    return program(question=question)  # What if LM API fails?
```
✅ Handle errors gracefully:
```python
# Good
def predict(question):
    try:
        return program(question=question)
    except Exception as e:
        log_error(e)
        return fallback_response
```

❌ **No monitoring**: Flying blind
```python
# Bad - Can't track costs, errors, or performance
```
✅ Track metrics:
```python
# Good
prediction_counter.inc()
with prediction_duration.time():
    result = program(question=question)
lm_cost.inc(calculate_cost(result))
```

❌ **Deploying untested versions**: Production incidents
```python
# Bad - Direct deploy to production
modal deploy new_model.py
```
✅ Use A/B testing or blue-green:
```python
# Good
# Deploy to inactive environment
# Run smoke tests
# Gradually increase traffic
# Monitor metrics
# Rollback if needed
```

---

## Related Skills

- `dspy-testing.md` - Testing DSPy programs before production
- `dspy-debugging.md` - Debugging production issues
- `dspy-evaluation.md` - Evaluating production performance
- `modal-functions-basics.md` - Modal deployment fundamentals
- `redis-caching.md` - Redis caching patterns
- `prometheus-metrics.md` - Metrics and monitoring

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
