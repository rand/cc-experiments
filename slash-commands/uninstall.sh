#!/bin/bash

# Uninstall script for /skills slash command
# Clean, complete removal with no traces

set -e

INSTALL_PATH="$HOME/.claude/commands/skills.md"
BACKUP_PATH="$INSTALL_PATH.backup"

echo "━━━ /skills Slash Command Uninstaller ━━━"
echo ""

# Check if installed
if [ ! -f "$INSTALL_PATH" ]; then
    echo "✓ /skills command is not installed"
    echo ""
    echo "Nothing to uninstall."
    exit 0
fi

# Show what will be removed
echo "The following will be removed:"
echo "  - $INSTALL_PATH"
if [ -f "$BACKUP_PATH" ]; then
    echo "  - $BACKUP_PATH (backup)"
fi
echo ""

read -p "Continue with uninstallation? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled"
    exit 0
fi

# Remove the command file
echo "Removing /skills command..."
rm "$INSTALL_PATH"

# Remove backup if exists
if [ -f "$BACKUP_PATH" ]; then
    echo "Removing backup file..."
    rm "$BACKUP_PATH"
fi

# Verify removal
if [ ! -f "$INSTALL_PATH" ]; then
    echo ""
    echo "✓ Successfully uninstalled!"
    echo ""
    echo "The /skills command has been completely removed."
    echo "No traces left in your system."
    echo ""
    echo "To reinstall: ./install.sh"
    echo ""
else
    echo "✗ Uninstallation failed"
    exit 1
fi
