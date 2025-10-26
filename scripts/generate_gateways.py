#!/usr/bin/env python3
"""
Generate gateway SKILL.md files and category INDEX.md files for all skill categories.
"""

import os
from pathlib import Path
from typing import List, Tuple

# Category metadata: (directory, keywords, description)
CATEGORIES = [
    ("api", "API, REST, GraphQL, endpoints, authentication, OAuth, JWT, rate limiting, versioning, authorization",
     "Automatically discover API design skills"),
    ("database", "database, SQL, PostgreSQL, MongoDB, Redis, query optimization, schema design, migrations, ORM",
     "Automatically discover database skills"),
    ("frontend", "React, Next.js, frontend, UI, components, forms, state management, data fetching, accessibility",
     "Automatically discover frontend development skills"),
    ("testing", "testing, tests, unit tests, integration, e2e, TDD, test coverage, performance testing, Playwright",
     "Automatically discover testing skills"),
    ("containers", "Docker, containers, Kubernetes, container security, networking, registry, docker-compose",
     "Automatically discover container and Docker skills"),
    ("ml", "machine learning, ML, AI, models, training, inference, PyTorch, TensorFlow, transformers, embeddings",
     "Automatically discover machine learning and AI skills"),
    ("math", "mathematics, algorithms, linear algebra, calculus, topology, category theory, proofs, theorems",
     "Automatically discover mathematics and algorithm skills"),
    ("cloud", "cloud, Modal, serverless, functions, AWS, GCP, Azure, deployment, scaling, cloud infrastructure",
     "Automatically discover cloud computing and serverless skills"),
    ("plt", "compilers, parsers, programming language theory, type systems, interpreters, AST, LLVM, bytecode",
     "Automatically discover programming language theory skills"),
    ("debugging", "debugging, GDB, LLDB, profiling, memory leaks, performance analysis, troubleshooting, diagnostics",
     "Automatically discover debugging and profiling skills"),
    ("observability", "monitoring, logging, tracing, metrics, distributed tracing, alerts, dashboards, observability",
     "Automatically discover observability and monitoring skills"),
    ("build-systems", "build systems, Make, CMake, Gradle, Maven, Bazel, compilation, incremental builds, caching",
     "Automatically discover build system skills"),
    ("caching", "caching, cache, Redis, CDN, HTTP caching, cache invalidation, performance, Service Workers",
     "Automatically discover caching and performance skills"),
    ("formal", "formal methods, theorem proving, SAT, SMT, Z3, Lean, constraint solving, verification, proofs",
     "Automatically discover formal methods and verification skills"),
    ("deployment", "deployment, Netlify, Heroku, CI/CD, production, releases, rollback, deployment strategies",
     "Automatically discover deployment and release skills"),
    ("infrastructure", "infrastructure, Terraform, IaC, Cloudflare Workers, security, cost optimization, DevOps",
     "Automatically discover infrastructure and DevOps skills"),
    ("data", "ETL, data pipelines, batch processing, stream processing, data validation, orchestration, Airflow",
     "Automatically discover data pipeline and ETL skills"),
    ("realtime", "realtime, WebSockets, Server-Sent Events, streaming, push notifications, live updates, pub/sub",
     "Automatically discover realtime communication skills"),
    ("mobile", "iOS, Swift, SwiftUI, mobile, SwiftData, concurrency, networking, mobile app development",
     "Automatically discover mobile development skills"),
    ("wasm", "WebAssembly, WASM, wasm-pack, Rust to WASM, browser WASM, WASI, portable bytecode",
     "Automatically discover WebAssembly skills"),
    ("ebpf", "eBPF, kernel, tracing, networking, security, BPF, performance monitoring, system observability",
     "Automatically discover eBPF and kernel skills"),
    ("cicd", "CI/CD, GitHub Actions, GitLab CI, automation, pipelines, continuous integration, deployment automation",
     "Automatically discover CI/CD and automation skills"),
    ("product", "product management, roadmap, strategy, prioritization, user research, product development",
     "Automatically discover product management skills"),
    ("engineering", "engineering practices, code review, documentation, team collaboration, technical leadership",
     "Automatically discover software engineering practice skills"),
    ("collaboration", "collaboration, code review, documentation, pair programming, team workflows, communication",
     "Automatically discover collaboration and teamwork skills"),
    ("ir", "intermediate representation, IR, LLVM IR, compiler optimizations, code generation, SSA",
     "Automatically discover intermediate representation and compiler skills"),
    ("modal", "Modal, serverless functions, cloud deployment, GPU workloads, web endpoints, Modal platform",
     "Automatically discover Modal platform skills"),
]

def get_skills_in_category(category_dir: str) -> List[str]:
    """Get list of skill files in a category directory."""
    path = Path(f"skills/{category_dir}")
    if not path.exists():
        return []

    skills = []
    for file in path.glob("*.md"):
        if file.name != "INDEX.md":
            skills.append(file.name)
    return sorted(skills)

def generate_gateway_skill(category: str, keywords: str, description: str) -> str:
    """Generate a gateway SKILL.md file."""
    skills = get_skills_in_category(category)
    skill_list = "\n".join([f"{i+1}. **{s.replace('.md', '')}**" for i, s in enumerate(skills)])

    template = f"""---
name: discover-{category}
description: {description} when working with {keywords.split(',')[0].strip()}. Activates for {category} development tasks.
---

# {category.title().replace('-', ' ')} Skills Discovery

Provides automatic access to comprehensive {category} skills.

## When This Skill Activates

This skill auto-activates when you're working with:
{chr(10).join([f"- {kw.strip()}" for kw in keywords.split(',')[:8]])}

## Available Skills

### Quick Reference

The {category.title()} category contains {len(skills)} skills:

{skill_list}

### Load Full Category Details

For complete descriptions and workflows:

```bash
cat skills/{category}/INDEX.md
```

This loads the full {category.title()} category index with:
- Detailed skill descriptions
- Usage triggers for each skill
- Common workflow combinations
- Cross-references to related skills

### Load Specific Skills

Load individual skills as needed:

```bash
{chr(10).join([f"cat skills/{category}/{skill}" for skill in skills[:5]])}
```

## Progressive Loading

This gateway skill enables progressive loading:
- **Level 1**: Gateway loads automatically (you're here now)
- **Level 2**: Load category INDEX.md for full overview
- **Level 3**: Load specific skills as needed

## Usage Instructions

1. **Auto-activation**: This skill loads automatically when Claude Code detects {category} work
2. **Browse skills**: Run `cat skills/{category}/INDEX.md` for full category overview
3. **Load specific skills**: Use bash commands above to load individual skills

---

**Next Steps**: Run `cat skills/{category}/INDEX.md` to see full category details.
"""
    return template

def main():
    """Generate gateway skills for all categories."""
    print("Generating gateway skills and category indexes...")

    for category, keywords, description in CATEGORIES:
        # Skip if already exists (for POC skills)
        gateway_dir = Path(f"skills/discover-{category}")
        gateway_file = gateway_dir / "SKILL.md"

        if gateway_file.exists():
            print(f"✓ {category}: Gateway already exists, skipping")
            continue

        # Create gateway directory
        gateway_dir.mkdir(parents=True, exist_ok=True)

        # Generate gateway skill
        content = generate_gateway_skill(category, keywords, description)
        gateway_file.write_text(content)

        print(f"✓ {category}: Created gateway skill")

    print("\nDone! Generated gateway skills for all categories.")
    print("\nNext steps:")
    print("1. Create category INDEX.md files (manual or scripted)")
    print("2. Review and enhance gateway skills with workflow details")

if __name__ == "__main__":
    main()
