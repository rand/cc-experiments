---
name: ebpf-networking
description: Fast packet processing with XDP, TC filtering, socket programs, load balancing, and Cilium networking
---

# eBPF Networking

**Scope**: XDP packet processing, TC filtering, socket programs, L4/L7 load balancing, and Cilium for Kubernetes
**Lines**: ~340
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building high-performance packet filters or firewalls
- Implementing custom load balancers at L4 or L7
- Processing packets at line rate with XDP
- Modifying packets with TC (Traffic Control)
- Creating per-socket filtering rules
- Using Cilium for Kubernetes networking and security
- Mitigating DDoS attacks at the kernel level
- Optimizing network performance with zero-copy packet access

## Core Concepts

### Concept 1: XDP (eXpress Data Path)

**Actions**: XDP_PASS, XDP_DROP, XDP_TX, XDP_REDIRECT, XDP_ABORTED

**Execution point**: Earliest possible (before SKB allocation)

```c
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/icmp.h>
#include <bpf/bpf_helpers.h>

SEC("xdp")
int xdp_firewall(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    // Parse Ethernet header
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_DROP;

    // Only process IP packets
    if (eth->h_proto != htons(ETH_P_IP))
        return XDP_PASS;

    // Parse IP header
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_DROP;

    // Drop ICMP packets (simple firewall)
    if (ip->protocol == IPPROTO_ICMP)
        return XDP_DROP;

    // Drop packets from specific IP
    __u32 blocked_ip = 0x0a000001; // 10.0.0.1
    if (ip->saddr == htonl(blocked_ip))
        return XDP_DROP;

    return XDP_PASS;
}

char LICENSE[] SEC("license") = "GPL";
```

**XDP modes**:
- Native: Driver support required (fastest)
- Offload: NIC hardware execution (rare)
- Generic: Software fallback (slower, no special driver)

### Concept 2: TC (Traffic Control)

**Hook points**: Ingress (incoming), Egress (outgoing)

**Capabilities**: Packet modification, redirection, drop, pass

```c
#include <linux/bpf.h>
#include <linux/pkt_cls.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <bpf/bpf_helpers.h>

SEC("tc")
int tc_modify_port(struct __sk_buff *skb) {
    void *data_end = (void *)(long)skb->data_end;
    void *data = (void *)(long)skb->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return TC_ACT_OK;

    if (eth->h_proto != htons(ETH_P_IP))
        return TC_ACT_OK;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return TC_ACT_OK;

    if (ip->protocol != IPPROTO_TCP)
        return TC_ACT_OK;

    struct tcphdr *tcp = (void *)(ip + 1);
    if ((void *)(tcp + 1) > data_end)
        return TC_ACT_OK;

    // Redirect port 80 traffic to port 8080
    if (tcp->dest == htons(80)) {
        __u16 new_port = htons(8080);

        // Recalculate TCP checksum
        __u32 csum = tcp->check;
        csum = bpf_csum_diff(&tcp->dest, sizeof(__u16),
                             &new_port, sizeof(__u16), ~csum);
        tcp->check = csum_fold(csum);

        tcp->dest = new_port;
    }

    return TC_ACT_OK;
}

char LICENSE[] SEC("license") = "GPL";
```

### Concept 3: Socket Programs

**Types**: Socket filter, sockops, sk_msg, sk_skb

**Use case**: Per-socket policy, connection steering

```c
// Socket filter: Drop packets for specific socket
SEC("socket")
int socket_filter(struct __sk_buff *skb) {
    // Access socket info
    __u32 protocol = load_byte(skb, offsetof(struct iphdr, protocol));

    if (protocol == IPPROTO_UDP)
        return 0; // Drop UDP

    return -1; // Pass others
}

// Sockops: Attach to socket operations
SEC("sockops")
int sockops_prog(struct bpf_sock_ops *skops) {
    __u32 op = skops->op;

    switch (op) {
    case BPF_SOCK_OPS_PASSIVE_ESTABLISHED_CB:
    case BPF_SOCK_OPS_ACTIVE_ESTABLISHED_CB:
        // Socket established
        bpf_sock_ops_cb_flags_set(skops, BPF_SOCK_OPS_ALL_CB_FLAGS);
        break;

    case BPF_SOCK_OPS_RTO_CB:
        // Retransmit timeout
        bpf_printk("RTO event\n");
        break;
    }

    return 1;
}

char LICENSE[] SEC("license") = "GPL";
```

### Concept 4: Packet Redirection

**XDP_REDIRECT**: Send packet to another interface or CPU

```c
struct {
    __uint(type, BPF_MAP_TYPE_DEVMAP);
    __uint(max_entries, 256);
    __type(key, __u32);
    __type(value, __u32);
} tx_port SEC(".maps");

SEC("xdp")
int xdp_redirect(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_DROP;

    // Redirect to interface in map
    __u32 key = 0;
    return bpf_redirect_map(&tx_port, key, 0);
}

// User space setup
int main() {
    int map_fd = bpf_map__fd(tx_port);
    __u32 key = 0;
    __u32 ifindex = if_nametoindex("eth1"); // Target interface

    bpf_map_update_elem(map_fd, &key, &ifindex, BPF_ANY);
    // Packets now redirect to eth1
}
```

---

## Patterns

### Pattern 1: DDoS Mitigation

**When to use**: Protect against network floods

```c
struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 1000000);
    __type(key, __u32);    // Source IP
    __type(value, __u64);  // Packet count
} rate_limit SEC(".maps");

SEC("xdp")
int xdp_rate_limit(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_DROP;

    if (eth->h_proto != htons(ETH_P_IP))
        return XDP_PASS;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_DROP;

    __u32 src_ip = ip->saddr;
    __u64 *count = bpf_map_lookup_elem(&rate_limit, &src_ip);

    if (count) {
        // Limit: 10,000 packets per second
        if (*count > 10000)
            return XDP_DROP;

        __sync_fetch_and_add(count, 1);
    } else {
        __u64 init = 1;
        bpf_map_update_elem(&rate_limit, &src_ip, &init, BPF_ANY);
    }

    return XDP_PASS;
}

// User space: Reset counts every second
void reset_counters(int map_fd) {
    while (1) {
        sleep(1);
        // LRU automatically evicts old entries
    }
}
```

### Pattern 2: L4 Load Balancer

**Use case**: Distribute connections across backends

```c
struct backend {
    __u32 ip;
    __u16 port;
};

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 4);
    __type(key, __u32);
    __type(value, struct backend);
} backends SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 100000);
    __type(key, __u64);      // Connection hash
    __type(value, __u32);    // Backend index
} conn_table SEC(".maps");

SEC("xdp")
int xdp_lb(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_DROP;

    if (eth->h_proto != htons(ETH_P_IP))
        return XDP_PASS;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_DROP;

    if (ip->protocol != IPPROTO_TCP)
        return XDP_PASS;

    struct tcphdr *tcp = (void *)(ip + 1);
    if ((void *)(tcp + 1) > data_end)
        return XDP_DROP;

    // Hash connection
    __u64 conn_hash = ((__u64)ip->saddr << 32) | ip->daddr;
    conn_hash ^= ((__u64)tcp->source << 16) | tcp->dest;

    // Lookup existing connection
    __u32 *backend_idx = bpf_map_lookup_elem(&conn_table, &conn_hash);
    __u32 idx;

    if (!backend_idx) {
        // New connection: Round-robin selection
        idx = (conn_hash % 4); // 4 backends
        bpf_map_update_elem(&conn_table, &conn_hash, &idx, BPF_ANY);
    } else {
        idx = *backend_idx;
    }

    // Get backend
    struct backend *be = bpf_map_lookup_elem(&backends, &idx);
    if (!be)
        return XDP_DROP;

    // Rewrite destination IP and port
    ip->daddr = be->ip;
    tcp->dest = htons(be->port);

    // Recalculate checksums
    ip->check = 0;
    ip->check = ip_checksum(ip);

    return XDP_TX; // Send back out same interface
}
```

### Pattern 3: Packet Sampling

**When to use**: Network monitoring with low overhead

```c
struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
} events SEC(".maps");

struct packet_sample {
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u8 protocol;
    __u32 len;
};

SEC("xdp")
int xdp_sample(struct xdp_md *ctx) {
    // Sample 1 out of 1000 packets
    if ((bpf_get_prandom_u32() % 1000) != 0)
        return XDP_PASS;

    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (eth->h_proto != htons(ETH_P_IP))
        return XDP_PASS;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;

    struct packet_sample sample = {
        .src_ip = ip->saddr,
        .dst_ip = ip->daddr,
        .protocol = ip->protocol,
        .len = ctx->data_end - ctx->data,
    };

    if (ip->protocol == IPPROTO_TCP) {
        struct tcphdr *tcp = (void *)(ip + 1);
        if ((void *)(tcp + 1) <= data_end) {
            sample.src_port = tcp->source;
            sample.dst_port = tcp->dest;
        }
    }

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU,
                          &sample, sizeof(sample));

    return XDP_PASS;
}
```

### Pattern 4: Cilium Network Policy

**Use case**: Kubernetes networking with eBPF

```yaml
# Cilium NetworkPolicy
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
```

**Under the hood**: Cilium generates eBPF programs

```c
// Simplified Cilium-style policy enforcement
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10000);
    __type(key, __u32);    // Identity
    __type(value, __u8);   // Allowed
} policy_map SEC(".maps");

SEC("from-container")
int enforce_egress(struct __sk_buff *skb) {
    __u32 src_identity = skb->cb[0]; // Cilium sets this
    __u32 dst_identity = skb->cb[1];

    struct policy_key {
        __u32 src;
        __u32 dst;
    } key = {
        .src = src_identity,
        .dst = dst_identity,
    };

    // Lookup policy
    __u8 *allowed = bpf_map_lookup_elem(&policy_map, &key);
    if (!allowed || *allowed == 0)
        return TC_ACT_SHOT; // Drop

    return TC_ACT_OK; // Allow
}
```

### Pattern 5: Connection Tracking

**Use case**: Stateful firewalling

```c
struct conn_key {
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u8 protocol;
};

struct conn_state {
    __u64 packets;
    __u64 bytes;
    __u64 last_seen;
    __u8 state; // NEW, ESTABLISHED, etc.
};

struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 1000000);
    __type(key, struct conn_key);
    __type(value, struct conn_state);
} conntrack SEC(".maps");

SEC("xdp")
int xdp_conntrack(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_DROP;

    if (eth->h_proto != htons(ETH_P_IP))
        return XDP_PASS;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_DROP;

    if (ip->protocol != IPPROTO_TCP)
        return XDP_PASS;

    struct tcphdr *tcp = (void *)(ip + 1);
    if ((void *)(tcp + 1) > data_end)
        return XDP_DROP;

    struct conn_key key = {
        .src_ip = ip->saddr,
        .dst_ip = ip->daddr,
        .src_port = tcp->source,
        .dst_port = tcp->dest,
        .protocol = ip->protocol,
    };

    struct conn_state *state = bpf_map_lookup_elem(&conntrack, &key);

    if (!state) {
        // New connection
        if (!(tcp->syn && !tcp->ack))
            return XDP_DROP; // Must start with SYN

        struct conn_state new_state = {
            .packets = 1,
            .bytes = ctx->data_end - ctx->data,
            .last_seen = bpf_ktime_get_ns(),
            .state = 0, // NEW
        };
        bpf_map_update_elem(&conntrack, &key, &new_state, BPF_ANY);
    } else {
        // Existing connection
        __sync_fetch_and_add(&state->packets, 1);
        __sync_fetch_and_add(&state->bytes, ctx->data_end - ctx->data);
        state->last_seen = bpf_ktime_get_ns();
    }

    return XDP_PASS;
}
```

### Pattern 6: Zero-Copy Packet Modification

**When to use**: High-performance packet rewriting

```c
SEC("xdp")
int xdp_rewrite_mac(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_DROP;

    // Rewrite MAC addresses in-place (zero-copy)
    __u8 src_mac[6] = {0x00, 0x11, 0x22, 0x33, 0x44, 0x55};
    __u8 dst_mac[6] = {0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff};

    __builtin_memcpy(eth->h_source, src_mac, 6);
    __builtin_memcpy(eth->h_dest, dst_mac, 6);

    return XDP_TX; // Transmit modified packet
}
```

---

## Quick Reference

### XDP Actions

```
Action         | Description                    | Use Case
---------------|--------------------------------|------------------
XDP_PASS       | Pass to kernel stack           | Normal processing
XDP_DROP       | Drop packet                    | Firewall, DDoS
XDP_TX         | Bounce back same interface     | Reflection
XDP_REDIRECT   | Redirect to another interface  | Forwarding, LB
XDP_ABORTED    | Drop + trace event             | Error handling
```

### TC Actions

```
Action       | Description
-------------|----------------------------------
TC_ACT_OK    | Pass packet
TC_ACT_SHOT  | Drop packet
TC_ACT_STOLEN| Consumed, don't process further
TC_ACT_REDIRECT | Redirect to another device
```

### Loading Commands

```bash
# XDP
ip link set dev eth0 xdp obj program.o sec xdp

# TC ingress
tc qdisc add dev eth0 clsact
tc filter add dev eth0 ingress bpf da obj program.o sec tc

# Cilium
cilium install
kubectl apply -f policy.yaml
```

### Key Guidelines

```
✅ DO: Use XDP for earliest packet processing
✅ DO: Validate all packet bounds before access
✅ DO: Use LRU maps for connection tracking
✅ DO: Test with different packet sizes and types
✅ DO: Measure performance impact

❌ DON'T: Modify packets without checksum updates
❌ DON'T: Access packet data without bounds checking
❌ DON'T: Use XDP for complex packet inspection (use TC)
```

---

## Anti-Patterns

### Critical Violations

```c
// ❌ NEVER: Access packet data without bounds check
SEC("xdp")
int bad_xdp(struct xdp_md *ctx) {
    struct ethhdr *eth = (void *)(long)ctx->data;
    __u16 proto = eth->h_proto; // REJECTED - no bounds check
    return XDP_PASS;
}

// ✅ CORRECT: Always validate bounds
SEC("xdp")
int good_xdp(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_DROP;

    __u16 proto = eth->h_proto; // ACCEPTED
    return XDP_PASS;
}
```

❌ **No bounds checking**: Verifier rejection, crashes
✅ **Correct approach**: Validate before every access

### Common Mistakes

```c
// ❌ Don't: Modify checksums without recalculation
tcp->dest = htons(8080);
// Checksum now invalid! Packet will be dropped

// ✅ Correct: Recalculate checksums
__u16 old_port = tcp->dest;
__u16 new_port = htons(8080);

tcp->check = bpf_csum_diff(&old_port, sizeof(old_port),
                           &new_port, sizeof(new_port),
                           ~tcp->check);
tcp->dest = new_port;
```

❌ **Invalid checksums**: Packets dropped by receivers
✅ **Better**: Always update checksums when modifying headers

---

## Related Skills

- `ebpf-fundamentals.md` - Core eBPF concepts and verifier
- `ebpf-tracing-observability.md` - Network observability
- `network-protocols.md` - Understanding TCP/IP stack
- `kubernetes-networking.md` - Container networking

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
