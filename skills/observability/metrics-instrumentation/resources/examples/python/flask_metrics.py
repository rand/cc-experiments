"""
Flask Application with Prometheus Metrics

Demonstrates comprehensive Prometheus instrumentation for a Flask web application
including HTTP metrics, custom business metrics, and best practices.

Usage:
    pip install flask prometheus-client
    python flask_metrics.py

Metrics available at: http://localhost:8080/metrics
"""

from flask import Flask, request, jsonify
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
)
from functools import wraps
import time
import random
import psutil
import os

app = Flask(__name__)

# Create custom registry (optional, useful for testing)
# registry = CollectorRegistry()

# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

http_request_size_bytes = Summary(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint']
)

http_response_size_bytes = Summary(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint']
)

# ============================================================================
# Application Metrics
# ============================================================================

app_info = Info(
    'app',
    'Application information'
)
app_info.info({
    'version': '1.0.0',
    'environment': os.environ.get('ENV', 'development'),
    'python_version': os.sys.version.split()[0]
})

# ============================================================================
# Business Metrics
# ============================================================================

user_login_total = Counter(
    'user_login_total',
    'Total user logins',
    ['status']  # success, failure
)

user_sessions_active = Gauge(
    'user_sessions_active',
    'Number of active user sessions'
)

order_value_dollars = Histogram(
    'order_value_dollars',
    'Order value in dollars',
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000]
)

orders_total = Counter(
    'orders_total',
    'Total orders processed',
    ['product_category', 'payment_method']
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

cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result']  # operation: get/set/delete, result: hit/miss
)

# ============================================================================
# System Metrics (Custom)
# ============================================================================

process_cpu_usage_ratio = Gauge(
    'process_cpu_usage_ratio',
    'Process CPU usage ratio (0-1)'
)

process_memory_bytes = Gauge(
    'process_memory_bytes',
    'Process memory usage in bytes'
)

process_open_fds = Gauge(
    'process_open_fds',
    'Number of open file descriptors'
)

# ============================================================================
# Middleware & Decorators
# ============================================================================

@app.before_request
def before_request():
    """Track request start time and increment in-progress gauge."""
    request.start_time = time.time()

    # Get normalized endpoint
    endpoint = request.endpoint or 'unknown'

    # Increment in-progress gauge
    http_requests_in_progress.labels(
        method=request.method,
        endpoint=endpoint
    ).inc()

    # Track request size
    request_size = request.content_length or 0
    http_request_size_bytes.labels(
        method=request.method,
        endpoint=endpoint
    ).observe(request_size)


@app.after_request
def after_request(response):
    """Track request metrics after response."""
    # Calculate duration
    duration = time.time() - request.start_time

    # Get normalized endpoint
    endpoint = request.endpoint or 'unknown'

    # Decrement in-progress gauge
    http_requests_in_progress.labels(
        method=request.method,
        endpoint=endpoint
    ).dec()

    # Record metrics
    http_requests_total.labels(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code
    ).inc()

    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=endpoint
    ).observe(duration)

    # Track response size
    response_size = response.content_length or len(response.get_data())
    http_response_size_bytes.labels(
        method=request.method,
        endpoint=endpoint
    ).observe(response_size)

    return response


def track_db_query(operation: str, table: str):
    """Decorator to track database query metrics."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()

            try:
                result = func(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                duration = time.time() - start

                database_queries_total.labels(
                    operation=operation,
                    table=table
                ).inc()

                database_query_duration_seconds.labels(
                    operation=operation,
                    table=table
                ).observe(duration)

        return wrapper
    return decorator


# ============================================================================
# Background System Metrics Collector
# ============================================================================

def update_system_metrics():
    """Update system metrics (call periodically)."""
    process = psutil.Process()

    # CPU usage
    cpu_percent = process.cpu_percent(interval=None) / 100.0
    process_cpu_usage_ratio.set(cpu_percent)

    # Memory usage
    memory_info = process.memory_info()
    process_memory_bytes.set(memory_info.rss)

    # Open file descriptors
    try:
        num_fds = process.num_fds()
        process_open_fds.set(num_fds)
    except AttributeError:
        # num_fds() not available on Windows
        pass


# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/')
def index():
    """Homepage."""
    return jsonify({
        'name': 'Flask Metrics Demo',
        'version': '1.0.0',
        'metrics_url': '/metrics'
    })


@app.route('/api/users', methods=['GET'])
def get_users():
    """Get users (simulated)."""
    # Simulate database query
    @track_db_query('select', 'users')
    def query_users():
        time.sleep(random.uniform(0.01, 0.05))
        return [
            {'id': 1, 'name': 'Alice'},
            {'id': 2, 'name': 'Bob'}
        ]

    # Check cache (simulated)
    cache_hit = random.random() > 0.3
    cache_operations_total.labels(
        operation='get',
        result='hit' if cache_hit else 'miss'
    ).inc()

    if cache_hit:
        users = [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]
    else:
        users = query_users()
        cache_operations_total.labels(operation='set', result='success').inc()

    return jsonify({'users': users})


@app.route('/api/login', methods=['POST'])
def login():
    """User login (simulated)."""
    # Simulate login logic
    success = random.random() > 0.1  # 90% success rate

    user_login_total.labels(
        status='success' if success else 'failure'
    ).inc()

    if success:
        # Increment active sessions
        user_sessions_active.inc()
        return jsonify({'status': 'success', 'token': 'fake-token'}), 200
    else:
        return jsonify({'status': 'failure', 'error': 'Invalid credentials'}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    """User logout (simulated)."""
    # Decrement active sessions
    user_sessions_active.dec()
    return jsonify({'status': 'success'}), 200


@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create order (simulated)."""
    # Simulate order data
    order_value = random.uniform(10, 500)
    product_category = random.choice(['electronics', 'books', 'clothing'])
    payment_method = random.choice(['credit_card', 'paypal', 'bank_transfer'])

    # Track business metrics
    order_value_dollars.observe(order_value)
    orders_total.labels(
        product_category=product_category,
        payment_method=payment_method
    ).inc()

    # Simulate database insert
    @track_db_query('insert', 'orders')
    def insert_order():
        time.sleep(random.uniform(0.02, 0.08))

    insert_order()

    return jsonify({
        'order_id': random.randint(1000, 9999),
        'value': order_value,
        'category': product_category,
        'payment_method': payment_method
    }), 201


@app.route('/api/slow', methods=['GET'])
def slow_endpoint():
    """Intentionally slow endpoint for testing."""
    time.sleep(random.uniform(1.0, 3.0))
    return jsonify({'status': 'slow response'})


@app.route('/api/error', methods=['GET'])
def error_endpoint():
    """Intentionally failing endpoint for testing."""
    if random.random() > 0.5:
        raise Exception("Simulated error")
    return jsonify({'status': 'ok'})


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


# ============================================================================
# Metrics Endpoint
# ============================================================================

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint."""
    # Update system metrics before serving
    update_system_metrics()

    # Generate metrics output
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    print("Starting Flask application with Prometheus metrics...")
    print("Metrics endpoint: http://localhost:8080/metrics")
    print("API endpoints:")
    print("  - GET  /api/users")
    print("  - POST /api/login")
    print("  - POST /api/logout")
    print("  - POST /api/orders")
    print("  - GET  /api/slow")
    print("  - GET  /api/error")
    print("  - GET  /health")

    app.run(host='0.0.0.0', port=8080, debug=False)
