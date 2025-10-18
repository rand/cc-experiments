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
129 atomic, composable skills organized by category:

**Core Categories (71 skills):**
- **API Design** (7): REST, GraphQL, auth/authz, rate limiting, versioning, error handling
- **Testing** (6): Unit, integration, e2e, TDD, coverage, performance testing
- **Containers** (5): Dockerfile optimization, Compose, security, networking, registries
- **Frontend** (8): React patterns, Next.js App Router, state/data/forms, a11y, performance, SEO
- **Database** (8): Postgres, MongoDB, Redis, pooling, ORMs, selection
- **Workflow & Tasks** (5): Beads workflow, context strategies, multi-session, dependency management
- **Meta Skills** (4): Skill discovery and planning for repositories and prompts
- **iOS/Swift** (6): SwiftUI architecture, Swift concurrency, SwiftData, networking, testing, UIKit integration
- **Modal.com** (8): Functions, GPU workloads, web endpoints, volumes, scheduling, troubleshooting, debugging, optimization
- **Networking** (5): Tailscale, mTLS, Mosh, NAT traversal, resilience patterns
- **TUI** (5): Bubble Tea/Ratatui architecture, styling, components, state management
- **Zig** (6): Project setup, memory management, testing, comptime, cross-compilation, C interop

**Advanced Infrastructure (25 skills):**
- **CI/CD** (5): GitHub Actions workflows, testing strategy, deployment, optimization, security
- **Infrastructure** (6): Terraform, AWS serverless, Kubernetes, Cloudflare Workers, cost optimization, security
- **Observability** (5): Logging, metrics, tracing, alerting, dashboards
- **Real-time** (4): WebSocket, Server-Sent Events, sync, pub/sub patterns
- **Data Pipeline** (5): ETL, stream processing, batch processing, validation, orchestration

**Specialized Domains (33 skills):**
- **SAT/SMT Solvers** (3): Z3 solver basics, SAT solving, SMT theory
- **Lean 4** (4): Proof basics, tactics, mathlib4, theorem proving
- **Constraint Satisfaction** (3): CSP modeling, constraint propagation, backtracking
- **Heroku** (3): Deployment, add-ons, troubleshooting
- **Netlify** (3): Deployment, functions, optimization
- **LLM Fine-tuning** (4): Unsloth, HuggingFace AutoTrain, dataset preparation, LoRA/PEFT
- **Diffusion Models** (3): Diffusion basics, Stable Diffusion deployment, fine-tuning
- **Advanced Mathematics** (4): Linear algebra, optimization, numerical methods, probability/statistics
- **React Native** (4): Setup, navigation, native modules, performance

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
    ├── deployment/        # Deployment platform skills (Heroku, Netlify)
    ├── formal/            # Formal methods (SAT/SMT, Lean, CSP)
    ├── frontend/          # Frontend skills
    ├── infrastructure/    # Infrastructure skills
    ├── math/              # Advanced mathematics
    ├── ml/                # Machine learning (LLM fine-tuning, diffusion models)
    ├── mobile/            # Mobile development (React Native)
    ├── modal/             # Modal.com cloud platform
    ├── observability/     # Observability skills
    ├── realtime/          # Real-time skills
    ├── testing/           # Testing skills
    ├── skill-*.md         # Meta skills (discovery, planning, creation)
    └── *.md               # Individual skills (Beads, iOS, Zig, networking, etc.)
```

## Getting Started

1. **Read CLAUDE.md** for comprehensive development guidelines
2. **Explore skills/_INDEX.md** for the complete skills catalog
3. **Search by pattern** to find relevant skills for your task
4. **Compose skills** as needed for complex workflows
5. **Follow the Master Decision Tree** in CLAUDE.md for task execution

## Contributing

This is a personal reference repository. Skills are atomic, composable, and regularly updated based on practical experience.
