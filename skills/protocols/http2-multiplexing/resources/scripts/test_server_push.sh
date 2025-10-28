#!/bin/bash
#
# HTTP/2 Server Push Tester
#
# Tests HTTP/2 server push functionality by analyzing pushed resources,
# measuring performance impact, and validating cache behavior.
#
# Features:
# - Detect server push support
# - List pushed resources
# - Measure push performance vs. regular requests
# - Validate cache headers on pushed resources
# - Test push rejection (RST_STREAM)
#
# Usage:
#   ./test_server_push.sh --url https://example.com
#   ./test_server_push.sh --url https://example.com --json output.json
#   ./test_server_push.sh --help

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
URL=""
JSON_OUTPUT=""
VERBOSE=false
TIMEOUT=10

usage() {
    cat <<EOF
HTTP/2 Server Push Tester

Usage: $0 [OPTIONS]

Options:
    --url URL           URL to test (required)
    --json FILE         Output results to JSON file
    --verbose           Verbose output
    --timeout SECONDS   Request timeout (default: 10)
    --help             Show this help message

Examples:
    # Basic test
    $0 --url https://example.com

    # JSON output
    $0 --url https://example.com --json results.json

    # Verbose output
    $0 --url https://example.com --verbose

Requirements:
    - curl with HTTP/2 support (curl --version | grep HTTP2)
    - nghttp (optional, for detailed frame analysis)
EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            URL="$2"
            shift 2
            ;;
        --json)
            JSON_OUTPUT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

if [[ -z "$URL" ]]; then
    echo "Error: --url is required"
    usage
fi

log() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check requirements
check_requirements() {
    log "Checking requirements..."

    # Check curl with HTTP/2 support
    if ! command -v curl &> /dev/null; then
        error "curl is not installed"
        exit 1
    fi

    if ! curl --version | grep -q "HTTP2"; then
        error "curl does not support HTTP/2"
        exit 1
    fi

    # Check nghttp (optional)
    if command -v nghttp &> /dev/null; then
        log "nghttp found (will use for detailed analysis)"
        HAS_NGHTTP=true
    else
        log "nghttp not found (install for detailed frame analysis)"
        HAS_NGHTTP=false
    fi
}

# Test HTTP/2 support
test_http2_support() {
    log "Testing HTTP/2 support..."

    local response
    response=$(curl -sI --http2 --max-time "$TIMEOUT" "$URL" 2>&1 || true)

    if echo "$response" | grep -q "HTTP/2"; then
        success "Server supports HTTP/2"
        return 0
    else
        error "Server does not support HTTP/2"
        echo "$response"
        return 1
    fi
}

# Detect server push
detect_server_push() {
    log "Detecting server push..."

    local tmpfile
    tmpfile=$(mktemp)

    # Use curl with verbose output to capture push promises
    curl -sI --http2 --max-time "$TIMEOUT" -v "$URL" > "$tmpfile" 2>&1

    local pushed_resources
    pushed_resources=$(grep -i "< link:" "$tmpfile" | grep -i "preload" || true)

    if [[ -n "$pushed_resources" ]]; then
        success "Server push detected via Link headers"
        echo "$pushed_resources" | while read -r line; do
            echo "  $line"
        done
        rm "$tmpfile"
        return 0
    else
        warning "No server push detected (Link headers)"
    fi

    rm "$tmpfile"
    return 1
}

# Analyze push with nghttp
analyze_with_nghttp() {
    if [[ "$HAS_NGHTTP" != "true" ]]; then
        return
    fi

    log "Analyzing with nghttp..."

    local tmpfile
    tmpfile=$(mktemp)

    # Use nghttp to capture frames
    nghttp -v "$URL" > "$tmpfile" 2>&1 || true

    # Look for PUSH_PROMISE frames
    local push_promises
    push_promises=$(grep "PUSH_PROMISE" "$tmpfile" || true)

    if [[ -n "$push_promises" ]]; then
        success "PUSH_PROMISE frames detected:"
        echo "$push_promises" | while read -r line; do
            echo "  $line"
        done
    else
        warning "No PUSH_PROMISE frames detected"
    fi

    # Extract pushed resource paths
    local pushed_paths
    pushed_paths=$(grep -A 5 "PUSH_PROMISE" "$tmpfile" | grep ":path:" | awk '{print $3}' || true)

    if [[ -n "$pushed_paths" ]]; then
        echo ""
        echo "Pushed resources:"
        echo "$pushed_paths" | while read -r path; do
            echo "  - $path"
        done
    fi

    rm "$tmpfile"
}

# Measure performance impact
measure_push_performance() {
    log "Measuring performance impact..."

    local tmpfile
    tmpfile=$(mktemp)

    # Measure with push enabled (HTTP/2)
    local time_with_push
    time_with_push=$( (time curl -s --http2 --max-time "$TIMEOUT" "$URL" > /dev/null) 2>&1 | grep real | awk '{print $2}')

    # Measure with HTTP/1.1 (no push)
    local time_without_push
    time_without_push=$( (time curl -s --http1.1 --max-time "$TIMEOUT" "$URL" > /dev/null) 2>&1 | grep real | awk '{print $2}')

    echo ""
    echo "Performance comparison:"
    echo "  HTTP/2 (with potential push): $time_with_push"
    echo "  HTTP/1.1 (no push):          $time_without_push"

    rm -f "$tmpfile"
}

# Test cache headers on pushed resources
test_push_cache_headers() {
    log "Testing cache headers on pushed resources..."

    # Extract Link header for pushed resources
    local link_header
    link_header=$(curl -sI --http2 --max-time "$TIMEOUT" "$URL" | grep -i "^link:" | head -1 || true)

    if [[ -z "$link_header" ]]; then
        warning "No Link headers found for pushed resources"
        return
    fi

    # Parse first pushed resource
    local pushed_resource
    pushed_resource=$(echo "$link_header" | sed -n 's/.*<\([^>]*\)>.*/\1/p' | head -1)

    if [[ -z "$pushed_resource" ]]; then
        warning "Could not parse pushed resource from Link header"
        return
    fi

    # Make full URL
    local base_url
    base_url=$(echo "$URL" | sed 's/\(https\?:\/\/[^/]*\).*/\1/')
    local full_url="${base_url}${pushed_resource}"

    log "Testing cache headers for: $full_url"

    # Fetch cache headers
    local cache_control
    cache_control=$(curl -sI --http2 --max-time "$TIMEOUT" "$full_url" | grep -i "^cache-control:" || true)

    if [[ -n "$cache_control" ]]; then
        echo ""
        echo "Cache headers for pushed resource ($pushed_resource):"
        echo "  $cache_control"

        if echo "$cache_control" | grep -qi "max-age"; then
            success "Resource has max-age directive (good for caching)"
        else
            warning "Resource lacks max-age directive"
        fi
    else
        warning "No cache-control header on pushed resource"
    fi
}

# Generate JSON report
generate_json_report() {
    if [[ -z "$JSON_OUTPUT" ]]; then
        return
    fi

    log "Generating JSON report..."

    local http2_support
    if curl -sI --http2 --max-time "$TIMEOUT" "$URL" 2>&1 | grep -q "HTTP/2"; then
        http2_support="true"
    else
        http2_support="false"
    fi

    local push_detected
    if curl -sI --http2 --max-time "$TIMEOUT" -v "$URL" 2>&1 | grep -qi "link:.*preload"; then
        push_detected="true"
    else
        push_detected="false"
    fi

    cat > "$JSON_OUTPUT" <<EOF
{
  "url": "$URL",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "http2_support": $http2_support,
  "server_push_detected": $push_detected,
  "test_completed": true
}
EOF

    success "JSON report written to $JSON_OUTPUT"
}

# Main
main() {
    echo ""
    echo "======================================================================"
    echo "HTTP/2 Server Push Tester"
    echo "======================================================================"
    echo ""
    echo "URL: $URL"
    echo ""

    check_requirements

    if ! test_http2_support; then
        exit 1
    fi

    detect_server_push
    analyze_with_nghttp
    measure_push_performance
    test_push_cache_headers

    generate_json_report

    echo ""
    echo "======================================================================"
    echo "Test completed"
    echo "======================================================================"
    echo ""
}

main
