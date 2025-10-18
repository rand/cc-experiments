---
name: api-api-versioning
description: Planning API changes and deciding on versioning approach
---



# API Versioning

**Scope**: API versioning strategies, breaking changes, deprecation workflow, migration patterns
**Lines**: ~200
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Planning API changes and deciding on versioning approach
- Managing multiple API versions in production
- Deprecating old API versions
- Migrating clients to new API versions
- Designing backward compatibility strategies
- Implementing breaking changes safely
- Establishing sunset policies for legacy APIs

## Core Concepts

### What is API Versioning?

**Problem**: APIs evolve over time. Changes can break existing clients.

**Solution**: Maintain multiple API versions simultaneously, allowing clients to migrate gradually.

**Benefits**:
- Backward compatibility for existing clients
- Safe deployment of breaking changes
- Gradual client migration
- Clear contract between API and clients

**Cost**:
- Maintenance burden (multiple codebases)
- Testing complexity
- Documentation overhead

---

## Versioning Strategies

### 1. URL Path Versioning

**Format**: `/v1/users`, `/v2/users`

**Example**:
```
GET /v1/users/123
GET /v2/users/123
```

**Implementation** (FastAPI):
```python
from fastapi import FastAPI

app = FastAPI()

# Version 1
@app.get("/v1/users/{user_id}")
async def get_user_v1(user_id: int):
    return {"id": user_id, "name": "Alice"}

# Version 2 (with email field)
@app.get("/v2/users/{user_id}")
async def get_user_v2(user_id: int):
    return {
        "id": user_id,
        "name": "Alice",
        "email": "alice@example.com"
    }
```

**Pros**:
- Simple and explicit
- Easy to route and cache
- Visible in logs and monitoring
- Works with all HTTP clients

**Cons**:
- URL changes break bookmarks
- Version in URL feels unnatural
- No granular versioning per endpoint

**Best for**: Public APIs, REST APIs, simple versioning schemes

---

### 2. Header Versioning

**Format**: `Accept: application/vnd.api.v1+json`

**Example**:
```http
GET /users/123
Accept: application/vnd.api.v2+json
```

**Implementation** (FastAPI):
```python
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    accept: str = Header(default="application/vnd.api.v1+json")
):
    if "v2" in accept:
        return {
            "id": user_id,
            "name": "Alice",
            "email": "alice@example.com"
        }
    elif "v1" in accept:
        return {"id": user_id, "name": "Alice"}
    else:
        raise HTTPException(400, "Unsupported API version")
```

**Pros**:
- Clean URLs (no version pollution)
- RESTful (resource unchanged, representation varies)
- Granular control per request

**Cons**:
- Less discoverable (hidden in headers)
- Harder to test (need header support)
- Caching complexity

**Best for**: Internal APIs, strict REST adherence, content negotiation

---

### 3. Query Parameter Versioning

**Format**: `/users?api_version=2`

**Example**:
```
GET /users/123?api_version=2
```

**Implementation** (FastAPI):
```python
from fastapi import FastAPI, Query

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    api_version: int = Query(default=1)
):
    if api_version == 2:
        return {
            "id": user_id,
            "name": "Alice",
            "email": "alice@example.com"
        }
    else:
        return {"id": user_id, "name": "Alice"}
```

**Pros**:
- Simple to implement
- Easy to test (just add parameter)
- Works with all clients

**Cons**:
- Version in query string feels unnatural
- Pollutes URL space
- Can conflict with other parameters

**Best for**: Simple internal APIs, quick prototypes

---

### 4. Custom Header Versioning

**Format**: `X-API-Version: 2`

**Example**:
```http
GET /users/123
X-API-Version: 2
```

**Implementation** (FastAPI):
```python
from fastapi import FastAPI, Header

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    x_api_version: int = Header(default=1)
):
    if x_api_version == 2:
        return {
            "id": user_id,
            "name": "Alice",
            "email": "alice@example.com"
        }
    else:
        return {"id": user_id, "name": "Alice"}
```

**Pros**:
- Clean URLs
- Explicit versioning
- Easy to add middleware

**Cons**:
- Custom headers not standard
- Requires client header support
- Less discoverable

**Best for**: Internal APIs, microservices, controlled environments

---

## Breaking vs Non-Breaking Changes

### Non-Breaking Changes (Safe)

**Can deploy without versioning**:

✅ **Adding optional fields to request**:
```json
// Before
{"name": "Alice"}

// After (optional email)
{"name": "Alice", "email": "alice@example.com"}
```

✅ **Adding new fields to response**:
```json
// Before
{"id": 1, "name": "Alice"}

// After (added email)
{"id": 1, "name": "Alice", "email": "alice@example.com"}
```

✅ **Adding new endpoints**:
```
POST /v1/users        (existing)
POST /v1/users/bulk   (new, safe)
```

✅ **Adding new optional query parameters**
✅ **Expanding enum values** (if clients ignore unknown)
✅ **Relaxing validation** (accepting more input)

---

### Breaking Changes (Require Versioning)

**Must introduce new version**:

❌ **Removing fields from response**:
```json
// Before
{"id": 1, "name": "Alice", "email": "alice@example.com"}

// After (removed email) - BREAKS CLIENTS
{"id": 1, "name": "Alice"}
```

❌ **Renaming fields**:
```json
// Before
{"user_id": 1}

// After - BREAKS CLIENTS
{"id": 1}
```

❌ **Changing field types**:
```json
// Before
{"created_at": "2025-01-15"}

// After - BREAKS CLIENTS
{"created_at": 1736899200}
```

❌ **Making optional field required**
❌ **Removing endpoints**
❌ **Changing URL structure**
❌ **Stricter validation** (rejecting previously valid input)
❌ **Changing authentication scheme**

---

## Breaking Change Checklist

Before introducing breaking change:

```
[ ] Identified all affected clients
[ ] Planned new version number/identifier
[ ] Implemented both old and new versions
[ ] Created migration guide for clients
[ ] Set deprecation timeline (e.g., 6 months)
[ ] Added deprecation warnings to old version
[ ] Updated documentation
[ ] Communicated timeline to stakeholders
[ ] Monitored usage of old version
[ ] Planned sunset date for old version
```

---

## Deprecation Workflow

### Phase 1: Announce (Month 0)

**Actions**:
1. Document breaking changes
2. Announce deprecation timeline
3. Add deprecation headers to old version

**Example** (FastAPI):
```python
from fastapi import Response

@app.get("/v1/users/{user_id}")
async def get_user_v1(user_id: int, response: Response):
    # Add deprecation warning
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2025-07-01"
    response.headers["Link"] = '</v2/users>; rel="successor-version"'

    return {"id": user_id, "name": "Alice"}
```

**Communication**:
```
Subject: API v1 Deprecation Notice

We're deprecating /v1/users in favor of /v2/users.

Timeline:
- Today: v2 available, v1 still supported
- Month 3: Deprecation warnings added to v1
- Month 6: v1 sunset (will return 410 Gone)

Migration guide: https://docs.api.com/v1-to-v2

Questions? Contact api-support@example.com
```

---

### Phase 2: Warn (Month 3)

**Actions**:
1. Log clients still using old version
2. Send targeted emails to heavy users
3. Add warning in response body

**Example**:
```python
@app.get("/v1/users/{user_id}")
async def get_user_v1(user_id: int, response: Response):
    response.headers["X-Deprecation-Warning"] = "v1 will sunset on 2025-07-01"

    return {
        "id": user_id,
        "name": "Alice",
        "_deprecation": {
            "message": "This endpoint will be removed on 2025-07-01",
            "migration_guide": "https://docs.api.com/v1-to-v2"
        }
    }
```

---

### Phase 3: Sunset (Month 6)

**Actions**:
1. Return `410 Gone` for old version
2. Redirect to migration guide
3. Monitor for stragglers

**Example**:
```python
@app.get("/v1/users/{user_id}")
async def get_user_v1(user_id: int):
    raise HTTPException(
        status_code=410,
        detail={
            "error": "This API version has been sunset",
            "sunset_date": "2025-07-01",
            "migration_guide": "https://docs.api.com/v1-to-v2",
            "new_endpoint": "/v2/users/{user_id}"
        }
    )
```

---

## Deprecation Timeline Template

```
Month 0: Announcement
  - Release v2 alongside v1
  - Announce deprecation timeline
  - Update documentation

Month 1-2: Migration Period
  - Monitor v1 usage
  - Provide migration support
  - Send reminder emails

Month 3: Warning Phase
  - Add deprecation headers
  - Log clients using v1
  - Contact heavy users directly

Month 4-5: Final Warning
  - Increase warning visibility
  - Offer migration assistance
  - Set hard sunset date

Month 6: Sunset
  - Return 410 Gone for v1
  - Redirect to migration guide
  - Monitor for issues
```

**Adjust timeline based on**:
- API criticality (longer for critical APIs)
- Number of clients (longer for many clients)
- Migration complexity (longer for complex changes)

**Recommended timelines**:
- Internal APIs: 3 months
- Public APIs: 6-12 months
- Critical APIs: 12-24 months

---

## Version Migration Patterns

### Pattern 1: Parallel Versions

**Strategy**: Run old and new versions side-by-side.

```python
# v1/users.py
@router.get("/v1/users/{user_id}")
async def get_user_v1(user_id: int):
    return {"id": user_id, "name": "Alice"}

# v2/users.py
@router.get("/v2/users/{user_id}")
async def get_user_v2(user_id: int):
    return {
        "id": user_id,
        "name": "Alice",
        "email": "alice@example.com"
    }
```

**Pros**: Clean separation, easy rollback
**Cons**: Code duplication, maintenance burden

---

### Pattern 2: Adapter Pattern

**Strategy**: Single core implementation, adapters for each version.

```python
# core/users.py
def get_user_data(user_id: int):
    return {
        "id": user_id,
        "name": "Alice",
        "email": "alice@example.com"
    }

# api/v1.py
@app.get("/v1/users/{user_id}")
async def get_user_v1(user_id: int):
    data = get_user_data(user_id)
    # Adapter: remove email for v1
    return {"id": data["id"], "name": data["name"]}

# api/v2.py
@app.get("/v2/users/{user_id}")
async def get_user_v2(user_id: int):
    return get_user_data(user_id)  # Full data
```

**Pros**: Single source of truth, less duplication
**Cons**: Adapter complexity increases over time

---

### Pattern 3: Feature Flags

**Strategy**: Use flags to toggle new behavior.

```python
from functools import wraps

def version_aware(func):
    @wraps(func)
    async def wrapper(user_id: int, version: int = 1):
        data = await func(user_id)

        if version == 1:
            # Remove new fields for v1
            return {k: v for k, v in data.items() if k in ["id", "name"]}
        else:
            return data

    return wrapper

@version_aware
async def get_user(user_id: int):
    return {
        "id": user_id,
        "name": "Alice",
        "email": "alice@example.com"
    }
```

**Pros**: Single endpoint, flexible
**Cons**: Complexity in logic, harder to test

---

## Backward Compatibility Techniques

### Technique 1: Additive Changes Only

**Rule**: Only add, never remove or change.

```json
// Version 1
{"id": 1, "name": "Alice"}

// Version 1.1 (backward compatible)
{"id": 1, "name": "Alice", "email": "alice@example.com"}

// Version 1.2 (still backward compatible)
{"id": 1, "name": "Alice", "email": "alice@example.com", "phone": "555-1234"}
```

**Clients ignore unknown fields** → No breaking changes.

---

### Technique 2: Default Values

**Strategy**: Provide defaults for new required fields.

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int
    name: str
    email: str = Field(default="noreply@example.com")  # Default for old clients
```

**Old requests** (no email) → Use default
**New requests** (with email) → Use provided value

---

### Technique 3: Field Aliases

**Strategy**: Support both old and new field names.

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    user_id: int = Field(alias="id")  # Accept both "id" and "user_id"
    name: str
```

**Accepts**:
```json
{"id": 1, "name": "Alice"}         // Old clients
{"user_id": 1, "name": "Alice"}    // New clients
```

---

## Versioning Strategy Comparison

| Strategy | Discoverability | Caching | Simplicity | Best For |
|----------|----------------|---------|------------|----------|
| **URL Path** | ⭐⭐⭐ High | ⭐⭐⭐ Easy | ⭐⭐⭐ Simple | Public APIs, REST |
| **Header (Accept)** | ⭐ Low | ⭐ Complex | ⭐⭐ Moderate | Strict REST, Internal |
| **Query Param** | ⭐⭐ Medium | ⭐⭐ Moderate | ⭐⭐⭐ Simple | Prototypes, Internal |
| **Custom Header** | ⭐ Low | ⭐⭐ Moderate | ⭐⭐ Moderate | Microservices, Internal |

**Recommendation**: Use **URL Path Versioning** for simplicity and discoverability unless strict REST compliance required.

---

## Related Skills

- `fastapi-routing.md` - Organizing API routes and versioning
- `api-design-patterns.md` - RESTful API design principles
- `api-documentation.md` - Documenting versioned APIs (OpenAPI/Swagger)
- `database-migrations.md` - Versioning database schemas alongside APIs
- `feature-flags.md` - Using feature flags for gradual rollouts

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
