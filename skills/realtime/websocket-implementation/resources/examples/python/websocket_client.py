#!/usr/bin/env python3
"""
WebSocket Client Example (Python)

Demonstrates a robust WebSocket client with reconnection, message queueing,
and heartbeat detection using the 'websockets' library.

Installation:
    pip install websockets

Usage:
    python websocket_client.py
    python websocket_client.py --url wss://api.example.com/ws
"""

import asyncio
import json
import logging
import signal
import time
from typing import Optional, Callable, Any
import websockets
from websockets.client import WebSocketClientProtocol


# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class RobustWebSocketClient:
    """Robust WebSocket client with reconnection and message queueing"""

    def __init__(
        self,
        url: str,
        reconnect: bool = True,
        reconnect_interval: float = 1.0,
        max_reconnect_interval: float = 30.0,
        max_reconnect_attempts: int = float('inf'),
        heartbeat_interval: float = 30.0,
        max_queue_size: int = 100
    ):
        self.url = url
        self.ws: Optional[WebSocketClientProtocol] = None

        # Reconnection settings
        self.reconnect_enabled = reconnect
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_interval = max_reconnect_interval
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = max_reconnect_attempts

        # Heartbeat settings
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_task: Optional[asyncio.Task] = None

        # Message queue
        self.message_queue = []
        self.max_queue_size = max_queue_size

        # State
        self.state = 'disconnected'  # disconnected, connecting, connected, reconnecting
        self.running = False

        # Event callbacks
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    async def connect(self):
        """Connect to WebSocket server"""
        if self.state in ('connecting', 'connected'):
            logger.warning('Already connected or connecting')
            return

        self.state = 'connecting'
        logger.info(f'Connecting to {self.url}...')

        try:
            self.ws = await websockets.connect(self.url)
            self.state = 'connected'
            self.reconnect_attempts = 0

            logger.info('Connected successfully')

            if self.on_connected:
                await self.on_connected()

            # Flush queued messages
            await self.flush_queue()

            # Start heartbeat
            self.start_heartbeat()

            # Start message listener
            await self.listen()

        except Exception as e:
            logger.error(f'Connection failed: {e}')
            self.state = 'disconnected'

            if self.on_error:
                await self.on_error(e)

            if self.reconnect_enabled:
                await self.reconnect()

    async def disconnect(self):
        """Disconnect from WebSocket server"""
        logger.info('Disconnecting...')

        self.reconnect_enabled = False
        self.running = False
        self.stop_heartbeat()

        if self.ws:
            await self.ws.close(code=1000, reason='Client disconnect')

        self.state = 'disconnected'

    async def send(self, data: Any):
        """Send message to server"""
        if self.ws and self.state == 'connected':
            try:
                payload = data if isinstance(data, str) else json.dumps(data)
                await self.ws.send(payload)
                logger.debug(f'Sent: {payload}')
            except Exception as e:
                logger.error(f'Send error: {e}')
                self.queue_message(data)
        else:
            logger.debug('Not connected, queueing message')
            self.queue_message(data)

    def queue_message(self, data: Any):
        """Queue message for later sending"""
        if len(self.message_queue) >= self.max_queue_size:
            logger.warning('Message queue full, dropping oldest message')
            self.message_queue.pop(0)

        self.message_queue.append(data)

    async def flush_queue(self):
        """Send all queued messages"""
        if not self.message_queue:
            return

        logger.info(f'Flushing message queue ({len(self.message_queue)} messages)')

        while self.message_queue and self.state == 'connected':
            message = self.message_queue.pop(0)
            await self.send(message)

    async def listen(self):
        """Listen for incoming messages"""
        try:
            async for message in self.ws:
                logger.debug(f'Received: {message}')

                # Try to parse as JSON
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    data = message

                if self.on_message:
                    await self.on_message(data)

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f'Connection closed: code={e.code}, reason={e.reason}')

            self.state = 'disconnected'
            self.stop_heartbeat()

            if self.on_disconnected:
                await self.on_disconnected(e.code, e.reason)

            # Reconnect if not normal closure
            if self.reconnect_enabled and e.code != 1000:
                await self.reconnect()

        except Exception as e:
            logger.error(f'Listen error: {e}')

            if self.on_error:
                await self.on_error(e)

            if self.reconnect_enabled:
                await self.reconnect()

    async def reconnect(self):
        """Reconnect to server with exponential backoff"""
        if not self.reconnect_enabled:
            logger.info('Reconnection disabled')
            return

        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error('Max reconnection attempts reached')
            return

        self.reconnect_attempts += 1

        # Exponential backoff with jitter
        delay = min(
            self.reconnect_interval * (2 ** (self.reconnect_attempts - 1)),
            self.max_reconnect_interval
        )
        jitter = delay * 0.1 * (2 * asyncio.get_event_loop().time() % 1 - 0.5)
        actual_delay = delay + jitter

        logger.info(f'Reconnecting in {actual_delay:.2f}s (attempt {self.reconnect_attempts})')

        self.state = 'reconnecting'

        await asyncio.sleep(actual_delay)
        await self.connect()

    def start_heartbeat(self):
        """Start heartbeat task"""
        self.stop_heartbeat()

        async def heartbeat():
            while self.state == 'connected':
                try:
                    logger.debug('Sending ping...')
                    pong = await self.ws.ping()
                    await asyncio.wait_for(pong, timeout=5.0)
                    logger.debug('Received pong')
                except asyncio.TimeoutError:
                    logger.warning('Heartbeat timeout, reconnecting...')
                    if self.ws:
                        await self.ws.close()
                    break
                except Exception as e:
                    logger.error(f'Heartbeat error: {e}')
                    break

                await asyncio.sleep(self.heartbeat_interval)

        self.heartbeat_task = asyncio.create_task(heartbeat())

    def stop_heartbeat(self):
        """Stop heartbeat task"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None

    async def run(self):
        """Run the client (main loop)"""
        self.running = True
        await self.connect()

    def get_state(self) -> str:
        """Get current connection state"""
        return self.state


async def example_usage():
    """Example usage of RobustWebSocketClient"""
    import argparse

    parser = argparse.ArgumentParser(description='WebSocket Client')
    parser.add_argument('--url', default='ws://localhost:8080', help='WebSocket URL')
    args = parser.parse_args()

    client = RobustWebSocketClient(
        url=args.url,
        reconnect=True,
        reconnect_interval=1.0,
        max_reconnect_interval=30.0,
        heartbeat_interval=30.0
    )

    # Event handlers
    async def on_connected():
        logger.info('[EVENT] Connected!')

        # Join a room
        await client.send({
            'type': 'join',
            'room': 'test-room'
        })

        # Send periodic messages
        async def send_periodic():
            while client.get_state() == 'connected':
                await client.send({
                    'type': 'message',
                    'content': f'Hello at {time.time()}'
                })
                await asyncio.sleep(5)

        asyncio.create_task(send_periodic())

    async def on_disconnected(code, reason):
        logger.info(f'[EVENT] Disconnected: {code} - {reason}')

    async def on_message(data):
        logger.info(f'[EVENT] Message: {data}')

    async def on_error(error):
        logger.error(f'[EVENT] Error: {error}')

    # Set callbacks
    client.on_connected = on_connected
    client.on_disconnected = on_disconnected
    client.on_message = on_message
    client.on_error = on_error

    # Graceful shutdown
    loop = asyncio.get_event_loop()

    def shutdown():
        logger.info('Shutting down...')
        asyncio.create_task(client.disconnect())
        loop.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown)

    # Run client
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info('Interrupted by user')
        await client.disconnect()


if __name__ == '__main__':
    asyncio.run(example_usage())
