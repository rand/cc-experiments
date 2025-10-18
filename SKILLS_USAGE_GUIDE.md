# Skills Usage Guide

**Last Updated**: 2025-10-18
**Status**: Production-ready with CI validation

---

## Quick Start

### For Claude/AI Agents

All 132 skills now have YAML frontmatter compliant with [agent_skills_spec.md](https://github.com/anthropics/skills/blob/main/agent_skills_spec.md):

```yaml
---
name: skill-name
description: Clear description of what this skill does
---
```

This enables:
- **Programmatic discovery**: Parse frontmatter to find relevant skills
- **Agent compatibility**: Direct integration with Claude and other AI agents
- **Automated validation**: CI checks ensure quality and consistency

### For Developers

**Recommended workflow**:

1. **Automatic Discovery** (Best):
   ```bash
   # New repository? Analyze it:
   Read skill-repo-discovery.md → Get list of relevant skills

   # User request? Analyze intent:
   Read skill-prompt-discovery.md → Get list of relevant skills
   ```

2. **Manual Discovery** (Alternative):
   ```bash
   # Search by pattern:
   ls ~/.claude/skills/modal-*.md
   ls ~/.claude/skills/swiftui-*.md

   # Browse catalog:
   cat ~/.claude/skills/_INDEX.md
   ```

3. **Read Only What You Need**:
   ```bash
   # Don't read all 132 skills upfront!
   # Read 2-3 relevant skills based on your task
   ```

---

## Quality Standards

### ✅ What's Guaranteed (as of 2025-10-18)

1. **YAML Frontmatter**: All 132 skills have valid frontmatter
2. **Date Accuracy**: 0 future dates (all validated by CI)
3. **Code Validation**: Python code blocks are syntax-checked
4. **Size Guidelines**: Target <500 lines per skill

### 🔄 In Progress

1. **Splitting oversized skills**: 89 skills >500 lines identified
   - See `ENHANCEMENT_PLAN.md` for split roadmap
   - Priority 1: orm-patterns, duckdb-analytics, docker-compose, rest-api

2. **Companion assets**: 54 templates planned
   - Modal starter templates
   - SwiftUI starter templates
   - Zig starter templates

3. **Extended smoke tests**:
   - Dependency validation
   - Execution tests
   - Snapshot testing

---

## CI/CD Validation

Every pull request and commit is validated for:

### 1. Date Validation
- **File**: `.github/workflows/validate-dates.yml`
- **Checks**: No future-dated "Last Updated" fields
- **Runs**: On every PR and push to main

### 2. Frontmatter Validation
- **File**: `.github/workflows/smoke-tests.yml`
- **Checks**:
  - YAML frontmatter present
  - Required fields (name, description)
  - Valid name format (hyphen-case)

### 3. Code Syntax Validation
- **File**: `tests/validate_code_blocks.py`
- **Checks**: Python code blocks are syntactically valid
- **Future**: Swift, Zig, JavaScript validation

---

## Skill Categories

### Core Categories (74 skills)

**API Design** (7):
- `api-authentication.md` - JWT, OAuth 2.0, API keys
- `api-authorization.md` - RBAC, ABAC, permissions
- `api-error-handling.md` - Error responses, validation
- `api-rate-limiting.md` - Token bucket, sliding window
- `api-versioning.md` - URL, header, content-type versioning
- `graphql-schema-design.md` - GraphQL schemas, resolvers
- `rest-api-design.md` - RESTful resources, HTTP methods

**Testing** (6):
- `unit-testing-patterns.md` - Mocks, stubs, AAA pattern
- `integration-testing.md` - API testing, DB integration
- `e2e-testing.md` - Playwright, Cypress, Selenium
- `test-driven-development.md` - Red-green-refactor
- `test-coverage-strategy.md` - What to test, coverage goals
- `performance-testing.md` - Load testing, stress testing

**Containers** (5):
- `dockerfile-optimization.md` - Multi-stage builds, caching
- `docker-compose-development.md` - Local dev environments
- `container-security.md` - Scanning, secrets, non-root
- `container-networking.md` - Networks, DNS, service discovery
- `container-registry-management.md` - Image tagging, promotion

**Frontend** (8):
- `react-component-patterns.md` - Composition, custom hooks
- `react-state-management.md` - Context, Zustand, Jotai
- `react-data-fetching.md` - SWR, React Query, Server Actions
- `react-form-handling.md` - React Hook Form, Zod validation
- `nextjs-app-router.md` - Server/Client Components, layouts
- `nextjs-seo.md` - Metadata API, structured data
- `frontend-performance.md` - Bundle optimization, Core Web Vitals
- `web-accessibility.md` - ARIA, keyboard navigation, screen readers

**Database** (11):
- `postgres-query-optimization.md` - EXPLAIN, indexes, query plans
- `postgres-migrations.md` - Schema evolution, zero-downtime
- `postgres-schema-design.md` - Relationships, normalization
- `mongodb-document-design.md` - Embedding vs referencing
- `redis-data-structures.md` - Strings, hashes, sets, sorted sets
- `database-connection-pooling.md` - Pool sizing, configuration
- `database-selection.md` - SQL vs NoSQL decision tree
- `orm-patterns.md` - N+1 prevention, eager loading
- `redpanda-streaming.md` - Kafka-compatible streaming
- `apache-iceberg.md` - Table format, time travel
- `duckdb-analytics.md` - Embedded analytics, Parquet

**Workflow & Tasks** (5):
- `beads-workflow.md` - bd CLI, issue tracking
- `beads-context-strategies.md` - /context vs /compact
- `beads-multi-session-patterns.md` - Long-running tasks
- `beads-dependency-management.md` - Issue dependencies

**Meta Skills** (5):
- `skill-repo-discovery.md` - Analyze repos → find skills
- `skill-prompt-discovery.md` - Analyze prompts → find skills
- `skill-repo-planning.md` - Plan development roadmap
- `skill-prompt-planning.md` - Plan task breakdown
- `skill-creation.md` - Create new skills

### Specialized Domains (33 skills)

**Modal.com** (8):
- `modal-functions-basics.md` - App structure, decorators
- `modal-gpu-workloads.md` - GPU selection, ML inference
- `modal-web-endpoints.md` - FastAPI integration, HTTP
- `modal-image-building.md` - uv_pip_install, layer caching
- `modal-scheduling.md` - Scheduled functions, cron
- `modal-volumes-secrets.md` - Persistent storage, secrets
- `modal-common-errors.md` - Troubleshooting
- `modal-performance-debugging.md` - Optimization

**iOS/Swift** (6):
- `swiftui-architecture.md` - MVVM, @Observable, state management
- `swift-concurrency.md` - async/await, actors, Swift 6
- `swiftdata-persistence.md` - Models, queries, relationships
- `swiftui-navigation.md` - NavigationStack, deep linking
- `ios-networking.md` - URLSession, NetworkService actor
- `ios-testing.md` - XCTest, view model testing

**Zig** (6):
- `zig-project-setup.md` - Project initialization, structure
- `zig-build-system.md` - build.zig configuration
- `zig-memory-management.md` - Allocators, defer/errdefer
- `zig-testing.md` - test blocks, expectations
- `zig-package-management.md` - build.zig.zon, dependencies
- `zig-c-interop.md` - FFI, C integration

**Formal Methods** (10):
- `z3-solver-basics.md` - SMT solving with Z3
- `sat-solving-strategies.md` - Boolean satisfiability
- `smt-theory-applications.md` - Program verification
- `lean-proof-basics.md` - Lean 4 fundamentals
- `lean-tactics.md` - Proof tactics
- `lean-mathlib4.md` - Math library
- `lean-theorem-proving.md` - Formal proofs
- `csp-modeling.md` - Constraint satisfaction
- `constraint-propagation.md` - CSP solving
- `backtracking-search.md` - Search strategies

**ML/AI** (7):
- `unsloth-finetuning.md` - Fast LLM fine-tuning
- `huggingface-autotrain.md` - AutoML training
- `llm-dataset-preparation.md` - Dataset cleaning, formatting
- `lora-peft-techniques.md` - Parameter-efficient fine-tuning
- `diffusion-model-basics.md` - Diffusion fundamentals
- `stable-diffusion-deployment.md` - SD deployment
- `diffusion-finetuning.md` - Custom diffusion models

---

## Discovery Patterns

### Pattern 1: Technology-Based Discovery

```bash
# I'm working with Modal.com
ls ~/.claude/skills/modal-*.md
# Returns: 8 Modal skills

# I'm building a SwiftUI app
ls ~/.claude/skills/swiftui-*.md ~/.claude/skills/swift-*.md ~/.claude/skills/ios-*.md
# Returns: 6 iOS/Swift skills

# I need API design help
ls ~/.claude/skills/api/*.md
# Returns: 7 API skills
```

### Pattern 2: Task-Based Discovery

```bash
# I need to test my code
ls ~/.claude/skills/testing/*.md
# Returns: 6 testing skills

# I'm deploying to production
ls ~/.claude/skills/cicd/*.md
ls ~/.claude/skills/deployment/*.md
# Returns: 5 CI/CD + 6 deployment skills
```

### Pattern 3: Problem-Based Discovery

```bash
# My database is slow
Read postgres-query-optimization.md
Read database-connection-pooling.md

# I have N+1 queries
Read orm-patterns.md  # See "N+1 Query Problem" section

# My container is too large
Read dockerfile-optimization.md
Read container-security.md  # See "Minimal Base Images"
```

### Pattern 4: Automated Discovery (Recommended)

```bash
# Use meta skills for intelligent discovery:

# New repository?
Read skill-repo-discovery.md
# Input: Repository path
# Output: List of relevant skills based on tech stack

# Complex user request?
Read skill-prompt-discovery.md
# Input: User request/prompt
# Output: List of relevant skills based on intent
```

---

## Best Practices

### DO ✅

1. **Use automated discovery** for new repos and complex requests
2. **Read 2-3 skills** max per task (avoid context bloat)
3. **Compose skills** for complex workflows
4. **Check _INDEX.md** for comprehensive catalog
5. **Validate with CI** when creating new skills

### DON'T ❌

1. **Don't read all 132 skills** upfront (waste of context)
2. **Don't skip discovery skills** (skill-repo-discovery, skill-prompt-discovery)
3. **Don't create monolithic skills** (keep under 500 lines)
4. **Don't ignore CI failures** (frontmatter, dates, syntax)
5. **Don't create new skills** for existing functionality (check _INDEX.md first)

---

## Creating New Skills

See `skill-creation.md` for comprehensive guide.

**Quick checklist**:
```
[ ] YAML frontmatter with name and description
[ ] Name in hyphen-case (lowercase, hyphens only)
[ ] Description explains what and when to use
[ ] Target <500 lines (split if larger)
[ ] "When to Use This Skill" section
[ ] Code examples with syntax validation
[ ] Related skills cross-references
[ ] Last Updated: YYYY-MM-DD
```

**Validation**:
```bash
# Test your skill before committing:
python3 tests/validate_code_blocks.py

# CI will also check:
# - YAML frontmatter validity
# - Date accuracy (no future dates)
# - Code syntax (Python blocks)
```

---

## Roadmap

See `ENHANCEMENT_PLAN.md` for details.

### Immediate (In Progress)
- Split 89 oversized skills to <500 lines
- Create Modal/iOS/Zig starter templates
- Expand smoke tests (Swift, Zig, JavaScript)

### Short-term (Next 2 Weeks)
- Complete Priority 1 skill splits (orm-patterns, duckdb-analytics, etc.)
- Add companion assets for Modal skills
- Implement dependency validation tests

### Medium-term (Next Month)
- 90% of skills under 500 lines
- 54 companion assets available
- Execution tests for code examples
- Snapshot testing for deterministic outputs

### Long-term (Next Quarter)
- 80% code block coverage in smoke tests
- Documentation site with search
- Auto-update toolchain version checks

---

## Support & Contributing

**Issues**: Found a problem? Check `ENHANCEMENT_PLAN.md` or create an issue

**Questions**: See `_INDEX.md` for full catalog and examples

**New Skills**: Follow `skill-creation.md` guidelines

**CI Status**: All checks must pass before merge

---

**Quality Guarantee**: All 132 skills are production-ready with CI validation ✅

**Last Updated**: 2025-10-18
