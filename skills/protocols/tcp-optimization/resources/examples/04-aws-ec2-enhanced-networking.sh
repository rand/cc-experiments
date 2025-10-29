#!/usr/bin/env bash
# AWS EC2 Enhanced Networking and TCP Optimization
# Optimizes TCP for AWS EC2 instances with ENA (Elastic Network Adapter)

set -euo pipefail

echo "AWS EC2 TCP Optimization Setup"
echo "======================================"

# Detect if running on AWS EC2
if ! curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/instance-id &>/dev/null; then
    echo "Error: Not running on AWS EC2"
    exit 1
fi

INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
INSTANCE_TYPE=$(curl -s http://169.254.169.254/latest/meta-data/instance-type)
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)

echo "Instance ID: $INSTANCE_ID"
echo "Instance Type: $INSTANCE_TYPE"
echo "Availability Zone: $AZ"
echo ""

# Check if ENA is loaded
if lsmod | grep -q ena; then
    echo "✓ ENA driver loaded"
    modinfo ena | grep -E "^version|^description"
else
    echo "✗ ENA driver not loaded"
    echo "Install with: sudo apt install linux-aws"
fi
echo ""

# Configure jumbo frames (MTU 9001) for VPC traffic
echo "Configuring jumbo frames (MTU 9001)..."
INTERFACE=$(ip route | grep default | awk '{print $5}' | head -1)
ip link set dev "$INTERFACE" mtu 9001
echo "✓ MTU set to 9001 on $INTERFACE"
echo ""

# Apply TCP optimizations
cat > /etc/sysctl.d/99-aws-tcp.conf <<'EOF'
# AWS EC2 TCP Optimization

# BBR congestion control
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq

# Large buffers for 10-100 Gbps
net.ipv4.tcp_rmem = 4096 131072 134217728
net.ipv4.tcp_wmem = 4096 131072 134217728
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728

# TCP features
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_mtu_probing = 1
net.ipv4.tcp_fastopen = 3

# Connection handling
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_max_tw_buckets = 2000000
net.ipv4.ip_local_port_range = 10000 65535
net.core.somaxconn = 4096
EOF

sysctl -p /etc/sysctl.d/99-aws-tcp.conf
echo "✓ TCP parameters applied"
echo ""

# Configure NIC offloading
echo "Configuring NIC offloading..."
ethtool -K "$INTERFACE" tso on gso on gro on || true
ethtool -L "$INTERFACE" combined "$(nproc)" || true
echo "✓ NIC offloading configured"
echo ""

# Make MTU persistent
cat > /etc/network/if-up.d/mtu-9001 <<'EOF'
#!/bin/sh
ip link set dev eth0 mtu 9001
EOF
chmod +x /etc/network/if-up.d/mtu-9001

echo "======================================"
echo "AWS EC2 TCP Optimization Complete"
echo ""
echo "Test with:"
echo "  iperf3 -c <server-in-same-vpc> -t 60"
echo ""
echo "Verify MTU:"
echo "  ping -M do -s 8973 <server-in-vpc>"
echo "======================================"
