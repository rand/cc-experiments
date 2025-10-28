# WebSocket Protocol - Comprehensive Reference

## Table of Contents

1. [Protocol Fundamentals](#protocol-fundamentals)
2. [Connection Lifecycle](#connection-lifecycle)
3. [Frame Structure](#frame-structure)
4. [Message Types](#message-types)
5. [Security](#security)
6. [Scaling Patterns](#scaling-patterns)
7. [Reconnection Strategies](#reconnection-strategies)
8. [Server Implementations](#server-implementations)
9. [Client Implementations](#client-implementations)
10. [Testing Strategies](#testing-strategies)
11. [Common Patterns](#common-patterns)
12. [Comparison with Alternatives](#comparison-with-alternatives)
13. [Production Best Practices](#production-best-practices)
14. [Troubleshooting](#troubleshooting)
15. [Performance Optimization](#performance-optimization)

---

## Protocol Fundamentals

### RFC 6455 Overview

WebSocket is a computer communications protocol providing full-duplex communication channels over a single TCP connection. Standardized by RFC 6455 in 2011, it enables real-time, bidirectional data exchange between client and server with lower overhead than HTTP polling.

**Key Characteristics**:
- Full-duplex bidirectional communication
- Single TCP connection
- Low overhead (2-14 bytes per frame vs HTTP headers)
- Works over HTTP ports (80/443)
- Upgrades from HTTP via handshake
- UTF-8 text or binary data
- Built-in ping/pong for keepalive

**Protocol URI Schemes**:
```
ws://  - Unencrypted WebSocket (like HTTP)
wss:// - Encrypted WebSocket over TLS (like HTTPS)
```

### WebSocket vs HTTP

**HTTP Request/Response**:
```
Client -> Server: GET /data HTTP/1.1
Server -> Client: 200 OK + data
[Connection closes or kept alive]
Client -> Server: New request needed for new data
```

**WebSocket Persistent Connection**:
```
Client -> Server: Upgrade to WebSocket
Server -> Client: 101 Switching Protocols
[Connection remains open]
Client <-> Server: Bidirectional messages anytime
```

**Overhead Comparison**:
```
HTTP Request Headers:  ~200-800 bytes per request
HTTP Response Headers: ~200-500 bytes per response
Total per exchange:    ~400-1300 bytes

WebSocket Frame:       2-14 bytes per message
```

For 1000 messages:
- HTTP: 400KB - 1.3MB overhead
- WebSocket: 2KB - 14KB overhead

### Protocol Layers

```
┌─────────────────────────────────┐
│   Application Layer             │
│   (Your application logic)      │
├─────────────────────────────────┤
│   WebSocket Protocol            │
│   (RFC 6455 - Framing/Messages) │
├─────────────────────────────────┤
│   TLS (for wss://)              │
│   (Optional encryption)         │
├─────────────────────────────────┤
│   TCP                           │
│   (Reliable transport)          │
├─────────────────────────────────┤
│   IP                            │
│   (Network routing)             │
└─────────────────────────────────┘
```

### Use Cases

**Ideal for**:
- Real-time chat applications
- Live sports/stock tickers
- Multiplayer games
- Collaborative editing (Google Docs-style)
- Live dashboards/monitoring
- IoT device communication
- Live video streaming metadata
- Trading platforms
- Real-time notifications

**Not ideal for**:
- One-way server push (use SSE)
- Infrequent updates (use HTTP polling)
- REST API calls (use HTTP)
- File uploads (use HTTP multipart)
- Heavy proxy/firewall environments

---

## Connection Lifecycle

### Phase 1: HTTP Upgrade Handshake

The WebSocket connection begins as an HTTP request that "upgrades" to the WebSocket protocol.

**Client Handshake Request**:
```http
GET /chat HTTP/1.1
Host: example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
Origin: http://example.com
Sec-WebSocket-Protocol: chat, superchat
Sec-WebSocket-Extensions: permessage-deflate
```

**Header Breakdown**:
- `Upgrade: websocket` - Request protocol upgrade
- `Connection: Upgrade` - Indicate connection will be upgraded
- `Sec-WebSocket-Key` - Random base64-encoded 16-byte value (security)
- `Sec-WebSocket-Version` - WebSocket protocol version (13 is current)
- `Origin` - Browser security (prevent CSRF)
- `Sec-WebSocket-Protocol` - Subprotocols (optional)
- `Sec-WebSocket-Extensions` - Extensions like compression (optional)

**Server Handshake Response**:
```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
Sec-WebSocket-Protocol: chat
Sec-WebSocket-Extensions: permessage-deflate
```

**Header Breakdown**:
- `101 Switching Protocols` - Upgrade accepted
- `Sec-WebSocket-Accept` - Computed from client's key (see below)
- `Sec-WebSocket-Protocol` - Selected subprotocol (if any)
- `Sec-WebSocket-Extensions` - Accepted extensions

**Sec-WebSocket-Accept Calculation**:
```javascript
// Server computes this from client's Sec-WebSocket-Key
const crypto = require('crypto');

function generateAcceptKey(clientKey) {
  const GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'; // RFC 6455 magic string
  const hash = crypto
    .createHash('sha1')
    .update(clientKey + GUID)
    .digest('base64');
  return hash;
}

// Example:
const clientKey = 'dGhlIHNhbXBsZSBub25jZQ==';
const acceptKey = generateAcceptKey(clientKey);
// Returns: 's3pPLMBiTxaQ9kYGzzhZRbK+xOo='
```

This prevents accidental WebSocket connections and ensures both sides understand the protocol.

### Phase 2: Data Transfer

Once upgraded, the connection switches to WebSocket framing. Both client and server can send messages at any time.

**Message Flow**:
```
Client                          Server
  |                               |
  |-- Text Message -------------->|
  |                               |
  |<-- Text Message --------------|
  |                               |
  |-- Binary Message ------------>|
  |                               |
  |<-- Ping -----------------------|
  |-- Pong ---------------------->|
  |                               |
```

**Multiplexing**: A single WebSocket connection can carry multiple logical channels/topics by using message prefixes or JSON envelopes:

```javascript
// Topic-based routing
ws.send(JSON.stringify({
  topic: 'chat',
  data: { user: 'Alice', message: 'Hello' }
}));

ws.send(JSON.stringify({
  topic: 'notifications',
  data: { type: 'friend_request', from: 'Bob' }
}));
```

### Phase 3: Connection Close

Either side can initiate a close. The closing handshake ensures graceful shutdown.

**Close Handshake**:
```
Client                          Server
  |                               |
  |-- Close Frame (code 1000) --->|
  |                               |
  |<-- Close Frame (code 1000) ---|
  |                               |
  [TCP connection closes]
```

**Close Codes** (from RFC 6455):
```
1000 - Normal Closure
1001 - Going Away (server shutdown, browser navigation)
1002 - Protocol Error
1003 - Unsupported Data (e.g., text-only but received binary)
1006 - Abnormal Closure (no close frame, connection lost)
1007 - Invalid Payload Data (malformed UTF-8 in text)
1008 - Policy Violation (generic)
1009 - Message Too Big
1010 - Mandatory Extension (client expected extension)
1011 - Internal Server Error
1015 - TLS Handshake Failure
```

**Application-Defined Codes**: 3000-4999 range for custom close reasons.

**Close Sequence**:
```javascript
// Client initiates close
ws.close(1000, 'User logged out');

// Server receives close event
ws.on('close', (code, reason) => {
  console.log(`Closed: ${code} - ${reason}`);
  // Cleanup resources
});

// Server responds with close frame
// TCP connection terminates
```

### State Transitions

```
CONNECTING (0)
    ↓
    [Handshake completes]
    ↓
OPEN (1)
    ↓
    [Close initiated]
    ↓
CLOSING (2)
    ↓
    [Close handshake completes]
    ↓
CLOSED (3)
```

**Browser WebSocket API States**:
```javascript
WebSocket.CONNECTING  // 0
WebSocket.OPEN        // 1
WebSocket.CLOSING     // 2
WebSocket.CLOSED      // 3

// Check state
if (ws.readyState === WebSocket.OPEN) {
  ws.send('message');
}
```

### Connection Errors

**Common Failure Modes**:
1. **Handshake Rejection**: Server returns non-101 status
2. **Network Interruption**: Connection drops without close frame
3. **Timeout**: No data received for extended period
4. **Protocol Violation**: Invalid frame received
5. **TLS Failure**: Certificate issues on wss://

**Error Handling**:
```javascript
ws.on('error', (error) => {
  console.error('WebSocket error:', error);
  // Attempt reconnection if appropriate
});

ws.on('close', (code, reason) => {
  if (code !== 1000) {
    console.error(`Abnormal close: ${code} - ${reason}`);
    // Trigger reconnection logic
  }
});
```

---

## Frame Structure

WebSocket uses a binary framing protocol. Each message is split into one or more frames.

### Frame Format

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

### Field Descriptions

**FIN (1 bit)**:
- `1` = Final fragment in message
- `0` = More fragments follow
- Allows message fragmentation

**RSV1, RSV2, RSV3 (1 bit each)**:
- Reserved for extensions
- Must be 0 unless extension defines usage
- Example: RSV1 = 1 for permessage-deflate compression

**Opcode (4 bits)**:
```
0x0 - Continuation frame
0x1 - Text frame (UTF-8)
0x2 - Binary frame
0x8 - Connection close
0x9 - Ping
0xA - Pong
0x3-0x7 - Reserved for future data frames
0xB-0xF - Reserved for future control frames
```

**MASK (1 bit)**:
- `1` = Payload is masked (MUST be 1 for client->server)
- `0` = Payload is not masked (server->client)
- Prevents cache poisoning attacks

**Payload Length (7 bits, 7+16 bits, or 7+64 bits)**:
```
0-125:  Actual payload length
126:    Next 2 bytes are 16-bit length
127:    Next 8 bytes are 64-bit length
```

**Masking Key (0 or 4 bytes)**:
- Present if MASK bit is set
- Random 32-bit value
- Used to XOR payload data

**Payload Data**:
- Extension data (if negotiated) + Application data
- Masked if from client

### Masking Algorithm

Client-to-server frames MUST be masked to prevent cache poisoning:

```javascript
function maskPayload(payload, maskingKey) {
  const masked = Buffer.alloc(payload.length);
  for (let i = 0; i < payload.length; i++) {
    masked[i] = payload[i] ^ maskingKey[i % 4];
  }
  return masked;
}

// Example
const payload = Buffer.from('Hello');
const maskingKey = Buffer.from([0x12, 0x34, 0x56, 0x78]);
const masked = maskPayload(payload, maskingKey);

// Unmask (server-side)
const unmasked = maskPayload(masked, maskingKey); // XOR is reversible
// unmasked equals original payload
```

### Frame Examples

**Simple Text Message** (client->server):
```
"Hi" (2 bytes payload)

0x81 0x82 [mask] [masked payload]

Breakdown:
0x81 = 10000001
  - FIN=1 (final fragment)
  - RSV=000
  - Opcode=0001 (text)

0x82 = 10000010
  - MASK=1
  - Length=2

[4 bytes masking key]
[2 bytes masked payload]

Total: 8 bytes
```

**Ping Frame** (server->client):
```
0x89 0x00

Breakdown:
0x89 = 10001001
  - FIN=1
  - RSV=000
  - Opcode=1001 (ping)

0x00 = 00000000
  - MASK=0
  - Length=0

Total: 2 bytes
```

**Large Binary Message** (server->client, 65KB):
```
0x82 0x7E [2-byte length] [payload]

Breakdown:
0x82 = 10000010
  - FIN=1
  - Opcode=0010 (binary)

0x7E = 01111110
  - MASK=0
  - Length=126 (indicates next 2 bytes are length)

[2 bytes: 0xFF 0xFF = 65535]
[65535 bytes payload]

Total: 4 + 65535 = 65539 bytes
```

### Fragmentation

Large messages can be split into multiple frames:

```
Frame 1: FIN=0, Opcode=0x1 (text), Payload="Hello "
Frame 2: FIN=0, Opcode=0x0 (continuation), Payload="World"
Frame 3: FIN=1, Opcode=0x0 (continuation), Payload="!"

Reassembled: "Hello World!"
```

**Fragmentation Rules**:
- First frame has message opcode (text/binary)
- Subsequent frames have opcode 0x0 (continuation)
- Control frames (ping/pong/close) can be interleaved
- Control frames MUST NOT be fragmented

**Example with Interleaved Ping**:
```
Frame 1: FIN=0, Opcode=0x1 (text), Payload="Start"
Frame 2: FIN=1, Opcode=0x9 (ping), Payload=""
Frame 3: FIN=1, Opcode=0xA (pong), Payload=""
Frame 4: FIN=1, Opcode=0x0 (continuation), Payload="End"

Text message: "StartEnd"
Ping/Pong: Handled separately
```

### Control Frames

**Characteristics**:
- Opcode >= 0x8
- MUST NOT be fragmented
- Payload <= 125 bytes
- Can be injected mid-message

**Close Frame Payload**:
```
[2-byte status code] [UTF-8 reason]

Example:
0x03 0xE8 "Going away"
  = 1000 "Going away"
```

**Ping/Pong Application Data**:
```
Ping: 0x89 0x05 "12345"
Pong: 0x8A 0x05 "12345"  (echoes ping data)
```

---

## Message Types

### Text Messages

**Characteristics**:
- Opcode: 0x1
- Payload MUST be valid UTF-8
- Server MUST close connection on invalid UTF-8 (code 1007)

**Sending**:
```javascript
// Browser
ws.send('Hello World');
ws.send(JSON.stringify({ type: 'chat', msg: 'Hi' }));

// Node.js (ws library)
ws.send('Hello World', { binary: false });
```

**Receiving**:
```javascript
ws.onmessage = (event) => {
  if (typeof event.data === 'string') {
    console.log('Text:', event.data);
    const obj = JSON.parse(event.data);
  }
};
```

**UTF-8 Validation**:
```javascript
// Server must validate
function isValidUTF8(buffer) {
  try {
    buffer.toString('utf8');
    return true;
  } catch (e) {
    return false;
  }
}

ws.on('message', (data, isBinary) => {
  if (!isBinary && !isValidUTF8(data)) {
    ws.close(1007, 'Invalid UTF-8');
  }
});
```

**Common JSON Envelope Pattern**:
```javascript
// Structured message format
const message = {
  type: 'event_type',
  id: 'unique_id',
  timestamp: Date.now(),
  data: { /* payload */ }
};

ws.send(JSON.stringify(message));
```

### Binary Messages

**Characteristics**:
- Opcode: 0x2
- Raw binary data
- No encoding constraints

**Sending**:
```javascript
// Browser - ArrayBuffer
const buffer = new ArrayBuffer(8);
const view = new DataView(buffer);
view.setUint32(0, 12345678);
ws.send(buffer);

// Browser - Blob
const blob = new Blob(['binary data'], { type: 'application/octet-stream' });
ws.send(blob);

// Node.js - Buffer
const buf = Buffer.from([0x01, 0x02, 0x03]);
ws.send(buf, { binary: true });
```

**Receiving**:
```javascript
// Browser
ws.binaryType = 'arraybuffer'; // or 'blob'

ws.onmessage = (event) => {
  if (event.data instanceof ArrayBuffer) {
    const view = new DataView(event.data);
    const value = view.getUint32(0);
  }
};

// Node.js
ws.on('message', (data, isBinary) => {
  if (isBinary) {
    console.log('Binary:', data); // Buffer
  }
});
```

**Use Cases**:
- Image/video streaming
- Audio data
- Protocol buffers / MessagePack
- Game state (packed binary formats)
- Sensor data

### Ping/Pong Frames

**Purpose**:
- Keep connection alive
- Detect broken connections
- Measure latency

**Ping Frame**:
- Opcode: 0x9
- Optional payload (max 125 bytes)
- Recipient MUST respond with Pong

**Pong Frame**:
- Opcode: 0xA
- MUST echo Ping payload
- Can be sent unsolicited (heartbeat)

**Browser Limitation**: JavaScript WebSocket API doesn't expose ping/pong directly (browser handles automatically).

**Server-Side Ping** (Node.js ws):
```javascript
const ws = new WebSocket.Server({ port: 8080 });

ws.on('connection', (socket) => {
  const interval = setInterval(() => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.ping();
    }
  }, 30000); // Every 30 seconds

  socket.on('pong', () => {
    console.log('Pong received');
  });

  socket.on('close', () => {
    clearInterval(interval);
  });
});
```

**Client-Side Pong** (automatic in most libraries):
```javascript
// Most libraries auto-respond to ping
// Manual pong (if needed):
ws.on('ping', (data) => {
  ws.pong(data);
});
```

**Latency Measurement**:
```javascript
let pingStart;

const interval = setInterval(() => {
  pingStart = Date.now();
  ws.ping();
}, 5000);

ws.on('pong', () => {
  const latency = Date.now() - pingStart;
  console.log(`Latency: ${latency}ms`);
});
```

**Timeout Detection**:
```javascript
const PING_INTERVAL = 30000;
const PONG_TIMEOUT = 5000;

let pingTimeout;

function heartbeat() {
  clearTimeout(pingTimeout);
  pingTimeout = setTimeout(() => {
    console.log('Connection timed out');
    ws.terminate(); // Force close
  }, PONG_TIMEOUT);
}

const interval = setInterval(() => {
  ws.ping();
  heartbeat();
}, PING_INTERVAL);

ws.on('pong', () => {
  heartbeat();
});

ws.on('close', () => {
  clearInterval(interval);
  clearTimeout(pingTimeout);
});
```

### Close Frames

**Close Frame Structure**:
```
[2-byte status code] [optional UTF-8 reason]
```

**Common Patterns**:
```javascript
// Normal closure
ws.close(1000, 'Goodbye');

// Application error
ws.close(4000, 'Authentication failed');

// Policy violation
ws.close(1008, 'Rate limit exceeded');

// Going away
ws.close(1001, 'Server shutting down');
```

**Graceful Shutdown**:
```javascript
// Server shutdown
process.on('SIGTERM', () => {
  wss.clients.forEach((ws) => {
    ws.close(1001, 'Server shutting down');
  });

  setTimeout(() => {
    process.exit(0);
  }, 5000);
});
```

**Close Handshake Timeout**:
```javascript
ws.on('close', (code, reason) => {
  console.log(`Closed: ${code} - ${reason}`);
});

// Force close if handshake takes too long
const closeTimeout = setTimeout(() => {
  ws.terminate(); // Forceful close
}, 3000);

ws.on('close', () => {
  clearTimeout(closeTimeout);
});
```

---

## Security

### Origin Validation

The `Origin` header (sent by browsers) must be validated to prevent CSRF attacks.

**Attack Scenario**:
```
1. User logged into trusted.com (has WebSocket connection)
2. User visits evil.com
3. evil.com JavaScript tries: new WebSocket('wss://trusted.com/ws')
4. Without origin check, connection succeeds with user's cookies
```

**Server-Side Validation**:
```javascript
const ALLOWED_ORIGINS = [
  'https://trusted.com',
  'https://app.trusted.com'
];

wss.on('connection', (ws, req) => {
  const origin = req.headers.origin;

  if (!ALLOWED_ORIGINS.includes(origin)) {
    ws.close(1008, 'Origin not allowed');
    return;
  }

  // Continue with connection
});
```

**Development vs Production**:
```javascript
const ALLOWED_ORIGINS = process.env.NODE_ENV === 'production'
  ? ['https://app.example.com']
  : ['http://localhost:3000', 'http://localhost:5173'];
```

### Authentication

WebSocket doesn't have built-in authentication. Common patterns:

**1. Token in Query String**:
```javascript
// Client
const token = await getAuthToken();
const ws = new WebSocket(`wss://api.example.com/ws?token=${token}`);

// Server
wss.on('connection', (ws, req) => {
  const url = new URL(req.url, 'wss://api.example.com');
  const token = url.searchParams.get('token');

  if (!verifyToken(token)) {
    ws.close(1008, 'Invalid token');
    return;
  }

  ws.userId = extractUserId(token);
});
```

**Caution**: Tokens in URLs may be logged. Use wss:// to encrypt.

**2. Token in Subprotocol**:
```javascript
// Client
const ws = new WebSocket('wss://api.example.com/ws', ['access_token', token]);

// Server
wss.on('connection', (ws, req) => {
  const protocol = req.headers['sec-websocket-protocol'];
  const [_, token] = protocol.split(', ');

  if (!verifyToken(token)) {
    ws.close(1008, 'Invalid token');
    return;
  }
});
```

**3. Cookie-Based** (if same-origin):
```javascript
// Cookies sent automatically in handshake
wss.on('connection', (ws, req) => {
  const cookies = parseCookies(req.headers.cookie);
  const sessionId = cookies['session_id'];

  if (!validateSession(sessionId)) {
    ws.close(1008, 'Invalid session');
    return;
  }
});
```

**4. Post-Connection Authentication**:
```javascript
// Client
const ws = new WebSocket('wss://api.example.com/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: authToken
  }));
};

// Server
const pendingAuth = new WeakMap();

wss.on('connection', (ws) => {
  pendingAuth.set(ws, setTimeout(() => {
    ws.close(1008, 'Authentication timeout');
  }, 5000));

  ws.on('message', (data) => {
    const msg = JSON.parse(data);

    if (msg.type === 'auth' && pendingAuth.has(ws)) {
      clearTimeout(pendingAuth.get(ws));
      pendingAuth.delete(ws);

      if (verifyToken(msg.token)) {
        ws.authenticated = true;
        ws.userId = extractUserId(msg.token);
      } else {
        ws.close(1008, 'Invalid credentials');
      }
    } else if (!ws.authenticated) {
      ws.close(1008, 'Not authenticated');
    }
  });
});
```

### TLS/SSL (wss://)

**Always use wss:// in production**:
- Encrypts all data
- Prevents eavesdropping
- Prevents man-in-the-middle attacks
- Required for browser security features

**Certificate Setup**:
```javascript
const https = require('https');
const WebSocket = require('ws');
const fs = require('fs');

const server = https.createServer({
  cert: fs.readFileSync('/path/to/cert.pem'),
  key: fs.readFileSync('/path/to/key.pem')
});

const wss = new WebSocket.Server({ server });

server.listen(8080);
```

**Let's Encrypt with Certbot**:
```bash
certbot certonly --standalone -d api.example.com
# Certificates in /etc/letsencrypt/live/api.example.com/
```

### Rate Limiting

Prevent abuse by limiting message frequency:

```javascript
const MESSAGE_LIMIT = 10;
const WINDOW_MS = 1000;

const rateLimits = new WeakMap();

wss.on('connection', (ws) => {
  rateLimits.set(ws, {
    count: 0,
    resetTime: Date.now() + WINDOW_MS
  });

  ws.on('message', (data) => {
    const limit = rateLimits.get(ws);

    if (Date.now() > limit.resetTime) {
      limit.count = 0;
      limit.resetTime = Date.now() + WINDOW_MS;
    }

    limit.count++;

    if (limit.count > MESSAGE_LIMIT) {
      ws.close(1008, 'Rate limit exceeded');
      return;
    }

    // Process message
  });
});
```

**Token Bucket Algorithm**:
```javascript
class TokenBucket {
  constructor(capacity, refillRate) {
    this.capacity = capacity;
    this.tokens = capacity;
    this.refillRate = refillRate; // tokens per second
    this.lastRefill = Date.now();
  }

  consume(tokens = 1) {
    this.refill();

    if (this.tokens >= tokens) {
      this.tokens -= tokens;
      return true;
    }
    return false;
  }

  refill() {
    const now = Date.now();
    const elapsed = (now - this.lastRefill) / 1000;
    const tokensToAdd = elapsed * this.refillRate;

    this.tokens = Math.min(this.capacity, this.tokens + tokensToAdd);
    this.lastRefill = now;
  }
}

const buckets = new WeakMap();

wss.on('connection', (ws) => {
  buckets.set(ws, new TokenBucket(100, 10)); // 100 capacity, 10/sec refill

  ws.on('message', (data) => {
    const bucket = buckets.get(ws);

    if (!bucket.consume()) {
      ws.send(JSON.stringify({ error: 'Rate limit exceeded' }));
      return;
    }

    // Process message
  });
});
```

### Input Validation

Always validate and sanitize incoming messages:

```javascript
ws.on('message', (data, isBinary) => {
  // Size limit
  if (data.length > 1024 * 1024) { // 1MB
    ws.close(1009, 'Message too large');
    return;
  }

  // Type validation
  if (isBinary && !expectBinary) {
    ws.close(1003, 'Unexpected binary data');
    return;
  }

  // JSON parsing
  let msg;
  try {
    msg = JSON.parse(data);
  } catch (e) {
    ws.send(JSON.stringify({ error: 'Invalid JSON' }));
    return;
  }

  // Schema validation
  if (!isValidSchema(msg)) {
    ws.send(JSON.stringify({ error: 'Invalid message format' }));
    return;
  }

  // Sanitize strings (prevent XSS if echoed to browser)
  if (msg.text) {
    msg.text = sanitizeHtml(msg.text);
  }

  // Process validated message
});
```

### DoS Protection

**Connection Limits**:
```javascript
const MAX_CONNECTIONS_PER_IP = 10;
const connections = new Map();

wss.on('connection', (ws, req) => {
  const ip = req.socket.remoteAddress;
  const count = connections.get(ip) || 0;

  if (count >= MAX_CONNECTIONS_PER_IP) {
    ws.close(1008, 'Too many connections');
    return;
  }

  connections.set(ip, count + 1);

  ws.on('close', () => {
    connections.set(ip, connections.get(ip) - 1);
  });
});
```

**Message Size Limits**:
```javascript
const wss = new WebSocket.Server({
  port: 8080,
  maxPayload: 100 * 1024 // 100KB max message size
});
```

**Compression Bomb Protection**:
```javascript
const wss = new WebSocket.Server({
  perMessageDeflate: {
    zlibDeflateOptions: {
      level: 6 // Balanced compression
    },
    zlibInflateOptions: {
      chunkSize: 10 * 1024 // Limit decompressed chunks
    },
    threshold: 1024 // Only compress messages > 1KB
  }
});
```

---

## Scaling Patterns

### Horizontal Scaling Challenges

WebSocket connections are stateful and long-lived, creating scaling challenges:

**Problem**: Client connected to Server A cannot receive messages from Server B.

```
Client 1 ─┬─> Server A ─┐
Client 2 ─┘             │
                        ├─> Load Balancer
Client 3 ─┬─> Server B ─┘
Client 4 ─┘

If Client 1 sends to Client 3, message stuck in Server A.
```

### Sticky Sessions

Route all requests from a client to the same server.

**Load Balancer Configuration** (Nginx):
```nginx
upstream websocket_backend {
  ip_hash; # Route by client IP
  server 10.0.0.1:8080;
  server 10.0.0.2:8080;
  server 10.0.0.3:8080;
}

server {
  listen 80;

  location /ws {
    proxy_pass http://websocket_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }
}
```

**HAProxy Configuration**:
```
frontend websocket_front
  bind *:80
  default_backend websocket_back

backend websocket_back
  balance source # IP-based sticky sessions
  server ws1 10.0.0.1:8080 check
  server ws2 10.0.0.2:8080 check
  server ws3 10.0.0.3:8080 check
```

**Limitations**:
- Uneven distribution if clients behind NAT
- Can't rebalance without dropping connections
- Server failure drops all its clients

### Pub/Sub with Redis

Enable cross-server messaging using Redis as a message broker.

**Architecture**:
```
Client 1 ──> Server A ──┐
                        ├──> Redis Pub/Sub ──┬──> Server B ──> Client 3
Client 2 ──> Server B ──┘                    └──> Server C ──> Client 4
```

**Implementation** (Node.js):
```javascript
const Redis = require('ioredis');
const WebSocket = require('ws');

// Create Redis clients (pub and sub must be separate)
const publisher = new Redis();
const subscriber = new Redis();

const wss = new WebSocket.Server({ port: 8080 });

// Subscribe to Redis channel
subscriber.subscribe('chat');

subscriber.on('message', (channel, message) => {
  const msg = JSON.parse(message);

  // Broadcast to all local WebSocket clients
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      // Optional: filter by room/topic
      if (client.room === msg.room) {
        client.send(JSON.stringify(msg));
      }
    }
  });
});

// Handle WebSocket messages
wss.on('connection', (ws) => {
  ws.on('message', (data) => {
    const msg = JSON.parse(data);

    // Publish to Redis (reaches all servers)
    publisher.publish('chat', JSON.stringify(msg));
  });
});
```

**Room-Based Routing**:
```javascript
// Client joins room
ws.on('message', (data) => {
  const msg = JSON.parse(data);

  if (msg.type === 'join') {
    ws.room = msg.room;
    subscriber.subscribe(`chat:${msg.room}`);
  } else if (msg.type === 'message') {
    publisher.publish(`chat:${ws.room}`, JSON.stringify(msg));
  }
});

// Targeted broadcast
subscriber.on('message', (channel, message) => {
  const room = channel.split(':')[1];

  wss.clients.forEach((client) => {
    if (client.room === room && client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });
});
```

**Presence Tracking**:
```javascript
const PRESENCE_KEY = 'websocket:presence';

wss.on('connection', (ws, req) => {
  const userId = getUserId(req);
  const serverId = process.env.SERVER_ID;

  // Add to presence set
  publisher.sadd(PRESENCE_KEY, JSON.stringify({
    userId,
    serverId,
    connectedAt: Date.now()
  }));

  ws.on('close', () => {
    // Remove from presence set
    publisher.srem(PRESENCE_KEY, JSON.stringify({ userId, serverId }));
  });
});

// Get online users
async function getOnlineUsers() {
  const members = await publisher.smembers(PRESENCE_KEY);
  return members.map(JSON.parse);
}
```

### Redis Streams (Alternative)

More robust than Pub/Sub with message persistence and consumer groups:

```javascript
const Redis = require('ioredis');
const redis = new Redis();

// Producer (WebSocket server receives message)
async function publishMessage(room, message) {
  await redis.xadd(
    `stream:${room}`,
    '*', // Auto-generate ID
    'data', JSON.stringify(message)
  );
}

// Consumer (read messages)
async function consumeMessages(room) {
  let lastId = '0-0';

  while (true) {
    const results = await redis.xread(
      'BLOCK', 1000,
      'STREAMS', `stream:${room}`, lastId
    );

    if (results) {
      const [stream, messages] = results[0];

      messages.forEach(([id, fields]) => {
        const data = fields[1];
        const msg = JSON.parse(data);

        // Broadcast to WebSocket clients
        broadcastToRoom(room, msg);

        lastId = id;
      });
    }
  }
}
```

### Message Queue (RabbitMQ)

For complex routing and guaranteed delivery:

```javascript
const amqp = require('amqplib');

async function setupRabbitMQ() {
  const connection = await amqp.connect('amqp://localhost');
  const channel = await connection.createChannel();

  // Fanout exchange (broadcast to all)
  await channel.assertExchange('websocket', 'fanout', { durable: false });

  // Create queue for this server
  const { queue } = await channel.assertQueue('', { exclusive: true });
  await channel.bindQueue(queue, 'websocket', '');

  // Consume messages
  channel.consume(queue, (msg) => {
    const data = JSON.parse(msg.content.toString());

    wss.clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify(data));
      }
    });
  }, { noAck: true });

  // Publish messages
  wss.on('connection', (ws) => {
    ws.on('message', (data) => {
      channel.publish('websocket', '', Buffer.from(data));
    });
  });
}
```

### Database for Persistence

Store messages for offline users:

```javascript
const { Pool } = require('pg');
const pool = new Pool();

// Store message
async function storeMessage(roomId, userId, message) {
  await pool.query(
    'INSERT INTO messages (room_id, user_id, content, created_at) VALUES ($1, $2, $3, NOW())',
    [roomId, userId, message]
  );
}

// Get missed messages
async function getMissedMessages(roomId, since) {
  const result = await pool.query(
    'SELECT * FROM messages WHERE room_id = $1 AND created_at > $2 ORDER BY created_at',
    [roomId, since]
  );
  return result.rows;
}

// On reconnection
ws.on('message', async (data) => {
  const msg = JSON.parse(data);

  if (msg.type === 'join') {
    const missed = await getMissedMessages(msg.room, msg.lastSeen);
    missed.forEach((m) => {
      ws.send(JSON.stringify(m));
    });
  }
});
```

### Serverless WebSocket

**AWS API Gateway WebSockets**:
```javascript
// Lambda handler for connect
exports.connect = async (event) => {
  const connectionId = event.requestContext.connectionId;

  // Store connection in DynamoDB
  await dynamodb.put({
    TableName: 'WebSocketConnections',
    Item: { connectionId, timestamp: Date.now() }
  }).promise();

  return { statusCode: 200 };
};

// Lambda handler for message
exports.message = async (event) => {
  const { connectionId } = event.requestContext;
  const message = JSON.parse(event.body);

  // Get all connections
  const connections = await dynamodb.scan({
    TableName: 'WebSocketConnections'
  }).promise();

  // Send to all
  const apiGateway = new AWS.ApiGatewayManagementApi({
    endpoint: event.requestContext.domainName + '/' + event.requestContext.stage
  });

  await Promise.all(connections.Items.map(async ({ connectionId: targetId }) => {
    try {
      await apiGateway.postToConnection({
        ConnectionId: targetId,
        Data: JSON.stringify(message)
      }).promise();
    } catch (e) {
      if (e.statusCode === 410) {
        // Clean up stale connection
        await dynamodb.delete({
          TableName: 'WebSocketConnections',
          Key: { connectionId: targetId }
        }).promise();
      }
    }
  }));

  return { statusCode: 200 };
};
```

---

## Reconnection Strategies

Network interruptions require robust reconnection logic.

### Exponential Backoff

Avoid overwhelming the server with reconnection attempts:

```javascript
class WebSocketClient {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectInterval = 1000; // Start at 1 second
    this.maxReconnectInterval = 30000; // Cap at 30 seconds
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('Connected');
      this.reconnectAttempts = 0; // Reset on success
    };

    this.ws.onclose = (event) => {
      console.log('Disconnected:', event.code, event.reason);
      this.reconnect();
    };

    this.ws.onerror = (error) => {
      console.error('Error:', error);
    };
  }

  reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;

    // Exponential backoff with jitter
    const delay = Math.min(
      this.reconnectInterval * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectInterval
    );

    const jitter = delay * 0.1 * Math.random(); // +/- 10% jitter
    const actualDelay = delay + jitter;

    console.log(`Reconnecting in ${actualDelay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      this.connect();
    }, actualDelay);
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    } else {
      console.warn('Cannot send, not connected');
      // Queue message or handle error
    }
  }
}

const client = new WebSocketClient('wss://api.example.com/ws');
client.connect();
```

### Message Queueing

Buffer messages while disconnected:

```javascript
class RobustWebSocket {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.messageQueue = [];
    this.maxQueueSize = 100;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('Connected, flushing queue');
      this.flushQueue();
    };

    this.ws.onclose = () => {
      this.reconnect();
    };
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    } else {
      // Queue message
      if (this.messageQueue.length < this.maxQueueSize) {
        this.messageQueue.push(data);
      } else {
        console.warn('Message queue full, dropping oldest');
        this.messageQueue.shift();
        this.messageQueue.push(data);
      }
    }
  }

  flushQueue() {
    while (this.messageQueue.length > 0 && this.ws.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift();
      this.ws.send(message);
    }
  }

  reconnect() {
    // Exponential backoff logic from previous example
  }
}
```

### State Synchronization

Resync state after reconnection:

```javascript
class StatefulWebSocket {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.lastMessageId = 0;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      // Request missed messages
      this.ws.send(JSON.stringify({
        type: 'sync',
        lastMessageId: this.lastMessageId
      }));
    };

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.id > this.lastMessageId) {
        this.lastMessageId = msg.id;
        this.handleMessage(msg);
      } else {
        // Duplicate or old message, ignore
      }
    };
  }

  handleMessage(msg) {
    // Process message
    console.log('Message:', msg);
  }
}
```

### Heartbeat Detection

Detect connection death faster than TCP keepalive:

```javascript
class HeartbeatWebSocket {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.heartbeatInterval = null;
    this.heartbeatTimeout = null;
    this.HEARTBEAT_INTERVAL = 30000; // 30 seconds
    this.HEARTBEAT_TIMEOUT = 5000; // 5 seconds
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === 'pong') {
        this.resetHeartbeat();
      } else {
        this.handleMessage(msg);
      }
    };

    this.ws.onclose = () => {
      this.stopHeartbeat();
      this.reconnect();
    };
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.ping();
    }, this.HEARTBEAT_INTERVAL);
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  ping() {
    this.ws.send(JSON.stringify({ type: 'ping' }));

    // Expect pong within timeout
    this.heartbeatTimeout = setTimeout(() => {
      console.warn('Heartbeat timeout, reconnecting');
      this.ws.close();
    }, this.HEARTBEAT_TIMEOUT);
  }

  resetHeartbeat() {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  reconnect() {
    // Exponential backoff logic
  }
}
```

### Connection State Machine

Robust state management:

```javascript
const States = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting'
};

class StateMachineWebSocket {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.state = States.DISCONNECTED;
    this.listeners = {};
  }

  connect() {
    if (this.state !== States.DISCONNECTED) {
      console.warn('Already connecting or connected');
      return;
    }

    this.setState(States.CONNECTING);
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.setState(States.CONNECTED);
    };

    this.ws.onclose = () => {
      if (this.state === States.CONNECTED) {
        this.setState(States.RECONNECTING);
        this.reconnect();
      } else {
        this.setState(States.DISCONNECTED);
      }
    };

    this.ws.onerror = (error) => {
      this.emit('error', error);
    };
  }

  setState(newState) {
    const oldState = this.state;
    this.state = newState;
    this.emit('stateChange', { from: oldState, to: newState });
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  }

  reconnect() {
    // Exponential backoff
    setTimeout(() => {
      this.state = States.DISCONNECTED;
      this.connect();
    }, 1000);
  }
}

// Usage
const ws = new StateMachineWebSocket('wss://api.example.com/ws');

ws.on('stateChange', ({ from, to }) => {
  console.log(`State: ${from} -> ${to}`);

  if (to === States.CONNECTED) {
    // Update UI to show connected
  } else if (to === States.RECONNECTING) {
    // Show reconnecting indicator
  }
});

ws.connect();
```

---

## Server Implementations

### Node.js (ws library)

**Installation**:
```bash
npm install ws
```

**Basic Server**:
```javascript
const WebSocket = require('ws');

const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', (ws, req) => {
  console.log('Client connected:', req.socket.remoteAddress);

  ws.on('message', (data, isBinary) => {
    console.log('Received:', data.toString());

    // Echo back
    ws.send(data, { binary: isBinary });
  });

  ws.on('close', (code, reason) => {
    console.log('Client disconnected:', code, reason.toString());
  });

  ws.on('error', (error) => {
    console.error('WebSocket error:', error);
  });

  ws.send('Welcome!');
});

console.log('WebSocket server running on ws://localhost:8080');
```

**Broadcast to All Clients**:
```javascript
function broadcast(data) {
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(data);
    }
  });
}

wss.on('connection', (ws) => {
  ws.on('message', (data) => {
    broadcast(data); // Send to all connected clients
  });
});
```

**Room-Based Broadcasting**:
```javascript
const rooms = new Map();

wss.on('connection', (ws) => {
  ws.on('message', (data) => {
    const msg = JSON.parse(data);

    if (msg.type === 'join') {
      if (!rooms.has(msg.room)) {
        rooms.set(msg.room, new Set());
      }
      rooms.get(msg.room).add(ws);
      ws.room = msg.room;
    } else if (msg.type === 'message') {
      const room = rooms.get(ws.room);
      if (room) {
        room.forEach((client) => {
          if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify(msg));
          }
        });
      }
    }
  });

  ws.on('close', () => {
    if (ws.room && rooms.has(ws.room)) {
      rooms.get(ws.room).delete(ws);
    }
  });
});
```

**With Express**:
```javascript
const express = require('express');
const { createServer } = require('http');
const WebSocket = require('ws');

const app = express();
const server = createServer(app);
const wss = new WebSocket.Server({ server });

app.get('/', (req, res) => {
  res.send('WebSocket server running');
});

wss.on('connection', (ws) => {
  ws.send('Connected to WebSocket server');
});

server.listen(8080, () => {
  console.log('Server running on http://localhost:8080');
});
```

**Compression (permessage-deflate)**:
```javascript
const wss = new WebSocket.Server({
  port: 8080,
  perMessageDeflate: {
    zlibDeflateOptions: {
      chunkSize: 1024,
      memLevel: 7,
      level: 3
    },
    zlibInflateOptions: {
      chunkSize: 10 * 1024
    },
    clientNoContextTakeover: true,
    serverNoContextTakeover: true,
    serverMaxWindowBits: 10,
    concurrencyLimit: 10,
    threshold: 1024 // Only compress messages > 1KB
  }
});
```

### Python (websockets library)

**Installation**:
```bash
pip install websockets
```

**Basic Server** (async):
```python
import asyncio
import websockets

async def handler(websocket, path):
    print(f"Client connected: {websocket.remote_address}")

    try:
        async for message in websocket:
            print(f"Received: {message}")

            # Echo back
            await websocket.send(message)
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    async with websockets.serve(handler, "localhost", 8080):
        print("WebSocket server running on ws://localhost:8080")
        await asyncio.Future()  # Run forever

asyncio.run(main())
```

**Broadcast to All Clients**:
```python
import asyncio
import websockets

connected = set()

async def handler(websocket, path):
    connected.add(websocket)
    try:
        async for message in websocket:
            # Broadcast to all clients
            websockets.broadcast(connected, message)
    finally:
        connected.remove(websocket)

async def main():
    async with websockets.serve(handler, "localhost", 8080):
        await asyncio.Future()

asyncio.run(main())
```

**JSON Messages**:
```python
import asyncio
import websockets
import json

async def handler(websocket, path):
    async for message in websocket:
        data = json.loads(message)

        # Process
        response = {
            "type": "response",
            "echo": data
        }

        await websocket.send(json.dumps(response))

async def main():
    async with websockets.serve(handler, "localhost", 8080):
        await asyncio.Future()

asyncio.run(main())
```

**With Authentication**:
```python
import asyncio
import websockets
import jwt

async def handler(websocket, path):
    # Read first message as auth token
    try:
        token = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        payload = jwt.decode(token, "secret", algorithms=["HS256"])
        user_id = payload["user_id"]
    except (asyncio.TimeoutError, jwt.InvalidTokenError):
        await websocket.close(1008, "Authentication failed")
        return

    print(f"User {user_id} authenticated")

    # Continue with authenticated connection
    async for message in websocket:
        await websocket.send(f"User {user_id}: {message}")

async def main():
    async with websockets.serve(handler, "localhost", 8080):
        await asyncio.Future()

asyncio.run(main())
```

### Go (gorilla/websocket)

**Installation**:
```bash
go get github.com/gorilla/websocket
```

**Basic Server**:
```go
package main

import (
    "fmt"
    "log"
    "net/http"

    "github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
    CheckOrigin: func(r *http.Request) bool {
        return true // Allow all origins (configure for production)
    },
}

func handler(w http.ResponseWriter, r *http.Request) {
    conn, err := upgrader.Upgrade(w, r, nil)
    if err != nil {
        log.Println("Upgrade error:", err)
        return
    }
    defer conn.Close()

    fmt.Println("Client connected:", conn.RemoteAddr())

    for {
        messageType, message, err := conn.ReadMessage()
        if err != nil {
            log.Println("Read error:", err)
            break
        }

        fmt.Printf("Received: %s\n", message)

        // Echo back
        err = conn.WriteMessage(messageType, message)
        if err != nil {
            log.Println("Write error:", err)
            break
        }
    }
}

func main() {
    http.HandleFunc("/ws", handler)

    fmt.Println("WebSocket server running on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

**Broadcast Hub**:
```go
package main

import (
    "github.com/gorilla/websocket"
)

type Hub struct {
    clients    map[*websocket.Conn]bool
    broadcast  chan []byte
    register   chan *websocket.Conn
    unregister chan *websocket.Conn
}

func newHub() *Hub {
    return &Hub{
        clients:    make(map[*websocket.Conn]bool),
        broadcast:  make(chan []byte),
        register:   make(chan *websocket.Conn),
        unregister: make(chan *websocket.Conn),
    }
}

func (h *Hub) run() {
    for {
        select {
        case conn := <-h.register:
            h.clients[conn] = true
        case conn := <-h.unregister:
            if _, ok := h.clients[conn]; ok {
                delete(h.clients, conn)
                conn.Close()
            }
        case message := <-h.broadcast:
            for conn := range h.clients {
                err := conn.WriteMessage(websocket.TextMessage, message)
                if err != nil {
                    h.unregister <- conn
                }
            }
        }
    }
}

var hub = newHub()

func handler(w http.ResponseWriter, r *http.Request) {
    conn, _ := upgrader.Upgrade(w, r, nil)
    hub.register <- conn

    defer func() {
        hub.unregister <- conn
    }()

    for {
        _, message, err := conn.ReadMessage()
        if err != nil {
            break
        }
        hub.broadcast <- message
    }
}

func main() {
    go hub.run()

    http.HandleFunc("/ws", handler)
    http.ListenAndServe(":8080", nil)
}
```

---

## Client Implementations

### Browser (Native WebSocket API)

**Basic Connection**:
```javascript
const ws = new WebSocket('wss://api.example.com/ws');

ws.onopen = (event) => {
  console.log('Connected');
  ws.send('Hello Server');
};

ws.onmessage = (event) => {
  console.log('Received:', event.data);

  // Parse JSON if needed
  const data = JSON.parse(event.data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
  console.log('Disconnected:', event.code, event.reason);
};
```

**Send Binary Data**:
```javascript
// ArrayBuffer
const buffer = new ArrayBuffer(4);
const view = new DataView(buffer);
view.setUint32(0, 42);
ws.send(buffer);

// Blob
const blob = new Blob(['binary data']);
ws.send(blob);
```

**Receive Binary Data**:
```javascript
ws.binaryType = 'arraybuffer'; // or 'blob'

ws.onmessage = (event) => {
  if (event.data instanceof ArrayBuffer) {
    const view = new DataView(event.data);
    const value = view.getUint32(0);
    console.log('Binary:', value);
  } else {
    console.log('Text:', event.data);
  }
};
```

### Node.js Client (ws library)

```javascript
const WebSocket = require('ws');

const ws = new WebSocket('wss://api.example.com/ws');

ws.on('open', () => {
  console.log('Connected');
  ws.send('Hello');
});

ws.on('message', (data, isBinary) => {
  console.log('Received:', data.toString());
});

ws.on('close', (code, reason) => {
  console.log('Closed:', code, reason.toString());
});

ws.on('error', (error) => {
  console.error('Error:', error);
});
```

### Python Client (websockets)

```python
import asyncio
import websockets

async def client():
    async with websockets.connect('wss://api.example.com/ws') as ws:
        await ws.send('Hello')

        async for message in ws:
            print(f"Received: {message}")

asyncio.run(client())
```

### React Hook (useWebSocket)

```typescript
import { useEffect, useRef, useState } from 'react';

function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      setLastMessage(event.data);
    };

    ws.current.onclose = () => {
      setIsConnected(false);
    };

    return () => {
      ws.current?.close();
    };
  }, [url]);

  const send = (data: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(data);
    }
  };

  return { isConnected, lastMessage, send };
}

// Usage
function App() {
  const { isConnected, lastMessage, send } = useWebSocket('wss://api.example.com/ws');

  return (
    <div>
      <p>Status: {isConnected ? 'Connected' : 'Disconnected'}</p>
      <p>Last message: {lastMessage}</p>
      <button onClick={() => send('Hello')}>Send</button>
    </div>
  );
}
```

---

## Testing Strategies

### Unit Testing

**Test Message Handling**:
```javascript
const WebSocket = require('ws');

describe('WebSocket Handler', () => {
  let wss, ws;

  beforeAll((done) => {
    wss = new WebSocket.Server({ port: 8080 });
    wss.on('connection', (socket) => {
      socket.on('message', (data) => {
        const msg = JSON.parse(data);
        socket.send(JSON.stringify({ echo: msg }));
      });
    });
    done();
  });

  afterAll(() => {
    wss.close();
  });

  test('echoes message', (done) => {
    ws = new WebSocket('ws://localhost:8080');

    ws.on('open', () => {
      ws.send(JSON.stringify({ test: 'data' }));
    });

    ws.on('message', (data) => {
      const msg = JSON.parse(data);
      expect(msg.echo.test).toBe('data');
      ws.close();
      done();
    });
  });
});
```

### Integration Testing

**Test Full Flow**:
```javascript
describe('Chat Integration', () => {
  let server, client1, client2;

  beforeAll(async () => {
    server = new WebSocket.Server({ port: 8080 });
    // Setup broadcast logic

    client1 = new WebSocket('ws://localhost:8080');
    client2 = new WebSocket('ws://localhost:8080');

    await Promise.all([
      new Promise((resolve) => client1.on('open', resolve)),
      new Promise((resolve) => client2.on('open', resolve))
    ]);
  });

  test('broadcasts message to all clients', (done) => {
    client2.on('message', (data) => {
      expect(data.toString()).toBe('Hello');
      done();
    });

    client1.send('Hello');
  });

  afterAll(() => {
    client1.close();
    client2.close();
    server.close();
  });
});
```

### Load Testing

**Artillery**:
```yaml
# artillery.yml
config:
  target: "wss://api.example.com"
  phases:
    - duration: 60
      arrivalRate: 10
      name: "Warm up"
    - duration: 120
      arrivalRate: 50
      name: "Sustained load"
  engines:
    ws:
      timeout: 60

scenarios:
  - engine: ws
    flow:
      - connect:
          target: "/ws"
      - send: '{"type": "join", "room": "test"}'
      - think: 1
      - loop:
          - send: '{"type": "message", "text": "Hello"}'
          - think: 2
        count: 10
```

```bash
artillery run artillery.yml
```

**k6**:
```javascript
import ws from 'k6/ws';
import { check } from 'k6';

export let options = {
  vus: 100,
  duration: '30s',
};

export default function () {
  const url = 'wss://api.example.com/ws';

  const res = ws.connect(url, {}, function (socket) {
    socket.on('open', () => socket.send('Hello'));

    socket.on('message', (data) => {
      console.log('Received:', data);
    });

    socket.setTimeout(() => {
      socket.close();
    }, 10000);
  });

  check(res, { 'status is 101': (r) => r && r.status === 101 });
}
```

---

## Common Patterns

### Chat Application

**Server** (Node.js):
```javascript
const rooms = new Map();

wss.on('connection', (ws) => {
  ws.on('message', (data) => {
    const msg = JSON.parse(data);

    switch (msg.type) {
      case 'join':
        if (!rooms.has(msg.room)) {
          rooms.set(msg.room, new Set());
        }
        rooms.get(msg.room).add(ws);
        ws.room = msg.room;
        ws.username = msg.username;
        break;

      case 'message':
        const room = rooms.get(ws.room);
        if (room) {
          const payload = JSON.stringify({
            type: 'message',
            username: ws.username,
            text: msg.text,
            timestamp: Date.now()
          });

          room.forEach((client) => {
            if (client.readyState === WebSocket.OPEN) {
              client.send(payload);
            }
          });
        }
        break;
    }
  });

  ws.on('close', () => {
    if (ws.room && rooms.has(ws.room)) {
      rooms.get(ws.room).delete(ws);
    }
  });
});
```

**Client** (React):
```typescript
function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const ws = useRef<WebSocket>();

  useEffect(() => {
    ws.current = new WebSocket('wss://api.example.com/ws');

    ws.current.onopen = () => {
      ws.current.send(JSON.stringify({
        type: 'join',
        room: 'general',
        username: 'Alice'
      }));
    };

    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      setMessages((prev) => [...prev, msg]);
    };

    return () => ws.current?.close();
  }, []);

  const sendMessage = () => {
    ws.current?.send(JSON.stringify({
      type: 'message',
      text: input
    }));
    setInput('');
  };

  return (
    <div>
      {messages.map((msg, i) => (
        <div key={i}>{msg.username}: {msg.text}</div>
      ))}
      <input value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}
```

### Real-Time Dashboard

**Server** (push updates):
```javascript
const clients = new Set();

wss.on('connection', (ws) => {
  clients.add(ws);

  ws.on('close', () => {
    clients.remove(ws);
  });
});

// Push data updates
setInterval(() => {
  const data = {
    type: 'metrics',
    cpu: Math.random() * 100,
    memory: Math.random() * 100,
    timestamp: Date.now()
  };

  clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(data));
    }
  });
}, 1000);
```

**Client** (React with Chart):
```typescript
function Dashboard() {
  const [metrics, setMetrics] = useState([]);

  useEffect(() => {
    const ws = new WebSocket('wss://api.example.com/ws');

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMetrics((prev) => [...prev.slice(-60), data]); // Keep last 60
    };

    return () => ws.close();
  }, []);

  return (
    <LineChart data={metrics}>
      <Line dataKey="cpu" stroke="#8884d8" />
      <Line dataKey="memory" stroke="#82ca9d" />
    </LineChart>
  );
}
```

### Multiplayer Game (State Sync)

**Server**:
```javascript
const gameState = {
  players: new Map()
};

wss.on('connection', (ws) => {
  const playerId = generateId();

  gameState.players.set(playerId, {
    id: playerId,
    x: 0,
    y: 0
  });

  // Send full state to new player
  ws.send(JSON.stringify({
    type: 'init',
    playerId,
    state: Array.from(gameState.players.values())
  }));

  // Broadcast new player to others
  broadcast({
    type: 'player_joined',
    player: gameState.players.get(playerId)
  });

  ws.on('message', (data) => {
    const msg = JSON.parse(data);

    if (msg.type === 'move') {
      const player = gameState.players.get(playerId);
      player.x = msg.x;
      player.y = msg.y;

      // Broadcast position update
      broadcast({
        type: 'player_moved',
        playerId,
        x: msg.x,
        y: msg.y
      });
    }
  });

  ws.on('close', () => {
    gameState.players.delete(playerId);
    broadcast({
      type: 'player_left',
      playerId
    });
  });
});
```

---

## Comparison with Alternatives

### Server-Sent Events (SSE)

**SSE Characteristics**:
- Unidirectional (server → client only)
- HTTP-based (simpler than WebSocket)
- Automatic reconnection
- Text-only (no binary)
- EventSource API in browsers

**When to Use SSE**:
- One-way server push (notifications, live feeds)
- Simpler infrastructure requirements
- No binary data needed
- Want automatic reconnection

**When to Use WebSocket**:
- Bidirectional communication needed
- Low latency critical
- Binary data
- Custom protocols

**SSE Example**:
```javascript
// Server (Express)
app.get('/events', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const interval = setInterval(() => {
    res.write(`data: ${JSON.stringify({ time: Date.now() })}\n\n`);
  }, 1000);

  req.on('close', () => {
    clearInterval(interval);
  });
});

// Client
const eventSource = new EventSource('/events');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

### Long Polling

**Characteristics**:
- Client repeatedly requests updates
- Server holds request until data available
- High overhead (new request each time)

**When to Use Long Polling**:
- Legacy browser support
- Restrictive firewall/proxy
- Very infrequent updates

**When to Use WebSocket**:
- Frequent updates
- Modern browsers
- Real-time requirements

### HTTP/2 Server Push

**Characteristics**:
- Server can push resources proactively
- Still request/response model
- Limited browser support

**WebSocket Advantages**:
- True bidirectional
- Lower overhead
- Better browser support
- Persistent connection

---

## Production Best Practices

### Monitoring

**Key Metrics**:
- Active connections count
- Message throughput (messages/sec)
- Message latency (time from send to receive)
- Connection duration
- Reconnection rate
- Error rate
- Memory usage per connection

**Prometheus Metrics**:
```javascript
const prometheus = require('prom-client');

const activeConnections = new prometheus.Gauge({
  name: 'websocket_connections_active',
  help: 'Number of active WebSocket connections'
});

const messagesTotal = new prometheus.Counter({
  name: 'websocket_messages_total',
  help: 'Total number of WebSocket messages',
  labelNames: ['direction', 'type']
});

const messageLatency = new prometheus.Histogram({
  name: 'websocket_message_latency_seconds',
  help: 'WebSocket message latency',
  buckets: [0.001, 0.01, 0.1, 0.5, 1]
});

wss.on('connection', (ws) => {
  activeConnections.inc();

  ws.on('message', (data) => {
    messagesTotal.inc({ direction: 'inbound', type: 'text' });

    const start = Date.now();
    // Process message
    const duration = (Date.now() - start) / 1000;
    messageLatency.observe(duration);
  });

  ws.on('close', () => {
    activeConnections.dec();
  });
});
```

### Logging

**Structured Logging**:
```javascript
const winston = require('winston');

const logger = winston.createLogger({
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'websocket.log' })
  ]
});

wss.on('connection', (ws, req) => {
  const connId = generateId();

  logger.info('connection', {
    connId,
    ip: req.socket.remoteAddress,
    origin: req.headers.origin
  });

  ws.on('message', (data) => {
    logger.debug('message', {
      connId,
      size: data.length,
      type: typeof data
    });
  });

  ws.on('close', (code, reason) => {
    logger.info('disconnect', {
      connId,
      code,
      reason: reason.toString()
    });
  });

  ws.on('error', (error) => {
    logger.error('error', {
      connId,
      error: error.message,
      stack: error.stack
    });
  });
});
```

### Resource Limits

**Per-Connection Limits**:
```javascript
const MAX_MESSAGE_SIZE = 100 * 1024; // 100KB
const MAX_MESSAGES_PER_MINUTE = 60;

const wss = new WebSocket.Server({
  port: 8080,
  maxPayload: MAX_MESSAGE_SIZE
});

const rateLimits = new WeakMap();

wss.on('connection', (ws) => {
  rateLimits.set(ws, {
    count: 0,
    resetAt: Date.now() + 60000
  });

  ws.on('message', (data) => {
    const limit = rateLimits.get(ws);

    if (Date.now() > limit.resetAt) {
      limit.count = 0;
      limit.resetAt = Date.now() + 60000;
    }

    if (++limit.count > MAX_MESSAGES_PER_MINUTE) {
      ws.close(1008, 'Rate limit exceeded');
      return;
    }
  });
});
```

### Graceful Shutdown

```javascript
process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing connections');

  wss.clients.forEach((ws) => {
    ws.close(1001, 'Server shutting down');
  });

  const timeout = setTimeout(() => {
    console.log('Force closing remaining connections');
    wss.close(() => {
      process.exit(0);
    });
  }, 30000);

  wss.close(() => {
    clearTimeout(timeout);
    process.exit(0);
  });
});
```

---

## Troubleshooting

### Connection Fails

**Check**:
1. Correct URL scheme (ws:// vs wss://)
2. Server is running and accessible
3. Firewall allows WebSocket connections
4. Load balancer configured for WebSocket upgrade
5. Certificate valid (for wss://)

**Debug**:
```javascript
ws.onerror = (error) => {
  console.error('Connection error:', error);
  // Check: incorrect URL, network issues, server down
};

ws.onclose = (event) => {
  console.log('Close code:', event.code);
  console.log('Close reason:', event.reason);
  // 1006 = abnormal closure (network issue)
  // 1011 = server error
};
```

### Messages Not Received

**Check**:
1. Connection state (OPEN)
2. Message size within limits
3. Proper masking (client→server)
4. Valid UTF-8 (text messages)
5. Server is broadcasting correctly

**Debug**:
```javascript
console.log('WebSocket state:', ws.readyState);
// 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED

if (ws.readyState === WebSocket.OPEN) {
  ws.send('test');
} else {
  console.warn('Cannot send, connection not open');
}
```

### High Latency

**Causes**:
- Network congestion
- Server overload
- Message queue backlog
- Slow message processing

**Solutions**:
```javascript
// Measure latency
ws.send(JSON.stringify({ type: 'ping', sent: Date.now() }));

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'pong') {
    const latency = Date.now() - msg.sent;
    console.log('Latency:', latency, 'ms');
  }
};

// Server-side processing time
const start = Date.now();
// ... process message ...
const duration = Date.now() - start;
if (duration > 100) {
  console.warn('Slow processing:', duration, 'ms');
}
```

### Memory Leaks

**Common Causes**:
- Not removing event listeners
- Storing references to closed connections
- Unbounded message buffers

**Prevention**:
```javascript
const clients = new Set();

wss.on('connection', (ws) => {
  clients.add(ws);

  ws.on('close', () => {
    clients.delete(ws); // Clean up reference
  });
});

// Use WeakMap for connection metadata
const metadata = new WeakMap();

wss.on('connection', (ws) => {
  metadata.set(ws, { /* data */ }); // Auto-cleaned when ws GC'd
});
```

---

## Performance Optimization

### Compression

Enable permessage-deflate for text messages:

```javascript
const wss = new WebSocket.Server({
  perMessageDeflate: {
    threshold: 1024 // Only compress > 1KB
  }
});
```

**Trade-offs**:
- CPU usage vs bandwidth
- Latency increase (compression time)
- Memory usage (compression contexts)

### Binary Protocols

Use binary formats for structured data:

**MessagePack**:
```javascript
const msgpack = require('msgpack-lite');

// Send
const data = { user: 'Alice', count: 42 };
const encoded = msgpack.encode(data);
ws.send(encoded, { binary: true });

// Receive
ws.on('message', (data, isBinary) => {
  if (isBinary) {
    const decoded = msgpack.decode(data);
  }
});
```

**Protocol Buffers**:
```protobuf
message ChatMessage {
  string username = 1;
  string text = 2;
  int64 timestamp = 3;
}
```

```javascript
const protobuf = require('protobufjs');

const root = protobuf.loadSync('chat.proto');
const ChatMessage = root.lookupType('ChatMessage');

// Send
const message = ChatMessage.create({
  username: 'Alice',
  text: 'Hello',
  timestamp: Date.now()
});
const buffer = ChatMessage.encode(message).finish();
ws.send(buffer, { binary: true });
```

### Batching

Reduce overhead by batching multiple messages:

```javascript
const batch = [];
const BATCH_SIZE = 10;
const BATCH_INTERVAL = 100; // ms

function queueMessage(msg) {
  batch.push(msg);

  if (batch.length >= BATCH_SIZE) {
    flushBatch();
  }
}

function flushBatch() {
  if (batch.length === 0) return;

  ws.send(JSON.stringify(batch));
  batch.length = 0;
}

setInterval(flushBatch, BATCH_INTERVAL);
```

### Connection Pooling (Client)

Reuse connections for multiple logical channels:

```javascript
class WebSocketPool {
  constructor(url, size) {
    this.connections = [];
    for (let i = 0; i < size; i++) {
      this.connections.push(new WebSocket(url));
    }
    this.index = 0;
  }

  getConnection() {
    const conn = this.connections[this.index];
    this.index = (this.index + 1) % this.connections.length;
    return conn;
  }

  send(data) {
    const conn = this.getConnection();
    if (conn.readyState === WebSocket.OPEN) {
      conn.send(data);
    }
  }
}

const pool = new WebSocketPool('wss://api.example.com/ws', 5);
pool.send('message 1');
pool.send('message 2');
```

---

**End of WebSocket Reference**

This comprehensive reference covers the WebSocket protocol from fundamentals to production deployment. For hands-on examples, see the `examples/` directory. For testing and analysis tools, see the `scripts/` directory.
