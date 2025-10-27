---
name: security-authentication
description: Authentication patterns including JWT, OAuth2, sessions, and multi-factor authentication for secure user identity verification
---

# Security: Authentication

**Scope**: Authentication patterns, identity verification, credential management, MFA
**Lines**: ~380
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Implementing user login and authentication systems
- Choosing authentication strategies for applications
- Securing user credentials and password management
- Implementing multi-factor authentication (MFA/2FA)
- Designing session management systems
- Preventing authentication bypass vulnerabilities
- Migrating authentication systems

## Authentication Fundamentals

### Authentication vs Authorization

**Authentication**: "Who are you?" - Verifying identity
**Authorization**: "What can you do?" - Verifying permissions

```python
# Authentication: Verify user identity
def authenticate(username: str, password: str) -> User:
    user = db.get_user_by_username(username)
    if user and verify_password(password, user.password_hash):
        return user
    raise AuthenticationError("Invalid credentials")

# Authorization: Check permissions (see security-authorization.md)
def authorize(user: User, resource: str, action: str) -> bool:
    return user.has_permission(resource, action)
```

## Password Security

### Password Hashing

**Bad - Never use**:
```python
# ❌ Plain text storage
user.password = request.password

# ❌ Weak hashing (MD5, SHA1)
user.password = hashlib.md5(request.password.encode()).hexdigest()

# ❌ No salt
user.password = hashlib.sha256(request.password.encode()).hexdigest()
```

**Good - Use strong hashing**:
```python
import bcrypt
from argon2 import PasswordHasher

# ✅ bcrypt (widely used, battle-tested)
def hash_password_bcrypt(password: str) -> bytes:
    salt = bcrypt.gensalt(rounds=12)  # Cost factor
    return bcrypt.hashpw(password.encode(), salt)

def verify_password_bcrypt(password: str, hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hash)

# ✅ Argon2 (modern, recommended)
ph = PasswordHasher()

def hash_password_argon2(password: str) -> str:
    return ph.hash(password)

def verify_password_argon2(password: str, hash: str) -> bool:
    try:
        ph.verify(hash, password)
        return True
    except:
        return False
```

### Password Validation

```python
import re
from typing import List

def validate_password_strength(password: str) -> tuple[bool, List[str]]:
    """
    Validate password meets security requirements.
    Returns (is_valid, list_of_errors)
    """
    errors = []

    # Minimum length
    if len(password) < 12:
        errors.append("Password must be at least 12 characters")

    # Character requirements
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain uppercase letter")

    if not re.search(r'[a-z]', password):
        errors.append("Password must contain lowercase letter")

    if not re.search(r'\d', password):
        errors.append("Password must contain digit")

    if not re.search(r'[^A-Za-z0-9]', password):
        errors.append("Password must contain special character")

    # Check against common passwords (use library like commonpasswords)
    if password.lower() in COMMON_PASSWORDS:
        errors.append("Password is too common")

    return (len(errors) == 0, errors)
```

### Password Reset Flow

```python
import secrets
from datetime import datetime, timedelta

# Step 1: Generate reset token
def create_password_reset_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(hours=1)

    # Store hashed token
    db.execute("""
        INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
        VALUES (?, ?, ?)
    """, [user_id, hash_token(token), expiry])

    return token  # Send via email

# Step 2: Validate and reset
def reset_password(token: str, new_password: str) -> bool:
    token_hash = hash_token(token)

    # Find valid token
    record = db.fetch_one("""
        SELECT user_id FROM password_reset_tokens
        WHERE token_hash = ? AND expires_at > ? AND used = FALSE
    """, [token_hash, datetime.utcnow()])

    if not record:
        raise InvalidTokenError("Invalid or expired token")

    # Update password
    new_hash = hash_password(new_password)
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
               [new_hash, record['user_id']])

    # Mark token as used
    db.execute("UPDATE password_reset_tokens SET used = TRUE WHERE token_hash = ?",
               [token_hash])

    return True
```

## Session-Based Authentication

### Session Implementation (Python/Flask)

```python
from flask import Flask, session, request
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Use environment variable
app.permanent_session_lifetime = timedelta(hours=24)

@app.route('/login', methods=['POST'])
def login():
    credentials = request.json

    # Authenticate user
    user = authenticate(credentials['username'], credentials['password'])

    # Create session
    session.permanent = True
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role

    return {"message": "Login successful"}

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return {"message": "Logout successful"}

# Middleware to require authentication
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return {"error": "Unauthorized"}, 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/protected')
@require_auth
def protected_route():
    return {"user_id": session['user_id']}
```

### Session Security

```python
from flask import Flask
from flask_session import Session

app = Flask(__name__)

# Configure secure session
app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,    # No JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=3600, # 1 hour timeout
)

# Server-side session storage (Redis)
app.config.update(
    SESSION_TYPE='redis',
    SESSION_REDIS=redis.from_url('redis://localhost:6379')
)

Session(app)
```

## JWT Authentication

See `api-authentication.md` for comprehensive JWT implementation details.

**Quick reference**:
```python
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key"

def create_jwt(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
```

## Multi-Factor Authentication (MFA)

### TOTP (Time-based One-Time Password)

```python
import pyotp
import qrcode
from io import BytesIO

class MFAService:
    @staticmethod
    def setup_totp(user: User) -> dict:
        """Generate TOTP secret and QR code for user"""
        secret = pyotp.random_base32()

        # Store encrypted secret
        user.mfa_secret = encrypt(secret)
        user.mfa_enabled = False  # Enable after verification
        db.save(user)

        # Generate provisioning URI
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="YourApp"
        )

        # Generate QR code
        qr = qrcode.make(uri)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')

        return {
            "secret": secret,  # Show once for manual entry
            "qr_code": buffer.getvalue()
        }

    @staticmethod
    def verify_totp(user: User, code: str) -> bool:
        """Verify TOTP code"""
        if not user.mfa_enabled:
            return False

        secret = decrypt(user.mfa_secret)
        totp = pyotp.TOTP(secret)

        # Allow 30-second window (1 step before/after)
        return totp.verify(code, valid_window=1)

    @staticmethod
    def enable_mfa(user: User, code: str) -> bool:
        """Enable MFA after verifying setup code"""
        if MFAService.verify_totp(user, code):
            user.mfa_enabled = True
            db.save(user)
            return True
        return False
```

### MFA Login Flow

```python
from flask import Flask, request, session

@app.route('/login', methods=['POST'])
def login():
    credentials = request.json

    # Step 1: Verify username/password
    user = authenticate(credentials['username'], credentials['password'])

    if user.mfa_enabled:
        # MFA required - issue temporary token
        temp_token = create_temporary_token(user.id)
        session['requires_mfa'] = True
        session['temp_user_id'] = user.id

        return {
            "requires_mfa": True,
            "temp_token": temp_token
        }, 200

    # No MFA - complete login
    create_full_session(user)
    return {"message": "Login successful"}, 200

@app.route('/login/mfa', methods=['POST'])
def login_mfa():
    """Complete MFA challenge"""
    if not session.get('requires_mfa'):
        return {"error": "No MFA challenge pending"}, 400

    user_id = session['temp_user_id']
    mfa_code = request.json['code']

    user = db.get_user(user_id)

    if MFAService.verify_totp(user, mfa_code):
        # MFA verified - complete login
        session.pop('requires_mfa')
        session.pop('temp_user_id')
        create_full_session(user)

        return {"message": "Login successful"}, 200

    return {"error": "Invalid MFA code"}, 401
```

### Backup Codes

```python
import secrets

def generate_backup_codes(count: int = 10) -> List[str]:
    """Generate one-time backup codes"""
    codes = [secrets.token_hex(4) for _ in range(count)]  # 8-char codes

    # Store hashed codes
    hashed_codes = [hash_backup_code(code) for code in codes]

    return codes, hashed_codes

def verify_backup_code(user: User, code: str) -> bool:
    """Verify and consume backup code"""
    code_hash = hash_backup_code(code)

    # Find and remove code
    result = db.execute("""
        DELETE FROM backup_codes
        WHERE user_id = ? AND code_hash = ? AND used = FALSE
        RETURNING id
    """, [user.id, code_hash])

    return result is not None
```

## OAuth 2.0 Authentication

See `api-authentication.md` for full OAuth implementation.

**Quick integration (Python/Authlib)**:
```python
from authlib.integrations.flask_client import OAuth

oauth = OAuth(app)

# Register OAuth provider
oauth.register(
    'google',
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.route('/auth/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.parse_id_token(token)

    # Find or create user
    user = User.find_or_create_by_email(user_info['email'])
    create_full_session(user)

    return redirect('/dashboard')
```

## Security Best Practices

### Account Lockout

```python
from datetime import datetime, timedelta

def check_login_attempts(username: str) -> bool:
    """Check if account is locked due to failed attempts"""
    attempts = db.fetch_one("""
        SELECT COUNT(*) as count, MAX(attempted_at) as last_attempt
        FROM login_attempts
        WHERE username = ? AND attempted_at > ?
    """, [username, datetime.utcnow() - timedelta(minutes=15)])

    if attempts['count'] >= 5:
        # Lock account for 15 minutes
        return False

    return True

def record_failed_login(username: str):
    """Record failed login attempt"""
    db.execute("""
        INSERT INTO login_attempts (username, attempted_at, success)
        VALUES (?, ?, FALSE)
    """, [username, datetime.utcnow()])

def clear_login_attempts(username: str):
    """Clear attempts after successful login"""
    db.execute("DELETE FROM login_attempts WHERE username = ?", [username])
```

### Security Checklist

**Password Security**:
- [ ] Use Argon2 or bcrypt (cost factor 12+)
- [ ] Enforce minimum length (12+ characters)
- [ ] Require complexity (uppercase, lowercase, digits, special)
- [ ] Check against common password lists
- [ ] Implement secure password reset flow
- [ ] Never email passwords in plain text

**Session Security**:
- [ ] Use secure, httpOnly cookies
- [ ] Set SameSite attribute (CSRF protection)
- [ ] Implement session timeout (idle + absolute)
- [ ] Regenerate session ID after login
- [ ] Clear session on logout
- [ ] Use server-side session storage for sensitive apps

**Authentication Flow**:
- [ ] Implement rate limiting on auth endpoints
- [ ] Log all authentication attempts
- [ ] Account lockout after failed attempts
- [ ] MFA for sensitive operations
- [ ] Secure password reset tokens (short-lived, one-time)
- [ ] HTTPS only for authentication

**Token Security**:
- [ ] Short-lived access tokens (15min-1hr)
- [ ] Secure token storage (httpOnly cookies or secure storage)
- [ ] Implement token refresh mechanism
- [ ] Validate token signature and expiration
- [ ] Use refresh token rotation

## Common Vulnerabilities

### Brute Force Attack

**Attack**: Automated password guessing
**Prevention**:
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # Rate limit
def login():
    # Check account lockout
    if not check_login_attempts(username):
        return {"error": "Account locked"}, 429

    # Authenticate...
```

### Credential Stuffing

**Attack**: Using leaked credentials from other sites
**Prevention**:
- Implement MFA
- Monitor for unusual login patterns
- Check passwords against breach databases (haveibeenpwned.com API)

### Session Fixation

**Attack**: Forcing user to use known session ID
**Prevention**:
```python
from flask import session

@app.route('/login', methods=['POST'])
def login():
    # Authenticate user
    user = authenticate(...)

    # Regenerate session ID
    session.regenerate()

    session['user_id'] = user.id
```

## Related Skills

- `security-authorization.md` - Access control and permissions
- `security-input-validation.md` - Validating authentication inputs
- `security-secrets-management.md` - Storing authentication secrets
- `api-authentication.md` - JWT and OAuth 2.0 implementation
- `database-security.md` - Securing credential storage

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
