#!/usr/bin/env python3
"""
CRDT Convergence Visualization

Generates diagrams showing how CRDT replicas converge over time with
different network topologies and operation patterns.

Outputs:
- ASCII diagrams (terminal)
- Mermaid diagrams (markdown)
- DOT graphs (Graphviz)
- JSON data for external visualization
"""

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from typing import List, Set, Dict, Tuple, Optional


# =============================================================================
# Simple CRDT Implementations
# =============================================================================

class GCounter:
    """G-Counter for visualization"""

    def __init__(self, n_replicas: int, replica_id: int):
        self.payload = [0] * n_replicas
        self.replica_id = replica_id
        self.n_replicas = n_replicas

    def increment(self, amount: int = 1):
        self.payload[self.replica_id] += amount

    def value(self) -> int:
        return sum(self.payload)

    def merge(self, other: "GCounter"):
        for i in range(self.n_replicas):
            self.payload[i] = max(self.payload[i], other.payload[i])

    def state_str(self) -> str:
        return f"[{','.join(map(str, self.payload))}]={self.value()}"

    def copy(self) -> "GCounter":
        c = GCounter(self.n_replicas, self.replica_id)
        c.payload = self.payload[:]
        return c


class ORSet:
    """OR-Set for visualization"""

    def __init__(self, replica_id: int):
        self.payload: Set[Tuple[str, int, int]] = set()
        self.replica_id = replica_id
        self.clock = 0

    def add(self, element: str):
        self.clock += 1
        self.payload.add((element, self.replica_id, self.clock))

    def remove(self, element: str):
        self.payload = {t for t in self.payload if t[0] != element}

    def elements(self) -> Set[str]:
        return {t[0] for t in self.payload}

    def merge(self, other: "ORSet"):
        self.payload |= other.payload
        self.clock = max(self.clock, other.clock)

    def state_str(self) -> str:
        elems = sorted(self.elements())
        return f"{{{','.join(elems)}}}"

    def copy(self) -> "ORSet":
        c = ORSet(self.replica_id)
        c.payload = self.payload.copy()
        c.clock = self.clock
        return c


# =============================================================================
# Convergence Simulation
# =============================================================================

@dataclass
class Event:
    """Event in the convergence timeline"""
    time: int
    replica: int
    event_type: str  # "operation" or "merge"
    description: str
    state_before: str
    state_after: str
    merge_target: Optional[int] = None


class ConvergenceSimulation:
    """Simulate CRDT convergence with network delays"""

    def __init__(self, crdt_type: str, n_replicas: int):
        self.crdt_type = crdt_type
        self.n_replicas = n_replicas
        self.time = 0
        self.events: List[Event] = []

        # Create replicas
        if crdt_type == "g-counter":
            self.replicas = [GCounter(n_replicas, i) for i in range(n_replicas)]
        elif crdt_type == "or-set":
            self.replicas = [ORSet(i) for i in range(n_replicas)]
        else:
            raise ValueError(f"Unknown CRDT type: {crdt_type}")

    def operation(self, replica_id: int, op_type: str, **kwargs):
        """Apply operation to replica"""
        replica = self.replicas[replica_id]
        state_before = replica.state_str()

        if self.crdt_type == "g-counter":
            if op_type == "increment":
                replica.increment(kwargs.get("amount", 1))
                desc = f"R{replica_id} increment({kwargs.get('amount', 1)})"
        elif self.crdt_type == "or-set":
            if op_type == "add":
                replica.add(kwargs["element"])
                desc = f"R{replica_id} add('{kwargs['element']}')"
            elif op_type == "remove":
                replica.remove(kwargs["element"])
                desc = f"R{replica_id} remove('{kwargs['element']}')"

        state_after = replica.state_str()

        self.events.append(Event(
            time=self.time,
            replica=replica_id,
            event_type="operation",
            description=desc,
            state_before=state_before,
            state_after=state_after
        ))

        self.time += 1

    def merge(self, replica1_id: int, replica2_id: int):
        """Merge replica2 into replica1"""
        r1 = self.replicas[replica1_id]
        r2 = self.replicas[replica2_id]

        state_before = r1.state_str()
        r1.merge(r2)
        state_after = r1.state_str()

        self.events.append(Event(
            time=self.time,
            replica=replica1_id,
            event_type="merge",
            description=f"R{replica1_id} ← R{replica2_id}",
            state_before=state_before,
            state_after=state_after,
            merge_target=replica2_id
        ))

        self.time += 1

    def get_states(self) -> List[str]:
        """Get current state of all replicas"""
        return [r.state_str() for r in self.replicas]

    def converged(self) -> bool:
        """Check if all replicas have converged"""
        states = self.get_states()
        return len(set(states)) == 1


# =============================================================================
# Visualization Generators
# =============================================================================

class ASCIIVisualizer:
    """Generate ASCII diagram of convergence"""

    @staticmethod
    def generate(sim: ConvergenceSimulation) -> str:
        """Generate ASCII timeline"""
        lines = []
        lines.append(f"CRDT Convergence Timeline: {sim.crdt_type.upper()}")
        lines.append("=" * 70)
        lines.append("")

        for event in sim.events:
            time_str = f"[T{event.time:02d}]"
            if event.event_type == "operation":
                lines.append(f"{time_str} {event.description}")
                lines.append(f"       {event.state_before} → {event.state_after}")
            else:
                lines.append(f"{time_str} MERGE: {event.description}")
                lines.append(f"       {event.state_before} → {event.state_after}")
            lines.append("")

        lines.append("Final States:")
        lines.append("-" * 70)
        for i, state in enumerate(sim.get_states()):
            lines.append(f"  Replica {i}: {state}")

        converged = sim.converged()
        lines.append("")
        lines.append(f"Converged: {converged}")

        return "\n".join(lines)


class MermaidVisualizer:
    """Generate Mermaid diagram"""

    @staticmethod
    def generate(sim: ConvergenceSimulation) -> str:
        """Generate Mermaid sequence diagram"""
        lines = []
        lines.append("```mermaid")
        lines.append("sequenceDiagram")
        lines.append("    autonumber")

        # Participants
        for i in range(sim.n_replicas):
            lines.append(f"    participant R{i} as Replica {i}")
        lines.append("")

        # Events
        for event in sim.events:
            if event.event_type == "operation":
                lines.append(f"    R{event.replica}->>R{event.replica}: {event.description}")
                lines.append(f"    Note right of R{event.replica}: {event.state_after}")
            else:
                lines.append(f"    R{event.merge_target}->>R{event.replica}: sync")
                lines.append(f"    Note right of R{event.replica}: {event.state_after}")

        lines.append("```")
        return "\n".join(lines)


class GraphvizVisualizer:
    """Generate Graphviz DOT diagram"""

    @staticmethod
    def generate(sim: ConvergenceSimulation) -> str:
        """Generate DOT graph showing merge topology"""
        lines = []
        lines.append("digraph convergence {")
        lines.append("    rankdir=LR;")
        lines.append("    node [shape=box, style=rounded];")
        lines.append("")

        # Create nodes for each time step and replica
        time_steps = {}
        for event in sim.events:
            if event.time not in time_steps:
                time_steps[event.time] = {}

            node_id = f"R{event.replica}_T{event.time}"
            label = f"R{event.replica}\\nT{event.time}\\n{event.state_after}"

            if event.event_type == "operation":
                color = "lightblue"
            else:
                color = "lightgreen"

            lines.append(f'    {node_id} [label="{label}", fillcolor={color}, style=filled];')

            time_steps[event.time][event.replica] = node_id

        lines.append("")

        # Add edges for operations and merges
        prev_states = {i: None for i in range(sim.n_replicas)}

        for event in sim.events:
            node_id = f"R{event.replica}_T{event.time}"

            # Edge from previous state
            if prev_states[event.replica] is not None:
                if event.event_type == "operation":
                    lines.append(f'    {prev_states[event.replica]} -> {node_id} [label="op"];')
                else:
                    lines.append(f'    {prev_states[event.replica]} -> {node_id} [label="merge"];')

            # Edge from merge source
            if event.event_type == "merge" and event.merge_target is not None:
                merge_source = prev_states[event.merge_target]
                if merge_source is not None:
                    lines.append(f'    {merge_source} -> {node_id} [style=dashed, color=red];')

            prev_states[event.replica] = node_id

        lines.append("}")
        return "\n".join(lines)


# =============================================================================
# Predefined Scenarios
# =============================================================================

def scenario_linear_convergence(sim: ConvergenceSimulation):
    """Linear merge topology: R0 → R1 → R2"""
    print("Scenario: Linear convergence (chain topology)")
    print("Topology: R0 → R1 → R2\n")

    # Operations on each replica
    if sim.crdt_type == "g-counter":
        sim.operation(0, "increment", amount=5)
        sim.operation(1, "increment", amount=3)
        sim.operation(2, "increment", amount=7)

        # Linear merge
        sim.merge(1, 0)  # R1 ← R0
        sim.merge(2, 1)  # R2 ← R1
        sim.merge(0, 2)  # R0 ← R2

    elif sim.crdt_type == "or-set":
        sim.operation(0, "add", element="a")
        sim.operation(1, "add", element="b")
        sim.operation(2, "add", element="c")

        sim.merge(1, 0)
        sim.merge(2, 1)
        sim.merge(0, 2)


def scenario_star_convergence(sim: ConvergenceSimulation):
    """Star topology: all replicas merge to R0"""
    print("Scenario: Star convergence (hub topology)")
    print("Topology: R1,R2 → R0\n")

    # Operations
    if sim.crdt_type == "g-counter":
        sim.operation(0, "increment", amount=2)
        sim.operation(1, "increment", amount=4)
        sim.operation(2, "increment", amount=6)

        # Star merge to R0
        sim.merge(0, 1)
        sim.merge(0, 2)

        # Propagate back
        sim.merge(1, 0)
        sim.merge(2, 0)

    elif sim.crdt_type == "or-set":
        sim.operation(0, "add", element="x")
        sim.operation(1, "add", element="y")
        sim.operation(2, "add", element="z")

        sim.merge(0, 1)
        sim.merge(0, 2)
        sim.merge(1, 0)
        sim.merge(2, 0)


def scenario_concurrent_add_remove(sim: ConvergenceSimulation):
    """Concurrent add and remove operations"""
    if sim.crdt_type != "or-set":
        print("Skipping: scenario only for OR-Set")
        return

    print("Scenario: Concurrent add/remove (add-wins semantics)")
    print("Topology: Concurrent ops then merge\n")

    # R0 and R1 both add "x"
    sim.operation(0, "add", element="x")
    sim.operation(1, "add", element="x")

    # R0 removes "x" (only observes its own add)
    sim.operation(0, "remove", element="x")

    # R1 adds more elements
    sim.operation(1, "add", element="y")

    # Merge
    sim.merge(0, 1)  # R1's "x" survives (add-wins)
    sim.merge(1, 0)


def scenario_partition_heal(sim: ConvergenceSimulation):
    """Network partition then heal"""
    print("Scenario: Network partition then heal")
    print("Topology: (R0,R1) | (R2) partition, then merge\n")

    # Partition 1: R0, R1
    if sim.crdt_type == "g-counter":
        sim.operation(0, "increment", amount=3)
        sim.operation(1, "increment", amount=2)
        sim.merge(0, 1)
        sim.merge(1, 0)

        # Partition 2: R2
        sim.operation(2, "increment", amount=8)

        # Heal: merge partitions
        sim.merge(0, 2)
        sim.merge(1, 0)
        sim.merge(2, 1)

    elif sim.crdt_type == "or-set":
        sim.operation(0, "add", element="a")
        sim.operation(1, "add", element="b")
        sim.merge(0, 1)
        sim.merge(1, 0)

        sim.operation(2, "add", element="c")

        sim.merge(0, 2)
        sim.merge(1, 0)
        sim.merge(2, 1)


# =============================================================================
# Main CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Visualize CRDT convergence with different network topologies"
    )
    parser.add_argument(
        "crdt_type",
        choices=["g-counter", "or-set"],
        help="Type of CRDT to visualize"
    )
    parser.add_argument(
        "--scenario", "-s",
        choices=["linear", "star", "concurrent", "partition"],
        default="linear",
        help="Convergence scenario"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["ascii", "mermaid", "dot", "json", "all"],
        default="ascii",
        help="Output format"
    )
    parser.add_argument(
        "--replicas", "-n",
        type=int,
        default=3,
        help="Number of replicas (default: 3)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file (stdout if not specified)"
    )

    args = parser.parse_args()

    # Create simulation
    sim = ConvergenceSimulation(args.crdt_type, args.replicas)

    # Run scenario
    try:
        if args.scenario == "linear":
            scenario_linear_convergence(sim)
        elif args.scenario == "star":
            scenario_star_convergence(sim)
        elif args.scenario == "concurrent":
            scenario_concurrent_add_remove(sim)
        elif args.scenario == "partition":
            scenario_partition_heal(sim)

    except Exception as e:
        print(f"Error running scenario: {e}", file=sys.stderr)
        return 1

    # Generate output
    outputs = {}

    if args.format in ["ascii", "all"]:
        outputs["ascii"] = ASCIIVisualizer.generate(sim)

    if args.format in ["mermaid", "all"]:
        outputs["mermaid"] = MermaidVisualizer.generate(sim)

    if args.format in ["dot", "all"]:
        outputs["dot"] = GraphvizVisualizer.generate(sim)

    if args.format in ["json", "all"]:
        outputs["json"] = json.dumps({
            "crdt_type": sim.crdt_type,
            "n_replicas": sim.n_replicas,
            "scenario": args.scenario,
            "events": [
                {
                    "time": e.time,
                    "replica": e.replica,
                    "event_type": e.event_type,
                    "description": e.description,
                    "state_before": e.state_before,
                    "state_after": e.state_after,
                    "merge_target": e.merge_target
                }
                for e in sim.events
            ],
            "final_states": sim.get_states(),
            "converged": sim.converged()
        }, indent=2)

    # Output
    if args.output:
        with open(args.output, 'w') as f:
            if args.format == "all":
                f.write("# CRDT Convergence Visualization\n\n")
                f.write("## ASCII Timeline\n\n")
                f.write(outputs["ascii"])
                f.write("\n\n## Mermaid Diagram\n\n")
                f.write(outputs["mermaid"])
                f.write("\n\n## Graphviz DOT\n\n")
                f.write("```dot\n")
                f.write(outputs["dot"])
                f.write("\n```\n")
                f.write("\n\n## JSON Data\n\n")
                f.write("```json\n")
                f.write(outputs["json"])
                f.write("\n```\n")
            else:
                f.write(outputs[args.format])
        print(f"Output written to {args.output}")
    else:
        if args.format == "all":
            print("\n" + "="*70)
            print("ASCII Timeline")
            print("="*70 + "\n")
            print(outputs["ascii"])
            print("\n" + "="*70)
            print("Mermaid Diagram")
            print("="*70 + "\n")
            print(outputs["mermaid"])
            print("\n" + "="*70)
            print("Graphviz DOT")
            print("="*70 + "\n")
            print(outputs["dot"])
            print("\n" + "="*70)
            print("JSON Data")
            print("="*70 + "\n")
            print(outputs["json"])
        else:
            print(outputs[args.format])

    return 0


if __name__ == "__main__":
    sys.exit(main())
