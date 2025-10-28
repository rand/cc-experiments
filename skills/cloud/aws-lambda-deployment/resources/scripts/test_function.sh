#!/bin/bash
set -euo pipefail

##
# Test AWS Lambda functions with comprehensive validation.
#
# Features:
# - Synchronous and asynchronous invocation
# - Load testing
# - Event file support
# - Response validation
# - Performance timing
# - Concurrency testing
##

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Global variables
FUNCTION_NAME=""
EVENT_FILE=""
INVOCATION_TYPE="RequestResponse"
OUTPUT_FILE=""
LOAD_TEST=false
CONCURRENCY=1
DURATION=60
JSON_OUTPUT=false
REGION="us-east-1"
PROFILE=""

usage() {
    cat <<EOF
Usage: $0 --function-name FUNCTION [OPTIONS]

Test AWS Lambda functions with comprehensive validation.

Required Arguments:
  --function-name NAME      Lambda function name or ARN

Optional Arguments:
  --event FILE              Event JSON file (default: empty {})
  --async                   Asynchronous invocation (default: synchronous)
  --output FILE             Save response to file
  --load-test               Run load test
  --concurrency N           Concurrent invocations for load test (default: 1)
  --duration SECONDS        Load test duration in seconds (default: 60)
  --region REGION           AWS region (default: us-east-1)
  --profile PROFILE         AWS profile name
  --json                    Output JSON
  --help                    Show this help message

Examples:
  # Simple invocation
  $0 --function-name my-function

  # With event file
  $0 --function-name my-function --event event.json

  # Async invocation
  $0 --function-name my-function --async

  # Load test
  $0 --function-name my-function --load-test --concurrency 10 --duration 30

  # JSON output
  $0 --function-name my-function --json

EOF
    exit 0
}

log_info() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${GREEN}[INFO]${NC} $1"
    fi
}

log_warn() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${YELLOW}[WARN]${NC} $1" >&2
    fi
}

log_error() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${RED}[ERROR]${NC} $1" >&2
    fi
}

check_dependencies() {
    local missing=()

    if ! command -v aws &> /dev/null; then
        missing+=("aws-cli")
    fi

    if ! command -v jq &> /dev/null; then
        missing+=("jq")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing[*]}"
        log_error "Install them and try again."
        exit 1
    fi
}

invoke_function() {
    local function_name="$1"
    local event_file="$2"
    local invocation_type="$3"
    local output_file="$4"

    local aws_cmd="aws lambda invoke"

    # Add region
    if [[ -n "$REGION" ]]; then
        aws_cmd="$aws_cmd --region $REGION"
    fi

    # Add profile
    if [[ -n "$PROFILE" ]]; then
        aws_cmd="$aws_cmd --profile $PROFILE"
    fi

    # Build command
    aws_cmd="$aws_cmd --function-name $function_name"
    aws_cmd="$aws_cmd --invocation-type $invocation_type"

    # Add event
    if [[ -n "$event_file" ]]; then
        aws_cmd="$aws_cmd --payload file://$event_file"
    else
        aws_cmd="$aws_cmd --payload '{}'"
    fi

    # Output file
    local response_file="${output_file:-/tmp/lambda-response-$$.json}"
    aws_cmd="$aws_cmd $response_file"

    # Add log type for synchronous
    if [[ "$invocation_type" == "RequestResponse" ]]; then
        aws_cmd="$aws_cmd --log-type Tail"
    fi

    # Time the invocation
    local start_time=$(date +%s.%N)

    # Execute
    local invoke_output
    invoke_output=$(eval "$aws_cmd" 2>&1)
    local exit_code=$?

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    if [[ $exit_code -ne 0 ]]; then
        log_error "Invocation failed: $invoke_output"
        return 1
    fi

    # Parse invoke output (JSON from AWS CLI)
    local status_code=$(echo "$invoke_output" | jq -r '.StatusCode // empty')
    local function_error=$(echo "$invoke_output" | jq -r '.FunctionError // empty')
    local log_result=$(echo "$invoke_output" | jq -r '.LogResult // empty')

    # Decode logs if present
    local logs=""
    if [[ -n "$log_result" && "$log_result" != "null" ]]; then
        logs=$(echo "$log_result" | base64 --decode)
    fi

    # Read response
    local response=""
    if [[ -f "$response_file" ]]; then
        response=$(cat "$response_file")
        if [[ -z "$output_file" ]]; then
            rm -f "$response_file"
        fi
    fi

    # Output results
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        jq -n \
            --arg status "$status_code" \
            --arg error "$function_error" \
            --arg duration "$duration" \
            --argjson response "$response" \
            --arg logs "$logs" \
            '{
                status_code: $status,
                function_error: $error,
                duration_seconds: $duration,
                response: $response,
                logs: $logs
            }'
    else
        echo "Status Code: $status_code"
        if [[ -n "$function_error" ]]; then
            echo "Function Error: $function_error"
        fi
        echo "Duration: ${duration}s"
        echo ""
        echo "Response:"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"

        if [[ -n "$logs" ]]; then
            echo ""
            echo "Logs:"
            echo "$logs"
        fi
    fi

    # Check for errors
    if [[ -n "$function_error" ]]; then
        return 1
    fi

    return 0
}

load_test() {
    local function_name="$1"
    local event_file="$2"
    local concurrency="$3"
    local duration="$4"

    log_info "Starting load test..."
    log_info "Function: $function_name"
    log_info "Concurrency: $concurrency"
    log_info "Duration: ${duration}s"

    local end_time=$(($(date +%s) + duration))
    local total_requests=0
    local successful_requests=0
    local failed_requests=0
    local total_duration=0

    # Create temporary directory for load test
    local tmp_dir=$(mktemp -d)
    trap "rm -rf $tmp_dir" EXIT  # Test cleanup - safe in test context

    # Load test loop
    while [[ $(date +%s) -lt $end_time ]]; do
        # Launch concurrent invocations
        for ((i=0; i<concurrency; i++)); do
            (
                local start=$(date +%s.%N)
                local response_file="$tmp_dir/response-$$-$RANDOM.json"

                local aws_cmd="aws lambda invoke --function-name $function_name --invocation-type RequestResponse"

                if [[ -n "$REGION" ]]; then
                    aws_cmd="$aws_cmd --region $REGION"
                fi

                if [[ -n "$PROFILE" ]]; then
                    aws_cmd="$aws_cmd --profile $PROFILE"
                fi

                if [[ -n "$event_file" ]]; then
                    aws_cmd="$aws_cmd --payload file://$event_file"
                else
                    aws_cmd="$aws_cmd --payload '{}'"
                fi

                aws_cmd="$aws_cmd $response_file"

                if eval "$aws_cmd" &> /dev/null; then
                    local status_code=$(jq -r '.StatusCode // 200' "$response_file" 2>/dev/null || echo "200")
                    if [[ "$status_code" == "200" ]]; then
                        echo "success"
                    else
                        echo "error"
                    fi
                else
                    echo "error"
                fi

                local end=$(date +%s.%N)
                echo "duration:$(echo "$end - $start" | bc)"

                rm -f "$response_file"
            ) &
        done

        # Wait for this batch
        wait

        # Collect results
        local batch_success=$(jobs -p | wc -l)
        total_requests=$((total_requests + concurrency))

        # Small delay to avoid overwhelming
        sleep 0.1
    done

    # Wait for all background jobs
    wait

    # Analyze results from temporary files
    successful_requests=$(grep -c "success" "$tmp_dir"/* 2>/dev/null || echo "0")
    failed_requests=$((total_requests - successful_requests))

    if [[ -f "$tmp_dir"/duration_* ]]; then
        total_duration=$(awk '{sum+=$1} END {print sum}' "$tmp_dir"/duration_* 2>/dev/null || echo "0")
    fi

    local avg_duration=0
    if [[ $successful_requests -gt 0 ]]; then
        avg_duration=$(echo "scale=3; $total_duration / $successful_requests" | bc)
    fi

    local success_rate=0
    if [[ $total_requests -gt 0 ]]; then
        success_rate=$(echo "scale=2; $successful_requests * 100 / $total_requests" | bc)
    fi

    local rps=$(echo "scale=2; $total_requests / $duration" | bc)

    # Output results
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        jq -n \
            --arg total "$total_requests" \
            --arg successful "$successful_requests" \
            --arg failed "$failed_requests" \
            --arg success_rate "$success_rate" \
            --arg avg_duration "$avg_duration" \
            --arg rps "$rps" \
            --arg duration "$duration" \
            '{
                total_requests: $total,
                successful_requests: $successful,
                failed_requests: $failed,
                success_rate_percent: $success_rate,
                avg_duration_seconds: $avg_duration,
                requests_per_second: $rps,
                test_duration_seconds: $duration
            }'
    else
        echo ""
        echo "Load Test Results:"
        echo "  Total Requests: $total_requests"
        echo "  Successful: $successful_requests"
        echo "  Failed: $failed_requests"
        echo "  Success Rate: ${success_rate}%"
        echo "  Avg Duration: ${avg_duration}s"
        echo "  Requests/Second: $rps"
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --function-name)
            FUNCTION_NAME="$2"
            shift 2
            ;;
        --event)
            EVENT_FILE="$2"
            shift 2
            ;;
        --async)
            INVOCATION_TYPE="Event"
            shift
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --load-test)
            LOAD_TEST=true
            shift
            ;;
        --concurrency)
            CONCURRENCY="$2"
            shift 2
            ;;
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required arguments
if [[ -z "$FUNCTION_NAME" ]]; then
    log_error "Missing required argument: --function-name"
    usage
fi

# Check dependencies
check_dependencies

# Validate event file if provided
if [[ -n "$EVENT_FILE" ]]; then
    if [[ ! -f "$EVENT_FILE" ]]; then
        log_error "Event file not found: $EVENT_FILE"
        exit 1
    fi

    # Validate JSON
    if ! jq empty "$EVENT_FILE" 2>/dev/null; then
        log_error "Invalid JSON in event file: $EVENT_FILE"
        exit 1
    fi
fi

# Execute based on mode
if [[ "$LOAD_TEST" == "true" ]]; then
    load_test "$FUNCTION_NAME" "$EVENT_FILE" "$CONCURRENCY" "$DURATION"
else
    invoke_function "$FUNCTION_NAME" "$EVENT_FILE" "$INVOCATION_TYPE" "$OUTPUT_FILE"
fi
