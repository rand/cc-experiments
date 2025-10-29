#!/usr/bin/env python3
"""
Flask + Sentry Integration Example

Complete production-ready Flask application with comprehensive Sentry error tracking.

Features:
- Automatic exception capture
- User context tracking
- Custom error fingerprinting
- PII scrubbing
- Performance monitoring
- Release tracking
- Breadcrumbs
- Custom context enrichment

Usage:
    export SENTRY_DSN="https://..."
    export FLASK_ENV=production
    python flask-sentry.py
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, request, jsonify, g
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def init_sentry(app):
    """Initialize Sentry with comprehensive configuration."""

    # Logging integration
    logging_integration = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Capture errors as events
    )

    sentry_sdk.init(
        dsn=app.config.get('SENTRY_DSN'),
        environment=app.config.get('ENVIRONMENT', 'development'),
        release=app.config.get('RELEASE', 'unknown'),

        # Integrations
        integrations=[
            FlaskIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
            logging_integration,
        ],

        # Performance monitoring
        traces_sample_rate=get_traces_sample_rate(app.config.get('ENVIRONMENT')),
        profiles_sample_rate=0.1,

        # Privacy
        send_default_pii=False,
        request_bodies='never',

        # Hooks
        before_send=before_send_handler,
        before_breadcrumb=before_breadcrumb_handler,

        # Ignoring
        ignore_errors=[
            KeyboardInterrupt,
            SystemExit,
            BrokenPipeError,
            ConnectionResetError,
        ],

        # Advanced
        max_breadcrumbs=50,
        attach_stacktrace=True,
        shutdown_timeout=2,
    )

    # Set global tags
    sentry_sdk.set_tag("service", "flask-api")
    sentry_sdk.set_tag("datacenter", app.config.get('DATACENTER', 'unknown'))


def get_traces_sample_rate(environment):
    """Get sample rate based on environment."""
    rates = {
        'production': 0.05,   # 5%
        'staging': 0.5,       # 50%
        'development': 1.0    # 100%
    }
    return rates.get(environment, 0.1)


def before_send_handler(event, hint):
    """Scrub sensitive data before sending to Sentry."""

    # Remove cookies
    if 'request' in event:
        if 'cookies' in event['request']:
            event['request']['cookies'] = {}

        # Remove sensitive headers
        if 'headers' in event['request']:
            sensitive_headers = [
                'Authorization',
                'Cookie',
                'X-API-Key',
                'X-Auth-Token'
            ]
            for header in sensitive_headers:
                event['request']['headers'].pop(header, None)

        # Scrub query parameters
        if 'query_string' in event['request']:
            from urllib.parse import parse_qs, urlencode
            parsed = parse_qs(event['request']['query_string'])

            sensitive_params = ['token', 'api_key', 'password', 'secret']
            for param in sensitive_params:
                if param in parsed:
                    parsed[param] = ['[Filtered]']

            event['request']['query_string'] = urlencode(parsed, doseq=True)

    # Remove local variables from stack frames
    if 'exception' in event:
        for exception in event['exception'].get('values', []):
            if 'stacktrace' in exception:
                for frame in exception['stacktrace'].get('frames', []):
                    if 'vars' in frame:
                        # Keep only non-sensitive variables
                        filtered_vars = {}
                        for key, value in frame['vars'].items():
                            if not any(sensitive in key.lower() for sensitive in ['password', 'token', 'secret', 'key']):
                                filtered_vars[key] = value
                        frame['vars'] = filtered_vars

    # Sample common exceptions more aggressively
    if 'exception' in event:
        exc_type = event['exception']['values'][0].get('type', '')

        # Sample connection errors at 10%
        if exc_type in ['ConnectionError', 'TimeoutError']:
            import random
            if random.random() > 0.1:
                return None

    return event


def before_breadcrumb_handler(crumb, hint):
    """Filter or modify breadcrumbs before recording."""

    # Don't log SQL queries with sensitive data
    if crumb.get('category') == 'query':
        message = crumb.get('message', '').lower()
        if any(keyword in message for keyword in ['password', 'secret', 'token']):
            return None

    # Limit console breadcrumbs
    if crumb.get('category') == 'console':
        if crumb.get('level') == 'debug':
            return None

    return crumb


# Create Flask app
app = Flask(__name__)

# Configuration
app.config.update(
    SENTRY_DSN=os.getenv('SENTRY_DSN'),
    ENVIRONMENT=os.getenv('FLASK_ENV', 'development'),
    RELEASE=os.getenv('RELEASE', '1.0.0'),
    DATACENTER=os.getenv('DATACENTER', 'local'),
)

# Initialize Sentry
init_sentry(app)


@app.before_request
def before_request():
    """Add context before each request."""

    # Track request ID
    request_id = request.headers.get('X-Request-ID', 'unknown')
    sentry_sdk.set_tag("request_id", request_id)

    # User context (if authenticated)
    user_id = request.headers.get('X-User-ID')
    if user_id:
        sentry_sdk.set_user({
            "id": user_id,
            "ip_address": request.remote_addr,
        })

    # Request context
    sentry_sdk.set_context("request_info", {
        "url": request.url,
        "method": request.method,
        "endpoint": request.endpoint,
        "referrer": request.referrer,
        "user_agent": request.user_agent.string,
    })

    # Breadcrumb for request start
    sentry_sdk.add_breadcrumb(
        category='request',
        message=f'{request.method} {request.path}',
        level='info'
    )

    # Store request start time
    g.request_start_time = datetime.now()


@app.after_request
def after_request(response):
    """Add context after request completes."""

    # Calculate request duration
    if hasattr(g, 'request_start_time'):
        duration = (datetime.now() - g.request_start_time).total_seconds()
        sentry_sdk.set_tag("request_duration", f"{duration:.3f}s")

    # Breadcrumb for response
    sentry_sdk.add_breadcrumb(
        category='response',
        message=f'Status: {response.status_code}',
        level='info' if response.status_code < 400 else 'warning',
        data={
            'status_code': response.status_code,
            'content_length': response.content_length,
        }
    )

    return response


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all exceptions and send to Sentry."""

    # Capture exception with custom context
    with sentry_sdk.push_scope() as scope:
        # Add error-specific context
        scope.set_context("error_info", {
            "type": type(e).__name__,
            "message": str(e),
            "endpoint": request.endpoint,
        })

        # Custom fingerprinting for better grouping
        if isinstance(e, ConnectionError):
            scope.set_fingerprint(['connection-error', request.endpoint])
        elif isinstance(e, TimeoutError):
            scope.set_fingerprint(['timeout-error', request.endpoint])
        else:
            scope.set_fingerprint(['{{ default }}'])

        # Capture exception
        sentry_sdk.capture_exception(e)

    # Return error response
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500


# API Routes

@app.route('/')
def index():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "flask-api",
        "environment": app.config['ENVIRONMENT']
    })


@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    """Get user by ID (demo endpoint)."""

    # Add user context
    sentry_sdk.set_user({"id": str(user_id)})

    # Simulate user lookup
    sentry_sdk.add_breadcrumb(
        category='database',
        message=f'Looking up user {user_id}',
        level='info'
    )

    # Simulate error for testing
    if user_id == 999:
        raise ValueError(f"User not found: {user_id}")

    return jsonify({
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    })


@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create order (demo endpoint)."""

    data = request.get_json()

    # Add order context
    sentry_sdk.set_context("order", {
        "items_count": len(data.get('items', [])),
        "total": data.get('total', 0),
    })

    # Breadcrumb for order creation
    sentry_sdk.add_breadcrumb(
        category='business',
        message='Creating order',
        level='info',
        data=data
    )

    # Simulate order processing
    if data.get('total', 0) <= 0:
        raise ValueError("Order total must be positive")

    # Simulate external API call
    sentry_sdk.add_breadcrumb(
        category='http',
        message='Calling payment API',
        level='info'
    )

    return jsonify({
        "order_id": "ORD-12345",
        "status": "created"
    }), 201


@app.route('/api/test-error')
def test_error():
    """Trigger test error for verification."""

    # Send test error with full context
    sentry_sdk.set_tag("test", "true")

    try:
        raise RuntimeError("Test error from Flask API")
    except Exception as e:
        # Capture and re-raise
        sentry_sdk.capture_exception(e)
        raise


@app.route('/api/test-performance')
def test_performance():
    """Test performance monitoring."""

    import time

    with sentry_sdk.start_span(op="business_logic", description="process_data"):
        time.sleep(0.1)

        with sentry_sdk.start_span(op="database", description="query_users"):
            time.sleep(0.05)

        with sentry_sdk.start_span(op="external", description="call_api"):
            time.sleep(0.15)

    return jsonify({"status": "completed"})


if __name__ == '__main__':
    # Verify Sentry DSN is configured
    if not app.config.get('SENTRY_DSN'):
        print("ERROR: SENTRY_DSN environment variable not set", file=sys.stderr)
        sys.exit(1)

    print(f"Starting Flask API with Sentry error tracking")
    print(f"Environment: {app.config['ENVIRONMENT']}")
    print(f"Release: {app.config['RELEASE']}")

    app.run(host='0.0.0.0', port=5000, debug=False)
