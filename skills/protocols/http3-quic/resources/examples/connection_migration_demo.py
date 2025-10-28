#!/usr/bin/env python3
"""HTTP/3 Connection Migration Demonstration

Shows how QUIC connections survive network changes (IP/port changes).
"""

import asyncio
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration
from aioquic.h3.connection import H3_ALPN
import ssl

async def demo():
    print("HTTP/3 Connection Migration Demo")
    print("=" * 60)
    print("\nConnection migration allows QUIC connections to survive:")
    print("  - WiFi ↔ Cellular switches")
    print("  - NAT rebinding")
    print("  - IP address changes")
    print("\nConnection ID: Identifies connection (not IP:port)\n")

    configuration = QuicConfiguration(
        alpn_protocols=H3_ALPN,
        is_client=True,
        verify_mode=ssl.CERT_NONE,
    )

    async with connect("cloudflare-quic.com", 443, configuration=configuration) as client:
        conn_id = client._quic._peer_cid
        print(f"✓ Connected with Connection ID: {conn_id.hex()}")
        print(f"  Local: {client._local}")
        print(f"  Remote: {client._remote}")
        print("\nConnection survives network changes (same Connection ID)")
        print("Note: Full demo requires network interface changes")

if __name__ == "__main__":
    asyncio.run(demo())
