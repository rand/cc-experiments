#!/usr/bin/env python3
"""
Nginx Configuration Validator

Validates Nginx configuration files for security issues, best practices,
and common misconfigurations.

Usage:
    ./validate_config.py --help
    ./validate_config.py --config-file /etc/nginx/nginx.conf
    ./validate_config.py --config-file nginx.conf --json
    ./validate_config.py --config-file nginx.conf --strict
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional, Set


@dataclass
class Issue:
    """Represents a configuration issue"""
    severity: str  # error, warning, info
    category: str
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Validation results"""
    file_path: str
    valid: bool
    issues: List[Issue] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    def add_issue(self, severity: str, category: str, message: str,
                  line: Optional[int] = None, suggestion: Optional[str] = None):
        """Add an issue to the results"""
        self.issues.append(Issue(severity, category, message, line, suggestion))
        if severity == "error":
            self.valid = False

    def to_dict(self):
        """Convert to dictionary for JSON output"""
        return {
            "file_path": self.file_path,
            "valid": self.valid,
            "issues": [asdict(issue) for issue in self.issues],
            "stats": self.stats
        }


class NginxConfigValidator:
    """Validates Nginx configuration files"""

    # Deprecated directives
    DEPRECATED_DIRECTIVES = {
        "spdy_headers_comp": "Removed in Nginx 1.9.5, use http2 instead",
        "ssl_protocols SSLv2": "SSLv2 is insecure, use TLSv1.2 or TLSv1.3",
        "ssl_protocols SSLv3": "SSLv3 is insecure, use TLSv1.2 or TLSv1.3",
        "ssl_protocols TLSv1": "TLSv1 is insecure, use TLSv1.2 or TLSv1.3",
        "ssl_protocols TLSv1.1": "TLSv1.1 is deprecated, use TLSv1.2 or TLSv1.3",
    }

    # Weak SSL ciphers
    WEAK_CIPHERS = [
        "RC4", "DES", "3DES", "MD5", "SHA1", "NULL", "EXPORT", "LOW", "MEDIUM",
        "aNULL", "eNULL", "EXP"
    ]

    # Security headers that should be present
    SECURITY_HEADERS = {
        "X-Frame-Options": "Prevents clickjacking attacks",
        "X-Content-Type-Options": "Prevents MIME type sniffing",
        "Strict-Transport-Security": "Enforces HTTPS (for SSL sites)",
        "Content-Security-Policy": "Prevents XSS and injection attacks",
    }

    def __init__(self, strict: bool = False):
        self.strict = strict

    def validate_file(self, config_path: Path) -> ValidationResult:
        """Validate a configuration file"""
        result = ValidationResult(file_path=str(config_path), valid=True)

        if not config_path.exists():
            result.add_issue("error", "file", f"Configuration file not found: {config_path}")
            return result

        try:
            content = config_path.read_text()
            lines = content.split('\n')
        except Exception as e:
            result.add_issue("error", "file", f"Failed to read file: {e}")
            return result

        # Run validations
        self._check_syntax(lines, result)
        self._check_deprecated_directives(lines, result)
        self._check_security(lines, result)
        self._check_ssl_tls(lines, result)
        self._check_performance(lines, result)
        self._check_best_practices(lines, result)
        self._generate_stats(result)

        return result

    def _check_syntax(self, lines: List[str], result: ValidationResult):
        """Check basic syntax issues"""
        in_block = 0
        for i, line in enumerate(lines, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Check braces
            in_block += line.count('{') - line.count('}')

            # Check semicolons (directives should end with ; or {)
            if not line.endswith((';', '{', '}')) and not line.startswith('#'):
                # Could be a multi-line directive
                if '{' not in line and '}' not in line:
                    result.add_issue(
                        "warning", "syntax",
                        "Directive may be missing semicolon",
                        line=i,
                        suggestion="Add semicolon at the end of the directive"
                    )

        # Check balanced braces
        if in_block != 0:
            result.add_issue(
                "error", "syntax",
                f"Unbalanced braces: {in_block} unclosed blocks",
                suggestion="Ensure all { have matching }"
            )

    def _check_deprecated_directives(self, lines: List[str], result: ValidationResult):
        """Check for deprecated directives"""
        for i, line in enumerate(lines, 1):
            line_clean = line.strip()

            for deprecated, message in self.DEPRECATED_DIRECTIVES.items():
                if deprecated in line_clean:
                    result.add_issue(
                        "warning", "deprecated",
                        f"Deprecated directive: {deprecated}",
                        line=i,
                        suggestion=message
                    )

    def _check_security(self, lines: List[str], result: ValidationResult):
        """Check security configurations"""
        content = '\n'.join(lines)

        # Check if server_tokens is disabled
        if 'server_tokens off' not in content:
            result.add_issue(
                "warning", "security",
                "server_tokens should be disabled to hide Nginx version",
                suggestion="Add 'server_tokens off;' in http or server block"
            )

        # Check for security headers (if SSL is used)
        if 'ssl_certificate' in content:
            for header, description in self.SECURITY_HEADERS.items():
                if header not in content:
                    severity = "error" if self.strict else "warning"
                    result.add_issue(
                        severity, "security",
                        f"Missing security header: {header}",
                        suggestion=f"Add 'add_header {header} ...; ({description})"
                    )

        # Check for default_server without server_name
        if 'default_server' in content:
            # This is actually OK, just informational
            result.add_issue(
                "info", "security",
                "default_server configured (ensure this is intentional)"
            )

        # Check for allow/deny rules
        if 'allow all' in content:
            result.add_issue(
                "warning", "security",
                "Found 'allow all' - ensure this is intentional",
                suggestion="Use specific IP ranges instead of 'allow all'"
            )

    def _check_ssl_tls(self, lines: List[str], result: ValidationResult):
        """Check SSL/TLS configuration"""
        content = '\n'.join(lines)

        if 'ssl_certificate' not in content:
            return  # No SSL configured

        # Check SSL protocols
        ssl_protocols = re.search(r'ssl_protocols\s+([^;]+);', content)
        if ssl_protocols:
            protocols = ssl_protocols.group(1).lower()

            # Check for weak protocols
            if 'sslv2' in protocols or 'sslv3' in protocols:
                result.add_issue(
                    "error", "ssl",
                    "Insecure SSL protocols detected (SSLv2/SSLv3)",
                    suggestion="Use only TLSv1.2 and TLSv1.3"
                )

            if 'tlsv1 ' in protocols or 'tlsv1.1' in protocols:
                result.add_issue(
                    "warning", "ssl",
                    "Weak TLS protocols detected (TLSv1.0/TLSv1.1)",
                    suggestion="Use only TLSv1.2 and TLSv1.3"
                )

            # Check if TLS 1.2 or 1.3 is present
            if 'tlsv1.2' not in protocols and 'tlsv1.3' not in protocols:
                result.add_issue(
                    "error", "ssl",
                    "No modern TLS protocols configured",
                    suggestion="Add 'ssl_protocols TLSv1.2 TLSv1.3;'"
                )
        else:
            result.add_issue(
                "warning", "ssl",
                "ssl_protocols not explicitly configured",
                suggestion="Add 'ssl_protocols TLSv1.2 TLSv1.3;'"
            )

        # Check SSL ciphers
        ssl_ciphers = re.search(r'ssl_ciphers\s+[\'"]?([^;\'"]+)[\'"]?;', content)
        if ssl_ciphers:
            cipher_string = ssl_ciphers.group(1).upper()

            for weak_cipher in self.WEAK_CIPHERS:
                if weak_cipher in cipher_string:
                    result.add_issue(
                        "error", "ssl",
                        f"Weak cipher detected: {weak_cipher}",
                        suggestion="Use strong ciphers (ECDHE-*-AES*-GCM-SHA*, CHACHA20-POLY1305)"
                    )

        # Check for session cache
        if 'ssl_session_cache' not in content:
            result.add_issue(
                "warning", "ssl",
                "ssl_session_cache not configured",
                suggestion="Add 'ssl_session_cache shared:SSL:10m;' for better performance"
            )

        # Check for OCSP stapling
        if 'ssl_stapling on' not in content:
            result.add_issue(
                "info", "ssl",
                "OCSP stapling not enabled",
                suggestion="Add 'ssl_stapling on;' and 'ssl_stapling_verify on;'"
            )

        # Check for session tickets (should be off for better forward secrecy)
        if 'ssl_session_tickets' not in content:
            result.add_issue(
                "info", "ssl",
                "ssl_session_tickets not explicitly configured",
                suggestion="Add 'ssl_session_tickets off;' for better forward secrecy"
            )

    def _check_performance(self, lines: List[str], result: ValidationResult):
        """Check performance configurations"""
        content = '\n'.join(lines)

        # Check worker_processes
        if 'worker_processes' not in content:
            result.add_issue(
                "warning", "performance",
                "worker_processes not configured",
                suggestion="Add 'worker_processes auto;' to match CPU cores"
            )
        elif 'worker_processes 1' in content:
            result.add_issue(
                "info", "performance",
                "Only 1 worker process configured",
                suggestion="Consider 'worker_processes auto;' for better performance"
            )

        # Check worker_connections
        if 'worker_connections' not in content:
            result.add_issue(
                "warning", "performance",
                "worker_connections not configured",
                suggestion="Add 'worker_connections 1024;' (or higher) in events block"
            )

        # Check sendfile
        if 'sendfile on' not in content:
            result.add_issue(
                "info", "performance",
                "sendfile not enabled",
                suggestion="Add 'sendfile on;' for better file serving performance"
            )

        # Check tcp_nopush
        if 'sendfile on' in content and 'tcp_nopush on' not in content:
            result.add_issue(
                "info", "performance",
                "tcp_nopush not enabled",
                suggestion="Add 'tcp_nopush on;' when using sendfile"
            )

        # Check gzip
        if 'gzip on' not in content:
            result.add_issue(
                "info", "performance",
                "gzip compression not enabled",
                suggestion="Add 'gzip on;' to compress responses"
            )

        # Check keepalive
        keepalive_match = re.search(r'keepalive\s+(\d+)', content)
        if keepalive_match:
            keepalive = int(keepalive_match.group(1))
            if keepalive < 16:
                result.add_issue(
                    "info", "performance",
                    f"Low keepalive connections ({keepalive})",
                    suggestion="Consider increasing to 32 or more"
                )

    def _check_best_practices(self, lines: List[str], result: ValidationResult):
        """Check best practices"""
        content = '\n'.join(lines)

        # Check for hardcoded IPs in proxy_pass
        proxy_passes = re.findall(r'proxy_pass\s+http://(\d+\.\d+\.\d+\.\d+)', content)
        if proxy_passes:
            result.add_issue(
                "warning", "best-practice",
                "Hardcoded IP addresses in proxy_pass",
                suggestion="Use upstream blocks for load balancing and failover"
            )

        # Check for if statements (if is evil)
        if_count = content.count('if (')
        if if_count > 3:
            result.add_issue(
                "warning", "best-practice",
                f"Multiple if statements found ({if_count})",
                suggestion="Consider using location blocks or map instead of if"
            )

        # Check for error_log
        if 'error_log' not in content:
            result.add_issue(
                "warning", "best-practice",
                "error_log not configured",
                suggestion="Add 'error_log /var/log/nginx/error.log warn;'"
            )

        # Check for access_log
        if 'access_log' not in content:
            result.add_issue(
                "info", "best-practice",
                "access_log not configured",
                suggestion="Add 'access_log /var/log/nginx/access.log;'"
            )

        # Check for client_max_body_size with uploads
        if 'proxy_pass' in content and 'client_max_body_size' not in content:
            result.add_issue(
                "info", "best-practice",
                "client_max_body_size not configured",
                suggestion="Add 'client_max_body_size 10m;' to allow file uploads"
            )

        # Check for proxy headers
        if 'proxy_pass' in content:
            required_headers = [
                'proxy_set_header Host',
                'proxy_set_header X-Real-IP',
                'proxy_set_header X-Forwarded-For'
            ]
            for header in required_headers:
                if header not in content:
                    result.add_issue(
                        "warning", "best-practice",
                        f"Missing recommended proxy header: {header}",
                        suggestion=f"Add '{header}' directive"
                    )

        # Check for rate limiting zones defined but not used
        limit_zones = re.findall(r'limit_req_zone[^;]+zone=(\w+)', content)
        for zone in limit_zones:
            if f'limit_req zone={zone}' not in content:
                result.add_issue(
                    "warning", "best-practice",
                    f"Rate limit zone '{zone}' defined but not used",
                    suggestion=f"Use 'limit_req zone={zone} burst=X;' in a location"
                )

    def _generate_stats(self, result: ValidationResult):
        """Generate statistics about issues"""
        result.stats = {
            "total_issues": len(result.issues),
            "errors": sum(1 for i in result.issues if i.severity == "error"),
            "warnings": sum(1 for i in result.issues if i.severity == "warning"),
            "info": sum(1 for i in result.issues if i.severity == "info"),
        }

        # Count by category
        categories = {}
        for issue in result.issues:
            categories[issue.category] = categories.get(issue.category, 0) + 1
        result.stats["by_category"] = categories


def format_output(result: ValidationResult, json_output: bool = False) -> str:
    """Format validation results"""
    if json_output:
        return json.dumps(result.to_dict(), indent=2)

    output = []
    output.append(f"\n{'='*70}")
    output.append(f"Nginx Configuration Validation: {result.file_path}")
    output.append(f"{'='*70}\n")

    if result.valid and not result.issues:
        output.append("✓ Configuration is valid with no issues found.\n")
        return '\n'.join(output)

    # Group issues by severity
    errors = [i for i in result.issues if i.severity == "error"]
    warnings = [i for i in result.issues if i.severity == "warning"]
    info = [i for i in result.issues if i.severity == "info"]

    # Display errors
    if errors:
        output.append(f"ERRORS ({len(errors)}):")
        output.append("-" * 70)
        for issue in errors:
            output.append(f"  [{issue.category.upper()}] {issue.message}")
            if issue.line:
                output.append(f"    Line: {issue.line}")
            if issue.suggestion:
                output.append(f"    Suggestion: {issue.suggestion}")
            output.append("")

    # Display warnings
    if warnings:
        output.append(f"WARNINGS ({len(warnings)}):")
        output.append("-" * 70)
        for issue in warnings:
            output.append(f"  [{issue.category.upper()}] {issue.message}")
            if issue.line:
                output.append(f"    Line: {issue.line}")
            if issue.suggestion:
                output.append(f"    Suggestion: {issue.suggestion}")
            output.append("")

    # Display info
    if info:
        output.append(f"INFORMATION ({len(info)}):")
        output.append("-" * 70)
        for issue in info:
            output.append(f"  [{issue.category.upper()}] {issue.message}")
            if issue.line:
                output.append(f"    Line: {issue.line}")
            if issue.suggestion:
                output.append(f"    Suggestion: {issue.suggestion}")
            output.append("")

    # Summary
    output.append("=" * 70)
    output.append("SUMMARY:")
    output.append(f"  Total Issues: {result.stats['total_issues']}")
    output.append(f"  Errors: {result.stats['errors']}")
    output.append(f"  Warnings: {result.stats['warnings']}")
    output.append(f"  Info: {result.stats['info']}")
    output.append("")

    if result.stats.get('by_category'):
        output.append("Issues by Category:")
        for category, count in sorted(result.stats['by_category'].items()):
            output.append(f"  {category}: {count}")
        output.append("")

    output.append(f"Status: {'FAILED' if not result.valid else 'PASSED'}")
    output.append("=" * 70 + "\n")

    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Validate Nginx configuration files for security and best practices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a configuration file
  %(prog)s --config-file /etc/nginx/nginx.conf

  # Validate with JSON output
  %(prog)s --config-file nginx.conf --json

  # Strict mode (treat warnings as errors)
  %(prog)s --config-file nginx.conf --strict

  # Validate and save output
  %(prog)s --config-file nginx.conf > validation-report.txt
        """
    )

    parser.add_argument(
        '--config-file',
        required=True,
        type=Path,
        help='Path to Nginx configuration file'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='Strict mode: treat some warnings as errors'
    )

    args = parser.parse_args()

    # Validate configuration
    validator = NginxConfigValidator(strict=args.strict)
    result = validator.validate_file(args.config_file)

    # Output results
    output = format_output(result, json_output=args.json)
    print(output)

    # Exit code
    sys.exit(0 if result.valid else 1)


if __name__ == '__main__':
    main()
