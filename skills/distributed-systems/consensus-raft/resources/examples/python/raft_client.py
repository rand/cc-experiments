#!/usr/bin/env python3
"""
Production-ready etcd RAFT client examples

Demonstrates common patterns for working with etcd consensus:
- Basic key-value operations
- Transactions (atomic compare-and-swap)
- Leases (TTL-based keys for distributed locking)
- Watches (real-time change notifications)
- Leader election
- Configuration management

Requirements:
    pip install etcd3-py
"""

import time
import json
import threading
from typing import Optional, Callable
from contextlib import contextmanager

try:
    import etcd3
except ImportError:
    print("Error: etcd3-py not installed")
    print("Install with: pip install etcd3-py")
    exit(1)


class RAFTClient:
    """Production-ready etcd client with best practices"""

    def __init__(self, host='localhost', port=2379, timeout=10):
        """
        Initialize etcd client

        Args:
            host: etcd server hostname
            port: etcd server port
            timeout: Connection timeout in seconds
        """
        self.client = etcd3.client(host=host, port=port, timeout=timeout)
        self.host = host
        self.port = port

    def put(self, key: str, value: str, lease: Optional[int] = None) -> bool:
        """
        Write key-value pair (goes through RAFT consensus)

        Args:
            key: Key to write
            value: Value to write
            lease: Optional lease ID for TTL

        Returns:
            True if successful
        """
        try:
            if lease:
                self.client.put(key, value, lease=lease)
            else:
                self.client.put(key, value)
            return True
        except Exception as e:
            print(f"PUT error: {e}")
            return False

    def get(self, key: str) -> Optional[str]:
        """
        Read value for key (linearizable read from leader by default)

        Args:
            key: Key to read

        Returns:
            Value if found, None otherwise
        """
        try:
            value, metadata = self.client.get(key)
            return value.decode('utf-8') if value else None
        except Exception as e:
            print(f"GET error: {e}")
            return None

    def get_prefix(self, prefix: str) -> dict:
        """
        Get all keys with given prefix

        Args:
            prefix: Key prefix

        Returns:
            Dictionary of key-value pairs
        """
        try:
            results = {}
            for value, metadata in self.client.get_prefix(prefix):
                key = metadata.key.decode('utf-8')
                val = value.decode('utf-8')
                results[key] = val
            return results
        except Exception as e:
            print(f"GET_PREFIX error: {e}")
            return {}

    def delete(self, key: str) -> bool:
        """
        Delete key

        Args:
            key: Key to delete

        Returns:
            True if deleted
        """
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"DELETE error: {e}")
            return False

    def compare_and_swap(self, key: str, expected_value: str, new_value: str) -> bool:
        """
        Atomic compare-and-swap using transaction

        Args:
            key: Key to update
            expected_value: Expected current value
            new_value: New value to set

        Returns:
            True if swap succeeded
        """
        try:
            success, responses = self.client.transaction(
                compare=[
                    self.client.transactions.value(key) == expected_value.encode('utf-8')
                ],
                success=[
                    self.client.transactions.put(key, new_value)
                ],
                failure=[
                    self.client.transactions.get(key)
                ]
            )
            return success
        except Exception as e:
            print(f"CAS error: {e}")
            return False

    def increment_counter(self, key: str) -> Optional[int]:
        """
        Atomically increment counter using transaction

        Args:
            key: Counter key

        Returns:
            New counter value, None on error
        """
        try:
            while True:
                current_value = self.get(key)
                current = int(current_value) if current_value else 0
                new_value = current + 1

                if self.compare_and_swap(key, str(current), str(new_value)):
                    return new_value

                # CAS failed, retry
                time.sleep(0.001)
        except Exception as e:
            print(f"INCREMENT error: {e}")
            return None

    @contextmanager
    def lease(self, ttl: int):
        """
        Context manager for lease (TTL-based key)

        Args:
            ttl: Time-to-live in seconds

        Usage:
            with client.lease(60) as lease_id:
                client.put('/ephemeral/key', 'value', lease=lease_id)
        """
        lease_obj = self.client.lease(ttl)
        try:
            yield lease_obj.id
        finally:
            lease_obj.revoke()

    def watch(self, key: str, callback: Callable, prefix: bool = False):
        """
        Watch for changes to key

        Args:
            key: Key to watch
            callback: Function to call on changes (receives event)
            prefix: If True, watch all keys with prefix

        Usage:
            def on_change(event):
                print(f"Changed: {event.key} = {event.value}")

            client.watch('/config/', on_change, prefix=True)
        """
        try:
            watch_id = self.client.add_watch_callback(
                key,
                callback,
                range_end=self.client.range_end_for_prefix(key) if prefix else None
            )
            return watch_id
        except Exception as e:
            print(f"WATCH error: {e}")
            return None


class DistributedLock:
    """Distributed lock using etcd leases"""

    def __init__(self, client: RAFTClient, lock_name: str, ttl: int = 60):
        """
        Initialize distributed lock

        Args:
            client: RAFT client
            lock_name: Unique lock identifier
            ttl: Lock TTL in seconds
        """
        self.client = client
        self.lock_key = f'/locks/{lock_name}'
        self.ttl = ttl
        self.lease_id = None
        self.keep_alive_thread = None
        self.stop_keep_alive = False

    def acquire(self, timeout: int = 10) -> bool:
        """
        Acquire lock (blocking with timeout)

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if acquired
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Create lease
            lease = self.client.client.lease(self.ttl)
            self.lease_id = lease.id

            # Try to acquire lock (create key if doesn't exist)
            success, _ = self.client.client.transaction(
                compare=[
                    self.client.client.transactions.version(self.lock_key) == 0
                ],
                success=[
                    self.client.client.transactions.put(
                        self.lock_key,
                        'locked',
                        lease=self.lease_id
                    )
                ],
                failure=[]
            )

            if success:
                # Start keep-alive thread
                self._start_keep_alive(lease)
                return True

            # Lock held by someone else, wait and retry
            time.sleep(0.1)

        return False

    def release(self):
        """Release lock"""
        self.stop_keep_alive = True
        if self.keep_alive_thread:
            self.keep_alive_thread.join()

        if self.lease_id:
            try:
                self.client.client.revoke_lease(self.lease_id)
            except:
                pass
            self.lease_id = None

    def _start_keep_alive(self, lease):
        """Start background thread to keep lease alive"""
        def keep_alive():
            while not self.stop_keep_alive:
                try:
                    lease.refresh()
                except:
                    break
                time.sleep(self.ttl / 3)  # Refresh at 1/3 TTL

        self.keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        self.keep_alive_thread.start()

    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            raise RuntimeError("Failed to acquire lock")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()


class LeaderElection:
    """Leader election using etcd"""

    def __init__(self, client: RAFTClient, election_name: str, node_id: str, ttl: int = 60):
        """
        Initialize leader election

        Args:
            client: RAFT client
            election_name: Unique election identifier
            node_id: This node's identifier
            ttl: Leadership TTL in seconds
        """
        self.client = client
        self.election_key = f'/elections/{election_name}/leader'
        self.node_id = node_id
        self.ttl = ttl
        self.is_leader = False
        self.lease_id = None
        self.keep_alive_thread = None
        self.stop_keep_alive = False

    def campaign(self) -> bool:
        """
        Attempt to become leader

        Returns:
            True if became leader
        """
        # Create lease
        lease = self.client.client.lease(self.ttl)
        self.lease_id = lease.id

        # Try to become leader
        success, _ = self.client.client.transaction(
            compare=[
                self.client.client.transactions.version(self.election_key) == 0
            ],
            success=[
                self.client.client.transactions.put(
                    self.election_key,
                    self.node_id,
                    lease=self.lease_id
                )
            ],
            failure=[]
        )

        if success:
            self.is_leader = True
            self._start_keep_alive(lease)
            return True

        return False

    def resign(self):
        """Resign from leadership"""
        self.stop_keep_alive = True
        if self.keep_alive_thread:
            self.keep_alive_thread.join()

        if self.lease_id:
            try:
                self.client.client.revoke_lease(self.lease_id)
            except:
                pass
            self.lease_id = None

        self.is_leader = False

    def get_leader(self) -> Optional[str]:
        """
        Get current leader

        Returns:
            Leader node ID, None if no leader
        """
        leader = self.client.get(self.election_key)
        return leader

    def _start_keep_alive(self, lease):
        """Start background thread to keep lease alive"""
        def keep_alive():
            while not self.stop_keep_alive:
                try:
                    lease.refresh()
                except:
                    self.is_leader = False
                    break
                time.sleep(self.ttl / 3)

        self.keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        self.keep_alive_thread.start()


# Example usage
if __name__ == '__main__':
    print("=== RAFT Client Examples ===\n")

    # Initialize client
    client = RAFTClient(host='localhost', port=2379)

    # 1. Basic key-value operations
    print("1. Basic Operations:")
    client.put('/config/app_name', 'my-app')
    value = client.get('/config/app_name')
    print(f"   GET /config/app_name = {value}")

    # 2. Atomic counter
    print("\n2. Atomic Counter:")
    for i in range(5):
        count = client.increment_counter('/counters/requests')
        print(f"   Request count: {count}")

    # 3. Compare-and-swap
    print("\n3. Compare-and-Swap:")
    client.put('/status', 'idle')
    success = client.compare_and_swap('/status', 'idle', 'processing')
    print(f"   CAS idle->processing: {success}")
    success = client.compare_and_swap('/status', 'idle', 'done')
    print(f"   CAS idle->done: {success} (expected False)")

    # 4. Lease (TTL)
    print("\n4. Lease (TTL):")
    with client.lease(10) as lease_id:
        client.put('/temp/session', 'active', lease=lease_id)
        print(f"   Created ephemeral key with 10s TTL")

    # 5. Distributed lock
    print("\n5. Distributed Lock:")
    lock = DistributedLock(client, 'my-resource')
    if lock.acquire():
        print("   Lock acquired")
        time.sleep(1)
        lock.release()
        print("   Lock released")

    # 6. Leader election
    print("\n6. Leader Election:")
    election = LeaderElection(client, 'my-service', 'node-1')
    if election.campaign():
        print(f"   Node {election.node_id} became leader")
        time.sleep(2)
        election.resign()
        print("   Resigned leadership")
    else:
        leader = election.get_leader()
        print(f"   Current leader: {leader}")

    # 7. Watch for changes
    print("\n7. Watch (run 'etcdctl put /watch/test value' in another terminal):")

    def on_change(event):
        print(f"   Change detected: {event.key.decode('utf-8')} = {event.value.decode('utf-8')}")

    watch_id = client.watch('/watch/', on_change, prefix=True)
    print("   Watching /watch/* for 5 seconds...")
    time.sleep(5)

    print("\n=== Examples Complete ===")
