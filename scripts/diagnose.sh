#!/usr/bin/env bash
# diagnose.sh - Comprehensive cc-polymath diagnostics
#
# Usage: bash <cc-polymath-root>/scripts/diagnose.sh [--verbose]
#
# This script performs comprehensive read-only diagnostics to help
# troubleshoot cc-polymath installation and configuration issues.
#
# Exit codes:
#   0 - No issues detected
#   1 - Issues found (see recommendations)

set -e

PLUGIN_DIR="$HOME/.claude/plugins/cc-polymath"
VERBOSE=false

if [ "$1" == "--verbose" ] || [ "$1" == "-v" ]; then
    VERBOSE=true
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  cc-polymath Diagnostic Report"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Section 1: System Information
echo "┌─ System Information"
echo "│"
echo "│ OS:        $(uname -s)"
echo "│ Version:   $(uname -r)"
echo "│ Shell:     $SHELL"
echo "│ User:      $USER"
echo "│ Home:      $HOME"
echo "│ Date:      $(date)"
echo "└─"
echo ""

# Section 2: Plugin Status
echo "┌─ Plugin Status"
echo "│"
if [ -d "$PLUGIN_DIR" ]; then
    echo "│ ✓ Plugin directory:  $PLUGIN_DIR"

    if [ -f "$PLUGIN_DIR/.claude-plugin/plugin.json" ]; then
        version=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$PLUGIN_DIR/.claude-plugin/plugin.json" | cut -d'"' -f4)
        echo "│ ✓ Version:           $version"
    else
        echo "│ ✗ plugin.json not found"
    fi

    # Count files
    skill_files=$(find "$PLUGIN_DIR/skills" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
    command_files=$(find "$PLUGIN_DIR/commands" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
    gateway_dirs=$(find "$PLUGIN_DIR/skills" -type d -name "discover-*" 2>/dev/null | wc -l | tr -d ' ')

    echo "│ ✓ Skill files:       $skill_files"
    echo "│ ✓ Command files:     $command_files"
    echo "│ ✓ Gateway skills:    $gateway_dirs"
else
    echo "│ ✗ Plugin not installed"
    echo "│   Install: /plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath"
fi
echo "└─"
echo ""

# Section 3: File Integrity
echo "┌─ File Integrity"
echo "│"
critical_files=(
    ".claude-plugin/plugin.json"
    "skills/README.md"
    "commands/skills.md"
    "skills/discover-api/SKILL.md"
    "skills/discover-frontend/SKILL.md"
    "skills/api/INDEX.md"
    "skills/database/INDEX.md"
    "docs/GETTING_STARTED.md"
    "scripts/verify-install.sh"
)

integrity_ok=true
for file in "${critical_files[@]}"; do
    if [ -f "$PLUGIN_DIR/$file" ]; then
        size=$(wc -c < "$PLUGIN_DIR/$file" 2>/dev/null | tr -d ' ')
        if $VERBOSE; then
            echo "│ ✓ $file ($size bytes)"
        fi
    else
        echo "│ ✗ Missing: $file"
        integrity_ok=false
    fi
done

if $integrity_ok; then
    echo "│ ✓ All critical files present"
else
    echo "│"
    echo "│ Some files are missing - reinstall may be needed"
fi
echo "└─"
echo ""

# Section 4: Path Resolution
echo "┌─ Path Resolution Analysis"
echo "│"
echo "│ Plugin install path: $PLUGIN_DIR/skills/"
echo "│"

# Check what paths are referenced in commands
if [ -f "$PLUGIN_DIR/commands/discover-api.md" ]; then
    path_in_cmd=$(grep -o '~/.claude/[^/]*/skills/' "$PLUGIN_DIR/commands/discover-api.md" 2>/dev/null | head -1)
    if [ -n "$path_in_cmd" ]; then
        echo "│ Path in commands:    $path_in_cmd"

        if [[ "$path_in_cmd" == *"/plugins/cc-polymath/skills/"* ]]; then
            echo "│ ✓ Command paths are correct"
        else
            echo "│ ✗ Command paths need updating"
            echo "│   Expected: <cc-polymath-root>/skills/"
            echo "│   Found:    $path_in_cmd"
        fi
    else
        echo "│ ⚠ Could not detect path references in commands"
    fi
else
    echo "│ ✗ Cannot check paths - discover-api.md not found"
fi
echo "└─"
echo ""

# Section 5: Old Installation Detection
echo "┌─ Legacy Installation Check"
echo "│"
if [ -d "$HOME/.claude/skills" ] && [ ! -L "$HOME/.claude/skills" ]; then
    echo "│ ⚠ Old manual installation detected"
    echo "│   Location: <cc-polymath-root>/skills/"
    echo "│"
    echo "│ Recommendation: Migrate to plugin"
    echo "│   See: $PLUGIN_DIR/MIGRATION.md"
else
    echo "│ ✓ No legacy installation conflicts"
fi
echo "└─"
echo ""

# Section 6: Permissions
echo "┌─ File Permissions"
echo "│"
permissions_ok=true

if [ -r "$PLUGIN_DIR/skills/README.md" ]; then
    echo "│ ✓ Skills readable"
else
    echo "│ ✗ Cannot read skills"
    echo "│   Fix: chmod -R u+rX $PLUGIN_DIR"
    permissions_ok=false
fi

if [ -r "$PLUGIN_DIR/commands/skills.md" ]; then
    echo "│ ✓ Commands readable"
else
    echo "│ ✗ Cannot read commands"
    echo "│   Fix: chmod -R u+rX $PLUGIN_DIR"
    permissions_ok=false
fi

if [ -x "$PLUGIN_DIR/scripts/verify-install.sh" ]; then
    echo "│ ✓ Scripts executable"
else
    if [ -f "$PLUGIN_DIR/scripts/verify-install.sh" ]; then
        echo "│ ⚠ Scripts not executable"
        echo "│   Fix: chmod +x $PLUGIN_DIR/scripts/*.sh"
    fi
fi
echo "└─"
echo ""

# Section 7: Sample Skill Test
echo "┌─ Sample Skill Test"
echo "│"
if [ -f "$PLUGIN_DIR/skills/discover-api/SKILL.md" ]; then
    line_count=$(wc -l < "$PLUGIN_DIR/skills/discover-api/SKILL.md" 2>/dev/null | tr -d ' ')
    echo "│ ✓ discover-api/SKILL.md loads"
    echo "│   Lines: $line_count"

    if [ "$line_count" -lt 50 ]; then
        echo "│ ⚠ Skill file seems truncated"
    fi
else
    echo "│ ✗ Cannot load sample skill"
fi
echo "└─"
echo ""

# Section 8: Plugin Configuration
echo "┌─ Plugin Configuration"
echo "│"
if [ -f "$PLUGIN_DIR/.claude-plugin/plugin.json" ]; then
    # Check for skills field (should not exist)
    if grep -q '"skills"' "$PLUGIN_DIR/.claude-plugin/plugin.json" 2>/dev/null; then
        echo "│ ⚠ plugin.json contains 'skills' field"
        echo "│   Note: Skills auto-discover without manifest registration"
        echo "│   Consider removing this field (per Claude Code docs)"
    else
        echo "│ ✓ plugin.json correctly configured"
    fi

    # Check for commands field (should exist)
    if grep -q '"commands"' "$PLUGIN_DIR/.claude-plugin/plugin.json" 2>/dev/null; then
        echo "│ ✓ Commands field present"
    else
        echo "│ ✗ Commands field missing"
    fi
else
    echo "│ ✗ plugin.json not found"
fi
echo "└─"
echo ""

# Verbose output
if $VERBOSE; then
    echo "┌─ Detailed File Listing"
    echo "│"
    echo "│ Gateway Skills:"
    find "$PLUGIN_DIR/skills" -type d -name "discover-*" 2>/dev/null | while read -r dir; do
        echo "│   $(basename "$dir")"
    done
    echo "│"
    echo "│ Categories:"
    find "$PLUGIN_DIR/skills" -type f -name "INDEX.md" 2>/dev/null | while read -r file; do
        category=$(dirname "$file" | xargs basename)
        skill_count=$(grep -c "^##" "$file" 2>/dev/null || echo "?")
        echo "│   $category ($skill_count skills)"
    done
    echo "│"
    echo "│ Documentation Files:"
    if [ -d "$PLUGIN_DIR/docs" ]; then
        find "$PLUGIN_DIR/docs" -name "*.md" -type f 2>/dev/null | while read -r file; do
            echo "│   $(basename "$file")"
        done
    else
        echo "│   (docs/ directory not found)"
    fi
    echo "└─"
    echo ""
fi

# Section 9: Recommendations
echo "┌─ Recommendations"
echo "│"

recommendations=()

if [ ! -d "$PLUGIN_DIR" ]; then
    recommendations+=("Install plugin: /plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath")
fi

if [ -d "$HOME/.claude/skills" ] && [ ! -L "$HOME/.claude/skills" ]; then
    recommendations+=("Migrate from manual installation (see MIGRATION.md)")
fi

if ! $integrity_ok; then
    recommendations+=("Reinstall plugin to fix missing files")
fi

if ! $permissions_ok; then
    recommendations+=("Fix file permissions: chmod -R u+rX $PLUGIN_DIR")
fi

if [ ${#recommendations[@]} -eq 0 ]; then
    echo "│ ✓ No issues detected"
    echo "│"
    echo "│ Your cc-polymath installation looks good!"
else
    for rec in "${recommendations[@]}"; do
        echo "│ → $rec"
    done
fi
echo "└─"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  End of Diagnostic Report"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ${#recommendations[@]} -gt 0 ]; then
    echo "For detailed solutions, see:"
    echo "  $PLUGIN_DIR/docs/TROUBLESHOOTING.md"
    exit 1
else
    echo "For usage examples, see:"
    echo "  $PLUGIN_DIR/docs/GETTING_STARTED.md"
    echo "  $PLUGIN_DIR/docs/FIRST_CONVERSATIONS.md"
    exit 0
fi
