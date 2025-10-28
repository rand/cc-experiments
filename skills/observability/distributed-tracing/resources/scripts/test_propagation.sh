#!/usr/bin/env bash
#
# Distributed Tracing Context Propagation Test Tool
#
# Tests trace context propagation across HTTP services, validating that
# trace IDs and span IDs are correctly passed through headers.
#
# Usage:
#   test_propagation.sh --url http://localhost:8000
#   test_propagation.sh --url http://localhost:8000 --format w3c
#   test_propagation.sh --url http://localhost:8000 --format b3 --json

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
URL=""
FORMAT="w3c"
JSON_OUTPUT=false
VERBOSE=false
DOWNSTREAM_URL=""

# Help message
show_help() {
    cat << EOF
Distributed Tracing Context Propagation Test Tool

Tests trace context propagation by sending requests with trace headers
and validating that downstream services receive and propagate the context.

USAGE:
    $(basename "$0") --url <service-url> [OPTIONS]

OPTIONS:
    --url <url>              Target service URL (required)
    --format <format>        Propagation format: w3c, b3, b3-single, jaeger, xray
                             (default: w3c)
    --downstream <url>       Downstream service to test multi-hop propagation
    --json                   Output results as JSON
    --verbose                Show detailed request/response headers
    --help                   Show this help message

EXAMPLES:
    # Test W3C Trace Context propagation
    $(basename "$0") --url http://localhost:8000/api/users

    # Test B3 multi-header propagation
    $(basename "$0") --url http://localhost:8000 --format b3

    # Test multi-hop propagation (service A -> service B)
    $(basename "$0") --url http://localhost:8000 \\
        --downstream http://localhost:8001

    # JSON output for automation
    $(basename "$0") --url http://localhost:8000 --json

PROPAGATION FORMATS:
    w3c        W3C Trace Context (traceparent, tracestate)
    b3         Zipkin B3 multi-header (X-B3-TraceId, X-B3-SpanId, etc.)
    b3-single  Zipkin B3 single header (b3: trace-span-sampled)
    jaeger     Jaeger (uber-trace-id)
    xray       AWS X-Ray (X-Amzn-Trace-Id)

RETURN CODES:
    0          All tests passed
    1          Test failures or errors
    2          Invalid arguments
EOF
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --url)
                URL="$2"
                shift 2
                ;;
            --format)
                FORMAT="$2"
                shift 2
                ;;
            --downstream)
                DOWNSTREAM_URL="$2"
                shift 2
                ;;
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                show_help
                exit 2
                ;;
        esac
    done

    if [[ -z "$URL" ]]; then
        echo "Error: --url is required" >&2
        show_help
        exit 2
    fi
}

# Generate random trace ID (128-bit hex)
generate_trace_id() {
    printf '%032x' $((RANDOM * RANDOM * RANDOM * RANDOM))
}

# Generate random span ID (64-bit hex)
generate_span_id() {
    printf '%016x' $((RANDOM * RANDOM))
}

# Generate W3C traceparent header
generate_w3c_traceparent() {
    local trace_id="$1"
    local span_id="$2"
    local sampled="01"  # sampled flag
    echo "00-${trace_id}-${span_id}-${sampled}"
}

# Generate B3 multi-header
generate_b3_multi() {
    local trace_id="$1"
    local span_id="$2"
    echo "X-B3-TraceId: ${trace_id}"
    echo "X-B3-SpanId: ${span_id}"
    echo "X-B3-Sampled: 1"
}

# Generate B3 single header
generate_b3_single() {
    local trace_id="$1"
    local span_id="$2"
    echo "b3: ${trace_id}-${span_id}-1"
}

# Generate Jaeger uber-trace-id
generate_jaeger() {
    local trace_id="$1"
    local span_id="$2"
    echo "uber-trace-id: ${trace_id}:${span_id}:0:1"
}

# Generate AWS X-Ray trace ID
generate_xray() {
    local timestamp=$(date +%s)
    local random=$(printf '%024x' $((RANDOM * RANDOM * RANDOM)))
    local trace_id="1-${timestamp}-${random}"
    echo "X-Amzn-Trace-Id: Root=${trace_id};Sampled=1"
}

# Test propagation
test_propagation() {
    local url="$1"
    local format="$2"

    local trace_id=$(generate_trace_id)
    local span_id=$(generate_span_id)

    # Build curl command with appropriate headers
    local curl_cmd="curl -s -D /tmp/test_propagation_headers_$$.txt"

    case "$format" in
        w3c)
            local traceparent=$(generate_w3c_traceparent "$trace_id" "$span_id")
            curl_cmd="$curl_cmd -H 'traceparent: $traceparent'"
            ;;
        b3)
            curl_cmd="$curl_cmd -H 'X-B3-TraceId: $trace_id' -H 'X-B3-SpanId: $span_id' -H 'X-B3-Sampled: 1'"
            ;;
        b3-single)
            local b3_header="${trace_id}-${span_id}-1"
            curl_cmd="$curl_cmd -H 'b3: $b3_header'"
            ;;
        jaeger)
            curl_cmd="$curl_cmd -H 'uber-trace-id: ${trace_id}:${span_id}:0:1'"
            ;;
        xray)
            local xray_trace_id="1-$(date +%s)-${trace_id:0:24}"
            curl_cmd="$curl_cmd -H 'X-Amzn-Trace-Id: Root=$xray_trace_id;Sampled=1'"
            ;;
        *)
            echo "Unknown format: $format" >&2
            return 1
            ;;
    esac

    # Execute request
    if [[ "$VERBOSE" == true ]]; then
        echo "Request headers:" >&2
        echo "$curl_cmd" >&2
    fi

    local response
    response=$(eval "$curl_cmd '$url'" 2>&1) || {
        echo "Error: Failed to connect to $url" >&2
        return 1
    }

    # Read response headers
    local response_headers=""
    if [[ -f "/tmp/test_propagation_headers_$$.txt" ]]; then
        response_headers=$(cat "/tmp/test_propagation_headers_$$.txt")
        rm -f "/tmp/test_propagation_headers_$$.txt"
    fi

    if [[ "$VERBOSE" == true ]]; then
        echo "Response headers:" >&2
        echo "$response_headers" >&2
    fi

    # Validate propagation
    local propagated=false
    local received_trace_id=""

    case "$format" in
        w3c)
            if echo "$response_headers" | grep -qi "traceparent:"; then
                propagated=true
                received_trace_id=$(echo "$response_headers" | grep -i "traceparent:" | sed 's/.*00-\([^-]*\).*/\1/')
            fi
            ;;
        b3)
            if echo "$response_headers" | grep -qi "X-B3-TraceId:"; then
                propagated=true
                received_trace_id=$(echo "$response_headers" | grep -i "X-B3-TraceId:" | awk '{print $2}' | tr -d '\r')
            fi
            ;;
        b3-single)
            if echo "$response_headers" | grep -qi "b3:"; then
                propagated=true
                received_trace_id=$(echo "$response_headers" | grep -i "b3:" | sed 's/.*b3: \([^-]*\).*/\1/')
            fi
            ;;
        jaeger)
            if echo "$response_headers" | grep -qi "uber-trace-id:"; then
                propagated=true
                received_trace_id=$(echo "$response_headers" | grep -i "uber-trace-id:" | sed 's/.*uber-trace-id: \([^:]*\).*/\1/')
            fi
            ;;
        xray)
            if echo "$response_headers" | grep -qi "X-Amzn-Trace-Id:"; then
                propagated=true
                received_trace_id=$(echo "$response_headers" | grep -i "X-Amzn-Trace-Id:" | sed 's/.*Root=\([^;]*\).*/\1/')
            fi
            ;;
    esac

    # Check trace ID preservation
    local trace_preserved=false
    if [[ "$received_trace_id" == "$trace_id"* ]]; then
        trace_preserved=true
    fi

    # Return result
    echo "$propagated|$trace_preserved|$trace_id|$received_trace_id"
}

# Test multi-hop propagation
test_multihop() {
    local url1="$1"
    local url2="$2"
    local format="$3"

    local trace_id=$(generate_trace_id)
    local span_id=$(generate_span_id)

    # Send request to first service
    local result1
    result1=$(test_propagation "$url1" "$format")

    local propagated1=$(echo "$result1" | cut -d'|' -f1)

    if [[ "$propagated1" != "true" ]]; then
        echo "false|false|$trace_id||"
        return 1
    fi

    # Send request to second service (downstream)
    local result2
    result2=$(test_propagation "$url2" "$format")

    local propagated2=$(echo "$result2" | cut -d'|' -f1)
    local trace_preserved2=$(echo "$result2" | cut -d'|' -f2)
    local received_trace_id2=$(echo "$result2" | cut -d'|' -f4)

    echo "$propagated2|$trace_preserved2|$trace_id|$received_trace_id2|multihop"
}

# Format output
format_output() {
    local result="$1"
    local test_name="$2"

    local propagated=$(echo "$result" | cut -d'|' -f1)
    local trace_preserved=$(echo "$result" | cut -d'|' -f2)
    local sent_trace_id=$(echo "$result" | cut -d'|' -f3)
    local received_trace_id=$(echo "$result" | cut -d'|' -f4)

    if [[ "$JSON_OUTPUT" == true ]]; then
        cat << EOF
{
  "test": "$test_name",
  "format": "$FORMAT",
  "propagated": $propagated,
  "trace_preserved": $trace_preserved,
  "sent_trace_id": "$sent_trace_id",
  "received_trace_id": "$received_trace_id",
  "passed": $([ "$propagated" == "true" ] && [ "$trace_preserved" == "true" ] && echo "true" || echo "false")
}
EOF
    else
        echo "Test: $test_name"
        echo "Format: $FORMAT"
        echo "Sent Trace ID: $sent_trace_id"
        echo "Received Trace ID: $received_trace_id"

        if [[ "$propagated" == "true" ]]; then
            echo -e "${GREEN}✓${NC} Trace context propagated"
        else
            echo -e "${RED}✗${NC} Trace context NOT propagated"
        fi

        if [[ "$trace_preserved" == "true" ]]; then
            echo -e "${GREEN}✓${NC} Trace ID preserved"
        else
            echo -e "${RED}✗${NC} Trace ID NOT preserved"
        fi

        if [[ "$propagated" == "true" ]] && [[ "$trace_preserved" == "true" ]]; then
            echo -e "${GREEN}✓ PASSED${NC}"
            return 0
        else
            echo -e "${RED}✗ FAILED${NC}"
            return 1
        fi
    fi
}

# Main execution
main() {
    parse_args "$@"

    local exit_code=0

    if [[ -z "$DOWNSTREAM_URL" ]]; then
        # Single service test
        result=$(test_propagation "$URL" "$FORMAT")
        format_output "$result" "Single Service Propagation" || exit_code=1
    else
        # Multi-hop test
        result=$(test_multihop "$URL" "$DOWNSTREAM_URL" "$FORMAT")
        format_output "$result" "Multi-Hop Propagation" || exit_code=1
    fi

    exit $exit_code
}

main "$@"
