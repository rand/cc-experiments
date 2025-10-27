---
name: mermaid-specialized
description: Create specialized diagrams with Mermaid including Git graphs, Sankey flows, mindmaps, and other advanced visualization types
---

# Mermaid Specialized Diagrams

**Scope**: GitGraph, Sankey, mindmaps, and advanced diagram types in Mermaid.js
**Lines**: ~430
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Visualizing Git workflows and branching strategies
- Showing data flows and transformations (Sankey)
- Creating hierarchical concept maps (mindmaps)
- Documenting version control processes
- Illustrating energy/material flows
- Brainstorming and organizing ideas
- Mapping dependencies and conversions

---

# Part 1: Git Graphs

## Core Concepts

### Concept 1: Basic Commits and Branches

**Linear commits**:
```mermaid
gitGraph
    commit
    commit
    commit
```

**Feature branch**:
```mermaid
gitGraph
    commit
    commit
    branch feature
    checkout feature
    commit
    commit
    checkout main
    commit
    merge feature
    commit
```

### Concept 2: Commit Metadata

**Commits with IDs and tags**:
```mermaid
gitGraph
    commit id: "Initial commit"
    commit id: "Add authentication" tag: "v0.1"

    branch develop
    checkout develop
    commit id: "Feature work"
    commit id: "Bug fixes"

    checkout main
    merge develop tag: "v1.0"
    commit id: "Hotfix" tag: "v1.0.1"
```

### Concept 3: Commit Types

**Visual emphasis**:
```mermaid
gitGraph
    commit type: NORMAL
    commit type: HIGHLIGHT id: "Important change"
    commit type: REVERSE id: "Reverted change"
    branch hotfix
    checkout hotfix
    commit type: HIGHLIGHT id: "Critical fix"
    checkout main
    merge hotfix tag: "v1.0.1"
```

**Commit types**:
- `NORMAL` - Standard commit (default)
- `HIGHLIGHT` - Important commit (emphasized)
- `REVERSE` - Reverted or rolled back commit

## Git Graph Patterns

### Pattern 1: Gitflow Workflow

```mermaid
gitGraph
    commit id: "Initial"
    commit id: "Setup project"

    branch develop
    checkout develop
    commit id: "Add core features"

    branch feature/login
    checkout feature/login
    commit id: "Add login UI"
    commit id: "Add authentication"

    checkout develop
    merge feature/login
    commit id: "Integrate login"

    branch release/1.0
    checkout release/1.0
    commit id: "Bump version"
    commit id: "Update changelog"

    checkout main
    merge release/1.0 tag: "v1.0.0"

    checkout develop
    merge release/1.0

    branch hotfix/security
    checkout hotfix/security
    commit id: "Fix vulnerability" type: HIGHLIGHT

    checkout main
    merge hotfix/security tag: "v1.0.1"

    checkout develop
    merge hotfix/security
```

### Pattern 2: Trunk-Based Development

```mermaid
gitGraph
    commit id: "Base"

    branch feature-a
    commit id: "Feature A work"
    checkout main

    branch feature-b
    commit id: "Feature B work"
    checkout main

    merge feature-a
    commit id: "CI/CD deploy"

    merge feature-b
    commit id: "CI/CD deploy"
    commit tag: "v1.0" type: HIGHLIGHT
```

### Pattern 3: Release Branches

```mermaid
gitGraph
    commit id: "v0.9"
    branch release/1.0
    checkout release/1.0
    commit id: "RC1" tag: "v1.0-rc1"
    commit id: "Bug fixes"
    commit id: "RC2" tag: "v1.0-rc2"

    checkout main
    branch develop
    checkout develop
    commit id: "New features for v1.1"

    checkout release/1.0
    commit id: "Final polish"
    checkout main
    merge release/1.0 tag: "v1.0.0" type: HIGHLIGHT

    checkout develop
    merge main
    commit id: "Continue v1.1 work"
```

---

# Part 2: Sankey Diagrams

## Core Concepts

### Concept 1: Basic Flow

**Simple data flow**:
```mermaid
sankey-beta
Source,Process,100
Process,Output A,60
Process,Output B,40
```

### Concept 2: Complex Flows

**Energy distribution**:
```mermaid
sankey-beta
Power Plant,Transmission,1000
Transmission,Industrial,400
Transmission,Commercial,350
Transmission,Residential,200
Transmission,Loss,50
```

### Concept 3: Multi-Stage Flows

**Data pipeline**:
```mermaid
sankey-beta
Raw Data,Cleaning,10000
Cleaning,Valid Records,8500
Cleaning,Rejected,1500
Valid Records,Processing,8500
Processing,Output DB,7000
Processing,Archive,1500
```

## Sankey Patterns

### Pattern 1: User Journey Flow

```mermaid
sankey-beta
Landing Page,Sign Up,10000
Landing Page,Browse,5000
Landing Page,Exit,15000
Sign Up,Complete Profile,7000
Sign Up,Abandon,3000
Browse,Add to Cart,2000
Browse,Exit,3000
Add to Cart,Checkout,1500
Add to Cart,Abandon Cart,500
Checkout,Purchase,1200
Checkout,Abandon,300
```

### Pattern 2: Budget Allocation

```mermaid
sankey-beta
Total Budget,Engineering,450000
Total Budget,Sales,300000
Total Budget,Marketing,150000
Total Budget,Operations,100000

Engineering,Salaries,350000
Engineering,Infrastructure,70000
Engineering,Tools,30000

Sales,Salaries,200000
Sales,Travel,50000
Sales,CRM,50000

Marketing,Ads,80000
Marketing,Events,40000
Marketing,Content,30000
```

### Pattern 3: Application Resource Usage

```mermaid
sankey-beta
Total Memory,Application Heap,2048
Total Memory,Native Memory,512
Total Memory,System,512

Application Heap,Active Objects,1500
Application Heap,Cached Data,548

Active Objects,User Sessions,800
Active Objects,Business Logic,500
Active Objects,Framework,200
```

---

# Part 3: Mindmaps

## Core Concepts

### Concept 1: Basic Hierarchy

**Simple structure**:
```mermaid
mindmap
    root((Project))
        Planning
            Requirements
            Design
        Development
            Frontend
            Backend
        Testing
            Unit Tests
            Integration Tests
```

### Concept 2: Node Shapes

**Different shapes for emphasis**:
```mermaid
mindmap
    root((Core Concept))
        [Important Category]
            (Sub-item 1)
            (Sub-item 2)
        {Cloud Topic}
            ((Circle Item))
            [!Bang Item!]
        {{Hexagon Topic}}
```

**Shape reference**:
- `((text))` - Circle (root default)
- `(text)` - Rounded square
- `[text]` - Square
- `{text}` - Cloud
- `{{text}}` - Hexagon
- `[!text!]` - Bang

### Concept 3: Icons and Styling

**With icons**:
```mermaid
mindmap
    root((Project))::icon(fa fa-project-diagram)
        Planning::icon(fa fa-calendar)
            Requirements
            Timeline
        Development::icon(fa fa-code)
            Frontend
            Backend
        Deploy::icon(fa fa-rocket)
```

## Mindmap Patterns

### Pattern 1: System Architecture

```mermaid
mindmap
    root((E-commerce Platform))
        Frontend
            Web App
                React
                TypeScript
                Vite
            Mobile App
                React Native
                iOS
                Android
        Backend
            API Gateway
                Kong
                Rate Limiting
            Microservices
                User Service
                Order Service
                Payment Service
            Databases
                PostgreSQL
                Redis
                MongoDB
        Infrastructure
            AWS
                EC2
                RDS
                S3
            Monitoring
                Prometheus
                Grafana
            CI/CD
                GitHub Actions
                Docker
```

### Pattern 2: Learning Path

```mermaid
mindmap
    root((Full-Stack Development))
        Frontend
            HTML/CSS
                Semantic HTML
                Flexbox
                Grid
            JavaScript
                ES6+
                Async/Await
                DOM
            React
                Hooks
                Context
                Router
        Backend
            Node.js
                Express
                NestJS
            Databases
                SQL
                    PostgreSQL
                    Joins
                NoSQL
                    MongoDB
                    Redis
        DevOps
            Docker
                Containers
                Compose
            Kubernetes
                Pods
                Services
            AWS
                EC2
                S3
                Lambda
```

### Pattern 3: Project Breakdown

```mermaid
mindmap
    root((Launch New Feature))
        Research
            User Interviews
            Competitor Analysis
            Market Research
        Design
            Wireframes
            Mockups
            User Flows
            Design System
        Development
            Backend API
                Database Schema
                Endpoints
                Auth
            Frontend
                Components
                Pages
                State Management
            Testing
                Unit Tests
                Integration
                E2E
        Launch
            Beta Release
            Marketing
            Documentation
            Training
```

---

# Part 4: Other Specialized Diagrams

## Requirement Diagrams

**Requirements traceability**:
```mermaid
requirementDiagram
    requirement UserAuth {
        id: REQ-001
        text: Users must authenticate
        risk: high
        verifymethod: test
    }

    functionalRequirement LoginAPI {
        id: FREQ-001
        text: Provide login endpoint
    }

    element AuthService {
        type: service
        docRef: auth-service.md
    }

    UserAuth - satisfies -> LoginAPI
    LoginAPI - implements -> AuthService
```

## Best Practices

### Git Graphs

**Do**:
- Show realistic branching strategies
- Use tags for releases
- Highlight important commits
- Show merge directions clearly

**Don't**:
- Create overly complex graphs (limit to 20-30 commits)
- Mix different workflows in one diagram
- Omit critical merge points

### Sankey Diagrams

**Do**:
- Use for flow visualization (data, energy, resources)
- Ensure flow values are consistent (in = out)
- Label nodes clearly
- Show losses/waste explicitly

**Don't**:
- Use for hierarchies (use mindmap)
- Create circular flows
- Omit significant flow paths

### Mindmaps

**Do**:
- Start with central concept
- Group related items
- Use shapes for categorization
- Limit depth to 4-5 levels

**Don't**:
- Create unbalanced trees
- Mix abstraction levels
- Overcrowd with too many nodes

## Anti-Patterns

### ❌ Overcomplicated Git Graph
```mermaid
gitGraph
    commit
    branch feat1
    branch feat2
    branch feat3
    %% ... 10 more branches
```
**Solution**: Split into multiple diagrams or show just relevant branches

### ❌ Inconsistent Sankey Flows
```mermaid
sankey-beta
Input,Process,100
Process,Output,120  %% Where did extra 20 come from?
```
**✅ Better**: Flows must balance

### ❌ Flat Mindmap (No Hierarchy)
```mermaid
mindmap
    root
        Item1
        Item2
        Item3
        %% No grouping or structure
```
**✅ Better**: Group related concepts into hierarchies

## Integration Tips

- **GitGraph + Sequence**: Version control workflow + runtime behavior
- **Sankey + Architecture**: Data flow + system structure
- **Mindmap + Flowchart**: Concept breakdown + process flow
- **GitGraph + Project Timeline**: Development workflow + schedule

## Related Skills

- `mermaid-flowcharts.md` - Process flows
- `mermaid-sequence-diagrams.md` - Interactions
- `mermaid-architecture-diagrams.md` - System design
- `version-control.md` - Git workflows

## Resources

- Official Docs:
  - https://mermaid.js.org/syntax/gitgraph.html
  - https://mermaid.js.org/syntax/sankey.html
  - https://mermaid.js.org/syntax/mindmap.html
- Live Editor: https://mermaid.live
- Gitflow: https://nvie.com/posts/a-successful-git-branching-model/
- Trunk-Based Development: https://trunkbaseddevelopment.com/
