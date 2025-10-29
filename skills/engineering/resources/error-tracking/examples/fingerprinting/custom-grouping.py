#!/usr/bin/env python3
"""
Custom Error Fingerprinting Examples

Demonstrates advanced error grouping strategies using custom fingerprints.

Strategies covered:
1. Group by exception type and context
2. Parameterize dynamic data (IDs, timestamps)
3. Group by business impact
4. Group by root cause
5. API endpoint-based grouping
"""

import sentry_sdk
import re


def setup_sentry_with_fingerprinting():
    """Initialize Sentry with custom fingerprinting."""

    sentry_sdk.init(
        dsn="https://...",
        before_send=apply_custom_fingerprints,
    )


def apply_custom_fingerprints(event, hint):
    """Apply custom fingerprinting logic."""

    if 'exception' in event:
        exc_values = event['exception']['values']
        if exc_values:
            exc = exc_values[0]
            exc_type = exc.get('type', '')
            exc_value = exc.get('value', '')

            # Strategy 1: Database errors by table
            if exc_type == 'DatabaseError':
                table = extract_table_name(exc_value)
                if table:
                    event['fingerprint'] = ['database-error', table]
                    return event

            # Strategy 2: API errors by endpoint and status
            if exc_type in ['APIError', 'HTTPError']:
                endpoint = extract_api_endpoint(event)
                status_code = extract_status_code(exc_value)
                if endpoint and status_code:
                    event['fingerprint'] = ['api-error', endpoint, status_code]
                    return event

            # Strategy 3: Timeout errors by operation
            if 'timeout' in exc_value.lower():
                operation = extract_operation(event)
                event['fingerprint'] = ['timeout', operation]
                return event

            # Strategy 4: Validation errors (group all together)
            if exc_type == 'ValidationError':
                event['fingerprint'] = ['validation-error']
                return event

            # Strategy 5: User not found errors (parameterize ID)
            if 'user' in exc_value.lower() and 'not found' in exc_value.lower():
                event['fingerprint'] = ['user-not-found']
                return event

            # Strategy 6: Connection errors by destination
            if exc_type in ['ConnectionError', 'ConnectionRefusedError']:
                destination = extract_connection_destination(exc_value)
                event['fingerprint'] = ['connection-error', destination]
                return event

    # Default grouping
    return event


def extract_table_name(error_message):
    """Extract database table name from error message."""
    # Example: 'relation "users" does not exist'
    match = re.search(r'relation "(\w+)"', error_message)
    if match:
        return match.group(1)

    # Example: 'Table \'orders\' doesn\'t exist'
    match = re.search(r"Table ['\"](\w+)['\"]", error_message)
    if match:
        return match.group(1)

    return 'unknown'


def extract_api_endpoint(event):
    """Extract API endpoint from request context."""
    if 'request' in event and 'url' in event['request']:
        url = event['request']['url']
        # Remove query string and extract path
        path = url.split('?')[0]
        # Normalize path (remove IDs)
        path = re.sub(r'/\d+', '/:id', path)
        return path

    return 'unknown'


def extract_status_code(error_message):
    """Extract HTTP status code from error message."""
    match = re.search(r'\b([45]\d{2})\b', error_message)
    if match:
        return match.group(1)
    return 'unknown'


def extract_operation(event):
    """Extract operation name from stack trace."""
    if 'exception' in event:
        exc = event['exception']['values'][0]
        if 'stacktrace' in exc:
            frames = exc['stacktrace'].get('frames', [])
            if frames:
                # Get first in-app frame
                for frame in reversed(frames):
                    if frame.get('in_app'):
                        return frame.get('function', 'unknown')

    return 'unknown'


def extract_connection_destination(error_message):
    """Extract connection destination from error message."""
    # Example: 'Connection refused: 192.168.1.10:5432'
    match = re.search(r'(\w+):\/\/([\w\.\-]+)', error_message)
    if match:
        return match.group(2)

    # Example: 'Failed to connect to redis-01'
    match = re.search(r'connect to ([\w\-]+)', error_message)
    if match:
        return match.group(1)

    return 'unknown'


# Example usage

def example_database_error():
    """Example: Database error that will be grouped by table."""
    sentry_sdk.set_context("database", {
        "query": "SELECT * FROM users WHERE id = 123"
    })

    try:
        # Simulate database error
        raise Exception('relation "users" does not exist')
    except Exception as e:
        sentry_sdk.capture_exception(e)
        # Fingerprint: ['database-error', 'users']


def example_api_error():
    """Example: API error grouped by endpoint and status."""
    sentry_sdk.set_context("request", {
        "url": "https://api.example.com/v1/orders/123?token=abc"
    })

    try:
        # Simulate API error
        raise Exception('API request failed with status 503')
    except Exception as e:
        sentry_sdk.capture_exception(e)
        # Fingerprint: ['api-error', '/v1/orders/:id', '503']


def example_user_not_found():
    """Example: User not found errors grouped together."""
    try:
        # All these create same issue (different user IDs)
        raise ValueError(f'User 12345 not found')
    except Exception as e:
        # Don't include user ID in fingerprint
        sentry_sdk.set_context("user", {"id": "12345"})
        sentry_sdk.capture_exception(e)
        # Fingerprint: ['user-not-found']


def example_parameterize_dynamic_data():
    """Example: Remove dynamic data from error message."""

    # BAD: Dynamic data in exception message
    # This creates separate issue for every order/timestamp
    # raise Exception(f"Order {order_id} failed at {timestamp}")

    # GOOD: Static message, dynamic data in context
    order_id = "ORD-12345"
    timestamp = "2024-01-15T10:30:00Z"

    sentry_sdk.set_context("order", {
        "id": order_id,
        "timestamp": timestamp
    })

    try:
        raise Exception("Order processing failed")
    except Exception as e:
        sentry_sdk.capture_exception(e)
        # All orders grouped under single issue


if __name__ == '__main__':
    setup_sentry_with_fingerprinting()

    # Run examples
    example_database_error()
    example_api_error()
    example_user_not_found()
    example_parameterize_dynamic_data()

    # Flush events
    sentry_sdk.flush()
