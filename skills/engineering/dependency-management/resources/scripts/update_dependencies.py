#!/usr/bin/env python3
"""
Automated dependency update tool with testing and rollback.

Features:
- Multi-language support (npm, pip, cargo, go)
- Update strategies (conservative, balanced, aggressive)
- Automatic testing after updates
- Rollback on test failure
- Grouped updates
- Security-only mode

Usage:
    ./update_dependencies.py --path /path/to/project
    ./update_dependencies.py --path . --strategy conservative
    ./update_dependencies.py --path . --security-only
    ./update_dependencies.py --path . --package express
    ./update_dependencies.py --path . --test-command "npm test"
    ./update_dependencies.py --path . --json --verbose
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class UpdateStrategy(Enum):
    """Dependency update strategies."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class UpdateType(Enum):
    """Type of dependency update."""
    SECURITY = "security"
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"


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
    UNKNOWN = "unknown"


@dataclass
class DependencyUpdate:
    """Information about a dependency update."""
    name: str
    current_version: str
    target_version: str
    update_type: UpdateType
    is_security: bool = False
    breaking_changes: bool = False
    changelog_url: Optional[str] = None


@dataclass
class UpdateResult:
    """Result of dependency update operation."""
    success: bool
    ecosystem: Ecosystem
    updates_applied: List[DependencyUpdate]
    updates_failed: List[DependencyUpdate]
    test_output: Optional[str] = None
    rollback_performed: bool = False
    error_message: Optional[str] = None


class DependencyUpdater:
    """Automated dependency updater with testing and rollback."""

    def __init__(self, project_path: str, verbose: bool = False):
        self.project_path = Path(project_path).resolve()
        self.verbose = verbose
        self.ecosystem = self._detect_ecosystem()
        self.backup_dir: Optional[Path] = None

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
                timeout=600
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
        if (self.project_path / "package-lock.json").exists():
            return Ecosystem.NPM
        if (self.project_path / "yarn.lock").exists():
            return Ecosystem.YARN
        if (self.project_path / "pnpm-lock.yaml").exists():
            return Ecosystem.PNPM
        if (self.project_path / "poetry.lock").exists():
            return Ecosystem.POETRY
        if (self.project_path / "pyproject.toml").exists():
            return Ecosystem.UV
        if (self.project_path / "requirements.txt").exists():
            return Ecosystem.PIP
        if (self.project_path / "Cargo.lock").exists():
            return Ecosystem.CARGO
        if (self.project_path / "go.sum").exists():
            return Ecosystem.GO

        return Ecosystem.UNKNOWN

    def _create_backup(self) -> None:
        """Create backup of dependency files."""
        self.backup_dir = Path(tempfile.mkdtemp(prefix="dep_backup_"))
        self._log(f"Creating backup in {self.backup_dir}")

        files_to_backup = []

        if self.ecosystem in [Ecosystem.NPM, Ecosystem.YARN, Ecosystem.PNPM]:
            files_to_backup.extend(["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"])
        elif self.ecosystem in [Ecosystem.PIP, Ecosystem.POETRY, Ecosystem.UV]:
            files_to_backup.extend(["requirements.txt", "poetry.lock", "Pipfile.lock", "pyproject.toml", "uv.lock"])
        elif self.ecosystem == Ecosystem.CARGO:
            files_to_backup.extend(["Cargo.toml", "Cargo.lock"])
        elif self.ecosystem == Ecosystem.GO:
            files_to_backup.extend(["go.mod", "go.sum"])

        for filename in files_to_backup:
            src = self.project_path / filename
            if src.exists():
                dst = self.backup_dir / filename
                shutil.copy2(src, dst)
                self._log(f"Backed up {filename}")

    def _restore_backup(self) -> None:
        """Restore from backup."""
        if not self.backup_dir or not self.backup_dir.exists():
            raise RuntimeError("No backup available to restore")

        self._log(f"Restoring from backup {self.backup_dir}")

        for backup_file in self.backup_dir.iterdir():
            dst = self.project_path / backup_file.name
            shutil.copy2(backup_file, dst)
            self._log(f"Restored {backup_file.name}")

        self._cleanup_backup()

    def _cleanup_backup(self) -> None:
        """Clean up backup directory."""
        if self.backup_dir and self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
            self._log(f"Cleaned up backup {self.backup_dir}")
            self.backup_dir = None

    def update(
        self,
        strategy: UpdateStrategy = UpdateStrategy.BALANCED,
        security_only: bool = False,
        package_name: Optional[str] = None,
        test_command: Optional[str] = None,
        skip_tests: bool = False
    ) -> UpdateResult:
        """Update dependencies with specified strategy."""
        self._log(f"Starting update with strategy: {strategy.value}")

        if self.ecosystem == Ecosystem.UNKNOWN:
            return UpdateResult(
                success=False,
                ecosystem=self.ecosystem,
                updates_applied=[],
                updates_failed=[],
                error_message="Unknown ecosystem"
            )

        try:
            self._create_backup()

            if self.ecosystem in [Ecosystem.NPM, Ecosystem.YARN, Ecosystem.PNPM]:
                result = self._update_javascript(strategy, security_only, package_name)
            elif self.ecosystem in [Ecosystem.PIP, Ecosystem.POETRY, Ecosystem.UV]:
                result = self._update_python(strategy, security_only, package_name)
            elif self.ecosystem == Ecosystem.CARGO:
                result = self._update_rust(strategy, security_only, package_name)
            elif self.ecosystem == Ecosystem.GO:
                result = self._update_go(strategy, security_only, package_name)
            else:
                return UpdateResult(
                    success=False,
                    ecosystem=self.ecosystem,
                    updates_applied=[],
                    updates_failed=[],
                    error_message=f"Ecosystem {self.ecosystem.value} not supported"
                )

            if not result.success:
                self._log("Update failed, restoring backup")
                self._restore_backup()
                result.rollback_performed = True
                return result

            if not skip_tests and test_command:
                self._log(f"Running tests: {test_command}")
                stdout, stderr, code = self._run_command(test_command.split(), check=False)
                result.test_output = stdout + stderr

                if code != 0:
                    self._log("Tests failed, rolling back")
                    self._restore_backup()
                    result.success = False
                    result.rollback_performed = True
                    result.error_message = "Tests failed after update"
                    return result

            self._cleanup_backup()
            return result

        except Exception as e:
            self._log(f"Error during update: {e}")
            if self.backup_dir:
                self._restore_backup()
            return UpdateResult(
                success=False,
                ecosystem=self.ecosystem,
                updates_applied=[],
                updates_failed=[],
                rollback_performed=True,
                error_message=str(e)
            )

    def _update_javascript(
        self,
        strategy: UpdateStrategy,
        security_only: bool,
        package_name: Optional[str]
    ) -> UpdateResult:
        """Update JavaScript dependencies."""
        self._log("Updating JavaScript dependencies")

        updates_applied = []
        updates_failed = []

        if security_only:
            stdout, stderr, code = self._run_command(["npm", "audit", "fix"], check=False)
            if code == 0:
                updates_applied.append(DependencyUpdate(
                    name="security-updates",
                    current_version="",
                    target_version="",
                    update_type=UpdateType.SECURITY,
                    is_security=True
                ))
            else:
                return UpdateResult(
                    success=False,
                    ecosystem=self.ecosystem,
                    updates_applied=[],
                    updates_failed=[],
                    error_message=f"npm audit fix failed: {stderr}"
                )
        elif package_name:
            target_version = self._get_latest_npm_version(package_name, strategy)
            stdout, stderr, code = self._run_command(
                ["npm", "install", f"{package_name}@{target_version}"],
                check=False
            )
            if code == 0:
                updates_applied.append(DependencyUpdate(
                    name=package_name,
                    current_version="",
                    target_version=target_version,
                    update_type=UpdateType.MINOR
                ))
            else:
                updates_failed.append(DependencyUpdate(
                    name=package_name,
                    current_version="",
                    target_version=target_version,
                    update_type=UpdateType.MINOR
                ))
        else:
            stdout, stderr, code = self._run_command(["npm", "outdated", "--json"], check=False)

            try:
                outdated = json.loads(stdout) if stdout else {}
            except json.JSONDecodeError:
                outdated = {}

            for pkg_name, info in outdated.items():
                current = info.get("current", "")
                wanted = info.get("wanted", "")
                latest = info.get("latest", "")

                update_type = self._classify_update_type(current, latest)

                if strategy == UpdateStrategy.CONSERVATIVE and update_type == UpdateType.MAJOR:
                    continue
                if strategy == UpdateStrategy.BALANCED and update_type == UpdateType.MAJOR:
                    continue

                target = wanted if strategy == UpdateStrategy.CONSERVATIVE else latest

                self._log(f"Updating {pkg_name}: {current} -> {target}")
                stdout, stderr, code = self._run_command(
                    ["npm", "install", f"{pkg_name}@{target}"],
                    check=False
                )

                update = DependencyUpdate(
                    name=pkg_name,
                    current_version=current,
                    target_version=target,
                    update_type=update_type
                )

                if code == 0:
                    updates_applied.append(update)
                else:
                    updates_failed.append(update)

        return UpdateResult(
            success=len(updates_failed) == 0,
            ecosystem=self.ecosystem,
            updates_applied=updates_applied,
            updates_failed=updates_failed
        )

    def _update_python(
        self,
        strategy: UpdateStrategy,
        security_only: bool,
        package_name: Optional[str]
    ) -> UpdateResult:
        """Update Python dependencies."""
        self._log("Updating Python dependencies")

        updates_applied = []
        updates_failed = []

        if self.ecosystem == Ecosystem.UV:
            if package_name:
                stdout, stderr, code = self._run_command(
                    ["uv", "add", "--upgrade", package_name],
                    check=False
                )
                if code == 0:
                    updates_applied.append(DependencyUpdate(
                        name=package_name,
                        current_version="",
                        target_version="",
                        update_type=UpdateType.MINOR
                    ))
                else:
                    updates_failed.append(DependencyUpdate(
                        name=package_name,
                        current_version="",
                        target_version="",
                        update_type=UpdateType.MINOR
                    ))
            else:
                stdout, stderr, code = self._run_command(["uv", "sync", "--upgrade"], check=False)
                if code == 0:
                    updates_applied.append(DependencyUpdate(
                        name="all-packages",
                        current_version="",
                        target_version="",
                        update_type=UpdateType.MINOR
                    ))
        elif self.ecosystem == Ecosystem.POETRY:
            if package_name:
                stdout, stderr, code = self._run_command(
                    ["poetry", "update", package_name],
                    check=False
                )
                if code == 0:
                    updates_applied.append(DependencyUpdate(
                        name=package_name,
                        current_version="",
                        target_version="",
                        update_type=UpdateType.MINOR
                    ))
            else:
                stdout, stderr, code = self._run_command(["poetry", "update"], check=False)
                if code == 0:
                    updates_applied.append(DependencyUpdate(
                        name="all-packages",
                        current_version="",
                        target_version="",
                        update_type=UpdateType.MINOR
                    ))
        else:
            stdout, stderr, code = self._run_command(
                ["pip", "list", "--outdated", "--format=json"],
                check=False
            )

            try:
                outdated = json.loads(stdout) if stdout else []
            except json.JSONDecodeError:
                outdated = []

            for pkg in outdated:
                pkg_name = pkg["name"]
                current = pkg["version"]
                latest = pkg["latest_version"]

                if package_name and pkg_name != package_name:
                    continue

                update_type = self._classify_update_type(current, latest)

                if strategy == UpdateStrategy.CONSERVATIVE and update_type == UpdateType.MAJOR:
                    continue

                self._log(f"Updating {pkg_name}: {current} -> {latest}")
                stdout, stderr, code = self._run_command(
                    ["pip", "install", "--upgrade", pkg_name],
                    check=False
                )

                update = DependencyUpdate(
                    name=pkg_name,
                    current_version=current,
                    target_version=latest,
                    update_type=update_type
                )

                if code == 0:
                    updates_applied.append(update)
                else:
                    updates_failed.append(update)

        return UpdateResult(
            success=len(updates_failed) == 0,
            ecosystem=self.ecosystem,
            updates_applied=updates_applied,
            updates_failed=updates_failed
        )

    def _update_rust(
        self,
        strategy: UpdateStrategy,
        security_only: bool,
        package_name: Optional[str]
    ) -> UpdateResult:
        """Update Rust dependencies."""
        self._log("Updating Rust dependencies")

        updates_applied = []
        updates_failed = []

        if package_name:
            stdout, stderr, code = self._run_command(
                ["cargo", "update", "-p", package_name],
                check=False
            )
            if code == 0:
                updates_applied.append(DependencyUpdate(
                    name=package_name,
                    current_version="",
                    target_version="",
                    update_type=UpdateType.MINOR
                ))
            else:
                updates_failed.append(DependencyUpdate(
                    name=package_name,
                    current_version="",
                    target_version="",
                    update_type=UpdateType.MINOR
                ))
        else:
            stdout, stderr, code = self._run_command(["cargo", "update"], check=False)
            if code == 0:
                updates_applied.append(DependencyUpdate(
                    name="all-packages",
                    current_version="",
                    target_version="",
                    update_type=UpdateType.MINOR
                ))
            else:
                return UpdateResult(
                    success=False,
                    ecosystem=self.ecosystem,
                    updates_applied=[],
                    updates_failed=[],
                    error_message=f"cargo update failed: {stderr}"
                )

        if strategy == UpdateStrategy.AGGRESSIVE:
            stdout, stderr, code = self._run_command(
                ["cargo", "outdated", "--format", "json"],
                check=False
            )

            if code == 127:
                self._log("cargo-outdated not installed")
            elif code == 0:
                try:
                    outdated = json.loads(stdout)
                    for dep in outdated.get("dependencies", []):
                        if dep.get("latest") and dep.get("latest") != dep.get("project"):
                            self._log(f"Updating {dep['name']} to {dep['latest']}")
                except json.JSONDecodeError:
                    pass

        return UpdateResult(
            success=len(updates_failed) == 0,
            ecosystem=self.ecosystem,
            updates_applied=updates_applied,
            updates_failed=updates_failed
        )

    def _update_go(
        self,
        strategy: UpdateStrategy,
        security_only: bool,
        package_name: Optional[str]
    ) -> UpdateResult:
        """Update Go dependencies."""
        self._log("Updating Go dependencies")

        updates_applied = []
        updates_failed = []

        if package_name:
            stdout, stderr, code = self._run_command(
                ["go", "get", "-u", package_name],
                check=False
            )
            if code == 0:
                updates_applied.append(DependencyUpdate(
                    name=package_name,
                    current_version="",
                    target_version="",
                    update_type=UpdateType.MINOR
                ))
            else:
                updates_failed.append(DependencyUpdate(
                    name=package_name,
                    current_version="",
                    target_version="",
                    update_type=UpdateType.MINOR
                ))
        else:
            if strategy == UpdateStrategy.AGGRESSIVE:
                stdout, stderr, code = self._run_command(["go", "get", "-u", "./..."], check=False)
            else:
                stdout, stderr, code = self._run_command(["go", "get", "-u=patch", "./..."], check=False)

            if code == 0:
                updates_applied.append(DependencyUpdate(
                    name="all-packages",
                    current_version="",
                    target_version="",
                    update_type=UpdateType.MINOR if strategy == UpdateStrategy.AGGRESSIVE else UpdateType.PATCH
                ))
            else:
                return UpdateResult(
                    success=False,
                    ecosystem=self.ecosystem,
                    updates_applied=[],
                    updates_failed=[],
                    error_message=f"go get failed: {stderr}"
                )

        stdout, stderr, code = self._run_command(["go", "mod", "tidy"], check=False)

        return UpdateResult(
            success=len(updates_failed) == 0,
            ecosystem=self.ecosystem,
            updates_applied=updates_applied,
            updates_failed=updates_failed
        )

    def _get_latest_npm_version(self, package_name: str, strategy: UpdateStrategy) -> str:
        """Get latest version of npm package based on strategy."""
        stdout, stderr, code = self._run_command(
            ["npm", "view", package_name, "version"],
            check=False
        )
        if code == 0:
            return stdout.strip()
        return "latest"

    def _classify_update_type(self, current: str, target: str) -> UpdateType:
        """Classify update type based on version change."""
        try:
            current_parts = [int(x) for x in current.split(".")[:3]]
            target_parts = [int(x) for x in target.split(".")[:3]]

            while len(current_parts) < 3:
                current_parts.append(0)
            while len(target_parts) < 3:
                target_parts.append(0)

            if target_parts[0] > current_parts[0]:
                return UpdateType.MAJOR
            elif target_parts[1] > current_parts[1]:
                return UpdateType.MINOR
            elif target_parts[2] > current_parts[2]:
                return UpdateType.PATCH
            else:
                return UpdateType.PATCH
        except (ValueError, IndexError):
            return UpdateType.MINOR

    def dry_run(
        self,
        strategy: UpdateStrategy = UpdateStrategy.BALANCED,
        security_only: bool = False
    ) -> List[DependencyUpdate]:
        """Perform dry run to show what would be updated."""
        self._log("Performing dry run")

        if self.ecosystem in [Ecosystem.NPM, Ecosystem.YARN, Ecosystem.PNPM]:
            return self._dry_run_javascript(strategy, security_only)
        elif self.ecosystem in [Ecosystem.PIP, Ecosystem.POETRY, Ecosystem.UV]:
            return self._dry_run_python(strategy, security_only)
        elif self.ecosystem == Ecosystem.CARGO:
            return self._dry_run_rust(strategy, security_only)
        elif self.ecosystem == Ecosystem.GO:
            return self._dry_run_go(strategy, security_only)
        else:
            return []

    def _dry_run_javascript(self, strategy: UpdateStrategy, security_only: bool) -> List[DependencyUpdate]:
        """Dry run for JavaScript."""
        updates = []

        if security_only:
            stdout, stderr, code = self._run_command(["npm", "audit", "--json"], check=False)
            try:
                data = json.loads(stdout) if stdout else {}
                vuln_count = data.get("metadata", {}).get("vulnerabilities", {}).get("total", 0)
                if vuln_count > 0:
                    updates.append(DependencyUpdate(
                        name="security-updates",
                        current_version="",
                        target_version="",
                        update_type=UpdateType.SECURITY,
                        is_security=True
                    ))
            except json.JSONDecodeError:
                pass
        else:
            stdout, stderr, code = self._run_command(["npm", "outdated", "--json"], check=False)
            try:
                outdated = json.loads(stdout) if stdout else {}
                for pkg_name, info in outdated.items():
                    current = info.get("current", "")
                    wanted = info.get("wanted", "")
                    latest = info.get("latest", "")

                    update_type = self._classify_update_type(current, latest)

                    if strategy == UpdateStrategy.CONSERVATIVE and update_type == UpdateType.MAJOR:
                        continue
                    if strategy == UpdateStrategy.BALANCED and update_type == UpdateType.MAJOR:
                        continue

                    target = wanted if strategy == UpdateStrategy.CONSERVATIVE else latest

                    updates.append(DependencyUpdate(
                        name=pkg_name,
                        current_version=current,
                        target_version=target,
                        update_type=update_type
                    ))
            except json.JSONDecodeError:
                pass

        return updates

    def _dry_run_python(self, strategy: UpdateStrategy, security_only: bool) -> List[DependencyUpdate]:
        """Dry run for Python."""
        updates = []

        stdout, stderr, code = self._run_command(
            ["pip", "list", "--outdated", "--format=json"],
            check=False
        )

        try:
            outdated = json.loads(stdout) if stdout else []
            for pkg in outdated:
                pkg_name = pkg["name"]
                current = pkg["version"]
                latest = pkg["latest_version"]

                update_type = self._classify_update_type(current, latest)

                if strategy == UpdateStrategy.CONSERVATIVE and update_type == UpdateType.MAJOR:
                    continue

                updates.append(DependencyUpdate(
                    name=pkg_name,
                    current_version=current,
                    target_version=latest,
                    update_type=update_type
                ))
        except json.JSONDecodeError:
            pass

        return updates

    def _dry_run_rust(self, strategy: UpdateStrategy, security_only: bool) -> List[DependencyUpdate]:
        """Dry run for Rust."""
        updates = []

        stdout, stderr, code = self._run_command(
            ["cargo", "outdated", "--format", "json"],
            check=False
        )

        if code == 127:
            self._log("cargo-outdated not installed, run: cargo install cargo-outdated")
            return updates

        try:
            data = json.loads(stdout) if stdout else {}
            for dep in data.get("dependencies", []):
                current = dep.get("project", "")
                compatible = dep.get("compat", "")
                latest = dep.get("latest", "")

                if not latest or latest == current:
                    continue

                update_type = self._classify_update_type(current, latest)

                if strategy == UpdateStrategy.CONSERVATIVE:
                    target = compatible
                elif strategy == UpdateStrategy.BALANCED:
                    target = compatible if update_type != UpdateType.MAJOR else current
                else:
                    target = latest

                if target and target != current:
                    updates.append(DependencyUpdate(
                        name=dep["name"],
                        current_version=current,
                        target_version=target,
                        update_type=update_type
                    ))
        except json.JSONDecodeError:
            pass

        return updates

    def _dry_run_go(self, strategy: UpdateStrategy, security_only: bool) -> List[DependencyUpdate]:
        """Dry run for Go."""
        updates = []

        stdout, stderr, code = self._run_command(["go", "list", "-m", "-u", "all"], check=False)

        for line in stdout.strip().split("\n"):
            if "[" in line:
                parts = line.split()
                if len(parts) >= 3:
                    name = parts[0]
                    current = parts[1]
                    latest = parts[2].strip("[]")

                    update_type = self._classify_update_type(current, latest)

                    if strategy == UpdateStrategy.CONSERVATIVE and update_type == UpdateType.MAJOR:
                        continue

                    updates.append(DependencyUpdate(
                        name=name,
                        current_version=current,
                        target_version=latest,
                        update_type=update_type
                    ))

        return updates


def format_output_text(result: UpdateResult) -> str:
    """Format update result as human-readable text."""
    lines = []

    lines.append("=" * 70)
    lines.append("DEPENDENCY UPDATE REPORT")
    lines.append("=" * 70)
    lines.append(f"Ecosystem: {result.ecosystem.value}")
    lines.append(f"Success: {result.success}")
    lines.append(f"Rollback Performed: {result.rollback_performed}")
    lines.append("")

    if result.updates_applied:
        lines.append("UPDATES APPLIED")
        lines.append("-" * 70)
        for update in result.updates_applied:
            lines.append(f"✓ {update.name}")
            if update.current_version and update.target_version:
                lines.append(f"  {update.current_version} → {update.target_version} ({update.update_type.value})")
        lines.append("")

    if result.updates_failed:
        lines.append("UPDATES FAILED")
        lines.append("-" * 70)
        for update in result.updates_failed:
            lines.append(f"✗ {update.name}")
            if update.current_version and update.target_version:
                lines.append(f"  {update.current_version} → {update.target_version} ({update.update_type.value})")
        lines.append("")

    if result.error_message:
        lines.append("ERROR")
        lines.append("-" * 70)
        lines.append(result.error_message)
        lines.append("")

    if result.test_output:
        lines.append("TEST OUTPUT")
        lines.append("-" * 70)
        lines.append(result.test_output)
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated dependency update tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --path /path/to/project
  %(prog)s --path . --strategy conservative
  %(prog)s --path . --security-only
  %(prog)s --path . --package express
  %(prog)s --path . --test-command "npm test"
  %(prog)s --path . --dry-run
  %(prog)s --path . --json --verbose
        """
    )

    parser.add_argument(
        "--path",
        default=".",
        help="Path to project directory (default: current directory)"
    )
    parser.add_argument(
        "--strategy",
        choices=["conservative", "balanced", "aggressive"],
        default="balanced",
        help="Update strategy (default: balanced)"
    )
    parser.add_argument(
        "--security-only",
        action="store_true",
        help="Only apply security updates"
    )
    parser.add_argument(
        "--package",
        help="Update specific package only"
    )
    parser.add_argument(
        "--test-command",
        help="Command to run tests after update"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    try:
        updater = DependencyUpdater(args.path, verbose=args.verbose)

        strategy = UpdateStrategy[args.strategy.upper()]

        if args.dry_run:
            updates = updater.dry_run(strategy, args.security_only)

            if args.json:
                output = [
                    {
                        "name": u.name,
                        "current_version": u.current_version,
                        "target_version": u.target_version,
                        "update_type": u.update_type.value,
                        "is_security": u.is_security
                    }
                    for u in updates
                ]
                print(json.dumps(output, indent=2))
            else:
                print(f"Would update {len(updates)} packages:")
                for update in updates:
                    print(f"  {update.name}: {update.current_version} → {update.target_version} ({update.update_type.value})")
            return

        result = updater.update(
            strategy=strategy,
            security_only=args.security_only,
            package_name=args.package,
            test_command=args.test_command,
            skip_tests=args.skip_tests
        )

        if args.json:
            output = {
                "success": result.success,
                "ecosystem": result.ecosystem.value,
                "rollback_performed": result.rollback_performed,
                "updates_applied": [
                    {
                        "name": u.name,
                        "current_version": u.current_version,
                        "target_version": u.target_version,
                        "update_type": u.update_type.value,
                        "is_security": u.is_security
                    }
                    for u in result.updates_applied
                ],
                "updates_failed": [
                    {
                        "name": u.name,
                        "current_version": u.current_version,
                        "target_version": u.target_version,
                        "update_type": u.update_type.value
                    }
                    for u in result.updates_failed
                ],
                "error_message": result.error_message
            }
            print(json.dumps(output, indent=2))
        else:
            print(format_output_text(result))

        sys.exit(0 if result.success else 1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
