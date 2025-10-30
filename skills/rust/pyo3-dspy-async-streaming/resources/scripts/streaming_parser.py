#!/usr/bin/env python3
"""
Streaming Parser for LM Responses

Parses streaming LM responses from SSE and WebSocket sources with chunking,
reassembly, and validation capabilities.

Usage:
    python streaming_parser.py parse --input stream.log --format sse
    python streaming_parser.py test --url ws://localhost:8000/stream
    python streaming_parser.py validate --stream stream.log
    python streaming_parser.py benchmark --streams 10 --duration 30
"""

import argparse
import asyncio
import json
import re
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import AsyncIterator, Deque, List, Optional, Union
from urllib.parse import urlparse

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("Warning: websockets not available. Install with: uv add websockets", file=sys.stderr)


class StreamFormat(Enum):
    """Supported stream formats."""
    SSE = "sse"
    WEBSOCKET = "websocket"
    RAW = "raw"


class StreamState(Enum):
    """Stream processing states."""
    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    BUFFERING = "buffering"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class StreamChunk:
    """Individual stream chunk."""
    data: str
    timestamp: float
    sequence: int
    is_complete: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class StreamMessage:
    """Reassembled stream message."""
    content: str
    chunks: List[StreamChunk]
    start_time: float
    end_time: float
    total_tokens: int = 0

    @property
    def duration(self) -> float:
        """Message processing duration in seconds."""
        return self.end_time - self.start_time

    @property
    def tokens_per_second(self) -> float:
        """Tokens per second throughput."""
        if self.duration == 0:
            return 0.0
        return self.total_tokens / self.duration


class SSEParser:
    """Server-Sent Events (SSE) parser."""

    # SSE field patterns
    DATA_PATTERN = re.compile(r'^data:\s*(.*)$')
    EVENT_PATTERN = re.compile(r'^event:\s*(.*)$')
    ID_PATTERN = re.compile(r'^id:\s*(.*)$')
    RETRY_PATTERN = re.compile(r'^retry:\s*(\d+)$')

    def __init__(self):
        self.buffer: List[str] = []
        self.current_event: Optional[str] = None
        self.current_id: Optional[str] = None

    def parse_line(self, line: str) -> Optional[dict]:
        """Parse a single SSE line.

        Returns event dict if complete, None if buffering.
        """
        line = line.rstrip('\n\r')

        # Empty line signals end of event
        if not line:
            if self.buffer:
                event = self._flush_event()
                return event
            return None

        # Comment line
        if line.startswith(':'):
            return None

        # Data field
        data_match = self.DATA_PATTERN.match(line)
        if data_match:
            self.buffer.append(data_match.group(1))
            return None

        # Event field
        event_match = self.EVENT_PATTERN.match(line)
        if event_match:
            self.current_event = event_match.group(1)
            return None

        # ID field
        id_match = self.ID_PATTERN.match(line)
        if id_match:
            self.current_id = id_match.group(1)
            return None

        # Retry field
        retry_match = self.RETRY_PATTERN.match(line)
        if retry_match:
            return {
                'type': 'retry',
                'retry': int(retry_match.group(1))
            }

        return None

    def _flush_event(self) -> dict:
        """Flush buffered data into event."""
        data = '\n'.join(self.buffer)
        event = {
            'type': self.current_event or 'message',
            'data': data,
            'id': self.current_id
        }

        # Reset state
        self.buffer.clear()
        self.current_event = None
        self.current_id = None

        return event

    def parse_stream(self, stream: str) -> List[dict]:
        """Parse complete SSE stream."""
        events = []
        for line in stream.split('\n'):
            event = self.parse_line(line)
            if event:
                events.append(event)

        # Flush remaining buffer
        if self.buffer:
            events.append(self._flush_event())

        return events


class WebSocketParser:
    """WebSocket message parser."""

    def __init__(self):
        self.message_buffer: Deque[str] = deque()

    def parse_message(self, message: Union[str, bytes]) -> Optional[dict]:
        """Parse WebSocket message.

        Handles text and binary messages, JSON payloads.
        """
        # Convert bytes to string
        if isinstance(message, bytes):
            try:
                message = message.decode('utf-8')
            except UnicodeDecodeError:
                return {
                    'type': 'binary',
                    'data': message,
                    'error': 'Failed to decode as UTF-8'
                }

        # Try parsing as JSON
        try:
            data = json.loads(message)
            return {
                'type': 'json',
                'data': data
            }
        except json.JSONDecodeError:
            # Plain text message
            return {
                'type': 'text',
                'data': message
            }

    def buffer_message(self, message: str):
        """Add message to buffer for reassembly."""
        self.message_buffer.append(message)

    def flush_buffer(self) -> str:
        """Flush and return buffered messages."""
        result = ''.join(self.message_buffer)
        self.message_buffer.clear()
        return result


class StreamingParser:
    """Main streaming parser with chunking and reassembly."""

    def __init__(self, format: StreamFormat = StreamFormat.SSE):
        self.format = format
        self.sse_parser = SSEParser()
        self.ws_parser = WebSocketParser()
        self.state = StreamState.IDLE
        self.chunk_buffer: List[StreamChunk] = []
        self.sequence = 0

    def parse_chunk(self, data: str, timestamp: Optional[float] = None) -> StreamChunk:
        """Parse individual chunk."""
        if timestamp is None:
            timestamp = time.time()

        chunk = StreamChunk(
            data=data,
            timestamp=timestamp,
            sequence=self.sequence,
            is_complete=self._is_complete_marker(data)
        )

        self.sequence += 1
        return chunk

    def _is_complete_marker(self, data: str) -> bool:
        """Detect stream completion markers."""
        completion_markers = [
            '[DONE]',
            '{"done": true}',
            '{"complete": true}',
            '{"status": "complete"}',
            'data: [DONE]'
        ]

        return any(marker in data for marker in completion_markers)

    def reassemble_chunks(self, chunks: List[StreamChunk]) -> StreamMessage:
        """Reassemble chunks into complete message."""
        if not chunks:
            return StreamMessage(
                content="",
                chunks=[],
                start_time=time.time(),
                end_time=time.time()
            )

        # Extract content from chunks
        content_parts = []
        for chunk in chunks:
            if self.format == StreamFormat.SSE:
                # Parse SSE data fields
                events = self.sse_parser.parse_stream(chunk.data)
                for event in events:
                    if event['type'] == 'message' and event['data']:
                        content_parts.append(event['data'])
            elif self.format == StreamFormat.WEBSOCKET:
                # Parse WebSocket messages
                parsed = self.ws_parser.parse_message(chunk.data)
                if parsed and parsed.get('type') == 'json':
                    # Extract content from common JSON formats
                    data = parsed['data']
                    if isinstance(data, dict):
                        content = (data.get('content') or
                                 data.get('text') or
                                 data.get('delta', {}).get('content') or
                                 '')
                        if content:
                            content_parts.append(content)
                elif parsed:
                    content_parts.append(str(parsed.get('data', '')))
            else:
                # Raw format
                content_parts.append(chunk.data)

        content = ''.join(content_parts)

        # Estimate tokens (rough approximation)
        tokens = len(content.split())

        return StreamMessage(
            content=content,
            chunks=chunks,
            start_time=chunks[0].timestamp,
            end_time=chunks[-1].timestamp,
            total_tokens=tokens
        )

    def parse_file(self, filepath: Path) -> List[StreamMessage]:
        """Parse stream from file."""
        with open(filepath, 'r') as f:
            content = f.read()

        chunks = []
        timestamp = time.time()

        if self.format == StreamFormat.SSE:
            # Split by double newline (SSE event separator)
            for part in content.split('\n\n'):
                if part.strip():
                    chunk = self.parse_chunk(part, timestamp)
                    chunks.append(chunk)
                    timestamp += 0.001  # Simulate timing
        else:
            # Split by newlines for WebSocket/raw
            for line in content.split('\n'):
                if line.strip():
                    chunk = self.parse_chunk(line, timestamp)
                    chunks.append(chunk)
                    timestamp += 0.001

        # Reassemble into messages (group by completion markers)
        messages = []
        current_chunks = []

        for chunk in chunks:
            current_chunks.append(chunk)
            if chunk.is_complete:
                message = self.reassemble_chunks(current_chunks)
                messages.append(message)
                current_chunks = []

        # Reassemble remaining chunks
        if current_chunks:
            message = self.reassemble_chunks(current_chunks)
            messages.append(message)

        return messages

    async def parse_websocket_stream(self, url: str, duration: Optional[float] = None) -> List[StreamMessage]:
        """Parse WebSocket stream."""
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError("websockets package not installed")

        messages = []
        chunks = []
        start_time = time.time()

        async with websockets.connect(url) as websocket:
            self.state = StreamState.STREAMING

            try:
                while True:
                    if duration and (time.time() - start_time) > duration:
                        break

                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    chunk = self.parse_chunk(message)
                    chunks.append(chunk)

                    if chunk.is_complete:
                        msg = self.reassemble_chunks(chunks)
                        messages.append(msg)
                        chunks = []

            except asyncio.TimeoutError:
                pass
            except websockets.exceptions.ConnectionClosed:
                pass

        # Reassemble remaining chunks
        if chunks:
            msg = self.reassemble_chunks(chunks)
            messages.append(msg)

        self.state = StreamState.COMPLETE
        return messages


class StreamValidator:
    """Validate stream integrity and completeness."""

    @staticmethod
    def validate_message(message: StreamMessage) -> dict:
        """Validate single message."""
        issues = []

        # Check for empty content
        if not message.content.strip():
            issues.append("Empty content")

        # Check for missing chunks
        sequences = [chunk.sequence for chunk in message.chunks]
        if sequences:
            expected = set(range(min(sequences), max(sequences) + 1))
            actual = set(sequences)
            if expected != actual:
                missing = expected - actual
                issues.append(f"Missing chunk sequences: {missing}")

        # Check timing
        if message.duration < 0:
            issues.append("Negative duration")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'chunks': len(message.chunks),
            'tokens': message.total_tokens,
            'duration': message.duration
        }

    @staticmethod
    def validate_stream(messages: List[StreamMessage]) -> dict:
        """Validate complete stream."""
        total_issues = []
        total_chunks = 0
        total_tokens = 0
        total_duration = 0.0

        for i, message in enumerate(messages):
            result = StreamValidator.validate_message(message)
            if not result['valid']:
                total_issues.append(f"Message {i}: {', '.join(result['issues'])}")

            total_chunks += result['chunks']
            total_tokens += result['tokens']
            total_duration += result['duration']

        return {
            'valid': len(total_issues) == 0,
            'issues': total_issues,
            'messages': len(messages),
            'total_chunks': total_chunks,
            'total_tokens': total_tokens,
            'total_duration': total_duration,
            'avg_tokens_per_second': total_tokens / total_duration if total_duration > 0 else 0
        }


async def benchmark_parsing(num_streams: int, duration: float):
    """Benchmark stream parsing performance."""
    print(f"Benchmarking {num_streams} streams for {duration}s each...")

    results = []
    start_time = time.time()

    for i in range(num_streams):
        # Generate synthetic stream
        chunks = []
        chunk_start = time.time()

        for j in range(100):  # 100 chunks per stream
            data = f"data: chunk {j}\n\n"
            chunk = StreamChunk(
                data=data,
                timestamp=chunk_start + (j * 0.01),
                sequence=j,
                is_complete=(j == 99)
            )
            chunks.append(chunk)

        parser = StreamingParser(StreamFormat.SSE)
        message = parser.reassemble_chunks(chunks)

        results.append({
            'stream': i,
            'chunks': len(message.chunks),
            'tokens': message.total_tokens,
            'duration': message.duration,
            'tokens_per_second': message.tokens_per_second
        })

    total_time = time.time() - start_time

    print(f"\nBenchmark Results:")
    print(f"Total time: {total_time:.2f}s")
    print(f"Streams processed: {num_streams}")
    print(f"Streams per second: {num_streams / total_time:.2f}")
    print(f"Average tokens per stream: {sum(r['tokens'] for r in results) / num_streams:.2f}")
    print(f"Average tokens per second: {sum(r['tokens_per_second'] for r in results) / num_streams:.2f}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Stream parser for LM responses")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse stream from file')
    parse_parser.add_argument('--input', required=True, help='Input stream file')
    parse_parser.add_argument('--format', choices=['sse', 'websocket', 'raw'], default='sse')
    parse_parser.add_argument('--output', help='Output JSON file')

    # Test command
    test_parser = subparsers.add_parser('test', help='Test WebSocket stream')
    test_parser.add_argument('--url', required=True, help='WebSocket URL')
    test_parser.add_argument('--duration', type=float, help='Test duration in seconds')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate stream')
    validate_parser.add_argument('--stream', required=True, help='Stream file to validate')
    validate_parser.add_argument('--format', choices=['sse', 'websocket', 'raw'], default='sse')

    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Benchmark parsing')
    benchmark_parser.add_argument('--streams', type=int, default=10, help='Number of streams')
    benchmark_parser.add_argument('--duration', type=float, default=30, help='Duration per stream')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'parse':
        format_map = {
            'sse': StreamFormat.SSE,
            'websocket': StreamFormat.WEBSOCKET,
            'raw': StreamFormat.RAW
        }

        parser = StreamingParser(format_map[args.format])
        messages = parser.parse_file(Path(args.input))

        print(f"Parsed {len(messages)} messages from {args.input}")
        for i, msg in enumerate(messages):
            print(f"\nMessage {i}:")
            print(f"  Chunks: {len(msg.chunks)}")
            print(f"  Tokens: {msg.total_tokens}")
            print(f"  Duration: {msg.duration:.3f}s")
            print(f"  Tokens/sec: {msg.tokens_per_second:.2f}")
            print(f"  Content preview: {msg.content[:100]}...")

        if args.output:
            output_data = [
                {
                    'chunks': len(msg.chunks),
                    'tokens': msg.total_tokens,
                    'duration': msg.duration,
                    'content': msg.content
                }
                for msg in messages
            ]

            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\nOutput written to {args.output}")

    elif args.command == 'test':
        if not WEBSOCKETS_AVAILABLE:
            print("Error: websockets package not installed. Install with: uv add websockets", file=sys.stderr)
            sys.exit(1)

        parser = StreamingParser(StreamFormat.WEBSOCKET)
        messages = asyncio.run(parser.parse_websocket_stream(args.url, args.duration))

        print(f"Received {len(messages)} messages from {args.url}")
        for i, msg in enumerate(messages):
            print(f"\nMessage {i}:")
            print(f"  Chunks: {len(msg.chunks)}")
            print(f"  Tokens: {msg.total_tokens}")
            print(f"  Duration: {msg.duration:.3f}s")
            print(f"  Content preview: {msg.content[:100]}...")

    elif args.command == 'validate':
        format_map = {
            'sse': StreamFormat.SSE,
            'websocket': StreamFormat.WEBSOCKET,
            'raw': StreamFormat.RAW
        }

        parser = StreamingParser(format_map[args.format])
        messages = parser.parse_file(Path(args.stream))

        result = StreamValidator.validate_stream(messages)

        print(f"Validation Results:")
        print(f"  Valid: {result['valid']}")
        print(f"  Messages: {result['messages']}")
        print(f"  Total chunks: {result['total_chunks']}")
        print(f"  Total tokens: {result['total_tokens']}")
        print(f"  Total duration: {result['total_duration']:.3f}s")
        print(f"  Avg tokens/sec: {result['avg_tokens_per_second']:.2f}")

        if result['issues']:
            print(f"\nIssues found:")
            for issue in result['issues']:
                print(f"  - {issue}")
        else:
            print(f"\nNo issues found!")

    elif args.command == 'benchmark':
        asyncio.run(benchmark_parsing(args.streams, args.duration))


if __name__ == '__main__':
    main()
