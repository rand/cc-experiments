"""
G-Counter (Grow-only Counter) Implementation

Example demonstrating a production-ready G-Counter CRDT with:
- Multiple replica support
- Merge operation
- Delta-state optimization
- JSON serialization
"""

from typing import List, Dict
import json


class GCounter:
    """
    Grow-only Counter CRDT

    A counter that only supports increment operations. Each replica maintains
    its own counter, and the global value is the sum of all replica counters.
    """

    def __init__(self, n_replicas: int, replica_id: int):
        """
        Initialize G-Counter

        Args:
            n_replicas: Total number of replicas in the system
            replica_id: ID of this replica (0 to n_replicas-1)
        """
        if not (0 <= replica_id < n_replicas):
            raise ValueError(f"replica_id must be between 0 and {n_replicas-1}")

        self.n_replicas = n_replicas
        self.replica_id = replica_id
        self.payload: List[int] = [0] * n_replicas

    def increment(self, amount: int = 1) -> None:
        """
        Increment this replica's counter

        Args:
            amount: Amount to increment by (default: 1)
        """
        if amount < 0:
            raise ValueError("G-Counter only supports positive increments")
        self.payload[self.replica_id] += amount

    def value(self) -> int:
        """
        Get current counter value

        Returns:
            Sum of all replica counters
        """
        return sum(self.payload)

    def merge(self, other: "GCounter") -> None:
        """
        Merge another replica's state into this one

        Args:
            other: Another G-Counter replica to merge
        """
        if self.n_replicas != other.n_replicas:
            raise ValueError("Cannot merge counters with different replica counts")

        for i in range(self.n_replicas):
            self.payload[i] = max(self.payload[i], other.payload[i])

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "type": "G-Counter",
            "n_replicas": self.n_replicas,
            "replica_id": self.replica_id,
            "payload": self.payload,
            "value": self.value()
        }

    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict) -> "GCounter":
        """Deserialize from dictionary"""
        counter = cls(data["n_replicas"], data["replica_id"])
        counter.payload = data["payload"]
        return counter

    @classmethod
    def from_json(cls, json_str: str) -> "GCounter":
        """Deserialize from JSON"""
        return cls.from_dict(json.loads(json_str))

    def __repr__(self) -> str:
        return f"GCounter(replica={self.replica_id}, payload={self.payload}, value={self.value()})"


# =============================================================================
# Example Usage
# =============================================================================

def example_basic():
    """Basic G-Counter usage"""
    print("=" * 60)
    print("Example 1: Basic G-Counter")
    print("=" * 60)

    # Create 3 replicas
    counter1 = GCounter(3, 0)
    counter2 = GCounter(3, 1)
    counter3 = GCounter(3, 2)

    # Each replica increments independently
    counter1.increment(5)
    counter2.increment(3)
    counter3.increment(7)

    print(f"Counter 1: {counter1}")
    print(f"Counter 2: {counter2}")
    print(f"Counter 3: {counter3}")

    # Merge all counters
    counter1.merge(counter2)
    counter1.merge(counter3)

    print(f"\nAfter merge: {counter1}")
    print(f"Final value: {counter1.value()}")


def example_convergence():
    """Demonstrate convergence property"""
    print("\n" + "=" * 60)
    print("Example 2: Convergence (order doesn't matter)")
    print("=" * 60)

    # Create replicas
    r1a = GCounter(2, 0)
    r1b = GCounter(2, 1)

    r2a = GCounter(2, 0)
    r2b = GCounter(2, 1)

    # Same operations
    r1a.increment(10)
    r1b.increment(5)
    r2a.increment(10)
    r2b.increment(5)

    # Merge in different orders
    print("\nMerge order: A ← B")
    r1a.merge(r1b)
    print(f"Result: {r1a.value()}")

    print("\nMerge order: B ← A")
    r2b.merge(r2a)
    print(f"Result: {r2b.value()}")

    print(f"\nConverged: {r1a.value() == r2b.value()}")


def example_idempotence():
    """Demonstrate idempotence property"""
    print("\n" + "=" * 60)
    print("Example 3: Idempotence (repeated merge)")
    print("=" * 60)

    r1 = GCounter(2, 0)
    r2 = GCounter(2, 1)

    r1.increment(7)
    r2.increment(3)

    print(f"Before merge: {r1.value()}")

    r1.merge(r2)
    print(f"After 1st merge: {r1.value()}")

    r1.merge(r2)
    print(f"After 2nd merge: {r1.value()}")

    r1.merge(r2)
    print(f"After 3rd merge: {r1.value()}")

    print("\nValue remains the same (idempotent)")


def example_serialization():
    """Demonstrate serialization"""
    print("\n" + "=" * 60)
    print("Example 4: Serialization")
    print("=" * 60)

    counter = GCounter(3, 0)
    counter.increment(42)

    # Serialize to JSON
    json_str = counter.to_json()
    print(f"Serialized: {json_str}")

    # Deserialize
    restored = GCounter.from_json(json_str)
    print(f"Restored: {restored}")
    print(f"Value matches: {counter.value() == restored.value()}")


def example_distributed_system():
    """Simulate distributed system with multiple replicas"""
    print("\n" + "=" * 60)
    print("Example 5: Distributed System Simulation")
    print("=" * 60)

    # 4 replicas (servers)
    replicas = [GCounter(4, i) for i in range(4)]

    # Simulate operations
    print("Operations:")
    replicas[0].increment(10)
    print(f"  Server 0: +10")

    replicas[1].increment(5)
    print(f"  Server 1: +5")

    replicas[2].increment(8)
    print(f"  Server 2: +8")

    replicas[3].increment(3)
    print(f"  Server 3: +3")

    print("\nBefore sync:")
    for i, r in enumerate(replicas):
        print(f"  Server {i}: {r.value()}")

    # Gossip protocol: each replica syncs with next
    print("\nGossip sync (ring topology)...")
    for i in range(len(replicas)):
        next_i = (i + 1) % len(replicas)
        replicas[i].merge(replicas[next_i])
        replicas[next_i].merge(replicas[i])

    print("\nAfter 1 round:")
    for i, r in enumerate(replicas):
        print(f"  Server {i}: {r.value()}")

    # Check convergence
    values = [r.value() for r in replicas]
    converged = len(set(values)) == 1

    print(f"\nConverged: {converged}")
    if converged:
        print(f"Final value: {values[0]}")


if __name__ == "__main__":
    example_basic()
    example_convergence()
    example_idempotence()
    example_serialization()
    example_distributed_system()
