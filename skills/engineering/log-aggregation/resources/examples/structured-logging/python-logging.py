#!/usr/bin/env python3
"""
Structured Logging Example - Python with structlog

Demonstrates best practices for structured JSON logging in Python applications.

Install:
    pip install structlog

Run:
    python python-logging.py
"""

import structlog
import sys
import logging
from datetime import datetime


def configure_logging(service_name: str, version: str, environment: str):
    """
    Configure structured logging with JSON output.

    Args:
        service_name: Name of the service
        version: Service version
        environment: Deployment environment (dev/staging/production)
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if environment == "production" else logging.DEBUG
    )

    structlog.configure(
        processors=[
            # Add log level
            structlog.stdlib.add_log_level,

            # Add logger name
            structlog.stdlib.add_logger_name,

            # Add timestamp (ISO 8601 format)
            structlog.processors.TimeStamper(fmt="iso", utc=True),

            # Add context from thread-local storage
            structlog.threadlocal.merge_threadlocal,

            # Format positional args
            structlog.stdlib.PositionalArgumentsFormatter(),

            # Add stack info for exceptions
            structlog.processors.StackInfoRenderer(),

            # Format exception info
            structlog.processors.format_exc_info,

            # Decode unicode
            structlog.processors.UnicodeDecoder(),

            # Render as JSON
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Create logger with default context
    logger = structlog.get_logger()
    logger = logger.bind(
        service=service_name,
        version=version,
        environment=environment
    )

    return logger


def add_trace_context(logger, trace_id: str, span_id: str):
    """
    Add distributed tracing context to logger.

    Args:
        logger: Structured logger instance
        trace_id: Trace ID from OpenTelemetry/Jaeger
        span_id: Span ID

    Returns:
        Logger with tracing context
    """
    return logger.bind(
        trace_id=trace_id,
        span_id=span_id
    )


def log_http_request(logger, method: str, path: str, status_code: int,
                    duration_ms: float, user_id: str = None):
    """
    Log HTTP request with structured fields.

    Args:
        logger: Structured logger instance
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        user_id: Optional user ID
    """
    log_func = logger.info if status_code < 400 else logger.error

    log_func(
        "http_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        user_id=user_id,
        request_id=f"req_{datetime.utcnow().timestamp()}"
    )


def log_error(logger, error: Exception, context: dict = None):
    """
    Log error with full context and stack trace.

    Args:
        logger: Structured logger instance
        error: Exception object
        context: Additional context dictionary
    """
    logger.error(
        "error_occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {},
        exc_info=True  # Adds stack trace
    )


def log_database_query(logger, query: str, duration_ms: float,
                      rows_affected: int = None):
    """
    Log database query with performance metrics.
    NOTE: This only LOGS query info - it does not execute any database operations.

    Args:
        logger: Structured logger instance
        query: SQL query string (already executed, for logging only)
        duration_ms: Query duration in milliseconds
        rows_affected: Number of rows affected
    """
    # Truncate query string for logging (does not execute query)
    query_snippet = query[:100] if len(query) > 100 else query
    logger.info(
        "database_query",
        query=query_snippet,
        duration_ms=duration_ms,
        rows_affected=rows_affected,
        slow_query=duration_ms > 1000
    )


def example_application():
    """Example application demonstrating structured logging."""

    # Initialize logging
    logger = configure_logging(
        service_name="api-gateway",
        version="1.2.3",
        environment="production"
    )

    # Add tracing context
    logger = add_trace_context(
        logger,
        trace_id="abc123def456",
        span_id="span789"
    )

    # Application startup
    logger.info(
        "application_started",
        port=8080,
        workers=4
    )

    # Log HTTP request
    log_http_request(
        logger,
        method="GET",
        path="/api/users/123",
        status_code=200,
        duration_ms=45.3,
        user_id="user_456"
    )

    # Log database query
    log_database_query(
        logger,
        query="SELECT * FROM users WHERE id = $1",
        duration_ms=12.5,
        rows_affected=1
    )

    # Log slow query warning
    log_database_query(
        logger,
        query="SELECT * FROM orders JOIN order_items",
        duration_ms=1250.0,
        rows_affected=5000
    )

    # Log business event
    logger.info(
        "user_action",
        action="login",
        user_id="user_456",
        ip="192.168.1.1",
        success=True
    )

    # Log error with context
    try:
        result = 1 / 0
    except Exception as e:
        log_error(
            logger,
            error=e,
            context={
                "operation": "calculate_total",
                "user_id": "user_456"
            }
        )

    # Log with additional context using bind()
    order_logger = logger.bind(
        order_id="order_789",
        customer_id="customer_123"
    )

    order_logger.info(
        "order_created",
        total_amount=99.99,
        items_count=3
    )

    order_logger.info(
        "payment_processed",
        payment_method="credit_card",
        transaction_id="txn_abc"
    )

    # Log application shutdown
    logger.info("application_stopped", uptime_seconds=3600)


if __name__ == "__main__":
    example_application()
