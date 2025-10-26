#!/bin/bash

# Install script for /skills slash command
# Non-destructive installation for Claude Code

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMAND_FILE="$SCRIPT_DIR/skills.md"
INSTALL_DIR="$HOME/.claude/commands"
INSTALL_PATH="$INSTALL_DIR/skills.md"

echo "━━━ /skills Slash Command Installer ━━━"
echo ""

# Check if skills.md exists in this directory
if [ ! -f "$COMMAND_FILE" ]; then
    # Check if we're already in the commands directory
    if [ -f "$HOME/.claude/commands/skills.md" ]; then
        echo "✓ /skills command is already installed!"
        echo ""
        echo "Location: $HOME/.claude/commands/skills.md"
        echo ""
        echo "Try it: /skills"
        exit 0
    fi

    echo "✗ Error: skills.md not found in current directory"
    echo ""
    echo "Please run this script from the cc-slash-skill directory:"
    echo "  cd /path/to/cc-slash-skill"
    echo "  ./install.sh"
    exit 1
fi

# Create commands directory if it doesn't exist
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Creating commands directory: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
fi

# Check if already installed
if [ -f "$INSTALL_PATH" ]; then
    echo "⚠ /skills command is already installed"
    echo ""
    read -p "Overwrite existing installation? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled"
        exit 0
    fi
    echo "Backing up existing file to skills.md.backup"
    cp "$INSTALL_PATH" "$INSTALL_PATH.backup"
fi

# Install the command
echo "Installing /skills command..."
cp "$COMMAND_FILE" "$INSTALL_PATH"

# Verify installation
if [ -f "$INSTALL_PATH" ]; then
    echo ""
    echo "✓ Successfully installed!"
    echo ""
    echo "Location: $INSTALL_PATH"
    echo "Size: $(wc -c < "$INSTALL_PATH") bytes"
    echo ""
    echo "━━━ Next Steps ━━━"
    echo ""
    echo "1. Restart your Claude Code session (if running)"
    echo "2. Try the command:"
    echo "   /skills              # Context-aware recommendations"
    echo "   /skills frontend     # Browse category"
    echo "   /skills postgres     # Search for skills"
    echo "   /skills list         # All categories"
    echo ""
    echo "Documentation: $SCRIPT_DIR/README.md"
    echo "Uninstall: ./uninstall.sh"
    echo ""
else
    echo "✗ Installation failed"
    exit 1
fi
