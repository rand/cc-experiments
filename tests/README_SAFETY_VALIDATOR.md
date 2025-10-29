# Operational Safety Validator

A comprehensive static analysis tool for detecting operational safety issues in code, focused on production best practices and operational reliability.

## Overview

The `safety_validator.py` script scans codebases for operational safety issues that differ from security vulnerabilities. It focuses on patterns that can cause production incidents, data loss, resource leaks, race conditions, and system instability.

## Features

- **9 Detection Categories**: Comprehensive coverage of operational safety issues
- **500+ Lines**: Robust pattern detection with context-aware analysis
- **Multiple Output Formats**: Human-readable summary and JSON reports
- **Severity Levels**: CRITICAL, HIGH, MEDIUM, LOW, INFO
- **Actionable Recommendations**: Each finding includes specific remediation guidance
- **Statistics Tracking**: Detailed metrics on scanned files and findings

## Detection Categories

### 1. Destructive Operations Without Warnings
Detects potentially destructive operations that lack proper safeguards:
- `DROP TABLE/DATABASE` without confirmation
- `DELETE`/`TRUNCATE` without WHERE clause
- `rm -rf` without interactive mode
- `git reset --hard` without warning
- `kubectl delete` without dry-run/confirmation
- Filesystem format operations

**Example Finding:**
```sql
DELETE FROM users  -- CRITICAL: Missing WHERE clause
```

**Recommendation:** Add WHERE clause or implement multi-step confirmation

---

### 2. Database Transaction Safety
Identifies transaction management issues:
- `BEGIN TRANSACTION` without visible `COMMIT`/`ROLLBACK`
- Missing transaction error handling
- Long-running transactions (>20 lines) without timeout
- Nested transactions without `SAVEPOINT`
- Unsafe isolation levels (READ UNCOMMITTED)
- Table locks without timeout

**Example Finding:**
```python
cursor.execute("BEGIN TRANSACTION")
cursor.execute("UPDATE accounts SET balance = balance - 100")
# HIGH: No COMMIT or ROLLBACK visible
```

**Recommendation:** Implement try/except with rollback in error handler and commit in success path

---

### 3. Network Retry/Timeout Patterns
Detects missing resilience patterns in network operations:
- HTTP requests without timeout or retry logic
- Retry loops without exponential backoff
- Network errors silently ignored
- Missing circuit breaker patterns
- No connection pooling
- Requests without session reuse

**Example Finding:**
```python
response = requests.get("https://api.example.com")  # MEDIUM: No timeout
```

**Recommendation:** Add timeout parameter and implement retry logic with exponential backoff

---

### 4. Resource Cleanup
Identifies resource management issues:
- File handles opened without context managers
- Database connections without proper cleanup
- Network sockets without close
- Missing `__enter__`/`__exit__` in resource classes
- Non-daemon threads without join
- Subprocesses without wait
- Temporary files without cleanup

**Example Finding:**
```python
f = open("data.txt", "r")  # MEDIUM: No context manager
content = f.read()
# Missing f.close()
```

**Recommendation:** Use `with open(...) as f:` to ensure file is closed even on error

---

### 5. Race Condition Patterns
Detects common concurrency issues:
- Check-then-act (TOCTOU) without locking
- Shared state modification without synchronization
- Global state changes without locks
- Lazy initialization without locks
- Counter operations without atomicity
- Shared dictionaries without synchronization
- Parallel processing without proper primitives

**Example Finding:**
```python
if os.path.exists("data.txt"):  # HIGH: TOCTOU race condition
    with open("data.txt", "r") as f:
        content = f.read()
```

**Recommendation:** Use try/except with FileNotFoundError instead of checking existence first

---

### 6. Graceful Degradation
Identifies missing resilience patterns:
- Services without health check endpoints
- External service calls without fallback behavior
- Missing graceful shutdown handlers (SIGTERM/SIGINT)
- Infinite loops without signal handling
- Circuit breakers without fallback logic
- Service discovery without cached fallback
- Threads/processes without error handling

**Example Finding:**
```python
while True:  # LOW: No signal handling
    process_item()
```

**Recommendation:** Add signal handlers or catch KeyboardInterrupt for graceful shutdown

---

### 7. Database Connection Management
Detects inefficient database connection patterns:
- Connections created without pooling
- Connection creation inside loops
- Async database operations without pool
- SQLAlchemy engines without pool configuration
- `CREATE TABLE` without `IF NOT EXISTS`

**Example Finding:**
```python
for i in range(100):
    conn = psycopg2.connect("dbname=test")  # HIGH: Connection in loop
    cursor = conn.cursor()
```

**Recommendation:** Create connection once outside loop and reuse, or use connection pool

---

### 8. Observability
Detects missing logging and monitoring:
- Exceptions silently swallowed
- HTTP requests without logging
- Complex functions without logging
- Long sleeps without logging reason

**Example Finding:**
```python
try:
    risky_operation()
except Exception:
    pass  # HIGH: Exception silently swallowed
```

**Recommendation:** Log exception with traceback: `logger.exception("message")`

---

### 9. Kubernetes Safety
Identifies Kubernetes operational issues:
- `kubectl apply` without validation
- Containers without health probes (liveness/readiness)
- Missing resource limits and requests
- Deployments without update strategy
- `kubectl exec` without interactive mode

**Example Finding:**
```yaml
containers:
  - name: app
    image: myapp:latest
# MEDIUM: Missing livenessProbe and readinessProbe
```

**Recommendation:** Add livenessProbe and readinessProbe for proper health monitoring

---

## Usage

### Basic Scan
```bash
# Scan default skills directory
python3 tests/safety_validator.py

# Scan specific file
python3 tests/safety_validator.py --path skills/database-postgres.md

# Scan specific directory
python3 tests/safety_validator.py --path skills/
```

### Output Options
```bash
# Generate JSON report
python3 tests/safety_validator.py --json --output safety_report.json

# Verbose output (show all findings)
python3 tests/safety_validator.py --verbose

# JSON output to stdout
python3 tests/safety_validator.py --json
```

### Severity Options
```bash
# Fail on critical issues (default)
python3 tests/safety_validator.py --fail-on critical

# Fail on high or critical issues
python3 tests/safety_validator.py --fail-on high

# Fail on any finding
python3 tests/safety_validator.py --fail-on any
```

### Help
```bash
# Show help
python3 tests/safety_validator.py --help

# Show detailed category information
python3 tests/safety_validator.py --help-categories
```

---

## Output Format

### Human-Readable Summary
```
================================================================================
OPERATIONAL SAFETY VALIDATION REPORT
================================================================================

Files Scanned:   42
Scripts Scanned: 15
Lines Scanned:   12,543

Total Findings: 89
  CRITICAL: 2
  HIGH:     15
  MEDIUM:   45
  LOW:      27
  INFO:     0

================================================================================
FINDINGS BY CATEGORY
================================================================================

Database Transaction Safety: 12 issue(s)
Resource Cleanup: 23 issue(s)
Network Retry/Timeout: 8 issue(s)
Race Condition: 15 issue(s)
...

================================================================================
CRITICAL FINDINGS (fix immediately)
================================================================================

skills/database/postgres.md:145
  Category: Destructive Operations
  Issue: DELETE without WHERE clause
  Evidence: DELETE FROM users
  Recommendation: Add WHERE clause or implement confirmation for full table delete
```

### JSON Report Structure
```json
{
  "scan_date": "2025-10-29T08:00:00.000000",
  "scan_type": "operational_safety",
  "statistics": {
    "files_scanned": 42,
    "scripts_scanned": 15,
    "lines_scanned": 12543,
    "findings_by_severity": {
      "CRITICAL": 2,
      "HIGH": 15,
      "MEDIUM": 45,
      "LOW": 27
    }
  },
  "summary": {
    "total_findings": 89,
    "critical": 2,
    "high": 15,
    "medium": 45,
    "low": 27,
    "info": 0
  },
  "findings_by_severity": { ... },
  "findings_by_category": { ... },
  "all_findings": [
    {
      "severity": "HIGH",
      "category": "Resource Cleanup",
      "file": "tests/example.py",
      "line_number": 42,
      "issue": "Database connection without cleanup",
      "evidence": "conn = psycopg2.connect('dbname=test')",
      "recommendation": "Use context manager or ensure .close() in finally block"
    }
  ]
}
```

---

## Exit Codes

- **0**: No issues found (or issues below --fail-on threshold)
- **1**: High severity issues found (if --fail-on high)
- **2**: Critical severity issues found (if --fail-on critical)

---

## Integration with CI/CD

### GitHub Actions
```yaml
- name: Run Operational Safety Validator
  run: |
    python3 tests/safety_validator.py --fail-on high --output safety_report.json

- name: Upload Safety Report
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: safety-report
    path: safety_report.json
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running operational safety validator..."
python3 tests/safety_validator.py --fail-on high --path $(git diff --cached --name-only)

if [ $? -ne 0 ]; then
    echo "Operational safety issues found. Commit rejected."
    exit 1
fi
```

---

## Test Examples

The repository includes `tests/test_operational_safety_examples.py` which demonstrates all detection categories with intentionally unsafe code patterns and their safe alternatives.

Run the validator on the test file:
```bash
python3 tests/safety_validator.py --path tests/test_operational_safety_examples.py --verbose
```

Expected output: ~217 findings across all categories

---

## Comparison with Security Audit

While `security_audit.py` focuses on **security vulnerabilities** (secrets, injection, crypto), `safety_validator.py` focuses on **operational reliability**:

| Aspect | Security Audit | Safety Validator |
|--------|---------------|------------------|
| Focus | Confidentiality, Integrity | Availability, Reliability |
| Examples | SQL injection, hardcoded secrets | Race conditions, resource leaks |
| Impact | Data breaches, unauthorized access | Outages, data loss, crashes |
| Use Case | Security review, compliance | Production readiness, SRE review |

**Use both tools** for comprehensive code quality:
```bash
python3 tests/security_audit.py --fail-on high
python3 tests/safety_validator.py --fail-on high
```

---

## Customization

### Adding New Patterns

To add a new detection pattern, edit `safety_validator.py`:

```python
# In __init__ method of SafetyValidator class
self.your_category_patterns = {
    r'your_regex_pattern':
        ('SEVERITY', 'Issue description', 'Recommendation text'),
}

# In _scan_line method
for pattern, (severity, issue, recommendation) in self.your_category_patterns.items():
    if re.search(pattern, line):
        self._add_finding(severity, 'Your Category', file_path,
                        line_num, issue, line.strip(), recommendation)
```

### Tuning False Positives

The validator includes context-aware detection to reduce false positives:
- Checks for confirmation patterns near destructive operations
- Excludes test/example files from certain checks
- Uses multi-line context for transaction analysis

---

## Limitations

- **Static Analysis Only**: Cannot detect runtime issues or logical errors
- **Pattern-Based**: May have false positives/negatives with complex code
- **Context-Aware but Limited**: Cannot fully understand program flow
- **Language Coverage**: Primarily Python, SQL, Shell, YAML, Kubernetes manifests

---

## Best Practices

1. **Run regularly**: Integrate into CI/CD pipeline
2. **Fix by priority**: Address CRITICAL and HIGH findings first
3. **Review false positives**: Use context to determine if finding is valid
4. **Combine with other tools**: Use alongside security_audit.py, linters, type checkers
5. **Educate team**: Use findings to teach operational best practices

---

## Performance

- **Speed**: ~1000 lines/second on typical hardware
- **Memory**: Minimal (processes line-by-line)
- **Scalability**: Can scan large codebases (tested on 100k+ lines)

---

## Contributing

To add new detection patterns or improve existing ones:

1. Add pattern to appropriate category in `__init__` method
2. Add test case to `test_operational_safety_examples.py`
3. Run validator on test file to verify detection
4. Update this documentation with new category/pattern

---

## License

Same as parent project (cc-polymath)

---

## Support

For issues or questions:
- Check `--help-categories` for detailed category information
- Review test examples in `test_operational_safety_examples.py`
- Consult parent project documentation

---

## Quick Reference

```bash
# Most common usage patterns
python3 tests/safety_validator.py                                    # Basic scan
python3 tests/safety_validator.py --fail-on high                     # Strict mode
python3 tests/safety_validator.py --json --output report.json        # CI/CD
python3 tests/safety_validator.py --help-categories                  # Learn categories
python3 tests/safety_validator.py --path tests/ --verbose            # Debug
```
