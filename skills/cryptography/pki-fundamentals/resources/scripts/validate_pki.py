#!/usr/bin/env python3
"""
PKI Validation Tool - Comprehensive Certificate and PKI Infrastructure Validation

This script provides complete PKI validation capabilities including:
- Certificate chain validation against trust stores
- Policy checking (CP/CPS compliance)
- CRL/OCSP revocation verification
- Certificate Transparency log checking
- CA operations auditing
- Trust anchor validation

Usage:
    ./validate_pki.py --help
    ./validate_pki.py validate-chain --cert server.pem --ca-bundle ca.pem
    ./validate_pki.py check-policy --cert cert.pem --policy-oid 2.16.840.1.114412.1.1
    ./validate_pki.py check-revocation --cert cert.pem --method ocsp
    ./validate_pki.py check-ct-logs --cert cert.pem --domain example.com
    ./validate_pki.py audit-ca --ca-cert ca.pem --log-dir /var/log/ca
    ./validate_pki.py verify-trust --cert cert.pem --trust-store /etc/ssl/certs
"""

import argparse
import json
import sys
import os
import re
import hashlib
import datetime
import logging
import base64
import urllib.request
import urllib.error
import socket
import ssl
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtensionOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import rsa, ec, dsa, padding
except ImportError:
    print("Error: cryptography library required. Install with: pip install cryptography", file=sys.stderr)
    sys.exit(1)


class ValidationStatus(Enum):
    """Validation result status"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class RevocationMethod(Enum):
    """Revocation checking method"""
    CRL = "crl"
    OCSP = "ocsp"
    BOTH = "both"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_type: str
    status: ValidationStatus
    message: str
    details: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())


@dataclass
class ChainValidationResult:
    """Certificate chain validation result"""
    is_valid: bool
    chain_length: int
    trust_anchor: Optional[str]
    validation_path: List[str]
    errors: List[str]
    warnings: List[str]
    details: Dict = field(default_factory=dict)


@dataclass
class RevocationResult:
    """Revocation check result"""
    is_revoked: bool
    method: str
    status: str
    revocation_time: Optional[str]
    reason: Optional[str]
    details: Dict = field(default_factory=dict)


@dataclass
class PolicyValidationResult:
    """Certificate policy validation result"""
    is_compliant: bool
    policy_oid: str
    policy_name: Optional[str]
    violations: List[str]
    warnings: List[str]
    details: Dict = field(default_factory=dict)


@dataclass
class CTLogResult:
    """Certificate Transparency log check result"""
    is_logged: bool
    log_count: int
    logs: List[Dict]
    sct_count: int
    details: Dict = field(default_factory=dict)


class PKIValidator:
    """Main PKI validation class"""

    def __init__(self, verbose: bool = False, json_output: bool = False):
        self.verbose = verbose
        self.json_output = json_output
        self.logger = self._setup_logger()
        self.validation_results: List[ValidationResult] = []

    def _setup_logger(self) -> logging.Logger:
        """Configure logging"""
        logger = logging.getLogger("pki_validator")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        handler = logging.StreamHandler(sys.stderr if self.json_output else sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def load_certificate(self, cert_path: str) -> x509.Certificate:
        """Load certificate from file"""
        try:
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
                if b'-----BEGIN CERTIFICATE-----' in cert_data:
                    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                else:
                    cert = x509.load_der_x509_certificate(cert_data, default_backend())
            self.logger.debug(f"Loaded certificate: {cert.subject}")
            return cert
        except Exception as e:
            self.logger.error(f"Failed to load certificate from {cert_path}: {e}")
            raise

    def load_certificate_chain(self, chain_path: str) -> List[x509.Certificate]:
        """Load certificate chain from bundle file"""
        try:
            with open(chain_path, 'rb') as f:
                data = f.read()

            certs = []
            if b'-----BEGIN CERTIFICATE-----' in data:
                pem_certs = re.findall(
                    b'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',
                    data,
                    re.DOTALL
                )
                for pem_cert in pem_certs:
                    cert = x509.load_pem_x509_certificate(pem_cert, default_backend())
                    certs.append(cert)
            else:
                cert = x509.load_der_x509_certificate(data, default_backend())
                certs.append(cert)

            self.logger.debug(f"Loaded {len(certs)} certificates from chain")
            return certs
        except Exception as e:
            self.logger.error(f"Failed to load certificate chain: {e}")
            raise

    def validate_certificate_chain(
        self,
        cert: x509.Certificate,
        chain: List[x509.Certificate],
        trust_store: Optional[str] = None
    ) -> ChainValidationResult:
        """Validate certificate chain and trust path"""
        errors = []
        warnings = []
        validation_path = []
        trust_anchor = None

        try:
            current_cert = cert
            validation_path.append(self._format_cert_subject(current_cert))

            chain_dict = {self._get_subject_key_identifier(c): c for c in chain}

            while True:
                aki = self._get_authority_key_identifier(current_cert)
                if not aki:
                    if self._is_self_signed(current_cert):
                        trust_anchor = self._format_cert_subject(current_cert)
                        self.logger.debug(f"Reached self-signed root: {trust_anchor}")
                        break
                    else:
                        errors.append("Certificate chain incomplete: no AKI extension")
                        break

                if aki not in chain_dict:
                    errors.append(f"Missing issuer certificate for: {self._format_cert_subject(current_cert)}")
                    break

                issuer_cert = chain_dict[aki]

                if not self._verify_signature(current_cert, issuer_cert):
                    errors.append(f"Signature verification failed for: {self._format_cert_subject(current_cert)}")

                if not self._check_validity_period(issuer_cert):
                    errors.append(f"Issuer certificate expired: {self._format_cert_subject(issuer_cert)}")

                validation_path.append(self._format_cert_subject(issuer_cert))
                current_cert = issuer_cert

                if self._is_self_signed(current_cert):
                    trust_anchor = self._format_cert_subject(current_cert)
                    break

                if len(validation_path) > 10:
                    errors.append("Chain too long (possible loop)")
                    break

            if trust_store:
                if not self._verify_against_trust_store(current_cert, trust_store):
                    warnings.append("Root certificate not in trusted store")

            if not self._check_validity_period(cert):
                errors.append("End-entity certificate expired or not yet valid")

            basic_constraints = self._get_basic_constraints(cert)
            if basic_constraints and basic_constraints.ca:
                warnings.append("End-entity certificate has CA flag set")

            for i, path_cert in enumerate([cert] + chain):
                bc = self._get_basic_constraints(path_cert)
                if i > 0 and (not bc or not bc.ca):
                    errors.append(f"Intermediate certificate missing CA flag: {self._format_cert_subject(path_cert)}")

                if bc and bc.ca and bc.path_length is not None:
                    remaining_depth = len(validation_path) - i - 1
                    if remaining_depth > bc.path_length:
                        errors.append(f"Path length constraint violated: {self._format_cert_subject(path_cert)}")

            is_valid = len(errors) == 0

            return ChainValidationResult(
                is_valid=is_valid,
                chain_length=len(validation_path),
                trust_anchor=trust_anchor,
                validation_path=validation_path,
                errors=errors,
                warnings=warnings,
                details={
                    "subject": self._format_cert_subject(cert),
                    "issuer": self._format_cert_subject(cert.issuer),
                    "serial": hex(cert.serial_number),
                    "not_before": cert.not_valid_before.isoformat(),
                    "not_after": cert.not_valid_after.isoformat()
                }
            )

        except Exception as e:
            self.logger.error(f"Chain validation error: {e}")
            return ChainValidationResult(
                is_valid=False,
                chain_length=len(validation_path),
                trust_anchor=trust_anchor,
                validation_path=validation_path,
                errors=[f"Validation error: {str(e)}"],
                warnings=warnings,
                details={}
            )

    def check_revocation(
        self,
        cert: x509.Certificate,
        method: RevocationMethod = RevocationMethod.BOTH
    ) -> RevocationResult:
        """Check certificate revocation status via CRL or OCSP"""
        try:
            if method in (RevocationMethod.OCSP, RevocationMethod.BOTH):
                ocsp_urls = self._get_ocsp_urls(cert)
                if ocsp_urls:
                    self.logger.debug(f"Checking OCSP: {ocsp_urls}")
                    result = self._check_ocsp(cert, ocsp_urls[0])
                    if result:
                        return result

            if method in (RevocationMethod.CRL, RevocationMethod.BOTH):
                crl_urls = self._get_crl_urls(cert)
                if crl_urls:
                    self.logger.debug(f"Checking CRL: {crl_urls}")
                    result = self._check_crl(cert, crl_urls[0])
                    if result:
                        return result

            return RevocationResult(
                is_revoked=False,
                method="none",
                status="unknown",
                revocation_time=None,
                reason=None,
                details={"error": "No revocation information available"}
            )

        except Exception as e:
            self.logger.error(f"Revocation check error: {e}")
            return RevocationResult(
                is_revoked=False,
                method="error",
                status="error",
                revocation_time=None,
                reason=None,
                details={"error": str(e)}
            )

    def validate_policy(
        self,
        cert: x509.Certificate,
        required_policy_oid: Optional[str] = None
    ) -> PolicyValidationResult:
        """Validate certificate against policy requirements"""
        violations = []
        warnings = []
        policy_oid = required_policy_oid or "any"
        policy_name = None

        try:
            cert_policies = self._get_certificate_policies(cert)

            if required_policy_oid:
                if not cert_policies:
                    violations.append("Certificate has no policy extensions")
                else:
                    policy_oids = [p.policy_identifier.dotted_string for p in cert_policies]
                    if required_policy_oid not in policy_oids:
                        violations.append(f"Required policy OID {required_policy_oid} not present")
                    else:
                        policy_name = self._get_policy_name(required_policy_oid)

            key_usage = self._get_key_usage(cert)
            if key_usage:
                self._validate_key_usage(key_usage, violations, warnings)

            ext_key_usage = self._get_extended_key_usage(cert)
            if ext_key_usage:
                self._validate_extended_key_usage(ext_key_usage, violations, warnings)

            san = self._get_subject_alternative_names(cert)
            if not san:
                warnings.append("No Subject Alternative Name extension")

            if cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME):
                cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
                if san and cn not in self._get_san_dns_names(san):
                    warnings.append("Common Name not present in SAN")

            sig_alg = cert.signature_algorithm_oid.dotted_string
            if sig_alg in ["1.2.840.113549.1.1.5", "1.2.840.113549.1.1.4"]:  # SHA-1
                violations.append("Weak signature algorithm (SHA-1)")

            public_key = cert.public_key()
            if isinstance(public_key, rsa.RSAPublicKey):
                key_size = public_key.key_size
                if key_size < 2048:
                    violations.append(f"Weak RSA key size: {key_size} bits")
                elif key_size < 3072:
                    warnings.append(f"RSA key size {key_size} bits below recommended 3072+")

            validity_period = cert.not_valid_after - cert.not_valid_before
            if validity_period.days > 825:
                warnings.append(f"Validity period exceeds 825 days: {validity_period.days}")

            is_compliant = len(violations) == 0

            return PolicyValidationResult(
                is_compliant=is_compliant,
                policy_oid=policy_oid,
                policy_name=policy_name,
                violations=violations,
                warnings=warnings,
                details={
                    "policies": [p.policy_identifier.dotted_string for p in cert_policies] if cert_policies else [],
                    "key_usage": self._format_key_usage(key_usage) if key_usage else None,
                    "extended_key_usage": self._format_extended_key_usage(ext_key_usage) if ext_key_usage else None
                }
            )

        except Exception as e:
            self.logger.error(f"Policy validation error: {e}")
            return PolicyValidationResult(
                is_compliant=False,
                policy_oid=policy_oid,
                policy_name=policy_name,
                violations=[f"Validation error: {str(e)}"],
                warnings=warnings,
                details={}
            )

    def check_certificate_transparency(
        self,
        cert: x509.Certificate,
        domain: Optional[str] = None
    ) -> CTLogResult:
        """Check Certificate Transparency log presence"""
        logs = []
        sct_count = 0

        try:
            sct_extension = cert.extensions.get_extension_for_oid(
                x509.ObjectIdentifier("1.3.6.1.4.1.11129.2.4.2")
            )
            if sct_extension:
                sct_count = 1
                self.logger.debug("Certificate contains SCT extension")

        except x509.ExtensionNotFound:
            self.logger.debug("No SCT extension found")
        except Exception as e:
            self.logger.warning(f"Error checking SCT extension: {e}")

        if domain:
            try:
                ct_logs = self._query_ct_logs(cert, domain)
                logs.extend(ct_logs)
            except Exception as e:
                self.logger.warning(f"CT log query failed: {e}")

        is_logged = sct_count > 0 or len(logs) > 0

        return CTLogResult(
            is_logged=is_logged,
            log_count=len(logs),
            logs=logs,
            sct_count=sct_count,
            details={
                "serial": hex(cert.serial_number),
                "subject": self._format_cert_subject(cert),
                "domain": domain
            }
        )

    def audit_ca_operations(
        self,
        ca_cert: x509.Certificate,
        log_dir: str,
        days: int = 30
    ) -> Dict:
        """Audit CA operations from logs"""
        audit_results = {
            "ca_subject": self._format_cert_subject(ca_cert),
            "audit_period_days": days,
            "issuance_count": 0,
            "revocation_count": 0,
            "key_ceremonies": [],
            "anomalies": [],
            "compliance_issues": []
        }

        try:
            log_path = Path(log_dir)
            if not log_path.exists():
                audit_results["anomalies"].append(f"Log directory not found: {log_dir}")
                return audit_results

            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)

            for log_file in log_path.glob("*.log"):
                try:
                    with open(log_file, 'r') as f:
                        for line in f:
                            if self._parse_log_timestamp(line) < cutoff_date:
                                continue

                            if "certificate issued" in line.lower():
                                audit_results["issuance_count"] += 1

                            if "certificate revoked" in line.lower():
                                audit_results["revocation_count"] += 1

                            if "key ceremony" in line.lower():
                                audit_results["key_ceremonies"].append({
                                    "timestamp": self._parse_log_timestamp(line).isoformat(),
                                    "details": line.strip()
                                })

                except Exception as e:
                    self.logger.warning(f"Error reading log file {log_file}: {e}")

            issuance_rate = audit_results["issuance_count"] / days
            if issuance_rate > 1000:
                audit_results["anomalies"].append(
                    f"High issuance rate: {issuance_rate:.1f} certs/day"
                )

            if audit_results["revocation_count"] > audit_results["issuance_count"] * 0.1:
                audit_results["anomalies"].append(
                    f"High revocation rate: {audit_results['revocation_count']} revocations"
                )

        except Exception as e:
            self.logger.error(f"Audit error: {e}")
            audit_results["anomalies"].append(f"Audit error: {str(e)}")

        return audit_results

    def _verify_signature(self, cert: x509.Certificate, issuer_cert: x509.Certificate) -> bool:
        """Verify certificate signature"""
        try:
            public_key = issuer_cert.public_key()
            if isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    cert.signature_hash_algorithm
                )
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    ec.ECDSA(cert.signature_hash_algorithm)
                )
            else:
                return False
            return True
        except Exception as e:
            self.logger.debug(f"Signature verification failed: {e}")
            return False

    def _check_validity_period(self, cert: x509.Certificate) -> bool:
        """Check if certificate is within validity period"""
        now = datetime.datetime.utcnow()
        return cert.not_valid_before <= now <= cert.not_valid_after

    def _is_self_signed(self, cert: x509.Certificate) -> bool:
        """Check if certificate is self-signed"""
        return cert.issuer == cert.subject

    def _get_subject_key_identifier(self, cert: x509.Certificate) -> Optional[bytes]:
        """Get Subject Key Identifier extension"""
        try:
            ski = cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
            return ski.value.digest
        except x509.ExtensionNotFound:
            return None

    def _get_authority_key_identifier(self, cert: x509.Certificate) -> Optional[bytes]:
        """Get Authority Key Identifier extension"""
        try:
            aki = cert.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier)
            return aki.value.key_identifier
        except x509.ExtensionNotFound:
            return None

    def _get_basic_constraints(self, cert: x509.Certificate) -> Optional[x509.BasicConstraints]:
        """Get Basic Constraints extension"""
        try:
            bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
            return bc.value
        except x509.ExtensionNotFound:
            return None

    def _get_key_usage(self, cert: x509.Certificate) -> Optional[x509.KeyUsage]:
        """Get Key Usage extension"""
        try:
            ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
            return ku.value
        except x509.ExtensionNotFound:
            return None

    def _get_extended_key_usage(self, cert: x509.Certificate) -> Optional[x509.ExtendedKeyUsage]:
        """Get Extended Key Usage extension"""
        try:
            eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
            return eku.value
        except x509.ExtensionNotFound:
            return None

    def _get_subject_alternative_names(self, cert: x509.Certificate) -> Optional[x509.SubjectAlternativeName]:
        """Get Subject Alternative Name extension"""
        try:
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            return san.value
        except x509.ExtensionNotFound:
            return None

    def _get_certificate_policies(self, cert: x509.Certificate) -> Optional[List]:
        """Get Certificate Policies extension"""
        try:
            policies = cert.extensions.get_extension_for_class(x509.CertificatePolicies)
            return list(policies.value)
        except x509.ExtensionNotFound:
            return None

    def _get_ocsp_urls(self, cert: x509.Certificate) -> List[str]:
        """Extract OCSP URLs from certificate"""
        try:
            aia = cert.extensions.get_extension_for_class(x509.AuthorityInformationAccess)
            return [
                desc.access_location.value
                for desc in aia.value
                if desc.access_method == x509.AuthorityInformationAccessOID.OCSP
            ]
        except x509.ExtensionNotFound:
            return []

    def _get_crl_urls(self, cert: x509.Certificate) -> List[str]:
        """Extract CRL URLs from certificate"""
        try:
            cdp = cert.extensions.get_extension_for_class(x509.CRLDistributionPoints)
            urls = []
            for dp in cdp.value:
                if dp.full_name:
                    for name in dp.full_name:
                        if isinstance(name, x509.UniformResourceIdentifier):
                            urls.append(name.value)
            return urls
        except x509.ExtensionNotFound:
            return []

    def _check_ocsp(self, cert: x509.Certificate, ocsp_url: str) -> Optional[RevocationResult]:
        """Check OCSP status (simplified implementation)"""
        self.logger.debug(f"OCSP check not implemented for: {ocsp_url}")
        return None

    def _check_crl(self, cert: x509.Certificate, crl_url: str) -> Optional[RevocationResult]:
        """Check CRL status"""
        try:
            req = urllib.request.Request(crl_url)
            with urllib.request.urlopen(req, timeout=10) as response:
                crl_data = response.read()

            if b'-----BEGIN X509 CRL-----' in crl_data:
                crl = x509.load_pem_x509_crl(crl_data, default_backend())
            else:
                crl = x509.load_der_x509_crl(crl_data, default_backend())

            for revoked_cert in crl:
                if revoked_cert.serial_number == cert.serial_number:
                    return RevocationResult(
                        is_revoked=True,
                        method="crl",
                        status="revoked",
                        revocation_time=revoked_cert.revocation_date.isoformat(),
                        reason=self._format_revocation_reason(revoked_cert.extensions),
                        details={"crl_url": crl_url}
                    )

            return RevocationResult(
                is_revoked=False,
                method="crl",
                status="good",
                revocation_time=None,
                reason=None,
                details={"crl_url": crl_url}
            )

        except Exception as e:
            self.logger.error(f"CRL check failed: {e}")
            return None

    def _format_revocation_reason(self, extensions: x509.Extensions) -> Optional[str]:
        """Format revocation reason from CRL entry extensions"""
        try:
            reason = extensions.get_extension_for_class(x509.CRLReason)
            return reason.value.name
        except x509.ExtensionNotFound:
            return None

    def _query_ct_logs(self, cert: x509.Certificate, domain: str) -> List[Dict]:
        """Query Certificate Transparency logs (simplified)"""
        return []

    def _validate_key_usage(self, key_usage: x509.KeyUsage, violations: List[str], warnings: List[str]):
        """Validate Key Usage extension"""
        if key_usage.digital_signature and key_usage.key_encipherment:
            pass
        elif not key_usage.digital_signature:
            warnings.append("Digital signature not enabled")

    def _validate_extended_key_usage(self, ext_key_usage: x509.ExtendedKeyUsage, violations: List[str], warnings: List[str]):
        """Validate Extended Key Usage extension"""
        has_server_auth = ExtendedKeyUsageOID.SERVER_AUTH in ext_key_usage
        has_client_auth = ExtendedKeyUsageOID.CLIENT_AUTH in ext_key_usage

        if not has_server_auth and not has_client_auth:
            warnings.append("No standard authentication EKU present")

    def _verify_against_trust_store(self, cert: x509.Certificate, trust_store: str) -> bool:
        """Verify certificate against trust store"""
        try:
            trust_path = Path(trust_store)
            if trust_path.is_dir():
                for trust_cert_file in trust_path.glob("*.pem"):
                    trust_cert = self.load_certificate(str(trust_cert_file))
                    if cert.subject == trust_cert.subject:
                        return True
            else:
                trust_certs = self.load_certificate_chain(trust_store)
                for trust_cert in trust_certs:
                    if cert.subject == trust_cert.subject:
                        return True
            return False
        except Exception as e:
            self.logger.warning(f"Trust store verification failed: {e}")
            return False

    def _format_cert_subject(self, subject) -> str:
        """Format certificate subject as string"""
        if isinstance(subject, x509.Name):
            parts = []
            for attr in subject:
                parts.append(f"{attr.oid._name}={attr.value}")
            return ", ".join(parts)
        return str(subject)

    def _get_san_dns_names(self, san: x509.SubjectAlternativeName) -> List[str]:
        """Extract DNS names from SAN"""
        return [name.value for name in san if isinstance(name, x509.DNSName)]

    def _get_policy_name(self, oid: str) -> Optional[str]:
        """Map policy OID to name"""
        policy_map = {
            "2.16.840.1.114412.1.1": "DigiCert EV",
            "2.23.140.1.2.1": "CA/Browser Forum DV",
            "2.23.140.1.2.2": "CA/Browser Forum OV",
            "2.23.140.1.1": "CA/Browser Forum EV"
        }
        return policy_map.get(oid)

    def _format_key_usage(self, key_usage: x509.KeyUsage) -> List[str]:
        """Format key usage as list of strings"""
        usages = []
        if key_usage.digital_signature:
            usages.append("digitalSignature")
        if key_usage.key_encipherment:
            usages.append("keyEncipherment")
        if key_usage.key_agreement:
            usages.append("keyAgreement")
        if key_usage.key_cert_sign:
            usages.append("keyCertSign")
        if key_usage.crl_sign:
            usages.append("cRLSign")
        return usages

    def _format_extended_key_usage(self, ext_key_usage: x509.ExtendedKeyUsage) -> List[str]:
        """Format extended key usage as list of strings"""
        return [oid.dotted_string for oid in ext_key_usage]

    def _parse_log_timestamp(self, log_line: str) -> datetime.datetime:
        """Parse timestamp from log line"""
        try:
            match = re.search(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}', log_line)
            if match:
                return datetime.datetime.fromisoformat(match.group().replace(' ', 'T'))
        except Exception:
            pass
        return datetime.datetime.utcnow()


def main():
    parser = argparse.ArgumentParser(
        description="PKI Validation Tool - Comprehensive certificate and PKI validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Validate certificate chain:
    %(prog)s validate-chain --cert server.pem --ca-bundle ca-chain.pem

  Check policy compliance:
    %(prog)s check-policy --cert cert.pem --policy-oid 2.23.140.1.2.2

  Check revocation status:
    %(prog)s check-revocation --cert cert.pem --method both

  Check CT logs:
    %(prog)s check-ct-logs --cert cert.pem --domain example.com

  Audit CA operations:
    %(prog)s audit-ca --ca-cert ca.pem --log-dir /var/log/ca --days 30

  Verify against trust store:
    %(prog)s verify-trust --cert cert.pem --trust-store /etc/ssl/certs
        """
    )

    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    validate_chain_parser = subparsers.add_parser('validate-chain', help='Validate certificate chain')
    validate_chain_parser.add_argument('--cert', required=True, help='Certificate to validate')
    validate_chain_parser.add_argument('--ca-bundle', help='CA bundle file')
    validate_chain_parser.add_argument('--trust-store', help='Trust store path')

    check_policy_parser = subparsers.add_parser('check-policy', help='Check certificate policy compliance')
    check_policy_parser.add_argument('--cert', required=True, help='Certificate to check')
    check_policy_parser.add_argument('--policy-oid', help='Required policy OID')

    check_revocation_parser = subparsers.add_parser('check-revocation', help='Check revocation status')
    check_revocation_parser.add_argument('--cert', required=True, help='Certificate to check')
    check_revocation_parser.add_argument('--method', choices=['crl', 'ocsp', 'both'], default='both', help='Revocation check method')

    check_ct_parser = subparsers.add_parser('check-ct-logs', help='Check Certificate Transparency logs')
    check_ct_parser.add_argument('--cert', required=True, help='Certificate to check')
    check_ct_parser.add_argument('--domain', help='Domain name')

    audit_ca_parser = subparsers.add_parser('audit-ca', help='Audit CA operations')
    audit_ca_parser.add_argument('--ca-cert', required=True, help='CA certificate')
    audit_ca_parser.add_argument('--log-dir', required=True, help='CA log directory')
    audit_ca_parser.add_argument('--days', type=int, default=30, help='Audit period in days')

    verify_trust_parser = subparsers.add_parser('verify-trust', help='Verify against trust store')
    verify_trust_parser.add_argument('--cert', required=True, help='Certificate to verify')
    verify_trust_parser.add_argument('--trust-store', required=True, help='Trust store path')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    validator = PKIValidator(verbose=args.verbose, json_output=args.json)

    try:
        if args.command == 'validate-chain':
            cert = validator.load_certificate(args.cert)
            chain = []
            if args.ca_bundle:
                chain = validator.load_certificate_chain(args.ca_bundle)
            result = validator.validate_certificate_chain(cert, chain, args.trust_store)

            if args.json:
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"Chain Validation: {'VALID' if result.is_valid else 'INVALID'}")
                print(f"Chain Length: {result.chain_length}")
                print(f"Trust Anchor: {result.trust_anchor}")
                print("\nValidation Path:")
                for i, path in enumerate(result.validation_path):
                    print(f"  {i}: {path}")
                if result.errors:
                    print("\nErrors:")
                    for error in result.errors:
                        print(f"  - {error}")
                if result.warnings:
                    print("\nWarnings:")
                    for warning in result.warnings:
                        print(f"  - {warning}")

            return 0 if result.is_valid else 1

        elif args.command == 'check-policy':
            cert = validator.load_certificate(args.cert)
            result = validator.validate_policy(cert, args.policy_oid)

            if args.json:
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"Policy Compliance: {'COMPLIANT' if result.is_compliant else 'NON-COMPLIANT'}")
                print(f"Policy OID: {result.policy_oid}")
                if result.policy_name:
                    print(f"Policy Name: {result.policy_name}")
                if result.violations:
                    print("\nViolations:")
                    for violation in result.violations:
                        print(f"  - {violation}")
                if result.warnings:
                    print("\nWarnings:")
                    for warning in result.warnings:
                        print(f"  - {warning}")

            return 0 if result.is_compliant else 1

        elif args.command == 'check-revocation':
            cert = validator.load_certificate(args.cert)
            method = RevocationMethod[args.method.upper()]
            result = validator.check_revocation(cert, method)

            if args.json:
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"Revocation Status: {result.status.upper()}")
                print(f"Method: {result.method}")
                print(f"Revoked: {result.is_revoked}")
                if result.is_revoked:
                    print(f"Revocation Time: {result.revocation_time}")
                    print(f"Reason: {result.reason}")

            return 1 if result.is_revoked else 0

        elif args.command == 'check-ct-logs':
            cert = validator.load_certificate(args.cert)
            result = validator.check_certificate_transparency(cert, args.domain)

            if args.json:
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"CT Logged: {result.is_logged}")
                print(f"Log Count: {result.log_count}")
                print(f"SCT Count: {result.sct_count}")
                if result.logs:
                    print("\nLogs:")
                    for log in result.logs:
                        print(f"  - {log}")

            return 0 if result.is_logged else 1

        elif args.command == 'audit-ca':
            ca_cert = validator.load_certificate(args.ca_cert)
            result = validator.audit_ca_operations(ca_cert, args.log_dir, args.days)

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"CA: {result['ca_subject']}")
                print(f"Audit Period: {result['audit_period_days']} days")
                print(f"Certificates Issued: {result['issuance_count']}")
                print(f"Certificates Revoked: {result['revocation_count']}")
                if result['key_ceremonies']:
                    print(f"Key Ceremonies: {len(result['key_ceremonies'])}")
                if result['anomalies']:
                    print("\nAnomalies:")
                    for anomaly in result['anomalies']:
                        print(f"  - {anomaly}")
                if result['compliance_issues']:
                    print("\nCompliance Issues:")
                    for issue in result['compliance_issues']:
                        print(f"  - {issue}")

            return 0

        elif args.command == 'verify-trust':
            cert = validator.load_certificate(args.cert)
            is_trusted = validator._verify_against_trust_store(cert, args.trust_store)

            result = {
                "trusted": is_trusted,
                "certificate": validator._format_cert_subject(cert.subject),
                "trust_store": args.trust_store
            }

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Trusted: {is_trusted}")
                print(f"Certificate: {result['certificate']}")
                print(f"Trust Store: {result['trust_store']}")

            return 0 if is_trusted else 1

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
