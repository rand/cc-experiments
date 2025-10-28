#!/bin/bash
# Example: Generate Python code from Protocol Buffer schemas
#
# Demonstrates:
# - Basic code generation for Python
# - gRPC service generation
# - Output organization
# - Import path handling

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_FILE="${SCRIPT_DIR}/user_service.proto"
OUTPUT_DIR="${SCRIPT_DIR}/generated/python"

echo "Generating Python code from Protocol Buffers..."
echo "  Proto file: ${PROTO_FILE}"
echo "  Output dir: ${OUTPUT_DIR}"
echo

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Generate Python code with protoc
# Note: This requires protoc and grpc_tools to be installed:
#   pip install grpcio-tools
#
# Alternative using script:
#   ../scripts/generate_proto_code.py --proto-file user_service.proto --language python

echo "Method 1: Using protoc directly"
protoc \
  --python_out="${OUTPUT_DIR}" \
  --grpc_python_out="${OUTPUT_DIR}" \
  --proto_path="${SCRIPT_DIR}" \
  "${PROTO_FILE}"

echo "✓ Generated files:"
find "${OUTPUT_DIR}" -type f -name "*.py" | while read -r file; do
  echo "  - ${file}"
  lines=$(wc -l < "${file}")
  echo "    (${lines} lines)"
done

echo
echo "Method 2: Using generate_proto_code.py"
"${SCRIPT_DIR}/../scripts/generate_proto_code.py" \
  --proto-file "${PROTO_FILE}" \
  --language python \
  --plugin grpc \
  --output-dir "${OUTPUT_DIR}_v2" \
  --validate

echo
echo "Usage example:"
cat << 'EOF'

# Import generated code
from user_service_pb2 import User, CreateUserRequest
from user_service_pb2_grpc import UserServiceStub
import grpc

# Create a user message
user = User(
    id="user-123",
    email="user@example.com",
    display_name="John Doe"
)

# Serialize to bytes
data = user.SerializeToString()
print(f"Serialized: {len(data)} bytes")

# Deserialize from bytes
user2 = User()
user2.ParseFromString(data)
print(f"Deserialized: {user2.email}")

# gRPC client example
channel = grpc.insecure_channel('localhost:50051')
stub = UserServiceStub(channel)

request = CreateUserRequest(
    email="new@example.com",
    display_name="New User"
)
response = stub.CreateUser(request)
print(f"Created user: {response.user.id}")

EOF

echo
echo "Done! Python code generated successfully."
