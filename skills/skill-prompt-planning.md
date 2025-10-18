---
name: skill-prompt-planning
description: Skill for skill prompt planning
---


# Prompt Skill Planning

## Overview

This skill enables analyzing user prompts, requests, and conversation patterns to identify gaps in the skills catalog and plan creation of new skills that would be genuinely useful. It drives evolution of the skill system based on actual usage patterns rather than speculation.

## When to Use This Skill

### Primary Triggers

**User requests help with tech not in skills catalog**
```
Example: "Help me set up Cloudflare D1 with Drizzle ORM"
→ Search skills catalog: No cloudflare-d1-*.md or drizzle-*.md
→ Usage frequency check: First occurrence? Note and track
→ Second+ occurrence? Plan skill creation
```

**Repeated questions about same domain across conversations**
```
Example: User asks about Supabase auth integration 3 times over 2 weeks
→ Pattern detected: Recurring need
→ Current state: No supabase-*.md skills exist
→ Action: Plan supabase-auth-patterns.md skill
```

**Complex workflow lacks documented skill chain**
```
Example: User frequently combines Vercel + Postgres + Drizzle + tRPC
→ Individual pieces may exist, but workflow integration doesn't
→ Skill chain missing: vercel-fullstack-patterns.md
→ Plan composite skill documenting the full stack
```

**User brings unique domain expertise worth capturing**
```
Example: User shows deep knowledge of Kubernetes + Argo CD + GitOps
→ User's context/questions reveal expertise
→ Current catalog: No k8s-*.md or gitops-*.md skills
→ Opportunity: Capture user's workflow as skill
```

**After skill-prompt-discovery.md reveals gaps**
```
1. Run skill-prompt-discovery.md first
2. Identify what skills SHOULD exist but don't
3. Use THIS skill to plan creation
4. Use skill-creation.md to execute
```

### When NOT to Use This Skill

**Don't plan skills for**:
- One-time questions (not reusable)
- Highly project-specific needs (too narrow)
- Topics already covered in existing skills (check _INDEX.md first)
- Rapidly changing tech without stable patterns (e.g., alpha-stage frameworks)
- User's temporary curiosity vs actual workflow need

## Core Concepts

### Usage Pattern Analysis

**What gets asked repeatedly matters most**

```
Tracking Pattern Example:

Week 1: "How do I use Supabase auth with Next.js?"
Week 2: "Can you help with Supabase Row Level Security?"
Week 3: "Need help with Supabase realtime subscriptions"

Analysis:
- Domain: Supabase
- Frequency: 3 occurrences over 3 weeks
- Breadth: Auth, RLS, Realtime (3 sub-domains)
- Assessment: HIGH value skill candidate
- Proposed skill: supabase-integration-patterns.md
```

**Indicators of high-value patterns**:
- Same tech mentioned 3+ times
- Questions span multiple aspects of same domain
- User struggles with integration (not just API usage)
- Tech is part of recommended stack (see CLAUDE.md section 3-4)
- Community adoption is high (GitHub stars, npm downloads)

### Generalization

**Transform specific requests into general skill scope**

```
Specific Request → General Skill

"Help me deploy FastAPI to Fly.io with Postgres"
  ↓
Generalize: Not just Fly.io, but deployment patterns
  ↓
Check existing: modal-*.md (Modal deployment), but no generic Python deployment
  ↓
Proposed scope: python-deployment-patterns.md
  ↓
Contents: Fly.io, Railway, Render, Modal, AWS Lambda deployment
```

**Generalization Decision Tree**:
```
Specific request
  ↓
Is this pattern reusable? NO → Don't create skill
  ↓ YES
Does broader domain make sense? NO → Keep narrow scope
  ↓ YES
Would broader skill stay cohesive? NO → Split into multiple skills
  ↓ YES
Does it avoid duplication? NO → Extend existing skill instead
  ↓ YES
Generalize to broader scope
```

**Examples**:

```
❌ Too Specific:
Request: "Deploy my blog to Vercel with Sanity CMS"
Bad skill: vercel-sanity-blog-deployment.md
Why: Too narrow, one use case

✅ Well Generalized:
Request: "Deploy my blog to Vercel with Sanity CMS"
Good skill: vercel-deployment-patterns.md
Scope: Next.js deployment, env vars, domains, previews, analytics
Benefit: Reusable for any Vercel deployment
```

```
❌ Over-Generalized:
Request: "Help with React state management"
Bad skill: javascript-state-patterns.md
Why: Too broad, covers React, Vue, vanilla JS, etc.

✅ Appropriately Scoped:
Request: "Help with React state management"
Good skill: react-state-management.md
Scope: useState, useReducer, Context, Zustand, Jotai
Benefit: Cohesive, focused on React ecosystem
```

### Skill Worthiness Assessment

**One-off vs Reusable**

```
High Worthiness:
- Affects multiple projects/users
- Combines multiple technologies (integration patterns)
- Addresses common pain points (auth, deployment, testing)
- Part of recommended stack (CLAUDE.md section 3-4)
- Stable tech with established patterns

Low Worthiness:
- Project-specific configuration
- Solved by reading official docs once
- Tech in beta/alpha (patterns not stable)
- Already covered in existing skills
- Niche use case (affects <5% of projects)
```

**Scoring Framework** (0-10 scale):

```
Frequency (0-3):
0 = One-time question
1 = Asked 2 times
2 = Asked 3-5 times
3 = Asked 6+ times

Reusability (0-3):
0 = Project-specific
1 = Applies to similar projects
2 = Applies to domain (e.g., all web apps)
3 = Universal (applies to all projects)

Complexity (0-2):
0 = Answered by docs in 5 min
1 = Requires integration knowledge
2 = Requires deep expertise/patterns

Stability (0-2):
0 = Alpha/beta tech
1 = Stable but evolving
2 = Mature with established patterns

Total Score ≥ 6 → Create skill
Total Score 4-5 → Track and re-evaluate
Total Score ≤ 3 → Don't create skill
```

**Example Scoring**:

```
Request: "Help with Cloudflare D1 + Drizzle ORM"
Frequency: 2 (asked 3 times)
Reusability: 2 (applies to all CF Workers projects with DB)
Complexity: 2 (requires integration knowledge, migration patterns)
Stability: 1 (D1 is stable, but evolving)
Total: 7 → CREATE SKILL

Request: "How do I center a div in CSS?"
Frequency: 1 (asked twice)
Reusability: 3 (universal)
Complexity: 0 (docs solve it instantly)
Stability: 2 (mature)
Total: 6 → BORDERLINE (probably don't create, too basic)

Request: "Deploy to my company's internal Kubernetes cluster"
Frequency: 1 (asked twice)
Reusability: 0 (company-specific)
Complexity: 2 (requires expertise)
Stability: 2 (mature)
Total: 5 → DON'T CREATE (too specific)
```

### Conversation-Driven Skill Evolution

**Skills emerge from real usage, not speculation**

```
Wrong Approach:
"I'll create 50 skills covering every possible tech stack"
→ Result: Unused skills, maintenance burden, noise

Right Approach:
"User asked about Remix 3 times. Time to plan remix-patterns.md"
→ Result: Skills that get used, proven value
```

**Evolution Pattern**:
```
1. Track user questions (mental note or Beads issue)
2. Identify patterns (same domain, 3+ occurrences)
3. Validate gap (search _INDEX.md, grep skills/)
4. Score worthiness (use framework above)
5. Plan scope (generalize appropriately)
6. Create skill (use skill-creation.md)
7. Validate utility (does it get used?)
8. Iterate (extend based on new questions)
```

## Patterns

### Pattern: Identify Repeated Tech Stack Combinations

**Signal**: Same tech combo appears 3+ times

```
Example 1: Supabase + Next.js

Occurrence 1: "Setup Supabase auth in Next.js app"
Occurrence 2: "How do I use Supabase RLS with Next.js server actions?"
Occurrence 3: "Supabase realtime with Next.js App Router?"
Occurrence 4: "Deploy Next.js + Supabase to Vercel"
Occurrence 5: "Supabase storage in Next.js"

Analysis:
- Tech: Supabase + Next.js (confirmed stack)
- Frequency: 5 occurrences
- Breadth: Auth, RLS, Realtime, Storage, Deployment
- Gap: No supabase-*.md skills exist

Planned Skill: supabase-nextjs-patterns.md
Scope:
  - Supabase client setup (App Router)
  - Auth integration (middleware, server components)
  - Database queries (server actions, RLS)
  - Realtime subscriptions
  - Storage (uploads, signed URLs)
  - Deployment (env vars, migrations)

Atomic decomposition:
  - supabase-auth-patterns.md (auth, RLS, policies)
  - supabase-data-patterns.md (queries, realtime, storage)
  - supabase-deployment.md (migrations, CI/CD, env management)
```

```
Example 2: Cloudflare D1 + Drizzle

Occurrence 1: "Setup Drizzle with Cloudflare D1"
Occurrence 2: "D1 migrations with Drizzle"
Occurrence 3: "Type-safe queries with Drizzle + D1"

Analysis:
- Tech: Cloudflare D1 + Drizzle ORM
- Frequency: 3 occurrences
- Breadth: Setup, migrations, queries
- Gap: No cloudflare-d1-*.md or drizzle-*.md

Planned Skill: cloudflare-d1-drizzle.md
Scope:
  - Drizzle config for D1
  - Schema definition and types
  - Migrations (local vs production)
  - Query patterns (select, insert, joins)
  - Testing strategies
  - Deployment (wrangler, bindings)
```

### Pattern: Extract Workflow Patterns from Multi-Step Requests

**Signal**: User describes complex workflow with multiple steps

```
Example: Full-Stack Deployment Workflow

User request:
"I need to:
1. Setup Postgres database
2. Create Drizzle schema
3. Build FastAPI backend
4. Deploy to Railway
5. Connect Next.js frontend
6. Deploy frontend to Vercel
7. Setup CI/CD for both"

Analysis:
- This is a WORKFLOW, not a single tech question
- Multiple technologies involved
- User needs integration guidance, not individual tech docs
- Gap: No skill covers this full-stack pattern

Planned Skill: fullstack-deployment-workflow.md
Scope:
  - Database setup (Railway Postgres, Supabase, Neon)
  - ORM integration (Drizzle, Prisma)
  - Backend deployment (Railway, Render, Fly.io)
  - Frontend deployment (Vercel, Netlify, Cloudflare Pages)
  - Environment variable management
  - CI/CD patterns (GitHub Actions, Railway/Vercel auto-deploy)
  - Monitoring and debugging
```

### Pattern: Recognize Domain Expertise in User's Context

**Signal**: User demonstrates deep knowledge in specific domain

```
Example: User shows Kubernetes expertise

User's questions:
"How do I structure Helm charts for multi-tenant apps?"
"Best practices for Argo CD app-of-apps pattern?"
"Managing secrets with External Secrets Operator vs Sealed Secrets?"

Analysis:
- User has deep K8s knowledge (not beginner questions)
- Questions reveal production-grade patterns
- Current catalog: No k8s-*.md skills
- Opportunity: Capture user's expertise as skill

Action:
1. Ask user: "I notice you have K8s expertise. Would you be open to
   collaborating on a k8s-deployment-patterns.md skill?"
2. Use conversation to extract patterns
3. Document user's workflow and best practices
4. Create skill that captures this expertise
```

### Pattern: Map Pain Points to Skill Opportunities

**Signal**: User repeatedly struggles with same integration/concept

```
Example: Auth integration pain point

Occurrence 1: "How do I integrate Clerk with Next.js middleware?"
Occurrence 2: "Clerk session management in server components?"
Occurrence 3: "Protecting API routes with Clerk?"
Occurrence 4: "Clerk + tRPC integration?"

Analysis:
- Domain: Authentication (Clerk specifically)
- Pain point: Integration patterns (not Clerk basics)
- Pattern: User knows Clerk, struggles with Next.js integration
- Gap: No clerk-*.md or nextjs-auth-*.md skills

Planned Skill: nextjs-auth-patterns.md
Scope:
  - Auth providers (Clerk, Auth0, Supabase, NextAuth)
  - Middleware protection patterns
  - Server component auth
  - API route protection
  - Client-side auth state
  - Session management
  - Role-based access control (RBAC)
```

### Pattern: Validate Gap (Search _INDEX.md First)

**Critical step**: Always check before planning

```
Process:
1. Search _INDEX.md for domain keywords
2. Use glob to find related skills: ls skills/domain-*.md
3. Read potentially overlapping skills
4. Determine: Does skill exist, partially exist, or not exist?

Example: Planning "remix-patterns.md"

Step 1: Search _INDEX.md
→ No "Remix" entries found

Step 2: Glob search
→ ls skills/remix-*.md (no results)
→ ls skills/*routing*.md (find nextjs-routing.md, but not Remix)

Step 3: Read related skills
→ Read nextjs-routing.md to see if it covers Remix (it doesn't)

Step 4: Determine
→ Gap confirmed: No Remix skills exist
→ Proceed with planning
```

**Anti-example** (skip validation):

```
User: "Help with Modal.com GPU setup"

❌ Wrong: Immediately plan modal-gpu-setup.md

✅ Right:
1. Search _INDEX.md → Find "Modal.com Cloud (9 skills)"
2. Check catalog → modal-gpu-workloads.md EXISTS
3. Decision: Don't create skill, activate existing one
```

## Quick Reference

### Skill Worthiness Checklist

```
Create skill if ALL of these are true:
□ Asked about 3+ times (or 2+ with high complexity)
□ Applies to multiple projects/users
□ Not already covered in existing skills
□ Tech is stable (not alpha/beta)
□ Integration/workflow patterns (not just API reference)
□ Passes scoring framework (≥6 points)

Track and re-evaluate if:
□ Asked 2 times
□ Emerging tech with growing adoption
□ Partially covered by existing skills (might extend)

Don't create skill if:
□ One-time question
□ Project-specific
□ Fully covered in existing skills
□ Answered by official docs in <5 min
□ Tech is unstable (frequent breaking changes)
```

### Scope Definition Guide

**How broad/narrow should the skill be?**

```
Too Narrow (avoid):
- vercel-nextjs-blog-deployment.md (one use case)
- drizzle-postgres-user-table.md (one table schema)
- clerk-signin-button.md (one component)

Appropriately Scoped (target):
- vercel-deployment-patterns.md (all Vercel deployment)
- drizzle-schema-patterns.md (schema design patterns)
- clerk-auth-integration.md (full auth integration)

Too Broad (avoid):
- web-deployment.md (covers all platforms)
- database-patterns.md (covers all databases)
- authentication.md (covers all auth methods)
```

**Scope Decision Framework**:

```
1. Start with user's specific request
2. Identify the domain (Vercel, Drizzle, Clerk)
3. List related topics in same domain
4. Draw boundaries:
   - Include: Related patterns in same domain
   - Exclude: Different domains, one-off use cases
5. Validate cohesion: Would these topics go together in docs?
6. Check length: Can it fit in 350-400 lines?
   - Too long? Split into multiple atomic skills
   - Too short? Might be too narrow
```

### Priority Assessment

**Frequency × Reusability = Priority**

```
Priority Matrix:

High Frequency (6+ asks) + High Reusability (universal) = URGENT
  Example: nextjs-deployment-patterns.md

High Frequency (6+ asks) + Med Reusability (domain) = HIGH
  Example: fastapi-modal-patterns.md

Med Frequency (3-5 asks) + High Reusability (universal) = HIGH
  Example: ci-cd-patterns.md

Med Frequency (3-5 asks) + Med Reusability (domain) = MEDIUM
  Example: drizzle-schema-patterns.md

Low Frequency (2 asks) + High Reusability (universal) = MEDIUM
  Example: docker-optimization.md

Low Frequency (2 asks) + Low Reusability (specific) = LOW
  Example: Track and re-evaluate

Priority Levels:
- URGENT: Create immediately
- HIGH: Create within 1 week
- MEDIUM: Create when next encountered
- LOW: Track but don't create yet
```

### Planning Process

**Step-by-step workflow**:

```
1. Identify Gap
   - User asks question about tech X
   - Search _INDEX.md and grep skills/
   - Confirm: No skill exists for this domain

2. Validate Need
   - Is this the first, second, or third+ occurrence?
   - Score using worthiness framework
   - Decision: Create, track, or skip?

3. Scope Definition
   - What's the domain? (Vercel, Modal, Supabase)
   - What related topics fit? (deployment, auth, DB)
   - What's excluded? (other platforms, unrelated topics)
   - Validate cohesion and length

4. Execute with skill-creation.md
   - Follow template structure
   - Target 350-400 lines
   - Include concrete examples
   - Link to related skills

5. Track with Beads (optional)
   bd create "Create supabase-auth-patterns.md skill" -t task -p 2
```

## Anti-Patterns

### Creating Skills for One-Time Questions

```
❌ Anti-Pattern:

User: "How do I parse JSON in Python?"
You: "I'll create python-json-parsing.md skill"

Why wrong:
- One-time question
- Answered by docs in 30 seconds
- No integration complexity
- Won't be reused

✅ Correct:

User: "How do I parse JSON in Python?"
You: [Answer directly with json.loads() example]
Action: None (don't create skill)
```

### Over-Specializing (Skills Too Narrow)

```
❌ Anti-Pattern:

User asks about Vercel deployment 3 times:
- "Deploy Next.js to Vercel"
- "Setup Vercel environment variables"
- "Configure Vercel domains"

You create:
- vercel-nextjs-deployment.md
- vercel-env-vars.md
- vercel-domains.md

Why wrong:
- Three skills for one platform
- Should be one cohesive skill
- Fragmentation makes discovery harder

✅ Correct:

Create one skill: vercel-deployment-patterns.md
Sections:
- Next.js deployment
- Environment variables
- Custom domains
- Preview deployments
- Analytics and monitoring
```

### Duplicating Existing Skills Under Different Names

```
❌ Anti-Pattern:

Existing skill: modal-gpu-workloads.md (covers GPU selection, memory, timeouts)

User: "How do I run ML models on Modal?"
You: Plan modal-ml-deployment.md

Why wrong:
- modal-gpu-workloads.md already covers this
- Creates duplication and confusion
- Violates DRY principle

✅ Correct:

1. Search _INDEX.md → Find modal-gpu-workloads.md
2. Read existing skill → Confirm it covers ML use case
3. Activate existing skill instead of creating new one
4. If gap exists, consider EXTENDING existing skill
```

### Creating Skills Before Validating Need

```
❌ Anti-Pattern:

User: "Help with Astro framework"
You: Immediately plan astro-patterns.md

Why wrong:
- Didn't check if user will use Astro again
- Didn't validate if Astro is in recommended stack
- Didn't assess stability/adoption
- Might be one-off curiosity

✅ Correct:

1. Answer user's Astro question
2. Note occurrence (mental or Beads issue)
3. If asked again → Track pattern
4. If asked 3rd time → Score and plan skill
5. Validate: Is Astro part of workflows? Stable? Growing?
```

## Related Skills

### skill-creation.md
**When to use**: After planning, to execute skill creation
**Relationship**: Planning (this skill) → Creation (skill-creation.md)

```
Workflow:
1. Use skill-prompt-planning.md to plan scope
2. Use skill-creation.md to build the skill
```

### skill-prompt-discovery.md
**When to use**: Before planning, to discover what exists
**Relationship**: Discovery → Planning → Creation

```
Workflow:
1. Use skill-prompt-discovery.md to map current state
2. Use skill-prompt-planning.md to plan new skills
3. Use skill-creation.md to create
```

### skill-repo-planning.md
**When to use**: Planning skills based on repo analysis
**Relationship**: Repo-focused version of this skill

```
Difference:
- skill-prompt-planning.md: Driven by user questions/prompts
- skill-repo-planning.md: Driven by repo/codebase analysis

Both: Use skill-creation.md to execute
```

### beads-workflow.md
**When to use**: Track skill creation as Beads issues
**Relationship**: Task management for skill creation

```
Example:
bd create "Create supabase-auth-patterns.md" -t task -p 2
bd update bd-123 --status in_progress
[Create skill using skill-creation.md]
bd close bd-123 --reason "Skill created and validated"
```

## Examples

### Full Planning Example: Cloudflare D1 + Drizzle

```
Step 1: Identify Gap

User asks (over 2 weeks):
1. "Setup Drizzle with Cloudflare D1"
2. "How do I run D1 migrations with Drizzle?"
3. "Type-safe D1 queries with Drizzle?"

Search _INDEX.md: No cloudflare-* or drizzle-* skills
Grep skills/: No matches

Gap confirmed: Missing skill

Step 2: Validate Need

Worthiness scoring:
- Frequency: 2 (asked 3 times)
- Reusability: 2 (applies to all CF Workers with DB)
- Complexity: 2 (requires integration knowledge)
- Stability: 1 (D1 is stable, Drizzle is mature)
- Total: 7 → CREATE SKILL

Step 3: Scope Definition

Domain: Cloudflare D1 + Drizzle ORM
Related topics:
- Drizzle config for D1
- Schema definition
- Type generation
- Local development
- Migrations (wrangler d1 migrations)
- Query patterns
- Testing strategies
- Deployment

Excluded:
- Other Cloudflare services (R2, KV)
- Other ORMs (Prisma, Kysely)

Skill name: cloudflare-d1-drizzle.md
Target: 350-400 lines

Step 4: Execute

Use skill-creation.md to build:
- Overview section
- When to Use
- Core Concepts (D1 architecture, Drizzle setup)
- Patterns (schema, migrations, queries)
- Quick Reference
- Anti-Patterns
- Related Skills

Step 5: Validate

After creation:
- Does it answer the 3 original questions? ✓
- Is it reusable for future D1+Drizzle projects? ✓
- Is scope appropriate (not too narrow/broad)? ✓
- Length: 380 lines ✓
```

### Planning Decision: Don't Create Skill

```
Scenario:

User: "How do I deploy my company's internal app to our private K8s cluster with custom Helm charts and ArgoCD pointing to our GitLab instance?"

Analysis:

Worthiness scoring:
- Frequency: 0 (first time)
- Reusability: 0 (company-specific setup)
- Complexity: 2 (complex, but not generalizable)
- Stability: 2 (mature tech)
- Total: 4 → DON'T CREATE

Reasoning:
- Highly specific to user's company infrastructure
- Not reusable for other users
- Configuration details won't transfer
- Better served by direct assistance

Action:
- Help user directly
- Don't plan skill
- Note: If questions about general K8s+ArgoCD patterns emerge (not company-specific), re-evaluate
```

---

**Skill System Philosophy**: Skills emerge from real usage patterns. Plan when frequency × reusability × complexity justify creation. Validate gaps, scope appropriately, and execute with skill-creation.md.
