# API Design Skills

Comprehensive skills for designing, securing, and implementing production-ready APIs.

## Category Overview

**Total Skills**: 7
**Focus**: REST APIs, GraphQL, Authentication, Authorization, Rate Limiting, Versioning, Error Handling
**Use Cases**: Backend API development, microservices, web services, mobile backends

## Skills in This Category

### rest-api-design.md
**Description**: Designing RESTful APIs from scratch
**Lines**: ~280
**Use When**:
- Designing REST APIs from scratch
- Modeling resources and relationships
- Choosing appropriate HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Structuring API endpoints and URLs
- Selecting correct HTTP status codes (200, 201, 400, 404, 500, etc.)
- Implementing idempotency
- Optimizing for caching

**Key Concepts**: Resource modeling, HTTP semantics, URL conventions, status codes, HATEOAS

---

### graphql-schema-design.md
**Description**: Designing GraphQL schemas, resolvers, N+1 prevention
**Lines**: ~320
**Use When**:
- Designing GraphQL schemas and type systems
- Implementing resolvers efficiently
- Preventing N+1 query problems
- Building aggregation layers
- Handling complex data relationships
- Implementing batching and DataLoader patterns

**Key Concepts**: Schema design, types, resolvers, queries, mutations, subscriptions, N+1 prevention

---

### api-authentication.md
**Description**: Implementing authentication (JWT, OAuth 2.0, API keys, sessions)
**Lines**: ~280
**Use When**:
- Implementing user authentication
- Choosing between JWT, OAuth 2.0, API keys, sessions
- Designing token refresh flows
- Implementing social login (OAuth providers)
- Managing authentication state
- Securing authentication endpoints

**Key Concepts**: JWT (JSON Web Tokens), OAuth 2.0, API keys, sessions, cookies, token refresh, OpenID Connect

---

### api-authorization.md
**Description**: RBAC, ABAC, policy engines, permission systems
**Lines**: ~270
**Use When**:
- Implementing authorization and access control
- Designing Role-Based Access Control (RBAC)
- Implementing Attribute-Based Access Control (ABAC)
- Building permission systems
- Managing user roles and capabilities
- Implementing policy engines (OPA, Casbin)
- Securing resources at different granularities

**Key Concepts**: RBAC, ABAC, permissions, policies, roles, capabilities, resource-based access control

---

### api-rate-limiting.md
**Description**: Rate limiting strategies, token bucket, sliding window
**Lines**: ~240
**Use When**:
- Preventing API abuse and DDoS attacks
- Implementing rate limiting strategies
- Choosing between token bucket, leaky bucket, sliding window algorithms
- Setting rate limits per user, IP, or API key
- Implementing distributed rate limiting (Redis)
- Designing rate limit headers and responses

**Key Concepts**: Token bucket, leaky bucket, sliding window, fixed window, rate limit headers, Redis-based limiting

---

### api-versioning.md
**Description**: API versioning, deprecation, backward compatibility
**Lines**: ~220
**Use When**:
- Designing API versioning strategies
- Managing breaking changes
- Implementing deprecation workflows
- Maintaining backward compatibility
- Choosing versioning approach (URL, header, content negotiation)
- Communicating changes to API consumers

**Key Concepts**: URL versioning, header versioning, content negotiation, semantic versioning, deprecation, breaking changes

---

### api-error-handling.md
**Description**: Standardized error responses, RFC 7807, validation errors
**Lines**: ~250
**Use When**:
- Implementing standardized error responses
- Following RFC 7807 Problem Details
- Handling validation errors consistently
- Designing error codes and messages
- Logging and monitoring errors
- Providing actionable error information to clients

**Key Concepts**: RFC 7807, error codes, validation errors, error messages, error logging, problem details

---

## Common Workflows

### New REST API
**Goal**: Build a REST API from scratch

**Sequence**:
1. `rest-api-design.md` - Design resources, endpoints, HTTP methods
2. `api-authentication.md` - Add user authentication
3. `api-authorization.md` - Implement access control
4. `api-error-handling.md` - Standardize error responses
5. `api-versioning.md` - Plan for evolution

**Example**: Blog API with posts, comments, users

---

### New GraphQL API
**Goal**: Build a GraphQL API from scratch

**Sequence**:
1. `graphql-schema-design.md` - Design schema, types, resolvers
2. `api-authentication.md` - Add authentication context
3. `api-authorization.md` - Implement field-level permissions
4. `api-error-handling.md` - Handle GraphQL errors
5. `api-rate-limiting.md` - Prevent query complexity abuse

**Example**: Aggregation layer over multiple microservices

---

### API Hardening
**Goal**: Secure and production-harden an existing API

**Sequence**:
1. `api-rate-limiting.md` - Prevent abuse and DDoS
2. `api-error-handling.md` - Standardize error responses
3. `api-versioning.md` - Prepare for future changes
4. `api-authentication.md` - Review authentication security
5. `api-authorization.md` - Audit access control

**Example**: Preparing beta API for public release

---

### Authentication & Authorization
**Goal**: Implement complete auth system

**Sequence**:
1. `api-authentication.md` - Implement user login (JWT or OAuth)
2. `api-authorization.md` - Add role-based access control
3. `api-rate-limiting.md` - Rate limit auth endpoints
4. `api-error-handling.md` - Handle auth errors gracefully

**Example**: Multi-tenant SaaS application

---

### Public API Launch
**Goal**: Launch a public API

**Sequence**:
1. `rest-api-design.md` or `graphql-schema-design.md` - Design API
2. `api-authentication.md` - API keys or OAuth for consumers
3. `api-rate-limiting.md` - Implement tiered rate limiting
4. `api-versioning.md` - Version from day one
5. `api-error-handling.md` - Provide clear error messages
6. `api-authorization.md` - Control access to resources

**Example**: Platform API for third-party developers

---

## Skill Combinations

### With Database Skills (`discover-database`)
- API endpoints backed by database queries
- Connection pooling for API servers
- Query optimization for API performance
- Transaction management for API operations
- Database migrations alongside API versioning

**Common combos**:
- `rest-api-design.md` + `database/postgres-schema-design.md`
- `api-authentication.md` + `database/database-connection-pooling.md`

---

### With Testing Skills (`discover-testing`)
- Integration tests for API endpoints
- Contract testing for API consumers
- Load testing for API performance
- Unit tests for business logic

**Common combos**:
- `rest-api-design.md` + `testing/integration-testing.md`
- `api-rate-limiting.md` + `testing/performance-testing.md`

---

### With Frontend Skills (`discover-frontend`)
- API client libraries and data fetching
- Error handling in UI
- Authentication state management
- Real-time updates (WebSockets, Server-Sent Events)

**Common combos**:
- `graphql-schema-design.md` + `frontend/react-data-fetching.md`
- `api-authentication.md` + `frontend/react-state-management.md`

---

### With Infrastructure Skills (`discover-infra`, `discover-cloud`)
- API deployment strategies
- Load balancing and scaling
- API gateways and proxies
- Service mesh for microservices

**Common combos**:
- `rest-api-design.md` + `infrastructure/infrastructure-security.md`
- `api-rate-limiting.md` + `infrastructure/cost-optimization.md`

---

## Quick Selection Guide

**Choose REST when**:
- Building traditional web services
- Need simple CRUD operations
- Working with mobile apps or SPAs
- Require caching and HTTP semantics
- Want broad tooling support

**Choose GraphQL when**:
- Clients need flexible data fetching
- Reducing over-fetching or under-fetching
- Building aggregation layers
- Need strong typing for APIs
- Want to minimize API versioning

**Authentication vs Authorization**:
- **Authentication** = "Who are you?" → JWT, OAuth, sessions
- **Authorization** = "What can you do?" → RBAC, ABAC, permissions

**When to version**:
- Version from day one for public APIs
- Use semantic versioning for clarity
- Plan deprecation timelines early

**Rate limiting priorities**:
- Public APIs: Always implement
- Internal APIs: Optional but recommended
- Authentication endpoints: Critical (prevent brute force)
- Expensive operations: Essential (prevent abuse)

---

## Loading Skills

All skills are available in the `skills/api/` directory:

```bash
cat skills/api/rest-api-design.md
cat skills/api/graphql-schema-design.md
cat skills/api/api-authentication.md
cat skills/api/api-authorization.md
cat skills/api/api-rate-limiting.md
cat skills/api/api-versioning.md
cat skills/api/api-error-handling.md
```

**Pro tip**: Start with design (`rest-api-design.md` or `graphql-schema-design.md`), then layer on security (`api-authentication.md`, `api-authorization.md`, `api-rate-limiting.md`).

---

**Related Categories**:
- `discover-database` - Database design and queries
- `discover-testing` - API testing strategies
- `discover-frontend` - API consumption patterns
- `discover-infra` - API deployment and scaling
- `discover-cloud` - Serverless APIs (Modal, Lambda, etc.)
