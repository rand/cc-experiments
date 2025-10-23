#!/usr/bin/env python3
"""
Propagate constraints from a resolved hole to dependent holes

Updates REFACTOR_IR.md with propagated constraints.
"""

import argparse
import re
from pathlib import Path


def propagate_constraints(hole_id: str, ir_path: Path):
    """Update dependent holes with propagated constraints"""
    
    print(f"🔄 Propagating constraints from {hole_id}")
    print("=" * 60)
    print()
    
    content = ir_path.read_text()
    
    # Find holes that depend on this one
    dependent_pattern = rf'#### (H\d+|R\d+).*?\n\*\*Dependencies\*\*: ([^\n]*{hole_id}[^\n]*)\n'
    
    dependents = []
    for match in re.finditer(dependent_pattern, content):
        dependent_id = match.group(1)
        dependents.append(dependent_id)
    
    if not dependents:
        print(f"No holes depend on {hole_id}")
        print("This is a leaf node in the dependency graph.")
        print()
        return
    
    print(f"Found {len(dependents)} dependent holes:")
    for dep in dependents:
        print(f"  • {dep}")
    print()
    
    print("Action items:")
    print(f"  1. Review resolution of {hole_id}")
    print(f"  2. For each dependent hole, update constraints based on resolution")
    print(f"  3. Update REFACTOR_IR.md with new constraints")
    print(f"  4. Run: python scripts/next_hole.py")
    print()
    
    print("Constraint propagation patterns to consider:")
    print()
    print("  • If {hole_id} resolved with specific types:")
    print("    → Update dependent holes with type requirements")
    print()
    print("  • If {hole_id} resolved with resource limits:")
    print("    → Update dependent holes with resource constraints")
    print()
    print("  • If {hole_id} resolved with testing needs:")
    print("    → Update dependent holes with test data requirements")
    print()
    print("See references/CONSTRAINT_RULES.md for complete propagation rules.")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Propagate constraints from resolved hole"
    )
    parser.add_argument(
        "hole_id",
        help="Resolved hole ID (e.g., H1, R4)"
    )
    parser.add_argument(
        "--ir",
        type=Path,
        default=Path("REFACTOR_IR.md"),
        help="Path to REFACTOR_IR.md"
    )
    
    args = parser.parse_args()
    
    if not args.ir.exists():
        print(f"❌ Error: {args.ir} not found")
        return 1
    
    propagate_constraints(args.hole_id, args.ir)
    return 0


if __name__ == "__main__":
    exit(main())
