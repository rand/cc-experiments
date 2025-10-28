#!/usr/bin/env bash
# test_etcd_cluster.sh - Spin up and test etcd RAFT cluster
#
# Usage:
#   ./test_etcd_cluster.sh [options]
#
# Options:
#   --nodes N        Number of nodes (default: 3)
#   --network NAME   Docker network name (default: etcd-raft-test)
#   --cleanup        Cleanup existing cluster
#   --json           Output JSON format
#   --help           Show this help message
#
# Example:
#   ./test_etcd_cluster.sh --nodes 5 --json

set -euo pipefail

# Default values
NODES=3
NETWORK="etcd-raft-test"
CLEANUP=0
JSON_OUTPUT=0
ETCD_VERSION="v3.5.10"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${GREEN}[INFO]${NC} $1"
    fi
}

log_warn() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${YELLOW}[WARN]${NC} $1"
    fi
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

show_help() {
    sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# //' | sed 's/^#//'
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --nodes)
                NODES="$2"
                shift 2
                ;;
            --network)
                NETWORK="$2"
                shift 2
                ;;
            --cleanup)
                CLEANUP=1
                shift
                ;;
            --json)
                JSON_OUTPUT=1
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

cleanup_cluster() {
    log_info "Cleaning up existing cluster..."

    # Stop and remove containers
    for i in $(seq 1 "$NODES"); do
        docker rm -f "etcd-node$i" 2>/dev/null || true
    done

    # Remove network
    docker network rm "$NETWORK" 2>/dev/null || true

    log_info "Cleanup complete"
}

create_network() {
    log_info "Creating Docker network: $NETWORK"
    docker network create "$NETWORK" 2>/dev/null || log_warn "Network already exists"
}

start_etcd_cluster() {
    log_info "Starting $NODES-node etcd cluster..."

    # Build initial cluster string
    local initial_cluster=""
    for i in $(seq 1 "$NODES"); do
        initial_cluster="${initial_cluster}etcd-node$i=http://etcd-node$i:2380,"
    done
    initial_cluster="${initial_cluster%,}"

    # Start each node
    for i in $(seq 1 "$NODES"); do
        log_info "Starting etcd-node$i..."

        docker run -d \
            --name "etcd-node$i" \
            --network "$NETWORK" \
            -p "$((2378 + i)):2379" \
            -p "$((2478 + i)):2380" \
            "quay.io/coreos/etcd:${ETCD_VERSION}" \
            /usr/local/bin/etcd \
            --name "etcd-node$i" \
            --initial-advertise-peer-urls "http://etcd-node$i:2380" \
            --listen-peer-urls "http://0.0.0.0:2380" \
            --listen-client-urls "http://0.0.0.0:2379" \
            --advertise-client-urls "http://etcd-node$i:2379" \
            --initial-cluster-token "etcd-cluster-1" \
            --initial-cluster "$initial_cluster" \
            --initial-cluster-state "new" \
            --log-level info \
            > /dev/null
    done

    # Wait for cluster to be ready
    log_info "Waiting for cluster to be ready..."
    sleep 5

    local ready=0
    for attempt in $(seq 1 30); do
        if docker exec etcd-node1 etcdctl endpoint health 2>/dev/null | grep -q "is healthy"; then
            ready=1
            break
        fi
        sleep 1
    done

    if [[ $ready -eq 0 ]]; then
        log_error "Cluster failed to become ready"
        return 1
    fi

    log_info "Cluster is ready!"
}

test_cluster() {
    log_info "Running cluster tests..."

    # Test 1: Write and read
    log_info "Test 1: Write and read key"
    docker exec etcd-node1 etcdctl put test-key "test-value" > /dev/null
    local value=$(docker exec etcd-node1 etcdctl get test-key --print-value-only)
    if [[ "$value" == "test-value" ]]; then
        log_info "✓ Write/read test passed"
    else
        log_error "✗ Write/read test failed"
        return 1
    fi

    # Test 2: Read from different node (verify replication)
    log_info "Test 2: Verify replication across nodes"
    local value2=$(docker exec etcd-node2 etcdctl get test-key --print-value-only)
    if [[ "$value2" == "test-value" ]]; then
        log_info "✓ Replication test passed"
    else
        log_error "✗ Replication test failed"
        return 1
    fi

    # Test 3: Lease (TTL)
    log_info "Test 3: Test lease functionality"
    local lease_id=$(docker exec etcd-node1 etcdctl lease grant 10 | awk '{print $2}')
    docker exec etcd-node1 etcdctl put temp-key "temp-value" --lease="$lease_id" > /dev/null
    local temp_value=$(docker exec etcd-node1 etcdctl get temp-key --print-value-only)
    if [[ "$temp_value" == "temp-value" ]]; then
        log_info "✓ Lease test passed"
    else
        log_error "✗ Lease test failed"
        return 1
    fi

    # Test 4: Transaction
    log_info "Test 4: Test transaction"
    docker exec etcd-node1 etcdctl put counter "0" > /dev/null
    docker exec etcd-node1 etcdctl txn <<EOF > /dev/null
compare:
value("counter") = "0"

success requests (gets, puts, deletes):
put counter "1"

failure requests (gets, puts, deletes):

EOF
    local counter=$(docker exec etcd-node1 etcdctl get counter --print-value-only)
    if [[ "$counter" == "1" ]]; then
        log_info "✓ Transaction test passed"
    else
        log_error "✗ Transaction test failed"
        return 1
    fi
}

get_cluster_status() {
    local leader_id=""
    local nodes_status=()

    for i in $(seq 1 "$NODES"); do
        local status=$(docker exec "etcd-node$i" etcdctl endpoint status --cluster -w json 2>/dev/null || echo "[]")

        # Extract leader info
        local is_leader=$(echo "$status" | jq -r ".[0].Status.leader == .[0].Status.header.member_id")
        if [[ "$is_leader" == "true" ]]; then
            leader_id="etcd-node$i"
        fi

        # Build node status
        local node_info=$(cat <<JSON
{
  "node": "etcd-node$i",
  "endpoint": "http://localhost:$((2378 + i))",
  "is_leader": $is_leader,
  "healthy": true
}
JSON
)
        nodes_status+=("$node_info")
    done

    # Build JSON output
    if [[ $JSON_OUTPUT -eq 1 ]]; then
        cat <<JSON
{
  "cluster_size": $NODES,
  "leader": "$leader_id",
  "nodes": [
    $(IFS=,; echo "${nodes_status[*]}")
  ],
  "tests": {
    "write_read": "passed",
    "replication": "passed",
    "lease": "passed",
    "transaction": "passed"
  }
}
JSON
    else
        log_info "=== Cluster Status ==="
        log_info "Cluster size: $NODES nodes"
        log_info "Leader: $leader_id"
        log_info "All tests passed!"
        log_info ""
        log_info "Access cluster:"
        for i in $(seq 1 "$NODES"); do
            log_info "  Node $i: http://localhost:$((2378 + i))"
        done
        log_info ""
        log_info "Example commands:"
        log_info "  docker exec etcd-node1 etcdctl put mykey myvalue"
        log_info "  docker exec etcd-node1 etcdctl get mykey"
        log_info "  docker exec etcd-node1 etcdctl watch mykey"
        log_info ""
        log_info "Cleanup:"
        log_info "  $0 --cleanup"
    fi
}

main() {
    parse_args "$@"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if [[ $CLEANUP -eq 1 ]]; then
        cleanup_cluster
        exit 0
    fi

    # Setup cluster
    cleanup_cluster
    create_network
    start_etcd_cluster

    # Test cluster
    test_cluster

    # Show status
    get_cluster_status
}

main "$@"
