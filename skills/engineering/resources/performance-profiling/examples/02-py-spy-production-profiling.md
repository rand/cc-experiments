# Example 2: py-spy Production-Safe Python Profiling

This example demonstrates sampling-based profiling of production Python applications using py-spy with minimal overhead.

## Prerequisites

```bash
# Install py-spy
pip install py-spy

# Or with cargo
cargo install py-spy

# Or download binary
# https://github.com/benfred/py-spy/releases
```

## Sample Production Application

```python
# web_server.py
from flask import Flask, jsonify
import time
import random

app = Flask(__name__)

def expensive_computation(n):
    """Simulate CPU-intensive work."""
    result = 0
    for i in range(n):
        result += i ** 2
    return result

def database_query():
    """Simulate database query."""
    time.sleep(random.uniform(0.01, 0.05))
    return {"user": "test", "data": [1, 2, 3]}

@app.route('/api/fast')
def fast_endpoint():
    """Fast endpoint."""
    return jsonify({"status": "ok"})

@app.route('/api/slow')
def slow_endpoint():
    """Slow endpoint with CPU work."""
    result = expensive_computation(100000)
    data = database_query()
    return jsonify({"result": result, "data": data})

@app.route('/api/blocking')
def blocking_endpoint():
    """Endpoint with blocking I/O."""
    time.sleep(0.1)  # Simulate slow external API
    return jsonify({"status": "completed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Profiling Running Process

### Attach to running process

```bash
# Start application
python web_server.py &
APP_PID=$!

# Generate load (in another terminal)
while true; do
    curl -s http://localhost:5000/api/slow > /dev/null
    curl -s http://localhost:5000/api/blocking > /dev/null
    curl -s http://localhost:5000/api/fast > /dev/null
    sleep 0.1
done

# Profile for 60 seconds
py-spy record -o profile.svg --format flamegraph -p $APP_PID --duration 60

# View flame graph
open profile.svg  # macOS
# or xdg-open profile.svg  # Linux
```

### Profile on application start

```bash
# Profile entire execution
py-spy record -o profile.svg --format flamegraph -- python web_server.py

# With speedscope format for interactive analysis
py-spy record -o profile.speedscope --format speedscope -- python web_server.py

# Open in speedscope.app
open https://www.speedscope.app
# Upload profile.speedscope
```

## Real-Time Monitoring

### Top-like display

```bash
# Real-time function statistics
py-spy top --pid $APP_PID

# Output (refreshes every second):
# Total Samples: 1000
#   GIL: 95.2%
#   Threads: 4
#
# %Own   %Total  OwnTime  TotalTime  Function (filename:line)
# 45.2%  45.2%   0.452s   0.452s     expensive_computation (web_server.py:8)
# 30.1%  30.1%   0.301s   0.301s     time.sleep (time.py:...)
# 12.3%  15.6%   0.123s   0.156s     database_query (web_server.py:15)
```

### Monitor specific threads

```bash
# Show all threads
py-spy top --pid $APP_PID --subprocesses

# Show native stack traces (C extensions)
py-spy top --pid $APP_PID --native
```

## Advanced Features

### Sampling Rate

```bash
# Default: 100 Hz (samples per second)
py-spy record -o profile.svg -p $APP_PID --rate 100

# Higher rate for more detail (but more overhead)
py-spy record -o profile.svg -p $APP_PID --rate 500

# Lower rate for less overhead
py-spy record -o profile.svg -p $APP_PID --rate 50
```

### Subprocess Profiling

```bash
# Profile all subprocesses
py-spy record -o profile.svg --subprocesses -- python web_server.py

# Useful for:
# - Multiprocessing applications
# - Worker processes
# - Celery tasks
```

### Filtering

```bash
# Only show specific function
py-spy record -o profile.svg --function expensive_computation -- python web_server.py

# Exclude idle threads
py-spy record -o profile.svg --idle -- python web_server.py
```

## Interpreting Flame Graphs

### Example Flame Graph Analysis

```
[======== expensive_computation ========][== database_query ==][sleep]
           (45% of samples)                  (15% of samples)    (30%)
```

### Key Insights

1. **expensive_computation**: 45% of CPU time
   - Optimization target: algorithm or caching
   - Consider async execution if blocking users

2. **database_query**: 15% of time
   - Check if queries can be batched
   - Add database connection pooling
   - Consider caching results

3. **time.sleep**: 30% of time (blocking)
   - Off-CPU time (waiting)
   - Not shown in flame graph (CPU profiling)
   - Use `--idle` flag to capture

### Off-CPU Profiling

```bash
# Capture both CPU and idle time
py-spy record -o profile.svg --idle -p $APP_PID --duration 60

# Shows blocking I/O, sleep, GIL contention
```

## Production Best Practices

### 1. Low Overhead Configuration

```bash
# Recommended for production: 50-100 Hz
py-spy record -o profile.svg -p $APP_PID --rate 50 --duration 60

# Expected overhead: 1-3%
```

### 2. Continuous Profiling Setup

```bash
#!/bin/bash
# continuous_profile.sh

APP_NAME="web_server"
PROFILE_DIR="/var/log/profiles"
DURATION=300  # 5 minutes

while true; do
    timestamp=$(date +%Y%m%d_%H%M%S)
    pid=$(pgrep -f "$APP_NAME")

    if [ -n "$pid" ]; then
        echo "Profiling $APP_NAME (PID: $pid) at $timestamp"
        py-spy record -o "$PROFILE_DIR/profile_$timestamp.svg" \
            -p "$pid" \
            --duration "$DURATION" \
            --rate 50
    fi

    # Wait before next profile
    sleep 3600  # 1 hour
done
```

### 3. Docker Integration

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install py-spy
RUN pip install py-spy

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

# Run with profiling (development)
# CMD ["py-spy", "record", "-o", "/tmp/profile.svg", "--", "python", "web_server.py"]

# Normal run (production)
CMD ["python", "web_server.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./profiles:/tmp/profiles
    # Add capability for py-spy to attach
    cap_add:
      - SYS_PTRACE
```

### 4. Kubernetes Profiling

```yaml
# deployment.yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-profiler
spec:
  containers:
  - name: app
    image: myapp:latest
    securityContext:
      capabilities:
        add: ["SYS_PTRACE"]

  - name: profiler
    image: myapp:latest
    command:
      - sh
      - -c
      - |
        while true; do
          sleep 300
          py-spy record -o /tmp/profiles/profile_$(date +%s).svg \
            -p $(pgrep -f "python web_server.py") \
            --duration 60
        done
    volumeMounts:
      - name: profiles
        mountPath: /tmp/profiles

  volumes:
  - name: profiles
    persistentVolumeClaim:
      claimName: profiles-pvc
```

## Troubleshooting

### Issue: Permission denied
```bash
# Run with sudo
sudo py-spy record -o profile.svg -p $APP_PID

# Or add capability to user
sudo setcap cap_sys_ptrace+ep $(which py-spy)
```

### Issue: Cannot attach to Python process
```bash
# Check Python version compatibility
py-spy --version
python --version

# py-spy supports Python 2.7-3.11+
```

### Issue: Flame graph too cluttered
```bash
# Increase minimum sample threshold
py-spy record -o profile.svg -p $APP_PID --duration 60

# Then filter SVG manually or use speedscope format:
py-spy record -o profile.speedscope --format speedscope -p $APP_PID
# Open in speedscope.app with search/filter
```

## Comparison with cProfile

| Feature                | py-spy          | cProfile        |
|------------------------|-----------------|-----------------|
| Overhead               | 1-3%            | 5-20%           |
| Production-safe        | Yes             | Marginal        |
| Sampling vs Deterministic | Sampling    | Deterministic   |
| Attach to running      | Yes             | No              |
| C extensions visible   | Yes (with --native) | No          |
| Multi-threaded support | Yes             | Limited         |
| Flame graph generation | Built-in        | Requires tools  |

## Summary

- **py-spy**: Production-safe sampling profiler
- **Overhead**: 1-3% (safe for continuous profiling)
- **Use Cases**: Production debugging, continuous profiling
- **Flame Graphs**: Instant visualization
- **Alternative to**: cProfile (development), production profiling
