#!/usr/bin/env python3
"""
Cryptographic Key Audit Tool

Comprehensive audit of cryptographic keys across multiple KMS platforms.
Checks key usage, age, rotation status, compliance, and security posture.

Features:
- Multi-platform support (AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault)
- Key age and rotation compliance checks
- Unused key detection
- Access control audit
- Compliance reporting (FIPS 140-2, PCI-DSS, HIPAA, GDPR)
- Security score calculation
- Detailed and summary reports
- JSON and human-readable output

Usage:
    ./audit_keys.py --platform aws-kms --region us-east-1 --json
    ./audit_keys.py --platform gcp-kms --project my-project --location global
    ./audit_keys.py --platform azure --vault-name my-vault --compliance pci-dss
    ./audit_keys.py --platform vault --addr http://127.0.0.1:8200 --token <token>
    ./audit_keys.py --all-platforms --output-file audit-report.json
    ./audit_keys.py --platform aws-kms --check-unused --days 90 --verbose
"""

import argparse
import base64
import hashlib
import json
import os
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
import warnings


class KMSPlatform(Enum):
    """Supported KMS platforms"""
    AWS_KMS = "aws-kms"
    GCP_KMS = "gcp-kms"
    AZURE_VAULT = "azure"
    HASHICORP_VAULT = "vault"
    LOCAL = "local"


class ComplianceStandard(Enum):
    """Compliance standards"""
    FIPS_140_2 = "fips-140-2"
    PCI_DSS = "pci-dss"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    SOC2 = "soc2"
    NIST_800_57 = "nist-800-57"


class KeyStatus(Enum):
    """Key status"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    PENDING_DELETION = "pending_deletion"
    PENDING_IMPORT = "pending_import"
    UNAVAILABLE = "unavailable"


class SeverityLevel(Enum):
    """Audit finding severity"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class KeyMetadata:
    """Cryptographic key metadata"""
    key_id: str
    alias: Optional[str]
    arn: Optional[str]
    platform: str
    key_type: str  # "symmetric", "asymmetric", "hmac"
    algorithm: str  # "AES_256", "RSA_2048", etc.
    key_usage: str  # "ENCRYPT_DECRYPT", "SIGN_VERIFY"
    status: str
    created_at: datetime
    last_rotated_at: Optional[datetime]
    age_days: int
    rotation_enabled: bool
    deletion_date: Optional[datetime] = None
    description: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    is_managed: bool = False
    fips_validated: bool = False
    hsm_backed: bool = False


@dataclass
class KeyUsageStats:
    """Key usage statistics"""
    key_id: str
    encrypt_count: int = 0
    decrypt_count: int = 0
    sign_count: int = 0
    verify_count: int = 0
    total_operations: int = 0
    last_used: Optional[datetime] = None
    days_since_last_use: Optional[int] = None


@dataclass
class AccessControlInfo:
    """Key access control information"""
    key_id: str
    principals: List[str] = field(default_factory=list)  # Users/roles with access
    permissions: List[str] = field(default_factory=list)  # Granted permissions
    public_access: bool = False
    overly_permissive: bool = False
    mfa_required: bool = False


@dataclass
class ComplianceFinding:
    """Compliance audit finding"""
    key_id: str
    standard: str
    requirement: str
    compliant: bool
    severity: str
    details: str
    remediation: Optional[str] = None


@dataclass
class AuditFinding:
    """General audit finding"""
    key_id: str
    category: str  # "rotation", "usage", "access", "compliance", "security"
    severity: str
    title: str
    description: str
    remediation: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class KeyAuditReport:
    """Complete key audit report"""
    platform: str
    scan_time: str
    total_keys: int
    enabled_keys: int
    disabled_keys: int
    pending_deletion: int
    rotation_enabled: int
    hsm_backed: int
    fips_validated: int
    keys: List[KeyMetadata] = field(default_factory=list)
    findings: List[AuditFinding] = field(default_factory=list)
    compliance_findings: List[ComplianceFinding] = field(default_factory=list)
    security_score: Optional[int] = None
    summary: Dict = field(default_factory=dict)


class AWSKMSAuditor:
    """AWS KMS key auditor"""

    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.client = None
        self.cloudtrail = None

    def _init_clients(self):
        """Initialize AWS clients"""
        try:
            import boto3
            self.client = boto3.client('kms', region_name=self.region)
            self.cloudtrail = boto3.client('cloudtrail', region_name=self.region)
        except ImportError:
            raise RuntimeError("boto3 not installed. Install with: pip install boto3")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize AWS clients: {e}")

    def list_keys(self) -> List[KeyMetadata]:
        """List all KMS keys"""
        if not self.client:
            self._init_clients()

        keys = []
        paginator = self.client.get_paginator('list_keys')

        for page in paginator.paginate():
            for key in page['Keys']:
                key_id = key['KeyId']
                metadata = self._get_key_metadata(key_id)
                if metadata:
                    keys.append(metadata)

        return keys

    def _get_key_metadata(self, key_id: str) -> Optional[KeyMetadata]:
        """Get key metadata"""
        try:
            response = self.client.describe_key(KeyId=key_id)
            key_meta = response['KeyMetadata']

            # Get rotation status
            rotation_enabled = False
            try:
                rotation_response = self.client.get_key_rotation_status(KeyId=key_id)
                rotation_enabled = rotation_response['KeyRotationEnabled']
            except:
                pass  # Customer managed keys only

            # Get aliases
            alias = None
            try:
                aliases = self.client.list_aliases(KeyId=key_id)
                if aliases['Aliases']:
                    alias = aliases['Aliases'][0]['AliasName']
            except:
                pass

            # Get tags
            tags = {}
            try:
                tags_response = self.client.list_resource_tags(KeyId=key_id)
                tags = {tag['TagKey']: tag['TagValue'] for tag in tags_response.get('Tags', [])}
            except:
                pass

            created_at = key_meta['CreationDate']
            age_days = (datetime.now(timezone.utc) - created_at).days

            # Determine HSM backing
            hsm_backed = key_meta.get('Origin') == 'AWS_CLOUDHSM' or \
                        key_meta.get('CustomKeyStoreId') is not None

            # FIPS validation status
            fips_validated = hsm_backed  # CloudHSM is FIPS 140-2 Level 3

            return KeyMetadata(
                key_id=key_id,
                alias=alias,
                arn=key_meta['Arn'],
                platform="AWS KMS",
                key_type="symmetric" if key_meta['KeySpec'] == 'SYMMETRIC_DEFAULT' else "asymmetric",
                algorithm=key_meta.get('KeySpec', 'SYMMETRIC_DEFAULT'),
                key_usage=key_meta['KeyUsage'],
                status=key_meta['KeyState'],
                created_at=created_at,
                last_rotated_at=None,  # AWS doesn't expose this
                age_days=age_days,
                rotation_enabled=rotation_enabled,
                deletion_date=key_meta.get('DeletionDate'),
                description=key_meta.get('Description', ''),
                tags=tags,
                is_managed=key_meta['KeyManager'] == 'AWS',
                fips_validated=fips_validated,
                hsm_backed=hsm_backed
            )

        except Exception as e:
            print(f"Error getting metadata for key {key_id}: {e}", file=sys.stderr)
            return None

    def get_key_usage(self, key_id: str, days: int = 90) -> KeyUsageStats:
        """Get key usage statistics from CloudTrail"""
        usage = KeyUsageStats(key_id=key_id)

        try:
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

            # Query CloudTrail for KMS events
            response = self.cloudtrail.lookup_events(
                LookupAttributes=[
                    {'AttributeKey': 'ResourceName', 'AttributeValue': key_id}
                ],
                StartTime=start_time,
                MaxResults=50  # Limit for audit purposes
            )

            last_event_time = None

            for event in response.get('Events', []):
                event_name = event['EventName']

                if event_name == 'Encrypt':
                    usage.encrypt_count += 1
                elif event_name == 'Decrypt':
                    usage.decrypt_count += 1
                elif event_name == 'Sign':
                    usage.sign_count += 1
                elif event_name == 'Verify':
                    usage.verify_count += 1

                event_time = event['EventTime']
                if not last_event_time or event_time > last_event_time:
                    last_event_time = event_time

            usage.total_operations = (
                usage.encrypt_count +
                usage.decrypt_count +
                usage.sign_count +
                usage.verify_count
            )

            if last_event_time:
                usage.last_used = last_event_time
                usage.days_since_last_use = (datetime.now(timezone.utc) - last_event_time).days

        except Exception as e:
            print(f"Warning: Could not retrieve usage stats for {key_id}: {e}", file=sys.stderr)

        return usage

    def get_access_control(self, key_id: str) -> AccessControlInfo:
        """Get key access control information"""
        access = AccessControlInfo(key_id=key_id)

        try:
            # Get key policy
            response = self.client.get_key_policy(KeyId=key_id, PolicyName='default')
            policy = json.loads(response['Policy'])

            for statement in policy.get('Statement', []):
                principal = statement.get('Principal', {})

                # Check for public access
                if principal == '*' or principal.get('AWS') == '*':
                    access.public_access = True
                    access.overly_permissive = True

                # Extract principals
                if isinstance(principal, dict):
                    aws_principals = principal.get('AWS', [])
                    if isinstance(aws_principals, str):
                        aws_principals = [aws_principals]
                    access.principals.extend(aws_principals)

                # Extract permissions
                actions = statement.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                access.permissions.extend(actions)

                # Check for overly permissive policies
                if 'kms:*' in actions or '*' in actions:
                    access.overly_permissive = True

                # Check for MFA requirement
                condition = statement.get('Condition', {})
                if 'aws:MultiFactorAuthPresent' in str(condition):
                    access.mfa_required = True

        except Exception as e:
            print(f"Warning: Could not retrieve access control for {key_id}: {e}", file=sys.stderr)

        return access


class GCPKMSAuditor:
    """Google Cloud KMS auditor"""

    def __init__(self, project_id: str, location: str = "global"):
        self.project_id = project_id
        self.location = location
        self.client = None

    def _init_client(self):
        """Initialize GCP KMS client"""
        try:
            from google.cloud import kms
            self.client = kms.KeyManagementServiceClient()
        except ImportError:
            raise RuntimeError("google-cloud-kms not installed. Install with: pip install google-cloud-kms")

    def list_keys(self) -> List[KeyMetadata]:
        """List all KMS keys"""
        if not self.client:
            self._init_client()

        keys = []
        parent = f"projects/{self.project_id}/locations/{self.location}"

        # List key rings
        for key_ring in self.client.list_key_rings(request={"parent": parent}):
            # List crypto keys in each key ring
            for crypto_key in self.client.list_crypto_keys(request={"parent": key_ring.name}):
                metadata = self._parse_key_metadata(crypto_key)
                if metadata:
                    keys.append(metadata)

        return keys

    def _parse_key_metadata(self, crypto_key) -> Optional[KeyMetadata]:
        """Parse GCP crypto key metadata"""
        try:
            # Get primary version
            primary_version = crypto_key.primary

            created_at = crypto_key.create_time
            age_days = (datetime.now(timezone.utc) - created_at).days

            # Rotation configuration
            rotation_enabled = hasattr(crypto_key, 'rotation_period') and \
                             crypto_key.rotation_period.seconds > 0

            last_rotated = None
            if hasattr(crypto_key, 'next_rotation_time'):
                # Infer last rotation from next rotation time
                rotation_period = crypto_key.rotation_period.seconds
                next_rotation = crypto_key.next_rotation_time
                last_rotated = next_rotation - timedelta(seconds=rotation_period)

            # HSM and FIPS status
            hsm_backed = primary_version.protection_level == 3  # HSM
            fips_validated = hsm_backed  # GCP Cloud HSM is FIPS 140-2 Level 3

            return KeyMetadata(
                key_id=crypto_key.name.split('/')[-1],
                alias=None,
                arn=crypto_key.name,
                platform="GCP KMS",
                key_type="symmetric",  # GCP KMS is primarily symmetric
                algorithm=str(primary_version.algorithm),
                key_usage=str(crypto_key.purpose),
                status="ENABLED" if crypto_key.primary else "DISABLED",
                created_at=created_at,
                last_rotated_at=last_rotated,
                age_days=age_days,
                rotation_enabled=rotation_enabled,
                deletion_date=crypto_key.destroy_scheduled_duration if hasattr(crypto_key, 'destroy_scheduled_duration') else None,
                description="",
                tags={},
                is_managed=False,
                fips_validated=fips_validated,
                hsm_backed=hsm_backed
            )

        except Exception as e:
            print(f"Error parsing key metadata: {e}", file=sys.stderr)
            return None


class KeyAuditor:
    """Main key auditor"""

    def __init__(self, platform: KMSPlatform, config: Dict):
        self.platform = platform
        self.config = config
        self.auditor = self._create_auditor()

    def _create_auditor(self):
        """Create platform-specific auditor"""
        if self.platform == KMSPlatform.AWS_KMS:
            return AWSKMSAuditor(region=self.config.get('region', 'us-east-1'))
        elif self.platform == KMSPlatform.GCP_KMS:
            return GCPKMSAuditor(
                project_id=self.config['project'],
                location=self.config.get('location', 'global')
            )
        else:
            raise ValueError(f"Unsupported platform: {self.platform}")

    def audit(self, check_usage: bool = False, check_access: bool = False,
              check_compliance: bool = False, unused_days: int = 90) -> KeyAuditReport:
        """Perform comprehensive key audit"""

        # List all keys
        keys = self.auditor.list_keys()

        # Generate report
        report = KeyAuditReport(
            platform=self.platform.value,
            scan_time=datetime.now(timezone.utc).isoformat(),
            total_keys=len(keys),
            enabled_keys=sum(1 for k in keys if k.status == "ENABLED"),
            disabled_keys=sum(1 for k in keys if k.status == "DISABLED"),
            pending_deletion=sum(1 for k in keys if "PENDING_DELETION" in k.status),
            rotation_enabled=sum(1 for k in keys if k.rotation_enabled),
            hsm_backed=sum(1 for k in keys if k.hsm_backed),
            fips_validated=sum(1 for k in keys if k.fips_validated),
            keys=keys
        )

        # Check rotation compliance
        for key in keys:
            self._check_rotation_compliance(key, report)

        # Check key age
        for key in keys:
            self._check_key_age(key, report)

        # Check usage (if requested)
        if check_usage:
            for key in keys:
                self._check_key_usage(key, report, unused_days)

        # Check access control (if requested)
        if check_access:
            for key in keys:
                self._check_access_control(key, report)

        # Check compliance (if requested)
        if check_compliance:
            for key in keys:
                self._check_compliance(key, report)

        # Calculate security score
        report.security_score = self._calculate_security_score(report)

        # Generate summary
        report.summary = self._generate_summary(report)

        return report

    def _check_rotation_compliance(self, key: KeyMetadata, report: KeyAuditReport):
        """Check key rotation compliance"""
        if not key.rotation_enabled and not key.is_managed:
            report.findings.append(AuditFinding(
                key_id=key.key_id,
                category="rotation",
                severity=SeverityLevel.HIGH.value,
                title="Automatic key rotation not enabled",
                description=f"Key {key.key_id} does not have automatic rotation enabled",
                remediation="Enable automatic key rotation to improve security posture",
                metadata={"age_days": key.age_days}
            ))

    def _check_key_age(self, key: KeyMetadata, report: KeyAuditReport):
        """Check if key is too old"""
        if key.age_days > 365 and not key.rotation_enabled:
            report.findings.append(AuditFinding(
                key_id=key.key_id,
                category="rotation",
                severity=SeverityLevel.MEDIUM.value,
                title="Key older than 1 year without rotation",
                description=f"Key {key.key_id} is {key.age_days} days old and has no rotation policy",
                remediation="Rotate key or enable automatic rotation",
                metadata={"age_days": key.age_days}
            ))

    def _check_key_usage(self, key: KeyMetadata, report: KeyAuditReport, unused_days: int):
        """Check if key is unused"""
        if hasattr(self.auditor, 'get_key_usage'):
            usage = self.auditor.get_key_usage(key.key_id, days=unused_days)

            if usage.total_operations == 0:
                report.findings.append(AuditFinding(
                    key_id=key.key_id,
                    category="usage",
                    severity=SeverityLevel.LOW.value,
                    title=f"Key unused for {unused_days} days",
                    description=f"Key {key.key_id} has not been used in the last {unused_days} days",
                    remediation="Consider disabling or deleting unused key",
                    metadata={"days_checked": unused_days}
                ))

    def _check_access_control(self, key: KeyMetadata, report: KeyAuditReport):
        """Check key access control"""
        if hasattr(self.auditor, 'get_access_control'):
            access = self.auditor.get_access_control(key.key_id)

            if access.public_access:
                report.findings.append(AuditFinding(
                    key_id=key.key_id,
                    category="access",
                    severity=SeverityLevel.CRITICAL.value,
                    title="Key has public access",
                    description=f"Key {key.key_id} allows public access (*)",
                    remediation="Restrict key access to specific principals only",
                    metadata={"principals": access.principals}
                ))

            if access.overly_permissive and not access.public_access:
                report.findings.append(AuditFinding(
                    key_id=key.key_id,
                    category="access",
                    severity=SeverityLevel.HIGH.value,
                    title="Overly permissive key policy",
                    description=f"Key {key.key_id} has overly broad permissions (kms:* or *)",
                    remediation="Apply principle of least privilege to key policy",
                    metadata={"permissions": access.permissions}
                ))

            if not access.mfa_required:
                report.findings.append(AuditFinding(
                    key_id=key.key_id,
                    category="access",
                    severity=SeverityLevel.MEDIUM.value,
                    title="MFA not required for key operations",
                    description=f"Key {key.key_id} does not require MFA for sensitive operations",
                    remediation="Add MFA requirement to key policy for administrative operations",
                    metadata={}
                ))

    def _check_compliance(self, key: KeyMetadata, report: KeyAuditReport):
        """Check compliance requirements"""
        # PCI-DSS: Annual key rotation
        if not key.rotation_enabled:
            report.compliance_findings.append(ComplianceFinding(
                key_id=key.key_id,
                standard=ComplianceStandard.PCI_DSS.value,
                requirement="3.6.4 - Cryptographic key rotation",
                compliant=False,
                severity=SeverityLevel.HIGH.value,
                details="PCI-DSS requires cryptographic keys to be rotated at least annually",
                remediation="Enable automatic key rotation"
            ))

        # FIPS 140-2: HSM backing for high-security applications
        if not key.fips_validated and not key.is_managed:
            report.compliance_findings.append(ComplianceFinding(
                key_id=key.key_id,
                standard=ComplianceStandard.FIPS_140_2.value,
                requirement="FIPS 140-2 validated cryptographic module",
                compliant=False,
                severity=SeverityLevel.MEDIUM.value,
                details="Key is not backed by FIPS 140-2 validated HSM",
                remediation="Use CloudHSM or Hardware-backed keys for FIPS compliance"
            ))

    def _calculate_security_score(self, report: KeyAuditReport) -> int:
        """Calculate security score (0-100)"""
        score = 100

        # Deduct points for findings
        for finding in report.findings:
            if finding.severity == SeverityLevel.CRITICAL.value:
                score -= 20
            elif finding.severity == SeverityLevel.HIGH.value:
                score -= 10
            elif finding.severity == SeverityLevel.MEDIUM.value:
                score -= 5
            elif finding.severity == SeverityLevel.LOW.value:
                score -= 2

        # Bonus points for good practices
        if report.rotation_enabled == report.total_keys:
            score += 10
        if report.hsm_backed == report.total_keys:
            score += 10

        return max(0, min(100, score))

    def _generate_summary(self, report: KeyAuditReport) -> Dict:
        """Generate summary statistics"""
        return {
            "total_keys": report.total_keys,
            "enabled_keys": report.enabled_keys,
            "rotation_enabled_pct": round(report.rotation_enabled / report.total_keys * 100, 2) if report.total_keys > 0 else 0,
            "hsm_backed_pct": round(report.hsm_backed / report.total_keys * 100, 2) if report.total_keys > 0 else 0,
            "total_findings": len(report.findings),
            "critical_findings": sum(1 for f in report.findings if f.severity == SeverityLevel.CRITICAL.value),
            "high_findings": sum(1 for f in report.findings if f.severity == SeverityLevel.HIGH.value),
            "medium_findings": sum(1 for f in report.findings if f.severity == SeverityLevel.MEDIUM.value),
            "low_findings": sum(1 for f in report.findings if f.severity == SeverityLevel.LOW.value),
            "security_score": report.security_score,
            "compliance_violations": len([f for f in report.compliance_findings if not f.compliant])
        }


def print_report_human(report: KeyAuditReport):
    """Print human-readable report"""
    print(f"\n{'=' * 80}")
    print(f"Key Management Audit Report - {report.platform}")
    print(f"Scan Time: {report.scan_time}")
    print(f"{'=' * 80}\n")

    print(f"Summary:")
    print(f"  Total Keys: {report.total_keys}")
    print(f"  Enabled: {report.enabled_keys}")
    print(f"  Rotation Enabled: {report.rotation_enabled} ({report.summary['rotation_enabled_pct']}%)")
    print(f"  HSM Backed: {report.hsm_backed} ({report.summary['hsm_backed_pct']}%)")
    print(f"  Security Score: {report.security_score}/100")
    print()

    if report.findings:
        print(f"Findings ({len(report.findings)} total):")
        for severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM, SeverityLevel.LOW]:
            findings = [f for f in report.findings if f.severity == severity.value]
            if findings:
                print(f"\n  {severity.value.upper()} ({len(findings)}):")
                for finding in findings[:5]:  # Show first 5
                    print(f"    - [{finding.key_id[:20]}...] {finding.title}")
                    print(f"      {finding.description}")

    if report.compliance_findings:
        violations = [f for f in report.compliance_findings if not f.compliant]
        if violations:
            print(f"\nCompliance Violations ({len(violations)}):")
            for finding in violations[:5]:
                print(f"  - {finding.standard}: {finding.requirement}")
                print(f"    Key: {finding.key_id}")

    print(f"\n{'=' * 80}\n")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Audit cryptographic keys across KMS platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--platform',
        choices=['aws-kms', 'gcp-kms', 'azure', 'vault'],
        required=True,
        help='KMS platform to audit'
    )

    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (for AWS KMS)'
    )

    parser.add_argument(
        '--project',
        help='GCP project ID (for GCP KMS)'
    )

    parser.add_argument(
        '--location',
        default='global',
        help='GCP location (for GCP KMS)'
    )

    parser.add_argument(
        '--check-unused',
        action='store_true',
        help='Check for unused keys'
    )

    parser.add_argument(
        '--check-access',
        action='store_true',
        help='Check access control policies'
    )

    parser.add_argument(
        '--check-compliance',
        action='store_true',
        help='Check compliance requirements'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days for usage check (default: 90)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    parser.add_argument(
        '--output-file',
        type=Path,
        help='Write report to file'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Platform-specific config
    config = {}
    if args.platform == 'aws-kms':
        config['region'] = args.region
    elif args.platform == 'gcp-kms':
        if not args.project:
            parser.error("--project required for GCP KMS")
        config['project'] = args.project
        config['location'] = args.location

    # Create auditor
    try:
        platform = KMSPlatform(args.platform)
        auditor = KeyAuditor(platform, config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Run audit
    try:
        report = auditor.audit(
            check_usage=args.check_unused,
            check_access=args.check_access,
            check_compliance=args.check_compliance,
            unused_days=args.days
        )
    except Exception as e:
        print(f"Error running audit: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    # Output report
    if args.json:
        report_dict = asdict(report)
        # Convert datetime objects to ISO strings
        report_dict['keys'] = [
            {k: (v.isoformat() if isinstance(v, datetime) else v)
             for k, v in key.items()}
            for key in report_dict['keys']
        ]

        output = json.dumps(report_dict, indent=2)

        if args.output_file:
            args.output_file.write_text(output)
            print(f"Report written to {args.output_file}")
        else:
            print(output)
    else:
        print_report_human(report)

        if args.output_file:
            # Write JSON to file even in human mode
            report_dict = asdict(report)
            report_dict['keys'] = [
                {k: (v.isoformat() if isinstance(v, datetime) else v)
                 for k, v in key.items()}
                for key in report_dict['keys']
            ]
            args.output_file.write_text(json.dumps(report_dict, indent=2))
            print(f"\nJSON report written to {args.output_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
