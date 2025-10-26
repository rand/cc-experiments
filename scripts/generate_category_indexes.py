#!/usr/bin/env python3
"""
Generate category INDEX.md files for all skill categories.
Creates simpler templates that list skills with basic descriptions.
"""

import os
from pathlib import Path
from typing import List, Tuple

def get_skills_in_category(category_dir: str) -> List[str]:
    """Get list of skill files in a category directory."""
    path = Path(f"skills/{category_dir}")
    if not path.exists():
        return []

    skills = []
    for file in path.glob("*.md"):
        if file.name != "INDEX.md" and not file.name.startswith("_"):
            skills.append(file.name)
    return sorted(skills)

def read_skill_frontmatter(skill_path: Path) -> Tuple[str, str]:
    """Extract name and description from skill YAML frontmatter."""
    try:
        with open(skill_path, 'r') as f:
            lines = f.readlines()

        if not lines or not lines[0].strip() == '---':
            return "", ""

        name = ""
        description = ""
        for i in range(1, min(10, len(lines))):
            line = lines[i].strip()
            if line == '---':
                break
            if line.startswith('name:'):
                name = line.split('name:', 1)[1].strip()
            elif line.startswith('description:'):
                description = line.split('description:', 1)[1].strip()

        return name, description
    except Exception as e:
        print(f"Warning: Could not read {skill_path}: {e}")
        return "", ""

def generate_category_index(category: str, skills: List[str]) -> str:
    """Generate a category INDEX.md file."""

    # Read skill metadata
    skill_info = []
    for skill_file in skills:
        skill_path = Path(f"skills/{category}/{skill_file}")
        name, description = read_skill_frontmatter(skill_path)
        if not description:
            # Fallback to filename if no frontmatter
            description = f"Skills for {skill_file.replace('.md', '').replace('-', ' ')}"
        skill_info.append((skill_file, name or skill_file.replace('.md', ''), description))

    # Generate content
    content = f"""# {category.title().replace('-', ' ')} Skills

## Category Overview

**Total Skills**: {len(skills)}
**Category**: {category}

## Skills in This Category

"""

    for skill_file, name, description in skill_info:
        content += f"""### {skill_file}
**Description**: {description}

**Load this skill**:
```bash
cat skills/{category}/{skill_file}
```

---

"""

    content += f"""## Loading All Skills

```bash
# List all skills in this category
ls skills/{category}/*.md

# Load specific skills
"""

    for skill_file in skills[:3]:
        content += f"cat skills/{category}/{skill_file}\n"

    if len(skills) > 3:
        content += f"# ... and {len(skills) - 3} more\n"

    content += """```

## Related Categories

See `skills/README.md` for the complete catalog of all categories and gateway skills.

---

**Browse**: This index provides a quick reference. Load the `discover-{category}` gateway skill for common workflows and integration patterns.

```bash
cat skills/discover-{category}/SKILL.md
```
""".replace('{category}', category)

    return content

def main():
    """Generate INDEX.md files for all categories that don't have them yet."""

    # Get all category directories
    skills_path = Path("skills")
    categories = []

    for item in skills_path.iterdir():
        if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('discover-'):
            # Skip Agent Skill directories
            if (item / "SKILL.md").exists():
                continue
            categories.append(item.name)

    categories.sort()

    print(f"Found {len(categories)} categories")

    created = 0
    skipped = 0

    for category in categories:
        index_path = Path(f"skills/{category}/INDEX.md")

        if index_path.exists():
            print(f"✓ {category}: INDEX.md already exists, skipping")
            skipped += 1
            continue

        skills = get_skills_in_category(category)

        if not skills:
            print(f"⚠ {category}: No skills found, skipping")
            continue

        # Generate INDEX.md
        content = generate_category_index(category, skills)
        index_path.write_text(content)

        print(f"✓ {category}: Created INDEX.md ({len(skills)} skills)")
        created += 1

    print(f"\nSummary:")
    print(f"  Created: {created}")
    print(f"  Skipped: {skipped}")
    print(f"  Total categories: {len(categories)}")

if __name__ == "__main__":
    main()
