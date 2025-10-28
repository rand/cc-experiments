#!/usr/bin/env python3
"""
Deployment Configuration Validator

Validates deployment configuration files for common issues, best practices,
and security concerns across multiple deployment types (Kubernetes, ECS,
Lambda, etc.).

Usage:
    ./validate_deployment.py [OPTIONS]

Examples:
    ./validate_deployment.py --file deployment.yaml
    ./validate_deployment.py --file deployment.yaml --json
    ./validate_deployment.py --directory k8s/ --type kubernetes
    ./validate_deployment.py --file task-definition.json --type ecs
    ./validate_deployment.py --check-all
"""

import argparse
import json
import sys
import yaml
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any, Optional


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    severity: str  # 'critical', 'warning', 'info'
    category: str  # 'security', 'availability', 'performance', 'best-practice'
    message: str
    file: str
    resource: Optional[str] = None
    line: Optional[int] = None
    recommendation: Optional[str] = None


class DeploymentValidator:
    """Validates deployment configurations"""

    def __init__(self, deployment_type: Optional[str] = None):
        self.deployment_type = deployment_type
        self.issues: List[ValidationIssue] = []
        self.stats = {
            'files_checked': 0,
            'resources_validated': 0,
            'issues_by_severity': defaultdict(int),
            'issues_by_category': defaultdict(int)
        }

    def validate_file(self, file_path: Path) -> List[ValidationIssue]:
        """Validate a deployment configuration file"""
        self.stats['files_checked'] += 1

        try:
            # Load file
            with open(file_path) as f:
                if file_path.suffix in ['.yaml', '.yml']:
                    docs = list(yaml.safe_load_all(f))
                elif file_path.suffix == '.json':
                    docs = [json.load(f)]
                else:
                    self._add_issue(
                        'warning',
                        'best-practice',
                        f'Unknown file type: {file_path.suffix}',
                        str(file_path)
                    )
                    return self.issues

            # Detect deployment type if not specified
            if not self.deployment_type:
                self.deployment_type = self._detect_deployment_type(docs)

            # Validate based on type
            for doc in docs:
                if not doc:
                    continue

                if self.deployment_type == 'kubernetes':
                    self._validate_kubernetes(doc, str(file_path))
                elif self.deployment_type == 'ecs':
                    self._validate_ecs(doc, str(file_path))
                elif self.deployment_type == 'cloudformation':
                    self._validate_cloudformation(doc, str(file_path))
                elif self.deployment_type == 'terraform':
                    self._validate_terraform(doc, str(file_path))
                else:
                    self._validate_generic(doc, str(file_path))

        except Exception as e:
            self._add_issue(
                'critical',
                'best-practice',
                f'Failed to parse file: {str(e)}',
                str(file_path)
            )

        return self.issues

    def _detect_deployment_type(self, docs: List[Dict]) -> str:
        """Auto-detect deployment configuration type"""
        for doc in docs:
            if not isinstance(doc, dict):
                continue

            # Kubernetes
            if 'apiVersion' in doc and 'kind' in doc:
                return 'kubernetes'

            # ECS Task Definition
            if 'family' in doc and 'containerDefinitions' in doc:
                return 'ecs'

            # CloudFormation
            if 'AWSTemplateFormatVersion' in doc or 'Resources' in doc:
                return 'cloudformation'

            # Terraform
            if 'terraform' in doc or 'resource' in doc or 'provider' in doc:
                return 'terraform'

        return 'generic'

    def _validate_kubernetes(self, doc: Dict, file_path: str):
        """Validate Kubernetes manifest"""
        kind = doc.get('kind', '')
        name = doc.get('metadata', {}).get('name', 'unknown')

        self.stats['resources_validated'] += 1

        if kind == 'Deployment':
            self._validate_k8s_deployment(doc, file_path, name)
        elif kind == 'Service':
            self._validate_k8s_service(doc, file_path, name)
        elif kind == 'Pod':
            self._validate_k8s_pod(doc, file_path, name)

    def _validate_k8s_deployment(self, doc: Dict, file_path: str, name: str):
        """Validate Kubernetes Deployment"""
        spec = doc.get('spec', {})
        template = spec.get('template', {})
        pod_spec = template.get('spec', {})
        containers = pod_spec.get('containers', [])

        # Check replicas
        replicas = spec.get('replicas', 1)
        if replicas < 2:
            self._add_issue(
                'warning',
                'availability',
                f'Low replica count: {replicas}',
                file_path,
                name,
                recommendation='Use at least 2 replicas for high availability'
            )

        # Check strategy
        strategy = spec.get('strategy', {})
        strategy_type = strategy.get('type', 'RollingUpdate')

        if strategy_type == 'RollingUpdate':
            rolling_update = strategy.get('rollingUpdate', {})
            max_unavailable = rolling_update.get('maxUnavailable')
            max_surge = rolling_update.get('maxSurge')

            if max_unavailable and str(max_unavailable).endswith('%'):
                unavail_pct = int(max_unavailable.rstrip('%'))
                if unavail_pct > 50:
                    self._add_issue(
                        'warning',
                        'availability',
                        f'High maxUnavailable: {max_unavailable}',
                        file_path,
                        name,
                        recommendation='Keep maxUnavailable ≤ 50% to maintain availability'
                    )

            if not max_surge:
                self._add_issue(
                    'info',
                    'best-practice',
                    'maxSurge not specified (defaults to 25%)',
                    file_path,
                    name,
                    recommendation='Explicitly set maxSurge for clarity'
                )

        # Validate containers
        for i, container in enumerate(containers):
            self._validate_k8s_container(container, file_path, f"{name}/container[{i}]")

        # Check pod disruption budget
        if replicas >= 2:
            # Note: Can't validate PDB exists from deployment alone
            self._add_issue(
                'info',
                'availability',
                'Consider adding PodDisruptionBudget for this deployment',
                file_path,
                name,
                recommendation='PDBs prevent too many pods from being disrupted simultaneously'
            )

    def _validate_k8s_container(self, container: Dict, file_path: str, resource: str):
        """Validate Kubernetes container spec"""
        name = container.get('name', 'unknown')
        image = container.get('image', '')

        # Check image tag
        if not image:
            self._add_issue(
                'critical',
                'best-practice',
                'No image specified',
                file_path,
                resource
            )
        elif ':' not in image:
            self._add_issue(
                'warning',
                'best-practice',
                'Image has no tag (will use :latest)',
                file_path,
                resource,
                recommendation='Always specify explicit image tags'
            )
        elif image.endswith(':latest'):
            self._add_issue(
                'warning',
                'best-practice',
                'Using :latest tag',
                file_path,
                resource,
                recommendation='Use specific version tags for reproducibility'
            )

        # Check resource limits
        resources = container.get('resources', {})
        limits = resources.get('limits', {})
        requests = resources.get('requests', {})

        if not limits:
            self._add_issue(
                'warning',
                'performance',
                'No resource limits set',
                file_path,
                resource,
                recommendation='Set CPU and memory limits to prevent resource exhaustion'
            )

        if not requests:
            self._add_issue(
                'warning',
                'performance',
                'No resource requests set',
                file_path,
                resource,
                recommendation='Set resource requests for proper scheduling'
            )

        # Check probes
        liveness_probe = container.get('livenessProbe')
        readiness_probe = container.get('readinessProbe')

        if not liveness_probe:
            self._add_issue(
                'warning',
                'availability',
                'No liveness probe configured',
                file_path,
                resource,
                recommendation='Add liveness probe to detect and restart unhealthy containers'
            )

        if not readiness_probe:
            self._add_issue(
                'critical',
                'availability',
                'No readiness probe configured',
                file_path,
                resource,
                recommendation='Readiness probes are essential for zero-downtime deployments'
            )

        # Check security context
        security_context = container.get('securityContext', {})

        if security_context.get('privileged'):
            self._add_issue(
                'critical',
                'security',
                'Container runs in privileged mode',
                file_path,
                resource,
                recommendation='Avoid privileged containers unless absolutely necessary'
            )

        if not security_context.get('runAsNonRoot'):
            self._add_issue(
                'warning',
                'security',
                'Container may run as root',
                file_path,
                resource,
                recommendation='Set runAsNonRoot: true and specify runAsUser'
            )

        if not security_context.get('readOnlyRootFilesystem'):
            self._add_issue(
                'info',
                'security',
                'Root filesystem is writable',
                file_path,
                resource,
                recommendation='Consider setting readOnlyRootFilesystem: true'
            )

        # Check environment variables
        env = container.get('env', [])
        for env_var in env:
            if 'value' in env_var:
                value = str(env_var.get('value', ''))
                var_name = env_var.get('name', '')

                # Check for potential secrets in plain text
                if any(keyword in var_name.lower() for keyword in ['password', 'secret', 'token', 'key', 'api_key']):
                    self._add_issue(
                        'critical',
                        'security',
                        f'Potential secret in plain text env var: {var_name}',
                        file_path,
                        resource,
                        recommendation='Use Secrets instead of plain text environment variables'
                    )

    def _validate_k8s_service(self, doc: Dict, file_path: str, name: str):
        """Validate Kubernetes Service"""
        spec = doc.get('spec', {})
        service_type = spec.get('type', 'ClusterIP')

        # Check for NodePort
        if service_type == 'NodePort':
            self._add_issue(
                'warning',
                'security',
                'Service uses NodePort type',
                file_path,
                name,
                recommendation='Consider using LoadBalancer or Ingress instead'
            )

        # Check for LoadBalancer without annotations
        if service_type == 'LoadBalancer':
            metadata = doc.get('metadata', {})
            annotations = metadata.get('annotations', {})

            if not annotations:
                self._add_issue(
                    'info',
                    'best-practice',
                    'LoadBalancer service without annotations',
                    file_path,
                    name,
                    recommendation='Add cloud provider annotations for advanced features'
                )

        # Check session affinity
        session_affinity = spec.get('sessionAffinity')
        if session_affinity == 'ClientIP':
            self._add_issue(
                'info',
                'best-practice',
                'Service uses session affinity',
                file_path,
                name,
                recommendation='Ensure this is intentional; can affect load distribution'
            )

    def _validate_k8s_pod(self, doc: Dict, file_path: str, name: str):
        """Validate Kubernetes Pod"""
        self._add_issue(
            'warning',
            'best-practice',
            'Bare Pod detected (not managed by Deployment/StatefulSet)',
            file_path,
            name,
            recommendation='Use Deployment or StatefulSet for better management'
        )

    def _validate_ecs(self, doc: Dict, file_path: str):
        """Validate ECS task definition"""
        family = doc.get('family', 'unknown')
        self.stats['resources_validated'] += 1

        # Check network mode
        network_mode = doc.get('networkMode', 'bridge')
        if network_mode == 'host':
            self._add_issue(
                'warning',
                'security',
                'Using host network mode',
                file_path,
                family,
                recommendation='Use awsvpc network mode for better isolation'
            )

        # Check task role
        task_role_arn = doc.get('taskRoleArn')
        if not task_role_arn:
            self._add_issue(
                'warning',
                'security',
                'No task role specified',
                file_path,
                family,
                recommendation='Assign IAM task role for least privilege access'
            )

        # Validate containers
        containers = doc.get('containerDefinitions', [])
        for i, container in enumerate(containers):
            self._validate_ecs_container(container, file_path, f"{family}/container[{i}]")

    def _validate_ecs_container(self, container: Dict, file_path: str, resource: str):
        """Validate ECS container definition"""

        # Check health check
        health_check = container.get('healthCheck')
        if not health_check:
            self._add_issue(
                'warning',
                'availability',
                'No health check configured',
                file_path,
                resource,
                recommendation='Add health check for container health monitoring'
            )

        # Check logging
        log_configuration = container.get('logConfiguration')
        if not log_configuration:
            self._add_issue(
                'warning',
                'best-practice',
                'No log configuration specified',
                file_path,
                resource,
                recommendation='Configure logging for observability'
            )

        # Check privileged mode
        if container.get('privileged'):
            self._add_issue(
                'critical',
                'security',
                'Container runs in privileged mode',
                file_path,
                resource,
                recommendation='Avoid privileged mode unless absolutely necessary'
            )

        # Check environment variables for secrets
        environment = container.get('environment', [])
        for env in environment:
            name = env.get('name', '')
            if any(keyword in name.lower() for keyword in ['password', 'secret', 'token', 'key', 'api_key']):
                self._add_issue(
                    'critical',
                    'security',
                    f'Potential secret in plain text env var: {name}',
                    file_path,
                    resource,
                    recommendation='Use secrets in Systems Manager Parameter Store or Secrets Manager'
                )

    def _validate_cloudformation(self, doc: Dict, file_path: str):
        """Validate CloudFormation template"""
        resources = doc.get('Resources', {})

        for resource_name, resource_config in resources.items():
            self.stats['resources_validated'] += 1
            resource_type = resource_config.get('Type', '')

            if resource_type == 'AWS::EC2::SecurityGroup':
                self._validate_security_group(resource_config, file_path, resource_name)
            elif resource_type == 'AWS::IAM::Role':
                self._validate_iam_role(resource_config, file_path, resource_name)

    def _validate_security_group(self, resource: Dict, file_path: str, name: str):
        """Validate EC2 Security Group"""
        properties = resource.get('Properties', {})
        ingress_rules = properties.get('SecurityGroupIngress', [])

        for rule in ingress_rules:
            cidr = rule.get('CidrIp', '')
            if cidr == '0.0.0.0/0':
                from_port = rule.get('FromPort', '')
                to_port = rule.get('ToPort', '')

                self._add_issue(
                    'critical',
                    'security',
                    f'Security group allows 0.0.0.0/0 on port(s) {from_port}-{to_port}',
                    file_path,
                    name,
                    recommendation='Restrict ingress to specific CIDR blocks'
                )

    def _validate_iam_role(self, resource: Dict, file_path: str, name: str):
        """Validate IAM Role"""
        properties = resource.get('Properties', {})
        policies = properties.get('Policies', [])

        for policy in policies:
            policy_doc = policy.get('PolicyDocument', {})
            statements = policy_doc.get('Statement', [])

            for statement in statements:
                if not isinstance(statement, dict):
                    continue

                actions = statement.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]

                resources = statement.get('Resource', [])
                if isinstance(resources, str):
                    resources = [resources]

                # Check for wildcards
                if '*' in actions or any('*' in action for action in actions):
                    if '*' in resources:
                        self._add_issue(
                            'critical',
                            'security',
                            'IAM policy allows * actions on * resources',
                            file_path,
                            name,
                            recommendation='Follow principle of least privilege'
                        )

    def _validate_terraform(self, doc: Dict, file_path: str):
        """Validate Terraform configuration"""
        # Basic terraform validation
        if 'resource' in doc:
            resources = doc['resource']
            for resource_type, resource_instances in resources.items():
                for instance_name, config in resource_instances.items():
                    self.stats['resources_validated'] += 1
                    resource_id = f"{resource_type}.{instance_name}"

                    # Check for common issues
                    if 'aws_security_group' in resource_type:
                        self._validate_tf_security_group(config, file_path, resource_id)

    def _validate_tf_security_group(self, config: Dict, file_path: str, name: str):
        """Validate Terraform AWS security group"""
        ingress = config.get('ingress', [])

        for rule in ingress:
            cidr_blocks = rule.get('cidr_blocks', [])
            if '0.0.0.0/0' in cidr_blocks:
                from_port = rule.get('from_port', '')
                to_port = rule.get('to_port', '')

                self._add_issue(
                    'critical',
                    'security',
                    f'Security group allows 0.0.0.0/0 on port(s) {from_port}-{to_port}',
                    file_path,
                    name,
                    recommendation='Restrict ingress to specific CIDR blocks'
                )

    def _validate_generic(self, doc: Dict, file_path: str):
        """Validate generic deployment configuration"""
        self.stats['resources_validated'] += 1

        # Generic checks
        if isinstance(doc, dict):
            # Check for hardcoded secrets
            self._check_for_secrets(doc, file_path, 'root')

    def _check_for_secrets(self, obj: Any, file_path: str, path: str):
        """Recursively check for hardcoded secrets"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if any(keyword in key.lower() for keyword in ['password', 'secret', 'token', 'key', 'api_key']):
                    if isinstance(value, str) and value and not value.startswith('$'):
                        self._add_issue(
                            'critical',
                            'security',
                            f'Potential hardcoded secret at {path}.{key}',
                            file_path,
                            recommendation='Use secret management instead of hardcoded values'
                        )
                self._check_for_secrets(value, file_path, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._check_for_secrets(item, file_path, f"{path}[{i}]")

    def _add_issue(self, severity: str, category: str, message: str, file: str,
                   resource: Optional[str] = None, line: Optional[int] = None,
                   recommendation: Optional[str] = None):
        """Add a validation issue"""
        issue = ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            file=file,
            resource=resource,
            line=line,
            recommendation=recommendation
        )
        self.issues.append(issue)
        self.stats['issues_by_severity'][severity] += 1
        self.stats['issues_by_category'][category] += 1

    def get_summary(self) -> Dict:
        """Get validation summary"""
        return {
            'stats': dict(self.stats),
            'total_issues': len(self.issues),
            'issues_by_severity': dict(self.stats['issues_by_severity']),
            'issues_by_category': dict(self.stats['issues_by_category'])
        }


def main():
    parser = argparse.ArgumentParser(
        description='Validate deployment configuration files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--file', '-f',
        help='Deployment configuration file to validate'
    )
    parser.add_argument(
        '--directory', '-d',
        help='Directory containing deployment configurations'
    )
    parser.add_argument(
        '--type', '-t',
        choices=['kubernetes', 'ecs', 'cloudformation', 'terraform', 'auto'],
        default='auto',
        help='Deployment type (default: auto-detect)'
    )
    parser.add_argument(
        '--severity',
        choices=['critical', 'warning', 'info'],
        help='Minimum severity level to report'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )
    parser.add_argument(
        '--check-all',
        action='store_true',
        help='Check all supported files in current directory'
    )

    args = parser.parse_args()

    # Determine files to check
    files_to_check = []

    if args.file:
        files_to_check.append(Path(args.file))
    elif args.directory:
        dir_path = Path(args.directory)
        for pattern in ['*.yaml', '*.yml', '*.json']:
            files_to_check.extend(dir_path.glob(pattern))
    elif args.check_all:
        for pattern in ['*.yaml', '*.yml', '*.json']:
            files_to_check.extend(Path('.').glob(pattern))
            files_to_check.extend(Path('.').glob(f'**/{pattern}'))
    else:
        parser.error('Must specify --file, --directory, or --check-all')

    if not files_to_check:
        print('No files found to validate', file=sys.stderr)
        sys.exit(1)

    # Validate files
    deployment_type = None if args.type == 'auto' else args.type
    validator = DeploymentValidator(deployment_type)

    for file_path in files_to_check:
        if not file_path.exists():
            print(f'File not found: {file_path}', file=sys.stderr)
            continue

        validator.validate_file(file_path)

    # Filter by severity if requested
    issues = validator.issues
    if args.severity:
        severity_order = {'critical': 3, 'warning': 2, 'info': 1}
        min_level = severity_order[args.severity]
        issues = [i for i in issues if severity_order[i.severity] >= min_level]

    # Output results
    if args.json:
        output = {
            'summary': validator.get_summary(),
            'issues': [asdict(issue) for issue in issues]
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        summary = validator.get_summary()
        print(f"\nDeployment Validation Report")
        print(f"{'=' * 60}")
        print(f"Files checked: {summary['stats']['files_checked']}")
        print(f"Resources validated: {summary['stats']['resources_validated']}")
        print(f"Total issues: {summary['total_issues']}\n")

        print("Issues by Severity:")
        for severity in ['critical', 'warning', 'info']:
            count = summary['issues_by_severity'].get(severity, 0)
            if count > 0:
                print(f"  {severity.upper()}: {count}")

        print("\nIssues by Category:")
        for category, count in summary['issues_by_category'].items():
            print(f"  {category}: {count}")

        if issues:
            print(f"\n{'=' * 60}")
            print("Issues Found:\n")

            for issue in sorted(issues, key=lambda x: ('critical', 'warning', 'info').index(x.severity)):
                severity_icon = {'critical': '🔴', 'warning': '🟡', 'info': 'ℹ️'}
                print(f"{severity_icon[issue.severity]} [{issue.severity.upper()}] {issue.category}")
                print(f"   File: {issue.file}")
                if issue.resource:
                    print(f"   Resource: {issue.resource}")
                print(f"   {issue.message}")
                if issue.recommendation:
                    print(f"   → {issue.recommendation}")
                print()

    # Exit code
    critical_count = summary['issues_by_severity'].get('critical', 0)
    if critical_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
