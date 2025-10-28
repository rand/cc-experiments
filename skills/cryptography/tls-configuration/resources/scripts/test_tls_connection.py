#!/usr/bin/env python3
"""
test_tls_connection.py
Test TLS connections with detailed handshake analysis and timing
"""

import argparse
import json
import socket
import ssl
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from datetime import datetime


VERSION = "1.0.0"


@dataclass
class TimingInfo:
    """Connection timing information"""
    dns_lookup_ms: float
    tcp_connect_ms: float
    tls_handshake_ms: float
    total_ms: float


@dataclass
class CertificateDetails:
    """Detailed certificate information"""
    subject: Dict[str, str]
    issuer: Dict[str, str]
    version: int
    serial_number: str
    not_before: str
    not_after: str
    subject_alt_names: List[str]
    signature_algorithm: Optional[str]


@dataclass
class ConnectionResult:
    """TLS connection test result"""
    success: bool
    host: str
    port: int
    ip_address: str
    tls_version: str
    cipher_suite: str
    cipher_bits: int
    certificate: Optional[CertificateDetails]
    timing: Optional[TimingInfo]
    error: Optional[str]
    warnings: List[str]


def format_cert_subject(subject_tuple) -> Dict[str, str]:
    """Format certificate subject/issuer tuple to dict"""
    return {k: v for components in subject_tuple for k, v in components}


def get_certificate_details(cert: Dict) -> CertificateDetails:
    """Extract detailed certificate information"""
    subject = format_cert_subject(cert.get('subject', []))
    issuer = format_cert_subject(cert.get('issuer', []))

    # Extract Subject Alternative Names
    san_list = []
    for key, value in cert.get('subjectAltName', []):
        if key == 'DNS':
            san_list.append(value)

    return CertificateDetails(
        subject=subject,
        issuer=issuer,
        version=cert.get('version', 0),
        serial_number=cert.get('serialNumber', 'Unknown'),
        not_before=cert.get('notBefore', 'Unknown'),
        not_after=cert.get('notAfter', 'Unknown'),
        subject_alt_names=san_list,
        signature_algorithm=None  # Not available in basic cert info
    )


def test_tls_connection(
    host: str,
    port: int = 443,
    min_tls_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_2,
    max_tls_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_3,
    verify_cert: bool = True,
    cipher_suite: Optional[str] = None,
    timeout: int = 10,
    verbose: bool = False
) -> ConnectionResult:
    """Test TLS connection and gather detailed information"""

    warnings = []
    cert_details = None
    timing = None

    try:
        # DNS lookup timing
        dns_start = time.time()
        ip_address = socket.gethostbyname(host)
        dns_time = (time.time() - dns_start) * 1000

        if verbose:
            print(f"[INFO] Resolved {host} to {ip_address} in {dns_time:.2f}ms")

        # TCP connection timing
        tcp_start = time.time()
        sock = socket.create_connection((host, port), timeout=timeout)
        tcp_time = (time.time() - tcp_start) * 1000

        if verbose:
            print(f"[INFO] TCP connection established in {tcp_time:.2f}ms")

        try:
            # Create SSL context
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version = min_tls_version
            context.maximum_version = max_tls_version

            if not verify_cert:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                warnings.append("Certificate verification disabled")
            else:
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED
                context.load_default_certs()

            if cipher_suite:
                try:
                    context.set_ciphers(cipher_suite)
                    if verbose:
                        print(f"[INFO] Testing cipher suite: {cipher_suite}")
                except ssl.SSLError as e:
                    return ConnectionResult(
                        success=False,
                        host=host,
                        port=port,
                        ip_address=ip_address,
                        tls_version="",
                        cipher_suite="",
                        cipher_bits=0,
                        certificate=None,
                        timing=None,
                        error=f"Invalid cipher suite: {e}",
                        warnings=warnings
                    )

            # TLS handshake timing
            tls_start = time.time()
            ssock = context.wrap_socket(sock, server_hostname=host)
            tls_time = (time.time() - tls_start) * 1000
            total_time = dns_time + tcp_time + tls_time

            if verbose:
                print(f"[INFO] TLS handshake completed in {tls_time:.2f}ms")

            # Get connection info
            tls_version = ssock.version()
            cipher_info = ssock.cipher()
            cipher_name = cipher_info[0]
            cipher_protocol = cipher_info[1]
            cipher_bits = cipher_info[2]

            # Version mapping
            version_map = {
                ssl.TLSVersion.TLSv1: "TLS 1.0",
                ssl.TLSVersion.TLSv1_1: "TLS 1.1",
                ssl.TLSVersion.TLSv1_2: "TLS 1.2",
                ssl.TLSVersion.TLSv1_3: "TLS 1.3",
            }
            tls_version_str = version_map.get(tls_version, f"Unknown ({tls_version})")

            # Check for deprecated versions
            if tls_version in [ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1_1]:
                warnings.append(f"Deprecated TLS version: {tls_version_str}")

            # Get certificate
            cert = ssock.getpeercert()
            if cert:
                cert_details = get_certificate_details(cert)

                # Certificate validity warnings
                try:
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (not_after - datetime.now()).days
                    if days_until_expiry < 30:
                        warnings.append(f"Certificate expires in {days_until_expiry} days")
                except Exception:
                    pass

            timing = TimingInfo(
                dns_lookup_ms=dns_time,
                tcp_connect_ms=tcp_time,
                tls_handshake_ms=tls_time,
                total_ms=total_time
            )

            ssock.close()

            return ConnectionResult(
                success=True,
                host=host,
                port=port,
                ip_address=ip_address,
                tls_version=tls_version_str,
                cipher_suite=cipher_name,
                cipher_bits=cipher_bits,
                certificate=cert_details,
                timing=timing,
                error=None,
                warnings=warnings
            )

        finally:
            if sock:
                sock.close()

    except socket.gaierror as e:
        return ConnectionResult(
            success=False,
            host=host,
            port=port,
            ip_address="",
            tls_version="",
            cipher_suite="",
            cipher_bits=0,
            certificate=None,
            timing=None,
            error=f"DNS resolution failed: {e}",
            warnings=warnings
        )
    except socket.timeout:
        return ConnectionResult(
            success=False,
            host=host,
            port=port,
            ip_address="",
            tls_version="",
            cipher_suite="",
            cipher_bits=0,
            certificate=None,
            timing=None,
            error=f"Connection timeout after {timeout}s",
            warnings=warnings
        )
    except ssl.SSLError as e:
        return ConnectionResult(
            success=False,
            host=host,
            port=port,
            ip_address=ip_address if 'ip_address' in locals() else "",
            tls_version="",
            cipher_suite="",
            cipher_bits=0,
            certificate=None,
            timing=None,
            error=f"TLS error: {e}",
            warnings=warnings
        )
    except Exception as e:
        return ConnectionResult(
            success=False,
            host=host,
            port=port,
            ip_address=ip_address if 'ip_address' in locals() else "",
            tls_version="",
            cipher_suite="",
            cipher_bits=0,
            certificate=None,
            timing=None,
            error=f"Unexpected error: {e}",
            warnings=warnings
        )


def test_multiple_versions(host: str, port: int, verify_cert: bool, verbose: bool) -> Dict[str, ConnectionResult]:
    """Test all TLS versions"""
    results = {}

    versions = [
        ("TLS 1.0", ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1),
        ("TLS 1.1", ssl.TLSVersion.TLSv1_1, ssl.TLSVersion.TLSv1_1),
        ("TLS 1.2", ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_2),
        ("TLS 1.3", ssl.TLSVersion.TLSv1_3, ssl.TLSVersion.TLSv1_3),
    ]

    for version_name, min_ver, max_ver in versions:
        if verbose:
            print(f"\n[INFO] Testing {version_name}...")

        result = test_tls_connection(
            host=host,
            port=port,
            min_tls_version=min_ver,
            max_tls_version=max_ver,
            verify_cert=verify_cert,
            verbose=verbose
        )
        results[version_name] = result

    return results


def output_text_report(result: ConnectionResult):
    """Output text format report"""
    print(f"\n{'='*60}")
    print(f"TLS Connection Test: {result.host}:{result.port}")
    print(f"{'='*60}\n")

    if result.success:
        print(f"✓ Connection successful")
        print(f"\nConnection Details:")
        print(f"  IP Address: {result.ip_address}")
        print(f"  TLS Version: {result.tls_version}")
        print(f"  Cipher Suite: {result.cipher_suite}")
        print(f"  Cipher Strength: {result.cipher_bits} bits")

        if result.timing:
            print(f"\nTiming:")
            print(f"  DNS Lookup: {result.timing.dns_lookup_ms:.2f}ms")
            print(f"  TCP Connect: {result.timing.tcp_connect_ms:.2f}ms")
            print(f"  TLS Handshake: {result.timing.tls_handshake_ms:.2f}ms")
            print(f"  Total: {result.timing.total_ms:.2f}ms")

        if result.certificate:
            print(f"\nCertificate:")
            if 'commonName' in result.certificate.subject:
                print(f"  Subject CN: {result.certificate.subject['commonName']}")
            if 'organizationName' in result.certificate.subject:
                print(f"  Organization: {result.certificate.subject['organizationName']}")
            if 'commonName' in result.certificate.issuer:
                print(f"  Issuer: {result.certificate.issuer['commonName']}")
            print(f"  Serial: {result.certificate.serial_number}")
            print(f"  Valid From: {result.certificate.not_before}")
            print(f"  Valid Until: {result.certificate.not_after}")
            if result.certificate.subject_alt_names:
                print(f"  SANs: {', '.join(result.certificate.subject_alt_names)}")

        if result.warnings:
            print(f"\n⚠ Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")

    else:
        print(f"✗ Connection failed")
        print(f"\nError: {result.error}")

    print()


def output_json_report(result: ConnectionResult):
    """Output JSON format report"""
    output = {
        'version': VERSION,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'result': {
            'success': result.success,
            'host': result.host,
            'port': result.port,
            'ip_address': result.ip_address,
            'tls_version': result.tls_version,
            'cipher_suite': result.cipher_suite,
            'cipher_bits': result.cipher_bits,
            'error': result.error,
            'warnings': result.warnings,
        }
    }

    if result.timing:
        output['timing'] = asdict(result.timing)

    if result.certificate:
        output['certificate'] = asdict(result.certificate)

    print(json.dumps(output, indent=2))


def output_multi_version_report(results: Dict[str, ConnectionResult], json_output: bool):
    """Output report for multiple version tests"""
    if json_output:
        output = {
            'version': VERSION,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'tests': {}
        }
        for version, result in results.items():
            output['tests'][version] = {
                'success': result.success,
                'cipher_suite': result.cipher_suite if result.success else None,
                'error': result.error
            }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"TLS Version Support Test")
        print(f"{'='*60}\n")

        for version, result in results.items():
            status = "✓ Supported" if result.success else "✗ Not supported"
            print(f"{version:10s} {status}")
            if result.success:
                print(f"            Cipher: {result.cipher_suite}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='TLS Connection Tester',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s example.com
  %(prog)s api.github.com --port 443 --verbose
  %(prog)s example.com --test-all-versions
  %(prog)s example.com --min-tls 1.2 --max-tls 1.3
  %(prog)s example.com --cipher ECDHE-RSA-AES128-GCM-SHA256
  %(prog)s example.com --no-verify --json
        """
    )

    parser.add_argument('host', help='Target host')
    parser.add_argument('--port', type=int, default=443, help='Target port (default: 443)')
    parser.add_argument('--min-tls', choices=['1.0', '1.1', '1.2', '1.3'],
                        default='1.2', help='Minimum TLS version (default: 1.2)')
    parser.add_argument('--max-tls', choices=['1.0', '1.1', '1.2', '1.3'],
                        default='1.3', help='Maximum TLS version (default: 1.3)')
    parser.add_argument('--cipher', help='Specific cipher suite to test')
    parser.add_argument('--test-all-versions', action='store_true',
                        help='Test all TLS versions separately')
    parser.add_argument('--no-verify', action='store_true',
                        help='Disable certificate verification')
    parser.add_argument('--timeout', type=int, default=10,
                        help='Connection timeout in seconds (default: 10)')
    parser.add_argument('-j', '--json', action='store_true',
                        help='Output in JSON format')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')

    args = parser.parse_args()

    # Version mapping
    version_map = {
        '1.0': ssl.TLSVersion.TLSv1,
        '1.1': ssl.TLSVersion.TLSv1_1,
        '1.2': ssl.TLSVersion.TLSv1_2,
        '1.3': ssl.TLSVersion.TLSv1_3,
    }

    # Test all versions mode
    if args.test_all_versions:
        results = test_multiple_versions(
            host=args.host,
            port=args.port,
            verify_cert=not args.no_verify,
            verbose=args.verbose
        )
        output_multi_version_report(results, args.json)
        return 0

    # Single test mode
    min_tls = version_map[args.min_tls]
    max_tls = version_map[args.max_tls]

    result = test_tls_connection(
        host=args.host,
        port=args.port,
        min_tls_version=min_tls,
        max_tls_version=max_tls,
        verify_cert=not args.no_verify,
        cipher_suite=args.cipher,
        timeout=args.timeout,
        verbose=args.verbose
    )

    if args.json:
        output_json_report(result)
    else:
        output_text_report(result)

    return 0 if result.success else 1


if __name__ == '__main__':
    sys.exit(main())
