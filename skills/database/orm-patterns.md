---
name: database-orm-patterns
description: Working with ORMs (SQLAlchemy, Prisma, GORM, Diesel)
---



# ORM Patterns

**Scope**: ORM usage patterns, N+1 prevention, transactions, best practices
**Lines**: ~300
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Working with ORMs (SQLAlchemy, Prisma, GORM, Diesel)
- Debugging N+1 query problems
- Implementing eager loading strategies
- Managing database transactions
- Optimizing ORM query performance
- Choosing between ORM and raw SQL
- Performing batch operations

## Core Concepts

### ORM vs Raw SQL

**ORM (Object-Relational Mapping)**: Maps database tables to objects/classes.

**Benefits**:
- Type safety (especially in typed languages)
- Abstraction over SQL dialects
- Protection against SQL injection
- Easier refactoring
- Built-in migrations

**Drawbacks**:
- Performance overhead
- Complex queries can be verbose
- Hidden N+1 problems
- Learning curve for advanced features

### When to Use Each

```
Use ORM when:
├─ Simple CRUD operations
├─ Type safety is critical
├─ Working with relationships
├─ Need cross-database compatibility
└─ Team prefers ORM patterns

Use Raw SQL when:
├─ Complex analytics queries
├─ Performance-critical paths
├─ Bulk operations (1000+ rows)
├─ Database-specific features needed
└─ ORM generates suboptimal queries
```

---

## The N+1 Query Problem

### What is N+1?

**Problem**: Loading a collection of N items, then making 1 query per item to load related data.

**Example**: Load 100 users, then query orders for each user = **101 queries** (1 + 100).

### Detection

**Symptoms**:
- Slow page loads despite simple data
- Database query count >> expected
- Repeated similar queries with different IDs

**Logging**:
```python
# SQLAlchemy: Enable query logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

```typescript
// Prisma: Enable query logging
const prisma = new PrismaClient({
  log: ['query', 'info', 'warn', 'error'],
})
```

```go
// GORM: Enable query logging
db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
  Logger: logger.Default.LogMode(logger.Info),
})
```

```rust
// Diesel: No built-in logging, use diesel::debug_query
let query = users::table.filter(users::id.eq(1));
println!("{}", diesel::debug_query::<diesel::pg::Pg, _>(&query));
```

### N+1 Example (Anti-Pattern)

**SQLAlchemy (Python)**:
```python
# ❌ N+1 PROBLEM: 1 query for users + N queries for orders
users = session.query(User).all()  # 1 query
for user in users:
    orders = user.orders  # N queries (lazy load)
    print(f"{user.name}: {len(orders)} orders")
```

**Prisma (TypeScript)**:
```typescript
// ❌ N+1 PROBLEM
const users = await prisma.user.findMany();  // 1 query
for (const user of users) {
  const orders = await prisma.order.findMany({  // N queries
    where: { userId: user.id }
  });
  console.log(`${user.name}: ${orders.length} orders`);
}
```

**GORM (Go)**:
```go
// ❌ N+1 PROBLEM
var users []User
db.Find(&users)  // 1 query
for _, user := range users {
    var orders []Order
    db.Where("user_id = ?", user.ID).Find(&orders)  // N queries
    fmt.Printf("%s: %d orders\n", user.Name, len(orders))
}
```

**Diesel (Rust)**:
```rust
// ❌ N+1 PROBLEM
let users = users::table.load::<User>(&mut conn)?;  // 1 query
for user in &users {
    let orders = Order::belonging_to(user)  // N queries
        .load::<Order>(&mut conn)?;
    println!("{}: {} orders", user.name, orders.len());
}
```

---

## Eager Loading Solutions

### SQLAlchemy: joinedload / selectinload

**joinedload**: Single query with JOIN
```python
from sqlalchemy.orm import joinedload

# ✅ SOLUTION: 1 query with LEFT OUTER JOIN
users = session.query(User).options(joinedload(User.orders)).all()
for user in users:
    orders = user.orders  # No additional query
    print(f"{user.name}: {len(orders)} orders")

# Generated SQL:
# SELECT users.*, orders.*
# FROM users LEFT OUTER JOIN orders ON users.id = orders.user_id
```

**selectinload**: Two queries (1 for users, 1 for all orders)
```python
from sqlalchemy.orm import selectinload

# ✅ SOLUTION: 2 queries total
users = session.query(User).options(selectinload(User.orders)).all()

# Query 1: SELECT * FROM users
# Query 2: SELECT * FROM orders WHERE user_id IN (?, ?, ...)
```

**When to use which**:
- `joinedload`: Few related items, need data in single query
- `selectinload`: Many related items (avoids cartesian product)
- `lazyload`: Default (lazy), only load when accessed (causes N+1)
- `noload`: Don't load relationship at all

**Multiple relationships**:
```python
users = session.query(User).options(
    selectinload(User.orders).selectinload(Order.items),  # Nested
    joinedload(User.profile)  # Separate relationship
).all()
```

### Prisma: include

**include**: Eager load relationships
```typescript
// ✅ SOLUTION: Single operation with nested query
const users = await prisma.user.findMany({
  include: {
    orders: true,  // Load orders
  }
});

// Or with nested includes
const users = await prisma.user.findMany({
  include: {
    orders: {
      include: {
        items: true  // Load order items
      }
    },
    profile: true  // Load user profile
  }
});
```

**select**: Load specific fields only
```typescript
// Optimize by selecting only needed fields
const users = await prisma.user.findMany({
  select: {
    id: true,
    name: true,
    orders: {
      select: {
        id: true,
        total: true,
      }
    }
  }
});
```

### GORM: Preload / Joins

**Preload**: Separate queries (like selectinload)
```go
// ✅ SOLUTION: 2 queries total
var users []User
db.Preload("Orders").Find(&users)

// Query 1: SELECT * FROM users
// Query 2: SELECT * FROM orders WHERE user_id IN (?, ?, ...)

// Nested preload
db.Preload("Orders.Items").Preload("Profile").Find(&users)
```

**Joins**: Single query with JOIN
```go
// ✅ SOLUTION: 1 query with JOIN
var users []User
db.Joins("Orders").Find(&users)

// SELECT users.*, orders.* FROM users
// LEFT JOIN orders ON orders.user_id = users.id
```

**Preload with conditions**:
```go
db.Preload("Orders", "status = ?", "completed").Find(&users)
```

### Diesel: Associations

**Manual approach** (Diesel doesn't have built-in eager loading):
```rust
use diesel::prelude::*;

// ✅ SOLUTION: 2 queries manually executed
let users = users::table.load::<User>(&mut conn)?;
let user_ids: Vec<i32> = users.iter().map(|u| u.id).collect();

// Single query for all orders
let orders = orders::table
    .filter(orders::user_id.eq_any(&user_ids))
    .load::<Order>(&mut conn)?;

// Group orders by user_id in application code
let orders_by_user: HashMap<i32, Vec<Order>> = orders
    .into_iter()
    .fold(HashMap::new(), |mut acc, order| {
        acc.entry(order.user_id).or_insert_with(Vec::new).push(order);
        acc
    });

for user in &users {
    let user_orders = orders_by_user.get(&user.id).unwrap_or(&vec![]);
    println!("{}: {} orders", user.name, user_orders.len());
}
```

**Using diesel-async with joins**:
```rust
// Single query with JOIN
let results = users::table
    .left_join(orders::table)
    .select((User::as_select(), Option::<Order>::as_select()))
    .load::<(User, Option<Order>)>(&mut conn)?;

// Group by user in application
```

---

## Transaction Management

### SQLAlchemy

**Context manager (recommended)**:
```python
from sqlalchemy.orm import Session

# ✅ Automatic commit/rollback
with Session(engine) as session:
    user = User(name="Alice")
    session.add(user)
    session.commit()  # Explicit commit

# Or with automatic commit on exit
with Session(engine, expire_on_commit=False) as session:
    with session.begin():
        user = User(name="Bob")
        session.add(user)
    # Auto-commit on exit, rollback on exception
```

**Manual transaction**:
```python
session = Session(engine)
try:
    user = User(name="Charlie")
    session.add(user)
    session.commit()
except Exception as e:
    session.rollback()
    raise
finally:
    session.close()
```

**Nested transactions (savepoints)**:
```python
with session.begin():
    user = User(name="Dave")
    session.add(user)

    with session.begin_nested():  # Savepoint
        order = Order(user_id=user.id)
        session.add(order)
        # Rollback this savepoint if error, user still committed
```

### Prisma

**Implicit transactions** (single operations are atomic):
```typescript
// Automatically wrapped in transaction
await prisma.user.create({
  data: {
    name: "Alice",
    orders: {
      create: [
        { total: 100 },
        { total: 200 }
      ]
    }
  }
});
```

**Explicit transactions**:
```typescript
// ✅ Manual transaction for multiple operations
await prisma.$transaction(async (tx) => {
  const user = await tx.user.create({
    data: { name: "Bob" }
  });

  await tx.order.create({
    data: {
      userId: user.id,
      total: 150
    }
  });

  // Rollback automatically on error
});
```

**Sequential transactions** (array form):
```typescript
// All-or-nothing: all succeed or all rollback
await prisma.$transaction([
  prisma.user.create({ data: { name: "Charlie" }}),
  prisma.order.create({ data: { userId: 1, total: 100 }}),
]);
```

**Transaction isolation levels**:
```typescript
await prisma.$transaction(
  async (tx) => {
    // Transaction operations
  },
  {
    isolationLevel: Prisma.TransactionIsolationLevel.Serializable,
    maxWait: 5000,  // Wait up to 5 seconds
    timeout: 10000, // Transaction timeout
  }
);
```

### GORM

**Automatic transactions**:
```go
// Single operation is atomic
db.Create(&User{Name: "Alice"})
```

**Manual transactions**:
```go
// ✅ Explicit transaction
tx := db.Begin()
defer func() {
    if r := recover(); r != nil {
        tx.Rollback()
    }
}()

if err := tx.Create(&User{Name: "Bob"}).Error; err != nil {
    tx.Rollback()
    return err
}

if err := tx.Create(&Order{UserID: 1, Total: 100}).Error; err != nil {
    tx.Rollback()
    return err
}

return tx.Commit().Error
```

**Transaction callback** (cleaner):
```go
// ✅ Auto rollback on error, commit on success
err := db.Transaction(func(tx *gorm.DB) error {
    if err := tx.Create(&User{Name: "Charlie"}).Error; err != nil {
        return err  // Rollback
    }

    if err := tx.Create(&Order{UserID: 1, Total: 150}).Error; err != nil {
        return err  // Rollback
    }

    return nil  // Commit
})
```

**Savepoints**:
```go
tx := db.Begin()
tx.Create(&User{Name: "Dave"})

tx.SavePoint("sp1")
tx.Create(&Order{UserID: 1})
tx.RollbackTo("sp1")  // Rollback to savepoint

tx.Commit()  // User created, order not
```

### Diesel

**Transactions**:
```rust
use diesel::Connection;

// ✅ Explicit transaction
conn.transaction::<_, diesel::result::Error, _>(|conn| {
    diesel::insert_into(users::table)
        .values(&new_user)
        .execute(conn)?;

    diesel::insert_into(orders::table)
        .values(&new_order)
        .execute(conn)?;

    Ok(())  // Commit
})
// Automatic rollback on Err
```

**Nested transactions** (savepoints):
```rust
conn.transaction(|conn| {
    diesel::insert_into(users::table)
        .values(&new_user)
        .execute(conn)?;

    conn.transaction(|conn| {  // Savepoint
        diesel::insert_into(orders::table)
            .values(&new_order)
            .execute(conn)?;
        Ok(())
    })?;

    Ok(())
})
```

---

## Batch Operations

### SQLAlchemy

**Bulk insert** (fast, no ORM overhead):
```python
# ✅ Efficient bulk insert
users = [
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
    # ... 1000 more
]

session.bulk_insert_mappings(User, users)
session.commit()

# Or with ORM objects (slower, but fires events)
session.add_all([User(name="Alice"), User(name="Bob")])
session.commit()
```

**Bulk update**:
```python
# Update multiple rows at once
session.query(User).filter(User.status == "pending").update(
    {"status": "active"},
    synchronize_session=False  # Skip session sync for performance
)
session.commit()
```

**Bulk delete**:
```python
session.query(User).filter(User.status == "inactive").delete()
session.commit()
```

### Prisma

**createMany**:
```typescript
// ✅ Efficient batch insert
await prisma.user.createMany({
  data: [
    { name: "Alice", email: "alice@example.com" },
    { name: "Bob", email: "bob@example.com" },
    // ... more
  ],
  skipDuplicates: true,  // Optional: skip on unique constraint violation
});
```

**updateMany**:
```typescript
await prisma.user.updateMany({
  where: { status: "pending" },
  data: { status: "active" },
});
```

**deleteMany**:
```typescript
await prisma.user.deleteMany({
  where: { status: "inactive" },
});
```

### GORM

**CreateInBatches**:
```go
// ✅ Efficient batch insert
users := []User{
    {Name: "Alice", Email: "alice@example.com"},
    {Name: "Bob", Email: "bob@example.com"},
    // ... more
}

// Insert in batches of 100
db.CreateInBatches(users, 100)
```

**Batch updates**:
```go
// Update all matching rows
db.Model(&User{}).Where("status = ?", "pending").Update("status", "active")

// Or with map for multiple columns
db.Model(&User{}).Where("status = ?", "pending").Updates(map[string]interface{}{
    "status": "active",
    "updated_at": time.Now(),
})
```

### Diesel

**Batch insert**:
```rust
// ✅ Single INSERT with multiple VALUES
diesel::insert_into(users::table)
    .values(&vec![
        NewUser { name: "Alice", email: "alice@example.com" },
        NewUser { name: "Bob", email: "bob@example.com" },
        // ... more
    ])
    .execute(&mut conn)?;
```

**Batch update**:
```rust
diesel::update(users::table.filter(users::status.eq("pending")))
    .set(users::status.eq("active"))
    .execute(&mut conn)?;
```

---

## Query Optimization Techniques

### Select Only Needed Columns

**SQLAlchemy**:
```python
# ❌ Loads all columns
users = session.query(User).all()

# ✅ Load specific columns
users = session.query(User.id, User.name).all()

# Or with load_only
from sqlalchemy.orm import load_only
users = session.query(User).options(load_only(User.id, User.name)).all()
```

**Prisma**:
```typescript
// ✅ Select specific fields
const users = await prisma.user.findMany({
  select: {
    id: true,
    name: true,
  }
});
```

**GORM**:
```go
// ✅ Select specific columns
var users []User
db.Select("id", "name").Find(&users)
```

### Limit + Offset Pagination

**SQLAlchemy**:
```python
# ✅ Efficient pagination
page = 2
per_page = 20
users = session.query(User).limit(per_page).offset((page - 1) * per_page).all()
```

**Prisma**:
```typescript
const page = 2;
const perPage = 20;
const users = await prisma.user.findMany({
  skip: (page - 1) * perPage,
  take: perPage,
});
```

**Cursor-based pagination** (better for large datasets):
```typescript
const users = await prisma.user.findMany({
  take: 20,
  skip: 1,  // Skip the cursor itself
  cursor: {
    id: lastSeenId,
  },
  orderBy: {
    id: 'asc',
  },
});
```

### Counting Efficiently

**SQLAlchemy**:
```python
# ❌ Loads all rows
count = len(session.query(User).all())

# ✅ COUNT query
count = session.query(User).count()

# Or with func.count
from sqlalchemy import func
count = session.query(func.count(User.id)).scalar()
```

**Prisma**:
```typescript
const count = await prisma.user.count({
  where: { status: "active" },
});
```

---

## Raw SQL Escapes

### When to Use Raw SQL

- Complex joins ORM can't express efficiently
- Database-specific functions (window functions, CTEs)
- Bulk operations with special logic
- Performance-critical queries

### SQLAlchemy: text()

```python
from sqlalchemy import text

# ✅ Safe parameterized query
result = session.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": "alice@example.com"}
)
users = result.fetchall()

# Or with ORM objects
users = session.query(User).from_statement(
    text("SELECT * FROM users WHERE status = :status")
).params(status="active").all()
```

### Prisma: $queryRaw

```typescript
import { Prisma } from '@prisma/client';

// ✅ Safe parameterized query (prevents SQL injection)
const users = await prisma.$queryRaw<User[]>`
  SELECT * FROM users WHERE email = ${email}
`;

// For non-SELECT queries
await prisma.$executeRaw`
  UPDATE users SET status = 'active' WHERE created_at < ${cutoffDate}
`;

// Unsafe (only use with trusted input)
const result = await prisma.$queryRawUnsafe(
  'SELECT * FROM users WHERE status = $1',
  'active'
);
```

### GORM: Raw SQL

```go
// ✅ Safe parameterized query
var users []User
db.Raw("SELECT * FROM users WHERE email = ?", "alice@example.com").Scan(&users)

// Execute non-SELECT
db.Exec("UPDATE users SET status = ? WHERE created_at < ?", "active", cutoff)
```

### Diesel: sql_query

```rust
use diesel::sql_query;
use diesel::sql_types::Text;

// ✅ Safe parameterized query
let users = sql_query("SELECT * FROM users WHERE email = $1")
    .bind::<Text, _>("alice@example.com")
    .load::<User>(&mut conn)?;
```

---

## Common ORM Anti-Patterns

### 1. Loading Full Objects When Counting

```python
# ❌ Loads all data just to count
users = session.query(User).filter(User.status == "active").all()
count = len(users)

# ✅ Use COUNT
count = session.query(User).filter(User.status == "active").count()
```

### 2. Updating in Loop

```python
# ❌ N queries
for user in users:
    user.status = "active"
    session.commit()

# ✅ Batch update
session.query(User).filter(User.id.in_([u.id for u in users])).update(
    {"status": "active"},
    synchronize_session=False
)
session.commit()
```

### 3. Not Using Transactions for Related Data

```typescript
// ❌ No transaction (inconsistent state if error occurs)
const user = await prisma.user.create({ data: { name: "Alice" }});
await prisma.order.create({ data: { userId: user.id, total: 100 }});

// ✅ Use transaction
await prisma.$transaction(async (tx) => {
  const user = await tx.user.create({ data: { name: "Alice" }});
  await tx.order.create({ data: { userId: user.id, total: 100 }});
});
```

### 4. SELECT * in Queries

```go
// ❌ Loads all columns (wastes bandwidth)
var users []User
db.Find(&users)

// ✅ Select needed columns
db.Select("id", "name", "email").Find(&users)
```

### 5. Not Handling Connection Pooling

See `database-connection-pooling.md` for proper pool configuration per ORM.

---

## Quick Reference

### Eager Loading Comparison

| ORM | Method | Queries | Use Case |
|-----|--------|---------|----------|
| SQLAlchemy | `joinedload()` | 1 (JOIN) | Few related items |
| SQLAlchemy | `selectinload()` | 2 (IN) | Many related items |
| Prisma | `include` | 1-2 | Any relationships |
| GORM | `Preload()` | 2 (IN) | Standard loading |
| GORM | `Joins()` | 1 (JOIN) | Need JOIN conditions |
| Diesel | Manual grouping | 2 | Full control |

### Transaction Patterns

```python
# SQLAlchemy
with session.begin():
    # operations

# Prisma
await prisma.$transaction([...])

# GORM
db.Transaction(func(tx *gorm.DB) error { ... })

# Diesel
conn.transaction(|conn| { ... })
```

### Optimization Checklist

```
Performance Issues:
[ ] Enable query logging to detect N+1
[ ] Use eager loading (joinedload, include, Preload)
[ ] Select only needed columns (select, load_only)
[ ] Use batch operations for multiple inserts/updates
[ ] Count with COUNT query, not len(results)
[ ] Use transactions for related operations
[ ] Paginate with LIMIT/OFFSET or cursor
[ ] Monitor slow queries (see postgres-query-optimization.md)
[ ] Use raw SQL for complex analytics
[ ] Configure connection pool properly
```

---

## Related Skills

- `postgres-query-optimization.md` - Optimize underlying SQL queries
- `database-connection-pooling.md` - Pool configuration per ORM
- `postgres-schema-design.md` - Schema design affects ORM usage
- `postgres-migrations.md` - ORM migrations (Alembic, Prisma Migrate)

---

## Common Pitfalls

❌ **Ignoring N+1 queries** - Causes exponential slowdown
✅ Always eager load relationships with multiple items

❌ **No transactions for related operations** - Data inconsistency
✅ Wrap related inserts/updates in transaction

❌ **Using loops for batch operations** - Thousands of queries
✅ Use bulk_insert_mappings, createMany, CreateInBatches

❌ **Loading full objects for counting** - Wastes memory/bandwidth
✅ Use count() methods

❌ **Not using proper connection pooling** - Exhausted connections
✅ Configure pool based on workers/threads

❌ **Raw SQL without parameterization** - SQL injection
✅ Always use parameterized queries (text(), $queryRaw, bind)

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
