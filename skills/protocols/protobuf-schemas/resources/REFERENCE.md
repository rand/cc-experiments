# Protocol Buffers Schemas - Complete Reference

**Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: 3,200+

This comprehensive reference covers all aspects of Protocol Buffers schema design, evolution, code generation, and best practices.

---

## Table of Contents

1. [Fundamentals](#fundamentals)
2. [Proto Syntax](#proto-syntax)
3. [Data Types](#data-types)
4. [Schema Design](#schema-design)
5. [Schema Evolution](#schema-evolution)
6. [Code Generation](#code-generation)
7. [Well-Known Types](#well-known-types)
8. [Schema Registry](#schema-registry)
9. [Performance](#performance)
10. [Advanced Patterns](#advanced-patterns)
11. [Tools and Ecosystem](#tools-and-ecosystem)
12. [Anti-Patterns](#anti-patterns)
13. [Migration Guides](#migration-guides)
14. [Language-Specific Details](#language-specific-details)

---

## Fundamentals

### What are Protocol Buffers?

**Protocol Buffers** (protobuf) is Google's language-neutral, platform-neutral, extensible mechanism for serializing structured data.

**Key characteristics**:
- **Compact**: 3-10x smaller than XML, 1.5-3x smaller than JSON
- **Fast**: 20-100x faster serialization than XML, 3-5x faster than JSON
- **Type-safe**: Schema enforces structure at compile time
- **Extensible**: Add fields without breaking existing clients
- **Multi-language**: Official support for C++, C#, Dart, Go, Java, Kotlin, Objective-C, PHP, Python, Ruby
- **Self-describing**: Schema embedded in generated code

**History**:
- Created at Google in 2001
- Open-sourced in 2008
- Proto2 (2008-2016)
- Proto3 (2016-present, recommended)

### Binary Encoding

Protocol Buffers use a compact binary format based on variable-length encoding.

**Wire format basics**:
```
Message = Field*
Field = Tag + Value
Tag = (field_number << 3) | wire_type
```

**Wire types**:
```
0 = Varint (int32, int64, uint32, uint64, sint32, sint64, bool, enum)
1 = 64-bit (fixed64, sfixed64, double)
2 = Length-delimited (string, bytes, embedded messages, repeated fields)
3 = Start group (deprecated)
4 = End group (deprecated)
5 = 32-bit (fixed32, sfixed32, float)
```

**Example encoding**:
```protobuf
message Test {
  int32 a = 1;
}

// Value: a = 150
// Binary: 08 96 01
// 08 = field number 1, wire type 0 (varint)
// 96 01 = 150 in varint encoding (base 128)
```

**Varint encoding** (variable-length integer):
```
Value 1:   00000001 → 01
Value 150: 10010110 00000001 → 96 01
Value 300: 10101100 00000010 → AC 02
```

- Most significant bit (MSB) = continuation bit
- If MSB = 1, more bytes follow
- Efficient for small numbers (1 byte for 0-127)

**Field number encoding efficiency**:
```
Field 1-15:    1 byte tag (field number + wire type)
Field 16-2047: 2 byte tag
Field 2048+:   3+ byte tag
```

**Why field numbers 1-15 are special**:
- Single byte tag: `(field_number << 3) | wire_type` fits in 7 bits
- Use for frequently set fields (hot path)

### Message Structure

**Anatomy of a .proto file**:
```protobuf
// Version declaration (required)
syntax = "proto3";

// Package namespace
package users.v1;

// Import other proto files
import "google/protobuf/timestamp.proto";
import "common/address.proto";

// Code generation options
option go_package = "github.com/example/users/v1;usersv1";
option java_package = "com.example.users.v1";
option java_multiple_files = true;

// Message definitions
message User {
  string id = 1;
  string email = 2;
  google.protobuf.Timestamp created_at = 3;
  Address address = 4;
  Status status = 5;
}

// Enum definitions
enum Status {
  STATUS_UNSPECIFIED = 0;
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
}

// Service definitions (gRPC)
service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
  rpc ListUsers(ListUsersRequest) returns (stream User);
}

message GetUserRequest {
  string id = 1;
}

message GetUserResponse {
  User user = 1;
}
```

---

## Proto Syntax

### Proto3 vs Proto2

**Proto3** is the current recommended version with simpler syntax and better performance.

**Proto3 syntax**:
```protobuf
syntax = "proto3";

message User {
  // All fields are optional by default
  string id = 1;
  string name = 2;
  int32 age = 3;
  repeated string tags = 4;
}
```

**Proto2 syntax** (legacy):
```protobuf
syntax = "proto2";

message User {
  required string id = 1;      // Must be set
  optional string name = 2;    // May be omitted
  optional int32 age = 3 [default = 0];
  repeated string tags = 4;
}
```

**Key differences**:

| Feature | Proto2 | Proto3 |
|---------|--------|--------|
| Field presence | `required`, `optional`, `repeated` | All optional (no keyword) |
| Default values | Custom defaults allowed | Type defaults only |
| Unknown fields | Preserved | Preserved (as of 3.5) |
| Enum defaults | Any value can be first | First value must be 0 |
| Groups | Supported (deprecated) | Not supported |
| Extensions | Supported | Not supported |
| JSON mapping | Basic | Canonical mapping |
| Performance | Slower | Faster |

**Proto3 advantages**:
- Simpler syntax (less boilerplate)
- Better performance (10-20% faster)
- Cleaner JSON mapping
- Better forward compatibility
- Easier to learn

**Proto2 advantages**:
- Explicit field presence detection
- Custom default values
- Extensions for third-party additions
- Required fields (validation)

**Migration recommendation**: Use Proto3 for new projects. Migrate Proto2 to Proto3 gradually.

### Field Rules

**Proto3 field modifiers**:
```protobuf
message Example {
  // Singular field (default)
  string name = 1;

  // Repeated field (list/array)
  repeated string tags = 2;

  // Map field (dictionary/hash map)
  map<string, int32> scores = 3;

  // Optional field (explicit presence, proto3.15+)
  optional string nickname = 4;

  // Oneof (union type)
  oneof test_oneof {
    string name_field = 5;
    int32 id_field = 6;
  }
}
```

**Proto2 field modifiers**:
```protobuf
message Example {
  required string id = 1;           // Must be set
  optional string name = 2;         // May be omitted
  repeated string tags = 3;         // List (0 or more)
  optional int32 age = 4 [default = 0];  // Custom default
}
```

### Comments and Documentation

**Comment styles**:
```protobuf
// Single-line comment

/*
 * Multi-line comment
 * Used for detailed documentation
 */

/**
 * JavaDoc-style comment
 * Extracted by documentation tools
 */
message User {
  // Unique identifier for the user
  string id = 1;

  // User's email address (must be valid email format)
  string email = 2;
}
```

**Best practices**:
- Document all public messages and services
- Explain non-obvious field meanings
- Document constraints and validation rules
- Include examples for complex fields

---

## Data Types

### Scalar Types

**Integer types**:
```protobuf
message IntegerExample {
  // Signed integers (can be negative)
  int32 small_int = 1;    // -2^31 to 2^31-1
  int64 large_int = 2;    // -2^63 to 2^63-1

  // Unsigned integers (non-negative)
  uint32 small_uint = 3;  // 0 to 2^32-1
  uint64 large_uint = 4;  // 0 to 2^64-1

  // Signed with efficient negative encoding
  sint32 delta_32 = 5;    // Uses ZigZag encoding
  sint64 delta_64 = 6;    // Efficient for negatives

  // Fixed-width (always 4 or 8 bytes)
  fixed32 fixed_32 = 7;   // More efficient if values often > 2^28
  fixed64 fixed_64 = 8;   // More efficient if values often > 2^56
  sfixed32 sfixed_32 = 9;  // Signed fixed32
  sfixed64 sfixed_64 = 10; // Signed fixed64
}
```

**When to use each integer type**:
- `int32`/`int64`: Default choice for signed integers
- `uint32`/`uint64`: Non-negative values
- `sint32`/`sint64`: Frequently negative values (ZigZag encoding)
- `fixed32`/`fixed64`: Large values (> 2^28 or > 2^56)
- `sfixed32`/`sfixed64`: Signed large values

**Floating-point types**:
```protobuf
message FloatExample {
  float price = 1;        // 32-bit float
  double latitude = 2;    // 64-bit double
  double longitude = 3;   // 64-bit double
}
```

**Boolean type**:
```protobuf
message BoolExample {
  bool is_active = 1;     // true or false
  bool is_verified = 2;
}
```

**String and bytes**:
```protobuf
message StringExample {
  string name = 1;        // UTF-8 or ASCII (arbitrary text)
  bytes data = 2;         // Arbitrary byte sequence (binary data)
  bytes image = 3;        // Binary data (images, files, etc.)
}
```

**String vs bytes**:
- `string`: Text data, must be valid UTF-8
- `bytes`: Binary data, no UTF-8 validation

### Repeated Fields (Lists/Arrays)

**Basic repeated fields**:
```protobuf
message RepeatedExample {
  repeated string tags = 1;           // List of strings
  repeated int32 numbers = 2;         // List of integers
  repeated User users = 3;            // List of messages
}
```

**Packed encoding** (more efficient for numeric types):
```protobuf
message PackedExample {
  // Proto3: Packed by default for numeric types
  repeated int32 values = 1;          // Packed automatically

  // Proto2: Explicit packed option
  repeated int32 values = 2 [packed = true];

  // Unpacked (each value with separate tag)
  repeated int32 values = 3 [packed = false];
}
```

**Packed vs unpacked encoding**:
```
Unpacked: 08 01 08 02 08 03 (tag + value for each)
Packed:   0A 03 01 02 03    (tag + length + values)
```

**Packed encoding is more efficient** for numeric types (int32, int64, uint32, uint64, sint32, sint64, fixed32, fixed64, sfixed32, sfixed64, float, double, bool, enum).

### Map Fields

**Basic map syntax**:
```protobuf
message MapExample {
  map<string, string> attributes = 1;    // String → String
  map<string, int32> scores = 2;         // String → Int
  map<int32, User> users = 3;            // Int → Message
  map<string, Address> addresses = 4;    // String → Message
}
```

**Map key types** (must be scalar, except):
- ❌ Cannot use: `float`, `double`, `bytes`
- ✅ Can use: `int32`, `int64`, `uint32`, `uint64`, `sint32`, `sint64`, `fixed32`, `fixed64`, `sfixed32`, `sfixed64`, `bool`, `string`

**Map value types**: Any type (scalar or message)

**Map implementation** (equivalent to):
```protobuf
message MapFieldEntry {
  key_type key = 1;
  value_type value = 2;
}

repeated MapFieldEntry map = N;
```

**Map characteristics**:
- Unordered (iteration order undefined)
- No duplicate keys
- Cannot be `repeated`

### Oneof (Union Types)

**Basic oneof**:
```protobuf
message SearchRequest {
  oneof query {
    string text_query = 1;
    int32 id_query = 2;
    bool all_query = 3;
  }
}
```

**Behavior**:
- Only one field can be set at a time
- Setting a field clears all other fields in the oneof
- More memory efficient (union storage)

**Usage**:
```python
# Python
request = SearchRequest()
request.text_query = "hello"  # Sets text_query
request.id_query = 123        # Clears text_query, sets id_query

# Check which field is set
if request.WhichOneof('query') == 'text_query':
    print(request.text_query)
```

**Oneof with nested messages**:
```protobuf
message Payment {
  oneof payment_method {
    CreditCard credit_card = 1;
    PayPal paypal = 2;
    BankTransfer bank_transfer = 3;
  }

  message CreditCard {
    string card_number = 1;
    string cvv = 2;
  }

  message PayPal {
    string email = 1;
  }

  message BankTransfer {
    string account_number = 1;
    string routing_number = 2;
  }
}
```

**Oneof evolution**:
- ✅ Add new fields to oneof
- ✅ Remove fields (mark as reserved)
- ❌ Move fields in/out of oneof (breaks compatibility)

### Enums

**Basic enum**:
```protobuf
enum Status {
  STATUS_UNSPECIFIED = 0;  // Always define zero value
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
  STATUS_PENDING = 3;
}

message User {
  Status status = 1;
}
```

**Enum rules (Proto3)**:
- First value **must be 0** (default value)
- Use `_UNSPECIFIED` suffix for zero value
- Values must be unique within enum

**Enum with aliases**:
```protobuf
enum Status {
  option allow_alias = true;  // Enable aliases
  STATUS_UNSPECIFIED = 0;
  STATUS_ACTIVE = 1;
  STATUS_RUNNING = 1;         // Alias for ACTIVE
  STATUS_INACTIVE = 2;
}
```

**Enum prefixing** (avoid name collisions):
```protobuf
// Bad: No prefix
enum Status {
  UNSPECIFIED = 0;
  ACTIVE = 1;
  INACTIVE = 2;
}

// Good: Prefix with enum name
enum Status {
  STATUS_UNSPECIFIED = 0;
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
}
```

**Nested enums**:
```protobuf
message User {
  enum Status {
    STATUS_UNSPECIFIED = 0;
    STATUS_ACTIVE = 1;
    STATUS_INACTIVE = 2;
  }

  Status status = 1;
}

// Usage: User.Status or User.STATUS_ACTIVE
```

**Enum evolution**:
- ✅ Add new values
- ✅ Remove values (mark as reserved)
- ❌ Change value numbers (breaks wire format)
- ❌ Change zero value

**Reserved enum values**:
```protobuf
enum Status {
  reserved 5, 8 to 10;                    // Reserved numbers
  reserved "OLD_STATUS", "DEPRECATED";    // Reserved names

  STATUS_UNSPECIFIED = 0;
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
}
```

### Nested Messages

**Basic nesting**:
```protobuf
message User {
  string id = 1;
  Address address = 2;

  // Nested message
  message Address {
    string street = 1;
    string city = 2;
    string postal_code = 3;
    string country = 4;
  }
}

// Usage: User.Address
```

**When to nest**:
- Message only used within parent message
- Tight coupling between messages
- Logical grouping (e.g., User.Address)

**When not to nest**:
- Message used in multiple places
- Message is a domain entity
- Potential for reuse

**Multiple levels of nesting**:
```protobuf
message Company {
  string name = 1;

  message Department {
    string name = 1;

    message Employee {
      string id = 1;
      string name = 2;
    }

    repeated Employee employees = 2;
  }

  repeated Department departments = 2;
}

// Usage: Company.Department.Employee
```

---

## Schema Design

### Naming Conventions

**File names**:
```
user.proto           // Singular, lowercase
user_service.proto   // snake_case
order_event.proto
```

**Package names**:
```protobuf
package users.v1;            // Lowercase, versioned
package payments.v2;
package com.example.users;   // Reverse domain
```

**Message names**:
```protobuf
message User { }             // PascalCase
message UserProfile { }
message OrderEvent { }
```

**Field names**:
```protobuf
message User {
  string user_id = 1;        // snake_case
  string first_name = 2;
  int32 age_years = 3;
}
```

**Enum names**:
```protobuf
enum OrderStatus {           // PascalCase
  ORDER_STATUS_UNSPECIFIED = 0;  // PREFIX_UPPERCASE
  ORDER_STATUS_PENDING = 1;
  ORDER_STATUS_CONFIRMED = 2;
}
```

**Service names**:
```protobuf
service UserService { }      // PascalCase with "Service" suffix
service PaymentService { }
```

**RPC method names**:
```protobuf
service UserService {
  rpc GetUser(...) returns (...);        // PascalCase, verb prefix
  rpc ListUsers(...) returns (...);
  rpc CreateUser(...) returns (...);
  rpc UpdateUser(...) returns (...);
  rpc DeleteUser(...) returns (...);
}
```

### Field Numbering

**Field number ranges**:
```
1-15:         Single byte tag (use for frequent fields)
16-2047:      Two byte tag (use for less frequent fields)
2048-536870911: Three+ byte tag (avoid if possible)
19000-19999:  Reserved by Protocol Buffers
```

**Best practices**:
```protobuf
message User {
  // Hot fields (frequently set): 1-15
  string id = 1;
  string email = 2;
  string name = 3;

  // Cold fields (rarely set): 16+
  string middle_name = 16;
  string nickname = 17;
  int32 login_count = 18;
}
```

**Field number allocation strategy**:
1. Assign 1-15 to most frequently used fields
2. Leave gaps for future hot fields (e.g., 1, 2, 3, 5, 6, 8...)
3. Use 16-2047 for less frequent fields
4. Reserve deleted field numbers

**Reserved field numbers**:
```protobuf
message User {
  reserved 5, 8 to 10, 15;              // Reserved numbers
  reserved "old_field", "deprecated";   // Reserved names

  string id = 1;
  string name = 2;
  // Field 5 cannot be reused (breaking change)
}
```

**Why reserve field numbers**:
- Prevent accidental reuse of deleted field numbers
- Maintain backward compatibility
- Prevent wire format corruption

### Versioning Strategies

**Package versioning** (recommended):
```protobuf
// v1
package users.v1;

message User {
  string id = 1;
  string name = 2;
}

// v2
package users.v2;

message User {
  string id = 1;
  string full_name = 2;  // Renamed from 'name'
  string email = 3;      // New field
}
```

**File versioning**:
```
users_v1.proto
users_v2.proto
users_v3.proto
```

**Semantic versioning**:
```protobuf
package users.v2_1;  // Version 2.1
```

**When to increment version**:
- Breaking changes (requires new package version)
- Major feature additions (may use new package version)
- Minor additions/deprecations (can keep same version)

### Request/Response Patterns

**Standard RPC pattern**:
```protobuf
service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
}

message GetUserRequest {
  string id = 1;
}

message GetUserResponse {
  User user = 1;
}
```

**Why dedicated request/response messages**:
- ✅ Extensibility (add fields without breaking signature)
- ✅ Backward compatibility
- ✅ Clear intent
- ❌ Don't use primitives directly: `rpc GetUser(string) returns (User);`

**List/pagination pattern**:
```protobuf
message ListUsersRequest {
  int32 page_size = 1;      // Max results per page
  string page_token = 2;    // Token from previous response
  string filter = 3;        // Optional filter
}

message ListUsersResponse {
  repeated User users = 1;
  string next_page_token = 2;  // Token for next page
  int32 total_size = 3;        // Total count (optional)
}
```

**Error handling pattern**:
```protobuf
message GetUserResponse {
  oneof result {
    User user = 1;
    Error error = 2;
  }
}

message Error {
  int32 code = 1;
  string message = 2;
  repeated ErrorDetail details = 3;
}

message ErrorDetail {
  string field = 1;
  string description = 2;
}
```

**Batch operations**:
```protobuf
message BatchGetUsersRequest {
  repeated string ids = 1;
}

message BatchGetUsersResponse {
  map<string, User> users = 1;  // ID → User
  repeated string not_found = 2;
}
```

### Options and Custom Options

**Standard options**:
```protobuf
// File-level options
syntax = "proto3";
option go_package = "github.com/example/users/v1;usersv1";
option java_package = "com.example.users.v1";
option java_outer_classname = "UserProto";
option java_multiple_files = true;
option csharp_namespace = "Example.Users.V1";
option objc_class_prefix = "USR";
option php_namespace = "Example\\Users\\V1";

// Message-level options
message User {
  option deprecated = true;  // Mark message as deprecated
}

// Field-level options
message User {
  string name = 1 [deprecated = true];  // Deprecate field
  repeated int32 values = 2 [packed = true];  // Force packed encoding
}

// Enum-level options
enum Status {
  option allow_alias = true;  // Allow enum value aliases
  STATUS_ACTIVE = 1;
  STATUS_RUNNING = 1;  // Alias
}

// Service-level options
service UserService {
  option deprecated = true;
}

// Method-level options
service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse) {
    option deprecated = true;
  }
}
```

**Custom options**:
```protobuf
import "google/protobuf/descriptor.proto";

extend google.protobuf.MessageOptions {
  string my_option = 51234;
}

message User {
  option (my_option) = "custom_value";
}
```

---

## Schema Evolution

### Backward Compatibility

**Backward compatibility**: Old clients can read new data.

**Safe changes (backward compatible)**:
- ✅ Add new fields
- ✅ Delete fields (mark as reserved)
- ✅ Add new enum values
- ✅ Add new messages
- ✅ Add new services/methods

**Breaking changes (not backward compatible)**:
- ❌ Change field number
- ❌ Change field type
- ❌ Change field name (affects JSON, not binary)
- ❌ Change repeated ↔ singular
- ❌ Reuse deleted field numbers
- ❌ Change oneof membership
- ❌ Remove or rename service/method

**Example: Adding fields (safe)**:
```protobuf
// V1
message User {
  string id = 1;
  string name = 2;
}

// V2 (backward compatible)
message User {
  string id = 1;
  string name = 2;
  string email = 3;      // New field (old clients ignore)
  repeated string tags = 4;
}
```

**Old client behavior**:
- Reads V2 message
- Ignores unknown fields (email, tags)
- Processes id and name normally

**Example: Deleting fields (safe)**:
```protobuf
// V1
message User {
  string id = 1;
  string name = 2;
  string old_field = 3;  // To be deleted
}

// V2 (backward compatible)
message User {
  reserved 3;            // Reserve deleted field number
  reserved "old_field";  // Reserve deleted field name

  string id = 1;
  string name = 2;
}
```

**Old client behavior**:
- Sends V1 message with old_field
- New server ignores old_field (reserved)
- Processes id and name normally

### Forward Compatibility

**Forward compatibility**: New clients can read old data.

**Safe changes (forward compatible)**:
- ✅ Add new fields with defaults
- ✅ Delete fields
- ✅ Add new enum values (if client handles unknown values)

**Breaking changes (not forward compatible)**:
- ❌ Remove default values (proto2)
- ❌ Change field types
- ❌ Make field required (proto2)

**Example: New client reading old data**:
```protobuf
// V2
message User {
  string id = 1;
  string name = 2;
  string email = 3;      // New field
}
```

**New client behavior**:
- Reads V1 message (missing email field)
- email field has default value (empty string)
- Processes normally

### Type Changes

**Safe type changes** (compatible encodings):
```protobuf
// These types can be changed without breaking wire format:
int32 ↔ uint32 ↔ int64 ↔ uint64     // All use varint encoding
sint32 ↔ sint64                      // ZigZag encoding
fixed32 ↔ sfixed32                   // 32-bit fixed
fixed64 ↔ sfixed64                   // 64-bit fixed
string ↔ bytes                       // Length-delimited
```

**Example**:
```protobuf
// V1
message User {
  int32 age = 1;
}

// V2 (safe: int32 → int64)
message User {
  int64 age = 1;  // Wire format compatible
}
```

**Unsafe type changes**:
```
int32 → string  ❌ (different wire types)
int32 → float   ❌ (different wire types)
string → int32  ❌ (different wire types)
repeated → singular  ❌ (breaks structure)
```

### Repeated ↔ Singular Changes

**Changing repeated to singular** (UNSAFE):
```protobuf
// V1
message User {
  repeated string emails = 1;  // Multiple emails
}

// V2 (BREAKING)
message User {
  string email = 1;  // Single email ❌
}
```

**Why breaking**:
- V1 client sends multiple values
- V2 server expects single value
- Data loss or corruption

**Safe alternatives**:
1. Add new singular field, deprecate repeated:
```protobuf
message User {
  repeated string emails = 1 [deprecated = true];
  string primary_email = 2;  // New singular field
}
```

2. Use oneof for optional repeated:
```protobuf
message User {
  oneof email_field {
    string single_email = 1;
    EmailList multiple_emails = 2;
  }
}

message EmailList {
  repeated string emails = 1;
}
```

### Enum Evolution

**Adding enum values (safe)**:
```protobuf
// V1
enum Status {
  STATUS_UNSPECIFIED = 0;
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
}

// V2 (backward compatible)
enum Status {
  STATUS_UNSPECIFIED = 0;
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
  STATUS_PENDING = 3;      // New value
  STATUS_ARCHIVED = 4;     // New value
}
```

**Old client behavior**:
- Receives new enum value (e.g., STATUS_PENDING)
- Does not recognize value
- Treats as unknown (proto3: value preserved, proto2: may default to 0)

**Removing enum values**:
```protobuf
// V1
enum Status {
  STATUS_UNSPECIFIED = 0;
  STATUS_ACTIVE = 1;
  STATUS_OLD = 2;          // To be removed
  STATUS_INACTIVE = 3;
}

// V2
enum Status {
  reserved 2;              // Reserve deleted value
  reserved "STATUS_OLD";

  STATUS_UNSPECIFIED = 0;
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 3;
}
```

**Changing enum zero value (BREAKING)**:
```protobuf
// V1
enum Status {
  STATUS_ACTIVE = 0;       // Zero value
  STATUS_INACTIVE = 1;
}

// V2 (BREAKING) ❌
enum Status {
  STATUS_UNSPECIFIED = 0;  // Changed zero value
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
}
```

**Why breaking**: Default value changes from ACTIVE to UNSPECIFIED.

### Deprecation

**Deprecating fields**:
```protobuf
message User {
  string id = 1;
  string name = 2 [deprecated = true];      // Old field
  string full_name = 3;                     // Replacement
}
```

**Deprecation workflow**:
1. Add new field with improved design
2. Mark old field as deprecated
3. Update clients to use new field
4. Monitor old field usage
5. Remove old field when usage drops to zero
6. Mark field number as reserved

**Deprecating messages**:
```protobuf
message OldUser {
  option deprecated = true;
}

message User {
  // New improved message
}
```

**Deprecating services/methods**:
```protobuf
service UserService {
  rpc GetUserOld(GetUserRequest) returns (GetUserResponse) {
    option deprecated = true;
  }
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
}
```

---

## Code Generation

### protoc (Protocol Compiler)

**Installation**:
```bash
# macOS
brew install protobuf

# Ubuntu/Debian
apt-get install protobuf-compiler

# Windows
choco install protoc

# Verify
protoc --version  # Should show libprotoc 3.x.x or later
```

**Basic usage**:
```bash
# Generate code for single language
protoc --python_out=. user.proto

# Generate for multiple languages
protoc --python_out=./gen/python \
       --go_out=./gen/go \
       --java_out=./gen/java \
       user.proto

# With imports (search path)
protoc -I./protos \
       -I./third_party \
       --python_out=./gen \
       protos/user.proto
```

**Common flags**:
```bash
-I, --proto_path=PATH    # Import search path
--python_out=DIR         # Python output
--go_out=DIR            # Go output
--java_out=DIR          # Java output
--cpp_out=DIR           # C++ output
--csharp_out=DIR        # C# output
--ruby_out=DIR          # Ruby output
--php_out=DIR           # PHP output
--descriptor_set_out=FILE  # Binary descriptor
```

### Language-Specific Code Generation

#### Python

**Generate code**:
```bash
python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  user.proto
```

**Output**:
- `user_pb2.py`: Message classes
- `user_pb2_grpc.py`: Service stubs (if services defined)

**Usage**:
```python
import user_pb2

# Create message
user = user_pb2.User()
user.id = "123"
user.name = "Alice"
user.email = "alice@example.com"

# Serialize to bytes
data = user.SerializeToString()

# Deserialize from bytes
user2 = user_pb2.User()
user2.ParseFromString(data)

# Set repeated fields
user.tags.append("python")
user.tags.append("protobuf")

# Set map fields
user.attributes["key1"] = "value1"

# Check if field is set
user.HasField("email")  # proto3: Only for optional/oneof

# Clear field
user.ClearField("email")

# To dict (not recommended for production)
from google.protobuf.json_format import MessageToDict
user_dict = MessageToDict(user)

# From dict
from google.protobuf.json_format import ParseDict
user = ParseDict({"id": "123", "name": "Alice"}, user_pb2.User())
```

**Type hints**:
```python
from user_pb2 import User

def process_user(user: User) -> None:
    print(user.name)
```

#### Go

**Generate code**:
```bash
# Install plugins
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Generate
protoc --go_out=. --go_opt=paths=source_relative \
       --go-grpc_out=. --go-grpc_opt=paths=source_relative \
       user.proto
```

**Output**:
- `user.pb.go`: Message types
- `user_grpc.pb.go`: Service interfaces

**Usage**:
```go
import pb "github.com/example/protos/users/v1"

// Create message
user := &pb.User{
    Id:    "123",
    Name:  "Alice",
    Email: "alice@example.com",
}

// Serialize
data, err := proto.Marshal(user)
if err != nil {
    log.Fatal(err)
}

// Deserialize
user2 := &pb.User{}
err = proto.Unmarshal(data, user2)
if err != nil {
    log.Fatal(err)
}

// Repeated fields
user.Tags = []string{"go", "protobuf"}

// Map fields
user.Attributes = map[string]string{
    "key1": "value1",
}

// Clone
user3 := proto.Clone(user).(*pb.User)

// Equal
if proto.Equal(user, user2) {
    fmt.Println("Equal")
}
```

#### Java

**Generate code**:
```bash
protoc --java_out=src/main/java user.proto
```

**Maven plugin**:
```xml
<plugin>
    <groupId>org.xolstice.maven.plugins</groupId>
    <artifactId>protobuf-maven-plugin</artifactId>
    <version>0.6.1</version>
    <configuration>
        <protocArtifact>com.google.protobuf:protoc:3.19.0:exe:${os.detected.classifier}</protocArtifact>
    </configuration>
    <executions>
        <execution>
            <goals>
                <goal>compile</goal>
            </goals>
        </execution>
    </executions>
</plugin>
```

**Usage**:
```java
import com.example.UserProto.User;

// Create message (builder pattern)
User user = User.newBuilder()
    .setId("123")
    .setName("Alice")
    .setEmail("alice@example.com")
    .addTags("java")
    .addTags("protobuf")
    .putAttributes("key1", "value1")
    .build();

// Serialize
byte[] data = user.toByteArray();

// Deserialize
User user2 = User.parseFrom(data);

// Modify (creates new instance)
User user3 = user.toBuilder()
    .setName("Bob")
    .build();

// Check field presence
if (user.hasEmail()) {
    System.out.println(user.getEmail());
}

// Default values
User empty = User.getDefaultInstance();
```

#### TypeScript

**Generate code**:
```bash
# Install plugins
npm install -D grpc-tools protoc-gen-ts

# Generate
protoc --ts_out=./gen --grpc-web_out=import_style=typescript,mode=grpcwebtext:./gen user.proto
```

**Usage**:
```typescript
import { User } from './gen/user_pb';

// Create message
const user = new User();
user.setId('123');
user.setName('Alice');
user.setEmail('alice@example.com');

// Repeated fields
user.setTagsList(['typescript', 'protobuf']);
user.addTags('grpc');

// Map fields
const attrs = user.getAttributesMap();
attrs.set('key1', 'value1');

// Serialize
const bytes = user.serializeBinary();

// Deserialize
const user2 = User.deserializeBinary(bytes);

// To object
const obj = user.toObject();

// From object
const user3 = new User();
user3.setId(obj.id);
user3.setName(obj.name);
```

#### C++

**Generate code**:
```bash
protoc --cpp_out=. user.proto
```

**Output**:
- `user.pb.h`: Header file
- `user.pb.cc`: Implementation

**Usage**:
```cpp
#include "user.pb.h"

// Create message
User user;
user.set_id("123");
user.set_name("Alice");
user.set_email("alice@example.com");

// Repeated fields
user.add_tags("cpp");
user.add_tags("protobuf");

// Map fields
(*user.mutable_attributes())["key1"] = "value1";

// Serialize
std::string data;
user.SerializeToString(&data);

// Deserialize
User user2;
user2.ParseFromString(data);

// Check field presence
if (user.has_email()) {
    std::cout << user.email() << std::endl;
}

// Clear field
user.clear_email();

// Copy
User user3(user);  // Copy constructor
```

### Buf (Modern Protobuf Tool)

**Why Buf**:
- Faster builds (parallel compilation)
- Built-in linting and breaking change detection
- Simplified dependency management
- Better error messages
- Modern workflow (replacing protoc for many teams)

**Installation**:
```bash
# macOS
brew install bufbuild/buf/buf

# Linux
curl -sSL https://github.com/bufbuild/buf/releases/download/v1.9.0/buf-$(uname -s)-$(uname -m) \
  -o /usr/local/bin/buf
chmod +x /usr/local/bin/buf

# Verify
buf --version
```

**buf.yaml** (module configuration):
```yaml
version: v1
name: buf.build/example/users
breaking:
  use:
    - FILE
lint:
  use:
    - DEFAULT
  except:
    - PACKAGE_VERSION_SUFFIX
  ignore:
    - protos/legacy
deps:
  - buf.build/googleapis/googleapis
```

**buf.gen.yaml** (code generation):
```yaml
version: v1
managed:
  enabled: true
  go_package_prefix:
    default: github.com/example/gen/go
plugins:
  - name: go
    out: gen/go
    opt: paths=source_relative
  - name: go-grpc
    out: gen/go
    opt: paths=source_relative
  - name: python
    out: gen/python
  - name: python-grpc
    out: gen/python
```

**buf.lock** (dependency lock):
```yaml
# Auto-generated
version: v1
deps:
  - remote: buf.build
    owner: googleapis
    repository: googleapis
    commit: 62f35d8aed1149c291d606d958a7ce32
```

**Common buf commands**:
```bash
# Initialize
buf mod init

# Lint schemas
buf lint

# Format schemas
buf format -w

# Generate code
buf generate

# Breaking change detection
buf breaking --against .git#branch=main

# Build (compile to descriptor)
buf build -o image.bin

# Push to Buf Schema Registry
buf push
```

**Linting rules**:
```yaml
lint:
  use:
    - DEFAULT          # Standard rules
    - COMMENTS         # Require comments
    - FILE_LOWER_SNAKE_CASE
    - PACKAGE_DEFINED
    - PACKAGE_VERSION_SUFFIX
  enum_zero_value_suffix: _UNSPECIFIED
  rpc_allow_google_protobuf_empty_requests: false
  rpc_allow_google_protobuf_empty_responses: false
  service_suffix: Service
```

---

## Well-Known Types

Protocol Buffers provides common types in `google/protobuf/*`.

### Timestamp

**Definition**:
```protobuf
import "google/protobuf/timestamp.proto";

message Event {
  string id = 1;
  google.protobuf.Timestamp created_at = 2;
  google.protobuf.Timestamp updated_at = 3;
}
```

**Structure**:
```protobuf
message Timestamp {
  int64 seconds = 1;   // Seconds since Unix epoch
  int32 nanos = 2;     // Nanoseconds (0-999,999,999)
}
```

**Usage (Python)**:
```python
from google.protobuf.timestamp_pb2 import Timestamp
import time

# Create timestamp (now)
timestamp = Timestamp()
timestamp.GetCurrentTime()

# Create from seconds
timestamp.FromSeconds(int(time.time()))

# Create from datetime
from datetime import datetime
timestamp.FromDatetime(datetime.now())

# Convert to datetime
dt = timestamp.ToDatetime()

# Convert to seconds
seconds = timestamp.ToSeconds()
```

**Usage (Go)**:
```go
import (
    "time"
    "google.golang.org/protobuf/types/known/timestamppb"
)

// Create timestamp (now)
ts := timestamppb.Now()

// Create from time.Time
t := time.Now()
ts = timestamppb.New(t)

// Convert to time.Time
t2 := ts.AsTime()
```

### Duration

**Definition**:
```protobuf
import "google/protobuf/duration.proto";

message Config {
  google.protobuf.Duration timeout = 1;
  google.protobuf.Duration retry_delay = 2;
}
```

**Structure**:
```protobuf
message Duration {
  int64 seconds = 1;   // Signed seconds
  int32 nanos = 2;     // Signed nanoseconds
}
```

**Usage (Python)**:
```python
from google.protobuf.duration_pb2 import Duration

# Create duration (5 seconds)
duration = Duration(seconds=5)

# Create duration (5.5 seconds)
duration = Duration(seconds=5, nanos=500000000)

# From timedelta
from datetime import timedelta
duration.FromTimedelta(timedelta(seconds=5, milliseconds=500))

# To timedelta
td = duration.ToTimedelta()
```

**Usage (Go)**:
```go
import (
    "time"
    "google.golang.org/protobuf/types/known/durationpb"
)

// Create duration
d := durationpb.New(5 * time.Second)

// Convert to time.Duration
dur := d.AsDuration()
```

### Any

**Definition**:
```protobuf
import "google/protobuf/any.proto";

message Event {
  string id = 1;
  google.protobuf.Any payload = 2;  // Can hold any message type
}
```

**Structure**:
```protobuf
message Any {
  string type_url = 1;  // Type identifier (e.g., "type.googleapis.com/User")
  bytes value = 2;      // Serialized message
}
```

**Usage (Python)**:
```python
from google.protobuf.any_pb2 import Any
from user_pb2 import User

# Pack message into Any
user = User(id="123", name="Alice")
any_msg = Any()
any_msg.Pack(user)

# Unpack from Any
if any_msg.Is(User.DESCRIPTOR):
    user2 = User()
    any_msg.Unpack(user2)
    print(user2.name)

# Type URL
print(any_msg.type_url)  # "type.googleapis.com/User"
```

**Usage (Go)**:
```go
import (
    "google.golang.org/protobuf/types/known/anypb"
)

// Pack message
user := &pb.User{Id: "123", Name: "Alice"}
anyMsg, err := anypb.New(user)

// Unpack
user2 := &pb.User{}
if err := anyMsg.UnmarshalTo(user2); err == nil {
    fmt.Println(user2.Name)
}

// Check type
if anyMsg.MessageIs(&pb.User{}) {
    // Is User type
}
```

### Empty

**Definition**:
```protobuf
import "google/protobuf/empty.proto";

service UserService {
  rpc DeleteUser(DeleteUserRequest) returns (google.protobuf.Empty);
}
```

**Usage**: Represents empty message (no fields).

### FieldMask

**Definition**:
```protobuf
import "google/protobuf/field_mask.proto";

message UpdateUserRequest {
  User user = 1;
  google.protobuf.FieldMask update_mask = 2;  // Fields to update
}
```

**Structure**:
```protobuf
message FieldMask {
  repeated string paths = 1;  // Field paths (e.g., "name", "address.city")
}
```

**Usage (Python)**:
```python
from google.protobuf.field_mask_pb2 import FieldMask

# Create field mask
mask = FieldMask(paths=["name", "email"])

# Apply mask (update only specified fields)
from google.protobuf import field_mask
field_mask.merge(mask, src_user, dst_user)
```

**Usage (Go)**:
```go
import (
    "google.golang.org/protobuf/types/known/fieldmaskpb"
)

// Create field mask
mask := &fieldmaskpb.FieldMask{
    Paths: []string{"name", "email"},
}

// Normalize (expand wildcards, remove duplicates)
mask.Normalize()

// Check if path is in mask
if mask.IsValid(user) {
    // Valid paths for User
}
```

### Struct (Dynamic JSON)

**Definition**:
```protobuf
import "google/protobuf/struct.proto";

message Metadata {
  google.protobuf.Struct data = 1;  // Arbitrary JSON
}
```

**Structure**:
```protobuf
message Struct {
  map<string, Value> fields = 1;
}

message Value {
  oneof kind {
    NullValue null_value = 1;
    double number_value = 2;
    string string_value = 3;
    bool bool_value = 4;
    Struct struct_value = 5;
    ListValue list_value = 6;
  }
}
```

**Usage (Python)**:
```python
from google.protobuf.struct_pb2 import Struct

# Create struct from dict
s = Struct()
s.update({
    "name": "Alice",
    "age": 30,
    "tags": ["python", "protobuf"]
})

# Convert to dict
d = dict(s)
```

---

## Schema Registry

### Confluent Schema Registry (Kafka)

**Architecture**:
```
Producer → [Schema Registry] → Kafka → Consumer
            ↓ Store schemas
            ↓ Validate compatibility
            ↓ Assign schema IDs
```

**Setup**:
```yaml
# docker-compose.yml
version: '3'
services:
  schema-registry:
    image: confluentinc/cp-schema-registry:latest
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:9092
```

**Producer with Schema Registry (Python)**:
```python
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.protobuf import ProtobufSerializer
from user_pb2 import User

# Schema Registry client
schema_registry_conf = {'url': 'http://localhost:8081'}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

# Protobuf serializer
protobuf_serializer = ProtobufSerializer(
    User,
    schema_registry_client,
    conf={'use.deprecated.format': False}
)

# Producer
producer_conf = {
    'bootstrap.servers': 'localhost:9092',
    'value.serializer': protobuf_serializer
}
producer = SerializingProducer(producer_conf)

# Send message
user = User(id='123', name='Alice', email='alice@example.com')
producer.produce(topic='users', value=user, key='123')
producer.flush()
```

**Consumer with Schema Registry (Python)**:
```python
from confluent_kafka import DeserializingConsumer
from confluent_kafka.schema_registry.protobuf import ProtobufDeserializer

# Protobuf deserializer
protobuf_deserializer = ProtobufDeserializer(
    User,
    conf={'use.deprecated.format': False}
)

# Consumer
consumer_conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'user-consumer',
    'value.deserializer': protobuf_deserializer
}
consumer = DeserializingConsumer(consumer_conf)
consumer.subscribe(['users'])

# Consume
while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue

    user = msg.value()  # Deserialized User object
    print(f"User: {user.name}")
```

**Compatibility modes**:
```python
from confluent_kafka.schema_registry import SchemaRegistryClient

client = SchemaRegistryClient({'url': 'http://localhost:8081'})

# Set compatibility mode
client.set_compatibility(
    subject_name='users-value',
    level='BACKWARD'  # or 'FORWARD', 'FULL', 'NONE'
)
```

**Compatibility levels**:
- **BACKWARD**: New schema can read old data (default)
- **FORWARD**: Old schema can read new data
- **FULL**: Both backward and forward compatible
- **NONE**: No compatibility checks

**Schema evolution example**:
```python
# V1 schema
message User {
  string id = 1;
  string name = 2;
}

# V2 schema (backward compatible)
message User {
  string id = 1;
  string name = 2;
  string email = 3;  # New field (old consumers ignore)
}

# Register V2
# Schema Registry validates compatibility with V1
# If compatible, assigns new schema ID
```

### Pulsar Schema Registry

**Producer with Protobuf (Python)**:
```python
import pulsar
from user_pb2 import User

client = pulsar.Client('pulsar://localhost:6650')

# Producer with Protobuf schema
producer = client.create_producer(
    topic='users',
    schema=pulsar.schema.ProtobufSchema(User)
)

# Send message
user = User(id='123', name='Alice', email='alice@example.com')
producer.send(user)

producer.close()
client.close()
```

**Consumer with Protobuf (Python)**:
```python
import pulsar
from user_pb2 import User

client = pulsar.Client('pulsar://localhost:6650')

# Consumer with Protobuf schema
consumer = client.subscribe(
    topic='users',
    subscription_name='user-subscription',
    schema=pulsar.schema.ProtobufSchema(User)
)

# Receive messages
while True:
    msg = consumer.receive()
    try:
        user = msg.value()  # Deserialized User
        print(f"User: {user.name}")
        consumer.acknowledge(msg)
    except Exception as e:
        consumer.negative_acknowledge(msg)

consumer.close()
client.close()
```

**Schema evolution (automatic)**:
- Pulsar automatically handles schema evolution
- Validates compatibility on producer registration
- Stores schema versions in metadata store

---

## Performance

### Encoding Efficiency

**Message size comparison**:
```
JSON:     {"id": "123", "name": "Alice", "age": 30}
          47 bytes

XML:      <User><id>123</id><name>Alice</name><age>30</age></User>
          58 bytes

Protobuf: [binary]
          15 bytes (3x smaller than JSON)
```

**Field number impact**:
```protobuf
message Example {
  string field_1 = 1;     // Tag: 1 byte (0x0A)
  string field_15 = 15;   // Tag: 1 byte (0x7A)
  string field_16 = 16;   // Tag: 2 bytes (0x82 0x01)
  string field_2047 = 2047; // Tag: 2 bytes (0xFA 0x7F)
  string field_2048 = 2048; // Tag: 3 bytes (0x82 0x80 0x01)
}
```

**Takeaway**: Use field numbers 1-15 for frequently set fields to save 1 byte per field.

### Serialization Speed

**Benchmark comparison** (approximate):
```
Operation           Protobuf    JSON        XML
Serialize (1M msg)  0.5s        2.5s        10s
Deserialize (1M)    0.6s        3.0s        12s
```

**Protobuf advantages**:
- No parsing overhead (binary format)
- No string conversions
- Minimal allocations
- Direct memory mapping

### Packed Encoding

**Packed vs unpacked repeated fields**:
```protobuf
message Example {
  repeated int32 values = 1;  // Proto3: Packed by default
}

// Unpacked encoding (proto2 default):
values: [1, 2, 3]
Wire format: 08 01 08 02 08 03  (9 bytes)
             ^tag  ^tag  ^tag

// Packed encoding (proto3 default):
values: [1, 2, 3]
Wire format: 0A 03 01 02 03  (5 bytes)
             ^tag ^len ^values
```

**Savings**: ~40-50% for numeric repeated fields.

**When packed is more efficient**:
- Many small numeric values
- Repeated numeric types (int32, int64, uint32, uint64, sint32, sint64, fixed32, fixed64, sfixed32, sfixed64, float, double, bool, enum)

**When packed is less efficient**:
- Few values (overhead of length prefix)
- Large values (no benefit)
- String/bytes (not applicable)

### Message Size Optimization

**Tips**:
1. **Use smaller types**:
```protobuf
// Instead of:
int64 count = 1;  // 8 bytes for large values

// Use:
int32 count = 1;  // 4 bytes max
```

2. **Use sint for negative values**:
```protobuf
// Instead of:
int32 delta = 1;  // Inefficient for negatives (-1 = 10 bytes)

// Use:
sint32 delta = 1;  // ZigZag encoding (-1 = 1 byte)
```

3. **Use fixed types for large values**:
```protobuf
// If value often > 2^28:
fixed32 large_value = 1;  // Always 4 bytes

// If value often < 2^28:
int32 small_value = 2;  // 1-5 bytes (varint)
```

4. **Avoid large strings**:
```protobuf
// Instead of:
string large_text = 1;  // Stores entire content

// Use:
string text_url = 1;  // Store URL/reference
```

5. **Use bytes for binary data**:
```protobuf
// Instead of:
string base64_data = 1;  // 33% larger

// Use:
bytes binary_data = 1;  // Raw bytes
```

### Memory Usage

**Message pooling** (reduce allocations):
```go
import "sync"

var userPool = sync.Pool{
    New: func() interface{} {
        return &pb.User{}
    },
}

// Get from pool
user := userPool.Get().(*pb.User)
user.Reset()

// Use message
user.Id = "123"
user.Name = "Alice"

// Return to pool
userPool.Put(user)
```

**Avoid unnecessary copies**:
```go
// Bad: Copy entire message
func ProcessUser(user pb.User) {  // Pass by value
    // ...
}

// Good: Pass by reference
func ProcessUser(user *pb.User) {  // Pass by pointer
    // ...
}
```

---

## Advanced Patterns

### Event Sourcing

**Event schema design**:
```protobuf
import "google/protobuf/timestamp.proto";
import "google/protobuf/any.proto";

message Event {
  string event_id = 1;
  string aggregate_id = 2;
  int64 version = 3;
  google.protobuf.Timestamp timestamp = 4;
  google.protobuf.Any payload = 5;  // Event-specific data
  map<string, string> metadata = 6;
}

// Specific events
message UserCreatedEvent {
  string user_id = 1;
  string email = 2;
  string name = 3;
}

message UserEmailChangedEvent {
  string user_id = 1;
  string old_email = 2;
  string new_email = 3;
}

message UserDeletedEvent {
  string user_id = 1;
}
```

**Event envelope pattern**:
```protobuf
message EventEnvelope {
  string event_type = 1;          // "UserCreated", "UserEmailChanged"
  int64 sequence = 2;             // Event sequence number
  google.protobuf.Timestamp occurred_at = 3;
  string aggregate_id = 4;
  int64 aggregate_version = 5;

  oneof event {
    UserCreatedEvent user_created = 10;
    UserEmailChangedEvent user_email_changed = 11;
    UserDeletedEvent user_deleted = 12;
  }
}
```

### CQRS (Command Query Responsibility Segregation)

**Command messages**:
```protobuf
// Commands (write operations)
message CreateUserCommand {
  string command_id = 1;
  string email = 2;
  string name = 3;
  google.protobuf.Timestamp issued_at = 4;
}

message UpdateUserEmailCommand {
  string command_id = 1;
  string user_id = 2;
  string new_email = 3;
  google.protobuf.Timestamp issued_at = 4;
}

message DeleteUserCommand {
  string command_id = 1;
  string user_id = 2;
  google.protobuf.Timestamp issued_at = 3;
}
```

**Query messages**:
```protobuf
// Queries (read operations)
message GetUserQuery {
  string query_id = 1;
  string user_id = 2;
}

message ListUsersQuery {
  string query_id = 1;
  int32 page_size = 2;
  string page_token = 3;
  string filter = 4;
}

message UserReadModel {
  string id = 1;
  string email = 2;
  string name = 3;
  google.protobuf.Timestamp created_at = 4;
  google.protobuf.Timestamp updated_at = 5;
}
```

### Domain-Driven Design (DDD)

**Value objects**:
```protobuf
message Money {
  string currency = 1;  // ISO 4217 code (e.g., "USD")
  int64 amount = 2;     // Amount in smallest unit (cents)
}

message Address {
  string street = 1;
  string city = 2;
  string state = 3;
  string postal_code = 4;
  string country = 5;   // ISO 3166-1 alpha-2 (e.g., "US")
}

message EmailAddress {
  string value = 1;     // Validated email
}
```

**Entities**:
```protobuf
message User {
  string id = 1;              // Unique identifier
  EmailAddress email = 2;     // Value object
  string name = 3;
  Address address = 4;        // Value object
  google.protobuf.Timestamp created_at = 5;
  google.protobuf.Timestamp updated_at = 6;
  int64 version = 7;          // Optimistic locking
}
```

**Aggregates**:
```protobuf
message Order {
  string id = 1;
  string customer_id = 2;
  repeated OrderItem items = 3;
  Money total = 4;
  OrderStatus status = 5;
  google.protobuf.Timestamp created_at = 6;

  message OrderItem {
    string product_id = 1;
    int32 quantity = 2;
    Money unit_price = 3;
    Money subtotal = 4;
  }
}

enum OrderStatus {
  ORDER_STATUS_UNSPECIFIED = 0;
  ORDER_STATUS_PENDING = 1;
  ORDER_STATUS_CONFIRMED = 2;
  ORDER_STATUS_SHIPPED = 3;
  ORDER_STATUS_DELIVERED = 4;
  ORDER_STATUS_CANCELLED = 5;
}
```

### API Versioning

**Package-based versioning**:
```protobuf
// v1/user.proto
syntax = "proto3";
package users.v1;

message User {
  string id = 1;
  string name = 2;
}

service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
}

// v2/user.proto
syntax = "proto3";
package users.v2;

message User {
  string id = 1;
  string full_name = 2;  // Renamed from 'name'
  string email = 3;      // New field
}

service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
}
```

**Side-by-side versioning** (support both):
```go
import (
    v1 "github.com/example/users/v1"
    v2 "github.com/example/users/v2"
)

// V1 handler
func (s *Server) GetUserV1(ctx context.Context, req *v1.GetUserRequest) (*v1.GetUserResponse, error) {
    // V1 implementation
}

// V2 handler
func (s *Server) GetUserV2(ctx context.Context, req *v2.GetUserRequest) (*v2.GetUserResponse, error) {
    // V2 implementation
}
```

---

## Tools and Ecosystem

### protoc Plugins

**Official plugins**:
```bash
# Go
protoc-gen-go          # Message types
protoc-gen-go-grpc     # gRPC services

# Python
protoc-gen-python      # Message types (built-in)
protoc-gen-python-grpc # gRPC services

# Java
protoc-gen-java        # Message types (built-in)
protoc-gen-grpc-java   # gRPC services

# TypeScript
protoc-gen-ts          # Message types
protoc-gen-grpc-web    # gRPC-Web
```

**Third-party plugins**:
```bash
# Validation
protoc-gen-validate    # Generate validation code

# Documentation
protoc-gen-doc         # Generate HTML/Markdown docs

# OpenAPI
protoc-gen-openapi     # Generate OpenAPI specs

# GraphQL
protoc-gen-graphql     # Generate GraphQL schemas
```

### grpcurl (gRPC curl)

**Installation**:
```bash
# macOS
brew install grpcurl

# Go
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
```

**Usage**:
```bash
# List services
grpcurl -plaintext localhost:50051 list

# List methods
grpcurl -plaintext localhost:50051 list UserService

# Describe method
grpcurl -plaintext localhost:50051 describe UserService.GetUser

# Call method (JSON input)
grpcurl -plaintext -d '{"id": "123"}' localhost:50051 UserService/GetUser

# With metadata
grpcurl -plaintext -H 'Authorization: Bearer token123' -d '{"id": "123"}' localhost:50051 UserService/GetUser

# Server reflection (list all)
grpcurl -plaintext localhost:50051 list
```

### buf (Modern Build Tool)

See [Code Generation](#buf-modern-protobuf-tool) section for detailed buf usage.

**Key commands**:
```bash
buf lint              # Lint schemas
buf breaking          # Check breaking changes
buf generate          # Generate code
buf push              # Push to Buf Schema Registry
```

### protoc-gen-doc (Documentation Generator)

**Installation**:
```bash
go install github.com/pseudomuto/protoc-gen-doc/cmd/protoc-gen-doc@latest
```

**Generate HTML docs**:
```bash
protoc --doc_out=./docs --doc_opt=html,index.html user.proto
```

**Generate Markdown docs**:
```bash
protoc --doc_out=./docs --doc_opt=markdown,README.md user.proto
```

### protoc-gen-validate (Validation)

**Installation**:
```bash
go install github.com/envoyproxy/protoc-gen-validate@latest
```

**Add validation rules**:
```protobuf
import "validate/validate.proto";

message User {
  string id = 1 [(validate.rules).string = {min_len: 1, max_len: 36}];
  string email = 2 [(validate.rules).string.email = true];
  int32 age = 3 [(validate.rules).int32 = {gte: 0, lte: 150}];
  repeated string tags = 4 [(validate.rules).repeated = {min_items: 1, max_items: 10}];
}
```

**Generate validation code**:
```bash
protoc --validate_out="lang=go:." user.proto
```

---

## Anti-Patterns

### Field Number Misuse

❌ **Reusing deleted field numbers**:
```protobuf
// V1
message User {
  string id = 1;
  string old_field = 2;  // Deleted later
}

// V2 (WRONG)
message User {
  string id = 1;
  string new_field = 2;  // Reused field number 2 ❌
}
```

**Why bad**: Old clients send old_field with number 2, new server interprets as new_field → data corruption.

✅ **Use reserved**:
```protobuf
message User {
  reserved 2;
  reserved "old_field";

  string id = 1;
  string new_field = 3;  // New field number
}
```

### Type Changes

❌ **Incompatible type changes**:
```protobuf
// V1
message User {
  int32 age = 1;
}

// V2 (BREAKING)
message User {
  string age = 1;  // Changed int32 → string ❌
}
```

**Why bad**: Wire types incompatible (varint vs length-delimited) → parsing errors.

✅ **Add new field**:
```protobuf
message User {
  int32 age = 1 [deprecated = true];
  string age_text = 2;
}
```

### Large Messages

❌ **Monolithic messages**:
```protobuf
message User {
  string id = 1;
  string name = 2;
  bytes profile_image = 3;     // 5 MB image ❌
  bytes resume_pdf = 4;        // 10 MB PDF ❌
  repeated string log_entries = 5;  // 100k entries ❌
}
```

**Why bad**:
- Large serialization/deserialization time
- High memory usage
- Network overhead

✅ **Split into smaller messages**:
```protobuf
message User {
  string id = 1;
  string name = 2;
  string profile_image_url = 3;  // URL to image
  string resume_url = 4;         // URL to PDF
}

message UserLogs {
  string user_id = 1;
  repeated LogEntry entries = 2;
}
```

### Missing Zero Value in Enums

❌ **No zero value**:
```protobuf
enum Status {
  STATUS_ACTIVE = 1;     // First value not 0 ❌
  STATUS_INACTIVE = 2;
}
```

**Why bad**: Proto3 default is 0, which doesn't exist → undefined behavior.

✅ **Always define zero value**:
```protobuf
enum Status {
  STATUS_UNSPECIFIED = 0;  // Zero value
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
}
```

### No Versioning

❌ **No package versioning**:
```protobuf
package users;  // No version ❌

message User {
  string id = 1;
  string name = 2;
}
```

**Why bad**: Cannot introduce breaking changes without breaking clients.

✅ **Use versioned packages**:
```protobuf
package users.v1;

message User {
  string id = 1;
  string name = 2;
}
```

### Inefficient Field Numbers

❌ **Wasting 1-15 range**:
```protobuf
message User {
  string id = 100;              // Wasting 2-byte tag ❌
  string name = 200;
  string rarely_used = 1;       // Rare field in hot range ❌
}
```

✅ **Use 1-15 for hot fields**:
```protobuf
message User {
  string id = 1;                // Hot field
  string name = 2;              // Hot field
  string rarely_used = 100;     // Cold field
}
```

---

## Migration Guides

### Proto2 to Proto3 Migration

**Step 1: Analyze current schema**:
```bash
# Check for proto2-specific features
grep -r "required" *.proto
grep -r "optional" *.proto
grep -r "default =" *.proto
grep -r "extensions" *.proto
```

**Step 2: Remove required/optional**:
```protobuf
// Proto2
message User {
  required string id = 1;
  optional string name = 2;
}

// Proto3
message User {
  string id = 1;     // All fields optional
  string name = 2;
}
```

**Step 3: Remove custom defaults**:
```protobuf
// Proto2
message User {
  optional int32 age = 1 [default = 0];
}

// Proto3
message User {
  int32 age = 1;  // Default is 0 (type default)
}
```

**Step 4: Fix enum zero values**:
```protobuf
// Proto2
enum Status {
  ACTIVE = 1;
  INACTIVE = 2;
}

// Proto3
enum Status {
  STATUS_UNSPECIFIED = 0;  // Add zero value
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
}
```

**Step 5: Replace extensions with Any**:
```protobuf
// Proto2
message User {
  extensions 100 to 200;
}

extend User {
  optional string custom_field = 100;
}

// Proto3
import "google/protobuf/any.proto";

message User {
  google.protobuf.Any extensions = 10;
}
```

**Step 6: Update syntax**:
```protobuf
// Change from:
syntax = "proto2";

// To:
syntax = "proto3";
```

**Step 7: Test thoroughly**:
```bash
# Generate code
protoc --python_out=. user.proto

# Run tests
pytest tests/
```

### JSON to Protobuf Migration

**Step 1: Design schema from JSON**:
```json
{
  "id": "123",
  "name": "Alice",
  "age": 30,
  "tags": ["python", "protobuf"],
  "address": {
    "city": "New York",
    "country": "US"
  }
}
```

**Step 2: Create proto schema**:
```protobuf
syntax = "proto3";

message User {
  string id = 1;
  string name = 2;
  int32 age = 3;
  repeated string tags = 4;
  Address address = 5;

  message Address {
    string city = 1;
    string country = 2;
  }
}
```

**Step 3: Dual serialization (transition period)**:
```python
import json
from user_pb2 import User

def serialize_user(user_data):
    # Serialize as both JSON and Protobuf
    json_data = json.dumps(user_data)

    proto_user = User()
    proto_user.id = user_data['id']
    proto_user.name = user_data['name']
    proto_user.age = user_data['age']
    proto_user.tags.extend(user_data['tags'])
    proto_data = proto_user.SerializeToString()

    return {'json': json_data, 'proto': proto_data}

def deserialize_user(data):
    # Try Protobuf first, fall back to JSON
    try:
        user = User()
        user.ParseFromString(data)
        return user
    except:
        return json.loads(data)
```

**Step 4: Gradual rollout**:
1. Week 1: Deploy dual serialization (write both, read proto with JSON fallback)
2. Week 2-4: Monitor, ensure all clients upgraded
3. Week 5: Remove JSON serialization
4. Week 6: Remove JSON deserialization fallback

---

## Language-Specific Details

### Python Specifics

**Generated code structure**:
```python
# user_pb2.py
class User(Message):
    id: str
    name: str
    age: int

    def SerializeToString(self) -> bytes: ...
    def ParseFromString(self, data: bytes) -> None: ...
    def HasField(self, field_name: str) -> bool: ...
    def ClearField(self, field_name: str) -> None: ...
```

**Field access**:
```python
from user_pb2 import User

user = User()

# Set fields
user.id = "123"
user.name = "Alice"

# Get fields
print(user.id)
print(user.name)

# Repeated fields (list operations)
user.tags.append("python")
user.tags.extend(["protobuf", "grpc"])
del user.tags[0]

# Map fields (dict operations)
user.attributes["key1"] = "value1"
user.attributes.update({"key2": "value2"})

# Nested messages
user.address.city = "New York"
user.address.country = "US"
```

**Serialization**:
```python
# Binary serialization
data = user.SerializeToString()  # bytes

# JSON serialization
from google.protobuf.json_format import MessageToJson, Parse
json_str = MessageToJson(user)  # str
user2 = Parse(json_str, User())

# Dict conversion
from google.protobuf.json_format import MessageToDict, ParseDict
user_dict = MessageToDict(user)
user3 = ParseDict(user_dict, User())
```

**Validation**:
```python
# Check if field is set (only for optional/oneof fields)
if user.HasField("email"):
    print(user.email)

# Clear field
user.ClearField("email")

# Check which oneof is set
if user.WhichOneof("payment_method") == "credit_card":
    print(user.credit_card)
```

### Go Specifics

**Generated code structure**:
```go
type User struct {
    Id    string   `protobuf:"bytes,1,opt,name=id,proto3" json:"id,omitempty"`
    Name  string   `protobuf:"bytes,2,opt,name=name,proto3" json:"name,omitempty"`
    Age   int32    `protobuf:"varint,3,opt,name=age,proto3" json:"age,omitempty"`
    Tags  []string `protobuf:"bytes,4,rep,name=tags,proto3" json:"tags,omitempty"`
}

func (m *User) Reset()
func (m *User) String() string
func (m *User) ProtoMessage()
func (m *User) GetId() string
func (m *User) GetName() string
```

**Field access**:
```go
import pb "github.com/example/protos/users/v1"

user := &pb.User{
    Id:   "123",
    Name: "Alice",
    Age:  30,
    Tags: []string{"go", "protobuf"},
}

// Getters (safe for nil)
id := user.GetId()   // Returns "" if user is nil
name := user.GetName()

// Direct field access
user.Id = "456"
user.Name = "Bob"

// Repeated fields
user.Tags = append(user.Tags, "grpc")

// Map fields
user.Attributes = map[string]string{
    "key1": "value1",
}
```

**Serialization**:
```go
import "google.golang.org/protobuf/proto"

// Binary serialization
data, err := proto.Marshal(user)
if err != nil {
    log.Fatal(err)
}

// Deserialization
user2 := &pb.User{}
err = proto.Unmarshal(data, user2)
if err != nil {
    log.Fatal(err)
}

// Clone
user3 := proto.Clone(user).(*pb.User)

// Equal
if proto.Equal(user, user2) {
    fmt.Println("Equal")
}
```

**JSON marshaling**:
```go
import "google.golang.org/protobuf/encoding/protojson"

// To JSON
marshaler := protojson.MarshalOptions{
    Indent: "  ",
    UseProtoNames: true,  // Use proto field names (not lowerCamelCase)
}
jsonData, err := marshaler.Marshal(user)

// From JSON
unmarshaler := protojson.UnmarshalOptions{
    DiscardUnknown: true,
}
user2 := &pb.User{}
err = unmarshaler.Unmarshal(jsonData, user2)
```

### Java Specifics

**Generated code structure**:
```java
public final class User extends GeneratedMessageV3 {
    private volatile java.lang.Object id_;
    private volatile java.lang.Object name_;
    private int age_;

    public java.lang.String getId() { ... }
    public java.lang.String getName() { ... }
    public int getAge() { ... }

    public static Builder newBuilder() { ... }
    public byte[] toByteArray() { ... }
    public static User parseFrom(byte[] data) { ... }
}
```

**Field access (builder pattern)**:
```java
import com.example.UserProto.User;

// Create (immutable)
User user = User.newBuilder()
    .setId("123")
    .setName("Alice")
    .setAge(30)
    .addTags("java")
    .addTags("protobuf")
    .putAttributes("key1", "value1")
    .build();

// Getters
String id = user.getId();
String name = user.getName();
int age = user.getAge();

// Modify (creates new instance)
User user2 = user.toBuilder()
    .setName("Bob")
    .build();

// Check field presence
if (user.hasEmail()) {
    System.out.println(user.getEmail());
}
```

**Serialization**:
```java
// Binary serialization
byte[] data = user.toByteArray();

// Deserialization
User user2 = User.parseFrom(data);

// JSON serialization
import com.google.protobuf.util.JsonFormat;

String jsonString = JsonFormat.printer().print(user);
User.Builder builder = User.newBuilder();
JsonFormat.parser().merge(jsonString, builder);
User user3 = builder.build();
```

---

**End of Reference**

This reference covers all essential aspects of Protocol Buffers schema design, evolution, code generation, and best practices. For the latest updates and features, consult the official Protocol Buffers documentation at https://protobuf.dev/.
