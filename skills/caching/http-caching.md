---
name: caching-http-caching
description: Browser and HTTP cache layer optimization using cache headers, conditional requests, and validation strategies
---

# HTTP Caching

**Last Updated**: 2025-10-25

## When to Use This Skill

**Activate when**:
- Optimizing web application performance
- Reducing server load and bandwidth costs
- Implementing proper cache headers for static assets
- Debugging browser caching issues
- Designing API caching strategies
- Implementing conditional requests (ETags, Last-Modified)
- Configuring CDN caching behavior

**Prerequisites**: `caching-fundamentals.md`, basic HTTP knowledge

**Related Skills**: `cdn-edge-caching.md`, `service-worker-caching.md`, `frontend-performance.md`

---

## Core Concepts

### HTTP Cache Flow

```
Browser Request
    ↓
1. Check browser cache
    ↓
2. Is cached? Is fresh?
    ├─ Yes (HIT) → Return from cache
    ├─ Expired → Revalidate with server
    └─ No (MISS) → Request from server
         ↓
3. Server response with cache headers
    ↓
4. Store in cache (if cacheable)
    ↓
5. Return to application
```

### Cache Headers Overview

```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

@dataclass
class HTTPCacheHeaders:
    """HTTP caching headers reference"""

    # Modern (HTTP/1.1)
    cache_control: str  # Primary caching directive
    etag: Optional[str] = None  # Entity tag for validation
    last_modified: Optional[str] = None  # Last modification time

    # Legacy (HTTP/1.0)
    expires: Optional[str] = None  # Absolute expiration time
    pragma: Optional[str] = None  # Legacy no-cache

    # Additional
    vary: Optional[str] = None  # Vary cache by headers
    age: Optional[int] = None  # Time in cache (seconds)

class CacheDirectives:
    """Cache-Control directive meanings"""

    DIRECTIVES = {
        # Cacheability
        "public": "Cacheable by any cache (browsers, CDNs)",
        "private": "Cacheable by browser only, not CDNs",
        "no-cache": "Must revalidate before use (NOT 'don't cache')",
        "no-store": "Don't cache at all (sensitive data)",

        # Expiration
        "max-age=<seconds>": "Fresh for N seconds from response time",
        "s-maxage=<seconds>": "Shared cache (CDN) max age, overrides max-age",
        "stale-while-revalidate=<seconds>": "Serve stale while updating",
        "stale-if-error=<seconds>": "Serve stale if origin errors",

        # Revalidation
        "must-revalidate": "Must not serve stale without revalidation",
        "proxy-revalidate": "Shared caches must revalidate",
        "immutable": "Never revalidate (content won't change)",
    }
```

---

## Cache-Control Header

### Basic Examples

```python
class CacheControlExamples:
    """Common Cache-Control configurations"""

    @staticmethod
    def static_assets():
        """
        Static assets with fingerprinting (e.g., app.abc123.js)

        Pattern: Long cache with immutable
        """
        return {
            "header": "Cache-Control",
            "value": "public, max-age=31536000, immutable",
            "explanation": "Cache for 1 year, never revalidate",
            "use_for": ["JS/CSS with hash", "Versioned images"]
        }

    @staticmethod
    def html_pages():
        """
        HTML pages (dynamic content)

        Pattern: No caching or short TTL with revalidation
        """
        return {
            "header": "Cache-Control",
            "value": "public, max-age=0, must-revalidate",
            "explanation": "Always revalidate before serving",
            "use_for": ["HTML pages", "API HTML responses"]
        }

    @staticmethod
    def api_responses():
        """
        API responses (read-heavy endpoints)

        Pattern: Short TTL with private caching
        """
        return {
            "header": "Cache-Control",
            "value": "private, max-age=300",
            "explanation": "Cache in browser for 5 minutes",
            "use_for": ["User-specific API data", "Dashboard APIs"]
        }

    @staticmethod
    def cdn_assets():
        """
        CDN-delivered assets

        Pattern: Long browser cache, longer CDN cache
        """
        return {
            "header": "Cache-Control",
            "value": "public, max-age=3600, s-maxage=86400",
            "explanation": "Browser: 1 hour, CDN: 24 hours",
            "use_for": ["Images", "Fonts", "Public assets"]
        }

    @staticmethod
    def no_caching():
        """
        Sensitive or always-fresh data

        Pattern: Complete cache prevention
        """
        return {
            "header": "Cache-Control",
            "value": "no-store, no-cache, must-revalidate, private",
            "explanation": "Never cache, always fetch fresh",
            "use_for": ["Sensitive data", "Real-time data"]
        }

    @staticmethod
    def stale_while_revalidate():
        """
        Serve stale content while updating (2024 pattern)

        Pattern: Balance freshness and performance
        """
        return {
            "header": "Cache-Control",
            "value": "public, max-age=60, stale-while-revalidate=300",
            "explanation": "Serve stale for 5min while revalidating",
            "use_for": ["News feeds", "Social media timelines"]
        }

# Implementation examples
def set_cache_headers_flask():
    """Flask example"""
    from flask import make_response

    @app.route('/api/data')
    def api_data():
        response = make_response({"data": "value"})
        response.headers['Cache-Control'] = 'private, max-age=300'
        return response

def set_cache_headers_express():
    """Express.js example"""
    # JavaScript
    """
    app.get('/api/data', (req, res) => {
      res.set('Cache-Control', 'private, max-age=300');
      res.json({ data: 'value' });
    });
    """

def set_cache_headers_fastapi():
    """FastAPI example"""
    from fastapi import Response

    @app.get("/api/data")
    async def api_data(response: Response):
        response.headers["Cache-Control"] = "private, max-age=300"
        return {"data": "value"}
```

### Modern Directives (2024)

```python
class ModernCacheDirectives:
    """2024 caching best practices"""

    @staticmethod
    def immutable_pattern():
        """
        Immutable directive (Chrome 54+, Firefox 49+)

        Prevents revalidation even on reload
        """
        return {
            "header": "Cache-Control: public, max-age=31536000, immutable",
            "benefit": "No revalidation on refresh (F5)",
            "use_case": "Fingerprinted assets (app.[hash].js)",
            "support": "All modern browsers (2024)"
        }

    @staticmethod
    def stale_while_revalidate_pattern():
        """
        Serve stale while updating in background

        Chrome 75+, Firefox 68+
        """
        return {
            "header": "Cache-Control: max-age=60, stale-while-revalidate=86400",
            "behavior": [
                "< 60s: Serve from cache (fresh)",
                "60s - 24h: Serve stale, revalidate async",
                "> 24h: Block until revalidated"
            ],
            "benefit": "Instant responses + background updates",
            "support": "Chrome, Firefox, Safari 16+"
        }

    @staticmethod
    def stale_if_error_pattern():
        """
        Serve stale on server errors

        Resilience pattern for high availability
        """
        return {
            "header": "Cache-Control: max-age=3600, stale-if-error=86400",
            "behavior": "Serve stale up to 24h if origin returns 5xx",
            "benefit": "Graceful degradation during outages",
            "use_case": "Critical APIs, high-availability content"
        }
```

---

## Conditional Requests

### ETag (Entity Tag)

**Concept**: Hash/version of content for validation

```python
import hashlib
from typing import Optional

class ETagHandler:
    """ETag generation and validation"""

    @staticmethod
    def generate_etag(content: str) -> str:
        """
        Generate ETag from content

        Strong ETag: byte-for-byte match required
        Weak ETag: semantic equivalence (W/"...")
        """
        # Strong ETag
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f'"{hash_value}"'

    @staticmethod
    def generate_weak_etag(content: str) -> str:
        """
        Weak ETag for semantic equivalence

        Use when minor differences acceptable (whitespace, formatting)
        """
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f'W/"{hash_value}"'

    @staticmethod
    def validate_etag(request_etag: str, current_etag: str) -> bool:
        """Check if ETags match"""
        # Strip W/ prefix for weak comparison
        req = request_etag.replace('W/', '')
        cur = current_etag.replace('W/', '')
        return req == cur

# Flask implementation
def etag_example_flask():
    from flask import Flask, request, make_response

    app = Flask(__name__)

    @app.route('/api/data')
    def api_data():
        content = get_current_data()  # {"data": "value"}
        content_str = json.dumps(content, sort_keys=True)

        # Generate ETag
        etag = ETagHandler.generate_etag(content_str)

        # Check If-None-Match header
        if_none_match = request.headers.get('If-None-Match')

        if if_none_match == etag:
            # Content unchanged - return 304 Not Modified
            response = make_response('', 304)
            response.headers['ETag'] = etag
            return response

        # Content changed - return 200 with data
        response = make_response(content)
        response.headers['ETag'] = etag
        response.headers['Cache-Control'] = 'private, max-age=300'
        return response

# FastAPI implementation
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/api/data")
async def api_data(request: Request):
    content = {"data": "value"}
    content_str = json.dumps(content, sort_keys=True)

    # Generate ETag
    etag = ETagHandler.generate_etag(content_str)

    # Check If-None-Match
    if_none_match = request.headers.get("if-none-match")

    if if_none_match == etag:
        # Not modified
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})

    # Return data with ETag
    return JSONResponse(
        content=content,
        headers={
            "ETag": etag,
            "Cache-Control": "private, max-age=300"
        }
    )
```

### Last-Modified / If-Modified-Since

```python
from datetime import datetime
from email.utils import formatdate, parsedate_to_datetime

class LastModifiedHandler:
    """Last-Modified header handling"""

    @staticmethod
    def format_http_date(dt: datetime) -> str:
        """Convert datetime to HTTP date format"""
        # HTTP date: Wed, 21 Oct 2015 07:28:00 GMT
        return formatdate(dt.timestamp(), usegmt=True)

    @staticmethod
    def parse_http_date(date_str: str) -> datetime:
        """Parse HTTP date string to datetime"""
        return parsedate_to_datetime(date_str)

    @staticmethod
    def is_modified_since(last_modified: datetime, if_modified_since: Optional[str]) -> bool:
        """
        Check if content was modified since given time

        Returns: True if modified (send full response)
        """
        if not if_modified_since:
            return True  # No conditional request

        try:
            client_time = LastModifiedHandler.parse_http_date(if_modified_since)
            # Compare (truncate to seconds, HTTP dates have 1s precision)
            return last_modified.timestamp() > client_time.timestamp()
        except Exception:
            return True  # Parse error, send full response

# Flask example
@app.route('/api/document/<int:doc_id>')
def get_document(doc_id):
    doc = get_document_from_db(doc_id)  # Returns {content, updated_at}

    last_modified = doc['updated_at']
    last_modified_str = LastModifiedHandler.format_http_date(last_modified)

    # Check If-Modified-Since
    if_modified_since = request.headers.get('If-Modified-Since')

    if not LastModifiedHandler.is_modified_since(last_modified, if_modified_since):
        # Not modified
        response = make_response('', 304)
        response.headers['Last-Modified'] = last_modified_str
        return response

    # Modified - return full document
    response = make_response(doc['content'])
    response.headers['Last-Modified'] = last_modified_str
    response.headers['Cache-Control'] = 'private, max-age=300'
    return response
```

---

## Vary Header

**Purpose**: Vary cache by request headers (e.g., Accept-Encoding, User-Agent)

```python
class VaryHeaderExamples:
    """Vary header patterns"""

    @staticmethod
    def vary_by_encoding():
        """
        Vary by Accept-Encoding

        Cache separate versions for gzip, br, etc.
        """
        return {
            "header": "Vary: Accept-Encoding",
            "use_case": "Compressed responses",
            "example": "Same content, different compression"
        }

    @staticmethod
    def vary_by_auth():
        """
        Vary by Authorization

        Prevent caching of authenticated content
        """
        return {
            "header": "Vary: Authorization",
            "use_case": "User-specific content",
            "warning": "Often better to use Cache-Control: private"
        }

    @staticmethod
    def vary_by_multiple():
        """
        Vary by multiple headers

        Cache multiplied by combinations
        """
        return {
            "header": "Vary: Accept-Encoding, Accept-Language",
            "use_case": "i18n content with compression",
            "warning": "Cache fragmentation (many variants)"
        }

# Implementation
@app.route('/api/content')
def get_content():
    accept_encoding = request.headers.get('Accept-Encoding', '')
    accept_language = request.headers.get('Accept-Language', 'en')

    # Generate appropriate content
    content = get_localized_content(accept_language)

    response = make_response(content)
    response.headers['Vary'] = 'Accept-Encoding, Accept-Language'
    response.headers['Cache-Control'] = 'public, max-age=3600'

    return response
```

---

## Cache Busting Strategies

### 1. Fingerprinting / Hashing

**Best Practice**: Include content hash in filename

```python
import hashlib
import os

class CacheBusting:
    """Cache busting strategies"""

    @staticmethod
    def fingerprint_filename(filepath: str) -> str:
        """
        Add content hash to filename

        Example: app.js → app.a1b2c3d4.js
        """
        with open(filepath, 'rb') as f:
            content = f.read()

        # Generate hash
        hash_value = hashlib.md5(content).hexdigest()[:8]

        # Insert hash before extension
        name, ext = os.path.splitext(filepath)
        return f"{name}.{hash_value}{ext}"

    @staticmethod
    def query_string_versioning(url: str, version: str) -> str:
        """
        Add version query parameter

        Less ideal (some caches ignore query params)
        """
        separator = '&' if '?' in url else '?'
        return f"{url}{separator}v={version}"

# Build tool integration (example)
"""
# Webpack/Vite automatically handles this:

// webpack.config.js
module.exports = {
  output: {
    filename: '[name].[contenthash].js',
  },
};

// Results in: main.a1b2c3d4.js
// HTML references updated automatically
"""

# HTML generation
def generate_asset_url(asset_path: str, version: Optional[str] = None) -> str:
    """
    Generate versioned asset URL

    Development: /static/app.js
    Production: /static/app.a1b2c3d4.js
    """
    if os.environ.get('ENV') == 'production':
        return CacheBusting.fingerprint_filename(asset_path)
    else:
        return asset_path
```

### 2. Immutable Assets

```html
<!-- Immutable pattern with long cache -->
<link rel="stylesheet" href="/static/app.a1b2c3d4.css">
<!-- Server sends: Cache-Control: public, max-age=31536000, immutable -->

<!-- Non-fingerprinted assets: short cache -->
<link rel="stylesheet" href="/static/app.css">
<!-- Server sends: Cache-Control: public, max-age=300 -->
```

---

## Testing Cache Headers

### Using curl

```bash
# Check response headers
curl -I https://example.com/api/data

# Check with If-None-Match (ETag validation)
curl -H "If-None-Match: \"abc123\"" -I https://example.com/api/data

# Check with If-Modified-Since
curl -H "If-Modified-Since: Wed, 21 Oct 2015 07:28:00 GMT" -I \
  https://example.com/api/data

# Verbose output
curl -v https://example.com/api/data
```

### Browser DevTools

```javascript
// Chrome DevTools Network tab:
// 1. Open DevTools (F12)
// 2. Network tab
// 3. Disable cache checkbox (for testing)
// 4. Look at "Size" column:
//    - "(disk cache)" = from disk cache
//    - "(memory cache)" = from memory cache
//    - "304 Not Modified" = conditional request successful
//    - File size = fresh request

// Inspect headers
fetch('/api/data')
  .then(response => {
    console.log('Cache-Control:', response.headers.get('cache-control'));
    console.log('ETag:', response.headers.get('etag'));
    console.log('Age:', response.headers.get('age'));
  });
```

---

## Patterns

### Pattern 1: Static Asset Pipeline

```python
class StaticAssetCaching:
    """Optimal caching for static assets"""

    @staticmethod
    def configure_asset_caching():
        """
        Different strategies for different asset types
        """
        return {
            "fingerprinted_assets": {
                "pattern": "*.{hash}.{js,css,png,jpg}",
                "cache_control": "public, max-age=31536000, immutable",
                "explanation": "Content-addressed, never changes"
            },
            "fonts": {
                "pattern": "*.{woff,woff2,ttf}",
                "cache_control": "public, max-age=31536000, immutable",
                "explanation": "Fonts rarely change"
            },
            "images_without_hash": {
                "pattern": "*.{png,jpg,svg}",
                "cache_control": "public, max-age=2592000",  # 30 days
                "explanation": "Long but not immutable"
            },
            "html": {
                "pattern": "*.html",
                "cache_control": "public, max-age=0, must-revalidate",
                "explanation": "Always check for updates"
            }
        }

# Nginx configuration
"""
# Fingerprinted assets
location ~* \.[\da-f]{8}\.(js|css)$ {
    add_header Cache-Control "public, max-age=31536000, immutable";
}

# Fonts
location ~* \.(woff|woff2|ttf)$ {
    add_header Cache-Control "public, max-age=31536000, immutable";
}

# HTML
location ~* \.html$ {
    add_header Cache-Control "public, max-age=0, must-revalidate";
}
"""
```

---

## Anti-Patterns

### ❌ No Cache Headers
```python
# WRONG: Missing cache headers
@app.route('/api/data')
def api_data():
    return {"data": "value"}
# Browser uses heuristic caching (unpredictable)

# CORRECT: Explicit cache headers
@app.route('/api/data')
def api_data():
    response = make_response({"data": "value"})
    response.headers['Cache-Control'] = 'private, max-age=300'
    return response
```

### ❌ Confusing no-cache and no-store
```python
# WRONG: Using no-cache to prevent caching
response.headers['Cache-Control'] = 'no-cache'
# "no-cache" means "revalidate before use", NOT "don't cache"

# CORRECT: Use no-store to prevent caching
response.headers['Cache-Control'] = 'no-store'
```

### ❌ Caching Personalized Content
```python
# WRONG: Public cache for user-specific data
@app.route('/api/user/profile')
def user_profile():
    response = make_response(get_user_data())
    response.headers['Cache-Control'] = 'public, max-age=3600'
    # CDN will cache and serve to wrong users!
    return response

# CORRECT: Private cache only
@app.route('/api/user/profile')
def user_profile():
    response = make_response(get_user_data())
    response.headers['Cache-Control'] = 'private, max-age=300'
    return response
```

---

## Quick Reference

### Cache-Control Directives
| Directive | Meaning | Use Case |
|-----------|---------|----------|
| public | Any cache can store | Static assets, public APIs |
| private | Browser only, no CDN | User-specific data |
| no-cache | Revalidate before use | HTML, frequently updated |
| no-store | Don't cache | Sensitive data |
| max-age=N | Fresh for N seconds | All cacheable content |
| s-maxage=N | CDN max age | CDN-delivered content |
| immutable | Never revalidate | Fingerprinted assets |
| stale-while-revalidate=N | Serve stale while updating | Balance freshness/performance |

### Status Codes
| Code | Meaning | Use Case |
|------|---------|----------|
| 200 OK | Full response | Normal response |
| 304 Not Modified | Content unchanged | Successful conditional request |
| 412 Precondition Failed | Condition not met | Failed conditional request |

---

## Related Skills

**Next Steps**:
- `cdn-edge-caching.md` → CDN configuration and optimization
- `service-worker-caching.md` → Progressive Web App caching
- `cache-performance-monitoring.md` → Measuring cache effectiveness

**Foundations**:
- `caching-fundamentals.md` → Core caching concepts
- `frontend-performance.md` → Overall web performance

---

## Summary

HTTP caching optimizes web performance through browser and intermediate caches:
- **Cache-Control**: Modern directive for caching behavior (public, private, max-age, immutable)
- **Conditional Requests**: ETags and Last-Modified for validation
- **Vary**: Cache variations based on request headers
- **Cache Busting**: Fingerprinting for immutable assets

**Key takeaways**:
1. Use Cache-Control (not Expires) for modern caching
2. Fingerprint assets for long-term caching with immutable
3. Implement ETags for efficient revalidation
4. Use private for user-specific, public for shared content
5. Test cache behavior with curl and browser DevTools

**Next**: Move to `cdn-edge-caching.md` for CDN optimization.
