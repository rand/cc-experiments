---
name: debugging-memory-leak-debugging
description: Comprehensive memory leak detection and debugging using heap profiling tools across multiple languages
---

# Memory Leak Debugging

**Scope**: Heap profiling, memory leak detection patterns, and tools for Python, Go, Rust, C/C++, and .NET
**Lines**: ~440
**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Application memory usage grows unbounded over time
- Out-of-memory errors occur in production or long-running processes
- Need to profile heap allocations and identify leak sources
- Investigating memory bloat in microservices or servers
- Validating memory cleanup in resource-intensive applications
- Debugging reference cycles or unreleased resources
- Optimizing memory footprint for containerized applications
- Analyzing memory patterns in Python, Go, Rust, C/C++, or .NET

---

## Core Concepts

### Concept 1: Memory Leak Types

**Leak Categories**:
- **Direct leaks**: Allocated memory never freed (no references)
- **Indirect leaks**: Memory reachable only through leaked blocks
- **Still-reachable**: Memory with valid references but not freed at exit
- **Definitely lost**: No pointers to allocated blocks
- **Possibly lost**: Interior pointers only (offset from allocation start)

**Common Causes**:
- Forgotten deallocations (missing free/delete)
- Reference cycles in garbage-collected languages
- Event listener leaks (unsubscribed callbacks)
- Cache unbounded growth
- Thread-local storage leaks
- Static container growth

```python
# ❌ Memory leak: cached data never evicted
cache = {}

def get_user(user_id):
    if user_id not in cache:
        cache[user_id] = fetch_user(user_id)  # Cache grows forever
    return cache[user_id]

# ✅ Fixed: use LRU cache with size limit
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user(user_id):
    return fetch_user(user_id)
```

### Concept 2: Heap Profiling Workflow

**Standard Process**:
1. **Establish baseline**: Measure initial memory usage
2. **Run workload**: Execute representative operations
3. **Capture snapshot**: Take heap dump at intervals
4. **Compare snapshots**: Identify growing allocations
5. **Analyze backtraces**: Find allocation call stacks
6. **Fix and verify**: Patch leaks, re-profile to confirm

**Sampling vs Tracking**:
- **Sampling**: Periodic snapshots, lower overhead (production-safe)
- **Tracking**: Record every allocation, high overhead (dev/staging only)

```bash
# Production-safe sampling (low overhead)
py-spy record -o profile.svg --duration 60 python app.py

# Development tracking (high overhead)
valgrind --leak-check=full --track-origins=yes ./binary
```

### Concept 3: Leak Detection Tools by Language

**Tool Selection Matrix**:

| Language | Primary Tool | Secondary Tool | Production-Safe |
|----------|--------------|----------------|-----------------|
| C/C++ | Valgrind | AddressSanitizer | ASan only |
| Python | tracemalloc | memory_profiler | tracemalloc yes |
| Go | pprof heap | heapster | pprof yes |
| Rust | MIRI | valgrind | No (dev only) |
| .NET | dotnet-dump | PerfView | dotnet-dump yes |
| Java | VisualVM | Eclipse MAT | Both yes |

**Key Characteristics**:
- **Valgrind**: Zero code changes, high overhead (10-30x slowdown)
- **ASan**: Compile-time instrumentation, moderate overhead (2x slowdown)
- **tracemalloc**: Python stdlib, snapshot comparison, minimal overhead
- **pprof**: Go runtime profiling, live process inspection
- **MIRI**: Rust interpreter, catches undefined behavior

---

## Patterns

### Pattern 1: Valgrind Leak Detection (C/C++)

**When to use**:
- C/C++ applications with suspected memory leaks
- Need detailed leak reports without code changes
- Development/staging environments (overhead acceptable)

```bash
# Full leak check with origins tracking
valgrind --leak-check=full \
         --show-leak-kinds=all \
         --track-origins=yes \
         --log-file=valgrind.log \
         ./myapp arg1 arg2

# Analyze log file
grep "definitely lost" valgrind.log
grep "indirectly lost" valgrind.log

# Example output interpretation:
# ==12345== LEAK SUMMARY:
# ==12345==    definitely lost: 4,096 bytes in 1 blocks
# ==12345==    indirectly lost: 8,192 bytes in 2 blocks
# ==12345==      possibly lost: 0 bytes in 0 blocks
# ==12345==    still reachable: 512 bytes in 4 blocks
```

**Key Options**:
- `--leak-check=full`: Show detailed leak backtraces
- `--track-origins=yes`: Track uninitialized value origins
- `--show-leak-kinds=all`: Show all leak types (not just definite)
- `--suppressions=file.supp`: Suppress known library leaks

**Benefits**:
- No recompilation required
- Precise leak location reporting
- Handles C libraries transparently

### Pattern 2: AddressSanitizer (ASan) for C/C++

**When to use**:
- Faster leak detection than Valgrind (2x vs 10-30x overhead)
- Integration testing with moderate performance impact
- Compile-time instrumentation acceptable

```bash
# Compile with ASan
g++ -fsanitize=address -g -O1 app.cpp -o app
# or
clang++ -fsanitize=address -g -O1 app.cpp -o app

# Run instrumented binary
ASAN_OPTIONS=detect_leaks=1:log_path=asan.log ./app

# Example ASan report:
# =================================================================
# ==12345==ERROR: LeakSanitizer: detected memory leaks
#
# Direct leak of 4096 byte(s) in 1 object(s) allocated from:
#     #0 0x7f1234567890 in malloc (/lib/x86_64-linux-gnu/libasan.so.5+0x...)
#     #1 0x5678901234ab in allocate_buffer app.cpp:42
#     #2 0x5678901234cd in main app.cpp:123
```

**Configuration via ASAN_OPTIONS**:
```bash
# Common ASan options
export ASAN_OPTIONS="detect_leaks=1:\
                     fast_unwind_on_malloc=0:\
                     malloc_context_size=30:\
                     log_path=asan.log"
```

**Benefits**:
- 10-15x faster than Valgrind
- Catches use-after-free, buffer overflows simultaneously
- Integrates with CI/CD pipelines

### Pattern 3: Python tracemalloc

**When to use**:
- Python applications with growing memory usage
- Need allocation snapshots without external tools
- Production environments (low overhead)

```python
import tracemalloc
import linecache

def display_top(snapshot, key_type='lineno', limit=10):
    """Display top memory allocations."""
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ))
    top_stats = snapshot.statistics(key_type)

    print(f"Top {limit} lines:")
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        filename = frame.filename
        lineno = frame.lineno
        print(f"#{index}: {filename}:{lineno}: {stat.size / 1024:.1f} KiB")
        line = linecache.getline(filename, lineno).strip()
        if line:
            print(f"    {line}")

# Start tracing
tracemalloc.start()

# Take snapshot before operation
snapshot1 = tracemalloc.take_snapshot()

# Run workload
run_application()

# Take snapshot after operation
snapshot2 = tracemalloc.take_snapshot()

# Compare snapshots
top_stats = snapshot2.compare_to(snapshot1, 'lineno')

print("[ Top 10 differences ]")
for stat in top_stats[:10]:
    print(stat)

# Stop tracing
tracemalloc.stop()
```

**Snapshot Comparison**:
```python
# Identify memory growth between snapshots
for stat in top_stats[:10]:
    print(f"{stat.size_diff / 1024:.1f} KiB | {stat.count_diff:+} allocations")
    print(f"  {stat.traceback.format()[0]}")
```

**Benefits**:
- Built into Python stdlib (no dependencies)
- Low overhead (suitable for production)
- Precise line-level allocation tracking

### Pattern 4: Python memory_profiler

**When to use**:
- Line-by-line memory profiling needed
- Debugging specific function memory usage
- Development environments (higher overhead)

```python
# Install: pip install memory_profiler

from memory_profiler import profile

@profile
def process_data(data):
    """Process large dataset."""
    result = []
    for item in data:
        # This line allocates heavily
        result.append(expensive_transform(item))
    return result

# Run with: python -m memory_profiler script.py
# Output:
# Line #    Mem usage    Increment  Occurrences   Line Contents
# ================================================================
#      5   38.816 MiB   38.816 MiB           1   @profile
#      6                                         def process_data(data):
#      7   38.816 MiB    0.000 MiB           1       result = []
#      8  156.234 MiB  117.418 MiB        1001       for item in data:
#      9  156.234 MiB    0.000 MiB        1000           result.append(expensive_transform(item))
#     10  156.234 MiB    0.000 MiB           1       return result
```

**mprof Command-Line Tool**:
```bash
# Record memory usage over time
mprof run python script.py

# Plot memory usage graph
mprof plot

# Show peak memory
mprof peak
```

**Benefits**:
- Line-by-line granularity
- Visual plots of memory over time
- Easy decorator-based profiling

### Pattern 5: Go pprof Heap Profiling

**When to use**:
- Go services with memory growth issues
- Live production profiling (minimal overhead)
- Need allocation flame graphs

```go
package main

import (
    "net/http"
    _ "net/http/pprof"  // Registers /debug/pprof/* handlers
    "runtime"
)

func main() {
    // Enable pprof HTTP endpoint
    go func() {
        http.ListenAndServe("localhost:6060", nil)
    }()

    // Your application code
    runServer()
}

// Programmatic heap profiling
func captureHeapProfile() {
    runtime.GC()  // Get up-to-date statistics
    f, _ := os.Create("heap.prof")
    defer f.Close()
    runtime.WriteHeapProfile(f)
}
```

**Analyzing Heap Profiles**:
```bash
# Capture heap profile from running service
curl http://localhost:6060/debug/pprof/heap > heap.prof

# Interactive analysis
go tool pprof heap.prof
# Commands in interactive mode:
# > top10        # Show top 10 memory consumers
# > list funcName  # Show source with allocations
# > web          # Open browser with call graph

# Generate flame graph
go tool pprof -http=:8080 heap.prof

# Compare two heap snapshots (find memory growth)
curl http://localhost:6060/debug/pprof/heap > heap1.prof
# ... wait and let app run ...
curl http://localhost:6060/debug/pprof/heap > heap2.prof
go tool pprof -base=heap1.prof heap2.prof
```

**Key pprof Commands**:
- `top`: Show functions with highest memory usage
- `list <func>`: Source code with allocation annotations
- `web`: Visual call graph in browser
- `pdf`: Export call graph as PDF

**Benefits**:
- Production-safe (sampling, low overhead)
- Live process inspection
- Visual call graphs and flame graphs

### Pattern 6: Rust MIRI for Memory Debugging

**When to use**:
- Rust unsafe code memory validation
- Development/testing environments only
- Need to catch undefined behavior

```bash
# Install MIRI
rustup +nightly component add miri

# Run tests with MIRI
cargo +nightly miri test

# Run specific binary with MIRI
cargo +nightly miri run

# Example MIRI output for use-after-free:
# error: Undefined Behavior: pointer to alloc123 was dereferenced after this allocation got freed
#  --> src/main.rs:10:13
#   |
# 10|     println!("{}", *ptr);
#   |     ^^^^^^^^^^^^^^^^^ pointer to alloc123 was dereferenced after this allocation got freed
```

**MIRI Capabilities**:
- Detects use-after-free
- Detects invalid pointer arithmetic
- Detects data races (limited)
- Validates unsafe code invariants

**Limitations**:
- Slow (interpreter, not profiler)
- Dev/test only (cannot run in production)
- Cannot analyze external C libraries

### Pattern 7: .NET Memory Diagnostics

**When to use**:
- .NET Core/5+ applications with memory issues
- Production memory dumps analysis
- Cross-platform .NET diagnostics

```bash
# Install dotnet-dump
dotnet tool install --global dotnet-dump

# Capture memory dump from running process
dotnet-dump collect --process-id 12345

# Analyze dump
dotnet-dump analyze core_20251026_123456

# Inside analysis session:
> dumpheap -stat                    # Heap statistics by type
> dumpheap -mt <MethodTable>        # Objects of specific type
> gcroot <address>                  # Find roots keeping object alive
> eeheap -gc                        # GC heap statistics
> objsize <address>                 # Total size including referenced objects
```

**Example Analysis**:
```bash
# Find objects consuming most memory
> dumpheap -stat
# Output shows types sorted by total size:
# MT            Count    TotalSize Class Name
# 00007f1234567890  50000  12800000 System.String
# 00007f1234567891  10000  10240000 MyApp.LargeObject

# Investigate specific type
> dumpheap -mt 00007f1234567891
# Shows all instances of MyApp.LargeObject

# Find what's keeping them alive
> gcroot 00007f9876543210
# Shows reference chain from GC root to object
```

**Eclipse MAT (Memory Analyzer Tool)**:
- Cross-platform Java/.NET heap dump analysis
- Leak suspects report (automatic leak detection)
- Dominator tree (memory ownership visualization)

**Benefits**:
- Production dump analysis
- No application restart needed
- Cross-platform support

### Pattern 8: Heaptrack for C/C++

**When to use**:
- Linux C/C++ memory profiling
- Need GUI visualization of allocations
- Alternative to Valgrind with better performance

```bash
# Install heaptrack
sudo apt install heaptrack heaptrack-gui

# Record heap allocations
heaptrack ./myapp arg1 arg2
# Creates heaptrack.myapp.XXXXX.gz

# Analyze with GUI
heaptrack_gui heaptrack.myapp.12345.gz

# Command-line analysis
heaptrack_print heaptrack.myapp.12345.gz
```

**Heaptrack Features**:
- Flame graph visualization
- Timeline of allocations
- Peak memory analysis
- Call stack attribution
- Leak detection

**Benefits**:
- Lower overhead than Valgrind
- Excellent GUI for visual analysis
- Timeline view shows allocation patterns

---

## Quick Reference

### Tool Selection by Use Case

```
Use Case                    | Tool                      | Overhead  | Production-Safe
----------------------------|---------------------------|-----------|----------------
C/C++ leak detection        | Valgrind                  | 10-30x    | No
C/C++ faster detection      | AddressSanitizer          | 2x        | Maybe (staging)
C/C++ with GUI              | heaptrack                 | Low       | Yes
Python stdlib               | tracemalloc               | <5%       | Yes
Python line-by-line         | memory_profiler           | Medium    | No
Go live profiling           | pprof                     | <3%       | Yes
Rust unsafe validation      | MIRI                      | 100x+     | No (dev only)
.NET production dumps       | dotnet-dump               | N/A       | Yes
Java heap analysis          | Eclipse MAT, VisualVM     | N/A       | Yes (dumps)
```

### Key Guidelines

```
✅ DO: Establish memory baseline before profiling
✅ DO: Use sampling profilers in production (pprof, tracemalloc)
✅ DO: Compare heap snapshots to identify growth
✅ DO: Run leak detectors in CI/CD (ASan, Valgrind in tests)
✅ DO: Set memory limits for caches and containers
✅ DO: Profile representative workloads (not synthetic tests)
✅ DO: Suppress known library leaks in Valgrind

❌ DON'T: Run Valgrind in production (too slow)
❌ DON'T: Ignore "still-reachable" leaks (may indicate issues)
❌ DON'T: Profile debug builds (optimizations affect allocations)
❌ DON'T: Assume GC languages never leak (reference cycles do leak)
❌ DON'T: Profile with insufficient workload (leaks may not appear)
❌ DON'T: Mix profiler data from different runs (inconsistent)
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Unbounded cache growth
class UserService:
    def __init__(self):
        self.cache = {}  # Grows forever

    def get_user(self, user_id):
        if user_id not in self.cache:
            self.cache[user_id] = self.fetch_user(user_id)
        return self.cache[user_id]

# ✅ CORRECT: Use LRU cache with size limit
from functools import lru_cache

class UserService:
    @lru_cache(maxsize=1000)
    def get_user(self, user_id):
        return self.fetch_user(user_id)
```

❌ **Unbounded caching**: Cache grows indefinitely, causing OOM
✅ **Correct approach**: Use LRU cache with max size, TTL eviction, or weak references

### Common Mistakes

```go
// ❌ Don't: Forget to close resources in goroutines
func processFiles(files []string) {
    for _, file := range files {
        go func(f string) {
            data, _ := os.ReadFile(f)  // Leaks if goroutine never exits
            process(data)
        }(file)
    }
}

// ✅ Correct: Use context and cleanup
func processFiles(ctx context.Context, files []string) {
    var wg sync.WaitGroup
    for _, file := range files {
        wg.Add(1)
        go func(f string) {
            defer wg.Done()
            data, err := os.ReadFile(f)
            if err != nil {
                return
            }
            process(data)
        }(file)
    }
    wg.Wait()
}
```

❌ **Unclosed resources in goroutines**: File handles, connections leak
✅ **Better**: Use defer, WaitGroup, and context cancellation

```c++
// ❌ Don't: Raw pointers without ownership
class Service {
    std::vector<Connection*> connections;  // Who owns these?

    void add_connection(Connection* conn) {
        connections.push_back(conn);  // Leak risk
    }
};

// ✅ Correct: Use smart pointers with clear ownership
class Service {
    std::vector<std::unique_ptr<Connection>> connections;

    void add_connection(std::unique_ptr<Connection> conn) {
        connections.push_back(std::move(conn));  // Clear ownership
    }
};
```

❌ **Raw pointer ownership unclear**: Memory leaks from ambiguous ownership
✅ **Better**: Use unique_ptr/shared_ptr for automatic cleanup

```python
# ❌ Don't: Create reference cycles without weak references
class Node:
    def __init__(self, value):
        self.value = value
        self.parent = None  # Strong reference
        self.children = []

    def add_child(self, child):
        child.parent = self  # Cycle: parent <-> child
        self.children.append(child)

# ✅ Correct: Use weak references to break cycles
import weakref

class Node:
    def __init__(self, value):
        self.value = value
        self.parent = None  # Will be weakref
        self.children = []

    def add_child(self, child):
        child.parent = weakref.ref(self)  # Weak reference
        self.children.append(child)
```

❌ **Reference cycles**: Python GC can't collect cyclic references efficiently
✅ **Better**: Use weakref to break cycles in parent-child relationships

```bash
# ❌ Don't: Run production with tracking profilers
valgrind ./production-server  # 10-30x slowdown!

# ✅ Correct: Use sampling profilers in production
# Go
curl http://localhost:6060/debug/pprof/heap > heap.prof

# Python
python -X tracemalloc=5 app.py  # Minimal overhead
```

❌ **Tracking profilers in production**: Valgrind, MIRI unusable in production
✅ **Better**: Use sampling profilers (pprof, tracemalloc, dotnet-dump)

---

## Related Skills

- `testing/performance-testing.md` - Memory profiling integrates with performance tests
- `observability/metrics-instrumentation.md` - Export memory metrics to monitoring systems
- `containers/docker-optimization.md` - Container memory limits and OOM debugging
- `plt/rust-memory-safety.md` - Rust ownership model prevents many leaks
- `debugging/crash-debugging.md` - OOM crashes require memory analysis
- `cicd/testing-strategy.md` - Integrate ASan/Valgrind into CI pipelines

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
