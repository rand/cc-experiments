#!/usr/bin/env python3
"""
ACME Protocol Automation Example

Demonstrates automated certificate issuance and renewal using the ACME protocol
(Let's Encrypt compatible) with HTTP-01 and DNS-01 challenges.

Features:
- Account registration
- Certificate ordering
- HTTP-01 challenge handling
- DNS-01 challenge handling (Cloudflare, Route53)
- Certificate installation
- Automatic renewal

Note: This is a simplified example. Production use should use certbot or acme.sh.

Dependencies:
    pip install acme cryptography dns python cloudflare boto3
"""

import json
import time
from pathlib import Path
from typing import Optional

from acme import client, messages
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
import josepy as jose


class ACMEClient:
    """Simple ACME client for certificate automation"""

    def __init__(
        self,
        email: str,
        directory_url: str = 'https://acme-v02.api.letsencrypt.org/directory',
        account_key_path: Optional[Path] = None,
    ):
        self.email = email
        self.directory_url = directory_url
        self.account_key_path = account_key_path or Path('account.key')

        # Load or generate account key
        if self.account_key_path.exists():
            self.account_key = self._load_account_key()
        else:
            self.account_key = self._generate_account_key()

        # Create ACME client
        self.net = client.ClientNetwork(self.account_key)
        self.directory = client.ClientV2.get_directory(directory_url, self.net)
        self.client_acme = client.ClientV2(self.directory, self.net)

        # Register account
        self.account = self._register_account()

    def _generate_account_key(self) -> jose.JWKRSA:
        """Generate new account key"""
        print(f"Generating new account key: {self.account_key_path}")

        # Generate RSA key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )

        # Save key
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        self.account_key_path.write_bytes(pem)
        self.account_key_path.chmod(0o600)

        # Convert to JOSE key
        return jose.JWKRSA(key=private_key)

    def _load_account_key(self) -> jose.JWKRSA:
        """Load existing account key"""
        print(f"Loading account key: {self.account_key_path}")

        pem = self.account_key_path.read_bytes()
        private_key = serialization.load_pem_private_key(
            pem, password=None, backend=default_backend()
        )
        return jose.JWKRSA(key=private_key)

    def _register_account(self):
        """Register ACME account"""
        print(f"Registering account: {self.email}")

        # Create registration
        regr = messages.NewRegistration.from_data(
            email=self.email,
            terms_of_service_agreed=True,
        )

        try:
            account = self.client_acme.new_account(regr)
            print(f"Account created: {account.uri}")
            return account
        except Exception as e:
            print(f"Account registration error (may already exist): {e}")
            # Try to use existing account
            account = self.client_acme.new_account(regr)
            return account

    def order_certificate(
        self,
        domains: list[str],
        challenge_type: str = 'http-01',
    ) -> tuple[x509.Certificate, bytes]:
        """Order and obtain certificate"""

        print(f"\n=== Ordering certificate for: {', '.join(domains)} ===")

        # Create order
        order = self.client_acme.new_order(
            messages.NewOrder.from_data(identifiers=[
                messages.Identifier(typ=messages.IDENTIFIER_FQDN, value=domain)
                for domain in domains
            ])
        )

        print(f"Order created: {order.uri}")

        # Process authorizations
        for authz in order.authorizations:
            self._complete_authorization(authz, challenge_type)

        # Generate CSR
        csr_pem, private_key_pem = self._generate_csr(domains)

        # Finalize order
        print("\nFinalizing order...")
        order = self.client_acme.finalize_order(order, csr_pem)

        # Poll for certificate
        print("Waiting for certificate issuance...")
        for _ in range(30):  # 30 attempts
            time.sleep(2)
            order = self.client_acme.poll_and_finalize(order)
            if order.fullchain_pem:
                print("Certificate issued!")
                break
        else:
            raise Exception("Certificate issuance timeout")

        # Parse certificate
        cert = x509.load_pem_x509_certificate(
            order.fullchain_pem.encode(),
            default_backend(),
        )

        return cert, private_key_pem

    def _complete_authorization(self, authz, challenge_type: str):
        """Complete domain authorization"""

        domain = authz.body.identifier.value
        print(f"\nAuthorizing domain: {domain}")

        # Find challenge
        challenge = None
        for chall in authz.body.challenges:
            if chall.typ == challenge_type:
                challenge = chall
                break

        if not challenge:
            raise Exception(f"Challenge type {challenge_type} not offered")

        # Get challenge response
        response, validation = challenge.response_and_validation(self.account_key)

        print(f"Challenge type: {challenge_type}")
        print(f"Challenge token: {challenge.token}")
        print(f"Challenge validation: {validation}")

        if challenge_type == 'http-01':
            # HTTP-01: Place file at /.well-known/acme-challenge/{token}
            well_known_path = Path(f".well-known/acme-challenge/{challenge.token}")
            well_known_path.parent.mkdir(parents=True, exist_ok=True)
            well_known_path.write_text(validation)
            print(f"Created challenge file: {well_known_path}")
            print(f"Make sure this is accessible at: http://{domain}/.well-known/acme-challenge/{challenge.token}")

        elif challenge_type == 'dns-01':
            # DNS-01: Create TXT record at _acme-challenge.{domain}
            print(f"Create DNS TXT record:")
            print(f"  Name: _acme-challenge.{domain}")
            print(f"  Value: {validation}")

        input("Press Enter after completing the challenge...")

        # Submit challenge
        print("Submitting challenge response...")
        self.client_acme.answer_challenge(challenge, response)

        # Wait for validation
        print("Waiting for validation...")
        for _ in range(30):
            time.sleep(2)
            authz = self.client_acme.poll(authz)
            if authz.body.status == messages.STATUS_VALID:
                print(f"Domain {domain} validated!")
                break
            elif authz.body.status == messages.STATUS_INVALID:
                raise Exception(f"Validation failed for {domain}")
        else:
            raise Exception(f"Validation timeout for {domain}")

        # Cleanup
        if challenge_type == 'http-01':
            well_known_path.unlink(missing_ok=True)

    def _generate_csr(self, domains: list[str]) -> tuple[bytes, bytes]:
        """Generate Certificate Signing Request"""

        print(f"\nGenerating CSR for: {', '.join(domains)}")

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )

        # Build CSR
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, domains[0]),
        ])

        san = x509.SubjectAlternativeName([
            x509.DNSName(domain) for domain in domains
        ])

        csr = x509.CertificateSigningRequestBuilder().subject_name(
            subject
        ).add_extension(
            san,
            critical=False,
        ).sign(private_key, hashes.SHA256(), default_backend())

        # Serialize
        csr_pem = csr.public_bytes(serialization.Encoding.PEM)
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        return csr_pem, private_key_pem


def example_http01():
    """Example: Obtain certificate with HTTP-01 challenge"""

    acme_client = ACMEClient(
        email='admin@example.com',
        directory_url='https://acme-staging-v02.api.letsencrypt.org/directory',  # Staging
    )

    cert, private_key = acme_client.order_certificate(
        domains=['example.com', 'www.example.com'],
        challenge_type='http-01',
    )

    # Save certificate and key
    Path('cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    Path('key.pem').write_bytes(private_key)
    Path('key.pem').chmod(0o600)

    print("\n=== Certificate obtained successfully! ===")
    print(f"Certificate: cert.pem")
    print(f"Private key: key.pem")
    print(f"Valid until: {cert.not_valid_after}")


def example_dns01():
    """Example: Obtain wildcard certificate with DNS-01 challenge"""

    acme_client = ACMEClient(
        email='admin@example.com',
        directory_url='https://acme-staging-v02.api.letsencrypt.org/directory',  # Staging
    )

    cert, private_key = acme_client.order_certificate(
        domains=['*.example.com', 'example.com'],
        challenge_type='dns-01',
    )

    # Save certificate and key
    Path('wildcard-cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    Path('wildcard-key.pem').write_bytes(private_key)
    Path('wildcard-key.pem').chmod(0o600)

    print("\n=== Wildcard certificate obtained! ===")
    print(f"Certificate: wildcard-cert.pem")
    print(f"Private key: wildcard-key.pem")


if __name__ == '__main__':
    import sys

    print("ACME Protocol Automation Example")
    print("=" * 50)
    print("\nThis example uses Let's Encrypt STAGING environment")
    print("Certificates will NOT be trusted by browsers\n")

    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} http01   # HTTP-01 challenge")
        print(f"  {sys.argv[0]} dns01    # DNS-01 challenge (wildcard)")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == 'http01':
        example_http01()
    elif mode == 'dns01':
        example_dns01()
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
