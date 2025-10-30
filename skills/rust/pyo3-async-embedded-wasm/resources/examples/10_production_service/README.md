# Example 10: Production Service

Complete production-ready async service with rate limiting, monitoring, health checks, and statistics.

## Building
```bash
maturin develop
```

## Running
```bash
pytest test_example.py
python test_example.py
```

## Key Concepts
- Connection pooling and rate limiting
- Request statistics and monitoring
- Health checks
- Error handling and recovery
- Production patterns

## Features
- Semaphore-based concurrency control
- Real-time statistics tracking
- Health check endpoint
- Graceful error handling
- Thread-safe state management
