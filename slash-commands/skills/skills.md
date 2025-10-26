---
description: Discover and activate relevant skills with progressive loading (284 skills, 27 gateways)
argument-hint: [category|search-term] (optional)
---

# Skills Discovery Assistant

You are helping the user discover and activate relevant skills from their skills library using the progressive loading architecture.

## Your Task

**User's Request:** `$ARGUMENTS`

Follow these steps:

### 1. Read Skills Catalog

First, read the master catalog with gateway architecture:
```bash
cat skills/README.md
```

This catalog includes:
- **284 total skills** across 30 categories
- **27 gateway skills** for auto-discovery
- **Progressive loading** architecture (60-84% context reduction)

### 2. Detect Project Context

Analyze the current directory to understand the project:
```bash
# List files to detect project type
ls -la | head -30

# Check for language/framework indicators
ls *.{json,md,go,py,rs,swift,zig,toml,yaml,yml} 2>/dev/null | head -20
```

**Technology Detection → Gateway Mapping:**
- `package.json` → **discover-frontend** (React, Next.js, TypeScript)
- `go.mod` → **discover-backend** (Go), may also need discover-api
- `requirements.txt`, `pyproject.toml`, `uv.lock` → **discover-backend** (Python), **discover-ml** if ML work
- `Cargo.toml` → **discover-backend** (Rust), **discover-wasm** if WASM
- `build.zig` → Zig skills at root level
- `*.swift`, `*.xcodeproj` → **discover-mobile** (iOS/Swift)
- `Dockerfile`, `docker-compose.yml` → **discover-containers**
- `.beads/` → Beads workflow skills (root level)
- `tests/`, `__tests__/` → **discover-testing**
- Database files → **discover-database**

### 3. Analyze Conversation Context

Review the current conversation for:
- Technologies mentioned (frameworks, tools, databases)
- Problems discussed (performance, debugging, deployment)
- Explicit skill requests
- Work phase (planning, implementation, testing, deployment)

Map to gateway keywords:
- "REST API" → **discover-api**
- "GraphQL" → **discover-api**
- "Postgres", "MongoDB", "Redis" → **discover-database**
- "Docker", "Kubernetes" → **discover-containers**
- "CI/CD", "GitHub Actions" → **discover-cicd**
- "observability", "logging", "metrics" → **discover-observability**
- "caching", "CDN" → **discover-caching**
- "debugging", "GDB", "profiling" → **discover-debugging**
- "build", "Make", "CMake" → **discover-build-systems**
- "ML", "model", "training" → **discover-ml**
- "math", "linear algebra" → **discover-math**
- "compiler", "parser", "AST" → **discover-plt**

### 4. Provide Contextual Recommendations

Based on the argument provided:

**If NO ARGUMENT (default view):**

Display in this format:
```
━━━ SKILLS DISCOVERY ━━━

RECOMMENDED GATEWAYS FOR THIS PROJECT:
→ discover-[category] - [Gateway description]
  Load: cat skills/discover-[category]/SKILL.md
  Then: cat skills/[category]/INDEX.md for full details

→ discover-[category] - [Gateway description]
  Load: cat skills/discover-[category]/SKILL.md

PROGRESSIVE LOADING ARCHITECTURE:
Gateway Skills    (~200 lines) → Auto-discovered, lightweight
Category Indexes  (~300 lines) → Detailed skill listings
Individual Skills (~400 lines) → Full content

Context Savings: 60-84% reduction vs monolithic index

CATEGORIES (284 total skills across 27 gateways):
Frontend (8) | Database (8) | API (7) | Testing (6) | ML (30) | Math (19)
Debugging (14) | Build Systems (8) | Caching (7) | Observability (8)
Containers (5) | CI/CD (4) | PLT (13) | Formal (10) | Cloud (13)
[View full catalog: skills/README.md]

COMMANDS:
/skills api              - View API skills gateway
/skills frontend         - View frontend skills
/skills postgres         - Search for 'postgres' skills
/skills list             - Show all 27 gateway categories
```

Recommend 2-4 gateway skills that match:
- Detected technologies in the current directory
- Topics discussed in conversation
- Common workflows for the project type

### Gateway-First Recommendations:

**Format:**
```
RECOMMENDED GATEWAYS:
→ discover-api
  Keywords: REST, GraphQL, authentication, authorization, rate limiting
  Load: cat skills/discover-api/SKILL.md (~200 lines)
  Then: cat skills/api/INDEX.md for all 7 API skills

→ discover-database
  Keywords: PostgreSQL, MongoDB, Redis, query optimization
  Load: cat skills/discover-database/SKILL.md
  Then: cat skills/database/INDEX.md for all 8 database skills
```

**If ARGUMENT = category name:**

Two scenarios:

**A) If discover-{category} gateway exists:**
```
━━━ {CATEGORY} SKILLS GATEWAY ━━━

OVERVIEW:
Gateway: discover-{category}
Total Skills: [N]
Keywords: [comma-separated keywords]

QUICK REFERENCE:
[List 3-5 key skills with one-line descriptions]

LOAD FULL CATEGORY:
cat skills/{category}/INDEX.md (~300 lines)
  → Detailed descriptions for all skills
  → Usage triggers for each skill
  → Common workflow combinations

LOAD GATEWAY:
cat skills/discover-{category}/SKILL.md (~200 lines)
  → Lightweight overview
  → Auto-discovery triggers

PROGRESSIVE LOADING:
1. Gateway (you're here)    - ~200 lines
2. Category INDEX           - ~300 lines
3. Specific skill           - ~400 lines

[Load full index: cat skills/{category}/INDEX.md]
```

**B) If searching root-level skills:**
Check for skills like:
- `skill-*.md` (meta skills)
- `beads-*.md` (workflow skills)
- Root-level technology skills

Display similarly but note they're at root level.

**Example for `/skills api`:**
```
━━━ API SKILLS GATEWAY ━━━

OVERVIEW:
Gateway: discover-api
Total Skills: 7
Keywords: REST, GraphQL, authentication, authorization, rate limiting

SKILLS IN THIS CATEGORY:
1. rest-api-design - RESTful resource modeling, HTTP semantics
2. graphql-schema-design - GraphQL types, resolvers, N+1 prevention
3. api-authentication - JWT, OAuth 2.0, API keys, sessions
4. api-authorization - RBAC, ABAC, policy engines
5. api-rate-limiting - Token bucket, sliding window algorithms
6. api-versioning - API versioning, deprecation, compatibility
7. api-error-handling - RFC 7807, validation errors

LOAD FULL DETAILS:
cat skills/api/INDEX.md
  → Detailed descriptions, use cases, workflows

LOAD GATEWAY:
cat skills/discover-api/SKILL.md
  → Lightweight overview, common workflows

LOAD SPECIFIC SKILL:
cat skills/api/rest-api-design.md
cat skills/api/api-authentication.md

[Back to overview: /skills]
```

**If ARGUMENT = search term:**

Search across:
- Gateway skill descriptions (discover-*/SKILL.md)
- Category INDEX.md files
- skills/README.md catalog
- Root-level skill filenames

Display matching gateway categories FIRST, then specific skills:
```
━━━ SEARCH RESULTS: 'postgres' ━━━

GATEWAY MATCH:
→ discover-database
  Keywords: PostgreSQL, MongoDB, Redis, query optimization
  Contains postgres-specific skills
  Load: cat skills/discover-database/SKILL.md

SPECIFIC SKILLS:
→ postgres-query-optimization.md - skills/database/
  Debug slow queries, EXPLAIN plans, index design
  Load: cat skills/database/postgres-query-optimization.md

→ postgres-migrations.md - skills/database/
  Schema changes, zero-downtime deployments
  Load: cat skills/database/postgres-migrations.md

→ postgres-schema-design.md - skills/database/
  Designing schemas, relationships, data types
  Load: cat skills/database/postgres-schema-design.md

RELATED GATEWAYS:
→ discover-observability (database monitoring)
→ discover-caching (Redis with Postgres)

[Load category: cat skills/database/INDEX.md]
[Refine search: /skills postgres optimization]
```

**If ARGUMENT = "list":**

Show all 27 gateway categories:
```
━━━ ALL GATEWAY CATEGORIES (284 total skills) ━━━

BACKEND & DATA (40 skills):
  discover-api (7)         - REST, GraphQL, auth, rate limiting
  discover-database (8)    - Postgres, MongoDB, Redis, optimization
  discover-data (5)        - ETL, streaming, batch processing
  discover-caching (7)     - Redis, CDN, HTTP caching, invalidation

FRONTEND & MOBILE (12 skills):
  discover-frontend (8)    - React, Next.js, state management, a11y
  discover-mobile (4)      - iOS, Swift, SwiftUI, concurrency

TESTING & QUALITY (6 skills):
  discover-testing (6)     - Unit, integration, e2e, TDD, coverage

INFRASTRUCTURE (68 skills):
  discover-containers (5)  - Docker, Kubernetes, security
  discover-cicd (4)        - GitHub Actions, pipelines
  discover-cloud (13)      - Modal, AWS, GCP, serverless
  discover-infra (6)       - Terraform, IaC, Cloudflare Workers
  discover-observability (8) - Logging, metrics, tracing, alerts
  discover-debugging (14)  - GDB, LLDB, profiling, memory leaks
  discover-build-systems (8) - Make, CMake, Gradle, Maven, Bazel
  discover-deployment (6)  - Netlify, Heroku, platforms
  discover-realtime (4)    - WebSockets, SSE, pub/sub

SPECIALIZED DOMAINS (158 skills):
  discover-ml (30)         - Training, RAG, embeddings, evaluation
  discover-math (19)       - Linear algebra, topology, category theory
  discover-plt (13)        - Compilers, type systems, verification
  discover-formal (10)     - SAT/SMT, Z3, Lean, theorem proving
  discover-wasm (4)        - WebAssembly fundamentals, Rust to WASM
  discover-ebpf (4)        - eBPF tracing, networking, security
  discover-ir (5)          - LLVM IR, compiler optimizations
  discover-modal (2)       - Modal functions, scheduling
  discover-engineering (4) - Code review, documentation, leadership
  discover-product (4)     - Product strategy, roadmaps
  discover-collab (5)      - Collaboration, code review, pair programming

AGENT SKILLS (3):
  elegant-design          - UI/UX design, accessibility, design systems
  anti-slop               - Detect/eliminate AI-generated patterns
  typed-holes-refactor    - Systematic TDD-based refactoring

ROOT-LEVEL SKILLS (~7):
  skill-*.md              - Meta skills for discovery and creation
  beads-*.md              - Workflow and task management
  [Various tech-specific] - Zig, iOS, TUI, networking skills

[View category: /skills frontend]
[Search: /skills kubernetes]
[Full catalog: cat skills/README.md]
```

### 5. Output Requirements

**Format Guidelines:**
- Use Unicode box drawing (━ ─ │) for section headers
- Keep output under 30 lines for default view
- Use `→` for list items
- Include actionable next steps with actual commands
- Show progressive loading path (gateway → index → skill)
- Emphasize context efficiency (60-84% reduction)
- Group related items logically

**Progressive Loading Messaging:**
Always show users the three-tier architecture:
1. Gateway (~200 lines) - Lightweight overview
2. Category INDEX (~300 lines) - Detailed listings
3. Individual skill (~400 lines) - Full content

**Tone:**
- Helpful and direct
- Low noise, high signal
- Focus on relevance to current work
- Emphasize context efficiency
- Encourage exploration without overwhelming

**DO NOT:**
- Modify any skill files
- Create new skills
- Change README.md or INDEX files
- Make assumptions about skills you haven't read
- Display full skill contents (only summaries)
- Reference _INDEX.md (it's archived)

### 6. Graceful Fallbacks

**If skills/README.md not found:**
```
Skills catalog not found at skills/README.md

Expected structure:
skills/
├── README.md              (Master catalog)
├── discover-*/SKILL.md    (27 gateway skills)
└── {category}/INDEX.md    (Category indexes)

Is your repository in a different location?
```

**If no matches for search:**
```
No skills found matching '$ARGUMENTS'

Try:
- Broader search term
- View all gateways: /skills list
- Browse full catalog: cat skills/README.md
- Check a category: /skills api
```

**If empty project directory:**
```
━━━ SKILLS DISCOVERY ━━━

No project files detected in current directory.

GENERAL-PURPOSE GATEWAYS:
→ discover-collab - Collaboration, documentation, CodeTour walkthroughs
  Load: cat skills/discover-collab/SKILL.md

ROOT-LEVEL SKILLS:
→ beads-workflow.md - Multi-session task management
→ skill-creation.md - Creating new atomic skills
→ skill-repo-discovery.md - Discover skills for repositories

[View all: /skills list]
[Browse catalog: cat skills/README.md]
```

## Remember

- This is a **discovery tool** using progressive loading
- Read skills/README.md to get accurate information (NOT _INDEX.md - that's archived)
- Recommend **gateway skills first**, then specific skills
- Show the loading path: gateway → index → skill
- Emphasize **60-84% context savings** vs monolithic approach
- Match skills to project context when possible
- Keep output concise and actionable
- Never modify the skills library
- Encourage exploration with clear, copy-paste commands
- The architecture is: 284 skills, 27 gateways, 30 categories
