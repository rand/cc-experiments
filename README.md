# Claude Code Experiments

This repository contains development guidelines and a comprehensive skills library for working with Claude Code. It serves as a reference for best practices, workflows, and atomic skills across multiple technology stacks.

## Contents

### CLAUDE.md
Development guidelines covering:
- Core workflow with Beads task management
- Critical thinking and technical pushback
- Language stack standards (Python, Zig, Rust, Go, TypeScript, Swift)
- Cloud platform patterns (Modal.com, Cloudflare Workers, Vercel, AWS)
- Testing protocols and validation
- Version control workflows
- Frontend development with Next.js + shadcn/ui

### Skills Directory
91 atomic, composable skills organized by category:

**Core Categories (66 skills):**
- **API Design** (7): REST, GraphQL, auth/authz, rate limiting, versioning, error handling
- **Testing** (6): Unit, integration, e2e, TDD, coverage, performance testing
- **Containers** (5): Dockerfile optimization, Compose, security, networking, registries
- **Frontend** (8): React patterns, Next.js App Router, state/data/forms, a11y, performance, SEO
- **Database** (8): Postgres, MongoDB, Redis, pooling, ORMs, selection
- **Beads Workflow** (4): Core workflow, context strategies, multi-session, troubleshooting
- **iOS/Swift** (8): SwiftUI architecture, Swift concurrency, SwiftData, navigation
- **Modal.com** (9): Functions, GPU workloads, web endpoints, volumes, scheduling
- **Networking** (5): Tailscale, mTLS, Mosh, NAT traversal, resilience patterns
- **TUI** (5): Bubble Tea/Ratatui architecture, styling, components, state management
- **Zig** (6): Project setup, memory management, testing, comptime, cross-compilation

**Advanced Categories (25 skills):**
- **CI/CD** (5): GitHub Actions workflows, testing strategy, deployment, optimization, security
- **Infrastructure** (6): Terraform, AWS serverless, Kubernetes, Cloudflare Workers, cost optimization
- **Observability** (5): Logging, metrics, tracing, alerting, dashboards
- **Real-time** (4): WebSocket, Server-Sent Events, sync, pub/sub patterns
- **Data Pipeline** (5): ETL, stream processing, batch processing, validation, orchestration

## Usage

### Browse Skills
Explore the full catalog in `skills/_INDEX.md` or search by pattern:
```bash
ls skills/zig-*.md          # Zig development
ls skills/modal-*.md        # Modal.com cloud platform
ls skills/swiftui-*.md      # SwiftUI iOS development
ls skills/api/*.md          # API design patterns
ls skills/cicd/*.md         # CI/CD workflows
```

### Compose Skills
Combine multiple skills for complex workflows:
```bash
# Example: Full-stack web development
skills/api/rest-api-design.md
+ skills/frontend/nextjs-app-router.md
+ skills/database/postgres-schema-design.md
+ skills/cicd/github-actions-workflows.md
```

### Follow Guidelines
Refer to `CLAUDE.md` for:
- Session start protocols
- Testing workflows (commit before testing!)
- Git branching strategies
- Language-specific tooling
- Cloud deployment patterns

## Key Principles

1. **Atomic Skills**: Each skill is focused, composable, and ~260 lines
2. **Discovery-Driven**: Search and read only what you need
3. **Workflow-First**: Use Beads for task management and multi-session work
4. **Quality Gates**: Critical thinking, pushback on vague requirements, proper testing
5. **Standards Enforcement**: Language-specific package managers, strict typing, error handling

## Project Structure
```
.
├── CLAUDE.md              # Development guidelines
├── README.md              # This file
└── skills/                # Atomic skills library
    ├── _INDEX.md          # Full catalog with search patterns
    ├── api/               # API design skills
    ├── cicd/              # CI/CD skills
    ├── containers/        # Container skills
    ├── data/              # Data pipeline skills
    ├── database/          # Database skills
    ├── frontend/          # Frontend skills
    ├── infrastructure/    # Infrastructure skills
    ├── observability/     # Observability skills
    ├── realtime/          # Real-time skills
    ├── testing/           # Testing skills
    └── *.md               # Individual skills (Beads, Modal, iOS, Zig, etc.)
```

## Getting Started

1. **Read CLAUDE.md** for comprehensive development guidelines
2. **Explore skills/_INDEX.md** for the complete skills catalog
3. **Search by pattern** to find relevant skills for your task
4. **Compose skills** as needed for complex workflows
5. **Follow the Master Decision Tree** in CLAUDE.md for task execution

## Contributing

This is a personal reference repository. Skills are atomic, composable, and regularly updated based on practical experience.

## License

Personal reference materials. Not licensed for redistribution.
