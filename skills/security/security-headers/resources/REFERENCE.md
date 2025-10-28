# Security Headers Reference

Comprehensive reference for HTTP security headers, implementation patterns, attack vectors, and security hardening strategies.

## Table of Contents

1. [Core Security Headers](#core-security-headers)
2. [Content Security Policy (CSP)](#content-security-policy-csp)
3. [Cookie Security](#cookie-security)
4. [CORS Headers](#cors-headers)
5. [Referrer Policy](#referrer-policy)
6. [Permissions Policy](#permissions-policy)
7. [Attack Vectors & Mitigations](#attack-vectors--mitigations)
8. [Testing & Validation](#testing--validation)
9. [Browser Compatibility](#browser-compatibility)
10. [Implementation Patterns](#implementation-patterns)

---

## Core Security Headers

### Strict-Transport-Security (HSTS)

**Purpose**: Forces browsers to use HTTPS connections only.

**Syntax**:
```
Strict-Transport-Security: max-age=<seconds>; includeSubDomains; preload
```

**Parameters**:
- `max-age`: Duration (seconds) to remember HTTPS-only policy
- `includeSubDomains`: Apply policy to all subdomains
- `preload`: Enable HSTS preload list inclusion

**Recommended Configuration**:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Security Impact**:
- Prevents SSL stripping attacks
- Mitigates cookie hijacking over HTTP
- Eliminates mixed content warnings
- Risk: max-age=0 can disable HSTS

**Preload Requirements**:
1. Valid certificate
2. Redirect HTTP → HTTPS (same host)
3. HTTPS on all subdomains
4. max-age ≥ 31536000 (1 year)
5. includeSubDomains directive
6. preload directive
7. Submit to hstspreload.org

**Common Mistakes**:
```
# Too short max-age
Strict-Transport-Security: max-age=86400

# Missing includeSubDomains (subdomain vulnerability)
Strict-Transport-Security: max-age=31536000

# Preload without meeting requirements
Strict-Transport-Security: max-age=300; preload
```

### X-Frame-Options

**Purpose**: Prevents clickjacking attacks by controlling iframe embedding.

**Syntax**:
```
X-Frame-Options: DENY | SAMEORIGIN | ALLOW-FROM uri
```

**Directives**:
- `DENY`: No framing allowed
- `SAMEORIGIN`: Frame only from same origin
- `ALLOW-FROM uri`: Frame from specific URI (deprecated)

**Recommended Configuration**:
```
X-Frame-Options: DENY
```

**Security Impact**:
- Prevents UI redress attacks
- Blocks clickjacking
- Protects against drag-and-drop attacks
- Superseded by CSP frame-ancestors

**CSP Alternative** (preferred):
```
Content-Security-Policy: frame-ancestors 'none'
Content-Security-Policy: frame-ancestors 'self'
Content-Security-Policy: frame-ancestors https://trusted.com
```

**Browser Support**:
- X-Frame-Options: All modern browsers
- CSP frame-ancestors: Chrome 40+, Firefox 33+, Safari 10+

### X-Content-Type-Options

**Purpose**: Prevents MIME type sniffing.

**Syntax**:
```
X-Content-Type-Options: nosniff
```

**Security Impact**:
- Prevents browser MIME confusion attacks
- Blocks execution of JavaScript uploaded as images
- Forces browsers to respect declared Content-Type
- Mitigates polyglot file attacks

**Attack Scenario Prevented**:
```
# Without nosniff:
# Upload malicious.jpg containing JavaScript
# Browser sniffs content, detects JS, executes
# <script src="/uploads/malicious.jpg"></script>

# With nosniff:
# Browser respects Content-Type: image/jpeg
# JavaScript not executed
```

**Required For**:
- File upload systems
- User-generated content
- Dynamic script generation
- API endpoints returning JSON

### X-XSS-Protection

**Purpose**: Legacy XSS filter control (deprecated).

**Syntax**:
```
X-XSS-Protection: 0 | 1 | 1; mode=block | 1; report=<uri>
```

**Recommended Configuration**:
```
X-XSS-Protection: 0
```

**Why Disable**:
- Built-in XSS filters cause vulnerabilities
- CSP provides better protection
- Modern browsers removed XSS auditors
- Can introduce new attack vectors

**Use CSP Instead**:
```
Content-Security-Policy: script-src 'self'
```

### Referrer-Policy

**Purpose**: Controls Referer header information sent to other origins.

**Syntax**:
```
Referrer-Policy: no-referrer | no-referrer-when-downgrade | origin |
                 origin-when-cross-origin | same-origin | strict-origin |
                 strict-origin-when-cross-origin | unsafe-url
```

**Directives**:

| Policy | Same-Origin | Cross-Origin HTTPS | Cross-Origin HTTP |
|--------|-------------|-------------------|-------------------|
| `no-referrer` | None | None | None |
| `no-referrer-when-downgrade` | Full URL | Full URL | None |
| `origin` | Origin only | Origin only | Origin only |
| `origin-when-cross-origin` | Full URL | Origin only | Origin only |
| `same-origin` | Full URL | None | None |
| `strict-origin` | Origin only | Origin only | None |
| `strict-origin-when-cross-origin` | Full URL | Origin only | None |
| `unsafe-url` | Full URL | Full URL | Full URL |

**Recommended Configuration**:
```
Referrer-Policy: strict-origin-when-cross-origin
```

**Privacy Considerations**:
- `no-referrer`: Maximum privacy, breaks analytics
- `strict-origin-when-cross-origin`: Good balance
- `unsafe-url`: Leaks sensitive URLs

**Example Scenarios**:
```
# Private application
Referrer-Policy: no-referrer

# Public website with analytics
Referrer-Policy: strict-origin-when-cross-origin

# API endpoints
Referrer-Policy: no-referrer
```

---

## Content Security Policy (CSP)

### Overview

**Purpose**: Defines approved sources for content, preventing XSS and injection attacks.

**Syntax**:
```
Content-Security-Policy: <directive> <source>; <directive> <source>
```

**Deployment Modes**:
```
# Enforcement mode
Content-Security-Policy: <policy>

# Report-only mode (testing)
Content-Security-Policy-Report-Only: <policy>
```

### Fetch Directives

#### script-src

**Controls JavaScript execution sources.**

**Sources**:
```
script-src 'none'                    # Block all scripts
script-src 'self'                    # Same origin only
script-src 'self' https://cdn.com    # Self + specific domain
script-src 'unsafe-inline'           # Allow inline scripts (unsafe)
script-src 'unsafe-eval'             # Allow eval() (unsafe)
script-src 'nonce-<random>'          # Nonce-based (recommended)
script-src 'sha256-<hash>'           # Hash-based (recommended)
script-src 'strict-dynamic'          # Trust propagation
```

**Nonce Example**:
```html
<!-- Header -->
Content-Security-Policy: script-src 'nonce-2726c7f26c'

<!-- HTML -->
<script nonce="2726c7f26c">
  // Trusted script
</script>
```

**Hash Example**:
```html
<!-- Header -->
Content-Security-Policy: script-src 'sha256-xyz...'

<!-- HTML -->
<script>alert('Hello')</script>
<!-- Hash of "alert('Hello')" must match -->
```

**Strict Dynamic**:
```
script-src 'nonce-random' 'strict-dynamic'
```
- Scripts loaded by nonce/hash scripts are trusted
- Whitelist ignored (except 'unsafe-inline')
- Prevents bypasses via JSONP endpoints

#### style-src

**Controls CSS sources.**

```
style-src 'self'                     # Same origin stylesheets
style-src 'unsafe-inline'            # Inline styles (unsafe)
style-src 'nonce-<random>'           # Nonce-based
style-src 'sha256-<hash>'            # Hash-based
```

**Common Pattern**:
```
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com
```

#### img-src

**Controls image sources.**

```
img-src 'self'                       # Same origin images
img-src 'self' data:                 # Self + data URIs
img-src 'self' https:                # Self + any HTTPS
img-src *                            # Any source (permissive)
```

**Data URI Consideration**:
```
# Allow Base64 embedded images
img-src 'self' data:

# Security risk: Data URIs can bypass CSP for other types
```

#### connect-src

**Controls fetch, XHR, WebSocket, EventSource connections.**

```
connect-src 'self'                   # Same origin API calls
connect-src 'self' https://api.com   # Self + API domain
connect-src 'self' wss://ws.com      # Include WebSocket
```

**GraphQL Example**:
```
connect-src 'self' https://graphql.example.com
```

#### font-src

**Controls font sources.**

```
font-src 'self'                      # Same origin fonts
font-src 'self' https://fonts.gstatic.com
font-src 'self' data:                # Include data URIs
```

**Google Fonts Pattern**:
```
font-src 'self' https://fonts.gstatic.com
style-src 'self' https://fonts.googleapis.com
```

#### media-src

**Controls audio/video sources.**

```
media-src 'self'                     # Same origin media
media-src 'self' https://cdn.com
media-src *                          # Any source
```

#### object-src

**Controls Flash, Java, other plugins.**

```
object-src 'none'                    # Recommended (block plugins)
```

**Security Impact**:
- Prevents Flash-based attacks
- Blocks malicious plugin content
- Should always be 'none' unless legacy plugins required

#### frame-src

**Controls iframe sources.**

```
frame-src 'none'                     # No iframes allowed
frame-src 'self'                     # Same origin iframes
frame-src 'self' https://trusted.com
```

**Deprecated**: Use `child-src` or `frame-src` + `worker-src`

#### worker-src

**Controls Web Workers, Service Workers, Shared Workers.**

```
worker-src 'self'                    # Same origin workers
worker-src 'none'                    # Block workers
```

#### manifest-src

**Controls web app manifest sources.**

```
manifest-src 'self'                  # Same origin manifest
```

### Document Directives

#### base-uri

**Controls `<base>` tag URLs.**

```
base-uri 'none'                      # Block <base> tag
base-uri 'self'                      # Same origin only
```

**Security Impact**:
- Prevents relative URL hijacking
- Mitigates XSS via base tag injection

#### form-action

**Controls form submission targets.**

```
form-action 'self'                   # Same origin submissions
form-action 'self' https://pay.com   # Self + payment processor
form-action 'none'                   # Block all form submissions
```

**CSRF Protection Layer**:
```
form-action 'self'
```

#### frame-ancestors

**Controls who can frame this page (replaces X-Frame-Options).**

```
frame-ancestors 'none'               # Cannot be framed (X-Frame-Options: DENY)
frame-ancestors 'self'               # Same origin framing (X-Frame-Options: SAMEORIGIN)
frame-ancestors https://trusted.com  # Specific domain framing
```

### Navigation Directives

#### navigate-to

**Controls navigation targets (experimental).**

```
navigate-to 'self'                   # Navigate within same origin
navigate-to 'unsafe-allow-redirects' # Allow redirects
```

### Reporting Directives

#### report-uri (deprecated)

**Specifies violation report endpoint.**

```
report-uri /csp-report
```

**Deprecated**: Use `report-to` instead.

#### report-to

**Specifies Reporting API endpoint group.**

```
# Header 1: Define reporting endpoint
Report-To: {"group":"csp-endpoint","max_age":10886400,"endpoints":[{"url":"/csp-report"}]}

# Header 2: Reference in CSP
Content-Security-Policy: default-src 'self'; report-to csp-endpoint
```

### Other Directives

#### upgrade-insecure-requests

**Upgrades HTTP requests to HTTPS.**

```
Content-Security-Policy: upgrade-insecure-requests
```

**Effect**:
- HTTP → HTTPS for all subresources
- Helps migration to HTTPS
- No mixed content warnings

#### block-all-mixed-content (deprecated)

**Blocks mixed HTTP/HTTPS content.**

```
Content-Security-Policy: block-all-mixed-content
```

**Deprecated**: Use `upgrade-insecure-requests` instead.

#### require-trusted-types-for

**Enforces Trusted Types for DOM XSS prevention.**

```
Content-Security-Policy: require-trusted-types-for 'script'
```

**Effect**:
- Requires Trusted Types for dangerous DOM APIs
- Prevents DOM-based XSS
- Supported: Chrome 83+, Edge 83+

#### trusted-types

**Defines Trusted Types policy names.**

```
Content-Security-Policy: trusted-types myPolicy; require-trusted-types-for 'script'
```

**Example Usage**:
```javascript
if (window.trustedTypes && trustedTypes.createPolicy) {
  const myPolicy = trustedTypes.createPolicy('myPolicy', {
    createHTML: (string) => DOMPurify.sanitize(string)
  });

  element.innerHTML = myPolicy.createHTML(userInput);
}
```

### CSP Levels

#### CSP Level 1
- Basic fetch directives
- report-uri
- Browser support: All modern browsers

#### CSP Level 2
- Nonces and hashes
- frame-ancestors
- form-action
- plugin-types
- Browser support: Chrome 40+, Firefox 31+, Safari 10+

#### CSP Level 3
- 'strict-dynamic'
- Worker directives
- report-to
- Trusted Types
- Browser support: Chrome 52+, Firefox 52+

### CSP Best Practices

#### Progressive Enhancement

**Phase 1: Report-Only**
```
Content-Security-Policy-Report-Only: default-src 'self'; report-uri /csp-report
```

**Phase 2: Enforce + Monitor**
```
Content-Security-Policy: default-src 'self'; report-uri /csp-report
```

**Phase 3: Strict Policy**
```
Content-Security-Policy:
  default-src 'none';
  script-src 'nonce-random' 'strict-dynamic';
  style-src 'self';
  img-src 'self' https:;
  font-src 'self';
  connect-src 'self';
  base-uri 'none';
  form-action 'self';
  frame-ancestors 'none'
```

#### Nonce Generation

**Requirements**:
- Cryptographically random
- Unique per request
- Minimum 128 bits
- Base64 encoded

**Example (Python)**:
```python
import secrets
import base64

def generate_nonce():
    return base64.b64encode(secrets.token_bytes(16)).decode('utf-8')
```

#### Hash Generation

**Example (JavaScript)**:
```javascript
const crypto = require('crypto');

function generateScriptHash(scriptContent) {
  return crypto
    .createHash('sha256')
    .update(scriptContent)
    .digest('base64');
}

// Usage
const script = "alert('Hello')";
const hash = generateScriptHash(script);
// Content-Security-Policy: script-src 'sha256-${hash}'
```

### Common CSP Patterns

#### Static Website
```
Content-Security-Policy:
  default-src 'none';
  script-src 'self';
  style-src 'self';
  img-src 'self';
  font-src 'self';
  connect-src 'self';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none'
```

#### React/Vue SPA
```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self' data:;
  connect-src 'self' https://api.example.com;
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none'
```

#### Next.js/Nuxt SSR
```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'nonce-{NONCE}';
  style-src 'self' 'nonce-{NONCE}';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none'
```

#### API Server
```
Content-Security-Policy:
  default-src 'none';
  frame-ancestors 'none'
```

---

## Cookie Security

### SameSite Attribute

**Purpose**: Controls cookie sending in cross-site requests.

**Syntax**:
```
Set-Cookie: name=value; SameSite=Strict|Lax|None
```

#### SameSite=Strict

**Behavior**: Cookie never sent in cross-site requests.

```
Set-Cookie: session=abc123; SameSite=Strict; Secure; HttpOnly
```

**Use Cases**:
- Session tokens
- Authentication cookies
- CSRF-sensitive operations

**User Impact**:
- Clicking external link → No cookie sent
- User must re-authenticate after external navigation

**Example Scenario**:
```
1. User logged into bank.com
2. Clicks link from email to bank.com/account
3. Cookie NOT sent (SameSite=Strict)
4. User sees login page
```

#### SameSite=Lax

**Behavior**: Cookie sent in top-level navigation GET requests.

```
Set-Cookie: session=abc123; SameSite=Lax; Secure; HttpOnly
```

**Sent In**:
- `<a href="...">` clicks
- `window.location = "..."`
- `<link rel="prerender" href="...">`

**Not Sent In**:
- `<iframe src="...">`
- `<img src="...">`
- `fetch()`, `XMLHttpRequest`
- Form POST requests

**Use Cases**:
- Session cookies (better UX than Strict)
- Most authentication scenarios

**Example Scenario**:
```
1. User logged into bank.com
2. Clicks link from email to bank.com/account
3. Cookie SENT (top-level GET navigation)
4. User sees account page
```

#### SameSite=None

**Behavior**: Cookie sent in all cross-site requests.

```
Set-Cookie: tracking=xyz; SameSite=None; Secure
```

**Requirements**:
- MUST include `Secure` attribute
- HTTPS only

**Use Cases**:
- Third-party embeds (OAuth, payments)
- Cross-domain widgets
- Analytics/tracking

**Security Risk**:
- Vulnerable to CSRF
- Requires additional CSRF protection

#### Default Behavior

**Chrome 80+, Edge 86+, Firefox 69+**:
- No SameSite → Treated as `SameSite=Lax`
- 2-minute grace period for new cookies

### Cookie Security Attributes

#### Secure

**Purpose**: Cookie only sent over HTTPS.

```
Set-Cookie: session=abc; Secure
```

**Required For**:
- All production cookies
- SameSite=None cookies

#### HttpOnly

**Purpose**: Cookie inaccessible to JavaScript.

```
Set-Cookie: session=abc; HttpOnly
```

**Protection**:
- Prevents XSS cookie theft
- JavaScript `document.cookie` cannot access

**Use Cases**:
- Session tokens
- Authentication cookies
- Any security-sensitive cookie

#### Domain

**Purpose**: Specifies cookie scope across subdomains.

```
Set-Cookie: data=value; Domain=example.com
```

**Behavior**:
- `Domain=example.com` → Cookie sent to example.com and all subdomains
- No Domain attribute → Cookie only for exact domain

**Security Consideration**:
```
# Risky - sent to all subdomains
Set-Cookie: session=abc; Domain=example.com

# Safer - specific subdomain only
Set-Cookie: session=abc; Domain=app.example.com
```

#### Path

**Purpose**: Limits cookie to specific path.

```
Set-Cookie: data=value; Path=/app
```

**Behavior**:
- Cookie sent for `/app` and descendants
- Not sent for `/admin`

**Security Limitation**:
- Weak security boundary
- Can be bypassed with iframes/CORS

#### Max-Age / Expires

**Purpose**: Cookie expiration.

```
Set-Cookie: session=abc; Max-Age=3600
Set-Cookie: session=abc; Expires=Wed, 21 Oct 2025 07:28:00 GMT
```

**Best Practice**:
```
# Session cookie (no Max-Age/Expires)
Set-Cookie: session=abc; Secure; HttpOnly; SameSite=Strict

# Persistent cookie (short-lived)
Set-Cookie: remember=xyz; Max-Age=604800; Secure; HttpOnly; SameSite=Lax
```

### Cookie Prefixes

#### __Secure- Prefix

**Requirement**: Cookie must have `Secure` attribute and be set from HTTPS.

```
Set-Cookie: __Secure-SessionID=abc; Secure; Path=/
```

**Enforcement**:
- Browser rejects if not Secure
- Browser rejects if set from HTTP

#### __Host- Prefix

**Requirements**:
- Must have `Secure` attribute
- Must be set from HTTPS
- Must NOT have `Domain` attribute
- Must have `Path=/`

```
Set-Cookie: __Host-SessionID=abc; Secure; Path=/; HttpOnly; SameSite=Strict
```

**Security Benefit**:
- Prevents subdomain cookie injection
- Ensures cookie scope is tightly controlled

**Recommended Pattern**:
```
Set-Cookie: __Host-session=xyz; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600
```

---

## CORS Headers

### Access-Control-Allow-Origin

**Purpose**: Specifies allowed origins for cross-origin requests.

**Syntax**:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Origin: https://example.com
Access-Control-Allow-Origin: null
```

**Security**:
```
# Public API - any origin
Access-Control-Allow-Origin: *

# Private API - specific origin
Access-Control-Allow-Origin: https://trusted.com

# Never use with credentials
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
# ❌ Invalid - must specify origin when using credentials
```

**Dynamic Origin**:
```python
# Whitelist approach
ALLOWED_ORIGINS = ['https://app1.com', 'https://app2.com']

origin = request.headers.get('Origin')
if origin in ALLOWED_ORIGINS:
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Vary'] = 'Origin'
```

### Access-Control-Allow-Credentials

**Purpose**: Allows cookies/auth in cross-origin requests.

```
Access-Control-Allow-Credentials: true
```

**Requirements**:
- Must specify explicit origin (not *)
- Requires credentials in fetch request

**Fetch Example**:
```javascript
fetch('https://api.example.com/data', {
  credentials: 'include'  // Send cookies
})
```

### Access-Control-Allow-Methods

**Purpose**: Specifies allowed HTTP methods.

```
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
```

**Preflight Response**:
```
OPTIONS /api/resource HTTP/1.1

HTTP/1.1 204 No Content
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

### Access-Control-Allow-Headers

**Purpose**: Specifies allowed request headers.

```
Access-Control-Allow-Headers: Content-Type, Authorization, X-Custom-Header
```

**Common Pattern**:
```
Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With
```

### Access-Control-Expose-Headers

**Purpose**: Specifies headers accessible to JavaScript.

```
Access-Control-Expose-Headers: X-RateLimit-Remaining, X-RateLimit-Reset
```

**Default Exposed** (no header needed):
- Cache-Control
- Content-Language
- Content-Type
- Expires
- Last-Modified
- Pragma

### Access-Control-Max-Age

**Purpose**: Caches preflight request results.

```
Access-Control-Max-Age: 86400
```

**Value**: Seconds to cache (max browser-dependent)

**Performance Benefit**:
- Reduces preflight requests
- Recommended: 24 hours (86400)

### CORS Preflight

**Triggered By**:
- Methods: PUT, DELETE, PATCH, custom
- Headers: Non-simple headers
- Content-Type: application/json

**Example Flow**:
```
# Preflight Request
OPTIONS /api/resource HTTP/1.1
Origin: https://app.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Content-Type

# Preflight Response
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://app.com
Access-Control-Allow-Methods: POST, GET, OPTIONS
Access-Control-Allow-Headers: Content-Type
Access-Control-Max-Age: 86400

# Actual Request
POST /api/resource HTTP/1.1
Origin: https://app.com
Content-Type: application/json

# Actual Response
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://app.com
```

---

## Permissions Policy

**Purpose**: Controls browser features and APIs (successor to Feature-Policy).

**Syntax**:
```
Permissions-Policy: <feature>=(<allowlist>)
```

### Common Features

#### Geolocation
```
Permissions-Policy: geolocation=(self)
Permissions-Policy: geolocation=(self "https://maps.com")
Permissions-Policy: geolocation=()
```

#### Camera
```
Permissions-Policy: camera=(self)
Permissions-Policy: camera=()
```

#### Microphone
```
Permissions-Policy: microphone=(self)
Permissions-Policy: microphone=()
```

#### Payment
```
Permissions-Policy: payment=(self "https://stripe.com")
```

#### USB
```
Permissions-Policy: usb=()
```

#### Fullscreen
```
Permissions-Policy: fullscreen=(self)
```

#### Autoplay
```
Permissions-Policy: autoplay=(self)
```

### Multiple Features
```
Permissions-Policy:
  geolocation=(self),
  camera=(),
  microphone=(),
  payment=(self "https://stripe.com"),
  usb=()
```

### Allowlist Syntax

| Syntax | Meaning |
|--------|---------|
| `*` | All origins |
| `self` | Same origin |
| `src` | iframe src origin (iframe allow attribute) |
| `none` or `()` | No origins |
| `"https://example.com"` | Specific origin |

### Iframe Allow Attribute

**HTML**:
```html
<!-- Old Feature-Policy -->
<iframe allow="geolocation https://maps.com; camera 'none'"></iframe>

<!-- New Permissions-Policy -->
<iframe allow="geolocation https://maps.com; camera 'none'"></iframe>
```

### Complete Feature List

**Available Features**:
- accelerometer
- ambient-light-sensor
- autoplay
- battery
- camera
- display-capture
- document-domain
- encrypted-media
- fullscreen
- geolocation
- gyroscope
- magnetometer
- microphone
- midi
- payment
- picture-in-picture
- publickey-credentials-get
- screen-wake-lock
- sync-xhr
- usb
- web-share
- xr-spatial-tracking

### Recommended Restrictive Policy
```
Permissions-Policy:
  accelerometer=(),
  camera=(),
  geolocation=(),
  gyroscope=(),
  magnetometer=(),
  microphone=(),
  payment=(),
  usb=()
```

---

## Attack Vectors & Mitigations

### Cross-Site Scripting (XSS)

**Attack Types**:

#### Reflected XSS
```
# Vulnerable URL
https://site.com/search?q=<script>alert(1)</script>

# Vulnerable Code
echo "Results for: " . $_GET['q'];
```

**Mitigations**:
1. Output encoding
2. CSP with script-src 'self'
3. X-Content-Type-Options: nosniff
4. Trusted Types

#### Stored XSS
```
# Attacker stores malicious script in database
INSERT INTO comments VALUES ('<script>steal_cookies()</script>');

# Victim loads page
SELECT comment FROM comments;
echo $comment;  // Executes script
```

**Mitigations**:
1. Input validation
2. Output encoding
3. CSP
4. HttpOnly cookies

#### DOM-based XSS
```javascript
// Vulnerable code
const name = location.hash.slice(1);
document.getElementById('welcome').innerHTML = 'Hello ' + name;

// Attack: https://site.com#<img src=x onerror=alert(1)>
```

**Mitigations**:
1. Use textContent instead of innerHTML
2. CSP with trusted-types
3. DOMPurify library
4. Avoid eval(), setTimeout(string)

### Clickjacking

**Attack Scenario**:
```html
<!-- Attacker's page -->
<iframe src="https://bank.com/transfer" style="opacity: 0.01; position: absolute;"></iframe>
<button style="position: absolute; top: 100px; left: 100px;">Win iPhone!</button>
```

**Mitigations**:
1. X-Frame-Options: DENY
2. CSP frame-ancestors 'none'
3. JavaScript frame-busting (unreliable)

### Man-in-the-Middle (MITM)

**Attack**:
- Intercept HTTP traffic
- Steal session cookies
- Inject malicious content

**Mitigations**:
1. HSTS
2. Secure cookie attribute
3. Certificate pinning
4. upgrade-insecure-requests

### CSRF (Cross-Site Request Forgery)

**Attack**:
```html
<!-- Attacker's site -->
<img src="https://bank.com/transfer?to=attacker&amount=1000">
```

**Mitigations**:
1. SameSite=Strict/Lax cookies
2. CSRF tokens
3. Custom request headers
4. CSP form-action
5. Verify Origin/Referer headers

### Cookie Tossing

**Attack**:
```
# Attacker controls subdomain evil.example.com
Set-Cookie: session=malicious; Domain=example.com

# Victim at example.com receives attacker's cookie
```

**Mitigations**:
1. __Host- cookie prefix
2. Avoid Domain attribute
3. Cookie integrity checks

### MIME Sniffing Attacks

**Attack**:
```
# Upload polyglot file (valid image + JavaScript)
POST /upload
Content-Type: multipart/form-data

[polyglot.jpg containing JS]

# Later
<script src="/uploads/polyglot.jpg"></script>
# Without nosniff: Browser executes JS
```

**Mitigations**:
1. X-Content-Type-Options: nosniff
2. CSP script-src restrictions
3. File type validation
4. Separate upload domain

---

## Testing & Validation

### Manual Testing Tools

#### cURL
```bash
# Check security headers
curl -I https://example.com

# Specific header
curl -I https://example.com | grep -i strict-transport

# Test HSTS
curl -I https://example.com | grep -i strict-transport-security
```

#### Browser DevTools
```
1. Open DevTools (F12)
2. Network tab
3. Select request
4. Headers → Response Headers
5. Verify security headers present
```

### Online Testing Services

#### Mozilla Observatory
- URL: observatory.mozilla.org
- Grades: A+ to F
- Tests: CSP, HSTS, cookies, CORS, subresource integrity

#### SecurityHeaders.com
- URL: securityheaders.com
- Grades: A to F
- Fast header scanning
- Recommendations provided

#### SSL Labs
- URL: ssllabs.com/ssltest
- HSTS validation
- Certificate analysis
- Protocol support

#### CSP Evaluator
- URL: csp-evaluator.withgoogle.com
- CSP policy analysis
- Identifies bypasses
- Suggests improvements

### Automated Testing

#### npm: security-headers-check
```bash
npm install -g security-headers
security-headers check https://example.com
```

#### Python: requests + analysis
```python
import requests

def check_security_headers(url):
    r = requests.get(url)
    headers = r.headers

    checks = {
        'HSTS': 'Strict-Transport-Security' in headers,
        'CSP': 'Content-Security-Policy' in headers,
        'X-Frame-Options': 'X-Frame-Options' in headers,
        'X-Content-Type-Options': 'X-Content-Type-Options' in headers,
    }

    return checks
```

### CSP Violation Reporting

#### Report Endpoint
```python
# Flask example
@app.route('/csp-report', methods=['POST'])
def csp_report():
    report = request.get_json()

    # Log violation
    app.logger.warning(f"CSP Violation: {report}")

    # Store for analysis
    db.store_csp_violation(
        document_uri=report.get('csp-report', {}).get('document-uri'),
        violated_directive=report.get('csp-report', {}).get('violated-directive'),
        blocked_uri=report.get('csp-report', {}).get('blocked-uri'),
    )

    return '', 204
```

#### Report Format
```json
{
  "csp-report": {
    "document-uri": "https://example.com/page",
    "violated-directive": "script-src 'self'",
    "blocked-uri": "https://evil.com/malicious.js",
    "line-number": 35,
    "column-number": 12,
    "source-file": "https://example.com/page"
  }
}
```

### CI/CD Integration

#### GitHub Actions
```yaml
name: Security Headers Check

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Deploy preview
        run: npm run deploy:preview

      - name: Check headers
        run: |
          npm install -g security-headers
          security-headers check ${{ env.PREVIEW_URL }}
```

---

## Browser Compatibility

### HSTS

| Browser | Minimum Version | Notes |
|---------|-----------------|-------|
| Chrome | 4.0 | Full support |
| Firefox | 4.0 | Full support |
| Safari | 7.0 | Full support |
| Edge | 12.0 | Full support |
| IE | 11.0 | Partial support |

### CSP

| Level | Chrome | Firefox | Safari | Edge |
|-------|--------|---------|--------|------|
| CSP 1.0 | 25 | 23 | 7 | 12 |
| CSP 2.0 | 40 | 31 | 10 | 15 |
| CSP 3.0 | 59 | 58 | 15.4 | 79 |

**CSP 3 Features**:
- strict-dynamic: Chrome 52+, Firefox 52+
- worker-src: Chrome 59+, Firefox 58+
- Trusted Types: Chrome 83+

### SameSite Cookies

| Browser | Default=Lax | SameSite=None Requires Secure |
|---------|-------------|-------------------------------|
| Chrome | 80+ | 80+ |
| Firefox | 69+ | 69+ |
| Safari | 12.1+ | 12.1+ |
| Edge | 86+ | 86+ |

### Permissions-Policy

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome | 88+ | Full support |
| Edge | 88+ | Full support |
| Firefox | Partial | Some features only |
| Safari | Partial | Limited features |

**Fallback**: Use Feature-Policy for older browsers
```
Feature-Policy: geolocation 'self'; camera 'none'
Permissions-Policy: geolocation=(self), camera=()
```

### Referrer-Policy

| Browser | Minimum Version |
|---------|-----------------|
| Chrome | 61+ |
| Firefox | 50+ |
| Safari | 11.1+ |
| Edge | 79+ |

---

## Implementation Patterns

### Nginx

```nginx
# /etc/nginx/conf.d/security-headers.conf

# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# CSP
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;

# Frame protection
add_header X-Frame-Options "DENY" always;

# MIME sniffing protection
add_header X-Content-Type-Options "nosniff" always;

# XSS filter (disable)
add_header X-XSS-Protection "0" always;

# Referrer policy
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Permissions policy
add_header Permissions-Policy "geolocation=(), camera=(), microphone=()" always;
```

### Apache

```apache
# /etc/apache2/conf-available/security-headers.conf

<IfModule mod_headers.c>
    # HSTS
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"

    # CSP
    Header always set Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"

    # Frame protection
    Header always set X-Frame-Options "DENY"

    # MIME sniffing protection
    Header always set X-Content-Type-Options "nosniff"

    # XSS filter (disable)
    Header always set X-XSS-Protection "0"

    # Referrer policy
    Header always set Referrer-Policy "strict-origin-when-cross-origin"

    # Permissions policy
    Header always set Permissions-Policy "geolocation=(), camera=(), microphone=()"
</IfModule>
```

### Express.js (Node.js)

```javascript
const express = require('express');
const helmet = require('helmet');

const app = express();

// Use helmet middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
      styleSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
      fontSrc: ["'self'"],
      connectSrc: ["'self'"],
      frameAncestors: ["'none'"],
      baseUri: ["'self'"],
      formAction: ["'self'"]
    }
  },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  },
  frameguard: {
    action: 'deny'
  },
  noSniff: true,
  xssFilter: false,
  referrerPolicy: {
    policy: 'strict-origin-when-cross-origin'
  }
}));

// Custom Permissions-Policy (not in helmet)
app.use((req, res, next) => {
  res.setHeader('Permissions-Policy', 'geolocation=(), camera=(), microphone=()');
  next();
});
```

### Flask (Python)

```python
from flask import Flask, make_response
from functools import wraps

app = Flask(__name__)

def add_security_headers(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))

        # HSTS
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

        # CSP
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Frame protection
        response.headers['X-Frame-Options'] = 'DENY'

        # MIME sniffing protection
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # XSS filter (disable)
        response.headers['X-XSS-Protection'] = '0'

        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions policy
        response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'

        return response
    return decorated_function

@app.route('/')
@add_security_headers
def index():
    return 'Hello, World!'
```

### Django

```python
# settings.py

# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Force HTTPS
SECURE_SSL_REDIRECT = True

# Session cookies
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'

# CSRF cookies
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'

# Content type sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# Browser XSS protection (disable)
SECURE_BROWSER_XSS_FILTER = False

# Referrer policy
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# CSP (using django-csp)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)

# middleware.py
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # X-Frame-Options
        response['X-Frame-Options'] = 'DENY'

        # Permissions-Policy
        response['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'

        return response
```

### Next.js

```javascript
// next.config.js
module.exports = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains; preload'
          },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https:",
              "font-src 'self'",
              "connect-src 'self'",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'"
            ].join('; ')
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'X-XSS-Protection',
            value: '0'
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin'
          },
          {
            key: 'Permissions-Policy',
            value: 'geolocation=(), camera=(), microphone=()'
          }
        ]
      }
    ];
  }
};
```

---

## Security Header Grading

### Mozilla Observatory Grades

**A+ Grade Requirements**:
- CSP with no unsafe-inline or unsafe-eval
- HSTS with max-age ≥ 6 months
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY or CSP frame-ancestors
- Referrer-Policy set
- Subresource Integrity on external scripts
- No insecure protocols

**Common Downgrades**:
- CSP with unsafe-inline: A → B
- HSTS max-age < 6 months: -10 points
- Missing X-Content-Type-Options: -5 points
- Missing Referrer-Policy: -5 points

### SecurityHeaders.com Grades

**A Grade Requirements**:
- Strict-Transport-Security
- Content-Security-Policy
- X-Frame-Options
- X-Content-Type-Options
- Referrer-Policy

**A+ Requirements** (all A requirements plus):
- CSP with no unsafe directives
- HSTS preload
- Permissions-Policy

---

## Advanced Topics

### Nonce Rotation

**Per-Request Nonce**:
```python
import secrets
from flask import Flask, render_template, g

app = Flask(__name__)

@app.before_request
def generate_nonce():
    g.nonce = secrets.token_urlsafe(16)

@app.after_request
def add_csp(response):
    csp = f"script-src 'nonce-{g.nonce}'; object-src 'none'"
    response.headers['Content-Security-Policy'] = csp
    return response

@app.route('/')
def index():
    return render_template('index.html', nonce=g.nonce)
```

**Template**:
```html
<script nonce="{{ nonce }}">
  // Trusted inline script
</script>
```

### CSP for Single-Page Apps

**Challenge**: Inline styles in React/Vue

**Solution 1: Build-time hashes**
```javascript
// webpack plugin to generate CSP with hashes
const CspHtmlWebpackPlugin = require('csp-html-webpack-plugin');

module.exports = {
  plugins: [
    new CspHtmlWebpackPlugin({
      'script-src': ["'self'"],
      'style-src': ["'self'"]
    })
  ]
};
```

**Solution 2: Nonce injection**
```javascript
// Next.js middleware
export function middleware(request) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64');
  const cspHeader = `script-src 'self' 'nonce-${nonce}'; style-src 'self' 'nonce-${nonce}'`;

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce);
  requestHeaders.set('Content-Security-Policy', cspHeader);

  return NextResponse.next({
    request: {
      headers: requestHeaders
    }
  });
}
```

### Subresource Integrity (SRI)

**Purpose**: Verify external script integrity.

```html
<script
  src="https://cdn.example.com/library.js"
  integrity="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/ux..."
  crossorigin="anonymous">
</script>
```

**Generate Hash**:
```bash
curl https://cdn.example.com/library.js | openssl dgst -sha384 -binary | openssl base64 -A
```

**CSP Integration**:
```
Content-Security-Policy:
  script-src 'self' https://cdn.example.com;
  require-sri-for script style
```

---

## References

### Specifications
- CSP Level 3: W3C Working Draft
- Referrer Policy: W3C Candidate Recommendation
- SameSite Cookies: RFC 6265bis
- Permissions Policy: W3C Working Draft

### Tools
- Mozilla Observatory: https://observatory.mozilla.org
- SecurityHeaders.com: https://securityheaders.com
- CSP Evaluator: https://csp-evaluator.withgoogle.com
- SSL Labs: https://www.ssllabs.com/ssltest

### Libraries
- Helmet (Node.js): https://helmetjs.github.io
- django-csp (Python): https://django-csp.readthedocs.io
- secure_headers (Ruby): https://github.com/github/secure_headers

---

**Document Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: 1200+
