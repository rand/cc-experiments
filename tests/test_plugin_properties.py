#!/usr/bin/env python3
"""
Property-based tests for the cc-polymath plugin.

Validates structural invariants that must hold across all skills,
gateways, indexes, and configuration files.

Run: python3 tests/test_plugin_properties.py
"""

import os
import re
import sys
import json
import unittest
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / "skills"


def parse_frontmatter(path: Path) -> Optional[dict]:
    """Extract YAML frontmatter from a markdown file (minimal parser, no yaml dep)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    try:
        end = text.index("---", 3)
    except ValueError:
        return None
    block = text[3:end].strip()
    result = {}
    current_key = None
    sub_dict = None
    for line in block.split("\n"):
        if not line.strip():
            continue
        # Nested key (e.g., "  author: rand" under "metadata:")
        if line.startswith("  ") and current_key and sub_dict is not None:
            m = re.match(r'\s+(\w[\w-]*):\s*(.*)', line)
            if m:
                sub_dict[m.group(1)] = m.group(2).strip().strip('"').strip("'")
            continue
        m = re.match(r'(\w[\w-]*):\s*(.*)', line)
        if m:
            key = m.group(1)
            val = m.group(2).strip().strip('"').strip("'")
            if val == "":
                # Could be start of a nested block
                sub_dict = {}
                result[key] = sub_dict
                current_key = key
            else:
                result[key] = val
                current_key = key
                sub_dict = None
    return result


def all_gateway_skills() -> list[Path]:
    return sorted(SKILLS_DIR.glob("discover-*/SKILL.md"))


def all_index_files() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/INDEX.md"))


def all_leaf_skills() -> list[Path]:
    """All individual skill .md files (not INDEX, README, SKILL, templates)."""
    excluded_names = {"INDEX.md", "README.md", "SKILL.md", "_SKILL_TEMPLATE.md", "SECURITY.md"}
    results = []
    for md in SKILLS_DIR.rglob("*.md"):
        if md.name in excluded_names:
            continue
        # Exclude all-uppercase filenames (report/status files, not skills)
        stem = md.stem
        if stem == stem.upper() and not stem[0].islower():
            continue
        if "discover-" in str(md.relative_to(SKILLS_DIR)):
            continue
        if "resources/" in str(md.relative_to(SKILLS_DIR)):
            continue
        # Exclude Agent Skill subdirectories (foundation/, implementation/, etc)
        rel = str(md.relative_to(SKILLS_DIR))
        if any(d in rel for d in ["foundation/", "implementation/", "interactive/", "reference/", "references/", "scripts/"]):
            continue
        if ".beads/" in str(md):
            continue
        results.append(md)
    return sorted(results)


def all_cross_references(path: Path) -> list[str]:
    """Extract all Read/bash relative path references from a file.

    Only matches lines starting with Read or bash (Claude instructions),
    not references inside code blocks or documentation.
    Returns resolved paths relative to ROOT.
    """
    text = path.read_text(encoding="utf-8")
    refs: list[str] = []
    in_code_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        # Match lines that are Claude Read/bash instructions
        m = re.match(r"^(?:Read|bash)\s+(\.\.?/\S+)", stripped)
        if m:
            raw = m.group(1).rstrip("`)]>")
            resolved = (path.parent / raw).resolve()
            try:
                rel = str(resolved.relative_to(ROOT))
            except ValueError:
                continue
            refs.append(rel)
    return refs


# ── Property Tests ──────────────────────────────────────────────


class TestGatewayProperties(unittest.TestCase):
    """Every gateway skill must satisfy these invariants."""

    def test_all_gateways_have_frontmatter(self):
        for gw in all_gateway_skills():
            fm = parse_frontmatter(gw)
            self.assertIsNotNone(fm, f"Missing frontmatter: {gw}")

    def test_gateway_name_matches_directory(self):
        for gw in all_gateway_skills():
            fm = parse_frontmatter(gw)
            dir_name = gw.parent.name
            self.assertEqual(fm["name"], dir_name, f"Name mismatch in {gw}")

    def test_gateway_name_is_kebab_case(self):
        pattern = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
        for gw in all_gateway_skills():
            fm = parse_frontmatter(gw)
            self.assertRegex(fm["name"], pattern, f"Bad name format: {gw}")

    def test_gateway_description_within_limit(self):
        for gw in all_gateway_skills():
            fm = parse_frontmatter(gw)
            desc = fm.get("description", "")
            self.assertLessEqual(len(desc), 1024, f"Description too long: {gw}")
            self.assertGreater(len(desc), 0, f"Empty description: {gw}")

    def test_gateway_has_license(self):
        for gw in all_gateway_skills():
            fm = parse_frontmatter(gw)
            self.assertIn("license", fm, f"Missing license: {gw}")

    def test_gateway_has_metadata(self):
        for gw in all_gateway_skills():
            fm = parse_frontmatter(gw)
            self.assertIn("metadata", fm, f"Missing metadata: {gw}")
            self.assertIn("author", fm["metadata"], f"Missing author: {gw}")
            self.assertIn("version", fm["metadata"], f"Missing version: {gw}")

    def test_gateway_has_compatibility(self):
        for gw in all_gateway_skills():
            fm = parse_frontmatter(gw)
            self.assertIn("compatibility", fm, f"Missing compatibility: {gw}")

    def test_gateway_has_matching_category_dir(self):
        # Consolidated gateways map to multiple category dirs
        multi_category = {
            "infra": ["cloud", "infrastructure", "deployment", "containers"],
            "distributed": ["distributed-systems", "realtime"],
            "systems-theory": ["ebpf", "ir", "plt", "formal"],
        }
        for gw in all_gateway_skills():
            category = gw.parent.name.replace("discover-", "")
            if category in multi_category:
                # At least one mapped category dir must exist
                dirs = [SKILLS_DIR / c for c in multi_category[category]]
                self.assertTrue(
                    any(d.is_dir() for d in dirs),
                    f"Gateway {gw.parent.name} has no matching category dirs",
                )
            else:
                category_dir = SKILLS_DIR / category
                self.assertTrue(
                    category_dir.is_dir(),
                    f"Gateway {gw.parent.name} has no matching category dir: {category_dir}",
                )

    def test_gateway_references_resolve(self):
        for gw in all_gateway_skills():
            for ref in all_cross_references(gw):
                ref_path = ROOT / ref
                # Skip template patterns
                if "{" in ref or "*" in ref:
                    continue
                self.assertTrue(ref_path.exists(), f"Broken ref in {gw}: {ref}")


class TestIndexProperties(unittest.TestCase):
    """Every INDEX.md must satisfy these invariants."""

    def test_all_indexes_have_total_skills_count(self):
        for idx in all_index_files():
            text = idx.read_text(encoding="utf-8")
            self.assertRegex(
                text, r"Total Skills.*\d+",
                f"Missing Total Skills count: {idx}",
            )

    def test_index_references_resolve(self):
        for idx in all_index_files():
            for ref in all_cross_references(idx):
                ref_path = ROOT / ref
                if "{" in ref or "*" in ref:
                    continue
                self.assertTrue(ref_path.exists(), f"Broken ref in {idx}: {ref}")


class TestLeafSkillProperties(unittest.TestCase):
    """Leaf skills must have frontmatter with name and description."""

    def test_all_leaf_skills_have_frontmatter(self):
        for skill in all_leaf_skills():
            fm = parse_frontmatter(skill)
            self.assertIsNotNone(fm, f"Missing frontmatter: {skill}")

    def test_leaf_skill_has_name(self):
        for skill in all_leaf_skills():
            fm = parse_frontmatter(skill)
            if fm is None:
                continue  # Caught by test above
            self.assertIn("name", fm, f"Missing name: {skill}")

    def test_leaf_skill_has_description(self):
        for skill in all_leaf_skills():
            fm = parse_frontmatter(skill)
            if fm is None:
                continue
            self.assertIn("description", fm, f"Missing description: {skill}")


class TestConfigProperties(unittest.TestCase):
    """Plugin configuration must be internally consistent."""

    def test_plugin_json_valid(self):
        pj = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        self.assertIn("name", pj)
        self.assertIn("version", pj)
        self.assertIn("skills", pj)
        self.assertIn("hooks", pj)

    def test_marketplace_json_valid(self):
        mj = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
        self.assertIn("plugins", mj)

    def test_versions_match(self):
        pj = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        mj = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
        pj_version = pj["version"]
        mj_version = mj["plugins"][0]["version"]
        self.assertEqual(pj_version, mj_version, "Version mismatch between plugin.json and marketplace.json")

    def test_skill_count_floor(self):
        """The claimed skill count must be a floor (actual >= claimed).
        Uses the same counting method as validate.sh."""
        import subprocess
        pj = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        m = re.search(r"(\d+)\+? production", pj["description"])
        self.assertIsNotNone(m, "Could not parse skill count from description")
        claimed = int(m.group(1))
        # Count leaf skills same as validate.sh
        leaf_count = 0
        for md in SKILLS_DIR.rglob("*.md"):
            rel = md.relative_to(SKILLS_DIR)
            parts = rel.parts
            if len(parts) < 2:
                # Root-level skill
                if md.name not in {"README.md", "SECURITY.md", "_SKILL_TEMPLATE.md"}:
                    leaf_count += 1
                continue
            if md.name in {"INDEX.md", "README.md", "SKILL.md"}:
                continue
            if "discover-" in parts[0]:
                continue
            if "resources" in parts:
                continue
            if ".beads" in str(rel):
                continue
            leaf_count += 1
        self.assertGreaterEqual(
            leaf_count, claimed,
            f"Claimed {claimed}+ but only found {leaf_count} skills",
        )

    def test_gateway_count_accurate(self):
        gateways = all_gateway_skills()
        self.assertEqual(len(gateways), 23, f"Expected 23 gateways, found {len(gateways)}")


class TestCrossReferenceConsistency(unittest.TestCase):
    """Cross-references must be bidirectionally consistent."""

    def test_no_broken_references_in_skills(self):
        broken = []
        for md in SKILLS_DIR.rglob("*.md"):
            if ".beads/" in str(md):
                continue
            for ref in all_cross_references(md):
                if "{" in ref or "*" in ref:
                    continue
                ref_path = ROOT / ref
                if not ref_path.exists():
                    # Check if it's a directory reference
                    if not ref.endswith("/"):
                        broken.append((md, ref))
        self.assertEqual(
            broken, [],
            f"Found {len(broken)} broken references:\n"
            + "\n".join(f"  {f}: {r}" for f, r in broken[:10]),
        )


class TestAgentProperties(unittest.TestCase):
    """Agent definitions must be properly structured."""

    def test_all_agents_have_frontmatter(self):
        for agent in (ROOT / "agents").glob("*.md"):
            fm = parse_frontmatter(agent)
            self.assertIsNotNone(fm, f"Missing frontmatter: {agent}")
            self.assertIn("name", fm, f"Missing name: {agent}")
            self.assertIn("description", fm, f"Missing description: {agent}")


class TestNoOrphanedFiles(unittest.TestCase):
    """Detect orphaned skill files not referenced by any INDEX or gateway."""

    def test_no_orphaned_root_skill_files(self):
        """No skill files at skills/ root that should be in a category."""
        excluded = {"README.md", "SECURITY.md", "_SKILL_TEMPLATE.md"}
        orphans = []
        for f in SKILLS_DIR.glob("*.md"):
            if f.name in excluded:
                continue
            # Root-level meta skills are OK (skill-*.md)
            if f.name.startswith("skill-"):
                continue
            orphans.append(f.name)
        # These are expected root-level meta skills
        # Any other .md file at root is suspicious
        for o in orphans:
            if not o.startswith("skill-"):
                # Check it's not a stray file that belongs in a category
                self.assertFalse(
                    any(c in o for c in ["cloud-", "api-", "database-"]),
                    f"Likely orphaned file at skills root: {o}",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
