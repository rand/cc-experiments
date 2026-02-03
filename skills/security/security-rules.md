---
name: security-security-rules
description: 40+ opinionated secure coding rules covering input validation, authentication, secrets management, and common vulnerabilities. Actionable best practices.
---

# Secure Coding Rules

Opinionated, high-density rules for writing secure application code. Language-agnostic where possible, with concrete examples. These are prescriptive — follow them unless you have a specific, articulated reason not to. Not a tutorial; assumes working development knowledge.

---

## Input Validation

**1. Validate all external input.**
Every HTTP parameter, header, body field, file upload, webhook payload, and queue message is untrusted. Validate type, format, range, and length before processing.

**2. Allowlist over denylist.**
Define what's permitted, reject everything else. Denylist approaches miss novel attack patterns.

```python
# Bad: denylist
if "<script>" not in user_input:  # trivially bypassed
    process(user_input)

# Good: allowlist
if re.match(r'^[a-zA-Z0-9_-]{1,50}$', username):
    process(username)
```

**3. Validate on the server, always.**
Client-side validation is UX. Server-side validation is security. Attackers bypass your frontend entirely.

**4. Sanitize for the output context.**
HTML context needs HTML encoding. SQL context needs parameterization. URL context needs URL encoding. Shell context needs shell escaping. There is no universal "sanitize" function.

**5. Set size limits on everything.**
Request body size, file upload size, string field lengths, array lengths, JSON nesting depth. Unbounded input is a denial-of-service vector.

```python
# Limit request body
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

# Limit field lengths in schema
username: str = Field(max_length=50)
bio: str = Field(max_length=500)
```

**6. Reject unknown fields in strict mode.**
Extra fields in JSON payloads can exploit mass-assignment vulnerabilities. Parse with strict schemas that reject unexpected keys.

```python
# Pydantic
class UserCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str
    email: str
```

---

## Authentication

**7. Hash passwords with bcrypt or argon2.**
Never MD5, SHA-256, or any fast hash for passwords. Use bcrypt (cost 12+) or argon2id. The whole point is being slow.

```python
# Good
from passlib.hash import argon2
hashed = argon2.hash(password)
argon2.verify(password, hashed)
```

**8. Use constant-time comparison for secrets.**
Comparing tokens, API keys, or hashes with `==` leaks timing information. Use `hmac.compare_digest` or equivalent.

```python
import hmac
if hmac.compare_digest(provided_token, stored_token):
    grant_access()
```

**9. Rate limit login attempts.**
5 attempts per account per 15 minutes. Lock the account or add CAPTCHA after threshold. Exponential backoff on failure. Log every failed attempt.

**10. Configure sessions securely.**
`HttpOnly`, `Secure`, `SameSite=Lax` (minimum). Short expiration (hours, not weeks). Regenerate session ID after login. Invalidate on logout server-side.

```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 3600  # 1 hour
```

**11. Implement token rotation.**
Refresh tokens should be single-use. Issue a new refresh token with every access token refresh. Detect reuse — if a refresh token is used twice, revoke the entire family.

**12. Require MFA for sensitive operations.**
Password changes, payment methods, role changes, API key generation — require step-up authentication even for already-authenticated users.

---

## Secrets Management

**13. Never log secrets.**
Scrub API keys, tokens, passwords, and PII from log output. Use structured logging with explicit field selection — never log raw request/response bodies.

```python
# Bad
logger.info(f"Request: {request.headers}")  # may contain Authorization

# Good
logger.info("Request received", extra={"path": request.path, "method": request.method})
```

**14. Never commit secrets to version control.**
Use `.gitignore` for `.env` files. Use pre-commit hooks (e.g., `detect-secrets`, `gitleaks`) to catch accidental commits. If a secret is committed, rotate it immediately — don't just delete it from history.

**15. Rotate secrets regularly.**
API keys, database passwords, signing keys — rotate on a schedule (90 days max). Automate rotation. Support dual-read during rotation windows.

**16. Use environment variables or a secrets vault.**
Secrets in code or config files get committed, copied, and leaked. Use env vars for simple setups, HashiCorp Vault / AWS Secrets Manager / 1Password CLI for production.

**17. Use different secrets per environment.**
Dev, staging, and production must use completely separate credentials. A leaked dev secret should never grant production access.

---

## HTTP Security

**18. Set security headers on every response.**
At minimum:
```
Content-Security-Policy: default-src 'self'
Strict-Transport-Security: max-age=63072000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

**19. Enforce HTTPS everywhere.**
No mixed content. No HTTP fallbacks. HSTS with long max-age. Redirect HTTP to HTTPS at the load balancer. Include `Secure` flag on all cookies.

**20. Set `SameSite` on all cookies.**
`SameSite=Lax` is the minimum. Use `Strict` for authentication cookies. `None` only when cross-site is genuinely required (and always with `Secure`).

**21. Allowlist CORS origins explicitly.**
Never `Access-Control-Allow-Origin: *` on authenticated endpoints. Maintain an explicit list of permitted origins. Validate the `Origin` header against the list.

**22. Never put sensitive data in URLs.**
Tokens, API keys, session IDs, PII — none of these belong in query strings. They leak via logs, referrer headers, browser history, and proxy caches. Use headers or POST bodies.

---

## Injection Prevention

**23. Use parameterized queries — no exceptions.**
This is the only reliable defense against SQL injection. ORMs use them by default; raw queries must use bind parameters. Never concatenate user input into SQL.

**24. Escape output for its rendering context.**
HTML → HTML-encode. JavaScript → JS-encode. CSS → CSS-encode. URLs → URL-encode. Use your framework's auto-escaping — don't disable it.

**25. Deploy Content Security Policy to mitigate XSS.**
Start with `default-src 'self'`. Add specific directives as needed. Never use `unsafe-inline` or `unsafe-eval` in production. Use nonces for inline scripts.

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-abc123'; style-src 'self' 'unsafe-inline'
```

**26. Never pass user input to eval, exec, or shell commands.**
No `eval()`, `exec()`, `os.system()`, or backtick execution with user-controlled strings. If you must run a subprocess, use an explicit argument list — never a shell string.

```python
# Bad
os.system(f"convert {user_filename} output.png")

# Good
subprocess.run(["convert", user_filename, "output.png"], shell=False)
```

**27. Validate file uploads rigorously.**
Check MIME type by content (magic bytes), not just extension or Content-Type header. Limit file size. Store outside webroot. Generate new filenames — never use the user-provided name for storage paths.

---

## Access Control

**28. Default deny.**
Start with no permissions. Explicitly grant access. If the authorization check is missing, the answer is "no."

**29. Check authorization on every request.**
Not just on the first request. Not just on the frontend. Every API endpoint, every server action, every GraphQL resolver checks "is this user allowed to do this to this resource?"

**30. Never rely on client-side access control.**
Hiding a button is not security. If the API endpoint exists, someone will call it. Enforce permissions server-side.

**31. Use framework middleware for auth checks.**
Don't sprinkle auth checks inside handler functions — they get forgotten. Use middleware, decorators, or guards that run before the handler.

```python
# Bad: manual check in every handler
@app.route('/admin/users')
def admin_users():
    if not current_user.is_admin:  # easy to forget
        abort(403)

# Good: decorator/middleware
@app.route('/admin/users')
@require_role('admin')
def admin_users():
    ...
```

**32. Log all access control failures.**
Every 401 and 403 should be logged with user identity, resource, action, and timestamp. Alert on anomalous patterns (bulk 403s from one user, after-hours access).

---

## Dependencies

**33. Audit dependencies regularly.**
Run `npm audit`, `pip-audit`, `cargo audit`, or equivalent in CI. Block merges with known high/critical vulnerabilities.

**34. Pin dependency versions.**
Use lockfiles (`package-lock.json`, `poetry.lock`, `Cargo.lock`). Pin exact versions in production. A surprise update shouldn't break or compromise your app.

**35. Use minimal dependencies.**
Every dependency is attack surface. Before adding a package, check: maintenance status, download count, known vulnerabilities, transitive dependency count. Can you write the 20 lines yourself?

**36. Monitor CVEs for your stack.**
Subscribe to security advisories for your language, framework, and critical dependencies. Use Dependabot, Renovate, or Snyk for automated alerts.

---

## Logging & Monitoring

**37. Log all security-relevant events.**
Authentication successes and failures, authorization failures, input validation failures, privilege changes, password resets, API key creation/rotation, admin actions. If it matters for security, log it.

**38. Use structured logging.**
JSON-formatted logs with consistent fields: `timestamp`, `level`, `event`, `user_id`, `ip`, `action`, `resource`. Structured logs are searchable and alertable.

```json
{
  "timestamp": "2024-01-15T09:30:00Z",
  "level": "warn",
  "event": "auth_failure",
  "user_id": "user-123",
  "ip": "192.168.1.1",
  "reason": "invalid_password",
  "attempt_count": 3
}
```

**39. Never log PII or secrets.**
No passwords, tokens, credit card numbers, SSNs, or full email addresses in logs. Mask or hash sensitive fields. Treat logs as eventually-public.

**40. Make logs tamper-evident.**
Ship logs to a centralized, append-only system (not the same server as the application). If an attacker compromises the app server, they shouldn't be able to erase their tracks.

**41. Alert on security anomalies.**
Set up alerts for: burst of auth failures, access from new geolocations, privilege escalation, unusual API patterns, dependency vulnerability discoveries. Detection speed is everything.

**42. Implement request tracing.**
Assign a unique request ID at the edge and propagate it through all services and logs. When investigating an incident, trace the full request path.

```
X-Request-ID: req_abc123def456
```
