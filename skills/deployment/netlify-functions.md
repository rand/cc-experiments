---
name: deployment-netlify-functions
description: Building API endpoints for JAMstack applications
---



# Netlify Functions

**Scope**: Netlify Functions (serverless), Edge Functions, background functions, and API patterns
**Lines**: ~330
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Building API endpoints for JAMstack applications
- Handling form submissions, webhooks, or third-party integrations
- Implementing authentication, authorization, or session management
- Processing data, images, or files serverlessly
- Running scheduled tasks or background jobs
- Using edge computing for low-latency responses
- Avoiding CORS issues with external APIs
- Creating serverless GraphQL or REST APIs

## Core Concepts

### Function Types

**Netlify Functions (serverless)**:
- Run on AWS Lambda (us-east-1 by default)
- Cold start: ~100-500ms
- Timeout: 10 seconds (free), 26 seconds (Pro)
- Memory: 1024 MB
- Use for: API endpoints, data processing, webhooks

**Edge Functions (Deno)**:
- Run on Deno Deploy (global edge network)
- Cold start: <10ms
- Timeout: 50 seconds
- Memory: 128 MB
- Use for: Authentication, geo-routing, A/B testing, low-latency APIs

**Background Functions**:
- Long-running tasks (up to 15 minutes)
- No cold starts (always warm)
- Use for: Data imports, report generation, batch processing

### Function Structure

**Directory structure**:
```
netlify/
  functions/        # Serverless functions
    hello.js
    api-proxy.ts
  edge-functions/   # Edge functions
    auth.ts
    geo-routing.ts
  background-functions/
    daily-report.js
```

**Function file = endpoint**:
- `netlify/functions/hello.js` → `/.netlify/functions/hello`
- `netlify/functions/api/users.js` → `/.netlify/functions/api/users`
- `netlify/edge-functions/auth.ts` → `/` (configured in netlify.toml)

### Environment Access

**Environment variables**:
- Access via `process.env.VAR_NAME` (Functions)
- Access via `Deno.env.get("VAR_NAME")` (Edge Functions)
- Set in Netlify UI, CLI, or netlify.toml (non-sensitive)

**Context object**:
- Request data, headers, query params
- Identity (Netlify Identity user info)
- Geo location (Edge Functions)

---

## Patterns

### Pattern 1: Basic Netlify Function (Node.js)

```javascript
// netlify/functions/hello.js
exports.handler = async (event, context) => {
  // event.httpMethod - GET, POST, etc.
  // event.path - Request path
  // event.headers - Request headers
  // event.queryStringParameters - Query params
  // event.body - Request body (string)

  try {
    const name = event.queryStringParameters?.name || 'World';

    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*', // CORS
      },
      body: JSON.stringify({
        message: `Hello, ${name}!`,
        timestamp: new Date().toISOString(),
      }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message }),
    };
  }
};
```

**TypeScript version**:
```typescript
// netlify/functions/hello.ts
import { Handler, HandlerEvent, HandlerContext } from '@netlify/functions';

interface HelloResponse {
  message: string;
  timestamp: string;
}

export const handler: Handler = async (
  event: HandlerEvent,
  context: HandlerContext
) => {
  const name = event.queryStringParameters?.name || 'World';

  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: `Hello, ${name}!`,
      timestamp: new Date().toISOString(),
    } as HelloResponse),
  };
};
```

**When to use**:
- Simple API endpoints
- Webhook handlers
- Form processors

### Pattern 2: POST Request with Body Parsing

```typescript
// netlify/functions/create-user.ts
import { Handler } from '@netlify/functions';

interface CreateUserBody {
  email: string;
  name: string;
}

export const handler: Handler = async (event) => {
  // Only allow POST
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: 'Method not allowed' }),
    };
  }

  try {
    // Parse JSON body
    const body: CreateUserBody = JSON.parse(event.body || '{}');

    // Validate required fields
    if (!body.email || !body.name) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Missing required fields' }),
      };
    }

    // Process user creation (e.g., save to database)
    const user = await createUser(body);

    return {
      statusCode: 201,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user }),
    };
  } catch (error) {
    console.error('Error creating user:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Internal server error' }),
    };
  }
};

async function createUser(data: CreateUserBody) {
  // Database logic here
  return { id: '123', ...data };
}
```

**When to use**:
- Form submissions
- API mutations
- Webhook receivers

### Pattern 3: API Proxy (Avoid CORS)

```typescript
// netlify/functions/api-proxy.ts
import { Handler } from '@netlify/functions';

const API_BASE = 'https://external-api.com';
const API_KEY = process.env.API_KEY;

export const handler: Handler = async (event) => {
  const path = event.path.replace('/.netlify/functions/api-proxy', '');

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: event.httpMethod,
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: event.body || undefined,
    });

    const data = await response.text();

    return {
      statusCode: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      },
      body: data,
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Failed to fetch from API' }),
    };
  }
};
```

**When to use**:
- Hiding API keys from client
- Avoiding CORS issues
- Adding authentication to external APIs

### Pattern 4: Edge Function (Deno)

```typescript
// netlify/edge-functions/auth.ts
import { Context } from "https://edge.netlify.com";

export default async (request: Request, context: Context) => {
  // Access cookies
  const token = context.cookies.get("auth_token");

  // Check authentication
  if (!token) {
    return new Response("Unauthorized", {
      status: 401,
      headers: {
        "Content-Type": "text/plain",
      },
    });
  }

  // Verify token (simplified)
  const isValid = await verifyToken(token);

  if (!isValid) {
    return new Response("Invalid token", { status: 401 });
  }

  // Continue to origin (pass-through)
  return context.next();
};

async function verifyToken(token: string): Promise<boolean> {
  // JWT verification logic
  return token === "valid-token";
}

export const config = {
  path: "/protected/*",
};
```

**Configure in netlify.toml**:
```toml
[[edge_functions]]
  function = "auth"
  path = "/protected/*"
```

**When to use**:
- Authentication gates
- Geo-based routing
- A/B testing
- Header manipulation
- Low-latency responses

### Pattern 5: Edge Function with Geo Routing

```typescript
// netlify/edge-functions/geo-routing.ts
import { Context } from "https://edge.netlify.com";

export default async (request: Request, context: Context) => {
  const country = context.geo?.country?.code || "US";

  // Route EU users to different content
  if (["GB", "FR", "DE", "IT", "ES"].includes(country)) {
    return context.rewrite("/eu/index.html");
  }

  // Route APAC users
  if (["JP", "CN", "AU", "SG"].includes(country)) {
    return context.rewrite("/apac/index.html");
  }

  // Default: US content
  return context.next();
};

export const config = {
  path: "/",
};
```

**When to use**:
- Geo-based content delivery
- Regional compliance (GDPR, etc.)
- Multi-language routing
- Performance optimization

### Pattern 6: Background Function

```javascript
// netlify/background-functions/daily-report.js
import { schedule } from '@netlify/functions';

// Runs daily at 9 AM UTC
export const handler = schedule("0 9 * * *", async (event) => {
  console.log("Generating daily report...");

  try {
    // Long-running task (up to 15 minutes)
    const report = await generateReport();

    // Send report via email
    await sendEmail({
      to: process.env.ADMIN_EMAIL,
      subject: "Daily Report",
      body: report,
    });

    return {
      statusCode: 200,
      body: JSON.stringify({ message: "Report sent successfully" }),
    };
  } catch (error) {
    console.error("Error generating report:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message }),
    };
  }
});

async function generateReport() {
  // Expensive computation
  return "Report data...";
}

async function sendEmail(options) {
  // Email sending logic
  console.log(`Sending email to ${options.to}`);
}
```

**When to use**:
- Scheduled tasks (cron jobs)
- Data imports/exports
- Report generation
- Batch processing

### Pattern 7: Multipart Form Upload

```typescript
// netlify/functions/upload.ts
import { Handler } from '@netlify/functions';
import multiparty from 'multiparty';

export const handler: Handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  return new Promise((resolve) => {
    const form = new multiparty.Form();

    form.parse(event, async (err, fields, files) => {
      if (err) {
        resolve({
          statusCode: 400,
          body: JSON.stringify({ error: err.message }),
        });
        return;
      }

      // Process uploaded file
      const file = files.file?.[0];
      if (!file) {
        resolve({
          statusCode: 400,
          body: JSON.stringify({ error: 'No file uploaded' }),
        });
        return;
      }

      // Upload to storage (S3, Cloudinary, etc.)
      const url = await uploadToStorage(file.path);

      resolve({
        statusCode: 200,
        body: JSON.stringify({ url }),
      });
    });
  });
};

async function uploadToStorage(filePath: string): Promise<string> {
  // Upload logic (S3, etc.)
  return 'https://cdn.example.com/file.jpg';
}
```

**When to use**:
- File uploads
- Image processing
- CSV imports

### Pattern 8: Rate Limiting

```typescript
// netlify/functions/rate-limited-api.ts
import { Handler } from '@netlify/functions';

// Simple in-memory rate limiter (use Redis in production)
const requests = new Map<string, number[]>();

const RATE_LIMIT = 10; // requests
const WINDOW_MS = 60000; // 1 minute

export const handler: Handler = async (event) => {
  const ip = event.headers['x-forwarded-for'] || 'unknown';
  const now = Date.now();

  // Get request timestamps for this IP
  const timestamps = requests.get(ip) || [];

  // Filter timestamps within window
  const recentRequests = timestamps.filter(t => now - t < WINDOW_MS);

  // Check rate limit
  if (recentRequests.length >= RATE_LIMIT) {
    return {
      statusCode: 429,
      body: JSON.stringify({
        error: 'Too many requests',
        retryAfter: Math.ceil((recentRequests[0] + WINDOW_MS - now) / 1000),
      }),
    };
  }

  // Add current request
  recentRequests.push(now);
  requests.set(ip, recentRequests);

  // Process request
  return {
    statusCode: 200,
    body: JSON.stringify({ message: 'Success' }),
  };
};
```

**When to use**:
- Public APIs
- Preventing abuse
- Cost control

---

## Quick Reference

### Function Types Comparison

```
Feature            | Functions      | Edge Functions | Background
-------------------|----------------|----------------|------------
Runtime            | Node.js        | Deno           | Node.js
Cold Start         | 100-500ms      | <10ms          | None
Timeout            | 10-26s         | 50s            | 15min
Memory             | 1024 MB        | 128 MB         | 1024 MB
Use Case           | API endpoints  | Auth, routing  | Batch jobs
```

### Common Patterns

```
Pattern              | Function Type  | Example
---------------------|----------------|---------------------------
REST API             | Functions      | CRUD endpoints
GraphQL              | Functions      | Apollo Server
Authentication       | Edge           | JWT validation
Geo routing          | Edge           | Country-based redirects
Webhooks             | Functions      | Stripe, GitHub webhooks
Scheduled tasks      | Background     | Daily reports
File processing      | Functions      | Image resize
API proxy            | Functions      | Hide API keys
```

### Environment Variables

```bash
# Set via CLI
netlify env:set API_KEY "secret"

# Access in Functions (Node.js)
process.env.API_KEY

# Access in Edge Functions (Deno)
Deno.env.get("API_KEY")

# Access Netlify context
event.headers["x-nf-client-connection-ip"]  # Client IP
context.clientContext                        # Identity info
```

### Local Development

```bash
# Start dev server with functions
netlify dev

# Test function locally
curl http://localhost:8888/.netlify/functions/hello

# View function logs
netlify functions:logs hello

# Invoke function
netlify functions:invoke hello --payload '{"name":"World"}'
```

### Deployment

```bash
# Deploy functions only
netlify deploy --functions=netlify/functions

# Deploy to production
netlify deploy --prod

# List deployed functions
netlify functions:list
```

---

## Anti-Patterns

❌ **Long-running functions exceeding timeout**: Function times out, incomplete work
✅ Use Background Functions for tasks >10 seconds

❌ **No error handling**: Functions crash, 500 errors to users
✅ Wrap in try-catch, return proper status codes

❌ **Ignoring cold starts**: Slow first request
✅ Use Edge Functions for low-latency, or keep Functions warm with pings

❌ **Large dependencies**: Slow cold starts, large bundle size
✅ Minimize dependencies, use ESM tree-shaking

❌ **Storing state in memory**: State lost between invocations
✅ Use external storage (Redis, Postgres, Netlify Blobs)

❌ **No rate limiting**: Abuse, unexpected bills
✅ Implement rate limiting for public APIs

❌ **Hardcoded secrets**: API keys in source code
✅ Use environment variables, never commit secrets

❌ **Synchronous processing in Functions**: Blocking, timeouts
✅ Use async/await, Background Functions for long tasks

---

## Related Skills

- `netlify-deployment.md` - Site deployment, build configuration, continuous deployment
- `netlify-optimization.md` - Performance optimization, caching, cost reduction
- `aws-serverless.md` - AWS Lambda patterns (Netlify Functions run on Lambda)
- `cloudflare-workers.md` - Alternative edge computing platform
- `api-design-rest.md` - REST API design patterns
- `authentication-jwt.md` - JWT authentication implementation

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
