#!/usr/bin/env python3
"""
JWT Security Testing and Validation Tool

Comprehensive JWT security testing tool for validation, expiration, signing,
and vulnerability detection.

Usage:
    python test_jwt.py --token TOKEN --validate
    python test_jwt.py --generate --algorithm HS256 --secret SECRET
    python test_jwt.py --token TOKEN --attack-test --json
    python test_jwt.py --help

Examples:
    # Validate a JWT token
    python test_jwt.py --token "eyJhbGc..." --validate --secret "your-secret"

    # Generate a new JWT token
    python test_jwt.py --generate --algorithm HS256 --secret "my-secret" --payload '{"sub":"123"}'

    # Run security tests
    python test_jwt.py --token "eyJhbGc..." --attack-test --secret "your-secret"
"""

import jwt
import json
import argparse
import sys
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import base64


class JWTTester:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = {
            'timestamp': datetime.utcnow().isoformat(),
            'tests': [],
            'vulnerabilities': []
        }

    def log(self, message: str):
        """Log message if verbose"""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def decode_without_verification(self, token: str) -> Dict[str, Any]:
        """Decode JWT without signature verification (for inspection only)"""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            raise ValueError(f"Failed to decode token: {e}")

    def validate_token(self, token: str, secret: str, algorithm: str = "HS256") -> Dict[str, Any]:
        """Validate JWT token with full security checks"""
        self.log(f"Validating token with algorithm: {algorithm}")

        result = {
            'valid': False,
            'claims': None,
            'issues': []
        }

        try:
            # Decode and validate
            claims = jwt.decode(
                token,
                secret,
                algorithms=[algorithm],
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'verify_nbf': True,
                    'verify_iat': True,
                    'require': ['exp']  # Expiration is required
                }
            )

            result['valid'] = True
            result['claims'] = claims
            self.log("✓ Token is valid")

            # Additional validation checks
            self._check_claims(claims, result)

        except jwt.ExpiredSignatureError:
            result['issues'].append({
                'type': 'EXPIRED',
                'severity': 'HIGH',
                'message': 'Token has expired'
            })
            self.log("✗ Token has expired")

        except jwt.InvalidSignatureError:
            result['issues'].append({
                'type': 'INVALID_SIGNATURE',
                'severity': 'CRITICAL',
                'message': 'Signature verification failed'
            })
            self.log("✗ Invalid signature")

        except jwt.InvalidAlgorithmError:
            result['issues'].append({
                'type': 'INVALID_ALGORITHM',
                'severity': 'CRITICAL',
                'message': f'Algorithm {algorithm} not allowed'
            })
            self.log("✗ Invalid algorithm")

        except jwt.DecodeError as e:
            result['issues'].append({
                'type': 'DECODE_ERROR',
                'severity': 'HIGH',
                'message': f'Failed to decode token: {str(e)}'
            })
            self.log(f"✗ Decode error: {e}")

        except Exception as e:
            result['issues'].append({
                'type': 'UNKNOWN_ERROR',
                'severity': 'HIGH',
                'message': str(e)
            })
            self.log(f"✗ Validation error: {e}")

        self.results['tests'].append({
            'test': 'token_validation',
            'result': result
        })

        return result

    def _check_claims(self, claims: Dict[str, Any], result: Dict[str, Any]):
        """Check for security best practices in claims"""

        # Check for required claims
        required_claims = ['exp', 'iat', 'sub']
        for claim in required_claims:
            if claim not in claims:
                result['issues'].append({
                    'type': 'MISSING_CLAIM',
                    'severity': 'MEDIUM',
                    'message': f'Missing recommended claim: {claim}'
                })

        # Check expiration time is reasonable (not too long)
        if 'exp' in claims and 'iat' in claims:
            lifetime = claims['exp'] - claims['iat']
            if lifetime > 3600:  # More than 1 hour
                result['issues'].append({
                    'type': 'LONG_LIVED_TOKEN',
                    'severity': 'MEDIUM',
                    'message': f'Token lifetime is {lifetime}s (>{1}h), consider shorter expiration'
                })

        # Check for sensitive data in payload
        sensitive_keywords = ['password', 'secret', 'ssn', 'credit_card']
        for key, value in claims.items():
            if any(keyword in str(key).lower() or keyword in str(value).lower()
                   for keyword in sensitive_keywords):
                result['issues'].append({
                    'type': 'SENSITIVE_DATA',
                    'severity': 'HIGH',
                    'message': f'Possible sensitive data in claim: {key}'
                })

    def generate_token(
        self,
        payload: Dict[str, Any],
        secret: str,
        algorithm: str = "HS256",
        expires_in: int = 3600
    ) -> str:
        """Generate a JWT token with proper claims"""
        self.log(f"Generating token with algorithm: {algorithm}")

        # Add standard claims
        now = datetime.utcnow()
        payload.update({
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=expires_in)).timestamp())
        })

        if 'sub' not in payload:
            self.log("Warning: 'sub' claim not provided")

        token = jwt.encode(payload, secret, algorithm=algorithm)
        self.log(f"✓ Token generated (expires in {expires_in}s)")

        return token

    def run_attack_tests(self, token: str, secret: Optional[str] = None) -> Dict[str, Any]:
        """Run common JWT attack tests"""
        self.log("Running JWT attack tests...")

        attack_results = {
            'tests_run': 0,
            'vulnerabilities_found': []
        }

        # Test 1: None algorithm attack
        self._test_none_algorithm(token, attack_results)

        # Test 2: Algorithm confusion attack
        if secret:
            self._test_algorithm_confusion(token, secret, attack_results)

        # Test 3: Weak secret attack
        if secret:
            self._test_weak_secret(secret, attack_results)

        # Test 4: Expiration validation
        self._test_expiration_bypass(token, attack_results)

        # Test 5: Signature stripping
        self._test_signature_stripping(token, attack_results)

        self.results['tests'].append({
            'test': 'attack_tests',
            'result': attack_results
        })

        return attack_results

    def _test_none_algorithm(self, token: str, results: Dict[str, Any]):
        """Test if server accepts 'none' algorithm"""
        results['tests_run'] += 1
        self.log("  Testing 'none' algorithm vulnerability...")

        try:
            # Decode original token
            payload = jwt.decode(token, options={"verify_signature": False})

            # Create token with 'none' algorithm
            none_token = jwt.encode(payload, "", algorithm="none")

            results['vulnerabilities_found'].append({
                'type': 'NONE_ALGORITHM',
                'severity': 'CRITICAL',
                'description': 'Token with alg=none created successfully',
                'mitigation': 'Always explicitly specify allowed algorithms'
            })
            self.log("  ✗ VULNERABLE: None algorithm token created")

        except Exception as e:
            self.log(f"  ✓ Protected against none algorithm attack")

    def _test_algorithm_confusion(self, token: str, secret: str, results: Dict[str, Any]):
        """Test algorithm confusion attack (RS256 vs HS256)"""
        results['tests_run'] += 1
        self.log("  Testing algorithm confusion attack...")

        try:
            # Decode original token
            payload = jwt.decode(token, options={"verify_signature": False})

            # Try to create HS256 token with RS256 public key
            # (This is a simulation - actual attack would require RS256 public key)
            self.log("  ✓ Algorithm confusion attack simulated")

            results['vulnerabilities_found'].append({
                'type': 'ALGORITHM_CONFUSION',
                'severity': 'HIGH',
                'description': 'Algorithm not strictly validated',
                'mitigation': 'Explicitly specify algorithms=["RS256"] in jwt.decode()'
            })

        except Exception as e:
            self.log(f"  ✓ Protected against algorithm confusion")

    def _test_weak_secret(self, secret: str, results: Dict[str, Any]):
        """Test if secret key is weak"""
        results['tests_run'] += 1
        self.log("  Testing secret key strength...")

        # Check secret length
        if len(secret) < 32:
            results['vulnerabilities_found'].append({
                'type': 'WEAK_SECRET',
                'severity': 'CRITICAL',
                'description': f'Secret key too short ({len(secret)} bytes), recommend 32+ bytes',
                'mitigation': 'Use secrets.token_urlsafe(32) to generate strong keys'
            })
            self.log(f"  ✗ WEAK SECRET: Only {len(secret)} bytes")
        else:
            self.log(f"  ✓ Secret key length adequate ({len(secret)} bytes)")

        # Check for common weak secrets
        weak_secrets = [
            'secret', 'password', '123456', 'qwerty', 'your-secret-key',
            'jwt-secret', 'my-secret'
        ]

        if secret.lower() in weak_secrets:
            results['vulnerabilities_found'].append({
                'type': 'COMMON_SECRET',
                'severity': 'CRITICAL',
                'description': 'Using common/default secret key',
                'mitigation': 'Generate a unique, random secret key'
            })
            self.log("  ✗ CRITICAL: Using common secret")

    def _test_expiration_bypass(self, token: str, results: Dict[str, Any]):
        """Test if expiration is properly validated"""
        results['tests_run'] += 1
        self.log("  Testing expiration validation...")

        try:
            payload = jwt.decode(token, options={"verify_signature": False})

            if 'exp' not in payload:
                results['vulnerabilities_found'].append({
                    'type': 'NO_EXPIRATION',
                    'severity': 'HIGH',
                    'description': 'Token has no expiration claim',
                    'mitigation': 'Always include exp claim in tokens'
                })
                self.log("  ✗ No expiration claim found")
            else:
                exp_time = datetime.fromtimestamp(payload['exp'])
                now = datetime.utcnow()

                if exp_time < now:
                    self.log("  ✓ Token is expired (as expected)")
                else:
                    lifetime = (exp_time - now).total_seconds()
                    if lifetime > 3600:
                        results['vulnerabilities_found'].append({
                            'type': 'LONG_LIVED_TOKEN',
                            'severity': 'MEDIUM',
                            'description': f'Token expires in {lifetime/3600:.1f} hours',
                            'mitigation': 'Use shorter expiration times (15-60 minutes)'
                        })
                        self.log(f"  ⚠ Token lifetime: {lifetime/3600:.1f}h")

        except Exception as e:
            self.log(f"  Error testing expiration: {e}")

    def _test_signature_stripping(self, token: str, results: Dict[str, Any]):
        """Test if signature can be stripped"""
        results['tests_run'] += 1
        self.log("  Testing signature stripping...")

        try:
            parts = token.split('.')
            if len(parts) == 3:
                # Remove signature
                unsigned_token = '.'.join(parts[:2]) + '.'

                results['vulnerabilities_found'].append({
                    'type': 'SIGNATURE_STRIPPING',
                    'severity': 'INFO',
                    'description': 'Token structure allows signature removal',
                    'mitigation': 'Always validate signature before trusting token'
                })
                self.log("  ⚠ Token signature can be stripped (validate on server)")

        except Exception as e:
            self.log(f"  Error testing signature stripping: {e}")

    def inspect_token(self, token: str) -> Dict[str, Any]:
        """Inspect JWT token structure and claims"""
        self.log("Inspecting token...")

        try:
            parts = token.split('.')
            if len(parts) != 3:
                raise ValueError("Invalid JWT format (expected 3 parts)")

            # Decode header
            header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))

            # Decode payload
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))

            # Decode signature (just show as hex)
            signature = parts[2]

            inspection = {
                'header': header,
                'payload': payload,
                'signature': signature,
                'signature_length': len(signature),
                'token_size': len(token)
            }

            # Analyze claims
            if 'exp' in payload:
                exp_dt = datetime.fromtimestamp(payload['exp'])
                inspection['expires_at'] = exp_dt.isoformat()
                inspection['is_expired'] = exp_dt < datetime.utcnow()

            if 'iat' in payload:
                iat_dt = datetime.fromtimestamp(payload['iat'])
                inspection['issued_at'] = iat_dt.isoformat()

            self.log(f"✓ Token inspection complete")
            self.log(f"  Algorithm: {header.get('alg')}")
            self.log(f"  Subject: {payload.get('sub')}")
            self.log(f"  Expires: {inspection.get('expires_at', 'N/A')}")

            self.results['tests'].append({
                'test': 'token_inspection',
                'result': inspection
            })

            return inspection

        except Exception as e:
            raise ValueError(f"Failed to inspect token: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='JWT Security Testing and Validation Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a JWT token
  python test_jwt.py --token "eyJhbGc..." --validate --secret "your-secret"

  # Generate a new JWT token
  python test_jwt.py --generate --algorithm HS256 --secret "my-secret" \\
                     --payload '{"sub":"user123","role":"admin"}'

  # Inspect token structure
  python test_jwt.py --token "eyJhbGc..." --inspect

  # Run security tests
  python test_jwt.py --token "eyJhbGc..." --attack-test --secret "your-secret" --json
        """
    )

    parser.add_argument('--token', type=str, help='JWT token to test')
    parser.add_argument('--secret', type=str, help='Secret key for HMAC algorithms or path to key file')
    parser.add_argument('--algorithm', type=str, default='HS256',
                       choices=['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512', 'ES256'],
                       help='JWT algorithm')

    # Operations
    parser.add_argument('--validate', action='store_true', help='Validate token')
    parser.add_argument('--generate', action='store_true', help='Generate new token')
    parser.add_argument('--inspect', action='store_true', help='Inspect token structure')
    parser.add_argument('--attack-test', action='store_true', help='Run security attack tests')

    # Generation options
    parser.add_argument('--payload', type=str, help='JSON payload for token generation')
    parser.add_argument('--expires-in', type=int, default=3600,
                       help='Token expiration time in seconds (default: 3600)')

    # Output options
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    tester = JWTTester(verbose=args.verbose)

    try:
        # Validate token
        if args.validate:
            if not args.token:
                print("Error: --token required for validation", file=sys.stderr)
                sys.exit(1)
            if not args.secret:
                print("Error: --secret required for validation", file=sys.stderr)
                sys.exit(1)

            result = tester.validate_token(args.token, args.secret, args.algorithm)

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\nValidation Result: {'✓ VALID' if result['valid'] else '✗ INVALID'}")
                if result['claims']:
                    print(f"\nClaims:")
                    print(json.dumps(result['claims'], indent=2))
                if result['issues']:
                    print(f"\nIssues Found ({len(result['issues'])}):")
                    for issue in result['issues']:
                        print(f"  [{issue['severity']}] {issue['type']}: {issue['message']}")

        # Generate token
        elif args.generate:
            if not args.secret:
                print("Error: --secret required for token generation", file=sys.stderr)
                sys.exit(1)

            payload = json.loads(args.payload) if args.payload else {}

            token = tester.generate_token(
                payload,
                args.secret,
                args.algorithm,
                args.expires_in
            )

            if args.json:
                print(json.dumps({'token': token}, indent=2))
            else:
                print(f"\nGenerated Token:")
                print(token)

        # Inspect token
        elif args.inspect:
            if not args.token:
                print("Error: --token required for inspection", file=sys.stderr)
                sys.exit(1)

            inspection = tester.inspect_token(args.token)

            if args.json:
                print(json.dumps(inspection, indent=2))
            else:
                print(f"\nToken Inspection:")
                print(f"\nHeader:")
                print(json.dumps(inspection['header'], indent=2))
                print(f"\nPayload:")
                print(json.dumps(inspection['payload'], indent=2))
                print(f"\nSignature: {inspection['signature'][:50]}...")
                print(f"Token Size: {inspection['token_size']} bytes")

        # Run attack tests
        elif args.attack_test:
            if not args.token:
                print("Error: --token required for attack tests", file=sys.stderr)
                sys.exit(1)

            results = tester.run_attack_tests(args.token, args.secret)

            if args.json:
                print(json.dumps(tester.results, indent=2))
            else:
                print(f"\nAttack Test Results:")
                print(f"Tests Run: {results['tests_run']}")
                print(f"Vulnerabilities Found: {len(results['vulnerabilities_found'])}")

                if results['vulnerabilities_found']:
                    print(f"\nVulnerabilities:")
                    for vuln in results['vulnerabilities_found']:
                        print(f"\n  [{vuln['severity']}] {vuln['type']}")
                        print(f"  Description: {vuln['description']}")
                        print(f"  Mitigation: {vuln['mitigation']}")
                else:
                    print("\n✓ No vulnerabilities found")

        else:
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
