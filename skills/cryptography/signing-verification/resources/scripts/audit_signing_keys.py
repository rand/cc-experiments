#!/usr/bin/env python3
"""
Signing Key Audit Tool

Audits signing key usage, detects weak algorithms (SHA-1, RSA <2048),
tracks key lifecycle, identifies expiring keys, and performs compliance checking.

Features:
- Key inventory across filesystems and HSMs
- Algorithm strength assessment (weak hash functions, small key sizes)
- Certificate lifecycle tracking (expiration, renewal windows)
- Key usage auditing (signing frequency, last used)
- Compliance checking (FIPS 186-4, Common Criteria, eIDAS)
- Security recommendations
- Automated reporting

Usage:
    audit_signing_keys.py --scan /keys --output report.json
    audit_signing_keys.py --scan /keys --check-compliance fips-186-4
    audit_signing_keys.py --certificate cert.pem --verbose
    audit_signing_keys.py --hsm-module /usr/lib/softhsm/libsofthsm2.so --hsm-pin 1234
    audit_signing_keys.py --scan /keys --expiring-days 90 --warn-weak
"""

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import (
        dsa, ec, ed25519, ed448, rsa
    )
    from cryptography.hazmat.primitives.asymmetric.types import (
        CertificatePublicKeyTypes, PrivateKeyTypes, PublicKeyTypes
    )
    from cryptography.x509.oid import ExtensionOID, NameOID
except ImportError:
    print("Error: cryptography library required. Install: pip install cryptography", file=sys.stderr)
    sys.exit(1)

try:
    import pkcs11
    HAS_PKCS11 = True
except ImportError:
    HAS_PKCS11 = False


@dataclass
class KeyInfo:
    """Key information"""
    path: str
    type: str  # 'private', 'public', 'certificate'
    algorithm: str
    key_size: int
    fingerprint: str
    created: Optional[str] = None
    last_modified: Optional[str] = None


@dataclass
class CertificateInfo:
    """Certificate information"""
    path: str
    subject: str
    issuer: str
    serial_number: str
    not_before: str
    not_after: str
    days_until_expiry: int
    is_expired: bool
    is_self_signed: bool
    key_algorithm: str
    key_size: int
    signature_algorithm: str
    key_usage: List[str]
    extended_key_usage: List[str]
    subject_alt_names: List[str]
    fingerprint_sha256: str


@dataclass
class SecurityIssue:
    """Security issue"""
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    category: str
    description: str
    path: str
    recommendation: str


@dataclass
class AuditReport:
    """Comprehensive audit report"""
    scan_time: str
    scan_paths: List[str]
    total_keys: int = 0
    total_certificates: int = 0
    keys: List[KeyInfo] = field(default_factory=list)
    certificates: List[CertificateInfo] = field(default_factory=list)
    issues: List[SecurityIssue] = field(default_factory=list)
    compliance: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)


class SigningKeyAuditor:
    """Signing key auditing and compliance checking"""

    # Weak algorithms
    WEAK_HASH_ALGORITHMS = {'md5', 'sha1'}
    MINIMUM_RSA_SIZE = 2048
    MINIMUM_EC_SIZE = 224
    MINIMUM_DSA_SIZE = 2048

    # Compliance standards
    FIPS_186_4_APPROVED = {
        'rsa': [2048, 3072, 4096],
        'ecdsa': ['secp256r1', 'secp384r1', 'secp521r1'],
        'dsa': [2048, 3072]
    }

    COMMON_CRITERIA_EAL4_PLUS = {
        'rsa': [2048, 3072, 4096],
        'ecdsa': ['secp256r1', 'secp384r1', 'secp521r1'],
        'ed25519': True
    }

    def __init__(
        self,
        expiring_days: int = 90,
        warn_weak: bool = True,
        compliance_standard: Optional[str] = None
    ):
        self.expiring_days = expiring_days
        self.warn_weak = warn_weak
        self.compliance_standard = compliance_standard
        self.report = AuditReport(
            scan_time=datetime.now(timezone.utc).isoformat(),
            scan_paths=[]
        )

    def scan_directory(self, directory: Path) -> None:
        """Scan directory for keys and certificates"""
        self.report.scan_paths.append(str(directory))

        for root, dirs, files in os.walk(directory):
            root_path = Path(root)

            for filename in files:
                file_path = root_path / filename

                # Skip common non-key files
                if filename.startswith('.') or filename.endswith(('.txt', '.md', '.json')):
                    continue

                try:
                    self._scan_file(file_path)
                except Exception as e:
                    # Skip files that can't be processed
                    pass

    def _scan_file(self, file_path: Path) -> None:
        """Scan individual file"""
        try:
            data = file_path.read_bytes()
        except Exception:
            return

        # Try to parse as private key
        if self._try_parse_private_key(file_path, data):
            return

        # Try to parse as certificate
        if self._try_parse_certificate(file_path, data):
            return

        # Try to parse as public key
        self._try_parse_public_key(file_path, data)

    def _try_parse_private_key(self, file_path: Path, data: bytes) -> bool:
        """Try to parse as private key"""
        key = None

        # Try PEM format
        try:
            key = serialization.load_pem_private_key(data, password=None)
        except Exception:
            pass

        # Try DER format
        if not key:
            try:
                key = serialization.load_der_private_key(data, password=None)
            except Exception:
                pass

        if key:
            key_info = self._extract_key_info(file_path, key, 'private')
            self.report.keys.append(key_info)
            self.report.total_keys += 1

            # Check for security issues
            self._check_key_security(key_info)
            return True

        return False

    def _try_parse_certificate(self, file_path: Path, data: bytes) -> bool:
        """Try to parse as certificate"""
        cert = None

        # Try PEM format
        try:
            cert = x509.load_pem_x509_certificate(data)
        except Exception:
            pass

        # Try DER format
        if not cert:
            try:
                cert = x509.load_der_x509_certificate(data)
            except Exception:
                pass

        if cert:
            cert_info = self._extract_certificate_info(file_path, cert)
            self.report.certificates.append(cert_info)
            self.report.total_certificates += 1

            # Check for security issues
            self._check_certificate_security(cert_info, cert)
            return True

        return False

    def _try_parse_public_key(self, file_path: Path, data: bytes) -> bool:
        """Try to parse as public key"""
        key = None

        # Try PEM format
        try:
            key = serialization.load_pem_public_key(data)
        except Exception:
            pass

        # Try DER format
        if not key:
            try:
                key = serialization.load_der_public_key(data)
            except Exception:
                pass

        if key:
            key_info = self._extract_public_key_info(file_path, key)
            self.report.keys.append(key_info)
            self.report.total_keys += 1

            # Check for security issues
            self._check_key_security(key_info)
            return True

        return False

    def _extract_key_info(self, file_path: Path, key: PrivateKeyTypes, key_type: str) -> KeyInfo:
        """Extract information from private key"""
        if isinstance(key, rsa.RSAPrivateKey):
            algorithm = 'RSA'
            key_size = key.key_size
        elif isinstance(key, ec.EllipticCurvePrivateKey):
            algorithm = f'ECDSA-{key.curve.name}'
            key_size = key.curve.key_size
        elif isinstance(key, ed25519.Ed25519PrivateKey):
            algorithm = 'Ed25519'
            key_size = 256
        elif isinstance(key, ed448.Ed448PrivateKey):
            algorithm = 'Ed448'
            key_size = 448
        elif isinstance(key, dsa.DSAPrivateKey):
            algorithm = 'DSA'
            key_size = key.key_size
        else:
            algorithm = 'unknown'
            key_size = 0

        # Compute fingerprint
        public_key = key.public_key()
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        fingerprint = hashlib.sha256(public_bytes).hexdigest()

        # Get file metadata
        stat = file_path.stat()
        created = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
        last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

        return KeyInfo(
            path=str(file_path),
            type=key_type,
            algorithm=algorithm,
            key_size=key_size,
            fingerprint=fingerprint,
            created=created,
            last_modified=last_modified
        )

    def _extract_public_key_info(self, file_path: Path, key: PublicKeyTypes) -> KeyInfo:
        """Extract information from public key"""
        if isinstance(key, rsa.RSAPublicKey):
            algorithm = 'RSA'
            key_size = key.key_size
        elif isinstance(key, ec.EllipticCurvePublicKey):
            algorithm = f'ECDSA-{key.curve.name}'
            key_size = key.curve.key_size
        elif isinstance(key, ed25519.Ed25519PublicKey):
            algorithm = 'Ed25519'
            key_size = 256
        elif isinstance(key, ed448.Ed448PublicKey):
            algorithm = 'Ed448'
            key_size = 448
        elif isinstance(key, dsa.DSAPublicKey):
            algorithm = 'DSA'
            key_size = key.key_size
        else:
            algorithm = 'unknown'
            key_size = 0

        # Compute fingerprint
        public_bytes = key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        fingerprint = hashlib.sha256(public_bytes).hexdigest()

        # Get file metadata
        stat = file_path.stat()
        created = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
        last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

        return KeyInfo(
            path=str(file_path),
            type='public',
            algorithm=algorithm,
            key_size=key_size,
            fingerprint=fingerprint,
            created=created,
            last_modified=last_modified
        )

    def _extract_certificate_info(self, file_path: Path, cert: x509.Certificate) -> CertificateInfo:
        """Extract information from certificate"""
        # Basic info
        subject = cert.subject.rfc4514_string()
        issuer = cert.issuer.rfc4514_string()
        serial = format(cert.serial_number, 'x')

        # Validity
        now = datetime.now(timezone.utc)
        days_until_expiry = (cert.not_valid_after_utc - now).days
        is_expired = now > cert.not_valid_after_utc
        is_self_signed = cert.issuer == cert.subject

        # Public key info
        public_key = cert.public_key()
        if isinstance(public_key, rsa.RSAPublicKey):
            key_algorithm = 'RSA'
            key_size = public_key.key_size
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            key_algorithm = f'ECDSA-{public_key.curve.name}'
            key_size = public_key.curve.key_size
        elif isinstance(public_key, ed25519.Ed25519PublicKey):
            key_algorithm = 'Ed25519'
            key_size = 256
        elif isinstance(public_key, ed448.Ed448PublicKey):
            key_algorithm = 'Ed448'
            key_size = 448
        else:
            key_algorithm = 'unknown'
            key_size = 0

        # Signature algorithm
        sig_algorithm = cert.signature_algorithm_oid._name

        # Key usage
        key_usage = []
        try:
            ku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
            ku = ku_ext.value
            if ku.digital_signature:
                key_usage.append('digitalSignature')
            if ku.content_commitment:
                key_usage.append('nonRepudiation')
            if ku.key_cert_sign:
                key_usage.append('keyCertSign')
            if ku.crl_sign:
                key_usage.append('cRLSign')
        except x509.ExtensionNotFound:
            pass

        # Extended key usage
        eku = []
        try:
            eku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
            for usage in eku_ext.value:
                eku.append(usage.dotted_string)
        except x509.ExtensionNotFound:
            pass

        # Subject alternative names
        san = []
        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            for name in san_ext.value:
                san.append(str(name))
        except x509.ExtensionNotFound:
            pass

        # Fingerprint
        fingerprint = cert.fingerprint(hashes.SHA256()).hex()

        return CertificateInfo(
            path=str(file_path),
            subject=subject,
            issuer=issuer,
            serial_number=serial,
            not_before=cert.not_valid_before_utc.isoformat(),
            not_after=cert.not_valid_after_utc.isoformat(),
            days_until_expiry=days_until_expiry,
            is_expired=is_expired,
            is_self_signed=is_self_signed,
            key_algorithm=key_algorithm,
            key_size=key_size,
            signature_algorithm=sig_algorithm,
            key_usage=key_usage,
            extended_key_usage=eku,
            subject_alt_names=san,
            fingerprint_sha256=fingerprint
        )

    def _check_key_security(self, key_info: KeyInfo) -> None:
        """Check key for security issues"""
        # Check key size
        if 'RSA' in key_info.algorithm:
            if key_info.key_size < self.MINIMUM_RSA_SIZE:
                self.report.issues.append(SecurityIssue(
                    severity='high',
                    category='weak_key',
                    description=f'RSA key size {key_info.key_size} is below minimum {self.MINIMUM_RSA_SIZE}',
                    path=key_info.path,
                    recommendation=f'Replace with RSA-{self.MINIMUM_RSA_SIZE} or larger'
                ))
        elif 'ECDSA' in key_info.algorithm:
            if key_info.key_size < self.MINIMUM_EC_SIZE:
                self.report.issues.append(SecurityIssue(
                    severity='high',
                    category='weak_key',
                    description=f'ECDSA key size {key_info.key_size} is below minimum {self.MINIMUM_EC_SIZE}',
                    path=key_info.path,
                    recommendation='Replace with P-256 or larger curve'
                ))
        elif 'DSA' in key_info.algorithm:
            self.report.issues.append(SecurityIssue(
                severity='medium',
                category='deprecated_algorithm',
                description='DSA is deprecated',
                path=key_info.path,
                recommendation='Migrate to RSA or ECDSA'
            ))

    def _check_certificate_security(self, cert_info: CertificateInfo, cert: x509.Certificate) -> None:
        """Check certificate for security issues"""
        # Check expiration
        if cert_info.is_expired:
            self.report.issues.append(SecurityIssue(
                severity='critical',
                category='expired_certificate',
                description=f'Certificate expired on {cert_info.not_after}',
                path=cert_info.path,
                recommendation='Renew certificate immediately'
            ))
        elif cert_info.days_until_expiry <= self.expiring_days:
            severity = 'high' if cert_info.days_until_expiry <= 30 else 'medium'
            self.report.issues.append(SecurityIssue(
                severity=severity,
                category='expiring_certificate',
                description=f'Certificate expires in {cert_info.days_until_expiry} days',
                path=cert_info.path,
                recommendation='Renew certificate before expiration'
            ))

        # Check signature algorithm
        sig_algo_lower = cert_info.signature_algorithm.lower()
        if any(weak in sig_algo_lower for weak in self.WEAK_HASH_ALGORITHMS):
            self.report.issues.append(SecurityIssue(
                severity='high',
                category='weak_signature_algorithm',
                description=f'Weak signature algorithm: {cert_info.signature_algorithm}',
                path=cert_info.path,
                recommendation='Reissue certificate with SHA-256 or stronger'
            ))

        # Check key size
        if 'RSA' in cert_info.key_algorithm:
            if cert_info.key_size < self.MINIMUM_RSA_SIZE:
                self.report.issues.append(SecurityIssue(
                    severity='high',
                    category='weak_key',
                    description=f'RSA key size {cert_info.key_size} is below minimum',
                    path=cert_info.path,
                    recommendation=f'Reissue with RSA-{self.MINIMUM_RSA_SIZE} or larger'
                ))

        # Check key usage for code signing
        if 'digitalSignature' not in cert_info.key_usage and 'nonRepudiation' not in cert_info.key_usage:
            if cert_info.key_usage:  # Only warn if key usage is present
                self.report.issues.append(SecurityIssue(
                    severity='low',
                    category='key_usage',
                    description='Certificate lacks signing key usage',
                    path=cert_info.path,
                    recommendation='Verify certificate is intended for signing'
                ))

    def check_compliance(self, standard: str) -> Dict[str, Any]:
        """Check compliance with standard"""
        compliance_result = {
            'standard': standard,
            'compliant': True,
            'violations': []
        }

        if standard == 'fips-186-4':
            compliance_result.update(self._check_fips_186_4())
        elif standard == 'common-criteria-eal4+':
            compliance_result.update(self._check_common_criteria())
        elif standard == 'eidas':
            compliance_result.update(self._check_eidas())
        else:
            compliance_result['compliant'] = False
            compliance_result['violations'].append(f'Unknown standard: {standard}')

        return compliance_result

    def _check_fips_186_4(self) -> Dict[str, Any]:
        """Check FIPS 186-4 compliance"""
        violations = []

        for key in self.report.keys:
            if 'RSA' in key.algorithm:
                if key.key_size not in self.FIPS_186_4_APPROVED['rsa']:
                    violations.append(f'{key.path}: RSA-{key.key_size} not FIPS 186-4 approved')
            elif 'ECDSA' in key.algorithm:
                curve = key.algorithm.split('-')[1]
                if curve not in self.FIPS_186_4_APPROVED['ecdsa']:
                    violations.append(f'{key.path}: ECDSA curve {curve} not FIPS 186-4 approved')
            elif 'DSA' in key.algorithm:
                if key.key_size not in self.FIPS_186_4_APPROVED['dsa']:
                    violations.append(f'{key.path}: DSA-{key.key_size} not FIPS 186-4 approved')

        for cert in self.report.certificates:
            sig_algo_lower = cert.signature_algorithm.lower()
            if 'sha1' in sig_algo_lower or 'md5' in sig_algo_lower:
                violations.append(f'{cert.path}: Weak hash algorithm not FIPS 186-4 approved')

        return {
            'compliant': len(violations) == 0,
            'violations': violations
        }

    def _check_common_criteria(self) -> Dict[str, Any]:
        """Check Common Criteria EAL4+ compliance"""
        violations = []

        for key in self.report.keys:
            if 'RSA' in key.algorithm:
                if key.key_size not in self.COMMON_CRITERIA_EAL4_PLUS['rsa']:
                    violations.append(f'{key.path}: RSA-{key.key_size} below EAL4+ requirements')
            elif 'ECDSA' in key.algorithm:
                curve = key.algorithm.split('-')[1]
                if curve not in self.COMMON_CRITERIA_EAL4_PLUS['ecdsa']:
                    violations.append(f'{key.path}: ECDSA curve {curve} not EAL4+ approved')

        return {
            'compliant': len(violations) == 0,
            'violations': violations
        }

    def _check_eidas(self) -> Dict[str, Any]:
        """Check eIDAS compliance"""
        violations = []

        # eIDAS requires qualified certificates with specific attributes
        for cert in self.report.certificates:
            # Check signature algorithm (must be SHA-256 or stronger)
            sig_algo_lower = cert.signature_algorithm.lower()
            if 'sha1' in sig_algo_lower or 'md5' in sig_algo_lower:
                violations.append(f'{cert.path}: Signature algorithm not eIDAS compliant')

            # Check key size
            if 'RSA' in cert.key_algorithm and cert.key_size < 2048:
                violations.append(f'{cert.path}: RSA key size below eIDAS minimum')
            elif 'ECDSA' in cert.key_algorithm and cert.key_size < 256:
                violations.append(f'{cert.path}: ECDSA key size below eIDAS minimum')

        return {
            'compliant': len(violations) == 0,
            'violations': violations
        }

    def scan_hsm(self, module_path: str, pin: Optional[str] = None) -> None:
        """Scan HSM for signing keys"""
        if not HAS_PKCS11:
            raise RuntimeError("python-pkcs11 library required. Install: pip install python-pkcs11")

        try:
            lib = pkcs11.lib(module_path)
            slots = lib.get_slots()

            for slot in slots:
                try:
                    session = slot.open(user_pin=pin)

                    # Find private keys
                    for obj in session.get_objects({pkcs11.Attribute.CLASS: pkcs11.ObjectClass.PRIVATE_KEY}):
                        try:
                            # Extract key attributes
                            label = obj[pkcs11.Attribute.LABEL]
                            key_type = obj[pkcs11.Attribute.KEY_TYPE]

                            # Create key info
                            key_info = KeyInfo(
                                path=f'hsm://{module_path}/slot{slot.slot_id}/{label}',
                                type='private',
                                algorithm=str(key_type),
                                key_size=0,  # Not easily accessible in PKCS#11
                                fingerprint='N/A'
                            )

                            self.report.keys.append(key_info)
                            self.report.total_keys += 1

                        except Exception:
                            continue

                    session.close()
                except Exception:
                    continue

        except Exception as e:
            raise RuntimeError(f"HSM scan failed: {e}")

    def generate_statistics(self) -> None:
        """Generate statistics"""
        stats = {
            'keys_by_algorithm': {},
            'keys_by_size': {},
            'certificates_by_issuer': {},
            'expiring_soon': 0,
            'expired': 0,
            'self_signed': 0,
            'issues_by_severity': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'info': 0
            }
        }

        # Key statistics
        for key in self.report.keys:
            stats['keys_by_algorithm'][key.algorithm] = stats['keys_by_algorithm'].get(key.algorithm, 0) + 1
            stats['keys_by_size'][key.key_size] = stats['keys_by_size'].get(key.key_size, 0) + 1

        # Certificate statistics
        for cert in self.report.certificates:
            stats['certificates_by_issuer'][cert.issuer] = stats['certificates_by_issuer'].get(cert.issuer, 0) + 1

            if cert.is_expired:
                stats['expired'] += 1
            elif cert.days_until_expiry <= self.expiring_days:
                stats['expiring_soon'] += 1

            if cert.is_self_signed:
                stats['self_signed'] += 1

        # Issue statistics
        for issue in self.report.issues:
            stats['issues_by_severity'][issue.severity] += 1

        self.report.statistics = stats

    def get_report(self) -> AuditReport:
        """Get audit report"""
        self.generate_statistics()

        if self.compliance_standard:
            self.report.compliance = self.check_compliance(self.compliance_standard)

        return self.report


def main():
    parser = argparse.ArgumentParser(
        description='Audit signing keys and certificates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--scan',
        type=Path,
        action='append',
        dest='scan_paths',
        help='Directory to scan for keys and certificates (can be specified multiple times)'
    )

    parser.add_argument(
        '--certificate',
        type=Path,
        help='Audit specific certificate file'
    )

    parser.add_argument(
        '--hsm-module',
        type=str,
        help='PKCS#11 module path for HSM scanning'
    )

    parser.add_argument(
        '--hsm-pin',
        type=str,
        help='HSM PIN'
    )

    parser.add_argument(
        '--expiring-days',
        type=int,
        default=90,
        help='Warn about certificates expiring within N days (default: 90)'
    )

    parser.add_argument(
        '--warn-weak',
        action='store_true',
        default=True,
        help='Warn about weak algorithms (default: true)'
    )

    parser.add_argument(
        '--check-compliance',
        choices=['fips-186-4', 'common-criteria-eal4+', 'eidas'],
        help='Check compliance with standard'
    )

    parser.add_argument(
        '--output',
        type=Path,
        help='Output file for audit report (JSON format)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output report in JSON format'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    if not args.scan_paths and not args.certificate and not args.hsm_module:
        parser.error("At least one of --scan, --certificate, or --hsm-module must be specified")

    # Create auditor
    auditor = SigningKeyAuditor(
        expiring_days=args.expiring_days,
        warn_weak=args.warn_weak,
        compliance_standard=args.check_compliance
    )

    # Scan directories
    if args.scan_paths:
        for scan_path in args.scan_paths:
            if not scan_path.is_dir():
                print(f"Warning: {scan_path} is not a directory", file=sys.stderr)
                continue
            auditor.scan_directory(scan_path)

    # Audit specific certificate
    if args.certificate:
        auditor._scan_file(args.certificate)

    # Scan HSM
    if args.hsm_module:
        try:
            auditor.scan_hsm(args.hsm_module, args.hsm_pin)
        except Exception as e:
            print(f"Error scanning HSM: {e}", file=sys.stderr)
            sys.exit(1)

    # Get report
    report = auditor.get_report()

    # Output report
    if args.json or args.output:
        output_data = asdict(report)

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"Audit report written to {args.output}")
        else:
            print(json.dumps(output_data, indent=2))
    else:
        # Human-readable output
        print("=" * 80)
        print("SIGNING KEY AUDIT REPORT")
        print("=" * 80)
        print(f"\nScan Time: {report.scan_time}")
        print(f"Scan Paths: {', '.join(report.scan_paths)}")
        print(f"\nTotal Keys: {report.total_keys}")
        print(f"Total Certificates: {report.total_certificates}")

        # Statistics
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)

        if report.statistics['keys_by_algorithm']:
            print("\nKeys by Algorithm:")
            for algo, count in sorted(report.statistics['keys_by_algorithm'].items()):
                print(f"  {algo}: {count}")

        if report.statistics['certificates_by_issuer']:
            print("\nCertificates by Issuer:")
            for issuer, count in sorted(report.statistics['certificates_by_issuer'].items()):
                print(f"  {issuer}: {count}")

        print(f"\nExpiring Soon ({args.expiring_days} days): {report.statistics['expiring_soon']}")
        print(f"Expired: {report.statistics['expired']}")
        print(f"Self-Signed: {report.statistics['self_signed']}")

        # Issues
        if report.issues:
            print("\n" + "=" * 80)
            print("SECURITY ISSUES")
            print("=" * 80)

            issues_by_severity = {}
            for issue in report.issues:
                if issue.severity not in issues_by_severity:
                    issues_by_severity[issue.severity] = []
                issues_by_severity[issue.severity].append(issue)

            for severity in ['critical', 'high', 'medium', 'low', 'info']:
                if severity in issues_by_severity:
                    print(f"\n{severity.upper()} ({len(issues_by_severity[severity])}):")
                    for issue in issues_by_severity[severity]:
                        print(f"\n  [{issue.category}] {issue.path}")
                        print(f"  {issue.description}")
                        print(f"  Recommendation: {issue.recommendation}")

        # Compliance
        if report.compliance:
            print("\n" + "=" * 80)
            print("COMPLIANCE CHECK")
            print("=" * 80)
            print(f"\nStandard: {report.compliance['standard']}")
            print(f"Compliant: {'✓' if report.compliance['compliant'] else '✗'}")

            if report.compliance['violations']:
                print("\nViolations:")
                for violation in report.compliance['violations']:
                    print(f"  • {violation}")

        # Verbose output
        if args.verbose:
            if report.certificates:
                print("\n" + "=" * 80)
                print("CERTIFICATES")
                print("=" * 80)

                for cert in report.certificates:
                    print(f"\nPath: {cert.path}")
                    print(f"Subject: {cert.subject}")
                    print(f"Issuer: {cert.issuer}")
                    print(f"Not Before: {cert.not_before}")
                    print(f"Not After: {cert.not_after}")
                    print(f"Days Until Expiry: {cert.days_until_expiry}")
                    print(f"Algorithm: {cert.key_algorithm} ({cert.key_size} bits)")
                    print(f"Signature Algorithm: {cert.signature_algorithm}")
                    if cert.key_usage:
                        print(f"Key Usage: {', '.join(cert.key_usage)}")
                    if cert.extended_key_usage:
                        print(f"Extended Key Usage: {', '.join(cert.extended_key_usage)}")

    # Exit with error if critical issues found
    critical_count = report.statistics['issues_by_severity']['critical']
    sys.exit(1 if critical_count > 0 else 0)


if __name__ == '__main__':
    main()
