#!/usr/bin/env python3
"""
Cache Manager for DSPy Predictions

Multi-level cache management (memory + Redis) with monitoring and debugging
capabilities. Supports cache warming, invalidation strategies, and statistics
tracking for production DSPy deployments.

Usage:
    python cache_manager.py set --key "question:test" --value prediction.json
    python cache_manager.py get --key "question:test"
    python cache_manager.py warm --predictions predictions.jsonl
    python cache_manager.py invalidate --pattern "question:*"
    python cache_manager.py stats
    python cache_manager.py inspect --top 10
"""

import os
import sys
import json
import time
import hashlib
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict
from collections import OrderedDict
from enum import Enum


class CacheLevel(str, Enum):
    """Cache level identifiers."""
    MEMORY = "memory"
    REDIS = "redis"


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Dict[str, Any]
    timestamp: float
    access_count: int = 0
    last_accessed: Optional[float] = None
    cache_level: str = CacheLevel.MEMORY.value
    ttl: Optional[int] = None  # TTL in seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create from dictionary."""
        return cls(**data)

    def is_expired(self) -> bool:
        """Check if entry has exceeded TTL."""
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl


class LRUCache:
    """In-memory LRU cache implementation."""

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from cache, updating access time."""
        if key not in self.cache:
            return None

        entry = self.cache[key]

        # Check expiration
        if entry.is_expired():
            del self.cache[key]
            return None

        # Update access metadata
        entry.access_count += 1
        entry.last_accessed = time.time()

        # Move to end (most recently used)
        self.cache.move_to_end(key)

        return entry

    def put(self, key: str, entry: CacheEntry) -> None:
        """Put value in cache, evicting LRU if at capacity."""
        if key in self.cache:
            self.cache.move_to_end(key)

        self.cache[key] = entry

        # Evict LRU if over capacity
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all entries."""
        self.cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)

    def keys(self) -> List[str]:
        """Get all cache keys."""
        return list(self.cache.keys())

    def items(self) -> List[Tuple[str, CacheEntry]]:
        """Get all cache items."""
        return list(self.cache.items())


class RedisCache:
    """Redis cache wrapper with connection pooling."""

    def __init__(self, url: str = "redis://localhost:6379", ttl: int = 3600):
        self.url = url
        self.ttl = ttl
        self._client = None

    @property
    def client(self):
        """Lazy-load Redis client."""
        if self._client is None:
            try:
                import redis
                self._client = redis.from_url(self.url, decode_responses=True)
            except ImportError:
                raise RuntimeError("redis-py not installed. Install with: pip install redis")
            except Exception as e:
                raise RuntimeError(f"Failed to connect to Redis: {e}")
        return self._client

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from Redis."""
        try:
            value = self.client.get(key)
            if value is None:
                return None

            data = json.loads(value)
            return CacheEntry.from_dict(data)
        except Exception as e:
            print(f"Redis get error: {e}", file=sys.stderr)
            return None

    def put(self, key: str, entry: CacheEntry, ttl: Optional[int] = None) -> bool:
        """Put value in Redis with TTL."""
        try:
            value = json.dumps(entry.to_dict())
            ttl_seconds = ttl or self.ttl
            self.client.setex(key, ttl_seconds, value)
            return True
        except Exception as e:
            print(f"Redis put error: {e}", file=sys.stderr)
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        try:
            return self.client.delete(key) > 0
        except Exception as e:
            print(f"Redis delete error: {e}", file=sys.stderr)
            return False

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        try:
            return self.client.keys(pattern)
        except Exception as e:
            print(f"Redis keys error: {e}", file=sys.stderr)
            return []

    def clear(self, pattern: str = "dspy:*") -> int:
        """Clear keys matching pattern."""
        try:
            keys = self.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Redis clear error: {e}", file=sys.stderr)
            return 0

    def ping(self) -> bool:
        """Check Redis connection."""
        try:
            return self.client.ping()
        except Exception:
            return False


class MultiLevelCache:
    """Multi-level cache manager (L1: Memory, L2: Redis)."""

    def __init__(
        self,
        memory_capacity: int = 1000,
        redis_url: str = "redis://localhost:6379",
        redis_ttl: int = 3600,
        key_prefix: str = "dspy:v1:prediction:",
    ):
        self.memory = LRUCache(capacity=memory_capacity)
        self.redis = RedisCache(url=redis_url, ttl=redis_ttl)
        self.key_prefix = key_prefix

        # Statistics
        self.stats = {
            "hits_memory": 0,
            "hits_redis": 0,
            "misses": 0,
            "writes": 0,
            "evictions": 0,
            "errors": 0,
        }

    def _normalize_key(self, key: str) -> str:
        """Normalize cache key with prefix."""
        if not key.startswith(self.key_prefix):
            return f"{self.key_prefix}{key}"
        return key

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get from cache (L1 then L2)."""
        key = self._normalize_key(key)

        # Check L1 (memory)
        entry = self.memory.get(key)
        if entry:
            self.stats["hits_memory"] += 1
            entry.cache_level = CacheLevel.MEMORY.value
            return entry.value

        # Check L2 (Redis)
        entry = self.redis.get(key)
        if entry:
            self.stats["hits_redis"] += 1
            entry.cache_level = CacheLevel.REDIS.value

            # Promote to L1
            self.memory.put(key, entry)

            return entry.value

        # Miss
        self.stats["misses"] += 1
        return None

    def put(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Put in both caches."""
        key = self._normalize_key(key)

        entry = CacheEntry(
            value=value,
            timestamp=time.time(),
            ttl=ttl,
        )

        # Store in L1
        self.memory.put(key, entry)

        # Store in L2
        success = self.redis.put(key, entry, ttl)

        if success:
            self.stats["writes"] += 1
        else:
            self.stats["errors"] += 1

        return success

    def delete(self, key: str) -> bool:
        """Delete from both caches."""
        key = self._normalize_key(key)

        mem_deleted = self.memory.delete(key)
        redis_deleted = self.redis.delete(key)

        return mem_deleted or redis_deleted

    def clear(self) -> Tuple[int, int]:
        """Clear both caches."""
        self.memory.clear()
        redis_cleared = self.redis.clear(self.key_prefix + "*")
        return (0, redis_cleared)

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate keys matching pattern."""
        full_pattern = self._normalize_key(pattern)
        keys = self.redis.keys(full_pattern)

        count = 0
        for key in keys:
            if self.delete(key):
                count += 1

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = (
            self.stats["hits_memory"] + self.stats["hits_redis"] + self.stats["misses"]
        )

        hit_rate = 0.0
        if total_requests > 0:
            hits = self.stats["hits_memory"] + self.stats["hits_redis"]
            hit_rate = hits / total_requests

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "memory_size": self.memory.size(),
            "memory_capacity": self.memory.capacity,
            "redis_connected": self.redis.ping(),
        }

    def inspect_top(self, n: int = 10) -> List[Dict[str, Any]]:
        """Inspect top N most accessed cache entries."""
        items = self.memory.items()

        # Sort by access count (descending)
        sorted_items = sorted(
            items, key=lambda x: x[1].access_count, reverse=True
        )[:n]

        results = []
        for key, entry in sorted_items:
            results.append({
                "key": key,
                "access_count": entry.access_count,
                "age_seconds": time.time() - entry.timestamp,
                "last_accessed": entry.last_accessed,
                "cache_level": entry.cache_level,
                "expired": entry.is_expired(),
            })

        return results


def generate_cache_key(inputs: Dict[str, Any], model: str = "default") -> str:
    """Generate deterministic cache key from inputs."""
    # Sort keys for consistency
    sorted_input = json.dumps(inputs, sort_keys=True)
    combined = f"{model}:{sorted_input}"

    # Use fast hash
    hash_obj = hashlib.blake2b(combined.encode(), digest_size=16)
    return hash_obj.hexdigest()


def cmd_get(args):
    """Get value from cache."""
    cache = MultiLevelCache(
        redis_url=args.redis_url,
        memory_capacity=args.memory_capacity,
    )

    value = cache.get(args.key)

    if value is None:
        print(f"Key not found: {args.key}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(value, indent=2))


def cmd_set(args):
    """Set value in cache."""
    cache = MultiLevelCache(
        redis_url=args.redis_url,
        memory_capacity=args.memory_capacity,
    )

    # Load value from file or string
    if args.value.endswith('.json'):
        with open(args.value) as f:
            value = json.load(f)
    else:
        value = json.loads(args.value)

    success = cache.put(args.key, value, ttl=args.ttl)

    if success:
        print(f"Successfully cached: {args.key}")
    else:
        print(f"Failed to cache: {args.key}", file=sys.stderr)
        sys.exit(1)


def cmd_warm(args):
    """Warm cache with predictions from JSONL file."""
    cache = MultiLevelCache(
        redis_url=args.redis_url,
        memory_capacity=args.memory_capacity,
    )

    count = 0
    errors = 0

    with open(args.predictions) as f:
        for line in f:
            try:
                prediction = json.loads(line)

                # Generate key from input
                if 'input' in prediction and 'output' in prediction:
                    key = generate_cache_key(prediction['input'], args.model)
                    cache.put(key, prediction['output'], ttl=args.ttl)
                    count += 1
                else:
                    print(f"Skipping invalid prediction: {line[:50]}...", file=sys.stderr)
                    errors += 1

            except Exception as e:
                print(f"Error processing line: {e}", file=sys.stderr)
                errors += 1

    print(f"Cache warming complete:")
    print(f"  Cached: {count}")
    print(f"  Errors: {errors}")


def cmd_invalidate(args):
    """Invalidate cache entries matching pattern."""
    cache = MultiLevelCache(
        redis_url=args.redis_url,
        memory_capacity=args.memory_capacity,
    )

    if args.all:
        mem_count, redis_count = cache.clear()
        print(f"Cleared all cache entries:")
        print(f"  Redis: {redis_count}")
    elif args.pattern:
        count = cache.invalidate_pattern(args.pattern)
        print(f"Invalidated {count} entries matching: {args.pattern}")
    elif args.key:
        success = cache.delete(args.key)
        if success:
            print(f"Invalidated: {args.key}")
        else:
            print(f"Key not found: {args.key}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: Must specify --all, --pattern, or --key", file=sys.stderr)
        sys.exit(1)


def cmd_stats(args):
    """Show cache statistics."""
    cache = MultiLevelCache(
        redis_url=args.redis_url,
        memory_capacity=args.memory_capacity,
    )

    stats = cache.get_stats()

    print("\nCache Statistics:")
    print("=" * 60)
    print(f"\nMemory Cache (L1):")
    print(f"  Size: {stats['memory_size']}/{stats['memory_capacity']}")
    print(f"  Hits: {stats['hits_memory']}")

    print(f"\nRedis Cache (L2):")
    print(f"  Connected: {stats['redis_connected']}")
    print(f"  Hits: {stats['hits_redis']}")

    print(f"\nOverall:")
    print(f"  Total Requests: {stats['total_requests']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit Rate: {stats['hit_rate']:.2%}")
    print(f"  Writes: {stats['writes']}")
    print(f"  Errors: {stats['errors']}")

    print("\n" + "=" * 60 + "\n")


def cmd_inspect(args):
    """Inspect cache contents."""
    cache = MultiLevelCache(
        redis_url=args.redis_url,
        memory_capacity=args.memory_capacity,
    )

    top_entries = cache.inspect_top(args.top)

    print(f"\nTop {len(top_entries)} Most Accessed Cache Entries:")
    print("=" * 80)

    for i, entry in enumerate(top_entries, 1):
        print(f"\n{i}. Key: {entry['key']}")
        print(f"   Access Count: {entry['access_count']}")
        print(f"   Age: {entry['age_seconds']:.1f}s")
        print(f"   Cache Level: {entry['cache_level']}")
        if entry['last_accessed']:
            print(f"   Last Accessed: {entry['last_accessed']:.1f}")
        print(f"   Expired: {entry['expired']}")

    print("\n" + "=" * 80 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Multi-level cache manager for DSPy predictions"
    )

    # Global options
    parser.add_argument(
        "--redis-url",
        default=os.environ.get("REDIS_URL", "redis://localhost:6379"),
        help="Redis connection URL (default: redis://localhost:6379)",
    )
    parser.add_argument(
        "--memory-capacity",
        type=int,
        default=1000,
        help="Memory cache capacity (default: 1000)",
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Get command
    parser_get = subparsers.add_parser('get', help='Get value from cache')
    parser_get.add_argument('key', help='Cache key')

    # Set command
    parser_set = subparsers.add_parser('set', help='Set value in cache')
    parser_set.add_argument('--key', required=True, help='Cache key')
    parser_set.add_argument('--value', required=True, help='Value (JSON string or file path)')
    parser_set.add_argument('--ttl', type=int, help='TTL in seconds')

    # Warm command
    parser_warm = subparsers.add_parser('warm', help='Warm cache from predictions file')
    parser_warm.add_argument('--predictions', required=True, help='JSONL file with predictions')
    parser_warm.add_argument('--model', default='default', help='Model name for key generation')
    parser_warm.add_argument('--ttl', type=int, help='TTL in seconds')

    # Invalidate command
    parser_inv = subparsers.add_parser('invalidate', help='Invalidate cache entries')
    parser_inv.add_argument('--all', action='store_true', help='Clear all cache entries')
    parser_inv.add_argument('--pattern', help='Pattern to match (e.g., "question:*")')
    parser_inv.add_argument('--key', help='Specific key to invalidate')

    # Stats command
    parser_stats = subparsers.add_parser('stats', help='Show cache statistics')

    # Inspect command
    parser_inspect = subparsers.add_parser('inspect', help='Inspect cache contents')
    parser_inspect.add_argument('--top', type=int, default=10, help='Number of top entries (default: 10)')

    args = parser.parse_args()

    if args.command == 'get':
        cmd_get(args)
    elif args.command == 'set':
        cmd_set(args)
    elif args.command == 'warm':
        cmd_warm(args)
    elif args.command == 'invalidate':
        cmd_invalidate(args)
    elif args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'inspect':
        cmd_inspect(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
