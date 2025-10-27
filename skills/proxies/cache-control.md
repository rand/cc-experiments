---
name: proxies-cache-control
description: HTTP caching strategies including cache headers, CDN patterns, cache invalidation, stale-while-revalidate, and edge caching optimization
---

# Cache Control

**Scope**: HTTP caching, cache headers, CDN patterns, invalidation strategies
**Lines**: ~380
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Implementing HTTP caching strategies
- Optimizing CDN usage
- Configuring cache headers
- Debugging cache-related issues
- Implementing cache invalidation
- Setting up edge caching
- Optimizing web performance
- Working with proxy caches

## Core Concepts

### HTTP Caching Layers

```
Client → Browser Cache → CDN Edge → Origin Cache → Origin Server
         (private)       (shared)    (shared)       (source)
```

**Cache Types**:
- **Private Cache**: Browser cache (single user)
- **Shared Cache**: CDN, proxy cache (multiple users)
- **Gateway Cache**: Reverse proxy cache (nginx, Varnish)

### Cache-Control Directives

**Request Directives**:
```http
Cache-Control: no-cache           # Revalidate with origin
Cache-Control: no-store           # Don't cache at all
Cache-Control: max-age=0          # Immediate revalidation
Cache-Control: max-stale=3600     # Accept stale up to 1h
Cache-Control: min-fresh=60       # Must be fresh for 60s
Cache-Control: only-if-cached     # Return cached or 504
```

**Response Directives**:
```http
Cache-Control: public             # Cacheable by any cache
Cache-Control: private            # Only browser cache
Cache-Control: no-cache           # Must revalidate
Cache-Control: no-store           # Don't cache
Cache-Control: max-age=3600       # Fresh for 1 hour
Cache-Control: s-maxage=7200      # Shared cache max age
Cache-Control: must-revalidate    # Must revalidate when stale
Cache-Control: proxy-revalidate   # Shared caches must revalidate
Cache-Control: immutable          # Never changes
```

---

## Patterns

### Pattern 1: Static Assets with Immutable Caching

**Use Case**: JavaScript, CSS, images with content hashing

```http
# ❌ Bad: Short cache time
GET /app.js HTTP/1.1
Response:
Cache-Control: max-age=3600

# ✅ Good: Immutable with content hash
GET /app.abc123def.js HTTP/1.1
Response:
Cache-Control: public, max-age=31536000, immutable
```

```nginx
# Nginx configuration
location ~* \.(?:css|js|jpg|jpeg|png|gif|ico|svg|woff|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;

    # Enable gzip for compressible assets
    gzip_static on;
}
```

**Benefits**:
- Maximum cache efficiency
- Eliminates revalidation requests
- Content hash prevents stale content
- CDN-friendly

### Pattern 2: API Responses with Conditional Requests

**Use Case**: Frequently accessed but changing data

```python
# ❌ Bad: No caching
@app.route('/api/users/<user_id>')
def get_user(user_id):
    user = get_user_from_db(user_id)
    return jsonify(user)
```

```python
# ✅ Good: ETag with conditional requests
from flask import Flask, jsonify, request, make_response
import hashlib

@app.route('/api/users/<user_id>')
def get_user(user_id):
    user = get_user_from_db(user_id)
    user_json = jsonify(user).get_data()

    # Generate ETag
    etag = hashlib.md5(user_json).hexdigest()

    # Check If-None-Match
    if request.headers.get('If-None-Match') == f'"{etag}"':
        return '', 304  # Not Modified

    response = make_response(jsonify(user))
    response.headers['ETag'] = f'"{etag}"'
    response.headers['Cache-Control'] = 'private, max-age=60, must-revalidate'
    return response
```

**Benefits**:
- Bandwidth savings with 304 responses
- Reduced server processing
- Guaranteed fresh data
- Works with CDNs

### Pattern 3: Stale-While-Revalidate

**Use Case**: Balance freshness and performance

```http
# ✅ Serve stale while fetching fresh
Cache-Control: max-age=60, stale-while-revalidate=300

# Timeline:
# 0-60s: Serve from cache (fresh)
# 60-360s: Serve from cache (stale) + async revalidate
# 360s+: Must fetch from origin
```

```nginx
# Nginx configuration
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g;

server {
    location /api/ {
        proxy_cache api_cache;
        proxy_cache_valid 200 60s;
        proxy_cache_use_stale updating;  # Serve stale while updating
        proxy_cache_background_update on;
        proxy_cache_lock on;

        add_header X-Cache-Status $upstream_cache_status;
        proxy_pass http://backend;
    }
}
```

---

## Cache Invalidation Strategies

### 1. Time-Based Expiration

```http
# Simple time-based
Cache-Control: max-age=3600

# Different for shared vs private
Cache-Control: private, max-age=300, s-maxage=3600
```

### 2. ETag/Last-Modified Validation

```python
from datetime import datetime

@app.route('/api/article/<article_id>')
def get_article(article_id):
    article = get_article_from_db(article_id)

    # Last-Modified header
    last_modified = article['updated_at'].strftime('%a, %d %b %Y %H:%M:%S GMT')

    # Check If-Modified-Since
    if_modified = request.headers.get('If-Modified-Since')
    if if_modified and if_modified == last_modified:
        return '', 304

    response = make_response(jsonify(article))
    response.headers['Last-Modified'] = last_modified
    response.headers['Cache-Control'] = 'private, max-age=300'
    return response
```

### 3. Cache Purging

```python
# Purge specific URL from cache
import requests

def purge_cache(url: str):
    """Send PURGE request to proxy cache"""
    try:
        response = requests.request('PURGE', url)
        return response.status_code == 200
    except:
        return False

# Usage
purge_cache('https://cdn.example.com/api/users/123')
```

```bash
# Nginx cache purge
curl -X PURGE https://example.com/cached-page

# Varnish cache purge
curl -X BAN -H "X-Ban-Url: /api/users/.*" http://localhost:6081/
```

### 4. Surrogate-Control for CDN

```http
# Control CDN cache separately from browser cache
Cache-Control: private, max-age=60
Surrogate-Control: max-age=3600

# CDN uses Surrogate-Control (3600s)
# Browser uses Cache-Control (60s)
```

---

## CDN Configuration

### Cloudflare

```javascript
// Cloudflare Workers - Custom caching
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const cache = caches.default
  const cacheKey = new Request(request.url, request)

  // Check cache
  let response = await cache.match(cacheKey)

  if (!response) {
    // Fetch from origin
    response = await fetch(request)

    // Clone response (can only read once)
    response = new Response(response.body, response)

    // Set custom cache headers
    response.headers.set('Cache-Control', 'public, max-age=3600')
    response.headers.set('X-Cache-Status', 'MISS')

    // Store in cache
    event.waitUntil(cache.put(cacheKey, response.clone()))
  } else {
    response.headers.set('X-Cache-Status', 'HIT')
  }

  return response
}
```

### AWS CloudFront

```json
{
  "CacheBehaviors": [
    {
      "PathPattern": "/api/*",
      "TargetOriginId": "api-origin",
      "ViewerProtocolPolicy": "redirect-to-https",
      "AllowedMethods": ["GET", "HEAD", "OPTIONS"],
      "CachedMethods": ["GET", "HEAD", "OPTIONS"],
      "Compress": true,
      "MinTTL": 0,
      "DefaultTTL": 300,
      "MaxTTL": 3600,
      "ForwardedValues": {
        "QueryString": true,
        "Headers": ["Authorization", "Accept"],
        "Cookies": {
          "Forward": "none"
        }
      }
    },
    {
      "PathPattern": "/static/*",
      "TargetOriginId": "static-origin",
      "ViewerProtocolPolicy": "redirect-to-https",
      "Compress": true,
      "MinTTL": 31536000,
      "DefaultTTL": 31536000,
      "MaxTTL": 31536000
    }
  ]
}
```

---

## Implementation Examples

### Python with Flask-Caching

```python
from flask import Flask
from flask_caching import Cache

app = Flask(__name__)

# Configure cache
cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': 'localhost',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_DEFAULT_TIMEOUT': 300
})

@app.route('/api/expensive')
@cache.cached(timeout=60, query_string=True)
def expensive_operation():
    """Cached for 60 seconds, varies by query string"""
    result = perform_expensive_calculation()
    return jsonify(result)

@app.route('/api/users/<user_id>')
@cache.memoize(timeout=120)
def get_user(user_id):
    """Cached per user_id for 120 seconds"""
    user = get_user_from_db(user_id)
    return jsonify(user)

# Manual cache control
@app.route('/api/data')
def get_data():
    cache_key = f"data:{request.args.get('filter')}"

    # Try cache first
    data = cache.get(cache_key)
    if data is None:
        data = fetch_data()
        cache.set(cache_key, data, timeout=300)

    response = make_response(jsonify(data))
    response.headers['Cache-Control'] = 'private, max-age=300'
    return response

# Cache invalidation
@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    update_user_in_db(user_id, request.json)

    # Invalidate cache
    cache.delete_memoized(get_user, user_id)

    return jsonify({'status': 'updated'})
```

### Go with groupcache

```go
package main

import (
    "context"
    "fmt"
    "github.com/golang/groupcache"
    "net/http"
)

var dataCache *groupcache.Group

func init() {
    // Create cache group
    dataCache = groupcache.NewGroup("data", 64<<20, groupcache.GetterFunc(
        func(ctx context.Context, key string, dest groupcache.Sink) error {
            // Fetch from source (called on cache miss)
            data, err := fetchDataFromDB(key)
            if err != nil {
                return err
            }
            dest.SetBytes([]byte(data))
            return nil
        },
    ))
}

func handleRequest(w http.ResponseWriter, r *http.Request) {
    key := r.URL.Path

    var data []byte
    err := dataCache.Get(r.Context(), key, groupcache.AllocatingByteSliceSink(&data))
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }

    // Set cache headers
    w.Header().Set("Cache-Control", "public, max-age=3600")
    w.Header().Set("Content-Type", "application/json")
    w.Write(data)
}

func fetchDataFromDB(key string) (string, error) {
    // Simulate database query
    return fmt.Sprintf(`{"key": "%s", "value": "data"}`, key), nil
}

func main() {
    http.HandleFunc("/", handleRequest)
    http.ListenAndServe(":8080", nil)
}
```

---

## Cache Key Design

### Good Cache Key Patterns

```python
# ✅ Good: Include all varying factors
cache_key = f"user:{user_id}:profile:v{api_version}"
cache_key = f"search:{query}:{page}:{sort}:{filter}"
cache_key = f"product:{product_id}:{lang}:{currency}"

# ❌ Bad: Missing important factors
cache_key = f"user:{user_id}"  # Doesn't vary by API version
cache_key = f"search:{query}"  # Doesn't vary by pagination
```

### Cache Key Normalization

```python
def normalize_cache_key(params: dict) -> str:
    """Create consistent cache key from parameters"""
    # Sort keys for consistency
    sorted_params = sorted(params.items())

    # Normalize values
    normalized = []
    for key, value in sorted_params:
        if isinstance(value, list):
            value = ','.join(sorted(str(v) for v in value))
        normalized.append(f"{key}={value}")

    return ':'.join(normalized)

# Usage
cache_key = normalize_cache_key({
    'user_id': 123,
    'filters': ['active', 'premium'],
    'page': 2
})
# Result: "filters=active,premium:page=2:user_id=123"
```

---

## Best Practices

### 1. Use Appropriate Cache Directives

```http
# Static assets (with versioning)
Cache-Control: public, max-age=31536000, immutable

# User-specific data
Cache-Control: private, max-age=300

# Frequently changing data
Cache-Control: private, max-age=60, must-revalidate

# Never cache
Cache-Control: no-store, no-cache, must-revalidate
```

### 2. Implement Cache Warming

```python
# Pre-populate cache with frequently accessed data
def warm_cache():
    popular_items = get_popular_items()

    for item_id in popular_items:
        cache_key = f"item:{item_id}"
        data = fetch_item_data(item_id)
        cache.set(cache_key, data, timeout=3600)

# Run on startup or scheduled
warm_cache()
```

### 3. Monitor Cache Hit Rates

```python
from prometheus_client import Counter, Histogram

cache_hits = Counter('cache_hits_total', 'Total cache hits')
cache_misses = Counter('cache_misses_total', 'Total cache misses')
cache_latency = Histogram('cache_operation_seconds', 'Cache operation latency')

@cache_latency.time()
def get_cached_data(key):
    data = cache.get(key)
    if data:
        cache_hits.inc()
        return data
    else:
        cache_misses.inc()
        data = fetch_data(key)
        cache.set(key, data)
        return data
```

---

## Troubleshooting

### Issue 1: Stale Cache

**Symptoms**: Users seeing old data
**Common Causes**:
- Long max-age values
- Missing cache invalidation
- Clock skew

**Solutions**:
```python
# 1. Use shorter TTLs with revalidation
response.headers['Cache-Control'] = 'max-age=60, must-revalidate'

# 2. Implement cache versioning
cache_key = f"data:{version}:{id}"

# 3. Use ETags for validation
response.headers['ETag'] = generate_etag(data)
```

### Issue 2: Cache Stampede

**Symptoms**: Multiple requests hit origin simultaneously
**Solution**:

```python
import threading

locks = {}

def get_with_lock(key: str):
    """Prevent cache stampede with locking"""
    # Try cache first
    data = cache.get(key)
    if data is not None:
        return data

    # Acquire lock for this key
    if key not in locks:
        locks[key] = threading.Lock()

    with locks[key]:
        # Check cache again (another thread may have filled it)
        data = cache.get(key)
        if data is not None:
            return data

        # Fetch and cache
        data = fetch_data(key)
        cache.set(key, data, timeout=300)
        return data
```

---

## Related Skills

- `proxies-nginx-configuration` - Nginx caching configuration
- `proxies-reverse-proxy` - Reverse proxy caching
- `protocols-http-fundamentals` - HTTP headers and caching
- `database-redis` - Redis as cache backend
- `observability-performance-monitoring` - Cache metrics

---

**Last Updated**: 2025-10-27
