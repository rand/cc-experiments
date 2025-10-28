"""
OR-Set (Observed-Remove Set) Implementation

Example demonstrating a production-ready OR-Set CRDT with:
- Add-wins semantics
- Unique tagging per add operation
- Concurrent add/remove handling
- JSON serialization
"""

from typing import Set, Tuple, Any, Dict, List
import json
import time


class ORSet:
    """
    Observed-Remove Set CRDT

    A set where elements can be added and removed multiple times.
    Concurrent add and remove operations: add wins.
    Each add creates a unique tag, and remove only affects observed adds.
    """

    def __init__(self, replica_id: int):
        """
        Initialize OR-Set

        Args:
            replica_id: Unique identifier for this replica
        """
        self.replica_id = replica_id
        self.payload: Set[Tuple[Any, int, int]] = set()  # (element, replica_id, timestamp)
        self.clock = 0

    def add(self, element: Any) -> Tuple[int, int]:
        """
        Add element to set

        Args:
            element: Element to add

        Returns:
            Unique tag (replica_id, timestamp) for this add
        """
        self.clock += 1
        tag = (self.replica_id, self.clock)
        self.payload.add((element, self.replica_id, self.clock))
        return tag

    def remove(self, element: Any) -> Set[Tuple[int, int]]:
        """
        Remove element from set

        Only removes tags that have been observed (are in local payload).

        Args:
            element: Element to remove

        Returns:
            Set of removed tags
        """
        removed_tags = set()
        new_payload = set()

        for elem, rid, ts in self.payload:
            if elem == element:
                removed_tags.add((rid, ts))
            else:
                new_payload.add((elem, rid, ts))

        self.payload = new_payload
        return removed_tags

    def contains(self, element: Any) -> bool:
        """
        Check if element is in set

        Args:
            element: Element to check

        Returns:
            True if element is in set
        """
        return any(elem == element for elem, _, _ in self.payload)

    def elements(self) -> Set[Any]:
        """
        Get set of unique elements

        Returns:
            Set of all unique elements
        """
        return {elem for elem, _, _ in self.payload}

    def merge(self, other: "ORSet") -> None:
        """
        Merge another replica's state into this one

        Args:
            other: Another OR-Set replica to merge
        """
        self.payload |= other.payload
        self.clock = max(self.clock, other.clock)

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "type": "OR-Set",
            "replica_id": self.replica_id,
            "clock": self.clock,
            "payload": [
                {"element": elem, "replica_id": rid, "timestamp": ts}
                for elem, rid, ts in sorted(self.payload, key=lambda x: (x[0], x[2]))
            ],
            "elements": sorted(list(self.elements()))
        }

    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict) -> "ORSet":
        """Deserialize from dictionary"""
        orset = cls(data["replica_id"])
        orset.clock = data["clock"]
        orset.payload = {
            (item["element"], item["replica_id"], item["timestamp"])
            for item in data["payload"]
        }
        return orset

    @classmethod
    def from_json(cls, json_str: str) -> "ORSet":
        """Deserialize from JSON"""
        return cls.from_dict(json.loads(json_str))

    def __repr__(self) -> str:
        return f"ORSet(replica={self.replica_id}, elements={sorted(self.elements())})"


# =============================================================================
# Example Usage
# =============================================================================

def example_basic():
    """Basic OR-Set usage"""
    print("=" * 60)
    print("Example 1: Basic OR-Set")
    print("=" * 60)

    orset = ORSet(replica_id=0)

    # Add elements
    orset.add("apple")
    orset.add("banana")
    orset.add("cherry")

    print(f"After adds: {orset.elements()}")

    # Remove element
    orset.remove("banana")

    print(f"After remove: {orset.elements()}")

    # Check membership
    print(f"Contains 'apple': {orset.contains('apple')}")
    print(f"Contains 'banana': {orset.contains('banana')}")


def example_add_wins():
    """Demonstrate add-wins semantics"""
    print("\n" + "=" * 60)
    print("Example 2: Add-Wins Semantics")
    print("=" * 60)

    # Two replicas
    set1 = ORSet(replica_id=0)
    set2 = ORSet(replica_id=1)

    # Both add "x"
    print("Both replicas add 'x'")
    set1.add("x")
    set2.add("x")

    print(f"Set 1: {set1.elements()}")
    print(f"Set 2: {set2.elements()}")

    # Set 1 removes "x" (only observes its own add)
    print("\nSet 1 removes 'x' (only knows about its own add)")
    set1.remove("x")
    print(f"Set 1: {set1.elements()}")

    # Merge
    print("\nMerge Set 2 into Set 1")
    set1.merge(set2)
    print(f"Set 1 after merge: {set1.elements()}")
    print("Note: 'x' survives because Set 2's add wasn't observed by Set 1's remove")


def example_concurrent_operations():
    """Demonstrate concurrent add/remove"""
    print("\n" + "=" * 60)
    print("Example 3: Concurrent Operations")
    print("=" * 60)

    # Three replicas
    set1 = ORSet(replica_id=0)
    set2 = ORSet(replica_id=1)
    set3 = ORSet(replica_id=2)

    # Concurrent operations
    print("Concurrent operations:")
    set1.add("a")
    print("  Set 1: add 'a'")

    set2.add("b")
    print("  Set 2: add 'b'")

    set3.add("a")  # Concurrent add of 'a'
    print("  Set 3: add 'a'")

    set1.remove("a")  # Remove 'a' from set1
    print("  Set 1: remove 'a'")

    print("\nBefore merge:")
    print(f"  Set 1: {set1.elements()}")
    print(f"  Set 2: {set2.elements()}")
    print(f"  Set 3: {set3.elements()}")

    # Merge all
    print("\nMerging...")
    set1.merge(set2)
    set1.merge(set3)
    set2.merge(set1)
    set3.merge(set1)

    print("\nAfter merge:")
    print(f"  Set 1: {set1.elements()}")
    print(f"  Set 2: {set2.elements()}")
    print(f"  Set 3: {set3.elements()}")

    print("\nNote: 'a' survives because Set 3's add was concurrent with Set 1's remove")


def example_readd():
    """Demonstrate re-adding removed elements"""
    print("\n" + "=" * 60)
    print("Example 4: Re-adding Removed Elements")
    print("=" * 60)

    orset = ORSet(replica_id=0)

    # Add, remove, add again
    print("Add 'item'")
    orset.add("item")
    print(f"  Elements: {orset.elements()}")

    print("\nRemove 'item'")
    orset.remove("item")
    print(f"  Elements: {orset.elements()}")

    print("\nAdd 'item' again")
    orset.add("item")
    print(f"  Elements: {orset.elements()}")

    print("\nNote: Element can be re-added after removal (new unique tag created)")


def example_unique_tags():
    """Demonstrate unique tags"""
    print("\n" + "=" * 60)
    print("Example 5: Unique Tags (Internal Representation)")
    print("=" * 60)

    orset = ORSet(replica_id=0)

    # Add same element multiple times
    tag1 = orset.add("x")
    tag2 = orset.add("x")
    tag3 = orset.add("x")

    print(f"Added 'x' three times:")
    print(f"  Tag 1: {tag1}")
    print(f"  Tag 2: {tag2}")
    print(f"  Tag 3: {tag3}")

    print(f"\nElements: {orset.elements()}")
    print(f"Payload size: {len(orset.payload)} (3 unique tags)")

    # Remove once
    print("\nRemove 'x' once")
    removed = orset.remove("x")
    print(f"  Removed tags: {len(removed)}")
    print(f"  Elements: {orset.elements()}")

    print("\nNote: All instances of 'x' removed when element is removed")


def example_distributed_shopping_cart():
    """Simulate distributed shopping cart"""
    print("\n" + "=" * 60)
    print("Example 6: Distributed Shopping Cart")
    print("=" * 60)

    # User has three devices
    mobile = ORSet(replica_id=0)
    desktop = ORSet(replica_id=1)
    tablet = ORSet(replica_id=2)

    # Operations on different devices
    print("Operations:")
    mobile.add("laptop")
    print("  Mobile: Add laptop")

    desktop.add("mouse")
    desktop.add("keyboard")
    print("  Desktop: Add mouse, keyboard")

    tablet.add("monitor")
    print("  Tablet: Add monitor")

    mobile.remove("laptop")  # Changed mind
    print("  Mobile: Remove laptop")

    tablet.add("laptop")  # But tablet adds it concurrently
    print("  Tablet: Add laptop (concurrent with mobile's remove)")

    print("\nBefore sync:")
    print(f"  Mobile: {mobile.elements()}")
    print(f"  Desktop: {desktop.elements()}")
    print(f"  Tablet: {tablet.elements()}")

    # Sync all devices
    print("\nSyncing devices...")
    mobile.merge(desktop)
    mobile.merge(tablet)
    desktop.merge(mobile)
    tablet.merge(mobile)

    print("\nAfter sync (all devices):")
    print(f"  Mobile: {mobile.elements()}")
    print(f"  Desktop: {desktop.elements()}")
    print(f"  Tablet: {tablet.elements()}")

    converged = (mobile.elements() == desktop.elements() == tablet.elements())
    print(f"\nConverged: {converged}")


def example_serialization():
    """Demonstrate serialization"""
    print("\n" + "=" * 60)
    print("Example 7: Serialization")
    print("=" * 60)

    orset = ORSet(replica_id=0)
    orset.add("red")
    orset.add("green")
    orset.add("blue")

    # Serialize
    json_str = orset.to_json()
    print(f"Serialized:\n{json_str}")

    # Deserialize
    restored = ORSet.from_json(json_str)
    print(f"\nRestored: {restored}")

    print(f"\nElements match: {orset.elements() == restored.elements()}")


if __name__ == "__main__":
    example_basic()
    example_add_wins()
    example_concurrent_operations()
    example_readd()
    example_unique_tags()
    example_distributed_shopping_cart()
    example_serialization()
