# Skills Catalog

**Total Skills**: 284 across 30 categories
**Gateway Skills**: 27 (auto-discovered by Claude Code)
**Agent Skills**: 3 (elegant-design, anti-slop, typed-holes-refactor)

## Overview

This skills library uses a **progressive discovery architecture** optimized for context efficiency:

1. **Gateway Skills** (`discover-{category}/SKILL.md`) - Auto-discovered by Claude Code based on keywords
2. **Category Indexes** (`{category}/INDEX.md`) - Detailed category overviews loaded on-demand
3. **Individual Skills** (`{category}/{skill}.md`) - Specific skill content loaded as needed

**Context Savings**: 60-84% reduction vs monolithic index (5-10K tokens vs 25K+)

## How It Works

### Automatic Discovery
When you work on a task, Claude Code automatically activates relevant gateway skills based on keywords in your request.

**Example**: "Design a REST API with Postgres"
- → `discover-api` gateway activates (keywords: API, REST)
- → `discover-database` gateway activates (keywords: Postgres, database)
- → Both gateways load (~4K tokens total)
- → You can then load specific skills as needed

### Manual Discovery
Browse categories and load skills explicitly:

```bash
# List all gateway skills
ls -d skills/discover-*

# Load a category overview
cat skills/api/INDEX.md

# Load a specific skill
cat skills/api/rest-api-design.md
```

## Gateway Skills by Category

### Backend & APIs (7 skills)
**Gateway**: `discover-api`
**Keywords**: API, REST, GraphQL, authentication, authorization, rate limiting
**Skills**: REST API design, GraphQL schemas, authentication (JWT/OAuth), authorization (RBAC/ABAC), rate limiting, versioning, error handling

```bash
cat skills/api/INDEX.md
```

---

### Databases (8 skills)
**Gateway**: `discover-database`
**Keywords**: database, SQL, PostgreSQL, MongoDB, Redis, query optimization
**Skills**: PostgreSQL (schema, queries, migrations), MongoDB documents, Redis structures, connection pooling, ORMs, database selection

```bash
cat skills/database/INDEX.md
```

---

### Frontend (8 skills + elegant-design Agent Skill)
**Gateway**: `discover-frontend`
**Keywords**: React, Next.js, UI, components, state management, forms
**Skills**: React patterns, Next.js App Router, state management, data fetching, forms, accessibility, performance, SEO
**Note**: `elegant-design` is a separate Agent Skill for UI design work

```bash
cat skills/frontend/INDEX.md
```

---

### Testing (6 skills)
**Gateway**: `discover-testing`
**Keywords**: testing, tests, unit, integration, e2e, TDD, coverage
**Skills**: Unit testing, integration testing, e2e testing, TDD, test coverage, performance testing

```bash
cat skills/testing/INDEX.md
```

---

### Machine Learning (30 skills)
**Gateway**: `discover-ml`
**Keywords**: machine learning, ML, AI, models, training, embeddings, transformers
**Skills**: Model training, inference, embeddings, RAG, evaluation, routing, fine-tuning, PyTorch, TensorFlow, Hugging Face

```bash
cat skills/ml/INDEX.md
```

---

### Mathematics (19 skills)
**Gateway**: `discover-math`
**Keywords**: mathematics, algorithms, linear algebra, calculus, topology, category theory
**Skills**: Linear algebra, calculus, topology, category theory, set theory, number theory, abstract algebra, graph theory, optimization

```bash
cat skills/math/INDEX.md
```

---

### Elegant Design (Agent Skill)
**Gateway**: Auto-discovered separately
**Keywords**: design, UI, UX, accessibility, chat, terminal, code display, streaming
**Skills**: World-class accessible interfaces, shadcn/ui, interactive components, design systems

```bash
# This is an Agent Skill - loads automatically when doing UI design work
cat skills/elegant-design/SKILL.md
```

---

### Debugging (14 skills)
**Gateway**: `discover-debugging`
**Keywords**: debugging, GDB, LLDB, profiling, memory leaks, performance
**Skills**: GDB/LLDB, Python debugging, browser DevTools, remote debugging, memory profiling, concurrency debugging

```bash
cat skills/debugging/INDEX.md
```

---

### Programming Language Theory (13 skills)
**Gateway**: `discover-plt`
**Keywords**: compilers, parsers, type systems, interpreters, LLVM
**Skills**: Parsing, type systems, code generation, compiler optimizations, LLVM, bytecode, interpreters

```bash
cat skills/plt/INDEX.md
```

---

### Cloud & Serverless (13 skills)
**Gateway**: `discover-cloud`
**Keywords**: cloud, serverless, Modal, AWS, GCP, functions, deployment
**Skills**: Modal platform, serverless patterns, cloud deployment, scaling, GPU workloads

```bash
cat skills/cloud/INDEX.md
```

---

### Formal Methods (10 skills)
**Gateway**: `discover-formal`
**Keywords**: formal methods, SAT, SMT, Z3, Lean, theorem proving, verification
**Skills**: SAT solving, SMT theory, Z3 solver, Lean theorem proving, constraint solving, formal verification

```bash
cat skills/formal/INDEX.md
```

---

### Observability (8 skills)
**Gateway**: `discover-observability`
**Keywords**: monitoring, logging, tracing, metrics, distributed tracing, alerts
**Skills**: Structured logging, metrics instrumentation, distributed tracing, alerting, dashboard design

```bash
cat skills/observability/INDEX.md
```

---

### Build Systems (8 skills)
**Gateway**: `discover-build`
**Keywords**: build systems, Make, CMake, Gradle, Maven, Bazel, compilation
**Skills**: Make, CMake, Gradle, Maven, Bazel, cross-platform builds, build optimization

```bash
cat skills/build-systems/INDEX.md
```

---

### Caching (7 skills)
**Gateway**: `discover-caching`
**Keywords**: caching, cache, Redis, CDN, HTTP caching, performance
**Skills**: Caching fundamentals, HTTP caching, CDN edge caching, Redis patterns, cache invalidation, Service Workers, monitoring

```bash
cat skills/caching/INDEX.md
```

---

### Deployment (6 skills)
**Gateway**: `discover-deployment`
**Keywords**: deployment, Netlify, Heroku, CI/CD, production, releases
**Skills**: Netlify deployment/functions/optimization, Heroku deployment/addons/troubleshooting

```bash
cat skills/deployment/INDEX.md
```

---

### Infrastructure (6 skills)
**Gateway**: `discover-infra`
**Keywords**: infrastructure, Terraform, IaC, Cloudflare Workers, security, DevOps
**Skills**: Cloudflare Workers, infrastructure security, cost optimization, IaC patterns

```bash
cat skills/infrastructure/INDEX.md
```

---

### Anti-Slop (Agent Skill)
**Gateway**: Auto-discovered separately
**Keywords**: slop, AI patterns, code quality, content quality
**Skills**: Detect and eliminate generic AI patterns in text, code, and design

```bash
# This is an Agent Skill - loads automatically for quality review
cat skills/anti-slop/SKILL.md
```

---

### Typed Holes Refactor (Agent Skill)
**Gateway**: Auto-discovered separately
**Keywords**: refactoring, typed holes, incremental refactoring, test-driven
**Skills**: Systematic refactoring using typed holes methodology

```bash
# This is an Agent Skill - loads automatically for refactoring work
cat skills/typed-holes-refactor/SKILL.md
```

---

### Containers (5 skills)
**Gateway**: `discover-containers`
**Keywords**: Docker, containers, Kubernetes, container security, docker-compose
**Skills**: Dockerfile optimization, docker-compose, container security, networking, registry management

```bash
cat skills/containers/INDEX.md
```

---

### Data Pipelines (5 skills)
**Gateway**: `discover-data`
**Keywords**: ETL, data pipelines, batch processing, stream processing, orchestration
**Skills**: ETL patterns, batch processing, stream processing, pipeline orchestration, data validation

```bash
cat skills/data/INDEX.md
```

---

### Mobile (4 skills)
**Gateway**: `discover-mobile`
**Keywords**: iOS, Swift, SwiftUI, mobile, SwiftData, concurrency
**Skills**: SwiftUI architecture, Swift concurrency, iOS networking, iOS testing

```bash
cat skills/mobile/INDEX.md
```

---

### CI/CD (4 skills)
**Gateway**: `discover-cicd`
**Keywords**: CI/CD, GitHub Actions, automation, pipelines
**Skills**: GitHub Actions, GitLab CI, pipeline patterns, deployment automation

```bash
cat skills/cicd/INDEX.md
```

---

### Realtime (4 skills)
**Gateway**: `discover-realtime`
**Keywords**: realtime, WebSockets, Server-Sent Events, streaming, pub/sub
**Skills**: WebSocket patterns, SSE, real-time protocols, state synchronization

```bash
cat skills/realtime/INDEX.md
```

---

### WebAssembly (4 skills)
**Gateway**: `discover-wasm`
**Keywords**: WebAssembly, WASM, wasm-pack, Rust to WASM
**Skills**: WASM fundamentals, Rust to WASM, WASM in browsers, WASI

```bash
cat skills/wasm/INDEX.md
```

---

### eBPF (4 skills)
**Gateway**: `discover-ebpf`
**Keywords**: eBPF, kernel, tracing, networking, BPF
**Skills**: eBPF fundamentals, tracing, networking, security monitoring

```bash
cat skills/ebpf/INDEX.md
```

---

### Engineering Practices (4 skills)
**Gateway**: `discover-engineering`
**Keywords**: engineering practices, code review, technical leadership
**Skills**: Code review, documentation, technical leadership, team practices

```bash
cat skills/engineering/INDEX.md
```

---

### Product (4 skills)
**Gateway**: `discover-product`
**Keywords**: product management, roadmap, strategy, prioritization
**Skills**: Product strategy, roadmap planning, user research, prioritization

```bash
cat skills/product/INDEX.md
```

---

### Collaboration (5 skills)
**Gateway**: `discover-collab`
**Keywords**: collaboration, code review, documentation, pair programming
**Skills**: Code review, documentation, pair programming, team workflows

```bash
cat skills/collaboration/INDEX.md
```

---

### Intermediate Representation (5 skills)
**Gateway**: `discover-ir`
**Keywords**: IR, LLVM IR, intermediate representation, compiler optimizations
**Skills**: LLVM IR, SSA form, code generation, IR optimizations

```bash
cat skills/ir/INDEX.md
```

---

### Modal (2 skills)
**Gateway**: `discover-modal`
**Keywords**: Modal, serverless functions, cloud deployment
**Skills**: Modal functions basics, Modal scheduling

```bash
cat skills/modal/INDEX.md
```

---

## Quick Reference

### Find Skills by Technology

**Python**: discover-backend, discover-ml, discover-data, discover-testing
**TypeScript/React**: discover-frontend, discover-testing
**Zig**: discover-backend, discover-build
**Go**: discover-backend, discover-cloud
**Rust**: discover-backend, discover-wasm

### Find Skills by Task

**Build API**: discover-api, discover-database, discover-testing
**Build Frontend**: discover-frontend, elegant-design, discover-api, discover-testing
**Optimize Performance**: discover-caching, discover-database, discover-observability
**Debug Issues**: discover-debugging, discover-observability
**Deploy Application**: discover-deployment, discover-cloud, discover-infra, discover-cicd
**Data Engineering**: discover-data, discover-database, discover-observability

### Root-Level Skills

45 skills at root level (not yet categorized):
- Beads workflow skills (beads-*.md)
- Zig skills (zig-*.md)
- TUI skills (bubbletea-*.md, ratatui-*.md)
- iOS skills (swift*.md, ios-*.md, swiftui-*.md)
- Modal skills (modal-*.md)
- Networking skills (mosh-*.md, mtls-*.md, nat-traversal.md, network-resilience-patterns.md, tailscale-vpn.md)
- Discovery/Meta skills (skill-*.md)
- Misc (apache-iceberg.md, duckdb-analytics.md, redpanda-streaming.md)

These will be integrated into appropriate categories in a future update.

---

## Usage Patterns

### Automatic (Recommended)
Just start working. Claude Code will auto-activate relevant gateway skills.

### Browse Then Load
1. Review this README for category overview
2. Load category index: `cat skills/{category}/INDEX.md`
3. Load specific skill: `cat skills/{category}/{skill}.md`

### Search by Keyword
```bash
# Find skills matching a keyword
grep -r "keyword" skills/*/INDEX.md

# Find gateway skills by description
grep "description:" skills/discover-*/SKILL.md
```

---

## Architecture Benefits

✅ **Context Efficient**: 60-84% reduction in tokens loaded
✅ **Auto-Discovery**: Keywords trigger relevant gateway skills
✅ **Progressive Loading**: Load only what you need, when you need it
✅ **Scalable**: Can grow to 1000+ skills with same footprint
✅ **Maintainable**: Small, focused files instead of monolithic index
✅ **Flexible**: Works for automatic AND manual discovery

---

**See also**:
- `skill-repo-discovery.md` - Discover skills for a new repository
- `skill-prompt-discovery.md` - Discover skills from user prompts
- `CLAUDE.md` - Complete development guidelines with Work Plan Protocol
