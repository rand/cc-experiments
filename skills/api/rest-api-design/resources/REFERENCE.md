# REST API Design Reference

> **Comprehensive guide to designing production-grade REST APIs**

## Table of Contents

1. [REST Principles](#rest-principles)
2. [HTTP Methods](#http-methods)
3. [Status Codes](#status-codes)
4. [URL Design](#url-design)
5. [Request/Response Formats](#requestresponse-formats)
6. [Pagination](#pagination)
7. [Filtering, Sorting, and Searching](#filtering-sorting-and-searching)
8. [Versioning](#versioning)
9. [Error Handling](#error-handling)
10. [HATEOAS and Hypermedia](#hateoas-and-hypermedia)
11. [Rate Limiting](#rate-limiting)
12. [Caching](#caching)
13. [Authentication and Authorization](#authentication-and-authorization)
14. [CORS](#cors)
15. [API Documentation](#api-documentation)
16. [Common Patterns](#common-patterns)
17. [Anti-Patterns](#anti-patterns)
18. [Security Best Practices](#security-best-practices)
19. [Performance Optimization](#performance-optimization)
20. [Testing Strategies](#testing-strategies)

---

## REST Principles

### What is REST?

**REST** (Representational State Transfer) is an architectural style for distributed hypermedia systems. It was first defined by Roy Fielding in his doctoral dissertation in 2000.

### Core Constraints

#### 1. Client-Server Architecture

**Principle**: Separation of concerns between client and server.

```
Client (UI/UX)  ←→  Server (Data/Logic)
```

**Benefits**:
- Independent evolution of client and server
- Improved scalability
- Better portability across platforms

**Example**:
```javascript
// Client: React application
fetch('/api/users')
  .then(res => res.json())
  .then(users => renderUsers(users));

// Server: Express API
app.get('/api/users', (req, res) => {
  res.json(users);
});
```

#### 2. Statelessness

**Principle**: Each request contains all information needed to process it. Server stores no client context between requests.

**Server does NOT store**:
- Session state
- Authentication state (use tokens instead)
- Request context

**Client must send**:
- Authentication credentials (every request)
- All necessary parameters
- Complete context

**Example**:
```http
# Stateless (CORRECT)
GET /api/users/123 HTTP/1.1
Authorization: Bearer eyJhbGc...
Accept: application/json

# Stateful (INCORRECT - don't do this)
GET /api/users/current HTTP/1.1
Cookie: session_id=abc123
```

**Benefits**:
- Improved scalability (no server-side session storage)
- Simplified server implementation
- Better reliability (no session loss)
- Easier load balancing

**Trade-offs**:
- Larger request payloads (must send auth every time)
- Client manages more state

#### 3. Cacheability

**Principle**: Responses must define themselves as cacheable or non-cacheable.

**Cache Control Headers**:
```http
# Cacheable response
HTTP/1.1 200 OK
Cache-Control: max-age=3600, public
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
Last-Modified: Wed, 21 Oct 2025 07:28:00 GMT

# Non-cacheable response
HTTP/1.1 200 OK
Cache-Control: no-store, no-cache, must-revalidate
Pragma: no-cache
```

**Caching Strategies**:

1. **Public Caching** (CDN, shared proxies):
```http
Cache-Control: public, max-age=86400
```

2. **Private Caching** (browser only):
```http
Cache-Control: private, max-age=3600
```

3. **No Caching**:
```http
Cache-Control: no-store
```

4. **Conditional Requests**:
```http
# Request
GET /api/users/123
If-None-Match: "33a64df551425fcc55e4d42a148795d9f25f89d4"

# Response (not modified)
HTTP/1.1 304 Not Modified
```

#### 4. Uniform Interface

**Principle**: Standardized way to interact with resources.

**Four Sub-Constraints**:

1. **Resource Identification**:
```http
GET /api/users/123          # Identifies a specific user
GET /api/orders/456/items   # Identifies items in an order
```

2. **Resource Manipulation through Representations**:
```json
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com"
}
```

3. **Self-Descriptive Messages**:
```http
GET /api/users/123 HTTP/1.1
Host: api.example.com
Accept: application/json
Authorization: Bearer token

HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 98
```

4. **HATEOAS** (Hypermedia as the Engine of Application State):
```json
{
  "id": 123,
  "name": "John Doe",
  "_links": {
    "self": { "href": "/api/users/123" },
    "orders": { "href": "/api/users/123/orders" },
    "avatar": { "href": "/api/users/123/avatar" }
  }
}
```

#### 5. Layered System

**Principle**: Client cannot tell if connected directly to server or through intermediaries.

```
Client → Load Balancer → API Gateway → Cache → Service → Database
```

**Benefits**:
- Add authentication layers
- Add caching layers
- Add load balancing
- Enforce security policies

**Example Architecture**:
```
┌──────────┐
│  Client  │
└────┬─────┘
     │
┌────▼──────────┐
│ Load Balancer │
└────┬──────────┘
     │
┌────▼────────┐
│ API Gateway │ (Auth, Rate Limiting)
└────┬────────┘
     │
┌────▼──────┐
│   Cache   │ (Redis, Varnish)
└────┬──────┘
     │
┌────▼────────┐
│ API Service │
└────┬────────┘
     │
┌────▼────────┐
│  Database   │
└─────────────┘
```

#### 6. Code on Demand (Optional)

**Principle**: Server can extend client functionality by transferring executable code.

**Examples**:
- JavaScript sent to browser
- Applets
- Client-side scripts

```json
{
  "data": {...},
  "script": "https://cdn.example.com/widget.js"
}
```

**Note**: This constraint is optional and rarely used in modern REST APIs.

---

## HTTP Methods

### Overview

HTTP methods define the action to be performed on a resource.

| Method  | CRUD      | Idempotent | Safe | Cacheable |
|---------|-----------|------------|------|-----------|
| GET     | Read      | Yes        | Yes  | Yes       |
| POST    | Create    | No         | No   | Rarely    |
| PUT     | Replace   | Yes        | No   | No        |
| PATCH   | Update    | No         | No   | No        |
| DELETE  | Delete    | Yes        | No   | No        |
| HEAD    | Headers   | Yes        | Yes  | Yes       |
| OPTIONS | Metadata  | Yes        | Yes  | No        |

**Definitions**:
- **Idempotent**: Multiple identical requests have the same effect as a single request
- **Safe**: Does not modify server state
- **Cacheable**: Response can be stored for future use

### GET - Read Resources

**Purpose**: Retrieve resource representation.

**Characteristics**:
- Safe (no side effects)
- Idempotent
- Cacheable
- Can include query parameters

**Usage**:

```http
# Get single resource
GET /api/users/123
Accept: application/json

# Get collection
GET /api/users?limit=10&offset=0

# Get nested resource
GET /api/users/123/orders

# Get with filtering
GET /api/products?category=electronics&price_min=100

# Get with sorting
GET /api/users?sort=created_at:desc
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: max-age=3600
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"

{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com",
  "created_at": "2025-10-27T10:00:00Z"
}
```

**Best Practices**:
```python
# Good: Use query params for filtering
GET /api/users?role=admin&status=active

# Bad: Don't use request body
GET /api/users
Body: { "role": "admin" }  # WRONG

# Good: Support field selection
GET /api/users?fields=id,name,email

# Good: Support expansion
GET /api/orders/123?expand=customer,items
```

### POST - Create Resources

**Purpose**: Create new resource or trigger action.

**Characteristics**:
- Not safe (modifies state)
- Not idempotent (creates new resource each time)
- Can be cacheable (with appropriate headers)

**Usage**:

```http
# Create new resource
POST /api/users
Content-Type: application/json

{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "role": "user"
}
```

**Success Response**:
```http
HTTP/1.1 201 Created
Content-Type: application/json
Location: /api/users/124

{
  "id": 124,
  "name": "Jane Smith",
  "email": "jane@example.com",
  "role": "user",
  "created_at": "2025-10-27T10:30:00Z"
}
```

**POST for Actions**:
```http
# Trigger action
POST /api/users/123/send-welcome-email
Content-Type: application/json

{
  "template": "welcome_v2",
  "language": "en"
}
```

**Response**:
```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "job_id": "abc-123",
  "status": "queued",
  "estimated_completion": "2025-10-27T10:35:00Z"
}
```

**Best Practices**:
```python
# Good: Return created resource
HTTP/1.1 201 Created
Location: /api/users/124
Body: { "id": 124, ... }

# Good: Return 202 for async operations
HTTP/1.1 202 Accepted
Body: { "job_id": "abc-123", "status": "processing" }

# Bad: Don't use POST when PUT/PATCH is appropriate
POST /api/users/123/update  # WRONG - use PUT/PATCH

# Good: Use POST for complex searches
POST /api/search
Body: { "query": {...}, "filters": {...} }
```

### PUT - Replace Resources

**Purpose**: Replace entire resource or create at specific URI.

**Characteristics**:
- Not safe (modifies state)
- Idempotent (same result regardless of repetition)
- Complete replacement

**Usage**:

```http
# Replace entire resource
PUT /api/users/123
Content-Type: application/json

{
  "name": "John Doe Updated",
  "email": "john.updated@example.com",
  "role": "admin",
  "bio": "New bio"
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 123,
  "name": "John Doe Updated",
  "email": "john.updated@example.com",
  "role": "admin",
  "bio": "New bio",
  "updated_at": "2025-10-27T11:00:00Z"
}
```

**Create with PUT** (if URI is known):
```http
PUT /api/users/new-user-id
Content-Type: application/json

{
  "name": "New User",
  "email": "new@example.com"
}
```

**Response**:
```http
HTTP/1.1 201 Created
Location: /api/users/new-user-id
```

**Best Practices**:
```python
# Good: Full replacement
PUT /api/users/123
Body: { "name": "...", "email": "...", "role": "..." }

# Bad: Partial update (use PATCH instead)
PUT /api/users/123
Body: { "email": "new@example.com" }  # Missing fields

# Good: Idempotent behavior
PUT /api/users/123  # First call: updates
PUT /api/users/123  # Second call: same result

# Good: Use for upsert operations
PUT /api/config/theme
Body: { "primary_color": "#007bff" }
```

### PATCH - Partial Update

**Purpose**: Apply partial modifications to resource.

**Characteristics**:
- Not safe (modifies state)
- Can be idempotent (depends on implementation)
- Partial modification

**Usage**:

```http
# JSON Patch (RFC 6902)
PATCH /api/users/123
Content-Type: application/json-patch+json

[
  { "op": "replace", "path": "/email", "value": "new@example.com" },
  { "op": "add", "path": "/phone", "value": "+1234567890" }
]
```

**Merge Patch (RFC 7396)**:
```http
PATCH /api/users/123
Content-Type: application/merge-patch+json

{
  "email": "new@example.com",
  "bio": "Updated bio"
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 123,
  "name": "John Doe",
  "email": "new@example.com",
  "phone": "+1234567890",
  "bio": "Updated bio",
  "updated_at": "2025-10-27T11:30:00Z"
}
```

**JSON Patch Operations**:

```json
[
  { "op": "add", "path": "/tags/-", "value": "important" },
  { "op": "remove", "path": "/deprecated" },
  { "op": "replace", "path": "/status", "value": "active" },
  { "op": "move", "from": "/old_field", "path": "/new_field" },
  { "op": "copy", "from": "/source", "path": "/destination" },
  { "op": "test", "path": "/version", "value": 2 }
]
```

**Best Practices**:
```python
# Good: Use PATCH for partial updates
PATCH /api/users/123
Body: { "email": "new@example.com" }

# Good: Specify content type
Content-Type: application/merge-patch+json
Content-Type: application/json-patch+json

# Bad: Don't use for full replacement
PATCH /api/users/123
Body: { "name": "...", "email": "...", ...all fields... }  # Use PUT

# Good: Support both formats
Accept: application/json-patch+json, application/merge-patch+json
```

### DELETE - Remove Resources

**Purpose**: Delete resource.

**Characteristics**:
- Not safe (modifies state)
- Idempotent (deleting deleted resource has same effect)

**Usage**:

```http
# Delete resource
DELETE /api/users/123
```

**Success Response** (deleted):
```http
HTTP/1.1 204 No Content
```

**Success Response** (with body):
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 123,
  "deleted": true,
  "deleted_at": "2025-10-27T12:00:00Z"
}
```

**Already Deleted**:
```http
HTTP/1.1 404 Not Found
```

**Soft Delete**:
```http
DELETE /api/users/123

HTTP/1.1 200 OK
{
  "id": 123,
  "status": "deleted",
  "deleted_at": "2025-10-27T12:00:00Z"
}
```

**Best Practices**:
```python
# Good: Return 204 No Content
HTTP/1.1 204 No Content

# Good: Return 404 if already deleted
HTTP/1.1 404 Not Found

# Good: Consider soft deletes
DELETE /api/users/123
Response: { "status": "deleted", "recoverable_until": "..." }

# Good: Bulk delete
DELETE /api/users?ids=1,2,3
Response: { "deleted_count": 3 }

# Bad: Don't require request body
DELETE /api/users
Body: { "id": 123 }  # WRONG
```

### HEAD - Get Headers

**Purpose**: Retrieve response headers without body.

**Characteristics**:
- Safe
- Idempotent
- Same headers as GET

**Usage**:

```http
HEAD /api/users/123
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 298
Last-Modified: Wed, 27 Oct 2025 10:00:00 GMT
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
```

**Use Cases**:
- Check if resource exists
- Get metadata (size, modification date)
- Check cache validity
- Pre-flight checks

**Example**:
```python
# Check if file exists before downloading
response = requests.head('https://api.example.com/files/large-file.zip')
if response.status_code == 200:
    file_size = int(response.headers['Content-Length'])
    if file_size < MAX_SIZE:
        download_file()
```

### OPTIONS - Metadata

**Purpose**: Retrieve supported methods and capabilities.

**Characteristics**:
- Safe
- Idempotent
- Used for CORS preflight

**Usage**:

```http
OPTIONS /api/users/123
```

**Response**:
```http
HTTP/1.1 200 OK
Allow: GET, PUT, PATCH, DELETE, HEAD, OPTIONS
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, PUT, PATCH, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
```

**CORS Preflight**:
```http
OPTIONS /api/users
Origin: https://example.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Content-Type

HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

---

## Status Codes

### Overview

HTTP status codes indicate the result of a request.

| Range | Category          | Meaning                       |
|-------|-------------------|-------------------------------|
| 1xx   | Informational     | Request received, processing  |
| 2xx   | Success           | Request successful            |
| 3xx   | Redirection       | Further action needed         |
| 4xx   | Client Error      | Client error                  |
| 5xx   | Server Error      | Server error                  |

### 1xx Informational

**100 Continue**:
```http
# Client sends
POST /api/large-upload
Expect: 100-continue
Content-Length: 1000000000

# Server responds
HTTP/1.1 100 Continue

# Client sends body
```

**101 Switching Protocols**:
```http
GET /ws
Upgrade: websocket
Connection: Upgrade

HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
```

### 2xx Success

**200 OK**:
```http
# General success
GET /api/users/123

HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 123,
  "name": "John Doe"
}
```

**201 Created**:
```http
# Resource created
POST /api/users
Body: { "name": "Jane Smith" }

HTTP/1.1 201 Created
Location: /api/users/124
Content-Type: application/json

{
  "id": 124,
  "name": "Jane Smith"
}
```

**202 Accepted**:
```http
# Async processing
POST /api/reports/generate
Body: { "type": "annual", "year": 2025 }

HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "job_id": "abc-123",
  "status": "processing",
  "status_url": "/api/jobs/abc-123"
}
```

**204 No Content**:
```http
# Successful delete
DELETE /api/users/123

HTTP/1.1 204 No Content
```

**206 Partial Content**:
```http
# Range request
GET /api/files/large-file.bin
Range: bytes=0-1023

HTTP/1.1 206 Partial Content
Content-Range: bytes 0-1023/102400
Content-Length: 1024

[binary data]
```

### 3xx Redirection

**301 Moved Permanently**:
```http
GET /api/v1/users

HTTP/1.1 301 Moved Permanently
Location: /api/v2/users
```

**302 Found** (Temporary Redirect):
```http
GET /api/users/current

HTTP/1.1 302 Found
Location: /api/users/123
```

**303 See Other**:
```http
POST /api/orders
Body: { "items": [...] }

HTTP/1.1 303 See Other
Location: /api/orders/456
```

**304 Not Modified**:
```http
GET /api/users/123
If-None-Match: "33a64df551425fcc55e4d42a148795d9f25f89d4"

HTTP/1.1 304 Not Modified
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
```

**307 Temporary Redirect**:
```http
POST /api/login
Body: { "username": "...", "password": "..." }

HTTP/1.1 307 Temporary Redirect
Location: /api/auth/login
```

**308 Permanent Redirect**:
```http
POST /api/v1/users
Body: { "name": "..." }

HTTP/1.1 308 Permanent Redirect
Location: /api/v2/users
```

### 4xx Client Errors

**400 Bad Request**:
```http
POST /api/users
Body: { "invalid": "data" }

HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "validation_error",
  "message": "Invalid request data",
  "details": [
    {
      "field": "email",
      "message": "Email is required"
    }
  ]
}
```

**401 Unauthorized**:
```http
GET /api/users/123

HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="API"
Content-Type: application/json

{
  "error": "unauthorized",
  "message": "Authentication required"
}
```

**403 Forbidden**:
```http
DELETE /api/users/admin

HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": "forbidden",
  "message": "You don't have permission to delete admin users"
}
```

**404 Not Found**:
```http
GET /api/users/999

HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": "not_found",
  "message": "User with id 999 not found"
}
```

**405 Method Not Allowed**:
```http
DELETE /api/health

HTTP/1.1 405 Method Not Allowed
Allow: GET, HEAD, OPTIONS
Content-Type: application/json

{
  "error": "method_not_allowed",
  "message": "DELETE is not allowed on this endpoint",
  "allowed_methods": ["GET", "HEAD", "OPTIONS"]
}
```

**406 Not Acceptable**:
```http
GET /api/users/123
Accept: application/xml

HTTP/1.1 406 Not Acceptable
Content-Type: application/json

{
  "error": "not_acceptable",
  "message": "Server cannot produce application/xml",
  "supported_types": ["application/json"]
}
```

**409 Conflict**:
```http
POST /api/users
Body: { "email": "existing@example.com" }

HTTP/1.1 409 Conflict
Content-Type: application/json

{
  "error": "conflict",
  "message": "User with email existing@example.com already exists"
}
```

**410 Gone**:
```http
GET /api/v1/users/123

HTTP/1.1 410 Gone
Content-Type: application/json

{
  "error": "gone",
  "message": "API v1 is no longer available. Use /api/v2/users/123"
}
```

**415 Unsupported Media Type**:
```http
POST /api/users
Content-Type: application/xml
Body: <user>...</user>

HTTP/1.1 415 Unsupported Media Type
Content-Type: application/json

{
  "error": "unsupported_media_type",
  "message": "Content-Type application/xml is not supported",
  "supported_types": ["application/json"]
}
```

**422 Unprocessable Entity**:
```http
POST /api/users
Body: { "email": "invalid-email", "age": -5 }

HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{
  "error": "validation_error",
  "message": "Request validation failed",
  "details": [
    { "field": "email", "message": "Invalid email format" },
    { "field": "age", "message": "Age must be positive" }
  ]
}
```

**429 Too Many Requests**:
```http
GET /api/users

HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1698400000

{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again in 60 seconds"
}
```

### 5xx Server Errors

**500 Internal Server Error**:
```http
GET /api/users/123

HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "error": "internal_error",
  "message": "An unexpected error occurred",
  "incident_id": "inc-123456"
}
```

**501 Not Implemented**:
```http
TRACE /api/users

HTTP/1.1 501 Not Implemented
Content-Type: application/json

{
  "error": "not_implemented",
  "message": "TRACE method is not implemented"
}
```

**502 Bad Gateway**:
```http
GET /api/users/123

HTTP/1.1 502 Bad Gateway
Content-Type: application/json

{
  "error": "bad_gateway",
  "message": "Upstream service returned invalid response"
}
```

**503 Service Unavailable**:
```http
GET /api/users

HTTP/1.1 503 Service Unavailable
Retry-After: 300
Content-Type: application/json

{
  "error": "service_unavailable",
  "message": "Service temporarily unavailable. Maintenance in progress"
}
```

**504 Gateway Timeout**:
```http
GET /api/reports/slow

HTTP/1.1 504 Gateway Timeout
Content-Type: application/json

{
  "error": "gateway_timeout",
  "message": "Upstream service timed out"
}
```

---

## URL Design

### Resource Naming

**Principles**:
- Use nouns (not verbs)
- Use plural forms for collections
- Use kebab-case for multi-word resources
- Be consistent

**Good Examples**:
```
GET    /api/users
GET    /api/users/123
GET    /api/users/123/orders
GET    /api/blog-posts
GET    /api/user-preferences
```

**Bad Examples**:
```
GET    /api/getUsers           # Don't use verbs
GET    /api/user               # Use plural
GET    /api/users/getById/123  # Don't use verbs
GET    /api/blogPosts          # Use kebab-case
GET    /api/Users              # Use lowercase
```

### Resource Hierarchy

**Nested Resources**:
```
# User's orders
GET /api/users/123/orders

# Specific order for user
GET /api/users/123/orders/456

# Order items
GET /api/orders/456/items

# Deep nesting (use sparingly)
GET /api/users/123/orders/456/items/789
```

**Best Practices**:
```python
# Good: Limit nesting to 2-3 levels
GET /api/users/123/orders
GET /api/users/123/orders/456

# Bad: Too deep
GET /api/organizations/1/departments/2/teams/3/members/4/tasks/5

# Better: Flatten with query params
GET /api/tasks/5?member_id=4&team_id=3
GET /api/tasks?team_id=3&member_id=4
```

### Query Parameters

**Filtering**:
```
GET /api/users?status=active
GET /api/users?role=admin&department=engineering
GET /api/products?category=electronics&price_min=100&price_max=500
```

**Sorting**:
```
GET /api/users?sort=created_at
GET /api/users?sort=-created_at           # Descending
GET /api/users?sort=last_name,first_name  # Multiple fields
```

**Pagination**:
```
GET /api/users?limit=20&offset=0
GET /api/users?page=1&per_page=20
GET /api/users?cursor=abc123
```

**Field Selection**:
```
GET /api/users?fields=id,name,email
GET /api/users?exclude=password,ssn
```

**Expansion**:
```
GET /api/orders?expand=customer
GET /api/orders?expand=customer,items
GET /api/orders?expand=customer.address
```

**Search**:
```
GET /api/users?q=john
GET /api/users?search=john+doe
GET /api/products?q=laptop&category=electronics
```

### Actions and Operations

**Use POST for actions**:
```
POST /api/users/123/send-email
POST /api/orders/456/cancel
POST /api/payments/789/refund
POST /api/reports/generate
```

**Alternative: Use status updates**:
```
PATCH /api/orders/456
Body: { "status": "cancelled" }

PATCH /api/tasks/123
Body: { "completed": true }
```

**Complex operations**:
```
# Search with complex criteria
POST /api/search
Body: {
  "query": "laptop",
  "filters": {
    "category": ["electronics", "computers"],
    "price": { "min": 500, "max": 2000 },
    "brand": ["Dell", "HP"]
  }
}

# Batch operations
POST /api/users/batch-update
Body: {
  "user_ids": [1, 2, 3],
  "updates": { "status": "active" }
}
```

### Versioning in URLs

**URI Versioning**:
```
https://api.example.com/v1/users
https://api.example.com/v2/users
```

**Path Versioning**:
```
https://api.example.com/api/v1/users
https://api.example.com/api/v2/users
```

**Best Practices**:
```python
# Good: Major version in path
/api/v1/users
/api/v2/users

# Bad: Minor/patch version in path
/api/v1.2.3/users  # Too granular

# Good: Use header for minor versions
GET /api/v2/users
API-Version: 2.1
```

---

## Request/Response Formats

### Content Negotiation

**Accept Header** (request):
```http
GET /api/users/123
Accept: application/json
Accept: application/xml
Accept: application/json, application/xml;q=0.9
```

**Content-Type Header** (response):
```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "id": 123,
  "name": "John Doe"
}
```

### JSON Format

**Standard Format**:
```json
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com",
  "created_at": "2025-10-27T10:00:00Z",
  "is_active": true,
  "roles": ["user", "editor"],
  "metadata": {
    "last_login": "2025-10-27T09:00:00Z",
    "login_count": 42
  }
}
```

**Collection Format**:
```json
{
  "data": [
    { "id": 1, "name": "User 1" },
    { "id": 2, "name": "User 2" }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  },
  "links": {
    "self": "/api/users?page=1",
    "next": "/api/users?page=2",
    "last": "/api/users?page=5"
  }
}
```

**Naming Conventions**:

1. **snake_case** (Python, Ruby):
```json
{
  "user_id": 123,
  "first_name": "John",
  "created_at": "2025-10-27T10:00:00Z"
}
```

2. **camelCase** (JavaScript):
```json
{
  "userId": 123,
  "firstName": "John",
  "createdAt": "2025-10-27T10:00:00Z"
}
```

**Best Practice**: Choose one and be consistent.

### Date/Time Formats

**ISO 8601** (recommended):
```json
{
  "created_at": "2025-10-27T10:00:00Z",
  "updated_at": "2025-10-27T10:30:00+00:00",
  "scheduled_for": "2025-10-28T14:00:00-05:00"
}
```

**Unix Timestamp**:
```json
{
  "created_at": 1698400000,
  "updated_at": 1698401800
}
```

**Best Practice**: Use ISO 8601 for human readability.

### Null vs Empty Values

```json
{
  "name": "John Doe",
  "middle_name": null,        // Value is null
  "email": "john@example.com",
  "bio": "",                   // Empty string
  "tags": [],                  // Empty array
  "metadata": {}               // Empty object
}
```

**Handling Optional Fields**:
```json
// Option 1: Include with null
{
  "name": "John Doe",
  "phone": null
}

// Option 2: Omit entirely
{
  "name": "John Doe"
}
```

**Best Practice**: Be consistent. Document your choice.

### Boolean Values

```json
{
  "is_active": true,
  "has_premium": false,
  "email_verified": true
}
```

**Don't use**:
```json
{
  "active": "yes",     // Use boolean
  "verified": 1,       // Use boolean
  "enabled": "true"    // Use boolean (not string)
}
```

### Enumerations

```json
{
  "status": "active",           // Not: 1, "ACTIVE"
  "role": "admin",              // Not: "ADMIN", "Admin"
  "priority": "high"            // Not: 3, "HIGH"
}
```

**Best Practice**: Use lowercase strings.

---

## Pagination

### Offset-Based Pagination

**Request**:
```http
GET /api/users?limit=20&offset=40
```

**Response**:
```json
{
  "data": [...],
  "pagination": {
    "limit": 20,
    "offset": 40,
    "total": 500
  },
  "links": {
    "first": "/api/users?limit=20&offset=0",
    "prev": "/api/users?limit=20&offset=20",
    "self": "/api/users?limit=20&offset=40",
    "next": "/api/users?limit=20&offset=60",
    "last": "/api/users?limit=20&offset=480"
  }
}
```

**Pros**:
- Simple implementation
- Easy to jump to specific page
- Total count available

**Cons**:
- Performance degrades with large offsets
- Inconsistent with real-time data changes

### Page-Based Pagination

**Request**:
```http
GET /api/users?page=3&per_page=20
```

**Response**:
```json
{
  "data": [...],
  "pagination": {
    "page": 3,
    "per_page": 20,
    "total_pages": 25,
    "total_items": 500
  },
  "links": {
    "first": "/api/users?page=1&per_page=20",
    "prev": "/api/users?page=2&per_page=20",
    "self": "/api/users?page=3&per_page=20",
    "next": "/api/users?page=4&per_page=20",
    "last": "/api/users?page=25&per_page=20"
  }
}
```

**Pros**:
- User-friendly (page numbers)
- Easy to understand

**Cons**:
- Same as offset-based

### Cursor-Based Pagination

**Request**:
```http
GET /api/users?cursor=abc123&limit=20
```

**Response**:
```json
{
  "data": [
    { "id": 41, "name": "User 41" },
    { "id": 42, "name": "User 42" },
    ...
  ],
  "pagination": {
    "limit": 20,
    "next_cursor": "def456",
    "prev_cursor": "xyz789",
    "has_more": true
  },
  "links": {
    "next": "/api/users?cursor=def456&limit=20",
    "prev": "/api/users?cursor=xyz789&limit=20"
  }
}
```

**Cursor Generation**:
```python
import base64

# Encode last item's ID + timestamp
cursor_data = f"{last_id}:{last_timestamp}"
cursor = base64.b64encode(cursor_data.encode()).decode()
```

**Pros**:
- Consistent results with real-time changes
- Better performance for large datasets
- No skipped/duplicate items

**Cons**:
- Can't jump to specific page
- No total count (usually)

### Link Header Pagination (RFC 5988)

**Response Headers**:
```http
HTTP/1.1 200 OK
Link: </api/users?page=1>; rel="first",
      </api/users?page=2>; rel="prev",
      </api/users?page=4>; rel="next",
      </api/users?page=10>; rel="last"
X-Total-Count: 200
X-Page: 3
X-Per-Page: 20
```

**Pros**:
- Clean response body
- Standard HTTP headers

**Cons**:
- Less discoverable
- Not all clients parse Link headers

### Keyset Pagination

**Request**:
```http
GET /api/users?since_id=100&limit=20
```

**Response**:
```json
{
  "data": [
    { "id": 101, "name": "User 101" },
    { "id": 102, "name": "User 102" }
  ],
  "pagination": {
    "since_id": 100,
    "max_id": 120,
    "limit": 20
  }
}
```

**Best For**: Infinite scroll, real-time feeds.

### Best Practices

```python
# Good: Include metadata
{
  "data": [...],
  "pagination": {...},
  "links": {...}
}

# Good: Consistent parameter names
GET /api/users?limit=20&offset=0
GET /api/posts?limit=20&offset=0

# Good: Sensible defaults
GET /api/users  # Default: limit=20, offset=0

# Good: Maximum limits
GET /api/users?limit=1000  # Returns error
{
  "error": "limit_exceeded",
  "message": "Maximum limit is 100"
}

# Bad: No pagination info
{
  "users": [...]  # How do I get more?
}
```

---

## Filtering, Sorting, and Searching

### Filtering

**Simple Filters**:
```http
GET /api/users?status=active
GET /api/users?role=admin
GET /api/products?category=electronics
```

**Multiple Values (OR)**:
```http
GET /api/users?role=admin,editor
GET /api/products?category=electronics,computers
```

**Multiple Filters (AND)**:
```http
GET /api/users?status=active&role=admin&department=engineering
```

**Range Filters**:
```http
GET /api/products?price_min=100&price_max=500
GET /api/users?created_after=2025-01-01&created_before=2025-12-31
```

**Complex Filters (Query DSL)**:
```http
POST /api/search/users
Content-Type: application/json

{
  "filters": {
    "and": [
      { "field": "status", "op": "eq", "value": "active" },
      {
        "or": [
          { "field": "role", "op": "eq", "value": "admin" },
          { "field": "role", "op": "eq", "value": "editor" }
        ]
      },
      { "field": "age", "op": "gte", "value": 18 }
    ]
  }
}
```

**LHS Brackets Notation** (advanced):
```http
GET /api/users?filter[status]=active&filter[role][in]=admin,editor
GET /api/products?filter[price][gte]=100&filter[price][lte]=500
```

### Sorting

**Single Field**:
```http
GET /api/users?sort=created_at
GET /api/users?sort=-created_at  # Descending
```

**Multiple Fields**:
```http
GET /api/users?sort=last_name,first_name
GET /api/users?sort=-priority,created_at
```

**Explicit Direction**:
```http
GET /api/users?sort=created_at:asc
GET /api/users?sort=created_at:desc,name:asc
```

**Complex Sorting**:
```json
POST /api/search/users
{
  "sort": [
    { "field": "priority", "order": "desc" },
    { "field": "created_at", "order": "asc" }
  ]
}
```

### Searching

**Full-Text Search**:
```http
GET /api/users?q=john+doe
GET /api/products?search=laptop
```

**Field-Specific Search**:
```http
GET /api/users?name=john&email=doe
GET /api/products?name_contains=laptop
```

**Wildcard Search**:
```http
GET /api/users?name=john*
GET /api/users?email=*@example.com
```

**Advanced Search** (POST):
```http
POST /api/search
Content-Type: application/json

{
  "query": "laptop",
  "filters": {
    "category": ["electronics", "computers"],
    "price": { "min": 500, "max": 2000 }
  },
  "sort": [
    { "field": "relevance", "order": "desc" },
    { "field": "price", "order": "asc" }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20
  }
}
```

**Response**:
```json
{
  "results": [
    {
      "id": 123,
      "name": "Dell Laptop",
      "price": 899,
      "relevance_score": 0.95
    }
  ],
  "facets": {
    "category": {
      "electronics": 45,
      "computers": 32
    },
    "brand": {
      "Dell": 12,
      "HP": 8,
      "Lenovo": 7
    }
  },
  "pagination": {...}
}
```

### Best Practices

```python
# Good: Support common patterns
GET /api/users?status=active&sort=-created_at&limit=20

# Good: Validate filters
GET /api/users?invalid_field=value
Response: {
  "error": "invalid_filter",
  "message": "invalid_field is not a valid filter"
}

# Good: Document operators
GET /api/users?age_gte=18&age_lte=65
# Supported: _eq, _ne, _gt, _gte, _lt, _lte, _in, _contains

# Bad: Unclear syntax
GET /api/users?filters=status:active,role:admin

# Good: Use POST for complex queries
POST /api/search
Body: { complex query DSL }
```

---

## Versioning

### Why Version?

**Breaking changes**:
- Field removal/rename
- Response format changes
- Behavior changes
- New required fields

**Non-breaking changes**:
- New optional fields
- New endpoints
- Bug fixes

### URI Versioning

**Format**:
```
https://api.example.com/v1/users
https://api.example.com/v2/users
```

**Pros**:
- Simple and clear
- Easy to test
- Browser-friendly

**Cons**:
- Versioned URLs everywhere
- Cache invalidation

**Example**:
```python
# Version 1
GET /api/v1/users/123
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com"
}

# Version 2
GET /api/v2/users/123
{
  "id": 123,
  "full_name": "John Doe",  # Renamed field
  "email": "john@example.com",
  "phone": "+1234567890"     # New field
}
```

### Header Versioning

**Custom Header**:
```http
GET /api/users/123
API-Version: 2
```

**Accept Header**:
```http
GET /api/users/123
Accept: application/vnd.example.v2+json
```

**Pros**:
- Clean URLs
- Better caching

**Cons**:
- Less discoverable
- Harder to test

**Example**:
```python
# Request
GET /api/users/123
API-Version: 2
Accept: application/json

# Response
HTTP/1.1 200 OK
API-Version: 2
Content-Type: application/json

{
  "id": 123,
  "full_name": "John Doe"
}
```

### Query Parameter Versioning

**Format**:
```http
GET /api/users/123?version=2
```

**Pros**:
- Simple to implement
- Easy to test

**Cons**:
- Pollutes query namespace
- Not RESTful

### Content Negotiation Versioning

**Accept Header**:
```http
GET /api/users/123
Accept: application/vnd.example.v2+json
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/vnd.example.v2+json

{
  "id": 123,
  "full_name": "John Doe"
}
```

**Pros**:
- RESTful
- Flexible

**Cons**:
- Complex
- Hard to discover

### Versioning Strategy

**Semantic Versioning**:
```
Major.Minor.Patch
2.1.0
```

- **Major**: Breaking changes
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes

**API Versioning**:
```
# Only major version in URL/header
GET /api/v2/users

# Minor version in header (optional)
API-Version: 2.1
```

**Best Practices**:
```python
# Good: Version only on breaking changes
/api/v1/users  # Initial version
/api/v2/users  # Breaking changes
/api/v3/users  # More breaking changes

# Bad: Version on every change
/api/v1.0.0/users
/api/v1.0.1/users  # Just a bug fix
/api/v1.1.0/users  # Minor feature

# Good: Support multiple versions
/api/v1/users  # Still supported
/api/v2/users  # Current
/api/v3/users  # Beta

# Good: Deprecation warnings
GET /api/v1/users
Response:
{
  "data": [...],
  "deprecation": {
    "version": "v1",
    "sunset_date": "2026-01-01",
    "migration_guide": "https://docs.example.com/migration/v1-to-v2"
  }
}
```

### Deprecation Process

**Phase 1: Announce**:
```http
GET /api/v1/users

HTTP/1.1 200 OK
Warning: 299 - "API v1 is deprecated. Use v2. See https://docs.example.com"
Sunset: Wed, 01 Jan 2026 00:00:00 GMT
```

**Phase 2: Deprecate**:
```http
GET /api/v1/users

HTTP/1.1 200 OK
Deprecation: true
Warning: 299 - "API v1 will be removed on 2026-01-01"
```

**Phase 3: Sunset**:
```http
GET /api/v1/users

HTTP/1.1 410 Gone
{
  "error": "version_deprecated",
  "message": "API v1 is no longer available. Use v2",
  "migration_guide": "https://docs.example.com/migration/v1-to-v2"
}
```

---

## Error Handling

### Error Response Format

**Standard Format**:
```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "code": "invalid_email",
        "message": "Email format is invalid"
      }
    ],
    "request_id": "req-123456",
    "timestamp": "2025-10-27T10:00:00Z"
  }
}
```

**Simple Format**:
```json
{
  "error": "not_found",
  "message": "User with id 123 not found"
}
```

### RFC 7807 - Problem Details

**Format**:
```json
{
  "type": "https://example.com/problems/validation-error",
  "title": "Request validation failed",
  "status": 422,
  "detail": "The request body contains invalid data",
  "instance": "/api/users",
  "invalid_params": [
    {
      "name": "email",
      "reason": "Invalid email format"
    }
  ]
}
```

**Headers**:
```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/problem+json
```

### Error Codes

**Standard Codes**:
```python
# Authentication/Authorization
"unauthorized"              # 401
"forbidden"                 # 403
"token_expired"             # 401
"invalid_token"             # 401

# Validation
"validation_error"          # 422
"invalid_input"             # 400
"missing_field"             # 400
"invalid_format"            # 400

# Resources
"not_found"                 # 404
"conflict"                  # 409
"gone"                      # 410

# Rate Limiting
"rate_limit_exceeded"       # 429
"quota_exceeded"            # 429

# Server Errors
"internal_error"            # 500
"service_unavailable"       # 503
"gateway_timeout"           # 504
```

### Validation Errors

**Detailed Format**:
```json
{
  "error": "validation_error",
  "message": "Request validation failed",
  "details": [
    {
      "field": "email",
      "code": "invalid_email",
      "message": "Email format is invalid",
      "value": "invalid-email"
    },
    {
      "field": "age",
      "code": "out_of_range",
      "message": "Age must be between 18 and 120",
      "value": -5,
      "constraints": {
        "min": 18,
        "max": 120
      }
    }
  ]
}
```

### Error Context

**Include Helpful Information**:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded",
  "context": {
    "limit": 100,
    "remaining": 0,
    "reset_at": "2025-10-27T11:00:00Z",
    "retry_after": 60
  }
}
```

**Incident Tracking**:
```json
{
  "error": "internal_error",
  "message": "An unexpected error occurred",
  "incident_id": "inc-123456",
  "support_email": "support@example.com"
}
```

### Best Practices

```python
# Good: Consistent error format
{
  "error": "...",
  "message": "...",
  "details": [...]
}

# Bad: Inconsistent
{
  "err": "...",
  "msg": "...",
  "errors": [...]
}

# Good: User-friendly messages
{
  "error": "validation_error",
  "message": "Email address is required"
}

# Bad: Technical messages
{
  "error": "NullPointerException",
  "message": "object reference not set to an instance of an object"
}

# Good: Don't expose sensitive data
{
  "error": "authentication_failed",
  "message": "Invalid credentials"
}

# Bad: Reveals too much
{
  "error": "authentication_failed",
  "message": "User with email john@example.com does not exist"
}

# Good: Include request ID
{
  "error": "internal_error",
  "request_id": "req-123456"
}
```

---

## HATEOAS and Hypermedia

### What is HATEOAS?

**HATEOAS**: Hypermedia as the Engine of Application State

**Principle**: Responses include links to related resources and possible actions.

### Basic Links

**Simple Link**:
```json
{
  "id": 123,
  "name": "John Doe",
  "links": {
    "self": "/api/users/123",
    "orders": "/api/users/123/orders",
    "avatar": "/api/users/123/avatar"
  }
}
```

**Detailed Links**:
```json
{
  "id": 123,
  "name": "John Doe",
  "_links": {
    "self": {
      "href": "/api/users/123",
      "method": "GET"
    },
    "update": {
      "href": "/api/users/123",
      "method": "PUT"
    },
    "delete": {
      "href": "/api/users/123",
      "method": "DELETE"
    },
    "orders": {
      "href": "/api/users/123/orders",
      "method": "GET"
    }
  }
}
```

### HAL (Hypertext Application Language)

**Format**:
```json
{
  "_links": {
    "self": { "href": "/api/users/123" },
    "orders": { "href": "/api/users/123/orders" },
    "avatar": { "href": "/api/users/123/avatar" }
  },
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com"
}
```

**Embedded Resources**:
```json
{
  "_links": {
    "self": { "href": "/api/users/123" }
  },
  "id": 123,
  "name": "John Doe",
  "_embedded": {
    "orders": [
      {
        "_links": {
          "self": { "href": "/api/orders/456" }
        },
        "id": 456,
        "total": 99.99
      }
    ]
  }
}
```

### JSON:API Format

**Resource Object**:
```json
{
  "data": {
    "type": "users",
    "id": "123",
    "attributes": {
      "name": "John Doe",
      "email": "john@example.com"
    },
    "relationships": {
      "orders": {
        "links": {
          "self": "/api/users/123/relationships/orders",
          "related": "/api/users/123/orders"
        },
        "data": [
          { "type": "orders", "id": "456" }
        ]
      }
    },
    "links": {
      "self": "/api/users/123"
    }
  }
}
```

### Collection+JSON

**Format**:
```json
{
  "collection": {
    "version": "1.0",
    "href": "/api/users",
    "items": [
      {
        "href": "/api/users/123",
        "data": [
          { "name": "name", "value": "John Doe" },
          { "name": "email", "value": "john@example.com" }
        ],
        "links": [
          { "rel": "orders", "href": "/api/users/123/orders" }
        ]
      }
    ],
    "template": {
      "data": [
        { "name": "name", "prompt": "Full name" },
        { "name": "email", "prompt": "Email address" }
      ]
    }
  }
}
```

### Practical HATEOAS

**State-Driven Links**:
```json
{
  "id": 456,
  "status": "pending",
  "total": 99.99,
  "_links": {
    "self": { "href": "/api/orders/456" },
    "cancel": {
      "href": "/api/orders/456/cancel",
      "method": "POST"
    },
    "pay": {
      "href": "/api/orders/456/pay",
      "method": "POST"
    }
  }
}

// After payment
{
  "id": 456,
  "status": "paid",
  "total": 99.99,
  "_links": {
    "self": { "href": "/api/orders/456" },
    "refund": {
      "href": "/api/orders/456/refund",
      "method": "POST"
    },
    "invoice": {
      "href": "/api/orders/456/invoice",
      "method": "GET"
    }
  }
}
```

### Benefits

**Discoverability**:
- Clients discover available actions from responses
- No hardcoded URLs in client

**Evolvability**:
- Server can change URLs without breaking clients
- Add new links without versioning

**Self-Documentation**:
- Responses show what's possible
- Reduce documentation burden

### Best Practices

```python
# Good: Include links
{
  "data": {...},
  "_links": {...}
}

# Good: State-specific links
# Only show "cancel" if order is cancellable

# Good: Use standard format (HAL, JSON:API)
# Consistent structure

# Bad: Hardcoded URLs in client
const url = `https://api.example.com/users/${id}`;  # Don't do this

# Good: Follow links from responses
const url = response._links.orders.href;
```

---

## Rate Limiting

### Why Rate Limit?

**Reasons**:
- Prevent abuse
- Ensure fair usage
- Protect infrastructure
- Control costs

### Rate Limiting Strategies

**1. Fixed Window**:
```
100 requests per hour
Window: 10:00-11:00, 11:00-12:00, ...
```

**Problem**: Burst at window boundaries.

**2. Sliding Window**:
```
100 requests per hour
Window: Last 60 minutes from current time
```

**Better**: Smooth distribution.

**3. Token Bucket**:
```
Bucket capacity: 100 tokens
Refill rate: 10 tokens/minute
```

**Best**: Allows bursts while enforcing average rate.

**4. Leaky Bucket**:
```
Queue capacity: 100 requests
Process rate: 10 requests/minute
```

**Best**: Smooth output rate.

### Response Headers

**Standard Headers**:
```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1698400000
X-RateLimit-Used: 13
```

**When Exceeded**:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1698400000

{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again in 60 seconds",
  "retry_after": 60
}
```

### Multiple Limits

**Different Tiers**:
```http
# Free tier
X-RateLimit-Limit: 100
X-RateLimit-Window: hour

# Pro tier
X-RateLimit-Limit: 1000
X-RateLimit-Window: hour

# Enterprise tier
X-RateLimit-Limit: 10000
X-RateLimit-Window: hour
```

**Multiple Windows**:
```http
# Per minute
X-RateLimit-Minute-Limit: 10
X-RateLimit-Minute-Remaining: 8

# Per hour
X-RateLimit-Hour-Limit: 100
X-RateLimit-Hour-Remaining: 87

# Per day
X-RateLimit-Day-Limit: 1000
X-RateLimit-Day-Remaining: 913
```

### Endpoint-Specific Limits

```http
# List users (expensive)
GET /api/users
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87

# Get user (cheap)
GET /api/users/123
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
```

### Cost-Based Rate Limiting

**Different Weights**:
```python
GET /api/users/123        # 1 point
GET /api/users            # 5 points
POST /api/search          # 10 points
POST /api/reports/generate # 50 points
```

**Headers**:
```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Cost: 50
```

### Best Practices

```python
# Good: Clear headers
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1698400000

# Good: Helpful error messages
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again in 60 seconds",
  "retry_after": 60,
  "documentation": "https://docs.example.com/rate-limits"
}

# Good: Different limits for different operations
# Stricter for expensive operations

# Good: Allow bursts
# Token bucket or leaky bucket

# Good: Provide upgrade path
{
  "error": "rate_limit_exceeded",
  "upgrade_url": "https://example.com/pricing"
}
```

---

## Caching

### Cache-Control Header

**Directives**:
```http
# Public (cacheable by any cache)
Cache-Control: public, max-age=3600

# Private (cacheable only by browser)
Cache-Control: private, max-age=3600

# No caching
Cache-Control: no-store

# Revalidate before use
Cache-Control: no-cache

# Must revalidate when stale
Cache-Control: must-revalidate

# Combined
Cache-Control: public, max-age=3600, must-revalidate
```

### ETags

**Strong ETag**:
```http
# Request
GET /api/users/123

# Response
HTTP/1.1 200 OK
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
Content-Type: application/json

{
  "id": 123,
  "name": "John Doe"
}

# Conditional request
GET /api/users/123
If-None-Match: "33a64df551425fcc55e4d42a148795d9f25f89d4"

# Not modified
HTTP/1.1 304 Not Modified
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
```

**Weak ETag**:
```http
ETag: W/"33a64df551425fcc55e4d42a148795d9f25f89d4"
```

### Last-Modified

**Headers**:
```http
# Response
HTTP/1.1 200 OK
Last-Modified: Wed, 27 Oct 2025 10:00:00 GMT

# Conditional request
GET /api/users/123
If-Modified-Since: Wed, 27 Oct 2025 10:00:00 GMT

# Not modified
HTTP/1.1 304 Not Modified
Last-Modified: Wed, 27 Oct 2025 10:00:00 GMT
```

### Conditional Requests

**If-None-Match** (ETags):
```http
GET /api/users/123
If-None-Match: "etag-value"

# 304 Not Modified if ETag matches
# 200 OK with new ETag if changed
```

**If-Modified-Since** (timestamps):
```http
GET /api/users/123
If-Modified-Since: Wed, 27 Oct 2025 10:00:00 GMT

# 304 Not Modified if not modified
# 200 OK if modified
```

**If-Match** (for updates):
```http
PUT /api/users/123
If-Match: "etag-value"
Body: {...}

# 200 OK if ETag matches
# 412 Precondition Failed if changed
```

**If-Unmodified-Since**:
```http
PUT /api/users/123
If-Unmodified-Since: Wed, 27 Oct 2025 10:00:00 GMT
Body: {...}

# 200 OK if not modified
# 412 Precondition Failed if modified
```

### Vary Header

**Content Negotiation**:
```http
HTTP/1.1 200 OK
Vary: Accept, Accept-Language
Content-Type: application/json

# Cache key includes Accept and Accept-Language headers
```

**Example**:
```http
# Request 1
GET /api/users/123
Accept: application/json

# Request 2 (different cache entry)
GET /api/users/123
Accept: application/xml
```

### Cache Strategies

**Immutable Resources**:
```http
# Files with hash in name
GET /assets/script.a3b5c7.js

Cache-Control: public, max-age=31536000, immutable
```

**Short-Lived**:
```http
# Frequently changing data
GET /api/users/me

Cache-Control: private, max-age=60
```

**No Caching**:
```http
# Sensitive or real-time data
GET /api/transactions

Cache-Control: no-store, no-cache, must-revalidate
Pragma: no-cache
```

**Stale-While-Revalidate**:
```http
# Serve stale while fetching fresh
Cache-Control: max-age=60, stale-while-revalidate=120
```

### Best Practices

```python
# Good: Use ETags for dynamic content
HTTP/1.1 200 OK
ETag: "generated-hash"
Cache-Control: private, max-age=0, must-revalidate

# Good: Long cache for static assets
Cache-Control: public, max-age=31536000, immutable

# Good: Vary header for content negotiation
Vary: Accept, Accept-Encoding, Accept-Language

# Bad: No cache headers
# HTTP/1.1 200 OK
# (no caching headers)

# Good: Support conditional requests
If-None-Match: "etag"
If-Modified-Since: date

# Good: Use Expires for legacy clients
Expires: Wed, 27 Oct 2025 11:00:00 GMT
Cache-Control: max-age=3600
```

---

## Authentication and Authorization

### Authentication Methods

**1. API Keys**:
```http
GET /api/users
X-API-Key: your-api-key-here

# Or as query parameter (less secure)
GET /api/users?api_key=your-api-key-here
```

**Pros**: Simple
**Cons**: No expiration, hard to rotate, not user-specific

**2. Basic Authentication**:
```http
GET /api/users
Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

# Base64("username:password")
```

**Pros**: Simple, standard
**Cons**: Insecure over HTTP, credentials in every request

**3. Bearer Tokens (JWT)**:
```http
GET /api/users
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**JWT Payload**:
```json
{
  "sub": "123",
  "name": "John Doe",
  "role": "admin",
  "iat": 1698400000,
  "exp": 1698403600
}
```

**Pros**: Stateless, self-contained, supports expiration
**Cons**: Can't revoke before expiration

**4. OAuth 2.0**:
```http
# Authorization Code Flow
GET /oauth/authorize?
  response_type=code&
  client_id=CLIENT_ID&
  redirect_uri=REDIRECT_URI&
  scope=read write

# Exchange code for token
POST /oauth/token
Body:
  grant_type=authorization_code&
  code=AUTH_CODE&
  client_id=CLIENT_ID&
  client_secret=CLIENT_SECRET

# Use token
GET /api/users
Authorization: Bearer ACCESS_TOKEN
```

**5. API Keys + Secret**:
```http
POST /api/users
X-API-Key: public-key
X-API-Signature: hmac-sha256-signature
X-API-Timestamp: 1698400000

# Signature = HMAC-SHA256(secret, method + path + timestamp + body)
```

### Authorization

**Role-Based Access Control (RBAC)**:
```json
{
  "user_id": 123,
  "roles": ["user", "editor"],
  "permissions": ["read:posts", "write:posts"]
}
```

**Response**:
```http
# Allowed
GET /api/posts/123
Authorization: Bearer token

HTTP/1.1 200 OK
{
  "id": 123,
  "title": "Post title"
}

# Forbidden
DELETE /api/posts/123
Authorization: Bearer token

HTTP/1.1 403 Forbidden
{
  "error": "forbidden",
  "message": "You don't have permission to delete posts"
}
```

**Attribute-Based Access Control (ABAC)**:
```json
{
  "user_id": 123,
  "department": "engineering",
  "clearance_level": 3,
  "location": "US"
}
```

### Token Refresh

**Refresh Token Flow**:
```http
# Login
POST /api/auth/login
Body: { "username": "...", "password": "..." }

Response:
{
  "access_token": "short-lived-token",
  "refresh_token": "long-lived-token",
  "expires_in": 3600
}

# Refresh access token
POST /api/auth/refresh
Body: { "refresh_token": "long-lived-token" }

Response:
{
  "access_token": "new-short-lived-token",
  "expires_in": 3600
}
```

### Best Practices

```python
# Good: Use HTTPS
# ALWAYS use HTTPS for authentication

# Good: Use Authorization header
Authorization: Bearer token

# Bad: Token in URL
GET /api/users?token=secret  # NEVER do this

# Good: Short-lived access tokens
access_token: 15 minutes
refresh_token: 7 days

# Good: Validate tokens
# Check signature, expiration, issuer, audience

# Good: Use scopes
# Limit token permissions

# Good: Rate limit auth endpoints
# Prevent brute force attacks

# Good: Return clear errors
401 Unauthorized: Authentication required
403 Forbidden: Insufficient permissions
```

---

## CORS

### What is CORS?

**CORS** (Cross-Origin Resource Sharing): Mechanism to allow requests from different origins.

**Same Origin**:
```
https://example.com/api/users
https://example.com/app
# Same origin (same protocol, domain, port)
```

**Cross Origin**:
```
https://example.com/api/users
https://app.example.com/
# Different origin (different subdomain)
```

### CORS Headers

**Response Headers**:
```http
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 86400
Access-Control-Expose-Headers: X-Total-Count, X-Page
```

### Simple Requests

**Request**:
```http
GET /api/users
Origin: https://app.example.com
```

**Response**:
```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://app.example.com
Content-Type: application/json

{...}
```

### Preflight Requests

**Preflight (OPTIONS)**:
```http
OPTIONS /api/users
Origin: https://app.example.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Content-Type, Authorization
```

**Response**:
```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

**Actual Request**:
```http
POST /api/users
Origin: https://app.example.com
Content-Type: application/json
Authorization: Bearer token

{...}
```

**Response**:
```http
HTTP/1.1 201 Created
Access-Control-Allow-Origin: https://app.example.com
```

### Credentials

**With Credentials**:
```http
# Request
GET /api/users/me
Origin: https://app.example.com
Cookie: session=abc123

# Response
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Credentials: true
```

**Note**: Cannot use `Access-Control-Allow-Origin: *` with credentials.

### Best Practices

```python
# Good: Specific origins
Access-Control-Allow-Origin: https://app.example.com

# Bad: Wildcard with credentials
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true  # ERROR

# Good: Validate origin
allowed_origins = ["https://app.example.com", "https://web.example.com"]
if request.origin in allowed_origins:
    response.headers["Access-Control-Allow-Origin"] = request.origin

# Good: Cache preflight
Access-Control-Max-Age: 86400  # 24 hours

# Good: Limit methods
Access-Control-Allow-Methods: GET, POST, PUT, DELETE

# Good: Limit headers
Access-Control-Allow-Headers: Content-Type, Authorization, X-Custom-Header
```

---

## API Documentation

### OpenAPI (Swagger)

**Specification**:
```yaml
openapi: 3.0.0
info:
  title: Example API
  version: 1.0.0
  description: Example REST API

servers:
  - url: https://api.example.com/v1

paths:
  /users:
    get:
      summary: List users
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
        - name: offset
          in: query
          schema:
            type: integer
            default: 0
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/User'
                  pagination:
                    $ref: '#/components/schemas/Pagination'

components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
        email:
          type: string
          format: email
      required:
        - id
        - name
        - email

  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - bearerAuth: []
```

### Documentation Elements

**Endpoint Documentation**:
```
# GET /api/users

List all users

## Parameters

- `limit` (integer, optional): Number of results (default: 20, max: 100)
- `offset` (integer, optional): Offset for pagination (default: 0)
- `status` (string, optional): Filter by status (active, inactive)
- `sort` (string, optional): Sort field (created_at, name)

## Response

200 OK
```json
{
  "data": [
    {
      "id": 123,
      "name": "John Doe",
      "email": "john@example.com"
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 100
  }
}
```

## Errors

- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
```

### Code Examples

**Multiple Languages**:
```
# cURL
curl -X GET "https://api.example.com/v1/users?limit=20" \
  -H "Authorization: Bearer token"

# Python
import requests
response = requests.get(
    "https://api.example.com/v1/users",
    headers={"Authorization": "Bearer token"},
    params={"limit": 20}
)

# JavaScript
fetch("https://api.example.com/v1/users?limit=20", {
  headers: {
    "Authorization": "Bearer token"
  }
})

# Go
req, _ := http.NewRequest("GET", "https://api.example.com/v1/users?limit=20", nil)
req.Header.Set("Authorization", "Bearer token")
```

### Best Practices

```python
# Good: Interactive documentation
# Swagger UI, Redoc, Postman Collections

# Good: Examples for every endpoint
# Request examples
# Response examples
# Error examples

# Good: Clear descriptions
# What the endpoint does
# When to use it
# Side effects

# Good: Version documentation
# Document all supported versions
# Migration guides

# Good: Authentication docs
# How to authenticate
# How to get tokens
# Token scopes

# Good: Rate limit docs
# Limits per tier
# Headers to check
# How to request increase
```

---

## Common Patterns

### Bulk Operations

**Bulk Create**:
```http
POST /api/users/bulk
Content-Type: application/json

{
  "users": [
    { "name": "User 1", "email": "user1@example.com" },
    { "name": "User 2", "email": "user2@example.com" }
  ]
}

Response:
{
  "created": [
    { "id": 123, "name": "User 1" },
    { "id": 124, "name": "User 2" }
  ],
  "failed": []
}
```

**Bulk Update**:
```http
PATCH /api/users/bulk
Content-Type: application/json

{
  "updates": [
    { "id": 123, "status": "active" },
    { "id": 124, "status": "inactive" }
  ]
}
```

**Bulk Delete**:
```http
DELETE /api/users/bulk
Content-Type: application/json

{
  "ids": [123, 124, 125]
}

Response:
{
  "deleted": 3
}
```

### Batch Requests

**Multiple Operations**:
```http
POST /api/batch
Content-Type: application/json

{
  "requests": [
    {
      "id": "req1",
      "method": "GET",
      "path": "/api/users/123"
    },
    {
      "id": "req2",
      "method": "GET",
      "path": "/api/orders/456"
    }
  ]
}

Response:
{
  "responses": [
    {
      "id": "req1",
      "status": 200,
      "body": { "id": 123, "name": "John Doe" }
    },
    {
      "id": "req2",
      "status": 200,
      "body": { "id": 456, "total": 99.99 }
    }
  ]
}
```

### Long-Running Operations

**Async Pattern**:
```http
# Start operation
POST /api/reports/generate
Content-Type: application/json

{
  "type": "annual",
  "year": 2025
}

# Accept with job ID
HTTP/1.1 202 Accepted
Location: /api/jobs/job-123

{
  "job_id": "job-123",
  "status": "processing",
  "status_url": "/api/jobs/job-123"
}

# Check status
GET /api/jobs/job-123

{
  "job_id": "job-123",
  "status": "completed",
  "result_url": "/api/reports/report-456"
}

# Get result
GET /api/reports/report-456

{
  "id": "report-456",
  "type": "annual",
  "data": {...}
}
```

### Webhooks

**Register Webhook**:
```http
POST /api/webhooks
Content-Type: application/json

{
  "url": "https://yourapp.com/webhook",
  "events": ["user.created", "user.updated"],
  "secret": "your-secret"
}

Response:
{
  "id": "wh-123",
  "url": "https://yourapp.com/webhook",
  "events": ["user.created", "user.updated"],
  "created_at": "2025-10-27T10:00:00Z"
}
```

**Webhook Payload**:
```http
POST https://yourapp.com/webhook
Content-Type: application/json
X-Webhook-Signature: sha256=signature

{
  "event": "user.created",
  "timestamp": "2025-10-27T10:00:00Z",
  "data": {
    "id": 123,
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

### File Uploads

**Multipart Form Data**:
```http
POST /api/users/123/avatar
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="avatar.jpg"
Content-Type: image/jpeg

[binary data]
------WebKitFormBoundary--

Response:
{
  "url": "https://cdn.example.com/avatars/123.jpg",
  "size": 102400,
  "type": "image/jpeg"
}
```

**Base64 Upload**:
```http
POST /api/users/123/avatar
Content-Type: application/json

{
  "filename": "avatar.jpg",
  "content_type": "image/jpeg",
  "data": "base64-encoded-data"
}
```

**Chunked Upload**:
```http
# Initialize
POST /api/uploads
Response: { "upload_id": "up-123", "chunk_size": 1048576 }

# Upload chunks
PUT /api/uploads/up-123/chunk/0
Content-Range: bytes 0-1048575/10485760

# Complete
POST /api/uploads/up-123/complete
Response: { "file_id": "file-456", "url": "..." }
```

---

## Anti-Patterns

### URL Anti-Patterns

**Bad: Verbs in URLs**:
```
❌ GET /api/getUsers
❌ POST /api/createUser
❌ POST /api/users/deleteUser

✅ GET /api/users
✅ POST /api/users
✅ DELETE /api/users/123
```

**Bad: RPC-style endpoints**:
```
❌ POST /api/users/update
❌ POST /api/orders/calculate

✅ PUT /api/users/123
✅ GET /api/orders/123/total
```

**Bad: Inconsistent naming**:
```
❌ /api/users (plural)
❌ /api/order (singular)
❌ /api/blog_posts (underscore)

✅ /api/users
✅ /api/orders
✅ /api/blog-posts
```

### Response Anti-Patterns

**Bad: Inconsistent formats**:
```
❌ { "users": [...] }
❌ { "data": [...] }
❌ [...]

✅ { "data": [...] }  # Pick one and stick with it
```

**Bad: Metadata in arrays**:
```
❌ [
     { "id": 1, "name": "User 1" },
     { "total": 100, "page": 1 }  # Metadata mixed with data
   ]

✅ {
     "data": [...],
     "pagination": { "total": 100, "page": 1 }
   }
```

**Bad: String booleans**:
```
❌ { "active": "true" }
❌ { "verified": "yes" }

✅ { "active": true }
✅ { "verified": true }
```

### Status Code Anti-Patterns

**Bad: Wrong status codes**:
```
❌ 200 OK with error in body
❌ 404 for validation errors
❌ 500 for user errors

✅ 400 for client errors
✅ 422 for validation errors
✅ 500 only for server errors
```

**Bad: Generic errors**:
```
❌ Always return 500
❌ Always return 400

✅ Use appropriate status codes
```

### Error Anti-Patterns

**Bad: Exposing internals**:
```
❌ {
     "error": "NullPointerException at line 42"
   }

✅ {
     "error": "internal_error",
     "message": "An error occurred",
     "incident_id": "inc-123"
   }
```

**Bad: No error details**:
```
❌ {
     "error": "Invalid request"
   }

✅ {
     "error": "validation_error",
     "details": [
       { "field": "email", "message": "Invalid format" }
     ]
   }
```

### Versioning Anti-Patterns

**Bad: No versioning**:
```
❌ /api/users  # Breaking changes break all clients
```

**Bad: Excessive versioning**:
```
❌ /api/v1.2.3/users  # Too granular
```

**Bad: Version everything**:
```
❌ Every endpoint has different version
❌ /api/users/v3
❌ /api/orders/v1
```

---

## Security Best Practices

### Input Validation

```python
# Validate all inputs
# Reject invalid data early

# Bad
def create_user(data):
    user = User(**data)  # Direct insertion
    db.save(user)

# Good
def create_user(data):
    schema = UserSchema()
    validated = schema.load(data)  # Validation
    user = User(**validated)
    db.save(user)
```

### SQL Injection Prevention

```python
# Bad: String concatenation
query = f"SELECT * FROM users WHERE email = '{email}'"

# Good: Parameterized queries
query = "SELECT * FROM users WHERE email = ?"
db.execute(query, (email,))
```

### XSS Prevention

```python
# Sanitize output
# Escape HTML entities
# Use Content-Type: application/json
# Set Content-Security-Policy header
```

### CSRF Protection

```python
# Use CSRF tokens for state-changing operations
# Verify Origin/Referer headers
# Use SameSite cookies
```

### Authentication Security

```python
# Use HTTPS
# Hash passwords (bcrypt, argon2)
# Use secure token storage
# Implement token expiration
# Rate limit auth endpoints
# Use MFA when possible
```

### Authorization Security

```python
# Check permissions on every request
# Don't trust client-side checks
# Use principle of least privilege
# Validate resource ownership
```

### Rate Limiting

```python
# Prevent abuse
# Limit by IP, user, endpoint
# Return 429 Too Many Requests
```

### Logging and Monitoring

```python
# Log authentication attempts
# Log authorization failures
# Log rate limit violations
# Don't log sensitive data (passwords, tokens)
# Monitor for suspicious patterns
```

---

## Performance Optimization

### Response Compression

```http
# Request
GET /api/users
Accept-Encoding: gzip, deflate, br

# Response
HTTP/1.1 200 OK
Content-Encoding: gzip
Content-Length: 1024

[compressed data]
```

### Field Selection

```http
# Select specific fields
GET /api/users?fields=id,name,email

# Reduce payload size
```

### Resource Expansion

```http
# Avoid N+1 queries
GET /api/orders?expand=customer,items

Response:
{
  "id": 123,
  "customer": { "id": 456, "name": "John Doe" },
  "items": [...]
}
```

### Conditional Requests

```http
# Use ETags and Last-Modified
# Return 304 Not Modified when possible
# Reduce bandwidth
```

### Caching

```python
# Cache responses
# Use CDN for static content
# Cache at multiple levels (browser, CDN, server)
```

### Database Optimization

```python
# Use indexes
# Optimize queries
# Use pagination
# Avoid N+1 queries
# Use connection pooling
```

### Async Processing

```python
# Long-running tasks
# Use background jobs
# Return 202 Accepted
# Provide status endpoint
```

---

## Testing Strategies

### Unit Tests

```python
def test_create_user():
    user_data = {"name": "John", "email": "john@example.com"}
    user = create_user(user_data)
    assert user.name == "John"
    assert user.email == "john@example.com"
```

### Integration Tests

```python
def test_api_create_user():
    response = client.post("/api/users", json={
        "name": "John",
        "email": "john@example.com"
    })
    assert response.status_code == 201
    assert response.json["name"] == "John"
```

### Contract Tests

```python
# Verify API adheres to OpenAPI spec
def test_openapi_compliance():
    spec = load_openapi_spec()
    response = client.get("/api/users")
    validate_response(spec, "/users", "get", response)
```

### Load Tests

```python
# Apache Bench, JMeter, k6, Locust
# Test performance under load
# Identify bottlenecks
```

### Security Tests

```python
# Test authentication
# Test authorization
# Test input validation
# Test rate limiting
# Test CORS
```

---

This comprehensive reference covers REST API design principles, patterns, and best practices. Use it as a guide for building production-grade REST APIs.
