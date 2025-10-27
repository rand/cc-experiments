/**
 * WebSocket Client Example (Node.js)
 *
 * Demonstrates a robust WebSocket client with reconnection, message queueing,
 * and heartbeat detection.
 *
 * Installation:
 *   npm install ws
 *
 * Usage:
 *   node websocket-client.js
 *   node websocket-client.js --url wss://api.example.com/ws
 */

const WebSocket = require('ws');
const EventEmitter = require('events');

class RobustWebSocketClient extends EventEmitter {
  constructor(url, options = {}) {
    super();

    this.url = url;
    this.ws = null;

    // Options
    this.reconnectEnabled = options.reconnect !== false;
    this.reconnectInterval = options.reconnectInterval || 1000;
    this.maxReconnectInterval = options.maxReconnectInterval || 30000;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = options.maxReconnectAttempts || Infinity;

    this.heartbeatInterval = options.heartbeatInterval || 30000;
    this.heartbeatTimeout = options.heartbeatTimeout || 5000;

    this.messageQueue = [];
    this.maxQueueSize = options.maxQueueSize || 100;

    this.state = 'disconnected';
    this.heartbeatTimer = null;
    this.heartbeatTimeoutTimer = null;
    this.reconnectTimer = null;
  }

  connect() {
    if (this.state === 'connecting' || this.state === 'connected') {
      console.log('Already connected or connecting');
      return;
    }

    this.state = 'connecting';
    this.emit('connecting');

    console.log(`Connecting to ${this.url}...`);

    try {
      this.ws = new WebSocket(this.url);

      this.ws.on('open', () => this.onOpen());
      this.ws.on('message', (data, isBinary) => this.onMessage(data, isBinary));
      this.ws.on('close', (code, reason) => this.onClose(code, reason));
      this.ws.on('error', (error) => this.onError(error));
      this.ws.on('pong', () => this.onPong());

    } catch (error) {
      this.onError(error);
      this.reconnect();
    }
  }

  disconnect() {
    console.log('Disconnecting...');

    this.reconnectEnabled = false;
    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
    }

    this.state = 'disconnected';
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const payload = typeof data === 'string' ? data : JSON.stringify(data);
      this.ws.send(payload);
      console.log('Sent:', payload);
    } else {
      console.log('Not connected, queueing message');
      this.queueMessage(data);
    }
  }

  queueMessage(data) {
    if (this.messageQueue.length >= this.maxQueueSize) {
      console.warn('Message queue full, dropping oldest message');
      this.messageQueue.shift();
    }
    this.messageQueue.push(data);
  }

  flushQueue() {
    console.log(`Flushing message queue (${this.messageQueue.length} messages)`);

    while (this.messageQueue.length > 0 && this.ws.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift();
      this.send(message);
    }
  }

  startHeartbeat() {
    this.stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        console.log('Sending ping...');
        this.ws.ping();

        // Expect pong within timeout
        this.heartbeatTimeoutTimer = setTimeout(() => {
          console.warn('Heartbeat timeout, reconnecting...');
          this.ws.terminate();
        }, this.heartbeatTimeout);
      }
    }, this.heartbeatInterval);
  }

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }

  onOpen() {
    console.log('Connected successfully');

    this.state = 'connected';
    this.reconnectAttempts = 0;
    this.emit('connected');

    // Flush queued messages
    this.flushQueue();

    // Start heartbeat
    this.startHeartbeat();
  }

  onMessage(data, isBinary) {
    if (isBinary) {
      console.log('Received binary:', data);
      this.emit('message', data, true);
    } else {
      const text = data.toString();
      console.log('Received:', text);

      try {
        const msg = JSON.parse(text);
        this.emit('message', msg, false);

        // Handle specific message types
        if (msg.type === 'pong') {
          this.emit('pong', msg);
        }
      } catch (e) {
        this.emit('message', text, false);
      }
    }
  }

  onClose(code, reason) {
    console.log(`Disconnected: code=${code}, reason=${reason.toString()}`);

    this.state = 'disconnected';
    this.stopHeartbeat();
    this.emit('disconnected', { code, reason: reason.toString() });

    // Reconnect if enabled
    if (this.reconnectEnabled && code !== 1000) {
      this.reconnect();
    }
  }

  onError(error) {
    console.error('WebSocket error:', error.message);
    this.emit('error', error);
  }

  onPong() {
    console.log('Received pong');

    // Clear heartbeat timeout
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }

    this.emit('pong');
  }

  reconnect() {
    if (!this.reconnectEnabled) {
      console.log('Reconnection disabled');
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('max_reconnect_attempts');
      return;
    }

    this.reconnectAttempts++;

    // Exponential backoff with jitter
    const delay = Math.min(
      this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectInterval
    );
    const jitter = delay * 0.1 * Math.random();
    const actualDelay = delay + jitter;

    console.log(`Reconnecting in ${actualDelay}ms (attempt ${this.reconnectAttempts})`);

    this.state = 'reconnecting';
    this.emit('reconnecting', { attempt: this.reconnectAttempts, delay: actualDelay });

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, actualDelay);
  }

  getState() {
    return this.state;
  }
}

// Example usage
if (require.main === module) {
  const args = process.argv.slice(2);
  const urlArg = args.find(arg => arg.startsWith('--url='));
  const url = urlArg ? urlArg.split('=')[1] : 'ws://localhost:8080';

  const client = new RobustWebSocketClient(url, {
    reconnect: true,
    reconnectInterval: 1000,
    maxReconnectInterval: 30000,
    heartbeatInterval: 30000
  });

  // Event listeners
  client.on('connecting', () => {
    console.log('[EVENT] Connecting...');
  });

  client.on('connected', () => {
    console.log('[EVENT] Connected!');

    // Join a room
    client.send({
      type: 'join',
      room: 'test-room'
    });

    // Send periodic messages
    setInterval(() => {
      if (client.getState() === 'connected') {
        client.send({
          type: 'message',
          content: `Hello at ${new Date().toISOString()}`
        });
      }
    }, 5000);
  });

  client.on('disconnected', ({ code, reason }) => {
    console.log(`[EVENT] Disconnected: ${code} - ${reason}`);
  });

  client.on('reconnecting', ({ attempt, delay }) => {
    console.log(`[EVENT] Reconnecting (attempt ${attempt}, delay ${delay}ms)`);
  });

  client.on('message', (msg, isBinary) => {
    if (!isBinary) {
      console.log('[EVENT] Message:', msg);
    }
  });

  client.on('error', (error) => {
    console.error('[EVENT] Error:', error.message);
  });

  // Connect
  client.connect();

  // Graceful shutdown
  process.on('SIGINT', () => {
    console.log('\nShutting down...');
    client.disconnect();
    setTimeout(() => process.exit(0), 1000);
  });
}

module.exports = RobustWebSocketClient;
