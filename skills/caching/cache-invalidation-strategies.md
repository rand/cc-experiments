---
name: caching-cache-invalidation-strategies
description: Cache invalidation patterns and techniques - time-based, event-based, key-based, and version-based invalidation for maintaining cache consistency.
---
# Cache Invalidation Strategies

**Last Updated**: 2025-10-25

## When to Use This Skill

Use this skill when:
- Ensuring cached data stays synchronized with source of truth
- Designing invalidation strategies for distributed caches
- Dealing with stale cache issues in production
- Implementing event-driven cache updates
- Migrating from simple TTL to sophisticated invalidation
- Optimizing cache hit rates while maintaining data freshness

**Famous quote**: "There are only two hard things in Computer Science: cache invalidation and naming things." - Phil Karlton

**Prerequisites**: Understanding of `caching-fundamentals.md` and `redis-caching-patterns.md`

## Core Concepts

Cache invalidation is the process of removing or updating stale data from a cache. The challenge is balancing **freshness** (data accuracy) with **performance** (cache hit rate).

### Invalidation Strategy Decision Matrix

| Strategy | Freshness | Complexity | Use Case |
|----------|-----------|------------|----------|
| **Time-Based** | Low-Medium | Low | Content that changes predictably |
| **Event-Based** | High | Medium-High | Real-time updates required |
| **Key-Based** | High | Medium | Related data needs coordinated invalidation |
| **Version-Based** | Very High | Low-Medium | Immutable data with versions |

## Time-Based Invalidation

### Fixed TTL (Time-To-Live)

**Simplest approach** - cache entries expire after a fixed duration.

```python
import redis
import json
from datetime import datetime, timedelta

class FixedTTLCache:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    def set_with_ttl(self, key: str, value: dict, ttl_seconds: int) -> None:
        """Set cache entry with fixed TTL"""
        self.cache.setex(key, ttl_seconds, json.dumps(value))
        print(f"Cached {key} with TTL={ttl_seconds}s")

    def get(self, key: str) -> dict:
        """Get cached value (auto-expires after TTL)"""
        cached = self.cache.get(key)
        if cached:
            ttl_remaining = self.cache.ttl(key)
            print(f"Cache hit: {key} (expires in {ttl_remaining}s)")
            return json.loads(cached)
        print(f"Cache miss: {key}")
        return None

# Usage: Different TTLs for different data types
cache = FixedTTLCache(redis_client)
cache.set_with_ttl("user:123", user_data, 3600)      # 1 hour (semi-static)
cache.set_with_ttl("product:456", product_data, 300)  # 5 minutes (dynamic)
cache.set_with_ttl("homepage", html, 60)              # 1 minute (very dynamic)
```

### Absolute Expiration

**Expire at specific time** - useful for time-sensitive data.

```python
from datetime import datetime, timezone

class AbsoluteExpirationCache:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    def set_expire_at(self, key: str, value: dict, expire_at: datetime) -> None:
        """Set cache to expire at specific timestamp"""
        self.cache.set(key, json.dumps(value))
        self.cache.expireat(key, int(expire_at.timestamp()))
        print(f"Cached {key}, expires at {expire_at.isoformat()}")

# Usage: Flash sale ending at specific time
sale_end = datetime(2025, 10, 25, 23, 59, 59, tzinfo=timezone.utc)
cache.set_expire_at("flash_sale:electronics", sale_data, sale_end)
```

### Sliding Expiration

**Reset TTL on access** - keeps frequently accessed data cached.

```python
class SlidingExpirationCache:
    def __init__(self, redis_client: redis.Redis, ttl: int = 1800):
        self.cache = redis_client
        self.ttl = ttl  # 30 minutes default

    def get_with_sliding(self, key: str) -> dict:
        """Get value and reset TTL (sliding window)"""
        cached = self.cache.get(key)
        if cached:
            # Reset expiration on access
            self.cache.expire(key, self.ttl)
            print(f"Cache hit: {key}, TTL reset to {self.ttl}s")
            return json.loads(cached)
        return None

    def set_sliding(self, key: str, value: dict) -> None:
        self.cache.setex(key, self.ttl, json.dumps(value))

# User session storage: extends session on activity
session_cache = SlidingExpirationCache(redis_client, ttl=1800)
```

## Event-Based Invalidation

### Pub/Sub Invalidation

**Invalidate on data change events** - use Redis Pub/Sub to propagate invalidation.

```python
import threading

class PubSubInvalidation:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client
        self.pubsub = redis_client.pubsub()

    def start_listener(self):
        """Listen for invalidation events"""
        self.pubsub.subscribe('cache:invalidate')
        thread = threading.Thread(target=self._listen)
        thread.daemon = True
        thread.start()

    def _listen(self):
        """Background thread processing invalidation events"""
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                key_pattern = message['data'].decode('utf-8')
                self._invalidate_pattern(key_pattern)

    def _invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        keys = self.cache.keys(pattern)
        if keys:
            self.cache.delete(*keys)
            print(f"Invalidated {len(keys)} keys matching {pattern}")

    def publish_invalidation(self, key_pattern: str):
        """Publish invalidation event"""
        self.cache.publish('cache:invalidate', key_pattern)
        print(f"Published invalidation: {key_pattern}")

# Usage
invalidator = PubSubInvalidation(redis_client)
invalidator.start_listener()

# When user updates profile
def update_user_profile(user_id: int, new_data: dict):
    save_to_database(user_id, new_data)
    # Invalidate all user-related caches
    invalidator.publish_invalidation(f"user:{user_id}:*")
```

### Change Data Capture (CDC)

**Invalidate based on database changes** - monitor database transaction log.

```python
# Pseudo-code for CDC-based invalidation (using Debezium/Kafka pattern)
class CDCInvalidation:
    def __init__(self, kafka_consumer, redis_client):
        self.consumer = kafka_consumer
        self.cache = redis_client

    def process_cdc_events(self):
        """Process CDC events from Kafka"""
        for message in self.consumer:
            event = json.loads(message.value)

            if event['operation'] in ['UPDATE', 'DELETE']:
                # Extract entity ID from CDC event
                entity_type = event['table']
                entity_id = event['after']['id'] if event['operation'] == 'UPDATE' else event['before']['id']

                # Invalidate related cache entries
                self._invalidate_entity(entity_type, entity_id)

    def _invalidate_entity(self, entity_type: str, entity_id: int):
        """Invalidate cache for specific entity"""
        pattern = f"{entity_type}:{entity_id}:*"
        keys = self.cache.keys(pattern)
        if keys:
            self.cache.delete(*keys)
            print(f"CDC invalidation: {entity_type}:{entity_id}")

# Real-world example: PostgreSQL logical replication + Kafka
# 1. Enable logical replication in PostgreSQL
# 2. Debezium connector streams changes to Kafka
# 3. Consumer invalidates cache based on database changes
```

## Key-Based Invalidation (Cache Tags)

### Surrogate Keys / Cache Tags

**Tag cache entries for bulk invalidation** - Netflix uses this pattern.

```python
class CacheTagInvalidation:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    def set_with_tags(self, key: str, value: dict, tags: list[str], ttl: int = 3600):
        """Store cache entry with associated tags"""
        # Store the value
        self.cache.setex(key, ttl, json.dumps(value))

        # Associate key with each tag
        for tag in tags:
            tag_set = f"tag:{tag}"
            self.cache.sadd(tag_set, key)
            self.cache.expire(tag_set, ttl + 300)  # Tag outlives cache entry

        print(f"Cached {key} with tags: {tags}")

    def invalidate_by_tag(self, tag: str):
        """Invalidate all cache entries with specific tag"""
        tag_set = f"tag:{tag}"
        keys = self.cache.smembers(tag_set)

        if keys:
            # Delete all tagged entries
            self.cache.delete(*keys)
            # Delete tag set
            self.cache.delete(tag_set)
            print(f"Invalidated {len(keys)} entries with tag '{tag}'")

# Usage: E-commerce product cache
tagger = CacheTagInvalidation(redis_client)

product_data = {"id": 123, "name": "Laptop", "category_id": 5, "brand_id": 10}
tagger.set_with_tags(
    key="product:123",
    value=product_data,
    tags=["product", "category:5", "brand:10"],
    ttl=3600
)

# When category 5 updates, invalidate all products in that category
tagger.invalidate_by_tag("category:5")
```

### Dependency Graph Invalidation

**Invalidate related data hierarchically** - complex but precise.

```python
class DependencyGraphInvalidation:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    def set_with_dependencies(self, key: str, value: dict, dependencies: list[str], ttl: int = 3600):
        """Store cache with dependency tracking"""
        self.cache.setex(key, ttl, json.dumps(value))

        # Store dependency graph
        dep_key = f"deps:{key}"
        self.cache.sadd(dep_key, *dependencies)
        self.cache.expire(dep_key, ttl)

    def invalidate_cascade(self, key: str):
        """Recursively invalidate key and all dependents"""
        # Find all keys that depend on this key
        dependents = self._find_dependents(key)

        # Invalidate in topological order
        for dependent in dependents:
            self.cache.delete(dependent)
            self.cache.delete(f"deps:{dependent}")

        # Invalidate the key itself
        self.cache.delete(key)
        self.cache.delete(f"deps:{key}")

        print(f"Cascade invalidation: {key} + {len(dependents)} dependents")

    def _find_dependents(self, key: str) -> list[str]:
        """Find all keys that depend on given key"""
        dependents = []
        # Scan all dependency sets (simplified - use index in production)
        for dep_key in self.cache.scan_iter("deps:*"):
            deps = self.cache.smembers(dep_key)
            if key.encode() in deps:
                dependent_key = dep_key.decode().replace("deps:", "")
                dependents.append(dependent_key)
        return dependents

# Usage: User profile affects multiple derived caches
graph = DependencyGraphInvalidation(redis_client)

graph.set_with_dependencies("user:123", user_data, dependencies=[], ttl=3600)
graph.set_with_dependencies("user:123:posts", posts, dependencies=["user:123"], ttl=1800)
graph.set_with_dependencies("user:123:feed", feed, dependencies=["user:123", "user:123:posts"], ttl=600)

# When user updates, cascade invalidation
graph.invalidate_cascade("user:123")  # Invalidates user, posts, feed
```

## Version-Based Invalidation

### Immutable Data with Versioning

**Never invalidate, just create new versions** - GitHub uses this pattern.

```python
import hashlib

class VersionBasedCache:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    def set_versioned(self, base_key: str, value: dict, ttl: int = 86400):
        """Store data with content-based version key"""
        # Generate version hash from content
        content_hash = self._hash_content(value)
        versioned_key = f"{base_key}:v:{content_hash}"

        # Store with long TTL (immutable data)
        self.cache.setex(versioned_key, ttl, json.dumps(value))

        # Update pointer to latest version
        self.cache.setex(f"{base_key}:latest", ttl, content_hash)

        print(f"Stored {versioned_key} (immutable)")
        return content_hash

    def get_versioned(self, base_key: str, version: str = None) -> dict:
        """Get specific version or latest"""
        if not version:
            # Get latest version
            version = self.cache.get(f"{base_key}:latest")
            if not version:
                return None
            version = version.decode()

        versioned_key = f"{base_key}:v:{version}"
        cached = self.cache.get(versioned_key)
        return json.loads(cached) if cached else None

    def _hash_content(self, value: dict) -> str:
        """Generate content hash for versioning"""
        content = json.dumps(value, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:12]

# Usage: API responses with versioning
vcache = VersionBasedCache(redis_client)

# Store new version
version = vcache.set_versioned("api:users:list", users_data)

# Get latest
latest = vcache.get_versioned("api:users:list")

# Get specific version (for rollback or A/B testing)
specific = vcache.get_versioned("api:users:list", version="a1b2c3d4e5f6")
```

### Cache Busting with Fingerprints

**Frontend asset invalidation** - append hash to filenames.

```typescript
// TypeScript: Frontend asset fingerprinting
class AssetFingerprinting {
  private manifest: Map<string, string> = new Map();

  // Build time: Generate manifest
  generateManifest(files: string[]): void {
    files.forEach(file => {
      const hash = this.hashFile(file);
      const fingerprinted = this.addFingerprint(file, hash);
      this.manifest.set(file, fingerprinted);
    });
  }

  // Runtime: Get fingerprinted URL
  getAssetUrl(file: string): string {
    return this.manifest.get(file) || file;
  }

  private addFingerprint(file: string, hash: string): string {
    const ext = file.split('.').pop();
    const base = file.replace(`.${ext}`, '');
    return `${base}.${hash}.${ext}`;
  }

  private hashFile(file: string): string {
    // Simplified: Use file content hash in production
    return Math.random().toString(36).substring(2, 10);
  }
}

// HTML generation with fingerprinted assets
const assets = new AssetFingerprinting();
// app.js -> app.a1b2c3d4.js (immutable, cache forever)
const scriptUrl = assets.getAssetUrl('app.js');
// <script src="/static/app.a1b2c3d4.js"></script>
// Cache-Control: public, max-age=31536000, immutable
```

## Netflix Case Study: Mixed Invalidation

**Real-world example**: Netflix hybrid approach (2024 data).

```python
class NetflixStyleInvalidation:
    """
    Netflix invalidation strategy (simplified):
    - Time-based for most content (TTL)
    - Event-based for critical updates (user actions)
    - Key-based for related content (recommendations)
    Result: 30% CPU reduction, faster cache refresh
    """
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    def cache_movie_metadata(self, movie_id: int, metadata: dict):
        """Time-based: Movie metadata changes rarely"""
        ttl = 86400  # 24 hours
        self.cache.setex(f"movie:{movie_id}", ttl, json.dumps(metadata))

        # Tag for bulk invalidation
        self.cache.sadd("tag:movie_metadata", f"movie:{movie_id}")

    def cache_user_recommendations(self, user_id: int, recommendations: list):
        """Event-based: Invalidate on user actions"""
        ttl = 3600  # 1 hour
        key = f"recs:{user_id}"
        self.cache.setex(key, ttl, json.dumps(recommendations))

        # Watch for user events to invalidate
        self.cache.setex(f"recs_invalidate:{user_id}", ttl, "pending")

    def on_user_watch_event(self, user_id: int, movie_id: int):
        """Event: User watched movie -> invalidate recommendations"""
        self.cache.delete(f"recs:{user_id}")
        print(f"Event invalidation: User {user_id} recs after watching {movie_id}")

    def invalidate_movie_category(self, category: str):
        """Key-based: Invalidate all movies in category"""
        keys = self.cache.smembers(f"tag:category:{category}")
        if keys:
            self.cache.delete(*keys)
            print(f"Bulk invalidation: {len(keys)} movies in {category}")
```

## Cache Warming After Invalidation

**Prevent thundering herd** - proactively populate cache after invalidation.

```python
import asyncio
import aiohttp

class CacheWarming:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    async def warm_cache(self, keys_to_warm: list[str], fetch_fn):
        """Asynchronously warm cache after invalidation"""
        tasks = [self._warm_single(key, fetch_fn) for key in keys_to_warm]
        await asyncio.gather(*tasks)
        print(f"Warmed {len(keys_to_warm)} cache entries")

    async def _warm_single(self, key: str, fetch_fn):
        """Warm single cache entry"""
        data = await fetch_fn(key)
        if data:
            self.cache.setex(key, 3600, json.dumps(data))

# Usage: Warm popular items after deployment
async def fetch_product(product_id: str):
    # Fetch from database
    return {"id": product_id, "name": f"Product {product_id}"}

warmer = CacheWarming(redis_client)
popular_products = ["product:1", "product:2", "product:3"]
await warmer.warm_cache(popular_products, fetch_product)
```

## Graceful Degradation

**Handle invalidation failures** - serve stale data if necessary.

```python
class GracefulCacheInvalidation:
    def __init__(self, redis_client: redis.Redis):
        self.cache = redis_client

    def get_with_stale_fallback(self, key: str, fetch_fn, ttl: int = 300):
        """Serve stale data if refresh fails"""
        cached = self.cache.get(key)
        ttl_remaining = self.cache.ttl(key)

        # Fresh cache hit
        if cached and ttl_remaining > 0:
            return json.loads(cached)

        # Try refresh
        try:
            fresh_data = fetch_fn()
            self.cache.setex(key, ttl, json.dumps(fresh_data))
            return fresh_data
        except Exception as e:
            print(f"Fetch failed: {e}")

            # Serve stale data if available
            if cached:
                print(f"Serving stale data for {key}")
                # Extend TTL briefly while fixing issue
                self.cache.expire(key, 60)
                return json.loads(cached)

            raise  # No stale data available, propagate error
```

## Anti-Patterns

### ❌ Invalidating Too Aggressively

```python
# WRONG: Invalidate on every write
def update_user(user_id: int, data: dict):
    save_to_db(user_id, data)
    cache.delete(f"user:{user_id}")
    cache.delete(f"user:{user_id}:*")  # Overly aggressive
    # Next read causes cache miss

# CORRECT: Update cache instead of deleting
def update_user(user_id: int, data: dict):
    save_to_db(user_id, data)
    cache.setex(f"user:{user_id}", 3600, json.dumps(data))
```

### ❌ No Invalidation Strategy

```python
# WRONG: Set cache, never invalidate
cache.set("config", config_data)  # Stale data forever

# CORRECT: Use appropriate TTL or event-based invalidation
cache.setex("config", 300, json.dumps(config_data))  # 5 min TTL
```

### ❌ Invalidating Without Warming

```python
# WRONG: Invalidate during traffic spike
cache.delete("popular_product:*")  # Thundering herd to database

# CORRECT: Warm cache before invalidating
warm_cache(popular_products)
cache.delete("popular_product:*")
```

## Quick Reference

**Invalidation Strategy Selection**:
```
Static content → Time-based (long TTL)
User-specific → Sliding expiration
Real-time updates → Event-based (pub/sub)
Related data → Key-based (tags)
Immutable data → Version-based (no invalidation)
```

**Best Practices**:
- Use TTL as a safety net (always set expiration)
- Combine strategies (Netflix: time + event + key-based)
- Warm cache after invalidation
- Monitor cache hit rate to tune invalidation
- Plan for graceful degradation

**Common TTL Values**:
```
Static assets: 1 year (31536000s) + fingerprinting
API responses: 5-30 minutes (300-1800s)
User sessions: 30 minutes sliding
Database queries: 1-10 minutes (60-600s)
Real-time data: 10-60 seconds
```

## Related Skills

- `caching-fundamentals.md` - Core caching patterns
- `redis-caching-patterns.md` - Redis-specific implementations
- `http-caching.md` - Browser cache invalidation (ETag, Last-Modified)
- `cdn-edge-caching.md` - CDN cache purging strategies
- `cache-performance-monitoring.md` - Measuring invalidation effectiveness

## Summary

Cache invalidation is one of the hardest problems in computer science, but following proven strategies makes it manageable:

**Key Takeaways**:
1. **There's no one-size-fits-all** - Combine multiple strategies (Netflix approach)
2. **Time-based is simplest** - Use TTL as default, add sophistication as needed
3. **Event-based is most accurate** - But requires infrastructure (pub/sub, CDC)
4. **Version-based is most elegant** - Treat data as immutable when possible
5. **Always warm after invalidation** - Prevent thundering herd
6. **Monitor invalidation effectiveness** - Track cache hit rate, stale data incidents

The goal is balancing freshness with performance. Start simple (TTL), add event-based invalidation for critical paths, and use versioning for static assets.
