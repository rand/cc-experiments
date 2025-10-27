---
name: mermaid-sequence-diagrams
description: Create interaction and message flow diagrams with Mermaid showing communication between actors, services, and components over time
---

# Mermaid Sequence Diagrams

**Scope**: Interaction and message flow visualization with Mermaid.js
**Lines**: ~350
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Documenting API interactions and request/response flows
- Visualizing microservice communication patterns
- Showing user-system interactions
- Mapping message flows in distributed systems
- Illustrating protocol sequences
- Creating actor interaction diagrams
- Documenting async/sync communication patterns

## Core Concepts

### Concept 1: Participants and Actors

**Basic participant definition**:
```mermaid
sequenceDiagram
    participant A as Alice
    participant B as Bob
    A->>B: Hello Bob!
    B->>A: Hi Alice!
```

**Participant types**:
```mermaid
sequenceDiagram
    actor User
    participant API as API Gateway
    participant Auth as Auth Service
    database DB as PostgreSQL
    queue Q as Message Queue

    User->>API: POST /login
    API->>Auth: Verify credentials
    Auth->>DB: Query user
    DB-->>Auth: User data
    Auth-->>API: Token
    API->>Q: Log event
    API-->>User: 200 OK + Token
```

**Participant ordering**:
```mermaid
sequenceDiagram
    %% Define order explicitly
    participant C as Client
    participant API
    participant Cache
    participant DB

    C->>API: Request
    API->>Cache: Check cache
    alt Cache miss
        API->>DB: Query
        DB-->>API: Data
        API->>Cache: Store
    end
    API-->>C: Response
```

### Concept 2: Message Arrow Types

**Arrow styles and meanings**:
```mermaid
sequenceDiagram
    participant A
    participant B

    A->>B: Solid line with arrow (synchronous)
    A-->>B: Dotted line with arrow (async/response)
    A->B: Solid line without arrow (simple message)
    A-->B: Dotted line without arrow
    A-xB: Solid line with X (failed/rejected)
    A--xB: Dotted line with X
    A-)B: Solid line with open arrow (async)
    A--)B: Dotted line with open arrow
```

**Semantic usage**:
```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant DB

    Client->>Server: Synchronous request
    activate Server
    Server->>DB: Query (sync)
    activate DB
    DB-->>Server: Result (response)
    deactivate DB
    Server-)Client: Async notification
    Server-->>Client: Response (reply)
    deactivate Server

    Client-xServer: Failed request
```

### Concept 3: Activation Boxes

**Manual activation**:
```mermaid
sequenceDiagram
    participant A
    participant B

    A->>B: Request
    activate B
    B->>B: Process internally
    B-->>A: Response
    deactivate B
```

**Shorthand with +/-**:
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Service

    Client->>+API: Request
    API->>+Service: Forward
    Service-->>-API: Response
    API-->>-Client: Result
```

**Nested activations**:
```mermaid
sequenceDiagram
    participant A
    participant B
    participant C

    A->>+B: Start
    B->>+C: Call helper
    C-->>-B: Helper result
    B->>+C: Another call
    C-->>-B: Second result
    B-->>-A: Final result
```

### Concept 4: Control Flow Blocks

**Alternatives (if/else)**:
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB

    Client->>API: Request user
    API->>DB: Query

    alt User found
        DB-->>API: User data
        API-->>Client: 200 OK
    else User not found
        DB-->>API: Not found
        API-->>Client: 404 Not Found
    else Database error
        DB--xAPI: Error
        API-->>Client: 500 Server Error
    end
```

**Optional block**:
```mermaid
sequenceDiagram
    participant User
    participant App
    participant Analytics

    User->>App: Perform action
    App->>App: Process

    opt Analytics enabled
        App-)Analytics: Track event
    end

    App-->>User: Success
```

**Loop block**:
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Queue

    loop Until success or max retries
        Client->>API: Poll for result
        API->>Queue: Check status

        alt Ready
            Queue-->>API: Result
            API-->>Client: 200 + Data
        else Not ready
            Queue-->>API: Pending
            API-->>Client: 202 Accepted
        end
    end
```

**Parallel blocks**:
```mermaid
sequenceDiagram
    participant Client
    participant Gateway
    participant ServiceA
    participant ServiceB
    participant ServiceC

    Client->>Gateway: Request

    par Call ServiceA
        Gateway->>ServiceA: Request
        ServiceA-->>Gateway: ResponseA
    and Call ServiceB
        Gateway->>ServiceB: Request
        ServiceB-->>Gateway: ResponseB
    and Call ServiceC
        Gateway->>ServiceC: Request
        ServiceC-->>Gateway: ResponseC
    end

    Gateway-->>Client: Aggregated result
```

**Critical sections**:
```mermaid
sequenceDiagram
    participant P1 as Process 1
    participant Resource
    participant P2 as Process 2

    critical Acquire lock
        P1->>Resource: Lock
        Resource-->>P1: Locked
        P1->>Resource: Read/Write
    option Lock timeout
        Resource--xP1: Timeout
    end

    P1->>Resource: Unlock
```

### Concept 5: Notes and Comments

**Note positioning**:
```mermaid
sequenceDiagram
    participant A
    participant B
    participant C

    Note left of A: Client initiates
    A->>B: Request
    Note right of B: Server validates
    B->>C: Forward
    Note over C: Database query
    C-->>B: Result
    Note over A,B: Response path
    B-->>A: Response
```

**Multi-line notes**:
```mermaid
sequenceDiagram
    participant API
    participant DB

    Note over API,DB: Transaction begins<br/>Multiple operations<br/>Must complete atomically

    API->>DB: BEGIN
    API->>DB: INSERT
    API->>DB: UPDATE
    API->>DB: COMMIT
```

**Comments**:
```mermaid
sequenceDiagram
    %% This is a comment explaining the flow
    participant A
    participant B

    %% Main interaction
    A->>B: Message

    %% TODO: Add error handling
```

## Common Patterns

### Pattern 1: RESTful API Request/Response

```mermaid
sequenceDiagram
    actor Client
    participant Gateway as API Gateway
    participant Auth as Auth Service
    participant API as User Service
    database DB as PostgreSQL

    Client->>+Gateway: POST /users/login
    Note over Client,Gateway: HTTPS with credentials

    Gateway->>+Auth: Verify JWT
    alt Valid token
        Auth-->>-Gateway: Claims
        Gateway->>+API: GET /users/{id}
        API->>+DB: SELECT * FROM users
        DB-->>-API: User record
        API-->>-Gateway: 200 OK + User data
        Gateway-->>-Client: 200 OK
    else Invalid token
        Auth-->>-Gateway: Unauthorized
        Gateway-->>Client: 401 Unauthorized
    end
```

### Pattern 2: Microservice Communication

```mermaid
sequenceDiagram
    participant Order as Order Service
    participant Inventory as Inventory Service
    participant Payment as Payment Service
    participant Shipping as Shipping Service
    queue EventBus as Event Bus

    Order->>+Inventory: Reserve items
    Inventory-->>-Order: Reserved

    Order->>+Payment: Charge customer
    alt Payment success
        Payment-->>-Order: Success
        Order-)EventBus: OrderPaid event
        EventBus-)Inventory: Confirm reservation
        EventBus-)Shipping: Initiate shipment

        par Ship order
            Shipping->>Shipping: Create shipment
        and Update inventory
            Inventory->>Inventory: Decrement stock
        end
    else Payment failed
        Payment-->>-Order: Failed
        Order->>Inventory: Release reservation
        Order-->>Order: Cancel order
    end
```

### Pattern 3: Retry with Exponential Backoff

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Service

    loop Retry up to 3 times
        Client->>+API: Request
        API->>+Service: Call external API

        alt Success
            Service-->>-API: 200 OK
            API-->>-Client: Success
        else Failure
            Service--xAPI: 503 Service Unavailable
            API-->>-Client: 503 + Retry-After
            Note over Client: Wait exponentially<br/>(1s, 2s, 4s)
        end
    end

    alt Max retries exceeded
        Client->>Client: Log failure
        Note over Client: Circuit breaker opens
    end
```

## Best Practices

### 1. Clear Participant Naming
```mermaid
sequenceDiagram
    %% Good: Descriptive names
    actor User
    participant WebApp as Web Application
    participant AuthAPI as Authentication API
    database UserDB as User Database

    %% Bad: Cryptic abbreviations
    participant A
    participant B
    participant C
```

### 2. Use Activation Appropriately
```mermaid
sequenceDiagram
    participant A
    participant B

    %% Shows that B is processing
    A->>+B: Request
    B->>B: Long process
    B-->>-A: Response

    %% Not needed for simple pass-through
    A->>B: Quick message
    B-->>A: Quick reply
```

### 3. Group Related Interactions
```mermaid
sequenceDiagram
    box User Layer
        actor User
        participant UI
    end

    box Application Layer
        participant API
        participant Service
    end

    box Data Layer
        database DB
        database Cache
    end

    User->>UI: Click button
    UI->>API: POST /action
    API->>Service: Process
    Service->>Cache: Check
    Service->>DB: Query
```

### 4. Label Meaningful Responses
```mermaid
sequenceDiagram
    participant A
    participant B

    %% Good: Shows what's returned
    A->>B: GET /user/123
    B-->>A: 200 OK + {id, name, email}

    %% Bad: Generic response
    A->>B: Request
    B-->>A: Response
```

## Anti-Patterns

### ❌ Too Many Participants
Creates visual clutter, hard to follow:
```mermaid
sequenceDiagram
    participant A
    participant B
    participant C
    participant D
    participant E
    participant F
    participant G
```
**Solution**: Group related participants or split into multiple diagrams

### ❌ Missing Activations
Can't tell when services are actively processing:
```mermaid
sequenceDiagram
    A->>B: Start long process
    B->>C: Sub-task
    C-->>B: Done
    B-->>A: Complete
```

**✅ Better**:
```mermaid
sequenceDiagram
    A->>+B: Start long process
    B->>+C: Sub-task
    C-->>-B: Done
    B-->>-A: Complete
```

### ❌ Unlabeled Decision Points
```mermaid
sequenceDiagram
    A->>B: Request
    alt
        B-->>A: Response1
    else
        B-->>A: Response2
    end
```

**✅ Better**:
```mermaid
sequenceDiagram
    A->>B: Request
    alt Valid input
        B-->>A: 200 OK
    else Invalid input
        B-->>A: 400 Bad Request
    end
```

## Integration with Other Diagrams

- **Start with sequence** → Then create flowchart for complex logic
- **Sequence for interactions** → Class diagram for structure
- **Sequence for runtime** → Architecture diagram for deployment

## Related Skills

- `mermaid-flowcharts.md` - For process logic
- `mermaid-class-state-diagrams.md` - For object structure
- `mermaid-architecture-diagrams.md` - For system design

## Resources

- Official Docs: https://mermaid.js.org/syntax/sequenceDiagram.html
- Live Editor: https://mermaid.live
- GitHub/GitLab: Auto-rendering in markdown
