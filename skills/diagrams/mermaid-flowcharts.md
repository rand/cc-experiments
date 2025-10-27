---
name: mermaid-flowcharts
description: Create process flow diagrams with Mermaid using nodes, arrows, decisions, and subgraphs for visual documentation
---

# Mermaid Flowcharts

**Scope**: Process flow visualization with Mermaid.js syntax
**Lines**: ~320
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Documenting process workflows and algorithms
- Visualizing decision trees and conditional logic
- Creating system flow diagrams
- Mapping user or data flows
- Generating architecture flow documentation
- Adding diagrams to markdown documentation
- Explaining complex procedures visually

## Core Concepts

### Concept 1: Graph Direction and Basic Structure

**Direction Options**:
- `TD` or `TB` - Top to bottom (default)
- `LR` - Left to right
- `RL` - Right to left
- `BT` - Bottom to top

```mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
```

```mermaid
graph LR
    A[Input] --> B[Transform]
    B --> C[Output]
```

**When to use each direction**:
- TD/TB: Hierarchical processes, decision trees
- LR: Linear workflows, pipelines, data flows
- BT: Bottom-up analysis, dependency flows
- RL: Reverse processes, unwinding

### Concept 2: Node Shapes

**Shape Reference**:
```mermaid
graph TD
    A[Rectangle - Standard process]
    B(Rounded - Start/End alternative)
    C([Stadium - Start/End points])
    D[[Subroutine - Function call]]
    E[(Database - Data storage)]
    F((Circle - Connection point))
    G{Diamond - Decision}}
    H{{Hexagon - Preparation}}
    I[/Parallelogram - Input/Output/]
    J[\Inverted parallelogram - Output/Input\]
    K[/Trapezoid - Manual operation\]
    L[\Inverted trapezoid/]
```

**Semantic meaning by shape**:
- **Rectangle**: Standard process step
- **Rounded/Stadium**: Start and end points
- **Diamond**: Decision points (if/then)
- **Parallelogram**: Input/Output operations
- **Cylinder**: Database operations
- **Hexagon**: Preparation or initialization
- **Subroutine**: Function or subprocess call
- **Circle**: Connection or merge points

```mermaid
graph TD
    Start([Start Process])
    Start --> Input[/Get User Input/]
    Input --> Validate{Valid Input?}
    Validate -->|No| Error[Show Error]
    Error --> Input
    Validate -->|Yes| Process[Process Data]
    Process --> DB[(Save to Database)]
    DB --> Output[\Display Result\]
    Output --> End([End])
```

### Concept 3: Connection Types and Labels

**Arrow Styles**:
```mermaid
graph LR
    A --> B
    B --- C
    C -.-> D
    D ==> E
    E <--> F
```

- `-->` - Solid arrow (standard flow)
- `---` - Line without arrow (connection)
- `-.->` - Dotted arrow (optional/async flow)
- `==>` - Thick arrow (emphasized flow)
- `<-->` - Bi-directional (mutual dependency)

**Link Labels**:
```mermaid
graph TD
    A[Check Status] -->|Success| B[Continue]
    A -->|Failure| C[Retry]
    A -.->|Timeout| D[Alert]
    C ==>|Max Retries| D
```

**Multi-word labels**:
```mermaid
graph LR
    A -->|"Step 1: Validate"| B
    B -->|"Step 2: Process"| C
    C -->|"Step 3: Save"| D
```

### Concept 4: Subgraphs for Organization

**Basic subgraph syntax**:
```mermaid
graph TD
    A[Start] --> B[Login]

    subgraph Authentication
        B --> C{Credentials Valid?}
        C -->|Yes| D[Generate Token]
        C -->|No| E[Show Error]
        E --> B
    end

    D --> F[Access Dashboard]

    subgraph Dashboard
        F --> G[Display Data]
        G --> H[User Actions]
    end

    H --> I[Logout]
    I --> J[End]
```

**Nested subgraphs**:
```mermaid
graph TD
    subgraph API Layer
        A[Request] --> B[Validate]

        subgraph Auth
            B --> C[Check Token]
            C --> D[Verify Permissions]
        end

        D --> E[Route]
    end

    E --> F[Database]
```

**Direction in subgraphs**:
```mermaid
graph TD
    A[Start]

    subgraph Processing["Data Processing"]
        direction LR
        B[Parse] --> C[Transform] --> D[Validate]
    end

    A --> B
    D --> E[Save]
```

### Concept 5: Styling and Classes

**Inline node styling**:
```mermaid
graph TD
    A[Normal]
    B[Highlighted]
    style B fill:#f9f,stroke:#333,stroke-width:4px
```

**Class definitions**:
```mermaid
graph TD
    A[Success]:::success
    B[Error]:::error
    C[Warning]:::warning

    classDef success fill:#9f6,stroke:#333,stroke-width:2px
    classDef error fill:#f66,stroke:#333,stroke-width:2px
    classDef warning fill:#ff6,stroke:#333,stroke-width:2px
```

**Styling subgraphs**:
```mermaid
graph TD
    subgraph Critical [Critical Path]
        A[Step 1] --> B[Step 2]
    end

    style Critical fill:#ffe6e6,stroke:#ff0000,stroke-width:2px
```

### Concept 6: Complex Flow Patterns

**Decision tree with multiple paths**:
```mermaid
graph TD
    Start([Start]) --> Input[/Enter Data/]
    Input --> Validate{Validate}

    Validate -->|Valid| TypeCheck{Check Type}
    Validate -->|Invalid| Error1[Show Validation Error]
    Error1 --> Input

    TypeCheck -->|Type A| ProcessA[Process A Path]
    TypeCheck -->|Type B| ProcessB[Process B Path]
    TypeCheck -->|Type C| ProcessC[Process C Path]

    ProcessA --> Merge((Merge))
    ProcessB --> Merge
    ProcessC --> Merge

    Merge --> Save[(Save Results)]
    Save --> Success([Success])
```

**Parallel processing**:
```mermaid
graph TD
    Start([Start]) --> Split[Split Work]

    Split --> T1[Task 1]
    Split --> T2[Task 2]
    Split --> T3[Task 3]

    T1 --> Join((Join))
    T2 --> Join
    T3 --> Join

    Join --> Aggregate[Aggregate Results]
    Aggregate --> End([End])
```

**Error handling flow**:
```mermaid
graph TD
    Start([Start])
    Start --> Try[Try Operation]

    Try --> Success{Success?}
    Success -->|Yes| Continue[Continue]
    Success -->|No| Retry{Retry Count < 3?}

    Retry -->|Yes| Wait[Wait & Retry]
    Wait --> Try

    Retry -->|No| Error[Log Error]
    Error --> Fallback[Execute Fallback]
    Fallback --> Notify[/Notify Admin/]

    Continue --> End([End])
    Notify --> End
```

## Common Patterns

### Pattern 1: API Request Flow

```mermaid
graph TD
    Client([Client]) --> Request[HTTP Request]
    Request --> Gateway[API Gateway]

    Gateway --> Auth{Authenticated?}
    Auth -->|No| Reject[401 Unauthorized]
    Auth -->|Yes| Rate{Rate Limit OK?}

    Rate -->|No| Throttle[429 Too Many Requests]
    Rate -->|Yes| Route[Route to Service]

    Route --> Process[Process Request]
    Process --> DB[(Database)]
    DB --> Transform[Transform Response]
    Transform --> Cache[(Cache)]
    Cache --> Response[\HTTP Response\]

    Response --> Client
    Reject --> Client
    Throttle --> Client
```

### Pattern 2: Data Pipeline

```mermaid
graph LR
    Source[(Source DB)] -->|Extract| ETL

    subgraph ETL Process
        direction TB
        E[Extract] --> T[Transform]
        T --> V{Validate}
        V -->|Invalid| Log[/Log Error/]
        V -->|Valid| L[Load]
    end

    L --> Target[(Target DB)]
    L --> Analytics[(Analytics)]
    Log --> Monitor[Monitoring]
```

### Pattern 3: User Authentication Flow

```mermaid
graph TD
    Start([User Login]) --> Input[/Enter Credentials/]
    Input --> Validate{Valid Format?}

    Validate -->|No| FormatError[Show Format Error]
    FormatError --> Input

    Validate -->|Yes| CheckDB[(Query User DB)]
    CheckDB --> Exists{User Exists?}

    Exists -->|No| NotFound[User Not Found]
    Exists -->|Yes| CheckPass{Password Match?}

    CheckPass -->|No| Attempts{Attempts < 3?}
    Attempts -->|Yes| Failed[Login Failed]
    Failed --> Input
    Attempts -->|No| Lock[Lock Account]
    Lock --> Notify[/Send Alert/]

    CheckPass -->|Yes| Generate[Generate Session]
    Generate --> Token[[Create JWT]]
    Token --> Success([Login Success])

    NotFound --> End([End])
    Notify --> End
    Success --> End
```

## Best Practices

### 1. Keep It Simple
- Limit to 10-15 nodes per diagram
- Use subgraphs to break down complex flows
- One main path with branches, not web of connections

### 2. Consistent Naming
```mermaid
graph TD
    %% Good: Clear, descriptive names
    UserInput[/Get User Input/]
    ValidateEmail{Email Valid?}
    SendConfirmation[\Send Email\]

    %% Bad: Cryptic abbreviations
    UI[/UI/]
    VE{VE?}
    SC[\SC\]
```

### 3: Logical Flow Direction
- Top-to-bottom for hierarchical processes
- Left-to-right for sequential pipelines
- Keep arrows flowing in primary direction
- Minimize backward arrows (creates visual clutter)

### 4. Meaningful Shapes
```mermaid
graph TD
    Start([Start/End - Stadium])
    Process[Process - Rectangle]
    Decision{Decision - Diamond}
    IO[/Input or Output - Parallelogram/]
    Data[(Database - Cylinder)]
    Function[[Function Call - Subroutine]]
```

### 5. Color Coding for Status
```mermaid
graph TD
    Normal[Normal Flow]
    Critical[Critical Path]:::critical
    Error[Error Handler]:::error
    Success[Success State]:::success

    classDef critical fill:#ffa,stroke:#ff0,stroke-width:3px
    classDef error fill:#faa,stroke:#f00,stroke-width:2px
    classDef success fill:#afa,stroke:#0f0,stroke-width:2px
```

## Integration Examples

### In Markdown Documentation
```markdown
# User Registration Process

Our registration flow follows this pattern:

\```mermaid
graph TD
    A[User Visits] --> B[Fill Form]
    B --> C{Valid?}
    C -->|Yes| D[Create Account]
    C -->|No| B
    D --> E[Send Email]
    E --> F[Verify Email]
\```
```

### In GitHub README
```markdown
## Architecture Flow

\```mermaid
graph LR
    Client --> API[API Gateway]
    API --> Auth[Auth Service]
    API --> Data[Data Service]
    Data --> DB[(PostgreSQL)]
\```
```

### In Documentation Sites (Docusaurus, VuePress, etc.)
Most support Mermaid rendering natively or via plugins.

## Anti-Patterns

### ❌ Too Many Connections
```mermaid
graph TD
    A --> B
    A --> C
    A --> D
    B --> C
    B --> D
    B --> E
    C --> D
    C --> E
    D --> E
```
**Problem**: Creates visual spaghetti, hard to follow

### ❌ Inconsistent Shapes
```mermaid
graph TD
    A[Start]
    B(Process)
    C{Decision}
    D[Another Process]
    E((End))
```
**Problem**: No semantic meaning, just random shapes

### ❌ Missing Labels on Decisions
```mermaid
graph TD
    A{Check} --> B
    A --> C
```
**Problem**: Can't tell which branch is true/false

### ✅ Correct Version
```mermaid
graph TD
    A{Valid Input?} -->|Yes| B[Process]
    A -->|No| C[Error]
```

## Related Skills

- `mermaid-sequence-diagrams.md` - For interaction flows
- `mermaid-class-state-diagrams.md` - For UML and state machines
- `mermaid-architecture-diagrams.md` - For C4 and system architecture

## Resources

- Official Docs: https://mermaid.js.org/syntax/flowchart.html
- Live Editor: https://mermaid.live
- GitHub Integration: Automatic rendering in `.md` files
- VS Code: Mermaid Preview extension
