# `/skills` - Claude Code Skills Discovery Command

A slash command for Claude Code that provides context-aware skill discovery and activation, helping you leverage your skills library more effectively.

## What It Does

The `/skills` command helps you:
- **Discover** relevant skills for your current project
- **Browse** skills by category
- **Search** for specific skills or topics
- **Activate** the right skills for your workflow

All without leaving your Claude Code session.

## Features

- ✅ **Context-Aware Recommendations** - Detects your project type and suggests relevant skills
- ✅ **Non-Destructive** - Read-only operation, never modifies your skills library
- ✅ **Easy Install/Uninstall** - Single command to install or remove
- ✅ **CLI-Optimized** - Clean, readable output designed for terminal use
- ✅ **Flexible Discovery** - Browse by category or search by keyword
- ✅ **Works Everywhere** - Compatible with all projects and existing skill discovery

## Installation

### Quick Install

```bash
# Copy the command file to your personal commands directory
cp ~/.claude/commands/skills.md ~/.claude/commands/skills.md
```

**Already installed!** The file is at `~/.claude/commands/skills.md`

### Verify Installation

```bash
# Check the command exists
ls -la ~/.claude/commands/skills.md
```

You should see the file listed. Next time you start Claude Code, `/skills` will be available.

## Usage

### Basic Discovery

```
/skills
```

Shows:
- Recommended skills for your current project
- All skill categories with counts
- Quick commands for browsing and searching

### Browse by Category

```
/skills frontend
/skills database
/skills testing
```

Displays all skills in that category with descriptions and usage guidance.

### Search for Skills

```
/skills postgres
/skills authentication
/skills kubernetes
```

Fuzzy searches across skill names, descriptions, and categories.

### List All Categories

```
/skills list
```

Shows all available skill categories with counts and descriptions.

## Example Output

### Default View (`/skills`)

```
━━━ SKILLS DISCOVERY ━━━

RECOMMENDED FOR THIS PROJECT:
→ nextjs-app-router.md - Next.js App Router, Server Components
→ react-component-patterns.md - Component design, hooks, performance
→ postgres-query-optimization.md - Debug slow queries, EXPLAIN plans

CATEGORIES (135 total skills):
Frontend (9) | Database (11) | API (7) | Testing (6) | Containers (5)
Workflow (6) | iOS (6) | Modal (8) | Networking (5) | TUI (5) | Zig (6)
[View full catalog: ~/.claude/skills/_INDEX.md]

COMMANDS:
/skills frontend     - View all Frontend skills
/skills postgres     - Search for 'postgres' skills
/skills list         - Show all categories with descriptions
```

### Category View (`/skills frontend`)

```
━━━ FRONTEND SKILLS (9 skills) ━━━

react-component-patterns.md (~320 lines)
  → Component design, composition, hooks, performance
  → Use when: Building React components, optimizing renders

nextjs-app-router.md (~340 lines)
  → Next.js App Router, Server Components, routing
  → Use when: Building Next.js applications with App Router

elegant-design/SKILL.md (~302 lines)
  → World-class accessible interfaces, chat/terminal/code UIs
  → Use when: Building professional, accessible web interfaces

[... more skills ...]

RELATED CATEGORIES:
Testing (6) | API (7) | Database (11)

[Back to overview: /skills]
```

### Search Results (`/skills postgres`)

```
━━━ SEARCH RESULTS: 'postgres' ━━━

EXACT MATCHES:
→ postgres-query-optimization.md - Database/Performance
  Debug slow queries, EXPLAIN plans, index design

→ postgres-migrations.md - Database/Schema
  Schema changes, zero-downtime deployments

→ postgres-schema-design.md - Database/Design
  Designing schemas, relationships, data types

RELATED:
→ database-selection.md - Choosing databases (mentions Postgres)
→ orm-patterns.md - ORM usage (works with Postgres)

[Refine search: /skills postgres optimization]
[View category: /skills database]
```

## How It Works

### Context Detection

The command analyzes:
- **Project files** - Detects `package.json`, `go.mod`, `Cargo.toml`, etc.
- **Directory structure** - Looks for `.beads/`, `tests/`, `docker-compose.yml`
- **Conversation context** - Reviews what you've discussed with Claude
- **Work phase** - Understands if you're planning, coding, testing, or deploying

### Skill Matching

Based on detected context, it recommends skills that:
- Match your project's technology stack
- Address problems mentioned in conversation
- Fit common workflows for your project type
- Help with the current development phase

### Read-Only Operations

The command **only reads** from:
- `~/.claude/skills/_INDEX.md` (master catalog)
- `~/.claude/skills/*.md` (skill files)
- Current working directory (for project detection)

It **never modifies**:
- Skill files
- Index files
- Claude Code configuration
- Your project files

## Uninstallation

### Complete Removal

```bash
# Remove the command file
rm ~/.claude/commands/skills.md
```

**That's it!** No traces left, no cleanup needed.

### Verify Removal

```bash
# Check it's gone
ls ~/.claude/commands/skills.md
# Should output: No such file or directory
```

The next time you restart Claude Code, `/skills` will no longer be available.

## Compatibility

### Works With

- ✅ All existing skills (135+ skills)
- ✅ Existing skill discovery mechanisms
- ✅ All project types (Go, Python, Rust, JavaScript, Swift, Zig, etc.)
- ✅ Empty projects (provides general-purpose recommendations)
- ✅ Multi-language projects (detects all technologies)

### Doesn't Interfere With

- ✅ `skill-prompt-discovery.md` (automatic activation)
- ✅ `skill-repo-discovery.md` (repo-based activation)
- ✅ Manual skill reading
- ✅ Other slash commands
- ✅ Claude Code settings

## Troubleshooting

### Command Not Found

**Problem:** `/skills` doesn't work in Claude Code

**Solution:**
1. Verify file exists: `ls ~/.claude/commands/skills.md`
2. Restart Claude Code session
3. Try again

### No Recommendations

**Problem:** Shows empty or generic recommendations

**Possible causes:**
- Empty/new project directory → Expected behavior, shows general skills
- Skills index not found → Check `~/.claude/skills/_INDEX.md` exists

### Skills Index Not Found

**Problem:** Error message about missing `_INDEX.md`

**Solution:**
1. Verify skills directory: `ls ~/.claude/skills/`
2. Check index exists: `cat ~/.claude/skills/_INDEX.md`
3. If missing, restore from your skills repository

## Examples

### Starting a New Next.js Project

```bash
cd ~/projects/my-nextjs-app
# In Claude Code:
/skills
```

**Expected recommendations:**
- `nextjs-app-router.md`
- `react-component-patterns.md`
- `frontend-performance.md`
- `web-accessibility.md`

### Working on Database Optimization

```bash
cd ~/projects/slow-app
# In Claude Code, after discussing slow queries:
/skills postgres
```

**Expected results:**
- `postgres-query-optimization.md`
- `postgres-schema-design.md`
- `database-connection-pooling.md`

### Exploring Available Skills

```
/skills list
```

**Shows all categories** with descriptions, helping you discover skills you didn't know existed.

## Design Principles

**Low Noise** - Max 25 lines of output, fits in one screen
**High Signal** - Only relevant, actionable recommendations
**Augmentative** - Enhances workflow without interrupting it
**Composable** - Works alongside existing discovery mechanisms
**Safe** - Read-only, non-destructive, easily removable

## Technical Details

- **File:** `~/.claude/commands/skills.md`
- **Size:** ~6.8 KB (243 lines)
- **Format:** Markdown with YAML frontmatter
- **Dependencies:** None (uses Claude Code built-in slash command system)
- **Compatibility:** Claude Code v2.0+

## Contributing

This slash command is designed to be self-contained and maintenance-free. However, if you find issues or have suggestions:

1. The command reads from `~/.claude/skills/_INDEX.md`
2. Keep that file updated as you add new skills
3. The command will automatically show new skills

## License

This slash command is provided as-is for use with Claude Code and compatible with your existing skills setup.

## Version

**Version:** 1.0.0
**Last Updated:** 2025-10-25
**Compatibility:** Claude Code v2.0+

---

**Quick Reference:**

```bash
# Install
cp skills.md ~/.claude/commands/skills.md

# Use
/skills                  # Context-aware recommendations
/skills frontend         # Browse category
/skills postgres         # Search for skills
/skills list             # All categories

# Uninstall
rm ~/.claude/commands/skills.md
```
