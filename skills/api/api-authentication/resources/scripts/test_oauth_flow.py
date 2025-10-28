#!/usr/bin/env python3
"""
OAuth 2.0 Flow Validator

Validates OAuth 2.0 implementation for security best practices and compliance
with RFC 6749. Tests Authorization Code Flow, PKCE, token endpoints, and more.

Usage:
    python test_oauth_flow.py --auth-url https://auth.example.com --test-flow
    python test_oauth_flow.py --token-url https://auth.example.com/token --test-token-endpoint
    python test_oauth_flow.py --config oauth_config.json --full-test --json

Examples:
    # Test authorization endpoint
    python test_oauth_flow.py --auth-url https://auth.example.com/authorize \\
                              --client-id CLIENT_ID --redirect-uri https://app.example.com/callback

    # Test token endpoint
    python test_oauth_flow.py --token-url https://auth.example.com/token \\
                              --client-id CLIENT_ID --client-secret SECRET --test-token-endpoint

    # Full OAuth flow test
    python test_oauth_flow.py --config oauth_config.json --full-test
"""

import requests
import json
import argparse
import sys
import secrets
import hashlib
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode


class OAuthTester:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = {
            'timestamp': datetime.utcnow().isoformat(),
            'tests': [],
            'issues': []
        }

    def log(self, message: str):
        """Log message if verbose"""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def generate_pkce_pair(self) -> Dict[str, str]:
        """Generate PKCE code verifier and challenge"""
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

        # Generate code challenge (SHA-256 hash of verifier)
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')

        return {
            'code_verifier': code_verifier,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }

    def test_authorization_endpoint(
        self,
        auth_url: str,
        client_id: str,
        redirect_uri: str,
        scope: str = 'openid profile email'
    ) -> Dict[str, Any]:
        """Test OAuth 2.0 authorization endpoint"""
        self.log("Testing authorization endpoint...")

        result = {
            'endpoint': auth_url,
            'tests_passed': 0,
            'tests_failed': 0,
            'issues': []
        }

        # Test 1: Basic authorization request
        self._test_basic_auth_request(auth_url, client_id, redirect_uri, scope, result)

        # Test 2: PKCE support
        self._test_pkce_support(auth_url, client_id, redirect_uri, scope, result)

        # Test 3: State parameter
        self._test_state_parameter(auth_url, client_id, redirect_uri, scope, result)

        # Test 4: Invalid redirect URI
        self._test_redirect_uri_validation(auth_url, client_id, result)

        # Test 5: Response type validation
        self._test_response_type_validation(auth_url, client_id, redirect_uri, result)

        self.results['tests'].append({
            'test': 'authorization_endpoint',
            'result': result
        })

        return result

    def _test_basic_auth_request(
        self,
        auth_url: str,
        client_id: str,
        redirect_uri: str,
        scope: str,
        result: Dict[str, Any]
    ):
        """Test basic authorization request"""
        self.log("  Testing basic authorization request...")

        try:
            params = {
                'response_type': 'code',
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'scope': scope,
                'state': secrets.token_urlsafe(16)
            }

            response = requests.get(
                auth_url,
                params=params,
                allow_redirects=False,
                timeout=10
            )

            # Should return 302 redirect or 200 with login page
            if response.status_code in [200, 302]:
                result['tests_passed'] += 1
                self.log("  ✓ Authorization endpoint responding")
            else:
                result['tests_failed'] += 1
                result['issues'].append({
                    'severity': 'HIGH',
                    'issue': f'Unexpected response: {response.status_code}'
                })
                self.log(f"  ✗ Unexpected status: {response.status_code}")

            # Check for HTTPS
            if not auth_url.startswith('https://'):
                result['issues'].append({
                    'severity': 'CRITICAL',
                    'issue': 'Authorization endpoint not using HTTPS'
                })
                self.log("  ✗ CRITICAL: Not using HTTPS")

        except requests.RequestException as e:
            result['tests_failed'] += 1
            result['issues'].append({
                'severity': 'HIGH',
                'issue': f'Failed to connect: {str(e)}'
            })
            self.log(f"  ✗ Connection failed: {e}")

    def _test_pkce_support(
        self,
        auth_url: str,
        client_id: str,
        redirect_uri: str,
        scope: str,
        result: Dict[str, Any]
    ):
        """Test PKCE support"""
        self.log("  Testing PKCE support...")

        try:
            pkce = self.generate_pkce_pair()

            params = {
                'response_type': 'code',
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'scope': scope,
                'state': secrets.token_urlsafe(16),
                'code_challenge': pkce['code_challenge'],
                'code_challenge_method': pkce['code_challenge_method']
            }

            response = requests.get(
                auth_url,
                params=params,
                allow_redirects=False,
                timeout=10
            )

            # If server accepts PKCE parameters without error, it supports PKCE
            if response.status_code in [200, 302]:
                result['tests_passed'] += 1
                self.log("  ✓ PKCE parameters accepted")
            else:
                result['tests_failed'] += 1
                result['issues'].append({
                    'severity': 'MEDIUM',
                    'issue': 'PKCE parameters not accepted (may not support PKCE)'
                })
                self.log("  ⚠ PKCE support unclear")

        except Exception as e:
            result['tests_failed'] += 1
            self.log(f"  ✗ PKCE test failed: {e}")

    def _test_state_parameter(
        self,
        auth_url: str,
        client_id: str,
        redirect_uri: str,
        scope: str,
        result: Dict[str, Any]
    ):
        """Test state parameter handling"""
        self.log("  Testing state parameter...")

        try:
            # Test with state parameter
            state = secrets.token_urlsafe(16)

            params = {
                'response_type': 'code',
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'scope': scope,
                'state': state
            }

            response = requests.get(
                auth_url,
                params=params,
                allow_redirects=False,
                timeout=10
            )

            if response.status_code in [200, 302]:
                result['tests_passed'] += 1
                self.log("  ✓ State parameter accepted")
            else:
                result['tests_failed'] += 1
                self.log("  ✗ State parameter handling unclear")

        except Exception as e:
            result['tests_failed'] += 1
            self.log(f"  ✗ State test failed: {e}")

    def _test_redirect_uri_validation(
        self,
        auth_url: str,
        client_id: str,
        result: Dict[str, Any]
    ):
        """Test redirect URI validation"""
        self.log("  Testing redirect URI validation...")

        try:
            # Test with obviously invalid redirect URI
            params = {
                'response_type': 'code',
                'client_id': client_id,
                'redirect_uri': 'https://attacker.com/callback',
                'state': secrets.token_urlsafe(16)
            }

            response = requests.get(
                auth_url,
                params=params,
                allow_redirects=False,
                timeout=10
            )

            # Should reject invalid redirect URI (400 or error page)
            if response.status_code == 400 or 'error' in response.text.lower():
                result['tests_passed'] += 1
                self.log("  ✓ Invalid redirect URI rejected")
            else:
                result['tests_failed'] += 1
                result['issues'].append({
                    'severity': 'CRITICAL',
                    'issue': 'Server may not validate redirect URIs properly'
                })
                self.log("  ✗ CRITICAL: Redirect URI validation unclear")

        except Exception as e:
            self.log(f"  ⚠ Redirect URI test inconclusive: {e}")

    def _test_response_type_validation(
        self,
        auth_url: str,
        client_id: str,
        redirect_uri: str,
        result: Dict[str, Any]
    ):
        """Test response_type parameter validation"""
        self.log("  Testing response_type validation...")

        try:
            # Test with invalid response_type
            params = {
                'response_type': 'invalid',
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'state': secrets.token_urlsafe(16)
            }

            response = requests.get(
                auth_url,
                params=params,
                allow_redirects=False,
                timeout=10
            )

            # Should reject invalid response_type
            if response.status_code >= 400:
                result['tests_passed'] += 1
                self.log("  ✓ Invalid response_type rejected")
            else:
                result['tests_failed'] += 1
                result['issues'].append({
                    'severity': 'HIGH',
                    'issue': 'Invalid response_type not rejected'
                })
                self.log("  ✗ Invalid response_type accepted")

        except Exception as e:
            self.log(f"  ⚠ Response type test inconclusive: {e}")

    def test_token_endpoint(
        self,
        token_url: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        """Test OAuth 2.0 token endpoint"""
        self.log("Testing token endpoint...")

        result = {
            'endpoint': token_url,
            'tests_passed': 0,
            'tests_failed': 0,
            'issues': []
        }

        # Test 1: Client credentials flow
        self._test_client_credentials(token_url, client_id, client_secret, result)

        # Test 2: Invalid client credentials
        self._test_invalid_credentials(token_url, client_id, result)

        # Test 3: HTTPS enforcement
        self._test_https_enforcement(token_url, result)

        # Test 4: Content-Type validation
        self._test_content_type(token_url, client_id, client_secret, result)

        self.results['tests'].append({
            'test': 'token_endpoint',
            'result': result
        })

        return result

    def _test_client_credentials(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        result: Dict[str, Any]
    ):
        """Test client credentials grant"""
        self.log("  Testing client credentials grant...")

        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }

            response = requests.post(
                token_url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )

            if response.status_code == 200:
                token_data = response.json()

                # Validate response structure
                if 'access_token' in token_data and 'token_type' in token_data:
                    result['tests_passed'] += 1
                    self.log("  ✓ Token endpoint working")

                    # Check token_type
                    if token_data['token_type'].lower() != 'bearer':
                        result['issues'].append({
                            'severity': 'MEDIUM',
                            'issue': f'Unexpected token_type: {token_data["token_type"]}'
                        })

                    # Check expires_in
                    if 'expires_in' not in token_data:
                        result['issues'].append({
                            'severity': 'LOW',
                            'issue': 'Missing expires_in in token response'
                        })

                else:
                    result['tests_failed'] += 1
                    result['issues'].append({
                        'severity': 'HIGH',
                        'issue': 'Invalid token response structure'
                    })
                    self.log("  ✗ Invalid response structure")

            elif response.status_code == 401:
                self.log("  ⚠ Authentication failed (expected with test credentials)")
            else:
                result['tests_failed'] += 1
                result['issues'].append({
                    'severity': 'HIGH',
                    'issue': f'Unexpected response: {response.status_code}'
                })
                self.log(f"  ✗ Unexpected status: {response.status_code}")

        except requests.RequestException as e:
            result['tests_failed'] += 1
            result['issues'].append({
                'severity': 'HIGH',
                'issue': f'Failed to connect: {str(e)}'
            })
            self.log(f"  ✗ Connection failed: {e}")

    def _test_invalid_credentials(
        self,
        token_url: str,
        client_id: str,
        result: Dict[str, Any]
    ):
        """Test with invalid credentials"""
        self.log("  Testing invalid credentials handling...")

        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': 'invalid_secret'
            }

            response = requests.post(
                token_url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )

            # Should return 401
            if response.status_code == 401:
                result['tests_passed'] += 1
                self.log("  ✓ Invalid credentials rejected")
            else:
                result['tests_failed'] += 1
                result['issues'].append({
                    'severity': 'CRITICAL',
                    'issue': 'Invalid credentials not properly rejected'
                })
                self.log("  ✗ CRITICAL: Invalid credentials accepted")

        except Exception as e:
            self.log(f"  ⚠ Invalid credentials test inconclusive: {e}")

    def _test_https_enforcement(self, token_url: str, result: Dict[str, Any]):
        """Test HTTPS enforcement"""
        self.log("  Testing HTTPS enforcement...")

        if not token_url.startswith('https://'):
            result['issues'].append({
                'severity': 'CRITICAL',
                'issue': 'Token endpoint not using HTTPS'
            })
            self.log("  ✗ CRITICAL: Not using HTTPS")
            result['tests_failed'] += 1
        else:
            result['tests_passed'] += 1
            self.log("  ✓ Using HTTPS")

    def _test_content_type(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        result: Dict[str, Any]
    ):
        """Test Content-Type header validation"""
        self.log("  Testing Content-Type validation...")

        try:
            # Test with incorrect Content-Type
            data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }

            response = requests.post(
                token_url,
                json=data,  # Wrong: should be form-encoded
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            # Should reject or handle gracefully
            if response.status_code >= 400:
                result['tests_passed'] += 1
                self.log("  ✓ Incorrect Content-Type rejected")
            else:
                self.log("  ⚠ Server accepts multiple Content-Types")

        except Exception as e:
            self.log(f"  ⚠ Content-Type test inconclusive: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='OAuth 2.0 Flow Validator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test authorization endpoint
  python test_oauth_flow.py --auth-url https://auth.example.com/authorize \\
                            --client-id CLIENT_ID \\
                            --redirect-uri https://app.example.com/callback

  # Test token endpoint
  python test_oauth_flow.py --token-url https://auth.example.com/token \\
                            --client-id CLIENT_ID \\
                            --client-secret SECRET \\
                            --test-token-endpoint

  # Full test
  python test_oauth_flow.py --auth-url https://auth.example.com/authorize \\
                            --token-url https://auth.example.com/token \\
                            --client-id CLIENT_ID \\
                            --client-secret SECRET \\
                            --redirect-uri https://app.example.com/callback \\
                            --full-test
        """
    )

    parser.add_argument('--auth-url', type=str, help='Authorization endpoint URL')
    parser.add_argument('--token-url', type=str, help='Token endpoint URL')
    parser.add_argument('--client-id', type=str, help='OAuth client ID')
    parser.add_argument('--client-secret', type=str, help='OAuth client secret')
    parser.add_argument('--redirect-uri', type=str, help='Redirect URI')
    parser.add_argument('--scope', type=str, default='openid profile email',
                       help='OAuth scopes (default: openid profile email)')

    # Test operations
    parser.add_argument('--test-auth-endpoint', action='store_true',
                       help='Test authorization endpoint')
    parser.add_argument('--test-token-endpoint', action='store_true',
                       help='Test token endpoint')
    parser.add_argument('--full-test', action='store_true',
                       help='Run all tests')

    # Output options
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    tester = OAuthTester(verbose=args.verbose)

    try:
        # Test authorization endpoint
        if args.test_auth_endpoint or args.full_test:
            if not args.auth_url or not args.client_id or not args.redirect_uri:
                print("Error: --auth-url, --client-id, and --redirect-uri required",
                      file=sys.stderr)
                sys.exit(1)

            result = tester.test_authorization_endpoint(
                args.auth_url,
                args.client_id,
                args.redirect_uri,
                args.scope
            )

            if not args.json and not args.full_test:
                print(f"\nAuthorization Endpoint Test Results:")
                print(f"Passed: {result['tests_passed']}")
                print(f"Failed: {result['tests_failed']}")

                if result['issues']:
                    print(f"\nIssues Found ({len(result['issues'])}):")
                    for issue in result['issues']:
                        print(f"  [{issue['severity']}] {issue['issue']}")

        # Test token endpoint
        if args.test_token_endpoint or args.full_test:
            if not args.token_url or not args.client_id or not args.client_secret:
                print("Error: --token-url, --client-id, and --client-secret required",
                      file=sys.stderr)
                sys.exit(1)

            result = tester.test_token_endpoint(
                args.token_url,
                args.client_id,
                args.client_secret
            )

            if not args.json and not args.full_test:
                print(f"\nToken Endpoint Test Results:")
                print(f"Passed: {result['tests_passed']}")
                print(f"Failed: {result['tests_failed']}")

                if result['issues']:
                    print(f"\nIssues Found ({len(result['issues'])}):")
                    for issue in result['issues']:
                        print(f"  [{issue['severity']}] {issue['issue']}")

        # Output full results
        if args.json:
            print(json.dumps(tester.results, indent=2))
        elif args.full_test:
            print(f"\nOAuth 2.0 Security Test Results:")
            print(f"Total Tests: {len(tester.results['tests'])}")
            print(f"Total Issues: {len(tester.results['issues'])}")

            for test in tester.results['tests']:
                print(f"\n{test['test'].replace('_', ' ').title()}:")
                result = test['result']
                print(f"  Passed: {result['tests_passed']}")
                print(f"  Failed: {result['tests_failed']}")

                if result.get('issues'):
                    print(f"  Issues:")
                    for issue in result['issues']:
                        print(f"    [{issue['severity']}] {issue['issue']}")

        if not (args.test_auth_endpoint or args.test_token_endpoint or args.full_test):
            parser.print_help()
            sys.exit(1)

    except Exception as e:
        if args.json:
            print(json.dumps({'error': str(e)}, indent=2), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
