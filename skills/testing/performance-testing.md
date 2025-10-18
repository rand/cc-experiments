---
name: testing-performance-testing
description: Measure system performance under load (response time, throughput)
---



# Performance Testing

## When to Use This Skill

Use this skill when you need to:
- Measure system performance under load (response time, throughput)
- Identify bottlenecks in applications and APIs
- Verify service level objectives (SLOs) and SLAs
- Test scalability and capacity limits
- Simulate realistic user behavior patterns
- Benchmark before and after optimizations
- Plan infrastructure capacity and scaling strategies

**ACTIVATE THIS SKILL**: When validating performance requirements, optimizing systems, or planning capacity

## Core Concepts

### Types of Performance Tests

**Load Testing**: Normal expected load
- Goal: Verify system handles typical traffic
- Example: 1,000 concurrent users, sustained for 1 hour
- Metrics: Response time, throughput, error rate

**Stress Testing**: Beyond normal capacity
- Goal: Find breaking point
- Example: Gradually increase to 10,000 users
- Metrics: When does system start failing?

**Spike Testing**: Sudden traffic surge
- Goal: Handle sudden spikes (flash sales, viral content)
- Example: 100 → 5,000 users in 30 seconds
- Metrics: Recovery time, error rate during spike

**Soak Testing**: Sustained load over time
- Goal: Detect memory leaks, resource exhaustion
- Example: 1,000 users for 24 hours
- Metrics: Memory usage, connection pool exhaustion

**Scalability Testing**: System scales with resources
- Goal: Verify horizontal/vertical scaling
- Example: 1 server → 5 servers, does throughput 5x?
- Metrics: Throughput per server, efficiency

### Key Metrics

**Response Time**:
- p50 (median): 50% of requests faster than this
- p95: 95% of requests faster (typical SLO)
- p99: 99% of requests faster (outlier detection)
- Max: Slowest request (can indicate issues)

**Throughput**:
- Requests per second (RPS)
- Transactions per minute (TPM)
- Data transferred (MB/s)

**Error Rate**:
- HTTP errors (4xx, 5xx)
- Timeouts
- Connection failures

**Resource Utilization**:
- CPU usage (%)
- Memory usage (MB/GB)
- Network I/O (MB/s)
- Disk I/O (IOPS)

### Performance Testing Tools

**k6** (Recommended, modern):
- JavaScript-based test scripts
- Great developer experience
- Real-time metrics
- Cloud and local execution

**Locust** (Python-based):
- Python test scripts
- Web-based UI
- Distributed load generation
- Easy to extend

**JMeter** (Java-based, legacy):
- GUI-based test creation
- Wide protocol support
- Large ecosystem
- Heavy and complex

**Apache Bench (ab)** (Simple CLI):
- Quick one-liners
- Basic load testing
- No scripting required
- Limited features

## Patterns

### Basic Load Test (k6)

```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],   // Error rate < 1%
  },
};

// Test scenario
export default function () {
  // Test homepage
  const res = http.get('https://api.example.com/');

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  sleep(1); // Think time between requests
}
```

```bash
# Run test
k6 run load-test.js

# Output:
# ✓ status is 200
# ✓ response time < 500ms
#
# http_req_duration..........: avg=234ms min=102ms med=215ms max=876ms p(95)=456ms
# http_req_failed............: 0.12%
# http_reqs..................: 45000 (150/s)
# vus........................: 100
```

### API Load Test with Authentication

```javascript
// api-load-test.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },
    { duration: '3m', target: 50 },
    { duration: '1m', target: 0 },
  ],
};

// Setup: Run once before test
export function setup() {
  // Authenticate and get token
  const loginRes = http.post('https://api.example.com/auth/login', {
    username: 'test@example.com',
    password: 'testpass123',
  });

  const token = loginRes.json('access_token');
  return { token };
}

// Main test
export default function (data) {
  const headers = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  };

  // GET request
  const getRes = http.get('https://api.example.com/api/users', { headers });
  check(getRes, {
    'GET status 200': (r) => r.status === 200,
    'GET has users': (r) => r.json('users').length > 0,
  });

  // POST request
  const payload = JSON.stringify({
    name: 'Test User',
    email: `user-${__VU}-${__ITER}@example.com`,
  });

  const postRes = http.post('https://api.example.com/api/users', payload, { headers });
  check(postRes, {
    'POST status 201': (r) => r.status === 201,
    'POST returns ID': (r) => r.json('id') !== null,
  });
}
```

### Stress Test (Find Breaking Point)

```javascript
// stress-test.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Normal load
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },   // Increase load
    { duration: '5m', target: 200 },
    { duration: '2m', target: 300 },   // Further increase
    { duration: '5m', target: 300 },
    { duration: '2m', target: 400 },   // Push to limits
    { duration: '5m', target: 400 },
    { duration: '10m', target: 0 },    // Recovery
  ],
  thresholds: {
    http_req_duration: ['p(99)<1000'],
    http_req_failed: ['rate<0.05'],
  },
};

export default function () {
  const res = http.get('https://api.example.com/heavy-endpoint');

  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}

// Analyze output to find where error rate spikes
// Example: System stable at 300 users, errors at 400+ → Capacity is ~300 users
```

### Spike Test (Sudden Traffic)

```javascript
// spike-test.js
export const options = {
  stages: [
    { duration: '10s', target: 100 },   // Normal traffic
    { duration: '1m', target: 100 },
    { duration: '10s', target: 1400 },  // SPIKE! 14x increase
    { duration: '3m', target: 1400 },   // Sustained spike
    { duration: '10s', target: 100 },   // Recovery
    { duration: '3m', target: 100 },
    { duration: '10s', target: 0 },
  ],
};

export default function () {
  http.get('https://api.example.com/');
}

// Key metric: How quickly does error rate drop after spike?
// Good system: Errors during spike, recovers within 30s
// Bad system: Errors persist after spike ends (resource exhaustion)
```

### Soak Test (Endurance)

```javascript
// soak-test.js
export const options = {
  stages: [
    { duration: '5m', target: 100 },   // Ramp up
    { duration: '24h', target: 100 },  // Sustained load for 24 hours
    { duration: '5m', target: 0 },     // Ramp down
  ],
};

export default function () {
  http.get('https://api.example.com/');
}

// Monitor system metrics over 24 hours:
// - Memory usage: Should be stable (not climbing)
// - Response time: Should remain consistent
// - Error rate: Should stay low
// - DB connections: Should not exhaust pool
```

## Examples by Tool

### Locust (Python)

```python
# locustfile.py
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3s between requests

    def on_start(self):
        """Run once per user on start"""
        # Login
        self.client.post("/auth/login", json={
            "username": "test@example.com",
            "password": "testpass123"
        })

    @task(3)  # Weight: 3x more likely than other tasks
    def view_homepage(self):
        self.client.get("/")

    @task(2)
    def view_product(self):
        product_id = random.randint(1, 100)
        self.client.get(f"/products/{product_id}")

        # Add to cart
        self.client.post(f"/cart/add", json={
            "product_id": product_id,
            "quantity": 1
        })

    @task(1)
    def checkout(self):
        # View cart
        self.client.get("/cart")

        # Checkout
        self.client.post("/checkout", json={
            "payment_method": "credit_card"
        })

# Run:
# locust -f locustfile.py --host=https://api.example.com
# Open http://localhost:8089 (Web UI)
```

### Apache Bench (Quick Tests)

```bash
# Simple load test: 1000 requests, 10 concurrent
ab -n 1000 -c 10 https://api.example.com/

# With POST data
ab -n 1000 -c 10 -p data.json -T application/json https://api.example.com/api/users

# With authentication
ab -n 1000 -c 10 -H "Authorization: Bearer TOKEN" https://api.example.com/protected

# Output:
# Requests per second:    150.23 [#/sec] (mean)
# Time per request:       66.566 [ms] (mean)
# Time per request:       6.657 [ms] (mean, across all concurrent requests)
# Transfer rate:          245.67 [Kbytes/sec] received
#
# Percentage of requests served within a certain time (ms)
#   50%     62
#   66%     68
#   75%     73
#   80%     76
#   90%     85
#   95%     95
#   98%    105
#   99%    112
#  100%    234 (longest request)
```

### JMeter (GUI-based)

```xml
<!-- test-plan.jmx (simplified) -->
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2">
  <hashTree>
    <TestPlan>
      <stringProp name="TestPlan.comments">API Load Test</stringProp>
      <boolProp name="TestPlan.functional_mode">false</boolProp>
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>

      <ThreadGroup guiclass="ThreadGroupGui">
        <stringProp name="ThreadGroup.num_threads">100</stringProp>
        <stringProp name="ThreadGroup.ramp_time">60</stringProp>
        <stringProp name="ThreadGroup.duration">300</stringProp>

        <HTTPSamplerProxy>
          <stringProp name="HTTPSampler.domain">api.example.com</stringProp>
          <stringProp name="HTTPSampler.port">443</stringProp>
          <stringProp name="HTTPSampler.protocol">https</stringProp>
          <stringProp name="HTTPSampler.path">/api/users</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
        </HTTPSamplerProxy>
      </ThreadGroup>
    </TestPlan>
  </hashTree>
</jmeterTestPlan>
```

```bash
# Run JMeter test (command line)
jmeter -n -t test-plan.jmx -l results.jtl -e -o report/

# Generate HTML report
jmeter -g results.jtl -o report/
```

## Interpreting Results

### Good Performance Profile

```
Metrics:
  p50: 120ms   (median response time)
  p95: 350ms   (95th percentile)
  p99: 580ms   (99th percentile)
  max: 1.2s    (outliers exist but rare)
  error rate: 0.05%

Analysis: ✅
- Most requests fast (p50 = 120ms)
- Tail latency acceptable (p95 < 500ms)
- Very few errors
- System is stable
```

### Warning Signs

```
Metrics:
  p50: 800ms   (median slow)
  p95: 5.2s    (tail latency very high)
  p99: 12s     (extremely slow)
  max: 30s     (timeouts)
  error rate: 3.5%

Analysis: ⚠️
- Median response time too high
- Wide gap between p50 and p95 (inconsistent performance)
- High error rate
- Likely bottleneck (database? cache? CPU?)

Action:
1. Profile application (find slow queries, hot code paths)
2. Check resource utilization (CPU, memory, DB connections)
3. Review logs for errors
4. Consider scaling or optimization
```

### Identifying Bottlenecks

**Database Bottleneck**:
```
Symptoms:
- Response time increases linearly with load
- DB CPU/connections maxed out
- Application CPU low

Solution:
- Add database indexes
- Optimize slow queries
- Add read replicas
- Implement caching
```

**CPU Bottleneck**:
```
Symptoms:
- Response time increases with load
- CPU usage 90-100%
- Queue depth increases

Solution:
- Optimize hot code paths
- Add horizontal scaling
- Use caching
- Offload to background jobs
```

**Memory Bottleneck**:
```
Symptoms:
- Performance degrades over time
- Memory usage climbs
- GC pauses increase

Solution:
- Fix memory leaks
- Increase memory
- Optimize data structures
```

**Network Bottleneck**:
```
Symptoms:
- High latency but low CPU/memory
- Network throughput maxed
- Large response payloads

Solution:
- Compress responses
- Reduce payload size
- CDN for static assets
- Upgrade network capacity
```

## Checklist

**Before Performance Testing**:
- [ ] Define performance goals (SLOs: p95 < 500ms, error < 1%)
- [ ] Identify critical user journeys to test
- [ ] Set up monitoring (APM, logs, metrics)
- [ ] Create test environment (production-like)
- [ ] Prepare test data (realistic dataset)

**Running Tests**:
- [ ] Start with baseline (low load)
- [ ] Gradually increase load (ramp up)
- [ ] Monitor system metrics (CPU, memory, DB)
- [ ] Record results (response times, errors)
- [ ] Test recovery (ramp down, verify cleanup)

**Analyzing Results**:
- [ ] Check p50, p95, p99 response times
- [ ] Verify error rate within threshold
- [ ] Identify bottlenecks (CPU, DB, network)
- [ ] Compare to SLOs/SLAs
- [ ] Document findings and recommendations

**After Testing**:
- [ ] Share results with team
- [ ] Prioritize optimizations
- [ ] Retest after improvements
- [ ] Update capacity plans
- [ ] Set up continuous performance monitoring

## Anti-Patterns

```
❌ NEVER: Test in production without preparation
   → Risk of actual outages

❌ NEVER: Test with unrealistic data (empty DB)
   → Results not representative

❌ NEVER: Only test happy path
   → Miss error handling performance

❌ NEVER: Ignore tail latency (p95, p99)
   → Bad experience for some users

❌ NEVER: Test from single location
   → Miss geographic latency issues

❌ NEVER: Skip monitoring during tests
   → Can't identify bottlenecks

❌ NEVER: Run tests without baseline
   → No comparison for improvements
```

## Related Skills

**Foundation**:
- `unit-testing-patterns.md` - Testing individual components
- `integration-testing.md` - Testing service interactions

**Performance**:
- `profiling-applications.md` - Finding performance bottlenecks
- `database-optimization.md` - Optimizing queries and indexes
- `caching-strategies.md` - Reducing load with caching

**Monitoring**:
- `observability-patterns.md` - Metrics, logs, traces
- `alerting-strategies.md` - Performance alerts

**Tools**:
- k6: Modern, developer-friendly load testing
- Locust: Python-based, distributed testing
- JMeter: Java-based, comprehensive
- Apache Bench: Quick CLI tests
- Artillery: Node.js-based load testing
