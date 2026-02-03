# cc-polymath Claude Code Plugin

**Version:** 3.1.0
**Type:** Skills & Commands Plugin
**Author:** rand
**License:** MIT

## Overview

cc-polymath is a comprehensive Claude Code plugin that provides 410+ atomic, production-ready skills across 33+ domains, plus context-aware skill discovery commands and specialized subagents. It uses a gateway-based progressive loading architecture to minimize context usage while maximizing skill availability.

## Plugin Structure

```
cc-polymath/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── skills/                       # 410+ skills, 33+ domains
│   ├── README.md                 # Master catalog (gateway index)
│   ├── discover-*/               # 40 gateway skills
│   │   └── SKILL.md
│   ├── api/                      # Category directories
│   │   └── INDEX.md              # Category index
│   │   └── *.md                  # Individual skills
│   ├── database/
│   ├── testing/
│   ├── diagrams/
│   ├── ml/
│   ├── math/
│   └── [30+ more categories...]
├── commands/                     # Slash commands
│   └── skills.md                 # /skills command
├── agents/                       # Specialized subagents
│   ├── skill-navigator.md        # Skills library expert guide
│   ├── architecture-advisor.md   # System design specialist
│   ├── polyglot-engineer.md      # Multi-language expert
│   └── skill-creator.md          # Generates new spec-compliant skills
├── .claude-plugin/
│   ├── plugin.json               # Plugin manifest
│   └── marketplace.json          # Marketplace configuration
├── LICENSE                       # MIT License
├── README.md                     # Main documentation
├── PLUGIN.md                     # This file
└── MIGRATION.md                  # Migration guide

```

## Installation

### For Users

Install the plugin with a single command:

```bash
# Option 1: Via GitHub repository
/plugin install https://github.com/rand/cc-polymath

# Option 2: Via marketplace (if configured)
/plugin marketplace add rand/cc-polymath
/plugin install cc-polymath
```

Claude Code will:
1. Clone the repository to `<cc-polymath-root>/`
2. Register all slash commands (e.g., `/skills`, `/discover-api`, etc.)
3. Make all 410+ skills available for discovery
4. Register specialized subagents (skill-navigator, architecture-advisor, polyglot-engineer, skill-creator)
5. Enable gateway-based progressive loading

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

**Tier 1: Gateway Skills (40 skills)**
- Lightweight entry points (~200 lines each)
- Activate based on project keywords
- Guide to category indexes
- Examples: `discover-frontend`, `discover-database`, `discover-ml`

**Tier 2: Category Indexes (33+ indexes)**
- Comprehensive category overviews
- List all skills in category with descriptions
- Load-on-demand when category is relevant
- Examples: `api/INDEX.md`, `database/INDEX.md`

**Tier 3: Individual Skills (410+ skills)**
- Deep, actionable guidance (~320 lines avg)
- Load only when specifically needed
- Contain code examples, best practices, workflows
- Examples: `api/rest-design.md`, `database/postgres-optimization.md`

### Context Management

**Lazy Loading:**
- Gateway skills load first (minimal context)
- Category indexes load on-demand
- Individual skills load when explicitly needed
- Subagents operate in separate context windows

**Progressive Discovery:**
```
Project detected → Gateway activates → Category shown → Skill loaded
                    (~200 lines)        (~500 lines)     (~320 lines)
```

**Context Savings:**
- Loading all 410+ skills: ~143,000 lines
- Gateway-based approach: ~200-1,500 lines per session
- **98-99% context reduction**

## Commands

### `/skills` - Comprehensive Skill Discovery

**Purpose:** Context-aware skill discovery and browsing with intelligent recommendations

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
- CLI-optimized output

**Implementation:** `commands/skills.md`

### Gateway Discovery Commands

Quick access to specific skill domains via slash commands:

| Command | Domain | Coverage |
|---------|--------|----------|
| `/discover-api` | API Design | REST, GraphQL, auth, rate limiting |
| `/discover-database` | Databases | PostgreSQL, MongoDB, Redis, optimization |
| `/discover-frontend` | Frontend | React, Next.js, TypeScript, state |
| `/discover-ml` | Machine Learning | DSPy, training, RAG, embeddings |
| `/discover-diagrams` | Diagrams | Mermaid flowcharts, sequence, ER |
| `/discover-testing` | Testing | Unit, integration, e2e, TDD |
| `/discover-infrastructure` | Infrastructure | Terraform, IaC, cloud, containers |
| `/discover-debugging` | Debugging | GDB, LLDB, profiling, memory |
| `/discover-containers` | Containers | Docker, Kubernetes, security |
| `/discover-mobile` | Mobile | iOS, Swift, SwiftUI, React Native |

**Usage:**
```bash
/discover-api        # Load API design skills directly
/discover-database   # Load database skills directly
```

These commands complement the auto-discovery system by providing explicit invocation.

## Specialized Subagents

cc-polymath includes four specialized subagents that leverage the skills library for focused workflows:

### `skill-navigator`
**Purpose:** Expert guide for navigating the 410+ skill library

**Use when:**
- Users need help finding relevant skills
- Understanding skill coverage across domains
- Discovering what's available for a specific technology

**Tools:** Read, Grep, Glob (fast, read-only)
**Model:** Haiku (optimized for quick responses)

**Invocation:** Automatically available via Task tool with `subagent_type: skill-navigator`

### `architecture-advisor`
**Purpose:** System design and architecture specialist

**Use when:**
- Designing new systems or microservices
- Refactoring existing architecture
- Making technology stack decisions
- Planning infrastructure and observability

**Tools:** All tools available
**Model:** Sonnet (complex reasoning)

Combines skills across API design, databases, infrastructure, caching, observability, and security.

**Invocation:** Automatically available via Task tool with `subagent_type: architecture-advisor`

### `polyglot-engineer`
**Purpose:** Multi-language expert (Rust, Python, Zig, Go, TypeScript, Swift)

**Use when:**
- Cross-language projects or porting code
- Choosing the right language for a task
- Language-specific best practices
- Rust/Python integration via PyO3

**Tools:** Read, Write, Edit, Bash, Grep, Glob
**Model:** Sonnet

Leverages language-specific skills and can implement solutions in the best-fit language.

**Invocation:** Automatically available via Task tool with `subagent_type: polyglot-engineer`

## Skill Categories

### Available Categories (33+ total)

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
  "description": "410+ atomic, production-ready skills with gateway-based progressive loading for Claude Code. 33+ domains including API design, databases, ML, diagrams (Mermaid), mathematics, testing, infrastructure, cryptography, protocols, MCP, agentic workflows, and more. Context-efficient three-tier architecture with auto-discovery gateways.",
  "author": {
    "name": "rand"
  },
  "homepage": "https://github.com/rand/cc-polymath",
  "repository": "https://github.com/rand/cc-polymath",
  "license": "MIT",
  "keywords": [
    "skills", "gateway", "progressive-loading", "diagrams", "mermaid",
    "ml", "api", "database", "testing", "infrastructure", "mathematics",
    "debugging", "frontend", "backend", "rust", "python", "zig",
    "cryptography", "protocols", "engineering", "mobile", "cloud",
    "devops", "security", "performance", "observability", "pyo3",
    "dspy", "context-efficient"
  ],
  "commands": "commands",
  "skills": "skills"
}
```

### Version History

- **v2.0.0** - Plugin architecture with subagents (2025-11-22)
  - Enhanced plugin manifest with explicit paths
  - Added 10 gateway discovery slash commands (`/discover-*`)
  - Created 3 specialized subagents (skill-navigator, architecture-advisor, polyglot-engineer)
  - Added marketplace.json for distribution
  - Updated to 410+ skills across 33+ domains
  - Enhanced keywords for better discoverability
  - Converted to Claude Code plugin
  - Added plugin manifest
  - Removed manual installation scripts
  - Renamed `slash-commands/` → `commands/`
  - Added LICENSE for marketplace compatibility

- **v1.0.0** - Manual installation
  - 410+ skills across 33+ categories
  - Gateway-based progressive loading
  - Manual sync with install.sh

## Plugin Lifecycle

### Installation
```bash
/plugin install https://github.com/rand/cc-polymath
```

**Process:**
1. Claude Code clones repository to `<cc-polymath-root>/`
2. Reads `.claude-plugin/plugin.json` for metadata
3. Registers commands from `commands/` directory
4. Makes skills available at `<cc-polymath-root>/skills/`

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
2. Removes `<cc-polymath-root>/` directory
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
ls <cc-polymath-root>/skills/

# Reinstall if missing
/plugin uninstall cc-polymath
/plugin install https://github.com/rand/cc-polymath
```

### Want to modify skills

**Location:**
```bash
cd <cc-polymath-root>/skills/
# Edit skills here
# Changes will persist until plugin update
```

**Note:** Plugin updates will overwrite changes. Fork the repository for permanent modifications.

## Technical Details

### File Structure

```
<cc-polymath-root>/
├── .claude-plugin/
│   └── plugin.json          # Metadata read by Claude Code
├── skills/                   # Discovered by skill system
│   ├── README.md             # Master catalog (40 gateways)
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
**Last Updated:** 2025-11-22
