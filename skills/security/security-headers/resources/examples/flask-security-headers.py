#!/usr/bin/env python3
"""
Flask Security Headers Implementation

Production-ready security headers middleware for Flask applications.
Supports CSP nonces, flexible configuration, and per-route policies.
"""

import secrets
from functools import wraps
from typing import Optional, Dict, Callable
from flask import Flask, Response, g, make_response, request


class SecurityHeaders:
    """Flask middleware for security headers."""

    def __init__(
        self,
        app: Optional[Flask] = None,
        hsts: bool = True,
        hsts_max_age: int = 31536000,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = True,
        csp: Optional[str] = None,
        csp_nonce: bool = False,
        x_frame_options: str = "DENY",
        x_content_type_options: bool = True,
        x_xss_protection: str = "0",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: Optional[str] = None,
    ):
        self.hsts = hsts
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.csp = csp
        self.csp_nonce = csp_nonce
        self.x_frame_options = x_frame_options
        self.x_content_type_options = x_content_type_options
        self.x_xss_protection = x_xss_protection
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy or (
            "geolocation=(), camera=(), microphone=(), "
            "payment=(), usb=(), magnetometer=(), "
            "gyroscope=(), accelerometer=()"
        )

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize middleware with Flask app."""
        app.before_request(self._generate_nonce)
        app.after_request(self._add_headers)

    def _generate_nonce(self):
        """Generate CSP nonce for request."""
        if self.csp_nonce:
            g.csp_nonce = secrets.token_urlsafe(16)

    def _add_headers(self, response: Response) -> Response:
        """Add security headers to response."""

        # HSTS
        if self.hsts and request.is_secure:
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # CSP
        if self.csp:
            csp_value = self.csp
            if self.csp_nonce and hasattr(g, "csp_nonce"):
                csp_value = csp_value.replace("{nonce}", g.csp_nonce)
            response.headers["Content-Security-Policy"] = csp_value

        # X-Frame-Options
        if self.x_frame_options:
            response.headers["X-Frame-Options"] = self.x_frame_options

        # X-Content-Type-Options
        if self.x_content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection
        if self.x_xss_protection:
            response.headers["X-XSS-Protection"] = self.x_xss_protection

        # Referrer-Policy
        if self.referrer_policy:
            response.headers["Referrer-Policy"] = self.referrer_policy

        # Permissions-Policy
        if self.permissions_policy:
            response.headers["Permissions-Policy"] = self.permissions_policy

        return response


def require_csp(policy: str) -> Callable:
    """Decorator to set custom CSP for specific route."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = make_response(f(*args, **kwargs))

            # Replace nonce placeholder if present
            csp_value = policy
            if hasattr(g, "csp_nonce"):
                csp_value = csp_value.replace("{nonce}", g.csp_nonce)

            response.headers["Content-Security-Policy"] = csp_value
            return response

        return decorated_function

    return decorator


def set_cookie_secure(
    response: Response,
    key: str,
    value: str,
    max_age: Optional[int] = None,
    httponly: bool = True,
    secure: bool = True,
    samesite: str = "Strict",
    **kwargs,
) -> Response:
    """Set cookie with secure attributes."""
    response.set_cookie(
        key,
        value,
        max_age=max_age,
        httponly=httponly,
        secure=secure,
        samesite=samesite,
        **kwargs,
    )
    return response


# Example Flask application
def create_app():
    """Create example Flask application with security headers."""
    app = Flask(__name__)

    # Configure session security
    app.config.update(
        SECRET_KEY=secrets.token_hex(32),
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        PERMANENT_SESSION_LIFETIME=3600,
    )

    # Initialize security headers
    SecurityHeaders(
        app,
        hsts=True,
        hsts_max_age=31536000,
        hsts_include_subdomains=True,
        hsts_preload=True,
        csp=(
            "default-src 'self'; "
            "script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'nonce-{nonce}'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'"
        ),
        csp_nonce=True,
        x_frame_options="DENY",
        x_content_type_options=True,
        x_xss_protection="0",
        referrer_policy="strict-origin-when-cross-origin",
        permissions_policy=(
            "geolocation=(), camera=(), microphone=(), "
            "payment=(), usb=()"
        ),
    )

    @app.route("/")
    def index():
        """Home page."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Security Headers Example</title>
            <style nonce="{g.csp_nonce}">
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                }}
                .header {{ color: #2c3e50; }}
                .code {{ background: #f4f4f4; padding: 10px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1 class="header">Flask Security Headers Example</h1>
            <p>This application demonstrates security headers implementation.</p>

            <h2>Active Security Headers:</h2>
            <ul>
                <li>Strict-Transport-Security (HSTS)</li>
                <li>Content-Security-Policy (CSP) with nonces</li>
                <li>X-Frame-Options</li>
                <li>X-Content-Type-Options</li>
                <li>Referrer-Policy</li>
                <li>Permissions-Policy</li>
            </ul>

            <h2>CSP Nonce:</h2>
            <div class="code">{g.csp_nonce}</div>

            <script nonce="{g.csp_nonce}">
                console.log('Script with nonce executed');
                console.log('CSP Nonce:', '{g.csp_nonce}');
            </script>
        </body>
        </html>
        """

    @app.route("/api/data")
    @require_csp("default-src 'none'; frame-ancestors 'none'")
    def api_data():
        """API endpoint with strict CSP."""
        return {"message": "API data", "status": "success"}

    @app.route("/set-cookie")
    def set_cookie_example():
        """Example of setting secure cookie."""
        response = make_response({"message": "Cookie set"})
        set_cookie_secure(
            response,
            key="user_session",
            value="abc123",
            max_age=3600,
            httponly=True,
            secure=True,
            samesite="Strict",
        )
        return response

    @app.route("/csp-report", methods=["POST"])
    def csp_report():
        """CSP violation report endpoint."""
        report = request.get_json()
        app.logger.warning(f"CSP Violation: {report}")

        # Store in database, send to monitoring service, etc.
        # ...

        return "", 204

    return app


# Alternative: Simpler decorator-based approach
def add_security_headers(f):
    """Simple decorator to add security headers to response."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))

        # HSTS
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # CSP
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'"
        )

        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "0"

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=()"
        )

        return response

    return decorated_function


# Example using decorator approach
def create_simple_app():
    """Create Flask app with decorator-based security headers."""
    app = Flask(__name__)

    @app.route("/")
    @add_security_headers
    def index():
        return "<h1>Hello, World!</h1>"

    return app


if __name__ == "__main__":
    # Run example application
    app = create_app()
    app.run(debug=False, host="127.0.0.1", port=5000)
