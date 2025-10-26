---
name: caching-cdn-edge-caching
description: CDN and edge cache optimization with Cloudflare, Fastly, and CloudFront for global performance and reduced origin load
---

# CDN Edge Caching

**Last Updated**: 2025-10-25

## When to Use This Skill

**Activate when**:
- Delivering content globally with low latency
- Reducing origin server load and bandwidth costs
- Implementing edge caching with Cloudflare, Fastly, or CloudFront
- Optimizing TTFB (Time To First Byte) performance
- Configuring cache purging and invalidation at scale
- Setting up geo-caching and regional optimization
- Debugging CDN cache behavior and hit rates

**Prerequisites**: `http-caching.md`, `caching-fundamentals.md`, basic CDN knowledge

**Related Skills**: `cache-invalidation-strategies.md`, `cloudflare-workers.md`, `frontend-performance.md`

---

## Core Concepts

### CDN Architecture

```
User Request → Edge Server (PoP) → Origin Shield → Origin Server
    (10-50ms)      (cache check)      (optional)      (100-500ms)

Edge Cache Hierarchy:
1. Edge PoP (Point of Presence) - 200+ locations globally
2. Origin Shield (optional) - Regional cache tier
3. Origin Server - Your application/storage
```

### Performance Impact (2024 Data)

```python
from dataclasses import dataclass

@dataclass
class CDNPerformanceMetrics:
    """Real-world CDN performance improvements"""

    # TTFB improvements with edge caching
    without_cdn = {
        "average_ttfb": "402ms",
        "p95_ttfb": "800ms",
        "origin_requests": "100%"
    }

    with_cdn = {
        "average_ttfb": "207ms",  # 49% improvement
        "p95_ttfb": "350ms",      # 56% improvement
        "cache_hit_rate": "85-95%",
        "origin_requests": "5-15%"
    }

    # Case study: Optimized edge TTL
    edge_ttl_optimization = {
        "before": "Edge TTL: 1 hour",
        "after": "Edge TTL: 1 week",
        "result": "Long-tail content cached, 70% TTFB reduction (500ms → 150ms)"
    }

    # Netflix 2022 optimization
    netflix_case_study = {
        "change": "Mixed invalidation + expiration approach",
        "cpu_reduction": "30%",
        "cache_efficiency": "Maintained data freshness"
    }
```

---

## Cloudflare Edge Caching

### 1. Cache Rules

**Concept**: Control caching behavior based on URL patterns, file types, conditions

```javascript
// Cloudflare Workers example
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Define cache behavior by path
    let cacheControl;

    if (url.pathname.match(/\.(js|css|png|jpg|svg)$/)) {
      // Static assets - long cache
      cacheControl = 'public, max-age=31536000, immutable';
    } else if (url.pathname.startsWith('/api/')) {
      // API responses - short cache
      cacheControl = 'public, max-age=300, s-maxage=600';
    } else if (url.pathname.endsWith('.html')) {
      // HTML - always revalidate
      cacheControl = 'public, max-age=0, must-revalidate';
    } else {
      // Default
      cacheControl = 'public, max-age=3600';
    }

    // Fetch from origin
    const response = await fetch(request);

    // Clone response and add cache header
    const newResponse = new Response(response.body, response);
    newResponse.headers.set('Cache-Control', cacheControl);

    return newResponse;
  }
};
```

### 2. Edge TTL Configuration

```python
class CloudflareEdgeTTL:
    """Cloudflare Edge TTL best practices (2024)"""

    @staticmethod
    def dynamic_content():
        """
        Dynamic content with short Edge TTL

        Ensures content freshness for frequently updated data
        """
        return {
            "edge_ttl": "1-4 hours",
            "browser_ttl": "5 minutes",
            "use_case": "News feeds, dashboards",
            "headers": "Cache-Control: public, max-age=300, s-maxage=3600"
        }

    @staticmethod
    def static_content():
        """
        Static content with long Edge TTL

        2024 optimization: 1 week is sweet spot
        """
        return {
            "edge_ttl": "1 week (604800s)",
            "browser_ttl": "1 hour",
            "use_case": "Images, fonts, versioned assets",
            "headers": "Cache-Control: public, max-age=3600, s-maxage=604800",
            "benefit": "Long-tail content cached at edge"
        }

    @staticmethod
    def api_responses():
        """
        API responses with balanced TTL

        Longer edge cache than browser for shared caching
        """
        return {
            "edge_ttl": "10 minutes",
            "browser_ttl": "1 minute",
            "use_case": "Public APIs, product catalogs",
            "headers": "Cache-Control: public, max-age=60, s-maxage=600"
        }

# Cloudflare Page Rules (Dashboard configuration)
"""
URL Pattern: example.com/static/*
Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 week
  - Browser Cache TTL: 1 hour

URL Pattern: example.com/api/*
Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 10 minutes
  - Browser Cache TTL: 1 minute
  - Bypass Cache on Cookie: yes
"""
```

### 3. Tiered Cache

**Concept**: Multi-tier caching to reduce origin requests

```python
class CloudflareTieredCache:
    """
    Tiered Cache optimization (included with all plans)

    Flow: Edge PoP → Regional Tier → Origin
    """

    benefits = {
        "reduced_origin_load": "Upper-tier PoPs cache for lower-tier",
        "improved_hit_rate": "Regional cache serves multiple edge locations",
        "lower_bandwidth": "Fewer origin fetches",
        "automatic": "No configuration needed (enabled by default)"
    }

    # How it works
    """
    1. User in Asia requests /image.jpg
    2. Asia PoP checks local cache (MISS)
    3. Asia PoP checks regional tier (Singapore)
    4. Regional tier has cached copy (HIT)
    5. Regional tier serves to Asia PoP
    6. Asia PoP caches and serves to user

    Next request from Japan:
    - Japan PoP → Singapore regional → Cached! (no origin)
    """
```

### 4. Bypass Cache on Cookie

```javascript
// Cloudflare Worker: Bypass cache for authenticated users
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Check for session cookie
    const cookies = request.headers.get('Cookie') || '';
    const hasSessionCookie = cookies.includes('session_id=');

    if (hasSessionCookie) {
      // Bypass cache for authenticated users
      const response = await fetch(request, {
        cf: { cacheEverything: false }
      });

      const newResponse = new Response(response.body, response);
      newResponse.headers.set('Cache-Control', 'private, no-cache');
      return newResponse;
    }

    // Cache for anonymous users
    const response = await fetch(request, {
      cf: {
        cacheEverything: true,
        cacheTtl: 3600
      }
    });

    return response;
  }
};
```

---

## Fastly Edge Caching

### 1. VCL (Varnish Configuration Language)

```vcl
# Fastly VCL example
sub vcl_recv {
  # Skip cache for authenticated requests
  if (req.http.Cookie ~ "session_id") {
    return(pass);
  }

  # Normalize URL for better cache hit rate
  if (req.url ~ "\?$") {
    set req.url = regsub(req.url, "\?$", "");
  }

  # Set cache key
  set req.hash += req.url;
  set req.hash += req.http.host;
}

sub vcl_fetch {
  # Override cache TTL based on content type
  if (beresp.http.Content-Type ~ "image/") {
    set beresp.ttl = 7d;  # 1 week for images
    set beresp.http.Cache-Control = "public, max-age=604800";
  }

  if (beresp.http.Content-Type ~ "application/json") {
    set beresp.ttl = 5m;  # 5 minutes for JSON APIs
    set beresp.http.Cache-Control = "public, max-age=300";
  }

  return(deliver);
}

sub vcl_deliver {
  # Add cache status header for debugging
  if (obj.hits > 0) {
    set resp.http.X-Cache = "HIT";
    set resp.http.X-Cache-Hits = obj.hits;
  } else {
    set resp.http.X-Cache = "MISS";
  }
}
```

### 2. Surrogate Keys (Cache Tags)

**Concept**: Tag-based cache invalidation for granular control

```python
class FastlySurrogateKeys:
    """Surrogate key patterns for efficient purging"""

    @staticmethod
    def set_surrogate_keys(product_id: int, category_id: int) -> str:
        """
        Set multiple surrogate keys for flexible invalidation

        Pattern: entity-type:id
        """
        keys = [
            f"product:{product_id}",
            f"category:{category_id}",
            "product-listing",
            f"v1"  # API version
        ]
        return " ".join(keys)

    # Flask example
    @staticmethod
    def flask_example():
        """
        from flask import Response

        @app.route('/api/product/<int:product_id>')
        def get_product(product_id):
            product = get_product_from_db(product_id)

            # Set surrogate keys
            keys = FastlySurrogateKeys.set_surrogate_keys(
                product_id, product['category_id']
            )

            response = Response(json.dumps(product))
            response.headers['Surrogate-Key'] = keys
            response.headers['Cache-Control'] = 'public, max-age=3600'

            return response
        """

    @staticmethod
    def purge_by_key(api_key: str, service_id: str, surrogate_key: str):
        """
        Purge cache by surrogate key via Fastly API

        Benefits:
        - Purge all products in category: "category:123"
        - Purge specific product: "product:456"
        - Purge all product listings: "product-listing"
        """
        import requests

        url = f"https://api.fastly.com/service/{service_id}/purge/{surrogate_key}"
        headers = {
            "Fastly-Key": api_key,
            "Accept": "application/json"
        }

        response = requests.post(url, headers=headers)
        return response.json()

# Usage
"""
# When product 456 is updated:
purge_by_key(api_key, service_id, "product:456")

# When category 123 changes:
purge_by_key(api_key, service_id, "category:123")
# Invalidates all products in that category
"""
```

### 3. Soft Purge vs Instant Purge

```python
class FastlyPurgeStrategies:
    """Purge strategies for different scenarios"""

    @staticmethod
    def instant_purge():
        """
        Hard purge: Immediately remove from cache

        Use when: Critical updates, security issues
        Downside: All requests hit origin (stampede risk)
        """
        return {
            "method": "POST /purge/{url}",
            "behavior": "Remove immediately, next request hits origin",
            "use_case": "Breaking news, security patches"
        }

    @staticmethod
    def soft_purge():
        """
        Soft purge: Mark stale, serve while revalidating

        Use when: Normal updates, performance critical
        Benefit: No origin stampede, smooth updates
        """
        return {
            "method": "POST /purge/{url} with Fastly-Soft-Purge: 1",
            "behavior": "Mark stale, serve stale while revalidating",
            "use_case": "Product updates, content changes"
        }

# Implementation
import requests

def soft_purge_url(api_key: str, url: str):
    """Soft purge specific URL"""
    headers = {
        "Fastly-Key": api_key,
        "Fastly-Soft-Purge": "1"
    }
    response = requests.post(f"https://api.fastly.com/purge/{url}", headers=headers)
    return response.json()
```

---

## CloudFront Caching

### 1. Cache Behaviors

```python
class CloudFrontCacheBehaviors:
    """AWS CloudFront cache configuration"""

    @staticmethod
    def static_assets_behavior():
        """Cache behavior for static assets"""
        return {
            "path_pattern": "/static/*",
            "viewer_protocol_policy": "redirect-to-https",
            "cache_policy": {
                "min_ttl": 86400,      # 1 day
                "default_ttl": 2592000,  # 30 days
                "max_ttl": 31536000    # 1 year
            },
            "compress": True,
            "allowed_methods": ["GET", "HEAD"],
        }

    @staticmethod
    def api_behavior():
        """Cache behavior for API endpoints"""
        return {
            "path_pattern": "/api/*",
            "viewer_protocol_policy": "https-only",
            "cache_policy": {
                "min_ttl": 0,
                "default_ttl": 300,    # 5 minutes
                "max_ttl": 3600        # 1 hour
            },
            "origin_request_policy": "AllViewer",
            "cache_based_on": ["query_strings", "headers"]
        }

# Terraform configuration
"""
resource "aws_cloudfront_distribution" "main" {
  enabled = true

  origin {
    domain_name = "origin.example.com"
    origin_id   = "primary"
  }

  # Static assets
  ordered_cache_behavior {
    path_pattern     = "/static/*"
    target_origin_id = "primary"

    min_ttl     = 86400
    default_ttl = 2592000
    max_ttl     = 31536000

    compress = true

    allowed_methods = ["GET", "HEAD"]
    cached_methods  = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
  }

  # API endpoints
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    target_origin_id = "primary"

    min_ttl     = 0
    default_ttl = 300
    max_ttl     = 3600

    allowed_methods = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods  = ["GET", "HEAD"]

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Accept"]
      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "https-only"
  }
}
"""
```

### 2. Lambda@Edge for Dynamic Caching

```javascript
// Lambda@Edge: Viewer Request
exports.handler = async (event) => {
  const request = event.Records[0].cf.request;
  const headers = request.headers;

  // Normalize URL for better cache hit rate
  if (request.querystring) {
    // Sort query parameters
    const params = new URLSearchParams(request.querystring);
    const sortedParams = new URLSearchParams([...params.entries()].sort());
    request.querystring = sortedParams.toString();
  }

  // Add cache key based on device type
  const userAgent = headers['user-agent'][0].value.toLowerCase();
  const deviceType = /mobile/i.test(userAgent) ? 'mobile' : 'desktop';
  headers['x-device-type'] = [{ value: deviceType }];

  return request;
};

// Lambda@Edge: Origin Response
exports.handler = async (event) => {
  const response = event.Records[0].cf.response;

  // Set cache headers based on content type
  const contentType = response.headers['content-type']?.[0]?.value || '';

  if (contentType.includes('image/')) {
    response.headers['cache-control'] = [{
      value: 'public, max-age=31536000, immutable'
    }];
  } else if (contentType.includes('application/json')) {
    response.headers['cache-control'] = [{
      value: 'public, max-age=300'
    }];
  }

  return response;
};
```

---

## Cache Warming Strategies

```python
import asyncio
import aiohttp
from typing import List

class CacheWarming:
    """Proactive cache warming for deployments"""

    @staticmethod
    async def warm_urls(urls: List[str], headers: dict = None):
        """
        Warm cache by requesting URLs

        Use after: Deployments, cache purges, invalidations
        """
        if headers is None:
            headers = {"User-Agent": "Cache-Warmer/1.0"}

        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in urls:
                tasks.append(session.get(url, headers=headers))

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            results = []
            for url, response in zip(urls, responses):
                if isinstance(response, Exception):
                    results.append({"url": url, "status": "error", "error": str(response)})
                else:
                    results.append({
                        "url": url,
                        "status": response.status,
                        "cache_status": response.headers.get("X-Cache", "unknown")
                    })

            return results

    @staticmethod
    def generate_warm_urls(sitemap_url: str) -> List[str]:
        """
        Generate URLs to warm from sitemap

        Prioritize high-traffic pages
        """
        import requests
        from xml.etree import ElementTree

        response = requests.get(sitemap_url)
        root = ElementTree.fromstring(response.content)

        urls = []
        for url_element in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
            urls.append(url_element.text)

        return urls

# Usage
async def warm_cache_after_deployment():
    """Warm cache after deployment"""
    important_urls = [
        "https://example.com/",
        "https://example.com/products",
        "https://example.com/api/featured",
    ]

    results = await CacheWarming.warm_urls(important_urls)

    for result in results:
        print(f"{result['url']}: {result['status']} - {result.get('cache_status')}")

# Run warming
# asyncio.run(warm_cache_after_deployment())
```

---

## Geo-Caching and Regional Optimization

```python
class GeoCaching:
    """Geographic caching strategies"""

    @staticmethod
    def geo_specific_content():
        """
        Serve different content by region

        Use Vary header or separate cache keys
        """
        return {
            "approach_1_vary_header": {
                "header": "Vary: Cloudflare-IPCountry",
                "behavior": "Separate cache per country",
                "use_case": "I18n content"
            },
            "approach_2_dynamic_routing": {
                "method": "Cloudflare Workers geo-routing",
                "benefit": "Custom logic per region",
                "use_case": "Complex regional rules"
            }
        }

# Cloudflare Workers geo-routing
"""
export default {
  async fetch(request, env) {
    const country = request.cf.country;

    // Route to regional buckets
    let cacheKey;
    if (['US', 'CA', 'MX'].includes(country)) {
      cacheKey = `https://cdn.example.com/na/${request.url}`;
    } else if (['GB', 'FR', 'DE'].includes(country)) {
      cacheKey = `https://cdn.example.com/eu/${request.url}`;
    } else {
      cacheKey = `https://cdn.example.com/global/${request.url}`;
    }

    // Fetch with regional cache key
    return fetch(cacheKey, request);
  }
};
"""
```

---

## Debugging and Monitoring

```python
class CDNCacheDebugging:
    """Tools for debugging CDN cache behavior"""

    @staticmethod
    def check_cache_status():
        """
        Interpret cache status headers

        Common headers:
        - X-Cache: HIT/MISS
        - CF-Cache-Status: Cloudflare status
        - X-Cache-Hits: Number of hits
        - Age: Time in cache (seconds)
        """
        return {
            "cloudflare": {
                "HIT": "Served from Cloudflare cache",
                "MISS": "Not in cache, fetched from origin",
                "EXPIRED": "Cached but TTL expired, revalidating",
                "STALE": "Serving stale content",
                "BYPASS": "Cache bypassed",
                "DYNAMIC": "Uncacheable (dynamic content)"
            },
            "fastly": {
                "HIT": "Served from Fastly cache",
                "MISS": "Origin fetch",
                "PASS": "Bypassed cache"
            }
        }

# curl debugging
"""
# Check cache status
curl -I https://example.com/api/data

# Relevant headers:
# CF-Cache-Status: HIT
# Age: 120
# Cache-Control: public, max-age=3600
"""

# Python debugging
import requests

def debug_cdn_cache(url: str):
    """Debug CDN cache behavior"""
    response = requests.get(url)

    return {
        "url": url,
        "status": response.status_code,
        "cache_control": response.headers.get("Cache-Control"),
        "cf_cache_status": response.headers.get("CF-Cache-Status"),
        "x_cache": response.headers.get("X-Cache"),
        "age": response.headers.get("Age"),
        "etag": response.headers.get("ETag"),
    }

# Monitor cache hit rate
def calculate_hit_rate(total_requests: int, cache_hits: int) -> float:
    """Calculate cache hit rate percentage"""
    return (cache_hits / total_requests) * 100 if total_requests > 0 else 0
```

---

## Quick Reference

### CDN Selection Guide
| Feature | Cloudflare | Fastly | CloudFront |
|---------|-----------|--------|------------|
| **Ease of Use** | Excellent | Moderate | Good |
| **Free Tier** | Yes (generous) | No | Yes (limited) |
| **Purge API** | Yes | Excellent (surrogate keys) | Yes |
| **Edge Compute** | Workers | Compute@Edge | Lambda@Edge |
| **Cache TTL Control** | Page Rules, Workers | VCL | Behaviors |
| **Best For** | General sites | High-performance APIs | AWS ecosystem |

### Cache Optimization Checklist
- [ ] Set appropriate Edge TTL (1 week for static, minutes for dynamic)
- [ ] Configure browser Cache-Control headers
- [ ] Enable compression (gzip/brotli)
- [ ] Implement cache warming for critical pages
- [ ] Set up cache purging/invalidation
- [ ] Monitor cache hit rates (target: 85%+)
- [ ] Use Tiered Cache (Cloudflare) or Origin Shield
- [ ] Test cache behavior with curl/browser tools

---

## Related Skills

**Next Steps**:
- `cache-invalidation-strategies.md` → Purging and invalidation patterns
- `cache-performance-monitoring.md` → Measuring CDN effectiveness
- `cloudflare-workers.md` → Edge compute integration

**Foundations**:
- `http-caching.md` → Browser and HTTP caching
- `caching-fundamentals.md` → Core caching concepts

---

## Summary

CDN edge caching dramatically improves global performance and reduces origin load:
- **Cloudflare**: Easy setup, generous free tier, Tiered Cache, Workers for custom logic
- **Fastly**: VCL power, surrogate keys for granular purging, instant/soft purge
- **CloudFront**: AWS integration, Lambda@Edge, robust cache behaviors
- **Performance**: 49-80% TTFB improvements, 85-95% cache hit rates

**Key takeaways**:
1. Use long Edge TTL (1 week) for static content
2. Implement Tiered Cache to reduce origin requests
3. Use surrogate keys (Fastly) or tags for granular invalidation
4. Monitor cache hit rates and optimize for 85%+ hits
5. Warm cache after deployments and purges

**Next**: Move to `redis-caching-patterns.md` for application-level caching.
