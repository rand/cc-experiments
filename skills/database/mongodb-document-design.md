---
name: database-mongodb-document-design
description: Designing MongoDB schemas
---



# MongoDB Document Design

**Scope**: Document modeling, embedding vs referencing, schema patterns
**Lines**: ~280
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Designing MongoDB schemas
- Choosing between embedding and referencing
- Modeling relationships in document databases
- Handling large or unbounded arrays
- Optimizing for MongoDB query patterns
- Migrating from relational to document model

## Core Concepts

### Document Model Fundamentals

MongoDB stores data as **BSON documents** (JSON-like):

```javascript
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "name": "Alice",
  "email": "alice@example.com",
  "created_at": ISODate("2024-01-15T10:30:00Z")
}
```

**Key differences from relational**:
- No fixed schema (documents in same collection can vary)
- Supports nested documents and arrays
- No enforced relationships (application-level)
- Optimized for document retrieval (not joins)

### Design Philosophy

**Relational**: Normalize first, denormalize for performance
**MongoDB**: Model for your access patterns, embed related data

**Goal**: Minimize queries by structuring data as it's retrieved.

---

## Embedding vs Referencing

### Embedding (Denormalization)

**Pattern**: Store related data inside the document.

```javascript
// User document with embedded address
{
  "_id": ObjectId("..."),
  "name": "Alice",
  "email": "alice@example.com",
  "address": {
    "street": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94105"
  }
}
```

**When to embed**:
- Related data is always accessed together
- Related data doesn't change often
- Related data size is bounded
- One-to-one or one-to-few relationships

**Pros**:
- Single query to retrieve all data
- Atomicity (update entire document in one operation)
- Better performance (no joins)

**Cons**:
- Duplicates data if embedded document is shared
- Document size can grow large (16MB limit per document)
- Harder to update embedded data across multiple documents

### Referencing (Normalization)

**Pattern**: Store reference to another document (like foreign key).

```javascript
// User document
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "name": "Alice",
  "email": "alice@example.com"
}

// Order document with reference
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("507f1f77bcf86cd799439011"),  // Reference
  "total": 99.99,
  "items": [...]
}
```

**When to reference**:
- Related data changes frequently
- Related data is large
- Unbounded relationships (one-to-many with many)
- Many-to-many relationships
- Need to query related data independently

**Pros**:
- No data duplication
- Smaller documents
- Can update related data once (affects all references)

**Cons**:
- Requires multiple queries or $lookup (join-like)
- No foreign key enforcement (application responsibility)
- Slower than embedding

---

## Decision Tree: Embed or Reference?

```
Start: How is the data accessed?
│
├─ Always accessed together?
│  ├─ Yes → Embed
│  └─ No → Reference
│
├─ How often does related data change?
│  ├─ Rarely → Embed
│  └─ Frequently → Reference
│
├─ How many related items?
│  ├─ One or few (1:1, 1:few) → Embed
│  ├─ Bounded (1:many, predictable) → Embed or Reference
│  └─ Unbounded (1:many, grows indefinitely) → Reference
│
├─ Is related data shared across documents?
│  ├─ Yes → Reference
│  └─ No → Embed
│
└─ Document size concerns?
   ├─ Will exceed 16MB? → Reference
   └─ Stays small → Embed
```

---

## Common Patterns

### Pattern 1: One-to-One (Embed)

**Use case**: User profile

```javascript
{
  "_id": ObjectId("..."),
  "email": "alice@example.com",
  "profile": {
    "first_name": "Alice",
    "last_name": "Smith",
    "bio": "Software engineer",
    "avatar_url": "https://..."
  },
  "created_at": ISODate("...")
}
```

**Why embed**: Profile is always accessed with user, doesn't change often.

### Pattern 2: One-to-Few (Embed)

**Use case**: Blog post with comments (limited)

```javascript
{
  "_id": ObjectId("..."),
  "title": "My Blog Post",
  "content": "Lorem ipsum...",
  "author": "Alice",
  "comments": [
    {
      "author": "Bob",
      "text": "Great post!",
      "created_at": ISODate("...")
    },
    {
      "author": "Charlie",
      "text": "Thanks for sharing",
      "created_at": ISODate("...")
    }
  ]
}
```

**Why embed**: Few comments (10-20), retrieved with post.

**Constraint**: Limit embedded array size (e.g., max 100 comments).

### Pattern 3: One-to-Many (Bounded) - Hybrid

**Use case**: Product with reviews (potentially many)

**Option 1**: Embed first N reviews, reference rest

```javascript
// Product document
{
  "_id": ObjectId("..."),
  "name": "Widget",
  "price": 29.99,
  "recent_reviews": [  // Embed first 10 for quick display
    {
      "user": "Alice",
      "rating": 5,
      "text": "Great product!",
      "created_at": ISODate("...")
    }
  ],
  "review_count": 150
}

// Separate reviews collection for full list
db.reviews.find({ product_id: ObjectId("...") })
```

**Option 2**: Reference all reviews

```javascript
// Product document
{
  "_id": ObjectId("..."),
  "name": "Widget",
  "price": 29.99,
  "review_count": 150
}

// Reviews collection
{
  "_id": ObjectId("..."),
  "product_id": ObjectId("..."),  // Reference
  "user": "Alice",
  "rating": 5,
  "text": "Great product!"
}
```

**Query with $lookup** (join):

```javascript
db.products.aggregate([
  { $match: { _id: ObjectId("...") } },
  { $lookup: {
      from: "reviews",
      localField: "_id",
      foreignField: "product_id",
      as: "reviews"
  }}
])
```

### Pattern 4: One-to-Many (Unbounded) - Reference

**Use case**: User with orders (grows indefinitely)

```javascript
// User document
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "name": "Alice",
  "email": "alice@example.com"
}

// Orders collection
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("507f1f77bcf86cd799439011"),  // Reference
  "items": [...],
  "total": 99.99,
  "created_at": ISODate("...")
}

// Query user's orders
db.orders.find({ user_id: ObjectId("507f1f77bcf86cd799439011") })
```

**Why reference**: Orders grow indefinitely, not always accessed with user.

### Pattern 5: Many-to-Many (Reference with Junction)

**Use case**: Users and roles

**Option 1**: Embed role IDs in user

```javascript
// User document
{
  "_id": ObjectId("..."),
  "name": "Alice",
  "role_ids": [
    ObjectId("role1"),
    ObjectId("role2")
  ]
}

// Roles collection
{
  "_id": ObjectId("role1"),
  "name": "admin",
  "permissions": ["read", "write", "delete"]
}

// Query with $lookup
db.users.aggregate([
  { $match: { _id: ObjectId("...") } },
  { $lookup: {
      from: "roles",
      localField: "role_ids",
      foreignField: "_id",
      as: "roles"
  }}
])
```

**Option 2**: Separate junction collection

```javascript
// Users
{ "_id": ObjectId("user1"), "name": "Alice" }

// Roles
{ "_id": ObjectId("role1"), "name": "admin" }

// User-Roles junction
{
  "user_id": ObjectId("user1"),
  "role_id": ObjectId("role1"),
  "granted_at": ISODate("...")
}
```

---

## Avoiding Unbounded Arrays

**Problem**: Embedding unbounded arrays leads to document growth and performance issues.

```javascript
// ❌ BAD: Unbounded array
{
  "_id": ObjectId("..."),
  "user": "Alice",
  "posts": [  // Could grow to thousands
    { "title": "Post 1", "content": "..." },
    { "title": "Post 2", "content": "..." },
    // ... thousands more
  ]
}
```

**Solutions**:

### Solution 1: Reference Instead

```javascript
// User
{ "_id": ObjectId("user1"), "name": "Alice" }

// Posts (separate collection)
{ "_id": ObjectId("..."), "user_id": ObjectId("user1"), "title": "Post 1" }
{ "_id": ObjectId("..."), "user_id": ObjectId("user1"), "title": "Post 2" }
```

### Solution 2: Bucketing Pattern

**Use case**: Time-series data (sensor readings, logs)

```javascript
// Instead of one document per reading:
// { sensor_id: 1, reading: 23.5, timestamp: ... }

// Bucket readings by hour:
{
  "_id": ObjectId("..."),
  "sensor_id": 1,
  "bucket_hour": ISODate("2024-01-15T10:00:00Z"),
  "readings": [
    { "value": 23.5, "minute": 0 },
    { "value": 23.7, "minute": 1 },
    // ... up to 60 readings per hour
  ],
  "reading_count": 60
}
```

**Benefits**:
- Reduces document count (60 readings → 1 document)
- Bounded array size (max 60 readings)
- Efficient queries (one document per hour)

### Solution 3: Outlier Pattern

**Use case**: Products with varying review counts (most have few, some have thousands)

```javascript
// For products with < 100 reviews: embed
{
  "_id": ObjectId("product1"),
  "name": "Widget",
  "reviews": [
    { "user": "Alice", "rating": 5, "text": "..." }
  ],
  "review_count": 10
}

// For products with > 100 reviews: reference
{
  "_id": ObjectId("product2"),
  "name": "Popular Widget",
  "review_count": 5000,
  "has_outlier_reviews": true  // Flag
}

// Separate reviews collection for outlier products
db.reviews.find({ product_id: ObjectId("product2") })
```

---

## Schema Validation

MongoDB supports **JSON Schema validation** to enforce structure.

```javascript
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["email", "name", "created_at"],
      properties: {
        email: {
          bsonType: "string",
          pattern: "^.+@.+$",
          description: "must be a valid email"
        },
        name: {
          bsonType: "string",
          minLength: 1,
          maxLength: 100
        },
        age: {
          bsonType: "int",
          minimum: 0,
          maximum: 120
        },
        created_at: {
          bsonType: "date"
        }
      }
    }
  }
})
```

**Validation modes**:
- `strict` (default): Reject invalid documents
- `moderate`: Validate new documents, allow existing invalid ones

---

## Indexing Strategies

### Single Field Index

```javascript
db.users.createIndex({ email: 1 })  // Ascending
db.users.createIndex({ created_at: -1 })  // Descending
```

### Compound Index

```javascript
db.orders.createIndex({ user_id: 1, created_at: -1 })
```

**Order matters**: Can use for `user_id` alone, but not `created_at` alone.

### Unique Index

```javascript
db.users.createIndex({ email: 1 }, { unique: true })
```

### Sparse Index

**Use case**: Index field that doesn't exist in all documents.

```javascript
db.users.createIndex({ phone: 1 }, { sparse: true })
```

Only indexes documents with `phone` field.

### TTL Index (Auto-Delete)

**Use case**: Session data, temporary records.

```javascript
db.sessions.createIndex(
  { created_at: 1 },
  { expireAfterSeconds: 3600 }  // Delete after 1 hour
)
```

### Text Index (Full-Text Search)

```javascript
db.posts.createIndex({ title: "text", content: "text" })

// Search
db.posts.find({ $text: { $search: "mongodb tutorial" } })
```

---

## Common Pitfalls

❌ **Embedding unbounded arrays** - Document grows indefinitely
✅ Use referencing or bucketing pattern

❌ **Normalizing like relational DB** - Loses MongoDB benefits
✅ Embed related data when accessed together

❌ **No indexing on reference fields** - Slow lookups
✅ Index foreign key fields (`user_id`, etc.)

❌ **Exceeding 16MB document limit** - Insert/update fails
✅ Reference large data, use GridFS for files

❌ **Using $lookup for every query** - Slow (like SQL joins)
✅ Embed data when possible, minimize lookups

❌ **No schema validation** - Data inconsistency
✅ Use JSON Schema validation for structure

---

## Migration from Relational

### Relational → MongoDB Mapping

| Relational | MongoDB |
|------------|---------|
| Table | Collection |
| Row | Document |
| Column | Field |
| Primary Key | `_id` field |
| Foreign Key | Reference (ObjectId) or embedded |
| JOIN | $lookup or embedded |
| Index | Index |

### Example: Blog Schema

**Relational**:
```sql
CREATE TABLE users (id, name, email);
CREATE TABLE posts (id, user_id, title, content);
CREATE TABLE comments (id, post_id, user_id, text);
```

**MongoDB (Embedded)**:
```javascript
// posts collection
{
  "_id": ObjectId("..."),
  "title": "My Post",
  "content": "...",
  "author": {  // Embedded user (denormalized)
    "name": "Alice",
    "email": "alice@example.com"
  },
  "comments": [  // Embedded comments
    {
      "author": "Bob",
      "text": "Great post!",
      "created_at": ISODate("...")
    }
  ]
}
```

**MongoDB (Referenced)**:
```javascript
// users collection
{ "_id": ObjectId("user1"), "name": "Alice", "email": "..." }

// posts collection
{
  "_id": ObjectId("post1"),
  "user_id": ObjectId("user1"),  // Reference
  "title": "My Post",
  "content": "..."
}

// comments collection
{
  "_id": ObjectId("..."),
  "post_id": ObjectId("post1"),  // Reference
  "user_id": ObjectId("user1"),  // Reference
  "text": "Great post!"
}
```

**Decision**: Embed if data accessed together, reference if queried independently.

---

## Quick Reference

### Embed When:
- Data accessed together
- One-to-one or one-to-few relationship
- Related data doesn't change often
- Related data is small

### Reference When:
- Data queried independently
- One-to-many (unbounded)
- Many-to-many
- Related data changes frequently
- Related data is large or shared

### Design Checklist

```
Schema Design:
[ ] Modeled for access patterns (not normalization first)
[ ] Embedded data that's always accessed together
[ ] Referenced unbounded or frequently changing data
[ ] Avoided unbounded arrays
[ ] Considered bucketing for time-series data
[ ] Added schema validation for critical fields

Indexes:
[ ] _id indexed automatically
[ ] Foreign key fields (user_id, etc.) indexed
[ ] Frequently queried fields indexed
[ ] Compound indexes for multi-field queries
[ ] Unique indexes where appropriate

Performance:
[ ] Documents stay under 16MB
[ ] Minimize use of $lookup (prefer embedding)
[ ] Use projections to return only needed fields
[ ] Consider capping collections for logs/events
```

---

## Related Skills

- `postgres-schema-design.md` - Relational schema design for comparison
- `database-selection.md` - When to use MongoDB vs PostgreSQL
- `redis-data-structures.md` - Complementary data store for caching
- `orm-patterns.md` - ORM usage with MongoDB (Mongoose, etc.)

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
