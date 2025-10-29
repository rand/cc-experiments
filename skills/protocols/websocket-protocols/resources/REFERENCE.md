# WebSocket Protocols Reference

**Version**: 1.0
**Last Updated**: 2025-10-29
**Lines**: ~3,200

This comprehensive reference covers WebSocket protocol implementation, scaling, security, and production deployment patterns.

---

## Table of Contents

1. [WebSocket Protocol Fundamentals](#1-websocket-protocol-fundamentals)
2. [Protocol Handshake](#2-protocol-handshake)
3. [Frame Structure](#3-frame-structure)
4. [Message Types and Opcodes](#4-message-types-and-opcodes)
5. [Connection Lifecycle](#5-connection-lifecycle)
6. [Python Implementation](#6-python-implementation)
7. [Node.js Implementation](#7-nodejs-implementation)
8. [Go Implementation](#8-go-implementation)
9. [Java Implementation](#9-java-implementation)
10. [Client Implementation Patterns](#10-client-implementation-patterns)
11. [Load Balancing](#11-load-balancing)
12. [Horizontal Scaling](#12-horizontal-scaling)
13. [Authentication and Authorization](#13-authentication-and-authorization)
14. [Security Best Practices](#14-security-best-practices)
15. [Heartbeat and Health Monitoring](#15-heartbeat-and-health-monitoring)
16. [Error Handling](#16-error-handling)
17. [Performance Optimization](#17-performance-optimization)
18. [Testing and Debugging](#18-testing-and-debugging)
19. [Production Deployment](#19-production-deployment)
20. [Monitoring and Observability](#20-monitoring-and-observability)
21. [Anti-Patterns](#21-anti-patterns)
22. [References](#22-references)

---

## 1. WebSocket Protocol Fundamentals

### What is WebSocket?

**WebSocket** (RFC 6455) is a protocol providing full-duplex communication channels over a single TCP connection. It enables bidirectional, real-time data exchange between client and server.

**Key characteristics**:
- **Full-duplex**: Both client and server can send messages simultaneously
- **Persistent connection**: Long-lived connection, not request-response
- **Low overhead**: 2-byte frame header (vs HTTP headers)
- **Upgrade from HTTP**: Starts as HTTP/1.1, upgrades via handshake
- **Binary and text**: Supports both UTF-8 text and binary data
- **Built-in ping/pong**: Connection health checking mechanism
- **Cross-origin**: Subject to same CORS policies as HTTP

### WebSocket vs HTTP

| Feature | WebSocket | HTTP |
|---------|-----------|------|
| **Connection** | Persistent | Request-response |
| **Direction** | Full-duplex | Half-duplex |
| **Overhead** | 2-byte frame | Headers per request |
| **Latency** | Low (no handshake) | Higher (handshake per request) |
| **Server Push** | Native | Workarounds (SSE, long polling) |
| **Use Case** | Real-time, bidirectional | CRUD, RESTful APIs |
| **Browser Support** | All modern browsers | Universal |

### When to Use WebSocket

**Ideal use cases**:
- **Real-time chat**: Instant messaging, group chat
- **Live updates**: Stock tickers, sports scores, news feeds
- **Collaborative editing**: Google Docs-style applications
- **Gaming**: Multiplayer game state synchronization
- **IoT**: Sensor data streaming, device control
- **Monitoring**: Real-time dashboards, system metrics
- **Trading platforms**: Order book updates, trade execution

**When NOT to use WebSocket**:
- Simple CRUD operations (use REST)
- Infrequent updates (use polling or SSE)
- Public APIs for unknown clients (use REST)
- Static content delivery (use HTTP)
- Large file transfers (use HTTP with resumable uploads)

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                         Client                                │
│                                                               │
│  ┌────────────┐    HTTP Upgrade Request    ┌──────────────┐ │
│  │ JavaScript │──────────────────────────►  │   Server     │ │
│  │  WebSocket │    101 Switching Protocols  │              │ │
│  │    API     │◄──────────────────────────  │   WebSocket  │ │
│  └────────────┘                             │   Handler    │ │
│        ▲│                                    └──────────────┘ │
│        │▼                                           ▲│        │
│   ┌─────────┐                                      │▼        │
│   │ Frames  │◄──────────────────────────────────►┌──────┐   │
│   │ (binary)│      WebSocket Protocol             │Redis │   │
│   └─────────┘      Full-duplex over TCP           │Pub/  │   │
│                                                    │Sub   │   │
└────────────────────────────────────────────────────┴──────┘   │
```

---

## 2. Protocol Handshake

### Opening Handshake

The WebSocket connection begins with an HTTP/1.1 upgrade request.

**Client Request**:
```http
GET /chat HTTP/1.1
Host: server.example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
Origin: http://example.com
Sec-WebSocket-Protocol: chat, superchat
Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits
```

**Required headers**:
- `Upgrade: websocket` - Requests protocol upgrade
- `Connection: Upgrade` - Indicates upgrade intent
- `Sec-WebSocket-Key` - Base64-encoded random 16-byte value (prevents caching)
- `Sec-WebSocket-Version: 13` - WebSocket protocol version (always 13)
- `Host` - Server hostname (standard HTTP header)

**Optional headers**:
- `Origin` - For CORS validation (browser sets automatically)
- `Sec-WebSocket-Protocol` - Subprotocol negotiation (comma-separated)
- `Sec-WebSocket-Extensions` - Extension negotiation (e.g., compression)
- `Cookie` - Authentication cookies
- Custom headers (e.g., `Authorization`)

**Server Response**:
```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
Sec-WebSocket-Protocol: chat
Sec-WebSocket-Extensions: permessage-deflate
```

**Required response headers**:
- `HTTP/1.1 101 Switching Protocols` - Upgrade accepted
- `Upgrade: websocket` - Confirms protocol upgrade
- `Connection: Upgrade` - Confirms connection upgrade
- `Sec-WebSocket-Accept` - Cryptographic confirmation (see below)

**Optional response headers**:
- `Sec-WebSocket-Protocol` - Selected subprotocol (must be from client's list)
- `Sec-WebSocket-Extensions` - Accepted extensions

### Sec-WebSocket-Accept Computation

The `Sec-WebSocket-Accept` header proves the server supports WebSocket protocol.

**Algorithm**:
1. Concatenate `Sec-WebSocket-Key` + magic GUID
2. Compute SHA-1 hash
3. Base64-encode the hash

**Magic GUID**: `258EAFA5-E914-47DA-95CA-C5AB0DC85B11` (defined in RFC 6455)

**Python implementation**:
```python
import base64
import hashlib

def compute_accept_key(websocket_key: str) -> str:
    """
    Compute Sec-WebSocket-Accept from Sec-WebSocket-Key.

    Args:
        websocket_key: Value from Sec-WebSocket-Key header

    Returns:
        Base64-encoded SHA-1 hash for Sec-WebSocket-Accept
    """
    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    concatenated = websocket_key + GUID
    sha1_hash = hashlib.sha1(concatenated.encode('utf-8')).digest()
    return base64.b64encode(sha1_hash).decode('utf-8')

# Example
key = "dGhlIHNhbXBsZSBub25jZQ=="
accept = compute_accept_key(key)
# Result: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

**Why this mechanism?**:
- Prevents non-WebSocket servers from accidentally accepting upgrade
- Proves server understands WebSocket protocol
- Protects against certain proxy caching issues

### Subprotocol Negotiation

Subprotocols allow application-level protocol selection.

**Client request**:
```http
Sec-WebSocket-Protocol: mqtt, v10.stomp, v11.stomp
```

**Server selects one**:
```http
Sec-WebSocket-Protocol: v11.stomp
```

**Common subprotocols**:
- `mqtt` - MQTT over WebSocket
- `stomp` - STOMP messaging protocol
- `wamp` - Web Application Messaging Protocol
- Custom protocols (e.g., `chat.v1`, `graphql-ws`)

**Implementation**:
```python
async def handler(websocket, path):
    # Check requested subprotocols
    requested = websocket.request_headers.get('Sec-WebSocket-Protocol', '')
    subprotocols = [s.strip() for s in requested.split(',')]

    # Select supported protocol
    if 'chat.v2' in subprotocols:
        websocket.subprotocol = 'chat.v2'
    elif 'chat.v1' in subprotocols:
        websocket.subprotocol = 'chat.v1'
    else:
        await websocket.close(4000, "No supported subprotocol")
        return
```

### Extension Negotiation

Extensions modify the WebSocket framing layer.

**permessage-deflate** (compression):
```http
Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits=15; server_max_window_bits=15
```

**Parameters**:
- `client_max_window_bits`: LZ77 sliding window size (client)
- `server_max_window_bits`: LZ77 sliding window size (server)
- `client_no_context_takeover`: Disable compression context reuse (client)
- `server_no_context_takeover`: Disable compression context reuse (server)

**Benefits**:
- Reduces bandwidth (text messages compress well)
- Lower latency for slow connections

**Costs**:
- CPU overhead (compression/decompression)
- Memory overhead (sliding windows)
- Complexity (compression state management)

**When to use**:
- ✅ Large text messages (JSON, XML)
- ✅ Bandwidth-constrained connections
- ❌ Already compressed data (images, video)
- ❌ CPU-constrained servers
- ❌ Binary data (typically pre-compressed)

---

## 3. Frame Structure

### Frame Format

Every WebSocket message is sent as one or more frames.

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len == 127  |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                               |Masking-key, if MASK set to 1  |
+-------------------------------+-------------------------------+
| Masking-key (continued)       |          Payload Data         |
+-------------------------------- - - - - - - - - - - - - - - - +
:                     Payload Data continued ...                :
+ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
|                     Payload Data continued ...                |
+---------------------------------------------------------------+
```

### Frame Header

**Byte 0**:
- **FIN (bit 0)**: Final fragment flag
  - `1` = Last frame in message
  - `0` = More fragments follow
- **RSV1-RSV3 (bits 1-3)**: Reserved for extensions
  - Must be `0` unless extension defines meaning
  - permessage-deflate uses RSV1
- **Opcode (bits 4-7)**: Frame type

**Byte 1**:
- **MASK (bit 0)**: Masking flag
  - `1` = Payload is masked (required for client→server)
  - `0` = Payload not masked (server→client)
- **Payload length (bits 1-7)**:
  - `0-125`: Actual length
  - `126`: Next 2 bytes = 16-bit length
  - `127`: Next 8 bytes = 64-bit length

**Extended payload length**:
- If payload length = 126: Next 2 bytes (16-bit unsigned)
- If payload length = 127: Next 8 bytes (64-bit unsigned)

**Masking key** (4 bytes):
- Present only if MASK = 1
- Random 32-bit value
- Used to XOR payload data

### Payload Masking

Client frames MUST be masked (prevents cache poisoning attacks).

**Masking algorithm**:
```python
def mask_payload(data: bytes, masking_key: bytes) -> bytes:
    """
    Mask/unmask payload data using XOR with masking key.

    Args:
        data: Payload data to mask/unmask
        masking_key: 4-byte masking key

    Returns:
        Masked/unmasked data (XOR is reversible)
    """
    masked = bytearray(len(data))
    for i in range(len(data)):
        masked[i] = data[i] ^ masking_key[i % 4]
    return bytes(masked)

# Example
import os
data = b"Hello, WebSocket!"
masking_key = os.urandom(4)
masked = mask_payload(data, masking_key)
unmasked = mask_payload(masked, masking_key)  # XOR is reversible
assert unmasked == data
```

**Why masking?**:
- Prevents certain proxy cache poisoning attacks
- Makes it impossible to inject predictable frames
- Required by RFC 6455 for client→server frames

**Server→client frames**:
- MUST NOT be masked
- Server can send frames without masking

### Frame Size Limits

**Payload length encoding**:
- **0-125 bytes**: Single-byte length field
- **126-65,535 bytes**: 3-byte length (flag + 2-byte length)
- **65,536+ bytes**: 9-byte length (flag + 8-byte length)

**Practical limits**:
- **Maximum frame size**: 2^63 - 1 bytes (~9 exabytes, theoretical)
- **Practical server limits**: 1-16 MB per message (configurable)
- **Recommendation**: Keep messages < 1 MB for best performance

**Fragmentation**:
- Large messages can be split across multiple frames
- Receiver must buffer and reassemble fragments
- Useful for streaming large data

---

## 4. Message Types and Opcodes

### Opcode Reference

| Opcode | Type | Description |
|--------|------|-------------|
| `0x0` | Continuation | Continuation frame (not first frame) |
| `0x1` | Text | UTF-8 encoded text data |
| `0x2` | Binary | Binary application data |
| `0x3-0x7` | Reserved | Reserved for future data frames |
| `0x8` | Close | Connection close frame |
| `0x9` | Ping | Heartbeat request |
| `0xA` | Pong | Heartbeat response |
| `0xB-0xF` | Reserved | Reserved for future control frames |

### Text Frames (0x1)

UTF-8 encoded text messages.

**Characteristics**:
- Payload MUST be valid UTF-8
- Invalid UTF-8 = protocol violation (close 1007)
- Can be fragmented across multiple frames
- Null terminator not required

**Example**:
```python
import json

# Send text message
message = json.dumps({"type": "chat", "text": "Hello!"})
await websocket.send(message)  # Automatically uses text frame

# Receive text message
data = await websocket.recv()
message = json.loads(data)
```

**Use cases**:
- JSON messages
- Plain text chat
- XML/SOAP messages
- CSV data

### Binary Frames (0x2)

Raw binary data.

**Characteristics**:
- No encoding restrictions
- Efficient for non-text data
- Can be fragmented
- No validation performed

**Example**:
```python
import struct

# Send binary message (image data)
with open('image.png', 'rb') as f:
    image_data = f.read()
await websocket.send(image_data)  # Automatically uses binary frame

# Send structured binary (e.g., protocol buffer)
message = struct.pack('!IH', message_id, payload_length)
await websocket.send(message)

# Receive binary
data = await websocket.recv()
message_id, length = struct.unpack('!IH', data[:6])
```

**Use cases**:
- Image/video streaming
- Audio data
- Protocol Buffers, MessagePack, CBOR
- File transfers
- Game state snapshots

### Continuation Frames (0x0)

Used for fragmented messages.

**Fragmentation rules**:
1. First frame: Opcode = 0x1 (text) or 0x2 (binary), FIN = 0
2. Middle frames: Opcode = 0x0 (continuation), FIN = 0
3. Last frame: Opcode = 0x0 (continuation), FIN = 1

**Example**:
```
Frame 1: FIN=0, opcode=0x1 (text), payload="Hello, "
Frame 2: FIN=0, opcode=0x0 (continuation), payload="World"
Frame 3: FIN=1, opcode=0x0 (continuation), payload="!"
Result: "Hello, World!"
```

**Control frames**:
- MUST NOT be fragmented
- Can be interleaved between fragments
- Allow ping/pong during large message transfer

**Implementation**:
```python
async def send_fragmented(websocket, data: bytes, chunk_size: int = 64 * 1024):
    """Send data in fragments"""
    total = len(data)
    offset = 0

    while offset < total:
        chunk = data[offset:offset + chunk_size]
        is_final = (offset + chunk_size >= total)
        is_first = (offset == 0)

        # Determine opcode
        if is_first:
            opcode = 0x2  # Binary
        else:
            opcode = 0x0  # Continuation

        # Send frame (pseudo-code)
        await websocket.send_frame(
            fin=is_final,
            opcode=opcode,
            payload=chunk
        )

        offset += chunk_size
```

### Close Frames (0x8)

Initiates graceful connection closure.

**Frame structure**:
- **2-byte status code** (optional)
- **UTF-8 reason string** (optional)

**Common status codes**:

| Code | Name | Description |
|------|------|-------------|
| `1000` | Normal Closure | Successful operation complete |
| `1001` | Going Away | Endpoint going away (server shutdown, browser navigation) |
| `1002` | Protocol Error | Protocol violation detected |
| `1003` | Unsupported Data | Received data type not accepted |
| `1005` | No Status | No status code present (not sent on wire) |
| `1006` | Abnormal Closure | Connection closed abnormally (not sent on wire) |
| `1007` | Invalid Payload | Invalid UTF-8 in text frame |
| `1008` | Policy Violation | Message violates policy (e.g., too large) |
| `1009` | Message Too Big | Message too large to process |
| `1010` | Missing Extension | Client requires extension, server doesn't support |
| `1011` | Internal Error | Server encountered error |
| `1012` | Service Restart | Server restarting |
| `1013` | Try Again Later | Temporary server overload |
| `1014` | Bad Gateway | Gateway/proxy error |
| `1015` | TLS Handshake | TLS handshake failure (not sent on wire) |
| `4000-4999` | Private Use | Application-specific codes |

**Close handshake**:
1. Initiator sends close frame with status code
2. Receiver sends close frame in response
3. Both sides close TCP connection

**Example**:
```python
# Close with reason
await websocket.close(code=1000, reason="Normal closure")

# Close on error
await websocket.close(code=1008, reason="Message exceeds size limit")

# Handle close frame
try:
    async for message in websocket:
        # Process message
        pass
except websockets.exceptions.ConnectionClosedOK:
    print("Connection closed normally")
except websockets.exceptions.ConnectionClosedError as e:
    print(f"Connection closed with error: {e.code} - {e.reason}")
```

### Ping/Pong Frames (0x9, 0xA)

Heartbeat mechanism for connection health.

**Ping (0x9)**:
- Sender can include application data (≤125 bytes)
- Receiver MUST respond with pong containing same data

**Pong (0xA)**:
- Response to ping
- Can be sent unsolicited (heartbeat)
- MUST echo ping's payload

**Characteristics**:
- Control frames (cannot be fragmented)
- Can be sent at any time, even during message fragments
- Payload data is arbitrary (useful for timing/correlation)

**Example**:
```python
import asyncio
import time

async def send_ping(websocket):
    """Send ping with timestamp"""
    timestamp = str(time.time()).encode('utf-8')
    await websocket.ping(timestamp)

async def heartbeat(websocket, interval: int = 30):
    """Periodic heartbeat"""
    while True:
        try:
            start = time.time()
            pong_waiter = await websocket.ping()
            await asyncio.wait_for(pong_waiter, timeout=10)
            latency = time.time() - start
            print(f"Ping: {latency*1000:.2f}ms")
        except asyncio.TimeoutError:
            print("Ping timeout - connection dead")
            await websocket.close()
            break
        await asyncio.sleep(interval)
```

**Use cases**:
- Detect dead connections
- Keep connections alive through firewalls/proxies
- Measure round-trip latency
- Prevent idle timeouts

---

## 5. Connection Lifecycle

### State Machine

```
┌──────────────┐
│ CONNECTING   │ ──handshake──► ┌──────────┐
└──────────────┘                │  OPEN    │
       │                        └────┬─────┘
       │ handshake failed           │
       ▼                            │ close initiated
┌──────────────┐                   ▼
│   CLOSING    │◄──────────────┌──────────┐
└──────┬───────┘  close ack    │ CLOSING  │
       │                        └──────────┘
       │ TCP close
       ▼
┌──────────────┐
│   CLOSED     │
└──────────────┘
```

**States**:
1. **CONNECTING**: Handshake in progress
2. **OPEN**: Connection established, data transfer possible
3. **CLOSING**: Close handshake initiated
4. **CLOSED**: Connection terminated

### Connection Establishment

**Client-side**:
```javascript
const ws = new WebSocket('wss://example.com/ws');

ws.onopen = (event) => {
    console.log('Connected');
    ws.send('Hello, Server!');
};

ws.onerror = (error) => {
    console.error('Connection error:', error);
};
```

**Server-side** (Python):
```python
import asyncio
import websockets

async def handler(websocket, path):
    print(f"Client connected from {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"Received: {message}")
            await websocket.send(f"Echo: {message}")
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Run forever

asyncio.run(main())
```

### Message Exchange

**Sending messages**:
```python
# Text message
await websocket.send("Hello, World!")
await websocket.send(json.dumps({"type": "message", "data": "..."}))

# Binary message
await websocket.send(b"\x00\x01\x02\x03")

# Check if connection is open
if websocket.open:
    await websocket.send("Message")
```

**Receiving messages**:
```python
# Blocking receive
message = await websocket.recv()

# Iterate over messages
async for message in websocket:
    if isinstance(message, str):
        print(f"Text: {message}")
    else:
        print(f"Binary: {len(message)} bytes")

# Non-blocking receive with timeout
try:
    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
except asyncio.TimeoutError:
    print("No message received within 5 seconds")
```

### Graceful Shutdown

**Client-initiated close**:
```javascript
// Close with reason
ws.close(1000, 'Normal closure');

// Close on error
ws.close(4001, 'Authentication failed');
```

**Server-initiated close**:
```python
# Normal closure
await websocket.close(code=1000, reason="Server shutting down")

# Close with custom code
await websocket.close(code=4000, reason="Session expired")

# Wait for close handshake
await websocket.wait_closed()
```

**Handling server shutdown**:
```python
import signal
import asyncio

class WebSocketServer:
    def __init__(self):
        self.clients = set()

    async def handler(self, websocket, path):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                # Handle message
                pass
        finally:
            self.clients.remove(websocket)

    async def shutdown(self):
        """Gracefully close all connections"""
        print(f"Closing {len(self.clients)} connections...")

        # Notify all clients
        close_tasks = [
            client.close(code=1001, reason="Server shutting down")
            for client in self.clients
        ]

        # Wait for all close handshakes (with timeout)
        await asyncio.gather(*close_tasks, return_exceptions=True)

    async def run(self):
        async with websockets.serve(self.handler, "0.0.0.0", 8765) as server:
            # Setup signal handlers
            loop = asyncio.get_running_loop()
            stop = loop.create_future()

            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, stop.set_result, None)

            # Wait for shutdown signal
            await stop

            # Graceful shutdown
            await self.shutdown()

# Run server
server = WebSocketServer()
asyncio.run(server.run())
```

### Error Handling

**Connection errors**:
```python
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedOK,
    ConnectionClosedError,
    InvalidHandshake,
    InvalidMessage,
    InvalidStatusCode
)

async def handler(websocket, path):
    try:
        async for message in websocket:
            await process_message(message)
    except ConnectionClosedOK:
        # Normal close (1000-1001)
        print("Connection closed normally")
    except ConnectionClosedError as e:
        # Abnormal close
        print(f"Connection closed with error: {e.code} - {e.reason}")
    except InvalidMessage as e:
        # Protocol violation
        print(f"Invalid message: {e}")
        await websocket.close(code=1002, reason="Protocol error")
    except Exception as e:
        # Application error
        print(f"Error: {e}")
        await websocket.close(code=1011, reason="Internal error")
```

---

## 6. Python Implementation

### Using `websockets` Library

**Installation**:
```bash
pip install websockets
```

### Basic Server

```python
#!/usr/bin/env python3
"""
Basic WebSocket server with connection management.
"""

import asyncio
import json
import logging
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketServer:
    """WebSocket server with client tracking"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()

    async def register(self, websocket: WebSocketServerProtocol) -> None:
        """Register new client"""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}. Total: {len(self.clients)}")

    async def unregister(self, websocket: WebSocketServerProtocol) -> None:
        """Unregister client"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected: {websocket.remote_address}. Total: {len(self.clients)}")

    async def broadcast(self, message: str, exclude: WebSocketServerProtocol = None) -> None:
        """Broadcast message to all clients except sender"""
        if not self.clients:
            return

        tasks = [
            client.send(message)
            for client in self.clients
            if client != exclude and client.open
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def handler(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handle individual client connection"""
        await self.register(websocket)

        try:
            async for message in websocket:
                # Parse message
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Connection closed: {e.code} - {e.reason}")
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
        finally:
            await self.unregister(websocket)

    async def handle_message(self, websocket: WebSocketServerProtocol, data: dict) -> None:
        """Handle incoming message"""
        msg_type = data.get("type")

        if msg_type == "ping":
            # Respond to application-level ping
            await websocket.send(json.dumps({"type": "pong"}))

        elif msg_type == "broadcast":
            # Broadcast to all clients
            await self.broadcast(json.dumps(data), exclude=websocket)

        elif msg_type == "echo":
            # Echo back to sender
            await websocket.send(json.dumps({
                "type": "echo",
                "data": data.get("data")
            }))
        else:
            # Unknown message type
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {msg_type}"
            }))

    def run(self) -> None:
        """Start WebSocket server"""
        async def serve():
            async with websockets.serve(
                self.handler,
                self.host,
                self.port,
                ping_interval=30,           # Send ping every 30 seconds
                ping_timeout=10,            # Close if no pong within 10 seconds
                max_size=10 * 1024 * 1024,  # 10 MB max message size
                compression=None             # Disable compression (enable if needed)
            ):
                logger.info(f"WebSocket server running on ws://{self.host}:{self.port}")
                await asyncio.Future()  # Run forever

        asyncio.run(serve())


if __name__ == "__main__":
    server = WebSocketServer()
    server.run()
```

### Client with Reconnection

```python
#!/usr/bin/env python3
"""
WebSocket client with automatic reconnection and exponential backoff.
"""

import asyncio
import json
import logging
from typing import Optional, Callable
import websockets
from websockets.client import WebSocketClientProtocol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReconnectingWebSocketClient:
    """WebSocket client with automatic reconnection"""

    def __init__(
        self,
        uri: str,
        on_message: Optional[Callable] = None,
        max_reconnect_delay: int = 60
    ):
        self.uri = uri
        self.on_message = on_message
        self.max_reconnect_delay = max_reconnect_delay
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.running = False

    async def connect(self) -> None:
        """Connect with exponential backoff"""
        delay = 1

        while self.running:
            try:
                self.websocket = await websockets.connect(
                    self.uri,
                    ping_interval=30,
                    ping_timeout=10
                )
                logger.info(f"Connected to {self.uri}")
                delay = 1  # Reset delay on successful connection

                # Message receive loop
                async for message in self.websocket:
                    if self.on_message:
                        await self.on_message(message)

            except (websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.InvalidMessage,
                    OSError) as e:
                logger.warning(f"Connection lost: {e}")

                if self.running:
                    # Exponential backoff
                    logger.info(f"Reconnecting in {delay} seconds...")
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, self.max_reconnect_delay)

    async def send(self, message: str) -> None:
        """Send message (queues if not connected)"""
        if self.websocket and self.websocket.open:
            await self.websocket.send(message)
        else:
            raise ConnectionError("WebSocket not connected")

    async def send_json(self, data: dict) -> None:
        """Send JSON message"""
        await self.send(json.dumps(data))

    async def start(self) -> None:
        """Start client"""
        self.running = True
        await self.connect()

    async def stop(self) -> None:
        """Stop client"""
        self.running = False
        if self.websocket:
            await self.websocket.close()


# Example usage
async def handle_message(message: str):
    """Handle incoming message"""
    try:
        data = json.loads(message)
        print(f"Received: {data}")
    except json.JSONDecodeError:
        print(f"Received: {message}")


async def main():
    client = ReconnectingWebSocketClient(
        "ws://localhost:8765",
        on_message=handle_message
    )

    # Start client in background
    asyncio.create_task(client.start())

    # Send messages
    await asyncio.sleep(1)  # Wait for connection
    await client.send_json({"type": "ping"})
    await client.send_json({"type": "echo", "data": "Hello, Server!"})

    # Run for 60 seconds
    await asyncio.sleep(60)
    await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Server with Authentication

```python
#!/usr/bin/env python3
"""
WebSocket server with JWT authentication and rate limiting.
"""

import asyncio
import json
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
import websockets
from websockets.server import WebSocketServerProtocol
import jwt


@dataclass
class ClientState:
    """Track client state for rate limiting"""
    websocket: WebSocketServerProtocol
    user_id: Optional[str] = None
    authenticated: bool = False
    message_count: int = 0
    last_message_time: float = field(default_factory=time.time)


class AuthenticatedWebSocketServer:
    """WebSocket server with authentication and rate limiting"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        jwt_secret: str = "your-secret-key",
        max_messages_per_minute: int = 60
    ):
        self.host = host
        self.port = port
        self.jwt_secret = jwt_secret
        self.max_messages_per_minute = max_messages_per_minute
        self.clients: Dict[WebSocketServerProtocol, ClientState] = {}

    async def authenticate(self, websocket: WebSocketServerProtocol, token: str) -> bool:
        """Authenticate client using JWT token"""
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")

            if not user_id:
                return False

            # Update client state
            self.clients[websocket].user_id = user_id
            self.clients[websocket].authenticated = True
            return True

        except jwt.ExpiredSignatureError:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Token expired"
            }))
            return False
        except jwt.InvalidTokenError:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid token"
            }))
            return False

    async def check_rate_limit(self, websocket: WebSocketServerProtocol) -> bool:
        """Check if client exceeds rate limit"""
        client = self.clients[websocket]
        now = time.time()

        # Reset counter every minute
        if now - client.last_message_time > 60:
            client.message_count = 0
            client.last_message_time = now

        client.message_count += 1

        if client.message_count > self.max_messages_per_minute:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Rate limit exceeded"
            }))
            return False

        return True

    async def handler(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handle client connection"""
        # Create client state
        self.clients[websocket] = ClientState(websocket=websocket)

        try:
            # Wait for authentication (5 second timeout)
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)

            try:
                data = json.loads(auth_message)
                if data.get("type") != "auth":
                    await websocket.close(code=4000, reason="Authentication required")
                    return

                token = data.get("token")
                if not await self.authenticate(websocket, token):
                    await websocket.close(code=4001, reason="Authentication failed")
                    return

            except json.JSONDecodeError:
                await websocket.close(code=4002, reason="Invalid auth message")
                return

            # Send auth success
            await websocket.send(json.dumps({
                "type": "auth_success",
                "user_id": self.clients[websocket].user_id
            }))

            # Message loop
            async for message in websocket:
                # Check rate limit
                if not await self.check_rate_limit(websocket):
                    continue

                # Process message
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))

        except asyncio.TimeoutError:
            await websocket.close(code=4003, reason="Authentication timeout")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.pop(websocket, None)

    async def handle_message(self, websocket: WebSocketServerProtocol, data: dict) -> None:
        """Handle authenticated message"""
        msg_type = data.get("type")
        client = self.clients[websocket]

        if msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))
        elif msg_type == "echo":
            await websocket.send(json.dumps({
                "type": "echo",
                "user_id": client.user_id,
                "data": data.get("data")
            }))
        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {msg_type}"
            }))

    def run(self) -> None:
        """Start server"""
        async def serve():
            async with websockets.serve(self.handler, self.host, self.port):
                await asyncio.Future()

        asyncio.run(serve())


if __name__ == "__main__":
    # Generate test token
    test_token = jwt.encode({"user_id": "user123"}, "your-secret-key", algorithm="HS256")
    print(f"Test token: {test_token}")

    server = AuthenticatedWebSocketServer()
    server.run()
```

---

## 7. Node.js Implementation

### Using `ws` Library

**Installation**:
```bash
npm install ws
```

### Basic Server

```javascript
#!/usr/bin/env node
/**
 * Basic WebSocket server using ws library
 */

const WebSocket = require('ws');

class WebSocketServer {
    constructor(port = 8080) {
        this.port = port;
        this.wss = null;
        this.clients = new Set();
    }

    start() {
        this.wss = new WebSocket.Server({ port: this.port });

        this.wss.on('connection', (ws, req) => {
            console.log(`Client connected from ${req.socket.remoteAddress}`);
            this.handleConnection(ws);
        });

        this.wss.on('error', (error) => {
            console.error('Server error:', error);
        });

        console.log(`WebSocket server listening on port ${this.port}`);
    }

    handleConnection(ws) {
        // Add to clients
        this.clients.add(ws);

        // Setup heartbeat
        ws.isAlive = true;
        ws.on('pong', () => {
            ws.isAlive = true;
        });

        // Handle messages
        ws.on('message', async (data) => {
            try {
                const message = JSON.parse(data);
                await this.handleMessage(ws, message);
            } catch (error) {
                ws.send(JSON.stringify({
                    type: 'error',
                    message: 'Invalid JSON'
                }));
            }
        });

        // Handle close
        ws.on('close', (code, reason) => {
            console.log(`Client disconnected: ${code} - ${reason}`);
            this.clients.delete(ws);
        });

        // Handle errors
        ws.on('error', (error) => {
            console.error('Client error:', error);
            this.clients.delete(ws);
        });
    }

    async handleMessage(ws, data) {
        const { type } = data;

        switch (type) {
            case 'ping':
                ws.send(JSON.stringify({ type: 'pong' }));
                break;

            case 'broadcast':
                this.broadcast(JSON.stringify(data), ws);
                break;

            case 'echo':
                ws.send(JSON.stringify({
                    type: 'echo',
                    data: data.data
                }));
                break;

            default:
                ws.send(JSON.stringify({
                    type: 'error',
                    message: `Unknown message type: ${type}`
                }));
        }
    }

    broadcast(message, exclude = null) {
        this.clients.forEach((client) => {
            if (client !== exclude && client.readyState === WebSocket.OPEN) {
                client.send(message);
            }
        });
    }

    startHeartbeat() {
        // Check connection health every 30 seconds
        setInterval(() => {
            this.wss.clients.forEach((ws) => {
                if (ws.isAlive === false) {
                    console.log('Terminating dead connection');
                    return ws.terminate();
                }

                ws.isAlive = false;
                ws.ping();
            });
        }, 30000);
    }

    shutdown() {
        console.log('Shutting down server...');

        // Close all client connections
        this.clients.forEach((client) => {
            client.close(1001, 'Server shutting down');
        });

        // Close server
        this.wss.close(() => {
            console.log('Server closed');
            process.exit(0);
        });
    }
}

// Start server
const server = new WebSocketServer(8080);
server.start();
server.startHeartbeat();

// Graceful shutdown
process.on('SIGTERM', () => server.shutdown());
process.on('SIGINT', () => server.shutdown());
```

### Cluster Mode (Multi-Process)

```javascript
#!/usr/bin/env node
/**
 * WebSocket server with cluster mode for multi-core scaling
 */

const cluster = require('cluster');
const os = require('os');
const WebSocket = require('ws');

if (cluster.isMaster) {
    // Master process
    const numCPUs = os.cpus().length;
    console.log(`Master process started. Forking ${numCPUs} workers...`);

    for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
    }

    cluster.on('exit', (worker, code, signal) => {
        console.log(`Worker ${worker.process.pid} died. Forking new worker...`);
        cluster.fork();
    });

} else {
    // Worker process
    const wss = new WebSocket.Server({ port: 8080 });

    wss.on('connection', (ws) => {
        console.log(`[Worker ${process.pid}] Client connected`);

        ws.on('message', (data) => {
            try {
                const message = JSON.parse(data);

                // Echo back
                ws.send(JSON.stringify({
                    type: 'echo',
                    worker: process.pid,
                    data: message
                }));
            } catch (error) {
                ws.send(JSON.stringify({
                    type: 'error',
                    message: 'Invalid JSON'
                }));
            }
        });

        ws.on('close', () => {
            console.log(`[Worker ${process.pid}] Client disconnected`);
        });
    });

    console.log(`Worker ${process.pid} started`);
}
```

---

## 8. Go Implementation

### Using `gorilla/websocket`

```go
package main

import (
    "encoding/json"
    "log"
    "net/http"
    "sync"
    "time"

    "github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
    ReadBufferSize:  1024,
    WriteBufferSize: 1024,
    CheckOrigin: func(r *http.Request) bool {
        // Validate origin
        return true  // Allow all origins (adjust for production)
    },
}

type Client struct {
    conn *websocket.Conn
    send chan []byte
}

type Hub struct {
    clients    map[*Client]bool
    broadcast  chan []byte
    register   chan *Client
    unregister chan *Client
    mu         sync.RWMutex
}

func newHub() *Hub {
    return &Hub{
        broadcast:  make(chan []byte, 256),
        register:   make(chan *Client),
        unregister: make(chan *Client),
        clients:    make(map[*Client]bool),
    }
}

func (h *Hub) run() {
    for {
        select {
        case client := <-h.register:
            h.mu.Lock()
            h.clients[client] = true
            h.mu.Unlock()
            log.Printf("Client registered. Total: %d", len(h.clients))

        case client := <-h.unregister:
            h.mu.Lock()
            if _, ok := h.clients[client]; ok {
                delete(h.clients, client)
                close(client.send)
            }
            h.mu.Unlock()
            log.Printf("Client unregistered. Total: %d", len(h.clients))

        case message := <-h.broadcast:
            h.mu.RLock()
            for client := range h.clients {
                select {
                case client.send <- message:
                default:
                    close(client.send)
                    delete(h.clients, client)
                }
            }
            h.mu.RUnlock()
        }
    }
}

func (c *Client) readPump(hub *Hub) {
    defer func() {
        hub.unregister <- c
        c.conn.Close()
    }()

    c.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
    c.conn.SetPongHandler(func(string) error {
        c.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
        return nil
    })

    for {
        _, message, err := c.conn.ReadMessage()
        if err != nil {
            if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
                log.Printf("error: %v", err)
            }
            break
        }

        // Parse message
        var msg map[string]interface{}
        if err := json.Unmarshal(message, &msg); err != nil {
            continue
        }

        // Handle different message types
        msgType, _ := msg["type"].(string)
        switch msgType {
        case "broadcast":
            hub.broadcast <- message
        case "ping":
            response, _ := json.Marshal(map[string]string{"type": "pong"})
            c.send <- response
        }
    }
}

func (c *Client) writePump() {
    ticker := time.NewTicker(54 * time.Second)
    defer func() {
        ticker.Stop()
        c.conn.Close()
    }()

    for {
        select {
        case message, ok := <-c.send:
            c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
            if !ok {
                c.conn.WriteMessage(websocket.CloseMessage, []byte{})
                return
            }

            w, err := c.conn.NextWriter(websocket.TextMessage)
            if err != nil {
                return
            }
            w.Write(message)

            if err := w.Close(); err != nil {
                return
            }

        case <-ticker.C:
            c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
            if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
                return
            }
        }
    }
}

func serveWs(hub *Hub, w http.ResponseWriter, r *http.Request) {
    conn, err := upgrader.Upgrade(w, r, nil)
    if err != nil {
        log.Println(err)
        return
    }

    client := &Client{conn: conn, send: make(chan []byte, 256)}
    hub.register <- client

    go client.writePump()
    go client.readPump(hub)
}

func main() {
    hub := newHub()
    go hub.run()

    http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
        serveWs(hub, w, r)
    })

    log.Println("WebSocket server starting on :8080")
    if err := http.ListenAndServe(":8080", nil); err != nil {
        log.Fatal(err)
    }
}
```

---

## 9. Java Implementation

### Using Spring WebSocket

```java
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArraySet;

@SpringBootApplication
public class WebSocketApplication {
    public static void main(String[] args) {
        SpringApplication.run(WebSocketApplication.class, args);
    }
}

@Configuration
@EnableWebSocket
class WebSocketConfig implements WebSocketConfigurer {
    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(new WebSocketHandler(), "/ws")
                .setAllowedOrigins("*");
    }
}

class WebSocketHandler extends TextWebSocketHandler {
    private final CopyOnWriteArraySet<WebSocketSession> sessions = new CopyOnWriteArraySet<>();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        sessions.add(session);
        System.out.println("Client connected: " + session.getId());
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        System.out.println("Received: " + payload);

        // Echo back to sender
        session.sendMessage(new TextMessage("Echo: " + payload));

        // Broadcast to all clients
        broadcast(message, session);
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        sessions.remove(session);
        System.out.println("Client disconnected: " + session.getId());
    }

    private void broadcast(TextMessage message, WebSocketSession exclude) {
        sessions.forEach(session -> {
            if (session.isOpen() && !session.equals(exclude)) {
                try {
                    session.sendMessage(message);
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
        });
    }
}
```

---

## 10. Client Implementation Patterns

### Browser JavaScript

**Basic connection**:
```javascript
const ws = new WebSocket('wss://example.com/ws');

ws.onopen = (event) => {
    console.log('Connected to WebSocket');
    ws.send('Hello, Server!');
};

ws.onmessage = (event) => {
    console.log('Message from server:', event.data);

    // Parse JSON
    try {
        const data = JSON.parse(event.data);
        console.log('Type:', data.type);
    } catch (e) {
        console.error('Invalid JSON:', event.data);
    }
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
    console.log(`Connection closed: ${event.code} - ${event.reason}`);
};

// Send message
ws.send(JSON.stringify({ type: 'ping' }));
```

### React Hook

```javascript
import { useEffect, useState, useRef, useCallback } from 'react';

/**
 * useWebSocket hook with automatic reconnection
 */
function useWebSocket(url, options = {}) {
    const {
        reconnectInterval = 5000,
        maxReconnectAttempts = 10,
        onOpen = () => {},
        onClose = () => {},
        onMessage = () => {},
        onError = () => {}
    } = options;

    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState(null);
    const [reconnectCount, setReconnectCount] = useState(0);

    const ws = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    const connect = useCallback(() => {
        try {
            ws.current = new WebSocket(url);

            ws.current.onopen = (event) => {
                console.log('WebSocket connected');
                setIsConnected(true);
                setReconnectCount(0);
                onOpen(event);
            };

            ws.current.onmessage = (event) => {
                const message = event.data;
                setLastMessage(message);
                onMessage(message);
            };

            ws.current.onerror = (error) => {
                console.error('WebSocket error:', error);
                onError(error);
            };

            ws.current.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                setIsConnected(false);
                onClose(event);

                // Attempt reconnection
                if (reconnectCount < maxReconnectAttempts) {
                    console.log(`Reconnecting in ${reconnectInterval}ms...`);
                    reconnectTimeoutRef.current = setTimeout(() => {
                        setReconnectCount(prev => prev + 1);
                        connect();
                    }, reconnectInterval);
                } else {
                    console.error('Max reconnection attempts reached');
                }
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
        }
    }, [url, reconnectInterval, maxReconnectAttempts, reconnectCount]);

    const sendMessage = useCallback((message) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(message);
        } else {
            console.warn('WebSocket not connected');
        }
    }, []);

    const sendJSON = useCallback((data) => {
        sendMessage(JSON.stringify(data));
    }, [sendMessage]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (ws.current) {
            ws.current.close(1000, 'Client disconnect');
        }
    }, []);

    useEffect(() => {
        connect();
        return () => disconnect();
    }, []);

    return {
        isConnected,
        lastMessage,
        sendMessage,
        sendJSON,
        disconnect,
        reconnect: connect
    };
}

// Usage in component
function ChatComponent() {
    const {
        isConnected,
        lastMessage,
        sendJSON
    } = useWebSocket('wss://example.com/ws', {
        onMessage: (message) => {
            console.log('Received:', message);
        },
        onOpen: () => {
            console.log('Connection established');
        },
        onClose: () => {
            console.log('Connection closed');
        }
    });

    const handleSendMessage = () => {
        sendJSON({ type: 'chat', text: 'Hello!' });
    };

    return (
        <div>
            <div>Status: {isConnected ? 'Connected' : 'Disconnected'}</div>
            <button onClick={handleSendMessage} disabled={!isConnected}>
                Send Message
            </button>
            <div>Last message: {lastMessage}</div>
        </div>
    );
}
```

---

## 11. Load Balancing

### Sticky Sessions

WebSocket connections MUST use sticky sessions (session affinity) because:
- Connection state stored on specific backend server
- Cannot switch servers mid-connection
- All frames from same client must route to same backend

**Methods**:
1. **IP-based**: Route by client IP (simple but can imbalance)
2. **Cookie-based**: Set cookie during HTTP upgrade
3. **Connection ID**: Use WebSocket key for consistent hashing

### nginx Configuration

```nginx
# Upstream backend servers
upstream websocket_backend {
    # IP hash for sticky sessions
    ip_hash;

    server backend1.example.com:8080 max_fails=3 fail_timeout=30s;
    server backend2.example.com:8080 max_fails=3 fail_timeout=30s;
    server backend3.example.com:8080 max_fails=3 fail_timeout=30s;

    # Health check
    # Requires nginx Plus or custom module
}

# HTTP server
server {
    listen 80;
    server_name ws.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name ws.example.com;

    # SSL configuration
    ssl_certificate /etc/ssl/certs/ws.example.com.crt;
    ssl_certificate_key /etc/ssl/private/ws.example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # WebSocket endpoint
    location /ws {
        # Proxy to backend
        proxy_pass http://websocket_backend;

        # Required WebSocket headers
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts (increase for long-lived connections)
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;

        # Disable buffering (critical for WebSocket)
        proxy_buffering off;
        proxy_cache off;

        # Disable request/response buffering
        proxy_request_buffering off;
        proxy_http_version 1.1;
    }

    # Health check endpoint (regular HTTP)
    location /health {
        proxy_pass http://websocket_backend/health;
        proxy_http_version 1.1;
    }
}

# Connection limits
limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;
limit_req_zone $binary_remote_addr zone=req_limit_per_ip:10m rate=10r/s;

server {
    # Apply limits
    limit_conn conn_limit_per_ip 10;
    limit_req zone=req_limit_per_ip burst=20;
}
```

### HAProxy Configuration

```haproxy
# Global settings
global
    log /dev/log local0
    maxconn 50000
    tune.ssl.default-dh-param 2048

# Defaults
defaults
    log global
    mode http
    option httplog
    option dontlognull
    timeout connect 5s
    timeout client 7d
    timeout server 7d
    timeout tunnel 3600s  # Important for WebSocket

# Frontend (client-facing)
frontend websocket_front
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/ws.example.com.pem

    # Redirect HTTP to HTTPS
    redirect scheme https if !{ ssl_fc }

    # ACL for WebSocket upgrade
    acl is_websocket hdr(Upgrade) -i websocket
    acl is_websocket_path path_beg /ws

    # Use WebSocket backend
    use_backend websocket_back if is_websocket is_websocket_path

    # Default backend for non-WebSocket
    default_backend web_back

# Backend (servers)
backend websocket_back
    # Sticky session using source IP
    balance source
    hash-type consistent

    # Health check
    option httpchk GET /health HTTP/1.1\r\nHost:\ localhost
    http-check expect status 200

    # Server timeouts
    timeout server 7d
    timeout tunnel 7d

    # Backend servers
    server ws1 backend1.example.com:8080 check inter 5s rise 2 fall 3
    server ws2 backend2.example.com:8080 check inter 5s rise 2 fall 3
    server ws3 backend3.example.com:8080 check inter 5s rise 2 fall 3

backend web_back
    balance roundrobin
    server web1 backend1.example.com:8081 check
    server web2 backend2.example.com:8081 check
```

### AWS Application Load Balancer

```yaml
# ALB configuration (Terraform example)
resource "aws_lb" "websocket" {
  name               = "websocket-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = var.public_subnets

  enable_http2 = true
}

resource "aws_lb_target_group" "websocket" {
  name     = "websocket-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  # Health check
  health_check {
    enabled             = true
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  # Sticky sessions (required for WebSocket)
  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400  # 24 hours
    enabled         = true
  }

  # Connection draining
  deregistration_delay = 30
}

resource "aws_lb_listener" "websocket_https" {
  load_balancer_arn = aws_lb.websocket.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.websocket.arn
  }
}

resource "aws_lb_target_group_attachment" "websocket" {
  count            = length(var.backend_instances)
  target_group_arn = aws_lb_target_group.websocket.arn
  target_id        = var.backend_instances[count.index]
  port             = 8080
}
```

---

## 12. Horizontal Scaling

### Problem

Load-balanced WebSocket servers need to communicate to broadcast messages across all connections.

**Example scenario**:
```
User A → Backend Server 1
User B → Backend Server 2
User C → Backend Server 3

User A sends message → Only Server 1 receives it
But Users B and C (on different servers) need to receive it too
```

### Solution: Redis Pub/Sub

**Architecture**:
```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Server 1 │     │ Server 2 │     │ Server 3 │
│          │     │          │     │          │
│ Client A │     │ Client B │     │ Client C │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │
     │ publish        │ subscribe      │ subscribe
     └──────┬─────────┴────────────────┴────────┐
            │                                     │
            ▼                                     │
       ┌────────────┐                           │
       │   Redis    │                           │
       │  Pub/Sub   │                           │
       └────────────┘                           │
            │                                     │
            │ broadcast to all subscribers       │
            └─────────────────────────────────────┘
```

**Python implementation**:
```python
import asyncio
import json
import redis.asyncio as redis
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol


class ScalableWebSocketServer:
    """WebSocket server with Redis pub/sub for horizontal scaling"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        redis_host: str = "localhost",
        redis_port: int = 6379
    ):
        self.host = host
        self.port = port
        self.redis_host = redis_host
        self.redis_port = redis_port

        self.clients: Set[WebSocketServerProtocol] = set()
        self.redis_client = None
        self.pubsub = None

    async def connect_redis(self) -> None:
        """Connect to Redis"""
        self.redis_client = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()
        await self.pubsub.subscribe('websocket_broadcast')

    async def redis_listener(self) -> None:
        """Listen for Redis pub/sub messages"""
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                data = message['data']
                await self.local_broadcast(data)

    async def local_broadcast(self, message: str) -> None:
        """Broadcast to local clients only"""
        if not self.clients:
            return

        tasks = [
            client.send(message)
            for client in self.clients
            if client.open
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def global_broadcast(self, message: str) -> None:
        """Broadcast to all servers via Redis"""
        await self.redis_client.publish('websocket_broadcast', message)

    async def handler(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handle client connection"""
        self.clients.add(websocket)

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "broadcast":
                        # Broadcast globally via Redis
                        await self.global_broadcast(message)
                    elif msg_type == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": f"Unknown type: {msg_type}"
                        }))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)

    async def serve(self) -> None:
        """Start WebSocket server"""
        # Connect to Redis
        await self.connect_redis()

        # Start Redis listener
        asyncio.create_task(self.redis_listener())

        # Start WebSocket server
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()  # Run forever

    def run(self) -> None:
        """Run server"""
        asyncio.run(self.serve())


if __name__ == "__main__":
    server = ScalableWebSocketServer()
    server.run()
```

### Alternative: Message Queue (RabbitMQ, Kafka)

For more complex routing, use message queues:

**RabbitMQ**:
```python
import pika
import json
from typing import Set
import websockets

class RabbitMQWebSocketServer:
    def __init__(self, rabbitmq_host: str = "localhost"):
        # RabbitMQ connection
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbitmq_host)
        )
        self.channel = self.connection.channel()

        # Declare exchange
        self.channel.exchange_declare(
            exchange='websocket_broadcast',
            exchange_type='fanout'
        )

        # Create exclusive queue for this server
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.queue_name = result.method.queue

        # Bind queue to exchange
        self.channel.queue_bind(
            exchange='websocket_broadcast',
            queue=self.queue_name
        )

        self.clients: Set[websockets.WebSocketServerProtocol] = set()

    def global_broadcast(self, message: str) -> None:
        """Publish to RabbitMQ"""
        self.channel.basic_publish(
            exchange='websocket_broadcast',
            routing_key='',
            body=message
        )

    async def local_broadcast(self, message: str) -> None:
        """Send to local clients"""
        tasks = [client.send(message) for client in self.clients if client.open]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def rabbitmq_consumer(self) -> None:
        """Consume messages from RabbitMQ"""
        def callback(ch, method, properties, body):
            message = body.decode('utf-8')
            asyncio.create_task(self.local_broadcast(message))

        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=callback,
            auto_ack=True
        )

        self.channel.start_consuming()
```

---

## 13. Authentication and Authorization

### Token-Based Authentication

**Method 1: Token in URL query parameter**:

```javascript
// Client
const token = localStorage.getItem('auth_token');
const ws = new WebSocket(`wss://api.example.com/ws?token=${token}`);
```

```python
# Server
from urllib.parse import urlparse, parse_qs
import jwt

async def handler(websocket, path):
    # Extract token from URL
    query = parse_qs(urlparse(path).query)
    token = query.get('token', [None])[0]

    # Verify token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload['user_id']
    except jwt.ExpiredSignatureError:
        await websocket.close(code=4001, reason="Token expired")
        return
    except jwt.InvalidTokenError:
        await websocket.close(code=4002, reason="Invalid token")
        return

    # Continue with authenticated connection
    print(f"User {user_id} authenticated")
```

**Pros**:
- Simple implementation
- Works with all WebSocket clients

**Cons**:
- Token visible in logs, browser history
- Cannot update token without reconnecting

**Method 2: Auth message after connection**:

```javascript
// Client
const ws = new WebSocket('wss://api.example.com/ws');

ws.onopen = () => {
    const token = localStorage.getItem('auth_token');
    ws.send(JSON.stringify({ type: 'auth', token: token }));
};
```

```python
# Server
async def handler(websocket, path):
    # Wait for auth message (5 second timeout)
    try:
        auth_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        data = json.loads(auth_msg)

        if data.get('type') != 'auth':
            await websocket.close(code=4000, reason="Auth required")
            return

        token = data.get('token')
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload['user_id']

        # Send auth success
        await websocket.send(json.dumps({
            "type": "auth_success",
            "user_id": user_id
        }))

    except asyncio.TimeoutError:
        await websocket.close(code=4003, reason="Auth timeout")
        return
    except (json.JSONDecodeError, jwt.InvalidTokenError):
        await websocket.close(code=4004, reason="Auth failed")
        return

    # Continue with authenticated session
```

**Pros**:
- Token not visible in URLs
- Can update token mid-session

**Cons**:
- More complex implementation
- Requires timeout handling

**Method 3: HTTP cookie**:

```javascript
// Client (cookie set by HTTP login endpoint)
const ws = new WebSocket('wss://api.example.com/ws');
// Browser automatically sends cookies
```

```python
# Server
async def handler(websocket, path):
    # Extract cookie from request headers
    cookie_header = websocket.request_headers.get('Cookie', '')
    cookies = parse_cookie(cookie_header)
    session_id = cookies.get('session_id')

    # Verify session
    user_id = await verify_session(session_id)
    if not user_id:
        await websocket.close(code=4005, reason="Invalid session")
        return

    # Continue
```

**Pros**:
- Secure (httpOnly, secure flags)
- Automatically handled by browser

**Cons**:
- Only works in browser
- CSRF considerations

### Role-Based Access Control (RBAC)

```python
from enum import Enum
from typing import Set

class Role(Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    BAN_USER = "ban_user"

ROLE_PERMISSIONS = {
    Role.USER: {Permission.READ, Permission.WRITE},
    Role.MODERATOR: {Permission.READ, Permission.WRITE, Permission.DELETE},
    Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.BAN_USER}
}

class AuthorizedWebSocketHandler:
    def __init__(self):
        self.user_roles = {}  # websocket -> role

    async def handler(self, websocket, path):
        # Authenticate and get role
        role = await self.authenticate(websocket)
        self.user_roles[websocket] = role

        try:
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type")

                # Check permissions
                if msg_type == "delete_message":
                    if not self.has_permission(websocket, Permission.DELETE):
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Insufficient permissions"
                        }))
                        continue

                    # Process delete
                    await self.delete_message(data.get("message_id"))

                elif msg_type == "ban_user":
                    if not self.has_permission(websocket, Permission.BAN_USER):
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Admin only"
                        }))
                        continue

                    # Process ban
                    await self.ban_user(data.get("user_id"))
        finally:
            self.user_roles.pop(websocket, None)

    def has_permission(self, websocket, permission: Permission) -> bool:
        """Check if user has permission"""
        role = self.user_roles.get(websocket)
        if not role:
            return False

        return permission in ROLE_PERMISSIONS.get(role, set())
```

---

## 14. Security Best Practices

### Use TLS/SSL (wss://)

**Always use `wss://` in production**:
- Encrypts all data in transit
- Prevents man-in-the-middle attacks
- Required for HTTPS pages (mixed content policy)

```python
import ssl

# Server
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('/path/to/cert.pem', '/path/to/key.pem')

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765, ssl=ssl_context):
        await asyncio.Future()
```

### Origin Validation

**Prevent cross-site WebSocket hijacking**:

```python
async def handler(websocket, path):
    # Check Origin header
    origin = websocket.request_headers.get('Origin')
    allowed_origins = [
        'https://example.com',
        'https://app.example.com',
        'https://www.example.com'
    ]

    if origin not in allowed_origins:
        await websocket.close(code=4006, reason="Invalid origin")
        return

    # Continue
```

### Rate Limiting

**Prevent message flooding**:

```python
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_per_minute: int = 60):
        self.max_per_minute = max_per_minute
        self.client_counts = defaultdict(lambda: {'count': 0, 'reset_time': time.time() + 60})

    def is_allowed(self, client_id: str) -> bool:
        """Check if client is within rate limit"""
        now = time.time()
        client_data = self.client_counts[client_id]

        # Reset counter if minute elapsed
        if now > client_data['reset_time']:
            client_data['count'] = 0
            client_data['reset_time'] = now + 60

        client_data['count'] += 1

        return client_data['count'] <= self.max_per_minute

# Usage
rate_limiter = RateLimiter(max_per_minute=60)

async def handler(websocket, path):
    client_id = websocket.remote_address[0]

    async for message in websocket:
        if not rate_limiter.is_allowed(client_id):
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Rate limit exceeded"
            }))
            continue

        # Process message
```

### Message Size Limits

**Prevent memory exhaustion**:

```python
# Set max message size
async def main():
    async with websockets.serve(
        handler,
        "0.0.0.0",
        8765,
        max_size=1 * 1024 * 1024,  # 1 MB max
        max_queue=32               # Max queued messages
    ):
        await asyncio.Future()
```

### Input Validation

**Validate all incoming data**:

```python
from pydantic import BaseModel, validator, ValidationError

class ChatMessage(BaseModel):
    type: str
    text: str

    @validator('text')
    def text_length(cls, v):
        if len(v) > 1000:
            raise ValueError('Message too long')
        return v

    @validator('type')
    def valid_type(cls, v):
        if v not in ['chat', 'ping', 'broadcast']:
            raise ValueError('Invalid message type')
        return v

async def handler(websocket, path):
    async for message in websocket:
        try:
            data = json.loads(message)
            validated = ChatMessage(**data)

            # Process validated message
            await process_message(validated)

        except ValidationError as e:
            await websocket.send(json.dumps({
                "type": "error",
                "message": str(e)
            }))
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid JSON"
            }))
```

### Connection Limits

**Prevent resource exhaustion**:

```python
class ConnectionLimiter:
    def __init__(self, max_connections: int = 10000, max_per_ip: int = 10):
        self.max_connections = max_connections
        self.max_per_ip = max_per_ip
        self.connections = set()
        self.ip_counts = defaultdict(int)

    def can_connect(self, websocket) -> bool:
        """Check if new connection allowed"""
        if len(self.connections) >= self.max_connections:
            return False

        client_ip = websocket.remote_address[0]
        if self.ip_counts[client_ip] >= self.max_per_ip:
            return False

        return True

    def add_connection(self, websocket):
        """Register new connection"""
        self.connections.add(websocket)
        client_ip = websocket.remote_address[0]
        self.ip_counts[client_ip] += 1

    def remove_connection(self, websocket):
        """Unregister connection"""
        self.connections.discard(websocket)
        client_ip = websocket.remote_address[0]
        self.ip_counts[client_ip] -= 1

# Usage
limiter = ConnectionLimiter(max_connections=10000, max_per_ip=10)

async def handler(websocket, path):
    if not limiter.can_connect(websocket):
        await websocket.close(code=4007, reason="Connection limit reached")
        return

    limiter.add_connection(websocket)
    try:
        async for message in websocket:
            # Process
            pass
    finally:
        limiter.remove_connection(websocket)
```

---

## 15. Heartbeat and Health Monitoring

### Protocol-Level Ping/Pong

**Automatic with `websockets` library**:

```python
async def main():
    async with websockets.serve(
        handler,
        "0.0.0.0",
        8765,
        ping_interval=30,  # Send ping every 30 seconds
        ping_timeout=10    # Close if no pong within 10 seconds
    ):
        await asyncio.Future()
```

**Manual ping/pong**:

```python
async def heartbeat(websocket):
    """Send periodic ping"""
    while True:
        try:
            pong_waiter = await websocket.ping()
            await asyncio.wait_for(pong_waiter, timeout=10)
            print("Pong received")
        except asyncio.TimeoutError:
            print("Ping timeout - closing connection")
            await websocket.close()
            break
        await asyncio.sleep(30)

async def handler(websocket, path):
    # Start heartbeat in background
    heartbeat_task = asyncio.create_task(heartbeat(websocket))

    try:
        async for message in websocket:
            # Process
            pass
    finally:
        heartbeat_task.cancel()
```

### Application-Level Heartbeat

**For debugging and latency measurement**:

```python
import time

async def app_heartbeat(websocket):
    """Application-level heartbeat"""
    while True:
        start = time.time()

        # Send ping
        await websocket.send(json.dumps({
            "type": "ping",
            "timestamp": start
        }))

        # Wait for pong
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("type") == "pong":
                latency = time.time() - start
                print(f"Round-trip latency: {latency*1000:.2f}ms")
        except asyncio.TimeoutError:
            print("Application ping timeout")
            break

        await asyncio.sleep(15)
```

### Health Check Endpoint

**HTTP health check for load balancers**:

```python
from aiohttp import web

class WebSocketServerWithHealth:
    def __init__(self):
        self.clients = set()
        self.healthy = True

    async def health_handler(self, request):
        """HTTP health check endpoint"""
        if not self.healthy:
            return web.Response(status=503, text="Unhealthy")

        return web.json_response({
            "status": "healthy",
            "connections": len(self.clients),
            "timestamp": time.time()
        })

    async def start(self):
        """Start both WebSocket and HTTP servers"""
        # HTTP server for health checks
        app = web.Application()
        app.router.add_get('/health', self.health_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

        # WebSocket server
        async with websockets.serve(self.ws_handler, "0.0.0.0", 8765):
            await asyncio.Future()
```

---

## 16. Error Handling

### Common Error Scenarios

**Connection errors**:
```python
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedOK,
    ConnectionClosedError,
    InvalidHandshake,
    InvalidMessage,
    PayloadTooBig,
    WebSocketProtocolError
)

async def handler(websocket, path):
    try:
        async for message in websocket:
            await process(message)

    except ConnectionClosedOK:
        # Normal close (1000, 1001)
        log.info("Connection closed normally")

    except ConnectionClosedError as e:
        # Abnormal close
        log.warning(f"Connection error: {e.code} - {e.reason}")

    except PayloadTooBig as e:
        # Message exceeds max_size
        log.warning(f"Payload too big: {e}")
        await websocket.close(code=1009, reason="Message too big")

    except InvalidMessage as e:
        # Protocol violation
        log.error(f"Protocol error: {e}")
        await websocket.close(code=1002, reason="Protocol error")

    except WebSocketProtocolError as e:
        # General protocol error
        log.error(f"WebSocket protocol error: {e}")

    except Exception as e:
        # Application error
        log.error(f"Unexpected error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass
```

### Retry Logic (Client)

```python
class RetryWebSocketClient:
    def __init__(self, uri, max_retries=5, base_delay=1):
        self.uri = uri
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def connect_with_retry(self):
        """Connect with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                websocket = await websockets.connect(self.uri)
                print(f"Connected on attempt {attempt + 1}")
                return websocket

            except (OSError, websockets.exceptions.WebSocketException) as e:
                if attempt == self.max_retries - 1:
                    raise

                delay = self.base_delay * (2 ** attempt)
                print(f"Connection failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
```

### Circuit Breaker Pattern

```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures detected, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def record_success(self):
        """Record successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0

    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def can_attempt(self) -> bool:
        """Check if operation can be attempted"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False

        # HALF_OPEN: allow attempt
        return True

# Usage
circuit_breaker = CircuitBreaker()

async def send_with_circuit_breaker(websocket, message):
    """Send message with circuit breaker protection"""
    if not circuit_breaker.can_attempt():
        raise Exception("Circuit breaker OPEN")

    try:
        await websocket.send(message)
        circuit_breaker.record_success()
    except Exception as e:
        circuit_breaker.record_failure()
        raise
```

---

## 17. Performance Optimization

### Connection Pooling (Client)

```python
import asyncio
from typing import List
import websockets

class WebSocketPool:
    """Connection pool for WebSocket clients"""

    def __init__(self, uri: str, pool_size: int = 10):
        self.uri = uri
        self.pool_size = pool_size
        self.pool: List[websockets.WebSocketClientProtocol] = []
        self.semaphore = asyncio.Semaphore(pool_size)

    async def init_pool(self):
        """Initialize connection pool"""
        tasks = [websockets.connect(self.uri) for _ in range(self.pool_size)]
        self.pool = await asyncio.gather(*tasks)

    async def get_connection(self):
        """Get connection from pool"""
        await self.semaphore.acquire()
        return self.pool.pop() if self.pool else await websockets.connect(self.uri)

    async def return_connection(self, conn):
        """Return connection to pool"""
        if conn.open:
            self.pool.append(conn)
        self.semaphore.release()

    async def send(self, message: str):
        """Send message using pooled connection"""
        conn = await self.get_connection()
        try:
            await conn.send(message)
        finally:
            await self.return_connection(conn)
```

### Compression (permessage-deflate)

```python
# Server
async def main():
    async with websockets.serve(
        handler,
        "0.0.0.0",
        8765,
        compression="deflate"  # Enable compression
    ):
        await asyncio.Future()

# Client
async def client():
    async with websockets.connect("ws://localhost:8765", compression="deflate"):
        # Compressed communication
        pass
```

**When to use compression**:
- ✅ Large text messages (JSON, XML)
- ✅ Bandwidth-constrained connections
- ❌ Binary data (already compressed)
- ❌ CPU-constrained servers
- ❌ Very small messages (overhead > savings)

### Batching

**Reduce frame overhead by batching messages**:

```python
import asyncio
from typing import List

class MessageBatcher:
    """Batch multiple messages into single frame"""

    def __init__(self, max_batch_size: int = 100, max_wait_ms: int = 50):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms / 1000
        self.buffer: List[dict] = []
        self.last_flush = time.time()

    async def add(self, message: dict) -> bool:
        """Add message to batch. Returns True if should flush."""
        self.buffer.append(message)

        should_flush = (
            len(self.buffer) >= self.max_batch_size or
            time.time() - self.last_flush >= self.max_wait_ms
        )

        return should_flush

    def flush(self) -> str:
        """Get batched messages and clear buffer"""
        if not self.buffer:
            return None

        batch = {
            "type": "batch",
            "messages": self.buffer
        }
        self.buffer = []
        self.last_flush = time.time()

        return json.dumps(batch)

# Usage
async def send_with_batching(websocket, messages):
    """Send messages in batches"""
    batcher = MessageBatcher()

    for message in messages:
        should_flush = await batcher.add(message)

        if should_flush:
            batch = batcher.flush()
            if batch:
                await websocket.send(batch)

    # Flush remaining
    batch = batcher.flush()
    if batch:
        await websocket.send(batch)
```

### Binary Protocols

**Use binary format for efficiency**:

```python
import struct
import msgpack

# MessagePack (efficient JSON alternative)
async def send_msgpack(websocket, data: dict):
    """Send message using MessagePack"""
    packed = msgpack.packb(data)
    await websocket.send(packed)

async def receive_msgpack(websocket):
    """Receive MessagePack message"""
    data = await websocket.recv()
    return msgpack.unpackb(data)

# Protocol Buffers
from google.protobuf import message

async def send_protobuf(websocket, proto_message):
    """Send Protocol Buffer message"""
    serialized = proto_message.SerializeToString()
    await websocket.send(serialized)

async def receive_protobuf(websocket, MessageClass):
    """Receive Protocol Buffer message"""
    data = await websocket.recv()
    message = MessageClass()
    message.ParseFromString(data)
    return message
```

---

## 18. Testing and Debugging

### Testing Tools

**wscat** (CLI client):
```bash
# Install
npm install -g wscat

# Connect
wscat -c ws://localhost:8080

# Connect with header
wscat -c ws://localhost:8080 -H "Authorization: Bearer token"

# Send message
> {"type": "ping"}

# Close
> ^C
```

**websocat** (advanced CLI):
```bash
# Install
brew install websocat  # macOS
apt install websocat   # Linux

# Connect
websocat ws://localhost:8080

# Connect with auto-reconnect
websocat --reconnect ws://localhost:8080

# Pipe data
echo '{"type":"ping"}' | websocat ws://localhost:8080

# Listen mode (WebSocket server)
websocat -s 8080
```

**Browser DevTools**:
```javascript
// Console
const ws = new WebSocket('wss://example.com/ws');
ws.onmessage = (e) => console.log('Received:', e.data);
ws.send('Hello');

// Network tab: Filter by "WS" to see WebSocket connections
// - View frames sent/received
// - Inspect frame data
// - See close codes
```

### Unit Testing

```python
import pytest
import websockets
import asyncio

@pytest.mark.asyncio
async def test_websocket_echo():
    """Test echo server"""
    async with websockets.serve(echo_handler, "localhost", 0) as server:
        port = server.sockets[0].getsockname()[1]
        uri = f"ws://localhost:{port}"

        async with websockets.connect(uri) as websocket:
            # Send message
            await websocket.send("Hello")

            # Receive echo
            response = await websocket.recv()
            assert response == "Hello"

@pytest.mark.asyncio
async def test_websocket_broadcast():
    """Test broadcast to multiple clients"""
    async with websockets.serve(broadcast_handler, "localhost", 0) as server:
        port = server.sockets[0].getsockname()[1]
        uri = f"ws://localhost:{port}"

        # Connect two clients
        async with websockets.connect(uri) as ws1:
            async with websockets.connect(uri) as ws2:
                # Send from client 1
                await ws1.send(json.dumps({"type": "broadcast", "data": "test"}))

                # Receive on client 2
                response = await ws2.recv()
                data = json.loads(response)
                assert data["data"] == "test"
```

### Load Testing

```python
import asyncio
import time
import websockets
from statistics import mean, median, stdev

async def load_test(uri: str, num_clients: int, duration: int):
    """Load test WebSocket server"""
    results = {
        "connections": 0,
        "messages_sent": 0,
        "messages_received": 0,
        "latencies": [],
        "errors": 0
    }

    async def client_worker():
        """Single client worker"""
        try:
            async with websockets.connect(uri) as websocket:
                results["connections"] += 1

                start_time = time.time()
                while time.time() - start_time < duration:
                    # Send ping
                    send_time = time.time()
                    await websocket.send(json.dumps({"type": "ping"}))
                    results["messages_sent"] += 1

                    # Wait for pong
                    response = await websocket.recv()
                    recv_time = time.time()
                    results["messages_received"] += 1

                    # Record latency
                    latency = (recv_time - send_time) * 1000  # ms
                    results["latencies"].append(latency)

                    await asyncio.sleep(0.1)
        except Exception as e:
            results["errors"] += 1
            print(f"Client error: {e}")

    # Launch clients
    print(f"Starting {num_clients} clients...")
    tasks = [client_worker() for _ in range(num_clients)]
    await asyncio.gather(*tasks)

    # Print results
    print(f"\n=== Load Test Results ===")
    print(f"Successful connections: {results['connections']}/{num_clients}")
    print(f"Messages sent: {results['messages_sent']}")
    print(f"Messages received: {results['messages_received']}")
    print(f"Errors: {results['errors']}")

    if results["latencies"]:
        print(f"\nLatency Statistics (ms):")
        print(f"  Mean: {mean(results['latencies']):.2f}")
        print(f"  Median: {median(results['latencies']):.2f}")
        print(f"  Std Dev: {stdev(results['latencies']):.2f}")
        print(f"  Min: {min(results['latencies']):.2f}")
        print(f"  Max: {max(results['latencies']):.2f}")

# Run load test
asyncio.run(load_test("ws://localhost:8080", num_clients=100, duration=60))
```

---

## 19. Production Deployment

### Docker Deployment

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server.py .

# Expose port
EXPOSE 8765

# Run server
CMD ["python", "server.py"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  websocket:
    build: .
    ports:
      - "8765:8765"
    environment:
      - REDIS_HOST=redis
      - LOG_LEVEL=INFO
    depends_on:
      - redis
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
    depends_on:
      - websocket
    restart: unless-stopped

volumes:
  redis_data:
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: websocket-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: websocket
  template:
    metadata:
      labels:
        app: websocket
    spec:
      containers:
      - name: websocket
        image: myregistry/websocket:latest
        ports:
        - containerPort: 8765
        env:
        - name: REDIS_HOST
          value: redis-service
        resources:
          requests:
            memory: "256Mi"
            cpu: "500m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: websocket-service
spec:
  type: LoadBalancer
  sessionAffinity: ClientIP  # Sticky sessions
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800  # 3 hours
  selector:
    app: websocket
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8765
```

### Systemd Service

```ini
# /etc/systemd/system/websocket.service
[Unit]
Description=WebSocket Server
After=network.target redis.service

[Service]
Type=simple
User=websocket
WorkingDirectory=/opt/websocket
ExecStart=/usr/bin/python3 /opt/websocket/server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Environment
Environment="REDIS_HOST=localhost"
Environment="LOG_LEVEL=INFO"

# Resource limits
LimitNOFILE=65536
CPUQuota=100%
MemoryLimit=1G

[Install]
WantedBy=multi-user.target
```

---

## 20. Monitoring and Observability

### Metrics

**Prometheus metrics**:

```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Metrics
websocket_connections = Gauge(
    'websocket_connections_total',
    'Number of active WebSocket connections'
)

websocket_messages_sent = Counter(
    'websocket_messages_sent_total',
    'Total messages sent'
)

websocket_messages_received = Counter(
    'websocket_messages_received_total',
    'Total messages received'
)

websocket_message_latency = Histogram(
    'websocket_message_latency_seconds',
    'Message processing latency'
)

websocket_errors = Counter(
    'websocket_errors_total',
    'Total errors',
    ['error_type']
)

class MonitoredWebSocketServer:
    def __init__(self):
        self.clients = set()

        # Start Prometheus metrics server
        start_http_server(9090)

    async def handler(self, websocket, path):
        # Track connection
        websocket_connections.inc()
        self.clients.add(websocket)

        try:
            async for message in websocket:
                # Track received message
                websocket_messages_received.inc()

                # Measure processing time
                with websocket_message_latency.time():
                    await self.process_message(websocket, message)

                # Track sent message
                websocket_messages_sent.inc()

        except websockets.exceptions.ConnectionClosed:
            websocket_errors.labels(error_type='connection_closed').inc()
        except Exception as e:
            websocket_errors.labels(error_type=type(e).__name__).inc()
        finally:
            # Untrack connection
            self.clients.discard(websocket)
            websocket_connections.dec()
```

### Logging

```python
import logging
import json

# Structured logging
class JSONFormatter(logging.Formatter):
    """JSON log formatter"""

    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields
        if hasattr(record, "client_id"):
            log_data["client_id"] = record.client_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data)

# Configure logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Usage
async def handler(websocket, path):
    client_id = websocket.remote_address

    logger.info(
        "Client connected",
        extra={"client_id": client_id}
    )

    start = time.time()
    try:
        async for message in websocket:
            await process(message)
    finally:
        duration = (time.time() - start) * 1000
        logger.info(
            "Client disconnected",
            extra={
                "client_id": client_id,
                "duration_ms": duration
            }
        )
```

---

## 21. Anti-Patterns

### Common Mistakes

❌ **No sticky sessions on load balancer**
```
Problem: Client randomly routed to different backends
Solution: Use ip_hash (nginx) or session affinity
```

❌ **No heartbeat/ping**
```
Problem: Dead connections stay open, waste resources
Solution: Enable ping_interval and ping_timeout
```

❌ **No authentication**
```
Problem: Anyone can connect
Solution: Verify tokens during handshake or within timeout
```

❌ **Ignoring Origin header**
```
Problem: Cross-site WebSocket hijacking (CSRF)
Solution: Validate Origin against allowed list
```

❌ **Synchronous blocking code**
```
Problem: Blocks event loop, kills performance
Solution: Use async/await for all I/O
```

❌ **No message size limit**
```
Problem: Memory exhaustion attack
Solution: Set max_size parameter
```

❌ **No rate limiting**
```
Problem: Message flooding
Solution: Implement token bucket or sliding window
```

❌ **Not handling reconnection (client)**
```
Problem: Permanent disconnection on network blip
Solution: Implement exponential backoff reconnection
```

❌ **Storing state only in memory**
```
Problem: Connection loss = data loss
Solution: Use Redis/database for persistent state
```

❌ **Not validating input**
```
Problem: Injection attacks, crashes
Solution: Validate and sanitize all input
```

❌ **Forgetting wss:// in production**
```
Problem: Unencrypted traffic, MITM attacks
Solution: Always use wss:// with valid TLS certificate
```

❌ **Not setting Connection/Upgrade headers in proxy**
```
Problem: HTTP upgrade fails, connection fails
Solution: Configure proxy headers correctly
```

---

## 22. References

### Official Specifications

- **RFC 6455**: The WebSocket Protocol
  https://datatracker.ietf.org/doc/html/rfc6455

- **RFC 7692**: Compression Extensions for WebSocket
  https://datatracker.ietf.org/doc/html/rfc7692

### Libraries

**Python**:
- websockets: https://websockets.readthedocs.io/
- aiohttp: https://docs.aiohttp.org/en/stable/web_quickstart.html#websockets

**JavaScript/Node.js**:
- ws: https://github.com/websockets/ws
- Socket.IO: https://socket.io/docs/v4/

**Go**:
- gorilla/websocket: https://github.com/gorilla/websocket
- nhooyr.io/websocket: https://github.com/nhooyr/websocket

**Java**:
- Spring WebSocket: https://docs.spring.io/spring-framework/reference/web/websocket.html
- Java-WebSocket: https://github.com/TooTallNate/Java-WebSocket

**Rust**:
- tokio-tungstenite: https://github.com/snapview/tokio-tungstenite
- actix-web: https://actix.rs/docs/websockets/

### Tools

- wscat: https://github.com/websockets/wscat
- websocat: https://github.com/vi/websocat
- Postman: WebSocket support

### Best Practices

- MDN WebSocket API: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- OWASP WebSocket Security: https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Cheat_Sheet.html

---

**End of Reference**

**Version**: 1.0
**Last Updated**: 2025-10-29
**Lines**: ~3,200
