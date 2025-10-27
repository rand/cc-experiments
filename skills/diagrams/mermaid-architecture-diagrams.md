---
name: mermaid-architecture-diagrams
description: Create C4 and block architecture diagrams with Mermaid for system design and infrastructure visualization
---

# Mermaid Architecture Diagrams

**Scope**: System architecture, C4 diagrams, and infrastructure visualization with Mermaid.js
**Lines**: ~430
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Designing system architecture
- Documenting microservices topology
- Creating infrastructure diagrams
- Visualizing deployment architectures
- Planning cloud infrastructure
- Mapping service dependencies
- Explaining system context to stakeholders

---

# Part 1: C4 Diagrams

## Core Concepts

### Concept 1: System Context (Level 1)

**Purpose**: Show the system and its users/dependencies

```mermaid
C4Context
    title System Context for Online Banking

    Person(customer, "Customer", "A banking customer")
    Person(admin, "Administrator", "Bank staff member")

    System(banking, "Online Banking System", "Allows customers to manage accounts")

    System_Ext(email, "Email System", "Microsoft Exchange")
    System_Ext(mainframe, "Core Banking", "Legacy mainframe")

    Rel(customer, banking, "Uses", "HTTPS")
    Rel(admin, banking, "Manages", "HTTPS")
    Rel(banking, email, "Sends emails", "SMTP")
    Rel(banking, mainframe, "Gets account data", "XML/HTTPS")
```

**System boundary**:
```mermaid
C4Context
    title E-commerce Platform Context

    Person(buyer, "Buyer", "Purchases products")
    Person(seller, "Seller", "Lists products")

    System_Boundary(platform, "E-commerce Platform") {
        System(web, "Web App", "Customer-facing")
        System(seller_portal, "Seller Portal", "Vendor management")
    }

    System_Ext(payment, "Payment Gateway", "Stripe")
    System_Ext(shipping, "Shipping Provider", "FedEx API")

    Rel(buyer, web, "Shops on")
    Rel(seller, seller_portal, "Manages inventory")
    Rel(web, payment, "Processes payments")
    Rel(web, shipping, "Creates shipments")
```

### Concept 2: Container Diagram (Level 2)

**Purpose**: Show high-level technology choices

```mermaid
C4Container
    title Container Diagram for Banking System

    Person(customer, "Customer")

    Container_Boundary(system, "Banking System") {
        Container(web, "Web Application", "React", "Delivers static content")
        Container(api, "API Gateway", "Node.js", "Handles requests")
        Container(auth, "Auth Service", "Go", "Authentication")
        Container(accounts, "Account Service", "Java", "Account operations")
        Container(db, "Database", "PostgreSQL", "Stores account data")
        Container(cache, "Cache", "Redis", "Session storage")
    }

    System_Ext(email, "Email Service")

    Rel(customer, web, "Uses", "HTTPS")
    Rel(web, api, "Makes API calls", "JSON/HTTPS")
    Rel(api, auth, "Authenticates", "gRPC")
    Rel(api, accounts, "Queries", "gRPC")
    Rel(accounts, db, "Reads/Writes", "SQL")
    Rel(auth, cache, "Stores sessions", "Redis Protocol")
    Rel(accounts, email, "Sends notifications", "SMTP")
```

### Concept 3: Component Diagram (Level 3)

**Purpose**: Show internal structure of a container

```mermaid
C4Component
    title Component Diagram for API Gateway

    Container(web, "Web App")
    Container(db, "Database")

    Container_Boundary(api, "API Gateway") {
        Component(router, "Router", "Express", "Routes requests")
        Component(auth_middleware, "Auth Middleware", "Passport", "Verifies JWT")
        Component(validator, "Request Validator", "Joi", "Validates input")
        Component(user_ctrl, "User Controller", "Node.js", "User operations")
        Component(order_ctrl, "Order Controller", "Node.js", "Order operations")
        Component(logger, "Logger", "Winston", "Logs requests")
    }

    Rel(web, router, "Sends requests")
    Rel(router, auth_middleware, "Passes through")
    Rel(auth_middleware, validator, "Validates")
    Rel(validator, user_ctrl, "Routes to")
    Rel(validator, order_ctrl, "Routes to")
    Rel(user_ctrl, db, "Queries")
    Rel(order_ctrl, db, "Queries")
    Rel(router, logger, "Logs via")
```

## C4 Common Patterns

### Pattern 1: Microservices Architecture

```mermaid
C4Container
    title Microservices E-commerce Platform

    Person(user, "User")

    Container_Boundary(frontend, "Frontend") {
        Container(web, "Web App", "React", "SPA")
        Container(mobile, "Mobile App", "React Native", "iOS/Android")
    }

    Container_Boundary(backend, "Backend Services") {
        Container(gateway, "API Gateway", "Kong", "Entry point")
        Container(user_svc, "User Service", "Go", "User management")
        Container(product_svc, "Product Service", "Node.js", "Catalog")
        Container(order_svc, "Order Service", "Java", "Orders")
        Container(payment_svc, "Payment Service", "Python", "Payments")
    }

    Container_Boundary(data, "Data Layer") {
        ContainerDb(user_db, "User DB", "PostgreSQL")
        ContainerDb(product_db, "Product DB", "MongoDB")
        ContainerDb(order_db, "Order DB", "PostgreSQL")
        ContainerQueue(queue, "Message Queue", "RabbitMQ")
    }

    Rel(user, web, "Uses")
    Rel(user, mobile, "Uses")
    Rel(web, gateway, "API calls", "HTTPS")
    Rel(mobile, gateway, "API calls", "HTTPS")

    Rel(gateway, user_svc, "Routes to")
    Rel(gateway, product_svc, "Routes to")
    Rel(gateway, order_svc, "Routes to")

    Rel(order_svc, payment_svc, "Requests payment")
    Rel(payment_svc, queue, "Publishes events")
    Rel(order_svc, queue, "Consumes events")

    Rel(user_svc, user_db, "Reads/Writes")
    Rel(product_svc, product_db, "Reads/Writes")
    Rel(order_svc, order_db, "Reads/Writes")
```

### Pattern 2: Serverless Architecture

```mermaid
C4Container
    title Serverless Image Processing

    Person(user, "User")

    Container_Boundary(aws, "AWS Cloud") {
        Container(s3_upload, "Upload Bucket", "S3", "Raw images")
        Container(lambda_process, "Processor", "Lambda", "Resize images")
        Container(s3_processed, "Processed Bucket", "S3", "Optimized images")
        Container(dynamo, "Metadata DB", "DynamoDB", "Image metadata")
        Container(sqs, "Queue", "SQS", "Processing queue")
        Container(api, "API", "API Gateway", "REST API")
    }

    Rel(user, api, "Uploads", "HTTPS")
    Rel(api, s3_upload, "Stores")
    Rel(s3_upload, sqs, "Triggers event")
    Rel(sqs, lambda_process, "Invokes")
    Rel(lambda_process, s3_processed, "Saves")
    Rel(lambda_process, dynamo, "Updates metadata")
```

---

# Part 2: Block Diagrams

## Core Concepts

### Concept 1: Basic Blocks and Layout

**Simple blocks**:
```mermaid
block-beta
    columns 3
    Frontend Backend Database
```

**With labels**:
```mermaid
block-beta
    columns 3
    A["Web App"] B["API Server"] C["PostgreSQL"]
```

**Block spanning**:
```mermaid
block-beta
    columns 3
    LoadBalancer:3
    Server1 Server2 Server3
    Database:3
```

### Concept 2: Block Shapes

**Different shapes**:
```mermaid
block-beta
    columns 1
    A["Rectangle - Default"]
    B("Rounded - Service")
    C(("Circle - Node"))
    D[("Cylinder - Database")]
    E{{"Hexagon - Process"}}
    F>"Asymmetric - Queue"]
```

### Concept 3: Nested Blocks

**Grouping components**:
```mermaid
block-beta
    columns 3

    block:Frontend:1
        Web["Web App"]
        Mobile["Mobile App"]
    end

    block:Backend:1
        API["API Gateway"]
        Services["Microservices"]
    end

    block:Data:1
        DB[("Database")]
        Cache[("Redis")]
    end
```

### Concept 4: Connections

**Connecting blocks**:
```mermaid
block-beta
    columns 3
    Client --> Gateway --> Services
    Services --> Database
```

**Labeled connections**:
```mermaid
block-beta
    columns 2
    Frontend["Web App"]
    Backend["API Server"]

    Frontend -- "HTTPS" --> Backend
    Backend -- "SQL" --> DB[("PostgreSQL")]
```

## Block Diagram Patterns

### Pattern 1: Three-Tier Architecture

```mermaid
block-beta
    columns 3

    block:Presentation:3
        Web["Web Browser"]
        Mobile["Mobile App"]
    end

    space

    block:Application:3
        LB["Load Balancer"]:3
        App1["App Server 1"]
        App2["App Server 2"]
        App3["App Server 3"]
    end

    space

    block:Data:3
        Primary[("Primary DB")]
        Replica1[("Replica 1")]
        Replica2[("Replica 2")]
    end

    Web --> LB
    Mobile --> LB
    LB --> App1
    LB --> App2
    LB --> App3
    App1 --> Primary
    App2 --> Primary
    App3 --> Primary
    Primary --> Replica1
    Primary --> Replica2
```

### Pattern 2: Event-Driven Architecture

```mermaid
block-beta
    columns 5

    Producer1["Order Service"]
    Producer2["Payment Service"]
    Queue>"Event Bus"]
    Consumer1["Email Service"]
    Consumer2["Analytics Service"]

    Producer1 -- "OrderCreated" --> Queue
    Producer2 -- "PaymentProcessed" --> Queue
    Queue -- "Consumes" --> Consumer1
    Queue -- "Consumes" --> Consumer2
```

### Pattern 3: Cloud Infrastructure

```mermaid
block-beta
    columns 4

    block:Internet:4
        Users["Users"]
    end

    block:AWS:4
        CDN["CloudFront CDN"]:4

        space
        ALB["Load Balancer"]:2
        space

        block:VPC:4
            columns 2
            block:Public:1
                NAT["NAT Gateway"]
            end

            block:Private:1
                EC2_1["EC2 Instance 1"]
                EC2_2["EC2 Instance 2"]
                RDS[("RDS PostgreSQL")]
            end
        end
    end

    Users --> CDN
    CDN --> ALB
    ALB --> EC2_1
    ALB --> EC2_2
    EC2_1 --> RDS
    EC2_2 --> RDS
    EC2_1 --> NAT
    EC2_2 --> NAT
```

### Pattern 4: Kubernetes Deployment

```mermaid
block-beta
    columns 3

    block:K8s:3
        columns 3

        Ingress["Ingress Controller"]:3

        space:3

        block:Frontend:1
            FE_Pod1["Frontend Pod 1"]
            FE_Pod2["Frontend Pod 2"]
        end

        block:Backend:1
            BE_Pod1["Backend Pod 1"]
            BE_Pod2["Backend Pod 2"]
        end

        block:Data:1
            Redis[("Redis")]
            Postgres[("PostgreSQL")]
        end

        space:3

        ConfigMap["ConfigMap"]:1
        Secrets["Secrets"]:1
        PVC["PersistentVolume"]:1
    end

    Ingress --> FE_Pod1
    Ingress --> FE_Pod2
    FE_Pod1 --> BE_Pod1
    FE_Pod1 --> BE_Pod2
    FE_Pod2 --> BE_Pod1
    FE_Pod2 --> BE_Pod2
    BE_Pod1 --> Redis
    BE_Pod2 --> Redis
    BE_Pod1 --> Postgres
    BE_Pod2 --> Postgres
    Postgres --> PVC
```

## Best Practices

### 1. Layer Your Architecture
Group components by responsibility:
- Presentation layer
- Application layer
- Data layer
- External systems

### 2. Show Technology Choices
```mermaid
C4Container
    Container(web, "Web App", "React 18", "SPA with Vite")
    Container(api, "API", "FastAPI + Python 3.11", "REST API")
    Container(db, "Database", "PostgreSQL 15", "Primary datastore")
```

### 3. Indicate Data Flow Direction
```mermaid
block-beta
    Client --> Gateway
    Gateway --> Service
    Service --> Database
    Database -- "Async" --> Cache
```

### 4. Group Related Components
Use boundaries and nested blocks to show ownership and deployment context.

### 5. Document External Dependencies
```mermaid
C4Context
    System(app, "Your System")
    System_Ext(stripe, "Stripe", "Payment processing")
    System_Ext(sendgrid, "SendGrid", "Email delivery")
```

## Anti-Patterns

### ❌ Too Many Components in One Diagram
**Problem**: Visual overload, hard to understand
**Solution**: Split into multiple diagrams by context/layer

### ❌ Missing Technology Labels
```mermaid
C4Container
    Container(api, "API")  %% What technology?
```
**✅ Better**:
```mermaid
C4Container
    Container(api, "API", "Node.js + Express", "REST API")
```

### ❌ Unclear Relationships
```mermaid
block-beta
    A --> B
    B --> C
```
**✅ Better**:
```mermaid
block-beta
    A -- "HTTPS/JSON" --> B
    B -- "gRPC" --> C
```

### ❌ No Grouping or Boundaries
**Problem**: Can't tell what's internal vs external, or which team owns what
**Solution**: Use system boundaries and nested blocks

## Integration Tips

- **Start with Context** → Then drill into Containers → Then Components
- **Use with sequence diagrams** → Show runtime behavior
- **Combine with ER diagrams** → Document data model
- **Export as SVG** → Include in architecture docs

## Related Skills

- `mermaid-sequence-diagrams.md` - Runtime interactions
- `mermaid-flowcharts.md` - Process flows
- `mermaid-er-diagrams.md` - Data modeling

## Resources

- C4 Model: https://c4model.com
- Official Docs:
  - https://mermaid.js.org/syntax/c4.html
  - https://mermaid.js.org/syntax/block.html
- Live Editor: https://mermaid.live
- Architecture patterns: https://microservices.io/patterns/index.html
