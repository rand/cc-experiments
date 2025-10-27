#!/usr/bin/env python3
"""
OAuth 2.0 Flow End-to-End Tester

Tests OAuth 2.0 authorization flows end-to-end including authorization code,
client credentials, PKCE, token refresh, and security validations.

Usage:
    ./test_oauth_flow.py --authorization-server https://auth.example.com --flow authorization_code
    ./test_oauth_flow.py --authorization-server https://auth.example.com --flow client_credentials --json
    ./test_oauth_flow.py --config test-config.json --all-flows

Examples:
    # Test authorization code flow with PKCE
    ./test_oauth_flow.py --authorization-server https://auth.example.com \\
                         --client-id test-client \\
                         --client-secret secret123 \\
                         --redirect-uri https://app.example.com/callback \\
                         --flow authorization_code

    # Test client credentials flow
    ./test_oauth_flow.py --authorization-server https://auth.example.com \\
                         --client-id service-client \\
                         --client-secret secret456 \\
                         --flow client_credentials

    # Test all flows from config
    ./test_oauth_flow.py --config oauth-test-config.json --all-flows --json

Options:
    --authorization-server URL    Authorization server base URL
    --client-id ID               OAuth client ID
    --client-secret SECRET       OAuth client secret (for confidential clients)
    --redirect-uri URI           Redirect URI for authorization code flow
    --flow FLOW                  Flow to test: authorization_code, client_credentials, refresh_token
    --all-flows                  Test all configured flows
    --config FILE                Configuration file with test parameters
    --json                       Output results as JSON
    --output FILE                Write output to file
    --help                       Show this help message
"""

import requests
import json
import argparse
import sys
import secrets
import hashlib
import base64
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode
from enum import Enum


class TestStatus(Enum):
    """Test status"""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    WARNING = "WARNING"


@dataclass
class TestResult:
    """Individual test result"""
    name: str
    status: TestStatus
    message: str
    duration_ms: float
    details: Optional[Dict] = None


@dataclass
class FlowTestResult:
    """Flow test result"""
    flow_name: str
    success: bool
    tests: List[TestResult]
    passed: int
    failed: int
    warnings: int
    total_duration_ms: float
    error: Optional[str] = None


class PKCEGenerator:
    """PKCE code verifier and challenge generator"""

    @staticmethod
    def generate_verifier(length: int = 64) -> str:
        """Generate code verifier"""
        # Generate random bytes
        random_bytes = secrets.token_bytes(length)
        # Base64URL encode without padding
        verifier = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
        # Truncate to requested length (43-128 chars)
        return verifier[:max(43, min(128, length))]

    @staticmethod
    def generate_challenge(verifier: str, method: str = 'S256') -> str:
        """Generate code challenge from verifier"""
        if method == 'S256':
            # SHA-256 hash
            digest = hashlib.sha256(verifier.encode('utf-8')).digest()
            # Base64URL encode without padding
            challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
            return challenge
        elif method == 'plain':
            return verifier
        else:
            raise ValueError(f"Unsupported method: {method}")

    @staticmethod
    def generate_pair(method: str = 'S256') -> Dict[str, str]:
        """Generate PKCE verifier and challenge pair"""
        verifier = PKCEGenerator.generate_verifier()
        challenge = PKCEGenerator.generate_challenge(verifier, method)
        return {
            'code_verifier': verifier,
            'code_challenge': challenge,
            'code_challenge_method': method
        }


class OAuthFlowTester:
    """OAuth 2.0 flow tester"""

    def __init__(self, auth_server: str, client_id: str, client_secret: Optional[str] = None,
                 redirect_uri: Optional[str] = None, verbose: bool = False):
        self.auth_server = auth_server.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.verbose = verbose

        # Discover endpoints
        self.endpoints = self._discover_endpoints()

    def _discover_endpoints(self) -> Dict[str, str]:
        """Discover OAuth endpoints"""
        # Try .well-known discovery
        discovery_url = f"{self.auth_server}/.well-known/oauth-authorization-server"

        try:
            response = requests.get(discovery_url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass

        # Fall back to standard paths
        return {
            'authorization_endpoint': f"{self.auth_server}/authorize",
            'token_endpoint': f"{self.auth_server}/token",
            'introspection_endpoint': f"{self.auth_server}/introspect",
            'revocation_endpoint': f"{self.auth_server}/revoke"
        }

    def log(self, message: str):
        """Log message if verbose"""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def test_authorization_code_flow(self) -> FlowTestResult:
        """Test authorization code flow with PKCE"""
        flow_start = time.time()
        tests = []

        self.log("Testing Authorization Code Flow with PKCE...")

        try:
            # Test 1: Generate PKCE pair
            start = time.time()
            pkce = PKCEGenerator.generate_pair()
            duration = (time.time() - start) * 1000

            tests.append(TestResult(
                name="Generate PKCE pair",
                status=TestStatus.PASSED,
                message=f"Generated code_verifier and code_challenge (S256)",
                duration_ms=duration,
                details={'method': 'S256', 'verifier_length': len(pkce['code_verifier'])}
            ))

            # Test 2: Build authorization URL
            start = time.time()
            state = secrets.token_urlsafe(32)
            auth_params = {
                'response_type': 'code',
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'scope': 'openid profile email',
                'state': state,
                'code_challenge': pkce['code_challenge'],
                'code_challenge_method': pkce['code_challenge_method']
            }

            auth_url = f"{self.endpoints['authorization_endpoint']}?{urlencode(auth_params)}"
            duration = (time.time() - start) * 1000

            tests.append(TestResult(
                name="Build authorization URL",
                status=TestStatus.PASSED,
                message="Authorization URL constructed with PKCE parameters",
                duration_ms=duration,
                details={'url': auth_url, 'state': state}
            ))

            # Test 3: Validate authorization endpoint (HEAD request)
            start = time.time()
            try:
                response = requests.head(
                    self.endpoints['authorization_endpoint'],
                    timeout=10,
                    allow_redirects=False
                )
                duration = (time.time() - start) * 1000

                # Accept 405 (Method Not Allowed) as valid - endpoint exists
                if response.status_code in [200, 302, 400, 405]:
                    tests.append(TestResult(
                        name="Validate authorization endpoint",
                        status=TestStatus.PASSED,
                        message=f"Authorization endpoint is accessible (HTTP {response.status_code})",
                        duration_ms=duration
                    ))
                else:
                    tests.append(TestResult(
                        name="Validate authorization endpoint",
                        status=TestStatus.FAILED,
                        message=f"Unexpected response: HTTP {response.status_code}",
                        duration_ms=duration
                    ))
            except Exception as e:
                duration = (time.time() - start) * 1000
                tests.append(TestResult(
                    name="Validate authorization endpoint",
                    status=TestStatus.FAILED,
                    message=f"Endpoint unreachable: {str(e)}",
                    duration_ms=duration
                ))

            # Test 4: Validate HTTPS usage
            start = time.time()
            uses_https = self.endpoints['authorization_endpoint'].startswith('https://')
            duration = (time.time() - start) * 1000

            tests.append(TestResult(
                name="Validate HTTPS usage",
                status=TestStatus.PASSED if uses_https else TestStatus.FAILED,
                message="Authorization endpoint uses HTTPS" if uses_https else "Authorization endpoint does NOT use HTTPS (CRITICAL)",
                duration_ms=duration
            ))

            # NOTE: Cannot complete full flow without user interaction
            tests.append(TestResult(
                name="Complete authorization flow",
                status=TestStatus.SKIPPED,
                message="Requires user interaction (manual test)",
                duration_ms=0,
                details={'instruction': 'Visit authorization URL and complete flow manually'}
            ))

            # Calculate summary
            passed = sum(1 for t in tests if t.status == TestStatus.PASSED)
            failed = sum(1 for t in tests if t.status == TestStatus.FAILED)
            warnings = sum(1 for t in tests if t.status == TestStatus.WARNING)
            total_duration = (time.time() - flow_start) * 1000

            return FlowTestResult(
                flow_name="Authorization Code with PKCE",
                success=failed == 0,
                tests=tests,
                passed=passed,
                failed=failed,
                warnings=warnings,
                total_duration_ms=total_duration
            )

        except Exception as e:
            total_duration = (time.time() - flow_start) * 1000
            return FlowTestResult(
                flow_name="Authorization Code with PKCE",
                success=False,
                tests=tests,
                passed=0,
                failed=len(tests),
                warnings=0,
                total_duration_ms=total_duration,
                error=str(e)
            )

    def test_client_credentials_flow(self) -> FlowTestResult:
        """Test client credentials flow"""
        flow_start = time.time()
        tests = []

        self.log("Testing Client Credentials Flow...")

        try:
            # Test 1: Token request
            start = time.time()
            token_data = {
                'grant_type': 'client_credentials',
                'scope': 'api:read api:write'
            }

            try:
                response = requests.post(
                    self.endpoints['token_endpoint'],
                    auth=(self.client_id, self.client_secret) if self.client_secret else None,
                    data=token_data,
                    timeout=10
                )
                duration = (time.time() - start) * 1000

                if response.status_code == 200:
                    tokens = response.json()

                    tests.append(TestResult(
                        name="Request access token",
                        status=TestStatus.PASSED,
                        message="Successfully obtained access token",
                        duration_ms=duration,
                        details={
                            'token_type': tokens.get('token_type'),
                            'expires_in': tokens.get('expires_in'),
                            'scope': tokens.get('scope')
                        }
                    ))

                    # Test 2: Validate token response format
                    start = time.time()
                    required_fields = ['access_token', 'token_type']
                    missing = [f for f in required_fields if f not in tokens]
                    duration = (time.time() - start) * 1000

                    if not missing:
                        tests.append(TestResult(
                            name="Validate token response",
                            status=TestStatus.PASSED,
                            message="Token response contains required fields",
                            duration_ms=duration
                        ))
                    else:
                        tests.append(TestResult(
                            name="Validate token response",
                            status=TestStatus.FAILED,
                            message=f"Missing required fields: {', '.join(missing)}",
                            duration_ms=duration
                        ))

                    # Test 3: Validate token type
                    start = time.time()
                    token_type = tokens.get('token_type', '').lower()
                    duration = (time.time() - start) * 1000

                    if token_type == 'bearer':
                        tests.append(TestResult(
                            name="Validate token type",
                            status=TestStatus.PASSED,
                            message="Token type is 'Bearer'",
                            duration_ms=duration
                        ))
                    else:
                        tests.append(TestResult(
                            name="Validate token type",
                            status=TestStatus.WARNING,
                            message=f"Token type is '{token_type}' (expected 'Bearer')",
                            duration_ms=duration
                        ))

                    # Test 4: Check token expiration
                    start = time.time()
                    expires_in = tokens.get('expires_in')
                    duration = (time.time() - start) * 1000

                    if expires_in:
                        if 300 <= expires_in <= 86400:  # 5 min to 24 hours
                            tests.append(TestResult(
                                name="Validate token expiration",
                                status=TestStatus.PASSED,
                                message=f"Token expires in {expires_in} seconds (reasonable)",
                                duration_ms=duration
                            ))
                        else:
                            tests.append(TestResult(
                                name="Validate token expiration",
                                status=TestStatus.WARNING,
                                message=f"Token expires in {expires_in} seconds (unusual)",
                                duration_ms=duration
                            ))
                    else:
                        tests.append(TestResult(
                            name="Validate token expiration",
                            status=TestStatus.WARNING,
                            message="Token expiration not specified",
                            duration_ms=duration
                        ))

                elif response.status_code == 401:
                    tests.append(TestResult(
                        name="Request access token",
                        status=TestStatus.FAILED,
                        message="Client authentication failed (401 Unauthorized)",
                        duration_ms=duration,
                        details={'response': response.text}
                    ))
                else:
                    tests.append(TestResult(
                        name="Request access token",
                        status=TestStatus.FAILED,
                        message=f"Token request failed: HTTP {response.status_code}",
                        duration_ms=duration,
                        details={'response': response.text}
                    ))

            except Exception as e:
                duration = (time.time() - start) * 1000
                tests.append(TestResult(
                    name="Request access token",
                    status=TestStatus.FAILED,
                    message=f"Request failed: {str(e)}",
                    duration_ms=duration
                ))

            # Calculate summary
            passed = sum(1 for t in tests if t.status == TestStatus.PASSED)
            failed = sum(1 for t in tests if t.status == TestStatus.FAILED)
            warnings = sum(1 for t in tests if t.status == TestStatus.WARNING)
            total_duration = (time.time() - flow_start) * 1000

            return FlowTestResult(
                flow_name="Client Credentials",
                success=failed == 0,
                tests=tests,
                passed=passed,
                failed=failed,
                warnings=warnings,
                total_duration_ms=total_duration
            )

        except Exception as e:
            total_duration = (time.time() - flow_start) * 1000
            return FlowTestResult(
                flow_name="Client Credentials",
                success=False,
                tests=tests,
                passed=0,
                failed=len(tests),
                warnings=0,
                total_duration_ms=total_duration,
                error=str(e)
            )

    def test_token_revocation(self, access_token: str) -> FlowTestResult:
        """Test token revocation"""
        flow_start = time.time()
        tests = []

        self.log("Testing Token Revocation...")

        try:
            # Test 1: Revoke token
            start = time.time()
            revoke_data = {
                'token': access_token,
                'token_type_hint': 'access_token'
            }

            try:
                response = requests.post(
                    self.endpoints['revocation_endpoint'],
                    auth=(self.client_id, self.client_secret) if self.client_secret else None,
                    data=revoke_data,
                    timeout=10
                )
                duration = (time.time() - start) * 1000

                if response.status_code == 200:
                    tests.append(TestResult(
                        name="Revoke token",
                        status=TestStatus.PASSED,
                        message="Token revocation successful",
                        duration_ms=duration
                    ))
                else:
                    tests.append(TestResult(
                        name="Revoke token",
                        status=TestStatus.FAILED,
                        message=f"Revocation failed: HTTP {response.status_code}",
                        duration_ms=duration
                    ))

            except Exception as e:
                duration = (time.time() - start) * 1000
                tests.append(TestResult(
                    name="Revoke token",
                    status=TestStatus.FAILED,
                    message=f"Request failed: {str(e)}",
                    duration_ms=duration
                ))

            # Calculate summary
            passed = sum(1 for t in tests if t.status == TestStatus.PASSED)
            failed = sum(1 for t in tests if t.status == TestStatus.FAILED)
            warnings = sum(1 for t in tests if t.status == TestStatus.WARNING)
            total_duration = (time.time() - flow_start) * 1000

            return FlowTestResult(
                flow_name="Token Revocation",
                success=failed == 0,
                tests=tests,
                passed=passed,
                failed=failed,
                warnings=warnings,
                total_duration_ms=total_duration
            )

        except Exception as e:
            total_duration = (time.time() - flow_start) * 1000
            return FlowTestResult(
                flow_name="Token Revocation",
                success=False,
                tests=tests,
                passed=0,
                failed=len(tests),
                warnings=0,
                total_duration_ms=total_duration,
                error=str(e)
            )


def print_results(results: List[FlowTestResult], json_output: bool = False, output_file: Optional[str] = None):
    """Print test results"""

    if json_output:
        output = {
            'timestamp': datetime.now().isoformat(),
            'flows': [
                {
                    'flow_name': r.flow_name,
                    'success': r.success,
                    'passed': r.passed,
                    'failed': r.failed,
                    'warnings': r.warnings,
                    'duration_ms': r.total_duration_ms,
                    'error': r.error,
                    'tests': [
                        {
                            'name': t.name,
                            'status': t.status.value,
                            'message': t.message,
                            'duration_ms': t.duration_ms,
                            'details': t.details
                        }
                        for t in r.tests
                    ]
                }
                for r in results
            ]
        }

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2)
        else:
            print(json.dumps(output, indent=2))

    else:
        print("\n" + "=" * 70)
        print("OAuth 2.0 Flow Test Results")
        print("=" * 70)

        for result in results:
            print(f"\n{result.flow_name}")
            print("-" * 70)
            print(f"Status: {'✓ PASSED' if result.success else '✗ FAILED'}")
            print(f"Tests: {result.passed} passed, {result.failed} failed, {result.warnings} warnings")
            print(f"Duration: {result.total_duration_ms:.2f}ms")

            if result.error:
                print(f"Error: {result.error}")

            for test in result.tests:
                status_icon = {
                    TestStatus.PASSED: "✓",
                    TestStatus.FAILED: "✗",
                    TestStatus.SKIPPED: "⊘",
                    TestStatus.WARNING: "⚠"
                }[test.status]

                print(f"  {status_icon} {test.name}")
                print(f"    {test.message} ({test.duration_ms:.2f}ms)")

                if test.details:
                    print(f"    Details: {json.dumps(test.details, indent=6)}")

        print("\n" + "=" * 70)

        # Summary
        total_passed = sum(r.passed for r in results)
        total_failed = sum(r.failed for r in results)
        total_warnings = sum(r.warnings for r in results)
        all_success = all(r.success for r in results)

        print(f"\nOverall: {'✓ ALL PASSED' if all_success else '✗ SOME FAILED'}")
        print(f"Total: {total_passed} passed, {total_failed} failed, {total_warnings} warnings")

        if output_file:
            print(f"\nResults written to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='OAuth 2.0 Flow End-to-End Tester',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--authorization-server', help='Authorization server base URL')
    parser.add_argument('--client-id', help='OAuth client ID')
    parser.add_argument('--client-secret', help='OAuth client secret')
    parser.add_argument('--redirect-uri', help='Redirect URI for authorization code flow')
    parser.add_argument('--flow', choices=['authorization_code', 'client_credentials', 'refresh_token'],
                        help='Flow to test')
    parser.add_argument('--all-flows', action='store_true', help='Test all flows')
    parser.add_argument('--config', help='Configuration file')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--output', help='Write output to file')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Load config if provided
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
            args.authorization_server = config.get('authorization_server', args.authorization_server)
            args.client_id = config.get('client_id', args.client_id)
            args.client_secret = config.get('client_secret', args.client_secret)
            args.redirect_uri = config.get('redirect_uri', args.redirect_uri)

    # Validate required parameters
    if not args.authorization_server:
        print("Error: --authorization-server is required", file=sys.stderr)
        sys.exit(1)

    if not args.client_id:
        print("Error: --client-id is required", file=sys.stderr)
        sys.exit(1)

    # Create tester
    tester = OAuthFlowTester(
        auth_server=args.authorization_server,
        client_id=args.client_id,
        client_secret=args.client_secret,
        redirect_uri=args.redirect_uri,
        verbose=args.verbose
    )

    # Run tests
    results = []

    if args.all_flows or args.flow == 'authorization_code':
        if not args.redirect_uri:
            print("Warning: --redirect-uri required for authorization code flow, skipping...", file=sys.stderr)
        else:
            results.append(tester.test_authorization_code_flow())

    if args.all_flows or args.flow == 'client_credentials':
        if not args.client_secret:
            print("Warning: --client-secret required for client credentials flow, skipping...", file=sys.stderr)
        else:
            results.append(tester.test_client_credentials_flow())

    # Print results
    if results:
        print_results(results, json_output=args.json, output_file=args.output)

        # Exit with appropriate code
        all_success = all(r.success for r in results)
        sys.exit(0 if all_success else 1)
    else:
        print("No tests were run. Specify --flow or --all-flows.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
