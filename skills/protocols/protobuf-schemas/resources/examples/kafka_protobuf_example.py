#!/usr/bin/env python3
"""
Kafka with Protocol Buffers Example

Demonstrates using Protocol Buffers for Kafka message serialization,
providing type safety, schema evolution, and efficient encoding.

Benefits over JSON:
- 3-10x smaller message size
- Type safety at compile time
- Schema evolution support
- Faster serialization/deserialization

Requirements:
    pip install kafka-python protobuf

Usage:
    # Generate proto code first
    protoc --python_out=. user_service.proto

    # Run producer
    python kafka_protobuf_example.py --mode producer

    # Run consumer
    python kafka_protobuf_example.py --mode consumer
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Optional

try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError
except ImportError:
    print("Error: kafka-python not installed. Run: pip install kafka-python", file=sys.stderr)
    sys.exit(1)

# Import generated protobuf classes
# Note: This assumes user_service_pb2.py has been generated
try:
    import user_service_pb2 as pb
    from google.protobuf.timestamp_pb2 import Timestamp
except ImportError:
    print("Error: Generated protobuf code not found.", file=sys.stderr)
    print("Run: protoc --python_out=. user_service.proto", file=sys.stderr)
    sys.exit(1)


class ProtobufSerializer:
    """Serializer for Protocol Buffer messages"""

    @staticmethod
    def serialize(message) -> bytes:
        """Serialize protobuf message to bytes"""
        return message.SerializeToString()

    @staticmethod
    def deserialize(data: bytes, message_type):
        """Deserialize bytes to protobuf message"""
        message = message_type()
        message.ParseFromString(data)
        return message


class UserEventProducer:
    """Kafka producer for user events using Protocol Buffers"""

    def __init__(self, bootstrap_servers: str = "localhost:9092", topic: str = "user-events"):
        self.topic = topic
        self.serializer = ProtobufSerializer()

        # Create Kafka producer with custom serializer
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: v,  # We'll handle serialization
            compression_type='snappy',  # Compress messages
            acks='all',  # Wait for all replicas
            retries=3
        )

        print(f"Producer initialized: {bootstrap_servers}")
        print(f"Topic: {topic}")

    def create_user_event(self, user_id: str, email: str, display_name: str) -> pb.User:
        """Create a User protobuf message"""
        user = pb.User()
        user.id = user_id
        user.email = email
        user.display_name = display_name
        user.status = pb.USER_STATUS_ACTIVE
        user.role = pb.USER_ROLE_USER
        user.email_verified = False

        # Set timestamps
        now = Timestamp()
        now.GetCurrentTime()
        user.created_at.CopyFrom(now)
        user.updated_at.CopyFrom(now)

        # Set profile
        user.profile.timezone = "UTC"
        user.profile.language = "en"

        # Set metadata
        user.metadata["source"] = "kafka_example"
        user.metadata["version"] = "1.0"

        return user

    def send_user_created(self, user: pb.User) -> None:
        """Send user created event"""
        try:
            # Serialize protobuf to bytes
            value = self.serializer.serialize(user)

            # Use user ID as key for partitioning
            key = user.id.encode('utf-8')

            # Send to Kafka
            future = self.producer.send(
                self.topic,
                key=key,
                value=value,
                headers=[
                    ('event_type', b'user.created'),
                    ('schema_version', b'v1'),
                    ('content_type', b'application/x-protobuf')
                ]
            )

            # Wait for confirmation
            record_metadata = future.get(timeout=10)

            print(f"✓ Sent user.created event:")
            print(f"    User ID: {user.id}")
            print(f"    Email: {user.email}")
            print(f"    Partition: {record_metadata.partition}")
            print(f"    Offset: {record_metadata.offset}")
            print(f"    Size: {len(value)} bytes")
            print()

        except KafkaError as e:
            print(f"✗ Failed to send message: {e}", file=sys.stderr)

    def send_multiple(self, count: int = 10) -> None:
        """Send multiple test messages"""
        print(f"Sending {count} user events...")
        print()

        for i in range(count):
            user = self.create_user_event(
                user_id=f"user-{i:04d}",
                email=f"user{i}@example.com",
                display_name=f"User {i}"
            )
            self.send_user_created(user)
            time.sleep(0.1)  # Small delay

        self.producer.flush()
        print(f"✓ Sent {count} events successfully")

    def close(self) -> None:
        """Close producer"""
        self.producer.close()
        print("Producer closed")


class UserEventConsumer:
    """Kafka consumer for user events using Protocol Buffers"""

    def __init__(self, bootstrap_servers: str = "localhost:9092", topic: str = "user-events", group_id: str = "user-consumer-group"):
        self.topic = topic
        self.serializer = ProtobufSerializer()

        # Create Kafka consumer
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda v: v,  # We'll handle deserialization
            auto_offset_reset='earliest',  # Start from beginning
            enable_auto_commit=True,
            auto_commit_interval_ms=1000
        )

        print(f"Consumer initialized: {bootstrap_servers}")
        print(f"Topic: {topic}")
        print(f"Group ID: {group_id}")
        print()

    def consume(self, max_messages: Optional[int] = None) -> None:
        """Consume and process messages"""
        print("Consuming messages... (Ctrl+C to stop)")
        print()

        message_count = 0

        try:
            for message in self.consumer:
                # Deserialize protobuf
                user = self.serializer.deserialize(message.value, pb.User)

                # Extract headers
                headers = {k: v.decode('utf-8') for k, v in message.headers}

                # Process message
                print(f"✓ Received message:")
                print(f"    Partition: {message.partition}")
                print(f"    Offset: {message.offset}")
                print(f"    Key: {message.key.decode('utf-8')}")
                print(f"    Headers: {headers}")
                print(f"    User:")
                print(f"      ID: {user.id}")
                print(f"      Email: {user.email}")
                print(f"      Display Name: {user.display_name}")
                print(f"      Status: {pb.UserStatus.Name(user.status)}")
                print(f"      Role: {pb.UserRole.Name(user.role)}")
                print(f"      Created: {user.created_at.ToDatetime()}")
                print(f"    Size: {len(message.value)} bytes")
                print()

                message_count += 1

                if max_messages and message_count >= max_messages:
                    break

        except KeyboardInterrupt:
            print("\nStopping consumer...")

        finally:
            print(f"\nProcessed {message_count} messages")

    def close(self) -> None:
        """Close consumer"""
        self.consumer.close()
        print("Consumer closed")


def compare_sizes() -> None:
    """Compare message sizes: Protobuf vs JSON"""
    print("Comparing message sizes: Protobuf vs JSON")
    print("=" * 60)

    # Create protobuf message
    user = pb.User()
    user.id = "user-12345"
    user.email = "user@example.com"
    user.display_name = "John Doe"
    user.status = pb.USER_STATUS_ACTIVE
    user.role = pb.USER_ROLE_USER

    now = Timestamp()
    now.GetCurrentTime()
    user.created_at.CopyFrom(now)
    user.updated_at.CopyFrom(now)

    # Serialize to protobuf
    protobuf_bytes = user.SerializeToString()

    # Serialize to JSON (approximate equivalent)
    json_data = {
        "id": "user-12345",
        "email": "user@example.com",
        "display_name": "John Doe",
        "status": 1,
        "role": 1,
        "created_at": now.ToDatetime().isoformat(),
        "updated_at": now.ToDatetime().isoformat()
    }
    json_bytes = json.dumps(json_data).encode('utf-8')

    # Compare
    print(f"Protobuf size: {len(protobuf_bytes)} bytes")
    print(f"JSON size: {len(json_bytes)} bytes")
    print(f"Savings: {len(json_bytes) - len(protobuf_bytes)} bytes ({100 * (1 - len(protobuf_bytes) / len(json_bytes)):.1f}%)")
    print()

    # Show what's in each
    print("Protobuf (hex):")
    print(protobuf_bytes.hex()[:100] + "...")
    print()

    print("JSON:")
    print(json.dumps(json_data, indent=2))
    print()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Kafka with Protocol Buffers example",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--mode',
        choices=['producer', 'consumer', 'compare'],
        required=True,
        help="Run mode: producer, consumer, or compare"
    )

    parser.add_argument(
        '--bootstrap-servers',
        default='localhost:9092',
        help="Kafka bootstrap servers (default: localhost:9092)"
    )

    parser.add_argument(
        '--topic',
        default='user-events',
        help="Kafka topic (default: user-events)"
    )

    parser.add_argument(
        '--count',
        type=int,
        default=10,
        help="Number of messages to send (producer mode, default: 10)"
    )

    parser.add_argument(
        '--group-id',
        default='user-consumer-group',
        help="Consumer group ID (consumer mode, default: user-consumer-group)"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point"""
    args = parse_args()

    if args.mode == 'compare':
        compare_sizes()
        return 0

    elif args.mode == 'producer':
        producer = UserEventProducer(
            bootstrap_servers=args.bootstrap_servers,
            topic=args.topic
        )

        try:
            producer.send_multiple(count=args.count)
        finally:
            producer.close()

        return 0

    elif args.mode == 'consumer':
        consumer = UserEventConsumer(
            bootstrap_servers=args.bootstrap_servers,
            topic=args.topic,
            group_id=args.group_id
        )

        try:
            consumer.consume()
        finally:
            consumer.close()

        return 0

    return 1


if __name__ == '__main__':
    sys.exit(main())
