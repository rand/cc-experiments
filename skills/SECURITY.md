# Security Policy

## Overview

The cc-polymath skills library contains educational content, code examples, and executable scripts. Security is paramount to ensure users can safely learn and apply these skills without exposing their systems to risk.

## Our Commitment

We are committed to:
- Maintaining secure code examples
- Clearly marking dangerous operations
- Providing rollback procedures for destructive operations
- Protecting against accidentally committed secrets
- Validating all contributed skills for security issues

## Reporting a Vulnerability

If you discover a security vulnerability in cc-polymath, please report it responsibly:

1. **DO NOT** open a public GitHub issue
2. Email security concerns to: [rand.arete@gmail.com]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work to fix CRITICAL issues within 7 days.

## Security Guidelines for Skill Contributors

### Before Creating a Skill

Review the security checklist in `.claude/audits/safety-checklist.md` and ensure your skill meets all criteria.

### Required Security Practices

#### 1. Never Include Real Credentials

❌ **NEVER**:
```python
# WARNING: These are EXAMPLES of what NOT to do
API_KEY = "sk-live-EXAMPLE_BAD"  # Never hardcode real keys
password = "EXAMPLE_BAD_PASSWORD"  # Never hardcode passwords
```

✅ **ALWAYS**:
```python
API_KEY = os.environ.get("API_KEY")  # From environment
password = os.environ.get("DB_PASSWORD", "test_password_for_local_dev_only")
```

#### 2. Mark Destructive Operations

All destructive operations must have clear warnings:

```markdown
⚠️ **WARNING**: This command permanently deletes data without recovery.
**Always backup before running in production.**

\`\`\`bash
# Example: Destructive operation that requires warning and confirmation
TARGET_DIR="$1"
echo "WARNING: This will delete $TARGET_DIR"
echo "Are you sure? Type 'yes' to confirm:"
read confirmation
if [ "$confirmation" = "yes" ]; then
    # Destructive operation (rm with recursive force)
    # Add safety checks before actual deletion
    [ -z "$TARGET_DIR" ] && echo "Error: No target specified" && exit 1
    [ "$TARGET_DIR" = "/" ] && echo "Error: Cannot delete root" && exit 1
    # Perform deletion with user confirmation received
    find "$TARGET_DIR" -type f -delete
fi
\`\`\`
```

#### 3. Provide Rollback Procedures

Skills with deployment or migration operations must document rollback:

```markdown
## Rollback Procedure

If deployment fails:
1. Revert to previous version: `git revert HEAD`
2. Redeploy previous release: `deploy.sh --version v1.2.3`
3. Verify services: `./health-check.sh`
```

#### 4. Validate User Input in Scripts

All scripts must validate inputs:

```python
# ❌ Bad: No validation
filename = sys.argv[1]
os.remove(filename)

# ✅ Good: Validate path
filename = sys.argv[1]
if not filename.startswith('/safe/directory/'):
    raise ValueError("Path must be within /safe/directory/")
if '..' in filename:
    raise ValueError("Path traversal not allowed")
os.remove(filename)
```

#### 5. Use Parameterized Queries

Always use parameterized queries for databases:

```python
# ❌ Bad: SQL injection risk
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# ✅ Good: Parameterized query
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

#### 6. Avoid Dangerous Patterns

These patterns are flagged by our security scanner:

- `eval()` or `exec()` with user input
- `shell=True` in subprocess
- Piping network downloads to shell interpreters (download first, verify, then execute)
- Hardcoded secrets or API keys
- Destructive file operations without confirmation
- `sudo` without justification
- SQL queries with string concatenation

#### 7. Test Credentials Must Be Obvious

Test credentials must be clearly fake:

```bash
# ✅ Good: Obviously fake credentials for testing
DB_PASSWORD="test_password_for_local_dev_only"
API_KEY="fake_api_key_replace_with_real"
SECRET="example_secret_replace_me"

# ❌ Bad: EXAMPLE - looks too real (Never use format like these)
# DB_PASSWORD="EXAMPLE_BAD_xK9m"
# API_KEY="EXAMPLE_BAD_sk-abc"
```

### Severity Levels

Our security scanner categorizes findings by severity:

- **CRITICAL**: Must fix immediately (blocks PR merge)
  - Real credentials committed
  - Remote code execution vectors
  - SQL injection vulnerabilities
  - Pipe curl/wget to shell

- **HIGH**: Should fix before merge
  - Destructive operations without warnings
  - Command injection risks
  - Unvalidated user input in file operations
  - Weak cryptographic practices

- **MEDIUM**: Should fix eventually
  - Missing input validation
  - Use of `sudo` without justification
  - HTTP instead of HTTPS for external resources
  - Overly permissive file permissions

- **LOW**: Nice to fix
  - Informational security notes
  - Best practice recommendations

## Security Scanning

All skills are automatically scanned for security issues:

### Local Scanning

Run security audit before committing:

```bash
# Scan all skills
python3 tests/security_audit.py

# Scan specific skill
python3 tests/security_audit.py --path skills/your-skill.md

# Generate JSON report
python3 tests/security_audit.py --output security-report.json
```

### CI/CD Integration

Security scans run automatically on:
- Every pull request
- Commits to main branch
- Weekly (every Monday)
- Manual workflow dispatch

PRs with CRITICAL or HIGH findings are blocked until resolved.

## Acceptable Risk

Some security findings may be accepted if properly documented:

1. **Educational Examples**: Examples demonstrating vulnerabilities for learning purposes must:
   - Clearly label the code as insecure
   - Explain why it's dangerous
   - Provide secure alternative

2. **Test/Development Code**: Scripts for local development may use simpler patterns if:
   - Clearly marked as test/dev only
   - Never used in production
   - Documented in comments

3. **Platform Limitations**: Some platforms require patterns that would normally be flagged:
   - Document why the pattern is necessary
   - Note any mitigations in place
   - Reference official documentation

To accept risk, add a comment in the skill:

```markdown
<!-- SECURITY: Accepted risk - Educational example of SQL injection -->
\`\`\`python
# ⚠️ INSECURE: This demonstrates SQL injection vulnerability
# NEVER use this pattern in production
query = f"SELECT * FROM users WHERE name = '{user_input}'"
\`\`\`

**Secure alternative:**
\`\`\`python
query = "SELECT * FROM users WHERE name = %s"
cursor.execute(query, (user_input,))
\`\`\`
```

## Security Review Process

All new skills undergo security review:

1. **Automated Scan**: CI runs security_audit.py
2. **Secrets Detection**: gitleaks scans for credentials
3. **Code Analysis**: bandit/shellcheck validate scripts
4. **Manual Review**: Maintainers review high-risk skills
5. **Approval**: PR approved only if all checks pass

High-risk skills (security, cryptography, deployment) require additional manual review by project maintainers.

## Incident Response

If a security issue is discovered in published skills:

1. **Assess severity** using our severity levels
2. **Create private issue** for CRITICAL/HIGH
3. **Develop fix** with security review
4. **Test fix** thoroughly
5. **Deploy fix** to main branch
6. **Notify users** if necessary (via GitHub release notes)
7. **Document incident** in `.claude/audits/vulnerabilities.jsonl`

## Security Resources

- Security Audit Script: `tests/security_audit.py`
- Safety Checklist: `.claude/audits/safety-checklist.md`
- CI Workflow: `.github/workflows/security-audit.yml`
- Recent Findings: `.claude/audits/security-report-*.json`

## Questions

For security questions or concerns:
- Open a discussion on GitHub (for general questions)
- Email security reports to: [rand.arete@gmail.com]
- Review existing security documentation in this file

## Acknowledgments

We appreciate responsible disclosure of security issues. Contributors who report valid security vulnerabilities will be acknowledged in release notes (unless they prefer to remain anonymous).

---

**Last Updated**: 2025-10-27
**Version**: 1.0
