---
name: protocols-mqtt-messaging
description: MQTT pub-sub messaging for IoT and real-time applications
---

# MQTT Messaging

**Scope**: MQTT protocol, pub-sub patterns, QoS levels, broker configuration, IoT integration
**Lines**: ~400
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Implementing MQTT pub-sub messaging systems
- Building IoT device communication
- Designing lightweight messaging protocols
- Implementing real-time sensor data collection
- Setting up MQTT brokers (Mosquitto, EMQX, HiveMQ)
- Configuring QoS levels and message delivery guarantees
- Implementing retained messages and last will
- Designing topic hierarchies and wildcard subscriptions
- Securing MQTT with TLS and authentication
- Integrating with cloud IoT platforms (AWS IoT Core, Azure IoT Hub)

## Core Concepts

### MQTT Architecture

**MQTT** (Message Queuing Telemetry Transport): Lightweight pub-sub protocol designed for constrained devices and unreliable networks.

**Key characteristics**:
- **Publish-Subscribe**: Decoupled message pattern (publishers don't know subscribers)
- **Lightweight**: Minimal 2-byte header overhead
- **QoS levels**: Three levels of delivery guarantees (0, 1, 2)
- **TCP/IP transport**: Reliable, ordered delivery (or WebSocket for browsers)
- **Broker-based**: Central broker routes messages between clients
- **Topic-based routing**: Hierarchical topics with wildcard subscriptions

**Architecture components**:
```
Publisher → Broker → Subscriber(s)
            ↓
        Topics + QoS
            ↓
        Retained Messages
        Last Will Testament
```

---

## MQTT Basics

### Connection Flow

```
Client                              Broker
  |                                   |
  |-- CONNECT (clientId, auth) ----->|
  |                                   |
  |<-- CONNACK (session present) -----|
  |                                   |
  |-- SUBSCRIBE (topic, QoS) -------->|
  |                                   |
  |<-- SUBACK (granted QoS) ----------|
  |                                   |
  |-- PUBLISH (topic, payload, QoS) ->|
  |                                   |
  |<-- PUBACK (if QoS 1+) ------------|
  |                                   |
  |-- DISCONNECT ---------------------->|
```

### QoS Levels

**QoS 0 - At Most Once** (Fire and forget):
- No acknowledgment or retransmission
- Message may be lost
- Fastest, lowest overhead
- Use case: Non-critical data (sensor readings where loss is acceptable)

**QoS 1 - At Least Once** (Acknowledged delivery):
- Message acknowledged with PUBACK
- Message may be delivered multiple times
- Moderate overhead
- Use case: Important messages where duplicates are acceptable

**QoS 2 - Exactly Once** (Assured delivery):
- Four-way handshake (PUBLISH → PUBREC → PUBREL → PUBCOMP)
- Message delivered exactly once
- Highest overhead
- Use case: Critical messages (billing, alarms)

```python
# QoS comparison
qos_0 = client.publish("sensor/temp", "22.5", qos=0)  # No ACK
qos_1 = client.publish("sensor/temp", "22.5", qos=1)  # PUBACK required
qos_2 = client.publish("alarm/fire", "triggered", qos=2)  # 4-way handshake
```

---

## Topic Design

### Topic Hierarchy

Topics are UTF-8 strings using `/` as separator:

```
# Good topic hierarchy
home/bedroom/temperature
home/bedroom/humidity
home/livingroom/temperature
factory/line1/machine5/status
factory/line1/machine5/telemetry

# Topic components
{domain}/{location}/{device}/{measurement}
```

### Wildcards

**Single-level wildcard (`+`)**:
- Matches one topic level
- `home/+/temperature` matches `home/bedroom/temperature` and `home/kitchen/temperature`

**Multi-level wildcard (`#`)**:
- Matches zero or more topic levels (must be last character)
- `home/#` matches `home/bedroom/temperature` and `home/bedroom/humidity`

```python
# Wildcard subscriptions
client.subscribe("home/+/temperature")    # All rooms' temperature
client.subscribe("home/bedroom/#")        # All bedroom sensors
client.subscribe("#")                      # All topics (expensive!)
```

### Topic Best Practices

**DO**:
- Use hierarchical structure: `domain/location/device/metric`
- Keep topics descriptive and consistent
- Use lowercase with underscores: `home/living_room/temp`
- Limit topic depth (3-7 levels)
- Avoid leading/trailing slashes

**DON'T**:
- Don't use spaces or special characters
- Don't use topics starting with `$` (reserved for broker)
- Don't subscribe to `#` wildcard (high load)
- Don't embed data in topics: `sensor/temp/22.5` (use payload)

---

## Python Client Implementation

### Basic Publisher

```python
import paho.mqtt.client as mqtt
import json
import time

class MQTTPublisher:
    def __init__(self, broker, port=1883, client_id=None):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(client_id=client_id)

        # Callbacks
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to {self.broker}:{self.port}")
        else:
            print(f"Connection failed: {rc}")

    def on_publish(self, client, userdata, mid):
        print(f"Message {mid} published")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"Unexpected disconnect: {rc}")

    def connect(self):
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()

    def publish(self, topic, payload, qos=0, retain=False):
        """Publish message to topic"""
        if isinstance(payload, dict):
            payload = json.dumps(payload)

        result = self.client.publish(topic, payload, qos=qos, retain=retain)
        return result.mid

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

# Usage
publisher = MQTTPublisher("mqtt.example.com")
publisher.connect()

# Publish sensor data
publisher.publish("home/bedroom/temperature", "22.5", qos=1)
publisher.publish("home/bedroom/humidity", "65", qos=1)

# Publish JSON
publisher.publish("sensor/data", {
    "device_id": "sensor_01",
    "temperature": 22.5,
    "humidity": 65,
    "timestamp": time.time()
}, qos=1)

time.sleep(2)
publisher.disconnect()
```

### Basic Subscriber

```python
import paho.mqtt.client as mqtt
import json

class MQTTSubscriber:
    def __init__(self, broker, port=1883, client_id=None):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(client_id=client_id)

        # Callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.client.on_disconnect = self.on_disconnect

        # Message handlers
        self.handlers = {}

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to {self.broker}:{self.port}")
            # Resubscribe on reconnect
            for topic, qos in self.handlers.keys():
                client.subscribe(topic, qos)
        else:
            print(f"Connection failed: {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        qos = msg.qos

        print(f"Received: {topic} (QoS {qos}): {payload}")

        # Call registered handler
        for (handler_topic, handler_qos), handler_func in self.handlers.items():
            if self.topic_matches(topic, handler_topic):
                handler_func(topic, payload, qos)

    def on_subscribe(self, client, userdata, mid, granted_qos):
        print(f"Subscribed (QoS {granted_qos})")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"Unexpected disconnect: {rc}")

    def topic_matches(self, topic, pattern):
        """Check if topic matches pattern with wildcards"""
        # Simplified matching (paho does this internally)
        return mqtt.topic_matches_sub(pattern, topic)

    def connect(self):
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()

    def subscribe(self, topic, qos=0, handler=None):
        """Subscribe to topic with optional handler"""
        self.client.subscribe(topic, qos)
        if handler:
            self.handlers[(topic, qos)] = handler

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

# Usage
subscriber = MQTTSubscriber("mqtt.example.com")

# Register handler
def handle_temperature(topic, payload, qos):
    temp = float(payload)
    if temp > 25:
        print(f"High temperature alert: {temp}°C")

subscriber.subscribe("home/+/temperature", qos=1, handler=handle_temperature)
subscriber.connect()

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    subscriber.disconnect()
```

---

## Advanced Features

### Retained Messages

**Retained messages** are stored by the broker and delivered to new subscribers immediately.

```python
# Publish retained message (e.g., device status)
client.publish("device/status", "online", qos=1, retain=True)

# New subscribers immediately receive last retained message
# Use case: Device status, configuration, last known value
```

**Use cases**:
- Device online/offline status
- Last known sensor value
- System configuration

**Clear retained message**:
```python
client.publish("device/status", "", qos=1, retain=True)  # Empty payload clears
```

### Last Will and Testament (LWT)

**LWT** is a message automatically sent by broker if client disconnects unexpectedly.

```python
client = mqtt.Client()

# Set last will (sent if client disconnects without DISCONNECT)
client.will_set(
    topic="device/status",
    payload="offline",
    qos=1,
    retain=True
)

client.connect("mqtt.example.com")
# If client crashes or loses connection, broker publishes "offline"
```

**Use cases**:
- Device presence detection
- Connection monitoring
- Automatic cleanup

### Clean Session vs Persistent Session

**Clean Session = True** (default):
- Broker discards all session state on disconnect
- Subscriptions not preserved
- Queued messages discarded

**Clean Session = False** (persistent):
- Broker stores subscriptions and QoS 1+ messages
- Messages delivered when client reconnects
- Use same client ID to resume session

```python
# Persistent session
client = mqtt.Client(client_id="sensor_01", clean_session=False)
client.connect("mqtt.example.com")

# Subscribe with QoS 1
client.subscribe("commands/sensor_01", qos=1)

# Even if disconnected, messages are queued and delivered on reconnect
```

---

## Security

### TLS/SSL Encryption

```python
import ssl

client = mqtt.Client()

# TLS with server certificate verification
client.tls_set(
    ca_certs="/path/to/ca.crt",
    certfile="/path/to/client.crt",  # Optional client cert
    keyfile="/path/to/client.key",   # Optional client key
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.connect("mqtt.example.com", port=8883)  # TLS port
```

### Username/Password Authentication

```python
client = mqtt.Client()
client.username_pw_set(username="sensor_01", password="secret")
client.connect("mqtt.example.com")
```

### Token-Based Authentication (AWS IoT Core)

```python
# AWS IoT Core uses mutual TLS (certificate-based)
client = mqtt.Client()
client.tls_set(
    ca_certs="AmazonRootCA1.pem",
    certfile="device.pem.crt",
    keyfile="device.pem.key",
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.connect("xxxxxx-ats.iot.us-east-1.amazonaws.com", port=8883)
```

---

## MQTT Brokers

### Mosquitto (Open Source)

**Lightweight broker** for development and small deployments.

```bash
# Install
sudo apt-get install mosquitto mosquitto-clients

# Start broker
mosquitto -c /etc/mosquitto/mosquitto.conf

# Test with CLI
mosquitto_sub -h localhost -t "test/topic"
mosquitto_pub -h localhost -t "test/topic" -m "Hello"
```

**Configuration** (`/etc/mosquitto/mosquitto.conf`):
```
# Basic config
listener 1883
allow_anonymous true

# TLS config
listener 8883
cafile /path/to/ca.crt
certfile /path/to/server.crt
keyfile /path/to/server.key
require_certificate false

# Authentication
password_file /etc/mosquitto/passwd
```

### EMQX (Scalable, Enterprise)

**High-performance broker** for large-scale IoT deployments.

```bash
# Docker deployment
docker run -d --name emqx \
  -p 1883:1883 \
  -p 8083:8083 \
  -p 8084:8084 \
  -p 8883:8883 \
  -p 18083:18083 \
  emqx/emqx:latest

# Dashboard: http://localhost:18083 (admin/public)
```

**Features**:
- Clustering and scalability (millions of connections)
- Rule engine for data processing
- Built-in authentication (JWT, database, HTTP)
- Metrics and monitoring

### HiveMQ (Enterprise)

**Production-grade broker** with enterprise features.

**Features**:
- High availability and clustering
- Kafka integration
- Security (TLS, OAuth, LDAP)
- Management dashboard

---

## Common Patterns

### Request-Response Pattern

MQTT is pub-sub, but request-response can be implemented:

```python
# Client sends request with reply topic
request_payload = json.dumps({
    "command": "get_status",
    "reply_to": f"responses/{client_id}"
})

client.subscribe(f"responses/{client_id}", qos=1)
client.publish("commands/device_01", request_payload, qos=1)

# Device responds to reply_to topic
def on_message(client, userdata, msg):
    request = json.loads(msg.payload)
    reply_topic = request.get("reply_to")

    response = {"status": "online", "uptime": 3600}
    client.publish(reply_topic, json.dumps(response), qos=1)
```

### IoT Device Telemetry

```python
# Device sends periodic telemetry
def send_telemetry():
    while True:
        telemetry = {
            "device_id": "sensor_01",
            "temperature": read_temperature(),
            "humidity": read_humidity(),
            "battery": get_battery_level(),
            "timestamp": time.time()
        }

        client.publish(
            f"devices/{device_id}/telemetry",
            json.dumps(telemetry),
            qos=1
        )

        time.sleep(60)  # Every minute
```

### Command and Control

```python
# Backend sends commands to devices
client.publish(
    "commands/sensor_01/update_config",
    json.dumps({"interval": 30}),
    qos=1
)

# Device subscribes to commands
client.subscribe("commands/sensor_01/#", qos=1)

def on_message(client, userdata, msg):
    command = msg.topic.split("/")[-1]
    payload = json.loads(msg.payload)

    if command == "update_config":
        update_config(payload)
    elif command == "reboot":
        reboot_device()
```

---

## Anti-Patterns

❌ **Subscribing to `#` wildcard**: Receives all messages (broker load)
✅ Use specific wildcards: `home/+/temperature`

❌ **Using QoS 2 everywhere**: Highest overhead (4-way handshake)
✅ Use QoS 0 for non-critical data, QoS 1 for most cases, QoS 2 only when required

❌ **Large payloads (>1 MB)**: MQTT is for small messages
✅ Keep payloads small (<10 KB), use external storage for large data

❌ **Embedding data in topics**: `sensor/temp/22.5`
✅ Use topics for routing, payloads for data: `sensor/temp` with payload `22.5`

❌ **No authentication**: Open broker accessible to anyone
✅ Use TLS + username/password or client certificates

❌ **Ignoring connection failures**: No reconnection logic
✅ Implement exponential backoff reconnection

❌ **Not using retained messages for status**: Subscribers miss status
✅ Use retained messages for device status, config

---

## Level 3: Resources

### Overview

This skill includes comprehensive Level 3 resources for deep MQTT implementation knowledge and practical tools.

**Resources include**:
- **REFERENCE.md** (3,200+ lines): Complete technical reference covering MQTT protocol, brokers, patterns
- **3 executable scripts**: Config validation, QoS testing, broker benchmarking
- **7 production examples**: Complete implementations across brokers, platforms, languages

### REFERENCE.md

**Location**: `skills/protocols/mqtt-messaging/resources/REFERENCE.md`

**Comprehensive technical reference** (3,200+ lines) covering:

**Core Topics**:
- MQTT protocol fundamentals (v3.1.1, v5.0)
- Pub-sub architecture and message flow
- QoS levels (0, 1, 2) and delivery guarantees
- Topic design and wildcard patterns
- Connection management and keep-alive
- Retained messages and last will
- Clean vs persistent sessions
- Security (TLS, authentication, authorization)
- MQTT brokers (Mosquitto, EMQX, HiveMQ)
- MQTT over WebSocket
- AWS IoT Core integration
- Azure IoT Hub integration
- MQTT v5.0 features
- Performance optimization
- Testing strategies
- Anti-patterns

**Key Sections**:
1. **Protocol Fundamentals**: MQTT v3.1.1/v5.0, packet types, control packets
2. **QoS Levels**: Detailed flow diagrams for QoS 0/1/2
3. **Topic Design**: Hierarchies, wildcards, best practices
4. **Broker Setup**: Mosquitto, EMQX, HiveMQ configuration
5. **Security**: TLS/mTLS, authentication methods, authorization
6. **Client Implementation**: Python, Node.js, Go examples
7. **Cloud Integration**: AWS IoT Core, Azure IoT Hub
8. **MQTT v5.0**: New features (user properties, reason codes, shared subscriptions)
9. **Performance**: Connection pooling, batching, compression
10. **Anti-Patterns**: Common mistakes and solutions

**Format**: Markdown with extensive code examples in Python, Node.js, and shell scripts

### Scripts

Three production-ready executable scripts in `resources/scripts/`:

#### 1. validate_mqtt_config.py (550 lines)

**Purpose**: Validate MQTT broker and topic configurations

**Features**:
- Parse Mosquitto and EMQX config files
- Validate topic naming conventions
- Check security settings (TLS, auth)
- Detect misconfigurations
- Validate ACL rules
- Output as JSON or human-readable text

**Usage**:
```bash
# Validate Mosquitto config
./validate_mqtt_config.py --config /etc/mosquitto/mosquitto.conf

# JSON output
./validate_mqtt_config.py --config /etc/mosquitto/mosquitto.conf --json

# Check topics
./validate_mqtt_config.py --check-topics --topics-file topics.txt

# Validate ACL
./validate_mqtt_config.py --config mosquitto.conf --check-acl
```

**Checks**:
- **Config**: Listener ports, TLS settings, auth configuration
- **Topics**: Naming conventions, hierarchy depth, wildcard usage
- **Security**: TLS version, certificate paths, password files
- **ACL**: Permission rules, topic patterns, user access

#### 2. test_mqtt_qos.py (600 lines)

**Purpose**: Test MQTT QoS levels and message delivery

**Features**:
- Test QoS 0, 1, 2 delivery
- Measure message loss and duplicates
- Test retained messages
- Test last will and testament
- Connection reliability testing
- Latency measurements
- JSON output for CI/CD

**Usage**:
```bash
# Test all QoS levels
./test_mqtt_qos.py --broker mqtt.example.com --test-all

# Test QoS 1
./test_mqtt_qos.py --broker mqtt.example.com --qos 1 --count 100

# Test retained messages
./test_mqtt_qos.py --broker mqtt.example.com --test-retained

# Test LWT
./test_mqtt_qos.py --broker mqtt.example.com --test-lwt

# JSON output
./test_mqtt_qos.py --broker mqtt.example.com --test-all --json
```

**Metrics**: Delivery rate, message loss, duplicates, latency (min, avg, p95, max)

#### 3. benchmark_mqtt_broker.py (650 lines)

**Purpose**: Benchmark MQTT broker performance and scalability

**Features**:
- Test concurrent connections (100s to 1000s)
- Measure throughput (messages/sec)
- Pub-sub latency testing
- Connection establishment time
- Memory and CPU monitoring
- Ramp-up testing
- JSON output for reporting

**Usage**:
```bash
# Benchmark with 1000 connections
./benchmark_mqtt_broker.py --broker mqtt.example.com --connections 1000 --duration 60

# Test throughput
./benchmark_mqtt_broker.py --broker mqtt.example.com --test throughput --messages 10000

# Test latency
./benchmark_mqtt_broker.py --broker mqtt.example.com --test latency --count 100

# Ramp-up test
./benchmark_mqtt_broker.py --broker mqtt.example.com --connections 5000 --ramp-up 120 --duration 300

# JSON output
./benchmark_mqtt_broker.py --broker mqtt.example.com --connections 1000 --json
```

**Metrics**: Connections/sec, messages/sec, latency (p50, p95, p99), memory usage

### Examples

Seven production-ready examples in `resources/examples/`:

#### 1. python/publisher.py

Complete Python publisher implementation:
- Connection management with reconnection
- QoS 0/1/2 support
- Retained messages
- JSON payload serialization
- Error handling and logging
- CLI interface

#### 2. python/subscriber.py

Complete Python subscriber implementation:
- Topic subscription with wildcards
- Message handlers
- Persistent sessions
- Automatic reconnection
- Message queueing
- CLI interface

#### 3. mosquitto/mosquitto.conf

Production Mosquitto configuration:
- Multiple listeners (1883, 8883, 9001 WebSocket)
- TLS/SSL configuration
- Password authentication
- ACL file for authorization
- Logging and persistence
- Connection limits

#### 4. emqx/docker-compose.yml

EMQX deployment with Docker:
- EMQX broker with clustering support
- Prometheus metrics
- Grafana dashboards
- MQTT over WebSocket
- Health checks
- Volume mounts for persistence

#### 5. aws_iot/iot_device.py

AWS IoT Core integration:
- Certificate-based authentication (mutual TLS)
- Device shadows
- Thing registry
- Job execution
- Fleet provisioning
- Telemetry publishing

#### 6. node/mqtt_client.js

Node.js client implementation:
- MQTT.js library
- Async/await patterns
- Reconnection logic
- Event handlers
- TypeScript types

#### 7. tls/generate_certs.sh

TLS certificate generation script:
- CA certificate creation
- Server certificate
- Client certificates
- Mosquitto configuration for TLS
- Testing with mosquitto_pub/sub

### Quick Start

**1. Validate broker config**:
```bash
cd skills/protocols/mqtt-messaging/resources/scripts
./validate_mqtt_config.py --config ../examples/mosquitto/mosquitto.conf --json
```

**2. Test QoS levels**:
```bash
./test_mqtt_qos.py --broker localhost --test-all
```

**3. Run examples**:
```bash
cd ../examples

# Start Mosquitto
mosquitto -c mosquitto/mosquitto.conf

# Run publisher (in another terminal)
python python/publisher.py --broker localhost --topic test/topic --message "Hello MQTT"

# Run subscriber (in another terminal)
python python/subscriber.py --broker localhost --topic test/#
```

**4. Deploy with Docker**:
```bash
cd emqx
docker-compose up -d
# Dashboard: http://localhost:18083 (admin/public)
```

**5. Benchmark broker**:
```bash
cd ../scripts
./benchmark_mqtt_broker.py --broker localhost --connections 100 --duration 30
```

### File Structure

```
skills/protocols/mqtt-messaging/
├── mqtt-messaging.md (this file)
└── resources/
    ├── REFERENCE.md (3,200+ lines)
    ├── scripts/
    │   ├── validate_mqtt_config.py (550 lines) - Config validation
    │   ├── test_mqtt_qos.py (600 lines) - QoS testing
    │   └── benchmark_mqtt_broker.py (650 lines) - Broker benchmarking
    └── examples/
        ├── python/
        │   ├── publisher.py - Python publisher
        │   └── subscriber.py - Python subscriber
        ├── mosquitto/
        │   ├── mosquitto.conf - Mosquitto config
        │   └── acl.conf - ACL rules
        ├── emqx/
        │   └── docker-compose.yml - EMQX deployment
        ├── aws_iot/
        │   └── iot_device.py - AWS IoT Core client
        ├── node/
        │   └── mqtt_client.js - Node.js client
        └── tls/
            └── generate_certs.sh - TLS certificate generation
```

### Resources Summary

| Category | Item | Lines | Description |
|----------|------|-------|-------------|
| **Reference** | REFERENCE.md | 3,200+ | Complete technical reference |
| **Scripts** | validate_mqtt_config.py | 550 | Config validation tool |
| | test_mqtt_qos.py | 600 | QoS testing tool |
| | benchmark_mqtt_broker.py | 650 | Broker benchmarking tool |
| **Examples** | python/publisher.py | 180 | Python publisher |
| | python/subscriber.py | 200 | Python subscriber |
| | mosquitto.conf | 120 | Mosquitto configuration |
| | docker-compose.yml | 100 | EMQX deployment |
| | iot_device.py | 250 | AWS IoT Core client |
| | mqtt_client.js | 150 | Node.js client |
| | generate_certs.sh | 100 | TLS cert generation |

**Total**: 6,100+ lines of production-ready resources

---

## Related Skills

- `protocols-grpc-implementation.md` - gRPC for microservice communication
- `realtime-websocket-implementation.md` - WebSocket for bidirectional messaging
- `pubsub-patterns.md` - Pub-sub architecture patterns
- `iot-device-management.md` - IoT device lifecycle management
- `message-queue-patterns.md` - Message queuing architectures

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
