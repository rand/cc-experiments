#!/usr/bin/env python3
"""
MQTT QoS Testing Tool

Tests MQTT QoS levels (0, 1, 2) and measures delivery guarantees, latency,
message loss, and duplicates.

Usage:
    ./test_mqtt_qos.py --broker mqtt.example.com --test-all
    ./test_mqtt_qos.py --broker localhost --qos 1 --count 100
    ./test_mqtt_qos.py --broker mqtt.example.com --test-retained
    ./test_mqtt_qos.py --broker mqtt.example.com --test-lwt --json
"""

import argparse
import json
import sys
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import paho.mqtt.client as mqtt

@dataclass
class QoSTestResult:
    """Results from QoS testing"""
    qos: int
    messages_sent: int = 0
    messages_received: int = 0
    duplicates: int = 0
    loss_rate: float = 0.0
    latencies: List[float] = field(default_factory=list)
    min_latency: float = 0.0
    avg_latency: float = 0.0
    p95_latency: float = 0.0
    max_latency: float = 0.0
    errors: List[str] = field(default_factory=list)

@dataclass
class TestSuite:
    """Complete test suite results"""
    broker: str
    port: int
    timestamp: float = field(default_factory=time.time)
    qos_tests: Dict[int, QoSTestResult] = field(default_factory=dict)
    retained_test: Optional[Dict] = None
    lwt_test: Optional[Dict] = None

class MQTTQoSTester:
    """Tests MQTT QoS levels"""

    def __init__(self, broker: str, port: int = 1883, username: Optional[str] = None,
                 password: Optional[str] = None):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.verbose = False

    def test_qos(self, qos: int, count: int = 100, timeout: int = 10) -> QoSTestResult:
        """Test specific QoS level"""
        result = QoSTestResult(qos=qos)
        received_messages = {}
        message_times = {}
        lock = threading.Lock()
        connected = threading.Event()
        subscribed = threading.Event()

        # Subscriber client
        sub_client = mqtt.Client(client_id=f"qos_test_sub_{qos}")
        if self.username and self.password:
            sub_client.username_pw_set(self.username, self.password)

        def on_connect_sub(client, userdata, flags, rc):
            if rc == 0:
                connected.set()
                client.subscribe(f"test/qos/{qos}", qos=qos)
            else:
                result.errors.append(f"Subscriber connection failed: {rc}")

        def on_subscribe(client, userdata, mid, granted_qos):
            subscribed.set()

        def on_message(client, userdata, msg):
            try:
                msg_id = int(msg.payload.decode())
                recv_time = time.time()

                with lock:
                    if msg_id in received_messages:
                        result.duplicates += 1
                    else:
                        received_messages[msg_id] = recv_time
                        result.messages_received += 1

                        # Calculate latency
                        if msg_id in message_times:
                            latency = recv_time - message_times[msg_id]
                            result.latencies.append(latency)

            except Exception as e:
                result.errors.append(f"Message processing error: {e}")

        sub_client.on_connect = on_connect_sub
        sub_client.on_subscribe = on_subscribe
        sub_client.on_message = on_message

        try:
            # Connect subscriber
            sub_client.connect(self.broker, self.port, keepalive=60)
            sub_client.loop_start()

            if not connected.wait(timeout=5):
                result.errors.append("Subscriber connection timeout")
                return result

            if not subscribed.wait(timeout=5):
                result.errors.append("Subscription timeout")
                return result

            time.sleep(1)  # Wait for subscription to be fully active

            # Publisher client
            pub_client = mqtt.Client(client_id=f"qos_test_pub_{qos}")
            if self.username and self.password:
                pub_client.username_pw_set(self.username, self.password)

            pub_connected = threading.Event()

            def on_connect_pub(client, userdata, flags, rc):
                if rc == 0:
                    pub_connected.set()
                else:
                    result.errors.append(f"Publisher connection failed: {rc}")

            pub_client.on_connect = on_connect_pub

            # Connect publisher
            pub_client.connect(self.broker, self.port, keepalive=60)
            pub_client.loop_start()

            if not pub_connected.wait(timeout=5):
                result.errors.append("Publisher connection timeout")
                return result

            # Publish messages
            if self.verbose:
                print(f"Publishing {count} messages with QoS {qos}...")

            for i in range(count):
                send_time = time.time()
                message_times[i] = send_time

                info = pub_client.publish(
                    f"test/qos/{qos}",
                    payload=str(i),
                    qos=qos
                )

                if info.rc != mqtt.MQTT_ERR_SUCCESS:
                    result.errors.append(f"Publish failed for message {i}: {info.rc}")
                else:
                    result.messages_sent += 1

                # Small delay for QoS 0 to avoid overwhelming
                if qos == 0:
                    time.sleep(0.001)

            # Wait for QoS 1/2 to complete
            if qos > 0:
                time.sleep(2)

            # Wait for messages to arrive
            wait_time = 0
            while wait_time < timeout:
                with lock:
                    if result.messages_received >= result.messages_sent:
                        break
                time.sleep(0.1)
                wait_time += 0.1

            # Calculate statistics
            with lock:
                if result.messages_sent > 0:
                    lost = result.messages_sent - result.messages_received
                    result.loss_rate = (lost / result.messages_sent) * 100.0

                if result.latencies:
                    result.latencies.sort()
                    result.min_latency = result.latencies[0]
                    result.max_latency = result.latencies[-1]
                    result.avg_latency = sum(result.latencies) / len(result.latencies)
                    p95_idx = int(len(result.latencies) * 0.95)
                    result.p95_latency = result.latencies[p95_idx] if p95_idx < len(result.latencies) else result.max_latency

            # Cleanup
            pub_client.loop_stop()
            pub_client.disconnect()

        except Exception as e:
            result.errors.append(f"Test exception: {e}")

        finally:
            sub_client.loop_stop()
            sub_client.disconnect()

        return result

    def test_retained(self, timeout: int = 10) -> Dict:
        """Test retained messages"""
        result = {
            "success": False,
            "retained_received": False,
            "retained_cleared": False,
            "errors": []
        }

        retained_msg = f"retained_test_{time.time()}"
        received = threading.Event()
        cleared = threading.Event()

        # Publisher
        pub_client = mqtt.Client(client_id="retained_test_pub")
        if self.username and self.password:
            pub_client.username_pw_set(self.username, self.password)

        try:
            pub_client.connect(self.broker, self.port, keepalive=60)
            pub_client.loop_start()
            time.sleep(1)

            # Publish retained message
            if self.verbose:
                print("Publishing retained message...")

            pub_client.publish("test/retained", retained_msg, qos=1, retain=True)
            time.sleep(1)

            # New subscriber should receive retained message
            sub_client = mqtt.Client(client_id="retained_test_sub")
            if self.username and self.password:
                sub_client.username_pw_set(self.username, self.password)

            def on_message_retained(client, userdata, msg):
                if msg.payload.decode() == retained_msg and msg.retain:
                    received.set()

            sub_client.on_message = on_message_retained
            sub_client.connect(self.broker, self.port, keepalive=60)
            sub_client.subscribe("test/retained", qos=1)
            sub_client.loop_start()

            # Wait for retained message
            if received.wait(timeout=timeout):
                result["retained_received"] = True
                if self.verbose:
                    print("✓ Retained message received")
            else:
                result["errors"].append("Retained message not received")

            # Clear retained message
            if self.verbose:
                print("Clearing retained message...")

            pub_client.publish("test/retained", "", qos=1, retain=True)
            time.sleep(1)

            # New subscriber should not receive retained message
            sub_client.loop_stop()
            sub_client.disconnect()

            sub_client2 = mqtt.Client(client_id="retained_test_sub2")
            if self.username and self.password:
                sub_client2.username_pw_set(self.username, self.password)

            received_after_clear = [False]

            def on_message_cleared(client, userdata, msg):
                if msg.topic == "test/retained":
                    received_after_clear[0] = True

            sub_client2.on_message = on_message_cleared
            sub_client2.connect(self.broker, self.port, keepalive=60)
            sub_client2.subscribe("test/retained", qos=1)
            sub_client2.loop_start()

            time.sleep(2)

            if not received_after_clear[0]:
                result["retained_cleared"] = True
                if self.verbose:
                    print("✓ Retained message cleared")
            else:
                result["errors"].append("Retained message not cleared")

            # Cleanup
            sub_client2.loop_stop()
            sub_client2.disconnect()
            pub_client.loop_stop()
            pub_client.disconnect()

            result["success"] = result["retained_received"] and result["retained_cleared"]

        except Exception as e:
            result["errors"].append(f"Test exception: {e}")

        return result

    def test_lwt(self, timeout: int = 10) -> Dict:
        """Test Last Will and Testament"""
        result = {
            "success": False,
            "lwt_received": False,
            "errors": []
        }

        lwt_msg = f"offline_{time.time()}"
        lwt_received = threading.Event()

        # Subscriber
        sub_client = mqtt.Client(client_id="lwt_test_sub")
        if self.username and self.password:
            sub_client.username_pw_set(self.username, self.password)

        def on_message_lwt(client, userdata, msg):
            if msg.payload.decode() == lwt_msg:
                lwt_received.set()

        sub_client.on_message = on_message_lwt

        try:
            sub_client.connect(self.broker, self.port, keepalive=60)
            sub_client.subscribe("test/lwt", qos=1)
            sub_client.loop_start()
            time.sleep(1)

            # Client with LWT
            lwt_client = mqtt.Client(client_id="lwt_test_client")
            if self.username and self.password:
                lwt_client.username_pw_set(self.username, self.password)

            # Set LWT before connecting
            lwt_client.will_set("test/lwt", lwt_msg, qos=1, retain=False)

            if self.verbose:
                print("Connecting client with LWT...")

            lwt_client.connect(self.broker, self.port, keepalive=5)  # Short keepalive
            lwt_client.loop_start()
            time.sleep(1)

            # Publish online status
            lwt_client.publish("test/lwt", "online", qos=1)
            time.sleep(1)

            # Simulate unexpected disconnect (hard exit)
            if self.verbose:
                print("Simulating unexpected disconnect...")

            # Force disconnect without DISCONNECT packet
            lwt_client._sock.close()
            lwt_client.loop_stop()

            # Wait for LWT (broker will publish after keepalive timeout ~7.5s)
            if lwt_received.wait(timeout=timeout):
                result["lwt_received"] = True
                result["success"] = True
                if self.verbose:
                    print("✓ LWT message received")
            else:
                result["errors"].append("LWT message not received within timeout")

            # Cleanup
            sub_client.loop_stop()
            sub_client.disconnect()

        except Exception as e:
            result["errors"].append(f"Test exception: {e}")

        return result

def format_qos_result(result: QoSTestResult) -> str:
    """Format QoS test result"""
    lines = [f"QoS {result.qos} Test Results:"]
    lines.append(f"  Messages sent: {result.messages_sent}")
    lines.append(f"  Messages received: {result.messages_received}")
    lines.append(f"  Duplicates: {result.duplicates}")
    lines.append(f"  Loss rate: {result.loss_rate:.2f}%")

    if result.latencies:
        lines.append(f"  Latency (ms):")
        lines.append(f"    Min: {result.min_latency * 1000:.2f}")
        lines.append(f"    Avg: {result.avg_latency * 1000:.2f}")
        lines.append(f"    P95: {result.p95_latency * 1000:.2f}")
        lines.append(f"    Max: {result.max_latency * 1000:.2f}")

    if result.errors:
        lines.append(f"  Errors:")
        for error in result.errors:
            lines.append(f"    - {error}")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(
        description="Test MQTT QoS levels and delivery guarantees",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all QoS levels
  %(prog)s --broker mqtt.example.com --test-all

  # Test specific QoS
  %(prog)s --broker localhost --qos 1 --count 100

  # Test retained messages
  %(prog)s --broker mqtt.example.com --test-retained

  # Test Last Will and Testament
  %(prog)s --broker mqtt.example.com --test-lwt

  # JSON output
  %(prog)s --broker mqtt.example.com --test-all --json
        """
    )

    parser.add_argument(
        '--broker',
        required=True,
        help='MQTT broker hostname'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=1883,
        help='MQTT broker port (default: 1883)'
    )
    parser.add_argument(
        '--username',
        help='MQTT username'
    )
    parser.add_argument(
        '--password',
        help='MQTT password'
    )
    parser.add_argument(
        '--qos',
        type=int,
        choices=[0, 1, 2],
        help='Test specific QoS level (0, 1, or 2)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=100,
        help='Number of messages to send (default: 100)'
    )
    parser.add_argument(
        '--test-all',
        action='store_true',
        help='Test all QoS levels (0, 1, 2)'
    )
    parser.add_argument(
        '--test-retained',
        action='store_true',
        help='Test retained messages'
    )
    parser.add_argument(
        '--test-lwt',
        action='store_true',
        help='Test Last Will and Testament'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Test timeout in seconds (default: 10)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    if not any([args.qos is not None, args.test_all, args.test_retained, args.test_lwt]):
        parser.print_help()
        sys.exit(1)

    tester = MQTTQoSTester(
        broker=args.broker,
        port=args.port,
        username=args.username,
        password=args.password
    )
    tester.verbose = args.verbose

    suite = TestSuite(broker=args.broker, port=args.port)

    # Test specific QoS
    if args.qos is not None:
        if args.verbose:
            print(f"Testing QoS {args.qos}...")
        result = tester.test_qos(args.qos, count=args.count, timeout=args.timeout)
        suite.qos_tests[args.qos] = result

    # Test all QoS levels
    if args.test_all:
        for qos in [0, 1, 2]:
            if args.verbose:
                print(f"\nTesting QoS {qos}...")
            result = tester.test_qos(qos, count=args.count, timeout=args.timeout)
            suite.qos_tests[qos] = result

    # Test retained messages
    if args.test_retained:
        if args.verbose:
            print("\nTesting retained messages...")
        suite.retained_test = tester.test_retained(timeout=args.timeout)

    # Test LWT
    if args.test_lwt:
        if args.verbose:
            print("\nTesting Last Will and Testament...")
        suite.lwt_test = tester.test_lwt(timeout=args.timeout)

    # Output results
    if args.json:
        output = {
            "broker": suite.broker,
            "port": suite.port,
            "timestamp": suite.timestamp,
            "qos_tests": {
                qos: asdict(result) for qos, result in suite.qos_tests.items()
            },
            "retained_test": suite.retained_test,
            "lwt_test": suite.lwt_test
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n=== MQTT QoS Test Results ===")
        print(f"Broker: {suite.broker}:{suite.port}\n")

        for qos, result in suite.qos_tests.items():
            print(format_qos_result(result))
            print()

        if suite.retained_test:
            print("Retained Messages Test:")
            print(f"  Success: {suite.retained_test['success']}")
            print(f"  Retained received: {suite.retained_test['retained_received']}")
            print(f"  Retained cleared: {suite.retained_test['retained_cleared']}")
            if suite.retained_test['errors']:
                print("  Errors:")
                for error in suite.retained_test['errors']:
                    print(f"    - {error}")
            print()

        if suite.lwt_test:
            print("Last Will and Testament Test:")
            print(f"  Success: {suite.lwt_test['success']}")
            print(f"  LWT received: {suite.lwt_test['lwt_received']}")
            if suite.lwt_test['errors']:
                print("  Errors:")
                for error in suite.lwt_test['errors']:
                    print(f"    - {error}")
            print()

    # Exit code
    all_success = all(
        len(result.errors) == 0 for result in suite.qos_tests.values()
    )
    if suite.retained_test:
        all_success = all_success and suite.retained_test['success']
    if suite.lwt_test:
        all_success = all_success and suite.lwt_test['success']

    sys.exit(0 if all_success else 1)

if __name__ == "__main__":
    main()
