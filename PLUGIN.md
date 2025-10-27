# cc-polymath Claude Code Plugin

**Version:** 2.0.0
**Type:** Skills & Commands Plugin
**Author:** rand
**License:** MIT

## Overview

cc-polymath is a comprehensive Claude Code plugin that provides 292 atomic, composable skills across 31 categories, plus context-aware skill discovery commands. It uses a gateway-based progressive loading architecture to minimize context usage while maximizing skill availability.

## Plugin Structure

```
cc-polymath/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── skills/                       # 292 skills, 31 categories
│   ├── README.md                 # Master catalog (gateway index)
│   ├── discover-*/               # 28 gateway skills
│   │   └── SKILL.md
│   ├── api/                      # Category directories
│   │   └── INDEX.md              # Category index
│   │   └── *.md                  # Individual skills
│   ├── database/
│   ├── testing/
│   ├── diagrams/
│   ├── ml/
│   ├── math/
│   └── [28 more categories...]
├── commands/
│   └── skills.md                 # /skills command
├── LICENSE                       # MIT License
├── README.md                     # Main documentation
├── PLUGIN.md                     # This file
└── MIGRATION.md                  # Migration guide

```

## Installation

### For Users

Install the plugin with a single command:

```bash
/plugin install https://github.com/rand/cc-polymath
```

Claude Code will:
1. Clone the repository to `~/.claude/plugins/cc-polymath/`
2. Register all commands (e.g., `/skills`)
3. Make all 292 skills available for discovery
4. Enable gateway-based progressive loading

### For Developers

Clone the repository to develop locally:

```bash
git clone https://github.com/rand/cc-polymath
cd cc-polymath

# Install as plugin from local directory
/plugin install file://$(pwd)
```

## Plugin Architecture

### Three-Tier Progressive Loading

**Tier 1: Gateway Skills (28 skills)**
- Lightweight entry points (~200 lines each)
- Activate based on project keywords
- Guide to category indexes
- Examples: `discover-frontend`, `discover-database`, `discover-ml`

**Tier 2: Category Indexes (31 indexes)**
- Comprehensive category overviews
- List all skills in category with descriptions
- Load-on-demand when category is relevant
- Examples: `api/INDEX.md`, `database/INDEX.md`

**Tier 3: Individual Skills (233 skills)**
- Deep, actionable guidance (~300 lines avg)
- Load only when specifically needed
- Contain code examples, best practices, workflows
- Examples: `api/rest-design.md`, `database/postgres-optimization.md`

### Context Management

**Lazy Loading:**
- Gateway skills load first (minimal context)
- Category indexes load on-demand
- Individual skills load when explicitly needed

**Progressive Discovery:**
```
Project detected → Gateway activates → Category shown → Skill loaded
                    (~200 lines)        (~500 lines)     (~300 lines)
```

**Context Savings:**
- Loading all 292 skills: ~87,600 lines
- Gateway-based approach: ~200-1,000 lines per session
- **98-99% context reduction**

## Commands

### `/skills` - Skill Discovery

**Purpose:** Context-aware skill discovery and browsing

**Usage:**
```bash
/skills                  # Recommendations based on project
/skills frontend         # Browse frontend skills
/skills postgres         # Search for postgres-related skills
/skills list             # Show all categories
```

**Features:**
- Detects project type (Next.js, Go, Rust, Python, etc.)
- Recommends relevant skills automatically
- Non-destructive (read-only operations)
- CLI-optimized output (max 25 lines)

**Implementation:** `commands/skills.md` (325 lines)

## Skill Categories

### Available Categories (31 total)

| Category | Skills | Description |
|----------|--------|-------------|
| **API** | 7 | REST, GraphQL, gRPC, authentication, rate limiting |
| **Testing** | 6 | Unit, integration, E2E, property-based testing |
| **Database** | 8 | PostgreSQL, MongoDB, Redis, migrations, optimization |
| **Frontend** | 8 | React, Next.js, state management, accessibility |
| **Diagrams** | 8 | Mermaid, Graphviz, railroad diagrams, ASCII art |
| **ML** | 30 | LLMs, RAG, evaluation, DSPy, prompt engineering |
| **Math** | 19 | Category theory, algebra, topology, differential equations |
| **Debugging** | 14 | Performance profiling, memory analysis, distributed tracing |
| **Build Systems** | 8 | Docker, CI/CD, dependency management |
| **Caching** | 7 | Redis, CDN, cache invalidation strategies |
| **Observability** | 8 | Logging, metrics, tracing, alerting |
| **...** | ... | 20 more categories |

**Full list:** See `skills/README.md` after installation

## Plugin Metadata

### plugin.json

```json
{
  "name": "cc-polymath",
  "version": "2.0.0",
  "description": "292 atomic skills with gateway-based progressive loading",
  "author": "rand",
  "homepage": "https://github.com/rand/cc-polymath",
  "repository": "https://github.com/rand/cc-polymath",
  "license": "MIT",
  "keywords": [
    "skills", "gateway", "progressive-loading",
    "diagrams", "mermaid", "ml", "api", "database",
    "testing", "infrastructure", "mathematics", "debugging"
  ]
}
```

### Version History

- **v2.0.0** - Plugin architecture (2025-10-27)
  - Converted to Claude Code plugin
  - Added plugin manifest
  - Removed manual installation scripts
  - Renamed `slash-commands/` → `commands/`
  - Added LICENSE for marketplace compatibility

- **v1.0.0** - Manual installation
  - 292 skills across 31 categories
  - Gateway-based progressive loading
  - Manual sync with install.sh

## Plugin Lifecycle

### Installation
```bash
/plugin install https://github.com/rand/cc-polymath
```

**Process:**
1. Claude Code clones repository to `~/.claude/plugins/cc-polymath/`
2. Reads `.claude-plugin/plugin.json` for metadata
3. Registers commands from `commands/` directory
4. Makes skills available at `~/.claude/plugins/cc-polymath/skills/`

### Updates
```bash
/plugin update cc-polymath
```

**Process:**
1. Pulls latest version from repository
2. Updates plugin metadata
3. Refreshes commands and skills
4. Preserves user customizations (if any)

### Uninstallation
```bash
/plugin uninstall cc-polymath
```

**Process:**
1. Unregisters all commands
2. Removes `~/.claude/plugins/cc-polymath/` directory
3. Cleans up plugin metadata
4. No traces left in Claude Code configuration

## Development

### Adding New Skills

1. **Choose category** or create new one:
   ```bash
   mkdir skills/new-category
   ```

2. **Create skill file** (use kebab-case):
   ```bash
   cat > skills/new-category/my-skill.md << 'EOF'
   ---
   name: new-category-my-skill
   category: new-category
   description: Brief description of what this skill does
   keywords: [keyword1, keyword2, keyword3]
   ---

   # Skill content here
   EOF
   ```

3. **Update category INDEX.md**:
   ```markdown
   ## Skills
   - **my-skill.md** - Brief description
   ```

4. **Update gateway if needed** (`skills/discover-new-category/SKILL.md`)

5. **Update master catalog** (`skills/README.md`):
   ```markdown
   ### New Category (1 skill)
   Keywords: keyword1, keyword2
   ```

6. **Test the skill**:
   ```bash
   /skills new-category
   cat skills/new-category/my-skill.md
   ```

### Adding New Commands

1. **Create command file** in `commands/`:
   ```bash
   cat > commands/my-command.md << 'EOF'
   ---
   name: my-command
   description: What this command does
   ---

   # Command implementation
   EOF
   ```

2. **Test the command**:
   ```bash
   /my-command
   ```

3. **Document in README.md**

### Contribution Guidelines

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-skill`
3. **Follow naming conventions**:
   - Skills: `category-skill-name.md` (kebab-case)
   - Categories: lowercase, no spaces
   - Commands: lowercase, hyphen-separated
4. **Keep skills focused**: 200-400 lines, single responsibility
5. **Add YAML frontmatter**: name, category, description, keywords
6. **Update documentation**: INDEX.md, README.md, gateway skills
7. **Test locally**: Install as plugin, verify discovery works
8. **Submit pull request** with clear description

### Testing Locally

```bash
# Install from local directory
cd /path/to/cc-polymath
/plugin install file://$(pwd)

# Test commands
/skills
/skills your-category

# Test skill discovery
cat skills/your-category/your-skill.md

# Uninstall local version
/plugin uninstall cc-polymath
```

## Plugin Best Practices

### For Plugin Users

1. **Use `/skills` for discovery** - Don't manually browse directories
2. **Load skills on-demand** - Let gateways guide you
3. **Update regularly** - `/plugin update cc-polymath` for latest skills
4. **Provide feedback** - Report issues or suggest improvements

### For Plugin Developers

1. **Maintain gateway architecture** - Don't break progressive loading
2. **Keep skills atomic** - One skill = one responsibility
3. **Optimize for context** - Skills should be 200-400 lines
4. **Test before publishing** - Verify plugin installs and commands work
5. **Semantic versioning** - Use semver for releases (2.0.0, 2.1.0, etc.)
6. **Document changes** - Update README.md and PLUGIN.md

## Compatibility

### Claude Code Version

- **Required:** Claude Code v2.0+ with plugin support
- **Recommended:** Latest version for best experience

### Existing Installations

- **Migrating from manual installation?** See [MIGRATION.md](MIGRATION.md)
- **Can coexist with manual installation** (not recommended)
- **Plugin takes precedence** for commands and discovery

### Other Plugins

- **Compatible** with all Claude Code plugins
- **No conflicts** with built-in skills or commands
- **Composable** with other skill libraries

## Troubleshooting

### Plugin not installing

**Check:**
```bash
# Verify plugin system is available
/plugin help

# Check Claude Code version
# Plugins require v2.0+
```

### Commands not working after install

**Solution:**
```bash
# Restart Claude Code session
# Then verify
/plugin list  # Should show cc-polymath
/skills       # Should work
```

### Skills not discovered

**Check:**
```bash
# Verify plugin directory exists
ls ~/.claude/plugins/cc-polymath/skills/

# Reinstall if missing
/plugin uninstall cc-polymath
/plugin install https://github.com/rand/cc-polymath
```

### Want to modify skills

**Location:**
```bash
cd ~/.claude/plugins/cc-polymath/skills/
# Edit skills here
# Changes will persist until plugin update
```

**Note:** Plugin updates will overwrite changes. Fork the repository for permanent modifications.

## Technical Details

### File Structure

```
~/.claude/plugins/cc-polymath/
├── .claude-plugin/
│   └── plugin.json          # Metadata read by Claude Code
├── skills/                   # Discovered by skill system
│   ├── README.md             # Master catalog (28 gateways)
│   ├── discover-*/SKILL.md   # Gateway skills
│   └── */INDEX.md            # Category indexes
├── commands/                 # Auto-registered by plugin system
│   └── skills.md             # /skills command
└── [docs, license, etc.]
```

### Discovery Algorithm

**Project Detection:**
1. Scan working directory for indicator files
   - `package.json` → Frontend/Node.js
   - `go.mod` → Go
   - `Cargo.toml` → Rust
   - `pyproject.toml` → Python
   - etc.
2. Analyze conversation context
3. Match to gateway keywords
4. Recommend relevant skills

**Skill Matching:**
1. Gateway activates based on keywords
2. Category index provides overview
3. User loads specific skill when needed

### Performance

- **Installation:** ~2-3 seconds (clone + register)
- **Command execution:** <100ms (read-only operations)
- **Skill discovery:** <50ms (file scanning + matching)
- **Context usage:** 200-1,000 lines per session (vs 87,600 if all loaded)

## Future Enhancements

### Planned Features

- [ ] **Marketplace distribution** - Publish to official Claude Code marketplace
- [ ] **Skill analytics** - Track most-used skills, improve recommendations
- [ ] **Custom gateways** - User-defined gateway skills
- [ ] **Skill collections** - Curated bundles for specific workflows
- [ ] **Interactive skill wizard** - Guide users to right skills

### Community Requests

See [GitHub Issues](https://github.com/rand/cc-polymath/issues) for feature requests and discussions.

## Support

### Documentation

- **README.md** - Main documentation and quick start
- **PLUGIN.md** - This file (plugin details)
- **MIGRATION.md** - Migration from manual installation
- **commands/skills/README.md** - /skills command documentation
- **skills/README.md** - Master skills catalog

### Getting Help

1. **Check documentation** - README.md, PLUGIN.md, MIGRATION.md
2. **Browse issues** - https://github.com/rand/cc-polymath/issues
3. **Open new issue** - Provide details about problem
4. **Discussions** - https://github.com/rand/cc-polymath/discussions

### Contributing

Contributions welcome! See [Development](#development) section above.

1. Fork repository
2. Create feature branch
3. Make changes
4. Test locally
5. Submit pull request

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Credits

**Author:** rand
**Repository:** https://github.com/rand/cc-polymath
**Plugin System:** Claude Code by Anthropic

---

**Plugin Status:** ✅ Active Development
**Latest Version:** 2.0.0
**Last Updated:** 2025-10-27
