#!/usr/bin/env bash
# Comprehensive iperf3 benchmark suite for TCP performance testing

set -euo pipefail

SERVER="${1:-}"
if [[ -z "$SERVER" ]]; then
    echo "Usage: $0 <server-ip>"
    exit 1
fi

RESULTS_DIR="./iperf3-results-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

run_test() {
    local name="$1"
    shift
    echo "Running: $name"
    iperf3 -c "$SERVER" "$@" -J > "$RESULTS_DIR/${name}.json" 2>&1 || echo "Failed: $name"
}

echo "iperf3 Benchmark Suite"
echo "Server: $SERVER"
echo "Results: $RESULTS_DIR"
echo ""

# Single stream baseline
run_test "01-baseline-60s" -t 60

# Parallel streams
run_test "02-parallel-4-streams" -t 60 -P 4
run_test "03-parallel-8-streams" -t 60 -P 8
run_test "04-parallel-16-streams" -t 60 -P 16

# Reverse direction (server sends)
run_test "05-reverse" -t 60 -R

# Bidirectional
run_test "06-bidirectional" -t 60 --bidir

# Window sizes
run_test "07-window-64k" -t 30 -w 64K
run_test "08-window-256k" -t 30 -w 256K
run_test "09-window-1m" -t 30 -w 1M
run_test "10-window-4m" -t 30 -w 4M

# Congestion control comparison
for cc in cubic bbr; do
    run_test "11-cc-${cc}" -t 60 -C "$cc"
done

# Long test for stability
run_test "12-long-test-300s" -t 300 -P 4

# UDP baseline (for comparison)
run_test "13-udp-1gbps" -u -b 1G -t 30

echo ""
echo "Benchmark complete!"
echo "Results in: $RESULTS_DIR"
echo ""
echo "Summary:"
for f in "$RESULTS_DIR"/*.json; do
    name=$(basename "$f" .json)
    throughput=$(jq -r '.end.sum_received.bits_per_second // 0' "$f" 2>/dev/null)
    throughput_mbps=$(echo "scale=2; $throughput / 1000000" | bc 2>/dev/null || echo "N/A")
    echo "  $name: $throughput_mbps Mbps"
done
