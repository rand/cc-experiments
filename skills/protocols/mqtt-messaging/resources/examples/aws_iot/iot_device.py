#!/usr/bin/env python3
"""
AWS IoT Core Device Example

Example IoT device connecting to AWS IoT Core using certificates.

Prerequisites:
    pip install AWSIoTPythonSDK

Usage:
    python iot_device.py --endpoint xxx.iot.us-east-1.amazonaws.com --thing my_device
"""

import argparse
import json
import logging
import sys
import time
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IoTDevice:
    """AWS IoT Core Device"""

    def __init__(self, endpoint: str, thing_name: str, root_ca: str,
                 cert_path: str, key_path: str):
        self.endpoint = endpoint
        self.thing_name = thing_name

        # Initialize client
        self.client = AWSIoTMQTTClient(thing_name)
        self.client.configureEndpoint(endpoint, 8883)
        self.client.configureCredentials(root_ca, key_path, cert_path)

        # Connection settings
        self.client.configureAutoReconnectBackoffTime(1, 32, 20)
        self.client.configureOfflinePublishQueueing(-1)  # Infinite
        self.client.configureDrainingFrequency(2)  # 2 Hz
        self.client.configureConnectDisconnectTimeout(10)
        self.client.configureMQTTOperationTimeout(5)

    def connect(self):
        """Connect to AWS IoT Core"""
        try:
            logger.info(f"Connecting to {self.endpoint}...")
            self.client.connect()
            logger.info("Connected to AWS IoT Core")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def publish_telemetry(self, data: dict):
        """Publish telemetry data"""
        topic = f"dt/{self.thing_name}/telemetry"
        payload = json.dumps(data)

        try:
            self.client.publish(topic, payload, 1)
            logger.info(f"Published telemetry: {data}")
            return True
        except Exception as e:
            logger.error(f"Publish failed: {e}")
            return False

    def subscribe_commands(self, callback):
        """Subscribe to command topic"""
        topic = f"cmd/{self.thing_name}/#"

        def command_callback(client, userdata, message):
            payload = json.loads(message.payload)
            callback(message.topic, payload)

        self.client.subscribe(topic, 1, command_callback)
        logger.info(f"Subscribed to {topic}")

    def update_shadow(self, state: dict):
        """Update device shadow"""
        topic = f"$aws/things/{self.thing_name}/shadow/update"
        payload = json.dumps({"state": state})

        try:
            self.client.publish(topic, payload, 1)
            logger.info(f"Updated shadow: {state}")
            return True
        except Exception as e:
            logger.error(f"Shadow update failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from AWS IoT Core"""
        self.client.disconnect()
        logger.info("Disconnected")

def main():
    parser = argparse.ArgumentParser(description="AWS IoT Device")
    parser.add_argument('--endpoint', required=True, help='IoT endpoint')
    parser.add_argument('--thing', required=True, help='Thing name')
    parser.add_argument('--root-ca', default='AmazonRootCA1.pem')
    parser.add_argument('--cert', default='device.pem.crt')
    parser.add_argument('--key', default='device.pem.key')

    args = parser.parse_args()

    # Create device
    device = IoTDevice(
        endpoint=args.endpoint,
        thing_name=args.thing,
        root_ca=args.root_ca,
        cert_path=args.cert,
        key_path=args.key
    )

    # Connect
    if not device.connect():
        sys.exit(1)

    # Subscribe to commands
    def handle_command(topic, payload):
        logger.info(f"Received command: {topic} -> {payload}")

    device.subscribe_commands(handle_command)

    # Publish telemetry loop
    try:
        count = 0
        while True:
            telemetry = {
                "temperature": 20 + (count % 10),
                "humidity": 60 + (count % 20),
                "timestamp": int(time.time())
            }

            device.publish_telemetry(telemetry)

            # Update shadow
            if count % 10 == 0:
                device.update_shadow({
                    "reported": {
                        "online": True,
                        "uptime": count * 5
                    }
                })

            time.sleep(5)
            count += 1

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        device.disconnect()

if __name__ == "__main__":
    main()
