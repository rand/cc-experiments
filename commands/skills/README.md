# `/skills` - Claude Code Skills Discovery Command

A slash command for Claude Code that provides context-aware skill discovery and activation from a library of 292 skills across 31 categories.

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

### Plugin Installation (Recommended)

The `/skills` command is part of the **cc-polymath** Claude Code plugin. Install the entire plugin to get all 292 skills and commands:

```bash
/plugin install https://github.com/rand/cc-polymath
```

That's it! The plugin auto-registers all skills and commands, including `/skills`.

### Verify Installation

```bash
/plugin list
```

You should see `cc-polymath` in the list of installed plugins. The `/skills` command is now available.

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

CATEGORIES (292 total skills):
Frontend (8) | Database (8) | API (7) | Testing (6) | Diagrams (8) | ML (30)
Math (19) | Debugging (14) | Build Systems (8) | Caching (7) | Observability (8)
[View full catalog: ~/.claude/skills/README.md]

COMMANDS:
/skills frontend     - View all Frontend skills
/skills postgres     - Search for 'postgres' skills
/skills list         - Show all categories with descriptions
```

### Category View (`/skills frontend`)

```
FRONTEND SKILLS (8 total)
Keywords: React, Next.js, UI, components, state management, forms

SKILLS:
1. react-component-patterns - React patterns, hooks, composition
2. nextjs-app-router - Next.js App Router, Server Components
3. react-state-management - Context, Zustand, Redux patterns
4. react-data-fetching - TanStack Query, SWR, data loading
5. web-forms - Form validation, accessibility, user experience
6. web-accessibility - WCAG compliance, ARIA, inclusive design
7. frontend-performance - Core Web Vitals, optimization
8. nextjs-seo - SEO best practices, metadata, structured data

LOAD:
cat skills/frontend/INDEX.md                  # Full details
cat skills/discover-frontend/SKILL.md         # Gateway overview
cat skills/frontend/react-component-patterns.md  # Specific skill
```

### Search Results (`/skills postgres`)

```
SEARCH: 'postgres'

GATEWAY:
→ discover-database
  Keywords: PostgreSQL, MongoDB, Redis, query optimization
  cat skills/discover-database/SKILL.md

SKILLS:
→ postgres-query-optimization.md
  Debug slow queries, EXPLAIN plans, index design
  cat skills/database/postgres-query-optimization.md

→ postgres-migrations.md
  Schema changes, zero-downtime deployments
  cat skills/database/postgres-migrations.md

→ postgres-schema-design.md
  Designing schemas, relationships, data types
  cat skills/database/postgres-schema-design.md

RELATED: discover-observability, discover-caching
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
- `~/.claude/skills/README.md` (master catalog)
- `~/.claude/skills/{category}/INDEX.md` (category indexes)
- `~/.claude/skills/discover-*/SKILL.md` (gateway skills)
- Current working directory (for project detection)

It **never modifies**:
- Skill files
- Index or catalog files
- Claude Code configuration
- Your project files

## Uninstallation

### Plugin Uninstallation

```bash
/plugin uninstall cc-polymath
```

**That's it!** All skills, commands, and plugin data are cleanly removed.

### Verify Removal

```bash
/plugin list
```

The `cc-polymath` plugin should no longer appear in the list. All commands (including `/skills`) are automatically unregistered.

## Compatibility

### Works With

- ✅ All existing skills (292 skills across 31 categories)
- ✅ 28 gateway skills for auto-discovery
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
1. Verify plugin installed: `/plugin list` (should show `cc-polymath`)
2. If not installed: `/plugin install https://github.com/rand/cc-polymath`
3. Restart Claude Code session if needed

### No Recommendations

**Problem:** Shows empty or generic recommendations

**Possible causes:**
- Empty/new project directory → Expected behavior, shows general skills
- Skills catalog not found → Check `~/.claude/skills/README.md` exists

### Skills Catalog Not Found

**Problem:** Error message about missing `README.md`

**Solution:**
1. Verify skills directory: `ls ~/.claude/skills/`
2. Check catalog exists: `cat ~/.claude/skills/README.md`
3. If missing, restore from your skills repository (cc-polymath)

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

- **Plugin:** cc-polymath v2.0.0
- **File:** Auto-installed to `~/.claude/plugins/cc-polymath/commands/skills.md`
- **Size:** ~10 KB (325 lines)
- **Format:** Markdown with YAML frontmatter
- **Dependencies:** None (uses Claude Code plugin system)
- **Skills:** 292 skills, 28 gateways, 31 categories
- **Compatibility:** Claude Code v2.0+ with plugin support

## Contributing

This slash command is designed to be self-contained and maintenance-free. However, if you find issues or have suggestions:

1. The command reads from `~/.claude/skills/README.md` (master catalog)
2. Keep that file updated as you add new skills
3. Update individual category `INDEX.md` files as needed
4. The command will automatically show new skills

## License

This slash command is provided as-is for use with Claude Code and compatible with your existing skills setup.

## Version

**Version:** 2.0.0
**Last Updated:** 2025-10-27
**Compatibility:** Claude Code v2.0+
**Architecture:** Gateway-based progressive loading

---

**Quick Reference:**

```bash
# Install Plugin
/plugin install https://github.com/rand/cc-polymath

# Use
/skills                  # Context-aware recommendations
/skills frontend         # Browse category
/skills postgres         # Search for skills
/skills list             # All categories

# Uninstall Plugin
/plugin uninstall cc-polymath
```
