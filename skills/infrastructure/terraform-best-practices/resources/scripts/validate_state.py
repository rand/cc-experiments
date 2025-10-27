#!/usr/bin/env python3
"""
Terraform State Validator

Validates Terraform state file health, consistency, and detects potential issues.
Checks for orphaned resources, drift indicators, and state file integrity.

Usage:
    ./validate_state.py [OPTIONS]

Examples:
    ./validate_state.py
    ./validate_state.py --json
    ./validate_state.py --state-file custom.tfstate
    ./validate_state.py --remote --backend s3 --bucket my-bucket --key terraform.tfstate
    ./validate_state.py --check-drift --output report.json
"""

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


@dataclass
class ValidationIssue:
    """Represents a state validation issue"""
    severity: str
    category: str
    message: str
    resource: Optional[str] = None
    details: Optional[str] = None
    recommendation: Optional[str] = None


class StateValidator:
    """Validates Terraform state file"""

    def __init__(self, state_path: Optional[str] = None, use_remote: bool = False):
        self.state_path = state_path
        self.use_remote = use_remote
        self.issues: List[ValidationIssue] = []
        self.state_data: Optional[Dict] = None
        self.stats = {
            'resources': 0,
            'data_sources': 0,
            'modules': 0,
            'outputs': 0,
            'issues_by_severity': defaultdict(int),
            'issues_by_category': defaultdict(int)
        }

    def validate(self) -> List[ValidationIssue]:
        """Run all validation checks"""
        # Load state
        self._load_state()

        if not self.state_data:
            self._add_issue(
                'critical',
                'state',
                'Failed to load state file',
                recommendation='Check state file path and permissions'
            )
            return self.issues

        # Run checks
        self._check_state_version()
        self._check_state_integrity()
        self._check_resource_count()
        self._check_orphaned_resources()
        self._check_duplicate_resources()
        self._check_resource_dependencies()
        self._check_state_lineage()
        self._check_state_serial()
        self._check_sensitive_data()
        self._check_resource_modes()
        self._check_provider_versions()
        self._check_outputs()

        return self.issues

    def _load_state(self):
        """Load state from file or remote backend"""
        try:
            if self.use_remote:
                # Pull remote state
                result = subprocess.run(
                    ['terraform', 'state', 'pull'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.state_data = json.loads(result.stdout)
            else:
                # Load local state
                state_file = Path(self.state_path) if self.state_path else Path('terraform.tfstate')
                if not state_file.exists():
                    self._add_issue(
                        'critical',
                        'state',
                        f'State file not found: {state_file}',
                        recommendation='Run terraform init and terraform apply first'
                    )
                    return

                self.state_data = json.loads(state_file.read_text())

            # Collect stats
            if 'resources' in self.state_data:
                for resource in self.state_data['resources']:
                    if resource.get('mode') == 'managed':
                        self.stats['resources'] += len(resource.get('instances', []))
                    elif resource.get('mode') == 'data':
                        self.stats['data_sources'] += len(resource.get('instances', []))

                    if resource.get('module'):
                        self.stats['modules'] += 1

            if 'outputs' in self.state_data:
                self.stats['outputs'] = len(self.state_data['outputs'])

        except subprocess.CalledProcessError as e:
            self._add_issue(
                'critical',
                'state',
                f'Failed to pull remote state: {e.stderr}',
                recommendation='Check Terraform configuration and backend settings'
            )
        except json.JSONDecodeError as e:
            self._add_issue(
                'critical',
                'state',
                f'Invalid JSON in state file: {e}',
                recommendation='State file may be corrupted - restore from backup'
            )
        except Exception as e:
            self._add_issue(
                'critical',
                'state',
                f'Error loading state: {e}',
                recommendation='Check file permissions and Terraform installation'
            )

    def _check_state_version(self):
        """Check state file version compatibility"""
        version = self.state_data.get('version')
        terraform_version = self.state_data.get('terraform_version')

        if not version:
            self._add_issue(
                'high',
                'compatibility',
                'State file version not found',
                recommendation='State file may be corrupted'
            )
            return

        if version < 4:
            self._add_issue(
                'medium',
                'compatibility',
                f'Old state file version: {version}',
                details='State file version is outdated',
                recommendation='Consider upgrading Terraform version'
            )

        if terraform_version:
            self._add_issue(
                'info',
                'info',
                f'State created with Terraform {terraform_version}',
                details='State file metadata'
            )

    def _check_state_integrity(self):
        """Check state file structural integrity"""
        required_fields = ['version', 'terraform_version', 'serial', 'lineage']

        for field in required_fields:
            if field not in self.state_data:
                self._add_issue(
                    'high',
                    'integrity',
                    f'Missing required field: {field}',
                    recommendation='State file may be corrupted - restore from backup'
                )

        # Check resources structure
        if 'resources' in self.state_data:
            for resource in self.state_data['resources']:
                if 'type' not in resource:
                    self._add_issue(
                        'high',
                        'integrity',
                        'Resource missing type field',
                        resource=resource.get('name', 'unknown'),
                        recommendation='State file corruption detected'
                    )

                if 'instances' not in resource:
                    self._add_issue(
                        'medium',
                        'integrity',
                        'Resource missing instances',
                        resource=f"{resource.get('type')}.{resource.get('name')}",
                        recommendation='Resource may be improperly initialized'
                    )

    def _check_resource_count(self):
        """Check resource counts and warn about limits"""
        resource_count = self.stats['resources']

        if resource_count == 0:
            self._add_issue(
                'medium',
                'state',
                'No managed resources in state',
                details='State file contains no resources',
                recommendation='This may be expected for new infrastructure'
            )
        elif resource_count > 1000:
            self._add_issue(
                'medium',
                'performance',
                f'Large state file with {resource_count} resources',
                details='Consider splitting into multiple state files',
                recommendation='Use workspaces or separate state files for better performance'
            )

        self._add_issue(
            'info',
            'info',
            f'State contains {resource_count} managed resources and {self.stats["data_sources"]} data sources',
            details='Resource inventory'
        )

    def _check_orphaned_resources(self):
        """Check for orphaned resources"""
        # This would require comparing with actual Terraform configuration
        # For now, we'll check for resources without valid providers
        if 'resources' in self.state_data:
            for resource in self.state_data['resources']:
                provider = resource.get('provider')
                if not provider:
                    self._add_issue(
                        'high',
                        'resources',
                        'Resource without provider',
                        resource=f"{resource.get('type')}.{resource.get('name')}",
                        recommendation='Resource may be orphaned - verify configuration'
                    )

    def _check_duplicate_resources(self):
        """Check for duplicate resource addresses"""
        resource_addresses = defaultdict(int)

        if 'resources' in self.state_data:
            for resource in self.state_data['resources']:
                address = f"{resource.get('type')}.{resource.get('name')}"
                if resource.get('module'):
                    address = f"{resource['module']}.{address}"

                resource_addresses[address] += 1

        duplicates = {addr: count for addr, count in resource_addresses.items() if count > 1}

        if duplicates:
            for address, count in duplicates.items():
                self._add_issue(
                    'critical',
                    'resources',
                    f'Duplicate resource address: {address} (appears {count} times)',
                    resource=address,
                    recommendation='Remove duplicate resources from configuration'
                )

    def _check_resource_dependencies(self):
        """Check resource dependencies for cycles"""
        # Build dependency graph
        dependencies = defaultdict(set)

        if 'resources' in self.state_data:
            for resource in self.state_data['resources']:
                resource_addr = f"{resource.get('type')}.{resource.get('name')}"

                for instance in resource.get('instances', []):
                    deps = instance.get('dependencies', [])
                    dependencies[resource_addr].update(deps)

        # Simple cycle detection
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependencies.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        for node in dependencies:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    self._add_issue(
                        'high',
                        'dependencies',
                        'Circular dependency detected in state',
                        resource=node,
                        recommendation='Review resource dependencies in configuration'
                    )
                    break

    def _check_state_lineage(self):
        """Check state lineage for consistency"""
        lineage = self.state_data.get('lineage')

        if not lineage:
            self._add_issue(
                'medium',
                'state',
                'State lineage not found',
                details='Lineage tracks state file history',
                recommendation='This may indicate state file was manually created'
            )
        else:
            self._add_issue(
                'info',
                'info',
                f'State lineage: {lineage[:8]}...',
                details='Unique identifier for state file history'
            )

    def _check_state_serial(self):
        """Check state serial number"""
        serial = self.state_data.get('serial')

        if serial is None:
            self._add_issue(
                'high',
                'state',
                'State serial number missing',
                recommendation='State file may be corrupted'
            )
        elif serial == 0:
            self._add_issue(
                'info',
                'info',
                'State is new (serial: 0)',
                details='No operations have been performed yet'
            )
        elif serial > 10000:
            self._add_issue(
                'low',
                'state',
                f'High serial number: {serial}',
                details='Many operations have been performed',
                recommendation='Consider state file maintenance and cleanup'
            )
        else:
            self._add_issue(
                'info',
                'info',
                f'State serial: {serial}',
                details='Number of operations performed'
            )

    def _check_sensitive_data(self):
        """Check for potentially sensitive data in state"""
        sensitive_patterns = [
            'password', 'secret', 'api_key', 'private_key',
            'access_key', 'token', 'credential'
        ]

        state_str = json.dumps(self.state_data).lower()

        found_sensitive = []
        for pattern in sensitive_patterns:
            if pattern in state_str:
                found_sensitive.append(pattern)

        if found_sensitive:
            self._add_issue(
                'high',
                'security',
                f'Potentially sensitive data in state: {", ".join(found_sensitive)}',
                details='State file may contain sensitive information',
                recommendation='Ensure state file is encrypted and access is restricted'
            )

    def _check_resource_modes(self):
        """Check resource modes distribution"""
        modes = defaultdict(int)

        if 'resources' in self.state_data:
            for resource in self.state_data['resources']:
                mode = resource.get('mode', 'unknown')
                modes[mode] += 1

        for mode, count in modes.items():
            self._add_issue(
                'info',
                'info',
                f'Resources in {mode} mode: {count}',
                details='Resource mode distribution'
            )

    def _check_provider_versions(self):
        """Check provider versions in state"""
        providers = set()

        if 'resources' in self.state_data:
            for resource in self.state_data['resources']:
                provider = resource.get('provider')
                if provider:
                    providers.add(provider)

        if providers:
            self._add_issue(
                'info',
                'info',
                f'Providers in use: {len(providers)}',
                details=', '.join(sorted(providers))
            )

    def _check_outputs(self):
        """Check state outputs"""
        outputs = self.state_data.get('outputs', {})

        if not outputs:
            self._add_issue(
                'low',
                'outputs',
                'No outputs defined',
                recommendation='Consider defining outputs for important values'
            )
        else:
            self._add_issue(
                'info',
                'info',
                f'Outputs defined: {len(outputs)}',
                details=', '.join(outputs.keys())
            )

            # Check for sensitive outputs
            sensitive_outputs = [
                name for name, value in outputs.items()
                if value.get('sensitive', False)
            ]

            if sensitive_outputs:
                self._add_issue(
                    'info',
                    'security',
                    f'Sensitive outputs: {len(sensitive_outputs)}',
                    details=', '.join(sensitive_outputs)
                )

    def check_drift(self) -> bool:
        """Check for state drift (requires terraform plan)"""
        try:
            result = subprocess.run(
                ['terraform', 'plan', '-detailed-exitcode', '-no-color'],
                capture_output=True,
                text=True
            )

            # Exit codes:
            # 0 = no changes
            # 1 = error
            # 2 = changes detected
            if result.returncode == 2:
                self._add_issue(
                    'high',
                    'drift',
                    'State drift detected',
                    details='Infrastructure has drifted from state',
                    recommendation='Review changes and run terraform apply or terraform refresh'
                )
                return True
            elif result.returncode == 1:
                self._add_issue(
                    'critical',
                    'drift',
                    'Error checking for drift',
                    details=result.stderr,
                    recommendation='Fix configuration errors before checking drift'
                )
            else:
                self._add_issue(
                    'info',
                    'drift',
                    'No drift detected',
                    details='Infrastructure matches state'
                )
                return False

        except subprocess.CalledProcessError as e:
            self._add_issue(
                'critical',
                'drift',
                f'Failed to check drift: {e}',
                recommendation='Ensure terraform is installed and configuration is valid'
            )
            return False

    def _add_issue(
        self,
        severity: str,
        category: str,
        message: str,
        resource: Optional[str] = None,
        details: Optional[str] = None,
        recommendation: Optional[str] = None
    ):
        """Add validation issue"""
        issue = ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            resource=resource,
            details=details,
            recommendation=recommendation
        )
        self.issues.append(issue)
        self.stats['issues_by_severity'][severity] += 1
        self.stats['issues_by_category'][category] += 1

    def get_report(self) -> Dict[str, Any]:
        """Generate validation report"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'resources': self.stats['resources'],
                'data_sources': self.stats['data_sources'],
                'modules': self.stats['modules'],
                'outputs': self.stats['outputs'],
                'total_issues': len(self.issues),
                'by_severity': dict(self.stats['issues_by_severity']),
                'by_category': dict(self.stats['issues_by_category'])
            },
            'issues': [asdict(issue) for issue in self.issues]
        }


def format_table(report: Dict[str, Any]) -> str:
    """Format report as table"""
    output = []
    output.append("\n" + "=" * 100)
    output.append("TERRAFORM STATE VALIDATION REPORT")
    output.append("=" * 100)
    output.append(f"\nGenerated: {report['timestamp']}")

    # Summary
    summary = report['summary']
    output.append(f"\nState Summary:")
    output.append(f"  Resources: {summary['resources']}")
    output.append(f"  Data Sources: {summary['data_sources']}")
    output.append(f"  Modules: {summary['modules']}")
    output.append(f"  Outputs: {summary['outputs']}")

    output.append(f"\nValidation Summary:")
    output.append(f"  Total Issues: {summary['total_issues']}")

    output.append("\n  By Severity:")
    for sev in ['critical', 'high', 'medium', 'low', 'info']:
        count = summary['by_severity'].get(sev, 0)
        if count > 0:
            output.append(f"    {sev.upper()}: {count}")

    output.append("\n  By Category:")
    for cat, count in sorted(summary['by_category'].items()):
        output.append(f"    {cat}: {count}")

    # Issues
    issues = [i for i in report['issues'] if i['severity'] != 'info']

    if issues:
        output.append("\n" + "=" * 100)
        output.append("ISSUES")
        output.append("=" * 100)

        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        issues.sort(key=lambda x: severity_order.get(x['severity'], 99))

        for i, issue in enumerate(issues, 1):
            output.append(f"\n[{i}] {issue['severity'].upper()} - {issue['category']}")
            output.append(f"    Message: {issue['message']}")
            if issue.get('resource'):
                output.append(f"    Resource: {issue['resource']}")
            if issue.get('details'):
                output.append(f"    Details: {issue['details']}")
            if issue.get('recommendation'):
                output.append(f"    Fix: {issue['recommendation']}")

    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Validate Terraform state file health and consistency',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--state-file',
        help='Path to state file (default: terraform.tfstate)'
    )
    parser.add_argument(
        '--remote',
        action='store_true',
        help='Pull state from remote backend'
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
        '--check-drift',
        action='store_true',
        help='Check for state drift (runs terraform plan)'
    )

    args = parser.parse_args()

    # Run validation
    validator = StateValidator(
        state_path=args.state_file,
        use_remote=args.remote
    )

    try:
        validator.validate()

        if args.check_drift:
            validator.check_drift()

        report = validator.get_report()

        # Format output
        if args.json:
            output = json.dumps(report, indent=2)
        else:
            output = format_table(report)

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
