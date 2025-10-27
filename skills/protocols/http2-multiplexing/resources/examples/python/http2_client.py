#!/usr/bin/env python3
"""
Python HTTP/2 Client Examples

Complete examples demonstrating HTTP/2 client features:
- Multiplexed requests on single connection
- Header compression (HPACK)
- Server push handling
- Stream prioritization
- Concurrent requests

Requirements:
    pip install httpx h2
"""

import asyncio
import time
from typing import List, Dict
import httpx
from h2.connection import H2Connection
from h2.events import (
    ResponseReceived, DataReceived, StreamEnded,
    PushPromiseReceived, SettingsAcknowledged
)
import socket
import ssl


# ============================================================================
# Example 1: Basic HTTP/2 Request (httpx)
# ============================================================================

def basic_http2_request():
    """Simple HTTP/2 request using httpx."""
    print("Example 1: Basic HTTP/2 Request")
    print("-" * 50)

    # Create HTTP/2 client
    client = httpx.Client(http2=True)

    # Make request
    response = client.get('https://http2.golang.org/')

    print(f"Protocol: {response.http_version}")
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Body: {response.text[:100]}...")

    client.close()
    print()


# ============================================================================
# Example 2: Concurrent Requests (Multiplexing)
# ============================================================================

async def concurrent_requests():
    """Multiple concurrent requests on single HTTP/2 connection."""
    print("Example 2: Concurrent Requests (Multiplexing)")
    print("-" * 50)

    urls = [
        'https://http2.golang.org/',
        'https://http2.golang.org/reqinfo',
        'https://http2.golang.org/serverpush',
        'https://http2.golang.org/file/go.png',
    ]

    # All requests use same connection (multiplexed)
    async with httpx.AsyncClient(http2=True) as client:
        start_time = time.time()

        # Launch all requests concurrently
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)

        end_time = time.time()

        print(f"Completed {len(responses)} requests in {end_time - start_time:.2f}s")
        print(f"All requests used single HTTP/2 connection")

        for url, response in zip(urls, responses):
            print(f"  {url}: {response.status_code} ({len(response.content)} bytes)")

    print()


# ============================================================================
# Example 3: Low-Level HTTP/2 with h2 Library
# ============================================================================

class HTTP2Client:
    """Low-level HTTP/2 client using h2 library."""

    def __init__(self, hostname: str, port: int = 443):
        self.hostname = hostname
        self.port = port
        self.conn = H2Connection()
        self.socket = None
        self.responses: Dict[int, Dict] = {}

    def connect(self):
        """Establish TLS connection and HTTP/2 handshake."""
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Wrap with TLS
        context = ssl.create_default_context()
        context.set_alpn_protocols(['h2'])

        self.socket = context.wrap_socket(
            sock,
            server_hostname=self.hostname
        )

        # Connect
        self.socket.connect((self.hostname, self.port))

        # Verify ALPN negotiated h2
        negotiated = self.socket.selected_alpn_protocol()
        if negotiated != 'h2':
            raise Exception(f"ALPN failed: {negotiated}")

        print(f"Connected with ALPN: {negotiated}")

        # HTTP/2 connection preface
        self.conn.initiate_connection()
        self.socket.sendall(self.conn.data_to_send())

    def request(self, path: str, method: str = 'GET') -> int:
        """Send HTTP/2 request, return stream ID."""
        stream_id = self.conn.get_next_available_stream_id()

        headers = [
            (':method', method),
            (':path', path),
            (':scheme', 'https'),
            (':authority', self.hostname),
            ('user-agent', 'python-h2-client'),
        ]

        self.conn.send_headers(stream_id, headers, end_stream=True)
        self.socket.sendall(self.conn.data_to_send())

        # Initialize response storage
        self.responses[stream_id] = {
            'headers': {},
            'data': b'',
            'complete': False
        }

        return stream_id

    def receive_response(self, stream_id: int):
        """Receive response for given stream."""
        while not self.responses[stream_id]['complete']:
            data = self.socket.recv(65536)
            if not data:
                break

            events = self.conn.receive_data(data)

            for event in events:
                if isinstance(event, ResponseReceived):
                    if event.stream_id == stream_id:
                        headers = dict(event.headers)
                        self.responses[stream_id]['headers'] = headers
                        print(f"Stream {stream_id}: Received headers")

                elif isinstance(event, DataReceived):
                    if event.stream_id == stream_id:
                        self.responses[stream_id]['data'] += event.data
                        self.conn.acknowledge_received_data(
                            event.flow_controlled_length,
                            stream_id
                        )

                elif isinstance(event, StreamEnded):
                    if event.stream_id == stream_id:
                        self.responses[stream_id]['complete'] = True
                        print(f"Stream {stream_id}: Complete")

                elif isinstance(event, PushPromiseReceived):
                    print(f"Server push promised: {dict(event.headers)}")

            # Send any pending data (ACKs, window updates)
            self.socket.sendall(self.conn.data_to_send())

        return self.responses[stream_id]

    def close(self):
        """Close connection."""
        if self.socket:
            self.socket.close()


def low_level_http2():
    """Low-level HTTP/2 request using h2 library."""
    print("Example 3: Low-Level HTTP/2")
    print("-" * 50)

    client = HTTP2Client('http2.golang.org')
    client.connect()

    # Send request
    stream_id = client.request('/reqinfo')
    print(f"Sent request on stream {stream_id}")

    # Receive response
    response = client.receive_response(stream_id)

    print(f"Status: {response['headers'].get(b':status', b'').decode()}")
    print(f"Data: {response['data'][:200].decode()}...")

    client.close()
    print()


# ============================================================================
# Example 4: Parallel Requests with Performance Measurement
# ============================================================================

async def parallel_requests_benchmark():
    """Benchmark HTTP/2 multiplexing vs HTTP/1.1."""
    print("Example 4: HTTP/2 vs HTTP/1.1 Benchmark")
    print("-" * 50)

    urls = [f'https://http2.golang.org/file/gopher.png?{i}' for i in range(10)]

    # HTTP/2 (multiplexed)
    async with httpx.AsyncClient(http2=True) as client:
        start = time.time()
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        http2_time = time.time() - start

    print(f"HTTP/2: {len(responses)} requests in {http2_time:.2f}s")

    # HTTP/1.1 (6 connections max)
    async with httpx.AsyncClient(http2=False) as client:
        start = time.time()
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        http1_time = time.time() - start

    print(f"HTTP/1.1: {len(responses)} requests in {http1_time:.2f}s")
    print(f"HTTP/2 is {http1_time / http2_time:.1f}x faster")
    print()


# ============================================================================
# Example 5: Stream Prioritization
# ============================================================================

async def prioritized_requests():
    """Demonstrate stream prioritization."""
    print("Example 5: Stream Prioritization")
    print("-" * 50)

    # Critical resources (CSS)
    critical_urls = [
        'https://http2.golang.org/file/go.png',
    ]

    # Less critical (images)
    normal_urls = [
        'https://http2.golang.org/file/gopher.png',
        'https://http2.golang.org/file/gopher.png',
    ]

    async with httpx.AsyncClient(http2=True) as client:
        # Note: httpx doesn't expose priority API directly
        # In production, use h2 library for fine-grained control

        print("Requesting critical resources first...")
        start = time.time()

        # Request critical resources
        critical_tasks = [client.get(url) for url in critical_urls]
        critical_responses = await asyncio.gather(*critical_tasks)

        # Then request normal resources
        normal_tasks = [client.get(url) for url in normal_urls]
        normal_responses = await asyncio.gather(*normal_tasks)

        elapsed = time.time() - start

        print(f"Critical resources: {len(critical_responses)}")
        print(f"Normal resources: {len(normal_responses)}")
        print(f"Total time: {elapsed:.2f}s")

    print()


# ============================================================================
# Example 6: API Client with Authentication
# ============================================================================

class HTTP2APIClient:
    """HTTP/2 API client with authentication."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.Client(
            http2=True,
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30.0
        )

    def get(self, endpoint: str) -> Dict:
        """GET request."""
        url = f"{self.base_url}{endpoint}"
        response = self.client.get(url)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: Dict) -> Dict:
        """POST request."""
        url = f"{self.base_url}{endpoint}"
        response = self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()

    async def batch_get(self, endpoints: List[str]) -> List[Dict]:
        """Parallel GET requests (multiplexed)."""
        async with httpx.AsyncClient(
            http2=True,
            headers={'Authorization': f'Bearer {self.api_key}'},
            timeout=30.0
        ) as client:
            tasks = [
                client.get(f"{self.base_url}{endpoint}")
                for endpoint in endpoints
            ]
            responses = await asyncio.gather(*tasks)

            return [r.json() for r in responses if r.status_code == 200]

    def close(self):
        """Close client."""
        self.client.close()


def api_client_example():
    """API client example."""
    print("Example 6: API Client")
    print("-" * 50)

    # Note: This is a demonstration - replace with real API
    client = HTTP2APIClient(
        base_url='https://httpbin.org',
        api_key='demo_key_12345'
    )

    # Single request
    try:
        response = client.get('/get')
        print(f"Single request: {response.get('url')}")
    except Exception as e:
        print(f"Single request failed: {e}")

    # Batch requests (multiplexed)
    async def batch_demo():
        endpoints = ['/get', '/uuid', '/headers']
        responses = await client.batch_get(endpoints)
        print(f"Batch requests: {len(responses)} responses")

    try:
        asyncio.run(batch_demo())
    except Exception as e:
        print(f"Batch requests failed: {e}")

    client.close()
    print()


# ============================================================================
# Example 7: Connection Settings
# ============================================================================

async def connection_settings():
    """Demonstrate custom HTTP/2 settings."""
    print("Example 7: Custom Connection Settings")
    print("-" * 50)

    # Configure HTTP/2 settings
    limits = httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=30.0
    )

    async with httpx.AsyncClient(
        http2=True,
        limits=limits,
        timeout=httpx.Timeout(10.0)
    ) as client:
        response = await client.get('https://http2.golang.org/')
        print(f"Status: {response.status_code}")
        print(f"Protocol: {response.http_version}")

        # Connection details
        print(f"Connection pool: {limits.max_connections} max connections")

    print()


# ============================================================================
# Main Runner
# ============================================================================

def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("Python HTTP/2 Client Examples")
    print("=" * 70 + "\n")

    # Synchronous examples
    basic_http2_request()

    # Example with h2 library
    try:
        low_level_http2()
    except Exception as e:
        print(f"Low-level example failed: {e}\n")

    # API client example
    api_client_example()

    # Async examples
    print("Running async examples...")
    asyncio.run(concurrent_requests())
    asyncio.run(parallel_requests_benchmark())
    asyncio.run(prioritized_requests())
    asyncio.run(connection_settings())

    print("\n" + "=" * 70)
    print("All examples completed")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
