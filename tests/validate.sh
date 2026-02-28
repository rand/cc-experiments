#!/bin/bash
# cc-polymath v4.0.0 validation script
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
if [ "$VERSION" = "4.0.0" ]; then
  pass "Version is 4.0.0"
else
  fail "Version is $VERSION, expected 4.0.0"
fi

# 3. marketplace.json is valid and matches
echo "3. Checking marketplace.json..."
if python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))" 2>/dev/null; then
  pass "marketplace.json is valid JSON"
else
  fail "marketplace.json is invalid JSON"
fi
MKT_VERSION=$(python3 -c "import json; print(json.load(open('.claude-plugin/marketplace.json'))['plugins'][0]['version'])" 2>/dev/null)
if [ "$MKT_VERSION" = "4.0.0" ]; then
  pass "marketplace.json version matches (4.0.0)"
else
  fail "marketplace.json version is $MKT_VERSION, expected 4.0.0"
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
    fdir = os.path.dirname(f)
    with open(f) as fh:
        for i, line in enumerate(fh, 1):
            for m in re.finditer(r'(?:Read|bash)\s+(\.\./[^\s\)\]\>]+\.(?:md|sh|py))', line):
                relpath = m.group(1)
                if '{' in relpath or '[' in relpath or '*' in relpath:
                    continue
                abspath = os.path.normpath(os.path.join(fdir, relpath))
                if not os.path.isfile(abspath):
                    broken.append(f'{f}:{i} -> {relpath}')
                    print(f'    BROKEN: {f}:{i} -> {relpath}')
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
  # Consolidated gateways map to multiple category dirs
  case "$cat_name" in
    infra) cats="cloud infrastructure deployment containers" ;;
    distributed) cats="distributed-systems realtime" ;;
    systems-theory) cats="ebpf ir plt formal" ;;
    *) cats="$cat_name" ;;
  esac
  found=0
  for c in $cats; do
    if [ -d "skills/$c" ]; then
      found=1
      break
    fi
  done
  if [ "$found" -eq 0 ]; then
    fail "Gateway $dir has no category dir"
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

# 7. Agent Skills spec compliance
echo "7. Checking Agent Skills spec compliance..."
SPEC_FAIL=0
for gw in skills/discover-*/SKILL.md; do
  NAME=$(python3 -c "
import re
text = open('$gw').read()
m = re.search(r'^name:\s*(.+)$', text, re.M)
print(m.group(1).strip() if m else '')
" 2>/dev/null)
  DESC=$(python3 -c "
import re
text = open('$gw').read()
m = re.search(r'^description:\s*(.+)$', text, re.M)
print(m.group(1).strip() if m else '')
" 2>/dev/null)
  # Name must be kebab-case, 1-64 chars
  if [ -z "$NAME" ]; then
    fail "Missing name: $gw"
    SPEC_FAIL=$((SPEC_FAIL + 1))
  elif ! echo "$NAME" | grep -qE '^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'; then
    fail "Name not kebab-case: $gw ($NAME)"
    SPEC_FAIL=$((SPEC_FAIL + 1))
  elif [ ${#NAME} -gt 64 ]; then
    fail "Name >64 chars: $gw ($NAME)"
    SPEC_FAIL=$((SPEC_FAIL + 1))
  fi
  # Description must exist and be ≤1024 chars
  if [ -z "$DESC" ]; then
    fail "Missing description: $gw"
    SPEC_FAIL=$((SPEC_FAIL + 1))
  elif [ ${#DESC} -gt 1024 ]; then
    warn "Description >1024 chars: $gw (${#DESC} chars)"
  fi
  # Check for required spec fields
  if ! grep -q '^license:' "$gw"; then
    fail "Missing license field: $gw"
    SPEC_FAIL=$((SPEC_FAIL + 1))
  fi
  if ! grep -q '^metadata:' "$gw"; then
    fail "Missing metadata block: $gw"
    SPEC_FAIL=$((SPEC_FAIL + 1))
  fi
done
if [ "$SPEC_FAIL" -eq 0 ]; then
  pass "All gateways pass Agent Skills spec checks"
fi

# 8. Skill counts
echo "8. Checking skill counts..."
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
m = re.search(r'(\d+)\+? production', d['description'])
print(m.group(1) if m else 'unknown')
" 2>/dev/null)
if [ "$CLAIMED" = "unknown" ]; then
  warn "Could not parse skill count from plugin.json description"
elif [ "$TOTAL" -ge "$CLAIMED" ]; then
  pass "plugin.json claims ${CLAIMED}+ skills — actual is $TOTAL"
else
  warn "plugin.json claims ${CLAIMED}+ skills but actual is only $TOTAL"
fi

# 9. No redundant discover commands
echo "9. Checking commands directory..."
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

# 10. No stale count references
echo "10. Checking for stale skill count references..."
STALE_447=$(grep -r '\b447\b' --include="*.md" . 2>/dev/null | grep -v '.git/' | grep -v '.reasoning_logs/' | grep -v 'node_modules/' | wc -l | tr -d ' ')
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
