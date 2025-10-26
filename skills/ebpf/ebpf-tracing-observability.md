---
name: ebpf-tracing-observability
description: Using eBPF for tracing with bpftrace, kprobes, uprobes, tracepoints, and performance analysis
---

# eBPF Tracing and Observability

**Scope**: System tracing with bpftrace, kprobes/uprobes, tracepoints, perf events, and latency analysis patterns
**Lines**: ~360
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Analyzing system performance and latency issues
- Tracing kernel function calls with kprobes
- Tracing user-space function calls with uprobes
- Using bpftrace for ad-hoc system analysis
- Monitoring function call frequencies and durations
- Debugging production issues with minimal overhead
- Collecting stack traces for profiling
- Creating custom observability tools

## Core Concepts

### Concept 1: bpftrace Language

**One-liners**: Quick system insights

```bash
# Trace all syscalls by process
bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'

# Show file opens
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s: %s\n", comm, str(args->filename)); }'

# Measure syscall latency
bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @start[tid] = nsecs; }
              tracepoint:raw_syscalls:sys_exit /@start[tid]/ {
                @ns = hist(nsecs - @start[tid]);
                delete(@start[tid]);
              }'

# Top processes by CPU
bpftrace -e 'profile:hz:99 { @[comm] = count(); }'

# Block I/O size distribution
bpftrace -e 'tracepoint:block:block_rq_issue { @bytes = hist(args->bytes); }'
```

### Concept 2: kprobes and kretprobes

**kprobe**: Trace kernel function entry
**kretprobe**: Trace kernel function exit (return value)

```bash
# bpftrace: Trace function entry
bpftrace -e 'kprobe:do_sys_open { printf("Process %s opening file\n", comm); }'

# Trace function with arguments
bpftrace -e 'kprobe:do_sys_open {
    printf("%s called do_sys_open(dfd=%d, filename=%s)\n",
           comm, arg0, str(arg1));
}'

# Trace function return value
bpftrace -e 'kretprobe:do_sys_open {
    printf("do_sys_open returned: %d\n", retval);
}'

# Measure function duration
bpftrace -e 'kprobe:vfs_read { @start[tid] = nsecs; }
              kretprobe:vfs_read /@start[tid]/ {
                @duration_us = hist((nsecs - @start[tid]) / 1000);
                delete(@start[tid]);
              }'
```

**C program** (libbpf):

```c
#include <vmlinux.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

SEC("kprobe/do_sys_open")
int BPF_KPROBE(trace_open_entry, int dfd, const char __user *filename) {
    char fname[256];
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    char comm[16];

    bpf_get_current_comm(&comm, sizeof(comm));
    bpf_probe_read_user_str(&fname, sizeof(fname), filename);

    bpf_printk("PID %d (%s) opening: %s\n", pid, comm, fname);
    return 0;
}

SEC("kretprobe/do_sys_open")
int BPF_KRETPROBE(trace_open_exit, int ret) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    bpf_printk("PID %d open returned: %d\n", pid, ret);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

### Concept 3: uprobes for User-Space Tracing

**Purpose**: Trace user-space functions (applications, libraries)

```bash
# Trace malloc calls
bpftrace -e 'uprobe:/lib/x86_64-linux-gnu/libc.so.6:malloc {
    printf("%s malloc(%d)\n", comm, arg0);
}'

# Trace application function
bpftrace -e 'uprobe:/usr/bin/python3.9:PyEval_EvalFrameEx {
    printf("Python frame execution in %s\n", comm);
}'

# Trace with return value
bpftrace -e 'uretprobe:/lib/x86_64-linux-gnu/libc.so.6:malloc {
    printf("malloc returned: %p\n", retval);
}'

# Trace custom application
bpftrace -e 'uprobe:./myapp:process_request {
    printf("Request processing started\n");
}
uretprobe:./myapp:process_request {
    printf("Request took: %d ns\n", retval);
}'
```

**C program** (libbpf):

```c
SEC("uprobe/lib/x86_64-linux-gnu/libc.so.6:malloc")
int BPF_KPROBE(trace_malloc, size_t size) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    char comm[16];
    bpf_get_current_comm(&comm, sizeof(comm));

    bpf_printk("PID %d (%s) malloc(%lu)\n", pid, comm, size);
    return 0;
}

SEC("uretprobe/lib/x86_64-linux-gnu/libc.so.6:malloc")
int BPF_KRETPROBE(trace_malloc_ret, void *ret) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    bpf_printk("PID %d malloc returned: %p\n", pid, ret);
    return 0;
}
```

### Concept 4: Tracepoints - Stable ABI

**Advantages**: Stable across kernel versions, no symbol lookup

```bash
# List available tracepoints
bpftrace -l 'tracepoint:*' | grep syscalls

# Trace syscall entry
bpftrace -e 'tracepoint:syscalls:sys_enter_write {
    printf("write(%d, ..., %d)\n", args->fd, args->count);
}'

# Trace scheduler events
bpftrace -e 'tracepoint:sched:sched_switch {
    printf("%s -> %s\n", args->prev_comm, args->next_comm);
}'

# Trace network transmit
bpftrace -e 'tracepoint:net:netif_rx {
    printf("RX %d bytes on %s\n", args->len, args->name);
}'
```

**C program**:

```c
#include <vmlinux.h>
#include <bpf/bpf_helpers.h>

SEC("tracepoint/syscalls/sys_enter_openat")
int trace_openat(struct trace_event_raw_sys_enter *ctx) {
    char filename[256];
    char comm[16];

    bpf_get_current_comm(&comm, sizeof(comm));
    bpf_probe_read_user_str(&filename, sizeof(filename),
                            (void *)ctx->args[1]);

    bpf_printk("%s opening: %s\n", comm, filename);
    return 0;
}

SEC("tracepoint/sched/sched_process_exec")
int trace_exec(struct trace_event_raw_sched_process_exec *ctx) {
    char comm[16];
    bpf_get_current_comm(&comm, sizeof(comm));

    bpf_printk("Exec: %s (PID %d)\n", comm, ctx->pid);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

---

## Patterns

### Pattern 1: Latency Analysis

**When to use**: Identify slow operations

```bash
# Histogram of read() latency
bpftrace -e '
tracepoint:syscalls:sys_enter_read {
    @start[tid] = nsecs;
}

tracepoint:syscalls:sys_exit_read /@start[tid]/ {
    @latency_us = hist((nsecs - @start[tid]) / 1000);
    delete(@start[tid]);
}

interval:s:5 {
    print(@latency_us);
    clear(@latency_us);
}'
```

**C implementation** (more control):

```c
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, u32);
    __type(value, u64);
} start_times SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HISTOGRAM);
    __uint(max_entries, 64);
} latency_hist SEC(".maps");

SEC("tracepoint/syscalls/sys_enter_read")
int trace_read_enter(struct trace_event_raw_sys_enter *ctx) {
    u32 tid = bpf_get_current_pid_tgid() & 0xFFFFFFFF;
    u64 ts = bpf_ktime_get_ns();
    bpf_map_update_elem(&start_times, &tid, &ts, BPF_ANY);
    return 0;
}

SEC("tracepoint/syscalls/sys_exit_read")
int trace_read_exit(struct trace_event_raw_sys_exit *ctx) {
    u32 tid = bpf_get_current_pid_tgid() & 0xFFFFFFFF;
    u64 *tsp = bpf_map_lookup_elem(&start_times, &tid);

    if (tsp) {
        u64 delta_us = (bpf_ktime_get_ns() - *tsp) / 1000;
        bpf_map_update_elem(&latency_hist, &delta_us, NULL, BPF_ANY);
        bpf_map_delete_elem(&start_times, &tid);
    }

    return 0;
}
```

### Pattern 2: Function Counting

**Use case**: Find hot paths in code

```bash
# Count kernel function calls
bpftrace -e 'kprobe:vfs_* { @[probe] = count(); }'

# Count by process
bpftrace -e 'kprobe:tcp_sendmsg { @sends[comm] = count(); }'

# Top 10 callers
bpftrace -e 'kprobe:do_sys_open { @[comm] = count(); }
              interval:s:10 { print(@, 10); clear(@); }'
```

**C program** (per-CPU for performance):

```c
struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_HASH);
    __uint(max_entries, 10240);
    __type(key, char[16]);
    __type(value, u64);
} call_counts SEC(".maps");

SEC("kprobe/tcp_sendmsg")
int count_tcp_send(struct pt_regs *ctx) {
    char comm[16];
    u64 zero = 0, *count;

    bpf_get_current_comm(&comm, sizeof(comm));

    count = bpf_map_lookup_elem(&call_counts, &comm);
    if (count) {
        __sync_fetch_and_add(count, 1);
    } else {
        bpf_map_update_elem(&call_counts, &comm, &zero, BPF_NOEXIST);
    }

    return 0;
}
```

### Pattern 3: Stack Trace Collection

**When to use**: Profiling, identifying code paths

```bash
# User stack traces
bpftrace -e 'profile:hz:99 /comm == "myapp"/ {
    @[ustack] = count();
}'

# Kernel stack traces
bpftrace -e 'kprobe:tcp_sendmsg {
    @[kstack] = count();
}'

# Combined user + kernel stacks
bpftrace -e 'profile:hz:99 {
    @[ustack, kstack, comm] = count();
}'
```

**C program**:

```c
struct {
    __uint(type, BPF_MAP_TYPE_STACK_TRACE);
    __uint(max_entries, 1024);
    __uint(key_size, sizeof(u32));
    __uint(value_size, PERF_MAX_STACK_DEPTH * sizeof(u64));
} stack_traces SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, u32);
    __type(value, u64);
} stack_counts SEC(".maps");

SEC("kprobe/tcp_sendmsg")
int trace_tcp_send(struct pt_regs *ctx) {
    u32 stack_id = bpf_get_stackid(ctx, &stack_traces, BPF_F_USER_STACK);
    u64 *count, zero = 0;

    count = bpf_map_lookup_elem(&stack_counts, &stack_id);
    if (count) {
        __sync_fetch_and_add(count, 1);
    } else {
        bpf_map_update_elem(&stack_counts, &stack_id, &zero, BPF_ANY);
    }

    return 0;
}
```

### Pattern 4: Argument Inspection

**Use case**: Understand function inputs

```bash
# Inspect syscall arguments
bpftrace -e 'tracepoint:syscalls:sys_enter_write {
    printf("write(fd=%d, count=%d) by %s\n",
           args->fd, args->count, comm);
}'

# String arguments
bpftrace -e 'tracepoint:syscalls:sys_enter_execve {
    printf("exec: %s %s\n", comm, str(args->filename));
}'

# Struct arguments (kernel functions)
bpftrace -e 'kprobe:tcp_sendmsg {
    printf("tcp_sendmsg: size=%d\n", ((struct msghdr *)arg1)->msg_iter.count);
}'
```

### Pattern 5: Filtering by PID/Process

**Use case**: Focus on specific application

```bash
# Single PID
bpftrace -e 'tracepoint:syscalls:sys_enter_read /pid == 1234/ {
    printf("Read by PID 1234\n");
}'

# Process name
bpftrace -e 'kprobe:vfs_read /comm == "nginx"/ {
    @reads = count();
}'

# Multiple PIDs
bpftrace -e '
BEGIN { @pids[1234] = 1; @pids[5678] = 1; }

kprobe:do_sys_open /@pids[pid]/ {
    printf("Monitored PID %d opened file\n", pid);
}'
```

**C program**:

```c
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, u32);
    __type(value, u8);
} filter_pids SEC(".maps");

SEC("kprobe/do_sys_open")
int trace_open_filtered(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;

    if (!bpf_map_lookup_elem(&filter_pids, &pid))
        return 0; // Skip if not in filter

    char comm[16];
    bpf_get_current_comm(&comm, sizeof(comm));
    bpf_printk("Filtered PID %d (%s) opening file\n", pid, comm);

    return 0;
}
```

### Pattern 6: Time-Based Sampling

**When to use**: Reduce overhead for high-frequency events

```bash
# Sample 1% of events
bpftrace -e 'kprobe:vfs_read /(rand() % 100) < 1/ {
    @sampled = count();
}'

# Sample every 100th event
bpftrace -e '
kprobe:tcp_sendmsg {
    @count++;
    if (@count % 100 == 0) {
        printf("Sample: %s sent TCP\n", comm);
    }
}'
```

### Pattern 7: Multi-Function Correlation

**Use case**: Track request flow across functions

```bash
bpftrace -e '
kprobe:tcp_sendmsg {
    @start[tid] = nsecs;
    printf("-> tcp_sendmsg (%s)\n", comm);
}

kprobe:ip_queue_xmit /@start[tid]/ {
    printf("  -> ip_queue_xmit (+%d us)\n",
           (nsecs - @start[tid]) / 1000);
}

kretprobe:tcp_sendmsg /@start[tid]/ {
    printf("<- tcp_sendmsg (total: %d us)\n",
           (nsecs - @start[tid]) / 1000);
    delete(@start[tid]);
}'
```

---

## Quick Reference

### bpftrace Probe Types

```
Probe Type           | Syntax                        | Example
---------------------|-------------------------------|---------------------------
Tracepoint           | tracepoint:category:name      | tracepoint:syscalls:sys_enter_read
kprobe               | kprobe:function               | kprobe:do_sys_open
kretprobe            | kretprobe:function            | kretprobe:do_sys_open
uprobe               | uprobe:path:function          | uprobe:/bin/bash:readline
uretprobe            | uretprobe:path:function       | uretprobe:/lib/libc.so:malloc
Software             | software:event:count          | software:page-faults:
Hardware             | hardware:event:count          | hardware:cache-misses:
Profile              | profile:hz:rate               | profile:hz:99
Interval             | interval:s:seconds            | interval:s:5
```

### Common bpftrace Variables

```
Variable  | Description
----------|----------------------------------
pid       | Process ID
tid       | Thread ID
uid       | User ID
comm      | Process name
nsecs     | Nanosecond timestamp
arg0-argN | Function arguments (kprobe/uprobe)
retval    | Return value (kretprobe/uretprobe)
```

### Key Guidelines

```
✅ DO: Use tracepoints for stable production tracing
✅ DO: Sample high-frequency events to reduce overhead
✅ DO: Clean up maps after use (delete)
✅ DO: Use filters to minimize data collection
✅ DO: Test scripts on dev systems first

❌ DON'T: Trace every event without filtering
❌ DON'T: Forget to handle missing entries in maps
❌ DON'T: Use kprobes on unstable kernel internals in production
```

---

## Anti-Patterns

### Critical Violations

```bash
# ❌ NEVER: Trace everything without filtering
bpftrace -e 'kprobe:* { printf("Called: %s\n", probe); }'
# Massive overhead, system slowdown

# ✅ CORRECT: Filter to specific probes
bpftrace -e 'kprobe:vfs_* { @[probe] = count(); }'
```

❌ **Unbounded tracing**: System performance degradation
✅ **Correct approach**: Specific probes with filters

### Common Mistakes

```bash
# ❌ Don't: Forget to clean up maps
bpftrace -e '
kprobe:do_sys_open { @start[tid] = nsecs; }
kretprobe:do_sys_open { /* No delete! */ }'

# ✅ Correct: Always clean up
bpftrace -e '
kprobe:do_sys_open { @start[tid] = nsecs; }
kretprobe:do_sys_open /@start[tid]/ {
    delete(@start[tid]);  # Prevent map growth
}'
```

❌ **Map bloat**: Memory exhaustion over time
✅ **Better**: Delete entries after use

---

## Related Skills

- `ebpf-fundamentals.md` - Core eBPF concepts and verifier
- `ebpf-networking.md` - Packet processing with XDP/TC
- `ebpf-security-monitoring.md` - Security observability
- `performance-tuning.md` - System performance optimization

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
