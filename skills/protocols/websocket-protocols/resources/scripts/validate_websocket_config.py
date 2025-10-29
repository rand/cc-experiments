#!/usr/bin/env python3
"""
WebSocket Configuration Validator

Validates WebSocket server configurations for nginx, HAProxy, and Envoy.
Checks security settings, performance tuning, and deployment best practices.

Usage:
    ./validate_websocket_config.py --config nginx.conf --type nginx
    ./validate_websocket_config.py --config haproxy.cfg --type haproxy --json
    ./validate_websocket_config.py --config envoy.yaml --type envoy --verbose
    ./validate_websocket_config.py --help

Requirements:
    pip install pyyaml
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
import yaml


@dataclass
class ValidationIssue:
    """Represents a configuration validation issue"""
    severity: str  # error, warning, info
    category: str  # security, performance, deployment, websocket
    component: str
    issue: str
    current_value: Optional[str]
    recommended_value: Optional[str]
    description: str
    line_number: Optional[int] = None


@dataclass
class ValidationResult:
    """Complete validation results"""
    config_type: str
    config_file: str
    status: str  # pass, warning, fail
    issues: List[ValidationIssue] = field(default_factory=list)
    websocket_enabled: bool = False
    tls_enabled: bool = False
    sticky_sessions_enabled: bool = False
    total_errors: int = 0
    total_warnings: int = 0
    total_info: int = 0


class BaseConfigValidator:
    """Base class for configuration validators"""

    def __init__(self, config_file: str, verbose: bool = False):
        self.config_file = config_file
        self.verbose = verbose
        self.issues: List[ValidationIssue] = []
        self.config_content = ""

    def load_config(self) -> bool:
        """Load configuration file"""
        try:
            path = Path(self.config_file)
            if not path.exists():
                self.add_issue(
                    severity="error",
                    category="deployment",
                    component="file",
                    issue="Configuration file not found",
                    description=f"File {self.config_file} does not exist"
                )
                return False

            self.config_content = path.read_text()
            return True
        except Exception as e:
            self.add_issue(
                severity="error",
                category="deployment",
                component="file",
                issue="Failed to read configuration file",
                description=str(e)
            )
            return False

    def add_issue(
        self,
        severity: str,
        category: str,
        component: str,
        issue: str,
        description: str,
        current_value: Optional[str] = None,
        recommended_value: Optional[str] = None,
        line_number: Optional[int] = None
    ):
        """Add validation issue"""
        self.issues.append(ValidationIssue(
            severity=severity,
            category=category,
            component=component,
            issue=issue,
            current_value=current_value,
            recommended_value=recommended_value,
            description=description,
            line_number=line_number
        ))

    def find_pattern(self, pattern: str, flags=0) -> Optional[re.Match]:
        """Find pattern in config"""
        return re.search(pattern, self.config_content, flags)

    def find_all_patterns(self, pattern: str, flags=0) -> List[re.Match]:
        """Find all pattern matches"""
        return re.findall(pattern, self.config_content, flags)

    def get_line_number(self, position: int) -> int:
        """Get line number from character position"""
        return self.config_content[:position].count('\n') + 1


class NginxConfigValidator(BaseConfigValidator):
    """Validator for nginx WebSocket configurations"""

    def validate(self) -> ValidationResult:
        """Run all validation checks"""
        if not self.load_config():
            return self.create_result()

        self.check_websocket_support()
        self.check_upstream_config()
        self.check_proxy_headers()
        self.check_timeouts()
        self.check_buffering()
        self.check_tls()
        self.check_sticky_sessions()
        self.check_connection_limits()
        self.check_security()

        return self.create_result()

    def check_websocket_support(self):
        """Check if WebSocket upgrade is configured"""
        upgrade_header = self.find_pattern(r'proxy_set_header\s+Upgrade\s+\$http_upgrade', re.IGNORECASE)
        connection_header = self.find_pattern(r'proxy_set_header\s+Connection\s+["\']?upgrade["\']?', re.IGNORECASE)

        if not upgrade_header or not connection_header:
            self.add_issue(
                severity="error",
                category="websocket",
                component="proxy_headers",
                issue="WebSocket upgrade headers missing",
                current_value="Not configured",
                recommended_value="proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection \"upgrade\";",
                description="WebSocket connections require Upgrade and Connection headers for protocol upgrade"
            )
        else:
            if self.verbose:
                self.add_issue(
                    severity="info",
                    category="websocket",
                    component="proxy_headers",
                    issue="WebSocket upgrade configured",
                    description="Upgrade and Connection headers are properly set"
                )

    def check_upstream_config(self):
        """Check upstream backend configuration"""
        upstream_blocks = self.find_all_patterns(r'upstream\s+(\w+)\s*{([^}]+)}', re.DOTALL)

        if not upstream_blocks:
            self.add_issue(
                severity="warning",
                category="deployment",
                component="upstream",
                issue="No upstream configuration found",
                description="Consider using upstream block for backend servers"
            )
            return

        for match in re.finditer(r'upstream\s+(\w+)\s*{([^}]+)}', self.config_content, re.DOTALL):
            upstream_name = match.group(1)
            upstream_config = match.group(2)

            # Check load balancing method
            if 'ip_hash' not in upstream_config and 'hash' not in upstream_config:
                self.add_issue(
                    severity="error",
                    category="websocket",
                    component=f"upstream_{upstream_name}",
                    issue="No sticky session mechanism configured",
                    current_value="None",
                    recommended_value="ip_hash; or hash $remote_addr consistent;",
                    description="WebSocket requires sticky sessions to route clients to same backend",
                    line_number=self.get_line_number(match.start())
                )

            # Check health checks
            if 'max_fails' not in upstream_config:
                self.add_issue(
                    severity="warning",
                    category="deployment",
                    component=f"upstream_{upstream_name}",
                    issue="No health check configuration",
                    recommended_value="max_fails=3 fail_timeout=30s",
                    description="Health checks help detect and remove failed backends",
                    line_number=self.get_line_number(match.start())
                )

    def check_proxy_headers(self):
        """Check required proxy headers"""
        required_headers = {
            'Host': r'proxy_set_header\s+Host\s+\$host',
            'X-Real-IP': r'proxy_set_header\s+X-Real-IP\s+\$remote_addr',
            'X-Forwarded-For': r'proxy_set_header\s+X-Forwarded-For\s+\$proxy_add_x_forwarded_for',
            'X-Forwarded-Proto': r'proxy_set_header\s+X-Forwarded-Proto\s+\$scheme'
        }

        for header_name, pattern in required_headers.items():
            if not self.find_pattern(pattern, re.IGNORECASE):
                self.add_issue(
                    severity="warning",
                    category="deployment",
                    component="proxy_headers",
                    issue=f"Missing {header_name} header",
                    recommended_value=f"proxy_set_header {header_name} (appropriate value);",
                    description=f"{header_name} header is recommended for proper proxying"
                )

    def check_timeouts(self):
        """Check timeout configurations"""
        timeout_configs = {
            'proxy_connect_timeout': {'min': 3600, 'recommended': 86400},  # 1 hour / 1 day
            'proxy_send_timeout': {'min': 3600, 'recommended': 86400},
            'proxy_read_timeout': {'min': 3600, 'recommended': 86400}
        }

        for timeout_name, limits in timeout_configs.items():
            pattern = rf'{timeout_name}\s+(\d+)([smhd]?)'
            match = self.find_pattern(pattern)

            if not match:
                self.add_issue(
                    severity="error",
                    category="websocket",
                    component="timeouts",
                    issue=f"{timeout_name} not configured",
                    recommended_value=f"{timeout_name} 7d;",
                    description="WebSocket connections are long-lived and require extended timeouts"
                )
            else:
                value = int(match.group(1))
                unit = match.group(2) or 's'

                # Convert to seconds
                multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
                value_seconds = value * multipliers.get(unit, 1)

                if value_seconds < limits['min']:
                    self.add_issue(
                        severity="warning",
                        category="websocket",
                        component="timeouts",
                        issue=f"{timeout_name} too short",
                        current_value=f"{value}{unit}",
                        recommended_value=f">= {limits['recommended']}s (1 day)",
                        description="Short timeouts may prematurely close WebSocket connections"
                    )

    def check_buffering(self):
        """Check buffering settings"""
        proxy_buffering = self.find_pattern(r'proxy_buffering\s+off', re.IGNORECASE)
        proxy_cache = self.find_pattern(r'proxy_cache\s+off', re.IGNORECASE)

        if not proxy_buffering:
            self.add_issue(
                severity="error",
                category="websocket",
                component="buffering",
                issue="proxy_buffering not disabled",
                current_value="Not set (default: on)",
                recommended_value="proxy_buffering off;",
                description="WebSocket requires buffering to be disabled for real-time communication"
            )

        if not proxy_cache:
            self.add_issue(
                severity="warning",
                category="websocket",
                component="buffering",
                issue="proxy_cache not explicitly disabled",
                recommended_value="proxy_cache off;",
                description="Explicitly disable caching for WebSocket endpoints"
            )

        # Check request buffering (nginx 1.7.11+)
        if not self.find_pattern(r'proxy_request_buffering\s+off', re.IGNORECASE):
            self.add_issue(
                severity="info",
                category="performance",
                component="buffering",
                issue="proxy_request_buffering not disabled",
                recommended_value="proxy_request_buffering off;",
                description="Disabling request buffering can improve WebSocket performance"
            )

    def check_tls(self):
        """Check TLS/SSL configuration"""
        ssl_cert = self.find_pattern(r'ssl_certificate\s+')
        ssl_key = self.find_pattern(r'ssl_certificate_key\s+')
        listen_ssl = self.find_pattern(r'listen\s+\d+\s+ssl', re.IGNORECASE)

        if not listen_ssl:
            self.add_issue(
                severity="error",
                category="security",
                component="tls",
                issue="TLS/SSL not enabled",
                recommended_value="listen 443 ssl http2;",
                description="WebSocket should use wss:// (TLS) in production for security"
            )
            return

        if not ssl_cert or not ssl_key:
            self.add_issue(
                severity="error",
                category="security",
                component="tls",
                issue="SSL certificate or key not configured",
                description="TLS enabled but certificate/key paths not set"
            )

        # Check SSL protocols
        ssl_protocols = self.find_pattern(r'ssl_protocols\s+([\w\s\.]+);')
        if ssl_protocols:
            protocols = ssl_protocols.group(1)
            if 'TLSv1 ' in protocols or 'TLSv1.1' in protocols:
                self.add_issue(
                    severity="warning",
                    category="security",
                    component="tls",
                    issue="Insecure TLS protocols enabled",
                    current_value=protocols,
                    recommended_value="TLSv1.2 TLSv1.3",
                    description="TLSv1.0 and TLSv1.1 are deprecated and insecure"
                )
        else:
            self.add_issue(
                severity="warning",
                category="security",
                component="tls",
                issue="SSL protocols not explicitly configured",
                recommended_value="ssl_protocols TLSv1.2 TLSv1.3;",
                description="Explicitly configure TLS protocols to ensure security"
            )

        # Check HTTP to HTTPS redirect
        http_server = self.find_pattern(r'listen\s+80\s*;')
        if http_server and not self.find_pattern(r'return\s+301\s+https://'):
            self.add_issue(
                severity="warning",
                category="security",
                component="tls",
                issue="No HTTP to HTTPS redirect",
                recommended_value="return 301 https://$server_name$request_uri;",
                description="Redirect HTTP traffic to HTTPS for security"
            )

    def check_sticky_sessions(self):
        """Check sticky session configuration"""
        upstream_blocks = re.finditer(r'upstream\s+\w+\s*{([^}]+)}', self.config_content, re.DOTALL)

        has_sticky = False
        for match in upstream_blocks:
            upstream_config = match.group(1)
            if 'ip_hash' in upstream_config or 'hash' in upstream_config:
                has_sticky = True
                break

        if not has_sticky:
            self.add_issue(
                severity="error",
                category="websocket",
                component="load_balancing",
                issue="Sticky sessions not configured",
                recommended_value="ip_hash; (in upstream block)",
                description="WebSocket connections must use sticky sessions to route to same backend"
            )

    def check_connection_limits(self):
        """Check connection limit configurations"""
        if not self.find_pattern(r'limit_conn_zone'):
            self.add_issue(
                severity="info",
                category="security",
                component="limits",
                issue="No connection limit zone defined",
                recommended_value="limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;",
                description="Connection limits help prevent abuse and DoS attacks"
            )

        if not self.find_pattern(r'limit_req_zone'):
            self.add_issue(
                severity="info",
                category="security",
                component="limits",
                issue="No request rate limit zone defined",
                recommended_value="limit_req_zone $binary_remote_addr zone=req_limit_per_ip:10m rate=10r/s;",
                description="Rate limits help prevent abuse during connection establishment"
            )

    def check_security(self):
        """Check general security settings"""
        # Check for security headers
        security_headers = {
            'X-Frame-Options': r'add_header\s+X-Frame-Options',
            'X-Content-Type-Options': r'add_header\s+X-Content-Type-Options',
            'X-XSS-Protection': r'add_header\s+X-XSS-Protection'
        }

        for header_name, pattern in security_headers.items():
            if not self.find_pattern(pattern, re.IGNORECASE):
                self.add_issue(
                    severity="info",
                    category="security",
                    component="headers",
                    issue=f"{header_name} header not set",
                    recommended_value=f"add_header {header_name} (appropriate value);",
                    description=f"Security header {header_name} helps protect against attacks"
                )

    def create_result(self) -> ValidationResult:
        """Create validation result"""
        errors = sum(1 for i in self.issues if i.severity == "error")
        warnings = sum(1 for i in self.issues if i.severity == "warning")
        info = sum(1 for i in self.issues if i.severity == "info")

        status = "pass"
        if errors > 0:
            status = "fail"
        elif warnings > 0:
            status = "warning"

        websocket_enabled = self.find_pattern(r'proxy_set_header\s+Upgrade\s+\$http_upgrade') is not None
        tls_enabled = self.find_pattern(r'listen\s+\d+\s+ssl') is not None
        sticky_sessions = any('ip_hash' in m or 'hash' in m
                             for m in self.find_all_patterns(r'upstream\s+\w+\s*{([^}]+)}', re.DOTALL))

        return ValidationResult(
            config_type="nginx",
            config_file=self.config_file,
            status=status,
            issues=self.issues,
            websocket_enabled=websocket_enabled,
            tls_enabled=tls_enabled,
            sticky_sessions_enabled=sticky_sessions,
            total_errors=errors,
            total_warnings=warnings,
            total_info=info
        )


class HAProxyConfigValidator(BaseConfigValidator):
    """Validator for HAProxy WebSocket configurations"""

    def validate(self) -> ValidationResult:
        """Run all validation checks"""
        if not self.load_config():
            return self.create_result()

        self.check_websocket_acl()
        self.check_backend_config()
        self.check_timeouts()
        self.check_health_checks()
        self.check_sticky_sessions()
        self.check_tls()
        self.check_balance_algorithm()

        return self.create_result()

    def check_websocket_acl(self):
        """Check WebSocket ACL configuration"""
        acl_upgrade = self.find_pattern(r'acl\s+\w+\s+hdr\(Upgrade\)\s+-i\s+websocket', re.IGNORECASE)
        use_backend = self.find_pattern(r'use_backend\s+\w+\s+if\s+\w+')

        if not acl_upgrade:
            self.add_issue(
                severity="warning",
                category="websocket",
                component="acl",
                issue="No WebSocket ACL defined",
                recommended_value="acl is_websocket hdr(Upgrade) -i websocket",
                description="ACL helps route WebSocket connections to appropriate backend"
            )

        if not use_backend and acl_upgrade:
            self.add_issue(
                severity="warning",
                category="websocket",
                component="routing",
                issue="WebSocket ACL defined but not used",
                recommended_value="use_backend websocket_back if is_websocket",
                description="Define backend routing based on WebSocket ACL"
            )

    def check_backend_config(self):
        """Check backend configuration"""
        backend_blocks = re.finditer(r'backend\s+(\w+)\s*\n((?:(?!^backend|^frontend|^global|^defaults)\s+.+\n)*)',
                                     self.config_content, re.MULTILINE)

        if not any(backend_blocks):
            self.add_issue(
                severity="error",
                category="deployment",
                component="backend",
                issue="No backend configuration found",
                description="HAProxy requires backend section for upstream servers"
            )
            return

        for match in re.finditer(r'backend\s+(\w+)\s*\n((?:(?!^backend|^frontend|^global|^defaults)\s+.+\n)*)',
                                 self.config_content, re.MULTILINE):
            backend_name = match.group(1)
            backend_config = match.group(2)

            # Check server definitions
            if 'server ' not in backend_config:
                self.add_issue(
                    severity="error",
                    category="deployment",
                    component=f"backend_{backend_name}",
                    issue="No servers defined in backend",
                    description="Backend must define at least one server",
                    line_number=self.get_line_number(match.start())
                )

    def check_timeouts(self):
        """Check timeout configurations"""
        timeout_configs = {
            'timeout tunnel': {'min': 3600, 'unit': 's'},
            'timeout server': {'min': 3600, 'unit': 's'},
            'timeout client': {'min': 3600, 'unit': 's'}
        }

        for timeout_name, limits in timeout_configs.items():
            pattern = rf'{timeout_name}\s+(\d+)([smhd]?)'
            match = self.find_pattern(pattern)

            if not match:
                self.add_issue(
                    severity="error",
                    category="websocket",
                    component="timeouts",
                    issue=f"{timeout_name} not configured",
                    recommended_value=f"{timeout_name} 3600s",
                    description="WebSocket connections require extended timeouts"
                )
            else:
                value = int(match.group(1))
                unit = match.group(2) or limits['unit']

                multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
                value_seconds = value * multipliers.get(unit, 1)

                if value_seconds < limits['min']:
                    self.add_issue(
                        severity="warning",
                        category="websocket",
                        component="timeouts",
                        issue=f"{timeout_name} too short",
                        current_value=f"{value}{unit}",
                        recommended_value=f">= {limits['min']}s",
                        description="Short timeouts may prematurely close WebSocket connections"
                    )

    def check_health_checks(self):
        """Check health check configuration"""
        backend_blocks = re.finditer(r'backend\s+(\w+)\s*\n((?:(?!^backend|^frontend|^global|^defaults)\s+.+\n)*)',
                                     self.config_content, re.MULTILINE)

        for match in backend_blocks:
            backend_name = match.group(1)
            backend_config = match.group(2)

            if 'option httpchk' not in backend_config:
                self.add_issue(
                    severity="warning",
                    category="deployment",
                    component=f"backend_{backend_name}",
                    issue="No health check configured",
                    recommended_value="option httpchk GET /health",
                    description="Health checks help detect and remove failed backends",
                    line_number=self.get_line_number(match.start())
                )

    def check_sticky_sessions(self):
        """Check sticky session configuration"""
        backend_blocks = re.finditer(r'backend\s+(\w+)\s*\n((?:(?!^backend|^frontend|^global|^defaults)\s+.+\n)*)',
                                     self.config_content, re.MULTILINE)

        for match in backend_blocks:
            backend_name = match.group(1)
            backend_config = match.group(2)

            has_sticky = ('balance source' in backend_config or
                         'stick-table' in backend_config or
                         'stick on' in backend_config)

            if not has_sticky:
                self.add_issue(
                    severity="error",
                    category="websocket",
                    component=f"backend_{backend_name}",
                    issue="Sticky sessions not configured",
                    recommended_value="balance source",
                    description="WebSocket connections must use sticky sessions",
                    line_number=self.get_line_number(match.start())
                )

    def check_tls(self):
        """Check TLS configuration"""
        frontend_ssl = self.find_pattern(r'bind\s+[^:]+:\d+\s+ssl', re.IGNORECASE)

        if not frontend_ssl:
            self.add_issue(
                severity="error",
                category="security",
                component="tls",
                issue="TLS not enabled on frontend",
                recommended_value="bind *:443 ssl crt /path/to/cert.pem",
                description="WebSocket should use wss:// (TLS) in production"
            )
            return

        # Check certificate
        if not self.find_pattern(r'bind\s+[^:]+:\d+\s+ssl\s+crt\s+'):
            self.add_issue(
                severity="error",
                category="security",
                component="tls",
                issue="SSL certificate not specified",
                description="TLS enabled but certificate path not set"
            )

        # Check HTTP redirect
        http_bind = self.find_pattern(r'bind\s+[^:]+:80\s')
        if http_bind and not self.find_pattern(r'redirect\s+scheme\s+https'):
            self.add_issue(
                severity="warning",
                category="security",
                component="tls",
                issue="No HTTP to HTTPS redirect",
                recommended_value="redirect scheme https if !{ ssl_fc }",
                description="Redirect HTTP traffic to HTTPS for security"
            )

    def check_balance_algorithm(self):
        """Check load balancing algorithm"""
        backend_blocks = re.finditer(r'backend\s+(\w+)\s*\n((?:(?!^backend|^frontend|^global|^defaults)\s+.+\n)*)',
                                     self.config_content, re.MULTILINE)

        for match in backend_blocks:
            backend_name = match.group(1)
            backend_config = match.group(2)

            if 'balance' not in backend_config:
                self.add_issue(
                    severity="warning",
                    category="deployment",
                    component=f"backend_{backend_name}",
                    issue="No load balancing algorithm specified",
                    recommended_value="balance source (or roundrobin for non-WebSocket)",
                    description="Explicitly configure load balancing algorithm",
                    line_number=self.get_line_number(match.start())
                )

    def create_result(self) -> ValidationResult:
        """Create validation result"""
        errors = sum(1 for i in self.issues if i.severity == "error")
        warnings = sum(1 for i in self.issues if i.severity == "warning")
        info = sum(1 for i in self.issues if i.severity == "info")

        status = "pass"
        if errors > 0:
            status = "fail"
        elif warnings > 0:
            status = "warning"

        websocket_enabled = self.find_pattern(r'acl\s+\w+\s+hdr\(Upgrade\)\s+-i\s+websocket') is not None
        tls_enabled = self.find_pattern(r'bind\s+[^:]+:\d+\s+ssl') is not None

        backend_blocks = list(re.finditer(r'backend\s+\w+\s*\n((?:(?!^backend|^frontend)\s+.+\n)*)',
                                         self.config_content, re.MULTILINE))
        sticky_sessions = any('balance source' in m.group(1) or 'stick' in m.group(1)
                             for m in backend_blocks)

        return ValidationResult(
            config_type="haproxy",
            config_file=self.config_file,
            status=status,
            issues=self.issues,
            websocket_enabled=websocket_enabled,
            tls_enabled=tls_enabled,
            sticky_sessions_enabled=sticky_sessions,
            total_errors=errors,
            total_warnings=warnings,
            total_info=info
        )


def format_output(result: ValidationResult, output_format: str = "text") -> str:
    """Format validation results"""
    if output_format == "json":
        return json.dumps(asdict(result), indent=2)

    # Text output
    lines = []
    lines.append(f"\n{'='*70}")
    lines.append(f"WebSocket Configuration Validation Report")
    lines.append(f"{'='*70}")
    lines.append(f"Config Type: {result.config_type.upper()}")
    lines.append(f"Config File: {result.config_file}")
    lines.append(f"Status: {result.status.upper()}")
    lines.append(f"")
    lines.append(f"WebSocket Enabled: {'✓' if result.websocket_enabled else '✗'}")
    lines.append(f"TLS Enabled: {'✓' if result.tls_enabled else '✗'}")
    lines.append(f"Sticky Sessions: {'✓' if result.sticky_sessions_enabled else '✗'}")
    lines.append(f"")
    lines.append(f"Issues Summary:")
    lines.append(f"  Errors:   {result.total_errors}")
    lines.append(f"  Warnings: {result.total_warnings}")
    lines.append(f"  Info:     {result.total_info}")

    if result.issues:
        lines.append(f"\n{'='*70}")
        lines.append(f"Detailed Issues")
        lines.append(f"{'='*70}\n")

        # Group by severity
        for severity in ['error', 'warning', 'info']:
            issues = [i for i in result.issues if i.severity == severity]
            if not issues:
                continue

            lines.append(f"\n{severity.upper()}S:")
            lines.append("-" * 70)

            for i, issue in enumerate(issues, 1):
                lines.append(f"\n{i}. [{issue.category.upper()}] {issue.component}")
                lines.append(f"   Issue: {issue.issue}")
                if issue.current_value:
                    lines.append(f"   Current: {issue.current_value}")
                if issue.recommended_value:
                    lines.append(f"   Recommended: {issue.recommended_value}")
                lines.append(f"   Description: {issue.description}")
                if issue.line_number:
                    lines.append(f"   Line: {issue.line_number}")

    lines.append(f"\n{'='*70}\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Validate WebSocket server configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate nginx configuration
  %(prog)s --config nginx.conf --type nginx

  # Validate HAProxy configuration with JSON output
  %(prog)s --config haproxy.cfg --type haproxy --json

  # Verbose output
  %(prog)s --config nginx.conf --type nginx --verbose

Supported configuration types:
  - nginx: nginx WebSocket proxy configuration
  - haproxy: HAProxy WebSocket load balancer configuration
        """
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Path to configuration file"
    )

    parser.add_argument(
        "--type",
        choices=["nginx", "haproxy"],
        required=True,
        help="Configuration type"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include informational messages"
    )

    args = parser.parse_args()

    # Create appropriate validator
    if args.type == "nginx":
        validator = NginxConfigValidator(args.config, verbose=args.verbose)
    elif args.type == "haproxy":
        validator = HAProxyConfigValidator(args.config, verbose=args.verbose)
    else:
        print(f"Error: Unsupported config type: {args.type}", file=sys.stderr)
        sys.exit(1)

    # Run validation
    result = validator.validate()

    # Output results
    output_format = "json" if args.json else "text"
    print(format_output(result, output_format))

    # Exit with appropriate code
    if result.status == "fail":
        sys.exit(1)
    elif result.status == "warning":
        sys.exit(0)  # Warnings don't fail
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
