#!/usr/bin/env python3
"""QPACK Header Compression Analysis

Demonstrates QPACK compression efficiency vs uncompressed headers.
"""

import sys

def analyze_qpack():
    print("QPACK Header Compression Analysis")
    print("=" * 70)

    # Example HTTP headers
    headers = [
        (":method", "GET"),
        (":scheme", "https"),
        (":authority", "example.com"),
        (":path", "/api/users?id=123"),
        ("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
        ("accept", "application/json"),
        ("accept-encoding", "gzip, deflate, br"),
        ("accept-language", "en-US,en;q=0.9"),
        ("cache-control", "no-cache"),
        ("content-type", "application/json"),
    ]

    print("\nOriginal Headers:")
    uncompressed_size = 0
    for name, value in headers:
        line = f"  {name}: {value}"
        print(line)
        uncompressed_size += len(name) + len(value) + 4  # +4 for ": " and "\r\n"

    print(f"\nUncompressed size: {uncompressed_size} bytes")

    # QPACK compression (simulated)
    # Static table indices for common headers
    static_table = {
        ":method GET": 2,      # 2 bytes
        ":scheme https": 5,    # 2 bytes
        "accept application/json": -1,
        "content-type application/json": -1,
    }

    compressed_size = 0
    print("\nQPACK Encoding:")
    for name, value in headers:
        key = f"{name} {value}"
        if key in static_table and static_table[key] != -1:
            # Static table reference (2 bytes)
            compressed_size += 2
            print(f"  {name}: {value} → Static table index (2 bytes)")
        else:
            # Literal (name + value + overhead)
            literal_size = len(name) + len(value) + 3
            compressed_size += literal_size
            print(f"  {name}: {value} → Literal ({literal_size} bytes)")

    print(f"\nCompressed size: {compressed_size} bytes")
    ratio = (1 - compressed_size / uncompressed_size) * 100
    print(f"Compression ratio: {ratio:.1f}%")
    print(f"Bandwidth saved: {uncompressed_size - compressed_size} bytes")

    print("\n" + "=" * 70)
    print("QPACK Benefits:")
    print("  • Static table: Predefined common headers")
    print("  • Dynamic table: Learned headers during connection")
    print("  • No head-of-line blocking (unlike HPACK)")
    print("  • Independent streams with compression")

if __name__ == "__main__":
    analyze_qpack()
