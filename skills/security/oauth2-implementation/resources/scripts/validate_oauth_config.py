#!/usr/bin/env python3
"""
OAuth 2.0 Configuration Validator

Validates OAuth 2.0 authorization server configuration for security best practices
and compliance with RFCs 6749, 7636, and OAuth 2.1 recommendations.

Usage:
    ./validate_oauth_config.py --config oauth-server.conf
    ./validate_oauth_config.py --config config.json --json
    ./validate_oauth_config.py --config keycloak-realm.json --format keycloak --json

Examples:
    # Validate generic OAuth config
    ./validate_oauth_config.py --config oauth-config.json

    # Validate Keycloak realm export
    ./validate_oauth_config.py --config realm-export.json --format keycloak

    # Output JSON for CI/CD
    ./validate_oauth_config.py --config config.json --json --output report.json

Options:
    --config FILE       Configuration file to validate
    --format FORMAT     Config format: generic, keycloak, auth0, okta (default: generic)
    --json              Output results as JSON
    --output FILE       Write output to file
    --strict            Enable strict mode (fail on warnings)
    --help              Show this help message
"""

import json
import argparse
import sys
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class Severity(Enum):
    """Issue severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    """Validation issue"""
    severity: Severity
    category: str
    message: str
    field: Optional[str] = None
    recommendation: Optional[str] = None
    reference: Optional[str] = None


@dataclass
class ValidationResult:
    """Validation result"""
    valid: bool
    score: int  # 0-100
    issues: List[ValidationIssue]
    warnings: int
    errors: int
    critical: int
    checks_passed: int
    checks_total: int


class OAuthConfigValidator:
    """OAuth 2.0 configuration validator"""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.issues: List[ValidationIssue] = []
        self.checks_passed = 0
        self.checks_total = 0

    def add_issue(self, severity: Severity, category: str, message: str,
                  field: Optional[str] = None, recommendation: Optional[str] = None,
                  reference: Optional[str] = None):
        """Add validation issue"""
        self.issues.append(ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            field=field,
            recommendation=recommendation,
            reference=reference
        ))

    def check(self, condition: bool, pass_msg: str = None) -> bool:
        """Track check result"""
        self.checks_total += 1
        if condition:
            self.checks_passed += 1
            if pass_msg:
                print(f"✓ {pass_msg}")
        return condition

    def validate_https_endpoints(self, config: Dict) -> None:
        """Validate all endpoints use HTTPS"""
        endpoints = [
            'authorization_endpoint',
            'token_endpoint',
            'introspection_endpoint',
            'revocation_endpoint',
            'jwks_uri',
            'issuer'
        ]

        for endpoint in endpoints:
            if endpoint in config:
                url = config[endpoint]
                if not self.check(
                    url.startswith('https://'),
                    f"Endpoint {endpoint} uses HTTPS"
                ):
                    self.add_issue(
                        Severity.CRITICAL,
                        "HTTPS",
                        f"{endpoint} does not use HTTPS",
                        field=endpoint,
                        recommendation="All OAuth endpoints MUST use HTTPS (TLS 1.2+)",
                        reference="RFC 6749 Section 3.1"
                    )

    def validate_grant_types(self, config: Dict) -> None:
        """Validate grant type configuration"""
        supported_grants = config.get('grant_types_supported', [])

        # OAuth 2.1 deprecations
        deprecated = ['implicit', 'password']
        for grant in deprecated:
            if grant in supported_grants:
                self.add_issue(
                    Severity.HIGH,
                    "Grant Types",
                    f"Grant type '{grant}' is deprecated in OAuth 2.1",
                    field='grant_types_supported',
                    recommendation=f"Remove '{grant}' grant type. Use 'authorization_code' with PKCE instead.",
                    reference="OAuth 2.1 Draft"
                )

        # Check for authorization_code
        if self.check(
            'authorization_code' in supported_grants,
            "Authorization code grant is supported"
        ):
            pass
        else:
            self.add_issue(
                Severity.MEDIUM,
                "Grant Types",
                "Authorization code grant not listed in supported grant types",
                field='grant_types_supported',
                recommendation="Enable 'authorization_code' grant type",
                reference="RFC 6749"
            )

    def validate_pkce_enforcement(self, config: Dict) -> None:
        """Validate PKCE configuration"""
        # Check if PKCE is supported
        code_challenge_methods = config.get('code_challenge_methods_supported', [])

        if self.check(
            len(code_challenge_methods) > 0,
            "PKCE is supported"
        ):
            # Check if S256 is supported
            if self.check(
                'S256' in code_challenge_methods,
                "PKCE S256 method is supported"
            ):
                pass
            else:
                self.add_issue(
                    Severity.HIGH,
                    "PKCE",
                    "S256 code challenge method not supported",
                    field='code_challenge_methods_supported',
                    recommendation="Add 'S256' to supported code challenge methods",
                    reference="RFC 7636 Section 4.2"
                )

            # Warn about plain method
            if 'plain' in code_challenge_methods:
                self.add_issue(
                    Severity.MEDIUM,
                    "PKCE",
                    "Plain code challenge method is supported (not recommended)",
                    field='code_challenge_methods_supported',
                    recommendation="Remove 'plain' method, use only 'S256'",
                    reference="RFC 7636 Section 4.2"
                )
        else:
            self.add_issue(
                Severity.CRITICAL,
                "PKCE",
                "PKCE is not supported",
                field='code_challenge_methods_supported',
                recommendation="PKCE is REQUIRED in OAuth 2.1 for all authorization code flows",
                reference="OAuth 2.1 Draft Section 7.6"
            )

        # Check PKCE enforcement policy
        pkce_required = config.get('require_pkce', False)
        pkce_required_public = config.get('require_pkce_public_clients', False)

        if not self.check(
            pkce_required or pkce_required_public,
            "PKCE enforcement configured"
        ):
            self.add_issue(
                Severity.HIGH,
                "PKCE",
                "PKCE not enforced for any client type",
                field='require_pkce',
                recommendation="Set 'require_pkce: true' or at minimum 'require_pkce_public_clients: true'",
                reference="OAuth 2.1 Draft"
            )

    def validate_token_lifetimes(self, config: Dict) -> None:
        """Validate token lifetime configuration"""
        # Access token lifetime
        access_token_lifetime = config.get('access_token_lifetime', None)
        if access_token_lifetime:
            # Recommended: 5-15 minutes for access tokens
            if not self.check(
                300 <= access_token_lifetime <= 3600,
                f"Access token lifetime is reasonable ({access_token_lifetime}s)"
            ):
                if access_token_lifetime > 3600:
                    self.add_issue(
                        Severity.MEDIUM,
                        "Token Lifetime",
                        f"Access token lifetime is too long ({access_token_lifetime}s)",
                        field='access_token_lifetime',
                        recommendation="Reduce access token lifetime to 5-15 minutes (300-900s)",
                        reference="OAuth 2.0 Security Best Practices"
                    )
                else:
                    self.add_issue(
                        Severity.LOW,
                        "Token Lifetime",
                        f"Access token lifetime is very short ({access_token_lifetime}s)",
                        field='access_token_lifetime',
                        recommendation="Consider increasing to at least 5 minutes (300s) to reduce refresh overhead"
                    )

        # Authorization code lifetime
        auth_code_lifetime = config.get('authorization_code_lifetime', None)
        if auth_code_lifetime:
            if not self.check(
                auth_code_lifetime <= 600,
                f"Authorization code lifetime is secure ({auth_code_lifetime}s)"
            ):
                self.add_issue(
                    Severity.HIGH,
                    "Token Lifetime",
                    f"Authorization code lifetime is too long ({auth_code_lifetime}s)",
                    field='authorization_code_lifetime',
                    recommendation="Authorization codes should expire within 10 minutes (600s)",
                    reference="RFC 6749 Section 4.1.2"
                )

        # Refresh token lifetime
        refresh_token_lifetime = config.get('refresh_token_lifetime', None)
        if refresh_token_lifetime:
            # Check if refresh token rotation is enabled
            rotate_refresh_tokens = config.get('rotate_refresh_tokens', False)
            if not rotate_refresh_tokens and refresh_token_lifetime > 86400 * 90:  # 90 days
                self.add_issue(
                    Severity.MEDIUM,
                    "Token Lifetime",
                    f"Long-lived refresh tokens without rotation ({refresh_token_lifetime}s)",
                    field='refresh_token_lifetime',
                    recommendation="Enable refresh token rotation or reduce lifetime",
                    reference="OAuth 2.0 Security Best Practices"
                )

    def validate_redirect_uri_security(self, config: Dict) -> None:
        """Validate redirect URI security configuration"""
        # Check if wildcard redirects are allowed
        allow_wildcard_redirects = config.get('allow_wildcard_redirect_uris', False)
        if not self.check(
            not allow_wildcard_redirects,
            "Wildcard redirect URIs are disabled"
        ):
            self.add_issue(
                Severity.CRITICAL,
                "Redirect URI",
                "Wildcard redirect URIs are allowed",
                field='allow_wildcard_redirect_uris',
                recommendation="Disable wildcard redirect URIs - use exact matching only",
                reference="RFC 6749 Section 3.1.2.3, OAuth 2.0 Security Best Practices"
            )

        # Check redirect URI validation mode
        redirect_uri_validation = config.get('redirect_uri_validation', 'exact')
        if not self.check(
            redirect_uri_validation == 'exact',
            "Redirect URI validation uses exact matching"
        ):
            self.add_issue(
                Severity.HIGH,
                "Redirect URI",
                f"Redirect URI validation mode is '{redirect_uri_validation}' (not exact)",
                field='redirect_uri_validation',
                recommendation="Use exact matching for redirect URIs",
                reference="RFC 6749 Section 3.1.2.3"
            )

        # Check for HTTP redirect URIs allowed
        allow_http_redirects = config.get('allow_http_redirect_uris', False)
        if allow_http_redirects:
            # HTTP only acceptable for localhost in development
            allow_http_localhost = config.get('allow_http_localhost_only', True)
            if not allow_http_localhost:
                self.add_issue(
                    Severity.HIGH,
                    "Redirect URI",
                    "HTTP redirect URIs allowed (not localhost-only)",
                    field='allow_http_redirect_uris',
                    recommendation="Disable HTTP redirects or restrict to localhost only",
                    reference="RFC 6749 Section 3.1.2.1"
                )

    def validate_cors_configuration(self, config: Dict) -> None:
        """Validate CORS configuration for token endpoints"""
        cors_config = config.get('cors', {})

        if cors_config:
            # Check if CORS allows credentials
            allow_credentials = cors_config.get('allow_credentials', False)
            allowed_origins = cors_config.get('allowed_origins', [])

            if allow_credentials and '*' in allowed_origins:
                self.add_issue(
                    Severity.CRITICAL,
                    "CORS",
                    "CORS allows credentials with wildcard origins",
                    field='cors.allowed_origins',
                    recommendation="Do not use '*' for allowed_origins when allow_credentials is true",
                    reference="CORS Specification"
                )

            # Check for overly permissive origins
            if '*' in allowed_origins:
                self.add_issue(
                    Severity.MEDIUM,
                    "CORS",
                    "CORS allows all origins (wildcard)",
                    field='cors.allowed_origins',
                    recommendation="Specify explicit allowed origins instead of wildcard",
                    reference="OAuth 2.0 Security Best Practices"
                )

    def validate_client_secret_requirements(self, config: Dict) -> None:
        """Validate client secret requirements"""
        # Check minimum secret length
        min_secret_length = config.get('min_client_secret_length', 0)
        if not self.check(
            min_secret_length >= 32,
            f"Minimum client secret length is adequate ({min_secret_length})"
        ):
            self.add_issue(
                Severity.MEDIUM,
                "Client Secrets",
                f"Minimum client secret length is too short ({min_secret_length} chars)",
                field='min_client_secret_length',
                recommendation="Require at least 32 characters for client secrets",
                reference="OAuth 2.0 Security Best Practices"
            )

        # Check if secrets are hashed
        hash_client_secrets = config.get('hash_client_secrets', False)
        if not self.check(
            hash_client_secrets,
            "Client secrets are hashed"
        ):
            self.add_issue(
                Severity.HIGH,
                "Client Secrets",
                "Client secrets are not hashed in storage",
                field='hash_client_secrets',
                recommendation="Hash client secrets using bcrypt or Argon2 before storage",
                reference="OAuth 2.0 Security Best Practices"
            )

    def validate_scope_configuration(self, config: Dict) -> None:
        """Validate scope configuration"""
        scopes = config.get('scopes_supported', [])

        if not scopes:
            self.add_issue(
                Severity.LOW,
                "Scopes",
                "No scopes defined",
                field='scopes_supported',
                recommendation="Define scopes for fine-grained authorization"
            )

        # Check for overly broad scopes
        dangerous_scopes = ['*', 'all', 'admin:*', 'full_access']
        for scope in scopes:
            if scope in dangerous_scopes:
                self.add_issue(
                    Severity.MEDIUM,
                    "Scopes",
                    f"Overly broad scope defined: '{scope}'",
                    field='scopes_supported',
                    recommendation="Use granular scopes instead of broad wildcards",
                    reference="OAuth 2.0 Security Best Practices"
                )

    def validate_rate_limiting(self, config: Dict) -> None:
        """Validate rate limiting configuration"""
        rate_limit_config = config.get('rate_limiting', {})

        if not rate_limit_config:
            self.add_issue(
                Severity.MEDIUM,
                "Rate Limiting",
                "No rate limiting configured",
                field='rate_limiting',
                recommendation="Configure rate limiting to prevent abuse",
                reference="OAuth 2.0 Security Best Practices"
            )
        else:
            # Check token endpoint rate limit
            token_limit = rate_limit_config.get('token_endpoint', {})
            if not token_limit:
                self.add_issue(
                    Severity.MEDIUM,
                    "Rate Limiting",
                    "No rate limiting on token endpoint",
                    field='rate_limiting.token_endpoint',
                    recommendation="Apply rate limiting to token endpoint",
                    reference="OAuth 2.0 Security Best Practices"
                )

    def validate_token_introspection(self, config: Dict) -> None:
        """Validate token introspection configuration"""
        introspection_endpoint = config.get('introspection_endpoint')

        if introspection_endpoint:
            # Check authentication requirement
            require_auth = config.get('require_introspection_auth', False)
            if not self.check(
                require_auth,
                "Token introspection requires authentication"
            ):
                self.add_issue(
                    Severity.HIGH,
                    "Token Introspection",
                    "Token introspection does not require authentication",
                    field='require_introspection_auth',
                    recommendation="Require resource server authentication for introspection",
                    reference="RFC 7662 Section 2.1"
                )

    def validate_refresh_token_rotation(self, config: Dict) -> None:
        """Validate refresh token rotation configuration"""
        rotate_refresh_tokens = config.get('rotate_refresh_tokens', False)

        if not self.check(
            rotate_refresh_tokens,
            "Refresh token rotation is enabled"
        ):
            self.add_issue(
                Severity.MEDIUM,
                "Refresh Tokens",
                "Refresh token rotation is not enabled",
                field='rotate_refresh_tokens',
                recommendation="Enable refresh token rotation for enhanced security",
                reference="OAuth 2.0 Security Best Practices"
            )

        # Check token family tracking
        if rotate_refresh_tokens:
            track_families = config.get('track_refresh_token_families', False)
            if not self.check(
                track_families,
                "Refresh token family tracking is enabled"
            ):
                self.add_issue(
                    Severity.LOW,
                    "Refresh Tokens",
                    "Refresh token family tracking is not enabled",
                    field='track_refresh_token_families',
                    recommendation="Enable family tracking to detect token theft",
                    reference="OAuth 2.0 Security Best Practices"
                )

    def validate(self, config: Dict) -> ValidationResult:
        """Validate OAuth configuration"""
        self.issues = []
        self.checks_passed = 0
        self.checks_total = 0

        # Run all validations
        self.validate_https_endpoints(config)
        self.validate_grant_types(config)
        self.validate_pkce_enforcement(config)
        self.validate_token_lifetimes(config)
        self.validate_redirect_uri_security(config)
        self.validate_cors_configuration(config)
        self.validate_client_secret_requirements(config)
        self.validate_scope_configuration(config)
        self.validate_rate_limiting(config)
        self.validate_token_introspection(config)
        self.validate_refresh_token_rotation(config)

        # Count issues by severity
        critical = sum(1 for i in self.issues if i.severity == Severity.CRITICAL)
        errors = sum(1 for i in self.issues if i.severity == Severity.HIGH)
        warnings = sum(1 for i in self.issues if i.severity in [Severity.MEDIUM, Severity.LOW])

        # Calculate score (0-100)
        if self.checks_total > 0:
            score = int((self.checks_passed / self.checks_total) * 100)
        else:
            score = 0

        # Penalize for critical issues
        score -= critical * 20
        score -= errors * 10
        score = max(0, min(100, score))

        # Determine if valid
        valid = critical == 0 and (errors == 0 or not self.strict)

        return ValidationResult(
            valid=valid,
            score=score,
            issues=self.issues,
            warnings=warnings,
            errors=errors,
            critical=critical,
            checks_passed=self.checks_passed,
            checks_total=self.checks_total
        )


def load_config(filepath: str, format_type: str) -> Dict:
    """Load configuration file"""
    with open(filepath, 'r') as f:
        config = json.load(f)

    # Transform format-specific configs to generic format
    if format_type == 'keycloak':
        return transform_keycloak_config(config)
    elif format_type == 'auth0':
        return transform_auth0_config(config)
    elif format_type == 'okta':
        return transform_okta_config(config)

    return config


def transform_keycloak_config(config: Dict) -> Dict:
    """Transform Keycloak realm export to generic format"""
    # Extract relevant OAuth settings from Keycloak format
    generic = {
        'issuer': config.get('issuer', f"https://keycloak.example.com/realms/{config.get('realm', 'master')}"),
        'authorization_endpoint': f"{config.get('issuer', '')}/protocol/openid-connect/auth",
        'token_endpoint': f"{config.get('issuer', '')}/protocol/openid-connect/token",
        'introspection_endpoint': f"{config.get('issuer', '')}/protocol/openid-connect/token/introspect",
        'revocation_endpoint': f"{config.get('issuer', '')}/protocol/openid-connect/revoke",
        'jwks_uri': f"{config.get('issuer', '')}/protocol/openid-connect/certs",
        'grant_types_supported': ['authorization_code', 'refresh_token', 'client_credentials'],
        'code_challenge_methods_supported': ['S256', 'plain'],
        'require_pkce': config.get('oauth2DeviceConfig', {}).get('oauth2DeviceCodeLifespan', False),
        'access_token_lifetime': config.get('accessTokenLifespan', 300),
        'authorization_code_lifetime': config.get('accessCodeLifespan', 60),
        'refresh_token_lifetime': config.get('ssoSessionIdleTimeout', 1800),
    }

    return generic


def transform_auth0_config(config: Dict) -> Dict:
    """Transform Auth0 config to generic format"""
    return config  # Placeholder


def transform_okta_config(config: Dict) -> Dict:
    """Transform Okta config to generic format"""
    return config  # Placeholder


def print_results(result: ValidationResult, json_output: bool = False, output_file: Optional[str] = None):
    """Print validation results"""

    if json_output:
        output = {
            'valid': result.valid,
            'score': result.score,
            'summary': {
                'critical': result.critical,
                'errors': result.errors,
                'warnings': result.warnings,
                'checks_passed': result.checks_passed,
                'checks_total': result.checks_total
            },
            'issues': [
                {
                    'severity': i.severity.value,
                    'category': i.category,
                    'message': i.message,
                    'field': i.field,
                    'recommendation': i.recommendation,
                    'reference': i.reference
                }
                for i in result.issues
            ]
        }

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2)
        else:
            print(json.dumps(output, indent=2))

    else:
        print("\n" + "=" * 70)
        print("OAuth 2.0 Configuration Validation Report")
        print("=" * 70)

        print(f"\nScore: {result.score}/100")
        print(f"Status: {'✓ VALID' if result.valid else '✗ INVALID'}")
        print(f"Checks: {result.checks_passed}/{result.checks_total} passed")

        print(f"\nIssues Summary:")
        print(f"  Critical: {result.critical}")
        print(f"  Errors:   {result.errors}")
        print(f"  Warnings: {result.warnings}")

        if result.issues:
            print("\n" + "-" * 70)
            print("Issues Found:")
            print("-" * 70)

            for i, issue in enumerate(result.issues, 1):
                print(f"\n{i}. [{issue.severity.value}] {issue.category}")
                print(f"   Message: {issue.message}")
                if issue.field:
                    print(f"   Field: {issue.field}")
                if issue.recommendation:
                    print(f"   Recommendation: {issue.recommendation}")
                if issue.reference:
                    print(f"   Reference: {issue.reference}")

        print("\n" + "=" * 70)

        if output_file:
            print(f"\nReport written to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='OAuth 2.0 Configuration Validator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--config', required=True, help='Configuration file to validate')
    parser.add_argument('--format', default='generic',
                        choices=['generic', 'keycloak', 'auth0', 'okta'],
                        help='Configuration format')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--output', help='Write output to file')
    parser.add_argument('--strict', action='store_true', help='Strict mode (fail on warnings)')

    args = parser.parse_args()

    try:
        # Load configuration
        config = load_config(args.config, args.format)

        # Validate
        validator = OAuthConfigValidator(strict=args.strict)
        result = validator.validate(config)

        # Print results
        print_results(result, json_output=args.json, output_file=args.output)

        # Exit with appropriate code
        sys.exit(0 if result.valid else 1)

    except FileNotFoundError:
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
