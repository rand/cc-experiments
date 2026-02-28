# FAQ: cc-polymath

Quick answers to frequently asked questions about cc-polymath, organized by topic.

## Installation & Setup

### How do I install cc-polymath?

Open Claude Code and run:

```
/plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath
```

That's it. All 410+ skills are immediately available and auto-discover as you work.

For local development, use:
```
/plugin install /Users/rand/src/cc-polymath
```

### Do I need to configure anything after installation?

No configuration needed. Skills auto-discover based on your project files and conversation keywords.

To verify installation works:
```bash
bash ../scripts/verify-install.sh
```

### Can I install manually instead of as a plugin?

Yes. Clone or fork the repository and symlink it to `~/.claude/plugins/cc-polymath`:
```bash
git clone https://github.com/rand/cc-polymath ~/.claude/plugins/cc-polymath
```

Then restart Claude Code. You'll have the same functionality.

### How do I update to the latest version?

If installed as a plugin via `/plugin install https://...`, updates happen automatically.

If you cloned the repo:
```bash
cd ~/.claude/plugins/cc-polymath && git pull origin main
```

### How do I uninstall?

```
/plugin uninstall cc-polymath
```

Or manually remove:
```bash
rm -rf ~/.claude/plugins/cc-polymath
```

---

## Using Skills

### How do I know which skills are available?

List all 33+ categories:
```
/skills list
```

Search for specific topics:
```
/skills postgres
/skills react
/skills kubernetes
```

Get recommendations for your current project:
```
/skills
```

This analyzes your files (package.json, requirements.txt, etc.) and recommends relevant skills.

### How does auto-discovery work?

Skills activate automatically based on keywords in your messages. Examples:

- Mention "React" or "Next.js" → `discover-frontend` skill loads
- Mention "PostgreSQL" or "query optimization" → `discover-database` skill loads
- Mention "REST API" or "GraphQL" → `discover-api` skill loads

**No commands needed.** Just work naturally and relevant skills appear.

### What if auto-discovery doesn't trigger?

Use manual commands to load what you need:

```bash
# Load a specific gateway skill
/discover-api
/discover-ml
/discover-debugging

# Browse a category
/skills database
/skills testing

# Load a specific skill directly
Read ../skills/api/rest-api-design.md
```

Auto-discovery covers ~80% of common cases. Manual loading handles the rest.

### How do I load a specific skill?

**Option 1: Use the slash command**
```
/discover-frontend
```

**Option 2: Search by topic**
```
/skills postgres
```

**Option 3: Browse the category**
```
/skills database
```

**Option 4: Load directly with cat** (if you know the exact path)
Read ../skills/database/postgres-query-optimization.md


### Can I load multiple skills at once?

Yes. Use multiple commands or ask Claude to load related skills:

```
/discover-api
/discover-database
/discover-testing
```

Or naturally in conversation: "I'm building a REST API with PostgreSQL and need testing patterns" — multiple skills auto-discover together.

### How much context do skills use?

**Gateway skills**: ~1K tokens (~200 lines)  
**Category indexes**: ~2.5K tokens (~500 lines)  
**Individual skills**: ~1.5K tokens (~320 lines)

Loading 3-5 skills uses **less context than most project files**. This is why the three-tier system works: you get comprehensive knowledge while using minimal tokens.

---

## Skill Organization

### What's the difference between gateway, index, and individual skills?

**Gateway Skills** (~200 lines)
- Lightweight entry points
- Auto-discover based on keywords
- Provide quick reference + links to related skills
- Example: `/discover-frontend` covers React, Next.js, TypeScript overview

**Category Indexes** (~500 lines)
- Comprehensive listings with descriptions
- Show all skills in a domain with use cases
- Loaded when browsing or planning
- Example: `/skills database` shows all 11 database skills

**Individual Skills** (~320 lines)
- Complete implementation guides
- Loaded on-demand for deep technical content
- Self-contained but cross-referenced
- Example: `postgres-query-optimization.md` with EXPLAIN patterns

**Flow**: Gateway → Index → Individual = Progressive discovery

### How are skills organized?

By **33+ categories** grouped into themes:

**Core Development** (125 skills)
- Languages: Python, Rust, Zig, Go, JavaScript
- Frameworks: React, Next.js, FastAPI, Axum
- Databases: PostgreSQL, MongoDB, Redis
- Testing: Unit, integration, e2e

**Infrastructure & DevOps** (70 skills)
- Cloud: AWS, GCP, Modal, Vercel
- Containers: Docker, Kubernetes
- CI/CD: GitHub Actions, pipelines
- Observability: Logging, metrics, tracing

**Specialized** (85 skills)
- ML/AI: DSPy, HuggingFace, embeddings, RAG
- Formal Methods: Z3, Lean 4, SAT/SMT solvers
- Mathematics: Linear algebra, topology, category theory
- Systems: WebAssembly, eBPF, binary protocols

**Meta** (7 skills)
- Workflow: Beads task management
- Discovery: Analyzing projects and prompts
- Skill creation: Building custom skills

Full list: `/skills list`

### How many skills are there?

**400 total skills** across 31+ categories:
- 283 individual skills
- 31 gateway skills (auto-discover)
- 30 category indexes
- 7 meta/workflow skills

See them all with `/skills list`.

### Can I create custom skills?

Yes. Skills follow Anthropic's agent skills framework with clear structure:

```markdown
---
title: "My Custom Skill"
description: "What this skill covers"
keywords: [keyword1, keyword2]
---

# Skill Content
[Implementation guide, patterns, examples]
```

See `skills/skill-creation.md` for the full template and guidelines.

You can:
- Add custom skills to your local cc-polymath fork
- Create standalone skills in your own projects
- Share skills via pull requests

---

## Common Workflows

### Building a web app?

Let skills auto-discover naturally, or load explicitly:

```
/discover-frontend      # React, Next.js, TypeScript
/discover-api           # REST/GraphQL design
/discover-database      # Database selection & optimization
/discover-testing       # Unit, integration, e2e patterns
```

Skills compose together seamlessly for full-stack work.

### Debugging performance issues?

```
/discover-debugging      # GDB, LLDB, profiling tools
/discover-observability  # Metrics, tracing, logging
/skills postgres         # If database-related
/discover-cloud          # If cloud infrastructure
```

Combine skills based on where the bottleneck is.

### Working with data?

```
/discover-database   # SQL optimization, schema design
/discover-data       # ETL, streaming, batch processing
/discover-caching    # Redis, CDN strategies
/discover-ml         # Analytics, embeddings, RAG
```

Data workflows often need 3-4 skills working together.

### Creating documentation?

```
/discover-diagrams   # Mermaid flowcharts, ER diagrams, sequences
/skills mermaid      # Search for diagram-specific patterns
```

Diagrams skills help create professional visuals for docs.

---

## Troubleshooting

### Commands aren't working (e.g., `/discover-frontend` returns an error)

Check installation:
```bash
bash ../scripts/verify-install.sh
```

If it fails, reinstall:
```
/plugin uninstall cc-polymath
/plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath
```

If the plugin is installed but commands don't work, restart Claude Code.

### Skills aren't loading or auto-discovery doesn't trigger

**Test auto-discovery**:
Try a clear prompt like: "I'm building a React app with TypeScript"

You should see `discover-frontend` activate automatically.

**Force load a skill**:
Read ../skills/discover-frontend/SKILL.md


If that returns content, the installation is working. Auto-discovery may just need clearer keywords.

**Run diagnostics**:
```bash
bash ../scripts/diagnose.sh
```

This reports what's installed and any configuration issues.

### Path errors or file not found

Verify the plugin path is correct:
```bash
ls ../skills
```

You should see skill directories. If empty or missing, reinstall the plugin.

Check that you're not in a directory with conflicting configuration:
```bash
cat ~/.claude/config.json | grep cc-polymath
```

---

## Advanced Usage

### Can I use skills with other plugins?

Yes. Skills are model-invoked and work alongside other Claude Code plugins.

If two plugins provide similar functionality, Claude intelligently selects which to use based on context. No conflicts.

### How do I find skills for my specific framework?

**Search by name**:
```
/skills nextjs
/skills fastapi
/skills axum
```

**Browse a category**:
```
/skills frontend
/skills backend
```

**Use auto-discovery**:
Just mention your framework naturally in a prompt. Skills auto-discover.

**Check the README**:
`../skills/README.md` lists all skills by framework.

### Can I contribute skills?

Yes! Pull requests welcome. The repository is open for community contributions.

**Process**:
1. Fork the repository
2. Add your skill to the appropriate category
3. Follow the template in `skills/skill-creation.md`
4. Include keywords for auto-discovery
5. Submit a PR

Skills are validated for:
- Code block syntax
- YAML frontmatter
- Cross-references
- Line count (individual skills ~320 lines)

See CONTRIBUTING.md for detailed guidelines.

### How do I report issues?

Open an issue on GitHub: [cc-polymath issues](https://github.com/rand/cc-polymath/issues)

Include:
- What you were trying to do
- Which skills were involved
- Error message or unexpected behavior
- Output from `diagnose.sh`

Bugs are fixed quickly. Feature requests welcome.

---

## Comparison to Other Approaches

### vs. Loading all skills upfront

| Approach | Context Cost | Boot Time | Discoverability |
|----------|--------------|-----------|-----------------|
| **cc-polymath** | 2-5K tokens | Instant | Auto-discover + manual |
| **All upfront** | 143K tokens | Slow | Everything available |
| **Savings** | **98% reduction** | **Much faster** | **More intelligent** |

With cc-polymath, you spend context on your actual work, not documentation.

### vs. Manual skill files

**cc-polymath advantages**:
- Auto-discovery (no need to remember what exists)
- Organized into categories (easy browsing)
- Cross-referenced (skills link to related skills)
- Commands for quick access (`/discover-*`)
- Progressive loading (gateway → index → skill)

**Manual files require**:
- Remembering the skill exists
- Manual file loading
- No automatic activation
- Less organization

### vs. Monolithic documentation

| Approach | Granularity | Reusability | Context Efficiency |
|----------|-------------|-------------|-------------------|
| **cc-polymath** | Atomic (410+ skills) | Compose freely | 98% savings |
| **Monolithic** | Large chapters | Load all-or-nothing | High overhead |
| **Best for** | Precise knowledge | Flexible workflows | Efficient context |

Atomic skills let you load *exactly* what you need, no more. This precision is what enables 98% context reduction.

---

## More Resources

**Getting Started**
- [GETTING_STARTED.md](GETTING_STARTED.md) - 5-minute quick start with walkthroughs

**Learning by Example**
- [FIRST_CONVERSATIONS.md](FIRST_CONVERSATIONS.md) - 6 complete example workflows

**Deep Dives**
- [WALKTHROUGHS.md](WALKTHROUGHS.md) - End-to-end project guides

**Troubleshooting**
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- `bash ../scripts/diagnose.sh` - Automated diagnostics

**Full Documentation**
- [README.md](../README.md) - Complete project overview
- [PLUGIN.md](../PLUGIN.md) - Plugin architecture details

**Explore Skills**
- `/skills list` - All 33+ categories
- `/skills [topic]` - Search for specific topics
- `Read ../skills/README.md` - Full skill catalog

---

**Still have questions?** Check TROUBLESHOOTING.md or open an issue on GitHub.
