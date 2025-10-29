#!/usr/bin/env python3
"""
Validate Level 3 Resources for all skills with production-ready checks.

Checks:
- REFERENCE.md exists and is within 1,500-4,000 line range
- All scripts are executable and have proper shebang
- Scripts have --help and --json support (basic check)
- No TODO/stub/mock comments in scripts
- Minimum number of examples present

Enhanced Production-Ready Checks:
- Script quality: type hints, error handling, logging, --dry-run flags, input sanitization
- Security: hardcoded secrets, unsafe subprocess, HTTPS enforcement, authentication
- Example quality: READMEs, dependency files, Docker security, health checks, error handling
- Documentation: TOC, anti-patterns section, references, docstrings, inline comments
- Production readiness: rate limiting, timeouts, retry logic, graceful shutdown, resource cleanup

Usage:
    ./validate_resources.py                           # Validate all skills (basic checks)
    ./validate_resources.py --check-security          # Include security checks
    ./validate_resources.py --check-production-ready  # Include production readiness checks
    ./validate_resources.py --strict-mode             # All checks + strict validation
    ./validate_resources.py --skill grpc              # Validate specific skill
    ./validate_resources.py --json                    # JSON output
    ./validate_resources.py --strict                  # Fail on warnings
"""

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class ValidationResult:
    """Result of validating a single skill's resources."""
    skill_path: str
    skill_name: str
    status: str  # 'pass', 'warn', 'fail'
    issues: List[str]
    warnings: List[str]
    stats: Dict[str, any]
    security_findings: List[Dict] = field(default_factory=list)
    quality_findings: List[Dict] = field(default_factory=list)
    production_findings: List[Dict] = field(default_factory=list)

class ResourceValidator:
    """Validator for Level 3 Resources with enhanced production checks."""

    def __init__(
        self,
        skills_dir: Path,
        strict: bool = False,
        check_security: bool = False,
        check_production: bool = False,
        strict_mode: bool = False
    ):
        self.skills_dir = skills_dir
        self.strict = strict or strict_mode
        self.check_security = check_security or strict_mode
        self.check_production = check_production or strict_mode
        self.strict_mode = strict_mode
        self.results: List[ValidationResult] = []

        # Security patterns (from security_audit.py)
        self._init_security_patterns()

        # Production readiness patterns
        self._init_production_patterns()

    def _init_security_patterns(self):
        """Initialize security check patterns."""
        self.secrets_patterns = {
            r'(?i)api[_-]?key\s*[:=]\s*["\'](?!test|fake|example|YOUR_|placeholder|xxx|<)[A-Za-z0-9+/]{20,}':
                'Possible hardcoded API key',
            r'(?i)password\s*[:=]\s*["\'](?!test|fake|example|pass|password|YOUR_|placeholder|xxx|<)[^\'"]{8,}':
                'Possible hardcoded password',
            r'(?i)secret\s*[:=]\s*["\'](?!test|fake|example|YOUR_|placeholder|xxx|<)[A-Za-z0-9+/]{20,}':
                'Possible hardcoded secret',
            r'(?i)-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----':
                'Private key in file',
        }

        self.unsafe_subprocess_patterns = {
            r'shell\s*=\s*True': 'Unsafe shell=True in subprocess',
            r'os\.system\s*\(': 'Unsafe os.system() usage',
            r'\beval\s*\(': 'Dangerous eval() usage',
            r'\bexec\s*\(': 'Dangerous exec() usage',
        }

        self.http_patterns = {
            r'(?<!https:)http://(?!localhost|127\.0\.0\.1|example\.com|0\.0\.0\.0)':
                'Unencrypted HTTP URL (use HTTPS)',
        }

    def _init_production_patterns(self):
        """Initialize production readiness patterns."""
        self.rate_limit_patterns = {
            r'while\s+True\s*:(?!\s*\n.*(?:sleep|time\.sleep|await\s+asyncio\.sleep|break))':
                'Infinite loop without rate limiting',
            r'requests\.\w+\s*\([^)]*(?!timeout)':
                'HTTP request without timeout',
        }

        self.retry_patterns = {
            r'(?:requests|urllib|aiohttp|httpx)\.\w+\s*\(': 'Check for retry logic',
        }

        self.cleanup_patterns = {
            r'\bopen\s*\((?![^)]*with\b)': 'File opened without context manager',
        }

    def validate_all(self) -> List[ValidationResult]:
        """Validate all skills with resources."""
        skills_with_resources = self._find_skills_with_resources()

        for skill_path in sorted(skills_with_resources):
            result = self.validate_skill(skill_path)
            self.results.append(result)

        return self.results

    def validate_skill(self, skill_path: Path) -> ValidationResult:
        """Validate a single skill's resources with enhanced checks."""
        skill_name = self._get_skill_name(skill_path)
        resources_dir = skill_path / "resources"

        issues = []
        warnings = []
        stats = {}
        security_findings = []
        quality_findings = []
        production_findings = []

        # Basic checks
        ref_check = self._check_reference_md(resources_dir)
        issues.extend(ref_check['errors'])
        warnings.extend(ref_check['warnings'])
        stats['reference_lines'] = ref_check['lines']

        # Enhanced documentation checks
        if self.check_production or self.strict_mode:
            doc_check = self._check_documentation_quality(resources_dir)
            warnings.extend(doc_check['warnings'])
            quality_findings.extend(doc_check['findings'])
            stats.update(doc_check['stats'])

        # Scripts validation
        scripts_check = self._check_scripts(resources_dir)
        issues.extend(scripts_check['errors'])
        warnings.extend(scripts_check['warnings'])
        stats['scripts_count'] = scripts_check['count']
        stats['scripts_executable'] = scripts_check['executable']

        # Enhanced script quality checks
        if self.check_production or self.strict_mode:
            quality_check = self._check_script_quality(resources_dir)
            warnings.extend(quality_check['warnings'])
            quality_findings.extend(quality_check['findings'])
            stats.update(quality_check['stats'])

        # Security checks
        if self.check_security or self.strict_mode:
            security_check = self._check_security(resources_dir)
            if security_check['critical']:
                issues.extend(security_check['critical'])
            warnings.extend(security_check['warnings'])
            security_findings.extend(security_check['findings'])
            stats.update(security_check['stats'])

        # Examples validation
        examples_check = self._check_examples(resources_dir)
        warnings.extend(examples_check['warnings'])
        stats['examples_count'] = examples_check['count']

        # Enhanced example quality checks
        if self.check_production or self.strict_mode:
            example_quality = self._check_example_quality(resources_dir)
            warnings.extend(example_quality['warnings'])
            quality_findings.extend(example_quality['findings'])
            stats.update(example_quality['stats'])

        # Production readiness checks
        if self.check_production or self.strict_mode:
            prod_check = self._check_production_readiness(resources_dir)
            warnings.extend(prod_check['warnings'])
            production_findings.extend(prod_check['findings'])
            stats.update(prod_check['stats'])

        # Determine status
        if issues:
            status = 'fail'
        elif warnings and self.strict:
            status = 'fail'
        elif warnings:
            status = 'warn'
        else:
            status = 'pass'

        return ValidationResult(
            skill_path=str(skill_path.relative_to(self.skills_dir)),
            skill_name=skill_name,
            status=status,
            issues=issues,
            warnings=warnings,
            stats=stats,
            security_findings=security_findings,
            quality_findings=quality_findings,
            production_findings=production_findings
        )

    def _find_skills_with_resources(self) -> List[Path]:
        """Find all skill directories that have resources/ subdirectory."""
        skills = []

        # Search in main skills directory and category subdirectories
        for category_dir in self.skills_dir.iterdir():
            if not category_dir.is_dir():
                continue

            # Check if category has resources/ directly (e.g., engineering/resources/sre-practices)
            if (category_dir / "resources").exists():
                # Find skill directories under resources/
                resources_dir = category_dir / "resources"
                for skill_dir in resources_dir.iterdir():
                    if skill_dir.is_dir() and (skill_dir / "REFERENCE.md").exists():
                        skills.append(skill_dir.parent.parent / skill_dir.name)

            # Check for individual skill directories with resources/
            for item in category_dir.iterdir():
                if item.is_dir() and (item / "resources").exists():
                    skills.append(item)

        return skills

    def _get_skill_name(self, skill_path: Path) -> str:
        """Extract skill name from path."""
        # Handle both formats:
        # - category/skill-name/resources
        # - category/resources/skill-name
        parts = skill_path.parts
        if 'resources' in parts:
            idx = parts.index('resources')
            if idx > 0 and idx < len(parts) - 1:
                # Format: category/resources/skill-name
                return parts[-1]
            else:
                # Format: category/skill-name/resources
                return parts[-2] if len(parts) > 1 else parts[-1]
        return skill_path.name

    def _check_reference_md(self, resources_dir: Path) -> Dict:
        """Check REFERENCE.md file."""
        result = {'errors': [], 'warnings': [], 'lines': 0}

        ref_path = resources_dir / "REFERENCE.md"

        if not ref_path.exists():
            result['errors'].append("REFERENCE.md not found")
            return result

        # Count lines
        try:
            lines = len(ref_path.read_text().splitlines())
            result['lines'] = lines

            if lines < 1500:
                result['errors'].append(f"REFERENCE.md too short: {lines} lines (minimum 1,500)")
            elif lines > 4000:
                result['warnings'].append(f"REFERENCE.md very long: {lines} lines (target max 4,000)")
        except Exception as e:
            result['errors'].append(f"Error reading REFERENCE.md: {e}")

        return result

    def _check_scripts(self, resources_dir: Path) -> Dict:
        """Check scripts directory."""
        result = {'errors': [], 'warnings': [], 'count': 0, 'executable': 0}

        scripts_dir = resources_dir / "scripts"

        if not scripts_dir.exists():
            result['errors'].append("scripts/ directory not found")
            return result

        # Find all Python scripts
        scripts = list(scripts_dir.glob("*.py"))
        result['count'] = len(scripts)

        if len(scripts) < 3:
            result['warnings'].append(f"Only {len(scripts)} scripts found (expected 3)")

        for script in scripts:
            # Check executable
            if script.stat().st_mode & 0o111:
                result['executable'] += 1
            else:
                result['errors'].append(f"{script.name} is not executable")

            # Check shebang
            try:
                first_line = script.read_text().split('\n')[0]
                if not first_line.startswith('#!'):
                    result['errors'].append(f"{script.name} missing shebang")
                elif 'python' not in first_line.lower():
                    result['warnings'].append(f"{script.name} shebang doesn't reference python")
            except Exception as e:
                result['errors'].append(f"Error reading {script.name}: {e}")

            # Check for TODO/stub/mock comments
            try:
                content = script.read_text()
                if re.search(r'\bTODO\b', content, re.IGNORECASE):
                    result['warnings'].append(f"{script.name} contains TODO comments")
                if re.search(r'\bstub\b', content, re.IGNORECASE):
                    result['warnings'].append(f"{script.name} contains stub comments")
                if re.search(r'\bmock\b.*\bimplementation\b', content, re.IGNORECASE):
                    result['warnings'].append(f"{script.name} may contain mock implementation")

                # Check for --help support (basic heuristic)
                if '--help' not in content and 'argparse' not in content:
                    result['warnings'].append(f"{script.name} may not support --help")

                # Check for --json support (basic heuristic)
                if '--json' not in content:
                    result['warnings'].append(f"{script.name} may not support --json")

            except Exception as e:
                result['errors'].append(f"Error checking {script.name} content: {e}")

        return result

    def _check_examples(self, resources_dir: Path) -> Dict:
        """Check examples directory."""
        result = {'warnings': [], 'count': 0}

        examples_dir = resources_dir / "examples"

        if not examples_dir.exists():
            result['warnings'].append("examples/ directory not found")
            return result

        # Count example files (excluding READMEs and hidden files)
        examples = [f for f in examples_dir.rglob("*")
                   if f.is_file()
                   and not f.name.startswith('.')
                   and f.name.lower() != 'readme.md']
        result['count'] = len(examples)

        if len(examples) < 6:
            result['warnings'].append(f"Only {len(examples)} examples found (expected 6-10)")

        return result

    def _check_documentation_quality(self, resources_dir: Path) -> Dict:
        """Check documentation completeness and quality."""
        result = {'warnings': [], 'findings': [], 'stats': {}}

        ref_path = resources_dir / "REFERENCE.md"
        if not ref_path.exists():
            return result

        try:
            content = ref_path.read_text()

            # Check for table of contents
            has_toc = bool(re.search(r'##\s*Table\s+of\s+Contents', content, re.IGNORECASE))
            result['stats']['has_toc'] = has_toc
            if not has_toc:
                result['warnings'].append("REFERENCE.md missing Table of Contents")
                result['findings'].append({
                    'type': 'documentation',
                    'severity': 'medium',
                    'issue': 'Missing Table of Contents in REFERENCE.md'
                })

            # Check for anti-patterns section
            has_antipatterns = bool(re.search(r'##\s*Anti[- ]?[Pp]atterns', content, re.IGNORECASE))
            result['stats']['has_antipatterns'] = has_antipatterns
            if not has_antipatterns:
                result['warnings'].append("REFERENCE.md missing Anti-Patterns section")
                result['findings'].append({
                    'type': 'documentation',
                    'severity': 'medium',
                    'issue': 'Missing Anti-Patterns section in REFERENCE.md'
                })

            # Check for references section
            has_references = bool(re.search(r'##\s*References', content, re.IGNORECASE))
            result['stats']['has_references'] = has_references
            if not has_references:
                result['warnings'].append("REFERENCE.md missing References section")
                result['findings'].append({
                    'type': 'documentation',
                    'severity': 'low',
                    'issue': 'Missing References section in REFERENCE.md'
                })

        except Exception as e:
            result['warnings'].append(f"Error checking documentation quality: {e}")

        return result

    def _check_script_quality(self, resources_dir: Path) -> Dict:
        """Check script quality: type hints, error handling, logging, etc."""
        result = {'warnings': [], 'findings': [], 'stats': {
            'scripts_with_type_hints': 0,
            'scripts_with_error_handling': 0,
            'scripts_with_logging': 0,
            'scripts_with_dry_run': 0,
            'scripts_with_input_sanitization': 0
        }}

        scripts_dir = resources_dir / "scripts"
        if not scripts_dir.exists():
            return result

        scripts = list(scripts_dir.glob("*.py"))

        for script in scripts:
            try:
                content = script.read_text()

                # Check for type hints using AST
                has_type_hints = self._has_type_hints(script)
                if has_type_hints:
                    result['stats']['scripts_with_type_hints'] += 1
                else:
                    result['warnings'].append(f"{script.name} lacks type hints")
                    result['findings'].append({
                        'type': 'quality',
                        'severity': 'low',
                        'file': script.name,
                        'issue': 'Missing type hints'
                    })

                # Check for error handling
                has_error_handling = bool(re.search(r'\btry\s*:', content))
                if has_error_handling:
                    result['stats']['scripts_with_error_handling'] += 1
                else:
                    result['warnings'].append(f"{script.name} lacks error handling (try/except)")
                    result['findings'].append({
                        'type': 'quality',
                        'severity': 'medium',
                        'file': script.name,
                        'issue': 'Missing error handling'
                    })

                # Check for structured logging
                has_logging = bool(re.search(r'import\s+logging|from\s+logging', content))
                if has_logging:
                    result['stats']['scripts_with_logging'] += 1
                else:
                    result['warnings'].append(f"{script.name} lacks structured logging")
                    result['findings'].append({
                        'type': 'quality',
                        'severity': 'low',
                        'file': script.name,
                        'issue': 'Missing structured logging'
                    })

                # Check for --dry-run flag (for destructive operations)
                is_destructive = bool(re.search(r'\b(delete|remove|drop|truncate|rm\s)', content, re.IGNORECASE))
                has_dry_run = bool(re.search(r'--dry-?run', content))

                if is_destructive and has_dry_run:
                    result['stats']['scripts_with_dry_run'] += 1
                elif is_destructive and not has_dry_run:
                    result['warnings'].append(f"{script.name} has destructive operations but no --dry-run flag")
                    result['findings'].append({
                        'type': 'quality',
                        'severity': 'high',
                        'file': script.name,
                        'issue': 'Destructive operations without --dry-run flag'
                    })

                # Check for input sanitization patterns
                has_input = bool(re.search(r'input\s*\(|sys\.argv|argparse', content))
                has_sanitization = bool(re.search(
                    r'(validate|sanitize|strip|clean|escape|quote|shlex\.quote)', content
                ))

                if has_input and has_sanitization:
                    result['stats']['scripts_with_input_sanitization'] += 1
                elif has_input and not has_sanitization:
                    result['warnings'].append(f"{script.name} accepts input but lacks sanitization")
                    result['findings'].append({
                        'type': 'quality',
                        'severity': 'medium',
                        'file': script.name,
                        'issue': 'Input accepted without visible sanitization'
                    })

            except Exception as e:
                result['warnings'].append(f"Error checking {script.name}: {e}")

        return result

    def _has_type_hints(self, script_path: Path) -> bool:
        """Check if a Python script has type hints using AST parsing."""
        try:
            with open(script_path, 'r') as f:
                tree = ast.parse(f.read())

            # Check for function definitions with type hints
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check return annotation or any argument annotations
                    if node.returns is not None:
                        return True
                    for arg in node.args.args:
                        if arg.annotation is not None:
                            return True

            return False
        except:
            return False

    def _check_security(self, resources_dir: Path) -> Dict:
        """Perform security checks on scripts and examples."""
        result = {
            'critical': [],
            'warnings': [],
            'findings': [],
            'stats': {
                'hardcoded_secrets': 0,
                'unsafe_subprocess': 0,
                'insecure_http': 0
            }
        }

        # Check scripts
        scripts_dir = resources_dir / "scripts"
        if scripts_dir.exists():
            for script in scripts_dir.glob("*.py"):
                self._scan_file_security(script, result)

        # Check examples
        examples_dir = resources_dir / "examples"
        if examples_dir.exists():
            for example in examples_dir.rglob("*"):
                if example.is_file() and example.suffix in {'.py', '.sh', '.js', '.ts'}:
                    self._scan_file_security(example, result)

        return result

    def _scan_file_security(self, file_path: Path, result: Dict):
        """Scan a single file for security issues."""
        try:
            content = file_path.read_text()
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                # Check for hardcoded secrets
                for pattern, issue in self.secrets_patterns.items():
                    if re.search(pattern, line):
                        if not self._is_test_file(file_path):
                            result['critical'].append(
                                f"{file_path.name}:{line_num} - {issue}"
                            )
                            result['findings'].append({
                                'type': 'security',
                                'severity': 'critical',
                                'file': file_path.name,
                                'line': line_num,
                                'issue': issue
                            })
                            result['stats']['hardcoded_secrets'] += 1

                # Check for unsafe subprocess usage
                for pattern, issue in self.unsafe_subprocess_patterns.items():
                    if re.search(pattern, line):
                        result['warnings'].append(f"{file_path.name}:{line_num} - {issue}")
                        result['findings'].append({
                            'type': 'security',
                            'severity': 'high',
                            'file': file_path.name,
                            'line': line_num,
                            'issue': issue
                        })
                        result['stats']['unsafe_subprocess'] += 1

                # Check for insecure HTTP
                for pattern, issue in self.http_patterns.items():
                    if re.search(pattern, line):
                        result['warnings'].append(f"{file_path.name}:{line_num} - {issue}")
                        result['findings'].append({
                            'type': 'security',
                            'severity': 'medium',
                            'file': file_path.name,
                            'line': line_num,
                            'issue': issue
                        })
                        result['stats']['insecure_http'] += 1

        except Exception as e:
            result['warnings'].append(f"Error scanning {file_path.name}: {e}")

    def _is_test_file(self, file_path: Path) -> bool:
        """Check if a file is a test/example file."""
        path_str = str(file_path).lower()
        return any(x in path_str for x in ['test', 'example', 'demo', 'fixture', 'mock'])

    def _check_example_quality(self, resources_dir: Path) -> Dict:
        """Check example quality: READMEs, dependencies, Docker security, etc."""
        result = {
            'warnings': [],
            'findings': [],
            'stats': {
                'examples_with_readme': 0,
                'examples_with_dependencies': 0,
                'docker_examples': 0,
                'docker_non_root': 0,
                'examples_with_health_checks': 0,
                'examples_with_error_handling': 0
            }
        }

        examples_dir = resources_dir / "examples"
        if not examples_dir.exists():
            return result

        # Check for example subdirectories with READMEs
        example_dirs = [d for d in examples_dir.iterdir() if d.is_dir()]
        for ex_dir in example_dirs:
            has_readme = (ex_dir / "README.md").exists()
            if has_readme:
                result['stats']['examples_with_readme'] += 1
            else:
                result['warnings'].append(f"Example {ex_dir.name} lacks README.md")
                result['findings'].append({
                    'type': 'example_quality',
                    'severity': 'medium',
                    'example': ex_dir.name,
                    'issue': 'Missing README.md'
                })

            # Check for dependency files
            has_deps = any([
                (ex_dir / "requirements.txt").exists(),
                (ex_dir / "package.json").exists(),
                (ex_dir / "go.mod").exists(),
                (ex_dir / "Cargo.toml").exists()
            ])
            if has_deps:
                result['stats']['examples_with_dependencies'] += 1

        # Check Docker files
        docker_files = list(examples_dir.rglob("Dockerfile*"))
        result['stats']['docker_examples'] = len(docker_files)

        for dockerfile in docker_files:
            try:
                content = dockerfile.read_text()

                # Check for non-root user
                has_user = bool(re.search(r'^USER\s+(?!root)', content, re.MULTILINE))
                if has_user:
                    result['stats']['docker_non_root'] += 1
                else:
                    result['warnings'].append(f"{dockerfile.name} doesn't use non-root user")
                    result['findings'].append({
                        'type': 'example_quality',
                        'severity': 'high',
                        'file': dockerfile.name,
                        'issue': 'Docker container runs as root'
                    })

                # Check for HEALTHCHECK
                has_healthcheck = bool(re.search(r'^HEALTHCHECK', content, re.MULTILINE))
                if has_healthcheck:
                    result['stats']['examples_with_health_checks'] += 1

            except Exception as e:
                result['warnings'].append(f"Error checking {dockerfile.name}: {e}")

        # Check Python examples for error handling
        py_examples = list(examples_dir.rglob("*.py"))
        for py_file in py_examples:
            try:
                content = py_file.read_text()
                has_error_handling = bool(re.search(r'\btry\s*:', content))
                if has_error_handling:
                    result['stats']['examples_with_error_handling'] += 1
            except:
                pass

        return result

    def _check_production_readiness(self, resources_dir: Path) -> Dict:
        """Check production readiness: rate limiting, timeouts, retry logic, etc."""
        result = {
            'warnings': [],
            'findings': [],
            'stats': {
                'scripts_with_rate_limiting': 0,
                'scripts_with_timeouts': 0,
                'scripts_with_retry': 0,
                'scripts_with_graceful_shutdown': 0,
                'scripts_with_context_managers': 0
            }
        }

        scripts_dir = resources_dir / "scripts"
        if not scripts_dir.exists():
            return result

        scripts = list(scripts_dir.glob("*.py"))

        for script in scripts:
            try:
                content = script.read_text()

                # Check for rate limiting
                has_rate_limit = bool(re.search(
                    r'(sleep|time\.sleep|rate.*limit|throttle|backoff)', content, re.IGNORECASE
                ))
                if has_rate_limit:
                    result['stats']['scripts_with_rate_limiting'] += 1

                # Check for HTTP timeouts
                has_http = bool(re.search(r'(requests|urllib|aiohttp|httpx)', content))
                has_timeout = bool(re.search(r'timeout\s*=', content))

                if has_http and has_timeout:
                    result['stats']['scripts_with_timeouts'] += 1
                elif has_http and not has_timeout:
                    result['warnings'].append(f"{script.name} makes HTTP requests without timeouts")
                    result['findings'].append({
                        'type': 'production',
                        'severity': 'medium',
                        'file': script.name,
                        'issue': 'HTTP requests without timeout configuration'
                    })

                # Check for retry logic
                has_retry = bool(re.search(
                    r'(retry|tenacity|backoff|retrying|@retry)', content, re.IGNORECASE
                ))
                if has_retry:
                    result['stats']['scripts_with_retry'] += 1

                # Check for graceful shutdown
                has_shutdown = bool(re.search(
                    r'(signal\.signal|atexit|KeyboardInterrupt|SIGTERM|SIGINT)', content
                ))
                if has_shutdown:
                    result['stats']['scripts_with_graceful_shutdown'] += 1

                # Check for context managers
                has_context = bool(re.search(r'\bwith\s+', content))
                if has_context:
                    result['stats']['scripts_with_context_managers'] += 1
                else:
                    # Check if file operations exist without context managers
                    has_open = bool(re.search(r'\bopen\s*\(', content))
                    if has_open:
                        result['warnings'].append(
                            f"{script.name} uses open() without context managers"
                        )
                        result['findings'].append({
                            'type': 'production',
                            'severity': 'low',
                            'file': script.name,
                            'issue': 'File operations without context managers'
                        })

            except Exception as e:
                result['warnings'].append(f"Error checking {script.name}: {e}")

        return result

    def print_results(self, verbose: bool = False):
        """Print validation results in human-readable format with enhanced findings."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == 'pass')
        warned = sum(1 for r in self.results if r.status == 'warn')
        failed = sum(1 for r in self.results if r.status == 'fail')

        # Count enhanced findings
        total_security = sum(len(r.security_findings) for r in self.results)
        total_quality = sum(len(r.quality_findings) for r in self.results)
        total_production = sum(len(r.production_findings) for r in self.results)

        print(f"\n{'='*80}")
        print(f"Resource Validation Results")
        if self.check_security:
            print(f"Security Checks: ENABLED")
        if self.check_production:
            print(f"Production Checks: ENABLED")
        if self.strict_mode:
            print(f"Mode: STRICT")
        print(f"{'='*80}\n")

        print(f"Total skills validated: {total}")
        print(f"  ✓ Passed: {passed}")
        print(f"  ⚠ Warnings: {warned}")
        print(f"  ✗ Failed: {failed}")
        print()

        if self.check_security or self.check_production or self.strict_mode:
            print(f"Enhanced Findings:")
            if self.check_security or self.strict_mode:
                print(f"  Security findings: {total_security}")
            if self.check_production or self.strict_mode:
                print(f"  Quality findings: {total_quality}")
                print(f"  Production findings: {total_production}")
            print()

        # Group by status
        for status, symbol in [('fail', '✗'), ('warn', '⚠'), ('pass', '✓')]:
            results = [r for r in self.results if r.status == status]
            if not results:
                continue

            print(f"\n{symbol} {status.upper()} ({len(results)}):")
            print("-" * 80)

            for result in results:
                print(f"\n{result.skill_name} ({result.skill_path})")
                print(f"  Stats: {result.stats.get('reference_lines', 0)} lines REFERENCE.md, "
                      f"{result.stats.get('scripts_count', 0)} scripts, "
                      f"{result.stats.get('examples_count', 0)} examples")

                # Enhanced stats
                if self.check_production or self.strict_mode:
                    if 'scripts_with_type_hints' in result.stats:
                        print(f"  Quality: {result.stats['scripts_with_type_hints']} with type hints, "
                              f"{result.stats['scripts_with_error_handling']} with error handling, "
                              f"{result.stats['scripts_with_logging']} with logging")

                if result.issues:
                    print(f"  Issues:")
                    for issue in result.issues:
                        print(f"    ✗ {issue}")

                if result.warnings and (verbose or status != 'pass'):
                    print(f"  Warnings:")
                    for warning in result.warnings[:10]:  # Limit to first 10
                        print(f"    ⚠ {warning}")
                    if len(result.warnings) > 10:
                        print(f"    ... and {len(result.warnings) - 10} more warnings")

                # Show critical security findings
                if result.security_findings and (verbose or status == 'fail'):
                    critical = [f for f in result.security_findings if f.get('severity') == 'critical']
                    if critical:
                        print(f"  Critical Security Issues:")
                        for finding in critical[:5]:
                            print(f"    🔴 {finding.get('file', 'N/A')}: {finding.get('issue', 'N/A')}")

                # Show high severity quality findings
                if result.quality_findings and verbose:
                    high = [f for f in result.quality_findings if f.get('severity') == 'high']
                    if high:
                        print(f"  High Priority Quality Issues:")
                        for finding in high[:3]:
                            print(f"    ⚡ {finding.get('file', 'N/A')}: {finding.get('issue', 'N/A')}")

        print(f"\n{'='*80}\n")

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        return {
            'total': len(self.results),
            'passed': sum(1 for r in self.results if r.status == 'pass'),
            'warned': sum(1 for r in self.results if r.status == 'warn'),
            'failed': sum(1 for r in self.results if r.status == 'fail'),
            'skills': [asdict(r) for r in self.results]
        }

def main():
    parser = argparse.ArgumentParser(
        description="Validate Level 3 Resources for skills with production-ready checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic validation
  ./validate_resources.py

  # With security checks
  ./validate_resources.py --check-security

  # With all production checks
  ./validate_resources.py --check-production-ready

  # Strict mode (all checks + fail on warnings)
  ./validate_resources.py --strict-mode

  # Specific skill with verbose output
  ./validate_resources.py --skill grpc -v

  # JSON output for CI/CD
  ./validate_resources.py --check-security --json
        """
    )

    parser.add_argument('--skill', help="Validate specific skill (name or path)")
    parser.add_argument('--json', action='store_true', help="Output as JSON")
    parser.add_argument('--strict', action='store_true', help="Fail on warnings")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose output")
    parser.add_argument('--skills-dir', type=Path, default=Path('skills'),
                       help="Path to skills directory (default: skills)")

    # Enhanced check options
    parser.add_argument('--check-security', action='store_true',
                       help="Enable security checks (secrets, unsafe code, HTTP)")
    parser.add_argument('--check-production-ready', action='store_true',
                       help="Enable production readiness checks (timeouts, retries, cleanup)")
    parser.add_argument('--strict-mode', action='store_true',
                       help="Enable all checks and fail on any warnings")

    args = parser.parse_args()

    if not args.skills_dir.exists():
        print(f"Error: Skills directory not found: {args.skills_dir}", file=sys.stderr)
        sys.exit(1)

    validator = ResourceValidator(
        args.skills_dir,
        strict=args.strict,
        check_security=args.check_security,
        check_production=args.check_production_ready,
        strict_mode=args.strict_mode
    )

    if args.skill:
        # Validate specific skill
        skill_path = args.skills_dir / args.skill
        if not skill_path.exists():
            # Try finding it
            candidates = list(args.skills_dir.rglob(f"*{args.skill}*"))
            if not candidates:
                print(f"Error: Skill not found: {args.skill}", file=sys.stderr)
                sys.exit(1)
            skill_path = candidates[0]

        result = validator.validate_skill(skill_path)
        validator.results = [result]
    else:
        # Validate all skills
        validator.validate_all()

    if args.json:
        print(json.dumps(validator.get_summary(), indent=2))
    else:
        validator.print_results(verbose=args.verbose)

    # Exit code
    summary = validator.get_summary()
    if summary['failed'] > 0:
        sys.exit(1)
    elif summary['warned'] > 0 and (args.strict or args.strict_mode):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
