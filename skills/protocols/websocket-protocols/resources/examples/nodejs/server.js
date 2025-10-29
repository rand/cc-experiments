#!/usr/bin/env node
/**
 * Production-Ready WebSocket Server (Node.js)
 *
 * Features:
 * - WebSocket server using 'ws' library
 * - Connection management
 * - Heartbeat monitoring
 * - Broadcast messaging
 * - Graceful shutdown
 */

const WebSocket = require('ws');
const http = require('http');

class WebSocketServer {
    constructor(port = 8080) {
        this.port = port;
        this.clients = new Set();
        this.server = http.createServer();
        this.wss = new WebSocket.Server({ server: this.server });
    }

    start() {
        this.wss.on('connection', (ws, req) => {
            console.log(`Client connected from ${req.socket.remoteAddress}`);
            this.handleConnection(ws);
        });

        this.server.listen(this.port, () => {
            console.log(`WebSocket server listening on port ${this.port}`);
        });

        // Start heartbeat
        this.startHeartbeat();

        // Graceful shutdown
        process.on('SIGTERM', () => this.shutdown());
        process.on('SIGINT', () => this.shutdown());
    }

    handleConnection(ws) {
        this.clients.add(ws);

        // Setup heartbeat
        ws.isAlive = true;
        ws.on('pong', () => {
            ws.isAlive = true;
        });

        // Handle messages
        ws.on('message', (data) => {
            try {
                const message = JSON.parse(data);
                this.handleMessage(ws, message);
            } catch (error) {
                ws.send(JSON.stringify({
                    type: 'error',
                    message: 'Invalid JSON'
                }));
            }
        });

        // Handle close
        ws.on('close', () => {
            console.log('Client disconnected');
            this.clients.delete(ws);
        });

        // Handle errors
        ws.on('error', (error) => {
            console.error('WebSocket error:', error);
            this.clients.delete(ws);
        });
    }

    handleMessage(ws, data) {
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
            this.server.close(() => {
                console.log('Server closed');
                process.exit(0);
            });
        });
    }
}

// Start server
const port = process.env.PORT || 8080;
const server = new WebSocketServer(port);
server.start();
