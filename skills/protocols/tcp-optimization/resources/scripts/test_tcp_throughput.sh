#!/usr/bin/env bash

# test_tcp_throughput.sh - Automated iperf3 testing and analysis
# Tests TCP throughput under various scenarios and provides detailed reporting

set -euo pipefail

# Script metadata
readonly SCRIPT_NAME="test_tcp_throughput.sh"
readonly SCRIPT_VERSION="1.0.0"
readonly RESULTS_DIR="/var/tmp/tcp-throughput-tests"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Global flags
VERBOSE=0
JSON_OUTPUT=0
SERVER=""
PORT=5201
DURATION=60
PARALLEL_STREAMS=1
SCENARIOS="single"
REPORT_FILE=""
BASELINE_FILE=""
CONGESTION_CONTROL=""

# Logging functions
log_info() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${BLUE}[INFO]${NC} $*" >&2
    fi
}

log_success() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
    fi
}

log_warning() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${YELLOW}[WARNING]${NC} $*" >&2
    fi
}

log_error() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${RED}[ERROR]${NC} $*" >&2
    fi
}

log_verbose() {
    if [[ $VERBOSE -eq 1 && $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $*" >&2
    fi
}

# Help message
show_help() {
    cat <<EOF
$SCRIPT_NAME - Automated TCP throughput testing with iperf3

USAGE:
    $SCRIPT_NAME --server <host> [OPTIONS]

REQUIRED:
    --server <host>         iperf3 server hostname or IP address

OPTIONS:
    --help, -h              Show this help message
    --version, -v           Show script version
    --verbose               Enable verbose output
    --json                  Output results in JSON format
    --port <port>           iperf3 server port (default: 5201)
    --duration <sec>        Test duration in seconds (default: 60)
    --parallel <n>          Number of parallel streams (default: 1)
    --scenarios <list>      Test scenarios (comma-separated, default: single)
    --report <file>         Save detailed report to file
    --baseline <file>       Compare results with baseline from file
    --congestion <algo>     Use specific congestion control algorithm

SCENARIOS:
    single                  Single TCP stream
    parallel                Multiple parallel streams (4 streams)
    bidirectional           Bidirectional test
    reverse                 Reverse direction (server sends)
    window                  Test with various window sizes
    all                     Run all scenarios

EXAMPLES:
    # Basic single-stream test
    $SCRIPT_NAME --server 192.168.1.100

    # Multiple scenarios with verbose output
    $SCRIPT_NAME --server 192.168.1.100 --scenarios single,parallel,reverse --verbose

    # Long test with many parallel streams
    $SCRIPT_NAME --server 192.168.1.100 --duration 300 --parallel 8

    # Test with BBR congestion control
    $SCRIPT_NAME --server 192.168.1.100 --congestion bbr

    # Generate baseline for future comparisons
    $SCRIPT_NAME --server 192.168.1.100 --json > baseline.json

    # Compare with baseline
    $SCRIPT_NAME --server 192.168.1.100 --baseline baseline.json --report results.txt

NOTES:
    - Requires iperf3 to be installed on both client and server
    - Server must be running: iperf3 -s
    - Results are saved to $RESULTS_DIR
    - Use --json for machine-readable output
    - Baseline comparison shows performance regression/improvement

EOF
}

# Version information
show_version() {
    echo "$SCRIPT_NAME version $SCRIPT_VERSION"
}

# Check dependencies
check_dependencies() {
    local missing=0

    if ! command -v iperf3 &> /dev/null; then
        log_error "iperf3 is not installed"
        log_error "Install with: apt install iperf3 (Debian/Ubuntu) or yum install iperf3 (RHEL/CentOS)"
        missing=1
    fi

    if ! command -v jq &> /dev/null; then
        log_warning "jq is not installed (JSON parsing will be limited)"
        log_warning "Install with: apt install jq (Debian/Ubuntu) or yum install jq (RHEL/CentOS)"
    fi

    if [[ $missing -eq 1 ]]; then
        exit 1
    fi
}

# Test server connectivity
test_server_connectivity() {
    local server="$1"
    local port="$2"

    log_verbose "Testing connectivity to $server:$port"

    if ! timeout 5 bash -c "cat < /dev/null > /dev/tcp/$server/$port" 2>/dev/null; then
        log_error "Cannot connect to iperf3 server at $server:$port"
        log_error "Make sure the server is running: iperf3 -s -p $port"
        return 1
    fi

    log_verbose "Server is reachable"
    return 0
}

# Run iperf3 test
run_iperf3_test() {
    local test_name="$1"
    local args=("${@:2}")

    log_info "Running test: $test_name"

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local output_file="$RESULTS_DIR/${test_name}_${timestamp}.json"

    mkdir -p "$RESULTS_DIR"

    # Build iperf3 command
    local cmd=(iperf3 -c "$SERVER" -p "$PORT" -t "$DURATION" -J)
    cmd+=("${args[@]}")

    # Add congestion control if specified
    if [[ -n "$CONGESTION_CONTROL" ]]; then
        cmd+=(-C "$CONGESTION_CONTROL")
    fi

    log_verbose "Command: ${cmd[*]}"

    # Run test
    if ! "${cmd[@]}" > "$output_file" 2>&1; then
        log_error "Test failed: $test_name"
        return 1
    fi

    log_success "Test completed: $test_name"
    log_verbose "Results saved to: $output_file"

    # Extract key metrics
    if command -v jq &> /dev/null; then
        local throughput
        throughput=$(jq -r '.end.sum_received.bits_per_second // 0' "$output_file")
        throughput=$(echo "scale=2; $throughput / 1000000" | bc)
        log_info "  Throughput: ${throughput} Mbps"

        local retrans
        retrans=$(jq -r '.end.sum_sent.retransmits // 0' "$output_file")
        log_info "  Retransmits: $retrans"
    fi

    echo "$output_file"
}

# Single stream test
test_single_stream() {
    log_info "=== Single Stream Test ==="
    run_iperf3_test "single_stream"
}

# Parallel streams test
test_parallel_streams() {
    log_info "=== Parallel Streams Test ==="
    local streams="${PARALLEL_STREAMS:-4}"
    run_iperf3_test "parallel_streams" -P "$streams"
}

# Bidirectional test
test_bidirectional() {
    log_info "=== Bidirectional Test ==="
    run_iperf3_test "bidirectional" --bidir
}

# Reverse direction test
test_reverse() {
    log_info "=== Reverse Direction Test ==="
    run_iperf3_test "reverse" -R
}

# Window size tests
test_window_sizes() {
    log_info "=== Window Size Tests ==="

    local windows=(64K 128K 256K 512K 1M 2M 4M)

    for window in "${windows[@]}"; do
        log_info "Testing with window size: $window"
        run_iperf3_test "window_${window}" -w "$window"
    done
}

# Parse iperf3 JSON results
parse_results() {
    local result_file="$1"

    if [[ ! -f "$result_file" ]]; then
        log_error "Result file not found: $result_file"
        return 1
    fi

    if ! command -v jq &> /dev/null; then
        log_warning "jq not installed, skipping detailed parsing"
        return 1
    fi

    # Extract metrics
    local throughput_send throughput_recv retrans cwnd rtt

    throughput_send=$(jq -r '.end.sum_sent.bits_per_second // 0' "$result_file")
    throughput_recv=$(jq -r '.end.sum_received.bits_per_second // 0' "$result_file")
    retrans=$(jq -r '.end.sum_sent.retransmits // 0' "$result_file")
    cwnd=$(jq -r '.end.streams[0].sender.max_cwnd // 0' "$result_file")
    rtt=$(jq -r '.end.streams[0].sender.mean_rtt // 0' "$result_file")

    # Convert to Mbps
    throughput_send=$(echo "scale=2; $throughput_send / 1000000" | bc)
    throughput_recv=$(echo "scale=2; $throughput_recv / 1000000" | bc)

    echo "throughput_send=$throughput_send"
    echo "throughput_recv=$throughput_recv"
    echo "retrans=$retrans"
    echo "cwnd=$cwnd"
    echo "rtt=$rtt"
}

# Compare with baseline
compare_with_baseline() {
    local current_file="$1"
    local baseline_file="$2"

    if [[ ! -f "$baseline_file" ]]; then
        log_error "Baseline file not found: $baseline_file"
        return 1
    fi

    log_info "Comparing with baseline: $baseline_file"

    if ! command -v jq &> /dev/null; then
        log_warning "jq not installed, skipping comparison"
        return 1
    fi

    # Extract metrics from both files
    local current_throughput baseline_throughput
    current_throughput=$(jq -r '.end.sum_received.bits_per_second // 0' "$current_file")
    baseline_throughput=$(jq -r '.end.sum_received.bits_per_second // 0' "$baseline_file")

    # Calculate percentage change
    local change
    if [[ $baseline_throughput -gt 0 ]]; then
        change=$(echo "scale=2; (($current_throughput - $baseline_throughput) / $baseline_throughput) * 100" | bc)

        log_info "Throughput comparison:"
        log_info "  Baseline: $(echo "scale=2; $baseline_throughput / 1000000" | bc) Mbps"
        log_info "  Current:  $(echo "scale=2; $current_throughput / 1000000" | bc) Mbps"

        if (( $(echo "$change > 0" | bc -l) )); then
            log_success "  Change: +${change}% (improvement)"
        elif (( $(echo "$change < 0" | bc -l) )); then
            log_warning "  Change: ${change}% (regression)"
        else
            log_info "  Change: 0% (no change)"
        fi
    fi
}

# Generate comprehensive report
generate_report() {
    local report_file="$1"
    shift
    local result_files=("$@")

    log_info "Generating report: $report_file"

    {
        echo "================================================================================"
        echo "TCP Throughput Test Report"
        echo "================================================================================"
        echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo "Server: $SERVER:$PORT"
        echo "Duration: ${DURATION}s"
        if [[ -n "$CONGESTION_CONTROL" ]]; then
            echo "Congestion Control: $CONGESTION_CONTROL"
        fi
        echo ""

        for result_file in "${result_files[@]}"; do
            if [[ ! -f "$result_file" ]]; then
                continue
            fi

            local test_name
            test_name=$(basename "$result_file" .json | sed 's/_[0-9]\{8\}_[0-9]\{6\}//')

            echo "Test: $test_name"
            echo "----------------------------------------"

            if command -v jq &> /dev/null; then
                # Extract and display metrics
                local throughput_send throughput_recv retrans cwnd rtt

                throughput_send=$(jq -r '.end.sum_sent.bits_per_second // 0' "$result_file")
                throughput_recv=$(jq -r '.end.sum_received.bits_per_second // 0' "$result_file")
                retrans=$(jq -r '.end.sum_sent.retransmits // 0' "$result_file")
                cwnd=$(jq -r '.end.streams[0].sender.max_cwnd // 0' "$result_file")
                rtt=$(jq -r '.end.streams[0].sender.mean_rtt // 0' "$result_file")

                throughput_send=$(echo "scale=2; $throughput_send / 1000000" | bc)
                throughput_recv=$(echo "scale=2; $throughput_recv / 1000000" | bc)

                echo "  Throughput (send): ${throughput_send} Mbps"
                echo "  Throughput (recv): ${throughput_recv} Mbps"
                echo "  Retransmits: $retrans"
                echo "  Max cwnd: $cwnd"
                echo "  Mean RTT: $rtt µs"
            else
                echo "  (jq not installed for detailed metrics)"
            fi

            echo ""
        done

        echo "================================================================================"
        echo "Result files stored in: $RESULTS_DIR"
        echo "================================================================================"
    } > "$report_file"

    log_success "Report generated: $report_file"
}

# Generate JSON summary
generate_json_summary() {
    local result_files=("$@")

    if ! command -v jq &> /dev/null; then
        log_error "jq is required for JSON output"
        return 1
    fi

    echo "{"
    echo "  \"script\": \"$SCRIPT_NAME\","
    echo "  \"version\": \"$SCRIPT_VERSION\","
    echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"server\": \"$SERVER\","
    echo "  \"port\": $PORT,"
    echo "  \"duration\": $DURATION,"

    if [[ -n "$CONGESTION_CONTROL" ]]; then
        echo "  \"congestion_control\": \"$CONGESTION_CONTROL\","
    fi

    echo "  \"tests\": ["

    local first=1
    for result_file in "${result_files[@]}"; do
        if [[ ! -f "$result_file" ]]; then
            continue
        fi

        if [[ $first -eq 0 ]]; then
            echo "    ,"
        fi
        first=0

        local test_name
        test_name=$(basename "$result_file" .json | sed 's/_[0-9]\{8\}_[0-9]\{6\}//')

        echo "    {"
        echo "      \"name\": \"$test_name\","
        echo "      \"file\": \"$result_file\","

        local throughput_send throughput_recv retrans
        throughput_send=$(jq -r '.end.sum_sent.bits_per_second // 0' "$result_file")
        throughput_recv=$(jq -r '.end.sum_received.bits_per_second // 0' "$result_file")
        retrans=$(jq -r '.end.sum_sent.retransmits // 0' "$result_file")

        echo "      \"throughput_send_bps\": $throughput_send,"
        echo "      \"throughput_recv_bps\": $throughput_recv,"
        echo "      \"retransmits\": $retrans"
        echo -n "    }"
    done

    echo ""
    echo "  ]"
    echo "}"
}

# Main function
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --version|-v)
                show_version
                exit 0
                ;;
            --verbose)
                VERBOSE=1
                shift
                ;;
            --json)
                JSON_OUTPUT=1
                shift
                ;;
            --server)
                SERVER="$2"
                shift 2
                ;;
            --port)
                PORT="$2"
                shift 2
                ;;
            --duration)
                DURATION="$2"
                shift 2
                ;;
            --parallel)
                PARALLEL_STREAMS="$2"
                shift 2
                ;;
            --scenarios)
                SCENARIOS="$2"
                shift 2
                ;;
            --report)
                REPORT_FILE="$2"
                shift 2
                ;;
            --baseline)
                BASELINE_FILE="$2"
                shift 2
                ;;
            --congestion)
                CONGESTION_CONTROL="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$SERVER" ]]; then
        log_error "Server is required (use --server)"
        show_help
        exit 1
    fi

    # Check dependencies
    check_dependencies

    # Test server connectivity
    if ! test_server_connectivity "$SERVER" "$PORT"; then
        exit 1
    fi

    # Parse scenarios
    IFS=',' read -ra SCENARIO_LIST <<< "$SCENARIOS"

    # Run tests
    local result_files=()

    for scenario in "${SCENARIO_LIST[@]}"; do
        case "$scenario" in
            single)
                result_files+=($(test_single_stream))
                ;;
            parallel)
                result_files+=($(test_parallel_streams))
                ;;
            bidirectional)
                result_files+=($(test_bidirectional))
                ;;
            reverse)
                result_files+=($(test_reverse))
                ;;
            window)
                result_files+=($(test_window_sizes))
                ;;
            all)
                result_files+=($(test_single_stream))
                result_files+=($(test_parallel_streams))
                result_files+=($(test_bidirectional))
                result_files+=($(test_reverse))
                ;;
            *)
                log_error "Unknown scenario: $scenario"
                exit 1
                ;;
        esac
    done

    # Compare with baseline if provided
    if [[ -n "$BASELINE_FILE" && ${#result_files[@]} -gt 0 ]]; then
        compare_with_baseline "${result_files[0]}" "$BASELINE_FILE"
    fi

    # Generate report
    if [[ $JSON_OUTPUT -eq 1 ]]; then
        generate_json_summary "${result_files[@]}"
    elif [[ -n "$REPORT_FILE" ]]; then
        generate_report "$REPORT_FILE" "${result_files[@]}"
        cat "$REPORT_FILE"
    else
        # Generate temporary report
        local tmp_report
        tmp_report=$(mktemp)
        generate_report "$tmp_report" "${result_files[@]}"
        cat "$tmp_report"
        rm -f "$tmp_report"
    fi

    log_success "All tests completed"
    log_info "Results stored in: $RESULTS_DIR"
}

# Run main function
main "$@"
