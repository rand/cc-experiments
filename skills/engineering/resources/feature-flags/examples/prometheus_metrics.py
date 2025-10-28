"""
Prometheus Metrics for Feature Flags

Production-ready Prometheus metrics collection and export for feature flags.
Tracks evaluations, latency, variations, and errors.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
from typing import Dict, Optional, Any
import time
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FlagMetrics:
    """
    Prometheus metrics for feature flags

    Tracks:
    - Flag evaluations (total, per flag, per variation)
    - Evaluation latency
    - Cache hit/miss rates
    - Errors and failures
    - Active flags count
    - Flag metadata

    Usage:
        metrics = FlagMetrics()

        # Track evaluation
        with metrics.track_evaluation('new-feature'):
            result = evaluate_flag('new-feature', user)

        # Track variation
        metrics.record_variation('new-feature', 'enabled')

        # Track error
        metrics.record_error('new-feature', 'timeout')
    """

    def __init__(self, namespace: str = "feature_flags"):
        """
        Initialize metrics

        Args:
            namespace: Prometheus namespace for metrics
        """
        self.namespace = namespace

        # Counter: Total flag evaluations
        self.evaluations_total = Counter(
            f'{namespace}_evaluations_total',
            'Total number of feature flag evaluations',
            ['flag_key', 'variation', 'environment']
        )

        # Counter: Evaluation errors
        self.evaluation_errors_total = Counter(
            f'{namespace}_evaluation_errors_total',
            'Total number of evaluation errors',
            ['flag_key', 'error_type', 'environment']
        )

        # Histogram: Evaluation duration
        self.evaluation_duration_seconds = Histogram(
            f'{namespace}_evaluation_duration_seconds',
            'Time spent evaluating feature flags',
            ['flag_key', 'environment'],
            buckets=[.001, .0025, .005, .01, .025, .05, .1, .25, .5, 1.0]
        )

        # Counter: Cache hits/misses
        self.cache_hits_total = Counter(
            f'{namespace}_cache_hits_total',
            'Total number of cache hits',
            ['flag_key', 'environment']
        )

        self.cache_misses_total = Counter(
            f'{namespace}_cache_misses_total',
            'Total number of cache misses',
            ['flag_key', 'environment']
        )

        # Gauge: Active flags
        self.active_flags = Gauge(
            f'{namespace}_active_flags',
            'Number of active feature flags',
            ['environment', 'flag_type']
        )

        # Gauge: Flag rollout percentage
        self.flag_rollout_percentage = Gauge(
            f'{namespace}_rollout_percentage',
            'Current rollout percentage for flag',
            ['flag_key', 'environment']
        )

        # Counter: Flag changes
        self.flag_changes_total = Counter(
            f'{namespace}_changes_total',
            'Total number of flag configuration changes',
            ['flag_key', 'change_type', 'environment']
        )

        # Histogram: Targeting rule evaluation time
        self.targeting_duration_seconds = Histogram(
            f'{namespace}_targeting_duration_seconds',
            'Time spent evaluating targeting rules',
            ['flag_key', 'environment'],
            buckets=[.0001, .0005, .001, .0025, .005, .01, .025]
        )

        # Info: SDK version
        self.sdk_info = Info(
            f'{namespace}_sdk_info',
            'Feature flag SDK information'
        )

        # Counter: Provider API calls
        self.provider_api_calls_total = Counter(
            f'{namespace}_provider_api_calls_total',
            'Total API calls to flag provider',
            ['provider', 'operation', 'status']
        )

        # Gauge: Stale flags
        self.stale_flags = Gauge(
            f'{namespace}_stale_flags',
            'Number of stale feature flags',
            ['environment']
        )

        logger.info(f"Initialized FlagMetrics with namespace: {namespace}")

    def track_evaluation(self, flag_key: str, environment: str = "production"):
        """
        Context manager to track flag evaluation

        Usage:
            with metrics.track_evaluation('my-flag'):
                result = evaluate_flag()
        """
        class EvaluationTracker:
            def __init__(self, metrics, flag_key, environment):
                self.metrics = metrics
                self.flag_key = flag_key
                self.environment = environment
                self.start_time = None

            def __enter__(self):
                self.start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                self.metrics.evaluation_duration_seconds.labels(
                    flag_key=self.flag_key,
                    environment=self.environment
                ).observe(duration)

                if exc_type:
                    self.metrics.record_error(
                        self.flag_key,
                        exc_type.__name__,
                        self.environment
                    )
                return False

        return EvaluationTracker(self, flag_key, environment)

    def record_evaluation(
        self,
        flag_key: str,
        variation: str,
        environment: str = "production"
    ):
        """Record a flag evaluation"""
        self.evaluations_total.labels(
            flag_key=flag_key,
            variation=variation,
            environment=environment
        ).inc()

    def record_variation(
        self,
        flag_key: str,
        variation: str,
        environment: str = "production"
    ):
        """Record which variation was served"""
        self.record_evaluation(flag_key, variation, environment)

    def record_error(
        self,
        flag_key: str,
        error_type: str,
        environment: str = "production"
    ):
        """Record an evaluation error"""
        self.evaluation_errors_total.labels(
            flag_key=flag_key,
            error_type=error_type,
            environment=environment
        ).inc()

    def record_cache_hit(self, flag_key: str, environment: str = "production"):
        """Record cache hit"""
        self.cache_hits_total.labels(
            flag_key=flag_key,
            environment=environment
        ).inc()

    def record_cache_miss(self, flag_key: str, environment: str = "production"):
        """Record cache miss"""
        self.cache_misses_total.labels(
            flag_key=flag_key,
            environment=environment
        ).inc()

    def set_active_flags_count(
        self,
        count: int,
        environment: str = "production",
        flag_type: str = "all"
    ):
        """Set number of active flags"""
        self.active_flags.labels(
            environment=environment,
            flag_type=flag_type
        ).set(count)

    def set_rollout_percentage(
        self,
        flag_key: str,
        percentage: float,
        environment: str = "production"
    ):
        """Set current rollout percentage"""
        self.flag_rollout_percentage.labels(
            flag_key=flag_key,
            environment=environment
        ).set(percentage)

    def record_flag_change(
        self,
        flag_key: str,
        change_type: str,
        environment: str = "production"
    ):
        """Record flag configuration change"""
        self.flag_changes_total.labels(
            flag_key=flag_key,
            change_type=change_type,
            environment=environment
        ).inc()

    def track_targeting(self, flag_key: str, environment: str = "production"):
        """Track targeting rule evaluation time"""
        class TargetingTracker:
            def __init__(self, metrics, flag_key, environment):
                self.metrics = metrics
                self.flag_key = flag_key
                self.environment = environment
                self.start_time = None

            def __enter__(self):
                self.start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                self.metrics.targeting_duration_seconds.labels(
                    flag_key=self.flag_key,
                    environment=self.environment
                ).observe(duration)
                return False

        return TargetingTracker(self, flag_key, environment)

    def set_sdk_info(self, version: str, provider: str):
        """Set SDK information"""
        self.sdk_info.info({
            'version': version,
            'provider': provider
        })

    def record_provider_api_call(
        self,
        provider: str,
        operation: str,
        status: str
    ):
        """Record API call to flag provider"""
        self.provider_api_calls_total.labels(
            provider=provider,
            operation=operation,
            status=status
        ).inc()

    def set_stale_flags_count(self, count: int, environment: str = "production"):
        """Set number of stale flags"""
        self.stale_flags.labels(environment=environment).set(count)


def instrumented(metrics: FlagMetrics, environment: str = "production"):
    """
    Decorator to automatically instrument flag evaluation functions

    Usage:
        @instrumented(metrics)
        def evaluate_flag(flag_key, user):
            # Evaluation logic
            return True
    """
    def decorator(func):
        @wraps(func)
        def wrapper(flag_key, *args, **kwargs):
            with metrics.track_evaluation(flag_key, environment):
                result = func(flag_key, *args, **kwargs)

                # Record variation
                variation = str(result)
                metrics.record_variation(flag_key, variation, environment)

                return result
        return wrapper
    return decorator


class MetricsExporter:
    """
    Export metrics in Prometheus format

    Usage:
        exporter = MetricsExporter(metrics)

        # Flask
        @app.route('/metrics')
        def metrics():
            return exporter.export()

        # FastAPI
        @app.get('/metrics')
        def metrics():
            return Response(exporter.export(), media_type='text/plain')
    """

    def __init__(self, metrics: Optional[FlagMetrics] = None):
        """
        Initialize exporter

        Args:
            metrics: FlagMetrics instance (optional, uses default registry)
        """
        self.metrics = metrics

    def export(self) -> bytes:
        """Export metrics in Prometheus format"""
        return generate_latest(REGISTRY)


# Example integration with feature flag client
class InstrumentedFlagClient:
    """
    Feature flag client with Prometheus instrumentation

    Wraps any flag client and adds metrics automatically.

    Usage:
        client = InstrumentedFlagClient(base_client, metrics)

        # Metrics tracked automatically
        enabled = client.is_enabled('new-feature', user)
    """

    def __init__(
        self,
        client: Any,
        metrics: FlagMetrics,
        environment: str = "production"
    ):
        """
        Initialize instrumented client

        Args:
            client: Base flag client
            metrics: Metrics instance
            environment: Environment name
        """
        self.client = client
        self.metrics = metrics
        self.environment = environment

    def is_enabled(
        self,
        flag_key: str,
        user: Any,
        default: bool = False
    ) -> bool:
        """Check if flag is enabled with metrics"""
        with self.metrics.track_evaluation(flag_key, self.environment):
            try:
                result = self.client.is_enabled(flag_key, user, default)
                variation = "enabled" if result else "disabled"
                self.metrics.record_variation(flag_key, variation, self.environment)
                return result
            except Exception as e:
                self.metrics.record_error(flag_key, type(e).__name__, self.environment)
                raise

    def get_variation(
        self,
        flag_key: str,
        user: Any,
        default: Any
    ) -> Any:
        """Get flag variation with metrics"""
        with self.metrics.track_evaluation(flag_key, self.environment):
            try:
                result = self.client.get_variation(flag_key, user, default)
                self.metrics.record_variation(flag_key, str(result), self.environment)
                return result
            except Exception as e:
                self.metrics.record_error(flag_key, type(e).__name__, self.environment)
                raise


# Example Flask integration
def create_flask_app():
    """Example Flask app with metrics endpoint"""
    from flask import Flask, Response

    app = Flask(__name__)
    metrics = FlagMetrics()
    exporter = MetricsExporter(metrics)

    @app.route('/metrics')
    def metrics_endpoint():
        return Response(exporter.export(), mimetype='text/plain')

    @app.route('/feature/<flag_key>')
    def check_feature(flag_key):
        # Simulate flag check
        with metrics.track_evaluation(flag_key):
            enabled = True  # Actual evaluation
            metrics.record_variation(flag_key, "enabled" if enabled else "disabled")

        return {'enabled': enabled}

    return app


# Example FastAPI integration
def create_fastapi_app():
    """Example FastAPI app with metrics endpoint"""
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    app = FastAPI()
    metrics = FlagMetrics()
    exporter = MetricsExporter(metrics)

    @app.get('/metrics', response_class=PlainTextResponse)
    async def metrics_endpoint():
        return exporter.export()

    @app.get('/feature/{flag_key}')
    async def check_feature(flag_key: str):
        with metrics.track_evaluation(flag_key):
            enabled = True  # Actual evaluation
            metrics.record_variation(flag_key, "enabled" if enabled else "disabled")

        return {'enabled': enabled}

    return app


# Grafana Dashboard JSON (example queries)
GRAFANA_QUERIES = {
    "total_evaluations": """
        rate(feature_flags_evaluations_total[5m])
    """,
    "evaluation_latency_p95": """
        histogram_quantile(0.95,
            rate(feature_flags_evaluation_duration_seconds_bucket[5m])
        )
    """,
    "error_rate": """
        rate(feature_flags_evaluation_errors_total[5m])
        /
        rate(feature_flags_evaluations_total[5m])
    """,
    "cache_hit_rate": """
        rate(feature_flags_cache_hits_total[5m])
        /
        (rate(feature_flags_cache_hits_total[5m]) + rate(feature_flags_cache_misses_total[5m]))
    """,
    "active_flags_by_type": """
        feature_flags_active_flags
    """,
    "top_evaluated_flags": """
        topk(10, rate(feature_flags_evaluations_total[5m]))
    """,
    "flag_rollout_status": """
        feature_flags_rollout_percentage
    """
}


if __name__ == '__main__':
    # Example usage
    metrics = FlagMetrics()

    # Set SDK info
    metrics.set_sdk_info(version="1.0.0", provider="launchdarkly")

    # Simulate flag evaluations
    for i in range(100):
        flag_key = f"feature-{i % 5}"
        variation = "enabled" if i % 2 == 0 else "disabled"

        with metrics.track_evaluation(flag_key):
            time.sleep(0.001)  # Simulate work
            metrics.record_variation(flag_key, variation)

        if i % 10 == 0:
            metrics.record_cache_hit(flag_key)
        else:
            metrics.record_cache_miss(flag_key)

    # Set active flags
    metrics.set_active_flags_count(5, flag_type="release")
    metrics.set_active_flags_count(2, flag_type="experiment")

    # Set rollout percentages
    for i in range(5):
        metrics.set_rollout_percentage(f"feature-{i}", i * 25.0)

    # Record some errors
    metrics.record_error("feature-0", "timeout")
    metrics.record_error("feature-1", "network_error")

    # Export metrics
    exporter = MetricsExporter(metrics)
    print(exporter.export().decode())
