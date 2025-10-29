#!/usr/bin/env python3
"""
eBPF TCP Tracing Example
Traces TCP connection events, retransmits, and performance metrics

Requirements:
  - bcc (BPF Compiler Collection)
  - Linux kernel 4.9+

Install:
  sudo apt install python3-bpfcc  # Debian/Ubuntu
  sudo yum install bcc-tools python3-bcc  # RHEL/CentOS

Usage:
  sudo python3 09-ebpf-tcp-tracing.py
"""

from bcc import BPF
import socket
import struct
import time

# BPF program
bpf_text = """
#include <uapi/linux/ptrace.h>
#include <net/sock.h>
#include <bcc/proto.h>

struct tcp_event_t {
    u32 pid;
    char comm[16];
    u32 saddr;
    u32 daddr;
    u16 sport;
    u16 dport;
    u64 bytes;
    u32 retrans;
};

BPF_PERF_OUTPUT(events);

int trace_tcp_retransmit(struct pt_regs *ctx, struct sock *sk) {
    struct tcp_event_t event = {};

    event.pid = bpf_get_current_pid_tgid() >> 32;
    bpf_get_current_comm(&event.comm, sizeof(event.comm));

    u16 family = sk->__sk_common.skc_family;
    if (family == AF_INET) {
        event.saddr = sk->__sk_common.skc_rcv_saddr;
        event.daddr = sk->__sk_common.skc_daddr;
        event.sport = sk->__sk_common.skc_num;
        event.dport = sk->__sk_common.skc_dport;
        event.dport = ntohs(event.dport);

        events.perf_submit(ctx, &event, sizeof(event));
    }

    return 0;
}
"""

# Load BPF program
b = BPF(text=bpf_text)
b.attach_kprobe(event="tcp_retransmit_skb", fn_name="trace_tcp_retransmit")

def inet_ntoa(addr):
    return socket.inet_ntoa(struct.pack("I", addr))

def print_event(cpu, data, size):
    event = b["events"].event(data)
    print(f"[{event.comm.decode()}:{event.pid}] "
          f"{inet_ntoa(event.saddr)}:{event.sport} -> "
          f"{inet_ntoa(event.daddr)}:{event.dport} "
          f"RETRANSMIT")

print("Tracing TCP retransmits... Press Ctrl-C to exit")
b["events"].open_perf_buffer(print_event)

running = True
def signal_handler(sig, frame):
    global running
    running = False
    print("\nExiting...")

import signal
signal.signal(signal.SIGINT, signal_handler)

while running:
    b.perf_buffer_poll(timeout=100)  # Polls with 100ms timeout (blocks, not tight loop)
