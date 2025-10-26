---
name: engineering-rfc-decision-documentation
description: Architecture Decision Records (ADRs), decision rationale, status tracking, and post-implementation review
---

# RFC Decision Documentation

**Scope**: Documenting architectural decisions, tracking status, maintaining decision history, and post-implementation review
**Lines**: ~320
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Creating Architecture Decision Records (ADRs) for significant decisions
- Documenting decision rationale (why we chose X over Y)
- Tracking RFC status (proposed, accepted, deprecated, superseded)
- Maintaining a changelog of RFC updates during review
- Using DACI framework to clarify decision-making roles
- Conducting post-implementation reviews (retrospectives on decisions)
- Managing decision deprecation (when decisions become obsolete)
- Creating searchable decision history for future reference

## Core Concepts

### Concept 1: Architecture Decision Records (ADRs)

**Purpose**: Lightweight documentation of significant architectural decisions
**Format**: Markdown file in `docs/adr/` or `adr/` directory
**Naming**: `ADR-NNN-title-in-kebab-case.md` (e.g., `ADR-005-use-postgres-over-mongodb.md`)

**When to Write an ADR**:
- Choosing technology (database, framework, cloud provider)
- Architectural pattern (microservices, monolith, event-driven)
- Security approach (OAuth, JWT, session-based auth)
- Data storage strategy (relational, NoSQL, caching)
- Any decision with long-term impact (hard to reverse)

**When NOT to Write an ADR**:
- Routine code changes (refactoring, bug fixes)
- Tactical decisions (variable naming, file organization)
- Decisions easily reversed (UI colors, button labels)

### Concept 2: Decision Status Lifecycle

**Status Flow**:
```
Proposed → Accepted → Implemented → [Deprecated | Superseded]
   ↓
Rejected
```

**Proposed**: Decision is being considered, not yet approved
**Accepted**: Decision approved, ready for implementation
**Implemented**: Decision has been built and deployed
**Deprecated**: Decision no longer valid (context changed)
**Superseded**: Replaced by newer decision (link to new ADR)
**Rejected**: Decision not accepted (document why)

### Concept 3: Decision Rationale Components

**Context**: What circumstances led to this decision?
**Options Considered**: What alternatives were evaluated?
**Decision**: What did we choose?
**Rationale**: Why did we choose this? (trade-offs, constraints)
**Consequences**: What are the positive, negative, neutral outcomes?
**Related Decisions**: What other decisions does this affect?

---

## Patterns

### Pattern 1: ADR Template (Minimal)

**When to use**:
- Documenting single architectural decision
- Quick reference for future engineers

```markdown
# ADR-012: Use JWT for API Authentication

**Date**: 2025-10-25
**Status**: Accepted
**Deciders**: @alice (backend lead), @bob (security)

## Context
We need to authenticate API requests from web and mobile clients.
Current system uses session cookies (server-side state, doesn't scale).

Requirements:
- Stateless authentication (no server-side sessions)
- Works for web and mobile
- Support for token expiration and refresh

## Decision
We will use **JWT (JSON Web Tokens)** for API authentication.

## Rationale
- **Stateless**: No server-side session storage (scales horizontally)
- **Cross-platform**: Works for web, mobile, and third-party API clients
- **Standard**: Well-documented, many libraries available
- **Expiration**: Built-in expiry (`exp` claim), supports refresh tokens

## Consequences

### Positive
- Horizontal scaling: No session replication needed
- Faster authentication: No database lookup per request
- Mobile-friendly: Tokens stored in app, not cookies

### Negative
- Token size: ~200 bytes vs 32-byte session ID (acceptable overhead)
- Revocation: Cannot invalidate token before expiry (mitigated with short TTL + refresh tokens)
- Secret management: Must protect JWT signing secret (use env vars, rotate regularly)

### Neutral
- Need to implement token refresh logic (standard pattern)
- Must validate tokens on every request (minimal CPU overhead)

## Alternatives Considered

### Session-based Auth (Current System)
**Pros**: Simple, easy to revoke
**Cons**: Server-side state, doesn't scale horizontally, not mobile-friendly
**Rejected**: Scalability requirement

### OAuth 2.0
**Pros**: Industry standard, supports third-party login
**Cons**: Complex for our use case (overkill for internal API)
**Deferred**: Consider for future third-party integrations

### API Keys
**Pros**: Simple, long-lived
**Cons**: No expiration, hard to rotate, security risk
**Rejected**: No built-in expiration mechanism
```

### Pattern 2: ADR with DACI Framework

**Use case**: Complex decision requiring clear accountability

```markdown
# ADR-018: Migrate from Monolith to Microservices

**Date**: 2025-10-25
**Status**: Accepted
**Last Updated**: 2025-10-26

## DACI

**Driver**: @alex (backend architect)
- Responsible for RFC and implementation plan

**Approver**: @cto
- Final decision authority
- Accountable for outcome

**Contributors**:
- @jordan (backend lead): Technical feasibility
- @taylor (DevOps): Infrastructure and deployment
- @sam (product): Product impact and timeline

**Informed**:
- engineering@company.com
- leadership@company.com

## Context
Current monolithic Rails app is becoming difficult to scale and maintain:
- Deployment takes 30+ minutes (affects release velocity)
- Tight coupling makes bug fixes risky (change one feature, break another)
- Team growth is bottlenecked (merge conflicts, slow tests)
- Database queries are slow (N+1 problems, no caching)

Goals:
- Improve deployment speed (target: <5 min per service)
- Enable independent team scaling (3 teams, 15 engineers)
- Reduce blast radius of bugs (isolate failures)

## Decision
We will **gradually migrate** from monolith to microservices using the Strangler Fig pattern.

**Phase 1**: Extract Auth Service (Q1 2025)
**Phase 2**: Extract User Service (Q2 2025)
**Phase 3**: Extract Project Service (Q3 2025)

## Rationale
- **Gradual migration**: Reduces risk vs big-bang rewrite
- **Strangler Fig**: Proven pattern (Netflix, Airbnb successfully used)
- **Start small**: Auth Service is well-isolated, low risk
- **Team autonomy**: Each service can be owned by a team (clear boundaries)

## Consequences

### Positive
- Faster deployments: 5 min per service vs 30 min monolith
- Independent scaling: Scale auth separately from other services
- Team autonomy: Teams can deploy independently (no coordination)
- Technology flexibility: Can use different languages/frameworks per service

### Negative
- Complexity: Distributed systems (service discovery, tracing)
- Cost: More infrastructure (3 services vs 1 monolith)
  - Estimated: $500/mo → $1,200/mo (2.4x increase)
- Debugging: Cross-service issues harder to debug (need distributed tracing)
- Data consistency: Eventual consistency (no ACID across services)

### Neutral
- Learning curve: Team needs to learn Kubernetes, service mesh
- Operational overhead: More services to monitor and maintain
- Network latency: Service-to-service calls add ~10ms overhead

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration takes too long | High | Timebox to 9 months, cancel if not on track |
| Data consistency issues | High | Use event sourcing for critical workflows |
| Cost overruns | Medium | Monitor monthly, optimize resource usage |
| Team expertise gap | Medium | Hire DevOps engineer, training budget |

## Alternatives Considered

### Continue with Monolith
**Pros**: No migration cost, simpler operations
**Cons**: Doesn't solve scaling, deployment, team autonomy problems
**Rejected**: Problems will worsen as team grows

### Modular Monolith
**Pros**: Logical separation, single deployment
**Cons**: Still have deployment bottleneck, doesn't solve scaling
**Considered**: Good middle ground, but doesn't meet goals

### Full Microservices Rewrite
**Pros**: Clean slate, modern architecture
**Cons**: High risk, 12+ months, business disruption
**Rejected**: Too risky, Strangler Fig is safer

## Implementation Plan
[Link to RFC-042: Microservices Migration Plan]

## Post-Implementation Review
**Scheduled**: 2026-01-15 (3 months after Phase 3 completion)
**Participants**: @alex, @jordan, @taylor, @sam, @cto
**Review Questions**:
- Did we achieve deployment speed goal? (<5 min per service)
- Did team autonomy improve? (measure: deploy frequency per team)
- What unexpected issues arose?
- Would we make the same decision again?
```

### Pattern 3: Decision Status Tracking

**Use case**: Maintaining history of decision lifecycle

```markdown
# ADR-005: Use PostgreSQL Over MongoDB

**Status**: Implemented
**Created**: 2025-01-15
**Accepted**: 2025-01-20
**Implemented**: 2025-02-10
**Last Reviewed**: 2025-10-25

## Status History

| Date | Status | Notes |
|------|--------|-------|
| 2025-01-15 | Proposed | Initial draft by @alice |
| 2025-01-17 | In Review | Feedback from @bob, @charlie |
| 2025-01-20 | Accepted | Approved by @cto after design review |
| 2025-02-10 | Implemented | Deployed to production |
| 2025-10-25 | Reviewed | Still valid, no changes needed |

## Review Notes (2025-10-25)
- **Still valid?**: Yes, Postgres continues to meet needs
- **Performance**: Query latency <50ms (p95), meets SLA
- **Scalability**: 1.5M users, no scaling issues yet
- **Would we choose differently?**: No, Postgres was correct choice
- **Next review**: 2026-04-25 (6 months)
```

### Pattern 4: Superseded Decision

**Use case**: When a decision is replaced by a newer one

```markdown
# ADR-003: Use Redis for Session Storage

**Status**: Superseded by ADR-012 (JWT Authentication)
**Created**: 2024-06-01
**Accepted**: 2024-06-10
**Implemented**: 2024-07-01
**Superseded**: 2025-10-25

## Superseded Notice
⚠️ **This decision is no longer active.**

**Superseded by**: [ADR-012: Use JWT for API Authentication](./ADR-012-use-jwt-for-api-authentication.md)

**Reason**: Migrated from session-based auth to stateless JWT auth for better scalability.

**Migration**: Completed 2025-10-25. Redis session store decommissioned.

---

## Original Decision (For Historical Reference)

### Context
We needed server-side session storage for user authentication...

[Keep original ADR content for historical reference]
```

### Pattern 5: Deprecated Decision

**Use case**: When context changes and decision is no longer valid

```markdown
# ADR-008: Deploy on Heroku

**Status**: Deprecated (No Longer Valid)
**Created**: 2023-03-15
**Accepted**: 2023-03-20
**Implemented**: 2023-04-01
**Deprecated**: 2025-06-15

## Deprecation Notice
⚠️ **This decision is no longer valid.**

**Deprecated Date**: 2025-06-15
**Reason**: Company standardized on AWS for all infrastructure.

**Current State**: All services migrated to AWS ECS (completed 2025-06-15).

**Replacement Decision**: [ADR-025: Standardize on AWS](./ADR-025-standardize-on-aws.md)

---

## Original Decision (For Historical Context)

### Context
We chose Heroku for fast iteration and minimal DevOps overhead...

[Keep original content for reference]
```

### Pattern 6: Rejected Decision

**Use case**: Documenting decisions that were NOT accepted

```markdown
# ADR-014: Use GraphQL for Public API (REJECTED)

**Status**: Rejected
**Created**: 2025-05-10
**Rejected**: 2025-05-20
**Deciders**: @alice (backend lead), @bob (CTO)

## Context
We evaluated GraphQL as an alternative to our REST API for the public API.

## Proposal (Rejected)
Replace REST API with GraphQL to reduce over-fetching and under-fetching.

## Rationale for Rejection

### Reasons NOT Accepted
1. **Team expertise**: No GraphQL experience on team (6+ month learning curve)
2. **Third-party integrations**: Most partners expect REST APIs (not GraphQL)
3. **Tooling**: Our monitoring/caching infrastructure is REST-optimized
4. **Client complexity**: Mobile apps would need GraphQL client library (adds weight)

### What We Learned
- Over-fetching is not a significant problem (bandwidth is cheap)
- Under-fetching can be solved with REST API design (compound endpoints)
- GraphQL benefits don't justify migration cost for our use case

## Alternative Chosen
Continue with REST API, improve with:
- Compound endpoints to reduce round-trips (e.g., `/users/:id?include=projects`)
- Field filtering via query params (e.g., `?fields=name,email`)
- Better API documentation (OpenAPI/Swagger)

## Related Decisions
- [ADR-006: REST API Design Principles](./ADR-006-rest-api-design-principles.md)

## Future Consideration
If we build a complex web app with diverse data needs, revisit GraphQL.
**Trigger**: If >10 clients request custom data views.
```

### Pattern 7: RFC Changelog

**Use case**: Tracking changes to RFC during review process

```markdown
# RFC-042: Real-Time Collaboration

[... RFC content ...]

---

## Changelog

### Version 1.3 (2025-10-26) - Final
- **Added**: Security section (rate limiting, auth)
- **Changed**: WebSocket server from Node.js to Go (better concurrency)
- **Reason**: Security review feedback from @charlie
- **Status**: Approved by @cto

### Version 1.2 (2025-10-25)
- **Added**: Failure mode analysis (Redis downtime)
- **Changed**: Rate limit from 100 to 200 ops/sec
- **Removed**: Audio/video chat (out of scope)
- **Reason**: Design review feedback from @jordan, @taylor

### Version 1.1 (2025-10-24)
- **Added**: Cost analysis ($500/mo at 10k users)
- **Changed**: Alternative approach section (expanded CRDTs analysis)
- **Reason**: @bob requested cost breakdown

### Version 1.0 (2025-10-23) - Initial Draft
- **Created**: Initial draft by @alex
- **Sections**: Problem, solution, architecture, alternatives

---

## Version History Table

| Version | Date | Author | Status | Key Changes |
|---------|------|--------|--------|-------------|
| 1.3 | 2025-10-26 | @alex | Approved | Security section added |
| 1.2 | 2025-10-25 | @alex | In Review | Failure modes, rate limit |
| 1.1 | 2025-10-24 | @alex | In Review | Cost analysis |
| 1.0 | 2025-10-23 | @alex | Draft | Initial draft |
```

### Pattern 8: Post-Implementation Review

**Use case**: Retrospective after decision is implemented

```markdown
# Post-Implementation Review: ADR-012 JWT Authentication

**Review Date**: 2025-10-25 (6 months post-implementation)
**Participants**: @alice (backend lead), @bob (security), @charlie (DevOps), @dana (product)

## Original Decision (Summary)
- **Date**: 2025-04-25
- **Decision**: Migrate from session-based auth to JWT
- **Rationale**: Stateless, scalable, mobile-friendly

## Implementation Timeline
- **Start**: 2025-05-01
- **Alpha**: 2025-05-15 (internal testing)
- **Beta**: 2025-06-01 (10% rollout)
- **GA**: 2025-06-15 (100% rollout)

## Success Metrics (Actual vs Target)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| API latency reduction | -20ms (p95) | -35ms | ✅ Exceeded |
| Horizontal scaling | 3x capacity | 5x capacity | ✅ Exceeded |
| Failed logins (migration) | <1% | 0.3% | ✅ Met |
| Support tickets (auth issues) | <50 | 12 | ✅ Exceeded |

## What Went Well
1. **Smooth migration**: Dual-write period prevented data loss
2. **Performance**: Better than expected (-35ms vs -20ms target)
3. **Scalability**: 5x capacity increase (vs 3x target)
4. **Minimal user impact**: Only 12 support tickets (vs 50 expected)

## What Went Poorly
1. **Token refresh complexity**: Took 2 weeks longer than estimated
   - Root cause: Edge cases in refresh token rotation
   - Mitigation: Added integration tests for refresh flows
2. **Secret rotation**: Manual process (should be automated)
   - Action item: Automate JWT secret rotation (ADR-030)
3. **Mobile token storage**: Security concern (tokens in local storage)
   - Action item: Migrate to secure keychain (iOS) and keystore (Android)

## Unexpected Challenges
- **Third-party integrations**: 3 partners needed JWT support (undiscovered dependency)
  - Resolution: Provided migration guide and support
- **Token size**: 200-byte tokens caused issues with legacy proxies
  - Resolution: Whitelisted JWT header in proxy config

## Lessons Learned
1. **Dual-write is critical**: Prevented data loss during migration
2. **Test refresh flows**: Edge cases are tricky, need comprehensive tests
3. **Automate ops**: Secret rotation should be automated from day 1
4. **Mobile security**: Token storage needs platform-specific solutions

## Would We Make Same Decision?
**Yes**, JWT was the correct choice.

**Rationale**:
- Performance and scalability benefits exceeded expectations
- Migration was smooth despite token refresh complexity
- Would address mobile token storage earlier next time

## Follow-Up Actions
- [ ] **ADR-030**: Automate JWT secret rotation (assigned: @charlie)
- [ ] **ADR-031**: Migrate mobile to secure token storage (assigned: @alice)
- [ ] **Documentation**: Update API docs with JWT best practices

## Next Review
**Scheduled**: 2026-04-25 (6 months)
**Trigger**: If token-related security incidents occur, review immediately
```

---

## Quick Reference

### ADR Checklist

```
Required Sections | Optional Sections
------------------|------------------
Date              | DACI roles
Status            | Status history
Context           | Related decisions
Decision          | Risks & mitigations
Rationale         | Implementation plan
Consequences      | Post-implementation review
Alternatives      |
```

### Decision Status Values

```
Status | Meaning | Next Action
-------|---------|------------
Proposed | Being considered | Seek feedback, approve/reject
Accepted | Approved | Implement
Implemented | Deployed | Monitor, review
Deprecated | No longer valid | Link to replacement
Superseded | Replaced | Link to new decision
Rejected | Not accepted | Document why
```

### When to Write an ADR

```
Write ADR | Don't Write ADR
----------|----------------
Technology choice (DB, cloud) | Routine code changes
Architectural pattern | Variable naming
Security approach | UI colors/layout
Data strategy | Bug fixes
Hard-to-reverse decisions | Easily reversible decisions
```

### Post-Implementation Review Questions

```
Question | Purpose
---------|--------
Did we achieve goals? | Measure success
What went well? | Identify strengths
What went poorly? | Learn from mistakes
Would we decide the same way? | Validate decision
What's next? | Plan follow-up actions
```

### Key Guidelines

```
✅ DO: Document why, not just what (rationale is critical)
✅ DO: Include alternatives considered (why not X?)
✅ DO: Track status changes over time
✅ DO: Conduct post-implementation reviews (learn from outcomes)
✅ DO: Link related decisions (create decision graph)

❌ DON'T: Skip consequences (positive, negative, neutral)
❌ DON'T: Forget to update status (proposed → accepted → implemented)
❌ DON'T: Delete superseded ADRs (keep for historical context)
❌ DON'T: Write ADRs for trivial decisions
❌ DON'T: Ignore post-implementation learnings
```

---

## Anti-Patterns

### Critical Violations

❌ **Decision Without Rationale**: "We chose X" without explaining why
```markdown
# ❌ NEVER:
## Decision
We will use PostgreSQL.

# ✅ CORRECT:
## Decision
We will use PostgreSQL.

## Rationale
- ACID transactions required for billing (compliance)
- Rich query capabilities (JOINs, window functions)
- Team expertise (all backend engineers know SQL)
- Proven scalability (read replicas, partitioning)

## Alternatives Considered
- MongoDB: Flexible schema, but no ACID (rejected)
- DynamoDB: Managed, but vendor lock-in (rejected)
```

❌ **No Consequences Section**: Ignoring negative outcomes
✅ **Correct approach**: Document positive, negative, and neutral consequences

### Common Mistakes

❌ **Deleting Superseded Decisions**: Removing historical context
```markdown
# ❌ Don't:
[Delete ADR-003 after it's superseded]

# ✅ Correct:
Keep ADR-003 with "Superseded" status and link to ADR-012
```

❌ **No Status Updates**: Decision stays "Proposed" even after implementation
✅ **Better**: Update status to Accepted → Implemented with dates

❌ **Skipping Post-Implementation Review**: No retrospective on decision
```markdown
# ❌ Don't:
Implement decision → Move on to next task

# ✅ Correct:
Implement decision → Wait 3-6 months → Conduct review → Document learnings
```

❌ **ADR for Trivial Decisions**: "ADR-099: Use camelCase for variable names"
✅ **Better**: ADRs for significant, hard-to-reverse decisions only

---

## Related Skills

- `rfc-structure-format.md` - RFC document templates and formatting
- `rfc-technical-design.md` - Architecture proposals and technical design
- `rfc-consensus-building.md` - Driving approval and building consensus
- `product/prd-structure-templates.md` - Product decision documentation (PRDs)

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
