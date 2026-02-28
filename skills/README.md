# Skills Catalog

**Total Skills**: 410+ across 33+ categories
**Gateway Skills**: 40 (auto-discovered by Claude Code)
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
Read api/INDEX.md

# Load a specific skill
Read api/rest-api-design.md
```

## Gateway Skills by Category

### Backend & APIs (7 skills)
**Gateway**: `discover-api`
**Keywords**: API, REST, GraphQL, authentication, authorization, rate limiting
**Skills**: REST API design, GraphQL schemas, authentication (JWT/OAuth), authorization (RBAC/ABAC), rate limiting, versioning, error handling

Read api/INDEX.md


---

### Databases (8 skills)
**Gateway**: `discover-database`
**Keywords**: database, SQL, PostgreSQL, MongoDB, Redis, query optimization
**Skills**: PostgreSQL (schema, queries, migrations), MongoDB documents, Redis structures, connection pooling, ORMs, database selection

Read database/INDEX.md


---

### Frontend (8 skills + elegant-design Agent Skill)
**Gateway**: `discover-frontend`
**Keywords**: React, Next.js, UI, components, state management, forms
**Skills**: React patterns, Next.js App Router, state management, data fetching, forms, accessibility, performance, SEO
**Note**: `elegant-design` is a separate Agent Skill for UI design work

Read frontend/INDEX.md


---

### Testing (6 skills)
**Gateway**: `discover-testing`
**Keywords**: testing, tests, unit, integration, e2e, TDD, coverage
**Skills**: Unit testing, integration testing, e2e testing, TDD, test coverage, performance testing

Read testing/INDEX.md


---

### Diagrams & Visualization (8 skills)
**Gateway**: `discover-engineering`
**Keywords**: diagram, flowchart, sequence, architecture, ER, UML, Mermaid, visualization
**Skills**: Flowcharts, sequence diagrams, class/state diagrams, ER diagrams, architecture (C4/block), charts (pie/XY/quadrant/radar), project diagrams (Gantt/timeline), specialized (Git/Sankey/mindmaps)

Read diagrams/INDEX.md


---

### Machine Learning (30 skills)
**Gateway**: `discover-ml`
**Keywords**: machine learning, ML, AI, models, training, embeddings, transformers
**Skills**: Model training, inference, embeddings, RAG, evaluation, routing, fine-tuning, PyTorch, TensorFlow, Hugging Face

Read ml/INDEX.md


---

### Mathematics (19 skills)
**Gateway**: `discover-math`
**Keywords**: mathematics, algorithms, linear algebra, calculus, topology, category theory
**Skills**: Linear algebra, calculus, topology, category theory, set theory, number theory, abstract algebra, graph theory, optimization

Read math/INDEX.md


---

### Elegant Design (Agent Skill)
**Gateway**: Auto-discovered separately
**Keywords**: design, UI, UX, accessibility, chat, terminal, code display, streaming
**Skills**: World-class accessible interfaces, shadcn/ui, interactive components, design systems

# This is an Agent Skill - loads automatically when doing UI design work
Read elegant-design/SKILL.md


---

### Debugging (14 skills)
**Gateway**: `discover-debugging`
**Keywords**: debugging, GDB, LLDB, profiling, memory leaks, performance
**Skills**: GDB/LLDB, Python debugging, browser DevTools, remote debugging, memory profiling, concurrency debugging

Read debugging/INDEX.md


---

### Programming Language Theory (13 skills)
**Gateway**: `discover-systems-theory`
**Keywords**: compilers, parsers, type systems, interpreters, LLVM
**Skills**: Parsing, type systems, code generation, compiler optimizations, LLVM, bytecode, interpreters

Read plt/INDEX.md


---

### Cloud & Serverless (13 skills)
**Gateway**: `discover-infra`
**Keywords**: cloud, serverless, Modal, AWS, GCP, functions, deployment
**Skills**: Modal platform, serverless patterns, cloud deployment, scaling, GPU workloads

Read cloud/INDEX.md


---

### Formal Methods (10 skills)
**Gateway**: `discover-systems-theory`
**Keywords**: formal methods, SAT, SMT, Z3, Lean, theorem proving, verification
**Skills**: SAT solving, SMT theory, Z3 solver, Lean theorem proving, constraint solving, formal verification

Read formal/INDEX.md


---

### Observability (8 skills)
**Gateway**: `discover-debugging`
**Keywords**: monitoring, logging, tracing, metrics, distributed tracing, alerts
**Skills**: Structured logging, metrics instrumentation, distributed tracing, alerting, dashboard design

Read observability/INDEX.md


---

### Build Systems (8 skills)
**Gateway**: `discover-cicd`
**Keywords**: build systems, Make, CMake, Gradle, Maven, Bazel, compilation
**Skills**: Make, CMake, Gradle, Maven, Bazel, cross-platform builds, build optimization

Read build-systems/INDEX.md


---

### Caching (7 skills)
**Gateway**: `discover-database`
**Keywords**: caching, cache, Redis, CDN, HTTP caching, performance
**Skills**: Caching fundamentals, HTTP caching, CDN edge caching, Redis patterns, cache invalidation, Service Workers, monitoring

Read caching/INDEX.md


---

### Deployment (6 skills)
**Gateway**: `discover-infra`
**Keywords**: deployment, Netlify, Heroku, CI/CD, production, releases
**Skills**: Netlify deployment/functions/optimization, Heroku deployment/addons/troubleshooting

Read deployment/INDEX.md


---

### Infrastructure (6 skills)
**Gateway**: `discover-infra`
**Keywords**: infrastructure, Terraform, IaC, Cloudflare Workers, security, DevOps
**Skills**: Cloudflare Workers, infrastructure security, cost optimization, IaC patterns

Read infrastructure/INDEX.md


---

### Anti-Slop (Agent Skill)
**Gateway**: Auto-discovered separately
**Keywords**: slop, AI patterns, code quality, content quality
**Skills**: Detect and eliminate generic AI patterns in text, code, and design

# This is an Agent Skill - loads automatically for quality review
Read anti-slop/SKILL.md


---

### Typed Holes Refactor (Agent Skill)
**Gateway**: Auto-discovered separately
**Keywords**: refactoring, typed holes, incremental refactoring, test-driven
**Skills**: Systematic refactoring using typed holes methodology

# This is an Agent Skill - loads automatically for refactoring work
Read typed-holes-refactor/SKILL.md


---

### Containers (5 skills)
**Gateway**: `discover-infra`
**Keywords**: Docker, containers, Kubernetes, container security, docker-compose
**Skills**: Dockerfile optimization, docker-compose, container security, networking, registry management

Read containers/INDEX.md


---

### Data Pipelines (9 skills)
**Gateway**: `discover-data`
**Keywords**: ETL, data pipelines, batch processing, stream processing, orchestration
**Skills**: ETL patterns, batch processing, stream processing, pipeline orchestration, data validation

Read data/INDEX.md


---

### Mobile (4 skills)
**Gateway**: `discover-mobile`
**Keywords**: iOS, Swift, SwiftUI, mobile, SwiftData, concurrency
**Skills**: SwiftUI architecture, Swift concurrency, iOS networking, iOS testing

Read mobile/INDEX.md


---

### CI/CD (4 skills)
**Gateway**: `discover-cicd`
**Keywords**: CI/CD, GitHub Actions, automation, pipelines
**Skills**: GitHub Actions, GitLab CI, pipeline patterns, deployment automation

Read cicd/INDEX.md


---

### Realtime (4 skills)
**Gateway**: `discover-distributed`
**Keywords**: realtime, WebSockets, Server-Sent Events, streaming, pub/sub
**Skills**: WebSocket patterns, SSE, real-time protocols, state synchronization

Read realtime/INDEX.md


---

### WebAssembly (4 skills)
**Gateway**: `discover-wasm`
**Keywords**: WebAssembly, WASM, wasm-pack, Rust to WASM
**Skills**: WASM fundamentals, Rust to WASM, WASM in browsers, WASI

Read wasm/INDEX.md


---

### eBPF (4 skills)
**Gateway**: `discover-systems-theory`
**Keywords**: eBPF, kernel, tracing, networking, BPF
**Skills**: eBPF fundamentals, tracing, networking, security monitoring

Read ebpf/INDEX.md


---

### Engineering Practices (6+ skills)
**Gateway**: `discover-engineering`
**Keywords**: engineering practices, code review, technical leadership
**Skills**: Code review, code review rules, git workflows, documentation, technical leadership, team practices

Read engineering/INDEX.md


---

### Product (4 skills)
**Gateway**: `discover-product`
**Keywords**: product management, roadmap, strategy, prioritization
**Skills**: Product strategy, roadmap planning, user research, prioritization

Read product/INDEX.md


---

### Collaboration (6 skills)
**Gateway**: `discover-product`
**Keywords**: collaboration, code review, documentation, pair programming
**Skills**: Code review, documentation, pair programming, team workflows

Read collaboration/INDEX.md


---

### Intermediate Representation (5 skills)
**Gateway**: `discover-systems-theory`
**Keywords**: IR, LLVM IR, intermediate representation, compiler optimizations
**Skills**: LLVM IR, SSA form, code generation, IR optimizations

Read ir/INDEX.md


---

### Modal (2 skills)
**Gateway**: `discover-ml`
**Keywords**: Modal, serverless functions, cloud deployment
**Skills**: Modal functions basics, Modal scheduling

Read modal/INDEX.md


---

### Workflow (5 skills)
**Gateway**: `discover-product`
**Keywords**: Beads, workflow, task management, synthesis, cleanup, consolidation, roadmap
**Skills**: Beads workflow, dependency management, multi-session patterns, context strategies, project synthesis

Read workflow/INDEX.md


---

### Cryptography (15 skills)
**Gateway**: `discover-cryptography`
**Keywords**: TLS, certificates, encryption, PKI, key management, secrets
**Skills**: TLS configuration, certificate management, PKI, key management, encryption at rest, secrets rotation, signing

Read cryptography/INDEX.md


---

### Distributed Systems (19 skills)
**Gateway**: `discover-distributed`
**Keywords**: distributed systems, consensus, CRDT, event sourcing, CAP theorem
**Skills**: Raft consensus, CRDTs, event sourcing, partitioning, replication, distributed locks

Read distributed-systems/INDEX.md


---

### Protocols (12 skills)
**Gateway**: `discover-networking`
**Keywords**: gRPC, Kafka, MQTT, AMQP, protobuf, HTTP/2, HTTP/3
**Skills**: gRPC, Kafka streams, MQTT, AMQP/RabbitMQ, protobuf, HTTP/2, HTTP/3, TCP optimization

Read protocols/INDEX.md


---

### Proxies (8 skills)
**Gateway**: `discover-networking`
**Keywords**: Nginx, Envoy, Traefik, reverse proxy, load balancing
**Skills**: Nginx, Envoy, Traefik, reverse proxy, forward proxy, NATS messaging

Read proxies/INDEX.md


---

### Networking (5 skills)
**Gateway**: `discover-networking`
**Keywords**: Tailscale, mTLS, NAT traversal, SSH, VPN
**Skills**: Tailscale VPN, mTLS, NAT traversal, Mosh, network resilience

Read networking/INDEX.md


---

### Security (9 skills)
**Gateway**: `discover-security`
**Keywords**: authentication, authorization, OAuth, secrets, security headers, vulnerabilities
**Skills**: Authentication, authorization, OAuth 2.0, secrets management, security headers, input validation, security rules

Read security/INDEX.md


---

### Zig (6 skills)
**Gateway**: `discover-zig`
**Keywords**: Zig, systems programming, memory management, build system
**Skills**: Project setup, memory management, build system, C interop, testing, package management

Read zig/INDEX.md


---

### Terminal UI (6 skills)
**Gateway**: `discover-frontend`
**Keywords**: terminal UI, TUI, Bubble Tea, Ratatui, CLI
**Skills**: Bubble Tea architecture/components, Ratatui architecture/widgets, TUI best practices

Read tui/INDEX.md


---

### Rust / PyO3 (19 skills)
**Gateway**: Auto-discovered via discover-backend keywords
**Keywords**: Rust, PyO3, Python extensions, FFI
**Skills**: PyO3 fundamentals, classes, async, packaging, testing, data science, DSPy integration

Read rust/INDEX.md


---

### Research (8 skills)
**Gateway**: `discover-research`
**Keywords**: research methods, data collection, analysis, synthesis
**Skills**: Research design, data collection, analysis, qualitative/quantitative methods, synthesis, writing

Read research/INDEX.md


---

### MCP (3 skills)
**Gateway**: `discover-mcp`
**Keywords**: MCP, Model Context Protocol, tool design, MCP server
**Skills**: MCP server fundamentals, tool design, testing

Read mcp/INDEX.md


---

### Agentic (3 skills)
**Gateway**: `discover-agentic`
**Keywords**: agentic, task decomposition, tool use, memory patterns
**Skills**: Task decomposition, tool use patterns, memory management

Read agentic/INDEX.md


---

## Quick Reference

### Find Skills by Technology

**Python**: discover-ml, discover-data, discover-testing
**TypeScript/React**: discover-frontend, discover-testing
**Zig**: discover-zig, discover-cicd
**Go**: discover-infra, discover-api
**Rust**: discover-wasm

### Find Skills by Task

**Build API**: discover-api, discover-database, discover-testing
**Build Frontend**: discover-frontend, elegant-design, discover-api, discover-testing
**Optimize Performance**: discover-database, discover-database, discover-debugging
**Debug Issues**: discover-debugging, discover-debugging
**Deploy Application**: discover-infra, discover-infra, discover-infra, discover-cicd
**Data Engineering**: discover-data, discover-database, discover-debugging

---

## Usage Patterns

### Automatic (Recommended)
Just start working. Claude Code will auto-activate relevant gateway skills.

### Browse Then Load
1. Review this README for category overview
2. Load category index: `Read {category}/INDEX.md`
3. Load specific skill: `Read {category}/{skill}.md`

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
