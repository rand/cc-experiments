#!/usr/bin/env python3
"""
Prometheus Certificate Exporter

Exports certificate expiration metrics for Prometheus monitoring.

Metrics:
- ssl_certificate_expiry_seconds: Seconds until certificate expires
- ssl_certificate_info: Certificate metadata (issuer, subject, SANs)
- ssl_certificate_valid: Certificate validity (1=valid, 0=invalid)

Usage:
    # Start exporter
    python prometheus_cert_exporter.py --port 9117

    # Prometheus scrape config:
    scrape_configs:
      - job_name: 'ssl-certs'
        static_configs:
          - targets: ['localhost:9117']

Dependencies:
    pip install prometheus_client cryptography
"""

import argparse
import time
import socket
import ssl
from datetime import datetime
from typing import Dict, List
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from prometheus_client import Counter, Gauge, Info, generate_latest, REGISTRY
from cryptography import x509
from cryptography.hazmat.backends import default_backend


# Prometheus metrics
CERT_EXPIRY = Gauge(
    'ssl_certificate_expiry_seconds',
    'Seconds until SSL certificate expires',
    ['hostname', 'port', 'issuer', 'subject_cn']
)

CERT_VALID = Gauge(
    'ssl_certificate_valid',
    'SSL certificate validity (1=valid, 0=invalid/expired)',
    ['hostname', 'port', 'reason']
)

CERT_INFO = Info(
    'ssl_certificate',
    'SSL certificate information',
    ['hostname', 'port']
)

SCRAPE_DURATION = Gauge(
    'ssl_certificate_scrape_duration_seconds',
    'Duration of certificate check',
    ['hostname', 'port']
)

SCRAPE_ERRORS = Counter(
    'ssl_certificate_scrape_errors_total',
    'Total certificate check errors',
    ['hostname', 'port', 'error_type']
)


class CertificateCollector:
    """Collects certificate metrics"""

    def __init__(self, hosts: List[tuple], timeout: int = 10):
        """
        Args:
            hosts: List of (hostname, port) tuples to monitor
            timeout: Connection timeout in seconds
        """
        self.hosts = hosts
        self.timeout = timeout

    def collect_certificate_metrics(self, hostname: str, port: int) -> Dict:
        """Collect metrics for a single certificate"""

        start_time = time.time()
        metrics = {
            'hostname': hostname,
            'port': port,
            'valid': False,
            'error': None,
        }

        try:
            # Connect and get certificate
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert_bin()
                    cert = x509.load_der_x509_certificate(cert_der, default_backend())

                    # Extract certificate info
                    subject_cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
                    subject_cn = subject_cn[0].value if subject_cn else 'unknown'

                    issuer_cn = cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
                    issuer_cn = issuer_cn[0].value if issuer_cn else 'unknown'

                    # Calculate expiry
                    now = datetime.utcnow()
                    expiry_seconds = (cert.not_valid_after - now).total_seconds()

                    # Get SANs
                    try:
                        san_ext = cert.extensions.get_extension_for_oid(
                            x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                        )
                        sans = ','.join([name.value for name in san_ext.value])
                    except x509.ExtensionNotFound:
                        sans = ''

                    # Determine validity
                    valid = True
                    reason = 'valid'

                    if now < cert.not_valid_before:
                        valid = False
                        reason = 'not_yet_valid'
                    elif now > cert.not_valid_after:
                        valid = False
                        reason = 'expired'

                    # Update metrics
                    metrics.update({
                        'valid': valid,
                        'reason': reason,
                        'subject_cn': subject_cn,
                        'issuer_cn': issuer_cn,
                        'not_before': cert.not_valid_before.isoformat(),
                        'not_after': cert.not_valid_after.isoformat(),
                        'expiry_seconds': expiry_seconds,
                        'sans': sans,
                        'serial': hex(cert.serial_number),
                    })

                    # Export to Prometheus
                    CERT_EXPIRY.labels(
                        hostname=hostname,
                        port=port,
                        issuer=issuer_cn,
                        subject_cn=subject_cn,
                    ).set(expiry_seconds)

                    CERT_VALID.labels(
                        hostname=hostname,
                        port=port,
                        reason=reason,
                    ).set(1 if valid else 0)

                    CERT_INFO.labels(
                        hostname=hostname,
                        port=port,
                    ).info({
                        'subject_cn': subject_cn,
                        'issuer': issuer_cn,
                        'not_before': cert.not_valid_before.isoformat(),
                        'not_after': cert.not_valid_after.isoformat(),
                        'serial': hex(cert.serial_number),
                        'sans': sans,
                    })

        except socket.timeout:
            metrics['error'] = 'timeout'
            SCRAPE_ERRORS.labels(hostname=hostname, port=port, error_type='timeout').inc()
        except socket.gaierror:
            metrics['error'] = 'dns_error'
            SCRAPE_ERRORS.labels(hostname=hostname, port=port, error_type='dns_error').inc()
        except ssl.SSLError as e:
            metrics['error'] = f'ssl_error: {e}'
            SCRAPE_ERRORS.labels(hostname=hostname, port=port, error_type='ssl_error').inc()
        except Exception as e:
            metrics['error'] = f'error: {e}'
            SCRAPE_ERRORS.labels(hostname=hostname, port=port, error_type='unknown').inc()
        finally:
            duration = time.time() - start_time
            SCRAPE_DURATION.labels(hostname=hostname, port=port).set(duration)

        return metrics

    def collect_all(self) -> List[Dict]:
        """Collect metrics for all configured hosts"""

        results = []
        for hostname, port in self.hosts:
            metrics = self.collect_certificate_metrics(hostname, port)
            results.append(metrics)

        return results


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics"""

    collector: CertificateCollector = None

    def do_GET(self):
        """Handle HTTP GET request"""

        if self.path == '/metrics':
            # Collect fresh metrics
            if self.collector:
                self.collector.collect_all()

            # Generate Prometheus metrics
            metrics = generate_latest(REGISTRY)

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()
            self.wfile.write(metrics)

        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK\n')

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default logging
        pass


def parse_hosts_file(file_path: str) -> List[tuple]:
    """Parse hosts file (one host per line, format: hostname:port)"""

    hosts = []
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if ':' in line:
                hostname, port = line.split(':', 1)
                port = int(port)
            else:
                hostname = line
                port = 443

            hosts.append((hostname, port))

    return hosts


def main():
    parser = argparse.ArgumentParser(
        description='Prometheus SSL Certificate Exporter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor specific hosts
  %(prog)s --hosts example.com:443 api.example.com:8443

  # Monitor hosts from file
  %(prog)s --hosts-file hosts.txt

  # Custom port
  %(prog)s --port 9117 --hosts example.com

  # With custom timeout
  %(prog)s --hosts example.com --timeout 5

Hosts file format (hosts.txt):
  example.com
  api.example.com:8443
  internal.example.com:443

Prometheus scrape config:
  scrape_configs:
    - job_name: 'ssl-certs'
      scrape_interval: 60s
      static_configs:
        - targets: ['localhost:9117']

Prometheus alerts:
  - alert: CertificateExpiringSoon
    expr: ssl_certificate_expiry_seconds < 86400 * 30
    labels:
      severity: warning
    annotations:
      summary: "Certificate expiring in < 30 days"
        """
    )

    parser.add_argument('--port', type=int, default=9117,
                        help='Exporter port (default: 9117)')
    parser.add_argument('--hosts', nargs='+',
                        help='Hosts to monitor (format: hostname:port)')
    parser.add_argument('--hosts-file',
                        help='File with hosts to monitor (one per line)')
    parser.add_argument('--timeout', type=int, default=10,
                        help='Connection timeout (default: 10s)')

    args = parser.parse_args()

    # Parse hosts
    hosts = []

    if args.hosts_file:
        hosts.extend(parse_hosts_file(args.hosts_file))

    if args.hosts:
        for host in args.hosts:
            if ':' in host:
                hostname, port = host.split(':', 1)
                port = int(port)
            else:
                hostname = host
                port = 443
            hosts.append((hostname, port))

    if not hosts:
        parser.error('Must specify --hosts or --hosts-file')

    print(f"Certificate Exporter starting on port {args.port}")
    print(f"Monitoring {len(hosts)} host(s):")
    for hostname, port in hosts:
        print(f"  - {hostname}:{port}")

    # Create collector
    collector = CertificateCollector(hosts=hosts, timeout=args.timeout)

    # Collect initial metrics
    print("\nCollecting initial metrics...")
    results = collector.collect_all()
    for result in results:
        if result.get('error'):
            print(f"  ✗ {result['hostname']}:{result['port']} - {result['error']}")
        else:
            days = int(result['expiry_seconds'] / 86400)
            print(f"  ✓ {result['hostname']}:{result['port']} - {days} days remaining")

    # Setup HTTP server
    MetricsHandler.collector = collector
    server = HTTPServer(('', args.port), MetricsHandler)

    print(f"\nExporter ready!")
    print(f"Metrics endpoint: http://localhost:{args.port}/metrics")
    print(f"Health endpoint: http://localhost:{args.port}/health")
    print("Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()
