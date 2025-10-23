#!/usr/bin/env python3
"""
Convert Holes to Beads Issues

Synchronizes typed holes from REFACTOR_IR.md with beads issues for workflow integration.
Enables tracking hole resolution through beads while maintaining hole-specific IR.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Hole:
    id: str
    question: str
    dependencies: List[str]
    status: str
    type: str


class HolesToBeads:
    def __init__(self, refactor_ir: Path, dry_run: bool = False):
        self.refactor_ir = refactor_ir
        self.dry_run = dry_run
        self.holes: Dict[str, Hole] = {}
        self.bead_mapping: Dict[str, str] = {}  # hole_id -> bead_id

    def parse_holes(self):
        """Parse REFACTOR_IR.md to extract holes"""
        if not self.refactor_ir.exists():
            print(f"❌ REFACTOR_IR.md not found at {self.refactor_ir}")
            return

        content = self.refactor_ir.read_text()

        # Extract holes
        hole_sections = re.split(r'####\s+([HRM]\d+_\w+)', content)[1:]

        for i in range(0, len(hole_sections), 2):
            if i + 1 >= len(hole_sections):
                break

            hole_id = hole_sections[i]
            hole_content = hole_sections[i + 1]

            # Extract question
            question_match = re.search(r'\*\*Question\*\*:\s*(.+?)(?:\n|$)', hole_content)
            question = question_match.group(1).strip() if question_match else f"Resolve {hole_id}"

            # Extract dependencies
            deps_match = re.search(r'\*\*Dependencies\*\*:\s*(.+?)(?:\n|$)', hole_content)
            dependencies = []
            if deps_match:
                deps_text = deps_match.group(1)
                if deps_text.lower() not in ['none', 'n/a', '']:
                    deps = re.findall(r'([HRM]\d+_\w+)', deps_text)
                    dependencies = deps

            # Extract status
            status_match = re.search(r'\*\*Status\*\*:\s*(\w+)', hole_content)
            status = status_match.group(1).lower() if status_match else 'pending'

            # Determine type
            hole_type = self._categorize_hole(hole_id)

            self.holes[hole_id] = Hole(hole_id, question, dependencies, status, hole_type)

    def _categorize_hole(self, hole_id: str) -> str:
        """Categorize hole by prefix"""
        if hole_id.startswith('H0_'):
            return 'current_state'
        elif hole_id.startswith('R'):
            if any(hole_id.startswith(f'R{i}_') for i in [1, 2, 3]):
                return 'architecture'
            elif any(hole_id.startswith(f'R{i}_') for i in [4, 5, 6]):
                return 'implementation'
            elif any(hole_id.startswith(f'R{i}_') for i in [7, 8, 9]):
                return 'quality'
            else:
                return 'refactor'
        elif hole_id.startswith('M'):
            return 'migration'
        return 'unknown'

    def sync_to_beads(self):
        """Create or update beads issues for all holes"""
        print("🔄 Syncing holes to beads...\n")

        # Get existing beads
        existing_beads = self._get_existing_beads()

        created = 0
        updated = 0
        skipped = 0

        for hole_id, hole in self.holes.items():
            # Check if bead already exists for this hole
            existing_bead = existing_beads.get(hole_id)

            if existing_bead:
                # Update if status changed
                if self._should_update_bead(hole, existing_bead):
                    self._update_bead(existing_bead['id'], hole)
                    updated += 1
                else:
                    skipped += 1
            else:
                # Create new bead
                bead_id = self._create_bead(hole)
                if bead_id:
                    self.bead_mapping[hole_id] = bead_id
                    created += 1

        print(f"\n✅ Sync complete:")
        print(f"   Created: {created}")
        print(f"   Updated: {updated}")
        print(f"   Skipped: {skipped}")

        # Add dependencies
        if not self.dry_run:
            print(f"\n🔗 Adding dependencies...")
            self._add_dependencies()

    def _get_existing_beads(self) -> Dict[str, Dict]:
        """Get existing beads that reference hole IDs"""
        try:
            result = subprocess.run(
                ["bd", "list", "--json"],
                capture_output=True,
                text=True,
                check=True
            )

            if result.returncode != 0:
                return {}

            beads_data = json.loads(result.stdout)
            existing = {}

            for bead in beads_data:
                # Check if title contains hole ID
                title = bead.get('title', '')
                for hole_id in self.holes.keys():
                    if hole_id in title:
                        existing[hole_id] = bead
                        break

            return existing

        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            return {}

    def _should_update_bead(self, hole: Hole, bead: Dict) -> bool:
        """Check if bead needs updating"""
        bead_status = bead.get('status', '').lower()
        hole_status_map = {
            'pending': 'ready',
            'in_progress': 'in_progress',
            'resolved': 'done',
            'complete': 'done',
            'done': 'done'
        }

        expected_status = hole_status_map.get(hole.status, 'ready')
        return bead_status != expected_status

    def _create_bead(self, hole: Hole) -> Optional[str]:
        """Create a new bead issue for this hole"""
        title = f"Resolve {hole.id}: {hole.question[:80]}"

        # Map hole type to bead type
        type_map = {
            'current_state': 'task',
            'architecture': 'architecture',
            'implementation': 'feature',
            'quality': 'test',
            'migration': 'deploy',
            'refactor': 'refactor'
        }
        bead_type = type_map.get(hole.type, 'task')

        # Map hole status to bead status
        status_map = {
            'pending': 'ready',
            'in_progress': 'in_progress',
            'resolved': 'done',
            'complete': 'done',
            'done': 'done'
        }
        bead_status = status_map.get(hole.status, 'ready')

        # Determine priority
        priority = 1 if hole.type in ['current_state', 'architecture'] else 2

        cmd = [
            "bd", "create",
            title,
            "-t", bead_type,
            "-p", str(priority),
            "--json"
        ]

        if self.dry_run:
            print(f"[DRY RUN] Would create: {title}")
            return f"bd-{hole.id}"

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            if result.returncode == 0:
                bead_data = json.loads(result.stdout)
                bead_id = bead_data.get('id', '')
                print(f"✓ Created {bead_id}: {hole.id}")

                # Update status if not ready
                if bead_status != 'ready':
                    self._update_bead(bead_id, hole)

                return bead_id

        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            print(f"✗ Failed to create bead for {hole.id}: {e}")

        return None

    def _update_bead(self, bead_id: str, hole: Hole):
        """Update bead status"""
        status_map = {
            'pending': 'ready',
            'in_progress': 'in_progress',
            'resolved': 'done',
            'complete': 'done',
            'done': 'done'
        }
        bead_status = status_map.get(hole.status, 'ready')

        cmd = ["bd", "update", bead_id, "--status", bead_status, "--json"]

        if self.dry_run:
            print(f"[DRY RUN] Would update {bead_id} to {bead_status}")
            return

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✓ Updated {bead_id}: {hole.id} → {bead_status}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"✗ Failed to update {bead_id}: {e}")

    def _add_dependencies(self):
        """Add bead dependencies based on hole dependencies"""
        if self.dry_run:
            return

        # Get current bead mapping
        existing_beads = self._get_existing_beads()
        bead_ids = {}

        for hole_id, bead_data in existing_beads.items():
            bead_ids[hole_id] = bead_data['id']

        # Add custom mapping from creation
        bead_ids.update(self.bead_mapping)

        # Add dependencies
        for hole_id, hole in self.holes.items():
            if not hole.dependencies:
                continue

            bead_id = bead_ids.get(hole_id)
            if not bead_id:
                continue

            for dep_hole_id in hole.dependencies:
                dep_bead_id = bead_ids.get(dep_hole_id)
                if not dep_bead_id:
                    continue

                cmd = ["bd", "dep", "add", bead_id, dep_bead_id, "--type", "blocks"]

                try:
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                    print(f"✓ Added dependency: {bead_id} ← {dep_bead_id}")
                except subprocess.CalledProcessError:
                    # Dependency might already exist
                    pass

    def export_mapping(self, output_file: Path):
        """Export hole-to-bead mapping"""
        mapping = {
            "holes_to_beads": self.bead_mapping,
            "total_holes": len(self.holes),
            "synced": len(self.bead_mapping)
        }

        output_file.write_text(json.dumps(mapping, indent=2))
        print(f"\n📋 Mapping saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Sync typed holes to beads issues"
    )
    parser.add_argument(
        "--ir",
        type=Path,
        default=Path("REFACTOR_IR.md"),
        help="Path to REFACTOR_IR.md"
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path(".beads/hole_mapping.json"),
        help="Output file for hole-to-bead mapping"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without creating beads"
    )

    args = parser.parse_args()

    # Check if bd is available
    try:
        subprocess.run(["bd", "version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: 'bd' command not found")
        print("   Install beads: go install github.com/steveyegge/beads/cmd/bd@latest")
        sys.exit(1)

    print("🔄 Typed Holes to Beads Sync\n")

    syncer = HolesToBeads(args.ir, dry_run=args.dry_run)
    syncer.parse_holes()

    if not syncer.holes:
        print("No holes found in REFACTOR_IR.md")
        sys.exit(1)

    print(f"Found {len(syncer.holes)} holes\n")

    syncer.sync_to_beads()

    if not args.dry_run:
        args.mapping.parent.mkdir(parents=True, exist_ok=True)
        syncer.export_mapping(args.mapping)

        print("\n💡 Next steps:")
        print("   • Run 'bd ready' to see ready holes")
        print("   • Run 'bd list --json' to see all synced issues")
        print("   • Use 'bd update <id> --status in_progress' when starting work")
        print("   • Export state: bd export -o .beads/issues.jsonl")


if __name__ == "__main__":
    main()
