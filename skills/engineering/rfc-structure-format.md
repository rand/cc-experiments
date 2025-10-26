---
name: engineering-rfc-structure-format
description: RFC document structure, templates, formatting conventions, and versioning for technical design documents
---

# RFC Structure & Format

**Scope**: Comprehensive guide to RFC formats, sections, templates, and documentation best practices for technical design
**Lines**: ~300
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Writing a new RFC (Request for Comments) for technical design
- Standardizing RFC format across an engineering team
- Choosing between lightweight and comprehensive RFC templates
- Defining what sections belong in an RFC vs PRD
- Setting up RFC templates in GitHub, Notion, or Google Docs
- Establishing RFC review and approval workflows
- Training engineers on effective technical writing
- Creating Architecture Decision Records (ADRs) for significant decisions

## Core Concepts

### Concept 1: RFC Purpose and Audience

**Primary Goals**:
- Document technical design decisions and rationale
- Enable team review and feedback before implementation
- Create referenceable record of why decisions were made
- Surface risks, trade-offs, and alternatives

**Key Audiences**:
- Engineering team: needs implementation details, trade-offs, risks
- Architects: needs system design, integration points, scalability
- Product/Design: needs understanding of technical constraints
- Future engineers: needs historical context for decisions

### Concept 2: RFC vs PRD vs ADR

**PRD (Product Requirements Document)**:
- Written by: Product Manager
- Focus: What we're building, why, user stories, success metrics
- Audience: Cross-functional (eng, design, leadership)

**RFC (Request for Comments)**:
- Written by: Engineer or Tech Lead
- Focus: How we're building it, architecture, trade-offs
- Audience: Engineering team, technical stakeholders

**ADR (Architecture Decision Record)**:
- Written by: Engineer or Architect
- Focus: Single significant decision (e.g., "Why we chose Postgres over MongoDB")
- Audience: Engineering team, future maintainers
- Format: Lightweight, decision-focused (subset of RFC)

### Concept 3: RFC Lifecycle and Status

**Status Flow**:
```
Draft → In Review → Approved → Implemented → Superseded/Deprecated
```

**Draft**: Author is still writing, not ready for review
**In Review**: Open for comments and feedback
**Approved**: Design accepted, ready for implementation
**Implemented**: Design has been built and shipped
**Superseded**: Replaced by newer RFC
**Deprecated**: Decision no longer valid (context changed)
**Rejected**: Proposal not accepted (document why)

---

## Patterns

### Pattern 1: Lightweight RFC Template

**When to use**:
- Small-to-medium features
- Established system with well-understood architecture
- Fast iteration, small team

```markdown
# RFC-001: Add User Profile Photo Upload

**Author**: Jane Doe (@jane)
**Created**: 2025-10-25
**Status**: Draft → In Review → Approved
**Reviewers**: @alice (backend), @bob (frontend), @charlie (security)

## Problem Statement
Users cannot currently upload profile photos. This is a top-requested feature
(50+ support tickets) and blocks social features planned for Q1.

## Proposed Solution
Add profile photo upload with S3 storage and CloudFront CDN.

### Architecture
```
Client → API (/upload-photo) → S3 (storage) → CloudFront (CDN) → Client (display)
```

### Implementation
1. Add `profile_photo_url` column to `users` table (nullable)
2. Create `/api/users/:id/upload-photo` endpoint:
   - Accept multipart/form-data (max 5MB)
   - Validate image type (JPEG, PNG, WebP)
   - Resize to 400x400px (ImageMagick)
   - Upload to S3 with UUID filename
   - Store CloudFront URL in database
3. Frontend: Add upload button in settings, display photo in nav

### Trade-offs
- **S3 + CloudFront** (chosen): Scalable, low latency, $0.023/GB
- **Local storage**: Cheaper short-term, doesn't scale, slow serving
- **Database BLOB**: Simple, but bloats DB and slow retrieval

## Security Considerations
- File type validation (reject executables, scripts)
- Virus scanning (ClamAV integration, future RFC)
- Rate limiting: 5 uploads per user per hour
- Private S3 bucket with signed URLs

## Risks
- Cost: ~$50/month at 10k users, $500/month at 100k users
- Storage growth: Plan archival policy (future RFC)

## Open Questions
- [ ] Should we support GIF avatars? (Decision: No for v1, revisit in Q2)
- [ ] Compress images server-side? (Decision: Yes, use 80% JPEG quality)

## Approval
- [x] Backend: @alice (approved 2025-10-25)
- [x] Frontend: @bob (approved 2025-10-25)
- [x] Security: @charlie (approved 2025-10-26)
```

### Pattern 2: Comprehensive RFC Template

**Use case**: Major architectural changes, new services, complex features

```markdown
# RFC-042: Real-Time Collaborative Editing System

## Metadata
- **RFC Number**: 042
- **Title**: Real-Time Collaborative Editing System
- **Author**: Alex Chen (@alex)
- **Contributors**: @jordan (backend), @taylor (frontend)
- **Created**: 2025-10-25
- **Last Updated**: 2025-10-26
- **Status**: In Review
- **DACI**:
  - **Driver**: @alex
  - **Approver**: @engineering-lead
  - **Contributors**: @jordan, @taylor, @sam (product)
  - **Informed**: eng-team@company.com

## Executive Summary
Implement real-time collaborative editing (like Google Docs) for our document editor.
Uses WebSocket for transport, Operational Transform (OT) for conflict resolution,
and Redis for state management. Supports 50 concurrent editors per document.

[2-3 paragraph summary for leadership]

## Background & Context
### Current State
- Document editing is single-user only
- Users manually save and reload to see others' changes
- Conflicts are frequent (last-write-wins, data loss)

### Problem
- 40% of users work in teams (user research, Q4 2024)
- 200+ support tickets re: lost edits due to conflicts
- Competitors (Notion, Coda) all have real-time collab

### Goals
- Enable 2-50 users to edit same document simultaneously
- Latency <200ms for edit propagation (p95)
- Zero data loss from conflicts (OT guarantees convergence)
- Ship MVP by Q1 2025

## Proposed Solution
### High-Level Architecture
```
┌──────────┐
│  Client  │ (Browser)
│  Editor  │
└────┬─────┘
     │ WebSocket
     ▼
┌──────────┐      ┌────────┐      ┌──────────┐
│   API    │─────▶│ Redis  │─────▶│ Postgres │
│  Server  │      │ (State)│      │ (Persist)│
└──────────┘      └────────┘      └──────────┘
```

### Components

**1. WebSocket Server** (Node.js + ws library)
- Handles persistent connections
- Routes operations between clients
- Manages presence (who's editing)

**2. Operational Transform Engine** (ot.js library)
- Transforms concurrent operations
- Guarantees convergence (all clients reach same state)
- Handles text insert/delete operations

**3. Redis State Store**
- Stores active document state (TTL: 1 hour)
- Manages operation history for late joiners
- Publishes operations to subscribers (Redis Pub/Sub)

**4. PostgreSQL Persistence**
- Stores final document snapshots (every 100 operations or 5 min)
- Document version history
- Audit log of all edits

**5. Client Editor** (React + Slate.js)
- Rich text editor with OT integration
- Displays cursors/selections of other users
- Optimistic updates with conflict resolution

### Data Flow
1. User types in editor → Generate OT operation
2. Send operation via WebSocket to server
3. Server applies OT transform (resolve conflicts)
4. Broadcast transformed operation to all clients
5. Clients apply operation to local state
6. Every 100 ops, persist snapshot to Postgres

## Alternative Approaches Considered

### Alternative 1: CRDTs (Conflict-Free Replicated Data Types)
**Pros**: Simpler conflict resolution, eventual consistency
**Cons**: Larger payload size, less battle-tested for text editing
**Decision**: OT chosen for smaller payloads and industry standard

### Alternative 2: Server-Side Rendering (SSR) with Polling
**Pros**: No WebSocket complexity
**Cons**: High latency (>1s), poor UX, server load
**Decision**: Rejected, latency unacceptable

### Alternative 3: Firebase Realtime Database
**Pros**: Fully managed, easy to integrate
**Cons**: Vendor lock-in, $0.05/GB (expensive at scale), limited OT support
**Decision**: Rejected, build in-house for cost and control

## Technical Deep Dive

### WebSocket Protocol
```json
// Client → Server: Edit operation
{
  "type": "operation",
  "doc_id": "abc123",
  "operation": {
    "position": 42,
    "insert": "Hello",
    "version": 15
  },
  "client_id": "user-xyz"
}

// Server → Clients: Transformed operation
{
  "type": "operation",
  "operation": {
    "position": 45,  // Transformed position
    "insert": "Hello",
    "version": 16
  },
  "author": "user-xyz"
}
```

### OT Transformation Example
```
Client A: Insert "X" at position 5 (version 10)
Client B: Insert "Y" at position 5 (version 10) [concurrent!]

Server receives A's operation first:
- Apply: "HelloWorld" → "HelloXWorld" (version 11)
- Broadcast to B with version 11

Server receives B's operation (still at version 10):
- Transform B's operation against A's: position 5 → 6 (shift right)
- Apply: "HelloXWorld" → "HelloXYWorld" (version 12)
- Broadcast to A with version 12

Final state for both clients: "HelloXYWorld" ✅ (converged)
```

## Non-Functional Requirements

### Performance
- Latency: <200ms for operation propagation (p95)
- Throughput: 1,000 operations/sec per server
- Concurrent editors: 50 per document
- WebSocket connections: 10,000 per server

### Scalability
- Horizontal scaling: Add more WebSocket servers (load balanced)
- Redis cluster: Shard by document ID
- Database: Read replicas for snapshots

### Reliability
- Auto-reconnect on connection loss (exponential backoff)
- Replay missed operations on reconnect (via Redis history)
- Periodic snapshots to survive Redis cache eviction

### Security
- Authenticate WebSocket connections (JWT)
- Authorize document access (check permissions)
- Rate limit: 100 operations/sec per user

## Migration & Rollout Plan

### Phase 1: Infrastructure Setup (Week 1-2)
- Deploy WebSocket server (1 instance)
- Set up Redis cluster
- Implement OT engine (ot.js integration)

### Phase 2: Alpha Testing (Week 3-4)
- Enable for internal team only (feature flag)
- Test with 2-5 concurrent editors
- Identify and fix bugs

### Phase 3: Beta Rollout (Week 5-6)
- Enable for 10% of users (feature flag)
- Monitor performance metrics (latency, errors)
- Gather user feedback

### Phase 4: General Availability (Week 7-8)
- Enable for all users
- Monitor at scale (10k+ concurrent editors)
- Plan horizontal scaling if needed

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| WebSocket server crash | High | Medium | Auto-restart, load balancer health checks |
| Redis cache eviction | High | Low | Persist snapshots every 5 min, replay from Postgres |
| OT bugs (divergence) | Critical | Low | Extensive testing, snapshot reconciliation |
| High cost at scale | Medium | Medium | Monitor costs, optimize Redis usage |

## Metrics & Monitoring

### Success Metrics
- 80% of collaborative sessions have <200ms latency
- <0.1% operation conflicts requiring manual resolution
- 90% of users report improved collaboration (survey)

### Monitoring
- Grafana dashboard: latency, operation rate, connection count
- Error tracking: Sentry for WebSocket errors
- Alerts: Latency >500ms, error rate >1%, Redis down

## Open Questions
- [ ] **Q1**: Should we support audio/video chat? (Decision: No, defer to Q2)
- [ ] **Q2**: Max document size for real-time? (Decision: 50k chars, show warning)
- [x] **Q3**: Which OT library? (Decision: ot.js, battle-tested)

## Appendix

### References
- Operational Transform: https://operational-transformation.github.io/
- ot.js library: https://github.com/Operational-Transformation/ot.js
- Google Wave OT whitepaper: [link]

### Glossary
- **OT**: Operational Transform (conflict resolution algorithm)
- **CRDT**: Conflict-Free Replicated Data Type (alternative to OT)
- **TTL**: Time To Live (Redis cache expiration)
```

### Pattern 3: Architecture Decision Record (ADR) Template

**Use case**: Documenting single significant decision

```markdown
# ADR-005: Use PostgreSQL Over MongoDB for User Data

**Date**: 2025-10-25
**Status**: Accepted
**Deciders**: @alice (backend lead), @bob (architect)
**Consulted**: @charlie (DBA), @dana (product)

## Context
We need to choose a database for storing user data (profiles, settings, activity).
Current requirements:
- 100k users (growing to 1M in 2 years)
- ACID transactions for billing data
- Complex queries (JOINs, aggregations)
- Relational data (users, projects, memberships)

## Decision
We will use **PostgreSQL** as the primary database for user data.

## Consequences

### Positive
- ACID guarantees for financial transactions (required for compliance)
- Rich query capabilities (JOINs, window functions, CTEs)
- Strong ecosystem (ORMs, tools, monitoring)
- Team familiarity (all backend engineers know SQL)
- Proven scalability (10M+ rows, read replicas, partitioning)

### Negative
- Vertical scaling limits (need sharding at 10M+ users)
- Harder to scale writes than NoSQL
- Schema migrations require downtime (mitigated with tools like Alembic)

### Neutral
- Requires careful indexing for performance
- Need to plan sharding strategy for future scale

## Alternatives Considered

### MongoDB
**Pros**: Flexible schema, horizontal scaling, fast writes
**Cons**: No ACID across collections (deal-breaker for billing), weaker query capabilities
**Decision**: Rejected due to ACID requirement

### MySQL
**Pros**: Similar to Postgres, team familiarity
**Cons**: Weaker JSON support, less feature-rich than Postgres
**Decision**: Postgres chosen for JSON columns and better full-text search

### DynamoDB
**Pros**: Fully managed, infinite scaling
**Cons**: Vendor lock-in, expensive, limited query flexibility
**Decision**: Rejected, need complex queries
```

### Pattern 4: RFC Changelog and Version Tracking

**Use case**: Tracking changes during review process

```markdown
## Version History

| Version | Date | Author | Summary of Changes |
|---------|------|--------|--------------------|
| 1.3 | 2025-10-26 | @alex | Added security section per @charlie's feedback |
| 1.2 | 2025-10-25 | @alex | Changed from CRDTs to OT per team discussion |
| 1.1 | 2025-10-24 | @alex | Added cost analysis |
| 1.0 | 2025-10-23 | @alex | Initial draft |

## Change Log
- **2025-10-26**: Added rate limiting (100 ops/sec per user) per security review
- **2025-10-25**: Switched from CRDTs to OT after benchmarking (payload size 60% smaller)
- **2025-10-24**: Added Redis Pub/Sub for operation broadcast (replaced direct WebSocket)
```

### Pattern 5: DACI Decision Framework in RFC

**Use case**: Clarifying roles for complex decisions

```markdown
## DACI Framework

**Driver**: @alex
- Responsible for RFC creation and pushing to decision
- Collects feedback and drives consensus
- Updates RFC based on input

**Approver**: @engineering-lead
- Final decision authority
- Approves or rejects RFC
- Can delegate to subject matter expert

**Contributors**: @jordan (backend), @taylor (frontend), @sam (product)
- Provide input and feedback
- Review and comment on RFC
- No veto power, but concerns addressed

**Informed**: eng-team@company.com, product-team@company.com
- Kept in the loop
- Can read and comment, but not required
- Notified when RFC status changes
```

---

## Quick Reference

### RFC Section Checklist

```
Required Sections          | Optional Sections
---------------------------|-------------------
Problem Statement          | Executive Summary
Proposed Solution          | Background/Context
Alternatives Considered    | Technical Deep Dive
Risks & Mitigations        | Migration Plan
Approval/DACI              | Metrics & Monitoring
                           | Appendix/References
```

### RFC vs PRD vs ADR

```
Document | Author | Focus | Audience
---------|--------|-------|----------
PRD | PM | What & why | Cross-functional
RFC | Engineer | How (architecture) | Engineering
ADR | Engineer | Single decision | Engineering + future
```

### RFC Status Flow

```
Draft → In Review → Approved → Implemented
                       ↓
                   Rejected (with rationale)
                       ↓
                   Superseded (replaced by newer RFC)
```

### Documentation Tools

```
Tool | Best For | RFC Features
-----|----------|-------------
GitHub | Code-focused teams | Markdown, PR workflow, comments
Notion | Flexible workflows | Templates, comments, databases
Google Docs | Collaboration | Real-time editing, suggestions
Confluence | Enterprise | Versioning, permissions, templates
```

### Key Guidelines

```
✅ DO: Write for future engineers (historical context)
✅ DO: Document alternatives considered (why not X?)
✅ DO: Include trade-off analysis (pros/cons)
✅ DO: Define clear approval criteria (DACI)
✅ DO: Version your RFC and track changes

❌ DON'T: Skip the "why" (rationale is critical)
❌ DON'T: Prescribe without justification (explain trade-offs)
❌ DON'T: Write implementation code in RFC (high-level design only)
❌ DON'T: Ignore edge cases and failure modes
❌ DON'T: Forget to update RFC status after implementation
```

---

## Anti-Patterns

### Critical Violations

❌ **Solution Without Problem Statement**: Jumping to implementation without context
```markdown
# ❌ NEVER:
## Proposed Solution
We'll use Redis for caching and WebSockets for real-time updates.

# ✅ CORRECT:
## Problem Statement
API response times are >2 seconds due to repeated database queries (N+1 problem).
Users report slow dashboard loads, causing 15% drop in engagement.

## Proposed Solution
Implement Redis caching to reduce database load and improve response times to <200ms.
```

❌ **Single Option RFC**: Only presenting one solution without alternatives
✅ **Correct approach**: Always present 2-3 alternatives with trade-off analysis

### Common Mistakes

❌ **Missing Trade-Off Analysis**: "We'll use Postgres" without explaining why
```markdown
# ❌ Don't:
We'll use PostgreSQL for the database.

# ✅ Correct:
## Database Choice: PostgreSQL

**Alternatives Considered**:
1. **PostgreSQL** (chosen): ACID, complex queries, team familiarity
   - Pros: Strong consistency, rich features
   - Cons: Vertical scaling limits
2. **MongoDB**: Flexible schema, horizontal scaling
   - Pros: Easy sharding
   - Cons: No ACID, weaker queries (deal-breaker for billing)
3. **DynamoDB**: Fully managed, infinite scale
   - Pros: No ops burden
   - Cons: Vendor lock-in, expensive, limited queries

**Decision**: Postgres for ACID guarantees (financial transactions) and query flexibility.
```

❌ **Ignoring Risks**: No discussion of what could go wrong
✅ **Better**: Document risks and mitigation plans

❌ **Vague Approval Process**: "Get team feedback" instead of clear DACI
✅ **Better**: Define Driver, Approver, Contributors, Informed

---

## Related Skills

- `rfc-technical-design.md` - Deep dive on architecture proposals and technical design
- `rfc-consensus-building.md` - How to gather feedback and drive approval
- `rfc-decision-documentation.md` - ADRs, tracking decisions, post-implementation review
- `product/prd-structure-templates.md` - Product counterpart for product requirements
- `product/prd-technical-specifications.md` - PM's technical specs that feed into RFCs

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
