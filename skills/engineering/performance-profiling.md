---
name: engineering-performance-profiling
description: Production-ready performance profiling and optimization strategies
---

# Performance Profiling

**Scope**: CPU profiling, memory profiling, I/O profiling, flame graphs, bottleneck identification, sampling vs instrumentation, production profiling, profile-guided optimization

**Lines**: 387

**Last Updated**: 2025-10-29

---

## When to Use This Skill

Use this skill when:
- Diagnosing performance bottlenecks in production or development
- Optimizing CPU-bound or memory-bound operations
- Analyzing application hotspots and critical paths
- Generating flame graphs for visualization
- Implementing continuous profiling infrastructure
- Applying profile-guided optimization (PGO)
- Investigating memory leaks or allocation patterns
- Profiling I/O or network performance
- Comparing performance before/after optimizations

**Don't use** for:
- Load testing (use load-testing.md)
- Application metrics (use metrics-instrumentation.md)
- Distributed tracing (use distributed-tracing.md)

---

## Core Concepts

### Profiling Types

**CPU Profiling**
- Identifies where CPU time is spent
- Sampling (periodic snapshots) vs instrumentation (every call)
- Overhead: Sampling ~1-5%, instrumentation ~10-100%
- Best for: Computational bottlenecks, hot loops

**Memory Profiling**
- Tracks allocations, deallocations, and memory usage
- Heap profiling, stack profiling, leak detection
- Overhead: 10-50% depending on granularity
- Best for: Memory leaks, excessive allocations, fragmentation

**I/O Profiling**
- Measures disk I/O, network I/O, system calls
- File operations, socket operations, latency analysis
- Overhead: Low for system-level tools
- Best for: I/O bottlenecks, blocking operations

**Lock Profiling**
- Detects contention on mutexes, semaphores, locks
- Identifies serialization bottlenecks in concurrent code
- Best for: Multithreaded performance issues

---

## Profiling Tools by Language

### Python

```bash
# cProfile (built-in, deterministic)
python -m cProfile -o profile.stats script.py
python -m pstats profile.stats  # Interactive analysis

# py-spy (sampling, production-safe)
py-spy record -o profile.svg --format speedscope -- python script.py
py-spy top --pid 12345  # Live top-like display

# memory_profiler
mprof run script.py
mprof plot

# Scalene (CPU + memory + GPU)
scalene script.py
```

### Go

```bash
# CPU profiling
go test -cpuprofile cpu.prof -bench .
go tool pprof cpu.prof

# Memory profiling
go test -memprofile mem.prof -bench .
go tool pprof -alloc_space mem.prof

# Live profiling (pprof server)
import _ "net/http/pprof"
# Access http://localhost:6060/debug/pprof/
```

### Node.js

```bash
# Built-in profiler
node --prof script.js
node --prof-process isolate-*.log > processed.txt

# Chrome DevTools
node --inspect script.js
# Open chrome://inspect

# clinic.js suite
clinic doctor -- node script.js
clinic flame -- node script.js
```

### Rust

```bash
# cargo-flamegraph
cargo install flamegraph
cargo flamegraph --bin myapp

# perf (Linux)
cargo build --release
perf record --call-graph=dwarf ./target/release/myapp
perf report
```

### Java

```bash
# JFR (Java Flight Recorder)
java -XX:StartFlightRecording=filename=recording.jfr MyApp
jcmd <pid> JFR.dump filename=recording.jfr

# async-profiler
./profiler.sh -d 60 -f flamegraph.html <pid>
```

---

## Flame Graphs

### Generation

```bash
# Linux perf
perf record -F 99 -a -g -- sleep 60
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg

# py-spy
py-spy record -o profile.svg --format flamegraph -- python app.py

# Go pprof
go tool pprof -http=:8080 cpu.prof
```

### Interpretation

**X-axis**: Alphabetical order (NOT time)
**Y-axis**: Stack depth
**Width**: Proportion of samples (time spent)
**Color**: Usually random or by function type

**Patterns to look for**:
- Wide plateaus: Hot functions consuming significant time
- Tall stacks: Deep call chains, possible recursion issues
- Narrow spikes: Rare but expensive operations
- Differential flame graphs: Compare before/after optimizations

---

## Bottleneck Identification

### Amdahl's Law

```
Speedup = 1 / ((1 - P) + P/S)

P = Proportion of parallelizable code
S = Speedup of parallelizable portion
```

**Insight**: Optimize the slowest 20% first (80/20 rule)

### Critical Path Analysis

1. **Profile end-to-end**: Measure total execution time
2. **Identify hotspots**: Functions consuming >5% of time
3. **Analyze call graphs**: Find critical paths through hot functions
4. **Measure overhead**: Distinguish algorithm vs overhead (allocation, I/O)
5. **Prioritize optimization**: High impact, low effort first

### Common Bottlenecks

**CPU-bound**:
- Inefficient algorithms (O(n²) when O(n log n) possible)
- Unnecessary computation in loops
- Missing memoization/caching
- Serialization/deserialization overhead

**Memory-bound**:
- Excessive allocations in hot paths
- Cache misses (poor locality of reference)
- Large data copies
- Memory leaks causing GC pressure

**I/O-bound**:
- Synchronous I/O in hot paths
- Missing batching of operations
- Network round-trips in loops (N+1 queries)
- Unbuffered I/O

---

## Optimization Strategies

### Low-Hanging Fruit

1. **Algorithmic improvements**: O(n²) → O(n log n)
2. **Caching**: Memoize expensive computations
3. **Reduce allocations**: Reuse buffers, object pooling
4. **Batch operations**: Combine I/O, reduce round-trips
5. **Lazy evaluation**: Compute only when needed

### Advanced Techniques

**Profile-Guided Optimization (PGO)**
```bash
# Collect profile
RUSTFLAGS="-Cprofile-generate=/tmp/pgo-data" cargo build --release
./target/release/app < typical_workload.txt

# Optimize with profile
llvm-profdata merge -o /tmp/pgo-data/merged.profdata /tmp/pgo-data
RUSTFLAGS="-Cprofile-use=/tmp/pgo-data/merged.profdata" cargo build --release
```

**SIMD vectorization**: Use CPU vector instructions
**Data-oriented design**: Improve cache locality
**Async I/O**: Overlap computation and I/O
**JIT compilation**: Runtime optimization for hot paths

---

## Production Profiling

### Continuous Profiling

**Benefits**:
- Always-on profiling with <1% overhead
- Detect regressions immediately
- Correlate performance with deployments
- Historical performance data

**Tools**:
- **Pyroscope**: Open-source continuous profiling
- **Parca**: eBPF-based profiling for any language
- **Google Cloud Profiler**: Managed service
- **Datadog Continuous Profiler**: Commercial solution

```yaml
# Pyroscope example
services:
  app:
    environment:
      PYROSCOPE_APPLICATION_NAME: myapp
      PYROSCOPE_SERVER_ADDRESS: http://pyroscope:4040
```

### Low-Overhead Techniques

**Sampling profilers**: 1-5% overhead
- py-spy, perf, pprof in sampling mode
- Safe for production

**Adaptive profiling**: Profile only during anomalies
- Trigger on high latency or CPU
- Automatic capture and analysis

**eBPF profiling**: Kernel-level, negligible overhead
- Parca, Pixie
- No application instrumentation

---

## Anti-Patterns

```
❌ Profile without load: Synthetic workload != production
❌ Optimize prematurely: Measure first, then optimize
❌ Ignore Amdahl's Law: Optimizing 1% of runtime has negligible impact
❌ High overhead in prod: >5% overhead affects behavior
❌ Test optimizations without profiling: Verify improvements empirically
❌ Focus on micro-optimizations: Algorithm choice matters more
❌ Profile debug builds: Always profile release builds
❌ Single sample: Take multiple samples to account for variance
```

---

## Quick Reference

### Profiling Workflow

```bash
# 1. Establish baseline
time ./app < workload.txt  # 10.5s

# 2. Profile (choose tool based on language)
perf record -g ./app < workload.txt
py-spy record -o flame.svg -- python app.py < workload.txt
go tool pprof -http=:8080 cpu.prof

# 3. Identify hotspots (>5% of time)
# Look for wide plateaus in flame graph

# 4. Optimize target code
# Apply algorithmic improvements, caching, etc.

# 5. Verify improvement
time ./app < workload.txt  # 3.2s (3.3x speedup)

# 6. Diff profile to confirm
# Compare before/after flame graphs
```

### Tool Selection Matrix

| Language   | CPU Profiling       | Memory Profiling     | Production-Safe   |
|------------|---------------------|----------------------|-------------------|
| Python     | cProfile, py-spy    | memory_profiler      | py-spy, Scalene   |
| Go         | pprof               | pprof (heap)         | pprof (sampling)  |
| Node.js    | clinic.js, --prof   | heapdump             | clinic.js         |
| Rust       | flamegraph, perf    | valgrind, heaptrack  | perf              |
| Java       | JFR, async-profiler | JFR                  | JFR, async-prof   |
| C/C++      | perf, gprof         | valgrind, heaptrack  | perf              |

### Common Commands

```bash
# CPU hotspots (Linux)
perf record -F 99 -a -g -- sleep 60
perf report --stdio | head -50

# Memory leaks (C/C++)
valgrind --leak-check=full --show-leak-kinds=all ./app

# Python profiling
python -m cProfile -s cumtime script.py | head -30

# Go profiling
go tool pprof -top cpu.prof
go tool pprof -list=FunctionName cpu.prof

# Flame graph from perf
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg
```

---

## Resources

See `skills/engineering/resources/performance-profiling/` for:
- **REFERENCE.md**: Comprehensive profiling guide (1,500-4,000 lines)
- **scripts/**: Production-ready profiling scripts
  - `profile_application.py`: Multi-language profiling automation
  - `analyze_profile.py`: Profile analysis and reporting
  - `benchmark_compare.py`: Performance regression detection
- **examples/**: 7-9 production examples covering:
  - Python profiling workflows
  - Go pprof integration
  - Node.js profiling
  - Continuous profiling setup
  - Flame graph generation and analysis
  - Profile-guided optimization
  - Performance CI integration

---

## Integration

**With CI/CD**:
- Benchmark on every commit
- Detect performance regressions
- Block merges on degradation >10%

**With monitoring**:
- Correlate profiles with high latency events
- Auto-trigger profiling on SLO violations
- Historical trend analysis

**With load testing**:
- Profile under realistic load
- Identify scaling bottlenecks
- Validate optimization under stress
