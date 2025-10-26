#!/usr/bin/env python3
"""
Create gateway skills for new categories.
"""

from pathlib import Path

NEW_GATEWAYS = [
    ("tui", "terminal user interfaces, TUI, Bubble Tea, Ratatui, terminal UI, text-based interfaces, ncurses",
     "Automatically discover terminal UI skills"),
    ("zig", "Zig, systems programming, comptime, allocators, C interop, build.zig, zon package manager",
     "Automatically discover Zig programming skills"),
    ("networking", "networking, SSH, mTLS, NAT traversal, VPN, Tailscale, network resilience, connection reliability",
     "Automatically discover networking and connectivity skills"),
    ("workflow", "Beads, workflow, task management, context strategies, dependency management, multi-session",
     "Automatically discover workflow and task management skills"),
]

GATEWAY_TEMPLATE = """---
name: discover-{category}
description: {description} when working with {first_keyword}. Activates for {category} development tasks.
---

# {title} Skills Discovery

Provides automatic access to comprehensive {category} skills.

## When This Skill Activates

This skill auto-activates when you're working with:
{keyword_list}

## Available Skills

### Quick Reference

The {title} category contains {skill_count} skills:

{skill_list}

### Load Full Category Details

For complete descriptions and workflows:

```bash
cat skills/{category}/INDEX.md
```

This loads the full {title} category index with:
- Detailed skill descriptions
- Usage triggers for each skill
- Common workflow combinations
- Cross-references to related skills

### Load Specific Skills

Load individual skills as needed:

```bash
{load_examples}
```

## Progressive Loading

This gateway skill enables progressive loading:
- **Level 1**: Gateway loads automatically (you're here now)
- **Level 2**: Load category INDEX.md for full overview
- **Level 3**: Load specific skills as needed

## Usage Instructions

1. **Auto-activation**: This skill loads automatically when Claude Code detects {category} work
2. **Browse skills**: Run `cat skills/{category}/INDEX.md` for full category overview
3. **Load specific skills**: Use bash commands above to load individual skills

---

**Next Steps**: Run `cat skills/{category}/INDEX.md` to see full category details.
"""

def get_skills_in_category(category):
    """Get list of skill files in a category."""
    path = Path(f"skills/{category}")
    if not path.exists():
        return []

    skills = []
    for file in path.glob("*.md"):
        if file.name != "INDEX.md":
            skills.append(file.name)
    return sorted(skills)

def create_gateway(category, keywords, description):
    """Create a gateway skill for a category."""
    skills = get_skills_in_category(category)
    if not skills:
        print(f"⚠ {category}: No skills found")
        return False

    # Parse keywords
    keyword_list = [f"- {kw.strip()}" for kw in keywords.split(',')[:8]]
    first_keyword = keywords.split(',')[0].strip()

    # Generate skill list
    skill_list = "\n".join([f"{i+1}. **{s.replace('.md', '')}**"
                           for i, s in enumerate(skills)])

    # Generate load examples
    load_examples = "\n".join([f"cat skills/{category}/{s}"
                              for s in skills[:3]])

    # Generate content
    title = category.title().replace('-', ' ')
    content = GATEWAY_TEMPLATE.format(
        category=category,
        description=description,
        first_keyword=first_keyword,
        title=title,
        keyword_list="\n".join(keyword_list),
        skill_count=len(skills),
        skill_list=skill_list,
        load_examples=load_examples
    )

    # Write file
    gateway_dir = Path(f"skills/discover-{category}")
    gateway_dir.mkdir(parents=True, exist_ok=True)
    gateway_file = gateway_dir / "SKILL.md"
    gateway_file.write_text(content)

    print(f"✓ discover-{category}: Created gateway ({len(skills)} skills)")
    return True

def main():
    """Create gateway skills for new categories."""
    print("Creating gateway skills for new categories...\n")

    created = 0
    for category, keywords, description in NEW_GATEWAYS:
        if create_gateway(category, keywords, description):
            created += 1

    print(f"\nCreated {created} new gateway skills")

if __name__ == "__main__":
    main()
