#!/usr/bin/env bash
#
# Network traffic capture and analysis with tcpdump.
#
# Demonstrates production-safe packet capture and analysis.
#

set -euo pipefail

INTERFACE="${INTERFACE:-any}"
DURATION="${DURATION:-30}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp}"

echo "=== Network Traffic Analysis ==="
echo "Interface: $INTERFACE"
echo "Duration: $DURATION seconds"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "Warning: This script requires root privileges"
    echo "Try: sudo $0"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CAPTURE_FILE="$OUTPUT_DIR/capture_${TIMESTAMP}.pcap"

# Function to capture HTTP traffic
capture_http() {
    echo "--- Capturing HTTP traffic ---"
    timeout "$DURATION" tcpdump -i "$INTERFACE" -n -s 65535 -w "$CAPTURE_FILE" 'tcp port 80 or tcp port 8080'
    echo "Capture complete: $CAPTURE_FILE"
}

# Function to capture HTTPS traffic
capture_https() {
    echo "--- Capturing HTTPS traffic ---"
    timeout "$DURATION" tcpdump -i "$INTERFACE" -n -s 65535 -w "$CAPTURE_FILE" 'tcp port 443'
    echo "Capture complete: $CAPTURE_FILE"
}

# Function to capture database traffic
capture_database() {
    echo "--- Capturing database traffic ---"
    timeout "$DURATION" tcpdump -i "$INTERFACE" -n -s 65535 -w "$CAPTURE_FILE" \
        'port 5432 or port 3306 or port 6379 or port 27017'
    echo "Capture complete: $CAPTURE_FILE"
}

# Function to analyze capture file
analyze_capture() {
    local capture_file="$1"

    if ! command -v tshark &>/dev/null; then
        echo "tshark not found. Install wireshark to analyze captures."
        return
    fi

    echo ""
    echo "--- Analysis Results ---"
    echo ""

    echo "1. Protocol distribution:"
    tshark -r "$capture_file" -q -z io,phs
    echo ""

    echo "2. Top talkers (by packet count):"
    tshark -r "$capture_file" -q -z conv,ip | head -20
    echo ""

    echo "3. TCP retransmissions:"
    tshark -r "$capture_file" -Y "tcp.analysis.retransmission" | wc -l
    echo ""

    echo "4. TCP resets:"
    tshark -r "$capture_file" -Y "tcp.flags.reset == 1" | wc -l
    echo ""

    echo "5. HTTP requests:"
    tshark -r "$capture_file" -Y "http.request" -T fields \
        -e http.request.method \
        -e http.host \
        -e http.request.uri | head -20
}

# Main capture
echo "Starting capture..."
timeout "$DURATION" tcpdump -i "$INTERFACE" -n -s 65535 -w "$CAPTURE_FILE" || true

echo ""
echo "Capture saved to: $CAPTURE_FILE"
echo "Size: $(du -h "$CAPTURE_FILE" | cut -f1)"
echo ""

# Analyze if tshark available
if command -v tshark &>/dev/null; then
    analyze_capture "$CAPTURE_FILE"
else
    echo "Install Wireshark/tshark for analysis:"
    echo "  - Ubuntu/Debian: apt install tshark"
    echo "  - macOS: brew install wireshark"
    echo ""
    echo "Or open $CAPTURE_FILE in Wireshark GUI"
fi
