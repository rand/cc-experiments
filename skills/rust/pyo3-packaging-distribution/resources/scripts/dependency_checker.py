#!/usr/bin/env python3
"""
PyO3 Dependency Checker - Validate dependencies, security, and license compliance

This script provides comprehensive dependency analysis for PyO3 projects:
- Validates Rust dependencies (Cargo.toml)
- Validates Python dependencies (pyproject.toml)
- Checks system requirements (BLAS, LAPACK, etc.)
- Verifies version compatibility
- Performs security audits with cargo-audit
- Validates license compliance
"""
import argparse
import json
import logging
import sys
import subprocess
import shutil
import re
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import tempfile

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity levels for issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DependencyType(Enum):
    """Types of dependencies."""
    RUST = "rust"
    PYTHON = "python"
    SYSTEM = "system"


@dataclass
class Issue:
    """Represents a dependency issue."""
    severity: Severity
    category: str
    message: str
    dependency: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'severity': self.severity.value,
            'category': self.category,
            'message': self.message,
            'dependency': self.dependency,
            'details': self.details or {}
        }


@dataclass
class Dependency:
    """Represents a single dependency."""
    name: str
    version: str
    dep_type: DependencyType
    optional: bool = False
    features: List[str] = field(default_factory=list)
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'version': self.version,
            'type': self.dep_type.value,
            'optional': self.optional,
            'features': self.features,
            'source': self.source
        }


@dataclass
class License:
    """Represents a software license."""
    name: str
    spdx_id: Optional[str] = None
    is_osi_approved: bool = False
    is_permissive: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'spdx_id': self.spdx_id,
            'is_osi_approved': self.is_osi_approved,
            'is_permissive': self.is_permissive
        }


@dataclass
class SecurityVulnerability:
    """Represents a security vulnerability."""
    id: str
    package: str
    version: str
    severity: Severity
    title: str
    description: str
    url: Optional[str] = None
    patched_versions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'package': self.package,
            'version': self.version,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'url': self.url,
            'patched_versions': self.patched_versions
        }


@dataclass
class CheckResult:
    """Result of a dependency check."""
    success: bool
    dependencies: List[Dependency]
    issues: List[Issue]
    vulnerabilities: List[SecurityVulnerability] = field(default_factory=list)
    licenses: Dict[str, License] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'dependencies': [d.to_dict() for d in self.dependencies],
            'issues': [i.to_dict() for i in self.issues],
            'vulnerabilities': [v.to_dict() for v in self.vulnerabilities],
            'licenses': {k: v.to_dict() for k, v in self.licenses.items()}
        }


class LicenseDatabase:
    """Database of common software licenses with metadata."""

    # OSI-approved permissive licenses
    PERMISSIVE_LICENSES = {
        'MIT', 'Apache-2.0', 'BSD-3-Clause', 'BSD-2-Clause', 'ISC',
        'Unlicense', '0BSD', 'CC0-1.0', 'BSL-1.0', 'Zlib', 'Python-2.0'
    }

    # OSI-approved copyleft licenses
    COPYLEFT_LICENSES = {
        'GPL-2.0', 'GPL-3.0', 'LGPL-2.1', 'LGPL-3.0', 'AGPL-3.0',
        'MPL-2.0', 'EPL-2.0', 'EUPL-1.2'
    }

    # Potentially problematic licenses
    RESTRICTED_LICENSES = {
        'SSPL-1.0', 'Commons-Clause', 'BUSL-1.1', 'Proprietary'
    }

    @classmethod
    def get_license_info(cls, license_id: str) -> License:
        """Get license information."""
        normalized = cls.normalize_license_id(license_id)

        if normalized in cls.PERMISSIVE_LICENSES:
            return License(
                name=license_id,
                spdx_id=normalized,
                is_osi_approved=True,
                is_permissive=True
            )
        elif normalized in cls.COPYLEFT_LICENSES:
            return License(
                name=license_id,
                spdx_id=normalized,
                is_osi_approved=True,
                is_permissive=False
            )
        elif normalized in cls.RESTRICTED_LICENSES:
            return License(
                name=license_id,
                spdx_id=normalized,
                is_osi_approved=False,
                is_permissive=False
            )
        else:
            return License(
                name=license_id,
                spdx_id=normalized,
                is_osi_approved=False,
                is_permissive=False
            )

    @staticmethod
    def normalize_license_id(license_id: str) -> str:
        """Normalize license identifier."""
        # Handle common variations
        replacements = {
            'MIT/Apache-2.0': 'MIT OR Apache-2.0',
            'Apache-2.0/MIT': 'Apache-2.0 OR MIT',
            'Apache 2.0': 'Apache-2.0',
            'BSD 3-Clause': 'BSD-3-Clause',
            'BSD 2-Clause': 'BSD-2-Clause',
        }
        return replacements.get(license_id, license_id)


class CargoTomlParser:
    """Parse Cargo.toml files."""

    def __init__(self, cargo_toml_path: Path):
        self.path = cargo_toml_path
        self.content: Optional[str] = None
        self.parsed: Dict[str, Any] = {}

    def parse(self) -> bool:
        """Parse Cargo.toml file."""
        try:
            self.content = self.path.read_text()
            # Use cargo metadata for accurate parsing
            result = subprocess.run(
                ['cargo', 'metadata', '--format-version=1', '--no-deps'],
                cwd=self.path.parent,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0:
                self.parsed = json.loads(result.stdout)
                return True
            else:
                logger.warning(f"Failed to parse Cargo.toml: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error parsing Cargo.toml: {e}")
            return False

    def get_dependencies(self) -> List[Dependency]:
        """Extract dependencies from Cargo.toml."""
        deps = []

        if not self.parsed:
            return deps

        packages = self.parsed.get('packages', [])
        if not packages:
            return deps

        package = packages[0]  # First package in workspace

        # Regular dependencies
        for dep_name, dep_info in package.get('dependencies', []):
            if isinstance(dep_info, dict):
                dep = Dependency(
                    name=dep_name,
                    version=dep_info.get('req', '*'),
                    dep_type=DependencyType.RUST,
                    optional=dep_info.get('optional', False),
                    features=dep_info.get('features', []),
                    source=dep_info.get('source')
                )
                deps.append(dep)

        return deps

    def check_pyo3_features(self) -> List[Issue]:
        """Check PyO3 feature configuration."""
        issues = []

        if not self.content:
            return issues

        # Check for extension-module feature
        pyo3_pattern = r'pyo3\s*=\s*{[^}]*}'
        matches = re.findall(pyo3_pattern, self.content)

        for match in matches:
            if 'extension-module' not in match:
                issues.append(Issue(
                    severity=Severity.CRITICAL,
                    category='configuration',
                    message='PyO3 dependency missing extension-module feature',
                    dependency='pyo3',
                    details={
                        'fix': 'Add features = ["extension-module"] to pyo3 dependency',
                        'example': 'pyo3 = { version = "0.20", features = ["extension-module"] }'
                    }
                ))

        return issues

    def check_crate_type(self) -> List[Issue]:
        """Check crate-type configuration."""
        issues = []

        if not self.content:
            return issues

        # Check for cdylib crate type
        if 'crate-type = ["cdylib"]' not in self.content:
            issues.append(Issue(
                severity=Severity.HIGH,
                category='configuration',
                message='Missing cdylib crate type for Python extension',
                details={
                    'fix': 'Add crate-type = ["cdylib"] to [lib] section',
                    'example': '[lib]\ncrate-type = ["cdylib"]'
                }
            ))

        return issues


class PyprojectTomlParser:
    """Parse pyproject.toml files."""

    def __init__(self, pyproject_toml_path: Path):
        self.path = pyproject_toml_path
        self.content: Optional[str] = None
        self.parsed: Dict[str, Any] = {}

    def parse(self) -> bool:
        """Parse pyproject.toml file."""
        try:
            import tomli
        except ImportError:
            try:
                import tomllib as tomli
            except ImportError:
                logger.warning("tomli not available, using regex parsing")
                self.content = self.path.read_text()
                return True

        try:
            with open(self.path, 'rb') as f:
                self.parsed = tomli.load(f)
            self.content = self.path.read_text()
            return True
        except Exception as e:
            logger.error(f"Error parsing pyproject.toml: {e}")
            return False

    def get_dependencies(self) -> List[Dependency]:
        """Extract dependencies from pyproject.toml."""
        deps = []

        if not self.parsed:
            return deps

        project = self.parsed.get('project', {})

        # Main dependencies
        for dep_spec in project.get('dependencies', []):
            name, version = self._parse_dep_spec(dep_spec)
            deps.append(Dependency(
                name=name,
                version=version,
                dep_type=DependencyType.PYTHON,
                optional=False
            ))

        # Optional dependencies
        for group, dep_list in project.get('optional-dependencies', {}).items():
            for dep_spec in dep_list:
                name, version = self._parse_dep_spec(dep_spec)
                deps.append(Dependency(
                    name=name,
                    version=version,
                    dep_type=DependencyType.PYTHON,
                    optional=True,
                    features=[group]
                ))

        return deps

    @staticmethod
    def _parse_dep_spec(spec: str) -> Tuple[str, str]:
        """Parse dependency specification string."""
        # Handle: "package>=1.0,<2.0"
        match = re.match(r'^([a-zA-Z0-9\-_]+)(.*)$', spec)
        if match:
            name = match.group(1)
            version = match.group(2).strip()
            return name, version if version else '*'
        return spec, '*'

    def check_maturin_config(self) -> List[Issue]:
        """Check maturin configuration."""
        issues = []

        if not self.parsed:
            return issues

        build_system = self.parsed.get('build-system', {})

        # Check maturin in requires
        requires = build_system.get('requires', [])
        has_maturin = any('maturin' in req for req in requires)

        if not has_maturin:
            issues.append(Issue(
                severity=Severity.HIGH,
                category='configuration',
                message='maturin not specified in build-system requires',
                details={
                    'fix': 'Add maturin to build-system.requires',
                    'example': 'requires = ["maturin>=1.4,<2.0"]'
                }
            ))

        # Check build-backend
        backend = build_system.get('build-backend')
        if backend != 'maturin':
            issues.append(Issue(
                severity=Severity.HIGH,
                category='configuration',
                message=f'build-backend should be "maturin", got "{backend}"',
                details={
                    'fix': 'Set build-backend = "maturin"'
                }
            ))

        return issues

    def check_python_version(self) -> List[Issue]:
        """Check Python version requirements."""
        issues = []

        if not self.parsed:
            return issues

        project = self.parsed.get('project', {})
        requires_python = project.get('requires-python')

        if not requires_python:
            issues.append(Issue(
                severity=Severity.MEDIUM,
                category='configuration',
                message='Missing requires-python specification',
                details={
                    'fix': 'Add requires-python field',
                    'example': 'requires-python = ">=3.8"'
                }
            ))

        return issues


class SystemRequirementsChecker:
    """Check system requirements (BLAS, LAPACK, etc.)."""

    def __init__(self):
        self.pkgconfig_path = shutil.which('pkg-config')

    def check_blas(self) -> Optional[Issue]:
        """Check for BLAS library."""
        if not self.pkgconfig_path:
            return None

        try:
            result = subprocess.run(
                ['pkg-config', '--exists', 'blas'],
                capture_output=True,
                check=False
            )

            if result.returncode != 0:
                return Issue(
                    severity=Severity.INFO,
                    category='system',
                    message='BLAS library not found via pkg-config',
                    details={
                        'note': 'Required for numpy/scipy extensions',
                        'install': 'apt-get install libblas-dev (Debian/Ubuntu)'
                    }
                )

        except Exception as e:
            logger.debug(f"Error checking BLAS: {e}")

        return None

    def check_lapack(self) -> Optional[Issue]:
        """Check for LAPACK library."""
        if not self.pkgconfig_path:
            return None

        try:
            result = subprocess.run(
                ['pkg-config', '--exists', 'lapack'],
                capture_output=True,
                check=False
            )

            if result.returncode != 0:
                return Issue(
                    severity=Severity.INFO,
                    category='system',
                    message='LAPACK library not found via pkg-config',
                    details={
                        'note': 'Required for scipy extensions',
                        'install': 'apt-get install liblapack-dev (Debian/Ubuntu)'
                    }
                )

        except Exception as e:
            logger.debug(f"Error checking LAPACK: {e}")

        return None

    def check_openmp(self) -> Optional[Issue]:
        """Check for OpenMP support."""
        if not self.pkgconfig_path:
            return None

        try:
            result = subprocess.run(
                ['pkg-config', '--exists', 'openmp'],
                capture_output=True,
                check=False
            )

            if result.returncode != 0:
                return Issue(
                    severity=Severity.INFO,
                    category='system',
                    message='OpenMP not found via pkg-config',
                    details={
                        'note': 'Required for parallel extensions',
                        'install': 'apt-get install libomp-dev (Debian/Ubuntu)'
                    }
                )

        except Exception as e:
            logger.debug(f"Error checking OpenMP: {e}")

        return None

    def check_all(self) -> List[Issue]:
        """Check all system requirements."""
        issues = []

        checks = [
            self.check_blas(),
            self.check_lapack(),
            self.check_openmp()
        ]

        for issue in checks:
            if issue:
                issues.append(issue)

        return issues


class SecurityAuditor:
    """Perform security audits using cargo-audit."""

    def __init__(self):
        self.cargo_audit_path = shutil.which('cargo-audit')

    def is_available(self) -> bool:
        """Check if cargo-audit is available."""
        return self.cargo_audit_path is not None

    def install_instructions(self) -> str:
        """Get installation instructions."""
        return "cargo install cargo-audit"

    def audit(self, project_dir: Path) -> List[SecurityVulnerability]:
        """Run cargo-audit on project."""
        if not self.is_available():
            logger.warning("cargo-audit not available, skipping security audit")
            return []

        vulnerabilities = []

        try:
            result = subprocess.run(
                ['cargo', 'audit', '--json'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)

                    for vuln in data.get('vulnerabilities', {}).get('list', []):
                        advisory = vuln.get('advisory', {})
                        package_info = vuln.get('package', {})

                        severity_str = advisory.get('severity', 'medium').lower()
                        try:
                            severity = Severity(severity_str)
                        except ValueError:
                            severity = Severity.MEDIUM

                        vulnerabilities.append(SecurityVulnerability(
                            id=advisory.get('id', 'UNKNOWN'),
                            package=package_info.get('name', 'unknown'),
                            version=package_info.get('version', 'unknown'),
                            severity=severity,
                            title=advisory.get('title', 'Unknown vulnerability'),
                            description=advisory.get('description', ''),
                            url=advisory.get('url'),
                            patched_versions=advisory.get('patched_versions', [])
                        ))

                except json.JSONDecodeError:
                    logger.warning("Failed to parse cargo-audit JSON output")

        except Exception as e:
            logger.error(f"Error running cargo-audit: {e}")

        return vulnerabilities


class LicenseChecker:
    """Check license compliance for dependencies."""

    def __init__(self):
        self.cargo_license_path = shutil.which('cargo-license')

    def is_available(self) -> bool:
        """Check if cargo-license is available."""
        return self.cargo_license_path is not None

    def install_instructions(self) -> str:
        """Get installation instructions."""
        return "cargo install cargo-license"

    def check_rust_licenses(self, project_dir: Path) -> Tuple[Dict[str, License], List[Issue]]:
        """Check Rust dependency licenses."""
        licenses = {}
        issues = []

        if not self.is_available():
            logger.warning("cargo-license not available, skipping license check")
            return licenses, issues

        try:
            result = subprocess.run(
                ['cargo', 'license', '--json'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)

                    for entry in data:
                        name = entry.get('name', 'unknown')
                        license_id = entry.get('license', 'UNKNOWN')

                        license_info = LicenseDatabase.get_license_info(license_id)
                        licenses[name] = license_info

                        # Check for restricted licenses
                        normalized = LicenseDatabase.normalize_license_id(license_id)
                        if normalized in LicenseDatabase.RESTRICTED_LICENSES:
                            issues.append(Issue(
                                severity=Severity.HIGH,
                                category='license',
                                message=f'Dependency uses restricted license: {license_id}',
                                dependency=name,
                                details={
                                    'license': license_id,
                                    'note': 'This license may have usage restrictions'
                                }
                            ))

                except json.JSONDecodeError:
                    logger.warning("Failed to parse cargo-license JSON output")

        except Exception as e:
            logger.error(f"Error checking Rust licenses: {e}")

        return licenses, issues

    def check_python_licenses(self, dependencies: List[Dependency]) -> Tuple[Dict[str, License], List[Issue]]:
        """Check Python dependency licenses (basic check)."""
        licenses = {}
        issues = []

        # Note: Full implementation would query PyPI API or use pip-licenses
        # For production, integrate with pip-licenses or similar tool

        for dep in dependencies:
            if dep.dep_type == DependencyType.PYTHON:
                # Placeholder: would query PyPI metadata
                licenses[dep.name] = License(
                    name="UNKNOWN",
                    spdx_id=None,
                    is_osi_approved=False,
                    is_permissive=False
                )

        return licenses, issues


class DependencyChecker:
    """Main dependency checker orchestrator."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.cargo_toml_path = project_dir / 'Cargo.toml'
        self.pyproject_toml_path = project_dir / 'pyproject.toml'

        self.cargo_parser: Optional[CargoTomlParser] = None
        self.pyproject_parser: Optional[PyprojectTomlParser] = None
        self.system_checker = SystemRequirementsChecker()
        self.security_auditor = SecurityAuditor()
        self.license_checker = LicenseChecker()

    def check_tools(self) -> Dict[str, bool]:
        """Check availability of required tools."""
        return {
            'cargo': shutil.which('cargo') is not None,
            'rustc': shutil.which('rustc') is not None,
            'cargo-audit': self.security_auditor.is_available(),
            'cargo-license': self.license_checker.is_available(),
            'pkg-config': self.system_checker.pkgconfig_path is not None,
        }

    def validate_structure(self) -> List[Issue]:
        """Validate project structure."""
        issues = []

        if not self.cargo_toml_path.exists():
            issues.append(Issue(
                severity=Severity.CRITICAL,
                category='structure',
                message='Cargo.toml not found',
                details={'path': str(self.cargo_toml_path)}
            ))

        if not self.pyproject_toml_path.exists():
            issues.append(Issue(
                severity=Severity.CRITICAL,
                category='structure',
                message='pyproject.toml not found',
                details={'path': str(self.pyproject_toml_path)}
            ))

        src_dir = self.project_dir / 'src'
        if not src_dir.exists():
            issues.append(Issue(
                severity=Severity.HIGH,
                category='structure',
                message='src/ directory not found',
                details={'path': str(src_dir)}
            ))

        return issues

    def check_all(self, skip_audit: bool = False, skip_licenses: bool = False) -> CheckResult:
        """Perform all dependency checks."""
        dependencies = []
        issues = []
        vulnerabilities = []
        licenses = {}

        # Validate structure
        structure_issues = self.validate_structure()
        issues.extend(structure_issues)

        if any(issue.severity == Severity.CRITICAL for issue in structure_issues):
            return CheckResult(False, dependencies, issues, vulnerabilities, licenses)

        # Parse Cargo.toml
        if self.cargo_toml_path.exists():
            self.cargo_parser = CargoTomlParser(self.cargo_toml_path)
            if self.cargo_parser.parse():
                dependencies.extend(self.cargo_parser.get_dependencies())
                issues.extend(self.cargo_parser.check_pyo3_features())
                issues.extend(self.cargo_parser.check_crate_type())

        # Parse pyproject.toml
        if self.pyproject_toml_path.exists():
            self.pyproject_parser = PyprojectTomlParser(self.pyproject_toml_path)
            if self.pyproject_parser.parse():
                dependencies.extend(self.pyproject_parser.get_dependencies())
                issues.extend(self.pyproject_parser.check_maturin_config())
                issues.extend(self.pyproject_parser.check_python_version())

        # Check system requirements
        issues.extend(self.system_checker.check_all())

        # Security audit
        if not skip_audit:
            vulnerabilities = self.security_auditor.audit(self.project_dir)

        # License checking
        if not skip_licenses:
            rust_licenses, rust_issues = self.license_checker.check_rust_licenses(self.project_dir)
            licenses.update(rust_licenses)
            issues.extend(rust_issues)

        # Determine success
        critical_issues = [i for i in issues if i.severity in [Severity.CRITICAL, Severity.HIGH]]
        success = len(critical_issues) == 0 and len(vulnerabilities) == 0

        return CheckResult(success, dependencies, issues, vulnerabilities, licenses)


class ReportGenerator:
    """Generate reports from check results."""

    @staticmethod
    def generate_text(result: CheckResult) -> str:
        """Generate human-readable text report."""
        lines = ["=== Dependency Check Report ===\n"]

        # Summary
        status = "PASS" if result.success else "FAIL"
        lines.append(f"Status: {status}")
        lines.append(f"Dependencies: {len(result.dependencies)}")
        lines.append(f"Issues: {len(result.issues)}")
        lines.append(f"Vulnerabilities: {len(result.vulnerabilities)}")
        lines.append(f"Licenses: {len(result.licenses)}")
        lines.append("")

        # Dependencies
        if result.dependencies:
            lines.append("=== Dependencies ===")
            rust_deps = [d for d in result.dependencies if d.dep_type == DependencyType.RUST]
            python_deps = [d for d in result.dependencies if d.dep_type == DependencyType.PYTHON]

            if rust_deps:
                lines.append(f"\nRust Dependencies ({len(rust_deps)}):")
                for dep in rust_deps:
                    optional = " (optional)" if dep.optional else ""
                    lines.append(f"  - {dep.name} {dep.version}{optional}")

            if python_deps:
                lines.append(f"\nPython Dependencies ({len(python_deps)}):")
                for dep in python_deps:
                    optional = " (optional)" if dep.optional else ""
                    lines.append(f"  - {dep.name} {dep.version}{optional}")

            lines.append("")

        # Issues
        if result.issues:
            lines.append("=== Issues ===")
            by_severity = {}
            for issue in result.issues:
                by_severity.setdefault(issue.severity, []).append(issue)

            for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
                issues = by_severity.get(severity, [])
                if issues:
                    lines.append(f"\n{severity.value.upper()} ({len(issues)}):")
                    for issue in issues:
                        dep_info = f" [{issue.dependency}]" if issue.dependency else ""
                        lines.append(f"  - {issue.message}{dep_info}")
                        if issue.details:
                            for key, value in issue.details.items():
                                lines.append(f"    {key}: {value}")

            lines.append("")

        # Vulnerabilities
        if result.vulnerabilities:
            lines.append("=== Security Vulnerabilities ===")
            for vuln in result.vulnerabilities:
                lines.append(f"\n{vuln.id} - {vuln.title}")
                lines.append(f"  Package: {vuln.package} {vuln.version}")
                lines.append(f"  Severity: {vuln.severity.value.upper()}")
                if vuln.description:
                    lines.append(f"  Description: {vuln.description}")
                if vuln.url:
                    lines.append(f"  URL: {vuln.url}")
                if vuln.patched_versions:
                    lines.append(f"  Patched: {', '.join(vuln.patched_versions)}")

            lines.append("")

        # Licenses
        if result.licenses:
            lines.append("=== License Summary ===")

            permissive = [name for name, lic in result.licenses.items() if lic.is_permissive]
            copyleft = [name for name, lic in result.licenses.items() if not lic.is_permissive and lic.is_osi_approved]
            other = [name for name, lic in result.licenses.items() if not lic.is_osi_approved]

            if permissive:
                lines.append(f"\nPermissive Licenses ({len(permissive)}):")
                for name in permissive[:10]:
                    lic = result.licenses[name]
                    lines.append(f"  - {name}: {lic.name}")
                if len(permissive) > 10:
                    lines.append(f"  ... and {len(permissive) - 10} more")

            if copyleft:
                lines.append(f"\nCopyleft Licenses ({len(copyleft)}):")
                for name in copyleft[:10]:
                    lic = result.licenses[name]
                    lines.append(f"  - {name}: {lic.name}")
                if len(copyleft) > 10:
                    lines.append(f"  ... and {len(copyleft) - 10} more")

            if other:
                lines.append(f"\nOther Licenses ({len(other)}):")
                for name in other[:10]:
                    lic = result.licenses[name]
                    lines.append(f"  - {name}: {lic.name}")
                if len(other) > 10:
                    lines.append(f"  ... and {len(other) - 10} more")

        return "\n".join(lines)

    @staticmethod
    def generate_json(result: CheckResult) -> str:
        """Generate JSON report."""
        return json.dumps(result.to_dict(), indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='PyO3 Dependency Checker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check all dependencies
  %(prog)s check /path/to/project

  # Security audit only
  %(prog)s audit /path/to/project

  # License compliance check
  %(prog)s licenses /path/to/project

  # Validate configuration
  %(prog)s validate /path/to/project

  # JSON output
  %(prog)s check /path/to/project --json
        """
    )

    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Check command
    check_parser = subparsers.add_parser('check', help='Check all dependencies')
    check_parser.add_argument('project', type=Path, help='Project directory')
    check_parser.add_argument('--skip-audit', action='store_true', help='Skip security audit')
    check_parser.add_argument('--skip-licenses', action='store_true', help='Skip license check')

    # Audit command
    audit_parser = subparsers.add_parser('audit', help='Security audit only')
    audit_parser.add_argument('project', type=Path, help='Project directory')

    # Licenses command
    licenses_parser = subparsers.add_parser('licenses', help='License check only')
    licenses_parser.add_argument('project', type=Path, help='Project directory')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration only')
    validate_parser.add_argument('project', type=Path, help='Project directory')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.command == 'check':
            checker = DependencyChecker(args.project)
            result = checker.check_all(
                skip_audit=args.skip_audit,
                skip_licenses=args.skip_licenses
            )

            report_gen = ReportGenerator()
            if args.json:
                print(report_gen.generate_json(result))
            else:
                print(report_gen.generate_text(result))

            sys.exit(0 if result.success else 1)

        elif args.command == 'audit':
            checker = DependencyChecker(args.project)
            auditor = SecurityAuditor()

            if not auditor.is_available():
                logger.error("cargo-audit not available")
                logger.info(f"Install with: {auditor.install_instructions()}")
                sys.exit(1)

            vulnerabilities = auditor.audit(args.project)

            if args.json:
                data = {'vulnerabilities': [v.to_dict() for v in vulnerabilities]}
                print(json.dumps(data, indent=2))
            else:
                print(f"Found {len(vulnerabilities)} vulnerabilities\n")
                for vuln in vulnerabilities:
                    print(f"{vuln.id} - {vuln.title}")
                    print(f"  Package: {vuln.package} {vuln.version}")
                    print(f"  Severity: {vuln.severity.value.upper()}")
                    if vuln.url:
                        print(f"  URL: {vuln.url}")
                    print()

            sys.exit(1 if vulnerabilities else 0)

        elif args.command == 'licenses':
            checker = DependencyChecker(args.project)
            license_checker = LicenseChecker()

            if not license_checker.is_available():
                logger.error("cargo-license not available")
                logger.info(f"Install with: {license_checker.install_instructions()}")
                sys.exit(1)

            licenses, issues = license_checker.check_rust_licenses(args.project)

            if args.json:
                data = {
                    'licenses': {k: v.to_dict() for k, v in licenses.items()},
                    'issues': [i.to_dict() for i in issues]
                }
                print(json.dumps(data, indent=2))
            else:
                print(f"Found {len(licenses)} dependencies with licenses\n")

                by_license = {}
                for name, lic in licenses.items():
                    by_license.setdefault(lic.name, []).append(name)

                for license_name, deps in sorted(by_license.items()):
                    print(f"{license_name} ({len(deps)} deps):")
                    for dep in deps[:5]:
                        print(f"  - {dep}")
                    if len(deps) > 5:
                        print(f"  ... and {len(deps) - 5} more")
                    print()

                if issues:
                    print("Issues:")
                    for issue in issues:
                        print(f"  - {issue.message}")

            sys.exit(1 if issues else 0)

        elif args.command == 'validate':
            checker = DependencyChecker(args.project)

            # Structure validation
            issues = checker.validate_structure()

            # Config validation
            if checker.cargo_toml_path.exists():
                parser_cargo = CargoTomlParser(checker.cargo_toml_path)
                if parser_cargo.parse():
                    issues.extend(parser_cargo.check_pyo3_features())
                    issues.extend(parser_cargo.check_crate_type())

            if checker.pyproject_toml_path.exists():
                parser_py = PyprojectTomlParser(checker.pyproject_toml_path)
                if parser_py.parse():
                    issues.extend(parser_py.check_maturin_config())
                    issues.extend(parser_py.check_python_version())

            if args.json:
                data = {'issues': [i.to_dict() for i in issues]}
                print(json.dumps(data, indent=2))
            else:
                if not issues:
                    print("Configuration is valid")
                else:
                    print(f"Found {len(issues)} issues:\n")
                    for issue in issues:
                        print(f"[{issue.severity.value.upper()}] {issue.message}")
                        if issue.details:
                            for key, value in issue.details.items():
                                print(f"  {key}: {value}")
                        print()

            sys.exit(1 if issues else 0)

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
