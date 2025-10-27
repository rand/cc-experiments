#!/bin/bash

# Install script for /skills slash command
# Integrated with cc-polymath gateway architecture

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMAND_FILE="$REPO_ROOT/slash-commands/skills/skills.md"
SKILLS_CATALOG="$REPO_ROOT/skills/README.md"
INSTALL_DIR="$HOME/.claude/commands"

echo "━━━ /skills Command Installer ━━━"
echo ""

# Validate repository structure
if [ ! -f "$COMMAND_FILE" ]; then
    echo "✗ Error: Command file not found"
    echo "  Expected: $COMMAND_FILE"
    echo ""
    echo "Please run this installer from the cc-polymath repository root:"
    echo "  cd /path/to/cc-polymath"
    echo "  ./slash-commands/install.sh"
    exit 1
fi

if [ ! -f "$SKILLS_CATALOG" ]; then
    echo "✗ Error: Skills catalog not found"
    echo "  Expected: $SKILLS_CATALOG"
    echo ""
    echo "This installer must be run from cc-polymath repository."
    echo "The gateway architecture requires skills/README.md"
    exit 1
fi

# Verify gateway architecture
GATEWAY_COUNT=$(find "$REPO_ROOT/skills" -name "discover-*" -type d 2>/dev/null | wc -l | tr -d ' ')
if [ "$GATEWAY_COUNT" -lt 26 ]; then
    echo "⚠ Warning: Expected ~28 gateway skills, found $GATEWAY_COUNT"
    echo "  Gateway architecture may not be fully set up"
    echo ""
fi

# Check for _INDEX.md.archive (confirms new architecture)
if [ ! -f "$REPO_ROOT/skills/_INDEX.md.archive" ]; then
    echo "⚠ Warning: Old architecture detected"
    echo "  skills/_INDEX.md.archive not found"
    echo "  The /skills command expects the gateway architecture"
    echo ""
fi

# Create commands directory
mkdir -p "$INSTALL_DIR"

# Check if already installed
if [ -f "$INSTALL_DIR/skills.md" ]; then
    echo "⚠ /skills command is already installed"
    echo ""
    read -p "Overwrite existing installation? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled"
        exit 0
    fi

    # Backup existing
    if [ -L "$INSTALL_DIR/skills.md" ]; then
        echo "Removing existing symlink..."
    else
        echo "Backing up existing file to skills.md.backup..."
        cp "$INSTALL_DIR/skills.md" "$INSTALL_DIR/skills.md.backup"
    fi
    rm "$INSTALL_DIR/skills.md"
fi

# Try symlink first (enables auto-updates)
if ln -sf "$COMMAND_FILE" "$INSTALL_DIR/skills.md" 2>/dev/null; then
    echo "✓ Symlinked /skills command"
    echo "  Auto-updates enabled: changes in repo reflect immediately"
else
    cp "$COMMAND_FILE" "$INSTALL_DIR/skills.md"
    echo "✓ Copied /skills command"
    echo "  Note: Re-run installer after updating skills.md in repo"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Installation complete!"
echo ""
echo "Skills Architecture:"
echo "  292 skills across 31 categories"
echo "  28 gateway skills for auto-discovery"
echo "  Progressive loading (60-84% context reduction)"
echo ""
echo "Usage:"
echo "  /skills              # Browse all skills and categories"
echo "  /skills api          # View API skills gateway"
echo "  /skills frontend     # View frontend skills"
echo "  /skills diagrams     # View diagram/Mermaid skills"
echo "  /skills ml           # View ML/AI skills"
echo "  /skills postgres     # Search for Postgres skills"
echo "  /skills list         # Show all categories"
echo ""
echo "Progressive loading: Gateway → Category → Skill"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
