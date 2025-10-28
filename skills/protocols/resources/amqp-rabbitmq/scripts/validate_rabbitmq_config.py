#!/usr/bin/env python3
"""
RabbitMQ Configuration Validator

Validates RabbitMQ broker configurations, queue/exchange settings, policies,
detects anti-patterns, and validates virtual hosts.

Usage:
    ./validate_rabbitmq_config.py --url amqp://localhost
    ./validate_rabbitmq_config.py --url amqp://localhost --vhost myapp --json
    ./validate_rabbitmq_config.py --url amqp://localhost --check-policies
    ./validate_rabbitmq_config.py --help
"""

import argparse
import json
import sys
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from urllib.parse import urlparse, quote


class Severity(Enum):
    """Issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: str
    category: str
    resource_type: str
    resource_name: str
    message: str
    recommendation: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        return result


@dataclass
class ValidationReport:
    """Complete validation report."""
    broker_url: str
    vhost: str
    total_issues: int
    critical_count: int
    error_count: int
    warning_count: int
    info_count: int
    issues: List[ValidationIssue]
    queues_checked: int
    exchanges_checked: int
    bindings_checked: int
    policies_checked: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'broker_url': self.broker_url,
            'vhost': self.vhost,
            'summary': {
                'total_issues': self.total_issues,
                'critical': self.critical_count,
                'error': self.error_count,
                'warning': self.warning_count,
                'info': self.info_count,
            },
            'resources_checked': {
                'queues': self.queues_checked,
                'exchanges': self.exchanges_checked,
                'bindings': self.bindings_checked,
                'policies': self.policies_checked,
            },
            'issues': [issue.to_dict() for issue in self.issues]
        }


class RabbitMQValidator:
    """Validates RabbitMQ configuration."""

    def __init__(
        self,
        management_url: str,
        username: str,
        password: str,
        vhost: str = "/"
    ):
        """
        Initialize validator.

        Args:
            management_url: RabbitMQ management API URL
            username: RabbitMQ username
            password: RabbitMQ password
            vhost: Virtual host to validate
        """
        self.management_url = management_url.rstrip('/')
        self.username = username
        self.password = password
        self.vhost = vhost
        self.issues: List[ValidationIssue] = []
        self.logger = logging.getLogger(__name__)

    def add_issue(
        self,
        severity: Severity,
        category: str,
        resource_type: str,
        resource_name: str,
        message: str,
        recommendation: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add validation issue."""
        issue = ValidationIssue(
            severity=severity.value,
            category=category,
            resource_type=resource_type,
            resource_name=resource_name,
            message=message,
            recommendation=recommendation,
            details=details
        )
        self.issues.append(issue)

    def get(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Make GET request to management API.

        Args:
            endpoint: API endpoint (e.g., '/api/queues')

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

    def validate_queue(self, queue: Dict[str, Any]) -> None:
        """
        Validate queue configuration.

        Args:
            queue: Queue information from API
        """
        name = queue['name']

        # Check if queue is durable
        if not queue.get('durable', False):
            self.add_issue(
                Severity.WARNING,
                'durability',
                'queue',
                name,
                'Queue is not durable',
                'Set durable=True to survive broker restarts',
                {'durable': queue.get('durable')}
            )

        # Check for excessive message accumulation
        messages = queue.get('messages', 0)
        if messages > 100000:
            self.add_issue(
                Severity.ERROR,
                'performance',
                'queue',
                name,
                f'Queue has {messages:,} messages (excessive accumulation)',
                'Increase consumer rate, add consumers, or set x-max-length',
                {'messages': messages}
            )
        elif messages > 10000:
            self.add_issue(
                Severity.WARNING,
                'performance',
                'queue',
                name,
                f'Queue has {messages:,} messages (potential backlog)',
                'Monitor consumer throughput and consider scaling',
                {'messages': messages}
            )

        # Check for unacknowledged messages
        unacked = queue.get('messages_unacknowledged', 0)
        if unacked > 0:
            unacked_ratio = unacked / max(messages, 1)
            if unacked_ratio > 0.5:
                self.add_issue(
                    Severity.WARNING,
                    'reliability',
                    'queue',
                    name,
                    f'High ratio of unacknowledged messages ({unacked}/{messages})',
                    'Check consumer processing time and prefetch_count',
                    {'unacknowledged': unacked, 'total': messages}
                )

        # Check for missing consumers
        consumers = queue.get('consumers', 0)
        if consumers == 0 and messages > 0:
            self.add_issue(
                Severity.ERROR,
                'reliability',
                'queue',
                name,
                'Queue has messages but no consumers',
                'Start consumers or remove unused queue',
                {'messages': messages, 'consumers': 0}
            )

        # Check queue arguments
        args = queue.get('arguments', {})

        # Check for DLX configuration
        if 'x-dead-letter-exchange' not in args:
            if queue.get('durable') and messages > 0:
                self.add_issue(
                    Severity.INFO,
                    'reliability',
                    'queue',
                    name,
                    'No dead letter exchange configured',
                    'Consider adding x-dead-letter-exchange for failed message handling',
                    {'arguments': args}
                )

        # Check for message TTL
        if 'x-message-ttl' in args:
            ttl = args['x-message-ttl']
            if ttl < 1000:  # Less than 1 second
                self.add_issue(
                    Severity.WARNING,
                    'configuration',
                    'queue',
                    name,
                    f'Very short message TTL ({ttl}ms)',
                    'Verify TTL is intentional, may cause message loss',
                    {'x-message-ttl': ttl}
                )

        # Check for queue length limits
        if 'x-max-length' not in args and 'x-max-length-bytes' not in args:
            if messages > 1000:
                self.add_issue(
                    Severity.INFO,
                    'performance',
                    'queue',
                    name,
                    'No queue length limit configured',
                    'Consider x-max-length or x-max-length-bytes to prevent unbounded growth',
                    {'messages': messages}
                )

        # Check for lazy queue mode
        queue_mode = args.get('x-queue-mode')
        if messages > 100000 and queue_mode != 'lazy':
            self.add_issue(
                Severity.WARNING,
                'performance',
                'queue',
                name,
                'Large queue without lazy mode',
                'Consider x-queue-mode=lazy to reduce memory usage',
                {'messages': messages, 'queue_mode': queue_mode}
            )

        # Check queue type
        queue_type = args.get('x-queue-type', 'classic')
        if queue_type == 'classic' and queue.get('durable'):
            # Check if queue should be quorum
            if consumers > 1:
                self.add_issue(
                    Severity.INFO,
                    'high_availability',
                    'queue',
                    name,
                    'Classic queue with multiple consumers',
                    'Consider using quorum queue for higher availability',
                    {'queue_type': queue_type, 'consumers': consumers}
                )

        # Check for priority queue
        if 'x-max-priority' in args:
            max_priority = args['x-max-priority']
            if max_priority > 10:
                self.add_issue(
                    Severity.WARNING,
                    'performance',
                    'queue',
                    name,
                    f'High priority range ({max_priority})',
                    'High priority ranges increase overhead, consider 0-5',
                    {'x-max-priority': max_priority}
                )

    def validate_exchange(self, exchange: Dict[str, Any]) -> None:
        """
        Validate exchange configuration.

        Args:
            exchange: Exchange information from API
        """
        name = exchange['name']

        # Skip built-in exchanges
        if name.startswith('amq.') or name == '':
            return

        # Check if exchange is durable
        if not exchange.get('durable', False):
            self.add_issue(
                Severity.WARNING,
                'durability',
                'exchange',
                name,
                'Exchange is not durable',
                'Set durable=True to survive broker restarts',
                {'durable': exchange.get('durable')}
            )

        # Check exchange type
        exchange_type = exchange.get('type')
        if exchange_type not in ['direct', 'fanout', 'topic', 'headers']:
            self.add_issue(
                Severity.ERROR,
                'configuration',
                'exchange',
                name,
                f'Invalid exchange type: {exchange_type}',
                'Use direct, fanout, topic, or headers',
                {'type': exchange_type}
            )

        # Check for unused exchanges (no bindings)
        # Note: Would need to fetch bindings separately

    def validate_binding(self, binding: Dict[str, Any]) -> None:
        """
        Validate binding configuration.

        Args:
            binding: Binding information from API
        """
        source = binding.get('source', '')
        destination = binding.get('destination', '')
        routing_key = binding.get('routing_key', '')

        # Skip default exchange bindings
        if source == '':
            return

        # Check for potential routing loops (exchange-to-exchange)
        if binding.get('destination_type') == 'exchange':
            if source == destination:
                self.add_issue(
                    Severity.CRITICAL,
                    'routing',
                    'binding',
                    f"{source} -> {destination}",
                    'Self-binding detected (routing loop)',
                    'Remove binding to prevent infinite message routing',
                    {'source': source, 'destination': destination}
                )

        # Check topic patterns
        dest_type = binding.get('destination_type', 'queue')
        exchange_props = binding.get('properties_key', {})

        # Validate topic patterns
        if '.' in routing_key:
            words = routing_key.split('.')
            if len(words) > 10:
                self.add_issue(
                    Severity.WARNING,
                    'configuration',
                    'binding',
                    f"{source} -> {destination}",
                    'Very long topic pattern (poor performance)',
                    'Simplify routing key pattern',
                    {'routing_key': routing_key, 'word_count': len(words)}
                )

    def validate_policy(self, policy: Dict[str, Any]) -> None:
        """
        Validate RabbitMQ policy.

        Args:
            policy: Policy information from API
        """
        name = policy['name']
        pattern = policy.get('pattern', '')
        definition = policy.get('definition', {})

        # Check HA policy (deprecated)
        if 'ha-mode' in definition:
            self.add_issue(
                Severity.WARNING,
                'deprecated',
                'policy',
                name,
                'Using deprecated ha-mode (mirrored queues)',
                'Migrate to quorum queues instead',
                {'ha-mode': definition['ha-mode']}
            )

        # Check max-length
        if 'max-length' in definition:
            max_length = definition['max-length']
            if max_length < 1000:
                self.add_issue(
                    Severity.WARNING,
                    'configuration',
                    'policy',
                    name,
                    f'Low max-length limit ({max_length})',
                    'Ensure limit is appropriate for workload',
                    {'max-length': max_length}
                )

        # Check message-ttl
        if 'message-ttl' in definition:
            ttl = definition['message-ttl']
            if ttl < 1000:
                self.add_issue(
                    Severity.WARNING,
                    'configuration',
                    'policy',
                    name,
                    f'Very short message TTL ({ttl}ms)',
                    'Verify TTL is intentional',
                    {'message-ttl': ttl}
                )

        # Check pattern overlap
        if pattern in ['.*', '#', '.*.*', '*']:
            self.add_issue(
                Severity.INFO,
                'configuration',
                'policy',
                name,
                'Policy applies to all resources (broad pattern)',
                'Consider narrowing pattern to specific resources',
                {'pattern': pattern}
            )

    def validate_vhost(self) -> None:
        """Validate virtual host configuration."""
        vhost_encoded = quote(self.vhost, safe='')
        vhost_info = self.get(f'/api/vhosts/{vhost_encoded}')

        if not vhost_info:
            self.add_issue(
                Severity.CRITICAL,
                'configuration',
                'vhost',
                self.vhost,
                'Virtual host does not exist or is not accessible',
                'Create vhost or check permissions',
                {}
            )
            return

    def validate_node_health(self) -> None:
        """Validate node health and resources."""
        nodes = self.get('/api/nodes')

        if not nodes:
            self.add_issue(
                Severity.CRITICAL,
                'availability',
                'cluster',
                'cluster',
                'Cannot retrieve node information',
                'Check management API and node health',
                {}
            )
            return

        for node in nodes:
            name = node.get('name', 'unknown')

            # Check memory
            mem_used = node.get('mem_used', 0)
            mem_limit = node.get('mem_limit', 1)
            mem_ratio = mem_used / mem_limit if mem_limit > 0 else 0

            if mem_ratio > 0.9:
                self.add_issue(
                    Severity.CRITICAL,
                    'resources',
                    'node',
                    name,
                    f'Very high memory usage ({mem_ratio*100:.1f}%)',
                    'Scale vertically, add consumers, or enable lazy queues',
                    {'mem_used': mem_used, 'mem_limit': mem_limit}
                )
            elif mem_ratio > 0.7:
                self.add_issue(
                    Severity.WARNING,
                    'resources',
                    'node',
                    name,
                    f'High memory usage ({mem_ratio*100:.1f}%)',
                    'Monitor memory and prepare to scale',
                    {'mem_used': mem_used, 'mem_limit': mem_limit}
                )

            # Check disk
            disk_free = node.get('disk_free', 0)
            disk_limit = node.get('disk_free_limit', 0)

            if disk_free < disk_limit * 2:
                self.add_issue(
                    Severity.ERROR,
                    'resources',
                    'node',
                    name,
                    f'Low disk space ({disk_free / 1e9:.2f}GB free)',
                    'Free up disk space or increase storage',
                    {'disk_free': disk_free, 'disk_limit': disk_limit}
                )

            # Check file descriptors
            fd_used = node.get('fd_used', 0)
            fd_total = node.get('fd_total', 1)
            fd_ratio = fd_used / fd_total if fd_total > 0 else 0

            if fd_ratio > 0.8:
                self.add_issue(
                    Severity.ERROR,
                    'resources',
                    'node',
                    name,
                    f'High file descriptor usage ({fd_ratio*100:.1f}%)',
                    'Increase ulimit or reduce connections',
                    {'fd_used': fd_used, 'fd_total': fd_total}
                )

            # Check Erlang processes
            proc_used = node.get('proc_used', 0)
            proc_total = node.get('proc_total', 1)
            proc_ratio = proc_used / proc_total if proc_total > 0 else 0

            if proc_ratio > 0.8:
                self.add_issue(
                    Severity.WARNING,
                    'resources',
                    'node',
                    name,
                    f'High Erlang process usage ({proc_ratio*100:.1f}%)',
                    'Monitor process count, may need to tune Erlang VM',
                    {'proc_used': proc_used, 'proc_total': proc_total}
                )

    def validate_all(self) -> ValidationReport:
        """
        Run all validations.

        Returns:
            Validation report
        """
        self.issues = []

        # Validate vhost
        self.validate_vhost()

        # Validate node health
        self.validate_node_health()

        # Validate queues
        vhost_encoded = quote(self.vhost, safe='')
        queues = self.get(f'/api/queues/{vhost_encoded}') or []
        for queue in queues:
            self.validate_queue(queue)

        # Validate exchanges
        exchanges = self.get(f'/api/exchanges/{vhost_encoded}') or []
        for exchange in exchanges:
            self.validate_exchange(exchange)

        # Validate bindings
        bindings = self.get(f'/api/bindings/{vhost_encoded}') or []
        for binding in bindings:
            self.validate_binding(binding)

        # Validate policies
        policies = self.get('/api/policies') or []
        vhost_policies = [p for p in policies if p.get('vhost') == self.vhost]
        for policy in vhost_policies:
            self.validate_policy(policy)

        # Count issues by severity
        critical_count = sum(1 for i in self.issues if i.severity == Severity.CRITICAL.value)
        error_count = sum(1 for i in self.issues if i.severity == Severity.ERROR.value)
        warning_count = sum(1 for i in self.issues if i.severity == Severity.WARNING.value)
        info_count = sum(1 for i in self.issues if i.severity == Severity.INFO.value)

        return ValidationReport(
            broker_url=self.management_url,
            vhost=self.vhost,
            total_issues=len(self.issues),
            critical_count=critical_count,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            issues=self.issues,
            queues_checked=len(queues),
            exchanges_checked=len(exchanges),
            bindings_checked=len(bindings),
            policies_checked=len(vhost_policies)
        )


def parse_amqp_url(url: str) -> Tuple[str, str, str, str]:
    """
    Parse AMQP URL.

    Args:
        url: AMQP URL (e.g., amqp://user:pass@localhost:5672/vhost)

    Returns:
        Tuple of (management_url, username, password, vhost)
    """
    parsed = urlparse(url)

    # Extract credentials
    username = parsed.username or 'guest'
    password = parsed.password or 'guest'

    # Build management URL
    host = parsed.hostname or 'localhost'
    # Management API typically on port 15672
    management_url = f"http://{host}:15672"

    # Extract vhost
    vhost = parsed.path.lstrip('/') or '/'

    return management_url, username, password, vhost


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate RabbitMQ configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate default vhost
  %(prog)s --url amqp://localhost

  # Validate specific vhost
  %(prog)s --url amqp://localhost --vhost myapp

  # JSON output
  %(prog)s --url amqp://localhost --json

  # Check policies only
  %(prog)s --url amqp://localhost --check-policies

  # Custom management URL
  %(prog)s --url amqp://localhost --management-url http://localhost:15672
        """
    )

    parser.add_argument(
        '--url',
        required=True,
        help='AMQP broker URL (amqp://user:pass@host:port/vhost)'
    )
    parser.add_argument(
        '--vhost',
        help='Virtual host to validate (default: from URL or /)'
    )
    parser.add_argument(
        '--management-url',
        help='Management API URL (default: inferred from AMQP URL)'
    )
    parser.add_argument(
        '--check-policies',
        action='store_true',
        help='Check policies only'
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

    # Parse AMQP URL
    management_url, username, password, vhost = parse_amqp_url(args.url)

    # Override with command line args
    if args.management_url:
        management_url = args.management_url
    if args.vhost:
        vhost = args.vhost

    # Create validator
    validator = RabbitMQValidator(
        management_url=management_url,
        username=username,
        password=password,
        vhost=vhost
    )

    # Run validation
    report = validator.validate_all()

    # Output results
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        # Human-readable output
        print(f"\n{'='*80}")
        print(f"RabbitMQ Configuration Validation Report")
        print(f"{'='*80}")
        print(f"Broker: {report.broker_url}")
        print(f"VHost: {report.vhost}")
        print(f"\nResources Checked:")
        print(f"  - Queues: {report.queues_checked}")
        print(f"  - Exchanges: {report.exchanges_checked}")
        print(f"  - Bindings: {report.bindings_checked}")
        print(f"  - Policies: {report.policies_checked}")
        print(f"\nIssues Found: {report.total_issues}")
        print(f"  - Critical: {report.critical_count}")
        print(f"  - Error: {report.error_count}")
        print(f"  - Warning: {report.warning_count}")
        print(f"  - Info: {report.info_count}")

        if report.issues:
            print(f"\n{'='*80}")
            print("Issues:")
            print(f"{'='*80}\n")

            for issue in sorted(report.issues, key=lambda x: (
                ['info', 'warning', 'error', 'critical'].index(x.severity),
                x.category,
                x.resource_name
            )):
                severity_display = {
                    'info': '  INFO',
                    'warning': '  WARN',
                    'error': ' ERROR',
                    'critical': ' CRIT',
                }
                print(f"[{severity_display[issue.severity]}] {issue.category.upper()}")
                print(f"  Resource: {issue.resource_type}/{issue.resource_name}")
                print(f"  Issue: {issue.message}")
                print(f"  Recommendation: {issue.recommendation}")
                if issue.details:
                    print(f"  Details: {json.dumps(issue.details)}")
                print()

    # Return exit code
    if report.critical_count > 0:
        return 2
    elif report.error_count > 0:
        return 1
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())
