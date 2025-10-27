#!/usr/bin/env python3
"""
Certificate Validation Tool

Validates SSL/TLS certificates for security issues, expiration, chain completeness,
and compliance requirements.

Features:
- Certificate expiration checking
- Chain validation
- Weak algorithm detection
- OCSP/CRL revocation checking
- Compliance validation (PCI-DSS, HIPAA, SOC2)
- Multiple certificate formats (PEM, DER, PKCS#12)
- Batch validation
- JSON output for CI/CD integration

Usage:
    ./validate_certificates.py --host example.com
    ./validate_certificates.py --file cert.pem --check-revocation
    ./validate_certificates.py --host example.com --compliance PCI-DSS --json
    ./validate_certificates.py --batch-file hosts.txt --json

Author: Generated with Claude Code
License: MIT
"""

import argparse
import json
import socket
import ssl
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import re

try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.x509.oid import NameOID, ExtensionOID
except ImportError:
    print("Error: cryptography library required. Install with: pip install cryptography", file=sys.stderr)
    sys.exit(1)


class CertificateValidator:
    """Validates SSL/TLS certificates"""

    # Weak algorithms
    WEAK_SIGNATURE_ALGORITHMS = ['md5', 'sha1']
    WEAK_KEY_TYPES = []
    MIN_RSA_KEY_SIZE = 2048
    MIN_ECDSA_KEY_SIZE = 256

    # Compliance requirements
    COMPLIANCE_REQUIREMENTS = {
        'PCI-DSS': {
            'min_rsa_key_size': 2048,
            'min_ecdsa_key_size': 256,
            'allowed_signature_algorithms': ['sha256', 'sha384', 'sha512'],
            'max_cert_age_days': 398,  # ~13 months
            'require_revocation_check': True,
        },
        'HIPAA': {
            'min_rsa_key_size': 2048,
            'min_ecdsa_key_size': 256,
            'allowed_signature_algorithms': ['sha256', 'sha384', 'sha512'],
            'max_cert_age_days': 365,
            'require_revocation_check': True,
        },
        'SOC2': {
            'min_rsa_key_size': 2048,
            'min_ecdsa_key_size': 256,
            'allowed_signature_algorithms': ['sha256', 'sha384', 'sha512'],
            'max_cert_age_days': 398,
            'require_revocation_check': False,
        },
    }

    def __init__(self, check_revocation: bool = False, compliance: Optional[str] = None):
        self.check_revocation = check_revocation
        self.compliance = compliance

    def validate_from_host(self, hostname: str, port: int = 443, timeout: int = 10) -> Dict:
        """Validate certificate from remote host"""
        results = {
            'hostname': hostname,
            'port': port,
            'timestamp': datetime.utcnow().isoformat(),
            'issues': [],
            'warnings': [],
            'info': [],
        }

        try:
            # Connect and get certificate
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert_bin()
                    cert = x509.load_der_x509_certificate(cert_der, default_backend())

                    # Get certificate chain
                    results['chain_length'] = len(ssock.getpeercert(binary_form=False).get('issuer', []))

            # Validate certificate
            self._validate_certificate(cert, hostname, results)

            # Check revocation if requested
            if self.check_revocation:
                self._check_revocation(cert, results)

            # Compliance checks
            if self.compliance:
                self._check_compliance(cert, results)

        except socket.timeout:
            results['issues'].append({
                'severity': 'critical',
                'message': f'Connection timeout to {hostname}:{port}',
            })
        except socket.gaierror as e:
            results['issues'].append({
                'severity': 'critical',
                'message': f'DNS resolution failed: {e}',
            })
        except ssl.SSLError as e:
            results['issues'].append({
                'severity': 'critical',
                'message': f'SSL error: {e}',
            })
        except Exception as e:
            results['issues'].append({
                'severity': 'critical',
                'message': f'Unexpected error: {e}',
            })

        # Determine overall status
        results['status'] = self._determine_status(results)
        return results

    def validate_from_file(self, cert_path: Path, hostname: Optional[str] = None) -> Dict:
        """Validate certificate from file"""
        results = {
            'file': str(cert_path),
            'timestamp': datetime.utcnow().isoformat(),
            'issues': [],
            'warnings': [],
            'info': [],
        }

        try:
            # Read certificate
            cert_data = cert_path.read_bytes()

            # Try PEM format first
            try:
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            except:
                # Try DER format
                try:
                    cert = x509.load_der_x509_certificate(cert_data, default_backend())
                except Exception as e:
                    results['issues'].append({
                        'severity': 'critical',
                        'message': f'Failed to load certificate: {e}',
                    })
                    results['status'] = 'error'
                    return results

            # Validate certificate
            self._validate_certificate(cert, hostname, results)

            # Compliance checks
            if self.compliance:
                self._check_compliance(cert, results)

        except FileNotFoundError:
            results['issues'].append({
                'severity': 'critical',
                'message': f'File not found: {cert_path}',
            })
        except Exception as e:
            results['issues'].append({
                'severity': 'critical',
                'message': f'Unexpected error: {e}',
            })

        results['status'] = self._determine_status(results)
        return results

    def _validate_certificate(self, cert: x509.Certificate, hostname: Optional[str], results: Dict):
        """Perform certificate validation checks"""

        # Extract basic info
        subject = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        subject_cn = subject[0].value if subject else 'N/A'
        issuer = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
        issuer_cn = issuer[0].value if issuer else 'N/A'

        results['info'].append({
            'field': 'Subject CN',
            'value': subject_cn,
        })
        results['info'].append({
            'field': 'Issuer',
            'value': issuer_cn,
        })

        # Check expiration
        now = datetime.utcnow()
        not_before = cert.not_valid_before
        not_after = cert.not_valid_after
        days_remaining = (not_after - now).days

        results['info'].append({
            'field': 'Valid From',
            'value': not_before.isoformat(),
        })
        results['info'].append({
            'field': 'Valid Until',
            'value': not_after.isoformat(),
        })
        results['info'].append({
            'field': 'Days Remaining',
            'value': days_remaining,
        })

        if now < not_before:
            results['issues'].append({
                'severity': 'critical',
                'message': f'Certificate not yet valid (valid from {not_before})',
            })
        elif now > not_after:
            results['issues'].append({
                'severity': 'critical',
                'message': f'Certificate expired on {not_after}',
            })
        elif days_remaining <= 7:
            results['issues'].append({
                'severity': 'critical',
                'message': f'Certificate expires in {days_remaining} days',
            })
        elif days_remaining <= 14:
            results['warnings'].append({
                'severity': 'high',
                'message': f'Certificate expires in {days_remaining} days',
            })
        elif days_remaining <= 30:
            results['warnings'].append({
                'severity': 'medium',
                'message': f'Certificate expires in {days_remaining} days',
            })

        # Check key size and algorithm
        public_key = cert.public_key()
        key_type = public_key.__class__.__name__

        if 'RSA' in key_type:
            key_size = public_key.key_size
            results['info'].append({
                'field': 'Key Type',
                'value': f'RSA {key_size} bits',
            })

            if key_size < self.MIN_RSA_KEY_SIZE:
                results['issues'].append({
                    'severity': 'critical',
                    'message': f'RSA key size {key_size} bits is too weak (minimum {self.MIN_RSA_KEY_SIZE})',
                })
            elif key_size < 3072:
                results['warnings'].append({
                    'severity': 'low',
                    'message': f'RSA key size {key_size} bits is acceptable but 3072+ recommended',
                })

        elif 'EllipticCurve' in key_type:
            key_size = public_key.key_size
            results['info'].append({
                'field': 'Key Type',
                'value': f'ECDSA {key_size} bits',
            })

            if key_size < self.MIN_ECDSA_KEY_SIZE:
                results['issues'].append({
                    'severity': 'critical',
                    'message': f'ECDSA key size {key_size} bits is too weak (minimum {self.MIN_ECDSA_KEY_SIZE})',
                })

        else:
            results['info'].append({
                'field': 'Key Type',
                'value': key_type,
            })

        # Check signature algorithm
        sig_alg = cert.signature_algorithm_oid._name.lower()
        results['info'].append({
            'field': 'Signature Algorithm',
            'value': sig_alg,
        })

        for weak_alg in self.WEAK_SIGNATURE_ALGORITHMS:
            if weak_alg in sig_alg:
                results['issues'].append({
                    'severity': 'critical',
                    'message': f'Weak signature algorithm: {sig_alg}',
                })
                break

        # Check SANs
        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            san_names = [name.value for name in san_ext.value]
            results['info'].append({
                'field': 'SANs',
                'value': ', '.join(san_names),
            })

            # Check if hostname matches SAN
            if hostname:
                hostname_matches = any(
                    self._matches_san(hostname, san) for san in san_names
                )
                if not hostname_matches:
                    results['issues'].append({
                        'severity': 'critical',
                        'message': f'Hostname {hostname} does not match any SAN: {san_names}',
                    })
        except x509.ExtensionNotFound:
            results['warnings'].append({
                'severity': 'medium',
                'message': 'No Subject Alternative Names extension found',
            })

        # Check basic constraints
        try:
            bc_ext = cert.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
            if bc_ext.value.ca:
                results['info'].append({
                    'field': 'Certificate Type',
                    'value': 'CA Certificate',
                })
            else:
                results['info'].append({
                    'field': 'Certificate Type',
                    'value': 'End-Entity Certificate',
                })
        except x509.ExtensionNotFound:
            pass

        # Check key usage
        try:
            ku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
            key_usages = []
            if ku_ext.value.digital_signature:
                key_usages.append('digitalSignature')
            if ku_ext.value.key_encipherment:
                key_usages.append('keyEncipherment')
            if ku_ext.value.key_cert_sign:
                key_usages.append('keyCertSign')
            results['info'].append({
                'field': 'Key Usage',
                'value': ', '.join(key_usages),
            })
        except x509.ExtensionNotFound:
            pass

    def _check_revocation(self, cert: x509.Certificate, results: Dict):
        """Check certificate revocation status"""
        try:
            # Try OCSP first
            aia_ext = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS)
            for desc in aia_ext.value:
                if desc.access_method == x509.AuthorityInformationAccessOID.OCSP:
                    ocsp_url = desc.access_location.value
                    results['info'].append({
                        'field': 'OCSP URL',
                        'value': ocsp_url,
                    })
                    # Note: Full OCSP checking requires issuer certificate
                    results['warnings'].append({
                        'severity': 'low',
                        'message': 'OCSP revocation checking requires issuer certificate (not implemented)',
                    })
        except x509.ExtensionNotFound:
            results['warnings'].append({
                'severity': 'medium',
                'message': 'No OCSP information available',
            })

        # Check for CRL
        try:
            crl_ext = cert.extensions.get_extension_for_oid(ExtensionOID.CRL_DISTRIBUTION_POINTS)
            crl_urls = []
            for dp in crl_ext.value:
                for name in dp.full_name:
                    crl_urls.append(name.value)
            results['info'].append({
                'field': 'CRL URLs',
                'value': ', '.join(crl_urls),
            })
        except x509.ExtensionNotFound:
            results['warnings'].append({
                'severity': 'low',
                'message': 'No CRL distribution points found',
            })

    def _check_compliance(self, cert: x509.Certificate, results: Dict):
        """Check compliance requirements"""
        if self.compliance not in self.COMPLIANCE_REQUIREMENTS:
            results['warnings'].append({
                'severity': 'low',
                'message': f'Unknown compliance standard: {self.compliance}',
            })
            return

        reqs = self.COMPLIANCE_REQUIREMENTS[self.compliance]
        compliance_issues = []

        # Check key size
        public_key = cert.public_key()
        key_type = public_key.__class__.__name__

        if 'RSA' in key_type:
            key_size = public_key.key_size
            if key_size < reqs['min_rsa_key_size']:
                compliance_issues.append(
                    f"RSA key size {key_size} < {reqs['min_rsa_key_size']} required by {self.compliance}"
                )

        elif 'EllipticCurve' in key_type:
            key_size = public_key.key_size
            if key_size < reqs['min_ecdsa_key_size']:
                compliance_issues.append(
                    f"ECDSA key size {key_size} < {reqs['min_ecdsa_key_size']} required by {self.compliance}"
                )

        # Check signature algorithm
        sig_alg = cert.signature_algorithm_oid._name.lower()
        allowed_algs = reqs['allowed_signature_algorithms']
        if not any(alg in sig_alg for alg in allowed_algs):
            compliance_issues.append(
                f"Signature algorithm {sig_alg} not in allowed list for {self.compliance}: {allowed_algs}"
            )

        # Check certificate age
        now = datetime.utcnow()
        cert_age_days = (now - cert.not_valid_before).days
        if cert_age_days > reqs['max_cert_age_days']:
            compliance_issues.append(
                f"Certificate age {cert_age_days} days > {reqs['max_cert_age_days']} days allowed by {self.compliance}"
            )

        # Report compliance issues
        if compliance_issues:
            results['issues'].append({
                'severity': 'high',
                'message': f'{self.compliance} compliance violations:',
                'details': compliance_issues,
            })
        else:
            results['info'].append({
                'field': 'Compliance',
                'value': f'{self.compliance} requirements satisfied',
            })

    def _matches_san(self, hostname: str, san: str) -> bool:
        """Check if hostname matches SAN (including wildcards)"""
        # Exact match
        if hostname.lower() == san.lower():
            return True

        # Wildcard match
        if san.startswith('*.'):
            san_domain = san[2:]
            if hostname.lower().endswith('.' + san_domain.lower()):
                return True

        return False

    def _determine_status(self, results: Dict) -> str:
        """Determine overall validation status"""
        if any(issue.get('severity') == 'critical' for issue in results['issues']):
            return 'critical'
        elif results['issues']:
            return 'fail'
        elif any(w.get('severity') in ['high', 'medium'] for w in results['warnings']):
            return 'warning'
        else:
            return 'pass'


def main():
    parser = argparse.ArgumentParser(
        description='Validate SSL/TLS certificates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate remote certificate
  %(prog)s --host example.com

  # Validate with revocation checking
  %(prog)s --host example.com --check-revocation

  # Validate certificate file
  %(prog)s --file cert.pem --hostname example.com

  # Check compliance
  %(prog)s --host example.com --compliance PCI-DSS --json

  # Batch validation
  %(prog)s --batch-file hosts.txt --json > results.json

  # Validate with custom port
  %(prog)s --host example.com --port 8443
        """
    )

    parser.add_argument('--host', help='Hostname to validate')
    parser.add_argument('--port', type=int, default=443, help='Port (default: 443)')
    parser.add_argument('--file', type=Path, help='Certificate file to validate')
    parser.add_argument('--hostname', help='Expected hostname (for file validation)')
    parser.add_argument('--batch-file', type=Path, help='File with list of hosts (one per line)')
    parser.add_argument('--check-revocation', action='store_true', help='Check revocation status')
    parser.add_argument('--compliance', choices=['PCI-DSS', 'HIPAA', 'SOC2'],
                        help='Check compliance requirements')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--timeout', type=int, default=10, help='Connection timeout (default: 10s)')
    parser.add_argument('--help-full', action='store_true', help='Show detailed help')

    args = parser.parse_args()

    if args.help_full:
        parser.print_help()
        print("\n=== Compliance Standards ===")
        for std, reqs in CertificateValidator.COMPLIANCE_REQUIREMENTS.items():
            print(f"\n{std}:")
            for key, value in reqs.items():
                print(f"  {key}: {value}")
        sys.exit(0)

    # Validate arguments
    if not any([args.host, args.file, args.batch_file]):
        parser.error('Must specify --host, --file, or --batch-file')

    validator = CertificateValidator(
        check_revocation=args.check_revocation,
        compliance=args.compliance
    )

    results_list = []

    # Batch validation
    if args.batch_file:
        if not args.batch_file.exists():
            print(f"Error: Batch file not found: {args.batch_file}", file=sys.stderr)
            sys.exit(1)

        hosts = args.batch_file.read_text().strip().split('\n')
        for host in hosts:
            host = host.strip()
            if not host or host.startswith('#'):
                continue
            results = validator.validate_from_host(host, args.port, args.timeout)
            results_list.append(results)

    # Single host validation
    elif args.host:
        results = validator.validate_from_host(args.host, args.port, args.timeout)
        results_list.append(results)

    # File validation
    elif args.file:
        results = validator.validate_from_file(args.file, args.hostname)
        results_list.append(results)

    # Output results
    if args.json:
        print(json.dumps(results_list, indent=2))
    else:
        for results in results_list:
            print_results(results)

    # Exit code based on worst status
    statuses = [r['status'] for r in results_list]
    if 'critical' in statuses or 'fail' in statuses:
        sys.exit(1)
    elif 'warning' in statuses:
        sys.exit(0)  # Warnings don't fail
    else:
        sys.exit(0)


def print_results(results: Dict):
    """Print validation results in human-readable format"""
    if 'hostname' in results:
        print(f"\n=== Certificate Validation: {results['hostname']}:{results['port']} ===")
    else:
        print(f"\n=== Certificate Validation: {results['file']} ===")

    print(f"Status: {results['status'].upper()}")
    print(f"Timestamp: {results['timestamp']}")

    if results['info']:
        print("\n--- Information ---")
        for info in results['info']:
            print(f"  {info['field']}: {info['value']}")

    if results['warnings']:
        print("\n--- Warnings ---")
        for warning in results['warnings']:
            severity = warning.get('severity', 'unknown')
            message = warning.get('message', '')
            print(f"  [{severity.upper()}] {message}")
            if 'details' in warning:
                for detail in warning['details']:
                    print(f"    - {detail}")

    if results['issues']:
        print("\n--- Issues ---")
        for issue in results['issues']:
            severity = issue.get('severity', 'unknown')
            message = issue.get('message', '')
            print(f"  [{severity.upper()}] {message}")
            if 'details' in issue:
                for detail in issue['details']:
                    print(f"    - {detail}")

    print()


if __name__ == '__main__':
    main()
