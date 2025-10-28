#!/usr/bin/env python3
"""
Kafka Configuration Validator

Validates Kafka broker and topic configurations against best practices.
Checks broker settings, topic configurations, replication, and performance tuning.

Usage:
    ./validate_kafka_config.py --bootstrap-servers localhost:9092
    ./validate_kafka_config.py --bootstrap-servers localhost:9092 --topics orders,payments
    ./validate_kafka_config.py --bootstrap-servers localhost:9092 --json
    ./validate_kafka_config.py --help

Requirements:
    pip install kafka-python
"""

import argparse
import json
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from kafka import KafkaAdminClient, KafkaConsumer
from kafka.admin import ConfigResource, ConfigResourceType
from kafka.errors import KafkaError


@dataclass
class ValidationIssue:
    """Represents a configuration validation issue"""
    severity: str  # error, warning, info
    category: str
    resource: str
    issue: str
    current_value: Optional[str]
    recommended_value: Optional[str]
    description: str


@dataclass
class ValidationResult:
    """Complete validation results"""
    status: str  # pass, warning, fail
    issues: List[ValidationIssue]
    broker_count: int
    topic_count: int
    total_partitions: int


class KafkaConfigValidator:
    """Validates Kafka broker and topic configurations"""

    # Best practice thresholds
    BROKER_CONFIG_RULES = {
        'num.network.threads': {'min': 3, 'recommended': 8},
        'num.io.threads': {'min': 8, 'recommended': 16},
        'socket.send.buffer.bytes': {'min': 102400, 'recommended': 1048576},
        'socket.receive.buffer.bytes': {'min': 102400, 'recommended': 1048576},
        'num.replica.fetchers': {'min': 1, 'recommended': 4},
        'replica.lag.time.max.ms': {'max': 30000},
        'log.retention.hours': {'min': 1},
    }

    TOPIC_CONFIG_RULES = {
        'min.insync.replicas': {'min': 2},
        'replication.factor': {'min': 3},
        'partitions': {'min': 1, 'max': 1000},
    }

    def __init__(self, bootstrap_servers: str):
        """Initialize validator with Kafka connection"""
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = None
        self.issues: List[ValidationIssue] = []

    def connect(self) -> bool:
        """Connect to Kafka cluster"""
        try:
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                request_timeout_ms=10000
            )
            return True
        except KafkaError as e:
            self.issues.append(ValidationIssue(
                severity='error',
                category='connection',
                resource='cluster',
                issue='Failed to connect to Kafka cluster',
                current_value=None,
                recommended_value=None,
                description=str(e)
            ))
            return False

    def validate_cluster(self) -> None:
        """Validate cluster-level configuration"""
        try:
            # Get broker configs
            cluster_metadata = self.admin_client.describe_cluster()
            broker_count = len(cluster_metadata['brokers'])

            # Check broker count
            if broker_count < 3:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='cluster',
                    resource='brokers',
                    issue='Low broker count',
                    current_value=str(broker_count),
                    recommended_value='3+',
                    description='Production clusters should have at least 3 brokers for fault tolerance'
                ))

            # Check if cluster has controller
            controller_id = cluster_metadata.get('controller_id')
            if controller_id is None:
                self.issues.append(ValidationIssue(
                    severity='error',
                    category='cluster',
                    resource='controller',
                    issue='No active controller',
                    current_value='None',
                    recommended_value='1',
                    description='Cluster must have exactly one active controller'
                ))

        except Exception as e:
            self.issues.append(ValidationIssue(
                severity='error',
                category='cluster',
                resource='metadata',
                issue='Failed to retrieve cluster metadata',
                current_value=None,
                recommended_value=None,
                description=str(e)
            ))

    def validate_broker_configs(self) -> None:
        """Validate broker-level configurations"""
        try:
            # Get broker list
            cluster_metadata = self.admin_client.describe_cluster()
            brokers = cluster_metadata['brokers']

            for broker in brokers:
                broker_id = broker['nodeId']

                # Get broker configs
                config_resource = ConfigResource(
                    ConfigResourceType.BROKER,
                    str(broker_id)
                )

                configs = self.admin_client.describe_configs([config_resource])

                if not configs:
                    continue

                broker_config = configs[0].resources[0][4]  # Config entries

                # Validate each config
                self._validate_broker_config_values(broker_id, broker_config)

        except Exception as e:
            self.issues.append(ValidationIssue(
                severity='warning',
                category='broker',
                resource='configs',
                issue='Failed to retrieve broker configurations',
                current_value=None,
                recommended_value=None,
                description=str(e)
            ))

    def _validate_broker_config_values(self, broker_id: int, config: Dict) -> None:
        """Validate individual broker config values"""
        for config_name, rules in self.BROKER_CONFIG_RULES.items():
            if config_name not in config:
                continue

            value = config[config_name].value

            try:
                numeric_value = int(value)
            except (ValueError, TypeError):
                continue

            # Check minimum
            if 'min' in rules and numeric_value < rules['min']:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='broker',
                    resource=f'broker-{broker_id}',
                    issue=f'Low {config_name}',
                    current_value=str(numeric_value),
                    recommended_value=f">= {rules['min']}",
                    description=f'Value is below minimum recommended threshold'
                ))

            # Check recommended
            if 'recommended' in rules and numeric_value < rules['recommended']:
                self.issues.append(ValidationIssue(
                    severity='info',
                    category='broker',
                    resource=f'broker-{broker_id}',
                    issue=f'Suboptimal {config_name}',
                    current_value=str(numeric_value),
                    recommended_value=str(rules['recommended']),
                    description=f'Consider increasing for better performance'
                ))

            # Check maximum
            if 'max' in rules and numeric_value > rules['max']:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='broker',
                    resource=f'broker-{broker_id}',
                    issue=f'High {config_name}',
                    current_value=str(numeric_value),
                    recommended_value=f"<= {rules['max']}",
                    description=f'Value exceeds maximum recommended threshold'
                ))

    def validate_topics(self, topic_filter: Optional[List[str]] = None) -> None:
        """Validate topic configurations"""
        try:
            # Get topic list
            consumer = KafkaConsumer(bootstrap_servers=self.bootstrap_servers)
            all_topics = consumer.topics()
            consumer.close()

            # Filter topics if specified
            if topic_filter:
                topics = [t for t in all_topics if t in topic_filter]
            else:
                topics = list(all_topics)

            # Filter out internal topics
            topics = [t for t in topics if not t.startswith('__')]

            total_partitions = 0

            for topic in topics:
                # Get topic metadata
                metadata = self.admin_client.describe_topics([topic])

                if not metadata:
                    continue

                topic_metadata = metadata[0]
                partitions = len(topic_metadata.get('partitions', []))
                total_partitions += partitions

                # Get topic configs
                config_resource = ConfigResource(ConfigResourceType.TOPIC, topic)
                configs = self.admin_client.describe_configs([config_resource])

                if not configs:
                    continue

                topic_config = configs[0].resources[0][4]

                # Validate topic
                self._validate_topic_config(topic, partitions, topic_config)

            return total_partitions

        except Exception as e:
            self.issues.append(ValidationIssue(
                severity='error',
                category='topics',
                resource='metadata',
                issue='Failed to retrieve topic metadata',
                current_value=None,
                recommended_value=None,
                description=str(e)
            ))
            return 0

    def _validate_topic_config(self, topic: str, partitions: int, config: Dict) -> None:
        """Validate individual topic configuration"""
        # Validate partition count
        if partitions < self.TOPIC_CONFIG_RULES['partitions']['min']:
            self.issues.append(ValidationIssue(
                severity='warning',
                category='topic',
                resource=topic,
                issue='Low partition count',
                current_value=str(partitions),
                recommended_value=f">= {self.TOPIC_CONFIG_RULES['partitions']['min']}",
                description='Topic has very few partitions, limiting parallelism'
            ))

        if partitions > self.TOPIC_CONFIG_RULES['partitions']['max']:
            self.issues.append(ValidationIssue(
                severity='warning',
                category='topic',
                resource=topic,
                issue='High partition count',
                current_value=str(partitions),
                recommended_value=f"<= {self.TOPIC_CONFIG_RULES['partitions']['max']}",
                description='Too many partitions can cause performance issues'
            ))

        # Validate replication factor
        if 'replication.factor' in config:
            replication_factor = int(config['replication.factor'].value)
            min_rf = self.TOPIC_CONFIG_RULES['replication.factor']['min']

            if replication_factor < min_rf:
                self.issues.append(ValidationIssue(
                    severity='error',
                    category='topic',
                    resource=topic,
                    issue='Low replication factor',
                    current_value=str(replication_factor),
                    recommended_value=str(min_rf),
                    description='Low replication increases risk of data loss'
                ))

        # Validate min.insync.replicas
        if 'min.insync.replicas' in config:
            min_isr = int(config['min.insync.replicas'].value)
            recommended_isr = self.TOPIC_CONFIG_RULES['min.insync.replicas']['min']

            if min_isr < recommended_isr:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='topic',
                    resource=topic,
                    issue='Low min.insync.replicas',
                    current_value=str(min_isr),
                    recommended_value=str(recommended_isr),
                    description='Low min.insync.replicas reduces durability guarantees'
                ))

        # Check retention
        if 'retention.ms' in config:
            retention_ms = int(config['retention.ms'].value)
            if retention_ms < 3600000:  # 1 hour
                self.issues.append(ValidationIssue(
                    severity='info',
                    category='topic',
                    resource=topic,
                    issue='Very short retention',
                    current_value=f'{retention_ms / 1000}s',
                    recommended_value='>= 1 hour',
                    description='Short retention may cause data loss for slow consumers'
                ))

        # Check cleanup policy
        if 'cleanup.policy' in config:
            cleanup_policy = config['cleanup.policy'].value
            if cleanup_policy not in ['delete', 'compact', 'compact,delete']:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='topic',
                    resource=topic,
                    issue='Invalid cleanup policy',
                    current_value=cleanup_policy,
                    recommended_value='delete or compact',
                    description='Cleanup policy must be delete, compact, or both'
                ))

    def validate(self, topic_filter: Optional[List[str]] = None) -> ValidationResult:
        """Run complete validation"""
        # Connect to cluster
        if not self.connect():
            return ValidationResult(
                status='fail',
                issues=self.issues,
                broker_count=0,
                topic_count=0,
                total_partitions=0
            )

        # Validate cluster
        self.validate_cluster()

        # Validate brokers
        self.validate_broker_configs()

        # Validate topics
        total_partitions = self.validate_topics(topic_filter)

        # Get counts
        try:
            cluster_metadata = self.admin_client.describe_cluster()
            broker_count = len(cluster_metadata['brokers'])

            consumer = KafkaConsumer(bootstrap_servers=self.bootstrap_servers)
            topic_count = len([t for t in consumer.topics() if not t.startswith('__')])
            consumer.close()
        except Exception:
            broker_count = 0
            topic_count = 0

        # Determine overall status
        error_count = sum(1 for i in self.issues if i.severity == 'error')
        warning_count = sum(1 for i in self.issues if i.severity == 'warning')

        if error_count > 0:
            status = 'fail'
        elif warning_count > 0:
            status = 'warning'
        else:
            status = 'pass'

        return ValidationResult(
            status=status,
            issues=self.issues,
            broker_count=broker_count,
            topic_count=topic_count,
            total_partitions=total_partitions
        )

    def close(self):
        """Close connections"""
        if self.admin_client:
            self.admin_client.close()


def format_text_output(result: ValidationResult) -> str:
    """Format validation results as human-readable text"""
    lines = []
    lines.append("=" * 80)
    lines.append("Kafka Configuration Validation Report")
    lines.append("=" * 80)
    lines.append("")

    lines.append(f"Overall Status: {result.status.upper()}")
    lines.append(f"Brokers: {result.broker_count}")
    lines.append(f"Topics: {result.topic_count}")
    lines.append(f"Total Partitions: {result.total_partitions}")
    lines.append("")

    if not result.issues:
        lines.append("✓ No issues found - configuration looks good!")
        lines.append("")
        return "\n".join(lines)

    # Group issues by severity
    errors = [i for i in result.issues if i.severity == 'error']
    warnings = [i for i in result.issues if i.severity == 'warning']
    info = [i for i in result.issues if i.severity == 'info']

    # Errors
    if errors:
        lines.append(f"ERRORS ({len(errors)}):")
        lines.append("-" * 80)
        for issue in errors:
            lines.append(f"  Resource: {issue.resource}")
            lines.append(f"  Issue: {issue.issue}")
            if issue.current_value:
                lines.append(f"  Current: {issue.current_value}")
            if issue.recommended_value:
                lines.append(f"  Recommended: {issue.recommended_value}")
            lines.append(f"  Description: {issue.description}")
            lines.append("")

    # Warnings
    if warnings:
        lines.append(f"WARNINGS ({len(warnings)}):")
        lines.append("-" * 80)
        for issue in warnings:
            lines.append(f"  Resource: {issue.resource}")
            lines.append(f"  Issue: {issue.issue}")
            if issue.current_value:
                lines.append(f"  Current: {issue.current_value}")
            if issue.recommended_value:
                lines.append(f"  Recommended: {issue.recommended_value}")
            lines.append(f"  Description: {issue.description}")
            lines.append("")

    # Info
    if info:
        lines.append(f"RECOMMENDATIONS ({len(info)}):")
        lines.append("-" * 80)
        for issue in info:
            lines.append(f"  Resource: {issue.resource}")
            lines.append(f"  Issue: {issue.issue}")
            if issue.current_value:
                lines.append(f"  Current: {issue.current_value}")
            if issue.recommended_value:
                lines.append(f"  Recommended: {issue.recommended_value}")
            lines.append(f"  Description: {issue.description}")
            lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


def format_json_output(result: ValidationResult) -> str:
    """Format validation results as JSON"""
    output = {
        'status': result.status,
        'summary': {
            'broker_count': result.broker_count,
            'topic_count': result.topic_count,
            'total_partitions': result.total_partitions,
            'error_count': sum(1 for i in result.issues if i.severity == 'error'),
            'warning_count': sum(1 for i in result.issues if i.severity == 'warning'),
            'info_count': sum(1 for i in result.issues if i.severity == 'info'),
        },
        'issues': [asdict(issue) for issue in result.issues]
    }
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Validate Kafka broker and topic configurations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate entire cluster
  %(prog)s --bootstrap-servers localhost:9092

  # Validate specific topics
  %(prog)s --bootstrap-servers localhost:9092 --topics orders,payments

  # JSON output for automation
  %(prog)s --bootstrap-servers localhost:9092 --json

  # Save report to file
  %(prog)s --bootstrap-servers localhost:9092 --json > validation-report.json
        """
    )

    parser.add_argument(
        '--bootstrap-servers',
        required=True,
        help='Kafka bootstrap servers (e.g., localhost:9092)'
    )

    parser.add_argument(
        '--topics',
        help='Comma-separated list of topics to validate (default: all topics)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Parse topics
    topic_filter = None
    if args.topics:
        topic_filter = [t.strip() for t in args.topics.split(',')]

    # Run validation
    validator = KafkaConfigValidator(args.bootstrap_servers)

    try:
        result = validator.validate(topic_filter)

        # Format output
        if args.json:
            output = format_json_output(result)
        else:
            output = format_text_output(result)

        print(output)

        # Exit code
        if result.status == 'fail':
            sys.exit(1)
        elif result.status == 'warning':
            sys.exit(0)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\nValidation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        validator.close()


if __name__ == '__main__':
    main()
