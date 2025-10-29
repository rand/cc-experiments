# Example 8: Profile-Guided Optimization (PGO)

This example demonstrates Profile-Guided Optimization, where compilers use runtime profile data to make better optimization decisions.

## Overview

**PGO Benefits**:
- 10-30% performance improvement (typical)
- Better inlining decisions
- Improved branch prediction
- Optimized instruction cache layout
- Dead code elimination

**Process**:
1. Compile with instrumentation
2. Run with representative workload
3. Collect profile data
4. Recompile with profile data

## C/C++ with GCC

### Sample Application

```c
// fibonacci.c
#include <stdio.h>
#include <stdlib.h>

// Recursive Fibonacci (frequently called with small n)
long long fibonacci_recursive(int n) {
    if (n <= 1) return n;
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2);
}

// Iterative Fibonacci (rarely called)
long long fibonacci_iterative(int n) {
    if (n <= 1) return n;
    long long a = 0, b = 1;
    for (int i = 2; i <= n; i++) {
        long long temp = a + b;
        a = b;
        b = temp;
    }
    return b;
}

// Main function processes typical workload
int main(int argc, char** argv) {
    long long total = 0;

    // Typical workload: mostly small n (hot path)
    for (int i = 0; i < 10000; i++) {
        total += fibonacci_recursive(20);  // Hot: small n
    }

    // Edge case: large n (cold path)
    if (argc > 1) {
        total += fibonacci_iterative(40);  // Cold: rarely executed
    }

    printf("Total: %lld\n", total);
    return 0;
}
```

### Step 1: Instrumented Build

```bash
# Compile with profiling instrumentation
gcc -fprofile-generate -O2 -o fibonacci fibonacci.c

# This generates:
# - Instrumented binary (slower)
# - Will produce *.gcda files on execution
```

### Step 2: Training Run

```bash
# Run with representative workload (typical usage)
./fibonacci

# Generates profile data: fibonacci.gcda
```

### Step 3: Optimized Build

```bash
# Recompile using profile data
gcc -fprofile-use -O2 -o fibonacci fibonacci.c

# Compiler optimizations based on profile:
# - Inline fibonacci_recursive (hot path)
# - Don't inline fibonacci_iterative (cold path)
# - Optimize branch predictions
# - Arrange code for better cache locality
```

### Step 4: Benchmark

```bash
# Compare performance
time ./fibonacci_no_pgo  # Without PGO
time ./fibonacci_pgo     # With PGO

# Typical results:
# No PGO:  2.34s
# With PGO: 1.85s (21% faster)
```

## Multi-Stage Training

### Collect Multiple Profiles

```bash
# Training run 1: typical workload
./fibonacci > /dev/null

# Training run 2: edge case
./fibonacci edge_case_input

# Training run 3: stress test
for i in {1..100}; do ./fibonacci; done

# Merge profiles
gcov-tool merge -o merged.profdata fibonacci*.gcda

# Build with merged profile
gcc -fprofile-use=merged.profdata -O2 -o fibonacci fibonacci.c
```

## C/C++ with Clang/LLVM

### Step 1: Instrumented Build

```bash
# Compile with instrumentation
clang -fprofile-instr-generate -O2 -o fibonacci fibonacci.c
```

### Step 2: Training Run

```bash
# Run and specify profile output
LLVM_PROFILE_FILE="fibonacci.profraw" ./fibonacci

# Or with multiple runs
LLVM_PROFILE_FILE="fibonacci-%p.profraw" ./fibonacci  # %p = PID
```

### Step 3: Convert Profile

```bash
# Convert raw profile to indexed format
llvm-profdata merge -output=fibonacci.profdata fibonacci*.profraw
```

### Step 4: Optimized Build

```bash
# Build with profile
clang -fprofile-instr-use=fibonacci.profdata -O2 -o fibonacci fibonacci.c
```

## Rust with PGO

### Sample Rust Application

```rust
// src/main.rs
fn fibonacci_recursive(n: u64) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2),
    }
}

fn fibonacci_iterative(n: u64) -> u64 {
    let (mut a, mut b) = (0u64, 1u64);
    for _ in 0..n {
        let temp = a;
        a = b;
        b = temp + b;
    }
    a
}

fn main() {
    let mut total = 0u64;

    // Hot path: small n
    for _ in 0..10000 {
        total = total.wrapping_add(fibonacci_recursive(20));
    }

    // Cold path: large n
    if std::env::args().len() > 1 {
        total = total.wrapping_add(fibonacci_iterative(40));
    }

    println!("Total: {}", total);
}
```

### Step 1: Instrumented Build

```bash
# Set environment variable for instrumentation
export RUSTFLAGS="-Cprofile-generate=/tmp/pgo-data"

# Build release binary
cargo build --release

# Binary is in target/release/
```

### Step 2: Training Run

```bash
# Run to collect profile
./target/release/fibonacci

# Profile data written to /tmp/pgo-data/*.profraw
```

### Step 3: Merge Profiles

```bash
# Merge raw profiles
llvm-profdata merge -o /tmp/pgo-data/merged.profdata /tmp/pgo-data/*.profraw
```

### Step 4: Optimized Build

```bash
# Build with profile
export RUSTFLAGS="-Cprofile-use=/tmp/pgo-data/merged.profdata -Cllvm-args=-pgo-warn-missing-function"
cargo build --release

# Optimized binary with PGO
```

### Automated PGO Script

```bash
#!/bin/bash
# pgo_build_rust.sh

PROJECT_NAME="fibonacci"
PGO_DATA="/tmp/pgo-data"

# Clean previous data
rm -rf "$PGO_DATA"
mkdir -p "$PGO_DATA"

# Step 1: Instrumented build
echo "Step 1: Building instrumented binary..."
RUSTFLAGS="-Cprofile-generate=$PGO_DATA" \
    cargo build --release

# Step 2: Training runs
echo "Step 2: Collecting profile data..."
./target/release/$PROJECT_NAME

# Additional training runs
for i in {1..10}; do
    ./target/release/$PROJECT_NAME > /dev/null
done

# Step 3: Merge profiles
echo "Step 3: Merging profiles..."
llvm-profdata merge -o "$PGO_DATA/merged.profdata" "$PGO_DATA"/*.profraw

# Step 4: Optimized build
echo "Step 4: Building optimized binary..."
RUSTFLAGS="-Cprofile-use=$PGO_DATA/merged.profdata" \
    cargo build --release

echo "PGO build complete: target/release/$PROJECT_NAME"
```

## Go with PGO (Go 1.20+)

### Sample Go Application

```go
// main.go
package main

import (
    "flag"
    "fmt"
    "runtime/pprof"
    "os"
)

func fibonacciRecursive(n int) int {
    if n <= 1 {
        return n
    }
    return fibonacciRecursive(n-1) + fibonacciRecursive(n-2)
}

func main() {
    cpuprofile := flag.String("cpuprofile", "", "write cpu profile to file")
    flag.Parse()

    if *cpuprofile != "" {
        f, _ := os.Create(*cpuprofile)
        defer f.Close()
        pprof.StartCPUProfile(f)
        defer pprof.StopCPUProfile()
    }

    total := 0
    for i := 0; i < 10000; i++ {
        total += fibonacciRecursive(20)
    }

    fmt.Printf("Total: %d\n", total)
}
```

### Step 1: Default Build

```bash
go build -o fibonacci main.go
```

### Step 2: Collect CPU Profile

```bash
# Run and collect profile
./fibonacci -cpuprofile=default.pgo
```

### Step 3: PGO Build

```bash
# Go automatically uses default.pgo if present
go build -o fibonacci main.go

# Or specify custom profile
go build -pgo=custom.pgo -o fibonacci main.go
```

### Verification

```bash
# Check if PGO was used
go build -pgo=default.pgo -n 2>&1 | grep "PGO"

# Benchmark comparison
go test -bench=. -cpuprofile=baseline.prof
go build -pgo=baseline.prof
go test -bench=. -cpuprofile=pgo.prof
```

## Best Practices

### 1. Representative Workload

```bash
# ❌ Bad: Synthetic test
./app --test-mode

# ✓ Good: Production-like workload
./app < production_sample.dat

# ✓ Better: Multiple scenarios
for input in scenarios/*.dat; do
    ./app < "$input"
done
```

### 2. Profile Staleness

```bash
# Update profiles regularly (e.g., every release)
# Stale profiles can hurt performance

# Check profile age
stat -c %y fibonacci.profdata

# Regenerate if >30 days old
if [ $(find fibonacci.profdata -mtime +30) ]; then
    echo "Profile stale, regenerating..."
    ./regenerate_profile.sh
fi
```

### 3. Validation

```bash
#!/bin/bash
# validate_pgo.sh

# Build without PGO
gcc -O2 -o app_baseline app.c

# Build with PGO
gcc -fprofile-generate -O2 -o app_instrumented app.c
./app_instrumented < workload.dat
gcc -fprofile-use -O2 -o app_pgo app.c

# Benchmark
echo "Baseline:"
time ./app_baseline < workload.dat

echo "PGO:"
time ./app_pgo < workload.dat

# Verify correctness
diff <(./app_baseline < test.dat) <(./app_pgo < test.dat)
if [ $? -eq 0 ]; then
    echo "✓ PGO build is correct"
else
    echo "✗ PGO build produced different output!"
    exit 1
fi
```

### 4. CI/CD Integration

```yaml
# .github/workflows/pgo-build.yml
name: PGO Build

on:
  release:
    types: [published]

jobs:
  pgo-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: sudo apt-get install -y gcc llvm

      - name: Instrumented build
        run: gcc -fprofile-generate -O2 -o app app.c

      - name: Training run
        run: |
          ./app < workload1.dat
          ./app < workload2.dat
          ./app < workload3.dat

      - name: Optimized build
        run: gcc -fprofile-use -O2 -o app app.c

      - name: Benchmark
        run: ./benchmark.sh

      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: pgo-binary
          path: app
```

## Troubleshooting

### Issue: Warning "no profile data available"

```bash
# Ensure training run completed
ls -la *.gcda  # GCC
ls -la *.profraw  # Clang

# If missing, training run didn't complete or crashed
```

### Issue: Profile merge errors

```bash
# Clang/LLVM: Version mismatch
clang --version
llvm-profdata --version  # Must match

# GCC: Incompatible profiles
# Regenerate all profiles with same compiler version
```

### Issue: No performance improvement

```bash
# Check if profile was actually used
gcc -fprofile-use -Q --help=optimizers | grep profile

# Verify workload is representative
# Profile data should cover hot paths exercised in production
```

### Issue: Performance regression

```bash
# Profile may be stale or unrepresentative
# Regenerate with current workload

# Or disable PGO for affected functions
__attribute__((noinline, cold))
void problematic_function() {
    // Compiler won't aggressively optimize
}
```

## Results Analysis

### Measure Improvement

```bash
#!/bin/bash
# measure_pgo_improvement.sh

ITERATIONS=10

# Baseline
echo "Measuring baseline..."
total_baseline=0
for i in $(seq 1 $ITERATIONS); do
    runtime=$(./app_baseline 2>&1 | grep "Time:" | awk '{print $2}')
    total_baseline=$(echo "$total_baseline + $runtime" | bc)
done
avg_baseline=$(echo "scale=3; $total_baseline / $ITERATIONS" | bc)

# PGO
echo "Measuring PGO..."
total_pgo=0
for i in $(seq 1 $ITERATIONS); do
    runtime=$(./app_pgo 2>&1 | grep "Time:" | awk '{print $2}')
    total_pgo=$(echo "$total_pgo + $runtime" | bc)
done
avg_pgo=$(echo "scale=3; $total_pgo / $ITERATIONS" | bc)

# Calculate improvement
improvement=$(echo "scale=2; ($avg_baseline - $avg_pgo) / $avg_baseline * 100" | bc)

echo "Baseline:    ${avg_baseline}s"
echo "PGO:         ${avg_pgo}s"
echo "Improvement: ${improvement}%"
```

### Expected Improvements

| Workload Type       | Typical Improvement |
|---------------------|---------------------|
| Branch-heavy        | 15-30%              |
| Loop-intensive      | 10-20%              |
| Recursive           | 20-35%              |
| I/O-bound           | 5-10%               |
| Mixed               | 10-20%              |

## Summary

- **PGO**: Compiler optimization using runtime profile data
- **Improvement**: 10-30% typical, up to 50% for branch-heavy code
- **Best For**: CPU-bound applications with predictable hot paths
- **Languages**: C/C++ (GCC/Clang), Rust, Go, Java, .NET
- **Workflow**: Instrument → Profile → Optimize
- **Production Use**: Update profiles regularly (every release)
- **Trade-offs**: Additional build complexity for performance gain
