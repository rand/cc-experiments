#!/usr/bin/env python3
"""
HTTP/3 0-RTT (Zero Round-Trip Time) Demonstration

Shows the performance benefits of 0-RTT connection resumption.

Requirements:
    pip install aioquic

Usage:
    # Generate certificates first
    openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes

    # Run demo
    python python_0rtt_demo.py --url https://cloudflare-quic.com
"""

import asyncio
import time
import ssl
from aioquic.asyncio import connect
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import HeadersReceived
from aioquic.quic.configuration import QuicConfiguration


async def test_1rtt_connection(host, port):
    """Test 1-RTT connection (standard handshake)"""
    configuration = QuicConfiguration(
        alpn_protocols=H3_ALPN,
        is_client=True,
        verify_mode=ssl.CERT_NONE,  # For demo only
    )

    start = time.time()
    async with connect(host, port, configuration=configuration) as client:
        http = H3Connection(client._quic)
        stream_id = client._quic.get_next_available_stream_id()

        headers = [
            (b":method", b"GET"),
            (b":scheme", b"https"),
            (b":authority", host.encode()),
            (b":path", b"/"),
        ]

        http.send_headers(stream_id=stream_id, headers=headers)

        # Wait for response
        while True:
            for event in client._quic.next_event():
                if isinstance(event, HeadersReceived):
                    duration = (time.time() - start) * 1000
                    return duration
            await asyncio.sleep(0.01)


async def test_0rtt_connection(host, port, session_ticket):
    """Test 0-RTT connection (zero round-trip)"""
    configuration = QuicConfiguration(
        alpn_protocols=H3_ALPN,
        is_client=True,
        verify_mode=ssl.CERT_NONE,
    )

    # Load session ticket for 0-RTT
    configuration.load_session_ticket(session_ticket)

    start = time.time()
    async with connect(host, port, configuration=configuration) as client:
        http = H3Connection(client._quic)
        stream_id = client._quic.get_next_available_stream_id()

        headers = [
            (b":method", b"GET"),
            (b":scheme", b"https"),
            (b":authority", host.encode()),
            (b":path", b"/"),
        ]

        http.send_headers(stream_id=stream_id, headers=headers)

        # Wait for response
        while True:
            for event in client._quic.next_event():
                if isinstance(event, HeadersReceived):
                    duration = (time.time() - start) * 1000
                    return duration
            await asyncio.sleep(0.01)


async def demo():
    """Run 0-RTT demonstration"""
    host = "cloudflare-quic.com"
    port = 443

    print("HTTP/3 0-RTT Demonstration")
    print("=" * 60)
    print()

    # Step 1: Initial connection to get session ticket
    print("Step 1: Initial connection (to obtain session ticket)")
    session_ticket = None

    def save_ticket(ticket):
        nonlocal session_ticket
        session_ticket = ticket

    configuration = QuicConfiguration(
        alpn_protocols=H3_ALPN,
        is_client=True,
        verify_mode=ssl.CERT_NONE,
        session_ticket_handler=save_ticket,
    )

    async with connect(host, port, configuration=configuration) as client:
        await asyncio.sleep(0.5)

    if not session_ticket:
        print("❌ Failed to obtain session ticket")
        return

    print("✓ Session ticket obtained")
    print()

    # Step 2: Test 1-RTT
    print("Step 2: Testing 1-RTT connection (standard handshake)")
    rtt_1_times = []
    for i in range(5):
        duration = await test_1rtt_connection(host, port)
        rtt_1_times.append(duration)
        print(f"  Iteration {i+1}: {duration:.2f}ms")

    avg_1rtt = sum(rtt_1_times) / len(rtt_1_times)
    print(f"Average 1-RTT: {avg_1rtt:.2f}ms")
    print()

    # Step 3: Test 0-RTT
    print("Step 3: Testing 0-RTT connection (zero round-trip)")
    rtt_0_times = []
    for i in range(5):
        duration = await test_0rtt_connection(host, port, session_ticket)
        rtt_0_times.append(duration)
        print(f"  Iteration {i+1}: {duration:.2f}ms")

    avg_0rtt = sum(rtt_0_times) / len(rtt_0_times)
    print(f"Average 0-RTT: {avg_0rtt:.2f}ms")
    print()

    # Step 4: Calculate improvement
    improvement = ((avg_1rtt - avg_0rtt) / avg_1rtt) * 100

    print("=" * 60)
    print("Results:")
    print(f"  1-RTT average: {avg_1rtt:.2f}ms")
    print(f"  0-RTT average: {avg_0rtt:.2f}ms")
    print(f"  Improvement: {improvement:.1f}%")
    print()
    print("Note: 0-RTT reduces connection latency by eliminating handshake")
    print("      Use only for idempotent requests (GET, not POST)")


if __name__ == "__main__":
    asyncio.run(demo())
