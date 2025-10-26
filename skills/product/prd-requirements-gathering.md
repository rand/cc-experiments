---
name: product-prd-requirements-gathering
description: Research methods, stakeholder interviews, prioritization frameworks, and requirements synthesis for PRDs
---

# PRD Requirements Gathering

**Scope**: Comprehensive techniques for discovering, validating, and prioritizing product requirements
**Lines**: ~340
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Starting discovery for a new product or feature
- Conducting user interviews to identify needs and pain points
- Synthesizing research findings into actionable requirements
- Prioritizing features using frameworks like RICE or MoSCoW
- Running stakeholder interviews to understand constraints and alignment
- Performing competitive analysis to identify market gaps
- Validating assumptions before writing a PRD
- Dealing with conflicting stakeholder requests and need prioritization

## Core Concepts

### Concept 1: Jobs to Be Done Framework

**Core Principle**:
Users don't want products; they "hire" products to get jobs done.

**JTBD Interview Structure**:
- **Situation**: What circumstances trigger the need?
- **Motivation**: What functional, emotional, social outcomes do they seek?
- **Constraints**: What limitations or anxieties exist?
- **Success**: How do they know the job is done well?

**Example Questions**:
- "Walk me through the last time you needed to [accomplish goal]"
- "What were you trying to achieve?"
- "What did you try before finding our product?"
- "What would make this experience significantly better?"

### Concept 2: Research Synthesis Process

**Data Collection**:
- User interviews (qualitative depth)
- Surveys (quantitative validation)
- Analytics (behavioral evidence)
- Support tickets (pain point frequency)
- Sales/CS calls (voice of customer)

**Synthesis Steps**:
1. **Transcribe and Tag**: Label quotes by theme (usability, performance, feature requests)
2. **Identify Patterns**: Look for repeated pain points across 3+ users
3. **Prioritize Insights**: Weight by frequency, severity, and alignment with strategy
4. **Extract Requirements**: Translate insights into "system must do X because Y"

### Concept 3: Prioritization Frameworks

**RICE Scoring**:
- **Reach**: How many users affected? (per quarter)
- **Impact**: How much will it improve outcomes? (0.25=minimal, 3=massive)
- **Confidence**: How certain are estimates? (50%=low, 100%=high)
- **Effort**: Person-months required
- **Score**: (Reach × Impact × Confidence) / Effort

**MoSCoW Method**:
- **Must Have**: Non-negotiable for launch (failure without it)
- **Should Have**: Important but not critical (workarounds exist)
- **Could Have**: Nice-to-have improvements (if time permits)
- **Won't Have**: Explicitly deferred (out of scope)

**Kano Model**:
- **Basic Needs**: Must be present or users reject product (table stakes)
- **Performance Needs**: More is better (speed, accuracy)
- **Delight Needs**: Unexpected features that wow users

---

## Patterns

### Pattern 1: User Interview Question Design

**When to use**:
- Discovering unmet needs
- Understanding workflows and pain points
- Validating problem hypotheses

```markdown
## User Interview Script Template

### Opening (5 min)
"Thanks for joining! We're trying to understand how people currently [accomplish goal].
No right answers - just want to learn about your experience."

### Context Questions (10 min)
- "Tell me about your role and how [domain] fits into your day."
- "How often do you [perform task]?"
- "Walk me through the last time you needed to [accomplish goal]."

### Pain Point Discovery (15 min)
- "What's most frustrating about [current process]?"
- "What workarounds have you created?"
- "What would you change if you had a magic wand?"
- "What almost made you stop using [current solution]?"

### Jobs to Be Done (15 min)
- "What were you hoping to accomplish when you started using [product]?"
- "What did you try before [product]? Why did you switch?"
- "How do you know when you've succeeded at [task]?"
- "What would make this 10x better?"

### Closing (5 min)
- "Anything else we should know?"
- "Can we follow up if we have questions?"
```

**Key Practices**:
- Ask "why" 3+ times to get to root motivations
- Avoid leading questions ("Would you like feature X?" → "How do you currently solve Y?")
- Listen for emotional language (frustration, delight, anxiety)
- Take verbatim quotes for PRD evidence

### Pattern 2: Stakeholder Interview Template

**Use case**: Understanding technical constraints, business goals, and cross-functional dependencies

```markdown
## Stakeholder Interview Guide

### Engineering Lead
- "What are our biggest technical constraints for [area]?"
- "What would make this project risky from an eng perspective?"
- "What dependencies or integrations do we need to consider?"
- "What's the maintenance burden of different approaches?"

### Design Lead
- "What design patterns have worked well for [similar use case]?"
- "What accessibility requirements do we need to meet?"
- "What user research exists on [topic]?"
- "What are the visual/interaction constraints?"

### Sales/CS
- "What features do prospects ask for most?"
- "What causes deals to stall or users to churn?"
- "What competitive features are we losing to?"
- "What would make your job significantly easier?"

### Leadership
- "How does this align with our annual goals?"
- "What's the business case (revenue, retention, cost savings)?"
- "What timeline are we targeting?"
- "What's the acceptable scope/timeline trade-off?"
```

### Pattern 3: Competitive Analysis Matrix

**When to use**:
- Identifying market gaps
- Benchmarking feature parity
- Finding differentiation opportunities

```markdown
## Competitive Feature Matrix

| Feature | Us | Competitor A | Competitor B | Competitor C | Market Gap? |
|---------|-------|--------------|--------------|--------------|-------------|
| Real-time collaboration | ❌ | ✅ Premium | ✅ All plans | ❌ | Opportunity |
| API access | ✅ Enterprise | ✅ All plans | ❌ | ✅ Pro+ | Competitive |
| Mobile app | ✅ Basic | ✅ Full-featured | ✅ Limited | ❌ | Parity |
| Reporting | ✅ Advanced | ❌ | ✅ Basic | ✅ Basic | Advantage |

## Analysis Notes
- **Opportunity**: Real-time collab is table stakes for Competitors A&B; we're behind
- **Differentiation**: Our reporting is more advanced; lean into this strength
- **Market Gap**: No competitor offers automated workflow templates (white space!)

## Prioritization Implication
1. **Must Have**: Real-time collaboration (basic parity)
2. **Should Have**: Enhanced reporting dashboard (leverage advantage)
3. **Could Have**: Automated templates (differentiation play)
```

### Pattern 4: RICE Prioritization Worksheet

**Use case**: Scoring and ranking feature requests objectively

```markdown
## RICE Scoring Template

| Feature | Reach (users/qtr) | Impact (0.25-3) | Confidence (%) | Effort (PM) | RICE Score |
|---------|-------------------|-----------------|----------------|-------------|------------|
| Real-time collab | 5,000 | 2.0 | 80% | 6 | 1,333 |
| API rate limits | 500 | 0.5 | 100% | 1 | 250 |
| Dark mode | 8,000 | 0.5 | 90% | 2 | 1,800 |
| Export PDF | 3,000 | 1.0 | 100% | 1 | 3,000 |

## Scoring Definitions
**Reach**: Unique users affected per quarter (use analytics or estimates)
**Impact**:
  - 3 = Massive (core workflow, 3x better)
  - 2 = High (significant improvement, 2x better)
  - 1 = Medium (noticeable improvement)
  - 0.5 = Low (nice-to-have)
  - 0.25 = Minimal (tiny improvement)

**Confidence**:
  - 100% = High certainty on all estimates
  - 80% = Medium confidence
  - 50% = Low confidence (use for ideas needing research)

**Effort**: Person-months (eng + design + PM time)

## Priority Ranking
1. Export PDF (score: 3,000) - Quick win, high impact
2. Dark mode (score: 1,800) - High reach, low effort
3. Real-time collab (score: 1,333) - Critical but expensive
4. API rate limits (score: 250) - Low reach, low impact
```

### Pattern 5: MoSCoW Categorization

**Use case**: Creating clear scope boundaries for MVP vs future iterations

```markdown
## MoSCoW Prioritization

### Must Have (Launch Blockers)
- User authentication (can't ship without it)
- Data encryption at rest (compliance requirement)
- Basic reporting dashboard (core value prop)
- Mobile responsive design (50% of traffic is mobile)

**Validation**: Would we cancel launch without this? If yes → Must Have.

### Should Have (Important but Not Critical)
- CSV export (workaround: manual copy-paste exists)
- Advanced filtering (nice-to-have, but search works)
- Email notifications (can use in-app for v1)

**Validation**: Is there a reasonable workaround? If yes → Should Have.

### Could Have (If Time Permits)
- Dark mode (aesthetic preference, not functional need)
- Keyboard shortcuts (power users would love it)
- Bulk operations (currently do one-by-one)

**Validation**: Would users notice if missing? If no → Could Have.

### Won't Have (Explicitly Out of Scope)
- Real-time collaboration (defer to Q2 based on eng complexity)
- Mobile native app (web-first strategy, evaluate later)
- Integration with Salesforce (only 10% of users requested)

**Validation**: Have we decided to explicitly defer? If yes → Won't Have.
```

### Pattern 6: Research Synthesis Affinity Mapping

**Use case**: Organizing qualitative insights from 10+ user interviews

```markdown
## Affinity Mapping Process

### Step 1: Extract Quotes
Read transcripts and pull verbatim user quotes:
- "I spend 2 hours a day copying data between systems" - User 3
- "The export feature crashes on large datasets" - User 7
- "I wish I could share reports with my team" - User 2
- "Loading times make me dread using this" - User 5

### Step 2: Group by Theme
**Performance Issues** (4 mentions):
- "Loading times make me dread using this" - User 5
- "Export crashes on large datasets" - User 7
- "Search takes forever" - User 12
- "Page hangs when I filter" - User 9

**Data Export/Integration** (6 mentions):
- "I spend 2 hours a day copying data" - User 3
- "Export feature crashes" - User 7
- "Need API access" - User 1
- "Can't automate reporting" - User 8

**Collaboration** (3 mentions):
- "I wish I could share reports" - User 2
- "No way to comment on data" - User 6
- "Team visibility is missing" - User 11

### Step 3: Prioritize by Frequency + Severity
1. **Data Export/Integration**: 6 mentions, blocks workflows → High priority
2. **Performance**: 4 mentions, causes daily pain → High priority
3. **Collaboration**: 3 mentions, workaround exists (email) → Medium priority

### Step 4: Translate to Requirements
**Data Export Pain** → Requirement:
- FR1: System must support CSV/JSON export for datasets up to 1M rows
- NFR1: Exports must complete in <30 seconds for 100k rows
- FR2: System must provide REST API for programmatic data access
```

### Pattern 7: Validation Metrics Planning

**Use case**: Defining how you'll measure if requirements solve the problem

```markdown
## Validation Metrics Template

### Problem: Users spend 2+ hours/day on manual data exports
**Hypothesis**: API access will reduce manual export time by 80%

**Leading Indicators** (measure during beta):
- API adoption rate: 30% of users within 30 days
- Support tickets re: exports: Decrease by 50%
- Time spent on export tasks: Measured via time-tracking survey

**Lagging Indicators** (measure post-launch):
- User productivity score (survey): Increase from 6/10 to 8/10
- Retention rate: Increase by 5 percentage points
- NPS for export feature: >40

**Measurement Plan**:
- Instrument API usage analytics (track calls, unique users, errors)
- Send survey at day 7, day 30, day 90 post-API access
- Tag support tickets related to exports for trend analysis
```

### Pattern 8: Bias Mitigation Checklist

**Use case**: Ensuring research quality and avoiding confirmation bias

```markdown
## Research Quality Checklist

### Sample Bias
- [ ] Interviewed users across segments (new, power, churned)
- [ ] Included non-users or lost deals (understand why they left)
- [ ] Avoided only interviewing friendly/engaged users
- [ ] Ensured geographic/demographic diversity if relevant

### Confirmation Bias
- [ ] Asked open-ended questions (not "Would you like X?")
- [ ] Recorded contradictory evidence (users who don't have problem)
- [ ] Avoided leading questions that imply "right" answer
- [ ] Tested alternative hypotheses (maybe problem isn't what we think)

### Recency Bias
- [ ] Looked at long-term trends (6+ months analytics)
- [ ] Didn't over-weight most recent user complaints
- [ ] Validated "urgent" requests with historical data

### Interpretation Bias
- [ ] Used verbatim quotes (not paraphrased interpretations)
- [ ] Had second person review synthesis for accuracy
- [ ] Separated observations from conclusions
```

---

## Quick Reference

### Interview Question Types

```
Question Type | Example | Purpose
--------------|---------|--------
Behavioral | "Walk me through last time you..." | Concrete stories, not hypotheticals
Pain Point | "What's most frustrating about...?" | Discover problems
Workaround | "How do you currently solve...?" | Understand severity (more hacks = worse pain)
Comparative | "What did you try before X?" | Competitive context
Outcome | "How do you know when you've succeeded?" | Success criteria
Hypothetical | "What would make this 10x better?" | Future state vision
```

### Prioritization Framework Comparison

```
Framework | Best For | Output
----------|----------|-------
RICE | Scoring features objectively | Ranked list by score
MoSCoW | Defining MVP scope | Must/Should/Could/Won't buckets
Kano | Understanding user perception | Basic/Performance/Delight categories
Value vs Effort | Quick 2x2 prioritization | Quadrant matrix
Impact/Feasibility | Strategic planning | High-impact, feasible initiatives
```

### Key Guidelines

```
✅ DO: Interview 5-10 users minimum for patterns to emerge
✅ DO: Record and transcribe interviews for accurate quotes
✅ DO: Validate quantitative data with qualitative insights
✅ DO: Involve stakeholders early to surface constraints
✅ DO: Document assumptions and confidence levels

❌ DON'T: Trust single user's feature request as universal need
❌ DON'T: Ask "Would you use X?" (users always say yes)
❌ DON'T: Skip talking to users who churned or chose competitors
❌ DON'T: Prioritize based on who shouted loudest
❌ DON'T: Confuse correlation with causation in data
```

---

## Anti-Patterns

### Critical Violations

❌ **Confirmation Bias in Interviews**: Only asking questions that validate your hypothesis
```markdown
# ❌ NEVER:
"We're thinking of building a real-time chat feature. Would you use that?"
[User, wanting to be helpful: "Sure, that sounds nice!"]

# ✅ CORRECT:
"When you need quick answers, how do you currently get help?"
[User: "Honestly, I just email support and wait. It's annoying but works."]
"How urgent are those questions typically?"
[User: "Not very - I can wait a day usually."]
→ Insight: Real-time chat may not be high priority
```

❌ **Single-Source Requirements**: Building features based on one loud customer
✅ **Correct approach**: Validate request with 5+ users, check analytics for frequency

### Common Mistakes

❌ **Asking "Would You Use X?"**: Users always say yes to hypothetical features
```markdown
# ❌ Don't:
"We could add a dark mode. Would you use it?"
[User: "Yeah, sure!" → Doesn't mean they actually would]

# ✅ Correct:
"How often do you work at night or in low-light environments?"
"Have you enabled dark mode in other apps? Which ones?"
"Does light mode in our app cause any issues for you?"
→ Behavioral evidence > Hypothetical interest
```

❌ **Ignoring Churned Users**: Only interviewing happy current users
✅ **Better**: Interview lost deals and churned users to understand failures

❌ **Skipping Quantitative Validation**: Assuming 3 user complaints = universal problem
✅ **Better**: Check analytics - is this 3 users or 3,000 affected?

❌ **Feature Request Collection, Not Problem Discovery**: "What features do you want?"
✅ **Better**: "What's hardest about [workflow]? Walk me through it."

---

## Related Skills

- `prd-structure-templates.md` - Use after gathering requirements to document in PRD format
- `prd-user-stories-acceptance.md` - Translate gathered requirements into user stories with acceptance criteria
- `prd-technical-specifications.md` - Bridge requirements to technical implementation details
- `test-strategy-planning.md` - Plan how to validate requirements through testing
- `api-design-rest.md` - If requirements include API access needs

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
