#!/usr/bin/env python3
"""
Analyze Dockerfile for anti-patterns and optimization opportunities.

Detects common issues:
- Root user execution
- Latest tag usage
- Missing .dockerignore
- Inefficient layer structure
- Security vulnerabilities
- Size optimization opportunities
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any


@dataclass
class Issue:
    """Represents a Dockerfile issue."""
    severity: str  # critical, high, medium, low
    category: str
    line: int
    instruction: str
    message: str
    recommendation: str


@dataclass
class Analysis:
    """Results of Dockerfile analysis."""
    file: str
    issues: List[Issue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    score: int = 100


class DockerfileAnalyzer:
    """Analyzes Dockerfiles for anti-patterns and optimization opportunities."""

    def __init__(self, dockerfile_path: Path):
        self.path = dockerfile_path
        self.lines = []
        self.analysis = Analysis(file=str(dockerfile_path))

    def load(self) -> None:
        """Load Dockerfile contents."""
        if not self.path.exists():
            raise FileNotFoundError(f"Dockerfile not found: {self.path}")

        self.lines = self.path.read_text().splitlines()

    def analyze(self) -> Analysis:
        """Run all analysis checks."""
        self.load()

        # Run checks
        self._check_base_image()
        self._check_user()
        self._check_layer_efficiency()
        self._check_security()
        self._check_size_optimization()
        self._check_build_optimization()
        self._check_best_practices()
        self._check_dockerignore()

        # Calculate stats
        self._calculate_stats()

        # Calculate score
        self._calculate_score()

        return self.analysis

    def _check_base_image(self) -> None:
        """Check base image usage."""
        for i, line in enumerate(self.lines, 1):
            if not line.strip() or line.strip().startswith('#'):
                continue

            if line.strip().upper().startswith('FROM'):
                # Check for 'latest' tag
                if ':latest' in line or (
                    'FROM' in line and ':' not in line.split()[1]
                ):
                    self.analysis.issues.append(Issue(
                        severity='high',
                        category='base_image',
                        line=i,
                        instruction=line.strip(),
                        message='Using :latest tag or no tag specified',
                        recommendation='Pin to specific version: FROM python:3.11.7-slim'
                    ))

                # Check for bloated base images
                image = line.split()[1].lower()
                if any(x in image for x in ['ubuntu:', 'debian:', 'centos:']) and \
                   'slim' not in image and 'alpine' not in image:
                    self.analysis.issues.append(Issue(
                        severity='medium',
                        category='base_image',
                        line=i,
                        instruction=line.strip(),
                        message='Using full base image instead of slim/alpine variant',
                        recommendation='Consider slim or alpine variant for smaller size'
                    ))

    def _check_user(self) -> None:
        """Check for non-root user usage."""
        has_user_instruction = False

        for i, line in enumerate(self.lines, 1):
            if line.strip().upper().startswith('USER'):
                has_user_instruction = True
                user = line.split()[1] if len(line.split()) > 1 else ''
                if user in ['root', '0']:
                    self.analysis.issues.append(Issue(
                        severity='critical',
                        category='security',
                        line=i,
                        instruction=line.strip(),
                        message='Explicitly setting USER to root',
                        recommendation='Use non-root user: USER appuser or USER 1000'
                    ))

        if not has_user_instruction:
            self.analysis.issues.append(Issue(
                severity='high',
                category='security',
                line=0,
                instruction='N/A',
                message='No USER instruction found - container runs as root',
                recommendation='Add: RUN useradd -r -u 1000 appuser && USER appuser'
            ))

    def _check_layer_efficiency(self) -> None:
        """Check for inefficient layer structure."""
        run_commands = []

        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped.upper().startswith('RUN'):
                run_commands.append((i, stripped))

        # Check for multiple consecutive RUN commands that could be combined
        if len(run_commands) > 3:
            consecutive_runs = []
            for i in range(len(run_commands) - 1):
                curr_line, _ = run_commands[i]
                next_line, _ = run_commands[i + 1]
                if next_line - curr_line < 3:  # Close together
                    consecutive_runs.append(curr_line)

            if len(consecutive_runs) >= 2:
                self.analysis.issues.append(Issue(
                    severity='medium',
                    category='layers',
                    line=consecutive_runs[0],
                    instruction='Multiple RUN commands',
                    message=f'Found {len(consecutive_runs)} consecutive RUN commands',
                    recommendation='Combine related RUN commands with && to reduce layers'
                ))

    def _check_security(self) -> None:
        """Check for security issues."""
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip().upper()

            # Check for secrets in environment variables
            if stripped.startswith('ENV') and any(
                secret in line.upper()
                for secret in ['PASSWORD', 'SECRET', 'TOKEN', 'KEY', 'CREDENTIAL']
            ):
                if '=' in line:
                    self.analysis.issues.append(Issue(
                        severity='critical',
                        category='security',
                        line=i,
                        instruction=line.strip(),
                        message='Potential secret in ENV instruction',
                        recommendation='Use secrets management or runtime environment variables'
                    ))

            # Check for ADD with URLs (security risk)
            if stripped.startswith('ADD') and ('http://' in line or 'https://' in line):
                self.analysis.issues.append(Issue(
                    severity='medium',
                    category='security',
                    line=i,
                    instruction=line.strip(),
                    message='ADD with URL - potential security risk',
                    recommendation='Use curl/wget with checksum verification instead'
                ))

            # Check for curl/wget without verification
            if 'curl' in line.lower() or 'wget' in line.lower():
                if 'http://' in line.lower() and 'sha' not in line.lower():
                    self.analysis.issues.append(Issue(
                        severity='medium',
                        category='security',
                        line=i,
                        instruction=line.strip(),
                        message='Downloading without checksum verification',
                        recommendation='Add checksum verification for downloads'
                    ))

    def _check_size_optimization(self) -> None:
        """Check for size optimization opportunities."""
        has_cache_cleanup = False

        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()

            # Check for package manager without cleanup
            if 'apt-get install' in line and 'rm -rf /var/lib/apt/lists/*' not in line:
                # Check if cleanup is in same RUN command
                if not self._is_multiline_command_with_cleanup(i, 'rm -rf /var/lib/apt/lists/*'):
                    self.analysis.issues.append(Issue(
                        severity='medium',
                        category='size',
                        line=i,
                        instruction=line.strip(),
                        message='apt-get install without cleanup',
                        recommendation='Add: && rm -rf /var/lib/apt/lists/* in same RUN'
                    ))

            if 'apk add' in line and '--no-cache' not in line:
                self.analysis.issues.append(Issue(
                    severity='medium',
                    category='size',
                    line=i,
                    instruction=line.strip(),
                    message='apk add without --no-cache flag',
                    recommendation='Use: apk add --no-cache package'
                ))

            if 'pip install' in line and '--no-cache-dir' not in line:
                self.analysis.issues.append(Issue(
                    severity='low',
                    category='size',
                    line=i,
                    instruction=line.strip(),
                    message='pip install without --no-cache-dir',
                    recommendation='Use: pip install --no-cache-dir package'
                ))

            if 'npm install' in line and 'npm cache clean' not in line:
                if not self._is_multiline_command_with_cleanup(i, 'npm cache clean'):
                    self.analysis.issues.append(Issue(
                        severity='low',
                        category='size',
                        line=i,
                        instruction=line.strip(),
                        message='npm install without cache cleanup',
                        recommendation='Add: && npm cache clean --force'
                    ))

    def _check_build_optimization(self) -> None:
        """Check for build time optimization opportunities."""
        has_copy_before_install = False
        copy_line = 0
        install_line = 0

        for i, line in enumerate(self.lines, 1):
            stripped = line.strip().upper()

            # Check for COPY . before installing dependencies
            if stripped.startswith('COPY') and ' . ' in line:
                copy_line = i

            if any(cmd in line for cmd in ['pip install', 'npm install', 'go mod download']):
                if copy_line > 0 and install_line == 0:
                    install_line = i
                    if copy_line < install_line:
                        self.analysis.issues.append(Issue(
                            severity='high',
                            category='caching',
                            line=copy_line,
                            instruction=self.lines[copy_line - 1].strip(),
                            message='COPY . before dependency install - invalidates cache',
                            recommendation='Copy dependency files first, install, then COPY .'
                        ))

    def _check_best_practices(self) -> None:
        """Check for general best practices."""
        has_healthcheck = False
        has_multistage = False
        from_count = 0

        for i, line in enumerate(self.lines, 1):
            stripped = line.strip().upper()

            if stripped.startswith('HEALTHCHECK'):
                has_healthcheck = True

            if stripped.startswith('FROM'):
                from_count += 1

            # Check for shell form vs exec form
            if stripped.startswith('CMD') or stripped.startswith('ENTRYPOINT'):
                if '[' not in line:
                    self.analysis.issues.append(Issue(
                        severity='medium',
                        category='best_practice',
                        line=i,
                        instruction=line.strip(),
                        message='Using shell form instead of exec form',
                        recommendation='Use exec form: CMD ["python", "app.py"]'
                    ))

            # Check for ADD when COPY should be used
            if stripped.startswith('ADD'):
                if not ('http://' in line or 'https://' in line or '.tar' in line):
                    self.analysis.issues.append(Issue(
                        severity='low',
                        category='best_practice',
                        line=i,
                        instruction=line.strip(),
                        message='Using ADD when COPY would be better',
                        recommendation='Use COPY instead of ADD for simple file copies'
                    ))

        if from_count > 1:
            has_multistage = True

        if not has_healthcheck:
            self.analysis.issues.append(Issue(
                severity='low',
                category='best_practice',
                line=0,
                instruction='N/A',
                message='No HEALTHCHECK instruction',
                recommendation='Add HEALTHCHECK for container health monitoring'
            ))

        if not has_multistage and from_count == 1:
            self.analysis.issues.append(Issue(
                severity='low',
                category='best_practice',
                line=0,
                instruction='N/A',
                message='Not using multi-stage build',
                recommendation='Consider multi-stage build for smaller images'
            ))

    def _check_dockerignore(self) -> None:
        """Check for .dockerignore file."""
        dockerignore = self.path.parent / '.dockerignore'
        if not dockerignore.exists():
            self.analysis.issues.append(Issue(
                severity='medium',
                category='best_practice',
                line=0,
                instruction='N/A',
                message='No .dockerignore file found',
                recommendation='Create .dockerignore to exclude unnecessary files'
            ))

    def _is_multiline_command_with_cleanup(self, start_line: int, cleanup_text: str) -> bool:
        """Check if a RUN command is multiline and contains cleanup."""
        # Look ahead for continuation lines
        for i in range(start_line - 1, min(start_line + 10, len(self.lines))):
            if cleanup_text in self.lines[i]:
                return True
            if i > start_line - 1 and not self.lines[i].strip().endswith('\\'):
                break
        return False

    def _calculate_stats(self) -> None:
        """Calculate statistics about the Dockerfile."""
        total_lines = len(self.lines)
        instruction_lines = sum(
            1 for line in self.lines
            if line.strip() and not line.strip().startswith('#')
        )

        instructions = {}
        for line in self.lines:
            stripped = line.strip().upper()
            if stripped and not stripped.startswith('#'):
                cmd = stripped.split()[0]
                instructions[cmd] = instructions.get(cmd, 0) + 1

        severity_counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        for issue in self.analysis.issues:
            severity_counts[issue.severity] += 1

        self.analysis.stats = {
            'total_lines': total_lines,
            'instruction_lines': instruction_lines,
            'instructions': instructions,
            'issues_by_severity': severity_counts,
            'total_issues': len(self.analysis.issues)
        }

    def _calculate_score(self) -> None:
        """Calculate overall score (0-100)."""
        score = 100

        severity_penalties = {
            'critical': 20,
            'high': 10,
            'medium': 5,
            'low': 2
        }

        for issue in self.analysis.issues:
            score -= severity_penalties.get(issue.severity, 0)

        self.analysis.score = max(0, score)


def format_text_output(analysis: Analysis) -> str:
    """Format analysis as human-readable text."""
    lines = []
    lines.append(f"\nDockerfile Analysis: {analysis.file}")
    lines.append("=" * 80)
    lines.append(f"\nOverall Score: {analysis.score}/100")

    if analysis.score >= 90:
        lines.append("Grade: A (Excellent)")
    elif analysis.score >= 80:
        lines.append("Grade: B (Good)")
    elif analysis.score >= 70:
        lines.append("Grade: C (Fair)")
    elif analysis.score >= 60:
        lines.append("Grade: D (Poor)")
    else:
        lines.append("Grade: F (Needs Improvement)")

    lines.append("\nStatistics:")
    lines.append(f"  Total lines: {analysis.stats['total_lines']}")
    lines.append(f"  Instruction lines: {analysis.stats['instruction_lines']}")
    lines.append(f"  Total issues: {analysis.stats['total_issues']}")

    lines.append("\nIssues by Severity:")
    for severity in ['critical', 'high', 'medium', 'low']:
        count = analysis.stats['issues_by_severity'][severity]
        if count > 0:
            lines.append(f"  {severity.upper()}: {count}")

    if analysis.issues:
        lines.append("\nIssues Found:")
        lines.append("-" * 80)

        for issue in sorted(analysis.issues, key=lambda x:
                           ['critical', 'high', 'medium', 'low'].index(x.severity)):
            lines.append(f"\n[{issue.severity.upper()}] Line {issue.line}: {issue.category}")
            lines.append(f"  Issue: {issue.message}")
            lines.append(f"  Instruction: {issue.instruction}")
            lines.append(f"  Recommendation: {issue.recommendation}")
    else:
        lines.append("\nNo issues found! Great job!")

    lines.append("\n")
    return "\n".join(lines)


def format_json_output(analysis: Analysis) -> str:
    """Format analysis as JSON."""
    data = {
        'file': analysis.file,
        'score': analysis.score,
        'stats': analysis.stats,
        'issues': [
            {
                'severity': issue.severity,
                'category': issue.category,
                'line': issue.line,
                'instruction': issue.instruction,
                'message': issue.message,
                'recommendation': issue.recommendation
            }
            for issue in analysis.issues
        ]
    }
    return json.dumps(data, indent=2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze Dockerfile for anti-patterns and optimization opportunities'
    )
    parser.add_argument(
        'dockerfile',
        nargs='?',
        default='Dockerfile',
        help='Path to Dockerfile (default: ./Dockerfile)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )
    parser.add_argument(
        '--min-score',
        type=int,
        default=0,
        help='Minimum score required (exits with code 1 if below)'
    )

    args = parser.parse_args()

    try:
        analyzer = DockerfileAnalyzer(Path(args.dockerfile))
        analysis = analyzer.analyze()

        if args.json:
            print(format_json_output(analysis))
        else:
            print(format_text_output(analysis))

        # Exit with error code if score is below minimum
        if analysis.score < args.min_score:
            sys.exit(1)

        # Exit with error code if critical issues found
        if any(issue.severity == 'critical' for issue in analysis.issues):
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error analyzing Dockerfile: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
