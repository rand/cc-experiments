#!/usr/bin/env bash
#
# Prometheus Exporter Testing Tool
#
# Tests Prometheus exporters for:
# - Metrics endpoint availability
# - Prometheus text format compliance
# - Metric naming conventions
# - HELP and TYPE annotations
# - Cardinality issues
# - Performance benchmarking
#
# Usage:
#   ./test_exporter.sh --endpoint http://localhost:9090/metrics
#   ./test_exporter.sh --endpoint http://localhost:8080/metrics --json
#   ./test_exporter.sh --endpoint http://localhost:9100/metrics --timeout 10

set -euo pipefail

# Default values
ENDPOINT=""
TIMEOUT=5
JSON_OUTPUT=false
VERBOSE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Statistics
TOTAL_METRICS=0
TOTAL_SAMPLES=0
TOTAL_HELP=0
TOTAL_TYPE=0
ISSUES_COUNT=0
WARNINGS_COUNT=0

# Arrays for tracking issues
declare -a ISSUES
declare -a WARNINGS
declare -a STATS

# Utility functions
log_info() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${GREEN}[✓]${NC} $1"
    fi
}

log_warning() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${YELLOW}[⚠]${NC} $1"
    fi
    WARNINGS+=("$1")
    ((WARNINGS_COUNT++)) || true
}

log_error() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${RED}[✗]${NC} $1"
    fi
    ISSUES+=("$1")
    ((ISSUES_COUNT++)) || true
}

usage() {
    cat << EOF
Prometheus Exporter Testing Tool

Tests Prometheus exporters for correctness and best practices.

Usage:
    $0 --endpoint <url> [options]

Options:
    --endpoint <url>    Metrics endpoint URL (required)
    --timeout <sec>     HTTP timeout in seconds (default: 5)
    --json              Output results in JSON format
    --verbose           Verbose output
    --help              Show this help message

Examples:
    # Test node_exporter
    $0 --endpoint http://localhost:9100/metrics

    # Test with JSON output
    $0 --endpoint http://localhost:8080/metrics --json

    # Test with custom timeout
    $0 --endpoint http://localhost:9090/metrics --timeout 10

    # Save JSON output to file
    $0 --endpoint http://localhost:9100/metrics --json > exporter_test.json

EOF
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --endpoint)
            ENDPOINT="$2"
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
if [[ -z "$ENDPOINT" ]]; then
    echo "Error: --endpoint is required"
    usage
    exit 1
fi

# Test 1: Check endpoint availability
test_endpoint_availability() {
    log_info "Testing endpoint availability: $ENDPOINT"

    local start_time=$(date +%s.%N)
    local http_code=$(curl -s -o /tmp/metrics_test.txt -w "%{http_code}" \
        --max-time "$TIMEOUT" \
        --connect-timeout "$TIMEOUT" \
        "$ENDPOINT" 2>/dev/null || echo "000")
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    STATS+=("response_time_seconds:$duration")
    STATS+=("http_status_code:$http_code")

    if [[ "$http_code" != "200" ]]; then
        log_error "Endpoint returned HTTP $http_code (expected 200)"
        return 1
    fi

    log_success "Endpoint available (${duration}s)"
    return 0
}

# Test 2: Validate Prometheus text format
test_text_format() {
    log_info "Validating Prometheus text format"

    local metrics_file="/tmp/metrics_test.txt"

    # Check if file is empty
    if [[ ! -s "$metrics_file" ]]; then
        log_error "Metrics file is empty"
        return 1
    fi

    # Count total lines
    local total_lines=$(wc -l < "$metrics_file")
    STATS+=("total_lines:$total_lines")

    # Check for valid metric lines
    local valid_metrics=0
    local invalid_lines=0

    while IFS= read -r line; do
        # Skip comments and empty lines
        if [[ -z "$line" ]] || [[ "$line" =~ ^# ]]; then
            continue
        fi

        # Valid metric format: metric_name{labels} value [timestamp]
        if [[ "$line" =~ ^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^}]*\})?\ +[0-9eE.+-]+(\s+[0-9]+)?$ ]]; then
            ((valid_metrics++)) || true
        else
            ((invalid_lines++)) || true
            if [[ "$VERBOSE" == "true" ]]; then
                log_warning "Invalid metric line: $line"
            fi
        fi
    done < "$metrics_file"

    STATS+=("valid_metrics:$valid_metrics")

    if [[ $invalid_lines -gt 0 ]]; then
        log_warning "Found $invalid_lines invalid metric lines"
    else
        log_success "All metric lines valid"
    fi

    return 0
}

# Test 3: Check metric naming conventions
test_naming_conventions() {
    log_info "Checking metric naming conventions"

    local metrics_file="/tmp/metrics_test.txt"
    local camel_case_count=0
    local missing_units_count=0
    local double_underscore_count=0

    # Extract metric names
    local metric_names=$(grep -v '^#' "$metrics_file" | grep -v '^$' | \
        sed -E 's/^([a-zA-Z_:][a-zA-Z0-9_:]*).*/\1/' | sort -u)

    TOTAL_METRICS=$(echo "$metric_names" | wc -l)
    STATS+=("unique_metrics:$TOTAL_METRICS")

    # Check each metric name
    while IFS= read -r metric; do
        # Check for CamelCase
        if [[ "$metric" =~ [A-Z] ]]; then
            ((camel_case_count++)) || true
            if [[ "$VERBOSE" == "true" ]]; then
                log_warning "Metric uses CamelCase: $metric"
            fi
        fi

        # Check for double underscores (invalid)
        if [[ "$metric" =~ __ ]] && [[ ! "$metric" =~ ^__ ]]; then
            ((double_underscore_count++)) || true
            log_error "Metric contains double underscore: $metric"
        fi

        # Check for missing units (heuristic)
        local has_unit=false
        for suffix in _total _seconds _bytes _ratio _percent _count _sum _bucket _celsius _fahrenheit; do
            if [[ "$metric" == *"$suffix" ]]; then
                has_unit=true
                break
            fi
        done

        if [[ "$has_unit" == "false" ]]; then
            # Check if it should have a unit
            for keyword in count total size duration latency time; do
                if [[ "$metric" == *"$keyword"* ]]; then
                    ((missing_units_count++)) || true
                    if [[ "$VERBOSE" == "true" ]]; then
                        log_warning "Metric may be missing unit suffix: $metric"
                    fi
                    break
                fi
            done
        fi
    done <<< "$metric_names"

    STATS+=("camel_case_metrics:$camel_case_count")
    STATS+=("double_underscore_metrics:$double_underscore_count")
    STATS+=("possibly_missing_units:$missing_units_count")

    if [[ $camel_case_count -gt 0 ]]; then
        log_warning "$camel_case_count metrics use CamelCase (should be snake_case)"
    fi

    if [[ $double_underscore_count -gt 0 ]]; then
        log_error "$double_underscore_count metrics contain double underscores"
    fi

    if [[ $missing_units_count -gt 0 ]]; then
        log_warning "$missing_units_count metrics may be missing unit suffixes"
    fi

    if [[ $camel_case_count -eq 0 ]] && [[ $double_underscore_count -eq 0 ]] && [[ $missing_units_count -eq 0 ]]; then
        log_success "Metric naming conventions followed"
    fi

    return 0
}

# Test 4: Check HELP and TYPE annotations
test_help_type_annotations() {
    log_info "Checking HELP and TYPE annotations"

    local metrics_file="/tmp/metrics_test.txt"

    # Count HELP and TYPE lines
    TOTAL_HELP=$(grep -c '^# HELP ' "$metrics_file" || true)
    TOTAL_TYPE=$(grep -c '^# TYPE ' "$metrics_file" || true)

    STATS+=("help_annotations:$TOTAL_HELP")
    STATS+=("type_annotations:$TOTAL_TYPE")

    # Extract metric names
    local metric_names=$(grep -v '^#' "$metrics_file" | grep -v '^$' | \
        sed -E 's/^([a-zA-Z_:][a-zA-Z0-9_:]*).*/\1/' | sort -u)

    local metrics_count=$(echo "$metric_names" | wc -l)

    # Check if all metrics have HELP and TYPE
    if [[ $TOTAL_HELP -lt $metrics_count ]]; then
        local missing=$((metrics_count - TOTAL_HELP))
        log_warning "$missing metrics missing HELP annotations"
    else
        log_success "All metrics have HELP annotations"
    fi

    if [[ $TOTAL_TYPE -lt $metrics_count ]]; then
        local missing=$((metrics_count - TOTAL_TYPE))
        log_warning "$missing metrics missing TYPE annotations"
    else
        log_success "All metrics have TYPE annotations"
    fi

    return 0
}

# Test 5: Check for potential cardinality issues
test_cardinality() {
    log_info "Checking for potential cardinality issues"

    local metrics_file="/tmp/metrics_test.txt"

    # Count total samples
    TOTAL_SAMPLES=$(grep -v '^#' "$metrics_file" | grep -v '^$' | wc -l)
    STATS+=("total_samples:$TOTAL_SAMPLES")

    # Calculate average cardinality per metric
    if [[ $TOTAL_METRICS -gt 0 ]]; then
        local avg_cardinality=$((TOTAL_SAMPLES / TOTAL_METRICS))
        STATS+=("avg_cardinality:$avg_cardinality")

        if [[ $avg_cardinality -gt 100 ]]; then
            log_warning "High average cardinality: $avg_cardinality samples per metric"
        elif [[ $avg_cardinality -gt 50 ]]; then
            log_warning "Moderate average cardinality: $avg_cardinality samples per metric"
        else
            log_success "Cardinality looks reasonable: $avg_cardinality samples per metric"
        fi
    fi

    # Find metrics with high cardinality
    local high_cardinality=$(grep -v '^#' "$metrics_file" | grep -v '^$' | \
        sed -E 's/^([a-zA-Z_:][a-zA-Z0-9_:]*).*/\1/' | \
        sort | uniq -c | sort -rn | head -5)

    if [[ "$VERBOSE" == "true" ]]; then
        log_info "Top 5 metrics by sample count:"
        echo "$high_cardinality" | while read -r count metric; do
            echo "  $metric: $count samples"
        done
    fi

    return 0
}

# Test 6: Validate metric types
test_metric_types() {
    log_info "Validating metric types"

    local metrics_file="/tmp/metrics_test.txt"

    # Extract TYPE annotations
    local types=$(grep '^# TYPE ' "$metrics_file" | awk '{print $4}' | sort | uniq -c)

    if [[ "$VERBOSE" == "true" ]]; then
        log_info "Metric type distribution:"
        echo "$types" | while read -r count type; do
            echo "  $type: $count"
        done
    fi

    # Check for valid types
    local invalid_types=$(grep '^# TYPE ' "$metrics_file" | \
        awk '{print $4}' | grep -Ev '^(counter|gauge|histogram|summary|untyped)$' || true)

    if [[ -n "$invalid_types" ]]; then
        log_error "Found invalid metric types: $invalid_types"
    else
        log_success "All metric types are valid"
    fi

    return 0
}

# Generate JSON output
output_json() {
    local success=$1

    # Convert arrays to JSON
    local issues_json=$(printf '%s\n' "${ISSUES[@]}" | jq -R -s -c 'split("\n")[:-1]')
    local warnings_json=$(printf '%s\n' "${WARNINGS[@]}" | jq -R -s -c 'split("\n")[:-1]')

    # Convert stats to JSON object
    local stats_json="{"
    local first=true
    for stat in "${STATS[@]}"; do
        local key="${stat%%:*}"
        local value="${stat#*:}"
        if [[ "$first" == "true" ]]; then
            first=false
        else
            stats_json+=","
        fi
        stats_json+="\"$key\":\"$value\""
    done
    stats_json+="}"

    cat << EOF
{
  "endpoint": "$ENDPOINT",
  "success": $success,
  "stats": $stats_json,
  "issues": $issues_json,
  "warnings": $warnings_json,
  "summary": {
    "total_metrics": $TOTAL_METRICS,
    "total_samples": $TOTAL_SAMPLES,
    "help_annotations": $TOTAL_HELP,
    "type_annotations": $TOTAL_TYPE,
    "issues_count": $ISSUES_COUNT,
    "warnings_count": $WARNINGS_COUNT
  }
}
EOF
}

# Generate text output
output_text() {
    local success=$1

    echo ""
    echo "================================================================================"
    echo "Prometheus Exporter Test Results"
    echo "================================================================================"
    echo ""
    echo "Endpoint: $ENDPOINT"
    echo ""

    echo "Summary:"
    echo "  Total Metrics: $TOTAL_METRICS"
    echo "  Total Samples: $TOTAL_SAMPLES"
    echo "  HELP Annotations: $TOTAL_HELP"
    echo "  TYPE Annotations: $TOTAL_TYPE"
    echo "  Issues: $ISSUES_COUNT"
    echo "  Warnings: $WARNINGS_COUNT"
    echo ""

    if [[ $ISSUES_COUNT -gt 0 ]]; then
        echo "Issues:"
        printf '%s\n' "${ISSUES[@]}" | sed 's/^/  - /'
        echo ""
    fi

    if [[ $WARNINGS_COUNT -gt 0 ]]; then
        echo "Warnings:"
        printf '%s\n' "${WARNINGS[@]}" | sed 's/^/  - /'
        echo ""
    fi

    if [[ "$success" == "true" ]]; then
        echo -e "${GREEN}✓ All tests passed${NC}"
    else
        echo -e "${RED}✗ Some tests failed${NC}"
    fi

    echo ""
    echo "================================================================================"
}

# Main execution
main() {
    local all_tests_passed=true

    # Run tests
    test_endpoint_availability || all_tests_passed=false
    test_text_format || all_tests_passed=false
    test_naming_conventions || all_tests_passed=false
    test_help_type_annotations || all_tests_passed=false
    test_cardinality || all_tests_passed=false
    test_metric_types || all_tests_passed=false

    # Output results
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        output_json "$all_tests_passed"
    else
        output_text "$all_tests_passed"
    fi

    # Cleanup
    rm -f /tmp/metrics_test.txt

    # Exit with appropriate code
    if [[ "$all_tests_passed" == "true" ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main
main
