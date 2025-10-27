---
name: protocols-grpc-implementation
description: Implementing gRPC APIs with Protocol Buffers
---

# gRPC Implementation

**Scope**: gRPC services, Protocol Buffers, streaming, error handling, performance optimization
**Lines**: ~350
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Implementing gRPC services from scratch
- Designing Protocol Buffer schemas
- Implementing streaming RPCs (unary, server, client, bidirectional)
- Adding error handling and status codes
- Implementing interceptors and middleware
- Optimizing gRPC performance
- Setting up load balancing for gRPC
- Securing gRPC with TLS and authentication
- Debugging gRPC services

## Core Concepts

### gRPC Architecture

**gRPC** (gRPC Remote Procedure Call): High-performance RPC framework using HTTP/2 and Protocol Buffers.

**Key characteristics**:
- **HTTP/2 transport**: Multiplexing, header compression, binary framing
- **Protocol Buffers**: Efficient binary serialization (smaller payloads than JSON)
- **Code generation**: Client and server code generated from .proto files
- **Streaming**: Native support for streaming requests and responses
- **Multi-language**: Official support for 10+ languages
- **Type-safe**: Strong typing enforced by Protocol Buffers

**Architecture components**:
```
Client → Stub (Generated) → HTTP/2 → Server → Service Implementation
         ↓                              ↓
    Interceptors                   Interceptors
         ↓                              ↓
    Metadata                       Metadata
```

---

## Protocol Buffers Basics

### Message Definition

```protobuf
// users.proto
syntax = "proto3";

package users.v1;

option go_package = "github.com/example/users/v1;usersv1";

// User represents a user in the system
message User {
  string id = 1;              // Field number (used for encoding)
  string email = 2;
  string name = 3;
  int32 age = 4;
  bool is_active = 5;
  repeated string tags = 6;   // List of strings
  google.protobuf.Timestamp created_at = 7;
}

// CreateUserRequest with nested message
message CreateUserRequest {
  string email = 1;
  string name = 2;
  Profile profile = 3;        // Nested message

  message Profile {
    string bio = 1;
    string avatar_url = 2;
  }
}

message CreateUserResponse {
  User user = 1;
  string message = 2;
}
```

**Key concepts**:
- **Field numbers** (1, 2, 3): Used for encoding (never reuse deleted numbers)
- **Types**: `string`, `int32`, `int64`, `bool`, `bytes`, `float`, `double`
- **repeated**: List/array of values
- **Nested messages**: Messages within messages
- **Imports**: `import "google/protobuf/timestamp.proto";`

### Service Definition (RPC Methods)

```protobuf
// Four types of RPCs
service UserService {
  // Unary: Single request → Single response
  rpc GetUser(GetUserRequest) returns (GetUserResponse);

  // Server streaming: Single request → Stream of responses
  rpc ListUsers(ListUsersRequest) returns (stream User);

  // Client streaming: Stream of requests → Single response
  rpc CreateUsers(stream CreateUserRequest) returns (CreateUsersResponse);

  // Bidirectional streaming: Stream of requests ↔ Stream of responses
  rpc Chat(stream ChatMessage) returns (stream ChatMessage);
}

message GetUserRequest {
  string id = 1;
}

message GetUserResponse {
  User user = 1;
}

message ListUsersRequest {
  int32 page_size = 1;
  string page_token = 2;
}

message CreateUsersResponse {
  repeated User users = 1;
  int32 created_count = 2;
}

message ChatMessage {
  string user_id = 1;
  string content = 2;
  google.protobuf.Timestamp timestamp = 3;
}
```

---

## RPC Types and Implementation

### 1. Unary RPC (Request-Response)

**Pattern**: Client sends one request, server returns one response

**.proto definition**:
```protobuf
rpc GetUser(GetUserRequest) returns (GetUserResponse);
```

**Python server** (grpcio):
```python
import grpc
from concurrent import futures
import users_pb2
import users_pb2_grpc

class UserService(users_pb2_grpc.UserServiceServicer):
    def GetUser(self, request, context):
        # request: GetUserRequest
        # context: grpc.ServicerContext (metadata, peer, etc.)

        user_id = request.id

        # Fetch from database
        user = db.get_user(user_id)

        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f'User {user_id} not found')
            return users_pb2.GetUserResponse()

        # Return response
        return users_pb2.GetUserResponse(
            user=users_pb2.User(
                id=user['id'],
                email=user['email'],
                name=user['name']
            )
        )

# Start server
server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
users_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
server.add_insecure_port('[::]:50051')
server.start()
server.wait_for_termination()
```

**Python client**:
```python
import grpc
import users_pb2
import users_pb2_grpc

# Create channel
channel = grpc.insecure_channel('localhost:50051')
stub = users_pb2_grpc.UserServiceStub(channel)

# Call RPC
try:
    response = stub.GetUser(users_pb2.GetUserRequest(id='123'))
    print(f'User: {response.user.name}')
except grpc.RpcError as e:
    print(f'Error: {e.code()} - {e.details()}')
```

### 2. Server Streaming RPC

**Pattern**: Client sends one request, server streams multiple responses

**.proto definition**:
```protobuf
rpc ListUsers(ListUsersRequest) returns (stream User);
```

**Python server**:
```python
def ListUsers(self, request, context):
    page_size = request.page_size or 50

    # Stream users (yield multiple responses)
    for user in db.list_users(limit=page_size):
        yield users_pb2.User(
            id=user['id'],
            email=user['email'],
            name=user['name']
        )
```

**Python client**:
```python
# Receive stream
response_stream = stub.ListUsers(users_pb2.ListUsersRequest(page_size=10))

for user in response_stream:
    print(f'User: {user.name} ({user.email})')
```

### 3. Client Streaming RPC

**Pattern**: Client streams multiple requests, server returns one response

**.proto definition**:
```protobuf
rpc CreateUsers(stream CreateUserRequest) returns (CreateUsersResponse);
```

**Python server**:
```python
def CreateUsers(self, request_iterator, context):
    created_users = []

    # Receive stream of requests
    for request in request_iterator:
        user = db.create_user(email=request.email, name=request.name)
        created_users.append(user)

    return users_pb2.CreateUsersResponse(
        users=created_users,
        created_count=len(created_users)
    )
```

**Python client**:
```python
def request_generator():
    # Generate stream of requests
    for i in range(5):
        yield users_pb2.CreateUserRequest(
            email=f'user{i}@example.com',
            name=f'User {i}'
        )

# Send stream
response = stub.CreateUsers(request_generator())
print(f'Created {response.created_count} users')
```

### 4. Bidirectional Streaming RPC

**Pattern**: Client and server both stream messages independently

**.proto definition**:
```protobuf
rpc Chat(stream ChatMessage) returns (stream ChatMessage);
```

**Python server**:
```python
def Chat(self, request_iterator, context):
    # Concurrent reading and writing
    for message in request_iterator:
        # Process incoming message
        user_id = message.user_id
        content = message.content

        # Broadcast to other users (example)
        response = users_pb2.ChatMessage(
            user_id='system',
            content=f'{user_id} said: {content}',
            timestamp=Timestamp()
        )
        yield response
```

**Python client**:
```python
def message_generator():
    messages = ['Hello', 'How are you?', 'Goodbye']
    for msg in messages:
        yield users_pb2.ChatMessage(
            user_id='user123',
            content=msg,
            timestamp=Timestamp()
        )

# Bidirectional stream
responses = stub.Chat(message_generator())

for response in responses:
    print(f'{response.user_id}: {response.content}')
```

---

## Error Handling

### gRPC Status Codes

```python
from grpc import StatusCode

# Common status codes
StatusCode.OK               # 0: Success
StatusCode.CANCELLED        # 1: Operation cancelled
StatusCode.INVALID_ARGUMENT # 3: Invalid argument
StatusCode.NOT_FOUND        # 5: Resource not found
StatusCode.ALREADY_EXISTS   # 6: Resource already exists
StatusCode.PERMISSION_DENIED # 7: Permission denied
StatusCode.UNAUTHENTICATED  # 16: Missing authentication
StatusCode.INTERNAL         # 13: Internal error
StatusCode.UNAVAILABLE      # 14: Service unavailable
StatusCode.DEADLINE_EXCEEDED # 4: Deadline exceeded
```

### Server Error Handling

```python
def GetUser(self, request, context):
    try:
        user_id = request.id

        # Validate input
        if not user_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('User ID is required')
            return users_pb2.GetUserResponse()

        # Check authentication
        if not context.metadata().get('authorization'):
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details('Authentication required')
            return users_pb2.GetUserResponse()

        # Fetch user
        user = db.get_user(user_id)

        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f'User {user_id} not found')
            return users_pb2.GetUserResponse()

        return users_pb2.GetUserResponse(user=user)

    except Exception as e:
        context.set_code(grpc.StatusCode.INTERNAL)
        context.set_details(f'Internal error: {str(e)}')
        return users_pb2.GetUserResponse()
```

### Client Error Handling

```python
try:
    response = stub.GetUser(
        users_pb2.GetUserRequest(id='123'),
        timeout=5  # Deadline in seconds
    )
    print(f'User: {response.user.name}')

except grpc.RpcError as e:
    # Handle specific errors
    if e.code() == grpc.StatusCode.NOT_FOUND:
        print('User not found')
    elif e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
        print('Request timeout')
    elif e.code() == grpc.StatusCode.UNAUTHENTICATED:
        print('Authentication required')
    else:
        print(f'Error: {e.code()} - {e.details()}')
```

---

## Interceptors (Middleware)

### Server Interceptor

```python
class LoggingInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        # Before RPC
        method = handler_call_details.method
        print(f'[Server] Received: {method}')

        # Continue to actual RPC
        response = continuation(handler_call_details)

        # After RPC
        print(f'[Server] Completed: {method}')
        return response

# Use interceptor
server = grpc.server(
    futures.ThreadPoolExecutor(max_workers=10),
    interceptors=[LoggingInterceptor()]
)
```

### Client Interceptor

```python
class AuthInterceptor(grpc.UnaryUnaryClientInterceptor):
    def __init__(self, token):
        self.token = token

    def intercept_unary_unary(self, continuation, client_call_details, request):
        # Add authentication metadata
        metadata = []
        if client_call_details.metadata:
            metadata = list(client_call_details.metadata)
        metadata.append(('authorization', f'Bearer {self.token}'))

        # Update call details
        new_details = client_call_details._replace(metadata=metadata)

        # Continue with modified metadata
        return continuation(new_details, request)

# Use interceptor
channel = grpc.insecure_channel('localhost:50051')
intercepted_channel = grpc.intercept_channel(
    channel,
    AuthInterceptor(token='secret-token')
)
stub = users_pb2_grpc.UserServiceStub(intercepted_channel)
```

---

## Common Patterns and Best Practices

### Deadlines (Timeouts)

**Always set deadlines** to prevent hanging requests:

```python
# Client-side deadline
response = stub.GetUser(
    request,
    timeout=5  # 5 seconds
)

# Server-side deadline check
def GetUser(self, request, context):
    if context.time_remaining() < 1:  # Less than 1 second left
        context.set_code(grpc.StatusCode.DEADLINE_EXCEEDED)
        return users_pb2.GetUserResponse()
```

### Metadata (Headers)

```python
# Client: Send metadata
metadata = [
    ('authorization', 'Bearer token123'),
    ('request-id', 'abc-123')
]
response = stub.GetUser(request, metadata=metadata)

# Server: Read metadata
def GetUser(self, request, context):
    metadata = dict(context.invocation_metadata())
    auth_token = metadata.get('authorization')
    request_id = metadata.get('request-id')
```

### Connection Management

```python
# Reuse channels (don't create per-request)
channel = grpc.insecure_channel('localhost:50051')
stub = users_pb2_grpc.UserServiceStub(channel)

# Close when done
channel.close()

# Connection options
channel = grpc.insecure_channel(
    'localhost:50051',
    options=[
        ('grpc.max_receive_message_length', 10 * 1024 * 1024),  # 10 MB
        ('grpc.max_send_message_length', 10 * 1024 * 1024),     # 10 MB
        ('grpc.keepalive_time_ms', 30000),                       # 30 seconds
    ]
)
```

---

## Anti-Patterns

❌ **Not setting deadlines**: Requests can hang forever
✅ Set timeouts: `stub.GetUser(request, timeout=5)`

❌ **Creating channels per request**: Expensive (TCP connection overhead)
✅ Reuse channels: Create once, use many times

❌ **Ignoring status codes**: All errors return same generic message
✅ Handle specific codes: Check `grpc.StatusCode.NOT_FOUND`, etc.

❌ **Large messages**: Sending 100 MB+ messages
✅ Use streaming: Break into smaller chunks

❌ **No error handling in streams**: Stream errors kill connection
✅ Wrap in try/except: Handle `grpc.RpcError`

❌ **Missing field numbers**: Can't decode old messages
✅ Never reuse field numbers: Mark as `reserved`

❌ **Breaking changes**: Removing required fields
✅ Use proto evolution: Add fields, use `reserved`, deprecate

---

## Related Skills

- `protobuf-schema-design.md` - Advanced Protocol Buffers patterns
- `grpc-load-balancing.md` - Client-side and proxy load balancing
- `grpc-security.md` - TLS, authentication, authorization
- `http2-fundamentals.md` - Understanding HTTP/2 (gRPC transport)
- `api-rest-design.md` - Comparing REST vs gRPC

---

## Level 3: Resources

### Overview

This skill includes comprehensive Level 3 resources for deep gRPC implementation knowledge and practical tools.

**Resources include**:
- **REFERENCE.md** (2,303 lines): Complete technical reference covering all gRPC concepts
- **3 executable scripts**: Proto validation, client generation, server testing
- **8 production examples**: Complete implementations across multiple languages

### REFERENCE.md

**Location**: `skills/protocols/grpc-implementation/resources/REFERENCE.md`

**Comprehensive technical reference** (2,303 lines) covering:

**Core Topics**:
- gRPC fundamentals and architecture
- Protocol Buffers (syntax, types, evolution)
- Service definitions and RPC types
- Error handling and status codes
- Interceptors and middleware
- Metadata and headers
- Deadlines and timeouts
- Load balancing strategies
- Security (TLS, authentication)
- Performance optimization
- Streaming patterns
- Testing strategies
- Debugging tools
- Migration strategies
- Anti-patterns
- Language-specific guides (Python, Go, Node.js)

**Key Sections**:
1. **Fundamentals**: HTTP/2 transport, Protocol Buffers, code generation
2. **Protocol Buffers**: Complete syntax guide, field types, schema evolution
3. **RPC Types**: All four types with complete implementations (unary, server streaming, client streaming, bidirectional)
4. **Error Handling**: Status codes, rich error details, retry strategies
5. **Interceptors**: Server and client interceptors for cross-cutting concerns
6. **Load Balancing**: Client-side and proxy-based strategies
7. **Security**: TLS/mTLS, token-based auth, OAuth 2.0
8. **Performance**: Connection pooling, compression, keepalive
9. **Tools**: grpcurl, buf, grpc-gateway, health probes
10. **Anti-Patterns**: Common mistakes and solutions

**Format**: Markdown with extensive code examples in Python, Go, and Node.js

### Scripts

Three production-ready executable scripts in `resources/scripts/`:

#### 1. validate_proto.py (687 lines)

**Purpose**: Validate Protocol Buffer definitions

**Features**:
- Parse and validate .proto syntax
- Check naming conventions (PascalCase messages, snake_case fields)
- Detect breaking changes between versions
- Validate service definitions
- Check best practices (reserved fields, deprecation)
- Output as JSON or human-readable text

**Usage**:
```bash
# Basic validation
./validate_proto.py --proto-file api.proto

# JSON output
./validate_proto.py --proto-file api.proto --json

# Check breaking changes
./validate_proto.py --proto-file api_v2.proto --check-breaking --baseline api_v1.proto

# Save report
./validate_proto.py --proto-file api.proto --json > validation-report.json
```

**Categories checked**:
- **Syntax**: Proto syntax errors, duplicate field numbers, reserved ranges
- **Naming**: Convention violations (PascalCase, snake_case)
- **Best practices**: Missing options, field number efficiency, request/response patterns
- **Breaking changes**: Deleted messages/services, changed types, reused field numbers

#### 2. generate_client.py (906 lines)

**Purpose**: Generate gRPC client code and examples

**Features**:
- Generate client code for Python, Go, Node.js
- Include example usage code
- Add error handling patterns
- Generate interceptor templates
- Create testing helpers
- Support multiple output formats

**Usage**:
```bash
# Generate Python client
./generate_client.py --proto-file api.proto --language python --output-dir ./client

# Generate Go client
./generate_client.py --proto-file api.proto --language go --output-dir ./client

# JSON output (list generated files)
./generate_client.py --proto-file api.proto --language python --json
```

**Generated files**:
- **Python**: client.py, example.py, interceptor.py, test_client.py
- **Go**: client.go, example.go
- **Node.js**: client.js, example.js

**Includes**: Error handling, retry logic, connection management, interceptors

#### 3. test_grpc_server.sh (643 lines)

**Purpose**: Test gRPC server endpoints and performance

**Features**:
- Test all four RPC types
- Measure latency and throughput
- Test error handling
- Validate metadata
- Generate test reports (JSON or text)
- Performance benchmarking

**Usage**:
```bash
# Test all methods
./test_grpc_server.sh --server localhost:50051 --proto-file api.proto

# Test specific method
./test_grpc_server.sh --server localhost:50051 --proto-file api.proto --method UserService/GetUser

# With metadata (authentication)
./test_grpc_server.sh --server localhost:50051 --proto-file api.proto --metadata authorization:"Bearer token123"

# JSON output for CI/CD
./test_grpc_server.sh --server localhost:50051 --proto-file api.proto --json > report.json

# Performance test (100 iterations)
./test_grpc_server.sh --server localhost:50051 --proto-file api.proto --iterations 100
```

**Requirements**: grpcurl, jq, bc

**Metrics**: Latency (min, avg, p50, p95, p99, max), throughput (req/sec), success rate

### Examples

Eight production-ready examples in `resources/examples/`:

#### 1. protos/service.proto

Complete service definition demonstrating:
- All four RPC types (unary, server streaming, client streaming, bidirectional)
- Domain models (User, UserStatus)
- Request/response messages
- Enums and oneof types
- Well-known types (Timestamp, Empty)
- Complete CRUD operations plus streaming

**Services**: UserService with 10 methods covering all RPC patterns

#### 2. python/server.py

Complete Python gRPC server implementation:
- All four RPC types implemented
- In-memory database (example)
- Error handling with proper status codes
- Input validation
- Metadata handling
- Authentication checks
- Comprehensive logging
- Context management

**Key features**: Unary CRUD, server streaming (ListUsers, WatchUserChanges), client streaming (CreateUsers, UploadUserData), bidirectional (Chat, CollaborativeEdit)

#### 3. python/client.py

Complete Python gRPC client implementation:
- Test functions for all RPC types
- Error handling with retries
- Timeout configuration
- Metadata support
- Comprehensive examples
- Test suite for error cases

**Tests**: Unary RPCs, server streaming, client streaming, bidirectional streaming, error handling

#### 4. go/server.go

Go gRPC server implementation (template):
- Type-safe implementation
- Context handling
- Error handling with status package
- Connection management

**Format**: Production-ready Go server template

#### 5. nodejs/server.js

Node.js gRPC server implementation (template):
- Async/await patterns
- Callback-based RPCs
- Error handling
- Proto loading with grpc-js

**Format**: Production-ready Node.js server template

#### 6. interceptors/auth_interceptor.py

Authentication interceptor example:
- **Server interceptor**: JWT validation, public methods whitelist, UNAUTHENTICATED errors
- **Client interceptor**: Automatic token addition, metadata management
- Token generation utilities
- Complete JWT flow example

**Features**: JWT authentication, token validation, expiration handling, public endpoint support

#### 7. streaming/bidirectional_chat.py

Bidirectional streaming example (template):
- Chat room implementation
- Concurrent send/receive
- Connection management
- Message broadcasting

**Pattern**: Full duplex communication for real-time chat

#### 8. docker/docker-compose.yml

Production Docker deployment:
- gRPC server container
- gRPC client container
- grpcurl for testing
- Health checks
- Service networking
- Volume mounts for code
- Automatic code generation

**Services**: grpc-server (Python), grpc-client (Python), grpcurl (testing)

**Features**: Health checks, service discovery, logging, production notes for TLS/auth

### Quick Start

**1. Validate your .proto file**:
```bash
cd skills/protocols/grpc-implementation/resources/scripts
./validate_proto.py --proto-file ../examples/protos/service.proto --json
```

**2. Generate client code**:
```bash
./generate_client.py --proto-file ../examples/protos/service.proto --language python --output-dir ./client
```

**3. Run examples**:
```bash
cd ../examples

# Generate stubs
python -m grpc_tools.protoc -I./protos --python_out=./python --grpc_python_out=./python protos/service.proto

# Start server
python python/server.py

# Run client (in another terminal)
python python/client.py
```

**4. Test with Docker**:
```bash
cd docker
docker-compose up
```

**5. Test server**:
```bash
cd scripts
./test_grpc_server.sh --server localhost:50051 --proto-file ../examples/protos/service.proto --json
```

### File Structure

```
skills/protocols/grpc-implementation/
├── grpc-implementation.md (this file)
└── resources/
    ├── REFERENCE.md (2,303 lines)
    ├── scripts/
    │   ├── validate_proto.py (687 lines) - Proto validation
    │   ├── generate_client.py (906 lines) - Client generation
    │   └── test_grpc_server.sh (643 lines) - Server testing
    └── examples/
        ├── protos/
        │   └── service.proto - Complete service definition
        ├── python/
        │   ├── server.py - Python server (all RPC types)
        │   └── client.py - Python client (all RPC types)
        ├── go/
        │   └── server.go - Go server template
        ├── nodejs/
        │   └── server.js - Node.js server template
        ├── interceptors/
        │   └── auth_interceptor.py - JWT authentication
        ├── streaming/
        │   └── bidirectional_chat.py - Chat example
        └── docker/
            └── docker-compose.yml - Docker deployment
```

### Resources Summary

| Category | Item | Lines | Description |
|----------|------|-------|-------------|
| **Reference** | REFERENCE.md | 2,303 | Complete technical reference |
| **Scripts** | validate_proto.py | 687 | Proto validation tool |
| | generate_client.py | 906 | Client code generator |
| | test_grpc_server.sh | 643 | Server testing tool |
| **Examples** | service.proto | 156 | Complete service definition |
| | python/server.py | 450 | Python server implementation |
| | python/client.py | 280 | Python client implementation |
| | auth_interceptor.py | 240 | JWT authentication example |
| | docker-compose.yml | 90 | Docker deployment |

**Total**: 5,755 lines of production-ready resources

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
