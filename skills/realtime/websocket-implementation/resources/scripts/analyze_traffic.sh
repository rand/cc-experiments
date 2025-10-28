#!/usr/bin/env bash
#
# WebSocket Traffic Analyzer
#
# Capture and analyze WebSocket traffic using tcpdump and optional tshark/wireshark.
# Supports filtering, real-time monitoring, and traffic statistics.
#
# Usage:
#   analyze_traffic.sh [options]
#   analyze_traffic.sh --interface eth0 --port 8080
#   analyze_traffic.sh --file capture.pcap --analyze
#   analyze_traffic.sh --host api.example.com --port 443 --duration 60
#

set -euo pipefail

# Default values
INTERFACE=""
PORT=""
HOST=""
DURATION=""
OUTPUT_FILE=""
ANALYZE_ONLY=false
JSON_OUTPUT=false
VERBOSE=false
FILTER=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Usage information
usage() {
    cat << EOF
WebSocket Traffic Analyzer

Usage: $0 [options]

Options:
    -i, --interface IFACE    Network interface to capture on (e.g., eth0, en0)
    -p, --port PORT          WebSocket server port (default: auto-detect)
    -H, --host HOST          Filter by host/IP address
    -d, --duration SECONDS   Capture duration in seconds
    -o, --output FILE        Output pcap file (default: ws_capture_TIMESTAMP.pcap)
    -f, --file FILE          Analyze existing pcap file
    -a, --analyze            Analyze mode only (requires --file)
    --filter FILTER          Additional tcpdump filter
    --json                   Output analysis in JSON format
    -v, --verbose            Verbose output
    -h, --help               Show this help message

Examples:
    # Capture WebSocket traffic on port 8080 for 60 seconds
    $0 --interface eth0 --port 8080 --duration 60

    # Capture wss:// traffic to specific host
    $0 --interface en0 --host api.example.com --port 443

    # Analyze existing capture
    $0 --file capture.pcap --analyze

    # Real-time monitoring with JSON output
    $0 --interface eth0 --port 8080 --json

Requirements:
    - tcpdump (for packet capture)
    - tshark (optional, for detailed analysis)
    - jq (optional, for JSON processing)
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--interface)
                INTERFACE="$2"
                shift 2
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -H|--host)
                HOST="$2"
                shift 2
                ;;
            -d|--duration)
                DURATION="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            -f|--file)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            -a|--analyze)
                ANALYZE_ONLY=true
                shift
                ;;
            --filter)
                FILTER="$2"
                shift 2
                ;;
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
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
}

# Log message
log() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${BLUE}[INFO]${NC} $*" >&2
    fi
}

# Error message
error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# Success message
success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
}

# Warning message
warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check requirements
check_requirements() {
    local missing=()

    if ! command_exists tcpdump; then
        missing+=("tcpdump")
    fi

    if [[ "$ANALYZE_ONLY" == true ]] && ! command_exists tshark; then
        warn "tshark not found - analysis will be limited"
    fi

    if [[ "$JSON_OUTPUT" == true ]] && ! command_exists jq; then
        warn "jq not found - JSON output may be malformed"
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        error "Missing required commands: ${missing[*]}"
        error "Please install the missing tools and try again"
        exit 1
    fi
}

# Build tcpdump filter
build_filter() {
    local filter_parts=()

    # Port filter
    if [[ -n "$PORT" ]]; then
        filter_parts+=("port $PORT")
    fi

    # Host filter
    if [[ -n "$HOST" ]]; then
        filter_parts+=("host $HOST")
    fi

    # TCP only (WebSocket runs over TCP)
    filter_parts+=("tcp")

    # Additional user filter
    if [[ -n "$FILTER" ]]; then
        filter_parts+=("($FILTER)")
    fi

    # Join with "and"
    local result=""
    for i in "${!filter_parts[@]}"; do
        if [[ $i -eq 0 ]]; then
            result="${filter_parts[$i]}"
        else
            result="$result and ${filter_parts[$i]}"
        fi
    done

    echo "$result"
}

# Capture traffic
capture_traffic() {
    local interface="$1"
    local filter="$2"
    local output="$3"
    local duration="$4"

    log "Starting packet capture..."
    log "Interface: $interface"
    log "Filter: $filter"
    log "Output: $output"

    if [[ -n "$duration" ]]; then
        log "Duration: ${duration}s"

        # Capture with timeout
        timeout "${duration}s" sudo tcpdump -i "$interface" -w "$output" -s 0 "$filter" 2>&1 | while read -r line; do
            if [[ "$VERBOSE" == true ]]; then
                echo "$line" >&2
            fi
        done || true  # Ignore timeout exit code
    else
        # Capture until interrupted
        sudo tcpdump -i "$interface" -w "$output" -s 0 "$filter"
    fi

    success "Capture complete: $output"
}

# Analyze with tcpdump (basic)
analyze_basic() {
    local file="$1"

    echo "=== Basic Traffic Analysis ==="
    echo

    # Total packets
    local total_packets
    total_packets=$(tcpdump -r "$file" 2>/dev/null | wc -l)
    echo "Total packets: $total_packets"

    # Unique hosts
    echo
    echo "Unique hosts:"
    tcpdump -r "$file" -n 2>/dev/null | \
        awk '{print $3, $5}' | \
        tr '.' ' ' | \
        awk '{print $1"."$2"."$3"."$4}' | \
        sort -u | \
        head -20

    # Protocol breakdown
    echo
    echo "Protocol breakdown:"
    tcpdump -r "$file" -n 2>/dev/null | \
        awk '{print $NF}' | \
        sort | uniq -c | sort -rn | head -10
}

# Analyze with tshark (detailed)
analyze_detailed() {
    local file="$1"

    if ! command_exists tshark; then
        warn "tshark not available, skipping detailed analysis"
        return
    fi

    echo "=== Detailed WebSocket Analysis ==="
    echo

    # WebSocket handshakes
    echo "WebSocket handshakes:"
    local handshakes
    handshakes=$(tshark -r "$file" -Y "http.upgrade contains WebSocket" 2>/dev/null | wc -l)
    echo "  Total: $handshakes"

    # WebSocket frames
    echo
    echo "WebSocket frames:"
    local frames
    frames=$(tshark -r "$file" -Y "websocket" 2>/dev/null | wc -l)
    echo "  Total: $frames"

    # Frame types
    echo
    echo "Frame types:"
    tshark -r "$file" -Y "websocket" -T fields -e websocket.opcode 2>/dev/null | \
        sort | uniq -c | while read -r count opcode; do
        case "$opcode" in
            0x01) echo "  Text:   $count" ;;
            0x02) echo "  Binary: $count" ;;
            0x08) echo "  Close:  $count" ;;
            0x09) echo "  Ping:   $count" ;;
            0x0a) echo "  Pong:   $count" ;;
            *) echo "  Other ($opcode): $count" ;;
        esac
    done

    # Payload sizes
    echo
    echo "Payload size statistics:"
    tshark -r "$file" -Y "websocket" -T fields -e websocket.payload.length 2>/dev/null | \
        awk '{
            sum += $1
            count++
            if (min == "" || $1 < min) min = $1
            if ($1 > max) max = $1
        }
        END {
            if (count > 0) {
                printf "  Min:     %d bytes\n", min
                printf "  Max:     %d bytes\n", max
                printf "  Average: %.2f bytes\n", sum/count
                printf "  Total:   %d bytes\n", sum
            }
        }'

    # Connection durations
    echo
    echo "Connection statistics:"
    tshark -r "$file" -q -z conv,tcp 2>/dev/null | tail -n +6 | head -n -1 | \
        awk '{printf "  %s <-> %s: %.2fs, %s bytes\n", $1, $3, $6, $8}' | \
        head -10
}

# Analyze in JSON format
analyze_json() {
    local file="$1"

    local total_packets
    total_packets=$(tcpdump -r "$file" 2>/dev/null | wc -l)

    local handshakes=0
    local frames=0

    if command_exists tshark; then
        handshakes=$(tshark -r "$file" -Y "http.upgrade contains WebSocket" 2>/dev/null | wc -l)
        frames=$(tshark -r "$file" -Y "websocket" 2>/dev/null | wc -l)
    fi

    cat << EOF
{
  "file": "$file",
  "total_packets": $total_packets,
  "websocket": {
    "handshakes": $handshakes,
    "frames": $frames
  },
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

# Main function
main() {
    parse_args "$@"

    check_requirements

    # Set default output file if not specified
    if [[ -z "$OUTPUT_FILE" ]]; then
        OUTPUT_FILE="ws_capture_$(date +%Y%m%d_%H%M%S).pcap"
    fi

    # Analyze mode
    if [[ "$ANALYZE_ONLY" == true ]]; then
        if [[ ! -f "$OUTPUT_FILE" ]]; then
            error "File not found: $OUTPUT_FILE"
            exit 1
        fi

        log "Analyzing: $OUTPUT_FILE"

        if [[ "$JSON_OUTPUT" == true ]]; then
            analyze_json "$OUTPUT_FILE"
        else
            analyze_basic "$OUTPUT_FILE"
            echo
            analyze_detailed "$OUTPUT_FILE"
        fi

        exit 0
    fi

    # Capture mode
    if [[ -z "$INTERFACE" ]]; then
        error "Interface required for capture mode (use --interface)"
        exit 1
    fi

    # Build filter
    local filter
    filter=$(build_filter)

    if [[ -z "$filter" ]]; then
        warn "No filter specified - capturing all TCP traffic"
        filter="tcp"
    fi

    # Check if interface exists
    if ! ip link show "$INTERFACE" >/dev/null 2>&1 && ! ifconfig "$INTERFACE" >/dev/null 2>&1; then
        error "Interface not found: $INTERFACE"
        echo "Available interfaces:" >&2
        if command_exists ip; then
            ip link show | grep -E '^[0-9]+:' | awk '{print "  " $2}' | tr -d ':' >&2
        else
            ifconfig -a | grep -E '^[a-z]' | awk '{print "  " $1}' | tr -d ':' >&2
        fi
        exit 1
    fi

    # Capture traffic
    capture_traffic "$INTERFACE" "$filter" "$OUTPUT_FILE" "$DURATION"

    # Analyze if file was created
    if [[ -f "$OUTPUT_FILE" ]]; then
        echo
        if [[ "$JSON_OUTPUT" == true ]]; then
            analyze_json "$OUTPUT_FILE"
        else
            analyze_basic "$OUTPUT_FILE"
            echo
            analyze_detailed "$OUTPUT_FILE"
        fi
    fi
}

# Handle Ctrl+C gracefully
trap 'echo; warn "Interrupted by user"; exit 130' INT TERM

main "$@"
