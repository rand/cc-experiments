#!/bin/bash

# Uninstall script for /skills slash command

INSTALL_PATH="$HOME/.claude/commands/skills.md"

echo "━━━ /skills Command Uninstaller ━━━"
echo ""

if [ ! -e "$INSTALL_PATH" ]; then
    echo "✓ /skills command is not installed"
    echo ""
    echo "Install location: $INSTALL_PATH"
    exit 0
fi

# Check type
if [ -L "$INSTALL_PATH" ]; then
    echo "Removing symlink: $INSTALL_PATH"
else
    echo "Removing file: $INSTALL_PATH"

    # Offer to show backup if it exists
    if [ -f "$INSTALL_PATH.backup" ]; then
        echo ""
        echo "Note: Backup exists at $INSTALL_PATH.backup"
    fi
fi

rm "$INSTALL_PATH"

echo "✓ /skills command removed"
echo ""
echo "To reinstall:"
echo "  cd /path/to/cc-experiments"
echo "  ./slash-commands/install.sh"
