#!/usr/bin/env python3
"""Consolidate gateway skills from 40 to 23.

Reads source gateways, merges their content, and writes consolidated gateways.
Also removes old gateway directories and updates cross-references.
"""

import os
import re
import shutil
import yaml
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


def parse_frontmatter(path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a SKILL.md file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.index("---", 3)
    return yaml.safe_load(text[3:end])


def parse_gateway(path: Path) -> dict[str, Any]:
    """Parse a gateway SKILL.md into structured data."""
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(path)

    # Extract "When This Skill Activates" section
    activates_match = re.search(
        r'## When This Skill Activates\n(.*?)(?=\n## )', text, re.DOTALL
    )
    activates = activates_match.group(1).strip() if activates_match else ""

    # Extract skills section
    skills_match = re.search(
        r'## Available Skills.*?\n(.*?)(?=\n## )', text, re.DOTALL
    )
    skills_section = skills_match.group(1).strip() if skills_match else ""

    # Extract category indexes referenced
    index_refs = re.findall(r'Read\s+(\.\.?/[^\s]+INDEX\.md)', text)

    return {
        "frontmatter": fm,
        "activates": activates,
        "skills_section": skills_section,
        "index_refs": index_refs,
        "path": path,
    }


def count_skills_in_section(section: str) -> int:
    """Count skill entries (lines starting with - or numbered) in a section."""
    count = 0
    for line in section.splitlines():
        stripped = line.strip()
        if re.match(r'^[\d]+\.\s+', stripped) or (stripped.startswith('- ') and not stripped.startswith('- **')):
            count += 1
    return count


def build_gateway(
    name: str,
    description: str,
    title: str,
    activates_lines: list[str],
    skill_groups: list[tuple[str, str]],  # (heading, content)
    index_refs: list[str],
    workflows: list[tuple[str, list[str]]],  # (name, steps)
) -> str:
    """Build a consolidated gateway SKILL.md."""
    # Count total skills
    total_skills = sum(count_skills_in_section(content) for _, content in skill_groups)
    if total_skills == 0:
        # Fallback: count non-empty lines in skill sections
        for _, content in skill_groups:
            for line in content.splitlines():
                if line.strip().startswith(('-', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    total_skills += 1

    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        "license: MIT",
        "metadata:",
        "  author: rand",
        '  version: "4.0"',
        "compatibility:",
        '  claude-code: ">=1.0.0"',
        "---",
        "",
        f"# {title}",
        "",
        "## When This Skill Activates",
    ]

    for a in activates_lines:
        lines.append(f"- {a}")

    lines.extend([
        "",
        f"## Available Skills ({total_skills} total)",
    ])

    for heading, content in skill_groups:
        if heading:
            lines.append(f"\n### {heading}")
        lines.append(content)

    lines.extend(["", "## Load Full Category Details"])
    for ref in index_refs:
        lines.append(f"Read {ref}")

    if workflows:
        lines.extend(["", "## Common Workflows"])
        for wf_name, steps in workflows:
            lines.append(f"\n### {wf_name}")
            for i, step in enumerate(steps, 1):
                lines.append(f"{i}. {step}")

    lines.extend([
        "",
        "## Progressive Loading",
        f"- **Level 1**: This gateway loads automatically (~{len(lines)} lines)",
        "- **Level 2**: Load category INDEX.md for full skill listings",
        "- **Level 3**: Load specific skills as needed",
    ])

    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════════
# CONSOLIDATION DEFINITIONS
# ═══════════════════════════════════════════════════════════════

MERGES = {
    # New gateway name -> list of source gateways to merge
    "discover-infra": [
        "discover-cloud",
        "discover-infrastructure",
        "discover-deployment",
        "discover-containers",
    ],
    "discover-distributed": [
        "discover-distributed-systems",
        "discover-realtime",
    ],
    "discover-systems-theory": [
        "discover-ebpf",
        "discover-ir",
        "discover-plt",
        "discover-formal",
    ],
}

# Absorptions: target gateway absorbs source gateways
ABSORPTIONS = {
    "discover-cicd": ["discover-build-systems"],
    "discover-networking": ["discover-protocols", "discover-proxies"],
    "discover-product": ["discover-collaboration", "discover-workflow"],
    "discover-database": ["discover-caching"],
    "discover-debugging": ["discover-observability"],
    "discover-engineering": ["discover-diagrams"],
    "discover-frontend": ["discover-tui"],
    "discover-ml": ["discover-modal"],
}


def merge_gateways(target_name: str, sources: list[str]) -> None:
    """Create a new merged gateway from multiple source gateways."""
    parsed = []
    for src in sources:
        path = SKILLS_DIR / src / "SKILL.md"
        if path.exists():
            parsed.append(parse_gateway(path))

    # Combine activates lines (deduplicated)
    all_activates = []
    seen = set()
    for p in parsed:
        for line in p["activates"].splitlines():
            stripped = line.strip().lstrip("- ")
            if stripped and stripped not in seen:
                seen.add(stripped)
                all_activates.append(stripped)

    # Combine skill sections with source labels
    skill_groups = []
    for p in parsed:
        src_name = p["frontmatter"].get("name", "").replace("discover-", "").replace("-", " ").title()
        skill_groups.append((f"{src_name} Skills", p["skills_section"]))

    # Combine index refs (deduplicated)
    all_refs = []
    seen_refs = set()
    for p in parsed:
        for ref in p["index_refs"]:
            if ref not in seen_refs:
                seen_refs.add(ref)
                # Recompute relative path from new gateway location
                src_dir = p["path"].parent
                abs_ref = (src_dir / ref).resolve()
                new_dir = SKILLS_DIR / target_name
                try:
                    new_ref = os.path.relpath(abs_ref, new_dir)
                except ValueError:
                    new_ref = ref
                all_refs.append(new_ref)

    return all_activates, skill_groups, all_refs


def absorb_gateway(target_name: str, source_names: list[str]) -> None:
    """Absorb source gateways into an existing target gateway."""
    target_path = SKILLS_DIR / target_name / "SKILL.md"
    target = parse_gateway(target_path)

    for src_name in source_names:
        src_path = SKILLS_DIR / src_name / "SKILL.md"
        if not src_path.exists():
            continue
        source = parse_gateway(src_path)

        # Merge activates
        existing = set(line.strip().lstrip("- ") for line in target["activates"].splitlines() if line.strip())
        for line in source["activates"].splitlines():
            stripped = line.strip().lstrip("- ")
            if stripped and stripped not in existing:
                target["activates"] += f"\n- {stripped}"
                existing.add(stripped)

        # Add skill section
        src_label = source["frontmatter"].get("name", src_name).replace("discover-", "").replace("-", " ").title()
        target["skills_section"] += f"\n\n### {src_label} Skills\n{source['skills_section']}"

        # Add index refs
        existing_refs = set(target["index_refs"])
        for ref in source["index_refs"]:
            # Recompute relative path
            src_dir = source["path"].parent
            abs_ref = (src_dir / ref).resolve()
            target_dir = target_path.parent
            try:
                new_ref = os.path.relpath(abs_ref, target_dir)
            except ValueError:
                new_ref = ref
            if new_ref not in existing_refs:
                target["index_refs"].append(new_ref)
                existing_refs.add(new_ref)

    return target


def remove_old_gateways(gateways: list[str], dry_run: bool = False) -> None:
    """Remove old gateway directories."""
    for gw in gateways:
        path = SKILLS_DIR / gw
        if path.exists():
            if dry_run:
                print(f"  [DRY RUN] Would remove {path}")
            else:
                shutil.rmtree(path)
                print(f"  Removed {path.relative_to(REPO_ROOT)}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    all_removed = []

    # Process merges
    print("\n=== Processing Merges ===")
    for target_name, sources in MERGES.items():
        print(f"\n  Creating {target_name} from {', '.join(sources)}")
        activates, skill_groups, refs = merge_gateways(target_name, sources)

        # Custom descriptions and titles
        meta = {
            "discover-infra": {
                "title": "Infrastructure & Cloud Skills Discovery",
                "description": "Automatically discover cloud, infrastructure, deployment, and container skills when working with AWS, GCP, Azure, Docker, Kubernetes, Terraform, Netlify, Heroku, serverless, or IaC",
            },
            "discover-distributed": {
                "title": "Distributed Systems & Realtime Skills Discovery",
                "description": "Automatically discover distributed systems and realtime communication skills when working with consensus, CRDTs, replication, WebSocket, SSE, pub/sub, or event-driven architectures",
            },
            "discover-systems-theory": {
                "title": "Systems Theory & Language Design Skills Discovery",
                "description": "Automatically discover eBPF, compiler, programming language theory, information retrieval, and formal verification skills when working with kernel tracing, parsers, type systems, Z3, Lean, or theorem proving",
            },
        }

        m = meta.get(target_name, {"title": target_name, "description": ""})
        content = build_gateway(
            name=target_name,
            description=m["description"],
            title=m["title"],
            activates_lines=activates,
            skill_groups=skill_groups,
            index_refs=refs,
            workflows=[],
        )

        target_dir = SKILLS_DIR / target_name
        if not args.dry_run:
            target_dir.mkdir(exist_ok=True)
            (target_dir / "SKILL.md").write_text(content, encoding="utf-8")
            print(f"  Wrote {target_dir.relative_to(REPO_ROOT)}/SKILL.md")
        else:
            print(f"  [DRY RUN] Would write {target_name}/SKILL.md ({len(content)} chars)")

        all_removed.extend(sources)

    # Process absorptions
    print("\n=== Processing Absorptions ===")
    for target_name, sources in ABSORPTIONS.items():
        print(f"\n  Absorbing {', '.join(sources)} into {target_name}")
        result = absorb_gateway(target_name, sources)

        target_path = SKILLS_DIR / target_name / "SKILL.md"
        text = target_path.read_text(encoding="utf-8")

        # Update the activates section
        activates_match = re.search(
            r'(## When This Skill Activates\n)(.*?)(\n## )', text, re.DOTALL
        )
        if activates_match:
            text = text[:activates_match.start(2)] + result["activates"] + text[activates_match.end(2):]

        # Update the skills section
        skills_match = re.search(
            r'(## Available Skills.*?\n)(.*?)(\n## (?:Load|Common|Progressive))', text, re.DOTALL
        )
        if skills_match:
            # Recount total
            total = count_skills_in_section(result["skills_section"])
            header_line = skills_match.group(1)
            # Update count in header
            header_line = re.sub(r'\(\d+ total\)', f'({total} total)', header_line)
            text = text[:skills_match.start(1)] + header_line + result["skills_section"] + text[skills_match.end(2):]

        # Update index refs section
        refs_match = re.search(
            r'(## Load Full Category Details\n)(.*?)(\n## )', text, re.DOTALL
        )
        if refs_match:
            new_refs = "\n".join(f"Read {ref}" for ref in result["index_refs"])
            text = text[:refs_match.start(2)] + new_refs + "\n" + text[refs_match.end(2):]

        # Update version in frontmatter
        text = re.sub(r'version: "3\.1"', 'version: "4.0"', text)

        if not args.dry_run:
            target_path.write_text(text, encoding="utf-8")
            print(f"  Updated {target_path.relative_to(REPO_ROOT)}")
        else:
            print(f"  [DRY RUN] Would update {target_name}/SKILL.md")

        all_removed.extend(sources)

    # Remove old gateway directories
    print("\n=== Removing Old Gateways ===")
    # Deduplicate and exclude targets
    to_remove = [gw for gw in set(all_removed)]
    remove_old_gateways(to_remove, dry_run=args.dry_run)

    print(f"\nConsolidated {40} gateways to {40 - len(to_remove)} gateways")
    print(f"Removed {len(to_remove)} old gateway directories")


if __name__ == "__main__":
    main()
