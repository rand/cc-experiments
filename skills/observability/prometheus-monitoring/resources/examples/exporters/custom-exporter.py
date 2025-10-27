#!/usr/bin/env python3
"""
Custom Prometheus Exporter (Python)

Production-ready custom exporter example using prometheus_client.
Exposes application and system metrics.

Usage:
    pip install prometheus-client psutil
    python custom-exporter.py

Metrics available at: http://localhost:8080/metrics
"""

from prometheus_client import start_http_server, Gauge, Counter, Histogram, Info
import time
import random
import psutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# System metrics
cpu_usage = Gauge('custom_cpu_usage_percent', 'CPU usage percentage')
cpu_cores = Gauge('custom_cpu_cores', 'Number of CPU cores')

memory_usage_bytes = Gauge('custom_memory_usage_bytes', 'Memory usage in bytes')
memory_total_bytes = Gauge('custom_memory_total_bytes', 'Total memory in bytes')
memory_available_bytes = Gauge('custom_memory_available_bytes', 'Available memory in bytes')

disk_usage_percent = Gauge(
    'custom_disk_usage_percent',
    'Disk usage percentage',
    ['mount_point', 'device']
)

network_bytes_sent = Counter(
    'custom_network_bytes_sent_total',
    'Total network bytes sent',
    ['interface']
)

network_bytes_received = Counter(
    'custom_network_bytes_received_total',
    'Total network bytes received',
    ['interface']
)

# Application metrics
app_requests_total = Counter(
    'custom_app_requests_total',
    'Total application requests',
    ['endpoint', 'method', 'status']
)

app_request_duration_seconds = Histogram(
    'custom_app_request_duration_seconds',
    'Application request duration',
    ['endpoint', 'method'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

app_errors_total = Counter(
    'custom_app_errors_total',
    'Total application errors',
    ['error_type']
)

app_active_connections = Gauge(
    'custom_app_active_connections',
    'Number of active connections'
)

app_queue_size = Gauge(
    'custom_app_queue_size',
    'Queue size',
    ['queue_name']
)

# Business metrics
orders_total = Counter(
    'custom_orders_total',
    'Total orders processed',
    ['product_category', 'status']
)

order_value_dollars = Histogram(
    'custom_order_value_dollars',
    'Order value in dollars',
    buckets=[10, 25, 50, 100, 250, 500, 1000, 5000]
)

revenue_total_dollars = Counter(
    'custom_revenue_total_dollars',
    'Total revenue in dollars',
    ['product_category']
)

# Build info
build_info = Info('custom_app_build', 'Application build information')
build_info.info({
    'version': '1.2.3',
    'commit': 'abc123',
    'build_date': '2025-10-27'
})


def collect_system_metrics():
    """Collect system metrics using psutil."""
    try:
        # CPU
        cpu_usage.set(psutil.cpu_percent(interval=1))
        cpu_cores.set(psutil.cpu_count())

        # Memory
        mem = psutil.virtual_memory()
        memory_usage_bytes.set(mem.used)
        memory_total_bytes.set(mem.total)
        memory_available_bytes.set(mem.available)

        # Disk
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage_percent.labels(
                    mount_point=partition.mountpoint,
                    device=partition.device
                ).set(usage.percent)
            except PermissionError:
                pass

        # Network
        net_io = psutil.net_io_counters(pernic=True)
        for interface, counters in net_io.items():
            # These are cumulative counters
            network_bytes_sent.labels(interface=interface)._value._value = counters.bytes_sent
            network_bytes_received.labels(interface=interface)._value._value = counters.bytes_recv

        logger.debug("System metrics collected successfully")

    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}")


def simulate_application_metrics():
    """Simulate application metrics for demonstration."""
    try:
        # Simulate HTTP requests
        endpoints = ['/api/users', '/api/orders', '/api/products']
        methods = ['GET', 'POST', 'PUT']
        statuses = ['200', '201', '400', '404', '500']

        endpoint = random.choice(endpoints)
        method = random.choice(methods)
        status = random.choice(statuses)

        # Record request
        app_requests_total.labels(
            endpoint=endpoint,
            method=method,
            status=status
        ).inc()

        # Record duration
        duration = random.uniform(0.01, 2.0)
        app_request_duration_seconds.labels(
            endpoint=endpoint,
            method=method
        ).observe(duration)

        # Simulate errors (10% chance)
        if random.random() < 0.1:
            error_types = ['database_error', 'validation_error', 'timeout']
            app_errors_total.labels(error_type=random.choice(error_types)).inc()

        # Update gauges
        app_active_connections.set(random.randint(10, 500))
        app_queue_size.labels(queue_name='tasks').set(random.randint(0, 100))
        app_queue_size.labels(queue_name='emails').set(random.randint(0, 50))

        logger.debug("Application metrics simulated successfully")

    except Exception as e:
        logger.error(f"Error simulating application metrics: {e}")


def simulate_business_metrics():
    """Simulate business metrics for demonstration."""
    try:
        # Simulate orders (20% chance)
        if random.random() < 0.2:
            categories = ['electronics', 'clothing', 'books', 'home']
            statuses = ['completed', 'pending', 'cancelled']

            category = random.choice(categories)
            status = random.choice(statuses)
            value = random.uniform(10, 5000)

            orders_total.labels(
                product_category=category,
                status=status
            ).inc()

            order_value_dollars.observe(value)

            if status == 'completed':
                revenue_total_dollars.labels(product_category=category).inc(value)

        logger.debug("Business metrics simulated successfully")

    except Exception as e:
        logger.error(f"Error simulating business metrics: {e}")


def main():
    """Main exporter loop."""
    port = 8080

    # Start HTTP server for metrics endpoint
    start_http_server(port)
    logger.info(f"Custom exporter started on port {port}")
    logger.info(f"Metrics available at http://localhost:{port}/metrics")

    # Collect metrics periodically
    while True:
        try:
            collect_system_metrics()
            simulate_application_metrics()
            simulate_business_metrics()
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Exporter stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)


if __name__ == '__main__':
    main()
