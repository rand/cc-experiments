#!/bin/bash
# cc-polymath v3.0.0 validation script
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ERRORS=0
WARNINGS=0

pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; ERRORS=$((ERRORS + 1)); }
warn() { echo "  ⚠ $1"; WARNINGS=$((WARNINGS + 1)); }

echo "=== cc-polymath validation ==="
echo ""

# 1. No old hardcoded paths (exclude this script itself and tests/)
echo "1. Checking for old hardcoded paths..."
PAT1='~/.claude/skills/'
PAT2='~/.claude/plugins/cc-polymath/'
OLD_SKILLS=$(grep -r "$PAT1" --include="*.md" --include="*.sh" . 2>/dev/null | grep -v '.git/' | grep -v '.reasoning_logs/' | grep -v 'tests/' | wc -l | tr -d ' ')
OLD_PLUGIN=$(grep -r "$PAT2" --include="*.md" --include="*.sh" . 2>/dev/null | grep -v '.git/' | grep -v '.reasoning_logs/' | grep -v 'tests/' | wc -l | tr -d ' ')
if [ "$OLD_SKILLS" -eq 0 ] && [ "$OLD_PLUGIN" -eq 0 ]; then
  pass "No old hardcoded paths found"
else
  fail "Found $OLD_SKILLS old skills refs and $OLD_PLUGIN old plugin refs"
fi

# 2. plugin.json is valid
echo "2. Checking plugin.json..."
if python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))" 2>/dev/null; then
  pass "plugin.json is valid JSON"
else
  fail "plugin.json is invalid JSON"
fi
if python3 -c "import json; d=json.load(open('.claude-plugin/plugin.json')); assert d.get('hooks',{}).get('SessionStart'), 'missing'" 2>/dev/null; then
  pass "SessionStart hook present"
else
  fail "SessionStart hook missing from plugin.json"
fi
VERSION=$(python3 -c "import json; print(json.load(open('.claude-plugin/plugin.json'))['version'])" 2>/dev/null)
if [ "$VERSION" = "3.0.0" ]; then
  pass "Version is 3.0.0"
else
  fail "Version is $VERSION, expected 3.0.0"
fi

# 3. marketplace.json is valid and matches
echo "3. Checking marketplace.json..."
if python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))" 2>/dev/null; then
  pass "marketplace.json is valid JSON"
else
  fail "marketplace.json is invalid JSON"
fi
MKT_VERSION=$(python3 -c "import json; print(json.load(open('.claude-plugin/marketplace.json'))['plugins'][0]['version'])" 2>/dev/null)
if [ "$MKT_VERSION" = "3.0.0" ]; then
  pass "marketplace.json version matches (3.0.0)"
else
  fail "marketplace.json version is $MKT_VERSION, expected 3.0.0"
fi

# 4. Cross-reference validation
echo "4. Checking cross-references..."
BROKEN_COUNT=$(python3 -c "
import re, os
broken = []
files = []
for d in ['skills', 'commands', 'docs']:
    for dp, dn, fns in os.walk(d):
        files.extend(os.path.join(dp, f) for f in fns if f.endswith('.md'))
for f in files:
    with open(f) as fh:
        for i, line in enumerate(fh, 1):
            for m in re.finditer(r'<cc-polymath-root>/(\S+\.md)', line):
                path = m.group(1)
                if '{' in path or '[' in path or '*' in path:
                    continue
                if not os.path.isfile(path):
                    broken.append(f'{f}:{i} -> {path}')
                    print(f'    BROKEN: {f}:{i} -> {path}')
print(len(broken))
" 2>/dev/null | tail -1)
if [ "$BROKEN_COUNT" = "0" ]; then
  pass "All cross-references resolve"
else
  fail "$BROKEN_COUNT broken cross-references"
fi

# 5. Gateway structure
echo "5. Checking gateway structure..."
GATEWAY_COUNT=$(ls -d skills/discover-*/SKILL.md 2>/dev/null | wc -l | tr -d ' ')
pass "$GATEWAY_COUNT gateway skills found"
MISSING_CAT=0
for gw in skills/discover-*/SKILL.md; do
  dir=$(dirname "$gw")
  cat_name=$(basename "$dir" | sed 's/discover-//')
  if [ ! -d "skills/$cat_name" ]; then
    fail "Gateway $dir has no category dir skills/$cat_name/"
    MISSING_CAT=$((MISSING_CAT + 1))
  fi
done
if [ "$MISSING_CAT" -eq 0 ]; then
  pass "All gateways have matching category directories"
fi

# 6. Frontmatter validation
echo "6. Checking gateway frontmatter..."
MISSING_FM=0
for gw in skills/discover-*/SKILL.md; do
  if ! head -1 "$gw" | grep -q '^---$'; then
    fail "Missing frontmatter: $gw"
    MISSING_FM=$((MISSING_FM + 1))
  fi
done
if [ "$MISSING_FM" -eq 0 ]; then
  pass "All gateways have YAML frontmatter"
fi

# 7. Skill counts
echo "7. Checking skill counts..."
LEAF_SKILLS=$(find skills -mindepth 2 -name "*.md" \
  -not -name "INDEX.md" -not -name "README.md" -not -name "SKILL.md" \
  -not -path "*/discover-*/*" -not -path "*/resources/*" | wc -l | tr -d ' ')
ROOT_SKILLS=$(find skills -maxdepth 1 -name "*.md" \
  -not -name "README.md" -not -name "SECURITY.md" -not -name "_SKILL_TEMPLATE.md" | wc -l | tr -d ' ')
TOTAL=$((LEAF_SKILLS + ROOT_SKILLS))
pass "$TOTAL total skills ($LEAF_SKILLS in categories + $ROOT_SKILLS root-level)"

CLAIMED=$(python3 -c "
import json, re
d = json.load(open('.claude-plugin/plugin.json'))
m = re.search(r'(\d+) production', d['description'])
print(m.group(1) if m else 'unknown')
" 2>/dev/null)
if [ "$CLAIMED" = "$TOTAL" ]; then
  pass "plugin.json claims $CLAIMED skills — matches actual"
else
  warn "plugin.json claims $CLAIMED skills but actual is $TOTAL"
fi

# 8. No redundant discover commands
echo "8. Checking commands directory..."
DISCOVER_CMDS=$(ls commands/discover-*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$DISCOVER_CMDS" -eq 0 ]; then
  pass "No redundant discover-*.md commands"
else
  warn "$DISCOVER_CMDS redundant discover commands still present"
fi
if [ -f commands/skills.md ]; then
  pass "commands/skills.md exists"
else
  fail "commands/skills.md missing"
fi

# 9. No stale count references
echo "9. Checking for stale skill count references..."
STALE_447=$(grep -r '\b447\b' --include="*.md" . 2>/dev/null | grep -v '.git/' | grep -v '.reasoning_logs/' | wc -l | tr -d ' ')
if [ "$STALE_447" -eq 0 ]; then
  pass "No stale 447 skill count references"
else
  warn "$STALE_447 references to old count 447"
fi

# Summary
echo ""
echo "=== Results ==="
echo "Errors:   $ERRORS"
echo "Warnings: $WARNINGS"
if [ "$ERRORS" -eq 0 ]; then
  echo "PASS ✓"
  exit 0
else
  echo "FAIL ✗"
  exit 1
fi
