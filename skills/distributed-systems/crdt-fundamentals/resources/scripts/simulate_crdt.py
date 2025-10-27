#!/usr/bin/env python3
"""
CRDT Simulation Script

Simulates different CRDT types with concurrent operations to demonstrate
convergence properties and conflict resolution.

Supports:
- G-Counter: Grow-only counter
- PN-Counter: Positive-negative counter
- OR-Set: Observed-remove set
- LWW-Set: Last-write-wins set
- RGA: Replicated growable array (text)
"""

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple


# =============================================================================
# G-Counter Implementation
# =============================================================================

class GCounter:
    """Grow-only counter CRDT"""

    def __init__(self, n_replicas: int, replica_id: int):
        self.n_replicas = n_replicas
        self.replica_id = replica_id
        self.payload = [0] * n_replicas

    def increment(self, amount: int = 1):
        """Increment counter for this replica"""
        self.payload[self.replica_id] += amount

    def value(self) -> int:
        """Get current counter value"""
        return sum(self.payload)

    def merge(self, other: "GCounter"):
        """Merge with another replica"""
        for i in range(self.n_replicas):
            self.payload[i] = max(self.payload[i], other.payload[i])

    def state_dict(self) -> Dict:
        """Get state as dictionary"""
        return {
            "type": "G-Counter",
            "replica_id": self.replica_id,
            "payload": self.payload,
            "value": self.value()
        }


# =============================================================================
# PN-Counter Implementation
# =============================================================================

class PNCounter:
    """Positive-negative counter CRDT"""

    def __init__(self, n_replicas: int, replica_id: int):
        self.n_replicas = n_replicas
        self.replica_id = replica_id
        self.positive = [0] * n_replicas
        self.negative = [0] * n_replicas

    def increment(self, amount: int = 1):
        """Increment counter"""
        self.positive[self.replica_id] += amount

    def decrement(self, amount: int = 1):
        """Decrement counter"""
        self.negative[self.replica_id] += amount

    def value(self) -> int:
        """Get current counter value"""
        return sum(self.positive) - sum(self.negative)

    def merge(self, other: "PNCounter"):
        """Merge with another replica"""
        for i in range(self.n_replicas):
            self.positive[i] = max(self.positive[i], other.positive[i])
            self.negative[i] = max(self.negative[i], other.negative[i])

    def state_dict(self) -> Dict:
        """Get state as dictionary"""
        return {
            "type": "PN-Counter",
            "replica_id": self.replica_id,
            "positive": self.positive,
            "negative": self.negative,
            "value": self.value()
        }


# =============================================================================
# OR-Set Implementation
# =============================================================================

@dataclass(frozen=True)
class ORSetElement:
    """Element in OR-Set with unique tag"""
    value: Any
    replica_id: int
    timestamp: int


class ORSet:
    """Observed-remove set CRDT"""

    def __init__(self, replica_id: int):
        self.replica_id = replica_id
        self.payload: Set[ORSetElement] = set()
        self.clock = 0

    def add(self, element: Any):
        """Add element to set"""
        self.clock += 1
        tag = ORSetElement(element, self.replica_id, self.clock)
        self.payload.add(tag)
        return tag

    def remove(self, element: Any):
        """Remove all observed instances of element"""
        to_remove = {tag for tag in self.payload if tag.value == element}
        self.payload -= to_remove
        return to_remove

    def contains(self, element: Any) -> bool:
        """Check if element is in set"""
        return any(tag.value == element for tag in self.payload)

    def elements(self) -> Set[Any]:
        """Get set of unique elements"""
        return {tag.value for tag in self.payload}

    def merge(self, other: "ORSet"):
        """Merge with another replica"""
        self.payload |= other.payload
        self.clock = max(self.clock, other.clock)

    def state_dict(self) -> Dict:
        """Get state as dictionary"""
        return {
            "type": "OR-Set",
            "replica_id": self.replica_id,
            "payload": [
                {"value": tag.value, "replica": tag.replica_id, "ts": tag.timestamp}
                for tag in sorted(self.payload, key=lambda t: (t.value, t.timestamp))
            ],
            "elements": sorted(list(self.elements()))
        }


# =============================================================================
# LWW-Set Implementation
# =============================================================================

class LWWSet:
    """Last-write-wins set CRDT"""

    def __init__(self, replica_id: int):
        self.replica_id = replica_id
        self.added: Dict[Any, int] = {}
        self.removed: Dict[Any, int] = {}
        self.clock = 0

    def add(self, element: Any, timestamp: int = None):
        """Add element with timestamp"""
        if timestamp is None:
            self.clock += 1
            timestamp = self.clock
        self.added[element] = max(self.added.get(element, 0), timestamp)

    def remove(self, element: Any, timestamp: int = None):
        """Remove element with timestamp"""
        if timestamp is None:
            self.clock += 1
            timestamp = self.clock
        self.removed[element] = max(self.removed.get(element, 0), timestamp)

    def contains(self, element: Any) -> bool:
        """Check if element is in set (add-bias)"""
        add_ts = self.added.get(element, 0)
        rem_ts = self.removed.get(element, 0)
        return add_ts > rem_ts  # Add wins on tie

    def elements(self) -> Set[Any]:
        """Get all elements in set"""
        return {e for e in self.added if self.contains(e)}

    def merge(self, other: "LWWSet"):
        """Merge with another replica"""
        for e, ts in other.added.items():
            self.added[e] = max(self.added.get(e, 0), ts)
        for e, ts in other.removed.items():
            self.removed[e] = max(self.removed.get(e, 0), ts)
        self.clock = max(self.clock, other.clock)

    def state_dict(self) -> Dict:
        """Get state as dictionary"""
        return {
            "type": "LWW-Set",
            "replica_id": self.replica_id,
            "added": self.added,
            "removed": self.removed,
            "elements": sorted(list(self.elements()))
        }


# =============================================================================
# RGA (Replicated Growable Array) Implementation
# =============================================================================

@dataclass
class RGANode:
    """Node in RGA linked list"""
    id: Tuple[int, int]  # (replica_id, seq_num)
    value: str
    timestamp: int
    tombstone: bool = False
    next_node: "RGANode" = None


class RGA:
    """Replicated growable array for text editing"""

    def __init__(self, replica_id: int):
        self.replica_id = replica_id
        self.seq_num = 0
        # Head sentinel
        self.head = RGANode((-1, -1), "", -1)
        self.nodes: Dict[Tuple[int, int], RGANode] = {self.head.id: self.head}

    def insert(self, value: str, after_id: Tuple[int, int], timestamp: int = None):
        """Insert character after specified node"""
        if timestamp is None:
            timestamp = time.time_ns()

        self.seq_num += 1
        new_id = (self.replica_id, self.seq_num)
        new_node = RGANode(new_id, value, timestamp)
        self.nodes[new_id] = new_node

        # Find insertion point
        prev = self.nodes[after_id]

        # Find correct position among concurrent inserts
        current = prev.next_node
        while current is not None:
            # Compare timestamps, then IDs for deterministic order
            if (current.timestamp < timestamp or
                (current.timestamp == timestamp and current.id < new_id)):
                break
            prev = current
            current = current.next_node

        # Insert
        new_node.next_node = prev.next_node
        prev.next_node = new_node

        return new_id

    def delete(self, node_id: Tuple[int, int]):
        """Delete node (mark as tombstone)"""
        if node_id in self.nodes:
            self.nodes[node_id].tombstone = True

    def to_string(self) -> str:
        """Convert to string"""
        result = []
        node = self.head.next_node
        while node is not None:
            if not node.tombstone:
                result.append(node.value)
            node = node.next_node
        return ''.join(result)

    def merge(self, other: "RGA"):
        """Merge with another replica"""
        # Merge all nodes
        for node_id, node in other.nodes.items():
            if node_id not in self.nodes:
                # Add new node
                new_node = RGANode(
                    node.id,
                    node.value,
                    node.timestamp,
                    node.tombstone
                )
                self.nodes[node_id] = new_node

                # Find insertion point
                if node_id == (-1, -1):  # Skip head
                    continue

                # Rebuild links based on timestamps
                self._rebuild_links()
            else:
                # Update tombstone status
                if node.tombstone:
                    self.nodes[node_id].tombstone = True

        self.seq_num = max(self.seq_num, other.seq_num)

    def _rebuild_links(self):
        """Rebuild linked list based on timestamps"""
        # Sort all nodes (except head) by timestamp, then ID
        nodes = [n for n in self.nodes.values() if n.id != (-1, -1)]
        nodes.sort(key=lambda n: (n.timestamp, n.id))

        # Rebuild links
        self.head.next_node = nodes[0] if nodes else None
        for i in range(len(nodes) - 1):
            nodes[i].next_node = nodes[i + 1]
        if nodes:
            nodes[-1].next_node = None

    def state_dict(self) -> Dict:
        """Get state as dictionary"""
        nodes = []
        node = self.head.next_node
        while node is not None:
            nodes.append({
                "id": node.id,
                "value": node.value,
                "timestamp": node.timestamp,
                "tombstone": node.tombstone
            })
            node = node.next_node

        return {
            "type": "RGA",
            "replica_id": self.replica_id,
            "nodes": nodes,
            "text": self.to_string()
        }


# =============================================================================
# Simulation Engine
# =============================================================================

class CRDTSimulation:
    """Simulate CRDT with concurrent operations"""

    def __init__(self, crdt_type: str, n_replicas: int):
        self.crdt_type = crdt_type
        self.n_replicas = n_replicas
        self.replicas = []
        self.operations = []
        self.merge_history = []

        # Create replicas
        for i in range(n_replicas):
            if crdt_type == "g-counter":
                self.replicas.append(GCounter(n_replicas, i))
            elif crdt_type == "pn-counter":
                self.replicas.append(PNCounter(n_replicas, i))
            elif crdt_type == "or-set":
                self.replicas.append(ORSet(i))
            elif crdt_type == "lww-set":
                self.replicas.append(LWWSet(i))
            elif crdt_type == "rga":
                self.replicas.append(RGA(i))
            else:
                raise ValueError(f"Unknown CRDT type: {crdt_type}")

    def apply_operation(self, replica_id: int, operation: Dict):
        """Apply operation to specific replica"""
        replica = self.replicas[replica_id]
        op_type = operation["type"]

        if self.crdt_type == "g-counter":
            if op_type == "increment":
                replica.increment(operation.get("amount", 1))

        elif self.crdt_type == "pn-counter":
            if op_type == "increment":
                replica.increment(operation.get("amount", 1))
            elif op_type == "decrement":
                replica.decrement(operation.get("amount", 1))

        elif self.crdt_type in ["or-set", "lww-set"]:
            if op_type == "add":
                replica.add(operation["element"])
            elif op_type == "remove":
                replica.remove(operation["element"])

        elif self.crdt_type == "rga":
            if op_type == "insert":
                after_id = operation.get("after_id", (-1, -1))
                replica.insert(operation["value"], after_id)
            elif op_type == "delete":
                replica.delete(operation["node_id"])

        self.operations.append({
            "replica": replica_id,
            "operation": operation,
            "timestamp": time.time()
        })

    def merge_replicas(self, replica1_id: int, replica2_id: int):
        """Merge two replicas"""
        r1 = self.replicas[replica1_id]
        r2 = self.replicas[replica2_id]

        r1.merge(r2)

        self.merge_history.append({
            "from": replica2_id,
            "to": replica1_id,
            "timestamp": time.time()
        })

    def merge_all(self):
        """Merge all replicas together"""
        for i in range(1, self.n_replicas):
            self.replicas[0].merge(self.replicas[i])
        for i in range(1, self.n_replicas):
            self.replicas[i].merge(self.replicas[0])

    def get_states(self) -> List[Dict]:
        """Get current state of all replicas"""
        return [replica.state_dict() for replica in self.replicas]

    def check_convergence(self) -> bool:
        """Check if all replicas have converged"""
        states = self.get_states()
        if not states:
            return True

        if self.crdt_type in ["g-counter", "pn-counter"]:
            values = [s["value"] for s in states]
            return len(set(values)) == 1

        elif self.crdt_type in ["or-set", "lww-set"]:
            element_sets = [set(s["elements"]) for s in states]
            return len(set(map(frozenset, element_sets))) == 1

        elif self.crdt_type == "rga":
            texts = [s["text"] for s in states]
            return len(set(texts)) == 1

        return False


# =============================================================================
# Predefined Scenarios
# =============================================================================

def scenario_counter_concurrent_increments(sim: CRDTSimulation):
    """Scenario: Concurrent increments on different replicas"""
    print("Scenario: Concurrent increments on 3 replicas")

    # Each replica increments independently
    sim.apply_operation(0, {"type": "increment", "amount": 5})
    sim.apply_operation(1, {"type": "increment", "amount": 3})
    sim.apply_operation(2, {"type": "increment", "amount": 7})

    print("\nBefore merge:")
    for i, state in enumerate(sim.get_states()):
        print(f"  Replica {i}: {state}")

    # Merge all
    sim.merge_all()

    print("\nAfter merge:")
    for i, state in enumerate(sim.get_states()):
        print(f"  Replica {i}: {state}")

    print(f"\nConverged: {sim.check_convergence()}")


def scenario_pn_counter_concurrent_ops(sim: CRDTSimulation):
    """Scenario: Concurrent increments and decrements"""
    print("Scenario: Concurrent increments and decrements")

    # Concurrent operations
    sim.apply_operation(0, {"type": "increment", "amount": 10})
    sim.apply_operation(1, {"type": "decrement", "amount": 3})
    sim.apply_operation(2, {"type": "increment", "amount": 5})
    sim.apply_operation(0, {"type": "decrement", "amount": 2})

    print("\nBefore merge:")
    for i, state in enumerate(sim.get_states()):
        print(f"  Replica {i}: {state}")

    sim.merge_all()

    print("\nAfter merge:")
    for i, state in enumerate(sim.get_states()):
        print(f"  Replica {i}: {state}")

    print(f"\nConverged: {sim.check_convergence()}")


def scenario_or_set_concurrent_add_remove(sim: CRDTSimulation):
    """Scenario: Concurrent add and remove on OR-Set"""
    print("Scenario: Concurrent add/remove on OR-Set")

    # Replica 0 and 1 both add "x"
    sim.apply_operation(0, {"type": "add", "element": "x"})
    sim.apply_operation(1, {"type": "add", "element": "x"})

    # Replica 0 removes "x" (only observes its own add)
    sim.apply_operation(0, {"type": "remove", "element": "x"})

    # Replica 1 adds "y" and "z"
    sim.apply_operation(1, {"type": "add", "element": "y"})
    sim.apply_operation(2, {"type": "add", "element": "z"})

    print("\nBefore merge:")
    for i, state in enumerate(sim.get_states()):
        print(f"  Replica {i}: {state}")

    sim.merge_all()

    print("\nAfter merge:")
    for i, state in enumerate(sim.get_states()):
        print(f"  Replica {i}: {state}")
    print("  Note: 'x' from replica 1 survives (add-wins semantics)")

    print(f"\nConverged: {sim.check_convergence()}")


def scenario_lww_set_timestamp_conflicts(sim: CRDTSimulation):
    """Scenario: LWW-Set with timestamp conflicts"""
    print("Scenario: LWW-Set with concurrent add/remove")

    # Add element on different replicas
    sim.apply_operation(0, {"type": "add", "element": "a"})
    time.sleep(0.01)

    # Concurrent remove and add
    sim.apply_operation(1, {"type": "remove", "element": "a"})
    sim.apply_operation(2, {"type": "add", "element": "a"})

    print("\nBefore merge:")
    for i, state in enumerate(sim.get_states()):
        print(f"  Replica {i}: {state}")

    sim.merge_all()

    print("\nAfter merge:")
    for i, state in enumerate(sim.get_states()):
        print(f"  Replica {i}: {state}")
    print("  Note: Highest timestamp wins")

    print(f"\nConverged: {sim.check_convergence()}")


def scenario_rga_text_editing(sim: CRDTSimulation):
    """Scenario: Concurrent text editing with RGA"""
    print("Scenario: Concurrent text editing")

    # Replica 0 types "Hello"
    ids = [sim.replicas[0].head.id]
    for char in "Hello":
        node_id = sim.replicas[0].insert(char, ids[-1])
        ids.append(node_id)

    # Replica 1 types "World" at beginning
    ids1 = [sim.replicas[1].head.id]
    for char in "World":
        node_id = sim.replicas[1].insert(char, ids1[-1])
        ids1.append(node_id)

    print("\nBefore merge:")
    for i, state in enumerate(sim.get_states()):
        print(f"  Replica {i}: text='{state['text']}'")

    sim.merge_all()

    print("\nAfter merge:")
    for i, state in enumerate(sim.get_states()):
        print(f"  Replica {i}: text='{state['text']}'")
    print("  Note: Deterministic merge based on timestamps")

    print(f"\nConverged: {sim.check_convergence()}")


# =============================================================================
# Main CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Simulate CRDT operations and demonstrate convergence"
    )
    parser.add_argument(
        "crdt_type",
        choices=["g-counter", "pn-counter", "or-set", "lww-set", "rga"],
        help="Type of CRDT to simulate"
    )
    parser.add_argument(
        "--replicas", "-n",
        type=int,
        default=3,
        help="Number of replicas (default: 3)"
    )
    parser.add_argument(
        "--scenario",
        choices=["concurrent-ops", "add-remove", "timestamp-conflict", "text-edit"],
        default="concurrent-ops",
        help="Predefined scenario to run"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Create simulation
    sim = CRDTSimulation(args.crdt_type, args.replicas)

    # Run scenario
    if not args.json:
        print(f"\n{'='*60}")
        print(f"CRDT Simulation: {args.crdt_type.upper()}")
        print(f"Replicas: {args.replicas}")
        print(f"{'='*60}\n")

    try:
        if args.crdt_type == "g-counter":
            scenario_counter_concurrent_increments(sim)
        elif args.crdt_type == "pn-counter":
            scenario_pn_counter_concurrent_ops(sim)
        elif args.crdt_type == "or-set":
            scenario_or_set_concurrent_add_remove(sim)
        elif args.crdt_type == "lww-set":
            scenario_lww_set_timestamp_conflicts(sim)
        elif args.crdt_type == "rga":
            scenario_rga_text_editing(sim)

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"\nError: {e}", file=sys.stderr)
        return 1

    # Output results
    if args.json:
        result = {
            "crdt_type": args.crdt_type,
            "n_replicas": args.replicas,
            "operations": sim.operations,
            "merge_history": sim.merge_history,
            "final_states": sim.get_states(),
            "converged": sim.check_convergence()
        }
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
