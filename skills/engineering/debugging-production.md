---
name: engineering-debugging-production
description: Comprehensive production debugging practices including live debugging, distributed tracing, memory analysis, core dumps, network debugging, and APM integration with safety-first approach
---

# Production Debugging

**Scope**: Complete production debugging lifecycle from issue detection through resolution, including distributed tracing, live debugging, memory analysis, core dumps, network debugging, database debugging, and APM integration

**Lines**: ~350

**Last Updated**: 2025-10-29

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Debugging live production issues
- Analyzing performance degradation in production
- Investigating memory leaks or resource exhaustion
- Analyzing core dumps from crashed processes
- Tracing requests through distributed systems
- Debugging network connectivity issues
- Analyzing slow database queries
- Integrating APM tools for observability
- Performing non-invasive production diagnostics

Don't use this skill for:
- Local development debugging (see `debugging-local.md`)
- Test environment debugging (see `testing-integration.md`)
- Static code analysis (see `code-quality.md`)
- Security incident response (see `security-incident-response.md`)

---

## Core Concepts

### Concept 1: Safety-First Production Debugging

**Definition**: Debug production systems without causing additional harm or data loss

**Safety Principles**:
```
Minimal Impact:
├─ Read-only operations when possible
├─ Non-invasive monitoring
├─ Short-duration sampling
└─ Automatic safety timeouts

Risk Assessment:
├─ Can this harm customers?
├─ Can this cause data loss?
├─ Can this cause cascading failures?
└─ Is there a safer alternative?

Safety Measures:
├─ Debug replicas, not primaries
├─ Use read replicas for queries
├─ Limit trace sampling rates
└─ Set resource limits on debug tools
```

**Decision Framework**:
```
Need debug data? → Can get from logs/metrics? → YES → Use those
                → Must debug live? → YES → Assess risk
                                         → High risk? → Replicate to staging
                                         → Low risk? → Proceed with limits
```

**Safety Checklist**:
- [ ] Confirmed not debugging primary/leader instance
- [ ] Set resource limits (CPU, memory, time)
- [ ] Verified debug actions are reversible
- [ ] Have rollback plan if issue worsens
- [ ] Documented what you're doing
- [ ] Team aware of debug session

---

### Concept 2: Distributed Tracing

**Definition**: Track requests across multiple services to understand system behavior

**Trace Structure**:
```
Trace (end-to-end request):
├─ Span 1: API Gateway (10ms)
│  ├─ HTTP metadata
│  └─ Tags: service=gateway, method=GET
├─ Span 2: Auth Service (25ms)
│  ├─ Cache hit/miss
│  └─ Tags: service=auth, cache=hit
├─ Span 3: User Service (150ms)
│  ├─ Database query (140ms) ← BOTTLENECK
│  └─ Tags: service=user, db=postgres
└─ Span 4: Response Transform (5ms)
   └─ Tags: service=gateway

Total: 190ms
```

**OpenTelemetry Standard**:
```python
from opentelemetry import trace
from opentelemetry.instrumentation.auto import AutoInstrumentation

# Automatic instrumentation
AutoInstrumentation().instrument()

# Manual spans for custom logic
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_order") as span:
    span.set_attribute("order.id", order_id)
    span.set_attribute("order.total", total)

    result = process_payment(order_id)

    if result.error:
        span.set_status(StatusCode.ERROR)
        span.record_exception(result.error)
```

**Trace Analysis**:
- **Latency**: Identify slow spans (database, external APIs)
- **Errors**: Find where failures occur in chain
- **Dependencies**: Map service relationships
- **Sampling**: Balance observability vs overhead (1-10%)

---

### Concept 3: Memory Debugging

**Definition**: Diagnose memory leaks, excessive allocations, and memory exhaustion

**Memory Issues**:
```
Memory Leak:
├─ Symptoms: Gradual memory growth, eventual OOM
├─ Causes: Unclosed resources, circular references, caches
└─ Detection: Heap snapshots over time

Memory Exhaustion:
├─ Symptoms: Sudden OOM, allocation failures
├─ Causes: Large allocations, memory spikes
└─ Detection: Allocation profiling

Excessive GC:
├─ Symptoms: High CPU, latency spikes
├─ Causes: Too many short-lived objects
└─ Detection: GC logs, pause time metrics
```

**Heap Analysis Workflow**:
```bash
# Python: py-spy for live profiling
py-spy record --pid 12345 --rate 100 --duration 60 --output profile.svg

# Python: memory profiler
memray run --live app.py
memray flamegraph memray-output.bin

# Go: pprof heap profiling
go tool pprof http://localhost:6060/debug/pprof/heap

# Java: heap dump
jmap -dump:live,format=b,file=heap.hprof $PID
jhat heap.hprof  # Or use Eclipse MAT

# Native: valgrind (not for production)
# Native: tcmalloc heap profiler
HEAPPROFILE=/tmp/heap pprof --heap /path/to/binary
```

**Memory Leak Detection**:
1. Take baseline heap snapshot
2. Exercise system (run workload)
3. Force GC (if applicable)
4. Take second snapshot
5. Compare: What grew significantly?
6. Analyze references to leaked objects

---

## Patterns

### Pattern 1: Core Dump Analysis

**Problem**: Process crashed, need to understand why without reproducing

**Core Dump Collection**:
```bash
# Enable core dumps
ulimit -c unlimited

# Set core pattern
echo "/var/crash/core.%e.%p.%t" > /proc/sys/kernel/core_pattern

# With systemd
mkdir -p /var/lib/systemd/coredump
coredumpctl list
coredumpctl info <PID>
coredumpctl dump <PID> > core.dump
```

**Analysis Workflow**:
```bash
# GDB for C/C++
gdb /path/to/binary /path/to/core
(gdb) bt full          # Full backtrace
(gdb) info threads     # All threads
(gdb) thread apply all bt  # Backtrace all threads
(gdb) frame 3          # Switch to frame
(gdb) info locals      # Local variables
(gdb) print variable   # Inspect variable

# Delve for Go
dlv core /path/to/binary /path/to/core
(dlv) goroutines       # List goroutines
(dlv) goroutine 5      # Switch to goroutine
(dlv) bt               # Backtrace
(dlv) locals           # Local variables

# LLDB for Rust/Swift
lldb -c /path/to/core /path/to/binary
(lldb) bt all          # All threads
(lldb) frame variable  # Variables in frame
```

**Common Crash Patterns**:
```
Segmentation Fault:
├─ Null pointer dereference
├─ Buffer overflow
├─ Use after free
└─ Stack overflow

Assertion Failed:
├─ Invariant violated
├─ Unexpected state
└─ Check code at assertion

Signal 6 (SIGABRT):
├─ Explicit abort() call
├─ Failed assertion
└─ Uncaught exception

Signal 11 (SIGSEGV):
├─ Invalid memory access
├─ Stack corruption
└─ Memory unmapped
```

---

### Pattern 2: Network Debugging

**Problem**: Network issues causing timeouts, errors, or data corruption

**Packet Capture**:
```bash
# tcpdump: capture packets
tcpdump -i any -n -s 65535 -w capture.pcap 'host 10.0.1.5 and port 443'

# Filter by service
tcpdump -i eth0 'port 5432'  # PostgreSQL
tcpdump -i eth0 'port 6379'  # Redis

# Capture for limited time
timeout 30 tcpdump -i any -w issue.pcap

# Analyze with Wireshark
wireshark capture.pcap
```

**TLS Debugging**:
```bash
# Capture TLS with keys (must have SSLKEYLOGFILE)
export SSLKEYLOGFILE=/tmp/sslkeys.log
tcpdump -i any -w tls.pcap 'port 443'

# OpenSSL s_client for TLS testing
openssl s_client -connect api.example.com:443 -showcerts

# Test certificate chain
openssl s_client -connect api.example.com:443 -CAfile ca-bundle.crt
```

**HTTP Debugging**:
```bash
# mitmproxy: interactive HTTP proxy
mitmproxy --mode reverse:https://backend:443 --listen-port 8080

# curl with verbose output
curl -v --trace-ascii trace.txt https://api.example.com/endpoint

# Check connection reuse
curl -v --trace-time https://api.example.com/endpoint1
curl -v --trace-time https://api.example.com/endpoint2
```

**Connection Analysis**:
```bash
# netstat: active connections
netstat -antp | grep :8080
ss -antp | grep :8080

# Check connection states
ss -s  # Summary

# TIME_WAIT accumulation
ss -tan state time-wait | wc -l

# Established connections per service
ss -tan state established 'sport = :8080' | wc -l
```

---

### Pattern 3: Live Debugging in Production

**Problem**: Need to inspect running process without stopping it

**Dynamic Tracing**:
```bash
# eBPF tools (Linux)
# Function latency histogram
funclatency -p 12345 'func_name'

# Trace function calls with arguments
trace -p 12345 'func(arg1, arg2)'

# Memory allocations
memleak -p 12345 -t

# strace: system calls (high overhead)
strace -p 12345 -f -t -s 200

# ltrace: library calls
ltrace -p 12345 -f -t
```

**Language-Specific Live Debugging**:
```bash
# Python: py-spy (safe, low overhead)
py-spy top --pid 12345           # Top functions
py-spy dump --pid 12345          # Thread dump
py-spy record --pid 12345        # Flame graph

# Go: pprof endpoints
curl http://localhost:6060/debug/pprof/goroutine?debug=2
curl http://localhost:6060/debug/pprof/profile > cpu.prof
go tool pprof cpu.prof

# Java: JMX and jcmd
jcmd 12345 Thread.print
jcmd 12345 GC.heap_info
jcmd 12345 VM.system_properties

# Node.js: inspector protocol
node --inspect=0.0.0.0:9229 app.js
# Connect with Chrome DevTools
```

**Safety Limits**:
```bash
# Limit CPU impact
nice -n 19 strace -p 12345
taskset -c 0 strace -p 12345  # Pin to one core

# Timeout automatically
timeout 30s py-spy record --pid 12345

# Sample, don't trace everything
py-spy record --rate 50 --pid 12345  # 50 Hz instead of 100
```

---

## Checklist

### Production Debugging Checklist

**Before Starting**:
- [ ] Confirmed issue in production (not just staging artifact)
- [ ] Checked existing logs and metrics first
- [ ] Reviewed recent deployments and changes
- [ ] Assessed impact and urgency
- [ ] Notified team of debug session
- [ ] Selected non-primary instance if possible
- [ ] Have rollback plan if issue worsens

**During Debugging**:
- [ ] Set timeouts on all debug commands
- [ ] Monitor resource usage of debug tools
- [ ] Document findings in real-time
- [ ] Check for customer impact during session
- [ ] Take snapshots/dumps for offline analysis
- [ ] Limit scope (specific service, time window)
- [ ] Use sampling, not full tracing

**After Debugging**:
- [ ] Cleaned up debug tools and processes
- [ ] Disabled trace collection if enabled
- [ ] Removed debug endpoints if added
- [ ] Documented root cause
- [ ] Created postmortem or runbook
- [ ] Shared findings with team
- [ ] Created tickets for permanent fixes

---

## Anti-Patterns

**Safety Anti-Patterns**:
```
❌ Debug primary database → Use read replica
❌ No timeout on debug tools → Can run forever
❌ 100% trace sampling → Overwhelms system
❌ Attach debugger to process → Pauses execution
❌ No resource limits → Debug tool consumes all CPU/memory
❌ Skip team notification → Confusion during incident
```

**Analysis Anti-Patterns**:
```
❌ Change code in production to add logging → Deploy properly
❌ Restart without collecting diagnostics → Lost evidence
❌ Guess without data → Use traces, profiles, dumps
❌ Debug without reproducing → May not be real issue
❌ Focus on code, ignore infrastructure → Check network, disk, etc.
❌ Serial debugging → Use distributed tracing for distributed systems
```

**Tool Anti-Patterns**:
```
❌ Use heavyweight tools in production → Use lightweight alternatives
❌ Leave tracing enabled permanently → Only during investigation
❌ Full heap dumps on large processes → Sample or use live profiling
❌ Blocking debug operations → Use async/sampling approaches
❌ Ignore tool overhead → Monitor impact
```

---

## Recovery

**When Debug Tool Causes Issues**:
```
1. STOP debug tool immediately (kill -9 if needed)
2. CHECK metrics: Did impact reduce?
3. DOCUMENT what was running and parameters
4. ANALYZE collected data offline
5. CHOOSE less invasive tool for retry
```

**When Can't Reproduce Issue**:
```
1. COLLECT more context:
   - Exact timestamps
   - Affected users/requests
   - Environmental conditions (load, time of day)
2. COMPARE with baseline (when working)
3. CHECK for intermittent patterns
4. INCREASE observability (more metrics, logging)
5. CONSIDER chaos engineering to trigger
```

**When Root Cause Unclear**:
```
1. VERIFY assumptions with data
2. ELIMINATE variables one at a time
3. CHECK all layers of stack:
   - Application code
   - Runtime (GC, memory)
   - OS (file descriptors, memory)
   - Network (latency, packet loss)
   - Infrastructure (CPU, disk)
4. CONSULT with specialists
5. REPRODUCE in isolated environment
```

---

## Level 3: Resources

**Extended Documentation**: [REFERENCE.md](debugging-production/resources/REFERENCE.md) (3,500+ lines)
- Production debugging philosophy and safety principles
- Comprehensive distributed tracing guide (OpenTelemetry, Jaeger, Zipkin)
- Memory debugging techniques for all major languages
- Core dump analysis workflows with debugger commands
- Network debugging with packet capture and analysis
- Database debugging and query optimization
- Container and Kubernetes debugging
- APM tool integration guides (Datadog, New Relic, Dynatrace)
- Live debugging tools and techniques
- Performance profiling and flame graphs
- Common production issues and diagnostic approaches
- Safety best practices and risk assessment

**Scripts**: Production-ready tools in `debugging-production/resources/scripts/`
- `analyze_traces.py` (900+ lines): Distributed trace analysis, latency bottleneck identification, error correlation, service dependency mapping with CLI
- `debug_memory.py` (850+ lines): Memory leak detection, heap dump analysis, memory growth trending, GC analysis with comprehensive reporting
- `analyze_coredump.sh` (750+ lines): Core dump collection and analysis, stack trace extraction, symbol resolution, automated report generation

**Examples**: Production-ready examples in `debugging-production/resources/examples/`
- **tracing/**:
  - `opentelemetry-setup.py`: Complete OpenTelemetry setup with auto and manual instrumentation, Jaeger export, sampling configuration
  - `trace-analysis-workflow.md`: End-to-end trace analysis workflow with real examples
- **memory/**:
  - `python-memory-debug.py`: Live Python memory debugging with py-spy and memray
  - `memory-leak-detection.md`: Memory leak detection methodology and tools
- **network/**:
  - `tcpdump-analysis.sh`: Network traffic capture and analysis scripts
  - `tls-debugging-guide.md`: TLS/SSL debugging procedures
- **database/**:
  - `slow-query-analysis.sql`: Database slow query identification and optimization
  - `postgres-debugging.md`: PostgreSQL-specific debugging techniques
- **kubernetes/**:
  - `kubectl-debug-pod.sh`: Kubernetes pod debugging with ephemeral containers
  - `k8s-troubleshooting-guide.md`: Complete Kubernetes debugging workflows
- **apm/**:
  - `datadog-integration.py`: Datadog APM integration with custom metrics
  - `newrelic-setup.py`: New Relic APM setup and configuration
- **runbooks/**:
  - `production-debugging-checklist.md`: Comprehensive debugging checklist and procedures

All scripts include:
- `--help` for comprehensive usage documentation
- `--json` output for programmatic integration
- Executable permissions and proper shebang lines
- Type hints and comprehensive docstrings
- Error handling and validation
- Safety limits and timeout mechanisms
- Example usage demonstrations

**Usage**:
```bash
# Analyze distributed traces
./analyze_traces.py --service api --time-range 1h \
  --latency-threshold 500ms --verbose --json

# Debug memory issues
./debug_memory.py --pid 12345 --duration 60 \
  --detect-leaks --heap-snapshot --output report.json

# Analyze core dump
./analyze_coredump.sh /var/crash/core.app.12345.1234567890 \
  --binary /usr/bin/app --symbols /usr/lib/debug \
  --output analysis.txt

# OpenTelemetry setup
python opentelemetry-setup.py --service my-api --jaeger-endpoint localhost:4318

# Kubernetes pod debugging
./kubectl-debug-pod.sh my-pod my-namespace --collect-logs --network-trace
```

---

## Related Skills

- `monitoring-alerts.md`: Detection and alerting
- `incident-response.md`: Production incident handling
- `observability-metrics.md`: Metrics and dashboards
- `performance-optimization.md`: Performance tuning
- `database-optimization.md`: Database debugging
- `networking-protocols.md`: Network debugging
- `containers-kubernetes.md`: Container debugging
