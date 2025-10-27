---
name: distributed-systems-probabilistic-data-structures
description: Probabilistic data structures including Bloom filters, HyperLogLog, Count-Min Sketch for space-efficient approximations
---

# Probabilistic Data Structures

**Scope**: Bloom filters, HyperLogLog, Count-Min Sketch, space-efficient algorithms
**Lines**: ~240
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Space constraints critical
- Approximate answers acceptable
- Working with large-scale data
- Implementing caching layers
- Building distributed databases
- Deduplication at scale
- Cardinality estimation
- Frequency estimation

## Core Concepts

### Trade-off: Space vs Accuracy

```
Traditional data structures: Exact answers, more space
Probabilistic structures: Approximate answers, less space

Example: Set membership
- Hash set: O(n) space, exact
- Bloom filter: O(1) space per element, small false positive rate
```

---

## Bloom Filter

### Overview

**Purpose**: Test set membership with false positives (but no false negatives)

```
Bloom filter says:
- "Definitely not in set" → 100% accurate
- "Probably in set" → May have false positives
```

### Implementation

```python
import hashlib

class BloomFilter:
    """Space-efficient probabilistic set"""

    def __init__(self, size=1000, num_hashes=3):
        self.size = size
        self.num_hashes = num_hashes
        self.bits = [False] * size

    def _hashes(self, item):
        """Generate k hash values"""
        hashes = []
        for i in range(self.num_hashes):
            # Use different seeds for each hash
            hash_input = f"{item}:{i}".encode()
            hash_val = int(hashlib.md5(hash_input).hexdigest(), 16)
            hashes.append(hash_val % self.size)
        return hashes

    def add(self, item):
        """Add item to set"""
        for hash_val in self._hashes(item):
            self.bits[hash_val] = True

    def contains(self, item):
        """Check if item might be in set"""
        return all(self.bits[h] for h in self._hashes(item))

# Usage
bf = BloomFilter(size=1000, num_hashes=3)

bf.add('apple')
bf.add('banana')

print(bf.contains('apple'))   # True (definitely added)
print(bf.contains('cherry'))  # False (definitely not added)
print(bf.contains('xyz'))     # Maybe False (could be false positive)

# False positive rate depends on size, num_hashes, num_items
```

### Applications

```
✅ Cache filtering (check before expensive lookup)
✅ Deduplication (seen this data before?)
✅ Spell checking (is this a valid word?)
✅ Network routers (packet filtering)
```

**Example: Cache Filter**
```python
class CachedStore:
    def __init__(self):
        self.cache = {}
        self.bloom = BloomFilter(size=10000)

    def get(self, key):
        # Quick check with Bloom filter
        if not self.bloom.contains(key):
            # Definitely not in cache
            return self.fetch_from_db(key)

        # Maybe in cache - check actual cache
        if key in self.cache:
            return self.cache[key]
        else:
            # False positive
            return self.fetch_from_db(key)

    def put(self, key, value):
        self.cache[key] = value
        self.bloom.add(key)
```

---

## HyperLogLog

### Overview

**Purpose**: Estimate cardinality (count distinct elements) with small memory

```
Traditional: Store all elements → O(n) space
HyperLogLog: Fixed memory (few KB) → estimates count within 2% error
```

### Implementation (Simplified)

```python
import hashlib
import math

class HyperLogLog:
    """Cardinality estimation"""

    def __init__(self, precision=14):
        self.precision = precision
        self.m = 1 << precision  # 2^precision buckets
        self.registers = [0] * self.m

    def _hash(self, item):
        """Hash item to 64-bit value"""
        return int(hashlib.md5(str(item).encode()).hexdigest(), 16) & ((1 << 64) - 1)

    def add(self, item):
        """Add item"""
        h = self._hash(item)

        # Use first p bits for bucket index
        bucket = h & (self.m - 1)

        # Count leading zeros in remaining bits
        remaining = h >> self.precision
        leading_zeros = self._count_leading_zeros(remaining, 64 - self.precision)

        # Update register with maximum
        self.registers[bucket] = max(self.registers[bucket], leading_zeros + 1)

    def cardinality(self):
        """Estimate cardinality"""
        # Harmonic mean of 2^register values
        raw_estimate = self._alpha() * (self.m ** 2) / sum(2 ** (-reg) for reg in self.registers)

        # Bias correction for small/large cardinalities
        if raw_estimate <= 2.5 * self.m:
            # Small range correction
            zeros = self.registers.count(0)
            if zeros != 0:
                return self.m * math.log(self.m / zeros)

        return int(raw_estimate)

    def _alpha(self):
        """Bias correction constant"""
        if self.m >= 128:
            return 0.7213 / (1 + 1.079 / self.m)
        elif self.m >= 64:
            return 0.709
        elif self.m >= 32:
            return 0.697
        else:
            return 0.673

    def _count_leading_zeros(self, value, max_width):
        """Count leading zeros"""
        if value == 0:
            return max_width
        return max_width - value.bit_length()

    def merge(self, other):
        """Merge with another HyperLogLog"""
        for i in range(self.m):
            self.registers[i] = max(self.registers[i], other.registers[i])

# Usage
hll = HyperLogLog()

# Add millions of items
for i in range(1000000):
    hll.add(f"user_{i}")

print(f"Estimated unique users: {hll.cardinality()}")  # ~1,000,000
# Uses only ~16KB memory!
```

### Applications

```
✅ Unique visitors counting (web analytics)
✅ Distinct IP addresses
✅ Database query optimization (cardinality estimates)
✅ Stream processing (count unique events)
```

---

## Count-Min Sketch

### Overview

**Purpose**: Estimate frequency of elements with bounded error

```
Traditional: Hash map → O(n) space, exact counts
Count-Min Sketch: Fixed memory → approximate counts with error bound
```

### Implementation

```python
import hashlib

class CountMinSketch:
    """Frequency estimation"""

    def __init__(self, width=1000, depth=7):
        self.width = width
        self.depth = depth
        self.table = [[0] * width for _ in range(depth)]

    def _hashes(self, item):
        """Generate d hash values"""
        hashes = []
        for i in range(self.depth):
            hash_input = f"{item}:{i}".encode()
            hash_val = int(hashlib.md5(hash_input).hexdigest(), 16)
            hashes.append(hash_val % self.width)
        return hashes

    def add(self, item, count=1):
        """Increment count for item"""
        for i, h in enumerate(self._hashes(item)):
            self.table[i][h] += count

    def estimate(self, item):
        """Estimate count (returns minimum across rows)"""
        return min(self.table[i][h] for i, h in enumerate(self._hashes(item)))

# Usage
cms = CountMinSketch(width=1000, depth=7)

# Count events
for event in event_stream:
    cms.add(event)

# Estimate frequency
print(f"Event X count: {cms.estimate('event_x')}")  # Approximate count
# Never underestimates, may overestimate due to collisions
```

### Applications

```
✅ Heavy hitters detection (top-k frequent items)
✅ Network traffic analysis
✅ Query frequency estimation
✅ Rate limiting (count requests per user)
```

---

## Comparison

| Structure | Purpose | Space | Accuracy | False Positives |
|-----------|---------|-------|----------|-----------------|
| **Bloom Filter** | Membership | O(1) per item | High | Yes (tunable) |
| **HyperLogLog** | Cardinality | Fixed (~KB) | ~2% error | N/A |
| **Count-Min Sketch** | Frequency | Fixed | Bounded error | Overestimates |
| **Hash Set** | Membership | O(n) | 100% | No |
| **Hash Map** | Frequency | O(n) | 100% | No |

---

## Choosing the Right Structure

### Use Bloom Filter When:
```python
# Large set, only need membership test
user_blacklist = BloomFilter(size=1000000)

if user_blacklist.contains(user_id):
    # Might be blacklisted - check database
    if database.is_blacklisted(user_id):
        reject()
```

### Use HyperLogLog When:
```python
# Count unique items in stream
unique_visitors = HyperLogLog()

for request in request_stream:
    unique_visitors.add(request.user_id)

print(f"DAU: {unique_visitors.cardinality()}")
```

### Use Count-Min Sketch When:
```python
# Track frequency, find heavy hitters
request_counts = CountMinSketch()

for request in request_stream:
    request_counts.add(request.endpoint)

# Find most frequent endpoints
top_endpoints = [(e, request_counts.estimate(e)) for e in endpoints]
top_endpoints.sort(key=lambda x: x[1], reverse=True)
```

---

## Real-World Examples

### Redis

```bash
# HyperLogLog for unique counting
PFADD unique_visitors user:123
PFCOUNT unique_visitors  # Approximate count

# Bloom filter (via RedisBloom module)
BF.ADD bloom_filter "item"
BF.EXISTS bloom_filter "item"
```

### Cassandra

```
Uses Bloom filters for:
- SSTable filtering (avoid disk reads)
- Reduce false positive rate with multiple hash functions
```

---

## Related Skills

- `distributed-systems-eventual-consistency` - Consistency trade-offs
- `distributed-systems-partitioning-sharding` - Data distribution
- `distributed-systems-gossip-protocols` - Epidemic algorithms

---

**Last Updated**: 2025-10-27
