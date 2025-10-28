# Alembic Migrations Example

Complete Alembic setup with example migrations.

## Setup

```bash
# Install dependencies
pip install alembic psycopg2-binary

# Or with uv
uv add alembic psycopg2-binary
```

## Configuration

Edit `alembic.ini` and set your database URL:

```ini
sqlalchemy.url = postgresql://user:password@localhost:5432/dbname
```

Or use environment variable:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
# Then in alembic/env.py, read from env
```

## Usage

```bash
# Check current version
alembic current

# Show migration history
alembic history

# Apply all pending migrations
alembic upgrade head

# Apply one migration
alembic upgrade +1

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade 001

# Create new migration
alembic revision -m "add new feature"

# Generate migration from models (requires target_metadata)
alembic revision --autogenerate -m "auto-detected changes"
```

## Example Migrations

### 001_initial_schema.py

Creates `users` table with:
- Auto-incrementing ID
- Unique email with index
- Username
- Timestamps

### 002_add_orders_table.py

Creates `orders` table with:
- Foreign key to users
- Indexes on user_id and status
- Cascade delete

## Testing

```bash
# Start PostgreSQL (Docker)
docker run -d --name postgres-test \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=migration_example \
  -p 5432:5432 \
  postgres:15

# Apply migrations
alembic upgrade head

# Verify
psql postgresql://postgres:postgres@localhost:5432/migration_example -c "\dt"

# Test rollback
alembic downgrade base
alembic upgrade head

# Cleanup
docker stop postgres-test
docker rm postgres-test
```

## Structure

```
alembic_migrations/
├── alembic.ini              # Configuration file
├── alembic/
│   ├── env.py               # Runtime environment
│   ├── script.py.mako       # Migration template
│   └── versions/
│       ├── 001_initial_schema.py
│       └── 002_add_orders_table.py
└── README.md
```

## Integration with Application

```python
# app.py
from sqlalchemy import create_engine
from alembic.config import Config
from alembic import command

def run_migrations():
    """Apply migrations programmatically"""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

if __name__ == "__main__":
    run_migrations()
    # Start application
```

## Best Practices

1. **One logical change per migration** - easier to understand and rollback
2. **Test migrations locally** - always test upgrade and downgrade
3. **Use transactions** - wrap operations in BEGIN/COMMIT when possible
4. **Avoid data migrations in same file as schema** - separate concerns
5. **Document complex migrations** - add comments explaining why

## Common Issues

**Import errors**: Ensure target_metadata is properly configured in `env.py`

**Database connection fails**: Check DATABASE_URL and network connectivity

**Migration conflict**: Use `alembic merge` to combine branches

**Can't rollback**: Some operations are irreversible (e.g., dropping columns with data)
