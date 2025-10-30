"""
Production QA Server

FastAPI server with Modal deployment, caching, monitoring, and production features.
"""

import dspy
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# FastAPI
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Production features
import modal

# ============================================================================
# CONFIGURATION
# ============================================================================

# Modal setup
stub = modal.Stub("production-qa")

# Cache volume for model storage
cache_vol = modal.SharedVolume().persist("qa-cache")

# Image with dependencies
image = (
    modal.Image.debian_slim()
    .pip_install(
        "dspy-ai",
        "fastapi",
        "pydantic",
        "redis",
        "prometheus-client",
        "python-json-logger"
    )
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# MODELS
# ============================================================================

class QuestionRequest(BaseModel):
    """Request model for questions."""

    question: str = Field(..., min_length=1, max_length=1000, description="Question to answer")
    variant: Optional[str] = Field(default="a", description="A/B test variant (a/b)")
    user_id: Optional[str] = Field(default=None, description="User ID for tracking")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class AnswerResponse(BaseModel):
    """Response model for answers."""

    answer: str
    confidence: str
    sources: Optional[str] = None
    request_id: str
    latency_ms: float
    cache_hit: bool
    model_version: str
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    uptime_seconds: float
    requests_total: int
    error_rate: float


class StatsResponse(BaseModel):
    """Statistics response."""

    requests_total: int
    success_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    cache_hit_rate: float


# ============================================================================
# QA PIPELINE
# ============================================================================

class QAPipeline(dspy.Module):
    """Production QA pipeline with RAG."""

    def __init__(self, k: int = 5):
        """Initialize QA pipeline.

        Args:
            k: Number of passages to retrieve
        """
        super().__init__()
        self.retrieve = dspy.Retrieve(k=k)
        self.generate = dspy.ChainOfThought("context, question -> answer, confidence")

    def forward(self, question: str) -> dspy.Prediction:
        """Process question.

        Args:
            question: User question

        Returns:
            Answer with confidence
        """
        # Retrieve context
        retrieval = self.retrieve(question)
        context = "\n".join(retrieval.passages)

        # Generate answer
        result = self.generate(context=context, question=question)

        # Assertions
        dspy.Assert(len(result.answer) > 0, "Answer cannot be empty")
        dspy.Suggest(
            len(result.answer) > 20,
            "Answer should be detailed",
            target_module=self.generate
        )

        # Add sources
        result.sources = "\n".join(retrieval.passages[:3])

        return result


# ============================================================================
# METRICS COLLECTOR
# ============================================================================

@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    request_id: str
    timestamp: datetime
    latency_ms: float
    success: bool
    cache_hit: bool
    error: Optional[str] = None


class MetricsCollector:
    """Simple metrics collector."""

    def __init__(self):
        self.metrics = []
        self.requests_total = 0
        self.errors_total = 0

    def record(self, metrics: RequestMetrics):
        """Record request metrics."""
        self.metrics.append(metrics)
        self.requests_total += 1
        if not metrics.success:
            self.errors_total += 1

        # Keep only last 1000
        if len(self.metrics) > 1000:
            self.metrics = self.metrics[-1000:]

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        if not self.metrics:
            return {
                "requests_total": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "cache_hit_rate": 0.0
            }

        recent = self.metrics[-100:]  # Last 100 requests
        successes = sum(1 for m in recent if m.success)
        latencies = [m.latency_ms for m in recent]
        cache_hits = sum(1 for m in recent if m.cache_hit)

        latencies.sort()

        return {
            "requests_total": self.requests_total,
            "success_rate": successes / len(recent),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "p50_latency_ms": latencies[len(latencies) // 2],
            "p95_latency_ms": latencies[int(len(latencies) * 0.95)],
            "p99_latency_ms": latencies[int(len(latencies) * 0.99)],
            "cache_hit_rate": cache_hits / len(recent)
        }


# ============================================================================
# SIMPLE CACHE
# ============================================================================

class SimpleCache:
    """Simple in-memory cache with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get from cache."""
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        """Set in cache."""
        expiry = time.time() + self.ttl
        self.cache[key] = (value, expiry)

        # Evict if too large
        if len(self.cache) > 1000:
            oldest = min(self.cache.items(), key=lambda x: x[1][1])
            del self.cache[oldest[0]]


# ============================================================================
# FASTAPI APP
# ============================================================================

# Global state
qa_pipeline: Optional[QAPipeline] = None
metrics_collector = MetricsCollector()
cache = SimpleCache(ttl_seconds=3600)
start_time = time.time()

# Create app
app = FastAPI(
    title="Production QA API",
    description="Production-ready question answering with DSPy",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    global qa_pipeline

    logger.info("Initializing QA system...")

    # Configure DSPy
    lm = dspy.OpenAI(model="gpt-3.5-turbo", max_tokens=500)
    dspy.settings.configure(lm=lm)

    # Load or create pipeline
    try:
        qa_pipeline = QAPipeline()
        # Try to load optimized model
        # qa_pipeline.load("models/qa_optimized.json")
        logger.info("✓ QA pipeline initialized")
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        raise


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest, req: Request):
    """Answer a question.

    Args:
        request: Question request
        req: FastAPI request object

    Returns:
        Answer with metadata

    Example:
        ```bash
        curl -X POST http://localhost:8000/ask \
          -H "Content-Type: application/json" \
          -d '{"question": "What is Python?"}'
        ```
    """
    import hashlib
    import json

    request_id = hashlib.md5(
        f"{time.time()}{request.question}".encode()
    ).hexdigest()[:8]

    start = time.time()

    try:
        # Check cache
        cache_key = hashlib.md5(request.question.encode()).hexdigest()
        cached = cache.get(cache_key)

        if cached:
            latency_ms = (time.time() - start) * 1000
            logger.info(f"[{request_id}] Cache hit (latency: {latency_ms:.2f}ms)")

            # Record metrics
            metrics_collector.record(RequestMetrics(
                request_id=request_id,
                timestamp=datetime.now(),
                latency_ms=latency_ms,
                success=True,
                cache_hit=True
            ))

            return AnswerResponse(
                answer=cached["answer"],
                confidence=cached["confidence"],
                sources=cached.get("sources"),
                request_id=request_id,
                latency_ms=latency_ms,
                cache_hit=True,
                model_version="1.0.0",
                timestamp=datetime.now().isoformat()
            )

        # Process question
        logger.info(f"[{request_id}] Processing: {request.question[:50]}...")

        result = qa_pipeline(question=request.question)

        latency_ms = (time.time() - start) * 1000

        # Cache result
        cache.set(cache_key, {
            "answer": result.answer,
            "confidence": result.confidence,
            "sources": result.sources
        })

        # Record metrics
        metrics_collector.record(RequestMetrics(
            request_id=request_id,
            timestamp=datetime.now(),
            latency_ms=latency_ms,
            success=True,
            cache_hit=False
        ))

        logger.info(f"[{request_id}] Success (latency: {latency_ms:.2f}ms)")

        return AnswerResponse(
            answer=result.answer,
            confidence=result.confidence,
            sources=result.sources,
            request_id=request_id,
            latency_ms=latency_ms,
            cache_hit=False,
            model_version="1.0.0",
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        latency_ms = (time.time() - start) * 1000

        # Record error
        metrics_collector.record(RequestMetrics(
            request_id=request_id,
            timestamp=datetime.now(),
            latency_ms=latency_ms,
            success=False,
            cache_hit=False,
            error=str(e)
        ))

        logger.error(f"[{request_id}] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.

    Returns:
        Health status
    """
    uptime = time.time() - start_time
    stats = metrics_collector.get_stats()

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime_seconds=uptime,
        requests_total=stats["requests_total"],
        error_rate=1.0 - stats["success_rate"]
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get system statistics.

    Returns:
        Aggregated statistics
    """
    stats = metrics_collector.get_stats()

    return StatsResponse(**stats)


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint.

    Returns:
        Prometheus-formatted metrics
    """
    stats = metrics_collector.get_stats()

    metrics_text = f"""# HELP qa_requests_total Total requests
# TYPE qa_requests_total counter
qa_requests_total {stats['requests_total']}

# HELP qa_success_rate Success rate
# TYPE qa_success_rate gauge
qa_success_rate {stats['success_rate']}

# HELP qa_latency_seconds Request latency
# TYPE qa_latency_seconds summary
qa_latency_seconds{{quantile="0.5"}} {stats['p50_latency_ms'] / 1000}
qa_latency_seconds{{quantile="0.95"}} {stats['p95_latency_ms'] / 1000}
qa_latency_seconds{{quantile="0.99"}} {stats['p99_latency_ms'] / 1000}

# HELP qa_cache_hit_rate Cache hit rate
# TYPE qa_cache_hit_rate gauge
qa_cache_hit_rate {stats['cache_hit_rate']}
"""

    return metrics_text


# ============================================================================
# MODAL DEPLOYMENT
# ============================================================================

@stub.function(
    image=image,
    shared_volumes={"/cache": cache_vol},
    cpu=2.0,
    memory=4096,
    allow_concurrent_inputs=10,
    keep_warm=1
)
@modal.asgi_app()
def modal_app():
    """Modal deployment endpoint."""
    return app


# ============================================================================
# LOCAL DEVELOPMENT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("Starting Production QA Server...")
    print("Docs: http://localhost:8000/docs")
    print("Health: http://localhost:8000/health")
    print("Metrics: http://localhost:8000/metrics")

    uvicorn.run(app, host="0.0.0.0", port=8000)
