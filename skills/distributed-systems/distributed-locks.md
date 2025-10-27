---
name: distributed-systems-distributed-locks
description: Distributed locking patterns including Redis Redlock, ZooKeeper locks, lease-based locking, and fencing tokens
---

# Distributed Locks

**Scope**: Distributed mutual exclusion, Redlock, ZooKeeper locks, leases, fencing tokens
**Lines**: ~230
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Coordinating distributed processes
- Preventing concurrent resource access
- Implementing leader election
- Building job schedulers
- Ensuring exactly-once processing
- Understanding Redis, ZooKeeper patterns
- Implementing critical sections
- Handling distributed coordination

## Core Concepts

### Why Distributed Locks?

```
Problem: Multiple processes accessing shared resource

Process A ─┐
           ├─→ Shared Resource (database, file, etc.)
Process B ─┘

Without lock: Race conditions, data corruption
With lock: Only one process accesses at a time
```

### Properties

```
Safety: At most one process holds lock
Liveness: Eventually can acquire lock
Deadlock-free: No circular waiting
Fault tolerance: Works despite failures
```

---

## Lock Implementations

### 1. Redis-based Lock (Simple)

```python
import redis
import time
import uuid

class RedisLock:
    """Simple Redis-based distributed lock"""

    def __init__(self, redis_client, lock_name, ttl=10):
        self.redis = redis_client
        self.lock_name = f"lock:{lock_name}"
        self.ttl = ttl
        self.token = str(uuid.uuid4())

    def acquire(self, blocking=True, timeout=None):
        """Acquire lock"""
        start_time = time.time()

        while True:
            # SET if not exists with expiration
            acquired = self.redis.set(
                self.lock_name,
                self.token,
                nx=True,  # Only set if not exists
                ex=self.ttl  # Expire after TTL
            )

            if acquired:
                return True

            if not blocking:
                return False

            if timeout and (time.time() - start_time) > timeout:
                return False

            time.sleep(0.01)

    def release(self):
        """Release lock (only if we own it)"""
        # Lua script for atomic check-and-delete
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        self.redis.eval(lua_script, 1, self.lock_name, self.token)

# Usage
redis_client = redis.Redis()
lock = RedisLock(redis_client, "my_resource")

if lock.acquire(timeout=5):
    try:
        # Critical section
        process_resource()
    finally:
        lock.release()
```

### 2. Redlock Algorithm (Multi-Redis)

```python
import redis
import time

class Redlock:
    """Redlock algorithm across multiple Redis instances"""

    def __init__(self, redis_instances):
        self.redis_instances = redis_instances
        self.quorum = len(redis_instances) // 2 + 1

    def acquire(self, resource, ttl=10000):
        """Acquire lock on majority of instances"""
        token = str(uuid.uuid4())
        start_time = time.time()

        # Try to acquire on all instances
        acquired_count = 0
        for redis_client in self.redis_instances:
            try:
                if redis_client.set(f"lock:{resource}", token, nx=True, px=ttl):
                    acquired_count += 1
            except:
                pass

        elapsed = (time.time() - start_time) * 1000  # ms

        # Check if acquired on majority and within validity time
        validity_time = ttl - elapsed - 100  # drift

        if acquired_count >= self.quorum and validity_time > 0:
            return token, validity_time

        # Failed - release locks
        self.release(resource, token)
        return None, 0

    def release(self, resource, token):
        """Release lock on all instances"""
        for redis_client in self.redis_instances:
            try:
                lua = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                end
                """
                redis_client.eval(lua, 1, f"lock:{resource}", token)
            except:
                pass
```

### 3. ZooKeeper Lock

```python
from kazoo.client import KazooClient
from kazoo.recipe.lock import Lock

class ZooKeeperLock:
    """Distributed lock using ZooKeeper"""

    def __init__(self, zk_hosts, lock_path):
        self.zk = KazooClient(hosts=zk_hosts)
        self.zk.start()
        self.lock = Lock(self.zk, lock_path)

    def acquire(self, blocking=True, timeout=None):
        """Acquire lock"""
        return self.lock.acquire(blocking=blocking, timeout=timeout)

    def release(self):
        """Release lock"""
        self.lock.release()

# Usage
zk_lock = ZooKeeperLock("localhost:2181", "/locks/my_resource")

with zk_lock:
    # Critical section
    process_resource()
```

---

## Fencing Tokens

### Problem: Lock Timeout

```
Client A acquires lock
Client A pauses (GC, network delay)
Lock expires
Client B acquires lock
Client A resumes, thinks it still has lock!
```

### Solution: Fencing Tokens

```python
class FencedLock:
    """Lock with monotonically increasing fencing token"""

    def __init__(self):
        self.current_token = 0
        self.lock_holder = None

    def acquire(self, client_id):
        """Acquire lock with fencing token"""
        if self.lock_holder is None:
            self.current_token += 1
            self.lock_holder = (client_id, self.current_token)
            return self.current_token

        return None

    def release(self, client_id, token):
        """Release lock if token matches"""
        if self.lock_holder and self.lock_holder == (client_id, token):
            self.lock_holder = None
            return True

        return False

# Resource checks fencing token
class FencedResource:
    """Resource that validates fencing tokens"""

    def __init__(self):
        self.highest_token_seen = 0

    def write(self, data, fencing_token):
        """Write only if token is higher than any seen"""
        if fencing_token > self.highest_token_seen:
            self.highest_token_seen = fencing_token
            self._do_write(data)
        else:
            raise FencingTokenError("Stale token")
```

---

## Lease-Based Locking

```python
import time

class LeaseLock:
    """Lock with lease (time-based ownership)"""

    def __init__(self, ttl=10):
        self.ttl = ttl
        self.lease_end = 0
        self.holder = None

    def acquire(self, client_id):
        """Acquire lease"""
        now = time.time()

        # Check if current lease expired
        if now > self.lease_end:
            self.holder = client_id
            self.lease_end = now + self.ttl
            return True

        return False

    def renew(self, client_id):
        """Renew lease (keep-alive)"""
        now = time.time()

        if self.holder == client_id and now <= self.lease_end:
            self.lease_end = now + self.ttl
            return True

        return False

    def release(self, client_id):
        """Explicitly release lease"""
        if self.holder == client_id:
            self.lease_end = 0
            self.holder = None
            return True

        return False

# Client with keep-alive
class LeaseClient:
    def __init__(self, lock, client_id):
        self.lock = lock
        self.client_id = client_id
        self.keep_alive_thread = None

    def acquire_with_keepalive(self):
        """Acquire and automatically renew"""
        if self.lock.acquire(self.client_id):
            self._start_keepalive()
            return True

        return False

    def _start_keepalive(self):
        """Background thread to renew lease"""
        def renew_loop():
            while True:
                time.sleep(self.lock.ttl / 2)
                if not self.lock.renew(self.client_id):
                    break

        self.keep_alive_thread = threading.Thread(target=renew_loop, daemon=True)
        self.keep_alive_thread.start()
```

---

## Best Practices

### 1. Always Use Timeouts

```python
# ✅ Good: Timeout to prevent deadlock
if lock.acquire(timeout=30):
    try:
        work()
    finally:
        lock.release()

# ❌ Bad: Infinite wait
lock.acquire()  # Could hang forever
```

### 2. Use Try-Finally

```python
# ✅ Good: Always release
try:
    lock.acquire()
    work()
finally:
    lock.release()

# ❌ Bad: Exception leaves lock held
lock.acquire()
work()  # Exception → lock never released!
lock.release()
```

### 3. Set Appropriate TTL

```python
# ✅ Good: TTL longer than max work time
lock = RedisLock(redis_client, "resource", ttl=60)  # 60s for 30s job

# ❌ Bad: TTL too short
lock = RedisLock(redis_client, "resource", ttl=1)  # Expires during work!
```

---

## When NOT to Use Locks

```
❌ Don't use locks when:
- CRDTs or conflict-free operations possible
- Optimistic concurrency control sufficient
- Idempotent operations
- Performance critical path

✅ Do use locks when:
- True mutual exclusion required
- Coordination needed
- Non-idempotent operations
- Simplifies application logic
```

---

## Real-World Examples

### etcd Lock
```python
import etcd3

etcd = etcd3.client()

with etcd.lock('my-lock', ttl=60):
    # Critical section
    process_resource()
```

### Consul Lock
```python
import consul

c = consul.Consul()

session = c.session.create(ttl=60)

if c.kv.put('locks/my-resource', 'holder', acquire=session):
    try:
        # Critical section
        process_resource()
    finally:
        c.kv.put('locks/my-resource', '', release=session)
```

---

## Related Skills

- `distributed-systems-leader-election` - Leader election patterns
- `distributed-systems-consensus-raft` - Consensus algorithms
- `distributed-systems-eventual-consistency` - Consistency models

---

**Last Updated**: 2025-10-27
