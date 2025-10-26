---
name: debugging-performance-profiling
description: Performance profiling with CPU profilers (perf, pprof, py-spy), flame graphs, memory profiling (heaptrack, Valgrind), and profile-guided optimization
---

# Performance Profiling

**Scope**: CPU profiling (perf, Instruments, pprof, py-spy), flame graphs, sampling vs instrumentation, profile-guided optimization (PGO), memory profiling, I/O profiling, lock contention

**Lines**: 450

**Last Updated**: 2025-10-26

---

## When to Use This Skill

Use this skill when:
- Identifying performance bottlenecks in production or development
- Optimizing CPU-bound operations (hot paths)
- Debugging memory leaks or excessive allocations
- Analyzing I/O performance (disk, network)
- Investigating lock contention in concurrent programs
- Preparing for profile-guided optimization (PGO)
- Generating flame graphs for visual analysis
- Comparing performance before/after optimizations

**Don't use** for:
- Functional debugging (use debuggers)
- Simple timing measurements (use time.time() or timeit)
- Load testing (use k6, Locust, etc.)

---

## Core Concepts

### Profiling Approaches

**Sampling Profiling** (recommended for production):
- Periodically sample call stack (e.g., 100 Hz)
- Low overhead (~1-5%)
- Statistical approximation
- Tools: perf, py-spy, pprof (sampling mode), Instruments

**Instrumentation Profiling** (development only):
- Insert timing code at every function call
- High overhead (10-100x slower)
- Exact measurements
- Tools: cProfile, gprof, Valgrind callgrind

### Profiling Types

```
CPU Profiling: Which functions consume CPU time?
├─ Sampling: perf, py-spy, pprof (Go), Instruments (macOS)
└─ Instrumentation: cProfile (Python), gprof (C/C++)

Memory Profiling: Where is memory allocated?
├─ Heap profiling: heaptrack, Valgrind massif, memory_profiler
├─ Leak detection: Valgrind memcheck, AddressSanitizer
└─ Allocation tracing: jemalloc, tcmalloc

I/O Profiling: Where is time spent waiting?
├─ Disk I/O: iostat, iotop, strace
├─ Network I/O: tcpdump, Wireshark, netstat
└─ Syscall tracing: strace, dtrace, perf trace

Lock Contention: Where do threads wait for locks?
├─ perf lock
├─ Go pprof (mutex profile)
└─ Instruments (macOS Thread State trace)
```

### Visualization Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| **Flame graph** | Stack samples visualized as horizontal bars | Identify hot paths, CPU bottlenecks |
| **Icicle graph** | Inverted flame graph (root at top) | Alternative visualization |
| **Call graph** | Directed graph of function calls | Understand call relationships |
| **Timeline** | Time-based execution trace | Analyze concurrency, I/O waits |

---

## Patterns

### Pattern 1: CPU Profiling with perf (Linux)

```bash
# 1. Record CPU profile (99 Hz sampling)
perf record -F 99 -g -p <pid> -- sleep 30
# -F 99: Sample at 99 Hz (avoid timer bias at 100 Hz)
# -g: Record call stacks
# -p <pid>: Attach to running process
# -- sleep 30: Profile for 30 seconds

# Alternative: Profile command from start
perf record -F 99 -g python app.py

# 2. View report (text)
perf report

# 3. Generate flamegraph
# Install: git clone https://github.com/brendangregg/FlameGraph
perf script | FlameGraph/stackcollapse-perf.pl | FlameGraph/flamegraph.pl > flamegraph.svg
open flamegraph.svg

# 4. Profile all CPUs (system-wide)
sudo perf record -F 99 -g -a -- sleep 30

# 5. Profile specific events
perf list  # List available events
perf record -e cache-misses -g -p <pid> -- sleep 30

# 6. Profile with call graph (dwarf)
perf record -F 99 -g --call-graph dwarf -p <pid> -- sleep 30

# Example workflow
# Terminal 1: Run application
python app.py

# Terminal 2: Profile for 30 seconds
PID=$(pgrep -f app.py)
perf record -F 99 -g -p $PID -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > cpu_profile.svg

# Analyze flamegraph
open cpu_profile.svg
# Look for:
# - Wide bars: CPU-intensive functions
# - Tower shape: Deep call stacks
# - Flat top: Time spent in function itself (not callees)
```

### Pattern 2: CPU Profiling with py-spy (Python)

```bash
# Install py-spy
pip install py-spy

# 1. Profile running Python process
py-spy record -o profile.svg --pid <pid>

# 2. Profile for specific duration
py-spy record -o profile.svg --pid <pid> --duration 60

# 3. Profile with higher sample rate
py-spy record -o profile.svg --pid <pid> --rate 200

# 4. Generate flamegraph
py-spy record -o flamegraph.svg --format flamegraph --pid <pid> --duration 30

# 5. Profile all threads
py-spy record -o profile.svg --pid <pid> --threads

# 6. Profile subprocesses
py-spy record -o profile.svg --pid <pid> --subprocesses

# 7. Top-like interface (live view)
py-spy top --pid <pid>

# Example: Profile FastAPI app
# Terminal 1: Start app
uvicorn app:app --host 0.0.0.0 --port 8000

# Terminal 2: Profile
PID=$(pgrep -f uvicorn)
py-spy record -o profile.svg --pid $PID --duration 60 --rate 200

# Terminal 3: Generate load
wrk -t4 -c100 -d60s http://localhost:8000/api/users

# Analyze profile.svg
open profile.svg
```

### Pattern 3: CPU Profiling with pprof (Go)

```go
package main

import (
    "log"
    "net/http"
    _ "net/http/pprof"
    "os"
    "runtime"
    "runtime/pprof"
)

func main() {
    // Method 1: HTTP server (production)
    go func() {
        log.Println(http.ListenAndServe("localhost:6060", nil))
    }()

    // Method 2: File-based profiling (development)
    f, err := os.Create("cpu.prof")
    if err != nil {
        log.Fatal(err)
    }
    defer f.Close()

    if err := pprof.StartCPUProfile(f); err != nil {
        log.Fatal(err)
    }
    defer pprof.StopCPUProfile()

    // Your application code
    runApp()
}

func runApp() {
    // CPU-intensive work
    for i := 0; i < 1000000; i++ {
        compute(i)
    }
}

func compute(n int) int {
    result := 0
    for i := 0; i < n; i++ {
        result += i
    }
    return result
}
```

**Analyze Go profiles**:
```bash
# Method 1: HTTP endpoint (live profiling)
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# Interactive commands:
# (pprof) top10        # Top 10 functions
# (pprof) list compute # Show source for function
# (pprof) web          # Open in browser (requires graphviz)
# (pprof) svg          # Generate SVG

# Method 2: File-based profile
go tool pprof cpu.prof

# Generate flamegraph
go tool pprof -http=:8080 cpu.prof
# Open http://localhost:8080 in browser

# Generate flamegraph SVG
go tool pprof -output=flamegraph.svg -svg cpu.prof

# Compare two profiles (before/after optimization)
go tool pprof -base=cpu_before.prof cpu_after.prof
```

### Pattern 4: Memory Profiling

**Python (memory_profiler)**:
```python
# Install: pip install memory_profiler

from memory_profiler import profile

@profile
def process_data():
    # Large allocation
    data = [i for i in range(1000000)]

    # Memory leak (never freed)
    cache = {}
    for i in range(100000):
        cache[i] = [0] * 1000

    return data

if __name__ == "__main__":
    process_data()
```

```bash
# Run with memory profiling
python -m memory_profiler app.py

# Output shows memory usage per line:
# Line #    Mem usage    Increment   Line Contents
# ================================================
#      5     38.3 MiB     38.3 MiB   @profile
#      6                             def process_data():
#      8     45.9 MiB      7.6 MiB       data = [i for i in range(1000000)]
#     11    809.4 MiB    763.5 MiB       for i in range(100000):
#     12    809.4 MiB      0.0 MiB           cache[i] = [0] * 1000
```

**C/C++ (Valgrind Massif)**:
```bash
# Run with heap profiling
valgrind --tool=massif ./myapp

# Generates massif.out.<pid>

# Analyze
ms_print massif.out.12345

# Generate graph
massif-visualizer massif.out.12345  # GUI tool
```

**Go (pprof heap)**:
```go
import (
    "net/http"
    _ "net/http/pprof"
    "runtime"
)

func main() {
    // Enable HTTP pprof server
    go func() {
        http.ListenAndServe("localhost:6060", nil)
    }()

    // Your app code
    runApp()
}
```

```bash
# Capture heap profile
go tool pprof http://localhost:6060/debug/pprof/heap

# Interactive commands
(pprof) top        # Top allocations
(pprof) list main  # Show allocations in main

# Generate graph
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/heap
```

### Pattern 5: Flame Graphs

```bash
# Install FlameGraph tools
git clone https://github.com/brendangregg/FlameGraph
cd FlameGraph

# Generate from perf data (Linux)
perf record -F 99 -g -p <pid> -- sleep 30
perf script | ./stackcollapse-perf.pl | ./flamegraph.pl > flame.svg

# Generate from DTrace (macOS)
sudo dtrace -x ustackframes=100 -n 'profile-997 /pid == <pid>/ { @[ustack()] = count(); }' -o out.stacks
./stackcollapse.pl out.stacks | ./flamegraph.pl > flame.svg

# Generate from pprof (Go)
go tool pprof -output=flame.svg -svg cpu.prof

# Generate from py-spy (Python)
py-spy record -o flame.svg --format flamegraph --pid <pid> --duration 30

# Reading flame graphs:
# - X-axis: Alphabetical order (not time!)
# - Y-axis: Stack depth
# - Width: Time spent in function
# - Color: Random (some tools use color for libraries)
# - Click to zoom
# - Look for wide bars (hot functions)
```

### Pattern 6: Profile-Guided Optimization (PGO)

**C/C++ (GCC/Clang)**:
```bash
# Step 1: Compile with instrumentation
gcc -fprofile-generate -O2 myapp.c -o myapp

# Step 2: Run with representative workload
./myapp < typical_input.txt
# Generates *.gcda files

# Step 3: Recompile with profile data
gcc -fprofile-use -O2 myapp.c -o myapp_optimized

# Compare performance
time ./myapp < input.txt
time ./myapp_optimized < input.txt
```

**Go (PGO in Go 1.21+)**:
```bash
# Step 1: Build binary
go build -o myapp

# Step 2: Run with CPU profiling
./myapp --cpuprofile=cpu.prof

# Step 3: Rebuild with profile
go build -pgo=cpu.prof -o myapp_optimized

# Compare
time ./myapp
time ./myapp_optimized
```

**Rust (PGO)**:
```bash
# Step 1: Instrument
RUSTFLAGS="-Cprofile-generate=/tmp/pgo-data" cargo build --release

# Step 2: Run
./target/release/myapp

# Step 3: Merge profiles
llvm-profdata merge -o /tmp/pgo-data/merged.profdata /tmp/pgo-data

# Step 4: Optimize
RUSTFLAGS="-Cprofile-use=/tmp/pgo-data/merged.profdata" cargo build --release
```

### Pattern 7: I/O Profiling

```bash
# 1. strace (syscall tracing)
strace -c python app.py  # Summary
strace -T -e trace=read,write python app.py  # Time per syscall

# 2. iostat (disk I/O)
iostat -x 1  # Extended stats, 1 second interval

# 3. iotop (per-process I/O)
sudo iotop -o  # Only show processes doing I/O

# 4. lsof (open file descriptors)
lsof -p <pid>  # Show open files for process

# 5. perf trace (lightweight strace)
sudo perf trace -p <pid>

# Example: Profile file I/O
# Terminal 1: Run app
python app.py

# Terminal 2: Trace I/O
PID=$(pgrep -f app.py)
strace -e trace=open,read,write,close -c -p $PID
# Ctrl+C after 30 seconds
# Shows count, time, errors per syscall
```

### Pattern 8: Lock Contention Profiling

**Go (mutex profiling)**:
```go
import (
    "net/http"
    _ "net/http/pprof"
    "runtime"
)

func main() {
    // Enable mutex profiling
    runtime.SetMutexProfileFraction(1)

    // HTTP server for pprof
    go func() {
        http.ListenAndServe("localhost:6060", nil)
    }()

    runApp()
}
```

```bash
# Capture mutex profile
go tool pprof http://localhost:6060/debug/pprof/mutex

# Interactive
(pprof) top
(pprof) list main

# Generate graph
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/mutex
```

**Linux (perf lock)**:
```bash
# Record lock contention
sudo perf lock record -p <pid> -- sleep 30

# Report
sudo perf lock report
```

---

## Quick Reference

### Profiling Tools by Language

| Language | CPU Profiling | Memory Profiling | I/O Profiling |
|----------|---------------|------------------|---------------|
| **Python** | py-spy, cProfile | memory_profiler | strace |
| **Go** | pprof (CPU) | pprof (heap) | perf trace |
| **Rust** | perf, cargo-flamegraph | heaptrack, Valgrind | strace |
| **C/C++** | perf, gprof | Valgrind massif | strace, ltrace |
| **Java** | async-profiler | JProfiler, VisualVM | strace |
| **Node.js** | 0x, clinic.js | heapdump | strace |

### perf Commands

```bash
# Record CPU profile
perf record -F 99 -g -p <pid> -- sleep 30

# View report
perf report

# Record specific events
perf record -e cache-misses -g -p <pid>

# Record system-wide
sudo perf record -F 99 -g -a -- sleep 30

# Generate flamegraph
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg

# Record with call graph (dwarf)
perf record -F 99 -g --call-graph dwarf -p <pid>
```

### py-spy Commands

```bash
# Record flamegraph
py-spy record -o profile.svg --pid <pid> --duration 60

# Live top view
py-spy top --pid <pid>

# Profile all threads
py-spy record -o profile.svg --pid <pid> --threads

# Profile subprocesses
py-spy record -o profile.svg --pid <pid> --subprocesses
```

### Go pprof Endpoints

```bash
# CPU profile (30 seconds)
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# Heap profile
go tool pprof http://localhost:6060/debug/pprof/heap

# Goroutine profile
go tool pprof http://localhost:6060/debug/pprof/goroutine

# Mutex profile
go tool pprof http://localhost:6060/debug/pprof/mutex

# Block profile (blocking operations)
go tool pprof http://localhost:6060/debug/pprof/block
```

---

## Anti-Patterns

### ❌ Using Instrumentation Profiling in Production

```python
# WRONG: cProfile slows down production by 10-100x
import cProfile
cProfile.run('app.run()')  # NEVER in production!

# CORRECT: Use sampling profiler (py-spy)
# py-spy record -o profile.svg --pid <pid> --duration 30
```

### ❌ Profiling Debug Builds

```bash
# WRONG: Profile unoptimized build
cargo build  # Debug mode!
perf record ./target/debug/myapp

# CORRECT: Profile release build
cargo build --release
perf record ./target/release/myapp
```

### ❌ Profiling Without Representative Load

```bash
# WRONG: Profile with no traffic
py-spy record -o profile.svg --pid <pid> --duration 60
# App is idle!

# CORRECT: Profile under load
# Terminal 1: Start app
uvicorn app:app

# Terminal 2: Generate load
wrk -t4 -c100 -d60s http://localhost:8000/api/users

# Terminal 3: Profile
py-spy record -o profile.svg --pid <pid> --duration 60
```

### ❌ Ignoring Compiler Optimizations

```c
// WRONG: Volatile prevents optimization
volatile int result = 0;
for (int i = 0; i < 1000000; i++) {
    result += compute(i);
}

// CORRECT: Let compiler optimize
int result = 0;
for (int i = 0; i < 1000000; i++) {
    result += compute(i);
}
// Use result to prevent DCE
printf("%d\n", result);
```

---

## Related Skills

- **debugging/production-debugging.md** - Non-intrusive production debugging
- **testing/performance-testing.md** - Load testing to generate profiling workload
- **observability/metrics-instrumentation.md** - Runtime performance metrics
- **build-systems/compiler-optimization.md** - Compiler flags for performance

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
