#!/usr/bin/env python3
"""
PKCE Code Verifier and Challenge Generator

Generates PKCE (Proof Key for Code Exchange) code verifier and code challenge
pairs for OAuth 2.0 authorization code flow with PKCE (RFC 7636).

Usage:
    ./generate_pkce.py
    ./generate_pkce.py --method S256 --verifier-length 64
    ./generate_pkce.py --json
    ./generate_pkce.py --verify CODE_VERIFIER CODE_CHALLENGE

Examples:
    # Generate PKCE pair with default settings (S256, 64 char verifier)
    ./generate_pkce.py

    # Generate with custom verifier length
    ./generate_pkce.py --verifier-length 86

    # Generate with plain method (NOT RECOMMENDED)
    ./generate_pkce.py --method plain

    # Output as JSON
    ./generate_pkce.py --json

    # Verify a PKCE pair
    ./generate_pkce.py --verify "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk" \\
                       "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM" \\
                       --method S256

    # Show complete OAuth flow example
    ./generate_pkce.py --show-flow

Options:
    --method METHOD          Challenge method: S256 or plain (default: S256)
    --verifier-length LENGTH Code verifier length: 43-128 chars (default: 64)
    --json                   Output as JSON
    --verify V C             Verify verifier V produces challenge C
    --show-flow              Show complete OAuth flow with PKCE
    --help                   Show this help message
"""

import argparse
import sys
import secrets
import hashlib
import base64
import json
from typing import Dict, Tuple


def generate_code_verifier(length: int = 64) -> str:
    """
    Generate PKCE code verifier.

    Args:
        length: Verifier length (43-128 characters, default 64)

    Returns:
        Base64URL-encoded random string

    Spec: RFC 7636 Section 4.1
    - Length: 43 to 128 characters
    - Character set: [A-Z] [a-z] [0-9] - . _ ~ (unreserved URI characters)
    - Entropy: Minimum 256 bits recommended
    """
    if not (43 <= length <= 128):
        raise ValueError("Code verifier length must be between 43 and 128 characters")

    # Generate random bytes (ensure sufficient entropy)
    num_bytes = (length * 3) // 4  # Base64 encoding ratio
    random_bytes = secrets.token_bytes(num_bytes)

    # Base64URL encode without padding
    verifier = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')

    # Truncate to exact length
    return verifier[:length]


def generate_code_challenge(verifier: str, method: str = 'S256') -> str:
    """
    Generate PKCE code challenge from verifier.

    Args:
        verifier: Code verifier
        method: Challenge method ('S256' or 'plain')

    Returns:
        Code challenge

    Spec: RFC 7636 Section 4.2
    - S256: BASE64URL(SHA256(ASCII(code_verifier)))
    - plain: code_verifier
    """
    if method == 'S256':
        # SHA-256 hash
        digest = hashlib.sha256(verifier.encode('ascii')).digest()
        # Base64URL encode without padding
        challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
        return challenge

    elif method == 'plain':
        # Plain method: challenge == verifier
        return verifier

    else:
        raise ValueError(f"Unsupported method: {method}. Use 'S256' or 'plain'")


def verify_pkce_pair(verifier: str, challenge: str, method: str = 'S256') -> bool:
    """
    Verify that a code verifier produces the given code challenge.

    Args:
        verifier: Code verifier
        challenge: Code challenge to verify
        method: Challenge method used

    Returns:
        True if verifier produces challenge, False otherwise
    """
    try:
        computed_challenge = generate_code_challenge(verifier, method)
        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(computed_challenge, challenge)
    except Exception:
        return False


def generate_pkce_pair(method: str = 'S256', verifier_length: int = 64) -> Dict[str, str]:
    """
    Generate complete PKCE code verifier and challenge pair.

    Args:
        method: Challenge method ('S256' or 'plain')
        verifier_length: Code verifier length (43-128 chars)

    Returns:
        Dictionary with code_verifier, code_challenge, and code_challenge_method
    """
    verifier = generate_code_verifier(verifier_length)
    challenge = generate_code_challenge(verifier, method)

    return {
        'code_verifier': verifier,
        'code_challenge': challenge,
        'code_challenge_method': method
    }


def show_oauth_flow_example(pkce: Dict[str, str]):
    """Show complete OAuth flow with PKCE"""
    print("\n" + "=" * 70)
    print("Complete OAuth 2.0 Authorization Code Flow with PKCE")
    print("=" * 70)

    print("\n1. Client Generates PKCE Pair:")
    print("-" * 70)
    print(f"   code_verifier: {pkce['code_verifier']}")
    print(f"   code_challenge: {pkce['code_challenge']}")
    print(f"   code_challenge_method: {pkce['code_challenge_method']}")

    print("\n2. Authorization Request (Client → Authorization Server):")
    print("-" * 70)
    print("   GET /authorize?response_type=code")
    print("                 &client_id=CLIENT_ID")
    print("                 &redirect_uri=https://app.example.com/callback")
    print("                 &scope=openid profile email")
    print("                 &state=RANDOM_STATE")
    print(f"                 &code_challenge={pkce['code_challenge']}")
    print(f"                 &code_challenge_method={pkce['code_challenge_method']}")

    print("\n3. User Authenticates and Authorizes")
    print("-" * 70)
    print("   User logs in and grants permissions")

    print("\n4. Authorization Response (Authorization Server → Client):")
    print("-" * 70)
    print("   HTTP/1.1 302 Found")
    print("   Location: https://app.example.com/callback?code=AUTH_CODE&state=RANDOM_STATE")

    print("\n5. Token Request (Client → Authorization Server):")
    print("-" * 70)
    print("   POST /token")
    print("   Content-Type: application/x-www-form-urlencoded")
    print("")
    print("   grant_type=authorization_code")
    print("   &code=AUTH_CODE")
    print("   &redirect_uri=https://app.example.com/callback")
    print("   &client_id=CLIENT_ID")
    print(f"   &code_verifier={pkce['code_verifier']}")

    print("\n6. Server Validates PKCE:")
    print("-" * 70)
    print(f"   Stored challenge: {pkce['code_challenge']}")
    print(f"   Received verifier: {pkce['code_verifier']}")
    print(f"   Computed challenge: {generate_code_challenge(pkce['code_verifier'], pkce['code_challenge_method'])}")
    print("   Validation: ✓ PASS" if verify_pkce_pair(
        pkce['code_verifier'],
        pkce['code_challenge'],
        pkce['code_challenge_method']
    ) else "   Validation: ✗ FAIL")

    print("\n7. Token Response (Authorization Server → Client):")
    print("-" * 70)
    print("   HTTP/1.1 200 OK")
    print("   Content-Type: application/json")
    print("")
    print("   {")
    print('     "access_token": "eyJhbGc...",')
    print('     "token_type": "Bearer",')
    print('     "expires_in": 3600,')
    print('     "refresh_token": "tGzv3JO...",')
    print('     "scope": "openid profile email"')
    print("   }")

    print("\n" + "=" * 70)


def print_pkce_pair(pkce: Dict[str, str], json_output: bool = False):
    """Print PKCE pair in human-readable or JSON format"""

    if json_output:
        print(json.dumps(pkce, indent=2))
    else:
        print("\n" + "=" * 70)
        print("PKCE Code Verifier and Challenge")
        print("=" * 70)
        print(f"\nMethod: {pkce['code_challenge_method']}")
        print(f"\nCode Verifier ({len(pkce['code_verifier'])} chars):")
        print(f"  {pkce['code_verifier']}")
        print(f"\nCode Challenge ({len(pkce['code_challenge'])} chars):")
        print(f"  {pkce['code_challenge']}")

        print("\n" + "-" * 70)
        print("Usage:")
        print("-" * 70)
        print("\n1. Store code_verifier securely (session, secure storage)")
        print("\n2. Send authorization request with code_challenge:")
        print(f"   code_challenge={pkce['code_challenge']}")
        print(f"   code_challenge_method={pkce['code_challenge_method']}")
        print("\n3. Send token request with code_verifier:")
        print(f"   code_verifier={pkce['code_verifier']}")

        print("\n" + "-" * 70)
        print("Security Properties:")
        print("-" * 70)
        print("  ✓ code_verifier: High entropy (cryptographically secure)")
        print("  ✓ code_challenge: One-way transformation (SHA-256)")
        print("  ✓ Verifier length:", len(pkce['code_verifier']), "chars (RFC 7636 compliant)")

        if pkce['code_challenge_method'] == 'plain':
            print("\n  ⚠ WARNING: Plain method is NOT RECOMMENDED")
            print("              Use S256 for production deployments")

        print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='PKCE Code Verifier and Challenge Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--method', choices=['S256', 'plain'], default='S256',
                        help='Code challenge method (default: S256)')
    parser.add_argument('--verifier-length', type=int, default=64,
                        help='Code verifier length: 43-128 chars (default: 64)')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')
    parser.add_argument('--verify', nargs=2, metavar=('VERIFIER', 'CHALLENGE'),
                        help='Verify that verifier produces challenge')
    parser.add_argument('--show-flow', action='store_true',
                        help='Show complete OAuth flow with PKCE')

    args = parser.parse_args()

    try:
        # Verify mode
        if args.verify:
            verifier, challenge = args.verify
            is_valid = verify_pkce_pair(verifier, challenge, args.method)

            if args.json:
                result = {
                    'code_verifier': verifier,
                    'code_challenge': challenge,
                    'code_challenge_method': args.method,
                    'valid': is_valid
                }
                print(json.dumps(result, indent=2))
            else:
                print("\n" + "=" * 70)
                print("PKCE Verification")
                print("=" * 70)
                print(f"\nCode Verifier:  {verifier}")
                print(f"Code Challenge: {challenge}")
                print(f"Method:         {args.method}")

                computed = generate_code_challenge(verifier, args.method)
                print(f"\nComputed Challenge: {computed}")
                print(f"\nResult: {'✓ VALID' if is_valid else '✗ INVALID'}")
                print("=" * 70)

            sys.exit(0 if is_valid else 1)

        # Generate mode
        pkce = generate_pkce_pair(method=args.method, verifier_length=args.verifier_length)

        # Show flow example
        if args.show_flow:
            show_oauth_flow_example(pkce)
        else:
            print_pkce_pair(pkce, json_output=args.json)

        sys.exit(0)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
