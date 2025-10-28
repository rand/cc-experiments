# Docker Migration Testing Environment

Complete Docker environment for testing PostgreSQL migrations safely.

## Quick Start

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
docker-compose ps

# Run migrations with Flyway
docker-compose up flyway

# Verify schema
docker-compose exec postgres psql -U postgres -d migration_test -c "\dt"

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## Services

### PostgreSQL (postgres)

- **Image**: postgres:15-alpine
- **Port**: 5432
- **Database**: migration_test
- **User**: postgres
- **Password**: postgres

**Connect**:
```bash
# From host
psql postgresql://postgres:postgres@localhost:5432/migration_test

# From container
docker-compose exec postgres psql -U postgres -d migration_test
```

### Flyway (flyway)

- **Image**: flyway/flyway:latest
- **Command**: migrate
- **Migrations**: Loaded from `../sql/safe_migrations/`

**Run migrations**:
```bash
docker-compose up flyway
```

**Check migration status**:
```bash
docker-compose run flyway info
```

**Validate migrations**:
```bash
docker-compose run flyway validate
```

### pgAdmin (pgadmin) - Optional

- **Image**: dpage/pgadmin4:latest
- **Port**: 5050
- **Email**: admin@example.com
- **Password**: admin
- **Profile**: with-pgadmin

**Enable pgAdmin**:
```bash
docker-compose --profile with-pgadmin up -d
```

**Access**: Open http://localhost:5050

**Add server in pgAdmin**:
- Host: postgres
- Port: 5432
- Database: migration_test
- Username: postgres
- Password: postgres

## Testing Different Migration Tools

### Flyway (included)

```bash
# Apply migrations
docker-compose up flyway

# Show migration history
docker-compose run flyway info

# Validate
docker-compose run flyway validate
```

### golang-migrate

```bash
# Install golang-migrate
go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest

# Apply migrations
migrate -database "postgres://postgres:postgres@localhost:5432/migration_test?sslmode=disable" \
  -path ../sql/safe_migrations up

# Rollback
migrate -database "postgres://postgres:postgres@localhost:5432/migration_test?sslmode=disable" \
  -path ../sql/safe_migrations down 1
```

### dbmate

```bash
# Install dbmate
brew install dbmate

# Apply migrations
export DATABASE_URL="postgres://postgres:postgres@localhost:5432/migration_test?sslmode=disable"
dbmate -d ../sql/safe_migrations up

# Rollback
dbmate -d ../sql/safe_migrations down
```

### Alembic

```bash
# Install alembic
pip install alembic psycopg2-binary

# Configure alembic.ini
# sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/migration_test

# Apply migrations
cd ../python/alembic_migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Workflows

### Test Safe Migrations

```bash
# Start database
docker-compose up -d postgres

# Apply safe migrations
docker-compose up flyway

# Verify schema
docker-compose exec postgres psql -U postgres -d migration_test -c "
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public';
"

# Check indexes
docker-compose exec postgres psql -U postgres -d migration_test -c "
  SELECT indexname, indexdef FROM pg_indexes
  WHERE schemaname = 'public';
"

# Clean up
docker-compose down -v
```

### Test Migration Rollback

```bash
# Start database
docker-compose up -d postgres

# Apply migrations
docker-compose up flyway

# Create backup
docker-compose exec postgres pg_dump -U postgres migration_test > backup.sql

# Test rollback (manual) - destructive operation for testing migration reversibility
docker-compose exec postgres psql -U postgres -d migration_test -c "
  DROP TABLE IF EXISTS orders CASCADE;
  DROP TABLE IF EXISTS users CASCADE;
"

# Restore from backup
cat backup.sql | docker-compose exec -T postgres psql -U postgres -d migration_test

# Clean up
rm backup.sql
docker-compose down -v
```

### Load Production Data Dump

```bash
# Start database
docker-compose up -d postgres

# Load production dump
cat production_dump.sql | docker-compose exec -T postgres psql -U postgres -d migration_test

# Or for binary dumps
docker-compose exec -T postgres pg_restore -U postgres -d migration_test < production.dump

# Apply migrations
docker-compose up flyway

# Verify
docker-compose exec postgres psql -U postgres -d migration_test -c "SELECT COUNT(*) FROM users;"
```

### Performance Testing

```bash
# Start database
docker-compose up -d postgres

# Generate test data
docker-compose exec postgres psql -U postgres -d migration_test -c "
  CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, email VARCHAR(255));
  INSERT INTO users (email)
  SELECT 'user' || i || '@example.com'
  FROM generate_series(1, 1000000) AS i;
"

# Test migration performance
time docker-compose exec postgres psql -U postgres -d migration_test -c "
  CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
"

# Clean up
docker-compose down -v
```

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# PostgreSQL only
docker-compose logs -f postgres

# Flyway only
docker-compose logs flyway
```

### Database Statistics

```bash
# Table sizes
docker-compose exec postgres psql -U postgres -d migration_test -c "
  SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Index sizes
docker-compose exec postgres psql -U postgres -d migration_test -c "
  SELECT
    indexname,
    pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) AS size
  FROM pg_indexes
  WHERE schemaname = 'public'
  ORDER BY pg_relation_size(schemaname||'.'||indexname) DESC;
"

# Active connections
docker-compose exec postgres psql -U postgres -d migration_test -c "
  SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
"
```

## Troubleshooting

**PostgreSQL won't start**:
```bash
# Check logs
docker-compose logs postgres

# Remove volumes and retry
docker-compose down -v
docker-compose up -d postgres
```

**Flyway migration fails**:
```bash
# Check migration history
docker-compose run flyway info

# Repair (use with caution)
docker-compose run flyway repair

# Or clean and restart
docker-compose down -v
docker-compose up -d postgres
docker-compose up flyway
```

**Port 5432 already in use**:
```bash
# Change port in docker-compose.yml
ports:
  - "5433:5432"  # Use 5433 on host

# Then connect with
psql postgresql://postgres:postgres@localhost:5433/migration_test
```

**Cannot connect from host**:
```bash
# Ensure container is running
docker-compose ps

# Check firewall
sudo ufw allow 5432/tcp

# Verify network
docker-compose exec postgres pg_isready -U postgres
```

## Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Remove everything
docker-compose down -v --rmi all --remove-orphans
```

## Integration with CI/CD

### GitHub Actions

```yaml
name: Test Migrations

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: migration_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Run Flyway migrations
        uses: docker://flyway/flyway:latest
        with:
          args: migrate
        env:
          FLYWAY_URL: jdbc:postgresql://postgres:5432/migration_test
          FLYWAY_USER: postgres
          FLYWAY_PASSWORD: postgres

      - name: Verify schema
        run: |
          psql postgresql://postgres:postgres@localhost:5432/migration_test -c "\dt"
```

## Best Practices

1. **Always use volumes** for data persistence during development
2. **Clean up after testing** with `docker-compose down -v`
3. **Test rollback** before applying to production
4. **Monitor logs** during migration application
5. **Use healthchecks** to ensure database is ready
6. **Version control docker-compose.yml** with your migrations

## Resources

- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Flyway Docker Image](https://hub.docker.com/r/flyway/flyway)
- [pgAdmin Docker Image](https://hub.docker.com/r/dpage/pgadmin4)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
