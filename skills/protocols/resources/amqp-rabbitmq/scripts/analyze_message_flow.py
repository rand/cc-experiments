#!/usr/bin/env python3
"""
RabbitMQ Message Flow Analyzer

Traces message routing, analyzes exchange bindings, detects routing loops,
measures throughput, and identifies bottlenecks.

Usage:
    ./analyze_message_flow.py --url amqp://localhost
    ./analyze_message_flow.py --url amqp://localhost --exchange logs --routing-key error
    ./analyze_message_flow.py --url amqp://localhost --detect-loops --json
    ./analyze_message_flow.py --url amqp://localhost --measure-throughput --duration 60
    ./analyze_message_flow.py --help
"""

import argparse
import json
import sys
import logging
import time
from typing import Dict, List, Any, Set, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
import requests
from urllib.parse import urlparse, quote


@dataclass
class BindingInfo:
    """Information about a binding."""
    source: str
    destination: str
    destination_type: str
    routing_key: str
    arguments: Dict[str, Any]

    def __hash__(self):
        return hash((self.source, self.destination, self.routing_key))


@dataclass
class RouteResult:
    """Result of message routing analysis."""
    exchange: str
    routing_key: str
    matched_queues: List[str]
    matched_exchanges: List[str]
    routing_path: List[str]
    is_routable: bool
    potential_loops: List[List[str]]


@dataclass
class ThroughputMetrics:
    """Throughput metrics for a queue."""
    queue_name: str
    publish_rate: float
    deliver_rate: float
    ack_rate: float
    messages_ready: int
    messages_unacknowledged: int
    consumers: int
    backlog_growth_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BottleneckAnalysis:
    """Bottleneck analysis result."""
    queue_name: str
    bottleneck_type: str
    severity: str
    description: str
    metrics: Dict[str, Any]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FlowAnalysisReport:
    """Complete flow analysis report."""
    broker_url: str
    vhost: str
    analysis_type: str
    timestamp: float
    routing_analysis: Optional[List[RouteResult]] = None
    loop_detection: Optional[List[List[str]]] = None
    throughput_metrics: Optional[List[ThroughputMetrics]] = None
    bottleneck_analysis: Optional[List[BottleneckAnalysis]] = None
    topology_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'broker_url': self.broker_url,
            'vhost': self.vhost,
            'analysis_type': self.analysis_type,
            'timestamp': self.timestamp,
        }
        if self.routing_analysis:
            result['routing_analysis'] = [asdict(r) for r in self.routing_analysis]
        if self.loop_detection:
            result['loop_detection'] = self.loop_detection
        if self.throughput_metrics:
            result['throughput_metrics'] = [m.to_dict() for m in self.throughput_metrics]
        if self.bottleneck_analysis:
            result['bottleneck_analysis'] = [b.to_dict() for b in self.bottleneck_analysis]
        if self.topology_summary:
            result['topology_summary'] = self.topology_summary
        return result


class MessageFlowAnalyzer:
    """Analyzes RabbitMQ message flow."""

    def __init__(
        self,
        management_url: str,
        username: str,
        password: str,
        vhost: str = "/"
    ):
        """
        Initialize analyzer.

        Args:
            management_url: RabbitMQ management API URL
            username: RabbitMQ username
            password: RabbitMQ password
            vhost: Virtual host to analyze
        """
        self.management_url = management_url.rstrip('/')
        self.username = username
        self.password = password
        self.vhost = vhost
        self.logger = logging.getLogger(__name__)

        # Cached topology
        self.exchanges: Dict[str, Dict[str, Any]] = {}
        self.queues: Dict[str, Dict[str, Any]] = {}
        self.bindings: List[BindingInfo] = []

    def get(self, endpoint: str) -> Optional[Any]:
        """
        Make GET request to management API.

        Args:
            endpoint: API endpoint

        Returns:
            Response JSON or None on error
        """
        url = f"{self.management_url}{endpoint}"
        try:
            response = requests.get(
                url,
                auth=(self.username, self.password),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return None

    def load_topology(self) -> None:
        """Load broker topology."""
        vhost_encoded = quote(self.vhost, safe='')

        # Load exchanges
        exchanges = self.get(f'/api/exchanges/{vhost_encoded}') or []
        self.exchanges = {ex['name']: ex for ex in exchanges}

        # Load queues
        queues = self.get(f'/api/queues/{vhost_encoded}') or []
        self.queues = {q['name']: q for q in queues}

        # Load bindings
        bindings = self.get(f'/api/bindings/{vhost_encoded}') or []
        self.bindings = [
            BindingInfo(
                source=b.get('source', ''),
                destination=b.get('destination', ''),
                destination_type=b.get('destination_type', 'queue'),
                routing_key=b.get('routing_key', ''),
                arguments=b.get('arguments', {})
            )
            for b in bindings
        ]

        self.logger.info(
            f"Loaded topology: {len(self.exchanges)} exchanges, "
            f"{len(self.queues)} queues, {len(self.bindings)} bindings"
        )

    def match_routing_key(
        self,
        pattern: str,
        routing_key: str,
        exchange_type: str
    ) -> bool:
        """
        Check if routing key matches pattern.

        Args:
            pattern: Binding pattern
            routing_key: Message routing key
            exchange_type: Exchange type

        Returns:
            True if matches
        """
        if exchange_type == 'fanout':
            return True
        elif exchange_type == 'direct':
            return pattern == routing_key
        elif exchange_type == 'topic':
            return self._match_topic(pattern, routing_key)
        elif exchange_type == 'headers':
            # Headers exchange requires header matching (not supported here)
            return False
        return False

    def _match_topic(self, pattern: str, routing_key: str) -> bool:
        """
        Match topic pattern.

        Args:
            pattern: Topic pattern with * and #
            routing_key: Routing key

        Returns:
            True if matches
        """
        pattern_parts = pattern.split('.')
        key_parts = routing_key.split('.')

        def match_parts(p_parts: List[str], k_parts: List[str]) -> bool:
            if not p_parts and not k_parts:
                return True
            if not p_parts:
                return False
            if not k_parts:
                return len(p_parts) == 1 and p_parts[0] == '#'

            p = p_parts[0]
            k = k_parts[0]

            if p == '#':
                # # matches zero or more words
                for i in range(len(k_parts) + 1):
                    if match_parts(p_parts[1:], k_parts[i:]):
                        return True
                return False
            elif p == '*':
                # * matches exactly one word
                return match_parts(p_parts[1:], k_parts[1:])
            elif p == k:
                return match_parts(p_parts[1:], k_parts[1:])
            else:
                return False

        return match_parts(pattern_parts, key_parts)

    def trace_routing(
        self,
        exchange: str,
        routing_key: str,
        visited: Optional[Set[str]] = None
    ) -> RouteResult:
        """
        Trace message routing from exchange.

        Args:
            exchange: Source exchange name
            routing_key: Message routing key
            visited: Set of visited exchanges (for loop detection)

        Returns:
            Routing result
        """
        if visited is None:
            visited = set()

        if exchange in visited:
            # Loop detected
            return RouteResult(
                exchange=exchange,
                routing_key=routing_key,
                matched_queues=[],
                matched_exchanges=[],
                routing_path=list(visited) + [exchange],
                is_routable=False,
                potential_loops=[list(visited) + [exchange]]
            )

        visited = visited | {exchange}

        matched_queues = []
        matched_exchanges = []
        routing_path = [exchange]
        potential_loops = []

        # Get exchange info
        ex_info = self.exchanges.get(exchange, {})
        ex_type = ex_info.get('type', 'direct')

        # Find matching bindings
        for binding in self.bindings:
            if binding.source != exchange:
                continue

            # Check if routing key matches
            if self.match_routing_key(binding.routing_key, routing_key, ex_type):
                if binding.destination_type == 'queue':
                    matched_queues.append(binding.destination)
                    routing_path.append(f"queue:{binding.destination}")
                elif binding.destination_type == 'exchange':
                    matched_exchanges.append(binding.destination)
                    # Recursively trace exchange-to-exchange
                    sub_result = self.trace_routing(
                        binding.destination,
                        routing_key,
                        visited
                    )
                    matched_queues.extend(sub_result.matched_queues)
                    matched_exchanges.extend(sub_result.matched_exchanges)
                    routing_path.extend(sub_result.routing_path[1:])
                    potential_loops.extend(sub_result.potential_loops)

        is_routable = len(matched_queues) > 0

        return RouteResult(
            exchange=exchange,
            routing_key=routing_key,
            matched_queues=list(set(matched_queues)),
            matched_exchanges=list(set(matched_exchanges)),
            routing_path=routing_path,
            is_routable=is_routable,
            potential_loops=potential_loops
        )

    def detect_routing_loops(self) -> List[List[str]]:
        """
        Detect routing loops in exchange-to-exchange bindings.

        Returns:
            List of routing loops (each loop is a list of exchange names)
        """
        loops = []

        # Build exchange graph
        graph: Dict[str, List[str]] = defaultdict(list)
        for binding in self.bindings:
            if binding.destination_type == 'exchange':
                graph[binding.source].append(binding.destination)

        # DFS to detect cycles
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Cycle detected
                    cycle_start = path.index(neighbor)
                    loop = path[cycle_start:] + [neighbor]
                    if loop not in loops:
                        loops.append(loop)

            path.pop()
            rec_stack.remove(node)

        for exchange in graph.keys():
            if exchange not in visited:
                dfs(exchange, [])

        return loops

    def measure_throughput(self, duration: int = 60) -> List[ThroughputMetrics]:
        """
        Measure queue throughput over duration.

        Args:
            duration: Measurement duration in seconds

        Returns:
            List of throughput metrics
        """
        self.logger.info(f"Measuring throughput for {duration} seconds...")

        # Initial snapshot
        initial_snapshot = {}
        for queue_name, queue_info in self.queues.items():
            stats = queue_info.get('message_stats', {})
            initial_snapshot[queue_name] = {
                'publish': stats.get('publish', 0),
                'deliver_get': stats.get('deliver_get', 0),
                'ack': stats.get('ack', 0),
                'messages': queue_info.get('messages', 0),
                'timestamp': time.time()
            }

        # Wait
        time.sleep(duration)

        # Reload topology
        self.load_topology()

        # Final snapshot
        metrics = []
        for queue_name, queue_info in self.queues.items():
            if queue_name not in initial_snapshot:
                continue

            initial = initial_snapshot[queue_name]
            stats = queue_info.get('message_stats', {})

            time_elapsed = time.time() - initial['timestamp']

            publish_total = stats.get('publish', 0)
            deliver_total = stats.get('deliver_get', 0)
            ack_total = stats.get('ack', 0)

            publish_delta = max(0, publish_total - initial['publish'])
            deliver_delta = max(0, deliver_total - initial['deliver_get'])
            ack_delta = max(0, ack_total - initial['ack'])

            publish_rate = publish_delta / time_elapsed
            deliver_rate = deliver_delta / time_elapsed
            ack_rate = ack_delta / time_elapsed

            messages_now = queue_info.get('messages', 0)
            messages_initial = initial['messages']
            backlog_growth = messages_now - messages_initial
            backlog_growth_rate = backlog_growth / time_elapsed

            metrics.append(ThroughputMetrics(
                queue_name=queue_name,
                publish_rate=round(publish_rate, 2),
                deliver_rate=round(deliver_rate, 2),
                ack_rate=round(ack_rate, 2),
                messages_ready=queue_info.get('messages_ready', 0),
                messages_unacknowledged=queue_info.get('messages_unacknowledged', 0),
                consumers=queue_info.get('consumers', 0),
                backlog_growth_rate=round(backlog_growth_rate, 2)
            ))

        return metrics

    def identify_bottlenecks(
        self,
        throughput_metrics: Optional[List[ThroughputMetrics]] = None
    ) -> List[BottleneckAnalysis]:
        """
        Identify bottlenecks in message flow.

        Args:
            throughput_metrics: Optional throughput metrics (will measure if not provided)

        Returns:
            List of bottleneck analyses
        """
        if throughput_metrics is None:
            throughput_metrics = self.measure_throughput(duration=30)

        bottlenecks = []

        for metric in throughput_metrics:
            recommendations = []

            # Check for backlog growth
            if metric.backlog_growth_rate > 10:
                bottlenecks.append(BottleneckAnalysis(
                    queue_name=metric.queue_name,
                    bottleneck_type='backlog_growth',
                    severity='high',
                    description=f'Queue backlog growing at {metric.backlog_growth_rate:.1f} msg/s',
                    metrics={
                        'backlog_growth_rate': metric.backlog_growth_rate,
                        'publish_rate': metric.publish_rate,
                        'deliver_rate': metric.deliver_rate
                    },
                    recommendations=[
                        'Increase consumer count',
                        'Optimize consumer processing',
                        'Check consumer errors/redeliveries'
                    ]
                ))

            # Check for publish > deliver
            if metric.publish_rate > metric.deliver_rate * 1.5:
                bottlenecks.append(BottleneckAnalysis(
                    queue_name=metric.queue_name,
                    bottleneck_type='slow_consumers',
                    severity='high',
                    description=f'Publish rate ({metric.publish_rate:.1f} msg/s) exceeds deliver rate ({metric.deliver_rate:.1f} msg/s)',
                    metrics={
                        'publish_rate': metric.publish_rate,
                        'deliver_rate': metric.deliver_rate,
                        'ratio': metric.publish_rate / max(metric.deliver_rate, 0.1)
                    },
                    recommendations=[
                        'Scale consumers horizontally',
                        'Increase prefetch_count',
                        'Optimize message processing'
                    ]
                ))

            # Check for no consumers
            if metric.consumers == 0 and metric.messages_ready > 0:
                bottlenecks.append(BottleneckAnalysis(
                    queue_name=metric.queue_name,
                    bottleneck_type='no_consumers',
                    severity='critical',
                    description=f'Queue has {metric.messages_ready} messages but no consumers',
                    metrics={
                        'messages_ready': metric.messages_ready,
                        'consumers': 0
                    },
                    recommendations=[
                        'Start consumers',
                        'Check if queue is still needed',
                        'Consider auto-delete or TTL'
                    ]
                ))

            # Check for high unacked
            if metric.messages_unacknowledged > 1000:
                bottlenecks.append(BottleneckAnalysis(
                    queue_name=metric.queue_name,
                    bottleneck_type='high_unacked',
                    severity='medium',
                    description=f'High unacknowledged messages ({metric.messages_unacknowledged})',
                    metrics={
                        'messages_unacknowledged': metric.messages_unacknowledged,
                        'ack_rate': metric.ack_rate
                    },
                    recommendations=[
                        'Reduce prefetch_count',
                        'Check consumer processing time',
                        'Investigate consumer hangs'
                    ]
                ))

            # Check for deliver > ack (redeliveries)
            if metric.deliver_rate > metric.ack_rate * 1.2:
                bottlenecks.append(BottleneckAnalysis(
                    queue_name=metric.queue_name,
                    bottleneck_type='high_redelivery',
                    severity='medium',
                    description=f'Deliver rate ({metric.deliver_rate:.1f}) exceeds ack rate ({metric.ack_rate:.1f}), indicating redeliveries',
                    metrics={
                        'deliver_rate': metric.deliver_rate,
                        'ack_rate': metric.ack_rate,
                        'redelivery_ratio': (metric.deliver_rate - metric.ack_rate) / max(metric.deliver_rate, 0.1)
                    },
                    recommendations=[
                        'Investigate consumer errors',
                        'Check consumer connection stability',
                        'Review error handling logic'
                    ]
                ))

        return bottlenecks

    def analyze_topology(self) -> Dict[str, Any]:
        """
        Analyze broker topology.

        Returns:
            Topology summary
        """
        # Exchange type distribution
        exchange_types = defaultdict(int)
        for ex in self.exchanges.values():
            ex_type = ex.get('type', 'unknown')
            exchange_types[ex_type] += 1

        # Queue type distribution
        queue_types = defaultdict(int)
        for q in self.queues.values():
            args = q.get('arguments', {})
            q_type = args.get('x-queue-type', 'classic')
            queue_types[q_type] += 1

        # Binding statistics
        queue_bindings = sum(1 for b in self.bindings if b.destination_type == 'queue')
        exchange_bindings = sum(1 for b in self.bindings if b.destination_type == 'exchange')

        # Durable vs non-durable
        durable_exchanges = sum(1 for ex in self.exchanges.values() if ex.get('durable', False))
        durable_queues = sum(1 for q in self.queues.values() if q.get('durable', False))

        # Messages
        total_messages = sum(q.get('messages', 0) for q in self.queues.values())
        total_ready = sum(q.get('messages_ready', 0) for q in self.queues.values())
        total_unacked = sum(q.get('messages_unacknowledged', 0) for q in self.queues.values())

        # Consumers
        total_consumers = sum(q.get('consumers', 0) for q in self.queues.values())

        return {
            'exchanges': {
                'total': len(self.exchanges),
                'by_type': dict(exchange_types),
                'durable': durable_exchanges,
                'non_durable': len(self.exchanges) - durable_exchanges
            },
            'queues': {
                'total': len(self.queues),
                'by_type': dict(queue_types),
                'durable': durable_queues,
                'non_durable': len(self.queues) - durable_queues
            },
            'bindings': {
                'total': len(self.bindings),
                'queue_bindings': queue_bindings,
                'exchange_bindings': exchange_bindings
            },
            'messages': {
                'total': total_messages,
                'ready': total_ready,
                'unacknowledged': total_unacked
            },
            'consumers': {
                'total': total_consumers
            }
        }


def parse_amqp_url(url: str) -> Tuple[str, str, str, str]:
    """
    Parse AMQP URL.

    Args:
        url: AMQP URL

    Returns:
        Tuple of (management_url, username, password, vhost)
    """
    parsed = urlparse(url)

    username = parsed.username or 'guest'
    password = parsed.password or 'guest'
    host = parsed.hostname or 'localhost'
    management_url = f"http://{host}:15672"
    vhost = parsed.path.lstrip('/') or '/'

    return management_url, username, password, vhost


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze RabbitMQ message flow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze topology
  %(prog)s --url amqp://localhost

  # Trace message routing
  %(prog)s --url amqp://localhost --exchange logs --routing-key error

  # Detect routing loops
  %(prog)s --url amqp://localhost --detect-loops

  # Measure throughput
  %(prog)s --url amqp://localhost --measure-throughput --duration 60

  # Identify bottlenecks
  %(prog)s --url amqp://localhost --identify-bottlenecks

  # Full analysis (JSON output)
  %(prog)s --url amqp://localhost --full-analysis --json
        """
    )

    parser.add_argument(
        '--url',
        required=True,
        help='AMQP broker URL'
    )
    parser.add_argument(
        '--vhost',
        help='Virtual host (default: from URL or /)'
    )
    parser.add_argument(
        '--management-url',
        help='Management API URL (default: inferred)'
    )
    parser.add_argument(
        '--exchange',
        help='Exchange name for routing analysis'
    )
    parser.add_argument(
        '--routing-key',
        help='Routing key for routing analysis'
    )
    parser.add_argument(
        '--detect-loops',
        action='store_true',
        help='Detect routing loops'
    )
    parser.add_argument(
        '--measure-throughput',
        action='store_true',
        help='Measure queue throughput'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Measurement duration in seconds (default: 60)'
    )
    parser.add_argument(
        '--identify-bottlenecks',
        action='store_true',
        help='Identify bottlenecks'
    )
    parser.add_argument(
        '--full-analysis',
        action='store_true',
        help='Run full analysis (all checks)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output JSON format'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Parse URL
    management_url, username, password, vhost = parse_amqp_url(args.url)

    if args.management_url:
        management_url = args.management_url
    if args.vhost:
        vhost = args.vhost

    # Create analyzer
    analyzer = MessageFlowAnalyzer(
        management_url=management_url,
        username=username,
        password=password,
        vhost=vhost
    )

    # Load topology
    analyzer.load_topology()

    # Determine analysis type
    analysis_type = 'topology'
    routing_analysis = None
    loop_detection = None
    throughput_metrics = None
    bottleneck_analysis = None
    topology_summary = None

    if args.full_analysis:
        analysis_type = 'full'
        # Run all analyses
        topology_summary = analyzer.analyze_topology()
        loop_detection = analyzer.detect_routing_loops()
        throughput_metrics = analyzer.measure_throughput(args.duration)
        bottleneck_analysis = analyzer.identify_bottlenecks(throughput_metrics)

    else:
        # Individual analyses
        if args.exchange and args.routing_key:
            analysis_type = 'routing'
            result = analyzer.trace_routing(args.exchange, args.routing_key)
            routing_analysis = [result]

        if args.detect_loops:
            analysis_type = 'loops'
            loop_detection = analyzer.detect_routing_loops()

        if args.measure_throughput:
            analysis_type = 'throughput'
            throughput_metrics = analyzer.measure_throughput(args.duration)

        if args.identify_bottlenecks:
            analysis_type = 'bottlenecks'
            bottleneck_analysis = analyzer.identify_bottlenecks()

        # Default: topology analysis
        if not any([
            args.exchange,
            args.detect_loops,
            args.measure_throughput,
            args.identify_bottlenecks
        ]):
            topology_summary = analyzer.analyze_topology()

    # Create report
    report = FlowAnalysisReport(
        broker_url=management_url,
        vhost=vhost,
        analysis_type=analysis_type,
        timestamp=time.time(),
        routing_analysis=routing_analysis,
        loop_detection=loop_detection,
        throughput_metrics=throughput_metrics,
        bottleneck_analysis=bottleneck_analysis,
        topology_summary=topology_summary
    )

    # Output results
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        # Human-readable output
        print(f"\n{'='*80}")
        print(f"RabbitMQ Message Flow Analysis")
        print(f"{'='*80}")
        print(f"Broker: {report.broker_url}")
        print(f"VHost: {report.vhost}")
        print(f"Analysis Type: {report.analysis_type}")

        if topology_summary:
            print(f"\n{'='*80}")
            print("Topology Summary")
            print(f"{'='*80}")
            print(f"\nExchanges:")
            print(f"  Total: {topology_summary['exchanges']['total']}")
            print(f"  By Type: {topology_summary['exchanges']['by_type']}")
            print(f"  Durable: {topology_summary['exchanges']['durable']}")

            print(f"\nQueues:")
            print(f"  Total: {topology_summary['queues']['total']}")
            print(f"  By Type: {topology_summary['queues']['by_type']}")
            print(f"  Durable: {topology_summary['queues']['durable']}")

            print(f"\nBindings:")
            print(f"  Total: {topology_summary['bindings']['total']}")
            print(f"  Queue Bindings: {topology_summary['bindings']['queue_bindings']}")
            print(f"  Exchange Bindings: {topology_summary['bindings']['exchange_bindings']}")

            print(f"\nMessages:")
            print(f"  Total: {topology_summary['messages']['total']:,}")
            print(f"  Ready: {topology_summary['messages']['ready']:,}")
            print(f"  Unacknowledged: {topology_summary['messages']['unacknowledged']:,}")

            print(f"\nConsumers:")
            print(f"  Total: {topology_summary['consumers']['total']}")

        if routing_analysis:
            print(f"\n{'='*80}")
            print("Routing Analysis")
            print(f"{'='*80}")
            for result in routing_analysis:
                print(f"\nExchange: {result.exchange}")
                print(f"Routing Key: {result.routing_key}")
                print(f"Routable: {result.is_routable}")
                print(f"Matched Queues: {result.matched_queues}")
                if result.matched_exchanges:
                    print(f"Matched Exchanges: {result.matched_exchanges}")
                print(f"Routing Path: {' -> '.join(result.routing_path)}")
                if result.potential_loops:
                    print(f"WARNING: Potential routing loops detected!")
                    for loop in result.potential_loops:
                        print(f"  Loop: {' -> '.join(loop)}")

        if loop_detection:
            print(f"\n{'='*80}")
            print("Routing Loop Detection")
            print(f"{'='*80}")
            if loop_detection:
                print(f"\nFound {len(loop_detection)} routing loop(s):")
                for i, loop in enumerate(loop_detection, 1):
                    print(f"\nLoop {i}: {' -> '.join(loop)}")
            else:
                print("\nNo routing loops detected.")

        if throughput_metrics:
            print(f"\n{'='*80}")
            print("Throughput Metrics")
            print(f"{'='*80}")
            print(f"\n{'Queue':<40} {'Pub/s':>10} {'Del/s':>10} {'Ack/s':>10} {'Ready':>10} {'Unack':>10} {'Cons':>6} {'Growth':>10}")
            print("-" * 126)
            for metric in sorted(throughput_metrics, key=lambda m: m.publish_rate, reverse=True):
                print(
                    f"{metric.queue_name:<40} "
                    f"{metric.publish_rate:>10.2f} "
                    f"{metric.deliver_rate:>10.2f} "
                    f"{metric.ack_rate:>10.2f} "
                    f"{metric.messages_ready:>10,} "
                    f"{metric.messages_unacknowledged:>10,} "
                    f"{metric.consumers:>6} "
                    f"{metric.backlog_growth_rate:>10.2f}"
                )

        if bottleneck_analysis:
            print(f"\n{'='*80}")
            print("Bottleneck Analysis")
            print(f"{'='*80}")
            if bottleneck_analysis:
                print(f"\nFound {len(bottleneck_analysis)} bottleneck(s):")
                for i, bottleneck in enumerate(bottleneck_analysis, 1):
                    print(f"\n[{bottleneck.severity.upper()}] {bottleneck.queue_name}")
                    print(f"  Type: {bottleneck.bottleneck_type}")
                    print(f"  Description: {bottleneck.description}")
                    print(f"  Metrics: {json.dumps(bottleneck.metrics)}")
                    print(f"  Recommendations:")
                    for rec in bottleneck.recommendations:
                        print(f"    - {rec}")
            else:
                print("\nNo bottlenecks detected.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
