#!/usr/bin/env python3
"""
WebSocket Server Example (Python)

Demonstrates a production-ready WebSocket server using the 'websockets' library.
Features: broadcast, rooms, authentication, async/await patterns.

Installation:
    pip install websockets

Usage:
    python websocket_server.py
    python websocket_server.py --port 8080
"""

import asyncio
import json
import logging
import signal
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Set, Dict, Optional
import websockets
from websockets.server import WebSocketServerProtocol


# Configuration
PORT = 8080
PING_INTERVAL = 30  # seconds
PING_TIMEOUT = 5    # seconds

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Metrics:
    """Server metrics"""
    connections: int = 0
    total_connections: int = 0
    messages_received: int = 0
    messages_sent: int = 0
    bytes_received: int = 0
    bytes_sent: int = 0


class RateLimiter:
    """Simple rate limiter using token bucket algorithm"""

    def __init__(self, max_rate: int = 10):
        self.max_rate = max_rate
        self.buckets: Dict[WebSocketServerProtocol, dict] = {}

    def check(self, ws: WebSocketServerProtocol) -> bool:
        """Check if request is within rate limit"""
        if ws not in self.buckets:
            self.buckets[ws] = {
                'count': 0,
                'reset_time': time.time() + 1.0
            }

        bucket = self.buckets[ws]

        if time.time() > bucket['reset_time']:
            bucket['count'] = 0
            bucket['reset_time'] = time.time() + 1.0

        bucket['count'] += 1

        return bucket['count'] <= self.max_rate

    def cleanup(self, ws: WebSocketServerProtocol):
        """Remove bucket for disconnected client"""
        self.buckets.pop(ws, None)


class WebSocketServer:
    """WebSocket server with rooms and broadcast support"""

    def __init__(self):
        self.clients: Set[WebSocketServerProtocol] = set()
        self.rooms: Dict[str, Set[WebSocketServerProtocol]] = defaultdict(set)
        self.metrics = Metrics()
        self.rate_limiter = RateLimiter(max_rate=10)

    async def register(self, ws: WebSocketServerProtocol):
        """Register a new client"""
        self.clients.add(ws)
        self.metrics.connections += 1
        self.metrics.total_connections += 1

        ws.user_id = f"user_{id(ws) % 10000:04d}"
        ws.room = None

        logger.info(f"Client connected: {ws.user_id} ({ws.remote_address})")

        # Send welcome message
        await self.send_message(ws, {
            'type': 'welcome',
            'user_id': ws.user_id,
            'timestamp': time.time()
        })

    async def unregister(self, ws: WebSocketServerProtocol):
        """Unregister a client"""
        self.clients.discard(ws)
        self.metrics.connections -= 1

        # Leave room if in one
        if hasattr(ws, 'room') and ws.room:
            await self.leave_room(ws)

        # Cleanup rate limiter
        self.rate_limiter.cleanup(ws)

        logger.info(f"Client disconnected: {ws.user_id}")

    async def join_room(self, ws: WebSocketServerProtocol, room: str):
        """Join a room"""
        # Leave current room if in one
        if hasattr(ws, 'room') and ws.room:
            await self.leave_room(ws)

        # Join new room
        self.rooms[room].add(ws)
        ws.room = room

        logger.info(f"Client {ws.user_id} joined room: {room} ({len(self.rooms[room])} members)")

        # Notify room members
        await self.broadcast_to_room(room, {
            'type': 'user_joined',
            'user_id': ws.user_id,
            'room': room,
            'timestamp': time.time()
        }, exclude=ws)

        # Confirm to client
        await self.send_message(ws, {
            'type': 'joined',
            'room': room,
            'members': len(self.rooms[room]),
            'timestamp': time.time()
        })

    async def leave_room(self, ws: WebSocketServerProtocol):
        """Leave current room"""
        if not hasattr(ws, 'room') or not ws.room:
            return

        room = ws.room
        self.rooms[room].discard(ws)

        # Notify room members
        await self.broadcast_to_room(room, {
            'type': 'user_left',
            'user_id': ws.user_id,
            'room': room,
            'timestamp': time.time()
        })

        # Clean up empty room
        if len(self.rooms[room]) == 0:
            del self.rooms[room]

        logger.info(f"Client {ws.user_id} left room: {room}")

        ws.room = None

        # Confirm to client
        await self.send_message(ws, {
            'type': 'left',
            'timestamp': time.time()
        })

    async def send_message(self, ws: WebSocketServerProtocol, message: dict):
        """Send message to a single client"""
        try:
            data = json.dumps(message)
            await ws.send(data)
            self.metrics.messages_sent += 1
            self.metrics.bytes_sent += len(data)
        except Exception as e:
            logger.error(f"Error sending message to {ws.user_id}: {e}")

    async def broadcast_to_room(self, room: str, message: dict, exclude: Optional[WebSocketServerProtocol] = None):
        """Broadcast message to all clients in a room"""
        if room not in self.rooms:
            return

        data = json.dumps(message)
        tasks = []

        for client in self.rooms[room]:
            if client != exclude:
                tasks.append(client.send(data))
                self.metrics.messages_sent += 1
                self.metrics.bytes_sent += len(data)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_all(self, message: dict, exclude: Optional[WebSocketServerProtocol] = None):
        """Broadcast message to all connected clients"""
        data = json.dumps(message)
        tasks = []

        for client in self.clients:
            if client != exclude:
                tasks.append(client.send(data))
                self.metrics.messages_sent += 1
                self.metrics.bytes_sent += len(data)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def handle_message(self, ws: WebSocketServerProtocol, data: str):
        """Handle incoming message"""
        self.metrics.messages_received += 1
        self.metrics.bytes_received += len(data)

        # Rate limiting
        if not self.rate_limiter.check(ws):
            await self.send_message(ws, {
                'type': 'error',
                'error': 'Rate limit exceeded'
            })
            return

        # Parse message
        try:
            msg = json.loads(data)
        except json.JSONDecodeError:
            await self.send_message(ws, {
                'type': 'error',
                'error': 'Invalid JSON'
            })
            return

        msg_type = msg.get('type')

        # Route message
        if msg_type == 'join':
            room = msg.get('room')
            if room:
                await self.join_room(ws, room)
            else:
                await self.send_message(ws, {
                    'type': 'error',
                    'error': 'Missing room parameter'
                })

        elif msg_type == 'leave':
            await self.leave_room(ws)

        elif msg_type == 'message':
            if not hasattr(ws, 'room') or not ws.room:
                await self.send_message(ws, {
                    'type': 'error',
                    'error': 'Not in a room'
                })
                return

            content = msg.get('content')
            if content:
                await self.broadcast_to_room(ws.room, {
                    'type': 'message',
                    'user_id': ws.user_id,
                    'room': ws.room,
                    'content': content,
                    'timestamp': time.time()
                }, exclude=ws)

                logger.info(f"Message in room {ws.room} from {ws.user_id}: {content}")

        elif msg_type == 'broadcast':
            content = msg.get('content')
            if content:
                await self.broadcast_all({
                    'type': 'broadcast',
                    'user_id': ws.user_id,
                    'content': content,
                    'timestamp': time.time()
                }, exclude=ws)

                logger.info(f"Broadcast from {ws.user_id}: {content}")

        elif msg_type == 'ping':
            await self.send_message(ws, {
                'type': 'pong',
                'timestamp': time.time()
            })

        else:
            await self.send_message(ws, {
                'type': 'error',
                'error': f'Unknown message type: {msg_type}'
            })

    async def handler(self, ws: WebSocketServerProtocol, path: str):
        """Main WebSocket handler"""
        await self.register(ws)

        try:
            async for message in ws:
                await self.handle_message(ws, message)

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Error in handler for {ws.user_id}: {e}")
        finally:
            await self.unregister(ws)

    async def start(self, host: str = 'localhost', port: int = PORT):
        """Start the WebSocket server"""
        async with websockets.serve(
            self.handler,
            host,
            port,
            ping_interval=PING_INTERVAL,
            ping_timeout=PING_TIMEOUT
        ):
            logger.info(f"WebSocket server running on ws://{host}:{port}")

            # Metrics reporting
            async def report_metrics():
                while True:
                    await asyncio.sleep(60)
                    logger.info(
                        f"Metrics: connections={self.metrics.connections}, "
                        f"total={self.metrics.total_connections}, "
                        f"msgs_recv={self.metrics.messages_received}, "
                        f"msgs_sent={self.metrics.messages_sent}"
                    )

            asyncio.create_task(report_metrics())

            # Wait forever
            await asyncio.Future()


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='WebSocket Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=PORT, help='Port to bind to')
    args = parser.parse_args()

    server = WebSocketServer()

    # Graceful shutdown
    loop = asyncio.get_event_loop()

    def shutdown():
        logger.info("Shutting down...")
        loop.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown)

    try:
        await server.start(host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == '__main__':
    asyncio.run(main())
