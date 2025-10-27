---
name: security-security-headers
description: HTTP security headers including CSP, HSTS, X-Frame-Options, CORS, and other protective headers for web application security
---

# Security: Security Headers

**Scope**: HTTP security headers, CSP, HSTS, CORS, XSS protection
**Lines**: ~350
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Hardening web application security
- Preventing clickjacking, XSS, and MITM attacks
- Configuring Content Security Policy (CSP)
- Setting up CORS for APIs
- Implementing HTTPS enforcement (HSTS)
- Protecting against browser-based attacks
- Passing security audits and penetration tests

## Essential Security Headers

### Complete Header Configuration

```python
from flask import Flask, make_response

app = Flask(__name__)

@app.after_request
def add_security_headers(response):
    """Apply security headers to all responses"""

    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'

    # Enable browser XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # Enforce HTTPS
    response.headers['Strict-Transport-Security'] = (
        'max-age=31536000; includeSubDomains; preload'
    )

    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.example.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' https://api.example.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Permissions policy (formerly Feature Policy)
    response.headers['Permissions-Policy'] = (
        'geolocation=(), microphone=(), camera=()'
    )

    return response
```

## Content Security Policy (CSP)

### CSP Directives

```python
class CSPBuilder:
    """Build Content Security Policy header"""

    def __init__(self):
        self.directives = {
            'default-src': ["'self'"],
            'script-src': ["'self'"],
            'style-src': ["'self'"],
            'img-src': ["'self'"],
            'font-src': ["'self'"],
            'connect-src': ["'self'"],
            'media-src': ["'self'"],
            'object-src': ["'none'"],
            'frame-src': ["'none'"],
            'frame-ancestors': ["'none'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"],
            'upgrade-insecure-requests': []
        }

    def allow_scripts_from(self, *sources):
        """Allow scripts from specific sources"""
        self.directives['script-src'].extend(sources)
        return self

    def allow_styles_from(self, *sources):
        """Allow styles from specific sources"""
        self.directives['style-src'].extend(sources)
        return self

    def allow_images_from(self, *sources):
        """Allow images from specific sources"""
        self.directives['img-src'].extend(sources)
        return self

    def allow_inline_scripts(self, nonce: str = None):
        """Allow inline scripts (use nonce for security)"""
        if nonce:
            self.directives['script-src'].append(f"'nonce-{nonce}'")
        else:
            # Less secure - avoid if possible
            self.directives['script-src'].append("'unsafe-inline'")
        return self

    def allow_inline_styles(self):
        """Allow inline styles"""
        self.directives['style-src'].append("'unsafe-inline'")
        return self

    def report_to(self, endpoint: str):
        """Set CSP violation reporting endpoint"""
        self.directives['report-uri'] = [endpoint]
        return self

    def build(self) -> str:
        """Build CSP header string"""
        parts = []
        for directive, sources in self.directives.items():
            if sources:
                parts.append(f"{directive} {' '.join(sources)}")
            else:
                parts.append(directive)
        return '; '.join(parts)

# Usage
csp = (CSPBuilder()
    .allow_scripts_from('https://cdn.jsdelivr.net', 'https://www.googletagmanager.com')
    .allow_styles_from('https://fonts.googleapis.com')
    .allow_images_from('data:', 'https:')
    .report_to('/csp-violation-report')
    .build())

# Result:
# "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net https://www.googletagmanager.com; ..."
```

### CSP with Nonces (Recommended)

```python
import secrets
from flask import Flask, render_template, g

app = Flask(__name__)

@app.before_request
def generate_csp_nonce():
    """Generate unique nonce for each request"""
    g.csp_nonce = secrets.token_urlsafe(16)

@app.after_request
def add_csp_header(response):
    """Add CSP with nonce"""
    nonce = getattr(g, 'csp_nonce', None)

    if nonce:
        csp = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            f"style-src 'self' 'nonce-{nonce}'; "
            f"object-src 'none';"
        )
        response.headers['Content-Security-Policy'] = csp

    return response

@app.route('/')
def index():
    """Template can use nonce for inline scripts"""
    return render_template('index.html', csp_nonce=g.csp_nonce)
```

```html
<!-- Template with nonce -->
<!DOCTYPE html>
<html>
<head>
    <!-- Inline style with nonce -->
    <style nonce="{{ csp_nonce }}">
        body { background: white; }
    </style>
</head>
<body>
    <!-- Inline script with nonce -->
    <script nonce="{{ csp_nonce }}">
        console.log('This script is allowed');
    </script>
</body>
</html>
```

### CSP Violation Reporting

```python
@app.route('/csp-violation-report', methods=['POST'])
def csp_violation():
    """Handle CSP violation reports"""
    import json

    report = request.get_json()

    # Log violation
    logger.warning('CSP Violation', extra={
        'document_uri': report.get('document-uri'),
        'violated_directive': report.get('violated-directive'),
        'blocked_uri': report.get('blocked-uri'),
        'source_file': report.get('source-file'),
        'line_number': report.get('line-number')
    })

    # Store in database for analysis
    db.insert_csp_violation(report)

    return '', 204  # No content
```

## Strict-Transport-Security (HSTS)

### HSTS Configuration

```python
# Basic HSTS
response.headers['Strict-Transport-Security'] = 'max-age=31536000'

# HSTS with subdomains
response.headers['Strict-Transport-Security'] = (
    'max-age=31536000; includeSubDomains'
)

# HSTS with preload (submit to browser preload list)
response.headers['Strict-Transport-Security'] = (
    'max-age=31536000; includeSubDomains; preload'
)

# ⚠️ Remove HSTS (emergency only)
response.headers['Strict-Transport-Security'] = 'max-age=0'
```

### HTTPS Redirect Middleware

```python
from flask import Flask, redirect, request

app = Flask(__name__)

@app.before_request
def redirect_to_https():
    """Enforce HTTPS for all requests"""
    if not request.is_secure and app.config.get('FORCE_HTTPS'):
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
```

## X-Frame-Options

### Clickjacking Prevention

```python
# Deny all framing (most secure)
response.headers['X-Frame-Options'] = 'DENY'

# Allow framing from same origin
response.headers['X-Frame-Options'] = 'SAMEORIGIN'

# Allow framing from specific domain (deprecated, use CSP)
response.headers['X-Frame-Options'] = 'ALLOW-FROM https://trusted.com'

# Modern alternative: CSP frame-ancestors
response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"  # Deny
response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"  # Same origin
response.headers['Content-Security-Policy'] = "frame-ancestors https://trusted.com"  # Specific domain
```

## Cross-Origin Resource Sharing (CORS)

### CORS Configuration

```python
from flask_cors import CORS

# Allow all origins (development only)
app = Flask(__name__)
CORS(app)  # ⚠️ Not for production

# Specific origin
CORS(app, origins=['https://example.com'])

# Multiple origins with credentials
CORS(app,
     origins=['https://app1.example.com', 'https://app2.example.com'],
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'],
     expose_headers=['X-Total-Count'],
     max_age=3600)

# Manual CORS handling
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')

    # Whitelist allowed origins
    allowed_origins = [
        'https://app.example.com',
        'https://admin.example.com'
    ]

    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Max-Age'] = '3600'

    return response

# Preflight request handler
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_preflight(path):
    """Handle CORS preflight requests"""
    return '', 204
```

### CORS Security Considerations

```python
# ❌ VULNERABLE - Reflecting Origin header
@app.after_request
def vulnerable_cors(response):
    # Never do this - allows any origin
    origin = request.headers.get('Origin')
    response.headers['Access-Control-Allow-Origin'] = origin  # VULNERABLE
    return response

# ✅ SECURE - Whitelist validation
@app.after_request
def secure_cors(response):
    origin = request.headers.get('Origin')

    # Validate against whitelist
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
    elif '*' in ALLOWED_ORIGINS and not CREDENTIALS_REQUIRED:
        # Only allow wildcard without credentials
        response.headers['Access-Control-Allow-Origin'] = '*'

    return response
```

## Other Security Headers

### X-Content-Type-Options

```python
# Prevent MIME type sniffing
response.headers['X-Content-Type-Options'] = 'nosniff'

# Ensures browsers respect Content-Type header
# Prevents IE/Chrome from interpreting files as different type
```

### Referrer-Policy

```python
# Don't send referrer
response.headers['Referrer-Policy'] = 'no-referrer'

# Send only origin (no path)
response.headers['Referrer-Policy'] = 'origin'

# Send full URL to same origin, origin to cross-origin
response.headers['Referrer-Policy'] = 'origin-when-cross-origin'

# Strict: only HTTPS → HTTPS
response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

# No referrer to less secure (HTTPS → HTTP)
response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
```

### Permissions-Policy

```python
# Disable all features
response.headers['Permissions-Policy'] = (
    'geolocation=(), microphone=(), camera=(), '
    'payment=(), usb=(), magnetometer=(), gyroscope=()'
)

# Allow specific features for self
response.headers['Permissions-Policy'] = (
    'geolocation=(self), camera=(self)'
)

# Allow for specific origins
response.headers['Permissions-Policy'] = (
    'geolocation=(self "https://maps.example.com")'
)
```

### X-XSS-Protection (Legacy)

```python
# Enable XSS filter (legacy browsers)
response.headers['X-XSS-Protection'] = '1; mode=block'

# Note: Modern browsers rely on CSP instead
# Still useful for older browsers
```

## Framework-Specific Implementations

### FastAPI Security Headers

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=['https://example.com'],
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
    allow_headers=['*'],
)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=['example.com', '*.example.com']
)

# Custom security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)

    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = (
        'max-age=31536000; includeSubDomains'
    )
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; script-src 'self' https://cdn.example.com"
    )

    return response
```

### Express.js (Helmet)

```javascript
const express = require('express');
const helmet = require('helmet');

const app = express();

// Use Helmet with all defaults
app.use(helmet());

// Custom configuration
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "https://cdn.jsdelivr.net"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'", "https://api.example.com"],
      fontSrc: ["'self'", "https://fonts.gstatic.com"],
      objectSrc: ["'none'"],
      frameAncestors: ["'none'"],
    },
  },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  },
}));
```

### Nginx Configuration

```nginx
# Security headers in Nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # CSP
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://cdn.example.com" always;

    # Clickjacking protection
    add_header X-Frame-Options "DENY" always;

    # MIME type sniffing protection
    add_header X-Content-Type-Options "nosniff" always;

    # XSS protection
    add_header X-XSS-Protection "1; mode=block" always;

    # Referrer policy
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Permissions policy
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    location / {
        proxy_pass http://backend;
    }
}
```

## Testing Security Headers

### Automated Testing

```python
import requests

def test_security_headers():
    """Test if security headers are present"""
    response = requests.get('https://example.com')

    # Required headers
    assert 'Strict-Transport-Security' in response.headers
    assert 'X-Frame-Options' in response.headers
    assert 'X-Content-Type-Options' in response.headers
    assert 'Content-Security-Policy' in response.headers

    # Validate HSTS
    hsts = response.headers['Strict-Transport-Security']
    assert 'max-age=31536000' in hsts
    assert 'includeSubDomains' in hsts

    # Validate CSP
    csp = response.headers['Content-Security-Policy']
    assert "default-src 'self'" in csp

    # Check no insecure headers
    assert 'X-Powered-By' not in response.headers  # Remove server info
```

### Manual Testing Tools

```bash
# Check headers with curl
curl -I https://example.com

# Check with httpie
http HEAD https://example.com

# Online tools:
# - https://securityheaders.com
# - https://observatory.mozilla.org
```

## Security Best Practices

### Security Headers Checklist

**Essential Headers**:
- [ ] Strict-Transport-Security (HSTS)
- [ ] Content-Security-Policy (CSP)
- [ ] X-Frame-Options or CSP frame-ancestors
- [ ] X-Content-Type-Options: nosniff
- [ ] Referrer-Policy

**CORS Configuration**:
- [ ] Whitelist allowed origins (no wildcard with credentials)
- [ ] Specify allowed methods and headers
- [ ] Set appropriate max-age for preflight caching
- [ ] Enable credentials only when necessary

**CSP Best Practices**:
- [ ] Start with restrictive policy
- [ ] Use nonces for inline scripts/styles
- [ ] Avoid 'unsafe-inline' and 'unsafe-eval'
- [ ] Enable CSP reporting
- [ ] Test in report-only mode first

**General**:
- [ ] Remove server identification headers (X-Powered-By, Server)
- [ ] Enforce HTTPS everywhere
- [ ] Set Permissions-Policy to disable unused features
- [ ] Regular security header audits

## Related Skills

- `security-input-validation.md` - CSP and XSS prevention
- `security-vulnerability-assessment.md` - Testing security headers
- `frontend-performance.md` - CSP impact on resource loading
- `api-error-handling.md` - CORS error handling

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
