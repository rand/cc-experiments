# Troubleshooting Guide

Having issues with cc-polymath? This guide covers the 10 most common problems and their solutions.

## Quick Diagnostic

Run the verification script for instant analysis:

```bash
bash <cc-polymath-root>/scripts/verify-install.sh
```

This checks:
- Plugin installation status
- File integrity and presence
- Path resolution
- File permissions
- Common installation conflicts

Expected output shows all checks passing. If you see failures, jump to the relevant issue below.

---

## 1. Command Not Found: `/discover-*`

**Symptom**: You try `/discover-frontend`, `/discover-api`, or another gateway command and get:
```
Error: Command not found
```

**Cause**: The plugin isn't installed, the command file is missing, or the plugin wasn't reloaded after installation.

**Solution**:

```bash
# Step 1: Verify plugin is installed
/plugin list

# You should see "cc-polymath" in the list with version 2.0.0+
# If not found, install it:
/plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath

# Step 2: If installed but commands don't work, reload the plugin
/plugin uninstall cc-polymath
/plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath

# Step 3: Verify installation worked
bash <cc-polymath-root>/scripts/verify-install.sh
```

**Additional context**: Commands are defined in `/commands/` and registered via `.claude-plugin/plugin.json`. If they're not available immediately after installation, restart Claude Code.

---

## 2. File Not Found: Plugin Skills Path

**Symptom**: When trying to load skills manually, you get errors like:
```
cat: <cc-polymath-root>/skills/api/rest-api-design.md: No such file or directory
```

**Cause**: Plugin installed to wrong location, or using old paths from a manual installation.

**Solution**:

```bash
# Step 1: Verify plugin location
[ -d ~/.claude/plugins/cc-polymath ] && echo "Plugin found" || echo "Plugin not found"

# Step 2: List what's actually there
ls -la <cc-polymath-root>/skills/ | head -20

# Step 3: If the directory doesn't exist, reinstall
/plugin uninstall cc-polymath
/plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath

# Step 4: Verify it worked
bash <cc-polymath-root>/scripts/verify-install.sh
```

**Common mistake**: Using old paths like `<cc-polymath-root>/skills/` instead of `<cc-polymath-root>/skills/`. See Issue #4 if you have both directories.

---

## 3. Auto-Discovery Not Triggering

**Symptom**: You mention keywords like "React", "PostgreSQL", or "REST API" but the relevant gateway skill doesn't load automatically.

**Cause**: Auto-discovery works through the skill system, not slash commands. It requires Claude to interpret your prompt and decide when to invoke the skill. It's not guaranteed for every mention—the model uses judgment about relevance.

**Solution**:

```bash
# Option 1: Use explicit commands instead of relying on auto-discovery
/discover-frontend    # For React, Next.js, TypeScript
/discover-database    # For PostgreSQL, MongoDB, Redis
/discover-api         # For REST, GraphQL, authentication

# Option 2: Try the /skills command to see what's recommended
/skills               # Auto-recommends for your current project
/skills database      # Browse database category
/skills postgres      # Search for PostgreSQL-specific skills

# Option 3: Check if the skill exists
ls <cc-polymath-root>/skills/ | grep discover-
```

**Note**: Auto-discovery is a convenience feature, not guaranteed. Manual commands are always reliable. For consistent access, use `/discover-*` commands or `/skills` search explicitly.

---

## 4. Old Manual Installation Conflicts

**Symptom**: Skills loading from unexpected locations, inconsistent behavior, or duplicate paths.

**Cause**: You installed skills manually to `<cc-polymath-root>/skills/` before the plugin system existed. Now both directories exist and Claude might be loading from the wrong one.

**Solution**:

```bash
# Step 1: Verify both directories exist
[ -d ~/.claude/skills ] && echo "Old skills dir exists" || echo "Old skills dir not found"
[ -d ~/.claude/plugins/cc-polymath ] && echo "Plugin dir exists" || echo "Plugin dir not found"

# Step 2: Back up the old directory if you customized it
[ -d ~/.claude/skills ] && cp -r ~/.claude/skills ~/.claude/skills.backup

# Step 3: Remove old manual installation
rm -rf ~/.claude/skills

# Step 4: Verify plugin installation is current
/plugin uninstall cc-polymath
/plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath

# Step 5: Run verification
bash <cc-polymath-root>/scripts/verify-install.sh
```

**Why this matters**: The plugin system at `<cc-polymath-root>/` is the source of truth. Manual installations at `<cc-polymath-root>/skills/` will be stale and cause confusion.

---

## 5. Permission Denied Errors

**Symptom**: You get errors when trying to read or execute plugin files:
```
Permission denied: <cc-polymath-root>/scripts/verify-install.sh
```

**Cause**: Plugin files were installed with incorrect file permissions, or your user doesn't have read access.

**Solution**:

```bash
# Step 1: Fix permissions on all plugin files
chmod -R u+rX <cc-polymath-root>/

# Step 2: Verify permissions are readable
ls -la <cc-polymath-root>/ | head -5

# Step 3: Test access
bash <cc-polymath-root>/scripts/verify-install.sh

# If still failing, check your user and ownership
# Step 4: (Advanced) Fix ownership if needed
whoami                                    # Check your username
ls -ld <cc-polymath-root>/     # Check current owner
# If owner differs, contact system administrator
```

**Note**: Scripts need execute permission (`+x`), skills need read permission (`+r`). The `u+rX` pattern grants read and execute to the user recursively.

---

## 6. Outdated Plugin Version

**Symptom**: Commands work differently than the documentation describes, or you see version mismatch warnings.

**Cause**: You have an old version of cc-polymath installed, before recent fixes and improvements.

**Solution**:

```bash
# Step 1: Check current version
/plugin list | grep cc-polymath

# Look for version 2.0.1 or higher
# Old versions: 1.0.x, 2.0.0
# Current: 2.0.1+

# Step 2: Update to latest version
/plugin uninstall cc-polymath
/plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath

# Step 3: Verify new version installed
/plugin list | grep cc-polymath

# Step 4: Run verification
bash <cc-polymath-root>/scripts/verify-install.sh
```

**Breaking changes in v2.0.1+**:
- Commands updated to use correct paths: `<cc-polymath-root>/`
- Old paths like `<cc-polymath-root>/skills/` no longer work
- Plugin system required (no manual skill files)

If you need version history: `git log --oneline` in the plugin directory shows all releases.

---

## 7. Skills Catalog Shows Wrong Count

**Symptom**: Commands report different numbers of skills than the README says (e.g., you see 283 skills but README says 400).

**Cause**: Cached catalog data, incomplete installation, or you're counting a subset (only gateway skills vs all skills).

**Solution**:

```bash
# Step 1: Count actual skill files
find <cc-polymath-root>/skills -name "*.md" -type f | wc -l

# You should see ~450+ files (skills + indexes + gateways)

# Step 2: Count just gateway skills
find <cc-polymath-root>/skills -type d -name "discover-*" | wc -l

# Should be 28-31 gateways

# Step 3: Count category indexes
find <cc-polymath-root>/skills -name "INDEX.md" | wc -l

# Should be 30+

# Step 4: If counts are low, reinstall
/plugin uninstall cc-polymath
/plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath

# Step 5: Verify
bash <cc-polymath-root>/scripts/verify-install.sh
```

**Note on counting**: 
- **283 skills** = Individual atomic skill files (not counting gateways or indexes)
- **31 gateways** = discover-* entry points
- **30+ indexes** = Category overviews
- **400 total** = Skills + gateways + indexes + meta files

If you see significantly different numbers, your installation is incomplete.

---

## 8. Can't Find Specific Skill

**Symptom**: You search for a skill (e.g., "REST API design") and either:
- The `/skills` command doesn't find it
- You know it should exist but can't locate it

**Cause**: Skill exists but search might not match exactly, or you need to browse the category instead.

**Solution**:

```bash
# Option 1: Try different search terms
/skills rest           # Search for "rest"
/skills api            # Search for "api"
/skills http           # Search for "http"

# Option 2: Browse the category
/skills api            # Shows all API skills
# Look for the one you need

# Option 3: Search the filesystem directly
find <cc-polymath-root>/skills -name "*rest*" -o -name "*api*"

# Option 4: Check the category index
Read <cc-polymath-root>/skills/api/INDEX.md

# Look for "REST" or similar keywords in the file

# Option 5: If skill truly doesn't exist
Read <cc-polymath-root>/skills/README.md

# Check the full catalog to see what categories exist
```

**Pro tip**: 
- Skills are organized in folders by category: `api/`, `database/`, `frontend/`, etc.
- Each category has an `INDEX.md` with all skills
- Gateway skills (`discover-*`) provide quick entry points
- If you know the category, browse the INDEX first

---

## 9. Gateway Skill Doesn't Load Full Category

**Symptom**: You load a gateway skill like `/discover-api`, but it doesn't show all API skills you know should exist.

**Cause**: Gateway skills are intentionally lightweight (~200 lines) and provide overview + quick reference, not the complete listing.

**Solution**:

```bash
# Step 1: Understand the 3-tier architecture
# Tier 1: Gateway Skills (quick reference, auto-discover)
/discover-api         # ~200 lines, shows quick reference

# Tier 2: Category Indexes (detailed listings)
Read <cc-polymath-root>/skills/api/INDEX.md
# ~500 lines, shows all 7 API skills with descriptions

# Tier 3: Individual Skills (complete guides)
Read <cc-polymath-root>/skills/api/rest-api-design.md
# ~320 lines, full REST implementation patterns

# Step 2: To see all skills in a category, load the INDEX
/skills api           # Shows all API skills

# Or browse directly:
Read <cc-polymath-root>/skills/api/INDEX.md

# Step 3: Then load the specific skill you need
Read <cc-polymath-root>/skills/api/rest-api-design.md
```

**Design note**: This three-tier system minimizes context usage. Gateway skills use ~1K tokens, the full category list ~2.5K tokens, and individual skills ~1.5K tokens. Loading everything upfront would use 143K tokens. Load what you actually need.

---

## 10. Commands Reference Wrong Paths

**Symptom**: Old commands or documentation show paths like:
- `<cc-polymath-root>/skills/discover-frontend/SKILL.md`
- `skills/api/rest-api-design.md` (relative path)

And you get "file not found" errors.

**Cause**: You're looking at documentation from before v2.0.1, when the plugin system changed. Paths were updated to the plugin location.

**Solution**:

```bash
# WRONG (old paths):
Read <cc-polymath-root>/skills/discover-frontend/SKILL.md
cat skills/api/rest-api-design.md

# CORRECT (current paths):
Read <cc-polymath-root>/skills/discover-frontend/SKILL.md
Read <cc-polymath-root>/skills/api/rest-api-design.md

# Quick reference:
# Replace this:    <cc-polymath-root>/skills/
# With this:       <cc-polymath-root>/skills/

# Test with a working command
Read <cc-polymath-root>/skills/README.md
# Should output the skills catalog

# If you have saved commands or scripts with old paths
# Use find and replace:
# Before:          skills/
# After:           <cc-polymath-root>/skills/
```

**Why this changed**: The plugin system requires skills to live in `<cc-polymath-root>/` instead of `<cc-polymath-root>/skills/`. This allows multiple plugins to coexist without conflicts.

---

## Still Having Issues?

### Advanced Diagnostics

If the 10 common issues don't solve your problem, try deeper investigation:

```bash
# Check Claude Code plugin system
/plugin list --verbose

# Verify plugin structure completely
find ~/.claude/plugins/cc-polymath -type f -name "*.md" | wc -l

# Check for specific file existence
[ -f <cc-polymath-root>/commands/skills.md ] && echo "Found" || echo "Missing"

# Inspect plugin configuration
Read <cc-polymath-root>/.claude-plugin/plugin.json

# Check bash PATH (if script execution fails)
echo $PATH
which bash
```

### Manual Verification Steps

1. **Installation directory**: `<cc-polymath-root>/` should exist
2. **Plugin config**: `.claude-plugin/plugin.json` should be present
3. **Skills catalog**: `skills/README.md` should list 31+ categories
4. **Gateway skills**: `skills/discover-*` directories (28-31 total)
5. **Category indexes**: `skills/*/INDEX.md` files (30+)
6. **Commands**: `commands/skills.md` and similar (10+)
7. **Permissions**: User should have read access to all files

### Get Help

If you've tried these solutions and still have issues:

- **Check documentation**: [GETTING_STARTED.md](GETTING_STARTED.md) covers basics
- **See examples**: [FIRST_CONVERSATIONS.md](FIRST_CONVERSATIONS.md) shows working usage
- **Read FAQ**: [FAQ.md](FAQ.md) for quick answers
- **Report bug**: [GitHub Issues](https://github.com/rand/cc-polymath/issues) with:
  - Steps to reproduce
  - Output of `bash <cc-polymath-root>/scripts/verify-install.sh`
  - Your platform (macOS, Linux, Windows + WSL)
  - Claude Code version

---

## Summary Table

| Issue | Symptom | Quick Fix |
|-------|---------|-----------|
| Plugin not installed | Command not found | `/plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath` |
| Wrong file path | "No such file or directory" | Update path to `<cc-polymath-root>/` |
| Auto-discovery not working | Skills don't auto-load | Use `/discover-*` commands explicitly |
| Old installation conflict | Inconsistent behavior | `rm -rf ~/.claude/skills` |
| Permission denied | Can't read files | `chmod -R u+rX <cc-polymath-root>/` |
| Outdated version | Commands work differently | `/plugin uninstall` then `/plugin install` |
| Wrong skill count | Fewer skills than expected | Check if counting gateways (31) vs all files (400) |
| Can't find skill | Search returns nothing | Use `/skills [category]` to browse |
| Gateway incomplete | Missing skills from category | Load INDEX.md for complete listing |
| Old documentation | Paths don't work | Replace `skills/` with `<cc-polymath-root>/skills/` |

---

## Next Steps

Once you've resolved your issue:

1. **Verify everything works**: `bash <cc-polymath-root>/scripts/verify-install.sh`
2. **Try your first command**: `/skills` to see what's recommended
3. **Read getting started**: [GETTING_STARTED.md](GETTING_STARTED.md)
4. **See examples**: [FIRST_CONVERSATIONS.md](FIRST_CONVERSATIONS.md)

Happy coding with cc-polymath!
