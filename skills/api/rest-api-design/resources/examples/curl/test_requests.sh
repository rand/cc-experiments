#!/usr/bin/env bash
#
# REST API cURL Examples
#
# Demonstrates various REST API patterns with cURL

set -e

# Configuration
BASE_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-valid-token}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper function
log() {
    echo -e "${BLUE}==>${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

section() {
    echo ""
    echo -e "${YELLOW}━━━ $1 ━━━${NC}"
    echo ""
}

# 1. Health Check
section "Health Check"
log "GET /health"

curl -X GET "${BASE_URL}/health" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

success "Health check complete"

# 2. List Users (with pagination)
section "List Users"
log "GET /api/users?limit=10&offset=0"

curl -X GET "${BASE_URL}/api/users?limit=10&offset=0" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

success "List users complete"

# 3. Filtering
section "Filtering"
log "GET /api/users?status=active&role=admin"

curl -X GET "${BASE_URL}/api/users?status=active&role=admin" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

success "Filtering complete"

# 4. Sorting
section "Sorting"
log "GET /api/users?sort=-created_at"

curl -X GET "${BASE_URL}/api/users?sort=-created_at" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

success "Sorting complete"

# 5. Get Single User
section "Get Single User"
log "GET /api/users/1"

curl -X GET "${BASE_URL}/api/users/1" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

success "Get user complete"

# 6. Conditional Request (If-None-Match)
section "Conditional Request"
log "GET /api/users/1 with If-None-Match"

# Get ETag first
ETAG=$(curl -s -X GET "${BASE_URL}/api/users/1" \
  -H "Authorization: Bearer ${API_KEY}" \
  -I | grep -i etag | cut -d' ' -f2 | tr -d '\r')

echo "ETag: $ETAG"

# Request with If-None-Match
curl -X GET "${BASE_URL}/api/users/1" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "If-None-Match: ${ETAG}" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code} (should be 304 if not modified)\n"

success "Conditional request complete"

# 7. Create User (POST)
section "Create User"
log "POST /api/users"

curl -X POST "${BASE_URL}/api/users" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "password": "secretpassword",
    "role": "user"
  }' \
  -w "\nStatus: %{http_code}\n"

success "Create user complete"

# 8. Update User (PUT)
section "Update User (PUT)"
log "PUT /api/users/1"

curl -X PUT "${BASE_URL}/api/users/1" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "name": "Updated User",
    "email": "updated@example.com",
    "role": "admin"
  }' \
  -w "\nStatus: %{http_code}\n"

success "Update user (PUT) complete"

# 9. Partial Update (PATCH)
section "Partial Update (PATCH)"
log "PATCH /api/users/1"

curl -X PATCH "${BASE_URL}/api/users/1" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "email": "patched@example.com"
  }' \
  -w "\nStatus: %{http_code}\n"

success "Partial update complete"

# 10. JSON Patch (RFC 6902)
section "JSON Patch"
log "PATCH /api/users/1 (JSON Patch)"

curl -X PATCH "${BASE_URL}/api/users/1" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json-patch+json" \
  -H "Accept: application/json" \
  -d '[
    { "op": "replace", "path": "/email", "value": "jsonpatch@example.com" },
    { "op": "add", "path": "/bio", "value": "New bio" }
  ]' \
  -w "\nStatus: %{http_code}\n"

success "JSON Patch complete"

# 11. Delete User
section "Delete User"
log "DELETE /api/users/999"

curl -X DELETE "${BASE_URL}/api/users/999" \
  -H "Authorization: Bearer ${API_KEY}" \
  -w "\nStatus: %{http_code}\n"

success "Delete user complete"

# 12. Error Handling (404)
section "Error Handling - Not Found"
log "GET /api/users/999999"

curl -X GET "${BASE_URL}/api/users/999999" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

success "404 error handling complete"

# 13. Validation Error (422)
section "Error Handling - Validation Error"
log "POST /api/users (invalid data)"

curl -X POST "${BASE_URL}/api/users" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "name": "",
    "email": "invalid-email",
    "password": "short"
  }' \
  -w "\nStatus: %{http_code}\n"

success "Validation error handling complete"

# 14. Authentication Error (401)
section "Error Handling - Unauthorized"
log "GET /api/users (no auth)"

curl -X GET "${BASE_URL}/api/users" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

success "401 error handling complete"

# 15. Content Negotiation
section "Content Negotiation"
log "GET /api/users (Accept: application/json)"

curl -X GET "${BASE_URL}/api/users?limit=5" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\nContent-Type: %{content_type}\n"

success "Content negotiation complete"

# 16. Compression
section "Compression"
log "GET /api/users (Accept-Encoding: gzip)"

curl -X GET "${BASE_URL}/api/users?limit=5" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Accept: application/json" \
  -H "Accept-Encoding: gzip, deflate" \
  --compressed \
  -w "\nStatus: %{http_code}\n"

success "Compression complete"

# 17. Rate Limiting Headers
section "Rate Limiting"
log "GET /api/users (check rate limit headers)"

curl -X GET "${BASE_URL}/api/users" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Accept: application/json" \
  -I | grep -i "x-ratelimit"

success "Rate limiting check complete"

# 18. CORS Preflight
section "CORS Preflight"
log "OPTIONS /api/users"

curl -X OPTIONS "${BASE_URL}/api/users" \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type, Authorization" \
  -I

success "CORS preflight complete"

# 19. Bulk Operations
section "Bulk Operations"
log "POST /api/users/bulk"

curl -X POST "${BASE_URL}/api/users/bulk" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "users": [
      {
        "name": "User 1",
        "email": "user1@example.com",
        "password": "password123"
      },
      {
        "name": "User 2",
        "email": "user2@example.com",
        "password": "password123"
      }
    ]
  }' \
  -w "\nStatus: %{http_code}\n"

success "Bulk operation complete"

# 20. Async Operations
section "Async Operations"
log "POST /api/reports/generate"

curl -X POST "${BASE_URL}/api/reports/generate" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "type": "annual",
    "year": 2025
  }' \
  -w "\nStatus: %{http_code} (should be 202 Accepted)\n"

success "Async operation complete"

# Summary
section "Summary"
echo "All examples completed successfully!"
echo ""
echo "For more details, see:"
echo "  - OpenAPI spec: examples/openapi/petstore.yaml"
echo "  - Python example: examples/python/fastapi_rest.py"
echo "  - Node.js example: examples/node/express_rest.js"
echo "  - TypeScript client: examples/typescript/api_client.ts"
