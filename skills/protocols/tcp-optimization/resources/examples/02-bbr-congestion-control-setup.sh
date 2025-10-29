#!/usr/bin/env bash

# BBR (Bottleneck Bandwidth and RTT) Congestion Control Setup
# Enables and configures BBR for optimal TCP performance
#
# BBR is a model-based congestion control algorithm developed by Google
# that achieves higher throughput and lower latency than traditional
# loss-based algorithms (Reno, Cubic).
#
# Requirements:
#   - Linux kernel 4.9+ (BBR v1)
#   - Linux kernel 5.18+ (BBR v2)
#
# Usage:
#   sudo bash 02-bbr-congestion-control-setup.sh
#
# Tested on:
#   - Ubuntu 22.04 LTS
#   - Debian 12
#   - RHEL 9 / Rocky Linux 9

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}BBR Congestion Control Setup${NC}"
echo "======================================"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Check kernel version
echo -e "${BLUE}[1/6] Checking kernel version${NC}"
KERNEL_VERSION=$(uname -r | cut -d. -f1-2)
KERNEL_MAJOR=$(echo "$KERNEL_VERSION" | cut -d. -f1)
KERNEL_MINOR=$(echo "$KERNEL_VERSION" | cut -d. -f2)

echo "Kernel version: $(uname -r)"

if [[ $KERNEL_MAJOR -lt 4 ]] || [[ $KERNEL_MAJOR -eq 4 && $KERNEL_MINOR -lt 9 ]]; then
    echo -e "${RED}Error: BBR requires kernel 4.9 or newer${NC}"
    echo "Current kernel: $KERNEL_VERSION"
    exit 1
fi

if [[ $KERNEL_MAJOR -ge 5 && $KERNEL_MINOR -ge 18 ]]; then
    echo -e "${GREEN}BBR v2 is available (kernel 5.18+)${NC}"
    BBR_VERSION="bbr2"
elif [[ $KERNEL_MAJOR -ge 4 && $KERNEL_MINOR -ge 9 ]]; then
    echo -e "${GREEN}BBR v1 is available (kernel 4.9+)${NC}"
    BBR_VERSION="bbr"
fi

echo ""

# Check available congestion control algorithms
echo -e "${BLUE}[2/6] Checking available congestion control algorithms${NC}"
AVAILABLE_CC=$(sysctl -n net.ipv4.tcp_available_congestion_control)
echo "Available: $AVAILABLE_CC"

if [[ ! "$AVAILABLE_CC" =~ "bbr" ]]; then
    echo -e "${YELLOW}BBR not in available list, will attempt to load kernel module${NC}"
fi

echo ""

# Load BBR kernel module
echo -e "${BLUE}[3/6] Loading BBR kernel module${NC}"

if modprobe tcp_bbr 2>/dev/null; then
    echo -e "${GREEN}Successfully loaded tcp_bbr kernel module${NC}"
elif lsmod | grep -q tcp_bbr; then
    echo -e "${GREEN}tcp_bbr kernel module already loaded${NC}"
else
    echo -e "${RED}Failed to load tcp_bbr kernel module${NC}"
    echo -e "${YELLOW}BBR may be built into your kernel${NC}"
fi

# If BBR v2 is available, try to load it
if [[ "$BBR_VERSION" == "bbr2" ]]; then
    if modprobe tcp_bbr2 2>/dev/null; then
        echo -e "${GREEN}Successfully loaded tcp_bbr2 kernel module${NC}"
    elif lsmod | grep -q tcp_bbr2; then
        echo -e "${GREEN}tcp_bbr2 kernel module already loaded${NC}"
    else
        echo -e "${YELLOW}BBR v2 not available, using BBR v1${NC}"
        BBR_VERSION="bbr"
    fi
fi

echo ""

# Configure BBR
echo -e "${BLUE}[4/6] Configuring BBR congestion control${NC}"

# Set BBR as congestion control
if sysctl -w net.ipv4.tcp_congestion_control="$BBR_VERSION" >/dev/null 2>&1; then
    echo -e "${GREEN}Set congestion control to $BBR_VERSION${NC}"
else
    echo -e "${RED}Failed to set congestion control to $BBR_VERSION${NC}"
    exit 1
fi

# Set Fair Queueing as default qdisc (required for BBR)
if sysctl -w net.core.default_qdisc=fq >/dev/null 2>&1; then
    echo -e "${GREEN}Set default qdisc to fq (Fair Queueing)${NC}"
else
    echo -e "${RED}Failed to set default qdisc to fq${NC}"
    exit 1
fi

echo ""

# Make configuration persistent
echo -e "${BLUE}[5/6] Making configuration persistent${NC}"

SYSCTL_CONF="/etc/sysctl.d/99-bbr.conf"

cat > "$SYSCTL_CONF" <<EOF
# BBR Congestion Control Configuration
# Generated: $(date)

# Enable BBR congestion control
net.ipv4.tcp_congestion_control = $BBR_VERSION

# Set Fair Queueing as default qdisc (required for BBR)
net.core.default_qdisc = fq

# Optional: Enable ECN (Explicit Congestion Notification)
# ECN can further improve performance by signaling congestion
# without packet loss
net.ipv4.tcp_ecn = 1
EOF

echo -e "${GREEN}Configuration saved to $SYSCTL_CONF${NC}"

# Load tcp_bbr module on boot
MODULES_CONF="/etc/modules-load.d/bbr.conf"
echo "tcp_bbr" > "$MODULES_CONF"

if [[ "$BBR_VERSION" == "bbr2" ]]; then
    echo "tcp_bbr2" >> "$MODULES_CONF"
fi

echo -e "${GREEN}Module loading configured in $MODULES_CONF${NC}"

echo ""

# Verify configuration
echo -e "${BLUE}[6/6] Verifying configuration${NC}"

CURRENT_CC=$(sysctl -n net.ipv4.tcp_congestion_control)
CURRENT_QDISC=$(sysctl -n net.core.default_qdisc)

echo "Current congestion control: $CURRENT_CC"
echo "Current default qdisc: $CURRENT_QDISC"

if [[ "$CURRENT_CC" == "$BBR_VERSION" ]] && [[ "$CURRENT_QDISC" == "fq" ]]; then
    echo -e "${GREEN}BBR configuration successful!${NC}"
else
    echo -e "${RED}BBR configuration may have issues${NC}"
    exit 1
fi

echo ""

# Optional: Apply to existing interfaces
echo -e "${BLUE}Optional: Applying qdisc to network interfaces${NC}"

for iface in $(ip -o link show | awk -F': ' '{print $2}' | grep -v lo); do
    if tc qdisc replace dev "$iface" root fq 2>/dev/null; then
        echo -e "${GREEN}Applied fq qdisc to $iface${NC}"
    else
        echo -e "${YELLOW}Could not apply fq qdisc to $iface (may not support it)${NC}"
    fi
done

echo ""

# Display summary
cat <<EOF
======================================"
${GREEN}BBR Setup Complete${NC}
======================================"

Configuration:
  - Congestion Control: $BBR_VERSION
  - Queue Discipline: fq
  - Persistent Config: $SYSCTL_CONF
  - Module Loading: $MODULES_CONF

Next Steps:
  1. Test throughput with iperf3:
     iperf3 -c <server> -t 60 -C $BBR_VERSION

  2. Monitor TCP connections:
     ss -tin | grep bbr

  3. Check TCP statistics:
     nstat -az | grep Tcp

  4. Compare with baseline (optional):
     Test with Cubic: iperf3 -c <server> -C cubic
     Test with BBR: iperf3 -c <server> -C $BBR_VERSION

Benefits of BBR:
  ✓ Higher throughput on high BDP networks
  ✓ Lower latency (smaller queues)
  ✓ Better loss tolerance (wireless/mobile)
  ✓ Faster convergence
  ✓ Works well with shallow buffers

Notes:
  - BBR is model-based (not loss-based)
  - Operates at optimal bandwidth-delay product
  - Requires Fair Queueing (fq) qdisc
  - Works best with modern kernels (5.10+)

======================================"
EOF
