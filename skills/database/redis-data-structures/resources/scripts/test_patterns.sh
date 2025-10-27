#!/usr/bin/env bash
#
# Test Common Redis Patterns
#
# Tests common Redis usage patterns including caching, queues, and pub/sub
#

set -euo pipefail

# Default configuration
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
REDIS_DB="${REDIS_DB:-0}"
JSON_OUTPUT=false
VERBOSE=false
TEST_PATTERN="all"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Usage function
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Test common Redis usage patterns.

OPTIONS:
    --host HOST         Redis host (default: localhost)
    --port PORT         Redis port (default: 6379)
    --password PASS     Redis password
    --db DB             Redis database (default: 0)
    --pattern PATTERN   Test pattern to run: all, cache, queue, pubsub,
                        lock, leaderboard, rate-limit (default: all)
    --json              Output results as JSON
    --verbose, -v       Verbose output
    --help, -h          Show this help message

EXAMPLES:
    # Test all patterns
    $(basename "$0")

    # Test specific pattern
    $(basename "$0") --pattern cache

    # Test with JSON output
    $(basename "$0") --json

    # Connect to remote Redis
    $(basename "$0") --host redis.example.com --port 6380 --password secret

EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            REDIS_HOST="$2"
            shift 2
            ;;
        --port)
            REDIS_PORT="$2"
            shift 2
            ;;
        --password)
            REDIS_PASSWORD="$2"
            shift 2
            ;;
        --db)
            REDIS_DB="$2"
            shift 2
            ;;
        --pattern)
            TEST_PATTERN="$2"
            shift 2
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check for redis-cli
if ! command -v redis-cli &> /dev/null; then
    echo "Error: redis-cli not found. Please install redis-tools." >&2
    exit 1
fi

# Build redis-cli command
REDIS_CMD="redis-cli -h $REDIS_HOST -p $REDIS_PORT -n $REDIS_DB"
if [[ -n "$REDIS_PASSWORD" ]]; then
    REDIS_CMD="$REDIS_CMD -a $REDIS_PASSWORD --no-auth-warning"
fi

# Test connection
log_verbose() {
    if [[ "$VERBOSE" == true ]] && [[ "$JSON_OUTPUT" == false ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $*" >&2
    fi
}

log_info() {
    if [[ "$JSON_OUTPUT" == false ]]; then
        echo -e "${GREEN}[INFO]${NC} $*" >&2
    fi
}

log_warn() {
    if [[ "$JSON_OUTPUT" == false ]]; then
        echo -e "${YELLOW}[WARN]${NC} $*" >&2
    fi
}

log_error() {
    if [[ "$JSON_OUTPUT" == false ]]; then
        echo -e "${RED}[ERROR]${NC} $*" >&2
    fi
}

log_test() {
    if [[ "$JSON_OUTPUT" == false ]]; then
        echo -e "${BLUE}[TEST]${NC} $*" >&2
    fi
}

# Test connection
test_connection() {
    log_verbose "Testing connection to Redis at $REDIS_HOST:$REDIS_PORT..."

    if ! $REDIS_CMD PING &> /dev/null; then
        log_error "Cannot connect to Redis at $REDIS_HOST:$REDIS_PORT"
        exit 1
    fi

    log_verbose "Connection successful"
}

# Results tracking
declare -A TEST_RESULTS

record_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    local duration="$4"

    TEST_RESULTS["${test_name}_status"]="$status"
    TEST_RESULTS["${test_name}_message"]="$message"
    TEST_RESULTS["${test_name}_duration"]="$duration"
}

# Cache pattern tests
test_cache_pattern() {
    log_test "Testing Cache Pattern..."
    local start_time=$(date +%s.%N)

    local key="test:cache:user:1000"
    local value='{"name":"Alice","email":"alice@example.com"}'

    # Test 1: Set with TTL
    log_verbose "Setting cache entry with TTL..."
    if ! $REDIS_CMD SET "$key" "$value" EX 60 > /dev/null; then
        record_result "cache_set" "FAIL" "Failed to set cache entry" "0"
        return 1
    fi

    # Test 2: Get cached value
    log_verbose "Getting cached value..."
    local retrieved=$($REDIS_CMD GET "$key")
    if [[ "$retrieved" != "$value" ]]; then
        record_result "cache_get" "FAIL" "Retrieved value doesn't match" "0"
        return 1
    fi

    # Test 3: Check TTL
    log_verbose "Checking TTL..."
    local ttl=$($REDIS_CMD TTL "$key")
    if [[ $ttl -le 0 ]] || [[ $ttl -gt 60 ]]; then
        record_result "cache_ttl" "FAIL" "TTL not set correctly: $ttl" "0"
        return 1
    fi

    # Test 4: Cache invalidation
    log_verbose "Testing cache invalidation..."
    if ! $REDIS_CMD DEL "$key" > /dev/null; then
        record_result "cache_invalidate" "FAIL" "Failed to delete cache entry" "0"
        return 1
    fi

    local exists=$($REDIS_CMD EXISTS "$key")
    if [[ $exists -ne 0 ]]; then
        record_result "cache_invalidate" "FAIL" "Key still exists after deletion" "0"
        return 1
    fi

    # Cleanup
    $REDIS_CMD DEL "$key" &> /dev/null

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    record_result "cache" "PASS" "All cache operations successful" "$duration"
    log_info "Cache pattern tests passed"
    return 0
}

# Queue pattern tests
test_queue_pattern() {
    log_test "Testing Queue Pattern..."
    local start_time=$(date +%s.%N)

    local queue="test:queue:tasks"

    # Test 1: Push items (producer)
    log_verbose "Pushing items to queue..."
    for i in {1..5}; do
        if ! $REDIS_CMD LPUSH "$queue" "task:$i" > /dev/null; then
            record_result "queue_push" "FAIL" "Failed to push to queue" "0"
            return 1
        fi
    done

    # Test 2: Check queue length
    log_verbose "Checking queue length..."
    local length=$($REDIS_CMD LLEN "$queue")
    if [[ $length -ne 5 ]]; then
        record_result "queue_length" "FAIL" "Queue length incorrect: $length" "0"
        $REDIS_CMD DEL "$queue" &> /dev/null
        return 1
    fi

    # Test 3: Pop items (consumer)
    log_verbose "Popping items from queue..."
    local popped_count=0
    for i in {1..5}; do
        local item=$($REDIS_CMD RPOP "$queue")
        if [[ -n "$item" ]]; then
            ((popped_count++))
        fi
    done

    if [[ $popped_count -ne 5 ]]; then
        record_result "queue_pop" "FAIL" "Popped count incorrect: $popped_count" "0"
        $REDIS_CMD DEL "$queue" &> /dev/null
        return 1
    fi

    # Test 4: Reliable queue pattern (BRPOPLPUSH)
    log_verbose "Testing reliable queue pattern..."
    local pending_queue="test:queue:pending"
    local processing_queue="test:queue:processing"

    # Add items to pending
    $REDIS_CMD LPUSH "$pending_queue" "task:1" "task:2" "task:3" > /dev/null

    # Move to processing
    local task=$($REDIS_CMD RPOPLPUSH "$pending_queue" "$processing_queue")
    if [[ -z "$task" ]]; then
        record_result "queue_reliable" "FAIL" "RPOPLPUSH failed" "0"
        $REDIS_CMD DEL "$pending_queue" "$processing_queue" &> /dev/null
        return 1
    fi

    # Cleanup
    $REDIS_CMD DEL "$queue" "$pending_queue" "$processing_queue" &> /dev/null

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    record_result "queue" "PASS" "All queue operations successful" "$duration"
    log_info "Queue pattern tests passed"
    return 0
}

# Pub/Sub pattern tests
test_pubsub_pattern() {
    log_test "Testing Pub/Sub Pattern..."
    local start_time=$(date +%s.%N)

    local channel="test:channel:notifications"

    # Test pub/sub by checking channel exists after subscribe
    # Note: Full pub/sub testing requires background processes

    # Test 1: Publish to channel (no subscribers)
    log_verbose "Publishing message..."
    local subscribers=$($REDIS_CMD PUBLISH "$channel" "test message")

    # No subscribers expected, but command should succeed
    if [[ $? -ne 0 ]]; then
        record_result "pubsub_publish" "FAIL" "Failed to publish message" "0"
        return 1
    fi

    # Test 2: Check channel info
    log_verbose "Checking pub/sub info..."
    if ! $REDIS_CMD PUBSUB CHANNELS "test:channel:*" &> /dev/null; then
        record_result "pubsub_info" "FAIL" "Failed to get pub/sub info" "0"
        return 1
    fi

    # Test 3: Test pattern subscription info
    log_verbose "Checking pattern subscription info..."
    if ! $REDIS_CMD PUBSUB NUMPAT &> /dev/null; then
        record_result "pubsub_pattern" "FAIL" "Failed to get pattern info" "0"
        return 1
    fi

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    record_result "pubsub" "PASS" "Pub/Sub operations successful (basic)" "$duration"
    log_info "Pub/Sub pattern tests passed (basic tests only)"
    return 0
}

# Distributed lock pattern tests
test_lock_pattern() {
    log_test "Testing Distributed Lock Pattern..."
    local start_time=$(date +%s.%N)

    local lock_key="test:lock:resource"
    local lock_value="unique-token-$$"

    # Test 1: Acquire lock
    log_verbose "Acquiring lock..."
    local acquired=$($REDIS_CMD SET "$lock_key" "$lock_value" NX EX 10)
    if [[ "$acquired" != "OK" ]]; then
        record_result "lock_acquire" "FAIL" "Failed to acquire lock" "0"
        return 1
    fi

    # Test 2: Try to acquire again (should fail)
    log_verbose "Trying to acquire lock again (should fail)..."
    local reacquired=$($REDIS_CMD SET "$lock_key" "other-token" NX EX 10)
    if [[ -n "$reacquired" ]]; then
        record_result "lock_exclusivity" "FAIL" "Lock not exclusive" "0"
        $REDIS_CMD DEL "$lock_key" &> /dev/null
        return 1
    fi

    # Test 3: Check lock exists
    log_verbose "Checking lock exists..."
    local exists=$($REDIS_CMD EXISTS "$lock_key")
    if [[ $exists -ne 1 ]]; then
        record_result "lock_exists" "FAIL" "Lock doesn't exist" "0"
        return 1
    fi

    # Test 4: Release lock (atomic with Lua)
    log_verbose "Releasing lock..."
    local lua_script='if redis.call("GET", KEYS[1]) == ARGV[1] then return redis.call("DEL", KEYS[1]) else return 0 end'
    local released=$($REDIS_CMD EVAL "$lua_script" 1 "$lock_key" "$lock_value")

    if [[ $released -ne 1 ]]; then
        record_result "lock_release" "FAIL" "Failed to release lock" "0"
        $REDIS_CMD DEL "$lock_key" &> /dev/null
        return 1
    fi

    # Cleanup
    $REDIS_CMD DEL "$lock_key" &> /dev/null

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    record_result "lock" "PASS" "All lock operations successful" "$duration"
    log_info "Distributed lock pattern tests passed"
    return 0
}

# Leaderboard pattern tests
test_leaderboard_pattern() {
    log_test "Testing Leaderboard Pattern..."
    local start_time=$(date +%s.%N)

    local leaderboard="test:leaderboard"

    # Test 1: Add players with scores
    log_verbose "Adding players to leaderboard..."
    for i in {1..10}; do
        if ! $REDIS_CMD ZADD "$leaderboard" $((i * 100)) "player:$i" > /dev/null; then
            record_result "leaderboard_add" "FAIL" "Failed to add player" "0"
            return 1
        fi
    done

    # Test 2: Get top 3 players
    log_verbose "Getting top 3 players..."
    local top_3=$($REDIS_CMD ZREVRANGE "$leaderboard" 0 2 WITHSCORES)
    if [[ -z "$top_3" ]]; then
        record_result "leaderboard_top" "FAIL" "Failed to get top players" "0"
        $REDIS_CMD DEL "$leaderboard" &> /dev/null
        return 1
    fi

    # Test 3: Get player rank
    log_verbose "Getting player rank..."
    local rank=$($REDIS_CMD ZREVRANK "$leaderboard" "player:5")
    if [[ $rank -lt 0 ]] || [[ $rank -gt 9 ]]; then
        record_result "leaderboard_rank" "FAIL" "Invalid rank: $rank" "0"
        $REDIS_CMD DEL "$leaderboard" &> /dev/null
        return 1
    fi

    # Test 4: Get player score
    log_verbose "Getting player score..."
    local score=$($REDIS_CMD ZSCORE "$leaderboard" "player:5")
    if [[ -z "$score" ]]; then
        record_result "leaderboard_score" "FAIL" "Failed to get score" "0"
        $REDIS_CMD DEL "$leaderboard" &> /dev/null
        return 1
    fi

    # Test 5: Increment score
    log_verbose "Incrementing player score..."
    if ! $REDIS_CMD ZINCRBY "$leaderboard" 50 "player:1" > /dev/null; then
        record_result "leaderboard_incr" "FAIL" "Failed to increment score" "0"
        $REDIS_CMD DEL "$leaderboard" &> /dev/null
        return 1
    fi

    # Cleanup
    $REDIS_CMD DEL "$leaderboard" &> /dev/null

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    record_result "leaderboard" "PASS" "All leaderboard operations successful" "$duration"
    log_info "Leaderboard pattern tests passed"
    return 0
}

# Rate limiting pattern tests
test_rate_limit_pattern() {
    log_test "Testing Rate Limiting Pattern..."
    local start_time=$(date +%s.%N)

    local rate_key="test:rate:user:1000"
    local limit=10

    # Test 1: Simple counter-based rate limiting
    log_verbose "Testing counter-based rate limiting..."
    local count=0
    for i in {1..15}; do
        local current=$($REDIS_CMD INCR "$rate_key")
        if [[ $i -eq 1 ]]; then
            $REDIS_CMD EXPIRE "$rate_key" 60 &> /dev/null
        fi

        if [[ $current -le $limit ]]; then
            ((count++))
        fi
    done

    if [[ $count -ne $limit ]]; then
        record_result "rate_limit_counter" "FAIL" "Counter rate limit failed: $count" "0"
        $REDIS_CMD DEL "$rate_key" &> /dev/null
        return 1
    fi

    # Test 2: Sliding window with sorted set
    log_verbose "Testing sliding window rate limiting..."
    local window_key="test:rate:window:user:1000"
    local now=$(date +%s)
    local window=60

    # Add requests
    for i in {1..10}; do
        $REDIS_CMD ZADD "$window_key" $((now + i)) "req:$i" > /dev/null
    done

    # Remove old entries
    $REDIS_CMD ZREMRANGEBYSCORE "$window_key" 0 $((now - window)) > /dev/null

    # Count requests in window
    local window_count=$($REDIS_CMD ZCARD "$window_key")
    if [[ $window_count -ne 10 ]]; then
        record_result "rate_limit_window" "FAIL" "Window count incorrect: $window_count" "0"
        $REDIS_CMD DEL "$rate_key" "$window_key" &> /dev/null
        return 1
    fi

    # Cleanup
    $REDIS_CMD DEL "$rate_key" "$window_key" &> /dev/null

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    record_result "rate_limit" "PASS" "All rate limiting operations successful" "$duration"
    log_info "Rate limiting pattern tests passed"
    return 0
}

# Output results
output_results() {
    local total_tests=0
    local passed_tests=0
    local failed_tests=0

    # Count results
    for key in "${!TEST_RESULTS[@]}"; do
        if [[ "$key" == *"_status" ]]; then
            ((total_tests++))
            if [[ "${TEST_RESULTS[$key]}" == "PASS" ]]; then
                ((passed_tests++))
            else
                ((failed_tests++))
            fi
        fi
    done

    if [[ "$JSON_OUTPUT" == true ]]; then
        # JSON output
        echo "{"
        echo "  \"summary\": {"
        echo "    \"total\": $total_tests,"
        echo "    \"passed\": $passed_tests,"
        echo "    \"failed\": $failed_tests"
        echo "  },"
        echo "  \"tests\": {"

        local first=true
        for test_name in cache queue pubsub lock leaderboard rate_limit; do
            if [[ -n "${TEST_RESULTS[${test_name}_status]:-}" ]]; then
                if [[ "$first" == false ]]; then
                    echo ","
                fi
                first=false

                echo -n "    \"$test_name\": {"
                echo -n "\"status\": \"${TEST_RESULTS[${test_name}_status]}\", "
                echo -n "\"message\": \"${TEST_RESULTS[${test_name}_message]}\", "
                echo -n "\"duration\": ${TEST_RESULTS[${test_name}_duration]}"
                echo -n "}"
            fi
        done

        echo ""
        echo "  }"
        echo "}"
    else
        # Human-readable output
        echo ""
        echo "========================================"
        echo "Test Results Summary"
        echo "========================================"
        echo "Total Tests: $total_tests"
        echo "Passed: $passed_tests"
        echo "Failed: $failed_tests"
        echo ""

        for test_name in cache queue pubsub lock leaderboard rate_limit; do
            if [[ -n "${TEST_RESULTS[${test_name}_status]:-}" ]]; then
                local status="${TEST_RESULTS[${test_name}_status]}"
                local message="${TEST_RESULTS[${test_name}_message]}"
                local duration="${TEST_RESULTS[${test_name}_duration]}"

                if [[ "$status" == "PASS" ]]; then
                    echo -e "${GREEN}✓${NC} $test_name: $message (${duration}s)"
                else
                    echo -e "${RED}✗${NC} $test_name: $message"
                fi
            fi
        done

        echo ""
        echo "========================================"
    fi
}

# Main execution
main() {
    test_connection

    case "$TEST_PATTERN" in
        all)
            test_cache_pattern
            test_queue_pattern
            test_pubsub_pattern
            test_lock_pattern
            test_leaderboard_pattern
            test_rate_limit_pattern
            ;;
        cache)
            test_cache_pattern
            ;;
        queue)
            test_queue_pattern
            ;;
        pubsub)
            test_pubsub_pattern
            ;;
        lock)
            test_lock_pattern
            ;;
        leaderboard)
            test_leaderboard_pattern
            ;;
        rate-limit)
            test_rate_limit_pattern
            ;;
        *)
            log_error "Unknown pattern: $TEST_PATTERN"
            usage
            ;;
    esac

    output_results
}

main
