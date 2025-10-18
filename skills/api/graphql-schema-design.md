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

## Related Skills

- `rest-api-design.md` - Comparing REST vs GraphQL
- `dataloader-optimization.md` - Advanced DataLoader patterns
- `postgres-query-optimization.md` - Optimizing database queries
- `api-authentication.md` - JWT and OAuth patterns

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
