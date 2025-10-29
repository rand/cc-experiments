# Example 3: Go pprof CPU and Memory Profiling

This example demonstrates built-in profiling for Go applications using pprof with interactive analysis and flame graphs.

## Sample Go Application

```go
// main.go
package main

import (
    "fmt"
    "math"
    "net/http"
    _ "net/http/pprof"  // Import for side-effect: registers pprof handlers
    "runtime"
    "time"
)

// CPUIntensive performs expensive computation
func CPUIntensive(n int) int {
    result := 0
    for i := 0; i < n; i++ {
        result += int(math.Sqrt(float64(i)))
    }
    return result
}

// MemoryIntensive allocates large data structures
func MemoryIntensive() [][]int {
    data := make([][]int, 0, 1000)
    for i := 0; i < 1000; i++ {
        row := make([]int, 1000)
        for j := range row {
            row[j] = i * j
        }
        data = append(data, row)
    }
    return data
}

// Worker simulates background work
func Worker() {
    for {
        _ = CPUIntensive(10000)
        _ = MemoryIntensive()
        time.Sleep(100 * time.Millisecond)
    }
}

func handler(w http.ResponseWriter, r *http.Request) {
    result := CPUIntensive(50000)
    fmt.Fprintf(w, "Result: %d\n", result)
}

func main() {
    // Start background workers
    for i := 0; i < 3; i++ {
        go Worker()
    }

    // HTTP server with pprof endpoints
    http.HandleFunc("/", handler)

    fmt.Println("Server starting on :8080")
    fmt.Println("Profile endpoints:")
    fmt.Println("  http://localhost:8080/debug/pprof/")
    fmt.Println("  http://localhost:8080/debug/pprof/profile?seconds=30")
    fmt.Println("  http://localhost:8080/debug/pprof/heap")
    fmt.Println("  http://localhost:8080/debug/pprof/goroutine")

    if err := http.ListenAndServe(":8080", nil); err != nil {
        panic(err)
    }
}
```

## HTTP Server Profiling (Production)

### 1. Access Profile Endpoints

```bash
# CPU profile (30 second sample)
curl http://localhost:8080/debug/pprof/profile?seconds=30 > cpu.prof

# Heap profile (memory)
curl http://localhost:8080/debug/pprof/heap > heap.prof

# Goroutine profile
curl http://localhost:8080/debug/pprof/goroutine > goroutine.prof

# Block profile (lock contention)
curl http://localhost:8080/debug/pprof/block > block.prof
```

### 2. Analyze with go tool pprof

```bash
# Interactive mode
go tool pprof cpu.prof

# Commands in interactive mode:
# (pprof) top10           # Top 10 functions by time
# (pprof) list main.CPUIntensive  # Source code with annotations
# (pprof) web             # Open call graph in browser
# (pprof) svg > profile.svg  # Generate SVG flame graph
# (pprof) quit
```

### 3. Web UI (Recommended)

```bash
# Start interactive web UI
go tool pprof -http=:8081 cpu.prof

# Opens browser with:
# - Flame graph
# - Top functions
# - Source code view
# - Call graph
```

## Benchmark Profiling

### Sample Benchmark

```go
// benchmark_test.go
package main

import (
    "testing"
)

func BenchmarkCPUIntensive(b *testing.B) {
    for i := 0; i < b.N; i++ {
        CPUIntensive(10000)
    }
}

func BenchmarkMemoryIntensive(b *testing.B) {
    for i := 0; i < b.N; i++ {
        _ = MemoryIntensive()
    }
}
```

### CPU Profiling

```bash
# Run benchmark with CPU profile
go test -bench=. -cpuprofile=cpu.prof

# Analyze
go tool pprof cpu.prof
# (pprof) top
# (pprof) list BenchmarkCPUIntensive
```

### Memory Profiling

```bash
# Allocations profile
go test -bench=. -memprofile=mem.prof

# Analyze allocation sites
go tool pprof mem.prof
# (pprof) top
# (pprof) list MemoryIntensive

# Analyze by allocation space (total allocated)
go tool pprof -alloc_space mem.prof

# Analyze by in-use space (currently allocated)
go tool pprof -inuse_space mem.prof
```

### Block Profiling (Lock Contention)

```go
// Enable block profiling
func init() {
    runtime.SetBlockProfileRate(1)  // Sample every block event
}
```

```bash
# Run with block profile
go test -bench=. -blockprofile=block.prof

# Analyze
go tool pprof block.prof
```

## Programmatic Profiling

### CPU Profile

```go
package main

import (
    "os"
    "runtime/pprof"
)

func main() {
    // Create CPU profile file
    f, err := os.Create("cpu.prof")
    if err != nil {
        panic(err)
    }
    defer f.Close()

    // Start profiling
    if err := pprof.StartCPUProfile(f); err != nil {
        panic(err)
    }
    defer pprof.StopCPUProfile()

    // Code to profile
    for i := 0; i < 10; i++ {
        CPUIntensive(100000)
    }
}
```

### Memory Profile

```go
package main

import (
    "os"
    "runtime"
    "runtime/pprof"
)

func main() {
    // Code to profile
    for i := 0; i < 10; i++ {
        _ = MemoryIntensive()
    }

    // Create memory profile file
    f, err := os.Create("mem.prof")
    if err != nil {
        panic(err)
    }
    defer f.Close()

    // Force GC before capturing profile
    runtime.GC()

    // Write heap profile
    if err := pprof.WriteHeapProfile(f); err != nil {
        panic(err)
    }
}
```

## Interpreting pprof Output

### CPU Profile Example

```
(pprof) top10
Showing nodes accounting for 2.50s, 89.29% of 2.80s total
Dropped 15 nodes (cum <= 0.01s)
Showing top 10 nodes out of 45
      flat  flat%   sum%        cum   cum%
     1.20s 42.86% 42.86%      1.20s 42.86%  main.CPUIntensive
     0.50s 17.86% 60.71%      0.50s 17.86%  math.Sqrt
     0.30s 10.71% 71.43%      0.80s 28.57%  main.Worker
     0.20s  7.14% 78.57%      0.20s  7.14%  runtime.mallocgc
     0.15s  5.36% 83.93%      0.15s  5.36%  runtime.scanobject
```

**flat**: Time spent in function itself (excluding callees)
**cum**: Cumulative time (including callees)

### Memory Profile Example

```
(pprof) top10
Showing nodes accounting for 512MB, 95.3% of 537MB total
      flat  flat%   sum%        cum   cum%
    256MB 47.67% 47.67%     256MB 47.67%  main.MemoryIntensive
    128MB 23.83% 71.50%     128MB 23.83%  runtime.makeslice
     64MB 11.92% 83.42%      64MB 11.92%  runtime.newobject
```

### Flame Graph Interpretation

```
[============== main.Worker ==============]
  [==== CPUIntensive ====][= Sqrt =][MemoryIntensive]
       (42% of time)       (18%)        (15%)
```

**Width**: Proportion of samples (time/memory)
**Height**: Call stack depth

## Advanced Analysis

### Compare Profiles

```bash
# Generate baseline
go test -bench=. -cpuprofile=baseline.prof

# Make optimization changes

# Generate new profile
go test -bench=. -cpuprofile=optimized.prof

# Compare (shows diff)
go tool pprof -base=baseline.prof optimized.prof
# (pprof) top
# Shows functions with +/- changes
```

### Source Code Annotation

```bash
go tool pprof -http=:8081 cpu.prof

# Navigate to "Source" tab
# Shows source code with time spent per line
```

### Call Graph Visualization

```bash
# Generate call graph
go tool pprof -pdf cpu.prof > callgraph.pdf

# Or in interactive mode
(pprof) web

# Opens browser with graphviz call graph:
# - Node size = time spent
# - Edge labels = call counts
```

## Production Best Practices

### 1. Conditional Profiling

```go
package main

import (
    "flag"
    "net/http"
    _ "net/http/pprof"
)

func main() {
    enablePprof := flag.Bool("pprof", false, "Enable pprof endpoints")
    flag.Parse()

    if *enablePprof {
        go func() {
            http.ListenAndServe("localhost:6060", nil)
        }()
    }

    // Rest of application
}
```

### 2. Continuous Profiling

```bash
#!/bin/bash
# continuous_profile_go.sh

APP_HOST="localhost:8080"
PROFILE_DIR="/var/log/profiles"

while true; do
    timestamp=$(date +%Y%m%d_%H%M%S)

    # CPU profile
    curl -s "http://$APP_HOST/debug/pprof/profile?seconds=60" \
        > "$PROFILE_DIR/cpu_$timestamp.prof"

    # Heap profile
    curl -s "http://$APP_HOST/debug/pprof/heap" \
        > "$PROFILE_DIR/heap_$timestamp.prof"

    # Wait 15 minutes before next profile
    sleep 900
done
```

### 3. Automated Analysis

```bash
#!/bin/bash
# analyze_go_profile.sh

PROFILE=$1

# Generate reports
go tool pprof -top -output=top.txt "$PROFILE"
go tool pprof -list=main -output=main.txt "$PROFILE"
go tool pprof -svg -output=flame.svg "$PROFILE"

# Email or upload to monitoring system
echo "Profile analysis completed"
cat top.txt
```

## Troubleshooting

### Issue: No profile data
**Solution**: Ensure enough load during profiling
```bash
# Generate load while profiling
while true; do curl http://localhost:8080/; done &
curl http://localhost:8080/debug/pprof/profile?seconds=30 > cpu.prof
```

### Issue: pprof endpoints not available
**Solution**: Import pprof package
```go
import _ "net/http/pprof"
```

### Issue: Memory profile shows no allocations
**Solution**: Check if GC ran before profile
```go
runtime.GC()  // Force GC
pprof.WriteHeapProfile(f)
```

## CI/CD Integration

```yaml
# .github/workflows/benchmark.yml
name: Benchmark

on: [push, pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-go@v4
        with:
          go-version: '1.21'

      - name: Run benchmarks
        run: |
          go test -bench=. -cpuprofile=cpu.prof -memprofile=mem.prof

      - name: Analyze profiles
        run: |
          go tool pprof -top -output=cpu_top.txt cpu.prof
          go tool pprof -top -output=mem_top.txt mem.prof

      - name: Upload profiles
        uses: actions/upload-artifact@v3
        with:
          name: profiles
          path: |
            *.prof
            *_top.txt
```

## Summary

- **pprof**: Built-in Go profiling tool
- **HTTP Endpoints**: Production-safe profiling
- **Overhead**: ~1-5% (sampling-based)
- **Interactive Analysis**: Web UI with flame graphs
- **Use Cases**: Production debugging, benchmark optimization
