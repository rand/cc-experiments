---
name: caching-cache-performance-monitoring
description: Measuring and optimizing cache performance - metrics, monitoring tools, alerts, load testing, and instrumentation for cache hit rates and latency.
---
# Cache Performance Monitoring

**Last Updated**: 2025-10-25

## When to Use This Skill

Use this skill when:
- Measuring cache effectiveness (hit ratio, latency, eviction rate)
- Optimizing cache configuration based on data
- Debugging cache performance issues
- Setting up alerts for cache anomalies
- Load testing applications with caching layers
- Demonstrating cache performance improvements to stakeholders
- Troubleshooting high database load or slow responses

**Prerequisites**: Understanding of `caching-fundamentals.md`, `redis-caching-patterns.md`, `http-caching.md`, and `cdn-edge-caching.md`

## Core Metrics

### Key Performance Indicators (KPIs)

| Metric | Formula | Target | Interpretation |
|--------|---------|--------|----------------|
| **Cache Hit Ratio** | `hits / (hits + misses)` | 85-95% | % of requests served from cache |
| **Cache Miss Ratio** | `misses / (hits + misses)` | 5-15% | % of requests requiring source fetch |
| **Eviction Rate** | `evictions / total_items` | <10% | % of items removed before expiration |
| **Cache Latency** | p50, p95, p99 response time | <5ms (Redis) | Time to retrieve from cache |
| **Cache Memory Usage** | `used_memory / max_memory` | <80% | Memory utilization |
| **Stale Serve Rate** | `stale_responses / total_responses` | Context-dependent | % of stale data served |

### Industry Benchmarks (2024-2025)

```
Redis Cache Hit Ratio: 90-95% (well-configured)
CDN Cache Hit Ratio: 85-95% (optimized)
Browser Cache Hit Ratio: 60-80% (varies by site)

Redis Latency: <1ms p99 (local), <5ms p99 (network)
CDN Latency: 20-50ms TTFB (cached), 200-500ms (miss)

Eviction Rate: <5% (healthy), >20% (undersized cache)
```

## Redis Monitoring

### Redis INFO Command

```python
import redis
from typing import Dict

class RedisMonitor:
    def __init__(self, redis_client: redis.Redis):
        self.client = redis_client

    def get_cache_metrics(self) -> Dict:
        """Extract cache metrics from Redis INFO"""
        info = self.client.info()

        # Memory metrics
        used_memory = info['used_memory_human']
        max_memory = info.get('maxmemory_human', 'unlimited')
        memory_usage_pct = (info['used_memory'] / info.get('maxmemory', float('inf'))) * 100

        # Cache hit/miss metrics
        hits = info['keyspace_hits']
        misses = info['keyspace_misses']
        total_requests = hits + misses
        hit_ratio = (hits / total_requests * 100) if total_requests > 0 else 0

        # Eviction metrics
        evicted_keys = info['evicted_keys']

        # Connection metrics
        connected_clients = info['connected_clients']

        return {
            'used_memory': used_memory,
            'max_memory': max_memory,
            'memory_usage_pct': round(memory_usage_pct, 2),
            'keyspace_hits': hits,
            'keyspace_misses': misses,
            'hit_ratio': round(hit_ratio, 2),
            'evicted_keys': evicted_keys,
            'connected_clients': connected_clients,
            'uptime_days': info['uptime_in_days'],
        }

    def print_metrics(self):
        """Human-readable metrics output"""
        metrics = self.get_cache_metrics()

        print("=== Redis Cache Metrics ===")
        print(f"Memory: {metrics['used_memory']} / {metrics['max_memory']} ({metrics['memory_usage_pct']}%)")
        print(f"Hit Ratio: {metrics['hit_ratio']}%")
        print(f"Cache Hits: {metrics['keyspace_hits']:,}")
        print(f"Cache Misses: {metrics['keyspace_misses']:,}")
        print(f"Evicted Keys: {metrics['evicted_keys']:,}")
        print(f"Connected Clients: {metrics['connected_clients']}")
        print(f"Uptime: {metrics['uptime_days']} days")

# Usage
monitor = RedisMonitor(redis.Redis())
monitor.print_metrics()
```

### Redis Slow Log

```python
class RedisSlowLogMonitor:
    def __init__(self, redis_client: redis.Redis):
        self.client = redis_client

    def get_slow_queries(self, count: int = 10):
        """Get slowest Redis commands"""
        slow_log = self.client.slowlog_get(count)

        print(f"=== Top {count} Slow Redis Commands ===")
        for entry in slow_log:
            # entry: (id, timestamp, duration_microseconds, command, client_addr, client_name)
            cmd_id, timestamp, duration_us, command, *_ = entry
            duration_ms = duration_us / 1000

            print(f"[{duration_ms:.2f}ms] {' '.join(str(c) for c in command)}")

# Configure slow log threshold (10ms)
redis_client.config_set('slowlog-log-slower-than', 10000)  # microseconds
monitor = RedisSlowLogMonitor(redis_client)
monitor.get_slow_queries()
```

### Application-Level Instrumentation

```python
import time
from functools import wraps
from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0

    @property
    def avg_latency_ms(self) -> float:
        total_requests = self.hits + self.misses
        return (self.total_latency_ms / total_requests) if total_requests > 0 else 0


class InstrumentedCache:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client
        self.stats = CacheStats()

    def get(self, key: str) -> Any:
        """Instrumented cache get"""
        start = time.perf_counter()

        try:
            value = self.cache.get(key)
            latency_ms = (time.perf_counter() - start) * 1000
            self.stats.total_latency_ms += latency_ms

            if value:
                self.stats.hits += 1
                print(f"[CACHE HIT] {key} ({latency_ms:.2f}ms)")
            else:
                self.stats.misses += 1
                print(f"[CACHE MISS] {key} ({latency_ms:.2f}ms)")

            return value
        except Exception as e:
            self.stats.errors += 1
            print(f"[CACHE ERROR] {key}: {e}")
            return None

    def print_stats(self):
        """Print accumulated statistics"""
        print("\n=== Cache Performance Stats ===")
        print(f"Hits: {self.stats.hits}")
        print(f"Misses: {self.stats.misses}")
        print(f"Hit Ratio: {self.stats.hit_ratio:.2f}%")
        print(f"Avg Latency: {self.stats.avg_latency_ms:.2f}ms")
        print(f"Errors: {self.stats.errors}")

# Usage
cache = InstrumentedCache(redis_client)
for i in range(100):
    cache.get(f"user:{i}")
cache.print_stats()
```

## HTTP Cache Monitoring

### Analyzing Response Headers

```python
import requests
from datetime import datetime

class HTTPCacheAnalyzer:
    @staticmethod
    def analyze_response(url: str):
        """Analyze HTTP cache headers"""
        response = requests.get(url)

        print(f"=== HTTP Cache Analysis: {url} ===")
        print(f"Status: {response.status_code}")

        # Cache-Control
        cache_control = response.headers.get('Cache-Control', 'Not set')
        print(f"Cache-Control: {cache_control}")

        # ETag
        etag = response.headers.get('ETag', 'Not set')
        print(f"ETag: {etag}")

        # Last-Modified
        last_modified = response.headers.get('Last-Modified', 'Not set')
        print(f"Last-Modified: {last_modified}")

        # Age (time in cache)
        age = response.headers.get('Age', '0')
        print(f"Age: {age}s")

        # X-Cache (CDN cache status)
        x_cache = response.headers.get('X-Cache', 'Not set')
        print(f"X-Cache: {x_cache}")

        # Cloudflare specific
        cf_cache_status = response.headers.get('CF-Cache-Status', 'Not set')
        print(f"CF-Cache-Status: {cf_cache_status}")

        # Calculate freshness
        if 'max-age' in cache_control:
            max_age = int(cache_control.split('max-age=')[1].split(',')[0])
            age_seconds = int(age)
            freshness_pct = ((max_age - age_seconds) / max_age * 100) if max_age > 0 else 0
            print(f"Freshness: {freshness_pct:.1f}% ({max_age - age_seconds}s remaining)")

# Usage
analyzer = HTTPCacheAnalyzer()
analyzer.analyze_response('https://example.com/api/data')
```

### Browser Cache DevTools Automation

```javascript
// JavaScript: Monitor browser cache performance

class BrowserCacheMonitor {
  constructor() {
    this.stats = { cacheHits: 0, cacheMisses: 0 };
  }

  // Monitor Performance API
  analyzeResourceTiming() {
    const resources = performance.getEntriesByType('resource');

    resources.forEach((resource) => {
      const fromCache =
        resource.transferSize === 0 ||
        resource.transferSize < resource.encodedBodySize;

      if (fromCache) {
        this.stats.cacheHits++;
        console.log(`[CACHE HIT] ${resource.name}`);
      } else {
        this.stats.cacheMisses++;
        console.log(`[CACHE MISS] ${resource.name} (${resource.transferSize} bytes)`);
      }
    });

    this.printStats();
  }

  printStats() {
    const total = this.stats.cacheHits + this.stats.cacheMisses;
    const hitRatio = (this.stats.cacheHits / total) * 100;

    console.log('\n=== Browser Cache Performance ===');
    console.log(`Cache Hits: ${this.stats.cacheHits}`);
    console.log(`Cache Misses: ${this.stats.cacheMisses}`);
    console.log(`Hit Ratio: ${hitRatio.toFixed(2)}%`);
  }
}

// Usage (run in browser console)
const monitor = new BrowserCacheMonitor();
monitor.analyzeResourceTiming();
```

## CDN Analytics

### Cloudflare Analytics

```python
import requests
import os
from datetime import datetime, timedelta

class CloudflareAnalytics:
    def __init__(self, api_token: str, zone_id: str):
        self.api_token = api_token
        self.zone_id = zone_id
        self.base_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/analytics"

    def get_cache_metrics(self, since_hours: int = 24):
        """Get Cloudflare cache analytics"""
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
        }

        since = datetime.utcnow() - timedelta(hours=since_hours)
        params = {
            'since': since.isoformat() + 'Z',
        }

        response = requests.get(
            f"{self.base_url}/dashboard",
            headers=headers,
            params=params
        )
        data = response.json()

        if data['success']:
            totals = data['result']['totals']

            requests_total = totals['requests']['all']
            requests_cached = totals['requests']['cached']
            requests_uncached = totals['requests']['uncached']

            cache_hit_ratio = (requests_cached / requests_total * 100) if requests_total > 0 else 0

            bandwidth_total = totals['bandwidth']['all']
            bandwidth_cached = totals['bandwidth']['cached']
            bandwidth_saved_pct = (bandwidth_cached / bandwidth_total * 100) if bandwidth_total > 0 else 0

            print(f"=== Cloudflare Cache Analytics (Last {since_hours}h) ===")
            print(f"Total Requests: {requests_total:,}")
            print(f"Cached Requests: {requests_cached:,}")
            print(f"Uncached Requests: {requests_uncached:,}")
            print(f"Cache Hit Ratio: {cache_hit_ratio:.2f}%")
            print(f"Bandwidth Saved: {bandwidth_saved_pct:.2f}%")

# Usage
analytics = CloudflareAnalytics(
    api_token=os.environ['CLOUDFLARE_API_TOKEN'],
    zone_id=os.environ['CLOUDFLARE_ZONE_ID']
)
analytics.get_cache_metrics(since_hours=24)
```

### Fastly Real-Time Stats

```python
class FastlyAnalytics:
    def __init__(self, api_key: str, service_id: str):
        self.api_key = api_key
        self.service_id = service_id

    def get_realtime_stats(self):
        """Get Fastly real-time cache stats"""
        headers = {'Fastly-Key': self.api_key}
        url = f"https://api.fastly.com/stats/service/{self.service_id}"

        response = requests.get(url, headers=headers)
        data = response.json()

        # Aggregate stats from all datacenters
        total_hits = sum(dc['hits'] for dc in data['data'])
        total_miss = sum(dc['miss'] for dc in data['data'])
        total_pass = sum(dc['pass'] for dc in data['data'])

        total_requests = total_hits + total_miss + total_pass
        hit_ratio = (total_hits / total_requests * 100) if total_requests > 0 else 0

        print("=== Fastly Real-Time Stats ===")
        print(f"Cache Hits: {total_hits:,}")
        print(f"Cache Misses: {total_miss:,}")
        print(f"Cache Pass: {total_pass:,}")
        print(f"Hit Ratio: {hit_ratio:.2f}%")

# Usage
fastly = FastlyAnalytics(
    api_key=os.environ['FASTLY_API_KEY'],
    service_id=os.environ['FASTLY_SERVICE_ID']
)
fastly.get_realtime_stats()
```

## APM Integration

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
cache_requests = Counter('cache_requests_total', 'Total cache requests', ['status'])
cache_latency = Histogram('cache_latency_seconds', 'Cache operation latency')
cache_size = Gauge('cache_size_bytes', 'Current cache size in bytes')

class PrometheusInstrumentedCache:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    @cache_latency.time()
    def get(self, key: str):
        """Cache get with Prometheus instrumentation"""
        value = self.cache.get(key)

        if value:
            cache_requests.labels(status='hit').inc()
        else:
            cache_requests.labels(status='miss').inc()

        return value

    def update_cache_size(self):
        """Update cache size gauge"""
        info = self.cache.info()
        cache_size.set(info['used_memory'])

# Expose metrics endpoint (Flask example)
from flask import Flask
from prometheus_client import generate_latest

app = Flask(__name__)

@app.route('/metrics')
def metrics():
    return generate_latest()
```

### StatsD Integration

```python
from statsd import StatsD

class StatsDInstrumentedCache:
    def __init__(self, redis_client: redis.Redis, statsd_host: str = 'localhost', statsd_port: int = 8125):
        self.cache = redis_client
        self.statsd = StatsD(host=statsd_host, port=statsd_port)

    def get(self, key: str):
        """Cache get with StatsD metrics"""
        start = time.time()
        value = self.cache.get(key)
        duration_ms = (time.time() - start) * 1000

        # Record latency
        self.statsd.timing('cache.latency', duration_ms)

        # Record hit/miss
        if value:
            self.statsd.incr('cache.hits')
        else:
            self.statsd.incr('cache.misses')

        return value
```

## Load Testing with Caching

### Cache Performance Testing

```python
import asyncio
import aiohttp
import time
from statistics import mean, median

class CacheLoadTester:
    def __init__(self, url: str, num_requests: int = 1000):
        self.url = url
        self.num_requests = num_requests
        self.results = []

    async def make_request(self, session: aiohttp.ClientSession, request_id: int):
        """Single request with timing"""
        start = time.perf_counter()

        async with session.get(self.url) as response:
            await response.read()
            latency_ms = (time.perf_counter() - start) * 1000

            # Check cache status
            cache_status = response.headers.get('X-Cache-Status', 'UNKNOWN')

            self.results.append({
                'request_id': request_id,
                'latency_ms': latency_ms,
                'status': response.status,
                'cache_status': cache_status,
            })

    async def run_test(self):
        """Run concurrent load test"""
        print(f"Starting load test: {self.num_requests} requests to {self.url}")

        async with aiohttp.ClientSession() as session:
            tasks = [self.make_request(session, i) for i in range(self.num_requests)]
            await asyncio.gather(*tasks)

        self.analyze_results()

    def analyze_results(self):
        """Analyze load test results"""
        latencies = [r['latency_ms'] for r in self.results]
        cache_hits = sum(1 for r in self.results if 'HIT' in r.get('cache_status', ''))
        cache_misses = sum(1 for r in self.results if 'MISS' in r.get('cache_status', ''))

        print("\n=== Load Test Results ===")
        print(f"Total Requests: {len(self.results)}")
        print(f"Cache Hits: {cache_hits}")
        print(f"Cache Misses: {cache_misses}")
        print(f"Hit Ratio: {cache_hits / len(self.results) * 100:.2f}%")
        print(f"\nLatency:")
        print(f"  Mean: {mean(latencies):.2f}ms")
        print(f"  Median: {median(latencies):.2f}ms")
        print(f"  p95: {sorted(latencies)[int(len(latencies) * 0.95)]:.2f}ms")
        print(f"  p99: {sorted(latencies)[int(len(latencies) * 0.99)]:.2f}ms")

# Usage
tester = CacheLoadTester('https://example.com/api/data', num_requests=1000)
asyncio.run(tester.run_test())
```

## Alerts and Anomaly Detection

### Alert Thresholds

```python
class CacheAlertManager:
    def __init__(self, redis_monitor: RedisMonitor):
        self.monitor = redis_monitor

    def check_alerts(self) -> list[str]:
        """Check cache metrics against thresholds"""
        metrics = self.monitor.get_cache_metrics()
        alerts = []

        # Alert: Low hit ratio
        if metrics['hit_ratio'] < 80:
            alerts.append(f"⚠️  Low cache hit ratio: {metrics['hit_ratio']}% (threshold: 80%)")

        # Alert: High memory usage
        if metrics['memory_usage_pct'] > 90:
            alerts.append(f"🚨 High memory usage: {metrics['memory_usage_pct']}% (threshold: 90%)")

        # Alert: High eviction rate
        total_keys = metrics['keyspace_hits'] + metrics['keyspace_misses']
        eviction_rate = (metrics['evicted_keys'] / total_keys * 100) if total_keys > 0 else 0
        if eviction_rate > 10:
            alerts.append(f"⚠️  High eviction rate: {eviction_rate:.2f}% (threshold: 10%)")

        # Alert: Too many connected clients
        if metrics['connected_clients'] > 1000:
            alerts.append(f"⚠️  High client count: {metrics['connected_clients']} (threshold: 1000)")

        return alerts

    def send_alerts(self):
        """Check and send alerts"""
        alerts = self.check_alerts()

        if alerts:
            print("=== Cache Alerts ===")
            for alert in alerts:
                print(alert)
                # Send to alerting system (PagerDuty, Slack, etc.)
        else:
            print("✅ All cache metrics within normal range")

# Usage
alert_manager = CacheAlertManager(monitor)
alert_manager.send_alerts()
```

## Anti-Patterns

### ❌ Not Monitoring Cache Performance

```python
# WRONG: Deploy caching without monitoring
cache.set("user:123", data)  # No metrics, no alerts

# CORRECT: Instrument all cache operations
instrumented_cache.set("user:123", data)  # Tracks hits, misses, latency
```

### ❌ Ignoring Cache Hit Ratio

```python
# WRONG: Accept 30% hit ratio as "good enough"
# Problem: 70% of requests hit database

# CORRECT: Investigate and optimize for >85% hit ratio
```

### ❌ No Alerting for Cache Failures

```python
# WRONG: Cache failures silently fall back to database
# Problem: Database overload during cache outage

# CORRECT: Alert when cache hit ratio drops suddenly
```

## Quick Reference

**Critical Metrics**:
- Hit Ratio: 85-95% (target)
- Cache Latency: <5ms p99 (Redis)
- Memory Usage: <80% (healthy)
- Eviction Rate: <10% (well-sized)

**Monitoring Tools**:
- Redis: `INFO`, slowlog, redis-cli --stat
- HTTP: Response headers (Age, X-Cache, CF-Cache-Status)
- CDN: Cloudflare Analytics, Fastly Real-Time Stats
- APM: Prometheus, StatsD, Datadog, New Relic

**Alert Thresholds**:
```
Hit ratio < 80% → Investigate cache strategy
Memory usage > 90% → Increase cache size or tune eviction
Eviction rate > 10% → Cache undersized
Latency p99 > 10ms → Network or Redis issue
```

## Related Skills

- `redis-caching-patterns.md` - Redis metrics and instrumentation
- `cache-invalidation-strategies.md` - Monitor invalidation effectiveness
- `cdn-edge-caching.md` - CDN cache performance monitoring
- `observability/structured-logging.md` - Logging cache events
- `observability/metrics-instrumentation.md` - Application metrics

## Summary

Cache performance monitoring is essential for maintaining high-performance applications:

**Key Takeaways**:
1. **Measure hit ratio religiously** - Target 85-95% for production systems
2. **Monitor latency** - Cache should be 10-100x faster than origin
3. **Set up alerts** - Catch cache issues before they impact users
4. **Use multiple monitoring layers** - Application, Redis, HTTP, CDN
5. **Load test with caching** - Verify cache performance under load
6. **Track eviction rate** - High evictions indicate undersized cache
7. **Integrate with APM** - Cache metrics alongside application metrics

Without monitoring, you're flying blind. Cache performance monitoring provides the visibility needed to optimize caching strategies and maintain system health.
