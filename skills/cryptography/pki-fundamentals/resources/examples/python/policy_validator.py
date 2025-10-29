#!/usr/bin/env python3
"""
Certificate Policy Validator

Validates certificates against Certificate Practice Statement (CPS) and
Certificate Policy (CP) requirements. Enforces organizational policy rules.

Usage:
    ./policy_validator.py --help
    ./policy_validator.py --cert cert.pem --policy policy.yaml
    ./policy_validator.py --cert cert.pem --policy policy.yaml --strict
    ./policy_validator.py --scan-dir /etc/ssl/certs --policy policy.yaml --report violations.json

Policy YAML format:
    allowed_key_types: [RSA, EC]
    min_rsa_key_size: 2048
    allowed_signature_algorithms: [sha256WithRSAEncryption, ecdsa-with-SHA256]
    max_validity_days: 398
    required_extensions: [keyUsage, extendedKeyUsage, subjectAlternativeName]
    allowed_issuers: ["CN=Example CA"]
    forbidden_domains: [".local", ".internal"]
"""

import argparse
import json
import sys
import os
import re
import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict, field

try:
    import yaml
except ImportError:
    print("Error: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtensionOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import rsa, ec, dsa
except ImportError:
    print("Error: cryptography library required. Install with: pip install cryptography", file=sys.stderr)
    sys.exit(1)


@dataclass
class ValidationRule:
    """Policy validation rule"""
    rule_id: str
    rule_type: str
    description: str
    severity: str
    check: Any


@dataclass
class ValidationViolation:
    """Policy violation"""
    rule_id: str
    severity: str
    message: str
    certificate: str
    details: Dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Validation report"""
    timestamp: str
    policy_file: str
    certificates_checked: int
    violations: List[ValidationViolation]
    warnings: List[str]
    passed: bool


class PolicyValidator:
    """Certificate policy validator"""

    SEVERITY_ERROR = "error"
    SEVERITY_WARNING = "warning"

    def __init__(self, policy_file: str, strict: bool = False, verbose: bool = False):
        self.policy_file = policy_file
        self.strict = strict
        self.verbose = verbose
        self.logger = self._setup_logger()

        self.policy = self._load_policy()
        self.violations: List[ValidationViolation] = []
        self.warnings: List[str] = []

    def _setup_logger(self) -> logging.Logger:
        """Configure logging"""
        logger = logging.getLogger("policy_validator")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _load_policy(self) -> Dict:
        """Load policy from YAML file"""
        try:
            with open(self.policy_file, 'r') as f:
                policy = yaml.safe_load(f)
            self.logger.info(f"Loaded policy from: {self.policy_file}")
            return policy
        except Exception as e:
            self.logger.error(f"Failed to load policy: {e}")
            raise

    def validate_certificate(self, cert_path: str) -> bool:
        """Validate certificate against policy"""
        try:
            cert = self._load_certificate(cert_path)
            self.logger.info(f"Validating: {cert_path}")

            violations_before = len(self.violations)

            self._check_key_type(cert, cert_path)
            self._check_key_size(cert, cert_path)
            self._check_signature_algorithm(cert, cert_path)
            self._check_validity_period(cert, cert_path)
            self._check_required_extensions(cert, cert_path)
            self._check_issuer(cert, cert_path)
            self._check_subject(cert, cert_path)
            self._check_san(cert, cert_path)
            self._check_key_usage(cert, cert_path)
            self._check_extended_key_usage(cert, cert_path)
            self._check_certificate_policies(cert, cert_path)

            violations_found = len(self.violations) - violations_before
            if violations_found == 0:
                self.logger.info(f"✓ Certificate passed all checks: {cert_path}")
                return True
            else:
                self.logger.warning(f"✗ Certificate has {violations_found} violation(s): {cert_path}")
                return False

        except Exception as e:
            self.logger.error(f"Error validating {cert_path}: {e}")
            self.warnings.append(f"Validation error for {cert_path}: {str(e)}")
            return False

    def _load_certificate(self, path: str) -> x509.Certificate:
        """Load certificate from file"""
        with open(path, 'rb') as f:
            data = f.read()
            if b'-----BEGIN CERTIFICATE-----' in data:
                return x509.load_pem_x509_certificate(data, default_backend())
            else:
                return x509.load_der_x509_certificate(data, default_backend())

    def _add_violation(self, rule_id: str, severity: str, message: str, cert_path: str, details: Dict = None):
        """Add validation violation"""
        violation = ValidationViolation(
            rule_id=rule_id,
            severity=severity,
            message=message,
            certificate=cert_path,
            details=details or {}
        )
        self.violations.append(violation)

    def _check_key_type(self, cert: x509.Certificate, cert_path: str):
        """Check key type against policy"""
        allowed_types = self.policy.get('allowed_key_types', ['RSA', 'EC'])

        public_key = cert.public_key()
        if isinstance(public_key, rsa.RSAPublicKey):
            key_type = 'RSA'
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            key_type = 'EC'
        elif isinstance(public_key, dsa.DSAPublicKey):
            key_type = 'DSA'
        else:
            key_type = 'UNKNOWN'

        if key_type not in allowed_types:
            self._add_violation(
                'key_type',
                self.SEVERITY_ERROR,
                f"Key type {key_type} not allowed. Allowed types: {', '.join(allowed_types)}",
                cert_path,
                {'key_type': key_type, 'allowed': allowed_types}
            )

    def _check_key_size(self, cert: x509.Certificate, cert_path: str):
        """Check key size against policy"""
        public_key = cert.public_key()

        if isinstance(public_key, rsa.RSAPublicKey):
            min_size = self.policy.get('min_rsa_key_size', 2048)
            key_size = public_key.key_size
            if key_size < min_size:
                self._add_violation(
                    'key_size',
                    self.SEVERITY_ERROR,
                    f"RSA key size {key_size} below minimum {min_size}",
                    cert_path,
                    {'key_size': key_size, 'min_size': min_size}
                )

        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            min_size = self.policy.get('min_ec_key_size', 256)
            key_size = public_key.curve.key_size
            if key_size < min_size:
                self._add_violation(
                    'key_size',
                    self.SEVERITY_ERROR,
                    f"EC key size {key_size} below minimum {min_size}",
                    cert_path,
                    {'key_size': key_size, 'min_size': min_size}
                )

    def _check_signature_algorithm(self, cert: x509.Certificate, cert_path: str):
        """Check signature algorithm against policy"""
        allowed_algs = self.policy.get('allowed_signature_algorithms', [])
        if not allowed_algs:
            return

        sig_alg = cert.signature_algorithm_oid._name

        if sig_alg not in allowed_algs:
            self._add_violation(
                'signature_algorithm',
                self.SEVERITY_ERROR,
                f"Signature algorithm {sig_alg} not allowed",
                cert_path,
                {'algorithm': sig_alg, 'allowed': allowed_algs}
            )

    def _check_validity_period(self, cert: x509.Certificate, cert_path: str):
        """Check validity period against policy"""
        max_days = self.policy.get('max_validity_days')
        if not max_days:
            return

        validity_period = cert.not_valid_after - cert.not_valid_before
        validity_days = validity_period.days

        if validity_days > max_days:
            severity = self.SEVERITY_ERROR if self.strict else self.SEVERITY_WARNING
            self._add_violation(
                'validity_period',
                severity,
                f"Validity period {validity_days} days exceeds maximum {max_days} days",
                cert_path,
                {'validity_days': validity_days, 'max_days': max_days}
            )

        now = datetime.datetime.utcnow()
        if now < cert.not_valid_before:
            self._add_violation(
                'validity_not_yet',
                self.SEVERITY_WARNING,
                "Certificate not yet valid",
                cert_path,
                {'not_before': cert.not_valid_before.isoformat()}
            )
        elif now > cert.not_valid_after:
            self._add_violation(
                'validity_expired',
                self.SEVERITY_ERROR,
                "Certificate expired",
                cert_path,
                {'not_after': cert.not_valid_after.isoformat()}
            )

    def _check_required_extensions(self, cert: x509.Certificate, cert_path: str):
        """Check required extensions"""
        required = self.policy.get('required_extensions', [])
        if not required:
            return

        extension_oids = {ext.oid._name for ext in cert.extensions}

        for req_ext in required:
            if req_ext not in extension_oids:
                self._add_violation(
                    'required_extension',
                    self.SEVERITY_ERROR,
                    f"Missing required extension: {req_ext}",
                    cert_path,
                    {'extension': req_ext}
                )

    def _check_issuer(self, cert: x509.Certificate, cert_path: str):
        """Check issuer against policy"""
        allowed_issuers = self.policy.get('allowed_issuers', [])
        if not allowed_issuers:
            return

        issuer_str = self._format_name(cert.issuer)

        if not any(allowed in issuer_str for allowed in allowed_issuers):
            self._add_violation(
                'issuer',
                self.SEVERITY_ERROR,
                f"Issuer not in allowed list: {issuer_str}",
                cert_path,
                {'issuer': issuer_str, 'allowed': allowed_issuers}
            )

    def _check_subject(self, cert: x509.Certificate, cert_path: str):
        """Check subject against policy"""
        required_attrs = self.policy.get('required_subject_attributes', [])
        if not required_attrs:
            return

        subject_attrs = {attr.oid._name for attr in cert.subject}

        for req_attr in required_attrs:
            if req_attr not in subject_attrs:
                self._add_violation(
                    'subject_attribute',
                    self.SEVERITY_WARNING,
                    f"Missing subject attribute: {req_attr}",
                    cert_path,
                    {'attribute': req_attr}
                )

    def _check_san(self, cert: x509.Certificate, cert_path: str):
        """Check Subject Alternative Names"""
        try:
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            domains = [name.value for name in san.value if isinstance(name, x509.DNSName)]

            forbidden = self.policy.get('forbidden_domains', [])
            for domain in domains:
                for forbidden_pattern in forbidden:
                    if forbidden_pattern in domain:
                        self._add_violation(
                            'forbidden_domain',
                            self.SEVERITY_ERROR,
                            f"Domain contains forbidden pattern: {domain}",
                            cert_path,
                            {'domain': domain, 'pattern': forbidden_pattern}
                        )

            max_san = self.policy.get('max_san_entries')
            if max_san and len(domains) > max_san:
                self._add_violation(
                    'san_count',
                    self.SEVERITY_WARNING,
                    f"Too many SAN entries: {len(domains)} (max: {max_san})",
                    cert_path,
                    {'count': len(domains), 'max': max_san}
                )

        except x509.ExtensionNotFound:
            if self.policy.get('require_san', True):
                self._add_violation(
                    'missing_san',
                    self.SEVERITY_ERROR,
                    "Missing Subject Alternative Name extension",
                    cert_path
                )

    def _check_key_usage(self, cert: x509.Certificate, cert_path: str):
        """Check Key Usage extension"""
        required_ku = self.policy.get('required_key_usage', [])
        if not required_ku:
            return

        try:
            ku = cert.extensions.get_extension_for_class(x509.KeyUsage)

            ku_map = {
                'digitalSignature': ku.value.digital_signature,
                'keyEncipherment': ku.value.key_encipherment,
                'keyAgreement': ku.value.key_agreement,
                'keyCertSign': ku.value.key_cert_sign,
                'cRLSign': ku.value.crl_sign
            }

            for req_ku in required_ku:
                if req_ku in ku_map and not ku_map[req_ku]:
                    self._add_violation(
                        'key_usage',
                        self.SEVERITY_ERROR,
                        f"Missing required Key Usage: {req_ku}",
                        cert_path,
                        {'key_usage': req_ku}
                    )

        except x509.ExtensionNotFound:
            self._add_violation(
                'missing_key_usage',
                self.SEVERITY_ERROR,
                "Missing Key Usage extension",
                cert_path
            )

    def _check_extended_key_usage(self, cert: x509.Certificate, cert_path: str):
        """Check Extended Key Usage extension"""
        required_eku = self.policy.get('required_extended_key_usage', [])
        if not required_eku:
            return

        try:
            eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
            eku_oids = {oid.dotted_string for oid in eku.value}

            for req_eku in required_eku:
                if req_eku not in eku_oids:
                    self._add_violation(
                        'extended_key_usage',
                        self.SEVERITY_ERROR,
                        f"Missing required Extended Key Usage: {req_eku}",
                        cert_path,
                        {'eku': req_eku}
                    )

        except x509.ExtensionNotFound:
            if required_eku:
                self._add_violation(
                    'missing_extended_key_usage',
                    self.SEVERITY_ERROR,
                    "Missing Extended Key Usage extension",
                    cert_path
                )

    def _check_certificate_policies(self, cert: x509.Certificate, cert_path: str):
        """Check Certificate Policies extension"""
        required_policies = self.policy.get('required_policies', [])
        if not required_policies:
            return

        try:
            policies = cert.extensions.get_extension_for_class(x509.CertificatePolicies)
            policy_oids = {p.policy_identifier.dotted_string for p in policies.value}

            for req_policy in required_policies:
                if req_policy not in policy_oids:
                    self._add_violation(
                        'certificate_policy',
                        self.SEVERITY_ERROR,
                        f"Missing required Certificate Policy: {req_policy}",
                        cert_path,
                        {'policy': req_policy}
                    )

        except x509.ExtensionNotFound:
            if required_policies:
                self._add_violation(
                    'missing_policies',
                    self.SEVERITY_WARNING,
                    "Missing Certificate Policies extension",
                    cert_path
                )

    def _format_name(self, name: x509.Name) -> str:
        """Format X.509 name"""
        parts = []
        for attr in name:
            parts.append(f"{attr.oid._name}={attr.value}")
        return ", ".join(parts)

    def generate_report(self, certificates_checked: int) -> ValidationReport:
        """Generate validation report"""
        passed = len([v for v in self.violations if v.severity == self.SEVERITY_ERROR]) == 0

        return ValidationReport(
            timestamp=datetime.datetime.utcnow().isoformat(),
            policy_file=self.policy_file,
            certificates_checked=certificates_checked,
            violations=self.violations,
            warnings=self.warnings,
            passed=passed
        )


def main():
    parser = argparse.ArgumentParser(
        description="Certificate Policy Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Validate single certificate:
    %(prog)s --cert server.pem --policy policy.yaml

  Strict validation (warnings become errors):
    %(prog)s --cert cert.pem --policy policy.yaml --strict

  Scan directory:
    %(prog)s --scan-dir /etc/ssl/certs --policy policy.yaml

  Generate JSON report:
    %(prog)s --cert cert.pem --policy policy.yaml --report violations.json
        """
    )

    parser.add_argument('--cert', help='Certificate file to validate')
    parser.add_argument('--scan-dir', help='Directory to scan for certificates')
    parser.add_argument('--policy', required=True, help='Policy YAML file')
    parser.add_argument('--strict', action='store_true', help='Strict mode (warnings as errors)')
    parser.add_argument('--report', help='Output JSON report file')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    if not args.cert and not args.scan_dir:
        parser.error("Either --cert or --scan-dir must be specified")

    try:
        validator = PolicyValidator(
            policy_file=args.policy,
            strict=args.strict,
            verbose=args.verbose
        )

        certificates = []
        if args.cert:
            certificates.append(args.cert)
        elif args.scan_dir:
            scan_path = Path(args.scan_dir)
            for pattern in ['*.pem', '*.crt', '*.cer']:
                certificates.extend([str(p) for p in scan_path.glob(pattern)])

        print(f"Validating {len(certificates)} certificate(s) against policy: {args.policy}")

        for cert_path in certificates:
            validator.validate_certificate(cert_path)

        report = validator.generate_report(len(certificates))

        if args.report:
            with open(args.report, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)
            print(f"\nReport saved to: {args.report}")

        print(f"\nValidation Report")
        print(f"=" * 60)
        print(f"Certificates Checked: {report.certificates_checked}")
        print(f"Violations: {len([v for v in report.violations if v.severity == 'error'])}")
        print(f"Warnings: {len([v for v in report.violations if v.severity == 'warning'])}")
        print(f"Status: {'PASSED' if report.passed else 'FAILED'}")

        if report.violations:
            print(f"\nViolations:")
            for v in report.violations:
                print(f"  [{v.severity.upper()}] {v.rule_id}: {v.message}")
                print(f"    Certificate: {v.certificate}")

        return 0 if report.passed else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
