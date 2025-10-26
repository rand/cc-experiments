---
name: nat-traversal
description: Building peer-to-peer applications
---



# NAT Traversal Techniques

**Use this skill when:**
- Building peer-to-peer applications
- Establishing direct connections through NAT
- Implementing WebRTC or similar protocols
- Avoiding relay servers for cost/performance
- Creating decentralized networks

## STUN (Session Traversal Utilities for NAT)

### Discover Public IP and Port

```python
import stun

# Discover public IP/port
nat_type, external_ip, external_port = stun.get_ip_info()

print(f"NAT Type: {nat_type}")
print(f"External IP: {external_ip}")
print(f"External Port: {external_port}")

# Use external IP/port for peer connection
```

### STUN Server

```python
# Using public STUN server
STUN_SERVER = "stun.l.google.com:19302"

import socket
import struct

def stun_request(server, port=19302):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # STUN Binding Request
    message = b'\x00\x01\x00\x00\x21\x12\xa4\x42' + b'\x00' * 12

    sock.sendto(message, (server, port))
    data, addr = sock.recvfrom(1024)

    # Parse STUN response for external IP/port
    return parse_stun_response(data)
```

## TURN (Traversal Using Relays around NAT)

### TURN Relay

```python
# When direct connection fails, use TURN relay
import asyncio
from aioice import Candidate, Connection

async def connect_with_turn():
    connection = Connection(ice_controlling=True)

    # Add TURN server
    await connection.gather_candidates(
        stun_server=("stun.example.com", 3478),
        turn_server=("turn.example.com", 3478),
        turn_username="user",
        turn_password="pass"
    )

    # Exchange candidates with peer
    # Then connect through relay if needed
```

## ICE (Interactive Connectivity Establishment)

### ICE Implementation

```python
import asyncio
from aiortc import RTCPeerConnection, RTCConfiguration, RTCIceServer

async def create_peer_connection():
    config = RTCConfiguration(
        iceServers=[
            RTCIceServer(urls="stun:stun.l.google.com:19302"),
            RTCIceServer(
                urls="turn:turn.example.com:3478",
                username="user",
                credential="pass"
            )
        ]
    )

    pc = RTCPeerConnection(configuration=config)

    # ICE candidate gathering
    @pc.on("icecandidate")
    def on_icecandidate(candidate):
        if candidate:
            # Send candidate to peer via signaling
            send_to_peer({"candidate": candidate})

    # Create offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    return pc
```

## UDP Hole Punching

### Simultaneous UDP

```python
import socket
import threading

def udp_hole_punch(peer_addr, local_port=0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', local_port))

    # Send empty packet to create hole
    sock.sendto(b'', peer_addr)

    # Both peers send simultaneously
    # Creates mapping in both NATs

    return sock

# Usage (coordinated via signaling server)
# Peer A: sock = udp_hole_punch(('peer_b_ip', peer_b_port))
# Peer B: sock = udp_hole_punch(('peer_a_ip', peer_a_port))

# Then communicate directly
```

## Signaling Server

### WebSocket Signaling

```python
import asyncio
import websockets
import json

peers = {}

async def signaling_handler(websocket, path):
    peer_id = None

    try:
        async for message in websocket:
            data = json.loads(message)

            if data['type'] == 'register':
                peer_id = data['peer_id']
                peers[peer_id] = websocket

            elif data['type'] == 'offer':
                # Forward offer to target peer
                target = data['target']
                if target in peers:
                    await peers[target].send(json.dumps({
                        'type': 'offer',
                        'from': peer_id,
                        'sdp': data['sdp']
                    }))

            elif data['type'] == 'answer':
                # Forward answer
                target = data['target']
                if target in peers:
                    await peers[target].send(json.dumps({
                        'type': 'answer',
                        'from': peer_id,
                        'sdp': data['sdp']
                    }))

    finally:
        if peer_id and peer_id in peers:
            del peers[peer_id]

# Run signaling server
async def main():
    async with websockets.serve(signaling_handler, "0.0.0.0", 8080):
        await asyncio.Future()

asyncio.run(main())
```

## NAT Type Detection

### Determine NAT Behavior

```python
def detect_nat_type():
    # Full cone NAT: Port mapping same for all destinations
    # Restricted cone: IP filtering
    # Port restricted: IP+Port filtering
    # Symmetric: Different mapping per destination

    import stun
    nat_type, ext_ip, ext_port = stun.get_ip_info()

    return nat_type

# Traversal difficulty:
# Full cone: Easy (simple hole punching)
# Restricted cone: Medium (need simultaneous UDP)
# Port restricted: Hard (precise timing needed)
# Symmetric: Very hard (need TURN relay)
```

## Related Skills

- **tailscale-vpn.md** - Tailscale handles NAT traversal automatically
- **network-resilience-patterns.md** - Fallback strategies
