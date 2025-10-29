#!/usr/bin/env python3
"""
Horizontally Scalable WebSocket Server using Redis Pub/Sub

Allows multiple WebSocket server instances to communicate via Redis,
enabling broadcasting across all connected clients regardless of which
server they're connected to.

Usage:
    python redis_pubsub_server.py --port 8765
    python redis_pubsub_server.py --port 8766  # Run multiple instances
"""

import asyncio
import json
import logging
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScalableWebSocketServer:
    """WebSocket server with Redis pub/sub for horizontal scaling"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        server_id: str = None
    ):
        self.host = host
        self.port = port
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.server_id = server_id or f"{host}:{port}"

        self.clients: Set[WebSocketServerProtocol] = set()
        self.redis_client = None
        self.pubsub = None

    async def connect_redis(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")

            # Subscribe to broadcast channel
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe('websocket_broadcast')
            logger.info("Subscribed to Redis broadcast channel")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def redis_listener(self):
        """Listen for messages from Redis pub/sub"""
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    data = message['data']

                    # Parse message
                    try:
                        msg = json.loads(data)

                        # Skip messages from this server
                        if msg.get('server_id') == self.server_id:
                            continue

                        # Broadcast to local clients
                        await self.local_broadcast(json.dumps(msg.get('payload')))

                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON from Redis: {data}")

        except Exception as e:
            logger.error(f"Redis listener error: {e}")

    async def local_broadcast(self, message: str):
        """Broadcast to local clients only"""
        if not self.clients:
            return

        tasks = [
            client.send(message)
            for client in self.clients
            if client.open
        ]

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            errors = sum(1 for r in results if isinstance(r, Exception))
            if errors > 0:
                logger.warning(f"Failed to send to {errors} clients")

    async def global_broadcast(self, message: dict):
        """Broadcast to all servers via Redis"""
        try:
            # Wrap message with server ID
            wrapped = {
                'server_id': self.server_id,
                'payload': message
            }

            # Publish to Redis
            await self.redis_client.publish('websocket_broadcast', json.dumps(wrapped))

        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")

    async def register(self, websocket: WebSocketServerProtocol):
        """Register new client"""
        self.clients.add(websocket)
        logger.info(f"[{self.server_id}] Client connected. Total: {len(self.clients)}")

        # Publish connection event
        await self.global_broadcast({
            'type': 'server_event',
            'event': 'client_connected',
            'total_clients': len(self.clients)
        })

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister client"""
        self.clients.discard(websocket)
        logger.info(f"[{self.server_id}] Client disconnected. Total: {len(self.clients)}")

        # Publish disconnection event
        await self.global_broadcast({
            'type': 'server_event',
            'event': 'client_disconnected',
            'total_clients': len(self.clients)
        })

    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        """Handle client connection"""
        await self.register(websocket)

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "broadcast":
                        # Broadcast globally via Redis
                        await self.global_broadcast({
                            'type': 'broadcast',
                            'data': data.get('data'),
                            'timestamp': asyncio.get_event_loop().time()
                        })

                    elif msg_type == "ping":
                        # Local response
                        await websocket.send(json.dumps({
                            "type": "pong",
                            "server_id": self.server_id
                        }))

                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": f"Unknown message type: {msg_type}"
                        }))

                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def run(self):
        """Start server"""
        # Connect to Redis
        await self.connect_redis()

        # Start Redis listener
        listener_task = asyncio.create_task(self.redis_listener())

        # Start WebSocket server
        async with websockets.serve(
            self.handler,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10
        ):
            logger.info(f"[{self.server_id}] WebSocket server running on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scalable WebSocket Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8765, help="Port number")
    parser.add_argument("--redis-host", default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")
    parser.add_argument("--server-id", help="Server ID (default: host:port)")

    args = parser.parse_args()

    server = ScalableWebSocketServer(
        args.host,
        args.port,
        args.redis_host,
        args.redis_port,
        args.server_id
    )

    asyncio.run(server.run())
