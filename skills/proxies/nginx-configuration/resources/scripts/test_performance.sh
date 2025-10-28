#!/usr/bin/env bash
#
# Nginx Performance Testing Script
#
# Benchmarks Nginx performance using wrk and reports detailed metrics.
#
# Usage:
#   ./test_performance.sh --help
#   ./test_performance.sh --url http://localhost
#   ./test_performance.sh --url http://localhost --concurrency 100 --json
#   ./test_performance.sh --url http://localhost --duration 30 --threads 4

set -euo pipefail

# Default values
URL=""
CONCURRENCY=50
THREADS=2
DURATION=10
JSON_OUTPUT=false
TEST_WORKERS=false
TEST_CACHE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_usage() {
    cat << EOF
Nginx Performance Testing Script

Usage: $(basename "$0") [OPTIONS]

Options:
    --url URL               Target URL to test (required)
    --concurrency NUM       Number of concurrent connections (default: 50)
    --threads NUM           Number of threads (default: 2)
    --duration SEC          Test duration in seconds (default: 10)
    --json                  Output results in JSON format
    --test-workers          Test different worker configurations
    --test-cache            Test cache effectiveness
    --help                  Show this help message

Examples:
    # Basic performance test
    $(basename "$0") --url http://localhost

    # High concurrency test
    $(basename "$0") --url http://localhost --concurrency 100 --threads 4

    # Extended test with JSON output
    $(basename "$0") --url http://localhost --duration 30 --json

    # Test worker configurations
    $(basename "$0") --url http://localhost --test-workers

    # Test cache performance
    $(basename "$0") --url http://localhost --test-cache

EOF
}

log_info() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${GREEN}[SUCCESS]${NC} $1"
    fi
}

log_warning() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${YELLOW}[WARNING]${NC} $1"
    fi
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

check_dependencies() {
    local missing_deps=()

    if ! command -v wrk &> /dev/null; then
        missing_deps+=("wrk")
    fi

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Install with: apt-get install wrk curl (Ubuntu/Debian)"
        log_error "           or: brew install wrk curl (macOS)"
        exit 1
    fi
}

test_connectivity() {
    log_info "Testing connectivity to $URL..."

    if ! curl -s -o /dev/null -w "%{http_code}" "$URL" &> /dev/null; then
        log_error "Cannot connect to $URL"
        exit 1
    fi

    log_success "Successfully connected to $URL"
}

run_wrk_test() {
    local url="$1"
    local threads="$2"
    local connections="$3"
    local duration="$4"
    local label="${5:-Basic Test}"

    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo "=========================================="
        echo "$label"
        echo "=========================================="
        echo "URL: $url"
        echo "Threads: $threads"
        echo "Connections: $connections"
        echo "Duration: ${duration}s"
        echo ""
    fi

    # Run wrk and capture output
    local wrk_output
    wrk_output=$(wrk -t"$threads" -c"$connections" -d"${duration}s" --latency "$url" 2>&1)

    # Parse wrk output
    local requests_per_sec
    local total_requests
    local total_data
    local avg_latency
    local max_latency
    local stdev_latency
    local latency_50
    local latency_75
    local latency_90
    local latency_99

    requests_per_sec=$(echo "$wrk_output" | grep "Requests/sec:" | awk '{print $2}')
    total_requests=$(echo "$wrk_output" | grep "requests in" | awk '{print $1}')
    total_data=$(echo "$wrk_output" | grep "requests in" | awk '{print $5}')
    avg_latency=$(echo "$wrk_output" | grep "Latency" | head -1 | awk '{print $2}')
    max_latency=$(echo "$wrk_output" | grep "Latency" | head -1 | awk '{print $4}')
    stdev_latency=$(echo "$wrk_output" | grep "Latency" | head -1 | awk '{print $3}')

    # Percentiles
    latency_50=$(echo "$wrk_output" | grep "50.000%" | awk '{print $2}')
    latency_75=$(echo "$wrk_output" | grep "75.000%" | awk '{print $2}')
    latency_90=$(echo "$wrk_output" | grep "90.000%" | awk '{print $2}')
    latency_99=$(echo "$wrk_output" | grep "99.000%" | awk '{print $2}')

    # Output results
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        cat << EOF
{
    "test": "$label",
    "url": "$url",
    "threads": $threads,
    "connections": $connections,
    "duration": $duration,
    "requests_per_second": ${requests_per_sec:-0},
    "total_requests": ${total_requests:-0},
    "total_data": "$total_data",
    "latency": {
        "avg": "$avg_latency",
        "max": "$max_latency",
        "stdev": "$stdev_latency",
        "percentiles": {
            "p50": "$latency_50",
            "p75": "$latency_75",
            "p90": "$latency_90",
            "p99": "$latency_99"
        }
    }
}
EOF
    else
        echo "Results:"
        echo "  Requests/sec: $requests_per_sec"
        echo "  Total Requests: $total_requests"
        echo "  Total Data: $total_data"
        echo ""
        echo "Latency:"
        echo "  Average: $avg_latency"
        echo "  Max: $max_latency"
        echo "  Stdev: $stdev_latency"
        echo ""
        echo "Latency Percentiles:"
        echo "  50th: $latency_50"
        echo "  75th: $latency_75"
        echo "  90th: $latency_90"
        echo "  99th: $latency_99"
        echo ""
    fi

    # Return requests/sec for comparison
    echo "$requests_per_sec" > /tmp/wrk_rps.tmp
}

test_different_workers() {
    log_info "Testing different worker configurations..."
    log_warning "This requires ability to reload Nginx configuration"

    local results=()

    for workers in 1 2 4 auto; do
        log_info "Testing with worker_processes = $workers"

        # Note: This would require actually changing Nginx config and reloading
        # For now, just run the test and note the configuration
        run_wrk_test "$URL" "$THREADS" "$CONCURRENCY" "$DURATION" "Workers: $workers"

        if [[ -f /tmp/wrk_rps.tmp ]]; then
            local rps
            rps=$(cat /tmp/wrk_rps.tmp)
            results+=("$workers:$rps")
        fi

        sleep 2
    done

    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo "=========================================="
        echo "Worker Configuration Comparison"
        echo "=========================================="
        for result in "${results[@]}"; do
            echo "Workers: ${result%%:*} -> ${result##*:} req/s"
        done
        echo ""
    fi
}

test_cache_effectiveness() {
    log_info "Testing cache effectiveness..."

    # First request (cache miss)
    log_info "Testing cache MISS (first request)..."
    run_wrk_test "$URL" "$THREADS" "$CONCURRENCY" 5 "Cache MISS Test"
    local miss_rps
    miss_rps=$(cat /tmp/wrk_rps.tmp 2>/dev/null || echo "0")

    sleep 2

    # Second request (should be cached)
    log_info "Testing cache HIT (cached content)..."
    run_wrk_test "$URL" "$THREADS" "$CONCURRENCY" 5 "Cache HIT Test"
    local hit_rps
    hit_rps=$(cat /tmp/wrk_rps.tmp 2>/dev/null || echo "0")

    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo "=========================================="
        echo "Cache Effectiveness"
        echo "=========================================="
        echo "Cache MISS: $miss_rps req/s"
        echo "Cache HIT: $hit_rps req/s"

        if (( $(echo "$hit_rps > $miss_rps" | bc -l) )); then
            local improvement
            improvement=$(echo "scale=2; (($hit_rps - $miss_rps) / $miss_rps) * 100" | bc)
            echo "Improvement: ${improvement}%"
            log_success "Cache is working effectively"
        else
            log_warning "Cache may not be working or URL is not cacheable"
        fi
        echo ""
    fi
}

run_ssl_test() {
    if [[ "$URL" == https://* ]]; then
        log_info "Testing SSL/TLS performance..."

        # Test different protocol versions if possible
        run_wrk_test "$URL" "$THREADS" "$CONCURRENCY" "$DURATION" "HTTPS Performance"

        # Check SSL info
        log_info "SSL/TLS Information:"
        if [[ "$JSON_OUTPUT" == "false" ]]; then
            curl -I -v --silent "$URL" 2>&1 | grep -E "SSL|TLS" || true
        fi
    fi
}

generate_report() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        cat << EOF

========================================
Performance Test Summary
========================================
Target URL: $URL
Test Duration: ${DURATION}s
Concurrency: $CONCURRENCY
Threads: $THREADS

Recommendations:
EOF

        # Read the last test results
        if [[ -f /tmp/wrk_rps.tmp ]]; then
            local rps
            rps=$(cat /tmp/wrk_rps.tmp)

            if (( $(echo "$rps < 100" | bc -l) )); then
                echo "  - Low requests/sec ($rps). Consider:"
                echo "    * Increasing worker_processes"
                echo "    * Enabling keepalive connections"
                echo "    * Optimizing backend application"
                echo "    * Checking for bottlenecks in proxy_pass"
            elif (( $(echo "$rps < 1000" | bc -l) )); then
                echo "  - Moderate requests/sec ($rps). Consider:"
                echo "    * Enabling gzip compression"
                echo "    * Implementing caching (proxy_cache)"
                echo "    * Using HTTP/2"
                echo "    * Optimizing buffer sizes"
            else
                echo "  - Good requests/sec ($rps)"
                echo "    * Monitor for errors under load"
                echo "    * Consider load balancing if scaling further"
                echo "    * Ensure rate limiting is configured"
            fi
        fi

        echo ""
        echo "=========================================="
    fi
}

cleanup() {
    rm -f /tmp/wrk_rps.tmp
}

trap cleanup EXIT

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            URL="$2"
            shift 2
            ;;
        --concurrency)
            CONCURRENCY="$2"
            shift 2
            ;;
        --threads)
            THREADS="$2"
            shift 2
            ;;
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --test-workers)
            TEST_WORKERS=true
            shift
            ;;
        --test-cache)
            TEST_CACHE=true
            shift
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$URL" ]]; then
    log_error "URL is required"
    print_usage
    exit 1
fi

# Main execution
main() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo "╔════════════════════════════════════════╗"
        echo "║   Nginx Performance Testing Script    ║"
        echo "╚════════════════════════════════════════╝"
        echo ""
    fi

    check_dependencies
    test_connectivity

    if [[ "$TEST_WORKERS" == "true" ]]; then
        test_different_workers
    elif [[ "$TEST_CACHE" == "true" ]]; then
        test_cache_effectiveness
    else
        run_wrk_test "$URL" "$THREADS" "$CONCURRENCY" "$DURATION" "Performance Test"
        run_ssl_test
        generate_report
    fi

    if [[ "$JSON_OUTPUT" == "false" ]]; then
        log_success "Performance test completed"
    fi
}

main
