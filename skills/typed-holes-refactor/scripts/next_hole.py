#!/usr/bin/env python3
"""
Show next resolvable holes based on dependency graph

A hole is resolvable when all its dependencies are resolved.
"""

import argparse
import re
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass
class Hole:
    id: str
    type: str
    question: str
    dependencies: List[str]
    status: str


def parse_refactor_ir(ir_path: Path) -> Dict[str, Hole]:
    """Parse REFACTOR_IR.md to extract holes"""
    content = ir_path.read_text()
    holes = {}
    
    # Extract hole sections
    hole_pattern = r'#### (H\d+|R\d+).*?\n\*\*Question\*\*: (.*?)\n\*\*Dependencies\*\*: (.*?)\n\*\*Status\*\*: (.*?)\n'
    
    for match in re.finditer(hole_pattern, content, re.DOTALL):
        hole_id = match.group(1)
        question = match.group(2).strip()
        deps_str = match.group(3).strip()
        status = match.group(4).strip()
        
        dependencies = []
        if deps_str and deps_str.lower() != 'none':
            dependencies = [d.strip() for d in deps_str.split(',')]
        
        # Infer type from ID
        if hole_id.startswith('H'):
            hole_type = "current_state"
        elif hole_id.startswith('R'):
            hole_type = "refactor"
        else:
            hole_type = "unknown"
        
        holes[hole_id] = Hole(
            id=hole_id,
            type=hole_type,
            question=question,
            dependencies=dependencies,
            status=status
        )
    
    return holes


def get_resolvable_holes(holes: Dict[str, Hole]) -> List[Hole]:
    """Get holes that are ready to resolve"""
    resolvable = []
    
    for hole in holes.values():
        # Skip already resolved
        if hole.status.lower() in ['resolved', 'done']:
            continue
        
        # Check if all dependencies are resolved
        deps_resolved = all(
            holes.get(dep_id, Hole('', '', '', [], 'resolved')).status.lower() in ['resolved', 'done']
            for dep_id in hole.dependencies
        )
        
        if deps_resolved:
            resolvable.append(hole)
    
    return resolvable


def get_blocked_holes(holes: Dict[str, Hole]) -> List[Hole]:
    """Get holes that are blocked by dependencies"""
    blocked = []
    
    for hole in holes.values():
        if hole.status.lower() in ['resolved', 'done']:
            continue
        
        # Check if any dependencies are unresolved
        has_unresolved_deps = any(
            holes.get(dep_id, Hole('', '', '', [], 'pending')).status.lower() not in ['resolved', 'done']
            for dep_id in hole.dependencies
        )
        
        if has_unresolved_deps and hole.dependencies:
            blocked.append(hole)
    
    return blocked


def display_holes(resolvable: List[Hole], blocked: List[Hole], all_holes: Dict[str, Hole]):
    """Display holes in a readable format"""
    total = len(all_holes)
    resolved = sum(1 for h in all_holes.values() if h.status.lower() in ['resolved', 'done'])
    in_progress = sum(1 for h in all_holes.values() if h.status.lower() == 'in_progress')
    
    print("🎯 Typed Holes Refactor - Next Steps")
    print("=" * 60)
    print(f"\n📊 Progress: {resolved}/{total} resolved ({in_progress} in progress)")
    print()
    
    if resolvable:
        print("✅ READY TO RESOLVE (no blocking dependencies):")
        print()
        
        for hole in sorted(resolvable, key=lambda h: h.id):
            print(f"  {hole.id} [{hole.type}]")
            print(f"  ❓ {hole.question}")
            if hole.status.lower() == 'in_progress':
                print(f"  ⚠️  Status: IN PROGRESS")
            print()
        
        print(f"💡 Suggested next action:")
        print(f"   1. Pick a hole from above (suggest: {resolvable[0].id})")
        print(f"   2. Write tests first: tests/refactor/test_{resolvable[0].id.lower()}_*.py")
        print(f"   3. Implement resolution")
        print(f"   4. Validate: python scripts/validate_resolution.py {resolvable[0].id}")
        print(f"   5. Propagate: python scripts/propagate.py {resolvable[0].id}")
        print()
    else:
        print("🎉 No holes ready to resolve!")
        if blocked:
            print("   All remaining holes are blocked by dependencies.")
        else:
            print("   All holes are resolved! Run generate_report.py")
        print()
    
    if blocked:
        print("🔒 BLOCKED (waiting on dependencies):")
        print()
        
        for hole in sorted(blocked, key=lambda h: h.id):
            unresolved_deps = [
                dep for dep in hole.dependencies
                if all_holes.get(dep, Hole('', '', '', [], 'pending')).status.lower() not in ['resolved', 'done']
            ]
            
            print(f"  {hole.id} ← waiting on: {', '.join(unresolved_deps)}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Show next resolvable holes")
    parser.add_argument(
        "--ir",
        type=Path,
        default=Path("REFACTOR_IR.md"),
        help="Path to REFACTOR_IR.md"
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all holes including resolved"
    )
    
    args = parser.parse_args()
    
    if not args.ir.exists():
        print(f"❌ Error: {args.ir} not found")
        print("   Run: python scripts/discover_holes.py")
        return 1
    
    holes = parse_refactor_ir(args.ir)
    resolvable = get_resolvable_holes(holes)
    blocked = get_blocked_holes(holes)
    
    display_holes(resolvable, blocked, holes)
    
    if args.show_all:
        resolved = [h for h in holes.values() if h.status.lower() in ['resolved', 'done']]
        if resolved:
            print("✅ RESOLVED:")
            print()
            for hole in sorted(resolved, key=lambda h: h.id):
                print(f"  {hole.id} - {hole.question}")
            print()
    
    return 0


if __name__ == "__main__":
    exit(main())
