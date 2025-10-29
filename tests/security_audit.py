#!/usr/bin/env python3
"""
Security Audit Script for cc-polymath Skills Library

Scans all skills, scripts, and examples for security vulnerabilities and
safety issues. Produces a comprehensive report with findings categorized
by severity.

Detection Categories:
    - Dangerous Commands: rm -rf, DROP TABLE, destructive operations
    - Command Injection: eval(), shell=True, os.system()
    - Hardcoded Secrets: API keys, passwords, tokens, private keys
    - Cloud Credentials: AWS keys, GitHub tokens, OAuth tokens, JWT
    - Network Security: Insecure HTTP, pipe to shell
    - SQL Injection: String formatting in queries
    - Path Traversal: Directory traversal patterns
    - Unsafe File Operations: chmod 777, unsafe ownership changes
    - Rate Limiting / DoS: Infinite loops, unbounded operations, missing timeouts
    - Input Validation: Unvalidated user input, request parameters
    - Insecure Defaults: Disabled HTTPS verification, weak crypto, debug mode
    - Unsafe Deserialization: pickle, unsafe YAML load
    - Timing Attacks: Non-constant-time secret comparison

Usage:
    python tests/security_audit.py [--output report.json] [--verbose]
    python tests/security_audit.py --path skills/specific/skill.md
    python tests/security_audit.py --fail-on high
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
from datetime import datetime


@dataclass
class Finding:
    """Security finding with severity and details."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str
    file: str
    line_number: int
    issue: str
    evidence: str
    recommendation: str


class SecurityAuditor:
    """Main security auditor class."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.findings: List[Finding] = []
        self.stats = {
            'files_scanned': 0,
            'scripts_scanned': 0,
            'lines_scanned': 0,
            'findings_by_severity': defaultdict(int)
        }

        # Dangerous command patterns
        self.dangerous_commands = {
            r'\brm\s+-rf\b': ('CRITICAL', 'Destructive file deletion',
                            'Use safer alternatives or require explicit confirmation'),
            r'\bgit\s+reset\s+--hard\b': ('HIGH', 'Destructive git operation',
                                         'Warn about data loss and require confirmation'),
            r'\bDROP\s+TABLE\b': ('HIGH', 'Destructive database operation',
                                 'Require backup and confirmation before execution'),
            r'\bTRUNCATE\b': ('HIGH', 'Destructive database operation',
                             'Require backup and confirmation'),
            r'\bDELETE\s+FROM\b.*without\s+WHERE': ('HIGH', 'Unqualified DELETE',
                                                    'Add WHERE clause or require confirmation'),
            r'\bsudo\s+': ('MEDIUM', 'Privilege escalation',
                          'Document why sudo is needed and alternatives'),
            r'--force(?!\-rebuild)': ('MEDIUM', 'Force flag usage',
                                     'Ensure user understands consequences'),
        }

        # Command injection patterns
        self.injection_patterns = {
            r'\beval\s*\(': ('CRITICAL', 'eval() usage',
                          'Never use eval() with user input'),
            # exec() in Python or require('child_process').exec() in JS/TS
            # BUT NOT regex.exec() in JavaScript
            r'(?:child_process|subprocess)\.exec\s*\(': ('HIGH', 'process exec() usage',
                           'Avoid shell execution or strictly validate input'),
            # Python's exec() builtin (not in comments or strings)
            r'^\s*exec\s*\(': ('HIGH', 'Python exec() usage',
                           'Avoid exec() or strictly validate input'),
            r'shell\s*=\s*True': ('HIGH', 'shell=True in subprocess',
                                 'Use shell=False and pass command as list'),
            r'os\.system\s*\(': ('HIGH', 'os.system() usage',
                               'Use subprocess with proper escaping'),
            r'\$\([^)]*\)': ('MEDIUM', 'Command substitution in shell',
                           'Validate and sanitize all inputs'),
            r'`[^`]+`': ('MEDIUM', 'Backtick command execution',
                        'Use $() syntax and validate inputs'),
        }

        # Hardcoded secrets patterns (excluding obvious test patterns)
        self.secrets_patterns = {
            r'(?i)api[_-]?key\s*[:=]\s*["\'](?!test|fake|example|YOUR_|placeholder|xxx|<)[A-Za-z0-9+/]{20,}':
                ('CRITICAL', 'Possible hardcoded API key', 'Use environment variables or secret management'),
            r'(?i)password\s*[:=]\s*["\'](?!test|fake|example|pass|password|YOUR_|placeholder|xxx|<)[^\'"]{8,}':
                ('HIGH', 'Possible hardcoded password', 'Use environment variables or secret management'),
            r'(?i)secret\s*[:=]\s*["\'](?!test|fake|example|YOUR_|placeholder|xxx|<)[A-Za-z0-9+/]{20,}':
                ('HIGH', 'Possible hardcoded secret', 'Use environment variables or secret management'),
            r'(?i)token\s*[:=]\s*["\'](?!test|fake|example|YOUR_|placeholder|xxx|<)[A-Za-z0-9._\-]{20,}':
                ('HIGH', 'Possible hardcoded token', 'Use environment variables or secret management'),
            r'(?i)-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----':
                ('CRITICAL', 'Private key in file', 'Never commit private keys'),
        }

        # Cloud credentials patterns
        # Note: These patterns exclude common example/test values
        self.cloud_credentials_patterns = {
            r'(?<![A-Za-z0-9])AKIA(?!IOSFODNN7EXAMPLE)[0-9A-Z]{16}(?![A-Za-z0-9])':
                ('CRITICAL', 'AWS Access Key ID detected', 'Remove immediately and rotate credentials'),
            r'(?<![A-Za-z0-9])ASIA(?!IOSFODNN7EXAMPLE)[0-9A-Z]{16}(?![A-Za-z0-9])':
                ('CRITICAL', 'AWS Session Token detected', 'Remove immediately and rotate credentials'),
            r'ghp_(?!1234567890123456789012345678901234)[A-Za-z0-9]{36}':
                ('CRITICAL', 'GitHub Personal Access Token detected', 'Remove immediately and rotate token'),
            r'gho_[A-Za-z0-9]{36}':
                ('CRITICAL', 'GitHub OAuth Token detected', 'Remove immediately and rotate token'),
            r'ghs_[A-Za-z0-9]{36}':
                ('CRITICAL', 'GitHub App Token detected', 'Remove immediately and rotate token'),
            r'ghr_[A-Za-z0-9]{36}':
                ('CRITICAL', 'GitHub Refresh Token detected', 'Remove immediately and rotate token'),
        }

        # Insecure network patterns
        self.network_patterns = {
            r'curl\s+[^|]*\|\s*(?:bash|sh)': ('CRITICAL', 'Pipe curl to shell',
                                              'Download, verify, then execute'),
            r'wget\s+[^|]*\|\s*(?:bash|sh)': ('CRITICAL', 'Pipe wget to shell',
                                              'Download, verify, then execute'),
            r'(?<!https:)http://(?!localhost|127\.0\.0\.1|example\.com)':
                ('MEDIUM', 'Unencrypted HTTP', 'Use HTTPS for external resources'),
        }

        # SQL injection patterns
        self.sql_injection_patterns = {
            r'(?:execute|cursor\.execute|query)\s*\(\s*[\'"].*?%s.*?[\'"].*?%':
                ('HIGH', 'Possible SQL injection via string formatting',
                 'Use parameterized queries'),
            r'(?:execute|cursor\.execute|query)\s*\(\s*f[\'"]':
                ('HIGH', 'Possible SQL injection via f-string',
                 'Use parameterized queries'),
            r'(?:execute|cursor\.execute|query)\s*\(\s*.*?\+\s*':
                ('HIGH', 'Possible SQL injection via string concatenation',
                 'Use parameterized queries'),
        }

        # Path traversal patterns
        self.path_traversal_patterns = {
            r'\.\.[\\/]': ('MEDIUM', 'Path traversal pattern',
                         'Validate and sanitize file paths'),
            r'open\s*\([^)]*user': ('MEDIUM', 'User-controlled file path',
                                   'Validate path is within allowed directory'),
        }

        # Unsafe file operations
        self.unsafe_file_ops = {
            r'chmod\s+777': ('HIGH', 'Overly permissive file permissions',
                           'Use minimum required permissions'),
            r'chown\s+.*:.*\s+/': ('MEDIUM', 'Ownership change on root paths',
                                  'Ensure path is specific and validated'),
        }

        # Rate limiting and DoS prevention patterns
        self.rate_limiting_patterns = {
            r'while\s+True\s*:(?!\s*\n.*(?:sleep|time\.sleep|await\s+asyncio\.sleep|break))':
                ('HIGH', 'Infinite loop without sleep/break', 'Add rate limiting or sleep to prevent CPU exhaustion'),
            r'for\s+.*\s+in\s+range\s*\(\s*(?:9999999|999999999|[0-9]{8,})\s*\)':
                ('MEDIUM', 'Unbounded loop with large range', 'Consider adding limits or pagination'),
            r'requests\.\w+\s*\([^)]*(?!timeout)':
                ('MEDIUM', 'HTTP request without timeout', 'Add timeout parameter to prevent hanging'),
            r'urllib\.request\.urlopen\s*\([^)]*(?!timeout)':
                ('MEDIUM', 'URL request without timeout', 'Add timeout parameter to prevent hanging'),
            r'(?:aiohttp|httpx)\.\w+\s*\([^)]*(?!timeout)':
                ('MEDIUM', 'Async HTTP request without timeout', 'Add timeout parameter'),
        }

        # Input validation patterns
        self.input_validation_patterns = {
            r'input\s*\([^)]*\)(?!\s*\n.*(?:validate|sanitize|strip|clean|int\(|float\())':
                ('MEDIUM', 'Unvalidated user input', 'Validate and sanitize all user inputs'),
            r'request\.args\.get\s*\([^)]*\)(?!\s*\n.*(?:validate|sanitize|int\(|float\())':
                ('MEDIUM', 'Unvalidated Flask request parameter', 'Validate request parameters'),
            r'request\.form\.get\s*\([^)]*\)(?!\s*\n.*(?:validate|sanitize))':
                ('MEDIUM', 'Unvalidated Flask form data', 'Validate form inputs'),
            r'req\.query\.\w+(?!\s*\n.*(?:validate|sanitize|parseInt))':
                ('MEDIUM', 'Unvalidated query parameter', 'Validate query parameters'),
        }

        # Secure defaults patterns
        self.secure_defaults_patterns = {
            r'(?:requests\.(?:get|post|put|delete|patch))\s*\([^)]*verify\s*=\s*False':
                ('CRITICAL', 'HTTPS verification disabled', 'Never disable SSL verification in production'),
            r'ssl\._create_unverified_context':
                ('CRITICAL', 'SSL verification bypassed', 'Use verified SSL contexts'),
            r'(?i)(?:md5|sha1)\s*\(.*(?:password|secret|token|key)':
                ('HIGH', 'Weak cryptographic algorithm for security', 'Use SHA-256 or better for security purposes'),
            r'hashlib\.(?:md5|sha1)\s*\(':
                ('MEDIUM', 'Weak hash algorithm', 'Consider SHA-256 or SHA-3 for security purposes'),
            r'(?i)(?:password|passwd|pwd)\s*[:=]\s*["\'](?:admin|password|pass|123456|default)':
                ('CRITICAL', 'Default/weak password', 'Never use default or weak passwords'),
            r'(?i)debug\s*[:=]\s*True(?!.*test)':
                ('HIGH', 'Debug mode enabled', 'Disable debug mode in production'),
            r'app\.run\s*\([^)]*debug\s*=\s*True':
                ('HIGH', 'Flask debug mode in code', 'Use environment variables for debug flag'),
            r'DEBUG\s*=\s*True':
                ('MEDIUM', 'Debug flag set to True', 'Ensure debug is disabled in production'),
        }

        # Unsafe deserialization patterns
        self.unsafe_deserialization_patterns = {
            r'pickle\.loads?\s*\(':
                ('HIGH', 'Unsafe pickle deserialization', 'Use JSON or validate pickle data source'),
            r'yaml\.load\s*\((?![^)]*Loader\s*=\s*yaml\.SafeLoader)':
                ('HIGH', 'Unsafe YAML deserialization', 'Use yaml.safe_load() instead'),
            r'yaml\.unsafe_load\s*\(':
                ('CRITICAL', 'Explicitly unsafe YAML load', 'Use yaml.safe_load() instead'),
            r'json\.loads?\s*\([^)]*\)(?!\s*\n.*(?:validate|schema|isinstance))':
                ('LOW', 'JSON deserialization without validation', 'Validate JSON structure and types'),
            r'marshal\.loads?\s*\(':
                ('HIGH', 'Unsafe marshal deserialization', 'Use JSON or validate data source'),
        }

        # Timing attack patterns
        self.timing_attack_patterns = {
            r'(?:password|secret|token|key|hash)\s*==\s*(?:password|secret|token|key|hash)':
                ('MEDIUM', 'String comparison for secrets', 'Use hmac.compare_digest() for constant-time comparison'),
            r'if\s+[^=]*(?:password|secret|token|key)\s*==\s*["\']':
                ('MEDIUM', 'Direct string comparison of secret', 'Use constant-time comparison function'),
        }

    def scan_file(self, file_path: Path) -> None:
        """Scan a single file for security issues."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')

            self.stats['files_scanned'] += 1
            self.stats['lines_scanned'] += len(lines)

            # Determine if this is a script
            is_script = file_path.suffix in {'.py', '.sh', '.js', '.ts', '.bash'}
            if is_script:
                self.stats['scripts_scanned'] += 1

            # Scan each line
            for line_num, line in enumerate(lines, 1):
                self._scan_line(file_path, line_num, line, is_script, content)

        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not scan {file_path}: {e}", file=sys.stderr)

    def _scan_line(self, file_path: Path, line_num: int, line: str,
                   is_script: bool, full_content: str) -> None:
        """Scan a single line for security issues."""

        # Skip comments in most cases (but not for secrets)
        is_comment = line.strip().startswith('#') or line.strip().startswith('//')

        # Dangerous commands
        if not is_comment:
            for pattern, (severity, issue, recommendation) in self.dangerous_commands.items():
                if re.search(pattern, line, re.IGNORECASE):
                    self._add_finding(severity, 'Dangerous Command', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Command injection (scripts only)
        if is_script:
            for pattern, (severity, issue, recommendation) in self.injection_patterns.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'Command Injection Risk', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Hardcoded secrets (scan all files, including comments)
        for pattern, (severity, issue, recommendation) in self.secrets_patterns.items():
            match = re.search(pattern, line)
            if match:
                # Additional validation: check if it's clearly a test value
                matched_value = match.group(0)
                if not self._is_test_credential(matched_value, file_path):
                    self._add_finding(severity, 'Hardcoded Secret', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Cloud credentials (scan all files, including comments)
        for pattern, (severity, issue, recommendation) in self.cloud_credentials_patterns.items():
            if re.search(pattern, line):
                self._add_finding(severity, 'Cloud Credentials', file_path,
                                line_num, issue, line.strip(), recommendation)

        # Network security
        if not is_comment:
            for pattern, (severity, issue, recommendation) in self.network_patterns.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'Network Security', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # SQL injection (scripts only)
        if is_script:
            for pattern, (severity, issue, recommendation) in self.sql_injection_patterns.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'SQL Injection Risk', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Path traversal
        for pattern, (severity, issue, recommendation) in self.path_traversal_patterns.items():
            if re.search(pattern, line):
                self._add_finding(severity, 'Path Traversal Risk', file_path,
                                line_num, issue, line.strip(), recommendation)

        # Unsafe file operations
        if is_script:
            for pattern, (severity, issue, recommendation) in self.unsafe_file_ops.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'Unsafe File Operation', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Rate limiting and DoS prevention (scripts only)
        if is_script and not is_comment:
            for pattern, (severity, issue, recommendation) in self.rate_limiting_patterns.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'Rate Limiting / DoS', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Input validation (scripts only)
        if is_script and not is_comment:
            for pattern, (severity, issue, recommendation) in self.input_validation_patterns.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'Input Validation', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Secure defaults (scripts only)
        if is_script:
            for pattern, (severity, issue, recommendation) in self.secure_defaults_patterns.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'Insecure Defaults', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Unsafe deserialization (scripts only)
        if is_script and not is_comment:
            for pattern, (severity, issue, recommendation) in self.unsafe_deserialization_patterns.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'Unsafe Deserialization', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Timing attacks (scripts only)
        if is_script and not is_comment:
            for pattern, (severity, issue, recommendation) in self.timing_attack_patterns.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'Timing Attack Risk', file_path,
                                    line_num, issue, line.strip(), recommendation)

    def _is_test_credential(self, value: str, file_path: Path) -> bool:
        """Check if a credential is clearly a test/example value."""
        test_indicators = [
            'test', 'fake', 'example', 'placeholder', 'YOUR_',
            'xxx', 'yyy', '<', '>', 'TODO', 'CHANGEME',
            'demo', 'sample', 'dummy'
        ]

        # Check if it's in a test/example file
        path_str = str(file_path).lower()
        if any(x in path_str for x in ['test', 'example', 'demo', 'fixture']):
            return True

        # Check the value itself
        value_lower = value.lower()
        return any(indicator in value_lower for indicator in test_indicators)

    def _add_finding(self, severity: str, category: str, file_path: Path,
                     line_num: int, issue: str, evidence: str,
                     recommendation: str) -> None:
        """Add a finding to the results."""
        finding = Finding(
            severity=severity,
            category=category,
            file=str(file_path),
            line_number=line_num,
            issue=issue,
            evidence=evidence[:200],  # Limit evidence length
            recommendation=recommendation
        )
        self.findings.append(finding)
        self.stats['findings_by_severity'][severity] += 1

    def scan_directory(self, directory: Path, patterns: List[str] = None) -> None:
        """Scan a directory recursively."""
        if patterns is None:
            patterns = ['**/*.md', '**/*.py', '**/*.sh', '**/*.js', '**/*.ts']

        for pattern in patterns:
            for file_path in directory.glob(pattern):
                # Skip certain directories
                if any(x in file_path.parts for x in ['.git', 'node_modules', '__pycache__', '.venv']):
                    continue

                if file_path.is_file():
                    if self.verbose:
                        print(f"Scanning: {file_path}")
                    self.scan_file(file_path)

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive security report."""
        findings_by_severity = defaultdict(list)
        findings_by_category = defaultdict(list)

        for finding in self.findings:
            findings_by_severity[finding.severity].append(asdict(finding))
            findings_by_category[finding.category].append(asdict(finding))

        report = {
            'scan_date': datetime.now().isoformat(),
            'statistics': dict(self.stats),
            'summary': {
                'total_findings': len(self.findings),
                'critical': self.stats['findings_by_severity']['CRITICAL'],
                'high': self.stats['findings_by_severity']['HIGH'],
                'medium': self.stats['findings_by_severity']['MEDIUM'],
                'low': self.stats['findings_by_severity']['LOW'],
                'info': self.stats['findings_by_severity']['INFO'],
            },
            'findings_by_severity': dict(findings_by_severity),
            'findings_by_category': dict(findings_by_category),
            'all_findings': [asdict(f) for f in self.findings]
        }

        return report

    def print_summary(self, report: Dict[str, Any]) -> None:
        """Print a human-readable summary."""
        print("\n" + "="*70)
        print("SECURITY AUDIT SUMMARY")
        print("="*70)

        stats = report['statistics']
        print(f"\nFiles Scanned: {stats['files_scanned']}")
        print(f"Scripts Scanned: {stats['scripts_scanned']}")
        print(f"Lines Scanned: {stats['lines_scanned']:,}")

        summary = report['summary']
        print(f"\nTotal Findings: {summary['total_findings']}")
        print(f"  CRITICAL: {summary['critical']}")
        print(f"  HIGH:     {summary['high']}")
        print(f"  MEDIUM:   {summary['medium']}")
        print(f"  LOW:      {summary['low']}")
        print(f"  INFO:     {summary['info']}")

        # Show critical findings
        if summary['critical'] > 0:
            print("\n" + "="*70)
            print("CRITICAL FINDINGS (must fix immediately)")
            print("="*70)
            for finding in report['findings_by_severity'].get('CRITICAL', [])[:10]:
                print(f"\n• {finding['file']}:{finding['line_number']}")
                print(f"  Issue: {finding['issue']}")
                print(f"  Evidence: {finding['evidence']}")
                print(f"  → {finding['recommendation']}")

        # Show high findings
        if summary['high'] > 0:
            print("\n" + "="*70)
            print("HIGH FINDINGS (should fix soon)")
            print("="*70)
            count = min(5, summary['high'])
            for finding in report['findings_by_severity'].get('HIGH', [])[:count]:
                print(f"\n• {finding['file']}:{finding['line_number']}")
                print(f"  Issue: {finding['issue']}")
                print(f"  → {finding['recommendation']}")

            if summary['high'] > count:
                print(f"\n... and {summary['high'] - count} more HIGH findings")

        print("\n" + "="*70)

        # Exit code based on severity
        if summary['critical'] > 0:
            print("\n❌ FAILED: Critical security issues found")
            return 2
        elif summary['high'] > 0:
            print("\n⚠️  WARNING: High severity issues found")
            return 1
        else:
            print("\n✅ PASSED: No critical or high severity issues")
            return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Security audit scanner for cc-polymath skills library'
    )
    parser.add_argument('--path', type=Path, default=Path('skills'),
                       help='Path to scan (default: skills/)')
    parser.add_argument('--output', type=Path,
                       help='Output JSON report file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--fail-on', choices=['critical', 'high', 'medium', 'any'],
                       default='critical',
                       help='Fail if findings at this severity or higher (default: critical)')

    args = parser.parse_args()

    # Create auditor and scan
    auditor = SecurityAuditor(verbose=args.verbose)

    if args.path.is_file():
        auditor.scan_file(args.path)
    else:
        auditor.scan_directory(args.path)

    # Generate report
    report = auditor.generate_report()

    # Save JSON if requested
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nJSON report saved to: {args.output}")

    # Print summary
    exit_code = auditor.print_summary(report)

    # Determine exit code based on --fail-on
    summary = report['summary']
    if args.fail_on == 'critical' and summary['critical'] > 0:
        sys.exit(2)
    elif args.fail_on == 'high' and (summary['critical'] > 0 or summary['high'] > 0):
        sys.exit(1)
    elif args.fail_on == 'medium' and (summary['critical'] > 0 or summary['high'] > 0 or summary['medium'] > 0):
        sys.exit(1)
    elif args.fail_on == 'any' and summary['total_findings'] > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
