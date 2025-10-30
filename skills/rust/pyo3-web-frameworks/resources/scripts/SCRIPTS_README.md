# PyO3 Web Frameworks Scripts

Production-quality Python scripts for the pyo3-web-frameworks skill.

## Scripts Overview

### 1. api_benchmark.py (947 lines)
API endpoint performance benchmarking for FastAPI, Flask, and Django.

**Features:**
- Request/response timing measurement
- Concurrent load testing
- Statistical latency analysis (p50, p95, p99)
- Throughput measurement
- JSON and text output formats
- Result comparison and analysis
- Custom headers and authentication
- Request body templating

**Commands:**
- `benchmark` - Run performance benchmark
- `load-test` - Run load test for specified duration
- `analyze` - Analyze benchmark results
- `compare` - Compare two benchmark results

**Example Usage:**
```bash
# Basic benchmark
./api_benchmark.py benchmark http://localhost:8000/api/users --requests 1000

# Load test with concurrency
./api_benchmark.py load-test http://localhost:8000/api/users --concurrent 50 --duration 60

# Compare results
./api_benchmark.py compare baseline.json current.json
```

### 2. middleware_generator.py (1056 lines)
Middleware boilerplate generator for FastAPI, Flask, and Django.

**Features:**
- Multi-framework support (FastAPI, Flask, Django)
- Template-based code generation
- Multiple middleware types (auth, logging, rate-limiting, caching, CORS)
- Testing scaffold generation
- Framework detection
- Hook point validation
- PyO3 integration patterns

**Commands:**
- `generate` - Generate middleware code
- `scaffold` - Generate complete middleware scaffold
- `validate` - Validate middleware implementation
- `list-templates` - List available middleware templates

**Example Usage:**
```bash
# Generate authentication middleware
./middleware_generator.py generate auth --framework fastapi --output middleware/

# List available templates
./middleware_generator.py list-templates --json

# Validate middleware
./middleware_generator.py validate middleware/auth_middleware.py
```

### 3. websocket_tester.py (836 lines)
WebSocket connection testing and stress testing.

**Features:**
- Connection stability testing
- Message sending/receiving
- Stress testing with concurrent connections
- Performance metrics (latency, throughput, error rates)
- Binary and text message support
- Long-term monitoring
- Ping/pong tracking

**Commands:**
- `connect` - Test WebSocket connection
- `send` - Send message and test echo
- `stress-test` - Run stress test with multiple connections
- `monitor` - Monitor WebSocket connection over time

**Example Usage:**
```bash
# Test connection
./websocket_tester.py connect ws://localhost:8000/ws

# Send message
./websocket_tester.py send ws://localhost:8000/ws --message '{"type": "hello"}'

# Stress test
./websocket_tester.py stress-test ws://localhost:8000/ws --connections 100 --duration 60

# Monitor connection
./websocket_tester.py monitor ws://localhost:8000/ws --duration 300
```

## Wave 10-11 Standards Compliance

All scripts follow Wave 10-11 standards:

- ✓ Full CLI with argparse
- ✓ 100% type hints (typing module)
- ✓ Multiple output formats (text, JSON)
- ✓ Production-ready error handling
- ✓ Dataclasses for structured data
- ✓ Comprehensive docstrings
- ✓ Executable with proper shebangs
- ✓ 700-900+ lines of production code

## Dependencies

### Core (all scripts):
- Python 3.8+
- Standard library (argparse, json, dataclasses, etc.)

### websocket_tester.py specific:
- `websockets` - WebSocket client library
  ```bash
  pip install websockets
  ```

## Installation

All scripts are standalone and executable:

```bash
chmod +x api_benchmark.py
chmod +x middleware_generator.py
chmod +x websocket_tester.py
```

## Testing

Run syntax validation:
```bash
python3 -m py_compile *.py
```

Run help for each script:
```bash
./api_benchmark.py --help
./middleware_generator.py --help
./websocket_tester.py --help
```
