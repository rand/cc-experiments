#!/usr/bin/env python3

"""
analyze_tcp_performance.py - TCP metrics collection and performance analysis

Collects TCP metrics, identifies bottlenecks, and provides tuning recommendations.
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class TCPMetrics:
    """TCP performance metrics"""
    # Connection stats
    curr_estab: int = 0
    active_opens: int = 0
    passive_opens: int = 0
    attempt_fails: int = 0
    estab_resets: int = 0

    # Data transfer
    in_segs: int = 0
    out_segs: int = 0
    retrans_segs: int = 0

    # Loss and errors
    in_errs: int = 0
    in_csum_errors: int = 0
    tcp_loss: int = 0
    tcp_timeouts: int = 0

    # SACK
    sack_reorder: int = 0
    sack_discard: int = 0

    # Derived metrics
    retrans_rate: float = 0.0
    error_rate: float = 0.0

    def calculate_derived(self) -> None:
        """Calculate derived metrics"""
        if self.out_segs > 0:
            self.retrans_rate = (self.retrans_segs / self.out_segs) * 100
        if self.in_segs > 0:
            self.error_rate = (self.in_errs / self.in_segs) * 100


@dataclass
class ConnectionInfo:
    """TCP connection information"""
    state: str
    local_addr: str
    remote_addr: str
    cwnd: int = 0
    ssthresh: int = 0
    rtt: float = 0.0
    retrans: int = 0
    send_rate: float = 0.0


@dataclass
class SystemInfo:
    """System configuration information"""
    congestion_control: str = "unknown"
    qdisc: str = "unknown"
    window_scaling: int = 0
    sack: int = 0
    timestamps: int = 0
    rmem_max: int = 0
    wmem_max: int = 0
    tcp_mem: str = "unknown"


@dataclass
class PerformanceAnalysis:
    """Performance analysis results"""
    timestamp: str
    metrics: TCPMetrics
    connections: List[ConnectionInfo]
    system: SystemInfo
    bottlenecks: List[str]
    recommendations: List[str]
    severity: str  # low, medium, high, critical


class TCPAnalyzer:
    """TCP performance analyzer"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.metrics = TCPMetrics()
        self.connections: List[ConnectionInfo] = []
        self.system = SystemInfo()
        self.bottlenecks: List[str] = []
        self.recommendations: List[str] = []

    def log(self, message: str) -> None:
        """Log message if verbose"""
        if self.verbose:
            print(f"[VERBOSE] {message}", file=sys.stderr)

    def run_command(self, cmd: List[str]) -> Optional[str]:
        """Run command and return output"""
        try:
            self.log(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}")
            return None
        except subprocess.TimeoutExpired:
            self.log(f"Command timeout: {' '.join(cmd)}")
            return None
        except FileNotFoundError:
            self.log(f"Command not found: {cmd[0]}")
            return None

    def collect_system_info(self) -> None:
        """Collect system configuration"""
        self.log("Collecting system configuration")

        # Congestion control
        output = self.run_command(["sysctl", "-n", "net.ipv4.tcp_congestion_control"])
        if output:
            self.system.congestion_control = output.strip()

        # Default qdisc
        output = self.run_command(["sysctl", "-n", "net.core.default_qdisc"])
        if output:
            self.system.qdisc = output.strip()

        # Window scaling
        output = self.run_command(["sysctl", "-n", "net.ipv4.tcp_window_scaling"])
        if output:
            self.system.window_scaling = int(output.strip())

        # SACK
        output = self.run_command(["sysctl", "-n", "net.ipv4.tcp_sack"])
        if output:
            self.system.sack = int(output.strip())

        # Timestamps
        output = self.run_command(["sysctl", "-n", "net.ipv4.tcp_timestamps"])
        if output:
            self.system.timestamps = int(output.strip())

        # Buffer sizes
        output = self.run_command(["sysctl", "-n", "net.core.rmem_max"])
        if output:
            self.system.rmem_max = int(output.strip())

        output = self.run_command(["sysctl", "-n", "net.core.wmem_max"])
        if output:
            self.system.wmem_max = int(output.strip())

        # TCP memory
        output = self.run_command(["sysctl", "-n", "net.ipv4.tcp_mem"])
        if output:
            self.system.tcp_mem = output.strip()

    def collect_tcp_metrics(self) -> None:
        """Collect TCP metrics from nstat"""
        self.log("Collecting TCP metrics")

        output = self.run_command(["nstat", "-az"])
        if not output:
            self.log("Failed to collect nstat metrics")
            return

        # Parse nstat output
        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue

            metric_name = parts[0]
            try:
                metric_value = int(parts[1])
            except ValueError as e:
                self.log(f"Skipping invalid metric '{metric_name}': {e}")
                continue

            # Map metrics
            if metric_name == "TcpCurrEstab":
                self.metrics.curr_estab = metric_value
            elif metric_name == "TcpActiveOpens":
                self.metrics.active_opens = metric_value
            elif metric_name == "TcpPassiveOpens":
                self.metrics.passive_opens = metric_value
            elif metric_name == "TcpAttemptFails":
                self.metrics.attempt_fails = metric_value
            elif metric_name == "TcpEstabResets":
                self.metrics.estab_resets = metric_value
            elif metric_name == "TcpInSegs":
                self.metrics.in_segs = metric_value
            elif metric_name == "TcpOutSegs":
                self.metrics.out_segs = metric_value
            elif metric_name == "TcpRetransSegs":
                self.metrics.retrans_segs = metric_value
            elif metric_name == "TcpInErrs":
                self.metrics.in_errs = metric_value
            elif metric_name == "TcpInCsumErrors":
                self.metrics.in_csum_errors = metric_value
            elif metric_name == "TcpExtTCPLoss":
                self.metrics.tcp_loss = metric_value
            elif metric_name == "TcpExtTCPTimeouts":
                self.metrics.tcp_timeouts = metric_value
            elif metric_name == "TcpExtTCPSACKReorder":
                self.metrics.sack_reorder = metric_value
            elif metric_name == "TcpExtTCPSACKDiscard":
                self.metrics.sack_discard = metric_value

        # Calculate derived metrics
        self.metrics.calculate_derived()

    def collect_connection_info(self, limit: int = 10) -> None:
        """Collect active TCP connection information"""
        self.log("Collecting connection information")

        output = self.run_command(["ss", "-tin", "state", "established"])
        if not output:
            self.log("Failed to collect connection info")
            return

        # Parse ss output
        current_conn: Optional[ConnectionInfo] = None
        count = 0

        for line in output.splitlines():
            if count >= limit:
                break

            # Connection line: ESTAB 0 0 local:port remote:port
            if line.startswith("ESTAB") or line.startswith("SYN-"):
                parts = line.split()
                if len(parts) >= 5:
                    current_conn = ConnectionInfo(
                        state=parts[0],
                        local_addr=parts[3],
                        remote_addr=parts[4]
                    )
                    count += 1

            # TCP info line
            elif current_conn and line.strip():
                # Extract TCP parameters
                cwnd_match = re.search(r'cwnd:(\d+)', line)
                if cwnd_match:
                    current_conn.cwnd = int(cwnd_match.group(1))

                ssthresh_match = re.search(r'ssthresh:(\d+)', line)
                if ssthresh_match:
                    current_conn.ssthresh = int(ssthresh_match.group(1))

                rtt_match = re.search(r'rtt:([\d.]+)', line)
                if rtt_match:
                    current_conn.rtt = float(rtt_match.group(1))

                retrans_match = re.search(r'retrans:(\d+)/\d+', line)
                if retrans_match:
                    current_conn.retrans = int(retrans_match.group(1))

                send_match = re.search(r'send ([\d.]+)([KMG]?)bps', line)
                if send_match:
                    rate = float(send_match.group(1))
                    unit = send_match.group(2)
                    if unit == "K":
                        rate *= 1e3
                    elif unit == "M":
                        rate *= 1e6
                    elif unit == "G":
                        rate *= 1e9
                    current_conn.send_rate = rate

                # Add connection after parsing its info
                if cwnd_match or rtt_match:
                    self.connections.append(current_conn)
                    current_conn = None

    def analyze_performance(self) -> None:
        """Analyze performance and identify bottlenecks"""
        self.log("Analyzing performance")

        # Check retransmission rate
        if self.metrics.retrans_rate > 1.0:
            severity = "critical" if self.metrics.retrans_rate > 5.0 else "high"
            self.bottlenecks.append(
                f"High retransmission rate: {self.metrics.retrans_rate:.2f}% (threshold: 1%)"
            )
            self.recommendations.append("Increase TCP buffer sizes")
            self.recommendations.append("Consider using BBR congestion control")
            self.recommendations.append("Check for network packet loss")

        # Check error rate
        if self.metrics.error_rate > 0.1:
            self.bottlenecks.append(
                f"High error rate: {self.metrics.error_rate:.2f}%"
            )
            self.recommendations.append("Check network hardware (NICs, cables)")
            self.recommendations.append("Verify checksums and offloading settings")

        # Check congestion control
        if self.system.congestion_control not in ["bbr", "bbr2"]:
            self.bottlenecks.append(
                f"Using {self.system.congestion_control} congestion control (consider BBR)"
            )
            self.recommendations.append("Enable BBR congestion control for better performance")

        # Check window scaling
        if self.system.window_scaling == 0:
            self.bottlenecks.append("Window scaling disabled (limits throughput)")
            self.recommendations.append("Enable window scaling: sysctl -w net.ipv4.tcp_window_scaling=1")

        # Check SACK
        if self.system.sack == 0:
            self.bottlenecks.append("SACK disabled (inefficient loss recovery)")
            self.recommendations.append("Enable SACK: sysctl -w net.ipv4.tcp_sack=1")

        # Check timestamps
        if self.system.timestamps == 0:
            self.bottlenecks.append("TCP timestamps disabled")
            self.recommendations.append("Enable timestamps: sysctl -w net.ipv4.tcp_timestamps=1")

        # Check buffer sizes
        if self.system.rmem_max < 16777216:  # 16 MB
            self.bottlenecks.append(
                f"Small receive buffer: {self.system.rmem_max / 1024 / 1024:.1f} MB (recommend >= 16 MB)"
            )
            self.recommendations.append("Increase receive buffer: sysctl -w net.core.rmem_max=67108864")

        # Check connections with small cwnd
        small_cwnd_count = sum(1 for c in self.connections if c.cwnd < 10)
        if small_cwnd_count > 0:
            self.bottlenecks.append(
                f"{small_cwnd_count} connections with small congestion window (cwnd < 10)"
            )
            self.recommendations.append("Check for packet loss or network issues")

        # Check connections with high retransmits
        high_retrans_count = sum(1 for c in self.connections if c.retrans > 0)
        if high_retrans_count > len(self.connections) * 0.2:  # More than 20%
            self.bottlenecks.append(
                f"{high_retrans_count}/{len(self.connections)} connections have retransmits"
            )
            self.recommendations.append("Investigate network quality and buffer sizes")

        # Check for high RTT
        if self.connections:
            avg_rtt = sum(c.rtt for c in self.connections if c.rtt > 0) / max(
                sum(1 for c in self.connections if c.rtt > 0), 1
            )
            if avg_rtt > 100:  # > 100ms
                self.bottlenecks.append(f"High average RTT: {avg_rtt:.1f} ms")
                self.recommendations.append("Consider increasing buffer sizes for high-latency network")
                self.recommendations.append("Use BBR congestion control for better high-latency performance")

    def determine_severity(self) -> str:
        """Determine overall severity"""
        if not self.bottlenecks:
            return "low"

        # Critical conditions
        if self.metrics.retrans_rate > 5.0:
            return "critical"
        if self.system.window_scaling == 0:
            return "critical"

        # High severity
        if self.metrics.retrans_rate > 1.0:
            return "high"
        if self.system.sack == 0:
            return "high"

        # Medium severity
        if self.metrics.retrans_rate > 0.1:
            return "medium"
        if self.system.congestion_control not in ["bbr", "bbr2"]:
            return "medium"

        return "low"

    def calculate_bdp(self, bandwidth_mbps: float, rtt_ms: float) -> int:
        """Calculate Bandwidth-Delay Product"""
        # BDP = Bandwidth (bits/sec) × RTT (sec) / 8 (to get bytes)
        bandwidth_bps = bandwidth_mbps * 1e6
        rtt_sec = rtt_ms / 1000
        bdp_bytes = int((bandwidth_bps * rtt_sec) / 8)
        return bdp_bytes

    def generate_tuning_recommendation(self, bandwidth_mbps: Optional[float] = None,
                                     rtt_ms: Optional[float] = None) -> Dict[str, str]:
        """Generate specific tuning recommendations"""
        recommendations = {}

        if bandwidth_mbps and rtt_ms:
            bdp = self.calculate_bdp(bandwidth_mbps, rtt_ms)
            buffer_size = bdp * 2  # 2x BDP for safety

            recommendations["tcp_rmem"] = f"4096 131072 {buffer_size}"
            recommendations["tcp_wmem"] = f"4096 131072 {buffer_size}"
            recommendations["rmem_max"] = str(buffer_size)
            recommendations["wmem_max"] = str(buffer_size)

        # Always recommend BBR for better performance
        if self.system.congestion_control not in ["bbr", "bbr2"]:
            recommendations["tcp_congestion_control"] = "bbr"
            recommendations["default_qdisc"] = "fq"

        # Essential parameters
        if self.system.window_scaling == 0:
            recommendations["tcp_window_scaling"] = "1"
        if self.system.sack == 0:
            recommendations["tcp_sack"] = "1"
        if self.system.timestamps == 0:
            recommendations["tcp_timestamps"] = "1"

        return recommendations

    def analyze(self, bandwidth_mbps: Optional[float] = None,
               rtt_ms: Optional[float] = None) -> PerformanceAnalysis:
        """Run complete analysis"""
        self.log("Starting TCP performance analysis")

        # Collect data
        self.collect_system_info()
        self.collect_tcp_metrics()
        self.collect_connection_info()

        # Analyze
        self.analyze_performance()

        # Generate tuning recommendations
        if bandwidth_mbps and rtt_ms:
            tuning = self.generate_tuning_recommendation(bandwidth_mbps, rtt_ms)
            self.recommendations.append(f"Recommended buffer size for {bandwidth_mbps} Mbps, {rtt_ms} ms RTT:")
            for key, value in tuning.items():
                self.recommendations.append(f"  sysctl -w net.{key.replace('_', '.')}={value}")

        # Create analysis result
        analysis = PerformanceAnalysis(
            timestamp=datetime.utcnow().isoformat() + "Z",
            metrics=self.metrics,
            connections=self.connections,
            system=self.system,
            bottlenecks=self.bottlenecks,
            recommendations=list(set(self.recommendations)),  # Deduplicate
            severity=self.determine_severity()
        )

        return analysis


def format_output_text(analysis: PerformanceAnalysis) -> str:
    """Format analysis output as text"""
    lines = []

    lines.append("=" * 80)
    lines.append("TCP Performance Analysis Report")
    lines.append("=" * 80)
    lines.append(f"Timestamp: {analysis.timestamp}")
    lines.append(f"Severity: {analysis.severity.upper()}")
    lines.append("")

    # System configuration
    lines.append("System Configuration:")
    lines.append(f"  Congestion Control: {analysis.system.congestion_control}")
    lines.append(f"  Default Qdisc: {analysis.system.qdisc}")
    lines.append(f"  Window Scaling: {'Enabled' if analysis.system.window_scaling else 'Disabled'}")
    lines.append(f"  SACK: {'Enabled' if analysis.system.sack else 'Disabled'}")
    lines.append(f"  Timestamps: {'Enabled' if analysis.system.timestamps else 'Disabled'}")
    lines.append(f"  Receive Buffer Max: {analysis.system.rmem_max / 1024 / 1024:.1f} MB")
    lines.append(f"  Send Buffer Max: {analysis.system.wmem_max / 1024 / 1024:.1f} MB")
    lines.append("")

    # TCP metrics
    lines.append("TCP Metrics:")
    lines.append(f"  Established Connections: {analysis.metrics.curr_estab}")
    lines.append(f"  Active Opens: {analysis.metrics.active_opens}")
    lines.append(f"  Passive Opens: {analysis.metrics.passive_opens}")
    lines.append(f"  Segments In: {analysis.metrics.in_segs}")
    lines.append(f"  Segments Out: {analysis.metrics.out_segs}")
    lines.append(f"  Retransmitted Segments: {analysis.metrics.retrans_segs}")
    lines.append(f"  Retransmission Rate: {analysis.metrics.retrans_rate:.2f}%")
    lines.append(f"  Input Errors: {analysis.metrics.in_errs}")
    lines.append(f"  Error Rate: {analysis.metrics.error_rate:.4f}%")
    lines.append("")

    # Connection info
    if analysis.connections:
        lines.append(f"Active Connections (showing {len(analysis.connections)}):")
        for i, conn in enumerate(analysis.connections, 1):
            lines.append(f"  Connection {i}:")
            lines.append(f"    State: {conn.state}")
            lines.append(f"    Remote: {conn.remote_addr}")
            lines.append(f"    cwnd: {conn.cwnd}, ssthresh: {conn.ssthresh}")
            lines.append(f"    RTT: {conn.rtt:.2f} ms")
            lines.append(f"    Retransmits: {conn.retrans}")
            if conn.send_rate > 0:
                lines.append(f"    Send Rate: {conn.send_rate / 1e6:.2f} Mbps")
        lines.append("")

    # Bottlenecks
    if analysis.bottlenecks:
        lines.append("Identified Bottlenecks:")
        for bottleneck in analysis.bottlenecks:
            lines.append(f"  - {bottleneck}")
        lines.append("")

    # Recommendations
    if analysis.recommendations:
        lines.append("Recommendations:")
        for rec in analysis.recommendations:
            lines.append(f"  - {rec}")
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def format_output_json(analysis: PerformanceAnalysis) -> str:
    """Format analysis output as JSON"""
    # Convert dataclasses to dict
    data = {
        "timestamp": analysis.timestamp,
        "severity": analysis.severity,
        "system": asdict(analysis.system),
        "metrics": asdict(analysis.metrics),
        "connections": [asdict(c) for c in analysis.connections],
        "bottlenecks": analysis.bottlenecks,
        "recommendations": analysis.recommendations
    }

    return json.dumps(data, indent=2)


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Analyze TCP performance and provide tuning recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  sudo %(prog)s

  # Verbose output
  sudo %(prog)s --verbose

  # JSON output
  sudo %(prog)s --json

  # With network characteristics for BDP calculation
  sudo %(prog)s --bandwidth 10000 --rtt 100

  # Save report to file
  sudo %(prog)s --json > tcp_analysis.json
        """
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )

    parser.add_argument(
        "--bandwidth",
        type=float,
        help="Network bandwidth in Mbps (for BDP calculation)"
    )

    parser.add_argument(
        "--rtt",
        type=float,
        help="Round-trip time in milliseconds (for BDP calculation)"
    )

    parser.add_argument(
        "--connections",
        type=int,
        default=10,
        help="Number of connections to analyze (default: 10)"
    )

    args = parser.parse_args()

    # Check if running as root
    if subprocess.run(["id", "-u"], capture_output=True, text=True).stdout.strip() != "0":
        print("Warning: This script should be run as root for complete metrics", file=sys.stderr)

    # Run analysis
    analyzer = TCPAnalyzer(verbose=args.verbose)
    analysis = analyzer.analyze(bandwidth_mbps=args.bandwidth, rtt_ms=args.rtt)

    # Output results
    if args.json:
        print(format_output_json(analysis))
    else:
        print(format_output_text(analysis))

    # Return exit code based on severity
    severity_codes = {
        "low": 0,
        "medium": 1,
        "high": 2,
        "critical": 3
    }
    return severity_codes.get(analysis.severity, 0)


if __name__ == "__main__":
    sys.exit(main())
