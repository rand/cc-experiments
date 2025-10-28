# GraphQL Schema Design Reference

## Table of Contents

1. [Core Principles](#core-principles)
2. [Type System](#type-system)
3. [Schema Patterns](#schema-patterns)
4. [Query Design](#query-design)
5. [Mutation Design](#mutation-design)
6. [Subscription Design](#subscription-design)
7. [Error Handling](#error-handling)
8. [Pagination](#pagination)
9. [Performance Optimization](#performance-optimization)
10. [Security](#security)
11. [Versioning](#versioning)
12. [Schema Federation](#schema-federation)
13. [Testing](#testing)
14. [Anti-Patterns](#anti-patterns)

---

## Core Principles

### Design Philosophy

**1. Client-Driven Design**
- Design schema from client perspective
- Support client use cases explicitly
- Minimize over-fetching and under-fetching
- Group related fields logically

**2. Type Safety**
- Leverage GraphQL's strong type system
- Make invalid states unrepresentable
- Use non-null types judiciously
- Prefer unions over nullable fields

**3. Evolutionary Design**
- Plan for schema evolution from day one
- Use deprecation over breaking changes
- Document migration paths
- Maintain backward compatibility

**4. Performance by Default**
- Design for efficient data fetching
- Avoid N+1 queries in schema design
- Use pagination for lists
- Consider complexity limits

### Schema Design Checklist

```markdown
## Schema Review Checklist

### Type Design
- [ ] All types have clear, descriptive names
- [ ] Object types represent domain concepts
- [ ] Fields are appropriately nullable/non-null
- [ ] Related fields are grouped logically
- [ ] ID fields use ID scalar type
- [ ] Enums used for fixed value sets

### Query Design
- [ ] Top-level queries represent use cases
- [ ] Query complexity is bounded
- [ ] Pagination implemented for lists
- [ ] Filtering/sorting arguments provided
- [ ] Single-entity and list queries available

### Mutation Design
- [ ] Mutations use input types
- [ ] Mutations return affected entities
- [ ] Error cases handled explicitly
- [ ] Side effects documented
- [ ] Idempotency considered

### Documentation
- [ ] All types documented
- [ ] All fields documented
- [ ] Arguments documented
- [ ] Examples provided
- [ ] Deprecations marked with @deprecated

### Performance
- [ ] DataLoader patterns identified
- [ ] Connection types for pagination
- [ ] Query complexity analysis done
- [ ] Batching opportunities identified
- [ ] Caching strategy defined
```

---

## Type System

### Scalar Types

**Built-in Scalars**

```graphql
scalar Int      # 32-bit integer
scalar Float    # Double-precision floating-point
scalar String   # UTF-8 character sequence
scalar Boolean  # true or false
scalar ID       # Unique identifier (serialized as string)
```

**Custom Scalars**

```graphql
# Date and Time
scalar DateTime    # ISO 8601 timestamp
scalar Date        # YYYY-MM-DD
scalar Time        # HH:MM:SS
scalar Duration    # ISO 8601 duration

# Numeric
scalar Decimal     # Arbitrary precision decimal
scalar Money       # Currency amount
scalar Percentage  # 0-100 percentage

# String Formats
scalar Email       # RFC 5322 email address
scalar URL         # RFC 3986 URL
scalar UUID        # RFC 4122 UUID
scalar JSON        # Arbitrary JSON
scalar JSONObject  # JSON object specifically

# Geographic
scalar Latitude    # -90 to 90
scalar Longitude   # -180 to 180
scalar PostalCode  # Country-specific postal code

# Binary
scalar Base64      # Base64-encoded binary
scalar Hex         # Hexadecimal string
```

**Custom Scalar Implementation (Python/Strawberry)**

```python
from datetime import datetime
from typing import NewType
import strawberry
from email_validator import validate_email

@strawberry.scalar(
    serialize=lambda v: v.isoformat(),
    parse_value=lambda v: datetime.fromisoformat(v)
)
class DateTime:
    """ISO 8601 datetime with timezone"""
    pass

@strawberry.scalar(
    serialize=lambda v: str(v),
    parse_value=lambda v: validate_email(v).email
)
class Email:
    """RFC 5322 email address"""
    pass
```

### Object Types

**Basic Object Type**

```graphql
type User {
  id: ID!
  username: String!
  email: Email!
  displayName: String
  avatarUrl: URL
  createdAt: DateTime!
  updatedAt: DateTime!
}
```

**Design Guidelines**

1. **Required vs Optional Fields**
   - Use `!` for fields that always exist
   - Make fields nullable if they may be absent
   - Consider client impact of null values

2. **Field Naming**
   - Use camelCase for field names
   - Be descriptive but concise
   - Avoid redundant prefixes (user.userName → user.name)
   - Use consistent naming patterns

3. **Field Types**
   - Use ID for identifiers
   - Use specific scalars (Email vs String)
   - Use enums for fixed sets
   - Use objects for structured data

### Interfaces

**Definition**

```graphql
interface Node {
  """Globally unique identifier"""
  id: ID!
}

interface Timestamped {
  """Creation timestamp"""
  createdAt: DateTime!
  """Last update timestamp"""
  updatedAt: DateTime!
}

interface Actor {
  """Display name for the actor"""
  displayName: String!
  """Avatar image URL"""
  avatarUrl: URL
}
```

**Implementation**

```graphql
type User implements Node & Timestamped & Actor {
  id: ID!
  createdAt: DateTime!
  updatedAt: DateTime!
  displayName: String!
  avatarUrl: URL

  # User-specific fields
  email: Email!
  username: String!
  isVerified: Boolean!
}

type Organization implements Node & Timestamped & Actor {
  id: ID!
  createdAt: DateTime!
  updatedAt: DateTime!
  displayName: String!
  avatarUrl: URL

  # Organization-specific fields
  slug: String!
  memberCount: Int!
}
```

**When to Use Interfaces**

- Shared behavior across types
- Polymorphic queries
- Common field patterns
- Abstract domain concepts

### Union Types

**Definition**

```graphql
union SearchResult = User | Organization | Repository | Issue

union NotificationContent =
  | CommentNotification
  | MentionNotification
  | FollowNotification
  | LikeNotification
```

**Query Example**

```graphql
query Search($term: String!) {
  search(query: $term) {
    ... on User {
      id
      username
      email
    }
    ... on Organization {
      id
      name
      memberCount
    }
    ... on Repository {
      id
      name
      starCount
    }
  }
}
```

**When to Use Unions**

- Mutually exclusive types
- Search results across types
- Polymorphic responses
- Error handling patterns

### Enums

**Definition**

```graphql
enum UserRole {
  ADMIN
  MODERATOR
  USER
  GUEST
}

enum OrderStatus {
  PENDING
  CONFIRMED
  PROCESSING
  SHIPPED
  DELIVERED
  CANCELLED
  REFUNDED
}

enum SortDirection {
  ASC
  DESC
}
```

**Best Practices**

1. **Naming**: SCREAMING_SNAKE_CASE
2. **Stability**: Never remove values (deprecate instead)
3. **Documentation**: Document each value
4. **Semantics**: Use for fixed, known sets only

```graphql
enum UserRole {
  """Full system access"""
  ADMIN

  """Content moderation access"""
  MODERATOR

  """Standard user access"""
  USER

  """Limited guest access"""
  GUEST @deprecated(reason: "Use USER with limited permissions")
}
```

### Input Types

**Definition**

```graphql
input CreateUserInput {
  username: String!
  email: Email!
  password: String!
  displayName: String
  acceptedTerms: Boolean!
}

input UpdateUserInput {
  displayName: String
  avatarUrl: URL
  bio: String
}

input UserFilterInput {
  role: UserRole
  isVerified: Boolean
  createdAfter: DateTime
  createdBefore: DateTime
}

input PaginationInput {
  first: Int
  after: String
  last: Int
  before: String
}
```

**Best Practices**

1. **Separate Inputs**: Create vs Update operations
2. **Validation**: Document constraints in descriptions
3. **Optional Fields**: Make optional fields nullable
4. **Nested Inputs**: Use for complex input structures

---

## Schema Patterns

### Node Pattern (Global Object Identification)

```graphql
interface Node {
  """Globally unique identifier across all types"""
  id: ID!
}

type Query {
  """Fetch any object by its global ID"""
  node(id: ID!): Node

  """Fetch multiple objects by global IDs"""
  nodes(ids: [ID!]!): [Node]!
}

type User implements Node {
  id: ID!  # Format: "User:123" or base64("User:123")
  username: String!
}

type Post implements Node {
  id: ID!  # Format: "Post:456" or base64("Post:456")
  title: String!
}
```

**Implementation (Python)**

```python
import base64
from typing import Union

def encode_global_id(type_name: str, id: str) -> str:
    """Encode type and ID into global ID"""
    return base64.b64encode(f"{type_name}:{id}".encode()).decode()

def decode_global_id(global_id: str) -> tuple[str, str]:
    """Decode global ID into type and ID"""
    decoded = base64.b64decode(global_id).decode()
    type_name, id = decoded.split(":", 1)
    return type_name, id
```

### Connection Pattern (Relay-style Pagination)

```graphql
type PageInfo {
  """Whether more edges exist following the set"""
  hasNextPage: Boolean!

  """Whether more edges exist prior to the set"""
  hasPreviousPage: Boolean!

  """Cursor of the first edge"""
  startCursor: String

  """Cursor of the last edge"""
  endCursor: String
}

type UserEdge {
  """Cursor for pagination"""
  cursor: String!

  """The user node"""
  node: User!
}

type UserConnection {
  """List of edges"""
  edges: [UserEdge!]!

  """Page information"""
  pageInfo: PageInfo!

  """Total count (expensive, optional)"""
  totalCount: Int
}

type Query {
  users(
    first: Int
    after: String
    last: Int
    before: String
    filter: UserFilterInput
  ): UserConnection!
}
```

### Payload Pattern (Mutation Responses)

```graphql
interface MutationPayload {
  """Client mutation ID for request tracking"""
  clientMutationId: String

  """Whether the mutation succeeded"""
  success: Boolean!

  """Error messages if mutation failed"""
  errors: [Error!]
}

type CreateUserPayload implements MutationPayload {
  clientMutationId: String
  success: Boolean!
  errors: [Error!]

  """The created user"""
  user: User

  """The edge for inserting into connections"""
  userEdge: UserEdge
}

type Mutation {
  createUser(input: CreateUserInput!): CreateUserPayload!
}
```

### Error Type Pattern

```graphql
interface Error {
  """Error message"""
  message: String!

  """Error code for client handling"""
  code: ErrorCode!

  """Field path if field-specific"""
  path: [String!]
}

enum ErrorCode {
  VALIDATION_ERROR
  NOT_FOUND
  UNAUTHORIZED
  FORBIDDEN
  CONFLICT
  RATE_LIMITED
  INTERNAL_ERROR
}

type ValidationError implements Error {
  message: String!
  code: ErrorCode!
  path: [String!]

  """Validation rule that failed"""
  rule: String!

  """Expected value or format"""
  expected: String
}

type NotFoundError implements Error {
  message: String!
  code: ErrorCode!
  path: [String!]

  """Type of entity not found"""
  entityType: String!

  """ID that was not found"""
  entityId: ID!
}
```

---

## Query Design

### Top-Level Queries

**Design Principles**

1. **Use Case Oriented**: Each query represents a client use case
2. **Specific and General**: Provide both single-entity and list queries
3. **Filtering**: Support common filtering patterns
4. **Performance**: Bound complexity with pagination

```graphql
type Query {
  # Single entity queries
  user(id: ID!): User
  userByUsername(username: String!): User

  # List queries with pagination
  users(
    first: Int
    after: String
    filter: UserFilterInput
    sort: UserSortInput
  ): UserConnection!

  # Search queries
  searchUsers(query: String!): UserConnection!

  # Aggregate queries
  userStats: UserStats!

  # Current user (authenticated)
  viewer: User
}
```

### Query Arguments

**Filtering**

```graphql
input UserFilterInput {
  # Exact match
  role: UserRole
  isVerified: Boolean

  # Range queries
  createdAfter: DateTime
  createdBefore: DateTime

  # Text search
  username: String

  # List membership
  ids: [ID!]
  roles: [UserRole!]

  # Logical operators
  AND: [UserFilterInput!]
  OR: [UserFilterInput!]
  NOT: UserFilterInput
}
```

**Sorting**

```graphql
input UserSortInput {
  field: UserSortField!
  direction: SortDirection!
}

enum UserSortField {
  CREATED_AT
  UPDATED_AT
  USERNAME
  EMAIL
}

enum SortDirection {
  ASC
  DESC
}
```

### Field Arguments

```graphql
type User {
  id: ID!
  username: String!

  # Parameterized fields
  avatar(size: Int = 128): URL!

  # Filtered relationships
  posts(
    first: Int
    status: PostStatus
  ): PostConnection!

  # Computed fields
  followerCount: Int!
  isFollowedBy(userId: ID!): Boolean!
}
```

### Query Complexity

**Depth Limiting**

```graphql
# Bad: Unlimited depth
query DeepQuery {
  user {
    followers {
      followers {
        followers {
          # ... infinite nesting
        }
      }
    }
  }
}
```

**Complexity Analysis**

```python
def calculate_complexity(query_node, complexity_map):
    """Calculate query complexity score"""
    base_complexity = complexity_map.get(query_node.field_name, 1)

    # Multiply by connection size
    if is_connection(query_node):
        first = query_node.arguments.get('first', 10)
        base_complexity *= first

    # Add child field complexity
    child_complexity = sum(
        calculate_complexity(child, complexity_map)
        for child in query_node.selections
    )

    return base_complexity + child_complexity
```

---

## Mutation Design

### Mutation Structure

```graphql
type Mutation {
  # Entity creation
  createUser(input: CreateUserInput!): CreateUserPayload!

  # Entity updates
  updateUser(id: ID!, input: UpdateUserInput!): UpdateUserPayload!

  # Entity deletion
  deleteUser(id: ID!): DeleteUserPayload!

  # Actions
  followUser(userId: ID!): FollowUserPayload!
  unfollowUser(userId: ID!): UnfollowUserPayload!

  # Bulk operations
  bulkUpdateUsers(inputs: [BulkUpdateUserInput!]!): BulkUpdateUsersPayload!
}
```

### Input Design

**Create Input**

```graphql
input CreatePostInput {
  """Required fields"""
  title: String!
  content: String!

  """Optional fields"""
  tags: [String!]
  publishedAt: DateTime

  """Relationships"""
  authorId: ID!
  categoryId: ID

  """Client mutation ID"""
  clientMutationId: String
}
```

**Update Input**

```graphql
input UpdatePostInput {
  """All fields optional for partial updates"""
  title: String
  content: String
  tags: [String!]
  publishedAt: DateTime

  """Explicit null to clear field"""
  categoryId: ID

  clientMutationId: String
}
```

### Payload Design

**Standard Payload**

```graphql
type CreatePostPayload {
  """Standard fields"""
  clientMutationId: String
  success: Boolean!
  errors: [Error!]

  """Result data"""
  post: Post

  """Related data for cache updates"""
  author: User
  category: Category

  """Connection edge for list updates"""
  postEdge: PostEdge
}
```

**Bulk Payload**

```graphql
type BulkUpdateUsersPayload {
  clientMutationId: String
  success: Boolean!
  errors: [Error!]

  """Partial success tracking"""
  successCount: Int!
  failureCount: Int!

  """Results per input"""
  results: [UpdateUserResult!]!
}

type UpdateUserResult {
  success: Boolean!
  errors: [Error!]
  user: User
  inputIndex: Int!
}
```

### Mutation Patterns

**Optimistic Updates**

```graphql
type Mutation {
  likePost(postId: ID!): LikePostPayload!
}

type LikePostPayload {
  success: Boolean!
  errors: [Error!]
  post: Post!

  """For optimistic UI updates"""
  optimisticId: String
}
```

**Idempotency**

```graphql
input CreateUserInput {
  """Idempotency key for duplicate prevention"""
  idempotencyKey: String!

  username: String!
  email: Email!
}
```

**Transaction Support**

```graphql
type Mutation {
  """Execute multiple mutations atomically"""
  transaction(
    operations: [TransactionOperation!]!
  ): TransactionPayload!
}

input TransactionOperation {
  operationType: OperationType!
  input: JSON!
}

enum OperationType {
  CREATE_USER
  UPDATE_USER
  DELETE_USER
  CREATE_POST
}
```

---

## Subscription Design

### Basic Subscriptions

```graphql
type Subscription {
  """Subscribe to new posts"""
  postCreated: Post!

  """Subscribe to post updates"""
  postUpdated(postId: ID!): Post!

  """Subscribe to user's feed"""
  feedUpdated(userId: ID!): FeedUpdate!
}
```

### Filtered Subscriptions

```graphql
type Subscription {
  """Subscribe with filters"""
  postCreated(
    authorId: ID
    categoryId: ID
    tags: [String!]
  ): Post!

  """Subscribe to specific events"""
  notification(
    types: [NotificationType!]
  ): Notification!
}
```

### Subscription Payloads

```graphql
type Subscription {
  postUpdated(postId: ID!): PostUpdatePayload!
}

type PostUpdatePayload {
  """Update type for client handling"""
  updateType: UpdateType!

  """The updated entity"""
  post: Post!

  """Previous state for diff"""
  previousState: Post

  """Changed fields"""
  changedFields: [String!]!
}

enum UpdateType {
  CREATED
  UPDATED
  DELETED
}
```

---

## Error Handling

### Errors in Schema

**Field-Level Errors**

```graphql
type Query {
  user(id: ID!): UserResult!
}

union UserResult = User | NotFoundError | UnauthorizedError
```

**Payload Errors**

```graphql
type CreateUserPayload {
  success: Boolean!
  errors: [Error!]
  user: User
}
```

### Error Types

```graphql
interface Error {
  message: String!
  code: ErrorCode!
  path: [String!]
}

type ValidationError implements Error {
  message: String!
  code: ErrorCode!
  path: [String!]
  validationErrors: [FieldValidationError!]!
}

type FieldValidationError {
  field: String!
  message: String!
  constraint: String!
}

type NotFoundError implements Error {
  message: String!
  code: ErrorCode!
  path: [String!]
  entityType: String!
  entityId: ID!
}

type UnauthorizedError implements Error {
  message: String!
  code: ErrorCode!
  path: [String!]
  requiredPermission: String
}
```

### Error Codes

```graphql
enum ErrorCode {
  # Client errors (4xx)
  VALIDATION_ERROR
  NOT_FOUND
  UNAUTHORIZED
  FORBIDDEN
  CONFLICT
  RATE_LIMITED

  # Server errors (5xx)
  INTERNAL_ERROR
  SERVICE_UNAVAILABLE
  TIMEOUT

  # Business logic errors
  INSUFFICIENT_BALANCE
  DUPLICATE_ENTRY
  INVALID_STATE
}
```

---

## Pagination

### Offset-Based Pagination

```graphql
type Query {
  users(
    limit: Int = 20
    offset: Int = 0
  ): UserPage!
}

type UserPage {
  items: [User!]!
  total: Int!
  limit: Int!
  offset: Int!
  hasMore: Boolean!
}
```

**Pros**: Simple, familiar
**Cons**: Inconsistent with mutations, inefficient for large offsets

### Cursor-Based Pagination

```graphql
type Query {
  users(
    first: Int
    after: String
    last: Int
    before: String
  ): UserConnection!
}

type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
  totalCount: Int
}

type UserEdge {
  cursor: String!
  node: User!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
```

**Pros**: Consistent with mutations, efficient, handles real-time updates
**Cons**: More complex, cursors can be opaque

### Cursor Implementation

**Opaque Cursor**

```python
import base64
import json

def encode_cursor(data: dict) -> str:
    """Encode cursor data"""
    json_str = json.dumps(data)
    return base64.b64encode(json_str.encode()).decode()

def decode_cursor(cursor: str) -> dict:
    """Decode cursor data"""
    json_str = base64.b64decode(cursor).decode()
    return json.loads(json_str)

# Usage
cursor = encode_cursor({"id": "123", "created_at": "2025-01-15T10:00:00Z"})
# Result: "eyJpZCI6ICIxMjMiLCAiY3JlYXRlZF9hdCI6ICIyMDI1LTAxLTE1VDEwOjAwOjAwWiJ9"
```

**Stable Cursor (ID + Timestamp)**

```python
def make_cursor(id: str, timestamp: datetime) -> str:
    """Create stable cursor"""
    return encode_cursor({
        "id": id,
        "ts": timestamp.isoformat()
    })

def paginate_forward(after: str | None, first: int):
    """Forward pagination"""
    if after:
        cursor_data = decode_cursor(after)
        query = query.filter(
            or_(
                Model.created_at > cursor_data["ts"],
                and_(
                    Model.created_at == cursor_data["ts"],
                    Model.id > cursor_data["id"]
                )
            )
        )

    query = query.order_by(Model.created_at, Model.id).limit(first + 1)
    items = query.all()

    has_next = len(items) > first
    return items[:first], has_next
```

---

## Performance Optimization

### DataLoader Pattern

**Problem: N+1 Queries**

```graphql
query {
  posts {          # 1 query
    id
    title
    author {       # N queries (one per post)
      id
      name
    }
  }
}
```

**Solution: Batching**

```python
from aiodataloader import DataLoader

class UserLoader(DataLoader):
    async def batch_load_fn(self, user_ids):
        """Load users in batch"""
        users = await db.query(User).filter(User.id.in_(user_ids)).all()
        user_map = {user.id: user for user in users}
        return [user_map.get(id) for id in user_ids]

# Usage in resolver
@strawberry.field
async def author(self, info) -> User:
    loader = info.context.loaders.user_loader
    return await loader.load(self.author_id)
```

**DataLoader Features**

1. **Batching**: Collects multiple load() calls, executes once
2. **Caching**: Per-request cache for loaded values
3. **Deduplication**: Multiple loads of same key = single fetch

### Query Complexity Analysis

**Assign Complexity Costs**

```python
COMPLEXITY_MAP = {
    "Query.users": 10,
    "Query.posts": 10,
    "User.posts": 5,
    "User.followers": 10,
    "Post.comments": 3,
}

def calculate_complexity(query_ast, max_depth=5):
    """Calculate total query complexity"""
    def visit_field(field, depth, multiplier):
        if depth > max_depth:
            raise Exception("Query depth exceeded")

        # Base cost
        cost = COMPLEXITY_MAP.get(field.name, 1)

        # Connection multiplier
        if "first" in field.arguments:
            multiplier *= field.arguments["first"]

        cost *= multiplier

        # Child fields
        for selection in field.selections:
            cost += visit_field(selection, depth + 1, multiplier)

        return cost

    return visit_field(query_ast.root, 0, 1)
```

### Caching Strategies

**Field-Level Caching**

```python
import strawberry
from functools import lru_cache

@strawberry.type
class Query:
    @strawberry.field
    @lru_cache(maxsize=1000)
    def expensive_computation(self, input: str) -> str:
        # Expensive operation
        return compute(input)
```

**HTTP Caching**

```graphql
type Query {
  """Cache for 1 hour"""
  publicPosts: [Post!]! @cacheControl(maxAge: 3600)

  """Cache for 5 minutes"""
  trendingPosts: [Post!]! @cacheControl(maxAge: 300)

  """No caching"""
  viewer: User! @cacheControl(maxAge: 0)
}
```

### Persisted Queries

**Concept**: Send query hash instead of full query text

```graphql
# Client sends
{
  "queryId": "abc123...",
  "variables": {"userId": "123"}
}

# Instead of
{
  "query": "query GetUser($userId: ID!) { user(id: $userId) { ... } }",
  "variables": {"userId": "123"}
}
```

**Benefits**: Smaller payloads, query allowlisting, better caching

---

## Security

### Authentication

**Context Pattern**

```python
@strawberry.type
class Query:
    @strawberry.field
    def viewer(self, info) -> User | None:
        """Return authenticated user"""
        return info.context.user

    @strawberry.field
    def user(self, info, id: strawberry.ID) -> User:
        if not info.context.user:
            raise UnauthorizedException("Authentication required")
        return get_user(id)
```

**Directive Pattern**

```graphql
directive @auth(requires: Role = USER) on FIELD_DEFINITION

type Query {
  publicPosts: [Post!]!

  viewer: User! @auth

  adminDashboard: Dashboard! @auth(requires: ADMIN)
}
```

### Authorization

**Field-Level Authorization**

```python
@strawberry.type
class User:
    id: strawberry.ID
    username: str

    @strawberry.field
    def email(self, info) -> str:
        """Only user themselves can see email"""
        if info.context.user.id != self.id:
            raise ForbiddenException("Cannot access email")
        return self._email

    @strawberry.field
    def posts(self, info) -> list[Post]:
        """Filter posts by visibility"""
        if info.context.user.id == self.id:
            return self.all_posts()
        return self.public_posts()
```

**Policy-Based Authorization**

```python
class Policy:
    def can_view_user(self, viewer: User, target: User) -> bool:
        return True

    def can_edit_user(self, viewer: User, target: User) -> bool:
        return viewer.id == target.id or viewer.is_admin

    def can_delete_user(self, viewer: User, target: User) -> bool:
        return viewer.is_admin

@strawberry.type
class Mutation:
    @strawberry.mutation
    def update_user(
        self,
        info,
        id: strawberry.ID,
        input: UpdateUserInput
    ) -> UpdateUserPayload:
        user = get_user(id)
        policy = info.context.policy

        if not policy.can_edit_user(info.context.user, user):
            raise ForbiddenException()

        return update_user(user, input)
```

### Rate Limiting

**Per-User Rate Limiting**

```python
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        user_id: str,
        operation: str,
        limit: int,
        window: timedelta
    ):
        """Check if operation is within rate limit"""
        key = f"ratelimit:{user_id}:{operation}"
        current = await self.redis.get(key)

        if current and int(current) >= limit:
            raise RateLimitException(
                f"Rate limit exceeded: {limit} per {window}"
            )

        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, int(window.total_seconds()))
        await pipe.execute()
```

**Query Complexity Limiting**

```python
def check_complexity(query, max_complexity=1000):
    """Enforce query complexity limits"""
    complexity = calculate_complexity(query)

    if complexity > max_complexity:
        raise Exception(
            f"Query too complex: {complexity} > {max_complexity}"
        )
```

### Input Validation

```python
import re
from email_validator import validate_email

def validate_create_user_input(input: CreateUserInput):
    """Validate user input"""
    errors = []

    # Username validation
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', input.username):
        errors.append(ValidationError(
            field="username",
            message="Must be 3-20 alphanumeric characters",
            code="INVALID_FORMAT"
        ))

    # Email validation
    try:
        validate_email(input.email)
    except:
        errors.append(ValidationError(
            field="email",
            message="Invalid email format",
            code="INVALID_FORMAT"
        ))

    # Password strength
    if len(input.password) < 8:
        errors.append(ValidationError(
            field="password",
            message="Must be at least 8 characters",
            code="TOO_SHORT"
        ))

    if errors:
        raise ValidationException(errors)
```

---

## Versioning

### Field Deprecation

```graphql
type User {
  id: ID!
  name: String! @deprecated(reason: "Use displayName instead")
  displayName: String!

  email: String! @deprecated(
    reason: "Use emailAddress. Will be removed in v2.0"
  )
  emailAddress: Email!
}
```

### Enum Evolution

```graphql
enum UserStatus {
  ACTIVE
  INACTIVE
  SUSPENDED
  DELETED @deprecated(reason: "Use INACTIVE with deletedAt field")
}
```

### Optional Arguments

```graphql
type Query {
  # Old: single filter
  users(role: UserRole): [User!]!

  # New: comprehensive filtering (backward compatible)
  users(
    role: UserRole
    filter: UserFilterInput
  ): [User!]!
}
```

### Schema Evolution Patterns

**Additive Changes (Safe)**

```graphql
# Adding new fields
type User {
  id: ID!
  name: String!
  email: String!
  bio: String!  # New field
}

# Adding new types
type UserProfile {
  bio: String
  location: String
}

# Adding new arguments (optional)
type Query {
  users(
    limit: Int = 20
    filter: UserFilterInput  # New argument
  ): [User!]!
}
```

**Breaking Changes (Avoid)**

```graphql
# Removing fields
type User {
  id: ID!
  # name: String!  # REMOVED - breaking!
}

# Changing field types
type User {
  id: ID!
  age: String!  # Was Int! - breaking!
}

# Making fields non-null
type User {
  id: ID!
  email: String!  # Was String - breaking!
}
```

---

## Schema Federation

### Apollo Federation Basics

```graphql
# Users service
extend schema @link(
  url: "https://specs.apollo.dev/federation/v2.0",
  import: ["@key", "@shareable"]
)

type User @key(fields: "id") {
  id: ID!
  username: String!
  email: String!
}

# Posts service
extend schema @link(
  url: "https://specs.apollo.dev/federation/v2.0",
  import: ["@key", "@external"]
)

type User @key(fields: "id") {
  id: ID! @external
  posts: [Post!]!
}

type Post @key(fields: "id") {
  id: ID!
  title: String!
  author: User!
}
```

### Entity Resolution

```python
@strawberry.federation.type(keys=["id"])
class User:
    id: strawberry.ID
    username: str

    @classmethod
    def resolve_reference(cls, id: strawberry.ID) -> "User":
        """Resolve User entity from other services"""
        return get_user(id)
```

### Schema Stitching

```javascript
const { stitchSchemas } = require('@graphql-tools/stitch');

const schema = stitchSchemas({
  subschemas: [
    {
      schema: usersSchema,
      executor: usersExecutor
    },
    {
      schema: postsSchema,
      executor: postsExecutor
    }
  ]
});
```

---

## Testing

### Query Testing

```python
import pytest
from strawberry.test import GraphQLTestClient

@pytest.fixture
def client():
    return GraphQLTestClient(schema)

def test_query_user(client):
    query = """
        query GetUser($id: ID!) {
            user(id: $id) {
                id
                username
                email
            }
        }
    """

    result = client.query(
        query,
        variables={"id": "123"}
    )

    assert result.errors is None
    assert result.data["user"]["username"] == "testuser"
```

### Mutation Testing

```python
def test_create_user_mutation(client):
    mutation = """
        mutation CreateUser($input: CreateUserInput!) {
            createUser(input: $input) {
                success
                errors {
                    message
                    code
                }
                user {
                    id
                    username
                }
            }
        }
    """

    result = client.query(
        mutation,
        variables={
            "input": {
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123"
            }
        }
    )

    assert result.data["createUser"]["success"] is True
    assert result.data["createUser"]["user"]["username"] == "newuser"
```

### Schema Testing

```python
from graphql import build_schema, validate_schema

def test_schema_validation():
    """Ensure schema is valid"""
    errors = validate_schema(schema)
    assert len(errors) == 0

def test_no_breaking_changes():
    """Compare against previous schema"""
    from graphql import find_breaking_changes

    old_schema = load_schema_from_file("schema.v1.graphql")
    new_schema = schema

    breaking_changes = find_breaking_changes(old_schema, new_schema)
    assert len(breaking_changes) == 0
```

---

## Anti-Patterns

### Schema Design Anti-Patterns

**1. Over-Normalization**

```graphql
# Bad: Too fragmented
type User {
  id: ID!
  profile: UserProfile!
  settings: UserSettings!
  preferences: UserPreferences!
}

# Good: Group related data
type User {
  id: ID!
  username: String!
  email: String!
  displayName: String
  bio: String
  avatarUrl: URL
}
```

**2. Leaky Implementation Details**

```graphql
# Bad: Exposes database structure
type User {
  id: ID!
  user_name: String!  # snake_case from DB
  email_addr: String!
  created_ts: Int!    # Unix timestamp
}

# Good: Clean API
type User {
  id: ID!
  username: String!
  email: Email!
  createdAt: DateTime!
}
```

**3. Non-Nullable Lists**

```graphql
# Bad: Cannot represent errors
type User {
  posts: [Post!]!  # Must always return array
}

# Good: Can return null on error
type User {
  posts: [Post!]  # Returns null if error fetching
}
```

**4. Boolean Arguments**

```graphql
# Bad: Unclear meaning
type Query {
  users(active: Boolean): [User!]!
}

# Good: Explicit enum
type Query {
  users(status: UserStatus): [User!]!
}

enum UserStatus {
  ACTIVE
  INACTIVE
  ALL
}
```

### Query Anti-Patterns

**1. Too Many Root Fields**

```graphql
# Bad: Dozens of root fields
type Query {
  user1: User
  user2: User
  user3: User
  # ... hundreds more
}

# Good: Parameterized queries
type Query {
  user(id: ID!): User
  users(ids: [ID!]!): [User!]!
}
```

**2. Unbounded Lists**

```graphql
# Bad: Can return millions of items
type Query {
  allUsers: [User!]!
}

# Good: Required pagination
type Query {
  users(first: Int!, after: String): UserConnection!
}
```

### Performance Anti-Patterns

**1. Missing DataLoaders**

```graphql
# Causes N+1 queries without DataLoader
query {
  posts {
    author { name }  # Separate query per post
    category { name }  # Separate query per post
  }
}
```

**2. Expensive Computed Fields**

```graphql
type User {
  # Bad: Expensive on every query
  followerCount: Int!  # Counts database rows

  # Good: Pre-computed or cached
  followerCount: Int! @cacheControl(maxAge: 300)
}
```

---

## Best Practices Summary

### Design Checklist

```markdown
## Schema Design Checklist

### Naming
- [ ] Types are nouns (User, Post, Comment)
- [ ] Fields are camelCase
- [ ] Enums are SCREAMING_SNAKE_CASE
- [ ] Mutations are verbs (createUser, updatePost)
- [ ] Booleans start with is/has/can

### Type Safety
- [ ] IDs use ID scalar type
- [ ] Appropriate nullability (prefer non-null)
- [ ] Custom scalars for specific formats
- [ ] Enums for fixed value sets
- [ ] Input types for mutations

### Relationships
- [ ] One-to-many uses lists
- [ ] Many-to-many uses connections
- [ ] Bidirectional relationships consistent
- [ ] Pagination for large collections

### Performance
- [ ] DataLoaders for relationships
- [ ] Pagination required for lists
- [ ] Complexity analysis implemented
- [ ] Expensive fields documented

### Evolution
- [ ] Deprecation over removal
- [ ] Backward compatible changes
- [ ] Migration path documented
- [ ] Version strategy defined

### Documentation
- [ ] All types documented
- [ ] All fields documented
- [ ] Examples provided
- [ ] Edge cases noted

### Security
- [ ] Authentication required
- [ ] Authorization implemented
- [ ] Input validation
- [ ] Rate limiting
- [ ] Query complexity limits
```

### Quick Reference

**Type System**
- Scalar: Int, Float, String, Boolean, ID, Custom
- Object: type User { ... }
- Interface: interface Node { ... }
- Union: union Result = A | B
- Enum: enum Status { ... }
- Input: input CreateInput { ... }

**Patterns**
- Node: Global object identification
- Connection: Relay pagination
- Payload: Mutation responses with errors
- Edge: Cursor + node wrapper

**Pagination**
- Offset: Simple, limit/offset
- Cursor: Efficient, first/after/last/before
- Connection: Full Relay specification

**Security**
- Authentication: Context pattern
- Authorization: Field-level checks
- Rate limiting: Per-user, per-operation
- Validation: Input sanitization

**Performance**
- DataLoader: Batch + cache
- Complexity: Cost analysis
- Caching: Field-level, HTTP
- Persisted Queries: Query allowlisting
