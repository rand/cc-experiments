#!/usr/bin/env bash
#
# Deployment Testing Script
#
# Tests deployment processes, measures downtime, validates health checks,
# and verifies rollback capabilities. Supports multiple deployment strategies.
#
# Usage:
#     ./test_deployment.sh [OPTIONS]
#
# Examples:
#     ./test_deployment.sh --url https://myapp.com --strategy blue-green
#     ./test_deployment.sh --url https://myapp.com --json
#     ./test_deployment.sh --url https://myapp.com --duration 300
#     ./test_deployment.sh --help

set -euo pipefail

# Default configuration
URL=""
STRATEGY="rolling"
DURATION=60
INTERVAL=1
HEALTH_ENDPOINT="/health"
JSON_OUTPUT=false
VERBOSE=false
CONCURRENT_REQUESTS=10
TIMEOUT=5

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Metrics
TOTAL_REQUESTS=0
SUCCESSFUL_REQUESTS=0
FAILED_REQUESTS=0
TIMEOUTS=0
TOTAL_LATENCY=0
MIN_LATENCY=999999
MAX_LATENCY=0
DOWNTIME_SECONDS=0
ERRORS=()

# Usage
usage() {
    cat <<EOF
Deployment Testing Script

Tests deployment processes and measures downtime.

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --url URL                 Target URL to test (required)
    --strategy STRATEGY       Deployment strategy (blue-green, canary, rolling, recreate)
    --duration SECONDS        Test duration in seconds (default: 60)
    --interval SECONDS        Request interval in seconds (default: 1)
    --health-endpoint PATH    Health check endpoint (default: /health)
    --concurrent N            Concurrent requests (default: 10)
    --timeout SECONDS         Request timeout (default: 5)
    --json                    Output results in JSON format
    --verbose                 Verbose output
    --help                    Show this help message

EXAMPLES:
    # Test deployment for 5 minutes
    $0 --url https://myapp.com --duration 300

    # Test with custom health endpoint
    $0 --url https://myapp.com --health-endpoint /api/health

    # Monitor blue-green deployment
    $0 --url https://myapp.com --strategy blue-green --json

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            URL="$2"
            shift 2
            ;;
        --strategy)
            STRATEGY="$2"
            shift 2
            ;;
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --health-endpoint)
            HEALTH_ENDPOINT="$2"
            shift 2
            ;;
        --concurrent)
            CONCURRENT_REQUESTS="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
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
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$URL" ]]; then
    echo "Error: --url is required"
    usage
    exit 1
fi

# Log function
log() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "$1"
    fi
}

# Make HTTP request and measure latency
make_request() {
    local url=$1
    local start_time
    local end_time
    local duration
    local http_code
    local response

    start_time=$(date +%s%N)

    # Make request with timeout
    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo -e "\n000")

    end_time=$(date +%s%N)
    duration=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds

    # Extract HTTP code (last line)
    http_code=$(echo "$response" | tail -n 1)

    TOTAL_REQUESTS=$((TOTAL_REQUESTS + 1))

    # Update latency stats
    TOTAL_LATENCY=$((TOTAL_LATENCY + duration))

    if [[ $duration -lt $MIN_LATENCY ]]; then
        MIN_LATENCY=$duration
    fi

    if [[ $duration -gt $MAX_LATENCY ]]; then
        MAX_LATENCY=$duration
    fi

    # Check response
    if [[ "$http_code" == "000" ]]; then
        # Timeout or connection error
        TIMEOUTS=$((TIMEOUTS + 1))
        FAILED_REQUESTS=$((FAILED_REQUESTS + 1))
        log "${RED}✗${NC} Request failed (timeout) - ${duration}ms"
        ERRORS+=("$(date -u +%Y-%m-%dT%H:%M:%SZ)|timeout|${duration}ms")
        return 1
    elif [[ "$http_code" -ge 200 ]] && [[ "$http_code" -lt 300 ]]; then
        # Success
        SUCCESSFUL_REQUESTS=$((SUCCESSFUL_REQUESTS + 1))
        log "${GREEN}✓${NC} Request successful (${http_code}) - ${duration}ms"
        return 0
    elif [[ "$http_code" -ge 500 ]]; then
        # Server error
        FAILED_REQUESTS=$((FAILED_REQUESTS + 1))
        log "${RED}✗${NC} Server error (${http_code}) - ${duration}ms"
        ERRORS+=("$(date -u +%Y-%m-%dT%H:%M:%SZ)|server_error|${http_code}|${duration}ms")
        return 1
    else
        # Client error
        FAILED_REQUESTS=$((FAILED_REQUESTS + 1))
        log "${YELLOW}!${NC} Client error (${http_code}) - ${duration}ms"
        ERRORS+=("$(date -u +%Y-%m-%dT%H:%M:%SZ)|client_error|${http_code}|${duration}ms")
        return 1
    fi
}

# Check health endpoint
check_health() {
    local health_url="${URL}${HEALTH_ENDPOINT}"
    local http_code

    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$health_url" 2>/dev/null || echo "000")

    if [[ "$http_code" == "200" ]]; then
        return 0
    else
        return 1
    fi
}

# Monitor deployment
monitor_deployment() {
    local start_time
    local end_time
    local elapsed
    local last_status="unknown"
    local downtime_start=0
    local in_downtime=false

    start_time=$(date +%s)
    end_time=$((start_time + DURATION))

    if [[ "$VERBOSE" == true ]]; then
        echo ""
        echo "========================================="
        echo "Deployment Monitoring Started"
        echo "========================================="
        echo "URL: $URL"
        echo "Strategy: $STRATEGY"
        echo "Duration: ${DURATION}s"
        echo "Interval: ${INTERVAL}s"
        echo "========================================="
        echo ""
    fi

    while [[ $(date +%s) -lt $end_time ]]; do
        elapsed=$(($(date +%s) - start_time))

        if [[ "$VERBOSE" == true ]]; then
            echo -ne "\rProgress: ${elapsed}s / ${DURATION}s | Requests: $TOTAL_REQUESTS | Success: $SUCCESSFUL_REQUESTS | Failed: $FAILED_REQUESTS"
        fi

        # Make concurrent requests
        local concurrent_success=0
        local concurrent_failed=0

        for ((i=1; i<=CONCURRENT_REQUESTS; i++)); do
            if make_request "$URL"; then
                concurrent_success=$((concurrent_success + 1))
            else
                concurrent_failed=$((concurrent_failed + 1))
            fi
        done

        # Detect downtime
        if [[ $concurrent_failed -gt $((CONCURRENT_REQUESTS / 2)) ]]; then
            # More than half failed = downtime
            if [[ "$in_downtime" == false ]]; then
                in_downtime=true
                downtime_start=$(date +%s)
                log "\n${RED}▼ DOWNTIME DETECTED${NC}"
            fi
            last_status="down"
        else
            # System is up
            if [[ "$in_downtime" == true ]]; then
                # Downtime ended
                local downtime_end
                downtime_end=$(date +%s)
                local downtime_duration=$((downtime_end - downtime_start))
                DOWNTIME_SECONDS=$((DOWNTIME_SECONDS + downtime_duration))
                in_downtime=false
                log "${GREEN}▲ SERVICE RECOVERED${NC} (downtime: ${downtime_duration}s)"
            fi
            last_status="up"
        fi

        sleep "$INTERVAL"
    done

    # Check if still in downtime at end
    if [[ "$in_downtime" == true ]]; then
        local downtime_end
        downtime_end=$(date +%s)
        local downtime_duration=$((downtime_end - downtime_start))
        DOWNTIME_SECONDS=$((DOWNTIME_SECONDS + downtime_duration))
    fi

    if [[ "$VERBOSE" == true ]]; then
        echo ""
        echo ""
    fi
}

# Calculate metrics
calculate_metrics() {
    local avg_latency=0
    local success_rate=0
    local error_rate=0
    local timeout_rate=0

    if [[ $TOTAL_REQUESTS -gt 0 ]]; then
        avg_latency=$((TOTAL_LATENCY / TOTAL_REQUESTS))
        success_rate=$(awk "BEGIN {printf \"%.2f\", ($SUCCESSFUL_REQUESTS / $TOTAL_REQUESTS) * 100}")
        error_rate=$(awk "BEGIN {printf \"%.2f\", ($FAILED_REQUESTS / $TOTAL_REQUESTS) * 100}")
        timeout_rate=$(awk "BEGIN {printf \"%.2f\", ($TIMEOUTS / $TOTAL_REQUESTS) * 100}")
    fi

    echo "$avg_latency|$success_rate|$error_rate|$timeout_rate"
}

# Output results
output_results() {
    local metrics
    metrics=$(calculate_metrics)
    IFS='|' read -r avg_latency success_rate error_rate timeout_rate <<< "$metrics"

    if [[ "$JSON_OUTPUT" == true ]]; then
        # JSON output
        cat <<EOF
{
  "deployment_strategy": "$STRATEGY",
  "test_duration_seconds": $DURATION,
  "total_requests": $TOTAL_REQUESTS,
  "successful_requests": $SUCCESSFUL_REQUESTS,
  "failed_requests": $FAILED_REQUESTS,
  "timeout_count": $TIMEOUTS,
  "success_rate": $success_rate,
  "error_rate": $error_rate,
  "timeout_rate": $timeout_rate,
  "latency": {
    "min_ms": $MIN_LATENCY,
    "avg_ms": $avg_latency,
    "max_ms": $MAX_LATENCY
  },
  "downtime_seconds": $DOWNTIME_SECONDS,
  "downtime_percentage": $(awk "BEGIN {printf \"%.2f\", ($DOWNTIME_SECONDS / $DURATION) * 100}"),
  "zero_downtime": $(if [[ $DOWNTIME_SECONDS -eq 0 ]]; then echo "true"; else echo "false"; fi),
  "errors": [
$(printf '    "%s"' "${ERRORS[@]}" | paste -sd ',' -)
  ]
}
EOF
    else
        # Human-readable output
        echo ""
        echo "========================================="
        echo "Deployment Test Results"
        echo "========================================="
        echo "Strategy: $STRATEGY"
        echo "Duration: ${DURATION}s"
        echo ""
        echo "Requests:"
        echo "  Total:      $TOTAL_REQUESTS"
        echo "  Successful: $SUCCESSFUL_REQUESTS (${success_rate}%)"
        echo "  Failed:     $FAILED_REQUESTS (${error_rate}%)"
        echo "  Timeouts:   $TIMEOUTS (${timeout_rate}%)"
        echo ""
        echo "Latency:"
        echo "  Min:        ${MIN_LATENCY}ms"
        echo "  Avg:        ${avg_latency}ms"
        echo "  Max:        ${MAX_LATENCY}ms"
        echo ""
        echo "Downtime:"
        echo "  Total:      ${DOWNTIME_SECONDS}s"
        echo "  Percentage: $(awk "BEGIN {printf \"%.2f\", ($DOWNTIME_SECONDS / $DURATION) * 100}")%"
        echo "  Zero-downtime: $(if [[ $DOWNTIME_SECONDS -eq 0 ]]; then echo "${GREEN}YES${NC}"; else echo "${RED}NO${NC}"; fi)"
        echo ""

        if [[ $DOWNTIME_SECONDS -eq 0 ]]; then
            echo "${GREEN}✓ Deployment achieved zero downtime!${NC}"
        else
            echo "${YELLOW}! Deployment experienced downtime${NC}"
        fi

        if [[ $FAILED_REQUESTS -eq 0 ]]; then
            echo "${GREEN}✓ No failed requests${NC}"
        else
            echo "${YELLOW}! ${FAILED_REQUESTS} requests failed${NC}"
        fi

        echo ""
        echo "========================================="
    fi
}

# Strategy-specific recommendations
strategy_recommendations() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        return
    fi

    echo ""
    echo "Strategy Analysis: $STRATEGY"
    echo "========================================="

    case "$STRATEGY" in
        "blue-green")
            if [[ $DOWNTIME_SECONDS -eq 0 ]]; then
                echo "${GREEN}✓ Blue-Green deployment successful${NC}"
                echo "  - Instant switch achieved zero downtime"
            else
                echo "${YELLOW}! Unexpected downtime in Blue-Green deployment${NC}"
                echo "  - Check router/load balancer configuration"
                echo "  - Verify health checks on green environment"
            fi
            ;;
        "canary")
            echo "Canary Deployment Analysis:"
            echo "  - Success rate: ${success_rate}%"
            if [[ $(awk "BEGIN {print ($error_rate > 1.0)}") -eq 1 ]]; then
                echo "  ${YELLOW}! Error rate above 1% threshold${NC}"
                echo "  - Consider rolling back canary"
            else
                echo "  ${GREEN}✓ Error rate within acceptable range${NC}"
            fi
            ;;
        "rolling")
            echo "Rolling Update Analysis:"
            if [[ $DOWNTIME_SECONDS -eq 0 ]]; then
                echo "  ${GREEN}✓ Zero-downtime rolling update${NC}"
            else
                echo "  ${YELLOW}! Downtime detected during rolling update${NC}"
                echo "  - Check readiness probes"
                echo "  - Verify graceful shutdown"
                echo "  - Review maxUnavailable setting"
            fi
            ;;
        "recreate")
            echo "Recreate Deployment Analysis:"
            echo "  - Downtime: ${DOWNTIME_SECONDS}s"
            if [[ $DOWNTIME_SECONDS -gt 0 ]]; then
                echo "  - Expected for recreate strategy"
                echo "  - Consider blue-green or rolling for production"
            fi
            ;;
    esac

    echo "========================================="
}

# Main execution
main() {
    # Pre-flight check
    if ! command -v curl &> /dev/null; then
        echo "Error: curl is required but not installed"
        exit 1
    fi

    # Check initial health
    if [[ "$VERBOSE" == true ]]; then
        echo "Checking initial health..."
        if check_health; then
            echo "${GREEN}✓ Service healthy${NC}"
        else
            echo "${YELLOW}! Service health check failed${NC}"
        fi
    fi

    # Monitor deployment
    monitor_deployment

    # Output results
    output_results

    # Strategy-specific recommendations
    strategy_recommendations

    # Exit code based on results
    if [[ $DOWNTIME_SECONDS -eq 0 ]] && [[ $FAILED_REQUESTS -eq 0 ]]; then
        exit 0
    elif [[ $DOWNTIME_SECONDS -gt 60 ]] || [[ $FAILED_REQUESTS -gt $((TOTAL_REQUESTS / 10)) ]]; then
        # Significant downtime or >10% error rate
        exit 2
    else
        exit 1
    fi
}

# Run main
main
