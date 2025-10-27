---
name: api-graphql-schema-design
description: Designing GraphQL APIs from scratch
---



# GraphQL Schema Design

**Scope**: Schema design, resolvers, N+1 prevention, pagination, authorization
**Lines**: ~260
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Designing GraphQL APIs from scratch
- Implementing GraphQL resolvers and DataLoader
- Solving N+1 query problems (performance)
- Adding pagination to GraphQL queries
- Implementing authorization in GraphQL
- Handling errors and validation
- Optimizing GraphQL query performance

## Schema Design Principles

### Types and Nullability

```graphql
type User {
  id: ID!                    # Non-null ID
  email: String!             # Non-null String
  age: Int                   # Nullable Int
  isActive: Boolean!         # Non-null Boolean
  createdAt: DateTime        # Custom scalar
}

type Post {
  id: ID!
  title: String!
  author: User!              # Relationship
  comments: [Comment!]!      # Non-null list of non-null items
}
```

**Nullability rules**:
- Use `!` for required fields
- Avoid `!` on top-level lists: `[Item!]!` allows empty list, `[Item]` allows null items
- Non-null fields can't be removed (breaking change)

### Queries and Mutations

```graphql
type Query {
  user(id: ID!): User
  posts(limit: Int, after: String): PostConnection!
}

type Mutation {
  createPost(input: CreatePostInput!): CreatePostPayload!
  updatePost(id: ID!, input: UpdatePostInput!): Post!
  deletePost(id: ID!): DeletePostPayload!
}

input CreatePostInput {
  title: String!
  content: String!
  tags: [String!]
}

type CreatePostPayload {
  post: Post
  errors: [ValidationError!]!
}

type ValidationError {
  field: String!
  message: String!
}
```

**Mutation patterns**:
- Use input types for complex arguments
- Return payload types with errors
- Name with verb prefix (create, update, delete)
- Keep atomic (single responsibility)

### Subscriptions (Real-time)

```graphql
type Subscription {
  postCreated: Post!
  postUpdated(postId: ID!): Post!
  commentAdded(postId: ID!): Comment!
}
```

**Implementation** (Node.js):
```javascript
const { PubSub } = require('graphql-subscriptions');
const pubsub = new PubSub();

const resolvers = {
  Subscription: {
    postCreated: {
      subscribe: () => pubsub.asyncIterator(['POST_CREATED'])
    }
  },
  Mutation: {
    createPost: async (_, { input }) => {
      const post = await db.createPost(input);
      pubsub.publish('POST_CREATED', { postCreated: post });
      return { post };
    }
  }
};
```

---

## N+1 Problem and DataLoader

### The N+1 Problem

**Example**: Fetching 10 posts with authors

```javascript
// This resolver is called 10 times (once per post)
Post: {
  author: async (post, args, context) => {
    // N+1: 1 query for posts + 10 queries for authors
    return await db.query('SELECT * FROM users WHERE id = ?', [post.authorId]);
  }
}
```

**Result**: 11 database queries (inefficient)

### DataLoader Solution

**DataLoader batches and caches requests within a single request**

```javascript
const DataLoader = require('dataloader');

// Batch function: receives array of IDs, returns array of users
const batchGetUsers = async (userIds) => {
  const users = await db.query(
    'SELECT * FROM users WHERE id IN (?)',
    [userIds]
  );

  // CRITICAL: Return users in same order as userIds
  const userMap = new Map(users.map(u => [u.id, u]));
  return userIds.map(id => userMap.get(id) || new Error('Not found'));
};

// Create DataLoader in context (per-request)
context: ({ req }) => ({
  loaders: {
    userLoader: new DataLoader(batchGetUsers)
  }
})

// Use in resolver
Post: {
  author: async (post, args, context) => {
    // DataLoader batches all calls and executes once
    return await context.loaders.userLoader.load(post.authorId);
  }
}
```

**Result**: 2 database queries (1 for posts + 1 batched for authors)

### DataLoader Best Practices

```javascript
// ✅ CORRECT: Create loaders in context (per-request)
context: ({ req }) => ({
  loaders: {
    userLoader: new DataLoader(batchGetUsers),
    postLoader: new DataLoader(batchGetPosts)
  }
})

// ❌ WRONG: Global DataLoader (caches across requests)
const globalUserLoader = new DataLoader(batchGetUsers);  // Memory leak!

// ✅ CORRECT: Return array in same order as input
const batchGetUsers = async (ids) => {
  const users = await fetchUsers(ids);
  const userMap = new Map(users.map(u => [u.id, u]));
  return ids.map(id => userMap.get(id) || new Error('Not found'));
};
```

---

## Error Handling

### User Errors (Validation)

```javascript
Mutation: {
  createPost: async (parent, { input }, context) => {
    const errors = [];

    if (input.title.length < 5) {
      errors.push({ field: 'title', message: 'Title too short' });
    }

    if (input.content.length < 20) {
      errors.push({ field: 'content', message: 'Content too short' });
    }

    if (errors.length > 0) {
      return { post: null, errors };
    }

    const post = await db.createPost(input);
    return { post, errors: [] };
  }
}
```

### System Errors (Unexpected)

```javascript
const { AuthenticationError, UserInputError } = require('apollo-server');

Query: {
  user: async (parent, { id }, context) => {
    if (!context.user) {
      throw new AuthenticationError('Must be logged in');
    }

    if (!id.match(/^\d+$/)) {
      throw new UserInputError('Invalid ID format');
    }

    return await db.getUserById(id);
  }
}
```

---

## Pagination

### Cursor-Based Pagination (Recommended)

```graphql
type Query {
  posts(first: Int = 10, after: String): PostConnection!
}

type PostConnection {
  edges: [PostEdge!]!
  pageInfo: PageInfo!
}

type PostEdge {
  node: Post!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  endCursor: String
}
```

**Implementation**:
```javascript
Query: {
  posts: async (parent, { first = 10, after }) => {
    const cursor = after ? decodeCursor(after) : 0;

    // Fetch one extra to check hasNextPage
    const posts = await db.query(
      'SELECT * FROM posts WHERE id > ? ORDER BY id ASC LIMIT ?',
      [cursor, first + 1]
    );

    const hasNextPage = posts.length > first;
    const nodes = hasNextPage ? posts.slice(0, -1) : posts;

    const edges = nodes.map(post => ({
      node: post,
      cursor: encodeCursor(post.id)
    }));

    return {
      edges,
      pageInfo: {
        hasNextPage,
        endCursor: edges[edges.length - 1]?.cursor
      }
    };
  }
}

const encodeCursor = (id) => Buffer.from(id.toString()).toString('base64');
const decodeCursor = (cursor) => parseInt(Buffer.from(cursor, 'base64').toString());
```

**Pros**: Consistent results, efficient for large datasets
**Cons**: Can't jump to arbitrary page

### Offset Pagination (Simpler)

```graphql
type Query {
  posts(limit: Int = 10, offset: Int = 0): PostPage!
}

type PostPage {
  items: [Post!]!
  total: Int!
}
```

**Pros**: Simple, can jump to page N
**Cons**: Inconsistent if data changes, slow for large offsets

---

## Authorization

### Field-Level Authorization

```javascript
const resolvers = {
  Query: {
    users: async (parent, args, context) => {
      // Query-level auth
      if (!context.user?.isAdmin) {
        throw new AuthenticationError('Admin only');
      }
      return await db.getUsers();
    }
  },

  User: {
    email: (user, args, context) => {
      // Field-level auth (hide email from non-owners)
      if (context.user?.id !== user.id && !context.user?.isAdmin) {
        return null;
      }
      return user.email;
    }
  }
};
```

### Directive-Based Authorization

```graphql
directive @auth(requires: Role = USER) on FIELD_DEFINITION

enum Role {
  USER
  ADMIN
}

type Query {
  posts: [Post!]!
  users: [User!]! @auth(requires: ADMIN)
}

type User {
  id: ID!
  name: String!
  email: String! @auth(requires: USER)
}
```

---

## Schema Patterns

### Interface (Polymorphism)

```graphql
interface Searchable {
  id: ID!
  title: String!
}

type Post implements Searchable {
  id: ID!
  title: String!
  content: String!
}

type Video implements Searchable {
  id: ID!
  title: String!
  url: String!
}

type Query {
  search(query: String!): [Searchable!]!
}
```

**Resolver**:
```javascript
Searchable: {
  __resolveType(obj) {
    if (obj.content) return 'Post';
    if (obj.url) return 'Video';
    return null;
  }
}
```

### Union (Flexible Results)

```graphql
union SearchResult = Post | Video | User

type Query {
  search(query: String!): [SearchResult!]!
}
```

**Client query**:
```graphql
query Search($query: String!) {
  search(query: $query) {
    __typename
    ... on Post { title content }
    ... on Video { title url }
    ... on User { name email }
  }
}
```

---

## Common Anti-Patterns

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| N+1 queries | Not using DataLoader | Batch with DataLoader |
| Deep queries | No depth limits | `validationRules: [depthLimit(5)]` |
| Large lists | No pagination | Use cursor pagination |
| Scalar mutations | `deletePost: Boolean` | Return payload object |
| Global DataLoader | Caches across requests | Create per-request in context |
| No error handling | Throw on validation | Return errors in payload |
| Logic in resolvers | Business logic mixed | Resolvers call service layer |

---

## Level 3: Resources

### Reference Documentation

**Location**: `skills/api/graphql-schema-design/resources/REFERENCE.md`

Comprehensive 900+ line reference covering:
- GraphQL schema design principles and best practices
- Complete type system (scalars, objects, interfaces, unions, enums, inputs)
- Schema patterns (Node, Connection, Payload, Error types)
- Query and mutation design with examples
- Subscription patterns for real-time updates
- Error handling strategies and types
- Pagination (offset-based, cursor-based, Relay connections)
- Performance optimization (DataLoader, complexity analysis, caching)
- Security (authentication, authorization, rate limiting, validation)
- Schema versioning and deprecation strategies
- Schema federation and stitching
- Testing strategies for schemas
- Complete anti-patterns catalog

### Executable Scripts

**Location**: `skills/api/graphql-schema-design/resources/scripts/`

1. **analyze_schema.py** - GraphQL schema analyzer
   - Analyzes GraphQL schemas for anti-patterns and best practices
   - Detects naming convention violations
   - Checks documentation coverage
   - Validates pagination patterns
   - Identifies nullability issues
   - Checks mutation design patterns
   - Calculates quality score (0-100)
   - Output: Human-readable report or JSON

   ```bash
   ./analyze_schema.py schema.graphql
   ./analyze_schema.py schema.graphql --json
   ./analyze_schema.py schema.graphql --min-score 80
   ```

2. **generate_types.py** - TypeScript type generator
   - Generates TypeScript type definitions from GraphQL schemas
   - Supports all GraphQL type system features
   - Handles custom scalars, enums, interfaces, unions
   - Configurable nullability handling
   - JSON output for programmatic use
   - Output: TypeScript .d.ts file or JSON

   ```bash
   ./generate_types.py schema.graphql -o types.ts
   ./generate_types.py schema.graphql --nullable-by-default
   ./generate_types.py schema.graphql --json
   ```

3. **benchmark_queries.js** - GraphQL query benchmarking tool
   - Benchmarks GraphQL query performance
   - Concurrent request support
   - Detailed timing metrics (min, max, avg, p50, p90, p95, p99)
   - Throughput calculation (requests/sec)
   - Payload size analysis
   - Warmup phase support
   - Custom headers and authentication
   - JSON output for CI/CD integration

   ```bash
   ./benchmark_queries.js -e http://localhost:4000/graphql -q "{ users { id } }"
   ./benchmark_queries.js -e http://localhost:4000/graphql --query-file query.graphql -c 10 -i 100
   ./benchmark_queries.js -e http://localhost:4000/graphql -q "{ posts { title } }" --json
   ```

### Code Examples

**Location**: `skills/api/graphql-schema-design/resources/examples/`

1. **python/graphql_server.py** - Strawberry GraphQL server
   - Complete GraphQL server using Strawberry (Python)
   - Type-safe schema with Python type hints
   - DataLoader for N+1 prevention
   - Connection-based pagination
   - Error handling with union types
   - Authentication and authorization
   - Input types and payload types
   - Runnable example with FastAPI

2. **typescript/graphql_server.ts** - Apollo Server implementation
   - Complete GraphQL server using Apollo Server
   - Type-safe resolvers with TypeScript
   - DataLoader batching patterns
   - Relay-style pagination
   - Error handling with interfaces
   - Context-based authentication
   - Subscription support
   - Runnable standalone server

3. **typescript/graphql_client.ts** - Apollo Client implementation
   - Complete GraphQL client using Apollo Client
   - Type-safe queries and mutations
   - Fragment composition
   - Cache management strategies
   - Pagination handling
   - Optimistic updates
   - Real-time query watching
   - Error handling patterns

4. **schemas/good-schema.graphql** - Best practices schema
   - Production-ready schema demonstrating all best practices
   - Complete documentation for all types and fields
   - Proper naming conventions (PascalCase, camelCase, SCREAMING_SNAKE_CASE)
   - Node interface for global object identification
   - Relay connection pattern for pagination
   - Error handling with interface types
   - Input types for all mutations
   - Payload types with success/errors fields
   - Custom scalars (DateTime, Email, URL, UUID)
   - Comprehensive type system usage

5. **schemas/anti-patterns.graphql** - Anti-patterns catalog
   - Comprehensive catalog of 30+ GraphQL anti-patterns
   - Each pattern documented with explanation
   - Shows incorrect approaches with comments
   - Covers naming, structure, performance, and design issues
   - Use as negative reference ("what NOT to do")

### Usage

All scripts are executable and include `--help`:

```bash
cd skills/api/graphql-schema-design/resources/scripts
./analyze_schema.py --help
./generate_types.py --help
./benchmark_queries.js --help
```

Examples are runnable with dependencies installed:

```bash
# Python server
cd examples/python
pip install strawberry-graphql fastapi uvicorn
python graphql_server.py

# TypeScript server
cd examples/typescript
npm install @apollo/server dataloader
ts-node graphql_server.ts

# TypeScript client
cd examples/typescript
npm install @apollo/client
ts-node graphql_client.ts
```

---

## Related Skills

- `rest-api-design.md` - Comparing REST vs GraphQL
- `dataloader-optimization.md` - Advanced DataLoader patterns
- `postgres-query-optimization.md` - Optimizing database queries
- `api-authentication.md` - JWT and OAuth patterns

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
