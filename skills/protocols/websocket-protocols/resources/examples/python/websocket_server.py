#!/usr/bin/env python3
"""
Production-Ready WebSocket Server (Python)

Complete WebSocket server with:
- Connection management
- Broadcast messaging
- Authentication
- Rate limiting
- Heartbeat monitoring
- Graceful shutdown

Usage:
    python websocket_server.py
    python websocket_server.py --host 0.0.0.0 --port 8765
"""

import asyncio
import json
import logging
import signal
import time
from typing import Set, Dict
from collections import defaultdict
import websockets
from websockets.server import WebSocketServerProtocol
import jwt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, max_per_minute: int = 60):
        self.max_per_minute = max_per_minute
        self.client_counts = defaultdict(lambda: {'count': 0, 'reset_time': time.time() + 60})

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        client_data = self.client_counts[client_id]

        if now > client_data['reset_time']:
            client_data['count'] = 0
            client_data['reset_time'] = now + 60

        client_data['count'] += 1
        return client_data['count'] <= self.max_per_minute


class WebSocketServer:
    """Production WebSocket server"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        jwt_secret: str = "your-secret-key"
    ):
        self.host = host
        self.port = port
        self.jwt_secret = jwt_secret
        self.clients: Set[WebSocketServerProtocol] = set()
        self.user_clients: Dict[str, WebSocketServerProtocol] = {}
        self.rate_limiter = RateLimiter(max_per_minute=60)
        self.running = True

    async def register(self, websocket: WebSocketServerProtocol, user_id: str):
        """Register authenticated client"""
        self.clients.add(websocket)
        self.user_clients[user_id] = websocket
        logger.info(f"Client registered: {user_id}. Total: {len(self.clients)}")

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister client"""
        self.clients.discard(websocket)
        user_id = next((uid for uid, ws in self.user_clients.items() if ws == websocket), None)
        if user_id:
            self.user_clients.pop(user_id, None)
        logger.info(f"Client unregistered. Total: {len(self.clients)}")

    async def authenticate(self, websocket: WebSocketServerProtocol) -> str:
        """Authenticate client"""
        try:
            auth_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(auth_msg)

            if data.get("type") != "auth":
                await websocket.close(code=4000, reason="Auth required")
                return None

            token = data.get("token")
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")

            await websocket.send(json.dumps({
                "type": "auth_success",
                "user_id": user_id
            }))

            return user_id

        except asyncio.TimeoutError:
            await websocket.close(code=4003, reason="Auth timeout")
            return None
        except (json.JSONDecodeError, jwt.InvalidTokenError) as e:
            await websocket.close(code=4001, reason="Auth failed")
            return None

    async def broadcast(self, message: str, exclude: WebSocketServerProtocol = None):
        """Broadcast to all clients"""
        if not self.clients:
            return

        tasks = [
            client.send(message)
            for client in self.clients
            if client != exclude and client.open
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        """Handle client connection"""
        # Authenticate
        user_id = await self.authenticate(websocket)
        if not user_id:
            return

        await self.register(websocket, user_id)

        try:
            async for message in websocket:
                # Rate limiting
                if not self.rate_limiter.is_allowed(user_id):
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Rate limit exceeded"
                    }))
                    continue

                # Parse message
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, user_id, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed for user: {user_id}")
        finally:
            await self.unregister(websocket)

    async def handle_message(self, websocket: WebSocketServerProtocol, user_id: str, data: dict):
        """Handle incoming message"""
        msg_type = data.get("type")

        if msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))

        elif msg_type == "broadcast":
            await self.broadcast(json.dumps({
                "type": "broadcast",
                "from": user_id,
                "data": data.get("data")
            }), exclude=websocket)

        elif msg_type == "echo":
            await websocket.send(json.dumps({
                "type": "echo",
                "data": data.get("data")
            }))

        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {msg_type}"
            }))

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down server...")
        self.running = False

        close_tasks = [
            client.close(code=1001, reason="Server shutting down")
            for client in self.clients
        ]

        await asyncio.gather(*close_tasks, return_exceptions=True)
        logger.info("Server shutdown complete")

    async def run(self):
        """Start server"""
        async with websockets.serve(
            self.handler,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
            max_size=10 * 1024 * 1024
        ):
            logger.info(f"WebSocket server running on ws://{self.host}:{self.port}")

            # Setup signal handlers
            loop = asyncio.get_running_loop()
            stop = loop.create_future()

            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, stop.set_result, None)

            # Wait for shutdown signal
            await stop

            # Graceful shutdown
            await self.shutdown()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WebSocket Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8765, help="Port number")
    parser.add_argument("--jwt-secret", default="your-secret-key", help="JWT secret")

    args = parser.parse_args()

    server = WebSocketServer(args.host, args.port, args.jwt_secret)
    asyncio.run(server.run())
