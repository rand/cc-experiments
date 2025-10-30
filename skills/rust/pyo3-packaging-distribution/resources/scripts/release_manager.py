#!/usr/bin/env python3
"""
PyO3 Release Manager - Automated version bumping, changelog, and release workflow

This script provides comprehensive release management for PyO3 projects:
- Automated version bumping (major/minor/patch)
- Changelog generation from git commits
- Git tagging workflow
- PyPI release automation
- GitHub release creation
- Pre-release validation
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
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import tempfile

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BumpType(Enum):
    """Version bump types."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"


class ChangeType(Enum):
    """Types of changes in commits."""
    BREAKING = "breaking"
    FEATURE = "feature"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    CHORE = "chore"
    REVERT = "revert"


@dataclass
class Version:
    """Represents a semantic version."""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    @classmethod
    def parse(cls, version_str: str) -> 'Version':
        """Parse version string."""
        # Remove 'v' prefix if present
        version_str = version_str.lstrip('v')

        # Split prerelease and build metadata
        parts = version_str.split('+', 1)
        version_part = parts[0]
        build = parts[1] if len(parts) > 1 else None

        # Split version and prerelease
        parts = version_part.split('-', 1)
        version_numbers = parts[0]
        prerelease = parts[1] if len(parts) > 1 else None

        # Parse version numbers
        numbers = version_numbers.split('.')
        if len(numbers) < 3:
            numbers.extend(['0'] * (3 - len(numbers)))

        return cls(
            major=int(numbers[0]),
            minor=int(numbers[1]),
            patch=int(numbers[2]),
            prerelease=prerelease,
            build=build
        )

    def bump(self, bump_type: BumpType) -> 'Version':
        """Bump version."""
        if bump_type == BumpType.MAJOR:
            return Version(self.major + 1, 0, 0)
        elif bump_type == BumpType.MINOR:
            return Version(self.major, self.minor + 1, 0)
        elif bump_type == BumpType.PATCH:
            return Version(self.major, self.minor, self.patch + 1)
        elif bump_type == BumpType.PRERELEASE:
            if self.prerelease:
                # Increment prerelease number
                match = re.match(r'([a-z]+)\.(\d+)', self.prerelease)
                if match:
                    prefix, number = match.groups()
                    return Version(
                        self.major, self.minor, self.patch,
                        f"{prefix}.{int(number) + 1}"
                    )
            # Start new prerelease
            return Version(self.major, self.minor, self.patch, "rc.1")
        else:
            raise ValueError(f"Unknown bump type: {bump_type}")

    def __str__(self) -> str:
        """String representation."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def to_tag(self) -> str:
        """Convert to git tag format."""
        return f"v{self}"


@dataclass
class Commit:
    """Represents a git commit."""
    hash: str
    short_hash: str
    subject: str
    body: str
    author: str
    date: str
    change_type: Optional[ChangeType] = None
    scope: Optional[str] = None
    breaking: bool = False

    @classmethod
    def parse(cls, commit_line: str, commit_details: Dict[str, str]) -> 'Commit':
        """Parse commit from git log output."""
        # Parse conventional commit format
        subject = commit_details.get('subject', '')
        body = commit_details.get('body', '')

        change_type = None
        scope = None
        breaking = False

        # Parse: type(scope): message or type: message
        match = re.match(r'^(\w+)(?:\(([^)]+)\))?: (.+)$', subject)
        if match:
            type_str, scope, message = match.groups()
            try:
                change_type = ChangeType(type_str.lower())
            except ValueError:
                change_type = ChangeType.CHORE

            # Check for breaking change
            if '!' in type_str or 'BREAKING CHANGE' in body:
                breaking = True
        else:
            # Non-conventional commit
            if 'fix' in subject.lower():
                change_type = ChangeType.FIX
            elif 'feat' in subject.lower() or 'add' in subject.lower():
                change_type = ChangeType.FEATURE
            else:
                change_type = ChangeType.CHORE

        return cls(
            hash=commit_details['hash'],
            short_hash=commit_details['short_hash'],
            subject=subject,
            body=body,
            author=commit_details['author'],
            date=commit_details['date'],
            change_type=change_type,
            scope=scope,
            breaking=breaking
        )


@dataclass
class ChangelogEntry:
    """Entry in changelog."""
    version: str
    date: str
    changes: Dict[ChangeType, List[Commit]]
    breaking_changes: List[Commit]

    def format_markdown(self) -> str:
        """Format as markdown."""
        lines = [f"## [{self.version}] - {self.date}\n"]

        # Breaking changes first
        if self.breaking_changes:
            lines.append("### ⚠ BREAKING CHANGES\n")
            for commit in self.breaking_changes:
                scope_str = f"**{commit.scope}**: " if commit.scope else ""
                lines.append(f"- {scope_str}{commit.subject} ({commit.short_hash})")
            lines.append("")

        # Features
        if ChangeType.FEATURE in self.changes:
            lines.append("### Features\n")
            for commit in self.changes[ChangeType.FEATURE]:
                scope_str = f"**{commit.scope}**: " if commit.scope else ""
                lines.append(f"- {scope_str}{commit.subject} ({commit.short_hash})")
            lines.append("")

        # Bug fixes
        if ChangeType.FIX in self.changes:
            lines.append("### Bug Fixes\n")
            for commit in self.changes[ChangeType.FIX]:
                scope_str = f"**{commit.scope}**: " if commit.scope else ""
                lines.append(f"- {scope_str}{commit.subject} ({commit.short_hash})")
            lines.append("")

        # Performance
        if ChangeType.PERF in self.changes:
            lines.append("### Performance\n")
            for commit in self.changes[ChangeType.PERF]:
                scope_str = f"**{commit.scope}**: " if commit.scope else ""
                lines.append(f"- {scope_str}{commit.subject} ({commit.short_hash})")
            lines.append("")

        # Documentation
        if ChangeType.DOCS in self.changes:
            lines.append("### Documentation\n")
            for commit in self.changes[ChangeType.DOCS]:
                scope_str = f"**{commit.scope}**: " if commit.scope else ""
                lines.append(f"- {scope_str}{commit.subject} ({commit.short_hash})")
            lines.append("")

        return "\n".join(lines)


@dataclass
class ReleaseConfig:
    """Configuration for release."""
    project_dir: Path
    version: Version
    changelog_path: Path
    dry_run: bool = False
    skip_tests: bool = False
    skip_build: bool = False
    skip_publish: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'project_dir': str(self.project_dir),
            'version': str(self.version),
            'changelog_path': str(self.changelog_path),
            'dry_run': self.dry_run,
            'skip_tests': self.skip_tests,
            'skip_build': self.skip_build,
            'skip_publish': self.skip_publish,
        }


@dataclass
class ReleaseResult:
    """Result of a release operation."""
    success: bool
    version: str
    tag: Optional[str] = None
    changelog_updated: bool = False
    tests_passed: bool = False
    wheels_built: List[str] = field(default_factory=list)
    published: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'version': self.version,
            'tag': self.tag,
            'changelog_updated': self.changelog_updated,
            'tests_passed': self.tests_passed,
            'wheels_built': self.wheels_built,
            'published': self.published,
            'errors': self.errors
        }


class GitOperations:
    """Git operations wrapper."""

    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir
        self.git_path = shutil.which('git')

        if not self.git_path:
            raise RuntimeError("git not found in PATH")

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run git command."""
        cmd = [self.git_path] + list(args)
        return subprocess.run(
            cmd,
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
            check=check
        )

    def get_current_version(self) -> Optional[Version]:
        """Get current version from latest tag."""
        try:
            result = self.run('describe', '--tags', '--abbrev=0', check=False)
            if result.returncode == 0:
                tag = result.stdout.strip()
                return Version.parse(tag)
        except Exception as e:
            logger.debug(f"Error getting version: {e}")

        return None

    def get_commits_since_tag(self, tag: Optional[str] = None) -> List[Commit]:
        """Get commits since tag."""
        commits = []

        if tag:
            rev_range = f"{tag}..HEAD"
        else:
            rev_range = "HEAD"

        try:
            # Get commit hashes
            result = self.run(
                'log', rev_range,
                '--format=%H',
                check=False
            )

            if result.returncode != 0:
                return commits

            hashes = result.stdout.strip().split('\n')

            # Get details for each commit
            for commit_hash in hashes:
                if not commit_hash:
                    continue

                details = self.get_commit_details(commit_hash)
                if details:
                    commit = Commit.parse(commit_hash, details)
                    commits.append(commit)

        except Exception as e:
            logger.error(f"Error getting commits: {e}")

        return commits

    def get_commit_details(self, commit_hash: str) -> Optional[Dict[str, str]]:
        """Get commit details."""
        try:
            result = self.run(
                'show', commit_hash,
                '--format=%H%n%h%n%s%n%b%n%an%n%ad',
                '--date=short',
                '-s',
                check=False
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 6:
                    return {
                        'hash': lines[0],
                        'short_hash': lines[1],
                        'subject': lines[2],
                        'body': '\n'.join(lines[3:-2]),
                        'author': lines[-2],
                        'date': lines[-1]
                    }

        except Exception as e:
            logger.debug(f"Error getting commit details: {e}")

        return None

    def create_tag(self, version: Version, message: str) -> bool:
        """Create annotated tag."""
        tag = version.to_tag()

        try:
            result = self.run(
                'tag', '-a', tag, '-m', message,
                check=False
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Error creating tag: {e}")
            return False

    def push_tag(self, version: Version) -> bool:
        """Push tag to remote."""
        tag = version.to_tag()

        try:
            result = self.run(
                'push', 'origin', tag,
                check=False
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Error pushing tag: {e}")
            return False

    def is_clean(self) -> bool:
        """Check if working directory is clean."""
        try:
            result = self.run('status', '--porcelain', check=False)
            return result.returncode == 0 and not result.stdout.strip()

        except Exception as e:
            logger.error(f"Error checking git status: {e}")
            return False

    def get_remote_url(self) -> Optional[str]:
        """Get remote URL."""
        try:
            result = self.run('remote', 'get-url', 'origin', check=False)
            if result.returncode == 0:
                return result.stdout.strip()

        except Exception as e:
            logger.debug(f"Error getting remote URL: {e}")

        return None


class VersionManager:
    """Manage version in project files."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.pyproject_path = project_dir / 'pyproject.toml'
        self.cargo_path = project_dir / 'Cargo.toml'

    def get_current_version(self) -> Optional[Version]:
        """Get current version from project files."""
        # Try pyproject.toml first
        if self.pyproject_path.exists():
            version = self._get_version_from_pyproject()
            if version:
                return version

        # Try Cargo.toml
        if self.cargo_path.exists():
            version = self._get_version_from_cargo()
            if version:
                return version

        return None

    def _get_version_from_pyproject(self) -> Optional[Version]:
        """Get version from pyproject.toml."""
        try:
            content = self.pyproject_path.read_text()
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return Version.parse(match.group(1))

        except Exception as e:
            logger.debug(f"Error reading pyproject.toml: {e}")

        return None

    def _get_version_from_cargo(self) -> Optional[Version]:
        """Get version from Cargo.toml."""
        try:
            content = self.cargo_path.read_text()
            # Only get version from [package] section
            match = re.search(r'\[package\].*?version\s*=\s*["\']([^"\']+)["\']', content, re.DOTALL)
            if match:
                version_str = match.group(1)
                # Skip if it's a placeholder
                if version_str != "0.0.0":
                    return Version.parse(version_str)

        except Exception as e:
            logger.debug(f"Error reading Cargo.toml: {e}")

        return None

    def update_version(self, version: Version) -> bool:
        """Update version in project files."""
        success = True

        if self.pyproject_path.exists():
            if not self._update_pyproject_version(version):
                success = False

        if self.cargo_path.exists():
            cargo_version = self._get_version_from_cargo()
            # Only update if Cargo.toml has a real version (not 0.0.0 placeholder)
            if cargo_version and cargo_version.major > 0:
                if not self._update_cargo_version(version):
                    success = False

        return success

    def _update_pyproject_version(self, version: Version) -> bool:
        """Update version in pyproject.toml."""
        try:
            content = self.pyproject_path.read_text()
            new_content = re.sub(
                r'(version\s*=\s*)["\'][^"\']+["\']',
                rf'\1"{version}"',
                content,
                count=1
            )

            self.pyproject_path.write_text(new_content)
            logger.info(f"Updated version in pyproject.toml to {version}")
            return True

        except Exception as e:
            logger.error(f"Error updating pyproject.toml: {e}")
            return False

    def _update_cargo_version(self, version: Version) -> bool:
        """Update version in Cargo.toml."""
        try:
            content = self.cargo_path.read_text()

            # Update version in [package] section only
            def replace_version(match):
                before = match.group(1)
                return f"{before}version = \"{version}\""

            new_content = re.sub(
                r'(\[package\].*?)(version\s*=\s*["\'][^"\']+["\'])',
                replace_version,
                content,
                count=1,
                flags=re.DOTALL
            )

            self.cargo_path.write_text(new_content)
            logger.info(f"Updated version in Cargo.toml to {version}")
            return True

        except Exception as e:
            logger.error(f"Error updating Cargo.toml: {e}")
            return False


class ChangelogGenerator:
    """Generate changelog from commits."""

    def __init__(self, changelog_path: Path):
        self.changelog_path = changelog_path

    def generate_entry(self, version: Version, commits: List[Commit]) -> ChangelogEntry:
        """Generate changelog entry from commits."""
        changes: Dict[ChangeType, List[Commit]] = {}
        breaking_changes: List[Commit] = []

        for commit in commits:
            if commit.breaking:
                breaking_changes.append(commit)

            if commit.change_type:
                changes.setdefault(commit.change_type, []).append(commit)

        return ChangelogEntry(
            version=str(version),
            date=datetime.now().strftime('%Y-%m-%d'),
            changes=changes,
            breaking_changes=breaking_changes
        )

    def update_changelog(self, entry: ChangelogEntry) -> bool:
        """Update CHANGELOG.md with new entry."""
        try:
            # Read existing changelog
            if self.changelog_path.exists():
                existing = self.changelog_path.read_text()
            else:
                existing = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"

            # Find position to insert (after header, before first version)
            lines = existing.split('\n')
            insert_pos = 0

            for i, line in enumerate(lines):
                if line.startswith('## ['):
                    insert_pos = i
                    break
            else:
                # No existing versions, insert after header
                insert_pos = len(lines)

            # Insert new entry
            new_entry = entry.format_markdown()
            lines.insert(insert_pos, new_entry)

            # Write back
            self.changelog_path.write_text('\n'.join(lines))
            logger.info(f"Updated {self.changelog_path}")
            return True

        except Exception as e:
            logger.error(f"Error updating changelog: {e}")
            return False


class ReleaseValidator:
    """Validate release readiness."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate release readiness."""
        errors = []

        # Check git status
        git = GitOperations(self.project_dir)
        if not git.is_clean():
            errors.append("Working directory has uncommitted changes")

        # Check for required files
        required_files = [
            'pyproject.toml',
            'Cargo.toml',
            'README.md',
            'LICENSE'
        ]

        for filename in required_files:
            if not (self.project_dir / filename).exists():
                errors.append(f"Missing required file: {filename}")

        # Check cargo check passes
        if shutil.which('cargo'):
            result = subprocess.run(
                ['cargo', 'check'],
                cwd=self.project_dir,
                capture_output=True,
                check=False
            )

            if result.returncode != 0:
                errors.append(f"cargo check failed: {result.stderr}")

        return len(errors) == 0, errors


class PyPIPublisher:
    """Publish to PyPI."""

    def __init__(self):
        self.twine_path = shutil.which('twine')
        self.maturin_path = shutil.which('maturin')

    def is_available(self) -> bool:
        """Check if publishing tools are available."""
        return self.twine_path is not None and self.maturin_path is not None

    def build_wheels(self, project_dir: Path) -> Tuple[bool, List[Path]]:
        """Build wheels for release."""
        wheels = []

        try:
            dist_dir = project_dir / 'dist'
            dist_dir.mkdir(exist_ok=True)

            result = subprocess.run(
                ['maturin', 'build', '--release', '--out', str(dist_dir)],
                cwd=project_dir,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                logger.error(f"Build failed: {result.stderr}")
                return False, wheels

            # Find built wheels
            wheels = list(dist_dir.glob('*.whl'))
            logger.info(f"Built {len(wheels)} wheels")

            return True, wheels

        except Exception as e:
            logger.error(f"Error building wheels: {e}")
            return False, wheels

    def publish(self, wheels: List[Path], repository: str = "pypi") -> bool:
        """Publish wheels to PyPI."""
        if not wheels:
            logger.error("No wheels to publish")
            return False

        try:
            cmd = ['twine', 'upload']

            if repository != "pypi":
                cmd.extend(['--repository', repository])

            cmd.extend([str(w) for w in wheels])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                logger.error(f"Publish failed: {result.stderr}")
                return False

            logger.info(f"Published {len(wheels)} wheels to {repository}")
            return True

        except Exception as e:
            logger.error(f"Error publishing: {e}")
            return False


class ReleaseManager:
    """Main release manager orchestrator."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.git = GitOperations(project_dir)
        self.version_manager = VersionManager(project_dir)
        self.changelog_generator = ChangelogGenerator(project_dir / 'CHANGELOG.md')
        self.validator = ReleaseValidator(project_dir)
        self.publisher = PyPIPublisher()

    def bump_version(self, bump_type: BumpType) -> Optional[Version]:
        """Bump version."""
        # Get current version
        current = self.version_manager.get_current_version()
        if not current:
            current = self.git.get_current_version()

        if not current:
            logger.error("Could not determine current version")
            return None

        # Bump version
        new_version = current.bump(bump_type)
        logger.info(f"Bumping version: {current} -> {new_version}")

        return new_version

    def prepare_release(self, version: Version, dry_run: bool = False) -> ReleaseResult:
        """Prepare release."""
        result = ReleaseResult(success=False, version=str(version))

        # Validate
        valid, errors = self.validator.validate()
        if not valid:
            result.errors.extend(errors)
            return result

        if dry_run:
            logger.info("Dry run mode - no changes will be made")

        # Get commits for changelog
        current_tag = self.git.get_current_version()
        tag_str = current_tag.to_tag() if current_tag else None
        commits = self.git.get_commits_since_tag(tag_str)

        # Generate changelog
        entry = self.changelog_generator.generate_entry(version, commits)
        if not dry_run:
            if self.changelog_generator.update_changelog(entry):
                result.changelog_updated = True
            else:
                result.errors.append("Failed to update changelog")
                return result

        # Update version
        if not dry_run:
            if not self.version_manager.update_version(version):
                result.errors.append("Failed to update version")
                return result

        result.success = True
        return result

    def create_release(self, config: ReleaseConfig) -> ReleaseResult:
        """Create complete release."""
        result = ReleaseResult(success=False, version=str(config.version))

        # Prepare
        prep_result = self.prepare_release(config.version, config.dry_run)
        result.changelog_updated = prep_result.changelog_updated

        if not prep_result.success:
            result.errors.extend(prep_result.errors)
            return result

        if config.dry_run:
            logger.info("Dry run complete - stopping before tag/publish")
            result.success = True
            return result

        # Create tag
        tag_message = f"Release {config.version}"
        if self.git.create_tag(config.version, tag_message):
            result.tag = config.version.to_tag()
            logger.info(f"Created tag: {result.tag}")
        else:
            result.errors.append("Failed to create tag")
            return result

        # Build wheels
        if not config.skip_build:
            success, wheels = self.publisher.build_wheels(config.project_dir)
            if success:
                result.wheels_built = [str(w) for w in wheels]
            else:
                result.errors.append("Failed to build wheels")
                return result

        # Publish
        if not config.skip_publish and result.wheels_built:
            wheels = [Path(w) for w in result.wheels_built]
            if self.publisher.publish(wheels):
                result.published = True
            else:
                result.errors.append("Failed to publish to PyPI")
                return result

        result.success = True
        return result


class ReportGenerator:
    """Generate reports."""

    @staticmethod
    def generate_text(result: ReleaseResult) -> str:
        """Generate text report."""
        lines = ["=== Release Report ===\n"]

        status = "SUCCESS" if result.success else "FAILED"
        lines.append(f"Status: {status}")
        lines.append(f"Version: {result.version}")

        if result.tag:
            lines.append(f"Tag: {result.tag}")

        if result.changelog_updated:
            lines.append("Changelog: Updated")

        if result.wheels_built:
            lines.append(f"\nWheels Built ({len(result.wheels_built)}):")
            for wheel in result.wheels_built:
                lines.append(f"  - {Path(wheel).name}")

        if result.published:
            lines.append("\nPublished: Yes")

        if result.errors:
            lines.append("\nErrors:")
            for error in result.errors:
                lines.append(f"  - {error}")

        return "\n".join(lines)

    @staticmethod
    def generate_json(result: ReleaseResult) -> str:
        """Generate JSON report."""
        return json.dumps(result.to_dict(), indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='PyO3 Release Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Bump patch version
  %(prog)s bump patch /path/to/project

  # Generate changelog
  %(prog)s changelog /path/to/project

  # Create git tag
  %(prog)s tag /path/to/project

  # Full release workflow
  %(prog)s release /path/to/project --bump minor

  # Dry run
  %(prog)s release /path/to/project --bump patch --dry-run

  # Validate release readiness
  %(prog)s validate /path/to/project
        """
    )

    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Bump command
    bump_parser = subparsers.add_parser('bump', help='Bump version')
    bump_parser.add_argument('type', type=str, choices=['major', 'minor', 'patch', 'prerelease'])
    bump_parser.add_argument('project', type=Path, help='Project directory')
    bump_parser.add_argument('--dry-run', action='store_true', help='Dry run')

    # Changelog command
    changelog_parser = subparsers.add_parser('changelog', help='Generate changelog')
    changelog_parser.add_argument('project', type=Path, help='Project directory')
    changelog_parser.add_argument('--version', type=str, help='Version for changelog')

    # Tag command
    tag_parser = subparsers.add_parser('tag', help='Create git tag')
    tag_parser.add_argument('project', type=Path, help='Project directory')
    tag_parser.add_argument('--version', type=str, required=True, help='Version to tag')
    tag_parser.add_argument('--push', action='store_true', help='Push tag to remote')

    # Release command
    release_parser = subparsers.add_parser('release', help='Full release workflow')
    release_parser.add_argument('project', type=Path, help='Project directory')
    release_parser.add_argument('--bump', type=str, choices=['major', 'minor', 'patch', 'prerelease'])
    release_parser.add_argument('--version', type=str, help='Explicit version')
    release_parser.add_argument('--dry-run', action='store_true', help='Dry run')
    release_parser.add_argument('--skip-tests', action='store_true', help='Skip tests')
    release_parser.add_argument('--skip-build', action='store_true', help='Skip building wheels')
    release_parser.add_argument('--skip-publish', action='store_true', help='Skip publishing')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate release readiness')
    validate_parser.add_argument('project', type=Path, help='Project directory')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.command == 'bump':
            manager = ReleaseManager(args.project)
            bump_type = BumpType(args.type)

            new_version = manager.bump_version(bump_type)
            if not new_version:
                sys.exit(1)

            if not args.dry_run:
                if manager.version_manager.update_version(new_version):
                    logger.info(f"Version bumped to {new_version}")
                else:
                    logger.error("Failed to update version")
                    sys.exit(1)
            else:
                logger.info(f"Would bump version to {new_version}")

        elif args.command == 'changelog':
            manager = ReleaseManager(args.project)

            # Get version
            if args.version:
                version = Version.parse(args.version)
            else:
                version = manager.version_manager.get_current_version()
                if not version:
                    logger.error("Could not determine version")
                    sys.exit(1)

            # Get commits
            current_tag = manager.git.get_current_version()
            tag_str = current_tag.to_tag() if current_tag else None
            commits = manager.git.get_commits_since_tag(tag_str)

            # Generate changelog
            entry = manager.changelog_generator.generate_entry(version, commits)

            if args.json:
                print(json.dumps({
                    'version': str(version),
                    'date': entry.date,
                    'changes': {
                        k.value: [{'hash': c.short_hash, 'subject': c.subject} for c in v]
                        for k, v in entry.changes.items()
                    }
                }, indent=2))
            else:
                print(entry.format_markdown())

        elif args.command == 'tag':
            manager = ReleaseManager(args.project)
            version = Version.parse(args.version)

            if manager.git.create_tag(version, f"Release {version}"):
                logger.info(f"Created tag {version.to_tag()}")

                if args.push:
                    if manager.git.push_tag(version):
                        logger.info(f"Pushed tag to remote")
                    else:
                        logger.error("Failed to push tag")
                        sys.exit(1)
            else:
                logger.error("Failed to create tag")
                sys.exit(1)

        elif args.command == 'release':
            manager = ReleaseManager(args.project)

            # Determine version
            if args.version:
                version = Version.parse(args.version)
            elif args.bump:
                version = manager.bump_version(BumpType(args.bump))
                if not version:
                    sys.exit(1)
            else:
                logger.error("Must specify --version or --bump")
                sys.exit(1)

            # Create release
            config = ReleaseConfig(
                project_dir=args.project,
                version=version,
                changelog_path=args.project / 'CHANGELOG.md',
                dry_run=args.dry_run,
                skip_tests=args.skip_tests,
                skip_build=args.skip_build,
                skip_publish=args.skip_publish
            )

            result = manager.create_release(config)

            report_gen = ReportGenerator()
            if args.json:
                print(report_gen.generate_json(result))
            else:
                print(report_gen.generate_text(result))

            sys.exit(0 if result.success else 1)

        elif args.command == 'validate':
            validator = ReleaseValidator(args.project)
            valid, errors = validator.validate()

            if args.json:
                print(json.dumps({
                    'valid': valid,
                    'errors': errors
                }, indent=2))
            else:
                if valid:
                    print("Release validation: PASS")
                else:
                    print("Release validation: FAIL\n")
                    print("Errors:")
                    for error in errors:
                        print(f"  - {error}")

            sys.exit(0 if valid else 1)

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
