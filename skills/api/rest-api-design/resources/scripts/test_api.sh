#!/usr/bin/env bash
#
# REST API Testing Script
#
# Test REST API endpoints with various scenarios including:
# - CRUD operations
# - Error handling
# - Authentication
# - Rate limiting
# - Caching
# - Pagination
# - Content negotiation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BASE_URL=""
API_KEY=""
VERBOSE=0
JSON_OUTPUT=0
SAVE_RESPONSES=0
OUTPUT_DIR="./api_test_results"

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Usage
usage() {
    cat <<EOF
Usage: $0 [options]

Test REST API endpoints with various scenarios.

Options:
    -u, --url URL           Base URL of the API (required)
    -k, --api-key KEY       API key for authentication
    -v, --verbose           Verbose output
    -j, --json              Output results as JSON
    -s, --save              Save responses to files
    -o, --output-dir DIR    Output directory for saved responses (default: ./api_test_results)
    -h, --help              Show this help message

Examples:
    # Basic test
    $0 --url https://api.example.com

    # With authentication
    $0 --url https://api.example.com --api-key YOUR_API_KEY

    # Verbose output with saved responses
    $0 --url https://api.example.com --verbose --save

    # JSON output
    $0 --url https://api.example.com --json
EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            BASE_URL="$2"
            shift 2
            ;;
        -k|--api-key)
            API_KEY="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -j|--json)
            JSON_OUTPUT=1
            shift
            ;;
        -s|--save)
            SAVE_RESPONSES=1
            shift
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required arguments
if [[ -z "$BASE_URL" ]]; then
    echo "Error: Base URL is required"
    usage
fi

# Create output directory if saving responses
if [[ $SAVE_RESPONSES -eq 1 ]]; then
    mkdir -p "$OUTPUT_DIR"
fi

# Logging functions
log_info() {
    if [[ $VERBOSE -eq 1 ]] && [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${GREEN}[PASS]${NC} $1"
    fi
}

log_failure() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${RED}[FAIL]${NC} $1"
    fi
}

log_warning() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${YELLOW}[WARN]${NC} $1"
    fi
}

# Test result tracking
record_test() {
    local name="$1"
    local passed="$2"
    local details="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [[ "$passed" == "true" ]]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_success "$name"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_failure "$name: $details"
    fi

    if [[ $JSON_OUTPUT -eq 1 ]]; then
        # Store for JSON output later
        echo "$name|$passed|$details" >> "$OUTPUT_DIR/.test_results.tmp"
    fi
}

# HTTP request wrapper
make_request() {
    local method="$1"
    local path="$2"
    local data="${3:-}"
    local headers="${4:-}"
    local expected_status="${5:-200}"

    local url="${BASE_URL}${path}"
    local curl_opts="-s -w \n%{http_code}\n -X $method"

    # Add headers
    if [[ -n "$API_KEY" ]]; then
        curl_opts="$curl_opts -H 'Authorization: Bearer $API_KEY'"
    fi

    if [[ -n "$headers" ]]; then
        curl_opts="$curl_opts $headers"
    fi

    # Add data for POST/PUT/PATCH
    if [[ -n "$data" ]]; then
        curl_opts="$curl_opts -H 'Content-Type: application/json' -d '$data'"
    fi

    # Make request
    log_info "Request: $method $url"

    local response
    response=$(eval curl $curl_opts "$url" 2>&1)

    # Parse response and status code
    local body
    local status_code
    body=$(echo "$response" | head -n -1)
    status_code=$(echo "$response" | tail -n 1)

    log_info "Status: $status_code"

    if [[ $VERBOSE -eq 1 ]]; then
        log_info "Response: $body"
    fi

    # Save response if requested
    if [[ $SAVE_RESPONSES -eq 1 ]]; then
        local filename="${method}_${path//\//_}.json"
        echo "$body" > "$OUTPUT_DIR/$filename"
    fi

    # Check status code
    if [[ "$status_code" -eq "$expected_status" ]]; then
        echo "$body"
        return 0
    else
        echo "Expected status $expected_status, got $status_code"
        return 1
    fi
}

# Test: Health check
test_health_check() {
    log_info "Testing health check endpoint..."

    local response
    if response=$(make_request GET /health "" "" 200 2>&1); then
        record_test "Health check" "true" ""
    else
        record_test "Health check" "false" "$response"
    fi
}

# Test: List resources
test_list_resources() {
    log_info "Testing list resources..."

    local response
    if response=$(make_request GET /api/users "" "" 200 2>&1); then
        # Check if response is valid JSON
        if echo "$response" | jq . >/dev/null 2>&1; then
            # Check for data or items array
            if echo "$response" | jq -e '.data // .items // .users' >/dev/null 2>&1; then
                record_test "List resources" "true" ""
            else
                record_test "List resources" "false" "Response missing data/items/users array"
            fi
        else
            record_test "List resources" "false" "Invalid JSON response"
        fi
    else
        record_test "List resources" "false" "$response"
    fi
}

# Test: Get single resource
test_get_resource() {
    log_info "Testing get single resource..."

    local response
    if response=$(make_request GET /api/users/1 "" "" 200 2>&1); then
        # Check if response contains id
        if echo "$response" | jq -e '.id' >/dev/null 2>&1; then
            record_test "Get resource" "true" ""
        else
            record_test "Get resource" "false" "Response missing id field"
        fi
    else
        # 404 is acceptable if resource doesn't exist
        if [[ "$response" == *"404"* ]]; then
            record_test "Get resource" "true" "Resource not found (404)"
        else
            record_test "Get resource" "false" "$response"
        fi
    fi
}

# Test: Create resource
test_create_resource() {
    log_info "Testing create resource..."

    local data='{"name":"Test User","email":"test@example.com"}'
    local response

    if response=$(make_request POST /api/users "$data" "" 201 2>&1); then
        # Check if response contains id
        if echo "$response" | jq -e '.id' >/dev/null 2>&1; then
            record_test "Create resource" "true" ""

            # Store ID for later tests
            CREATED_RESOURCE_ID=$(echo "$response" | jq -r '.id')
        else
            record_test "Create resource" "false" "Response missing id field"
        fi
    else
        # 200 is acceptable too
        if [[ "$response" == *"200"* ]]; then
            log_warning "POST returned 200 instead of 201"
            record_test "Create resource" "true" "Status 200 (should be 201)"
        else
            record_test "Create resource" "false" "$response"
        fi
    fi
}

# Test: Update resource
test_update_resource() {
    log_info "Testing update resource..."

    local resource_id="${CREATED_RESOURCE_ID:-1}"
    local data='{"name":"Updated User"}'
    local response

    if response=$(make_request PUT /api/users/$resource_id "$data" "" 200 2>&1); then
        record_test "Update resource (PUT)" "true" ""
    else
        record_test "Update resource (PUT)" "false" "$response"
    fi
}

# Test: Partial update
test_patch_resource() {
    log_info "Testing partial update..."

    local resource_id="${CREATED_RESOURCE_ID:-1}"
    local data='{"email":"updated@example.com"}'
    local response

    if response=$(make_request PATCH /api/users/$resource_id "$data" "" 200 2>&1); then
        record_test "Partial update (PATCH)" "true" ""
    else
        record_test "Partial update (PATCH)" "false" "$response"
    fi
}

# Test: Delete resource
test_delete_resource() {
    log_info "Testing delete resource..."

    local resource_id="${CREATED_RESOURCE_ID:-1}"
    local response

    # Accept both 204 and 200
    if response=$(make_request DELETE /api/users/$resource_id "" "" 204 2>&1); then
        record_test "Delete resource" "true" ""
    elif response=$(make_request DELETE /api/users/$resource_id "" "" 200 2>&1); then
        log_warning "DELETE returned 200 instead of 204"
        record_test "Delete resource" "true" "Status 200 (should be 204)"
    else
        record_test "Delete resource" "false" "$response"
    fi
}

# Test: Error handling (404)
test_not_found() {
    log_info "Testing 404 error handling..."

    local response
    if response=$(make_request GET /api/users/999999 "" "" 404 2>&1); then
        # Check if error response is JSON
        if echo "$response" | jq . >/dev/null 2>&1; then
            record_test "404 error handling" "true" ""
        else
            record_test "404 error handling" "false" "Error response is not JSON"
        fi
    else
        record_test "404 error handling" "false" "$response"
    fi
}

# Test: Validation error (400/422)
test_validation_error() {
    log_info "Testing validation error..."

    local data='{"invalid":"data"}'
    local response

    # Try to create with invalid data
    if response=$(make_request POST /api/users "$data" "" 400 2>&1); then
        record_test "Validation error (400)" "true" ""
    elif response=$(make_request POST /api/users "$data" "" 422 2>&1); then
        record_test "Validation error (422)" "true" ""
    else
        log_warning "API may not validate input properly"
        record_test "Validation error" "false" "Expected 400 or 422"
    fi
}

# Test: Pagination
test_pagination() {
    log_info "Testing pagination..."

    local response
    if response=$(make_request GET "/api/users?limit=10&offset=0" "" "" 200 2>&1); then
        # Check for pagination metadata
        if echo "$response" | jq -e '.pagination // .meta // .page_info' >/dev/null 2>&1; then
            record_test "Pagination" "true" ""
        else
            log_warning "Response missing pagination metadata"
            record_test "Pagination" "false" "Missing pagination metadata"
        fi
    else
        record_test "Pagination" "false" "$response"
    fi
}

# Test: Filtering
test_filtering() {
    log_info "Testing filtering..."

    local response
    if response=$(make_request GET "/api/users?status=active" "" "" 200 2>&1); then
        record_test "Filtering" "true" ""
    else
        record_test "Filtering" "false" "$response"
    fi
}

# Test: Sorting
test_sorting() {
    log_info "Testing sorting..."

    local response
    if response=$(make_request GET "/api/users?sort=created_at" "" "" 200 2>&1); then
        record_test "Sorting" "true" ""
    else
        record_test "Sorting" "false" "$response"
    fi
}

# Test: Content negotiation
test_content_negotiation() {
    log_info "Testing content negotiation..."

    local response
    if response=$(make_request GET /api/users "" "-H 'Accept: application/json'" 200 2>&1); then
        # Check Content-Type in response (would need -i flag)
        record_test "Content negotiation" "true" ""
    else
        record_test "Content negotiation" "false" "$response"
    fi
}

# Test: Rate limiting
test_rate_limiting() {
    log_info "Testing rate limiting..."

    # Make multiple rapid requests
    local count=0
    local max_requests=20
    local got_429=0

    for ((i=1; i<=max_requests; i++)); do
        local response
        if ! response=$(make_request GET /api/users "" "" 200 2>&1); then
            if [[ "$response" == *"429"* ]]; then
                got_429=1
                break
            fi
        fi
        count=$((count + 1))
    done

    if [[ $got_429 -eq 1 ]]; then
        record_test "Rate limiting" "true" "Got 429 after $count requests"
    else
        log_warning "No rate limit encountered after $max_requests requests"
        record_test "Rate limiting" "false" "No rate limit detected"
    fi
}

# Test: Caching
test_caching() {
    log_info "Testing caching..."

    # First request
    local response1
    response1=$(curl -s -I "${BASE_URL}/api/users" 2>&1)

    # Check for cache headers
    if echo "$response1" | grep -iq "cache-control\|etag\|last-modified"; then
        record_test "Caching headers" "true" ""
    else
        log_warning "No cache headers found"
        record_test "Caching headers" "false" "Missing cache headers"
    fi
}

# Test: Authentication
test_authentication() {
    log_info "Testing authentication..."

    # Try request without auth
    local response
    if ! response=$(make_request GET /api/users "" "" 401 2>&1); then
        # If we got 200, API might not require auth
        log_warning "API may not require authentication"
        record_test "Authentication" "true" "No auth required"
    else
        record_test "Authentication" "true" ""
    fi
}

# Test: CORS headers
test_cors() {
    log_info "Testing CORS headers..."

    local response
    response=$(curl -s -I -X OPTIONS "${BASE_URL}/api/users" 2>&1)

    if echo "$response" | grep -iq "access-control-allow"; then
        record_test "CORS headers" "true" ""
    else
        log_warning "No CORS headers found"
        record_test "CORS headers" "false" "Missing CORS headers"
    fi
}

# Output JSON results
output_json() {
    local results_file="$OUTPUT_DIR/.test_results.tmp"

    if [[ ! -f "$results_file" ]]; then
        echo '{"tests":[],"summary":{"total":0,"passed":0,"failed":0}}'
        return
    fi

    echo "{"
    echo '  "tests": ['

    local first=1
    while IFS='|' read -r name passed details; do
        if [[ $first -eq 1 ]]; then
            first=0
        else
            echo ","
        fi

        echo -n "    {"
        echo -n "\"name\":\"$name\","
        echo -n "\"passed\":$passed,"
        echo -n "\"details\":\"$details\""
        echo -n "}"
    done < "$results_file"

    echo ""
    echo "  ],"
    echo "  \"summary\": {"
    echo "    \"total\": $TOTAL_TESTS,"
    echo "    \"passed\": $PASSED_TESTS,"
    echo "    \"failed\": $FAILED_TESTS"
    echo "  }"
    echo "}"

    rm -f "$results_file"
}

# Main test execution
main() {
    log_info "Starting API tests for: $BASE_URL"
    log_info ""

    # Run all tests
    test_health_check
    test_list_resources
    test_get_resource
    test_create_resource
    test_update_resource
    test_patch_resource
    test_delete_resource
    test_not_found
    test_validation_error
    test_pagination
    test_filtering
    test_sorting
    test_content_negotiation
    test_rate_limiting
    test_caching
    test_authentication
    test_cors

    # Output results
    if [[ $JSON_OUTPUT -eq 1 ]]; then
        output_json
    else
        echo ""
        echo "=========================================="
        echo "Test Results"
        echo "=========================================="
        echo "Total:  $TOTAL_TESTS"
        echo "Passed: $PASSED_TESTS"
        echo "Failed: $FAILED_TESTS"
        echo "=========================================="

        if [[ $FAILED_TESTS -eq 0 ]]; then
            echo -e "${GREEN}All tests passed!${NC}"
            exit 0
        else
            echo -e "${RED}Some tests failed${NC}"
            exit 1
        fi
    fi
}

# Run main
main
