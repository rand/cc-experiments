#!/usr/bin/env python3
"""
WebSocket Server with Prometheus Metrics

Comprehensive monitoring of WebSocket server with Prometheus metrics:
- Active connections
- Messages sent/received
- Message latency
- Errors
- Connection duration

Usage:
    python prometheus_metrics.py
"""

import asyncio
import json
import logging
import time
from typing import Set
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Prometheus metrics
websocket_connections = Gauge(
    'websocket_connections_total',
    'Number of active WebSocket connections'
)

websocket_messages_sent = Counter(
    'websocket_messages_sent_total',
    'Total messages sent to clients'
)

websocket_messages_received = Counter(
    'websocket_messages_received_total',
    'Total messages received from clients'
)

websocket_message_latency = Histogram(
    'websocket_message_latency_seconds',
    'Message processing latency in seconds',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

websocket_connection_duration = Histogram(
    'websocket_connection_duration_seconds',
    'WebSocket connection duration in seconds',
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600, 7200, 14400, 28800, 43200, 86400)
)

websocket_errors = Counter(
    'websocket_errors_total',
    'Total WebSocket errors',
    ['error_type']
)

websocket_message_size_bytes = Histogram(
    'websocket_message_size_bytes',
    'Size of WebSocket messages in bytes',
    buckets=(10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000)
)


class MonitoredWebSocketServer:
    """WebSocket server with Prometheus metrics"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.client_connect_times = {}

    async def register(self, websocket: WebSocketServerProtocol):
        """Register new client"""
        self.clients.add(websocket)
        self.client_connect_times[websocket] = time.time()

        # Update metrics
        websocket_connections.inc()

        logger.info(f"Client connected. Total: {len(self.clients)}")

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister client"""
        self.clients.discard(websocket)

        # Record connection duration
        if websocket in self.client_connect_times:
            connect_time = self.client_connect_times.pop(websocket)
            duration = time.time() - connect_time
            websocket_connection_duration.observe(duration)

        # Update metrics
        websocket_connections.dec()

        logger.info(f"Client disconnected. Total: {len(self.clients)}")

    async def broadcast(self, message: str, exclude: WebSocketServerProtocol = None):
        """Broadcast message to all clients"""
        if not self.clients:
            return

        tasks = []
        for client in self.clients:
            if client != exclude and client.open:
                tasks.append(client.send(message))
                websocket_messages_sent.inc()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        """Handle client connection"""
        await self.register(websocket)

        try:
            async for message in websocket:
                # Measure processing time
                start_time = time.time()

                try:
                    # Track metrics
                    websocket_messages_received.inc()
                    websocket_message_size_bytes.observe(len(message))

                    # Parse message
                    data = json.loads(message)
                    await self.handle_message(websocket, data)

                    # Record latency
                    latency = time.time() - start_time
                    websocket_message_latency.observe(latency)

                except json.JSONDecodeError:
                    websocket_errors.labels(error_type='invalid_json').inc()
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
                except Exception as e:
                    websocket_errors.labels(error_type=type(e).__name__).inc()
                    logger.error(f"Error handling message: {e}")

        except websockets.exceptions.ConnectionClosedOK:
            websocket_errors.labels(error_type='connection_closed_ok').inc()
        except websockets.exceptions.ConnectionClosedError:
            websocket_errors.labels(error_type='connection_closed_error').inc()
        except Exception as e:
            websocket_errors.labels(error_type=type(e).__name__).inc()
            logger.error(f"Connection error: {e}")
        finally:
            await self.unregister(websocket)

    async def handle_message(self, websocket: WebSocketServerProtocol, data: dict):
        """Handle incoming message"""
        msg_type = data.get("type")

        if msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))
            websocket_messages_sent.inc()

        elif msg_type == "broadcast":
            await self.broadcast(json.dumps(data), exclude=websocket)

        elif msg_type == "echo":
            await websocket.send(json.dumps({
                "type": "echo",
                "data": data.get("data")
            }))
            websocket_messages_sent.inc()

        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {msg_type}"
            }))
            websocket_messages_sent.inc()

    async def run(self):
        """Start server"""
        # Start Prometheus metrics server
        start_http_server(9090)
        logger.info("Prometheus metrics server started on port 9090")

        # Start WebSocket server
        async with websockets.serve(
            self.handler,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10
        ):
            logger.info(f"WebSocket server running on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever


if __name__ == "__main__":
    server = MonitoredWebSocketServer()
    asyncio.run(server.run())
