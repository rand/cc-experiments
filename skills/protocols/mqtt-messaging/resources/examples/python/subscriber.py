#!/usr/bin/env python3
"""
MQTT Subscriber Example

Production-ready MQTT subscriber with message handling, reconnection, and CLI.

Usage:
    python subscriber.py --broker mqtt.example.com --topic "sensors/#"
    python subscriber.py --broker localhost --topic "home/+/temp" --qos 1
"""

import argparse
import json
import logging
import signal
import sys
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MQTTSubscriber:
    """Production MQTT Subscriber"""

    def __init__(self, broker: str, port: int = 1883, client_id: str = None,
                 username: str = None, password: str = None):
        self.broker = broker
        self.port = port
        self.client_id = client_id or f"subscriber_{int(time.time())}"
        self.client = mqtt.Client(client_id=self.client_id, clean_session=False)

        # Credentials
        if username and password:
            self.client.username_pw_set(username, password)

        # Callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe

        self.subscriptions = {}
        self.running = False

    def on_connect(self, client, userdata, flags, rc):
        """Connection callback"""
        if rc == 0:
            logger.info(f"Connected to {self.broker}:{self.port}")
            # Resubscribe to topics
            for topic, qos in self.subscriptions.items():
                client.subscribe(topic, qos)
        else:
            logger.error(f"Connection failed: {rc}")

    def on_disconnect(self, client, userdata, rc):
        """Disconnection callback"""
        if rc != 0:
            logger.warning(f"Unexpected disconnect: {rc}, will reconnect...")
        else:
            logger.info("Disconnected gracefully")

    def on_message(self, client, userdata, msg):
        """Message callback"""
        payload = msg.payload.decode()

        # Try to parse as JSON
        try:
            payload_json = json.loads(payload)
            logger.info(f"[{msg.topic}] (QoS {msg.qos}, retain={msg.retain}) {json.dumps(payload_json, indent=2)}")
        except:
            logger.info(f"[{msg.topic}] (QoS {msg.qos}, retain={msg.retain}) {payload}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """Subscribe callback"""
        logger.info(f"Subscribed (granted QoS: {granted_qos})")

    def connect(self):
        """Connect to broker"""
        try:
            logger.info(f"Connecting to {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, keepalive=60)
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def subscribe(self, topic: str, qos: int = 0):
        """Subscribe to topic"""
        self.subscriptions[topic] = qos
        self.client.subscribe(topic, qos)
        logger.info(f"Subscribing to {topic} (QoS {qos})")

    def start(self):
        """Start subscriber loop"""
        self.running = True
        self.client.loop_forever()

    def stop(self):
        """Stop subscriber"""
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Stopped")

def main():
    parser = argparse.ArgumentParser(description="MQTT Subscriber")
    parser.add_argument('--broker', required=True, help='MQTT broker hostname')
    parser.add_argument('--port', type=int, default=1883, help='Broker port')
    parser.add_argument('--client-id', help='Client ID')
    parser.add_argument('--username', help='Username')
    parser.add_argument('--password', help='Password')
    parser.add_argument('--topic', required=True, help='Topic to subscribe to')
    parser.add_argument('--qos', type=int, choices=[0, 1, 2], default=0, help='QoS level')

    args = parser.parse_args()

    # Create subscriber
    subscriber = MQTTSubscriber(
        broker=args.broker,
        port=args.port,
        client_id=args.client_id,
        username=args.username,
        password=args.password
    )

    # Connect
    if not subscriber.connect():
        sys.exit(1)

    # Subscribe
    subscriber.subscribe(topic=args.topic, qos=args.qos)

    # Handle signals
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        subscriber.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start
    logger.info("Listening for messages (Ctrl+C to exit)...")
    subscriber.start()

if __name__ == "__main__":
    import time
    main()
