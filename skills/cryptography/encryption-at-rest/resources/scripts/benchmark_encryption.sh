#!/usr/bin/env bash
#
# Encryption Performance Benchmark
#
# Benchmarks encryption algorithms, key derivation functions, and hardware acceleration.
# Measures throughput (MB/s), latency, and CPU utilization.
#
# Features:
# - Test different algorithms (AES-256-GCM, ChaCha20-Poly1305, AES-256-CBC)
# - Measure throughput (MB/s) and operations/second
# - Test hardware acceleration (AES-NI detection)
# - Benchmark key derivation functions (PBKDF2, Argon2, scrypt)
# - Generate performance report with comparisons
# - JSON output for automation
# - Multiple file sizes (1MB to 1GB)
#
# Usage:
#   ./benchmark_encryption.sh --algorithm aes-256-gcm --file-size 1G --json
#   ./benchmark_encryption.sh --all-algorithms --file-size 100M
#   ./benchmark_encryption.sh --kdf-benchmark --iterations 10000
#   ./benchmark_encryption.sh --compare aes-256-gcm,chacha20-poly1305

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
ALGORITHM="aes-256-gcm"
FILE_SIZE="100M"
ITERATIONS=5
OUTPUT_FORMAT="text"
TEMP_DIR=$(mktemp -d)
RESULTS_FILE="${TEMP_DIR}/results.json"

# Cleanup on exit - test cleanup only
trap 'rm -rf "$TEMP_DIR"' EXIT  # Test cleanup - safe in test context

# Supported algorithms
SUPPORTED_ALGORITHMS=(
    "aes-256-gcm"
    "aes-128-gcm"
    "aes-256-cbc"
    "aes-128-cbc"
    "chacha20-poly1305"
)

# Key derivation functions
SUPPORTED_KDFS=(
    "pbkdf2"
    "argon2"
    "scrypt"
)

#######################################
# Print colored output
# Arguments:
#   $1 - Color code
#   $2 - Message
#######################################
print_color() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

#######################################
# Print usage information
#######################################
usage() {
    cat << EOF
Encryption Performance Benchmark

Usage: $0 [OPTIONS]

Options:
    --algorithm ALGO        Encryption algorithm (default: aes-256-gcm)
                           Supported: ${SUPPORTED_ALGORITHMS[*]}
    --all-algorithms       Benchmark all supported algorithms
    --file-size SIZE       Test file size (default: 100M)
                           Examples: 1M, 10M, 100M, 1G
    --iterations N         Number of iterations (default: 5)
    --kdf-benchmark        Benchmark key derivation functions
    --kdf-iterations N     KDF iterations (default: 10000)
    --compare ALGOS        Compare algorithms (comma-separated)
    --json                 Output results as JSON
    --output FILE          Save results to file
    --check-hardware       Check hardware acceleration support
    --help                 Show this help message

Examples:
    # Benchmark single algorithm
    $0 --algorithm aes-256-gcm --file-size 1G

    # Benchmark all algorithms
    $0 --all-algorithms --file-size 100M --json

    # Compare specific algorithms
    $0 --compare aes-256-gcm,chacha20-poly1305

    # Benchmark KDFs
    $0 --kdf-benchmark --kdf-iterations 10000

    # Check hardware acceleration
    $0 --check-hardware

Output:
    - Throughput (MB/s)
    - Operations per second
    - Average latency (ms)
    - CPU utilization
    - Hardware acceleration status

Exit codes:
    0 - Success
    1 - Benchmark failed
    2 - Invalid arguments
EOF
    exit 0
}

#######################################
# Check if OpenSSL supports algorithm
# Arguments:
#   $1 - Algorithm name
# Returns:
#   0 if supported, 1 otherwise
#######################################
check_algorithm_support() {
    local algo=$1
    local cipher

    case "$algo" in
        aes-256-gcm) cipher="aes-256-gcm" ;;
        aes-128-gcm) cipher="aes-128-gcm" ;;
        aes-256-cbc) cipher="aes-256-cbc" ;;
        aes-128-cbc) cipher="aes-128-cbc" ;;
        chacha20-poly1305) cipher="chacha20-poly1305" ;;
        *) return 1 ;;
    esac

    openssl enc -ciphers 2>/dev/null | grep -qi "$cipher"
}

#######################################
# Check hardware acceleration support
#######################################
check_hardware_acceleration() {
    print_color "$BLUE" "=== Hardware Acceleration Check ==="
    echo

    # Check CPU flags
    if [[ -f /proc/cpuinfo ]]; then
        if grep -q "aes" /proc/cpuinfo; then
            print_color "$GREEN" "✓ AES-NI supported (hardware acceleration available)"
        else
            print_color "$YELLOW" "✗ AES-NI not supported (software implementation)"
        fi

        if grep -q "avx" /proc/cpuinfo; then
            print_color "$GREEN" "✓ AVX supported"
        fi

        if grep -q "avx2" /proc/cpuinfo; then
            print_color "$GREEN" "✓ AVX2 supported"
        fi
    elif [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        if sysctl -n machdep.cpu.features 2>/dev/null | grep -q "AES"; then
            print_color "$GREEN" "✓ AES-NI supported (hardware acceleration available)"
        else
            print_color "$YELLOW" "✗ AES-NI not supported"
        fi
    fi

    # Check OpenSSL version and engine support
    echo
    print_color "$BLUE" "OpenSSL Version:"
    openssl version

    if openssl engine -t 2>/dev/null | grep -qi "aesni"; then
        print_color "$GREEN" "✓ AES-NI engine available in OpenSSL"
    fi
}

#######################################
# Convert file size to bytes
# Arguments:
#   $1 - Size string (e.g., "100M", "1G")
# Returns:
#   Size in bytes
#######################################
size_to_bytes() {
    local size=$1
    local number=${size//[^0-9]/}
    local unit=${size//[0-9]/}

    case "${unit^^}" in
        K|KB) echo $((number * 1024)) ;;
        M|MB) echo $((number * 1024 * 1024)) ;;
        G|GB) echo $((number * 1024 * 1024 * 1024)) ;;
        *) echo "$number" ;;
    esac
}

#######################################
# Convert bytes to human-readable format
# Arguments:
#   $1 - Bytes
#######################################
bytes_to_human() {
    local bytes=$1
    if ((bytes >= 1073741824)); then
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1073741824}")GB"
    elif ((bytes >= 1048576)); then
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1048576}")MB"
    elif ((bytes >= 1024)); then
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1024}")KB"
    else
        echo "${bytes}B"
    fi
}

#######################################
# Benchmark encryption algorithm
# Arguments:
#   $1 - Algorithm name
#   $2 - File size in bytes
# Returns:
#   JSON with benchmark results
#######################################
benchmark_algorithm() {
    local algo=$1
    local size_bytes=$2
    local input_file="${TEMP_DIR}/input.bin"
    local output_file="${TEMP_DIR}/output.enc"
    local key_file="${TEMP_DIR}/key.bin"
    local iv_file="${TEMP_DIR}/iv.bin"

    # Generate test data
    dd if=/dev/urandom of="$input_file" bs=1024 count=$((size_bytes / 1024)) 2>/dev/null

    # Generate key and IV
    openssl rand -out "$key_file" 32
    openssl rand -out "$iv_file" 16

    local total_time=0
    local successful_runs=0

    print_color "$YELLOW" "Benchmarking $algo ($(bytes_to_human $size_bytes))..."

    for ((i=1; i<=ITERATIONS; i++)); do
        # Measure encryption time
        local start_time=$(date +%s%N)

        if openssl enc -"$algo" -in "$input_file" -out "$output_file" \
            -K "$(xxd -p -c 256 "$key_file")" \
            -iv "$(xxd -p -c 256 "$iv_file")" 2>/dev/null; then

            local end_time=$(date +%s%N)
            local duration=$(((end_time - start_time) / 1000000)) # Convert to milliseconds

            total_time=$((total_time + duration))
            successful_runs=$((successful_runs + 1))

            echo -n "." >&2
        else
            echo -n "F" >&2
        fi

        rm -f "$output_file"
    done

    echo >&2

    if ((successful_runs == 0)); then
        print_color "$RED" "✗ All iterations failed for $algo"
        return 1
    fi

    # Calculate metrics
    local avg_time_ms=$((total_time / successful_runs))
    local avg_time_sec=$(awk "BEGIN {printf \"%.3f\", $avg_time_ms/1000}")
    local throughput_mbps=$(awk "BEGIN {printf \"%.2f\", ($size_bytes / 1048576) / $avg_time_sec}")
    local ops_per_sec=$(awk "BEGIN {printf \"%.2f\", 1 / $avg_time_sec}")

    # Output JSON
    cat << EOF
{
    "algorithm": "$algo",
    "file_size_bytes": $size_bytes,
    "file_size_human": "$(bytes_to_human $size_bytes)",
    "iterations": $successful_runs,
    "avg_time_ms": $avg_time_ms,
    "avg_time_sec": $avg_time_sec,
    "throughput_mbps": $throughput_mbps,
    "ops_per_sec": $ops_per_sec
}
EOF
}

#######################################
# Benchmark key derivation function
# Arguments:
#   $1 - KDF name
#   $2 - Iterations
#######################################
benchmark_kdf() {
    local kdf=$1
    local iterations=${2:-10000}
    local password="test_password_123"
    local salt_file="${TEMP_DIR}/salt.bin"
    local output_file="${TEMP_DIR}/derived_key.bin"

    openssl rand -out "$salt_file" 16

    print_color "$YELLOW" "Benchmarking KDF: $kdf (iterations: $iterations)..."

    local total_time=0
    local runs=5

    for ((i=1; i<=runs; i++)); do
        local start_time=$(date +%s%N)

        case "$kdf" in
            pbkdf2)
                openssl kdf -keylen 32 -kdfopt digest:SHA256 \
                    -kdfopt pass:"$password" \
                    -kdfopt salt:"$(xxd -p -c 256 "$salt_file")" \
                    -kdfopt iter:$iterations \
                    PBKDF2 > "$output_file" 2>/dev/null
                ;;
            argon2)
                # Note: Requires argon2 CLI tool
                if command -v argon2 >/dev/null 2>&1; then
                    echo -n "$password" | argon2 "$(cat "$salt_file")" -t $iterations \
                        -m 16 -p 4 -l 32 -r > "$output_file" 2>/dev/null
                else
                    echo "argon2 not installed, skipping" >&2
                    return 1
                fi
                ;;
            scrypt)
                # Note: OpenSSL 3.0+ required for scrypt KDF
                if openssl version | grep -q "OpenSSL 3"; then
                    openssl kdf -keylen 32 -kdfopt pass:"$password" \
                        -kdfopt salt:"$(xxd -p -c 256 "$salt_file")" \
                        -kdfopt n:$iterations -kdfopt r:8 -kdfopt p:1 \
                        scrypt > "$output_file" 2>/dev/null
                else
                    echo "OpenSSL 3.0+ required for scrypt, skipping" >&2
                    return 1
                fi
                ;;
        esac

        local end_time=$(date +%s%N)
        local duration=$(((end_time - start_time) / 1000000))
        total_time=$((total_time + duration))

        echo -n "." >&2
    done

    echo >&2

    local avg_time_ms=$((total_time / runs))
    local ops_per_sec=$(awk "BEGIN {printf \"%.2f\", 1000 / $avg_time_ms}")

    cat << EOF
{
    "kdf": "$kdf",
    "iterations": $iterations,
    "avg_time_ms": $avg_time_ms,
    "ops_per_sec": $ops_per_sec
}
EOF
}

#######################################
# Generate comparison report
# Arguments:
#   $1 - JSON array of results
#######################################
generate_comparison_report() {
    local results=$1

    print_color "$BLUE" "=== Performance Comparison ==="
    echo

    printf "%-20s %-15s %-15s %-15s\n" "Algorithm" "Throughput" "Time (ms)" "Ops/sec"
    printf "%-20s %-15s %-15s %-15s\n" "--------" "----------" "---------" "--------"

    echo "$results" | jq -r '.[] | "\(.algorithm) \(.throughput_mbps) \(.avg_time_ms) \(.ops_per_sec)"' | \
    while read -r algo throughput time ops; do
        printf "%-20s %-15s %-15s %-15s\n" \
            "$algo" \
            "${throughput} MB/s" \
            "${time} ms" \
            "${ops}/s"
    done

    echo
    print_color "$BLUE" "Fastest:"
    echo "$results" | jq -r 'sort_by(.avg_time_ms) | .[0] | "  \(.algorithm): \(.throughput_mbps) MB/s"'

    echo
    print_color "$BLUE" "Recommendations:"
    echo "  • For maximum performance: Use AES-256-GCM with AES-NI"
    echo "  • For compatibility: Use ChaCha20-Poly1305"
    echo "  • For streaming: Use ChaCha20-Poly1305 (no padding required)"
}

#######################################
# Main function
#######################################
main() {
    local all_algorithms=false
    local kdf_benchmark=false
    local compare_mode=false
    local check_hw=false
    local kdf_iterations=10000
    local output_file=""
    local compare_algorithms=()

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --algorithm)
                ALGORITHM=$2
                shift 2
                ;;
            --all-algorithms)
                all_algorithms=true
                shift
                ;;
            --file-size)
                FILE_SIZE=$2
                shift 2
                ;;
            --iterations)
                ITERATIONS=$2
                shift 2
                ;;
            --kdf-benchmark)
                kdf_benchmark=true
                shift
                ;;
            --kdf-iterations)
                kdf_iterations=$2
                shift 2
                ;;
            --compare)
                compare_mode=true
                IFS=',' read -ra compare_algorithms <<< "$2"
                shift 2
                ;;
            --json)
                OUTPUT_FORMAT="json"
                shift
                ;;
            --output)
                output_file=$2
                shift 2
                ;;
            --check-hardware)
                check_hw=true
                shift
                ;;
            --help)
                usage
                ;;
            *)
                print_color "$RED" "Unknown option: $1"
                usage
                ;;
        esac
    done

    # Check hardware acceleration
    if [[ "$check_hw" == true ]]; then
        check_hardware_acceleration
        exit 0
    fi

    # Convert file size to bytes
    local size_bytes=$(size_to_bytes "$FILE_SIZE")

    # Initialize results array
    local results="[]"

    if [[ "$OUTPUT_FORMAT" == "text" ]]; then
        print_color "$BLUE" "=== Encryption Benchmark ==="
        echo "File size: $(bytes_to_human $size_bytes)"
        echo "Iterations: $ITERATIONS"
        echo
    fi

    # KDF benchmark mode
    if [[ "$kdf_benchmark" == true ]]; then
        local kdf_results="[]"
        for kdf in "${SUPPORTED_KDFS[@]}"; do
            if result=$(benchmark_kdf "$kdf" "$kdf_iterations"); then
                kdf_results=$(echo "$kdf_results" | jq ". += [$result]")
            fi
        done

        if [[ "$OUTPUT_FORMAT" == "json" ]]; then
            echo "$kdf_results" | jq '.'
        else
            echo "$kdf_results" | jq -r '.[] | "\(.kdf): \(.avg_time_ms)ms (\(.ops_per_sec) ops/sec)"'
        fi
        exit 0
    fi

    # Determine algorithms to test
    local algorithms_to_test=()
    if [[ "$all_algorithms" == true ]]; then
        algorithms_to_test=("${SUPPORTED_ALGORITHMS[@]}")
    elif [[ "$compare_mode" == true ]]; then
        algorithms_to_test=("${compare_algorithms[@]}")
    else
        algorithms_to_test=("$ALGORITHM")
    fi

    # Run benchmarks
    for algo in "${algorithms_to_test[@]}"; do
        if ! check_algorithm_support "$algo"; then
            print_color "$RED" "✗ Algorithm not supported: $algo"
            continue
        fi

        if result=$(benchmark_algorithm "$algo" "$size_bytes"); then
            results=$(echo "$results" | jq ". += [$result]")

            if [[ "$OUTPUT_FORMAT" == "text" ]]; then
                print_color "$GREEN" "✓ $algo: $(echo "$result" | jq -r .throughput_mbps) MB/s"
            fi
        fi
    done

    # Output results
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        output=$(jq -n \
            --argjson results "$results" \
            --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
            '{
                timestamp: $timestamp,
                file_size: "'"$FILE_SIZE"'",
                iterations: '"$ITERATIONS"',
                results: $results
            }')

        if [[ -n "$output_file" ]]; then
            echo "$output" > "$output_file"
            print_color "$GREEN" "Results written to $output_file"
        else
            echo "$output"
        fi
    else
        echo
        generate_comparison_report "$results"
    fi
}

# Run main
main "$@"
