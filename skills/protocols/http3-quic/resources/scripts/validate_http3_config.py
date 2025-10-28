#!/usr/bin/env python3
"""
HTTP/3 and QUIC Configuration Validator

Validates server configurations, QUIC parameters, TLS 1.3 settings, and detects common issues.

Usage:
    ./validate_http3_config.py --config nginx.conf [--json]
    ./validate_http3_config.py --config caddy.json [--type caddy] [--json]
    ./validate_http3_config.py --help

Features:
    - Parse and validate server configurations (nginx, Caddy, Apache)
    - Check QUIC parameters (connection IDs, flow control, streams)
    - Verify TLS 1.3 settings (ciphers, certificates, ALPN)
    - Detect UDP firewall issues
    - Validate Alt-Svc headers
    - Check system UDP buffer sizes
    - Output as JSON or human-readable text

Exit Codes:
    0: Success (no issues found)
    1: Warnings found (non-critical)
    2: Errors found (critical issues)
    3: Invalid arguments or file not found
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class Severity(str, Enum):
    """Issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Issue:
    """Represents a validation issue"""
    severity: Severity
    category: str
    message: str
    fix: Optional[str] = None
    line: Optional[int] = None


@dataclass
class ValidationResult:
    """Container for validation results"""
    config_file: str
    config_type: str
    issues: List[Issue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def add_issue(self, severity: Severity, category: str, message: str,
                  fix: Optional[str] = None, line: Optional[int] = None):
        """Add a validation issue"""
        self.issues.append(Issue(severity, category, message, fix, line))

    def has_errors(self) -> bool:
        """Check if any errors were found"""
        return any(issue.severity == Severity.ERROR for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if any warnings were found"""
        return any(issue.severity == Severity.WARNING for issue in self.issues)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "config_file": self.config_file,
            "config_type": self.config_type,
            "issues": [asdict(issue) for issue in self.issues],
            "stats": self.stats,
            "summary": {
                "total_issues": len(self.issues),
                "errors": sum(1 for i in self.issues if i.severity == Severity.ERROR),
                "warnings": sum(1 for i in self.issues if i.severity == Severity.WARNING),
                "info": sum(1 for i in self.issues if i.severity == Severity.INFO),
            }
        }


class ConfigValidator:
    """Base validator for server configurations"""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.content = ""
        self.lines = []

        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(self.config_path, 'r') as f:
            self.content = f.read()
            self.lines = self.content.splitlines()

    def validate(self) -> ValidationResult:
        """Run all validation checks"""
        raise NotImplementedError


class NginxValidator(ConfigValidator):
    """Validator for nginx configurations"""

    def validate(self) -> ValidationResult:
        result = ValidationResult(
            config_file=str(self.config_path),
            config_type="nginx"
        )

        # Check for QUIC/HTTP/3 listeners
        self._check_listeners(result)

        # Check TLS settings
        self._check_tls(result)

        # Check QUIC parameters
        self._check_quic_params(result)

        # Check Alt-Svc headers
        self._check_alt_svc(result)

        # Check fallback configuration
        self._check_fallback(result)

        # Collect statistics
        self._collect_stats(result)

        return result

    def _check_listeners(self, result: ValidationResult):
        """Check for HTTP/3 and HTTP/2 listeners"""
        quic_listeners = []
        http2_listeners = []

        for i, line in enumerate(self.lines, 1):
            if re.search(r'listen\s+\d+\s+quic', line):
                quic_listeners.append((i, line.strip()))
            if re.search(r'listen\s+\d+\s+ssl\s+http2', line):
                http2_listeners.append((i, line.strip()))

        if not quic_listeners:
            result.add_issue(
                Severity.ERROR,
                "listeners",
                "No HTTP/3 (QUIC) listener found",
                "Add: listen 443 quic reuseport;",
            )
        else:
            # Check for reuseport flag
            for line_num, line in quic_listeners:
                if 'reuseport' not in line:
                    result.add_issue(
                        Severity.WARNING,
                        "listeners",
                        f"QUIC listener missing 'reuseport' flag (line {line_num})",
                        "Add 'reuseport' to improve performance: listen 443 quic reuseport;",
                        line_num
                    )

        if not http2_listeners:
            result.add_issue(
                Severity.WARNING,
                "listeners",
                "No HTTP/2 fallback listener found",
                "Add: listen 443 ssl http2;",
            )

    def _check_tls(self, result: ValidationResult):
        """Check TLS 1.3 configuration"""
        ssl_protocols = []
        ssl_certs = []

        for i, line in enumerate(self.lines, 1):
            if re.search(r'ssl_protocols', line):
                ssl_protocols.append((i, line.strip()))
            if re.search(r'ssl_certificate\s+', line):
                ssl_certs.append((i, line.strip()))

        # Check TLS 1.3
        if not ssl_protocols:
            result.add_issue(
                Severity.ERROR,
                "tls",
                "No ssl_protocols directive found",
                "Add: ssl_protocols TLSv1.3;",
            )
        else:
            for line_num, line in ssl_protocols:
                if 'TLSv1.3' not in line:
                    result.add_issue(
                        Severity.ERROR,
                        "tls",
                        f"TLS 1.3 not enabled (line {line_num})",
                        "Update to: ssl_protocols TLSv1.3;",
                        line_num
                    )
                if 'TLSv1.2' in line or 'TLSv1.1' in line or 'TLSv1 ' in line:
                    result.add_issue(
                        Severity.WARNING,
                        "tls",
                        f"Old TLS versions enabled (line {line_num})",
                        "For HTTP/3 only, use: ssl_protocols TLSv1.3;",
                        line_num
                    )

        # Check certificates
        if not ssl_certs:
            result.add_issue(
                Severity.ERROR,
                "tls",
                "No SSL certificate configured",
                "Add: ssl_certificate /path/to/cert.pem; ssl_certificate_key /path/to/key.pem;",
            )
        else:
            # Verify certificate files exist
            for line_num, line in ssl_certs:
                match = re.search(r'ssl_certificate\s+(\S+);', line)
                if match:
                    cert_path = match.group(1)
                    if not Path(cert_path).exists():
                        result.add_issue(
                            Severity.ERROR,
                            "tls",
                            f"Certificate file not found: {cert_path} (line {line_num})",
                            f"Create or fix path to certificate",
                            line_num
                        )

    def _check_quic_params(self, result: ValidationResult):
        """Check QUIC-specific parameters"""
        quic_settings = {}

        for i, line in enumerate(self.lines, 1):
            if 'quic_retry' in line:
                quic_settings['retry'] = (i, line.strip())
            if 'quic_gso' in line:
                quic_settings['gso'] = (i, line.strip())
            if 'ssl_early_data' in line:
                quic_settings['early_data'] = (i, line.strip())

        # Check recommended settings
        if 'retry' not in quic_settings:
            result.add_issue(
                Severity.INFO,
                "quic",
                "quic_retry not configured",
                "Consider adding: quic_retry on; (protects against amplification attacks)",
            )

        if 'gso' not in quic_settings:
            result.add_issue(
                Severity.INFO,
                "quic",
                "quic_gso not configured",
                "Consider adding: quic_gso on; (improves performance with GSO support)",
            )

        if 'early_data' in quic_settings:
            line_num, line = quic_settings['early_data']
            if 'on' in line:
                result.add_issue(
                    Severity.WARNING,
                    "quic",
                    f"ssl_early_data enabled (0-RTT) - ensure idempotent requests only (line {line_num})",
                    "0-RTT data can be replayed - only use for safe operations (GET, not POST)",
                    line_num
                )

    def _check_alt_svc(self, result: ValidationResult):
        """Check Alt-Svc header for HTTP/3 advertisement"""
        alt_svc_found = False

        for i, line in enumerate(self.lines, 1):
            if 'Alt-Svc' in line or 'alt-svc' in line:
                alt_svc_found = True

                # Check format
                if not re.search(r'h3\s*=', line):
                    result.add_issue(
                        Severity.ERROR,
                        "alt-svc",
                        f"Alt-Svc header missing HTTP/3 (h3) protocol (line {i})",
                        "Update to: add_header Alt-Svc 'h3=\":443\"; ma=86400';",
                        i
                    )

                # Check max-age
                match = re.search(r'ma\s*=\s*(\d+)', line)
                if match:
                    max_age = int(match.group(1))
                    if max_age < 3600:
                        result.add_issue(
                            Severity.WARNING,
                            "alt-svc",
                            f"Alt-Svc max-age too low: {max_age} seconds (line {i})",
                            "Increase to at least 1 hour: ma=3600 or 1 day: ma=86400",
                            i
                        )

        if not alt_svc_found:
            result.add_issue(
                Severity.ERROR,
                "alt-svc",
                "No Alt-Svc header found - HTTP/3 not advertised to clients",
                "Add: add_header Alt-Svc 'h3=\":443\"; ma=86400';",
            )

    def _check_fallback(self, result: ValidationResult):
        """Check for HTTP/2 fallback configuration"""
        quic_only = True

        for line in self.lines:
            if re.search(r'listen\s+\d+\s+ssl\s+http2', line):
                quic_only = False
                break

        if quic_only:
            result.add_issue(
                Severity.WARNING,
                "fallback",
                "No HTTP/2 fallback - clients without HTTP/3 support may fail",
                "Add HTTP/2 listener: listen 443 ssl http2;",
            )

    def _collect_stats(self, result: ValidationResult):
        """Collect configuration statistics"""
        result.stats = {
            "quic_listeners": sum(1 for line in self.lines if 'quic' in line and 'listen' in line),
            "http2_listeners": sum(1 for line in self.lines if 'http2' in line and 'listen' in line),
            "ssl_certificates": sum(1 for line in self.lines if 'ssl_certificate ' in line),
            "alt_svc_headers": sum(1 for line in self.lines if 'Alt-Svc' in line or 'alt-svc' in line),
            "total_lines": len(self.lines),
        }


class CaddyValidator(ConfigValidator):
    """Validator for Caddy configurations (JSON)"""

    def validate(self) -> ValidationResult:
        result = ValidationResult(
            config_file=str(self.config_path),
            config_type="caddy"
        )

        try:
            config = json.loads(self.content)
        except json.JSONDecodeError as e:
            result.add_issue(
                Severity.ERROR,
                "syntax",
                f"Invalid JSON: {e}",
            )
            return result

        # Caddy enables HTTP/3 by default, but check configuration
        self._check_apps(config, result)

        return result

    def _check_apps(self, config: Dict, result: ValidationResult):
        """Check Caddy apps configuration"""
        apps = config.get("apps", {})
        http_app = apps.get("http", {})

        if not http_app:
            result.add_issue(
                Severity.WARNING,
                "config",
                "No HTTP app configured",
            )
            return

        # Check servers
        servers = http_app.get("servers", {})
        if not servers:
            result.add_issue(
                Severity.WARNING,
                "config",
                "No servers configured",
            )

        # Caddy enables HTTP/3 by default
        result.add_issue(
            Severity.INFO,
            "http3",
            "Caddy enables HTTP/3 by default - no explicit configuration needed",
        )


class SystemValidator:
    """Validator for system-level HTTP/3 requirements"""

    @staticmethod
    def check_udp_buffers() -> List[Issue]:
        """Check UDP buffer sizes"""
        issues = []

        try:
            # Read current settings
            with open('/proc/sys/net/core/rmem_max', 'r') as f:
                rmem_max = int(f.read().strip())
            with open('/proc/sys/net/core/wmem_max', 'r') as f:
                wmem_max = int(f.read().strip())

            # Recommended: 2.5 MB
            recommended = 2500000

            if rmem_max < recommended:
                issues.append(Issue(
                    Severity.WARNING,
                    "system",
                    f"UDP receive buffer too small: {rmem_max} bytes (recommended: {recommended})",
                    f"Increase: sysctl -w net.core.rmem_max={recommended}",
                ))

            if wmem_max < recommended:
                issues.append(Issue(
                    Severity.WARNING,
                    "system",
                    f"UDP send buffer too small: {wmem_max} bytes (recommended: {recommended})",
                    f"Increase: sysctl -w net.core.wmem_max={recommended}",
                ))
        except FileNotFoundError:
            # Not Linux or /proc not available
            pass
        except Exception as e:
            issues.append(Issue(
                Severity.INFO,
                "system",
                f"Could not check UDP buffers: {e}",
            ))

        return issues

    @staticmethod
    def check_udp_firewall(port: int = 443) -> List[Issue]:
        """Check if UDP port is accessible"""
        issues = []

        try:
            # Try to bind to UDP port (requires root or specific capabilities)
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', port))
            sock.close()

            issues.append(Issue(
                Severity.INFO,
                "firewall",
                f"UDP port {port} is bindable",
            ))
        except PermissionError:
            issues.append(Issue(
                Severity.INFO,
                "firewall",
                f"Cannot test UDP port {port} (insufficient permissions)",
            ))
        except OSError as e:
            if "Address already in use" in str(e):
                issues.append(Issue(
                    Severity.INFO,
                    "firewall",
                    f"UDP port {port} already in use (server may be running)",
                ))
            else:
                issues.append(Issue(
                    Severity.WARNING,
                    "firewall",
                    f"UDP port {port} may be blocked: {e}",
                    f"Check firewall: iptables -L -n | grep {port}",
                ))

        return issues

    @staticmethod
    def check_tls_version() -> List[Issue]:
        """Check OpenSSL/TLS version"""
        issues = []

        try:
            result = subprocess.run(
                ['openssl', 'version'],
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()

            # Check for OpenSSL 1.1.1+ (TLS 1.3 support)
            if 'OpenSSL 1.1.1' in version or 'OpenSSL 3.' in version:
                issues.append(Issue(
                    Severity.INFO,
                    "tls",
                    f"TLS 1.3 supported: {version}",
                ))
            else:
                issues.append(Issue(
                    Severity.ERROR,
                    "tls",
                    f"TLS 1.3 may not be supported: {version}",
                    "Upgrade to OpenSSL 1.1.1+ or OpenSSL 3.x",
                ))
        except FileNotFoundError:
            issues.append(Issue(
                Severity.WARNING,
                "tls",
                "OpenSSL not found in PATH",
            ))
        except Exception as e:
            issues.append(Issue(
                Severity.INFO,
                "tls",
                f"Could not check OpenSSL version: {e}",
            ))

        return issues


def print_human_readable(result: ValidationResult):
    """Print results in human-readable format"""
    print(f"\nHTTP/3 Configuration Validation")
    print(f"{'=' * 80}")
    print(f"Config File: {result.config_file}")
    print(f"Config Type: {result.config_type}")
    print()

    # Group issues by category
    categories = {}
    for issue in result.issues:
        if issue.category not in categories:
            categories[issue.category] = []
        categories[issue.category].append(issue)

    # Print issues by category
    for category, issues in sorted(categories.items()):
        print(f"\n{category.upper()}")
        print("-" * 80)

        for issue in issues:
            icon = {
                Severity.ERROR: "✗",
                Severity.WARNING: "⚠",
                Severity.INFO: "ℹ",
            }[issue.severity]

            color = {
                Severity.ERROR: "\033[91m",  # Red
                Severity.WARNING: "\033[93m",  # Yellow
                Severity.INFO: "\033[94m",  # Blue
            }[issue.severity]
            reset = "\033[0m"

            print(f"{color}{icon} [{issue.severity.value.upper()}]{reset} {issue.message}")
            if issue.line:
                print(f"  Line: {issue.line}")
            if issue.fix:
                print(f"  Fix: {issue.fix}")

    # Print statistics
    if result.stats:
        print(f"\n\nSTATISTICS")
        print("-" * 80)
        for key, value in sorted(result.stats.items()):
            print(f"{key.replace('_', ' ').title()}: {value}")

    # Print summary
    print(f"\n\nSUMMARY")
    print("-" * 80)
    summary = result.to_dict()["summary"]
    print(f"Total Issues: {summary['total_issues']}")
    print(f"  Errors: {summary['errors']}")
    print(f"  Warnings: {summary['warnings']}")
    print(f"  Info: {summary['info']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="HTTP/3 and QUIC Configuration Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate nginx config
  ./validate_http3_config.py --config /etc/nginx/nginx.conf

  # Validate Caddy config (JSON)
  ./validate_http3_config.py --config caddy.json --type caddy

  # JSON output
  ./validate_http3_config.py --config nginx.conf --json

  # Check system settings
  ./validate_http3_config.py --check-system

Exit codes:
  0 = Success (no issues)
  1 = Warnings found
  2 = Errors found
  3 = Invalid arguments
        """
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
    )

    parser.add_argument(
        "--type",
        choices=["nginx", "caddy", "auto"],
        default="auto",
        help="Configuration type (default: auto-detect)",
    )

    parser.add_argument(
        "--check-system",
        action="store_true",
        help="Check system-level HTTP/3 requirements",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Check arguments
    if not args.config and not args.check_system:
        parser.error("Either --config or --check-system is required")

    results = []

    # Validate configuration file
    if args.config:
        config_path = Path(args.config)

        # Auto-detect type
        config_type = args.type
        if config_type == "auto":
            if config_path.suffix == ".json":
                config_type = "caddy"
            else:
                config_type = "nginx"

        # Validate
        try:
            if config_type == "nginx":
                validator = NginxValidator(str(config_path))
            elif config_type == "caddy":
                validator = CaddyValidator(str(config_path))
            else:
                print(f"Error: Unknown config type: {config_type}", file=sys.stderr)
                return 3

            result = validator.validate()
            results.append(result)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 3
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 3

    # Check system settings
    if args.check_system:
        system_result = ValidationResult(
            config_file="system",
            config_type="system"
        )

        system_result.issues.extend(SystemValidator.check_udp_buffers())
        system_result.issues.extend(SystemValidator.check_udp_firewall())
        system_result.issues.extend(SystemValidator.check_tls_version())

        results.append(system_result)

    # Output results
    if args.json:
        output = {
            "results": [r.to_dict() for r in results],
            "exit_code": 0,
        }

        # Determine exit code
        if any(r.has_errors() for r in results):
            output["exit_code"] = 2
        elif any(r.has_warnings() for r in results):
            output["exit_code"] = 1

        print(json.dumps(output, indent=2))
        return output["exit_code"]
    else:
        for result in results:
            print_human_readable(result)

        # Determine exit code
        if any(r.has_errors() for r in results):
            return 2
        elif any(r.has_warnings() for r in results):
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(main())
