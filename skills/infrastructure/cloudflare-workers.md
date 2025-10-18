---
name: infrastructure-cloudflare-workers
description: Building serverless APIs at the edge (low latency globally)
---


# Cloudflare Workers

**Scope**: Edge computing with Cloudflare Workers - Edge functions, KV storage, Durable Objects, R2
**Lines**: 365
**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

**Activate when**:
- Building serverless APIs at the edge (low latency globally)
- Implementing CDN logic and custom routing
- A/B testing and feature flags
- Authentication and authorization at the edge
- API proxying and transformation
- Static site generation with dynamic elements

**Prerequisites**:
- Cloudflare account (free tier available)
- Node.js installed for Wrangler CLI
- Wrangler CLI installed (`npm install -g wrangler`)
- Basic JavaScript/TypeScript knowledge
- Cloudflare domain (for production deployment)

**Common scenarios**:
- API endpoints with global low latency
- Image resizing and optimization
- Request/response manipulation
- Rate limiting and bot protection
- Geo-routing and localization
- Edge-side rendering (ESR)

---

## Core Concepts

### 1. Basic Worker

```javascript
// src/index.js - Simple worker
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Simple routing
    if (url.pathname === '/api/hello') {
      return new Response(JSON.stringify({
        message: 'Hello from the edge!',
        location: request.cf.city,
        country: request.cf.country
      }), {
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      });
    }

    // 404 response
    return new Response('Not Found', { status: 404 });
  }
};
```

### 2. Wrangler Configuration

```toml
# wrangler.toml
name = "my-worker"
main = "src/index.js"
compatibility_date = "2024-01-01"

# Environment variables
[vars]
ENVIRONMENT = "production"
API_VERSION = "v1"

# KV Namespace bindings
[[kv_namespaces]]
binding = "CACHE"
id = "abcdef1234567890abcdef1234567890"

# Durable Object bindings
[[durable_objects.bindings]]
name = "COUNTER"
class_name = "Counter"

# R2 bucket bindings
[[r2_buckets]]
binding = "ASSETS"
bucket_name = "my-assets"

# Secrets (set with: wrangler secret put SECRET_NAME)
# Access via env.SECRET_NAME

# Routes (custom domain)
[[routes]]
pattern = "api.example.com/*"
zone_name = "example.com"

# Workers for Platforms (optional)
[dispatch_namespaces]
binding = "DISPATCHER"
namespace = "my-namespace"
```

### 3. Request/Response Handling

```typescript
// src/index.ts - TypeScript worker
interface Env {
  CACHE: KVNamespace;
  API_KEY: string;
  ENVIRONMENT: string;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // CORS handling
    if (request.method === 'OPTIONS') {
      return handleCORS();
    }

    // Authentication
    const apiKey = request.headers.get('X-API-Key');
    if (apiKey !== env.API_KEY) {
      return new Response('Unauthorized', { status: 401 });
    }

    // Route handling
    switch (url.pathname) {
      case '/api/data':
        return handleData(request, env, ctx);
      case '/api/upload':
        return handleUpload(request, env);
      default:
        return new Response('Not Found', { status: 404 });
    }
  }
};

function handleCORS(): Response {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
      'Access-Control-Max-Age': '86400',
    }
  });
}

async function handleData(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
  const cacheKey = new URL(request.url).pathname;

  // Check cache first
  const cached = await env.CACHE.get(cacheKey, 'json');
  if (cached) {
    return Response.json(cached, {
      headers: { 'X-Cache': 'HIT' }
    });
  }

  // Fetch data
  const data = await fetchData();

  // Cache in background
  ctx.waitUntil(
    env.CACHE.put(cacheKey, JSON.stringify(data), {
      expirationTtl: 3600  // 1 hour
    })
  );

  return Response.json(data, {
    headers: { 'X-Cache': 'MISS' }
  });
}

async function fetchData() {
  // Fetch from origin API
  const response = await fetch('https://api.example.com/data');
  return response.json();
}
```

### 4. KV Storage

```typescript
// KV operations
interface Env {
  CACHE: KVNamespace;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const key = url.searchParams.get('key');

    if (request.method === 'GET') {
      // Get value
      const value = await env.CACHE.get(key);
      if (!value) {
        return new Response('Not Found', { status: 404 });
      }
      return new Response(value);
    }

    if (request.method === 'POST') {
      // Put value with expiration
      const value = await request.text();
      await env.CACHE.put(key, value, {
        expirationTtl: 3600,  // Seconds
        metadata: { timestamp: Date.now() }
      });
      return new Response('Stored', { status: 201 });
    }

    if (request.method === 'DELETE') {
      // Delete value
      await env.CACHE.delete(key);
      return new Response('Deleted', { status: 204 });
    }

    // List keys with prefix
    if (url.pathname === '/list') {
      const prefix = url.searchParams.get('prefix') || '';
      const list = await env.CACHE.list({ prefix, limit: 100 });
      return Response.json(list.keys);
    }

    return new Response('Method Not Allowed', { status: 405 });
  }
};
```

### 5. Durable Objects

```typescript
// src/counter.ts - Durable Object
export class Counter {
  state: DurableObjectState;
  value: number;

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    this.value = 0;
  }

  async initialize() {
    // Load state from storage
    const stored = await this.state.storage.get('value');
    this.value = stored || 0;
  }

  async fetch(request: Request): Promise<Response> {
    await this.initialize();

    const url = new URL(request.url);

    if (url.pathname === '/increment') {
      this.value++;
      await this.state.storage.put('value', this.value);
      return Response.json({ value: this.value });
    }

    if (url.pathname === '/decrement') {
      this.value--;
      await this.state.storage.put('value', this.value);
      return Response.json({ value: this.value });
    }

    if (url.pathname === '/get') {
      return Response.json({ value: this.value });
    }

    return new Response('Not Found', { status: 404 });
  }
}

// src/index.ts - Use Durable Object
export { Counter } from './counter';

interface Env {
  COUNTER: DurableObjectNamespace;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // Get Durable Object instance by ID
    const id = env.COUNTER.idFromName('global-counter');
    const stub = env.COUNTER.get(id);

    // Forward request to Durable Object
    return stub.fetch(request);
  }
};
```

### 6. R2 Storage

```typescript
// R2 bucket operations
interface Env {
  ASSETS: R2Bucket;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const key = url.pathname.slice(1);  // Remove leading /

    if (request.method === 'GET') {
      // Get object
      const object = await env.ASSETS.get(key);

      if (!object) {
        return new Response('Not Found', { status: 404 });
      }

      const headers = new Headers();
      object.writeHttpMetadata(headers);
      headers.set('etag', object.httpEtag);

      return new Response(object.body, { headers });
    }

    if (request.method === 'PUT') {
      // Upload object
      await env.ASSETS.put(key, request.body, {
        httpMetadata: {
          contentType: request.headers.get('content-type') || 'application/octet-stream',
        },
        customMetadata: {
          uploadedBy: 'worker',
          timestamp: new Date().toISOString(),
        }
      });

      return new Response('Uploaded', { status: 201 });
    }

    if (request.method === 'DELETE') {
      // Delete object
      await env.ASSETS.delete(key);
      return new Response('Deleted', { status: 204 });
    }

    return new Response('Method Not Allowed', { status: 405 });
  }
};
```

---

## Patterns

### Edge Caching

```typescript
// Cache API with edge caching
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const cache = caches.default;

    // Try to get from cache
    let response = await cache.match(request);
    if (response) {
      return response;
    }

    // Fetch from origin
    response = await fetch(request);

    // Cache successful responses
    if (response.ok) {
      const responseToCache = response.clone();
      ctx.waitUntil(cache.put(request, responseToCache));
    }

    return response;
  }
};
```

### Request Rewriting

```typescript
// Rewrite requests to different origins
export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    // API proxy
    if (url.pathname.startsWith('/api/')) {
      url.hostname = 'api.backend.com';
      url.pathname = url.pathname.replace('/api/', '/v1/');

      const modifiedRequest = new Request(url.toString(), {
        method: request.method,
        headers: request.headers,
        body: request.body,
      });

      return fetch(modifiedRequest);
    }

    // Default to static assets
    url.hostname = 'static.example.com';
    return fetch(url.toString());
  }
};
```

### A/B Testing

```typescript
// A/B testing with cookie-based variants
export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    // Check for existing variant cookie
    let variant = getCookie(request, 'ab_variant');

    if (!variant) {
      // Assign random variant
      variant = Math.random() < 0.5 ? 'A' : 'B';
    }

    // Fetch variant-specific content
    const response = await fetch(`https://origin.com/${variant}${url.pathname}`);

    // Set variant cookie
    const newResponse = new Response(response.body, response);
    newResponse.headers.set('Set-Cookie', `ab_variant=${variant}; Path=/; Max-Age=86400`);

    return newResponse;
  }
};

function getCookie(request: Request, name: string): string | null {
  const cookies = request.headers.get('Cookie');
  if (!cookies) return null;

  const cookie = cookies.split(';').find(c => c.trim().startsWith(`${name}=`));
  return cookie ? cookie.split('=')[1] : null;
}
```

### Rate Limiting

```typescript
// Rate limiting with Durable Objects
export class RateLimiter {
  state: DurableObjectState;
  requests: Map<string, number[]>;

  constructor(state: DurableObjectState) {
    this.state = state;
    this.requests = new Map();
  }

  async fetch(request: Request): Promise<Response> {
    const clientId = request.headers.get('CF-Connecting-IP') || 'unknown';
    const now = Date.now();
    const windowMs = 60000;  // 1 minute
    const maxRequests = 100;

    // Get request timestamps for this client
    let timestamps = this.requests.get(clientId) || [];

    // Remove old timestamps outside window
    timestamps = timestamps.filter(ts => now - ts < windowMs);

    // Check if limit exceeded
    if (timestamps.length >= maxRequests) {
      return new Response('Rate limit exceeded', {
        status: 429,
        headers: {
          'Retry-After': '60'
        }
      });
    }

    // Add current request
    timestamps.push(now);
    this.requests.set(clientId, timestamps);

    return Response.json({
      allowed: true,
      remaining: maxRequests - timestamps.length
    });
  }
}
```

### Image Resizing

```typescript
// Image transformation
export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    // Parse resize parameters
    const width = parseInt(url.searchParams.get('width') || '800');
    const quality = parseInt(url.searchParams.get('quality') || '85');
    const format = url.searchParams.get('format') || 'auto';

    // Fetch original image
    const imageUrl = url.searchParams.get('url');
    if (!imageUrl) {
      return new Response('Missing url parameter', { status: 400 });
    }

    const response = await fetch(imageUrl);

    // Transform with Cloudflare Image Resizing
    return new Response(response.body, {
      headers: {
        'Content-Type': 'image/jpeg',
        'Cache-Control': 'public, max-age=31536000',
        'CF-Image-Width': width.toString(),
        'CF-Image-Quality': quality.toString(),
        'CF-Image-Format': format,
      }
    });
  }
};
```

---

## Quick Reference

### Wrangler Commands

```bash
# Development
wrangler dev                    # Local development server
wrangler dev --remote           # Remote development (actual edge)

# Deployment
wrangler deploy                 # Deploy to production
wrangler deploy --env staging   # Deploy to staging

# KV operations
wrangler kv:namespace create "CACHE"
wrangler kv:key put --binding=CACHE "key" "value"
wrangler kv:key get --binding=CACHE "key"
wrangler kv:key delete --binding=CACHE "key"
wrangler kv:key list --binding=CACHE

# R2 operations
wrangler r2 bucket create my-bucket
wrangler r2 object put my-bucket/file.txt --file=./file.txt
wrangler r2 object get my-bucket/file.txt

# Secrets
wrangler secret put API_KEY
wrangler secret delete API_KEY
wrangler secret list

# Logs
wrangler tail                   # Stream logs
wrangler tail --format=pretty

# Account info
wrangler whoami
wrangler deployments list
```

### Worker Limits

```
CPU Time: 10ms (free), 30s (paid) per request
Memory: 128 MB
Subrequest limit: 50 (free), 1000 (paid)
Script size: 1 MB (free), 10 MB (paid)
KV read: 100,000/day (free), unlimited (paid)
KV write: 1,000/day (free), unlimited (paid)
Durable Objects: Paid feature only
R2 storage: 10 GB (free), unlimited (paid)
```

---

## Anti-Patterns

### Critical Violations

```typescript
// ❌ NEVER: Store secrets in code
const API_KEY = "sk-1234567890abcdef";  // NEVER

// ✅ CORRECT: Use environment bindings
interface Env {
  API_KEY: string;  // Set with: wrangler secret put API_KEY
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.headers.get('X-API-Key') !== env.API_KEY) {
      return new Response('Unauthorized', { status: 401 });
    }
    // ...
  }
};
```

```typescript
// ❌ NEVER: Perform blocking operations
export default {
  async fetch(request: Request): Promise<Response> {
    // CPU-intensive synchronous work
    let result = 0;
    for (let i = 0; i < 1000000000; i++) {  // Will hit CPU limit
      result += i;
    }
    return Response.json({ result });
  }
};

// ✅ CORRECT: Use Durable Objects for stateful work
// Or offload to origin API for heavy computation
```

```typescript
// ❌ NEVER: Use global state
let counter = 0;  // Not shared across requests!

export default {
  async fetch(request: Request): Promise<Response> {
    counter++;  // Each request gets own isolate
    return Response.json({ counter });  // Always 1
  }
};

// ✅ CORRECT: Use KV or Durable Objects
interface Env {
  CACHE: KVNamespace;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const counter = parseInt(await env.CACHE.get('counter') || '0');
    await env.CACHE.put('counter', (counter + 1).toString());
    return Response.json({ counter: counter + 1 });
  }
};
```

### Common Mistakes

```typescript
// ❌ Don't forget CORS headers
export default {
  async fetch(request: Request): Promise<Response> {
    return Response.json({ data: 'value' });
    // Browser will block cross-origin requests
  }
};

// ✅ CORRECT: Add CORS headers
export default {
  async fetch(request: Request): Promise<Response> {
    const headers = {
      'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json',
    };
    return Response.json({ data: 'value' }, { headers });
  }
};
```

---

## Related Skills

**Infrastructure**:
- `aws-serverless.md` - Alternative serverless platform (Lambda, API Gateway)
- `infrastructure-security.md` - Authentication, authorization patterns
- `cost-optimization.md` - Workers pricing, caching strategies

**Development**:
- `modal-functions-basics.md` - Python-focused serverless alternative
- `terraform-patterns.md` - Infrastructure as Code for Cloudflare resources

**Standards from CLAUDE.md**:
- Use wrangler CLI for all operations
- Store secrets with `wrangler secret put`
- TypeScript for type safety
- Always handle CORS for API endpoints
- Use KV for simple key-value, Durable Objects for complex state

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
