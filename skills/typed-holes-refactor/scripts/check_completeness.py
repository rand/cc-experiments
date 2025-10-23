#!/usr/bin/env python3
"""
Check Overall Refactor Completeness

Provides a dashboard view of refactoring progress across all phases.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field


@dataclass
class HoleStatus:
    total: int = 0
    pending: int = 0
    in_progress: int = 0
    resolved: int = 0


@dataclass
class RefactorStatus:
    current_state: HoleStatus = field(default_factory=HoleStatus)
    architecture: HoleStatus = field(default_factory=HoleStatus)
    implementation: HoleStatus = field(default_factory=HoleStatus)
    quality: HoleStatus = field(default_factory=HoleStatus)
    migration: HoleStatus = field(default_factory=HoleStatus)

    @property
    def total_holes(self) -> int:
        return (self.current_state.total + self.architecture.total +
                self.implementation.total + self.quality.total +
                self.migration.total)

    @property
    def total_resolved(self) -> int:
        return (self.current_state.resolved + self.architecture.resolved +
                self.implementation.resolved + self.quality.resolved +
                self.migration.resolved)

    @property
    def completion_percent(self) -> float:
        if self.total_holes == 0:
            return 0.0
        return (self.total_resolved / self.total_holes) * 100


class CompletenessChecker:
    def __init__(self, refactor_ir: Path):
        self.refactor_ir = refactor_ir
        self.status = RefactorStatus()

    def analyze(self) -> RefactorStatus:
        """Analyze REFACTOR_IR.md and return status"""
        if not self.refactor_ir.exists():
            print(f"❌ REFACTOR_IR.md not found at {self.refactor_ir}")
            return self.status

        content = self.refactor_ir.read_text()

        # Find all holes
        hole_pattern = r'####\s+([HRM]\d+_\w+).*?\*\*Status\*\*:\s*(\w+)'
        matches = re.findall(hole_pattern, content, re.DOTALL)

        for hole_id, status in matches:
            status_lower = status.lower()
            hole_type = self._categorize_hole(hole_id)

            # Get the appropriate status object
            hole_status = getattr(self.status, hole_type)
            hole_status.total += 1

            if status_lower in ['resolved', 'complete', 'done']:
                hole_status.resolved += 1
            elif status_lower in ['in_progress', 'active', 'working']:
                hole_status.in_progress += 1
            else:
                hole_status.pending += 1

        return self.status

    def _categorize_hole(self, hole_id: str) -> str:
        """Categorize hole by ID prefix"""
        if hole_id.startswith('H0_'):
            return 'current_state'
        elif hole_id.startswith('R1_') or hole_id.startswith('R2_') or hole_id.startswith('R3_'):
            return 'architecture'
        elif hole_id.startswith('R4_') or hole_id.startswith('R5_') or hole_id.startswith('R6_'):
            return 'implementation'
        elif hole_id.startswith('R7_') or hole_id.startswith('R8_') or hole_id.startswith('R9_'):
            return 'quality'
        elif hole_id.startswith('M'):
            return 'migration'
        elif hole_id.startswith('R'):
            return 'implementation'  # Default for other R* holes
        else:
            return 'current_state'

    def display_dashboard(self):
        """Display progress dashboard"""
        print("=" * 60)
        print("  TYPED HOLES REFACTORING - PROGRESS DASHBOARD")
        print("=" * 60)
        print()

        # Overall progress
        completion = self.status.completion_percent
        total = self.status.total_holes
        resolved = self.status.total_resolved

        print(f"📊 Overall Progress: {resolved}/{total} holes ({completion:.1f}%)")
        self._print_progress_bar(completion)
        print()

        # Phase breakdown
        phases = [
            ("Current State (H0_*)", self.status.current_state, "🔍"),
            ("Architecture (R1-R3)", self.status.architecture, "🏗️"),
            ("Implementation (R4-R6)", self.status.implementation, "⚙️"),
            ("Quality (R7-R9)", self.status.quality, "✨"),
            ("Migration (M*)", self.status.migration, "🚀"),
        ]

        print("Phase Breakdown:")
        print("-" * 60)

        for name, hole_status, emoji in phases:
            if hole_status.total == 0:
                continue

            pct = (hole_status.resolved / hole_status.total * 100) if hole_status.total > 0 else 0
            print(f"\n{emoji}  {name}")
            print(f"    Total: {hole_status.total}  |  "
                  f"Resolved: {hole_status.resolved}  |  "
                  f"In Progress: {hole_status.in_progress}  |  "
                  f"Pending: {hole_status.pending}")
            print(f"    ", end="")
            self._print_progress_bar(pct, width=40)

        print()
        print("-" * 60)

        # Determine current phase
        current_phase = self._determine_phase()
        print(f"\n🎯 Current Phase: {current_phase}")

        # Next steps
        print(f"\n📋 Next Steps:")
        self._suggest_next_steps()

        print()
        print("=" * 60)

    def _print_progress_bar(self, percent: float, width: int = 50):
        """Print a visual progress bar"""
        filled = int(width * percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        print(f"[{bar}] {percent:.1f}%")

    def _determine_phase(self) -> str:
        """Determine which phase we're currently in"""
        if self.status.current_state.pending > 0:
            return "Phase 0: Discovery (analyzing current state)"

        if self.status.architecture.pending > 0 or self.status.architecture.in_progress > 0:
            return "Phase 1: Foundation (resolving architecture holes)"

        if self.status.implementation.pending > 0 or self.status.implementation.in_progress > 0:
            return "Phase 2: Implementation (resolving implementation holes)"

        if self.status.quality.pending > 0 or self.status.quality.in_progress > 0:
            return "Phase 3: Quality (resolving quality holes)"

        if self.status.migration.pending > 0 or self.status.migration.in_progress > 0:
            return "Phase 4: Migration (preparing for production)"

        if self.status.total_resolved == self.status.total_holes:
            return "Phase 5: Complete (ready for deployment)"

        return "Unknown phase"

    def _suggest_next_steps(self):
        """Suggest what to do next"""
        suggestions = []

        # Discovery phase
        if self.status.current_state.pending > 0:
            suggestions.append("  • Complete current state analysis (H0_ holes)")
            suggestions.append("  • Run: python scripts/next_hole.py")

        # Foundation phase
        elif self.status.architecture.pending > 0 or self.status.architecture.in_progress > 0:
            suggestions.append("  • Resolve architecture holes (R1-R3)")
            suggestions.append("  • Write characterization tests")
            suggestions.append("  • Run: python scripts/check_foundation.py")

        # Implementation phase
        elif self.status.implementation.pending > 0 or self.status.implementation.in_progress > 0:
            suggestions.append("  • Resolve implementation holes (R4-R6)")
            suggestions.append("  • Write resolution tests for each hole")
            suggestions.append("  • Run: python scripts/validate_resolution.py {HOLE_ID}")

        # Quality phase
        elif self.status.quality.pending > 0 or self.status.quality.in_progress > 0:
            suggestions.append("  • Resolve quality holes (R7-R9)")
            suggestions.append("  • Document test strategy and migration plan")
            suggestions.append("  • Run: python scripts/check_implementation.py")

        # Migration phase
        elif self.status.migration.pending > 0 or self.status.migration.in_progress > 0:
            suggestions.append("  • Define migration and rollback strategy")
            suggestions.append("  • Test rollback mechanism")
            suggestions.append("  • Run: python scripts/check_production.py")

        # Complete
        elif self.status.total_resolved == self.status.total_holes:
            suggestions.append("  • Generate final report: python scripts/generate_report.py")
            suggestions.append("  • Review all constraints satisfied")
            suggestions.append("  • Prepare PR for review")

        else:
            suggestions.append("  • Run: python scripts/next_hole.py")

        for suggestion in suggestions:
            print(suggestion)


def main():
    parser = argparse.ArgumentParser(
        description="Check overall refactor completeness and display dashboard"
    )
    parser.add_argument(
        "--ir",
        type=Path,
        default=Path("REFACTOR_IR.md"),
        help="Path to REFACTOR_IR.md"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    checker = CompletenessChecker(args.ir)
    status = checker.analyze()

    if args.json:
        result = {
            "total_holes": status.total_holes,
            "total_resolved": status.total_resolved,
            "completion_percent": status.completion_percent,
            "current_state": {
                "total": status.current_state.total,
                "resolved": status.current_state.resolved,
                "in_progress": status.current_state.in_progress,
                "pending": status.current_state.pending,
            },
            "architecture": {
                "total": status.architecture.total,
                "resolved": status.architecture.resolved,
                "in_progress": status.architecture.in_progress,
                "pending": status.architecture.pending,
            },
            "implementation": {
                "total": status.implementation.total,
                "resolved": status.implementation.resolved,
                "in_progress": status.implementation.in_progress,
                "pending": status.implementation.pending,
            },
            "quality": {
                "total": status.quality.total,
                "resolved": status.quality.resolved,
                "in_progress": status.quality.in_progress,
                "pending": status.quality.pending,
            },
            "migration": {
                "total": status.migration.total,
                "resolved": status.migration.resolved,
                "in_progress": status.migration.in_progress,
                "pending": status.migration.pending,
            }
        }
        print(json.dumps(result, indent=2))
    else:
        checker.display_dashboard()

    sys.exit(0)


if __name__ == "__main__":
    main()
