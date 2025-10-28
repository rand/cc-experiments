#!/usr/bin/env python3
"""
Mutual TLS (mTLS) Server and Client Example

Demonstrates mutual TLS authentication where both server and client verify
each other's certificates.

Use cases:
- Microservice authentication
- API authentication without API keys
- Zero-trust networks

Run:
    # Start server
    python mtls_server_client.py server

    # In another terminal, run client
    python mtls_server_client.py client
"""

import ssl
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys


class SecureHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler that shows client certificate info"""

    def do_GET(self):
        # Get client certificate
        client_cert = self.connection.getpeercert()

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        response = "=== mTLS Connection Successful ===\n\n"

        if client_cert:
            response += "Client Certificate:\n"
            for field, value in client_cert.items():
                response += f"  {field}: {value}\n"
        else:
            response += "No client certificate provided\n"

        self.wfile.write(response.encode())

    def log_message(self, format, *args):
        # Custom logging
        client_cert = self.connection.getpeercert()
        subject = dict(x[0] for x in client_cert['subject']) if client_cert else {}
        cn = subject.get('commonName', 'unknown')
        print(f"Request from {self.client_address[0]} (CN: {cn}): {format % args}")


def run_mtls_server(host='localhost', port=8443):
    """Run mTLS server"""

    print(f"Starting mTLS server on {host}:{port}...")

    # Create HTTP server
    server = HTTPServer((host, port), SecureHTTPRequestHandler)

    # Wrap with SSL/TLS
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

    # Server certificate and key
    context.load_cert_chain(
        certfile='server.crt',
        keyfile='server.key',
    )

    # Require client certificate
    context.verify_mode = ssl.CERT_REQUIRED

    # CA certificate to verify client certs
    context.load_verify_locations(cafile='ca.crt')

    # Optional: Set allowed TLS versions
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3

    # Wrap server socket
    server.socket = context.wrap_socket(server.socket, server_side=True)

    print("Server ready. Waiting for mTLS connections...")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


def run_mtls_client(host='localhost', port=8443):
    """Run mTLS client"""

    print(f"Connecting to mTLS server at {host}:{port}...")

    # Create SSL context
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

    # Load CA certificate (to verify server)
    context.load_verify_locations(cafile='ca.crt')

    # Load client certificate and key (for client authentication)
    context.load_cert_chain(
        certfile='client.crt',
        keyfile='client.key',
    )

    # Optional: Set allowed TLS versions
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3

    # Connect to server
    with socket.create_connection((host, port)) as sock:
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            print("mTLS handshake successful!")
            print(f"TLS version: {ssock.version()}")
            print(f"Cipher: {ssock.cipher()}")

            # Get server certificate
            server_cert = ssock.getpeercert()
            subject = dict(x[0] for x in server_cert['subject'])
            print(f"Connected to server: {subject.get('commonName', 'unknown')}")

            # Send HTTP request
            ssock.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")

            # Receive response
            response = b""
            while True:
                chunk = ssock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b"\r\n\r\n" in response and len(chunk) < 4096:
                    break

            print("\n=== Server Response ===")
            print(response.decode())


def generate_test_certificates():
    """Generate self-signed certificates for testing"""

    print("Generating test certificates...")

    import subprocess

    commands = [
        # Generate CA
        "openssl genrsa -out ca.key 2048",
        "openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 -out ca.crt -subj '/CN=Test CA'",

        # Generate server certificate
        "openssl genrsa -out server.key 2048",
        "openssl req -new -key server.key -out server.csr -subj '/CN=localhost'",
        "openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365 -sha256",

        # Generate client certificate
        "openssl genrsa -out client.key 2048",
        "openssl req -new -key client.key -out client.csr -subj '/CN=Test Client'",
        "openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 365 -sha256",

        # Cleanup CSRs
        "rm -f server.csr client.csr ca.srl",
    ]

    # SECURITY: Commands are hardcoded strings (no user input) - safe to use shell=True
    for cmd in commands:
        subprocess.run(cmd, shell=True, check=True)

    print("Test certificates generated:")
    print("  - ca.crt, ca.key (Certificate Authority)")
    print("  - server.crt, server.key (Server)")
    print("  - client.crt, client.key (Client)")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Mutual TLS Example")
        print("\nUsage:")
        print(f"  {sys.argv[0]} setup   # Generate test certificates")
        print(f"  {sys.argv[0]} server  # Run mTLS server")
        print(f"  {sys.argv[0]} client  # Run mTLS client")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == 'setup':
        generate_test_certificates()
    elif mode == 'server':
        run_mtls_server()
    elif mode == 'client':
        run_mtls_client()
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
