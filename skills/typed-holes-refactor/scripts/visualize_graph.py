#!/usr/bin/env python3
"""
Visualize Hole Dependency Graph

Generates visual representations of hole dependencies to identify:
- Critical path
- Bottlenecks
- Parallel work opportunities
- Circular dependencies
"""

import argparse
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class Hole:
    id: str
    status: str
    dependencies: List[str]


class DependencyGraphVisualizer:
    def __init__(self, refactor_ir: Path):
        self.refactor_ir = refactor_ir
        self.holes: Dict[str, Hole] = {}

    def parse_ir(self):
        """Parse REFACTOR_IR.md to extract holes and dependencies"""
        if not self.refactor_ir.exists():
            print(f"❌ REFACTOR_IR.md not found at {self.refactor_ir}")
            return

        content = self.refactor_ir.read_text()

        # Extract holes with their status and dependencies
        hole_sections = re.split(r'####\s+([HRM]\d+_\w+)', content)[1:]

        for i in range(0, len(hole_sections), 2):
            if i + 1 >= len(hole_sections):
                break

            hole_id = hole_sections[i]
            hole_content = hole_sections[i + 1]

            # Extract status
            status_match = re.search(r'\*\*Status\*\*:\s*(\w+)', hole_content)
            status = status_match.group(1) if status_match else 'pending'

            # Extract dependencies
            deps_match = re.search(r'\*\*Dependencies\*\*:\s*(.+?)(?:\n|$)', hole_content)
            dependencies = []
            if deps_match:
                deps_text = deps_match.group(1)
                if deps_text.lower() not in ['none', 'n/a', '']:
                    # Parse comma-separated or bracket-enclosed dependencies
                    deps = re.findall(r'([HRM]\d+_\w+)', deps_text)
                    dependencies = deps

            self.holes[hole_id] = Hole(hole_id, status.lower(), dependencies)

    def generate_mermaid(self) -> str:
        """Generate Mermaid diagram syntax"""
        lines = ["```mermaid", "graph TD"]

        # Style definitions
        lines.append("  classDef resolved fill:#90EE90")
        lines.append("  classDef inProgress fill:#FFD700")
        lines.append("  classDef pending fill:#FFB6C1")
        lines.append("  classDef blocked fill:#D3D3D3")
        lines.append("")

        # Add nodes with labels
        for hole_id, hole in self.holes.items():
            # Simplify label
            label = hole_id.replace('_', ' ')

            # Determine class based on status
            if hole.status in ['resolved', 'complete', 'done']:
                class_name = "resolved"
                symbol = "✓"
            elif hole.status in ['in_progress', 'active', 'working']:
                class_name = "inProgress"
                symbol = "⋯"
            elif hole.dependencies and not self._deps_resolved(hole):
                class_name = "blocked"
                symbol = "⊗"
            else:
                class_name = "pending"
                symbol = "○"

            lines.append(f"  {hole_id}[\"{symbol} {label}\"]:::{class_name}")

        lines.append("")

        # Add edges
        for hole_id, hole in self.holes.items():
            for dep_id in hole.dependencies:
                if dep_id in self.holes:
                    lines.append(f"  {dep_id} --> {hole_id}")

        lines.append("```")
        return "\n".join(lines)

    def generate_ascii(self) -> str:
        """Generate ASCII art dependency graph"""
        lines = ["=" * 70, "  HOLE DEPENDENCY GRAPH", "=" * 70, ""]

        # Group by layer (depth in dependency tree)
        layers = self._compute_layers()

        for layer_num in sorted(layers.keys()):
            layer_holes = layers[layer_num]
            lines.append(f"\nLayer {layer_num}:")
            lines.append("-" * 70)

            for hole_id in layer_holes:
                hole = self.holes[hole_id]
                status_symbol = self._get_status_symbol(hole)

                # Show hole with dependencies
                deps_str = ", ".join(hole.dependencies) if hole.dependencies else "none"
                lines.append(f"  {status_symbol} {hole_id}")
                if hole.dependencies:
                    lines.append(f"      ↑ depends on: {deps_str}")

        lines.append("\n" + "=" * 70)

        # Legend
        lines.append("\nLegend:")
        lines.append("  ✓ Resolved")
        lines.append("  ⋯ In Progress")
        lines.append("  ⊗ Blocked (waiting on dependencies)")
        lines.append("  ○ Pending (ready to start)")

        return "\n".join(lines)

    def generate_dot(self) -> str:
        """Generate Graphviz DOT format"""
        lines = ["digraph HoleDependencies {", "  rankdir=TB;", "  node [shape=box];", ""]

        # Add nodes
        for hole_id, hole in self.holes.items():
            label = hole_id.replace('_', '\\n')

            if hole.status in ['resolved', 'complete', 'done']:
                color = "lightgreen"
            elif hole.status in ['in_progress', 'active', 'working']:
                color = "gold"
            elif hole.dependencies and not self._deps_resolved(hole):
                color = "lightgray"
            else:
                color = "lightpink"

            lines.append(f'  {hole_id} [label="{label}", style=filled, fillcolor={color}];')

        lines.append("")

        # Add edges
        for hole_id, hole in self.holes.items():
            for dep_id in hole.dependencies:
                if dep_id in self.holes:
                    lines.append(f"  {dep_id} -> {hole_id};")

        lines.append("}")
        return "\n".join(lines)

    def identify_critical_path(self) -> List[str]:
        """Find the longest path through the dependency graph"""
        # Compute depth for each hole
        depths = {}

        def compute_depth(hole_id: str) -> int:
            if hole_id in depths:
                return depths[hole_id]

            hole = self.holes.get(hole_id)
            if not hole or not hole.dependencies:
                depths[hole_id] = 0
                return 0

            max_dep_depth = max(
                (compute_depth(dep) for dep in hole.dependencies if dep in self.holes),
                default=-1
            )
            depths[hole_id] = max_dep_depth + 1
            return depths[hole_id]

        for hole_id in self.holes:
            compute_depth(hole_id)

        # Find hole with maximum depth
        if not depths:
            return []

        max_depth_hole = max(depths.items(), key=lambda x: x[1])
        return [max_depth_hole[0]]

    def identify_bottlenecks(self) -> List[str]:
        """Find holes that many others depend on"""
        dependents_count = {hole_id: 0 for hole_id in self.holes}

        for hole in self.holes.values():
            for dep_id in hole.dependencies:
                if dep_id in dependents_count:
                    dependents_count[dep_id] += 1

        # Return holes with 3+ dependents
        bottlenecks = [
            hole_id for hole_id, count in dependents_count.items()
            if count >= 3
        ]
        return bottlenecks

    def identify_parallel_work(self) -> List[List[str]]:
        """Find holes that can be worked on in parallel"""
        # Find all ready holes (no pending dependencies)
        ready = []
        for hole_id, hole in self.holes.items():
            if hole.status not in ['resolved', 'complete', 'done']:
                if self._deps_resolved(hole):
                    ready.append(hole_id)

        # Group by layer
        layers = self._compute_layers()
        parallel_groups = []

        for layer_num in sorted(layers.keys()):
            layer_holes = [h for h in layers[layer_num] if h in ready]
            if len(layer_holes) > 1:
                parallel_groups.append(layer_holes)

        return parallel_groups

    def _deps_resolved(self, hole: Hole) -> bool:
        """Check if all dependencies are resolved"""
        for dep_id in hole.dependencies:
            if dep_id not in self.holes:
                continue
            dep = self.holes[dep_id]
            if dep.status not in ['resolved', 'complete', 'done']:
                return False
        return True

    def _get_status_symbol(self, hole: Hole) -> str:
        """Get visual symbol for hole status"""
        if hole.status in ['resolved', 'complete', 'done']:
            return "✓"
        elif hole.status in ['in_progress', 'active', 'working']:
            return "⋯"
        elif hole.dependencies and not self._deps_resolved(hole):
            return "⊗"
        else:
            return "○"

    def _compute_layers(self) -> Dict[int, List[str]]:
        """Compute depth layers for topological ordering"""
        layers = {}

        def compute_layer(hole_id: str, visited: Set[str]) -> int:
            if hole_id in visited:
                # Circular dependency detected
                return 0

            hole = self.holes.get(hole_id)
            if not hole or not hole.dependencies:
                return 0

            visited.add(hole_id)
            max_dep_layer = max(
                (compute_layer(dep, visited.copy()) for dep in hole.dependencies if dep in self.holes),
                default=-1
            )
            return max_dep_layer + 1

        for hole_id in self.holes:
            layer = compute_layer(hole_id, set())
            layers.setdefault(layer, []).append(hole_id)

        return layers


def main():
    parser = argparse.ArgumentParser(
        description="Visualize hole dependency graph"
    )
    parser.add_argument(
        "--ir",
        type=Path,
        default=Path("REFACTOR_IR.md"),
        help="Path to REFACTOR_IR.md"
    )
    parser.add_argument(
        "--format",
        choices=["ascii", "mermaid", "dot"],
        default="ascii",
        help="Output format (ascii, mermaid, or dot)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file (default: stdout)"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Show critical path and bottleneck analysis"
    )

    args = parser.parse_args()

    visualizer = DependencyGraphVisualizer(args.ir)
    visualizer.parse_ir()

    if not visualizer.holes:
        print("No holes found in REFACTOR_IR.md")
        return

    # Generate visualization
    if args.format == "mermaid":
        output = visualizer.generate_mermaid()
    elif args.format == "dot":
        output = visualizer.generate_dot()
    else:
        output = visualizer.generate_ascii()

    # Output
    if args.output:
        args.output.write_text(output)
        print(f"✅ Graph written to {args.output}")
    else:
        print(output)

    # Analysis
    if args.analyze:
        print("\n" + "=" * 70)
        print("  DEPENDENCY ANALYSIS")
        print("=" * 70)

        critical_path = visualizer.identify_critical_path()
        if critical_path:
            print(f"\n🎯 Critical Path (longest chain):")
            for hole_id in critical_path:
                print(f"  • {hole_id}")

        bottlenecks = visualizer.identify_bottlenecks()
        if bottlenecks:
            print(f"\n⚠️  Bottlenecks (3+ dependents):")
            for hole_id in bottlenecks:
                print(f"  • {hole_id}")

        parallel = visualizer.identify_parallel_work()
        if parallel:
            print(f"\n🔀 Parallel Work Opportunities:")
            for i, group in enumerate(parallel, 1):
                print(f"  Group {i}: {', '.join(group)}")
        else:
            print(f"\n✓ No parallel work available (linear dependencies)")


if __name__ == "__main__":
    main()
