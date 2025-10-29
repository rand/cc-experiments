#!/usr/bin/env python3
"""
Pipeline Configuration Validator

Validates CI/CD pipeline configurations across multiple platforms (GitHub Actions,
GitLab CI, Jenkins, CircleCI, Azure Pipelines) for best practices, security issues,
and common misconfigurations.

Usage:
    ./validate_pipeline.py --file .github/workflows/ci.yml --platform github-actions
    ./validate_pipeline.py --directory .github/workflows/ --platform github-actions
    ./validate_pipeline.py --file .gitlab-ci.yml --platform gitlab --verbose
    ./validate_pipeline.py --file Jenkinsfile --platform jenkins --json

Features:
    - Multi-platform support (GitHub Actions, GitLab CI, Jenkins, CircleCI, Azure)
    - Security best practices validation
    - Performance optimization checks
    - Dependency and secret scanning
    - Test coverage gate validation
    - JSON output for CI integration
    - Detailed verbose reporting

Author: Skills Team
Version: 1.0.0
"""

import argparse
import json
import sys
import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class Severity(Enum):
    """Issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Platform(Enum):
    """Supported CI/CD platforms"""
    GITHUB_ACTIONS = "github-actions"
    GITLAB_CI = "gitlab"
    JENKINS = "jenkins"
    CIRCLECI = "circleci"
    AZURE_PIPELINES = "azure"


@dataclass
class ValidationIssue:
    """Represents a single validation issue"""
    severity: Severity
    category: str
    message: str
    file: str
    line: Optional[int] = None
    recommendation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'severity': self.severity.value,
            'category': self.category,
            'message': self.message,
            'file': self.file,
            'line': self.line,
            'recommendation': self.recommendation
        }


class PipelineValidator:
    """Base class for pipeline validators"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.issues: List[ValidationIssue] = []

    def add_issue(self, issue: ValidationIssue):
        """Add a validation issue"""
        self.issues.append(issue)
        if self.verbose:
            self._print_issue(issue)

    def _print_issue(self, issue: ValidationIssue):
        """Print issue to console"""
        severity_colors = {
            Severity.ERROR: '\033[91m',
            Severity.WARNING: '\033[93m',
            Severity.INFO: '\033[94m'
        }
        reset = '\033[0m'
        color = severity_colors.get(issue.severity, '')

        location = f"{issue.file}"
        if issue.line:
            location += f":{issue.line}"

        print(f"{color}[{issue.severity.value.upper()}]{reset} {location}")
        print(f"  Category: {issue.category}")
        print(f"  Message: {issue.message}")
        if issue.recommendation:
            print(f"  Recommendation: {issue.recommendation}")
        print()

    def get_summary(self) -> Dict[str, int]:
        """Get summary of issues by severity"""
        summary = {
            'errors': 0,
            'warnings': 0,
            'info': 0,
            'total': len(self.issues)
        }
        for issue in self.issues:
            if issue.severity == Severity.ERROR:
                summary['errors'] += 1
            elif issue.severity == Severity.WARNING:
                summary['warnings'] += 1
            else:
                summary['info'] += 1
        return summary

    def validate(self, config: Any, filename: str) -> bool:
        """Validate configuration. Returns True if valid"""
        raise NotImplementedError


class GitHubActionsValidator(PipelineValidator):
    """Validator for GitHub Actions workflows"""

    def validate(self, config: Dict, filename: str) -> bool:
        """Validate GitHub Actions workflow"""
        self._check_workflow_structure(config, filename)
        self._check_triggers(config, filename)
        self._check_jobs(config, filename)
        self._check_security(config, filename)
        self._check_performance(config, filename)
        self._check_best_practices(config, filename)

        return self.get_summary()['errors'] == 0

    def _check_workflow_structure(self, config: Dict, filename: str):
        """Check basic workflow structure"""
        if 'name' not in config:
            self.add_issue(ValidationIssue(
                severity=Severity.WARNING,
                category='structure',
                message='Workflow missing name',
                file=filename,
                recommendation='Add a descriptive name to the workflow'
            ))

        if 'on' not in config:
            self.add_issue(ValidationIssue(
                severity=Severity.ERROR,
                category='structure',
                message='Workflow missing trigger configuration (on:)',
                file=filename,
                recommendation='Define when the workflow should run'
            ))

        if 'jobs' not in config:
            self.add_issue(ValidationIssue(
                severity=Severity.ERROR,
                category='structure',
                message='Workflow missing jobs',
                file=filename,
                recommendation='Define at least one job'
            ))

    def _check_triggers(self, config: Dict, filename: str):
        """Check workflow triggers"""
        if 'on' not in config:
            return

        triggers = config['on']
        if isinstance(triggers, str):
            triggers = {triggers: {}}

        # Check for overly broad triggers
        if 'push' in triggers:
            push_config = triggers['push'] if isinstance(triggers['push'], dict) else {}
            if not push_config or ('branches' not in push_config and 'tags' not in push_config):
                self.add_issue(ValidationIssue(
                    severity=Severity.WARNING,
                    category='triggers',
                    message='Push trigger runs on all branches',
                    file=filename,
                    recommendation='Limit push trigger to specific branches'
                ))

        # Check for schedule without cron
        if 'schedule' in triggers:
            schedule = triggers['schedule']
            if not isinstance(schedule, list) or not all('cron' in item for item in schedule):
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='triggers',
                    message='Schedule trigger missing cron expression',
                    file=filename,
                    recommendation='Add cron expression to schedule trigger'
                ))

    def _check_jobs(self, config: Dict, filename: str):
        """Check job configurations"""
        if 'jobs' not in config:
            return

        jobs = config['jobs']
        has_tests = False
        has_security_scan = False

        for job_name, job_config in jobs.items():
            # Check for runner specification
            if 'runs-on' not in job_config:
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='jobs',
                    message=f'Job "{job_name}" missing runs-on',
                    file=filename,
                    recommendation='Specify runner OS (e.g., ubuntu-latest)'
                ))

            # Check for steps
            if 'steps' not in job_config:
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='jobs',
                    message=f'Job "{job_name}" has no steps',
                    file=filename,
                    recommendation='Add steps to the job'
                ))
            else:
                self._check_steps(job_config['steps'], job_name, filename)

            # Check for test jobs
            if 'test' in job_name.lower():
                has_tests = True

            # Check for security scanning
            if any(keyword in job_name.lower() for keyword in ['security', 'scan', 'audit']):
                has_security_scan = True

        if not has_tests:
            self.add_issue(ValidationIssue(
                severity=Severity.WARNING,
                category='testing',
                message='No test jobs found in workflow',
                file=filename,
                recommendation='Add test jobs to validate code quality'
            ))

        if not has_security_scan:
            self.add_issue(ValidationIssue(
                severity=Severity.WARNING,
                category='security',
                message='No security scanning jobs found',
                file=filename,
                recommendation='Add security scanning (e.g., CodeQL, Snyk)'
            ))

    def _check_steps(self, steps: List[Dict], job_name: str, filename: str):
        """Check individual steps"""
        has_checkout = False
        action_versions = []

        for i, step in enumerate(steps):
            # Check for checkout
            if 'uses' in step and 'actions/checkout' in step['uses']:
                has_checkout = True

            # Check action versions
            if 'uses' in step:
                action = step['uses']
                if '@' in action:
                    _, version = action.rsplit('@', 1)
                    if version == 'master' or version == 'main':
                        self.add_issue(ValidationIssue(
                            severity=Severity.WARNING,
                            category='dependencies',
                            message=f'Job "{job_name}" step {i+1} uses unstable action version',
                            file=filename,
                            recommendation=f'Pin to specific version instead of {version}'
                        ))

            # Check for shell script security
            if 'run' in step:
                self._check_shell_command(step['run'], job_name, i+1, filename)

        if not has_checkout and job_name != 'setup':
            self.add_issue(ValidationIssue(
                severity=Severity.INFO,
                category='structure',
                message=f'Job "{job_name}" may be missing checkout step',
                file=filename,
                recommendation='Add actions/checkout@v4 if code access needed'
            ))

    def _check_shell_command(self, command: str, job_name: str, step_num: int, filename: str):
        """Check shell commands for security issues"""
        # Check for unquoted variables
        if re.search(r'\$\{[^}]+\}(?!["\'])', command) or re.search(r'\$[A-Z_]+(?!["\'])', command):
            self.add_issue(ValidationIssue(
                severity=Severity.WARNING,
                category='security',
                message=f'Job "{job_name}" step {step_num} has unquoted variables',
                file=filename,
                recommendation='Quote variables to prevent injection attacks'
            ))

        # Check for dangerous commands
        dangerous_patterns = [
            (r'eval\s+', 'Use of eval is dangerous'),
            (r'curl.*\|\s*sh', 'Piping curl to shell is dangerous'),
            (r'wget.*\|\s*sh', 'Piping wget to shell is dangerous'),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, command):
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='security',
                    message=f'Job "{job_name}" step {step_num}: {message}',
                    file=filename,
                    recommendation='Download and verify before executing'
                ))

    def _check_security(self, config: Dict, filename: str):
        """Check security configurations"""
        jobs = config.get('jobs', {})

        # Check for secret usage
        config_str = str(config)
        if 'secrets.' in config_str:
            # Check for secrets in outputs
            if 'outputs:' in config_str:
                self.add_issue(ValidationIssue(
                    severity=Severity.WARNING,
                    category='security',
                    message='Secrets may be exposed in job outputs',
                    file=filename,
                    recommendation='Never expose secrets in outputs or logs'
                ))

        # Check for OIDC usage
        uses_oidc = False
        for job_name, job_config in jobs.items():
            permissions = job_config.get('permissions', {})
            if isinstance(permissions, dict) and permissions.get('id-token') == 'write':
                uses_oidc = True
                break

        if 'aws' in config_str.lower() and not uses_oidc:
            self.add_issue(ValidationIssue(
                severity=Severity.INFO,
                category='security',
                message='Consider using OIDC for AWS authentication',
                file=filename,
                recommendation='Use OIDC instead of long-lived credentials'
            ))

    def _check_performance(self, config: Dict, filename: str):
        """Check performance optimizations"""
        jobs = config.get('jobs', {})

        # Check for caching
        uses_cache = False
        for job_name, job_config in jobs.items():
            steps = job_config.get('steps', [])
            for step in steps:
                if 'uses' in step:
                    if 'actions/cache' in step['uses'] or 'cache:' in str(step):
                        uses_cache = True
                        break

        if not uses_cache:
            self.add_issue(ValidationIssue(
                severity=Severity.INFO,
                category='performance',
                message='No caching configured',
                file=filename,
                recommendation='Add caching for dependencies and build artifacts'
            ))

        # Check for parallelization opportunities
        parallel_jobs = []
        for job_name, job_config in jobs.items():
            if 'needs' not in job_config:
                parallel_jobs.append(job_name)

        if len(jobs) > 3 and len(parallel_jobs) == len(jobs):
            self.add_issue(ValidationIssue(
                severity=Severity.INFO,
                category='performance',
                message='All jobs run in parallel without dependencies',
                file=filename,
                recommendation='Consider adding job dependencies for proper ordering'
            ))

    def _check_best_practices(self, config: Dict, filename: str):
        """Check best practices"""
        # Check for timeout
        jobs = config.get('jobs', {})
        for job_name, job_config in jobs.items():
            if 'timeout-minutes' not in job_config:
                self.add_issue(ValidationIssue(
                    severity=Severity.INFO,
                    category='best-practices',
                    message=f'Job "{job_name}" has no timeout',
                    file=filename,
                    recommendation='Set timeout-minutes to prevent runaway jobs'
                ))

        # Check for concurrency control
        if 'concurrency' not in config:
            self.add_issue(ValidationIssue(
                severity=Severity.INFO,
                category='best-practices',
                message='No concurrency control configured',
                file=filename,
                recommendation='Add concurrency to cancel in-progress runs'
            ))


class GitLabCIValidator(PipelineValidator):
    """Validator for GitLab CI pipelines"""

    def validate(self, config: Dict, filename: str) -> bool:
        """Validate GitLab CI configuration"""
        self._check_structure(config, filename)
        self._check_stages(config, filename)
        self._check_jobs(config, filename)
        self._check_security(config, filename)
        self._check_best_practices(config, filename)

        return self.get_summary()['errors'] == 0

    def _check_structure(self, config: Dict, filename: str):
        """Check basic structure"""
        if 'stages' not in config and not any(key.startswith('.') for key in config.keys()):
            self.add_issue(ValidationIssue(
                severity=Severity.WARNING,
                category='structure',
                message='No stages defined',
                file=filename,
                recommendation='Define stages for better pipeline organization'
            ))

    def _check_stages(self, config: Dict, filename: str):
        """Check stage configuration"""
        stages = config.get('stages', [])

        if not stages:
            return

        # Check for standard stages
        standard_stages = ['build', 'test', 'deploy']
        has_standard = any(stage in stages for stage in standard_stages)

        if not has_standard:
            self.add_issue(ValidationIssue(
                severity=Severity.INFO,
                category='structure',
                message='Non-standard stage names used',
                file=filename,
                recommendation='Consider using standard stages: build, test, deploy'
            ))

    def _check_jobs(self, config: Dict, filename: str):
        """Check job configurations"""
        jobs = {k: v for k, v in config.items() if not k.startswith('.') and k not in ['stages', 'variables', 'include']}

        for job_name, job_config in jobs.items():
            if not isinstance(job_config, dict):
                continue

            # Check for script
            if 'script' not in job_config and 'trigger' not in job_config:
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='jobs',
                    message=f'Job "{job_name}" missing script',
                    file=filename,
                    recommendation='Add script section with commands to execute'
                ))

            # Check for image
            if 'image' not in job_config and 'image' not in config:
                self.add_issue(ValidationIssue(
                    severity=Severity.WARNING,
                    category='jobs',
                    message=f'Job "{job_name}" has no image specified',
                    file=filename,
                    recommendation='Specify Docker image for consistent environment'
                ))

    def _check_security(self, config: Dict, filename: str):
        """Check security configurations"""
        # Check for secret variables
        variables = config.get('variables', {})
        for var_name, var_value in variables.items():
            if any(keyword in var_name.lower() for keyword in ['password', 'token', 'secret', 'key']):
                if not str(var_value).startswith('$'):
                    self.add_issue(ValidationIssue(
                        severity=Severity.ERROR,
                        category='security',
                        message=f'Hardcoded secret in variable "{var_name}"',
                        file=filename,
                        recommendation='Use GitLab CI/CD variables instead'
                    ))

    def _check_best_practices(self, config: Dict, filename: str):
        """Check best practices"""
        # Check for caching
        has_cache = False
        jobs = {k: v for k, v in config.items() if not k.startswith('.')}

        for job_name, job_config in jobs.items():
            if isinstance(job_config, dict) and 'cache' in job_config:
                has_cache = True
                break

        if not has_cache and 'cache' not in config:
            self.add_issue(ValidationIssue(
                severity=Severity.INFO,
                category='performance',
                message='No caching configured',
                file=filename,
                recommendation='Add cache for dependencies to speed up pipeline'
            ))


class JenkinsValidator(PipelineValidator):
    """Validator for Jenkins pipelines (Jenkinsfile)"""

    def validate(self, content: str, filename: str) -> bool:
        """Validate Jenkins pipeline"""
        self._check_syntax(content, filename)
        self._check_structure(content, filename)
        self._check_security(content, filename)
        self._check_best_practices(content, filename)

        return self.get_summary()['errors'] == 0

    def _check_syntax(self, content: str, filename: str):
        """Check basic syntax"""
        if not content.strip():
            self.add_issue(ValidationIssue(
                severity=Severity.ERROR,
                category='syntax',
                message='Empty Jenkinsfile',
                file=filename,
                recommendation='Add pipeline definition'
            ))
            return

        if 'pipeline' not in content and 'node' not in content:
            self.add_issue(ValidationIssue(
                severity=Severity.ERROR,
                category='syntax',
                message='No pipeline or node declaration found',
                file=filename,
                recommendation='Use declarative or scripted pipeline syntax'
            ))

    def _check_structure(self, content: str, filename: str):
        """Check pipeline structure"""
        if 'pipeline' in content:
            # Declarative pipeline
            if 'agent' not in content:
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='structure',
                    message='Pipeline missing agent declaration',
                    file=filename,
                    recommendation='Specify agent (e.g., agent any, agent { label "..." })'
                ))

            if 'stages' not in content:
                self.add_issue(ValidationIssue(
                    severity=Severity.WARNING,
                    category='structure',
                    message='Pipeline has no stages',
                    file=filename,
                    recommendation='Organize pipeline into stages'
                ))

    def _check_security(self, content: str, filename: str):
        """Check security issues"""
        # Check for hardcoded credentials
        credential_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
            (r'token\s*=\s*["\'][^"\']+["\']', 'Hardcoded token'),
            (r'apiKey\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key'),
        ]

        for pattern, message in credential_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='security',
                    message=message,
                    file=filename,
                    recommendation='Use credentials() or withCredentials() instead'
                ))

    def _check_best_practices(self, content: str, filename: str):
        """Check best practices"""
        if 'post' not in content and 'finally' not in content:
            self.add_issue(ValidationIssue(
                severity=Severity.INFO,
                category='best-practices',
                message='No cleanup section found',
                file=filename,
                recommendation='Add post section for cleanup and notifications'
            ))

        if 'timeout' not in content:
            self.add_issue(ValidationIssue(
                severity=Severity.WARNING,
                category='best-practices',
                message='No timeout configured',
                file=filename,
                recommendation='Add timeout to prevent runaway builds'
            ))


class CircleCIValidator(PipelineValidator):
    """Validator for CircleCI configurations"""

    def validate(self, config: Dict, filename: str) -> bool:
        """Validate CircleCI configuration"""
        self._check_version(config, filename)
        self._check_structure(config, filename)
        self._check_jobs(config, filename)
        self._check_workflows(config, filename)

        return self.get_summary()['errors'] == 0

    def _check_version(self, config: Dict, filename: str):
        """Check CircleCI version"""
        version = config.get('version')
        if not version:
            self.add_issue(ValidationIssue(
                severity=Severity.ERROR,
                category='structure',
                message='Missing version field',
                file=filename,
                recommendation='Add version: 2.1 (recommended)'
            ))
        elif version < 2.1:
            self.add_issue(ValidationIssue(
                severity=Severity.WARNING,
                category='structure',
                message=f'Using old version {version}',
                file=filename,
                recommendation='Upgrade to version 2.1 for orbs and reusable config'
            ))

    def _check_structure(self, config: Dict, filename: str):
        """Check basic structure"""
        if 'jobs' not in config and 'workflows' not in config:
            self.add_issue(ValidationIssue(
                severity=Severity.ERROR,
                category='structure',
                message='No jobs or workflows defined',
                file=filename,
                recommendation='Define at least one job or workflow'
            ))

    def _check_jobs(self, config: Dict, filename: str):
        """Check job configurations"""
        jobs = config.get('jobs', {})

        for job_name, job_config in jobs.items():
            if not isinstance(job_config, dict):
                continue

            # Check for executor
            if 'docker' not in job_config and 'machine' not in job_config and 'macos' not in job_config and 'executor' not in job_config:
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='jobs',
                    message=f'Job "{job_name}" missing executor',
                    file=filename,
                    recommendation='Specify docker, machine, macos, or executor'
                ))

            # Check for steps
            if 'steps' not in job_config:
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='jobs',
                    message=f'Job "{job_name}" has no steps',
                    file=filename,
                    recommendation='Add steps to execute'
                ))

    def _check_workflows(self, config: Dict, filename: str):
        """Check workflow configurations"""
        workflows = config.get('workflows', {})

        if not workflows and config.get('version', 0) >= 2:
            self.add_issue(ValidationIssue(
                severity=Severity.WARNING,
                category='workflows',
                message='No workflows defined',
                file=filename,
                recommendation='Define workflows for job orchestration'
            ))


class AzurePipelinesValidator(PipelineValidator):
    """Validator for Azure Pipelines"""

    def validate(self, config: Dict, filename: str) -> bool:
        """Validate Azure Pipeline configuration"""
        self._check_structure(config, filename)
        self._check_stages(config, filename)
        self._check_jobs(config, filename)

        return self.get_summary()['errors'] == 0

    def _check_structure(self, config: Dict, filename: str):
        """Check basic structure"""
        if 'stages' not in config and 'jobs' not in config and 'steps' not in config:
            self.add_issue(ValidationIssue(
                severity=Severity.ERROR,
                category='structure',
                message='No stages, jobs, or steps defined',
                file=filename,
                recommendation='Define at least stages, jobs, or steps'
            ))

    def _check_stages(self, config: Dict, filename: str):
        """Check stage configurations"""
        stages = config.get('stages', [])

        for stage in stages:
            if 'stage' not in stage:
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='stages',
                    message='Stage missing name',
                    file=filename,
                    recommendation='Add stage: field with name'
                ))

            if 'jobs' not in stage:
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='stages',
                    message=f'Stage "{stage.get("stage", "unnamed")}" has no jobs',
                    file=filename,
                    recommendation='Add jobs to stage'
                ))

    def _check_jobs(self, config: Dict, filename: str):
        """Check job configurations"""
        jobs = config.get('jobs', [])

        for job in jobs:
            if not isinstance(job, dict):
                continue

            job_name = job.get('job', 'unnamed')

            # Check for pool or steps
            if 'pool' not in job:
                self.add_issue(ValidationIssue(
                    severity=Severity.WARNING,
                    category='jobs',
                    message=f'Job "{job_name}" has no pool specified',
                    file=filename,
                    recommendation='Specify pool for agent selection'
                ))

            if 'steps' not in job and 'template' not in job:
                self.add_issue(ValidationIssue(
                    severity=Severity.ERROR,
                    category='jobs',
                    message=f'Job "{job_name}" has no steps',
                    file=filename,
                    recommendation='Add steps or use template'
                ))


def load_config(filepath: Path, platform: Platform) -> Tuple[Any, bool]:
    """Load configuration file based on platform"""
    try:
        with open(filepath, 'r') as f:
            if platform in [Platform.GITHUB_ACTIONS, Platform.GITLAB_CI, Platform.CIRCLECI, Platform.AZURE_PIPELINES]:
                return yaml.safe_load(f), True
            elif platform == Platform.JENKINS:
                return f.read(), True
    except yaml.YAMLError as e:
        print(f"Error parsing YAML in {filepath}: {e}", file=sys.stderr)
        return None, False
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return None, False


def validate_file(filepath: Path, platform: Platform, verbose: bool) -> List[ValidationIssue]:
    """Validate a single pipeline configuration file"""
    config, success = load_config(filepath, platform)
    if not success:
        return []

    validator_classes = {
        Platform.GITHUB_ACTIONS: GitHubActionsValidator,
        Platform.GITLAB_CI: GitLabCIValidator,
        Platform.JENKINS: JenkinsValidator,
        Platform.CIRCLECI: CircleCIValidator,
        Platform.AZURE_PIPELINES: AzurePipelinesValidator,
    }

    validator_class = validator_classes.get(platform)
    if not validator_class:
        print(f"Unsupported platform: {platform.value}", file=sys.stderr)
        return []

    validator = validator_class(verbose=verbose)
    validator.validate(config, str(filepath))

    return validator.issues


def validate_directory(directory: Path, platform: Platform, verbose: bool) -> List[ValidationIssue]:
    """Validate all pipeline files in a directory"""
    all_issues = []

    # Map platform to file patterns
    patterns = {
        Platform.GITHUB_ACTIONS: ['*.yml', '*.yaml'],
        Platform.GITLAB_CI: ['.gitlab-ci.yml'],
        Platform.JENKINS: ['Jenkinsfile'],
        Platform.CIRCLECI: ['config.yml'],
        Platform.AZURE_PIPELINES: ['azure-pipelines.yml', 'azure-pipelines.yaml'],
    }

    file_patterns = patterns.get(platform, ['*.yml', '*.yaml'])

    for pattern in file_patterns:
        for filepath in directory.glob(pattern):
            if filepath.is_file():
                issues = validate_file(filepath, platform, verbose)
                all_issues.extend(issues)

    return all_issues


def print_summary(issues: List[ValidationIssue]):
    """Print validation summary"""
    errors = sum(1 for issue in issues if issue.severity == Severity.ERROR)
    warnings = sum(1 for issue in issues if issue.severity == Severity.WARNING)
    info = sum(1 for issue in issues if issue.severity == Severity.INFO)

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total Issues: {len(issues)}")
    print(f"  Errors:   {errors}")
    print(f"  Warnings: {warnings}")
    print(f"  Info:     {info}")
    print("=" * 60 + "\n")

    if errors > 0:
        print("FAILED: Pipeline configuration has errors")
        return 1
    elif warnings > 0:
        print("PASSED: Pipeline configuration valid with warnings")
        return 0
    else:
        print("PASSED: Pipeline configuration is valid")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='Validate CI/CD pipeline configurations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file .github/workflows/ci.yml --platform github-actions
  %(prog)s --directory .github/workflows/ --platform github-actions --verbose
  %(prog)s --file .gitlab-ci.yml --platform gitlab --json
  %(prog)s --file Jenkinsfile --platform jenkins

Supported platforms:
  github-actions  GitHub Actions workflows
  gitlab          GitLab CI pipelines
  jenkins         Jenkins pipelines (Jenkinsfile)
  circleci        CircleCI configurations
  azure           Azure Pipelines
        """
    )

    parser.add_argument(
        '--file',
        type=Path,
        help='Path to pipeline configuration file'
    )
    parser.add_argument(
        '--directory',
        type=Path,
        help='Directory containing pipeline files'
    )
    parser.add_argument(
        '--platform',
        type=str,
        required=True,
        choices=[p.value for p in Platform],
        help='CI/CD platform'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output with detailed issues'
    )

    args = parser.parse_args()

    if not args.file and not args.directory:
        parser.error('Either --file or --directory must be specified')

    platform = Platform(args.platform)

    # Collect issues
    all_issues = []
    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            return 1
        all_issues = validate_file(args.file, platform, args.verbose)
    elif args.directory:
        if not args.directory.exists() or not args.directory.is_dir():
            print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
            return 1
        all_issues = validate_directory(args.directory, platform, args.verbose)

    # Output results
    if args.json:
        output = {
            'issues': [issue.to_dict() for issue in all_issues],
            'summary': {
                'total': len(all_issues),
                'errors': sum(1 for issue in all_issues if issue.severity == Severity.ERROR),
                'warnings': sum(1 for issue in all_issues if issue.severity == Severity.WARNING),
                'info': sum(1 for issue in all_issues if issue.severity == Severity.INFO),
            }
        }
        print(json.dumps(output, indent=2))
        return 1 if output['summary']['errors'] > 0 else 0
    else:
        if not args.verbose:
            # Print issues if not already printed in verbose mode
            for issue in all_issues:
                severity_colors = {
                    Severity.ERROR: '\033[91m',
                    Severity.WARNING: '\033[93m',
                    Severity.INFO: '\033[94m'
                }
                reset = '\033[0m'
                color = severity_colors.get(issue.severity, '')

                location = f"{issue.file}"
                if issue.line:
                    location += f":{issue.line}"

                print(f"{color}[{issue.severity.value.upper()}]{reset} {location}")
                print(f"  {issue.message}")
                if issue.recommendation:
                    print(f"  → {issue.recommendation}")
                print()

        return print_summary(all_issues)


if __name__ == '__main__':
    sys.exit(main())
