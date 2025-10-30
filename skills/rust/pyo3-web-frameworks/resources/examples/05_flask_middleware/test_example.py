"""Test suite for flask_middleware."""

import pytest
import flask_middleware


def test_request_logger():
    """Test request logging."""
    logger = flask_middleware.RequestLogger()
    logger.log_request("GET", "/api/test", 200, 0.123)

    logs = logger.get_logs()
    assert len(logs) == 1
    assert "GET" in logs[0]
    assert "/api/test" in logs[0]


def test_request_tracker():
    """Test request tracking."""
    import time

    tracker = flask_middleware.RequestTracker()
    tracker.start_request(1)
    time.sleep(0.1)
    duration = tracker.end_request(1)

    assert duration >= 0.1
    assert tracker.active_requests() == 0


def test_sanitize_headers():
    """Test header sanitization."""
    headers = [
        ("Content-Type", "application/json"),
        ("Authorization", "Bearer secret"),
        ("X-API-Key", "key123")
    ]

    sanitized = flask_middleware.sanitize_headers(headers)
    assert sanitized[0][1] == "application/json"
    assert sanitized[1][1] == "[REDACTED]"
    assert sanitized[2][1] == "[REDACTED]"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
