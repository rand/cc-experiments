/**
 * useWebSocket Hook for React
 *
 * A robust React hook for WebSocket connections with automatic reconnection,
 * message queueing, and state management.
 *
 * Installation:
 *   npm install react
 *
 * Usage:
 *   const { isConnected, lastMessage, sendMessage, error } = useWebSocket('wss://api.example.com/ws');
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface UseWebSocketOptions {
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  maxQueueSize?: number;
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onMessage?: (data: any) => void;
  onError?: (event: Event) => void;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  connectionState: 'disconnected' | 'connecting' | 'connected' | 'reconnecting';
  lastMessage: any;
  error: Event | null;
  sendMessage: (data: any) => void;
  disconnect: () => void;
  reconnect: () => void;
  queuedMessages: number;
}

/**
 * Custom React hook for WebSocket connections
 */
export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const {
    reconnect = true,
    reconnectInterval = 1000,
    maxReconnectInterval = 30000,
    maxReconnectAttempts = Infinity,
    heartbeatInterval = 30000,
    maxQueueSize = 100,
    onOpen,
    onClose,
    onMessage,
    onError,
  } = options;

  // State
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<'disconnected' | 'connecting' | 'connected' | 'reconnecting'>('disconnected');
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [error, setError] = useState<Event | null>(null);
  const [queuedMessages, setQueuedMessages] = useState(0);

  // Refs (don't trigger re-renders)
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const messageQueueRef = useRef<any[]>([]);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectEnabledRef = useRef(reconnect);

  // Start heartbeat (ping/pong not directly exposed in browser WebSocket API)
  const startHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
    }

    heartbeatTimerRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        // Send application-level ping
        wsRef.current.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
      }
    }, heartbeatInterval);
  }, [heartbeatInterval]);

  // Stop heartbeat
  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  }, []);

  // Queue message
  const queueMessage = useCallback((data: any) => {
    if (messageQueueRef.current.length >= maxQueueSize) {
      console.warn('[useWebSocket] Message queue full, dropping oldest message');
      messageQueueRef.current.shift();
    }
    messageQueueRef.current.push(data);
    setQueuedMessages(messageQueueRef.current.length);
  }, [maxQueueSize]);

  // Flush message queue
  const flushQueue = useCallback(() => {
    if (messageQueueRef.current.length === 0) return;

    console.log(`[useWebSocket] Flushing ${messageQueueRef.current.length} queued messages`);

    while (messageQueueRef.current.length > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
      const message = messageQueueRef.current.shift();
      const payload = typeof message === 'string' ? message : JSON.stringify(message);
      wsRef.current.send(payload);
    }

    setQueuedMessages(messageQueueRef.current.length);
  }, []);

  // Send message
  const sendMessage = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const payload = typeof data === 'string' ? data : JSON.stringify(data);
      wsRef.current.send(payload);
    } else {
      console.log('[useWebSocket] Not connected, queueing message');
      queueMessage(data);
    }
  }, [queueMessage]);

  // Reconnect with exponential backoff
  const reconnectWs = useCallback(() => {
    if (!reconnectEnabledRef.current) {
      console.log('[useWebSocket] Reconnection disabled');
      return;
    }

    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      console.error('[useWebSocket] Max reconnection attempts reached');
      return;
    }

    reconnectAttemptsRef.current += 1;

    // Exponential backoff with jitter
    const delay = Math.min(
      reconnectInterval * Math.pow(2, reconnectAttemptsRef.current - 1),
      maxReconnectInterval
    );
    const jitter = delay * 0.1 * Math.random();
    const actualDelay = delay + jitter;

    console.log(`[useWebSocket] Reconnecting in ${actualDelay}ms (attempt ${reconnectAttemptsRef.current})`);

    setConnectionState('reconnecting');

    reconnectTimerRef.current = setTimeout(() => {
      connectWs();
    }, actualDelay);
  }, [reconnectInterval, maxReconnectInterval, maxReconnectAttempts]);

  // Connect to WebSocket
  const connectWs = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.warn('[useWebSocket] Already connected or connecting');
      return;
    }

    setConnectionState('connecting');
    console.log(`[useWebSocket] Connecting to ${url}...`);

    try {
      const ws = new WebSocket(url);

      ws.onopen = (event) => {
        console.log('[useWebSocket] Connected');
        setIsConnected(true);
        setConnectionState('connected');
        setError(null);
        reconnectAttemptsRef.current = 0;

        // Flush queued messages
        flushQueue();

        // Start heartbeat
        startHeartbeat();

        // Call user callback
        onOpen?.();
      };

      ws.onmessage = (event) => {
        let data = event.data;

        // Try to parse JSON
        try {
          data = JSON.parse(event.data);
        } catch (e) {
          // Not JSON, use as-is
        }

        setLastMessage(data);

        // Call user callback
        onMessage?.(data);
      };

      ws.onclose = (event) => {
        console.log(`[useWebSocket] Disconnected: code=${event.code}, reason=${event.reason}`);
        setIsConnected(false);
        setConnectionState('disconnected');

        stopHeartbeat();

        // Call user callback
        onClose?.(event);

        // Reconnect if not normal closure
        if (reconnectEnabledRef.current && event.code !== 1000) {
          reconnectWs();
        }
      };

      ws.onerror = (event) => {
        console.error('[useWebSocket] Error:', event);
        setError(event);

        // Call user callback
        onError?.(event);
      };

      wsRef.current = ws;

    } catch (error) {
      console.error('[useWebSocket] Connection failed:', error);
      setConnectionState('disconnected');

      if (reconnectEnabledRef.current) {
        reconnectWs();
      }
    }
  }, [url, flushQueue, startHeartbeat, stopHeartbeat, reconnectWs, onOpen, onMessage, onClose, onError]);

  // Disconnect
  const disconnect = useCallback(() => {
    console.log('[useWebSocket] Disconnecting...');

    reconnectEnabledRef.current = false;
    stopHeartbeat();

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setConnectionState('disconnected');
    setIsConnected(false);
  }, [stopHeartbeat]);

  // Manual reconnect
  const manualReconnect = useCallback(() => {
    disconnect();
    reconnectEnabledRef.current = true;
    reconnectAttemptsRef.current = 0;
    connectWs();
  }, [disconnect, connectWs]);

  // Connect on mount
  useEffect(() => {
    connectWs();

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [url]); // Only reconnect if URL changes

  return {
    isConnected,
    connectionState,
    lastMessage,
    error,
    sendMessage,
    disconnect,
    reconnect: manualReconnect,
    queuedMessages,
  };
}

/**
 * Example usage component
 */
export function WebSocketExample() {
  const {
    isConnected,
    connectionState,
    lastMessage,
    sendMessage,
    queuedMessages,
  } = useWebSocket('ws://localhost:8080', {
    reconnect: true,
    reconnectInterval: 1000,
    maxReconnectInterval: 30000,
    onOpen: () => {
      console.log('WebSocket opened');
      // Join a room on connect
      sendMessage({ type: 'join', room: 'lobby' });
    },
    onMessage: (data) => {
      console.log('Received:', data);
    },
  });

  const handleSendMessage = () => {
    sendMessage({
      type: 'message',
      content: 'Hello from React!',
    });
  };

  return (
    <div className="websocket-example">
      <h2>WebSocket Connection</h2>

      <div className="status">
        <p>
          Status: <strong>{connectionState}</strong>
        </p>
        <p>
          Connected: <strong>{isConnected ? 'Yes' : 'No'}</strong>
        </p>
        <p>
          Queued Messages: <strong>{queuedMessages}</strong>
        </p>
      </div>

      <div className="controls">
        <button onClick={handleSendMessage} disabled={!isConnected}>
          Send Message
        </button>
      </div>

      <div className="messages">
        <h3>Last Message</h3>
        <pre>{JSON.stringify(lastMessage, null, 2)}</pre>
      </div>
    </div>
  );
}

/**
 * Example with room-based messaging
 */
export function ChatRoom({ roomName }: { roomName: string }) {
  const [messages, setMessages] = useState<any[]>([]);
  const [inputText, setInputText] = useState('');

  const { isConnected, sendMessage } = useWebSocket('ws://localhost:8080', {
    onOpen: () => {
      // Join room on connect
      sendMessage({ type: 'join', room: roomName });
    },
    onMessage: (data) => {
      if (data.type === 'message') {
        setMessages((prev) => [...prev, data]);
      }
    },
  });

  const handleSend = () => {
    if (inputText.trim() && isConnected) {
      sendMessage({
        type: 'message',
        content: inputText,
      });
      setInputText('');
    }
  };

  return (
    <div className="chat-room">
      <h2>Room: {roomName}</h2>

      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className="message">
            <strong>{msg.userId}:</strong> {msg.content}
          </div>
        ))}
      </div>

      <div className="input">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          disabled={!isConnected}
          placeholder="Type a message..."
        />
        <button onClick={handleSend} disabled={!isConnected}>
          Send
        </button>
      </div>
    </div>
  );
}
