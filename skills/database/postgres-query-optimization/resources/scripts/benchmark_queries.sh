#!/usr/bin/env bash
#
# PostgreSQL Query Benchmarking Tool
#
# Runs queries multiple times and reports timing statistics.
# Useful for comparing query performance before/after optimization.
#
# Usage:
#   ./benchmark_queries.sh --query "SELECT * FROM users WHERE email = 'foo@example.com'" --iterations 10
#   ./benchmark_queries.sh --query-file queries.sql --connection "postgresql://localhost/mydb"
#   ./benchmark_queries.sh --compare before.sql after.sql

set -euo pipefail

# Default values
ITERATIONS=10
CONNECTION="postgresql://localhost/postgres"
WARMUP_RUNS=2
OUTPUT_FORMAT="text"
VERBOSE=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Usage information
usage() {
    cat << EOF
PostgreSQL Query Benchmarking Tool

Usage:
    $(basename "$0") --query "SELECT ..." [OPTIONS]
    $(basename "$0") --query-file queries.sql [OPTIONS]
    $(basename "$0") --compare before.sql after.sql [OPTIONS]

Options:
    --query QUERY           SQL query to benchmark
    --query-file FILE       File containing SQL queries
    --compare FILE1 FILE2   Compare queries from two files
    --connection STRING     PostgreSQL connection string (default: postgresql://localhost/postgres)
    --iterations N          Number of benchmark iterations (default: 10)
    --warmup N             Number of warmup runs (default: 2)
    --json                 Output results as JSON
    --verbose              Show detailed output
    --help                 Show this help message

Examples:
    # Benchmark single query
    $(basename "$0") --query "SELECT * FROM users WHERE id = 123"

    # Benchmark from file
    $(basename "$0") --query-file queries.sql --iterations 20

    # Compare before/after optimization
    $(basename "$0") --compare slow_query.sql fast_query.sql

    # JSON output
    $(basename "$0") --query "SELECT COUNT(*) FROM orders" --json

EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --query)
            QUERY="$2"
            shift 2
            ;;
        --query-file)
            QUERY_FILE="$2"
            shift 2
            ;;
        --compare)
            COMPARE_FILE1="$2"
            COMPARE_FILE2="$3"
            shift 3
            ;;
        --connection)
            CONNECTION="$2"
            shift 2
            ;;
        --iterations)
            ITERATIONS="$2"
            shift 2
            ;;
        --warmup)
            WARMUP_RUNS="$2"
            shift 2
            ;;
        --json)
            OUTPUT_FORMAT="json"
            shift
            ;;
        --verbose)
            VERBOSE=1
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check for psql
if ! command -v psql &> /dev/null; then
    echo "Error: psql command not found. Please install PostgreSQL client tools." >&2
    exit 1
fi

# Function to execute query and measure time
benchmark_query() {
    local query="$1"
    local iterations="$2"
    local warmup="$3"

    # Warmup runs
    if [[ $VERBOSE -eq 1 ]]; then
        echo -e "${BLUE}Running $warmup warmup iterations...${NC}" >&2
    fi

    for ((i=1; i<=warmup; i++)); do
        psql "$CONNECTION" -c "$query" > /dev/null 2>&1 || true
    done

    # Benchmark runs
    if [[ $VERBOSE -eq 1 ]]; then
        echo -e "${BLUE}Running $iterations benchmark iterations...${NC}" >&2
    fi

    local times=()
    for ((i=1; i<=iterations; i++)); do
        local start=$(date +%s%N)
        psql "$CONNECTION" -c "EXPLAIN ANALYZE $query" 2>&1 | grep "Execution Time" | awk '{print $3}' > /tmp/bench_time_$$.txt
        local exec_time=$(cat /tmp/bench_time_$$.txt)

        if [[ -n "$exec_time" ]]; then
            times+=("$exec_time")
        fi

        if [[ $VERBOSE -eq 1 ]]; then
            echo -e "  Iteration $i: ${exec_time}ms" >&2
        fi
    done

    # Calculate statistics
    local sum=0
    local min=${times[0]}
    local max=${times[0]}

    for time in "${times[@]}"; do
        sum=$(echo "$sum + $time" | bc)
        if (( $(echo "$time < $min" | bc -l) )); then
            min=$time
        fi
        if (( $(echo "$time > $max" | bc -l) )); then
            max=$time
        fi
    done

    local mean=$(echo "scale=3; $sum / ${#times[@]}" | bc)

    # Calculate median
    IFS=$'\n' sorted=($(sort -n <<<"${times[*]}"))
    local count=${#sorted[@]}
    local median
    if (( count % 2 == 0 )); then
        local mid1=${sorted[$((count/2 - 1))]}
        local mid2=${sorted[$((count/2))]}
        median=$(echo "scale=3; ($mid1 + $mid2) / 2" | bc)
    else
        median=${sorted[$((count/2))]}
    fi

    # Calculate standard deviation
    local variance_sum=0
    for time in "${times[@]}"; do
        local diff=$(echo "$time - $mean" | bc)
        local squared=$(echo "$diff * $diff" | bc)
        variance_sum=$(echo "$variance_sum + $squared" | bc)
    done
    local variance=$(echo "scale=3; $variance_sum / ${#times[@]}" | bc)
    local stddev=$(echo "scale=3; sqrt($variance)" | bc)

    # Clean up
    rm -f /tmp/bench_time_$$.txt

    # Return results as JSON
    cat << EOF
{
  "iterations": ${#times[@]},
  "mean_ms": $mean,
  "median_ms": $median,
  "min_ms": $min,
  "max_ms": $max,
  "stddev_ms": $stddev,
  "times": [$(IFS=,; echo "${times[*]}")]
}
EOF
}

# Function to format output
format_output() {
    local results="$1"
    local query_name="$2"

    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        echo "$results"
    else
        local mean=$(echo "$results" | jq -r '.mean_ms')
        local median=$(echo "$results" | jq -r '.median_ms')
        local min=$(echo "$results" | jq -r '.min_ms')
        local max=$(echo "$results" | jq -r '.max_ms')
        local stddev=$(echo "$results" | jq -r '.stddev_ms')
        local iterations=$(echo "$results" | jq -r '.iterations')

        echo "================================================================================"
        echo "Benchmark Results: $query_name"
        echo "================================================================================"
        echo ""
        echo "Iterations:  $iterations"
        echo "Mean:        ${mean}ms"
        echo "Median:      ${median}ms"
        echo "Min:         ${min}ms"
        echo "Max:         ${max}ms"
        echo "Std Dev:     ${stddev}ms"
        echo ""
        echo "================================================================================"
    fi
}

# Function to compare two queries
compare_queries() {
    local query1="$1"
    local query2="$2"

    echo -e "${BLUE}Benchmarking Query 1 (BEFORE)...${NC}" >&2
    local results1=$(benchmark_query "$query1" "$ITERATIONS" "$WARMUP_RUNS")

    echo -e "${BLUE}Benchmarking Query 2 (AFTER)...${NC}" >&2
    local results2=$(benchmark_query "$query2" "$ITERATIONS" "$WARMUP_RUNS")

    local mean1=$(echo "$results1" | jq -r '.mean_ms')
    local mean2=$(echo "$results2" | jq -r '.mean_ms')

    local improvement=$(echo "scale=2; (($mean1 - $mean2) / $mean1) * 100" | bc)
    local speedup=$(echo "scale=2; $mean1 / $mean2" | bc)

    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        cat << EOF
{
  "before": $results1,
  "after": $results2,
  "improvement_percent": $improvement,
  "speedup_factor": $speedup
}
EOF
    else
        echo "================================================================================"
        echo "Query Comparison Results"
        echo "================================================================================"
        echo ""
        echo "BEFORE (Query 1):"
        echo "  Mean: ${mean1}ms"
        echo ""
        echo "AFTER (Query 2):"
        echo "  Mean: ${mean2}ms"
        echo ""

        if (( $(echo "$mean2 < $mean1" | bc -l) )); then
            echo -e "${GREEN}Improvement: ${improvement}% faster (${speedup}x speedup)${NC}"
        elif (( $(echo "$mean2 > $mean1" | bc -l) )); then
            echo -e "${RED}Regression: Query 2 is slower by ${improvement}%${NC}"
        else
            echo -e "${YELLOW}No significant change${NC}"
        fi

        echo ""
        echo "================================================================================"
    fi
}

# Check for jq (needed for JSON parsing)
if ! command -v jq &> /dev/null; then
    echo "Error: jq command not found. Please install jq for JSON processing." >&2
    echo "  Ubuntu/Debian: sudo apt-get install jq" >&2
    echo "  macOS: brew install jq" >&2
    exit 1
fi

# Main logic
if [[ -n "${COMPARE_FILE1:-}" ]] && [[ -n "${COMPARE_FILE2:-}" ]]; then
    # Compare mode
    query1=$(cat "$COMPARE_FILE1")
    query2=$(cat "$COMPARE_FILE2")
    compare_queries "$query1" "$query2"
elif [[ -n "${QUERY:-}" ]]; then
    # Single query mode
    results=$(benchmark_query "$QUERY" "$ITERATIONS" "$WARMUP_RUNS")
    format_output "$results" "Single Query"
elif [[ -n "${QUERY_FILE:-}" ]]; then
    # Query file mode
    query=$(cat "$QUERY_FILE")
    results=$(benchmark_query "$query" "$ITERATIONS" "$WARMUP_RUNS")
    format_output "$results" "$(basename "$QUERY_FILE")"
else
    usage
fi
