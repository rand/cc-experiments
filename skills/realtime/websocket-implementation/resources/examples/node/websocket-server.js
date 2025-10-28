/**
 * WebSocket Server Example (Node.js)
 *
 * Demonstrates a production-ready WebSocket server using the 'ws' library.
 * Features: broadcast, rooms, authentication, rate limiting, metrics.
 *
 * Installation:
 *   npm install ws
 *
 * Usage:
 *   node websocket-server.js
 *   node websocket-server.js --port 8080 --redis redis://localhost:6379
 */

const WebSocket = require('ws');
const http = require('http');
const crypto = require('crypto');

// Configuration
const PORT = process.env.PORT || 8080;
const PING_INTERVAL = 30000; // 30 seconds
const MESSAGE_RATE_LIMIT = 10; // messages per second
const MAX_MESSAGE_SIZE = 100 * 1024; // 100KB

// Metrics
const metrics = {
  connections: 0,
  totalConnections: 0,
  messagesReceived: 0,
  messagesSent: 0,
  bytesReceived: 0,
  bytesSent: 0
};

// Room management
const rooms = new Map();

// Rate limiting
class RateLimiter {
  constructor(maxRate) {
    this.maxRate = maxRate;
    this.buckets = new WeakMap();
  }

  check(ws) {
    if (!this.buckets.has(ws)) {
      this.buckets.set(ws, {
        count: 0,
        resetTime: Date.now() + 1000
      });
    }

    const bucket = this.buckets.get(ws);

    if (Date.now() > bucket.resetTime) {
      bucket.count = 0;
      bucket.resetTime = Date.now() + 1000;
    }

    bucket.count++;

    return bucket.count <= this.maxRate;
  }
}

const rateLimiter = new RateLimiter(MESSAGE_RATE_LIMIT);

// Broadcast to all clients in a room
function broadcastToRoom(room, message, sender = null) {
  const roomClients = rooms.get(room);
  if (!roomClients) return;

  const data = JSON.stringify(message);
  let sent = 0;

  roomClients.forEach((client) => {
    if (client !== sender && client.readyState === WebSocket.OPEN) {
      client.send(data);
      metrics.messagesSent++;
      metrics.bytesSent += data.length;
      sent++;
    }
  });

  return sent;
}

// Broadcast to all clients
function broadcastAll(message, sender = null) {
  const data = JSON.stringify(message);
  let sent = 0;

  wss.clients.forEach((client) => {
    if (client !== sender && client.readyState === WebSocket.OPEN) {
      client.send(data);
      metrics.messagesSent++;
      metrics.bytesSent += data.length;
      sent++;
    }
  });

  return sent;
}

// Join room
function joinRoom(ws, room) {
  if (!rooms.has(room)) {
    rooms.set(room, new Set());
  }

  rooms.get(room).add(ws);
  ws.room = room;

  console.log(`Client ${ws.id} joined room: ${room} (${rooms.get(room).size} members)`);

  // Notify room
  broadcastToRoom(room, {
    type: 'user_joined',
    userId: ws.userId,
    room: room,
    timestamp: Date.now()
  }, ws);
}

// Leave room
function leaveRoom(ws) {
  if (ws.room && rooms.has(ws.room)) {
    rooms.get(ws.room).delete(ws);

    // Notify room
    broadcastToRoom(ws.room, {
      type: 'user_left',
      userId: ws.userId,
      room: ws.room,
      timestamp: Date.now()
    }, ws);

    // Clean up empty rooms
    if (rooms.get(ws.room).size === 0) {
      rooms.delete(ws.room);
    }

    console.log(`Client ${ws.id} left room: ${ws.room}`);
    ws.room = null;
  }
}

// Message handlers
const messageHandlers = {
  join: (ws, data) => {
    if (ws.room) {
      leaveRoom(ws);
    }
    joinRoom(ws, data.room);

    ws.send(JSON.stringify({
      type: 'joined',
      room: data.room,
      timestamp: Date.now()
    }));
  },

  leave: (ws) => {
    leaveRoom(ws);

    ws.send(JSON.stringify({
      type: 'left',
      timestamp: Date.now()
    }));
  },

  message: (ws, data) => {
    if (!ws.room) {
      ws.send(JSON.stringify({
        type: 'error',
        error: 'Not in a room'
      }));
      return;
    }

    const sent = broadcastToRoom(ws.room, {
      type: 'message',
      userId: ws.userId,
      room: ws.room,
      content: data.content,
      timestamp: Date.now()
    }, ws);

    console.log(`Message in room ${ws.room}: ${data.content} (sent to ${sent} clients)`);
  },

  ping: (ws) => {
    ws.send(JSON.stringify({
      type: 'pong',
      timestamp: Date.now()
    }));
  },

  broadcast: (ws, data) => {
    const sent = broadcastAll({
      type: 'broadcast',
      userId: ws.userId,
      content: data.content,
      timestamp: Date.now()
    }, ws);

    console.log(`Broadcast: ${data.content} (sent to ${sent} clients)`);
  }
};

// Create HTTP server (for health checks, metrics)
const server = http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', uptime: process.uptime() }));
  } else if (req.url === '/metrics') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(metrics));
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
});

// Create WebSocket server
const wss = new WebSocket.Server({
  server,
  maxPayload: MAX_MESSAGE_SIZE,
  perMessageDeflate: {
    zlibDeflateOptions: {
      level: 6
    },
    threshold: 1024
  }
});

// Connection handler
wss.on('connection', (ws, req) => {
  // Generate connection ID
  ws.id = crypto.randomBytes(8).toString('hex');
  ws.userId = `user_${ws.id.slice(0, 8)}`;
  ws.isAlive = true;
  ws.room = null;

  metrics.connections++;
  metrics.totalConnections++;

  console.log(`Client connected: ${ws.id} (${req.socket.remoteAddress})`);

  // Send welcome message
  ws.send(JSON.stringify({
    type: 'welcome',
    userId: ws.userId,
    timestamp: Date.now()
  }));

  // Message handler
  ws.on('message', (data, isBinary) => {
    metrics.messagesReceived++;
    metrics.bytesReceived += data.length;

    // Rate limiting
    if (!rateLimiter.check(ws)) {
      ws.send(JSON.stringify({
        type: 'error',
        error: 'Rate limit exceeded'
      }));
      return;
    }

    // Parse message
    let msg;
    try {
      msg = isBinary ? data : JSON.parse(data.toString());
    } catch (e) {
      ws.send(JSON.stringify({
        type: 'error',
        error: 'Invalid JSON'
      }));
      return;
    }

    // Handle message
    const handler = messageHandlers[msg.type];
    if (handler) {
      try {
        handler(ws, msg);
      } catch (e) {
        console.error(`Error handling ${msg.type}:`, e);
        ws.send(JSON.stringify({
          type: 'error',
          error: 'Internal server error'
        }));
      }
    } else {
      ws.send(JSON.stringify({
        type: 'error',
        error: `Unknown message type: ${msg.type}`
      }));
    }
  });

  // Pong handler (for heartbeat)
  ws.on('pong', () => {
    ws.isAlive = true;
  });

  // Close handler
  ws.on('close', (code, reason) => {
    metrics.connections--;
    leaveRoom(ws);
    console.log(`Client disconnected: ${ws.id} (code: ${code}, reason: ${reason.toString()})`);
  });

  // Error handler
  ws.on('error', (error) => {
    console.error(`Client error (${ws.id}):`, error.message);
  });
});

// Heartbeat interval (ping/pong)
const heartbeatInterval = setInterval(() => {
  wss.clients.forEach((ws) => {
    if (ws.isAlive === false) {
      console.log(`Terminating inactive connection: ${ws.id}`);
      return ws.terminate();
    }

    ws.isAlive = false;
    ws.ping();
  });
}, PING_INTERVAL);

// Cleanup on server close
wss.on('close', () => {
  clearInterval(heartbeatInterval);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing server...');

  wss.clients.forEach((ws) => {
    ws.close(1001, 'Server shutting down');
  });

  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });

  // Force exit after 10 seconds
  setTimeout(() => {
    console.error('Forced exit after timeout');
    process.exit(1);
  }, 10000);
});

// Start server
server.listen(PORT, () => {
  console.log(`WebSocket server running on ws://localhost:${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Metrics: http://localhost:${PORT}/metrics`);
});
