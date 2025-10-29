# Example 7: Continuous Profiling with Pyroscope

This example demonstrates setting up continuous profiling infrastructure using Pyroscope for always-on, low-overhead profiling in production.

## Overview

**Pyroscope** provides:
- Always-on profiling (<2% overhead)
- Historical performance data
- Multi-language support (Python, Go, Node.js, Ruby, Java, .NET)
- Tag-based filtering (version, region, environment)
- Diff views for A/B testing

## Architecture

```
Application → Pyroscope Agent → Pyroscope Server → Web UI
                 (push mode)
```

## Installation

### Pyroscope Server (Docker)

```bash
# Run Pyroscope server
docker run -d \
  --name pyroscope \
  -p 4040:4040 \
  pyroscope/pyroscope:latest server
```

### Pyroscope Server (Kubernetes)

```bash
# Add Helm repository
helm repo add pyroscope-io https://pyroscope-io.github.io/helm-chart
helm repo update

# Install
helm install pyroscope pyroscope-io/pyroscope \
  --namespace monitoring \
  --create-namespace
```

## Python Integration

### Installation

```bash
pip install pyroscope-io
```

### Basic Integration

```python
# app.py
import pyroscope

# Initialize Pyroscope
pyroscope.configure(
    application_name="myapp.backend",
    server_address="http://pyroscope:4040",
    tags={
        "env": "production",
        "region": "us-west-2",
        "version": "1.2.3"
    }
)

# Your application code
def expensive_function():
    result = 0
    for i in range(1000000):
        result += i ** 2
    return result

def main():
    while True:
        expensive_function()
        time.sleep(1)

if __name__ == "__main__":
    main()
```

### Flask Application

```python
# flask_app.py
from flask import Flask
import pyroscope

app = Flask(__name__)

# Configure Pyroscope
pyroscope.configure(
    application_name="myapp.api",
    server_address="http://localhost:4040",
    tags={
        "env": "production"
    }
)

@app.route('/api/compute')
def compute():
    result = sum(i**2 for i in range(100000))
    return {"result": result}

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
```

### Dynamic Tags

```python
import pyroscope

pyroscope.configure(
    application_name="myapp",
    server_address="http://localhost:4040"
)

# Add tags dynamically per request
@pyroscope.tag_wrapper({"endpoint": "/api/users"})
def get_users():
    # Profiling data tagged with endpoint="/api/users"
    return query_database()

# Tag specific code blocks
with pyroscope.tag_wrapper({"operation": "database_query"}):
    results = execute_query()
```

## Go Integration

### Installation

```bash
go get github.com/pyroscope-io/client/pyroscope
```

### Basic Integration

```go
// main.go
package main

import (
    "time"
    "github.com/pyroscope-io/client/pyroscope"
)

func expensiveComputation() {
    for i := 0; i < 1000000; i++ {
        _ = i * i
    }
}

func main() {
    // Initialize Pyroscope
    pyroscope.Start(pyroscope.Config{
        ApplicationName: "myapp.backend",
        ServerAddress:   "http://localhost:4040",
        Tags: map[string]string{
            "env":     "production",
            "region":  "us-west-2",
            "version": "1.2.3",
        },
        ProfileTypes: []pyroscope.ProfileType{
            pyroscope.ProfileCPU,
            pyroscope.ProfileAllocObjects,
            pyroscope.ProfileAllocSpace,
            pyroscope.ProfileInuseObjects,
            pyroscope.ProfileInuseSpace,
        },
    })

    // Application code
    for {
        expensiveComputation()
        time.Sleep(time.Second)
    }
}
```

### HTTP Handler Integration

```go
package main

import (
    "net/http"
    "github.com/pyroscope-io/client/pyroscope"
)

func handler(w http.ResponseWriter, r *http.Request) {
    // Tag this request
    pyroscope.TagWrapper(r.Context(), pyroscope.Labels("endpoint", "/api/data"), func(ctx context.Context) {
        // Handler code with tagging
        result := processData()
        w.Write([]byte(result))
    })
}

func main() {
    pyroscope.Start(pyroscope.Config{
        ApplicationName: "myapp.api",
        ServerAddress:   "http://localhost:4040",
    })

    http.HandleFunc("/api/data", handler)
    http.ListenAndServe(":8080", nil)
}
```

## Node.js Integration

### Installation

```bash
npm install @pyroscope/nodejs
```

### Basic Integration

```javascript
// app.js
const Pyroscope = require('@pyroscope/nodejs');

// Initialize
Pyroscope.init({
  serverAddress: 'http://localhost:4040',
  appName: 'myapp.backend',
  tags: {
    env: 'production',
    region: 'us-west-2',
    version: '1.2.3'
  }
});

Pyroscope.start();

// Application code
function expensiveComputation() {
  let result = 0;
  for (let i = 0; i < 1000000; i++) {
    result += i ** 2;
  }
  return result;
}

setInterval(() => {
  expensiveComputation();
}, 1000);
```

### Express Integration

```javascript
const express = require('express');
const Pyroscope = require('@pyroscope/nodejs');

const app = express();

Pyroscope.init({
  serverAddress: 'http://localhost:4040',
  appName: 'myapp.api',
  tags: {
    env: 'production'
  }
});

Pyroscope.start();

app.get('/api/compute', (req, res) => {
  // Profiling automatically captures this endpoint
  const result = expensiveComputation();
  res.json({ result });
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

## Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  pyroscope:
    image: pyroscope/pyroscope:latest
    ports:
      - "4040:4040"
    command:
      - server
    volumes:
      - pyroscope-data:/var/lib/pyroscope

  app:
    build: .
    environment:
      PYROSCOPE_SERVER_ADDRESS: http://pyroscope:4040
      PYROSCOPE_APPLICATION_NAME: myapp.backend
    depends_on:
      - pyroscope

volumes:
  pyroscope-data:
```

## Kubernetes Deployment

```yaml
# pyroscope-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pyroscope
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pyroscope
  template:
    metadata:
      labels:
        app: pyroscope
    spec:
      containers:
      - name: pyroscope
        image: pyroscope/pyroscope:latest
        args:
          - server
        ports:
        - containerPort: 4040
        volumeMounts:
        - name: pyroscope-storage
          mountPath: /var/lib/pyroscope
      volumes:
      - name: pyroscope-storage
        persistentVolumeClaim:
          claimName: pyroscope-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: pyroscope
  namespace: monitoring
spec:
  selector:
    app: pyroscope
  ports:
  - port: 4040
    targetPort: 4040
```

```yaml
# application-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:latest
        env:
        - name: PYROSCOPE_SERVER_ADDRESS
          value: "http://pyroscope.monitoring:4040"
        - name: PYROSCOPE_APPLICATION_NAME
          value: "myapp"
        - name: PYROSCOPE_TAGS
          value: "env=production,region=us-west-2"
```

## Using the Pyroscope UI

### Access Web Interface

```bash
# Open browser
http://localhost:4040
```

### Key Features

1. **Timeline View**
   - Flame graph with time slider
   - Zoom into specific time ranges
   - Compare different time periods

2. **Tag Filtering**
   - Filter by environment, version, region
   - Multi-dimensional filtering
   - Dynamic tag exploration

3. **Comparison Mode**
   - Compare two time periods
   - Diff view (red = regression, green = improvement)
   - A/B testing analysis

4. **Single Profiling View**
   - Traditional flame graph
   - Function table
   - Export to JSON

### Example Queries

```
# All profiles for application
myapp

# Specific environment
myapp{env="production"}

# Multiple tags
myapp{env="production",region="us-west-2"}

# Specific version
myapp{version="1.2.3"}

# Compare versions
myapp{version="1.2.3"} vs myapp{version="1.2.4"}
```

## Advanced Configuration

### Sampling Rate

```python
# Python: Adjust sampling frequency
pyroscope.configure(
    application_name="myapp",
    server_address="http://localhost:4040",
    sample_rate=100,  # Hz (default: 100)
)
```

```go
// Go: Adjust sampling frequency
pyroscope.Start(pyroscope.Config{
    ApplicationName: "myapp",
    ServerAddress:   "http://localhost:4040",
    SampleRate:      100, // Hz
})
```

### Authentication

```python
# With authentication
pyroscope.configure(
    application_name="myapp",
    server_address="http://localhost:4040",
    auth_token="secret-token",
)
```

### Self-Hosted with Ingestion

```yaml
# pyroscope-server.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pyroscope-config
data:
  config.yaml: |
    log-level: info
    storage-path: /var/lib/pyroscope
    api-bind-addr: :4040
    retention-policy:
      max-age: 720h  # 30 days
```

## Best Practices

### 1. Tag Strategy

```python
# Good tagging strategy
pyroscope.configure(
    application_name="myapp",
    server_address="http://localhost:4040",
    tags={
        "env": os.getenv("ENV", "dev"),           # Environment
        "region": os.getenv("REGION", "unknown"), # Region
        "version": os.getenv("VERSION", "dev"),   # Version
        "host": socket.gethostname(),             # Host
    }
)
```

### 2. Cardinality Management

```
❌ High cardinality tags (avoid):
   - user_id: "12345"
   - session_id: "abc123"
   - request_id: "xyz789"

✓ Low cardinality tags (use):
   - env: "production"
   - region: "us-west-2"
   - version: "1.2.3"
   - endpoint: "/api/users"
```

### 3. Conditional Profiling

```python
# Enable only in specific environments
if os.getenv("ENABLE_PROFILING", "false").lower() == "true":
    pyroscope.configure(
        application_name="myapp",
        server_address="http://localhost:4040",
    )
```

### 4. Resource Limits

```yaml
# Kubernetes resource limits for Pyroscope server
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

## Monitoring and Alerting

### Prometheus Metrics

```yaml
# Pyroscope exposes Prometheus metrics at /metrics
# Add to Prometheus scrape config:
scrape_configs:
  - job_name: 'pyroscope'
    static_configs:
      - targets: ['pyroscope:4040']
```

### Alert on Performance Regressions

```yaml
# prometheus-alert.yaml
groups:
  - name: performance
    rules:
      - alert: CPUUsageSpike
        expr: rate(pyroscope_cpu_seconds_total[5m]) > 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected in {{ $labels.app_name }}"
```

## Troubleshooting

### Issue: No profiles appearing

```bash
# Check connectivity
curl http://localhost:4040/healthz

# Check application logs for Pyroscope errors
# Ensure server_address is correct
```

### Issue: High memory usage

```bash
# Reduce retention period
pyroscope server --retention-policy.max-age=168h  # 7 days

# Or configure in config file
```

### Issue: Overhead too high

```python
# Reduce sampling rate
pyroscope.configure(
    application_name="myapp",
    server_address="http://localhost:4040",
    sample_rate=50,  # 50 Hz instead of default 100 Hz
)
```

## Comparison with Alternatives

| Feature              | Pyroscope | Parca (eBPF) | Cloud Profiler |
|----------------------|-----------|--------------|----------------|
| Language support     | Multiple  | Any          | Multiple       |
| Overhead             | 1-2%      | <1%          | 1-2%           |
| Infrastructure       | Self-hosted| Self-hosted | Managed        |
| Cost                 | Free OSS  | Free OSS     | Paid           |
| eBPF-based           | No        | Yes          | No             |

## Summary

- **Pyroscope**: Open-source continuous profiling platform
- **Overhead**: 1-2% (safe for production)
- **Languages**: Python, Go, Node.js, Ruby, Java, .NET, Rust
- **Features**: Historical data, tags, comparison, flame graphs
- **Deployment**: Docker, Kubernetes, self-hosted
- **Use Case**: Always-on production profiling with historical analysis
