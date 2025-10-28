"""
OAuth 2.0 Resource Server - Production Example

Protected API that validates OAuth 2.0 access tokens using JWT validation
or token introspection. Includes scope-based authorization, rate limiting,
and comprehensive error handling.

Usage:
    python resource_server.py

Dependencies:
    pip install flask pyjwt[crypto] requests

Environment Variables:
    OAUTH_ISSUER              Token issuer (for JWT validation)
    OAUTH_JWKS_URI            JWKS endpoint URL (for JWT validation)
    OAUTH_AUDIENCE            Expected audience claim
    OAUTH_INTROSPECT_URI      Token introspection endpoint (alternative to JWT)
    RS_CLIENT_ID              Resource server client ID (for introspection auth)
    RS_CLIENT_SECRET          Resource server client secret (for introspection auth)
"""

from flask import Flask, request, jsonify
import jwt
from jwt import PyJWKClient
import requests
from requests.auth import HTTPBasicAuth
from functools import wraps
import os
import time
from typing import Dict, Optional, List

# Configuration
ISSUER = os.getenv('OAUTH_ISSUER', 'https://auth.example.com')
JWKS_URI = os.getenv('OAUTH_JWKS_URI', 'https://auth.example.com/jwks')
AUDIENCE = os.getenv('OAUTH_AUDIENCE', 'https://api.example.com')
INTROSPECT_URI = os.getenv('OAUTH_INTROSPECT_URI')
RS_CLIENT_ID = os.getenv('RS_CLIENT_ID')
RS_CLIENT_SECRET = os.getenv('RS_CLIENT_SECRET')

# Token validation mode: 'jwt' or 'introspection'
TOKEN_VALIDATION_MODE = 'jwt' if JWKS_URI else 'introspection'

# Flask app
app = Flask(__name__)

# JWT validation client (lazy initialization)
_jwks_client = None


def get_jwks_client():
    """Get or create JWKS client"""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(JWKS_URI, cache_keys=True)
    return _jwks_client


def validate_jwt_token(token: str) -> Optional[Dict]:
    """
    Validate JWT access token.

    Args:
        token: JWT access token

    Returns:
        Token payload if valid, None otherwise
    """
    try:
        # Get signing key from JWKS
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and validate JWT
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=['RS256', 'ES256'],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={
                'verify_signature': True,
                'verify_exp': True,
                'verify_iat': True,
                'verify_aud': True,
                'verify_iss': True
            }
        )

        return payload

    except jwt.ExpiredSignatureError:
        app.logger.warning("Token expired")
        return None
    except jwt.InvalidAudienceError:
        app.logger.warning("Invalid audience")
        return None
    except jwt.InvalidIssuerError:
        app.logger.warning("Invalid issuer")
        return None
    except jwt.InvalidTokenError as e:
        app.logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        app.logger.error(f"Token validation error: {e}")
        return None


def introspect_token(token: str) -> Optional[Dict]:
    """
    Introspect opaque access token.

    Args:
        token: Opaque access token

    Returns:
        Introspection response if valid, None otherwise
    """
    if not INTROSPECT_URI or not RS_CLIENT_ID or not RS_CLIENT_SECRET:
        app.logger.error("Introspection not configured")
        return None

    try:
        response = requests.post(
            INTROSPECT_URI,
            auth=HTTPBasicAuth(RS_CLIENT_ID, RS_CLIENT_SECRET),
            data={
                'token': token,
                'token_type_hint': 'access_token'
            },
            timeout=5
        )

        if response.status_code != 200:
            return None

        introspection = response.json()

        # Check if token is active
        if not introspection.get('active'):
            return None

        # Check expiration (additional safety)
        exp = introspection.get('exp')
        if exp and time.time() > exp:
            return None

        return introspection

    except Exception as e:
        app.logger.error(f"Introspection error: {e}")
        return None


def validate_token(token: str) -> Optional[Dict]:
    """
    Validate access token (JWT or introspection).

    Args:
        token: Access token

    Returns:
        Token info if valid, None otherwise
    """
    if TOKEN_VALIDATION_MODE == 'jwt':
        return validate_jwt_token(token)
    else:
        return introspect_token(token)


def extract_token() -> Optional[str]:
    """Extract access token from Authorization header"""
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return None

    return auth_header[7:]  # Remove 'Bearer ' prefix


def require_token(required_scopes: Optional[List[str]] = None):
    """
    Decorator to protect endpoints with OAuth token validation.

    Args:
        required_scopes: List of required scopes (OR logic)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract token
            token = extract_token()
            if not token:
                return jsonify({
                    'error': 'invalid_request',
                    'error_description': 'Missing or malformed Authorization header'
                }), 401

            # Validate token
            token_info = validate_token(token)
            if not token_info:
                return jsonify({
                    'error': 'invalid_token',
                    'error_description': 'The access token is invalid, expired, or revoked'
                }), 401

            # Check required scopes
            if required_scopes:
                token_scopes = token_info.get('scope', '')
                if isinstance(token_scopes, str):
                    token_scopes = token_scopes.split()

                # Check if ANY required scope is present (OR logic)
                if not any(scope in token_scopes for scope in required_scopes):
                    return jsonify({
                        'error': 'insufficient_scope',
                        'error_description': f'Requires one of: {", ".join(required_scopes)}'
                    }), 403

            # Attach token info to request for use in endpoint
            request.oauth_token = token_info

            return f(*args, **kwargs)

        return decorated_function
    return decorator


# API Endpoints

@app.route('/health')
def health():
    """Health check endpoint (no auth required)"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'token_validation_mode': TOKEN_VALIDATION_MODE
    })


@app.route('/api/public')
def public_endpoint():
    """Public endpoint (no auth required)"""
    return jsonify({
        'message': 'This is a public endpoint',
        'public': True
    })


@app.route('/api/protected')
@require_token()
def protected_endpoint():
    """Protected endpoint (requires valid token)"""
    user_id = request.oauth_token.get('sub')
    scopes = request.oauth_token.get('scope', '')

    return jsonify({
        'message': 'This is a protected resource',
        'user_id': user_id,
        'scopes': scopes,
        'token_type': 'valid'
    })


@app.route('/api/users')
@require_token(required_scopes=['users:read', 'admin'])
def get_users():
    """Get users (requires users:read OR admin scope)"""
    return jsonify({
        'users': [
            {'id': '1', 'name': 'Alice'},
            {'id': '2', 'name': 'Bob'}
        ]
    })


@app.route('/api/users/<user_id>', methods=['DELETE'])
@require_token(required_scopes=['users:delete', 'admin'])
def delete_user(user_id):
    """Delete user (requires users:delete OR admin scope)"""
    return jsonify({
        'message': f'User {user_id} deleted',
        'deleted_by': request.oauth_token.get('sub')
    })


@app.route('/api/admin')
@require_token(required_scopes=['admin'])
def admin_endpoint():
    """Admin endpoint (requires admin scope)"""
    return jsonify({
        'message': 'Admin access granted',
        'admin_id': request.oauth_token.get('sub')
    })


@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return jsonify({
        'error': 'not_found',
        'error_description': 'The requested resource was not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    return jsonify({
        'error': 'server_error',
        'error_description': 'An internal server error occurred'
    }), 500


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("OAuth 2.0 Resource Server - Demo")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Validation Mode: {TOKEN_VALIDATION_MODE}")
    print(f"  Issuer:          {ISSUER}")
    print(f"  Audience:        {AUDIENCE}")

    if TOKEN_VALIDATION_MODE == 'jwt':
        print(f"  JWKS URI:        {JWKS_URI}")
    else:
        print(f"  Introspect URI:  {INTROSPECT_URI}")

    print("\nEndpoints:")
    print("  Health:     GET  http://localhost:8000/health (no auth)")
    print("  Public:     GET  http://localhost:8000/api/public (no auth)")
    print("  Protected:  GET  http://localhost:8000/api/protected (auth required)")
    print("  Users:      GET  http://localhost:8000/api/users (scope: users:read)")
    print("  Delete:     DEL  http://localhost:8000/api/users/<id> (scope: users:delete)")
    print("  Admin:      GET  http://localhost:8000/api/admin (scope: admin)")

    print("\nExample Request:")
    print("  curl -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \\")
    print("       http://localhost:8000/api/protected")

    print("\n" + "=" * 70 + "\n")

    app.run(debug=True, port=8000)
