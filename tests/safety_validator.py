#!/usr/bin/env python3
"""
Operational Safety Validator for cc-polymath Skills Library

Scans all skills, scripts, and examples for operational safety issues focused
on best practices for production operations, different from security concerns.

Detection Categories:
    - Destructive Operations: DROP TABLE/DATABASE, DELETE without WHERE, rm -rf,
      git reset --hard, kubectl delete without confirmation
    - Database Transaction Safety: BEGIN without COMMIT/ROLLBACK, missing error
      handling, long-running transactions, nested transactions without savepoints
    - Network Retry/Timeout Patterns: HTTP requests without retry logic, missing
      exponential backoff, no circuit breaker patterns, missing connection pooling
    - Resource Cleanup: File handles without context managers, unclosed connections,
      network sockets without cleanup, missing __enter__/__exit__ in resource classes
    - Race Condition Patterns: Check-then-act without locking, shared state without
      synchronization, TOCTOU issues, missing atomic operations
    - Graceful Degradation: Services without health checks, missing fallback behavior,
      no graceful shutdown handlers, circuit breakers without fallback

Usage:
    python tests/safety_validator.py [--output report.json] [--verbose]
    python tests/safety_validator.py --path skills/specific/skill.md
    python tests/safety_validator.py --fail-on high --json
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
    """Operational safety finding with severity and details."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str
    file: str
    line_number: int
    issue: str
    evidence: str
    recommendation: str


class SafetyValidator:
    """Main operational safety validator class."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.findings: List[Finding] = []
        self.stats = {
            'files_scanned': 0,
            'scripts_scanned': 0,
            'lines_scanned': 0,
            'findings_by_severity': defaultdict(int)
        }

        # Destructive operations without warnings
        self.destructive_operations = {
            r'\bDROP\s+DATABASE\b(?!.*(?:IF\s+EXISTS|CONFIRM|WARNING|BACKUP))':
                ('CRITICAL', 'DROP DATABASE without confirmation',
                 'Add explicit confirmation prompt and backup verification before dropping database'),
            r'\bDROP\s+TABLE\b(?!.*(?:IF\s+EXISTS|CASCADE))(?!.*(?:CONFIRM|WARNING))':
                ('HIGH', 'DROP TABLE without safety check',
                 'Add IF EXISTS clause or explicit confirmation, ensure backup exists'),
            r'\bDELETE\s+FROM\s+\w+\s*(?:;|$)(?!.*WHERE)':
                ('CRITICAL', 'DELETE without WHERE clause',
                 'Add WHERE clause or implement confirmation for full table delete'),
            r'\bTRUNCATE\s+TABLE?\s+\w+(?!.*(?:CONFIRM|WARNING|BACKUP))':
                ('HIGH', 'TRUNCATE without confirmation',
                 'Add confirmation prompt and verify backup before truncating'),
            r'\brm\s+-rf?\s+(?:/|~|\$HOME|\*|\.\./)(?!.*(?:CONFIRM|read\s+-p))':
                ('CRITICAL', 'rm -rf on critical paths without confirmation',
                 'Add interactive confirmation or use safer alternatives like trash-cli'),
            r'\bgit\s+reset\s+--hard(?!.*(?:CONFIRM|WARNING|STASH))':
                ('HIGH', 'git reset --hard without warning',
                 'Warn about data loss, suggest git stash first, require explicit confirmation'),
            r'\bgit\s+clean\s+-[fxd]+(?!.*(?:--dry-run|CONFIRM))':
                ('MEDIUM', 'git clean without dry-run',
                 'Run with --dry-run first, show files to be removed, require confirmation'),
            r'\bkubectl\s+delete\s+(?:deployment|service|pod|namespace)(?!.*(?:--dry-run|CONFIRM|-n\s+\w+))':
                ('HIGH', 'kubectl delete without confirmation',
                 'Add --dry-run=client first, require explicit confirmation, specify namespace'),
            r'\bdocker\s+system\s+prune\s+-a(?!.*(?:--filter|CONFIRM))':
                ('MEDIUM', 'docker prune without filters',
                 'Add --filter to protect tagged images, require confirmation'),
            r'\bformat\s+[A-Za-z]:|mkfs\.':
                ('CRITICAL', 'Filesystem format operation',
                 'Implement multi-step confirmation, verify device path, check for mounted filesystem'),
        }

        # Database transaction safety patterns
        self.transaction_patterns = {
            r'\bBEGIN\s+(?:TRANSACTION|WORK|TRAN)?(?!.*(?:COMMIT|ROLLBACK))':
                ('HIGH', 'BEGIN TRANSACTION without visible COMMIT/ROLLBACK',
                 'Ensure transaction has both COMMIT and ROLLBACK paths with proper error handling'),
            r'\bSTART\s+TRANSACTION(?!.*(?:COMMIT|ROLLBACK))':
                ('HIGH', 'START TRANSACTION without COMMIT/ROLLBACK',
                 'Implement try/except with rollback in error handler and commit in success path'),
            r'cursor\.execute\s*\([^)]*BEGIN(?!.*(?:try|except|finally|context|with))':
                ('MEDIUM', 'Transaction without error handling',
                 'Wrap transaction in try/except/finally or use context manager'),
            r'BEGIN\s+TRANSACTION.*\n(?:.*\n){20,}':
                ('MEDIUM', 'Long-running transaction',
                 'Break into smaller transactions, add timeout, consider using SAVEPOINT for nested operations'),
            r'BEGIN.*BEGIN(?!.*SAVEPOINT)':
                ('MEDIUM', 'Nested transaction without SAVEPOINT',
                 'Use SAVEPOINT for nested transactions to allow partial rollback'),
            r'SET\s+TRANSACTION\s+ISOLATION\s+LEVEL\s+READ\s+UNCOMMITTED':
                ('HIGH', 'Unsafe transaction isolation level',
                 'Use READ COMMITTED or higher to prevent dirty reads'),
            r'(?:INSERT|UPDATE|DELETE).*(?:INSERT|UPDATE|DELETE).*(?:INSERT|UPDATE|DELETE)(?!.*(?:SAVEPOINT|COMMIT))':
                ('MEDIUM', 'Multiple DML operations without intermediate savepoints',
                 'Add SAVEPOINT after each major operation for partial rollback capability'),
            r'LOCK\s+TABLE(?!.*(?:NOWAIT|timeout))':
                ('MEDIUM', 'Table lock without timeout',
                 'Add NOWAIT or timeout to prevent indefinite blocking'),
        }

        # Network retry and timeout patterns
        self.network_patterns = {
            r'(?:requests|urllib|httpx|aiohttp)\.(?:get|post|put|delete|patch)\s*\([^)]*\)(?!.*(?:timeout|retry|Retry))':
                ('MEDIUM', 'HTTP request without timeout or retry',
                 'Add timeout parameter and implement retry logic with exponential backoff'),
            r'requests\.(?:get|post)(?!.*(?:Session|session\(\)))':
                ('LOW', 'HTTP request without connection pooling',
                 'Use requests.Session() for connection reuse and better performance'),
            r'while.*retry.*count\s*<\s*\d+(?!.*(?:time\.sleep|sleep|backoff|exponential))':
                ('MEDIUM', 'Retry without backoff',
                 'Implement exponential backoff between retries to avoid overwhelming service'),
            r'for.*range\(.*retry(?!.*(?:sleep|delay|backoff|wait))':
                ('MEDIUM', 'Retry loop without delay',
                 'Add exponential backoff: time.sleep(base_delay * (2 ** attempt))'),
            r'except.*(?:RequestException|ConnectionError|Timeout):\s*pass':
                ('HIGH', 'Network error silently ignored',
                 'Log error, implement circuit breaker pattern, notify monitoring system'),
            r'(?:requests|httpx)\.(?:get|post)(?!.*(?:CircuitBreaker|circuit_breaker|fallback))':
                ('LOW', 'No circuit breaker pattern',
                 'Implement circuit breaker to prevent cascading failures (e.g., pybreaker library)'),
            r'urlopen\s*\([^)]*\)(?!.*timeout)':
                ('MEDIUM', 'URL open without timeout',
                 'Add timeout parameter to prevent hanging connections'),
            r'(?:socket|asyncio)\.(?:create_connection|open_connection)(?!.*timeout)':
                ('MEDIUM', 'Socket connection without timeout',
                 'Set connection timeout to prevent indefinite blocking'),
            r'ConnectionPool\s*\((?!.*(?:maxsize|block))':
                ('LOW', 'Connection pool without size limits',
                 'Set maxsize and configure blocking behavior to prevent resource exhaustion'),
            r'requests\.adapters\.HTTPAdapter\s*\((?!.*(?:max_retries|pool_))':
                ('LOW', 'HTTPAdapter without retry or pool configuration',
                 'Configure max_retries and pool_connections/pool_maxsize'),
        }

        # Resource cleanup patterns
        self.resource_cleanup_patterns = {
            r'open\s*\([^)]*\)(?!.*(?:\bwith\b|\.close\(\)|context))':
                ('MEDIUM', 'File opened without context manager',
                 'Use "with open(...) as f:" to ensure file is closed even on error'),
            r'(?:psycopg2|pymysql|sqlite3)\.connect\s*\([^)]*\)(?!.*(?:\bwith\b|\.close\(\)|context))':
                ('HIGH', 'Database connection without cleanup',
                 'Use context manager or ensure .close() in finally block'),
            r'socket\.\w+\((?!.*(?:\bwith\b|\.close\(\)))':
                ('MEDIUM', 'Socket without cleanup',
                 'Use context manager or ensure socket.close() in finally block'),
            r'(?:urllib\.request\.urlopen|requests\.get).*(?!(?:with|\.close\(\)|finally))':
                ('LOW', 'HTTP response without explicit close',
                 'Use context manager for large responses to free resources immediately'),
            r'class\s+\w+.*:\s*\n(?:.*\n){0,50}?\s+def\s+__init__.*(?:open\(|connect\(|socket\()(?!.*(?:__enter__|__exit__|close))':
                ('MEDIUM', 'Resource class without context manager',
                 'Implement __enter__ and __exit__ methods to support "with" statement'),
            r'threading\.Thread\s*\(.*daemon\s*=\s*False(?!.*\.join\(\))':
                ('LOW', 'Non-daemon thread without join',
                 'Call thread.join() or set daemon=True to prevent blocking program exit'),
            r'subprocess\.Popen\s*\((?!.*(?:with|\.wait\(\)|\.communicate\(\)))':
                ('MEDIUM', 'Subprocess without wait',
                 'Call .wait() or .communicate() to clean up process resources'),
            r'tempfile\.(?:NamedTemporaryFile|mkstemp)(?!.*(?:delete=False|with)).*(?!.*(?:os\.unlink|remove))':
                ('LOW', 'Temporary file without cleanup',
                 'Use context manager or explicitly delete temporary files'),
            r'(?:redis|memcache)\.(?:Redis|Client)\s*\((?!.*(?:connection_pool|with))':
                ('LOW', 'Cache client without connection pooling',
                 'Use connection pool to manage resources efficiently'),
        }

        # Race condition patterns
        self.race_condition_patterns = {
            r'if\s+(?:os\.path\.)?exists\s*\([^)]+\):\s*\n\s*(?:open|with\s+open|os\.remove|shutil)':
                ('HIGH', 'TOCTOU race condition (check-then-act)',
                 'Use try/except with FileNotFoundError instead of checking existence first'),
            r'if\s+not\s+(?:os\.path\.)?exists.*:\s*\n\s*(?:open.*"w"|makedirs)':
                ('MEDIUM', 'Race condition in file creation',
                 'Use os.makedirs(exist_ok=True) or open with "x" mode for atomic creation'),
            r'(?:self|cls)\.\w+\s*(?:\+|\-)?=(?!.*(?:Lock|RLock|Semaphore|threading|asyncio\.Lock))':
                ('MEDIUM', 'Shared state modification without lock',
                 'Protect shared state with threading.Lock or asyncio.Lock'),
            r'(?:global|nonlocal)\s+\w+.*\n.*\w+\s*[+\-*/]?=(?!.*(?:Lock|atomic))':
                ('HIGH', 'Global state modification without synchronization',
                 'Use threading.Lock or atomic operations for thread-safe modifications'),
            r'if\s+.*\s+is\s+None:\s*\n\s*.*\s*=\s*(?!.*(?:Lock|setdefault|get_or_create))':
                ('MEDIUM', 'Lazy initialization without lock',
                 'Use threading.Lock for thread-safe lazy initialization or consider using @lru_cache'),
            r'\bcount\s*=\s*0.*\n(?:.*\n){0,20}?.*count\s*\+=\s*1(?!.*(?:Lock|atomic|threading))':
                ('MEDIUM', 'Counter without atomic operation',
                 'Use threading.Lock or atomic counter class for thread safety'),
            r'(?:cache|memo|state)\s*=\s*\{\}(?!.*(?:Lock|thread_safe))':
                ('MEDIUM', 'Shared dictionary without synchronization',
                 'Use threading.Lock or collections.defaultdict with lock for thread safety'),
            r'os\.rename\s*\([^)]*\)(?!.*try)':
                ('LOW', 'File rename without error handling',
                 'Wrap os.rename in try/except to handle race condition where file is moved/deleted'),
            r'(?:multiprocessing|concurrent\.futures)(?!.*(?:Lock|Manager|Queue))':
                ('LOW', 'Parallel processing without synchronization primitives',
                 'Use multiprocessing.Lock, Manager, or Queue for safe inter-process communication'),
        }

        # Graceful degradation and resilience patterns
        self.graceful_degradation_patterns = {
            r'def\s+(?:health|healthcheck|ready|liveness)\s*\([^)]*\)(?!.*(?:try|except))':
                ('MEDIUM', 'Health check without error handling',
                 'Wrap health check in try/except to prevent crashes from affecting monitoring'),
            r'(?:FastAPI|Flask|Django).*app(?!.*(?:/health|/healthz|/ready|health_check))':
                ('LOW', 'Web service without health endpoint',
                 'Add /health and /ready endpoints for load balancer and orchestration checks'),
            r'(?:requests\.get|urllib\.request)(?!.*(?:except|try|fallback))':
                ('LOW', 'External service call without fallback',
                 'Implement fallback behavior when external service is unavailable'),
            r'signal\.signal\s*\(.*SIGTERM(?!.*(?:shutdown|cleanup|graceful))':
                ('MEDIUM', 'SIGTERM handler without graceful shutdown',
                 'Implement graceful shutdown: finish in-flight requests, close connections, save state'),
            r'signal\.signal\s*\(.*SIGINT(?!.*(?:shutdown|cleanup|graceful))':
                ('MEDIUM', 'SIGINT handler without cleanup',
                 'Implement cleanup handler to release resources on Ctrl+C'),
            r'while\s+True:(?!.*(?:signal|KeyboardInterrupt|SystemExit))':
                ('LOW', 'Infinite loop without signal handling',
                 'Add signal handlers or catch KeyboardInterrupt for graceful shutdown'),
            r'(?:Thread|Process).*target\s*=(?!.*(?:try|except|finally))':
                ('LOW', 'Thread/Process without error handling',
                 'Wrap thread target in try/except to prevent silent failures'),
            r'class.*CircuitBreaker(?!.*(?:fallback|default|on_failure))':
                ('MEDIUM', 'Circuit breaker without fallback',
                 'Define fallback behavior when circuit is open (cached data, default values, degraded mode)'),
            r'@retry\s*\((?!.*(?:on_exception|fallback))':
                ('LOW', 'Retry decorator without fallback',
                 'Add fallback function for when all retries are exhausted'),
            r'(?:consul|etcd|zookeeper)\.(?:get|watch)(?!.*(?:default|fallback|cache))':
                ('MEDIUM', 'Service discovery without fallback',
                 'Cache last known good configuration for use when service discovery is unavailable'),
            r'def\s+\w+.*raise\s+Exception\b(?!.*(?:fallback|default))':
                ('LOW', 'Function that only fails without graceful degradation',
                 'Consider returning default value or degraded result instead of always raising'),
        }

        # Database connection pooling and management
        self.db_connection_patterns = {
            r'(?:psycopg2|pymysql|mysql\.connector)\.connect\s*\([^)]*\)(?!.*(?:pool|connection_pool))':
                ('MEDIUM', 'Database connection without pooling',
                 'Use connection pooling (e.g., psycopg2.pool, SQLAlchemy) for better resource management'),
            r'for\s+.*range.*:.*\.connect\s*\(':
                ('HIGH', 'Connection created in loop',
                 'Create connection once outside loop and reuse, or use connection pool'),
            r'(?:asyncpg|aiomysql)\.connect\s*\((?!.*(?:pool|create_pool))':
                ('MEDIUM', 'Async database connection without pool',
                 'Use connection pool for async database operations'),
            r'engine\s*=\s*create_engine\s*\([^)]*\)(?!.*(?:pool_size|max_overflow))':
                ('LOW', 'SQLAlchemy engine without pool configuration',
                 'Configure pool_size and max_overflow for your workload'),
            r'CREATE\s+TABLE(?!.*(?:IF\s+NOT\s+EXISTS))':
                ('LOW', 'CREATE TABLE without IF NOT EXISTS',
                 'Add IF NOT EXISTS to make operation idempotent'),
        }

        # Logging and observability
        self.observability_patterns = {
            r'except\s+\w+(?:Exception)?:\s*(?:pass|continue)(?!.*(?:log|print|warn))':
                ('HIGH', 'Exception silently swallowed',
                 'Log exception with traceback for debugging: logger.exception("message")'),
            r'(?:requests|http)\.(?:get|post)(?!.*(?:log|print|metric|trace))':
                ('LOW', 'HTTP request without logging',
                 'Log request details and duration for observability'),
            r'def\s+\w+.*:(?!.*(?:logger|logging|log|print))(?=.*\n(?:.*\n){5,}.*try)':
                ('LOW', 'Complex function without logging',
                 'Add logging for debugging and monitoring in production'),
            r'time\.sleep\s*\(\s*[0-9]+\s*\)(?!.*(?:log|print))':
                ('LOW', 'Long sleep without logging',
                 'Log reason for sleep to aid debugging (e.g., "Waiting for X to complete")'),
        }

        # Kubernetes and container safety
        self.kubernetes_patterns = {
            r'kubectl\s+apply(?!.*(?:--dry-run|--diff|-f\s+\w+\.ya?ml))':
                ('MEDIUM', 'kubectl apply without validation',
                 'Use --dry-run=client or --diff to preview changes before applying'),
            r'kubectl\s+exec(?!.*(?:-it|CONFIRM))':
                ('LOW', 'kubectl exec without interactive mode',
                 'Use -it flags for interactive sessions to prevent accidents'),
            r'containers:(?!.*(?:livenessProbe|readinessProbe))':
                ('MEDIUM', 'Kubernetes container without health probes',
                 'Add livenessProbe and readinessProbe for proper health monitoring'),
            r'kind:\s+Deployment(?!.*(?:strategy:|RollingUpdate))':
                ('LOW', 'Deployment without update strategy',
                 'Define update strategy (RollingUpdate) with maxSurge and maxUnavailable'),
            r'resources:(?!.*(?:limits|requests))':
                ('MEDIUM', 'Container without resource limits',
                 'Set resource requests and limits to prevent resource exhaustion'),
        }

    def scan_file(self, file_path: Path) -> None:
        """Scan a single file for operational safety issues."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')

            self.stats['files_scanned'] += 1
            self.stats['lines_scanned'] += len(lines)

            # Determine if this is a script
            is_script = file_path.suffix in {'.py', '.sh', '.js', '.ts', '.bash', '.sql', '.yaml', '.yml'}
            if is_script:
                self.stats['scripts_scanned'] += 1

            # Scan each line
            for line_num, line in enumerate(lines, 1):
                self._scan_line(file_path, line_num, line, is_script, content, lines)

        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not scan {file_path}: {e}", file=sys.stderr)

    def _scan_line(self, file_path: Path, line_num: int, line: str,
                   is_script: bool, full_content: str, lines: List[str]) -> None:
        """Scan a single line for operational safety issues."""

        # Skip comments in most cases
        is_comment = line.strip().startswith('#') or line.strip().startswith('//') or line.strip().startswith('--')
        is_multiline_string = '"""' in line or "'''" in line

        # Get context (next few lines for context-aware patterns)
        context_lines = '\n'.join(lines[max(0, line_num-1):min(len(lines), line_num+10)])

        # Destructive operations (always scan, even comments for documentation)
        for pattern, (severity, issue, recommendation) in self.destructive_operations.items():
            if re.search(pattern, line, re.IGNORECASE):
                # Check context for confirmation patterns
                if not self._has_confirmation_pattern(context_lines):
                    self._add_finding(severity, 'Destructive Operations', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Database transaction safety
        if is_script and not is_comment:
            for pattern, (severity, issue, recommendation) in self.transaction_patterns.items():
                if re.search(pattern, context_lines, re.IGNORECASE):
                    self._add_finding(severity, 'Database Transaction Safety', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Network retry/timeout patterns
        if is_script and not is_comment:
            for pattern, (severity, issue, recommendation) in self.network_patterns.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'Network Retry/Timeout', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Resource cleanup
        if is_script and not is_comment:
            for pattern, (severity, issue, recommendation) in self.resource_cleanup_patterns.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'Resource Cleanup', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Race condition patterns
        if is_script and not is_comment:
            for pattern, (severity, issue, recommendation) in self.race_condition_patterns.items():
                if re.search(pattern, context_lines):
                    self._add_finding(severity, 'Race Condition', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Graceful degradation
        if is_script and not is_comment:
            for pattern, (severity, issue, recommendation) in self.graceful_degradation_patterns.items():
                if re.search(pattern, context_lines):
                    self._add_finding(severity, 'Graceful Degradation', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Database connection patterns
        if is_script and not is_comment:
            for pattern, (severity, issue, recommendation) in self.db_connection_patterns.items():
                if re.search(pattern, line):
                    self._add_finding(severity, 'Database Connection Management', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Observability patterns
        if is_script and not is_comment:
            for pattern, (severity, issue, recommendation) in self.observability_patterns.items():
                if re.search(pattern, context_lines):
                    self._add_finding(severity, 'Observability', file_path,
                                    line_num, issue, line.strip(), recommendation)

        # Kubernetes patterns
        for pattern, (severity, issue, recommendation) in self.kubernetes_patterns.items():
            if re.search(pattern, context_lines, re.IGNORECASE):
                self._add_finding(severity, 'Kubernetes Safety', file_path,
                                line_num, issue, line.strip(), recommendation)

    def _has_confirmation_pattern(self, context: str) -> bool:
        """Check if context includes confirmation/safety patterns."""
        confirmation_patterns = [
            r'input\s*\([^)]*confirm',
            r'read\s+-p',
            r'--dry-run',
            r'if.*confirm',
            r'backup',
            r'WARNING',
            r'DANGER',
        ]
        return any(re.search(pattern, context, re.IGNORECASE) for pattern in confirmation_patterns)

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
            patterns = ['**/*.md', '**/*.py', '**/*.sh', '**/*.js', '**/*.ts',
                       '**/*.sql', '**/*.yaml', '**/*.yml']

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
        """Generate a comprehensive operational safety report."""
        findings_by_severity = defaultdict(list)
        findings_by_category = defaultdict(list)

        for finding in self.findings:
            findings_by_severity[finding.severity].append(asdict(finding))
            findings_by_category[finding.category].append(asdict(finding))

        report = {
            'scan_date': datetime.now().isoformat(),
            'scan_type': 'operational_safety',
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

    def print_summary(self, report: Dict[str, Any], json_output: bool = False) -> int:
        """Print a human-readable summary or JSON output."""
        if json_output:
            print(json.dumps(report, indent=2))
            return 0

        print("\n" + "="*80)
        print("OPERATIONAL SAFETY VALIDATION REPORT")
        print("="*80)

        stats = report['statistics']
        print(f"\nFiles Scanned:   {stats['files_scanned']}")
        print(f"Scripts Scanned: {stats['scripts_scanned']}")
        print(f"Lines Scanned:   {stats['lines_scanned']:,}")

        summary = report['summary']
        print(f"\nTotal Findings: {summary['total_findings']}")
        print(f"  CRITICAL: {summary['critical']}")
        print(f"  HIGH:     {summary['high']}")
        print(f"  MEDIUM:   {summary['medium']}")
        print(f"  LOW:      {summary['low']}")
        print(f"  INFO:     {summary['info']}")

        # Show findings by category
        if summary['total_findings'] > 0:
            print("\n" + "="*80)
            print("FINDINGS BY CATEGORY")
            print("="*80)
            for category, findings in report['findings_by_category'].items():
                print(f"\n{category}: {len(findings)} issue(s)")

        # Show critical findings
        if summary['critical'] > 0:
            print("\n" + "="*80)
            print("CRITICAL FINDINGS (fix immediately)")
            print("="*80)
            for finding in report['findings_by_severity'].get('CRITICAL', [])[:10]:
                print(f"\n{finding['file']}:{finding['line_number']}")
                print(f"  Category: {finding['category']}")
                print(f"  Issue: {finding['issue']}")
                print(f"  Evidence: {finding['evidence']}")
                print(f"  Recommendation: {finding['recommendation']}")

        # Show high findings
        if summary['high'] > 0:
            print("\n" + "="*80)
            print("HIGH FINDINGS (should fix soon)")
            print("="*80)
            count = min(5, summary['high'])
            for finding in report['findings_by_severity'].get('HIGH', [])[:count]:
                print(f"\n{finding['file']}:{finding['line_number']}")
                print(f"  Category: {finding['category']}")
                print(f"  Issue: {finding['issue']}")
                print(f"  Recommendation: {finding['recommendation']}")

            if summary['high'] > count:
                print(f"\n... and {summary['high'] - count} more HIGH findings")

        # Show medium findings summary
        if summary['medium'] > 0:
            print("\n" + "="*80)
            print(f"MEDIUM FINDINGS: {summary['medium']} issue(s)")
            print("="*80)
            print("Run with --verbose or --output to see all medium severity findings")

        print("\n" + "="*80)

        # Exit code based on severity
        if summary['critical'] > 0:
            print("\nFAILED: Critical operational safety issues found")
            return 2
        elif summary['high'] > 0:
            print("\nWARNING: High severity operational issues found")
            return 1
        else:
            print("\nPASSED: No critical or high severity operational issues")
            return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Operational Safety Validator for cc-polymath skills library',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/safety_validator.py
  python tests/safety_validator.py --path skills/database-postgres.md
  python tests/safety_validator.py --json --output safety_report.json
  python tests/safety_validator.py --fail-on high --verbose
        """
    )
    parser.add_argument('--path', type=Path, default=Path('skills'),
                       help='Path to scan (default: skills/)')
    parser.add_argument('--output', type=Path,
                       help='Output JSON report file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output showing all findings')
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format')
    parser.add_argument('--fail-on', choices=['critical', 'high', 'medium', 'any'],
                       default='critical',
                       help='Fail if findings at this severity or higher (default: critical)')
    parser.add_argument('--help-categories', action='store_true',
                       help='Show detailed information about detection categories')

    args = parser.parse_args()

    if args.help_categories:
        print("""
OPERATIONAL SAFETY DETECTION CATEGORIES

1. Destructive Operations Without Warnings
   - DROP TABLE/DATABASE without confirmation
   - DELETE/TRUNCATE without WHERE clause
   - rm -rf without interactive mode
   - git reset --hard without warning
   - kubectl delete without confirmation

2. Database Transaction Safety
   - BEGIN TRANSACTION without COMMIT/ROLLBACK
   - Missing transaction error handling
   - Long-running transactions without timeout
   - Nested transactions without savepoints

3. Network Retry/Timeout Patterns
   - HTTP requests without retry logic
   - Missing exponential backoff
   - No circuit breaker patterns
   - Requests without connection pooling

4. Resource Cleanup
   - File handles opened without context managers
   - Database connections without proper close
   - Network sockets without cleanup
   - Missing __enter__/__exit__ in resource classes

5. Race Condition Patterns
   - Check-then-act without locking
   - Shared state without synchronization
   - Time-of-check-time-of-use (TOCTOU)
   - Missing atomic operations

6. Graceful Degradation
   - Services without health checks
   - Missing fallback behavior
   - No graceful shutdown handlers
   - Circuit breakers without fallback

7. Database Connection Management
   - Connections without pooling
   - Connection creation in loops
   - Missing pool size configuration

8. Observability
   - Silent exception handling
   - Missing request logging
   - Complex functions without logging

9. Kubernetes Safety
   - kubectl apply without validation
   - Containers without health probes
   - Missing resource limits
   - No deployment strategy
        """)
        sys.exit(0)

    # Create validator and scan
    validator = SafetyValidator(verbose=args.verbose)

    if args.path.is_file():
        validator.scan_file(args.path)
    else:
        validator.scan_directory(args.path)

    # Generate report
    report = validator.generate_report()

    # Save JSON if requested
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        if not args.json:
            print(f"JSON report saved to: {args.output}")

    # Print summary
    exit_code = validator.print_summary(report, json_output=args.json)

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

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
