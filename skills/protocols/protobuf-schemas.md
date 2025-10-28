---
name: protocols-protobuf-schemas
description: Protocol Buffers schema design, evolution, and code generation
---

# Protocol Buffers Schemas

**Scope**: Proto syntax, schema design, field numbering, backward/forward compatibility, code generation, schema registry
**Lines**: ~350
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Designing Protocol Buffer schemas from scratch
- Implementing schema evolution strategies
- Managing schema versioning and compatibility
- Generating code for multiple languages
- Integrating with gRPC or Kafka
- Setting up schema registries
- Validating schema best practices
- Migrating between proto2 and proto3

## Core Concepts

### What are Protocol Buffers?

**Protocol Buffers** (protobuf): Language-neutral, platform-neutral mechanism for serializing structured data.

**Key characteristics**:
- **Compact binary format**: 3-10x smaller than XML/JSON
- **Fast**: 20-100x faster than XML/JSON
- **Type-safe**: Strong typing enforced by schema
- **Forward/backward compatible**: Schema evolution without breaking clients
- **Multi-language**: Code generation for 10+ languages
- **Self-describing**: Schema embedded in generated code

**Use cases**:
- gRPC service definitions
- Kafka message serialization
- Configuration files
- Data storage formats
- Inter-service communication

### Proto3 vs Proto2

**Proto3** (recommended):
```protobuf
syntax = "proto3";  // Always specify

message User {
  string id = 1;
  string name = 2;
  int32 age = 3;        // Default value: 0
  repeated string tags = 4;  // Default: empty list
}
```

**Proto2** (legacy):
```protobuf
syntax = "proto2";

message User {
  required string id = 1;      // Must be set
  optional string name = 2;    // May be set
  optional int32 age = 3 [default = 0];
  repeated string tags = 4;
}
```

**Key differences**:
- Proto3: No `required`/`optional` keywords (all fields optional)
- Proto3: No default values (uses type defaults)
- Proto3: Simpler syntax, better performance
- Proto2: Explicit presence detection

---

## Schema Design Basics

### Field Numbers

**Critical rule**: Field numbers are permanent identifiers used in binary encoding.

```protobuf
message User {
  string id = 1;      // Field number 1
  string name = 2;    // Field number 2
  int32 age = 3;      // Field number 3
}
```

**Best practices**:
- **1-15**: Single-byte encoding (use for frequent fields)
- **16-2047**: Two-byte encoding (use for less frequent fields)
- **19000-19999**: Reserved by Protocol Buffers
- **Never reuse** deleted field numbers (use `reserved`)

### Reserved Fields

Prevent field number/name reuse:

```protobuf
message User {
  reserved 5, 8 to 10;              // Reserved numbers
  reserved "old_field", "deprecated_field";  // Reserved names

  string id = 1;
  string name = 2;
  // Field 5 cannot be reused
}
```

### Data Types

**Scalar types**:
```protobuf
message Example {
  // Integers
  int32 age = 1;           // -2^31 to 2^31-1
  int64 user_id = 2;       // -2^63 to 2^63-1
  uint32 count = 3;        // 0 to 2^32-1
  sint32 delta = 4;        // Signed (efficient for negatives)

  // Floating point
  float price = 5;
  double precise = 6;

  // Boolean
  bool is_active = 7;

  // String (UTF-8 or ASCII)
  string name = 8;

  // Bytes (arbitrary byte sequence)
  bytes data = 9;
}
```

**Well-known types** (import from `google/protobuf/*`):
```protobuf
import "google/protobuf/timestamp.proto";
import "google/protobuf/duration.proto";
import "google/protobuf/any.proto";

message Event {
  google.protobuf.Timestamp created_at = 1;
  google.protobuf.Duration timeout = 2;
  google.protobuf.Any metadata = 3;  // Can hold any message type
}
```

### Repeated Fields (Lists)

```protobuf
message User {
  repeated string tags = 1;           // List of strings
  repeated Address addresses = 2;     // List of nested messages
}

// Packed encoding (more efficient for numeric types)
message Metrics {
  repeated int32 values = 1 [packed = true];  // Proto3 default
}
```

### Enums

```protobuf
enum Status {
  STATUS_UNSPECIFIED = 0;  // Always have 0 as first value
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
  STATUS_PENDING = 3;
}

message User {
  Status status = 1;
}
```

**Best practices**:
- First value must be 0 (default in proto3)
- Use `_UNSPECIFIED` suffix for zero value
- Prefix enum values with enum name to avoid conflicts

### Nested Messages

```protobuf
message User {
  string id = 1;
  Address address = 2;

  // Nested message (scoped to User)
  message Address {
    string street = 1;
    string city = 2;
    string postal_code = 3;
  }
}

// Usage: User.Address
```

### Oneof (Union Types)

Only one field can be set:

```protobuf
message SearchRequest {
  oneof query {
    string text_query = 1;
    int32 id_query = 2;
    bool all_query = 3;
  }
}

// Set text_query → id_query and all_query are cleared
```

### Maps

```protobuf
message User {
  map<string, string> attributes = 1;  // Key must be scalar (except float/double/bytes)
  map<int32, Address> addresses = 2;
}
```

---

## Schema Evolution

### Backward Compatibility

**Old clients** can read **new data**.

**Safe changes**:
- ✅ Add new fields (old clients ignore them)
- ✅ Delete fields (mark as `reserved`)
- ✅ Add new enum values (old clients see as unknown)

**Breaking changes**:
- ❌ Change field number
- ❌ Change field type (string ↔ int32, etc.)
- ❌ Rename fields (wire format uses numbers, but affects JSON)
- ❌ Change repeated ↔ singular
- ❌ Reuse deleted field numbers

**Example**:
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
  reserved 4;            // Deleted field
  repeated string tags = 5;
}
```

### Forward Compatibility

**New clients** can read **old data**.

**Safe changes**:
- ✅ Add new fields with defaults
- ✅ Delete fields (new client handles missing data)

**Breaking changes**:
- ❌ Make field required (proto2)
- ❌ Remove default values (proto2)

### Deprecation

```protobuf
message User {
  string id = 1;
  string name = 2 [deprecated = true];  // Mark as deprecated
  string full_name = 3;                 // Replacement field
}
```

---

## Code Generation

### Multi-Language Support

**Python**:
```bash
# Install compiler
pip install grpcio-tools

# Generate code
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. user.proto

# Output: user_pb2.py, user_pb2_grpc.py
```

**Go**:
```bash
# Install plugins
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Generate code
protoc --go_out=. --go_opt=paths=source_relative \
       --go-grpc_out=. --go-grpc_opt=paths=source_relative \
       user.proto

# Output: user.pb.go, user_grpc.pb.go
```

**Java**:
```bash
# Add plugin to pom.xml
protoc --java_out=src/main/java user.proto

# Output: User.java
```

**TypeScript**:
```bash
# Install plugins
npm install -D protoc-gen-ts protoc-gen-grpc-web

# Generate code
protoc --ts_out=. --grpc-web_out=import_style=typescript,mode=grpcwebtext:. user.proto

# Output: user_pb.ts
```

### Buf (Modern Build Tool)

**buf.yaml**:
```yaml
version: v1
breaking:
  use:
    - FILE
lint:
  use:
    - DEFAULT
```

**buf.gen.yaml** (code generation):
```yaml
version: v1
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

**Usage**:
```bash
# Install
brew install bufbuild/buf/buf

# Lint schemas
buf lint

# Generate code
buf generate

# Check breaking changes
buf breaking --against .git#branch=main
```

---

## Schema Registry Integration

### Confluent Schema Registry (Kafka)

```python
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.protobuf import ProtobufSerializer

# Schema Registry client
schema_registry_client = SchemaRegistryClient({
    'url': 'http://localhost:8081'
})

# Protobuf serializer
protobuf_serializer = ProtobufSerializer(
    User,  # Generated class
    schema_registry_client,
    {'use.deprecated.format': False}
)

# Producer
producer = SerializingProducer({
    'bootstrap.servers': 'localhost:9092',
    'value.serializer': protobuf_serializer
})

# Send message
user = User(id='123', name='Alice')
producer.produce('users', value=user)
producer.flush()
```

### Pulsar Schema Registry

```python
import pulsar

client = pulsar.Client('pulsar://localhost:6650')

# Producer with Protobuf schema
producer = client.create_producer(
    'users',
    schema=pulsar.schema.ProtobufSchema(User)
)

user = User(id='123', name='Alice')
producer.send(user)
```

---

## Common Patterns

### Request/Response Pattern (gRPC)

```protobuf
service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
  rpc ListUsers(ListUsersRequest) returns (ListUsersResponse);
}

message GetUserRequest {
  string id = 1;
}

message GetUserResponse {
  User user = 1;
  string error = 2;  // Error message if failed
}

message ListUsersRequest {
  int32 page_size = 1;
  string page_token = 2;
}

message ListUsersResponse {
  repeated User users = 1;
  string next_page_token = 2;
}
```

### Domain Modeling

```protobuf
// Event sourcing
message UserCreatedEvent {
  string user_id = 1;
  string email = 2;
  google.protobuf.Timestamp created_at = 3;
}

message UserUpdatedEvent {
  string user_id = 1;
  map<string, string> updated_fields = 2;
  google.protobuf.Timestamp updated_at = 3;
}

// Aggregate root
message User {
  string id = 1;
  string email = 2;
  UserProfile profile = 3;
  repeated Address addresses = 4;
  google.protobuf.Timestamp created_at = 5;
  google.protobuf.Timestamp updated_at = 6;
}
```

---

## Anti-Patterns

❌ **Reusing field numbers**: Breaks backward compatibility
✅ Use `reserved` for deleted fields

❌ **Changing field types**: `string` → `int32` breaks wire format
✅ Add new field with new type, deprecate old field

❌ **Using field numbers > 2047 for frequent fields**: Inefficient encoding
✅ Use 1-15 for hot fields, 16-2047 for cold fields

❌ **Not using `reserved`**: Developers might reuse numbers/names
✅ Always mark deleted fields as reserved

❌ **Enum without zero value**: Default is 0, must be defined
✅ Always have `NAME_UNSPECIFIED = 0` for enums

❌ **Large messages (> 1MB)**: Performance issues
✅ Split into smaller messages or use streaming

❌ **No schema versioning**: Can't track changes
✅ Use package versioning (`users.v1`, `users.v2`)

---

## Level 3: Resources

### Overview

This skill includes comprehensive Level 3 resources for deep Protocol Buffers schema design knowledge and practical automation tools.

**Resources include**:
- **REFERENCE.md** (3,200+ lines): Complete technical reference covering all protobuf concepts
- **3 executable scripts**: Schema validation, code generation, compatibility analysis
- **9 production examples**: Complete schema designs, evolution examples, multi-language integration

### REFERENCE.md

**Location**: `skills/protocols/protobuf-schemas/resources/REFERENCE.md`

**Comprehensive technical reference** (3,200+ lines) covering:

**Core Topics**:
- Protocol Buffers fundamentals and architecture
- Proto2 vs Proto3 syntax and migration
- Field types (scalar, repeated, maps, oneofs)
- Well-known types (Timestamp, Duration, Any, etc.)
- Schema evolution (backward/forward compatibility)
- Field numbering and reserved fields
- Code generation for Python, Go, Java, TypeScript, C++
- Schema registry integration (Confluent, Pulsar)
- Performance characteristics and optimization
- JSON mapping and custom options
- Advanced patterns (event sourcing, CQRS, domain modeling)

**Key Sections**:
1. **Fundamentals**: Binary encoding, wire format, serialization
2. **Syntax**: Proto3 syntax, field types, modifiers
3. **Schema Design**: Best practices, naming conventions, versioning
4. **Evolution**: Backward/forward compatibility rules, migration strategies
5. **Code Generation**: Multi-language support, custom options, plugins
6. **Well-Known Types**: Timestamp, Duration, Any, Empty, FieldMask
7. **Schema Registry**: Confluent, Pulsar, versioning strategies
8. **Performance**: Encoding efficiency, message size, serialization speed
9. **Advanced Patterns**: Event sourcing, domain modeling, API design
10. **Tools**: protoc, buf, grpcurl, schema validators
11. **Anti-Patterns**: Common mistakes and solutions

**Format**: Markdown with extensive code examples in multiple languages

### Scripts

Three production-ready executable scripts in `resources/scripts/`:

#### 1. validate_proto_schemas.py (680 lines)

**Purpose**: Parse and validate Protocol Buffer schemas

**Features**:
- Parse .proto files (proto2 and proto3)
- Validate syntax and field numbering
- Check naming conventions (PascalCase, snake_case)
- Detect breaking changes between versions
- Verify reserved fields and field number ranges
- Validate imports and dependencies
- Check best practices (enum zero values, field number efficiency)
- Output as JSON or human-readable text

**Usage**:
```bash
# Basic validation
./validate_proto_schemas.py --proto-file user.proto

# JSON output
./validate_proto_schemas.py --proto-file user.proto --json

# Check breaking changes
./validate_proto_schemas.py --proto-file user_v2.proto --check-breaking --baseline user_v1.proto

# Validate directory
./validate_proto_schemas.py --proto-dir ./protos --json
```

**Categories checked**:
- Syntax errors and parsing issues
- Field number conflicts and ranges
- Naming convention violations
- Reserved field usage
- Import validation
- Best practice recommendations

#### 2. generate_proto_code.py (750 lines)

**Purpose**: Generate code for multiple languages from proto schemas

**Features**:
- Support Python, Go, Java, TypeScript, C++
- Custom options and plugins
- Validate generated code structure
- Handle dependencies and imports
- Support buf.yaml and buf.gen.yaml
- Generate example usage code
- JSON output for automation

**Usage**:
```bash
# Generate Python code
./generate_proto_code.py --proto-file user.proto --language python --output-dir ./gen/python

# Generate multiple languages
./generate_proto_code.py --proto-file user.proto --languages python,go,java --output-dir ./gen

# Use buf for generation
./generate_proto_code.py --proto-dir ./protos --use-buf --output-dir ./gen

# JSON output
./generate_proto_code.py --proto-file user.proto --language go --json
```

**Supported languages**:
- Python: `*_pb2.py`, `*_pb2_grpc.py`
- Go: `*.pb.go`, `*_grpc.pb.go`
- Java: `*.java`
- TypeScript: `*_pb.ts`, `*_pb_service.ts`
- C++: `*.pb.h`, `*.pb.cc`

#### 3. analyze_schema_compatibility.py (650 lines)

**Purpose**: Compare schema versions and detect breaking changes

**Features**:
- Compare two schema versions
- Detect breaking vs non-breaking changes
- Verify backward/forward compatibility
- Suggest migration paths
- Validate evolution rules
- Generate compatibility report
- JSON output for CI/CD

**Usage**:
```bash
# Compare schemas
./analyze_schema_compatibility.py --old user_v1.proto --new user_v2.proto

# Check backward compatibility
./analyze_schema_compatibility.py --old user_v1.proto --new user_v2.proto --mode backward

# JSON output for automation
./analyze_schema_compatibility.py --old user_v1.proto --new user_v2.proto --json

# Detailed migration report
./analyze_schema_compatibility.py --old user_v1.proto --new user_v2.proto --migration-guide
```

**Detects**:
- Field number changes (breaking)
- Field type changes (breaking)
- Field deletions (potentially breaking)
- Field additions (safe)
- Enum value changes
- Message nesting changes
- Service changes (gRPC)

### Examples

Nine production-ready examples in `resources/examples/`:

#### 1. user_service.proto
Complete service definition with CRUD operations, nested messages, enums, and well-known types.

#### 2. schema_evolution/
Directory with v1, v2, v3 of a schema demonstrating evolution:
- Adding fields (backward compatible)
- Deprecating fields
- Using reserved fields
- Type changes (safe patterns)

#### 3. breaking_vs_nonbreaking.md
Comprehensive guide with examples of breaking vs non-breaking changes.

#### 4. code_generation/
Multi-language code generation examples:
- Python client/server
- Go client/server
- Java implementation
- TypeScript integration

#### 5. schema_registry/
Integration examples:
- Confluent Schema Registry (Kafka)
- Pulsar Schema Registry
- Schema versioning strategies

#### 6. grpc_service/
Complete gRPC service definition with:
- Unary, server streaming, client streaming, bidirectional RPCs
- Error handling patterns
- Request/response wrappers

#### 7. kafka_messages/
Kafka message schemas with:
- Event sourcing patterns
- CQRS command/query separation
- Protobuf serialization

#### 8. buf_configuration/
buf.yaml and buf.gen.yaml examples:
- Linting rules
- Breaking change detection
- Multi-language code generation

#### 9. ci_validation/
CI/CD pipeline examples:
- GitHub Actions workflow
- GitLab CI pipeline
- Schema validation in CI

### Quick Start

**1. Validate schemas**:
```bash
cd skills/protocols/protobuf-schemas/resources/scripts
./validate_proto_schemas.py --proto-file ../examples/user_service.proto --json
```

**2. Generate code**:
```bash
./generate_proto_code.py --proto-file ../examples/user_service.proto --languages python,go --output-dir ./gen
```

**3. Check compatibility**:
```bash
./analyze_schema_compatibility.py --old ../examples/schema_evolution/v1.proto --new ../examples/schema_evolution/v2.proto
```

### File Structure

```
skills/protocols/protobuf-schemas/
├── protobuf-schemas.md (this file)
└── resources/
    ├── REFERENCE.md (3,200+ lines)
    ├── scripts/
    │   ├── validate_proto_schemas.py (680 lines)
    │   ├── generate_proto_code.py (750 lines)
    │   └── analyze_schema_compatibility.py (650 lines)
    └── examples/
        ├── user_service.proto
        ├── schema_evolution/
        │   ├── v1.proto
        │   ├── v2.proto
        │   └── v3.proto
        ├── breaking_vs_nonbreaking.md
        ├── code_generation/
        ├── schema_registry/
        ├── grpc_service/
        ├── kafka_messages/
        ├── buf_configuration/
        └── ci_validation/
```

### Resources Summary

| Category | Item | Lines | Description |
|----------|------|-------|-------------|
| **Reference** | REFERENCE.md | 3,200+ | Complete technical reference |
| **Scripts** | validate_proto_schemas.py | 680 | Schema validator |
| | generate_proto_code.py | 750 | Code generator |
| | analyze_schema_compatibility.py | 650 | Compatibility analyzer |
| **Examples** | 9 examples | 2,000+ | Production-ready schemas |

**Total**: 7,000+ lines of production-ready resources

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
