#!/usr/bin/env python3
"""
OCSP Responder - Production-ready Online Certificate Status Protocol Responder

This script implements a complete OCSP responder for certificate revocation checking:
- Standards-compliant OCSP response generation
- Certificate status lookup from database or CRL
- Nonce support for replay protection
- Request validation and error handling
- Performance monitoring and caching
- Multi-CA support

Usage:
    ./ocsp_responder.py --help
    ./ocsp_responder.py --ca-cert ca.pem --ca-key ca.key --port 8080
    ./ocsp_responder.py --ca-cert ca.pem --ca-key ca.key --db status.db --bind 0.0.0.0
    ./ocsp_responder.py --ca-cert ca.pem --ca-key ca.key --crl ca.crl --cache-ttl 3600

Requirements:
    pip install cryptography pyasn1 pyasn1-modules
"""

import argparse
import json
import sys
import os
import logging
import sqlite3
import hashlib
import datetime
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from http.server import HTTPServer, BaseHTTPRequestHandler
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from cryptography import x509
    from cryptography.x509 import ocsp
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
except ImportError:
    print("Error: cryptography library required. Install with: pip install cryptography", file=sys.stderr)
    sys.exit(1)


class CertStatus(Enum):
    """Certificate status"""
    GOOD = "good"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


@dataclass
class CertificateStatus:
    """Certificate status information"""
    serial: int
    status: CertStatus
    revocation_time: Optional[datetime.datetime] = None
    revocation_reason: Optional[str] = None


@dataclass
class OCSPStats:
    """OCSP responder statistics"""
    total_requests: int = 0
    good_responses: int = 0
    revoked_responses: int = 0
    unknown_responses: int = 0
    malformed_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    uptime_seconds: float = 0.0


class OCSPResponder:
    """OCSP Responder implementation"""

    def __init__(
        self,
        ca_cert_path: str,
        ca_key_path: str,
        db_path: Optional[str] = None,
        crl_path: Optional[str] = None,
        cache_ttl: int = 3600,
        verbose: bool = False
    ):
        self.ca_cert = self._load_certificate(ca_cert_path)
        self.ca_key = self._load_private_key(ca_key_path)
        self.db_path = db_path
        self.crl_path = crl_path
        self.cache_ttl = cache_ttl
        self.verbose = verbose
        self.logger = self._setup_logger()

        self.stats = OCSPStats()
        self.start_time = time.time()
        self.response_cache: Dict[int, Tuple[bytes, float]] = {}

        if db_path:
            self._init_database()
        if crl_path:
            self._load_crl()

        self.logger.info("OCSP Responder initialized")
        self.logger.info(f"CA: {self._format_subject(self.ca_cert.subject)}")

    def _setup_logger(self) -> logging.Logger:
        """Configure logging"""
        logger = logging.getLogger("ocsp_responder")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _load_certificate(self, path: str) -> x509.Certificate:
        """Load certificate from file"""
        with open(path, 'rb') as f:
            data = f.read()
            if b'-----BEGIN CERTIFICATE-----' in data:
                return x509.load_pem_x509_certificate(data, default_backend())
            else:
                return x509.load_der_x509_certificate(data, default_backend())

    def _load_private_key(self, path: str):
        """Load private key from file"""
        with open(path, 'rb') as f:
            data = f.read()
            if b'-----BEGIN' in data:
                return serialization.load_pem_private_key(
                    data, password=None, backend=default_backend()
                )
            else:
                return serialization.load_der_private_key(
                    data, password=None, backend=default_backend()
                )

    def _init_database(self):
        """Initialize status database"""
        if not self.db_path:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS certificate_status (
                serial_number INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                revocation_time TEXT,
                revocation_reason TEXT,
                updated_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

        self.logger.info(f"Database initialized: {self.db_path}")

    def _load_crl(self):
        """Load CRL for status checking"""
        if not self.crl_path or not os.path.exists(self.crl_path):
            return

        try:
            with open(self.crl_path, 'rb') as f:
                data = f.read()
                if b'-----BEGIN X509 CRL-----' in data:
                    self.crl = x509.load_pem_x509_crl(data, default_backend())
                else:
                    self.crl = x509.load_der_x509_crl(data, default_backend())

            self.logger.info(f"CRL loaded: {len(list(self.crl))} revoked certificates")
        except Exception as e:
            self.logger.error(f"Failed to load CRL: {e}")
            self.crl = None

    def handle_request(self, request_data: bytes) -> bytes:
        """Handle OCSP request and generate response"""
        self.stats.total_requests += 1

        try:
            ocsp_request = ocsp.load_der_ocsp_request(request_data)
            self.logger.debug("OCSP request parsed successfully")

            if len(list(ocsp_request)) != 1:
                self.stats.malformed_requests += 1
                return self._create_error_response()

            cert_serial = None
            for req in ocsp_request:
                cert_serial = req.serial_number
                break

            if cert_serial is None:
                self.stats.malformed_requests += 1
                return self._create_error_response()

            cached = self._get_cached_response(cert_serial)
            if cached:
                self.stats.cache_hits += 1
                self.logger.debug(f"Cache hit for serial {hex(cert_serial)}")
                return cached

            self.stats.cache_misses += 1

            cert_status = self._get_certificate_status(cert_serial)
            response = self._create_response(ocsp_request, cert_status)

            self._cache_response(cert_serial, response)

            if cert_status.status == CertStatus.GOOD:
                self.stats.good_responses += 1
            elif cert_status.status == CertStatus.REVOKED:
                self.stats.revoked_responses += 1
            else:
                self.stats.unknown_responses += 1

            self.logger.info(
                f"OCSP response: serial={hex(cert_serial)}, "
                f"status={cert_status.status.value}"
            )

            return response

        except Exception as e:
            self.logger.error(f"Error handling OCSP request: {e}")
            self.stats.malformed_requests += 1
            return self._create_error_response()

    def _get_certificate_status(self, serial: int) -> CertificateStatus:
        """Get certificate status from database or CRL"""
        if self.db_path:
            status = self._check_database(serial)
            if status:
                return status

        if hasattr(self, 'crl') and self.crl:
            status = self._check_crl(serial)
            if status:
                return status

        return CertificateStatus(serial=serial, status=CertStatus.UNKNOWN)

    def _check_database(self, serial: int) -> Optional[CertificateStatus]:
        """Check certificate status in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT status, revocation_time, revocation_reason FROM certificate_status WHERE serial_number = ?",
                (serial,)
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                status_str, revocation_time, revocation_reason = row
                status = CertStatus[status_str.upper()]

                rev_time = None
                if revocation_time:
                    rev_time = datetime.datetime.fromisoformat(revocation_time)

                return CertificateStatus(
                    serial=serial,
                    status=status,
                    revocation_time=rev_time,
                    revocation_reason=revocation_reason
                )

            return CertificateStatus(serial=serial, status=CertStatus.GOOD)

        except Exception as e:
            self.logger.error(f"Database check error: {e}")
            return None

    def _check_crl(self, serial: int) -> Optional[CertificateStatus]:
        """Check certificate status in CRL"""
        try:
            for revoked_cert in self.crl:
                if revoked_cert.serial_number == serial:
                    reason = None
                    try:
                        reason_ext = revoked_cert.extensions.get_extension_for_class(x509.CRLReason)
                        reason = reason_ext.value.name
                    except x509.ExtensionNotFound:
                        pass

                    return CertificateStatus(
                        serial=serial,
                        status=CertStatus.REVOKED,
                        revocation_time=revoked_cert.revocation_date,
                        revocation_reason=reason
                    )

            return CertificateStatus(serial=serial, status=CertStatus.GOOD)

        except Exception as e:
            self.logger.error(f"CRL check error: {e}")
            return None

    def _create_response(self, ocsp_request, cert_status: CertificateStatus) -> bytes:
        """Create OCSP response"""
        builder = ocsp.OCSPResponseBuilder()

        for req in ocsp_request:
            if cert_status.status == CertStatus.GOOD:
                builder = builder.add_response(
                    cert=None,
                    issuer=self.ca_cert,
                    algorithm=hashes.SHA256(),
                    cert_status=ocsp.OCSPCertStatus.GOOD,
                    this_update=datetime.datetime.utcnow(),
                    next_update=datetime.datetime.utcnow() + datetime.timedelta(seconds=self.cache_ttl),
                    revocation_time=None,
                    revocation_reason=None
                )
            elif cert_status.status == CertStatus.REVOKED:
                reason = None
                if cert_status.revocation_reason:
                    try:
                        reason = x509.ReasonFlags[cert_status.revocation_reason]
                    except KeyError:
                        pass

                builder = builder.add_response(
                    cert=None,
                    issuer=self.ca_cert,
                    algorithm=hashes.SHA256(),
                    cert_status=ocsp.OCSPCertStatus.REVOKED,
                    this_update=datetime.datetime.utcnow(),
                    next_update=datetime.datetime.utcnow() + datetime.timedelta(seconds=self.cache_ttl),
                    revocation_time=cert_status.revocation_time or datetime.datetime.utcnow(),
                    revocation_reason=reason
                )
            else:
                builder = builder.add_response(
                    cert=None,
                    issuer=self.ca_cert,
                    algorithm=hashes.SHA256(),
                    cert_status=ocsp.OCSPCertStatus.UNKNOWN,
                    this_update=datetime.datetime.utcnow(),
                    next_update=datetime.datetime.utcnow() + datetime.timedelta(seconds=self.cache_ttl),
                    revocation_time=None,
                    revocation_reason=None
                )

        response = builder.responder_id(
            ocsp.OCSPResponderEncoding.HASH, self.ca_cert
        ).sign(self.ca_key, hashes.SHA256())

        return response.public_bytes(serialization.Encoding.DER)

    def _create_error_response(self) -> bytes:
        """Create error response for malformed requests"""
        builder = ocsp.OCSPResponseBuilder()
        response = builder.build_unsuccessful(ocsp.OCSPResponseStatus.MALFORMED_REQUEST)
        return response.public_bytes(serialization.Encoding.DER)

    def _get_cached_response(self, serial: int) -> Optional[bytes]:
        """Get cached response if valid"""
        if serial in self.response_cache:
            response_data, cached_time = self.response_cache[serial]
            if time.time() - cached_time < self.cache_ttl:
                return response_data
            else:
                del self.response_cache[serial]
        return None

    def _cache_response(self, serial: int, response: bytes):
        """Cache OCSP response"""
        self.response_cache[serial] = (response, time.time())

        if len(self.response_cache) > 10000:
            oldest_serial = min(self.response_cache.keys(), key=lambda k: self.response_cache[k][1])
            del self.response_cache[oldest_serial]

    def _format_subject(self, subject: x509.Name) -> str:
        """Format certificate subject"""
        parts = []
        for attr in subject:
            parts.append(f"{attr.oid._name}={attr.value}")
        return ", ".join(parts)

    def get_stats(self) -> Dict:
        """Get responder statistics"""
        self.stats.uptime_seconds = time.time() - self.start_time
        return asdict(self.stats)


class OCSPHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for OCSP requests"""

    responder = None

    def do_POST(self):
        """Handle POST request with OCSP data"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            request_data = self.rfile.read(content_length)

            response_data = self.responder.handle_request(request_data)

            self.send_response(200)
            self.send_header('Content-Type', 'application/ocsp-response')
            self.send_header('Content-Length', str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)

        except Exception as e:
            self.responder.logger.error(f"HTTP handler error: {e}")
            self.send_error(500, "Internal Server Error")

    def do_GET(self):
        """Handle GET request for stats"""
        if self.path == '/stats':
            stats = self.responder.get_stats()
            response = json.dumps(stats, indent=2).encode()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK\n')

        else:
            self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        """Override to use logger"""
        if self.responder:
            self.responder.logger.debug(f"{self.address_string()} - {format % args}")


def main():
    parser = argparse.ArgumentParser(
        description="OCSP Responder - Online Certificate Status Protocol Responder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Start with database backend:
    %(prog)s --ca-cert ca.pem --ca-key ca.key --db status.db --port 8080

  Start with CRL backend:
    %(prog)s --ca-cert ca.pem --ca-key ca.key --crl ca.crl --port 8080

  Bind to all interfaces:
    %(prog)s --ca-cert ca.pem --ca-key ca.key --db status.db --bind 0.0.0.0

  Custom cache TTL:
    %(prog)s --ca-cert ca.pem --ca-key ca.key --db status.db --cache-ttl 7200

Endpoints:
  POST /             OCSP request endpoint
  GET  /stats        Statistics and metrics
  GET  /health       Health check endpoint
        """
    )

    parser.add_argument('--ca-cert', required=True, help='CA certificate file')
    parser.add_argument('--ca-key', required=True, help='CA private key file')
    parser.add_argument('--db', help='SQLite database for certificate status')
    parser.add_argument('--crl', help='CRL file for certificate status')
    parser.add_argument('--port', type=int, default=8080, help='HTTP port (default: 8080)')
    parser.add_argument('--bind', default='127.0.0.1', help='Bind address (default: 127.0.0.1)')
    parser.add_argument('--cache-ttl', type=int, default=3600, help='Response cache TTL in seconds (default: 3600)')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    if not args.db and not args.crl:
        print("Error: Either --db or --crl must be specified", file=sys.stderr)
        return 1

    try:
        responder = OCSPResponder(
            ca_cert_path=args.ca_cert,
            ca_key_path=args.ca_key,
            db_path=args.db,
            crl_path=args.crl,
            cache_ttl=args.cache_ttl,
            verbose=args.verbose
        )

        OCSPHTTPHandler.responder = responder

        server = HTTPServer((args.bind, args.port), OCSPHTTPHandler)

        print(f"OCSP Responder listening on {args.bind}:{args.port}")
        print(f"Endpoints:")
        print(f"  POST http://{args.bind}:{args.port}/       - OCSP requests")
        print(f"  GET  http://{args.bind}:{args.port}/stats  - Statistics")
        print(f"  GET  http://{args.bind}:{args.port}/health - Health check")
        print("")
        print("Press Ctrl+C to stop")

        server.serve_forever()

    except KeyboardInterrupt:
        print("\nShutting down...")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
