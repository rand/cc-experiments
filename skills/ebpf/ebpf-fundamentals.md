---
name: ebpf-fundamentals
description: eBPF basics including program types, verifier, maps, BCC vs libbpf toolchains, and loading programs
---

# eBPF Fundamentals

**Scope**: Core eBPF concepts, program types, verifier constraints, maps, toolchain selection, and program lifecycle
**Lines**: ~320
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Starting new eBPF projects for tracing, networking, or security
- Understanding eBPF verifier requirements and constraints
- Choosing between BCC and libbpf toolchains
- Working with eBPF maps for data sharing
- Loading and attaching eBPF programs to kernel hooks
- Debugging verifier rejection errors
- Designing safe kernel-space programs
- Implementing custom observability or filtering logic

## Core Concepts

### Concept 1: eBPF vs Traditional BPF

**Classic BPF**: Packet filtering only, limited instruction set
**eBPF**: Extended functionality, multiple program types, maps, helper functions

**Evolution**:
- Classic BPF: tcpdump filters (1990s)
- eBPF: Kernel 3.18+ (2014), full programming model
- Modern: JIT compilation, verifier, safety guarantees

**Architecture**:
```
User Space Program
      ↓
  bpf() syscall
      ↓
 eBPF Verifier (safety check)
      ↓
  JIT Compiler
      ↓
Kernel Execution (kprobe, XDP, tracepoint, etc.)
```

### Concept 2: Program Types

**Common types**:

```c
// Kprobe: Trace kernel function entry
SEC("kprobe/sys_execve")
int trace_execve(struct pt_regs *ctx) {
    char comm[16];
    bpf_get_current_comm(&comm, sizeof(comm));
    bpf_printk("Process: %s\n", comm);
    return 0;
}

// XDP: Fast packet processing
SEC("xdp")
int xdp_drop_icmp(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (eth->h_proto == htons(ETH_P_IP)) {
        struct iphdr *ip = (void *)(eth + 1);
        if ((void *)(ip + 1) > data_end)
            return XDP_PASS;

        if (ip->protocol == IPPROTO_ICMP)
            return XDP_DROP; // Drop ICMP packets
    }

    return XDP_PASS;
}

// Tracepoint: Stable kernel ABI
SEC("tracepoint/syscalls/sys_enter_open")
int trace_open(struct trace_event_raw_sys_enter *ctx) {
    char filename[256];
    bpf_probe_read_user_str(&filename, sizeof(filename),
                            (void *)ctx->args[0]);
    bpf_printk("Opening: %s\n", filename);
    return 0;
}
```

**Program type table**:
```
Type          | Hook Point              | Use Case
--------------|-------------------------|---------------------------
kprobe        | Kernel function entry   | Tracing, monitoring
kretprobe     | Kernel function exit    | Return value inspection
tracepoint    | Stable kernel events    | Production tracing
XDP           | Network driver RX       | Fast packet filtering
TC            | Traffic control         | Packet modification
socket_filter | Socket-level filtering  | Per-socket inspection
cgroup/skb    | cgroup network events   | Container networking
```

### Concept 3: eBPF Verifier

**Safety guarantees**:
- No infinite loops (bounded loops only)
- No unbounded memory access
- No uninitialized reads
- Complexity limit (~1 million instructions verified)

```c
// ❌ REJECTED: Unbounded loop
for (int i = 0; i < n; i++) { // n from packet - verifier rejects
    // ...
}

// ✅ ACCEPTED: Bounded loop
#pragma unroll
for (int i = 0; i < 10; i++) { // Fixed bound
    // ...
}

// ❌ REJECTED: Uninitialized read
int value;
bpf_printk("%d", value); // value not initialized

// ✅ ACCEPTED: Initialized first
int value = 0;
bpf_printk("%d", value);

// ❌ REJECTED: Unbounded pointer access
char *ptr = get_user_pointer();
char c = *ptr; // Verifier can't prove bounds

// ✅ ACCEPTED: Bounds checking
char *ptr = get_user_pointer();
char buf[256];
bpf_probe_read(&buf, sizeof(buf), ptr); // Safe helper
```

### Concept 4: Maps - Data Sharing

**Map types**:
- Hash: Key-value storage
- Array: Fixed-size indexed array
- Perf buffer: Async event streaming to userspace
- Ring buffer: Newer, more efficient event streaming
- LRU Hash: Automatic eviction
- Stack/Queue: FIFO/LIFO structures

```c
// Define map in eBPF program
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, u32);    // PID
    __type(value, u64);  // Timestamp
} start_times SEC(".maps");

// Write to map
SEC("kprobe/sys_enter_read")
int trace_read_entry(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 ts = bpf_ktime_get_ns();

    bpf_map_update_elem(&start_times, &pid, &ts, BPF_ANY);
    return 0;
}

// Read from map
SEC("kretprobe/sys_exit_read")
int trace_read_exit(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 *tsp = bpf_map_lookup_elem(&start_times, &pid);

    if (tsp) {
        u64 delta = bpf_ktime_get_ns() - *tsp;
        bpf_printk("PID %d read took %llu ns\n", pid, delta);
        bpf_map_delete_elem(&start_times, &pid);
    }

    return 0;
}
```

---

## Patterns

### Pattern 1: BCC vs libbpf Toolchain Choice

**BCC (BPF Compiler Collection)**:
```python
# Quick prototyping with Python
from bcc import BPF

program = """
#include <uapi/linux/ptrace.h>

int trace_open(struct pt_regs *ctx) {
    bpf_trace_printk("open() called\\n");
    return 0;
}
"""

b = BPF(text=program)
b.attach_kprobe(event="do_sys_open", fn_name="trace_open")
b.trace_print()
```

**libbpf (CO-RE - Compile Once, Run Everywhere)**:
```c
// Modern approach - portable binaries
#include <vmlinux.h>
#include <bpf/bpf_helpers.h>

SEC("kprobe/do_sys_open")
int BPF_KPROBE(trace_open, int dfd, const char __user *filename) {
    char fname[256];
    bpf_probe_read_user_str(&fname, sizeof(fname), filename);
    bpf_printk("Opening: %s\n", fname);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

**When to use**:
- BCC: Prototyping, one-off tools, dynamic programs
- libbpf: Production, portable binaries, performance-critical

### Pattern 2: Ring Buffer for Events

**Use case**: Efficient event streaming to userspace

```c
// eBPF program
struct event {
    u32 pid;
    char comm[16];
    char filename[256];
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} events SEC(".maps");

SEC("kprobe/do_sys_open")
int trace_open(struct pt_regs *ctx) {
    struct event *e;

    e = bpf_ringbuf_reserve(&events, sizeof(*e), 0);
    if (!e)
        return 0;

    e->pid = bpf_get_current_pid_tgid() >> 32;
    bpf_get_current_comm(&e->comm, sizeof(e->comm));
    bpf_probe_read_user_str(&e->filename, sizeof(e->filename),
                            (void *)PT_REGS_PARM2(ctx));

    bpf_ringbuf_submit(e, 0);
    return 0;
}
```

```c
// Userspace consumer (C)
#include <bpf/libbpf.h>

int handle_event(void *ctx, void *data, size_t data_sz) {
    struct event *e = data;
    printf("PID %d (%s) opened: %s\n", e->pid, e->comm, e->filename);
    return 0;
}

int main() {
    struct ring_buffer *rb;
    struct bpf_object *obj;
    struct bpf_map *map;

    obj = bpf_object__open_file("program.bpf.o", NULL);
    bpf_object__load(obj);

    map = bpf_object__find_map_by_name(obj, "events");
    rb = ring_buffer__new(bpf_map__fd(map), handle_event, NULL, NULL);

    while (1) {
        ring_buffer__poll(rb, 100); // Poll every 100ms
    }

    return 0;
}
```

### Pattern 3: Filtering with Maps

**When to use**: Dynamic filtering controlled from userspace

```c
// Allowlist map
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, u32);    // PID
    __type(value, u8);   // Dummy value
} allowlist SEC(".maps");

SEC("kprobe/sys_execve")
int trace_execve(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;

    // Only trace allowed PIDs
    if (!bpf_map_lookup_elem(&allowlist, &pid))
        return 0;

    char comm[16];
    bpf_get_current_comm(&comm, sizeof(comm));
    bpf_printk("Allowed PID %d: %s\n", pid, comm);

    return 0;
}
```

```python
# Userspace control (Python with BCC)
from bcc import BPF

b = BPF(src_file="filter.bpf.c")
allowlist = b["allowlist"]

# Add PIDs to allowlist
allowlist[c_uint(1234)] = c_ubyte(1)
allowlist[c_uint(5678)] = c_ubyte(1)

# Remove PID
del allowlist[c_uint(1234)]
```

### Pattern 4: Aggregation with Per-CPU Maps

**Use case**: High-performance counters

```c
struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 256);
    __type(key, u32);
    __type(value, u64);
} syscall_counts SEC(".maps");

SEC("tracepoint/raw_syscalls/sys_enter")
int count_syscalls(struct trace_event_raw_sys_enter *ctx) {
    u32 syscall_id = ctx->id;
    u64 *count;

    count = bpf_map_lookup_elem(&syscall_counts, &syscall_id);
    if (count)
        __sync_fetch_and_add(count, 1); // Atomic increment

    return 0;
}
```

```c
// Userspace aggregation
int fd = bpf_map__fd(map);
__u32 key = 0;
__u64 values[num_cpus];

for (key = 0; key < 256; key++) {
    if (bpf_map_lookup_elem(fd, &key, values) == 0) {
        __u64 total = 0;
        for (int i = 0; i < num_cpus; i++)
            total += values[i];

        if (total > 0)
            printf("Syscall %d: %llu calls\n", key, total);
    }
}
```

### Pattern 5: Handling Verifier Errors

**Use case**: Debugging complex programs

```bash
# Load with verbose verifier output
bpftool prog load program.o /sys/fs/bpf/myprog type kprobe

# Common errors and fixes:

# Error: "back-edge from insn X to Y"
# Fix: Use #pragma unroll or reduce loop bound

# Error: "R1 invalid mem access"
# Fix: Add bounds checking before pointer dereference

# Error: "unreachable insn X"
# Fix: Remove dead code or ensure all paths are reachable

# Error: "program too large"
# Fix: Split into multiple programs or simplify logic
```

### Pattern 6: Helper Function Usage

**Common helpers**:

```c
// Get current process info
u32 pid = bpf_get_current_pid_tgid() >> 32;
u32 tid = bpf_get_current_pid_tgid() & 0xFFFFFFFF;
u64 uid = bpf_get_current_uid_gid() >> 32;

char comm[16];
bpf_get_current_comm(&comm, sizeof(comm));

// Time
u64 ns = bpf_ktime_get_ns();

// Kernel memory (safe)
struct task_struct *task = (struct task_struct *)bpf_get_current_task();
u32 ppid;
bpf_probe_read_kernel(&ppid, sizeof(ppid), &task->real_parent->tgid);

// User memory (safe)
char user_buf[256];
bpf_probe_read_user(&user_buf, sizeof(user_buf), user_ptr);

// Output
bpf_printk("Debug: %s %d\n", comm, pid);

// Tail calls (program chaining)
bpf_tail_call(ctx, &prog_array, index);
```

---

## Quick Reference

### Program Loading (libbpf)

```bash
# Compile
clang -O2 -target bpf -c program.bpf.c -o program.bpf.o

# Load and attach
bpftool prog load program.bpf.o /sys/fs/bpf/myprog
bpftool prog attach pinned /sys/fs/bpf/myprog kprobe do_sys_open

# List programs
bpftool prog list

# Dump map
bpftool map dump name my_map
```

### Map Operations

```
Operation          | Function                            | Description
-------------------|-------------------------------------|------------------
Lookup             | bpf_map_lookup_elem(map, &key)     | Get value
Update             | bpf_map_update_elem(map, &k, &v, 0)| Set value
Delete             | bpf_map_delete_elem(map, &key)     | Remove key
Get next key       | bpf_map_get_next_key(map, &k, &nk) | Iterate keys
```

### Key Guidelines

```
✅ DO: Keep programs simple and verifiable
✅ DO: Use bounded loops with #pragma unroll
✅ DO: Check all pointer bounds before access
✅ DO: Use libbpf for production deployments
✅ DO: Test with verifier verbose mode

❌ DON'T: Use unbounded loops or recursion
❌ DON'T: Access uninitialized variables
❌ DON'T: Exceed verifier complexity limits
```

---

## Anti-Patterns

### Critical Violations

```c
// ❌ NEVER: Unbounded operations
int count = get_packet_size(); // From network
for (int i = 0; i < count; i++) { // REJECTED
    // Process
}

// ✅ CORRECT: Bounded with max
int count = get_packet_size();
if (count > 100)
    count = 100;

#pragma unroll
for (int i = 0; i < count; i++) { // ACCEPTED
    // Process
}
```

❌ **Unbounded loops**: Verifier rejection
✅ **Correct approach**: Fixed bounds or explicit limits

### Common Mistakes

```c
// ❌ Don't: Forget bounds checking
void *data_end = (void *)(long)ctx->data_end;
void *data = (void *)(long)ctx->data;
struct ethhdr *eth = data;
__u16 proto = eth->h_proto; // REJECTED - no bounds check

// ✅ Correct: Always check bounds
void *data_end = (void *)(long)ctx->data_end;
void *data = (void *)(long)ctx->data;
struct ethhdr *eth = data;

if ((void *)(eth + 1) > data_end)
    return XDP_DROP;

__u16 proto = eth->h_proto; // ACCEPTED
```

❌ **No bounds checking**: Verifier rejection, potential crashes
✅ **Better**: Check before every pointer access

---

## Related Skills

- `ebpf-tracing-observability.md` - Using eBPF for tracing and monitoring
- `ebpf-networking.md` - XDP and TC for packet processing
- `ebpf-security-monitoring.md` - Security use cases with eBPF
- `linux-kernel-internals.md` - Understanding kernel hooks

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
