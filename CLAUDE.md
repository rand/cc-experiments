# Claude Development Guidelines

> **Critical Success Principle**: Following these guidelines is mandatory. Each section contains decision trees, mandatory checkpoints, and anti-patterns that protect against wasted time and technical debt.

## Table of Contents
1. [Core Workflow: Agentic Work](#1-core-workflow-agentic-work)
2. [Critical Thinking & Pushback](#2-critical-thinking--pushback)
3. [Language Stack & Tooling](#3-language-stack--tooling)
4. [Cloud Platforms & Infrastructure](#4-cloud-platforms--infrastructure)
5. [Project Initiation Protocol](#5-project-initiation-protocol)
6. [Testing & Validation](#6-testing--validation)
7. [Version Control & Git](#7-version-control--git)
8. [Frontend Development](#8-frontend-development)
9. [Skills System](#9-skills-system)
10. [Anti-Patterns & Violations](#10-anti-patterns--violations)
11. [Quick Reference](#11-quick-reference)

---

## 1. Core Workflow: Agentic Work

### Primary Framework: Beads
**Mandatory for**: All agentic work, sub-agents, multi-session tasks, complex workflows  
**Framework URL**: https://github.com/steveyegge/beads

### Session Start Protocol
```bash
go install github.com/steveyegge/beads/cmd/bd@latest  # MANDATORY at session start
bd version                                             # Verify installation
bd import -i .beads/issues.jsonl                       # Import state (existing projects)
bd ready --json --limit 5                              # Check ready work
```

### Core Workflow Pattern
```
Session Start → Import State → Check Ready Work
  ↓
Have Ready Work?
  ├─ Yes: Claim Task (bd update ID --status in_progress)
  └─ No: Create New Work (bd create)
  ↓
Execute & Discover → Discover Sub-tasks?
  ├─ Yes: File Immediately (bd create + bd dep add)
  └─ No: Continue
  ↓
Task Complete?
  ├─ Yes: Close (bd close ID --reason) → Export State → Commit
  └─ No: Context Bloat? → /compact or /context → Continue
```

### Context Management
**ACTIVATE**: `beads-workflow.md`, `beads-context-strategies.md`, `beads-multi-session-patterns.md`

**Strategic /context** (Preserve): Before complex issues, after discovering new work, before refactoring, when switching topics, after merge conflicts

**Strategic /compact** (Compress): After completing issues, after routine ops (bd list/show), when context >75% full, after bulk issue creation, during long troubleshooting

### Non-Negotiable Rules
1. NEVER leave TODO, mocks, or stubs → Implement NOW or create Beads issue
2. ALWAYS use `--json` flag with bd commands for parseable output
3. ALWAYS export state before ending: `bd export -o .beads/issues.jsonl`
4. ALWAYS commit .beads/issues.jsonl to git

---

## 2. Critical Thinking & Pushback

### When to Push Back (MANDATORY)
```
TRIGGER                     → RESPONSE
─────────────────────────────────────────────────
Vague requirements         → "Let's clarify X, Y, Z first"
Poor tech choice           → "Consider [alt] because [reason]"
Missing error handling     → "This needs error handling for [cases]"
Overly complex solution    → "Simpler approach: [alternative]"
Hidden arch costs          → "This will cause [problem] because [reason]"
Scalability issues         → "Won't scale past [limit] due to [constraint]"
Security vulnerabilities   → "This exposes [risk]. Use [secure pattern]"
Missing edge cases         → "What happens when [edge case]?"
```

### Constructive Challenge Pattern
```
WRONG: "You're absolutely right!"
RIGHT: "Consider X because Y. Here's the tradeoff: [analysis]"

WRONG: "That won't work."
RIGHT: "That approach has [limitation]. Alternative: [solution] with [benefit]"
```

### Decision Framework
```
Is requirement clear? NO → ASK for clarification
Is tech choice optimal? NO → SUGGEST better alternative
Are edge cases handled? NO → FLAG missing cases
Is solution maintainable? NO → PROPOSE simpler approach
→ Proceed
```

### Date and Time Awareness (MANDATORY)

**ABSOLUTE RULE**: NEVER assume the current date or time without verification

**Verification Protocol**:
```bash
# ALWAYS check system time before using dates in:
# - File timestamps
# - "Last Updated" fields
# - Log entries
# - Git commit messages
# - CI/CD timestamps
# - Documentation

date +%Y-%m-%d              # Get current date (YYYY-MM-DD)
date +"%Y-%m-%d %H:%M:%S"   # Get current datetime
```

**Critical Applications**:
- Setting "Last Updated" fields → MUST use `date +%Y-%m-%d`
- Timestamping logs/outputs → MUST verify current time
- Date-based file naming → MUST check date first
- Validating "no future dates" → MUST know current date

**Why This Matters**:
```
WRONG: Assume it's 2024 → Set all dates to 2024-10-18
  → Problem: Actually 2025, created incorrect timestamps
  → Result: Hours wasted fixing dates across entire codebase

CORRECT: Check `date` → Use actual current date
  → Benefit: Accurate timestamps from start
  → Result: No rework needed
```

---

## 3. Language Stack & Tooling

### Python → UV (MANDATORY)
```bash
uv init project && cd project && uv add pkg && uv run script.py
# ❌ NEVER: pip, poetry
```

### Zig → Comprehensive Skill Required
**ACTIVATE**: `zig-project-setup.md`, `zig-build-system.md`, `zig-memory-management.md`, all `zig-*.md` skills

**Covers**: Project setup (build.zig), allocators, defer/errdefer, testing, cross-compilation, comptime, C interop

**Standards**: Latest stable (0.13.x+), explicit allocators, comptime for zero-cost abstractions, defer/errdefer cleanup

### Rust → Standard Patterns
```bash
cargo new name && cargo add anyhow thiserror tokio
```
**Standards**: Ownership/borrowing first, Result<T,E>/Option<T>, iterators over loops, anyhow (apps), thiserror (libs), tokio (async)

### Go → TUI Development Skill Available
**ACTIVATE**: `bubbletea-architecture.md`, `ratatui-architecture.md` (Rust), all `bubbletea-*.md`/`ratatui-*.md`

**Standards**: Small interfaces (1-3 methods), explicit error returns (no panic), table-driven tests, standard toolchain

**TUI Framework**: Charm.sh (Bubble Tea + Lip Gloss + Bubbles)

### TypeScript → Strict Configuration
```json
{
  "compilerOptions": {
    "strict": true, "target": "ES2022", "module": "ESNext",
    "esModuleInterop": true, "skipLibCheck": false,
    "forceConsistentCasingInFileNames": true
  }
}
```
**Standards**: Strict mode mandatory, async/await over promises, ESM imports, Vitest/Jest testing

### Swift → iOS Native Skill Required
**ACTIVATE**: `swiftui-architecture.md`, `swift-concurrency.md`, `swiftdata-persistence.md`, all iOS skills (`swiftui-*.md`, `swift-*.md`, `ios-*.md`)

**Covers**: SwiftUI 5.0+, Swift 6.0 concurrency, MVVM, SwiftData/Charts/Navigation, UIKit integration

**Standards**: SwiftUI first (UIKit when needed), async/await over closures, Observation framework, iOS 17.0+ minimum

### Other Languages
**C/C++**: CMake 3.20+, C11/C17 or C++17/20, RAII, smart pointers, STL algorithms  
**Lean**: Lean 4 + mathlib4, readable tactics, snake_case, comprehensive docs

---

## 4. Cloud Platforms & Infrastructure

### Modal.com → Comprehensive Skill Required
**ACTIVATE**: `modal-functions-basics.md`, `modal-gpu-workloads.md`, `modal-web-endpoints.md`, all `modal-*.md`

**Covers**: App structure/decorators, GPU selection (L40S for cost/perf), image building (uv_pip_install), volumes, web endpoints (FastAPI), scheduled jobs, resource optimization

**Reference**: Check `docs/MODAL_REFERENCE.md` for project patterns

**Best Practices**:
- GPU: L40S (cost/perf), H100 (max perf), A100 (fallback), T4 (dev/light)
- Images: Use uv_pip_install, pin versions, layer strategically, dev with `--dev` flag
- Cleanup: ALWAYS stop dev resources after sessions (`modal app stop [name]`)

### Cloudflare Workers
```bash
wrangler dev && wrangler deploy
```
**Standards**: Workers Env, KV Storage, Durable Objects for state, edge-optimized

### Vercel
```bash
vercel dev && vercel --prod
```
**Standards**: Serverless Functions, Edge Functions, Env variables via UI, automatic HTTPS

### AWS Lambda
**Standards**: IAM roles principle of least privilege, Lambda layers for deps, CloudWatch for logging, API Gateway integration

### Other Cloud Services
**Supabase**: PostgreSQL + Auth + Storage + Realtime  
**Render**: Web services, DBs, cron jobs  
**Railway**: Full-stack apps, Postgres, Redis  
**Fly.io**: Global deployment, Postgres, persistent volumes

---

## 5. Project Initiation Protocol

### Step 1: Clarify Requirements
**MANDATORY QUESTIONS**:
- What's the core problem?
- Who's the primary user?
- What defines success?
- What's out of scope?
- Any performance/scale requirements?
- Existing systems to integrate?

### Step 2: Tech Stack Confirmation
**DO NOT ASSUME**. Always confirm:
- Frontend framework? (Next.js/React/Vue/Svelte)
- Backend/API? (FastAPI/Express/Go)
- Database? (Postgres/MySQL/Mongo/Redis)
- Auth? (Clerk/Auth0/Supabase/Custom)
- Deployment? (Vercel/Modal/Cloudflare/AWS)
- Mobile? (React Native/Swift/Expo)

### Step 3: Architecture Decision
```
Simple CRUD → Next.js + Supabase + Vercel
API-heavy → FastAPI + Postgres + Modal/Render
ML/AI → Modal.com + GPU workers + FastAPI endpoints
Real-time → WebSockets + Redis + Fly.io
Mobile → Swift (iOS native) or React Native (cross-platform)
CLI/TUI → Go (Bubble Tea) or Rust (Ratatui)
```

### Step 4: Discover Relevant Skills (UPDATED 2025-10-18)
Before starting specialized work:
1. **New repository?** Use `skill-repo-discovery.md` to analyze tech stack → Activate identified skills
2. **User prompt/request?** Use `skill-prompt-discovery.md` to extract intent → Activate identified skills
3. **Manual search?** Check `skills/_INDEX.md` or search by pattern: `modal-*.md`, `swiftui-*.md`, `zig-*.md`
4. Read only relevant skills (don't read all skills upfront)
5. Compose multiple skills for complex workflows

**Meta skills enable intelligent discovery** (all have YAML frontmatter for agent compatibility):
- Repository onboarding: `skill-repo-discovery.md` analyzes codebase → maps to existing skills
- Prompt analysis: `skill-prompt-discovery.md` extracts tech signals → activates relevant skills
- Gap identification: `skill-repo-planning.md` or `skill-prompt-planning.md` → plans missing skills

**Quality assurance**: All 132 skills are validated by CI for:
- YAML frontmatter compliance (agent_skills_spec.md)
- Date accuracy (no future dates)
- Code syntax (Python blocks validated)
- Size optimization (target <500 lines)

### Step 5: Project Structure
```
Language → Init Command → Structure
──────────────────────────────────────────
Python   → uv init → src/, tests/, pyproject.toml
Zig      → zig init → src/, build.zig, build.zig.zon
Rust     → cargo new → src/, Cargo.toml, Cargo.lock
Go       → go mod init → cmd/, pkg/, go.mod
TS       → pnpm create vite → src/, package.json
```

### Step 6: Version Control
```bash
git init && git checkout -b main
git add . && git commit -m "Initial commit"
gh repo create --source=. --remote=origin --push
```

---

## 6. Testing & Validation

### CRITICAL TESTING PROTOCOL

**ABSOLUTE RULE**: NEVER run tests before committing changes to git

**CORRECT FLOW** (MANDATORY):
```bash
# 1. Make changes
[edit files]

# 2. COMMIT FIRST (non-negotiable)
git add . && git commit -m "Description"

# 3. VERIFY COMMIT
git log -1 --oneline

# 4. KILL OLD TESTS (critical)
pkill -f "pytest" || pkill -f "test"

# 5. RUN TESTS IN BACKGROUND
pytest tests/ > /tmp/test_$(date +%Y%m%d_%H%M%S).log 2>&1 &
# or: ./run_tests.sh > /tmp/test_output.log 2>&1 &

# 6. WAIT FOR COMPLETION (do NOT interrupt)
jobs                    # Check if still running
wait                    # Block until complete

# 7. VERIFY RESULTS
tail -f /tmp/test_output.log
ls -lht /tmp/test_*.log | head -1  # Verify timestamp
```

### Why This Order Matters
```
WRONG: Code → Test → Commit
  → Problem: Tests run against uncommitted code
  → Result: False positives, hours wasted debugging

CORRECT: Code → Commit → Kill Old → Test
  → Benefit: Tests run against committed code
  → Result: Valid results, clear debugging path
```

### Testing Standards by Language
```
Python: pytest + pytest-cov (uv add --dev)
Rust: cargo test + criterion (benchmarks)
Go: go test -v ./... -cover
Zig: zig build test
TS: Vitest or Jest
Swift: XCTest (XCTAssertEqual, XCTAssertTrue)
```

### Test Structure Pattern
```
tests/
  unit/          # Pure functions
  integration/   # System interactions
  e2e/           # Full workflows
  fixtures/      # Test data
  conftest.py    # Shared setup (Python)
```

---

## 7. Version Control & Git

### Branch Strategy
```bash
# Feature work
git checkout -b feature/name

# Bug fixes
git checkout -b fix/issue-name

# Experiments
git checkout -b experiment/idea
```

### Commit Guidelines
**Good commits**:
- `feat: Add user authentication`
- `fix: Resolve race condition in worker pool`
- `refactor: Extract validation logic`
- `test: Add edge cases for parser`
- `docs: Update API documentation`

**Bad commits**:
- `wip`, `stuff`, `fixes`, `update` (too vague)

### Commit Message Rules (MANDATORY)

**ABSOLUTE RULE**: NEVER include AI attribution unless specifically requested by user

**FORBIDDEN in commits** (unless user explicitly requests):
```
❌ "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
❌ "Co-Authored-By: Claude <noreply@anthropic.com>"
❌ "Generated by AI"
❌ "Created with Claude"
❌ Any similar AI attribution or branding
```

**Why**:
- Commits should reflect actual work done, not tooling used
- Attribution clutters git history
- User controls commit authorship and attribution
- Professional commits focus on changes, not process

**When to include**:
- ONLY when user explicitly asks: "add AI attribution" or "include Claude credit"
- Otherwise: NEVER add attribution automatically

### Pull Request Workflow
```bash
# Push feature branch
git push -u origin feature/name

# Create PR
gh pr create --title "Add user auth" --body "Implements JWT-based authentication"

# After approval & merge
git checkout main && git pull
git branch -d feature/name
```

### Critical Rules
- NEVER commit directly to main for features (hotfixes only)
- NEVER force push to main or shared branches
- ALWAYS pull before pushing to avoid conflicts
- ALWAYS use descriptive commit messages
- ALWAYS commit .beads/issues.jsonl with state changes

---

## 8. Frontend Development

### Elegant Design Skill (RECOMMENDED)

**ACTIVATE**: `elegant-design/SKILL.md` when building user interfaces that need professional polish

**Covers**: World-class accessible interfaces, chat/messaging UIs, terminal/code display, streaming content, design systems (shadcn/ui, daisyUI, HeroUI), WCAG compliance, Core Web Vitals optimization

**Use When**:
- Building web applications with React/Next.js
- Creating developer tools or technical interfaces
- Designing interfaces with chat, terminals, or code display
- Implementing real-time or streaming features
- Ensuring accessibility and responsive design

**Key Features**:
- **Design Foundation**: Typography (Geist + JetBrains Mono), colors, spacing, layout patterns
- **Interactive Elements**: Chat interfaces, terminal emulators, code syntax highlighting, streaming/loading states, diffs/log viewers
- **Implementation**: Component architecture, WCAG 2.1 AA compliance, performance optimization, comprehensive testing
- **Design Systems**: shadcn/ui (primary), daisyUI, HeroUI with best practices

**Quick Reference**:
```
Simple UI: Read foundation/ files → Use design system components
Chat/Terminal/Code: Read SKILL.md → Read interactive/ guides → Implement
Complex interfaces: Follow full workflow (discovery → foundation → interactive → implementation)
```

See `skills/elegant-design/SKILL.md` for complete guidance and workflows.

### Next.js + shadcn/ui (MANDATORY)

**Step 1: Browse Blocks FIRST**
```bash
# Before building anything, check available blocks
open https://ui.shadcn.com/blocks
```

**Step 2: Choose Block(s)**
```
CORRECT: Find block that matches → Install → Customize minimally
WRONG: Build custom component → Reinvent wheel
```

**Step 3: Install Components**
```bash
npx shadcn@latest add button card dialog
npx shadcn@latest add-block sidebar-01  # Specific block
```

**Critical Rules**:
1. ALWAYS browse blocks before custom components
2. NEVER restructure shadcn components (breaks updates)
3. ALWAYS customize via Tailwind classes (not component changes)
4. ALWAYS handle loading/error states in UI

### Styling Standards
```tsx
// Loading state
{isLoading && <Spinner />}

// Error state
{error && <Alert variant="destructive">{error.message}</Alert>}

// Empty state
{items.length === 0 && <EmptyState />}

// Success state
{items.map(item => <Card key={item.id}>{item.name}</Card>)}
```

### Responsive Design
```tsx
// Use Tailwind responsive prefixes
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
```

### Theme Configuration
```bash
# Get theme from shadcn
open https://ui.shadcn.com/themes
# Copy variables to globals.css
```

---

## 9. Skills System

### Philosophy: Atomic Skills
**Old approach**: Monolithic skills `/zig-dev`, `/modal-dev` (too large)
**New approach**: Atomic, composable skills (~300 lines avg, <500 line guideline)

### Quality Standards (as of 2025-10-23)
- ✅ **135 skills** with YAML frontmatter (agent_skills_spec.md compliant)
- ✅ **0 future dates** - all dates validated by CI
- ✅ **Automated testing** - code syntax validation in CI
- 🔄 **Size optimization** - 89 skills >500 lines identified for splitting

### Discovery Pattern
```bash
# 0. AUTOMATIC DISCOVERY (Recommended)
# For new repos: Use skill-repo-discovery.md to analyze codebase → activates relevant skills
# For user requests: Use skill-prompt-discovery.md to extract intent → activates skills

# 1. Manual: Identify domain
"I need Zig memory management" → zig-memory-management.md

# 2. Manual: Search by pattern
ls skills/zig-*.md
ls skills/modal-*.md
ls skills/swiftui-*.md
ls skills/api-*.md
ls skills/test-*.md
ls skills/react-*.md
ls skills/cicd/*.md
ls skills/infrastructure/*.md
ls skills/observability/*.md
ls skills/formal/*.md
ls skills/ml/*.md
ls skills/deployment/*.md
ls skills/math/*.md
ls skills/mobile/*.md

# 3. Read relevant skills only (NOT all upfront)
Read zig-memory-management.md, zig-testing-patterns.md

# 4. Compose for complex workflows
Read beads-workflow.md + beads-context-strategies.md + beads-multi-session-patterns.md
```

### Skills Catalog (135 Total)

**Core Categories** (77 skills):
- **API Design** (7): REST, GraphQL, auth/authz, rate limiting, versioning, error handling
- **Testing** (6): Unit, integration, e2e, TDD, coverage, performance testing
- **Containers** (5): Dockerfile optimization, Compose, security, networking, registries
- **Frontend** (9): Elegant design (chat/terminal/code UIs), React patterns, Next.js App Router, state/data/forms, a11y, performance, SEO
- **Database** (11): Postgres (optimization, migrations, schema), MongoDB, Redis, Redpanda/Kafka streaming, Apache Iceberg, DuckDB analytics, pooling, ORMs, selection
- **Workflow & Tasks** (6): Beads workflow, context strategies, multi-session, dependency management, typed-holes refactoring
- **Quality & Content Review** (1): Anti-slop detection and cleanup (text, code, design)
- **Meta Skills** (4): Skill discovery and planning for repositories and prompts
  - Discovery: `skill-repo-discovery.md` (analyze repos), `skill-prompt-discovery.md` (analyze prompts)
  - Planning: `skill-repo-planning.md` (plan repo skills), `skill-prompt-planning.md` (plan prompt skills)
  - **Use proactively**: Run discovery skills when encountering new repos or complex user requests
- **iOS/Swift** (6): SwiftUI architecture, Swift concurrency, SwiftData, networking, UIKit integration, testing
- **Modal.com** (8): Functions, GPU workloads, web endpoints, volumes, scheduling, troubleshooting, debugging, optimization
- **Networking** (5): Tailscale, mTLS, Mosh, NAT traversal, resilience patterns
- **TUI** (5): Bubble Tea/Ratatui architecture, Lip Gloss styling, Bubbles components, state management
- **Zig** (6): Project setup, memory management, testing, comptime, cross-compilation, C interop

**Advanced Infrastructure** (25 skills):
- **CI/CD** (5): GitHub Actions workflows, testing strategy, deployment patterns, optimization, security
- **Infrastructure** (6): Terraform patterns, AWS serverless, Kubernetes basics, Cloudflare Workers, security, cost optimization
- **Observability** (5): Structured logging, metrics instrumentation, distributed tracing, alerting strategy, dashboard design
- **Real-time** (4): WebSocket implementation, Server-Sent Events, real-time sync, pub/sub patterns
- **Data Pipeline** (5): ETL patterns, stream processing, batch processing, data validation, pipeline orchestration

**Specialized Domains** (33 skills):
- **SAT/SMT Solvers** (3): Z3 solver basics, SAT solving strategies, SMT theory applications
- **Lean 4** (4): Proof basics, tactics, mathlib4, theorem proving
- **Constraint Satisfaction** (3): CSP modeling, constraint propagation, backtracking search
- **Heroku** (3): Deployment, add-ons, troubleshooting
- **Netlify** (3): Deployment, functions, optimization
- **LLM Fine-tuning** (4): Unsloth, HuggingFace AutoTrain, dataset preparation, LoRA/PEFT
- **Diffusion Models** (3): Diffusion basics, Stable Diffusion deployment, fine-tuning
- **Advanced Mathematics** (4): Linear algebra, optimization algorithms, numerical methods, probability/statistics
- **React Native** (4): Setup, navigation, native modules, performance

**Quick Category Reference**:
```
API/Backend:    api-*.md (7) | database-*.md, postgres-*.md, redpanda-*.md, apache-*.md, duckdb-*.md (11) | orm-*.md (1)
Testing:        test-*.md, unit-*.md, integration-*.md, e2e-*.md (6) | performance-testing.md
Containers:     dockerfile-*.md, docker-*.md, container-*.md (5)
Frontend:       react-*.md (5) | nextjs-*.md (2) | web-*.md, frontend-*.md (3)
DevOps/Infra:   cicd/ (5) | infrastructure/ (6) | observability/ (5)
Data:           data/ (5) | realtime/ (4)
Specialized:    modal-*.md (8) | swiftui-*.md, swift-*.md, ios-*.md (6) | zig-*.md (6)
Workflow:       beads-*.md (4) | typed-holes-refactor/ (1 skill + 3 refs + 5 scripts) | tui-*.md (5) | network-*.md (5)
Quality:        anti-slop/ (1 skill + 3 reference guides + 2 scripts)
Meta:           skill-*.md (5 including skill-creation.md)
Formal:         formal/z3-*.md, formal/sat-*.md, formal/smt-*.md (3) | formal/lean-*.md (4) | formal/csp-*.md (3)
ML:             ml/unsloth-*.md, ml/llm-*.md, ml/lora-*.md (4) | ml/diffusion-*.md (3)
Deployment:     deployment/heroku-*.md (3) | deployment/netlify-*.md (3)
Math:           math/*.md (4)
Mobile:         mobile/react-native-*.md (4)
```

### Key Principles
1. **Discover**: Use automated discovery skills OR search by pattern/category
2. **Compose**: Combine skills for complex workflows
3. **Apply**: Read only what you need, when you need it
4. **Iterate**: Add more skills during work as requirements emerge
5. **Validate**: Skills are CI-tested for syntax and frontmatter compliance

### Discovery Workflow (UPDATED 2025-10-18)
0. **New repo/codebase?** Run `skill-repo-discovery.md` → Activate identified skills
1. **User request?** Run `skill-prompt-discovery.md` → Activate identified skills
2. **Quick task?** Use Quick Category Reference for pattern matching
3. **Need workflow?** Check `skills/_INDEX.md` → "Skill Combination Examples"
4. **Deep dive?** Search `skills/_INDEX.md` by technology/task/problem domain
5. **Emergency?** Read relevant skill directly: `skills/api-*.md`, `skills/cicd/*.md`

**Full catalog**: `skills/_INDEX.md` (135 skills, workflows, search patterns, combinations)

### Skill Quality Assurance
All skills now include:
- **YAML frontmatter** with `name` and `description` (enables programmatic discovery)
- **Accurate dates** validated by CI (no future dates allowed)
- **Code validation** via smoke tests (Python syntax checked automatically)
- **Size guidelines** (<500 lines recommended; see `ENHANCEMENT_PLAN.md` for split plans)

---

## 10. Anti-Patterns & Violations

### Critical Violations (Hours Wasted)
```
❌ NEVER: Run tests before committing
   → Hours debugging stale code

❌ NEVER: Run tests in background while changing code
   → Invalid results, wasted time

❌ NEVER: Report test results without verifying timestamps
   → False positives/negatives

❌ NEVER: Assume current date/time without checking
   → Incorrect timestamps, hours fixing dates

❌ NEVER: Leave TODO, mocks, or stubs
   → Implement now OR create Beads issue

❌ NEVER: Commit directly to main for features
   → Use feature branches + PRs

❌ NEVER: Force push to main/shared branches
   → Lost work, broken history

❌ NEVER: Accept vague requirements
   → Rework, missed requirements
```

### Moderate Violations (Quality Issues)
```
❌ Don't assume tech stack without confirmation
❌ Don't skip shadcn blocks exploration
❌ Don't restructure shadcn components
❌ Don't use pip/poetry instead of uv
❌ Don't skip loading/error states
❌ Don't deploy without environment config
❌ Don't agree reflexively without analysis
❌ Don't leave cloud resources running (dev/test)
❌ Don't skip atomic skill discovery
❌ Don't add AI attribution to commits (unless user requests)
```

### Severity Matrix
| Severity | Impact | Examples |
|----------|--------|----------|
| 🔴 Critical | Hours wasted | Test before commit, background tests, stale results |
| 🟡 High | Quality issues | No pushback, skip blocks, wrong package manager |
| 🟢 Medium | Tech debt | Missing error states, unoptimized resources |

### Recovery Protocol
1. STOP immediately
2. ASSESS damage (what's invalid?)
3. RESET to last known good state
4. FOLLOW correct procedure from start
5. DOCUMENT what went wrong

---

## 11. Quick Reference

### Language Commands
```bash
# Python: uv init && uv add pkg && uv run script.py
# Zig: zig init && zig build && zig build test
# Rust: cargo new && cargo add anyhow tokio && cargo build
# Go: go mod init && go get package && go run .
# TS: pnpm create vite@latest && pnpm install && pnpm dev
```

### Cloud Commands
```bash
# Modal: modal app deploy && modal app stop [name]
# Cloudflare: wrangler dev && wrangler deploy
# AWS Lambda: aws lambda create-function && aws lambda invoke
```

### Git Commands
```bash
# Start: git checkout -b feature/name
# Commit: git add . && git commit -m "message"
# Push: git push -u origin feature/name
# PR: gh pr create --title "Title" --body "Description"
# Clean: git branch -d feature/name
```

### Beads Commands
```bash
# Start: go install github.com/steveyegge/beads/cmd/bd@latest
# Import: bd import -i .beads/issues.jsonl
# Ready: bd ready --json --limit 5
# Create: bd create "Task" -t bug -p 1 --json
# Deps: bd dep add bd-5 bd-3 --type blocks
# Update: bd update bd-5 --status in_progress --json
# Close: bd close bd-5 --reason "Complete" --json
# Export: bd export -o .beads/issues.jsonl
# Commit: git add .beads/issues.jsonl && git commit -m "Update issues"
```

### Testing Commands
```bash
# Correct flow:
git add . && git commit -m "Changes"
git log -1 --oneline
pkill -f "test"
./run_tests.sh > /tmp/test_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

### UI Commands
```bash
# Browse: open https://ui.shadcn.com/blocks
# Install: npx shadcn@latest add button
# Theme: open https://ui.shadcn.com/themes
```

---

## Master Decision Tree

```
New request
  ↓
Need dates/timestamps? YES → Check `date` command FIRST
  ↓
Specialized domain? → Activate skills
  ↓
Requirements clear? NO → ASK
  ↓
Tech stack confirmed? NO → CONFIRM
  ↓
Edge cases considered? NO → CHALLENGE
  ↓
Testing strategy? NONE → PLAN
  ↓
Cloud resources? YES → PLAN SHUTDOWN
  ↓
Using Beads? YES → Follow workflow
  ↓
Making changes? YES → Feature branch
  ↓
Need validation? YES → Testing protocol
  ↓
Session ending? YES → Export, commit, cleanup
  ↓
Execute
```

---

## Enforcement Checklist

Before completing ANY task:
```
[ ] Verified current date/time (if using timestamps/dates)
[ ] Discovered relevant skills (use skill-repo-discovery.md or skill-prompt-discovery.md)
[ ] Read atomic skills from skills/ directory (check skills/_INDEX.md)
[ ] Challenged vague requirements
[ ] Confirmed tech stack and deployment
[ ] Followed correct package manager (uv, cargo, etc.)
[ ] Used shadcn blocks before custom components
[ ] Planned loading/error states
[ ] Used feature branch (not direct to main)
[ ] Followed testing protocol (commit first!)
[ ] Managed context with /context or /compact
[ ] Cleaned up cloud resources
[ ] Exported Beads state (if using bd)
[ ] Committed and pushed changes (NO AI attribution unless requested)
```

**If ANY checkbox unchecked, stop and address it.**

### Skills Quality Standards (Updated 2025-10-18)
```
[ ] All skills have YAML frontmatter (name, description)
[ ] No future-dated "Last Updated" fields
[ ] Code blocks are syntactically valid
[ ] New skills should be <500 lines (guideline from skill-creation.md)
[ ] CI workflows validate quality on every commit
```

---

## Conclusion

These guidelines prevent common pitfalls:

1. Testing violations → Hours debugging stale code
2. Assuming dates/time → Hours fixing incorrect timestamps
3. Vague requirements → Rework and missed features
4. Wrong tools → Dependency hell and conflicts
5. Skipped skills → Reinventing solved problems
6. Direct to main → Broken builds and lost work
7. Running cloud resources → Unexpected bills
8. Missing context → Lost state across sessions

**Follow decision trees. Verify dates first. Activate skills. Challenge assumptions. Commit before testing. Clean up resources.**

The reward is high-quality, maintainable code delivered efficiently.
