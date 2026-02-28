# Detailed Walkthroughs

End-to-end guides showing how cc-polymath skills compose for complex, production-ready projects.

---

## Walkthrough 1: Building a Production REST API

**Scenario**: Build a production-ready task management API with authentication, rate limiting, and observability

**Time**: 2-3 hours
**Level**: Intermediate to Advanced

**Skills Used**:
- discover-api → rest-api-design, api-authentication, api-authorization, api-rate-limiting, api-versioning
- discover-database → database-selection, postgres-schema-design
- discover-testing → api-testing, integration-testing
- discover-debugging → logging-best-practices, metrics-collection

**What You'll Build**: A complete REST API with JWT auth, role-based access control, rate limiting, comprehensive tests, and production observability.

### Prerequisites
- Node.js/TypeScript or Python knowledge
- Basic understanding of HTTP and REST
- PostgreSQL installed locally

### Step 1: Design Resources (30 min)

Load API design skills:
```bash
/discover-api
```

**Resource Modeling**:
- **Users**: `/users` - User accounts and profiles
- **Projects**: `/projects` - Project containers
- **Tasks**: `/projects/{projectId}/tasks` - Tasks within projects
- **Comments**: `/tasks/{taskId}/comments` - Task comments

**Key HTTP Patterns**:
- GET `/projects` - List projects (pagination required)
- POST `/projects` - Create project (requires auth)
- GET `/projects/{id}` - Get single project
- PATCH `/projects/{id}` - Partial update
- DELETE `/projects/{id}` - Soft delete (mark as archived)

**Status Codes**:
- 200 OK - Successful GET/PATCH
- 201 Created - Successful POST with Location header
- 204 No Content - Successful DELETE
- 400 Bad Request - Validation errors
- 401 Unauthorized - Missing/invalid token
- 403 Forbidden - Insufficient permissions
- 404 Not Found - Resource doesn't exist
- 429 Too Many Requests - Rate limit exceeded

### Step 2: Choose Database (20 min)

**Decision**: PostgreSQL with JSONB for flexible metadata

**Rationale**:
- Strong ACID guarantees (critical for task management)
- Complex queries with JOINs (project → tasks → comments)
- JSONB for flexible task metadata without schema changes
- Excellent performance at scale

**Schema Design**:
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id),
    metadata JSONB DEFAULT '{}',
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'todo',
    assignee_id UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}',
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX idx_tasks_status ON tasks(status);
```

### Step 3: Implement Authentication (40 min)

**JWT Implementation**:
```typescript
// auth.ts
import jwt from 'jsonwebtoken';

interface TokenPayload {
  userId: string;
  email: string;
  role: string;
}

export function generateTokens(user: User) {
  const accessToken = jwt.sign(
    { userId: user.id, email: user.email, role: user.role },
    process.env.JWT_SECRET!,
    { expiresIn: '15m' }
  );

  const refreshToken = jwt.sign(
    { userId: user.id },
    process.env.REFRESH_SECRET!,
    { expiresIn: '7d' }
  );

  return { accessToken, refreshToken };
}

export function verifyToken(token: string): TokenPayload {
  return jwt.verify(token, process.env.JWT_SECRET!) as TokenPayload;
}
```

**Middleware**:
```typescript
export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid token' });
  }

  try {
    const token = authHeader.substring(7);
    req.user = verifyToken(token);
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid or expired token' });
  }
}
```

### Step 4: Add Rate Limiting (20 min)

**Token Bucket Algorithm**:
```typescript
import { RateLimiterMemory } from 'rate-limiter-flexible';

const rateLimiter = new RateLimiterMemory({
  points: 100, // Number of requests
  duration: 60, // Per 60 seconds
});

export async function rateLimit(req: Request, res: Response, next: NextFunction) {
  try {
    const key = req.user?.userId || req.ip;
    await rateLimiter.consume(key);
    next();
  } catch (error) {
    res.status(429).json({
      error: 'Too many requests',
      retryAfter: Math.ceil(error.msBeforeNext / 1000)
    });
  }
}
```

### Step 5: Testing Strategy (30 min)

**Three-layer approach**:
```typescript
// Unit tests - Business logic
describe('ProjectService', () => {
  it('should create project with valid data', async () => {
    const project = await projectService.create({
      name: 'Test Project',
      ownerId: userId
    });
    expect(project.id).toBeDefined();
  });
});

// Integration tests - API endpoints
describe('POST /projects', () => {
  it('should create project when authenticated', async () => {
    const response = await request(app)
      .post('/projects')
      .set('Authorization', `Bearer ${token}`)
      .send({ name: 'Test' });
    expect(response.status).toBe(201);
  });
});

// E2E tests - Full workflows
describe('Task Management Flow', () => {
  it('should complete full lifecycle', async () => {
    // Create project → Add task → Assign → Complete
  });
});
```

### Step 6: Observability (20 min)

**Structured Logging**:
```typescript
import winston from 'winston';

const logger = winston.createLogger({
  format: winston.format.json(),
  defaultMeta: { service: 'task-api' },
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

app.use((req, res, next) => {
  logger.info('HTTP Request', {
    method: req.method,
    path: req.path,
    userId: req.user?.userId,
    ip: req.ip
  });
  next();
});
```

**Metrics**:
```typescript
import prometheus from 'prom-client';

const httpRequestDuration = new prometheus.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status']
});

// Middleware to track
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    httpRequestDuration.labels(req.method, req.route?.path, res.statusCode).observe(duration);
  });
  next();
});
```

### Summary

**What You Built**:
- Production REST API with 4 resources
- JWT authentication with refresh tokens
- Role-based authorization
- Token bucket rate limiting
- Three-layer test coverage
- Structured logging and metrics

**Skills Composition**: Demonstrates how API design, database schema, security, and observability skills combine for production-ready systems.

---

## Walkthrough 2: Next.js E-commerce Site

**Scenario**: Build a performant e-commerce site with server-side rendering, optimistic updates, and multi-layer caching

**Time**: 3-4 hours
**Level**: Intermediate

**Skills Used**:
- discover-frontend → next-js-app-router, react-hooks, state-management, performance-optimization
- discover-database → multi-layer-caching, cdn-strategies
- discover-api → rest-api-design

**What You'll Build**: Full e-commerce site with product catalog, cart, checkout, and aggressive performance optimizations.

### Key Implementation Highlights

**Next.js App Router with React Server Components**:
```typescript
// app/products/[id]/page.tsx
export default async function ProductPage({ params }: { params: { id: string } }) {
  const product = await getProduct(params.id); // Server Component - no client JS

  return (
    <div>
      <ProductDetails product={product} />
      <AddToCartButton productId={params.id} /> {/* Client Component */}
    </div>
  );
}
```

**Optimistic Cart Updates**:
```typescript
'use client';
import { useOptimistic } from 'react';

export function Cart() {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [optimisticCart, addOptimistic] = useOptimistic(
    cart,
    (state, newItem: CartItem) => [...state, newItem]
  );

  async function addToCart(item: CartItem) {
    addOptimistic(item); // Immediate UI update
    await fetch('/api/cart', { method: 'POST', body: JSON.stringify(item) });
    setCart(await fetchCart()); // Reconcile with server
  }
}
```

**Multi-Layer Caching**:
- CDN: Static assets (images, CSS) - 1 year cache
- HTTP: API responses - 5 min stale-while-revalidate
- React: Server Component cache - 60s revalidation
- Client: SWR for data fetching - background refetch

**Performance Results**:
- First Contentful Paint: <1.5s
- Largest Contentful Paint: <2.5s
- Time to Interactive: <3.5s
- Lighthouse Score: 95+

---

## Walkthrough 3: Data Pipeline with ETL

**Scenario**: Build a real-time data pipeline processing millions of events per day

**Time**: 2-3 hours
**Level**: Advanced

**Skills Used**:
- discover-data → etl-patterns, stream-processing
- discover-database → postgres-optimization, redis-patterns
- discover-debugging → distributed-tracing

**What You'll Build**: Event streaming pipeline with transformation, enrichment, and real-time analytics.

### Architecture Overview

```
Event Sources → Kafka → Stream Processor → PostgreSQL
                  ↓                ↓
              Redis Cache    Dead Letter Queue
```

### Key Implementation

**Stream Processing with Apache Kafka**:
```python
from kafka import KafkaConsumer, KafkaProducer
import json

consumer = KafkaConsumer(
    'raw-events',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest'
)

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

for message in consumer:
    event = message.value

    # Validate
    if not validate_event(event):
        producer.send('dead-letter', event)
        continue

    # Enrich with cached data
    enriched = enrich_event(event)

    # Transform
    transformed = transform_event(enriched)

    # Store
    store_event(transformed)
    producer.send('processed-events', transformed)
```

**Data Quality Checks**:
- Schema validation
- Deduplication (by event ID)
- Timestamp validation (no future events)
- Required field presence
- Data type enforcement

---

## Walkthrough 4: Mobile App with SwiftUI

**Scenario**: Build an iOS habit tracking app with SwiftUI, modern concurrency, and offline-first architecture

**Time**: 2-3 hours
**Level**: Intermediate

**Skills Used**:
- discover-mobile → swiftui-fundamentals, swift-concurrency, swiftdata
- discover-api → rest-api-design

**What You'll Build**: Native iOS app with SwiftData persistence, async networking, and elegant SwiftUI interfaces.

### Key Implementation

**SwiftData Models**:
```swift
import SwiftData

@Model
final class Habit {
    var id: UUID
    var title: String
    var frequency: String
    var createdAt: Date
    @Relationship(deleteRule: .cascade) var completions: [Completion]

    init(title: String, frequency: String) {
        self.id = UUID()
        self.title = title
        self.frequency = frequency
        self.createdAt = Date()
    }
}
```

**Async/Await Networking**:
```swift
actor HabitService {
    func fetchHabits() async throws -> [Habit] {
        let (data, _) = try await URLSession.shared.data(from: habitURL)
        return try JSONDecoder().decode([Habit].self, from: data)
    }

    func syncHabits(_ habits: [Habit]) async throws {
        let data = try JSONEncoder().encode(habits)
        var request = URLRequest(url: syncURL)
        request.httpMethod = "POST"
        request.httpBody = data
        try await URLSession.shared.data(for: request)
    }
}
```

**SwiftUI View with MVVM**:
```swift
struct HabitListView: View {
    @Query(sort: \Habit.createdAt) private var habits: [Habit]
    @Environment(\.modelContext) private var modelContext
    @State private var viewModel = HabitViewModel()

    var body: some View {
        List(habits) { habit in
            HabitRow(habit: habit)
        }
        .task {
            await viewModel.syncHabits()
        }
    }
}
```

---

## Walkthrough 5: ML-Powered Product Recommendations

**Scenario**: Add AI-powered product recommendations to an existing e-commerce platform with hybrid collaborative filtering, content-based matching, and LLM-generated explanations

**Time**: 3-4 hours
**Level**: Advanced

**Skills Used**:
- discover-ml → embeddings, rag-patterns, llm-evaluation-benchmarks, llm-as-judge
- discover-database → vector-databases, postgres-optimization
- discover-api → ml-api-design
- discover-debugging → ml-monitoring
- discover-database → embedding-caching

**What You'll Build**: Production ML recommendation system with evaluation framework, A/B testing, and cost-optimized caching.

### Step 1: Requirements & Architecture (30 min)

**Business Metrics**:
- Click-through rate (CTR): +15% target
- Conversion rate: +20% target
- Average order value (AOV): +10% target

**ML Metrics**:
- Precision@10: >0.3 (30% of top 10 are relevant)
- Recall@50: >0.6 (60% of all relevant items in top 50)
- Mean Reciprocal Rank (MRR): >0.4

**LLM Metrics** (via LLM-as-judge):
- Explanation relevance: >8/10
- Personalization score: >7/10
- Helpfulness rating: >8/10

**Hybrid Architecture**:
```
User Request
   ↓
Collaborative Filtering → Top 100 candidates
   ↓
Content-Based (Embeddings) → Rerank to Top 20
   ↓
LLM Explanation Generation → Top 10 with reasons
   ↓
Response
```

### Step 2: Data Preparation (30 min)

**Product Embeddings**:
```python
from openai import OpenAI

client = OpenAI()

def generate_product_embedding(product):
    text = f"{product['name']} {product['description']} {product['category']}"
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# Batch process all products
products = load_products()
for product in products:
    embedding = generate_product_embedding(product)
    store_embedding(product['id'], embedding)
```

**User Interaction Matrix**:
```python
import pandas as pd
from scipy.sparse import csr_matrix

# Create user-item interaction matrix
interactions = pd.read_sql("SELECT user_id, product_id, weight FROM interactions", db)
user_item_matrix = csr_matrix(
    (interactions['weight'], (interactions['user_id'], interactions['product_id']))
)
```

### Step 3: Vector Database Setup (30 min)

**Using pgvector (PostgreSQL extension)**:
```sql
-- Enable pgvector
CREATE EXTENSION vector;

-- Store embeddings
CREATE TABLE product_embeddings (
    product_id UUID PRIMARY KEY,
    embedding vector(1536), -- text-embedding-3-small dimension
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create HNSW index for fast similarity search
CREATE INDEX ON product_embeddings USING hnsw (embedding vector_cosine_ops);

-- Similarity search query
SELECT product_id, 1 - (embedding <=> $1) AS similarity
FROM product_embeddings
ORDER BY embedding <=> $1
LIMIT 20;
```

### Step 4: Collaborative Filtering (45 min)

**User-based Collaborative Filtering**:
```python
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def get_collaborative_recommendations(user_id, n=100):
    # Get user's interaction vector
    user_vector = user_item_matrix[user_id].toarray()

    # Compute similarity with all users
    similarities = cosine_similarity(user_vector, user_item_matrix)[0]

    # Find top 50 similar users
    similar_users = np.argsort(similarities)[-51:-1]  # Exclude self

    # Aggregate their interactions
    recommendations = {}
    for similar_user in similar_users:
        similarity_score = similarities[similar_user]
        for product_id in get_user_products(similar_user):
            if product_id not in get_user_products(user_id):  # Not already purchased
                recommendations[product_id] = recommendations.get(product_id, 0) + similarity_score

    # Return top 100
    return sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:n]
```

### Step 5: Content-Based Reranking (40 min)

**Embedding Similarity**:
```python
async def rerank_with_embeddings(user_id, candidates, n=20):
    # Get user's preference embedding (average of liked products)
    user_embeddings = [get_embedding(pid) for pid in get_user_products(user_id)]
    user_preference = np.mean(user_embeddings, axis=0)

    # Score candidates
    scores = []
    for product_id, collab_score in candidates:
        embedding = get_embedding(product_id)
        content_score = cosine_similarity([user_preference], [embedding])[0][0]

        # Hybrid score: 60% collaborative, 40% content-based
        final_score = 0.6 * collab_score + 0.4 * content_score
        scores.append((product_id, final_score))

    return sorted(scores, key=lambda x: x[1], reverse=True)[:n]
```

### Step 6: LLM Explanation Generation (30 min)

**Personalized Explanations**:
```python
from anthropic import Anthropic

client = Anthropic()

def generate_explanation(user_id, product_id):
    user_history = get_user_purchase_history(user_id)
    product = get_product(product_id)

    prompt = f"""Generate a brief, personalized recommendation explanation.

User's recent purchases:
{format_purchase_history(user_history)}

Recommended product:
Name: {product['name']}
Category: {product['category']}
Features: {product['features']}

Generate ONE sentence explaining why this product is recommended for this user.
Be specific about their purchase patterns."""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text
```

### Step 7: Evaluation Framework (40 min)

**Business Metrics Tracking**:
```python
def track_recommendation_metrics(user_id, recommendations, interactions):
    impressions = len(recommendations)
    clicks = sum(1 for rec in recommendations if rec['id'] in interactions['clicked'])
    purchases = sum(1 for rec in recommendations if rec['id'] in interactions['purchased'])

    ctr = clicks / impressions if impressions > 0 else 0
    conversion_rate = purchases / impressions if impressions > 0 else 0

    log_metrics({
        'user_id': user_id,
        'impressions': impressions,
        'ctr': ctr,
        'conversion_rate': conversion_rate,
        'timestamp': datetime.now()
    })
```

**ML Metrics (Precision@K, MRR)**:
```python
def evaluate_recommendations(user_id, recommendations, ground_truth):
    relevant = set(ground_truth)

    # Precision@10
    top_10 = [r['id'] for r in recommendations[:10]]
    precision_10 = len(set(top_10) & relevant) / 10

    # Recall@50
    top_50 = [r['id'] for r in recommendations[:50]]
    recall_50 = len(set(top_50) & relevant) / len(relevant)

    # MRR
    for i, rec in enumerate(recommendations, 1):
        if rec['id'] in relevant:
            mrr = 1.0 / i
            break
    else:
        mrr = 0.0

    return {
        'precision_10': precision_10,
        'recall_50': recall_50,
        'mrr': mrr
    }
```

**LLM-as-Judge Evaluation**:
```python
def evaluate_explanation(explanation, product, user_history):
    prompt = f"""Evaluate this product recommendation explanation on three criteria:

Recommendation: "{explanation}"

Product: {product['name']}
User History: {user_history}

Rate each criterion from 1-10:

1. RELEVANCE: Does the explanation accurately connect to the product's features?
2. PERSONALIZATION: Does it reference the user's specific purchase patterns?
3. HELPFULNESS: Would this help the user decide to click/purchase?

Return ONLY a JSON object: {{"relevance": X, "personalization": Y, "helpfulness": Z}}"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(response.content[0].text)
```

### Step 8: Production Deployment (35 min)

**API Endpoint**:
```python
from fastapi import FastAPI, HTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

app = FastAPI()

@app.get("/recommendations/{user_id}")
@cache(expire=300)  # Cache for 5 minutes
async def get_recommendations(user_id: str, limit: int = 10):
    try:
        # Collaborative filtering
        candidates = get_collaborative_recommendations(user_id, n=100)

        # Content-based reranking
        reranked = await rerank_with_embeddings(user_id, candidates, n=20)

        # Generate explanations for top N
        recommendations = []
        for product_id, score in reranked[:limit]:
            product = get_product(product_id)
            explanation = generate_explanation(user_id, product_id)

            recommendations.append({
                'product_id': product_id,
                'name': product['name'],
                'score': score,
                'explanation': explanation
            })

        return {'recommendations': recommendations}

    except Exception as e:
        logger.error(f"Recommendation error for user {user_id}: {e}")
        # Fallback to popularity-based
        return {'recommendations': get_popular_products(limit)}
```

**Caching Strategy**:
- Embeddings: Redis cache, 24h TTL (rarely change)
- Collaborative scores: Redis cache, 1h TTL (updated hourly)
- LLM explanations: Redis cache, 6h TTL (balance freshness vs cost)
- API responses: Redis cache, 5min TTL (frequently update)

**Monitoring**:
```python
from prometheus_client import Histogram, Counter

rec_latency = Histogram(
    'recommendation_latency_seconds',
    'Time to generate recommendations',
    ['stage']
)

rec_requests = Counter(
    'recommendation_requests_total',
    'Total recommendation requests',
    ['status']
)

@app.middleware("http")
async def add_metrics(request, call_next):
    with rec_latency.labels(stage='total').time():
        response = await call_next(request)
    rec_requests.labels(status=response.status_code).inc()
    return response
```

**Cost Optimization**:
- Embedding generation: Batch process, cache forever
- LLM explanations: Generate top 10 only, aggressive caching
- Vector search: Use HNSW index (10x faster than brute force)
- Fallback: Popularity-based when ML fails (no cost)

**Expected Results**:
- Latency: p50 < 200ms, p95 < 500ms, p99 < 1s
- Cost: ~$0.02 per user per month (with caching)
- CTR improvement: +23%
- Conversion improvement: +18%
- AOV improvement: +12%

### Summary

**What You Built**:
- Hybrid recommendation engine (collaborative + content-based + LLM)
- Vector similarity search with pgvector
- LLM-generated personalized explanations
- Comprehensive evaluation framework (business + ML + LLM-as-judge)
- Production API with caching and fallbacks
- Real-time monitoring and cost optimization

**Skills Composition**: Demonstrates how ML skills (embeddings, RAG, evaluation), database skills (vector search), API design, and observability compose for production ML systems.

**Next Steps**:
- A/B test against existing recommendations
- Fine-tune collaborative/content-based weights
- Add diversity/novelty metrics
- Implement multi-armed bandit for exploration
- Add real-time user feedback loop

---

## Additional Resources

- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Quick start guide
- **[FIRST_CONVERSATIONS.md](FIRST_CONVERSATIONS.md)** - Example workflows
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues
- **[FAQ.md](FAQ.md)** - Quick answers

These walkthroughs show cc-polymath's skills composing naturally for complex, production-ready systems across backend, frontend, data, mobile, and ML domains.
