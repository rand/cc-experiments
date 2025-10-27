#!/usr/bin/env python3
"""
Terraform Code Analyzer

Analyzes Terraform code for common anti-patterns, security issues, and best practice violations.
Provides detailed reports with severity levels and recommendations.

Usage:
    ./analyze_terraform.py [OPTIONS] PATH

Examples:
    ./analyze_terraform.py .
    ./analyze_terraform.py --json terraform/
    ./analyze_terraform.py --severity high --format table .
    ./analyze_terraform.py --output report.json --json terraform/
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional


class Severity(Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Issue:
    """Represents a code issue"""
    severity: str
    category: str
    message: str
    file: str
    line: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None


class TerraformAnalyzer:
    """Analyzes Terraform code for anti-patterns and issues"""

    def __init__(self, path: str):
        self.path = Path(path)
        self.issues: List[Issue] = []
        self.stats = {
            'files_analyzed': 0,
            'issues_by_severity': defaultdict(int),
            'issues_by_category': defaultdict(int)
        }

    def analyze(self) -> List[Issue]:
        """Run all analysis checks"""
        if self.path.is_file():
            self._analyze_file(self.path)
        elif self.path.is_dir():
            for tf_file in self.path.rglob('*.tf'):
                self._analyze_file(tf_file)
        else:
            raise FileNotFoundError(f"Path not found: {self.path}")

        return self.issues

    def _analyze_file(self, file_path: Path):
        """Analyze a single Terraform file"""
        self.stats['files_analyzed'] += 1

        try:
            content = file_path.read_text()
            lines = content.split('\n')

            # Run all checks
            self._check_hardcoded_secrets(file_path, content, lines)
            self._check_security_groups(file_path, content, lines)
            self._check_encryption(file_path, content, lines)
            self._check_naming_conventions(file_path, content, lines)
            self._check_state_backend(file_path, content, lines)
            self._check_provider_versions(file_path, content, lines)
            self._check_count_vs_for_each(file_path, content, lines)
            self._check_dynamic_blocks(file_path, content, lines)
            self._check_data_source_usage(file_path, content, lines)
            self._check_tagging(file_path, content, lines)
            self._check_module_usage(file_path, content, lines)
            self._check_iam_policies(file_path, content, lines)
            self._check_public_access(file_path, content, lines)
            self._check_monitoring(file_path, content, lines)

        except Exception as e:
            self._add_issue(
                Severity.CRITICAL,
                "parsing",
                f"Failed to parse file: {e}",
                str(file_path)
            )

    def _check_hardcoded_secrets(self, file_path: Path, content: str, lines: List[str]):
        """Check for hardcoded secrets"""
        patterns = [
            (r'password\s*=\s*["\'](?!var\.|data\.|random_)[^"\']{3,}["\']', "Hardcoded password detected"),
            (r'secret\s*=\s*["\'](?!var\.|data\.|random_)[^"\']{3,}["\']', "Hardcoded secret detected"),
            (r'api_key\s*=\s*["\'](?!var\.|data\.|random_)[^"\']{3,}["\']', "Hardcoded API key detected"),
            (r'access_key\s*=\s*["\']AKIA[A-Z0-9]{16}["\']', "Hardcoded AWS access key detected"),
            (r'private_key\s*=\s*["\'](?!var\.|data\.|file\()[^"\']{20,}["\']', "Hardcoded private key detected"),
        ]

        for i, line in enumerate(lines, 1):
            for pattern, message in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self._add_issue(
                        Severity.CRITICAL,
                        "security",
                        message,
                        str(file_path),
                        i,
                        line.strip(),
                        "Use AWS Secrets Manager, SSM Parameter Store, or Vault for sensitive data"
                    )

    def _check_security_groups(self, file_path: Path, content: str, lines: List[str]):
        """Check for overly permissive security groups"""
        # Check for 0.0.0.0/0 ingress
        sg_blocks = re.finditer(r'resource\s+"aws_security_group"\s+"[^"]+"\s*\{([^}]+)\}', content, re.DOTALL)

        for match in sg_blocks:
            block = match.group(0)
            if re.search(r'ingress\s*\{[^}]*cidr_blocks\s*=\s*\[[^]]*"0\.0\.0\.0/0"', block, re.DOTALL):
                if not re.search(r'from_port\s*=\s*(80|443)', block):
                    line_num = content[:match.start()].count('\n') + 1
                    self._add_issue(
                        Severity.HIGH,
                        "security",
                        "Security group allows ingress from 0.0.0.0/0 on non-standard ports",
                        str(file_path),
                        line_num,
                        recommendation="Restrict ingress to specific IP ranges or security groups"
                    )

        # Check for unrestricted egress
        if re.search(r'protocol\s*=\s*"-1".*cidr_blocks\s*=\s*\[[^]]*"0\.0\.0\.0/0"', content, re.DOTALL):
            self._add_issue(
                Severity.MEDIUM,
                "security",
                "Security group allows unrestricted egress",
                str(file_path),
                recommendation="Consider restricting egress to required destinations only"
            )

    def _check_encryption(self, file_path: Path, content: str, lines: List[str]):
        """Check for encryption settings"""
        # S3 bucket without encryption
        if 'resource "aws_s3_bucket"' in content:
            if 'aws_s3_bucket_server_side_encryption_configuration' not in content:
                self._add_issue(
                    Severity.HIGH,
                    "security",
                    "S3 bucket may not have encryption enabled",
                    str(file_path),
                    recommendation="Add aws_s3_bucket_server_side_encryption_configuration resource"
                )

        # RDS without encryption
        rds_blocks = re.finditer(r'resource\s+"aws_db_instance"\s+"[^"]+"\s*\{([^}]+)\}', content, re.DOTALL)
        for match in rds_blocks:
            block = match.group(1)
            if 'storage_encrypted' not in block or 'storage_encrypted = false' in block:
                line_num = content[:match.start()].count('\n') + 1
                self._add_issue(
                    Severity.HIGH,
                    "security",
                    "RDS instance does not have storage encryption enabled",
                    str(file_path),
                    line_num,
                    recommendation="Set storage_encrypted = true"
                )

        # EBS without encryption
        ebs_blocks = re.finditer(r'resource\s+"aws_ebs_volume"\s+"[^"]+"\s*\{([^}]+)\}', content, re.DOTALL)
        for match in ebs_blocks:
            block = match.group(1)
            if 'encrypted' not in block or 'encrypted = false' in block:
                line_num = content[:match.start()].count('\n') + 1
                self._add_issue(
                    Severity.HIGH,
                    "security",
                    "EBS volume does not have encryption enabled",
                    str(file_path),
                    line_num,
                    recommendation="Set encrypted = true and specify kms_key_id"
                )

    def _check_naming_conventions(self, file_path: Path, content: str, lines: List[str]):
        """Check resource naming conventions"""
        # Check resource names
        resources = re.finditer(r'resource\s+"[^"]+"\s+"([^"]+)"', content)
        for match in resources:
            name = match.group(1)
            if not re.match(r'^[a-z][a-z0-9_]*$', name):
                line_num = content[:match.start()].count('\n') + 1
                self._add_issue(
                    Severity.LOW,
                    "naming",
                    f"Resource name '{name}' does not follow snake_case convention",
                    str(file_path),
                    line_num,
                    recommendation="Use lowercase letters, numbers, and underscores only"
                )

        # Check for single-letter names
        if re.search(r'resource\s+"[^"]+"\s+"[a-z]"\s*\{', content):
            self._add_issue(
                Severity.MEDIUM,
                "naming",
                "Resource uses single-letter name",
                str(file_path),
                recommendation="Use descriptive resource names"
            )

    def _check_state_backend(self, file_path: Path, content: str, lines: List[str]):
        """Check for remote state backend configuration"""
        if 'terraform {' in content:
            if 'backend' not in content:
                self._add_issue(
                    Severity.MEDIUM,
                    "state",
                    "No remote backend configured - using local state",
                    str(file_path),
                    recommendation="Configure remote backend (S3, Terraform Cloud, etc.)"
                )

            # Check for state locking
            if 'backend "s3"' in content:
                if 'dynamodb_table' not in content:
                    self._add_issue(
                        Severity.HIGH,
                        "state",
                        "S3 backend without DynamoDB locking",
                        str(file_path),
                        recommendation="Add dynamodb_table for state locking"
                    )
                if 'encrypt' not in content or 'encrypt = false' in content:
                    self._add_issue(
                        Severity.HIGH,
                        "state",
                        "S3 backend without encryption",
                        str(file_path),
                        recommendation="Set encrypt = true"
                    )

    def _check_provider_versions(self, file_path: Path, content: str, lines: List[str]):
        """Check provider version constraints"""
        if 'required_providers' in content:
            # Check for pinned versions (too strict)
            if re.search(r'version\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"', content):
                self._add_issue(
                    Severity.LOW,
                    "versioning",
                    "Provider version is pinned to exact version",
                    str(file_path),
                    recommendation="Consider using version constraints (~>, >=) for flexibility"
                )
        else:
            if 'provider' in content:
                self._add_issue(
                    Severity.MEDIUM,
                    "versioning",
                    "No provider version constraints specified",
                    str(file_path),
                    recommendation="Add required_providers block with version constraints"
                )

    def _check_count_vs_for_each(self, file_path: Path, content: str, lines: List[str]):
        """Check for count usage where for_each would be better"""
        count_blocks = re.finditer(r'resource\s+"[^"]+"\s+"[^"]+"\s*\{[^}]*count\s*=', content, re.DOTALL)

        for match in count_blocks:
            block = match.group(0)
            # If the resource uses count but references list indices, for_each might be better
            if re.search(r'\[count\.index\]', block):
                line_num = content[:match.start()].count('\n') + 1
                self._add_issue(
                    Severity.LOW,
                    "best-practices",
                    "Consider using for_each instead of count for better stability",
                    str(file_path),
                    line_num,
                    recommendation="Use for_each with maps to avoid resource recreation on list changes"
                )

    def _check_dynamic_blocks(self, file_path: Path, content: str, lines: List[str]):
        """Check for opportunities to use dynamic blocks"""
        # Look for repeated blocks that could be dynamic
        ingress_count = content.count('ingress {')
        egress_count = content.count('egress {')

        if ingress_count > 3:
            self._add_issue(
                Severity.LOW,
                "best-practices",
                f"Multiple ingress blocks ({ingress_count}) detected",
                str(file_path),
                recommendation="Consider using dynamic blocks for cleaner code"
            )

        if egress_count > 3:
            self._add_issue(
                Severity.LOW,
                "best-practices",
                f"Multiple egress blocks ({egress_count}) detected",
                str(file_path),
                recommendation="Consider using dynamic blocks for cleaner code"
            )

    def _check_data_source_usage(self, file_path: Path, content: str, lines: List[str]):
        """Check for hardcoded values that should use data sources"""
        # Check for hardcoded AMI IDs
        ami_matches = re.finditer(r'ami\s*=\s*"ami-[a-z0-9]+"', content)
        for match in ami_matches:
            line_num = content[:match.start()].count('\n') + 1
            self._add_issue(
                Severity.MEDIUM,
                "best-practices",
                "Hardcoded AMI ID",
                str(file_path),
                line_num,
                match.group(0),
                "Use aws_ami data source to fetch latest AMI dynamically"
            )

        # Check for hardcoded availability zones
        az_matches = re.finditer(r'availability_zone\s*=\s*"[a-z]+-[a-z]+-[0-9][a-z]"', content)
        for match in az_matches:
            line_num = content[:match.start()].count('\n') + 1
            self._add_issue(
                Severity.LOW,
                "best-practices",
                "Hardcoded availability zone",
                str(file_path),
                line_num,
                match.group(0),
                "Use aws_availability_zones data source"
            )

    def _check_tagging(self, file_path: Path, content: str, lines: List[str]):
        """Check for resource tagging"""
        resources = re.finditer(
            r'resource\s+"(aws_[^"]+)"\s+"[^"]+"\s*\{([^}]*)\}',
            content,
            re.DOTALL
        )

        taggable_resources = [
            'aws_instance', 'aws_vpc', 'aws_subnet', 'aws_security_group',
            'aws_ebs_volume', 'aws_db_instance', 'aws_s3_bucket',
            'aws_elb', 'aws_lb', 'aws_autoscaling_group'
        ]

        for match in resources:
            resource_type = match.group(1)
            resource_block = match.group(2)

            if resource_type in taggable_resources:
                if 'tags' not in resource_block and 'default_tags' not in content:
                    line_num = content[:match.start()].count('\n') + 1
                    self._add_issue(
                        Severity.MEDIUM,
                        "best-practices",
                        f"{resource_type} missing tags",
                        str(file_path),
                        line_num,
                        recommendation="Add tags for resource management and cost tracking"
                    )

    def _check_module_usage(self, file_path: Path, content: str, lines: List[str]):
        """Check for repeated code that should be modularized"""
        # Count similar resource blocks
        resource_types = re.findall(r'resource\s+"([^"]+)"', content)
        type_counts = defaultdict(int)

        for rt in resource_types:
            type_counts[rt] += 1

        for resource_type, count in type_counts.items():
            if count > 5:
                self._add_issue(
                    Severity.LOW,
                    "best-practices",
                    f"Multiple instances of {resource_type} ({count}) detected",
                    str(file_path),
                    recommendation="Consider creating a reusable module"
                )

    def _check_iam_policies(self, file_path: Path, content: str, lines: List[str]):
        """Check for overly permissive IAM policies"""
        # Check for wildcard actions
        policy_blocks = re.finditer(r'policy\s*=\s*jsonencode\(\{([^}]+)\}\)', content, re.DOTALL)

        for match in policy_blocks:
            policy = match.group(1)
            if '"Action": "*"' in policy or '"Action" = "*"' in policy:
                line_num = content[:match.start()].count('\n') + 1
                self._add_issue(
                    Severity.CRITICAL,
                    "security",
                    "IAM policy allows all actions (*)",
                    str(file_path),
                    line_num,
                    recommendation="Use specific actions following least privilege principle"
                )

            if '"Resource": "*"' in policy or '"Resource" = "*"' in policy:
                line_num = content[:match.start()].count('\n') + 1
                self._add_issue(
                    Severity.HIGH,
                    "security",
                    "IAM policy allows access to all resources (*)",
                    str(file_path),
                    line_num,
                    recommendation="Restrict to specific resource ARNs"
                )

    def _check_public_access(self, file_path: Path, content: str, lines: List[str]):
        """Check for publicly accessible resources"""
        # RDS publicly accessible
        if re.search(r'publicly_accessible\s*=\s*true', content):
            self._add_issue(
                Severity.CRITICAL,
                "security",
                "Database instance is publicly accessible",
                str(file_path),
                recommendation="Set publicly_accessible = false and access via VPN/bastion"
            )

        # S3 public ACLs
        if re.search(r'acl\s*=\s*"public-read', content):
            self._add_issue(
                Severity.HIGH,
                "security",
                "S3 bucket has public-read ACL",
                str(file_path),
                recommendation="Use restrictive ACLs and bucket policies"
            )

    def _check_monitoring(self, file_path: Path, content: str, lines: List[str]):
        """Check for monitoring and logging"""
        # Check for VPC Flow Logs
        if 'resource "aws_vpc"' in content:
            if 'aws_flow_log' not in content:
                self._add_issue(
                    Severity.MEDIUM,
                    "monitoring",
                    "VPC without flow logs",
                    str(file_path),
                    recommendation="Enable VPC flow logs for network monitoring"
                )

        # Check for CloudWatch logging
        if 'aws_db_instance' in content:
            if 'enabled_cloudwatch_logs_exports' not in content:
                self._add_issue(
                    Severity.LOW,
                    "monitoring",
                    "RDS instance without CloudWatch log exports",
                    str(file_path),
                    recommendation="Enable CloudWatch log exports for better observability"
                )

    def _add_issue(
        self,
        severity: Severity,
        category: str,
        message: str,
        file: str,
        line: Optional[int] = None,
        code_snippet: Optional[str] = None,
        recommendation: Optional[str] = None
    ):
        """Add an issue to the list"""
        issue = Issue(
            severity=severity.value,
            category=category,
            message=message,
            file=file,
            line=line,
            code_snippet=code_snippet,
            recommendation=recommendation
        )
        self.issues.append(issue)
        self.stats['issues_by_severity'][severity.value] += 1
        self.stats['issues_by_category'][category] += 1

    def get_report(self) -> Dict[str, Any]:
        """Generate analysis report"""
        return {
            'summary': {
                'files_analyzed': self.stats['files_analyzed'],
                'total_issues': len(self.issues),
                'by_severity': dict(self.stats['issues_by_severity']),
                'by_category': dict(self.stats['issues_by_category'])
            },
            'issues': [asdict(issue) for issue in self.issues]
        }


def format_table(report: Dict[str, Any], min_severity: Optional[str] = None) -> str:
    """Format report as table"""
    severity_order = {
        'critical': 0,
        'high': 1,
        'medium': 2,
        'low': 3,
        'info': 4
    }

    issues = report['issues']

    if min_severity:
        min_level = severity_order[min_severity]
        issues = [i for i in issues if severity_order[i['severity']] <= min_level]

    if not issues:
        return "No issues found!"

    # Sort by severity
    issues.sort(key=lambda x: severity_order[x['severity']])

    output = []
    output.append("\n" + "=" * 100)
    output.append("TERRAFORM CODE ANALYSIS REPORT")
    output.append("=" * 100)

    # Summary
    summary = report['summary']
    output.append(f"\nFiles Analyzed: {summary['files_analyzed']}")
    output.append(f"Total Issues: {summary['total_issues']}")
    output.append("\nBy Severity:")
    for sev in ['critical', 'high', 'medium', 'low', 'info']:
        count = summary['by_severity'].get(sev, 0)
        if count > 0:
            output.append(f"  {sev.upper()}: {count}")

    output.append("\nBy Category:")
    for cat, count in sorted(summary['by_category'].items()):
        output.append(f"  {cat}: {count}")

    # Issues
    output.append("\n" + "=" * 100)
    output.append("ISSUES")
    output.append("=" * 100)

    for i, issue in enumerate(issues, 1):
        output.append(f"\n[{i}] {issue['severity'].upper()} - {issue['category']}")
        output.append(f"    File: {issue['file']}")
        if issue.get('line'):
            output.append(f"    Line: {issue['line']}")
        output.append(f"    Message: {issue['message']}")
        if issue.get('code_snippet'):
            output.append(f"    Code: {issue['code_snippet']}")
        if issue.get('recommendation'):
            output.append(f"    Fix: {issue['recommendation']}")

    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Terraform code for anti-patterns and security issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'path',
        help='Path to Terraform file or directory'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Output file path'
    )
    parser.add_argument(
        '--severity',
        choices=['critical', 'high', 'medium', 'low', 'info'],
        help='Minimum severity level to report'
    )
    parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table)'
    )

    args = parser.parse_args()

    # Override format if --json is used
    if args.json:
        args.format = 'json'

    # Run analysis
    analyzer = TerraformAnalyzer(args.path)

    try:
        analyzer.analyze()
        report = analyzer.get_report()

        # Format output
        if args.format == 'json':
            output = json.dumps(report, indent=2)
        else:
            output = format_table(report, args.severity)

        # Write output
        if args.output:
            Path(args.output).write_text(output)
            print(f"Report written to {args.output}")
        else:
            print(output)

        # Exit code based on severity
        if report['summary']['by_severity'].get('critical', 0) > 0:
            sys.exit(2)
        elif report['summary']['by_severity'].get('high', 0) > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
