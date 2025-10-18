---
name: api-api-authorization
description: Implementing authorization logic in APIs
---



# API Authorization

**Scope**: Authorization models, permission systems, role-based access control
**Lines**: ~240
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Implementing authorization logic in APIs
- Designing permission systems for applications
- Choosing between RBAC, ABAC, or ACL models
- Building multi-tenant authorization systems
- Implementing resource-level permissions
- Configuring policy engines (OPA, Casbin)
- Debugging authorization failures or security vulnerabilities

## Core Concepts

### Authentication vs Authorization

**Authentication**: "Who are you?" - Verifying identity (login, JWT, OAuth)
**Authorization**: "What can you do?" - Verifying permissions

**This skill focuses on authorization only**. For authentication patterns, see `api-authentication.md`.

---

## Authorization Models

### Access Control List (ACL)

**What**: Direct mapping of users/groups to resources and permissions.

**Structure**:
```
Resource → List of (User/Group, Permissions)
```

**Example**:
```json
{
  "document_123": {
    "alice": ["read", "write"],
    "bob": ["read"],
    "editors_group": ["read", "write", "delete"]
  }
}
```

**Strengths**:
- Simple to understand
- Fine-grained control per resource
- Easy to audit ("who has access to X?")

**Weaknesses**:
- Doesn't scale well (many resources × many users)
- Difficult to manage patterns (all docs in folder X)
- Redundant permissions across resources

**Best for**:
- File systems
- Document sharing (Google Docs, Dropbox)
- Small-scale applications with few resources

### Role-Based Access Control (RBAC)

**What**: Permissions assigned to roles, users assigned to roles.

**Structure**:
```
User → Role → Permissions
```

**Example**:
```json
{
  "roles": {
    "admin": ["users:read", "users:write", "users:delete", "posts:*"],
    "editor": ["posts:read", "posts:write", "posts:delete"],
    "viewer": ["posts:read"]
  },
  "users": {
    "alice": ["admin"],
    "bob": ["editor"],
    "charlie": ["viewer"]
  }
}
```

**Strengths**:
- Scales well (manage roles, not individual permissions)
- Industry standard (widely understood)
- Simple to implement and audit
- Role hierarchy possible (manager inherits employee permissions)

**Weaknesses**:
- Coarse-grained (can't easily do "only own resources")
- Role explosion for complex scenarios
- Static (doesn't consider context like time, location)

**Best for**:
- Internal tools (admin panels, CMS)
- SaaS applications
- Enterprise software
- Multi-tenant systems

### Attribute-Based Access Control (ABAC)

**What**: Permissions based on attributes (user, resource, environment).

**Structure**:
```
Policy: IF (user attributes + resource attributes + environment) THEN allow/deny
```

**Example**:
```python
# Policy: Users can edit their own posts during business hours
if (
    user.id == post.author_id
    and current_time >= "09:00"
    and current_time <= "17:00"
    and user.department == post.department
):
    allow("edit")
```

**Attributes**:
- **User**: role, department, clearance_level, location
- **Resource**: owner, sensitivity, department, created_date
- **Environment**: time, IP address, device_type

**Strengths**:
- Extremely flexible (context-aware)
- Fine-grained control
- Reduces role explosion
- Dynamic (evaluates at runtime)

**Weaknesses**:
- Complex to implement and debug
- Performance overhead (policy evaluation)
- Difficult to audit ("who can access X?")
- Requires policy engine (OPA, Casbin)

**Best for**:
- Healthcare (HIPAA compliance)
- Government/military (clearance levels)
- Complex organizational hierarchies
- Context-dependent access (time, location)

---

## Authorization Model Decision Tree

```
Start: What's your primary requirement?
│
├─ Simple resource sharing?
│  └─ ACL (Google Docs-style)
│
├─ Predictable organizational roles?
│  ├─ Few roles (<10) → RBAC
│  ├─ Many roles (>20) → Continue
│  └─ Complex hierarchy → Hierarchical RBAC
│
├─ Context-dependent access? (time, location, attributes)
│  └─ ABAC (with policy engine)
│
├─ Resource-level permissions needed?
│  ├─ Per-user → ACL or ABAC
│  ├─ Per-role → RBAC with resource scopes
│  └─ Dynamic → ABAC
│
├─ Audit requirements?
│  ├─ "Who has access?" → ACL or RBAC
│  └─ "Who accessed X?" → Any (with logging)
│
└─ Default → RBAC (most common)
```

---

## RBAC vs ABAC Comparison

| Criteria | RBAC | ABAC |
|----------|------|------|
| **Complexity** | Low (roles + permissions) | High (policies + attributes) |
| **Granularity** | Coarse (role-level) | Fine (attribute-level) |
| **Scalability** | Good (role explosion risk) | Excellent (policy-based) |
| **Performance** | Fast (lookup) | Slower (policy evaluation) |
| **Auditability** | Easy ("list role permissions") | Hard ("evaluate all policies") |
| **Context-awareness** | None | Full (time, location, etc.) |
| **Implementation time** | Days | Weeks/months |
| **Best for** | 80% of applications | Complex compliance scenarios |

---

## Implementing RBAC

### Database Schema (PostgreSQL)

```sql
-- Users table
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL
);

-- Roles table
CREATE TABLE roles (
  id SERIAL PRIMARY KEY,
  name VARCHAR(50) UNIQUE NOT NULL,  -- e.g., "admin", "editor"
  description TEXT
);

-- Permissions table
CREATE TABLE permissions (
  id SERIAL PRIMARY KEY,
  resource VARCHAR(100) NOT NULL,    -- e.g., "posts", "users"
  action VARCHAR(50) NOT NULL,       -- e.g., "read", "write", "delete"
  UNIQUE(resource, action)
);

-- Role-Permission mapping (many-to-many)
CREATE TABLE role_permissions (
  role_id INT REFERENCES roles(id),
  permission_id INT REFERENCES permissions(id),
  PRIMARY KEY (role_id, permission_id)
);

-- User-Role mapping (many-to-many)
CREATE TABLE user_roles (
  user_id INT REFERENCES users(id),
  role_id INT REFERENCES roles(id),
  PRIMARY KEY (user_id, role_id)
);
```

### Permission Check Query

```sql
-- Check if user has permission
SELECT EXISTS (
  SELECT 1
  FROM user_roles ur
  JOIN role_permissions rp ON ur.role_id = rp.role_id
  JOIN permissions p ON rp.permission_id = p.id
  WHERE ur.user_id = $1           -- User ID
    AND p.resource = $2           -- e.g., "posts"
    AND p.action = $3             -- e.g., "write"
) AS has_permission;
```

### Authorization Middleware (Python/FastAPI)

```python
from functools import wraps
from fastapi import HTTPException, Depends

def require_permission(resource: str, action: str):
    """Decorator to check permissions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=Depends(get_current_user), **kwargs):
            # Query database for permission
            has_perm = await db.fetch_one(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM user_roles ur
                  JOIN role_permissions rp ON ur.role_id = rp.role_id
                  JOIN permissions p ON rp.permission_id = p.id
                  WHERE ur.user_id = $1 AND p.resource = $2 AND p.action = $3
                ) AS has_permission
                """,
                [current_user.id, resource, action]
            )

            if not has_perm["has_permission"]:
                raise HTTPException(status_code=403, detail="Permission denied")

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage
@app.delete("/posts/{post_id}")
@require_permission("posts", "delete")
async def delete_post(post_id: int, current_user: User):
    # Delete post logic
    pass
```

---

## Resource-Level Permissions

### Problem: RBAC + Ownership

**Scenario**: Editors can edit posts, but only their own posts.

**Solution 1: Hybrid RBAC + Resource Check**

```python
@app.put("/posts/{post_id}")
@require_permission("posts", "write")
async def update_post(post_id: int, current_user: User):
    post = await db.fetch_one("SELECT * FROM posts WHERE id = $1", [post_id])

    if not post:
        raise HTTPException(status_code=404)

    # Resource-level check
    if post["author_id"] != current_user.id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not your post")

    # Update post
    pass
```

**Solution 2: Scope-Based Permissions**

```sql
-- Add scope to permissions
ALTER TABLE role_permissions ADD COLUMN scope VARCHAR(50);
-- scope values: "all", "own", "department"

-- Check with scope
SELECT
  p.action,
  rp.scope
FROM user_roles ur
JOIN role_permissions rp ON ur.role_id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
WHERE ur.user_id = $1
  AND p.resource = $2;
```

```python
def check_resource_permission(user, resource, action, resource_obj):
    perms = get_user_permissions(user, resource, action)

    for perm in perms:
        if perm.scope == "all":
            return True
        elif perm.scope == "own" and resource_obj.owner_id == user.id:
            return True
        elif perm.scope == "department" and resource_obj.department == user.department:
            return True

    return False
```

---

## Hierarchical Roles

### Role Inheritance

**Example**: Manager inherits all Employee permissions + additional permissions.

```sql
-- Add parent_role_id for hierarchy
ALTER TABLE roles ADD COLUMN parent_role_id INT REFERENCES roles(id);

-- Example hierarchy
INSERT INTO roles (name, parent_role_id) VALUES
  ('employee', NULL),
  ('manager', (SELECT id FROM roles WHERE name = 'employee')),
  ('director', (SELECT id FROM roles WHERE name = 'manager'));
```

**Permission check with inheritance**:

```sql
-- Recursive CTE to get all inherited permissions
WITH RECURSIVE role_hierarchy AS (
  -- Base: User's direct roles
  SELECT r.id, r.name, r.parent_role_id
  FROM user_roles ur
  JOIN roles r ON ur.role_id = r.id
  WHERE ur.user_id = $1

  UNION

  -- Recursive: Parent roles
  SELECT r.id, r.name, r.parent_role_id
  FROM roles r
  JOIN role_hierarchy rh ON r.id = rh.parent_role_id
)
SELECT EXISTS (
  SELECT 1
  FROM role_hierarchy rh
  JOIN role_permissions rp ON rh.id = rp.role_id
  JOIN permissions p ON rp.permission_id = p.id
  WHERE p.resource = $2 AND p.action = $3
) AS has_permission;
```

---

## Policy Engines

### Open Policy Agent (OPA)

**What**: Declarative policy engine using Rego language.

**Use case**: Complex ABAC policies, Kubernetes admission control.

**Example policy** (`policy.rego`):

```rego
package app.authz

# Allow if user is admin
allow {
  input.user.role == "admin"
}

# Allow if user owns the resource
allow {
  input.user.id == input.resource.owner_id
}

# Allow if user is in same department and resource is not confidential
allow {
  input.user.department == input.resource.department
  input.resource.confidential == false
}
```

**Usage** (Python):

```python
import requests

def check_permission(user, resource, action):
    policy_input = {
        "user": {
            "id": user.id,
            "role": user.role,
            "department": user.department
        },
        "resource": {
            "id": resource.id,
            "owner_id": resource.owner_id,
            "department": resource.department,
            "confidential": resource.confidential
        },
        "action": action
    }

    response = requests.post(
        "http://opa:8181/v1/data/app/authz/allow",
        json={"input": policy_input}
    )

    return response.json().get("result", False)
```

**Pros**:
- Declarative (easy to read policies)
- Centralized policy management
- Language-agnostic (HTTP API)

**Cons**:
- Operational complexity (separate service)
- Learning curve (Rego syntax)

### Casbin

**What**: Authorization library with multiple models (RBAC, ABAC, ACL).

**Use case**: Embed authorization in application code.

**Example** (Python):

```python
import casbin

# Load model and policy
enforcer = casbin.Enforcer("model.conf", "policy.csv")

# Check permission
if enforcer.enforce("alice", "posts", "write"):
    print("Allowed")
else:
    print("Denied")
```

**Model file** (`model.conf`):

```ini
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

**Policy file** (`policy.csv`):

```csv
p, admin, posts, *
p, editor, posts, write
p, editor, posts, read
g, alice, admin
g, bob, editor
```

**Pros**:
- Embedded (no external service)
- Supports multiple models
- Good performance (in-memory)

**Cons**:
- Policy stored in CSV/DB (not as readable as OPA)

---

## Scope-Based Authorization

### JWT with Scopes

**What**: Embed permissions in JWT token.

**Example**:

```json
{
  "sub": "alice",
  "role": "editor",
  "scopes": ["posts:read", "posts:write", "users:read"]
}
```

**Authorization middleware**:

```python
def require_scope(required_scope: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, token=Depends(get_token), **kwargs):
            scopes = token.get("scopes", [])

            if required_scope not in scopes:
                raise HTTPException(status_code=403)

            return await func(*args, **kwargs)
        return wrapper
    return decorator

@app.delete("/posts/{post_id}")
@require_scope("posts:delete")
async def delete_post(post_id: int):
    pass
```

**Pros**:
- No database lookup (fast)
- Stateless

**Cons**:
- Can't revoke permissions until token expires
- Token bloat (many scopes)
- Security risk if token leaked (use short expiry)

---

## Common Authorization Pitfalls

### Pitfall 1: Missing Authorization Checks

**Problem**: Implementing authentication but forgetting authorization.

```python
# ❌ BAD: Only checks authentication
@app.delete("/posts/{post_id}")
async def delete_post(post_id: int, current_user=Depends(get_current_user)):
    await db.execute("DELETE FROM posts WHERE id = $1", [post_id])
```

**Solution**: Always check ownership or permissions.

```python
# ✅ GOOD: Checks both authentication and authorization
@app.delete("/posts/{post_id}")
async def delete_post(post_id: int, current_user=Depends(get_current_user)):
    post = await db.fetch_one("SELECT * FROM posts WHERE id = $1", [post_id])

    if not post:
        raise HTTPException(status_code=404)

    if post["author_id"] != current_user.id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403)

    await db.execute("DELETE FROM posts WHERE id = $1", [post_id])
```

### Pitfall 2: Insecure Direct Object Reference (IDOR)

**Problem**: Using predictable IDs without authorization.

```python
# ❌ BAD: Anyone can access any invoice
@app.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: int, current_user=Depends(get_current_user)):
    return await db.fetch_one("SELECT * FROM invoices WHERE id = $1", [invoice_id])
```

**Solution**: Check ownership.

```python
# ✅ GOOD: Only owner can access invoice
@app.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: int, current_user=Depends(get_current_user)):
    invoice = await db.fetch_one(
        "SELECT * FROM invoices WHERE id = $1 AND user_id = $2",
        [invoice_id, current_user.id]
    )

    if not invoice:
        raise HTTPException(status_code=404)  # Don't leak existence

    return invoice
```

### Pitfall 3: Privilege Escalation

**Problem**: Users can assign themselves higher roles.

```python
# ❌ BAD: Users can make themselves admin
@app.put("/users/{user_id}/role")
async def update_role(user_id: int, role: str, current_user=Depends(get_current_user)):
    await db.execute("UPDATE users SET role = $1 WHERE id = $2", [role, user_id])
```

**Solution**: Only admins can assign roles.

```python
# ✅ GOOD: Only admins can assign roles
@app.put("/users/{user_id}/role")
@require_permission("users", "manage_roles")
async def update_role(user_id: int, role: str, current_user=Depends(get_current_user)):
    await db.execute("UPDATE users SET role = $1 WHERE id = $2", [role, user_id])
```

### Pitfall 4: Caching Permissions Too Long

**Problem**: Permissions cached in JWT or session, changes not reflected.

**Solution**:
- Use short-lived tokens (15-30 min)
- Implement token refresh
- For critical permissions, query database

```python
# Hybrid approach: Cache non-critical, query critical
if action in ["delete", "admin_access"]:
    # Always query database for critical actions
    has_perm = await db.fetch_one(query)
else:
    # Use cached permissions from token
    has_perm = action in token["scopes"]
```

---

## Best Practices

### Do's

✅ **Always check authorization** (not just authentication)
✅ **Fail closed** (deny by default, explicit allow)
✅ **Check ownership** for resource-level permissions
✅ **Log authorization failures** (audit trail)
✅ **Use principle of least privilege** (minimal permissions)
✅ **Test with different roles** (ensure isolation)

### Don'ts

❌ **Don't trust client-side authorization** (always check server-side)
❌ **Don't leak information** (404 instead of 403 for private resources)
❌ **Don't use GET for permission changes** (CSRF risk)
❌ **Don't cache permissions indefinitely** (use short TTL)
❌ **Don't expose internal role names** (use display names)

---

## Quick Reference

### Authorization Checklist

```
[ ] Authentication verified (who is the user?)
[ ] Authorization verified (what can they do?)
[ ] Ownership checked (if resource-level)
[ ] Role/permissions cached (with TTL)
[ ] Authorization failures logged
[ ] Edge cases tested (no role, multiple roles, escalation)
[ ] IDOR vulnerabilities checked
[ ] Privilege escalation prevented
```

### RBAC Implementation Checklist

```
[ ] Database schema (users, roles, permissions, mappings)
[ ] Permission check function/query
[ ] Authorization middleware/decorator
[ ] Resource-level checks (ownership)
[ ] Role hierarchy (if needed)
[ ] Audit logging
[ ] Unit tests (permission matrix)
```

---

## Related Skills

- `api-authentication.md` - JWT, OAuth, session management
- `database-security.md` - Row-level security, SQL injection prevention
- `api-rate-limiting.md` - Rate limiting per role/user
- `api-multi-tenancy.md` - Tenant isolation in authorization

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
