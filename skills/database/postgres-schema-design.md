---
name: database-postgres-schema-design
description: Designing new database schemas
---



# PostgreSQL Schema Design

**Scope**: Table design, relationships, normalization, data types
**Lines**: ~320
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Designing new database schemas
- Modeling relationships (1:1, 1:N, N:M)
- Deciding normalization levels
- Choosing primary key strategies
- Handling polymorphic associations
- Planning for soft deletes or audit trails
- Selecting appropriate data types

## Core Concepts

### Database Normalization

**Goal**: Eliminate redundancy, maintain data integrity.

#### First Normal Form (1NF)

**Rule**: Each column contains atomic values (no arrays, no repeated groups).

```sql
-- ❌ VIOLATES 1NF: Multiple emails in one column
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    emails VARCHAR(500)  -- 'alice@example.com, alice@work.com'
);

-- ✅ 1NF: Atomic values
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE user_emails (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    email VARCHAR(255)
);
```

#### Second Normal Form (2NF)

**Rule**: 1NF + no partial dependencies (all non-key columns depend on entire primary key).

```sql
-- ❌ VIOLATES 2NF: teacher_name depends only on teacher_id, not (student_id, teacher_id)
CREATE TABLE enrollments (
    student_id INT,
    teacher_id INT,
    teacher_name VARCHAR(100),  -- Partial dependency
    PRIMARY KEY (student_id, teacher_id)
);

-- ✅ 2NF: Separate teacher data
CREATE TABLE teachers (
    id INT PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE enrollments (
    student_id INT,
    teacher_id INT REFERENCES teachers(id),
    PRIMARY KEY (student_id, teacher_id)
);
```

#### Third Normal Form (3NF)

**Rule**: 2NF + no transitive dependencies (non-key columns don't depend on other non-key columns).

```sql
-- ❌ VIOLATES 3NF: country depends on city (transitive dependency)
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    city VARCHAR(100),
    country VARCHAR(100)  -- Depends on city, not id
);

-- ✅ 3NF: Separate city/country
CREATE TABLE cities (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    country VARCHAR(100)
);

CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    city_id INT REFERENCES cities(id)
);
```

### When to Denormalize

**Reasons**:
- Read performance (avoid JOINs)
- Analytics/reporting
- Immutable data (historical snapshots)

**Example**: Order totals

```sql
-- Normalized (calculate on query)
SELECT SUM(quantity * price) FROM order_items WHERE order_id = 123;

-- Denormalized (store total on order)
CREATE TABLE orders (
    id INT PRIMARY KEY,
    total DECIMAL(10,2)  -- Denormalized for performance
);

-- Update total when items change (trigger or application logic)
```

---

## Relationship Patterns

### One-to-One (1:1)

**Use case**: Splitting tables for optional/large data.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_profiles (
    user_id INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    bio TEXT,
    avatar_url VARCHAR(500),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Key points**:
- `user_id` is both PRIMARY KEY and FOREIGN KEY
- `ON DELETE CASCADE` ensures orphan cleanup
- Profile is optional (can have user without profile)

### One-to-Many (1:N)

**Use case**: Most common relationship (users → posts, orders → items).

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_posts_user_id ON posts(user_id);
```

**Key points**:
- Foreign key on "many" side (posts.user_id)
- Index on foreign key for JOIN performance
- `NOT NULL` if every post must have a user

### Many-to-Many (N:M)

**Use case**: Tags, roles, followers.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- Junction table
CREATE TABLE user_tags (
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    tag_id INT REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, tag_id)
);

CREATE INDEX idx_user_tags_tag_id ON user_tags(tag_id);
```

**Key points**:
- Junction table with composite primary key
- Indexes on both foreign keys
- Can add extra columns (created_at, metadata)

### Self-Referencing (Hierarchical)

**Use case**: Comments, org charts, file systems.

```sql
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    parent_id INT REFERENCES comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_comments_parent_id ON comments(parent_id);
```

**Querying hierarchies**:
```sql
-- Recursive CTE for threaded comments
WITH RECURSIVE thread AS (
    -- Base case: top-level comments
    SELECT id, parent_id, content, 1 AS depth
    FROM comments WHERE parent_id IS NULL

    UNION ALL

    -- Recursive case: child comments
    SELECT c.id, c.parent_id, c.content, t.depth + 1
    FROM comments c
    JOIN thread t ON c.parent_id = t.id
)
SELECT * FROM thread ORDER BY depth, id;
```

---

## Primary Key Strategies

### Serial Integer (Auto-increment)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255)
);
```

**Pros**:
- Simple, compact (4 bytes)
- Sequential, good for indexes
- Human-readable

**Cons**:
- Predictable (security concern for public IDs)
- Doesn't work well in distributed systems (ID conflicts)
- Reveals record count

### UUID (Universally Unique Identifier)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255)
);
```

**Pros**:
- Globally unique (safe for distributed systems)
- Unpredictable (better security)
- Can generate client-side

**Cons**:
- Larger (16 bytes vs 4)
- Random (worse index performance)
- Not human-readable

### ULID/KSUID (Sortable UUIDs)

```sql
-- Using ulid extension
CREATE EXTENSION IF NOT EXISTS ulid;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT ulid_to_uuid(ulid_generate()),
    email VARCHAR(255)
);
```

**Pros**:
- Globally unique + sortable by time
- Better index performance than pure UUID
- Unpredictable

**Cons**:
- Requires extension
- Larger than integer

### Decision Tree

```
Do you need distributed ID generation?
├─ Yes → UUID or ULID
│   └─ Need time-ordering? → ULID
│       └─ Otherwise → UUID
└─ No → Is predictability a security concern?
    ├─ Yes → UUID
    └─ No → SERIAL (simplest, best performance)
```

---

## Common Schema Patterns

### Timestamps (Audit Trail)

```sql
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_posts_updated_at
BEFORE UPDATE ON posts
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
```

### Soft Deletes

```sql
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    deleted_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_posts_deleted_at ON posts(deleted_at) WHERE deleted_at IS NOT NULL;

-- Query active posts
SELECT * FROM posts WHERE deleted_at IS NULL;

-- "Delete" a post
UPDATE posts SET deleted_at = NOW() WHERE id = 123;
```

**Pros**:
- Can recover deleted data
- Audit trail of deletions

**Cons**:
- Complicates queries (must filter deleted_at IS NULL)
- UNIQUE constraints need to account for soft deletes
- Table grows indefinitely (need archival strategy)

**Alternative**: Archived tables

```sql
-- Move to archive table on delete
CREATE TABLE posts_archive (LIKE posts INCLUDING ALL);

INSERT INTO posts_archive SELECT * FROM posts WHERE id = 123;
DELETE FROM posts WHERE id = 123;
```

### Versioning/History

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE document_versions (
    id SERIAL PRIMARY KEY,
    document_id INT REFERENCES documents(id) ON DELETE CASCADE,
    version INT NOT NULL,
    title VARCHAR(255),
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (document_id, version)
);

-- Save version on update (trigger or application logic)
```

### Polymorphic Associations (Multiple Types)

**Problem**: Comments can belong to posts OR videos.

**Option 1: Exclusive FKs (Best)**

```sql
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    post_id INT REFERENCES posts(id) ON DELETE CASCADE,
    video_id INT REFERENCES videos(id) ON DELETE CASCADE,
    content TEXT,
    CHECK (
        (post_id IS NOT NULL AND video_id IS NULL) OR
        (post_id IS NULL AND video_id IS NOT NULL)
    )
);

CREATE INDEX idx_comments_post_id ON comments(post_id) WHERE post_id IS NOT NULL;
CREATE INDEX idx_comments_video_id ON comments(video_id) WHERE video_id IS NOT NULL;
```

**Pros**: Type-safe, enforced by database
**Cons**: Must add column for each new type

**Option 2: Generic FK (Not Recommended)**

```sql
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    commentable_type VARCHAR(50),  -- 'Post' or 'Video'
    commentable_id INT,             -- ID in posts or videos
    content TEXT
);

CREATE INDEX idx_comments_polymorphic ON comments(commentable_type, commentable_id);
```

**Pros**: Flexible, no schema changes for new types
**Cons**: No foreign key constraint, can't JOIN directly, error-prone

**Option 3: Supertable (Inheritance)**

```sql
CREATE TABLE commentables (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL
);

CREATE TABLE posts (
    id INT PRIMARY KEY REFERENCES commentables(id)
    title VARCHAR(255)
);

CREATE TABLE videos (
    id INT PRIMARY KEY REFERENCES commentables(id),
    url VARCHAR(500)
);

CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    commentable_id INT REFERENCES commentables(id),
    content TEXT
);
```

**Pros**: Type-safe, can query all commentables
**Cons**: Complex, requires joins for post/video data

---

## Data Type Selection

### Text/String Types

| Type | Max Size | Use Case |
|------|----------|----------|
| `CHAR(n)` | n chars (fixed) | Fixed-length codes (e.g., country codes 'US') |
| `VARCHAR(n)` | n chars | Most text (emails, names, titles) |
| `TEXT` | Unlimited | Large text (blog posts, descriptions) |

**Recommendation**: Use `TEXT` or `VARCHAR(n)` (for validation), avoid `CHAR` unless fixed-length.

### Numeric Types

| Type | Range | Storage | Use Case |
|------|-------|---------|----------|
| `INT` / `INTEGER` | ±2 billion | 4 bytes | Most integers |
| `BIGINT` | ±9 quintillion | 8 bytes | Large counts (user IDs at scale) |
| `SERIAL` | Auto-increment INT | 4 bytes | Primary keys |
| `BIGSERIAL` | Auto-increment BIGINT | 8 bytes | Primary keys at scale |
| `DECIMAL(p,s)` | Exact | Variable | Money, exact calculations |
| `NUMERIC(p,s)` | Same as DECIMAL | Variable | Money, exact calculations |
| `REAL` | 6 decimal digits | 4 bytes | Approximate (avoid for money) |
| `DOUBLE PRECISION` | 15 decimal digits | 8 bytes | Scientific calculations |

**Money**: Always use `DECIMAL(10,2)` or store cents as `BIGINT`.

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    price DECIMAL(10,2) NOT NULL  -- $12,345,678.99
);

-- Or store cents as integer (avoids floating-point issues)
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    price_cents BIGINT NOT NULL  -- 1234567899 = $12,345,678.99
);
```

### Date/Time Types

| Type | Range | Precision | Use Case |
|------|-------|-----------|----------|
| `DATE` | 4713 BC to 5874897 AD | Day | Birthdays, event dates |
| `TIME` | 00:00:00 to 24:00:00 | Microsecond | Time of day |
| `TIMESTAMP` | 4713 BC to 294276 AD | Microsecond | Most timestamps |
| `TIMESTAMPTZ` | Same as TIMESTAMP | Microsecond | **Recommended** (timezone-aware) |

**Always use `TIMESTAMPTZ`** for timestamps (stores UTC, displays in session timezone).

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ
);
```

### Boolean

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE
);
```

### JSON/JSONB

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    metadata JSONB  -- Use JSONB (not JSON) for performance
);

-- Query JSONB
SELECT * FROM events WHERE metadata @> '{"status": "active"}';
SELECT * FROM events WHERE metadata->>'user_id' = '123';

-- Index JSONB
CREATE INDEX idx_events_metadata_status ON events USING GIN ((metadata->'status'));
```

**JSONB vs JSON**:
- **JSONB**: Binary format, supports indexing, faster queries, **recommended**
- **JSON**: Text format, preserves formatting, slower

---

## Schema Design Checklist

```
Primary Keys:
[ ] Every table has a primary key
[ ] Primary key type chosen (SERIAL vs UUID vs ULID)

Foreign Keys:
[ ] Foreign keys defined with REFERENCES
[ ] ON DELETE behavior specified (CASCADE, SET NULL, RESTRICT)
[ ] Indexes on foreign key columns

Indexes:
[ ] Foreign keys indexed
[ ] Frequently queried columns indexed
[ ] Composite indexes for multi-column queries
[ ] UNIQUE constraints where appropriate

Timestamps:
[ ] created_at on all tables
[ ] updated_at on mutable tables
[ ] Trigger to auto-update updated_at

Constraints:
[ ] NOT NULL on required columns
[ ] CHECK constraints for validation
[ ] UNIQUE constraints for uniqueness

Data Types:
[ ] TIMESTAMPTZ (not TIMESTAMP) for dates
[ ] DECIMAL (not FLOAT) for money
[ ] TEXT or VARCHAR(n) for strings
[ ] JSONB (not JSON) for JSON data

Normalization:
[ ] At least 3NF (unless intentionally denormalized)
[ ] Denormalization justified with comments

Soft Deletes (if applicable):
[ ] deleted_at column
[ ] Index on deleted_at
[ ] UNIQUE constraints account for soft deletes
```

---

## Common Pitfalls

❌ **Using TIMESTAMP without timezone** - Causes timezone bugs
✅ Always use `TIMESTAMPTZ`

❌ **No index on foreign keys** - Slow JOINs
✅ Create index on every foreign key column

❌ **FLOAT/REAL for money** - Floating-point errors
✅ Use `DECIMAL(10,2)` or store cents as `BIGINT`

❌ **No primary key** - Can't update/delete reliably
✅ Every table must have a primary key

❌ **Generic polymorphic FKs** - No referential integrity
✅ Use exclusive FKs or supertable pattern

❌ **VARCHAR without length** - Behaves like TEXT (misleading)
✅ Use `TEXT` or `VARCHAR(n)` with explicit length

❌ **Not specifying ON DELETE** - Orphaned rows
✅ Always specify `ON DELETE CASCADE` or `SET NULL` or `RESTRICT`

---

## Related Skills

- `postgres-migrations.md` - Evolving schemas safely
- `postgres-query-optimization.md` - Index strategies for performance
- `orm-patterns.md` - ORM-specific schema patterns
- `database-selection.md` - When to use Postgres vs other databases

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
