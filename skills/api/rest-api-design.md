---
name: api-rest-api-design
description: Designing RESTful APIs from scratch
---



# REST API Design

**Scope**: RESTful resource modeling, HTTP semantics, URL conventions, status codes
**Lines**: ~280
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Designing RESTful APIs from scratch
- Modeling resources and relationships
- Choosing appropriate HTTP methods
- Structuring API endpoints and URLs
- Selecting correct HTTP status codes
- Implementing API versioning strategies
- Handling errors and validation
- Optimizing for idempotency and caching

## Core Concepts

### RESTful Principles

**REST** (Representational State Transfer): Architectural style for distributed systems.

**Key principles**:
- **Stateless**: Each request contains all needed information
- **Resource-based**: URLs identify resources (nouns, not verbs)
- **HTTP methods**: Use standard methods (GET, POST, PUT, DELETE)
- **Uniform interface**: Consistent patterns across API
- **Self-descriptive**: Responses include metadata (Content-Type, status codes)

---

## Resource Modeling

### Resources are Nouns, Not Verbs

**❌ Wrong** (verb-based):
```
POST /createUser
POST /getUserById
POST /updateUserEmail
POST /deleteUser
```

**✅ Correct** (resource-based):
```
POST   /users          # Create user
GET    /users/:id      # Get user
PUT    /users/:id      # Update user
DELETE /users/:id      # Delete user
```

### Resource Naming Conventions

**Use plural nouns**:
```
GET /users          # ✅ Consistent plural
GET /user           # ❌ Singular (inconsistent)
```

**Lowercase with hyphens** (not underscores or camelCase):
```
GET /user-profiles       # ✅ Kebab-case
GET /user_profiles       # ❌ Snake_case (harder to read in URLs)
GET /userProfiles        # ❌ camelCase (inconsistent)
```

**Hierarchy for relationships**:
```
GET /users/:id/posts              # User's posts
GET /users/:id/posts/:postId      # Specific post by user
GET /posts/:id/comments           # Comments on post
```

**Collections vs Singular Resources**:
```
GET /users           # Collection (returns array)
GET /users/42        # Singular resource (returns object)
GET /users/me        # Special singular (current user)
```

---

## HTTP Method Semantics

### GET - Retrieve Resources

**Purpose**: Fetch data without side effects

**Characteristics**:
- **Safe**: Doesn't modify state
- **Idempotent**: Multiple identical requests = same result
- **Cacheable**: Can be cached by intermediaries

**Examples**:
```
GET /users                    # List all users
GET /users?page=2&limit=20    # Paginated list
GET /users/42                 # Get user by ID
GET /users/42/posts           # Get user's posts
GET /posts?author=alice       # Filtered list
```

**Response**:
```json
// Single resource
{
  "id": 42,
  "email": "alice@example.com",
  "name": "Alice"
}

// Collection
{
  "data": [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
  ],
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}
```

### POST - Create Resources

**Purpose**: Create new resource or trigger action

**Characteristics**:
- **Not safe**: Modifies state
- **Not idempotent**: Multiple requests create multiple resources
- **Not cacheable**

**Examples**:
```
POST /users              # Create new user
POST /posts              # Create new post
POST /posts/42/publish   # Action (publish post)
```

**Request**:
```json
POST /users
Content-Type: application/json

{
  "email": "alice@example.com",
  "name": "Alice",
  "password": "secret123"
}
```

**Response** (201 Created):
```json
HTTP/1.1 201 Created
Location: /users/42
Content-Type: application/json

{
  "id": 42,
  "email": "alice@example.com",
  "name": "Alice",
  "created_at": "2025-10-18T12:00:00Z"
}
```

**Use POST for non-idempotent actions**:
```
POST /orders/42/payments    # Process payment (not idempotent)
POST /users/42/send-email   # Send email (side effect)
```

### PUT - Replace Resource

**Purpose**: Replace entire resource (or create if doesn't exist)

**Characteristics**:
- **Not safe**: Modifies state
- **Idempotent**: Multiple identical requests = same result
- **Not cacheable**

**Examples**:
```
PUT /users/42            # Replace entire user
PUT /posts/123           # Replace entire post
```

**Request** (must include all fields):
```json
PUT /users/42
Content-Type: application/json

{
  "email": "alice@example.com",
  "name": "Alice Cooper",  // Updated
  "bio": "Developer"       // All fields required
}
```

**Response** (200 OK):
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 42,
  "email": "alice@example.com",
  "name": "Alice Cooper",
  "bio": "Developer",
  "updated_at": "2025-10-18T12:00:00Z"
}
```

**PUT for upsert** (create if not exists):
```
PUT /users/alice@example.com   # Create or replace by email
```

### PATCH - Partial Update

**Purpose**: Partially update resource (modify specific fields)

**Characteristics**:
- **Not safe**: Modifies state
- **Not idempotent** (depends on implementation)
- **Not cacheable**

**Examples**:
```
PATCH /users/42          # Update specific fields
PATCH /posts/123         # Update subset of post
```

**Request** (only modified fields):
```json
PATCH /users/42
Content-Type: application/json

{
  "name": "Alice Cooper"   // Only update name
}
```

**Response** (200 OK):
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 42,
  "email": "alice@example.com",
  "name": "Alice Cooper",      // Updated
  "bio": "Developer",          // Unchanged
  "updated_at": "2025-10-18T12:00:00Z"
}
```

**PUT vs PATCH**:
```
PUT /users/42       # Replace entire user (all fields required)
PATCH /users/42     # Update specific fields (partial update)
```

### DELETE - Remove Resource

**Purpose**: Delete resource

**Characteristics**:
- **Not safe**: Modifies state
- **Idempotent**: Deleting twice = same result (404 second time)
- **Not cacheable**

**Examples**:
```
DELETE /users/42         # Delete user
DELETE /posts/123        # Delete post
```

**Response** (204 No Content):
```
HTTP/1.1 204 No Content
```

**Or** (200 OK with body):
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "message": "User deleted successfully",
  "id": 42
}
```

**Soft delete** (use PATCH instead):
```
PATCH /users/42
{"deleted_at": "2025-10-18T12:00:00Z"}
```

---

## HTTP Status Codes

### Success Codes (2xx)

**200 OK**: Standard success response (GET, PUT, PATCH)
```
GET /users/42           → 200 OK + user object
PUT /users/42           → 200 OK + updated user
PATCH /users/42         → 200 OK + updated user
```

**201 Created**: Resource created successfully (POST)
```
POST /users             → 201 Created + new user
Location: /users/42
```

**204 No Content**: Success with no response body (DELETE)
```
DELETE /users/42        → 204 No Content
```

**206 Partial Content**: Partial resource (range requests)
```
GET /videos/123
Range: bytes=0-1024     → 206 Partial Content
```

### Redirection Codes (3xx)

**301 Moved Permanently**: Resource permanently moved
```
GET /old-endpoint       → 301 Moved Permanently
Location: /new-endpoint
```

**304 Not Modified**: Cached version is still valid
```
GET /users/42
If-None-Match: "abc123" → 304 Not Modified
```

### Client Error Codes (4xx)

**400 Bad Request**: Invalid request (validation failed)
```json
POST /users
{"email": "invalid"}    → 400 Bad Request
{
  "error": "Validation failed",
  "details": {
    "email": ["Must be valid email address"]
  }
}
```

**401 Unauthorized**: Authentication required or failed
```
GET /users/me           → 401 Unauthorized
{
  "error": "Authentication required",
  "message": "Missing or invalid token"
}
```

**403 Forbidden**: Authenticated but not authorized
```
DELETE /users/99        → 403 Forbidden
{
  "error": "Forbidden",
  "message": "You don't have permission to delete this user"
}
```

**404 Not Found**: Resource doesn't exist
```
GET /users/99999        → 404 Not Found
{
  "error": "Not found",
  "message": "User not found"
}
```

**409 Conflict**: Request conflicts with current state
```
POST /users
{"email": "alice@example.com"}  → 409 Conflict
{
  "error": "Conflict",
  "message": "User with this email already exists"
}
```

**422 Unprocessable Entity**: Valid syntax, but semantic errors
```
POST /orders
{"product_id": 999}     → 422 Unprocessable Entity
{
  "error": "Unprocessable entity",
  "message": "Product not found"
}
```

**429 Too Many Requests**: Rate limit exceeded
```
GET /users              → 429 Too Many Requests
Retry-After: 60
{
  "error": "Rate limit exceeded",
  "message": "Try again in 60 seconds"
}
```

### Server Error Codes (5xx)

**500 Internal Server Error**: Unexpected server error
```
GET /users              → 500 Internal Server Error
{
  "error": "Internal server error",
  "message": "An unexpected error occurred"
}
```

**502 Bad Gateway**: Upstream server error (proxy/gateway)
```
GET /users              → 502 Bad Gateway
{
  "error": "Bad gateway",
  "message": "Upstream service unavailable"
}
```

**503 Service Unavailable**: Server temporarily unavailable
```
GET /users              → 503 Service Unavailable
Retry-After: 120
{
  "error": "Service unavailable",
  "message": "Server is under maintenance"
}
```

---

## URL Structure Best Practices

### Hierarchical Resource Relationships

```
GET /users/:userId/posts                    # User's posts
GET /users/:userId/posts/:postId            # Specific post
GET /users/:userId/posts/:postId/comments   # Post's comments
```

**Limit nesting to 2-3 levels**:
```
✅ GET /posts/:postId/comments/:commentId
❌ GET /users/:userId/posts/:postId/comments/:commentId/replies/:replyId
```

### Query Parameters for Filtering

**Filtering**:
```
GET /posts?status=published&author=alice
GET /users?role=admin&verified=true
```

**Sorting**:
```
GET /posts?sort=created_at:desc
GET /users?sort=-created_at              # Descending (- prefix)
GET /products?sort=price:asc,name:asc    # Multi-field
```

**Pagination**:
```
GET /posts?page=2&limit=20               # Page-based
GET /posts?offset=20&limit=20            # Offset-based
GET /posts?cursor=abc123&limit=20        # Cursor-based (best for large datasets)
```

**Field selection** (sparse fieldsets):
```
GET /users?fields=id,email,name          # Only return specified fields
GET /posts?include=author,comments       # Include related resources
```

### Action Endpoints (Non-CRUD)

**Use verbs for actions** (not CRUD):
```
POST /posts/:id/publish       # Publish post
POST /users/:id/send-reset    # Send password reset
POST /orders/:id/cancel       # Cancel order
POST /carts/:id/checkout      # Checkout cart
```

**Alternative: Use status changes**:
```
PATCH /posts/:id              # { "status": "published" }
PATCH /orders/:id             # { "status": "cancelled" }
```

---

## Idempotency

### Idempotent Methods

**Safe + Idempotent**: GET, HEAD, OPTIONS
**Idempotent (not safe)**: PUT, DELETE

**GET**: Multiple requests return same data
```
GET /users/42       # Always returns same user (if unchanged)
```

**PUT**: Multiple identical requests = same result
```
PUT /users/42
{"name": "Alice"}   # Setting name to "Alice" multiple times = same result
```

**DELETE**: Multiple deletes = same result
```
DELETE /users/42    # First: 204 No Content
DELETE /users/42    # Second: 404 Not Found (idempotent result)
```

### Non-Idempotent Methods

**POST**: Multiple requests create multiple resources
```
POST /orders        # Creates new order each time
POST /payments      # Processes payment each time (dangerous!)
```

**Making POST idempotent** (idempotency keys):
```
POST /payments
Idempotency-Key: abc123
{"amount": 100}

# Second request with same key returns original response (no duplicate charge)
POST /payments
Idempotency-Key: abc123
{"amount": 100}     # Returns 200 OK with original payment (no new charge)
```

**Implementation**:
```python
def create_payment(request):
    idempotency_key = request.headers.get('Idempotency-Key')

    # Check if already processed
    existing = db.query("SELECT * FROM payments WHERE idempotency_key = %s", [idempotency_key])
    if existing:
        return 200, existing  # Return original result

    # Process new payment
    payment = process_payment(request.body)
    payment.idempotency_key = idempotency_key
    db.save(payment)

    return 201, payment
```

---

## REST Maturity Model (Richardson)

### Level 0: The Swamp of POX (Plain Old XML)

**Single endpoint, single method**:
```
POST /api
{"method": "getUser", "id": 42}
{"method": "createUser", "data": {...}}
```

❌ Not RESTful

### Level 1: Resources

**Multiple endpoints (resources)**:
```
GET /users/42
POST /users
```

✅ Resource-based, but not using HTTP methods correctly

### Level 2: HTTP Verbs

**Proper use of HTTP methods**:
```
GET    /users/42      # Retrieve
POST   /users         # Create
PUT    /users/42      # Update
DELETE /users/42      # Delete
```

✅ RESTful, uses HTTP semantics

### Level 3: Hypermedia (HATEOAS)

**Hypermedia As The Engine Of Application State**:

Responses include links to related resources:
```json
GET /users/42

{
  "id": 42,
  "name": "Alice",
  "email": "alice@example.com",
  "_links": {
    "self": {"href": "/users/42"},
    "posts": {"href": "/users/42/posts"},
    "followers": {"href": "/users/42/followers"},
    "edit": {"href": "/users/42", "method": "PUT"},
    "delete": {"href": "/users/42", "method": "DELETE"}
  }
}
```

**Benefits**:
- Self-documenting API
- Clients discover actions dynamically
- Server can change URLs without breaking clients

**Trade-offs**:
- Increased response size
- More complex client implementation
- Rarely fully implemented in practice

---

## Content Negotiation

### Request Content Type

**Client specifies format**:
```
POST /users
Content-Type: application/json

{"name": "Alice"}
```

**Server validates**:
```
415 Unsupported Media Type (if Content-Type not supported)
```

### Response Content Type

**Client requests format**:
```
GET /users/42
Accept: application/json         # Request JSON
```

**Server responds**:
```
HTTP/1.1 200 OK
Content-Type: application/json

{"id": 42, "name": "Alice"}
```

**Multiple formats supported**:
```
GET /users/42
Accept: application/xml          # Request XML

HTTP/1.1 200 OK
Content-Type: application/xml

<user><id>42</id><name>Alice</name></user>
```

**Versioning via content type**:
```
Accept: application/vnd.myapi.v2+json
```

---

## API Versioning Strategies

### URL Versioning (Most Common)

```
GET /v1/users/42
GET /v2/users/42
```

**Pros**: Simple, explicit, easy to route
**Cons**: URL pollution, hard to migrate

### Header Versioning

```
GET /users/42
Accept: application/vnd.myapi.v2+json
```

**Pros**: Clean URLs, RESTful
**Cons**: Harder to test (can't use browser directly)

### Query Parameter Versioning

```
GET /users/42?version=2
```

**Pros**: Simple, easy to test
**Cons**: Less RESTful, query params should be for filtering

**Recommendation**: URL versioning (`/v1/`, `/v2/`) for simplicity

---

## HTTP Status Code Quick Reference

| Code | Name | Use Case |
|------|------|----------|
| **200** | OK | Successful GET, PUT, PATCH |
| **201** | Created | Successful POST (resource created) |
| **204** | No Content | Successful DELETE or PUT with no response |
| **400** | Bad Request | Validation error, malformed request |
| **401** | Unauthorized | Authentication required or failed |
| **403** | Forbidden | Authenticated but not authorized |
| **404** | Not Found | Resource doesn't exist |
| **409** | Conflict | Resource already exists, version conflict |
| **422** | Unprocessable Entity | Valid syntax, semantic error |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Internal Server Error | Unexpected server error |
| **502** | Bad Gateway | Upstream service error |
| **503** | Service Unavailable | Server under maintenance |

---

## REST API Checklist

```
Resource Modeling:
[ ] Resources are nouns (not verbs)
[ ] Plural nouns for collections (/users, /posts)
[ ] Kebab-case for multi-word resources (/user-profiles)
[ ] Hierarchical relationships (/users/:id/posts)

HTTP Methods:
[ ] GET for retrieval (safe, idempotent)
[ ] POST for creation (non-idempotent)
[ ] PUT for full replacement (idempotent)
[ ] PATCH for partial updates
[ ] DELETE for removal (idempotent)

Status Codes:
[ ] 200 for successful GET/PUT/PATCH
[ ] 201 for successful POST (with Location header)
[ ] 204 for successful DELETE
[ ] 400 for validation errors
[ ] 401 for authentication errors
[ ] 403 for authorization errors
[ ] 404 for not found
[ ] 500 for server errors

Idempotency:
[ ] GET, PUT, DELETE are idempotent
[ ] POST uses idempotency keys for critical operations
[ ] PATCH operations are designed to be repeatable

Response Format:
[ ] Consistent error structure
[ ] Pagination metadata for collections
[ ] Timestamps in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
[ ] Snake_case or camelCase (consistent across API)

Security:
[ ] Authentication required for sensitive endpoints
[ ] Authorization checks before operations
[ ] Rate limiting implemented
[ ] Input validation on all endpoints
```

---

## Common REST Anti-Patterns

❌ **Verbs in URLs**: `/getUser`, `/createPost`
✅ Use nouns + HTTP methods: `GET /users`, `POST /posts`

❌ **Using GET for actions**: `GET /users/42/delete`
✅ Use DELETE: `DELETE /users/42`

❌ **Returning 200 for errors**: `200 OK {"error": "User not found"}`
✅ Use proper status codes: `404 Not Found {"error": "User not found"}`

❌ **Inconsistent naming**: `/users`, `/post`, `/getComments`
✅ Consistent plural nouns: `/users`, `/posts`, `/comments`

❌ **Deep nesting**: `/orgs/:id/teams/:id/users/:id/posts/:id/comments/:id`
✅ Limit to 2-3 levels: `/posts/:id/comments` or `/comments?post_id=:id`

❌ **Ignoring idempotency**: `POST /payments` (no idempotency key)
✅ Implement idempotency: `Idempotency-Key` header

❌ **Exposing internal IDs**: `/users/42` (auto-increment)
✅ Use UUIDs or obfuscated IDs: `/users/550e8400-e29b-41d4-a716-446655440000`

---

## Related Skills

- `http-caching-strategies.md` - Cache headers, ETags, conditional requests
- `api-authentication.md` - JWT, OAuth2, API keys
- `api-rate-limiting.md` - Rate limiting strategies
- `graphql-vs-rest.md` - When to use GraphQL vs REST
- `openapi-documentation.md` - Documenting APIs with OpenAPI/Swagger

---

## Level 3: Resources

This skill includes comprehensive Level 3 resources in the `/resources/` directory:

### Reference Material (`resources/REFERENCE.md`)

Comprehensive 1,800+ line reference covering:
- REST principles (stateless, resource-based, uniform interface)
- HTTP methods (GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD)
- Status codes (proper usage for 2xx, 3xx, 4xx, 5xx)
- URL design and resource naming
- Request/response formats (JSON, content negotiation)
- Pagination strategies (offset, cursor, page-based)
- Filtering, sorting, and searching
- Versioning strategies (URI, header, content negotiation)
- Error handling and problem details (RFC 7807)
- HATEOAS and hypermedia
- Rate limiting and throttling
- Caching (ETags, Cache-Control, conditional requests)
- Authentication and authorization
- CORS
- API documentation (OpenAPI/Swagger)
- Security best practices
- Performance optimization
- Testing strategies
- Common patterns and anti-patterns

### Executable Scripts (`resources/scripts/`)

**validate_api.py**:
- Validate REST API design against best practices
- Check resource naming conventions, HTTP method usage, status codes
- Validate response format consistency, security headers, rate limiting
- Support for OpenAPI specs and custom formats
- JSON output for CI/CD integration

**generate_openapi.py**:
- Generate OpenAPI specs from Python (FastAPI, Flask) or JavaScript (Express) code
- Convert Swagger 2.0 to OpenAPI 3.0
- Generate client code (Python, JavaScript, TypeScript) from OpenAPI specs
- Automatic endpoint detection and schema generation

**test_api.sh**:
- Test REST API endpoints with various scenarios
- CRUD operations, error handling, authentication
- Pagination, filtering, sorting, caching
- Rate limiting, CORS, content negotiation
- Save responses and generate JSON reports

### Complete Examples (`resources/examples/`)

**python/fastapi_rest.py**:
- Complete REST API with FastAPI
- Resource-based endpoints, proper HTTP methods and status codes
- Pagination, filtering, sorting
- Authentication with Bearer tokens
- Rate limiting, caching headers
- Error handling with RFC 7807 format
- Request validation with Pydantic

**node/express_rest.js**:
- Complete REST API with Express.js
- Middleware for authentication, rate limiting, validation
- Error handling and logging
- Security headers with Helmet
- Request ID tracking

**openapi/petstore.yaml**:
- Complete OpenAPI 3.0 specification
- User management API example
- Components, schemas, responses
- Security schemes (Bearer auth)
- Pagination, filtering, error responses

**typescript/api_client.ts**:
- Type-safe API client
- Request/response interceptors
- Retry logic and error handling
- Caching with ETags
- TypeScript interfaces for all models

**curl/test_requests.sh**:
- Comprehensive curl examples
- CRUD operations, filtering, sorting, pagination
- Error handling, authentication, conditional requests
- CORS preflight, rate limiting, compression
- Bulk operations and async patterns

### Usage

```bash
# Validate API design
./resources/scripts/validate_api.py openapi.json --type spec --json

# Generate OpenAPI from code
./resources/scripts/generate_openapi.py from-code api.py --framework fastapi -o openapi.json

# Test API endpoints
./resources/scripts/test_api.sh --url https://api.example.com --api-key TOKEN --verbose

# Run curl examples
cd resources/examples/curl && ./test_requests.sh

# Run FastAPI example
cd resources/examples/python && python fastapi_rest.py

# Run Express example
cd resources/examples/node && node express_rest.js
```

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
