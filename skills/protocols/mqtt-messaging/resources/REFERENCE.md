# MQTT Messaging Reference

**Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: ~3,200

This comprehensive reference covers MQTT implementation from fundamentals to advanced patterns for IoT and real-time messaging.

---

## Table of Contents

1. [MQTT Fundamentals](#1-mqtt-fundamentals)
2. [Protocol Specifications](#2-protocol-specifications)
3. [QoS Levels Deep Dive](#3-qos-levels-deep-dive)
4. [Topic Design](#4-topic-design)
5. [Connection Management](#5-connection-management)
6. [Retained Messages](#6-retained-messages)
7. [Last Will and Testament](#7-last-will-and-testament)
8. [Session Management](#8-session-management)
9. [Security](#9-security)
10. [MQTT Brokers](#10-mqtt-brokers)
11. [Client Implementation](#11-client-implementation)
12. [MQTT over WebSocket](#12-mqtt-over-websocket)
13. [Cloud IoT Platforms](#13-cloud-iot-platforms)
14. [MQTT v5.0 Features](#14-mqtt-v50-features)
15. [Performance Optimization](#15-performance-optimization)
16. [Testing Strategies](#16-testing-strategies)
17. [Monitoring and Observability](#17-monitoring-and-observability)
18. [Common Patterns](#18-common-patterns)
19. [Anti-Patterns](#19-anti-patterns)
20. [Comparison with Alternatives](#20-comparison-with-alternatives)
21. [References](#21-references)

---

## 1. MQTT Fundamentals

### What is MQTT?

**MQTT** (Message Queuing Telemetry Transport) is a lightweight, publish-subscribe network protocol designed for machine-to-machine (M2M) and Internet of Things (IoT) communication. It was created by Andy Stanford-Clark (IBM) and Arlen Nipper in 1999.

**Key characteristics**:
- **Lightweight**: Minimal 2-byte fixed header overhead
- **Publish-Subscribe**: Decoupled communication pattern
- **QoS levels**: Three levels of delivery guarantees (0, 1, 2)
- **Small code footprint**: Ideal for constrained devices
- **TCP/IP transport**: Reliable, ordered delivery
- **Broker-based architecture**: Central message routing
- **Last Will and Testament**: Automatic notification of client disconnection
- **Retained messages**: Store-and-forward for new subscribers

### Why MQTT?

**Designed for**:
- Constrained devices (embedded systems, microcontrollers)
- Unreliable networks (cellular, satellite, mesh)
- Low bandwidth environments
- Battery-powered devices (minimal network overhead)

**Use cases**:
- IoT sensor networks (temperature, humidity, motion sensors)
- Industrial automation (SCADA systems, factory monitoring)
- Home automation (smart lights, thermostats, security)
- Vehicle telematics (fleet tracking, diagnostics)
- Mobile messaging (Facebook Messenger uses MQTT)
- Healthcare monitoring (patient sensors, medical devices)

### Architecture Overview

```
┌──────────────┐                           ┌──────────────┐
│  Publisher   │                           │  Subscriber  │
│              │                           │              │
│  ┌────────┐  │                           │  ┌────────┐  │
│  │ Client │  │                           │  │ Client │  │
│  └────┬───┘  │                           │  └────▲───┘  │
│       │      │                           │       │      │
└───────┼──────┘                           └───────┼──────┘
        │                                          │
        │ PUBLISH                                  │ Deliver
        │ (topic, payload, QoS)                    │
        │                                          │
        ▼                                          │
  ┌─────────────────────────────────────────────────────┐
  │                   MQTT Broker                       │
  │                                                     │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
  │  │   Topics     │  │ Subscriptions│  │  QoS     │ │
  │  │   Router     │  │    Manager   │  │ Manager  │ │
  │  └──────────────┘  └──────────────┘  └──────────┘ │
  │                                                     │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
  │  │   Session    │  │   Retained   │  │   Auth   │ │
  │  │    Store     │  │   Messages   │  │  Engine  │ │
  │  └──────────────┘  └──────────────┘  └──────────┘ │
  │                                                     │
  └─────────────────────────────────────────────────────┘
```

**Components**:
- **Client**: Publisher or subscriber (or both)
- **Broker**: Central message router and coordinator
- **Topics**: Hierarchical message routing paths
- **Messages**: Payload with topic and QoS

### MQTT vs Other Protocols

| Feature | MQTT | HTTP/REST | WebSocket | AMQP | CoAP |
|---------|------|-----------|-----------|------|------|
| **Pattern** | Pub-Sub | Request-Response | Bidirectional | Pub-Sub + Queues | Request-Response |
| **Transport** | TCP | TCP | TCP | TCP | UDP |
| **Overhead** | 2 bytes | 100s of bytes | 2-14 bytes | 8 bytes | 4 bytes |
| **QoS** | 0, 1, 2 | None | None | 0, 1 | 0, 1 (CoAP CON) |
| **Broker** | Required | No | No | Required | Optional |
| **Lightweight** | Yes | No | Yes | No | Yes (UDP) |
| **Reliability** | TCP | TCP | TCP | TCP | UDP (less reliable) |
| **Use Case** | IoT, M2M | Web APIs | Real-time web | Enterprise messaging | Constrained devices |

**When to use MQTT**:
- IoT devices with limited resources
- Unreliable or high-latency networks
- Need pub-sub pattern with QoS
- Battery-powered devices
- Many-to-many communication

**When NOT to use MQTT**:
- Simple request-response (use HTTP)
- Binary streaming (use WebSocket or gRPC)
- Enterprise message queues with complex routing (use RabbitMQ/AMQP)
- Extremely constrained devices on UDP (use CoAP)

---

## 2. Protocol Specifications

### MQTT Versions

**MQTT v3.1.1** (OASIS Standard, 2014):
- Most widely deployed version
- Supported by all major brokers and clients
- Fixed header + Variable header + Payload structure
- 14 packet types

**MQTT v5.0** (OASIS Standard, 2019):
- Enhanced error reporting (reason codes)
- User properties (custom metadata)
- Shared subscriptions
- Topic aliases
- Request/response pattern support
- Flow control (receive maximum)
- Better scalability features

### Packet Structure

**Fixed Header** (present in all packets):
```
 7  6  5  4  3  2  1  0
┌──┬──┬──┬──┬──┬──┬──┬──┐
│ Packet Type │ Flags  │  Byte 1
├──┴──┴──┴──┼──┴──┴──┴──┤
│  Remaining Length      │  Byte 2+ (1-4 bytes)
└────────────────────────┘
```

**Packet types** (4 bits, values 1-14):
1. **CONNECT** (1): Client request to connect to broker
2. **CONNACK** (2): Broker acknowledgment of connection
3. **PUBLISH** (3): Publish message to topic
4. **PUBACK** (4): Publish acknowledgment (QoS 1)
5. **PUBREC** (5): Publish received (QoS 2, part 1)
6. **PUBREL** (6): Publish release (QoS 2, part 2)
7. **PUBCOMP** (7): Publish complete (QoS 2, part 3)
8. **SUBSCRIBE** (8): Client subscribe to topics
9. **SUBACK** (9): Subscribe acknowledgment
10. **UNSUBSCRIBE** (10): Unsubscribe from topics
11. **UNSUBACK** (11): Unsubscribe acknowledgment
12. **PINGREQ** (12): Ping request (keep-alive)
13. **PINGRESP** (13): Ping response
14. **DISCONNECT** (14): Client disconnecting

**Remaining Length** (1-4 bytes):
- Variable-length encoding (continuation bit in MSB)
- Maximum value: 268,435,455 (256 MB)

Example:
```
Byte 1: 0x82 (1000 0010)
  → Type: PUBLISH (3) with DUP=1
Byte 2: 0x0F (15)
  → Remaining length: 15 bytes
```

### Control Packet Examples

**CONNECT Packet**:
```
Fixed Header:
  Type: 1 (CONNECT)
  Flags: 0000
  Length: [variable]

Variable Header:
  Protocol Name: "MQTT"
  Protocol Level: 4 (v3.1.1) or 5 (v5.0)
  Connect Flags:
    - Clean Session (bit 1)
    - Will Flag (bit 2)
    - Will QoS (bits 3-4)
    - Will Retain (bit 5)
    - Password Flag (bit 6)
    - Username Flag (bit 7)
  Keep Alive: 60 seconds (typical)

Payload:
  Client Identifier: "client_123"
  Will Topic: "device/status" (if Will Flag set)
  Will Message: "offline" (if Will Flag set)
  Username: "user" (if Username Flag set)
  Password: "pass" (if Password Flag set)
```

**PUBLISH Packet**:
```
Fixed Header:
  Type: 3 (PUBLISH)
  Flags:
    - DUP (bit 3): Duplicate delivery
    - QoS (bits 1-2): 0, 1, or 2
    - RETAIN (bit 0): Retained message
  Length: [variable]

Variable Header:
  Topic Name: "home/bedroom/temperature"
  Packet Identifier: 123 (if QoS > 0)

Payload:
  Message: "22.5"
```

**SUBSCRIBE Packet**:
```
Fixed Header:
  Type: 8 (SUBSCRIBE)
  Flags: 0010 (reserved)
  Length: [variable]

Variable Header:
  Packet Identifier: 456

Payload:
  Topic Filter: "home/+/temperature"
  QoS: 1
  [additional topic filters...]
```

### Keep-Alive Mechanism

**Purpose**: Detect broken connections without waiting for TCP timeout (which can be 2+ hours).

**How it works**:
1. Client specifies keep-alive interval in CONNECT (e.g., 60 seconds)
2. If no packet sent within keep-alive period, client sends PINGREQ
3. Broker responds with PINGRESP
4. If broker doesn't receive any packet within 1.5x keep-alive, it disconnects client

**Example**:
```
Keep-Alive: 60 seconds

Client ──CONNECT(keepalive=60)──> Broker
Client <──────CONNACK──────────── Broker

[55 seconds pass, no activity]

Client ───────PINGREQ───────────> Broker
Client <──────PINGRESP──────────── Broker

[If 90 seconds (1.5x60) pass without any packet, broker disconnects]
```

**Best practices**:
- Use 30-60 seconds for most applications
- Shorter intervals (5-10s) for critical connections
- Longer intervals (300s+) for battery-powered devices
- Set to 0 to disable (not recommended in production)

---

## 3. QoS Levels Deep Dive

### QoS 0 - At Most Once

**Guarantee**: Fire and forget, no acknowledgment

**Flow**:
```
Publisher                Broker                  Subscriber
    |                       |                         |
    |─── PUBLISH QoS 0 ──>  |                         |
    |                       |─── PUBLISH QoS 0 ──>    |
    |                       |                         |
   Done                   Done                      Done
```

**Characteristics**:
- Single packet transmission
- No acknowledgment or retransmission
- Message may be lost if network fails
- Fastest, lowest overhead (2 bytes header)
- Same reliability as underlying TCP connection

**Use cases**:
- Non-critical sensor data (temperature every 10 seconds)
- High-frequency telemetry where occasional loss is acceptable
- Data where latest value is what matters (not historical)

**Python example**:
```python
client.publish("sensor/temperature", "22.5", qos=0)
# No confirmation, fire and forget
```

### QoS 1 - At Least Once

**Guarantee**: Acknowledged delivery, may duplicate

**Flow**:
```
Publisher                Broker                  Subscriber
    |                       |                         |
    |─── PUBLISH QoS 1 ──>  |                         |
    |     (packet_id=123)   |─── PUBLISH QoS 1 ──>    |
    |                       |     (packet_id=456)     |
    |                       |                         |
    |                       |<──── PUBACK ─────────   |
    |<──── PUBACK ──────    |     (packet_id=456)     |
    |     (packet_id=123)   |                         |
   Done                   Done                      Done
```

**Characteristics**:
- Two packets: PUBLISH + PUBACK
- Broker acknowledges receipt
- Publisher retransmits if no PUBACK received (DUP flag set)
- Message delivered at least once (may duplicate if PUBACK lost)
- Most commonly used QoS level

**Use cases**:
- Important events (alarms, notifications)
- Database operations where duplicates are idempotent
- Most general-purpose messaging

**Python example**:
```python
result = client.publish("alarm/temperature", "CRITICAL", qos=1)
result.wait_for_publish()  # Wait for PUBACK
```

**Handling duplicates**:
```python
# Idempotent message handling
message_ids = set()

def on_message(client, userdata, msg):
    msg_id = msg.mid  # Message ID
    if msg_id in message_ids:
        print(f"Duplicate message {msg_id}, ignoring")
        return

    message_ids.add(msg_id)
    process_message(msg.payload)
```

### QoS 2 - Exactly Once

**Guarantee**: Exactly-once delivery, no duplicates

**Flow**:
```
Publisher                Broker                  Subscriber
    |                       |                         |
    |─── PUBLISH QoS 2 ──>  |                         |
    |     (packet_id=123)   |                         |
    |                       |─── PUBLISH QoS 2 ──>    |
    |                       |     (packet_id=456)     |
    |                       |                         |
    |                       |<──── PUBREC ─────────   |
    |<──── PUBREC ──────    |     (packet_id=456)     |
    |     (packet_id=123)   |                         |
    |                       |                         |
    |─── PUBREL ─────────>  |                         |
    |     (packet_id=123)   |─── PUBREL ──────────>   |
    |                       |     (packet_id=456)     |
    |                       |                         |
    |                       |<──── PUBCOMP ────────   |
    |<──── PUBCOMP ──────   |     (packet_id=456)     |
    |     (packet_id=123)   |                         |
   Done                   Done                      Done
```

**Characteristics**:
- Four-way handshake: PUBLISH → PUBREC → PUBREL → PUBCOMP
- Highest overhead (4 packets)
- Message delivered exactly once (no loss, no duplicates)
- Broker stores message until PUBREL received
- Slowest but most reliable

**Use cases**:
- Financial transactions (billing, payments)
- Critical commands (device firmware update)
- Non-idempotent operations (incrementing counters)
- Regulatory compliance (audit trails)

**Python example**:
```python
result = client.publish("billing/transaction", json.dumps(tx), qos=2)
result.wait_for_publish()  # Wait for full 4-way handshake
```

### QoS Downgrade

**Important**: Subscriber's QoS can be lower than publisher's QoS.

**Rule**: Message delivered at **minimum** of publisher QoS and subscriber QoS.

**Example**:
```
Publisher QoS 2 → Broker → Subscriber QoS 1
                  Result: Delivered as QoS 1

Publisher QoS 1 → Broker → Subscriber QoS 2
                  Result: Delivered as QoS 1
```

**SUBACK granted QoS**:
```python
# Client subscribes with QoS 2
client.subscribe("topic", qos=2)

# Broker may grant lower QoS (e.g., QoS 1)
# SUBACK will indicate granted QoS
def on_subscribe(client, userdata, mid, granted_qos):
    print(f"Granted QoS: {granted_qos}")  # May be [1] instead of [2]
```

### QoS Performance Comparison

**Latency** (typical, same data center):
- QoS 0: ~1 ms (1 packet)
- QoS 1: ~2 ms (2 packets, 1 RTT)
- QoS 2: ~4 ms (4 packets, 2 RTTs)

**Throughput** (1 KB messages, localhost):
- QoS 0: ~50,000 msg/sec
- QoS 1: ~25,000 msg/sec
- QoS 2: ~12,000 msg/sec

**Memory** (broker storage per in-flight message):
- QoS 0: None
- QoS 1: ~100 bytes (until PUBACK)
- QoS 2: ~200 bytes (until PUBCOMP)

**Battery consumption** (relative):
- QoS 0: 1x (baseline)
- QoS 1: 2x (double radio time)
- QoS 2: 4x (quadruple radio time)

### Choosing QoS Level

**Decision tree**:
```
Can you tolerate message loss?
  ├─ YES → Is latency critical?
  │         ├─ YES → QoS 0
  │         └─ NO  → QoS 0 (still fastest)
  │
  └─ NO → Are duplicates acceptable?
            ├─ YES → QoS 1 (most common)
            └─ NO  → QoS 2 (highest guarantee)
```

**Guidelines**:
- **Default**: Start with QoS 1 for most applications
- **QoS 0**: High-frequency telemetry, non-critical data
- **QoS 1**: Important events, idempotent operations
- **QoS 2**: Financial data, critical commands, non-idempotent ops

---

## 4. Topic Design

### Topic Syntax

**Structure**: UTF-8 strings with `/` as level separator

```
{domain}/{location}/{device}/{metric}
```

**Rules**:
- Case-sensitive: `Home/bedroom` ≠ `home/bedroom`
- No leading/trailing slashes: `home/bedroom`, not `/home/bedroom/`
- Max length: 65,535 bytes (practical limit ~1 KB)
- Allowed characters: UTF-8 (avoid special chars for compatibility)
- Reserved topics: Start with `$` (broker-specific, e.g., `$SYS/broker/uptime`)

### Hierarchical Design

**Best practices**:

**Domain-based**:
```
home/bedroom/temperature
home/bedroom/humidity
home/livingroom/temperature
office/conference_room_a/occupancy
office/conference_room_b/occupancy
```

**Device-centric**:
```
devices/sensor_01/telemetry
devices/sensor_01/status
devices/sensor_02/telemetry
devices/actuator_01/command
```

**Location-based**:
```
building_a/floor_2/room_203/hvac/temperature
building_a/floor_2/room_203/hvac/setpoint
building_b/floor_1/lobby/lighting/state
```

**Reverse domain (like Java packages)**:
```
com/example/devices/sensor_01/temperature
com/example/devices/sensor_01/humidity
```

**Recommended depth**: 3-7 levels (balance specificity vs complexity)

### Wildcards

**Single-level wildcard (`+`)**:
- Matches exactly one topic level
- Can appear multiple times

**Examples**:
```
home/+/temperature
  ✓ home/bedroom/temperature
  ✓ home/kitchen/temperature
  ✗ home/bedroom/sensor/temperature (too many levels)

+/bedroom/+
  ✓ home/bedroom/temperature
  ✓ office/bedroom/humidity

devices/+/+/temperature
  ✓ devices/sensor_01/outdoor/temperature
```

**Multi-level wildcard (`#`)**:
- Matches zero or more topic levels
- Must be last character in subscription
- Only one `#` per subscription

**Examples**:
```
home/#
  ✓ home/bedroom/temperature
  ✓ home/bedroom/sensor/temperature
  ✓ home (zero levels)

home/bedroom/#
  ✓ home/bedroom/temperature
  ✓ home/bedroom/humidity
  ✓ home/bedroom/sensor/motion

#
  ✓ Matches ALL topics (expensive, avoid in production!)
```

**Combining wildcards**:
```
home/+/temperature/#
  ✓ home/bedroom/temperature
  ✓ home/bedroom/temperature/celsius
  ✓ home/kitchen/temperature/reading/current
```

### Topic Best Practices

**DO**:
1. **Use hierarchical structure**: `domain/location/device/metric`
2. **Be consistent**: Pick a convention and stick to it
3. **Use lowercase**: `home/bedroom/temp` (easier to remember)
4. **Use underscores for spaces**: `conference_room_a` (not `conference-room-a`)
5. **Put data in payload**: Topic for routing, payload for data
6. **Version topics**: `v1/devices/sensor_01/data` (for breaking changes)
7. **Document schema**: Maintain topic registry

**DON'T**:
1. **Don't use spaces**: `home bedroom temp` (use `home/bedroom/temp`)
2. **Don't use special characters**: Avoid `!@#$%^&*()`
3. **Don't embed data**: `sensor/temp/22.5` (put `22.5` in payload)
4. **Don't use leading/trailing slashes**: `/home/bedroom/` (use `home/bedroom`)
5. **Don't subscribe to `#`**: Receives ALL messages (broker overload)
6. **Don't use too many levels**: >7 levels becomes unwieldy
7. **Don't use dynamic topics**: Avoid `sensor_{timestamp}/data`

### Topic Naming Conventions

**Telemetry** (device → cloud):
```
devices/{device_id}/telemetry
devices/{device_id}/events
sensors/{sensor_id}/readings
```

**Commands** (cloud → device):
```
devices/{device_id}/commands
devices/{device_id}/config
actuators/{actuator_id}/control
```

**Status**:
```
devices/{device_id}/status        # online/offline
devices/{device_id}/health        # health metrics
system/broker/status
```

**Request-Response**:
```
requests/{client_id}/{request_id}    # Request
responses/{client_id}/{request_id}   # Response
```

**Shared subscriptions** (MQTT v5.0):
```
$share/{group_name}/{topic_filter}
$share/workers/jobs/pending
```

### Topic ACL (Access Control)

**Mosquitto ACL example** (`acl.conf`):
```
# User "sensor_01" can publish to its own topics
user sensor_01
topic write devices/sensor_01/#

# User "backend" can subscribe to all device telemetry
user backend
topic read devices/+/telemetry
topic read devices/+/status

# Admin can do everything
user admin
topic readwrite #

# Anonymous users (if allow_anonymous=true)
topic read public/#
```

**EMQX ACL (HTTP Auth)**:
```json
{
  "username": "sensor_01",
  "topic": "devices/sensor_01/telemetry",
  "action": "publish",
  "access": "allow"
}
```

**AWS IoT Core Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": "arn:aws:iot:us-east-1:123456789012:topic/devices/${iot:Connection.Thing.ThingName}/*"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Subscribe",
      "Resource": "arn:aws:iot:us-east-1:123456789012:topicfilter/commands/${iot:Connection.Thing.ThingName}/*"
    }
  ]
}
```

---

## 5. Connection Management

### CONNECT Packet

**Client → Broker**:
```python
import paho.mqtt.client as mqtt

client = mqtt.Client(
    client_id="sensor_01",        # Unique identifier
    clean_session=True,            # or False for persistent session
    protocol=mqtt.MQTTv311         # or MQTTv5
)

# Set credentials
client.username_pw_set("username", "password")

# Set Last Will and Testament
client.will_set(
    topic="devices/sensor_01/status",
    payload="offline",
    qos=1,
    retain=True
)

# Connect
client.connect(
    host="mqtt.example.com",
    port=1883,
    keepalive=60                   # Keep-alive interval (seconds)
)
```

### CONNACK Response

**Broker → Client**:

**Return codes** (MQTT v3.1.1):
- `0`: Connection accepted
- `1`: Connection refused, unacceptable protocol version
- `2`: Connection refused, identifier rejected
- `3`: Connection refused, server unavailable
- `4`: Connection refused, bad username or password
- `5`: Connection refused, not authorized

**Session Present flag**:
- `0`: Clean session, no previous session
- `1`: Session resumed (clean_session=False)

**Python callback**:
```python
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully")
        print(f"Session present: {flags['session present']}")

        # Resubscribe on reconnect
        client.subscribe("devices/sensor_01/commands", qos=1)
    else:
        print(f"Connection failed: {rc}")
        # Handle error

client.on_connect = on_connect
```

### Reconnection Strategies

**Exponential backoff** (recommended):
```python
import time
import random

class MQTTReconnectClient:
    def __init__(self, broker, port=1883):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        self.reconnect_delay = 1          # Initial delay (seconds)
        self.max_reconnect_delay = 60     # Max delay
        self.reconnect_backoff = 2        # Exponential factor

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected")
            self.reconnect_delay = 1      # Reset on successful connect
        else:
            print(f"Connection failed: {rc}")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"Unexpected disconnect: {rc}")
            self.reconnect()

    def reconnect(self):
        while True:
            try:
                print(f"Reconnecting in {self.reconnect_delay}s...")
                time.sleep(self.reconnect_delay)

                self.client.reconnect()
                print("Reconnected")
                break

            except Exception as e:
                print(f"Reconnect failed: {e}")

                # Exponential backoff with jitter
                self.reconnect_delay = min(
                    self.reconnect_delay * self.reconnect_backoff,
                    self.max_reconnect_delay
                )
                jitter = random.uniform(0, 0.1 * self.reconnect_delay)
                self.reconnect_delay += jitter

    def connect(self):
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_forever()
        except Exception as e:
            print(f"Initial connection failed: {e}")
            self.reconnect()
```

**Fixed interval** (simple, but can cause thundering herd):
```python
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Disconnected, reconnecting in 5s...")
        time.sleep(5)
        client.reconnect()
```

**Automatic reconnection** (paho-mqtt built-in):
```python
client = mqtt.Client()
client.connect("mqtt.example.com", 1883, keepalive=60)

# loop_forever() automatically reconnects
client.loop_forever()
```

### Connection States

```python
# Check connection state
if client.is_connected():
    client.publish("topic", "message")
else:
    print("Not connected")

# Manual reconnect
try:
    client.reconnect()
except Exception as e:
    print(f"Reconnect failed: {e}")
```

---

## 6. Retained Messages

### What are Retained Messages?

**Retained messages** are stored by the broker and delivered to new subscribers immediately upon subscription, even if the publisher is offline.

**Characteristics**:
- Only one retained message per topic
- New subscribers receive it instantly
- Subsequent publishes replace retained message
- QoS preserved (retained message delivered with original QoS)

### Use Cases

**Device status**:
```python
# Device publishes status as retained
client.publish("devices/sensor_01/status", "online", qos=1, retain=True)

# New subscriber immediately knows device is online
# (even if published hours ago)
```

**Last known value**:
```python
# Publish last temperature reading
client.publish("home/bedroom/temperature", "22.5", qos=1, retain=True)

# New dashboard subscriber gets last value instantly
# (no need to wait for next reading)
```

**Configuration**:
```python
# System config as retained message
config = json.dumps({"interval": 60, "enabled": True})
client.publish("system/config", config, qos=1, retain=True)

# New services get current config on startup
```

### Publishing Retained Messages

```python
# Publish with retain=True
client.publish(
    topic="devices/sensor_01/status",
    payload="online",
    qos=1,
    retain=True
)
```

### Clearing Retained Messages

**Send empty payload with retain=True**:
```python
# Clear retained message
client.publish("devices/sensor_01/status", "", qos=0, retain=True)
```

### Receiving Retained Messages

```python
def on_message(client, userdata, msg):
    is_retained = msg.retain
    print(f"Retained: {is_retained}, Payload: {msg.payload}")

    if is_retained:
        print("This is a retained message (may be old)")
    else:
        print("This is a fresh message")

client.subscribe("devices/+/status", qos=1)
```

### Broker Storage

**Mosquitto configuration**:
```
# mosquitto.conf
persistence true
persistence_location /var/lib/mosquitto/
autosave_interval 300

# Max retained messages (0 = unlimited)
max_retained_messages 1000
```

**EMQX configuration**:
```erlang
# emqx.conf
## Retained messages
retainer.enable = true
retainer.max_retained_messages = 1000000
retainer.max_payload_size = 1MB
retainer.expiry_interval = 0
```

### Anti-Patterns

❌ **Using retained for high-frequency data**:
```python
# Wrong: Retained message updated every second
while True:
    temp = read_temperature()
    client.publish("sensor/temp", str(temp), qos=0, retain=True)
    time.sleep(1)
```
→ Unnecessary broker storage churn

✅ **Better**: Use retained for status, not frequent telemetry
```python
# Publish status (infrequent) as retained
client.publish("sensor/status", "online", qos=1, retain=True)

# Publish telemetry (frequent) without retain
temp = read_temperature()
client.publish("sensor/temp", str(temp), qos=0, retain=False)
```

❌ **Forgetting to clear retained messages**:
```python
# Device goes offline but retained message says "online"
```
→ Stale state

✅ **Better**: Clear on disconnect
```python
def on_disconnect(client, userdata, rc):
    # Clear status on disconnect
    client.publish("devices/sensor_01/status", "", qos=0, retain=True)
```

---

## 7. Last Will and Testament

### What is Last Will?

**Last Will and Testament (LWT)** is a message automatically published by the broker if a client disconnects unexpectedly (network failure, crash, power loss).

**Not sent if**:
- Client sends DISCONNECT packet (graceful disconnect)
- Client's keep-alive expires and broker times out

**Sent if**:
- Client loses network connection without DISCONNECT
- Client process crashes
- Keep-alive timeout (no PINGREQ received)

### Use Cases

**Device presence detection**:
```python
# Set LWT before connecting
client.will_set(
    topic="devices/sensor_01/status",
    payload="offline",
    qos=1,
    retain=True
)

# Publish online status after connect
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.publish("devices/sensor_01/status", "online", qos=1, retain=True)

# If device crashes, broker publishes "offline"
```

**Connection monitoring**:
```python
# Backend subscribes to status topics
def on_message(client, userdata, msg):
    if msg.topic.endswith("/status"):
        device_id = msg.topic.split("/")[1]
        status = msg.payload.decode()

        if status == "offline":
            alert_admin(f"Device {device_id} went offline")

client.subscribe("devices/+/status")
```

**Resource cleanup**:
```python
# Publish cleanup message as LWT
cleanup_msg = json.dumps({"action": "cleanup", "device_id": "sensor_01"})
client.will_set("system/cleanup", cleanup_msg, qos=1, retain=False)

# Backend handles cleanup on disconnect
def on_message(client, userdata, msg):
    if msg.topic == "system/cleanup":
        cleanup_data = json.loads(msg.payload)
        release_resources(cleanup_data["device_id"])
```

### Setting Last Will

```python
client = mqtt.Client(client_id="sensor_01")

# Set Last Will before connect()
client.will_set(
    topic="devices/sensor_01/status",     # Topic
    payload="offline",                     # Message
    qos=1,                                 # QoS level
    retain=True                            # Retain flag
)

client.connect("mqtt.example.com", 1883)
```

### LWT Flow

```
Device                          Broker                      Monitor
  |                               |                            |
  |─── CONNECT (with LWT) ──────> |                            |
  |                               | (Stores LWT)               |
  |<─── CONNACK ──────────────    |                            |
  |                               |                            |
  |─── PUBLISH (status=online) ─> |─── PUBLISH ─────────────> |
  |                               |                            |
  [Network failure / crash]       |                            |
  X                               |                            |
                                  | (Keep-alive timeout)       |
                                  | (Publishes LWT)            |
                                  |                            |
                                  |─── PUBLISH (status=offline) ─> |
```

### Testing LWT

**Simulate unexpected disconnect**:
```python
import paho.mqtt.client as mqtt
import time

client = mqtt.Client(client_id="test_device")

# Set LWT
client.will_set("test/status", "offline", qos=1, retain=True)

def on_connect(client, userdata, flags, rc):
    print("Connected")
    # Publish online status
    client.publish("test/status", "online", qos=1, retain=True)

client.on_connect = on_connect
client.connect("mqtt.example.com", 1883, keepalive=5)  # Short keep-alive
client.loop_start()

time.sleep(2)

# Simulate crash (don't send DISCONNECT)
import os
os._exit(1)  # Hard exit, no graceful disconnect

# Broker will publish LWT after keep-alive timeout (~7.5 seconds)
```

**Monitor**:
```bash
# Subscribe to status topic
mosquitto_sub -h mqtt.example.com -t "test/status" -v

# Output:
# test/status online
# [7.5 seconds later]
# test/status offline
```

---

## 8. Session Management

### Clean Session vs Persistent Session

**Clean Session = True** (default):
- Broker discards all session state on disconnect
- Subscriptions lost
- Queued QoS 1/2 messages discarded
- Client ID can be empty (broker generates)

**Clean Session = False** (persistent):
- Broker stores session state
- Subscriptions preserved
- QoS 1/2 messages queued for offline clients
- Same client ID required to resume

### Session State Includes

**Broker stores**:
- All subscriptions
- All QoS 1/2 messages not yet acknowledged (PUBACK, PUBCOMP)
- All QoS 1/2 messages pending transmission to client
- All QoS 2 messages received from client but not yet confirmed (PUBREL)

**Client stores**:
- All QoS 1/2 messages sent to broker (until PUBACK/PUBCOMP)
- All QoS 2 messages received from broker (until PUBCOMP sent)

### Using Persistent Sessions

**Publisher** (ensure delivery even if offline):
```python
client = mqtt.Client(
    client_id="publisher_01",  # Fixed client ID (required)
    clean_session=False         # Persistent session
)

client.connect("mqtt.example.com", 1883)

# Publish with QoS 1/2
client.publish("important/data", "critical message", qos=1)

# Even if client disconnects before PUBACK,
# broker will deliver when reconnected
```

**Subscriber** (receive messages while offline):
```python
client = mqtt.Client(
    client_id="subscriber_01",  # Fixed client ID
    clean_session=False          # Persistent session
)

def on_connect(client, userdata, flags, rc):
    if flags['session present']:
        print("Session resumed, will receive queued messages")
    else:
        print("New session, subscribing...")
        client.subscribe("important/data", qos=1)

client.on_connect = on_connect
client.connect("mqtt.example.com", 1883)
client.loop_forever()

# Messages published while offline are delivered on reconnect
```

### Session Expiry (MQTT v5.0)

**MQTT v5.0** adds **Session Expiry Interval**:
```python
# Session expires after 1 hour of disconnection
connect_properties = Properties(PacketTypes.CONNECT)
connect_properties.SessionExpiryInterval = 3600  # seconds

client.connect("mqtt.example.com", 1883, properties=connect_properties)

# Set to 0 to make session temporary (even with clean_session=False)
# Set to 0xFFFFFFFF (max) to never expire
```

### Clearing Session State

**Method 1**: Connect with clean_session=True
```python
# Clear session
client = mqtt.Client(client_id="sensor_01", clean_session=True)
client.connect("mqtt.example.com", 1883)
client.disconnect()

# Next connection starts fresh
```

**Method 2**: Use different client ID
```python
# New client ID = new session
client = mqtt.Client(client_id="sensor_01_new")
```

**Method 3**: Broker CLI (Mosquitto)
```bash
# mosquitto_sub with clean session to clear
mosquitto_sub -h localhost -i "sensor_01" -t "#" -c

# Ctrl+C to disconnect
```

### Broker Configuration

**Mosquitto** (`mosquitto.conf`):
```
# Persistent session storage
persistence true
persistence_location /var/lib/mosquitto/
autosave_interval 300

# Max queued messages per client (persistent session)
max_queued_messages 1000

# Disconnect after N seconds of inactivity
persistent_client_expiration 1h
```

**EMQX** (`emqx.conf`):
```erlang
## Session
session.max_subscriptions = 0     # Unlimited
session.upgrade_qos = off
session.expiry_interval = 2h
session.max_inflight = 32
session.max_awaiting_rel = 100
```

### Use Cases

**Persistent sessions**:
- Mobile apps (connection drops frequently)
- Critical monitoring (can't miss alarms)
- Backend services (want message queue)
- Low-power devices (sleep between publishes)

**Clean sessions**:
- Real-time dashboards (only care about latest data)
- High-frequency sensors (don't queue old data)
- Temporary clients (testing, debugging)
- Stateless services (replicas with shared subscriptions)

---

## 9. Security

### TLS/SSL Encryption

**Transport encryption** protects data in transit.

**Python client with TLS**:
```python
import ssl
import paho.mqtt.client as mqtt

client = mqtt.Client()

# Basic TLS (verify server certificate)
client.tls_set(
    ca_certs="/path/to/ca.crt",           # CA certificate
    certfile=None,                         # Client cert (optional)
    keyfile=None,                          # Client key (optional)
    tls_version=ssl.PROTOCOL_TLSv1_2
)

# Disable hostname verification (not recommended)
# client.tls_insecure_set(True)

# Connect to TLS port (usually 8883)
client.connect("mqtt.example.com", port=8883)
```

**Mutual TLS (mTLS)** (client certificate authentication):
```python
client = mqtt.Client()

# Mutual TLS (server verifies client certificate)
client.tls_set(
    ca_certs="/path/to/ca.crt",           # CA certificate
    certfile="/path/to/client.crt",       # Client certificate
    keyfile="/path/to/client.key",        # Client private key
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.connect("mqtt.example.com", port=8883)
```

### Mosquitto TLS Configuration

**Generate certificates**:
```bash
# CA certificate
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
  -subj "/C=US/ST=State/L=City/O=Org/CN=Mosquitto CA"

# Server certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "/C=US/ST=State/L=City/O=Org/CN=mqtt.example.com"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365

# Client certificate (for mutual TLS)
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr \
  -subj "/C=US/ST=State/L=City/O=Org/CN=client_01"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out client.crt -days 365
```

**mosquitto.conf**:
```
# TLS listener
listener 8883
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key

# Require TLS 1.2 or higher
tls_version tlsv1.2

# Optional: Require client certificates (mTLS)
require_certificate true
use_identity_as_username true
```

### Username/Password Authentication

**Mosquitto password file**:
```bash
# Create password file
mosquitto_passwd -c /etc/mosquitto/passwd sensor_01
Password: ****

# Add more users
mosquitto_passwd -b /etc/mosquitto/passwd backend secret123
```

**mosquitto.conf**:
```
# Enable password authentication
allow_anonymous false
password_file /etc/mosquitto/passwd
```

**Python client**:
```python
client = mqtt.Client()
client.username_pw_set(username="sensor_01", password="secret")
client.connect("mqtt.example.com", 1883)
```

### Access Control Lists (ACL)

**Mosquitto ACL** (`/etc/mosquitto/acl.conf`):
```
# Topic ACL format:
# topic [read|write|readwrite] <topic>

# User sensor_01 can publish to its own topics
user sensor_01
topic write devices/sensor_01/#

# User backend can subscribe to all devices
user backend
topic read devices/+/telemetry
topic read devices/+/status

# User admin has full access
user admin
topic readwrite #

# Pattern: %u is replaced with username
user %u
topic readwrite devices/%u/#

# Pattern: %c is replaced with client ID
user sensor
topic write devices/%c/telemetry
```

**mosquitto.conf**:
```
acl_file /etc/mosquitto/acl.conf
```

### Token-Based Authentication

**HTTP Auth Plugin** (EMQX, HiveMQ):

**Python client with JWT token**:
```python
import jwt
import time

# Generate JWT token
token = jwt.encode(
    {
        "sub": "sensor_01",
        "exp": int(time.time()) + 3600,  # 1 hour
        "permissions": ["publish:devices/sensor_01/#"]
    },
    "secret_key",
    algorithm="HS256"
)

# Use token as password
client = mqtt.Client()
client.username_pw_set(username="sensor_01", password=token)
client.connect("mqtt.example.com", 1883)
```

**EMQX HTTP Auth**:
```bash
# Configure EMQX to validate via HTTP endpoint
# emqx.conf
auth.http.auth_req.url = http://auth-service/mqtt/auth
auth.http.auth_req.method = post
auth.http.auth_req.params = clientid=%c,username=%u,password=%P
```

**Auth service** (Python Flask):
```python
from flask import Flask, request, jsonify
import jwt

app = Flask(__name__)

@app.route('/mqtt/auth', methods=['POST'])
def mqtt_auth():
    username = request.form.get('username')
    password = request.form.get('password')  # JWT token

    try:
        # Verify JWT
        payload = jwt.decode(password, "secret_key", algorithms=["HS256"])
        if payload['sub'] == username:
            return jsonify({"result": "allow"}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"result": "deny", "reason": "token expired"}), 200
    except Exception:
        pass

    return jsonify({"result": "deny"}), 200
```

### MQTT over WebSocket

**Client (browser JavaScript)**:
```javascript
// Using MQTT.js library
const client = mqtt.connect('wss://mqtt.example.com:9001/mqtt', {
  username: 'user',
  password: 'pass',
  clientId: 'browser_client_' + Math.random().toString(16).substr(2, 8)
});

client.on('connect', () => {
  console.log('Connected over WebSocket');
  client.subscribe('home/temperature');
});

client.on('message', (topic, message) => {
  console.log(`${topic}: ${message.toString()}`);
});
```

**Mosquitto WebSocket config**:
```
# WebSocket listener
listener 9001
protocol websockets

# WebSocket with TLS
listener 9002
protocol websockets
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
```

**EMQX WebSocket** (enabled by default):
```
# emqx.conf
listener.ws.external = 8083
listener.wss.external = 8084
listener.wss.external.keyfile = etc/certs/key.pem
listener.wss.external.certfile = etc/certs/cert.pem
```

---

## 10. MQTT Brokers

### Mosquitto

**Eclipse Mosquitto**: Open-source, lightweight MQTT broker.

**Installation**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients

# macOS
brew install mosquitto

# Docker
docker run -it -p 1883:1883 eclipse-mosquitto
```

**Configuration** (`/etc/mosquitto/mosquitto.conf`):
```
# Listeners
listener 1883
listener 8883
protocol mqtt

# WebSocket
listener 9001
protocol websockets

# Persistence
persistence true
persistence_location /var/lib/mosquitto/

# Logging
log_dest file /var/log/mosquitto/mosquitto.log
log_type all
log_timestamp true

# Security
allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl.conf

# Limits
max_connections 1000
max_queued_messages 1000
message_size_limit 10KB
```

**Testing**:
```bash
# Subscribe
mosquitto_sub -h localhost -t "test/topic" -v

# Publish
mosquitto_pub -h localhost -t "test/topic" -m "Hello MQTT"

# With authentication
mosquitto_pub -h localhost -t "test" -m "msg" -u user -P pass

# With TLS
mosquitto_pub -h localhost -p 8883 -t "test" -m "msg" \
  --cafile ca.crt --cert client.crt --key client.key
```

**Pros**:
- Lightweight (~200 KB binary)
- Easy to configure
- Low resource usage
- Good for small-medium deployments

**Cons**:
- Limited scalability (single-threaded)
- No built-in clustering
- Basic monitoring

---

### EMQX

**EMQX**: High-performance, scalable MQTT broker (formerly EMQ X).

**Installation** (Docker):
```bash
# Single node
docker run -d --name emqx \
  -p 1883:1883 \
  -p 8083:8083 \
  -p 8084:8084 \
  -p 8883:8883 \
  -p 18083:18083 \
  emqx/emqx:latest

# Dashboard: http://localhost:18083
# Username: admin, Password: public
```

**Docker Compose** (with clustering):
```yaml
version: '3.8'

services:
  emqx1:
    image: emqx/emqx:latest
    container_name: emqx1
    environment:
      - EMQX_NODE_NAME=emqx@emqx1
      - EMQX_CLUSTER__DISCOVERY_STRATEGY=static
      - EMQX_CLUSTER__STATIC__SEEDS=emqx@emqx1,emqx@emqx2
    ports:
      - "1883:1883"
      - "18083:18083"
    networks:
      - emqx_net

  emqx2:
    image: emqx/emqx:latest
    container_name: emqx2
    environment:
      - EMQX_NODE_NAME=emqx@emqx2
      - EMQX_CLUSTER__DISCOVERY_STRATEGY=static
      - EMQX_CLUSTER__STATIC__SEEDS=emqx@emqx1,emqx@emqx2
    networks:
      - emqx_net

networks:
  emqx_net:
    driver: bridge
```

**Features**:
- **Scalability**: 100M+ concurrent connections (clustered)
- **Clustering**: Automatic node discovery
- **Rule Engine**: SQL-based data processing
- **Data Integration**: Kafka, Redis, PostgreSQL, InfluxDB
- **Authentication**: HTTP, JWT, MySQL, PostgreSQL, Redis, LDAP
- **Dashboard**: Web UI for monitoring and management
- **MQTT v5.0**: Full support

**Configuration** (`/etc/emqx/emqx.conf`):
```erlang
## Node name
node.name = emqx@127.0.0.1

## Listeners
listener.tcp.external = 1883
listener.tcp.external.max_connections = 1024000
listener.ssl.external = 8883
listener.ws.external = 8083
listener.wss.external = 8084

## Authentication
auth.mnesia.as = username
auth.user.1.username = admin
auth.user.1.password = public

## ACL
acl_nomatch = deny
acl_file = etc/acl.conf

## Clustering
cluster.name = emqx
cluster.discovery = static
cluster.static.seeds = emqx1@192.168.1.101,emqx2@192.168.1.102
```

**REST API**:
```bash
# Get stats
curl -u admin:public http://localhost:18083/api/v4/stats

# List clients
curl -u admin:public http://localhost:18083/api/v4/clients

# Publish message
curl -u admin:public -X POST http://localhost:18083/api/v4/mqtt/publish \
  -H "Content-Type: application/json" \
  -d '{"topic":"test/topic","payload":"hello","qos":1}'
```

**Pros**:
- Highly scalable (millions of connections)
- Built-in clustering
- Rich features (rule engine, integrations)
- Web dashboard
- Enterprise support available

**Cons**:
- Higher resource usage than Mosquitto
- More complex configuration
- Steeper learning curve

---

### HiveMQ

**HiveMQ**: Enterprise MQTT broker with advanced features.

**Installation** (Docker):
```bash
# Community Edition
docker run -d --name hivemq \
  -p 1883:1883 \
  -p 8080:8080 \
  hivemq/hivemq-ce:latest

# Dashboard: http://localhost:8080
```

**Features**:
- **Enterprise-grade**: High availability, clustering
- **MQTT 5.0**: Full support
- **Extensions**: Plugin system for custom logic
- **Monitoring**: Built-in metrics (Prometheus, Grafana)
- **Kafka Integration**: Bridge to Kafka
- **Security**: OAuth 2.0, LDAP, TLS
- **Support**: Commercial support and SLA

**Pros**:
- Production-ready out of the box
- Excellent documentation
- Plugin ecosystem
- Commercial support

**Cons**:
- Enterprise edition is expensive
- Community edition has limitations
- Heavier than Mosquitto

---

## 11. Client Implementation

### Python (paho-mqtt)

**Installation**:
```bash
pip install paho-mqtt
```

**Complete example**:
```python
import paho.mqtt.client as mqtt
import json
import time

class MQTTClient:
    def __init__(self, broker, port=1883, client_id=None):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(client_id=client_id, clean_session=False)

        # Callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.client.on_publish = self.on_publish

        # Message handlers
        self.message_handlers = {}

    def on_connect(self, client, userdata, flags, rc):
        connection_codes = {
            0: "Connected successfully",
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier",
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorized"
        }

        if rc == 0:
            print(f"✓ {connection_codes[rc]}")
            print(f"  Session present: {flags['session present']}")

            # Resubscribe on reconnect (if clean_session=False)
            if not flags['session present']:
                self.resubscribe()
        else:
            print(f"✗ {connection_codes.get(rc, 'Unknown error')}")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"✗ Unexpected disconnect (rc={rc}), reconnecting...")
        else:
            print("✓ Disconnected gracefully")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        qos = msg.qos
        retain = msg.retain

        print(f"📥 {topic} (QoS {qos}, retain={retain}): {payload}")

        # Call registered handler
        for pattern, handler in self.message_handlers.items():
            if mqtt.topic_matches_sub(pattern, topic):
                handler(topic, payload, qos, retain)

    def on_subscribe(self, client, userdata, mid, granted_qos):
        print(f"✓ Subscribed (granted QoS: {granted_qos})")

    def on_publish(self, client, userdata, mid):
        print(f"✓ Published (mid={mid})")

    def connect(self, username=None, password=None):
        """Connect to MQTT broker"""
        if username and password:
            self.client.username_pw_set(username, password)

        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from broker"""
        self.client.loop_stop()
        self.client.disconnect()

    def subscribe(self, topic, qos=0, handler=None):
        """Subscribe to topic with optional handler"""
        self.client.subscribe(topic, qos)
        if handler:
            self.message_handlers[topic] = handler

    def unsubscribe(self, topic):
        """Unsubscribe from topic"""
        self.client.unsubscribe(topic)
        if topic in self.message_handlers:
            del self.message_handlers[topic]

    def publish(self, topic, payload, qos=0, retain=False):
        """Publish message to topic"""
        if isinstance(payload, dict):
            payload = json.dumps(payload)

        result = self.client.publish(topic, payload, qos=qos, retain=retain)
        return result.mid

    def resubscribe(self):
        """Resubscribe to all registered topics"""
        for topic in self.message_handlers.keys():
            self.client.subscribe(topic, qos=1)

# Usage example
def main():
    client = MQTTClient(
        broker="mqtt.example.com",
        port=1883,
        client_id="python_client"
    )

    # Register message handler
    def temperature_handler(topic, payload, qos, retain):
        temp = float(payload)
        if temp > 25:
            print(f"⚠️  High temperature: {temp}°C")

    client.subscribe("home/+/temperature", qos=1, handler=temperature_handler)
    client.connect(username="user", password="pass")

    # Publish some messages
    client.publish("home/bedroom/temperature", "22.5", qos=1)
    client.publish("home/livingroom/temperature", "27.0", qos=1)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.disconnect()

if __name__ == "__main__":
    main()
```

---

### Node.js (MQTT.js)

**Installation**:
```bash
npm install mqtt
```

**Complete example** (`mqtt_client.js`):
```javascript
const mqtt = require('mqtt');

class MQTTClient {
  constructor(broker, options = {}) {
    this.broker = broker;
    this.options = {
      clientId: options.clientId || `mqtt_${Math.random().toString(16).slice(2, 10)}`,
      clean: options.clean !== undefined ? options.clean : true,
      reconnectPeriod: options.reconnectPeriod || 1000,
      connectTimeout: options.connectTimeout || 30000,
      keepalive: options.keepalive || 60,
      username: options.username,
      password: options.password,
      will: options.will
    };

    this.messageHandlers = new Map();
    this.client = null;
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.client = mqtt.connect(this.broker, this.options);

      this.client.on('connect', (connack) => {
        console.log('✓ Connected successfully');
        console.log(`  Session present: ${connack.sessionPresent}`);

        // Resubscribe if persistent session
        if (!connack.sessionPresent && this.messageHandlers.size > 0) {
          this.resubscribe();
        }

        resolve();
      });

      this.client.on('error', (error) => {
        console.error('✗ Connection error:', error.message);
        reject(error);
      });

      this.client.on('disconnect', () => {
        console.log('✗ Disconnected');
      });

      this.client.on('offline', () => {
        console.log('⚠️  Client offline, reconnecting...');
      });

      this.client.on('message', (topic, payload, packet) => {
        const message = payload.toString();
        const qos = packet.qos;
        const retain = packet.retain;

        console.log(`📥 ${topic} (QoS ${qos}, retain=${retain}): ${message}`);

        // Call registered handlers
        for (const [pattern, handler] of this.messageHandlers.entries()) {
          if (this.topicMatches(topic, pattern)) {
            handler(topic, message, qos, retain);
          }
        }
      });
    });
  }

  subscribe(topic, qos = 0, handler = null) {
    return new Promise((resolve, reject) => {
      this.client.subscribe(topic, { qos }, (err, granted) => {
        if (err) {
          console.error(`✗ Subscribe failed: ${err.message}`);
          reject(err);
        } else {
          console.log(`✓ Subscribed to ${topic} (granted QoS: ${granted[0].qos})`);
          if (handler) {
            this.messageHandlers.set(topic, handler);
          }
          resolve(granted);
        }
      });
    });
  }

  unsubscribe(topic) {
    return new Promise((resolve, reject) => {
      this.client.unsubscribe(topic, (err) => {
        if (err) {
          console.error(`✗ Unsubscribe failed: ${err.message}`);
          reject(err);
        } else {
          console.log(`✓ Unsubscribed from ${topic}`);
          this.messageHandlers.delete(topic);
          resolve();
        }
      });
    });
  }

  publish(topic, payload, qos = 0, retain = false) {
    return new Promise((resolve, reject) => {
      if (typeof payload === 'object') {
        payload = JSON.stringify(payload);
      }

      this.client.publish(topic, payload, { qos, retain }, (err) => {
        if (err) {
          console.error(`✗ Publish failed: ${err.message}`);
          reject(err);
        } else {
          console.log(`✓ Published to ${topic}`);
          resolve();
        }
      });
    });
  }

  disconnect() {
    return new Promise((resolve) => {
      this.client.end(false, () => {
        console.log('✓ Disconnected gracefully');
        resolve();
      });
    });
  }

  resubscribe() {
    for (const topic of this.messageHandlers.keys()) {
      this.subscribe(topic, 1);
    }
  }

  topicMatches(topic, pattern) {
    // Simple wildcard matching
    const topicParts = topic.split('/');
    const patternParts = pattern.split('/');

    for (let i = 0; i < patternParts.length; i++) {
      if (patternParts[i] === '#') {
        return true;
      }
      if (patternParts[i] !== '+' && patternParts[i] !== topicParts[i]) {
        return false;
      }
    }

    return topicParts.length === patternParts.length;
  }
}

// Usage example
async function main() {
  const client = new MQTTClient('mqtt://mqtt.example.com:1883', {
    clientId: 'nodejs_client',
    username: 'user',
    password: 'pass',
    will: {
      topic: 'clients/nodejs/status',
      payload: 'offline',
      qos: 1,
      retain: true
    }
  });

  try {
    await client.connect();

    // Publish online status
    await client.publish('clients/nodejs/status', 'online', 1, true);

    // Subscribe with handler
    await client.subscribe('home/+/temperature', 1, (topic, payload) => {
      const temp = parseFloat(payload);
      if (temp > 25) {
        console.log(`⚠️  High temperature: ${temp}°C`);
      }
    });

    // Publish some test messages
    await client.publish('home/bedroom/temperature', '22.5', 1);
    await client.publish('home/livingroom/temperature', '27.0', 1);

    // Keep running
    process.on('SIGINT', async () => {
      console.log('\nShutting down...');
      await client.publish('clients/nodejs/status', 'offline', 1, true);
      await client.disconnect();
      process.exit(0);
    });

  } catch (error) {
    console.error('Fatal error:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = MQTTClient;
```

**Usage**:
```bash
node mqtt_client.js
```

---

## 12. MQTT over WebSocket

### Why WebSocket?

**Problem**: Browsers can't open raw TCP connections (security).

**Solution**: MQTT over WebSocket allows browser-based MQTT clients.

**Use cases**:
- Web dashboards
- Real-time web apps
- Progressive Web Apps (PWAs)
- Browser-based monitoring tools

### Protocol

**WebSocket upgrade**:
```
GET /mqtt HTTP/1.1
Host: mqtt.example.com:9001
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Protocol: mqtt
Sec-WebSocket-Version: 13
```

**Response**:
```
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
Sec-WebSocket-Protocol: mqtt
```

**After upgrade**: Standard MQTT packets over WebSocket frames.

### Browser Client (MQTT.js)

**HTML + JavaScript**:
```html
<!DOCTYPE html>
<html>
<head>
  <title>MQTT over WebSocket</title>
  <script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
</head>
<body>
  <h1>MQTT Dashboard</h1>
  <div id="status">Disconnected</div>
  <div id="messages"></div>

  <script>
    // Connect to broker via WebSocket
    const client = mqtt.connect('ws://mqtt.example.com:9001/mqtt', {
      clientId: 'browser_' + Math.random().toString(16).substr(2, 8),
      username: 'user',
      password: 'pass',
      reconnectPeriod: 1000
    });

    client.on('connect', () => {
      document.getElementById('status').textContent = 'Connected';
      document.getElementById('status').style.color = 'green';

      // Subscribe to topics
      client.subscribe('home/+/temperature', { qos: 1 });
      client.subscribe('home/+/humidity', { qos: 1 });
    });

    client.on('message', (topic, payload) => {
      const message = payload.toString();
      const div = document.getElementById('messages');
      const entry = document.createElement('div');
      entry.textContent = `${topic}: ${message}`;
      div.appendChild(entry);

      // Keep only last 50 messages
      while (div.children.length > 50) {
        div.removeChild(div.firstChild);
      }
    });

    client.on('error', (error) => {
      console.error('MQTT error:', error);
    });

    client.on('offline', () => {
      document.getElementById('status').textContent = 'Offline';
      document.getElementById('status').style.color = 'red';
    });

    // Publish test message on button click
    function publishTest() {
      client.publish('test/topic', 'Hello from browser!', { qos: 1 });
    }
  </script>

  <button onclick="publishTest()">Publish Test Message</button>
</body>
</html>
```

### Secure WebSocket (WSS)

**TLS-encrypted WebSocket**:
```javascript
// Connect with TLS
const client = mqtt.connect('wss://mqtt.example.com:9002/mqtt', {
  clientId: 'browser_client',
  username: 'user',
  password: 'pass'
});
```

**Mosquitto WSS config**:
```
# WebSocket with TLS
listener 9002
protocol websockets
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
```

### Nginx Reverse Proxy

**MQTT WebSocket behind Nginx**:
```nginx
# nginx.conf
http {
  upstream mqtt {
    server mosquitto:9001;
  }

  server {
    listen 80;
    server_name mqtt.example.com;

    location /mqtt {
      proxy_pass http://mqtt;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "Upgrade";
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;

      # Timeouts
      proxy_connect_timeout 7d;
      proxy_send_timeout 7d;
      proxy_read_timeout 7d;
    }
  }
}
```

---

## 13. Cloud IoT Platforms

### AWS IoT Core

**AWS IoT Core**: Managed MQTT broker with device management, rules engine, and AWS integration.

**Key features**:
- Certificate-based authentication (mutual TLS)
- Device registry (Thing Registry)
- Device shadows (persistent state)
- Rules engine (route to Lambda, DynamoDB, S3, etc.)
- Fleet provisioning
- Jobs (OTA updates, configuration)

**Connection**:
```python
import ssl
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# Initialize client
client = AWSIoTMQTTClient("my_device")
client.configureEndpoint("xxxxx-ats.iot.us-east-1.amazonaws.com", 8883)
client.configureCredentials(
    "AmazonRootCA1.pem",      # Root CA
    "device.pem.key",          # Private key
    "device.pem.crt"           # Certificate
)

# Connection settings
client.configureAutoReconnectBackoffTime(1, 32, 20)
client.configureOfflinePublishQueueing(-1)  # Infinite offline queue
client.configureDrainingFrequency(2)        # 2 Hz
client.configureConnectDisconnectTimeout(10)
client.configureMQTTOperationTimeout(5)

# Connect
client.connect()

# Publish telemetry
client.publish(
    "dt/my_device/telemetry",
    json.dumps({"temperature": 22.5}),
    1
)

# Subscribe to commands
def command_callback(client, userdata, message):
    payload = json.loads(message.payload)
    print(f"Command: {payload}")

client.subscribe("cmd/my_device", 1, command_callback)
```

**Device Shadow**:
```python
# Update shadow (desired state)
shadow = {
    "state": {
        "desired": {
            "color": "red",
            "brightness": 80
        }
    }
}
client.publish(f"$aws/things/my_device/shadow/update", json.dumps(shadow), 1)

# Subscribe to shadow delta (desired vs reported)
def shadow_delta(client, userdata, message):
    delta = json.loads(message.payload)
    print(f"Delta: {delta}")

    # Apply changes and report
    apply_changes(delta)

    reported = {"state": {"reported": delta}}
    client.publish(f"$aws/things/my_device/shadow/update", json.dumps(reported), 1)

client.subscribe(f"$aws/things/my_device/shadow/update/delta", 1, shadow_delta)
```

**Topic structure**:
```
# Telemetry (device → cloud)
dt/{device_id}/telemetry
dt/{device_id}/events

# Commands (cloud → device)
cmd/{device_id}

# Device Shadow
$aws/things/{device_id}/shadow/update
$aws/things/{device_id}/shadow/update/accepted
$aws/things/{device_id}/shadow/update/rejected
$aws/things/{device_id}/shadow/update/delta
$aws/things/{device_id}/shadow/get

# Jobs (OTA updates)
$aws/things/{device_id}/jobs/notify
$aws/things/{device_id}/jobs/{job_id}/get
$aws/things/{device_id}/jobs/{job_id}/update
```

**Rules Engine** (route to AWS services):
```sql
-- Rule to save telemetry to DynamoDB
SELECT temperature, humidity, timestamp
FROM 'dt/+/telemetry'
WHERE temperature > 25

-- Action: DynamoDB PutItem
-- Table: device_telemetry
-- Hash key: device_id (${topic(2)})
-- Range key: timestamp
```

---

### Azure IoT Hub

**Azure IoT Hub**: Managed IoT platform with MQTT support.

**Connection**:
```python
from azure.iot.device import IoTHubDeviceClient

# Connection string (from Azure Portal)
connection_string = "HostName=xxx.azure-devices.net;DeviceId=my_device;SharedAccessKey=xxx"

client = IoTHubDeviceClient.create_from_connection_string(connection_string)
client.connect()

# Send telemetry
message = Message(json.dumps({"temperature": 22.5}))
message.content_encoding = "utf-8"
message.content_type = "application/json"
client.send_message(message)

# Receive cloud-to-device messages
def message_handler(message):
    print(f"Message: {message.data}")

client.on_message_received = message_handler
```

**MQTT topics** (if using raw MQTT):
```
# Device-to-cloud (telemetry)
devices/{device_id}/messages/events/

# Cloud-to-device (commands)
devices/{device_id}/messages/devicebound/#

# Device twin (similar to AWS Device Shadow)
$iothub/twin/PATCH/properties/desired/#
$iothub/twin/GET/?$rid={request_id}
```

---

## 14. MQTT v5.0 Features

### Key Improvements

**MQTT v5.0** (OASIS Standard, 2019) adds:
1. **Reason codes**: Detailed error codes for all ACKs
2. **User properties**: Custom metadata on packets
3. **Shared subscriptions**: Load balancing across consumers
4. **Topic aliases**: Reduce bandwidth for long topics
5. **Request-response**: Built-in request/response pattern
6. **Flow control**: Receive maximum (in-flight messages)
7. **Session expiry**: Explicit session lifetime
8. **Server keep-alive**: Broker can override client keep-alive
9. **Clean start**: Replaces clean session (more intuitive)
10. **Enhanced authentication**: SASL, OAuth 2.0 support

### Reason Codes

**CONNACK reason codes** (v5.0):
```
0x00: Success
0x80: Unspecified error
0x81: Malformed packet
0x82: Protocol error
0x83: Implementation specific error
0x84: Unsupported protocol version
0x85: Client identifier not valid
0x86: Bad username or password
0x87: Not authorized
0x88: Server unavailable
0x89: Server busy
0x8A: Banned
0x8C: Bad authentication method
0x90: Topic name invalid
0x95: Packet too large
0x97: Quota exceeded
0x99: Payload format invalid
0x9A: Retain not supported
0x9B: QoS not supported
0x9C: Use another server
0x9D: Server moved
0x9F: Connection rate exceeded
```

**Python example**:
```python
from paho.mqtt.client import Client, MQTTv5

client = Client(protocol=MQTTv5)

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("Connected successfully")
    else:
        reason = {
            135: "Not authorized",
            144: "Topic name invalid",
            149: "Retain not supported"
        }.get(rc, f"Error code {rc}")
        print(f"Connection failed: {reason}")

client.on_connect = on_connect
```

### User Properties

**Custom metadata** on any packet:
```python
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

# Publish with user properties
properties = Properties(PacketTypes.PUBLISH)
properties.UserProperty = [
    ("device_type", "sensor"),
    ("location", "bedroom"),
    ("firmware_version", "1.2.3")
]

client.publish(
    "devices/sensor_01/telemetry",
    payload=json.dumps({"temp": 22.5}),
    qos=1,
    properties=properties
)

# Receive with user properties
def on_message(client, userdata, msg):
    if msg.properties:
        for key, value in msg.properties.UserProperty:
            print(f"Property: {key}={value}")
```

### Shared Subscriptions

**Load balancing** across multiple consumers:
```
$share/{group}/{topic}
```

**Example**:
```python
# Worker 1
client1.subscribe("$share/workers/jobs/queue", qos=1)

# Worker 2
client2.subscribe("$share/workers/jobs/queue", qos=1)

# Worker 3
client3.subscribe("$share/workers/jobs/queue", qos=1)

# Publisher sends 100 messages
for i in range(100):
    client.publish("jobs/queue", f"job_{i}", qos=1)

# Messages distributed round-robin across workers
# Each worker receives ~33 messages
```

**Use cases**:
- Job queues
- Load balancing
- Horizontal scaling of consumers

### Topic Aliases

**Reduce bandwidth** for long topics:
```python
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

# First publish: Full topic + alias
properties = Properties(PacketTypes.PUBLISH)
properties.TopicAlias = 1  # Assign alias 1 to this topic

client.publish(
    "factory/building_a/floor_2/line_5/machine_10/telemetry",
    "data",
    qos=1,
    properties=properties
)

# Subsequent publishes: Use alias (empty topic)
properties = Properties(PacketTypes.PUBLISH)
properties.TopicAlias = 1

client.publish(
    "",  # Empty topic (use alias)
    "more_data",
    qos=1,
    properties=properties
)
```

### Request-Response Pattern

**Built-in support**:
```python
# Request
properties = Properties(PacketTypes.PUBLISH)
properties.ResponseTopic = "responses/client_123"
properties.CorrelationData = b"request_456"

client.subscribe("responses/client_123", qos=1)
client.publish(
    "requests/get_status",
    "",
    qos=1,
    properties=properties
)

# Response
def on_message(client, userdata, msg):
    if msg.properties and msg.properties.ResponseTopic:
        response_topic = msg.properties.ResponseTopic
        correlation_data = msg.properties.CorrelationData

        # Send response
        response_props = Properties(PacketTypes.PUBLISH)
        response_props.CorrelationData = correlation_data

        client.publish(
            response_topic,
            json.dumps({"status": "online"}),
            qos=1,
            properties=response_props
        )
```

### Session Expiry

**Explicit session lifetime**:
```python
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

properties = Properties(PacketTypes.CONNECT)
properties.SessionExpiryInterval = 3600  # 1 hour

client.connect("mqtt.example.com", 1883, properties=properties)

# Session expires 1 hour after disconnect
# Set to 0 for temporary session
# Set to 0xFFFFFFFF for no expiry
```

---

## 15. Performance Optimization

### Connection Pooling

**Reuse connections** across threads/requests:
```python
import threading

class MQTTConnectionPool:
    def __init__(self, broker, size=10):
        self.broker = broker
        self.pool = []
        self.lock = threading.Lock()

        for i in range(size):
            client = mqtt.Client(client_id=f"pool_{i}")
            client.connect(broker, 1883)
            client.loop_start()
            self.pool.append(client)

    def get_client(self):
        with self.lock:
            if self.pool:
                return self.pool.pop()
        return None

    def return_client(self, client):
        with self.lock:
            self.pool.append(client)

    def publish(self, topic, payload, qos=0):
        client = self.get_client()
        if client:
            client.publish(topic, payload, qos)
            self.return_client(client)

# Usage
pool = MQTTConnectionPool("mqtt.example.com", size=10)

def worker():
    pool.publish("topic", "message", qos=1)

threads = [threading.Thread(target=worker) for _ in range(100)]
for t in threads:
    t.start()
```

### Batching

**Batch multiple messages**:
```python
import time

class BatchPublisher:
    def __init__(self, client, batch_size=100, flush_interval=1):
        self.client = client
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer = []
        self.last_flush = time.time()

    def publish(self, topic, payload, qos=0):
        self.buffer.append((topic, payload, qos))

        # Flush if batch full or interval elapsed
        if len(self.buffer) >= self.batch_size or \
           time.time() - self.last_flush >= self.flush_interval:
            self.flush()

    def flush(self):
        for topic, payload, qos in self.buffer:
            self.client.publish(topic, payload, qos)
        self.buffer = []
        self.last_flush = time.time()

# Usage
publisher = BatchPublisher(client, batch_size=100, flush_interval=1)

for i in range(1000):
    publisher.publish("sensor/data", f"reading_{i}", qos=0)
publisher.flush()  # Flush remaining
```

### QoS Selection

**Use lowest QoS necessary**:
```python
# High-frequency, non-critical data → QoS 0
for i in range(10000):
    client.publish("sensor/temp", str(read_temp()), qos=0)

# Important events → QoS 1
client.publish("alarm/fire", "triggered", qos=1)

# Critical, non-idempotent → QoS 2
client.publish("billing/transaction", json.dumps(tx), qos=2)
```

### Payload Compression

**Compress large payloads**:
```python
import gzip
import json

def publish_compressed(client, topic, data, qos=0):
    payload = json.dumps(data).encode()
    compressed = gzip.compress(payload)

    # Add header indicating compression
    client.publish(
        topic,
        b"GZIP:" + compressed,
        qos
    )

def on_message(client, userdata, msg):
    payload = msg.payload
    if payload.startswith(b"GZIP:"):
        payload = gzip.decompress(payload[5:])
    data = json.loads(payload)
```

### Keep-Alive Tuning

**Balance responsiveness vs battery**:
```python
# High-frequency monitoring (detect failures quickly)
client.connect("mqtt.example.com", 1883, keepalive=5)

# Normal applications
client.connect("mqtt.example.com", 1883, keepalive=60)

# Battery-powered devices (reduce radio usage)
client.connect("mqtt.example.com", 1883, keepalive=300)
```

### Broker Tuning

**Mosquitto optimizations** (`mosquitto.conf`):
```
# Connection limits
max_connections 10000
max_queued_messages 10000

# Message size
message_size_limit 1MB

# Persistence
persistence true
autosave_interval 300

# Logging (reduce I/O)
log_type error
log_type warning
```

**EMQX optimizations** (`emqx.conf`):
```erlang
## Listener
listener.tcp.external.max_connections = 1024000
listener.tcp.external.acceptors = 64
listener.tcp.external.max_conn_rate = 1000

## Session
session.max_inflight = 32
session.max_awaiting_rel = 100

## Message queue
mqtt.max_packet_size = 1MB
mqtt.max_clientid_len = 65535
```

---

## 16. Testing Strategies

### Unit Testing

**Mock MQTT client**:
```python
import unittest
from unittest.mock import MagicMock, patch
import paho.mqtt.client as mqtt

class TestMQTTPublisher(unittest.TestCase):
    @patch('paho.mqtt.client.Client')
    def test_publish(self, mock_client):
        # Mock client
        client = mock_client.return_value
        client.publish.return_value.rc = 0

        # Test
        publisher = MQTTPublisher("mqtt.example.com")
        publisher.publish("test/topic", "message", qos=1)

        # Assertions
        client.publish.assert_called_once_with(
            "test/topic",
            "message",
            qos=1,
            retain=False
        )
```

### Integration Testing

**Test against real broker** (Docker):
```python
import subprocess
import time

class TestMQTTIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start Mosquitto in Docker
        subprocess.run([
            "docker", "run", "-d",
            "--name", "test-mosquitto",
            "-p", "1883:1883",
            "eclipse-mosquitto"
        ])
        time.sleep(2)  # Wait for startup

    @classmethod
    def tearDownClass(cls):
        # Stop and remove container
        subprocess.run(["docker", "stop", "test-mosquitto"])
        subprocess.run(["docker", "rm", "test-mosquitto"])

    def test_publish_subscribe(self):
        # Publisher
        pub = mqtt.Client("publisher")
        pub.connect("localhost", 1883)
        pub.loop_start()

        # Subscriber
        sub = mqtt.Client("subscriber")
        received = []

        def on_message(client, userdata, msg):
            received.append(msg.payload.decode())

        sub.on_message = on_message
        sub.connect("localhost", 1883)
        sub.subscribe("test/topic", qos=1)
        sub.loop_start()

        time.sleep(1)  # Wait for subscription

        # Publish
        pub.publish("test/topic", "test message", qos=1)
        time.sleep(1)  # Wait for delivery

        # Assert
        self.assertEqual(received, ["test message"])

        # Cleanup
        pub.loop_stop()
        sub.loop_stop()
        pub.disconnect()
        sub.disconnect()
```

### Load Testing

**Benchmark connections**:
```python
import time
import threading

def benchmark_connections(broker, num_clients=1000):
    clients = []
    start_time = time.time()

    def connect_client(client_id):
        client = mqtt.Client(client_id=f"client_{client_id}")
        client.connect(broker, 1883)
        client.loop_start()
        clients.append(client)

    # Create threads
    threads = []
    for i in range(num_clients):
        t = threading.Thread(target=connect_client, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all
    for t in threads:
        t.join()

    elapsed = time.time() - start_time
    print(f"Connected {num_clients} clients in {elapsed:.2f}s")
    print(f"Rate: {num_clients / elapsed:.2f} conn/sec")

    # Cleanup
    for client in clients:
        client.loop_stop()
        client.disconnect()

benchmark_connections("mqtt.example.com", num_clients=1000)
```

**Benchmark throughput**:
```python
def benchmark_throughput(broker, num_messages=10000):
    client = mqtt.Client()
    client.connect(broker, 1883)
    client.loop_start()

    start_time = time.time()

    for i in range(num_messages):
        client.publish("test/topic", f"message_{i}", qos=0)

    # Wait for queue to empty
    while client._out_messages:
        time.sleep(0.01)

    elapsed = time.time() - start_time
    print(f"Published {num_messages} messages in {elapsed:.2f}s")
    print(f"Throughput: {num_messages / elapsed:.0f} msg/sec")

    client.loop_stop()
    client.disconnect()

benchmark_throughput("mqtt.example.com", num_messages=10000)
```

---

## 17. Monitoring and Observability

### Broker Metrics

**Mosquitto system topics** (`$SYS/#`):
```bash
# Subscribe to all system topics
mosquitto_sub -h localhost -t '$SYS/#' -v

# Key metrics:
$SYS/broker/uptime
$SYS/broker/version
$SYS/broker/clients/total
$SYS/broker/clients/connected
$SYS/broker/clients/disconnected
$SYS/broker/messages/received
$SYS/broker/messages/sent
$SYS/broker/messages/publish/received
$SYS/broker/messages/publish/sent
$SYS/broker/messages/retained/count
$SYS/broker/subscriptions/count
$SYS/broker/load/messages/received/1min
$SYS/broker/load/messages/received/5min
$SYS/broker/load/messages/received/15min
```

**Python monitoring**:
```python
def monitor_broker(broker):
    client = mqtt.Client()

    def on_message(client, userdata, msg):
        metric = msg.topic.split("/")[-1]
        value = msg.payload.decode()
        print(f"{metric}: {value}")

    client.on_message = on_message
    client.connect(broker, 1883)
    client.subscribe("$SYS/#")
    client.loop_forever()

monitor_broker("mqtt.example.com")
```

### EMQX Metrics (REST API)

```bash
# Get broker stats
curl -u admin:public http://localhost:18083/api/v4/stats

# Response:
{
  "connections.count": 1234,
  "connections.max": 10000,
  "messages.received": 567890,
  "messages.sent": 678901,
  "messages.qos0.received": 400000,
  "messages.qos1.received": 150000,
  "messages.qos2.received": 17890,
  "subscriptions.count": 5678,
  "topics.count": 1234,
  "retained.count": 456
}

# Get client list
curl -u admin:public http://localhost:18083/api/v4/clients

# Get specific client
curl -u admin:public http://localhost:18083/api/v4/clients/client_id
```

### Prometheus + Grafana

**EMQX Prometheus exporter** (`emqx.conf`):
```erlang
## Prometheus
prometheus.push.gateway.server = http://pushgateway:9091
prometheus.interval = 15000
```

**Prometheus scrape config** (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'emqx'
    static_configs:
      - targets: ['emqx:18083']
    metrics_path: '/api/v4/emqx_prometheus'
    basic_auth:
      username: admin
      password: public
```

**Key metrics**:
```
emqx_connections_count
emqx_messages_received
emqx_messages_sent
emqx_messages_qos0_received
emqx_messages_qos1_received
emqx_messages_qos2_received
emqx_session_created
emqx_session_terminated
```

### Application Metrics

**Python client metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
mqtt_messages_sent = Counter('mqtt_messages_sent_total', 'Total messages sent', ['topic', 'qos'])
mqtt_messages_received = Counter('mqtt_messages_received_total', 'Total messages received', ['topic'])
mqtt_publish_latency = Histogram('mqtt_publish_latency_seconds', 'Publish latency')
mqtt_connected_clients = Gauge('mqtt_connected_clients', 'Connected clients')

class InstrumentedMQTTClient:
    def __init__(self, broker):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(broker, 1883)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        mqtt_connected_clients.set(1)

    def on_message(self, client, userdata, msg):
        mqtt_messages_received.labels(topic=msg.topic).inc()

    def publish(self, topic, payload, qos=0):
        with mqtt_publish_latency.time():
            self.client.publish(topic, payload, qos)
        mqtt_messages_sent.labels(topic=topic, qos=qos).inc()
```

---

## 18. Common Patterns

### Telemetry Collection

**IoT device sends periodic telemetry**:
```python
import time
import json

def send_telemetry(client, device_id, interval=60):
    while True:
        telemetry = {
            "device_id": device_id,
            "temperature": read_temperature(),
            "humidity": read_humidity(),
            "battery": get_battery_level(),
            "rssi": get_wifi_rssi(),
            "timestamp": time.time()
        }

        client.publish(
            f"devices/{device_id}/telemetry",
            json.dumps(telemetry),
            qos=1
        )

        time.sleep(interval)
```

### Command and Control

**Backend sends commands to devices**:
```python
# Backend publishes command
command = {
    "action": "update_firmware",
    "url": "https://firmware.example.com/v1.2.3.bin",
    "checksum": "sha256:abc123..."
}

client.publish(
    f"commands/{device_id}/firmware",
    json.dumps(command),
    qos=1
)

# Device subscribes to commands
def on_message(client, userdata, msg):
    command = json.loads(msg.payload)
    action = command.get("action")

    if action == "update_firmware":
        download_and_install_firmware(command["url"], command["checksum"])
    elif action == "reboot":
        reboot_device()
    elif action == "set_interval":
        set_telemetry_interval(command["interval"])

client.subscribe(f"commands/{device_id}/#", qos=1)
```

### Presence Detection

**Detect online/offline devices**:
```python
# Device sets LWT and publishes online
client.will_set(
    f"devices/{device_id}/status",
    "offline",
    qos=1,
    retain=True
)
client.connect("mqtt.example.com", 1883)

# Publish online after connect
def on_connect(client, userdata, flags, rc):
    client.publish(
        f"devices/{device_id}/status",
        "online",
        qos=1,
        retain=True
    )

# Backend monitors presence
def on_message(client, userdata, msg):
    if msg.topic.endswith("/status"):
        device_id = msg.topic.split("/")[1]
        status = msg.payload.decode()

        if status == "online":
            print(f"✓ Device {device_id} is online")
        elif status == "offline":
            print(f"✗ Device {device_id} went offline")
            send_alert(device_id)

client.subscribe("devices/+/status", qos=1)
```

### Request-Response

**RPC-style request-response**:
```python
import uuid

# Client sends request
request_id = str(uuid.uuid4())
reply_topic = f"responses/{client_id}/{request_id}"

# Subscribe to reply topic
client.subscribe(reply_topic, qos=1)

# Publish request with reply_to
request = {
    "action": "get_status",
    "reply_to": reply_topic,
    "request_id": request_id
}
client.publish(f"requests/{device_id}", json.dumps(request), qos=1)

# Wait for response (with timeout)
response_received = threading.Event()
response_data = None

def on_message(client, userdata, msg):
    global response_data
    if msg.topic == reply_topic:
        response_data = json.loads(msg.payload)
        response_received.set()

if response_received.wait(timeout=5):
    print(f"Response: {response_data}")
else:
    print("Timeout waiting for response")

# Device handles request
def on_message(client, userdata, msg):
    request = json.loads(msg.payload)
    reply_to = request.get("reply_to")
    request_id = request.get("request_id")

    # Process request
    response = {
        "status": "online",
        "uptime": get_uptime(),
        "request_id": request_id
    }

    # Send response
    client.publish(reply_to, json.dumps(response), qos=1)
```

### Data Aggregation

**Aggregate data from multiple sensors**:
```python
import time
from collections import defaultdict

class DataAggregator:
    def __init__(self, client, window=60):
        self.client = client
        self.window = window
        self.data = defaultdict(list)
        self.last_flush = time.time()

    def on_message(self, client, userdata, msg):
        # Parse sensor data
        device_id = msg.topic.split("/")[1]
        value = float(msg.payload.decode())

        # Aggregate
        self.data[device_id].append(value)

        # Flush if window elapsed
        if time.time() - self.last_flush >= self.window:
            self.flush()

    def flush(self):
        aggregated = {}
        for device_id, values in self.data.items():
            aggregated[device_id] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values)
            }

        # Publish aggregated data
        self.client.publish(
            "aggregated/temperature",
            json.dumps(aggregated),
            qos=1
        )

        self.data.clear()
        self.last_flush = time.time()

# Usage
aggregator = DataAggregator(client, window=60)
client.on_message = aggregator.on_message
client.subscribe("devices/+/temperature", qos=1)
```

---

## 19. Anti-Patterns

### ❌ Subscribing to `#` Wildcard

**Problem**: Receives ALL topics (broker overload)

**Bad**:
```python
client.subscribe("#")  # Subscribes to everything!
```

**Why it's bad**:
- Massive message volume
- Broker CPU/memory overload
- Network bandwidth waste
- Client overwhelmed

**Better**:
```python
# Subscribe to specific topics
client.subscribe("devices/+/telemetry")
client.subscribe("alerts/#")
```

---

### ❌ Using QoS 2 Everywhere

**Problem**: Highest overhead (4-way handshake)

**Bad**:
```python
# QoS 2 for high-frequency sensor data
for i in range(10000):
    client.publish("sensor/temp", str(temp), qos=2)
```

**Why it's bad**:
- 4x network traffic vs QoS 0
- 2x latency vs QoS 1
- Broker memory overhead
- Battery drain on devices

**Better**:
```python
# Use appropriate QoS
client.publish("sensor/temp", str(temp), qos=0)          # Non-critical
client.publish("alarm/fire", "triggered", qos=1)         # Important
client.publish("billing/tx", json.dumps(tx), qos=2)      # Critical only
```

---

### ❌ Large Payloads

**Problem**: MQTT is for small messages

**Bad**:
```python
# Send 5 MB image via MQTT
with open("image.jpg", "rb") as f:
    image_data = f.read()
client.publish("device/image", image_data, qos=1)
```

**Why it's bad**:
- Broker memory exhausted
- Network congestion
- Timeout failures
- Not designed for large files

**Better**:
```python
# Upload to S3, send URL via MQTT
url = upload_to_s3("image.jpg")
client.publish("device/image", url, qos=1)
```

---

### ❌ Embedding Data in Topics

**Problem**: Topics for routing, not data

**Bad**:
```python
# Embed temperature value in topic
client.publish(f"sensor/temp/{temp_value}", "", qos=0)
```

**Why it's bad**:
- Infinite topics (broker memory leak)
- Can't use wildcards effectively
- Topic ACL doesn't work
- Not MQTT best practice

**Better**:
```python
# Topic for routing, payload for data
client.publish("sensor/temp", str(temp_value), qos=0)
```

---

### ❌ No Reconnection Logic

**Problem**: Connection lost forever

**Bad**:
```python
client = mqtt.Client()
client.connect("mqtt.example.com", 1883)
# No reconnection handling
```

**Why it's bad**:
- Network issues disconnect forever
- Server restarts disconnect forever
- No resilience

**Better**:
```python
client = mqtt.Client()
client.on_disconnect = lambda *args: client.reconnect()
client.connect("mqtt.example.com", 1883)
client.loop_forever()  # Auto-reconnects
```

---

### ❌ Ignoring Connection Errors

**Problem**: Silent failures

**Bad**:
```python
client.connect("mqtt.example.com", 1883)
client.publish("topic", "message")  # May fail silently
```

**Why it's bad**:
- Messages lost
- No error visibility
- Hard to debug

**Better**:
```python
def on_connect(client, userdata, flags, rc):
    if rc != 0:
        print(f"Connection failed: {rc}")
        # Handle error
    else:
        print("Connected")

client.on_connect = on_connect
client.connect("mqtt.example.com", 1883)
```

---

### ❌ No Authentication

**Problem**: Open broker accessible to anyone

**Bad**:
```
# mosquitto.conf
allow_anonymous true
```

**Why it's bad**:
- Anyone can publish/subscribe
- Data leaks
- Broker abuse
- Security vulnerability

**Better**:
```
# mosquitto.conf
allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl.conf

# TLS
listener 8883
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
```

---

## 20. Comparison with Alternatives

### MQTT vs AMQP (RabbitMQ)

| Feature | MQTT | AMQP |
|---------|------|------|
| **Pattern** | Pub-Sub | Pub-Sub + Queues |
| **Overhead** | 2 bytes | 8 bytes |
| **Use Case** | IoT, M2M | Enterprise messaging |
| **QoS** | 0, 1, 2 | 0, 1 |
| **Routing** | Topics | Exchanges + Bindings |
| **Queues** | No (broker-side only) | Yes (first-class) |
| **Transactions** | No | Yes |
| **Complexity** | Simple | Complex |

**Use MQTT when**: IoT devices, constrained networks, simple pub-sub
**Use AMQP when**: Enterprise integration, complex routing, guaranteed delivery with queues

---

### MQTT vs Kafka

| Feature | MQTT | Kafka |
|---------|------|-------|
| **Pattern** | Pub-Sub | Log-based streaming |
| **Retention** | Transient (or retained) | Persistent (days/weeks) |
| **Use Case** | IoT, real-time events | Event streaming, analytics |
| **Latency** | Low (ms) | Higher (10s of ms) |
| **Throughput** | Moderate | Very high |
| **Ordering** | Per topic | Per partition |
| **Consumers** | Push | Pull |

**Use MQTT when**: Real-time device communication, low latency
**Use Kafka when**: Event streaming, log aggregation, high throughput, replay

---

### MQTT vs WebSocket

| Feature | MQTT | WebSocket |
|---------|------|-----------|
| **Pattern** | Pub-Sub | Bidirectional |
| **Protocol** | MQTT (application) | Transport only |
| **Routing** | Broker-based topics | Application-level |
| **QoS** | 0, 1, 2 | None (TCP reliability) |
| **Use Case** | IoT, decoupled messaging | Real-time web apps |
| **Overhead** | Higher (broker) | Lower (direct) |

**Use MQTT when**: Decoupled pub-sub, QoS guarantees, many-to-many
**Use WebSocket when**: Direct client-server communication, custom protocol

---

### MQTT vs CoAP

| Feature | MQTT | CoAP |
|---------|------|------|
| **Transport** | TCP | UDP |
| **Pattern** | Pub-Sub | Request-Response |
| **Overhead** | 2 bytes (TCP overhead) | 4 bytes (UDP, lower) |
| **Use Case** | Reliable messaging | Extremely constrained devices |
| **Reliability** | TCP (reliable) | UDP (less reliable) |
| **QoS** | 0, 1, 2 | CON/NON |

**Use MQTT when**: Need pub-sub, reliable delivery, TCP acceptable
**Use CoAP when**: Extremely constrained, UDP preferred, RESTful API style

---

## 21. References

### Official Specifications

**MQTT v3.1.1**:
- OASIS Standard: https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html
- Ratified: October 29, 2014

**MQTT v5.0**:
- OASIS Standard: https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
- Ratified: March 7, 2019

### Broker Documentation

**Mosquitto**:
- Website: https://mosquitto.org/
- Documentation: https://mosquitto.org/documentation/
- GitHub: https://github.com/eclipse/mosquitto

**EMQX**:
- Website: https://www.emqx.io/
- Documentation: https://www.emqx.io/docs/en/latest/
- GitHub: https://github.com/emqx/emqx

**HiveMQ**:
- Website: https://www.hivemq.com/
- Documentation: https://www.hivemq.com/docs/

### Client Libraries

**Python (paho-mqtt)**:
- GitHub: https://github.com/eclipse/paho.mqtt.python
- Docs: https://eclipse.dev/paho/index.php?page=clients/python/docs/index.php

**Node.js (MQTT.js)**:
- GitHub: https://github.com/mqttjs/MQTT.js
- Docs: https://github.com/mqttjs/MQTT.js#readme

**Go (paho.mqtt.golang)**:
- GitHub: https://github.com/eclipse/paho.mqtt.golang

**Java (paho.mqtt.java)**:
- GitHub: https://github.com/eclipse/paho.mqtt.java

### Cloud Platforms

**AWS IoT Core**:
- Documentation: https://docs.aws.amazon.com/iot/
- MQTT Support: https://docs.aws.amazon.com/iot/latest/developerguide/mqtt.html

**Azure IoT Hub**:
- Documentation: https://docs.microsoft.com/en-us/azure/iot-hub/
- MQTT Support: https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-mqtt-support

**Google Cloud IoT Core** (deprecated):
- Migrating to alternatives

### Books

**"Building the Internet of Things with IPv6 and MIPv6"** by Daniel Minoli
**"MQTT Essentials"** by HiveMQ (free online)
**"IoT Inc"** by Bruce Sinclair

### Testing Tools

**MQTT Explorer**:
- GUI client for testing and debugging
- GitHub: https://github.com/thomasnordquist/MQTT-Explorer

**MQTT.fx**:
- Desktop MQTT client
- Website: https://mqttfx.jensd.de/

**mosquitto_pub/sub**:
- CLI tools (installed with Mosquitto)
- Documentation: https://mosquitto.org/man/mosquitto_pub-1.html

---

**End of Reference**

This comprehensive reference covers MQTT from fundamentals to advanced patterns. Use it as a guide for implementing production MQTT systems.
