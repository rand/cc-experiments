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

### Frontend Skills (8 skills)

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

**Common workflows:**
- New Next.js app: `nextjs-app-router.md` → `react-component-patterns.md` → `react-data-fetching.md`
- Forms with validation: `react-form-handling.md` → `react-state-management.md`
- Production optimization: `frontend-performance.md` → `web-accessibility.md` → `nextjs-seo.md`

---

### Database Skills (8 skills)

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

**Common workflows:**
- Slow query debugging: `postgres-query-optimization.md`
- Schema changes: `postgres-migrations.md` → `postgres-schema-design.md`
- New project: `database-selection.md` → `postgres-schema-design.md` or `mongodb-document-design.md`
- Performance issues: `postgres-query-optimization.md` → `database-connection-pooling.md` → `orm-patterns.md`
- Caching layer: `redis-data-structures.md`

---

### Workflow & Task Management (4 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `beads-workflow.md` | Starting sessions, running bd commands, managing issue workflow | ~350 |
| `beads-dependency-management.md` | Creating issue relationships, managing blockers, organizing work hierarchies | ~450 |
| `beads-context-strategies.md` | Managing Claude context, preventing bloat, preserving workflow state | ~400 |
| `beads-multi-session-patterns.md` | Complex multi-session tasks, long-horizon work chains, parallel streams | ~350 |

**Common workflows:**
- New session: `beads-workflow.md` → `beads-context-strategies.md`
- Complex task: `beads-workflow.md` → `beads-dependency-management.md` → `beads-multi-session-patterns.md`
- Context management: `beads-context-strategies.md` (throughout session)

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

### Observability Skills (5 skills)

| Skill | Use When | Lines |
|-------|----------|-------|
| `structured-logging.md` | JSON logging, log levels, correlation IDs, log aggregation | ~270 |
| `metrics-instrumentation.md` | Prometheus, StatsD, custom metrics, cardinality, histograms | ~290 |
| `distributed-tracing.md` | OpenTelemetry, spans, trace context, sampling | ~280 |
| `alerting-strategy.md` | Alert conditions, severity levels, on-call, alert fatigue | ~250 |
| `dashboard-design.md` | Grafana, visualization types, SLO dashboards, troubleshooting | ~260 |

**Common workflows:**
- Observability stack: `structured-logging.md` → `metrics-instrumentation.md` → `distributed-tracing.md`
- Monitoring setup: `metrics-instrumentation.md` → `alerting-strategy.md` → `dashboard-design.md`
- Debugging production: `distributed-tracing.md` → `structured-logging.md`

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

## Skill Discovery Patterns

### By Technology

**API Design:** Search `api-*.md`, `rest-*.md`, `graphql-*.md`
**Testing:** Search `test-*.md`, `unit-*.md`, `integration-*.md`, `e2e-*.md`, `performance-*.md`
**Containers/Docker:** Search `docker-*.md`, `container-*.md`, `dockerfile-*.md`
**Frontend/React:** Search `react-*.md`, `nextjs-*.md`, `web-*.md`, `frontend-*.md`
**Database/PostgreSQL:** Search `postgres-*.md`, `database-*.md`, `mongodb-*.md`, `redis-*.md`, `orm-*.md`
**Swift/SwiftUI:** Search `swiftui-*.md`, `swift-*.md`, `ios-*.md`
**Modal.com:** Search `modal-*.md`
**Networking:** Search `network-*.md`, `mtls-*.md`, `tailscale-*.md`, `nat-*.md`, `mosh-*.md`
**TUI (Go):** Search `bubbletea-*.md`, `tui-*.md`
**TUI (Rust):** Search `ratatui-*.md`, `tui-*.md`
**Zig:** Search `zig-*.md`
**Beads:** Search `beads-*.md`
**CI/CD:** Search `cicd/*.md`, `github-*.md`, `ci-*.md`, `cd-*.md`
**Infrastructure:** Search `infrastructure/*.md`, `terraform-*.md`, `aws-*.md`, `kubernetes-*.md`, `cloudflare-*.md`
**Observability:** Search `observability/*.md`, `logging-*.md`, `metrics-*.md`, `tracing-*.md`, `alerting-*.md`
**Real-time:** Search `realtime/*.md`, `websocket-*.md`, `sse-*.md`, `pubsub-*.md`
**Data Pipelines:** Search `data/*.md`, `etl-*.md`, `stream-*.md`, `batch-*.md`, `pipeline-*.md`

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

**Testing:**
- Unit tests: `unit-testing-patterns.md`
- Integration tests: `integration-testing.md`
- E2E tests: `e2e-testing.md`
- TDD workflow: `test-driven-development.md`
- iOS: `ios-testing.md`
- Zig: `zig-testing.md`

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

**Performance-critical:** `zig-memory-management.md`, `modal-gpu-workloads.md`, `tui-best-practices.md`, `frontend-performance.md`, `postgres-query-optimization.md`, `ci-optimization.md`
**Async/concurrent:** `swift-concurrency.md`, `bubbletea-architecture.md`, `ratatui-architecture.md`, `react-data-fetching.md`, `stream-processing.md`
**Security:** `mtls-implementation.md`, `tailscale-vpn.md`, `network-resilience-patterns.md`, `container-security.md`, `api-authentication.md`, `api-authorization.md`, `ci-security.md`, `infrastructure-security.md`
**UI/UX:** `swiftui-*.md`, `bubbletea-*.md`, `ratatui-*.md`, `react-component-patterns.md`, `web-accessibility.md`
**API Development:** `rest-api-design.md`, `graphql-schema-design.md`, `api-authentication.md`, `api-rate-limiting.md`
**DevOps/SRE:** `cicd/*.md`, `infrastructure/*.md`, `observability/*.md`, `cost-optimization.md`
**Data Engineering:** `data/*.md`, `stream-processing.md`, `batch-processing.md`, `data-validation.md`
**Real-time Systems:** `realtime/*.md`, `websocket-implementation.md`, `server-sent-events.md`, `pubsub-patterns.md`

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

---

## Quick Reference Table

| Task | Skills to Read | Order |
|------|----------------|-------|
| Build REST API | rest-api-design.md, api-authentication.md, api-authorization.md | 1→2→3 |
| Build GraphQL API | graphql-schema-design.md, api-authentication.md, api-authorization.md | 1→2→3 |
| Build Next.js app | nextjs-app-router.md, react-component-patterns.md, react-data-fetching.md | 1→2→3 |
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
| Setup VPN | tailscale-vpn.md | 1 |
| Remote SSH over poor network | mosh-resilient-ssh.md | 1 |
| P2P connection | nat-traversal.md, network-resilience-patterns.md | 1→2 |
| Optimize database | postgres-query-optimization.md, database-connection-pooling.md | 1→2 |
| Improve frontend perf | frontend-performance.md, web-accessibility.md | 1→2 |
| Setup CI/CD pipeline | github-actions-workflows.md, ci-testing-strategy.md, cd-deployment-patterns.md | 1→2→3 |
| Setup observability | structured-logging.md, metrics-instrumentation.md, distributed-tracing.md | 1→2→3 |
| Build data pipeline | etl-patterns.md, data-validation.md, pipeline-orchestration.md | 1→2→3 |
| Real-time features | websocket-implementation.md, realtime-sync.md | 1→2 |
| Infrastructure as Code | terraform-patterns.md, infrastructure-security.md, cost-optimization.md | 1→2→3 |
| Deploy to Kubernetes | kubernetes-basics.md, infrastructure-security.md | 1→2 |
| Stream processing | stream-processing.md, data-validation.md, pipeline-orchestration.md | 1→2→3 |

---

## Total Skills Count

- **91 atomic skills** across 16 categories
- **Average 280 lines** per skill
- **100% focused** - each skill has single clear purpose
- **Cross-referenced** - related skills linked for discoverability

### By Category Breakdown
**Core Foundation** (66 skills):
- API Design: 7 skills
- Testing: 6 skills
- Containers: 5 skills
- Frontend: 8 skills
- Database: 8 skills
- Beads Workflow: 4 skills
- iOS/Swift: 6 skills
- Modal.com: 6 skills
- Networking: 5 skills
- TUI Development: 5 skills
- Zig Programming: 6 skills

**Advanced Infrastructure** (25 skills):
- CI/CD: 5 skills
- Infrastructure: 6 skills
- Observability: 5 skills
- Real-time: 4 skills
- Data Pipelines: 5 skills

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

**Last Updated:** 2025-10-18
**Total Skills:** 91
**Format Version:** 1.0 (Atomic)
