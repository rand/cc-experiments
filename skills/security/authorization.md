---
name: security-authorization
description: Authorization models including RBAC, ABAC, policy engines, and access control patterns for securing resources
---

# Security: Authorization

**Scope**: Access control, RBAC, ABAC, policy engines, permissions
**Lines**: ~360
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Implementing access control systems
- Designing role-based or attribute-based authorization
- Building permission systems for multi-tenant applications
- Implementing policy engines (OPA, Casbin)
- Securing API endpoints and resources
- Preventing privilege escalation vulnerabilities
- Auditing access control decisions

## Authorization Fundamentals

### Authentication vs Authorization

**Authentication**: "Who are you?" - Verifying identity
**Authorization**: "What can you do?" - Verifying permissions

```python
# After authentication
user = authenticate(token)

# Before allowing action
if not user.can("delete", post):
    raise ForbiddenError("You cannot delete this post")

# Perform action
delete_post(post)
```

## Role-Based Access Control (RBAC)

### Basic RBAC Implementation

```python
from enum import Enum
from typing import Set

class Role(Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class User:
    def __init__(self, id: int, username: str, roles: Set[Role]):
        self.id = id
        self.username = username
        self.roles = roles

    def has_role(self, role: Role) -> bool:
        return role in self.roles

# Permission mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: {"read", "write", "delete", "manage_users"},
    Role.EDITOR: {"read", "write"},
    Role.VIEWER: {"read"}
}

def user_can(user: User, permission: str) -> bool:
    """Check if user has permission through any role"""
    for role in user.roles:
        if permission in ROLE_PERMISSIONS.get(role, set()):
            return True
    return False

# Usage
user = User(1, "alice", {Role.EDITOR})

if user_can(user, "write"):
    update_document(doc)
else:
    raise ForbiddenError("Insufficient permissions")
```

### Database Schema for RBAC

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Roles table
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- User-Role assignment (many-to-many)
CREATE TABLE user_roles (
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    role_id INT REFERENCES roles(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT NOW(),
    granted_by INT REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

-- Permissions table
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL
);

-- Role-Permission assignment
CREATE TABLE role_permissions (
    role_id INT REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INT REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Indexes for performance
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_role_permissions_role ON role_permissions(role_id);
```

### Hierarchical RBAC

```python
from typing import Dict, Set

class RoleHierarchy:
    """Implement role inheritance"""

    def __init__(self):
        # Define role hierarchy (child -> parents)
        self.hierarchy: Dict[Role, Set[Role]] = {
            Role.ADMIN: {Role.EDITOR, Role.VIEWER},
            Role.EDITOR: {Role.VIEWER},
            Role.VIEWER: set()
        }

    def get_effective_roles(self, role: Role) -> Set[Role]:
        """Get role and all inherited roles"""
        effective = {role}
        effective.update(self.hierarchy.get(role, set()))
        return effective

    def has_permission(self, user: User, permission: str) -> bool:
        """Check permission considering hierarchy"""
        for user_role in user.roles:
            effective_roles = self.get_effective_roles(user_role)
            for role in effective_roles:
                if permission in ROLE_PERMISSIONS.get(role, set()):
                    return True
        return False

# Usage
hierarchy = RoleHierarchy()
admin = User(1, "admin", {Role.ADMIN})

# Admin inherits EDITOR and VIEWER permissions
assert hierarchy.has_permission(admin, "read")   # From VIEWER
assert hierarchy.has_permission(admin, "write")  # From EDITOR
assert hierarchy.has_permission(admin, "manage_users")  # From ADMIN
```

## Attribute-Based Access Control (ABAC)

### ABAC Implementation

```python
from dataclasses import dataclass
from typing import Any, Dict
from datetime import datetime

@dataclass
class Resource:
    id: int
    type: str
    owner_id: int
    department: str
    classification: str  # public, internal, confidential
    created_at: datetime

@dataclass
class Context:
    ip_address: str
    time: datetime
    location: str

class ABACPolicy:
    """Attribute-based access control"""

    def can_access(self, user: User, action: str, resource: Resource,
                   context: Context) -> bool:
        """Evaluate access based on attributes"""

        # Rule 1: Owners can do anything with their resources
        if user.id == resource.owner_id:
            return True

        # Rule 2: Admins can access everything
        if Role.ADMIN in user.roles:
            return True

        # Rule 3: Department members can read internal resources
        if (action == "read" and
            user.department == resource.department and
            resource.classification in ["public", "internal"]):
            return True

        # Rule 4: Everyone can read public resources
        if action == "read" and resource.classification == "public":
            return True

        # Rule 5: Time-based access (business hours only)
        if context.time.hour < 9 or context.time.hour > 17:
            if resource.classification == "confidential":
                return False

        # Rule 6: Location-based access
        if resource.classification == "confidential":
            if context.location not in AUTHORIZED_LOCATIONS:
                return False

        return False

# Usage
policy = ABACPolicy()

user = User(id=1, username="alice", roles={Role.EDITOR},
            department="engineering")

resource = Resource(
    id=100,
    type="document",
    owner_id=2,
    department="engineering",
    classification="internal",
    created_at=datetime.now()
)

context = Context(
    ip_address="192.168.1.1",
    time=datetime.now(),
    location="office"
)

if policy.can_access(user, "read", resource, context):
    serve_resource(resource)
else:
    raise ForbiddenError("Access denied")
```

## Policy Engines

### Open Policy Agent (OPA)

**Rego policy example**:
```rego
package authz

import future.keywords.if

# Default deny
default allow := false

# Allow admins everything
allow if {
    input.user.roles[_] == "admin"
}

# Allow resource owners
allow if {
    input.user.id == input.resource.owner_id
}

# Allow department members to read internal resources
allow if {
    input.action == "read"
    input.user.department == input.resource.department
    input.resource.classification == "internal"
}

# Allow everyone to read public resources
allow if {
    input.action == "read"
    input.resource.classification == "public"
}
```

**Python integration**:
```python
import requests
import json

class OPAClient:
    def __init__(self, opa_url: str = "http://localhost:8181"):
        self.opa_url = opa_url

    def authorize(self, user: Dict, action: str, resource: Dict) -> bool:
        """Query OPA for authorization decision"""
        policy_path = "authz/allow"
        url = f"{self.opa_url}/v1/data/{policy_path}"

        payload = {
            "input": {
                "user": user,
                "action": action,
                "resource": resource
            }
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        return result.get("result", False)

# Usage
opa = OPAClient()

user_data = {
    "id": 1,
    "username": "alice",
    "roles": ["editor"],
    "department": "engineering"
}

resource_data = {
    "id": 100,
    "type": "document",
    "owner_id": 2,
    "department": "engineering",
    "classification": "internal"
}

if opa.authorize(user_data, "read", resource_data):
    serve_resource(resource_data)
```

### Casbin (Policy Engine)

```python
import casbin

# Model definition (RBAC with domains)
model_config = """
[request_definition]
r = sub, dom, obj, act

[policy_definition]
p = sub, dom, obj, act

[role_definition]
g = _, _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub, r.dom) && r.dom == p.dom && r.obj == p.obj && r.act == p.act
"""

# Policy (CSV format)
policy = """
p, admin, domain1, data1, read
p, admin, domain1, data1, write
p, alice, domain1, data2, read

g, alice, admin, domain1
"""

# Create enforcer
enforcer = casbin.Enforcer("model.conf", "policy.csv")

# Check permissions
if enforcer.enforce("alice", "domain1", "data1", "write"):
    # Alice inherits admin role, can write
    perform_write()

# Add policy at runtime
enforcer.add_policy("bob", "domain1", "data3", "read")

# Add role assignment
enforcer.add_grouping_policy("bob", "editor", "domain1")
```

## Resource-Based Authorization

### Ownership Check

```python
from fastapi import HTTPException, Depends

async def get_current_user() -> User:
    # Extract from JWT, session, etc.
    pass

async def get_post_or_404(post_id: int) -> Post:
    post = await db.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    user: User = Depends(get_current_user),
    post: Post = Depends(get_post_or_404)
):
    # Check ownership
    if post.author_id != user.id and not user.has_role(Role.ADMIN):
        raise HTTPException(status_code=403, detail="Forbidden")

    await db.delete_post(post_id)
    return {"message": "Post deleted"}
```

### Row-Level Security (PostgreSQL)

```sql
-- Enable RLS on table
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own documents
CREATE POLICY user_documents ON documents
    FOR SELECT
    USING (owner_id = current_setting('app.user_id')::int);

-- Policy: Users can update their own documents
CREATE POLICY user_update_documents ON documents
    FOR UPDATE
    USING (owner_id = current_setting('app.user_id')::int);

-- Policy: Admins can see everything
CREATE POLICY admin_all_documents ON documents
    FOR ALL
    USING (current_setting('app.user_role') = 'admin');
```

```python
# Set user context in application
async def set_user_context(user: User):
    await db.execute(f"SET LOCAL app.user_id = {user.id}")
    await db.execute(f"SET LOCAL app.user_role = '{user.role}'")

# Queries automatically filtered by RLS
@app.get("/documents")
async def list_documents(user: User = Depends(get_current_user)):
    await set_user_context(user)

    # RLS automatically filters results
    documents = await db.fetch_all("SELECT * FROM documents")

    return documents
```

## API Authorization Patterns

### Decorator-Based Authorization

```python
from functools import wraps
from flask import request, jsonify

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()

            if not user:
                return jsonify({"error": "Unauthorized"}), 401

            if not user_can(user, permission):
                return jsonify({"error": "Forbidden"}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/admin/users', methods=['GET'])
@require_permission("manage_users")
def list_users():
    users = db.get_all_users()
    return jsonify(users)
```

### Middleware-Based Authorization (FastAPI)

```python
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI()

async def check_permission(
    required_permission: str,
    user: User = Depends(get_current_user)
):
    """Dependency for permission checking"""
    if not user_can(user, required_permission):
        raise HTTPException(status_code=403, detail="Forbidden")
    return user

@app.get("/admin/users")
async def list_users(
    user: User = Depends(lambda: check_permission("manage_users"))
):
    users = await db.get_all_users()
    return users
```

## Multi-Tenant Authorization

### Tenant Isolation

```python
from fastapi import Header, HTTPException

async def get_tenant_id(x_tenant_id: str = Header(...)) -> str:
    """Extract tenant ID from header"""
    tenant = await db.get_tenant(x_tenant_id)
    if not tenant:
        raise HTTPException(status_code=400, detail="Invalid tenant")
    return x_tenant_id

async def check_tenant_access(
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """Verify user has access to tenant"""
    if not user.has_tenant_access(tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to tenant")
    return tenant_id

@app.get("/tenants/{tenant_id}/documents")
async def list_documents(
    tenant_id: str = Depends(check_tenant_access),
    user: User = Depends(get_current_user)
):
    # Query filtered by tenant
    documents = await db.get_documents(tenant_id=tenant_id)
    return documents
```

## Security Best Practices

### Authorization Checklist

**Design**:
- [ ] Principle of least privilege (deny by default)
- [ ] Separate authentication from authorization
- [ ] Use centralized authorization logic
- [ ] Audit all authorization decisions
- [ ] Fail securely (default deny)

**Implementation**:
- [ ] Check authorization on every request
- [ ] Validate on server-side (never trust client)
- [ ] Check both endpoint and resource-level permissions
- [ ] Use parameterized queries to prevent injection
- [ ] Log authorization failures

**Testing**:
- [ ] Test privilege escalation scenarios
- [ ] Test cross-tenant access attempts
- [ ] Test role/permission boundary cases
- [ ] Test with different user contexts
- [ ] Test authorization bypass attempts

## Common Vulnerabilities

### Insecure Direct Object Reference (IDOR)

**Vulnerable code**:
```python
@app.get("/users/{user_id}/profile")
def get_profile(user_id: int):
    # ❌ No authorization check
    profile = db.get_user_profile(user_id)
    return profile
```

**Fixed code**:
```python
@app.get("/users/{user_id}/profile")
def get_profile(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    # ✅ Check authorization
    if user_id != current_user.id and not current_user.is_admin():
        raise HTTPException(status_code=403, detail="Forbidden")

    profile = db.get_user_profile(user_id)
    return profile
```

### Privilege Escalation

**Vulnerable code**:
```python
@app.post("/users/{user_id}/role")
def update_role(user_id: int, role: str):
    # ❌ Any authenticated user can make anyone admin
    db.update_user_role(user_id, role)
```

**Fixed code**:
```python
@app.post("/users/{user_id}/role")
@require_permission("manage_users")
def update_role(
    user_id: int,
    role: str,
    current_user: User = Depends(get_current_user)
):
    # ✅ Only admins can update roles
    # ✅ Prevent self-modification
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify own role")

    db.update_user_role(user_id, role)
```

## Related Skills

- `security-authentication.md` - User identity verification
- `security-input-validation.md` - Validating authorization inputs
- `api-authorization.md` - API-specific authorization patterns
- `database-security.md` - Row-level security and database permissions

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
