---
name: product-prd-technical-specifications
description: API specifications, data models, architecture diagrams, and technical constraints for product requirements
---

# PRD Technical Specifications

**Scope**: Bridging product requirements and engineering implementation with API specs, data models, and technical constraints
**Lines**: ~360
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Defining API requirements for product features
- Specifying data models and entity relationships
- Documenting technical constraints (performance, scalability, security)
- Creating architecture diagrams to illustrate system design
- Planning third-party integrations and dependencies
- Defining migration strategies for data or features
- Collaborating with engineering to validate technical feasibility
- Bridging PRD requirements and RFC (Request for Comments) technical designs

## Core Concepts

### Concept 1: PM vs Engineering Technical Ownership

**PM Owns (in PRD)**:
- **What data** the system needs (e.g., "User profile must include name, email, preferences")
- **What API behaviors** are required (e.g., "API must support filtering by date range")
- **What constraints** exist (e.g., "Must support 10,000 concurrent users")
- **What integrations** are needed (e.g., "Must integrate with Stripe for payments")

**Engineering Owns (in RFC)**:
- **How data is stored** (e.g., Postgres schema, NoSQL structure)
- **How APIs are implemented** (e.g., REST vs GraphQL, specific endpoints)
- **How to achieve performance** (e.g., caching strategy, database indexing)
- **How to architect** the solution (e.g., microservices vs monolith)

**Collaboration Zone**: PMs and engineers collaborate on trade-offs (e.g., "Real-time updates vs eventual consistency")

### Concept 2: API Specification Formats

**OpenAPI (Swagger)**: Standard for REST APIs
- Machine-readable API definitions
- Auto-generates documentation
- Enables contract testing

**GraphQL Schema**: For GraphQL APIs
- Defines types, queries, mutations
- Self-documenting via introspection

**Informal API Specs** (in PRD):
- Describe endpoints, inputs, outputs at high level
- Engineering translates to formal OpenAPI/GraphQL schema in RFC

### Concept 3: Data Model Levels of Detail

**Conceptual Model** (PM in PRD):
- Entities and relationships (e.g., "User has many Projects")
- Key attributes (e.g., "Project has title, description, owner")
- Business logic constraints (e.g., "User can only own 10 projects on free plan")

**Logical Model** (Engineering in RFC):
- Normalized tables or collections
- Foreign keys, indexes
- Data types and validations

**Physical Model** (Engineering in implementation):
- Actual database schema (DDL)
- Performance optimizations (partitioning, sharding)

---

## Patterns

### Pattern 1: Informal API Specification (PM in PRD)

**When to use**:
- Defining API requirements at product level
- Providing engineering with clear API expectations
- Not prescribing exact implementation

```markdown
## API Requirements: User Management

### Create User Account
**Purpose**: Allow new users to sign up

**Input**:
- `email` (string, required): User's email address (validated format)
- `password` (string, required): Password (min 8 chars, 1 number, 1 symbol)
- `display_name` (string, optional): User's preferred display name

**Output (Success)**:
- `user_id` (string): Unique identifier for created user
- `email` (string): Confirmed email
- `created_at` (timestamp): Account creation time

**Output (Error)**:
- `error_code` (string): Machine-readable error (e.g., "EMAIL_IN_USE")
- `error_message` (string): Human-readable error
- `field_errors` (object, optional): Field-specific validation errors

**Constraints**:
- Must complete in <500ms (p95 latency)
- Must return 201 status on success, 4xx on validation error
- Must send verification email within 1 minute
- Email must be case-insensitive (user@example.com == USER@EXAMPLE.COM)

**Security**:
- Password must be hashed (bcrypt or stronger)
- Rate limit: 5 signup attempts per IP per hour
- Email verification required before account activation

### Get User Profile
**Purpose**: Retrieve user's profile information

**Input**:
- `user_id` (string, required): ID of user to fetch
- `fields` (array of strings, optional): Specific fields to return (default: all)

**Authentication**: Required (user can only fetch own profile, or admin can fetch any)

**Output (Success)**:
- `user_id` (string)
- `email` (string)
- `display_name` (string)
- `profile_photo_url` (string, optional)
- `created_at` (timestamp)
- `preferences` (object): User settings

**Output (Error)**:
- `error_code`: "UNAUTHORIZED" | "USER_NOT_FOUND"
- `error_message`: Human-readable error

**Constraints**:
- Must complete in <100ms (p95 latency)
- Must support up to 1,000 requests/sec per server
```

**Benefits**:
- Engineering understands API requirements without over-specification
- PM focuses on behavior, not implementation
- Easy to review and validate with stakeholders

### Pattern 2: Entity-Relationship Diagram (Conceptual)

**Use case**: Defining data model for PRD

```markdown
## Data Model: Project Management System

### Entities and Relationships

```
User (1) ──── (many) Project
         │
         └─── (many) ProjectMembership ──── (1) Project
```

### Entity: User
**Attributes**:
- `user_id` (unique identifier)
- `email` (unique, required)
- `display_name` (required)
- `profile_photo_url` (optional)
- `account_tier` ("free" | "pro" | "enterprise")
- `created_at` (timestamp)

**Business Rules**:
- Email must be verified before account activation
- Free tier users can own max 10 projects
- Pro tier users can own unlimited projects

### Entity: Project
**Attributes**:
- `project_id` (unique identifier)
- `title` (required, max 100 chars)
- `description` (optional, max 1000 chars)
- `owner_user_id` (foreign key to User)
- `status` ("active" | "archived" | "deleted")
- `created_at` (timestamp)
- `updated_at` (timestamp)

**Business Rules**:
- Only owner can delete project
- Archived projects are read-only
- Deleted projects are soft-deleted (not permanently removed)

### Entity: ProjectMembership
**Attributes**:
- `membership_id` (unique identifier)
- `project_id` (foreign key to Project)
- `user_id` (foreign key to User)
- `role` ("viewer" | "editor" | "admin")
- `invited_at` (timestamp)
- `joined_at` (timestamp, optional)

**Business Rules**:
- User can have only one membership per project (unique on project_id + user_id)
- Project owner automatically has "admin" role
- "Viewer" can read, "Editor" can read/write, "Admin" can read/write/invite
```

### Pattern 3: Technical Constraints Documentation

**Use case**: Defining non-functional requirements for engineering

```markdown
## Technical Constraints: User Dashboard

### Performance Requirements
**Page Load Time**:
- Initial load: <2 seconds on 4G network (p95)
- Subsequent navigation: <500ms (p95)
- Time to Interactive (TTI): <3 seconds (p95)

**API Response Time**:
- Read operations: <100ms (p95)
- Write operations: <500ms (p95)
- Bulk operations: <2 seconds for up to 1,000 items (p95)

**Scalability**:
- Must support 10,000 concurrent users (current peak: 2,000)
- Must handle 100,000 API requests/minute (current: 20,000/min)
- Database queries must support 1M+ user records

### Security Requirements
**Authentication**:
- JWT-based authentication with 1-hour expiration
- Refresh tokens with 30-day expiration
- HTTPS required for all API calls

**Authorization**:
- Role-based access control (RBAC)
- Users can only access their own data (except admins)
- API rate limiting: 1,000 requests/hour per user

**Data Protection**:
- Passwords hashed with bcrypt (cost factor 12+)
- Sensitive data encrypted at rest (AES-256)
- PII (email, name) encrypted in database
- GDPR compliance: user data export and deletion

### Availability & Reliability
**Uptime**:
- 99.9% uptime SLA (< 43 minutes downtime/month)
- Graceful degradation if dependent services fail
- Zero downtime deployments

**Data Durability**:
- Database backups every 6 hours
- Point-in-time recovery for last 30 days
- Multi-region replication for disaster recovery

### Compatibility Requirements
**Browser Support**:
- Chrome 90+ (last 2 years)
- Safari 14+ (last 2 years)
- Firefox 88+ (last 2 years)
- Edge 90+ (Chromium-based)

**Device Support**:
- Desktop (1920x1080 and above)
- Tablet (768px width and above)
- Mobile (375px width and above)
- Screen readers (WCAG 2.1 AA compliance)

### Operational Constraints
**Deployment**:
- CI/CD pipeline with automated tests
- Rollback capability within 5 minutes
- Feature flags for gradual rollout

**Monitoring**:
- Application performance monitoring (APM)
- Error tracking and alerting
- User analytics and funnel tracking
```

### Pattern 4: Third-Party Integration Specification

**Use case**: Defining integration requirements for external services

```markdown
## Integration Requirements: Payment Processing

### Integration: Stripe

**Use Case**: Process credit card payments for subscription upgrades

**Required Capabilities**:
- Create customer records
- Process one-time payments
- Set up recurring subscriptions
- Handle webhook events (payment success, failure, subscription changes)
- Retrieve payment history

**API Endpoints Needed** (Informal):
- `POST /payments/charge`: Initiate one-time payment
  - Input: `amount`, `currency`, `payment_method_id`, `customer_id`
  - Output: `transaction_id`, `status`, `receipt_url`
- `POST /subscriptions/create`: Start recurring subscription
  - Input: `customer_id`, `plan_id`, `payment_method_id`
  - Output: `subscription_id`, `status`, `next_billing_date`
- `POST /webhooks/stripe`: Receive Stripe events
  - Input: Stripe webhook payload
  - Output: 200 OK (acknowledge receipt)

**Error Handling**:
- Payment declined: Show user-friendly error, allow retry
- Network timeout: Implement retry logic with exponential backoff
- Webhook failure: Queue for retry (max 3 attempts)

**Security**:
- Never store raw credit card numbers (use Stripe tokens)
- Validate webhook signatures (Stripe signing secret)
- Use Stripe's test mode for development/staging

**Constraints**:
- Must use Stripe API version 2023-10-16 or later
- Must handle webhooks within 30 seconds (Stripe timeout)
- Must comply with PCI DSS requirements (Level 1)

**Fallback Plan**:
- If Stripe is down, display maintenance message
- Queue failed payments for manual retry
- Email customer with payment failure notice
```

### Pattern 5: Architecture Diagram (C4 Model - Context Level)

**Use case**: Illustrating system context for PRD

```markdown
## System Architecture: Project Management Platform

### Context Diagram (C4 Level 1)

```
┌─────────────────────────────────────────────────────────────┐
│                     External Systems                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐          │
│  │  Stripe  │      │ SendGrid │      │  Auth0   │          │
│  │ Payments │      │  Email   │      │   SSO    │          │
│  └────┬─────┘      └────┬─────┘      └────┬─────┘          │
│       │                 │                  │                 │
└───────┼─────────────────┼──────────────────┼─────────────────┘
        │                 │                  │
        │                 │                  │
┌───────┼─────────────────┼──────────────────┼─────────────────┐
│       │                 │                  │                 │
│       ▼                 ▼                  ▼                 │
│  ┌─────────────────────────────────────────────────┐        │
│  │    Project Management Platform (Web App)        │        │
│  │                                                  │        │
│  │  - User authentication & authorization          │        │
│  │  - Project creation & management                │        │
│  │  - Real-time collaboration                      │        │
│  │  - Payment processing                           │        │
│  │  - Email notifications                          │        │
│  └─────────────────────────────────────────────────┘        │
│                          ▲                                   │
│                          │                                   │
└──────────────────────────┼───────────────────────────────────┘
                           │
                           │
                  ┌────────┴────────┐
                  │                 │
            ┌─────▼─────┐     ┌─────▼─────┐
            │  Web User │     │ Mobile    │
            │  (Browser)│     │ User      │
            └───────────┘     └───────────┘
```

### Key Interactions
1. **User → Web App**: HTTPS, JWT authentication
2. **Web App → Stripe**: Payment processing API (HTTPS, webhook events)
3. **Web App → SendGrid**: Transactional email API (HTTPS)
4. **Web App → Auth0**: SSO authentication (OAuth 2.0, optional for enterprise)

### Data Flow
- **User signup**: Web App → SendGrid (verification email)
- **Subscription purchase**: Web App → Stripe (payment), Stripe → Web App (webhook)
- **Project creation**: Web App → Database (store), Web App → SendGrid (invite emails)
```

### Pattern 6: Migration and Rollout Plan

**Use case**: Defining how to transition from old to new system

```markdown
## Migration Plan: Legacy User System → New Authentication System

### Current State
- 50,000 active users on legacy auth (custom built)
- Passwords stored with MD5 hashing (insecure!)
- No email verification required
- No support for 2FA or SSO

### Target State
- All users migrated to new auth system (Auth0 or custom with bcrypt)
- Passwords re-hashed with bcrypt on first login
- Email verification enforced for new users
- 2FA available for all users

### Migration Strategy

**Phase 1: Dual-Write (Week 1-2)**
- New signups go directly to new system
- Existing user logins trigger background migration:
  1. Verify password against legacy system
  2. If correct, hash with bcrypt and store in new system
  3. Mark user as migrated in database flag
- No user-facing changes (transparent migration)

**Phase 2: Email Verification Backfill (Week 3-4)**
- Send verification emails to unmigrated users (50k total)
- Require verification on next login
- Grace period: 30 days before enforcing

**Phase 3: Dual-Read (Week 5-6)**
- Login attempts check new system first
- If user not migrated, fall back to legacy system and migrate
- Monitor migration rate (target: 90% in 30 days)

**Phase 4: Legacy System Deprecation (Week 7-8)**
- Force remaining users to reset password (triggers migration)
- Disable legacy login after 90% migration
- Archive legacy auth database (don't delete, keep for 1 year)

**Rollback Plan**:
- If migration fails, revert to legacy system
- Feature flag to toggle new vs legacy auth
- Monitor error rates (>5% triggers automatic rollback)

### Success Metrics
- 90% of users migrated within 30 days
- <1% failed login rate during migration
- Zero security incidents during migration
- <100 support tickets related to migration
```

### Pattern 7: OpenAPI Specification (Formal, Engineering-Led)

**Use case**: Engineering translates PM's informal API spec into OpenAPI for RFC

```yaml
# This is what engineering produces in RFC (not PRD)
# PM provides informal spec, engineering formalizes it

openapi: 3.0.0
info:
  title: User Management API
  version: 1.0.0
  description: API for user account management

paths:
  /users:
    post:
      summary: Create user account
      operationId: createUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - email
                - password
              properties:
                email:
                  type: string
                  format: email
                  example: user@example.com
                password:
                  type: string
                  minLength: 8
                  pattern: '^(?=.*[0-9])(?=.*[!@#$%^&*])'
                  example: SecurePass1!
                display_name:
                  type: string
                  maxLength: 50
                  example: John Doe
      responses:
        '201':
          description: User created successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id:
                    type: string
                    format: uuid
                  email:
                    type: string
                  created_at:
                    type: string
                    format: date-time
        '400':
          description: Validation error
          content:
            application/json:
              schema:
                type: object
                properties:
                  error_code:
                    type: string
                    enum: [EMAIL_IN_USE, INVALID_PASSWORD]
                  error_message:
                    type: string
                  field_errors:
                    type: object
```

**Note**: PM includes this in PRD appendix only if collaborating closely with engineering

### Pattern 8: Dependency Matrix

**Use case**: Tracking all external dependencies and their constraints

```markdown
## Dependencies: Project Management Platform

| Dependency | Purpose | Constraint | Risk | Mitigation |
|------------|---------|------------|------|------------|
| Stripe API | Payment processing | 99.9% uptime SLA | Outage blocks upgrades | Queue failed payments, retry |
| SendGrid API | Transactional email | 50k emails/month (free tier) | Hit limit | Upgrade to paid, throttle emails |
| Auth0 | SSO (enterprise only) | 7k active users (free tier) | Hit limit | Upgrade or build custom SSO |
| AWS S3 | File storage (profile photos) | Unlimited storage | Cost scales with usage | Set storage limits per user |
| PostgreSQL | Primary database | Self-hosted, manual scaling | Performance bottleneck | Plan sharding strategy |
| Redis | Session cache | Self-hosted, 16GB limit | Out of memory | Increase instance size |
| Vercel | Web hosting | 100GB bandwidth/month (free) | Hit limit | Upgrade to paid tier |

### Critical Dependencies (Failure Impact: High)
- **Stripe**: Cannot process payments → Revenue loss
- **PostgreSQL**: Cannot read/write data → Platform down

### Optional Dependencies (Failure Impact: Low)
- **SendGrid**: Cannot send emails → Use fallback (in-app notifications)
- **Auth0**: Cannot use SSO → Users use email/password login
```

---

## Quick Reference

### PM vs Engineering Technical Ownership

```
PM Owns (PRD)             | Engineering Owns (RFC)
--------------------------|---------------------------
What data is needed       | How data is stored (schema)
What API does             | How API is implemented (REST/GraphQL)
What constraints exist    | How to meet constraints (caching, etc.)
What integrations needed  | How to integrate (API client, webhooks)
```

### API Specification Checklist

```
Element | PM Should Define (PRD) | Engineering Should Define (RFC)
--------|------------------------|--------------------------------
Endpoint purpose | ✅ | ✅
Input parameters | ✅ | ✅ (with types, validation)
Output structure | ✅ | ✅ (with schema)
Error handling | ✅ | ✅ (with HTTP codes)
Performance | ✅ (SLA: <100ms) | ✅ (how to achieve)
Security | ✅ (auth required) | ✅ (JWT implementation)
Implementation | ❌ | ✅ (framework, libraries)
```

### Data Model Detail Levels

```
Level | Owner | Example
------|-------|--------
Conceptual | PM (PRD) | "User has many Projects"
Logical | Engineering (RFC) | Normalized tables, foreign keys
Physical | Engineering (Code) | DDL, indexes, partitions
```

### Key Guidelines

```
✅ DO: Define what the API must do, not how it's built
✅ DO: Collaborate with engineering on technical feasibility
✅ DO: Specify performance constraints (e.g., <100ms response)
✅ DO: Document third-party integrations and dependencies
✅ DO: Include security and compliance requirements

❌ DON'T: Prescribe database schema (that's RFC territory)
❌ DON'T: Specify frameworks or libraries (engineering decision)
❌ DON'T: Write formal OpenAPI specs in PRD (engineering's job)
❌ DON'T: Ignore engineering feedback on constraints
❌ DON'T: Forget to document migration and rollout plans
```

---

## Anti-Patterns

### Critical Violations

❌ **Over-Specifying Implementation in PRD**: Telling engineering how to build it
```markdown
# ❌ NEVER (in PRD):
## Technical Implementation
- Use PostgreSQL for user table
- Implement REST API with Express.js
- Hash passwords with bcrypt cost factor 12
- Deploy on AWS EC2 t3.medium instances

# ✅ CORRECT (in PRD):
## Technical Constraints
- Must support 10,000 concurrent users
- Password storage must meet OWASP guidelines (hashing, salting)
- API response time <100ms (p95)
- Must achieve 99.9% uptime SLA

[Engineering decides: Postgres vs Mongo, Express vs FastAPI, etc.]
```

❌ **Missing Performance Requirements**: Vague "should be fast" instead of SLAs
✅ **Correct approach**: "API must respond in <100ms for p95 latency"

### Common Mistakes

❌ **API Spec Without Error Handling**: Only defining happy path
```markdown
# ❌ Don't:
POST /users
Input: email, password
Output: user_id

# ✅ Correct:
POST /users
Input: email, password
Output (Success): user_id, email, created_at
Output (Error): error_code, error_message, field_errors
Error Codes: EMAIL_IN_USE, INVALID_PASSWORD, RATE_LIMIT_EXCEEDED
```

❌ **Ignoring Security Constraints**: No mention of auth, encryption, compliance
✅ **Better**: Document auth requirements, data encryption, GDPR compliance

❌ **Missing Dependency Risks**: Not planning for third-party service failures
✅ **Better**: Document fallback plans for each critical dependency

❌ **No Migration Plan**: Assuming new system magically replaces old one
✅ **Better**: Define phased rollout with dual-write, dual-read, deprecation

---

## Related Skills

- `prd-structure-templates.md` - Document technical specs within PRD sections
- `prd-requirements-gathering.md` - Gather technical constraints during research
- `prd-user-stories-acceptance.md` - Translate technical requirements into testable stories
- `engineering/rfc-structure-format.md` - Engineering's detailed technical design
- `engineering/rfc-technical-design.md` - Engineering translates PRD specs into implementation
- `api-design-rest.md` - Deep dive on REST API design patterns

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
