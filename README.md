# Atomic Skills for Claude Code

[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blue)](https://docs.claude.com/en/docs/claude-code/plugins)
[![Skills](https://img.shields.io/badge/Skills-447-green)](skills/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

**Context-efficient development knowledge via progressive skill discovery**

> **Claude Code Plugin**: Install with `/plugin install https://github.com/rand/cc-polymath`

This repository solves a tradeoff problem: how to give Claude Code access to comprehensive development knowledge without overwhelming its context window on boot. The solution is atomic, composable skills organized through a multi-tier discovery system.

## The Problem: Context vs Coverage

Using the default mechanism with many atomic skills yields a dilemma:
- **Load everything upfront** → 25K+ tokens consumed before any real work begins
- **Load nothing** → Claude lacks essential patterns and best practices
- **Manual loading** → Users must know what exists to ask for it

This creates an challenging tradeoff between comprehensive coverage and context efficiency.

## The Solution: Atomic Skills + Progressive Discovery

### Atomic Skills (447 total)
Each skill is **focused, self-contained, and composable**:
- Average 320 lines - small enough to load quickly
- Single responsibility - covers one clear topic
- Production-tested - real patterns from building at scale
- Cross-referenced - links to related skills for composition

**Why atomic matters**: Loading 5 focused skills (1.5K tokens) beats loading one monolithic guide (8K tokens) when you only need specific knowledge. Granularity enables precision.

### Three-Tier Architecture

**Tier 1: Gateway Skills (31 auto-discovered Agent Skills)**
Lightweight entry points that activate automatically based on keywords:
- `discover-api` → triggers on "REST", "GraphQL", "authentication"
- `discover-database` → triggers on "PostgreSQL", "MongoDB", "Redis"
- `discover-zig` → triggers on "Zig", "comptime", "allocators"

Each gateway is ~200 lines with quick reference and loading commands.

**Tier 2: Category Indexes (30 detailed references)**
Full skill listings with descriptions, use cases, and workflows:
- `api/INDEX.md` → All 7 API skills with integration patterns
- `database/INDEX.md` → All 11 database skills with decision trees
- Only loaded when browsing or planning work

**Tier 3: Individual Skills (on-demand)**
Complete implementation guides loaded only when needed:
- `api/rest-api-design.md` → Full REST patterns
- `database/postgres-query-optimization.md` → EXPLAIN plans, indexes

### Why This Works

**Context efficiency**: 60-84% reduction vs monolithic index
- Old approach: Load 25K token index on boot
- New approach: Load 2-5K tokens of relevant gateways as needed
- Result: More context available for actual code and conversation

**No boot overhead**: Claude Code starts with zero skills loaded
- Gateway skills auto-discover based on your prompt keywords
- Manual loading available when auto-discovery isn't enough
- System scales to hundreds more skills without boot cost

**Discoverability**: Users don't need to know what exists
- Keywords in prompts trigger relevant gateways automatically
- Gateways show what's available in their domain
- Progressive loading: gateway → index → specific skill

## What's Covered

### Core Development (125 skills)

**Languages & Frameworks**:
- **Backend**: Python (uv), Zig, Rust, Go (31 skills)
- **Frontend**: React, Next.js, TypeScript, Elegant Design (9 skills)
- **Mobile**: SwiftUI, Swift concurrency, SwiftData, React Native (10 skills)

**Infrastructure & DevOps**:
- **Build Systems**: Make, CMake, Gradle, Maven, Bazel, cross-platform (8 skills)
- **Debugging**: GDB, LLDB, Python, browser, memory, concurrency, production, distributed systems (14 skills)
- **Cloud**: AWS (7), GCP (6), Modal.com, Cloudflare Workers, Vercel (13 skills)
- **Containers**: Docker, Kubernetes, security (5 skills)
- **CI/CD**: GitHub Actions, pipelines (4 skills)
- **Observability**: Logging, metrics, tracing, OpenTelemetry, incident response (8 skills)

**Data & APIs**:
- **Databases**: Postgres, MongoDB, Redis, Redpanda, Iceberg, DuckDB (11 skills)
- **Caching**: Multi-layer (browser, HTTP, CDN, Redis), invalidation strategies (7 skills)
- **API Design**: REST, GraphQL, auth, rate limiting, versioning (7 skills)
- **Data Engineering**: ETL, streaming, batch processing (5 skills)
- **Testing**: Unit, integration, e2e, TDD, coverage (6 skills)

### Specialized Domains (85 skills)

**Machine Learning & AI** (33 skills):
- **LLM Evaluation**: Benchmarks (MMLU, HellaSwag), frameworks (Arize Phoenix, Braintrust), LLM-as-judge (Prometheus, G-Eval), RAGAS metrics
- **Model Routing**: RouteLLM, model comparison, multi-model orchestration
- **Advanced RAG**: Hybrid search, reranking (cross-encoder, LLM), GraphRAG, hierarchical retrieval
- **DSPy Framework**: Signatures, modules, optimizers, RAG, assertions (7 skills)
- **HuggingFace**: Hub, Transformers, Datasets, Spaces, AutoTrain (5 skills)
- **Fine-tuning**: Unsloth, LoRA/PEFT, dataset prep (3 skills)

**Rust & PyO3** (19 skills):
- **DSPy-PyO3 Integration**: RAG pipelines, agents, async streaming, production deployment, optimization (7 skills with 36 production examples)
- **Performance**: GIL management, parallel execution, data science, collections/iterators (6 skills)
- **Web**: Axum frameworks, streaming responses, IPC, gRPC (2 skills)
- **Production**: Packaging, testing, debugging, modules/functions/errors (4 skills with 20 examples)

**Information Retrieval** (5 skills):
- Search fundamentals (TF-IDF, BM25, Elasticsearch)
- Vector search (dense retrieval, embeddings)
- Ranking & reranking (learning to rank, cross-encoders)
- Recommendation systems (collaborative, content-based, hybrid)
- Query understanding (expansion, spell correction, semantic search)

**Programming Language Theory** (13 skills):
- Lambda calculus, type systems, dependent types
- Curry-Howard correspondence, operational semantics
- Program verification with Hoare logic
- **Typed Holes & Live Programming**: Hazel/Hazelnut calculus, incremental typing
- **AI-Assisted Programming**: LLM + typed holes integration (OOPSLA 2024), type-driven code synthesis

**Formal Methods** (10 skills):
- **SAT/SMT Solvers**: Z3 basics, SAT strategies, SMT theory (3 skills)
- **Lean 4**: Proof basics, tactics, mathlib4, theorem proving (4 skills)
- **Constraint Satisfaction**: CSP modeling, propagation, backtracking (3 skills)

**Advanced Mathematics** (11 skills):
- **Numerical**: Linear algebra, optimization, probability/statistics (4 skills)
- **Pure Math**: Topology (point-set, algebraic), category theory, differential equations, abstract algebra, set theory, number theory (7 skills)

**Systems Programming** (8 skills):
- **WebAssembly**: Fundamentals, Rust toolchain, browser integration, server-side (4 skills)
- **eBPF**: Fundamentals, tracing/observability, networking, security monitoring (4 skills)

**Collaboration & Process** (14 skills):
- **GitHub**: Repository management, pull requests, issues/projects, security, Actions (5 skills)
- **PRD Writing**: Structure, requirements gathering, user stories, technical specs (4 skills)
- **RFC Writing**: Structure, technical design, consensus building, decision docs (4 skills)

**Real-time & Networking** (5 skills):
- WebSocket, Server-Sent Events, pub/sub patterns
- Tailscale VPN, mTLS, NAT traversal, Mosh
- Network resilience patterns

### Workflow & Meta Skills (7 skills)

- **Beads**: AI-native task management, context strategies, multi-session workflows (4 skills)
- **TUI Development**: Bubble Tea (Go), Ratatui (Rust) (5 skills)
- **Skill Discovery**: Intelligent skill activation for repos and prompts (5 skills)
- **Anti-Slop**: Detection and cleanup of AI-generated patterns (Agent Skill)
- **Elegant Design**: World-class accessible interfaces, design systems (Agent Skill)
- **Typed Holes Refactor**: Systematic TDD-based refactoring (Agent Skill)

## Quick Start

### Installation

**As Claude Code Plugin (Recommended)**:
```bash
/plugin install https://github.com/rand/cc-polymath
```

That's it! All 447 skills and the `/skills` command are immediately available.

**For local development or testing**:
```bash
/plugin install /Users/rand/src/cc-polymath
```

### Auto-Discovery (How It Works)
Just start working. Claude Code automatically activates relevant gateway skills based on your task keywords.

**Example**: Mention "REST API with PostgreSQL" → `discover-api` and `discover-database` gateways activate automatically.

### Manual Loading
When you need to browse or plan:

```bash
# Browse skills catalog
cat skills/README.md

# View a category
cat skills/api/INDEX.md          # All API skills
cat skills/database/INDEX.md     # All database skills

# Load a gateway
cat skills/discover-ml/SKILL.md  # ML gateway with quick reference

# Load specific skills
cat skills/api/rest-api-design.md
cat skills/database/postgres-query-optimization.md
```

### Composing Workflows

Skills are designed to combine for complex workflows:

**Full-stack web app**:
```bash
cat skills/api/rest-api-design.md
cat skills/frontend/nextjs-app-router.md
cat skills/database/postgres-schema-design.md
cat skills/caching/redis-caching-patterns.md
cat skills/cicd/github-actions-workflows.md
```

**ML deployment with DSPy**:
```bash
cat skills/ml/dspy-setup.md
cat skills/ml/dspy-modules.md
cat skills/modal/modal-gpu-workloads.md
cat skills/modal/modal-web-endpoints.md
cat skills/observability/structured-logging.md
```

**Multi-layer caching strategy**:
```bash
cat skills/caching/caching-fundamentals.md
cat skills/caching/service-worker-caching.md    # Browser
cat skills/caching/http-caching.md              # HTTP layer
cat skills/caching/cdn-edge-caching.md          # CDN edge
cat skills/caching/redis-caching-patterns.md    # Application
cat skills/caching/cache-invalidation-strategies.md
```

**iOS app with streaming backend**:
```bash
cat skills/mobile/swiftui-architecture.md
cat skills/mobile/swift-concurrency.md
cat skills/mobile/swiftdata-persistence.md
cat skills/mobile/ios-networking.md
cat skills/database/redpanda-streaming.md
```

## Repository Structure

```
.
├── CLAUDE.md              # Development guidelines & protocols
│                          # - Multi-agent orchestration
│                          # - Work Plan Protocol (4 phases)
│                          # - Language standards (uv, cargo, zig)
│                          # - Testing protocols
│                          # - Anti-patterns
│
├── README.md              # This file
│
└── skills/                # 283 atomic skills, 31 gateways, 30 categories
    │
    ├── README.md          # Skills catalog
    │
    ├── Gateway Skills (31 auto-discovered Agent Skills)
    │   ├── discover-api/           # REST, GraphQL, authentication
    │   ├── discover-database/      # PostgreSQL, MongoDB, Redis
    │   ├── discover-frontend/      # React, Next.js, UI components
    │   ├── discover-ml/            # Machine learning, models
    │   ├── discover-math/          # Mathematics, algorithms
    │   ├── discover-plt/           # Programming language theory
    │   ├── discover-formal/        # Formal methods, verification
    │   ├── discover-cloud/         # Serverless, cloud platforms
    │   ├── discover-zig/           # Zig systems programming
    │   ├── discover-networking/    # SSH, mTLS, VPN, resilience
    │   ├── discover-workflow/      # Beads, context strategies
    │   └── ... 20 more gateways
    │
    ├── Category Indexes (30 detailed references)
    │   ├── api/INDEX.md            # All API skills overview
    │   ├── database/INDEX.md       # All database skills overview
    │   ├── ml/INDEX.md             # All ML skills overview
    │   └── ... 27 more indexes
    │
    └── Skills by Category
        ├── api/           # REST, GraphQL, auth (7)
        ├── database/      # Postgres, MongoDB, Redis, streaming (11)
        ├── frontend/      # React, Next.js, performance (8)
        ├── mobile/        # iOS/Swift, SwiftUI, SwiftData (10)
        ├── testing/       # Unit, integration, e2e (6)
        ├── caching/       # Multi-layer caching (7)
        ├── build-systems/ # Make, CMake, Gradle, Maven, Bazel (8)
        ├── debugging/     # GDB, LLDB, production, memory (14)
        ├── cloud/         # AWS, GCP, Modal, serverless (13)
        ├── containers/    # Docker, Kubernetes (5)
        ├── cicd/          # GitHub Actions, pipelines (4)
        ├── observability/ # Logging, metrics, tracing (8)
        ├── ml/            # DSPy, HuggingFace, LLM, RAG (30)
        ├── ir/            # Information retrieval (5)
        ├── math/          # Linear algebra, topology, category theory (19)
        ├── plt/           # Type systems, verification, typed holes (13)
        ├── formal/        # SAT/SMT, Lean, CSP (10)
        ├── wasm/          # WebAssembly (4)
        ├── ebpf/          # eBPF kernel programming (4)
        ├── networking/    # SSH, mTLS, VPN, NAT traversal (5)
        ├── tui/           # Terminal UI: Bubble Tea, Ratatui (5)
        ├── zig/           # Zig systems programming (6)
        ├── rust/          # Rust & PyO3: DSPy integration, performance, production (19)
        ├── workflow/      # Beads task management (4)
        ├── data/          # ETL, streaming, batch (5)
        ├── deployment/    # Heroku, Netlify (6)
        ├── realtime/      # WebSocket, SSE, pub/sub (4)
        ├── collaboration/ # GitHub, CodeTour (6)
        ├── product/       # PRD writing (4)
        ├── engineering/   # RFC writing (4)
        ├── infrastructure/# Terraform, Cloudflare Workers (6)
        │
        ├── Agent Skills (Root)
        │   ├── anti-slop/          # AI slop detection & cleanup
        │   ├── elegant-design/     # World-class UI design
        │   └── typed-holes-refactor/ # Systematic refactoring
        │
        └── Meta Skills (Root)
            ├── skill-repo-discovery.md    # Analyze repos for skills
            ├── skill-prompt-discovery.md  # Extract signals from prompts
            ├── skill-creation.md          # Create new skills
            └── skill-*-planning.md        # Planning workflows
```

## Technology Coverage

| Domain | Technologies | Skills | Gateway |
|--------|-------------|--------|---------|
| **Backend** | Python, Zig, Rust, Go | 18 | discover-backend |
| **Frontend** | React, Next.js, TypeScript | 9 | discover-frontend |
| **Mobile** | SwiftUI, Swift, React Native | 10 | discover-mobile |
| **Build** | Make, CMake, Gradle, Maven, Bazel | 8 | discover-build-systems |
| **Debug** | GDB, LLDB, pdb, DevTools, Valgrind | 14 | discover-debugging |
| **Cloud** | AWS, GCP, Modal, Vercel, Cloudflare | 27 | discover-cloud |
| **Database** | Postgres, Mongo, Redis, Redpanda, Iceberg | 11 | discover-database |
| **Caching** | Redis, HTTP, CDN, Service Workers | 7 | discover-caching |
| **ML/AI** | DSPy, HuggingFace, Arize, GraphRAG | 33 | discover-ml |
| **Rust/PyO3** | DSPy integration, RAG, agents, async, production | 19 | N/A |
| **IR** | Elasticsearch, Vector DBs, Ranking | 5 | discover-ir |
| **Systems** | WebAssembly, eBPF | 8 | discover-wasm, discover-ebpf |
| **Collaboration** | GitHub, PRD, RFC | 17 | discover-collaboration, discover-product, discover-engineering |
| **Formal** | Z3, Lean 4, CSP | 10 | discover-formal |
| **Math** | Linear algebra, topology, category theory | 19 | discover-math |
| **PLT** | Lambda calculus, type systems, typed holes | 13 | discover-plt |
| **DevOps** | GitHub Actions, Terraform, K8s, Docker | 16 | discover-cicd, discover-infrastructure, discover-containers |
| **Observability** | Prometheus, OpenTelemetry, Grafana | 8 | discover-observability |
| **Networking** | SSH, mTLS, VPN, Tailscale, NAT | 5 | discover-networking |
| **TUI** | Bubble Tea, Ratatui | 5 | discover-tui |
| **Zig** | Build systems, C interop, memory management | 6 | discover-zig |
| **Workflow** | Beads, context strategies | 4 | discover-workflow |

## Development Philosophy

### Atomic & Composable
- **Focused**: Each skill covers one topic (~320 lines)
- **Self-contained**: Can be loaded independently
- **Cross-referenced**: Links to related skills
- **Production-tested**: Real patterns from building at scale

### Progressive Discovery
- **Zero boot cost**: No skills loaded until needed
- **Automatic activation**: Gateway skills trigger on keywords
- **Manual override**: Browse and load specific skills
- **Context efficient**: Load only what's relevant

### Quality Standards
- ✅ **Code Block Validation**: 1100+ blocks syntax-checked
- ✅ **Frontmatter Validation**: 283 skills with YAML metadata
- ✅ **Date Validation**: No future dates in "Last Updated"
- ✅ **CI/CD Pipeline**: Automated validation on every commit
- ✅ **Cross-References**: Related skills linked for discoverability

## CLAUDE.md Development Guidelines

This repository includes comprehensive development guidelines in `CLAUDE.md`:

- **Multi-Agent Orchestration**: Coordinated system with Orchestrator, Optimizer, Reviewer, Executor
- **Work Plan Protocol**: 4-phase development (Prompt→Spec→Full Spec→Plan→Artifacts)
- **Beads Workflow**: AI-native task management with dependencies
- **Language Standards**: Correct tools (uv not pip, etc.)
- **Testing Protocol**: Commit before testing (mandatory)
- **Anti-Patterns**: Critical violations and recovery procedures

## Example Use Cases

### Build ML-powered API
```bash
cat skills/ml/dspy-setup.md              # Configure DSPy
cat skills/ml/dspy-modules.md            # Build RAG pipeline
cat skills/ml/dspy-optimizers.md         # Optimize prompts
cat skills/modal/modal-gpu-workloads.md  # Deploy on GPU
cat skills/modal/modal-web-endpoints.md  # Expose API
cat skills/api/rest-api-design.md        # Design contract
cat skills/api/api-rate-limiting.md      # Protect endpoint
```

### Formal Verification
```bash
cat skills/plt/type-systems.md           # Type soundness
cat skills/plt/dependent-types.md        # Π-types, Σ-types
cat skills/plt/program-verification.md   # Hoare logic
cat skills/formal/lean-proof-basics.md   # Formalize in Lean
cat skills/formal/z3-solver-basics.md    # SMT checking
```

### AI-Assisted Programming
```bash
cat skills/plt/typed-holes-foundations.md  # Gradual typing
cat skills/plt/typed-holes-llm.md          # LLM integration
cat skills/plt/live-programming-holes.md   # Real-time feedback
```

### Multi-Layer Caching
```bash
cat skills/caching/caching-fundamentals.md           # Core patterns
cat skills/caching/service-worker-caching.md         # Browser layer
cat skills/caching/http-caching.md                   # HTTP layer
cat skills/caching/cdn-edge-caching.md               # CDN layer
cat skills/caching/redis-caching-patterns.md         # Application layer
cat skills/caching/cache-invalidation-strategies.md  # Invalidation
cat skills/caching/cache-performance-monitoring.md   # Monitoring
```

## Level 3 Resources: Production-Ready Tools & References

**In Progress**: Building comprehensive Level 3 Resources for high-priority skills.

### What Are Level 3 Resources?

Each skill follows Anthropic's agent skills framework with three progressive levels:
- **Level 1**: Skill file (300-400 lines) - Core concepts, patterns, quick reference
- **Level 2**: Category INDEX - Detailed listings and workflows
- **Level 3**: Resources directory - Production tools, comprehensive references, examples

**Level 3 Resources** transform skills from guides into executable toolkits:

**REFERENCE.md** (1,500-4,000 lines):
- Comprehensive technical documentation
- Architecture patterns and best practices
- Troubleshooting guides and anti-patterns
- Integration examples and production patterns

**Scripts** (3 per skill, 550-800+ lines each):
- Production-ready Python tools
- Executable with `--help` and `--json` support
- Type hints and comprehensive error handling
- No TODOs or placeholders - fully implemented

**Examples** (7-10 per skill):
- Production-ready code across multiple languages/platforms
- Complete implementations with error handling
- Docker Compose setups, CI/CD workflows
- Monitoring and observability configurations

### Progress: Waves 1-10 Complete

**Status**: 48/123 HIGH priority skills have Level 3 Resources (39%)

#### Recent Completion (Waves 9-10)

**Wave 9** (6 skills, +51,979 lines):
- **Cryptography**: signing-verification, hsm-integration
- **Protocols**: amqp-rabbitmq, protobuf-schemas
- **Engineering**: sre-practices, feature-flags

**Wave 10** (2 skills, +14,375 lines):
- **Cryptography**: secrets-rotation (completes 6/7 in category)
- **Protocols**: http3-quic

#### Strategic Focus: Zero-Coverage Categories

**Target**: 28 skills across Cryptography, Protocols, Engineering
**Progress**: 18/28 complete (64%)

**Cryptography**: 6/7 complete (86%)
- ✅ encryption-at-rest, key-management, certificate-management, hsm-integration, signing-verification, secrets-rotation
- ⏳ pki-fundamentals (60% complete)

**Protocols**: 6/8 complete (75%)
- ✅ grpc-implementation, kafka-streams, mqtt-messaging, amqp-rabbitmq, protobuf-schemas, http3-quic
- ⏳ websocket-protocols (15% complete)
- ⏳ tcp-optimization

**Engineering**: 6/14 complete (43%)
- ✅ deployment-strategies, e2e-testing, monitoring-alerts, incident-response, sre-practices, feature-flags
- ⏳ ci-cd-pipelines (10% complete), capacity-planning (5% complete)
- ⏳ 6 more skills

### Methodology

**Hybrid Approach**: Combines manual quality control with template-based acceleration
- 24-35 completed skills serve as templates
- Pattern consistency enforced via quality gates
- 40-50% faster than pure manual while maintaining standards
- 6 parallel agents per wave (optimal throughput)

**Quality Gates** (enforced before commit):
- REFERENCE.md: 1,500-4,000 lines
- Scripts: 3 per skill, executable, --help/--json support, type hints
- Examples: 7-10 per skill, production-ready, no placeholders
- No TODO/stub/mock comments anywhere
- CI validation on all PRs

### CI/CD Integration

Automated validation runs on all resource changes:
- REFERENCE.md line count validation
- Script executability and shebang checks
- TODO/stub/mock comment detection
- Python syntax validation for examples
- Full validation results in PR comments

See `.github/workflows/validate-resources.yml` for details.

### Future Waves

**Next Sessions** (tracked in `.work/WAVE_10_INCOMPLETE.md`):
- Complete 4 partial Wave 10 skills (pki-fundamentals, websocket-protocols, ci-cd-pipelines, capacity-planning)
- 6 additional skills to reach 100% strategic focus coverage
- Estimated: 30-40 hours across 2-3 sessions

**Long-term**: 75+ additional skills need Level 3 Resources to reach comprehensive coverage

## Contributing

This is a personal reference repository maintained through practical development experience. Skills are added when new technologies are mastered, updated when better patterns emerge, and refined based on production use.

Feel free to fork and adapt for your own use. Pull requests welcome.

---

**447 atomic skills** • **41 gateway Agent Skills** • **35+ categories** • **100% CI-validated**
