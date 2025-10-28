#!/bin/bash
# Example: Generate TypeScript code from Protocol Buffer schemas
#
# Demonstrates:
# - TypeScript code generation
# - grpc-web for browser compatibility
# - npm package integration
# - Type-safe client code

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_FILE="${SCRIPT_DIR}/user_service.proto"
OUTPUT_DIR="${SCRIPT_DIR}/generated/typescript"

echo "Generating TypeScript code from Protocol Buffers..."
echo "  Proto file: ${PROTO_FILE}"
echo "  Output dir: ${OUTPUT_DIR}"
echo

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Generate TypeScript code
# Note: This requires protoc-gen-ts and protoc-gen-grpc-web:
#   npm install -g ts-protoc-gen
#   npm install -g protoc-gen-grpc-web

echo "Method 1: Using protoc with ts-protoc-gen"
protoc \
  --plugin=protoc-gen-ts=./node_modules/.bin/protoc-gen-ts \
  --ts_out="${OUTPUT_DIR}" \
  --proto_path="${SCRIPT_DIR}" \
  "${PROTO_FILE}"

# Generate grpc-web client
protoc \
  --plugin=protoc-gen-grpc-web=./node_modules/.bin/protoc-gen-grpc-web \
  --grpc-web_out=import_style=typescript,mode=grpcwebtext:"${OUTPUT_DIR}" \
  --proto_path="${SCRIPT_DIR}" \
  "${PROTO_FILE}"

echo "✓ Generated files:"
find "${OUTPUT_DIR}" -type f \( -name "*.ts" -o -name "*.d.ts" \) | while read -r file; do
  echo "  - ${file}"
  lines=$(wc -l < "${file}")
  echo "    (${lines} lines)"
done

echo
echo "Create package.json for generated code:"
cat > "${OUTPUT_DIR}/package.json" << 'EOF'
{
  "name": "@example/protos",
  "version": "1.0.0",
  "description": "Generated Protocol Buffer types",
  "main": "index.ts",
  "types": "index.ts",
  "dependencies": {
    "google-protobuf": "^3.21.0",
    "grpc-web": "^1.4.2"
  },
  "devDependencies": {
    "@types/google-protobuf": "^3.15.12",
    "typescript": "^5.0.0"
  }
}
EOF

cat > "${OUTPUT_DIR}/tsconfig.json" << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020"],
    "moduleResolution": "node",
    "declaration": true,
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["*.ts"],
  "exclude": ["node_modules"]
}
EOF

echo "✓ Created package.json and tsconfig.json"

echo
echo "Usage example:"
cat << 'EOF'

import { User, CreateUserRequest } from './user_service_pb';
import { UserServiceClient } from './user_service_grpc_web_pb';
import { Timestamp } from 'google-protobuf/google/protobuf/timestamp_pb';

// Create a user message
const user = new User();
user.setId('user-123');
user.setEmail('user@example.com');
user.setDisplayName('John Doe');

const timestamp = new Timestamp();
timestamp.fromDate(new Date());
user.setCreatedAt(timestamp);

// Serialize to bytes
const bytes = user.serializeBinary();
console.log(`Serialized: ${bytes.length} bytes`);

// Deserialize from bytes
const user2 = User.deserializeBinary(bytes);
console.log(`Deserialized: ${user2.getEmail()}`);

// gRPC-Web client example (for browser)
const client = new UserServiceClient('http://localhost:8080');

const request = new CreateUserRequest();
request.setEmail('new@example.com');
request.setDisplayName('New User');

client.createUser(request, {}, (err, response) => {
  if (err) {
    console.error('Error:', err);
    return;
  }
  const user = response.getUser();
  console.log(`Created user: ${user.getId()}`);
});

// Promise-based usage
const createUser = (email: string, displayName: string): Promise<User> => {
  return new Promise((resolve, reject) => {
    const request = new CreateUserRequest();
    request.setEmail(email);
    request.setDisplayName(displayName);

    client.createUser(request, {}, (err, response) => {
      if (err) {
        reject(err);
      } else {
        resolve(response.getUser());
      }
    });
  });
};

// Usage
createUser('test@example.com', 'Test User')
  .then(user => console.log('User created:', user.getId()))
  .catch(err => console.error('Error:', err));

EOF

echo
echo "Done! TypeScript code generated successfully."
