#!/usr/bin/env python3
"""
Kubernetes Deployment Analyzer

Analyzes Kubernetes deployments for:
- Configuration issues
- Security vulnerabilities
- Resource optimization opportunities
- High availability concerns
- Production readiness

Can analyze both manifest files and live cluster resources.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
import subprocess


class Colors:
    """ANSI color codes"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class Issue:
    """Represents an analysis issue"""
    SEVERITY_CRITICAL = 'critical'
    SEVERITY_HIGH = 'high'
    SEVERITY_MEDIUM = 'medium'
    SEVERITY_LOW = 'low'
    SEVERITY_INFO = 'info'

    def __init__(self, severity: str, category: str, message: str, recommendation: str = ""):
        self.severity = severity
        self.category = category
        self.message = message
        self.recommendation = recommendation

    def to_dict(self) -> Dict[str, str]:
        return {
            'severity': self.severity,
            'category': self.category,
            'message': self.message,
            'recommendation': self.recommendation
        }


class DeploymentAnalyzer:
    """Analyzer for Kubernetes deployments"""

    def __init__(self, no_color: bool = False):
        self.no_color = no_color
        self.issues: List[Issue] = []

    def color(self, color_code: str, text: str) -> str:
        """Apply color if enabled"""
        if self.no_color:
            return text
        return f"{color_code}{text}{Colors.RESET}"

    def analyze_file(self, file_path: Path) -> List[Issue]:
        """Analyze deployment from file"""
        try:
            with open(file_path, 'r') as f:
                documents = list(yaml.safe_load_all(f))

            for doc in documents:
                if doc and isinstance(doc, dict):
                    kind = doc.get('kind', '')
                    if kind in ['Deployment', 'StatefulSet', 'DaemonSet', 'Pod']:
                        self._analyze_workload(doc, str(file_path))

        except Exception as e:
            self.issues.append(Issue(
                Issue.SEVERITY_CRITICAL,
                'parsing',
                f"Failed to parse {file_path}: {e}"
            ))

        return self.issues

    def analyze_cluster(self, namespace: str = None, deployment: str = None) -> List[Issue]:
        """Analyze deployments from cluster"""
        try:
            # Build kubectl command
            cmd = ['kubectl', 'get', 'deployment', '-o', 'json']
            if namespace:
                cmd.extend(['-n', namespace])
            else:
                cmd.append('--all-namespaces')

            if deployment:
                cmd.append(deployment)

            # Get deployments
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                self.issues.append(Issue(
                    Issue.SEVERITY_CRITICAL,
                    'cluster',
                    f"Failed to get deployments: {result.stderr}"
                ))
                return self.issues

            data = json.loads(result.stdout)

            # Handle both single item and list
            items = [data] if data.get('kind') == 'Deployment' else data.get('items', [])

            for item in items:
                name = item['metadata']['name']
                ns = item['metadata'].get('namespace', 'default')
                self._analyze_workload(item, f"{ns}/{name}")

                # Get pods for this deployment
                self._analyze_deployment_pods(ns, name)

        except subprocess.TimeoutExpired:
            self.issues.append(Issue(
                Issue.SEVERITY_CRITICAL,
                'cluster',
                "kubectl command timed out"
            ))
        except json.JSONDecodeError as e:
            self.issues.append(Issue(
                Issue.SEVERITY_CRITICAL,
                'cluster',
                f"Failed to parse kubectl output: {e}"
            ))
        except Exception as e:
            self.issues.append(Issue(
                Issue.SEVERITY_CRITICAL,
                'cluster',
                f"Unexpected error: {e}"
            ))

        return self.issues

    def _analyze_workload(self, doc: Dict[str, Any], ref: str):
        """Analyze workload resource"""
        kind = doc.get('kind')
        spec = doc.get('spec', {})

        # Get pod template
        if kind == 'Pod':
            pod_spec = spec
            metadata = doc.get('metadata', {})
        else:
            template = spec.get('template', {})
            pod_spec = template.get('spec', {})
            metadata = template.get('metadata', {})

        # Analyze replicas
        if kind in ['Deployment', 'StatefulSet']:
            self._analyze_replicas(spec, ref)

        # Analyze update strategy
        if kind in ['Deployment', 'StatefulSet', 'DaemonSet']:
            self._analyze_update_strategy(spec, kind, ref)

        # Analyze pod spec
        self._analyze_pod_spec(pod_spec, ref)

        # Analyze labels and selectors
        self._analyze_labels(metadata, spec.get('selector', {}), ref)

        # Analyze containers
        for idx, container in enumerate(pod_spec.get('containers', [])):
            self._analyze_container(container, f"{ref}.containers[{idx}]", pod_spec)

    def _analyze_replicas(self, spec: Dict[str, Any], ref: str):
        """Analyze replica configuration"""
        replicas = spec.get('replicas', 1)

        if replicas < 2:
            self.issues.append(Issue(
                Issue.SEVERITY_HIGH,
                'high-availability',
                f"{ref}: Running with {replicas} replica(s)",
                "Use at least 2 replicas for high availability"
            ))
        elif replicas == 2:
            self.issues.append(Issue(
                Issue.SEVERITY_MEDIUM,
                'high-availability',
                f"{ref}: Running with 2 replicas",
                "Consider using 3+ replicas for better availability during rolling updates"
            ))

    def _analyze_update_strategy(self, spec: Dict[str, Any], kind: str, ref: str):
        """Analyze update strategy"""
        strategy = spec.get('strategy', {}) if kind == 'Deployment' else spec.get('updateStrategy', {})
        strategy_type = strategy.get('type')

        if kind == 'Deployment':
            if strategy_type == 'Recreate':
                self.issues.append(Issue(
                    Issue.SEVERITY_MEDIUM,
                    'availability',
                    f"{ref}: Using Recreate strategy causes downtime",
                    "Consider using RollingUpdate for zero-downtime deployments"
                ))
            elif strategy_type == 'RollingUpdate' or not strategy_type:
                rolling = strategy.get('rollingUpdate', {})
                max_unavailable = rolling.get('maxUnavailable', '25%')
                max_surge = rolling.get('maxSurge', '25%')

                # Check if values are too aggressive
                if isinstance(max_unavailable, str) and max_unavailable.endswith('%'):
                    pct = int(max_unavailable.rstrip('%'))
                    if pct > 50:
                        self.issues.append(Issue(
                            Issue.SEVERITY_MEDIUM,
                            'availability',
                            f"{ref}: maxUnavailable is {max_unavailable}",
                            "High maxUnavailable values can impact availability"
                        ))

    def _analyze_pod_spec(self, pod_spec: Dict[str, Any], ref: str):
        """Analyze pod specification"""
        # Check service account
        if not pod_spec.get('serviceAccountName'):
            self.issues.append(Issue(
                Issue.SEVERITY_LOW,
                'security',
                f"{ref}: No service account specified",
                "Consider creating a dedicated service account for this workload"
            ))

        # Check security context
        security_context = pod_spec.get('securityContext', {})
        if not security_context:
            self.issues.append(Issue(
                Issue.SEVERITY_HIGH,
                'security',
                f"{ref}: No pod security context defined",
                "Define security context with runAsNonRoot, fsGroup, etc."
            ))

        # Check for host namespace usage
        if pod_spec.get('hostNetwork'):
            self.issues.append(Issue(
                Issue.SEVERITY_HIGH,
                'security',
                f"{ref}: Using host network",
                "Avoid hostNetwork unless absolutely necessary"
            ))

        if pod_spec.get('hostPID'):
            self.issues.append(Issue(
                Issue.SEVERITY_HIGH,
                'security',
                f"{ref}: Using host PID namespace",
                "Avoid hostPID unless absolutely necessary"
            ))

        if pod_spec.get('hostIPC'):
            self.issues.append(Issue(
                Issue.SEVERITY_HIGH,
                'security',
                f"{ref}: Using host IPC namespace",
                "Avoid hostIPC unless absolutely necessary"
            ))

        # Check for affinity rules
        if not pod_spec.get('affinity'):
            self.issues.append(Issue(
                Issue.SEVERITY_LOW,
                'high-availability',
                f"{ref}: No affinity rules defined",
                "Consider adding pod anti-affinity to spread pods across nodes/zones"
            ))

        # Check topology spread constraints
        if not pod_spec.get('topologySpreadConstraints'):
            self.issues.append(Issue(
                Issue.SEVERITY_INFO,
                'high-availability',
                f"{ref}: No topology spread constraints",
                "Consider using topology spread constraints for even pod distribution"
            ))

    def _analyze_labels(self, metadata: Dict[str, Any], selector: Dict[str, Any], ref: str):
        """Analyze labels and selectors"""
        labels = metadata.get('labels', {})

        # Check for recommended labels
        recommended = {
            'app.kubernetes.io/name': 'Application name',
            'app.kubernetes.io/version': 'Application version',
            'app.kubernetes.io/component': 'Component within architecture',
        }

        missing_labels = [name for name in recommended if name not in labels]
        if missing_labels:
            self.issues.append(Issue(
                Issue.SEVERITY_LOW,
                'observability',
                f"{ref}: Missing recommended labels: {', '.join(missing_labels)}",
                "Use standard Kubernetes labels for better organization"
            ))

    def _analyze_container(self, container: Dict[str, Any], ref: str, pod_spec: Dict[str, Any]):
        """Analyze container configuration"""
        # Check image
        image = container.get('image', '')
        if ':latest' in image or ':' not in image:
            self.issues.append(Issue(
                Issue.SEVERITY_HIGH,
                'reliability',
                f"{ref}: Using 'latest' or untagged image",
                "Always use specific version tags for reproducible deployments"
            ))

        # Check image pull policy
        pull_policy = container.get('imagePullPolicy', 'IfNotPresent')
        if pull_policy == 'Always' and ':' in image and not image.endswith(':latest'):
            self.issues.append(Issue(
                Issue.SEVERITY_LOW,
                'performance',
                f"{ref}: Using imagePullPolicy: Always with tagged image",
                "Consider using IfNotPresent for tagged images to reduce image pulls"
            ))

        # Check resources
        self._analyze_container_resources(container.get('resources', {}), ref)

        # Check security context
        self._analyze_container_security(container.get('securityContext', {}), pod_spec.get('securityContext', {}), ref)

        # Check probes
        self._analyze_probes(container, ref)

        # Check for environment variables with sensitive data
        self._analyze_env_vars(container.get('env', []), ref)

    def _analyze_container_resources(self, resources: Dict[str, Any], ref: str):
        """Analyze container resource configuration"""
        requests = resources.get('requests', {})
        limits = resources.get('limits', {})

        if not requests and not limits:
            self.issues.append(Issue(
                Issue.SEVERITY_HIGH,
                'resource-management',
                f"{ref}: No resource requests or limits defined",
                "Define resource requests and limits for predictable scheduling and resource management"
            ))
            return

        if not requests:
            self.issues.append(Issue(
                Issue.SEVERITY_MEDIUM,
                'resource-management',
                f"{ref}: No resource requests defined",
                "Define resource requests for proper scheduling"
            ))

        if not limits:
            self.issues.append(Issue(
                Issue.SEVERITY_MEDIUM,
                'resource-management',
                f"{ref}: No resource limits defined",
                "Define resource limits to prevent resource exhaustion"
            ))

        # Check for missing CPU or memory
        if requests:
            if 'cpu' not in requests:
                self.issues.append(Issue(
                    Issue.SEVERITY_MEDIUM,
                    'resource-management',
                    f"{ref}: No CPU request defined",
                    "Define CPU request for proper scheduling"
                ))
            if 'memory' not in requests:
                self.issues.append(Issue(
                    Issue.SEVERITY_MEDIUM,
                    'resource-management',
                    f"{ref}: No memory request defined",
                    "Define memory request for proper scheduling"
                ))

    def _analyze_container_security(self, container_ctx: Dict[str, Any], pod_ctx: Dict[str, Any], ref: str):
        """Analyze container security context"""
        # Check privileged
        if container_ctx.get('privileged'):
            self.issues.append(Issue(
                Issue.SEVERITY_CRITICAL,
                'security',
                f"{ref}: Container running in privileged mode",
                "Avoid privileged containers. Use specific capabilities instead"
            ))

        # Check runAsNonRoot
        run_as_non_root = container_ctx.get('runAsNonRoot') or pod_ctx.get('runAsNonRoot')
        if not run_as_non_root:
            self.issues.append(Issue(
                Issue.SEVERITY_HIGH,
                'security',
                f"{ref}: Container may run as root",
                "Set runAsNonRoot: true to prevent running as root"
            ))

        # Check allowPrivilegeEscalation
        if container_ctx.get('allowPrivilegeEscalation', True):
            self.issues.append(Issue(
                Issue.SEVERITY_HIGH,
                'security',
                f"{ref}: Privilege escalation allowed",
                "Set allowPrivilegeEscalation: false"
            ))

        # Check readOnlyRootFilesystem
        if not container_ctx.get('readOnlyRootFilesystem'):
            self.issues.append(Issue(
                Issue.SEVERITY_MEDIUM,
                'security',
                f"{ref}: Root filesystem is writable",
                "Set readOnlyRootFilesystem: true and use emptyDir for writable paths"
            ))

        # Check capabilities
        capabilities = container_ctx.get('capabilities', {})
        if 'ALL' not in capabilities.get('drop', []):
            self.issues.append(Issue(
                Issue.SEVERITY_HIGH,
                'security',
                f"{ref}: Not dropping all capabilities",
                "Drop all capabilities and add back only required ones"
            ))

        # Check for seccomp profile
        seccomp = container_ctx.get('seccompProfile') or pod_ctx.get('seccompProfile')
        if not seccomp:
            self.issues.append(Issue(
                Issue.SEVERITY_MEDIUM,
                'security',
                f"{ref}: No seccomp profile defined",
                "Define seccomp profile (RuntimeDefault or custom)"
            ))

    def _analyze_probes(self, container: Dict[str, Any], ref: str):
        """Analyze health probes"""
        if 'livenessProbe' not in container:
            self.issues.append(Issue(
                Issue.SEVERITY_MEDIUM,
                'reliability',
                f"{ref}: No liveness probe defined",
                "Define liveness probe to detect and recover from deadlocks"
            ))

        if 'readinessProbe' not in container:
            self.issues.append(Issue(
                Issue.SEVERITY_HIGH,
                'reliability',
                f"{ref}: No readiness probe defined",
                "Define readiness probe to prevent traffic to unready pods"
            ))

        # Check probe configuration
        for probe_type in ['livenessProbe', 'readinessProbe', 'startupProbe']:
            probe = container.get(probe_type)
            if probe:
                self._validate_probe_config(probe, f"{ref}.{probe_type}")

    def _validate_probe_config(self, probe: Dict[str, Any], ref: str):
        """Validate probe configuration"""
        # Check timeout
        timeout = probe.get('timeoutSeconds', 1)
        if timeout < 2:
            self.issues.append(Issue(
                Issue.SEVERITY_LOW,
                'reliability',
                f"{ref}: Very short timeout ({timeout}s)",
                "Consider increasing timeout for more reliable health checks"
            ))

        # Check period
        period = probe.get('periodSeconds', 10)
        if period < 5:
            self.issues.append(Issue(
                Issue.SEVERITY_LOW,
                'performance',
                f"{ref}: Very frequent probe ({period}s period)",
                "Frequent probes can impact performance"
            ))

    def _analyze_env_vars(self, env_vars: List[Dict[str, Any]], ref: str):
        """Analyze environment variables for sensitive data"""
        sensitive_patterns = ['password', 'secret', 'key', 'token', 'credential']

        for env in env_vars:
            name = env.get('name', '').lower()
            value = env.get('value')

            # Check if sensitive data is hardcoded
            if value and any(pattern in name for pattern in sensitive_patterns):
                self.issues.append(Issue(
                    Issue.SEVERITY_CRITICAL,
                    'security',
                    f"{ref}: Sensitive data in plain text environment variable '{env.get('name')}'",
                    "Use Secrets and valueFrom instead of plain text values"
                ))

    def _analyze_deployment_pods(self, namespace: str, deployment: str):
        """Analyze pods for a deployment"""
        try:
            # Get pods
            cmd = [
                'kubectl', 'get', 'pods',
                '-n', namespace,
                '-l', f'deployment={deployment}',
                '-o', 'json'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return

            data = json.loads(result.stdout)
            pods = data.get('items', [])

            # Check pod status
            total_pods = len(pods)
            running_pods = sum(1 for pod in pods if pod['status']['phase'] == 'Running')
            ready_pods = sum(
                1 for pod in pods
                if pod['status']['phase'] == 'Running' and
                all(c['ready'] for c in pod['status'].get('containerStatuses', []))
            )

            ref = f"{namespace}/{deployment}"

            if total_pods == 0:
                self.issues.append(Issue(
                    Issue.SEVERITY_CRITICAL,
                    'availability',
                    f"{ref}: No pods running",
                    "Check deployment status and events"
                ))
            elif ready_pods < total_pods:
                self.issues.append(Issue(
                    Issue.SEVERITY_HIGH,
                    'availability',
                    f"{ref}: {ready_pods}/{total_pods} pods ready",
                    "Investigate pods that are not ready"
                ))

        except Exception:
            pass  # Ignore errors in pod analysis

    def print_results(self):
        """Print analysis results"""
        if not self.issues:
            print(self.color(Colors.GREEN + Colors.BOLD, "\n✓ No issues found!\n"))
            return

        # Group by severity
        by_severity = {
            Issue.SEVERITY_CRITICAL: [],
            Issue.SEVERITY_HIGH: [],
            Issue.SEVERITY_MEDIUM: [],
            Issue.SEVERITY_LOW: [],
            Issue.SEVERITY_INFO: []
        }

        for issue in self.issues:
            by_severity[issue.severity].append(issue)

        print(f"\n{self.color(Colors.BOLD, '=== Deployment Analysis Results ===')}\n")

        severity_config = {
            Issue.SEVERITY_CRITICAL: (Colors.RED + Colors.BOLD, '🔴 CRITICAL', Colors.RED),
            Issue.SEVERITY_HIGH: (Colors.RED, '🔴 HIGH', Colors.RED),
            Issue.SEVERITY_MEDIUM: (Colors.YELLOW, '🟡 MEDIUM', Colors.YELLOW),
            Issue.SEVERITY_LOW: (Colors.YELLOW, '🟡 LOW', Colors.YELLOW),
            Issue.SEVERITY_INFO: (Colors.CYAN, 'ℹ️  INFO', Colors.CYAN)
        }

        for severity in [Issue.SEVERITY_CRITICAL, Issue.SEVERITY_HIGH, Issue.SEVERITY_MEDIUM, Issue.SEVERITY_LOW, Issue.SEVERITY_INFO]:
            issues = by_severity[severity]
            if not issues:
                continue

            header_color, header_text, item_color = severity_config[severity]
            print(self.color(header_color, f"{header_text} ({len(issues)}):"))

            for issue in issues:
                print(self.color(item_color, f"  • [{issue.category}] {issue.message}"))
                if issue.recommendation:
                    print(self.color(Colors.CYAN, f"    → {issue.recommendation}"))
            print()

        # Summary
        critical_count = len(by_severity[Issue.SEVERITY_CRITICAL])
        high_count = len(by_severity[Issue.SEVERITY_HIGH])

        if critical_count > 0:
            print(self.color(Colors.RED + Colors.BOLD, f"⚠️  Found {critical_count} critical issue(s). Immediate action required!"))
        elif high_count > 0:
            print(self.color(Colors.YELLOW + Colors.BOLD, f"⚠️  Found {high_count} high severity issue(s). Please review."))
        else:
            print(self.color(Colors.GREEN, "✓ No critical or high severity issues found."))

    def get_json_results(self) -> str:
        """Return results as JSON"""
        by_severity = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': [],
            'info': []
        }

        for issue in self.issues:
            by_severity[issue.severity].append(issue.to_dict())

        return json.dumps({
            'total_issues': len(self.issues),
            'by_severity': {k: len(v) for k, v in by_severity.items()},
            'issues': by_severity
        }, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Kubernetes deployments for issues and optimization opportunities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze deployment file
  analyze_deployment.py deployment.yaml

  # Analyze all manifests in directory
  analyze_deployment.py manifests/

  # Analyze deployment in cluster
  analyze_deployment.py --cluster --deployment my-app --namespace production

  # Analyze all deployments in namespace
  analyze_deployment.py --cluster --namespace production

  # Analyze all deployments in cluster
  analyze_deployment.py --cluster --all-namespaces

  # Output as JSON
  analyze_deployment.py --json deployment.yaml
        """
    )

    parser.add_argument(
        'path',
        type=str,
        nargs='?',
        help='Path to YAML file or directory (not needed with --cluster)'
    )

    parser.add_argument(
        '--cluster',
        action='store_true',
        help='Analyze deployments from cluster instead of files'
    )

    parser.add_argument(
        '--deployment',
        type=str,
        help='Specific deployment name (requires --cluster)'
    )

    parser.add_argument(
        '--namespace',
        type=str,
        help='Kubernetes namespace (requires --cluster)'
    )

    parser.add_argument(
        '--all-namespaces',
        action='store_true',
        help='Analyze deployments in all namespaces (requires --cluster)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.cluster:
        if args.path:
            print("Error: Cannot specify path with --cluster", file=sys.stderr)
            return 1
        if args.deployment and args.all_namespaces:
            print("Error: Cannot use --deployment with --all-namespaces", file=sys.stderr)
            return 1
    else:
        if not args.path:
            print("Error: path required when not using --cluster", file=sys.stderr)
            return 1
        if args.deployment or args.all_namespaces:
            print("Error: --deployment and --all-namespaces require --cluster", file=sys.stderr)
            return 1

    # Create analyzer
    analyzer = DeploymentAnalyzer(no_color=args.no_color or args.json)

    # Analyze
    if args.cluster:
        namespace = args.namespace if not args.all_namespaces else None
        analyzer.analyze_cluster(namespace=namespace, deployment=args.deployment)
    else:
        path = Path(args.path)
        if not path.exists():
            print(f"Error: Path '{path}' does not exist", file=sys.stderr)
            return 1

        if path.is_file():
            analyzer.analyze_file(path)
        elif path.is_dir():
            for yaml_file in path.rglob('*.yaml'):
                analyzer.analyze_file(yaml_file)
            for yaml_file in path.rglob('*.yml'):
                analyzer.analyze_file(yaml_file)
        else:
            print(f"Error: '{path}' is not a file or directory", file=sys.stderr)
            return 1

    # Output results
    if args.json:
        print(analyzer.get_json_results())
    else:
        analyzer.print_results()

    # Return exit code based on critical/high issues
    critical_count = sum(1 for issue in analyzer.issues if issue.severity == Issue.SEVERITY_CRITICAL)
    if critical_count > 0:
        return 2
    high_count = sum(1 for issue in analyzer.issues if issue.severity == Issue.SEVERITY_HIGH)
    if high_count > 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
