#!/usr/bin/env python3
"""
Secure HTTPS server with modern TLS configuration
"""

import ssl
import http.server
import socketserver
from pathlib import Path


def create_secure_context(
    certfile: str,
    keyfile: str,
    min_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_2,
    max_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_3,
) -> ssl.SSLContext:
    """
    Create a secure SSL context with modern TLS configuration

    Args:
        certfile: Path to certificate file (PEM format)
        keyfile: Path to private key file (PEM format)
        min_version: Minimum TLS version (default: TLS 1.2)
        max_version: Maximum TLS version (default: TLS 1.3)

    Returns:
        Configured SSL context
    """
    # Create context for server
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Load certificate and key
    context.load_cert_chain(certfile, keyfile)

    # TLS versions
    context.minimum_version = min_version
    context.maximum_version = max_version

    # Cipher suites - only forward secrecy with AEAD
    # This covers both TLS 1.2 and TLS 1.3
    context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20')

    # Security options
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1
    context.options |= ssl.OP_NO_COMPRESSION  # Prevent CRIME attack
    context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE  # Prefer server cipher order

    # Disable session tickets for privacy (optional)
    context.options |= ssl.OP_NO_TICKET

    return context


class SecureHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with security headers"""

    def end_headers(self):
        """Add security headers to all responses"""
        # HSTS
        self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')

        # Content security
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('X-XSS-Protection', '1; mode=block')

        # CSP
        self.send_header('Content-Security-Policy', "default-src 'self'")

        super().end_headers()


def run_https_server(
    port: int = 8443,
    certfile: str = '/etc/ssl/certs/server.crt',
    keyfile: str = '/etc/ssl/private/server.key',
    bind: str = '0.0.0.0'
):
    """
    Run HTTPS server with secure TLS configuration

    Args:
        port: Port to listen on (default: 8443)
        certfile: Path to certificate file
        keyfile: Path to private key file
        bind: Interface to bind to (default: 0.0.0.0)
    """
    # Create SSL context
    context = create_secure_context(certfile, keyfile)

    # Create server
    with socketserver.TCPServer((bind, port), SecureHTTPRequestHandler) as httpd:
        # Wrap socket with TLS
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

        print(f"HTTPS server running on https://{bind}:{port}")
        print(f"TLS version range: {context.minimum_version.name} - {context.maximum_version.name}")

        # Serve forever
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")


# Example: Mutual TLS (mTLS) configuration
def create_mtls_context(
    certfile: str,
    keyfile: str,
    ca_certs: str,
) -> ssl.SSLContext:
    """
    Create SSL context with mutual TLS (client certificate verification)

    Args:
        certfile: Server certificate file
        keyfile: Server private key file
        ca_certs: CA certificates for verifying client certificates

    Returns:
        Configured SSL context with mTLS
    """
    # Start with secure context
    context = create_secure_context(certfile, keyfile)

    # Require client certificates
    context.verify_mode = ssl.CERT_REQUIRED

    # Load CA certificates for client verification
    context.load_verify_locations(ca_certs)

    # Set verification depth
    context.verify_depth = 2

    return context


# Example: TLS client configuration
def create_secure_client_context(
    ca_certs: str = None,
    certfile: str = None,
    keyfile: str = None,
) -> ssl.SSLContext:
    """
    Create SSL context for secure TLS client

    Args:
        ca_certs: CA certificates to trust (default: system trust store)
        certfile: Client certificate for mTLS (optional)
        keyfile: Client private key for mTLS (optional)

    Returns:
        Configured SSL context for client
    """
    # Create context for client
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    # TLS versions
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3

    # Cipher suites
    context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20')

    # Load CA certificates
    if ca_certs:
        context.load_verify_locations(ca_certs)
    else:
        context.load_default_certs()

    # Verify server certificates
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    # Load client certificate for mTLS (optional)
    if certfile and keyfile:
        context.load_cert_chain(certfile, keyfile)

    return context


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Secure HTTPS server')
    parser.add_argument('--port', type=int, default=8443, help='Port to listen on')
    parser.add_argument('--cert', required=True, help='Certificate file')
    parser.add_argument('--key', required=True, help='Private key file')
    parser.add_argument('--bind', default='0.0.0.0', help='Interface to bind to')

    args = parser.parse_args()

    run_https_server(
        port=args.port,
        certfile=args.cert,
        keyfile=args.key,
        bind=args.bind
    )
