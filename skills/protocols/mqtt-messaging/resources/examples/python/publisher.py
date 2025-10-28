#!/usr/bin/env python3
"""
MQTT Publisher Example

Production-ready MQTT publisher with error handling, reconnection, and CLI interface.

Usage:
    python publisher.py --broker mqtt.example.com --topic sensors/temp --message "22.5"
    python publisher.py --broker localhost --topic home/bedroom/temp --message "23.0" --qos 1 --retain
"""

import argparse
import json
import logging
import sys
import time
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MQTTPublisher:
    """Production MQTT Publisher"""

    def __init__(self, broker: str, port: int = 1883, client_id: str = None,
                 username: str = None, password: str = None):
        self.broker = broker
        self.port = port
        self.client_id = client_id or f"publisher_{int(time.time())}"
        self.client = mqtt.Client(client_id=self.client_id, clean_session=False)

        # Credentials
        if username and password:
            self.client.username_pw_set(username, password)

        # Callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        self.client.on_log = self.on_log

        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        """Connection callback"""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to {self.broker}:{self.port}")
        else:
            logger.error(f"Connection failed: {rc}")

    def on_disconnect(self, client, userdata, rc):
        """Disconnection callback"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnect: {rc}, reconnecting...")
        else:
            logger.info("Disconnected gracefully")

    def on_publish(self, client, userdata, mid):
        """Publish callback"""
        logger.debug(f"Message {mid} published")

    def on_log(self, client, userdata, level, buf):
        """Logging callback"""
        if level == mqtt.MQTT_LOG_ERR:
            logger.error(f"MQTT: {buf}")

    def connect(self):
        """Connect to broker"""
        try:
            logger.info(f"Connecting to {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()

            # Wait for connection
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1

            if not self.connected:
                raise ConnectionError("Connection timeout")

            return True

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from broker"""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected")

    def publish(self, topic: str, payload: any, qos: int = 0, retain: bool = False):
        """Publish message"""
        if not self.connected:
            logger.error("Not connected")
            return False

        # Convert payload to string if needed
        if isinstance(payload, dict) or isinstance(payload, list):
            payload = json.dumps(payload)
        elif not isinstance(payload, (str, bytes)):
            payload = str(payload)

        try:
            result = self.client.publish(topic, payload, qos=qos, retain=retain)

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Publish failed: {result.rc}")
                return False

            # Wait for QoS 1/2
            if qos > 0:
                result.wait_for_publish()

            logger.info(f"Published to {topic}: {payload[:50]}{'...' if len(str(payload)) > 50 else ''}")
            return True

        except Exception as e:
            logger.error(f"Publish exception: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="MQTT Publisher")
    parser.add_argument('--broker', required=True, help='MQTT broker hostname')
    parser.add_argument('--port', type=int, default=1883, help='Broker port')
    parser.add_argument('--client-id', help='Client ID')
    parser.add_argument('--username', help='Username')
    parser.add_argument('--password', help='Password')
    parser.add_argument('--topic', required=True, help='Topic to publish to')
    parser.add_argument('--message', required=True, help='Message payload')
    parser.add_argument('--qos', type=int, choices=[0, 1, 2], default=0, help='QoS level')
    parser.add_argument('--retain', action='store_true', help='Retain message')
    parser.add_argument('--json', action='store_true', help='Parse message as JSON')

    args = parser.parse_args()

    # Parse JSON payload if requested
    payload = args.message
    if args.json:
        try:
            payload = json.loads(args.message)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            sys.exit(1)

    # Create publisher
    publisher = MQTTPublisher(
        broker=args.broker,
        port=args.port,
        client_id=args.client_id,
        username=args.username,
        password=args.password
    )

    # Connect
    if not publisher.connect():
        sys.exit(1)

    # Publish
    success = publisher.publish(
        topic=args.topic,
        payload=payload,
        qos=args.qos,
        retain=args.retain
    )

    # Disconnect
    time.sleep(1)
    publisher.disconnect()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
