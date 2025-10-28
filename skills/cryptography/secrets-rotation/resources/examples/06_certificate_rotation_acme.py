#!/usr/bin/env python3
"""
TLS Certificate Rotation with ACME (Let's Encrypt)

Demonstrates:
- Automated certificate renewal using ACME protocol
- Zero-downtime certificate rotation
- Multi-domain certificate management
- Certificate monitoring and alerting
- Integration with load balancers/reverse proxies

Prerequisites:
    pip install acme certbot cryptography boto3

Let's Encrypt Setup:
    - Automatic via ACME protocol
    - HTTP-01 or DNS-01 challenge supported
    - Rate limits: 50 certs/domain/week
"""

import os
import time
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

import boto3
from acme import client, messages, challenges
from acme.client import ClientV2
from josepy import JWKRSA


class ACMECertificateRotator:
    """
    Automated certificate rotation using ACME protocol.
    """

    def __init__(self, email: str, acme_directory: str = 'https://acme-v02.api.letsencrypt.org/directory'):
        """
        Initialize ACME client.

        Args:
            email: Contact email for Let's Encrypt
            acme_directory: ACME directory URL
                - Production: https://acme-v02.api.letsencrypt.org/directory
                - Staging: https://acme-staging-v02.api.letsencrypt.org/directory
        """
        self.email = email
        self.acme_directory = acme_directory
        self.account_key = None
        self.acme_client = None
        self.cert_dir = Path('/etc/letsencrypt/live')
        self.cert_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self):
        """Initialize ACME client with account."""
        print(f"[{datetime.utcnow().isoformat()}] Initializing ACME client")

        # Generate account key if not exists
        account_key_path = Path('/etc/letsencrypt/account.key')
        if account_key_path.exists():
            with open(account_key_path, 'rb') as f:
                self.account_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
        else:
            self.account_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            with open(account_key_path, 'wb') as f:
                f.write(self.account_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            print(f"  Generated new account key")

        # Create ACME client
        net = client.ClientNetwork(self.account_key)
        directory = messages.Directory.from_json(net.get(self.acme_directory).json())
        self.acme_client = ClientV2(directory, net)

        # Register account
        try:
            registration = self.acme_client.new_account(
                messages.NewRegistration.from_data(
                    email=self.email,
                    terms_of_service_agreed=True
                )
            )
            print(f"  Registered ACME account: {self.email}")
        except Exception as e:
            print(f"  Using existing account: {self.email}")

    def obtain_certificate(self, domains: List[str], challenge_type: str = 'http-01') -> Dict[str, Any]:
        """
        Obtain new certificate for domains.

        Args:
            domains: List of domain names
            challenge_type: Challenge type (http-01 or dns-01)

        Returns:
            Certificate paths and metadata
        """
        print(f"[{datetime.utcnow().isoformat()}] Obtaining certificate")
        print(f"  Domains: {', '.join(domains)}")

        # Create order
        order = self.acme_client.new_order(
            [messages.Identifier(typ=messages.IDENTIFIER_FQDN, value=domain)
             for domain in domains]
        )

        print(f"  Order created: {order.uri}")

        # Process challenges
        for authz in order.authorizations:
            domain = authz.body.identifier.value
            print(f"  Processing challenges for: {domain}")

            # Get challenge
            challenge = None
            for chall in authz.body.challenges:
                if isinstance(chall.chall, challenges.HTTP01) and challenge_type == 'http-01':
                    challenge = chall
                    break
                elif isinstance(chall.chall, challenges.DNS01) and challenge_type == 'dns-01':
                    challenge = chall
                    break

            if not challenge:
                raise RuntimeError(f"No {challenge_type} challenge found for {domain}")

            # Respond to challenge
            response, validation = challenge.response_and_validation(self.account_key)

            if challenge_type == 'http-01':
                # HTTP-01: Create challenge file
                challenge_path = Path(f'/var/www/.well-known/acme-challenge/{challenge.chall.token}')
                challenge_path.parent.mkdir(parents=True, exist_ok=True)
                challenge_path.write_text(validation)
                print(f"    Created HTTP-01 challenge: {challenge_path}")

            elif challenge_type == 'dns-01':
                # DNS-01: Create TXT record
                txt_record = f"_acme-challenge.{domain}"
                print(f"    Create DNS TXT record: {txt_record} = {validation}")
                print(f"    Waiting for DNS propagation...")
                time.sleep(30)  # Wait for DNS propagation

            # Submit challenge response
            self.acme_client.answer_challenge(challenge, response)
            print(f"    Challenge submitted")

        # Wait for validation
        print("  Waiting for validation...")
        order = self.acme_client.poll_and_finalize(order)

        # Generate private key and CSR
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        csr_builder = x509.CertificateSigningRequestBuilder()
        csr_builder = csr_builder.subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, domains[0])
        ]))
        csr_builder = csr_builder.add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain) for domain in domains
            ]),
            critical=False
        )
        csr = csr_builder.sign(private_key, hashes.SHA256(), default_backend())

        # Get certificate
        cert = order.fullchain_pem
        print(f"  Certificate obtained")

        # Save certificate and key
        domain_dir = self.cert_dir / domains[0]
        domain_dir.mkdir(parents=True, exist_ok=True)

        cert_path = domain_dir / 'fullchain.pem'
        key_path = domain_dir / 'privkey.pem'

        cert_path.write_text(cert)
        key_path.write_bytes(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

        print(f"  Saved certificate: {cert_path}")
        print(f"  Saved private key: {key_path}")

        # Parse certificate for metadata
        cert_obj = x509.load_pem_x509_certificate(cert.encode(), default_backend())

        return {
            'domains': domains,
            'cert_path': str(cert_path),
            'key_path': str(key_path),
            'not_before': cert_obj.not_valid_before.isoformat(),
            'not_after': cert_obj.not_valid_after.isoformat(),
            'serial_number': cert_obj.serial_number,
            'obtained_at': datetime.utcnow().isoformat()
        }

    def renew_certificate(self, domains: List[str], days_before_expiry: int = 30) -> Optional[Dict[str, Any]]:
        """
        Renew certificate if expiring soon.

        Args:
            domains: Domain names
            days_before_expiry: Renew this many days before expiry

        Returns:
            Renewal result or None if not needed
        """
        print(f"[{datetime.utcnow().isoformat()}] Checking renewal: {domains[0]}")

        cert_path = self.cert_dir / domains[0] / 'fullchain.pem'

        if not cert_path.exists():
            print("  Certificate not found, obtaining new one")
            return self.obtain_certificate(domains)

        # Check expiry
        cert_data = cert_path.read_bytes()
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())

        days_until_expiry = (cert.not_valid_after - datetime.utcnow()).days
        print(f"  Days until expiry: {days_until_expiry}")

        if days_until_expiry <= days_before_expiry:
            print(f"  Renewal needed (threshold: {days_before_expiry} days)")
            return self.obtain_certificate(domains)
        else:
            print(f"  Renewal not needed")
            return None

    def rotate_certificate_on_load_balancer(self, domains: List[str],
                                           lb_arn: str, listener_arn: str):
        """
        Rotate certificate on AWS ALB/NLB with zero downtime.

        Args:
            domains: Domain names
            lb_arn: Load balancer ARN
            listener_arn: HTTPS listener ARN
        """
        print(f"[{datetime.utcnow().isoformat()}] Rotating certificate on load balancer")

        # Obtain new certificate
        cert_info = self.obtain_certificate(domains)

        # Upload to ACM
        acm_client = boto3.client('acm')

        cert_path = Path(cert_info['cert_path'])
        key_path = Path(cert_info['key_path'])

        response = acm_client.import_certificate(
            Certificate=cert_path.read_bytes(),
            PrivateKey=key_path.read_bytes()
        )

        new_cert_arn = response['CertificateArn']
        print(f"  Uploaded to ACM: {new_cert_arn}")

        # Update load balancer listener
        elbv2_client = boto3.client('elbv2')

        elbv2_client.modify_listener(
            ListenerArn=listener_arn,
            Certificates=[{
                'CertificateArn': new_cert_arn
            }]
        )

        print(f"  Load balancer updated")

        # Get old certificate ARN and delete after grace period
        print(f"  Waiting 5 minutes before removing old certificate...")
        time.sleep(300)

        # Note: In production, identify and delete old certificate
        print(f"  Rotation complete")


class CertificateMonitor:
    """
    Monitor certificates and trigger rotation.
    """

    def __init__(self, cert_dir: str = '/etc/letsencrypt/live'):
        self.cert_dir = Path(cert_dir)

    def check_all_certificates(self, warning_days: int = 30) -> List[Dict[str, Any]]:
        """
        Check all certificates for expiry.

        Args:
            warning_days: Warn if expiring within this many days

        Returns:
            List of certificates needing renewal
        """
        print(f"[{datetime.utcnow().isoformat()}] Checking all certificates")

        renewals_needed = []

        for cert_path in self.cert_dir.glob('*/fullchain.pem'):
            domain = cert_path.parent.name

            cert_data = cert_path.read_bytes()
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())

            days_until_expiry = (cert.not_valid_after - datetime.utcnow()).days

            status = {
                'domain': domain,
                'not_after': cert.not_valid_after.isoformat(),
                'days_until_expiry': days_until_expiry,
                'renewal_needed': days_until_expiry <= warning_days
            }

            print(f"  {domain}: {days_until_expiry} days until expiry")

            if status['renewal_needed']:
                renewals_needed.append(status)

        return renewals_needed


# Example usage
if __name__ == '__main__':
    # Configuration
    EMAIL = 'admin@example.com'
    DOMAINS = ['example.com', 'www.example.com']

    # Use staging for testing
    ACME_DIRECTORY = 'https://acme-staging-v02.api.letsencrypt.org/directory'

    # Initialize rotator
    rotator = ACMECertificateRotator(email=EMAIL, acme_directory=ACME_DIRECTORY)
    rotator.initialize()

    # Obtain certificate
    cert_info = rotator.obtain_certificate(DOMAINS)
    print(f"\nCertificate obtained:")
    print(f"  Domains: {', '.join(cert_info['domains'])}")
    print(f"  Valid until: {cert_info['not_after']}")
    print(f"  Certificate: {cert_info['cert_path']}")

    # Check renewal
    renewal = rotator.renew_certificate(DOMAINS, days_before_expiry=30)
    if renewal:
        print(f"\nCertificate renewed:")
        print(f"  New expiry: {renewal['not_after']}")

    # Monitor certificates
    monitor = CertificateMonitor()
    renewals = monitor.check_all_certificates(warning_days=30)
    print(f"\nCertificates needing renewal: {len(renewals)}")
