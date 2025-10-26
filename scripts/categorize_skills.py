#!/usr/bin/env python3
"""
Categorize root-level skills into appropriate directories.
"""

import os
import shutil
from pathlib import Path

# Categorization map: skill_file -> target_directory
CATEGORIZATION = {
    # Mobile/iOS skills (6) → mobile/
    "ios-networking.md": "mobile",
    "ios-testing.md": "mobile",
    "swift-concurrency.md": "mobile",
    "swiftdata-persistence.md": "mobile",
    "swiftui-architecture.md": "mobile",
    "swiftui-navigation.md": "mobile",

    # Modal skills (6) → modal/
    "modal-functions-basics.md": "modal",
    "modal-gpu-workloads.md": "modal",
    "modal-image-building.md": "modal",
    "modal-scheduling.md": "modal",
    "modal-volumes-secrets.md": "modal",
    "modal-web-endpoints.md": "modal",

    # TUI skills (5) → NEW: tui/
    "bubbletea-architecture.md": "tui",
    "bubbletea-components.md": "tui",
    "ratatui-architecture.md": "tui",
    "ratatui-widgets.md": "tui",
    "tui-best-practices.md": "tui",

    # Zig skills (6) → NEW: zig/
    "zig-build-system.md": "zig",
    "zig-c-interop.md": "zig",
    "zig-memory-management.md": "zig",
    "zig-package-management.md": "zig",
    "zig-project-setup.md": "zig",
    "zig-testing.md": "zig",

    # Networking skills (5) → NEW: networking/
    "mosh-resilient-ssh.md": "networking",
    "mtls-implementation.md": "networking",
    "nat-traversal.md": "networking",
    "network-resilience-patterns.md": "networking",
    "tailscale-vpn.md": "networking",

    # Data/Database skills (3) → database/
    "apache-iceberg.md": "database",
    "duckdb-analytics.md": "database",
    "redpanda-streaming.md": "database",

    # Beads workflow (4) → NEW: workflow/
    "beads-context-strategies.md": "workflow",
    "beads-dependency-management.md": "workflow",
    "beads-multi-session-patterns.md": "workflow",
    "beads-workflow.md": "workflow",

    # Collaboration (1) → collaboration/
    "codetour-guided-walkthroughs.md": "collaboration",

    # Meta/Discovery skills - KEEP AT ROOT (5)
    # skill-creation.md, skill-prompt-discovery.md, skill-prompt-planning.md,
    # skill-repo-discovery.md, skill-repo-planning.md

    # Documentation - KEEP AT ROOT
    # MIGRATION_GUIDE.md, REFACTORING_SUMMARY.md, _SKILL_TEMPLATE.md
}

def move_skill(skill_file, target_category):
    """Move a skill file to its target category directory."""
    source = Path(f"skills/{skill_file}")
    target_dir = Path(f"skills/{target_category}")
    target_file = target_dir / skill_file

    if not source.exists():
        print(f"⚠ {skill_file}: Source file not found, skipping")
        return False

    # Create target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)

    # Move the file
    shutil.move(str(source), str(target_file))
    print(f"✓ {skill_file} → {target_category}/")
    return True

def main():
    """Categorize all root-level skills."""
    print("Categorizing root-level skills...\n")

    moved = 0
    failed = 0

    for skill_file, target_category in sorted(CATEGORIZATION.items()):
        if move_skill(skill_file, target_category):
            moved += 1
        else:
            failed += 1

    print(f"\nSummary:")
    print(f"  Moved: {moved}")
    print(f"  Failed: {failed}")
    print(f"\nNew categories created:")
    print(f"  - tui/ (5 skills)")
    print(f"  - zig/ (6 skills)")
    print(f"  - networking/ (5 skills)")
    print(f"  - workflow/ (4 skills)")
    print(f"\nExisting categories expanded:")
    print(f"  - mobile/ (+6 skills)")
    print(f"  - modal/ (+6 skills)")
    print(f"  - database/ (+3 skills)")
    print(f"  - collaboration/ (+1 skill)")

if __name__ == "__main__":
    main()
