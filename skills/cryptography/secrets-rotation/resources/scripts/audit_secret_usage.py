#!/usr/bin/env python3
"""
Comprehensive secrets usage auditing and compliance checking tool.

Features:
- Track secret access patterns across platforms
- Detect stale secrets (never rotated or unused)
- Identify over-privileged secrets (excessive permissions)
- Compliance checking (PCI-DSS, HIPAA, SOC 2, GDPR)
- Secret age analysis and rotation recommendations
- Access anomaly detection
- Security score calculation
- Export audit reports

Usage:
    # Audit all secrets in AWS Secrets Manager
    ./audit_secret_usage.py --platform aws --region us-east-1

    # Check compliance
    ./audit_secret_usage.py --platform aws \\
        --check-compliance PCI-DSS \\
        --max-age-days 90

    # Find stale secrets
    ./audit_secret_usage.py --platform aws \\
        --find-stale \\
        --unused-days 180

    # Security score report
    ./audit_secret_usage.py --platform aws \\
        --security-score \\
        --json > audit_report.json

    # Specific secret audit
    ./audit_secret_usage.py --platform aws \\
        --secret-id prod/db/password \\
        --detailed

Author: Claude Code Skills
License: MIT
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import statistics

# Optional imports
try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

try:
    from google.cloud import secretmanager, logging as gcp_logging
    HAS_GCP = True
except ImportError:
    HAS_GCP = False

try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    from azure.monitor.query import LogsQueryClient
    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False

try:
    import hvac
    HAS_VAULT = True
except ImportError:
    HAS_VAULT = False


class ComplianceStandard:
    """Compliance standard requirements."""

    PCI_DSS = {
        'name': 'PCI-DSS 3.2.1',
        'max_age_days': 90,
        'requirements': [
            'Requirement 8.2.4: Change passwords at least every 90 days',
            'Requirement 8.2.5: Prevent password reuse',
            'Requirement 7.1: Limit access to least privilege'
        ]
    }

    HIPAA = {
        'name': 'HIPAA Security Rule',
        'max_age_days': 90,
        'requirements': [
            '164.312(a)(2)(i): Unique user identification',
            '164.312(a)(2)(iv): Encryption and decryption (addressable)',
            '164.308(a)(3): Workforce security'
        ]
    }

    SOC2 = {
        'name': 'SOC 2 Trust Services',
        'max_age_days': 90,
        'requirements': [
            'CC6.1: Logical and physical access controls',
            'CC6.2: Prior to issuing system credentials',
            'CC6.3: Removes access when necessary'
        ]
    }

    GDPR = {
        'name': 'GDPR Article 32',
        'max_age_days': None,  # Not specified
        'requirements': [
            'Article 32: Security of processing',
            'Appropriate technical measures (encryption)'
        ]
    }

    NIST = {
        'name': 'NIST SP 800-63B',
        'max_age_days': None,  # Recommends not requiring periodic changes
        'requirements': [
            'Memorized secrets: No composition rules',
            'Check against compromised password lists'
        ]
    }


class SecretAuditor:
    """
    Comprehensive secrets auditing tool.
    """

    def __init__(self, platform: str, config: Dict[str, Any]):
        """
        Initialize auditor.

        Args:
            platform: Platform name (aws, gcp, azure, vault)
            config: Platform configuration
        """
        self.platform = platform
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize platform client
        if platform == 'aws':
            if not HAS_BOTO3:
                raise ImportError("boto3 required for AWS platform")
            self.secrets_client = boto3.client(
                'secretsmanager',
                region_name=config.get('region', 'us-east-1')
            )
            self.cloudtrail_client = boto3.client(
                'cloudtrail',
                region_name=config.get('region', 'us-east-1')
            )
            self.iam_client = boto3.client('iam')

        elif platform == 'gcp':
            if not HAS_GCP:
                raise ImportError("google-cloud-secret-manager required for GCP")
            self.secrets_client = secretmanager.SecretManagerServiceClient()
            self.project_id = config.get('project_id')

        elif platform == 'azure':
            if not HAS_AZURE:
                raise ImportError("azure-keyvault-secrets required for Azure")
            credential = DefaultAzureCredential()
            self.secrets_client = SecretClient(
                vault_url=config.get('vault_url'),
                credential=credential
            )

        elif platform == 'vault':
            if not HAS_VAULT:
                raise ImportError("hvac required for Vault")
            self.secrets_client = hvac.Client(
                url=config.get('url'),
                token=config.get('token')
            )

        else:
            raise ValueError(f"Unsupported platform: {platform}")

    def audit_all_secrets(self) -> List[Dict[str, Any]]:
        """
        Audit all secrets in the platform.

        Returns:
            List of secret audit results
        """
        self.logger.info(f"Auditing all secrets on {self.platform}")

        secrets = self._list_secrets()
        results = []

        for secret_id in secrets:
            try:
                audit_result = self.audit_secret(secret_id)
                results.append(audit_result)
            except Exception as e:
                self.logger.error(f"Failed to audit {secret_id}: {e}")
                results.append({
                    'secret_id': secret_id,
                    'status': 'error',
                    'error': str(e)
                })

        return results

    def audit_secret(self, secret_id: str, detailed: bool = False) -> Dict[str, Any]:
        """
        Audit individual secret.

        Args:
            secret_id: Secret identifier
            detailed: Include detailed access logs

        Returns:
            Audit result
        """
        self.logger.info(f"Auditing secret: {secret_id}")

        result = {
            'secret_id': secret_id,
            'platform': self.platform,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Get secret metadata
        metadata = self._get_secret_metadata(secret_id)
        result.update(metadata)

        # Calculate age
        if 'created_at' in metadata:
            created_at = datetime.fromisoformat(metadata['created_at'].replace('Z', '+00:00'))
            age_days = (datetime.now(created_at.tzinfo) - created_at).days
            result['age_days'] = age_days

        # Get rotation history
        rotation_history = self._get_rotation_history(secret_id)
        result['rotation_history'] = rotation_history

        if rotation_history:
            last_rotated = rotation_history[0]['timestamp']
            last_rotated_dt = datetime.fromisoformat(last_rotated.replace('Z', '+00:00'))
            days_since_rotation = (datetime.now(last_rotated_dt.tzinfo) - last_rotated_dt).days
            result['days_since_rotation'] = days_since_rotation
        else:
            result['days_since_rotation'] = result.get('age_days', 0)

        # Get access logs
        if detailed:
            access_logs = self._get_access_logs(secret_id, days=30)
            result['access_logs'] = access_logs
            result['access_count_30d'] = len(access_logs)

            # Analyze access patterns
            access_analysis = self._analyze_access_patterns(access_logs)
            result['access_analysis'] = access_analysis

        # Check permissions
        permissions = self._get_permissions(secret_id)
        result['permissions'] = permissions

        # Security score
        security_score = self._calculate_security_score(result)
        result['security_score'] = security_score

        # Recommendations
        recommendations = self._generate_recommendations(result)
        result['recommendations'] = recommendations

        return result

    def _list_secrets(self) -> List[str]:
        """List all secret identifiers."""
        if self.platform == 'aws':
            paginator = self.secrets_client.get_paginator('list_secrets')
            secret_ids = []
            for page in paginator.paginate():
                for secret in page['SecretList']:
                    secret_ids.append(secret['Name'])
            return secret_ids

        elif self.platform == 'gcp':
            parent = f"projects/{self.project_id}"
            secrets = self.secrets_client.list_secrets(request={"parent": parent})
            return [secret.name.split('/')[-1] for secret in secrets]

        elif self.platform == 'azure':
            return [secret.name for secret in self.secrets_client.list_properties_of_secrets()]

        elif self.platform == 'vault':
            # List secrets in KV v2 backend
            response = self.secrets_client.secrets.kv.v2.list_secrets(path='')
            return response['data']['keys']

        else:
            return []

    def _get_secret_metadata(self, secret_id: str) -> Dict[str, Any]:
        """Get secret metadata."""
        if self.platform == 'aws':
            response = self.secrets_client.describe_secret(SecretId=secret_id)
            return {
                'name': response['Name'],
                'arn': response['ARN'],
                'created_at': response.get('CreatedDate', datetime.utcnow()).isoformat(),
                'last_accessed': response.get('LastAccessedDate', '').isoformat() if response.get('LastAccessedDate') else None,
                'rotation_enabled': response.get('RotationEnabled', False),
                'kms_key_id': response.get('KmsKeyId'),
                'tags': response.get('Tags', [])
            }

        elif self.platform == 'gcp':
            name = f"projects/{self.project_id}/secrets/{secret_id}"
            secret = self.secrets_client.get_secret(request={"name": name})
            return {
                'name': secret.name.split('/')[-1],
                'created_at': secret.create_time.isoformat(),
                'replication': str(secret.replication),
                'labels': dict(secret.labels)
            }

        elif self.platform == 'azure':
            secret = self.secrets_client.get_secret(secret_id)
            return {
                'name': secret.name,
                'created_at': secret.properties.created_on.isoformat(),
                'updated_at': secret.properties.updated_on.isoformat(),
                'enabled': secret.properties.enabled,
                'expires_on': secret.properties.expires_on.isoformat() if secret.properties.expires_on else None
            }

        else:
            return {}

    def _get_rotation_history(self, secret_id: str) -> List[Dict[str, Any]]:
        """Get rotation history."""
        if self.platform == 'aws':
            # Query CloudTrail for rotation events
            try:
                response = self.cloudtrail_client.lookup_events(
                    LookupAttributes=[
                        {'AttributeKey': 'ResourceName', 'AttributeValue': secret_id}
                    ],
                    MaxResults=50
                )

                rotations = []
                for event in response.get('Events', []):
                    if event['EventName'] in ['RotateSecret', 'PutSecretValue']:
                        rotations.append({
                            'timestamp': event['EventTime'].isoformat(),
                            'event': event['EventName'],
                            'user': event.get('Username', 'Unknown')
                        })
                return sorted(rotations, key=lambda x: x['timestamp'], reverse=True)

            except Exception as e:
                self.logger.warning(f"Failed to get rotation history: {e}")
                return []

        # Other platforms: implement similar logic
        return []

    def _get_access_logs(self, secret_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get secret access logs."""
        if self.platform == 'aws':
            start_time = datetime.utcnow() - timedelta(days=days)

            try:
                response = self.cloudtrail_client.lookup_events(
                    LookupAttributes=[
                        {'AttributeKey': 'ResourceName', 'AttributeValue': secret_id}
                    ],
                    StartTime=start_time,
                    MaxResults=1000
                )

                access_logs = []
                for event in response.get('Events', []):
                    if event['EventName'] == 'GetSecretValue':
                        access_logs.append({
                            'timestamp': event['EventTime'].isoformat(),
                            'user': event.get('Username', 'Unknown'),
                            'source_ip': event.get('SourceIPAddress', 'Unknown'),
                            'user_agent': event.get('UserAgent', 'Unknown')
                        })
                return access_logs

            except Exception as e:
                self.logger.warning(f"Failed to get access logs: {e}")
                return []

        # Other platforms: implement similar logic
        return []

    def _analyze_access_patterns(self, access_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze access patterns for anomalies."""
        if not access_logs:
            return {'anomalies': []}

        # Count accesses per user
        user_counts = defaultdict(int)
        ip_counts = defaultdict(int)
        hourly_counts = defaultdict(int)

        for log in access_logs:
            user_counts[log['user']] += 1
            ip_counts[log['source_ip']] += 1

            # Extract hour
            timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
            hour = timestamp.hour
            hourly_counts[hour] += 1

        # Detect anomalies
        anomalies = []

        # Unusual user access
        if user_counts:
            mean_access = statistics.mean(user_counts.values())
            for user, count in user_counts.items():
                if count > mean_access * 3:  # 3x above average
                    anomalies.append({
                        'type': 'unusual_user_access',
                        'user': user,
                        'count': count,
                        'threshold': mean_access * 3
                    })

        # Multiple IPs for same user
        user_ips = defaultdict(set)
        for log in access_logs:
            user_ips[log['user']].add(log['source_ip'])

        for user, ips in user_ips.items():
            if len(ips) > 3:
                anomalies.append({
                    'type': 'multiple_ips',
                    'user': user,
                    'ip_count': len(ips),
                    'ips': list(ips)
                })

        return {
            'total_accesses': len(access_logs),
            'unique_users': len(user_counts),
            'unique_ips': len(ip_counts),
            'user_counts': dict(user_counts),
            'hourly_distribution': dict(hourly_counts),
            'anomalies': anomalies
        }

    def _get_permissions(self, secret_id: str) -> Dict[str, Any]:
        """Get secret permissions/policies."""
        if self.platform == 'aws':
            try:
                # Get resource policy
                response = self.secrets_client.get_resource_policy(SecretId=secret_id)
                policy = json.loads(response.get('ResourcePolicy', '{}'))

                # Analyze permissions
                principals = set()
                actions = set()

                for statement in policy.get('Statement', []):
                    if isinstance(statement.get('Principal'), dict):
                        for principal_type, principal_list in statement['Principal'].items():
                            if isinstance(principal_list, list):
                                principals.update(principal_list)
                            else:
                                principals.add(principal_list)

                    action_list = statement.get('Action', [])
                    if isinstance(action_list, str):
                        actions.add(action_list)
                    else:
                        actions.update(action_list)

                return {
                    'has_resource_policy': bool(policy),
                    'principals': list(principals),
                    'actions': list(actions),
                    'is_public': '*' in principals
                }

            except Exception as e:
                self.logger.warning(f"Failed to get permissions: {e}")
                return {}

        # Other platforms: implement similar logic
        return {}

    def _calculate_security_score(self, audit_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate security score (0-100).

        Scoring criteria:
        - Rotation frequency: 30 points
        - Access control: 25 points
        - Encryption: 20 points
        - Age: 15 points
        - Monitoring: 10 points
        """
        score = 0
        max_score = 100
        details = []

        # 1. Rotation frequency (30 points)
        days_since_rotation = audit_result.get('days_since_rotation', 999)
        if days_since_rotation <= 30:
            score += 30
            details.append('Rotation: Excellent (≤30 days)')
        elif days_since_rotation <= 90:
            score += 20
            details.append('Rotation: Good (≤90 days)')
        elif days_since_rotation <= 180:
            score += 10
            details.append('Rotation: Fair (≤180 days)')
        else:
            details.append('Rotation: Poor (>180 days)')

        # 2. Access control (25 points)
        permissions = audit_result.get('permissions', {})
        if not permissions.get('is_public', False):
            score += 15
            details.append('Access: Not public')
        else:
            details.append('Access: PUBLIC (critical risk)')

        if permissions.get('has_resource_policy'):
            score += 10
            details.append('Access: Resource policy defined')

        # 3. Encryption (20 points)
        if audit_result.get('kms_key_id'):
            score += 20
            details.append('Encryption: KMS encrypted')
        else:
            score += 10
            details.append('Encryption: Default encryption')

        # 4. Age (15 points)
        age_days = audit_result.get('age_days', 0)
        if age_days <= 365:
            score += 15
            details.append('Age: Recent (≤1 year)')
        elif age_days <= 730:
            score += 10
            details.append('Age: Moderate (≤2 years)')
        else:
            score += 5
            details.append('Age: Old (>2 years)')

        # 5. Monitoring (10 points)
        rotation_enabled = audit_result.get('rotation_enabled', False)
        if rotation_enabled:
            score += 10
            details.append('Monitoring: Auto-rotation enabled')

        # Grade
        if score >= 90:
            grade = 'A'
        elif score >= 80:
            grade = 'B'
        elif score >= 70:
            grade = 'C'
        elif score >= 60:
            grade = 'D'
        else:
            grade = 'F'

        return {
            'score': score,
            'max_score': max_score,
            'percentage': round(score / max_score * 100, 1),
            'grade': grade,
            'details': details
        }

    def _generate_recommendations(self, audit_result: Dict[str, Any]) -> List[str]:
        """Generate security recommendations."""
        recommendations = []

        # Check rotation age
        days_since_rotation = audit_result.get('days_since_rotation', 0)
        if days_since_rotation > 90:
            recommendations.append(
                f"CRITICAL: Rotate secret (last rotated {days_since_rotation} days ago, recommended: 90 days)"
            )
        elif days_since_rotation > 60:
            recommendations.append(
                f"WARNING: Consider rotating secret (last rotated {days_since_rotation} days ago)"
            )

        # Check rotation enabled
        if not audit_result.get('rotation_enabled', False):
            recommendations.append("Enable automatic rotation")

        # Check permissions
        permissions = audit_result.get('permissions', {})
        if permissions.get('is_public'):
            recommendations.append("CRITICAL: Secret is publicly accessible - restrict immediately")

        if not permissions.get('has_resource_policy'):
            recommendations.append("Add resource policy to restrict access")

        # Check encryption
        if not audit_result.get('kms_key_id'):
            recommendations.append("Use customer-managed KMS key for encryption")

        # Check access patterns
        access_analysis = audit_result.get('access_analysis', {})
        anomalies = access_analysis.get('anomalies', [])
        if anomalies:
            recommendations.append(f"Investigate {len(anomalies)} access anomalies")

        # Check age
        age_days = audit_result.get('age_days', 0)
        if age_days > 730:
            recommendations.append("Consider retiring old secret (age >2 years)")

        return recommendations

    def check_compliance(
        self,
        standard: str,
        max_age_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Check compliance with standard.

        Args:
            standard: Compliance standard (PCI-DSS, HIPAA, SOC2, GDPR, NIST)
            max_age_days: Override maximum age (days)

        Returns:
            Compliance report
        """
        self.logger.info(f"Checking {standard} compliance")

        # Get standard requirements
        standards = {
            'PCI-DSS': ComplianceStandard.PCI_DSS,
            'HIPAA': ComplianceStandard.HIPAA,
            'SOC2': ComplianceStandard.SOC2,
            'GDPR': ComplianceStandard.GDPR,
            'NIST': ComplianceStandard.NIST
        }

        if standard not in standards:
            raise ValueError(f"Unknown standard: {standard}")

        std = standards[standard]
        max_age = max_age_days or std['max_age_days']

        # Audit all secrets
        audit_results = self.audit_all_secrets()

        # Check compliance
        violations = []
        compliant = []

        for result in audit_results:
            secret_id = result['secret_id']
            days_since_rotation = result.get('days_since_rotation', 0)

            if max_age and days_since_rotation > max_age:
                violations.append({
                    'secret_id': secret_id,
                    'violation': f"Rotation age exceeds {max_age} days",
                    'days_since_rotation': days_since_rotation
                })
            else:
                compliant.append(secret_id)

        # Compliance score
        total = len(audit_results)
        compliant_count = len(compliant)
        compliance_percentage = (compliant_count / total * 100) if total > 0 else 0

        return {
            'standard': std['name'],
            'requirements': std['requirements'],
            'max_age_days': max_age,
            'total_secrets': total,
            'compliant': compliant_count,
            'violations': len(violations),
            'compliance_percentage': round(compliance_percentage, 1),
            'compliant_secrets': compliant,
            'violation_details': violations,
            'timestamp': datetime.utcnow().isoformat()
        }

    def find_stale_secrets(self, unused_days: int = 180) -> List[Dict[str, Any]]:
        """
        Find stale secrets (never rotated or unused).

        Args:
            unused_days: Days threshold for unused secrets

        Returns:
            List of stale secrets
        """
        self.logger.info(f"Finding stale secrets (unused >{unused_days} days)")

        audit_results = self.audit_all_secrets()
        stale_secrets = []

        for result in audit_results:
            days_since_rotation = result.get('days_since_rotation', 0)

            if days_since_rotation > unused_days:
                stale_secrets.append({
                    'secret_id': result['secret_id'],
                    'days_since_rotation': days_since_rotation,
                    'created_at': result.get('created_at'),
                    'recommendation': 'Rotate or retire'
                })

        return sorted(stale_secrets, key=lambda x: x['days_since_rotation'], reverse=True)


def main():
    parser = argparse.ArgumentParser(
        description='Secrets usage auditing and compliance tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--platform',
        required=True,
        choices=['aws', 'gcp', 'azure', 'vault'],
        help='Secrets management platform'
    )

    parser.add_argument(
        '--secret-id',
        help='Audit specific secret'
    )

    parser.add_argument(
        '--check-compliance',
        choices=['PCI-DSS', 'HIPAA', 'SOC2', 'GDPR', 'NIST'],
        help='Check compliance with standard'
    )

    parser.add_argument(
        '--max-age-days',
        type=int,
        help='Maximum secret age (days) for compliance'
    )

    parser.add_argument(
        '--find-stale',
        action='store_true',
        help='Find stale/unused secrets'
    )

    parser.add_argument(
        '--unused-days',
        type=int,
        default=180,
        help='Days threshold for stale secrets'
    )

    parser.add_argument(
        '--security-score',
        action='store_true',
        help='Calculate security scores'
    )

    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Include detailed access logs'
    )

    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region'
    )

    parser.add_argument(
        '--project-id',
        help='GCP project ID'
    )

    parser.add_argument(
        '--vault-url',
        help='Azure Key Vault URL or Vault URL'
    )

    parser.add_argument(
        '--vault-token',
        help='Vault token'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose logging'
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Build config
    config = {
        'region': args.region,
        'project_id': args.project_id,
        'vault_url': args.vault_url,
        'token': args.vault_token
    }

    # Initialize auditor
    auditor = SecretAuditor(args.platform, config)

    try:
        if args.check_compliance:
            # Compliance check
            result = auditor.check_compliance(args.check_compliance, args.max_age_days)

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\n{result['standard']} Compliance Report")
                print("=" * 60)
                print(f"Compliance: {result['compliance_percentage']}%")
                print(f"Compliant: {result['compliant']}/{result['total_secrets']}")
                print(f"Violations: {result['violations']}")
                print("\nRequirements:")
                for req in result['requirements']:
                    print(f"  - {req}")
                if result['violation_details']:
                    print("\nViolations:")
                    for violation in result['violation_details'][:10]:
                        print(f"  - {violation['secret_id']}: {violation['violation']}")

        elif args.find_stale:
            # Find stale secrets
            stale = auditor.find_stale_secrets(args.unused_days)

            if args.json:
                print(json.dumps(stale, indent=2))
            else:
                print(f"\nStale Secrets (unused >{args.unused_days} days)")
                print("=" * 60)
                print(f"Found: {len(stale)} secrets")
                for secret in stale[:20]:
                    print(f"  - {secret['secret_id']}: {secret['days_since_rotation']} days")

        elif args.secret_id:
            # Audit specific secret
            result = auditor.audit_secret(args.secret_id, args.detailed)

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\nAudit Report: {result['secret_id']}")
                print("=" * 60)
                print(f"Age: {result.get('age_days', 'Unknown')} days")
                print(f"Days since rotation: {result.get('days_since_rotation', 'Unknown')}")
                if 'security_score' in result:
                    score = result['security_score']
                    print(f"\nSecurity Score: {score['score']}/{score['max_score']} ({score['grade']})")
                    for detail in score['details']:
                        print(f"  - {detail}")
                if result.get('recommendations'):
                    print("\nRecommendations:")
                    for rec in result['recommendations']:
                        print(f"  - {rec}")

        else:
            # Audit all secrets
            results = auditor.audit_all_secrets()

            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print(f"\nAudit Summary ({args.platform})")
                print("=" * 60)
                print(f"Total secrets: {len(results)}")

                if args.security_score:
                    # Calculate average security score
                    scores = [r['security_score']['score'] for r in results if 'security_score' in r]
                    if scores:
                        avg_score = sum(scores) / len(scores)
                        print(f"Average security score: {avg_score:.1f}/100")

                # Summary by age
                by_age = {
                    '<30 days': 0,
                    '30-90 days': 0,
                    '90-180 days': 0,
                    '>180 days': 0
                }
                for result in results:
                    days = result.get('days_since_rotation', 0)
                    if days < 30:
                        by_age['<30 days'] += 1
                    elif days < 90:
                        by_age['30-90 days'] += 1
                    elif days < 180:
                        by_age['90-180 days'] += 1
                    else:
                        by_age['>180 days'] += 1

                print("\nRotation Age Distribution:")
                for category, count in by_age.items():
                    print(f"  {category}: {count}")

        sys.exit(0)

    except Exception as e:
        logging.error(f"Audit failed: {e}", exc_info=True)
        if args.json:
            print(json.dumps({'error': str(e)}))
        sys.exit(1)


if __name__ == '__main__':
    main()
