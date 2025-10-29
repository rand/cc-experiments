# Performance Profiling - Comprehensive Reference

**Last Updated**: 2025-10-29
**Lines**: 3,847

This reference provides comprehensive documentation for performance profiling across languages, tools, and environments.

---

## Table of Contents

1. [Profiling Fundamentals](#1-profiling-fundamentals)
2. [CPU Profiling](#2-cpu-profiling)
3. [Memory Profiling](#3-memory-profiling)
4. [I/O Profiling](#4-io-profiling)
5. [Network Profiling](#5-network-profiling)
6. [Flame Graphs](#6-flame-graphs)
7. [Language-Specific Profiling](#7-language-specific-profiling)
8. [Production Profiling](#8-production-profiling)
9. [Profile-Guided Optimization](#9-profile-guided-optimization)
10. [Bottleneck Identification](#10-bottleneck-identification)
11. [Optimization Strategies](#11-optimization-strategies)
12. [Profiling Anti-Patterns](#12-profiling-anti-patterns)

---

## 1. Profiling Fundamentals

### 1.1 What is Profiling?

Profiling is the dynamic analysis of program execution to measure:
- **Where time is spent** (CPU profiling)
- **Where memory is allocated** (memory profiling)
- **What I/O operations occur** (I/O profiling)
- **Where contention happens** (lock profiling)

### 1.2 Profiling vs Tracing vs Monitoring

| Technique   | Granularity | Overhead | Use Case                          |
|-------------|-------------|----------|-----------------------------------|
| Profiling   | Function    | 1-10%    | Find hotspots, optimize code      |
| Tracing     | Request     | 0.1-1%   | Distributed systems, latency      |
| Monitoring  | Service     | <0.1%    | Alerting, dashboards, trends      |

### 1.3 Sampling vs Instrumentation

**Sampling Profiling**:
- Periodically samples call stack (e.g., every 10ms)
- Low overhead (1-5%)
- Statistical accuracy improves with sample count
- May miss rare but expensive operations
- **Production-safe**

```
Time:     0ms   10ms   20ms   30ms   40ms   50ms
          |      |      |      |      |      |
Sample:   foo -> bar -> foo -> baz -> bar -> foo
```

**Instrumentation Profiling**:
- Records every function entry/exit
- High overhead (10-100%)
- Exact counts and timings
- Captures all operations
- **Development only**

```
Function calls:
foo() entered at 0ms, exited at 15ms
  bar() entered at 5ms, exited at 10ms
baz() entered at 20ms, exited at 50ms
```

**When to use sampling**: Production, low overhead required, statistical data sufficient

**When to use instrumentation**: Development, need exact counts, debugging specific issues

### 1.4 Types of Profiling

**CPU Profiling**: Measures time spent executing code
- Identifies computational hotspots
- Reveals algorithmic inefficiencies
- Shows call graphs and stack traces

**Memory Profiling**: Tracks memory allocation and usage
- Detects memory leaks
- Identifies excessive allocations
- Shows allocation stack traces

**I/O Profiling**: Measures disk and network operations
- Identifies I/O bottlenecks
- Reveals blocking operations
- Shows file access patterns

**Lock Profiling**: Tracks contention on synchronization primitives
- Identifies lock contention
- Reveals serialization bottlenecks
- Shows wait times on locks

**Off-CPU Profiling**: Measures time NOT executing (waiting)
- Complements CPU profiling
- Shows blocking I/O, locks, sleep
- Reveals scheduling issues

### 1.5 Profiling Workflow

```
1. Define Goal
   ↓
2. Establish Baseline
   └─→ Measure current performance
   └─→ Identify target metrics (latency, throughput, memory)
   ↓
3. Profile Application
   └─→ Choose profiling tool
   └─→ Run under representative load
   └─→ Collect profile data
   ↓
4. Analyze Profile
   └─→ Identify hotspots (>5% of time)
   └─→ Understand call graphs
   └─→ Prioritize optimization targets
   ↓
5. Optimize Code
   └─→ Apply optimization techniques
   └─→ One change at a time
   ↓
6. Verify Improvement
   └─→ Re-profile
   └─→ Compare before/after
   └─→ Measure actual performance gain
   ↓
7. Iterate
   └─→ Continue until goal achieved
   └─→ Document optimizations
```

### 1.6 Performance Metrics

**Latency**: Time to complete a single operation
- P50, P95, P99 percentiles
- Measures user experience
- Target: <100ms for interactive, <1s for batch

**Throughput**: Operations per unit time
- Requests/second, transactions/second
- Measures capacity
- Target: Meet peak load + 20% headroom

**Resource Utilization**: CPU, memory, I/O usage
- Efficiency indicator
- Measures cost
- Target: <70% for bursty traffic, <90% steady state

**Scalability**: Performance as load increases
- Linear, sublinear, or superlinear
- Measures architecture fitness
- Target: Near-linear up to max capacity

---

## 2. CPU Profiling

### 2.1 CPU Profiling Basics

CPU profiling identifies where the CPU spends time executing code. It reveals:
- Hot functions (most time-consuming)
- Call graphs (who calls whom)
- Instruction-level bottlenecks

### 2.2 Linux perf

**Installation**:
```bash
# Ubuntu/Debian
sudo apt-get install linux-tools-common linux-tools-generic

# CentOS/RHEL
sudo yum install perf
```

**Basic CPU Profiling**:
```bash
# Record for 60 seconds
perf record -F 99 -a -g -- sleep 60

# Record specific process
perf record -F 99 -p <pid> -g -- sleep 60

# Record specific command
perf record -F 99 -g ./myapp arg1 arg2

# View report
perf report

# Export for flame graph
perf script > out.perf
```

**Sampling Frequency**:
- `-F 99`: 99 Hz (samples per second)
- Higher frequency = more accurate, more overhead
- 99 Hz is common (prime number avoids aliasing)
- Production: 49-99 Hz, Development: 199-999 Hz

**Call Graphs**:
```bash
# Enable call graphs
perf record -g --call-graph dwarf ./myapp

# View annotated call graph
perf report -g 'graph,0.5,caller'
```

**Filtering**:
```bash
# Filter by function name
perf report --comms myapp --symbols foo

# Filter by CPU
perf record -C 0,1 -g -- sleep 60  # CPUs 0 and 1 only

# Filter by event
perf record -e cycles -g ./myapp
perf record -e cache-misses -g ./myapp
```

**Performance Counters**:
```bash
# CPU cycles
perf stat ./myapp

# Cache misses
perf stat -e cache-references,cache-misses ./myapp

# Branch mispredictions
perf stat -e branches,branch-misses ./myapp

# Instruction-level parallelism
perf stat -e instructions,cycles ./myapp
```

### 2.3 Intel VTune Profiler

**Installation**:
```bash
# Download from Intel website
# https://software.intel.com/content/www/us/en/develop/tools/oneapi/components/vtune-profiler.html

# Install
sudo sh vtune_installer.sh
```

**Hotspot Analysis**:
```bash
# Collect hotspot profile
vtune -collect hotspots -result-dir r001hs ./myapp

# View report
vtune -report summary -r r001hs

# View top functions
vtune -report hotspots -r r001hs

# GUI
vtune-gui r001hs
```

**Microarchitecture Analysis**:
```bash
# Collect uarch profile (requires root)
sudo vtune -collect uarch-exploration -result-dir r002ua ./myapp

# Identify bottlenecks
vtune -report summary -r r002ua
```

**Call Graph**:
```bash
# Collect with call stacks
vtune -collect hotspots -knob sampling-mode=hw -knob enable-stack-collection=true ./myapp

# Bottom-up view (callers)
vtune -report bottom-up -r r001hs

# Top-down view (callees)
vtune -report top-down -r r001hs
```

### 2.4 gprof

**Compilation**:
```bash
# Compile with profiling enabled
gcc -pg -O2 -o myapp myapp.c

# Run program (generates gmon.out)
./myapp

# Generate report
gprof myapp gmon.out > analysis.txt
```

**Report Sections**:

**Flat Profile**: Time spent in each function
```
  %   cumulative   self              self     total
 time   seconds   seconds    calls  ms/call  ms/call  name
 33.34      0.02     0.02     7208     0.00     0.00  open
 16.67      0.03     0.01      244     0.04     0.12  offtime
 16.67      0.04     0.01        8     1.25     1.25  memccpy
```

**Call Graph**: Call relationships and time attribution
```
index % time    self  children    called     name
                0.00    0.05       1/1           main [2]
[1]     83.3    0.00    0.05       1         report [1]
                0.00    0.03       8/8           timelocal [4]
                0.00    0.01       1/1           print [9]
```

**Limitations**:
- High overhead (instrumentation-based)
- Requires recompilation
- Inaccurate for multi-threaded programs
- Better alternatives: perf, pprof

### 2.5 Valgrind Callgrind

**Basic Usage**:
```bash
# Profile with callgrind
valgrind --tool=callgrind --callgrind-out-file=callgrind.out ./myapp

# Annotate source with costs
callgrind_annotate callgrind.out source.c

# Visualize with KCachegrind
kcachegrind callgrind.out
```

**Cache Profiling**:
```bash
# Include cache simulation
valgrind --tool=callgrind --cache-sim=yes ./myapp

# I-cache misses (instruction cache)
# D-cache misses (data cache)
# LL-cache misses (last-level cache)
```

**Call Graph**:
```bash
# Collect call graph
valgrind --tool=callgrind --collect-jumps=yes ./myapp

# Call graph format in output
```

**Limitations**:
- Very high overhead (10-100x slowdown)
- Development only, not production
- Deterministic (no sampling)
- Excellent for cache analysis

### 2.6 DTrace (macOS, BSD, Solaris)

**CPU Profiling**:
```bash
# Profile for 10 seconds
sudo dtrace -n 'profile-997 { @[ustack()] = count(); } tick-10s { exit(0); }'

# Profile specific process
sudo dtrace -n 'profile-997 /pid == $target/ { @[ustack()] = count(); }' -p <pid>

# Function call count
sudo dtrace -n 'pid$target:::entry { @[probefunc] = count(); }' -c ./myapp
```

**Flame Graph**:
```bash
# Collect stacks
sudo dtrace -x ustackframes=100 -n 'profile-997 /pid == $target/ { @[ustack()] = count(); } tick-60s { exit(0); }' -p <pid> -o out.stacks

# Generate flame graph
stackcollapse.pl out.stacks | flamegraph.pl > flame.svg
```

### 2.7 Language-Specific CPU Profilers

See [Section 7](#7-language-specific-profiling) for detailed coverage of:
- Python: cProfile, py-spy, Scalene
- Go: pprof
- Node.js: --prof, clinic.js
- Rust: flamegraph, perf
- Java: JFR, async-profiler
- C/C++: perf, gprof, VTune

---

## 3. Memory Profiling

### 3.1 Memory Profiling Basics

Memory profiling tracks:
- **Allocations**: Where memory is allocated
- **Deallocations**: Where memory is freed
- **Leaks**: Memory allocated but never freed
- **Fragmentation**: Memory layout inefficiency
- **Peak usage**: Maximum memory consumption

### 3.2 Valgrind Memcheck

**Memory Leak Detection**:
```bash
# Basic leak check
valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes ./myapp

# Generate suppression file for known leaks
valgrind --leak-check=full --gen-suppressions=all ./myapp 2>&1 | grep -A 5 "insert_a_suppression" > myapp.supp

# Use suppression file
valgrind --leak-check=full --suppressions=myapp.supp ./myapp
```

**Output Interpretation**:
```
HEAP SUMMARY:
    in use at exit: 4,096 bytes in 1 blocks
  total heap usage: 10 allocs, 9 frees, 8,192 bytes allocated

LEAK SUMMARY:
   definitely lost: 4,096 bytes in 1 blocks
   indirectly lost: 0 bytes in 0 blocks
     possibly lost: 0 bytes in 0 blocks
   still reachable: 0 bytes in 0 blocks
```

**Leak Types**:
- **Definitely lost**: Memory leak, no pointers to it
- **Indirectly lost**: Leaked structure with pointers to other leaked memory
- **Possibly lost**: Pointers to middle of blocks
- **Still reachable**: Allocated but not freed, pointer exists

**Memory Errors**:
```bash
# Detect invalid reads/writes
valgrind --tool=memcheck ./myapp

# Common errors detected:
# - Use after free
# - Double free
# - Invalid read/write (buffer overflow)
# - Uninitialized value usage
```

### 3.3 Valgrind Massif

**Heap Profiling**:
```bash
# Profile heap usage over time
valgrind --tool=massif --massif-out-file=massif.out ./myapp

# Visualize with ms_print
ms_print massif.out

# Visualize with massif-visualizer (GUI)
massif-visualizer massif.out
```

**Output**:
```
    KB
19.63^                                                                       #
     |                                                                       #
     |                                                                       #
     |                                                                       #
     |                                                                       #
     |                                                                       #
     |                                                                       #
     |                                                                       #
     |                                                                       #
     |                                                                       #
   0 +----------------------------------------------------------------------->Ki
     0                                                                   113.4

Number   Allocated   Freed   Peak    Snapshot
------   ---------   -----   ----    --------
    1        1,024       0  1,024   [snapshot 0]
   10        8,192   4,096 12,288   [snapshot 5]
   20       20,480  16,384 20,480   [snapshot 10]
```

**Detailed Snapshots**:
```bash
# Take snapshots at intervals
valgrind --tool=massif --time-unit=B --detailed-freq=1 ./myapp

# Snapshot shows allocation tree
# Example:
# 92.31% (18,432B) (heap allocation functions) malloc/new/new[]
#  50.00% (10,000B) 0x400550: main (example.c:10)
#  42.31% (8,432B) 0x400570: foo (example.c:20)
```

### 3.4 heaptrack (Linux)

**Installation**:
```bash
sudo apt-get install heaptrack heaptrack-gui  # Ubuntu
sudo yum install heaptrack heaptrack-gui      # CentOS
```

**Profiling**:
```bash
# Record heap allocations
heaptrack ./myapp arg1 arg2

# Analyze with GUI
heaptrack_gui heaptrack.myapp.12345.gz

# Print summary
heaptrack_print heaptrack.myapp.12345.gz
```

**Output**:
```
MOST CALLS TO ALLOCATION FUNCTIONS
allocations    temporary  leaked  peak  function
      10000        9500     500  500   void* operator new(unsigned long)
        500          50     450  450   void* malloc(size_t)

PEAK MEMORY ALLOCATIONS
peak      leaked  allocations  temporary  function
100.0MB   10.0MB        10000       9500  void* operator new(unsigned long)
```

**Features**:
- Low overhead (~10%)
- Flame graph visualization
- Allocation timeline
- Temporary allocations tracking
- Call tree analysis

### 3.5 Memory Profilers by Language

**Python: memory_profiler**
```bash
pip install memory-profiler

# Profile line-by-line
python -m memory_profiler script.py

# Decorator in code
from memory_profiler import profile

@profile
def my_func():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)
    return a, b
```

**Go: pprof heap profiling**
```go
import _ "net/http/pprof"
import "runtime/pprof"

// Heap profile
f, _ := os.Create("heap.prof")
pprof.WriteHeapProfile(f)
f.Close()

// Analyze
// go tool pprof heap.prof
```

**Node.js: heapdump**
```javascript
const heapdump = require('heapdump');

// Take snapshot
heapdump.writeSnapshot('/tmp/' + Date.now() + '.heapsnapshot');

// Load in Chrome DevTools > Memory > Load
```

**Rust: heaptrack or valgrind**
```bash
# heaptrack
heaptrack ./target/release/myapp

# valgrind
valgrind --tool=massif ./target/release/myapp
```

**Java: JFR heap profiling**
```bash
java -XX:StartFlightRecording=settings=profile,filename=recording.jfr MyApp

# Analyze with JDK Mission Control
jmc recording.jfr
```

### 3.6 Memory Leak Detection Strategies

**Automated Detection**:
1. **Run under Valgrind**: Catches definite leaks
2. **Monitor RSS over time**: Steady growth indicates leak
3. **Heap profiling**: Compare snapshots before/after operation
4. **ASAN (AddressSanitizer)**: Compile-time instrumentation

**Manual Analysis**:
1. **Identify suspect code**: Recent changes, complex ownership
2. **Add allocation tracking**: Log alloc/free pairs
3. **Stress test**: Run operation in loop, monitor memory
4. **Diff heap snapshots**: Before/after to find leak source

**Prevention**:
- Use RAII (Resource Acquisition Is Initialization)
- Smart pointers (C++: unique_ptr, shared_ptr)
- Garbage-collected languages (Go, Java, Python)
- Static analysis tools (clang-tidy, cppcheck)

---

## 4. I/O Profiling

### 4.1 I/O Profiling Basics

I/O profiling identifies:
- **Disk I/O**: File reads, writes, seeks
- **Network I/O**: Socket operations, latency
- **Blocking operations**: Synchronous I/O stalls
- **I/O patterns**: Sequential vs random access

### 4.2 iotop

**Real-Time I/O Monitoring**:
```bash
# Monitor all processes
sudo iotop

# Monitor specific process
sudo iotop -p <pid>

# Batch mode (non-interactive)
sudo iotop -b -n 5 -d 1  # 5 iterations, 1 second apart

# Show accumulated I/O
sudo iotop -a
```

**Output**:
```
Total DISK READ: 8.15 M/s | Total DISK WRITE: 23.45 M/s
  TID  PRIO  USER     DISK READ  DISK WRITE  SWAPIN     IO>    COMMAND
 1234  be/4  user       8.15 M/s   23.45 M/s  0.00 % 15.23 % myapp arg1
```

### 4.3 iostat

**Disk Statistics**:
```bash
# Basic disk stats
iostat -x 1 10  # Extended stats, 1 second interval, 10 iterations

# Specific devices
iostat -x sda 1

# Show megabytes instead of blocks
iostat -xm 1
```

**Output**:
```
Device  r/s   w/s   rMB/s  wMB/s  await  %util
sda    12.3  45.6    1.2    5.4   10.2   45.0
```

**Key Metrics**:
- **r/s, w/s**: Reads/writes per second
- **rMB/s, wMB/s**: Throughput in MB/s
- **await**: Average wait time (ms)
- **%util**: Device utilization (>80% = saturated)

### 4.4 strace

**System Call Tracing**:
```bash
# Trace all system calls
strace ./myapp

# Trace specific system calls
strace -e open,read,write ./myapp

# Count calls and time
strace -c ./myapp

# Attach to running process
strace -p <pid>

# Trace file operations
strace -e trace=file ./myapp

# Trace network operations
strace -e trace=network ./myapp

# Output to file
strace -o trace.log ./myapp
```

**Summary Output** (`-c`):
```
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 54.32    0.005432          10       543           read
 23.45    0.002345           5       469           write
 12.34    0.001234          12       103           open
 10.00    0.001000           1      1000           stat
------ ----------- ----------- --------- --------- ----------------
100.00    0.010011                  2115           total
```

**Performance Impact**:
- Very high overhead (10-100x slowdown)
- Development/debugging only
- Alternative: eBPF for production

### 4.5 eBPF I/O Tracing (BCC Tools)

**Installation**:
```bash
# Ubuntu
sudo apt-get install bpfcc-tools linux-headers-$(uname -r)

# CentOS
sudo yum install bcc-tools kernel-devel-$(uname -r)
```

**biosnoop**: Trace block I/O
```bash
sudo biosnoop-bpfcc
# TIME(s)    COMM           PID    DISK    T  SECTOR    BYTES   LAT(ms)
# 0.000000   myapp         1234   sda     R  12345678  4096      2.34
```

**opensnoop**: Trace file opens
```bash
sudo opensnoop-bpfcc
# PID    COMM           FD ERR PATH
# 1234   myapp          3   0   /etc/config.json
```

**filetop**: File I/O by process
```bash
sudo filetop-bpfcc
# TID    COMM           READS  WRITES R_Kb    W_Kb    T FILE
# 1234   myapp          100    50     400     200     R /var/log/app.log
```

**ext4slower**: Trace slow ext4 operations
```bash
sudo ext4slower-bpfcc 10  # Operations >10ms
# TIME     COMM           PID    T BYTES   OFF_KB   LAT(ms) FILENAME
# 12:34:56 myapp         1234   R 4096    0        12.34   data.bin
```

**Low Overhead**: <1% typically, safe for production

### 4.6 lsof

**List Open Files**:
```bash
# All open files by process
lsof -p <pid>

# Network connections
lsof -i -p <pid>

# Specific file
lsof /path/to/file

# All files in directory
lsof +D /path/to/dir

# TCP connections
lsof -i TCP -p <pid>

# UDP connections
lsof -i UDP -p <pid>
```

**Output**:
```
COMMAND  PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
myapp   1234 user  cwd    DIR    8,1     4096  256 /home/user
myapp   1234 user  txt    REG    8,1    12345  789 /usr/bin/myapp
myapp   1234 user    3r   REG    8,1    98765 1024 /var/data/input.dat
myapp   1234 user    4w   REG    8,1        0 2048 /var/log/app.log
myapp   1234 user    5u  IPv4  12345      0t0  TCP *:8080 (LISTEN)
```

**Use Cases**:
- Find which process has file open
- Identify file descriptor leaks
- Monitor network connections
- Troubleshoot "file in use" errors

### 4.7 I/O Pattern Analysis

**Sequential vs Random**:
```bash
# Use blktrace for detailed I/O patterns
sudo blktrace -d /dev/sda -o - | blkparse -i -

# Analyze with btt (Block Trace Toolkit)
sudo blktrace -d /dev/sda -w 60
sudo blkparse sda.blktrace.* -o sda.parse
btt -i sda.parse
```

**Identifying Bottlenecks**:
1. **High await in iostat**: Disk saturated or slow
2. **Many small I/O operations**: Need batching
3. **High %util**: Need more IOPS or caching
4. **Random access pattern**: Consider SSD or redesign

**Optimization Strategies**:
- **Buffering**: Batch small operations
- **Caching**: Reduce redundant reads
- **Async I/O**: Overlap computation and I/O
- **Sequential access**: Improve locality
- **SSD**: Reduce random access penalty

---

## 5. Network Profiling

### 5.1 Network Profiling Basics

Network profiling measures:
- **Latency**: Time for request/response
- **Bandwidth**: Data transfer rate
- **Connection overhead**: Setup/teardown cost
- **Packet loss**: Reliability issues

### 5.2 tcpdump

**Basic Packet Capture**:
```bash
# Capture on interface
sudo tcpdump -i eth0

# Capture specific port
sudo tcpdump -i eth0 port 80

# Capture to file
sudo tcpdump -i eth0 -w capture.pcap

# Read from file
tcpdump -r capture.pcap

# Filter by host
sudo tcpdump -i eth0 host 192.168.1.100

# HTTP traffic
sudo tcpdump -i eth0 'tcp port 80'

# Show packet contents (hex)
sudo tcpdump -i eth0 -X

# Show packet contents (ASCII)
sudo tcpdump -i eth0 -A
```

**Filters**:
```bash
# Combinations
sudo tcpdump -i eth0 'host 192.168.1.100 and port 443'

# Exclude traffic
sudo tcpdump -i eth0 'not port 22'

# TCP flags
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-syn != 0'
```

### 5.3 Wireshark

**Command-Line (tshark)**:
```bash
# Capture
tshark -i eth0 -w capture.pcapng

# Read and filter
tshark -r capture.pcapng -Y "http.request"

# Statistics
tshark -r capture.pcapng -q -z io,phs

# Extract HTTP objects
tshark -r capture.pcapng --export-objects http,/tmp/objects
```

**GUI Analysis**:
1. Capture packets
2. Apply display filters: `tcp.stream eq 0`
3. Follow TCP stream: Analyze → Follow → TCP Stream
4. Statistics: Statistics → Protocol Hierarchy
5. I/O graph: Statistics → I/O Graph

### 5.4 netstat / ss

**Connection Statistics**:
```bash
# Active connections
netstat -an

# Listening sockets
netstat -ln

# Statistics by protocol
netstat -s

# Continuous monitoring
netstat -c

# Process information
sudo netstat -tulpn

# Modern alternative: ss
ss -tuln      # TCP/UDP listening
ss -s         # Summary
ss -o state established  # Established connections with timers
```

### 5.5 iftop

**Real-Time Bandwidth Monitoring**:
```bash
# Monitor interface
sudo iftop -i eth0

# Show ports
sudo iftop -i eth0 -P

# No DNS resolution
sudo iftop -i eth0 -n

# Text mode (non-interactive)
sudo iftop -i eth0 -t
```

**Output**:
```
192.168.1.100:443  => 10.0.0.50:54321    1.2Mb  800Kb  600Kb
192.168.1.100:443  <= 10.0.0.50:54321    100Kb  80Kb   60Kb
```

### 5.6 Network Latency Profiling

**ping**:
```bash
# Basic latency
ping -c 10 example.com

# Flood ping (high rate)
sudo ping -f -c 1000 example.com

# Specific packet size
ping -s 1400 -c 10 example.com
```

**mtr**: Continuous traceroute
```bash
# Interactive mode
mtr example.com

# Report mode
mtr -r -c 100 example.com

# Output
# Host                Loss%   Snt   Last   Avg  Best  Wrst
# 1. gateway           0.0%   100    1.2   1.5   1.0   5.0
# 2. isp-router        0.0%   100    8.5   9.2   7.5  15.0
# 3. example.com       0.0%   100   12.3  13.1  11.0  20.0
```

**hping3**: Advanced packet crafting
```bash
# TCP SYN to port 80
sudo hping3 -S -p 80 -c 10 example.com

# Measure TCP handshake time
sudo hping3 -S -p 80 example.com
```

### 5.7 Application-Level Network Profiling

**HTTP(S) with curl**:
```bash
# Timing breakdown
curl -w "@curl-format.txt" -o /dev/null -s https://example.com

# curl-format.txt:
#     time_namelookup:  %{time_namelookup}s
#        time_connect:  %{time_connect}s
#     time_appconnect:  %{time_appconnect}s
#    time_pretransfer:  %{time_pretransfer}s
#       time_redirect:  %{time_redirect}s
#  time_starttransfer:  %{time_starttransfer}s
#                     ----------
#          time_total:  %{time_total}s
```

**HTTP benchmarking**:
```bash
# Apache Bench
ab -n 1000 -c 10 http://example.com/

# wrk
wrk -t12 -c400 -d30s http://example.com/

# vegeta
echo "GET http://example.com/" | vegeta attack -duration=30s | vegeta report
```

---

## 6. Flame Graphs

### 6.1 Flame Graph Basics

**What is a Flame Graph?**
A visualization of profiled software, showing:
- **X-axis**: Alphabetical order (NOT time)
- **Y-axis**: Stack depth (call chain)
- **Width**: Proportion of samples (time spent)
- **Color**: Typically random or by module

**Advantages**:
- Visualize entire profile at once
- Identify hotspots immediately
- Understand call hierarchies
- Compare profiles with differential flame graphs

### 6.2 Generating Flame Graphs

**Linux perf**:
```bash
# Install FlameGraph tools
git clone https://github.com/brendangregg/FlameGraph.git

# Record profile
perf record -F 99 -a -g -- sleep 60

# Generate flame graph
perf script | ./FlameGraph/stackcollapse-perf.pl | ./FlameGraph/flamegraph.pl > flame.svg

# Open in browser
firefox flame.svg
```

**py-spy (Python)**:
```bash
# Direct flame graph generation
py-spy record -o profile.svg --format flamegraph -- python script.py

# From running process
py-spy record -o profile.svg --format flamegraph -p <pid> --duration 60
```

**pprof (Go)**:
```bash
# HTTP server with flame graph
go tool pprof -http=:8080 cpu.prof

# Static flame graph
go tool pprof -output=flame.svg -svg cpu.prof
```

**cargo-flamegraph (Rust)**:
```bash
cargo install flamegraph

# Profile and generate
cargo flamegraph --bin myapp
```

**async-profiler (Java)**:
```bash
./profiler.sh -d 60 -f flamegraph.html <pid>
```

### 6.3 Reading Flame Graphs

**Anatomy**:
```
[  main  ][   worker_thread   ][   io_thread  ]
   [foo]      [process_data]       [read_file]
  [bar]     [parse] [compute]       [syscall]
[baz][qux]   [A][B]  [C][D]           [read]
```

**Interpreting Patterns**:

**Wide Plateaus** = Hot functions
```
[===========================================]  <- 90% of time in this function
```

**Tall Stacks** = Deep call chains
```
[main]
  [a]
    [b]
      [c]
        [d]
          [e]  <- Deep recursion or layering
```

**Many Narrow Spikes** = Diverse workload
```
[a][b][c][d][e][f][g][h][i][j]  <- No single hotspot
```

**Tower** = Single code path dominating
```
[main]
  [foo]  <- 99% of time in one path
    [bar]
      [baz]
```

### 6.4 Differential Flame Graphs

**Purpose**: Compare two profiles to identify changes

**Generation**:
```bash
# Collect before profile
perf record -F 99 -g -o before.data -- ./app
perf script -i before.data > before.stacks

# Collect after profile
perf record -F 99 -g -o after.data -- ./app
perf script -i after.data > after.stacks

# Generate differential flame graph
./FlameGraph/difffolded.pl before.stacks after.stacks | ./FlameGraph/flamegraph.pl > diff.svg
```

**Interpretation**:
- **Red**: More time in after profile (regression)
- **Blue**: Less time in after profile (improvement)
- **Intensity**: Magnitude of change

**Use Cases**:
- Verify optimization effectiveness
- Identify regressions in code changes
- A/B test performance

### 6.5 Off-CPU Flame Graphs

**Purpose**: Show where threads are blocked (NOT executing)

**Generation**:
```bash
# Collect off-CPU profile with perf
perf record -e sched:sched_switch -e sched:sched_stat_sleep \
  -e sched:sched_stat_blocked -e sched:sched_process_exit \
  -a -g -o offcpu.data sleep 60

# Generate flame graph
perf script -i offcpu.data | ./FlameGraph/stackcollapse-perf.pl | \
  ./FlameGraph/flamegraph.pl --color=io --title="Off-CPU Time" > offcpu.svg
```

**Interpretation**:
- Shows blocking I/O, locks, sleep
- Complements CPU flame graphs
- Identifies serialization bottlenecks

### 6.6 Interactive Flame Graphs

**Speedscope**:
```bash
# Install
npm install -g speedscope

# Profile with py-spy
py-spy record -o profile.speedscope --format speedscope -- python script.py

# Open in speedscope
speedscope profile.speedscope
```

**Features**:
- Time-ordered view (left-to-right is chronological)
- Left-heavy view (traditional flame graph)
- Sandwich view (callers and callees)
- Search functionality
- Zoom and pan

**Firefox Profiler**:
```bash
# Profile Firefox itself
# Open about:profiling
# Start profiling, perform actions, stop
# Analyze in https://profiler.firefox.com
```

---

## 7. Language-Specific Profiling

### 7.1 Python Profiling

**cProfile (Built-in)**:
```python
import cProfile
import pstats

# Profile function
cProfile.run('my_function()', 'profile.stats')

# Analyze
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative')
p.print_stats(20)  # Top 20 functions

# Programmatic profiling
import cProfile
profiler = cProfile.Profile()
profiler.enable()
# Code to profile
result = my_function()
profiler.disable()
profiler.print_stats(sort='cumulative')
```

**Output**:
```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    5.234    5.234 script.py:10(main)
     1000    2.345    0.002    4.123    0.004 module.py:45(process)
   100000    1.234    0.000    1.234    0.000 {built-in method builtins.sum}
```

**py-spy (Sampling)**:
```bash
# Record flame graph
py-spy record -o profile.svg --format flamegraph -- python script.py

# Record speedscope format
py-spy record -o profile.speedscope --format speedscope -- python script.py

# Top-like display for running process
py-spy top --pid 12345

# Subprocesses
py-spy record --subprocesses -o profile.svg -- python script.py
```

**Scalene (CPU + Memory + GPU)**:
```bash
pip install scalene

# Profile script
scalene script.py

# Output HTML report
scalene --html --outfile profile.html script.py

# Profile specific lines
scalene --profile-interval 0.01 script.py
```

**Output**:
```
script.py: % of time =  100.00% out of   5.23s.
       ╷       ╷       ╷       ╷       ╷
  Line │Time   │Memory │       │       │[script.py]
       │Python │Python │       │       │
     1 │       │       │       │       │import numpy as np
    10 │45.2%  │       │       │       │def process(data):
    11 │       │       │       │       │    # Hot loop
    12 │54.8%  │ 12.3MB│       │       │    result = np.sum(data ** 2)
    13 │       │       │       │       │    return result
```

**line_profiler (Line-by-line)**:
```bash
pip install line_profiler

# Decorate function
@profile
def my_function():
    ...

# Run profiler
kernprof -l -v script.py
```

**memory_profiler (Memory)**:
```bash
pip install memory_profiler

# Decorate function
@profile
def my_function():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)
    return a, b

# Run
python -m memory_profiler script.py
```

**Output**:
```
Line #    Mem usage    Increment  Occurences   Line Contents
============================================================
     1   38.816 MiB   38.816 MiB           1   @profile
     2                                         def my_function():
     3   46.492 MiB    7.676 MiB           1       a = [1] * (10 ** 6)
     4  198.977 MiB  152.484 MiB           1       b = [2] * (2 * 10 ** 7)
     5  198.977 MiB    0.000 MiB           1       return a, b
```

### 7.2 Go Profiling

**pprof (Built-in)**:

**HTTP Server**:
```go
import (
    _ "net/http/pprof"
    "net/http"
)

func main() {
    go func() {
        http.ListenAndServe("localhost:6060", nil)
    }()
    // ... rest of application
}

// Access profiles:
// http://localhost:6060/debug/pprof/
// http://localhost:6060/debug/pprof/profile?seconds=30
// http://localhost:6060/debug/pprof/heap
```

**Programmatic CPU Profiling**:
```go
import (
    "os"
    "runtime/pprof"
)

func main() {
    f, _ := os.Create("cpu.prof")
    pprof.StartCPUProfile(f)
    defer pprof.StopCPUProfile()

    // ... code to profile
}

// Analyze
// go tool pprof cpu.prof
```

**Memory Profiling**:
```go
import (
    "os"
    "runtime"
    "runtime/pprof"
)

func main() {
    // ... code to profile

    f, _ := os.Create("mem.prof")
    runtime.GC()  // Force GC before snapshot
    pprof.WriteHeapProfile(f)
    f.Close()
}

// Analyze
// go tool pprof mem.prof
```

**Benchmark Profiling**:
```bash
# CPU profile
go test -cpuprofile cpu.prof -bench .

# Memory profile
go test -memprofile mem.prof -bench .

# Block profile (contention)
go test -blockprofile block.prof -bench .

# Analyze
go tool pprof cpu.prof
```

**pprof Commands**:
```
(pprof) top
(pprof) top10
(pprof) list FunctionName
(pprof) web
(pprof) svg > profile.svg
(pprof) pdf > profile.pdf
```

**HTTP Interface**:
```bash
# Interactive web UI
go tool pprof -http=:8080 cpu.prof

# Fetch from running server
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30
```

### 7.3 Node.js Profiling

**Built-in Profiler**:
```bash
# V8 profiler
node --prof script.js

# Process log file
node --prof-process isolate-0x*.log > processed.txt

# Output shows hot functions
```

**Inspector Protocol**:
```bash
# Start with inspector
node --inspect script.js

# Or attach to running process
node --inspect-brk script.js  # Break at start

# Open Chrome DevTools
# chrome://inspect
# Click "inspect" on target
# Go to Profiler tab, record CPU profile
```

**clinic.js Suite**:
```bash
npm install -g clinic

# Doctor: Overall health check
clinic doctor -- node script.js

# Flame: CPU profiling with flame graph
clinic flame -- node script.js

# Bubbleprof: Async operations
clinic bubbleprof -- node script.js

# Heap profiler
clinic heapprofiler -- node script.js
```

**0x (Flame graphs)**:
```bash
npm install -g 0x

# Profile and generate flame graph
0x script.js

# With arguments
0x -- node script.js arg1 arg2

# Opens HTML flame graph in browser
```

**v8-profiler-next (Programmatic)**:
```javascript
const profiler = require('v8-profiler-next');
const fs = require('fs');

// CPU profile
profiler.startProfiling('CPU profile');
// ... code to profile
const profile = profiler.stopProfiling();
profile.export()
  .pipe(fs.createWriteStream('profile.cpuprofile'))
  .on('finish', () => profile.delete());

// Load in Chrome DevTools > Profiler > Load
```

**Memory Profiling**:
```javascript
const heapdump = require('heapdump');

// Take heap snapshot
heapdump.writeSnapshot(`./heapdump-${Date.now()}.heapsnapshot`);

// Load in Chrome DevTools > Memory > Load
```

### 7.4 Rust Profiling

**cargo-flamegraph**:
```bash
cargo install flamegraph

# Profile binary
cargo flamegraph --bin myapp

# With custom arguments
cargo flamegraph --bin myapp -- arg1 arg2

# Specific feature
cargo flamegraph --features "feature1"

# Opens flamegraph in browser
```

**perf (Linux)**:
```bash
# Build with debug symbols
cargo build --release

# Profile
perf record -g ./target/release/myapp

# Report
perf report

# Flame graph
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg
```

**Valgrind Callgrind**:
```bash
cargo build --release

valgrind --tool=callgrind --callgrind-out-file=callgrind.out \
  ./target/release/myapp

kcachegrind callgrind.out
```

**Criterion (Benchmarking)**:
```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn fibonacci(n: u64) -> u64 {
    match n {
        0 => 1,
        1 => 1,
        n => fibonacci(n-1) + fibonacci(n-2),
    }
}

fn criterion_benchmark(c: &mut Criterion) {
    c.bench_function("fib 20", |b| b.iter(|| fibonacci(black_box(20))));
}

criterion_group!(benches, criterion_benchmark);
criterion_main!(benches);
```

```bash
cargo bench

# HTML reports in target/criterion/
```

**Memory Profiling**:
```bash
# heaptrack
heaptrack ./target/release/myapp

# Valgrind massif
valgrind --tool=massif ./target/release/myapp
ms_print massif.out.*
```

### 7.5 Java Profiling

**Java Flight Recorder (JFR)**:
```bash
# Start with JFR enabled
java -XX:StartFlightRecording=duration=60s,filename=recording.jfr MyApp

# Or trigger on running JVM
jcmd <pid> JFR.start duration=60s filename=recording.jfr

# Dump recording
jcmd <pid> JFR.dump filename=recording.jfr

# Analyze with JDK Mission Control
jmc recording.jfr
```

**async-profiler**:
```bash
# Download from https://github.com/jvm-profiling-tools/async-profiler

# CPU profiling with flame graph
./profiler.sh -d 60 -f flamegraph.html <pid>

# Allocation profiling
./profiler.sh -d 60 -e alloc -f flamegraph.html <pid>

# Lock profiling
./profiler.sh -d 60 -e lock -f flamegraph.html <pid>

# Convert to JFR format
./profiler.sh -d 60 -o jfr -f recording.jfr <pid>
```

**VisualVM**:
```bash
# Install
# Download from https://visualvm.github.io/

# Run
visualvm

# Attach to running JVM
# Tools > Plugins > Install "VisualVM-Profiler"
# Connect to local/remote JVM
# Profiler tab > CPU or Memory
```

**JProfiler**:
Commercial profiler with:
- CPU profiling (sampling and instrumentation)
- Memory profiling with allocation tracking
- Thread profiling
- JDBC profiling
- JEE profiling

**YourKit**:
Commercial profiler with:
- Low overhead sampling
- Call counting and tracing
- Memory leak detection
- CPU and memory profiling

### 7.6 C/C++ Profiling

**perf (Linux)**:
```bash
# Compile with debug symbols
gcc -g -O2 -o myapp myapp.c

# Profile
perf record -g ./myapp

# Report
perf report

# Annotated source
perf annotate

# Flame graph
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg
```

**gprof**:
```bash
# Compile with profiling
gcc -pg -O2 -o myapp myapp.c

# Run (generates gmon.out)
./myapp

# Generate report
gprof myapp gmon.out > analysis.txt
```

**Valgrind Callgrind**:
```bash
valgrind --tool=callgrind --callgrind-out-file=callgrind.out ./myapp

callgrind_annotate callgrind.out

kcachegrind callgrind.out
```

**Intel VTune**:
```bash
# Hotspot analysis
vtune -collect hotspots -result-dir r001hs ./myapp

# Report
vtune -report summary -r r001hs

# GUI
vtune-gui r001hs
```

**Google Performance Tools (gperftools)**:
```bash
# Install
sudo apt-get install google-perftools libgoogle-perftools-dev

# Link with library
gcc -O2 -o myapp myapp.c -lprofiler

# Profile
CPUPROFILE=myapp.prof ./myapp

# Analyze
pprof --text myapp myapp.prof
pprof --gv myapp myapp.prof  # Graphical
```

**AddressSanitizer (Memory errors)**:
```bash
# Compile with ASan
gcc -fsanitize=address -g -O1 -o myapp myapp.c

# Run (detects memory errors)
./myapp
```

**Memory Profiling**:
```bash
# Valgrind memcheck
valgrind --leak-check=full ./myapp

# heaptrack
heaptrack ./myapp
heaptrack_gui heaptrack.myapp.*.gz

# massif
valgrind --tool=massif ./myapp
ms_print massif.out.*
```

---

## 8. Production Profiling

### 8.1 Production Profiling Requirements

**Low Overhead**: <5% performance impact
**Always-On**: Continuous profiling, not manual
**Safe**: No crashes, data corruption, or security issues
**Efficient Storage**: Profile data doesn't overwhelm storage
**Privacy**: No sensitive data in profiles

### 8.2 Continuous Profiling Systems

**Pyroscope (Open Source)**:

**Installation**:
```bash
# Docker
docker run -d -p 4040:4040 pyroscope/pyroscope:latest

# Kubernetes
helm repo add pyroscope-io https://pyroscope-io.github.io/helm-chart
helm install pyroscope pyroscope-io/pyroscope
```

**Instrumentation**:

Python:
```python
import pyroscope

pyroscope.configure(
    application_name="myapp",
    server_address="http://pyroscope:4040",
)

# Code runs with automatic profiling
```

Go:
```go
import "github.com/pyroscope-io/client/pyroscope"

pyroscope.Start(pyroscope.Config{
    ApplicationName: "myapp",
    ServerAddress:   "http://pyroscope:4040",
})
```

Node.js:
```javascript
const Pyroscope = require('@pyroscope/nodejs');

Pyroscope.init({
  serverAddress: 'http://pyroscope:4040',
  appName: 'myapp'
});
Pyroscope.start();
```

**Features**:
- Tag-based filtering (region, version, etc.)
- Diff view for A/B testing
- Flame graph visualization
- Historical data retention

**Parca (eBPF-based)**:

**Installation**:
```bash
# Kubernetes
kubectl apply -f https://github.com/parca-dev/parca/releases/latest/download/kubernetes-manifest.yaml

# Binary
curl -sL https://github.com/parca-dev/parca/releases/latest/download/parca_Linux_x86_64.tar.gz | tar xvfz -
./parca
```

**Features**:
- Zero instrumentation (eBPF)
- Works with any language
- Very low overhead (<1%)
- Kernel and user space profiling
- Flame graphs and icicle graphs

**Google Cloud Profiler**:

```python
import googlecloudprofiler

googlecloudprofiler.start(
    service='myapp',
    service_version='1.0.0',
    verbose=3,
)
```

**Features**:
- Managed service
- Support for Python, Go, Node.js, Java
- Integration with Cloud Monitoring
- Historical data analysis

**Datadog Continuous Profiler**:

```python
from ddtrace.profiling import Profiler

prof = Profiler()
prof.start()
```

**Features**:
- Integrated with APM
- Code hotspots
- Flame graphs
- Profiling + traces correlation

### 8.3 Sampling-Based Production Profiling

**py-spy (Python)**:
```bash
# Profile production process
py-spy record -o profile.svg --format flamegraph -p <pid> --duration 60

# Non-invasive, no code changes
# Safe for production
```

**perf (Linux)**:
```bash
# System-wide profiling
sudo perf record -F 99 -a -g -- sleep 60

# Specific process
sudo perf record -F 99 -p <pid> -g -- sleep 60

# Low overhead (~1-2%)
```

**pprof (Go)**:
```go
import _ "net/http/pprof"

// Expose HTTP endpoint
// http://localhost:6060/debug/pprof/

// Fetch profile remotely
// go tool pprof http://production-server:6060/debug/pprof/profile?seconds=30
```

### 8.4 Adaptive Profiling

**Concept**: Enable profiling automatically when anomalies detected

**Implementation**:
```python
import time
import pyroscope

def adaptive_profiler(latency_threshold=1.0):
    """Enable profiling when latency exceeds threshold"""

    profiling_active = False

    while True:
        latency = measure_latency()

        if latency > latency_threshold and not profiling_active:
            print(f"High latency detected: {latency}s, enabling profiling")
            pyroscope.tag_wrapper({"anomaly": "high_latency"}, lambda: None)
            profiling_active = True
        elif latency <= latency_threshold and profiling_active:
            print("Latency normalized, disabling extra profiling")
            profiling_active = False

        time.sleep(10)
```

**Triggers**:
- High latency (P95 > threshold)
- High CPU utilization
- Memory usage spike
- Error rate increase

### 8.5 Production Profiling Best Practices

**1. Always Use Sampling**: Instrumentation too expensive
**2. Low Sampling Rate**: 10-100 Hz in production
**3. Time-Box Profiling**: Limit to 30-60 seconds
**4. Tag Profiles**: Add metadata (version, region, etc.)
**5. Store Aggregated Data**: Not every sample
**6. Alert on Overhead**: Monitor profiler CPU usage
**7. Security**: Sanitize profiles, no PII
**8. Correlate with Metrics**: Link profiles to anomalies

### 8.6 Production Profiling Overhead

| Tool               | Overhead | Safe for Prod? | Notes                     |
|--------------------|----------|----------------|---------------------------|
| perf (sampling)    | 1-2%     | Yes            | Linux only, low overhead  |
| py-spy             | 1-3%     | Yes            | Python only               |
| pprof (Go)         | <1%      | Yes            | Sampling mode             |
| Pyroscope          | 2-5%     | Yes            | Always-on continuous      |
| Parca (eBPF)       | <1%      | Yes            | Any language, eBPF        |
| JFR                | 1-2%     | Yes            | Java only                 |
| async-profiler     | 1-5%     | Yes            | Java, native sampling     |
| Valgrind           | 10-100x  | No             | Development only          |
| cProfile           | 5-20%    | Marginal       | Python, instrumentation   |

---

## 9. Profile-Guided Optimization

### 9.1 PGO Basics

**Profile-Guided Optimization (PGO)**: Compiler uses runtime profile data to optimize code

**Benefits**:
- 10-30% performance improvement typical
- Better inlining decisions
- Improved branch prediction
- Optimized instruction cache layout
- Dead code elimination

**Process**:
1. Compile with instrumentation
2. Run with representative workload
3. Collect profile data
4. Recompile with profile data

### 9.2 PGO with GCC

**Step 1: Instrumented Build**:
```bash
gcc -fprofile-generate -O2 -o myapp myapp.c
```

**Step 2: Training Run**:
```bash
./myapp < typical_input.txt
# Generates *.gcda files
```

**Step 3: Optimized Build**:
```bash
gcc -fprofile-use -O2 -o myapp myapp.c
```

**Multi-Stage**:
```bash
# Collect multiple profiles
./myapp < input1.txt
./myapp < input2.txt
./myapp < input3.txt

# Merge profiles
gcov-tool merge -o merged.profdata *.gcda

# Build with merged profile
gcc -fprofile-use=merged.profdata -O2 -o myapp myapp.c
```

### 9.3 PGO with Clang/LLVM

**Step 1: Instrumented Build**:
```bash
clang -fprofile-instr-generate -O2 -o myapp myapp.c
```

**Step 2: Training Run**:
```bash
LLVM_PROFILE_FILE="myapp.profraw" ./myapp < typical_input.txt
```

**Step 3: Convert Profile**:
```bash
llvm-profdata merge -output=myapp.profdata myapp.profraw
```

**Step 4: Optimized Build**:
```bash
clang -fprofile-instr-use=myapp.profdata -O2 -o myapp myapp.c
```

### 9.4 PGO with Rust

**Step 1: Instrumented Build**:
```bash
RUSTFLAGS="-Cprofile-generate=/tmp/pgo-data" \
  cargo build --release
```

**Step 2: Training Run**:
```bash
./target/release/myapp < typical_workload.txt
```

**Step 3: Merge Profiles**:
```bash
llvm-profdata merge -o /tmp/pgo-data/merged.profdata /tmp/pgo-data/*.profraw
```

**Step 4: Optimized Build**:
```bash
RUSTFLAGS="-Cprofile-use=/tmp/pgo-data/merged.profdata -Cllvm-args=-pgo-warn-missing-function" \
  cargo build --release
```

### 9.5 PGO with Go

Go's PGO is newer (Go 1.20+)

**Step 1: Default Build**:
```bash
go build -o myapp main.go
```

**Step 2: Collect CPU Profile**:
```bash
./myapp -cpuprofile=default.pgo
```

**Step 3: PGO Build**:
```bash
# Go looks for default.pgo automatically
go build -o myapp main.go

# Or specify profile
go build -pgo=custom.pgo -o myapp main.go
```

### 9.6 PGO Best Practices

**Representative Workload**:
- Use production-like data
- Cover common code paths
- Include edge cases sparingly
- Multiple training runs better

**Profile Staleness**:
- Regenerate profiles regularly
- Code changes invalidate profiles
- Automate PGO in CI/CD

**Validation**:
- Benchmark before/after PGO
- Verify correctness (PGO can introduce bugs)
- Test on production-like hardware

**Diminishing Returns**:
- First PGO: 10-30% improvement
- Subsequent optimizations: <5% each
- Focus on algorithmic improvements first

---

## 10. Bottleneck Identification

### 10.1 Amdahl's Law

**Formula**:
```
Speedup = 1 / ((1 - P) + P/S)

P = Proportion of code that is parallelizable
S = Speedup of the parallelized portion
```

**Example**:
- Program is 75% parallelizable (P = 0.75)
- Parallelized portion is 4x faster (S = 4)
- Overall speedup: 1 / ((1 - 0.75) + 0.75/4) = 1 / 0.4375 = 2.29x

**Insight**:
- Serial portion limits total speedup
- Optimize the slowest part first
- Parallelization has diminishing returns

### 10.2 Critical Path Analysis

**Process**:
1. Profile end-to-end operation
2. Identify functions consuming >5% of time
3. Build call graph of hot functions
4. Trace critical path (slowest sequence)
5. Optimize critical path first

**Example**:
```
main() [100%]
├─ load_data() [10%]
├─ process_data() [70%]  ← CRITICAL PATH
│  ├─ parse() [20%]
│  ├─ compute() [45%]  ← HOTSPOT
│  └─ validate() [5%]
└─ save_results() [20%]
```

**Optimization Priority**:
1. `compute()` - 45% of time
2. `process_data()` - overhead
3. `save_results()` - 20%
4. `parse()` - 20%

### 10.3 Roofline Model

**Purpose**: Identify if bottleneck is CPU or memory bandwidth

**Axes**:
- X: Operational intensity (FLOPs per byte)
- Y: Performance (GFLOPs/s)

**Regions**:
- **Memory-bound**: Limited by DRAM bandwidth
- **Compute-bound**: Limited by CPU throughput

**Analysis**:
```
If operational intensity < machine balance point:
    Bottleneck is memory bandwidth
    → Optimize data access patterns, cache locality
Else:
    Bottleneck is compute
    → Optimize algorithm, vectorization
```

### 10.4 80/20 Rule (Pareto Principle)

**Observation**: 80% of execution time in 20% of code

**Strategy**:
1. Profile entire application
2. Identify top 20% of functions by time
3. Focus optimization efforts there
4. Ignore functions <5% of time

**Example Profile**:
```
Function       Time    Cumulative
---------      ----    ----------
compute()      45%     45%   ← Focus here
parse()        20%     65%   ← Focus here
save()         15%     80%   ← Focus here
validate()      8%     88%   ← Marginal
load()          5%     93%   ← Ignore
misc()          7%    100%   ← Ignore
```

### 10.5 Common Bottleneck Patterns

**CPU-Bound**:
- Hot loops with O(n²) complexity
- Lack of caching/memoization
- Inefficient algorithms
- Serialization/deserialization

**Memory-Bound**:
- Cache misses (poor locality)
- Large data structures
- Memory allocations in hot path
- GC pressure

**I/O-Bound**:
- Synchronous I/O in hot path
- Small I/O operations (not batched)
- Network round-trips in loops
- Unbuffered I/O

**Concurrency-Bound**:
- Lock contention
- False sharing
- Over-synchronization
- Thread pool exhaustion

### 10.6 Profiling-Driven Optimization Workflow

```
1. Profile
   ├─ Identify hotspots (>5% time)
   └─ Measure baseline performance

2. Hypothesize
   ├─ Algorithmic issue? (O(n²) → O(n log n))
   ├─ Memory issue? (allocations, cache misses)
   ├─ I/O issue? (blocking, batching)
   └─ Concurrency issue? (locks, contention)

3. Optimize
   ├─ Apply one change at a time
   └─ Document change

4. Verify
   ├─ Re-profile
   ├─ Compare flame graphs
   └─ Measure performance gain

5. Iterate
   ├─ If goal not met, go to step 2
   └─ If goal met, document and commit
```

---

## 11. Optimization Strategies

### 11.1 Algorithmic Optimization

**Replace Inefficient Algorithms**:

```python
# Before: O(n²)
def find_duplicates(arr):
    result = []
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            if arr[i] == arr[j]:
                result.append(arr[i])
    return result

# After: O(n)
def find_duplicates(arr):
    seen = set()
    duplicates = set()
    for item in arr:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return list(duplicates)
```

**Impact**: 100x speedup for large inputs

### 11.2 Caching and Memoization

**Memoization**:
```python
from functools import lru_cache

# Before: Exponential time
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# After: Linear time
@lru_cache(maxsize=None)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

**Caching External Resources**:
```python
import functools
import time

@functools.lru_cache(maxsize=128)
def fetch_user(user_id):
    # Expensive database query or API call
    return database.query(f"SELECT * FROM users WHERE id = {user_id}")

# First call: slow
user = fetch_user(123)  # 50ms

# Subsequent calls: instant
user = fetch_user(123)  # <1ms
```

### 11.3 Reduce Memory Allocations

**Object Pooling**:
```python
# Before: Allocate on every call
def process_data(data):
    buffer = bytearray(1024)  # Allocation
    # ... process with buffer
    return result

# After: Reuse buffer
_buffer_pool = [bytearray(1024) for _ in range(10)]

def process_data(data):
    buffer = _buffer_pool.pop()  # Reuse
    try:
        # ... process with buffer
        return result
    finally:
        _buffer_pool.append(buffer)  # Return to pool
```

**Preallocate**:
```python
# Before: Append grows list
result = []
for item in data:
    result.append(process(item))

# After: Preallocate size
result = [None] * len(data)
for i, item in enumerate(data):
    result[i] = process(item)
```

### 11.4 Batching Operations

**Batch I/O**:
```python
# Before: Many small writes
for record in records:
    file.write(record)  # 1000 syscalls

# After: Buffer and batch
buffer = []
for record in records:
    buffer.append(record)
    if len(buffer) >= 100:
        file.writelines(buffer)  # 10 syscalls
        buffer.clear()
if buffer:
    file.writelines(buffer)
```

**Batch Network Requests**:
```python
# Before: N+1 query problem
users = db.query("SELECT * FROM users")
for user in users:
    orders = db.query(f"SELECT * FROM orders WHERE user_id = {user.id}")
    # ... process orders
# Total: 1 + N queries

# After: Batch with JOIN or IN clause
users = db.query("SELECT * FROM users")
user_ids = [user.id for user in users]
orders = db.query(f"SELECT * FROM orders WHERE user_id IN ({','.join(map(str, user_ids))})")
orders_by_user = defaultdict(list)
for order in orders:
    orders_by_user[order.user_id].append(order)
# Total: 2 queries
```

### 11.5 Lazy Evaluation

```python
# Before: Eager evaluation
def process_all(data):
    step1 = [transform1(x) for x in data]
    step2 = [transform2(x) for x in step1]
    step3 = [transform3(x) for x in step2]
    return step3

# After: Lazy with generators
def process_all(data):
    step1 = (transform1(x) for x in data)
    step2 = (transform2(x) for x in step1)
    step3 = (transform3(x) for x in step2)
    return step3  # No work done yet

# Work happens on iteration
for result in process_all(data):
    # Transforms applied on-demand
    ...
```

### 11.6 Concurrency and Parallelism

**Threading for I/O-bound**:
```python
import concurrent.futures

# Before: Sequential I/O
results = []
for url in urls:
    results.append(fetch_url(url))  # Total: N * latency

# After: Parallel I/O
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(fetch_url, urls))  # Total: ~max(latencies)
```

**Multiprocessing for CPU-bound**:
```python
import multiprocessing

# Before: Single-threaded
results = [expensive_computation(x) for x in data]

# After: Multiprocess
with multiprocessing.Pool() as pool:
    results = pool.map(expensive_computation, data)
```

### 11.7 SIMD and Vectorization

**NumPy (uses SIMD)**:
```python
import numpy as np

# Before: Python loop (slow)
result = []
for i in range(len(a)):
    result.append(a[i] * b[i] + c[i])

# After: NumPy vectorized (fast, uses SIMD)
result = a * b + c
```

**Auto-vectorization**:
```c
// Compiler can auto-vectorize with -O3 -march=native
void add_arrays(float *a, float *b, float *c, int n) {
    for (int i = 0; i < n; i++) {
        c[i] = a[i] + b[i];
    }
}

// Compiled to AVX instructions on x86-64
```

### 11.8 Async I/O

**Python asyncio**:
```python
import asyncio
import aiohttp

# Before: Synchronous
def fetch_all(urls):
    results = []
    for url in urls:
        response = requests.get(url)  # Blocks
        results.append(response.text)
    return results

# After: Asynchronous
async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_one(session, url) for url in urls]
        return await asyncio.gather(*tasks)

async def fetch_one(session, url):
    async with session.get(url) as response:
        return await response.text()
```

### 11.9 Data-Oriented Design

**Structure of Arrays (SoA) vs Array of Structures (AoS)**:

```c
// Array of Structures (AoS): Poor cache locality
struct Particle {
    float x, y, z;    // Position
    float vx, vy, vz; // Velocity
};
Particle particles[1000];

// Update positions (cache unfriendly)
for (int i = 0; i < 1000; i++) {
    particles[i].x += particles[i].vx;
    particles[i].y += particles[i].vy;
    particles[i].z += particles[i].vz;
}

// Structure of Arrays (SoA): Better cache locality
struct Particles {
    float x[1000], y[1000], z[1000];
    float vx[1000], vy[1000], vz[1000];
};
Particles particles;

// Update positions (cache friendly)
for (int i = 0; i < 1000; i++) {
    particles.x[i] += particles.vx[i];
    particles.y[i] += particles.vy[i];
    particles.z[i] += particles.vz[i];
}
```

**Benefits**: 2-4x speedup from improved cache utilization

### 11.10 Branch Prediction Optimization

**Avoid Unpredictable Branches**:
```c
// Before: Unpredictable branch
int sum = 0;
for (int i = 0; i < n; i++) {
    if (arr[i] > threshold) {  // Unpredictable
        sum += arr[i];
    }
}

// After: Branchless
int sum = 0;
for (int i = 0; i < n; i++) {
    sum += arr[i] * (arr[i] > threshold);  // No branch
}
```

**Sort for Better Prediction**:
```c
// If data is sorted, branch predictor performs well
std::sort(arr.begin(), arr.end());
for (int i = 0; i < n; i++) {
    if (arr[i] > threshold) {  // Predictable after sorting
        sum += arr[i];
    }
}
```

---

## 12. Profiling Anti-Patterns

### 12.1 Premature Optimization

**Anti-Pattern**:
```python
# Optimizing without profiling
def process_data(data):
    # Using complex optimization without evidence of need
    return numpy.array(data, dtype=np.float32).sum()
```

**Correct Approach**:
```python
# 1. Profile first
# 2. Identify bottleneck
# 3. Then optimize

# Simple first
def process_data(data):
    return sum(data)

# Profile reveals this is slow? Then optimize
```

**Quote**: "Premature optimization is the root of all evil" - Donald Knuth

### 12.2 Profiling Debug Builds

**Anti-Pattern**:
```bash
# Profiling debug build
gcc -g -O0 -o myapp myapp.c
perf record ./myapp
```

**Correct Approach**:
```bash
# Profile release build with debug symbols
gcc -g -O2 -o myapp myapp.c
perf record ./myapp
```

**Why**: Debug builds have no optimization, results don't reflect production

### 12.3 Single Sample

**Anti-Pattern**:
```bash
# One sample
perf record -g ./myapp
```

**Correct Approach**:
```bash
# Multiple samples to account for variance
for i in {1..5}; do
    perf record -g -o perf-$i.data ./myapp
done

# Analyze variance
```

**Why**: Single sample can be unrepresentative due to variance

### 12.4 Ignoring Amdahl's Law

**Anti-Pattern**:
```python
# Optimizing 1% of runtime
def rarely_called():  # Called once, takes 0.1s
    # Spend hours optimizing this
    ...

# Ignoring hot path
def frequently_called():  # Called 1M times, takes 50s total
    # No optimization
    ...
```

**Correct Approach**:
- Profile first
- Optimize functions >5% of runtime
- Focus on hot path

### 12.5 High Overhead in Production

**Anti-Pattern**:
```bash
# Running Valgrind in production (100x slowdown)
valgrind --tool=callgrind production-app
```

**Correct Approach**:
```bash
# Low overhead profiler
perf record -F 99 -p $(pgrep production-app) -g -- sleep 60
```

**Why**: High overhead affects behavior and user experience

### 12.6 Profiling Without Load

**Anti-Pattern**:
```bash
# Profiling with no realistic load
./myapp test_input.txt
```

**Correct Approach**:
```bash
# Profile under realistic load
./load_generator &  # Simulates production traffic
perf record -p $(pgrep myapp) -g -- sleep 60
```

**Why**: Bottlenecks differ under load (concurrency, caching, etc.)

### 12.7 Not Verifying Optimizations

**Anti-Pattern**:
```python
# Optimize without measurement
def optimized_version(data):
    # "This should be faster"
    return result
```

**Correct Approach**:
```python
# Benchmark before and after
import timeit

before = timeit.timeit(lambda: original_version(data), number=1000)
after = timeit.timeit(lambda: optimized_version(data), number=1000)

print(f"Speedup: {before/after:.2f}x")
```

**Why**: Assumptions can be wrong, always measure

### 12.8 Micro-Optimizations

**Anti-Pattern**:
```python
# Obsessing over micro-optimizations
# Replacing `i += 1` with `i = i + 1`
# Using `--i` instead of `i--`
```

**Correct Approach**:
- Focus on algorithmic improvements (O(n²) → O(n log n))
- Optimize data structures (list → set for lookups)
- Profile-driven optimization

**Why**: Micro-optimizations have negligible impact, waste time

### 12.9 Optimizing for Wrong Metric

**Anti-Pattern**:
```python
# Optimizing CPU when memory is the bottleneck
def process(data):
    # Fast algorithm but allocates 10GB
    ...
```

**Correct Approach**:
- Profile all dimensions (CPU, memory, I/O)
- Optimize the actual bottleneck
- Consider trade-offs

**Why**: Optimizing wrong dimension doesn't help

### 12.10 Profiling Without Commit

**Anti-Pattern**:
```bash
# Profile uncommitted code
# Make changes
# Profile again
# Can't compare because code changed
```

**Correct Approach**:
```bash
# Commit baseline
git add . && git commit -m "Baseline before optimization"

# Profile baseline
perf record -g -o baseline.data ./myapp

# Optimize
# ...

# Commit optimization
git add . && git commit -m "Optimize function X"

# Profile optimized
perf record -g -o optimized.data ./myapp

# Compare profiles
```

**Why**: Need stable baseline for comparison

---

## Conclusion

Performance profiling is essential for:
- **Identifying bottlenecks**: Where time/memory is spent
- **Guiding optimization**: Data-driven decisions
- **Verifying improvements**: Measure before/after
- **Continuous monitoring**: Always-on production profiling

**Key Takeaways**:
1. **Profile before optimizing**: Measure, don't guess
2. **Use right tool**: Sampling for production, instrumentation for development
3. **Focus on hotspots**: Optimize 20% that takes 80% of time
4. **Low overhead**: <5% in production
5. **Verify improvements**: Benchmark before/after

**Tools Summary**:
- **Linux**: perf, BCC/eBPF
- **Python**: py-spy, cProfile, Scalene
- **Go**: pprof
- **Node.js**: clinic.js, --prof
- **Rust**: flamegraph, perf
- **Java**: JFR, async-profiler
- **C/C++**: perf, Valgrind, VTune

**Continuous Profiling**: Pyroscope, Parca, Google Cloud Profiler

**Resources**:
- [Brendan Gregg's Blog](http://www.brendangregg.com/)
- [FlameGraph Repository](https://github.com/brendangregg/FlameGraph)
- [Systems Performance](http://www.brendangregg.com/systems-performance-2nd-edition-book.html)

---

**End of Reference Document**
