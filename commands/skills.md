---
description: Discover and activate relevant skills (410+ skills, 23 gateways)
argument-hint: [category|search-term] (optional)
context: fork
---

# Skills Discovery Assistant

You are helping the user discover and activate relevant skills from their skills library.

## Your Task

**User's Request:** `$ARGUMENTS`

Follow these steps:

### 1. Read Skills Catalog

Read the master catalog:
Read ../skills/README.md


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
- `go.mod` → **discover-api** (Go), **discover-infra**
- `requirements.txt`, `pyproject.toml`, `uv.lock` → **discover-api** (Python), **discover-ml** if ML work
- `Cargo.toml` → **discover-wasm** if WASM, **discover-api** for web services
- `build.zig` → **discover-zig**
- `*.swift`, `*.xcodeproj` → **discover-mobile** (iOS/Swift)
- `Dockerfile`, `docker-compose.yml` → **discover-infra**
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
- "Docker", "Kubernetes", "Terraform", "AWS", "GCP" → **discover-infra**
- "CI/CD", "GitHub Actions", "Make", "CMake", "Bazel" → **discover-cicd**
- "TCP", "HTTP/2", "gRPC", "Nginx", "proxy" → **discover-networking**
- "debugging", "GDB", "profiling", "logging", "metrics" → **discover-debugging**
- "caching", "CDN", "Redis cache" → **discover-database**
- "ML", "model", "training", "Modal" → **discover-ml**
- "math", "linear algebra" → **discover-math**
- "compiler", "parser", "AST", "eBPF", "Z3", "Lean" → **discover-systems-theory**
- "diagram", "flowchart", "Mermaid" → **discover-engineering**
- "MCP", "MCP server", "tool protocol" → **discover-mcp**
- "agent", "agentic", "tool use", "task decomposition" → **discover-agentic**
- "WebSocket", "SSE", "CRDT", "consensus" → **discover-distributed**
- "product", "roadmap", "collaboration", "GitHub workflows" → **discover-product**

### 4. Provide Contextual Recommendations

Based on the argument provided:

**If NO ARGUMENT (default view):**

Display in this format:
```
RECOMMENDED FOR THIS PROJECT:
→ discover-[category]
  Read ../skills/discover-[category]/SKILL.md

→ discover-[category]
  Read ../skills/discover-[category]/SKILL.md

CATEGORIES (410+ skills):
Frontend (8) | Database (8) | API (7) | Testing (6) | Diagrams (8) | ML (30)
Math (19) | Debugging (14) | Build Systems (8) | Caching (7) | Observability (8)
Containers (5) | CI/CD (4) | PLT (13) | Formal (10) | Cloud (13)

COMMANDS:
/skills api              - View API skills
/skills frontend         - View frontend skills
/skills postgres         - Search for 'postgres'
/skills list             - Show all categories
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
  Read ../skills/discover-api/SKILL.md

→ discover-database
  Keywords: PostgreSQL, MongoDB, Redis, query optimization
  Read ../skills/discover-database/SKILL.md
```

**If ARGUMENT = category name:**

Two scenarios:

**A) If discover-{category} gateway exists:**
```
{CATEGORY} SKILLS
Total: [N] skills
Keywords: [comma-separated keywords]

KEY SKILLS:
[List 3-5 key skills with one-line descriptions]

LOAD:
Read ../skills/{category}/INDEX.md          # All skills in category
Read ../skills/discover-{category}/SKILL.md # Gateway overview
```

**B) If searching root-level skills:**
Check for skills like:
- `skill-*.md` (meta skills)
- `beads-*.md` (workflow skills)
- Root-level technology skills

Display similarly but note they're at root level.

**Example for `/skills api`:**
```
API SKILLS (7 total)
Keywords: REST, GraphQL, authentication, authorization, rate limiting

SKILLS:
1. rest-api-design - RESTful resource modeling, HTTP semantics
2. graphql-schema-design - GraphQL types, resolvers, N+1 prevention
3. api-authentication - JWT, OAuth 2.0, API keys, sessions
4. api-authorization - RBAC, ABAC, policy engines
5. api-rate-limiting - Token bucket, sliding window algorithms
6. api-versioning - API versioning, deprecation, compatibility
7. api-error-handling - RFC 7807, validation errors

LOAD:
Read ../skills/api/INDEX.md                  # Full details
Read ../skills/discover-api/SKILL.md         # Gateway overview
Read ../skills/api/rest-api-design.md        # Specific skill
```

**If ARGUMENT = search term:**

Search across:
- Gateway skill descriptions (discover-*/SKILL.md)
- Category INDEX.md files
- skills/README.md catalog
- Root-level skill filenames

Display matching gateway categories FIRST, then specific skills:
```
SEARCH: 'postgres'

GATEWAY:
→ discover-database
  Keywords: PostgreSQL, MongoDB, Redis, query optimization
  Read ../skills/discover-database/SKILL.md

SKILLS:
→ postgres-query-optimization.md
  Debug slow queries, EXPLAIN plans, index design
  Read ../skills/database/postgres-query-optimization.md

→ postgres-migrations.md
  Schema changes, zero-downtime deployments
  Read ../skills/database/postgres-migrations.md

→ postgres-schema-design.md
  Designing schemas, relationships, data types
  Read ../skills/database/postgres-schema-design.md

RELATED: discover-debugging, discover-database
```

**If ARGUMENT = "list":**

Show all 23 gateway categories:
```
ALL CATEGORIES (410+ skills)

BACKEND & DATA:
  discover-api (7)         - REST, GraphQL, auth, rate limiting
  discover-database (15)   - Postgres, MongoDB, Redis, caching, CDN
  discover-data (5)        - ETL, streaming, batch processing

FRONTEND & MOBILE:
  discover-frontend (13)   - React, Next.js, state management, TUI
  discover-mobile (4)      - iOS, Swift, SwiftUI, concurrency

INFRASTRUCTURE:
  discover-infra (30)      - AWS, GCP, Docker, Kubernetes, Terraform, Netlify
  discover-cicd (12)       - GitHub Actions, Make, CMake, Gradle, Maven
  discover-networking (20) - TCP, HTTP, gRPC, Nginx, Traefik, proxies
  discover-distributed (21)- Consensus, CRDTs, WebSocket, SSE, pub/sub

QUALITY & ENGINEERING:
  discover-testing (6)     - Unit, integration, e2e, TDD, coverage
  discover-debugging (22)  - GDB, LLDB, profiling, observability, tracing
  discover-engineering (14)- Code review, git, diagrams, documentation
  discover-security (6)    - AppSec, threat modeling, hardening
  discover-cryptography (7)- TLS, certificates, encryption

SPECIALIZED:
  discover-ml (32)         - Training, RAG, embeddings, Modal, evaluation
  discover-math (19)       - Linear algebra, topology, category theory
  discover-systems-theory (32) - eBPF, compilers, PLT, formal methods, Z3, Lean
  discover-wasm (4)        - WebAssembly fundamentals, Rust to WASM
  discover-research (8)    - Research methods, writing, quantitative

PRODUCT & WORKFLOW:
  discover-product (15)    - PRDs, roadmaps, GitHub workflows, Beads
  discover-zig (6)         - Zig language, comptime, allocators

AI & AGENTIC:
  discover-mcp (3)         - MCP servers, tool design, testing
  discover-agentic (3)     - Task decomposition, tool use, memory patterns

AGENT SKILLS (Root):
  elegant-design          - UI/UX design, accessibility, design systems
  anti-slop               - Detect/eliminate AI-generated patterns
  typed-holes-refactor    - Systematic TDD-based refactoring

META SKILLS (Root):
  skill-*.md              - Discovery and creation
  beads-*.md              - Workflow and task management
```

### 5. Output Requirements

**Format Guidelines:**
- Keep output concise and scannable
- Use `→` for list items
- Include clear, copy-paste commands
- Group related items logically
- Show only relevant categories/skills for the context

**Tone:**
- Direct and helpful
- Low noise, high signal
- Focus on what the user needs now
- Don't explain the system unless asked

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
├── discover-*/SKILL.md    (23 gateway skills)
└── {category}/INDEX.md    (Category indexes)

Is your repository in a different location?
```

**If no matches for search:**
```
No skills found matching '$ARGUMENTS'

Try:
- Broader search term
- View all gateways: /skills list
- Browse full catalog: Read ../skills/README.md
- Check a category: /skills api
```

**If empty project directory:**
```
━━━ SKILLS DISCOVERY ━━━

No project files detected in current directory.

GENERAL-PURPOSE GATEWAYS:
→ discover-product - Product management, collaboration, documentation
  Load: Read ../skills/discover-product/SKILL.md

ROOT-LEVEL SKILLS:
→ beads-workflow.md - Multi-session task management
→ skill-creation.md - Creating new atomic skills
→ skill-repo-discovery.md - Discover skills for repositories

[View all: /skills list]
[Browse catalog: Read ../skills/README.md]
```

## Remember

- Read skills/README.md to get accurate information (NOT _INDEX.md - that's archived)
- Recommend gateway skills first, then specific skills
- Match skills to project context when possible
- Keep output concise and actionable
- Never modify the skills library
- Provide clear, copy-paste commands
- The catalog has: 410+ skills, 40 gateways, 33 categories
