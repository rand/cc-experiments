---
name: discover-database
description: Automatically discover database skills when working with SQL, PostgreSQL, MongoDB, Redis, database schema design, query optimization, migrations, connection pooling, ORMs, or database selection. Activates for database design, optimization, and implementation tasks.
license: MIT
metadata:
  author: rand
  version: "4.0"
compatibility: Designed for Claude Code. Compatible with any agent supporting the Agent Skills format.
---

# Database Skills Discovery

Provides automatic access to comprehensive database design, optimization, and implementation skills.

## When This Skill Activates
This skill auto-activates when you're working with:
- SQL databases (PostgreSQL, MySQL)
- NoSQL databases (MongoDB, Redis)
- Database schema design and modeling
- Query optimization and performance tuning
- Database migrations and schema evolution
- Connection pooling configuration
- ORM usage and patterns
- Database selection and architecture decisions
- caching
- cache
- Redis
- CDN
- HTTP caching
- cache invalidation
- performance
- Service Workers

## Available Skills

### Quick Reference

The Database category contains 19 skills across 2 subcategories:

**Database (12 skills):**
1. **postgres-schema-design** - Schema design, relationships, data types, normalization
2. **postgres-query-optimization** - EXPLAIN plans, indexes, slow query debugging
3. **postgres-migrations** - Schema changes, zero-downtime, rollback strategies
4. **mongodb-document-design** - Document modeling, embedding vs referencing
5. **redis-data-structures** - Caching, sessions, rate limiting, leaderboards
6. **database-connection-pooling** - Pool configuration, debugging exhaustion
7. **orm-patterns** - ORM best practices, N+1 prevention, eager loading
8. **database-selection** - Choosing databases, SQL vs NoSQL decisions

Plus 4 more in `../database/INDEX.md`

**Caching (7 skills):** See `../caching/INDEX.md`

### Load Full Category Details
Read ../database/INDEX.md
Read ../caching/INDEX.md

## Common Workflows

### New Database Project
**Sequence**: Selection → Schema design → Connection pooling

Read ../database/database-selection.md         # Choose database
Read ../database/postgres-schema-design.md     # or mongodb-document-design.md
Read ../database/database-connection-pooling.md


### Query Performance Debugging
**Sequence**: Optimization → Connection pooling → ORM patterns

Read ../database/postgres-query-optimization.md  # Debug slow queries
Read ../database/database-connection-pooling.md  # Check pool settings
Read ../database/orm-patterns.md                 # Fix N+1 queries


### Schema Evolution
**Sequence**: Schema design → Migrations

Read ../database/postgres-schema-design.md    # Design changes
Read ../database/postgres-migrations.md       # Implement safely


### Caching Layer
**Sequence**: Redis structures → Cache patterns

Read ../database/redis-data-structures.md     # Redis patterns
Read ../caching/INDEX.md                      # Cache patterns

## Skill Selection Guide

**PostgreSQL skills** (relational, ACID, complex queries):
- `postgres-schema-design.md` - Design relational schemas
- `postgres-query-optimization.md` - Optimize complex queries
- `postgres-migrations.md` - Evolve schema over time

**MongoDB skills** (document-oriented, flexible schema):
- `mongodb-document-design.md` - Design document structures
- Choose when: Flexible schema, nested data, rapid iteration

**Redis skills** (in-memory, key-value, caching):
- `redis-data-structures.md` - Caching, sessions, rate limiting
- Choose when: Speed critical, caching layer, real-time features

**Cross-database skills**:
- `database-selection.md` - **Start here** for new projects
- `database-connection-pooling.md` - All databases need this
- `orm-patterns.md` - When using ORMs (SQLAlchemy, Prisma, Mongoose)

## Integration with Other Skills

Database skills commonly combine with:

**API skills** (`discover-api`):
- API endpoints → Database queries
- Connection pooling for API servers
- Query optimization for API performance
- Migrations alongside API versioning

**Backend language skills** (`discover-backend`):
- Python: SQLAlchemy, psycopg2, PyMongo
- Zig: PostgreSQL C bindings
- Rust: SQLx, Diesel
- Go: database/sql, GORM

**Testing skills** (`discover-testing`):
- Integration tests with test databases
- Migration testing
- Query performance testing
- Data fixture management

**Data pipeline skills** (`discover-data`):
- ETL from databases
- Database as data source
- Bulk data operations
- Streaming database changes (CDC)

**Observability skills** (`discover-observability`):
- Query metrics and slow query logs
- Connection pool metrics
- Database performance monitoring
- Alert configuration

## Progressive Loading

This gateway skill (~200 lines, ~2K tokens) enables progressive loading:
- **Level 1**: Gateway loads automatically (you're here now)
- **Level 2**: Load category INDEX.md (~3K tokens) for full overview
- **Level 3**: Load specific skills (~2-4K tokens each) as needed

Total context: 2K + 3K + skill(s) = 5-10K tokens vs 25K+ for entire index.

## Quick Start Examples

**"Design a PostgreSQL schema for an e-commerce app"**:
Read ../database/postgres-schema-design.md


**"Why is my query slow?"**:
Read ../database/postgres-query-optimization.md


**"How do I safely change my database schema?"**:
Read ../database/postgres-migrations.md


**"Should I use MongoDB or PostgreSQL?"**:
Read ../database/database-selection.md


**"Implement caching with Redis"**:
Read ../database/redis-data-structures.md


**"Fix N+1 queries in my ORM"**:
Read ../database/orm-patterns.md


## Database Type Decision Tree

```
Need ACID transactions? YES → PostgreSQL
Need complex queries/joins? YES → PostgreSQL
Need flexible schema? YES → MongoDB
Need real-time caching? YES → Redis
Need full-text search? YES → PostgreSQL (with extensions) or Elasticsearch
Need graph relationships? YES → Neo4j or PostgreSQL (with extensions)
Need analytics? YES → DuckDB or Redpanda + Iceberg
```

For detailed decision-making:
Read ../database/database-selection.md


## PostgreSQL Focus Areas

**Schema design** → `postgres-schema-design.md`:
- Tables, columns, data types
- Primary keys, foreign keys, constraints
- Normalization vs denormalization
- Indexing strategies

**Query optimization** → `postgres-query-optimization.md`:
- EXPLAIN and EXPLAIN ANALYZE
- Index selection and creation
- Query plan analysis
- Performance tuning

**Migrations** → `postgres-migrations.md`:
- Schema change strategies
- Zero-downtime deployments
- Rollback procedures
- Migration tools (Alembic, Flyway, migrate)

## NoSQL Focus Areas

**MongoDB** → `mongodb-document-design.md`:
- Document structure and embedding
- References vs embedding tradeoffs
- Schema versioning
- Index design for documents

**Redis** → `redis-data-structures.md`:
- Strings, hashes, lists, sets, sorted sets
- Caching patterns and TTLs
- Session storage
- Rate limiting implementations
- Leaderboards and counters

## ORM Considerations

Before using ORMs, load:
Read ../database/orm-patterns.md


**Common ORM pitfalls**:
- N+1 query problems
- Lazy vs eager loading confusion
- Transaction management
- Raw SQL when necessary
- Migration generation

**Supported ORMs**:
- SQLAlchemy (Python)
- Prisma (TypeScript/Node.js)
- Diesel (Rust)
- GORM (Go)
- ActiveRecord (Ruby)
- Entity Framework (C#)

## Usage Instructions

1. **Auto-activation**: This skill loads automatically when Claude Code detects database work
2. **Browse skills**: Run `Read ../database/INDEX.md` for full category overview
3. **Load specific skills**: Use bash commands above to load individual skills
4. **Follow workflows**: Use recommended sequences for common patterns
5. **Decision support**: Start with `database-selection.md` for new projects


**Next Steps**: Run `Read ../database/INDEX.md` to see full category details, or load specific skills using the bash commands above.
