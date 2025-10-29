# Performance Profiling Resources

Comprehensive production-ready resources for performance profiling and optimization.

## Overview

This directory contains complete documentation, scripts, and examples for profiling applications across multiple languages and environments.

## Contents

### 1. REFERENCE.md (2,807 lines)

Comprehensive reference documentation covering:

- **Profiling Fundamentals**: Sampling vs instrumentation, types of profiling
- **CPU Profiling**: perf, VTune, gprof, language-specific profilers
- **Memory Profiling**: Valgrind, heaptrack, language-specific tools
- **I/O Profiling**: iotop, strace, eBPF tools
- **Network Profiling**: tcpdump, Wireshark, latency analysis
- **Flame Graphs**: Generation, interpretation, differential analysis
- **Language-Specific**: Python, Go, Node.js, Rust, Java, C/C++
- **Production Profiling**: Continuous profiling, low-overhead techniques
- **Profile-Guided Optimization**: GCC, Clang, Rust, Go
- **Bottleneck Identification**: Amdahl's Law, critical path analysis
- **Optimization Strategies**: Algorithmic, caching, concurrency, SIMD
- **Anti-Patterns**: Common mistakes and how to avoid them

### 2. Scripts (3 production-ready tools)

#### profile_application.py (911 lines)
Multi-language profiling automation with flame graph generation.

**Features**:
- Auto-detects language (Python, Node.js, Go, Java, native)
- Supports CPU, memory, and I/O profiling modes
- Generates flame graphs automatically
- Attach to running processes or profile from start
- Differential profiling for before/after comparison
- Low overhead sampling for production use

**Usage**:
```bash
# Profile Python script
./profile_application.py python script.py

# Profile running process
./profile_application.py --pid 12345 --duration 60

# Profile Go benchmark
./profile_application.py --language go go test -bench .

# Differential profiling
./profile_application.py --diff baseline.py optimized.py
```

#### analyze_profile.py (826 lines)
Profile analysis with hotspot identification and optimization recommendations.

**Features**:
- Supports perf, pprof, py-spy formats
- Identifies hotspots (>5% of runtime)
- Generates specific optimization recommendations
- Statistical analysis of function performance
- Severity classification (critical/high/medium)
- JSON and human-readable output

**Usage**:
```bash
# Analyze perf profile
./analyze_profile.py profile.data

# Analyze with detailed recommendations
./analyze_profile.py cpu.prof --type pprof --detailed

# JSON output for automation
./analyze_profile.py profile.data --json > analysis.json
```

#### benchmark_compare.py (867 lines)
Performance regression detection with statistical significance testing.

**Features**:
- Compares benchmark results across versions
- Statistical significance testing (Welch's t-test)
- Configurable regression thresholds
- HTML report generation
- Exit code 1 on regression (CI-friendly)
- Supports multiple benchmark formats

**Usage**:
```bash
# Compare two benchmark runs
./benchmark_compare.py baseline.json current.json

# Generate HTML report
./benchmark_compare.py baseline.json current.json --html report.html

# Fail on regression (for CI)
./benchmark_compare.py baseline.json current.json --fail-on-regression

# Custom thresholds
./benchmark_compare.py baseline.json current.json --regression-threshold 0.10
```

### 3. Examples (9 production scenarios)

#### 01-python-cprofile-snakeviz.md
Python profiling with cProfile and SnakeViz visualization.
- Built-in deterministic profiling
- Interactive flame graphs
- Development workflow
- CI integration

#### 02-py-spy-production-profiling.md
Production-safe Python profiling with py-spy.
- Sampling profiler (1-3% overhead)
- Attach to running processes
- Docker and Kubernetes integration
- Continuous profiling setup

#### 03-go-pprof-profiling.md
Go application profiling with built-in pprof.
- HTTP endpoints for live profiling
- CPU and memory profiling
- Benchmark integration
- Web UI analysis

#### 04-nodejs-clinic-profiling.md
Node.js profiling with Clinic.js suite.
- Doctor: Overall health check
- Flame: CPU flame graphs
- Bubbleprof: Async operation visualization
- Heapprofiler: Memory analysis

#### 05-linux-perf-flame-graphs.md
System-wide profiling with Linux perf.
- Universal profiling tool
- Flame graph generation
- Performance counters
- Off-CPU analysis

#### 06-valgrind-memory-leaks.md
Memory leak detection with Valgrind.
- Memcheck: Leak detection
- Massif: Heap profiling
- Use-after-free detection
- CI/CD integration

#### 07-continuous-profiling-pyroscope.md
Always-on profiling with Pyroscope.
- Multi-language support
- Historical performance data
- Tag-based filtering
- Production deployment

#### 08-profile-guided-optimization.md
Compiler optimization using runtime profiles.
- GCC and Clang workflows
- Rust and Go PGO
- 10-30% performance improvements
- CI/CD automation

#### 09-performance-regression-ci.md
Automated regression detection in CI/CD.
- GitHub Actions integration
- Automated baseline comparison
- PR comments with results
- Performance trend tracking

## Quick Start

### 1. Profile an Application

```bash
# Automatic language detection and profiling
./scripts/profile_application.py your_app

# View generated flame graph
open profiles/flame_*.svg
```

### 2. Analyze Profile

```bash
# Get hotspots and recommendations
./scripts/analyze_profile.py profiles/profile.data

# Output shows:
# - Top hotspots (>5% of time)
# - Severity classification
# - Specific optimization recommendations
```

### 3. Compare Benchmarks

```bash
# Detect performance regressions
./scripts/benchmark_compare.py baseline.json current.json

# Exit code 0: No regressions
# Exit code 1: Regressions detected
```

## Integration Patterns

### CI/CD Pipeline

```yaml
# .github/workflows/profile.yml
- name: Profile
  run: ./scripts/profile_application.py --pid $PID --duration 60

- name: Analyze
  run: ./scripts/analyze_profile.py profile.data --json > analysis.json

- name: Check for regressions
  run: ./scripts/benchmark_compare.py baseline.json current.json --fail-on-regression
```

### Production Monitoring

```bash
# Continuous profiling with Pyroscope
# See examples/07-continuous-profiling-pyroscope.md
docker run -d -p 4040:4040 pyroscope/pyroscope:latest server
```

## Best Practices

1. **Profile before optimizing**: Measure, don't guess
2. **Use sampling in production**: <5% overhead
3. **Focus on hotspots**: Optimize 20% that takes 80% of time
4. **Verify improvements**: Benchmark before/after
5. **Automate regression detection**: Integrate into CI/CD

## Tool Selection Matrix

| Need                  | Tool                      | Overhead | Scope       |
|-----------------------|---------------------------|----------|-------------|
| Python development    | cProfile + SnakeViz       | 5-20%    | Process     |
| Python production     | py-spy                    | 1-3%     | Process     |
| Go profiling          | pprof                     | 1-5%     | Process     |
| Node.js development   | Clinic.js                 | 10-50%   | Process     |
| System-wide (Linux)   | perf                      | 1-5%     | System      |
| Memory leaks (C/C++)  | Valgrind                  | 10-100x  | Process     |
| Continuous profiling  | Pyroscope                 | 1-2%     | Fleet       |
| Compiler optimization | PGO (GCC/Clang/Rust)      | N/A      | Build-time  |
| Regression detection  | pytest-benchmark + CI     | N/A      | CI/CD       |

## Requirements

### System Tools
- Linux: perf, valgrind
- Python: py-spy, pytest-benchmark
- Go: pprof (built-in)
- Node.js: clinic.js

### Installation

```bash
# Python tools
pip install py-spy pytest-benchmark

# Node.js tools
npm install -g clinic

# Go tools (built-in)
go install golang.org/x/tools/cmd/pprof@latest

# Linux tools
sudo apt-get install linux-tools-generic valgrind

# FlameGraph
git clone https://github.com/brendangregg/FlameGraph.git
export PATH=$PATH:$(pwd)/FlameGraph
```

## Resources

### External Links
- [Brendan Gregg's Blog](http://www.brendangregg.com/) - Performance analysis expert
- [FlameGraph Repository](https://github.com/brendangregg/FlameGraph)
- [Pyroscope Documentation](https://pyroscope.io/docs/)
- [Linux perf Examples](http://www.brendangregg.com/perf.html)
- [Go Profiling Guide](https://go.dev/blog/pprof)

### Books
- *Systems Performance* by Brendan Gregg
- *The Art of Application Performance Testing* by Ian Molyneaux
- *High Performance Python* by Micha Gorelick and Ian Ozsvald

## Contributing

To add new examples or improve existing content:

1. Follow existing example structure
2. Include complete, runnable code samples
3. Provide expected output and interpretation
4. Document troubleshooting steps
5. Test on multiple platforms if applicable

## License

These resources are part of the cc-polymath skill library and follow the repository license.

---

**Last Updated**: 2025-10-29
**Total Lines**: ~8,000+ across all files
**Examples**: 9 production-ready scenarios
**Scripts**: 3 comprehensive tools (2,600+ lines)
