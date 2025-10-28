#!/usr/bin/env bash
#
# Prometheus Exporter Test Script
#
# Tests Prometheus exporters by scraping metrics endpoints and validating
# the output format, checking for common issues, and verifying metrics quality.
#
# Usage:
#   test_exporter.sh --url http://localhost:8080/metrics
#   test_exporter.sh --url http://localhost:8080/metrics --json
#   test_exporter.sh --file exporters.txt
#   test_exporter.sh --url http://localhost:8080/metrics --verbose

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
VERBOSE=0
JSON_OUTPUT=0
TIMEOUT=10
HELP_TEXT="Usage: $(basename "$0") [OPTIONS]

Test Prometheus exporter metrics endpoints for correctness and quality.

OPTIONS:
    --url URL           Metrics endpoint URL (e.g., http://localhost:8080/metrics)
    --file FILE         File containing list of URLs (one per line)
    --timeout SECONDS   HTTP request timeout in seconds (default: 10)
    --json              Output results as JSON
    --verbose           Verbose output
    --help              Show this help message

EXAMPLES:
    # Test single endpoint
    $(basename "$0") --url http://localhost:8080/metrics

    # Test multiple endpoints from file
    $(basename "$0") --file exporters.txt

    # JSON output
    $(basename "$0") --url http://localhost:8080/metrics --json

    # Verbose mode
    $(basename "$0") --url http://localhost:8080/metrics --verbose
"

# Parse arguments
URL=""
FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            URL="$2"
            shift 2
            ;;
        --file)
            FILE="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --json)
            JSON_OUTPUT=1
            shift
            ;;
        --verbose)
            VERBOSE=1
            shift
            ;;
        --help)
            echo "$HELP_TEXT"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "$HELP_TEXT"
            exit 1
            ;;
    esac
done

# Validate input
if [[ -z "$URL" && -z "$FILE" ]]; then
    echo "Error: Either --url or --file must be provided" >&2
    echo "$HELP_TEXT"
    exit 1
fi

# Logging functions
log_info() {
    if [[ $VERBOSE -eq 1 && $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${BLUE}[INFO]${NC} $*" >&2
    fi
}

log_success() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${GREEN}[PASS]${NC} $*" >&2
    fi
}

log_warning() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${YELLOW}[WARN]${NC} $*" >&2
    fi
}

log_error() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${RED}[FAIL]${NC} $*" >&2
    fi
}

# Test result tracking
declare -a TEST_RESULTS=()

add_test_result() {
    local url="$1"
    local test="$2"
    local status="$3"  # pass, warning, fail
    local message="$4"

    TEST_RESULTS+=("{\"url\":\"$url\",\"test\":\"$test\",\"status\":\"$status\",\"message\":\"$message\"}")
}

# Fetch metrics from URL
fetch_metrics() {
    local url="$1"
    local output_file="$2"

    log_info "Fetching metrics from $url..."

    if curl -s -f -m "$TIMEOUT" -H "Accept: text/plain" "$url" > "$output_file" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Test 1: HTTP connectivity
test_connectivity() {
    local url="$1"
    local metrics_file="$2"

    if ! fetch_metrics "$url" "$metrics_file"; then
        log_error "Cannot connect to $url"
        add_test_result "$url" "connectivity" "fail" "Failed to fetch metrics"
        return 1
    fi

    log_success "Successfully connected to $url"
    add_test_result "$url" "connectivity" "pass" "Endpoint accessible"
    return 0
}

# Test 2: Content-Type header
test_content_type() {
    local url="$1"

    log_info "Checking Content-Type header..."

    local content_type
    content_type=$(curl -s -I -m "$TIMEOUT" "$url" 2>/dev/null | grep -i "content-type" | cut -d: -f2 | tr -d '[:space:]')

    # Prometheus expects text/plain or application/openmetrics-text
    if [[ "$content_type" =~ ^text/plain || "$content_type" =~ ^application/openmetrics-text ]]; then
        log_success "Content-Type is correct: $content_type"
        add_test_result "$url" "content_type" "pass" "Content-Type: $content_type"
        return 0
    else
        log_warning "Unexpected Content-Type: $content_type (expected text/plain)"
        add_test_result "$url" "content_type" "warning" "Content-Type: $content_type (expected text/plain)"
        return 1
    fi
}

# Test 3: Metrics format validation
test_metrics_format() {
    local url="$1"
    local metrics_file="$2"

    log_info "Validating metrics format..."

    local line_count=0
    local invalid_lines=0

    while IFS= read -r line; do
        ((line_count++))

        # Skip empty lines
        [[ -z "$line" ]] && continue

        # Skip comments (HELP, TYPE, etc.)
        if [[ "$line" =~ ^#.*$ ]]; then
            continue
        fi

        # Valid metric line format: metric_name{labels} value [timestamp]
        # Examples:
        #   http_requests_total{method="GET"} 1234
        #   temperature_celsius 23.5 1609459200000
        if ! [[ "$line" =~ ^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^}]*\})?\s+[0-9.eE+-]+ ]]; then
            log_warning "Invalid metric format at line $line_count: $line"
            ((invalid_lines++))
        fi
    done < "$metrics_file"

    if [[ $invalid_lines -eq 0 ]]; then
        log_success "All metrics have valid format"
        add_test_result "$url" "format" "pass" "All metrics formatted correctly"
        return 0
    else
        log_error "Found $invalid_lines invalid metric lines"
        add_test_result "$url" "format" "fail" "$invalid_lines invalid lines"
        return 1
    fi
}

# Test 4: Check for HELP and TYPE annotations
test_help_type_annotations() {
    local url="$1"
    local metrics_file="$2"

    log_info "Checking for HELP and TYPE annotations..."

    local metrics_with_help=0
    local metrics_with_type=0
    local total_metrics=0

    # Extract unique metric names
    declare -A metrics
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ -z "$line" || "$line" =~ ^#.*$ ]] && continue

        # Extract metric name
        if [[ "$line" =~ ^([a-zA-Z_:][a-zA-Z0-9_:]*) ]]; then
            metric_name="${BASH_REMATCH[1]}"
            metrics["$metric_name"]=1
        fi
    done < "$metrics_file"

    total_metrics=${#metrics[@]}

    # Count HELP annotations
    metrics_with_help=$(grep -c "^# HELP " "$metrics_file" || true)

    # Count TYPE annotations
    metrics_with_type=$(grep -c "^# TYPE " "$metrics_file" || true)

    local help_percentage=$((metrics_with_help * 100 / (total_metrics + 1)))
    local type_percentage=$((metrics_with_type * 100 / (total_metrics + 1)))

    if [[ $help_percentage -ge 80 && $type_percentage -ge 80 ]]; then
        log_success "Good documentation: $help_percentage% HELP, $type_percentage% TYPE"
        add_test_result "$url" "documentation" "pass" "$help_percentage% HELP, $type_percentage% TYPE"
        return 0
    else
        log_warning "Poor documentation: $help_percentage% HELP, $type_percentage% TYPE (< 80%)"
        add_test_result "$url" "documentation" "warning" "$help_percentage% HELP, $type_percentage% TYPE"
        return 1
    fi
}

# Test 5: Check metric naming conventions
test_naming_conventions() {
    local url="$1"
    local metrics_file="$2"

    log_info "Checking metric naming conventions..."

    local bad_names=0
    local total_metrics=0

    # Extract unique metric names
    declare -A metrics
    while IFS= read -r line; do
        [[ -z "$line" || "$line" =~ ^#.*$ ]] && continue

        if [[ "$line" =~ ^([a-zA-Z_:][a-zA-Z0-9_:]*) ]]; then
            metric_name="${BASH_REMATCH[1]}"

            if [[ -z "${metrics[$metric_name]:-}" ]]; then
                metrics["$metric_name"]=1
                ((total_metrics++))

                # Check naming conventions
                # Should be snake_case
                if [[ "$metric_name" =~ [A-Z] ]]; then
                    log_warning "Metric uses uppercase: $metric_name (should be snake_case)"
                    ((bad_names++))
                fi

                # Counters should end with _total
                if grep -q "^# TYPE $metric_name counter" "$metrics_file"; then
                    if [[ ! "$metric_name" =~ _total$ ]]; then
                        log_warning "Counter without _total suffix: $metric_name"
                        ((bad_names++))
                    fi
                fi

                # Should have unit suffix for measurements
                if grep -q "^# TYPE $metric_name gauge" "$metrics_file" || \
                   grep -q "^# TYPE $metric_name histogram" "$metrics_file"; then
                    if [[ ! "$metric_name" =~ _(seconds|bytes|ratio|percent|total)$ ]]; then
                        log_info "Metric might be missing unit suffix: $metric_name"
                    fi
                fi
            fi
        fi
    done < "$metrics_file"

    local error_percentage=0
    if [[ $total_metrics -gt 0 ]]; then
        error_percentage=$((bad_names * 100 / total_metrics))
    fi

    if [[ $error_percentage -lt 10 ]]; then
        log_success "Good naming conventions ($bad_names/$total_metrics issues)"
        add_test_result "$url" "naming" "pass" "$bad_names/$total_metrics naming issues"
        return 0
    else
        log_warning "Naming convention issues: $bad_names/$total_metrics metrics"
        add_test_result "$url" "naming" "warning" "$bad_names/$total_metrics naming issues"
        return 1
    fi
}

# Test 6: Check for high cardinality labels
test_cardinality() {
    local url="$1"
    local metrics_file="$2"

    log_info "Checking for potential cardinality issues..."

    local suspicious_labels=0

    # High-cardinality label patterns
    local patterns=(
        "id="
        "uuid="
        "guid="
        "email="
        "ip="
        "address="
        "token="
        "session="
        "trace_id="
        "span_id="
        "user_id="
        "timestamp="
    )

    for pattern in "${patterns[@]}"; do
        if grep -q "$pattern" "$metrics_file"; then
            log_warning "Found potentially high-cardinality label: $pattern"
            ((suspicious_labels++))
        fi
    done

    if [[ $suspicious_labels -eq 0 ]]; then
        log_success "No obvious cardinality issues detected"
        add_test_result "$url" "cardinality" "pass" "No high-cardinality labels detected"
        return 0
    else
        log_warning "Found $suspicious_labels potentially problematic label patterns"
        add_test_result "$url" "cardinality" "warning" "$suspicious_labels suspicious label patterns"
        return 1
    fi
}

# Test 7: Check metric count
test_metric_count() {
    local url="$1"
    local metrics_file="$2"

    log_info "Counting metrics..."

    local metric_count
    metric_count=$(grep -v "^#" "$metrics_file" | grep -c "^[a-zA-Z]" || true)

    log_info "Found $metric_count metric samples"

    if [[ $metric_count -eq 0 ]]; then
        log_error "No metrics found in response"
        add_test_result "$url" "metric_count" "fail" "0 metrics"
        return 1
    elif [[ $metric_count -gt 10000 ]]; then
        log_warning "Very high metric count: $metric_count (> 10,000)"
        add_test_result "$url" "metric_count" "warning" "$metric_count metrics (> 10k)"
        return 1
    else
        log_success "Metric count: $metric_count"
        add_test_result "$url" "metric_count" "pass" "$metric_count metrics"
        return 0
    fi
}

# Run all tests for a URL
test_exporter() {
    local url="$1"

    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo ""
        echo "================================================================================"
        echo "Testing: $url"
        echo "================================================================================"
    fi

    # Create temporary file for metrics
    local metrics_file
    metrics_file=$(mktemp)
    trap "rm -f $metrics_file" EXIT

    # Run tests
    local all_passed=1

    test_connectivity "$url" "$metrics_file" || all_passed=0

    if [[ -s "$metrics_file" ]]; then
        test_content_type "$url" || true  # Don't fail on content-type warning
        test_metrics_format "$url" "$metrics_file" || all_passed=0
        test_help_type_annotations "$url" "$metrics_file" || true
        test_naming_conventions "$url" "$metrics_file" || true
        test_cardinality "$url" "$metrics_file" || true
        test_metric_count "$url" "$metrics_file" || all_passed=0
    fi

    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo ""
        if [[ $all_passed -eq 1 ]]; then
            echo -e "${GREEN}Overall: PASSED${NC}"
        else
            echo -e "${RED}Overall: FAILED${NC}"
        fi
        echo "================================================================================"
    fi

    return $all_passed
}

# Main execution
main() {
    local urls=()

    # Collect URLs
    if [[ -n "$URL" ]]; then
        urls=("$URL")
    elif [[ -n "$FILE" ]]; then
        if [[ ! -f "$FILE" ]]; then
            echo "Error: File not found: $FILE" >&2
            exit 1
        fi

        while IFS= read -r line; do
            # Skip empty lines and comments
            [[ -z "$line" || "$line" =~ ^#.*$ ]] && continue
            urls+=("$line")
        done < "$FILE"
    fi

    if [[ ${#urls[@]} -eq 0 ]]; then
        echo "Error: No URLs to test" >&2
        exit 1
    fi

    # Test each URL
    local failed=0
    for test_url in "${urls[@]}"; do
        if ! test_exporter "$test_url"; then
            ((failed++))
        fi
    done

    # Output JSON if requested
    if [[ $JSON_OUTPUT -eq 1 ]]; then
        echo "{"
        echo "  \"summary\": {"
        echo "    \"total\": ${#urls[@]},"
        echo "    \"passed\": $((${#urls[@]} - failed)),"
        echo "    \"failed\": $failed"
        echo "  },"
        echo "  \"results\": ["

        local first=1
        for result in "${TEST_RESULTS[@]}"; do
            if [[ $first -eq 1 ]]; then
                first=0
            else
                echo ","
            fi
            echo -n "    $result"
        done
        echo ""
        echo "  ]"
        echo "}"
    fi

    # Exit with error if any tests failed
    if [[ $failed -gt 0 ]]; then
        exit 1
    fi
}

main
