#!/usr/bin/env python3
"""
check_cipher_suites.py
List and verify TLS cipher suites for a given host or configuration
"""

import argparse
import json
import ssl
import socket
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


VERSION = "1.0.0"

# TLS version mappings
TLS_VERSIONS = {
    ssl.TLSVersion.TLSv1: "TLS 1.0",
    ssl.TLSVersion.TLSv1_1: "TLS 1.1",
    ssl.TLSVersion.TLSv1_2: "TLS 1.2",
    ssl.TLSVersion.TLSv1_3: "TLS 1.3",
}

# Cipher suite security ratings
WEAK_CIPHERS = {
    'DES', 'RC4', 'MD5', 'EXPORT', 'NULL', 'aNULL', 'eNULL',
    'IDEA', 'SEED', 'CBC', '3DES'
}

STRONG_CIPHERS = {
    'ECDHE', 'DHE', 'GCM', 'CHACHA20', 'POLY1305', 'AES256', 'AES128'
}


@dataclass
class CipherSuiteInfo:
    """Information about a cipher suite"""
    name: str
    protocol_version: str
    bits: int
    has_forward_secrecy: bool
    is_aead: bool
    security_rating: str
    warnings: List[str]


@dataclass
class ScanResult:
    """TLS scan results"""
    host: str
    port: int
    supported_protocols: List[str]
    cipher_suites: List[CipherSuiteInfo]
    certificate_info: Optional[Dict]
    security_score: str
    total_ciphers: int
    weak_ciphers: int
    warnings: List[str]


def analyze_cipher_suite(cipher_name: str, protocol: str) -> CipherSuiteInfo:
    """Analyze a cipher suite and return security information"""
    warnings = []
    has_forward_secrecy = False
    is_aead = False
    security_rating = "MEDIUM"

    # Check for weak components
    for weak in WEAK_CIPHERS:
        if weak in cipher_name.upper():
            warnings.append(f"Contains weak component: {weak}")
            security_rating = "WEAK"

    # Check for strong components
    if 'ECDHE' in cipher_name or 'DHE' in cipher_name:
        has_forward_secrecy = True

    if 'GCM' in cipher_name or 'CHACHA20' in cipher_name or 'POLY1305' in cipher_name:
        is_aead = True

    # Determine security rating
    if security_rating != "WEAK":
        if has_forward_secrecy and is_aead:
            security_rating = "STRONG"
        elif has_forward_secrecy or is_aead:
            security_rating = "MEDIUM"

    # Protocol-specific warnings
    if protocol in ["TLS 1.0", "TLS 1.1"]:
        warnings.append(f"Deprecated protocol: {protocol}")
        if security_rating == "STRONG":
            security_rating = "MEDIUM"

    # Extract key size (approximate)
    bits = 128
    if 'AES256' in cipher_name or 'CAMELLIA256' in cipher_name:
        bits = 256
    elif 'AES128' in cipher_name or 'CAMELLIA128' in cipher_name:
        bits = 128
    elif '3DES' in cipher_name:
        bits = 168

    return CipherSuiteInfo(
        name=cipher_name,
        protocol_version=protocol,
        bits=bits,
        has_forward_secrecy=has_forward_secrecy,
        is_aead=is_aead,
        security_rating=security_rating,
        warnings=warnings
    )


def test_cipher_suite(host: str, port: int, cipher: str, tls_version: ssl.TLSVersion) -> Optional[Tuple[str, str]]:
    """Test if a specific cipher suite is supported"""
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers(cipher)
        context.minimum_version = tls_version
        context.maximum_version = tls_version

        with socket.create_connection((host, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                return (ssock.cipher()[0], TLS_VERSIONS[ssock.version()])
    except Exception:
        return None


def scan_host(host: str, port: int = 443, verbose: bool = False) -> ScanResult:
    """Scan a host and identify supported cipher suites"""
    supported_protocols = []
    cipher_suites = []
    certificate_info = None
    warnings = []

    # Get all available ciphers
    all_ciphers = []
    try:
        # Get default cipher list
        ctx = ssl.create_default_context()
        all_ciphers = ctx.get_ciphers()
    except Exception as e:
        warnings.append(f"Failed to get cipher list: {e}")

    # Test TLS versions
    for tls_version, version_name in TLS_VERSIONS.items():
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.minimum_version = tls_version
            context.maximum_version = tls_version

            with socket.create_connection((host, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    supported_protocols.append(version_name)
                    cipher_name = ssock.cipher()[0]

                    # Get certificate info on first successful connection
                    if certificate_info is None:
                        cert = ssock.getpeercert()
                        if cert:
                            certificate_info = {
                                'subject': dict(x[0] for x in cert['subject']),
                                'issuer': dict(x[0] for x in cert['issuer']),
                                'version': cert.get('version'),
                                'serialNumber': cert.get('serialNumber'),
                                'notBefore': cert.get('notBefore'),
                                'notAfter': cert.get('notAfter'),
                            }

                    # Analyze the negotiated cipher
                    cipher_info = analyze_cipher_suite(cipher_name, version_name)
                    if cipher_info not in cipher_suites:
                        cipher_suites.append(cipher_info)

                    if verbose:
                        print(f"[INFO] {version_name}: {cipher_name}")

        except Exception as e:
            if verbose:
                print(f"[INFO] {version_name} not supported: {e}")

    # Calculate security score
    weak_count = sum(1 for c in cipher_suites if c.security_rating == "WEAK")
    strong_count = sum(1 for c in cipher_suites if c.security_rating == "STRONG")

    if weak_count > 0:
        security_score = "C"
        warnings.append(f"{weak_count} weak cipher suite(s) found")
    elif strong_count == len(cipher_suites) and "TLS 1.3" in supported_protocols:
        security_score = "A+"
    elif strong_count >= len(cipher_suites) * 0.8:
        security_score = "A"
    else:
        security_score = "B"

    # Protocol warnings
    if "TLS 1.0" in supported_protocols or "TLS 1.1" in supported_protocols:
        warnings.append("Deprecated TLS versions supported (1.0 or 1.1)")

    if "TLS 1.3" not in supported_protocols:
        warnings.append("TLS 1.3 not supported")

    return ScanResult(
        host=host,
        port=port,
        supported_protocols=supported_protocols,
        cipher_suites=cipher_suites,
        certificate_info=certificate_info,
        security_score=security_score,
        total_ciphers=len(cipher_suites),
        weak_ciphers=weak_count,
        warnings=warnings
    )


def list_available_ciphers(tls_version: Optional[str] = None) -> List[str]:
    """List all available cipher suites for the system"""
    ciphers = []

    if tls_version:
        # Map version string to ssl.TLSVersion
        version_map = {
            "1.0": ssl.TLSVersion.TLSv1,
            "1.1": ssl.TLSVersion.TLSv1_1,
            "1.2": ssl.TLSVersion.TLSv1_2,
            "1.3": ssl.TLSVersion.TLSv1_3,
        }

        if tls_version not in version_map:
            raise ValueError(f"Invalid TLS version: {tls_version}")

        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version = version_map[tls_version]
            context.maximum_version = version_map[tls_version]
            ciphers = [c['name'] for c in context.get_ciphers()]
        except Exception as e:
            print(f"Error getting ciphers for TLS {tls_version}: {e}", file=sys.stderr)
    else:
        # Get all ciphers
        context = ssl.create_default_context()
        ciphers = [c['name'] for c in context.get_ciphers()]

    return sorted(ciphers)


def output_text_report(result: ScanResult):
    """Output results in text format"""
    print(f"\n{'='*60}")
    print(f"TLS Cipher Suite Analysis: {result.host}:{result.port}")
    print(f"{'='*60}\n")

    print(f"Security Score: {result.security_score}")
    print(f"Supported Protocols: {', '.join(result.supported_protocols)}")
    print(f"Total Cipher Suites: {result.total_ciphers}")
    print(f"Weak Ciphers: {result.weak_ciphers}")

    if result.warnings:
        print(f"\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    print(f"\n{'='*60}")
    print("Cipher Suites:")
    print(f"{'='*60}")

    for cipher in result.cipher_suites:
        rating_color = {
            'STRONG': '\033[92m',  # Green
            'MEDIUM': '\033[93m',  # Yellow
            'WEAK': '\033[91m',     # Red
        }.get(cipher.security_rating, '')
        reset_color = '\033[0m' if rating_color else ''

        print(f"\n{cipher.name}")
        print(f"  Protocol: {cipher.protocol_version}")
        print(f"  Bits: {cipher.bits}")
        print(f"  Forward Secrecy: {'Yes' if cipher.has_forward_secrecy else 'No'}")
        print(f"  AEAD: {'Yes' if cipher.is_aead else 'No'}")
        print(f"  Rating: {rating_color}{cipher.security_rating}{reset_color}")

        if cipher.warnings:
            for warning in cipher.warnings:
                print(f"  ⚠ {warning}")

    if result.certificate_info:
        print(f"\n{'='*60}")
        print("Certificate Information:")
        print(f"{'='*60}")
        cert = result.certificate_info
        if 'commonName' in cert['subject']:
            print(f"Subject: {cert['subject']['commonName']}")
        if 'commonName' in cert['issuer']:
            print(f"Issuer: {cert['issuer']['commonName']}")
        if 'notBefore' in cert:
            print(f"Valid From: {cert['notBefore']}")
        if 'notAfter' in cert:
            print(f"Valid Until: {cert['notAfter']}")


def output_json_report(result: ScanResult):
    """Output results in JSON format"""
    output = {
        'version': VERSION,
        'timestamp': None,  # Would use datetime in production
        'scan': {
            'host': result.host,
            'port': result.port,
            'security_score': result.security_score,
        },
        'protocols': result.supported_protocols,
        'cipher_suites': [asdict(c) for c in result.cipher_suites],
        'certificate': result.certificate_info,
        'summary': {
            'total_ciphers': result.total_ciphers,
            'weak_ciphers': result.weak_ciphers,
            'warnings': result.warnings,
        }
    }
    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description='TLS Cipher Suite Checker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --host example.com
  %(prog)s --host api.github.com --port 443 --json
  %(prog)s --list-ciphers
  %(prog)s --list-ciphers --tls-version 1.3
        """
    )

    parser.add_argument('--host', help='Target host to scan')
    parser.add_argument('--port', type=int, default=443, help='Target port (default: 443)')
    parser.add_argument('--list-ciphers', action='store_true',
                        help='List available cipher suites on this system')
    parser.add_argument('--tls-version', choices=['1.0', '1.1', '1.2', '1.3'],
                        help='Filter ciphers by TLS version')
    parser.add_argument('-j', '--json', action='store_true',
                        help='Output in JSON format')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')

    args = parser.parse_args()

    # List ciphers mode
    if args.list_ciphers:
        ciphers = list_available_ciphers(args.tls_version)
        if args.json:
            print(json.dumps({
                'tls_version': args.tls_version or 'all',
                'ciphers': ciphers,
                'count': len(ciphers)
            }, indent=2))
        else:
            version_str = f"TLS {args.tls_version}" if args.tls_version else "All TLS versions"
            print(f"\nAvailable Cipher Suites ({version_str}):")
            print(f"{'='*60}")
            for i, cipher in enumerate(ciphers, 1):
                print(f"{i:3d}. {cipher}")
            print(f"\nTotal: {len(ciphers)} cipher suites")
        return 0

    # Scan mode
    if not args.host:
        parser.error("--host is required for scanning mode")

    try:
        result = scan_host(args.host, args.port, args.verbose)

        if args.json:
            output_json_report(result)
        else:
            output_text_report(result)

        # Exit with error code if weak ciphers found
        return 1 if result.weak_ciphers > 0 else 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
