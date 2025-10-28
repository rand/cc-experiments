#!/bin/bash
# Example: Generate Go code from Protocol Buffer schemas
#
# Demonstrates:
# - Go code generation with proper module paths
# - gRPC service generation
# - Go package organization
# - Import path configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_FILE="${SCRIPT_DIR}/user_service.proto"
OUTPUT_DIR="${SCRIPT_DIR}/generated/go"
GO_MODULE="github.com/example/protos"

echo "Generating Go code from Protocol Buffers..."
echo "  Proto file: ${PROTO_FILE}"
echo "  Output dir: ${OUTPUT_DIR}"
echo "  Go module: ${GO_MODULE}"
echo

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Generate Go code with protoc
# Note: This requires protoc-gen-go and protoc-gen-go-grpc:
#   go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
#   go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

echo "Method 1: Using protoc directly"
protoc \
  --go_out="${OUTPUT_DIR}" \
  --go_opt=module="${GO_MODULE}" \
  --go-grpc_out="${OUTPUT_DIR}" \
  --go-grpc_opt=module="${GO_MODULE}" \
  --proto_path="${SCRIPT_DIR}" \
  "${PROTO_FILE}"

echo "✓ Generated files:"
find "${OUTPUT_DIR}" -type f -name "*.go" | while read -r file; do
  echo "  - ${file}"
  lines=$(wc -l < "${file}")
  echo "    (${lines} lines)"
done

echo
echo "Method 2: Using generate_proto_code.py"
"${SCRIPT_DIR}/../scripts/generate_proto_code.py" \
  --proto-file "${PROTO_FILE}" \
  --language go \
  --go-package "${GO_MODULE}" \
  --plugin grpc \
  --output-dir "${OUTPUT_DIR}_v2" \
  --validate

echo
echo "Create go.mod for generated code:"
cat > "${OUTPUT_DIR}/go.mod" << EOF
module ${GO_MODULE}

go 1.21

require (
    google.golang.org/protobuf v1.31.0
    google.golang.org/grpc v1.59.0
)
EOF

echo "✓ Created go.mod"

echo
echo "Usage example:"
cat << 'EOF'

package main

import (
    "context"
    "log"
    "time"

    pb "github.com/example/protos/user/v1"
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"
    "google.golang.org/protobuf/types/known/timestamppb"
)

func main() {
    // Create a user message
    user := &pb.User{
        Id:          "user-123",
        Email:       "user@example.com",
        DisplayName: "John Doe",
        CreatedAt:   timestamppb.New(time.Now()),
        Status:      pb.UserStatus_USER_STATUS_ACTIVE,
    }

    // Serialize to bytes
    data, err := proto.Marshal(user)
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Serialized: %d bytes", len(data))

    // Deserialize from bytes
    user2 := &pb.User{}
    if err := proto.Unmarshal(data, user2); err != nil {
        log.Fatal(err)
    }
    log.Printf("Deserialized: %s", user2.Email)

    // gRPC client example
    conn, err := grpc.Dial("localhost:50051",
        grpc.WithTransportCredentials(insecure.NewCredentials()))
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()

    client := pb.NewUserServiceClient(conn)

    req := &pb.CreateUserRequest{
        Email:       "new@example.com",
        DisplayName: "New User",
    }

    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()

    resp, err := client.CreateUser(ctx, req)
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Created user: %s", resp.User.Id)
}

EOF

echo
echo "Done! Go code generated successfully."
