#!/usr/bin/env python3
"""
Nginx Configuration Optimizer

Analyzes system resources and current Nginx configuration to recommend
optimized settings for better performance.

Usage:
    ./optimize_settings.py --help
    ./optimize_settings.py --current-config /etc/nginx/nginx.conf
    ./optimize_settings.py --current-config nginx.conf --json
    ./optimize_settings.py --traffic-profile high --json
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, List


@dataclass
class SystemResources:
    """System resource information"""
    cpu_cores: int
    total_memory_mb: int
    available_memory_mb: int
    disk_io_capable: bool = True


@dataclass
class TrafficProfile:
    """Traffic characteristics"""
    name: str
    requests_per_second: int
    avg_request_size_kb: int
    avg_response_size_kb: int
    concurrent_connections: int
    keepalive_ratio: float  # 0.0 to 1.0


@dataclass
class OptimizationRecommendation:
    """Single optimization recommendation"""
    directive: str
    current_value: Optional[str]
    recommended_value: str
    reason: str
    context: str  # events, http, server, etc.
    impact: str  # low, medium, high


@dataclass
class OptimizationResult:
    """Complete optimization results"""
    system_resources: SystemResources
    traffic_profile: TrafficProfile
    recommendations: List[OptimizationRecommendation]
    generated_config: str

    def to_dict(self):
        """Convert to dictionary for JSON output"""
        return {
            "system_resources": asdict(self.system_resources),
            "traffic_profile": asdict(self.traffic_profile),
            "recommendations": [asdict(r) for r in self.recommendations],
            "generated_config": self.generated_config
        }


class NginxOptimizer:
    """Optimizes Nginx configuration based on system resources and traffic"""

    # Predefined traffic profiles
    TRAFFIC_PROFILES = {
        "low": TrafficProfile(
            name="low",
            requests_per_second=100,
            avg_request_size_kb=4,
            avg_response_size_kb=50,
            concurrent_connections=500,
            keepalive_ratio=0.5
        ),
        "medium": TrafficProfile(
            name="medium",
            requests_per_second=1000,
            avg_request_size_kb=8,
            avg_response_size_kb=100,
            concurrent_connections=2000,
            keepalive_ratio=0.6
        ),
        "high": TrafficProfile(
            name="high",
            requests_per_second=10000,
            avg_request_size_kb=16,
            avg_response_size_kb=200,
            concurrent_connections=10000,
            keepalive_ratio=0.7
        ),
        "api": TrafficProfile(
            name="api",
            requests_per_second=5000,
            avg_request_size_kb=2,
            avg_response_size_kb=20,
            concurrent_connections=5000,
            keepalive_ratio=0.8
        ),
    }

    def __init__(self):
        self.current_config = {}

    def detect_system_resources(self) -> SystemResources:
        """Detect system resources"""
        cpu_cores = os.cpu_count() or 1

        try:
            # Try to get memory info on Linux
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                total_match = re.search(r'MemTotal:\s+(\d+)', meminfo)
                available_match = re.search(r'MemAvailable:\s+(\d+)', meminfo)

                total_mb = int(total_match.group(1)) // 1024 if total_match else 2048
                available_mb = int(available_match.group(1)) // 1024 if available_match else 1024
        except FileNotFoundError:
            # Fallback for non-Linux systems
            total_mb = 4096
            available_mb = 2048

        return SystemResources(
            cpu_cores=cpu_cores,
            total_memory_mb=total_mb,
            available_memory_mb=available_mb
        )

    def parse_current_config(self, config_path: Path):
        """Parse current configuration to extract values"""
        if not config_path.exists():
            return

        content = config_path.read_text()

        # Extract key directives
        patterns = {
            'worker_processes': r'worker_processes\s+(\w+);',
            'worker_connections': r'worker_connections\s+(\d+);',
            'worker_rlimit_nofile': r'worker_rlimit_nofile\s+(\d+);',
            'keepalive_timeout': r'keepalive_timeout\s+(\d+);',
            'keepalive_requests': r'keepalive_requests\s+(\d+);',
            'client_max_body_size': r'client_max_body_size\s+(\w+);',
            'client_body_buffer_size': r'client_body_buffer_size\s+(\w+);',
            'proxy_buffers': r'proxy_buffers\s+(\d+\s+\w+);',
            'gzip_comp_level': r'gzip_comp_level\s+(\d+);',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                self.current_config[key] = match.group(1)

    def optimize(self, system: SystemResources, traffic: TrafficProfile,
                 current_config_path: Optional[Path] = None) -> OptimizationResult:
        """Generate optimization recommendations"""

        if current_config_path:
            self.parse_current_config(current_config_path)

        recommendations = []

        # Worker processes
        current_workers = self.current_config.get('worker_processes', 'not set')
        recommended_workers = 'auto'
        recommendations.append(OptimizationRecommendation(
            directive='worker_processes',
            current_value=current_workers,
            recommended_value=recommended_workers,
            reason=f'Match CPU cores ({system.cpu_cores}) for optimal parallelism',
            context='main',
            impact='high'
        ))

        # Worker connections
        current_connections = self.current_config.get('worker_connections', 'not set')
        # Calculate based on traffic and memory
        connections_per_worker = min(
            traffic.concurrent_connections // system.cpu_cores,
            4096  # Reasonable upper limit
        )
        # Round to nearest power of 2
        connections_per_worker = 2 ** (connections_per_worker.bit_length() - 1)
        connections_per_worker = max(1024, connections_per_worker)  # Minimum 1024

        recommendations.append(OptimizationRecommendation(
            directive='worker_connections',
            current_value=current_connections,
            recommended_value=str(connections_per_worker),
            reason=f'Handle {traffic.concurrent_connections} concurrent connections across {system.cpu_cores} workers',
            context='events',
            impact='high'
        ))

        # Worker rlimit nofile
        current_rlimit = self.current_config.get('worker_rlimit_nofile', 'not set')
        recommended_rlimit = connections_per_worker * 2  # 2x connections for safety
        recommendations.append(OptimizationRecommendation(
            directive='worker_rlimit_nofile',
            current_value=current_rlimit,
            recommended_value=str(recommended_rlimit),
            reason='Allow enough file descriptors for connections (2x worker_connections)',
            context='main',
            impact='high'
        ))

        # Keepalive timeout
        current_keepalive = self.current_config.get('keepalive_timeout', 'not set')
        recommended_keepalive = 65 if traffic.keepalive_ratio > 0.6 else 30
        recommendations.append(OptimizationRecommendation(
            directive='keepalive_timeout',
            current_value=current_keepalive,
            recommended_value=str(recommended_keepalive),
            reason=f'Optimize for {int(traffic.keepalive_ratio * 100)}% keepalive connections',
            context='http',
            impact='medium'
        ))

        # Keepalive requests
        current_requests = self.current_config.get('keepalive_requests', 'not set')
        recommended_requests = 100 if traffic.keepalive_ratio > 0.6 else 50
        recommendations.append(OptimizationRecommendation(
            directive='keepalive_requests',
            current_value=current_requests,
            recommended_value=str(recommended_requests),
            reason='Balance connection reuse with resource cleanup',
            context='http',
            impact='medium'
        ))

        # Client body buffer size
        current_body_buffer = self.current_config.get('client_body_buffer_size', 'not set')
        recommended_body_buffer = f"{traffic.avg_request_size_kb}k"
        recommendations.append(OptimizationRecommendation(
            directive='client_body_buffer_size',
            current_value=current_body_buffer,
            recommended_value=recommended_body_buffer,
            reason=f'Match average request size ({traffic.avg_request_size_kb}KB)',
            context='http',
            impact='medium'
        ))

        # Proxy buffers (for reverse proxy)
        current_proxy_buffers = self.current_config.get('proxy_buffers', 'not set')
        buffer_size = max(4, traffic.avg_response_size_kb // 8)  # Divide into ~8 buffers
        recommended_proxy_buffers = f"8 {buffer_size}k"
        recommendations.append(OptimizationRecommendation(
            directive='proxy_buffers',
            current_value=current_proxy_buffers,
            recommended_value=recommended_proxy_buffers,
            reason=f'Efficiently buffer average response size ({traffic.avg_response_size_kb}KB)',
            context='http/location',
            impact='medium'
        ))

        # Gzip compression level
        current_gzip = self.current_config.get('gzip_comp_level', 'not set')
        # Higher traffic = lower compression level (CPU vs bandwidth trade-off)
        gzip_level = 4 if traffic.requests_per_second > 5000 else 6
        recommendations.append(OptimizationRecommendation(
            directive='gzip_comp_level',
            current_value=current_gzip,
            recommended_value=str(gzip_level),
            reason=f'Balance CPU usage with compression for {traffic.requests_per_second} req/s',
            context='http',
            impact='medium'
        ))

        # Upstream keepalive (for reverse proxy)
        upstream_keepalive = max(16, traffic.concurrent_connections // (system.cpu_cores * 10))
        recommendations.append(OptimizationRecommendation(
            directive='keepalive',
            current_value='not set',
            recommended_value=str(upstream_keepalive),
            reason='Reuse backend connections for better performance',
            context='upstream',
            impact='high'
        ))

        # Multi-accept
        recommendations.append(OptimizationRecommendation(
            directive='multi_accept',
            current_value='not set',
            recommended_value='on',
            reason='Accept multiple connections at once for better throughput',
            context='events',
            impact='medium'
        ))

        # Use epoll (Linux) or kqueue (BSD)
        use_method = 'epoll'  # Assuming Linux
        recommendations.append(OptimizationRecommendation(
            directive='use',
            current_value='not set',
            recommended_value=use_method,
            reason='Use efficient event notification mechanism',
            context='events',
            impact='medium'
        ))

        # Generate optimized configuration
        generated_config = self._generate_config(system, traffic, recommendations)

        return OptimizationResult(
            system_resources=system,
            traffic_profile=traffic,
            recommendations=recommendations,
            generated_config=generated_config
        )

    def _generate_config(self, system: SystemResources, traffic: TrafficProfile,
                         recommendations: List[OptimizationRecommendation]) -> str:
        """Generate optimized Nginx configuration"""

        # Extract recommendations by context
        rec_dict = {}
        for rec in recommendations:
            rec_dict[rec.directive] = rec.recommended_value

        config = f"""# Optimized Nginx Configuration
# Generated for: {traffic.name} traffic profile
# System: {system.cpu_cores} CPU cores, {system.total_memory_mb}MB RAM
# Traffic: {traffic.requests_per_second} req/s, {traffic.concurrent_connections} concurrent connections

user nginx;
worker_processes {rec_dict.get('worker_processes', 'auto')};
worker_rlimit_nofile {rec_dict.get('worker_rlimit_nofile', '65535')};
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {{
    worker_connections {rec_dict.get('worker_connections', '4096')};
    use {rec_dict.get('use', 'epoll')};
    multi_accept {rec_dict.get('multi_accept', 'on')};
}}

http {{
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log main buffer=32k flush=1m;

    # Performance optimizations
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout {rec_dict.get('keepalive_timeout', '65')};
    keepalive_requests {rec_dict.get('keepalive_requests', '100')};
    types_hash_max_size 2048;
    server_tokens off;

    # Client settings
    client_max_body_size 10m;
    client_body_buffer_size {rec_dict.get('client_body_buffer_size', '16k')};
    client_header_buffer_size 1k;
    large_client_header_buffers 4 16k;

    # Timeouts
    client_body_timeout 12s;
    client_header_timeout 12s;
    send_timeout 10s;
    reset_timedout_connection on;

    # Compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level {rec_dict.get('gzip_comp_level', '6')};
    gzip_min_length 1000;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml font/truetype font/opentype
               application/vnd.ms-fontobject image/svg+xml;

    # File cache
    open_file_cache max=10000 inactive=30s;
    open_file_cache_valid 60s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    # Proxy settings (for reverse proxy use)
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers {rec_dict.get('proxy_buffers', '8 4k')};
    proxy_busy_buffers_size 16k;
    proxy_connect_timeout 5s;
    proxy_send_timeout 10s;
    proxy_read_timeout 30s;

    # Example upstream with keepalive
    # upstream backend {{
    #     server backend1.internal:8080;
    #     server backend2.internal:8080;
    #     keepalive {rec_dict.get('keepalive', '32')};
    # }}

    # Include virtual hosts
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}}
"""
        return config


def format_output(result: OptimizationResult, json_output: bool = False) -> str:
    """Format optimization results"""
    if json_output:
        return json.dumps(result.to_dict(), indent=2)

    output = []
    output.append(f"\n{'='*70}")
    output.append("Nginx Configuration Optimization Recommendations")
    output.append(f"{'='*70}\n")

    # System information
    output.append("System Resources:")
    output.append(f"  CPU Cores: {result.system_resources.cpu_cores}")
    output.append(f"  Total Memory: {result.system_resources.total_memory_mb} MB")
    output.append(f"  Available Memory: {result.system_resources.available_memory_mb} MB")
    output.append("")

    # Traffic profile
    output.append(f"Traffic Profile: {result.traffic_profile.name}")
    output.append(f"  Requests/sec: {result.traffic_profile.requests_per_second}")
    output.append(f"  Concurrent Connections: {result.traffic_profile.concurrent_connections}")
    output.append(f"  Avg Request Size: {result.traffic_profile.avg_request_size_kb} KB")
    output.append(f"  Avg Response Size: {result.traffic_profile.avg_response_size_kb} KB")
    output.append(f"  Keepalive Ratio: {int(result.traffic_profile.keepalive_ratio * 100)}%")
    output.append("")

    # Recommendations by impact
    high_impact = [r for r in result.recommendations if r.impact == 'high']
    medium_impact = [r for r in result.recommendations if r.impact == 'medium']
    low_impact = [r for r in result.recommendations if r.impact == 'low']

    if high_impact:
        output.append("HIGH IMPACT RECOMMENDATIONS:")
        output.append("-" * 70)
        for rec in high_impact:
            output.append(f"  {rec.directive} ({rec.context})")
            output.append(f"    Current: {rec.current_value}")
            output.append(f"    Recommended: {rec.recommended_value}")
            output.append(f"    Reason: {rec.reason}")
            output.append("")

    if medium_impact:
        output.append("MEDIUM IMPACT RECOMMENDATIONS:")
        output.append("-" * 70)
        for rec in medium_impact:
            output.append(f"  {rec.directive} ({rec.context})")
            output.append(f"    Current: {rec.current_value}")
            output.append(f"    Recommended: {rec.recommended_value}")
            output.append(f"    Reason: {rec.reason}")
            output.append("")

    if low_impact:
        output.append("LOW IMPACT RECOMMENDATIONS:")
        output.append("-" * 70)
        for rec in low_impact:
            output.append(f"  {rec.directive} ({rec.context})")
            output.append(f"    Current: {rec.current_value}")
            output.append(f"    Recommended: {rec.recommended_value}")
            output.append(f"    Reason: {rec.reason}")
            output.append("")

    output.append("=" * 70)
    output.append("GENERATED OPTIMIZED CONFIGURATION:")
    output.append("=" * 70)
    output.append("")
    output.append(result.generated_config)

    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Optimize Nginx configuration based on system resources and traffic profile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Traffic Profiles:
  low     - ~100 req/s, 500 concurrent connections
  medium  - ~1,000 req/s, 2,000 concurrent connections
  high    - ~10,000 req/s, 10,000 concurrent connections
  api     - ~5,000 req/s, 5,000 concurrent connections (optimized for APIs)

Examples:
  # Optimize for high traffic
  %(prog)s --traffic-profile high

  # Analyze current config and optimize
  %(prog)s --current-config /etc/nginx/nginx.conf --traffic-profile medium

  # Generate JSON output
  %(prog)s --traffic-profile api --json

  # Save optimized configuration
  %(prog)s --traffic-profile high > nginx-optimized.conf
        """
    )

    parser.add_argument(
        '--current-config',
        type=Path,
        help='Path to current Nginx configuration file (optional)'
    )

    parser.add_argument(
        '--traffic-profile',
        choices=['low', 'medium', 'high', 'api'],
        default='medium',
        help='Expected traffic profile (default: medium)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )

    args = parser.parse_args()

    # Initialize optimizer
    optimizer = NginxOptimizer()

    # Detect system resources
    system = optimizer.detect_system_resources()

    # Get traffic profile
    traffic = optimizer.TRAFFIC_PROFILES[args.traffic_profile]

    # Generate recommendations
    result = optimizer.optimize(system, traffic, args.current_config)

    # Output results
    output = format_output(result, json_output=args.json)
    print(output)

    sys.exit(0)


if __name__ == '__main__':
    main()
