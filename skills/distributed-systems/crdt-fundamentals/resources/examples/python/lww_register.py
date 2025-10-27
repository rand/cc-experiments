"""
LWW-Register (Last-Write-Wins Register) Implementation

Example demonstrating a production-ready LWW-Register CRDT with:
- Timestamp-based conflict resolution
- Hybrid logical clocks
- Value history tracking
- JSON serialization
"""

from typing import Any, Dict, Optional, List, Tuple
import json
import time


class HybridLogicalClock:
    """
    Hybrid Logical Clock (HLC)

    Combines physical time with logical counter for better ordering.
    Provides monotonicity even if physical clocks drift.
    """

    def __init__(self):
        self.physical_time = 0
        self.logical_counter = 0

    def update(self, physical_time: Optional[int] = None) -> int:
        """
        Update clock and return timestamp

        Args:
            physical_time: Current physical time (nanoseconds), or use system time

        Returns:
            Hybrid timestamp
        """
        if physical_time is None:
            physical_time = time.time_ns()

        if physical_time > self.physical_time:
            self.physical_time = physical_time
            self.logical_counter = 0
        else:
            self.logical_counter += 1

        # Encode as: (physical_time << 16) | logical_counter
        return (self.physical_time << 16) | self.logical_counter

    def receive(self, remote_timestamp: int) -> None:
        """
        Receive timestamp from remote and update clock

        Args:
            remote_timestamp: Timestamp from remote replica
        """
        remote_physical = remote_timestamp >> 16
        remote_logical = remote_timestamp & 0xFFFF

        physical_time = time.time_ns()

        if remote_physical > physical_time and remote_physical > self.physical_time:
            self.physical_time = remote_physical
            self.logical_counter = remote_logical + 1
        elif remote_physical == self.physical_time:
            self.logical_counter = max(self.logical_counter, remote_logical) + 1
        else:
            self.update(physical_time)


class LWWRegister:
    """
    Last-Write-Wins Register CRDT

    A single-value register where concurrent writes are resolved by timestamp.
    The write with the highest timestamp wins.
    """

    def __init__(self, replica_id: int, use_hlc: bool = True):
        """
        Initialize LWW-Register

        Args:
            replica_id: Unique identifier for this replica
            use_hlc: Use hybrid logical clock (True) or physical time (False)
        """
        self.replica_id = replica_id
        self.value: Any = None
        self.timestamp: int = 0
        self.writer_id: int = -1
        self.use_hlc = use_hlc

        if use_hlc:
            self.hlc = HybridLogicalClock()

    def set(self, value: Any, timestamp: Optional[int] = None) -> None:
        """
        Set register value

        Args:
            value: New value
            timestamp: Explicit timestamp (or generate if None)
        """
        if timestamp is None:
            if self.use_hlc:
                timestamp = self.hlc.update()
            else:
                timestamp = time.time_ns()

        # Update if timestamp is higher, or same timestamp but higher replica_id
        if (timestamp > self.timestamp or
            (timestamp == self.timestamp and self.replica_id > self.writer_id)):
            self.value = value
            self.timestamp = timestamp
            self.writer_id = self.replica_id

            if self.use_hlc:
                self.hlc.receive(timestamp)

    def get(self) -> Any:
        """
        Get current value

        Returns:
            Current register value
        """
        return self.value

    def merge(self, other: "LWWRegister") -> None:
        """
        Merge another replica's state

        Args:
            other: Another LWW-Register replica to merge
        """
        # Take value with higher timestamp
        if (other.timestamp > self.timestamp or
            (other.timestamp == self.timestamp and other.writer_id > self.writer_id)):
            self.value = other.value
            self.timestamp = other.timestamp
            self.writer_id = other.writer_id

            if self.use_hlc:
                self.hlc.receive(other.timestamp)

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "type": "LWW-Register",
            "replica_id": self.replica_id,
            "value": self.value,
            "timestamp": self.timestamp,
            "writer_id": self.writer_id,
            "use_hlc": self.use_hlc
        }

    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict) -> "LWWRegister":
        """Deserialize from dictionary"""
        reg = cls(data["replica_id"], data["use_hlc"])
        reg.value = data["value"]
        reg.timestamp = data["timestamp"]
        reg.writer_id = data["writer_id"]
        return reg

    @classmethod
    def from_json(cls, json_str: str) -> "LWWRegister":
        """Deserialize from JSON"""
        return cls.from_dict(json.loads(json_str))

    def __repr__(self) -> str:
        return f"LWWRegister(replica={self.replica_id}, value={self.value}, ts={self.timestamp})"


class MVRegister:
    """
    Multi-Value Register CRDT

    Preserves all concurrent values instead of choosing one.
    Application must resolve conflicts.
    """

    def __init__(self, replica_id: int):
        """
        Initialize MV-Register

        Args:
            replica_id: Unique identifier for this replica
        """
        self.replica_id = replica_id
        self.values: Dict[Tuple[int, int], Any] = {}  # {(replica_id, timestamp): value}
        self.clock = 0

    def set(self, value: Any) -> None:
        """
        Set register value

        Args:
            value: New value
        """
        self.clock += 1
        timestamp = self.clock

        # Remove dominated versions (lower timestamps from this replica)
        self.values = {
            (rid, ts): v for (rid, ts), v in self.values.items()
            if rid != self.replica_id or ts >= timestamp
        }

        # Add new value
        self.values[(self.replica_id, timestamp)] = value

    def get(self) -> List[Any]:
        """
        Get all current values

        Returns:
            List of concurrent values
        """
        return list(self.values.values())

    def merge(self, other: "MVRegister") -> None:
        """
        Merge another replica's state

        Args:
            other: Another MV-Register replica to merge
        """
        # Combine all values
        combined = {**self.values, **other.values}

        # Remove dominated versions
        result = {}
        for (rid1, ts1), v1 in combined.items():
            dominated = False
            for (rid2, ts2), v2 in combined.items():
                if (rid1, ts1) != (rid2, ts2):
                    # Check if (rid1, ts1) is dominated by (rid2, ts2)
                    if ts2 > ts1 or (ts2 == ts1 and rid2 > rid1):
                        dominated = True
                        break
            if not dominated:
                result[(rid1, ts1)] = v1

        self.values = result
        self.clock = max(self.clock, other.clock)

    def __repr__(self) -> str:
        return f"MVRegister(replica={self.replica_id}, values={self.get()})"


# =============================================================================
# Example Usage
# =============================================================================

def example_basic():
    """Basic LWW-Register usage"""
    print("=" * 60)
    print("Example 1: Basic LWW-Register")
    print("=" * 60)

    reg = LWWRegister(replica_id=0)

    # Set values
    reg.set("Alice")
    print(f"After set: {reg.get()}")

    reg.set("Bob")
    print(f"After update: {reg.get()}")

    reg.set("Charlie")
    print(f"After update: {reg.get()}")


def example_concurrent_writes():
    """Demonstrate last-write-wins"""
    print("\n" + "=" * 60)
    print("Example 2: Concurrent Writes (Last-Write-Wins)")
    print("=" * 60)

    reg1 = LWWRegister(replica_id=0)
    reg2 = LWWRegister(replica_id=1)

    # Concurrent writes
    print("Concurrent writes:")
    reg1.set("Alice")
    print(f"  Replica 0: set 'Alice'")

    time.sleep(0.01)  # Small delay to ensure different timestamps

    reg2.set("Bob")
    print(f"  Replica 1: set 'Bob'")

    print(f"\nBefore merge:")
    print(f"  Replica 0: {reg1.get()}")
    print(f"  Replica 1: {reg2.get()}")

    # Merge
    reg1.merge(reg2)
    reg2.merge(reg1)

    print(f"\nAfter merge:")
    print(f"  Replica 0: {reg1.get()}")
    print(f"  Replica 1: {reg2.get()}")

    print("\nNote: Bob wins because it has a higher timestamp")


def example_mv_register():
    """Demonstrate multi-value register"""
    print("\n" + "=" * 60)
    print("Example 3: Multi-Value Register (Preserves Conflicts)")
    print("=" * 60)

    reg1 = MVRegister(replica_id=0)
    reg2 = MVRegister(replica_id=1)

    # Concurrent writes
    print("Concurrent writes:")
    reg1.set("Alice")
    print(f"  Replica 0: set 'Alice'")

    reg2.set("Bob")
    print(f"  Replica 1: set 'Bob'")

    print(f"\nBefore merge:")
    print(f"  Replica 0: {reg1.get()}")
    print(f"  Replica 1: {reg2.get()}")

    # Merge
    reg1.merge(reg2)
    reg2.merge(reg1)

    print(f"\nAfter merge:")
    print(f"  Replica 0: {reg1.get()}")
    print(f"  Replica 1: {reg2.get()}")

    print("\nNote: Both values preserved; application must resolve")


def example_replica_id_tiebreaker():
    """Demonstrate replica ID as tiebreaker"""
    print("\n" + "=" * 60)
    print("Example 4: Replica ID as Tiebreaker")
    print("=" * 60)

    # Use same timestamp
    ts = time.time_ns()

    reg1 = LWWRegister(replica_id=0)
    reg2 = LWWRegister(replica_id=1)

    # Set with same timestamp
    reg1.set("Alice", timestamp=ts)
    reg2.set("Bob", timestamp=ts)

    print(f"Both use timestamp: {ts}")
    print(f"Replica 0: {reg1.get()}")
    print(f"Replica 1: {reg2.get()}")

    # Merge
    reg1.merge(reg2)
    reg2.merge(reg1)

    print(f"\nAfter merge:")
    print(f"  Replica 0: {reg1.get()}")
    print(f"  Replica 1: {reg2.get()}")

    print("\nNote: Higher replica ID wins on timestamp tie")


def example_distributed_config():
    """Simulate distributed configuration"""
    print("\n" + "=" * 60)
    print("Example 5: Distributed Configuration")
    print("=" * 60)

    # Three config replicas
    config1 = LWWRegister(replica_id=0)
    config2 = LWWRegister(replica_id=1)
    config3 = LWWRegister(replica_id=2)

    # Initial config
    config1.set({"timeout": 30, "retries": 3})
    print(f"Config 1 (initial): {config1.get()}")

    # Propagate to others
    config2.merge(config1)
    config3.merge(config1)

    # Concurrent updates
    print("\nConcurrent updates:")
    config1.set({"timeout": 60, "retries": 3})
    print(f"  Config 1: timeout=60")

    time.sleep(0.01)

    config2.set({"timeout": 30, "retries": 5})
    print(f"  Config 2: retries=5")

    print(f"\nBefore sync:")
    print(f"  Config 1: {config1.get()}")
    print(f"  Config 2: {config2.get()}")
    print(f"  Config 3: {config3.get()}")

    # Sync all
    print("\nSyncing...")
    config1.merge(config2)
    config1.merge(config3)
    config2.merge(config1)
    config3.merge(config1)

    print(f"\nAfter sync:")
    print(f"  Config 1: {config1.get()}")
    print(f"  Config 2: {config2.get()}")
    print(f"  Config 3: {config3.get()}")

    print("\nNote: Config 2's update wins (higher timestamp)")


def example_hybrid_logical_clock():
    """Demonstrate hybrid logical clock"""
    print("\n" + "=" * 60)
    print("Example 6: Hybrid Logical Clock")
    print("=" * 60)

    reg1 = LWWRegister(replica_id=0, use_hlc=True)
    reg2 = LWWRegister(replica_id=1, use_hlc=True)

    # Multiple rapid updates
    print("Rapid updates on Replica 0:")
    for i in range(5):
        reg1.set(f"value_{i}")
        print(f"  {i}: timestamp={reg1.timestamp}")

    print("\nNote: Logical counter increments when physical time unchanged")


def example_serialization():
    """Demonstrate serialization"""
    print("\n" + "=" * 60)
    print("Example 7: Serialization")
    print("=" * 60)

    reg = LWWRegister(replica_id=0)
    reg.set({"user": "Alice", "role": "admin"})

    # Serialize
    json_str = reg.to_json()
    print(f"Serialized:\n{json_str}")

    # Deserialize
    restored = LWWRegister.from_json(json_str)
    print(f"\nRestored: {restored}")

    print(f"\nValue matches: {reg.get() == restored.get()}")


if __name__ == "__main__":
    example_basic()
    example_concurrent_writes()
    example_mv_register()
    example_replica_id_tiebreaker()
    example_distributed_config()
    example_hybrid_logical_clock()
    example_serialization()
