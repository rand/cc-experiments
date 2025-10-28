# Security Review Checklist

Use this checklist when reviewing code for security concerns. All items should be verified before approving security-sensitive changes.

## Authentication & Authorization

### Authentication
- [ ] All endpoints require authentication where appropriate
- [ ] Authentication tokens are validated on every request
- [ ] Token expiration is enforced
- [ ] Refresh tokens are implemented securely
- [ ] Session invalidation works correctly (logout, password change)
- [ ] Multi-factor authentication (MFA) is supported where required
- [ ] Failed login attempts are rate-limited
- [ ] Account lockout after repeated failed attempts
- [ ] Passwords are never logged or stored in plain text
- [ ] Password reset flow is secure (no user enumeration, expiring tokens)

### Authorization
- [ ] Authorization checks happen on every privileged operation
- [ ] Role-based access control (RBAC) is enforced
- [ ] Principle of least privilege is followed
- [ ] Users can only access their own data (no IDOR vulnerabilities)
- [ ] Object-level authorization is checked (not just endpoint-level)
- [ ] Privilege escalation is not possible
- [ ] JWT claims are validated (issuer, audience, expiration)
- [ ] API keys have appropriate scopes/permissions
- [ ] Service-to-service authentication is implemented
- [ ] Authorization decisions are centralized (not scattered)

## Input Validation

### General Validation
- [ ] All user input is validated (type, length, format)
- [ ] Validation happens on server-side (not just client-side)
- [ ] Whitelist validation is preferred over blacklist
- [ ] Error messages don't leak sensitive information
- [ ] File uploads are restricted (type, size, content)
- [ ] File names are sanitized (no path traversal)
- [ ] Uploaded files are scanned for malware
- [ ] Integer overflow/underflow is prevented
- [ ] Unicode/encoding issues are handled

### SQL Injection Prevention
- [ ] SQL queries use parameterized statements or ORM
- [ ] No string concatenation for SQL queries
- [ ] Dynamic SQL is avoided or properly escaped
- [ ] Stored procedures use parameters correctly
- [ ] Database permissions follow least privilege

### XSS Prevention
- [ ] All user input is escaped before rendering in HTML
- [ ] Content Security Policy (CSP) headers are set
- [ ] HTML sanitization library used for rich text
- [ ] JSON responses have correct Content-Type header
- [ ] DOM manipulation is safe (no innerHTML with user data)
- [ ] Template engine auto-escapes by default

### Command Injection Prevention
- [ ] System commands avoid shell=True
- [ ] User input is not passed to shell commands
- [ ] Commands use array syntax (not string concatenation)
- [ ] subprocess.run() uses list instead of string
- [ ] Environment variables are not user-controlled

### Path Traversal Prevention
- [ ] File paths are validated (no ../ sequences)
- [ ] Absolute paths are used internally
- [ ] File access is restricted to specific directories
- [ ] Symlinks are resolved and validated
- [ ] Chroot/sandbox is used where appropriate

## Data Protection

### Encryption at Rest
- [ ] Sensitive data is encrypted in database
- [ ] Encryption keys are stored securely (not in code)
- [ ] Strong encryption algorithms used (AES-256, RSA-2048+)
- [ ] Encryption keys are rotated periodically
- [ ] Backups are encrypted
- [ ] Database field-level encryption for PII
- [ ] Full-disk encryption for storage volumes

### Encryption in Transit
- [ ] All network traffic uses TLS/HTTPS
- [ ] TLS 1.2+ is required (1.0/1.1 disabled)
- [ ] Strong cipher suites configured
- [ ] Certificate validation is enforced
- [ ] Certificate pinning for mobile apps
- [ ] Internal service-to-service communication is encrypted
- [ ] WebSocket connections use WSS

### Secrets Management
- [ ] No secrets hardcoded in source code
- [ ] No secrets in configuration files committed to git
- [ ] Environment variables used for secrets
- [ ] Secrets manager used (AWS Secrets Manager, HashiCorp Vault)
- [ ] API keys rotated regularly
- [ ] Database passwords rotated regularly
- [ ] Secrets are not logged
- [ ] Secrets are not sent to error tracking services

### PII/Sensitive Data
- [ ] PII is identified and classified
- [ ] Data minimization principle followed (collect only what's needed)
- [ ] PII retention policy implemented
- [ ] Data deletion capability exists (GDPR right to erasure)
- [ ] Data export capability exists (GDPR right to portability)
- [ ] Consent management implemented
- [ ] Anonymization/pseudonymization used where appropriate
- [ ] PII access is logged and audited

## Common Vulnerabilities

### Injection Attacks
- [ ] No SQL injection vulnerabilities
- [ ] No command injection vulnerabilities
- [ ] No LDAP injection vulnerabilities
- [ ] No XML/XPath injection vulnerabilities
- [ ] No template injection vulnerabilities
- [ ] No NoSQL injection vulnerabilities

### Cross-Site Attacks
- [ ] No Cross-Site Scripting (XSS) vulnerabilities
- [ ] No Cross-Site Request Forgery (CSRF) vulnerabilities
- [ ] CSRF tokens implemented for state-changing operations
- [ ] SameSite cookie attribute set appropriately
- [ ] Origin validation for CORS
- [ ] No clickjacking vulnerabilities (X-Frame-Options header)

### Insecure Deserialization
- [ ] Deserialization only from trusted sources
- [ ] Type validation before deserialization
- [ ] Avoid pickle (Python), ObjectInputStream (Java) with user data
- [ ] Use safe serialization formats (JSON, protobuf)
- [ ] Signature verification for serialized data

### XXE (XML External Entity)
- [ ] XML parsing disables external entities
- [ ] XML parsing disables DTD processing
- [ ] Safe XML parsers configured correctly
- [ ] Avoid XML where JSON suffices

### Open Redirect
- [ ] Redirect URLs are validated
- [ ] Whitelist of allowed redirect destinations
- [ ] No user-controlled redirect parameters
- [ ] Referrer header checked for sensitive redirects

### Server-Side Request Forgery (SSRF)
- [ ] User-provided URLs are validated
- [ ] Whitelist of allowed protocols/hosts
- [ ] Internal IP ranges blocked (127.0.0.1, 169.254.x.x, etc.)
- [ ] DNS rebinding protection
- [ ] Timeout for external requests

## Dependencies & Supply Chain

### Dependency Management
- [ ] All dependencies are up-to-date
- [ ] No known vulnerabilities (npm audit, pip-audit, cargo audit)
- [ ] Dependency versions are pinned
- [ ] Transitive dependencies reviewed
- [ ] Dependencies have active maintenance
- [ ] Licenses are compatible with project
- [ ] Private package registry used for internal packages
- [ ] Dependency confusion attacks prevented

### Container Security
- [ ] Base images are minimal and up-to-date
- [ ] Containers run as non-root user
- [ ] Container images scanned for vulnerabilities (Trivy, Snyk)
- [ ] Multi-stage builds used to minimize image size
- [ ] Secrets not baked into images
- [ ] Container registry is private and secured

## Configuration & Deployment

### Security Headers
- [ ] Content-Security-Policy header set
- [ ] X-Frame-Options header set (DENY or SAMEORIGIN)
- [ ] X-Content-Type-Options: nosniff header set
- [ ] Strict-Transport-Security header set (HSTS)
- [ ] Referrer-Policy header set appropriately
- [ ] Permissions-Policy header set
- [ ] X-XSS-Protection header set (legacy browsers)

### CORS Configuration
- [ ] CORS is not wildcard (*) in production
- [ ] Allowed origins are whitelisted
- [ ] Credentials are handled securely
- [ ] Preflight requests handled correctly

### Error Handling
- [ ] Stack traces not exposed to users
- [ ] Error messages don't leak system information
- [ ] Generic error messages for authentication failures
- [ ] Detailed errors logged server-side only
- [ ] 404 vs 403 used appropriately (no information disclosure)

### Logging & Monitoring
- [ ] Security events are logged (login, logout, access denied)
- [ ] Logs don't contain sensitive information (passwords, tokens, PII)
- [ ] Logs are centralized and monitored
- [ ] Anomaly detection configured
- [ ] Alerting configured for security events
- [ ] Log retention policy defined

## Rate Limiting & DoS Protection

### Rate Limiting
- [ ] API endpoints have rate limits
- [ ] Login endpoints have stricter rate limits
- [ ] Rate limits are per-user and per-IP
- [ ] Rate limit headers returned (X-RateLimit-*)
- [ ] Rate limiting uses token bucket or leaky bucket algorithm
- [ ] Redis or similar for distributed rate limiting

### DoS Protection
- [ ] Request size limits enforced
- [ ] Request timeout configured
- [ ] Connection limits configured
- [ ] Expensive operations are async or queued
- [ ] CDN/WAF used for DDoS protection
- [ ] Circuit breaker pattern for external dependencies

## Mobile & API Specific

### Mobile Apps
- [ ] Certificate pinning implemented
- [ ] Secrets not stored in app binary
- [ ] Local data encrypted (Keychain, KeyStore)
- [ ] Jailbreak/root detection considered
- [ ] Code obfuscation used
- [ ] App transport security configured

### API Security
- [ ] API versioning implemented
- [ ] API documentation accurate and complete
- [ ] Deprecated endpoints removed or disabled
- [ ] API keys have expiration
- [ ] Webhook signatures verified
- [ ] GraphQL query depth limited
- [ ] GraphQL introspection disabled in production

## Compliance & Privacy

### GDPR (if applicable)
- [ ] Data processing legal basis documented
- [ ] Consent management implemented
- [ ] Right to access implemented
- [ ] Right to erasure implemented
- [ ] Right to portability implemented
- [ ] Data breach notification process defined
- [ ] Privacy policy accurate and accessible

### PCI-DSS (if handling payment cards)
- [ ] Credit card data not stored (use tokenization)
- [ ] PCI-compliant payment processor used
- [ ] Cardholder data environment (CDE) segmented
- [ ] Strong cryptography used
- [ ] Access to cardholder data logged

### HIPAA (if handling health data)
- [ ] PHI identified and protected
- [ ] Encryption at rest and in transit
- [ ] Access controls implemented
- [ ] Audit logging enabled
- [ ] Business associate agreements in place

## Incident Response

### Preparedness
- [ ] Security incident response plan exists
- [ ] Incident response team identified
- [ ] Escalation procedures documented
- [ ] Contact information up-to-date
- [ ] Runbooks for common security scenarios

### Detection
- [ ] Security monitoring configured
- [ ] Intrusion detection system (IDS) in place
- [ ] Log aggregation and analysis
- [ ] Alerting on suspicious activity
- [ ] Regular security audits scheduled

### Response
- [ ] Ability to disable compromised accounts
- [ ] Ability to rotate secrets quickly
- [ ] Ability to rollback deployments
- [ ] Backup and recovery tested
- [ ] Communication plan for security incidents

---

## Critical Security Checklist (Quick Reference)

Use this abbreviated checklist for fast security verification:

- [ ] Authentication on all protected endpoints
- [ ] Authorization checked for every privileged action
- [ ] All input validated (SQL, XSS, command injection)
- [ ] Secrets not in code (use environment variables)
- [ ] HTTPS everywhere (TLS 1.2+)
- [ ] CSRF protection on state-changing operations
- [ ] No sensitive data in logs
- [ ] Dependencies have no known vulnerabilities
- [ ] Rate limiting on public endpoints
- [ ] Security headers configured

---

## Severity Assessment

**CRITICAL (Block Merge)**:
- SQL injection, XSS, command injection vulnerabilities
- Authentication bypass
- Hardcoded secrets
- No authorization checks on sensitive operations
- Insecure deserialization of user data

**HIGH (Fix Before Merge)**:
- Missing CSRF protection
- Weak encryption (MD5, SHA1, DES)
- PII not encrypted at rest
- No rate limiting on authentication
- Known high-severity CVEs in dependencies

**MEDIUM (Fix Soon)**:
- Missing security headers
- Verbose error messages
- No input validation on non-critical fields
- Missing audit logging
- Known medium-severity CVEs

**LOW (Nice to Have)**:
- Missing documentation
- Non-optimal configuration
- Known low-severity CVEs
- Code quality issues affecting security indirectly

---

**Reviewer:** _____________
**Date:** _____________
**Result:** ⚪ Pass / 🔴 Fail / 🟡 Conditional Pass
