# Example 07: Multi-threaded Communication with Channels

Demonstrates channel-based communication patterns for coordinating work between threads.

## Patterns Covered

- **Producer-Consumer**: One producer, multiple consumers
- **Pipeline**: Multi-stage processing
- **Fan-out/Fan-in**: Distribute work, collect results
- **Broadcast**: Send to all workers

## Building

```bash
pip install maturin && maturin develop --release && python test_example.py
```

## Next Steps

Example 08: Zero-copy data transfer with numpy
