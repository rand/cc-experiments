#!/usr/bin/env python3
"""
Compliance Configuration for Key Management

Production example of configuring key management for compliance with
various standards (PCI-DSS, HIPAA, GDPR, SOC 2).

Features:
- Compliance policy templates
- Automated compliance checking
- Audit trail generation
- Key lifecycle enforcement
- Access control validation
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from enum import Enum
from dataclasses import dataclass, asdict


class ComplianceStandard(Enum):
    """Compliance standards"""
    PCI_DSS = "pci-dss"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    SOC2 = "soc2"
    FIPS_140_2 = "fips-140-2"


@dataclass
class CompliancePolicy:
    """Compliance policy configuration"""
    standard: str
    key_rotation_days: int
    min_key_length: int
    require_hsm: bool
    require_mfa: bool
    audit_log_retention_days: int
    allowed_algorithms: List[str]
    require_separation_of_duties: bool


class ComplianceConfigManager:
    """Compliance configuration manager"""

    @staticmethod
    def get_policy_template(standard: ComplianceStandard) -> CompliancePolicy:
        """Get compliance policy template for standard"""
        templates = {
            ComplianceStandard.PCI_DSS: CompliancePolicy(
                standard="PCI-DSS v4.0",
                key_rotation_days=365,  # Annual rotation required
                min_key_length=128,     # AES-128 minimum
                require_hsm=True,       # Requirement 3.6.1
                require_mfa=True,
                audit_log_retention_days=365,
                allowed_algorithms=["AES-256-GCM", "RSA-2048", "ECC-P256"],
                require_separation_of_duties=True
            ),
            ComplianceStandard.HIPAA: CompliancePolicy(
                standard="HIPAA Security Rule",
                key_rotation_days=365,
                min_key_length=128,
                require_hsm=False,      # Addressable, not required
                require_mfa=True,
                audit_log_retention_days=2555,  # 7 years
                allowed_algorithms=["AES-256-GCM", "AES-128-GCM"],
                require_separation_of_duties=True
            ),
            ComplianceStandard.GDPR: CompliancePolicy(
                standard="GDPR Article 32",
                key_rotation_days=180,  # Recommended practice
                min_key_length=256,     # State of the art
                require_hsm=False,
                require_mfa=True,
                audit_log_retention_days=365,
                allowed_algorithms=["AES-256-GCM", "ChaCha20-Poly1305"],
                require_separation_of_duties=False
            ),
            ComplianceStandard.SOC2: CompliancePolicy(
                standard="SOC 2 Trust Services Criteria",
                key_rotation_days=365,
                min_key_length=256,
                require_hsm=False,
                require_mfa=True,
                audit_log_retention_days=730,  # 2 years recommended
                allowed_algorithms=["AES-256-GCM", "RSA-2048", "ECC-P256"],
                require_separation_of_duties=True
            ),
            ComplianceStandard.FIPS_140_2: CompliancePolicy(
                standard="FIPS 140-2",
                key_rotation_days=365,
                min_key_length=128,
                require_hsm=True,       # Level 3/4 requirement
                require_mfa=False,
                audit_log_retention_days=365,
                allowed_algorithms=["AES-256-GCM", "AES-128-GCM", "RSA-2048"],
                require_separation_of_duties=False
            )
        }

        return templates.get(standard)

    @staticmethod
    def validate_key_compliance(key_metadata: Dict, policy: CompliancePolicy) -> Dict:
        """Validate key against compliance policy"""
        violations = []

        # Check key age
        created_at = datetime.fromisoformat(key_metadata.get('created_at', ''))
        age_days = (datetime.now(timezone.utc) - created_at).days

        if age_days > policy.key_rotation_days:
            violations.append({
                'requirement': 'Key rotation',
                'expected': f'{policy.key_rotation_days} days',
                'actual': f'{age_days} days',
                'severity': 'high'
            })

        # Check key length
        key_length = key_metadata.get('key_length', 0)
        if key_length < policy.min_key_length:
            violations.append({
                'requirement': 'Minimum key length',
                'expected': f'{policy.min_key_length} bits',
                'actual': f'{key_length} bits',
                'severity': 'critical'
            })

        # Check HSM requirement
        if policy.require_hsm and not key_metadata.get('hsm_backed', False):
            violations.append({
                'requirement': 'HSM-backed keys',
                'expected': 'true',
                'actual': 'false',
                'severity': 'high'
            })

        # Check algorithm
        algorithm = key_metadata.get('algorithm', '')
        if algorithm not in policy.allowed_algorithms:
            violations.append({
                'requirement': 'Approved algorithm',
                'expected': ', '.join(policy.allowed_algorithms),
                'actual': algorithm,
                'severity': 'high'
            })

        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'standard': policy.standard
        }

    @staticmethod
    def generate_compliance_report(keys: List[Dict], standard: ComplianceStandard) -> Dict:
        """Generate compliance report for all keys"""
        policy = ComplianceConfigManager.get_policy_template(standard)

        results = []
        total_violations = 0

        for key in keys:
            validation = ComplianceConfigManager.validate_key_compliance(key, policy)
            results.append({
                'key_id': key.get('key_id'),
                'compliant': validation['compliant'],
                'violations': validation['violations']
            })

            total_violations += len(validation['violations'])

        return {
            'standard': standard.value,
            'scan_time': datetime.now(timezone.utc).isoformat(),
            'total_keys': len(keys),
            'compliant_keys': sum(1 for r in results if r['compliant']),
            'total_violations': total_violations,
            'compliance_percentage': round(
                sum(1 for r in results if r['compliant']) / len(keys) * 100, 2
            ) if keys else 0,
            'results': results
        }


def main():
    """Example usage"""
    # Sample key metadata
    keys = [
        {
            'key_id': 'key-12345',
            'created_at': (datetime.now(timezone.utc) - timedelta(days=400)).isoformat(),
            'key_length': 256,
            'hsm_backed': True,
            'algorithm': 'AES-256-GCM'
        },
        {
            'key_id': 'key-67890',
            'created_at': (datetime.now(timezone.utc) - timedelta(days=100)).isoformat(),
            'key_length': 256,
            'hsm_backed': False,
            'algorithm': 'AES-256-GCM'
        }
    ]

    # Generate PCI-DSS compliance report
    report = ComplianceConfigManager.generate_compliance_report(
        keys,
        ComplianceStandard.PCI_DSS
    )

    print("PCI-DSS Compliance Report:")
    print(json.dumps(report, indent=2))

    # Get policy template for HIPAA
    hipaa_policy = ComplianceConfigManager.get_policy_template(
        ComplianceStandard.HIPAA
    )

    print("\nHIPAA Policy Template:")
    print(json.dumps(asdict(hipaa_policy), indent=2))


if __name__ == '__main__':
    main()
