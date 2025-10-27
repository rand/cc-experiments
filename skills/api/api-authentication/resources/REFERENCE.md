# API Authentication Reference

Comprehensive technical reference for JWT, OAuth 2.0, and API authentication specifications.

## Table of Contents

1. [JWT Specification (RFC 7519)](#jwt-specification-rfc-7519)
2. [OAuth 2.0 Framework (RFC 6749)](#oauth-20-framework-rfc-6749)
3. [PKCE Extension (RFC 7636)](#pkce-extension-rfc-7636)
4. [Token Storage Best Practices](#token-storage-best-practices)
5. [Security Considerations](#security-considerations)
6. [Attack Vectors and Mitigations](#attack-vectors-and-mitigations)
7. [Password Hashing Algorithms](#password-hashing-algorithms)
8. [Implementation Checklist](#implementation-checklist)

---

## JWT Specification (RFC 7519)

### Overview

JSON Web Token (JWT) is a compact, URL-safe means of representing claims to be transferred between two parties. The claims in a JWT are encoded as a JSON object that is used as the payload of a JSON Web Signature (JWS) structure or as the plaintext of a JSON Web Encryption (JWE) structure.

**Specification**: [RFC 7519](https://tools.ietf.org/html/rfc7519)

### JWT Structure

```
BASE64URL(HEADER).BASE64URL(PAYLOAD).BASE64URL(SIGNATURE)
```

**Example**:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

### Header Parameters

**Required**:
- `alg`: Algorithm used for signing (MUST be validated)
- `typ`: Token type (typically "JWT")

**Optional**:
- `kid`: Key ID hint indicating which key was used
- `cty`: Content type (only used for nested JWTs)

**Algorithms**:
```
HMAC:
  HS256 (HMAC with SHA-256) - Symmetric
  HS384 (HMAC with SHA-384) - Symmetric
  HS512 (HMAC with SHA-512) - Symmetric

RSA:
  RS256 (RSA with SHA-256) - Asymmetric
  RS384 (RSA with SHA-384) - Asymmetric
  RS512 (RSA with SHA-512) - Asymmetric

ECDSA:
  ES256 (ECDSA with P-256 and SHA-256) - Asymmetric
  ES384 (ECDSA with P-384 and SHA-384) - Asymmetric
  ES512 (ECDSA with P-521 and SHA-512) - Asymmetric

None:
  none (Unsecured JWT) - DANGEROUS, NEVER USE IN PRODUCTION
```

### Registered Claims (Payload)

**Standard claims per RFC 7519**:

| Claim | Name | Type | Description |
|-------|------|------|-------------|
| `iss` | Issuer | String | Principal that issued the JWT |
| `sub` | Subject | String | Principal that is the subject (user ID) |
| `aud` | Audience | String/Array | Recipients that the JWT is intended for |
| `exp` | Expiration Time | NumericDate | Expiration time after which JWT is invalid |
| `nbf` | Not Before | NumericDate | Time before which JWT is invalid |
| `iat` | Issued At | NumericDate | Time at which JWT was issued |
| `jti` | JWT ID | String | Unique identifier for the JWT |

**NumericDate**: JSON numeric value representing seconds since Unix epoch (1970-01-01T00:00:00Z UTC)

**Example Payload**:
```json
{
  "iss": "https://auth.example.com",
  "sub": "user_12345",
  "aud": ["https://api.example.com", "https://app.example.com"],
  "exp": 1735689600,
  "nbf": 1735686000,
  "iat": 1735686000,
  "jti": "unique-token-id-123",
  "custom_claim": "custom_value"
}
```

### Signature Verification

**HMAC (HS256)**:
```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret
)
```

**RSA (RS256)**:
```
RSASSA-PKCS1-v1_5 using SHA-256
```

**ECDSA (ES256)**:
```
ECDSA using P-256 curve and SHA-256
```

### Security Requirements

**MUST**:
- Validate signature before trusting claims
- Validate `exp` claim (reject expired tokens)
- Validate `iss` claim matches expected issuer
- Validate `aud` claim includes this service
- Reject tokens with `alg: none` in production
- Use secure random key generation (256+ bits)

**SHOULD**:
- Validate `nbf` claim (not before time)
- Validate `iat` claim (issued at time)
- Implement clock skew tolerance (±5 minutes)
- Use RS256 for microservices (no shared secret)
- Keep tokens short-lived (15 minutes to 1 hour)

**MUST NOT**:
- Store sensitive data in payload (it's readable)
- Trust token without signature validation
- Use weak keys (<256 bits for HMAC)
- Share private keys between services

---

## OAuth 2.0 Framework (RFC 6749)

### Overview

OAuth 2.0 is an authorization framework that enables applications to obtain limited access to user accounts on an HTTP service. It works by delegating user authentication to the service that hosts the user account and authorizing third-party applications to access that account.

**Specification**: [RFC 6749](https://tools.ietf.org/html/rfc6749)

### Roles

1. **Resource Owner**: User who owns the data
2. **Resource Server**: API serving protected resources
3. **Client**: Application requesting access
4. **Authorization Server**: Issues access tokens

### Grant Types

#### 1. Authorization Code Flow (Most Secure)

**Use case**: Web applications with server-side backend

**Flow**:
```
+----------+
| Resource |
|   Owner  |
|          |
+----------+
     v
     |
    (A) User authorizes client
     |
     v
+-----------+          Client Identifier      +---------------+
|           +----(A)-- & Redirection URI ---->|               |
|  User-    |                                  | Authorization |
|  Agent    +<---(B)-- Authorization Code ----+    Server     |
|           |                                  |               |
+-----------+          Authorization Code     +---------------+
                       & Redirection URI
     |                                              ^      v
     |                                              |     (C)
    (B)                                            (D)
     v                                              |
+-----------+                                  +---------------+
|           +---(C)-- Authorization Code ----->|               |
|  Client   |          & Client Credentials    |  Token        |
|           +<---(D)----- Access Token --------+  Endpoint     |
|           |         (& Refresh Token)        |               |
+-----------+                                  +---------------+
```

**Request Parameters**:
- `response_type=code` (required)
- `client_id` (required)
- `redirect_uri` (required)
- `scope` (optional)
- `state` (recommended for CSRF protection)

**Token Request**:
```http
POST /oauth/token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=AUTHORIZATION_CODE&
redirect_uri=https://client.example.com/callback&
client_id=CLIENT_ID&
client_secret=CLIENT_SECRET
```

#### 2. Client Credentials Flow

**Use case**: Server-to-server authentication (no user involved)

**Request**:
```http
POST /oauth/token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id=CLIENT_ID&
client_secret=CLIENT_SECRET&
scope=read write
```

#### 3. Refresh Token Flow

**Use case**: Obtain new access token without re-authentication

**Request**:
```http
POST /oauth/token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&
refresh_token=REFRESH_TOKEN&
client_id=CLIENT_ID&
client_secret=CLIENT_SECRET
```

### Token Response Format

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",
  "scope": "read write"
}
```

### Token Types

**Bearer Tokens** (RFC 6750):
```http
GET /api/resource HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGci...
```

### Error Responses

```json
{
  "error": "invalid_request",
  "error_description": "The redirect_uri is missing",
  "error_uri": "https://docs.example.com/errors/invalid_request"
}
```

**Error Codes**:
- `invalid_request`: Malformed request
- `invalid_client`: Client authentication failed
- `invalid_grant`: Authorization code/refresh token invalid
- `unauthorized_client`: Client not authorized for this grant type
- `unsupported_grant_type`: Grant type not supported
- `invalid_scope`: Requested scope invalid or exceeds granted scope

---

## PKCE Extension (RFC 7636)

### Overview

Proof Key for Code Exchange (PKCE) is an extension to OAuth 2.0 that prevents authorization code interception attacks for public clients (mobile apps, SPAs).

**Specification**: [RFC 7636](https://tools.ietf.org/html/rfc7636)

### Flow

**1. Client generates code verifier**:
```
code_verifier = high-entropy random string (43-128 characters)
Example: "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
```

**2. Client creates code challenge**:
```
code_challenge = BASE64URL(SHA256(code_verifier))

OR (plain method, less secure):
code_challenge = code_verifier
```

**3. Authorization request includes code challenge**:
```http
GET /authorize?
  response_type=code&
  client_id=CLIENT_ID&
  redirect_uri=https://app.example.com/callback&
  scope=read&
  state=xyz&
  code_challenge=CHALLENGE&
  code_challenge_method=S256
```

**4. Token request includes code verifier**:
```http
POST /token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=AUTHORIZATION_CODE&
redirect_uri=https://app.example.com/callback&
client_id=CLIENT_ID&
code_verifier=VERIFIER
```

**5. Server verifies**:
```
BASE64URL(SHA256(code_verifier)) == code_challenge
```

### When to Use PKCE

**MUST use**:
- Mobile applications
- Single-page applications (SPAs)
- Any public client (cannot securely store client secret)

**SHOULD use**:
- All OAuth 2.0 clients (even confidential clients)

---

## Token Storage Best Practices

### Browser-Based Applications

| Storage | Security | Accessibility | Persistence | Recommendation |
|---------|----------|---------------|-------------|----------------|
| **httpOnly Cookie** | HIGH | Automatic | Yes | RECOMMENDED |
| **Secure Cookie** | MEDIUM | Manual | Yes | Use with CSRF protection |
| **localStorage** | LOW | High | Yes | AVOID (XSS vulnerable) |
| **sessionStorage** | LOW | High | Tab-scoped | AVOID (XSS vulnerable) |
| **Memory (state)** | HIGH | High | No | RECOMMENDED for SPAs |

### Recommended Approach: httpOnly Cookies + CSRF Protection

**Set token in httpOnly cookie**:
```http
Set-Cookie: access_token=JWT_TOKEN;
            HttpOnly;
            Secure;
            SameSite=Strict;
            Max-Age=3600;
            Path=/
```

**Cookie attributes**:
- `HttpOnly`: Prevents JavaScript access (XSS protection)
- `Secure`: HTTPS only
- `SameSite=Strict`: Prevents CSRF attacks
- `Max-Age`: Expiration in seconds
- `Path=/`: Cookie scope

### Mobile Applications

**iOS (Keychain)**:
```swift
import Security

func saveToken(_ token: String) {
    let data = token.data(using: .utf8)!
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrAccount as String: "access_token",
        kSecValueData as String: data
    ]

    SecItemAdd(query as CFDictionary, nil)
}
```

**Android (EncryptedSharedPreferences)**:
```kotlin
import androidx.security.crypto.EncryptedSharedPreferences

val sharedPreferences = EncryptedSharedPreferences.create(
    context,
    "secure_prefs",
    masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
)

sharedPreferences.edit().putString("access_token", token).apply()
```

### Server-Side Storage

**Database schema for refresh tokens**:
```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INT NOT NULL REFERENCES users(id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash
    family_id UUID NOT NULL,  -- For token rotation detection
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    last_used_at TIMESTAMP,
    ip_address INET,
    user_agent TEXT,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_family ON refresh_tokens(family_id);
```

---

## Security Considerations

### JWT Security

**1. Algorithm Confusion Attack**

**Attack**: Change `alg` header from RS256 to HS256, sign with public key

**Mitigation**:
```python
# ALWAYS specify allowed algorithms explicitly
jwt.decode(token, key, algorithms=["RS256"])  # Good
jwt.decode(token, key, algorithms=["HS256", "RS256"])  # Bad
```

**2. None Algorithm Attack**

**Attack**: Set `alg: none` and remove signature

**Mitigation**:
```python
# NEVER allow 'none' algorithm
jwt.decode(token, key, algorithms=["HS256"])  # 'none' rejected
```

**3. Weak Secret Keys**

**Attack**: Brute force weak HMAC secrets

**Mitigation**:
```python
import secrets

# Generate cryptographically secure key (256 bits minimum)
secret = secrets.token_urlsafe(32)  # 32 bytes = 256 bits
```

### OAuth 2.0 Security

**1. Authorization Code Interception**

**Attack**: Intercept authorization code in redirect

**Mitigation**: Use PKCE (RFC 7636)

**2. Redirect URI Manipulation**

**Attack**: Change redirect_uri to attacker-controlled domain

**Mitigation**: Exact string matching on redirect URIs
```python
ALLOWED_REDIRECTS = [
    "https://app.example.com/callback",
    "https://app.example.com/oauth/callback"
]

if redirect_uri not in ALLOWED_REDIRECTS:
    raise ValueError("Invalid redirect URI")
```

**3. State Parameter Missing**

**Attack**: CSRF attack on OAuth flow

**Mitigation**: Always use state parameter
```python
import secrets

# Generate random state
state = secrets.token_urlsafe(32)

# Store in session
session['oauth_state'] = state

# Validate in callback
if request.args.get('state') != session.get('oauth_state'):
    raise ValueError("Invalid state parameter")
```

---

## Attack Vectors and Mitigations

### 1. Cross-Site Scripting (XSS)

**Attack**: Inject JavaScript to steal tokens from localStorage

**Vulnerable**:
```javascript
// Token accessible to JavaScript
localStorage.setItem('token', accessToken);
const stolen = localStorage.getItem('token');
```

**Mitigation**:
```javascript
// Use httpOnly cookies (not accessible to JavaScript)
// OR store in memory only
let accessToken = null;  // Lost on page refresh
```

### 2. Cross-Site Request Forgery (CSRF)

**Attack**: Trick user into making authenticated requests

**Vulnerable**:
```http
POST /api/transfer HTTP/1.1
Cookie: session_id=abc123
Content-Type: application/json

{"to": "attacker", "amount": 1000}
```

**Mitigation**:
```python
# Use SameSite cookies
response.set_cookie(
    'access_token',
    token,
    samesite='Strict',  # or 'Lax'
    httponly=True,
    secure=True
)

# OR use CSRF tokens
csrf_token = secrets.token_urlsafe(32)
session['csrf_token'] = csrf_token
```

### 3. Token Replay Attack

**Attack**: Reuse stolen/intercepted token

**Mitigation**:
- Short token expiration (15 minutes)
- Bind tokens to client IP/fingerprint
- Implement token blacklist for revocation

### 4. JWT Injection

**Attack**: Inject malicious claims into payload

**Vulnerable**:
```python
# User-controlled data in token
token = jwt.encode({"role": request.json['role']}, secret)
```

**Mitigation**:
```python
# Validate and sanitize inputs
allowed_roles = ['user', 'admin', 'moderator']
role = request.json['role'] if request.json['role'] in allowed_roles else 'user'
token = jwt.encode({"role": role}, secret)
```

### 5. Session Fixation

**Attack**: Force user to use attacker's session ID

**Mitigation**:
```python
# Regenerate session ID after login
from flask import session

@app.route('/login', methods=['POST'])
def login():
    # Authenticate user
    user = authenticate(request.json['email'], request.json['password'])

    # Regenerate session ID
    session.clear()
    session.regenerate()

    # Set new session data
    session['user_id'] = user.id
```

---

## Password Hashing Algorithms

### Comparison

| Algorithm | Year | Security | Speed | Memory | Recommendation |
|-----------|------|----------|-------|--------|----------------|
| **MD5** | 1992 | BROKEN | Fast | Low | NEVER USE |
| **SHA-1** | 1995 | BROKEN | Fast | Low | NEVER USE |
| **SHA-256** | 2001 | Weak | Fast | Low | NOT FOR PASSWORDS |
| **bcrypt** | 1999 | GOOD | Tunable | Low | RECOMMENDED |
| **scrypt** | 2009 | BETTER | Tunable | Tunable | RECOMMENDED |
| **Argon2** | 2015 | BEST | Tunable | Tunable | HIGHLY RECOMMENDED |
| **PBKDF2** | 2000 | OK | Tunable | Low | ACCEPTABLE |

### Argon2 (Winner of Password Hashing Competition 2015)

**Variants**:
- **Argon2d**: Maximizes resistance to GPU attacks (data-dependent)
- **Argon2i**: Maximizes resistance to side-channel attacks (data-independent)
- **Argon2id**: Hybrid approach (RECOMMENDED)

**Parameters**:
- `time_cost`: Number of iterations (3-10)
- `memory_cost`: Memory in KiB (65536 = 64MB)
- `parallelism`: Number of threads (4-8)

**Implementation**:
```python
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,        # Iterations
    memory_cost=65536,  # 64 MB
    parallelism=4,      # 4 threads
    hash_len=32,        # 32 bytes output
    salt_len=16         # 16 bytes salt
)

# Hash password
hash = ph.hash("user_password")

# Verify password
try:
    ph.verify(hash, "user_password")
    print("Password valid")
except:
    print("Password invalid")

# Check if rehashing needed (params changed)
if ph.check_needs_rehash(hash):
    hash = ph.hash("user_password")
```

### bcrypt

**Cost factor**: 2^cost iterations (10-14 recommended, 12 is good default)

**Implementation**:
```python
import bcrypt

# Hash password
password = b"user_password"
salt = bcrypt.gensalt(rounds=12)  # 2^12 = 4096 iterations
hash = bcrypt.hashpw(password, salt)

# Verify password
if bcrypt.checkpw(password, hash):
    print("Password valid")
```

### Performance Benchmark

**Target**: 250-500ms hashing time on your hardware

```python
import time
from argon2 import PasswordHasher

def benchmark_hashing(algorithm, password, iterations=100):
    start = time.time()

    for _ in range(iterations):
        if algorithm == 'argon2':
            ph = PasswordHasher()
            hash = ph.hash(password)
        elif algorithm == 'bcrypt':
            import bcrypt
            hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    elapsed = time.time() - start
    avg_time = (elapsed / iterations) * 1000  # ms

    print(f"{algorithm}: {avg_time:.2f}ms per hash")

benchmark_hashing('argon2', 'test_password')
benchmark_hashing('bcrypt', 'test_password')
```

---

## Implementation Checklist

### JWT Implementation

- [ ] Use RS256 for microservices (asymmetric)
- [ ] Use HS256 for monoliths (symmetric, if key secure)
- [ ] Set expiration time (exp claim, 15-60 minutes)
- [ ] Validate signature before trusting claims
- [ ] Validate iss (issuer) claim
- [ ] Validate aud (audience) claim
- [ ] Validate exp (expiration) claim
- [ ] Implement clock skew tolerance (±5 minutes)
- [ ] Use strong secret keys (256+ bits)
- [ ] Never store sensitive data in payload
- [ ] Explicitly specify allowed algorithms
- [ ] Reject 'none' algorithm

### OAuth 2.0 Implementation

- [ ] Use Authorization Code Flow for web apps
- [ ] Use PKCE for mobile apps and SPAs
- [ ] Validate redirect_uri (exact match)
- [ ] Use state parameter (CSRF protection)
- [ ] Short-lived access tokens (5-15 minutes)
- [ ] Long-lived refresh tokens (days to months)
- [ ] Implement refresh token rotation
- [ ] Store refresh tokens hashed in database
- [ ] Revoke refresh tokens on logout
- [ ] Implement token family tracking (detect theft)
- [ ] Use HTTPS everywhere
- [ ] Validate scope claims

### API Key Implementation

- [ ] Generate cryptographically secure keys (256+ bits)
- [ ] Store keys hashed (SHA-256 minimum)
- [ ] Implement rate limiting per key
- [ ] Support key revocation
- [ ] Set expiration dates
- [ ] Log key usage for audit
- [ ] Use HTTPS only
- [ ] Never expose keys in URLs
- [ ] Use custom headers (X-API-Key)
- [ ] Implement key rotation

### General Security

- [ ] Use HTTPS everywhere (TLS 1.2+)
- [ ] Implement rate limiting
- [ ] Log authentication attempts
- [ ] Detect and block brute force attacks
- [ ] Implement account lockout after failed attempts
- [ ] Use secure password hashing (Argon2id)
- [ ] Implement MFA for sensitive operations
- [ ] Validate all inputs
- [ ] Use CORS appropriately
- [ ] Set security headers (CSP, HSTS, etc.)
- [ ] Regular security audits
- [ ] Dependency vulnerability scanning

---

## References

- [RFC 7519 - JSON Web Token (JWT)](https://tools.ietf.org/html/rfc7519)
- [RFC 6749 - OAuth 2.0 Authorization Framework](https://tools.ietf.org/html/rfc6749)
- [RFC 6750 - OAuth 2.0 Bearer Token Usage](https://tools.ietf.org/html/rfc6750)
- [RFC 7636 - Proof Key for Code Exchange (PKCE)](https://tools.ietf.org/html/rfc7636)
- [RFC 7517 - JSON Web Key (JWK)](https://tools.ietf.org/html/rfc7517)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [Argon2 Specification](https://github.com/P-H-C/phc-winner-argon2/blob/master/argon2-specs.pdf)

---

**Last Updated**: 2025-10-27
**Version**: 1.0
