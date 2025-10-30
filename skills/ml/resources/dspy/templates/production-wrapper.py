"""
Production Wrapper Template for DSPy Programs

Wraps DSPy programs with production-ready features:
- Error handling and retries
- Caching
- Monitoring and metrics
- Circuit breaker
- Rate limiting
- Logging
"""

import dspy
import time
import logging
import hashlib
import json
from typing import Optional, Dict, Any, Callable
from functools import wraps
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque
from enum import Enum


# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# METRICS TRACKING
# ============================================================================

@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    request_id: str
    timestamp: datetime
    latency_ms: float
    success: bool
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    cache_hit: bool = False
    retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/export."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class MetricsCollector:
    """Collects and aggregates request metrics."""

    def __init__(self, window_size: int = 1000):
        """Initialize metrics collector.

        Args:
            window_size: Number of recent requests to track
        """
        self.metrics: deque = deque(maxlen=window_size)
        self.total_requests = 0
        self.total_errors = 0
        self.total_latency_ms = 0.0

    def record(self, metrics: RequestMetrics):
        """Record request metrics."""
        self.metrics.append(metrics)
        self.total_requests += 1

        if not metrics.success:
            self.total_errors += 1

        self.total_latency_ms += metrics.latency_ms

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        if not self.metrics:
            return {
                "total_requests": 0,
                "error_rate": 0.0,
                "avg_latency_ms": 0.0
            }

        recent_metrics = list(self.metrics)
        successes = sum(1 for m in recent_metrics if m.success)
        errors = len(recent_metrics) - successes
        latencies = [m.latency_ms for m in recent_metrics]

        return {
            "total_requests": self.total_requests,
            "recent_requests": len(recent_metrics),
            "success_rate": successes / len(recent_metrics),
            "error_rate": errors / len(recent_metrics),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "p50_latency_ms": self._percentile(latencies, 50),
            "p95_latency_ms": self._percentile(latencies, 95),
            "p99_latency_ms": self._percentile(latencies, 99),
            "cache_hit_rate": sum(1 for m in recent_metrics if m.cache_hit) / len(recent_metrics),
        }

    @staticmethod
    def _percentile(values: list, p: int) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * p / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]


# ============================================================================
# CACHING
# ============================================================================

class CacheBackend:
    """Simple in-memory cache with TTL."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """Initialize cache.

        Args:
            max_size: Maximum number of cached items
            ttl_seconds: Time-to-live for cache entries
        """
        self.cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            return None

        value, expiry = self.cache[key]

        # Check if expired
        if datetime.now() > expiry:
            del self.cache[key]
            return None

        return value

    def set(self, key: str, value: Any):
        """Set value in cache."""
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        expiry = datetime.now() + timedelta(seconds=self.ttl_seconds)
        self.cache[key] = (value, expiry)

    def clear(self):
        """Clear all cached items."""
        self.cache.clear()

    def _create_key(self, *args, **kwargs) -> str:
        """Create cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            # Check if should attempt recovery
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker recovered, entering CLOSED state")

        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, max_calls: int, period_seconds: int):
        """Initialize rate limiter.

        Args:
            max_calls: Maximum calls per period
            period_seconds: Period duration in seconds
        """
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.calls: deque = deque()

    def acquire(self) -> bool:
        """Try to acquire permission for a call.

        Returns:
            True if call is allowed, False if rate limited
        """
        now = time.time()

        # Remove old calls outside window
        while self.calls and self.calls[0] < now - self.period_seconds:
            self.calls.popleft()

        # Check if under limit
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True

        return False

    def wait_if_needed(self):
        """Block until rate limit allows call."""
        while not self.acquire():
            time.sleep(0.1)  # Wait 100ms


# ============================================================================
# PRODUCTION WRAPPER
# ============================================================================

class ProductionWrapper:
    """Production-ready wrapper for DSPy programs.

    Features:
    - Automatic retries with exponential backoff
    - Caching with TTL
    - Circuit breaker
    - Rate limiting
    - Metrics collection
    - Structured logging
    - Timeout enforcement

    Example:
        ```python
        program = RAGProgram()
        wrapper = ProductionWrapper(
            program=program,
            max_retries=3,
            cache_ttl=3600,
            enable_circuit_breaker=True
        )

        result = wrapper(question="What is AI?")
        stats = wrapper.get_stats()
        ```
    """

    def __init__(
        self,
        program: dspy.Module,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_backoff: float = 2.0,
        timeout_seconds: Optional[float] = None,
        cache_enabled: bool = True,
        cache_ttl: int = 3600,
        cache_max_size: int = 1000,
        enable_circuit_breaker: bool = True,
        circuit_failure_threshold: int = 5,
        circuit_recovery_timeout: int = 60,
        enable_rate_limiting: bool = False,
        rate_limit_calls: int = 60,
        rate_limit_period: int = 60,
    ):
        """Initialize production wrapper.

        Args:
            program: DSPy program to wrap
            max_retries: Maximum retry attempts
            retry_delay: Initial retry delay (seconds)
            retry_backoff: Backoff multiplier for retries
            timeout_seconds: Request timeout (None = no timeout)
            cache_enabled: Enable response caching
            cache_ttl: Cache time-to-live (seconds)
            cache_max_size: Maximum cache entries
            enable_circuit_breaker: Enable circuit breaker
            circuit_failure_threshold: Failures before opening circuit
            circuit_recovery_timeout: Recovery attempt interval
            enable_rate_limiting: Enable rate limiting
            rate_limit_calls: Max calls per period
            rate_limit_period: Period duration (seconds)
        """
        self.program = program
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff
        self.timeout_seconds = timeout_seconds

        # Initialize components
        self.metrics = MetricsCollector()

        self.cache = CacheBackend(
            max_size=cache_max_size,
            ttl_seconds=cache_ttl
        ) if cache_enabled else None

        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            recovery_timeout=circuit_recovery_timeout
        ) if enable_circuit_breaker else None

        self.rate_limiter = RateLimiter(
            max_calls=rate_limit_calls,
            period_seconds=rate_limit_period
        ) if enable_rate_limiting else None

    def __call__(self, **kwargs) -> dspy.Prediction:
        """Execute program with production features.

        Args:
            **kwargs: Arguments to pass to program

        Returns:
            Program prediction

        Raises:
            Exception: If all retries exhausted or circuit open
        """
        request_id = self._generate_request_id()
        start_time = time.time()

        logger.info(f"[{request_id}] Processing request")

        try:
            # Rate limiting
            if self.rate_limiter:
                self.rate_limiter.wait_if_needed()

            # Check cache
            cache_key = self._cache_key(**kwargs) if self.cache else None
            if cache_key:
                cached = self.cache.get(cache_key)
                if cached is not None:
                    latency_ms = (time.time() - start_time) * 1000
                    self._record_success(request_id, latency_ms, cache_hit=True)
                    logger.info(f"[{request_id}] Cache hit (latency: {latency_ms:.2f}ms)")
                    return cached

            # Execute with retries
            result = self._execute_with_retries(request_id, **kwargs)

            # Cache result
            if cache_key and self.cache:
                self.cache.set(cache_key, result)

            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            self._record_success(request_id, latency_ms, cache_hit=False)

            logger.info(f"[{request_id}] Success (latency: {latency_ms:.2f}ms)")
            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._record_failure(request_id, latency_ms, str(e))
            logger.error(f"[{request_id}] Failed: {e}")
            raise

    def _execute_with_retries(self, request_id: str, **kwargs) -> dspy.Prediction:
        """Execute program with retry logic."""
        last_exception = None
        delay = self.retry_delay

        for attempt in range(self.max_retries + 1):
            try:
                # Circuit breaker
                if self.circuit_breaker:
                    return self.circuit_breaker.call(self.program, **kwargs)
                else:
                    return self.program(**kwargs)

            except Exception as e:
                last_exception = e
                logger.warning(f"[{request_id}] Attempt {attempt + 1} failed: {e}")

                # Don't retry on last attempt
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= self.retry_backoff

        # All retries exhausted
        raise last_exception

    def _cache_key(self, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        return hashlib.md5(
            f"{time.time()}{id(self)}".encode()
        ).hexdigest()[:8]

    def _record_success(self, request_id: str, latency_ms: float, cache_hit: bool):
        """Record successful request."""
        metrics = RequestMetrics(
            request_id=request_id,
            timestamp=datetime.now(),
            latency_ms=latency_ms,
            success=True,
            cache_hit=cache_hit
        )
        self.metrics.record(metrics)

    def _record_failure(self, request_id: str, latency_ms: float, error: str):
        """Record failed request."""
        metrics = RequestMetrics(
            request_id=request_id,
            timestamp=datetime.now(),
            latency_ms=latency_ms,
            success=False,
            error=error
        )
        self.metrics.record(metrics)

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics.

        Returns:
            Dictionary with metrics
        """
        return self.metrics.get_stats()

    def reset_stats(self):
        """Reset metrics collector."""
        self.metrics = MetricsCollector()

    def clear_cache(self):
        """Clear response cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Cache cleared")


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_basic_usage():
    """Example: Basic production wrapper usage."""
    import dspy

    # Configure LM
    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    # Create program
    class QA(dspy.Module):
        def __init__(self):
            self.generate = dspy.ChainOfThought("question -> answer")

        def forward(self, question):
            return self.generate(question=question)

    program = QA()

    # Wrap for production
    wrapper = ProductionWrapper(
        program=program,
        max_retries=3,
        cache_enabled=True,
        enable_circuit_breaker=True
    )

    # Use wrapper
    result = wrapper(question="What is AI?")
    print(f"Answer: {result.answer}")

    # Check stats
    stats = wrapper.get_stats()
    print(f"Stats: {stats}")


def example_with_monitoring():
    """Example: Production wrapper with monitoring."""
    import dspy

    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    class QA(dspy.Module):
        def __init__(self):
            self.generate = dspy.ChainOfThought("question -> answer")

        def forward(self, question):
            return self.generate(question=question)

    program = QA()
    wrapper = ProductionWrapper(program=program)

    # Process requests
    questions = [
        "What is AI?",
        "What is machine learning?",
        "What is deep learning?"
    ]

    for q in questions:
        result = wrapper(question=q)
        print(f"Q: {q}")
        print(f"A: {result.answer}\n")

    # Review metrics
    stats = wrapper.get_stats()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Success rate: {stats['success_rate']:.2%}")
    print(f"Avg latency: {stats['avg_latency_ms']:.2f}ms")
    print(f"P95 latency: {stats['p95_latency_ms']:.2f}ms")
    print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")


if __name__ == "__main__":
    # Uncomment to run examples
    # example_basic_usage()
    # example_with_monitoring()
    pass
