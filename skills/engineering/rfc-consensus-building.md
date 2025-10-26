---
name: engineering-rfc-consensus-building
description: Stakeholder identification, feedback collection, consensus building, and approval processes for RFCs
---

# RFC Consensus Building

**Scope**: Techniques for identifying stakeholders, collecting feedback, building consensus, and driving RFC approval
**Lines**: ~280
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Identifying who needs to review and approve your RFC
- Collecting feedback from engineers, architects, and stakeholders
- Addressing concerns and incorporating feedback into RFC
- Facilitating design review meetings and Q&A sessions
- Handling disagreements and driving consensus
- Using decision frameworks (DACI, RACI) to clarify roles
- Escalating decisions when consensus cannot be reached
- Managing the RFC approval process from draft to approved

## Core Concepts

### Concept 1: Stakeholder Identification

**Categories of Stakeholders**:
- **Authors**: Write and own the RFC
- **Reviewers**: Provide feedback and expertise (SMEs)
- **Approvers**: Have veto power, make final decision
- **Implementers**: Engineers who will build the solution
- **Informed**: Need to know, but not involved in decision

**Identification Questions**:
- Who is affected by this change? (users, teams, systems)
- Who has expertise needed for review? (security, performance, data)
- Who has authority to approve? (tech lead, architect, director)
- Who will implement this? (frontend, backend, DevOps)
- Who needs to be informed? (adjacent teams, leadership)

### Concept 2: Feedback Collection Strategies

**Async Feedback** (Scale to many reviewers):
- Comments in Google Docs or GitHub PR
- Slack threads for quick questions
- Email for formal approvals

**Sync Feedback** (Deep discussions):
- Design review meetings (1 hour, 5-10 people)
- Office hours (open Q&A slots)
- One-on-one walkthroughs (for key stakeholders)

**Structured Feedback**:
- Request specific feedback areas (e.g., "Review security section")
- Set deadlines (e.g., "Please review by Friday")
- Use comment templates (e.g., "Blocking concern" vs "Nice-to-have")

### Concept 3: DACI Decision Framework

**Driver**: Owns the RFC and drives to decision
- Responsible for drafting, collecting feedback, updating RFC
- Facilitates meetings and discussions
- Proposes decision to Approver

**Approver**: Makes final decision
- Has veto power
- Accountable for outcome
- Typically tech lead, architect, or engineering manager

**Contributors**: Provide input and feedback
- Subject matter experts (security, performance, data)
- Affected teams (frontend, backend, DevOps)
- No veto power, but concerns must be addressed

**Informed**: Kept in the loop
- Adjacent teams, leadership
- Notified when decision is made
- Can comment but not required

---

## Patterns

### Pattern 1: Stakeholder Mapping for RFC

**When to use**:
- Starting RFC process
- Ensuring all affected parties are included

```markdown
## Stakeholder Map: Real-Time Collaboration RFC

### DACI Roles

**Driver**: @alex (backend engineer)
- Owns RFC creation and updates
- Drives consensus and decision

**Approver**: @engineering-lead (CTO)
- Final decision authority
- Approves or rejects RFC

**Contributors** (Must Review):
- @jordan (backend): WebSocket server design
- @taylor (frontend): Client-side editor integration
- @sam (product): Product requirements alignment
- @charlie (security): Authentication and rate limiting
- @dana (DevOps): Infrastructure and scaling plan

**Informed** (Notified, Optional Review):
- engineering@company.com (all engineers)
- product@company.com (product team)
- leadership@company.com (exec team)

### Review Timeline
- **Draft**: 2025-10-25 (author completes)
- **Review Start**: 2025-10-26 (invite contributors)
- **Feedback Deadline**: 2025-11-01 (5 business days)
- **Design Review Meeting**: 2025-11-02 (1 hour, sync discussion)
- **Final Decision**: 2025-11-03 (approver decides)

### Communication Plan
- **Draft ready**: Slack #engineering channel, tag contributors
- **Feedback reminder**: Email 2 days before deadline
- **Meeting invite**: Calendar invite with RFC link in description
- **Decision announcement**: Slack + email to "Informed" group
```

### Pattern 2: Feedback Collection Template

**Use case**: Requesting structured feedback from reviewers

```markdown
## Review Request: RFC-042 Real-Time Collaboration

Hi @jordan, @taylor, @charlie,

I've completed the draft for **RFC-042: Real-Time Collaboration**.
Please review by **Friday, Nov 1** and provide feedback.

**RFC Link**: [Google Doc / GitHub PR]

**Specific Feedback Needed**:
- @jordan (Backend): Review WebSocket server design (Section 3.2)
- @taylor (Frontend): Validate client editor integration (Section 3.3)
- @charlie (Security): Review auth and rate limiting (Section 5)

**Feedback Format**:
- **Blocking Concern**: "This must be addressed before approval"
- **Strong Suggestion**: "Recommend changing, but not blocking"
- **Question**: "Need clarification"
- **Nice-to-Have**: "Optional improvement"

**Design Review Meeting**: Tuesday, Nov 2 at 2pm (1 hour)
- We'll discuss blocking concerns and unresolved questions
- Please add questions to RFC comments beforehand

Thanks!
@alex
```

### Pattern 3: Design Review Meeting Agenda

**Use case**: Facilitating effective sync discussion

```markdown
## Design Review: RFC-042 Real-Time Collaboration

**Date**: 2025-11-02, 2:00 PM - 3:00 PM
**Location**: Zoom [link] / Conference Room B
**Attendees**: @alex (driver), @jordan, @taylor, @charlie, @sam, @engineering-lead

### Agenda (60 minutes)

**1. Context & Goals (5 min)** - @alex
- Briefly recap problem statement and proposed solution
- Clarify goals: real-time editing, <200ms latency, 50 concurrent users

**2. Architecture Overview (10 min)** - @alex
- Walk through architecture diagram (C4 Level 2)
- Explain WebSocket + OT + Redis approach
- Q&A on high-level design

**3. Blocking Concerns (20 min)** - All
- **Concern 1** (@charlie): "How do we prevent DoS attacks on WebSocket server?"
  - Proposed mitigation: Rate limiting (100 ops/sec per user)
  - Decision: Add to RFC Section 5.2
- **Concern 2** (@jordan): "What happens if Redis goes down?"
  - Proposed mitigation: Fallback to Postgres snapshots, auto-reconnect
  - Decision: Add to RFC Section 6.3 (Failure Modes)

**4. Alternative Approaches (15 min)** - All
- Discussion: Why OT over CRDTs?
- Discussion: Why Redis over in-memory state?
- Ensure alternatives are adequately documented

**5. Open Questions (5 min)** - All
- Q: Should we support audio/video chat? → Decision: No, defer to Q2
- Q: Max document size? → Decision: 50k chars, show warning

**6. Next Steps & Decision (5 min)** - @engineering-lead
- @alex: Update RFC with feedback by Nov 3
- @engineering-lead: Review updated RFC and approve by Nov 4
- If approved: Start implementation in Sprint 12

### Meeting Notes
[Collaborative doc for notes during meeting]
```

### Pattern 4: Handling Disagreements

**Use case**: Driving consensus when reviewers disagree

```markdown
## Disagreement: Database Choice (Postgres vs MongoDB)

### Positions
**@alice (Backend Lead)**: Prefers PostgreSQL
- Rationale: ACID transactions required for billing
- Concern: MongoDB lacks strong consistency guarantees

**@bob (Data Engineer)**: Prefers MongoDB
- Rationale: Flexible schema for rapidly changing product
- Concern: Postgres schema migrations are slow and risky

### Discussion Framework

**Step 1: Clarify Requirements**
- Q: Do we need ACID for billing? (Legal/compliance requirement?)
  - Answer: Yes, financial regulations require strong consistency
- Q: How often do we change schema?
  - Answer: ~2-3 times per quarter (moderate frequency)

**Step 2: Evaluate Trade-offs**
| Requirement | Postgres | MongoDB | Winner |
|-------------|----------|---------|--------|
| ACID for billing | ✅ Strong | ❌ Weak | Postgres |
| Schema flexibility | ⚠️ Migrations | ✅ Flexible | MongoDB |
| Team expertise | ✅ High | ⚠️ Medium | Postgres |
| Query richness | ✅ SQL | ⚠️ Limited | Postgres |

**Step 3: Seek Compromise**
- Hybrid approach: Postgres for billing, MongoDB for user-generated content?
  - Rejected: Too complex for small team (2 databases to maintain)
- Use Postgres with JSONB for flexible fields?
  - Accepted: JSONB columns provide schema flexibility where needed

**Step 4: Decision**
- **Chosen**: PostgreSQL with JSONB for flexible fields
- **Rationale**: ACID is non-negotiable, JSONB solves schema flexibility
- **Concession**: Invest in migration tooling (Alembic) to reduce risk

**Step 5: Document Decision**
- Update RFC Section 4 (Alternatives Considered)
- Create ADR-007: "Why Postgres over MongoDB"
- @bob: Acknowledge concern addressed, approve RFC
```

### Pattern 5: Escalation Process

**Use case**: When consensus cannot be reached

```markdown
## Escalation: Real-Time Collaboration - Performance Concerns

### Deadlock Scenario
- @jordan (Backend): "OT is too complex, will cause bugs"
- @alex (Driver): "OT is industry standard, proven by Google Docs"
- **Cannot reach consensus** after 2 design reviews

### Escalation Steps

**Step 1: Document Positions**
- @jordan's concern: OT has steep learning curve, risk of bugs
  - Evidence: 5 similar projects had OT bugs in first 6 months
- @alex's position: OT is only proven solution for text editing
  - Evidence: Google Docs, Figma, Notion all use OT successfully

**Step 2: Identify Decision Criteria**
- What matters most: correctness, time-to-market, or team expertise?
  - Product says: Time-to-market (ship in Q1)
  - Engineering says: Correctness (no data loss)

**Step 3: Escalate to Approver**
- Present both positions to @engineering-lead (Approver)
- Include: Trade-off matrix, evidence, recommended decision

**Step 4: Approver Decision**
- @engineering-lead: "Correctness is critical, accept slower time-to-market"
- **Decision**: Use OT, allocate 2 extra weeks for thorough testing
- **Mitigation**: Hire consultant with OT expertise (reduce risk)

**Step 5: Document and Move Forward**
- Update RFC with decision rationale
- @jordan: Acknowledge concern heard, move forward with team
- Plan: Weekly check-ins on OT implementation progress
```

### Pattern 6: Incorporating Feedback

**Use case**: Updating RFC based on review comments

```markdown
## Feedback Integration Log

### Feedback Received (2025-11-01)

**@jordan (Backend)**: "What's the fallback if Redis goes down?"
- **Type**: Blocking concern
- **Action**: Added Section 6.3 (Failure Modes)
- **Resolution**: Fallback to Postgres snapshots, auto-reconnect with backoff

**@taylor (Frontend)**: "How do we display cursors for 50 users?"
- **Type**: Question
- **Action**: Added Section 3.4 (Client UI Design)
- **Resolution**: Show top 10 active users, aggregate others as "+40 more"

**@charlie (Security)**: "Rate limiting is too low (100 ops/sec)"
- **Type**: Strong suggestion
- **Action**: Updated Section 5.2 (Rate Limiting)
- **Resolution**: Changed to 200 ops/sec (allow burst typing), with burst allowance

**@sam (Product)**: "Should we support markdown formatting?"
- **Type**: Nice-to-have
- **Action**: Added to "Future Work" section
- **Resolution**: Defer to v2, focus on plain text for MVP

### Changes Made
- ✅ Section 6.3 added: Failure mode analysis
- ✅ Section 3.4 added: Cursor display strategy
- ✅ Section 5.2 updated: Rate limit 100→200 ops/sec
- ✅ Future Work section: Markdown formatting for v2

### Changelog Entry
```
## Version 1.2 (2025-11-01)
- Added failure mode analysis (Redis downtime)
- Clarified cursor display strategy (top 10 users)
- Increased rate limit to 200 ops/sec per feedback
- Moved markdown formatting to future work
```

### Re-Review Request
"I've updated the RFC based on your feedback. Please review v1.2 and confirm blocking concerns are addressed."
```

### Pattern 7: Approval Checklist

**Use case**: Ensuring all approval criteria are met

```markdown
## RFC Approval Checklist

### Pre-Approval Requirements
- [x] All contributors have reviewed RFC
- [x] Blocking concerns addressed
- [x] Alternatives documented and evaluated
- [x] Risks and mitigations identified
- [x] Design review meeting completed (2025-11-02)
- [x] RFC updated with feedback (v1.2)
- [x] Approver has reviewed final version

### Contributor Sign-offs
- [x] @jordan (Backend): Approved (2025-11-01)
  - Comment: "Failure modes addressed, looks good"
- [x] @taylor (Frontend): Approved (2025-11-01)
  - Comment: "Cursor strategy is clear, ready to implement"
- [x] @charlie (Security): Approved with caveat (2025-11-01)
  - Comment: "Approved. Monitor rate limit, may need adjustment post-launch"
- [x] @sam (Product): Approved (2025-11-02)
  - Comment: "Aligned with product goals, ship it!"

### Approver Decision
- [x] @engineering-lead: **APPROVED** (2025-11-03)
  - Comment: "Well-documented, consensus reached, proceed with implementation"

### Next Steps
- [x] Update RFC status: Draft → Approved
- [x] Announce decision to "Informed" group (Slack #engineering)
- [ ] Create implementation tasks (Jira/Linear)
- [ ] Kick off Sprint 12 implementation
```

### Pattern 8: Post-Approval Communication

**Use case**: Announcing decision and next steps

```markdown
## Announcement: RFC-042 Real-Time Collaboration - APPROVED

**To**: engineering@company.com, product@company.com
**From**: @alex
**Date**: 2025-11-03

Hi team,

Great news! **RFC-042: Real-Time Collaboration** has been approved by @engineering-lead.

### Summary
We'll be implementing real-time collaborative editing using WebSocket + Operational Transform (OT) + Redis. This will enable 2-50 users to edit documents simultaneously with <200ms latency.

### What's Next
- **Implementation**: Starts Sprint 12 (Nov 6)
- **Timeline**: MVP targeted for Q1 2025
- **Team**: @alex (lead), @jordan (backend), @taylor (frontend)

### Key Decisions
- **Tech Stack**: WebSocket (ws), OT (ot.js), Redis, Postgres
- **Alternatives Rejected**: CRDTs (larger payloads), polling (high latency)
- **Risks Mitigated**: Redis failover, rate limiting, OT testing

### How You Can Help
- **Try the alpha** (internal only, Week 3-4 of Sprint 12)
- **Provide feedback** on UX and performance
- **Report bugs** in #collab-bugs channel

### RFC Document
Read the full RFC here: [link to Google Doc / GitHub]

Questions? Ping me in Slack or join office hours (Fridays 2-3pm).

Thanks to everyone who reviewed and provided feedback!

@alex
```

---

## Quick Reference

### Stakeholder Identification

```
Role | Responsibility | Example
-----|----------------|--------
Driver | Owns RFC, drives consensus | RFC author
Approver | Final decision authority | Tech lead, CTO
Contributors | Provide feedback, SMEs | Backend lead, security
Implementers | Build the solution | Frontend/backend engineers
Informed | Kept in loop | Adjacent teams, leadership
```

### Feedback Types

```
Type | Definition | Action Required
-----|------------|------------------
Blocking Concern | Must be addressed | Update RFC, re-review
Strong Suggestion | Recommend changing | Consider, justify if rejected
Question | Need clarification | Answer in RFC or comments
Nice-to-Have | Optional improvement | Defer to future work
```

### DACI Framework

```
DACI Role | Power | Count
----------|-------|------
Driver | Drives process | 1 person
Approver | Veto power | 1 person (or small group)
Contributors | Feedback, no veto | 3-10 people
Informed | Notified | Unlimited
```

### Key Guidelines

```
✅ DO: Identify all stakeholders upfront (DACI framework)
✅ DO: Set clear deadlines for feedback
✅ DO: Facilitate design review meetings for sync discussion
✅ DO: Address blocking concerns before seeking approval
✅ DO: Document disagreements and how they were resolved

❌ DON'T: Skip stakeholder identification (surprises later)
❌ DON'T: Ignore feedback (causes resentment, delays)
❌ DON'T: Rush to approval (consensus takes time)
❌ DON'T: Avoid conflict (address disagreements head-on)
❌ DON'T: Forget to announce decision (inform stakeholders)
```

---

## Anti-Patterns

### Critical Violations

❌ **Skipping Stakeholder Identification**: Not involving key reviewers
```markdown
# ❌ NEVER:
Write RFC → Send to engineering-lead for approval → Skip team review

# ✅ CORRECT:
Write RFC → Identify stakeholders (DACI) → Collect feedback → Address concerns → Seek approval
```

❌ **Ignoring Blocking Concerns**: Pushing for approval despite unresolved issues
✅ **Correct approach**: Address all blocking concerns, update RFC, re-review

### Common Mistakes

❌ **No Feedback Deadline**: Open-ended review period
```markdown
# ❌ Don't:
"Please review when you have time"

# ✅ Correct:
"Please review by Friday, Nov 1 (5 business days)"
```

❌ **Async-Only for Complex RFCs**: No sync discussion for controversial topics
✅ **Better**: Schedule design review meeting for deep discussions

❌ **Defensive Responses to Feedback**: Arguing instead of listening
```markdown
# ❌ Don't:
Reviewer: "This won't scale"
Author: "You're wrong, it will"

# ✅ Correct:
Reviewer: "This won't scale"
Author: "Can you elaborate? What scale are you concerned about?"
[Discuss, update RFC with scaling plan]
```

❌ **No Decision Documentation**: Approving without documenting rationale
✅ **Better**: Update RFC with decision, rationale, and next steps

---

## Related Skills

- `rfc-structure-format.md` - RFC document templates and formatting
- `rfc-technical-design.md` - Designing architecture and evaluating alternatives
- `rfc-decision-documentation.md` - Documenting decisions and ADRs
- `product/prd-requirements-gathering.md` - Stakeholder interviews (product side)

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
