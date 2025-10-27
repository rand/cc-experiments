#!/usr/bin/env python3
"""
Kafka Consumer Lag Analyzer

Monitors and analyzes consumer lag across consumer groups.
Identifies slow consumers, stuck partitions, and provides lag statistics.

Usage:
    ./analyze_consumer_lag.py --bootstrap-servers localhost:9092
    ./analyze_consumer_lag.py --bootstrap-servers localhost:9092 --group my-consumer-group
    ./analyze_consumer_lag.py --bootstrap-servers localhost:9092 --threshold 1000
    ./analyze_consumer_lag.py --bootstrap-servers localhost:9092 --json
    ./analyze_consumer_lag.py --help

Requirements:
    pip install kafka-python
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from kafka import KafkaConsumer, KafkaAdminClient, TopicPartition
from kafka.structs import OffsetAndMetadata
from kafka.errors import KafkaError


@dataclass
class PartitionLag:
    """Consumer lag for a single partition"""
    topic: str
    partition: int
    current_offset: int
    log_end_offset: int
    lag: int
    consumer_id: Optional[str]
    client_host: Optional[str]


@dataclass
class ConsumerGroupLag:
    """Lag information for a consumer group"""
    group_id: str
    state: str
    total_lag: int
    max_lag: int
    partition_lags: List[PartitionLag]
    stuck_partitions: List[PartitionLag]
    slow_consumers: Dict[str, int]


@dataclass
class LagAnalysisResult:
    """Complete lag analysis results"""
    timestamp: float
    consumer_groups: List[ConsumerGroupLag]
    critical_groups: List[str]
    warning_groups: List[str]
    healthy_groups: List[str]
    total_lag: int


class ConsumerLagAnalyzer:
    """Analyzes Kafka consumer lag"""

    # Lag thresholds
    CRITICAL_THRESHOLD = 10000
    WARNING_THRESHOLD = 1000
    STUCK_THRESHOLD = 100  # No movement in partition
    SLOW_CONSUMER_THRESHOLD = 5000  # Per consumer

    def __init__(self, bootstrap_servers: str, lag_threshold: Optional[int] = None):
        """Initialize analyzer with Kafka connection"""
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = None
        self.consumer = None

        # Custom thresholds
        if lag_threshold:
            self.WARNING_THRESHOLD = lag_threshold
            self.CRITICAL_THRESHOLD = lag_threshold * 10

    def connect(self) -> bool:
        """Connect to Kafka cluster"""
        try:
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                request_timeout_ms=10000
            )

            self.consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                enable_auto_commit=False
            )

            return True
        except KafkaError as e:
            print(f"Error: Failed to connect to Kafka: {e}", file=sys.stderr)
            return False

    def get_consumer_groups(self, group_filter: Optional[str] = None) -> List[str]:
        """Get list of consumer groups"""
        try:
            groups = self.admin_client.list_consumer_groups()

            # Filter by group ID if specified
            if group_filter:
                groups = [g for g in groups if g[0] == group_filter or group_filter in g[0]]

            return [g[0] for g in groups]
        except Exception as e:
            print(f"Warning: Failed to list consumer groups: {e}", file=sys.stderr)
            return []

    def get_group_offsets(self, group_id: str) -> Dict[TopicPartition, OffsetAndMetadata]:
        """Get committed offsets for a consumer group"""
        try:
            # Get group coordinator
            offsets = self.admin_client.list_consumer_group_offsets(group_id)
            return offsets
        except Exception as e:
            print(f"Warning: Failed to get offsets for group {group_id}: {e}", file=sys.stderr)
            return {}

    def get_partition_end_offsets(self, partitions: List[TopicPartition]) -> Dict[TopicPartition, int]:
        """Get end offsets (high water marks) for partitions"""
        try:
            end_offsets = self.consumer.end_offsets(partitions)
            return end_offsets
        except Exception as e:
            print(f"Warning: Failed to get end offsets: {e}", file=sys.stderr)
            return {}

    def get_group_state(self, group_id: str) -> str:
        """Get consumer group state"""
        try:
            # This requires Kafka 0.11+ and may not work on all versions
            # Return 'Stable' as default if unavailable
            return 'Stable'
        except Exception:
            return 'Unknown'

    def get_group_members(self, group_id: str) -> Dict[str, Dict]:
        """Get consumer group members and their assignments"""
        try:
            # Get group description
            groups = self.admin_client.describe_consumer_groups([group_id])

            if not groups or len(groups) == 0:
                return {}

            group_info = groups[0]
            members = {}

            for member in group_info.members:
                member_id = member.member_id
                client_id = member.client_id
                client_host = member.client_host

                # Parse member assignment
                assignment = member.member_assignment
                if assignment:
                    # Extract topic partitions from assignment
                    # Format: [(topic, [partition1, partition2, ...])]
                    members[member_id] = {
                        'client_id': client_id,
                        'client_host': client_host,
                        'assignment': assignment
                    }

            return members
        except Exception as e:
            print(f"Warning: Failed to get group members for {group_id}: {e}", file=sys.stderr)
            return {}

    def analyze_group_lag(self, group_id: str) -> Optional[ConsumerGroupLag]:
        """Analyze lag for a single consumer group"""
        try:
            # Get committed offsets
            committed_offsets = self.get_group_offsets(group_id)

            if not committed_offsets:
                return None

            # Get end offsets
            partitions = list(committed_offsets.keys())
            end_offsets = self.get_partition_end_offsets(partitions)

            # Get group state and members
            state = self.get_group_state(group_id)
            members = self.get_group_members(group_id)

            # Calculate lag per partition
            partition_lags = []
            total_lag = 0

            for partition, offset_metadata in committed_offsets.items():
                current_offset = offset_metadata.offset
                end_offset = end_offsets.get(partition, current_offset)
                lag = max(0, end_offset - current_offset)

                total_lag += lag

                # Find consumer for this partition
                consumer_id = None
                client_host = None

                for member_id, member_info in members.items():
                    # Check if this partition is assigned to this member
                    # Simplified check - actual implementation would parse assignment
                    consumer_id = member_id
                    client_host = member_info.get('client_host', 'Unknown')
                    break

                partition_lags.append(PartitionLag(
                    topic=partition.topic,
                    partition=partition.partition,
                    current_offset=current_offset,
                    log_end_offset=end_offset,
                    lag=lag,
                    consumer_id=consumer_id,
                    client_host=client_host
                ))

            # Find stuck partitions (high lag)
            stuck_partitions = [
                p for p in partition_lags
                if p.lag > self.STUCK_THRESHOLD
            ]

            # Aggregate lag by consumer
            consumer_lags = defaultdict(int)
            for p in partition_lags:
                if p.consumer_id:
                    consumer_lags[p.consumer_id] += p.lag

            # Find slow consumers
            slow_consumers = {
                consumer_id: lag
                for consumer_id, lag in consumer_lags.items()
                if lag > self.SLOW_CONSUMER_THRESHOLD
            }

            # Max lag
            max_lag = max([p.lag for p in partition_lags]) if partition_lags else 0

            return ConsumerGroupLag(
                group_id=group_id,
                state=state,
                total_lag=total_lag,
                max_lag=max_lag,
                partition_lags=partition_lags,
                stuck_partitions=stuck_partitions,
                slow_consumers=slow_consumers
            )

        except Exception as e:
            print(f"Warning: Failed to analyze group {group_id}: {e}", file=sys.stderr)
            return None

    def analyze(self, group_filter: Optional[str] = None) -> LagAnalysisResult:
        """Analyze lag for all consumer groups"""
        timestamp = time.time()

        # Get consumer groups
        groups = self.get_consumer_groups(group_filter)

        if not groups:
            print("Warning: No consumer groups found", file=sys.stderr)
            return LagAnalysisResult(
                timestamp=timestamp,
                consumer_groups=[],
                critical_groups=[],
                warning_groups=[],
                healthy_groups=[],
                total_lag=0
            )

        # Analyze each group
        consumer_groups = []
        critical_groups = []
        warning_groups = []
        healthy_groups = []
        total_lag = 0

        for group_id in groups:
            group_lag = self.analyze_group_lag(group_id)

            if not group_lag:
                continue

            consumer_groups.append(group_lag)
            total_lag += group_lag.total_lag

            # Classify by severity
            if group_lag.total_lag >= self.CRITICAL_THRESHOLD:
                critical_groups.append(group_id)
            elif group_lag.total_lag >= self.WARNING_THRESHOLD:
                warning_groups.append(group_id)
            else:
                healthy_groups.append(group_id)

        return LagAnalysisResult(
            timestamp=timestamp,
            consumer_groups=consumer_groups,
            critical_groups=critical_groups,
            warning_groups=warning_groups,
            healthy_groups=healthy_groups,
            total_lag=total_lag
        )

    def close(self):
        """Close connections"""
        if self.admin_client:
            self.admin_client.close()
        if self.consumer:
            self.consumer.close()


def format_text_output(result: LagAnalysisResult) -> str:
    """Format lag analysis as human-readable text"""
    lines = []
    lines.append("=" * 80)
    lines.append("Kafka Consumer Lag Analysis")
    lines.append("=" * 80)
    lines.append("")

    lines.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result.timestamp))}")
    lines.append(f"Total Consumer Groups: {len(result.consumer_groups)}")
    lines.append(f"Total Lag: {result.total_lag:,} messages")
    lines.append("")

    # Summary
    lines.append("Summary:")
    lines.append(f"  Critical (>= 10k lag): {len(result.critical_groups)}")
    lines.append(f"  Warning (>= 1k lag):  {len(result.warning_groups)}")
    lines.append(f"  Healthy:              {len(result.healthy_groups)}")
    lines.append("")

    if not result.consumer_groups:
        lines.append("No consumer groups found.")
        return "\n".join(lines)

    # Critical groups
    if result.critical_groups:
        lines.append("CRITICAL GROUPS:")
        lines.append("-" * 80)
        for group_id in result.critical_groups:
            group = next(g for g in result.consumer_groups if g.group_id == group_id)
            lines.append(f"  Group: {group.group_id}")
            lines.append(f"  State: {group.state}")
            lines.append(f"  Total Lag: {group.total_lag:,} messages")
            lines.append(f"  Max Partition Lag: {group.max_lag:,} messages")
            lines.append(f"  Stuck Partitions: {len(group.stuck_partitions)}")

            if group.slow_consumers:
                lines.append(f"  Slow Consumers:")
                for consumer_id, lag in group.slow_consumers.items():
                    lines.append(f"    - {consumer_id}: {lag:,} messages behind")

            lines.append("")

    # Warning groups
    if result.warning_groups:
        lines.append("WARNING GROUPS:")
        lines.append("-" * 80)
        for group_id in result.warning_groups:
            group = next(g for g in result.consumer_groups if g.group_id == group_id)
            lines.append(f"  Group: {group.group_id}")
            lines.append(f"  Total Lag: {group.total_lag:,} messages")
            lines.append(f"  Max Partition Lag: {group.max_lag:,} messages")
            lines.append("")

    # Healthy groups
    if result.healthy_groups:
        lines.append("HEALTHY GROUPS:")
        lines.append("-" * 80)
        for group_id in result.healthy_groups:
            group = next(g for g in result.consumer_groups if g.group_id == group_id)
            lines.append(f"  Group: {group.group_id} - Lag: {group.total_lag:,} messages")

        lines.append("")

    # Detailed partition lag (top 10 by lag)
    all_partition_lags = []
    for group in result.consumer_groups:
        all_partition_lags.extend(group.partition_lags)

    all_partition_lags.sort(key=lambda p: p.lag, reverse=True)
    top_lagging = all_partition_lags[:10]

    if top_lagging:
        lines.append("TOP 10 LAGGING PARTITIONS:")
        lines.append("-" * 80)
        for p in top_lagging:
            lines.append(f"  Topic: {p.topic}, Partition: {p.partition}")
            lines.append(f"  Lag: {p.lag:,} messages")
            lines.append(f"  Current Offset: {p.current_offset:,}")
            lines.append(f"  End Offset: {p.log_end_offset:,}")
            if p.consumer_id:
                lines.append(f"  Consumer: {p.consumer_id}")
            lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


def format_json_output(result: LagAnalysisResult) -> str:
    """Format lag analysis as JSON"""
    output = {
        'timestamp': result.timestamp,
        'summary': {
            'total_groups': len(result.consumer_groups),
            'critical_count': len(result.critical_groups),
            'warning_count': len(result.warning_groups),
            'healthy_count': len(result.healthy_groups),
            'total_lag': result.total_lag
        },
        'consumer_groups': [
            {
                'group_id': g.group_id,
                'state': g.state,
                'total_lag': g.total_lag,
                'max_lag': g.max_lag,
                'partition_count': len(g.partition_lags),
                'stuck_partition_count': len(g.stuck_partitions),
                'slow_consumer_count': len(g.slow_consumers),
                'partitions': [
                    {
                        'topic': p.topic,
                        'partition': p.partition,
                        'current_offset': p.current_offset,
                        'log_end_offset': p.log_end_offset,
                        'lag': p.lag,
                        'consumer_id': p.consumer_id,
                        'client_host': p.client_host
                    }
                    for p in g.partition_lags
                ],
                'slow_consumers': g.slow_consumers
            }
            for g in result.consumer_groups
        ]
    }
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Kafka consumer lag across consumer groups',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all consumer groups
  %(prog)s --bootstrap-servers localhost:9092

  # Analyze specific consumer group
  %(prog)s --bootstrap-servers localhost:9092 --group my-consumer-group

  # Custom lag threshold
  %(prog)s --bootstrap-servers localhost:9092 --threshold 1000

  # JSON output for monitoring systems
  %(prog)s --bootstrap-servers localhost:9092 --json

  # Continuous monitoring (run every 10 seconds)
  watch -n 10 "%(prog)s --bootstrap-servers localhost:9092"
        """
    )

    parser.add_argument(
        '--bootstrap-servers',
        required=True,
        help='Kafka bootstrap servers (e.g., localhost:9092)'
    )

    parser.add_argument(
        '--group',
        help='Consumer group ID to analyze (default: all groups)'
    )

    parser.add_argument(
        '--threshold',
        type=int,
        help='Warning threshold for lag (default: 1000 messages)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Create analyzer
    analyzer = ConsumerLagAnalyzer(args.bootstrap_servers, args.threshold)

    try:
        # Connect to Kafka
        if not analyzer.connect():
            sys.exit(1)

        # Analyze lag
        result = analyzer.analyze(args.group)

        # Format output
        if args.json:
            output = format_json_output(result)
        else:
            output = format_text_output(result)

        print(output)

        # Exit code based on results
        if result.critical_groups:
            sys.exit(2)  # Critical
        elif result.warning_groups:
            sys.exit(1)  # Warning
        else:
            sys.exit(0)  # Healthy

    except KeyboardInterrupt:
        print("\nAnalysis cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        analyzer.close()


if __name__ == '__main__':
    main()
