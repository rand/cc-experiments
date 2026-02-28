---
name: discover-api
description: Automatically discover API design skills when working with REST APIs, GraphQL schemas, API authentication, OAuth, JWT, rate limiting, API versioning, error handling, or endpoint design. Activates for backend API development tasks.
license: MIT
metadata:
  author: rand
  version: "4.0"
compatibility: Designed for Claude Code. Compatible with any agent supporting the Agent Skills format.
---

# API Skills Discovery

Provides automatic access to comprehensive API design, authentication, and implementation skills.

## When This Skill Activates

This skill auto-activates when you're working with:
- REST API design and implementation
- GraphQL schema design
- API authentication (JWT, OAuth 2.0, API keys, sessions)
- API authorization (RBAC, ABAC, permissions)
- Rate limiting and throttling
- API versioning strategies
- Error handling and validation
- HTTP methods, status codes, endpoints

## Available Skills

### Quick Reference

The API category contains 8 specialized skills:

1. **rest-api-design** - RESTful resource modeling, HTTP semantics, URL conventions
2. **graphql-schema-design** - GraphQL types, resolvers, N+1 problem prevention
3. **api-authentication** - JWT, OAuth 2.0, API keys, session management
4. **api-authorization** - RBAC, ABAC, policy engines, permission systems
5. **api-rate-limiting** - Token bucket, sliding window, rate limiting algorithms
6. **api-versioning** - API versioning, deprecation, backward compatibility
7. **api-error-handling** - RFC 7807 errors, validation, standardized responses
8. **api-design-rules** - 35 opinionated rules for API design

### Load Full Category Details

For complete descriptions and workflows:

Read ../api/INDEX.md


This loads the full API category index with:
- Detailed skill descriptions
- Usage triggers for each skill
- Common workflow combinations
- Cross-references to related skills

### Load Specific Skills

Load individual skills as needed:


# Core API design
Read ../api/rest-api-design.md
Read ../api/graphql-schema-design.md

# Security and access control
Read ../api/api-authentication.md
Read ../api/api-authorization.md

# Production hardening
Read ../api/api-rate-limiting.md
Read ../api/api-error-handling.md
Read ../api/api-versioning.md

# Rules and best practices
Read ../api/api-design-rules.md


## Common Workflows

### New REST API
**Sequence**: REST design → Authentication → Authorization

Read ../api/rest-api-design.md      # Resource modeling, HTTP methods
Read ../api/api-authentication.md   # User authentication
Read ../api/api-authorization.md    # Access control


### New GraphQL API
**Sequence**: GraphQL schema → Authentication → Authorization

Read ../api/graphql-schema-design.md  # Schema design, resolvers
Read ../api/api-authentication.md     # User authentication
Read ../api/api-authorization.md      # Field-level permissions


### API Hardening
**Sequence**: Rate limiting → Error handling → Versioning

Read ../api/api-rate-limiting.md    # Prevent abuse
Read ../api/api-error-handling.md   # Standardized errors
Read ../api/api-versioning.md       # Manage evolution


### Complete API Stack
**Full implementation from scratch**:


# 1. Design phase
Read ../api/rest-api-design.md

# 2. Security phase
Read ../api/api-authentication.md
Read ../api/api-authorization.md
Read ../api/api-rate-limiting.md

# 3. Production readiness
Read ../api/api-error-handling.md
Read ../api/api-versioning.md


## Skill Selection Guide

**Choose REST API skills when:**
- Building traditional web services
- Need simple CRUD operations
- Working with mobile apps or SPAs
- Require caching and HTTP semantics

**Choose GraphQL skills when:**
- Clients need flexible data fetching
- Reducing over-fetching or under-fetching
- Building aggregation layers
- Need strong typing for APIs

**Authentication vs Authorization:**
- **Authentication** (api-authentication.md): Who are you? (Login, JWT, OAuth)
- **Authorization** (api-authorization.md): What can you do? (Permissions, RBAC)

**Production considerations:**
- Always implement rate limiting for public APIs
- Use versioning from day one
- Standardize error responses early

## Integration with Other Skills

API skills commonly combine with:

**Database skills** (`discover-database`):
- API endpoints → Database queries
- Connection pooling for API servers
- Query optimization for API performance

**Testing skills** (`discover-testing`):
- Integration tests for API endpoints
- Contract testing for API consumers
- Load testing for API performance

**Frontend skills** (`discover-frontend`):
- API client libraries
- Data fetching patterns
- Error handling in UI

**Infrastructure skills** (`discover-infra`, `discover-cloud`):
- API deployment strategies
- Load balancing and scaling
- API gateways and proxies

## Usage Instructions

1. **Auto-activation**: This skill loads automatically when Claude Code detects API-related work
2. **Browse skills**: Run `Read ../api/INDEX.md` for full category overview
3. **Load specific skills**: Use bash commands above to load individual skills
4. **Follow workflows**: Use recommended sequences for common API patterns
5. **Combine skills**: Load multiple skills for comprehensive coverage

## Progressive Loading

This gateway skill (~200 lines, ~2K tokens) enables progressive loading:
- **Level 1**: Gateway loads automatically (you're here now)
- **Level 2**: Load category INDEX.md (~3K tokens) for full overview
- **Level 3**: Load specific skills (~2-3K tokens each) as needed

Total context: 2K + 3K + skill(s) = 5-10K tokens vs 25K+ for entire index.

## Quick Start Examples

**"Design a REST API for a blog"**:
Read ../api/rest-api-design.md


**"Add OAuth authentication to my API"**:
Read ../api/api-authentication.md


**"Implement role-based access control"**:
Read ../api/api-authorization.md


**"Prevent API abuse"**:
Read ../api/api-rate-limiting.md


**"Design an API versioning strategy"**:
Read ../api/api-versioning.md



**Next Steps**: Run `Read ../api/INDEX.md` to see full category details, or load specific skills using the bash commands above.
