"""
OAuth 2.0 Authorization Code Flow with PKCE - Production Example

Complete implementation of OAuth 2.0 authorization code flow with PKCE for
web applications using Flask. Includes state parameter, PKCE, automatic token
refresh, and secure token storage.

Usage:
    python authorization_code_flow.py

Dependencies:
    pip install flask requests

Environment Variables:
    OAUTH_CLIENT_ID          OAuth client ID
    OAUTH_CLIENT_SECRET      OAuth client secret (optional for public clients)
    OAUTH_AUTH_SERVER        Authorization server base URL
    OAUTH_REDIRECT_URI       Redirect URI
    FLASK_SECRET_KEY         Flask session secret key
"""

from flask import Flask, request, redirect, session, jsonify, url_for
import requests
import secrets
import hashlib
import base64
import time
import os
from typing import Dict, Optional
from functools import wraps
from urllib.parse import urlencode


# Configuration
AUTH_SERVER_BASE = os.getenv('OAUTH_AUTH_SERVER', 'https://auth.example.com')
CLIENT_ID = os.getenv('OAUTH_CLIENT_ID', 'your-client-id')
CLIENT_SECRET = os.getenv('OAUTH_CLIENT_SECRET')  # Optional for public clients
REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:5000/callback')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Flask app
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY


class PKCEGenerator:
    """PKCE code verifier and challenge generator"""

    @staticmethod
    def generate_verifier(length: int = 64) -> str:
        """Generate code verifier (43-128 chars)"""
        random_bytes = secrets.token_bytes(32)
        verifier = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
        return verifier[:max(43, min(128, length))]

    @staticmethod
    def generate_challenge(verifier: str) -> str:
        """Generate S256 code challenge from verifier"""
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
        return challenge


class OAuth2Client:
    """OAuth 2.0 client with authorization code flow and PKCE"""

    def __init__(self, auth_server: str, client_id: str, client_secret: Optional[str],
                 redirect_uri: str):
        self.auth_server = auth_server.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, scope: str = 'openid profile email') -> tuple:
        """
        Generate authorization URL with PKCE.

        Returns:
            Tuple of (authorization_url, state, code_verifier)
        """
        # Generate PKCE pair
        code_verifier = PKCEGenerator.generate_verifier()
        code_challenge = PKCEGenerator.generate_challenge(code_verifier)

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': scope,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }

        auth_url = f"{self.auth_server}/authorize?{urlencode(params)}"

        return auth_url, state, code_verifier

    def exchange_code_for_tokens(self, code: str, code_verifier: str) -> Dict:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code
            code_verifier: PKCE code verifier

        Returns:
            Token response dict

        Raises:
            Exception if token exchange fails
        """
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'code_verifier': code_verifier
        }

        # Add client secret if available (confidential client)
        if self.client_secret:
            token_data['client_secret'] = self.client_secret

        response = requests.post(
            f"{self.auth_server}/token",
            data=token_data,
            headers={'Accept': 'application/json'},
            timeout=10
        )

        if response.status_code != 200:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('error_description', error_data.get('error', 'Token exchange failed'))
            raise Exception(f"Token exchange failed: {error_msg}")

        return response.json()

    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            New token response dict

        Raises:
            Exception if refresh fails
        """
        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id
        }

        if self.client_secret:
            token_data['client_secret'] = self.client_secret

        response = requests.post(
            f"{self.auth_server}/token",
            data=token_data,
            timeout=10
        )

        if response.status_code != 200:
            raise Exception("Token refresh failed")

        return response.json()

    def revoke_token(self, token: str, token_type_hint: str = 'access_token'):
        """Revoke access or refresh token"""
        revoke_data = {
            'token': token,
            'token_type_hint': token_type_hint,
            'client_id': self.client_id
        }

        if self.client_secret:
            revoke_data['client_secret'] = self.client_secret

        requests.post(
            f"{self.auth_server}/revoke",
            data=revoke_data,
            timeout=10
        )


# Global OAuth client
oauth_client = OAuth2Client(
    auth_server=AUTH_SERVER_BASE,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI
)


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            return redirect(url_for('login'))

        # Check token expiration
        if time.time() >= session.get('token_expires_at', 0):
            # Token expired - attempt refresh
            if 'refresh_token' in session:
                try:
                    tokens = oauth_client.refresh_access_token(session['refresh_token'])
                    store_tokens(tokens)
                except Exception:
                    # Refresh failed - require re-login
                    session.clear()
                    return redirect(url_for('login'))
            else:
                # No refresh token - require re-login
                session.clear()
                return redirect(url_for('login'))

        return f(*args, **kwargs)

    return decorated_function


def store_tokens(tokens: Dict):
    """Store OAuth tokens in session"""
    session['access_token'] = tokens['access_token']
    session['token_type'] = tokens.get('token_type', 'Bearer')
    session['token_expires_at'] = time.time() + tokens.get('expires_in', 3600)

    if 'refresh_token' in tokens:
        session['refresh_token'] = tokens['refresh_token']

    if 'scope' in tokens:
        session['scope'] = tokens['scope']


@app.route('/')
def index():
    """Home page"""
    if 'access_token' in session:
        return f"""
        <h1>OAuth 2.0 Demo</h1>
        <p>You are authenticated!</p>
        <p>Access Token: {session['access_token'][:20]}...</p>
        <p>Token Type: {session.get('token_type')}</p>
        <p>Scope: {session.get('scope')}</p>
        <p>Expires: {session.get('token_expires_at') - time.time():.0f}s</p>
        <p><a href="/userinfo">Get User Info</a></p>
        <p><a href="/logout">Logout</a></p>
        """
    else:
        return """
        <h1>OAuth 2.0 Demo</h1>
        <p>You are not authenticated.</p>
        <p><a href="/login">Login with OAuth</a></p>
        """


@app.route('/login')
def login():
    """Initiate OAuth authorization code flow"""

    # Generate authorization URL with PKCE
    auth_url, state, code_verifier = oauth_client.get_authorization_url()

    # Store state and code_verifier in session
    session['oauth_state'] = state
    session['pkce_code_verifier'] = code_verifier

    # Redirect to authorization server
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """Handle OAuth callback"""

    # Validate state (CSRF protection)
    received_state = request.args.get('state')
    expected_state = session.pop('oauth_state', None)

    if not received_state or received_state != expected_state:
        return jsonify({'error': 'Invalid state parameter'}), 400

    # Check for authorization errors
    error = request.args.get('error')
    if error:
        error_description = request.args.get('error_description', 'Unknown error')
        return jsonify({
            'error': error,
            'error_description': error_description
        }), 400

    # Get authorization code
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'Missing authorization code'}), 400

    # Retrieve code_verifier
    code_verifier = session.pop('pkce_code_verifier', None)
    if not code_verifier:
        return jsonify({'error': 'Missing code_verifier'}), 400

    # Exchange code for tokens
    try:
        tokens = oauth_client.exchange_code_for_tokens(code, code_verifier)
        store_tokens(tokens)
        return redirect(url_for('index'))

    except Exception as e:
        return jsonify({'error': 'Token exchange failed', 'details': str(e)}), 500


@app.route('/userinfo')
@require_auth
def userinfo():
    """Get user info from resource server"""

    # Call userinfo endpoint with access token
    try:
        response = requests.get(
            f"{AUTH_SERVER_BASE}/userinfo",
            headers={'Authorization': f"Bearer {session['access_token']}"},
            timeout=10
        )

        if response.status_code == 200:
            user_data = response.json()
            return jsonify(user_data)
        else:
            return jsonify({'error': 'Failed to fetch user info'}), response.status_code

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/logout')
def logout():
    """Logout user and revoke tokens"""

    # Revoke tokens
    if 'refresh_token' in session:
        try:
            oauth_client.revoke_token(session['refresh_token'], 'refresh_token')
        except Exception:
            pass

    if 'access_token' in session:
        try:
            oauth_client.revoke_token(session['access_token'], 'access_token')
        except Exception:
            pass

    # Clear session
    session.clear()

    return redirect(url_for('index'))


@app.route('/api/protected')
@require_auth
def protected_api():
    """Example protected API endpoint"""
    return jsonify({
        'message': 'This is a protected resource',
        'user_token': session['access_token'][:20] + '...'
    })


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("OAuth 2.0 Authorization Code Flow with PKCE - Demo Server")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Authorization Server: {AUTH_SERVER_BASE}")
    print(f"  Client ID:            {CLIENT_ID}")
    print(f"  Redirect URI:         {REDIRECT_URI}")
    print(f"  Client Type:          {'Confidential' if CLIENT_SECRET else 'Public'}")
    print("\nEndpoints:")
    print(f"  Home:      http://localhost:5000/")
    print(f"  Login:     http://localhost:5000/login")
    print(f"  Callback:  http://localhost:5000/callback")
    print(f"  User Info: http://localhost:5000/userinfo")
    print(f"  Logout:    http://localhost:5000/logout")
    print("\n" + "=" * 70 + "\n")

    app.run(debug=True, port=5000)
