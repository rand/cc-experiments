#!/usr/bin/env python3
"""
Secure HTTPS client with modern TLS configuration
"""

import ssl
import socket
import urllib.request
import urllib.error
from typing import Optional, Dict, Any


def create_secure_client_context(
    min_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_2,
    max_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_3,
    verify_cert: bool = True,
    ca_certs: Optional[str] = None,
    client_cert: Optional[str] = None,
    client_key: Optional[str] = None,
) -> ssl.SSLContext:
    """
    Create a secure SSL context for TLS client

    Args:
        min_version: Minimum TLS version
        max_version: Maximum TLS version
        verify_cert: Whether to verify server certificates
        ca_certs: Path to CA certificates (default: system trust store)
        client_cert: Path to client certificate for mTLS
        client_key: Path to client key for mTLS

    Returns:
        Configured SSL context
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    # TLS versions
    context.minimum_version = min_version
    context.maximum_version = max_version

    # Cipher suites - only forward secrecy with AEAD
    context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20')

    # Certificate verification
    if verify_cert:
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        # Load CA certificates
        if ca_certs:
            context.load_verify_locations(ca_certs)
        else:
            context.load_default_certs()
    else:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    # Client certificate for mTLS (optional)
    if client_cert and client_key:
        context.load_cert_chain(client_cert, client_key)

    return context


def test_tls_connection(
    host: str,
    port: int = 443,
    timeout: int = 10,
    verify_cert: bool = True,
) -> Dict[str, Any]:
    """
    Test TLS connection and return connection details

    Args:
        host: Target hostname
        port: Target port
        timeout: Connection timeout in seconds
        verify_cert: Whether to verify server certificate

    Returns:
        Dictionary with connection details
    """
    context = create_secure_client_context(verify_cert=verify_cert)

    try:
        # Create connection
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                # Get connection info
                cipher = ssock.cipher()
                version = ssock.version()
                cert = ssock.getpeercert()

                return {
                    'success': True,
                    'host': host,
                    'port': port,
                    'tls_version': version,
                    'cipher_suite': cipher[0] if cipher else None,
                    'cipher_protocol': cipher[1] if cipher and len(cipher) > 1 else None,
                    'cipher_bits': cipher[2] if cipher and len(cipher) > 2 else None,
                    'certificate': {
                        'subject': dict(x[0] for x in cert['subject']) if cert else None,
                        'issuer': dict(x[0] for x in cert['issuer']) if cert else None,
                        'version': cert.get('version') if cert else None,
                        'serialNumber': cert.get('serialNumber') if cert else None,
                        'notBefore': cert.get('notBefore') if cert else None,
                        'notAfter': cert.get('notAfter') if cert else None,
                    }
                }
    except Exception as e:
        return {
            'success': False,
            'host': host,
            'port': port,
            'error': str(e)
        }


def https_request(
    url: str,
    method: str = 'GET',
    headers: Optional[Dict[str, str]] = None,
    data: Optional[bytes] = None,
    verify_cert: bool = True,
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    Make HTTPS request with secure TLS configuration

    Args:
        url: Target URL
        method: HTTP method (GET, POST, etc.)
        headers: HTTP headers
        data: Request body data
        verify_cert: Whether to verify server certificate
        timeout: Request timeout in seconds

    Returns:
        Dictionary with response details
    """
    context = create_secure_client_context(verify_cert=verify_cert)

    try:
        # Create request
        req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)

        # Make request
        with urllib.request.urlopen(req, context=context, timeout=timeout) as response:
            return {
                'success': True,
                'status_code': response.status,
                'headers': dict(response.headers),
                'body': response.read().decode('utf-8'),
                'url': response.url,
            }
    except urllib.error.HTTPError as e:
        return {
            'success': False,
            'status_code': e.code,
            'error': str(e),
            'body': e.read().decode('utf-8') if hasattr(e, 'read') else None,
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


# Example: Using with requests library (if available)
def create_requests_session(verify_cert: bool = True):
    """
    Create requests.Session with secure TLS configuration

    Requires: pip install requests

    Args:
        verify_cert: Whether to verify server certificates

    Returns:
        Configured requests.Session
    """
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.ssl_ import create_urllib3_context

        class TLSAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = create_urllib3_context()
                ctx.minimum_version = ssl.TLSVersion.TLSv1_2
                ctx.maximum_version = ssl.TLSVersion.TLSv1_3
                ctx.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20')
                kwargs['ssl_context'] = ctx
                return super().init_poolmanager(*args, **kwargs)

        session = requests.Session()
        session.mount('https://', TLSAdapter())
        session.verify = verify_cert

        return session
    except ImportError:
        raise ImportError("requests library not installed. Install with: pip install requests")


if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Secure HTTPS client')
    parser.add_argument('url', help='Target URL')
    parser.add_argument('--method', default='GET', help='HTTP method')
    parser.add_argument('--no-verify', action='store_true', help='Disable certificate verification')
    parser.add_argument('--test-connection', action='store_true', help='Test connection details only')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds')

    args = parser.parse_args()

    if args.test_connection:
        # Extract host and port from URL
        from urllib.parse import urlparse
        parsed = urlparse(args.url)
        host = parsed.hostname
        port = parsed.port or 443

        result = test_tls_connection(
            host=host,
            port=port,
            timeout=args.timeout,
            verify_cert=not args.no_verify
        )
        print(json.dumps(result, indent=2))
    else:
        # Make HTTP request
        result = https_request(
            url=args.url,
            method=args.method,
            verify_cert=not args.no_verify,
            timeout=args.timeout
        )
        print(json.dumps(result, indent=2))
