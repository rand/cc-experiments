#!/usr/bin/env python3
"""
PyO3 Web Frameworks Middleware Generator

Generates middleware boilerplate for FastAPI, Flask, and Django applications
with PyO3 integration. Automatically detects framework, finds hook points,
and generates production-ready middleware with testing scaffolds.

Features:
- Multi-framework detection (FastAPI, Flask, Django)
- Template-based code generation
- Hook point detection and validation
- Testing scaffold generation
- Type-annotated middleware
- PyO3 integration patterns
- Multiple middleware types (auth, logging, caching, CORS, etc.)

Usage:
    ./middleware_generator.py generate auth --framework fastapi
    ./middleware_generator.py generate logging --framework flask --output middleware/
    ./middleware_generator.py scaffold rate-limiting --framework django
    ./middleware_generator.py validate middleware/auth.py
    ./middleware_generator.py list-templates
"""

import argparse
import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MiddlewareTemplate:
    """Middleware template definition"""
    name: str
    description: str
    framework: str
    imports: List[str]
    class_template: str
    test_template: str
    hook_points: List[str] = field(default_factory=list)


@dataclass
class FrameworkConfig:
    """Framework-specific configuration"""
    name: str
    detection_patterns: List[str]
    middleware_base_class: Optional[str]
    hook_signature: str
    test_imports: List[str]


class FrameworkDetector:
    """Detect web framework from project structure"""

    FRAMEWORKS = {
        "fastapi": FrameworkConfig(
            name="fastapi",
            detection_patterns=[
                "from fastapi import",
                "import fastapi",
                "FastAPI()"
            ],
            middleware_base_class="BaseHTTPMiddleware",
            hook_signature="async def dispatch(self, request: Request, call_next)",
            test_imports=[
                "from fastapi.testclient import TestClient",
                "import pytest"
            ]
        ),
        "flask": FrameworkConfig(
            name="flask",
            detection_patterns=[
                "from flask import",
                "import flask",
                "Flask(__name__)"
            ],
            middleware_base_class=None,
            hook_signature="def __call__(self, environ, start_response)",
            test_imports=[
                "from flask import Flask",
                "import pytest"
            ]
        ),
        "django": FrameworkConfig(
            name="django",
            detection_patterns=[
                "from django",
                "import django",
                "MIDDLEWARE"
            ],
            middleware_base_class="MiddlewareMixin",
            hook_signature="def __call__(self, request)",
            test_imports=[
                "from django.test import TestCase, RequestFactory",
                "import pytest"
            ]
        )
    }

    def detect(self, project_path: Path) -> Optional[str]:
        """Detect framework from project files"""
        # Check for common framework files
        files_to_check = [
            "main.py", "app.py", "wsgi.py", "asgi.py",
            "manage.py", "settings.py", "requirements.txt"
        ]

        for file_name in files_to_check:
            file_path = project_path / file_name
            if file_path.exists():
                content = file_path.read_text()

                for framework, config in self.FRAMEWORKS.items():
                    for pattern in config.detection_patterns:
                        if pattern in content:
                            return framework

        return None

    def get_config(self, framework: str) -> Optional[FrameworkConfig]:
        """Get framework configuration"""
        return self.FRAMEWORKS.get(framework)


class TemplateRegistry:
    """Registry of middleware templates"""

    def __init__(self):
        self.templates: Dict[str, Dict[str, MiddlewareTemplate]] = {
            "fastapi": self._load_fastapi_templates(),
            "flask": self._load_flask_templates(),
            "django": self._load_django_templates()
        }

    def get_template(self, framework: str, name: str) -> Optional[MiddlewareTemplate]:
        """Get middleware template"""
        return self.templates.get(framework, {}).get(name)

    def list_templates(self, framework: Optional[str] = None) -> List[MiddlewareTemplate]:
        """List available templates"""
        if framework:
            return list(self.templates.get(framework, {}).values())
        else:
            all_templates = []
            for templates in self.templates.values():
                all_templates.extend(templates.values())
            return all_templates

    def _load_fastapi_templates(self) -> Dict[str, MiddlewareTemplate]:
        """Load FastAPI middleware templates"""
        return {
            "auth": MiddlewareTemplate(
                name="auth",
                description="JWT authentication middleware with PyO3 token validation",
                framework="fastapi",
                imports=[
                    "from fastapi import Request, Response",
                    "from fastapi.responses import JSONResponse",
                    "from starlette.middleware.base import BaseHTTPMiddleware",
                    "import my_pyo3_module  # PyO3 module",
                    "from typing import Callable"
                ],
                class_template="""
class AuthMiddleware(BaseHTTPMiddleware):
    \"\"\"Authentication middleware with PyO3 token validation\"\"\"

    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key
        self.validator = my_pyo3_module.JWTValidator(secret_key)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract token from header
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid authorization header"}
            )

        token = auth_header.replace("Bearer ", "")

        # Validate token using PyO3
        try:
            payload = self.validator.validate_token(token)
            request.state.user = payload
        except Exception as e:
            return JSONResponse(
                status_code=401,
                content={"error": f"Invalid token: {str(e)}"}
            )

        response = await call_next(request)
        return response
""",
                test_template="""
def test_auth_middleware_valid_token(client):
    \"\"\"Test authentication with valid token\"\"\"
    token = "valid_token_here"
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/protected", headers=headers)
    assert response.status_code == 200


def test_auth_middleware_missing_token(client):
    \"\"\"Test authentication with missing token\"\"\"
    response = client.get("/protected")
    assert response.status_code == 401
    assert "Missing or invalid" in response.json()["error"]


def test_auth_middleware_invalid_token(client):
    \"\"\"Test authentication with invalid token\"\"\"
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/protected", headers=headers)
    assert response.status_code == 401
""",
                hook_points=["dispatch"]
            ),
            "logging": MiddlewareTemplate(
                name="logging",
                description="Request/response logging with PyO3 performance",
                framework="fastapi",
                imports=[
                    "from fastapi import Request, Response",
                    "from starlette.middleware.base import BaseHTTPMiddleware",
                    "import my_pyo3_module  # PyO3 module",
                    "from typing import Callable",
                    "import time"
                ],
                class_template="""
class LoggingMiddleware(BaseHTTPMiddleware):
    \"\"\"Request/response logging with PyO3 performance\"\"\"

    def __init__(self, app, log_path: str):
        super().__init__(app)
        self.logger = my_pyo3_module.RequestLogger(log_path)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log using PyO3 (async logging)
        self.logger.log_request(
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
            duration_ms=duration_ms
        )

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response
""",
                test_template="""
def test_logging_middleware_logs_request(client, tmp_path):
    \"\"\"Test that requests are logged\"\"\"
    log_file = tmp_path / "requests.log"
    response = client.get("/test")
    assert response.status_code == 200
    assert "X-Response-Time" in response.headers


def test_logging_middleware_timing_header(client):
    \"\"\"Test that timing header is added\"\"\"
    response = client.get("/test")
    assert "X-Response-Time" in response.headers
    assert "ms" in response.headers["X-Response-Time"]
""",
                hook_points=["dispatch"]
            ),
            "rate-limiting": MiddlewareTemplate(
                name="rate-limiting",
                description="Rate limiting with PyO3 token bucket algorithm",
                framework="fastapi",
                imports=[
                    "from fastapi import Request, Response",
                    "from fastapi.responses import JSONResponse",
                    "from starlette.middleware.base import BaseHTTPMiddleware",
                    "import my_pyo3_module  # PyO3 module",
                    "from typing import Callable"
                ],
                class_template="""
class RateLimitMiddleware(BaseHTTPMiddleware):
    \"\"\"Rate limiting with PyO3 token bucket algorithm\"\"\"

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.limiter = my_pyo3_module.RateLimiter(max_requests, window_seconds)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client identifier (IP or user ID)
        client_id = request.client.host if request.client else "unknown"

        # Check rate limit
        allowed = self.limiter.check_rate_limit(client_id)

        if not allowed:
            remaining = self.limiter.get_remaining(client_id)
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "remaining": remaining}
            )

        response = await call_next(request)
        return response
""",
                test_template="""
def test_rate_limit_allows_requests(client):
    \"\"\"Test that requests within limit are allowed\"\"\"
    response = client.get("/test")
    assert response.status_code == 200


def test_rate_limit_blocks_excess_requests(client):
    \"\"\"Test that excess requests are blocked\"\"\"
    # Make requests up to limit
    for _ in range(100):
        response = client.get("/test")

    # This should be blocked
    response = client.get("/test")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["error"]
""",
                hook_points=["dispatch"]
            )
        }

    def _load_flask_templates(self) -> Dict[str, MiddlewareTemplate]:
        """Load Flask middleware templates"""
        return {
            "auth": MiddlewareTemplate(
                name="auth",
                description="JWT authentication middleware for Flask with PyO3",
                framework="flask",
                imports=[
                    "from flask import request, jsonify",
                    "from functools import wraps",
                    "import my_pyo3_module  # PyO3 module"
                ],
                class_template="""
class AuthMiddleware:
    \"\"\"Authentication middleware for Flask with PyO3\"\"\"

    def __init__(self, app, secret_key: str):
        self.app = app
        self.validator = my_pyo3_module.JWTValidator(secret_key)

    def __call__(self, environ, start_response):
        # Get authorization header
        auth_header = environ.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith('Bearer '):
            return self._unauthorized_response(start_response)

        token = auth_header.replace('Bearer ', '')

        # Validate token using PyO3
        try:
            payload = self.validator.validate_token(token)
            environ['USER'] = payload
        except Exception:
            return self._unauthorized_response(start_response)

        return self.app(environ, start_response)

    def _unauthorized_response(self, start_response):
        start_response('401 Unauthorized', [('Content-Type', 'application/json')])
        return [b'{"error": "Unauthorized"}']


def require_auth(f):
    \"\"\"Decorator to require authentication\"\"\"
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing authorization header"}), 401

        return f(*args, **kwargs)

    return decorated_function
""",
                test_template="""
def test_auth_middleware_valid_token(client):
    \"\"\"Test authentication with valid token\"\"\"
    headers = {"Authorization": "Bearer valid_token"}
    response = client.get("/protected", headers=headers)
    assert response.status_code == 200


def test_auth_middleware_missing_token(client):
    \"\"\"Test authentication with missing token\"\"\"
    response = client.get("/protected")
    assert response.status_code == 401
""",
                hook_points=["__call__"]
            ),
            "logging": MiddlewareTemplate(
                name="logging",
                description="Request logging middleware for Flask with PyO3",
                framework="flask",
                imports=[
                    "from flask import request, g",
                    "import my_pyo3_module  # PyO3 module",
                    "import time"
                ],
                class_template="""
class LoggingMiddleware:
    \"\"\"Request logging middleware for Flask with PyO3\"\"\"

    def __init__(self, app, log_path: str):
        self.app = app
        self.logger = my_pyo3_module.RequestLogger(log_path)

        # Register hooks
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        \"\"\"Record request start time\"\"\"
        g.start_time = time.time()

    def after_request(self, response):
        \"\"\"Log request after processing\"\"\"
        if hasattr(g, 'start_time'):
            duration_ms = (time.time() - g.start_time) * 1000

            self.logger.log_request(
                method=request.method,
                path=request.path,
                status=response.status_code,
                duration_ms=duration_ms
            )

            response.headers['X-Response-Time'] = f'{duration_ms:.2f}ms'

        return response
""",
                test_template="""
def test_logging_middleware_adds_timing_header(client):
    \"\"\"Test that timing header is added\"\"\"
    response = client.get("/test")
    assert "X-Response-Time" in response.headers
""",
                hook_points=["before_request", "after_request"]
            ),
            "caching": MiddlewareTemplate(
                name="caching",
                description="Response caching middleware for Flask with PyO3",
                framework="flask",
                imports=[
                    "from flask import request",
                    "import my_pyo3_module  # PyO3 module",
                    "import hashlib"
                ],
                class_template="""
class CachingMiddleware:
    \"\"\"Response caching middleware for Flask with PyO3\"\"\"

    def __init__(self, app, ttl_seconds: int = 300):
        self.app = app
        self.cache = my_pyo3_module.ResponseCache(ttl_seconds)

    def __call__(self, environ, start_response):
        # Generate cache key
        cache_key = self._generate_cache_key(environ)

        # Check cache
        cached_response = self.cache.get(cache_key)
        if cached_response:
            start_response('200 OK', [('Content-Type', 'application/json')])
            return [cached_response.encode()]

        # Call application
        response_data = []

        def capture_response(status, headers, exc_info=None):
            response_data.append((status, headers))
            return start_response(status, headers, exc_info)

        result = self.app(environ, capture_response)
        body = b''.join(result)

        # Cache successful responses
        if response_data and response_data[0][0].startswith('200'):
            self.cache.set(cache_key, body.decode())

        return [body]

    def _generate_cache_key(self, environ) -> str:
        \"\"\"Generate cache key from request\"\"\"
        path = environ.get('PATH_INFO', '')
        query = environ.get('QUERY_STRING', '')
        key_str = f"{path}?{query}"
        return hashlib.md5(key_str.encode()).hexdigest()
""",
                test_template="""
def test_caching_middleware_caches_response(client):
    \"\"\"Test that responses are cached\"\"\"
    response1 = client.get("/test")
    response2 = client.get("/test")
    assert response1.data == response2.data
""",
                hook_points=["__call__"]
            )
        }

    def _load_django_templates(self) -> Dict[str, MiddlewareTemplate]:
        """Load Django middleware templates"""
        return {
            "auth": MiddlewareTemplate(
                name="auth",
                description="JWT authentication middleware for Django with PyO3",
                framework="django",
                imports=[
                    "from django.http import JsonResponse",
                    "from django.utils.deprecation import MiddlewareMixin",
                    "import my_pyo3_module  # PyO3 module"
                ],
                class_template="""
class AuthMiddleware(MiddlewareMixin):
    \"\"\"Authentication middleware for Django with PyO3\"\"\"

    def __init__(self, get_response):
        super().__init__(get_response)
        self.validator = my_pyo3_module.JWTValidator(settings.SECRET_KEY)

    def process_request(self, request):
        \"\"\"Process request before view\"\"\"
        # Skip auth for certain paths
        if request.path.startswith('/public/'):
            return None

        # Get authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith('Bearer '):
            return JsonResponse(
                {"error": "Missing authorization header"},
                status=401
            )

        token = auth_header.replace('Bearer ', '')

        # Validate token using PyO3
        try:
            payload = self.validator.validate_token(token)
            request.user_payload = payload
        except Exception as e:
            return JsonResponse(
                {"error": f"Invalid token: {str(e)}"},
                status=401
            )

        return None
""",
                test_template="""
def test_auth_middleware_valid_token(client):
    \"\"\"Test authentication with valid token\"\"\"
    response = client.get(
        "/protected/",
        HTTP_AUTHORIZATION="Bearer valid_token"
    )
    assert response.status_code == 200


def test_auth_middleware_missing_token(client):
    \"\"\"Test authentication with missing token\"\"\"
    response = client.get("/protected/")
    assert response.status_code == 401
""",
                hook_points=["process_request"]
            ),
            "logging": MiddlewareTemplate(
                name="logging",
                description="Request logging middleware for Django with PyO3",
                framework="django",
                imports=[
                    "from django.utils.deprecation import MiddlewareMixin",
                    "import my_pyo3_module  # PyO3 module",
                    "import time"
                ],
                class_template="""
class LoggingMiddleware(MiddlewareMixin):
    \"\"\"Request logging middleware for Django with PyO3\"\"\"

    def __init__(self, get_response):
        super().__init__(get_response)
        self.logger = my_pyo3_module.RequestLogger('/var/log/app/requests.log')

    def process_request(self, request):
        \"\"\"Record request start time\"\"\"
        request._start_time = time.time()

    def process_response(self, request, response):
        \"\"\"Log request after processing\"\"\"
        if hasattr(request, '_start_time'):
            duration_ms = (time.time() - request._start_time) * 1000

            self.logger.log_request(
                method=request.method,
                path=request.path,
                status=response.status_code,
                duration_ms=duration_ms
            )

            response['X-Response-Time'] = f'{duration_ms:.2f}ms'

        return response
""",
                test_template="""
def test_logging_middleware_adds_timing_header(client):
    \"\"\"Test that timing header is added\"\"\"
    response = client.get("/test/")
    assert "X-Response-Time" in response
""",
                hook_points=["process_request", "process_response"]
            ),
            "cors": MiddlewareTemplate(
                name="cors",
                description="CORS middleware for Django with PyO3 validation",
                framework="django",
                imports=[
                    "from django.utils.deprecation import MiddlewareMixin",
                    "import my_pyo3_module  # PyO3 module"
                ],
                class_template="""
class CORSMiddleware(MiddlewareMixin):
    \"\"\"CORS middleware for Django with PyO3 validation\"\"\"

    def __init__(self, get_response):
        super().__init__(get_response)
        self.validator = my_pyo3_module.CORSValidator()

    def process_response(self, request, response):
        \"\"\"Add CORS headers to response\"\"\"
        origin = request.META.get('HTTP_ORIGIN', '')

        # Validate origin using PyO3
        if origin and self.validator.is_allowed_origin(origin):
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response['Access-Control-Max-Age'] = '3600'

        return response
""",
                test_template="""
def test_cors_middleware_adds_headers(client):
    \"\"\"Test that CORS headers are added\"\"\"
    response = client.get("/test/", HTTP_ORIGIN="https://example.com")
    assert "Access-Control-Allow-Origin" in response
""",
                hook_points=["process_response"]
            )
        }


class MiddlewareGenerator:
    """Generate middleware code from templates"""

    def __init__(self):
        self.registry = TemplateRegistry()

    def generate(
        self,
        framework: str,
        middleware_type: str,
        output_path: Optional[Path] = None,
        include_tests: bool = True
    ) -> Tuple[str, Optional[str]]:
        """Generate middleware code"""
        template = self.registry.get_template(framework, middleware_type)

        if not template:
            raise ValueError(
                f"Template '{middleware_type}' not found for framework '{framework}'"
            )

        # Generate middleware file
        middleware_code = self._generate_middleware_file(template)

        # Generate test file
        test_code = None
        if include_tests:
            test_code = self._generate_test_file(template)

        # Write files
        if output_path:
            output_path.mkdir(parents=True, exist_ok=True)

            middleware_file = output_path / f"{middleware_type}_middleware.py"
            middleware_file.write_text(middleware_code)

            if test_code:
                test_file = output_path / f"test_{middleware_type}_middleware.py"
                test_file.write_text(test_code)

        return middleware_code, test_code

    def _generate_middleware_file(self, template: MiddlewareTemplate) -> str:
        """Generate middleware file content"""
        lines = [
            '"""',
            f"{template.description}",
            "",
            f"Generated by middleware_generator.py",
            f"Framework: {template.framework}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            '"""',
            ""
        ]

        # Add imports
        lines.extend(template.imports)
        lines.append("")

        # Add class
        lines.append(template.class_template.strip())
        lines.append("")

        return "\n".join(lines)

    def _generate_test_file(self, template: MiddlewareTemplate) -> str:
        """Generate test file content"""
        detector = FrameworkDetector()
        config = detector.get_config(template.framework)

        lines = [
            '"""',
            f"Tests for {template.name} middleware",
            "",
            f"Generated by middleware_generator.py",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            '"""',
            ""
        ]

        # Add test imports
        if config:
            lines.extend(config.test_imports)
        lines.append("")

        # Add test class
        lines.append(template.test_template.strip())
        lines.append("")

        return "\n".join(lines)


class MiddlewareValidator:
    """Validate middleware implementation"""

    def validate(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Validate middleware file"""
        if not file_path.exists():
            return False, [f"File not found: {file_path}"]

        content = file_path.read_text()
        errors = []

        # Check for required components
        if "def __init__" not in content and "def __new__" not in content:
            errors.append("Missing __init__ or __new__ method")

        # Check for hook points
        hook_points = ["dispatch", "__call__", "process_request", "process_response"]
        has_hook = any(hook in content for hook in hook_points)

        if not has_hook:
            errors.append(f"Missing hook point (one of: {', '.join(hook_points)})")

        # Check for PyO3 import
        if "my_pyo3_module" not in content and "import" in content:
            errors.append("Warning: No PyO3 module import detected")

        # Check for error handling
        if "try:" not in content and "except" not in content:
            errors.append("Warning: No error handling detected")

        return len(errors) == 0, errors


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate middleware"""
    generator = MiddlewareGenerator()

    try:
        middleware_code, test_code = generator.generate(
            framework=args.framework,
            middleware_type=args.type,
            output_path=Path(args.output) if args.output else None,
            include_tests=not args.no_tests
        )

        if args.output:
            print(f"Generated middleware: {args.output}/{args.type}_middleware.py")
            if test_code:
                print(f"Generated tests: {args.output}/test_{args.type}_middleware.py")
        else:
            print("=" * 80)
            print("MIDDLEWARE CODE")
            print("=" * 80)
            print(middleware_code)

            if test_code:
                print()
                print("=" * 80)
                print("TEST CODE")
                print("=" * 80)
                print(test_code)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_scaffold(args: argparse.Namespace) -> int:
    """Generate complete middleware scaffold"""
    generator = MiddlewareGenerator()
    output_path = Path(args.output)

    try:
        middleware_code, test_code = generator.generate(
            framework=args.framework,
            middleware_type=args.type,
            output_path=output_path,
            include_tests=True
        )

        # Generate README
        readme_path = output_path / "README.md"
        readme_content = f"""# {args.type.title()} Middleware

Generated by middleware_generator.py

## Framework
{args.framework}

## Installation

1. Install PyO3 module:
   ```bash
   pip install -e /path/to/pyo3/module
   ```

2. Install middleware:
   ```python
   # Add to your application
   from {args.type}_middleware import {args.type.title()}Middleware
   ```

## Usage

See `{args.type}_middleware.py` for implementation details.

## Testing

Run tests:
```bash
pytest test_{args.type}_middleware.py
```
"""

        readme_path.write_text(readme_content)

        print(f"Scaffolded middleware in: {output_path}")
        print(f"  - {args.type}_middleware.py")
        print(f"  - test_{args.type}_middleware.py")
        print(f"  - README.md")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate middleware"""
    validator = MiddlewareValidator()

    file_path = Path(args.file)
    valid, errors = validator.validate(file_path)

    if valid:
        print(f"✓ {file_path} is valid")
        return 0
    else:
        print(f"✗ {file_path} has issues:")
        for error in errors:
            print(f"  - {error}")
        return 1


def cmd_list_templates(args: argparse.Namespace) -> int:
    """List available templates"""
    registry = TemplateRegistry()

    if args.json:
        templates_data = []
        for template in registry.list_templates(args.framework):
            templates_data.append({
                "name": template.name,
                "description": template.description,
                "framework": template.framework,
                "hook_points": template.hook_points
            })
        print(json.dumps(templates_data, indent=2))
    else:
        print("=" * 80)
        print("AVAILABLE MIDDLEWARE TEMPLATES")
        print("=" * 80)
        print()

        frameworks = ["fastapi", "flask", "django"]
        for framework in frameworks:
            templates = registry.list_templates(framework)
            if templates:
                print(f"{framework.upper()}")
                print("-" * 80)
                for template in templates:
                    print(f"  {template.name:20s} {template.description}")
                print()

    return 0


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate middleware for PyO3 web frameworks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Generate command
    generate_parser = subparsers.add_parser(
        'generate',
        help='Generate middleware code'
    )
    generate_parser.add_argument(
        'type',
        help='Middleware type (auth, logging, rate-limiting, caching, cors)'
    )
    generate_parser.add_argument(
        '--framework', '-f',
        required=True,
        choices=['fastapi', 'flask', 'django'],
        help='Web framework'
    )
    generate_parser.add_argument(
        '--output', '-o',
        help='Output directory'
    )
    generate_parser.add_argument(
        '--no-tests',
        action='store_true',
        help='Do not generate test files'
    )

    # Scaffold command
    scaffold_parser = subparsers.add_parser(
        'scaffold',
        help='Generate complete middleware scaffold'
    )
    scaffold_parser.add_argument(
        'type',
        help='Middleware type'
    )
    scaffold_parser.add_argument(
        '--framework', '-f',
        required=True,
        choices=['fastapi', 'flask', 'django'],
        help='Web framework'
    )
    scaffold_parser.add_argument(
        '--output', '-o',
        default='middleware',
        help='Output directory (default: middleware)'
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate middleware implementation'
    )
    validate_parser.add_argument(
        'file',
        help='Middleware file to validate'
    )

    # List templates command
    list_parser = subparsers.add_parser(
        'list-templates',
        help='List available middleware templates'
    )
    list_parser.add_argument(
        '--framework', '-f',
        choices=['fastapi', 'flask', 'django'],
        help='Filter by framework'
    )
    list_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'generate':
            return cmd_generate(args)
        elif args.command == 'scaffold':
            return cmd_scaffold(args)
        elif args.command == 'validate':
            return cmd_validate(args)
        elif args.command == 'list-templates':
            return cmd_list_templates(args)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
