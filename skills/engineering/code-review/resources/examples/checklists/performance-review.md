# Performance Review Checklist

Use this checklist when reviewing code for performance issues and optimization opportunities.

## Database & Data Access

### Query Optimization
- [ ] No N+1 query problems
- [ ] Appropriate use of eager loading (JOIN, prefetch)
- [ ] SELECT only needed columns (not SELECT *)
- [ ] Indexes exist for frequently queried fields
- [ ] Composite indexes for multi-column queries
- [ ] Index on foreign keys
- [ ] Appropriate index type (B-tree, hash, GiST, etc.)
- [ ] EXPLAIN/ANALYZE run on complex queries
- [ ] Query execution time acceptable (<100ms for simple queries)

### Data Fetching
- [ ] Pagination implemented for large result sets
- [ ] Cursor-based pagination for infinite scroll
- [ ] Batch fetching used instead of individual queries
- [ ] GraphQL dataloader or similar for batch loading
- [ ] Streaming used for large datasets
- [ ] Lazy loading appropriate (not loading unnecessary data)
- [ ] Connection pooling configured
- [ ] Database connection limits respected

### Caching
- [ ] Frequently accessed data is cached
- [ ] Cache invalidation strategy defined
- [ ] Cache TTL appropriate for data freshness requirements
- [ ] Cache keys are well-designed (no collisions)
- [ ] Cache miss handling is efficient
- [ ] Cache stampede prevention (lock, early refresh)
- [ ] Appropriate cache layer (in-memory, Redis, CDN)
- [ ] Cache hit rate monitored

### Transactions
- [ ] Transactions as short as possible
- [ ] No unnecessary locks held
- [ ] Appropriate isolation level
- [ ] Deadlock prevention considered
- [ ] Read-only queries not in transactions

## Algorithm & Data Structure Efficiency

### Algorithmic Complexity
- [ ] Time complexity is acceptable (avoid O(n²) where O(n log n) possible)
- [ ] Space complexity is reasonable
- [ ] No unnecessary nested loops
- [ ] Binary search instead of linear search where appropriate
- [ ] Hash maps used for O(1) lookups
- [ ] Appropriate sorting algorithm
- [ ] Early termination in loops where possible

### Data Structures
- [ ] Appropriate data structure for use case
- [ ] Set used instead of list for membership testing
- [ ] Deque used for queue operations
- [ ] OrderedDict/dict used appropriately
- [ ] Generators used for large sequences
- [ ] Arrays used for fixed-size numeric data
- [ ] Tree structures for hierarchical data

### String Operations
- [ ] String concatenation efficient (join vs +=)
- [ ] Regular expressions compiled and reused
- [ ] String formatting efficient (f-strings in Python)
- [ ] Unnecessary string copies avoided
- [ ] StringBuilder/StringBuffer used for repeated concatenation

## Memory Management

### Memory Usage
- [ ] Memory usage is bounded (no unbounded growth)
- [ ] Large objects released when no longer needed
- [ ] No memory leaks (objects properly cleaned up)
- [ ] Memory profiling done for critical paths
- [ ] Streaming used instead of loading entire file
- [ ] Object pooling considered for frequently created objects

### Data Structures Size
- [ ] No unnecessary data duplication
- [ ] Compact data representations used
- [ ] Lazy initialization for rarely used data
- [ ] Data structures sized appropriately (initial capacity)
- [ ] Old data evicted from caches
- [ ] Weak references used where appropriate

### Garbage Collection
- [ ] GC pressure minimized (fewer allocations)
- [ ] Object reuse where appropriate
- [ ] Short-lived vs long-lived objects separated
- [ ] Large objects kept in older generations

## Network & I/O

### Network Calls
- [ ] Network calls minimized (batching, caching)
- [ ] Async I/O used for concurrent operations
- [ ] Connection reuse (HTTP keep-alive, connection pooling)
- [ ] Appropriate timeout configured
- [ ] Retry logic with exponential backoff
- [ ] Circuit breaker for failing services
- [ ] Compression used for large payloads (gzip, brotli)
- [ ] HTTP/2 or HTTP/3 utilized where available

### API Design
- [ ] Pagination for large responses
- [ ] Field filtering (only return requested fields)
- [ ] ETags for conditional requests (304 Not Modified)
- [ ] GraphQL query depth limited
- [ ] REST endpoints coarse-grained (not chatty)
- [ ] Batch endpoints for multiple operations

### File I/O
- [ ] Files opened with appropriate buffer size
- [ ] Streaming for large files (not loading into memory)
- [ ] Async file I/O where beneficial
- [ ] File descriptors closed promptly
- [ ] Temporary files cleaned up

### Serialization
- [ ] Efficient serialization format (Protocol Buffers, MessagePack vs JSON)
- [ ] Serialization/deserialization profiled
- [ ] Schema evolution considered
- [ ] Binary formats for large data
- [ ] Streaming parsers for large documents

## Concurrency & Parallelism

### Thread Safety
- [ ] Thread-safe where multiple threads access
- [ ] Appropriate locking strategy (fine-grained vs coarse)
- [ ] Lock-free data structures considered
- [ ] No race conditions
- [ ] No deadlocks possible
- [ ] Lock contention minimized

### Async/Await
- [ ] Async functions actually async (not blocking)
- [ ] Await used correctly (not awaiting unnecessarily)
- [ ] Parallel execution for independent operations
- [ ] Event loop not blocked
- [ ] CPU-bound work offloaded to threads/processes

### Parallelization
- [ ] Parallel processing for CPU-bound tasks
- [ ] Thread pool sized appropriately
- [ ] Work distributed evenly across workers
- [ ] Overhead of parallelization justified
- [ ] Thread synchronization minimized

## Frontend Performance

### Rendering
- [ ] Virtual DOM/reconciliation efficient
- [ ] No unnecessary re-renders
- [ ] Memoization used appropriately (React.memo, useMemo)
- [ ] Virtualization for long lists (react-window, react-virtualized)
- [ ] Lazy loading for below-the-fold content
- [ ] Code splitting by route
- [ ] Tree shaking enabled

### Bundle Size
- [ ] Bundle size analyzed (webpack-bundle-analyzer)
- [ ] Dependencies minimized
- [ ] Moment.js replaced with date-fns or similar (smaller)
- [ ] Lodash imported selectively
- [ ] Images optimized (WebP, AVIF)
- [ ] SVG sprites for icons
- [ ] Fonts subset for used glyphs

### Asset Loading
- [ ] Critical CSS inlined
- [ ] Non-critical CSS deferred
- [ ] Scripts async or deferred
- [ ] Preload for critical resources
- [ ] Prefetch for next-page resources
- [ ] Images lazy loaded
- [ ] Responsive images (srcset)

### Caching (Frontend)
- [ ] Service worker for offline caching
- [ ] Cache-Control headers appropriate
- [ ] Versioned/hashed filenames for cache busting
- [ ] LocalStorage/SessionStorage used appropriately
- [ ] IndexedDB for large client-side data

## Monitoring & Measurement

### Profiling
- [ ] CPU profiling done for hot paths
- [ ] Memory profiling done
- [ ] Database query profiling done
- [ ] Network request profiling done
- [ ] Flame graphs analyzed

### Metrics
- [ ] Response time measured (p50, p95, p99)
- [ ] Throughput measured (requests/second)
- [ ] Error rate monitored
- [ ] Resource utilization monitored (CPU, memory, disk)
- [ ] Database connection pool utilization
- [ ] Cache hit rates
- [ ] Queue lengths (if using queues)

### Benchmarks
- [ ] Benchmarks written for critical paths
- [ ] Benchmarks run before and after changes
- [ ] Performance regression tests in CI
- [ ] Load testing performed
- [ ] Stress testing performed

## Common Performance Anti-Patterns

### Avoid These Patterns

**N+1 Queries**
```python
# ❌ Bad: N+1 queries
users = User.objects.all()
for user in users:
    print(user.profile.bio)  # Separate query for each user

# ✅ Good: Single query with JOIN
users = User.objects.select_related('profile').all()
for user in users:
    print(user.profile.bio)
```

**Loading Entire Dataset**
```python
# ❌ Bad: Load everything into memory
users = User.objects.all()  # Loads all users
for user in users:
    process(user)

# ✅ Good: Use iterator/batch
for user in User.objects.iterator(chunk_size=1000):
    process(user)
```

**Unnecessary Loops**
```python
# ❌ Bad: O(n²)
for item1 in items:
    for item2 in items:
        if item1.id == item2.related_id:
            process(item1, item2)

# ✅ Good: O(n) with hash map
related_map = {item.related_id: item for item in items}
for item in items:
    if item.id in related_map:
        process(item, related_map[item.id])
```

**String Concatenation in Loop**
```python
# ❌ Bad: O(n²) due to string immutability
result = ""
for item in items:
    result += str(item)  # Creates new string each time

# ✅ Good: O(n)
result = "".join(str(item) for item in items)
```

**Synchronous I/O in Loop**
```python
# ❌ Bad: Sequential network calls
results = []
for url in urls:
    response = requests.get(url)  # Blocks for each
    results.append(response.json())

# ✅ Good: Concurrent requests
import asyncio
import aiohttp

async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [session.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [await r.json() for r in responses]
```

**No Caching**
```python
# ❌ Bad: Expensive computation every time
def get_report(user_id):
    data = expensive_database_query(user_id)
    return process_data(data)

# ✅ Good: Cache the result
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_report(user_id):
    data = expensive_database_query(user_id)
    return process_data(data)
```

**Blocking Operations in Async**
```python
# ❌ Bad: Blocking in async function
async def handle_request():
    data = requests.get(url).json()  # Blocks event loop
    return process(data)

# ✅ Good: Use async client
async def handle_request():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return process(data)
```

## Performance Targets

### Response Time
- **API Endpoints:**
  - Simple queries: <100ms (p95)
  - Complex queries: <500ms (p95)
  - Batch operations: <2s (p95)

- **Web Pages:**
  - First Contentful Paint (FCP): <1.8s
  - Largest Contentful Paint (LCP): <2.5s
  - Time to Interactive (TTI): <3.8s
  - Cumulative Layout Shift (CLS): <0.1

### Throughput
- **API:** >100 requests/second (single instance)
- **Database:** >1000 queries/second (with proper indexing)
- **Cache:** >10,000 operations/second

### Resource Usage
- **Memory:** <512MB per instance (for typical web service)
- **CPU:** <70% average utilization
- **Database Connections:** <50% of pool size average
- **Cache Hit Rate:** >90% for hot data

### Scalability
- **Horizontal Scaling:** Linear up to 10 instances
- **Vertical Scaling:** 2x resources = 1.8x throughput minimum
- **Load Test:** Handle 2x peak traffic without degradation

---

## Performance Review Severity

**CRITICAL (Block Merge)**:
- N+1 query problem on high-traffic endpoint
- Memory leak in production code
- Infinite loop or exponential complexity
- Blocking I/O in async code (event loop blocking)
- Database table scan on large table

**HIGH (Fix Before Merge)**:
- Missing index on frequently queried field
- O(n²) algorithm where O(n log n) is easy
- Loading entire large dataset into memory
- No pagination on unbounded query
- Cache stampede vulnerability

**MEDIUM (Fix Soon)**:
- Suboptimal algorithm but acceptable performance
- Missing cache where it would help significantly
- Inefficient string operations in hot path
- Unnecessary object creation in loop
- Could use connection pooling but doesn't

**LOW (Optimization Opportunity)**:
- Minor inefficiency not in hot path
- Could be slightly more efficient
- Performance acceptable but could be better
- Nice-to-have optimization

---

## Performance Testing Checklist

Before approving performance-sensitive changes:

- [ ] Benchmarks run before and after change
- [ ] No performance regression (>5% slower)
- [ ] Load testing performed (simulate production load)
- [ ] Profiling shows no new bottlenecks
- [ ] Memory usage doesn't increase significantly
- [ ] Database query count doesn't increase
- [ ] Cache hit rate doesn't decrease
- [ ] P95/P99 latencies are acceptable

---

**Reviewer:** _____________
**Date:** _____________
**Performance Impact:** ⚪ None / 🟢 Improvement / 🟡 Neutral / 🔴 Regression
