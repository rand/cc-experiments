#!/usr/bin/env python3
"""
Kubernetes Manifest Validation Script

Validates Kubernetes YAML manifests for:
- YAML syntax
- Kubernetes API schema compliance
- Security best practices
- Resource configuration
- Common misconfigurations

Dependencies: pyyaml, kubernetes, jsonschema
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import yaml
import subprocess
import tempfile


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class ValidationResult:
    """Container for validation results"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.files_checked = 0
        self.manifests_checked = 0

    def add_error(self, message: str):
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def add_info(self, message: str):
        self.info.append(message)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class ManifestValidator:
    """Kubernetes manifest validator"""

    SECURITY_CHECKS = {
        'runAsNonRoot': 'Container should run as non-root user',
        'readOnlyRootFilesystem': 'Container should use read-only root filesystem',
        'allowPrivilegeEscalation': 'Container should not allow privilege escalation',
        'capabilities': 'Container should drop all capabilities',
        'seccompProfile': 'Pod should define seccomp profile',
    }

    RESOURCE_CHECKS = {
        'requests.cpu': 'CPU requests',
        'requests.memory': 'Memory requests',
        'limits.cpu': 'CPU limits',
        'limits.memory': 'Memory limits',
    }

    def __init__(self, strict: bool = False, skip_schema: bool = False, no_color: bool = False):
        self.strict = strict
        self.skip_schema = skip_schema
        self.no_color = no_color
        self.result = ValidationResult()

    def color(self, color_code: str, text: str) -> str:
        """Apply color to text if colors are enabled"""
        if self.no_color:
            return text
        return f"{color_code}{text}{Colors.RESET}"

    def validate_file(self, file_path: Path) -> ValidationResult:
        """Validate a single YAML file"""
        self.result.files_checked += 1

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Parse YAML (may contain multiple documents)
            try:
                documents = list(yaml.safe_load_all(content))
            except yaml.YAMLError as e:
                self.result.add_error(f"{file_path}: YAML parsing error: {e}")
                return self.result

            for idx, doc in enumerate(documents):
                if doc is None:
                    continue

                self.result.manifests_checked += 1
                doc_ref = f"{file_path}" if len(documents) == 1 else f"{file_path}[{idx}]"

                # Basic structure validation
                if not isinstance(doc, dict):
                    self.result.add_error(f"{doc_ref}: Document must be a dictionary")
                    continue

                # Validate Kubernetes manifest structure
                self._validate_k8s_structure(doc, doc_ref)

                # Validate specific resource types
                kind = doc.get('kind', '')
                if kind in ['Pod', 'Deployment', 'StatefulSet', 'DaemonSet', 'Job', 'CronJob']:
                    self._validate_workload(doc, doc_ref)

                # Schema validation with kubectl
                if not self.skip_schema:
                    self._validate_with_kubectl(doc, doc_ref)

        except Exception as e:
            self.result.add_error(f"{file_path}: Unexpected error: {e}")

        return self.result

    def validate_directory(self, dir_path: Path, recursive: bool = True) -> ValidationResult:
        """Validate all YAML files in a directory"""
        pattern = "**/*.yaml" if recursive else "*.yaml"
        yaml_files = list(dir_path.glob(pattern))
        yaml_files.extend(dir_path.glob(pattern.replace('.yaml', '.yml')))

        if not yaml_files:
            self.result.add_warning(f"No YAML files found in {dir_path}")
            return self.result

        for file_path in sorted(yaml_files):
            self.validate_file(file_path)

        return self.result

    def _validate_k8s_structure(self, doc: Dict[str, Any], doc_ref: str):
        """Validate basic Kubernetes manifest structure"""
        # Check required fields
        required_fields = ['apiVersion', 'kind', 'metadata']
        for field in required_fields:
            if field not in doc:
                self.result.add_error(f"{doc_ref}: Missing required field '{field}'")

        # Validate metadata
        metadata = doc.get('metadata', {})
        if not isinstance(metadata, dict):
            self.result.add_error(f"{doc_ref}: 'metadata' must be a dictionary")
        elif 'name' not in metadata:
            self.result.add_error(f"{doc_ref}: 'metadata.name' is required")

        # Check for deprecated apiVersion
        api_version = doc.get('apiVersion', '')
        deprecated = {
            'extensions/v1beta1': 'Use apps/v1 instead',
            'apps/v1beta1': 'Use apps/v1 instead',
            'apps/v1beta2': 'Use apps/v1 instead',
        }
        if api_version in deprecated:
            self.result.add_warning(f"{doc_ref}: Deprecated apiVersion '{api_version}'. {deprecated[api_version]}")

    def _validate_workload(self, doc: Dict[str, Any], doc_ref: str):
        """Validate workload-specific resources"""
        kind = doc.get('kind')
        spec = doc.get('spec', {})

        # Get pod template
        if kind == 'Pod':
            pod_spec = spec
        else:
            template = spec.get('template', {})
            pod_spec = template.get('spec', {})

        if not pod_spec:
            self.result.add_error(f"{doc_ref}: Missing pod spec")
            return

        # Validate containers
        containers = pod_spec.get('containers', [])
        if not containers:
            self.result.add_error(f"{doc_ref}: No containers defined")
            return

        for idx, container in enumerate(containers):
            container_ref = f"{doc_ref}.containers[{idx}]"
            self._validate_container(container, container_ref, pod_spec)

        # Validate init containers
        init_containers = pod_spec.get('initContainers', [])
        for idx, container in enumerate(init_containers):
            container_ref = f"{doc_ref}.initContainers[{idx}]"
            self._validate_container(container, container_ref, pod_spec)

        # Check for replicas (Deployment, StatefulSet)
        if kind in ['Deployment', 'StatefulSet']:
            replicas = spec.get('replicas', 1)
            if replicas < 2 and not self.strict:
                self.result.add_warning(
                    f"{doc_ref}: Single replica detected. Consider using multiple replicas for HA"
                )
            elif replicas < 2 and self.strict:
                self.result.add_error(
                    f"{doc_ref}: Single replica not allowed in strict mode"
                )

        # Check for pod disruption budget reference
        if kind in ['Deployment', 'StatefulSet', 'DaemonSet']:
            self.result.add_info(
                f"{doc_ref}: Consider creating a PodDisruptionBudget for this workload"
            )

    def _validate_container(self, container: Dict[str, Any], container_ref: str, pod_spec: Dict[str, Any]):
        """Validate container configuration"""
        # Check image
        image = container.get('image', '')
        if not image:
            self.result.add_error(f"{container_ref}: No image specified")
        elif ':latest' in image or ':' not in image:
            self.result.add_warning(
                f"{container_ref}: Using 'latest' or untagged image is not recommended. Use specific version tags"
            )

        # Check resources
        resources = container.get('resources', {})
        self._validate_resources(resources, container_ref)

        # Check security context
        container_security = container.get('securityContext', {})
        pod_security = pod_spec.get('securityContext', {})
        self._validate_security_context(container_security, pod_security, container_ref)

        # Check health probes
        if 'livenessProbe' not in container:
            self.result.add_warning(f"{container_ref}: No liveness probe defined")

        if 'readinessProbe' not in container:
            self.result.add_warning(f"{container_ref}: No readiness probe defined")

        # Check for privileged mode
        if container_security.get('privileged'):
            msg = f"{container_ref}: Running in privileged mode is a security risk"
            if self.strict:
                self.result.add_error(msg)
            else:
                self.result.add_warning(msg)

    def _validate_resources(self, resources: Dict[str, Any], container_ref: str):
        """Validate resource requests and limits"""
        requests = resources.get('requests', {})
        limits = resources.get('limits', {})

        # Check if resources are defined
        if not requests and not limits:
            msg = f"{container_ref}: No resource requests or limits defined"
            if self.strict:
                self.result.add_error(msg)
            else:
                self.result.add_warning(msg)
            return

        # Check for requests without limits
        if requests and not limits:
            self.result.add_warning(f"{container_ref}: Resource requests defined but no limits")

        # Check for limits without requests
        if limits and not requests:
            self.result.add_warning(
                f"{container_ref}: Resource limits defined but no requests. "
                "Kubernetes will set requests equal to limits"
            )

        # Validate CPU
        if 'cpu' in requests or 'cpu' in limits:
            if 'cpu' in limits and 'cpu' in requests:
                # Could add validation of values here
                pass

        # Validate memory
        if 'memory' in requests or 'memory' in limits:
            if 'memory' in limits and 'memory' in requests:
                # Could add validation of values here
                pass

    def _validate_security_context(
        self,
        container_ctx: Dict[str, Any],
        pod_ctx: Dict[str, Any],
        container_ref: str
    ):
        """Validate security context"""
        # Check runAsNonRoot
        run_as_non_root = container_ctx.get('runAsNonRoot') or pod_ctx.get('runAsNonRoot')
        if not run_as_non_root:
            msg = f"{container_ref}: Should set runAsNonRoot: true"
            if self.strict:
                self.result.add_error(msg)
            else:
                self.result.add_warning(msg)

        # Check readOnlyRootFilesystem
        if not container_ctx.get('readOnlyRootFilesystem'):
            self.result.add_warning(
                f"{container_ref}: Consider setting readOnlyRootFilesystem: true"
            )

        # Check allowPrivilegeEscalation
        if container_ctx.get('allowPrivilegeEscalation', True):
            msg = f"{container_ref}: Should set allowPrivilegeEscalation: false"
            if self.strict:
                self.result.add_error(msg)
            else:
                self.result.add_warning(msg)

        # Check capabilities
        capabilities = container_ctx.get('capabilities', {})
        drop_caps = capabilities.get('drop', [])

        if 'ALL' not in drop_caps:
            msg = f"{container_ref}: Should drop all capabilities (capabilities.drop: [ALL])"
            if self.strict:
                self.result.add_error(msg)
            else:
                self.result.add_warning(msg)

        # Check seccomp profile
        seccomp = container_ctx.get('seccompProfile') or pod_ctx.get('seccompProfile')
        if not seccomp:
            self.result.add_info(
                f"{container_ref}: Consider adding seccomp profile"
            )

    def _validate_with_kubectl(self, doc: Dict[str, Any], doc_ref: str):
        """Validate manifest using kubectl dry-run"""
        try:
            # Write manifest to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(doc, f)
                temp_file = f.name

            # Run kubectl apply --dry-run
            result = subprocess.run(
                ['kubectl', 'apply', '--dry-run=client', '-f', temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                self.result.add_error(f"{doc_ref}: kubectl validation failed: {error_msg}")

        except FileNotFoundError:
            self.result.add_warning("kubectl not found. Skipping schema validation")
        except subprocess.TimeoutExpired:
            self.result.add_warning(f"{doc_ref}: kubectl validation timed out")
        except Exception as e:
            self.result.add_warning(f"{doc_ref}: kubectl validation error: {e}")
        finally:
            # Clean up temp file
            try:
                if 'temp_file' in locals():
                    os.unlink(temp_file)
            except:
                pass

    def print_results(self):
        """Print validation results"""
        print(f"\n{self.color(Colors.BOLD, '=== Validation Results ===')}\n")

        print(f"Files checked: {self.result.files_checked}")
        print(f"Manifests validated: {self.result.manifests_checked}\n")

        # Print errors
        if self.result.errors:
            print(self.color(Colors.RED + Colors.BOLD, f"Errors ({len(self.result.errors)}):"))
            for error in self.result.errors:
                print(self.color(Colors.RED, f"  ✗ {error}"))
            print()

        # Print warnings
        if self.result.warnings:
            print(self.color(Colors.YELLOW + Colors.BOLD, f"Warnings ({len(self.result.warnings)}):"))
            for warning in self.result.warnings:
                print(self.color(Colors.YELLOW, f"  ⚠ {warning}"))
            print()

        # Print info
        if self.result.info:
            print(self.color(Colors.CYAN + Colors.BOLD, f"Info ({len(self.result.info)}):"))
            for info in self.result.info:
                print(self.color(Colors.CYAN, f"  ℹ {info}"))
            print()

        # Summary
        if not self.result.has_errors() and not self.result.has_warnings():
            print(self.color(Colors.GREEN + Colors.BOLD, "✓ All validations passed!"))
        elif self.result.has_errors():
            print(self.color(Colors.RED + Colors.BOLD, f"✗ Validation failed with {len(self.result.errors)} error(s)"))
        else:
            print(self.color(Colors.YELLOW + Colors.BOLD, f"⚠ Validation passed with {len(self.result.warnings)} warning(s)"))

    def get_json_results(self) -> str:
        """Return results as JSON"""
        return json.dumps({
            'files_checked': self.result.files_checked,
            'manifests_validated': self.result.manifests_checked,
            'errors': self.result.errors,
            'warnings': self.result.warnings,
            'info': self.result.info,
            'success': not self.result.has_errors()
        }, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Validate Kubernetes manifests for correctness and best practices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single file
  validate_manifests.py deployment.yaml

  # Validate all files in a directory
  validate_manifests.py manifests/

  # Validate with strict mode (errors instead of warnings)
  validate_manifests.py --strict manifests/

  # Skip kubectl schema validation
  validate_manifests.py --skip-schema deployment.yaml

  # Output as JSON
  validate_manifests.py --json manifests/ > results.json
        """
    )

    parser.add_argument(
        'path',
        type=str,
        help='Path to YAML file or directory containing manifests'
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='Strict mode: treat warnings as errors'
    )

    parser.add_argument(
        '--skip-schema',
        action='store_true',
        help='Skip kubectl schema validation'
    )

    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='Do not recursively search directories'
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

    # Create validator
    validator = ManifestValidator(
        strict=args.strict,
        skip_schema=args.skip_schema,
        no_color=args.no_color or args.json
    )

    # Validate path
    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path '{path}' does not exist", file=sys.stderr)
        return 1

    # Validate
    if path.is_file():
        validator.validate_file(path)
    elif path.is_dir():
        validator.validate_directory(path, recursive=not args.no_recursive)
    else:
        print(f"Error: '{path}' is not a file or directory", file=sys.stderr)
        return 1

    # Output results
    if args.json:
        print(validator.get_json_results())
    else:
        validator.print_results()

    # Return exit code
    return 1 if validator.result.has_errors() else 0


if __name__ == '__main__':
    sys.exit(main())
