# gRPC Implementation Reference

**Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: ~2,800

This comprehensive reference covers gRPC implementation from fundamentals to advanced patterns.

---

## Table of Contents

1. [gRPC Fundamentals](#1-grpc-fundamentals)
2. [Protocol Buffers](#2-protocol-buffers)
3. [Service Definition](#3-service-definition)
4. [RPC Types](#4-rpc-types)
5. [Error Handling](#5-error-handling)
6. [Interceptors and Middleware](#6-interceptors-and-middleware)
7. [Metadata](#7-metadata)
8. [Deadlines and Timeouts](#8-deadlines-and-timeouts)
9. [Load Balancing](#9-load-balancing)
10. [Security (TLS, Auth)](#10-security-tls-auth)
11. [Performance Optimization](#11-performance-optimization)
12. [Streaming Patterns](#12-streaming-patterns)
13. [Testing](#13-testing)
14. [Tooling](#14-tooling)
15. [Migration Strategies](#15-migration-strategies)
16. [Anti-Patterns](#16-anti-patterns)
17. [Language-Specific Guides](#17-language-specific-guides)
18. [References](#18-references)

---

## 1. gRPC Fundamentals

### What is gRPC?

**gRPC** (gRPC Remote Procedure Call) is a modern, high-performance RPC framework that uses HTTP/2 for transport, Protocol Buffers for serialization, and provides features like streaming, flow control, and bidirectional communication.

**Key characteristics**:
- **HTTP/2 transport**: Multiplexing, header compression, binary framing
- **Protocol Buffers**: Efficient binary serialization (smaller than JSON)
- **Code generation**: Client and server stubs generated from .proto files
- **Streaming**: Native support for streaming in both directions
- **Multi-language**: Official support for C++, C#, Go, Java, Node.js, PHP, Python, Ruby, Objective-C, Dart
- **Type-safe**: Strong typing enforced by Protocol Buffers
- **Deadline propagation**: Built-in timeout handling
- **Cancellation**: Request cancellation support

### Architecture Overview

```
┌─────────────┐                                    ┌─────────────┐
│   Client    │                                    │   Server    │
│             │                                    │             │
│  ┌───────┐  │                                    │  ┌───────┐  │
│  │  App  │  │                                    │  │  App  │  │
│  └───┬───┘  │                                    │  └───▲───┘  │
│      │      │                                    │      │      │
│  ┌───▼───┐  │      ┌──────────────────┐         │  ┌───┴───┐  │
│  │ Stub  │◄─┼──────┤ Protocol Buffers │─────────┼─►│Service│  │
│  │(Gen'd)│  │      └──────────────────┘         │  │(Gen'd)│  │
│  └───┬───┘  │                                    │  └───▲───┘  │
│      │      │                                    │      │      │
│  ┌───▼──────▼───────────────────────────────────▼──────┴───┐  │
│  │                    HTTP/2 Transport                      │  │
│  │  • Multiplexing    • Header Compression                 │  │
│  │  • Flow Control    • Binary Framing                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────┘                                    └─────────────┘
```

### gRPC vs REST

| Feature | gRPC | REST |
|---------|------|------|
| **Protocol** | HTTP/2 | HTTP/1.1 (or HTTP/2) |
| **Payload** | Protobuf (binary) | JSON (text) |
| **Schema** | Strict (.proto) | Flexible (OpenAPI optional) |
| **Streaming** | Native (4 types) | Limited (SSE, WebSocket) |
| **Code Gen** | Built-in | Third-party (OpenAPI) |
| **Browser Support** | Limited (grpc-web) | Full |
| **Performance** | High (binary, HTTP/2) | Lower (text, HTTP/1.1) |
| **Human Readable** | No (binary) | Yes (JSON) |
| **Use Case** | Microservices, internal APIs | Public APIs, web services |

**When to use gRPC**:
- Microservice-to-microservice communication
- Real-time bidirectional streaming
- Polyglot environments (multiple languages)
- Performance-critical applications
- Internal APIs with known clients

**When to use REST**:
- Public APIs for web/mobile
- Browser-based clients (direct)
- Simple CRUD operations
- Human-readable debugging
- Wide compatibility requirements

### HTTP/2 Benefits for gRPC

1. **Multiplexing**: Multiple RPCs over single TCP connection
2. **Header compression** (HPACK): Reduces overhead
3. **Binary framing**: Efficient parsing
4. **Server push**: Server-initiated streams (not used in gRPC)
5. **Flow control**: Prevents overwhelming slow clients
6. **Prioritization**: Important requests first

---

## 2. Protocol Buffers

### Syntax Basics

**File structure**:
```protobuf
// users.proto
syntax = "proto3";  // Use proto3 (recommended)

package users.v1;   // Namespace

option go_package = "github.com/example/users/v1;usersv1";
option java_package = "com.example.users.v1";
option java_multiple_files = true;

import "google/protobuf/timestamp.proto";
import "google/protobuf/empty.proto";

// Message definition
message User {
  string id = 1;
  string email = 2;
  string name = 3;
}

// Service definition
service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
}
```

### Data Types

**Scalar types**:

| Proto Type | C++ | Java | Python | Go | Notes |
|------------|-----|------|--------|----|-|
| `double` | double | double | float | float64 | |
| `float` | float | float | float | float32 | |
| `int32` | int32 | int | int | int32 | Variable-length encoding |
| `int64` | int64 | long | int/long | int64 | Variable-length encoding |
| `uint32` | uint32 | int | int/long | uint32 | Variable-length encoding |
| `uint64` | uint64 | long | int/long | uint64 | Variable-length encoding |
| `sint32` | int32 | int | int | int32 | Variable-length, efficient for negatives |
| `sint64` | int64 | long | int/long | int64 | Variable-length, efficient for negatives |
| `fixed32` | uint32 | int | int | uint32 | Fixed 4 bytes, efficient for large values |
| `fixed64` | uint64 | long | int/long | uint64 | Fixed 8 bytes |
| `bool` | bool | boolean | bool | bool | |
| `string` | string | String | str/unicode | string | UTF-8 or 7-bit ASCII |
| `bytes` | string | ByteString | str | []byte | Arbitrary byte sequence |

**Proto3 defaults**:
- Numbers: `0`
- Booleans: `false`
- Strings: `""` (empty)
- Enums: First value (must be 0)
- Messages: Language-specific (e.g., `nil` in Go)

### Messages

**Basic message**:
```protobuf
message User {
  string id = 1;           // Field number 1
  string email = 2;        // Field number 2
  string name = 3;
  int32 age = 4;
  bool is_active = 5;
}
```

**Field numbers**:
- **1-15**: 1 byte to encode (use for frequent fields)
- **16-2047**: 2 bytes to encode
- **19000-19999**: Reserved (cannot use)
- **Max**: 2^29 - 1 (536,870,911)

**Never reuse field numbers**: Old clients will misinterpret data.

**Repeated fields** (lists/arrays):
```protobuf
message User {
  string id = 1;
  repeated string tags = 2;       // List of strings
  repeated Address addresses = 3; // List of messages
}
```

**Nested messages**:
```protobuf
message User {
  string id = 1;
  Profile profile = 2;

  message Profile {
    string bio = 1;
    string avatar_url = 2;
  }
}
```

**Maps**:
```protobuf
message User {
  string id = 1;
  map<string, string> metadata = 2;  // Key-value pairs
  map<int32, Address> addresses = 3; // Integer keys
}
```

**Oneof** (union types):
```protobuf
message SearchResult {
  oneof result {
    User user = 1;
    Post post = 2;
    Comment comment = 3;
  }
}
// Only one field can be set at a time
```

**Enums**:
```protobuf
enum Status {
  STATUS_UNSPECIFIED = 0;  // First value MUST be 0
  STATUS_ACTIVE = 1;
  STATUS_INACTIVE = 2;
  STATUS_DELETED = 3;
}

message User {
  string id = 1;
  Status status = 2;
}
```

**Well-known types** (Google):
```protobuf
import "google/protobuf/timestamp.proto";
import "google/protobuf/duration.proto";
import "google/protobuf/empty.proto";
import "google/protobuf/wrappers.proto";

message Event {
  google.protobuf.Timestamp created_at = 1;
  google.protobuf.Duration timeout = 2;
  google.protobuf.Int32Value optional_count = 3;  // Distinguish 0 from unset
}
```

### Reserved Fields

**Prevent field number reuse**:
```protobuf
message User {
  reserved 2, 15, 9 to 11;           // Reserved field numbers
  reserved "old_field", "deprecated"; // Reserved field names

  string id = 1;
  string email = 3;  // Cannot use 2 (reserved)
}
```

**Why reserve**:
- Prevents accidental reuse of deleted fields
- Old clients reading new messages won't misinterpret data
- Essential for backward compatibility

### Proto Evolution (Backward Compatibility)

**Safe changes**:
- ✅ Add new fields
- ✅ Add new methods to services
- ✅ Add new values to enums (at end)
- ✅ Mark fields as `reserved`
- ✅ Change field names (field numbers matter, not names)

**Breaking changes** (avoid):
- ❌ Change field number
- ❌ Change field type
- ❌ Delete field without reserving
- ❌ Change message name (if used in service definition)
- ❌ Change `repeated` to singular or vice versa

**Example: Safe evolution**:
```protobuf
// Version 1
message User {
  string id = 1;
  string email = 2;
}

// Version 2 (safe: added fields)
message User {
  string id = 1;
  string email = 2;
  string name = 3;        // New field (safe)
  int32 age = 4;          // New field (safe)
}

// Version 3 (safe: deprecated field)
message User {
  string id = 1;
  string email = 2;
  string name = 3;
  reserved 4;             // Deprecated age (safe)
  google.protobuf.Timestamp birth_date = 5;  // Replacement
}
```

### Imports

```protobuf
// common.proto
syntax = "proto3";
package common;

message Address {
  string street = 1;
  string city = 2;
  string country = 3;
}

// users.proto
syntax = "proto3";
package users;

import "common.proto";  // Import other .proto files

message User {
  string id = 1;
  common.Address address = 2;  // Use imported message
}
```

---

## 3. Service Definition

### Basic Service

```protobuf
service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
  rpc CreateUser(CreateUserRequest) returns (CreateUserResponse);
  rpc UpdateUser(UpdateUserRequest) returns (UpdateUserResponse);
  rpc DeleteUser(DeleteUserRequest) returns (google.protobuf.Empty);
}
```

### Request/Response Pattern

**Best practice**: Create specific request/response messages (not reuse domain messages)

```protobuf
// ✅ GOOD: Explicit request/response messages
message GetUserRequest {
  string id = 1;
}

message GetUserResponse {
  User user = 1;
  string message = 2;
}

// ❌ BAD: Reusing domain message as response
rpc GetUser(GetUserRequest) returns (User);  // Less flexible
```

**Why explicit messages**:
- Allows adding metadata (e.g., `message`, `pagination`)
- Enables future evolution without breaking changes
- Clearer API contract

### Service Naming Conventions

**Protobuf style guide**:
- **Services**: PascalCase, suffix with `Service` (e.g., `UserService`)
- **Methods**: PascalCase, verb + noun (e.g., `GetUser`, `ListPosts`)
- **Messages**: PascalCase (e.g., `User`, `GetUserRequest`)
- **Fields**: snake_case (e.g., `user_id`, `created_at`)
- **Enums**: SCREAMING_SNAKE_CASE (e.g., `STATUS_ACTIVE`)

**Common method prefixes**:
- `Get`: Retrieve single resource (unary)
- `List`: Retrieve multiple resources (unary or server streaming)
- `Create`: Create new resource
- `Update`: Update existing resource
- `Delete`: Delete resource
- `Search`: Search resources
- `Watch`: Monitor changes (server streaming)

---

## 4. RPC Types

### 1. Unary RPC

**Pattern**: Client sends one request → Server returns one response

**Definition**:
```protobuf
rpc GetUser(GetUserRequest) returns (GetUserResponse);
```

**Python implementation**:
```python
# Server
class UserService(users_pb2_grpc.UserServiceServicer):
    def GetUser(self, request, context):
        user_id = request.id
        user = db.get_user(user_id)

        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f'User {user_id} not found')
            return users_pb2.GetUserResponse()

        return users_pb2.GetUserResponse(
            user=users_pb2.User(id=user['id'], name=user['name'])
        )

# Client
response = stub.GetUser(users_pb2.GetUserRequest(id='123'))
print(response.user.name)
```

**Go implementation**:
```go
// Server
func (s *server) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.GetUserResponse, error) {
    user, err := db.GetUser(req.Id)
    if err != nil {
        return nil, status.Errorf(codes.NotFound, "user %s not found", req.Id)
    }

    return &pb.GetUserResponse{
        User: &pb.User{
            Id:   user.ID,
            Name: user.Name,
        },
    }, nil
}

// Client
resp, err := client.GetUser(ctx, &pb.GetUserRequest{Id: "123"})
if err != nil {
    log.Fatalf("Error: %v", err)
}
fmt.Println(resp.User.Name)
```

**Node.js implementation**:
```javascript
// Server
function getUser(call, callback) {
    const userId = call.request.id;
    db.getUser(userId, (err, user) => {
        if (err) {
            callback({
                code: grpc.status.NOT_FOUND,
                message: `User ${userId} not found`
            });
            return;
        }

        callback(null, {
            user: { id: user.id, name: user.name }
        });
    });
}

// Client
client.getUser({ id: '123' }, (err, response) => {
    if (err) {
        console.error(err);
        return;
    }
    console.log(response.user.name);
});
```

**Use cases**:
- Simple request-response APIs
- CRUD operations
- Authentication
- Single resource retrieval

---

### 2. Server Streaming RPC

**Pattern**: Client sends one request → Server streams multiple responses

**Definition**:
```protobuf
rpc ListUsers(ListUsersRequest) returns (stream User);
```

**Python implementation**:
```python
# Server
def ListUsers(self, request, context):
    page_size = request.page_size or 50

    # Stream users (yield multiple responses)
    for user in db.list_users(limit=page_size):
        yield users_pb2.User(
            id=user['id'],
            email=user['email'],
            name=user['name']
        )

# Client
response_stream = stub.ListUsers(users_pb2.ListUsersRequest(page_size=10))
for user in response_stream:
    print(f'User: {user.name} ({user.email})')
```

**Go implementation**:
```go
// Server
func (s *server) ListUsers(req *pb.ListUsersRequest, stream pb.UserService_ListUsersServer) error {
    users, err := db.ListUsers(req.PageSize)
    if err != nil {
        return err
    }

    for _, user := range users {
        if err := stream.Send(&pb.User{
            Id:   user.ID,
            Name: user.Name,
        }); err != nil {
            return err
        }
    }

    return nil
}

// Client
stream, err := client.ListUsers(ctx, &pb.ListUsersRequest{PageSize: 10})
if err != nil {
    log.Fatal(err)
}

for {
    user, err := stream.Recv()
    if err == io.EOF {
        break
    }
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(user.Name)
}
```

**Node.js implementation**:
```javascript
// Server
function listUsers(call) {
    const pageSize = call.request.page_size || 50;

    db.listUsers(pageSize, (err, users) => {
        if (err) {
            call.emit('error', err);
            return;
        }

        users.forEach(user => {
            call.write({ id: user.id, name: user.name });
        });

        call.end();
    });
}

// Client
const call = client.listUsers({ page_size: 10 });

call.on('data', (user) => {
    console.log(user.name);
});

call.on('end', () => {
    console.log('Stream ended');
});

call.on('error', (err) => {
    console.error(err);
});
```

**Use cases**:
- Pagination (large result sets)
- Real-time data feeds (stock prices, sensor data)
- Log streaming
- File downloads (chunked)
- Progressive results

**Benefits**:
- Memory efficient (don't load all data at once)
- Lower latency (client receives first results immediately)
- Backpressure support (flow control)

---

### 3. Client Streaming RPC

**Pattern**: Client streams multiple requests → Server returns one response

**Definition**:
```protobuf
rpc CreateUsers(stream CreateUserRequest) returns (CreateUsersResponse);
```

**Python implementation**:
```python
# Server
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

# Client
def request_generator():
    for i in range(5):
        yield users_pb2.CreateUserRequest(
            email=f'user{i}@example.com',
            name=f'User {i}'
        )

response = stub.CreateUsers(request_generator())
print(f'Created {response.created_count} users')
```

**Go implementation**:
```go
// Server
func (s *server) CreateUsers(stream pb.UserService_CreateUsersServer) error {
    var users []*pb.User

    for {
        req, err := stream.Recv()
        if err == io.EOF {
            // End of stream
            return stream.SendAndClose(&pb.CreateUsersResponse{
                Users:        users,
                CreatedCount: int32(len(users)),
            })
        }
        if err != nil {
            return err
        }

        user, err := db.CreateUser(req.Email, req.Name)
        if err != nil {
            return err
        }

        users = append(users, &pb.User{
            Id:   user.ID,
            Name: user.Name,
        })
    }
}

// Client
stream, err := client.CreateUsers(ctx)
if err != nil {
    log.Fatal(err)
}

for i := 0; i < 5; i++ {
    if err := stream.Send(&pb.CreateUserRequest{
        Email: fmt.Sprintf("user%d@example.com", i),
        Name:  fmt.Sprintf("User %d", i),
    }); err != nil {
        log.Fatal(err)
    }
}

resp, err := stream.CloseAndRecv()
if err != nil {
    log.Fatal(err)
}
fmt.Printf("Created %d users\n", resp.CreatedCount)
```

**Use cases**:
- Batch operations (bulk inserts)
- File uploads (chunked)
- Log aggregation
- Metrics collection
- Data import

---

### 4. Bidirectional Streaming RPC

**Pattern**: Client and server both stream messages independently

**Definition**:
```protobuf
rpc Chat(stream ChatMessage) returns (stream ChatMessage);
```

**Python implementation**:
```python
# Server
def Chat(self, request_iterator, context):
    for message in request_iterator:
        # Process incoming message
        user_id = message.user_id
        content = message.content

        # Echo back (or broadcast to other users)
        response = users_pb2.ChatMessage(
            user_id='system',
            content=f'{user_id}: {content}',
            timestamp=Timestamp()
        )
        yield response

# Client
def message_generator():
    messages = ['Hello', 'How are you?', 'Goodbye']
    for msg in messages:
        yield users_pb2.ChatMessage(
            user_id='user123',
            content=msg,
            timestamp=Timestamp()
        )

responses = stub.Chat(message_generator())
for response in responses:
    print(f'{response.user_id}: {response.content}')
```

**Go implementation**:
```go
// Server
func (s *server) Chat(stream pb.UserService_ChatServer) error {
    for {
        msg, err := stream.Recv()
        if err == io.EOF {
            return nil
        }
        if err != nil {
            return err
        }

        // Echo back
        response := &pb.ChatMessage{
            UserId:  "system",
            Content: fmt.Sprintf("%s: %s", msg.UserId, msg.Content),
        }

        if err := stream.Send(response); err != nil {
            return err
        }
    }
}

// Client
stream, err := client.Chat(ctx)
if err != nil {
    log.Fatal(err)
}

// Send messages in goroutine
go func() {
    messages := []string{"Hello", "How are you?", "Goodbye"}
    for _, msg := range messages {
        if err := stream.Send(&pb.ChatMessage{
            UserId:  "user123",
            Content: msg,
        }); err != nil {
            log.Fatal(err)
        }
    }
    stream.CloseSend()
}()

// Receive messages
for {
    msg, err := stream.Recv()
    if err == io.EOF {
        break
    }
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("%s: %s\n", msg.UserId, msg.Content)
}
```

**Node.js implementation**:
```javascript
// Server
function chat(call) {
    call.on('data', (message) => {
        // Echo back
        call.write({
            user_id: 'system',
            content: `${message.user_id}: ${message.content}`
        });
    });

    call.on('end', () => {
        call.end();
    });
}

// Client
const call = client.chat();

call.on('data', (message) => {
    console.log(`${message.user_id}: ${message.content}`);
});

call.on('end', () => {
    console.log('Chat ended');
});

// Send messages
['Hello', 'How are you?', 'Goodbye'].forEach(msg => {
    call.write({ user_id: 'user123', content: msg });
});

call.end();
```

**Use cases**:
- Chat applications
- Real-time collaboration
- Live game state synchronization
- Bidirectional sensor data
- Interactive terminals

---

## 5. Error Handling

### gRPC Status Codes

**Standard codes** (from `google.rpc.Code`):

| Code | HTTP | Description | Use Case |
|------|------|-------------|----------|
| `OK` (0) | 200 | Success | Successful operation |
| `CANCELLED` (1) | 499 | Operation cancelled by client | Client cancelled request |
| `UNKNOWN` (2) | 500 | Unknown error | Unhandled exception |
| `INVALID_ARGUMENT` (3) | 400 | Invalid argument | Validation failed |
| `DEADLINE_EXCEEDED` (4) | 504 | Timeout exceeded | Request took too long |
| `NOT_FOUND` (5) | 404 | Resource not found | Entity doesn't exist |
| `ALREADY_EXISTS` (6) | 409 | Resource already exists | Duplicate creation |
| `PERMISSION_DENIED` (7) | 403 | Permission denied | Not authorized |
| `RESOURCE_EXHAUSTED` (8) | 429 | Rate limit or quota | Too many requests |
| `FAILED_PRECONDITION` (9) | 400 | Precondition failed | System state invalid |
| `ABORTED` (10) | 409 | Operation aborted | Conflict (e.g., lock) |
| `OUT_OF_RANGE` (11) | 400 | Out of range | Index/offset invalid |
| `UNIMPLEMENTED` (12) | 501 | Not implemented | Method not supported |
| `INTERNAL` (13) | 500 | Internal error | Server bug |
| `UNAVAILABLE` (14) | 503 | Service unavailable | Temporary failure |
| `DATA_LOSS` (15) | 500 | Data loss | Unrecoverable data loss |
| `UNAUTHENTICATED` (16) | 401 | Unauthenticated | Missing credentials |

### Server-Side Error Handling

**Python example**:
```python
import grpc
from grpc import StatusCode

def GetUser(self, request, context):
    try:
        # Validate input
        if not request.id:
            context.set_code(StatusCode.INVALID_ARGUMENT)
            context.set_details('User ID is required')
            return users_pb2.GetUserResponse()

        # Check authentication
        auth_metadata = dict(context.invocation_metadata())
        if 'authorization' not in auth_metadata:
            context.set_code(StatusCode.UNAUTHENTICATED)
            context.set_details('Authentication required')
            return users_pb2.GetUserResponse()

        # Check authorization
        if not self.is_authorized(auth_metadata, request.id):
            context.set_code(StatusCode.PERMISSION_DENIED)
            context.set_details('You do not have permission to access this user')
            return users_pb2.GetUserResponse()

        # Fetch user
        user = db.get_user(request.id)
        if not user:
            context.set_code(StatusCode.NOT_FOUND)
            context.set_details(f'User {request.id} not found')
            return users_pb2.GetUserResponse()

        return users_pb2.GetUserResponse(
            user=users_pb2.User(
                id=user['id'],
                name=user['name']
            )
        )

    except db.ConnectionError:
        context.set_code(StatusCode.UNAVAILABLE)
        context.set_details('Database temporarily unavailable')
        return users_pb2.GetUserResponse()

    except Exception as e:
        context.set_code(StatusCode.INTERNAL)
        context.set_details(f'Internal error: {str(e)}')
        return users_pb2.GetUserResponse()
```

**Go example**:
```go
import (
    "google.golang.org/grpc/codes"
    "google.golang.org/grpc/status"
)

func (s *server) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.GetUserResponse, error) {
    // Validate input
    if req.Id == "" {
        return nil, status.Error(codes.InvalidArgument, "user ID is required")
    }

    // Check authentication
    md, ok := metadata.FromIncomingContext(ctx)
    if !ok || len(md["authorization"]) == 0 {
        return nil, status.Error(codes.Unauthenticated, "authentication required")
    }

    // Fetch user
    user, err := db.GetUser(req.Id)
    if err == db.ErrNotFound {
        return nil, status.Errorf(codes.NotFound, "user %s not found", req.Id)
    }
    if err != nil {
        return nil, status.Error(codes.Internal, "internal error")
    }

    return &pb.GetUserResponse{
        User: &pb.User{
            Id:   user.ID,
            Name: user.Name,
        },
    }, nil
}
```

### Client-Side Error Handling

**Python example**:
```python
import grpc

try:
    response = stub.GetUser(
        users_pb2.GetUserRequest(id='123'),
        timeout=5  # Deadline
    )
    print(f'User: {response.user.name}')

except grpc.RpcError as e:
    code = e.code()
    details = e.details()

    if code == grpc.StatusCode.NOT_FOUND:
        print(f'User not found: {details}')
    elif code == grpc.StatusCode.DEADLINE_EXCEEDED:
        print('Request timeout')
    elif code == grpc.StatusCode.UNAUTHENTICATED:
        print('Authentication required')
    elif code == grpc.StatusCode.PERMISSION_DENIED:
        print(f'Permission denied: {details}')
    elif code == grpc.StatusCode.UNAVAILABLE:
        print('Service unavailable, retrying...')
    else:
        print(f'Error: {code} - {details}')
```

**Go example**:
```go
resp, err := client.GetUser(ctx, &pb.GetUserRequest{Id: "123"})
if err != nil {
    st, ok := status.FromError(err)
    if !ok {
        log.Fatalf("Unknown error: %v", err)
    }

    switch st.Code() {
    case codes.NotFound:
        log.Printf("User not found: %s", st.Message())
    case codes.DeadlineExceeded:
        log.Println("Request timeout")
    case codes.Unauthenticated:
        log.Println("Authentication required")
    case codes.PermissionDenied:
        log.Printf("Permission denied: %s", st.Message())
    case codes.Unavailable:
        log.Println("Service unavailable")
    default:
        log.Fatalf("Error: %v - %s", st.Code(), st.Message())
    }
    return
}

fmt.Println(resp.User.Name)
```

### Rich Error Details

**Using `google.rpc.Status`** for structured error details:

```protobuf
// Import error details
import "google/rpc/status.proto";
import "google/rpc/error_details.proto";
```

**Python server**:
```python
from google.rpc import error_details_pb2, status_pb2

def CreateUser(self, request, context):
    # Validate
    errors = []
    if not request.email:
        errors.append(('email', 'Email is required'))
    if not request.name:
        errors.append(('name', 'Name is required'))

    if errors:
        # Create rich error details
        bad_request = error_details_pb2.BadRequest()
        for field, message in errors:
            violation = bad_request.field_violations.add()
            violation.field = field
            violation.description = message

        # Set error with details
        rich_status = status_pb2.Status(
            code=3,  # INVALID_ARGUMENT
            message='Validation failed',
            details=[bad_request.SerializeToString()]
        )

        context.abort_with_status(rpc_status.to_status(rich_status))

    # ... create user
```

---

## 6. Interceptors and Middleware

### Server Interceptors

**Python - Logging interceptor**:
```python
import grpc
import time
import logging

class LoggingInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        method = handler_call_details.method
        start_time = time.time()

        logging.info(f'[gRPC] Started: {method}')

        # Continue to actual RPC
        response = continuation(handler_call_details)

        duration = time.time() - start_time
        logging.info(f'[gRPC] Completed: {method} ({duration:.3f}s)')

        return response

# Use interceptor
server = grpc.server(
    futures.ThreadPoolExecutor(max_workers=10),
    interceptors=[LoggingInterceptor()]
)
```

**Python - Authentication interceptor**:
```python
class AuthInterceptor(grpc.ServerInterceptor):
    def __init__(self, secret_key):
        self.secret_key = secret_key

    def intercept_service(self, continuation, handler_call_details):
        # Extract metadata
        metadata = dict(handler_call_details.invocation_metadata())
        token = metadata.get('authorization', '')

        # Validate token
        if not self.validate_token(token):
            return grpc.unary_unary_rpc_method_handler(
                lambda request, context: self._abort_auth(context)
            )

        # Continue to actual RPC
        return continuation(handler_call_details)

    def _abort_auth(self, context):
        context.set_code(grpc.StatusCode.UNAUTHENTICATED)
        context.set_details('Invalid or missing authentication token')
        return None

    def validate_token(self, token):
        # Implement token validation (JWT, etc.)
        return token.startswith('Bearer ')
```

**Go - Logging interceptor**:
```go
import (
    "context"
    "log"
    "time"

    "google.golang.org/grpc"
)

func loggingInterceptor(
    ctx context.Context,
    req interface{},
    info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler,
) (interface{}, error) {
    start := time.Now()

    log.Printf("[gRPC] Started: %s", info.FullMethod)

    // Continue to actual RPC
    resp, err := handler(ctx, req)

    duration := time.Since(start)
    log.Printf("[gRPC] Completed: %s (%v)", info.FullMethod, duration)

    return resp, err
}

// Use interceptor
server := grpc.NewServer(
    grpc.UnaryInterceptor(loggingInterceptor),
)
```

**Go - Authentication interceptor**:
```go
func authInterceptor(
    ctx context.Context,
    req interface{},
    info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler,
) (interface{}, error) {
    // Extract metadata
    md, ok := metadata.FromIncomingContext(ctx)
    if !ok {
        return nil, status.Error(codes.Unauthenticated, "missing metadata")
    }

    // Validate token
    tokens := md["authorization"]
    if len(tokens) == 0 {
        return nil, status.Error(codes.Unauthenticated, "missing token")
    }

    if !validateToken(tokens[0]) {
        return nil, status.Error(codes.Unauthenticated, "invalid token")
    }

    // Continue to actual RPC
    return handler(ctx, req)
}
```

### Client Interceptors

**Python - Adding authentication**:
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

**Go - Adding metadata**:
```go
func authInterceptor(token string) grpc.UnaryClientInterceptor {
    return func(
        ctx context.Context,
        method string,
        req, reply interface{},
        cc *grpc.ClientConn,
        invoker grpc.UnaryInvoker,
        opts ...grpc.CallOption,
    ) error {
        // Add metadata
        ctx = metadata.AppendToOutgoingContext(ctx, "authorization", "Bearer "+token)

        // Continue with modified context
        return invoker(ctx, method, req, reply, cc, opts...)
    }
}

// Use interceptor
conn, err := grpc.Dial(
    "localhost:50051",
    grpc.WithInsecure(),
    grpc.WithUnaryInterceptor(authInterceptor("secret-token")),
)
```

---

## 7. Metadata

### What is Metadata?

**Metadata** = HTTP/2 headers (key-value pairs sent with RPC calls)

**Common uses**:
- Authentication tokens
- Request IDs for tracing
- Client version
- User agent
- Custom headers

### Sending Metadata (Client)

**Python**:
```python
metadata = [
    ('authorization', 'Bearer token123'),
    ('request-id', 'abc-123'),
    ('client-version', '1.0.0')
]

response = stub.GetUser(
    users_pb2.GetUserRequest(id='123'),
    metadata=metadata
)
```

**Go**:
```go
import "google.golang.org/grpc/metadata"

md := metadata.Pairs(
    "authorization", "Bearer token123",
    "request-id", "abc-123",
    "client-version", "1.0.0",
)
ctx := metadata.NewOutgoingContext(context.Background(), md)

resp, err := client.GetUser(ctx, &pb.GetUserRequest{Id: "123"})
```

### Reading Metadata (Server)

**Python**:
```python
def GetUser(self, request, context):
    # Read metadata
    metadata = dict(context.invocation_metadata())
    auth_token = metadata.get('authorization')
    request_id = metadata.get('request-id')

    print(f'Auth: {auth_token}, Request ID: {request_id}')
```

**Go**:
```go
func (s *server) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.GetUserResponse, error) {
    // Read metadata
    md, ok := metadata.FromIncomingContext(ctx)
    if !ok {
        return nil, status.Error(codes.Internal, "failed to get metadata")
    }

    authTokens := md["authorization"]
    requestIDs := md["request-id"]

    log.Printf("Auth: %v, Request ID: %v", authTokens, requestIDs)
}
```

### Sending Metadata (Server to Client)

**Python**:
```python
def GetUser(self, request, context):
    # Send metadata to client
    context.set_trailing_metadata([
        ('server-version', '2.0.0'),
        ('cache-hit', 'true')
    ])

    return users_pb2.GetUserResponse(...)
```

**Go**:
```go
func (s *server) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.GetUserResponse, error) {
    // Send header metadata (before response)
    header := metadata.Pairs("server-version", "2.0.0")
    grpc.SendHeader(ctx, header)

    // Send trailer metadata (after response)
    trailer := metadata.Pairs("cache-hit", "true")
    grpc.SetTrailer(ctx, trailer)

    return &pb.GetUserResponse{...}, nil
}
```

---

## 8. Deadlines and Timeouts

### Why Deadlines Matter

**Problem**: Without deadlines, requests can hang indefinitely
**Solution**: Always set deadlines to prevent resource exhaustion

### Setting Deadlines (Client)

**Python**:
```python
import grpc

try:
    response = stub.GetUser(
        users_pb2.GetUserRequest(id='123'),
        timeout=5  # 5 seconds deadline
    )
except grpc.RpcError as e:
    if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
        print('Request timeout')
```

**Go**:
```go
import (
    "context"
    "time"
)

ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

resp, err := client.GetUser(ctx, &pb.GetUserRequest{Id: "123"})
if err != nil {
    if status.Code(err) == codes.DeadlineExceeded {
        log.Println("Request timeout")
    }
}
```

### Checking Deadlines (Server)

**Python**:
```python
def GetUser(self, request, context):
    # Check time remaining
    if context.time_remaining() < 1:  # Less than 1 second
        context.set_code(grpc.StatusCode.DEADLINE_EXCEEDED)
        context.set_details('Not enough time to complete request')
        return users_pb2.GetUserResponse()

    # Continue processing
    user = db.get_user(request.id)
    return users_pb2.GetUserResponse(user=user)
```

**Go**:
```go
func (s *server) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.GetUserResponse, error) {
    // Check if deadline exceeded
    deadline, ok := ctx.Deadline()
    if ok && time.Until(deadline) < 1*time.Second {
        return nil, status.Error(codes.DeadlineExceeded, "not enough time")
    }

    // Continue processing
    user, err := db.GetUser(req.Id)
    return &pb.GetUserResponse{User: user}, err
}
```

### Deadline Propagation

**Deadlines automatically propagate** to downstream services:

```
Client (10s timeout) → Service A (8s remaining) → Service B (6s remaining)
```

**Go example**:
```go
// Service A receives request with 10s deadline
func (s *serverA) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.GetUserResponse, error) {
    // Call Service B (deadline propagates automatically)
    resp, err := serviceBClient.GetDetails(ctx, &pb.GetDetailsRequest{...})
    // Service B sees remaining deadline (e.g., 8 seconds)
}
```

---

## 9. Load Balancing

### Client-Side Load Balancing

**gRPC supports client-side load balancing** (no proxy needed)

**Go example**:
```go
import (
    "google.golang.org/grpc"
    "google.golang.org/grpc/balancer/roundrobin"
)

// Connect to multiple backends
conn, err := grpc.Dial(
    "dns:///my-service:50051",  // DNS with multiple A records
    grpc.WithDefaultServiceConfig(`{"loadBalancingPolicy":"round_robin"}`),
    grpc.WithInsecure(),
)
```

**Load balancing policies**:
- **round_robin**: Distribute requests evenly across backends
- **pick_first**: Use first available backend (failover)
- **grpclb**: External load balancer (Google LB)

### Service Discovery

**DNS-based** (multiple A records):
```go
conn, err := grpc.Dial(
    "dns:///my-service.example.com:50051",
    grpc.WithDefaultServiceConfig(`{"loadBalancingPolicy":"round_robin"}`),
)
```

**Custom resolver** (e.g., Consul, etcd):
```go
import "google.golang.org/grpc/resolver"

// Implement custom resolver
type consulResolver struct{}

func (r *consulResolver) Build(target resolver.Target, cc resolver.ClientConn, opts resolver.BuildOptions) (resolver.Resolver, error) {
    // Fetch backends from Consul
    backends := consul.GetBackends("my-service")

    // Update ClientConn with backends
    cc.UpdateState(resolver.State{
        Addresses: backends,
    })
}

// Register resolver
resolver.Register(&consulResolver{})

// Use resolver
conn, err := grpc.Dial(
    "consul:///my-service",
    grpc.WithDefaultServiceConfig(`{"loadBalancingPolicy":"round_robin"}`),
)
```

### Proxy-Based Load Balancing

**Alternative**: Use external load balancer (Envoy, Nginx, HAProxy)

**Envoy example**:
```yaml
static_resources:
  listeners:
  - address:
      socket_address:
        address: 0.0.0.0
        port_value: 8080
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          codec_type: AUTO
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: grpc_service
          http_filters:
          - name: envoy.filters.http.router

  clusters:
  - name: grpc_service
    connect_timeout: 1s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    http2_protocol_options: {}
    load_assignment:
      cluster_name: grpc_service
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: backend1
                port_value: 50051
        - endpoint:
            address:
              socket_address:
                address: backend2
                port_value: 50051
```

---

## 10. Security (TLS, Auth)

### TLS Encryption

**Server with TLS** (Python):
```python
import grpc

# Load credentials
server_credentials = grpc.ssl_server_credentials([
    (
        open('server-key.pem', 'rb').read(),  # Private key
        open('server-cert.pem', 'rb').read()  # Certificate
    )
])

# Create secure server
server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
users_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
server.add_secure_port('[::]:50051', server_credentials)
server.start()
```

**Client with TLS** (Python):
```python
# Load credentials
channel_credentials = grpc.ssl_channel_credentials(
    root_certificates=open('ca-cert.pem', 'rb').read()
)

# Create secure channel
channel = grpc.secure_channel('localhost:50051', channel_credentials)
stub = users_pb2_grpc.UserServiceStub(channel)
```

**Go TLS example**:
```go
import (
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials"
)

// Server
creds, err := credentials.NewServerTLSFromFile("server-cert.pem", "server-key.pem")
if err != nil {
    log.Fatal(err)
}
server := grpc.NewServer(grpc.Creds(creds))

// Client
creds, err := credentials.NewClientTLSFromFile("ca-cert.pem", "")
if err != nil {
    log.Fatal(err)
}
conn, err := grpc.Dial("localhost:50051", grpc.WithTransportCredentials(creds))
```

### Token-Based Authentication

**Server interceptor** (Python):
```python
class TokenAuthInterceptor(grpc.ServerInterceptor):
    def __init__(self, secret_key):
        self.secret_key = secret_key

    def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata())
        token = metadata.get('authorization', '').replace('Bearer ', '')

        if not self.validate_token(token):
            return grpc.unary_unary_rpc_method_handler(
                lambda req, ctx: self._abort_auth(ctx)
            )

        return continuation(handler_call_details)

    def validate_token(self, token):
        # Implement JWT validation
        import jwt
        try:
            jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return True
        except:
            return False

    def _abort_auth(self, context):
        context.set_code(grpc.StatusCode.UNAUTHENTICATED)
        context.set_details('Invalid authentication token')
```

**Client sends token**:
```python
metadata = [('authorization', f'Bearer {jwt_token}')]
response = stub.GetUser(
    users_pb2.GetUserRequest(id='123'),
    metadata=metadata
)
```

---

## 11. Performance Optimization

### Connection Pooling

**Problem**: Creating new connections is expensive (TCP handshake, TLS negotiation)
**Solution**: Reuse connections

```python
# ✅ GOOD: Reuse channel
channel = grpc.insecure_channel('localhost:50051')
stub = users_pb2_grpc.UserServiceStub(channel)

for i in range(100):
    response = stub.GetUser(...)  # Reuses connection

# ❌ BAD: New connection per request
for i in range(100):
    channel = grpc.insecure_channel('localhost:50051')  # Expensive!
    stub = users_pb2_grpc.UserServiceStub(channel)
    response = stub.GetUser(...)
    channel.close()
```

### Compression

**Enable compression** to reduce payload size:

```python
# Client enables compression
response = stub.GetUser(
    users_pb2.GetUserRequest(id='123'),
    compression=grpc.Compression.Gzip  # or Deflate
)
```

```go
// Go client
resp, err := client.GetUser(
    ctx,
    &pb.GetUserRequest{Id: "123"},
    grpc.UseCompressor(gzip.Name),
)
```

### Message Size Limits

**Default**: 4 MB max message size
**Adjust if needed**:

```python
# Server
options = [
    ('grpc.max_receive_message_length', 10 * 1024 * 1024),  # 10 MB
    ('grpc.max_send_message_length', 10 * 1024 * 1024),
]
server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), options=options)

# Client
options = [
    ('grpc.max_receive_message_length', 10 * 1024 * 1024),
    ('grpc.max_send_message_length', 10 * 1024 * 1024),
]
channel = grpc.insecure_channel('localhost:50051', options=options)
```

### Keepalive

**Problem**: Long-lived idle connections may be closed by proxies/firewalls
**Solution**: Enable keepalive pings

```python
# Client keepalive
options = [
    ('grpc.keepalive_time_ms', 30000),           # Ping every 30 seconds
    ('grpc.keepalive_timeout_ms', 10000),        # Wait 10 seconds for response
    ('grpc.keepalive_permit_without_calls', 1),  # Allow keepalive without active RPCs
]
channel = grpc.insecure_channel('localhost:50051', options=options)
```

---

## 12. Streaming Patterns

### Pagination with Server Streaming

```protobuf
message ListUsersRequest {
  int32 page_size = 1;
  string page_token = 2;
}

service UserService {
  rpc ListUsers(ListUsersRequest) returns (stream User);
}
```

**Python implementation**:
```python
def ListUsers(self, request, context):
    page_size = request.page_size or 50
    page_token = request.page_token

    offset = int(page_token) if page_token else 0

    for user in db.list_users(limit=page_size, offset=offset):
        yield users_pb2.User(
            id=user['id'],
            name=user['name']
        )
```

### File Upload with Client Streaming

```protobuf
message UploadFileRequest {
  oneof data {
    FileMetadata metadata = 1;
    bytes chunk = 2;
  }
}

message FileMetadata {
  string filename = 1;
  int64 file_size = 2;
}

message UploadFileResponse {
  string file_id = 1;
  int64 bytes_uploaded = 2;
}

service FileService {
  rpc UploadFile(stream UploadFileRequest) returns (UploadFileResponse);
}
```

**Python implementation**:
```python
def UploadFile(self, request_iterator, context):
    file_id = None
    bytes_uploaded = 0
    file_handle = None

    for request in request_iterator:
        if request.HasField('metadata'):
            # First message: metadata
            file_id = generate_file_id()
            file_handle = open(f'/uploads/{file_id}', 'wb')
        elif request.HasField('chunk'):
            # Subsequent messages: chunks
            chunk = request.chunk
            file_handle.write(chunk)
            bytes_uploaded += len(chunk)

    if file_handle:
        file_handle.close()

    return files_pb2.UploadFileResponse(
        file_id=file_id,
        bytes_uploaded=bytes_uploaded
    )
```

---

## 13. Testing

### Unit Testing gRPC Services

**Python (pytest)**:
```python
import grpc
import grpc_testing
import users_pb2
import users_pb2_grpc

def test_get_user():
    # Create test server
    servicer = UserService()
    server = grpc_testing.server_from_dictionary(
        {users_pb2.DESCRIPTOR.services_by_name['UserService']: servicer},
        grpc_testing.strict_real_time()
    )

    # Create request
    request = users_pb2.GetUserRequest(id='123')

    # Call method
    method = server.invoke_unary_unary(
        users_pb2.DESCRIPTOR.services_by_name['UserService'].methods_by_name['GetUser'],
        (),
        request,
        None
    )

    # Assert response
    response, metadata, code, details = method.termination()
    assert code == grpc.StatusCode.OK
    assert response.user.id == '123'
```

### Integration Testing

**Python (with real server)**:
```python
import grpc
import pytest
import users_pb2
import users_pb2_grpc

@pytest.fixture
def grpc_client():
    channel = grpc.insecure_channel('localhost:50051')
    stub = users_pb2_grpc.UserServiceStub(channel)
    yield stub
    channel.close()

def test_create_and_get_user(grpc_client):
    # Create user
    create_response = grpc_client.CreateUser(
        users_pb2.CreateUserRequest(
            email='test@example.com',
            name='Test User'
        )
    )
    assert create_response.user.email == 'test@example.com'

    # Get user
    get_response = grpc_client.GetUser(
        users_pb2.GetUserRequest(id=create_response.user.id)
    )
    assert get_response.user.name == 'Test User'
```

---

## 14. Tooling

### grpcurl

**Command-line tool for testing gRPC services** (like curl for REST)

**List services**:
```bash
grpcurl -plaintext localhost:50051 list
```

**Call method**:
```bash
grpcurl -plaintext \
  -d '{"id": "123"}' \
  localhost:50051 \
  users.v1.UserService/GetUser
```

**With metadata**:
```bash
grpcurl -plaintext \
  -H 'authorization: Bearer token123' \
  -d '{"id": "123"}' \
  localhost:50051 \
  users.v1.UserService/GetUser
```

### grpc-gateway

**Generate REST API from gRPC service** (HTTP/JSON → gRPC translation)

**Install**:
```bash
go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway@latest
```

**Add annotations**:
```protobuf
import "google/api/annotations.proto";

service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse) {
    option (google.api.http) = {
      get: "/v1/users/{id}"
    };
  }

  rpc CreateUser(CreateUserRequest) returns (CreateUserResponse) {
    option (google.api.http) = {
      post: "/v1/users"
      body: "*"
    };
  }
}
```

**Generate gateway**:
```bash
protoc -I. \
  --grpc-gateway_out=. \
  --grpc-gateway_opt logtostderr=true \
  users.proto
```

**Result**: REST API that proxies to gRPC service
```bash
curl http://localhost:8080/v1/users/123
# Translates to: GetUser(GetUserRequest{id: "123"})
```

### buf

**Modern Protobuf toolchain** (better than `protoc`)

**Install**:
```bash
brew install bufbuild/buf/buf
```

**Initialize**:
```bash
buf config init
```

**Lint**:
```bash
buf lint
```

**Generate code**:
```bash
# buf.gen.yaml
version: v1
plugins:
  - plugin: go
    out: gen/go
    opt: paths=source_relative
  - plugin: go-grpc
    out: gen/go
    opt: paths=source_relative

# Generate
buf generate
```

**Breaking change detection**:
```bash
buf breaking --against '.git#branch=main'
```

---

## 15. Migration Strategies

### REST to gRPC Migration

**Strategy 1: Dual-mode service**
- Implement both REST and gRPC
- Use grpc-gateway for REST → gRPC translation
- Gradually migrate clients

**Strategy 2: Proxy approach**
- Deploy gRPC service alongside REST
- REST proxy calls gRPC internally
- Deprecate REST endpoints gradually

**Strategy 3: Strangler fig pattern**
- New features: gRPC only
- Existing features: Keep REST, migrate when high-value
- Eventually deprecate REST entirely

---

## 16. Anti-Patterns

### 1. Not Setting Deadlines

❌ **Problem**: Requests hang indefinitely
```python
response = stub.GetUser(request)  # No timeout!
```

✅ **Solution**: Always set deadlines
```python
response = stub.GetUser(request, timeout=5)
```

### 2. Creating Connections Per Request

❌ **Problem**: Expensive connection overhead
```python
for i in range(100):
    channel = grpc.insecure_channel('localhost:50051')  # BAD!
    stub = users_pb2_grpc.UserServiceStub(channel)
    response = stub.GetUser(...)
```

✅ **Solution**: Reuse channels
```python
channel = grpc.insecure_channel('localhost:50051')
stub = users_pb2_grpc.UserServiceStub(channel)

for i in range(100):
    response = stub.GetUser(...)
```

### 3. Large Messages Without Streaming

❌ **Problem**: 100 MB+ messages cause memory issues
```protobuf
rpc UploadFile(UploadFileRequest) returns (UploadFileResponse);

message UploadFileRequest {
  bytes file_data = 1;  // 100 MB!
}
```

✅ **Solution**: Use streaming for large data
```protobuf
rpc UploadFile(stream UploadFileRequest) returns (UploadFileResponse);

message UploadFileRequest {
  bytes chunk = 1;  // 64 KB chunks
}
```

### 4. Ignoring Status Codes

❌ **Problem**: Generic error handling
```python
try:
    response = stub.GetUser(request)
except grpc.RpcError:
    print("Error occurred")  # What error?
```

✅ **Solution**: Handle specific status codes
```python
try:
    response = stub.GetUser(request)
except grpc.RpcError as e:
    if e.code() == grpc.StatusCode.NOT_FOUND:
        print("User not found")
    elif e.code() == grpc.StatusCode.UNAUTHENTICATED:
        print("Authentication required")
```

### 5. Reusing Field Numbers

❌ **Problem**: Breaking backward compatibility
```protobuf
message User {
  string id = 1;
  string email = 2;  // Deleted
  string name = 3;   // Now using field 2 (BAD!)
}
```

✅ **Solution**: Reserve deleted field numbers
```protobuf
message User {
  string id = 1;
  reserved 2;  // Never reuse
  string name = 3;
}
```

---

## 17. Language-Specific Guides

### Python (grpcio)

**Install**:
```bash
pip install grpcio grpcio-tools
```

**Generate code**:
```bash
python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  users.proto
```

**Server**:
```python
import grpc
from concurrent import futures
import users_pb2_grpc

server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
users_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
server.add_insecure_port('[::]:50051')
server.start()
server.wait_for_termination()
```

**Client**:
```python
channel = grpc.insecure_channel('localhost:50051')
stub = users_pb2_grpc.UserServiceStub(channel)
response = stub.GetUser(users_pb2.GetUserRequest(id='123'))
```

---

### Go

**Install**:
```bash
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
```

**Generate code**:
```bash
protoc --go_out=. --go_opt=paths=source_relative \
  --go-grpc_out=. --go-grpc_opt=paths=source_relative \
  users.proto
```

**Server**:
```go
import (
    "net"
    "google.golang.org/grpc"
    pb "github.com/example/users/v1"
)

lis, _ := net.Listen("tcp", ":50051")
server := grpc.NewServer()
pb.RegisterUserServiceServer(server, &serverImpl{})
server.Serve(lis)
```

**Client**:
```go
conn, _ := grpc.Dial("localhost:50051", grpc.WithInsecure())
defer conn.Close()

client := pb.NewUserServiceClient(conn)
resp, _ := client.GetUser(ctx, &pb.GetUserRequest{Id: "123"})
```

---

### Node.js

**Install**:
```bash
npm install @grpc/grpc-js @grpc/proto-loader
```

**Server**:
```javascript
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

const packageDefinition = protoLoader.loadSync('users.proto');
const proto = grpc.loadPackageDefinition(packageDefinition);

const server = new grpc.Server();
server.addService(proto.users.v1.UserService.service, {
    getUser: (call, callback) => {
        callback(null, { user: { id: '123', name: 'Alice' } });
    }
});

server.bindAsync('0.0.0.0:50051', grpc.ServerCredentials.createInsecure(), () => {
    server.start();
});
```

**Client**:
```javascript
const client = new proto.users.v1.UserService(
    'localhost:50051',
    grpc.credentials.createInsecure()
);

client.getUser({ id: '123' }, (err, response) => {
    console.log(response.user.name);
});
```

---

## 18. References

### Official Documentation

- **gRPC**: https://grpc.io/
- **Protocol Buffers**: https://protobuf.dev/
- **gRPC Go**: https://grpc.io/docs/languages/go/
- **gRPC Python**: https://grpc.io/docs/languages/python/
- **gRPC Node.js**: https://grpc.io/docs/languages/node/

### Tools

- **grpcurl**: https://github.com/fullstorydev/grpcurl
- **buf**: https://buf.build/
- **grpc-gateway**: https://grpc-ecosystem.github.io/grpc-gateway/
- **Envoy**: https://www.envoyproxy.io/

### Style Guides

- **Protobuf Style Guide**: https://protobuf.dev/programming-guides/style/
- **API Design Guide**: https://cloud.google.com/apis/design

### Books

- "gRPC: Up and Running" by Kasun Indrasiri and Danesh Kuruppu
- "Practical gRPC" by Joshua B. Humphries

---

**Last Updated**: 2025-10-27
**Version**: 1.0
**Lines**: ~2,800
