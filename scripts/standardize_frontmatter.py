#!/usr/bin/env python3
"""Standardize frontmatter across all skill files.

Handles:
1. INDEX.md files: Add name + description frontmatter
2. Leaf skills missing frontmatter: Add based on filename
3. Leaf skills missing category prefix in name: Add prefix
4. math/graph Title Case names: Convert to slug format
"""

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


def slugify(text: str) -> str:
    """Convert text to kebab-case slug."""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def extract_first_heading(content: str) -> str:
    """Extract first markdown heading text."""
    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def extract_description_from_content(content: str) -> str:
    """Extract a description from the first paragraph after the heading."""
    # Skip frontmatter
    text = content
    if text.startswith("---"):
        end = text.index("---", 3)
        text = text[end + 3:].strip()

    # Find first paragraph after heading
    lines = text.split("\n")
    found_heading = False
    desc_lines = []
    for line in lines:
        if line.startswith("#"):
            if found_heading and desc_lines:
                break
            found_heading = True
            continue
        if found_heading:
            stripped = line.strip()
            if stripped and not stripped.startswith("-") and not stripped.startswith("#"):
                desc_lines.append(stripped)
            elif desc_lines:
                break

    desc = " ".join(desc_lines)[:200].strip()
    return desc if desc else "Skills index"


def has_frontmatter(content: str) -> bool:
    return content.startswith("---")


def parse_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    end = content.index("---", 3)
    block = content[3:end].strip()
    result = {}
    for line in block.split("\n"):
        m = re.match(r'^(\w[\w-]*)\s*:\s*(.+)', line)
        if m:
            result[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return result


def get_category_from_path(filepath: Path) -> str:
    """Get the category from a file's path relative to skills/."""
    rel = filepath.relative_to(SKILLS_DIR)
    parts = rel.parts
    if len(parts) >= 2:
        return parts[0]
    return "root"


def filename_has_category_prefix(filename: str, category: str) -> bool:
    """Check if filename already starts with the category name."""
    name = filename.replace(".md", "")
    cat_variants = [category, category.replace("-", "")]
    for cv in cat_variants:
        if name.startswith(cv + "-") or name.startswith(cv):
            return True
    return False


def fix_index_files(dry_run: bool = False) -> int:
    """Add frontmatter to INDEX.md files."""
    count = 0
    for idx_file in sorted(SKILLS_DIR.rglob("INDEX.md")):
        if ".beads/" in str(idx_file):
            continue
        content = idx_file.read_text(encoding="utf-8")
        if has_frontmatter(content):
            continue

        category = get_category_from_path(idx_file)
        heading = extract_first_heading(content)
        desc = f"Index of {heading}" if heading else f"Index of {category} skills"

        frontmatter = f"---\nname: {category}-index\ndescription: {desc}\n---\n\n"
        new_content = frontmatter + content

        if not dry_run:
            idx_file.write_text(new_content, encoding="utf-8")
        rel = idx_file.relative_to(REPO_ROOT)
        print(f"  {'[DRY] ' if dry_run else ''}Added frontmatter to {rel}")
        count += 1

    return count


def fix_missing_frontmatter(dry_run: bool = False) -> int:
    """Add frontmatter to files that have none."""
    count = 0
    for md_file in sorted(SKILLS_DIR.rglob("*.md")):
        if ".beads/" in str(md_file):
            continue
        if md_file.name in ("INDEX.md", "SKILL.md", "README.md", "_SKILL_TEMPLATE.md"):
            continue
        # Skip resource/reference subdirs
        rel = md_file.relative_to(SKILLS_DIR)
        if any(p in rel.parts for p in ("resources", "references", "scripts", "examples")):
            continue

        content = md_file.read_text(encoding="utf-8")
        if has_frontmatter(content):
            continue

        category = get_category_from_path(md_file)
        filename = md_file.stem
        heading = extract_first_heading(content)

        if category != "root" and not filename_has_category_prefix(filename, category):
            name = f"{category}-{filename}"
        else:
            name = filename

        desc = heading if heading else filename.replace("-", " ").title()

        frontmatter = f"---\nname: {name}\ndescription: {desc}\n---\n\n"
        new_content = frontmatter + content

        if not dry_run:
            md_file.write_text(new_content, encoding="utf-8")
        print(f"  {'[DRY] ' if dry_run else ''}Added frontmatter to {rel}")
        count += 1

    return count


def fix_name_prefixes(dry_run: bool = False) -> int:
    """Add missing category prefix to name fields."""
    count = 0
    for md_file in sorted(SKILLS_DIR.rglob("*.md")):
        if ".beads/" in str(md_file):
            continue
        if md_file.name in ("INDEX.md", "SKILL.md", "README.md", "_SKILL_TEMPLATE.md"):
            continue
        # Skip gateway and resource files
        rel = md_file.relative_to(SKILLS_DIR)
        if rel.parts[0].startswith("discover-"):
            continue
        if any(p in rel.parts for p in ("resources", "references", "scripts", "examples")):
            continue

        content = md_file.read_text(encoding="utf-8")
        if not has_frontmatter(content):
            continue

        fm = parse_frontmatter(content)
        if "name" not in fm:
            continue

        category = get_category_from_path(md_file)
        if category == "root":
            continue

        current_name = fm["name"]

        # Check if name already has category prefix
        if current_name.startswith(f"{category}-"):
            continue

        # Check for tautology (filename already has category prefix)
        if filename_has_category_prefix(md_file.stem, category):
            continue

        # Check for Title Case names (math/graph files)
        if " " in current_name or current_name[0].isupper():
            new_name = f"{category}-{slugify(current_name)}"
        else:
            new_name = f"{category}-{current_name}"

        # Replace in content
        old_line = f"name: {fm['name']}"
        # Handle quoted and unquoted values
        if f'name: "{fm["name"]}"' in content:
            old_line = f'name: "{fm["name"]}"'
            new_line = f'name: {new_name}'
        elif f"name: '{fm['name']}'" in content:
            old_line = f"name: '{fm['name']}'"
            new_line = f"name: {new_name}"
        else:
            new_line = f"name: {new_name}"

        new_content = content.replace(old_line, new_line, 1)

        if new_content != content:
            if not dry_run:
                md_file.write_text(new_content, encoding="utf-8")
            print(f"  {'[DRY] ' if dry_run else ''}{rel}: {current_name} → {new_name}")
            count += 1

    return count


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=== Adding frontmatter to INDEX.md files ===")
    n1 = fix_index_files(dry_run=args.dry_run)

    print("\n=== Adding frontmatter to files missing it ===")
    n2 = fix_missing_frontmatter(dry_run=args.dry_run)

    print("\n=== Fixing name prefixes ===")
    n3 = fix_name_prefixes(dry_run=args.dry_run)

    total = n1 + n2 + n3
    action = "Would update" if args.dry_run else "Updated"
    print(f"\n{action} {total} files ({n1} indexes, {n2} missing frontmatter, {n3} name prefixes)")


if __name__ == "__main__":
    main()
