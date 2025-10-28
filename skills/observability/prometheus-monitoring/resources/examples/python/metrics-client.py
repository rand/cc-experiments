#!/usr/bin/env python3
"""
Application Instrumentation Example

Demonstrates how to instrument a Python application with Prometheus metrics.
Shows patterns for HTTP servers, background workers, and business logic.

Usage:
    pip install prometheus-client flask
    python metrics-client.py

Metrics available at: http://localhost:8000/metrics
API available at: http://localhost:8000/api/*
"""

from prometheus_client import Counter, Histogram, Gauge, Summary, Info
from prometheus_client import start_http_server, generate_latest
from flask import Flask, request, Response, jsonify
import time
import random
import functools
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_request_size_bytes = Summary(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint']
)

http_response_size_bytes = Summary(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint', 'status']
)

http_active_requests = Gauge(
    'http_active_requests',
    'Number of active HTTP requests',
    ['method', 'endpoint']
)

# Application-specific metrics
user_logins_total = Counter(
    'user_logins_total',
    'Total user logins',
    ['status']  # success, failed
)

database_queries_total = Counter(
    'database_queries_total',
    'Total database queries',
    ['operation', 'table']
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits'
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses'
)

background_jobs_total = Counter(
    'background_jobs_total',
    'Total background jobs',
    ['job_type', 'status']
)

background_job_duration_seconds = Histogram(
    'background_job_duration_seconds',
    'Background job duration',
    ['job_type'],
    buckets=[1, 5, 10, 30, 60, 300, 600]
)

# Business metrics
orders_processed_total = Counter(
    'orders_processed_total',
    'Total orders processed',
    ['product_category', 'status']
)

order_value_dollars = Histogram(
    'order_value_dollars',
    'Order value in dollars',
    buckets=[10, 25, 50, 100, 250, 500, 1000, 5000]
)

active_users = Gauge(
    'active_users',
    'Number of currently active users'
)

# Build info
build_info = Info('app_build', 'Application build information')
build_info.info({
    'version': '1.2.3',
    'commit': 'abc123def456',
    'build_date': '2025-10-27',
    'python_version': '3.11'
})


def track_request(func):
    """Decorator to track HTTP request metrics."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        method = request.method
        endpoint = request.endpoint or request.path

        # Track active requests
        http_active_requests.labels(method=method, endpoint=endpoint).inc()

        # Track request size
        request_size = request.content_length or 0
        http_request_size_bytes.labels(method=method, endpoint=endpoint).observe(request_size)

        # Track request duration
        start_time = time.time()
        try:
            response = func(*args, **kwargs)
            status = getattr(response, 'status_code', 200)
            return response
        except Exception as e:
            status = 500
            logger.error(f"Request failed: {e}")
            raise
        finally:
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=str(status)
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # Track response size (if available)
            if isinstance(response, Response):
                response_size = len(response.get_data())
                http_response_size_bytes.labels(
                    method=method,
                    endpoint=endpoint,
                    status=str(status)
                ).observe(response_size)

            http_active_requests.labels(method=method, endpoint=endpoint).dec()

    return wrapper


def simulate_database_query(operation: str, table: str) -> dict:
    """Simulate database query with metrics."""
    start_time = time.time()

    try:
        # Simulate query
        time.sleep(random.uniform(0.001, 0.05))

        # Record metrics
        database_queries_total.labels(operation=operation, table=table).inc()

        duration = time.time() - start_time
        database_query_duration_seconds.labels(operation=operation, table=table).observe(duration)

        return {'success': True, 'rows': random.randint(1, 100)}

    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise


def check_cache(key: str) -> bool:
    """Check cache with metrics."""
    # Simulate cache lookup (80% hit rate)
    if random.random() < 0.8:
        cache_hits_total.inc()
        return True
    else:
        cache_misses_total.inc()
        return False


# API Routes

@app.route('/api/users', methods=['GET'])
@track_request
def get_users():
    """Get users endpoint."""
    # Check cache
    if check_cache('users'):
        users = [{'id': 1, 'name': 'Cached User'}]
    else:
        # Query database
        result = simulate_database_query('SELECT', 'users')
        users = [{'id': 1, 'name': 'User'}]

    return jsonify({'users': users})


@app.route('/api/users/<int:user_id>', methods=['GET'])
@track_request
def get_user(user_id):
    """Get specific user."""
    result = simulate_database_query('SELECT', 'users')
    return jsonify({'user': {'id': user_id, 'name': f'User {user_id}'}})


@app.route('/api/login', methods=['POST'])
@track_request
def login():
    """User login endpoint."""
    # Simulate authentication (90% success rate)
    if random.random() < 0.9:
        user_logins_total.labels(status='success').inc()
        return jsonify({'token': 'abc123'}), 200
    else:
        user_logins_total.labels(status='failed').inc()
        return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/api/orders', methods=['POST'])
@track_request
def create_order():
    """Create order endpoint."""
    categories = ['electronics', 'clothing', 'books', 'home']
    category = random.choice(categories)
    value = random.uniform(10, 5000)

    # Process order
    result = simulate_database_query('INSERT', 'orders')

    # Record business metrics
    orders_processed_total.labels(product_category=category, status='completed').inc()
    order_value_dollars.observe(value)

    return jsonify({
        'order_id': random.randint(1000, 9999),
        'category': category,
        'value': value
    }), 201


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint (not tracked)."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), mimetype='text/plain')


def background_worker():
    """Simulate background worker."""
    job_types = ['email', 'report', 'cleanup']

    while True:
        job_type = random.choice(job_types)
        start_time = time.time()

        try:
            # Simulate job
            time.sleep(random.uniform(1, 10))

            # Record metrics
            background_jobs_total.labels(job_type=job_type, status='success').inc()

            duration = time.time() - start_time
            background_job_duration_seconds.labels(job_type=job_type).observe(duration)

        except Exception as e:
            background_jobs_total.labels(job_type=job_type, status='failed').inc()
            logger.error(f"Background job failed: {e}")

        time.sleep(5)


def update_gauges():
    """Update gauge metrics periodically."""
    while True:
        # Simulate active users
        active_users.set(random.randint(100, 1000))
        time.sleep(10)


if __name__ == '__main__':
    # Start background workers in threads
    import threading

    threading.Thread(target=background_worker, daemon=True).start()
    threading.Thread(target=update_gauges, daemon=True).start()

    logger.info("Application started")
    logger.info("API available at http://localhost:8000/api/*")
    logger.info("Metrics available at http://localhost:8000/metrics")

    # Run Flask app
    app.run(host='0.0.0.0', port=8000, debug=False)
