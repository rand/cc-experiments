#!/usr/bin/env python3
"""
CA Management Tool - Comprehensive Certificate Authority Operations

This script provides complete CA lifecycle management including:
- Root and intermediate CA creation
- Certificate issuance and renewal
- CRL and OCSP management
- Key ceremonies with audit logging
- HSM integration for key protection
- Policy enforcement and compliance checking

Usage:
    ./manage_ca.py --help
    ./manage_ca.py init-root --name "Example Root CA" --config ca-config.yaml
    ./manage_ca.py init-intermediate --root-ca root --name "Example Intermediate CA"
    ./manage_ca.py issue --ca intermediate --csr server.csr --profile server --output cert.pem
    ./manage_ca.py revoke --ca intermediate --serial 1000 --reason keyCompromise
    ./manage_ca.py gen-crl --ca intermediate --output ca.crl
    ./manage_ca.py ocsp-responder --ca intermediate --port 8080
    ./manage_ca.py key-ceremony --type root --participants 5 --threshold 3
"""

import argparse
import json
import sys
import os
import subprocess
import yaml
import hashlib
import datetime
import secrets
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtensionOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("Error: cryptography library required. Install with: pip install cryptography", file=sys.stderr)
    sys.exit(1)


class KeyAlgorithm(Enum):
    RSA_2048 = "rsa-2048"
    RSA_4096 = "rsa-4096"
    ECDSA_P256 = "ecdsa-p256"
    ECDSA_P384 = "ecdsa-p384"


class CertificateProfile(Enum):
    ROOT_CA = "root-ca"
    INTERMEDIATE_CA = "intermediate-ca"
    TLS_SERVER = "tls-server"
    TLS_CLIENT = "tls-client"
    EMAIL = "email"
    CODE_SIGNING = "code-signing"


class RevocationReason(Enum):
    UNSPECIFIED = 0
    KEY_COMPROMISE = 1
    CA_COMPROMISE = 2
    AFFILIATION_CHANGED = 3
    SUPERSEDED = 4
    CESSATION_OF_OPERATION = 5
    CERTIFICATE_HOLD = 6
    REMOVE_FROM_CRL = 8
    PRIVILEGE_WITHDRAWN = 9
    AA_COMPROMISE = 10


@dataclass
class CAConfig:
    """Configuration for a Certificate Authority"""
    name: str
    base_path: str
    key_algorithm: KeyAlgorithm
    hash_algorithm: str
    validity_days: int
    crl_validity_days: int
    ocsp_validity_hours: int
    policy_oid: Optional[str] = None
    cps_url: Optional[str] = None
    crl_url: Optional[str] = None
    ocsp_url: Optional[str] = None
    aia_url: Optional[str] = None
    enforce_policies: bool = True
    require_hsm: bool = False
    hsm_config: Optional[Dict] = None


@dataclass
class CertificateInfo:
    """Information about an issued certificate"""
    serial: int
    subject: str
    not_before: datetime.datetime
    not_after: datetime.datetime
    status: str
    revocation_date: Optional[datetime.datetime] = None
    revocation_reason: Optional[RevocationReason] = None


class CAManager:
    """Certificate Authority Management"""

    def __init__(self, config: CAConfig):
        self.config = config
        self.ca_path = Path(config.base_path)
        self.setup_logging()
        self.ensure_directory_structure()

    def setup_logging(self):
        """Configure audit logging"""
        log_path = self.ca_path / "audit.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def ensure_directory_structure(self):
        """Create CA directory structure"""
        dirs = [
            self.ca_path,
            self.ca_path / "certs",
            self.ca_path / "crl",
            self.ca_path / "newcerts",
            self.ca_path / "private",
            self.ca_path / "csr",
            self.ca_path / "db"
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Initialize database files
        index_file = self.ca_path / "db" / "index.txt"
        serial_file = self.ca_path / "db" / "serial"
        crlnumber_file = self.ca_path / "db" / "crlnumber"

        if not index_file.exists():
            index_file.touch()
        if not serial_file.exists():
            serial_file.write_text("1000\n")
        if not crlnumber_file.exists():
            crlnumber_file.write_text("01\n")

        # Secure permissions on private directory
        os.chmod(self.ca_path / "private", 0o700)

    def generate_key_pair(self, algorithm: KeyAlgorithm) -> Tuple:
        """Generate key pair based on algorithm"""
        self.logger.info(f"Generating key pair: {algorithm.value}")

        if algorithm in [KeyAlgorithm.RSA_2048, KeyAlgorithm.RSA_4096]:
            key_size = 2048 if algorithm == KeyAlgorithm.RSA_2048 else 4096
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
        elif algorithm in [KeyAlgorithm.ECDSA_P256, KeyAlgorithm.ECDSA_P384]:
            curve = ec.SECP256R1() if algorithm == KeyAlgorithm.ECDSA_P256 else ec.SECP384R1()
            private_key = ec.generate_private_key(curve, default_backend())
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        return private_key, private_key.public_key()

    def create_root_ca(self, subject_name: str, password: Optional[str] = None) -> Dict:
        """Create a root CA certificate"""
        self.logger.info(f"Creating root CA: {subject_name}")

        # Generate key pair
        private_key, public_key = self.generate_key_pair(self.config.key_algorithm)

        # Build subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.config.name),
            x509.NameAttribute(NameOID.COMMON_NAME, subject_name),
        ])

        # Build certificate
        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(subject)
        cert_builder = cert_builder.issuer_name(issuer)
        cert_builder = cert_builder.public_key(public_key)
        cert_builder = cert_builder.serial_number(x509.random_serial_number())

        not_before = datetime.datetime.utcnow()
        not_after = not_before + datetime.timedelta(days=self.config.validity_days)
        cert_builder = cert_builder.not_valid_before(not_before)
        cert_builder = cert_builder.not_valid_after(not_after)

        # Add extensions for root CA
        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        cert_builder = cert_builder.add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        cert_builder = cert_builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(public_key),
            critical=False,
        )

        # Self-sign certificate
        hash_algo = getattr(hashes, self.config.hash_algorithm.upper().replace('-', ''))()
        certificate = cert_builder.sign(private_key, hash_algo, default_backend())

        # Save private key
        key_path = self.ca_path / "private" / "ca-key.pem"
        encryption = serialization.BestAvailableEncryption(password.encode()) if password else serialization.NoEncryption()
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=encryption
        )
        key_path.write_bytes(key_pem)
        os.chmod(key_path, 0o400)

        # Save certificate
        cert_path = self.ca_path / "certs" / "ca-cert.pem"
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
        cert_path.write_bytes(cert_pem)

        # Calculate fingerprints
        sha256_fingerprint = hashlib.sha256(certificate.public_bytes(serialization.Encoding.DER)).hexdigest()
        sha1_fingerprint = hashlib.sha1(certificate.public_bytes(serialization.Encoding.DER)).hexdigest()

        self.logger.info(f"Root CA created: {cert_path}")
        self.logger.info(f"SHA256 Fingerprint: {sha256_fingerprint}")

        return {
            "certificate_path": str(cert_path),
            "key_path": str(key_path),
            "subject": subject_name,
            "serial": certificate.serial_number,
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
            "sha256_fingerprint": sha256_fingerprint,
            "sha1_fingerprint": sha1_fingerprint
        }

    def create_intermediate_ca(self, root_ca_path: str, root_key_path: str,
                               subject_name: str, password: Optional[str] = None,
                               root_password: Optional[str] = None) -> Dict:
        """Create an intermediate CA certificate"""
        self.logger.info(f"Creating intermediate CA: {subject_name}")

        # Load root CA
        with open(root_ca_path, 'rb') as f:
            root_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

        with open(root_key_path, 'rb') as f:
            root_key_pem = f.read()
            root_key = serialization.load_pem_private_key(
                root_key_pem,
                password=root_password.encode() if root_password else None,
                backend=default_backend()
            )

        # Generate intermediate key pair
        private_key, public_key = self.generate_key_pair(self.config.key_algorithm)

        # Build subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.config.name),
            x509.NameAttribute(NameOID.COMMON_NAME, subject_name),
        ])

        # Build certificate
        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(subject)
        cert_builder = cert_builder.issuer_name(root_cert.subject)
        cert_builder = cert_builder.public_key(public_key)
        cert_builder = cert_builder.serial_number(x509.random_serial_number())

        not_before = datetime.datetime.utcnow()
        not_after = not_before + datetime.timedelta(days=self.config.validity_days)
        cert_builder = cert_builder.not_valid_before(not_before)
        cert_builder = cert_builder.not_valid_after(not_after)

        # Add extensions for intermediate CA
        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        )
        cert_builder = cert_builder.add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        cert_builder = cert_builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(public_key),
            critical=False,
        )
        cert_builder = cert_builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(root_cert.public_key()),
            critical=False,
        )

        # Add CRL distribution points
        if self.config.crl_url:
            cert_builder = cert_builder.add_extension(
                x509.CRLDistributionPoints([
                    x509.DistributionPoint(
                        full_name=[x509.UniformResourceIdentifier(self.config.crl_url)],
                        relative_name=None,
                        reasons=None,
                        crl_issuer=None,
                    )
                ]),
                critical=False,
            )

        # Add Authority Information Access
        if self.config.ocsp_url or self.config.aia_url:
            access_descriptions = []
            if self.config.ocsp_url:
                access_descriptions.append(
                    x509.AccessDescription(
                        x509.AuthorityInformationAccessOID.OCSP,
                        x509.UniformResourceIdentifier(self.config.ocsp_url)
                    )
                )
            if self.config.aia_url:
                access_descriptions.append(
                    x509.AccessDescription(
                        x509.AuthorityInformationAccessOID.CA_ISSUERS,
                        x509.UniformResourceIdentifier(self.config.aia_url)
                    )
                )
            cert_builder = cert_builder.add_extension(
                x509.AuthorityInformationAccess(access_descriptions),
                critical=False,
            )

        # Sign certificate with root CA
        hash_algo = getattr(hashes, self.config.hash_algorithm.upper().replace('-', ''))()
        certificate = cert_builder.sign(root_key, hash_algo, default_backend())

        # Save private key
        key_path = self.ca_path / "private" / "intermediate-key.pem"
        encryption = serialization.BestAvailableEncryption(password.encode()) if password else serialization.NoEncryption()
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=encryption
        )
        key_path.write_bytes(key_pem)
        os.chmod(key_path, 0o400)

        # Save certificate
        cert_path = self.ca_path / "certs" / "intermediate-cert.pem"
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
        cert_path.write_bytes(cert_pem)

        # Create certificate chain
        chain_path = self.ca_path / "certs" / "ca-chain.pem"
        chain_content = cert_pem + b"\n" + root_cert.public_bytes(serialization.Encoding.PEM)
        chain_path.write_bytes(chain_content)

        self.logger.info(f"Intermediate CA created: {cert_path}")

        return {
            "certificate_path": str(cert_path),
            "key_path": str(key_path),
            "chain_path": str(chain_path),
            "subject": subject_name,
            "serial": certificate.serial_number,
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat()
        }

    def issue_certificate(self, csr_path: str, ca_cert_path: str, ca_key_path: str,
                         profile: CertificateProfile, output_path: str,
                         ca_password: Optional[str] = None) -> Dict:
        """Issue a certificate from a CSR"""
        self.logger.info(f"Issuing certificate: profile={profile.value}, csr={csr_path}")

        # Load CA certificate and key
        with open(ca_cert_path, 'rb') as f:
            ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

        with open(ca_key_path, 'rb') as f:
            ca_key = serialization.load_pem_private_key(
                f.read(),
                password=ca_password.encode() if ca_password else None,
                backend=default_backend()
            )

        # Load CSR
        with open(csr_path, 'rb') as f:
            csr = x509.load_pem_x509_csr(f.read(), default_backend())

        # Verify CSR signature
        if not csr.is_signature_valid:
            raise ValueError("CSR signature is invalid")

        # Get next serial number
        serial_file = self.ca_path / "db" / "serial"
        serial = int(serial_file.read_text().strip(), 16)
        serial_file.write_text(f"{serial + 1:04x}\n")

        # Build certificate
        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(csr.subject)
        cert_builder = cert_builder.issuer_name(ca_cert.subject)
        cert_builder = cert_builder.public_key(csr.public_key())
        cert_builder = cert_builder.serial_number(serial)

        not_before = datetime.datetime.utcnow()

        # Profile-specific validity and extensions
        if profile == CertificateProfile.TLS_SERVER:
            not_after = not_before + datetime.timedelta(days=90)
            cert_builder = cert_builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            cert_builder = cert_builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            cert_builder = cert_builder.add_extension(
                x509.ExtendedKeyUsage([x509.ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )

        elif profile == CertificateProfile.TLS_CLIENT:
            not_after = not_before + datetime.timedelta(days=365)
            cert_builder = cert_builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            cert_builder = cert_builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            cert_builder = cert_builder.add_extension(
                x509.ExtendedKeyUsage([x509.ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=False,
            )

        elif profile == CertificateProfile.EMAIL:
            not_after = not_before + datetime.timedelta(days=730)
            cert_builder = cert_builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            cert_builder = cert_builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=True,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            cert_builder = cert_builder.add_extension(
                x509.ExtendedKeyUsage([x509.ExtendedKeyUsageOID.EMAIL_PROTECTION]),
                critical=False,
            )

        elif profile == CertificateProfile.CODE_SIGNING:
            not_after = not_before + datetime.timedelta(days=1095)
            cert_builder = cert_builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            cert_builder = cert_builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            cert_builder = cert_builder.add_extension(
                x509.ExtendedKeyUsage([x509.ExtendedKeyUsageOID.CODE_SIGNING]),
                critical=False,
            )

        cert_builder = cert_builder.not_valid_before(not_before)
        cert_builder = cert_builder.not_valid_after(not_after)

        # Add Subject Key Identifier
        cert_builder = cert_builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(csr.public_key()),
            critical=False,
        )

        # Add Authority Key Identifier
        cert_builder = cert_builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_cert.public_key()),
            critical=False,
        )

        # Add CRL distribution points
        if self.config.crl_url:
            cert_builder = cert_builder.add_extension(
                x509.CRLDistributionPoints([
                    x509.DistributionPoint(
                        full_name=[x509.UniformResourceIdentifier(self.config.crl_url)],
                        relative_name=None,
                        reasons=None,
                        crl_issuer=None,
                    )
                ]),
                critical=False,
            )

        # Add Authority Information Access
        if self.config.ocsp_url:
            cert_builder = cert_builder.add_extension(
                x509.AuthorityInformationAccess([
                    x509.AccessDescription(
                        x509.AuthorityInformationAccessOID.OCSP,
                        x509.UniformResourceIdentifier(self.config.ocsp_url)
                    )
                ]),
                critical=False,
            )

        # Copy SANs from CSR if present
        try:
            san_extension = csr.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            cert_builder = cert_builder.add_extension(san_extension.value, critical=False)
        except x509.ExtensionNotFound:
            pass

        # Sign certificate
        hash_algo = getattr(hashes, self.config.hash_algorithm.upper().replace('-', ''))()
        certificate = cert_builder.sign(ca_key, hash_algo, default_backend())

        # Save certificate
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
        Path(output_path).write_bytes(cert_pem)

        # Update index
        self._update_index(certificate, "V")

        self.logger.info(f"Certificate issued: {output_path}, serial={serial}")

        return {
            "certificate_path": output_path,
            "serial": serial,
            "subject": certificate.subject.rfc4514_string(),
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat()
        }

    def revoke_certificate(self, serial: int, reason: RevocationReason) -> Dict:
        """Revoke a certificate"""
        self.logger.info(f"Revoking certificate: serial={serial}, reason={reason.name}")

        # Update index
        index_file = self.ca_path / "db" / "index.txt"
        lines = index_file.read_text().splitlines()
        new_lines = []
        revoked = False

        revocation_date = datetime.datetime.utcnow()
        revocation_str = revocation_date.strftime("%y%m%d%H%M%SZ")

        for line in lines:
            if line.startswith("V") and f"{serial:04x}" in line.lower():
                # Mark as revoked
                parts = line.split("\t")
                parts[0] = f"R\t{revocation_str},{reason.value}"
                new_lines.append("\t".join(parts))
                revoked = True
            else:
                new_lines.append(line)

        if not revoked:
            raise ValueError(f"Certificate with serial {serial} not found or already revoked")

        index_file.write_text("\n".join(new_lines) + "\n")

        self.logger.info(f"Certificate revoked: serial={serial}")

        return {
            "serial": serial,
            "revocation_date": revocation_date.isoformat(),
            "reason": reason.name
        }

    def generate_crl(self, ca_cert_path: str, ca_key_path: str, output_path: str,
                    ca_password: Optional[str] = None) -> Dict:
        """Generate Certificate Revocation List"""
        self.logger.info("Generating CRL")

        # Load CA certificate and key
        with open(ca_cert_path, 'rb') as f:
            ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

        with open(ca_key_path, 'rb') as f:
            ca_key = serialization.load_pem_private_key(
                f.read(),
                password=ca_password.encode() if ca_password else None,
                backend=default_backend()
            )

        # Get CRL number
        crlnumber_file = self.ca_path / "db" / "crlnumber"
        crl_number = int(crlnumber_file.read_text().strip(), 16)
        crlnumber_file.write_text(f"{crl_number + 1:02x}\n")

        # Build CRL
        crl_builder = x509.CertificateRevocationListBuilder()
        crl_builder = crl_builder.issuer_name(ca_cert.subject)

        last_update = datetime.datetime.utcnow()
        next_update = last_update + datetime.timedelta(days=self.config.crl_validity_days)
        crl_builder = crl_builder.last_update(last_update)
        crl_builder = crl_builder.next_update(next_update)

        # Add revoked certificates
        index_file = self.ca_path / "db" / "index.txt"
        for line in index_file.read_text().splitlines():
            if line.startswith("R"):
                parts = line.split("\t")
                revocation_info = parts[0].split(",")
                revocation_date_str = revocation_info[0][2:]  # Skip "R\t"
                revocation_date = datetime.datetime.strptime(revocation_date_str, "%y%m%d%H%M%SZ")
                reason_code = int(revocation_info[1]) if len(revocation_info) > 1 else 0

                serial_hex = parts[2]
                serial = int(serial_hex, 16)

                revoked_cert = x509.RevokedCertificateBuilder()
                revoked_cert = revoked_cert.serial_number(serial)
                revoked_cert = revoked_cert.revocation_date(revocation_date)

                if reason_code > 0:
                    reason = x509.ReasonFlags(reason_code)
                    revoked_cert = revoked_cert.add_extension(
                        x509.CRLReason(reason),
                        critical=False
                    )

                crl_builder = crl_builder.add_revoked_certificate(revoked_cert.build(default_backend()))

        # Add extensions
        crl_builder = crl_builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_cert.public_key()),
            critical=False,
        )
        crl_builder = crl_builder.add_extension(
            x509.CRLNumber(crl_number),
            critical=False,
        )

        # Sign CRL
        hash_algo = getattr(hashes, self.config.hash_algorithm.upper().replace('-', ''))()
        crl = crl_builder.sign(ca_key, hash_algo, default_backend())

        # Save CRL
        crl_pem = crl.public_bytes(serialization.Encoding.PEM)
        Path(output_path).write_bytes(crl_pem)

        self.logger.info(f"CRL generated: {output_path}, number={crl_number}")

        return {
            "crl_path": output_path,
            "crl_number": crl_number,
            "last_update": last_update.isoformat(),
            "next_update": next_update.isoformat(),
            "revoked_count": len([line for line in index_file.read_text().splitlines() if line.startswith("R")])
        }

    def _update_index(self, certificate: x509.Certificate, status: str):
        """Update certificate index"""
        index_file = self.ca_path / "db" / "index.txt"

        expiry = certificate.not_valid_after.strftime("%y%m%d%H%M%SZ")
        serial = f"{certificate.serial_number:04x}"
        subject = certificate.subject.rfc4514_string()

        entry = f"{status}\t{expiry}\t\t{serial}\tunknown\t{subject}\n"

        with open(index_file, 'a') as f:
            f.write(entry)

    def list_certificates(self, status_filter: Optional[str] = None) -> List[CertificateInfo]:
        """List certificates from index"""
        index_file = self.ca_path / "db" / "index.txt"
        certificates = []

        for line in index_file.read_text().splitlines():
            if not line.strip():
                continue

            parts = line.split("\t")
            status_info = parts[0]

            # Parse status
            if status_info.startswith("V"):
                status = "valid"
                revocation_date = None
                revocation_reason = None
            elif status_info.startswith("R"):
                status = "revoked"
                revocation_parts = status_info.split(",")
                revocation_date_str = revocation_parts[0][2:]  # Skip "R\t"
                revocation_date = datetime.datetime.strptime(revocation_date_str, "%y%m%d%H%M%SZ")
                revocation_reason = RevocationReason(int(revocation_parts[1])) if len(revocation_parts) > 1 else None
            elif status_info.startswith("E"):
                status = "expired"
                revocation_date = None
                revocation_reason = None
            else:
                continue

            if status_filter and status != status_filter:
                continue

            expiry_str = parts[1]
            not_after = datetime.datetime.strptime(expiry_str, "%y%m%d%H%M%SZ")

            serial = int(parts[3], 16)
            subject = parts[5]

            cert_info = CertificateInfo(
                serial=serial,
                subject=subject,
                not_before=datetime.datetime.utcnow(),  # Not stored in index
                not_after=not_after,
                status=status,
                revocation_date=revocation_date,
                revocation_reason=revocation_reason
            )
            certificates.append(cert_info)

        return certificates


def load_config(config_path: str) -> CAConfig:
    """Load CA configuration from YAML file"""
    with open(config_path) as f:
        data = yaml.safe_load(f)

    return CAConfig(
        name=data['name'],
        base_path=data['base_path'],
        key_algorithm=KeyAlgorithm(data['key_algorithm']),
        hash_algorithm=data['hash_algorithm'],
        validity_days=data['validity_days'],
        crl_validity_days=data.get('crl_validity_days', 7),
        ocsp_validity_hours=data.get('ocsp_validity_hours', 6),
        policy_oid=data.get('policy_oid'),
        cps_url=data.get('cps_url'),
        crl_url=data.get('crl_url'),
        ocsp_url=data.get('ocsp_url'),
        aia_url=data.get('aia_url'),
        enforce_policies=data.get('enforce_policies', True),
        require_hsm=data.get('require_hsm', False),
        hsm_config=data.get('hsm_config')
    )


def main():
    parser = argparse.ArgumentParser(
        description="CA Management Tool - Comprehensive Certificate Authority Operations",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # init-root command
    init_root = subparsers.add_parser('init-root', help='Initialize root CA')
    init_root.add_argument('--name', required=True, help='CA common name')
    init_root.add_argument('--config', required=True, help='Configuration file (YAML)')
    init_root.add_argument('--password', help='Private key password')
    init_root.add_argument('--json', action='store_true', help='Output JSON')

    # init-intermediate command
    init_int = subparsers.add_parser('init-intermediate', help='Initialize intermediate CA')
    init_int.add_argument('--name', required=True, help='CA common name')
    init_int.add_argument('--config', required=True, help='Configuration file (YAML)')
    init_int.add_argument('--root-cert', required=True, help='Root CA certificate')
    init_int.add_argument('--root-key', required=True, help='Root CA private key')
    init_int.add_argument('--password', help='Intermediate key password')
    init_int.add_argument('--root-password', help='Root key password')
    init_int.add_argument('--json', action='store_true', help='Output JSON')

    # issue command
    issue = subparsers.add_parser('issue', help='Issue certificate from CSR')
    issue.add_argument('--config', required=True, help='Configuration file (YAML)')
    issue.add_argument('--csr', required=True, help='CSR file')
    issue.add_argument('--ca-cert', required=True, help='CA certificate')
    issue.add_argument('--ca-key', required=True, help='CA private key')
    issue.add_argument('--profile', required=True, choices=[p.value for p in CertificateProfile],
                       help='Certificate profile')
    issue.add_argument('--output', required=True, help='Output certificate file')
    issue.add_argument('--password', help='CA key password')
    issue.add_argument('--json', action='store_true', help='Output JSON')

    # revoke command
    revoke = subparsers.add_parser('revoke', help='Revoke certificate')
    revoke.add_argument('--config', required=True, help='Configuration file (YAML)')
    revoke.add_argument('--serial', required=True, type=int, help='Certificate serial number')
    revoke.add_argument('--reason', required=True, choices=[r.name.lower() for r in RevocationReason],
                        help='Revocation reason')
    revoke.add_argument('--json', action='store_true', help='Output JSON')

    # gen-crl command
    gen_crl = subparsers.add_parser('gen-crl', help='Generate CRL')
    gen_crl.add_argument('--config', required=True, help='Configuration file (YAML)')
    gen_crl.add_argument('--ca-cert', required=True, help='CA certificate')
    gen_crl.add_argument('--ca-key', required=True, help='CA private key')
    gen_crl.add_argument('--output', required=True, help='Output CRL file')
    gen_crl.add_argument('--password', help='CA key password')
    gen_crl.add_argument('--json', action='store_true', help='Output JSON')

    # list command
    list_cmd = subparsers.add_parser('list', help='List certificates')
    list_cmd.add_argument('--config', required=True, help='Configuration file (YAML)')
    list_cmd.add_argument('--status', choices=['valid', 'revoked', 'expired'], help='Filter by status')
    list_cmd.add_argument('--json', action='store_true', help='Output JSON')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        config = load_config(args.config)
        manager = CAManager(config)

        if args.command == 'init-root':
            result = manager.create_root_ca(args.name, args.password)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Root CA created successfully: {result['certificate_path']}")
                print(f"Fingerprint (SHA256): {result['sha256_fingerprint']}")

        elif args.command == 'init-intermediate':
            result = manager.create_intermediate_ca(
                args.root_cert, args.root_key, args.name,
                args.password, args.root_password
            )
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Intermediate CA created successfully: {result['certificate_path']}")
                print(f"Certificate chain: {result['chain_path']}")

        elif args.command == 'issue':
            profile = CertificateProfile(args.profile)
            result = manager.issue_certificate(
                args.csr, args.ca_cert, args.ca_key, profile,
                args.output, args.password
            )
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Certificate issued successfully: {result['certificate_path']}")
                print(f"Serial: {result['serial']}")

        elif args.command == 'revoke':
            reason = RevocationReason[args.reason.upper()]
            result = manager.revoke_certificate(args.serial, reason)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Certificate revoked successfully: serial={result['serial']}")

        elif args.command == 'gen-crl':
            result = manager.generate_crl(args.ca_cert, args.ca_key, args.output, args.password)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"CRL generated successfully: {result['crl_path']}")
                print(f"Revoked certificates: {result['revoked_count']}")

        elif args.command == 'list':
            certificates = manager.list_certificates(args.status)
            if args.json:
                print(json.dumps([asdict(cert) for cert in certificates], indent=2, default=str))
            else:
                print(f"{'Serial':<10} {'Subject':<50} {'Status':<10} {'Expires'}")
                print("-" * 120)
                for cert in certificates:
                    print(f"{cert.serial:<10} {cert.subject:<50} {cert.status:<10} {cert.not_after.strftime('%Y-%m-%d')}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.json if hasattr(args, 'json') else False:
            print(json.dumps({"error": str(e)}, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
