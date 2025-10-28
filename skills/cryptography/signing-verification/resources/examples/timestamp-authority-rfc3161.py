#!/usr/bin/env python3
"""
RFC 3161 Timestamp Authority Integration

Demonstrates integrating with Time Stamp Authorities (TSA) per RFC 3161.
Timestamps provide proof that data existed at a specific time, crucial for
long-term signature validity and non-repudiation.

Features:
- RFC 3161 timestamp request generation
- TSA interaction (HTTP POST)
- Timestamp response validation
- Signature + timestamp bundling
- Long-term signature verification

Production Considerations:
- Use qualified TSAs for legal/compliance requirements
- Implement TSA failover and redundancy
- Verify TSA certificates and policies
- Archive timestamps with signatures
- Plan for TSA certificate expiration

Common Public TSAs:
- FreeTSA: https://freetsa.org/tsr
- DigiCert: https://timestamp.digicert.com
- Sectigo: http://timestamp.sectigo.com
"""

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.x509 import ocsp
except ImportError:
    print("Error: cryptography required. Install: pip install cryptography", file=sys.stderr)
    sys.exit(1)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("Warning: requests library required for TSA. Install: pip install requests", file=sys.stderr)


def create_timestamp_request(data: bytes, hash_algorithm: str = 'sha256') -> bytes:
    """
    Create RFC 3161 timestamp request

    Note: This is a simplified implementation. Production code should use
    proper ASN.1 encoding libraries like asn1crypto or pyasn1.
    """
    # Compute message digest
    if hash_algorithm == 'sha256':
        digest = hashlib.sha256(data).digest()
        oid = "2.16.840.1.101.3.4.2.1"  # SHA-256 OID
    elif hash_algorithm == 'sha384':
        digest = hashlib.sha384(data).digest()
        oid = "2.16.840.1.101.3.4.2.2"  # SHA-384 OID
    elif hash_algorithm == 'sha512':
        digest = hashlib.sha512(data).digest()
        oid = "2.16.840.1.101.3.4.2.3"  # SHA-512 OID
    else:
        raise ValueError(f"Unsupported hash algorithm: {hash_algorithm}")

    # Build timestamp request (simplified)
    # In production, use proper ASN.1 encoding
    timestamp_req = {
        'version': 1,
        'messageImprint': {
            'hashAlgorithm': oid,
            'hashedMessage': digest.hex()
        },
        'certReq': True,  # Request TSA certificate
        'nonce': None  # Should include random nonce in production
    }

    return str(timestamp_req).encode()


def send_timestamp_request(
    tsa_url: str,
    data: bytes,
    hash_algorithm: str = 'sha256',
    timeout: int = 30
) -> Optional[bytes]:
    """Send timestamp request to TSA"""
    if not HAS_REQUESTS:
        raise RuntimeError("requests library required")

    # Create request
    ts_req = create_timestamp_request(data, hash_algorithm)

    try:
        # Send request to TSA
        response = requests.post(
            tsa_url,
            data=ts_req,
            headers={
                'Content-Type': 'application/timestamp-query',
                'Accept': 'application/timestamp-reply'
            },
            timeout=timeout
        )

        if response.status_code == 200:
            return response.content
        else:
            print(f"TSA request failed: HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"TSA request error: {e}")
        return None


def parse_timestamp_response(ts_response: bytes) -> dict:
    """
    Parse timestamp response

    Note: Simplified implementation. Production should properly parse
    TimeStampResp ASN.1 structure.
    """
    # In production, parse the TimeStampResp structure:
    # - status (PKIStatusInfo)
    # - timeStampToken (SignedData)
    # - Extract genTime, accuracy, ordering, nonce

    return {
        'status': 'granted',  # Simplified
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'tsa_certificate': None,
        'raw_response': ts_response
    }


class TimestampedSignature:
    """Signature with RFC 3161 timestamp"""

    def __init__(
        self,
        data: bytes,
        signature: bytes,
        algorithm: str,
        timestamp: Optional[bytes] = None,
        tsa_url: Optional[str] = None
    ):
        self.data = data
        self.signature = signature
        self.algorithm = algorithm
        self.timestamp = timestamp
        self.tsa_url = tsa_url

    def add_timestamp(self, tsa_url: str) -> bool:
        """Add timestamp to signature"""
        if not HAS_REQUESTS:
            print("Error: requests library required for timestamping")
            return False

        print(f"Requesting timestamp from {tsa_url}...")

        # Create timestamp request for signature
        ts_response = send_timestamp_request(tsa_url, self.signature)

        if ts_response:
            self.timestamp = ts_response
            self.tsa_url = tsa_url
            print("✓ Timestamp obtained")
            return True
        else:
            print("✗ Timestamp request failed")
            return False

    def verify_timestamp(self) -> bool:
        """Verify timestamp validity"""
        if not self.timestamp:
            print("No timestamp present")
            return False

        try:
            # Parse timestamp response
            ts_data = parse_timestamp_response(self.timestamp)

            # In production, verify:
            # 1. TimeStampToken signature
            # 2. TSA certificate chain
            # 3. MessageImprint matches signature hash
            # 4. Policy OID is acceptable

            print(f"Timestamp: {ts_data['timestamp']}")
            print(f"Status: {ts_data['status']}")
            return ts_data['status'] == 'granted'

        except Exception as e:
            print(f"Timestamp verification failed: {e}")
            return False

    def save(self, path: Path):
        """Save timestamped signature bundle"""
        import json

        bundle = {
            'signature': self.signature.hex(),
            'algorithm': self.algorithm,
            'timestamp': self.timestamp.hex() if self.timestamp else None,
            'tsa_url': self.tsa_url,
            'created': datetime.now(timezone.utc).isoformat()
        }

        path.write_text(json.dumps(bundle, indent=2))

    @classmethod
    def load(cls, path: Path) -> 'TimestampedSignature':
        """Load timestamped signature bundle"""
        import json

        bundle = json.loads(path.read_text())

        return cls(
            data=b"",  # Data not stored in bundle
            signature=bytes.fromhex(bundle['signature']),
            algorithm=bundle['algorithm'],
            timestamp=bytes.fromhex(bundle['timestamp']) if bundle['timestamp'] else None,
            tsa_url=bundle['tsa_url']
        )


def demonstrate_basic_timestamping():
    """Demonstrate basic timestamping workflow"""
    print("\nBasic Timestamping Workflow")
    print("="*60)

    # 1. Generate key and sign
    print("\n1. Generating key and signing document...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    document = b"Important legal document requiring timestamp"
    signature = private_key.sign(
        document,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    print(f"   ✓ Document signed ({len(signature)} bytes)")

    # 2. Create timestamped signature
    print("\n2. Creating timestamped signature...")
    ts_sig = TimestampedSignature(
        data=document,
        signature=signature,
        algorithm='RSA-PSS-SHA256'
    )

    # 3. Add timestamp (using FreeTSA as example)
    print("\n3. Adding timestamp...")
    print("   Note: Using simulated timestamp (FreeTSA may not be available)")

    # Simulate timestamp for demonstration
    ts_sig.timestamp = b"simulated_timestamp_response"
    ts_sig.tsa_url = "https://freetsa.org/tsr"
    print("   ✓ Timestamp added (simulated)")

    # For real timestamp:
    # ts_sig.add_timestamp("https://freetsa.org/tsr")

    # 4. Save timestamped signature
    print("\n4. Saving timestamped signature...")
    ts_sig.save(Path("document.ts-sig"))
    print("   ✓ Saved to document.ts-sig")

    # 5. Load and verify
    print("\n5. Loading and verifying timestamped signature...")
    loaded_ts_sig = TimestampedSignature.load(Path("document.ts-sig"))
    print(f"   Algorithm: {loaded_ts_sig.algorithm}")
    print(f"   TSA URL: {loaded_ts_sig.tsa_url}")
    print(f"   Has timestamp: {loaded_ts_sig.timestamp is not None}")


def demonstrate_long_term_validation():
    """Demonstrate long-term signature validation"""
    print("\n\nLong-Term Signature Validation")
    print("="*60)

    print("""
Long-term signature validation addresses the problem of signature
validity beyond certificate expiration. Timestamps prove the signature
was created while the certificate was valid.

Validation Process:
1. Verify signature with certificate
2. Verify timestamp on signature
3. Check that signature timestamp < certificate expiration
4. Verify timestamp authority certificate
5. Archive timestamp and certificate chain

Example Timeline:
  2024-01-01: Document signed, certificate valid until 2025-01-01
  2024-01-01: Timestamp obtained from TSA
  2025-06-01: Certificate expired
  2026-01-01: Verification still valid because:
              - Timestamp proves signature created 2024-01-01
              - Certificate was valid at 2024-01-01
              - Timestamp is valid

Standards:
- ETSI EN 319 102-1: AdES (Advanced Electronic Signatures)
- PDF: PAdES (PDF Advanced Electronic Signatures)
- XML: XAdES (XML Advanced Electronic Signatures)
- JSON: JAdES (JSON Advanced Electronic Signatures)

Formats:
- AdES-BES: Basic Electronic Signature
- AdES-T: With Timestamp
- AdES-C: With Complete validation data
- AdES-X: With Extended validation data (multiple timestamps)
- AdES-A: Archival format (periodic re-timestamping)
""")


def demonstrate_archival_signatures():
    """Demonstrate archival signature creation"""
    print("\nArchival Signatures (AdES-A)")
    print("="*60)

    print("""
Archival signatures extend validity indefinitely through periodic
re-timestamping before previous timestamps become invalid.

Process:
1. Create initial signature with timestamp (AdES-T)
2. Before TSA certificate expires: add archive timestamp
3. Archive timestamp covers:
   - Original signature
   - Original timestamp
   - All previous archive timestamps
4. Repeat step 2-3 indefinitely

Implementation:
- Monitor TSA certificate expiration
- Schedule re-timestamping 6-12 months before expiration
- Maintain complete timestamp chain
- Store all timestamps and certificates

Tools:
- OpenSSL: Basic timestamp operations
- Adobe Acrobat: PDF long-term validation (PAdES)
- GlobalSign DSS: Document signing service
- Notarius: Archival signature service
    """)


def main():
    """Main demonstration"""
    print("RFC 3161 Timestamp Authority Integration")
    print("="*60)

    # Basic timestamping
    demonstrate_basic_timestamping()

    # Long-term validation
    demonstrate_long_term_validation()

    # Archival signatures
    demonstrate_archival_signatures()

    print("\n" + "="*60)
    print("Production Recommendations:")
    print("")
    print("TSA Selection:")
    print("  • Use qualified TSAs for legal/compliance needs")
    print("  • Verify TSA is RFC 3161 compliant")
    print("  • Check TSA policy OIDs")
    print("  • Ensure TSA has 24/7 availability")
    print("  • Review TSA practice statement")
    print("")
    print("Implementation:")
    print("  • Use proper ASN.1 libraries (asn1crypto, pyasn1)")
    print("  • Include random nonce in requests")
    print("  • Request TSA certificate in response")
    print("  • Verify TSA certificate chain")
    print("  • Validate timestamp signature")
    print("")
    print("Operations:")
    print("  • Implement TSA failover (multiple TSAs)")
    print("  • Monitor TSA response times")
    print("  • Archive all timestamps and certificates")
    print("  • Plan for TSA certificate renewal")
    print("  • Test timestamp verification regularly")
    print("")
    print("Standards Compliance:")
    print("  • ETSI EN 319 102-1 for AdES")
    print("  • RFC 3161 for timestamp protocol")
    print("  • eIDAS for qualified timestamps (EU)")
    print("  • NIST SP 800-102 for long-term validation")
    print("")
    print("Common Public TSAs:")
    print("  • FreeTSA: https://freetsa.org/tsr")
    print("  • DigiCert: https://timestamp.digicert.com")
    print("  • Sectigo: http://timestamp.sectigo.com")
    print("  • GlobalSign: http://timestamp.globalsign.com/tsa/r6advanced1")


if __name__ == "__main__":
    main()
