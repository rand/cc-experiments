"""
Redis Caching Patterns Examples

Demonstrates cache-aside and write-through caching strategies.
"""

import json
import time
from typing import Optional, Dict, Any

import redis


class Database:
    """Mock database for demonstration."""

    def __init__(self):
        self.data = {
            1: {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30},
            2: {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25},
            3: {"id": 3, "name": "Charlie", "email": "charlie@example.com", "age": 35},
        }
        self.query_count = 0

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Simulate database query."""
        print(f"[DB] Querying user {user_id}...")
        time.sleep(0.1)  # Simulate latency
        self.query_count += 1
        return self.data.get(user_id)

    def update_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """Simulate database update."""
        print(f"[DB] Updating user {user_id}...")
        time.sleep(0.1)  # Simulate latency
        if user_id in self.data:
            self.data[user_id].update(data)
            return True
        return False


class CacheAside:
    """
    Cache-Aside Pattern (Lazy Loading)

    Application reads from cache first. On miss, loads from DB and updates cache.
    """

    def __init__(self, redis_client: redis.Redis, db: Database, ttl: int = 300):
        self.redis = redis_client
        self.db = db
        self.ttl = ttl

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user with cache-aside pattern.

        1. Check cache
        2. On miss: Load from DB
        3. Update cache
        4. Return data
        """
        cache_key = f"user:{user_id}"

        # Try cache first
        print(f"[Cache-Aside] Checking cache for user {user_id}...")
        cached = self.redis.get(cache_key)

        if cached:
            print(f"[Cache-Aside] Cache HIT for user {user_id}")
            return json.loads(cached)

        print(f"[Cache-Aside] Cache MISS for user {user_id}")

        # Load from database
        user = self.db.get_user(user_id)

        if user:
            # Update cache
            print(f"[Cache-Aside] Updating cache for user {user_id}")
            self.redis.setex(cache_key, self.ttl, json.dumps(user))

        return user

    def invalidate_user(self, user_id: int):
        """Invalidate cache entry."""
        cache_key = f"user:{user_id}"
        print(f"[Cache-Aside] Invalidating cache for user {user_id}")
        self.redis.delete(cache_key)


class WriteThrough:
    """
    Write-Through Pattern

    All writes go through cache, which synchronously writes to DB.
    """

    def __init__(self, redis_client: redis.Redis, db: Database, ttl: int = 300):
        self.redis = redis_client
        self.db = db
        self.ttl = ttl

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user from cache (assumes write-through keeps cache updated).
        """
        cache_key = f"user:wt:{user_id}"

        print(f"[Write-Through] Reading from cache for user {user_id}...")
        cached = self.redis.get(cache_key)

        if cached:
            print(f"[Write-Through] Cache HIT for user {user_id}")
            return json.loads(cached)

        print(f"[Write-Through] Cache MISS for user {user_id}")

        # On miss, load from DB and cache
        user = self.db.get_user(user_id)
        if user:
            self.redis.setex(cache_key, self.ttl, json.dumps(user))

        return user

    def update_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """
        Update user with write-through pattern.

        1. Update cache
        2. Update database
        3. Return success
        """
        cache_key = f"user:wt:{user_id}"

        print(f"[Write-Through] Updating user {user_id}...")

        # Get current user
        user = self.db.get_user(user_id)
        if not user:
            return False

        # Update data
        user.update(data)

        # Write to cache first
        print(f"[Write-Through] Writing to cache...")
        self.redis.setex(cache_key, self.ttl, json.dumps(user))

        # Write to database
        print(f"[Write-Through] Writing to database...")
        success = self.db.update_user(user_id, data)

        if not success:
            # Rollback cache on DB failure
            print(f"[Write-Through] DB write failed, invalidating cache...")
            self.redis.delete(cache_key)

        return success


class WriteBehind:
    """
    Write-Behind Pattern (Write-Back)

    Writes to cache immediately, queues for async DB write.
    """

    def __init__(self, redis_client: redis.Redis, db: Database, ttl: int = 300):
        self.redis = redis_client
        self.db = db
        self.ttl = ttl

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user from cache."""
        cache_key = f"user:wb:{user_id}"

        cached = self.redis.get(cache_key)
        if cached:
            print(f"[Write-Behind] Cache HIT for user {user_id}")
            return json.loads(cached)

        print(f"[Write-Behind] Cache MISS for user {user_id}")

        # Load from DB
        user = self.db.get_user(user_id)
        if user:
            self.redis.setex(cache_key, self.ttl, json.dumps(user))

        return user

    def update_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """
        Update user with write-behind pattern.

        1. Update cache immediately
        2. Queue for async DB write
        3. Return success (fast)
        """
        cache_key = f"user:wb:{user_id}"
        write_queue = "write_queue"

        print(f"[Write-Behind] Updating user {user_id}...")

        # Get current user
        user = self.db.get_user(user_id)
        if not user:
            return False

        # Update data
        user.update(data)

        # Write to cache immediately
        print(f"[Write-Behind] Writing to cache (fast)...")
        self.redis.setex(cache_key, self.ttl, json.dumps(user))

        # Queue for async DB write
        print(f"[Write-Behind] Queuing for async DB write...")
        write_task = {
            "user_id": user_id,
            "data": data,
            "timestamp": time.time()
        }
        self.redis.lpush(write_queue, json.dumps(write_task))

        return True

    def process_write_queue(self, batch_size: int = 10):
        """
        Process queued writes (background worker).

        In production, this would run in a separate process.
        """
        write_queue = "write_queue"

        print(f"[Write-Behind] Processing write queue...")

        for _ in range(batch_size):
            task_data = self.redis.rpop(write_queue)
            if not task_data:
                break

            task = json.loads(task_data)
            user_id = task["user_id"]
            data = task["data"]

            print(f"[Write-Behind] Processing queued write for user {user_id}...")
            self.db.update_user(user_id, data)


def demo_cache_aside():
    """Demonstrate cache-aside pattern."""
    print("\n" + "=" * 60)
    print("Cache-Aside Pattern Demo")
    print("=" * 60)

    redis_client = redis.Redis(decode_responses=True)
    db = Database()
    cache = CacheAside(redis_client, db)

    # First read: cache miss, loads from DB
    print("\n--- First read (cache miss) ---")
    user = cache.get_user(1)
    print(f"Result: {user}")

    # Second read: cache hit
    print("\n--- Second read (cache hit) ---")
    user = cache.get_user(1)
    print(f"Result: {user}")

    # Invalidate cache
    print("\n--- Invalidate cache ---")
    cache.invalidate_user(1)

    # Third read: cache miss again
    print("\n--- Third read (cache miss after invalidation) ---")
    user = cache.get_user(1)
    print(f"Result: {user}")

    print(f"\n[Stats] Database queries: {db.query_count}")


def demo_write_through():
    """Demonstrate write-through pattern."""
    print("\n" + "=" * 60)
    print("Write-Through Pattern Demo")
    print("=" * 60)

    redis_client = redis.Redis(decode_responses=True)
    db = Database()
    cache = WriteThrough(redis_client, db)

    # Read user
    print("\n--- Initial read ---")
    user = cache.get_user(2)
    print(f"Result: {user}")

    # Update user (writes to both cache and DB)
    print("\n--- Update user ---")
    cache.update_user(2, {"age": 26})

    # Read again (from cache)
    print("\n--- Read after update (from cache) ---")
    user = cache.get_user(2)
    print(f"Result: {user}")

    print(f"\n[Stats] Database queries: {db.query_count}")


def demo_write_behind():
    """Demonstrate write-behind pattern."""
    print("\n" + "=" * 60)
    print("Write-Behind Pattern Demo")
    print("=" * 60)

    redis_client = redis.Redis(decode_responses=True)
    db = Database()
    cache = WriteBehind(redis_client, db)

    # Read user
    print("\n--- Initial read ---")
    user = cache.get_user(3)
    print(f"Result: {user}")

    # Update user (writes to cache, queues for DB)
    print("\n--- Update user (fast write) ---")
    start = time.time()
    cache.update_user(3, {"age": 36})
    duration = time.time() - start
    print(f"Update completed in {duration:.3f}s (fast!)")

    # Read again (from cache, DB not updated yet)
    print("\n--- Read after update (from cache) ---")
    user = cache.get_user(3)
    print(f"Result: {user}")
    print(f"Note: DB not updated yet, but cache has new value")

    # Process write queue (background worker)
    print("\n--- Process write queue (background worker) ---")
    cache.process_write_queue()

    print(f"\n[Stats] Database queries: {db.query_count}")


def demo_cache_performance():
    """Compare performance with and without caching."""
    print("\n" + "=" * 60)
    print("Cache Performance Comparison")
    print("=" * 60)

    redis_client = redis.Redis(decode_responses=True)
    db = Database()
    cache = CacheAside(redis_client, db)

    # Without cache: read 100 times
    print("\n--- Without cache (100 reads) ---")
    start = time.time()
    for _ in range(100):
        db.get_user(1)
    duration_no_cache = time.time() - start
    print(f"Duration: {duration_no_cache:.3f}s")

    # With cache: read 100 times (first miss, rest hits)
    print("\n--- With cache (100 reads, 1 miss + 99 hits) ---")
    redis_client.delete("user:1")  # Clear cache
    db.query_count = 0
    start = time.time()
    for _ in range(100):
        cache.get_user(1)
    duration_cache = time.time() - start
    print(f"Duration: {duration_cache:.3f}s")
    print(f"Speedup: {duration_no_cache / duration_cache:.1f}x faster")
    print(f"Database queries: {db.query_count} (vs 100 without cache)")


def main():
    """Run all demos."""
    try:
        demo_cache_aside()
        demo_write_through()
        demo_write_behind()
        demo_cache_performance()

        print("\n" + "=" * 60)
        print("All demos completed!")
        print("=" * 60)
    except redis.exceptions.ConnectionError:
        print("Error: Cannot connect to Redis. Make sure Redis is running.")
        print("Start Redis with: redis-server")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
