---
name: api-api-authentication
description: Implementing API authentication for new services
---



# API Authentication

**Scope**: Authentication strategies, JWT, OAuth 2.0, API keys, token management
**Lines**: ~784
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Implementing API authentication for new services
- Choosing between authentication methods (JWT, OAuth, API keys)
- Securing REST or GraphQL APIs
- Implementing token refresh patterns
- Adding multi-factor authentication (MFA)
- Debugging authentication issues or token validation
- Migrating between authentication strategies

## Core Concepts

### Authentication vs Authorization

**Authentication**: Verifying identity ("Who are you?")
**Authorization**: Verifying permissions ("What can you do?")

**Example**:
```
Authentication: User logs in with email/password → Gets token
Authorization: Token includes role "admin" → Can access admin endpoints
```

---

## Authentication Method Comparison

### Decision Matrix

| Method | Best For | Complexity | Mobile-Friendly | Stateless | Revocable |
|--------|----------|------------|-----------------|-----------|-----------|
| **JWT** | Microservices, mobile apps | Medium | Yes | Yes | No* |
| **OAuth 2.0** | Third-party integrations, delegated access | High | Yes | Yes | Yes |
| **API Keys** | Server-to-server, simple APIs | Low | Limited | Yes | Yes |
| **Sessions** | Traditional web apps | Low | No | No | Yes |

*JWT requires token blacklisting for revocation

### When to Use Each Method

**JWT (JSON Web Tokens)**:
- Microservices architecture (no shared session store)
- Mobile apps (persistent authentication)
- Single-page applications (SPAs)
- Stateless APIs

**OAuth 2.0**:
- Third-party application access ("Sign in with Google")
- Delegated authorization (access user's data without password)
- Multiple clients (web, mobile, desktop)
- Enterprise integrations

**API Keys**:
- Server-to-server communication
- Internal services
- Simple authentication needs
- Rate limiting by client

**Sessions (Cookie-based)**:
- Traditional server-rendered web apps
- Need immediate revocation
- Single domain applications

---

## JWT (JSON Web Tokens)

### Structure

A JWT consists of three Base64-encoded parts separated by dots:

```
header.payload.signature
```

**Example**:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

### Header

Contains token type and signing algorithm:

```json
{
  "alg": "HS256",  // Algorithm (HS256, RS256)
  "typ": "JWT"     // Token type
}
```

**Algorithms**:
- `HS256` (HMAC SHA-256): Symmetric, shared secret
- `RS256` (RSA SHA-256): Asymmetric, public/private key
- `ES256` (ECDSA SHA-256): Asymmetric, elliptic curve

### Payload (Claims)

Contains user data and metadata:

```json
{
  "sub": "1234567890",        // Subject (user ID)
  "name": "John Doe",         // Custom claim
  "email": "john@example.com", // Custom claim
  "role": "admin",            // Custom claim
  "iat": 1516239022,          // Issued at (Unix timestamp)
  "exp": 1516242622,          // Expiration (Unix timestamp)
  "nbf": 1516239022,          // Not before
  "iss": "https://api.example.com", // Issuer
  "aud": "https://app.example.com"  // Audience
}
```

**Standard claims**:
- `sub`: Subject (user identifier)
- `exp`: Expiration time (required for security)
- `iat`: Issued at
- `iss`: Issuer (who created the token)
- `aud`: Audience (who the token is for)

### Signature

Ensures token integrity:

```javascript
// HS256 (symmetric)
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret_key
)

// RS256 (asymmetric)
RSASHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  private_key
)
```

### JWT Implementation Examples

#### Python (PyJWT)

```python
import jwt
from datetime import datetime, timedelta

# Generate token
def create_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, "your-secret-key", algorithm="HS256")

# Validate token
def validate_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            "your-secret-key",
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")
```

#### Node.js (jsonwebtoken)

```typescript
import jwt from 'jsonwebtoken';

// Generate token
function createToken(userId: string, role: string): string {
  return jwt.sign(
    { sub: userId, role },
    process.env.JWT_SECRET,
    { expiresIn: '1h', algorithm: 'HS256' }
  );
}

// Validate token
function validateToken(token: string): any {
  try {
    return jwt.verify(token, process.env.JWT_SECRET, {
      algorithms: ['HS256']
    });
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      throw new Error('Token expired');
    }
    throw new Error('Invalid token');
  }
}
```

#### Go (golang-jwt)

```go
import (
    "time"
    "github.com/golang-jwt/jwt/v5"
)

type Claims struct {
    UserID int    `json:"sub"`
    Role   string `json:"role"`
    jwt.RegisteredClaims
}

// Generate token
func CreateToken(userID int, role string) (string, error) {
    claims := &Claims{
        UserID: userID,
        Role:   role,
        RegisteredClaims: jwt.RegisteredClaims{
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(1 * time.Hour)),
            IssuedAt:  jwt.NewNumericDate(time.Now()),
        },
    }

    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString([]byte("your-secret-key"))
}

// Validate token
func ValidateToken(tokenString string) (*Claims, error) {
    claims := &Claims{}
    token, err := jwt.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (interface{}, error) {
        return []byte("your-secret-key"), nil
    })

    if err != nil || !token.Valid {
        return nil, err
    }
    return claims, nil
}
```

### JWT Best Practices

✅ **Always set expiration** (`exp` claim) - Short-lived tokens (15min-1hr)
✅ **Use strong secret keys** - At least 256 bits for HS256
✅ **Validate signature** - Always verify before trusting payload
✅ **Use RS256 for microservices** - Public key validation, no shared secret
✅ **Store minimal data** - JWTs sent with every request (size matters)

❌ **Don't store sensitive data** - JWTs are readable (Base64 encoded, not encrypted)
❌ **Don't use for session management alone** - Hard to revoke
❌ **Don't store in localStorage** - Vulnerable to XSS attacks
❌ **Don't make tokens long-lived** - Compromised tokens can't be revoked

---

## OAuth 2.0

### OAuth 2.0 Flows

#### Authorization Code Flow (Most Secure)

**Use case**: Server-side web apps, mobile apps with PKCE

```
User                    Client App              Auth Server            Resource Server
  |                         |                        |                        |
  |--1. Click "Login"------>|                        |                        |
  |                         |--2. Redirect to------->|                        |
  |                         |   /authorize           |                        |
  |<------3. Login page---------------------------|                        |
  |                         |                        |                        |
  |--4. Enter credentials------------------------>|                        |
  |                         |                        |                        |
  |<--5. Redirect with authorization code---------|                        |
  |    (to callback URL)    |                        |                        |
  |                         |                        |                        |
  |--6. Code to client----->|                        |                        |
  |                         |--7. Exchange code----->|                        |
  |                         |    for tokens          |                        |
  |                         |<--8. Access token------|                        |
  |                         |    + Refresh token     |                        |
  |                         |                        |                        |
  |                         |--9. Request with access token----------------->|
  |                         |<--10. Protected resource-----------------------|
```

**Implementation (Python with Authlib)**:

```python
from authlib.integrations.flask_client import OAuth

oauth = OAuth(app)
oauth.register(
    'google',
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.route('/login')
def login():
    redirect_uri = url_for('callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/callback')
def callback():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.parse_id_token(token)
    # Store token and user_info in session
    return redirect('/dashboard')
```

#### Client Credentials Flow (Server-to-Server)

**Use case**: Service-to-service authentication (no user involved)

```
Service A                 Auth Server
    |                          |
    |--1. POST /token--------->|
    |   (client_id + secret)   |
    |                          |
    |<--2. Access token--------|
    |                          |
    |--3. API request--------->|
    |   with access token      |
```

**Implementation**:

```python
import requests

# Get access token
response = requests.post('https://auth.example.com/oauth/token', data={
    'grant_type': 'client_credentials',
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret',
    'scope': 'read write'
})

token = response.json()['access_token']

# Use token to access API
api_response = requests.get(
    'https://api.example.com/resource',
    headers={'Authorization': f'Bearer {token}'}
)
```

#### Refresh Token Flow

**Use case**: Get new access token without re-authentication

```
Client                    Auth Server
  |                           |
  |--1. POST /token---------->|
  |   (refresh_token)         |
  |                           |
  |<--2. New access token-----|
  |   + New refresh token     |
```

**Implementation**:

```typescript
async function refreshAccessToken(refreshToken: string): Promise<string> {
  const response = await fetch('https://auth.example.com/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
      client_id: process.env.CLIENT_ID,
      client_secret: process.env.CLIENT_SECRET
    })
  });

  const data = await response.json();
  return data.access_token;
}
```

### OAuth 2.0 Best Practices

✅ **Use PKCE** (Proof Key for Code Exchange) for mobile/SPAs
✅ **Validate redirect URIs** - Prevent authorization code interception
✅ **Short-lived access tokens** (5-15 minutes) + long-lived refresh tokens
✅ **Store refresh tokens securely** - Encrypted database or secure storage
✅ **Implement token rotation** - Issue new refresh token on each use

---

## API Keys

### When to Use API Keys

**Best for**:
- Server-to-server communication
- Internal microservices
- Third-party integrations (customers accessing your API)
- Rate limiting and usage tracking

**Not suitable for**:
- User authentication (use JWT or sessions)
- Frontend apps (keys exposed to users)

### API Key Implementation

```python
import secrets
import hashlib
from datetime import datetime

# Generate API key
def generate_api_key() -> tuple[str, str]:
    # Generate random key
    key = secrets.token_urlsafe(32)  # 32 bytes = 256 bits

    # Hash for storage
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    return key, key_hash  # Return both (show key once, store hash)

# Validate API key
def validate_api_key(provided_key: str) -> bool:
    provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()

    # Look up in database
    stored_key = db.query("SELECT key_hash FROM api_keys WHERE key_hash = ?", [provided_hash])

    return stored_key is not None
```

### API Key Storage

**Database schema**:

```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash
    user_id INT NOT NULL,
    name VARCHAR(255),                      -- Key description
    scopes TEXT[],                          -- Permissions
    rate_limit_per_hour INT DEFAULT 1000,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    revoked BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
```

### API Key Middleware (FastAPI)

```python
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import hashlib

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def validate_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Check database
    key_data = await db.fetch_one(
        "SELECT * FROM api_keys WHERE key_hash = ? AND revoked = FALSE",
        [key_hash]
    )

    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Check expiration
    if key_data['expires_at'] and key_data['expires_at'] < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired"
        )

    # Update last_used_at
    await db.execute(
        "UPDATE api_keys SET last_used_at = NOW() WHERE id = ?",
        [key_data['id']]
    )

    return key_data
```

---

## Token Storage and Transmission

### Storage Options

| Storage | Pros | Cons | Best For |
|---------|------|------|----------|
| **httpOnly Cookie** | XSS-safe, automatic sending | CSRF risk (needs protection) | Web apps (same domain) |
| **localStorage** | Persistent, easy access | XSS vulnerable | Not recommended |
| **sessionStorage** | Tab-scoped, cleared on close | XSS vulnerable | Temporary data |
| **Memory (React state)** | XSS-safe if no innerHTML | Lost on refresh | SPAs with refresh tokens |
| **Secure native storage** | OS-level encryption | Platform-specific | Mobile apps |

### Recommended: httpOnly Cookie (Web Apps)

```python
from fastapi import Response

@app.post('/login')
async def login(response: Response, credentials: LoginRequest):
    # Validate credentials
    user = authenticate(credentials.email, credentials.password)

    # Generate token
    token = create_jwt(user.id, user.role)

    # Set httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,      # Not accessible via JavaScript (XSS protection)
        secure=True,        # HTTPS only
        samesite="strict",  # CSRF protection
        max_age=3600        # 1 hour
    )

    return {"message": "Login successful"}
```

### Transmission: Authorization Header

**Bearer token** (standard for JWTs and OAuth):

```bash
GET /api/user/profile HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**API key header**:

```bash
GET /api/data HTTP/1.1
Host: api.example.com
X-API-Key: sk_live_abc123def456...
```

---

## Token Refresh Patterns

### Pattern 1: Automatic Refresh (Before Expiration)

```typescript
let accessToken = '...';
let refreshToken = '...';
let tokenExpiry = Date.now() + 3600000; // 1 hour

// Interceptor to refresh token before requests
async function getValidToken(): Promise<string> {
  // Refresh 5 minutes before expiry
  if (Date.now() > tokenExpiry - 300000) {
    const response = await fetch('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken })
    });

    const data = await response.json();
    accessToken = data.access_token;
    tokenExpiry = Date.now() + data.expires_in * 1000;

    if (data.refresh_token) {
      refreshToken = data.refresh_token; // Token rotation
    }
  }

  return accessToken;
}
```

### Pattern 2: Retry on 401 (After Expiration)

```typescript
async function apiRequest(url: string, options: RequestInit = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${accessToken}`
    }
  });

  // Token expired
  if (response.status === 401) {
    // Refresh token
    const newToken = await refreshAccessToken(refreshToken);
    accessToken = newToken;

    // Retry original request
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${accessToken}`
      }
    });
  }

  return response;
}
```

---

## Multi-Factor Authentication (MFA)

### TOTP (Time-based One-Time Password)

**Use case**: Second factor for sensitive operations

```python
import pyotp
import qrcode
from io import BytesIO

# Generate MFA secret for user
def setup_mfa(user_id: int) -> dict:
    secret = pyotp.random_base32()

    # Store secret in database (encrypted)
    db.execute(
        "UPDATE users SET mfa_secret = ? WHERE id = ?",
        [encrypt(secret), user_id]
    )

    # Generate QR code for authenticator app
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name="YourApp"
    )

    qr = qrcode.make(totp_uri)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')

    return {
        "secret": secret,  # Show once to user
        "qr_code": buffer.getvalue()
    }

# Verify MFA code
def verify_mfa(user_id: int, code: str) -> bool:
    user = db.fetch_one("SELECT mfa_secret FROM users WHERE id = ?", [user_id])
    secret = decrypt(user['mfa_secret'])

    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # Allow 30s window
```

### MFA Login Flow

```
1. User enters email/password
2. Validate credentials → Generate temporary token
3. Require MFA code (SMS, TOTP, email)
4. Validate MFA code
5. Issue full access token
```

---

## Security Checklist

### JWT Security

- [ ] Set short expiration (`exp` claim: 15min-1hr)
- [ ] Use strong secret key (256+ bits for HS256)
- [ ] Always validate signature before trusting payload
- [ ] Use RS256 for microservices (public key validation)
- [ ] Don't store sensitive data in payload
- [ ] Validate `iss` (issuer) and `aud` (audience) claims
- [ ] Implement token blacklist for logout (if needed)

### OAuth 2.0 Security

- [ ] Use PKCE for mobile/SPAs
- [ ] Validate redirect URIs (exact match)
- [ ] Use state parameter (CSRF protection)
- [ ] Short-lived access tokens (5-15min)
- [ ] Secure refresh token storage (encrypted database)
- [ ] Implement refresh token rotation
- [ ] Use HTTPS only for token endpoints

### API Key Security

- [ ] Generate cryptographically secure keys (256+ bits)
- [ ] Store hashed keys only (SHA-256 or better)
- [ ] Implement rate limiting per key
- [ ] Support key revocation
- [ ] Set expiration dates
- [ ] Log key usage for audit trail
- [ ] Use HTTPS only for key transmission
- [ ] Never expose keys in URLs (use headers)

### General Security

- [ ] Use HTTPS everywhere
- [ ] Implement rate limiting
- [ ] Log authentication attempts (detect brute force)
- [ ] Use CORS appropriately
- [ ] Implement CSRF protection for cookies
- [ ] Validate all inputs
- [ ] Use secure password hashing (bcrypt, Argon2)
- [ ] Implement account lockout after failed attempts

---

## Auth Method Decision Tree

```
Start: What are you building?
│
├─ Third-party access (users sign in with Google/GitHub)?
│  └─ Use OAuth 2.0 (Authorization Code Flow + PKCE)
│
├─ Server-to-server communication?
│  └─ Use API Keys (with rate limiting)
│
├─ Mobile app or SPA?
│  ├─ Need user identity from third party?
│  │  └─ OAuth 2.0 + JWT
│  └─ Custom authentication?
│     └─ JWT (access + refresh tokens)
│
├─ Microservices architecture?
│  └─ JWT with RS256 (public key validation)
│
├─ Traditional web app (server-rendered)?
│  └─ Sessions (httpOnly cookies) or JWT (cookies)
│
└─ Internal admin tool?
   └─ Sessions (simplest) or API Keys
```

---

## Level 3 Resources

This skill includes comprehensive reference materials, executable scripts, and implementation examples.

### Reference Materials

**`api-authentication/resources/REFERENCE.md`** (~300 lines):
- JWT specification (RFC 7519) - Complete technical reference
- OAuth 2.0 framework (RFC 6749) - Authorization flows and grant types
- PKCE extension (RFC 7636) - Proof Key for Code Exchange
- Token storage best practices - Browser, mobile, server-side
- Security considerations - Algorithm confusion, CSRF, XSS, token replay
- Attack vectors and mitigations - Comprehensive security guide
- Password hashing algorithms - Argon2, bcrypt, scrypt comparison
- Implementation checklist - JWT, OAuth, API key requirements

### Executable Scripts

**`api-authentication/resources/scripts/`**:

1. **test_jwt.py** - JWT security testing and validation
   - Validate JWT tokens with full security checks
   - Generate tokens with proper claims
   - Inspect token structure (header, payload, signature)
   - Run attack tests (none algorithm, weak secrets, algorithm confusion)
   - Check expiration, signature, and claim validation

2. **test_oauth_flow.py** - OAuth 2.0 flow validator
   - Test authorization endpoints (Authorization Code Flow)
   - Test token endpoints (Client Credentials, Refresh Token)
   - Validate PKCE implementation
   - Check state parameter and redirect URI validation
   - Verify HTTPS enforcement

3. **benchmark_hashing.py** - Password hashing benchmark
   - Compare bcrypt, Argon2id, and scrypt
   - Auto-tune Argon2 parameters for target time (250-500ms)
   - Statistical analysis (mean, median, stdev)
   - Memory usage comparison

**Usage Examples**:
```bash
# JWT validation
python test_jwt.py --token "eyJhbGc..." --validate --secret "key" --algorithm HS256

# OAuth testing
python test_oauth_flow.py --auth-url https://auth.example.com/authorize \
                          --client-id ID --redirect-uri https://app.example.com/callback

# Hashing benchmark
python benchmark_hashing.py --compare --iterations 50
```

### Implementation Examples

**`api-authentication/resources/examples/`**:

- **python/jwt_authentication.py** - Complete FastAPI JWT auth with Argon2
- **typescript/jwt-auth-client.ts** - React/TypeScript auth client with automatic refresh
- **ci-cd/jwt-security-check.yml** - GitHub Actions security validation

See `api-authentication/resources/scripts/README.md` for detailed documentation.

---

## Related Skills

- `network-resilience-patterns.md` - Retry logic for auth failures
- `modal-web-endpoints.md` - Securing Modal endpoints with auth
- `ios-networking.md` - iOS auth patterns with URLSession
- `database-selection.md` - Storing user credentials and tokens

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
**Resources**: Level 3 (Reference, Scripts, Examples)
