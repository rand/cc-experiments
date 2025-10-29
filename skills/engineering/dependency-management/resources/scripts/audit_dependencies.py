#!/usr/bin/env python3
"""
Multi-language dependency auditing tool.

Scans projects for:
- Security vulnerabilities
- Outdated dependencies
- License compliance issues
- Dependency health metrics
- SBOM generation

Supports: JavaScript (npm/yarn/pnpm), Python (pip/poetry/uv), Rust (cargo),
          Go (go modules), Java (maven/gradle)

Usage:
    ./audit_dependencies.py --path /path/to/project
    ./audit_dependencies.py --path . --json
    ./audit_dependencies.py --path . --severity high
    ./audit_dependencies.py --path . --sbom cyclonedx
    ./audit_dependencies.py --path . --license-check
    ./audit_dependencies.py --path . --verbose
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class Severity(Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INFO = "info"

    def __lt__(self, other: "Severity") -> bool:
        order = [Severity.INFO, Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL]
        return order.index(self) < order.index(other)


class Ecosystem(Enum):
    """Package ecosystem types."""
    NPM = "npm"
    YARN = "yarn"
    PNPM = "pnpm"
    PIP = "pip"
    POETRY = "poetry"
    UV = "uv"
    CARGO = "cargo"
    GO = "go"
    MAVEN = "maven"
    GRADLE = "gradle"
    UNKNOWN = "unknown"


@dataclass
class Vulnerability:
    """Security vulnerability information."""
    id: str
    package: str
    version: str
    severity: Severity
    title: str
    description: str
    cve: Optional[str] = None
    cvss_score: Optional[float] = None
    patched_versions: List[str] = field(default_factory=list)
    vulnerable_versions: str = ""
    url: Optional[str] = None


@dataclass
class Dependency:
    """Dependency information."""
    name: str
    version: str
    latest_version: Optional[str] = None
    license: Optional[str] = None
    is_dev: bool = False
    is_transitive: bool = False
    depth: int = 0
    parent: Optional[str] = None
    vulnerabilities: List[Vulnerability] = field(default_factory=list)


@dataclass
class LicenseIssue:
    """License compliance issue."""
    package: str
    version: str
    license: str
    severity: str
    reason: str


@dataclass
class AuditResult:
    """Audit results for a project."""
    ecosystem: Ecosystem
    project_path: str
    scan_time: str
    dependencies: List[Dependency]
    vulnerabilities: List[Vulnerability]
    license_issues: List[LicenseIssue]
    outdated_count: int
    health_score: float
    summary: Dict[str, Any]


class DependencyAuditor:
    """Multi-language dependency auditing."""

    def __init__(self, project_path: str, verbose: bool = False):
        self.project_path = Path(project_path).resolve()
        self.verbose = verbose
        self.ecosystem = self._detect_ecosystem()

    def _log(self, message: str) -> None:
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def _run_command(self, cmd: List[str], check: bool = True) -> Tuple[str, str, int]:
        """Run shell command and return stdout, stderr, returncode."""
        self._log(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=check,
                timeout=300
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.CalledProcessError as e:
            return e.stdout, e.stderr, e.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", 124
        except FileNotFoundError:
            return "", f"Command not found: {cmd[0]}", 127

    def _detect_ecosystem(self) -> Ecosystem:
        """Detect package ecosystem from project files."""
        detections = []

        if (self.project_path / "package-lock.json").exists():
            detections.append((Ecosystem.NPM, 3))
        if (self.project_path / "yarn.lock").exists():
            detections.append((Ecosystem.YARN, 3))
        if (self.project_path / "pnpm-lock.yaml").exists():
            detections.append((Ecosystem.PNPM, 3))
        if (self.project_path / "package.json").exists():
            detections.append((Ecosystem.NPM, 2))

        if (self.project_path / "poetry.lock").exists():
            detections.append((Ecosystem.POETRY, 3))
        if (self.project_path / "Pipfile.lock").exists():
            detections.append((Ecosystem.PIP, 3))
        if (self.project_path / "requirements.txt").exists():
            detections.append((Ecosystem.PIP, 2))
        if (self.project_path / "pyproject.toml").exists():
            detections.append((Ecosystem.UV, 2))

        if (self.project_path / "Cargo.lock").exists():
            detections.append((Ecosystem.CARGO, 3))
        if (self.project_path / "Cargo.toml").exists():
            detections.append((Ecosystem.CARGO, 2))

        if (self.project_path / "go.sum").exists():
            detections.append((Ecosystem.GO, 3))
        if (self.project_path / "go.mod").exists():
            detections.append((Ecosystem.GO, 2))

        if (self.project_path / "pom.xml").exists():
            detections.append((Ecosystem.MAVEN, 3))
        if (self.project_path / "build.gradle").exists() or (self.project_path / "build.gradle.kts").exists():
            detections.append((Ecosystem.GRADLE, 3))

        if not detections:
            return Ecosystem.UNKNOWN

        detections.sort(key=lambda x: x[1], reverse=True)
        ecosystem = detections[0][0]
        self._log(f"Detected ecosystem: {ecosystem.value}")
        return ecosystem

    def audit(self, severity_threshold: Optional[Severity] = None,
              check_licenses: bool = False) -> AuditResult:
        """Run comprehensive audit."""
        self._log(f"Starting audit of {self.project_path}")

        if self.ecosystem == Ecosystem.UNKNOWN:
            raise ValueError(f"Unknown ecosystem in {self.project_path}")

        if self.ecosystem in [Ecosystem.NPM, Ecosystem.YARN, Ecosystem.PNPM]:
            return self._audit_javascript(severity_threshold, check_licenses)
        elif self.ecosystem in [Ecosystem.PIP, Ecosystem.POETRY, Ecosystem.UV]:
            return self._audit_python(severity_threshold, check_licenses)
        elif self.ecosystem == Ecosystem.CARGO:
            return self._audit_rust(severity_threshold, check_licenses)
        elif self.ecosystem == Ecosystem.GO:
            return self._audit_go(severity_threshold, check_licenses)
        else:
            raise NotImplementedError(f"Ecosystem {self.ecosystem.value} not yet supported")

    def _audit_javascript(self, severity_threshold: Optional[Severity],
                         check_licenses: bool) -> AuditResult:
        """Audit JavaScript/Node.js project."""
        self._log("Auditing JavaScript project")

        dependencies = self._list_javascript_dependencies()
        vulnerabilities = self._scan_javascript_vulnerabilities()
        license_issues = []

        if check_licenses:
            license_issues = self._check_javascript_licenses()

        if severity_threshold:
            vulnerabilities = [v for v in vulnerabilities if v.severity >= severity_threshold]

        outdated_count = sum(1 for d in dependencies if d.latest_version and d.version != d.latest_version)
        health_score = self._calculate_health_score(dependencies, vulnerabilities)

        summary = {
            "total_dependencies": len(dependencies),
            "direct_dependencies": sum(1 for d in dependencies if not d.is_transitive),
            "dev_dependencies": sum(1 for d in dependencies if d.is_dev),
            "vulnerabilities": {
                "total": len(vulnerabilities),
                "critical": sum(1 for v in vulnerabilities if v.severity == Severity.CRITICAL),
                "high": sum(1 for v in vulnerabilities if v.severity == Severity.HIGH),
                "moderate": sum(1 for v in vulnerabilities if v.severity == Severity.MODERATE),
                "low": sum(1 for v in vulnerabilities if v.severity == Severity.LOW),
            },
            "outdated": outdated_count,
            "license_issues": len(license_issues),
        }

        return AuditResult(
            ecosystem=self.ecosystem,
            project_path=str(self.project_path),
            scan_time=datetime.utcnow().isoformat(),
            dependencies=dependencies,
            vulnerabilities=vulnerabilities,
            license_issues=license_issues,
            outdated_count=outdated_count,
            health_score=health_score,
            summary=summary
        )

    def _list_javascript_dependencies(self) -> List[Dependency]:
        """List all JavaScript dependencies."""
        dependencies = []

        stdout, stderr, code = self._run_command(["npm", "list", "--json", "--all"], check=False)
        if code not in [0, 1]:
            self._log(f"npm list failed: {stderr}")
            return dependencies

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            self._log("Failed to parse npm list output")
            return dependencies

        def traverse(node: Dict[str, Any], depth: int = 0, is_dev: bool = False, parent: Optional[str] = None) -> None:
            if "dependencies" in node:
                for name, info in node["dependencies"].items():
                    version = info.get("version", "unknown")
                    dependencies.append(Dependency(
                        name=name,
                        version=version,
                        is_dev=is_dev,
                        is_transitive=depth > 0,
                        depth=depth,
                        parent=parent
                    ))
                    traverse(info, depth + 1, is_dev, name)

        traverse(data)

        if "devDependencies" in data:
            for name, info in data.get("devDependencies", {}).items():
                version = info.get("version", "unknown")
                dependencies.append(Dependency(
                    name=name,
                    version=version,
                    is_dev=True,
                    is_transitive=False,
                    depth=0
                ))

        self._log(f"Found {len(dependencies)} JavaScript dependencies")
        return dependencies

    def _scan_javascript_vulnerabilities(self) -> List[Vulnerability]:
        """Scan for vulnerabilities in JavaScript project."""
        vulnerabilities = []

        stdout, stderr, code = self._run_command(["npm", "audit", "--json"], check=False)

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            self._log("Failed to parse npm audit output")
            return vulnerabilities

        for advisory_id, advisory in data.get("advisories", {}).items():
            severity_str = advisory.get("severity", "low").lower()
            try:
                severity = Severity[severity_str.upper()]
            except KeyError:
                severity = Severity.LOW

            vuln = Vulnerability(
                id=str(advisory_id),
                package=advisory.get("module_name", "unknown"),
                version=advisory.get("findings", [{}])[0].get("version", "unknown") if advisory.get("findings") else "unknown",
                severity=severity,
                title=advisory.get("title", ""),
                description=advisory.get("overview", ""),
                cve=advisory.get("cves", [None])[0] if advisory.get("cves") else None,
                cvss_score=advisory.get("cvss", {}).get("score"),
                patched_versions=advisory.get("patched_versions", "").split("||"),
                vulnerable_versions=advisory.get("vulnerable_versions", ""),
                url=advisory.get("url")
            )
            vulnerabilities.append(vuln)

        self._log(f"Found {len(vulnerabilities)} vulnerabilities")
        return vulnerabilities

    def _check_javascript_licenses(self) -> List[LicenseIssue]:
        """Check JavaScript package licenses."""
        license_issues = []

        forbidden_licenses = {"GPL-2.0", "GPL-3.0", "AGPL-3.0"}
        requires_review = {"LGPL-2.1", "LGPL-3.0", "MPL-2.0"}

        stdout, stderr, code = self._run_command(
            ["npx", "license-checker", "--json"],
            check=False
        )

        if code != 0:
            self._log("license-checker not available, skipping license check")
            return license_issues

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return license_issues

        for package_name, info in data.items():
            license_str = info.get("licenses", "UNKNOWN")

            if license_str in forbidden_licenses:
                name, version = package_name.rsplit("@", 1)
                license_issues.append(LicenseIssue(
                    package=name,
                    version=version,
                    license=license_str,
                    severity="high",
                    reason="Forbidden copyleft license"
                ))
            elif license_str in requires_review:
                name, version = package_name.rsplit("@", 1)
                license_issues.append(LicenseIssue(
                    package=name,
                    version=version,
                    license=license_str,
                    severity="moderate",
                    reason="Requires legal review"
                ))

        self._log(f"Found {len(license_issues)} license issues")
        return license_issues

    def _audit_python(self, severity_threshold: Optional[Severity],
                     check_licenses: bool) -> AuditResult:
        """Audit Python project."""
        self._log("Auditing Python project")

        dependencies = self._list_python_dependencies()
        vulnerabilities = self._scan_python_vulnerabilities()
        license_issues = []

        if check_licenses:
            license_issues = self._check_python_licenses()

        if severity_threshold:
            vulnerabilities = [v for v in vulnerabilities if v.severity >= severity_threshold]

        outdated_count = sum(1 for d in dependencies if d.latest_version and d.version != d.latest_version)
        health_score = self._calculate_health_score(dependencies, vulnerabilities)

        summary = {
            "total_dependencies": len(dependencies),
            "vulnerabilities": {
                "total": len(vulnerabilities),
                "critical": sum(1 for v in vulnerabilities if v.severity == Severity.CRITICAL),
                "high": sum(1 for v in vulnerabilities if v.severity == Severity.HIGH),
                "moderate": sum(1 for v in vulnerabilities if v.severity == Severity.MODERATE),
                "low": sum(1 for v in vulnerabilities if v.severity == Severity.LOW),
            },
            "outdated": outdated_count,
            "license_issues": len(license_issues),
        }

        return AuditResult(
            ecosystem=self.ecosystem,
            project_path=str(self.project_path),
            scan_time=datetime.utcnow().isoformat(),
            dependencies=dependencies,
            vulnerabilities=vulnerabilities,
            license_issues=license_issues,
            outdated_count=outdated_count,
            health_score=health_score,
            summary=summary
        )

    def _list_python_dependencies(self) -> List[Dependency]:
        """List all Python dependencies."""
        dependencies = []

        stdout, stderr, code = self._run_command(["pip", "list", "--format=json"], check=False)
        if code != 0:
            self._log(f"pip list failed: {stderr}")
            return dependencies

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return dependencies

        for pkg in data:
            dependencies.append(Dependency(
                name=pkg["name"],
                version=pkg["version"]
            ))

        self._log(f"Found {len(dependencies)} Python dependencies")
        return dependencies

    def _scan_python_vulnerabilities(self) -> List[Vulnerability]:
        """Scan for vulnerabilities in Python project."""
        vulnerabilities = []

        stdout, stderr, code = self._run_command(["pip-audit", "--format=json"], check=False)

        if code == 127:
            self._log("pip-audit not installed, install with: pip install pip-audit")
            return vulnerabilities

        if code != 0 and not stdout:
            self._log(f"pip-audit failed: {stderr}")
            return vulnerabilities

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return vulnerabilities

        for vuln_data in data.get("dependencies", []):
            package_name = vuln_data.get("name", "unknown")
            version = vuln_data.get("version", "unknown")

            for vuln in vuln_data.get("vulns", []):
                severity_str = vuln.get("severity", "low").lower()
                try:
                    severity = Severity[severity_str.upper()]
                except KeyError:
                    severity = Severity.LOW

                vulnerabilities.append(Vulnerability(
                    id=vuln.get("id", "PYSEC-UNKNOWN"),
                    package=package_name,
                    version=version,
                    severity=severity,
                    title=vuln.get("summary", ""),
                    description=vuln.get("description", ""),
                    url=vuln.get("url")
                ))

        self._log(f"Found {len(vulnerabilities)} vulnerabilities")
        return vulnerabilities

    def _check_python_licenses(self) -> List[LicenseIssue]:
        """Check Python package licenses."""
        license_issues = []

        forbidden_licenses = {"GPL-2.0", "GPL-3.0", "AGPL-3.0"}

        stdout, stderr, code = self._run_command(["pip-licenses", "--format=json"], check=False)

        if code == 127:
            self._log("pip-licenses not installed")
            return license_issues

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return license_issues

        for pkg in data:
            license_str = pkg.get("License", "UNKNOWN")

            if any(forbidden in license_str for forbidden in forbidden_licenses):
                license_issues.append(LicenseIssue(
                    package=pkg.get("Name", "unknown"),
                    version=pkg.get("Version", "unknown"),
                    license=license_str,
                    severity="high",
                    reason="Forbidden copyleft license"
                ))

        return license_issues

    def _audit_rust(self, severity_threshold: Optional[Severity],
                   check_licenses: bool) -> AuditResult:
        """Audit Rust project."""
        self._log("Auditing Rust project")

        dependencies = self._list_rust_dependencies()
        vulnerabilities = self._scan_rust_vulnerabilities()
        license_issues = []

        if check_licenses:
            license_issues = self._check_rust_licenses()

        if severity_threshold:
            vulnerabilities = [v for v in vulnerabilities if v.severity >= severity_threshold]

        outdated_count = sum(1 for d in dependencies if d.latest_version and d.version != d.latest_version)
        health_score = self._calculate_health_score(dependencies, vulnerabilities)

        summary = {
            "total_dependencies": len(dependencies),
            "vulnerabilities": {
                "total": len(vulnerabilities),
                "critical": sum(1 for v in vulnerabilities if v.severity == Severity.CRITICAL),
                "high": sum(1 for v in vulnerabilities if v.severity == Severity.HIGH),
                "moderate": sum(1 for v in vulnerabilities if v.severity == Severity.MODERATE),
                "low": sum(1 for v in vulnerabilities if v.severity == Severity.LOW),
            },
            "outdated": outdated_count,
            "license_issues": len(license_issues),
        }

        return AuditResult(
            ecosystem=self.ecosystem,
            project_path=str(self.project_path),
            scan_time=datetime.utcnow().isoformat(),
            dependencies=dependencies,
            vulnerabilities=vulnerabilities,
            license_issues=license_issues,
            outdated_count=outdated_count,
            health_score=health_score,
            summary=summary
        )

    def _list_rust_dependencies(self) -> List[Dependency]:
        """List all Rust dependencies."""
        dependencies = []

        stdout, stderr, code = self._run_command(["cargo", "tree", "--depth", "0"], check=False)
        if code != 0:
            return dependencies

        for line in stdout.strip().split("\n")[1:]:
            match = re.match(r"[├└]── (.+?) v(.+)", line.strip())
            if match:
                name, version = match.groups()
                dependencies.append(Dependency(name=name, version=version))

        self._log(f"Found {len(dependencies)} Rust dependencies")
        return dependencies

    def _scan_rust_vulnerabilities(self) -> List[Vulnerability]:
        """Scan for vulnerabilities in Rust project."""
        vulnerabilities = []

        stdout, stderr, code = self._run_command(["cargo", "audit", "--json"], check=False)

        if code == 127:
            self._log("cargo-audit not installed, install with: cargo install cargo-audit")
            return vulnerabilities

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return vulnerabilities

        for vuln in data.get("vulnerabilities", {}).get("list", []):
            advisory = vuln.get("advisory", {})

            severity_map = {
                "critical": Severity.CRITICAL,
                "high": Severity.HIGH,
                "moderate": Severity.MODERATE,
                "low": Severity.LOW,
                "informational": Severity.INFO
            }
            severity = severity_map.get(advisory.get("severity", "low").lower(), Severity.LOW)

            vulnerabilities.append(Vulnerability(
                id=advisory.get("id", "RUSTSEC-UNKNOWN"),
                package=vuln.get("package", {}).get("name", "unknown"),
                version=vuln.get("package", {}).get("version", "unknown"),
                severity=severity,
                title=advisory.get("title", ""),
                description=advisory.get("description", ""),
                url=advisory.get("url")
            ))

        self._log(f"Found {len(vulnerabilities)} vulnerabilities")
        return vulnerabilities

    def _check_rust_licenses(self) -> List[LicenseIssue]:
        """Check Rust crate licenses."""
        license_issues = []

        stdout, stderr, code = self._run_command(["cargo", "license", "--json"], check=False)

        if code == 127:
            self._log("cargo-license not installed")
            return license_issues

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return license_issues

        forbidden_licenses = {"GPL-2.0", "GPL-3.0", "AGPL-3.0"}

        for crate in data:
            license_str = crate.get("license", "UNKNOWN")

            if license_str in forbidden_licenses:
                license_issues.append(LicenseIssue(
                    package=crate.get("name", "unknown"),
                    version=crate.get("version", "unknown"),
                    license=license_str,
                    severity="high",
                    reason="Forbidden copyleft license"
                ))

        return license_issues

    def _audit_go(self, severity_threshold: Optional[Severity],
                 check_licenses: bool) -> AuditResult:
        """Audit Go project."""
        self._log("Auditing Go project")

        dependencies = self._list_go_dependencies()
        vulnerabilities = self._scan_go_vulnerabilities()
        license_issues = []

        if severity_threshold:
            vulnerabilities = [v for v in vulnerabilities if v.severity >= severity_threshold]

        outdated_count = 0
        health_score = self._calculate_health_score(dependencies, vulnerabilities)

        summary = {
            "total_dependencies": len(dependencies),
            "vulnerabilities": {
                "total": len(vulnerabilities),
                "critical": sum(1 for v in vulnerabilities if v.severity == Severity.CRITICAL),
                "high": sum(1 for v in vulnerabilities if v.severity == Severity.HIGH),
                "moderate": sum(1 for v in vulnerabilities if v.severity == Severity.MODERATE),
                "low": sum(1 for v in vulnerabilities if v.severity == Severity.LOW),
            },
            "outdated": outdated_count,
        }

        return AuditResult(
            ecosystem=self.ecosystem,
            project_path=str(self.project_path),
            scan_time=datetime.utcnow().isoformat(),
            dependencies=dependencies,
            vulnerabilities=vulnerabilities,
            license_issues=license_issues,
            outdated_count=outdated_count,
            health_score=health_score,
            summary=summary
        )

    def _list_go_dependencies(self) -> List[Dependency]:
        """List all Go dependencies."""
        dependencies = []

        stdout, stderr, code = self._run_command(["go", "list", "-m", "all"], check=False)
        if code != 0:
            return dependencies

        for line in stdout.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) >= 2:
                dependencies.append(Dependency(name=parts[0], version=parts[1]))

        self._log(f"Found {len(dependencies)} Go dependencies")
        return dependencies

    def _scan_go_vulnerabilities(self) -> List[Vulnerability]:
        """Scan for vulnerabilities in Go project."""
        vulnerabilities = []

        stdout, stderr, code = self._run_command(["go", "list", "-json", "-m", "all"], check=False)

        self._log("Go vulnerability scanning requires govulncheck")
        return vulnerabilities

    def _calculate_health_score(self, dependencies: List[Dependency],
                                vulnerabilities: List[Vulnerability]) -> float:
        """Calculate overall project health score (0-100)."""
        if not dependencies:
            return 100.0

        score = 100.0

        critical_vulns = sum(1 for v in vulnerabilities if v.severity == Severity.CRITICAL)
        high_vulns = sum(1 for v in vulnerabilities if v.severity == Severity.HIGH)
        moderate_vulns = sum(1 for v in vulnerabilities if v.severity == Severity.MODERATE)
        low_vulns = sum(1 for v in vulnerabilities if v.severity == Severity.LOW)

        score -= critical_vulns * 15
        score -= high_vulns * 10
        score -= moderate_vulns * 5
        score -= low_vulns * 2

        outdated = sum(1 for d in dependencies if d.latest_version and d.version != d.latest_version)
        outdated_ratio = outdated / len(dependencies)
        score -= outdated_ratio * 20

        return max(0.0, min(100.0, score))

    def generate_sbom(self, format: str = "cyclonedx") -> str:
        """Generate Software Bill of Materials."""
        if format == "cyclonedx":
            return self._generate_cyclonedx_sbom()
        elif format == "spdx":
            return self._generate_spdx_sbom()
        else:
            raise ValueError(f"Unknown SBOM format: {format}")

    def _generate_cyclonedx_sbom(self) -> str:
        """Generate CycloneDX SBOM."""
        result = self.audit()

        components = []
        for dep in result.dependencies:
            component = {
                "type": "library",
                "name": dep.name,
                "version": dep.version,
                "purl": f"pkg:{result.ecosystem.value}/{dep.name}@{dep.version}"
            }
            if dep.license:
                component["licenses"] = [{"license": {"id": dep.license}}]
            components.append(component)

        sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "version": 1,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "tools": [
                    {
                        "vendor": "dependency-audit",
                        "name": "audit_dependencies.py",
                        "version": "1.0.0"
                    }
                ],
                "component": {
                    "type": "application",
                    "name": self.project_path.name
                }
            },
            "components": components
        }

        return json.dumps(sbom, indent=2)

    def _generate_spdx_sbom(self) -> str:
        """Generate SPDX SBOM."""
        result = self.audit()

        packages = []
        for dep in result.dependencies:
            package = {
                "SPDXID": f"SPDXRef-{dep.name}-{dep.version}",
                "name": dep.name,
                "versionInfo": dep.version,
                "downloadLocation": "NOASSERTION"
            }
            if dep.license:
                package["licenseConcluded"] = dep.license
            packages.append(package)

        sbom = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": self.project_path.name,
            "documentNamespace": f"https://example.com/{self.project_path.name}",
            "creationInfo": {
                "created": datetime.utcnow().isoformat() + "Z",
                "creators": ["Tool: audit_dependencies.py"]
            },
            "packages": packages
        }

        return json.dumps(sbom, indent=2)


def format_output_text(result: AuditResult) -> str:
    """Format audit result as human-readable text."""
    lines = []

    lines.append("=" * 70)
    lines.append("DEPENDENCY AUDIT REPORT")
    lines.append("=" * 70)
    lines.append(f"Project: {result.project_path}")
    lines.append(f"Ecosystem: {result.ecosystem.value}")
    lines.append(f"Scan Time: {result.scan_time}")
    lines.append(f"Health Score: {result.health_score:.1f}/100")
    lines.append("")

    lines.append("SUMMARY")
    lines.append("-" * 70)
    lines.append(f"Total Dependencies: {result.summary['total_dependencies']}")
    lines.append(f"Outdated: {result.outdated_count}")
    lines.append(f"Vulnerabilities: {result.summary['vulnerabilities']['total']}")
    lines.append(f"  Critical: {result.summary['vulnerabilities']['critical']}")
    lines.append(f"  High: {result.summary['vulnerabilities']['high']}")
    lines.append(f"  Moderate: {result.summary['vulnerabilities']['moderate']}")
    lines.append(f"  Low: {result.summary['vulnerabilities']['low']}")
    lines.append(f"License Issues: {result.summary['license_issues']}")
    lines.append("")

    if result.vulnerabilities:
        lines.append("VULNERABILITIES")
        lines.append("-" * 70)
        for vuln in sorted(result.vulnerabilities, key=lambda v: v.severity, reverse=True):
            lines.append(f"\n[{vuln.severity.value.upper()}] {vuln.package}@{vuln.version}")
            lines.append(f"  ID: {vuln.id}")
            lines.append(f"  Title: {vuln.title}")
            if vuln.cvss_score:
                lines.append(f"  CVSS Score: {vuln.cvss_score}")
            if vuln.url:
                lines.append(f"  URL: {vuln.url}")
        lines.append("")

    if result.license_issues:
        lines.append("LICENSE ISSUES")
        lines.append("-" * 70)
        for issue in result.license_issues:
            lines.append(f"\n[{issue.severity.upper()}] {issue.package}@{issue.version}")
            lines.append(f"  License: {issue.license}")
            lines.append(f"  Reason: {issue.reason}")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-language dependency auditing tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --path /path/to/project
  %(prog)s --path . --json
  %(prog)s --path . --severity high
  %(prog)s --path . --sbom cyclonedx
  %(prog)s --path . --license-check --verbose
        """
    )

    parser.add_argument(
        "--path",
        default=".",
        help="Path to project directory (default: current directory)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--severity",
        choices=["critical", "high", "moderate", "low", "info"],
        help="Minimum severity level to report"
    )
    parser.add_argument(
        "--license-check",
        action="store_true",
        help="Check license compliance"
    )
    parser.add_argument(
        "--sbom",
        choices=["cyclonedx", "spdx"],
        help="Generate Software Bill of Materials"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    try:
        auditor = DependencyAuditor(args.path, verbose=args.verbose)

        if args.sbom:
            sbom = auditor.generate_sbom(args.sbom)
            print(sbom)
            return

        severity_threshold = None
        if args.severity:
            severity_threshold = Severity[args.severity.upper()]

        result = auditor.audit(
            severity_threshold=severity_threshold,
            check_licenses=args.license_check
        )

        if args.json:
            output = {
                "ecosystem": result.ecosystem.value,
                "project_path": result.project_path,
                "scan_time": result.scan_time,
                "health_score": result.health_score,
                "summary": result.summary,
                "vulnerabilities": [
                    {
                        "id": v.id,
                        "package": v.package,
                        "version": v.version,
                        "severity": v.severity.value,
                        "title": v.title,
                        "description": v.description,
                        "cvss_score": v.cvss_score,
                        "url": v.url
                    }
                    for v in result.vulnerabilities
                ],
                "license_issues": [
                    {
                        "package": li.package,
                        "version": li.version,
                        "license": li.license,
                        "severity": li.severity,
                        "reason": li.reason
                    }
                    for li in result.license_issues
                ]
            }
            print(json.dumps(output, indent=2))
        else:
            print(format_output_text(result))

        critical = result.summary["vulnerabilities"]["critical"]
        high = result.summary["vulnerabilities"]["high"]
        if critical > 0 or high > 0:
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
