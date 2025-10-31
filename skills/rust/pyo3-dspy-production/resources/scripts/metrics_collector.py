#!/usr/bin/env python3
"""
Prometheus Metrics Collector for DSPy Services

Collect and export Prometheus metrics for DSPy services with HTTP endpoint.
Provides real-time monitoring of LM calls, latency, tokens, costs, and cache performance.

Usage:
    python metrics_collector.py start --port 9090
    python metrics_collector.py record lm_call --duration 1.5 --tokens 150
    python metrics_collector.py export --format prometheus
    python metrics_collector.py query --metric lm_calls_total
    python metrics_collector.py dashboard --refresh 5
"""

import os
import sys
import json
import time
import signal
import threading
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import defaultdict


class MetricType(str, Enum):
    """Prometheus metric types."""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """Single metric value with timestamp."""
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class HistogramBuckets:
    """Histogram buckets for latency tracking."""
    buckets: Dict[float, int] = field(default_factory=lambda: {
        0.01: 0, 0.05: 0, 0.1: 0, 0.5: 0,
        1.0: 0, 2.0: 0, 5.0: 0, 10.0: 0, 30.0: 0
    })
    count: int = 0
    sum: float = 0.0

    def observe(self, value: float):
        """Record a histogram observation."""
        self.count += 1
        self.sum += value
        for bucket, _ in sorted(self.buckets.items()):
            if value <= bucket:
                self.buckets[bucket] += 1


class MetricsStore:
    """Thread-safe metrics storage."""

    def __init__(self):
        self._counters: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: Dict[str, Dict[str, HistogramBuckets]] = defaultdict(lambda: defaultdict(HistogramBuckets))
        self._gauges: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._lock = threading.RLock()
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def register_metric(self, name: str, metric_type: str, help_text: str, label_names: List[str] = None):
        """Register a new metric."""
        with self._lock:
            self._metadata[name] = {
                "type": metric_type,
                "help": help_text,
                "label_names": label_names or []
            }

    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        with self._lock:
            label_key = self._label_key(labels or {})
            self._counters[name][label_key] += value

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric."""
        with self._lock:
            label_key = self._label_key(labels or {})
            self._gauges[name][label_key] = value

    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram observation."""
        with self._lock:
            label_key = self._label_key(labels or {})
            if name not in self._histograms or label_key not in self._histograms[name]:
                self._histograms[name][label_key] = HistogramBuckets()
            self._histograms[name][label_key].observe(value)

    def get_counter(self, name: str, labels: Dict[str, str] = None) -> float:
        """Get counter value."""
        with self._lock:
            label_key = self._label_key(labels or {})
            return self._counters[name].get(label_key, 0.0)

    def get_gauge(self, name: str, labels: Dict[str, str] = None) -> Optional[float]:
        """Get gauge value."""
        with self._lock:
            label_key = self._label_key(labels or {})
            return self._gauges[name].get(label_key)

    def get_histogram(self, name: str, labels: Dict[str, str] = None) -> Optional[HistogramBuckets]:
        """Get histogram buckets."""
        with self._lock:
            label_key = self._label_key(labels or {})
            return self._histograms[name].get(label_key)

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus format."""
        with self._lock:
            lines = []

            # Counters
            for name, label_values in self._counters.items():
                metadata = self._metadata.get(name, {})
                if metadata.get("help"):
                    lines.append(f"# HELP {name} {metadata['help']}")
                lines.append(f"# TYPE {name} counter")

                for label_key, value in label_values.items():
                    if label_key:
                        lines.append(f"{name}{{{label_key}}} {value}")
                    else:
                        lines.append(f"{name} {value}")

            # Gauges
            for name, label_values in self._gauges.items():
                metadata = self._metadata.get(name, {})
                if metadata.get("help"):
                    lines.append(f"# HELP {name} {metadata['help']}")
                lines.append(f"# TYPE {name} gauge")

                for label_key, value in label_values.items():
                    if label_key:
                        lines.append(f"{name}{{{label_key}}} {value}")
                    else:
                        lines.append(f"{name} {value}")

            # Histograms
            for name, label_values in self._histograms.items():
                metadata = self._metadata.get(name, {})
                if metadata.get("help"):
                    lines.append(f"# HELP {name} {metadata['help']}")
                lines.append(f"# TYPE {name} histogram")

                for label_key, buckets in label_values.items():
                    base_labels = label_key if label_key else ""

                    # Bucket counts
                    for le, count in sorted(buckets.buckets.items()):
                        bucket_labels = f'{base_labels},le="{le}"' if base_labels else f'le="{le}"'
                        lines.append(f"{name}_bucket{{{bucket_labels}}} {count}")

                    # +Inf bucket
                    inf_labels = f'{base_labels},le="+Inf"' if base_labels else 'le="+Inf"'
                    lines.append(f"{name}_bucket{{{inf_labels}}} {buckets.count}")

                    # Sum and count
                    if base_labels:
                        lines.append(f"{name}_sum{{{base_labels}}} {buckets.sum}")
                        lines.append(f"{name}_count{{{base_labels}}} {buckets.count}")
                    else:
                        lines.append(f"{name}_sum {buckets.sum}")
                        lines.append(f"{name}_count {buckets.count}")

            return "\n".join(lines) + "\n"

    def export_json(self) -> Dict[str, Any]:
        """Export all metrics as JSON."""
        with self._lock:
            return {
                "counters": {
                    name: dict(values) for name, values in self._counters.items()
                },
                "gauges": {
                    name: dict(values) for name, values in self._gauges.items()
                },
                "histograms": {
                    name: {
                        label_key: {
                            "count": hist.count,
                            "sum": hist.sum,
                            "buckets": hist.buckets
                        }
                        for label_key, hist in label_values.items()
                    }
                    for name, label_values in self._histograms.items()
                }
            }

    @staticmethod
    def _label_key(labels: Dict[str, str]) -> str:
        """Generate label key from dict."""
        if not labels:
            return ""
        sorted_labels = sorted(labels.items())
        return ",".join(f'{k}="{v}"' for k, v in sorted_labels)


class DSPyMetrics:
    """DSPy-specific metrics collector."""

    def __init__(self, store: MetricsStore):
        self.store = store
        self._register_metrics()

    def _register_metrics(self):
        """Register DSPy metrics."""
        # Counters
        self.store.register_metric(
            "dspy_lm_calls_total",
            MetricType.COUNTER,
            "Total number of language model calls",
            ["model", "status"]
        )

        self.store.register_metric(
            "dspy_cache_hits_total",
            MetricType.COUNTER,
            "Total cache hits by level",
            ["level"]
        )

        self.store.register_metric(
            "dspy_cache_misses_total",
            MetricType.COUNTER,
            "Total cache misses",
            ["model"]
        )

        self.store.register_metric(
            "dspy_errors_total",
            MetricType.COUNTER,
            "Total errors by type",
            ["error_type", "model"]
        )

        self.store.register_metric(
            "dspy_tokens_total",
            MetricType.COUNTER,
            "Total tokens used",
            ["model", "type"]
        )

        # Histograms
        self.store.register_metric(
            "dspy_lm_latency_seconds",
            MetricType.HISTOGRAM,
            "Language model call latency in seconds",
            ["model", "cached"]
        )

        # Gauges
        self.store.register_metric(
            "dspy_active_requests",
            MetricType.GAUGE,
            "Number of active requests",
            []
        )

        self.store.register_metric(
            "dspy_cache_size",
            MetricType.GAUGE,
            "Current cache size in bytes",
            []
        )

    def record_lm_call(self, duration: float, tokens: int, model: str = "default",
                       status: str = "success", cached: bool = False,
                       cache_level: Optional[str] = None):
        """Record a language model call."""
        # Increment call counter
        self.store.increment_counter(
            "dspy_lm_calls_total",
            labels={"model": model, "status": status}
        )

        # Record latency
        self.store.observe_histogram(
            "dspy_lm_latency_seconds",
            duration,
            labels={"model": model, "cached": str(cached).lower()}
        )

        # Record tokens
        if tokens > 0:
            self.store.increment_counter(
                "dspy_tokens_total",
                value=float(tokens),
                labels={"model": model, "type": "total"}
            )

        # Record cache metrics
        if cached and cache_level:
            self.store.increment_counter(
                "dspy_cache_hits_total",
                labels={"level": cache_level}
            )
        elif not cached:
            self.store.increment_counter(
                "dspy_cache_misses_total",
                labels={"model": model}
            )

    def record_error(self, error_type: str, model: str = "default"):
        """Record an error."""
        self.store.increment_counter(
            "dspy_errors_total",
            labels={"error_type": error_type, "model": model}
        )

    def set_active_requests(self, count: int):
        """Set active request count."""
        self.store.set_gauge("dspy_active_requests", float(count))

    def set_cache_size(self, size_bytes: int):
        """Set cache size."""
        self.store.set_gauge("dspy_cache_size", float(size_bytes))


class MetricsHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for metrics endpoint."""

    store: MetricsStore = None

    def do_GET(self):
        """Handle GET request."""
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()

            metrics_text = self.store.export_prometheus()
            self.wfile.write(metrics_text.encode())

        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class MetricsServer:
    """HTTP server for metrics."""

    def __init__(self, store: MetricsStore, port: int = 9090):
        self.store = store
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start metrics server."""
        MetricsHTTPHandler.store = self.store

        self.server = HTTPServer(("0.0.0.0", self.port), MetricsHTTPHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        print(f"Metrics server started on http://0.0.0.0:{self.port}/metrics")

    def stop(self):
        """Stop metrics server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("Metrics server stopped")

    def wait(self):
        """Wait for server to finish."""
        if self.thread:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.stop()


class Dashboard:
    """Real-time metrics dashboard."""

    def __init__(self, store: MetricsStore, refresh_interval: int = 5):
        self.store = store
        self.refresh_interval = refresh_interval

    def display(self):
        """Display real-time dashboard."""
        try:
            while True:
                self._clear_screen()
                self._print_dashboard()
                time.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            print("\n\nDashboard stopped.")

    def _clear_screen(self):
        """Clear terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')

    def _print_dashboard(self):
        """Print dashboard content."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("=" * 70)
        print(f"DSPy Metrics Dashboard - {now}")
        print("=" * 70)
        print()

        # LM Calls
        total_calls = self.store.get_counter("dspy_lm_calls_total", {"model": "default", "status": "success"})
        total_errors = self.store.get_counter("dspy_errors_total", {"error_type": "unknown", "model": "default"})
        print(f"LM Calls (Total):     {int(total_calls):,}")
        print(f"Errors (Total):       {int(total_errors):,}")
        print()

        # Cache Performance
        cache_hits_memory = self.store.get_counter("dspy_cache_hits_total", {"level": "memory"})
        cache_hits_redis = self.store.get_counter("dspy_cache_hits_total", {"level": "redis"})
        cache_misses = self.store.get_counter("dspy_cache_misses_total", {"model": "default"})
        total_cache_requests = cache_hits_memory + cache_hits_redis + cache_misses

        if total_cache_requests > 0:
            hit_rate = ((cache_hits_memory + cache_hits_redis) / total_cache_requests) * 100
        else:
            hit_rate = 0.0

        print(f"Cache Hits (Memory):  {int(cache_hits_memory):,}")
        print(f"Cache Hits (Redis):   {int(cache_hits_redis):,}")
        print(f"Cache Misses:         {int(cache_misses):,}")
        print(f"Hit Rate:             {hit_rate:.1f}%")
        print()

        # Latency
        hist = self.store.get_histogram("dspy_lm_latency_seconds", {"model": "default", "cached": "false"})
        if hist and hist.count > 0:
            avg_latency = hist.sum / hist.count
            print(f"Avg Latency:          {avg_latency:.3f}s")
            print(f"Total Requests:       {hist.count:,}")
        else:
            print(f"Avg Latency:          N/A")
        print()

        # Active requests
        active = self.store.get_gauge("dspy_active_requests")
        print(f"Active Requests:      {int(active or 0)}")
        print()

        print("=" * 70)
        print(f"Press Ctrl+C to exit | Refresh: {self.refresh_interval}s")


def cmd_start(args):
    """Start metrics server."""
    store = MetricsStore()
    metrics = DSPyMetrics(store)

    server = MetricsServer(store, port=args.port)
    server.start()

    # Register signal handler
    def signal_handler(sig, frame):
        print("\nShutting down...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"Metrics endpoints:")
    print(f"  - Prometheus: http://localhost:{args.port}/metrics")
    print(f"  - Health:     http://localhost:{args.port}/health")
    print("\nPress Ctrl+C to stop")

    server.wait()


def cmd_record(args):
    """Record a metric."""
    # Load or create store
    store_path = args.store or ".metrics_store.json"

    if os.path.exists(store_path):
        with open(store_path) as f:
            data = json.load(f)
        store = MetricsStore()
        # Restore state (simplified)
        for name, values in data.get("counters", {}).items():
            for label_key, value in values.items():
                store._counters[name][label_key] = value
    else:
        store = MetricsStore()

    metrics = DSPyMetrics(store)

    # Record based on subcommand
    if args.record_type == "lm_call":
        metrics.record_lm_call(
            duration=args.duration,
            tokens=args.tokens,
            model=args.model,
            status=args.status,
            cached=args.cached,
            cache_level=args.cache_level
        )
        print(f"✓ Recorded LM call: {args.duration}s, {args.tokens} tokens, {args.model}")

    elif args.record_type == "error":
        metrics.record_error(
            error_type=args.error_type,
            model=args.model
        )
        print(f"✓ Recorded error: {args.error_type}, {args.model}")

    # Save store
    with open(store_path, 'w') as f:
        json.dump(store.export_json(), f, indent=2)


def cmd_export(args):
    """Export metrics."""
    store_path = args.store or ".metrics_store.json"

    if not os.path.exists(store_path):
        print(f"✗ No metrics store found at {store_path}")
        sys.exit(1)

    with open(store_path) as f:
        data = json.load(f)

    store = MetricsStore()
    # Restore state (simplified)
    for name, values in data.get("counters", {}).items():
        for label_key, value in values.items():
            store._counters[name][label_key] = value

    metrics = DSPyMetrics(store)

    if args.format == "prometheus":
        print(store.export_prometheus())
    elif args.format == "json":
        print(json.dumps(store.export_json(), indent=2))


def cmd_query(args):
    """Query metrics."""
    store_path = args.store or ".metrics_store.json"

    if not os.path.exists(store_path):
        print(f"✗ No metrics store found at {store_path}")
        sys.exit(1)

    with open(store_path) as f:
        data = json.load(f)

    # Query specific metric
    if args.metric in data.get("counters", {}):
        print(f"\nCounter: {args.metric}")
        for label_key, value in data["counters"][args.metric].items():
            print(f"  {{{label_key}}} = {value}")

    elif args.metric in data.get("gauges", {}):
        print(f"\nGauge: {args.metric}")
        for label_key, value in data["gauges"][args.metric].items():
            print(f"  {{{label_key}}} = {value}")

    elif args.metric in data.get("histograms", {}):
        print(f"\nHistogram: {args.metric}")
        for label_key, hist in data["histograms"][args.metric].items():
            print(f"  {{{label_key}}}")
            print(f"    count: {hist['count']}")
            print(f"    sum:   {hist['sum']}")
            if hist['count'] > 0:
                print(f"    avg:   {hist['sum'] / hist['count']:.3f}")

    else:
        print(f"✗ Metric not found: {args.metric}")
        print("\nAvailable metrics:")
        for category in ["counters", "gauges", "histograms"]:
            if category in data:
                print(f"\n{category.upper()}:")
                for name in data[category].keys():
                    print(f"  - {name}")


def cmd_dashboard(args):
    """Start real-time dashboard."""
    store_path = args.store or ".metrics_store.json"

    if not os.path.exists(store_path):
        print(f"✗ No metrics store found at {store_path}")
        print(f"Starting with empty store...")

    store = MetricsStore()
    metrics = DSPyMetrics(store)

    dashboard = Dashboard(store, refresh_interval=args.refresh)
    dashboard.display()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Prometheus Metrics Collector for DSPy Services"
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Start command
    parser_start = subparsers.add_parser('start', help='Start metrics HTTP server')
    parser_start.add_argument('--port', type=int, default=9090, help='HTTP server port')

    # Record command
    parser_record = subparsers.add_parser('record', help='Record a metric')
    record_subparsers = parser_record.add_subparsers(dest='record_type', help='Record type')

    # Record LM call
    parser_lm = record_subparsers.add_parser('lm_call', help='Record LM call')
    parser_lm.add_argument('--duration', type=float, required=True, help='Call duration in seconds')
    parser_lm.add_argument('--tokens', type=int, required=True, help='Token count')
    parser_lm.add_argument('--model', default='default', help='Model name')
    parser_lm.add_argument('--status', default='success', help='Call status')
    parser_lm.add_argument('--cached', action='store_true', help='Was cached')
    parser_lm.add_argument('--cache-level', help='Cache level (memory/redis)')
    parser_lm.add_argument('--store', help='Metrics store path')

    # Record error
    parser_error = record_subparsers.add_parser('error', help='Record error')
    parser_error.add_argument('--error-type', required=True, help='Error type')
    parser_error.add_argument('--model', default='default', help='Model name')
    parser_error.add_argument('--store', help='Metrics store path')

    # Export command
    parser_export = subparsers.add_parser('export', help='Export metrics')
    parser_export.add_argument('--format', choices=['prometheus', 'json'], default='prometheus',
                               help='Export format')
    parser_export.add_argument('--store', help='Metrics store path')

    # Query command
    parser_query = subparsers.add_parser('query', help='Query metrics')
    parser_query.add_argument('--metric', required=True, help='Metric name')
    parser_query.add_argument('--store', help='Metrics store path')

    # Dashboard command
    parser_dashboard = subparsers.add_parser('dashboard', help='Start real-time dashboard')
    parser_dashboard.add_argument('--refresh', type=int, default=5, help='Refresh interval (seconds)')
    parser_dashboard.add_argument('--store', help='Metrics store path')

    args = parser.parse_args()

    if args.command == 'start':
        cmd_start(args)
    elif args.command == 'record':
        cmd_record(args)
    elif args.command == 'export':
        cmd_export(args)
    elif args.command == 'query':
        cmd_query(args)
    elif args.command == 'dashboard':
        cmd_dashboard(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
