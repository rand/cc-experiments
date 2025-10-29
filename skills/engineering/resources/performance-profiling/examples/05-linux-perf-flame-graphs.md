# Example 5: Linux perf with Flame Graph Generation

This example demonstrates system-wide profiling using Linux perf with flame graph visualization for any compiled language.

## Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get install linux-tools-common linux-tools-generic linux-tools-$(uname -r)

# CentOS/RHEL
sudo yum install perf

# FlameGraph tools
git clone https://github.com/brendangregg/FlameGraph.git
export PATH=$PATH:$(pwd)/FlameGraph
```

## Sample C Application

```c
// cpu_intensive.c
#include <stdio.h>
#include <math.h>

double expensive_calculation(int n) {
    double result = 0.0;
    for (int i = 0; i < n; i++) {
        result += sqrt(i) * log(i + 1);
    }
    return result;
}

void process_data(int iterations) {
    for (int i = 0; i < iterations; i++) {
        expensive_calculation(10000);
    }
}

void analyze_data(int iterations) {
    for (int i = 0; i < iterations; i++) {
        expensive_calculation(5000);
    }
}

int main() {
    printf("Starting CPU-intensive work...\n");

    process_data(500);
    analyze_data(1000);

    printf("Completed\n");
    return 0;
}
```

```bash
# Compile with debug symbols
gcc -g -O2 -o cpu_intensive cpu_intensive.c -lm
```

## Basic CPU Profiling

### Record Profile

```bash
# Profile specific command
perf record -g ./cpu_intensive

# System-wide profiling (requires root)
sudo perf record -a -g -- sleep 60

# Profile specific process
perf record -g -p <PID> -- sleep 60

# Custom sampling frequency (default: 1000 Hz)
perf record -F 99 -g ./cpu_intensive  # 99 Hz (less overhead)
```

### View Report

```bash
# Interactive TUI report
perf report

# Text report
perf report --stdio

# Show top 20 functions
perf report --stdio --no-children | head -30

# Filter by symbol/function
perf report --stdio --symbol=expensive_calculation
```

### Example Output

```
# Overhead  Command          Shared Object        Symbol
# ........  ...............  ...................  ........................
#
    45.23%  cpu_intensive    cpu_intensive        [.] expensive_calculation
    12.34%  cpu_intensive    libm.so.6            [.] __ieee754_sqrt_avx2
     8.90%  cpu_intensive    cpu_intensive        [.] process_data
     5.67%  cpu_intensive    cpu_intensive        [.] analyze_data
     4.32%  cpu_intensive    libm.so.6            [.] __log_finite
```

## Generating Flame Graphs

### CPU Flame Graph

```bash
# Record with call graphs
perf record -F 99 -a -g -- sleep 60

# Generate flame graph
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg

# Open in browser
firefox flame.svg
```

### All-in-One Script

```bash
#!/bin/bash
# profile_and_flame.sh

APP=$1
DURATION=${2:-60}
OUTPUT="flame_$(date +%Y%m%d_%H%M%S).svg"

echo "Profiling $APP for ${DURATION}s..."

# Record
perf record -F 99 -g -o perf.data -- "$APP"

# Generate flame graph
perf script -i perf.data | \
    stackcollapse-perf.pl | \
    flamegraph.pl --title "CPU Flame Graph: $APP" > "$OUTPUT"

echo "Flame graph: $OUTPUT"
rm perf.data

# Open
xdg-open "$OUTPUT"
```

## Advanced Profiling

### Call Graph Recording

```bash
# Frame pointer (FP) call graph
perf record -g ./cpu_intensive

# DWARF call graph (more accurate, larger overhead)
perf record -g --call-graph dwarf ./cpu_intensive

# Last Branch Record (LBR, Intel only)
perf record -g --call-graph lbr ./cpu_intensive
```

### CPU-Specific Profiling

```bash
# Profile specific CPUs
perf record -C 0,1 -g -- sleep 60  # CPUs 0 and 1 only

# Pin process to CPU and profile
taskset -c 0 ./cpu_intensive &
perf record -C 0 -g -- sleep 60
```

### Multi-Process Profiling

```bash
# Profile process and children
perf record -g -p <PID> -f -- sleep 60

# System-wide (all processes)
sudo perf record -a -g -- sleep 60
```

## Performance Counters

### List Available Events

```bash
# Show all events
perf list

# CPU cycles
perf stat -e cycles ./cpu_intensive

# Cache misses
perf stat -e cache-misses,cache-references ./cpu_intensive

# Branch mispredictions
perf stat -e branch-misses,branches ./cpu_intensive
```

### Detailed Statistics

```bash
# Comprehensive statistics
perf stat -d ./cpu_intensive

# Output:
# Performance counter stats for './cpu_intensive':
#
#       1,234.56 msec task-clock                #    0.999 CPUs utilized
#              3      context-switches          #    2.429 /sec
#              0      cpu-migrations            #    0.000 /sec
#            543      page-faults               #  439.876 /sec
#  4,567,890,123      cycles                    #    3.699 GHz
#  3,456,789,012      instructions              #    0.76  insn per cycle
#    789,012,345      branches                  #  638.765 M/sec
#     12,345,678      branch-misses             #    1.56% of all branches
#  2,345,678,901      L1-dcache-loads           #    1.899 G/sec
#     23,456,789      L1-dcache-load-misses     #    1.00% of all L1-dcache accesses
```

### Custom Event Profiling

```bash
# Profile cache misses
perf record -e cache-misses -g ./cpu_intensive
perf report --stdio

# Profile branch mispredictions
perf record -e branch-misses -g ./cpu_intensive

# Multiple events
perf record -e cycles,cache-misses -g ./cpu_intensive
```

## Off-CPU Flame Graphs

### Capture Off-CPU Time

```bash
# Requires BCC tools
sudo apt-get install bpfcc-tools

# Off-CPU profiling (shows blocking time)
sudo offcputime-bpfcc -df -p <PID> 60 > offcpu.stacks

# Generate flame graph
flamegraph.pl --color=io --title="Off-CPU Time" offcpu.stacks > offcpu.svg
```

### Interpreting Off-CPU

**Shows time NOT executing**:
- Blocking I/O
- Waiting on locks
- Sleep
- Scheduler delays

**Use case**: Complement to CPU profiling
```
CPU Profile:     Shows where CPU is used
Off-CPU Profile: Shows where waiting happens
```

## Differential Flame Graphs

### Compare Two Profiles

```bash
# Baseline
perf record -F 99 -g -o baseline.data ./app_v1
perf script -i baseline.data > baseline.stacks

# After optimization
perf record -F 99 -g -o optimized.data ./app_v2
perf script -i optimized.data > optimized.stacks

# Generate differential flame graph
difffolded.pl baseline.stacks optimized.stacks | \
    flamegraph.pl --negate > diff.svg
```

### Interpreting Diff Graph

- **Red**: More time in optimized (regression)
- **Blue**: Less time in optimized (improvement)
- **Intensity**: Magnitude of change

## Annotated Source Code

### View Source with Profiling Data

```bash
# Requires debug symbols (-g)
perf annotate --stdio

# Or interactive
perf annotate

# Specific function
perf annotate --symbol=expensive_calculation
```

### Example Annotated Output

```asm
 Percent |      Source code & Disassembly of cpu_intensive
---------+----------------------------------------------
         :      double expensive_calculation(int n) {
    0.00 :        push   %rbp
    0.00 :        mov    %rsp,%rbp
         :          double result = 0.0;
    0.00 :        pxor   %xmm0,%xmm0
         :          for (int i = 0; i < n; i++) {
    0.12 :        xor    %eax,%eax
         :              result += sqrt(i) * log(i + 1);
   45.23 :        cvtsi2sd %eax,%xmm1       ← HOT
   12.34 :        sqrtsd %xmm1,%xmm1        ← HOT
    8.90 :        addsd  %xmm1,%xmm0
```

## Production Profiling

### Low-Overhead Sampling

```bash
# 49 Hz sampling (prime number, avoids aliasing)
perf record -F 49 -a -g -- sleep 60

# Expected overhead: ~1-2%
```

### Continuous Profiling Script

```bash
#!/bin/bash
# continuous_perf_profiling.sh

PROFILE_DIR="/var/log/profiles"
DURATION=300  # 5 minutes
FREQUENCY=49  # Hz

mkdir -p "$PROFILE_DIR"

while true; do
    timestamp=$(date +%Y%m%d_%H%M%S)
    outfile="$PROFILE_DIR/perf_$timestamp"

    echo "Profiling at $timestamp..."

    # System-wide profiling
    perf record -F $FREQUENCY -a -g -o "$outfile.data" -- sleep $DURATION

    # Generate flame graph
    perf script -i "$outfile.data" | \
        stackcollapse-perf.pl | \
        flamegraph.pl > "$outfile.svg"

    # Compress and keep only flame graph
    gzip "$outfile.data"

    # Wait before next profile
    sleep 3600  # 1 hour
done
```

## Troubleshooting

### Issue: "perf not found"

```bash
# Install correct kernel tools
sudo apt-get install linux-tools-$(uname -r)

# Or generic version
sudo apt-get install linux-tools-generic
```

### Issue: "Permission denied" (non-root user)

```bash
# Option 1: Adjust paranoid level (temporary)
sudo sysctl -w kernel.perf_event_paranoid=1

# Option 2: Add capability to perf binary
sudo setcap cap_sys_admin=ep /usr/bin/perf

# Option 3: Use sudo
sudo perf record -a -g -- sleep 60
```

### Issue: Missing symbols in flame graph

```bash
# Ensure debug symbols installed
sudo apt-get install libc6-dbg

# Build with debug symbols
gcc -g -O2 -o app app.c

# Check symbols
nm app | grep expensive_calculation
```

### Issue: Frame pointers missing (incomplete call graphs)

```bash
# Compile with frame pointers
gcc -g -O2 -fno-omit-frame-pointer -o app app.c

# Or use DWARF unwinding
perf record -g --call-graph dwarf ./app
```

## Platform-Specific Notes

### Intel Processors

```bash
# Use LBR for accurate call graphs (low overhead)
perf record -g --call-graph lbr ./app

# Intel VTune integration
amplxe-cl -collect hotspots -result-dir r001hs ./app
```

### ARM Processors

```bash
# ARM-specific events
perf list | grep arm

# ARM CoreSight tracing
perf record -e cs_etm/@tmc_etr0/u ./app
```

## Summary

- **perf**: Universal Linux profiling tool
- **Overhead**: 1-5% (sampling-based)
- **Use Cases**: System-wide profiling, any compiled language
- **Flame Graphs**: Instant visualization of hotspots
- **Production-Safe**: Yes, with appropriate sampling rate
- **Requires**: Debug symbols for meaningful results
