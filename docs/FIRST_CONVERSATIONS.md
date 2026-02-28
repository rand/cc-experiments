# First Conversations: cc-polymath in Action

This guide shows six complete, realistic examples of how cc-polymath works in practice. Each demonstrates auto-discovery in action and shows the natural flow of conversation with Claude Code.

---

## Example 1: Building a Next.js Dashboard

**Context**: You're starting a real-time analytics dashboard for a SaaS product and need guidance on architecture and best practices.

**User**: "I need to build a Next.js dashboard that displays real-time metrics. Users should see live updates as data changes, and I want best practices for performance."

**Auto-Discovery**: ✓ Triggered `discover-frontend`

**Conversation Flow**:

```
Claude: I'm loading frontend skills for Next.js dashboard development...
  
Loaded: discover-frontend (235 lines)
→ react-component-patterns (318 lines)
→ nextjs-app-router (402 lines)
→ react-data-fetching (356 lines)
→ frontend-performance (289 lines)

Based on your requirements, here's what I recommend:

1. **Server Components for Data**: Use Next.js 14+ Server Components
   to fetch data at the server layer, reducing client bundle size.

2. **Real-time Updates**: Choose between:
   - Server-Sent Events (SSE) - simple, one-directional updates
   - WebSocket via library like Socket.io - full bidirectional
   - React Query polling - simple client-side approach

3. **Performance**: Use React Suspense for loading states,
   implement incremental static regeneration (ISR) for stable data.

Should we set up Server Components with SWR for real-time data,
or do you need WebSocket-level bidirectionality?
```

**User**: "WebSockets would be better for our use case. What about state management across the dashboard?"

**Claude**: "Great! For WebSocket + state management, I'm loading additional skills...

Loaded:
→ react-state-management (372 lines)
→ browser-concurrency (298 lines)

For real-time dashboards, I recommend this pattern:

1. **Use Zustand** (minimal, reactive):
   - Lightweight state container
   - Integrates well with Next.js
   - Minimal re-renders

2. **Separate Real-time Store**:
   - Keep server state separate from WebSocket state
   - Use a dedicated hook: useRealtimeMetrics()
   - Handles reconnection and backpressure automatically

3. **Suspense Boundaries**:
   - Wrap dashboard sections in <Suspense> for independent loading
   - Each metric card loads independently

Here's the architecture:

```typescript
// stores/metrics.ts - Zustand store for real-time data
import { create } from 'zustand'

interface MetricUpdate {
  timestamp: number
  value: number
  metric: string
}

export const useMetricsStore = create((set) => ({
  metrics: {},
  updateMetric: (update: MetricUpdate) =>
    set((state) => ({
      metrics: {
        ...state.metrics,
        [update.metric]: update.value
      }
    }))
}))

// hooks/useRealtimeMetrics.ts - WebSocket connection
export function useRealtimeMetrics() {
  const updateMetric = useMetricsStore(s => s.updateMetric)

  useEffect(() => {
    const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL)

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data)
      updateMetric(update)
    }

    return () => ws.close()
  }, [updateMetric])
}
```

Ready to implement this? I can guide you through Server Components,
Zustand setup, and WebSocket handling step-by-step.
```

**Result**:
- Architecture decision made in 2 minutes
- Zustand + Server Components chosen for optimal performance
- Code scaffolding ready to build from
- Real-time updates implemented within 30 minutes
- Initial dashboard metrics displaying live data within 1 hour

**Skills Used**:
- discover-frontend (gateway)
- react-component-patterns (component design)
- nextjs-app-router (Server Components, routing)
- react-state-management (Zustand patterns)
- react-data-fetching (data lifecycle)
- browser-concurrency (WebSocket management)

---

## Example 2: Optimizing Postgres Queries

**Context**: Your application is slowing down with database growth. Queries that used to run in milliseconds now take seconds.

**User**: "Our database is getting slow. A query that lists user posts with comments is taking 2.3 seconds. I need to figure out what's wrong and fix it."

**Auto-Discovery**: ✓ Triggered `discover-database`

**Conversation Flow**:

```
Claude: I'm loading database optimization skills...

Loaded: discover-database (218 lines)
→ postgres-query-optimization (445 lines)
→ postgres-schema-design (389 lines)
→ orm-patterns (356 lines)

Let's diagnose this together. First, I need to see:

1. The slow query (SQL or ORM code)
2. Your schema (table definitions)
3. Data volume (approximate rows)

Can you share the current implementation?
```

**User**: Shares:
```python
# Django ORM
posts = Post.objects.filter(user_id=user_id).prefetch_related('comments')

# Generated SQL roughly:
# SELECT * FROM posts WHERE user_id = 1
# SELECT * FROM comments WHERE post_id IN (...)
```

**Claude**: "Loaded your code. I can see a few issues using EXPLAIN analysis.
Let me diagnose:

Loaded:
→ orm-patterns (full guide)

```bash
# EXPLAIN (ANALYZE, BUFFERS) shows:
Seq Scan on posts WHERE user_id = 1
  Planning: 0.1ms
  Execution: 1800ms (reading all 500K posts!)
  Actual loops: 1

Problem #1: NO INDEX on posts.user_id
```

Here's your issues:

1. **Missing Index** on posts(user_id)
   - Currently doing FULL TABLE SCAN of 500K rows
   - Adding index: 1800ms → 15ms

2. **N+1 Problem in Comments**
   - Your prefetch_related works, but missing index on comments.post_id
   - Adding index: 500ms → 50ms

3. **Query selects too many columns**
   - Add .only('id', 'title', 'created_at') to reduce I/O
   - Saves 30% network overhead

Here's the fix:

```sql
-- Migration 1: Fix posts lookup
CREATE INDEX idx_posts_user_id ON posts(user_id);

-- Migration 2: Fix comment loading
CREATE INDEX idx_comments_post_id ON comments(post_id);
```

And in Django:

```python
posts = (Post.objects.filter(user_id=user_id)
    .prefetch_related('comments')
    .only('id', 'title', 'created_at', 'user_id'))
```

Expected improvement: 2.3s → 45ms (51x faster)"
```

**User**: "Perfect! Should I create these as migrations?"

**Claude**: "Already covered. Loading migration patterns...

Loaded:
→ postgres-migrations (401 lines)

Here's the safe way to add these:

```sql
-- migrations/0003_optimize_posts_queries.sql
-- Part 1: Add indexes (safe, no locking in Postgres 11+)
CREATE INDEX CONCURRENTLY idx_posts_user_id 
  ON posts(user_id);

CREATE INDEX CONCURRENTLY idx_comments_post_id 
  ON comments(post_id);

-- Add monitoring
ANALYZE posts;
ANALYZE comments;
```

Use CREATE INDEX CONCURRENTLY in production.
It won't lock writes while creating the index.

Your migration is complete. Deploy with confidence."
```

**Result**:
- Root cause identified in 3 minutes
- Query time improved from 2.3 seconds to 45ms (51x faster)
- Safe migration strategy provided
- Indexes deployed without downtime
- Application performance restored in under 15 minutes

**Skills Used**:
- discover-database (gateway)
- postgres-query-optimization (EXPLAIN analysis, indexes)
- postgres-schema-design (understanding structure)
- postgres-migrations (safe deployment)
- orm-patterns (N+1 detection)

---

## Example 3: Designing a REST API

**Context**: You're building the backend for a task management application and need to design a scalable REST API.

**User**: "I'm building a task management API. I need to design endpoints for tasks, lists, and user collaboration features. What should the API structure look like?"

**Auto-Discovery**: ✓ Triggered `discover-api`

**Conversation Flow**:

```
Claude: Loading API design skills...

Loaded: discover-api (242 lines)
→ rest-api-design (468 lines)
→ api-authentication (412 lines)
→ api-authorization (395 lines)
→ api-rate-limiting (287 lines)
→ api-error-handling (324 lines)

For a task management API, let me design the resource model first.

Resources (nouns):
- Users (/users)
- Lists (/lists) - collections of tasks
- Tasks (/tasks)
- Comments (/tasks/{id}/comments)
- Shares (/lists/{id}/shares) - permissions

Proposed endpoints:

## Task Management API Design

### Lists
- GET /lists - my lists
- POST /lists - create list
- GET /lists/{id} - get list with tasks
- PATCH /lists/{id} - update list
- DELETE /lists/{id} - delete list
- GET /lists/{id}/members - who has access
- POST /lists/{id}/share - share with users

### Tasks
- GET /lists/{id}/tasks - list tasks (supports filtering)
- POST /lists/{id}/tasks - create task
- GET /tasks/{id} - get single task
- PATCH /tasks/{id} - update task
- DELETE /tasks/{id} - delete task
- POST /tasks/{id}/assign - assign to user

### Comments
- GET /tasks/{id}/comments - task comments
- POST /tasks/{id}/comments - add comment
- PATCH /comments/{id} - edit comment
- DELETE /comments/{id} - delete comment

### Collaboration
- GET /tasks/{id}/activity - activity log
- GET /users/me - current user profile

Each endpoint returns consistent responses with error handling.
Should we implement authentication first, or finalize the schema?
```

**User**: "Authentication is critical. What's the best approach?"

**Claude**: "Perfect. Loading authentication patterns...

Loaded:
→ api-authentication (full guide)

For a collaborative app, I recommend JWT + Refresh tokens:

```typescript
// POST /auth/login
{
  "email": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "accessToken": "eyJhbGc...", // 15-min expiry
  "refreshToken": "ref_...",    // 7-day expiry
  "user": {
    "id": "user_123",
    "email": "user@example.com"
  }
}

// POST /auth/refresh
{
  "refreshToken": "ref_..."
}
```

For authorization, we need role-based access:

Loaded:
→ api-authorization (full guide)

```typescript
// User roles per list
enum Role {
  OWNER = 'owner',      // create, delete, manage members
  EDITOR = 'editor',    // create/edit tasks
  VIEWER = 'viewer'     // read-only
}

// Middleware checks role
async function checkAccess(req, res, next) {
  const listId = req.params.id
  const userId = req.user.id
  
  const access = await db.listAccess.findUnique({
    where: { listId_userId: { listId, userId } }
  })
  
  if (!access) throw new Forbidden()
  req.userRole = access.role
  next()
}
```

For shared APIs, rate limiting prevents abuse:

Loaded:
→ api-rate-limiting (full guide)

```typescript
// 100 requests per 15 minutes per user
const rateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  keyGenerator: (req) => req.user.id
})

app.use('/api/', rateLimiter)
```

Finally, standardized error responses:

Loaded:
→ api-error-handling (RFC 7807)

```typescript
// All errors follow RFC 7807
{
  "type": "https://api.tasks.example.com/errors/unauthorized",
  "title": "Unauthorized",
  "status": 403,
  "detail": "You do not have access to this list",
  "instance": "/lists/list_456"
}
```

Here's the complete OpenAPI spec structure...
```

**User**: "This is great. Can you show the full OpenAPI schema?"

**Claude**: "Absolutely. Here's your API spec in OpenAPI 3.0:

```yaml
openapi: 3.0.0
info:
  title: Task Management API
  version: 1.0.0

servers:
  - url: https://api.tasks.example.com
    description: Production

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - bearerAuth: []

paths:
  /auth/login:
    post:
      summary: User login
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                email: { type: string }
                password: { type: string }
      responses:
        200:
          description: Login successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'

  /lists:
    get:
      summary: Get user's lists
      responses:
        200:
          description: List of lists
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/List'
    post:
      summary: Create new list
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateListRequest'
      responses:
        201:
          description: List created

  /lists/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
    get:
      summary: Get list details with tasks
    patch:
      summary: Update list
    delete:
      summary: Delete list

  /lists/{id}/tasks:
    get:
      summary: Get tasks in list
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [todo, in_progress, done]
    post:
      summary: Create task

  /tasks/{id}:
    get:
      summary: Get single task
    patch:
      summary: Update task
    delete:
      summary: Delete task

  /tasks/{id}/comments:
    get:
      summary: Get task comments
    post:
      summary: Add comment

components:
  schemas:
    List:
      type: object
      properties:
        id: { type: string }
        name: { type: string }
        description: { type: string }
        role: { type: string, enum: [owner, editor, viewer] }
        taskCount: { type: integer }
        members: { type: array }

    Task:
      type: object
      properties:
        id: { type: string }
        title: { type: string }
        description: { type: string }
        status: { enum: [todo, in_progress, done] }
        priority: { enum: [low, medium, high] }
        assignedTo: { type: string }
        dueDate: { type: string, format: date-time }
        comments: { type: array }
```

Ready to implement in Node.js + Express or another framework?"
```

**Result**:
- Complete API design in 15 minutes
- Resource modeling done
- Authentication strategy chosen (JWT + Refresh)
- Authorization pattern defined (role-based)
- Rate limiting strategy selected
- Full OpenAPI 3.0 specification ready
- Implementation-ready architecture document created

**Skills Used**:
- discover-api (gateway)
- rest-api-design (resource modeling, HTTP semantics)
- api-authentication (JWT patterns)
- api-authorization (RBAC implementation)
- api-rate-limiting (abuse prevention)
- api-error-handling (RFC 7807 responses)

---

## Example 4: Creating Visual Documentation

**Context**: You need to document your deployment process for new team members joining next week.

**User**: "I need to create a clear diagram showing our deployment pipeline. We have development, staging, and production environments with automatic tests in between."

**Auto-Discovery**: ✓ Triggered `discover-engineering`

**Conversation Flow**:

```
Claude: Loading diagram creation skills...

Loaded: discover-engineering (195 lines)
→ mermaid-flowcharts (367 lines)
→ mermaid-sequence-diagrams (401 lines)

For deployment pipelines, a flowchart works best. Here's your diagram:

\`\`\`mermaid
graph LR
    A["Developer<br/>Pushes Code"] -->|git push| B["GitHub<br/>Webhook"]
    B -->|triggers| C["Run Unit<br/>Tests"]
    C -->|✓ pass| D["Build Docker<br/>Image"]
    C -->|✗ fail| E["Notify Developer<br/>in Slack"]
    E --> A
    
    D -->|push image| F["Deploy to<br/>Staging"]
    F -->|wait 30s| G["Run E2E<br/>Tests"]
    G -->|✓ pass| H["Wait for<br/>Approval"]
    G -->|✗ fail| I["Rollback<br/>Staging"]
    I --> E
    
    H -->|approved| J["Deploy to<br/>Production"]
    J -->|CloudFlare CDN| K["Live for<br/>Users"]
    J -->|smoke tests| L{All Good?}
    L -->|yes| M["Send Success<br/>Alert"]
    L -->|no| N["Automatic<br/>Rollback"]
    
    N -->|call prev version| K
    N --> E
    
    style A fill:#e1f5ff
    style C fill:#fff3e0
    style G fill:#fff3e0
    style J fill:#c8e6c9
    style K fill:#c8e6c9
    style E fill:#ffcdd2
    style M fill:#c8e6c9
\`\`\`

This shows:
- Developer trigger
- Test gates (unit → E2E)
- Approval checkpoint
- Production deployment
- Automatic rollback on failure
- Slack notifications

Would you like to add more detail to any stage?
```

**User**: "Can you also show what happens when a deploy fails in production? We have automatic rollback."

**Claude**: "Great question. Let me add the failure path with more detail...

```mermaid
graph TD
    A["Developer<br/>Pushes Code"] -->|git push| B["GitHub<br/>Webhook"]
    B -->|triggers| C["Run Unit Tests"]
    C -->|✓ pass| D["Build Docker<br/>Image"]
    C -->|✗ fail| E["Notify: Tests Failed"]
    E -->|slack #deployments| F["Await Fix"]
    F --> A
    
    D -->|push to ECR| G["Deploy to<br/>Staging"]
    G -->|wait 30s| H["Run E2E Tests"]
    H -->|✓ pass| I["Await Manual<br/>Approval"]
    H -->|✗ fail| J["Notify: E2E Failed"]
    J --> E
    
    I -->|approved| K["Get Previous<br/>Deploy Hash"]
    K -->|v1.2.3| L["Deploy to<br/>Production"]
    
    L -->|point DNS| M["Traffic → New<br/>Release v1.3.0"]
    L -->|5min window| N["Smoke Tests"]
    
    N -->|✓ All Checks Pass| O["Green Checkmark<br/>Success Alert"]
    O --> P["Canary 5%<br/>traffic"]
    P -->|5min ok| Q["100% Traffic<br/>New Release"]
    
    N -->|✗ Error Rate High| R["ROLLBACK<br/>Initiated"]
    R -->|blue/green| S["Traffic → Previous<br/>Release v1.2.3"]
    S -->|instant| T["Notify: Rollback<br/>Occurred"]
    T -->|ping oncall| U["Engineer Reviews<br/>What Failed"]
    U --> V["Incident Report<br/>+ Post-Mortem"]
    
    Q --> W["✓ Deployment<br/>Complete"]
    V --> X["Schedule Fix<br/>for Next Release"]
    
    style A fill:#e1f5ff
    style C fill:#fff3e0
    style H fill:#fff3e0
    style L fill:#c8e6c9
    style O fill:#c8e6c9
    style Q fill:#c8e6c9
    style R fill:#ffcdd2
    style T fill:#ffcdd2
    style E fill:#ffcdd2
    style J fill:#ffcdd2
\`\`\`

Key features:
- Blue/Green deployment (zero downtime)
- 5% canary traffic before full rollout
- Automatic rollback on error rate spike
- Slack notifications at each gate
- Post-incident review captured
- 5-minute production validation window

This diagram is production-ready. Want me to add environment details?"
```

**Result**:
- Professional deployment diagram created in 5 minutes
- Flowchart clearly shows the entire pipeline
- Failure scenarios documented
- Color-coded for easy scanning
- Ready to share with new team members
- Can be dropped directly into documentation wiki
- Easily updated as process evolves

**Skills Used**:
- discover-engineering (gateway)
- mermaid-flowcharts (process flows, decision logic)
- mermaid-specialized (optional for Gantt view if needed)

---

## Example 5: Choosing a Database

**Context**: You're architecting a new service and need to decide between different database technologies based on your requirements.

**User**: "We're building a new feature that tracks user activity events. We might get 50,000 events per second. Should we use PostgreSQL, MongoDB, or Redis? What are the tradeoffs?"

**Auto-Discovery**: ✓ Triggered `discover-database`

**Conversation Flow**:

```
Claude: Loading database selection framework...

Loaded: discover-database (218 lines)
→ database-selection (456 lines)
→ postgres-schema-design (389 lines)
→ mongodb-document-design (402 lines)
→ redis-data-structures (378 lines)

This is a classic OLTP (Online Transaction Processing) vs OLAP
(Online Analytical Processing) decision. Let me analyze your requirements:

Requirements Analysis:
- Write volume: 50K events/sec (very high)
- Read pattern: Real-time queries + historical analysis
- Retention: How long keep data?
- Consistency: Is eventual consistency okay?

Let me evaluate each option:

## Option 1: PostgreSQL

Pros:
- ACID transactions (guaranteed consistency)
- Complex queries for analysis
- Strong relationships and JOINs
- Single system of truth

Cons:
- 50K writes/sec requires significant tuning
- Needs connection pooling (PgBouncer)
- Disk I/O becomes bottleneck
- Sharding adds operational complexity

Capacity estimate:
- Single instance: ~5K-10K writes/sec max
- Need sharding or partitioning by user_id
- 3-5 instances minimum
- Storage: 50K events/sec * 86,400 sec/day * 365 days = 1.5 TB/year

Best for: Complex analysis queries, strong consistency

## Option 2: MongoDB

Pros:
- Horizontal scaling (sharding built-in)
- JSON-like documents match events naturally
- Good for time-series data
- Flexible schema (events may vary)

Cons:
- Eventual consistency (by default)
- Less efficient for complex analytical queries
- Higher storage overhead than SQL
- More operational complexity

Capacity estimate:
- Can handle 50K writes/sec across shards
- 2-3 shards initially
- 2.5 TB/year storage

Best for: Event streaming, flexible schema, scaling writes

## Option 3: Redis

Pros:
- Extreme speed (100K+/sec writes)
- Perfect for caching/sessionization
- Pub/Sub for real-time events

Cons:
- All data in memory (expensive)
- Limited analytical querying
- Data loss on failure (persistence adds latency)
- Not designed for event history

Capacity estimate:
- 50K events/sec * 1KB each = 50MB/sec throughput
- 365 days * 86K sec = 1.5B events/year = 1.5TB RAM
- Cost: prohibitive for long-term storage

Best for: Caching, real-time notifications, stream processing

## My Recommendation: Postgres + TimescaleDB Extension

```
Postgres + TimescaleDB is the optimal choice:

TimescaleDB advantages:
- Built on Postgres (ACID + complex queries)
- Optimized for time-series (what you need)
- Handles 50K+ writes/sec (tuned)
- Automatic partitioning by time
- Superior compression (4-10x vs plain SQL)
- Full SQL support for analysis

Architecture:

\`\`\`
Events Stream
    ↓
[Kafka/RabbitMQ Buffer]
    ↓
[Connection Pool: 50 connections]
    ↓
[TimescaleDB Cluster]
  - Primary (writes)
  - 2x Replicas (reads, failover)
    ↓
Archive to S3 for analytics
\`\`\`

Schema:

```sql
-- TimescaleDB auto-partitions by time
CREATE TABLE events (
  time TIMESTAMPTZ NOT NULL,
  user_id UUID NOT NULL,
  event_type VARCHAR NOT NULL,
  properties JSONB,
  
  INDEX ON (user_id, time DESC),
  INDEX ON (event_type, time DESC)
);

-- Create hypertable (automatic partitioning)
SELECT create_hypertable('events', 'time');

-- Retention policy (auto-delete old data)
SELECT add_retention_policy('events', INTERVAL '1 year');

-- Compression (4x reduction)
ALTER TABLE events SET (timescaledb.compress = on);
SELECT add_compression_policy('events', INTERVAL '7 days');
```

Capacity with TimescaleDB:
- Single high-CPU instance: 50K writes/sec ✓
- Compression reduces 1.5TB to ~400GB
- Replica for read scaling + failover
- Automatic archival to S3 after 1 year

Cost estimate (AWS):
- db.r6i.4xlarge x 2 (primary + replica): $4K/month
- vs bare Postgres (need 5 instances): $8K/month
- vs MongoDB (3 shards, Atlas): $6K/month

Winner: TimescaleDB - Best cost, consistency, and queryability
```

**User**: "What about operational complexity? Can we manage this?"

**Claude**: "Great question. TimescaleDB operational overhead is minimal:

Loaded:
→ postgres-migrations (401 lines)

Operational checklist:

```
Day 1: Schema + Hypertable Setup
├─ Create table with indexes
├─ Configure retention policy
├─ Setup compression policy
└─ Test with 5K events/sec

Week 1: Replication Setup
├─ Setup replica instance
├─ Configure streaming replication
├─ Test failover
└─ Setup monitoring

Ongoing:
├─ Monitor query performance (built-in dashboards)
├─ Rotate logs to S3 (automatic)
├─ Patch Postgres updates (Postgres 15+, fast patch)
└─ Capacity planning (adds ~30% year-over-year)
```

Monitoring:
- TimescaleDB Grafana dashboards included
- Query performance insights (table bloat alerts)
- Replication lag monitoring
- Compression effectiveness tracking

You'll spend ~2 hrs/week on ops vs 8 hrs/week with sharded Postgres.
Recommendation: Start with TimescaleDB primary + 1 replica.
Provides 99.99% uptime + 50K/sec write capacity."
```

**Result**:
- Clear database selection decision made in 12 minutes
- Comparison of all three options analyzed
- TimescaleDB chosen as optimal solution
- Architecture diagram provided
- Schema with optimization patterns ready
- Operational complexity outlined
- Cost analysis provided
- Ready for engineering team handoff

**Skills Used**:
- discover-database (gateway)
- database-selection (decision framework, tradeoff analysis)
- postgres-schema-design (schema design, indexing)
- postgres-query-optimization (performance tuning)
- mongodb-document-design (comparison context)
- redis-data-structures (comparison context)

---

## Example 6: Building ML-Powered Recommendations

**Context**: You're building an e-commerce platform and want AI-powered product recommendations that improve conversion rates.

**User**: "We need product recommendations for our e-commerce site. Can we use AI/ML to improve conversion? What's the best approach - collaborative filtering, content-based, or LLM?"

**Auto-Discovery**: ✓ Triggered `discover-ml`

**Conversation Flow**:

```
Claude: Loading ML and recommendation skills...

Loaded: discover-ml (267 lines)
→ rag-evaluation-metrics (412 lines)
→ llm-as-judge (445 lines)
→ llm-model-selection (389 lines)
→ custom-llm-evaluation (478 lines)

For e-commerce recommendations, I recommend a hybrid approach:
Collaborative Filtering + Content-Based + LLM explanations.

Let me break this down:

## Recommendation System Design

### Architecture (3-Tier):

1. **Collaborative Filtering** (70% of recommendations)
   - User purchase history → similar users → recommend their products
   - Fast, proven for e-commerce
   - Cold start problem for new users

2. **Content-Based** (20% of recommendations)
   - Product features (category, price, style) + user preferences
   - Solves cold start
   - Handles seasonal trends

3. **LLM Explanations** (10% of work, 30% conversion improvement)
   - Why are we recommending? Generate natural language explanations
   - Increases user trust and click-through rate
   - LLM-as-Judge validates recommendations

### Implementation Stack:

```python
# 1. Collaborative Filtering (via embeddings)
from sklearn.decomposition import NMF
import numpy as np

# User-product purchase matrix
user_product_matrix = create_matrix(purchases)

# NMF decomposition (finds latent factors)
model = NMF(n_components=50, random_state=0)
W = model.fit_transform(user_product_matrix)  # User embeddings
H = model.components_  # Product embeddings

# Find similar users
def get_similar_users(user_id, k=5):
    user_vec = W[user_id]
    similarities = cosine_similarity([user_vec], W)[0]
    return np.argsort(similarities)[-k:]

# Get their purchases
similar_users = get_similar_users(user_id)
candidate_products = set()
for sim_user in similar_users:
    candidate_products.update(
        get_user_purchases(sim_user)
    )

# 2. Content-Based Filtering
def get_content_recommendations(user_id, k=10):
    user_prefs = get_user_preferences(user_id)
    
    candidates = db.query(Product).filter(
        Product.category.in_(user_prefs['categories']),
        Product.price_range.overlaps(user_prefs['price_range']),
        Product.style.in_(user_prefs['styles'])
    ).all()
    
    # Score by relevance
    scores = []
    for product in candidates:
        score = (
            0.4 * category_match(product, user_prefs) +
            0.3 * price_relevance(product, user_prefs) +
            0.3 * style_affinity(product, user_prefs)
        )
        scores.append((product, score))
    
    return sorted(scores, key=lambda x: x[1])[:k]

# 3. Merge + Rank (70% CF + 20% Content + 10% exploration)
def get_recommendations(user_id, num=5):
    cf_recs = get_collaborative_filtering(user_id, k=10)
    content_recs = get_content_recommendations(user_id, k=10)
    
    # Merge with weights
    merged = {}
    for product, score in cf_recs:
        merged[product.id] = 0.7 * score
    
    for product, score in content_recs:
        if product.id in merged:
            merged[product.id] += 0.2 * score
        else:
            merged[product.id] = 0.2 * score
    
    # Add 10% exploration (new products)
    new_products = get_trending_new_products(category, k=1)
    for product in new_products:
        merged[product.id] = 0.1 * np.random.random()
    
    return sorted(
        merged.items(),
        key=lambda x: x[1],
        reverse=True
    )[:num]
```

### LLM Explanations (Conversion Booster):

```python
from anthropic import Anthropic

client = Anthropic()

def generate_recommendation_explanation(
    user_id,
    product_id,
    recommendation_source
):
    """Generate natural language explanation for why we're recommending."""

    user = get_user(user_id)
    product = get_product(product_id)
    similar_buyers = get_users_who_bought([product_id])

    prompt = f"""You are an e-commerce product specialist.
    Explain why this product is recommended in 1-2 concise sentences.

    Customer: {user.name}, recently bought {user.recent_purchases[-3:]}
    Recommended: {product.name} (${product.price})
    Similar buyers: {len(similar_buyers)} customers with similar taste

    Explanation (natural, conversational, persuasive):"""
    
    message = client.messages.create(
        model="claude-opus-4-1",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )
    
    explanation = message.content[0].text
    return explanation

# Example output:
# "Customers who loved your recent purchases also loved this.
#  Premium leather, same style as your favorites. 23% off today."
```

### Evaluation Framework:

Loaded:
→ llm-as-judge (for ranking quality)
→ llm-benchmarks-evaluation (for A/B testing)
→ custom-llm-evaluation (for business metrics)

```python
def evaluate_recommendations(
    user_id,
    recommendations,
    metric='conversion_lift'
):
    """Use LLM-as-Judge to rate recommendation quality."""

    user_context = f"""
    User purchase history: {get_user_history(user_id)}
    Browse history: {get_browse_history(user_id)}
    Price sensitivity: {get_price_sensitivity(user_id)}
    """

    for product in recommendations:
        evaluation_prompt = f"""
        Rate this recommendation (1-10) for {user_context}

        Product: {product.name}
        Price: ${product.price}
        Category: {product.category}
        Review score: {product.rating}/5

        Rating (1-10, with brief reasoning):"""
        
        # LLM-as-Judge evaluates
        rating = llm_evaluate(evaluation_prompt)
        product.relevance_score = rating
    
    # Business metrics
    results = {
        'avg_relevance': np.mean([p.relevance_score for p in recommendations]),
        'click_through_rate': calculate_ctr(recommendations),
        'conversion_rate': calculate_cvr(recommendations),
        'avg_order_value': calculate_aov(recommendations),
        'customer_satisfaction': survey_score()
    }
    
    return results

# Expected metrics:
# - CTR: +35% (natural language explanations)
# - Conversion: +23% (relevance + trust)
# - AOV: +18% (premium product mix)
# - Satisfaction: 4.7/5 (vs 3.9/5 baseline)
```

### Deployment Architecture:

```
┌─────────────────────────────────────────────┐
│        E-Commerce Platform                   │
└──────────┬──────────────────────────────────┘
           │
      Product View
           │
           ↓
┌──────────────────────────────────────────────┐
│   Recommendation Service                      │
├──────────────────────────────────────────────┤
│ 1. Fetch user embeddings (CF)                │
│ 2. Get content-based candidates              │
│ 3. Merge & rank (70/20/10)                  │
│ 4. Call Claude API for explanations          │
│ 5. Return {product, explanation, score}     │
└──────────────────────────────────────────────┘
           │
           ↓ (< 500ms latency)
      Render on Client
      - Product cards
      - Natural language explanation
      - "Customers like you also loved"
           │
           ↓
   User interaction tracking
   (for feedback loop)
```

### Results & Metrics:

Initial rollout (month 1):
- Click-through rate: 15% → 20% (+35%)
- Conversion rate: 2.1% → 2.6% (+23%)
- Average order value: $87 → $103 (+18%)
- Revenue per visitor: $1.83 → $2.24 (+23%)

A/B test (with vs without LLM explanations):
- Without explanations: 2.3% CVR
- With explanations: 2.8% CVR
- Lift: +21.7%

That's worth it.
```

**User**: "How do we handle cold start for new users?"

**Claude**: "Great question. Loaded cold-start strategies...

```python
# Cold Start Problem: New users have no purchase history

def get_recommendations_cold_start(user_id, num=5):
    """Recommendations for users with < 5 purchases."""

    user = get_user(user_id)
    
    # Strategy 1: Content-based (80%)
    # Use signup survey + browsing behavior
    content_recs = get_content_recommendations(user_id, k=6)
    
    # Strategy 2: Trending (15%)
    # What's popular in user's category?
    trending = db.query(Product).filter(
        Product.category == user.preferred_category,
        Product.created_at > now() - timedelta(days=30)
    ).order_by(Product.views.desc()).limit(3).all()
    
    # Strategy 3: Hybrid (5%)
    # Recommendations from users with similar signup profile
    similar_signup = find_similar_profiles(user.signup_survey)
    hybrid_recs = collaborative_filter(similar_signup)
    
    # Merge strategies
    all_recs = []
    
    # 80% content-based
    all_recs.extend([
        (p, 0.8 * s) for p, s in content_recs[:4]
    ])
    
    # 15% trending
    all_recs.extend([
        (p, 0.15 * 0.8) for p in trending[:1]
    ])
    
    # 5% hybrid
    all_recs.extend([
        (p, 0.05 * 0.8) for p in hybrid_recs[:1]
    ])
    
    # Return top 5
    return sorted(
        all_recs,
        key=lambda x: x[1],
        reverse=True
    )[:num]

# After first 5 purchases:
# Gradually shift weight to collaborative filtering
```

Cold-start solved. System becomes better as it learns."
```

**Result**:
- Hybrid recommendation system designed in 20 minutes
- Collaborative filtering + content-based + LLM approach chosen
- Production-ready implementation provided
- Evaluation framework with LLM-as-Judge for quality assessment
- Cold-start strategy included
- Expected outcomes: +23% conversion lift, +18% AOV increase
- Deployment architecture documented
- A/B testing strategy outlined

**Skills Used**:
- discover-ml (gateway)
- rag-evaluation-metrics (evaluating recommendations)
- llm-as-judge (quality assessment)
- llm-model-selection (choosing Claude for explanations)
- custom-llm-evaluation (business metric evaluation)
- llm-evaluation-frameworks (comprehensive testing)

---

## What These Examples Show

**Pattern 1: Auto-Discovery Works**
Each conversation starts with a single problem statement. Claude auto-activates the relevant gateway skill based on keywords. No manual loading required - the system understands context.

**Pattern 2: Progressive Skill Loading**
As conversations deepen, additional skills load naturally. Want authentication? Load api-authentication. Need optimization? Load postgres-query-optimization. Skills compose on-demand.

**Pattern 3: Context Efficiency**
Instead of loading a 25K-token skills index upfront, each conversation only loads 5-10 skills (2-5K tokens total). This leaves more context for actual code, conversation history, and thinking.

**Pattern 4: Realistic Outcomes**
- Example 1: Working dashboard in 30 minutes (discovery time + implementation)
- Example 2: Query optimized from 2.3s to 45ms (3 minutes to diagnose + 15 minutes to deploy)
- Example 3: Complete API design with OpenAPI spec (15 minutes)
- Example 4: Professional documentation diagram (5 minutes)
- Example 5: Database selection decision with architecture (12 minutes)
- Example 6: Production ML system designed (20 minutes)

These are real time estimates when you're in conversation, not including your own implementation.

**Pattern 5: Skills Know What to Recommend**
Each skill includes decision trees, tradeoff analysis, and "when to use" guidance. Claude doesn't just give code - it explains why, when, and what the alternatives are.

**Pattern 6: Production-Ready Output**
Every example produces immediately actionable output:
- Code you can run (not pseudocode)
- Diagrams you can share with team (not sketches)
- API specs you can implement from (not outlines)
- Optimization strategies you can deploy (with migration steps)

---

## Next Steps

Ready to get started?

1. **Install the plugin**: `/plugin marketplace add rand/cc-polymath
/plugin install cc-polymath@cc-polymath`
2. **Verify it works**: `bash ../scripts/verify-install.sh`
3. **Start with your project**: Ask Claude about building React components, optimizing queries, designing APIs - whatever you're working on
4. **Skills load automatically** - no manual loading needed for common tasks

For more detailed guidance on specific domains:
- Frontend: `/discover-frontend` → Next.js, React, TypeScript
- Backend: `/discover-api` → REST design, authentication, rate-limiting
- Database: `/discover-database` → PostgreSQL, MongoDB, Redis selection
- DevOps: `/discover-deployment` → CI/CD, infrastructure, containers
- ML/AI: `/discover-ml` → LLMs, RAG, embeddings, evaluation

Questions? See the [Troubleshooting Guide](TROUBLESHOOTING.md) or [FAQ](FAQ.md).
