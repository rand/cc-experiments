# Security Skills

Comprehensive skills for application security, vulnerability assessment, and security best practices.

## Category Overview

**Total Skills**: 6
**Focus**: Authentication, Authorization, Input Validation, Security Headers, Vulnerability Assessment, Secrets Management
**Use Cases**: Secure application development, security audits, OWASP compliance, penetration testing, secrets handling

## Skills in This Category

### authentication.md
**Description**: Authentication patterns including JWT, OAuth2, sessions, and multi-factor authentication
**Lines**: ~380
**Use When**:
- Implementing user login and authentication systems
- Choosing authentication strategies (JWT, OAuth2, sessions, API keys)
- Securing user credentials and password management
- Implementing multi-factor authentication (MFA/2FA)
- Designing session management systems
- Preventing authentication bypass vulnerabilities
- Migrating authentication systems

**Key Concepts**: Password hashing (bcrypt, Argon2), JWT, OAuth 2.0, sessions, MFA/TOTP, password reset flows, account lockout, credential stuffing prevention

---

### authorization.md
**Description**: Authorization models including RBAC, ABAC, policy engines, and access control
**Lines**: ~360
**Use When**:
- Implementing access control systems
- Designing role-based or attribute-based authorization
- Building permission systems for multi-tenant applications
- Implementing policy engines (OPA, Casbin)
- Securing API endpoints and resources
- Preventing privilege escalation vulnerabilities
- Auditing access control decisions

**Key Concepts**: RBAC (Role-Based Access Control), ABAC (Attribute-Based Access Control), policy engines, permissions, ownership checks, row-level security, IDOR prevention

---

### input-validation.md
**Description**: Input validation and sanitization to prevent SQL injection, XSS, and command injection
**Lines**: ~400
**Use When**:
- Processing user input in web applications or APIs
- Preventing SQL injection, XSS, or command injection attacks
- Validating and sanitizing form data
- Building input validation schemas
- Implementing file upload security
- Preventing path traversal attacks
- Designing secure data processing pipelines

**Key Concepts**: SQL injection prevention (parameterized queries), XSS prevention (escaping, CSP), command injection prevention, path traversal, file upload security, schema validation (Pydantic)

---

### security-headers.md
**Description**: HTTP security headers including CSP, HSTS, X-Frame-Options, and CORS
**Lines**: ~350
**Use When**:
- Hardening web application security
- Preventing clickjacking, XSS, and MITM attacks
- Configuring Content Security Policy (CSP)
- Setting up CORS for APIs
- Implementing HTTPS enforcement (HSTS)
- Protecting against browser-based attacks
- Passing security audits and penetration tests

**Key Concepts**: Content Security Policy (CSP), HSTS (HTTP Strict Transport Security), X-Frame-Options, CORS, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, CSP nonces

---

### vulnerability-assessment.md
**Description**: Security testing methodologies, OWASP Top 10, vulnerability scanning, and pentesting
**Lines**: ~390
**Use When**:
- Performing security audits of applications
- Testing for OWASP Top 10 vulnerabilities
- Setting up automated security scanning
- Conducting penetration testing
- Reviewing code for security issues
- Preparing for security certifications
- Implementing DevSecOps practices

**Key Concepts**: OWASP Top 10 (2021), SAST (static analysis), DAST (dynamic analysis), SCA (dependency scanning), penetration testing, security tools (Bandit, Semgrep, ZAP, Trivy), CI/CD security integration

---

### secrets-management.md
**Description**: Secrets handling including vaults, environment variables, and key rotation
**Lines**: ~380
**Use When**:
- Storing API keys, passwords, or credentials
- Implementing secrets management for applications
- Integrating with HashiCorp Vault, AWS Secrets Manager, or GCP Secret Manager
- Rotating encryption keys or credentials
- Managing secrets in CI/CD pipelines
- Preventing credential exposure in code or logs
- Designing multi-environment secret strategies

**Key Concepts**: HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager, environment variables, key rotation, dynamic credentials, secrets in CI/CD, zero-downtime rotation

---

## Common Workflows

### Secure Web Application
**Goal**: Implement comprehensive security for web app

**Sequence**:
1. `authentication.md` - Implement user authentication (sessions or JWT)
2. `authorization.md` - Add role-based access control
3. `input-validation.md` - Validate and sanitize all inputs
4. `security-headers.md` - Configure security headers (CSP, HSTS)
5. `secrets-management.md` - Secure API keys and credentials
6. `vulnerability-assessment.md` - Test for vulnerabilities

**Example**: E-commerce web application with user accounts and payments

---

### API Security Hardening
**Goal**: Secure REST or GraphQL API

**Sequence**:
1. `authentication.md` - Implement JWT or OAuth2 authentication
2. `authorization.md` - Add API access control and rate limiting
3. `input-validation.md` - Validate request payloads
4. `security-headers.md` - Configure CORS and security headers
5. `secrets-management.md` - Manage API keys securely
6. `vulnerability-assessment.md` - Scan for API vulnerabilities

**Example**: Public API for third-party integrations

---

### Security Audit
**Goal**: Comprehensive security assessment

**Sequence**:
1. `vulnerability-assessment.md` - Run automated scans (SAST/DAST)
2. `input-validation.md` - Test for injection vulnerabilities
3. `authentication.md` - Audit authentication mechanisms
4. `authorization.md` - Test access control bypass
5. `security-headers.md` - Verify security headers
6. `secrets-management.md` - Check for exposed secrets

**Example**: Pre-production security review

---

### OWASP Top 10 Compliance
**Goal**: Address OWASP Top 10 vulnerabilities

**Sequence**:
1. `authorization.md` - A01: Broken Access Control
2. `secrets-management.md` - A02: Cryptographic Failures
3. `input-validation.md` - A03: Injection
4. `authentication.md` - A07: Identification and Authentication Failures
5. `security-headers.md` - Misconfiguration (CSP, CORS)
6. `vulnerability-assessment.md` - Test all vulnerabilities

**Example**: Security compliance for regulated industry

---

### DevSecOps Pipeline
**Goal**: Integrate security into CI/CD

**Sequence**:
1. `vulnerability-assessment.md` - Set up SAST/DAST/SCA in pipeline
2. `secrets-management.md` - Configure secrets in GitHub Actions/GitLab CI
3. `input-validation.md` - Run security linters (Bandit, Semgrep)
4. `authorization.md` - Test access control in integration tests
5. `authentication.md` - Validate authentication flows
6. `security-headers.md` - Verify headers in staging

**Example**: Automated security testing on every commit

---

### Multi-Tenant SaaS Security
**Goal**: Secure multi-tenant application

**Sequence**:
1. `authentication.md` - Implement SSO and organization-level auth
2. `authorization.md` - Tenant isolation and row-level security
3. `input-validation.md` - Prevent cross-tenant injection
4. `secrets-management.md` - Per-tenant secrets management
5. `security-headers.md` - Configure CSP for embedded content
6. `vulnerability-assessment.md` - Test tenant isolation

**Example**: B2B SaaS platform with enterprise customers

---

## Skill Combinations

### With API Skills (`discover-api`)
- API authentication (JWT, OAuth2, API keys)
- API authorization (endpoint permissions)
- API rate limiting (abuse prevention)
- API error handling (security error responses)
- API versioning (deprecating insecure endpoints)

**Common combos**:
- `authentication.md` + `api-authentication.md`
- `authorization.md` + `api-authorization.md`
- `input-validation.md` + `api-error-handling.md`

---

### With Database Skills (`discover-database`)
- SQL injection prevention
- Database credential management
- Row-level security (PostgreSQL RLS)
- Connection pooling security
- Database encryption at rest

**Common combos**:
- `input-validation.md` + `database/postgres-schema-design.md`
- `secrets-management.md` + `database/database-connection-pooling.md`
- `authorization.md` + `database/postgres-row-level-security.md`

---

### With Frontend Skills (`discover-frontend`)
- XSS prevention in React/Vue/Angular
- Content Security Policy (CSP) configuration
- Secure cookie handling
- Client-side validation (UX, not security)
- Token storage (localStorage vs httpOnly cookies)

**Common combos**:
- `input-validation.md` + `frontend/react-patterns.md`
- `security-headers.md` + `frontend/react-data-fetching.md`
- `authentication.md` + `frontend/react-state-management.md`

---

### With Infrastructure Skills (`discover-infrastructure`, `discover-cloud`)
- Secrets management in Kubernetes
- Container security scanning
- TLS/SSL certificate management
- Network security (firewalls, security groups)
- WAF (Web Application Firewall) configuration

**Common combos**:
- `secrets-management.md` + `containers/kubernetes-deployment.md`
- `vulnerability-assessment.md` + `cicd/github-actions.md`
- `security-headers.md` + `infrastructure/nginx-config.md`

---

### With Cryptography Skills (`discover-cryptography`)
- Encryption key management
- TLS/SSL implementation
- Data encryption at rest and in transit
- Digital signatures and verification
- Hashing algorithms (passwords, integrity)

**Common combos**:
- `authentication.md` + `cryptography/hashing.md`
- `secrets-management.md` + `cryptography/encryption.md`
- `security-headers.md` + `cryptography/tls-ssl.md`

---

### With Testing Skills (`discover-testing`)
- Security integration tests
- Penetration testing automation
- Fuzz testing for inputs
- Authentication/authorization test coverage
- Security regression tests

**Common combos**:
- `vulnerability-assessment.md` + `testing/integration-testing.md`
- `input-validation.md` + `testing/unit-testing.md`
- `authentication.md` + `testing/e2e-testing.md`

---

## Quick Selection Guide

**Authentication vs Authorization**:
- **Authentication** = "Who are you?" → Login, JWT, OAuth, MFA
- **Authorization** = "What can you do?" → RBAC, permissions, policies

**Input Validation Strategy**:
- Use allowlists (whitelist) over blocklists (blacklist)
- Validate on server-side (never trust client)
- Use parameterized queries (prevent SQL injection)
- Escape output (prevent XSS)
- Validate file types by content, not extension

**Security Headers Priority**:
1. **Content-Security-Policy** - Prevents XSS, injection
2. **Strict-Transport-Security** - Enforces HTTPS
3. **X-Frame-Options** - Prevents clickjacking
4. **X-Content-Type-Options** - Prevents MIME sniffing

**Secrets Management Hierarchy**:
1. **Production**: HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager
2. **Staging**: Vault or cloud secrets manager
3. **Development**: Environment variables + .env files (not committed)
4. **Never**: Hardcoded in code or committed to git

**Vulnerability Testing Approach**:
1. **SAST** (Static): Scan code before deployment
2. **SCA** (Dependencies): Check for vulnerable packages
3. **DAST** (Dynamic): Test running application
4. **Penetration Testing**: Manual security assessment

---

## Loading Skills

All skills are available in the `skills/security/` directory:

```bash
cat skills/security/authentication.md
cat skills/security/authorization.md
cat skills/security/input-validation.md
cat skills/security/security-headers.md
cat skills/security/vulnerability-assessment.md
cat skills/security/secrets-management.md
```

**Pro tip**: Start with authentication and authorization (identity/access), then add input validation and security headers (protection), then implement vulnerability assessment and secrets management (operations).

---

## Security Principles

**Defense in Depth**:
- Multiple layers of security controls
- No single point of failure
- Fail securely (deny by default)

**Principle of Least Privilege**:
- Grant minimum necessary permissions
- Separate admin and user accounts
- Use role-based access control

**Zero Trust Architecture**:
- Verify every request
- Never trust, always verify
- Assume breach mentality

**Security by Design**:
- Consider security from the start
- Threat modeling in design phase
- Regular security reviews

---

**Related Categories**:
- `discover-api` - API authentication and authorization
- `discover-database` - Database security and SQL injection prevention
- `discover-cryptography` - Encryption, hashing, TLS/SSL
- `discover-infrastructure` - Network security, container security
- `discover-testing` - Security testing and penetration tests

---

**Resources**:
- OWASP Top 10: https://owasp.org/Top10/
- OWASP Cheat Sheets: https://cheatsheetseries.owasp.org/
- CWE (Common Weakness Enumeration): https://cwe.mitre.org/
- NIST Cybersecurity Framework: https://www.nist.gov/cyberframework
