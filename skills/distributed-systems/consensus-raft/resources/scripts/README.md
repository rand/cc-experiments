# RAFT Consensus Scripts

This directory contains executable scripts for testing, benchmarking, and visualizing RAFT consensus systems.

## Scripts Overview

### test_etcd_cluster.sh
Automated Docker-based etcd cluster setup and testing. Spins up multi-node RAFT cluster, runs consistency tests, and verifies replication.

**Usage**:
```bash
# Start 3-node cluster with tests
./test_etcd_cluster.sh

# Custom cluster size
./test_etcd_cluster.sh --nodes 5

# JSON output for CI/CD
./test_etcd_cluster.sh --nodes 3 --json

# Cleanup
./test_etcd_cluster.sh --cleanup
```

**What it tests**:
- Write/read consistency
- Log replication across nodes
- Lease/TTL functionality
- Transaction atomicity

**Output**: Cluster status with node endpoints, test results, and access instructions.

---

### benchmark_consensus.py
Performance benchmarking tool for RAFT consensus operations. Measures latency distribution and throughput under various workloads.

**Usage**:
```bash
# Basic benchmark (1000 operations)
./benchmark_consensus.py

# High-throughput test
./benchmark_consensus.py --operations 10000 --concurrency 100

# Custom endpoints and output
./benchmark_consensus.py --endpoints localhost:2379,localhost:2380 --json

# Large values
./benchmark_consensus.py --value-size 4096 --operations 5000
```

**Metrics**:
- Latency: min, max, mean, median, p95, p99
- Throughput: operations per second
- Success/failure rates
- Operation types: PUT, GET, Transaction

**Output formats**: Human-readable tables or JSON for automated analysis.

---

### visualize_raft_state.py
Generate visualizations of RAFT state machine, log replication, and leader election processes.

**Usage**:
```bash
# State machine diagram (Mermaid format)
./visualize_raft_state.py --type state-machine --format mermaid

# Log replication sequence (ASCII)
./visualize_raft_state.py --type log-replication --format ascii

# Leader election flow
./visualize_raft_state.py --type leader-election --format mermaid

# Live cluster status
./visualize_raft_state.py --type cluster-status --endpoints localhost:2379

# Save to file
./visualize_raft_state.py --type state-machine --format graphviz --output raft.dot
```

**Visualization types**:
- `state-machine`: Follower/Candidate/Leader transitions
- `log-replication`: Entry replication sequence
- `leader-election`: Election process flow
- `cluster-status`: Live cluster member info

**Output formats**:
- `mermaid`: Mermaid.js diagrams (render with mermaid CLI or web tools)
- `graphviz`: Graphviz DOT format (render with `dot` command)
- `ascii`: Plain text diagrams

---

## Prerequisites

### System Requirements
```bash
# Docker (for test_etcd_cluster.sh)
docker --version

# Python 3.8+ with etcd client
python3 --version
pip install etcd3-py
```

### etcd Installation
```bash
# macOS
brew install etcd

# Linux (download binary)
wget https://github.com/etcd-io/etcd/releases/download/v3.5.10/etcd-v3.5.10-linux-amd64.tar.gz
tar xzvf etcd-v3.5.10-linux-amd64.tar.gz
sudo mv etcd-v3.5.10-linux-amd64/etcd* /usr/local/bin/

# Verify
etcd --version
etcdctl version
```

---

## Complete Workflow Example

### 1. Setup Test Cluster
```bash
# Start 5-node cluster
./test_etcd_cluster.sh --nodes 5

# Output:
# [INFO] Cluster is ready!
# [INFO] Access cluster:
#   Node 1: http://localhost:2379
#   Node 2: http://localhost:2380
#   Node 3: http://localhost:2381
#   ...
```

### 2. Run Benchmarks
```bash
# Benchmark with 10k operations
./benchmark_consensus.py --operations 10000 --concurrency 50 --json > benchmark.json

# Analyze results
cat benchmark.json | jq '.results.put.latency'
# {
#   "min_ms": 1.23,
#   "max_ms": 45.67,
#   "mean_ms": 3.45,
#   "p99_ms": 12.34
# }
```

### 3. Visualize State
```bash
# Generate state machine diagram
./visualize_raft_state.py --type state-machine --format mermaid --output state.mmd

# Render with mermaid CLI (if installed)
mmdc -i state.mmd -o state.svg

# Or copy to https://mermaid.live for online rendering
```

### 4. Test Fault Tolerance
```bash
# In terminal 1: Monitor cluster
watch -n 1 './visualize_raft_state.py --type cluster-status'

# In terminal 2: Kill a node
docker stop etcd-node2

# Observe leader election and recovery in terminal 1

# Restart node
docker start etcd-node2
```

### 5. Cleanup
```bash
./test_etcd_cluster.sh --cleanup
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Test RAFT Consensus
  run: |
    cd skills/distributed-systems/consensus-raft/resources/scripts
    ./test_etcd_cluster.sh --json > cluster-status.json
    ./benchmark_consensus.py --operations 1000 --json > benchmark.json

- name: Verify Performance
  run: |
    p99=$(jq -r '.results.put.latency.p99_ms' benchmark.json)
    if (( $(echo "$p99 > 50" | bc -l) )); then
      echo "P99 latency too high: ${p99}ms"
      exit 1
    fi
```

---

## Troubleshooting

### Cluster Won't Start
```bash
# Check Docker
docker ps
docker network ls

# Cleanup and retry
./test_etcd_cluster.sh --cleanup
./test_etcd_cluster.sh
```

### Connection Refused
```bash
# Check etcd is listening
docker exec etcd-node1 netstat -tlnp | grep 2379

# Verify endpoints
./visualize_raft_state.py --type cluster-status --endpoints localhost:2379
```

### Benchmark Fails
```bash
# Ensure cluster is running
docker ps | grep etcd

# Test connectivity
docker exec etcd-node1 etcdctl put test-key test-value
docker exec etcd-node1 etcdctl get test-key

# Run with fewer operations
./benchmark_consensus.py --operations 100 --concurrency 5
```

---

## Advanced Usage

### Custom Cluster Configuration
```bash
# test_etcd_cluster.sh uses these environment variables:
export ETCD_VERSION="v3.5.10"
export NODES=7
./test_etcd_cluster.sh
```

### Benchmark Scenarios
```bash
# Small keys, large values (blob storage)
./benchmark_consensus.py --key-size 16 --value-size 8192 --operations 1000

# Large keys, small values (configuration)
./benchmark_consensus.py --key-size 256 --value-size 64 --operations 5000

# Mixed workload with high concurrency
./benchmark_consensus.py --operations 50000 --concurrency 200
```

### Visualization Pipeline
```bash
# Generate all diagrams
for type in state-machine log-replication leader-election; do
  ./visualize_raft_state.py --type $type --format mermaid --output ${type}.mmd
done

# Render with mermaid CLI
for file in *.mmd; do
  mmdc -i $file -o ${file%.mmd}.svg
done
```

---

## Performance Baselines

**Typical Results** (3-node cluster, same datacenter):

| Operation   | P50 Latency | P99 Latency | Throughput    |
|-------------|-------------|-------------|---------------|
| PUT         | 2-5 ms      | 10-20 ms    | 500-1000 ops/s|
| GET         | 0.5-2 ms    | 5-10 ms     | 2000-5000 ops/s|
| Transaction | 3-8 ms      | 15-30 ms    | 300-600 ops/s |

**Factors affecting performance**:
- Network latency between nodes
- Disk I/O speed (fsync)
- Cluster size (more nodes = slower writes)
- Payload size
- Concurrent clients

---

## References

- etcd Documentation: https://etcd.io/docs/
- RAFT Paper: https://raft.github.io/raft.pdf
- etcd Performance Benchmarking: https://etcd.io/docs/v3.5/op-guide/performance/
- Docker Compose for etcd: https://github.com/etcd-io/etcd/tree/main/contrib/docker-compose

---

**Last Updated**: 2025-10-27
