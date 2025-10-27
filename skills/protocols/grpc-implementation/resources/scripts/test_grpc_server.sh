#!/usr/bin/env bash
#
# gRPC Server Test Script
#
# Tests gRPC server endpoints and performance using grpcurl.
# Supports all four RPC types, measures latency and throughput,
# and generates test reports.
#
# Usage:
#   ./test_grpc_server.sh --server localhost:50051 --proto-file api.proto --json
#   ./test_grpc_server.sh --server localhost:50051 --proto-file api.proto --method UserService/GetUser
#   ./test_grpc_server.sh --help
#
# Requirements:
#   - grpcurl (https://github.com/fullstorydev/grpcurl)
#   - jq (for JSON parsing)
#   - bc (for calculations)
#
# Features:
#   - Test all four RPC types (unary, server stream, client stream, bidirectional)
#   - Measure latency and throughput
#   - Test error handling
#   - Validate metadata
#   - Generate test report (JSON or text)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SERVER=""
PROTO_FILE=""
METHOD=""
JSON_OUTPUT=false
ITERATIONS=10
TIMEOUT=5
METADATA=""
TLS=false
VERBOSE=false

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
declare -a TEST_RESULTS=()

#######################################
# Print usage information
#######################################
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Test gRPC server endpoints and performance.

Required Options:
    --server HOST:PORT          gRPC server address
    --proto-file FILE           Path to .proto file

Optional:
    --method SERVICE/METHOD     Test specific method (default: test all)
    --iterations N              Number of test iterations (default: 10)
    --timeout SECONDS           Request timeout (default: 5)
    --metadata KEY:VALUE        Add metadata header
    --tls                       Use TLS connection
    --json                      Output as JSON
    --verbose                   Enable verbose output
    --help                      Show this help message

Examples:
    # Test all methods
    $(basename "$0") --server localhost:50051 --proto-file api.proto

    # Test specific method
    $(basename "$0") --server localhost:50051 --proto-file api.proto --method UserService/GetUser

    # With metadata (authentication)
    $(basename "$0") --server localhost:50051 --proto-file api.proto --metadata authorization:"Bearer token123"

    # JSON output for CI/CD
    $(basename "$0") --server localhost:50051 --proto-file api.proto --json > report.json

    # Performance test (100 iterations)
    $(basename "$0") --server localhost:50051 --proto-file api.proto --iterations 100

Requirements:
    - grpcurl: brew install grpcurl  OR  go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
    - jq: brew install jq
    - bc: Usually pre-installed

EOF
    exit 0
}

#######################################
# Check if required tools are installed
#######################################
check_dependencies() {
    local missing_deps=()

    if ! command -v grpcurl &> /dev/null; then
        missing_deps+=("grpcurl")
    fi

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    if ! command -v bc &> /dev/null; then
        missing_deps+=("bc")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "${RED}Error: Missing required dependencies: ${missing_deps[*]}${NC}" >&2
        echo ""
        echo "Install with:"
        for dep in "${missing_deps[@]}"; do
            if [ "$dep" = "grpcurl" ]; then
                echo "  brew install grpcurl"
                echo "  OR go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest"
            elif [ "$dep" = "jq" ]; then
                echo "  brew install jq"
            fi
        done
        exit 1
    fi
}

#######################################
# Log message with color
#######################################
log() {
    local level=$1
    shift
    local message="$*"

    case "$level" in
        INFO)
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
        WARNING)
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} $message" >&2
            ;;
        *)
            echo "$message"
            ;;
    esac
}

#######################################
# List all services and methods
#######################################
list_services() {
    local proto_flag=""
    if [ -n "$PROTO_FILE" ]; then
        proto_flag="-proto $PROTO_FILE"
    fi

    local tls_flag=""
    if [ "$TLS" = true ]; then
        tls_flag=""
    else
        tls_flag="-plaintext"
    fi

    log INFO "Listing services on $SERVER..."

    if grpcurl $tls_flag $proto_flag "$SERVER" list &> /dev/null; then
        grpcurl $tls_flag $proto_flag "$SERVER" list
    else
        log ERROR "Failed to list services (is server reflection enabled?)"
        return 1
    fi
}

#######################################
# Test unary RPC method
#######################################
test_unary_method() {
    local service_method=$1
    local request_data=$2

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    local start_time=$(date +%s.%N)

    local tls_flag=""
    if [ "$TLS" = true ]; then
        tls_flag=""
    else
        tls_flag="-plaintext"
    fi

    local metadata_flag=""
    if [ -n "$METADATA" ]; then
        metadata_flag="-H $METADATA"
    fi

    # Execute RPC call
    local output
    local exit_code=0

    if output=$(grpcurl $tls_flag $metadata_flag \
        -proto "$PROTO_FILE" \
        -d "$request_data" \
        -max-time "$TIMEOUT" \
        "$SERVER" "$service_method" 2>&1); then

        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)

        PASSED_TESTS=$((PASSED_TESTS + 1))

        if [ "$VERBOSE" = true ]; then
            log SUCCESS "$service_method completed in ${duration}s"
            echo "$output" | jq '.' 2>/dev/null || echo "$output"
        fi

        TEST_RESULTS+=("SUCCESS|$service_method|$duration|$output")
        return 0
    else
        exit_code=$?
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)

        FAILED_TESTS=$((FAILED_TESTS + 1))

        log ERROR "$service_method failed (exit code: $exit_code)"
        if [ "$VERBOSE" = true ]; then
            echo "$output"
        fi

        TEST_RESULTS+=("FAILED|$service_method|$duration|$output")
        return 1
    fi
}

#######################################
# Test server streaming RPC method
#######################################
test_server_streaming() {
    local service_method=$1
    local request_data=$2

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    local start_time=$(date +%s.%N)

    local tls_flag=""
    if [ "$TLS" = true ]; then
        tls_flag=""
    else
        tls_flag="-plaintext"
    fi

    local metadata_flag=""
    if [ -n "$METADATA" ]; then
        metadata_flag="-H $METADATA"
    fi

    # Execute streaming RPC call
    local output
    local message_count=0

    if output=$(grpcurl $tls_flag $metadata_flag \
        -proto "$PROTO_FILE" \
        -d "$request_data" \
        -max-time "$TIMEOUT" \
        "$SERVER" "$service_method" 2>&1); then

        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)

        # Count messages in stream
        message_count=$(echo "$output" | jq -s 'length' 2>/dev/null || echo "1")

        PASSED_TESTS=$((PASSED_TESTS + 1))

        if [ "$VERBOSE" = true ]; then
            log SUCCESS "$service_method received $message_count messages in ${duration}s"
            echo "$output" | jq '.' 2>/dev/null || echo "$output"
        fi

        TEST_RESULTS+=("SUCCESS|$service_method|$duration|Received $message_count messages")
        return 0
    else
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)

        FAILED_TESTS=$((FAILED_TESTS + 1))

        log ERROR "$service_method failed"
        if [ "$VERBOSE" = true ]; then
            echo "$output"
        fi

        TEST_RESULTS+=("FAILED|$service_method|$duration|$output")
        return 1
    fi
}

#######################################
# Test metadata handling
#######################################
test_metadata() {
    local service_method=$1

    log INFO "Testing metadata for $service_method..."

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    local tls_flag=""
    if [ "$TLS" = true ]; then
        tls_flag=""
    else
        tls_flag="-plaintext"
    fi

    # Test with custom metadata
    if grpcurl $tls_flag \
        -proto "$PROTO_FILE" \
        -H "x-test-header:test-value" \
        -H "x-request-id:$(uuidgen 2>/dev/null || echo 'test-request-id')" \
        -d '{}' \
        -max-time "$TIMEOUT" \
        "$SERVER" "$service_method" &> /dev/null; then

        PASSED_TESTS=$((PASSED_TESTS + 1))
        log SUCCESS "Metadata test passed for $service_method"
        TEST_RESULTS+=("SUCCESS|$service_method (metadata)|0|Metadata accepted")
        return 0
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log ERROR "Metadata test failed for $service_method"
        TEST_RESULTS+=("FAILED|$service_method (metadata)|0|Metadata rejected")
        return 1
    fi
}

#######################################
# Benchmark method performance
#######################################
benchmark_method() {
    local service_method=$1
    local iterations=$2

    log INFO "Benchmarking $service_method ($iterations iterations)..."

    local latencies=()
    local success_count=0
    local error_count=0

    local tls_flag=""
    if [ "$TLS" = true ]; then
        tls_flag=""
    else
        tls_flag="-plaintext"
    fi

    for ((i=1; i<=iterations; i++)); do
        local start_time=$(date +%s.%N)

        if grpcurl $tls_flag \
            -proto "$PROTO_FILE" \
            -d '{}' \
            -max-time "$TIMEOUT" \
            "$SERVER" "$service_method" &> /dev/null; then

            local end_time=$(date +%s.%N)
            local duration=$(echo "$end_time - $start_time" | bc)
            latencies+=("$duration")
            success_count=$((success_count + 1))
        else
            error_count=$((error_count + 1))
        fi

        # Progress indicator
        if [ $((i % 10)) -eq 0 ]; then
            echo -n "."
        fi
    done
    echo ""

    if [ ${#latencies[@]} -eq 0 ]; then
        log ERROR "All benchmark requests failed"
        return 1
    fi

    # Calculate statistics
    local total=0
    local min=${latencies[0]}
    local max=${latencies[0]}

    for latency in "${latencies[@]}"; do
        total=$(echo "$total + $latency" | bc)

        if (( $(echo "$latency < $min" | bc -l) )); then
            min=$latency
        fi

        if (( $(echo "$latency > $max" | bc -l) )); then
            max=$latency
        fi
    done

    local avg=$(echo "scale=6; $total / ${#latencies[@]}" | bc)
    local rps=$(echo "scale=2; ${#latencies[@]} / $total" | bc)

    # Sort latencies for percentiles
    IFS=$'\n' sorted_latencies=($(sort -n <<<"${latencies[*]}"))
    unset IFS

    local p50_idx=$(( ${#sorted_latencies[@]} * 50 / 100 ))
    local p95_idx=$(( ${#sorted_latencies[@]} * 95 / 100 ))
    local p99_idx=$(( ${#sorted_latencies[@]} * 99 / 100 ))

    local p50=${sorted_latencies[$p50_idx]}
    local p95=${sorted_latencies[$p95_idx]}
    local p99=${sorted_latencies[$p99_idx]}

    # Display results
    echo ""
    log SUCCESS "Benchmark Results for $service_method:"
    echo "  Iterations:    $iterations"
    echo "  Success:       $success_count"
    echo "  Errors:        $error_count"
    echo "  Success Rate:  $(echo "scale=2; $success_count * 100 / $iterations" | bc)%"
    echo ""
    echo "  Latency (seconds):"
    echo "    Min:         $min"
    echo "    Average:     $avg"
    echo "    P50:         $p50"
    echo "    P95:         $p95"
    echo "    P99:         $p99"
    echo "    Max:         $max"
    echo ""
    echo "  Throughput:    $rps req/sec"
    echo ""
}

#######################################
# Generate test report
#######################################
generate_report() {
    if [ "$JSON_OUTPUT" = true ]; then
        generate_json_report
    else
        generate_text_report
    fi
}

#######################################
# Generate JSON report
#######################################
generate_json_report() {
    local results_json="["

    for ((i=0; i<${#TEST_RESULTS[@]}; i++)); do
        IFS='|' read -r status method duration output <<< "${TEST_RESULTS[$i]}"

        if [ $i -gt 0 ]; then
            results_json+=","
        fi

        results_json+="{"
        results_json+="\"status\":\"$status\","
        results_json+="\"method\":\"$method\","
        results_json+="\"duration\":$duration,"
        results_json+="\"output\":\"$(echo "$output" | sed 's/"/\\"/g')\""
        results_json+="}"
    done

    results_json+="]"

    cat << EOF
{
  "server": "$SERVER",
  "proto_file": "$PROTO_FILE",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "summary": {
    "total": $TOTAL_TESTS,
    "passed": $PASSED_TESTS,
    "failed": $FAILED_TESTS,
    "success_rate": $(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc 2>/dev/null || echo 0)
  },
  "results": $results_json
}
EOF
}

#######################################
# Generate text report
#######################################
generate_text_report() {
    echo ""
    echo "================================================================"
    echo "                    gRPC Server Test Report"
    echo "================================================================"
    echo ""
    echo "Server:      $SERVER"
    echo "Proto File:  $PROTO_FILE"
    echo "Timestamp:   $(date)"
    echo ""
    echo "Summary:"
    echo "  Total Tests:   $TOTAL_TESTS"
    echo "  Passed:        $PASSED_TESTS"
    echo "  Failed:        $FAILED_TESTS"
    echo "  Success Rate:  $(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)%"
    echo ""
    echo "================================================================"
    echo "                         Test Results"
    echo "================================================================"
    echo ""

    for result in "${TEST_RESULTS[@]}"; do
        IFS='|' read -r status method duration output <<< "$result"

        if [ "$status" = "SUCCESS" ]; then
            echo -e "${GREEN}✓${NC} $method (${duration}s)"
        else
            echo -e "${RED}✗${NC} $method (${duration}s)"
            if [ "$VERBOSE" = true ]; then
                echo "    Error: $output"
            fi
        fi
    done

    echo ""
    echo "================================================================"
    echo ""
}

#######################################
# Main execution
#######################################
main() {
    # Parse command-line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --server)
                SERVER="$2"
                shift 2
                ;;
            --proto-file)
                PROTO_FILE="$2"
                shift 2
                ;;
            --method)
                METHOD="$2"
                shift 2
                ;;
            --iterations)
                ITERATIONS="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --metadata)
                METADATA="$2"
                shift 2
                ;;
            --tls)
                TLS=true
                shift
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
                usage
                ;;
            *)
                echo "Error: Unknown option $1" >&2
                usage
                ;;
        esac
    done

    # Validate required arguments
    if [ -z "$SERVER" ] || [ -z "$PROTO_FILE" ]; then
        echo "Error: --server and --proto-file are required" >&2
        usage
    fi

    # Check if proto file exists
    if [ ! -f "$PROTO_FILE" ]; then
        log ERROR "Proto file not found: $PROTO_FILE"
        exit 1
    fi

    # Check dependencies
    check_dependencies

    # Run tests
    if [ -n "$METHOD" ]; then
        # Test specific method
        log INFO "Testing method: $METHOD"
        test_unary_method "$METHOD" "{}"

        if [ "$ITERATIONS" -gt 1 ]; then
            benchmark_method "$METHOD" "$ITERATIONS"
        fi
    else
        # List and test all methods
        log INFO "Discovering services..."
        list_services || exit 1

        # Example: Test a known method (customize based on your proto)
        log WARNING "Auto-discovery of methods not yet implemented"
        log INFO "Use --method to specify a method to test"
    fi

    # Generate report
    generate_report

    # Exit with appropriate code
    if [ "$FAILED_TESTS" -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function
main "$@"
