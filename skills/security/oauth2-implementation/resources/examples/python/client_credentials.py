"""
OAuth 2.0 Client Credentials Flow - Production Example

Service-to-service authentication using client credentials grant.
Includes token caching, automatic refresh, rate limiting, and error handling.

Usage:
    python client_credentials.py

Dependencies:
    pip install requests

Environment Variables:
    OAUTH_CLIENT_ID          Service client ID
    OAUTH_CLIENT_SECRET      Service client secret
    OAUTH_TOKEN_URL          Token endpoint URL
    OAUTH_SCOPE              Requested scopes (optional)
"""

import requests
from requests.auth import HTTPBasicAuth
import time
import os
from typing import Optional, Dict
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
TOKEN_URL = os.getenv('OAUTH_TOKEN_URL', 'https://auth.example.com/token')
CLIENT_ID = os.getenv('OAUTH_CLIENT_ID', 'service-client-id')
CLIENT_SECRET = os.getenv('OAUTH_CLIENT_SECRET', 'service-client-secret')
SCOPE = os.getenv('OAUTH_SCOPE', 'api:read api:write')


class TokenCache:
    """Simple in-memory token cache"""

    def __init__(self, ttl_buffer: int = 60):
        self.token: Optional[str] = None
        self.expires_at: float = 0
        self.ttl_buffer = ttl_buffer  # Refresh token N seconds before expiration

    def get(self) -> Optional[str]:
        """Get cached token if still valid"""
        if self.token and time.time() < (self.expires_at - self.ttl_buffer):
            return self.token
        return None

    def set(self, token: str, expires_in: int):
        """Cache token with expiration"""
        self.token = token
        self.expires_at = time.time() + expires_in

    def clear(self):
        """Clear cached token"""
        self.token = None
        self.expires_at = 0


class ClientCredentialsClient:
    """
    OAuth 2.0 Client Credentials Client

    Handles client credentials flow with:
    - Automatic token refresh
    - Token caching
    - Retry logic with exponential backoff
    - Rate limiting
    - Connection pooling
    """

    def __init__(self, token_url: str, client_id: str, client_secret: str,
                 scope: Optional[str] = None, cache_ttl_buffer: int = 60):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.cache = TokenCache(ttl_buffer=cache_ttl_buffer)

        # Connection pooling for performance
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(client_id, client_secret)

        # Rate limiting state
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests

    def _wait_for_rate_limit(self):
        """Implement basic rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get access token, requesting new one if needed.

        Args:
            force_refresh: Force token refresh even if cached token is valid

        Returns:
            Access token

        Raises:
            Exception if token request fails
        """
        # Return cached token if valid
        if not force_refresh:
            cached_token = self.cache.get()
            if cached_token:
                logger.debug("Using cached token")
                return cached_token

        logger.info("Requesting new access token...")

        # Apply rate limiting
        self._wait_for_rate_limit()

        # Request new token
        token_data = {'grant_type': 'client_credentials'}
        if self.scope:
            token_data['scope'] = self.scope

        try:
            response = self.session.post(
                self.token_url,
                data=token_data,
                headers={'Accept': 'application/json'},
                timeout=10
            )

            response.raise_for_status()
            tokens = response.json()

            # Cache token
            access_token = tokens['access_token']
            expires_in = tokens.get('expires_in', 3600)
            self.cache.set(access_token, expires_in)

            logger.info(f"Access token obtained (expires in {expires_in}s)")
            return access_token

        except requests.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("Client authentication failed - check credentials")
            elif e.response.status_code == 400:
                error_data = e.response.json() if e.response.headers.get('content-type') == 'application/json' else {}
                error_msg = error_data.get('error_description', error_data.get('error', 'Bad request'))
                raise Exception(f"Token request failed: {error_msg}")
            else:
                raise Exception(f"Token request failed: HTTP {e.response.status_code}")

        except requests.RequestException as e:
            raise Exception(f"Token request failed: {str(e)}")

    def call_api(self, url: str, method: str = 'GET', retry_on_401: bool = True, **kwargs) -> requests.Response:
        """
        Make API call with automatic token refresh.

        Args:
            url: API endpoint URL
            method: HTTP method
            retry_on_401: Retry once with fresh token if 401 received
            **kwargs: Additional arguments for requests

        Returns:
            Response object
        """
        # Get access token
        token = self.get_access_token()

        # Add authorization header
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {token}'
        kwargs['headers'] = headers

        # Make request
        response = self.session.request(method, url, **kwargs)

        # If 401 and retry enabled, try once with fresh token
        if response.status_code == 401 and retry_on_401:
            logger.warning("Received 401, refreshing token and retrying...")
            token = self.get_access_token(force_refresh=True)
            headers['Authorization'] = f'Bearer {token}'
            response = self.session.request(method, url, **kwargs)

        return response

    def close(self):
        """Close session and cleanup"""
        self.session.close()


def with_retry(max_retries: int = 3, backoff_factor: float = 2.0):
    """
    Decorator for retry logic with exponential backoff.

    Args:
        max_retries: Maximum number of retries
        backoff_factor: Backoff multiplier (delay = backoff_factor ^ attempt)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries - 1:
                        delay = backoff_factor ** attempt
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed")

            raise last_exception

        return wrapper
    return decorator


# Example usage
if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("OAuth 2.0 Client Credentials Flow - Demo")
    print("=" * 70)

    # Create client
    client = ClientCredentialsClient(
        token_url=TOKEN_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scope=SCOPE
    )

    print(f"\nConfiguration:")
    print(f"  Token URL:  {TOKEN_URL}")
    print(f"  Client ID:  {CLIENT_ID}")
    print(f"  Scope:      {SCOPE}")

    try:
        # Example 1: Get access token
        print("\n" + "-" * 70)
        print("Example 1: Get Access Token")
        print("-" * 70)

        token = client.get_access_token()
        print(f"Access Token: {token[:20]}...")

        # Example 2: Use cached token
        print("\n" + "-" * 70)
        print("Example 2: Use Cached Token")
        print("-" * 70)

        token2 = client.get_access_token()
        print(f"Access Token: {token2[:20]}... (from cache)")
        assert token == token2, "Tokens should match (cached)"

        # Example 3: Make API call
        print("\n" + "-" * 70)
        print("Example 3: API Call with Automatic Token Management")
        print("-" * 70)

        # Simulated API call (replace with real API)
        API_URL = 'https://api.example.com/resource'
        print(f"Calling: {API_URL}")

        # Note: This will fail if the API doesn't exist
        # In production, replace with your actual API endpoint
        try:
            response = client.call_api(API_URL)
            print(f"Response: HTTP {response.status_code}")
        except Exception as e:
            print(f"API call failed (expected if API doesn't exist): {e}")

        # Example 4: Retry decorator
        print("\n" + "-" * 70)
        print("Example 4: Retry with Exponential Backoff")
        print("-" * 70)

        @with_retry(max_retries=3, backoff_factor=2.0)
        def fetch_data():
            """Example function with retry"""
            response = client.call_api('https://api.example.com/data')
            response.raise_for_status()
            return response.json()

        try:
            data = fetch_data()
            print(f"Data: {data}")
        except Exception as e:
            print(f"Fetch failed after retries: {e}")

        print("\n" + "=" * 70)
        print("Demo complete!")
        print("=" * 70 + "\n")

    except Exception as e:
        logger.error(f"Error: {e}")

    finally:
        # Cleanup
        client.close()
