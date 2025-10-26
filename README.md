# Claude Code Development Reference

A comprehensive skills library and development guidelines for working with Claude Code across 284 atomic, composable skills spanning 30 technology domains.

## Overview

This repository serves as a complete reference for software development best practices, workflows, and atomic skills. Each skill is focused (~320 lines average), tested in production, and designed to compose with others for complex workflows.

**Key Features**:
- **Auto-Discovery**: 27 gateway Agent Skills automatically activate based on task context
- **Progressive Loading**: 60-84% context reduction via tiered architecture
- **284 Skills**: Comprehensive coverage across backend, frontend, data, ML, mathematics, and more
- **Production-Tested**: Real-world patterns from building systems at scale

**Use this when:**
- Starting a new project and need architecture patterns
- Working with unfamiliar technologies or frameworks
- Need production-ready workflows and best practices
- Building complex multi-technology systems
- Onboarding to a new codebase
- Learning advanced mathematics or programming language theory

## Quick Start

**Auto-discovery** (Recommended):
Just start working. Claude Code will automatically activate relevant gateway skills based on your task.

**Manual discovery**:
```bash
# View skills catalog
cat skills/README.md

# Browse a category
cat skills/api/INDEX.md

# Load a specific skill
cat skills/api/rest-api-design.md
```

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
- **Elegant Design**: World-class accessible interfaces, chat/terminal/code UIs, design systems

**Mobile:**
- **Swift/SwiftUI**: iOS native (iOS 17+), Swift concurrency, SwiftData
- **React Native**: Cross-platform mobile development

### Build Systems & Debugging (22 skills)
**Build Systems:**
- **Make**: Makefile syntax, targets, pattern rules, automatic variables, phony targets
- **CMake**: Modern CMake (3.20+, 4.0.2), target-based approach, find_package, FetchContent
- **Gradle**: Kotlin DSL, dependency management, version catalogs, build cache
- **Maven**: POM structure, dependency management, lifecycle phases, plugins
- **Bazel**: BUILD files, hermetic builds, remote caching, Starlark rules, monorepo patterns
- **Cross-platform**: Platform detection, conditional compilation, toolchains
- **Build Optimization**: Incremental builds, build caching (ccache, sccache), parallel builds

**Debugging:**
- **Native Debugging**: GDB (C/C++), LLDB (macOS/Swift, 50x faster step-over), TUI mode
- **Language Debugging**: Python (pdb, ipdb, VSCode), browser DevTools (performance, memory)
- **Production Debugging**: Remote debugging, non-intrusive debugging, dynamic logging, sampling profilers
- **Specialized Debugging**: Memory leaks (Valgrind, AddressSanitizer), concurrency (ThreadSanitizer, race detection)
- **System Debugging**: Core dumps, crash debugging (fuzzing with AFL/libFuzzer), performance profiling (perf, pprof, flame graphs)
- **Infrastructure Debugging**: Container debugging (docker exec, kubectl debug), network debugging (tcpdump, Wireshark), distributed systems debugging

### Cloud & Infrastructure (46 skills)
**Cloud Platforms:**
- **AWS**: Lambda functions, API Gateway, EC2 compute, S3/EBS/EFS storage, RDS/DynamoDB databases, VPC networking, IAM security (7 skills)
- **GCP**: Compute Engine/Cloud Run/GKE, Cloud Storage, Cloud SQL/Firestore/Spanner, VPC networking, IAM, Cloud Functions/App Engine (6 skills)

**Serverless & Edge:**
- **Modal.com**: GPU workloads (L40S/H100), serverless functions, web endpoints
- **Cloudflare Workers**: Edge computing, KV storage, Durable Objects
- **Vercel**: Serverless functions, edge runtime, automatic deployments
- **Heroku/Netlify**: Platform deployment, add-ons, optimization

**Infrastructure as Code:**
- **Terraform**: Resource patterns, state management
- **Kubernetes**: Pod design, services, deployments
- **Docker**: Multi-stage builds, security, optimization

**CI/CD & Observability:**
- **GitHub Actions**: Workflows, matrix builds, caching, security
- **Structured Logging**: JSON logging, correlation IDs, log aggregation
- **Metrics & Tracing**: Prometheus, StatsD, OpenTelemetry integration, distributed tracing, cardinality management
- **Alerting & Dashboards**: Alert conditions, on-call patterns, Grafana dashboards, SLO monitoring
- **Observability Cost**: Cost optimization, sampling strategies, log reduction, metrics aggregation
- **Incident Response**: Production incident debugging, logs→metrics→traces workflow, time-travel debugging, RCA

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

### Caching & Performance (7 skills)
**Multi-Layer Caching:**
- **Fundamentals**: Cache-Aside, Write-Through, Write-Behind patterns; LRU/LFU/TTL eviction
- **HTTP Caching**: Cache-Control, ETag, Last-Modified, immutable assets
- **CDN Edge**: Cloudflare/Fastly/CloudFront optimization, Edge TTL, cache warming
- **Application Cache**: Redis patterns, distributed caching, cache stampede prevention
- **Invalidation**: Time-based, event-based, key-based, version-based strategies
- **PWA/Service Workers**: Offline-first, Workbox, background sync
- **Monitoring**: Hit ratio metrics, Redis INFO, CDN analytics, load testing

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

### Specialized Domains (85 skills)

**Collaboration & Process:**
- **GitHub**: Repository management, pull requests, issues/projects, security features, Actions (5 skills)
- **PRD Writing**: Structure/templates, requirements gathering, user stories, technical specs (4 skills)
- **RFC Writing**: Structure/format, technical design, consensus building, decision documentation (4 skills)

**Machine Learning & AI:**
- **LLM Evaluation**: Benchmarks (MMLU, HellaSwag, HumanEval), frameworks (Arize Phoenix, Braintrust, LangSmith), LLM-as-judge (Prometheus 2, G-Eval), RAGAS metrics, custom evaluation (5 skills)
- **Model Routing & Selection**: RouteLLM framework, model comparison (GPT-4o, Claude, Gemini, DeepSeek), multi-model orchestration, cost optimization (3 skills)
- **Advanced RAG**: Hybrid search (vector + BM25), reranking (cross-encoder, LLM-as-reranker), GraphRAG (Microsoft 2024), hierarchical retrieval (4 skills)
- **DSPy Framework**: Signatures, modules, optimizers, RAG, assertions (7 skills)
- **HuggingFace**: Hub, Transformers, Datasets, Spaces, AutoTrain (5 skills)
- **LLM Fine-tuning**: Unsloth, LoRA/PEFT, dataset prep (3 skills)
- **Diffusion Models**: Stable Diffusion deployment, fine-tuning basics (3 skills)

**Information Retrieval:**
- **Search**: TF-IDF, BM25, Elasticsearch, inverted indexes (1 skill)
- **Vector Search**: Dense retrieval, embeddings, vector databases (1 skill)
- **Ranking**: Learning to rank, cross-encoders, reranking (1 skill)
- **Recommendations**: Collaborative filtering, content-based, hybrid systems (1 skill)
- **Query Understanding**: Query expansion, spell correction, semantic search (1 skill)

**Systems Programming:**
- **WebAssembly**: Fundamentals, Rust toolchain, browser integration, server-side (4 skills)
- **eBPF**: Fundamentals, tracing/observability, networking, security monitoring (4 skills)

**Formal Methods:**
- **SAT/SMT Solvers**: Z3 basics, SAT solving strategies, SMT theory (3 skills)
- **Lean 4**: Proof basics, tactics, mathlib4, theorem proving (4 skills)
- **Constraint Satisfaction**: CSP modeling, propagation, backtracking (3 skills)

**Advanced Mathematics** (11 skills):
- **Numerical**: Linear algebra, optimization algorithms, numerical methods, probability/statistics (4 skills)
- **Pure Math**: Topology (point-set, algebraic), category theory, differential equations, abstract algebra, set theory, number theory (7 skills)

**Programming Language Theory** (13 skills):
- **Core PLT**: Lambda calculus, type systems, dependent types
- **Curry-Howard & Semantics**: Propositions as types, operational semantics, program verification
- **Typed Holes & Live Programming**: Hazel/Hazelnut calculus, structure editors, incremental typing (OOPSLA 2025)
- **AI-Assisted Programming**: LLM + typed holes integration (OOPSLA 2024), static context for code synthesis

**Real-time & Networking:**
- WebSocket implementation, Server-Sent Events
- Pub/sub patterns, real-time sync
- Tailscale VPN, mTLS, NAT traversal
- Network resilience patterns, Mosh

**Workflow & Productivity:**
- **Beads**: Task management, context strategies, multi-session workflows
- **TUI Development**: Bubble Tea (Go), Ratatui (Rust)
- **Meta Skills**: Intelligent skill discovery for repos and prompts
- **Typed Holes Refactor**: Systematic TDD-based refactoring methodology
- **Anti-Slop**: Detection and cleanup of AI-generated "slop" in text, code, and design

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
ls skills/modal-*.md         # Modal.com: 8 skills
ls skills/api/*.md           # API design: 7 skills
ls skills/cloud/aws/*.md     # AWS: 7 skills
ls skills/cloud/gcp/*.md     # GCP: 6 skills
ls skills/formal/*.md        # Formal methods: 10 skills
ls skills/ml/*.md            # Machine learning: 21 skills (DSPy, HuggingFace, LLM, diffusion)
ls skills/plt/*.md           # Programming language theory: 13 skills
ls skills/ir/*.md            # Information Retrieval: 5 skills
ls skills/wasm/*.md          # WebAssembly: 4 skills
ls skills/ebpf/*.md          # eBPF: 4 skills

# By category directory
ls skills/build-systems/*.md  # Build Systems: 8 skills (Make, CMake, Gradle, Maven, Bazel)
ls skills/debugging/*.md      # Debugging: 14 skills (GDB, LLDB, Python, browser, remote, production, etc.)
ls skills/caching/*.md        # Caching: 7 skills
ls skills/cicd/*.md          # CI/CD: 5 skills
ls skills/infrastructure/*.md # Infrastructure: 6 skills
ls skills/observability/*.md  # Observability: 8 skills (logging, metrics, tracing, OTel, cost, incidents)
ls skills/deployment/*.md     # Deployment: 6 skills
ls skills/math/*.md          # Mathematics: 11 skills
ls skills/mobile/*.md        # Mobile: 4 skills
ls skills/collaboration/github/*.md  # GitHub: 5 skills
ls skills/product/*.md       # PRD Writing: 4 skills
ls skills/engineering/*.md   # RFC Writing: 4 skills

# By task
grep -l "GraphQL" skills/**/*.md
grep -l "streaming" skills/**/*.md
grep -l "topology" skills/**/*.md
grep -l "verification" skills/**/*.md
grep -l "Lambda" skills/**/*.md
grep -l "Kubernetes" skills/**/*.md
```

### 3. Compose Workflows
```bash
# Full-stack web app with caching
skills/api/rest-api-design.md
+ skills/frontend/nextjs-app-router.md
+ skills/database/postgres-schema-design.md
+ skills/caching/redis-caching-patterns.md
+ skills/caching/http-caching.md
+ skills/caching/cdn-edge-caching.md
+ skills/cicd/github-actions-workflows.md

# ML/AI deployment with DSPy
skills/ml/dspy-setup.md
+ skills/ml/dspy-modules.md
+ skills/modal-gpu-workloads.md
+ skills/modal-web-endpoints.md

# Full-stack caching strategy
skills/caching/caching-fundamentals.md
+ skills/caching/service-worker-caching.md (browser)
+ skills/caching/http-caching.md (HTTP layer)
+ skills/caching/cdn-edge-caching.md (CDN edge)
+ skills/caching/redis-caching-patterns.md (application)
+ skills/caching/cache-invalidation-strategies.md
+ skills/caching/cache-performance-monitoring.md

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

# Formal verification
skills/plt/type-systems.md
+ skills/plt/program-verification.md
+ skills/formal/z3-solver-basics.md
+ skills/formal/lean-proof-basics.md
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
└── skills/                # 247 atomic skills across 43 categories
    │
    ├── _INDEX.md          # Full catalog with use cases and workflows
    │
    ├── Core Foundation (108 skills)
    │   ├── api/           # REST, GraphQL, auth, rate limiting (7)
    │   ├── testing/       # Unit, integration, e2e, TDD (6)
    │   ├── containers/    # Docker, Compose, security (5)
    │   ├── frontend/      # React, Next.js, performance, a11y (9)
    │   ├── database/      # Postgres, MongoDB, Redis, Redpanda, Iceberg, DuckDB (11)
    │   ├── caching/       # Multi-layer caching: fundamentals, HTTP, CDN, Redis, invalidation, Service Workers, monitoring (7)
    │   ├── build-systems/ # Make, CMake, Gradle, Maven, Bazel, cross-platform, optimization (8)
    │   ├── debugging/     # GDB, LLDB, Python, browser, remote, production, memory, concurrency, profiling, containers, network, distributed (14)
    │   ├── beads-*.md     # Workflow & task management (4)
    │   ├── skill-*.md     # Meta skills: discovery & planning (5)
    │   ├── swiftui-*.md   # iOS/Swift native development (6)
    │   ├── modal-*.md     # Modal.com serverless + GPU (8)
    │   ├── network-*.md   # Tailscale, mTLS, Mosh, NAT (5)
    │   ├── bubbletea-*.md # TUI development Go/Rust (5)
    │   ├── zig-*.md       # Zig systems programming (6)
    │   ├── anti-slop/     # AI slop detection and cleanup (1)
    │   └── typed-holes-refactor/ # Systematic refactoring (1)
    │
    ├── Cloud Platforms (13 skills)
    │   ├── cloud/aws/     # Lambda, API Gateway, EC2, Storage, Databases, Networking, IAM (7)
    │   └── cloud/gcp/     # Compute, Storage, Databases, Networking, IAM, Serverless (6)
    │
    ├── Advanced Infrastructure (28 skills)
    │   ├── cicd/          # GitHub Actions, testing, deployment (5)
    │   ├── infrastructure/# Terraform, K8s, AWS, Cloudflare (6)
    │   ├── observability/ # Logging, metrics, tracing, alerting, dashboards, OTel, cost optimization, incident debugging (8)
    │   ├── realtime/      # WebSocket, SSE, pub/sub (4)
    │   └── data/          # ETL, streaming, batch processing (5)
    │
    ├── Collaboration & Process (17 skills)
    │   ├── collaboration/github/  # Repositories, PRs, issues, security, Actions (5)
    │   ├── product/       # PRD writing: structure, requirements, user stories, specs (4)
    │   └── engineering/   # RFC writing: structure, design, consensus, decisions (4)
    │
    └── Specialized Domains (81 skills)
        ├── ml/            # DSPy, HuggingFace, LLM fine-tuning, diffusion models (21)
        ├── ir/            # Information Retrieval: search, vector, ranking, recommendations (5)
        ├── wasm/          # WebAssembly: fundamentals, Rust, browser, server (4)
        ├── ebpf/          # eBPF: fundamentals, tracing, networking, security (4)
        ├── formal/        # SAT/SMT solvers, Lean 4, CSP (10)
        ├── deployment/    # Heroku, Netlify platforms (6)
        ├── math/          # Linear algebra, topology, category theory, etc. (11)
        ├── plt/           # Lambda calculus, type systems, verification, typed holes (13)
        └── mobile/        # React Native development (4)
```

## Development Philosophy

### Atomic Skills
- **Focused**: Each skill covers one clear topic (~320 lines average)
- **Composable**: Skills combine for complex workflows
- **Production-tested**: All patterns used in real projects
- **Cross-referenced**: Related skills linked for discovery
- **Agent-compatible**: YAML frontmatter enables programmatic discovery

### Quality Gates
1. **Critical Thinking**: Push back on vague requirements
2. **Standards Enforcement**: Correct package managers (uv not pip, etc.)
3. **Testing Protocol**: Always commit before testing
4. **Error Handling**: No TODOs/mocks - implement or file issue
5. **Code Quality**: All Python code blocks validated, frontmatter verified
6. **Date Validation**: No future dates in "Last Updated" fields

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

### Scenario: Build ML-powered API with DSPy
1. Read `skill-prompt-discovery.md` → identifies: Modal, FastAPI, DSPy skills
2. Compose workflow:
   - `ml/dspy-setup.md` → Configure DSPy with Modal-hosted models
   - `ml/dspy-modules.md` → Build RAG pipeline
   - `ml/dspy-optimizers.md` → Optimize prompts with BootstrapFewShot
   - `modal-gpu-workloads.md` → Deploy on L40S GPU
   - `modal-web-endpoints.md` → Expose FastAPI endpoint
   - `api/rest-api-design.md` → Design API contract
   - `api/api-rate-limiting.md` → Protect endpoint
   - `observability/structured-logging.md` → Add logging

### Scenario: Formal Verification of Algorithms
1. Start with `plt/type-systems.md` → Understand type soundness
2. Add `plt/dependent-types.md` → Learn Π-types and Σ-types
3. Use `plt/program-verification.md` → Apply Hoare logic
4. Implement in `formal/lean-proof-basics.md` → Formalize in Lean 4
5. Verify with `formal/z3-solver-basics.md` → SMT-based checking

### Scenario: Advanced Math for ML
1. Read `math/linear-algebra-computation.md` → Matrix operations
2. Add `math/optimization-algorithms.md` → Gradient descent
3. Study `math/category-theory-foundations.md` → Functors and monads
4. Apply `math/probability-statistics.md` → Statistical analysis
5. Combine with `ml/dspy-optimizers.md` → Optimize ML pipelines

### Scenario: Build iOS App with Streaming
1. Read `swiftui-architecture.md` → MVVM setup
2. Add `swift-concurrency.md` → async/await patterns
3. Implement `swiftdata-persistence.md` → local storage
4. Use `ios-networking.md` → API integration
5. Deploy backend with `redpanda-streaming.md` + `modal-web-endpoints.md`

### Scenario: AI-Assisted Programming with Typed Holes
1. Start with `plt/typed-holes-foundations.md` → Understand gradual typing and bidirectional checking
2. Study `plt/typed-holes-llm.md` → Learn OOPSLA 2024 approach to LLM + static types
3. Implement language server integration → Extract type context from holes
4. Build LLM integration → Type-driven prompts, validation pipeline, ranking
5. Add interactive refinement → User + LLM collaboration via holes
6. Optional: `plt/live-programming-holes.md` → Real-time feedback with incremental typing

## Technology Coverage Matrix

| Domain | Technologies | Skills | Key Capabilities |
|--------|-------------|--------|------------------|
| **Backend** | Python, Zig, Rust, Go | 18 | Systems programming, async, memory safety |
| **Frontend** | React, Next.js, TypeScript | 9 | SSR, performance, a11y, SEO, elegant design |
| **Mobile** | SwiftUI, React Native | 10 | iOS native, cross-platform |
| **Build Systems** | Make, CMake, Gradle, Maven, Bazel | 8 | C/C++ builds, JVM builds, monorepos, cross-platform, optimization |
| **Debugging** | GDB, LLDB, pdb, DevTools, Valgrind, ThreadSanitizer | 14 | Native, language, production, memory, concurrency, profiling, infrastructure |
| **Cloud** | AWS, GCP, Modal, Vercel, Cloudflare | 27 | Serverless, GPU, edge, compute, storage, networking |
| **Database** | Postgres, Mongo, Redis, Redpanda, Iceberg, DuckDB | 11 | OLTP, NoSQL, streaming, analytics |
| **Caching** | Redis, HTTP, CDN (Cloudflare/Fastly/CloudFront), Service Workers | 7 | Multi-layer caching, invalidation, performance monitoring |
| **ML/AI** | DSPy, HuggingFace, Unsloth, Arize Phoenix, Prometheus, GraphRAG | 33 | LLM orchestration, evaluation (benchmarks, LLM-as-judge, RAGAS), model routing, advanced RAG (hybrid, reranking, GraphRAG), fine-tuning |
| **IR** | Elasticsearch, Vector DBs, Ranking, Recommenders | 5 | Search, semantic retrieval, recommendations |
| **Systems** | WebAssembly, eBPF | 8 | Browser/server wasm, observability, networking, security |
| **Collaboration** | GitHub, PRD, RFC | 17 | Repository management, product specs, technical design |
| **Formal** | Z3, Lean 4, CSP | 10 | Proof systems, constraint solving |
| **Math** | Linear algebra, topology, category theory, etc. | 11 | Numerical + pure mathematics |
| **PLT** | Lambda calculus, type systems, typed holes, Hazel, LLM integration | 13 | Language design, live programming, AI-assisted coding |
| **DevOps** | GitHub Actions, Terraform, K8s, Docker | 16 | CI/CD, IaC, containers |
| **Observability** | Prometheus, OpenTelemetry, Grafana, structured logging | 8 | Metrics, tracing, logs, dashboards, cost optimization, incident response |
| **Data** | ETL, Streaming, Batch | 10 | Pipelines, real-time, analytics |

## Quality Assurance

All skills are validated through automated CI/CD pipelines:

- ✅ **Code Block Validation**: 1100+ Python/Swift/TypeScript/Bash/C/Java blocks syntax-checked
- ✅ **Frontmatter Validation**: 226 skills with proper YAML frontmatter
- ✅ **Date Validation**: All "Last Updated" dates verified (no future dates)
- ✅ **Format Compliance**: Atomic skill guidelines enforced (~250-500 lines)
- ✅ **Cross-References**: Related skills linked for discoverability

## Contributing

This is a personal reference repository maintained through practical development experience. Skills are:
- Added when new technologies are mastered
- Updated when better patterns emerge
- Refined based on production use
- Kept atomic and focused
- Validated through automated testing

Feel free to fork and adapt for your own use.

---

**Total: 226 atomic skills** | **Average: 420 lines/skill** | **45 categories** | **100% CI-validated**
