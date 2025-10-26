# Atomic Skills Index

This index catalogs all atomic skills available in the skills system, organized by category for quick discovery.

## How to Use This Index

1. **Browse by category** to find relevant skills
2. **Search by keyword** (use your editor's search function)
3. **Check triggers** - each skill lists when to use it
4. **Combine skills** - use multiple skills together for complex tasks

## Skills by Category

### API Design Skills (7 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `rest-api-design.md` | Designing REST APIs, choosing HTTP methods, status codes | ~300 |
| `graphql-schema-design.md` | Designing GraphQL schemas, resolvers, N+1 prevention | ~320 |
| `api-authentication.md` | Implementing auth (JWT, OAuth 2.0, API keys, sessions) | ~280 |
| `api-authorization.md` | RBAC, ABAC, policy engines, permission systems | ~270 |
| `api-rate-limiting.md` | Rate limiting strategies, token bucket, sliding window | ~240 |
| `api-versioning.md` | API versioning, deprecation, backward compatibility | ~220 |
| `api-error-handling.md` | Standardized error responses, RFC 7807, validation errors | ~250 |

**Common workflows:**
- New REST API: `rest-api-design.md` → `api-authentication.md` → `api-authorization.md`
- New GraphQL API: `graphql-schema-design.md` → `api-authentication.md` → `api-authorization.md`
- API hardening: `api-rate-limiting.md` → `api-error-handling.md` → `api-versioning.md`

---

### Testing Skills (6 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `unit-testing-patterns.md` | Writing unit tests, AAA pattern, mocks, test organization | ~290 |
| `integration-testing.md` | Testing database interactions, API testing, test containers | ~300 |
| `e2e-testing.md` | End-to-end tests with Playwright/Cypress, Page Object Model | ~310 |
| `test-driven-development.md` | TDD workflow, red-green-refactor, design benefits | ~260 |
| `test-coverage-strategy.md` | Coverage metrics, what to test, coverage goals | ~230 |
| `performance-testing.md` | Load testing, k6, JMeter, performance benchmarks | ~280 |

**Common workflows:**
- New feature: `test-driven-development.md` → `unit-testing-patterns.md` → `integration-testing.md`
- Test suite setup: `unit-testing-patterns.md` → `integration-testing.md` → `e2e-testing.md`
- Performance validation: `performance-testing.md` → `test-coverage-strategy.md`

---

### Container Skills (5 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `dockerfile-optimization.md` | Writing Dockerfiles, multi-stage builds, layer caching | ~310 |
| `docker-compose-development.md` | Local dev environments, docker-compose, networking | ~280 |
| `container-security.md` | Container security, vulnerability scanning, secrets | ~290 |
| `container-networking.md` | Docker networks, service discovery, DNS resolution | ~250 |
| `container-registry-management.md` | Image tagging, registry operations, CI/CD integration | ~230 |

**Common workflows:**
- New containerized app: `dockerfile-optimization.md` → `docker-compose-development.md`
- Production deployment: `dockerfile-optimization.md` → `container-security.md` → `container-registry-management.md`
- Debugging networking: `container-networking.md` → `docker-compose-development.md`

---

### Frontend Skills (9 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `react-component-patterns.md` | Component design, composition, hooks, performance | ~320 |
| `nextjs-app-router.md` | Next.js App Router, Server Components, routing | ~340 |
| `react-state-management.md` | State management (Context, Zustand, Redux Toolkit) | ~300 |
| `react-data-fetching.md` | Data fetching (SWR, React Query, Server Actions) | ~290 |
| `react-form-handling.md` | Forms (React Hook Form, Zod validation) | ~270 |
| `web-accessibility.md` | WCAG 2.1 AA compliance, ARIA, keyboard navigation | ~310 |
| `frontend-performance.md` | Bundle optimization, Core Web Vitals, code splitting | ~330 |
| `nextjs-seo.md` | SEO with Next.js, metadata API, structured data | ~250 |
| `elegant-design/SKILL.md` | World-class accessible interfaces, chat/terminal/code UIs, streaming, design systems (shadcn/ui) | ~302 |

**Common workflows:**
- New Next.js app: `nextjs-app-router.md` → `react-component-patterns.md` → `react-data-fetching.md`
- Elegant UI design: `elegant-design/SKILL.md` → `react-component-patterns.md` → `web-accessibility.md`
- Chat/Terminal/Code UI: `elegant-design/SKILL.md` (read interactive/ guides) → `react-component-patterns.md`
- Forms with validation: `react-form-handling.md` → `react-state-management.md`
- Production optimization: `frontend-performance.md` → `web-accessibility.md` → `nextjs-seo.md`

---

### Database Skills (11 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `postgres-query-optimization.md` | Debugging slow queries, analyzing EXPLAIN plans, designing indexes | ~350 |
| `postgres-migrations.md` | Schema changes, zero-downtime deployments, rollback strategies | ~280 |
| `postgres-schema-design.md` | Designing schemas, modeling relationships, choosing data types | ~320 |
| `mongodb-document-design.md` | MongoDB schemas, embedding vs referencing, document modeling | ~280 |
| `redis-data-structures.md` | Caching, sessions, rate limiting, leaderboards with Redis | ~270 |
| `database-connection-pooling.md` | Configuring connection pools, debugging pool exhaustion | ~220 |
| `orm-patterns.md` | ORM usage, N+1 prevention, eager loading, transactions | ~300 |
| `database-selection.md` | Choosing databases, SQL vs NoSQL, architecture decisions | ~280 |
| `redpanda-streaming.md` | Redpanda/Kafka streaming, event-driven architectures, rpk CLI | ~390 |
| `apache-iceberg.md` | Apache Iceberg table format, time travel, schema evolution, ACID transactions | ~615 |
| `duckdb-analytics.md` | DuckDB analytics, direct file querying, Python integration, OLAP queries | ~886 |

**Common workflows:**
- Slow query debugging: `postgres-query-optimization.md`
- Schema changes: `postgres-migrations.md` → `postgres-schema-design.md`
- New project: `database-selection.md` → `postgres-schema-design.md` or `mongodb-document-design.md`
- Performance issues: `postgres-query-optimization.md` → `database-connection-pooling.md` → `orm-patterns.md`
- Caching layer: `redis-data-structures.md`

---

### Caching & Performance (7 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `caching-fundamentals.md` | Core caching patterns (Cache-Aside, Write-Through), eviction policies (LRU, LFU, TTL), cache key design | ~400 |
| `http-caching.md` | Browser/HTTP caching, Cache-Control headers, ETag, Last-Modified, immutable assets | ~420 |
| `cdn-edge-caching.md` | CDN optimization (Cloudflare, Fastly, CloudFront), Edge TTL, cache warming, geo-caching | ~450 |
| `redis-caching-patterns.md` | Application-level caching with Redis, distributed caching, cache stampede prevention, session storage | ~420 |
| `cache-invalidation-strategies.md` | Time-based, event-based, key-based, version-based invalidation; Netflix case study (30% CPU reduction) | ~400 |
| `service-worker-caching.md` | PWA caching, Service Worker lifecycle, Workbox, offline-first, background sync | ~420 |
| `cache-performance-monitoring.md` | Cache metrics (hit ratio, latency), Redis INFO, CDN analytics, load testing, alerts | ~380 |

**Common workflows:**
- New caching layer: `caching-fundamentals.md` → `redis-caching-patterns.md` → `cache-invalidation-strategies.md`
- Full-stack caching: `service-worker-caching.md` (browser) → `http-caching.md` (HTTP) → `cdn-edge-caching.md` (CDN) → `redis-caching-patterns.md` (app)
- Optimization: `cache-performance-monitoring.md` → Identify bottlenecks → Apply appropriate caching skill
- CDN setup: `http-caching.md` → `cdn-edge-caching.md` → `cache-invalidation-strategies.md`

---

### Build Systems (8 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `make-fundamentals.md` | Makefile syntax, targets, dependencies, pattern rules, automatic variables, phony targets | ~420 |
| `cmake-patterns.md` | Modern CMake (3.20+, 4.0.2), target-based approach, find_package, FetchContent, generator expressions | ~450 |
| `gradle-jvm-builds.md` | Gradle Kotlin DSL, dependency management, version catalogs, build cache, multi-project builds | ~420 |
| `maven-configuration.md` | POM structure, dependency management, lifecycle phases, plugins, multi-module projects | ~400 |
| `bazel-monorepos.md` | BUILD files, hermetic builds, remote caching, Starlark rules, monorepo patterns | ~450 |
| `build-system-selection.md` | Decision matrix (Make/CMake/Gradle/Maven/Bazel), monorepo vs polyrepo, migration strategies | ~420 |
| `cross-platform-builds.md` | Platform detection, conditional compilation, CMake/Zig cross-compilation, toolchains | ~400 |
| `build-optimization.md` | Incremental builds, build caching (ccache, sccache), parallel builds, profiling | ~420 |

**Common workflows:**
- C/C++ project: `make-fundamentals.md` or `cmake-patterns.md` → `cross-platform-builds.md` → `build-optimization.md`
- Java project: `gradle-jvm-builds.md` or `maven-configuration.md` → `build-optimization.md`
- Monorepo: `bazel-monorepos.md` → `build-optimization.md`
- Choosing build system: `build-system-selection.md` → Selected system skill
- Optimize builds: `build-optimization.md` → Apply caching and parallel strategies

---

### Debugging (14 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `gdb-fundamentals.md` | C/C++ debugging, breakpoints, stack traces, variable inspection, GDB commands, TUI mode | ~440 |
| `lldb-macos-debugging.md` | macOS/iOS debugging, Swift/Obj-C debugging, LLDB vs GDB, Xcode integration, 50x faster step-over | ~420 |
| `python-debugging.md` | Python debugging (pdb, ipdb), VSCode/PyCharm, pytest debugging, remote debugging, profiling | ~400 |
| `browser-devtools.md` | Chrome/Firefox DevTools, Sources panel, performance profiling, memory analysis, React/Vue DevTools | ~450 |
| `remote-debugging.md` | SSH port forwarding, VSCode Remote, container debugging, Kubernetes debugging, symbol files | ~420 |
| `production-debugging.md` | Non-intrusive debugging, dynamic logging, feature flags, sampling profilers, observability correlation | ~430 |
| `memory-leak-debugging.md` | Heap profiling (Valgrind, AddressSanitizer, heaptrack), Python/Go/Rust memory debugging | ~440 |
| `concurrency-debugging.md` | Race detection (ThreadSanitizer), deadlock debugging, data races, lock ordering, Go race detector | ~430 |
| `core-dump-analysis.md` | Core dump generation, GDB/LLDB analysis, Python PyStack, automated crash reporting (Sentry) | ~420 |
| `crash-debugging.md` | Signal handling, crash reproduction, fuzzing (AFL, libFuzzer), crash telemetry | ~410 |
| `performance-profiling.md` | CPU profiling (perf, pprof, py-spy), flame graphs, sampling vs instrumentation, PGO | ~450 |
| `container-debugging.md` | Docker exec, kubectl debug, ephemeral containers, distroless debugging, sidecar patterns | ~410 |
| `network-debugging.md` | tcpdump, Wireshark, curl debugging, DNS tools (dig), network tracing (strace, dtrace, lsof) | ~420 |
| `distributed-systems-debugging.md` | Distributed tracing, cross-service debugging, request replay, traffic shadowing, chaos engineering | ~440 |

**Common workflows:**
- Debug C/C++ crash: `gdb-fundamentals.md` → `core-dump-analysis.md` → `crash-debugging.md`
- Debug Python app: `python-debugging.md` → `performance-profiling.md` → `memory-leak-debugging.md`
- Debug production: `production-debugging.md` → `distributed-systems-debugging.md` → Observability skills
- Debug memory issues: `memory-leak-debugging.md` → `performance-profiling.md`
- Debug concurrency: `concurrency-debugging.md` → `performance-profiling.md`
- Debug containers: `container-debugging.md` → `remote-debugging.md` → `network-debugging.md`
- Debug distributed system: `distributed-systems-debugging.md` → `network-debugging.md` → `production-debugging.md`

---

### Workflow & Task Management (6 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `beads-workflow.md` | Starting sessions, running bd commands, managing issue workflow | ~350 |
| `beads-dependency-management.md` | Creating issue relationships, managing blockers, organizing work hierarchies | ~450 |
| `beads-context-strategies.md` | Managing Claude context, preventing bloat, preserving workflow state | ~400 |
| `beads-multi-session-patterns.md` | Complex multi-session tasks, long-horizon work chains, parallel streams | ~350 |
| `typed-holes-refactor/SKILL.md` | Systematic codebase refactoring using Design by Typed Holes - iterative, test-driven with formal validation | ~350 |
| `skill-creation.md` | Creating new atomic skills, maintaining skills system, CLAUDE.md integration | ~400 |

**Common workflows:**
- New session: `beads-workflow.md` → `beads-context-strategies.md`
- Complex task: `beads-workflow.md` → `beads-dependency-management.md` → `beads-multi-session-patterns.md`
- Systematic refactoring: `typed-holes-refactor/SKILL.md` → Test-driven hole resolution → Constraint propagation
- Context management: `beads-context-strategies.md` (throughout session)
- Create new skill: `skill-creation.md` → Update _INDEX.md → Update CLAUDE.md

---

### Quality & Content Review (1 skill)

| Skill | Use When | Lines |
|-------|----------|-------|
| `anti-slop/SKILL.md` | Detecting/eliminating AI-generated patterns (slop) in text, code, design; content quality review; preventing generic outputs | ~420 |

**Common workflows:**
- Content review: Read `anti-slop/SKILL.md` → Run detection scripts → Apply cleanup → Manual review
- Code cleanup: Read `anti-slop/references/code-patterns.md` → Identify patterns → Refactor
- Design review: Read `anti-slop/references/design-patterns.md` → Audit against patterns → Recommendations

**Key features:**
- Automated text slop detection and cleanup scripts
- Comprehensive pattern catalogs for text, code, and design
- Quality principles for authentic, non-generic content
- Integration with development workflows

---

### Meta Skills (4 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `skill-repo-discovery.md` | Analyzing repository to find relevant skills, onboarding to new codebase | ~380 |
| `skill-repo-planning.md` | Identifying skill gaps in repository, planning new skills for missing tech | ~377 |
| `skill-prompt-discovery.md` | Analyzing user prompts to activate relevant skills, real-time skill selection | ~390 |
| `skill-prompt-planning.md` | Identifying skill gaps from conversation patterns, evolving skill catalog | ~380 |

**Common workflows:**
- New repository: `skill-repo-discovery.md` → Activate found skills → `skill-repo-planning.md` (if gaps exist)
- User request: `skill-prompt-discovery.md` → Activate skills → `skill-prompt-planning.md` (if gaps exist)
- Skill system evolution: Track patterns with `skill-prompt-planning.md` → `skill-creation.md`
- Complete analysis: `skill-repo-discovery.md` + `skill-repo-planning.md` → Gap report → Create skills

---

### iOS Development (6 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `swiftui-architecture.md` | Building SwiftUI views, MVVM patterns, state management | ~300 |
| `swift-concurrency.md` | Async/await, actors, Swift 6 concurrency safety | ~250 |
| `swiftdata-persistence.md` | Data persistence, models, queries, migrations | ~280 |
| `swiftui-navigation.md` | NavigationStack, type-safe routing, deep linking | ~220 |
| `ios-networking.md` | Network requests, URLSession patterns, async APIs | ~240 |
| `ios-testing.md` | Unit tests, UI tests, Swift Testing framework | ~210 |

**Common workflows:**
- New iOS app: `swiftui-architecture.md` → `swift-concurrency.md` → `swiftdata-persistence.md`
- Feature with API: `ios-networking.md` → `swiftui-architecture.md` → `swift-concurrency.md`
- Testing: `ios-testing.md` (after implementing features)

---

### Serverless & Cloud (6 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `modal-functions-basics.md` | Creating Modal apps, function decorators, basic patterns | ~280 |
| `modal-gpu-workloads.md` | ML inference, GPU selection, PyTorch workloads | ~320 |
| `modal-web-endpoints.md` | HTTP APIs, FastAPI integration, webhooks | ~260 |
| `modal-scheduling.md` | Cron jobs, scheduled tasks, automated workflows | ~190 |
| `modal-volumes-secrets.md` | Persistent storage, environment secrets, data management | ~240 |
| `modal-image-building.md` | Container images, dependencies, uv_pip_install | ~270 |

**Common workflows:**
- New Modal app: `modal-functions-basics.md` → `modal-image-building.md`
- ML deployment: `modal-gpu-workloads.md` → `modal-functions-basics.md` → `modal-volumes-secrets.md`
- API service: `modal-web-endpoints.md` → `modal-functions-basics.md` → `modal-scheduling.md`

---

### Networking & Security (5 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `tailscale-vpn.md` | Setting up mesh VPN, private network access, WireGuard | ~250 |
| `mtls-implementation.md` | Mutual TLS, service-to-service auth, certificate management | ~300 |
| `mosh-resilient-ssh.md` | Resilient SSH alternative, IP roaming, unstable connections | ~180 |
| `nat-traversal.md` | P2P connections, STUN/TURN, UDP hole punching | ~270 |
| `network-resilience-patterns.md` | Retry logic, circuit breakers, timeouts, connection pooling | ~290 |

**Common workflows:**
- Secure private network: `tailscale-vpn.md`
- Service mesh: `mtls-implementation.md` → `network-resilience-patterns.md`
- Remote development: `mosh-resilient-ssh.md` or `tailscale-vpn.md`
- P2P application: `nat-traversal.md` → `network-resilience-patterns.md`

---

### Terminal UI Development (5 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `bubbletea-architecture.md` | Building TUI apps in Go, Elm architecture, Bubble Tea | ~320 |
| `bubbletea-components.md` | Bubbles widgets, Lip Gloss styling, pre-built components | ~280 |
| `ratatui-architecture.md` | Building TUI apps in Rust, immediate-mode rendering | ~290 |
| `ratatui-widgets.md` | Ratatui layouts, tables, lists, styling | ~260 |
| `tui-best-practices.md` | Keybindings, performance, cross-platform compatibility | ~240 |

**Common workflows:**
- Go TUI: `bubbletea-architecture.md` → `bubbletea-components.md` → `tui-best-practices.md`
- Rust TUI: `ratatui-architecture.md` → `ratatui-widgets.md` → `tui-best-practices.md`

---

### Systems Programming - Zig (6 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `zig-project-setup.md` | Initializing Zig projects, project structure | ~200 |
| `zig-build-system.md` | build.zig configuration, cross-compilation, build modes | ~310 |
| `zig-testing.md` | Writing tests, test organization, running test suites | ~220 |
| `zig-package-management.md` | build.zig.zon, dependencies, zig fetch | ~250 |
| `zig-memory-management.md` | Allocators, defer/errdefer, memory safety patterns | ~280 |
| `zig-c-interop.md` | Linking C libraries, @cImport, calling C code | ~230 |

**Common workflows:**
- New Zig project: `zig-project-setup.md` → `zig-build-system.md` → `zig-testing.md`
- Adding dependencies: `zig-package-management.md` → `zig-build-system.md`
- C integration: `zig-c-interop.md` → `zig-build-system.md`
- Memory-intensive work: `zig-memory-management.md`

---

### CI/CD Skills (5 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `github-actions-workflows.md` | Writing GitHub Actions workflows, CI/CD pipelines, automation | ~300 |
| `ci-testing-strategy.md` | Test automation in CI, parallel execution, test splitting | ~280 |
| `cd-deployment-patterns.md` | Blue-green, canary, rolling deployments, rollback strategies | ~290 |
| `ci-optimization.md` | Pipeline speed optimization, caching, incremental builds | ~250 |
| `ci-security.md` | Secret management, OIDC, supply chain security, SBOM | ~270 |

**Common workflows:**
- New CI/CD pipeline: `github-actions-workflows.md` → `ci-testing-strategy.md` → `cd-deployment-patterns.md`
- Optimize existing pipeline: `ci-optimization.md` → `ci-security.md`
- Secure pipeline: `ci-security.md` → `github-actions-workflows.md`

---

### Infrastructure Skills (6 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `terraform-patterns.md` | Infrastructure as Code, modules, state management, workspaces | ~310 |
| `aws-serverless.md` | Lambda, API Gateway, DynamoDB, S3, EventBridge, Step Functions | ~330 |
| `kubernetes-basics.md` | Pods, Deployments, Services, ConfigMaps, Secrets, Ingress | ~320 |
| `cloudflare-workers.md` | Edge computing, KV storage, Durable Objects, R2 | ~280 |
| `infrastructure-security.md` | IAM, security groups, secrets management, encryption | ~290 |
| `cost-optimization.md` | Resource right-sizing, reserved instances, spot instances | ~260 |

**Common workflows:**
- New infrastructure: `terraform-patterns.md` → `infrastructure-security.md` → `cost-optimization.md`
- Serverless app: `aws-serverless.md` or `cloudflare-workers.md`
- Kubernetes deployment: `kubernetes-basics.md` → `infrastructure-security.md`

---

### Observability Skills (8 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `structured-logging.md` | JSON logging, log levels, correlation IDs, log aggregation | ~270 |
| `metrics-instrumentation.md` | Prometheus, StatsD, custom metrics, cardinality, histograms | ~290 |
| `distributed-tracing.md` | OpenTelemetry, spans, trace context, sampling | ~280 |
| `alerting-strategy.md` | Alert conditions, severity levels, on-call, alert fatigue | ~250 |
| `dashboard-design.md` | Grafana, visualization types, SLO dashboards, troubleshooting | ~260 |
| `opentelemetry-integration.md` | OTel Collector, auto-instrumentation, traces/metrics/logs correlation, backend integrations (Grafana/Datadog/New Relic) | ~460 |
| `observability-cost-optimization.md` | Cardinality management, sampling strategies, log reduction, metrics aggregation, OTel cost reduction | ~420 |
| `production-incident-debugging.md` | Incident triage (logs→metrics→traces), RCA with observability, time-travel debugging, runbooks, postmortems | ~440 |

**Common workflows:**
- Full observability stack: `opentelemetry-integration.md` → `structured-logging.md` → `metrics-instrumentation.md` → `distributed-tracing.md`
- Monitoring setup: `metrics-instrumentation.md` → `alerting-strategy.md` → `dashboard-design.md`
- Incident response: `production-incident-debugging.md` → `distributed-tracing.md` → `structured-logging.md`
- Cost optimization: `observability-cost-optimization.md` → Optimize sampling/cardinality → Monitor with `dashboard-design.md`
- OTel adoption: `opentelemetry-integration.md` → `distributed-tracing.md` → `metrics-instrumentation.md`

---

### Real-time Communication Skills (4 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `websocket-implementation.md` | WebSocket protocol, connection management, reconnection, heartbeat | ~300 |
| `server-sent-events.md` | SSE protocol, event streams, reconnection, fallback | ~260 |
| `realtime-sync.md` | Conflict resolution, CRDTs, operational transformation | ~290 |
| `pubsub-patterns.md` | Pub/sub architecture, Redis Pub/Sub, message queues, fan-out | ~270 |

**Common workflows:**
- Real-time features: `websocket-implementation.md` or `server-sent-events.md`
- Chat/collaboration: `websocket-implementation.md` → `realtime-sync.md` → `pubsub-patterns.md`
- Event streaming: `server-sent-events.md` → `pubsub-patterns.md`

---

### Data Pipeline Skills (5 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `etl-patterns.md` | Extract-Transform-Load, data sources, transformations, incremental processing | ~300 |
| `stream-processing.md` | Kafka, event streaming, windowing, stateful processing | ~310 |
| `batch-processing.md` | Airflow, DAGs, scheduling, dependency management, backfills | ~290 |
| `data-validation.md` | Schema validation, data quality checks, anomaly detection | ~260 |
| `pipeline-orchestration.md` | Workflow engines, error handling, retries, monitoring | ~280 |

**Common workflows:**
- ETL pipeline: `etl-patterns.md` → `data-validation.md` → `pipeline-orchestration.md`
- Stream processing: `stream-processing.md` → `data-validation.md`
- Batch jobs: `batch-processing.md` → `pipeline-orchestration.md`
- Data quality: `data-validation.md` → `pipeline-orchestration.md`

---

### SAT/SMT Solvers (3 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `z3-solver-basics.md` | Using Z3 SMT solver, constraint solving, program verification | ~350 |
| `sat-solving-strategies.md` | Boolean satisfiability, combinatorial problems, SAT encodings | ~320 |
| `smt-theory-applications.md` | SMT theories, model checking, test generation, scheduling | ~340 |

**Common workflows:**
- Constraint solving: `z3-solver-basics.md` → `smt-theory-applications.md`
- SAT problems: `sat-solving-strategies.md` → `z3-solver-basics.md`
- Formal verification: `smt-theory-applications.md` → `lean-theorem-proving.md`

---

### Lean 4 Theorem Proving (4 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `lean-proof-basics.md` | Learning Lean 4, writing simple proofs, understanding proof terms | ~330 |
| `lean-tactics.md` | Complex proofs, tactic development, proof automation | ~360 |
| `lean-mathlib4.md` | Mathematical formalization, using mathlib4, library development | ~350 |
| `lean-theorem-proving.md` | Advanced proving techniques, formalization strategies, research | ~370 |

**Common workflows:**
- Learning Lean: `lean-proof-basics.md` → `lean-tactics.md` → `lean-mathlib4.md`
- Formalization project: `lean-mathlib4.md` → `lean-theorem-proving.md`
- Proof automation: `lean-tactics.md` → `lean-theorem-proving.md`

---

### Modal.com Troubleshooting (2 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `modal-common-errors.md` | Debugging Modal apps, deployment issues, error resolution | ~504 |
| `modal-performance-debugging.md` | Performance issues, profiling, GPU optimization, cold starts | ~639 |

**Common workflows:**
- Debugging errors: `modal-common-errors.md` → `modal-debugging.md`
- Performance optimization: `modal-performance-debugging.md` → `modal-optimization.md`
- Production issues: `modal-common-errors.md` → `modal-performance-debugging.md`

---

### Heroku Deployment (3 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `heroku-deployment.md` | Deploying apps to Heroku, Procfile, buildpacks, pipelines | ~330 |
| `heroku-addons.md` | Adding Postgres, Redis, monitoring, email services | ~310 |
| `heroku-troubleshooting.md` | Debugging Heroku apps, logs, performance, scaling | ~320 |

**Common workflows:**
- New Heroku app: `heroku-deployment.md` → `heroku-addons.md`
- Production setup: `heroku-deployment.md` → `heroku-addons.md` → `heroku-troubleshooting.md`
- Debugging: `heroku-troubleshooting.md` → `structured-logging.md`

---

### Netlify Deployment (3 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `netlify-deployment.md` | Deploying static sites, JAMstack, Next.js to Netlify | ~320 |
| `netlify-functions.md` | Serverless functions, Edge Functions, form handling | ~330 |
| `netlify-optimization.md` | Performance optimization, CDN, caching, build optimization | ~310 |

**Common workflows:**
- New Netlify site: `netlify-deployment.md` → `netlify-optimization.md`
- Adding API: `netlify-functions.md` → `netlify-deployment.md`
- Production optimization: `netlify-deployment.md` → `netlify-optimization.md` → `frontend-performance.md`

---

### LLM Fine-tuning (4 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `unsloth-finetuning.md` | Fast LLM fine-tuning, memory optimization, multi-GPU | ~350 |
| `huggingface-autotrain.md` | No-code/low-code fine-tuning, quick experiments | ~330 |
| `llm-dataset-preparation.md` | Preparing training data, instruction tuning, chat fine-tuning | ~360 |
| `lora-peft-techniques.md` | LoRA, QLoRA, parameter-efficient fine-tuning | ~340 |

**Common workflows:**
- Fine-tuning workflow: `llm-dataset-preparation.md` → `unsloth-finetuning.md` → `lora-peft-techniques.md`
- Quick fine-tuning: `llm-dataset-preparation.md` → `huggingface-autotrain.md`
- Production deployment: `unsloth-finetuning.md` → `modal-gpu-workloads.md`

---

### DSPy Framework (7 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `dspy-setup.md` | Installing DSPy, configuring LMs (OpenAI, Anthropic, Modal, HuggingFace), environment setup | ~530 |
| `dspy-signatures.md` | Defining input/output signatures, typed fields, class-based signatures | ~464 |
| `dspy-modules.md` | Building Predict, ChainOfThought, ReAct modules, custom modules, composition | ~530 |
| `dspy-optimizers.md` | Optimizing with BootstrapFewShot, MIPROv2, COPRO, teleprompters, compilation | ~546 |
| `dspy-evaluation.md` | Metrics, Evaluate class, A/B testing, error analysis, performance measurement | ~526 |
| `dspy-rag.md` | Building RAG pipelines, vector databases (ChromaDB, Weaviate), retrieval optimization | ~641 |
| `dspy-assertions.md` | Adding constraints, validation, dspy.Assert, dspy.Suggest, retry logic | ~612 |

**Common workflows:**
- Getting started: `dspy-setup.md` → `dspy-signatures.md` → `dspy-modules.md`
- Building QA system: `dspy-signatures.md` → `dspy-modules.md` → `dspy-optimizers.md` → `dspy-evaluation.md`
- RAG pipeline: `dspy-setup.md` → `dspy-rag.md` → `dspy-optimizers.md` → `dspy-evaluation.md`
- Production system: `dspy-modules.md` → `dspy-assertions.md` → `dspy-evaluation.md` → `dspy-optimizers.md`
- Modal deployment: `dspy-setup.md` (Pattern 6: Modal + HuggingFace) → `dspy-rag.md` → `modal-gpu-workloads.md`

---

### Machine Learning - LLM Evaluation & Routing (8 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `ml/llm-benchmarks-evaluation.md` | MMLU, HellaSwag, BBH, HumanEval benchmarks; lm-evaluation-harness, LightEval | ~724 |
| `ml/llm-evaluation-frameworks.md` | Arize Phoenix (OpenTelemetry), Braintrust, LangSmith, Langfuse observability | ~921 |
| `ml/llm-as-judge.md` | Pairwise/pointwise/reference-guided eval; Prometheus 2, G-Eval, bias mitigation | ~1089 |
| `ml/rag-evaluation-metrics.md` | RAGAS metrics (Faithfulness, Answer Relevancy, Context Precision/Recall) | ~969 |
| `ml/custom-llm-evaluation.md` | Domain-specific metrics, RLHF, adversarial testing, bias evaluation | ~1053 |
| `ml/llm-model-routing.md` | RouteLLM, RoRF, semantic routing; GPT-4o vs Claude vs Gemini routing | ~562 |
| `ml/llm-model-selection.md` | 2025 model comparison, capability matrix, strategic stack approach | ~551 |
| `ml/multi-model-orchestration.md` | Pipeline/ensemble/cascade patterns, Arize Phoenix multi-model tracing | ~721 |

**Common workflows:**
- Evaluation setup: `llm-benchmarks-evaluation.md` → `llm-evaluation-frameworks.md` (Arize Phoenix)
- RAG evaluation: `rag-evaluation-metrics.md` → `llm-as-judge.md` → `llm-evaluation-frameworks.md`
- Custom evaluation: `custom-llm-evaluation.md` → `llm-as-judge.md` (Prometheus 2) → `llm-evaluation-frameworks.md`
- Model routing: `llm-model-selection.md` → `llm-model-routing.md` → `multi-model-orchestration.md`
- Cost optimization: `llm-model-selection.md` (pricing) → `llm-model-routing.md` (85% reduction)

---

### Machine Learning - Advanced RAG (4 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `ml/hybrid-search-rag.md` | Vector + BM25 fusion, RRF, Elasticsearch/Weaviate/Qdrant/Pinecone | ~656 |
| `ml/rag-reranking-techniques.md` | Cross-encoder, tensor-based, LLM-as-reranker; Cohere/BGE/ms-marco | ~623 |
| `ml/graph-rag.md` | Microsoft GraphRAG, entity extraction, community detection, multihop reasoning | ~696 |
| `ml/hierarchical-rag.md` | Multi-level structures, recursive summarization, parent-child chunks | ~694 |

**Common workflows:**
- Hybrid RAG: `dspy-rag.md` → `hybrid-search-rag.md` → `rag-reranking-techniques.md`
- Advanced RAG pipeline: `hybrid-search-rag.md` → `rag-reranking-techniques.md` → `rag-evaluation-metrics.md`
- GraphRAG: `graph-rag.md` → `llm-as-judge.md` (quality eval) → `rag-evaluation-metrics.md`
- Hierarchical docs: `hierarchical-rag.md` → `rag-reranking-techniques.md` → `rag-evaluation-metrics.md`

---

### Diffusion Models (3 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `diffusion-model-basics.md` | Understanding diffusion models, image generation, model selection | ~445 |
| `stable-diffusion-deployment.md` | Deploying Stable Diffusion, optimization, inference APIs | ~596 |
| `diffusion-finetuning.md` | Fine-tuning diffusion models, DreamBooth, LoRA | ~598 |

**Common workflows:**
- Learning diffusion: `diffusion-model-basics.md` → `stable-diffusion-deployment.md`
- Production API: `stable-diffusion-deployment.md` → `modal-gpu-workloads.md`
- Custom models: `diffusion-finetuning.md` → `stable-diffusion-deployment.md`

---

### Constraint Satisfaction (3 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `csp-modeling.md` | Modeling CSPs, scheduling, planning, resource allocation | ~423 |
| `constraint-propagation.md` | Constraint propagation, arc consistency, domain reduction | ~514 |
| `backtracking-search.md` | Backtracking search, heuristics, CSP optimization | ~466 |

**Common workflows:**
- CSP solving: `csp-modeling.md` → `constraint-propagation.md` → `backtracking-search.md`
- Optimization: `csp-modeling.md` → `backtracking-search.md`
- Scheduling problems: `csp-modeling.md` → `constraint-propagation.md`

---

### Advanced Mathematics (19 skills)

**Numerical & Applied:**

| Skill | Use When | Lines |
|-------|----------|-------|
| `linear-algebra-computation.md` | Matrix computations, solving linear systems, dimensionality reduction | ~350 |
| `optimization-algorithms.md` | Numerical optimization, gradient descent, constrained optimization | ~360 |
| `numerical-methods.md` | Solving ODEs/PDEs, numerical integration, root finding | ~340 |
| `probability-statistics.md` | Statistical analysis, hypothesis testing, Bayesian methods | ~330 |

**Pure Mathematics:**

| Skill | Use When | Lines |
|-------|----------|-------|
| `topology-point-set.md` | General topology, metric spaces, continuity, compactness, separation axioms | ~400 |
| `topology-algebraic.md` | Fundamental groups, homology, homotopy theory, persistent homology (TDA) | ~420 |
| `category-theory-foundations.md` | Categories, functors, natural transformations, adjunctions, monads | ~450 |
| `differential-equations.md` | ODEs, PDEs, analytical/numerical methods, phase plane analysis | ~400 |
| `abstract-algebra.md` | Groups, rings, fields, Galois theory, homomorphisms | ~420 |
| `set-theory.md` | ZFC axioms, ordinals, cardinals, axiom of choice, forcing | ~380 |
| `number-theory.md` | Primes, modular arithmetic, Diophantine equations, RSA cryptography | ~400 |

**Graph Theory:**

| Skill | Use When | Lines |
|-------|----------|-------|
| `graph/graph-theory-fundamentals.md` | Core graph concepts, graph types, properties, theorems (Handshaking, Euler, Kuratowski) | ~400 |
| `graph/graph-data-structures.md` | Adjacency matrix/list, edge lists, CSR, space-time tradeoffs | ~420 |
| `graph/graph-traversal-algorithms.md` | BFS, DFS, topological sort, strongly connected components, cycle detection | ~400 |
| `graph/shortest-path-algorithms.md` | Dijkstra, Bellman-Ford, Floyd-Warshall, A* pathfinding | ~450 |
| `graph/minimum-spanning-tree.md` | Kruskal, Prim, union-find, MST applications | ~380 |
| `graph/network-flow-algorithms.md` | Ford-Fulkerson, Edmonds-Karp, max flow, min cut, bipartite matching | ~420 |
| `graph/advanced-graph-algorithms.md` | Graph coloring, clique finding, vertex cover, matching (Blossom) | ~420 |
| `graph/graph-applications.md` | Social networks, routing, dependency resolution, recommendations | ~400 |

**Common workflows:**
- ML foundations: `linear-algebra-computation.md` → `optimization-algorithms.md`
- Scientific computing: `numerical-methods.md` → `differential-equations.md` → `optimization-algorithms.md`
- Data analysis: `probability-statistics.md` → `data-validation.md`
- Topology foundations: `topology-point-set.md` → `topology-algebraic.md`
- Abstract algebra: `set-theory.md` → `abstract-algebra.md` → `number-theory.md`
- Category theory: `category-theory-foundations.md` → `abstract-algebra.md` (categorical algebra)
- Graph algorithms: `graph/graph-theory-fundamentals.md` → `graph/graph-data-structures.md` → `graph/graph-traversal-algorithms.md`
- Shortest paths: `graph/graph-theory-fundamentals.md` → `graph/shortest-path-algorithms.md` → `graph/graph-applications.md`
- Network optimization: `graph/minimum-spanning-tree.md` → `graph/network-flow-algorithms.md` → `graph/advanced-graph-algorithms.md`
- Real-world graphs: `graph/graph-traversal-algorithms.md` → `graph/shortest-path-algorithms.md` → `graph/graph-applications.md`

---

### Programming Language Theory (13 skills)

**Core PLT:**

| Skill | Use When | Lines |
|-------|----------|-------|
| `lambda-calculus.md` | Understanding λ-calculus, Church encodings, β-reduction, combinators | ~420 |
| `type-systems.md` | Type checking, inference, polymorphism, subtyping, soundness | ~450 |
| `dependent-types.md` | Π-types, Σ-types, indexed families, proof assistants (Lean, Coq, Agda) | ~400 |
| `curry-howard.md` | Propositions as types, proofs as programs, extracting verified code | ~380 |
| `operational-semantics.md` | Small-step/big-step semantics, evaluation strategies, reduction systems | ~420 |
| `program-verification.md` | Hoare logic, SMT-based verification, refinement types, separation logic | ~400 |

**Typed Holes & Live Programming:**

| Skill | Use When | Lines |
|-------|----------|-------|
| `typed-holes-foundations.md` | Typed holes basics, gradual typing, bidirectional typing, hole semantics | ~400 |
| `hazelnut-calculus.md` | Structure editor calculus, edit actions, zipper navigation, Grove | ~420 |
| `typed-holes-semantics.md` | Advanced hole semantics: closures, pattern matching, error localization, polymorphism | ~400 |
| `typed-holes-interaction.md` | IDE integration, goal-directed programming, tactics, proof search, elaborator reflection | ~380 |
| `live-programming-holes.md` | Hazel environment, live evaluation, incremental typing (OOPSLA 2025), collaboration | ~420 |
| `structure-editors.md` | Structure editor design, projectional editing, rendering, text integration | ~400 |
| `typed-holes-llm.md` | LLM + typed holes (OOPSLA 2024), static context, validation, ranking, AI pair programming | ~450 |

**Common workflows:**
- PL foundations: `lambda-calculus.md` → `type-systems.md` → `operational-semantics.md`
- Dependent types: `type-systems.md` → `dependent-types.md` → `curry-howard.md`
- Formal verification: `operational-semantics.md` → `program-verification.md` → `formal/lean-proof-basics.md`
- Type theory: `lambda-calculus.md` → `type-systems.md` → `dependent-types.md` → `curry-howard.md`
- Typed holes theory: `typed-holes-foundations.md` → `hazelnut-calculus.md` → `typed-holes-semantics.md`
- Typed holes practice: `typed-holes-interaction.md` → `live-programming-holes.md` → `structure-editors.md`
- AI-assisted coding: `typed-holes-foundations.md` → `typed-holes-llm.md` → Implement LSP+LLM integration

---

### React Native iOS (4 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `react-native-setup.md` | Starting React Native projects, iOS development environment | ~320 |
| `react-native-navigation.md` | Multi-screen apps, navigation patterns, deep linking | ~340 |
| `react-native-native-modules.md` | Accessing iOS APIs, native functionality, Swift bridging | ~350 |
| `react-native-performance.md` | Performance optimization, iOS-specific optimizations | ~360 |

**Common workflows:**
- New React Native app: `react-native-setup.md` → `react-native-navigation.md` → `react-native-performance.md`
- Native integration: `react-native-native-modules.md` → `swift-concurrency.md`
- Production app: `react-native-navigation.md` → `react-native-performance.md` → `ios-testing.md`

---

### Cloud Platforms - AWS (7 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `cloud/aws/aws-lambda-functions.md` | Lambda basics, layers, triggers, runtime config, cold starts | ~658 |
| `cloud/aws/aws-api-gateway.md` | REST/HTTP/WebSocket APIs, authorization, throttling, integrations | ~599 |
| `cloud/aws/aws-ec2-compute.md` | EC2 instances, Auto Scaling, Load Balancing, AMIs | ~668 |
| `cloud/aws/aws-storage.md` | S3, EBS, EFS, Glacier, lifecycle policies | ~610 |
| `cloud/aws/aws-databases.md` | RDS, DynamoDB, ElastiCache, Aurora, backup strategies | ~694 |
| `cloud/aws/aws-networking.md` | VPC, security groups, Route53, CloudFront, Transit Gateway | ~702 |
| `cloud/aws/aws-iam-security.md` | IAM policies/roles, Cognito, Secrets Manager, KMS encryption | ~754 |

**Common workflows:**
- Serverless API: `aws-lambda-functions.md` → `aws-api-gateway.md` → `aws-iam-security.md`
- Web application: `aws-ec2-compute.md` → `aws-databases.md` → `aws-networking.md`
- Secure infrastructure: `aws-networking.md` → `aws-iam-security.md` → `infrastructure/aws-serverless.md`

---

### Cloud Platforms - GCP (6 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `cloud/gcp/gcp-compute.md` | Compute Engine, Cloud Run, GKE, instance groups, preemptible VMs | ~484 |
| `cloud/gcp/gcp-storage.md` | Cloud Storage, Persistent Disk, Filestore, lifecycle management | ~478 |
| `cloud/gcp/gcp-databases.md` | Cloud SQL, Firestore, Bigtable, Spanner, Memorystore | ~602 |
| `cloud/gcp/gcp-networking.md` | VPC, firewall rules, Cloud DNS, Cloud CDN, Load Balancing | ~584 |
| `cloud/gcp/gcp-iam-security.md` | IAM roles/policies, service accounts, Secret Manager, Cloud KMS | ~634 |
| `cloud/gcp/gcp-serverless.md` | Cloud Functions, Cloud Run, App Engine comparison, Eventarc | ~664 |

**Common workflows:**
- Serverless app: `gcp-serverless.md` → `gcp-iam-security.md` → `gcp-databases.md`
- Containerized app: `gcp-compute.md` (Cloud Run/GKE) → `gcp-networking.md` → `gcp-storage.md`
- Secure infrastructure: `gcp-networking.md` → `gcp-iam-security.md` → `infrastructure/cost-optimization.md`

---

### Collaboration - GitHub (5 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `collaboration/github/github-repository-management.md` | Repos, branches, tags, releases, GitHub CLI, templates | ~538 |
| `collaboration/github/github-pull-requests.md` | PR workflow, code review, merge strategies, auto-merge | ~639 |
| `collaboration/github/github-issues-projects.md` | Issue tracking, labels, milestones, project boards | ~677 |
| `collaboration/github/github-security-features.md` | Dependabot, code scanning, secret scanning, SBOM | ~809 |
| `collaboration/github/github-actions-workflows.md` | CI/CD workflows, triggers, jobs, matrix builds, caching | ~684 |

**Common workflows:**
- New project setup: `github-repository-management.md` → `github-actions-workflows.md` → `github-security-features.md`
- PR workflow: `github-pull-requests.md` → `github-issues-projects.md`
- Security hardening: `github-security-features.md` → `cicd/ci-security.md`

---

### Machine Learning - HuggingFace (5 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `ml/huggingface/huggingface-hub.md` | Model/dataset repos, Hub API, model cards, Spaces | ~518 |
| `ml/huggingface/huggingface-transformers.md` | Loading models, pipelines, inference, tokenizers, quantization | ~564 |
| `ml/huggingface/huggingface-datasets.md` | Loading datasets, preprocessing, streaming, custom datasets | ~595 |
| `ml/huggingface/huggingface-spaces.md` | Gradio/Streamlit apps, Space config, GPU hardware, secrets | ~584 |
| `ml/huggingface/huggingface-autotrain.md` | No-code/low-code fine-tuning, quick experiments | ~510 |

**Common workflows:**
- Model inference: `huggingface-hub.md` → `huggingface-transformers.md` → `modal-gpu-workloads.md`
- Dataset prep: `huggingface-datasets.md` → `llm-dataset-preparation.md` → `unsloth-finetuning.md`
- Demo app: `huggingface-transformers.md` → `huggingface-spaces.md`

---

### Information Retrieval (5 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `ir/ir-search-fundamentals.md` | TF-IDF, BM25, inverted indexes, Elasticsearch/OpenSearch | ~640 |
| `ir/ir-vector-search.md` | Embeddings, dense retrieval, vector DBs (Pinecone, Weaviate, Qdrant) | ~676 |
| `ir/ir-ranking-reranking.md` | Learning to rank, cross-encoders, reranking pipelines, nDCG/MAP | ~627 |
| `ir/ir-recommendation-systems.md` | Collaborative filtering, content-based, hybrid, matrix factorization | ~649 |
| `ir/ir-query-understanding.md` | Query expansion, spell correction, semantic search, autocomplete | ~666 |

**Common workflows:**
- Search system: `ir-search-fundamentals.md` → `ir-vector-search.md` → `ir-ranking-reranking.md`
- Hybrid search: `ir-search-fundamentals.md` + `ir-vector-search.md` → `ir-ranking-reranking.md`
- Recommendations: `ir-recommendation-systems.md` → `ir-ranking-reranking.md`
- Query processing: `ir-query-understanding.md` → `ir-search-fundamentals.md`

---

### Systems Programming - WebAssembly (4 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `wasm/wasm-fundamentals.md` | WebAssembly basics, WAT, binary format, WASI, use cases | ~421 |
| `wasm/wasm-rust-toolchain.md` | Rust→wasm, wasm-pack, wasm-bindgen, optimization | ~566 |
| `wasm/wasm-browser-integration.md` | Loading wasm, JS interop, DOM access, WebGL, Web Workers | ~657 |
| `wasm/wasm-server-side.md` | Wasmtime, WASI, edge compute (Cloudflare/Fastly), plugins | ~565 |

**Common workflows:**
- Browser wasm: `wasm-fundamentals.md` → `wasm-rust-toolchain.md` → `wasm-browser-integration.md`
- Server wasm: `wasm-fundamentals.md` → `wasm-server-side.md`
- Edge computing: `wasm-rust-toolchain.md` → `wasm-server-side.md` → `infrastructure/cloudflare-workers.md`

---

### Systems Programming - eBPF (4 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `ebpf/ebpf-fundamentals.md` | eBPF architecture, verifier, maps, programs, BCC vs libbpf | ~555 |
| `ebpf/ebpf-tracing-observability.md` | bpftrace, kprobes, uprobes, tracepoints, latency analysis | ~590 |
| `ebpf/ebpf-networking.md` | XDP, TC, socket filters, load balancing, Cilium, packet processing | ~701 |
| `ebpf/ebpf-security-monitoring.md` | Syscall tracking, Falco, Tetragon, runtime security, threat detection | ~690 |

**Common workflows:**
- Performance tracing: `ebpf-fundamentals.md` → `ebpf-tracing-observability.md`
- Network optimization: `ebpf-fundamentals.md` → `ebpf-networking.md`
- Security monitoring: `ebpf-fundamentals.md` → `ebpf-security-monitoring.md`
- Kubernetes observability: `ebpf-networking.md` + `ebpf-security-monitoring.md`

---

### Product Management - PRD (4 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `product/prd-structure-templates.md` | PRD format, sections, templates, stakeholder approval | ~468 |
| `product/prd-requirements-gathering.md` | User interviews, research synthesis, RICE/MoSCoW prioritization | ~466 |
| `product/prd-user-stories-acceptance.md` | Epics, user stories, acceptance criteria, story mapping | ~560 |
| `product/prd-technical-specifications.md` | API specs, data models, architecture diagrams, constraints | ~675 |

**Common workflows:**
- New feature PRD: `prd-requirements-gathering.md` → `prd-structure-templates.md` → `prd-user-stories-acceptance.md`
- Technical PRD: `prd-structure-templates.md` → `prd-technical-specifications.md`
- Full PRD: All 4 skills in sequence

---

### Engineering Process - RFC (4 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `engineering/rfc-structure-format.md` | RFC format, templates, ADRs, DACI framework, documentation | ~621 |
| `engineering/rfc-technical-design.md` | Architecture proposals, trade-offs, diagrams, API design | ~745 |
| `engineering/rfc-consensus-building.md` | Stakeholder engagement, feedback integration, approval process | ~544 |
| `engineering/rfc-decision-documentation.md` | ADRs, decision rationale, status tracking, post-implementation review | ~655 |

**Common workflows:**
- Architecture RFC: `rfc-structure-format.md` → `rfc-technical-design.md` → `rfc-consensus-building.md`
- Decision record: `rfc-decision-documentation.md`
- Full RFC process: All 4 skills in sequence

---

## Skill Discovery Patterns

### By Technology

**API Design:** Search `api-*.md`, `rest-*.md`, `graphql-*.md`
**Testing:** Search `test-*.md`, `unit-*.md`, `integration-*.md`, `e2e-*.md`, `performance-*.md`
**Containers/Docker:** Search `docker-*.md`, `container-*.md`, `dockerfile-*.md`
**Frontend/React:** Search `react-*.md`, `nextjs-*.md`, `web-*.md`, `frontend-*.md` | `elegant-design/` for UI/UX design systems
**Database/PostgreSQL:** Search `postgres-*.md`, `database-*.md`, `mongodb-*.md`, `redis-*.md`, `orm-*.md`
**Caching:** Search `caching/*.md`, `cache-*.md`
**Build Systems:** Search `build-systems/*.md`, `make-*.md`, `cmake-*.md`, `gradle-*.md`, `maven-*.md`, `bazel-*.md`
**Debugging:** Search `debugging/*.md`, `gdb-*.md`, `lldb-*.md`, `debug-*.md`, `profiling-*.md`, `memory-*.md`, `concurrency-*.md`
**Swift/SwiftUI:** Search `swiftui-*.md`, `swift-*.md`, `ios-*.md`
**Modal.com:** Search `modal-*.md`
**Networking:** Search `network-*.md`, `mtls-*.md`, `tailscale-*.md`, `nat-*.md`, `mosh-*.md`
**TUI (Go):** Search `bubbletea-*.md`, `tui-*.md`
**TUI (Rust):** Search `ratatui-*.md`, `tui-*.md`
**Zig:** Search `zig-*.md`
**Beads:** Search `beads-*.md`
**Refactoring:** `typed-holes-refactor/SKILL.md` (systematic TDD refactoring)
**Quality & Content:** `anti-slop/SKILL.md`, `anti-slop/references/*.md`
**Meta Skills:** Search `skill-*.md`
**CI/CD:** Search `cicd/*.md`, `github-*.md`, `ci-*.md`, `cd-*.md`
**Infrastructure:** Search `infrastructure/*.md`, `terraform-*.md`, `aws-*.md`, `kubernetes-*.md`, `cloudflare-*.md`
**Observability:** Search `observability/*.md`, `logging-*.md`, `metrics-*.md`, `tracing-*.md`, `alerting-*.md`
**Real-time:** Search `realtime/*.md`, `websocket-*.md`, `sse-*.md`, `pubsub-*.md`
**Data Pipelines:** Search `data/*.md`, `etl-*.md`, `stream-*.md`, `batch-*.md`, `pipeline-*.md`
**SAT/SMT Solvers:** Search `formal/z3-*.md`, `formal/sat-*.md`, `formal/smt-*.md`
**Lean 4:** Search `formal/lean-*.md`
**Constraint Satisfaction:** Search `formal/csp-*.md`, `formal/constraint-*.md`, `formal/backtracking-*.md`
**Heroku:** Search `deployment/heroku-*.md`
**Netlify:** Search `deployment/netlify-*.md`
**LLM Fine-tuning:** Search `ml/unsloth-*.md`, `ml/huggingface-*.md`, `ml/llm-*.md`, `ml/lora-*.md`
**LLM Evaluation:** Search `ml/llm-benchmarks-*.md`, `ml/llm-evaluation-*.md`, `ml/llm-as-judge.md`, `ml/rag-evaluation-*.md`, `ml/custom-llm-*.md`
**LLM Routing:** Search `ml/llm-model-routing.md`, `ml/llm-model-selection.md`, `ml/multi-model-*.md`
**Advanced RAG:** Search `ml/hybrid-search-*.md`, `ml/rag-reranking-*.md`, `ml/graph-rag.md`, `ml/hierarchical-rag.md`
**DSPy Framework:** Search `ml/dspy-*.md`
**Diffusion Models:** Search `ml/diffusion-*.md`, `ml/stable-diffusion-*.md`
**Advanced Mathematics:** Search `math/*.md`, `math/graph/*.md` | Numerical: `math/linear-algebra-*.md`, `math/optimization-*.md`, `math/numerical-*.md`, `math/probability-*.md` | Pure math: `math/topology-*.md`, `math/category-theory-*.md`, `math/differential-equations.md`, `math/abstract-algebra.md`, `math/set-theory.md`, `math/number-theory.md` | Graph theory: `math/graph/graph-theory-fundamentals.md`, `math/graph/graph-data-structures.md`, `math/graph/graph-traversal-algorithms.md`, `math/graph/shortest-path-algorithms.md`, `math/graph/minimum-spanning-tree.md`, `math/graph/network-flow-algorithms.md`, `math/graph/advanced-graph-algorithms.md`, `math/graph/graph-applications.md`
**Programming Language Theory:** Search `plt/*.md`, `plt/lambda-calculus.md`, `plt/type-systems.md`, `plt/dependent-types.md`, `plt/curry-howard.md`, `plt/operational-semantics.md`, `plt/program-verification.md`, `plt/typed-holes-*.md`, `plt/hazelnut-calculus.md`, `plt/live-programming-holes.md`, `plt/structure-editors.md`
**React Native:** Search `mobile/react-native-*.md`
**AWS Cloud:** Search `cloud/aws/*.md`, `aws-*.md`
**GCP Cloud:** Search `cloud/gcp/*.md`, `gcp-*.md`
**GitHub:** Search `collaboration/github/*.md`, `github-*.md`
**HuggingFace:** Search `ml/huggingface/*.md`, `huggingface-*.md`
**Information Retrieval:** Search `ir/*.md`, `ir-*.md`
**WebAssembly:** Search `wasm/*.md`, `wasm-*.md`
**eBPF:** Search `ebpf/*.md`, `ebpf-*.md`
**PRD Writing:** Search `product/*.md`, `prd-*.md`
**RFC Writing:** Search `engineering/*.md`, `rfc-*.md`

### By Task Type

**Starting new project:**
- iOS: `swiftui-architecture.md`
- Modal: `modal-functions-basics.md`
- TUI (Go): `bubbletea-architecture.md`
- TUI (Rust): `ratatui-architecture.md`
- Zig: `zig-project-setup.md`
- REST API: `rest-api-design.md`
- GraphQL API: `graphql-schema-design.md`
- Next.js app: `nextjs-app-router.md`
- React Native: `react-native-setup.md`
- Heroku deployment: `heroku-deployment.md`
- Netlify deployment: `netlify-deployment.md`

**Build systems:**
- C/C++ project: `make-fundamentals.md` or `cmake-patterns.md`
- Java project: `gradle-jvm-builds.md` or `maven-configuration.md`
- Monorepo: `bazel-monorepos.md`
- Choose build system: `build-system-selection.md`
- Cross-platform: `cross-platform-builds.md`
- Optimize builds: `build-optimization.md`

**Debugging:**
- C/C++ debugging: `gdb-fundamentals.md` or `lldb-macos-debugging.md`
- Python debugging: `python-debugging.md`
- Browser debugging: `browser-devtools.md`
- Remote debugging: `remote-debugging.md`
- Production debugging: `production-debugging.md`
- Memory leaks: `memory-leak-debugging.md`
- Concurrency issues: `concurrency-debugging.md`
- Core dumps: `core-dump-analysis.md`
- Crashes: `crash-debugging.md`
- Performance: `performance-profiling.md`
- Containers: `container-debugging.md`
- Network issues: `network-debugging.md`
- Distributed systems: `distributed-systems-debugging.md`

**Testing:**
- Unit tests: `unit-testing-patterns.md`
- Integration tests: `integration-testing.md`
- E2E tests: `e2e-testing.md`
- TDD workflow: `test-driven-development.md`
- iOS: `ios-testing.md`
- Zig: `zig-testing.md`

**Content quality review:**
- AI slop detection/cleanup: `anti-slop/SKILL.md`
- Text patterns: `anti-slop/references/text-patterns.md`
- Code patterns: `anti-slop/references/code-patterns.md`
- Design patterns: `anti-slop/references/design-patterns.md`

**Refactoring:**
- Systematic refactoring: `typed-holes-refactor/SKILL.md`
- Hole discovery: `typed-holes-refactor/scripts/discover_holes.py`
- Constraint propagation: `typed-holes-refactor/references/CONSTRAINT_RULES.md`
- Validation patterns: `typed-holes-refactor/references/VALIDATION_PATTERNS.md`

**Networking:**
- iOS: `ios-networking.md`
- Secure: `mtls-implementation.md`, `tailscale-vpn.md`
- Resilience: `network-resilience-patterns.md`, `mosh-resilient-ssh.md`

**Data persistence:**
- iOS: `swiftdata-persistence.md`
- Modal: `modal-volumes-secrets.md`
- PostgreSQL: `postgres-schema-design.md`
- MongoDB: `mongodb-document-design.md`

**Deployment:**
- Modal: `modal-functions-basics.md`, `modal-gpu-workloads.md`, `modal-web-endpoints.md`
- Containers: `dockerfile-optimization.md`, `docker-compose-development.md`
- Infrastructure: `terraform-patterns.md`, `aws-serverless.md`, `kubernetes-basics.md`
- CI/CD: `github-actions-workflows.md`, `cd-deployment-patterns.md`
- Zig: `zig-build-system.md`
- Heroku: `heroku-deployment.md`, `heroku-addons.md`
- Netlify: `netlify-deployment.md`, `netlify-functions.md`

**Observability:**
- Logging: `structured-logging.md`
- Metrics: `metrics-instrumentation.md`
- Tracing: `distributed-tracing.md`
- Alerting: `alerting-strategy.md`
- Dashboards: `dashboard-design.md`

**Data Engineering:**
- ETL: `etl-patterns.md`
- Streaming: `stream-processing.md`
- Batch: `batch-processing.md`
- Validation: `data-validation.md`
- Orchestration: `pipeline-orchestration.md`

### By Problem Domain

**Performance-critical:** `zig-memory-management.md`, `modal-gpu-workloads.md`, `tui-best-practices.md`, `frontend-performance.md`, `postgres-query-optimization.md`, `ci-optimization.md`, `react-native-performance.md`, `caching/*.md` (all caching skills)
**Async/concurrent:** `swift-concurrency.md`, `bubbletea-architecture.md`, `ratatui-architecture.md`, `react-data-fetching.md`, `stream-processing.md`
**Caching & Optimization:** `caching-fundamentals.md`, `http-caching.md`, `cdn-edge-caching.md`, `redis-caching-patterns.md`, `cache-invalidation-strategies.md`, `service-worker-caching.md`, `cache-performance-monitoring.md`
**Security:** `mtls-implementation.md`, `tailscale-vpn.md`, `network-resilience-patterns.md`, `container-security.md`, `api-authentication.md`, `api-authorization.md`, `ci-security.md`, `infrastructure-security.md`
**UI/UX:** `elegant-design/SKILL.md`, `swiftui-*.md`, `bubbletea-*.md`, `ratatui-*.md`, `react-component-patterns.md`, `web-accessibility.md`, `react-native-*.md`
**API Development:** `rest-api-design.md`, `graphql-schema-design.md`, `api-authentication.md`, `api-rate-limiting.md`
**DevOps/SRE:** `cicd/*.md`, `infrastructure/*.md`, `observability/*.md`, `cost-optimization.md`, `heroku-*.md`, `netlify-*.md`
**Data Engineering:** `data/*.md`, `stream-processing.md`, `batch-processing.md`, `data-validation.md`
**Content Quality:** `anti-slop/SKILL.md` (text, code, design quality review and cleanup)
**Refactoring:** `typed-holes-refactor/SKILL.md` (systematic test-driven refactoring with hole resolution)
**Real-time Systems:** `realtime/*.md`, `websocket-implementation.md`, `server-sent-events.md`, `pubsub-patterns.md`
**Formal Methods:** `formal/z3-*.md`, `formal/lean-*.md`, `formal/sat-*.md`, `formal/smt-*.md`, `formal/csp-*.md`
**Machine Learning:** `ml/unsloth-*.md`, `ml/diffusion-*.md`, `ml/llm-*.md`, `ml/stable-diffusion-*.md`
**Mathematics:** `math/*.md`
**Mobile Development:** `mobile/react-native-*.md`, `swiftui-*.md`, `ios-*.md`

---

## Skill Combination Examples

### Production-Ready CI/CD Pipeline
1. `github-actions-workflows.md` - Workflow structure
2. `ci-testing-strategy.md` - Test automation
3. `cd-deployment-patterns.md` - Deployment strategies
4. `ci-security.md` - Secret management
5. `ci-optimization.md` - Pipeline speed
6. `container-registry-management.md` - Image publishing
7. `observability/*.md` - Monitoring deployment

### Cloud Infrastructure with Terraform
1. `terraform-patterns.md` - IaC setup
2. `infrastructure-security.md` - Security hardening
3. `aws-serverless.md` or `kubernetes-basics.md` - Compute layer
4. `structured-logging.md` - Logging setup
5. `metrics-instrumentation.md` - Metrics collection
6. `alerting-strategy.md` - Alert configuration
7. `cost-optimization.md` - Resource optimization

### Real-time Collaboration Platform
1. `websocket-implementation.md` - Real-time connection
2. `realtime-sync.md` - Conflict resolution
3. `pubsub-patterns.md` - Message distribution
4. `redis-data-structures.md` - Session/presence storage
5. `api-authentication.md` - User auth
6. `distributed-tracing.md` - Debugging distributed system

### Data Pipeline with Observability
1. `etl-patterns.md` or `stream-processing.md` - Pipeline design
2. `data-validation.md` - Quality checks
3. `pipeline-orchestration.md` - Workflow management
4. `structured-logging.md` - Pipeline logging
5. `metrics-instrumentation.md` - Pipeline metrics
6. `alerting-strategy.md` - Data quality alerts
7. `dashboard-design.md` - Monitoring dashboards

### Full-Stack Next.js App
1. `nextjs-app-router.md` - App structure and routing
2. `react-component-patterns.md` - Component design
3. `react-data-fetching.md` - Data loading (SWR/React Query)
4. `react-form-handling.md` - Forms with validation
5. `frontend-performance.md` - Optimization
6. `web-accessibility.md` - A11y compliance
7. `nextjs-seo.md` - SEO optimization

### Elegant Interface with Chat/Terminal/Code
1. `elegant-design/SKILL.md` - Design foundation and workflow
2. Read `elegant-design/foundation/` - Typography, colors, spacing, layout
3. Read `elegant-design/interactive/` - Chat, terminals, code display, streaming
4. `react-component-patterns.md` - Component implementation
5. Read `elegant-design/implementation/` - Accessibility, performance, testing
6. `web-accessibility.md` - WCAG compliance validation

### Production REST API
1. `rest-api-design.md` - API design patterns
2. `api-authentication.md` - JWT/OAuth setup
3. `api-authorization.md` - RBAC implementation
4. `api-rate-limiting.md` - Rate limiting
5. `api-error-handling.md` - Standardized errors
6. `postgres-schema-design.md` - Database schema
7. `integration-testing.md` - API testing

### Containerized Microservice
1. `rest-api-design.md` or `graphql-schema-design.md` - API layer
2. `dockerfile-optimization.md` - Container image
3. `docker-compose-development.md` - Local development
4. `container-security.md` - Security hardening
5. `container-networking.md` - Service communication
6. `unit-testing-patterns.md` → `integration-testing.md` - Testing

### Full-Stack iOS App
1. `swiftui-architecture.md` - UI structure
2. `swift-concurrency.md` - Async data flow
3. `ios-networking.md` - API integration
4. `swiftdata-persistence.md` - Local storage
5. `swiftui-navigation.md` - Multi-screen flows
6. `ios-testing.md` - Test suite

### Modal ML Service
1. `modal-functions-basics.md` - App structure
2. `modal-image-building.md` - PyTorch environment
3. `modal-gpu-workloads.md` - GPU inference
4. `modal-web-endpoints.md` - HTTP API
5. `modal-volumes-secrets.md` - Model storage

### Secure Networked Service
1. `tailscale-vpn.md` - Private network
2. `mtls-implementation.md` - Service auth
3. `network-resilience-patterns.md` - Reliability
4. `modal-web-endpoints.md` or custom backend

### Terminal Dashboard
1. `bubbletea-architecture.md` or `ratatui-architecture.md` - Core framework
2. `bubbletea-components.md` or `ratatui-widgets.md` - UI components
3. `tui-best-practices.md` - Polish & performance
4. `network-resilience-patterns.md` - Data fetching (if needed)

### Complex Multi-Session Task
1. `beads-workflow.md` - Session management
2. `beads-dependency-management.md` - Task organization
3. `beads-multi-session-patterns.md` - Long-horizon patterns
4. `beads-context-strategies.md` - Context preservation (throughout)

### Systematic Codebase Refactoring
1. `typed-holes-refactor/SKILL.md` - Design by Typed Holes methodology
2. Create characterization tests - Capture current behavior
3. Discover holes - Identify architectural unknowns
4. Resolve holes iteratively - Test-driven development
5. Propagate constraints - Update dependent holes
6. Generate report - Comprehensive delta analysis

### SAT/SMT-based Verification
1. `z3-solver-basics.md` - Z3 fundamentals
2. `sat-solving-strategies.md` - SAT encoding
3. `smt-theory-applications.md` - Symbolic execution/model checking

### Lean 4 Formalization Project
1. `lean-proof-basics.md` - Proof structure
2. `lean-tactics.md` - Tactic language
3. `lean-mathlib4.md` - Library usage
4. `lean-theorem-proving.md` - Advanced proofs

### LLM Fine-tuning Workflow
1. `llm-dataset-preparation.md` - Dataset creation
2. `unsloth-finetuning.md` - Fast fine-tuning
3. `lora-peft-techniques.md` - LoRA/QLoRA
4. `modal-gpu-workloads.md` - Cloud GPU training

### Stable Diffusion Fine-tuning
1. `diffusion-model-basics.md` - Diffusion fundamentals
2. `diffusion-finetuning.md` - DreamBooth/LoRA
3. `stable-diffusion-deployment.md` - Modal deployment
4. `modal-gpu-workloads.md` - GPU optimization

### Constraint Satisfaction Problem
1. `csp-modeling.md` - CSP variables/constraints
2. `constraint-propagation.md` - AC-3 algorithm
3. `backtracking-search.md` - Optimization

### Heroku Deployment
1. `heroku-deployment.md` - App deployment
2. `heroku-addons.md` - Database/Redis/monitoring
3. `heroku-troubleshooting.md` - Debugging issues

### Netlify JAMstack
1. `netlify-deployment.md` - Static site deployment
2. `netlify-functions.md` - Serverless functions
3. `netlify-optimization.md` - Performance

### React Native iOS App
1. `react-native-setup.md` - Project initialization
2. `react-native-navigation.md` - Navigation
3. `react-native-native-modules.md` - Swift bridging
4. `react-native-performance.md` - Optimization
5. `ios-testing.md` - Testing

### Modal ML Troubleshooting
1. `modal-common-errors.md` - Common errors
2. `modal-performance-debugging.md` - Performance issues
3. `modal-gpu-workloads.md` - GPU optimization

### Full-Stack Caching Strategy
1. `caching-fundamentals.md` - Core patterns and eviction policies
2. `service-worker-caching.md` - Browser/PWA caching layer
3. `http-caching.md` - HTTP headers and conditional requests
4. `cdn-edge-caching.md` - CDN edge optimization
5. `redis-caching-patterns.md` - Application-level caching
6. `cache-invalidation-strategies.md` - Invalidation patterns
7. `cache-performance-monitoring.md` - Monitor and optimize

### High-Performance API with Caching
1. `rest-api-design.md` - API structure
2. `redis-caching-patterns.md` - Cache-Aside pattern
3. `cache-invalidation-strategies.md` - Event-based invalidation
4. `http-caching.md` - Cache-Control headers
5. `cdn-edge-caching.md` - CDN for static assets
6. `cache-performance-monitoring.md` - Track hit ratio

### Numerical Computing
1. `linear-algebra-computation.md` - Matrix operations
2. `optimization-algorithms.md` - SGD/Adam/L-BFGS
3. `numerical-methods.md` - ODE solvers
4. `probability-statistics.md` - Statistical methods

### Meta Skill Analysis
1. `skill-repo-discovery.md` - Analyze repository
2. `skill-repo-planning.md` - Plan missing skills for repo
3. `skill-prompt-discovery.md` - Analyze user prompt
4. `skill-prompt-planning.md` - Plan missing skills from prompts
5. `skill-creation.md` - Create new skills

### Content Quality Review
1. `anti-slop/SKILL.md` - Understand slop patterns & workflows
2. Run detection: `python scripts/detect_slop.py <file>`
3. Review findings manually with reference guides
4. Apply automated cleanup: `python scripts/clean_slop.py <file> --save`
5. Manual refinement and verification

---

## Quick Reference Table

| Task | Skills to Read | Order |
|------|----------------|-------|
| Build REST API | rest-api-design.md, api-authentication.md, api-authorization.md | 1→2→3 |
| Build GraphQL API | graphql-schema-design.md, api-authentication.md, api-authorization.md | 1→2→3 |
| Build Next.js app | nextjs-app-router.md, react-component-patterns.md, react-data-fetching.md | 1→2→3 |
| Setup C/C++ build | make-fundamentals.md or cmake-patterns.md, cross-platform-builds.md, build-optimization.md | 1→2→3 |
| Setup Java build | gradle-jvm-builds.md or maven-configuration.md, build-optimization.md | 1→2 |
| Setup monorepo build | bazel-monorepos.md, build-optimization.md | 1→2 |
| Choose build system | build-system-selection.md | 1 |
| Debug C/C++ crash | gdb-fundamentals.md or lldb-macos-debugging.md, core-dump-analysis.md, crash-debugging.md | 1→2→3 |
| Debug Python app | python-debugging.md, performance-profiling.md, memory-leak-debugging.md | 1→2→3 |
| Debug memory leak | memory-leak-debugging.md, performance-profiling.md | 1→2 |
| Debug concurrency | concurrency-debugging.md, performance-profiling.md | 1→2 |
| Debug production | production-debugging.md, distributed-systems-debugging.md | 1→2 |
| Debug containers | container-debugging.md, remote-debugging.md, network-debugging.md | 1→2→3 |
| Performance profiling | performance-profiling.md, build-optimization.md | 1→2 |
| Design elegant UI | elegant-design/SKILL.md, react-component-patterns.md, web-accessibility.md | 1→2→3 |
| Build chat interface | elegant-design/SKILL.md (read interactive/chat-and-messaging.md), react-component-patterns.md | 1→2 |
| Build terminal/code UI | elegant-design/SKILL.md (read interactive/terminals-and-code.md), react-component-patterns.md | 1→2 |
| Setup testing suite | unit-testing-patterns.md, integration-testing.md, e2e-testing.md | 1→2→3 |
| Practice TDD | test-driven-development.md, unit-testing-patterns.md | 1→2 |
| Containerize app | dockerfile-optimization.md, docker-compose-development.md | 1→2 |
| Start new iOS app | swiftui-architecture.md, swift-concurrency.md, swiftdata-persistence.md | 1→2→3 |
| Deploy ML model to Modal | modal-gpu-workloads.md, modal-functions-basics.md, modal-image-building.md | 1→2→3 |
| Build secure API | mtls-implementation.md, network-resilience-patterns.md | 1→2 |
| Create Go TUI app | bubbletea-architecture.md, bubbletea-components.md, tui-best-practices.md | 1→2→3 |
| Create Rust TUI app | ratatui-architecture.md, ratatui-widgets.md, tui-best-practices.md | 1→2→3 |
| New Zig project | zig-project-setup.md, zig-build-system.md, zig-memory-management.md | 1→2→3 |
| Manage long task | beads-workflow.md, beads-dependency-management.md, beads-multi-session-patterns.md | 1→2→3 |
| Create new skill | skill-creation.md | 1 |
| Setup VPN | tailscale-vpn.md | 1 |
| Remote SSH over poor network | mosh-resilient-ssh.md | 1 |
| P2P connection | nat-traversal.md, network-resilience-patterns.md | 1→2 |
| Optimize database | postgres-query-optimization.md, database-connection-pooling.md | 1→2 |
| Improve frontend perf | frontend-performance.md, web-accessibility.md | 1→2 |
| Add caching layer | caching-fundamentals.md, redis-caching-patterns.md, cache-performance-monitoring.md | 1→2→3 |
| Implement full-stack caching | service-worker-caching.md, http-caching.md, cdn-edge-caching.md, redis-caching-patterns.md | 1→2→3→4 |
| Optimize CDN caching | http-caching.md, cdn-edge-caching.md, cache-invalidation-strategies.md | 1→2→3 |
| Monitor cache performance | cache-performance-monitoring.md, cache-invalidation-strategies.md | 1→2 |
| Setup CI/CD pipeline | github-actions-workflows.md, ci-testing-strategy.md, cd-deployment-patterns.md | 1→2→3 |
| Setup observability | structured-logging.md, metrics-instrumentation.md, distributed-tracing.md | 1→2→3 |
| Build data pipeline | etl-patterns.md, data-validation.md, pipeline-orchestration.md | 1→2→3 |
| Real-time features | websocket-implementation.md, realtime-sync.md | 1→2 |
| Infrastructure as Code | terraform-patterns.md, infrastructure-security.md, cost-optimization.md | 1→2→3 |
| Deploy to Kubernetes | kubernetes-basics.md, infrastructure-security.md | 1→2 |
| Stream processing | stream-processing.md, data-validation.md, pipeline-orchestration.md | 1→2→3 |
| Solve SAT/SMT problem | z3-solver-basics.md, sat-solving-strategies.md | 1→2 |
| Formalize theorem in Lean | lean-proof-basics.md, lean-tactics.md, lean-mathlib4.md | 1→2→3 |
| Solve CSP | csp-modeling.md, constraint-propagation.md, backtracking-search.md | 1→2→3 |
| Fine-tune LLM | llm-dataset-preparation.md, unsloth-finetuning.md, lora-peft-techniques.md | 1→2→3 |
| Build DSPy QA system | dspy-setup.md, dspy-signatures.md, dspy-modules.md, dspy-optimizers.md | 1→2→3→4 |
| Build DSPy RAG pipeline | dspy-setup.md, dspy-rag.md, dspy-optimizers.md, dspy-evaluation.md | 1→2→3→4 |
| Evaluate LLM with benchmarks | llm-benchmarks-evaluation.md, llm-evaluation-frameworks.md | 1→2 |
| Setup LLM evaluation pipeline | llm-evaluation-frameworks.md (Arize Phoenix), llm-as-judge.md, rag-evaluation-metrics.md | 1→2→3 |
| Evaluate RAG system | rag-evaluation-metrics.md (RAGAS), llm-as-judge.md, llm-evaluation-frameworks.md | 1→2→3 |
| Route between multiple LLMs | llm-model-selection.md, llm-model-routing.md, multi-model-orchestration.md | 1→2→3 |
| Build hybrid search RAG | hybrid-search-rag.md, rag-reranking-techniques.md, rag-evaluation-metrics.md | 1→2→3 |
| Build GraphRAG system | graph-rag.md, llm-as-judge.md (quality eval), rag-evaluation-metrics.md | 1→2→3 |
| Build hierarchical RAG | hierarchical-rag.md, rag-reranking-techniques.md, rag-evaluation-metrics.md | 1→2→3 |
| Fine-tune diffusion model | diffusion-model-basics.md, diffusion-finetuning.md, stable-diffusion-deployment.md | 1→2→3 |
| Deploy to Heroku | heroku-deployment.md, heroku-addons.md | 1→2 |
| Deploy to Netlify | netlify-deployment.md, netlify-functions.md | 1→2 |
| Build React Native app | react-native-setup.md, react-native-navigation.md, react-native-performance.md | 1→2→3 |
| Debug Modal app | modal-common-errors.md, modal-performance-debugging.md | 1→2 |
| Numerical computing | linear-algebra-computation.md, optimization-algorithms.md, numerical-methods.md | 1→2→3 |
| Symbolic execution | z3-solver-basics.md, smt-theory-applications.md | 1→2 |
| Bridge React Native to Swift | react-native-native-modules.md, swift-concurrency.md | 1→2 |
| Analyze repository for skills | skill-repo-discovery.md, skill-repo-planning.md | 1→2 |
| Find skills for prompt | skill-prompt-discovery.md | 1 |
| Plan new skills | skill-repo-planning.md or skill-prompt-planning.md, skill-creation.md | 1→2 |
| Create new skill | skill-creation.md | 1 |
| Review content for AI slop | anti-slop/SKILL.md | 1 |
| Clean up generic code | anti-slop/references/code-patterns.md | 1 |
| Review design quality | anti-slop/references/design-patterns.md | 1 |
| Refactor codebase systematically | typed-holes-refactor/SKILL.md | 1 |

---

## Total Skills Count

- **259 atomic skills** across 45 categories
- **Average 380 lines** per skill
- **100% focused** - each skill has single clear purpose
- **Cross-referenced** - related skills linked for discoverability

### By Category Breakdown
**Core Foundation** (108 skills):
- API Design: 7 skills
- Testing: 6 skills
- Containers: 5 skills
- Frontend: 9 skills (including elegant-design)
- Database: 11 skills
- Caching & Performance: 7 skills (caching fundamentals, HTTP, CDN, Redis, invalidation, Service Workers, monitoring)
- Build Systems: 8 skills (Make, CMake, Gradle, Maven, Bazel, selection, cross-platform, optimization)
- Debugging: 14 skills (GDB, LLDB, Python, browser, remote, production, memory, concurrency, core dumps, crashes, profiling, containers, network, distributed)
- Workflow & Task Management: 6 skills (including typed-holes refactoring)
- Quality & Content Review: 1 skill (anti-slop detection and cleanup)
- Meta Skills: 4 skills (skill discovery and planning)
- iOS/Swift: 6 skills
- Modal.com: 8 skills (6 original + 2 troubleshooting)
- Networking: 5 skills
- TUI Development: 5 skills
- Zig Programming: 6 skills

**Cloud Platforms** (13 skills):
- AWS: 7 skills (Lambda, API Gateway, EC2, Storage, Databases, Networking, IAM/Security)
- GCP: 6 skills (Compute, Storage, Databases, Networking, IAM/Security, Serverless)

**Advanced Infrastructure** (28 skills):
- CI/CD: 5 skills
- Infrastructure: 6 skills
- Observability: 8 skills (logging, metrics, tracing, alerting, dashboards, OpenTelemetry, cost optimization, incident debugging)
- Real-time: 4 skills
- Data Pipelines: 5 skills

**Collaboration & Process** (17 skills):
- GitHub: 5 skills (Repository management, PRs, Issues/Projects, Security, Actions)
- Product (PRD): 4 skills (Structure, Requirements, User Stories, Technical Specs)
- Engineering (RFC): 4 skills (Structure, Technical Design, Consensus, Documentation)
- Heroku: 3 skills
- Netlify: 3 skills *(moved from Specialized Domains)*

**Machine Learning & AI** (33 skills):
- LLM Fine-tuning: 4 skills
- HuggingFace: 5 skills (Hub, Transformers, Datasets, Spaces, AutoTrain)
- DSPy Framework: 7 skills
- LLM Evaluation & Routing: 8 skills (Benchmarks, Frameworks, LLM-as-judge, RAGAS, Custom eval, Routing, Selection, Orchestration)
- Advanced RAG: 4 skills (Hybrid search, Reranking, GraphRAG, Hierarchical)
- Diffusion Models: 3 skills
- Information Retrieval: 5 skills (Search, Vector Search, Ranking, Recommendations, Query Understanding)

**Systems Programming** (8 skills):
- WebAssembly: 4 skills (Fundamentals, Rust Toolchain, Browser, Server-side)
- eBPF: 4 skills (Fundamentals, Tracing, Networking, Security)

**Specialized Domains** (52 skills):
- SAT/SMT Solvers: 3 skills
- Lean 4: 4 skills
- Constraint Satisfaction: 3 skills
- Advanced Mathematics: 11 skills (4 numerical + 7 pure math)
- Programming Language Theory: 13 skills (6 core + 7 typed holes & live programming)
- React Native: 4 skills
- Formal Methods: 2 skills (verification-focused)

---

## Migration from Old Skills

If you're looking for content from the original monolithic skills:

| Old Skill Directory | New Atomic Skills |
|---------------------|-------------------|
| `beads-context/` | `beads-*.md` (4 skills) |
| `ios-native-dev/` | `swiftui-*.md`, `swift-*.md`, `ios-*.md` (6 skills) |
| `modal-dev/` | `modal-*.md` (6 skills) |
| `secure-networking/` | `tailscale-*.md`, `mtls-*.md`, `mosh-*.md`, `nat-*.md`, `network-*.md` (5 skills) |
| `tui-development/` | `bubbletea-*.md`, `ratatui-*.md`, `tui-*.md` (5 skills) |
| `zig-dev/` | `zig-*.md` (6 skills) |

See `MIGRATION_GUIDE.md` for detailed mapping.

---

**Last Updated:** 2025-10-26
**Total Skills:** 259
**Format Version:** 1.0 (Atomic)
