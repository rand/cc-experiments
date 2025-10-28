#!/usr/bin/env python3
"""
HPACK Header Compression Analyzer

Analyzes HTTP/2 HPACK compression efficiency by simulating compression
of HTTP headers across multiple requests on the same connection.

Features:
- Static table lookup (RFC 7541)
- Dynamic table simulation
- Huffman encoding analysis
- Compression ratio calculation
- Visual representation of compression gains

Usage:
    python analyze_hpack.py --requests headers.txt
    python analyze_hpack.py --requests headers.txt --json output.json
    python analyze_hpack.py --demo
    python analyze_hpack.py --help
"""

import argparse
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import OrderedDict


# RFC 7541 Static Table (first 61 entries)
STATIC_TABLE = {
    # Pseudo-headers
    1: (":authority", ""),
    2: (":method", "GET"),
    3: (":method", "POST"),
    4: (":path", "/"),
    5: (":path", "/index.html"),
    6: (":scheme", "http"),
    7: (":scheme", "https"),
    8: (":status", "200"),
    9: (":status", "204"),
    10: (":status", "206"),
    11: (":status", "304"),
    12: (":status", "400"),
    13: (":status", "404"),
    14: (":status", "500"),
    # Common headers
    15: ("accept-charset", ""),
    16: ("accept-encoding", "gzip, deflate"),
    17: ("accept-language", ""),
    18: ("accept-ranges", ""),
    19: ("accept", ""),
    20: ("access-control-allow-origin", ""),
    21: ("age", ""),
    22: ("allow", ""),
    23: ("authorization", ""),
    24: ("cache-control", ""),
    25: ("content-disposition", ""),
    26: ("content-encoding", ""),
    27: ("content-language", ""),
    28: ("content-length", ""),
    29: ("content-location", ""),
    30: ("content-range", ""),
    31: ("content-type", ""),
    32: ("cookie", ""),
    33: ("date", ""),
    34: ("etag", ""),
    35: ("expect", ""),
    36: ("expires", ""),
    37: ("from", ""),
    38: ("host", ""),
    39: ("if-match", ""),
    40: ("if-modified-since", ""),
    41: ("if-none-match", ""),
    42: ("if-range", ""),
    43: ("if-unmodified-since", ""),
    44: ("last-modified", ""),
    45: ("link", ""),
    46: ("location", ""),
    47: ("max-forwards", ""),
    48: ("proxy-authenticate", ""),
    49: ("proxy-authorization", ""),
    50: ("range", ""),
    51: ("referer", ""),
    52: ("refresh", ""),
    53: ("retry-after", ""),
    54: ("server", ""),
    55: ("set-cookie", ""),
    56: ("strict-transport-security", ""),
    57: ("transfer-encoding", ""),
    58: ("user-agent", ""),
    59: ("vary", ""),
    60: ("via", ""),
    61: ("www-authenticate", ""),
}


@dataclass
class CompressionResult:
    """Result of compressing a single header"""
    name: str
    value: str
    encoding: str  # "indexed", "literal-indexed", "literal-never-indexed"
    bytes_uncompressed: int
    bytes_compressed: int
    table_index: Optional[int]


@dataclass
class RequestAnalysis:
    """Analysis of a single request's headers"""
    request_num: int
    headers: List[CompressionResult]
    total_uncompressed: int
    total_compressed: int
    compression_ratio: float
    dynamic_table_size: int


class HPACKAnalyzer:
    """Simulates HPACK compression"""

    def __init__(self, max_table_size: int = 4096):
        self.max_table_size = max_table_size
        # Dynamic table: OrderedDict for FIFO eviction
        self.dynamic_table: OrderedDict[int, Tuple[str, str]] = OrderedDict()
        self.next_index = 62  # Start after static table
        self.current_table_size = 0

    def find_in_static_table(self, name: str, value: str) -> Optional[int]:
        """Find exact match in static table"""
        for idx, (n, v) in STATIC_TABLE.items():
            if n.lower() == name.lower() and v == value:
                return idx
        return None

    def find_name_in_static_table(self, name: str) -> Optional[int]:
        """Find name-only match in static table"""
        for idx, (n, v) in STATIC_TABLE.items():
            if n.lower() == name.lower():
                return idx
        return None

    def find_in_dynamic_table(self, name: str, value: str) -> Optional[int]:
        """Find exact match in dynamic table"""
        for idx, (n, v) in self.dynamic_table.items():
            if n.lower() == name.lower() and v == value:
                return idx
        return None

    def add_to_dynamic_table(self, name: str, value: str) -> int:
        """Add entry to dynamic table with eviction"""
        entry_size = len(name) + len(value) + 32  # RFC 7541: 32 bytes overhead

        # Evict entries if needed
        while self.current_table_size + entry_size > self.max_table_size and self.dynamic_table:
            # Evict oldest (first) entry
            old_idx = next(iter(self.dynamic_table))
            old_name, old_value = self.dynamic_table.pop(old_idx)
            self.current_table_size -= (len(old_name) + len(old_value) + 32)

        # Add new entry if it fits
        if entry_size <= self.max_table_size:
            self.dynamic_table[self.next_index] = (name, value)
            self.current_table_size += entry_size
            self.next_index += 1
            return self.next_index - 1

        return -1

    def encode_header(self, name: str, value: str) -> CompressionResult:
        """Encode a single header with HPACK"""
        uncompressed_size = len(f"{name}: {value}\r\n")

        # Try exact match in static table
        static_idx = self.find_in_static_table(name, value)
        if static_idx:
            return CompressionResult(
                name=name,
                value=value,
                encoding="indexed (static)",
                bytes_uncompressed=uncompressed_size,
                bytes_compressed=1,  # Single index byte
                table_index=static_idx
            )

        # Try exact match in dynamic table
        dynamic_idx = self.find_in_dynamic_table(name, value)
        if dynamic_idx:
            return CompressionResult(
                name=name,
                value=value,
                encoding="indexed (dynamic)",
                bytes_uncompressed=uncompressed_size,
                bytes_compressed=1,  # Single index byte
                table_index=dynamic_idx
            )

        # Literal with incremental indexing
        name_idx = self.find_name_in_static_table(name)

        if name_idx:
            # Name indexed, value literal
            compressed_size = 1 + len(value)  # Index + value
        else:
            # Both name and value literal
            compressed_size = 1 + len(name) + len(value)

        # Add to dynamic table
        table_idx = self.add_to_dynamic_table(name, value)

        return CompressionResult(
            name=name,
            value=value,
            encoding="literal + indexed",
            bytes_uncompressed=uncompressed_size,
            bytes_compressed=compressed_size,
            table_index=table_idx if table_idx > 0 else None
        )

    def analyze_request(self, request_num: int, headers: Dict[str, str]) -> RequestAnalysis:
        """Analyze compression for all headers in a request"""
        results = []
        total_uncompressed = 0
        total_compressed = 0

        for name, value in headers.items():
            result = self.encode_header(name, value)
            results.append(result)
            total_uncompressed += result.bytes_uncompressed
            total_compressed += result.bytes_compressed

        compression_ratio = (1 - (total_compressed / total_uncompressed)) * 100 if total_uncompressed > 0 else 0

        return RequestAnalysis(
            request_num=request_num,
            headers=results,
            total_uncompressed=total_uncompressed,
            total_compressed=total_compressed,
            compression_ratio=compression_ratio,
            dynamic_table_size=self.current_table_size
        )


def parse_headers_file(filepath: str) -> List[Dict[str, str]]:
    """Parse headers from file (one request per section, separated by blank line)"""
    requests = []
    current_headers = {}

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()

            if not line:
                # Blank line: end of request
                if current_headers:
                    requests.append(current_headers)
                    current_headers = {}
            elif ': ' in line:
                # Header line
                name, value = line.split(': ', 1)
                current_headers[name.lower()] = value

    # Add final request
    if current_headers:
        requests.append(current_headers)

    return requests


def generate_demo_requests() -> List[Dict[str, str]]:
    """Generate demo requests for demonstration"""
    base_headers = {
        ':method': 'GET',
        ':scheme': 'https',
        ':authority': 'api.example.com',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'accept': 'application/json',
        'accept-encoding': 'gzip, deflate, br',
        'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0',
    }

    requests = []
    for i in range(1, 6):
        headers = base_headers.copy()
        headers[':path'] = f'/api/users/{i}'
        requests.append(headers)

    return requests


def print_analysis(analyses: List[RequestAnalysis], verbose: bool = False):
    """Print human-readable analysis"""
    print("\n" + "="*80)
    print("HPACK Header Compression Analysis")
    print("="*80)

    for analysis in analyses:
        print(f"\nRequest #{analysis.request_num}:")
        print(f"  Uncompressed: {analysis.total_uncompressed} bytes")
        print(f"  Compressed:   {analysis.total_compressed} bytes")
        print(f"  Compression:  {analysis.compression_ratio:.1f}%")
        print(f"  Dynamic table size: {analysis.dynamic_table_size} bytes")

        if verbose:
            print(f"\n  Header breakdown:")
            for header in analysis.headers:
                print(f"    {header.name}: {header.value[:50]}...")
                print(f"      Encoding: {header.encoding}")
                print(f"      Size: {header.bytes_uncompressed} → {header.bytes_compressed} bytes "
                      f"({((1 - header.bytes_compressed/header.bytes_uncompressed)*100):.0f}% compression)")
                if header.table_index:
                    print(f"      Table index: {header.table_index}")

    # Summary
    print("\n" + "="*80)
    print("Summary:")
    total_uncompressed = sum(a.total_uncompressed for a in analyses)
    total_compressed = sum(a.total_compressed for a in analyses)
    avg_compression = (1 - (total_compressed / total_uncompressed)) * 100

    print(f"  Total requests:     {len(analyses)}")
    print(f"  Total uncompressed: {total_uncompressed} bytes")
    print(f"  Total compressed:   {total_compressed} bytes")
    print(f"  Average compression: {avg_compression:.1f}%")
    print(f"  Bytes saved:        {total_uncompressed - total_compressed} bytes")

    # Per-request breakdown
    print(f"\n  Compression by request:")
    for analysis in analyses:
        bar_length = int(analysis.compression_ratio / 2)
        bar = "█" * bar_length
        print(f"    Request {analysis.request_num}: {bar} {analysis.compression_ratio:.1f}%")

    print("="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze HPACK header compression efficiency',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Demo mode
  python analyze_hpack.py --demo

  # Analyze headers from file
  python analyze_hpack.py --requests headers.txt

  # Verbose output with header details
  python analyze_hpack.py --demo --verbose

  # JSON output
  python analyze_hpack.py --demo --json output.json

Headers file format:
  :method: GET
  :path: /api/users/1
  :scheme: https
  host: api.example.com

  :method: GET
  :path: /api/users/2
  :scheme: https
  host: api.example.com
        """
    )

    parser.add_argument('--requests', type=str,
                        help='File containing HTTP headers (one request per section)')
    parser.add_argument('--demo', action='store_true',
                        help='Run with demo requests')
    parser.add_argument('--table-size', type=int, default=4096,
                        help='HPACK dynamic table size in bytes (default: 4096)')
    parser.add_argument('--verbose', action='store_true',
                        help='Verbose output with per-header details')
    parser.add_argument('--json', type=str,
                        help='Output results to JSON file')

    args = parser.parse_args()

    if not args.requests and not args.demo:
        parser.error('Either --requests or --demo must be specified')

    # Load requests
    if args.demo:
        requests = generate_demo_requests()
        print(f"Running demo with {len(requests)} sample requests...")
    else:
        requests = parse_headers_file(args.requests)
        print(f"Loaded {len(requests)} requests from {args.requests}")

    # Analyze
    analyzer = HPACKAnalyzer(max_table_size=args.table_size)
    analyses = []

    for i, headers in enumerate(requests, 1):
        analysis = analyzer.analyze_request(i, headers)
        analyses.append(analysis)

    # Output
    if not args.json:
        print_analysis(analyses, verbose=args.verbose)

    if args.json:
        output = {
            'table_size': args.table_size,
            'num_requests': len(requests),
            'analyses': [
                {
                    'request_num': a.request_num,
                    'total_uncompressed': a.total_uncompressed,
                    'total_compressed': a.total_compressed,
                    'compression_ratio': a.compression_ratio,
                    'dynamic_table_size': a.dynamic_table_size,
                    'headers': [asdict(h) for h in a.headers]
                }
                for a in analyses
            ]
        }
        with open(args.json, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Results written to {args.json}")


if __name__ == '__main__':
    main()
