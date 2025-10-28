#!/usr/bin/env python3
"""
REST API Validator

Validates REST API design against best practices including:
- Resource naming conventions
- HTTP method usage
- Status code correctness
- Response format consistency
- Security headers
- Rate limiting headers
- Pagination standards
- Error response format
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


class Severity(Enum):
    """Issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    """Validation issue"""
    severity: Severity
    category: str
    message: str
    endpoint: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Validation results"""
    passed: bool
    issues: List[Issue] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    def add_issue(self, severity: Severity, category: str, message: str,
                  endpoint: Optional[str] = None, suggestion: Optional[str] = None):
        """Add validation issue"""
        self.issues.append(Issue(severity, category, message, endpoint, suggestion))
        if not self.passed and severity == Severity.ERROR:
            self.passed = False


class APIValidator:
    """REST API validator"""

    def __init__(self):
        self.result = ValidationResult(passed=True)

    def validate_spec(self, spec: Dict[str, Any]) -> ValidationResult:
        """Validate API specification"""
        # OpenAPI format
        if "openapi" in spec or "swagger" in spec:
            return self._validate_openapi(spec)

        # Custom format
        if "endpoints" in spec:
            return self._validate_custom(spec)

        self.result.add_issue(
            Severity.ERROR,
            "format",
            "Unknown API specification format"
        )
        self.result.passed = False
        return self.result

    def _validate_openapi(self, spec: Dict[str, Any]) -> ValidationResult:
        """Validate OpenAPI specification"""
        # Validate paths
        paths = spec.get("paths", {})
        for path, methods in paths.items():
            self._validate_endpoint_path(path)

            for method, details in methods.items():
                if method.lower() in ["get", "post", "put", "patch", "delete", "options", "head"]:
                    self._validate_endpoint_method(path, method.upper(), details)

        # Validate security
        if "security" not in spec and "securitySchemes" not in spec.get("components", {}):
            self.result.add_issue(
                Severity.WARNING,
                "security",
                "No security schemes defined",
                suggestion="Add authentication requirements"
            )

        # Calculate stats
        self.result.stats = {
            "total_endpoints": sum(
                len([m for m in methods.keys() if m.lower() in ["get", "post", "put", "patch", "delete"]])
                for methods in paths.values()
            ),
            "errors": len([i for i in self.result.issues if i.severity == Severity.ERROR]),
            "warnings": len([i for i in self.result.issues if i.severity == Severity.WARNING]),
            "info": len([i for i in self.result.issues if i.severity == Severity.INFO])
        }

        return self.result

    def _validate_custom(self, spec: Dict[str, Any]) -> ValidationResult:
        """Validate custom API format"""
        endpoints = spec.get("endpoints", [])

        for endpoint in endpoints:
            path = endpoint.get("path", "")
            method = endpoint.get("method", "")

            self._validate_endpoint_path(path)
            self._validate_endpoint_method(path, method, endpoint)

        # Calculate stats
        self.result.stats = {
            "total_endpoints": len(endpoints),
            "errors": len([i for i in self.result.issues if i.severity == Severity.ERROR]),
            "warnings": len([i for i in self.result.issues if i.severity == Severity.WARNING]),
            "info": len([i for i in self.result.issues if i.severity == Severity.INFO])
        }

        return self.result

    def _validate_endpoint_path(self, path: str):
        """Validate endpoint path"""
        endpoint = path

        # Check for leading slash
        if not path.startswith("/"):
            self.result.add_issue(
                Severity.ERROR,
                "url_design",
                f"Path must start with /: {path}",
                endpoint=endpoint,
                suggestion=f"Use: /{path}"
            )

        # Check for trailing slash
        if path != "/" and path.endswith("/"):
            self.result.add_issue(
                Severity.WARNING,
                "url_design",
                f"Path should not end with /: {path}",
                endpoint=endpoint,
                suggestion=f"Use: {path.rstrip('/')}"
            )

        # Check for verbs in URL
        verbs = ["get", "create", "update", "delete", "list", "fetch", "retrieve", "add", "remove"]
        path_lower = path.lower()
        for verb in verbs:
            if f"/{verb}" in path_lower or path_lower.startswith(f"{verb}/"):
                self.result.add_issue(
                    Severity.ERROR,
                    "url_design",
                    f"URL contains verb '{verb}': {path}",
                    endpoint=endpoint,
                    suggestion="Use HTTP methods instead of verbs in URLs"
                )

        # Check for camelCase or snake_case (prefer kebab-case)
        parts = [p for p in path.split("/") if p and not p.startswith("{")]
        for part in parts:
            if "_" in part:
                self.result.add_issue(
                    Severity.WARNING,
                    "url_design",
                    f"Use kebab-case instead of snake_case: {part}",
                    endpoint=endpoint,
                    suggestion=part.replace("_", "-")
                )
            elif any(c.isupper() for c in part):
                self.result.add_issue(
                    Severity.WARNING,
                    "url_design",
                    f"Use lowercase in URLs: {part}",
                    endpoint=endpoint
                )

        # Check resource naming (prefer plural)
        static_parts = [p for p in path.split("/") if p and not p.startswith("{")]
        for i, part in enumerate(static_parts):
            # Skip if likely plural or special case
            if part in ["api", "v1", "v2", "v3", "auth", "health", "metrics"]:
                continue
            if part.endswith("s") or part.endswith("ies"):
                continue
            # If followed by parameter, likely should be plural
            path_parts = path.split("/")
            try:
                idx = path_parts.index(part)
                if idx + 1 < len(path_parts) and path_parts[idx + 1].startswith("{"):
                    self.result.add_issue(
                        Severity.INFO,
                        "url_design",
                        f"Consider using plural form: {part}",
                        endpoint=endpoint,
                        suggestion=f"Use: {part}s"
                    )
            except ValueError:
                pass

    def _validate_endpoint_method(self, path: str, method: str, details: Dict[str, Any]):
        """Validate HTTP method usage"""
        endpoint = f"{method} {path}"

        # GET should be safe and idempotent
        if method == "GET":
            if "requestBody" in details:
                self.result.add_issue(
                    Severity.ERROR,
                    "http_methods",
                    "GET requests should not have request body",
                    endpoint=endpoint,
                    suggestion="Use query parameters or switch to POST"
                )

        # POST for creation should return 201
        if method == "POST":
            responses = details.get("responses", {})
            if "201" not in responses and "200" in responses:
                self.result.add_issue(
                    Severity.WARNING,
                    "status_codes",
                    "POST for resource creation should return 201 Created",
                    endpoint=endpoint
                )

        # DELETE should return 204 or 200
        if method == "DELETE":
            responses = details.get("responses", {})
            if "204" not in responses and "200" not in responses:
                self.result.add_issue(
                    Severity.WARNING,
                    "status_codes",
                    "DELETE should return 204 No Content or 200 OK",
                    endpoint=endpoint
                )

        # Check for proper error responses
        responses = details.get("responses", {})
        has_4xx = any(code.startswith("4") for code in responses.keys())
        has_5xx = any(code.startswith("5") for code in responses.keys())

        if not has_4xx:
            self.result.add_issue(
                Severity.INFO,
                "error_handling",
                "Consider documenting 4xx error responses",
                endpoint=endpoint
            )

        if not has_5xx:
            self.result.add_issue(
                Severity.INFO,
                "error_handling",
                "Consider documenting 5xx error responses",
                endpoint=endpoint
            )

    def validate_response(self, response_data: Dict[str, Any]) -> ValidationResult:
        """Validate API response format"""
        # Check for consistent data wrapper
        if isinstance(response_data, list):
            self.result.add_issue(
                Severity.WARNING,
                "response_format",
                "Response is bare array, consider wrapping in object",
                suggestion='Use: {"data": [...]}'
            )

        # Check for pagination metadata in collections
        if isinstance(response_data, dict) and "data" in response_data:
            data = response_data["data"]
            if isinstance(data, list) and len(data) > 10:
                if "pagination" not in response_data:
                    self.result.add_issue(
                        Severity.INFO,
                        "pagination",
                        "Large collection without pagination metadata",
                        suggestion="Add pagination info (limit, offset, total)"
                    )

        # Check naming convention
        if isinstance(response_data, dict):
            self._check_naming_convention(response_data)

        return self.result

    def _check_naming_convention(self, obj: Dict[str, Any], path: str = ""):
        """Check JSON naming convention consistency"""
        snake_case = 0
        camel_case = 0

        for key in obj.keys():
            if "_" in key:
                snake_case += 1
            elif any(c.isupper() for c in key[1:]):  # camelCase has uppercase after first char
                camel_case += 1

        if snake_case > 0 and camel_case > 0:
            self.result.add_issue(
                Severity.WARNING,
                "response_format",
                f"Inconsistent naming convention (snake_case and camelCase mixed) at {path or 'root'}",
                suggestion="Choose one naming convention and stick with it"
            )

    def validate_headers(self, headers: Dict[str, str], method: str = "GET") -> ValidationResult:
        """Validate response headers"""
        headers_lower = {k.lower(): v for k, v in headers.items()}

        # Check Content-Type
        if "content-type" not in headers_lower:
            self.result.add_issue(
                Severity.ERROR,
                "headers",
                "Missing Content-Type header",
                suggestion="Add: Content-Type: application/json"
            )

        # Check cache headers for GET
        if method == "GET":
            if "cache-control" not in headers_lower and "etag" not in headers_lower:
                self.result.add_issue(
                    Severity.INFO,
                    "caching",
                    "No caching headers present",
                    suggestion="Consider adding Cache-Control or ETag headers"
                )

        # Check security headers
        security_headers = {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "strict-transport-security": None
        }

        for header, expected in security_headers.items():
            if header not in headers_lower:
                self.result.add_issue(
                    Severity.INFO,
                    "security",
                    f"Missing security header: {header}",
                    suggestion=f"Add: {header}: {expected}" if expected else None
                )

        # Check rate limit headers
        rate_limit_headers = ["x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"]
        has_rate_limit = any(h in headers_lower for h in rate_limit_headers)

        if not has_rate_limit:
            self.result.add_issue(
                Severity.INFO,
                "rate_limiting",
                "No rate limit headers present",
                suggestion="Consider adding X-RateLimit-* headers"
            )

        return self.result


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate REST API design against best practices"
    )
    parser.add_argument(
        "input",
        help="API specification file (OpenAPI JSON/YAML or custom format)"
    )
    parser.add_argument(
        "--type",
        choices=["spec", "response", "headers"],
        default="spec",
        help="Validation type (default: spec)"
    )
    parser.add_argument(
        "--method",
        default="GET",
        help="HTTP method for header validation (default: GET)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--help-full",
        action="store_true",
        help="Show detailed help and examples"
    )

    args = parser.parse_args()

    if args.help_full:
        print_full_help()
        return 0

    # Load input
    try:
        with open(args.input) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        return 1

    # Validate
    validator = APIValidator()

    if args.type == "spec":
        result = validator.validate_spec(data)
    elif args.type == "response":
        result = validator.validate_response(data)
    elif args.type == "headers":
        result = validator.validate_headers(data, args.method)
    else:
        print(f"Error: Unknown validation type: {args.type}", file=sys.stderr)
        return 1

    # Output results
    if args.json:
        output = {
            "passed": result.passed,
            "stats": result.stats,
            "issues": [
                {
                    "severity": issue.severity.value,
                    "category": issue.category,
                    "message": issue.message,
                    "endpoint": issue.endpoint,
                    "suggestion": issue.suggestion
                }
                for issue in result.issues
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        print_human_readable(result, args.strict)

    # Exit code
    errors = len([i for i in result.issues if i.severity == Severity.ERROR])
    if args.strict:
        errors += len([i for i in result.issues if i.severity == Severity.WARNING])

    return 1 if errors > 0 else 0


def print_human_readable(result: ValidationResult, strict: bool):
    """Print human-readable validation results"""
    # Stats
    if result.stats:
        print("Statistics:")
        for key, value in result.stats.items():
            print(f"  {key}: {value}")
        print()

    # Issues
    if not result.issues:
        print("✓ No issues found")
        return

    print(f"Found {len(result.issues)} issue(s):\n")

    # Group by severity
    for severity in [Severity.ERROR, Severity.WARNING, Severity.INFO]:
        issues = [i for i in result.issues if i.severity == severity]
        if not issues:
            continue

        icon = "✗" if severity == Severity.ERROR else "⚠" if severity == Severity.WARNING else "ℹ"
        print(f"{icon} {severity.value.upper()} ({len(issues)}):")

        for issue in issues:
            print(f"  [{issue.category}] {issue.message}")
            if issue.endpoint:
                print(f"    Endpoint: {issue.endpoint}")
            if issue.suggestion:
                print(f"    Suggestion: {issue.suggestion}")
            print()


def print_full_help():
    """Print detailed help"""
    help_text = """
REST API Validator - Detailed Help

USAGE:
    validate_api.py <input> [options]

VALIDATION TYPES:
    --type spec        Validate API specification (OpenAPI or custom format)
    --type response    Validate response format and structure
    --type headers     Validate HTTP headers

EXAMPLES:
    # Validate OpenAPI specification
    validate_api.py openapi.json --type spec

    # Validate response format
    validate_api.py response.json --type response --json

    # Validate headers
    validate_api.py headers.json --type headers --method GET

    # Strict mode (warnings as errors)
    validate_api.py openapi.json --strict

INPUT FORMATS:

1. OpenAPI Specification:
   {
     "openapi": "3.0.0",
     "paths": {
       "/users": {
         "get": {...}
       }
     }
   }

2. Custom Specification:
   {
     "endpoints": [
       {
         "path": "/api/users",
         "method": "GET",
         "responses": {...}
       }
     ]
   }

3. Response:
   {
     "data": [...],
     "pagination": {...}
   }

4. Headers:
   {
     "Content-Type": "application/json",
     "Cache-Control": "max-age=3600"
   }

VALIDATION CATEGORIES:
    - url_design: URL structure and naming conventions
    - http_methods: HTTP method usage
    - status_codes: Status code correctness
    - response_format: Response structure and consistency
    - error_handling: Error response format
    - security: Security headers
    - caching: Cache headers
    - rate_limiting: Rate limit headers
    - pagination: Pagination metadata

BEST PRACTICES CHECKED:
    ✓ Nouns in URLs (not verbs)
    ✓ Plural resource names
    ✓ kebab-case for multi-word resources
    ✓ Proper HTTP method usage
    ✓ Correct status codes
    ✓ Consistent naming conventions
    ✓ Error response format
    ✓ Security headers
    ✓ Cache headers
    ✓ Rate limit headers
    ✓ Pagination for collections

EXIT CODES:
    0: Success (no errors)
    1: Validation failed (errors found)
"""
    print(help_text)


if __name__ == "__main__":
    sys.exit(main())
