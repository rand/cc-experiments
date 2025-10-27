---
name: security-oauth2-implementation
description: OAuth 2.0 implementation including authorization code, client credentials, PKCE, refresh tokens, and security best practices
---

# Security: OAuth 2.0 Implementation

**Scope**: OAuth 2.0 flows, PKCE, token management, authorization server setup
**Lines**: ~400
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Implementing OAuth 2.0 authorization server
- Adding OAuth 2.0 to client applications
- Securing APIs with OAuth 2.0 tokens
- Implementing authorization code flow with PKCE
- Setting up service-to-service authentication (client credentials)
- Implementing refresh token rotation
- Migrating from session-based to token-based auth
- Integrating with third-party OAuth providers

## OAuth 2.0 Fundamentals

### Roles

```python
"""
OAuth 2.0 Four Roles:

1. Resource Owner (User)
   - Owns the protected data
   - Grants access to client applications

2. Client (Application)
   - Requests access to protected resources
   - Types: Confidential (server-side) or Public (mobile/SPA)

3. Authorization Server
   - Authenticates resource owner
   - Issues access tokens to clients

4. Resource Server (API)
   - Hosts protected resources
   - Validates access tokens
"""
```

### Grant Types

#### 1. Authorization Code Flow (Most Secure)

**Use for**: Web applications with server-side backend

```python
"""
Flow:
1. Client redirects user to authorization server
2. User authenticates and authorizes
3. Authorization server redirects back with code
4. Client exchanges code for tokens (server-side)
5. Client uses access token to call API

Security: Code never exposed to browser, client secret required
"""

from flask import Flask, redirect, request, session
import requests
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

AUTH_SERVER = "https://auth.example.com"
CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"
REDIRECT_URI = "https://yourapp.com/callback"

@app.route('/login')
def login():
    """Initiate authorization code flow"""

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    # Build authorization URL
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': 'read write',
        'state': state
    }

    auth_url = f"{AUTH_SERVER}/authorize?" + "&".join(
        f"{k}={v}" for k, v in params.items()
    )

    return redirect(auth_url)

@app.route('/callback')
def callback():
    """Handle authorization callback"""

    # Validate state (CSRF protection)
    if request.args.get('state') != session.get('oauth_state'):
        return "Invalid state", 400

    # Get authorization code
    code = request.args.get('code')
    if not code:
        error = request.args.get('error')
        return f"Authorization failed: {error}", 400

    # Exchange code for tokens
    token_response = requests.post(
        f"{AUTH_SERVER}/token",
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
    )

    if token_response.status_code != 200:
        return "Token exchange failed", 500

    tokens = token_response.json()

    # Store tokens securely
    session['access_token'] = tokens['access_token']
    session['refresh_token'] = tokens.get('refresh_token')

    return redirect('/dashboard')
```

#### 2. Authorization Code Flow with PKCE

**Use for**: Mobile apps, SPAs, any public client

```python
"""
PKCE (Proof Key for Code Exchange) - RFC 7636
Prevents authorization code interception attacks

Additional steps:
1. Client generates code_verifier (random string)
2. Client creates code_challenge = SHA256(code_verifier)
3. Authorization request includes code_challenge
4. Token request includes code_verifier
5. Server validates: SHA256(code_verifier) == code_challenge
"""

import secrets
import hashlib
import base64

def generate_pkce_pair():
    """Generate PKCE code verifier and challenge"""

    # Generate code verifier (43-128 chars)
    code_verifier = secrets.token_urlsafe(64)  # 86 chars

    # Create code challenge (S256 method)
    challenge_bytes = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode().rstrip('=')

    return code_verifier, code_challenge

# Client initiates flow
code_verifier, code_challenge = generate_pkce_pair()

# Step 1: Authorization request with challenge
auth_params = {
    'response_type': 'code',
    'client_id': CLIENT_ID,
    'redirect_uri': REDIRECT_URI,
    'scope': 'read write',
    'state': state,
    'code_challenge': code_challenge,
    'code_challenge_method': 'S256'  # SHA-256
}

# Step 2: Token request with verifier
token_data = {
    'grant_type': 'authorization_code',
    'code': authorization_code,
    'redirect_uri': REDIRECT_URI,
    'client_id': CLIENT_ID,
    'code_verifier': code_verifier  # Server validates this
}
```

#### 3. Client Credentials Flow

**Use for**: Server-to-server authentication, no user involved

```python
"""
Flow:
1. Client sends credentials to token endpoint
2. Authorization server validates and issues token
3. Client uses token to access API

No user interaction - machine-to-machine
"""

import requests
from requests.auth import HTTPBasicAuth

def get_access_token(client_id: str, client_secret: str, scope: str = None):
    """Get access token using client credentials"""

    response = requests.post(
        f"{AUTH_SERVER}/token",
        auth=HTTPBasicAuth(client_id, client_secret),
        data={
            'grant_type': 'client_credentials',
            'scope': scope or 'api:read api:write'
        }
    )

    response.raise_for_status()
    return response.json()['access_token']

# Usage
token = get_access_token(CLIENT_ID, CLIENT_SECRET)

# Use token for API calls
api_response = requests.get(
    "https://api.example.com/resource",
    headers={'Authorization': f'Bearer {token}'}
)
```

#### 4. Refresh Token Flow

**Use for**: Obtaining new access token without re-authentication

```python
"""
Refresh Token Strategy:
- Access tokens: Short-lived (5-15 minutes)
- Refresh tokens: Long-lived (days/weeks/months)
- Use refresh token to get new access token
- Implement refresh token rotation for security
"""

def refresh_access_token(refresh_token: str):
    """Exchange refresh token for new access token"""

    response = requests.post(
        f"{AUTH_SERVER}/token",
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
    )

    if response.status_code != 200:
        # Refresh token invalid/expired - user must re-authenticate
        return None

    tokens = response.json()

    return {
        'access_token': tokens['access_token'],
        'refresh_token': tokens.get('refresh_token'),  # May rotate
        'expires_in': tokens['expires_in']
    }

# Automatic token refresh wrapper
class OAuth2Client:
    """OAuth 2.0 client with automatic token refresh"""

    def __init__(self, access_token, refresh_token, expires_at):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at

    def get_valid_token(self):
        """Get access token, refreshing if needed"""
        import time

        if time.time() >= self.expires_at - 60:  # Refresh 1 min early
            tokens = refresh_access_token(self.refresh_token)

            if not tokens:
                raise Exception("Refresh token expired")

            self.access_token = tokens['access_token']
            self.refresh_token = tokens['refresh_token']
            self.expires_at = time.time() + tokens['expires_in']

        return self.access_token

    def api_call(self, url, **kwargs):
        """Make API call with automatic token refresh"""
        token = self.get_valid_token()

        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {token}'
        kwargs['headers'] = headers

        return requests.get(url, **kwargs)
```

## Authorization Server Implementation

### Simple Authorization Server (Python)

```python
from flask import Flask, request, jsonify, redirect
from datetime import datetime, timedelta
import secrets
import hashlib
import sqlite3

app = Flask(__name__)

class AuthorizationServer:
    """Minimal OAuth 2.0 authorization server"""

    def __init__(self):
        self.codes = {}  # {code: {client_id, redirect_uri, user_id, code_challenge}}
        self.tokens = {}  # {token: {user_id, client_id, scope, expires}}
        self.clients = {
            'client123': {
                'secret': 'secret456',
                'redirect_uris': ['https://client.example.com/callback']
            }
        }

    def validate_client(self, client_id, client_secret=None):
        """Validate client credentials"""
        if client_id not in self.clients:
            return False

        if client_secret:
            return self.clients[client_id]['secret'] == client_secret

        return True

    def validate_redirect_uri(self, client_id, redirect_uri):
        """Validate redirect URI (exact match)"""
        allowed = self.clients[client_id]['redirect_uris']
        return redirect_uri in allowed

    def generate_authorization_code(self, client_id, redirect_uri, user_id,
                                   code_challenge=None):
        """Generate authorization code"""
        code = secrets.token_urlsafe(32)

        self.codes[code] = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'user_id': user_id,
            'code_challenge': code_challenge,
            'expires': datetime.now() + timedelta(minutes=10)
        }

        return code

    def verify_pkce(self, code_verifier, code_challenge):
        """Verify PKCE code challenge"""
        # S256: BASE64URL(SHA256(code_verifier)) == code_challenge
        challenge_bytes = hashlib.sha256(code_verifier.encode()).digest()
        computed_challenge = base64.urlsafe_b64encode(challenge_bytes).decode().rstrip('=')

        return computed_challenge == code_challenge

    def generate_token(self, user_id, client_id, scope):
        """Generate access token"""
        token = secrets.token_urlsafe(32)

        self.tokens[token] = {
            'user_id': user_id,
            'client_id': client_id,
            'scope': scope,
            'expires': datetime.now() + timedelta(hours=1)
        }

        return token

auth_server = AuthorizationServer()

@app.route('/authorize')
def authorize():
    """Authorization endpoint"""

    # Validate parameters
    response_type = request.args.get('response_type')
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri')
    state = request.args.get('state')
    code_challenge = request.args.get('code_challenge')

    # Validate client
    if not auth_server.validate_client(client_id):
        return "Invalid client", 400

    # Validate redirect URI
    if not auth_server.validate_redirect_uri(client_id, redirect_uri):
        return "Invalid redirect URI", 400

    # Validate response type
    if response_type != 'code':
        return redirect(f"{redirect_uri}?error=unsupported_response_type&state={state}")

    # TODO: Authenticate user and get consent
    user_id = "user123"  # From session after login

    # Generate authorization code
    code = auth_server.generate_authorization_code(
        client_id, redirect_uri, user_id, code_challenge
    )

    # Redirect back to client
    callback_url = f"{redirect_uri}?code={code}"
    if state:
        callback_url += f"&state={state}"

    return redirect(callback_url)

@app.route('/token', methods=['POST'])
def token():
    """Token endpoint"""

    grant_type = request.form.get('grant_type')

    if grant_type == 'authorization_code':
        return handle_authorization_code_grant()
    elif grant_type == 'client_credentials':
        return handle_client_credentials_grant()
    elif grant_type == 'refresh_token':
        return handle_refresh_token_grant()
    else:
        return jsonify({'error': 'unsupported_grant_type'}), 400

def handle_authorization_code_grant():
    """Handle authorization code grant"""

    code = request.form.get('code')
    redirect_uri = request.form.get('redirect_uri')
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')
    code_verifier = request.form.get('code_verifier')

    # Validate client
    if not auth_server.validate_client(client_id, client_secret):
        return jsonify({'error': 'invalid_client'}), 401

    # Validate code
    if code not in auth_server.codes:
        return jsonify({'error': 'invalid_grant'}), 400

    code_data = auth_server.codes[code]

    # Check expiration
    if datetime.now() > code_data['expires']:
        del auth_server.codes[code]
        return jsonify({'error': 'invalid_grant'}), 400

    # Validate redirect URI
    if code_data['redirect_uri'] != redirect_uri:
        return jsonify({'error': 'invalid_grant'}), 400

    # Validate PKCE if used
    if code_data['code_challenge']:
        if not code_verifier:
            return jsonify({'error': 'invalid_request'}), 400

        if not auth_server.verify_pkce(code_verifier, code_data['code_challenge']):
            return jsonify({'error': 'invalid_grant'}), 400

    # Generate tokens
    access_token = auth_server.generate_token(
        code_data['user_id'], client_id, 'read write'
    )
    refresh_token = secrets.token_urlsafe(32)

    # Delete used code (single use)
    del auth_server.codes[code]

    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 3600,
        'refresh_token': refresh_token
    })
```

## Token Validation

### Resource Server Token Validation

```python
from functools import wraps
from flask import request, jsonify
import jwt

def require_oauth(scope_required=None):
    """Decorator to protect endpoints with OAuth"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract token from header
            auth_header = request.headers.get('Authorization')

            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'missing_token'}), 401

            token = auth_header[7:]  # Remove 'Bearer '

            # Validate token
            try:
                # Option 1: JWT validation (if using JWTs)
                payload = jwt.decode(
                    token,
                    PUBLIC_KEY,
                    algorithms=['RS256'],
                    audience='https://api.example.com'
                )

                # Option 2: Token introspection (opaque tokens)
                # payload = introspect_token(token)

            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'token_expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'invalid_token'}), 401

            # Validate scope
            if scope_required:
                token_scopes = payload.get('scope', '').split()
                if scope_required not in token_scopes:
                    return jsonify({'error': 'insufficient_scope'}), 403

            # Add user info to request context
            request.oauth_user_id = payload.get('sub')
            request.oauth_scope = payload.get('scope')

            return f(*args, **kwargs)

        return decorated_function
    return decorator

# Usage
@app.route('/api/protected')
@require_oauth(scope_required='read')
def protected_endpoint():
    user_id = request.oauth_user_id
    return jsonify({'user_id': user_id, 'data': 'sensitive'})
```

## Security Best Practices

### OAuth 2.0 Security Checklist

```python
"""
CRITICAL Security Requirements:

1. Always use HTTPS (TLS 1.2+)
   - Never send tokens/codes over HTTP
   - Use HSTS headers

2. Validate redirect URIs (EXACT match)
   - No wildcards or pattern matching
   - Store allowed URIs in database

3. Use state parameter (CSRF protection)
   - Generate random state for each request
   - Validate in callback

4. Implement PKCE for ALL clients
   - Mandatory for public clients (mobile/SPA)
   - Recommended for confidential clients

5. Short-lived access tokens
   - 5-15 minutes maximum
   - Use refresh tokens for longevity

6. Refresh token rotation
   - Issue new refresh token on use
   - Revoke old refresh token
   - Detect token theft (family tracking)

7. Token storage
   - Hash refresh tokens in database (SHA-256)
   - Never store tokens in localStorage (XSS risk)
   - Use httpOnly cookies or secure storage

8. Client authentication
   - Require client_secret for confidential clients
   - Validate credentials on every request

9. Rate limiting
   - Limit token requests per client
   - Detect brute force attacks

10. Scope validation
    - Validate requested scopes
    - Enforce least privilege
    - Check scopes on resource access
"""
```

### Common Vulnerabilities

```python
"""
Common OAuth 2.0 Vulnerabilities:

1. Authorization Code Interception
   Attack: Intercept code in redirect
   Mitigation: PKCE

2. Redirect URI Manipulation
   Attack: Change redirect_uri to attacker domain
   Mitigation: Exact URI matching

3. State Parameter Missing
   Attack: CSRF on OAuth flow
   Mitigation: Always use state parameter

4. Token Leakage
   Attack: Tokens in URLs, logs, referrer
   Mitigation: Use POST for tokens, no tokens in URLs

5. Insufficient Redirect URI Validation
   Attack: Open redirect to steal codes
   Mitigation: Strict whitelist validation

6. Refresh Token Reuse
   Attack: Stolen refresh token used indefinitely
   Mitigation: Token rotation, family tracking

7. Scope Escalation
   Attack: Request excessive scopes
   Mitigation: User consent, scope validation
"""
```

## Related Skills

- `security-authentication.md` - Authentication patterns, JWT, sessions
- `api-authentication.md` - API authentication strategies
- `security-secrets-management.md` - Storing client secrets, tokens
- `api-rest-design.md` - RESTful API design with OAuth

## Level 3: Resources

### Comprehensive Reference

**Location**: `skills/security/oauth2-implementation/resources/REFERENCE.md`

The REFERENCE.md file (3,200+ lines) provides exhaustive coverage of:
- Complete OAuth 2.0 specification (RFC 6749) with all grant types
- Authorization code flow with detailed sequence diagrams
- Client credentials flow for machine-to-machine authentication
- Device authorization flow (RFC 8628) for limited-input devices
- PKCE specification (RFC 7636) with S256 and plain methods
- Refresh token rotation and family tracking
- Token introspection (RFC 7662) and revocation (RFC 7009)
- Scope design best practices and hierarchies
- Security considerations from RFC 6819
- OAuth 2.1 draft updates and deprecations
- JWT vs opaque tokens comparison
- Authorization server implementation patterns
- Client libraries for Python, Node.js, Go, Java
- Integration with Keycloak, Auth0, Okta, ORY Hydra
- OpenID Connect (OIDC) layer on OAuth 2.0
- Token binding and proof-of-possession
- Attack vectors and mitigations (code interception, CSRF, etc.)
- Production deployment considerations
- Monitoring and logging OAuth flows

### Executable Scripts

**Location**: `skills/security/oauth2-implementation/resources/scripts/`

1. **validate_oauth_config.py** - OAuth 2.0 server configuration validator
   - Validates authorization server configuration files
   - Checks grant type security settings
   - Validates redirect URI patterns and security
   - Detects missing PKCE enforcement
   - Audits token lifetime configurations
   - Validates CORS settings for token endpoints
   - Checks client secret strength
   - Provides security recommendations
   - Supports JSON output for CI/CD
   - Usage: `./validate_oauth_config.py --config-file oauth-server.conf --json`

2. **test_oauth_flow.py** - OAuth 2.0 flow end-to-end testing
   - Tests authorization code flow with PKCE
   - Tests client credentials flow
   - Tests refresh token rotation
   - Validates token response format and claims
   - Tests token revocation endpoints
   - Validates state parameter handling
   - Checks PKCE challenge verification
   - Generates detailed test reports
   - Supports multiple authorization servers
   - Usage: `./test_oauth_flow.py --authorization-server https://auth.example.com --flow authorization_code --json`

3. **generate_pkce.py** - PKCE challenge and verifier generator
   - Generates cryptographically secure code_verifier
   - Creates code_challenge using S256 or plain method
   - Validates PKCE pairs for testing
   - Shows complete OAuth flow with PKCE
   - Supports custom verifier lengths (43-128 chars)
   - Includes verification function
   - Provides usage examples
   - Usage: `./generate_pkce.py --method S256 --verifier-length 64 --json`

### Production-Ready Examples

**Location**: `skills/security/oauth2-implementation/resources/examples/`

1. **python/authorization_code_flow.py** - Complete auth code flow with PKCE
   - Flask-based client implementation
   - PKCE generation and validation
   - State parameter CSRF protection
   - Automatic token refresh
   - Secure token storage patterns
   - Error handling and retry logic

2. **python/client_credentials.py** - Service-to-service authentication
   - Client credentials flow implementation
   - Token caching with expiration
   - Automatic token refresh
   - Rate limiting and backoff
   - Connection pooling

3. **python/resource_server.py** - Protected API with token validation
   - JWT validation with RS256
   - Token introspection support
   - Scope-based authorization
   - Rate limiting per client
   - Comprehensive error responses

4. **nodejs/oauth-server.js** - OAuth server with node-oauth2-server
   - Complete authorization server
   - All grant types supported
   - PKCE validation
   - Refresh token rotation
   - PostgreSQL token storage

5. **python/refresh_token_rotation.py** - Secure refresh token handling
   - Refresh token rotation pattern
   - Token family tracking (theft detection)
   - Automatic revocation on compromise
   - Database schema included

6. **config/keycloak-realm.json** - Keycloak realm configuration
   - Production-ready realm setup
   - Client configurations for web, mobile, SPA
   - Scope definitions
   - Token lifetimes
   - PKCE enforcement

7. **typescript/react-oauth-client.tsx** - React OAuth integration
   - React hooks for OAuth flow
   - PKCE implementation
   - Token storage in memory
   - Automatic token refresh
   - Protected route components

8. **docker/docker-compose.yml** - Complete OAuth environment
   - Authorization server (Keycloak)
   - Resource server (API)
   - Client application
   - PostgreSQL database
   - Nginx reverse proxy

All examples are production-ready, fully commented, and include error handling.

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
