import { useEffect, useState, useRef, useCallback } from 'react';

/**
 * Production-Ready React WebSocket Hook
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Connection state management
 * - Message queue for offline messages
 * - Heartbeat monitoring
 * - Type-safe message handling
 *
 * Usage:
 *   const { isConnected, sendMessage, lastMessage } = useWebSocket('wss://example.com/ws', {
 *     onMessage: (data) => console.log('Received:', data),
 *     onOpen: () => console.log('Connected'),
 *     onClose: () => console.log('Disconnected'),
 *     reconnectInterval: 3000,
 *     maxReconnectAttempts: 10
 *   });
 */

const useWebSocket = (url, options = {}) => {
    const {
        onOpen = () => {},
        onClose = () => {},
        onMessage = () => {},
        onError = () => {},
        reconnectInterval = 3000,
        maxReconnectAttempts = 10,
        heartbeatInterval = 30000,
        protocols = []
    } = options;

    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState(null);
    const [reconnectCount, setReconnectCount] = useState(0);

    const ws = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const heartbeatIntervalRef = useRef(null);
    const messageQueue = useRef([]);

    const connect = useCallback(() => {
        try {
            console.log('Connecting to WebSocket...');
            ws.current = new WebSocket(url, protocols);

            ws.current.onopen = (event) => {
                console.log('WebSocket connected');
                setIsConnected(true);
                setReconnectCount(0);

                // Send queued messages
                while (messageQueue.current.length > 0) {
                    const message = messageQueue.current.shift();
                    ws.current.send(message);
                }

                // Start heartbeat
                heartbeatIntervalRef.current = setInterval(() => {
                    if (ws.current?.readyState === WebSocket.OPEN) {
                        ws.current.send(JSON.stringify({ type: 'ping' }));
                    }
                }, heartbeatInterval);

                onOpen(event);
            };

            ws.current.onmessage = (event) => {
                const message = event.data;
                setLastMessage(message);

                // Parse JSON if possible
                try {
                    const data = JSON.parse(message);
                    onMessage(data);
                } catch (e) {
                    onMessage(message);
                }
            };

            ws.current.onerror = (error) => {
                console.error('WebSocket error:', error);
                onError(error);
            };

            ws.current.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                setIsConnected(false);

                // Clear heartbeat
                if (heartbeatIntervalRef.current) {
                    clearInterval(heartbeatIntervalRef.current);
                }

                onClose(event);

                // Attempt reconnection
                if (reconnectCount < maxReconnectAttempts) {
                    const delay = Math.min(
                        reconnectInterval * Math.pow(2, reconnectCount),
                        60000
                    );

                    console.log(`Reconnecting in ${delay}ms... (attempt ${reconnectCount + 1}/${maxReconnectAttempts})`);

                    reconnectTimeoutRef.current = setTimeout(() => {
                        setReconnectCount(prev => prev + 1);
                        connect();
                    }, delay);
                } else {
                    console.error('Max reconnection attempts reached');
                }
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            onError(error);
        }
    }, [url, reconnectCount, maxReconnectAttempts, reconnectInterval]);

    const sendMessage = useCallback((message) => {
        const data = typeof message === 'string' ? message : JSON.stringify(message);

        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(data);
        } else {
            console.warn('WebSocket not connected, queuing message');
            messageQueue.current.push(data);
        }
    }, []);

    const disconnect = useCallback(() => {
        console.log('Disconnecting WebSocket...');

        // Clear reconnection timeout
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }

        // Clear heartbeat
        if (heartbeatIntervalRef.current) {
            clearInterval(heartbeatIntervalRef.current);
        }

        // Close WebSocket
        if (ws.current) {
            ws.current.close(1000, 'Client disconnect');
        }

        setIsConnected(false);
    }, []);

    const reconnect = useCallback(() => {
        disconnect();
        setReconnectCount(0);
        setTimeout(connect, 100);
    }, [connect, disconnect]);

    useEffect(() => {
        connect();

        return () => {
            disconnect();
        };
    }, []);

    return {
        isConnected,
        lastMessage,
        sendMessage,
        disconnect,
        reconnect,
        readyState: ws.current?.readyState
    };
};

export default useWebSocket;


/**
 * Example Component
 */
export const ChatComponent = () => {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');

    const {
        isConnected,
        sendMessage
    } = useWebSocket('wss://example.com/ws', {
        onMessage: (data) => {
            if (data.type === 'chat') {
                setMessages(prev => [...prev, data]);
            }
        },
        onOpen: () => {
            console.log('Chat connected');
        },
        onClose: () => {
            console.log('Chat disconnected');
        }
    });

    const handleSend = () => {
        if (inputValue.trim() && isConnected) {
            sendMessage({
                type: 'chat',
                text: inputValue,
                timestamp: Date.now()
            });
            setInputValue('');
        }
    };

    return (
        <div className="chat-container">
            <div className="connection-status">
                Status: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </div>

            <div className="messages">
                {messages.map((msg, i) => (
                    <div key={i} className="message">
                        {msg.text}
                    </div>
                ))}
            </div>

            <div className="input-container">
                <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
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
};
