# Claude Code Development Reference

A comprehensive skills library and development guidelines for working with Claude Code across 132 atomic, composable skills spanning 27 technology domains.

## Overview

This repository serves as a complete reference for software development best practices, workflows, and atomic skills. Each skill is focused (~310 lines average), tested in production, and designed to compose with others for complex workflows.

**Use this when:**
- Starting a new project and need architecture patterns
- Working with unfamiliar technologies or frameworks
- Need production-ready workflows and best practices
- Building complex multi-technology systems
- Onboarding to a new codebase

## What's Covered

### Languages & Frameworks (31 skills)
**Backend/Systems:**
- **Python**: Modern development with `uv` package manager
- **Zig**: Systems programming with comptime, allocators, C interop
- **Rust**: Ownership patterns, async/tokio, error handling
- **Go**: Clean architecture, error handling, TUI development with Bubble Tea

**Frontend:**
- **TypeScript**: Strict mode, Next.js 14+ App Router, React patterns
- **React**: Component patterns, state management, data fetching, forms
- **Next.js**: App Router, SEO optimization, performance

**Mobile:**
- **Swift/SwiftUI**: iOS native (iOS 17+), Swift concurrency, SwiftData
- **React Native**: Cross-platform mobile development

### Cloud & Infrastructure (30 skills)
**Serverless & Edge:**
- **Modal.com**: GPU workloads (L40S/H100), serverless functions, web endpoints
- **Cloudflare Workers**: Edge computing, KV storage, Durable Objects
- **Vercel**: Serverless functions, edge runtime, automatic deployments
- **AWS Lambda**: Serverless architecture, IAM patterns
- **Heroku/Netlify**: Platform deployment, add-ons, optimization

**Infrastructure as Code:**
- **Terraform**: Resource patterns, state management
- **Kubernetes**: Pod design, services, deployments
- **Docker**: Multi-stage builds, security, optimization

**CI/CD & Observability:**
- **GitHub Actions**: Workflows, matrix builds, caching, security
- **Structured Logging**: JSON logging, correlation IDs
- **Metrics & Tracing**: Prometheus, OpenTelemetry, distributed tracing
- **Alerting**: Alert design, on-call patterns, runbooks

### Data & Databases (21 skills)
**Relational:**
- **Postgres**: Query optimization, migrations, schema design, EXPLAIN plans
- **Database Patterns**: Connection pooling, ORMs, transaction management

**NoSQL & Caching:**
- **MongoDB**: Document design, embedding vs referencing
- **Redis**: Data structures, caching, sessions, rate limiting

**Modern Data Stack:**
- **Redpanda/Kafka**: Streaming architecture, event-driven patterns, rpk CLI
- **Apache Iceberg**: Table format, time travel, schema evolution, ACID
- **DuckDB**: In-process analytics, direct file querying, OLAP queries

**Data Engineering:**
- **ETL Patterns**: Extract, transform, load workflows
- **Stream Processing**: Real-time data pipelines
- **Batch Processing**: Scheduled data jobs, orchestration

### API Design & Testing (13 skills)
**API Patterns:**
- REST API design, versioning, pagination
- GraphQL schema design, resolvers, federation
- Authentication/authorization (JWT, OAuth, RBAC)
- Rate limiting, error handling, API versioning

**Testing:**
- Unit testing patterns, TDD workflows
- Integration testing, e2e testing
- Performance testing, load testing
- Test coverage strategies

### Specialized Domains (37 skills)

**Machine Learning:**
- **LLM Fine-tuning**: Unsloth, HuggingFace AutoTrain, LoRA/PEFT, dataset prep
- **Diffusion Models**: Stable Diffusion deployment, fine-tuning basics

**Formal Methods:**
- **SAT/SMT Solvers**: Z3 basics, SAT solving strategies, SMT theory
- **Lean 4**: Proof basics, tactics, mathlib4, theorem proving
- **Constraint Satisfaction**: CSP modeling, propagation, backtracking

**Mathematics:**
- Linear algebra computation
- Optimization algorithms
- Numerical methods
- Probability & statistics

**Real-time & Networking:**
- WebSocket implementation, Server-Sent Events
- Pub/sub patterns, real-time sync
- Tailscale VPN, mTLS, NAT traversal
- Network resilience patterns, Mosh

**Workflow & Productivity:**
- **Beads**: Task management, context strategies, multi-session workflows
- **TUI Development**: Bubble Tea (Go), Ratatui (Rust)
- **Meta Skills**: Intelligent skill discovery for repos and prompts

## Quick Start

### 1. New Project Setup
```bash
# Read CLAUDE.md for project initiation protocol
# Covers: Requirements clarification, tech stack decisions, project structure

# Use meta skills for intelligent discovery
cat skills/skill-repo-discovery.md   # Analyze existing codebases
cat skills/skill-prompt-discovery.md # Extract tech signals from requirements
```

### 2. Find Relevant Skills
```bash
# By technology
ls skills/zig-*.md           # Zig: 6 skills
ls skills/swiftui-*.md       # SwiftUI: 4 skills
ls skills/modal-*.md         # Modal.com: 6 base + 2 troubleshooting
ls skills/api/*.md           # API design: 7 skills
ls skills/formal/*.md        # Formal methods: 10 skills
ls skills/ml/*.md            # Machine learning: 7 skills

# By category directory
ls skills/cicd/*.md          # CI/CD: 5 skills
ls skills/infrastructure/*.md # Infrastructure: 6 skills
ls skills/observability/*.md  # Observability: 5 skills
ls skills/deployment/*.md     # Deployment: 6 skills
ls skills/math/*.md          # Mathematics: 4 skills
ls skills/mobile/*.md        # Mobile: 4 skills

# By task
grep -l "GraphQL" skills/**/*.md
grep -l "streaming" skills/**/*.md
```

### 3. Compose Workflows
```bash
# Full-stack web app
skills/api/rest-api-design.md
+ skills/frontend/nextjs-app-router.md
+ skills/database/postgres-schema-design.md
+ skills/cicd/github-actions-workflows.md

# ML/AI deployment
skills/ml/unsloth-finetuning.md
+ skills/modal-gpu-workloads.md
+ skills/modal-web-endpoints.md

# Data pipeline
skills/redpanda-streaming.md
+ skills/data/stream-processing.md
+ skills/apache-iceberg.md
+ skills/observability/structured-logging.md

# iOS app
skills/swiftui-architecture.md
+ skills/swift-concurrency.md
+ skills/swiftdata-persistence.md
+ skills/ios-networking.md
```

## Repository Structure

```
.
├── CLAUDE.md              # Comprehensive development guidelines
│                          # - Beads task management workflow
│                          # - Language stack standards (uv, cargo, zig, etc.)
│                          # - Testing protocols (commit before testing!)
│                          # - Cloud deployment patterns
│                          # - Anti-patterns & violations
│
├── README.md              # This file
│
└── skills/                # 132 atomic skills across 27 categories
    │
    ├── _INDEX.md          # Full catalog with use cases and workflows
    │
    ├── Core Foundation (74 skills)
    │   ├── api/           # REST, GraphQL, auth, rate limiting (7)
    │   ├── testing/       # Unit, integration, e2e, TDD (6)
    │   ├── containers/    # Docker, Compose, security (5)
    │   ├── frontend/      # React, Next.js, performance, a11y (8)
    │   ├── database/      # Postgres, MongoDB, Redis, Redpanda, Iceberg, DuckDB (8)
    │   ├── beads-*.md     # Workflow & task management (5)
    │   ├── skill-*.md     # Meta skills: discovery & planning (4)
    │   ├── swiftui-*.md   # iOS/Swift native development (6)
    │   ├── modal-*.md     # Modal.com serverless + GPU (6)
    │   ├── modal/         # Modal troubleshooting (2)
    │   ├── network-*.md   # Tailscale, mTLS, Mosh, NAT (5)
    │   ├── bubbletea-*.md # TUI development Go/Rust (5)
    │   └── zig-*.md       # Zig systems programming (6)
    │
    ├── Advanced Infrastructure (25 skills)
    │   ├── cicd/          # GitHub Actions, testing, deployment (5)
    │   ├── infrastructure/# Terraform, K8s, AWS, Cloudflare (6)
    │   ├── observability/ # Logging, metrics, tracing, alerting (5)
    │   ├── realtime/      # WebSocket, SSE, pub/sub (4)
    │   └── data/          # ETL, streaming, batch processing (5)
    │
    └── Specialized Domains (33 skills)
        ├── formal/        # SAT/SMT solvers, Lean 4, CSP (10)
        ├── ml/            # LLM fine-tuning, diffusion models (7)
        ├── deployment/    # Heroku, Netlify platforms (6)
        ├── math/          # Linear algebra, optimization, stats (4)
        └── mobile/        # React Native development (4)
```

## Development Philosophy

### Atomic Skills
- **Focused**: Each skill covers one clear topic (~310 lines average)
- **Composable**: Skills combine for complex workflows
- **Production-tested**: All patterns used in real projects
- **Cross-referenced**: Related skills linked for discovery

### Quality Gates
1. **Critical Thinking**: Push back on vague requirements
2. **Standards Enforcement**: Correct package managers (uv not pip, etc.)
3. **Testing Protocol**: Always commit before testing
4. **Error Handling**: No TODOs/mocks - implement or file issue

### Discovery-Driven
```bash
# For new repositories
skills/skill-repo-discovery.md    # Analyze codebase → identify skills

# For user requests
skills/skill-prompt-discovery.md  # Extract tech signals → activate skills

# For planning
skills/skill-repo-planning.md     # Plan missing skills for repos
skills/skill-prompt-planning.md   # Plan missing skills for prompts

# For creating new skills
skills/skill-creation.md           # Template and guidelines
```

## Example Use Cases

### Scenario: Build ML-powered API
1. Read `skill-prompt-discovery.md` → identifies: Modal, FastAPI, LLM skills
2. Compose workflow:
   - `ml/unsloth-finetuning.md` → Fine-tune model
   - `modal-gpu-workloads.md` → Deploy on L40S GPU
   - `modal-web-endpoints.md` → Expose FastAPI endpoint
   - `api/rest-api-design.md` → Design API contract
   - `api/api-rate-limiting.md` → Protect endpoint
   - `observability/structured-logging.md` → Add logging
   - `cicd/github-actions-workflows.md` → Automate deployment

### Scenario: Optimize Slow Database
1. Start with `database/postgres-query-optimization.md`
2. Follow to `database/postgres-schema-design.md` for structural issues
3. Add `database/database-connection-pooling.md` if pool exhaustion
4. Implement `observability/metrics-instrumentation.md` for monitoring
5. Use `database/orm-patterns.md` to fix N+1 queries

### Scenario: Build iOS App with Streaming
1. Read `swiftui-architecture.md` → MVVM setup
2. Add `swift-concurrency.md` → async/await patterns
3. Implement `swiftdata-persistence.md` → local storage
4. Use `ios-networking.md` → API integration
5. Deploy backend with `redpanda-streaming.md` + `modal-web-endpoints.md`

## Technology Coverage Matrix

| Domain | Technologies | Skills | Key Capabilities |
|--------|-------------|--------|------------------|
| **Backend** | Python, Zig, Rust, Go | 18 | Systems programming, async, memory safety |
| **Frontend** | React, Next.js, TypeScript | 8 | SSR, performance, a11y, SEO |
| **Mobile** | SwiftUI, React Native | 10 | iOS native, cross-platform |
| **Cloud** | Modal, AWS, Vercel, Cloudflare | 14 | Serverless, GPU, edge computing |
| **Database** | Postgres, Mongo, Redis, Redpanda, Iceberg, DuckDB | 11 | OLTP, NoSQL, streaming, analytics |
| **ML/AI** | Unsloth, HuggingFace, Diffusion | 7 | LLM fine-tuning, image generation |
| **Formal** | Z3, Lean 4, CSP | 10 | Proof systems, constraint solving |
| **DevOps** | GitHub Actions, Terraform, K8s, Docker | 16 | CI/CD, IaC, containers |
| **Data** | ETL, Streaming, Batch | 10 | Pipelines, real-time, analytics |

## Contributing

This is a personal reference repository maintained through practical development experience. Skills are:
- Added when new technologies are mastered
- Updated when better patterns emerge
- Refined based on production use
- Kept atomic and focused

**Not accepting external contributions**, but feel free to fork and adapt for your own use.

---

**Total: 132 atomic skills** | **Average: 310 lines/skill** | **27 categories** | **100% production-tested**
