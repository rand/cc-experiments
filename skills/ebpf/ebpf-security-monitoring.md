---
name: ebpf-security-monitoring
description: Security monitoring with eBPF including syscall tracking, file/network monitoring, Falco, Tetragon, and threat detection
---

# eBPF Security Monitoring

**Scope**: Runtime security with eBPF for syscall tracking, process execution, file/network access, and threat detection
**Lines**: ~300
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Monitoring suspicious system call patterns
- Tracking file and network access for security
- Detecting privilege escalation attempts
- Using Falco for runtime security alerting
- Implementing Tetragon for security observability
- Creating custom threat detection rules
- Auditing container and Kubernetes security
- Analyzing malware behavior in sandboxed environments

## Core Concepts

### Concept 1: Syscall Tracking

**Purpose**: Monitor system calls for suspicious patterns

```c
#include <vmlinux.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

struct syscall_event {
    u32 pid;
    u32 uid;
    char comm[16];
    int syscall_id;
    u64 timestamp;
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} events SEC(".maps");

// Dangerous syscalls to monitor
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 256);
    __type(key, int);
    __type(value, u8);
} dangerous_syscalls SEC(".maps");

SEC("tracepoint/raw_syscalls/sys_enter")
int track_syscalls(struct trace_event_raw_sys_enter *ctx) {
    int syscall_id = ctx->id;

    // Check if dangerous
    if (!bpf_map_lookup_elem(&dangerous_syscalls, &syscall_id))
        return 0;

    struct syscall_event *e;
    e = bpf_ringbuf_reserve(&events, sizeof(*e), 0);
    if (!e)
        return 0;

    e->pid = bpf_get_current_pid_tgid() >> 32;
    e->uid = bpf_get_current_uid_gid() >> 32;
    e->syscall_id = syscall_id;
    e->timestamp = bpf_ktime_get_ns();
    bpf_get_current_comm(&e->comm, sizeof(e->comm));

    bpf_ringbuf_submit(e, 0);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

```python
# Userspace: Define dangerous syscalls
import os

dangerous = {
    'ptrace': 101,
    'setuid': 105,
    'setgid': 106,
    'execve': 59,
    'kill': 62,
    'mount': 165,
    'umount': 166,
}

# Populate map
for name, syscall_id in dangerous.items():
    dangerous_syscalls[syscall_id] = 1
```

### Concept 2: Process Execution Monitoring

**Detection**: Suspicious process spawning

```c
struct exec_event {
    u32 pid;
    u32 ppid;
    u32 uid;
    char comm[16];
    char filename[256];
    u64 timestamp;
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} exec_events SEC(".maps");

SEC("tracepoint/syscalls/sys_enter_execve")
int trace_execve(struct trace_event_raw_sys_enter *ctx) {
    struct exec_event *e;

    e = bpf_ringbuf_reserve(&exec_events, sizeof(*e), 0);
    if (!e)
        return 0;

    struct task_struct *task = (struct task_struct *)bpf_get_current_task();

    e->pid = bpf_get_current_pid_tgid() >> 32;
    e->uid = bpf_get_current_uid_gid() >> 32;
    e->timestamp = bpf_ktime_get_ns();

    bpf_get_current_comm(&e->comm, sizeof(e->comm));
    bpf_probe_read_kernel(&e->ppid, sizeof(e->ppid),
                          &task->real_parent->tgid);
    bpf_probe_read_user_str(&e->filename, sizeof(e->filename),
                            (void *)ctx->args[0]);

    bpf_ringbuf_submit(e, 0);
    return 0;
}
```

**Userspace detection logic**:

```python
suspicious_patterns = [
    '/tmp/',              # Execution from /tmp
    '/dev/shm/',          # Execution from shared memory
    'nc ',                # Netcat (reverse shell)
    'bash -i',            # Interactive shell
    'python -c',          # Inline Python
    '/proc/self/exe',     # Fileless execution
]

def analyze_exec(event):
    filename = event.filename.decode('utf-8')

    for pattern in suspicious_patterns:
        if pattern in filename:
            alert(f"Suspicious execution: {filename} by PID {event.pid}")
```

### Concept 3: File Access Monitoring

**Use case**: Detect sensitive file access

```c
struct file_event {
    u32 pid;
    char comm[16];
    char filename[256];
    u32 flags;
    u64 timestamp;
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} file_events SEC(".maps");

// Sensitive paths to monitor
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, char[256]);
    __type(value, u8);
} sensitive_paths SEC(".maps");

SEC("tracepoint/syscalls/sys_enter_openat")
int trace_open(struct trace_event_raw_sys_enter *ctx) {
    char filename[256];

    bpf_probe_read_user_str(&filename, sizeof(filename),
                            (void *)ctx->args[1]);

    // Check if path is sensitive
    if (!bpf_map_lookup_elem(&sensitive_paths, &filename))
        return 0;

    struct file_event *e;
    e = bpf_ringbuf_reserve(&file_events, sizeof(*e), 0);
    if (!e)
        return 0;

    e->pid = bpf_get_current_pid_tgid() >> 32;
    e->flags = ctx->args[2];
    e->timestamp = bpf_ktime_get_ns();

    bpf_get_current_comm(&e->comm, sizeof(e->comm));
    __builtin_memcpy(e->filename, filename, sizeof(filename));

    bpf_ringbuf_submit(e, 0);
    return 0;
}
```

```python
# Monitor sensitive files
sensitive_files = [
    '/etc/shadow',
    '/etc/passwd',
    '/root/.ssh/id_rsa',
    '/home/*/.ssh/id_rsa',
    '/var/log/auth.log',
]

for path in sensitive_files:
    sensitive_paths[path.encode()] = 1
```

### Concept 4: Network Activity Monitoring

**Pattern**: Detect suspicious connections

```c
struct connect_event {
    u32 pid;
    u32 uid;
    char comm[16];
    u32 dst_ip;
    u16 dst_port;
    u64 timestamp;
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} connect_events SEC(".maps");

SEC("kprobe/tcp_connect")
int trace_connect(struct pt_regs *ctx) {
    struct sock *sk = (struct sock *)PT_REGS_PARM1(ctx);
    struct connect_event *e;

    e = bpf_ringbuf_reserve(&connect_events, sizeof(*e), 0);
    if (!e)
        return 0;

    e->pid = bpf_get_current_pid_tgid() >> 32;
    e->uid = bpf_get_current_uid_gid() >> 32;
    e->timestamp = bpf_ktime_get_ns();

    bpf_get_current_comm(&e->comm, sizeof(e->comm));

    // Extract destination IP and port
    u16 family;
    bpf_probe_read_kernel(&family, sizeof(family), &sk->__sk_common.skc_family);

    if (family == AF_INET) {
        bpf_probe_read_kernel(&e->dst_ip, sizeof(e->dst_ip),
                              &sk->__sk_common.skc_daddr);
        bpf_probe_read_kernel(&e->dst_port, sizeof(e->dst_port),
                              &sk->__sk_common.skc_dport);
        e->dst_port = ntohs(e->dst_port);
    }

    bpf_ringbuf_submit(e, 0);
    return 0;
}
```

**Detection logic**:

```python
import ipaddress

# Suspicious ports
suspicious_ports = [4444, 5555, 6666, 7777, 8888, 9999]  # Common backdoor ports
blacklisted_ips = ['192.0.2.1', '198.51.100.1']  # Example C2 servers

def analyze_connection(event):
    dst_ip = ipaddress.IPv4Address(event.dst_ip)
    dst_port = event.dst_port

    if dst_port in suspicious_ports:
        alert(f"{event.comm} (PID {event.pid}) connecting to suspicious port {dst_port}")

    if str(dst_ip) in blacklisted_ips:
        alert(f"{event.comm} (PID {event.pid}) connecting to blacklisted IP {dst_ip}")
```

---

## Patterns

### Pattern 1: Privilege Escalation Detection

**When to use**: Detect setuid/setgid abuse

```c
SEC("tracepoint/syscalls/sys_enter_setuid")
int detect_setuid(struct trace_event_raw_sys_enter *ctx) {
    u32 current_uid = bpf_get_current_uid_gid() >> 32;
    u32 target_uid = ctx->args[0];

    // Alert if non-root tries to become root
    if (current_uid != 0 && target_uid == 0) {
        char comm[16];
        u32 pid = bpf_get_current_pid_tgid() >> 32;

        bpf_get_current_comm(&comm, sizeof(comm));
        bpf_printk("ALERT: PID %d (%s) attempting to setuid(0)\n",
                   pid, comm);
    }

    return 0;
}

SEC("tracepoint/syscalls/sys_enter_ptrace")
int detect_ptrace(struct trace_event_raw_sys_enter *ctx) {
    u32 request = ctx->args[0];
    u32 target_pid = ctx->args[1];

    char comm[16];
    u32 pid = bpf_get_current_pid_tgid() >> 32;

    bpf_get_current_comm(&comm, sizeof(comm));
    bpf_printk("ALERT: PID %d (%s) ptrace() on PID %d\n",
               pid, comm, target_pid);

    return 0;
}
```

### Pattern 2: Falco Integration

**Use case**: Production runtime security

```yaml
# Falco rule example
- rule: Suspicious Process Execution
  desc: Detect execution from /tmp or /dev/shm
  condition: >
    spawned_process and
    (proc.exe startswith /tmp or proc.exe startswith /dev/shm)
  output: >
    Suspicious execution (user=%user.name command=%proc.cmdline
    container=%container.name image=%container.image)
  priority: WARNING

- rule: Sensitive File Access
  desc: Detect access to /etc/shadow
  condition: >
    open_read and
    fd.name=/etc/shadow and
    not user.name in (root, systemd)
  output: >
    Sensitive file accessed (user=%user.name command=%proc.cmdline
    file=%fd.name)
  priority: CRITICAL

- rule: Reverse Shell
  desc: Detect common reverse shell patterns
  condition: >
    spawned_process and
    (proc.cmdline contains "bash -i" or
     proc.cmdline contains "nc " or
     proc.cmdline contains "python -c")
  output: >
    Potential reverse shell (user=%user.name command=%proc.cmdline)
  priority: CRITICAL
```

### Pattern 3: Tetragon Security Policies

**When to use**: Kubernetes security observability

```yaml
# Tetragon TracingPolicy
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: monitor-sensitive-files
spec:
  kprobes:
  - call: "security_file_open"
    syscall: false
    args:
    - index: 0
      type: "file"
    selectors:
    - matchArgs:
      - index: 0
        operator: "Prefix"
        values:
        - "/etc/shadow"
        - "/etc/passwd"
        - "/root/.ssh"
    - matchActions:
      - action: Post
```

```yaml
# Detect privilege escalation
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: detect-privilege-escalation
spec:
  tracepoints:
  - subsystem: "syscalls"
    event: "sys_enter_setuid"
    args:
    - index: 0
      type: "int"
    selectors:
    - matchArgs:
      - index: 0
        operator: "Equal"
        values:
        - "0"
    - matchCapabilities:
      - type: "Effective"
        operator: "NotIn"
        values:
        - "CAP_SETUID"
```

### Pattern 4: Container Escape Detection

**Use case**: Monitor container breakout attempts

```c
SEC("kprobe/commit_creds")
int detect_cred_override(struct pt_regs *ctx) {
    struct cred *new_creds = (struct cred *)PT_REGS_PARM1(ctx);
    u32 new_uid;

    bpf_probe_read_kernel(&new_uid, sizeof(new_uid), &new_creds->uid);

    u32 current_uid = bpf_get_current_uid_gid() >> 32;

    // Detect privilege escalation
    if (current_uid != 0 && new_uid == 0) {
        char comm[16];
        u32 pid = bpf_get_current_pid_tgid() >> 32;

        bpf_get_current_comm(&comm, sizeof(comm));
        bpf_printk("ALERT: Credential override! PID %d (%s) UID %d -> 0\n",
                   pid, comm, current_uid);
    }

    return 0;
}

SEC("kprobe/do_mount")
int detect_mount(struct pt_regs *ctx) {
    char source[256];
    char target[256];

    bpf_probe_read_user_str(&source, sizeof(source),
                            (void *)PT_REGS_PARM1(ctx));
    bpf_probe_read_user_str(&target, sizeof(target),
                            (void *)PT_REGS_PARM2(ctx));

    char comm[16];
    u32 pid = bpf_get_current_pid_tgid() >> 32;

    bpf_get_current_comm(&comm, sizeof(comm));
    bpf_printk("Mount: PID %d (%s) mounting %s to %s\n",
               pid, comm, source, target);

    return 0;
}
```

### Pattern 5: Malware Behavior Detection

**When to use**: Sandbox analysis

```python
# Behavioral analysis patterns
class MalwareDetector:
    def __init__(self):
        self.process_activity = {}

    def analyze_behavior(self, pid, event_type, details):
        if pid not in self.process_activity:
            self.process_activity[pid] = {
                'file_writes': 0,
                'network_connections': 0,
                'process_spawns': 0,
                'sensitive_files': [],
            }

        activity = self.process_activity[pid]

        if event_type == 'file_write':
            activity['file_writes'] += 1

        if event_type == 'network_connect':
            activity['network_connections'] += 1

        if event_type == 'process_spawn':
            activity['process_spawns'] += 1

        if event_type == 'sensitive_file':
            activity['sensitive_files'].append(details)

        # Detection heuristics
        score = 0

        # Mass file writes (ransomware)
        if activity['file_writes'] > 1000:
            score += 50

        # Excessive network connections (botnet)
        if activity['network_connections'] > 100:
            score += 30

        # Rapid process spawning (worm)
        if activity['process_spawns'] > 10:
            score += 40

        # Accessing credentials
        if any('ssh' in f or 'passwd' in f for f in activity['sensitive_files']):
            score += 60

        if score > 80:
            alert(f"High malware probability for PID {pid}: score={score}")
```

### Pattern 6: Audit Logging

**Use case**: Comprehensive security audit trail

```c
struct audit_event {
    u64 timestamp;
    u32 pid;
    u32 uid;
    u32 gid;
    char comm[16];
    u8 event_type;
    char details[256];
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 1024 * 1024);
} audit_log SEC(".maps");

static __always_inline void log_event(u8 event_type, const char *details) {
    struct audit_event *e;

    e = bpf_ringbuf_reserve(&audit_log, sizeof(*e), 0);
    if (!e)
        return;

    u64 pid_tgid = bpf_get_current_pid_tgid();
    u64 uid_gid = bpf_get_current_uid_gid();

    e->timestamp = bpf_ktime_get_ns();
    e->pid = pid_tgid >> 32;
    e->uid = uid_gid >> 32;
    e->gid = uid_gid & 0xFFFFFFFF;
    e->event_type = event_type;

    bpf_get_current_comm(&e->comm, sizeof(e->comm));
    bpf_probe_read_kernel_str(&e->details, sizeof(e->details), details);

    bpf_ringbuf_submit(e, 0);
}

// Use in various probes
SEC("tracepoint/syscalls/sys_enter_execve")
int audit_exec(struct trace_event_raw_sys_enter *ctx) {
    char filename[256];
    bpf_probe_read_user_str(&filename, sizeof(filename),
                            (void *)ctx->args[0]);

    log_event(EVENT_EXEC, filename);
    return 0;
}
```

---

## Quick Reference

### Common Threat Indicators

```
Pattern                  | Indicator                     | Severity
-------------------------|-------------------------------|----------
Execution from /tmp      | Malware persistence           | High
setuid(0) by non-root    | Privilege escalation          | Critical
Access to /etc/shadow    | Credential theft              | Critical
Reverse shell pattern    | Remote access/C2              | Critical
Mass file encryption     | Ransomware                    | Critical
Ptrace on init           | Container escape              | Critical
Mount operations         | Container escape              | High
```

### Falco Commands

```bash
# Run Falco
falco -c /etc/falco/falco.yaml

# Test rule
falco -M 45 -o json_output=true

# Custom rules
falco -r /etc/falco/custom_rules.yaml
```

### Key Guidelines

```
✅ DO: Monitor syscalls with high security impact
✅ DO: Use ringbuf for efficient event streaming
✅ DO: Implement behavioral analysis for detection
✅ DO: Integrate with SIEM for centralized logging
✅ DO: Test detection rules regularly

❌ DON'T: Monitor every syscall (overhead)
❌ DON'T: Ignore false positives (tune rules)
❌ DON'T: Run without proper alerting
```

---

## Anti-Patterns

### Critical Violations

```c
// ❌ NEVER: Monitor without filtering
SEC("tracepoint/raw_syscalls/sys_enter")
int trace_all_syscalls(void *ctx) {
    // Logs EVERY syscall - massive overhead!
    bpf_printk("Syscall\n");
    return 0;
}

// ✅ CORRECT: Filter to dangerous syscalls
SEC("tracepoint/raw_syscalls/sys_enter")
int trace_dangerous_only(struct trace_event_raw_sys_enter *ctx) {
    int syscall_id = ctx->id;

    if (!bpf_map_lookup_elem(&dangerous_syscalls, &syscall_id))
        return 0; // Skip safe syscalls

    // Log only dangerous ones
    return 0;
}
```

❌ **No filtering**: System slowdown, log flooding
✅ **Correct approach**: Filter to security-relevant events

---

## Related Skills

- `ebpf-fundamentals.md` - Core eBPF concepts
- `ebpf-tracing-observability.md` - General tracing patterns
- `container-security.md` - Container security practices
- `kubernetes-security.md` - K8s security patterns

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
