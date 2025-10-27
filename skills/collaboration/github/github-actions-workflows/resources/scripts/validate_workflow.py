#!/usr/bin/env python3
"""
GitHub Actions Workflow Validator

Validates GitHub Actions workflow files for syntax, security issues,
and best practices. Provides actionable suggestions for improvements.

Usage:
    ./validate_workflow.py .github/workflows/
    ./validate_workflow.py workflow.yml --json
    ./validate_workflow.py . --recursive --fix-suggestions
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


@dataclass
class ValidationIssue:
    """Represents a validation issue found in a workflow."""
    severity: str  # error, warning, info
    category: str  # syntax, security, performance, best-practice
    message: str
    file: str
    line: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Results of workflow validation."""
    file: str
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: int = 0
    errors: int = 0
    info: int = 0


class WorkflowValidator:
    """Validates GitHub Actions workflows."""

    def __init__(self):
        self.results: List[ValidationResult] = []

        # Security patterns
        self.secret_patterns = [
            r'password\s*[:=]\s*["\']?[a-zA-Z0-9]+["\']?',
            r'api[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9]+["\']?',
            r'token\s*[:=]\s*["\']?[a-zA-Z0-9]+["\']?',
            r'aws[_-]?access[_-]?key[_-]?id\s*[:=]',
            r'aws[_-]?secret[_-]?access[_-]?key\s*[:=]',
        ]

        # Recommended actions versions
        self.recommended_versions = {
            'actions/checkout': 'v4',
            'actions/setup-node': 'v4',
            'actions/setup-python': 'v5',
            'actions/setup-java': 'v4',
            'actions/setup-go': 'v5',
            'actions/cache': 'v4',
            'actions/upload-artifact': 'v4',
            'actions/download-artifact': 'v4',
            'docker/build-push-action': 'v5',
            'docker/login-action': 'v3',
            'docker/setup-buildx-action': 'v3',
        }

    def validate_file(self, filepath: Path) -> ValidationResult:
        """Validate a single workflow file."""
        result = ValidationResult(file=str(filepath), valid=True)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse YAML
            try:
                workflow = yaml.safe_load(content)
            except yaml.YAMLError as e:
                result.valid = False
                result.errors += 1
                result.issues.append(ValidationIssue(
                    severity='error',
                    category='syntax',
                    message=f'Invalid YAML syntax: {e}',
                    file=str(filepath)
                ))
                return result

            # Run validation checks
            self._check_required_fields(workflow, result)
            self._check_security_issues(workflow, content, result)
            self._check_permissions(workflow, result)
            self._check_caching(workflow, result)
            self._check_action_versions(workflow, result)
            self._check_best_practices(workflow, result)
            self._check_performance(workflow, result)

        except Exception as e:
            result.valid = False
            result.errors += 1
            result.issues.append(ValidationIssue(
                severity='error',
                category='syntax',
                message=f'Error reading file: {e}',
                file=str(filepath)
            ))

        # Count issues by severity
        for issue in result.issues:
            if issue.severity == 'error':
                result.errors += 1
                result.valid = False
            elif issue.severity == 'warning':
                result.warnings += 1
            elif issue.severity == 'info':
                result.info += 1

        return result

    def _check_required_fields(self, workflow: Dict, result: ValidationResult):
        """Check for required workflow fields."""
        if not workflow:
            result.issues.append(ValidationIssue(
                severity='error',
                category='syntax',
                message='Workflow file is empty',
                file=result.file
            ))
            return

        if 'on' not in workflow:
            result.issues.append(ValidationIssue(
                severity='error',
                category='syntax',
                message='Missing required field: on (workflow triggers)',
                file=result.file,
                suggestion='Add workflow triggers, e.g., on: [push, pull_request]'
            ))

        if 'jobs' not in workflow:
            result.issues.append(ValidationIssue(
                severity='error',
                category='syntax',
                message='Missing required field: jobs',
                file=result.file,
                suggestion='Add at least one job to the workflow'
            ))

        if 'name' not in workflow:
            result.issues.append(ValidationIssue(
                severity='info',
                category='best-practice',
                message='Workflow name not specified',
                file=result.file,
                suggestion='Add name field for better workflow identification'
            ))

    def _check_security_issues(self, workflow: Dict, content: str, result: ValidationResult):
        """Check for security issues."""
        # Check for hardcoded secrets
        for pattern in self.secret_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if '${{ secrets.' not in match.group():
                    line_num = content[:match.start()].count('\n') + 1
                    result.issues.append(ValidationIssue(
                        severity='error',
                        category='security',
                        message=f'Possible hardcoded secret detected: {match.group()[:50]}',
                        file=result.file,
                        line=line_num,
                        suggestion='Use GitHub Secrets: ${{ secrets.SECRET_NAME }}'
                    ))

        # Check for pull_request_target with checkout
        if isinstance(workflow.get('on'), dict):
            if 'pull_request_target' in workflow['on']:
                jobs = workflow.get('jobs', {})
                for job_name, job in jobs.items():
                    steps = job.get('steps', [])
                    for step in steps:
                        if isinstance(step, dict) and step.get('uses', '').startswith('actions/checkout'):
                            result.issues.append(ValidationIssue(
                                severity='error',
                                category='security',
                                message=f'Dangerous: pull_request_target with checkout in job "{job_name}"',
                                file=result.file,
                                suggestion='Use pull_request instead, or avoid checking out PR code with pull_request_target'
                            ))

        # Check for actions pinned to branches
        if 'jobs' in workflow:
            for job_name, job in workflow['jobs'].items():
                steps = job.get('steps', [])
                for i, step in enumerate(steps):
                    if isinstance(step, dict) and 'uses' in step:
                        uses = step['uses']
                        if '@' in uses:
                            action, ref = uses.split('@', 1)
                            if ref in ['main', 'master', 'develop', 'dev']:
                                result.issues.append(ValidationIssue(
                                    severity='warning',
                                    category='security',
                                    message=f'Action pinned to branch: {uses} in job "{job_name}"',
                                    file=result.file,
                                    suggestion=f'Pin to major version or commit SHA: {action}@v1'
                                ))

    def _check_permissions(self, workflow: Dict, result: ValidationResult):
        """Check permissions configuration."""
        if 'permissions' not in workflow:
            result.issues.append(ValidationIssue(
                severity='info',
                category='security',
                message='No workflow-level permissions specified',
                file=result.file,
                suggestion='Add permissions field to follow principle of least privilege'
            ))
            return

        permissions = workflow['permissions']

        # Check for overly permissive permissions
        if permissions == 'write-all' or permissions.get('contents') == 'write':
            result.issues.append(ValidationIssue(
                severity='warning',
                category='security',
                message='Overly permissive workflow permissions',
                file=result.file,
                suggestion='Use minimal permissions and grant additional permissions at job level'
            ))

    def _check_caching(self, workflow: Dict, result: ValidationResult):
        """Check for caching opportunities."""
        if 'jobs' not in workflow:
            return

        for job_name, job in workflow['jobs'].items():
            steps = job.get('steps', [])

            # Check for setup actions without cache
            setup_actions_without_cache = []
            has_cache_action = False

            for step in steps:
                if not isinstance(step, dict):
                    continue

                uses = step.get('uses', '')

                if 'actions/cache' in uses:
                    has_cache_action = True

                if 'actions/setup-node' in uses:
                    if not step.get('with', {}).get('cache'):
                        setup_actions_without_cache.append('setup-node')
                elif 'actions/setup-python' in uses:
                    if not step.get('with', {}).get('cache'):
                        setup_actions_without_cache.append('setup-python')
                elif 'actions/setup-go' in uses:
                    if not step.get('with', {}).get('cache'):
                        setup_actions_without_cache.append('setup-go')
                elif 'actions/setup-java' in uses:
                    if not step.get('with', {}).get('cache'):
                        setup_actions_without_cache.append('setup-java')

            if setup_actions_without_cache and not has_cache_action:
                result.issues.append(ValidationIssue(
                    severity='warning',
                    category='performance',
                    message=f'Setup action without caching in job "{job_name}": {", ".join(setup_actions_without_cache)}',
                    file=result.file,
                    suggestion='Enable cache parameter in setup action: with: { cache: "npm" }'
                ))

    def _check_action_versions(self, workflow: Dict, result: ValidationResult):
        """Check action versions against recommended versions."""
        if 'jobs' not in workflow:
            return

        for job_name, job in workflow['jobs'].items():
            steps = job.get('steps', [])

            for step in steps:
                if not isinstance(step, dict) or 'uses' not in step:
                    continue

                uses = step['uses']
                if '@' not in uses:
                    continue

                action, version = uses.split('@', 1)

                if action in self.recommended_versions:
                    recommended = self.recommended_versions[action]
                    current_major = version.split('.')[0].replace('v', '')
                    recommended_major = recommended.replace('v', '')

                    if current_major != recommended_major:
                        result.issues.append(ValidationIssue(
                            severity='info',
                            category='best-practice',
                            message=f'Outdated action version: {uses} in job "{job_name}"',
                            file=result.file,
                            suggestion=f'Update to {action}@{recommended}'
                        ))

    def _check_best_practices(self, workflow: Dict, result: ValidationResult):
        """Check for workflow best practices."""
        # Check for concurrency control
        if 'concurrency' not in workflow:
            triggers = workflow.get('on', {})
            if isinstance(triggers, dict) and ('pull_request' in triggers or 'push' in triggers):
                result.issues.append(ValidationIssue(
                    severity='info',
                    category='best-practice',
                    message='No concurrency control configured',
                    file=result.file,
                    suggestion='Add concurrency group to cancel redundant workflow runs'
                ))

        # Check for npm install vs npm ci
        if 'jobs' in workflow:
            for job_name, job in workflow['jobs'].items():
                steps = job.get('steps', [])
                for step in steps:
                    if isinstance(step, dict) and 'run' in step:
                        run_cmd = step['run']
                        if 'npm install' in run_cmd and 'npm ci' not in run_cmd:
                            result.issues.append(ValidationIssue(
                                severity='warning',
                                category='best-practice',
                                message=f'Using "npm install" instead of "npm ci" in job "{job_name}"',
                                file=result.file,
                                suggestion='Use "npm ci" for deterministic installs in CI/CD'
                            ))

        # Check for timeout configuration
        if 'jobs' in workflow:
            for job_name, job in workflow['jobs'].items():
                if 'timeout-minutes' not in job:
                    result.issues.append(ValidationIssue(
                        severity='info',
                        category='best-practice',
                        message=f'No timeout configured for job "{job_name}"',
                        file=result.file,
                        suggestion='Add timeout-minutes to prevent jobs from running indefinitely'
                    ))

    def _check_performance(self, workflow: Dict, result: ValidationResult):
        """Check for performance optimizations."""
        # Check for path filters
        triggers = workflow.get('on', {})
        if isinstance(triggers, dict):
            for trigger in ['push', 'pull_request']:
                if trigger in triggers and isinstance(triggers[trigger], dict):
                    if 'paths' not in triggers[trigger]:
                        result.issues.append(ValidationIssue(
                            severity='info',
                            category='performance',
                            message=f'No path filters on {trigger} trigger',
                            file=result.file,
                            suggestion='Add path filters to avoid unnecessary workflow runs'
                        ))

        # Check for parallel jobs
        if 'jobs' in workflow:
            jobs = workflow['jobs']
            if len(jobs) > 1:
                sequential_count = 0
                for job_name, job in jobs.items():
                    if 'needs' in job:
                        sequential_count += 1

                if sequential_count == len(jobs) - 1:
                    result.issues.append(ValidationIssue(
                        severity='info',
                        category='performance',
                        message='All jobs are sequential',
                        file=result.file,
                        suggestion='Consider parallelizing independent jobs'
                    ))

    def validate_directory(self, directory: Path, recursive: bool = False) -> List[ValidationResult]:
        """Validate all workflow files in a directory."""
        results = []

        if recursive:
            pattern = '**/*.yml'
        else:
            pattern = '*.yml'

        workflow_files = list(directory.glob(pattern))
        workflow_files.extend(directory.glob(pattern.replace('.yml', '.yaml')))

        if not workflow_files:
            print(f"No workflow files found in {directory}", file=sys.stderr)
            return results

        for filepath in workflow_files:
            if filepath.is_file():
                result = self.validate_file(filepath)
                results.append(result)

        return results

    def print_results(self, results: List[ValidationResult], show_suggestions: bool = True):
        """Print validation results in human-readable format."""
        total_errors = sum(r.errors for r in results)
        total_warnings = sum(r.warnings for r in results)
        total_info = sum(r.info for r in results)

        print(f"\nValidation Results for {len(results)} file(s):\n")
        print("=" * 80)

        for result in results:
            status = "✓ VALID" if result.valid else "✗ INVALID"
            print(f"\n{status}: {result.file}")
            print(f"  Errors: {result.errors}, Warnings: {result.warnings}, Info: {result.info}")

            if result.issues:
                print()
                for issue in result.issues:
                    severity_icon = {
                        'error': '✗',
                        'warning': '⚠',
                        'info': 'ℹ'
                    }[issue.severity]

                    location = f":{issue.line}" if issue.line else ""
                    print(f"  {severity_icon} [{issue.severity.upper()}] {issue.category}")
                    print(f"    {issue.message}")
                    if location:
                        print(f"    Location: {issue.file}{location}")
                    if show_suggestions and issue.suggestion:
                        print(f"    Suggestion: {issue.suggestion}")
                    print()

        print("=" * 80)
        print(f"\nSummary:")
        print(f"  Total files: {len(results)}")
        print(f"  Valid files: {sum(1 for r in results if r.valid)}")
        print(f"  Total errors: {total_errors}")
        print(f"  Total warnings: {total_warnings}")
        print(f"  Total info: {total_info}")

        return total_errors == 0

    def export_json(self, results: List[ValidationResult]) -> str:
        """Export results as JSON."""
        output = {
            'total_files': len(results),
            'valid_files': sum(1 for r in results if r.valid),
            'total_errors': sum(r.errors for r in results),
            'total_warnings': sum(r.warnings for r in results),
            'total_info': sum(r.info for r in results),
            'results': []
        }

        for result in results:
            result_dict = {
                'file': result.file,
                'valid': result.valid,
                'errors': result.errors,
                'warnings': result.warnings,
                'info': result.info,
                'issues': [
                    {
                        'severity': issue.severity,
                        'category': issue.category,
                        'message': issue.message,
                        'line': issue.line,
                        'suggestion': issue.suggestion
                    }
                    for issue in result.issues
                ]
            }
            output['results'].append(result_dict)

        return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Validate GitHub Actions workflow files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Validate a single file:
    %(prog)s workflow.yml

  Validate directory:
    %(prog)s .github/workflows/

  Validate recursively with JSON output:
    %(prog)s . --recursive --json

  Show fix suggestions:
    %(prog)s workflow.yml --fix-suggestions
        """
    )

    parser.add_argument(
        'path',
        help='Path to workflow file or directory'
    )

    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Recursively search for workflow files'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    parser.add_argument(
        '--fix-suggestions',
        action='store_true',
        default=True,
        help='Show fix suggestions (default: true)'
    )

    parser.add_argument(
        '--no-suggestions',
        action='store_true',
        help='Hide fix suggestions'
    )

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        sys.exit(1)

    validator = WorkflowValidator()

    if path.is_file():
        results = [validator.validate_file(path)]
    else:
        results = validator.validate_directory(path, args.recursive)

    if not results:
        print("No workflow files found to validate", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(validator.export_json(results))
    else:
        show_suggestions = args.fix_suggestions and not args.no_suggestions
        success = validator.print_results(results, show_suggestions)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
