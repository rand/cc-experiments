#!/usr/bin/env python3
"""Replace <cc-polymath-root> references with relative paths.

Scans all .md files in the repository and replaces occurrences of
<cc-polymath-root>/path/to/file with the relative path from the
containing file's directory to the target file.
"""

import os
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r'<cc-polymath-root>(/[^\s)>`\'"*\]]+)')


def compute_relative(from_file: Path, target_path: str) -> str:
    """Compute relative path from from_file's directory to target_path (repo-relative)."""
    from_dir = from_file.parent.relative_to(REPO_ROOT)
    # target_path starts with /, strip it to make repo-relative
    target = target_path.lstrip('/')
    target_p = Path(target)

    try:
        rel = os.path.relpath(REPO_ROOT / target_p, REPO_ROOT / from_dir)
    except ValueError:
        return target  # fallback

    return rel


def fix_file(filepath: Path, dry_run: bool = False) -> int:
    """Fix all <cc-polymath-root> references in a single file.

    Returns number of replacements made.
    """
    content = filepath.read_text(encoding='utf-8')

    if '<cc-polymath-root>' not in content:
        return 0

    count = 0

    def replace_match(m: re.Match) -> str:
        nonlocal count
        target_path = m.group(1)
        rel = compute_relative(filepath, target_path)
        count += 1
        return rel

    new_content = PATTERN.sub(replace_match, content)

    # Handle bare <cc-polymath-root> references (without a path following)
    # e.g., "Plugin data stays in `<cc-polymath-root>/`"
    bare_pattern = re.compile(r'<cc-polymath-root>/(?=[\s`\'")\]>*]|$)', re.MULTILINE)

    def replace_bare(m: re.Match) -> str:
        nonlocal count
        from_dir = filepath.parent.relative_to(REPO_ROOT)
        rel = os.path.relpath(REPO_ROOT, REPO_ROOT / from_dir)
        count += 1
        return f'{rel}/'

    new_content = bare_pattern.sub(replace_bare, new_content)

    # Handle remaining bare <cc-polymath-root> without trailing slash
    remaining = re.compile(r'<cc-polymath-root>')

    def replace_remaining(m: re.Match) -> str:
        nonlocal count
        from_dir = filepath.parent.relative_to(REPO_ROOT)
        rel = os.path.relpath(REPO_ROOT, REPO_ROOT / from_dir)
        count += 1
        return rel

    new_content = remaining.sub(replace_remaining, new_content)

    if not dry_run and new_content != content:
        filepath.write_text(new_content, encoding='utf-8')

    return count


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fix <cc-polymath-root> path references')
    parser.add_argument('--dry-run', action='store_true', help='Show what would change without modifying files')
    args = parser.parse_args()

    total_files = 0
    total_replacements = 0

    # Find all .md files
    for md_file in sorted(REPO_ROOT.rglob('*.md')):
        # Skip hidden directories and node_modules
        parts = md_file.relative_to(REPO_ROOT).parts
        if any(p.startswith('.') for p in parts):
            continue
        if 'node_modules' in parts:
            continue

        count = fix_file(md_file, dry_run=args.dry_run)
        if count > 0:
            rel = md_file.relative_to(REPO_ROOT)
            print(f"  {'[DRY RUN] ' if args.dry_run else ''}Fixed {count} refs in {rel}")
            total_files += 1
            total_replacements += count

    action = "Would fix" if args.dry_run else "Fixed"
    print(f"\n{action} {total_replacements} references across {total_files} files")


if __name__ == '__main__':
    main()
