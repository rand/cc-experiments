---
name: product-prd-structure-templates
description: PRD document structure, templates, and best practices for product requirements documentation
---

# PRD Structure & Templates

**Scope**: Comprehensive guide to PRD formats, sections, templates, and documentation best practices
**Lines**: ~320
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Writing a new Product Requirements Document from scratch
- Standardizing PRD format across a product team
- Choosing between lightweight and comprehensive PRD templates
- Defining what sections belong in a PRD vs RFC
- Setting up PRD templates in Notion, Confluence, or Google Docs
- Establishing PRD review and approval workflows
- Training PMs or teams on effective PRD writing
- Migrating from informal specs to structured PRDs

## Core Concepts

### Concept 1: PRD Purpose and Audience

**Primary Goals**:
- Align stakeholders on problem, goals, and solution
- Provide engineering with clear requirements for implementation
- Document decisions and rationale for future reference
- Define success metrics and validation criteria

**Key Audiences**:
- Engineering: needs technical requirements, edge cases, acceptance criteria
- Design: needs user flows, interaction patterns, visual requirements
- Leadership: needs business justification, metrics, timeline
- QA: needs testable criteria, edge cases, validation approach
- Marketing/Sales: needs feature benefits, target users, competitive positioning

### Concept 2: Standard PRD Sections

**Essential Sections** (every PRD must have):
- **Problem Statement**: What problem are we solving? Why now?
- **Goals & Success Metrics**: What does success look like? How do we measure it?
- **Requirements**: What must the solution do? (Functional, non-functional, constraints)
- **Out of Scope**: What are we explicitly NOT doing?

**Common Optional Sections**:
- Background/Context: Market research, user insights, competitive analysis
- User Stories/Scenarios: Concrete examples of user workflows
- Design Mocks: Visual representation of solution
- Technical Considerations: Architecture notes, dependencies, risks
- Timeline/Milestones: Key dates, phases, launch plan
- Open Questions: Unresolved items requiring further discussion

### Concept 3: PRD Formats by Use Case

**One-Pager PRD** (1-2 pages):
- Use for: Small features, quick experiments, internal tools
- Focus: Problem, proposed solution, success metrics
- Audience: Small team, fast iteration

**Lightweight PRD** (3-5 pages):
- Use for: Medium features, iterative development, established products
- Focus: Problem, goals, requirements, user stories
- Audience: Cross-functional team, regular cadence

**Comprehensive PRD** (10+ pages):
- Use for: Major initiatives, new products, complex integrations
- Focus: All sections, detailed analysis, multiple alternatives
- Audience: Leadership, multiple teams, long-term planning

---

## Patterns

### Pattern 1: One-Pager PRD Template

**When to use**:
- Quick iteration, small scope
- Internal tools or experiments
- Well-understood problem space

```markdown
# [Feature Name] - PRD One-Pager

**Author**: [Name] | **Date**: 2025-10-25 | **Status**: Draft

## Problem
What user problem are we solving? Why is this important now?

[2-3 sentences maximum]

## Solution
What are we building to solve this problem?

[3-5 bullet points describing key functionality]

## Success Metrics
How will we know if this succeeded?

- Metric 1: [e.g., 20% increase in user activation]
- Metric 2: [e.g., <5% error rate]
- Metric 3: [e.g., Ship by Q1 2025]

## Requirements
Must-haves for launch:
- [ ] Requirement 1
- [ ] Requirement 2
- [ ] Requirement 3

## Out of Scope
What we're NOT doing (at least not yet):
- Thing 1
- Thing 2
```

**Benefits**:
- Fast to write and review
- Forces focus on essentials
- Easy to keep updated

### Pattern 2: Lightweight PRD Template

**Use case**: Standard feature development with established processes

```markdown
# [Feature Name] - PRD

**Author**: [Name] | **Reviewers**: [Names] | **Date**: 2025-10-25
**Status**: Draft | Review | Approved

## Problem Statement
What problem exists today? Who experiences it? Why is it painful?

[Provide context: user quotes, data, competitive gaps]

## Goals
What are we trying to achieve?

1. **Primary Goal**: [e.g., Increase user retention by 15%]
2. **Secondary Goals**: [e.g., Reduce support tickets, improve NPS]

## Success Metrics
How will we measure success?

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| [KPI 1] | [baseline] | [goal] | [date] |
| [KPI 2] | [baseline] | [goal] | [date] |

## User Stories
Who will use this and how?

**As a** [user type]
**I want** [capability]
**So that** [benefit]

[Include 3-5 key user stories]

## Requirements

### Functional Requirements
- [ ] FR1: System must support [capability]
- [ ] FR2: Users can [action]
- [ ] FR3: [Specific behavior]

### Non-Functional Requirements
- [ ] NFR1: Performance: [e.g., <200ms response time]
- [ ] NFR2: Security: [e.g., SOC 2 compliant data handling]
- [ ] NFR3: Accessibility: [e.g., WCAG 2.1 AA]

### Constraints
- Must integrate with [existing system]
- Cannot exceed [budget/timeline]
- Must support [browsers/platforms]

## Out of Scope
What we're explicitly NOT doing:
- [Feature/capability that's tempting but out of scope]
- [Platform/integration we're deferring]

## Open Questions
- [ ] Question 1: [Issue needing resolution]
- [ ] Question 2: [Decision pending stakeholder input]

## Approval
- [ ] Engineering: [Name]
- [ ] Design: [Name]
- [ ] Product Lead: [Name]
```

### Pattern 3: Comprehensive PRD Template

**Use case**: Major initiatives, new products, complex features

```markdown
# [Product/Feature Name] - Comprehensive PRD

## Document Metadata
- **Author**: [Name, Role]
- **Stakeholders**: [List all reviewers and approvers]
- **Created**: 2025-10-25
- **Last Updated**: 2025-10-25
- **Status**: Draft | In Review | Approved | In Development
- **Version**: 1.0

## Executive Summary
[2-3 paragraph summary of entire PRD for leadership]

## Background & Context
Why are we doing this? What's the broader context?

### Market Context
- Competitive landscape
- Market trends
- Customer demand signals

### User Research
- Interview insights (n=X)
- Survey results (n=Y)
- Usage data analysis

## Problem Statement
### Current State
What's happening today? What's the pain?

### Desired State
What should the experience be?

### Gap Analysis
What's missing to get from current to desired state?

## Goals & Objectives
### Business Goals
1. [Revenue, growth, retention goal]
2. [Market positioning goal]

### User Goals
1. [User capability or outcome]
2. [User experience improvement]

### Success Metrics
| Category | Metric | Current | Target | Measurement |
|----------|--------|---------|--------|-------------|
| Business | [KPI] | [value] | [value] | [how] |
| User | [KPI] | [value] | [value] | [how] |
| Operational | [KPI] | [value] | [value] | [how] |

## User Personas & Scenarios
### Primary Persona: [Name]
- **Role**: [Job title]
- **Goals**: [What they want to achieve]
- **Pain Points**: [Current frustrations]
- **Context**: [When/where they'll use this]

### User Scenarios
1. **Scenario 1**: [Concrete example walkthrough]
2. **Scenario 2**: [Another key workflow]

## Requirements

### Functional Requirements
#### Core Functionality
- FR1: [Requirement]
  - Acceptance: [GIVEN-WHEN-THEN criteria]
- FR2: [Requirement]
  - Acceptance: [Criteria]

#### Secondary Features
- FR3: [Nice-to-have capability]

### Non-Functional Requirements
- NFR1: **Performance**: [Specific targets]
- NFR2: **Security**: [Compliance, data handling]
- NFR3: **Scalability**: [Growth expectations]
- NFR4: **Accessibility**: [Standards compliance]
- NFR5: **Localization**: [Languages, regions]

### Technical Constraints
- Must integrate with [system/API]
- Cannot change [existing behavior]
- Must support [platforms/browsers]

## Design & User Experience
[Link to Figma/design files]

### Key User Flows
1. [Flow 1 description with screenshots]
2. [Flow 2 description]

### Design Principles
- Principle 1: [e.g., "Progressive disclosure"]
- Principle 2: [e.g., "Mobile-first"]

## Technical Considerations
### Architecture Notes
[High-level technical approach - collaborate with eng]

### Dependencies
- Internal: [Team/system dependencies]
- External: [Third-party services, APIs]

### Risks & Mitigations
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [Risk 1] | High/Med/Low | High/Med/Low | [Plan] |

## Launch & Rollout
### Phases
1. **Alpha** (Week 1-2): Internal testing
2. **Beta** (Week 3-4): 10% of users
3. **GA** (Week 5): Full rollout

### Go-to-Market
- Marketing: [Campaign approach]
- Sales enablement: [Training, materials]
- Support: [Documentation, training]

## Out of Scope
Explicitly NOT included in this PRD:
- [Feature tempting to include but deferred]
- [Platform/integration postponed]
- [Capability for future iteration]

## Open Questions & Decisions
- [ ] **Q1**: [Question requiring answer before approval]
  - Decision: [TBD or decided]
- [ ] **Q2**: [Another open item]

## Appendix
### Research Data
[Link to user research, surveys, analytics]

### Competitive Analysis
[Comparison matrix of competitor features]

### Glossary
- **Term 1**: Definition
- **Term 2**: Definition
```

### Pattern 4: PRD Versioning and Changelog

**Use case**: Tracking changes during review and development

```markdown
## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.2 | 2025-10-25 | [Name] | Updated success metrics based on eng feedback |
| 1.1 | 2025-10-24 | [Name] | Added technical constraints section |
| 1.0 | 2025-10-23 | [Name] | Initial draft |

## Changelog
- **2025-10-25**: Removed "real-time sync" from scope per eng constraint discussion
- **2025-10-24**: Added NFR for WCAG 2.1 AA compliance per design review
```

---

## Quick Reference

### PRD Section Checklist

```
Required Sections          | Optional Sections
---------------------------|-------------------
Problem Statement          | Background/Context
Goals & Success Metrics    | User Personas
Requirements (Functional)  | Design Mocks
Out of Scope               | Technical Notes
                           | Timeline/Milestones
                           | Competitive Analysis
```

### Documentation Tools Comparison

```
Tool          | Best For                    | PRD Features
--------------|-----------------------------|--------------
Notion        | Startups, flexible workflows| Templates, comments, databases
Confluence    | Enterprise, integration     | Versioning, permissions, JIRA link
Google Docs   | Collaboration, accessibility| Comments, suggestions, easy sharing
Linear        | Dev-focused teams           | Issue linking, roadmap integration
Markdown+Git  | Engineering-led orgs        | Version control, code-like workflow
```

### Key Guidelines

```
✅ DO: Write for multiple audiences (eng, design, leadership)
✅ DO: Include concrete success metrics (not "improve UX")
✅ DO: Be specific about scope AND out-of-scope
✅ DO: Version your PRD and track changes
✅ DO: Link to supporting docs (research, designs, data)

❌ DON'T: Prescribe technical implementation (that's RFC territory)
❌ DON'T: Write requirements as user stories alone (need acceptance criteria)
❌ DON'T: Skip the "why" (problem statement is critical)
❌ DON'T: Make it longer than necessary (choose right template)
❌ DON'T: Forget to update PRD during development (living document)
```

---

## Anti-Patterns

### Critical Violations

❌ **Solution-First PRD**: Starting with "We're building X" without explaining the problem
```markdown
# ❌ NEVER:
## What We're Building
We're adding a real-time chat feature to the dashboard.

# ✅ CORRECT:
## Problem Statement
Users currently wait 24+ hours for email responses to time-sensitive questions,
causing frustration (NPS -15 for support experience) and 30% of users abandoning
mid-transaction. We need immediate communication for high-stakes workflows.

## Proposed Solution
Real-time chat embedded in dashboard for instant support connection.
```

❌ **Vague Success Metrics**: "Improve user satisfaction" instead of measurable targets
✅ **Correct approach**: "Increase NPS from 35 to 50 within 2 quarters post-launch"

### Common Mistakes

❌ **Missing Out-of-Scope Section**: Teams build features you didn't intend
```markdown
# ❌ Don't: Omit out-of-scope section
[No mention of what's NOT included]

# ✅ Correct: Explicitly call out scope boundaries
## Out of Scope
- Real-time collaborative editing (defer to Q2)
- Mobile app support (web-only for v1)
- Integration with Slack (evaluate post-launch)
```

❌ **Requirements Without Acceptance Criteria**: "System should be fast"
✅ **Better**: "API responses must complete in <200ms for p95 latency (NFR1)"

❌ **Mixing PRD and RFC Concerns**: PRD shouldn't specify database schema or API endpoints
✅ **Better**: PRD defines what data is needed; RFC defines how it's stored/accessed

---

## Related Skills

- `prd-requirements-gathering.md` - Use before this skill to collect requirements and research
- `prd-user-stories-acceptance.md` - Deep dive on writing effective user stories and acceptance criteria
- `prd-technical-specifications.md` - Bridge between PRD and RFC for technical details
- `engineering/rfc-structure-format.md` - Engineering counterpart for technical design docs
- `engineering/rfc-technical-design.md` - How engineering translates PRD into technical proposals

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
