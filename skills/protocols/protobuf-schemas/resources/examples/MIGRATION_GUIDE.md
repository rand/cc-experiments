# Protocol Buffer Schema Migration Guide

Comprehensive guide for migrating Protocol Buffer schemas safely while maintaining backward/forward compatibility.

## Table of Contents

1. [Migration Strategy](#migration-strategy)
2. [Breaking vs Non-Breaking Changes](#breaking-vs-non-breaking-changes)
3. [Migration Patterns](#migration-patterns)
4. [Version-by-Version Examples](#version-by-version-examples)
5. [Testing Migrations](#testing-migrations)
6. [Rollback Strategy](#rollback-strategy)
7. [Production Checklist](#production-checklist)

---

## Migration Strategy

### Three-Phase Deployment

The safest approach for schema evolution:

```
Phase 1: Deploy Transitional Version (backward compatible)
  - Add new fields as optional
  - Mark old fields as deprecated
  - Support both old and new patterns

Phase 2: Migrate Data and Clients
  - Update all clients to use new fields
  - Migrate existing data
  - Monitor for deprecated field usage

Phase 3: Clean Up (potentially breaking)
  - Remove deprecated fields (reserved)
  - Drop transitional support code
  - Deploy clean version
```

### Compatibility Modes

**Backward Compatible** (most common):
- New servers can read old client messages
- Safe for server-first deployments
- Add optional fields, new enum values

**Forward Compatible** (less common):
- Old servers can read new client messages
- Safe for client-first deployments
- Never remove fields

**Full Compatible** (ideal):
- Both backward and forward compatible
- Only add optional fields
- Never remove anything

---

## Breaking vs Non-Breaking Changes

### ✅ Non-Breaking Changes

```protobuf
// ✅ Adding optional fields
message User {
  string id = 1;
  string email = 2;
  string name = 3;           // New optional field
}

// ✅ Adding new enum values (at end)
enum Status {
  STATUS_UNSPECIFIED = 0;
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
  STATUS_ARCHIVED = 3;       // New value
}

// ✅ Marking fields deprecated
message User {
  string id = 1;
  string email = 2;
  string old_name = 3 [deprecated = true];
  string display_name = 4;   // Replacement
}

// ✅ Adding new messages/services
message UserProfile {        // New message
  string bio = 1;
}

// ✅ Reserving fields
message User {
  reserved 10, 11, 12;
  reserved "deleted_field", "removed_field";
}
```

### ❌ Breaking Changes

```protobuf
// ❌ Removing fields without reservation
message User {
  string id = 1;
  string email = 2;
  // string name = 3;         // REMOVED - breaks compatibility!
}

// ❌ Changing field types
message User {
  string id = 1;
  int64 user_id = 2;         // Was string, now int64 - BREAKS!
}

// ❌ Changing field numbers
message User {
  string id = 1;
  string email = 3;          // Was 2, now 3 - BREAKS!
}

// ❌ Removing enum values
enum Status {
  STATUS_UNSPECIFIED = 0;
  STATUS_ACTIVE = 1;
  // STATUS_INACTIVE = 2;     // REMOVED - old data becomes invalid!
}

// ❌ Changing required/optional (proto2)
message User {
  required string id = 1;    // Was optional - BREAKS!
}

// ❌ Renaming fields (without json_name)
message User {
  string id = 1;
  string user_email = 2;     // Was 'email' - JSON serialization BREAKS!
}
```

---

## Migration Patterns

### Pattern 1: Adding a Field

**Safe, backward compatible**

```protobuf
// Version 1
message User {
  string id = 1;
  string email = 2;
}

// Version 2 - Add optional field
message User {
  string id = 1;
  string email = 2;
  string phone = 3;          // New optional field
}
```

**Behavior**:
- Old clients: Ignore `phone` field (unknown field)
- New clients: Can read old data (phone will be empty)
- No deployment coordination needed

---

### Pattern 2: Replacing a Field

**Requires three-phase deployment**

```protobuf
// Version 1 (Original)
message User {
  string id = 1;
  string email = 2;
  string name = 3;
}

// Version 2 (Transitional - DEPLOY THIS FIRST)
message User {
  string id = 1;
  string email = 2;
  string name = 3 [deprecated = true];
  string display_name = 4;   // New field

  // Server code: Write to both, read from display_name preferring it
  // Client code: Start writing to display_name, read from both
}

// Version 3 (Final - DEPLOY AFTER ALL CLIENTS UPDATED)
message User {
  string id = 1;
  string email = 2;
  reserved 3;
  reserved "name";
  string display_name = 4;
}
```

**Migration steps**:
1. Deploy v2 servers (support both fields)
2. Migrate existing data (name → display_name)
3. Update all clients to use display_name
4. Monitor: Ensure no clients use deprecated field
5. Deploy v3 (remove deprecated field)

---

### Pattern 3: Changing Field Type

**Breaking change - requires new field**

```protobuf
// Version 1
message User {
  string id = 1;
  string age = 2;            // Oops, should be int32
}

// Version 2 (Correct approach)
message User {
  string id = 1;
  string age = 2 [deprecated = true];
  int32 age_years = 3;       // New field with correct type
}

// Server migration code:
// if (user.age_years == 0 && user.age != "") {
//   user.age_years = parseInt(user.age)
// }
```

**Never do this**:
```protobuf
// ❌ DON'T: Reuse field number with different type
message User {
  string id = 1;
  int32 age = 2;             // Same number, different type - BREAKS!
}
```

---

### Pattern 4: Enum Evolution

**Safe: Add values at end**

```protobuf
// Version 1
enum UserStatus {
  USER_STATUS_UNSPECIFIED = 0;
  USER_STATUS_ACTIVE = 1;
  USER_STATUS_INACTIVE = 2;
}

// Version 2 - Add new values
enum UserStatus {
  USER_STATUS_UNSPECIFIED = 0;
  USER_STATUS_ACTIVE = 1;
  USER_STATUS_INACTIVE = 2;
  USER_STATUS_SUSPENDED = 3;   // New value
  USER_STATUS_DELETED = 4;     // New value
}
```

**Unsafe: Remove values**

```protobuf
// ❌ DON'T: Remove enum values
enum UserStatus {
  USER_STATUS_UNSPECIFIED = 0;
  USER_STATUS_ACTIVE = 1;
  // USER_STATUS_INACTIVE = 2;  // Removed - old data invalid!
}

// ✅ DO: Deprecate and reserve
enum UserStatus {
  USER_STATUS_UNSPECIFIED = 0;
  USER_STATUS_ACTIVE = 1;
  reserved 2;
  reserved "USER_STATUS_INACTIVE";
}
```

---

### Pattern 5: Nested Message Changes

**Safe: Add optional nested message**

```protobuf
// Version 1
message User {
  string id = 1;
  string email = 2;
}

// Version 2
message User {
  string id = 1;
  string email = 2;
  UserProfile profile = 3;   // New nested message
}

message UserProfile {
  string bio = 1;
  string avatar_url = 2;
}
```

---

### Pattern 6: Service Evolution

**Safe: Add new methods**

```protobuf
// Version 1
service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
}

// Version 2
service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
  rpc ListUsers(ListUsersRequest) returns (ListUsersResponse);  // New
  rpc UpdateUser(UpdateUserRequest) returns (UpdateUserResponse);  // New
}
```

**Unsafe: Change method signatures**

```protobuf
// ❌ DON'T: Change request/response types
service UserService {
  // Was: GetUser(GetUserRequest) returns (GetUserResponse)
  rpc GetUser(GetUserRequestV2) returns (GetUserResponseV2);  // BREAKS!
}

// ✅ DO: Add new method
service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
  rpc GetUserV2(GetUserRequestV2) returns (GetUserResponseV2);  // New version
}
```

---

## Version-by-Version Examples

See the example files for concrete evolution:

### V1 → V2 (Non-Breaking)
- `user_service_v1.proto` → `user_service_v2.proto`
- Added optional fields (display_name, role, email_verified)
- Added new enum value (USER_STATUS_BANNED)
- Marked field deprecated (name → display_name)

### V2 → V3 (Breaking with Migration)
- `user_service_v2.proto` → `user_service_v3.proto`
- Removed deprecated field (properly reserved)
- Changed role system (UserRole → Permissions)
- Added nested profile message
- Required coordinated deployment

---

## Testing Migrations

### Compatibility Testing

```python
#!/usr/bin/env python3
"""Test schema compatibility"""

import user_v1_pb2 as v1
import user_v2_pb2 as v2

# Test 1: V1 writer, V2 reader (backward compatibility)
user_v1 = v1.User(id="123", email="test@example.com", name="John")
data = user_v1.SerializeToString()

user_v2 = v2.User()
user_v2.ParseFromString(data)

assert user_v2.id == "123"
assert user_v2.email == "test@example.com"
assert user_v2.name == "John"
assert user_v2.display_name == ""  # New field is empty
print("✅ Backward compatible: V1 → V2")

# Test 2: V2 writer, V1 reader (forward compatibility)
user_v2 = v2.User(
    id="456",
    email="test2@example.com",
    display_name="Jane Doe"
)
data = user_v2.SerializeToString()

user_v1 = v1.User()
user_v1.ParseFromString(data)

assert user_v1.id == "456"
assert user_v1.email == "test2@example.com"
# V1 ignores unknown field (display_name)
print("✅ Forward compatible: V2 → V1")
```

### Testing with Multiple Versions

```bash
#!/bin/bash
# Test all version combinations

# Generate code for all versions
for v in v1 v2 v3; do
  protoc --python_out=. user_service_${v}.proto
done

# Run compatibility tests
python test_v1_v2_compat.py
python test_v2_v3_compat.py
python test_v1_v3_compat.py  # Should fail if breaking changes

# Validate with tools
./scripts/analyze_schema_compatibility.py \
  --baseline user_service_v1.proto \
  --current user_service_v2.proto \
  --mode full

./scripts/analyze_schema_compatibility.py \
  --baseline user_service_v2.proto \
  --current user_service_v3.proto \
  --mode backward
```

---

## Rollback Strategy

### Rollback Scenarios

**Scenario 1: Non-Breaking Change Rollback**
```
V2 deployment failed → Rollback to V1
- Safe: V1 code can read V2 data (ignores new fields)
- No data migration needed
```

**Scenario 2: Breaking Change Rollback**
```
V3 deployment failed → Rollback to V2
- Risk: V2 code may not understand V3 data
- Need database rollback or data migration
- Always test rollback path before deployment!
```

### Rollback Testing

```bash
#!/bin/bash
# Test rollback scenarios

# 1. Deploy V2, generate data
deploy_v2
generate_test_data_v2

# 2. Rollback to V1
rollback_v1

# 3. Verify V1 can read V2 data
test_v1_reads_v2_data || exit 1

# 4. Verify no errors in logs
check_application_logs || exit 1

echo "✅ Rollback test passed"
```

---

## Production Checklist

Before deploying schema changes:

### Pre-Deployment

- [ ] **Analyze compatibility**
  ```bash
  ./scripts/analyze_schema_compatibility.py \
    --baseline prod_version.proto \
    --current new_version.proto \
    --mode backward
  ```

- [ ] **Run validation**
  ```bash
  ./scripts/validate_proto_schemas.py \
    --proto-file new_version.proto
  ```

- [ ] **Generate and test code**
  ```bash
  ./scripts/generate_proto_code.py \
    --proto-file new_version.proto \
    --language python,go \
    --validate
  ```

- [ ] **Review breaking changes**
  - Document all breaking changes
  - Plan migration strategy (3-phase if needed)
  - Communicate to all teams

- [ ] **Test compatibility**
  - Write compatibility tests
  - Test old client → new server
  - Test new client → old server
  - Test rollback scenario

- [ ] **Update documentation**
  - Update CHANGELOG
  - Document migration steps
  - Update API documentation

### Deployment

- [ ] **Phase 1: Deploy transitional version**
  - Supports both old and new patterns
  - Monitor logs for errors
  - Verify backward compatibility

- [ ] **Phase 2: Migrate data and clients**
  - Run data migration scripts
  - Deploy updated clients
  - Monitor deprecated field usage

- [ ] **Phase 3: Deploy final version**
  - Remove deprecated code
  - Clean up database
  - Update monitoring dashboards

### Post-Deployment

- [ ] **Monitor metrics**
  - Deserialization errors
  - Unknown field warnings
  - Application errors

- [ ] **Verify data integrity**
  - Sample data checks
  - Field population rates
  - Data type correctness

- [ ] **Update schema registry**
  - Register new schema version
  - Verify compatibility level
  - Update documentation

---

## Common Pitfalls

### 1. Reusing Field Numbers

**❌ DON'T:**
```protobuf
message User {
  string id = 1;
  // Removed: string email = 2;
  int32 age = 2;  // Reused number 2 - DANGER!
}
```

**Why it's bad**: Old data with email="test@example.com" will be parsed as age, causing corruption.

**✅ DO:**
```protobuf
message User {
  string id = 1;
  reserved 2;
  reserved "email";
  int32 age = 3;  // New number
}
```

### 2. Changing JSON Field Names

**❌ DON'T:**
```protobuf
message User {
  string user_identifier = 1;  // Was 'id'
}
```

**Why it's bad**: JSON serialization uses field names, breaking JSON clients.

**✅ DO:**
```protobuf
message User {
  string user_identifier = 1 [json_name = "id"];  // Keep JSON name
}
```

### 3. Assuming Zero Values

**❌ DON'T:**
```protobuf
enum Status {
  STATUS_ACTIVE = 0;  // Bad: zero should be unspecified
  STATUS_INACTIVE = 1;
}
```

**Why it's bad**: Cannot distinguish between unset and explicitly set to zero.

**✅ DO:**
```protobuf
enum Status {
  STATUS_UNSPECIFIED = 0;
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
}
```

---

## Tools and Resources

### Validation Tools

```bash
# Buf: Modern protobuf tool
buf lint
buf breaking --against '.git#branch=main'

# Custom scripts
./scripts/validate_proto_schemas.py --proto-dir protos
./scripts/analyze_schema_compatibility.py --baseline v1.proto --current v2.proto
```

### Monitoring

Set up alerts for:
- Protobuf deserialization errors
- Unknown field warnings
- Deprecated field usage
- Schema registry rejections

### Documentation

- Keep CHANGELOG.md updated
- Document breaking changes prominently
- Provide migration guides for major changes
- Update API documentation automatically

---

## Summary

**Golden Rules for Safe Schema Evolution:**

1. ✅ Always add fields, never remove (use reserved)
2. ✅ New fields must be optional
3. ✅ Never change field numbers
4. ✅ Never reuse field numbers
5. ✅ Enum zero value = UNSPECIFIED
6. ✅ Test backward compatibility
7. ✅ Use three-phase deployment for breaking changes
8. ✅ Monitor after deployment
9. ✅ Have rollback plan
10. ✅ Communicate changes to all teams

**When in doubt**: Add a new field rather than modifying an existing one.
