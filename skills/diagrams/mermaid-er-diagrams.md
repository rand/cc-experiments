---
name: mermaid-er-diagrams
description: Create entity-relationship diagrams with Mermaid for database schema design and data modeling
---

# Mermaid Entity-Relationship Diagrams

**Scope**: Database schema and data relationship visualization with Mermaid.js
**Lines**: ~400
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Designing database schemas
- Documenting data models
- Visualizing table relationships
- Planning database migrations
- Creating data architecture diagrams
- Modeling domain entities
- Explaining database structure to teams

---

## Core Concepts

### Concept 1: Basic Entity and Relationship Syntax

**Simple entity definition**:
```mermaid
erDiagram
    CUSTOMER
    ORDER
    PRODUCT
```

**With relationships**:
```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    PRODUCT ||--o{ LINE_ITEM : includes
```

**Relationship anatomy**:
```
ENTITY_A |cardinality|--relationship--|cardinality| ENTITY_B : label
         └─────┬─────┘                └─────┬─────┘
               └─ Left side                  └─ Right side
```

### Concept 2: Cardinality Notation

**Zero or One** `|o` or `o|`:
```mermaid
erDiagram
    USER ||--o| PROFILE : has
```
*Each user has zero or one profile*

**Exactly One** `||` or `||`:
```mermaid
erDiagram
    ORDER ||--|| INVOICE : generates
```
*Each order has exactly one invoice*

**Zero or More** `}o` or `o{`:
```mermaid
erDiagram
    AUTHOR }o--o{ BOOK : writes
```
*Authors can write zero or more books*

**One or More** `}|` or `|{`:
```mermaid
erDiagram
    COMPANY ||--|{ EMPLOYEE : employs
```
*A company has one or more employees*

**Visual reference**:
```mermaid
erDiagram
    A ||--|| B : "one-to-one (exactly)"
    C ||--o| D : "one-to-zero-or-one"
    E ||--|{ F : "one-to-one-or-more"
    G ||--o{ H : "one-to-zero-or-more"
    I }o--o{ J : "zero-or-more to zero-or-more"
```

### Concept 3: Relationship Types

**Identifying relationship (solid line `--`)**:
```mermaid
erDiagram
    ORDER ||--|{ LINE_ITEM : contains

    ORDER {
        int order_id PK
        date order_date
    }

    LINE_ITEM {
        int order_id PK,FK
        int line_number PK
        int quantity
    }
```
*LINE_ITEM cannot exist without ORDER (foreign key is part of primary key)*

**Non-identifying relationship (dashed line `..`)**:
```mermaid
erDiagram
    CUSTOMER ||..o{ ORDER : places

    CUSTOMER {
        int customer_id PK
        string name
    }

    ORDER {
        int order_id PK
        int customer_id FK
        date order_date
    }
```
*ORDER can exist independently, just references CUSTOMER*

### Concept 4: Attributes and Keys

**Attribute definition**:
```mermaid
erDiagram
    USER {
        int id PK
        string email UK
        string username UK
        string password_hash
        datetime created_at
        datetime updated_at
    }
```

**Key types**:
```mermaid
erDiagram
    PRODUCT {
        uuid product_id PK "Primary Key"
        string sku UK "Unique identifier"
        int category_id FK "References category"
        string name
        decimal price
        int stock_count
    }

    CATEGORY {
        int category_id PK
        string name UK
        string description
    }

    PRODUCT }o--|| CATEGORY : belongs_to
```

**Key annotations**:
- `PK` - Primary Key
- `FK` - Foreign Key
- `UK` - Unique Key

**Data types** (common conventions):
- `int`, `bigint`, `smallint`
- `string`, `varchar`, `text`
- `decimal`, `float`, `double`
- `boolean`, `bool`
- `date`, `datetime`, `timestamp`
- `uuid`, `json`, `blob`

### Concept 5: Complex Relationships

**Self-referential**:
```mermaid
erDiagram
    EMPLOYEE ||--o{ EMPLOYEE : manages

    EMPLOYEE {
        int employee_id PK
        string name
        int manager_id FK
        string position
    }
```

**Many-to-Many with junction table**:
```mermaid
erDiagram
    STUDENT ||--o{ ENROLLMENT : ""
    ENROLLMENT }o--|| COURSE : ""

    STUDENT {
        int student_id PK
        string name
        string email UK
    }

    ENROLLMENT {
        int enrollment_id PK
        int student_id FK
        int course_id FK
        date enrolled_date
        string grade
    }

    COURSE {
        int course_id PK
        string code UK
        string title
        int credits
    }
```

## Common Patterns

### Pattern 1: E-commerce Schema

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ ORDER_ITEM : contains
    PRODUCT ||--o{ ORDER_ITEM : included_in
    PRODUCT }o--|| CATEGORY : belongs_to
    ORDER ||--o| PAYMENT : has

    CUSTOMER {
        uuid customer_id PK
        string email UK
        string name
        string phone
        datetime created_at
    }

    ORDER {
        uuid order_id PK
        uuid customer_id FK
        datetime order_date
        decimal total_amount
        string status
    }

    ORDER_ITEM {
        uuid order_id PK,FK
        int line_number PK
        uuid product_id FK
        int quantity
        decimal price
        decimal subtotal
    }

    PRODUCT {
        uuid product_id PK
        string sku UK
        string name
        decimal price
        int stock
        uuid category_id FK
    }

    CATEGORY {
        uuid category_id PK
        string name UK
        string description
    }

    PAYMENT {
        uuid payment_id PK
        uuid order_id FK
        decimal amount
        string method
        datetime processed_at
        string status
    }
```

### Pattern 2: User Authentication System

```mermaid
erDiagram
    USER ||--o{ SESSION : has
    USER ||--o{ ROLE_ASSIGNMENT : has
    ROLE ||--o{ ROLE_ASSIGNMENT : assigned_to
    ROLE ||--o{ PERMISSION : includes
    USER ||--o| USER_PROFILE : has

    USER {
        uuid user_id PK
        string email UK
        string password_hash
        boolean email_verified
        datetime created_at
    }

    SESSION {
        uuid session_id PK
        uuid user_id FK
        string token UK
        datetime expires_at
        string ip_address
    }

    ROLE {
        int role_id PK
        string name UK
        string description
    }

    ROLE_ASSIGNMENT {
        uuid user_id PK,FK
        int role_id PK,FK
        datetime assigned_at
    }

    PERMISSION {
        int permission_id PK
        int role_id FK
        string resource
        string action
    }

    USER_PROFILE {
        uuid user_id PK,FK
        string display_name
        string bio
        string avatar_url
        json preferences
    }
```

### Pattern 3: Blog/CMS Schema

```mermaid
erDiagram
    USER ||--o{ POST : authors
    POST ||--o{ COMMENT : has
    USER ||--o{ COMMENT : writes
    POST }o--o{ TAG : tagged_with
    POST_TAG }o--|| POST : ""
    POST_TAG }o--|| TAG : ""
    POST }o--|| CATEGORY : belongs_to

    USER {
        uuid user_id PK
        string username UK
        string email UK
        string password_hash
        datetime created_at
    }

    POST {
        uuid post_id PK
        uuid author_id FK
        uuid category_id FK
        string title
        string slug UK
        text content
        string status
        datetime published_at
    }

    COMMENT {
        uuid comment_id PK
        uuid post_id FK
        uuid user_id FK
        uuid parent_comment_id FK
        text content
        datetime created_at
    }

    TAG {
        int tag_id PK
        string name UK
        string slug UK
    }

    POST_TAG {
        uuid post_id PK,FK
        int tag_id PK,FK
    }

    CATEGORY {
        uuid category_id PK
        string name UK
        string slug UK
        text description
    }
```

### Pattern 4: Multi-Tenancy SaaS

```mermaid
erDiagram
    ORGANIZATION ||--|{ USER : employs
    ORGANIZATION ||--|{ PROJECT : owns
    PROJECT ||--o{ TASK : contains
    USER ||--o{ TASK : assigned_to
    USER ||--o{ ACTIVITY_LOG : generates
    ORGANIZATION ||--o| SUBSCRIPTION : has

    ORGANIZATION {
        uuid org_id PK
        string name UK
        string slug UK
        datetime created_at
    }

    USER {
        uuid user_id PK
        uuid org_id FK
        string email UK
        string name
        string role
    }

    PROJECT {
        uuid project_id PK
        uuid org_id FK
        string name
        text description
        string status
    }

    TASK {
        uuid task_id PK
        uuid project_id FK
        uuid assigned_to FK
        string title
        text description
        string status
        date due_date
    }

    SUBSCRIPTION {
        uuid subscription_id PK
        uuid org_id FK
        string plan_name
        decimal price
        datetime expires_at
    }

    ACTIVITY_LOG {
        uuid log_id PK
        uuid user_id FK
        uuid org_id FK
        string action
        json metadata
        datetime created_at
    }
```

## Best Practices

### 1. Clear Entity Naming
```mermaid
erDiagram
    %% Good: Singular nouns, uppercase
    USER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains

    %% Bad: Plural, lowercase, inconsistent
    users ||--o{ order : places
    order ||--|{ order_line_items : contains
```

### 2. Explicit Foreign Keys
```mermaid
erDiagram
    POST {
        uuid post_id PK
        uuid author_id FK "References USER"
        uuid category_id FK "References CATEGORY"
    }

    USER {
        uuid user_id PK
    }

    CATEGORY {
        uuid category_id PK
    }

    POST }o--|| USER : authored_by
    POST }o--|| CATEGORY : in_category
```

### 3. Normalize Appropriately
**Good**: Many-to-many with junction table
```mermaid
erDiagram
    STUDENT ||--o{ ENROLLMENT : ""
    COURSE ||--o{ ENROLLMENT : ""

    ENROLLMENT {
        int student_id PK,FK
        int course_id PK,FK
        date enrolled_date
        string grade
    }
```

**Bad**: Denormalized array (avoid in SQL)
```mermaid
erDiagram
    STUDENT {
        int student_id PK
        string name
        json course_ids
    }
```

### 4. Use Descriptive Relationship Labels
```mermaid
erDiagram
    %% Good: Clear action verbs
    USER ||--o{ POST : authors
    COMPANY ||--|{ EMPLOYEE : employs
    ORDER ||--o| SHIPMENT : fulfilled_by

    %% Bad: Generic or missing
    USER ||--o{ POST : has
    COMPANY ||--|{ EMPLOYEE : related
    ORDER ||--o| SHIPMENT : ""
```

## Anti-Patterns

### ❌ Missing Cardinality
```mermaid
erDiagram
    USER -- ORDER : places
```
**Problem**: Relationship type unclear

**✅ Better**:
```mermaid
erDiagram
    USER ||--o{ ORDER : places
```

### ❌ No Primary Keys
```mermaid
erDiagram
    USER {
        string email
        string name
    }
```

**✅ Better**:
```mermaid
erDiagram
    USER {
        uuid user_id PK
        string email UK
        string name
    }
```

### ❌ Overloaded Entity
```mermaid
erDiagram
    ENTITY {
        int id PK
        string type
        json data1
        json data2
        json data3
        json data4
    }
```
**Problem**: God entity, lacks structure

**✅ Better**: Split into separate entities with clear responsibilities

### ❌ Circular Dependencies Without Nullables
```mermaid
erDiagram
    USER ||--|| PROFILE : has
    PROFILE ||--|| USER : belongs_to
```
**Problem**: Cannot create either without the other

**✅ Better**:
```mermaid
erDiagram
    USER ||--o| PROFILE : has
```

## Integration Tips

- **Start with ERD** → Then create migrations
- **Combine with class diagrams** → Show ORM models
- **Use sequence diagrams** → Show CRUD operations
- **Document indexes** → Add notes about performance

## Related Skills

- `mermaid-class-state-diagrams.md` - Object modeling
- `database-schema-design.md` - Schema best practices
- `database-migrations.md` - Evolution patterns

## Resources

- Official Docs: https://mermaid.js.org/syntax/entityRelationshipDiagram.html
- Live Editor: https://mermaid.live
- Chen ERD Notation: https://en.wikipedia.org/wiki/Entity%E2%80%93relationship_model
- Crow's Foot Notation: Standard cardinality visualization
