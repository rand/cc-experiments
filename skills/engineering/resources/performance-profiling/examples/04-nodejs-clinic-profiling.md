# Example 4: Node.js Profiling with Clinic.js Suite

This example demonstrates comprehensive Node.js profiling using the Clinic.js suite for CPU, async operations, and memory analysis.

## Prerequisites

```bash
npm install -g clinic
```

## Sample Node.js Application

```javascript
// server.js
const express = require('express');
const crypto = require('crypto');
const fs = require('fs').promises;

const app = express();

// CPU-intensive endpoint
app.get('/api/hash', async (req, res) => {
    const iterations = 100000;
    const hashes = [];

    for (let i = 0; i < iterations; i++) {
        const hash = crypto.createHash('sha256');
        hash.update(`data-${i}`);
        hashes.push(hash.digest('hex'));
    }

    res.json({ count: hashes.length });
});

// I/O-intensive endpoint
app.get('/api/files', async (req, res) => {
    const files = [];

    for (let i = 0; i < 100; i++) {
        try {
            const content = await fs.readFile(`./data/file${i}.txt`, 'utf8');
            files.push({ id: i, length: content.length });
        } catch (error) {
            files.push({ id: i, error: 'not found' });
        }
    }

    res.json({ files });
});

// Async waterfall (bad pattern)
app.get('/api/waterfall', async (req, res) => {
    const results = [];

    // Sequential instead of parallel (inefficient)
    for (let i = 0; i < 10; i++) {
        const result = await new Promise(resolve => {
            setTimeout(() => resolve(i * 2), 100);
        });
        results.push(result);
    }

    res.json({ results });
});

// Async parallel (good pattern)
app.get('/api/parallel', async (req, res) => {
    const promises = [];

    for (let i = 0; i < 10; i++) {
        promises.push(new Promise(resolve => {
            setTimeout(() => resolve(i * 2), 100);
        }));
    }

    const results = await Promise.all(promises);
    res.json({ results });
});

// Memory leak example (intentional)
const leakyCache = [];
app.get('/api/leak', (req, res) => {
    // Accumulates without clearing
    leakyCache.push(Buffer.alloc(1024 * 1024)); // 1MB per request
    res.json({ cached: leakyCache.length });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
```

## Clinic Doctor: Overall Health Check

### Profile and Analyze

```bash
# Start with profiling
clinic doctor -- node server.js

# Generate load in another terminal
npm install -g autocannon
autocannon -c 10 -d 30 http://localhost:3000/api/hash

# Stop server (Ctrl+C)
# Opens HTML report in browser automatically
```

### Interpreting Doctor Report

**Metrics analyzed**:
1. **CPU Usage**: High sustained CPU indicates compute bottleneck
2. **Memory**: Growing trend indicates leak
3. **Event Loop Delay**: High delay = blocked event loop
4. **Active Handles**: Growing handles = resource leak

**Recommendations**:
- "Detected blocking synchronous I/O" → Use async I/O
- "Event loop delay detected" → Reduce CPU-intensive work
- "Memory growth detected" → Check for memory leaks

## Clinic Flame: CPU Profiling with Flame Graph

### Profile and Generate Flame Graph

```bash
# CPU profiling with flame graph
clinic flame -- node server.js

# Generate load
autocannon -c 10 -d 30 http://localhost:3000/api/hash

# Stop server (Ctrl+C)
# Opens flame graph in browser
```

### Interpreting Flame Graph

```
[======== crypto.createHash ========][== hash.digest ==][= express routing =]
         (70% of samples)                (20%)               (5%)
```

**Key insights**:
- **Wide plateaus**: Hot functions (crypto.createHash)
- **Stack depth**: Call hierarchy
- **X-axis**: Alphabetical (NOT time)

**Optimization**:
- Move crypto operations to worker threads
- Implement caching for repeated hashes
- Use faster hash algorithms if security allows

## Clinic Bubbleprof: Async Operations

### Profile Async Bottlenecks

```bash
# Async operation profiling
clinic bubbleprof -- node server.js

# Test waterfall endpoint
autocannon -c 5 -d 20 http://localhost:3000/api/waterfall

# Stop server
# Opens bubble graph
```

### Interpreting Bubble Graph

**Visualization**:
- **Bubbles**: Async operations
- **Bubble size**: Duration
- **Lines**: Dependencies between operations
- **Clusters**: Related operations

**Common patterns**:
- **Waterfall**: Sequential operations (bad)
  ```
  Op1 → Op2 → Op3 → Op4  (total: sum of all)
  ```
- **Parallel**: Concurrent operations (good)
  ```
  Op1 ↘
  Op2 → Result  (total: max of all)
  Op3 ↗
  ```

**Optimization**:
```javascript
// Before (waterfall)
for (const item of items) {
    await processItem(item);  // Sequential
}

// After (parallel)
await Promise.all(items.map(item => processItem(item)));
```

## Clinic Heapprofiler: Memory Analysis

### Profile Memory Allocations

```bash
# Memory profiling
clinic heapprofiler -- node server.js

# Trigger memory leak
for i in {1..100}; do
    curl http://localhost:3000/api/leak
done

# Stop server
# Opens heap profile
```

### Interpreting Heap Profile

**Metrics**:
- **Allocated Space**: Total memory allocated
- **Retained Size**: Memory kept alive by object
- **Shallow Size**: Object size itself

**Finding Leaks**:
1. Take heap snapshot at baseline
2. Perform operations that might leak
3. Take another snapshot
4. Compare snapshots to find growing objects

**Example**:
```
Object Type          | Count | Retained Size
---------------------|-------|---------------
(array)              | 1,500 |    1,500 MB  ← Growing!
Buffer               |   150 |      150 MB
(string)             | 2,300 |       23 MB
```

## CLI Options

### Common Flags

```bash
# Collect profile without opening report
clinic doctor --collect-only -- node server.js

# Open existing profile
clinic doctor --visualize-only <PID>.clinic-doctor

# Output to specific directory
clinic doctor --dest=./profiles -- node server.js

# Sample interval (for flame)
clinic flame --sample-interval=100 -- node server.js  # 100µs

# Kernel tracing (flame, requires privileges)
sudo clinic flame --kernel-tracing -- node server.js
```

## Comparison: Clinic Tools

| Tool        | Purpose                    | Overhead | Output        |
|-------------|----------------------------|----------|---------------|
| Doctor      | Overall health check       | Low      | HTML report   |
| Flame       | CPU profiling              | Medium   | Flame graph   |
| Bubbleprof  | Async operations           | High     | Bubble graph  |
| Heapprofiler| Memory allocations         | Medium   | Heap profile  |

## Production Best Practices

### 1. Pre-Production Profiling

```bash
#!/bin/bash
# profile_before_deploy.sh

APP="server.js"
PROFILE_DIR="./profiles/$(date +%Y%m%d_%H%M%S)"

# Doctor analysis
clinic doctor --dest="$PROFILE_DIR/doctor" -- node "$APP" &
PID=$!
sleep 5
autocannon -c 10 -d 30 http://localhost:3000/api/hash
kill $PID

# Flame analysis
clinic flame --dest="$PROFILE_DIR/flame" -- node "$APP" &
PID=$!
sleep 5
autocannon -c 10 -d 30 http://localhost:3000/api/hash
kill $PID

echo "Profiles saved to $PROFILE_DIR"
```

### 2. CI Integration

```yaml
# .github/workflows/profile.yml
name: Profile Performance

on: [pull_request]

jobs:
  profile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - run: npm install
      - run: npm install -g clinic autocannon

      - name: Profile with Doctor
        run: |
          clinic doctor --collect-only -- node server.js &
          APP_PID=$!
          sleep 5
          autocannon -c 10 -d 20 http://localhost:3000/api/hash
          kill $APP_PID || true

      - name: Upload profiles
        uses: actions/upload-artifact@v3
        with:
          name: clinic-profiles
          path: |
            **/*.clinic-doctor/
```

### 3. Continuous Profiling (Not Recommended in Production)

Clinic.js has relatively high overhead. For production, use:
- Node.js built-in profiler (lower overhead)
- External APM tools (Datadog, New Relic)
- Google Cloud Profiler

## Alternatives

### Built-in Node.js Profiler

```bash
# V8 profiler (lower overhead)
node --prof server.js

# Generate load
autocannon -c 10 -d 30 http://localhost:3000/api/hash

# Process profile
node --prof-process isolate-*.log > processed.txt
```

### Chrome DevTools

```bash
# Start with inspector
node --inspect server.js

# Open Chrome DevTools
# chrome://inspect
# Click "inspect" → Profiler tab
```

### 0x (Quick Flame Graphs)

```bash
npm install -g 0x

# Profile and generate flame graph
0x server.js

# Opens browser with flame graph
```

## Troubleshooting

### Issue: "ENOSPC: System limit for number of file watchers reached"
```bash
# Increase inotify watchers (Linux)
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Issue: High overhead affecting results
```bash
# Use sampling profiler instead
0x server.js  # Lower overhead than Clinic Flame
```

### Issue: Missing CPU events (Flame)
```bash
# Enable kernel tracing (requires root)
sudo clinic flame --kernel-tracing -- node server.js
```

## Summary

- **Clinic.js**: Comprehensive Node.js profiling suite
- **Doctor**: Overall health check (low overhead)
- **Flame**: CPU profiling with flame graphs
- **Bubbleprof**: Async operation visualization
- **Heapprofiler**: Memory allocation tracking
- **Use Case**: Pre-production profiling, development
- **Production Alternative**: Built-in profiler, APM tools
