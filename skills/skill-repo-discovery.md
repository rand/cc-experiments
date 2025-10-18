# Repository Skill Discovery

**Scope**: Analyzing repositories to identify which existing skills are most useful for the codebase
**Lines**: ~380
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Starting work on an unfamiliar repository or codebase
- Onboarding to a new project and need to understand required skills
- Performing codebase audit to identify skill coverage gaps
- Planning which skills to read before implementing features
- Creating onboarding documentation for team members
- Mapping a repository's tech stack to available skills
- Prioritizing skill learning based on project needs
- Identifying missing skills that should be created

## Core Concepts

### Repository Anatomy Analysis

**Tech Stack Discovery**:
- Package managers reveal dependencies (package.json, requirements.txt, Cargo.toml, go.mod)
- Build configs show tooling (webpack.config.js, vite.config.ts, build.zig)
- Lock files indicate exact versions (package-lock.json, poetry.lock, Cargo.lock)
- Docker/container files show deployment targets (Dockerfile, docker-compose.yml)
- CI/CD configs reveal testing and deployment patterns (.github/workflows/, .gitlab-ci.yml)

**Architecture Patterns**:
- Directory structure indicates architecture (monorepo, microservices, MVC, Clean Architecture)
- Import/module patterns show dependencies between components
- Test directories reveal testing strategies (unit/, integration/, e2e/)
- Database migrations indicate schema management approach
- API specifications show interface contracts (OpenAPI, GraphQL schema)

**Deployment Infrastructure**:
- Cloud provider configs (vercel.json, modal app files, cloudflare wrangler.toml)
- Infrastructure as Code (Terraform, Pulumi, CDK)
- Environment management (.env.example, config files)
- Secrets management (vault configs, encrypted secrets)

### Skill Mapping Strategies

**Direct Mapping** (Tech → Skills):
- Technology identified → Activate corresponding skill
- Example: `package.json` with `"next"` → `nextjs-*.md` skills
- Example: `build.zig` → All `zig-*.md` skills
- Example: `Cargo.toml` → `rust-*.md` skills

**Pattern-Based Mapping** (Code Patterns → Skills):
- Code patterns identified → Activate pattern-specific skills
- Example: `@app.function` decorators → `modal-*.md` skills
- Example: SwiftUI views → `swiftui-*.md` skills
- Example: Bubble Tea components → `bubbletea-*.md` skills

**Workflow Mapping** (Process → Skills):
- Development workflow identified → Activate workflow skills
- Example: `.beads/` directory → `beads-*.md` skills
- Example: GitHub Actions with tests → `cicd-*.md`, `testing-*.md`
- Example: Database migrations → `database-*.md`, schema management skills

### Coverage Analysis

**Complete Coverage**: All major technologies have corresponding skills
- ✅ All frameworks have skills
- ✅ All deployment targets covered
- ✅ Testing strategies documented
- ✅ Development workflows supported

**Partial Coverage**: Some technologies covered, gaps exist
- ⚠️ Some frameworks missing skills
- ⚠️ Deployment process undocumented
- ⚠️ Testing patterns not standardized

**No Coverage**: Skills needed but missing
- ❌ Critical technologies without skills
- ❌ Custom patterns undocumented
- ❌ Team knowledge not captured
- → **Action**: Use `skill-creation.md` to create missing skills

### Priority Ranking

**Critical (Must Read First)**:
- Core language skills (Python, Rust, Go, TypeScript, Swift, Zig)
- Primary framework skills (Next.js, FastAPI, Bubble Tea, SwiftUI)
- Active deployment platform skills (Modal, Vercel, Cloudflare)
- Current workflow skills (Beads if `.beads/` exists)

**High (Read Before Feature Work)**:
- Database skills (Postgres, Redis, etc.)
- Testing framework skills
- State management patterns
- Authentication/authorization

**Medium (Read As Needed)**:
- Performance optimization skills
- Security hardening skills
- Monitoring and observability
- Advanced patterns

**Low (Reference Only)**:
- Alternative technology skills not in use
- Deprecated pattern skills
- Experimental feature skills

---

## Patterns

### Pattern 1: Package Manager Analysis

**Python (requirements.txt, pyproject.toml)**:
```bash
# Search for Python package managers
cd /path/to/repo
ls pyproject.toml requirements.txt poetry.lock Pipfile 2>/dev/null

# Analyze dependencies
grep -E "^(fastapi|django|flask|modal)" requirements.txt pyproject.toml

# Map to skills
# fastapi → api-*.md, modal-*.md (if deployed to Modal)
# django → django-*.md
# pytest → testing-*.md, pytest-*.md
# sqlalchemy → database-*.md, orm-*.md
```

**JavaScript/TypeScript (package.json)**:
```bash
# Check Node package manager
ls package.json pnpm-lock.yaml yarn.lock package-lock.json 2>/dev/null

# Analyze key dependencies
cat package.json | grep -A 20 '"dependencies"' | grep -E "(next|react|vue|svelte|express)"

# Map to skills
# "next": "14.x" → nextjs-*.md, react-*.md
# "@vercel/analytics" → vercel-*.md, analytics-*.md
# "tailwindcss" → tailwind-*.md
# "@shadcn/ui" → shadcn-*.md
```

**Rust (Cargo.toml)**:
```bash
# Check Rust package file
ls Cargo.toml Cargo.lock 2>/dev/null

# Analyze dependencies
grep -A 50 '\[dependencies\]' Cargo.toml | grep -E "(tokio|axum|ratatui|serde)"

# Map to skills
# tokio → rust-async.md, rust-concurrency.md
# ratatui → ratatui-*.md, tui-*.md
# serde → rust-serialization.md
# anyhow/thiserror → rust-error-handling.md
```

**Go (go.mod)**:
```bash
# Check Go module file
ls go.mod go.sum 2>/dev/null

# Analyze dependencies
grep -E "(bubbletea|cobra|gin|echo)" go.mod

# Map to skills
# bubbletea → bubbletea-*.md, tui-*.md
# cobra → cli-*.md
# gin/echo → api-*.md, go-web-*.md
```

**Zig (build.zig, build.zig.zon)**:
```bash
# Check Zig build files
ls build.zig build.zig.zon 2>/dev/null

# Analyze build configuration
grep -E "(exe|lib|test)" build.zig

# Map to skills
# Any build.zig → zig-*.md (all Zig skills)
# Specifically: zig-build-system.md, zig-project-setup.md
```

**Swift (Package.swift, Podfile, project.pbxproj)**:
```bash
# Check Swift package/dependency files
ls Package.swift Podfile *.xcodeproj/project.pbxproj 2>/dev/null

# For SwiftUI projects, check for SwiftUI imports
find . -name "*.swift" -type f -exec grep -l "import SwiftUI" {} \; | head -5

# Map to skills
# SwiftUI imports → swiftui-*.md, swift-*.md, ios-*.md
# Combine framework → combine-*.md
# async/await → swift-concurrency.md
```

### Pattern 2: Directory Structure Analysis

**Identify Architecture**:
```bash
# Check for monorepo
ls pnpm-workspace.yaml lerna.json nx.json turbo.json 2>/dev/null
# → monorepo-*.md skills

# Check for microservices
ls services/ apps/ packages/ 2>/dev/null
find . -name "docker-compose.yml" -o -name "Dockerfile" | wc -l
# → microservices-*.md, docker-*.md skills

# Check for MVC/Clean Architecture
ls -d app/models app/views app/controllers src/domain src/application 2>/dev/null
# → architecture-*.md skills

# Check for Next.js app router
ls -d app/ src/app/ 2>/dev/null
# → nextjs-app-router.md, nextjs-*.md skills
```

**Test Strategy Discovery**:
```bash
# Find test directories
find . -type d -name "test*" -o -name "__test__" -o -name "spec" | grep -v node_modules

# Identify test frameworks
grep -r "pytest\|unittest\|vitest\|jest\|cargo test\|go test" --include="*.json" --include="*.toml" --include="*.yaml"

# Map to skills
# tests/ with pytest → pytest-*.md, testing-*.md
# __tests__/ with Jest → jest-*.md, testing-*.md
# e2e/ directory → e2e-testing.md, playwright-*.md
# tests/unit tests/integration → testing-strategy.md
```

### Pattern 3: Cloud Platform Detection

**Modal.com**:
```bash
# Check for Modal usage
grep -r "import modal\|from modal" --include="*.py" | head -5
ls modal.toml .modal.toml 2>/dev/null
grep -r "@app\\.function\|@app\\.cls" --include="*.py" | head -3

# Activate skills
# → modal-*.md (all 9 Modal skills)
# Prioritize: modal-functions-basics.md, modal-gpu-workloads.md
```

**Vercel**:
```bash
# Check for Vercel deployment
ls vercel.json .vercel/ 2>/dev/null
grep "vercel" package.json

# Activate skills
# → vercel-*.md, nextjs-*.md (Vercel optimized)
```

**Cloudflare Workers**:
```bash
# Check for Cloudflare Workers
ls wrangler.toml 2>/dev/null
grep "workers\\.dev\|@cloudflare/workers" package.json

# Activate skills
# → cloudflare-*.md, workers-*.md
```

**AWS Lambda**:
```bash
# Check for AWS Lambda
ls serverless.yml sam.yaml template.yaml 2>/dev/null
grep -r "aws-lambda\|@aws-sdk" --include="*.json" --include="*.py"

# Activate skills
# → aws-lambda-*.md, serverless-*.md
```

### Pattern 4: Database and ORM Detection

**Database Usage**:
```bash
# Postgres
grep -r "psycopg2\|asyncpg\|pg\|postgres" requirements.txt package.json Cargo.toml go.mod
ls migrations/ alembic/ 2>/dev/null
# → postgres-*.md, database-*.md

# SQLite
find . -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3"
grep -r "sqlite3\|better-sqlite3" --include="*.json" --include="*.py"
# → sqlite-*.md, database-*.md

# Redis
grep -r "redis\|ioredis\|redis-py" requirements.txt package.json
# → redis-*.md, caching-*.md

# MongoDB
grep -r "pymongo\|mongoose\|mongodb" requirements.txt package.json
# → mongodb-*.md, nosql-*.md
```

**ORM/Query Builder**:
```bash
# SQLAlchemy (Python)
grep "sqlalchemy" requirements.txt pyproject.toml
# → sqlalchemy-*.md, orm-*.md

# Prisma (TypeScript)
grep "prisma" package.json
ls prisma/schema.prisma 2>/dev/null
# → prisma-*.md, orm-*.md

# Diesel (Rust)
grep "diesel" Cargo.toml
# → diesel-*.md, rust-database.md

# GORM (Go)
grep "gorm.io" go.mod
# → gorm-*.md, go-database.md
```

### Pattern 5: CI/CD and DevOps

**GitHub Actions**:
```bash
# Check for GitHub Actions workflows
ls .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null

# Analyze workflow content
grep -h "name:\|uses:\|run:" .github/workflows/*.yml | head -20

# Map to skills
# Actions with tests → testing-*.md, cicd-*.md
# Actions with deploy → deployment-*.md, cicd-*.md
# Actions with build → build-*.md
```

**Docker/Containers**:
```bash
# Check for Docker usage
ls Dockerfile docker-compose.yml .dockerignore 2>/dev/null
find . -name "Dockerfile*" | wc -l

# Activate skills
# → docker-*.md, containerization-*.md
# Multi-stage builds → docker-optimization.md
```

### Pattern 6: Beads Workflow Detection

**Check for Beads Usage**:
```bash
# Look for Beads state
ls .beads/issues.jsonl 2>/dev/null
grep -r "bd create\|bd update\|bd close" --include="*.sh" --include="*.md"

# Activate skills
# → beads-workflow.md
# → beads-context-strategies.md
# → beads-multi-session-patterns.md
# → beads-dependency-management.md
```

---

## Quick Reference

### Tech Stack → Skills Mapping

```
Technology/Framework          | Activate Skills                           | Priority
------------------------------|-------------------------------------------|----------
Next.js                       | nextjs-*.md, react-*.md                  | Critical
FastAPI                       | api-*.md, fastapi-*.md, python-*.md      | Critical
Modal.com                     | modal-*.md (all 9)                       | Critical
Vercel                        | vercel-*.md, deployment-*.md             | Critical
React                         | react-*.md, frontend-*.md                | High
TypeScript                    | typescript-*.md, type-safety.md          | High
SwiftUI                       | swiftui-*.md, swift-*.md, ios-*.md       | Critical
Bubble Tea (Go)               | bubbletea-*.md, tui-*.md, go-*.md        | Critical
Ratatui (Rust)                | ratatui-*.md, tui-*.md, rust-*.md        | Critical
Zig                           | zig-*.md (all 6)                         | Critical
Postgres                      | postgres-*.md, database-*.md             | High
Tailwind + shadcn/ui          | tailwind-*.md, shadcn-*.md               | High
Beads workflow                | beads-*.md (all 4)                       | Critical
GitHub Actions                | cicd-*.md, github-actions-*.md           | Medium
Docker                        | docker-*.md, containerization-*.md       | Medium
pytest/Jest/Vitest            | testing-*.md, [framework]-*.md           | High
```

### File Pattern → Skills

```
File/Directory Pattern        | Activate Skills
------------------------------|------------------------------------------
package.json                  | Check deps → nextjs/react/vue/svelte skills
pyproject.toml                | python-*.md, uv-*.md (if tool.uv exists)
Cargo.toml                    | rust-*.md
go.mod                        | go-*.md
build.zig                     | zig-*.md (all)
.beads/issues.jsonl           | beads-*.md (all)
.github/workflows/            | cicd-*.md, github-actions-*.md
Dockerfile                    | docker-*.md, containerization-*.md
tests/ or __tests__/          | testing-*.md
migrations/ or alembic/       | database-*.md, migrations-*.md
vercel.json                   | vercel-*.md
wrangler.toml                 | cloudflare-*.md
modal.toml                    | modal-*.md (all)
```

### Decision Tree: Repository → Skills

```
Start: Analyze Repository
  ↓
1. Check package managers (package.json, pyproject.toml, etc.)
   → Identify primary languages → Activate language skills
  ↓
2. Scan dependencies in package files
   → Map frameworks → Activate framework skills
  ↓
3. Check directory structure
   → Identify architecture → Activate architecture skills
  ↓
4. Look for cloud deployment configs (vercel.json, modal.toml, etc.)
   → Identify platforms → Activate platform skills
  ↓
5. Scan for database usage (migrations/, DB imports)
   → Identify databases → Activate database skills
  ↓
6. Check CI/CD configs (.github/workflows/)
   → Identify CI/CD → Activate cicd skills
  ↓
7. Look for Beads state (.beads/issues.jsonl)
   → If exists → Activate beads-*.md skills
  ↓
8. Identify test directories and frameworks
   → Activate testing skills
  ↓
9. Check _INDEX.md for skill catalog
   → Search for identified technologies
  ↓
10. Prioritize by immediate need
    → Critical: Core language + main framework + deployment
    → High: Database + testing + workflow
    → Medium: Advanced features + optimization
  ↓
Result: Prioritized skill reading list
```

### Commands for Quick Analysis

```bash
# Complete repository analysis
cd /path/to/repo

# 1. Identify languages
find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.go" -o -name "*.rs" -o -name "*.zig" -o -name "*.swift" \) | head -10

# 2. Check package managers
ls package.json pyproject.toml Cargo.toml go.mod build.zig Package.swift 2>/dev/null

# 3. Find deployment configs
find . -maxdepth 2 -name "vercel.json" -o -name "modal.toml" -o -name "wrangler.toml" -o -name "Dockerfile"

# 4. Check for Beads
ls .beads/issues.jsonl 2>/dev/null && echo "Beads workflow detected"

# 5. Identify testing
find . -type d -name "test*" -o -name "__test__" | head -5

# 6. Search skills catalog
cd ~/.claude/skills
grep -l "modal\|nextjs\|swiftui" *.md | sort
```

---

## Anti-Patterns

❌ **Reading all skills at once**: Cognitive overload, wasted time
✅ **Analyze repo first, then read only relevant skills** (5-10 max)

❌ **Ignoring _INDEX.md**: Missing organized skill catalog
✅ **Always check _INDEX.md for comprehensive skill list and discovery patterns**

❌ **Not prioritizing skills**: Reading low-priority skills first
✅ **Follow priority ranking: Critical → High → Medium → Reference**

❌ **Assuming tech stack**: Making incorrect skill choices
✅ **Use grep/find to confirm technologies before activating skills**

❌ **Missing skill combinations**: Reading skills in isolation
✅ **Check _INDEX.md for common workflows** (e.g., Modal + FastAPI + Postgres)

❌ **Skipping skill-creation.md when gaps exist**: Undocumented patterns
✅ **If critical technology lacks skill, create one using skill-creation.md**

❌ **Not updating skill list**: Stale skill inventory
✅ **After analysis, update project docs with recommended skills**

❌ **Reading without purpose**: Browsing skills aimlessly
✅ **Know what you're building → Identify needed skills → Read targeted subset**

---

## Related Skills

- `skill-creation.md` - Create new skills when gaps are discovered
- `skill-prompt-discovery.md` - Search for skills by prompt/task description
- `skill-repo-planning.md` - Plan skill-based development roadmap for repos
- `beads-workflow.md` - Manage skill discovery as tracked work
- `beads-context-strategies.md` - Manage context when reading multiple skills
- `_INDEX.md` - Complete catalog of all available skills (35+ skills)

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
