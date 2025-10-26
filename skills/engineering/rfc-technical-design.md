---
name: engineering-rfc-technical-design
description: Architecture proposals, technical diagrams, API design, trade-off analysis, and migration strategies for RFCs
---

# RFC Technical Design

**Scope**: Techniques for designing architecture, evaluating alternatives, creating technical diagrams, and planning migrations
**Lines**: ~340
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Designing system architecture for a new feature or service
- Evaluating multiple technical approaches and trade-offs
- Creating technical diagrams (architecture, sequence, data flow)
- Designing APIs (REST, GraphQL, gRPC) with versioning and compatibility
- Planning database schema changes or migrations
- Defining rollout strategies for new systems or migrations
- Analyzing performance, scalability, and reliability trade-offs
- Documenting technical decisions with quantitative justification

## Core Concepts

### Concept 1: Architecture Design Levels (C4 Model)

**Level 1: System Context**
- High-level view: System + external dependencies
- Audience: Non-technical stakeholders
- Example: "Web App talks to Stripe, SendGrid, and PostgreSQL"

**Level 2: Container Diagram**
- Major components (services, databases, message queues)
- Audience: Architects, senior engineers
- Example: "API Server, Worker Queue, Redis Cache, Postgres DB"

**Level 3: Component Diagram**
- Internal structure of a container (modules, classes)
- Audience: Engineers implementing the system
- Example: "API Server has Auth, User, Project modules"

**Level 4: Code Diagram**
- Class diagrams, sequence diagrams (optional)
- Audience: Engineers debugging or extending code

### Concept 2: Trade-Off Analysis Framework

**Evaluation Dimensions**:
- **Performance**: Latency, throughput, resource usage
- **Scalability**: Horizontal vs vertical, growth limits
- **Complexity**: Development time, maintenance burden
- **Cost**: Infrastructure, licensing, operational overhead
- **Reliability**: Fault tolerance, recovery, uptime
- **Maintainability**: Code clarity, debugging, extensibility

**Quantification**: Always include numbers where possible
- "50% faster" vs "faster"
- "$500/month at 10k users" vs "expensive"
- "2 weeks development" vs "takes time"

### Concept 3: API Design Principles

**Versioning Strategies**:
- URI versioning: `/api/v1/users`, `/api/v2/users`
- Header versioning: `Accept: application/vnd.api+json; version=1`
- Deprecation timeline: Announce → Grace period → Sunset

**Backwards Compatibility**:
- Add fields, don't remove (deprecate instead)
- Use optional parameters (don't require new fields)
- Version breaking changes (new endpoints)

**Error Handling**:
- Use HTTP status codes correctly (200, 201, 400, 401, 404, 500)
- Return structured errors (error_code, message, field_errors)
- Include request_id for debugging

---

## Patterns

### Pattern 1: Architecture Diagram (C4 Level 2 - Container)

**When to use**:
- Designing system architecture for RFC
- Illustrating component interactions

```markdown
## System Architecture: Real-Time Analytics Platform

### Container Diagram (C4 Level 2)

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Clients                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│    ┌──────────┐          ┌──────────┐          ┌──────────┐    │
│    │   Web    │          │  Mobile  │          │    API   │    │
│    │  Client  │          │   App    │          │  Client  │    │
│    └────┬─────┘          └────┬─────┘          └────┬─────┘    │
│         │                     │                      │           │
└─────────┼─────────────────────┼──────────────────────┼───────────┘
          │                     │                      │
          │ HTTPS               │ HTTPS                │ HTTPS
          │                     │                      │
          ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Load Balancer (NGINX)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  API Server  │   │  API Server  │   │  API Server  │
│   (Node.js)  │   │   (Node.js)  │   │   (Node.js)  │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       │                  │                  │
       ├──────────────────┴──────────────────┤
       │                                     │
       ▼                                     ▼
┌─────────────┐                       ┌─────────────┐
│   Redis     │                       │  RabbitMQ   │
│   Cache     │                       │   Queue     │
│             │                       │             │
└─────────────┘                       └──────┬──────┘
                                             │
                                             │
                                             ▼
                                      ┌──────────────┐
                                      │   Worker     │
                                      │  Processes   │
                                      │ (Python)     │
                                      └──────┬───────┘
                                             │
       ┌─────────────────────────────────────┤
       │                                     │
       ▼                                     ▼
┌─────────────┐                       ┌─────────────┐
│ PostgreSQL  │                       │  S3 Bucket  │
│  Database   │                       │   (Logs)    │
│             │                       │             │
└─────────────┘                       └─────────────┘
```

### Component Responsibilities

**Load Balancer (NGINX)**:
- Distributes traffic across API servers (round-robin)
- Terminates SSL/TLS
- Rate limiting (1000 req/min per IP)

**API Server (Node.js + Express)**:
- Handles HTTP requests
- Authentication/authorization (JWT)
- Business logic
- Publishes jobs to RabbitMQ

**Redis Cache**:
- Session storage (JWT tokens)
- Query result caching (TTL: 5 min)
- Rate limit counters

**RabbitMQ Queue**:
- Async job processing (reports, exports)
- Decouples API from heavy workloads

**Worker Processes (Python)**:
- Consumes jobs from RabbitMQ
- Generates reports, processes data
- Uploads results to S3

**PostgreSQL Database**:
- Primary data store (users, projects, analytics)
- ACID transactions
- Read replicas for analytics queries

**S3 Bucket**:
- Stores generated reports, exports
- CloudFront CDN for fast delivery
```

### Pattern 2: Sequence Diagram for Complex Workflows

**Use case**: Illustrating multi-step interactions

```markdown
## Sequence Diagram: User Signup Flow

```
Client          API Server      Database       SendGrid
  │                 │               │              │
  │  POST /signup   │               │              │
  ├────────────────>│               │              │
  │                 │               │              │
  │                 │ Validate      │              │
  │                 │ email/password│              │
  │                 │               │              │
  │                 │  Check if     │              │
  │                 │  email exists │              │
  │                 ├──────────────>│              │
  │                 │<──────────────┤              │
  │                 │  (not found)  │              │
  │                 │               │              │
  │                 │  Create user  │              │
  │                 ├──────────────>│              │
  │                 │<──────────────┤              │
  │                 │  (user_id)    │              │
  │                 │               │              │
  │                 │  Generate     │              │
  │                 │  verify token │              │
  │                 │               │              │
  │                 │ Send verification email      │
  │                 ├─────────────────────────────>│
  │                 │<─────────────────────────────┤
  │                 │            (200 OK)          │
  │                 │               │              │
  │   201 Created   │               │              │
  │<────────────────┤               │              │
  │  {user_id, ...} │               │              │
  │                 │               │              │
  │                 │               │   Email      │
  │                 │               │   delivered  │
  │                 │               │   to user    │
  │                 │               │              │
```

### Error Scenario: Email Already Exists

```
Client          API Server      Database
  │                 │               │
  │  POST /signup   │               │
  ├────────────────>│               │
  │                 │  Check email  │
  │                 ├──────────────>│
  │                 │<──────────────┤
  │                 │  (found!)     │
  │                 │               │
  │  400 Bad Req    │               │
  │<────────────────┤               │
  │  {error_code:   │               │
  │   EMAIL_IN_USE} │               │
```
```

### Pattern 3: Trade-Off Matrix for Alternatives

**Use case**: Comparing technical approaches objectively

```markdown
## Trade-Off Analysis: Caching Strategy

### Options Evaluated

| Criterion | Redis (In-Memory) | Postgres (DB Cache) | Memcached | CDN (CloudFront) |
|-----------|-------------------|---------------------|-----------|------------------|
| **Latency** | <1ms (local) | ~10ms (network) | <1ms (local) | ~50ms (edge) |
| **Scalability** | Horizontal (sharding) | Vertical (limited) | Horizontal | Infinite |
| **Persistence** | Optional (RDB/AOF) | Yes (durable) | No (memory only) | No (edge cache) |
| **Complexity** | Medium (setup cluster) | Low (already have DB) | Low (simple) | Medium (CDN config) |
| **Cost** | $50/mo (10GB instance) | $0 (included) | $30/mo (5GB) | $0.02/GB (traffic) |
| **Use Case Fit** | Session + query cache | Small datasets | Session only | Static assets |
| **Max TTL** | Custom (hours) | Custom (hours) | 30 days | 1 year |

### Decision: Redis

**Chosen**: Redis (in-memory cache with persistence)

**Rationale**:
- **Latency**: <1ms meets requirement (<10ms)
- **Scalability**: Can shard by cache key if needed (10k→100k users)
- **Persistence**: RDB snapshots prevent cache stampede on restart
- **Cost**: $50/mo acceptable for performance gain (vs $0 DB cache, but 10x slower)
- **Flexibility**: Supports sessions, query cache, rate limiting, pub/sub

**Runner-Up**: Postgres materialized views (for read-heavy analytics only)

**Rejected**:
- **Memcached**: No persistence (unacceptable for rate limiting data)
- **CDN**: Only for static assets (API responses are dynamic)
```

### Pattern 4: API Design with Versioning

**Use case**: Designing RESTful API with backwards compatibility

```markdown
## API Design: User Management

### Base URL
- Production: `https://api.example.com`
- Staging: `https://api-staging.example.com`

### Versioning Strategy
- URI versioning: `/v1/users`, `/v2/users`
- Current version: `v1`
- Deprecation policy: 12 months notice, 6 months grace period

### Endpoints

#### `POST /v1/users` - Create User
**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass1!",
  "display_name": "John Doe"  // optional
}
```

**Response (201 Created)**:
```json
{
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "display_name": "John Doe",
  "created_at": "2025-10-25T14:30:00Z"
}
```

**Response (400 Bad Request)**:
```json
{
  "error_code": "VALIDATION_ERROR",
  "error_message": "Invalid input",
  "request_id": "req_xyz789",
  "field_errors": {
    "email": "Email already in use",
    "password": "Password must include a number"
  }
}
```

**Rate Limiting**:
- 5 signups per IP per hour
- Headers: `X-RateLimit-Limit: 5`, `X-RateLimit-Remaining: 3`

#### `GET /v1/users/:id` - Get User Profile
**Authentication**: Required (JWT in `Authorization: Bearer <token>`)

**Response (200 OK)**:
```json
{
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "display_name": "John Doe",
  "profile_photo_url": "https://cdn.example.com/photos/abc123.jpg",
  "created_at": "2025-10-25T14:30:00Z",
  "preferences": {
    "theme": "dark",
    "notifications": true
  }
}
```

**Response (404 Not Found)**:
```json
{
  "error_code": "USER_NOT_FOUND",
  "error_message": "User with ID usr_abc123 not found",
  "request_id": "req_xyz789"
}
```

### Breaking Change Example (v1 → v2)

**v1**: Returns `created_at` as Unix timestamp (integer)
```json
{"created_at": 1698249600}
```

**v2**: Returns `created_at` as ISO 8601 string (breaking change)
```json
{"created_at": "2025-10-25T14:30:00Z"}
```

**Migration Plan**:
1. Announce deprecation: 2025-11-01 (email, docs, changelog)
2. Grace period: v1 supported until 2026-05-01 (6 months)
3. Sunset: v1 returns 410 Gone after 2026-05-01
```

### Pattern 5: Database Schema Design with Migrations

**Use case**: Planning schema changes with rollback strategy

```markdown
## Database Schema: User Authentication

### Current Schema (v1)
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Proposed Schema (v2) - Add Email Verification
```sql
-- Migration: Add email verification columns
ALTER TABLE users
  ADD COLUMN email_verified BOOLEAN DEFAULT FALSE,
  ADD COLUMN email_verify_token VARCHAR(255),
  ADD COLUMN email_verify_sent_at TIMESTAMP;

-- Create index for fast token lookup
CREATE INDEX idx_users_verify_token ON users(email_verify_token)
  WHERE email_verify_token IS NOT NULL;

-- Backfill existing users (mark as verified)
UPDATE users SET email_verified = TRUE WHERE created_at < NOW();
```

### Migration Plan

**Step 1: Deploy Schema Change** (Zero Downtime)
- Run `ALTER TABLE` during low-traffic window
- PostgreSQL locks table briefly (<1s for 100k rows)
- Backfill existing users as verified (no behavior change)

**Step 2: Deploy Code Changes**
- New signups: Set `email_verified = FALSE`, send verification email
- Login: Check `email_verified`, block if false
- Feature flag: `REQUIRE_EMAIL_VERIFICATION` (gradual rollout)

**Step 3: Monitor**
- Track verification rate (target: 80% verify within 24 hours)
- Monitor support tickets (expect questions)
- Alert if verification email delivery rate <95%

**Rollback Plan**:
- Revert code: Disable `REQUIRE_EMAIL_VERIFICATION` flag
- Keep schema changes (no need to drop columns, just stop using)
- If catastrophic: Drop columns (loses verification data)
```

### Pattern 6: Migration Strategy (Old System → New System)

**Use case**: Transitioning between systems with zero downtime

```markdown
## Migration: Monolith → Microservices (Auth Service)

### Current State
- Monolithic Rails app handles everything (auth, users, projects)
- Auth logic mixed with business logic (tight coupling)
- 100k active users, 10k requests/min peak

### Target State
- Standalone Auth Service (Node.js + JWT)
- Microservices for users, projects (separate from auth)
- Same 100k users, seamless migration

### Migration Strategy: Strangler Fig Pattern

**Phase 1: Build Auth Service (Parallel Run)**
- Build new Auth Service (JWT-based)
- Dual-write: Monolith writes to both old session DB and new Auth Service
- Read from old system only (no behavior change)
- Duration: 2 weeks

**Phase 2: Shadow Traffic**
- Route 1% of login requests to Auth Service (shadow mode)
- Compare results with monolith (validate correctness)
- Fix discrepancies, increase to 10%, then 50%
- Duration: 2 weeks

**Phase 3: Gradual Cutover**
- Route 10% of users to Auth Service (read + write)
- Monitor latency, error rates, user complaints
- Increase to 50%, then 100% over 4 weeks
- Duration: 4 weeks

**Phase 4: Monolith Deprecation**
- All auth traffic goes to Auth Service
- Remove auth code from monolith (dead code)
- Decommission old session database
- Duration: 2 weeks

### Rollback Plan
- Feature flag: `USE_AUTH_SERVICE` (toggle per user)
- If Auth Service fails, revert flag → monolith
- Monitoring: Alert if Auth Service latency >100ms or error rate >1%

### Metrics
- **Latency**: Auth Service <50ms (vs monolith 80ms)
- **Error Rate**: <0.1% (vs monolith 0.2%)
- **User Impact**: Zero failed logins during migration
```

### Pattern 7: Performance Benchmarking

**Use case**: Quantifying trade-offs with real data

```markdown
## Performance Benchmark: Caching Strategy

### Test Setup
- Dataset: 1M user records
- Query: `GET /users/:id/profile` (fetch user + projects)
- Load: 1,000 requests/sec (sustained)
- Tool: Apache Bench (`ab -n 10000 -c 100`)

### Results

| Approach | p50 Latency | p95 Latency | p99 Latency | Throughput | CPU Usage |
|----------|-------------|-------------|-------------|------------|-----------|
| **No Cache** (baseline) | 120ms | 350ms | 850ms | 800 req/s | 80% |
| **Redis Cache** | 8ms | 15ms | 45ms | 8,000 req/s | 20% |
| **Postgres Materialized View** | 25ms | 60ms | 150ms | 3,000 req/s | 40% |
| **In-Memory Map** (Node.js) | 2ms | 5ms | 12ms | 10,000 req/s | 30% |

### Analysis

**Winner**: Redis Cache (chosen)
- **Latency**: 15x faster than no cache (p95: 15ms vs 350ms) ✅
- **Throughput**: 10x higher (8k vs 800 req/s) ✅
- **Cost**: $50/mo for Redis instance (acceptable)
- **Risk**: Single point of failure (mitigated with Redis Sentinel)

**Runner-Up**: In-Memory Map
- **Faster**: 2ms latency, 10k req/s
- **Problem**: No persistence (lost on restart), no sharing across servers
- **Verdict**: Only viable for single-server deployment

**Rejected**: Postgres Materialized View
- **Reason**: Still 25ms latency (vs <10ms requirement)
- **Use Case**: Good for analytics, not real-time API
```

### Pattern 8: Failure Mode Analysis

**Use case**: Anticipating what can go wrong

```markdown
## Failure Mode Analysis: Payment Processing

### Failure Scenarios

#### 1. Stripe API Down
**Probability**: Low (99.99% uptime SLA)
**Impact**: High (no payments processed)
**Mitigation**:
- Detect: Health check every 30s, alert if 3 failures
- Respond: Show maintenance page, queue payment attempts
- Recover: Retry queued payments when Stripe recovers

#### 2. Database Connection Pool Exhausted
**Probability**: Medium (under high load)
**Impact**: High (API returns 500 errors)
**Mitigation**:
- Prevent: Set connection pool limit (50 connections)
- Detect: Monitor active connections (alert if >80%)
- Respond: Reject new requests with 503 (retry-after header)
- Recover: Scale database read replicas, optimize queries

#### 3. Redis Cache Eviction
**Probability**: Medium (if cache fills up)
**Impact**: Low (fallback to database, slower but works)
**Mitigation**:
- Prevent: Set max memory limit, use LRU eviction policy
- Detect: Monitor cache hit rate (alert if <80%)
- Respond: Cache miss → fetch from DB, repopulate cache
- Recover: Increase Redis memory, optimize cache keys

#### 4. Webhook Delivery Failure
**Probability**: High (network issues, client downtime)
**Impact**: Medium (events not processed by client)
**Mitigation**:
- Detect: HTTP status != 200 or timeout (>30s)
- Respond: Exponential backoff retry (1s, 2s, 4s, 8s, 16s)
- Recover: Dead letter queue after 5 failures, alert for manual review

### Circuit Breaker Pattern
```javascript
// Protect against cascading failures
class CircuitBreaker {
  constructor(failureThreshold = 5, timeout = 60000) {
    this.failureCount = 0;
    this.failureThreshold = failureThreshold;
    this.timeout = timeout;
    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
  }

  async call(fn) {
    if (this.state === 'OPEN') {
      throw new Error('Circuit breaker is OPEN');
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  onSuccess() {
    this.failureCount = 0;
    this.state = 'CLOSED';
  }

  onFailure() {
    this.failureCount++;
    if (this.failureCount >= this.failureThreshold) {
      this.state = 'OPEN';
      setTimeout(() => { this.state = 'HALF_OPEN'; }, this.timeout);
    }
  }
}

// Usage: Protect Stripe API calls
const stripeBreaker = new CircuitBreaker(5, 60000);
const charge = await stripeBreaker.call(() => stripe.charges.create({...}));
```
```

---

## Quick Reference

### Architecture Diagram Types

```
Diagram Type | Use Case | Audience
-------------|----------|----------
System Context (C4-1) | High-level overview | Leadership, PM
Container (C4-2) | Major components | Architects, senior eng
Component (C4-3) | Internal structure | Engineers
Sequence | Multi-step workflows | Engineers debugging
Data Flow | Data movement | Data engineers
```

### Trade-Off Evaluation Checklist

```
Dimension | Question to Ask
----------|----------------
Performance | What is p95 latency? Throughput?
Scalability | How does it scale? (horizontal/vertical)
Complexity | How long to implement? Maintain?
Cost | $ per month at 10k users? At 100k?
Reliability | What's uptime SLA? Failure modes?
Maintainability | How easy to debug? Extend?
```

### API Versioning Strategies

```
Strategy | Example | Pros | Cons
---------|---------|------|-----
URI | /v1/users | Simple, explicit | URL proliferation
Header | Accept: v=1 | Clean URLs | Less visible
Query Param | /users?v=1 | Easy to test | Ugly URLs
```

### Key Guidelines

```
✅ DO: Quantify trade-offs (numbers, not adjectives)
✅ DO: Create diagrams for complex architectures
✅ DO: Benchmark alternatives with real data
✅ DO: Plan failure modes and mitigations
✅ DO: Design APIs with backwards compatibility

❌ DON'T: Pick solutions without evaluating alternatives
❌ DON'T: Use vague terms ("fast", "scalable") without metrics
❌ DON'T: Ignore migration complexity
❌ DON'T: Skip performance benchmarking
❌ DON'T: Design APIs without versioning strategy
```

---

## Anti-Patterns

### Critical Violations

❌ **No Alternatives Analysis**: Presenting one solution without comparison
```markdown
# ❌ NEVER:
We'll use MongoDB for the database.

# ✅ CORRECT:
## Database Options
1. **PostgreSQL**: ACID, relations, complex queries (chosen)
2. **MongoDB**: Flexible schema, horizontal scaling
   - Rejected: No ACID for financial transactions (deal-breaker)
3. **DynamoDB**: Managed, infinite scale
   - Rejected: Vendor lock-in, limited query flexibility

**Decision**: Postgres for ACID guarantees and query richness.
```

❌ **Premature Optimization**: Optimizing without measuring
✅ **Correct approach**: Benchmark current performance, identify bottleneck, optimize

### Common Mistakes

❌ **Vague Performance Claims**: "Redis is faster than Postgres"
```markdown
# ❌ Don't:
Redis is faster, so we'll use it for caching.

# ✅ Correct:
## Benchmark Results
- Redis: 8ms p95 latency, 8k req/s throughput
- Postgres: 120ms p95 latency, 800 req/s throughput
- **Decision**: Redis for 15x latency improvement
```

❌ **No Failure Analysis**: Assuming happy path only
✅ **Better**: Document failure modes, circuit breakers, fallbacks

❌ **API Without Versioning**: No plan for breaking changes
✅ **Better**: URI versioning, deprecation policy, migration guide

❌ **Big Bang Migration**: Switching all users at once
✅ **Better**: Strangler fig pattern (gradual cutover with rollback plan)

---

## Related Skills

- `rfc-structure-format.md` - RFC document templates and formatting
- `rfc-consensus-building.md` - Driving approval for technical designs
- `rfc-decision-documentation.md` - Documenting decisions and ADRs
- `api-design-rest.md` - Deep dive on REST API best practices
- `database-postgres-optimization.md` - Postgres-specific performance tuning

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
