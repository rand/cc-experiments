---
name: skill-repo-planning
description: Skill for skill repo planning
---


# Repository Skill Planning

## Overview

This skill enables systematic analysis of codebases to identify skill gaps—domains, technologies, patterns, and workflows present in repositories that aren't covered by existing skills. Use this to plan which new skills should be created to maximize team effectiveness.

**Target**: 350-400 lines for focused, actionable guidance
**Scope**: Gap analysis, skill scoping, priority assessment, planning workflow

---

## When to Use This Skill

### Primary Triggers

1. **New Repository Analysis**
   - Discovered repo using technologies not in skills catalog
   - Onboarding to unfamiliar codebase with unique patterns
   - Inherited legacy system with undocumented conventions

2. **Gap Discovery**
   - After running `skill-repo-discovery.md` reveals missing coverage
   - Team repeatedly asks questions about same domain
   - Recurring patterns found during code review
   - Internal tooling lacks documentation

3. **Strategic Planning**
   - Planning skills expansion for organization
   - Capturing specialized domain knowledge before departure
   - Standardizing team practices across projects
   - Building organizational knowledge base

4. **Integration Points**
   - Custom frameworks/libraries unique to organization
   - Company-specific workflows (deployment, testing, auth)
   - Third-party service integration patterns
   - Internal API conventions

### Decision Framework

```
Repository Analysis Needed?
  ↓
Run skill-repo-discovery.md first
  ↓
Found gaps in coverage? YES → Use this skill
  ↓
Identify patterns → Scope skills → Prioritize → Create
```

---

## Core Concepts

### 1. Gap Analysis

**Definition**: Comparing what exists (current skills) vs. what's needed (repo patterns)

**Gap Types**:
- **Technology gaps**: Technologies used but not documented (e.g., Redis patterns, Celery workflows)
- **Pattern gaps**: Repeated code patterns without guidance (e.g., error handling, retry logic)
- **Workflow gaps**: Team processes undocumented (e.g., deployment, testing, PR review)
- **Domain gaps**: Business logic patterns (e.g., payment processing, data pipelines)

**Example**:
```
Repository: E-commerce platform
Current skills: swiftui-*, modal-*, zig-*
Gap found: Stripe payment integration repeated in 8 files
  → Missing skill: "stripe-integration-patterns.md"
```

### 2. Atomic Skill Scoping

**Philosophy**: One skill = One coherent domain (250-400 lines)

**Good Skill Boundaries**:
- **Focused**: Covers single technology/pattern comprehensively
- **Actionable**: Contains enough detail to implement
- **Discoverable**: Clear naming convention (domain-topic.md)
- **Composable**: Works with other skills for complex workflows

**Bad Skill Boundaries**:
- Too broad: "backend-development.md" (thousands of topics)
- Too narrow: "how-to-import-redis.md" (trivial, not reusable)
- Too specific: "fix-bug-in-user-service.md" (one-off solution)

**Scoping Example**:
```
WRONG: "python-backend.md" (monolithic)
RIGHT: Atomic skills:
  - fastapi-api-design.md
  - sqlalchemy-relationships.md
  - celery-task-patterns.md
  - redis-caching-strategies.md
```

### 3. Priority Assessment

**Impact Dimensions**:
- **Frequency**: How often is this needed? (daily/weekly/monthly/rarely)
- **Complexity**: How hard is it to figure out each time? (trivial/moderate/complex)
- **Team size**: How many people need this? (1/few/many)
- **Risk**: What happens if done wrong? (low/medium/high)

**Priority Formula**:
```
Priority = (Frequency × Complexity × Team Size) + Risk Multiplier

High: Daily × Complex × Many people + High risk
Medium: Weekly × Moderate × Few people + Medium risk
Low: Rarely × Simple × One person + Low risk
```

**Example Assessment**:
```
Pattern: Custom auth middleware (15 files)
  Frequency: Daily (new services need auth)
  Complexity: High (JWT + refresh + RBAC)
  Team Size: 8 backend devs
  Risk: High (security implications)
  → Priority: HIGH

Pattern: CSV export utility (2 files)
  Frequency: Monthly (reports)
  Complexity: Low (standard library)
  Team Size: 2 people
  Risk: Low (data formatting only)
  → Priority: LOW
```

### 4. Skill Planning Workflow

**Five-Phase Process**:

```
Phase 1: Discovery
  → Run skill-repo-discovery.md
  → List all technologies/patterns found
  → Compare against existing skills

Phase 2: Gap Identification
  → Mark what's missing
  → Group related gaps (e.g., all Redis patterns)
  → Filter out trivial/one-off items

Phase 3: Scoping
  → Define skill boundaries (atomic, focused)
  → Name skills clearly (domain-topic.md)
  → Estimate content size (aim 250-400 lines)

Phase 4: Prioritization
  → Score each proposed skill
  → Rank by priority formula
  → Select top N for creation

Phase 5: Creation
  → Use skill-creation.md for implementation
  → Track with beads-workflow.md if multi-session
  → Update _INDEX.md when complete
```

---

## Patterns

### Pattern 1: Identify Custom Frameworks

**Scenario**: Organization built internal frameworks/libraries

**Detection Strategy**:
```bash
# Find custom imports
grep -r "from internal\." --include="*.py" | cut -d: -f2 | sort | uniq -c | sort -rn

# Find internal package usage
grep -r "@company/" --include="*.ts" | cut -d: -f2 | sort | uniq -c | sort -rn

# Find custom decorators/annotations
grep -rE "@(internal|custom|company)" --include="*.py" --include="*.java"
```

**Example**:
```
Found: "from internal.auth import require_role" (47 files)
Gap: No skill for internal auth framework
Proposed: "company-auth-patterns.md"
  - Covers: require_role, check_permissions, token validation
  - Sections: Setup, decorators, RBAC, testing
```

### Pattern 2: Find Repeated Code Patterns

**Scenario**: Same logic duplicated across files (candidates for skills)

**Detection Strategy**:
```bash
# Find repeated error handling
grep -rn "try:" --include="*.py" -A 10 | grep -E "(except|finally)" | wc -l

# Find repeated API patterns
grep -rn "requests\.(get|post)" --include="*.py" | cut -d: -f1 | sort | uniq -c | sort -rn

# Find repeated database patterns
grep -rn "session\.(query|add|commit)" --include="*.py" | cut -d: -f1 | sort | uniq -c | sort -rn
```

**Example**:
```
Found: Retry logic repeated in 23 API client files
Gap: No skill for retry/backoff patterns
Proposed: "http-retry-patterns.md"
  - Covers: Exponential backoff, circuit breakers, timeout handling
  - Examples: tenacity library, custom decorators, testing strategies
```

### Pattern 3: Analyze Internal Tooling

**Scenario**: Custom scripts/tools for deployment, testing, automation

**Detection Strategy**:
```bash
# Find custom scripts
ls scripts/*.{sh,py,js} | xargs -I {} basename {}

# Find Makefile/Justfile targets
grep "^[a-z-]*:" Makefile Justfile 2>/dev/null

# Find GitHub Actions workflows
ls .github/workflows/*.yml | xargs grep "name:"

# Find custom CLI tools
find . -name "*.py" -exec grep -l "if __name__ == .__main__." {} \;
```

**Example**:
```
Found: scripts/deploy.sh (custom deployment)
  - Uses: kubectl, helm, internal config service
  - Called by: CI/CD, manual deploys
Gap: No skill for company deployment process
Proposed: "company-k8s-deployment.md"
  - Covers: Environment setup, deploy script, rollback, monitoring
```

### Pattern 4: Map Company-Specific Workflows

**Scenario**: Processes unique to organization (not generic best practices)

**Detection Areas**:
- **Code review**: Custom checklist, automation, conventions
- **Testing**: Internal test frameworks, fixtures, CI setup
- **Deployment**: Blue/green, canary, feature flags
- **Monitoring**: Internal dashboards, alerting, on-call
- **Documentation**: RFCs, ADRs, runbooks

**Example**:
```
Workflow: Feature flag rollout
  - Uses: Internal flag service + LaunchDarkly
  - Process: Create flag → Test in staging → Gradual rollout → Metrics review
Gap: No skill for feature flag workflow
Proposed: "company-feature-flags.md"
  - Setup, flag creation, targeting rules, monitoring, cleanup
```

### Pattern 5: Identify Integration Patterns

**Scenario**: Custom ways of combining third-party services

**Detection Strategy**:
```bash
# Find service integrations
grep -rE "(import.*stripe|import.*twilio|import.*sendgrid)" --include="*.py"

# Find Redis + Celery patterns
grep -r "celery" --include="*.py" | grep -l "redis"

# Find Kafka + Postgres patterns
grep -r "KafkaConsumer" --include="*.py" | xargs grep -l "psycopg2"
```

**Example**:
```
Found: Kafka → Redis → Postgres pipeline (8 services)
Pattern: Events from Kafka → Cache in Redis → Batch write to Postgres
Gap: No skill for this specific integration
Proposed: "kafka-redis-postgres-pipeline.md"
  - Event consumption, caching strategy, batch writes, error handling
```

---

## Gap Identification Workflow

### Step 1: Run Discovery First

```bash
# Use skill-repo-discovery.md to catalog repository
# Output: List of technologies, frameworks, patterns
```

### Step 2: Compare Against Existing Skills

```bash
# List existing skills
ls /Users/rand/.claude/skills/*.md | xargs basename -s .md

# Check for gaps
# Example: Found "FastAPI" in repo, but no fastapi-*.md skills
```

### Step 3: Search for Patterns

```bash
# Custom libraries
grep -r "from (internal|company|custom)" --include="*.py" | cut -d: -f2 | sort | uniq

# Repeated imports (high usage = candidate)
grep -rh "^import\|^from" --include="*.py" | sort | uniq -c | sort -rn | head -20

# Configuration patterns
find . -name "*.yaml" -o -name "*.toml" -o -name "*.json" | head -20

# Testing patterns
grep -r "def test_\|it(" --include="*.py" --include="*.ts" | wc -l
```

### Step 4: Document Gaps

**Template**:
```markdown
## Gap Analysis Report

### Repository: [name]
### Date: [YYYY-MM-DD]
### Analyzer: [name]

### Technologies Found (from skill-repo-discovery.md)
- Python 3.11, FastAPI, SQLAlchemy, Redis, Celery, Pytest
- React, TypeScript, Vite, Tailwind CSS
- Docker, Kubernetes, GitHub Actions

### Existing Skills Coverage
- Python: ✅ (general patterns)
- Redis: ❌ (no redis-*.md skills)
- Celery: ❌ (no celery-*.md skills)
- React: ❌ (no react-*.md skills)
- Kubernetes: ❌ (no k8s-*.md skills)

### Gaps Identified
1. **redis-caching-strategies.md** (HIGH)
   - Frequency: Daily
   - Complexity: High
   - Files: 34 files use Redis
   - Patterns: Cache warming, invalidation, pub/sub

2. **celery-task-patterns.md** (HIGH)
   - Frequency: Daily
   - Complexity: High
   - Files: 28 task definitions
   - Patterns: Retries, chains, error handling

3. **fastapi-api-design.md** (MEDIUM)
   - Frequency: Weekly
   - Complexity: Medium
   - Files: 15 router files
   - Patterns: Dependency injection, auth, validation

4. **company-deployment.md** (LOW)
   - Frequency: Weekly
   - Complexity: Low
   - Files: scripts/deploy.sh
   - Patterns: Helm charts, kubectl, rollback
```

---

## Skill Scoping Guide

### Template for New Skill

```markdown
## Proposed Skill

**Filename**: [domain-topic.md]
**Target Lines**: 250-400
**Priority**: HIGH/MEDIUM/LOW

**Sections**:
1. Overview (what/when to use)
2. Core Concepts (3-5 key ideas)
3. Common Patterns (5-8 patterns with examples)
4. Quick Reference (commands, config)
5. Anti-Patterns (what not to do)
6. Related Skills (composition)

**Content Sources**:
- Files to analyze: [list 5-10 representative files]
- Documentation: [internal docs, READMEs]
- Team members: [SMEs to consult]

**Validation**:
- [ ] Atomic (focused on one domain)
- [ ] Actionable (enough detail to implement)
- [ ] Discoverable (clear naming)
- [ ] Composable (works with other skills)
```

### Example: Planning a Redis Skill

```markdown
## Proposed Skill

**Filename**: redis-caching-strategies.md
**Target Lines**: 350 lines
**Priority**: HIGH

**Sections**:
1. Overview - When to cache, cache types
2. Core Concepts - TTL, eviction, serialization, key design
3. Patterns:
   - Cache-aside (lazy loading)
   - Write-through caching
   - Cache warming strategies
   - Invalidation patterns
   - Pub/Sub for cache busting
   - Distributed locking
4. Quick Reference - Redis commands, Python client config
5. Anti-Patterns - Cache stampede, stale data, memory bloat
6. Related Skills - fastapi-api-design.md, celery-task-patterns.md

**Content Sources**:
- Files: src/cache/*.py, src/services/user_cache.py, src/middleware/cache.py
- Docs: docs/caching.md, redis-config.yaml
- SME: Backend lead (10 years Redis experience)

**Validation**:
- [x] Atomic (Redis caching only, not general Redis)
- [x] Actionable (patterns with code examples)
- [x] Discoverable (redis-caching-strategies.md)
- [x] Composable (integrates with FastAPI, Celery skills)
```

---

## Priority Matrix

### Scoring System

| Dimension | Score | Criteria |
|-----------|-------|----------|
| Frequency | 3 | Daily use |
| | 2 | Weekly use |
| | 1 | Monthly/rare use |
| Complexity | 3 | High (requires expertise) |
| | 2 | Medium (needs guidance) |
| | 1 | Low (self-explanatory) |
| Team Size | 3 | Entire team (8+ people) |
| | 2 | Multiple people (3-7) |
| | 1 | Individual (1-2) |
| Risk | +3 | High (security, data loss) |
| | +1 | Medium (bugs, downtime) |
| | +0 | Low (cosmetic issues) |

**Total Score = (Frequency × Complexity × Team Size) + Risk**

### Example Prioritization

```
Proposed Skills:

1. redis-caching-strategies.md
   - Frequency: 3 (daily), Complexity: 3 (high), Team: 3 (8 devs), Risk: +1 (medium)
   - Score: (3 × 3 × 3) + 1 = 28
   - Priority: HIGH

2. celery-task-patterns.md
   - Frequency: 3 (daily), Complexity: 3 (high), Team: 2 (4 devs), Risk: +1 (medium)
   - Score: (3 × 3 × 2) + 1 = 19
   - Priority: HIGH

3. fastapi-api-design.md
   - Frequency: 2 (weekly), Complexity: 2 (medium), Team: 3 (8 devs), Risk: +0 (low)
   - Score: (2 × 2 × 3) + 0 = 12
   - Priority: MEDIUM

4. csv-export-utility.md
   - Frequency: 1 (monthly), Complexity: 1 (low), Team: 1 (1 dev), Risk: +0 (low)
   - Score: (1 × 1 × 1) + 0 = 1
   - Priority: LOW (skip)
```

---

## Quick Reference

### Gap Identification Checklist

```
[ ] Run skill-repo-discovery.md first
[ ] List all technologies/frameworks used
[ ] Compare against existing skills (ls /Users/rand/.claude/skills/*.md)
[ ] Search for repeated imports/patterns (grep -rh "^import")
[ ] Find custom libraries (grep -r "from internal")
[ ] Analyze scripts/tooling (ls scripts/)
[ ] Check CI/CD workflows (.github/workflows/)
[ ] Document integration patterns (service A + B)
[ ] Review team pain points (frequent questions)
[ ] Filter out trivial/one-off items
```

### Planning Workflow

```bash
# Step 1: Discovery
# Use skill-repo-discovery.md

# Step 2: Find patterns
grep -rh "^import\|^from" --include="*.py" | sort | uniq -c | sort -rn | head -20

# Step 3: Scope skills
# Use template above (Filename, Sections, Sources, Validation)

# Step 4: Prioritize
# Use scoring matrix (Frequency × Complexity × Team Size + Risk)

# Step 5: Create skills
# Use skill-creation.md for top priority items

# Step 6: Track progress
bd create "Create redis-caching-strategies.md skill" -t feature -p 1 --json
```

---

## Anti-Patterns

### ❌ Creating Monolithic Skills

**Problem**: "everything-about-X.md" (thousands of lines, hard to navigate)

**Example**:
```
WRONG: python-backend-development.md (covers FastAPI, SQLAlchemy, Celery, Redis, testing, deployment)
RIGHT: Separate skills:
  - fastapi-api-design.md
  - sqlalchemy-orm-patterns.md
  - celery-task-patterns.md
  - redis-caching-strategies.md
```

### ❌ Documenting One-Off Solutions

**Problem**: Creating skill for code that won't be reused

**Example**:
```
WRONG: "fix-user-service-bug.md" (specific to one incident)
RIGHT: "debugging-distributed-systems.md" (general debugging patterns)
```

### ❌ Skipping Validation

**Problem**: Assuming gap exists without checking if skill already exists under different name

**Example**:
```
WRONG: Create "kubernetes-deployment.md" without checking existing skills
RIGHT: Search first:
  ls skills/*k8s*.md
  ls skills/*deploy*.md
  grep -l "kubernetes" skills/*.md
```

### ❌ Creating Skills for Deprecated Tech

**Problem**: Documenting technology being phased out

**Example**:
```
WRONG: "angular-js-patterns.md" (team migrating to React)
RIGHT: "react-migration-patterns.md" (covers migration process)
```

### ❌ Ignoring Composition

**Problem**: Creating duplicate content instead of referencing related skills

**Example**:
```
WRONG: Repeat auth setup in "fastapi-api-design.md" and "celery-task-patterns.md"
RIGHT: Create "company-auth-patterns.md", reference from both skills
```

---

## Related Skills

### Prerequisite Skills

- **skill-repo-discovery.md**: Run first to catalog repository technologies/patterns
- **skill-creation.md**: Use after planning to implement new skills

### Complementary Skills

- **beads-workflow.md**: Track skill creation work across sessions
- **skill-prompt-planning.md**: Plan custom prompts for discovered workflows

### Workflow Integration

```
1. skill-repo-discovery.md → Catalog repo
2. skill-repo-planning.md → Identify gaps, scope skills (THIS SKILL)
3. beads-workflow.md → Track creation work (if multi-session)
4. skill-creation.md → Implement new skills
5. Update _INDEX.md → Make skills discoverable
```

---

## Execution Example

### Scenario: Analyzing E-commerce Backend

```bash
# Step 1: Discovery
# Output: Python 3.11, FastAPI, SQLAlchemy, Stripe, Redis, Celery, Pytest

# Step 2: Find patterns
grep -rh "^from\|^import" --include="*.py" src/ | sort | uniq -c | sort -rn | head -20
# Output:
#   47 from internal.auth import require_role
#   34 import redis
#   28 from celery import shared_task
#   23 import stripe
#   15 from fastapi import APIRouter

# Step 3: Identify gaps
ls /Users/rand/.claude/skills/*.md | grep -E "(redis|celery|stripe|fastapi)" | wc -l
# Output: 0 (no matching skills)

# Step 4: Scope skills
# - company-auth-patterns.md (internal framework)
# - redis-caching-strategies.md (34 files)
# - celery-task-patterns.md (28 tasks)
# - stripe-integration-patterns.md (payment flows)
# - fastapi-api-design.md (15 routers)

# Step 5: Prioritize
# Auth: (3×3×3)+3 = 30 (HIGH, security risk)
# Redis: (3×3×3)+1 = 28 (HIGH)
# Celery: (3×3×2)+1 = 19 (HIGH)
# Stripe: (2×3×2)+3 = 15 (MEDIUM, payment risk)
# FastAPI: (2×2×3)+0 = 12 (MEDIUM)

# Step 6: Create top 3 skills
bd create "Create company-auth-patterns.md skill" -p 1 --json
bd create "Create redis-caching-strategies.md skill" -p 1 --json
bd create "Create celery-task-patterns.md skill" -p 2 --json
```

---

## Summary

Repository skill planning transforms ad-hoc knowledge into reusable guidance:

1. **Discover gaps**: Compare repo patterns to existing skills
2. **Scope atomically**: One skill = One focused domain (250-400 lines)
3. **Prioritize ruthlessly**: Frequency × Complexity × Team Size + Risk
4. **Create systematically**: Use skill-creation.md for implementation
5. **Track progress**: Use beads-workflow.md for multi-skill projects

**Key principle**: Skills capture reusable knowledge, not one-off solutions. If it's repeated, complex, or high-risk, it's a skill candidate.

Follow the workflow: Discovery → Gap analysis → Scoping → Prioritization → Creation.
