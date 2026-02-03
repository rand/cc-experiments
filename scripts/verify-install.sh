#!/usr/bin/env bash
# verify-install.sh - Verify cc-polymath plugin installation
#
# Usage: bash <cc-polymath-root>/scripts/verify-install.sh
#
# This script performs read-only checks to verify that cc-polymath is
# installed correctly. It checks for:
# - Plugin directory existence
# - Critical files presence
# - Gateway skills accessibility
# - Skills catalog readability
# - Old manual installation conflicts
# - File permissions
#
# Exit codes:
#   0 - Installation verified successfully
#   1 - Installation has issues

set -e

PLUGIN_DIR="$HOME/.claude/plugins/cc-polymath"
PASSED=0
FAILED=0

echo "━━━ cc-polymath Installation Verification ━━━"
echo ""

# Check 1: Plugin directory exists
if [ -d "$PLUGIN_DIR" ]; then
    echo "✓ Plugin directory exists"
    ((PASSED++))
else
    echo "✗ Plugin directory not found: $PLUGIN_DIR"
    echo "  Run: /plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath"
    ((FAILED++))
    echo ""
    echo "━━━ Summary ━━━"
    echo "Passed: $PASSED"
    echo "Failed: $FAILED"
    exit 1
fi

# Check 2: Critical files present
files=(
    ".claude-plugin/plugin.json"
    "skills/README.md"
    "commands/skills.md"
)

for file in "${files[@]}"; do
    if [ -f "$PLUGIN_DIR/$file" ]; then
        echo "✓ Found $file"
        ((PASSED++))
    else
        echo "✗ Missing $file"
        ((FAILED++))
    fi
done

# Check 3: Gateway skills accessible
gateway_count=$(find "$PLUGIN_DIR/skills" -type d -name "discover-*" 2>/dev/null | wc -l | tr -d ' ')
if [ "$gateway_count" -ge 25 ]; then
    echo "✓ Found $gateway_count gateway skills"
    ((PASSED++))
else
    echo "⚠ Only found $gateway_count gateway skills (expected 28+)"
    ((FAILED++))
fi

# Check 4: Skills catalog readable
if [ -r "$PLUGIN_DIR/skills/README.md" ]; then
    # Count category headers (### in markdown)
    skill_count=$(grep -c "^###" "$PLUGIN_DIR/skills/README.md" 2>/dev/null || echo "0")
    echo "✓ Skills catalog readable ($skill_count categories)"
    ((PASSED++))
else
    echo "✗ Cannot read skills catalog"
    ((FAILED++))
fi

# Check 5: No old manual installation conflict
if [ -d "$HOME/.claude/skills" ] && [ ! -L "$HOME/.claude/skills" ]; then
    echo "⚠ Old manual installation detected at <cc-polymath-root>/skills/"
    echo "  Consider migrating: see MIGRATION.md"
    echo "  This may cause conflicts with plugin installation"
    # Not a failure, just a warning
fi

# Check 6: File permissions
if [ -r "$PLUGIN_DIR/commands/skills.md" ]; then
    echo "✓ File permissions OK"
    ((PASSED++))
else
    echo "✗ Permission issue - cannot read files"
    echo "  Fix: chmod -R u+rX $PLUGIN_DIR"
    ((FAILED++))
fi

# Summary
echo ""
echo "━━━ Summary ━━━"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✓ Installation verified successfully!"
    echo ""
    echo "Next steps:"
    echo "  • Try: /skills"
    echo "  • Read: $PLUGIN_DIR/docs/GETTING_STARTED.md"
    echo "  • Examples: $PLUGIN_DIR/docs/FIRST_CONVERSATIONS.md"
    exit 0
else
    echo "✗ Installation has issues. See errors above."
    echo ""
    echo "Try reinstalling:"
    echo "  /plugin uninstall cc-polymath"
    echo "  /plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath"
    echo ""
    echo "For more help:"
    echo "  • Troubleshooting: $PLUGIN_DIR/docs/TROUBLESHOOTING.md"
    echo "  • Diagnostics: bash $PLUGIN_DIR/scripts/diagnose.sh"
    exit 1
fi
