---
name: mermaid-project-diagrams
description: Create Gantt charts and timeline diagrams with Mermaid for project planning and chronological visualization
---

# Mermaid Project Diagrams

**Scope**: Project timelines, Gantt charts, and chronological visualization with Mermaid.js
**Lines**: ~400
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Planning project schedules
- Visualizing task dependencies
- Creating release timelines
- Documenting historical events
- Showing product roadmaps
- Mapping sprint schedules
- Tracking milestone progress

---

# Part 1: Gantt Charts

## Core Concepts

### Concept 1: Basic Task Structure

**Simple timeline**:
```mermaid
gantt
    title Project Timeline
    dateFormat YYYY-MM-DD

    section Planning
    Define Requirements    :2024-01-01, 10d
    Design Architecture    :2024-01-11, 15d

    section Development
    Build Backend          :2024-01-26, 30d
    Build Frontend         :2024-02-15, 25d
```

**Date format options**:
```mermaid
gantt
    dateFormat YYYY-MM-DD
    %% Also supported: MM-DD, DD, etc.

    Task 1    :2024-01-01, 5d
    Task 2    :2024-01-06, 1w
    Task 3    :2024-01-13, 2w
```

### Concept 2: Task States

**Active, done, and critical tasks**:
```mermaid
gantt
    title Development Sprint
    dateFormat YYYY-MM-DD

    section Backend
    API Design         :done, api, 2024-01-01, 5d
    Database Schema    :done, db, 2024-01-06, 3d
    API Implementation :active, impl, 2024-01-09, 10d
    Testing            :test, 2024-01-19, 5d

    section Critical Path
    Security Review    :crit, 2024-01-15, 7d
    Deploy to Prod     :crit, milestone, 2024-01-24, 0d
```

**Task tags**:
- `done` - Completed task (gray)
- `active` - Currently in progress (blue)
- `crit` - Critical path (red)
- `milestone` - Key milestone (marker)

### Concept 3: Dependencies

**Sequential tasks**:
```mermaid
gantt
    title Task Dependencies
    dateFormat YYYY-MM-DD

    section Phase 1
    Task A    :a, 2024-01-01, 5d
    Task B    :b, after a, 7d
    Task C    :c, after b, 4d

    section Phase 2
    Task D    :d, after c, 10d
    Task E    :e, after d, 8d
```

**Multiple dependencies**:
```mermaid
gantt
    dateFormat YYYY-MM-DD

    section Core
    Foundation    :f, 2024-01-01, 10d

    section Parallel
    Feature A     :a, after f, 15d
    Feature B     :b, after f, 12d
    Feature C     :c, after f, 18d

    section Integration
    Merge All     :crit, after a b c, 5d
```

### Concept 4: Milestones

**Project milestones**:
```mermaid
gantt
    title Product Launch Timeline
    dateFormat YYYY-MM-DD

    section Q1
    Planning           :2024-01-01, 30d
    MVP Complete       :milestone, 2024-01-31, 0d

    section Q2
    Beta Development   :2024-02-01, 60d
    Beta Launch        :milestone, crit, 2024-04-01, 0d

    section Q3
    Production Ready   :2024-04-02, 90d
    Public Launch      :milestone, crit, 2024-07-01, 0d
```

## Gantt Chart Patterns

### Pattern 1: Software Release Plan

```mermaid
gantt
    title Release 2.0 Schedule
    dateFormat YYYY-MM-DD

    section Planning
    Requirements Gathering    :done, 2024-01-01, 10d
    Technical Design          :done, 2024-01-11, 7d
    Sprint Planning           :done, 2024-01-18, 3d

    section Development
    Sprint 1                  :done, s1, 2024-01-22, 14d
    Sprint 2                  :active, s2, 2024-02-05, 14d
    Sprint 3                  :s3, 2024-02-19, 14d

    section Testing
    QA Testing                :after s3, 7d
    UAT                       :after s3, 10d
    Security Audit            :crit, after s3, 5d

    section Deployment
    Staging Deploy            :milestone, after s3, 0d
    Production Deploy         :crit, milestone, 2024-03-15, 0d
```

### Pattern 2: Feature Development

```mermaid
gantt
    title User Authentication Feature
    dateFormat YYYY-MM-DD
    excludes weekends

    section Backend
    Database Schema      :done, 2024-01-08, 2d
    API Endpoints        :done, 2024-01-10, 5d
    JWT Implementation   :active, 2024-01-15, 3d
    OAuth Integration    :2024-01-18, 5d

    section Frontend
    Login UI             :active, 2024-01-15, 4d
    Registration UI      :2024-01-19, 3d
    Password Reset       :2024-01-22, 3d

    section Testing
    Unit Tests           :2024-01-18, 5d
    Integration Tests    :2024-01-23, 4d
    E2E Tests            :crit, 2024-01-27, 3d

    section Documentation
    API Docs             :2024-01-25, 3d
    User Guide           :2024-01-28, 2d

    section Milestones
    Feature Complete     :milestone, crit, 2024-01-31, 0d
```

### Pattern 3: Infrastructure Migration

```mermaid
gantt
    title Cloud Migration Project
    dateFormat YYYY-MM-DD

    section Preparation
    Audit Current Infra       :done, 2024-01-01, 14d
    Choose Cloud Provider     :done, 2024-01-15, 7d
    Architecture Design       :done, 2024-01-22, 10d

    section Migration Phase 1
    Setup VPC & Networking    :active, p1, 2024-02-01, 7d
    Migrate Databases         :crit, after p1, 14d
    Setup Load Balancers      :after p1, 5d

    section Migration Phase 2
    Migrate App Servers       :p2, 2024-02-20, 14d
    Configure CDN             :after p2, 3d
    Setup Monitoring          :after p2, 5d

    section Testing
    Performance Testing       :crit, 2024-03-10, 10d
    Security Scan             :crit, 2024-03-10, 7d
    Disaster Recovery Test    :crit, 2024-03-17, 5d

    section Cutover
    DNS Switch                :milestone, crit, 2024-03-25, 0d
    Decommission Old          :2024-03-26, 14d
```

---

# Part 2: Timeline Diagrams

## Core Concepts

### Concept 1: Basic Timeline

**Simple chronology**:
```mermaid
timeline
    title History of JavaScript
    1995 : Brendan Eich creates JavaScript in 10 days
    1997 : ECMAScript 1 released
    1999 : ECMAScript 3 released
    2005 : AJAX becomes popular
    2009 : Node.js released
         : ECMAScript 5 released
    2015 : ECMAScript 6 (ES2015) major update
    2020 : ECMAScript 2020
```

**Multiple events per period**:
```mermaid
timeline
    title Product Evolution
    2020 : MVP Launch
         : 1K Users
    2021 : Mobile App
         : 10K Users
         : Series A Funding
    2022 : Enterprise Features
         : 100K Users
         : Profitability
```

### Concept 2: Sections

**Grouped by era**:
```mermaid
timeline
    title Company Milestones

    section Startup Phase
    2019 : Founded
         : Seed Funding $1M
    2020 : Product Launch
         : First 100 customers

    section Growth Phase
    2021 : Series A $10M
         : 1000 customers
         : Expand to EU
    2022 : Series B $50M
         : 10K customers

    section Scale Phase
    2023 : IPO
         : 100K customers
         : Global presence
```

### Concept 3: Product Roadmap

**Future planning**:
```mermaid
timeline
    title Product Roadmap 2024

    section Q1
    Jan 2024 : Dark Mode
             : Mobile App v2.0
    Feb 2024 : API v3.0
    Mar 2024 : Admin Dashboard

    section Q2
    Apr 2024 : Multi-language Support
    May 2024 : Advanced Analytics
    Jun 2024 : Collaboration Features

    section Q3
    Jul 2024 : Enterprise SSO
    Aug 2024 : Audit Logs
    Sep 2024 : Custom Workflows

    section Q4
    Oct 2024 : AI Integrations
    Nov 2024 : Mobile SDK
    Dec 2024 : Year in Review
```

## Timeline Patterns

### Pattern 1: Technology Evolution

```mermaid
timeline
    title Frontend Framework Evolution

    section Early Web
    1995 : JavaScript invented
    1999 : XMLHttpRequest (AJAX precursor)

    section Library Era
    2006 : jQuery released
         : Revolutionizes DOM manipulation
    2010 : Backbone.js
         : First MVC framework for web

    section Framework Era
    2013 : React introduced by Facebook
    2014 : Vue.js released
    2016 : Angular 2 rewrite

    section Modern Era
    2019 : React Hooks
         : Vue 3 Composition API
    2020 : Svelte gains popularity
    2021 : React Server Components
    2024 : AI-powered development tools
```

### Pattern 2: Project History

```mermaid
timeline
    title Project XYZ History

    section Discovery
    Week 1 : Initial brainstorming
           : Market research
    Week 2 : Competitive analysis
           : User interviews

    section Design
    Week 3 : Wireframes
           : User flows
    Week 4 : High-fidelity mockups
           : Design system

    section Development
    Week 5-8 : Sprint 1-4
             : Core features
    Week 9-10 : Testing & QA

    section Launch
    Week 11 : Beta release
    Week 12 : Public launch
            : Marketing campaign
```

### Pattern 3: Career Timeline

```mermaid
timeline
    title Professional Journey

    section Education
    2015-2019 : BS Computer Science
              : Internship at Startup

    section Early Career
    2019-2021 : Junior Developer at Tech Corp
              : Learned React, Node.js
              : Shipped 3 major features

    section Mid Career
    2021-2023 : Senior Developer at SaaS Co
              : Led team of 4
              : Architected microservices

    section Current
    2023-Present : Tech Lead at Enterprise
                 : Managing 10 engineers
                 : Driving technical strategy
```

## Best Practices

### Gantt Charts

**Do**:
- Use sections to group related tasks
- Mark critical path with `crit` tag
- Show dependencies with `after` syntax
- Include milestones for key dates
- Exclude weekends for realistic timelines

**Don't**:
- Overcrowd with too many tasks (group them)
- Forget to mark completed tasks as `done`
- Mix different levels of detail
- Omit dependencies between tasks

### Timelines

**Do**:
- Group events into logical sections
- Use consistent date formats
- Include multiple events per period when relevant
- Keep descriptions concise

**Don't**:
- Mix granularities (days with years)
- Omit important context
- Create too many sections (max 5-6)
- Use overly long event descriptions

## Anti-Patterns

### ❌ Missing Dependencies
```mermaid
gantt
    Task A    :2024-01-01, 5d
    Task B    :2024-01-01, 10d  %% Should start after A?
```
**✅ Better**: Use `after` for sequential tasks

### ❌ No Critical Path
```mermaid
gantt
    Important Task    :2024-01-01, 10d
```
**✅ Better**: Mark critical tasks
```mermaid
gantt
    Important Task    :crit, 2024-01-01, 10d
```

### ❌ Inconsistent Timeline Granularity
```mermaid
timeline
    1990 : Event A
    1995 : Event B
    Jan 2020 : Event C  %% Suddenly very specific
    2025 : Event D
```
**✅ Better**: Maintain consistent time scale

## Integration Tips

- **Gantt + Flowchart**: Process flow → then timeline
- **Timeline + Sequence**: History → then detailed interaction
- **Gantt + Architecture**: What to build → when to build it

Use Gantt for:
- Sprint planning
- Release schedules
- Resource allocation
- Dependency tracking

Use Timeline for:
- Product history
- Technology evolution
- Company milestones
- Roadmap communication

## Related Skills

- `mermaid-flowcharts.md` - Process flows
- `mermaid-sequence-diagrams.md` - Temporal interactions
- `project-management.md` - Planning methodologies

## Resources

- Official Docs:
  - https://mermaid.js.org/syntax/gantt.html
  - https://mermaid.js.org/syntax/timeline.html
- Live Editor: https://mermaid.live
- Project Management: PMBOK Guide
- Agile Planning: Scrum Guide
