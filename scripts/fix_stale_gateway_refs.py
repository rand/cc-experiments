#!/usr/bin/env python3
"""Fix references to removed/consolidated gateways.

Updates all .md files that reference old gateway names to use the new names.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Old gateway name -> new gateway name
RENAMES = {
    "discover-build-systems": "discover-cicd",
    "discover-containers": "discover-infra",
    "discover-cloud": "discover-infra",
    "discover-infrastructure": "discover-infra",
    "discover-deployment": "discover-infra",
    "discover-collaboration": "discover-product",
    "discover-diagrams": "discover-engineering",
    "discover-proxies": "discover-networking",
    "discover-protocols": "discover-networking",
    "discover-observability": "discover-debugging",
    "discover-caching": "discover-database",
    "discover-ebpf": "discover-systems-theory",
    "discover-ir": "discover-systems-theory",
    "discover-plt": "discover-systems-theory",
    "discover-formal": "discover-systems-theory",
    "discover-distributed-systems": "discover-distributed",
    "discover-realtime": "discover-distributed",
    "discover-workflow": "discover-product",
    "discover-modal": "discover-ml",
    "discover-tui": "discover-frontend",
}


def fix_file(filepath: Path, dry_run: bool = False) -> int:
    """Fix stale gateway references in a file."""
    content = filepath.read_text(encoding="utf-8")
    original = content
    count = 0

    for old, new in RENAMES.items():
        # Replace gateway name references (text mentions)
        # Match the gateway name as a whole word (not as part of a longer path)
        pattern = re.compile(
            r'(?<!/)'  # Not preceded by /
            + re.escape(old)
            + r'(?!/)'  # Not followed by /
        )
        matches = pattern.findall(content)
        if matches:
            content = pattern.sub(new, content)
            count += len(matches)

        # Fix Read paths that point to old gateway dirs
        old_read = f"Read ../{ old }/SKILL.md"
        new_read = f"Read ../{new}/SKILL.md"
        if old_read in content:
            n = content.count(old_read)
            content = content.replace(old_read, new_read)
            count += n

    if not dry_run and content != original:
        filepath.write_text(content, encoding="utf-8")

    return count


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    total_files = 0
    total_replacements = 0

    for md_file in sorted(REPO_ROOT.rglob("*.md")):
        parts = md_file.relative_to(REPO_ROOT).parts
        if any(p.startswith('.') for p in parts):
            continue
        if 'node_modules' in parts:
            continue
        # Skip the gateways themselves (they're already correct)
        if 'discover-' in str(md_file) and 'SKILL.md' in str(md_file):
            continue

        count = fix_file(md_file, dry_run=args.dry_run)
        if count > 0:
            rel = md_file.relative_to(REPO_ROOT)
            print(f"  {'[DRY RUN] ' if args.dry_run else ''}Fixed {count} refs in {rel}")
            total_files += 1
            total_replacements += count

    action = "Would fix" if args.dry_run else "Fixed"
    print(f"\n{action} {total_replacements} references across {total_files} files")


if __name__ == "__main__":
    main()
