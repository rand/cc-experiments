#!/usr/bin/env python3
"""
gRPC Client Generator

Generates gRPC client code and examples from Protocol Buffer definitions.
Supports multiple languages and includes error handling, interceptors, and testing helpers.

Usage:
    ./generate_client.py --proto-file api.proto --language python --output-dir ./client
    ./generate_client.py --proto-file api.proto --language go --json
    ./generate_client.py --help

Features:
- Generate client code for Python, Go, Node.js
- Include example usage code
- Add error handling patterns
- Generate interceptor templates
- Create testing helpers
- Support multiple output formats
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass, asdict


@dataclass
class ProtoService:
    """Parsed gRPC service"""
    name: str
    methods: List[Tuple[str, str, str, str]]  # (name, request_type, response_type, rpc_type)
    package: str


@dataclass
class GeneratedFile:
    """Generated file output"""
    path: str
    content: str
    description: str


class ProtoParser:
    """Parse Proto files to extract service definitions"""

    @staticmethod
    def parse_proto(proto_file: Path) -> List[ProtoService]:
        """Parse proto file and extract services"""
        if not proto_file.exists():
            raise FileNotFoundError(f"Proto file not found: {proto_file}")

        content = proto_file.read_text()
        lines = content.split('\n')

        package = ""
        services = []
        current_service = None

        for line in lines:
            line = line.strip()

            # Skip comments
            if not line or line.startswith('//'):
                continue

            # Extract package
            if line.startswith('package'):
                match = re.match(r'package\s+([^;]+);', line)
                if match:
                    package = match.group(1).strip()

            # Extract service
            elif line.startswith('service'):
                match = re.match(r'service\s+(\w+)', line)
                if match:
                    current_service = ProtoService(
                        name=match.group(1),
                        methods=[],
                        package=package
                    )
                    services.append(current_service)

            # Extract RPC methods
            elif current_service and line.startswith('rpc'):
                # Parse: rpc MethodName(stream? RequestType) returns (stream? ResponseType);
                match = re.match(
                    r'rpc\s+(\w+)\s*\(\s*(stream\s+)?(\w+)\s*\)\s*returns\s*\(\s*(stream\s+)?(\w+)\s*\)',
                    line
                )
                if match:
                    method_name = match.group(1)
                    req_stream = bool(match.group(2))
                    request_type = match.group(3)
                    resp_stream = bool(match.group(4))
                    response_type = match.group(5)

                    # Determine RPC type
                    if not req_stream and not resp_stream:
                        rpc_type = 'unary'
                    elif not req_stream and resp_stream:
                        rpc_type = 'server_streaming'
                    elif req_stream and not resp_stream:
                        rpc_type = 'client_streaming'
                    else:
                        rpc_type = 'bidirectional_streaming'

                    current_service.methods.append((
                        method_name,
                        request_type,
                        response_type,
                        rpc_type
                    ))

        return services


class PythonClientGenerator:
    """Generate Python gRPC client code"""

    @staticmethod
    def generate(service: ProtoService, proto_file: Path) -> List[GeneratedFile]:
        """Generate Python client files"""
        files = []

        # Generate main client
        files.append(GeneratedFile(
            path=f'{service.name.lower()}_client.py',
            content=PythonClientGenerator._generate_client(service, proto_file),
            description='Main gRPC client class'
        ))

        # Generate example usage
        files.append(GeneratedFile(
            path=f'{service.name.lower()}_example.py',
            content=PythonClientGenerator._generate_example(service),
            description='Example usage script'
        ))

        # Generate interceptor
        files.append(GeneratedFile(
            path=f'{service.name.lower()}_interceptor.py',
            content=PythonClientGenerator._generate_interceptor(),
            description='Client interceptor template'
        ))

        # Generate tests
        files.append(GeneratedFile(
            path=f'test_{service.name.lower()}_client.py',
            content=PythonClientGenerator._generate_tests(service),
            description='Unit tests for client'
        ))

        return files

    @staticmethod
    def _generate_client(service: ProtoService, proto_file: Path) -> str:
        """Generate main Python client"""
        proto_module = proto_file.stem
        methods = []

        for method_name, req_type, resp_type, rpc_type in service.methods:
            if rpc_type == 'unary':
                methods.append(f"""
    def {method_name}(self, request, timeout=None, metadata=None):
        \"\"\"
        {method_name} - Unary RPC

        Args:
            request ({req_type}): Request message
            timeout (float): Deadline in seconds
            metadata (list): Optional metadata

        Returns:
            {resp_type}: Response message

        Raises:
            grpc.RpcError: On RPC failure
        \"\"\"
        try:
            response = self.stub.{method_name}(
                request,
                timeout=timeout or self.default_timeout,
                metadata=metadata or []
            )
            return response

        except grpc.RpcError as e:
            self._handle_error(e, '{method_name}')
            raise
""")
            elif rpc_type == 'server_streaming':
                methods.append(f"""
    def {method_name}(self, request, timeout=None, metadata=None):
        \"\"\"
        {method_name} - Server streaming RPC

        Args:
            request ({req_type}): Request message
            timeout (float): Deadline in seconds
            metadata (list): Optional metadata

        Yields:
            {resp_type}: Stream of response messages

        Raises:
            grpc.RpcError: On RPC failure
        \"\"\"
        try:
            response_stream = self.stub.{method_name}(
                request,
                timeout=timeout or self.default_timeout,
                metadata=metadata or []
            )

            for response in response_stream:
                yield response

        except grpc.RpcError as e:
            self._handle_error(e, '{method_name}')
            raise
""")

        return f'''#!/usr/bin/env python3
"""
{service.name} gRPC Client

Auto-generated gRPC client for {service.name}.
Includes error handling, retry logic, and connection management.
"""

import grpc
import logging
import time
from typing import Optional, Iterator

import {proto_module}_pb2
import {proto_module}_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class {service.name}Client:
    """
    gRPC client for {service.name}

    Features:
    - Automatic connection management
    - Error handling with retry logic
    - Configurable timeouts
    - Logging and metrics

    Example:
        client = {service.name}Client('localhost:50051')
        response = client.SomeMethod(request)
    """

    def __init__(
        self,
        address: str,
        secure: bool = False,
        credentials=None,
        default_timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize {service.name} client

        Args:
            address: Server address (host:port)
            secure: Use TLS if True
            credentials: gRPC channel credentials (for TLS)
            default_timeout: Default RPC timeout in seconds
            max_retries: Maximum retry attempts for transient failures
        """
        self.address = address
        self.default_timeout = default_timeout
        self.max_retries = max_retries

        # Create channel
        if secure:
            if credentials is None:
                credentials = grpc.ssl_channel_credentials()
            self.channel = grpc.secure_channel(address, credentials)
        else:
            self.channel = grpc.insecure_channel(address)

        # Create stub
        self.stub = {proto_module}_pb2_grpc.{service.name}Stub(self.channel)

        logger.info(f'Connected to {{address}} (secure={{secure}})')

    def close(self):
        """Close the gRPC channel"""
        if self.channel:
            self.channel.close()
            logger.info('Channel closed')

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def _handle_error(self, error: grpc.RpcError, method_name: str):
        """
        Handle RPC errors with logging

        Args:
            error: The gRPC error
            method_name: Name of the method that failed
        """
        code = error.code()
        details = error.details()

        # Log based on error type
        if code == grpc.StatusCode.NOT_FOUND:
            logger.warning(f'{{method_name}}: Not found - {{details}}')
        elif code == grpc.StatusCode.DEADLINE_EXCEEDED:
            logger.error(f'{{method_name}}: Timeout - {{details}}')
        elif code == grpc.StatusCode.UNAUTHENTICATED:
            logger.error(f'{{method_name}}: Authentication required - {{details}}')
        elif code == grpc.StatusCode.PERMISSION_DENIED:
            logger.error(f'{{method_name}}: Permission denied - {{details}}')
        elif code == grpc.StatusCode.UNAVAILABLE:
            logger.error(f'{{method_name}}: Service unavailable - {{details}}')
        else:
            logger.error(f'{{method_name}}: {{code}} - {{details}}')

    def _retry_call(self, call_fn, *args, **kwargs):
        """
        Retry RPC call on transient failures

        Args:
            call_fn: Function to call
            *args, **kwargs: Arguments to pass to function

        Returns:
            Result from call_fn

        Raises:
            grpc.RpcError: If all retries fail
        """
        retriable_codes = {{
            grpc.StatusCode.UNAVAILABLE,
            grpc.StatusCode.DEADLINE_EXCEEDED,
            grpc.StatusCode.ABORTED
        }}

        last_error = None

        for attempt in range(self.max_retries):
            try:
                return call_fn(*args, **kwargs)

            except grpc.RpcError as e:
                last_error = e

                if e.code() not in retriable_codes:
                    raise  # Non-retriable error

                if attempt < self.max_retries - 1:
                    backoff = (2 ** attempt)  # Exponential backoff
                    logger.warning(f'Retry attempt {{attempt + 1}}/{{self.max_retries}} after {{backoff}}s')
                    time.sleep(backoff)
                else:
                    raise  # Max retries exceeded

        raise last_error

{"".join(methods)}

# Example usage
if __name__ == '__main__':
    # Create client
    with {service.name}Client('localhost:50051') as client:
        # Call methods here
        pass
'''

    @staticmethod
    def _generate_example(service: ProtoService) -> str:
        """Generate example usage script"""
        examples = []

        for method_name, req_type, resp_type, rpc_type in service.methods:
            if rpc_type == 'unary':
                examples.append(f"""
    # Unary RPC: {method_name}
    try:
        request = proto.{req_type}()  # Set request fields
        response = client.{method_name}(request, timeout=5.0)
        print(f'{method_name} response: {{response}}')
    except grpc.RpcError as e:
        print(f'{method_name} failed: {{e.code()}} - {{e.details()}}')
""")
            elif rpc_type == 'server_streaming':
                examples.append(f"""
    # Server streaming RPC: {method_name}
    try:
        request = proto.{req_type}()  # Set request fields
        for response in client.{method_name}(request, timeout=30.0):
            print(f'{method_name} received: {{response}}')
    except grpc.RpcError as e:
        print(f'{method_name} failed: {{e.code()}} - {{e.details()}}')
""")

        return f'''#!/usr/bin/env python3
"""
{service.name} Client Examples

Example usage of {service.name} client.
"""

import grpc
from {service.name.lower()}_client import {service.name}Client
import {service.package.replace('.', '_')}_pb2 as proto


def main():
    # Connect to server
    with {service.name}Client('localhost:50051') as client:
        {"".join(examples)}

if __name__ == '__main__':
    main()
'''

    @staticmethod
    def _generate_interceptor() -> str:
        """Generate client interceptor template"""
        return '''#!/usr/bin/env python3
"""
Client Interceptor Template

Template for implementing custom client interceptors.
"""

import grpc
import logging

logger = logging.getLogger(__name__)


class AuthInterceptor(grpc.UnaryUnaryClientInterceptor):
    """Add authentication token to all requests"""

    def __init__(self, token):
        self.token = token

    def intercept_unary_unary(self, continuation, client_call_details, request):
        """Add auth metadata"""
        metadata = []
        if client_call_details.metadata:
            metadata = list(client_call_details.metadata)

        metadata.append(('authorization', f'Bearer {self.token}'))

        new_details = client_call_details._replace(metadata=metadata)
        return continuation(new_details, request)


class LoggingInterceptor(grpc.UnaryUnaryClientInterceptor):
    """Log all RPC calls"""

    def intercept_unary_unary(self, continuation, client_call_details, request):
        """Log RPC calls"""
        logger.info(f'Calling: {client_call_details.method}')

        try:
            response = continuation(client_call_details, request)
            logger.info(f'Success: {client_call_details.method}')
            return response
        except grpc.RpcError as e:
            logger.error(f'Failed: {client_call_details.method} - {e.code()}')
            raise


class MetricsInterceptor(grpc.UnaryUnaryClientInterceptor):
    """Collect metrics for RPC calls"""

    def __init__(self):
        self.call_counts = {}

    def intercept_unary_unary(self, continuation, client_call_details, request):
        """Count RPC calls"""
        method = client_call_details.method
        self.call_counts[method] = self.call_counts.get(method, 0) + 1

        return continuation(client_call_details, request)

    def get_stats(self):
        """Get collected statistics"""
        return dict(self.call_counts)


# Usage example
if __name__ == '__main__':
    import grpc

    # Create intercepted channel
    channel = grpc.insecure_channel('localhost:50051')
    intercepted_channel = grpc.intercept_channel(
        channel,
        AuthInterceptor(token='secret-token'),
        LoggingInterceptor(),
        MetricsInterceptor()
    )
'''

    @staticmethod
    def _generate_tests(service: ProtoService) -> str:
        """Generate unit tests"""
        return f'''#!/usr/bin/env python3
"""
{service.name} Client Tests

Unit tests for {service.name} client.
"""

import unittest
from unittest.mock import MagicMock, patch
import grpc

from {service.name.lower()}_client import {service.name}Client


class Test{service.name}Client(unittest.TestCase):
    """Test {service.name}Client"""

    def setUp(self):
        """Set up test client"""
        self.client = {service.name}Client('localhost:50051')

    def tearDown(self):
        """Clean up"""
        self.client.close()

    def test_connection(self):
        """Test client connection"""
        self.assertIsNotNone(self.client.channel)
        self.assertIsNotNone(self.client.stub)

    def test_context_manager(self):
        """Test context manager"""
        with {service.name}Client('localhost:50051') as client:
            self.assertIsNotNone(client)

    @patch('grpc.insecure_channel')
    def test_insecure_connection(self, mock_channel):
        """Test insecure channel creation"""
        client = {service.name}Client('localhost:50051', secure=False)
        mock_channel.assert_called_once_with('localhost:50051')

    @patch('grpc.secure_channel')
    def test_secure_connection(self, mock_channel):
        """Test secure channel creation"""
        client = {service.name}Client('localhost:50051', secure=True)
        mock_channel.assert_called_once()


if __name__ == '__main__':
    unittest.main()
'''


class GoClientGenerator:
    """Generate Go gRPC client code"""

    @staticmethod
    def generate(service: ProtoService, proto_file: Path) -> List[GeneratedFile]:
        """Generate Go client files"""
        files = []

        # Generate main client
        files.append(GeneratedFile(
            path=f'{service.name.lower()}_client.go',
            content=GoClientGenerator._generate_client(service),
            description='Go gRPC client'
        ))

        # Generate example
        files.append(GeneratedFile(
            path=f'{service.name.lower()}_example.go',
            content=GoClientGenerator._generate_example(service),
            description='Example usage'
        ))

        return files

    @staticmethod
    def _generate_client(service: ProtoService) -> str:
        """Generate Go client"""
        methods = []

        for method_name, req_type, resp_type, rpc_type in service.methods:
            if rpc_type == 'unary':
                methods.append(f'''
// {method_name} calls the {method_name} RPC method
func (c *Client) {method_name}(ctx context.Context, req *pb.{req_type}) (*pb.{resp_type}, error) {{
    return c.client.{method_name}(ctx, req)
}}
''')

        return f'''package client

import (
    "context"
    "time"

    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials"
    pb "your-module/proto"
)

// Client wraps the gRPC client for {service.name}
type Client struct {{
    conn   *grpc.ClientConn
    client pb.{service.name}Client
}}

// NewClient creates a new {service.name} client
func NewClient(address string, secure bool) (*Client, error) {{
    var opts []grpc.DialOption

    if secure {{
        creds, err := credentials.NewClientTLSFromFile("cert.pem", "")
        if err != nil {{
            return nil, err
        }}
        opts = append(opts, grpc.WithTransportCredentials(creds))
    }} else {{
        opts = append(opts, grpc.WithInsecure())
    }}

    conn, err := grpc.Dial(address, opts...)
    if err != nil {{
        return nil, err
    }}

    return &Client{{
        conn:   conn,
        client: pb.New{service.name}Client(conn),
    }}, nil
}}

// Close closes the client connection
func (c *Client) Close() error {{
    if c.conn != nil {{
        return c.conn.Close()
    }}
    return nil
}}

{"".join(methods)}
'''

    @staticmethod
    def _generate_example(service: ProtoService) -> str:
        """Generate Go example"""
        return f'''package main

import (
    "context"
    "log"
    "time"

    "your-module/client"
    pb "your-module/proto"
)

func main() {{
    // Connect to server
    client, err := client.NewClient("localhost:50051", false)
    if err != nil {{
        log.Fatalf("Failed to connect: %v", err)
    }}
    defer client.Close()

    // Example: Call RPC method
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()

    // Add your RPC calls here
}}
'''


class NodeClientGenerator:
    """Generate Node.js gRPC client code"""

    @staticmethod
    def generate(service: ProtoService, proto_file: Path) -> List[GeneratedFile]:
        """Generate Node.js client files"""
        files = []

        # Generate main client
        files.append(GeneratedFile(
            path=f'{service.name.lower()}_client.js',
            content=NodeClientGenerator._generate_client(service, proto_file),
            description='Node.js gRPC client'
        ))

        # Generate example
        files.append(GeneratedFile(
            path=f'{service.name.lower()}_example.js',
            content=NodeClientGenerator._generate_example(service),
            description='Example usage'
        ))

        return files

    @staticmethod
    def_generate_client(service: ProtoService, proto_file: Path) -> str:
        """Generate Node.js client"""
        return f'''const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

/**
 * {service.name} gRPC Client
 */
class {service.name}Client {{
    constructor(address, secure = false) {{
        this.address = address;

        // Load proto file
        const packageDefinition = protoLoader.loadSync(
            '{proto_file.name}',
            {{
                keepCase: true,
                longs: String,
                enums: String,
                defaults: true,
                oneofs: true
            }}
        );

        const proto = grpc.loadPackageDefinition(packageDefinition);

        // Create client
        const credentials = secure
            ? grpc.credentials.createSsl()
            : grpc.credentials.createInsecure();

        this.client = new proto.{service.package}.{service.name}(
            address,
            credentials
        );
    }}

    close() {{
        if (this.client) {{
            this.client.close();
        }}
    }}
}}

module.exports = {service.name}Client;
'''

    @staticmethod
    def _generate_example(service: ProtoService) -> str:
        """Generate Node.js example"""
        return f'''const {service.name}Client = require('./{service.name.lower()}_client');

async function main() {{
    const client = new {service.name}Client('localhost:50051');

    try {{
        // Add your RPC calls here

    }} finally {{
        client.close();
    }}
}}

main().catch(console.error);
'''


def main():
    parser = argparse.ArgumentParser(
        description='Generate gRPC client code from Protocol Buffer definitions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate Python client
  %(prog)s --proto-file api.proto --language python --output-dir ./client

  # Generate Go client
  %(prog)s --proto-file api.proto --language go --output-dir ./client

  # JSON output (list generated files)
  %(prog)s --proto-file api.proto --language python --json

Supported Languages:
  - python: Python 3.7+ with grpcio
  - go: Go 1.16+ with google.golang.org/grpc
  - nodejs: Node.js with @grpc/grpc-js

Generated Files:
  Python:
    - <service>_client.py: Main client class
    - <service>_example.py: Usage examples
    - <service>_interceptor.py: Interceptor templates
    - test_<service>_client.py: Unit tests

  Go:
    - <service>_client.go: Main client
    - <service>_example.go: Usage example

  Node.js:
    - <service>_client.js: Main client
    - <service>_example.js: Usage example
        """
    )

    parser.add_argument(
        '--proto-file',
        type=Path,
        required=True,
        help='Path to .proto file'
    )

    parser.add_argument(
        '--language',
        choices=['python', 'go', 'nodejs'],
        required=True,
        help='Target language for client generation'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('.'),
        help='Output directory for generated files (default: current directory)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON (list of generated files)'
    )

    args = parser.parse_args()

    # Parse proto file
    try:
        services = ProtoParser.parse_proto(args.proto_file)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not services:
        print(f"Error: No services found in {args.proto_file}", file=sys.stderr)
        sys.exit(1)

    # Generate clients for all services
    all_files = []

    for service in services:
        # Select generator based on language
        if args.language == 'python':
            files = PythonClientGenerator.generate(service, args.proto_file)
        elif args.language == 'go':
            files = GoClientGenerator.generate(service, args.proto_file)
        elif args.language == 'nodejs':
            files = NodeClientGenerator.generate(service, args.proto_file)

        # Write files
        if not args.json:
            args.output_dir.mkdir(parents=True, exist_ok=True)

            for file in files:
                output_path = args.output_dir / file.path
                output_path.write_text(file.content)
                print(f"Generated: {output_path} ({file.description})")

        all_files.extend(files)

    # JSON output
    if args.json:
        result = {
            'language': args.language,
            'proto_file': str(args.proto_file),
            'services': [s.name for s in services],
            'files': [
                {
                    'path': f.path,
                    'description': f.description,
                    'lines': len(f.content.split('\n'))
                }
                for f in all_files
            ]
        }
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
