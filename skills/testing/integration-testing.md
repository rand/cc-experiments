---
name: testing-integration-testing
description: Test interactions between multiple components or services
---



# Integration Testing

## When to Use This Skill

Use this skill when you need to:
- Test interactions between multiple components or services
- Verify database operations (queries, transactions, migrations)
- Test API endpoints with real HTTP requests
- Use test containers for isolated infrastructure
- Implement transaction rollback patterns for clean test state
- Test message queues, caches, and external service integrations
- Balance integration test coverage with speed and reliability

**ACTIVATE THIS SKILL**: When testing component interactions, databases, APIs, or external services

## Core Concepts

### Integration Tests vs Unit Tests

**Unit Tests**:
- Single component in isolation
- Fast (< 100ms)
- Mock all dependencies
- Run thousands per second

**Integration Tests**:
- Multiple components together
- Slower (100ms - 5s)
- Real infrastructure (DB, cache, etc.)
- Run hundreds per minute
- Higher confidence in real behavior

### Test Database Strategies

**Strategy 1: In-Memory Database** (SQLite)
```python
# Python (pytest)
import pytest
from sqlalchemy import create_engine
from myapp.models import Base

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_user(db_session):
    user = User(name="Alice", email="alice@example.com")
    db_session.add(user)
    db_session.commit()

    retrieved = db_session.query(User).filter_by(email="alice@example.com").first()
    assert retrieved.name == "Alice"
```

**Strategy 2: Test Containers** (Docker)
```python
# Python (testcontainers)
from testcontainers.postgres import PostgresContainer
import pytest

@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:16") as postgres:
        yield postgres

@pytest.fixture
def db_connection(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    connection = engine.connect()
    yield connection
    connection.close()

def test_user_repository(db_connection):
    repo = UserRepository(db_connection)
    user = repo.create(name="Alice", email="alice@example.com")
    assert repo.find_by_id(user.id).name == "Alice"
```

```typescript
// TypeScript (testcontainers)
import { PostgreSqlContainer } from '@testcontainers/postgresql';
import { DataSource } from 'typeorm';

describe('UserRepository', () => {
  let container: PostgreSqlContainer;
  let dataSource: DataSource;

  beforeAll(async () => {
    container = await new PostgreSqlContainer('postgres:16').start();
    dataSource = new DataSource({
      type: 'postgres',
      host: container.getHost(),
      port: container.getPort(),
      username: container.getUsername(),
      password: container.getPassword(),
      database: container.getDatabase(),
      entities: [User],
      synchronize: true,
    });
    await dataSource.initialize();
  });

  afterAll(async () => {
    await dataSource.destroy();
    await container.stop();
  });

  it('creates and retrieves user', async () => {
    const repo = dataSource.getRepository(User);
    const user = await repo.save({ name: 'Alice', email: 'alice@example.com' });
    const retrieved = await repo.findOneBy({ id: user.id });
    expect(retrieved.name).toBe('Alice');
  });
});
```

**Strategy 3: Transaction Rollback**
```python
# Python (pytest)
@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

# Each test gets clean state via rollback
def test_create_user(db_session):
    user = User(name="Alice")
    db_session.add(user)
    db_session.commit()
    assert db_session.query(User).count() == 1
```

```go
// Go
func TestUserRepository(t *testing.T) {
    db := setupTestDB(t)
    tx := db.Begin()
    defer tx.Rollback()

    repo := NewUserRepository(tx)
    user, err := repo.Create("Alice", "alice@example.com")
    require.NoError(t, err)

    retrieved, err := repo.FindByID(user.ID)
    require.NoError(t, err)
    assert.Equal(t, "Alice", retrieved.Name)
}
```

## Patterns

### API Integration Testing

```python
# Python (FastAPI with TestClient)
from fastapi.testclient import TestClient
from myapp.main import app

client = TestClient(app)

def test_create_user_endpoint():
    # Arrange
    payload = {
        "name": "Alice",
        "email": "alice@example.com"
    }

    # Act
    response = client.post("/users", json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice"
    assert "id" in data

def test_get_user_endpoint(db_session):
    # Arrange: Create user in DB
    user = User(name="Alice", email="alice@example.com")
    db_session.add(user)
    db_session.commit()

    # Act
    response = client.get(f"/users/{user.id}")

    # Assert
    assert response.status_code == 200
    assert response.json()["name"] == "Alice"

def test_authentication_required():
    response = client.get("/protected-resource")
    assert response.status_code == 401

    response = client.get(
        "/protected-resource",
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 200
```

```typescript
// TypeScript (Express + Supertest)
import request from 'supertest';
import { app } from './app';
import { setupTestDB, teardownTestDB } from './test-helpers';

describe('User API', () => {
  beforeAll(async () => {
    await setupTestDB();
  });

  afterAll(async () => {
    await teardownTestDB();
  });

  it('creates user via POST /users', async () => {
    const response = await request(app)
      .post('/users')
      .send({ name: 'Alice', email: 'alice@example.com' })
      .expect(201);

    expect(response.body.name).toBe('Alice');
    expect(response.body.id).toBeDefined();
  });

  it('retrieves user via GET /users/:id', async () => {
    const createRes = await request(app)
      .post('/users')
      .send({ name: 'Bob', email: 'bob@example.com' });

    const userId = createRes.body.id;

    const response = await request(app)
      .get(`/users/${userId}`)
      .expect(200);

    expect(response.body.name).toBe('Bob');
  });
});
```

### Testing Database Migrations

```python
# Python (Alembic)
import pytest
from alembic import command
from alembic.config import Config

def test_migrations_run_successfully():
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", "sqlite:///:memory:")

    # Run all migrations
    command.upgrade(config, "head")

    # Verify schema exists
    engine = create_engine("sqlite:///:memory:")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "users" in tables
    assert "posts" in tables

def test_migration_rollback():
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", "sqlite:///:memory:")

    # Upgrade to latest
    command.upgrade(config, "head")

    # Downgrade one version
    command.downgrade(config, "-1")

    # Verify rollback worked
    # ... assertions ...
```

### Testing with Redis/Cache

```python
# Python (fakeredis)
import pytest
from fakeredis import FakeRedis

@pytest.fixture
def redis_client():
    return FakeRedis()

def test_cache_set_get(redis_client):
    cache = CacheService(redis_client)
    cache.set("key", "value", ttl=60)
    assert cache.get("key") == "value"

def test_cache_expiration(redis_client):
    cache = CacheService(redis_client)
    cache.set("key", "value", ttl=0)
    time.sleep(0.1)
    assert cache.get("key") is None
```

```typescript
// TypeScript (ioredis-mock)
import RedisMock from 'ioredis-mock';

describe('CacheService', () => {
  let redis: RedisMock;
  let cache: CacheService;

  beforeEach(() => {
    redis = new RedisMock();
    cache = new CacheService(redis);
  });

  it('sets and gets values', async () => {
    await cache.set('key', 'value', 60);
    const result = await cache.get('key');
    expect(result).toBe('value');
  });
});
```

### Testing Message Queues

```python
# Python (testing with in-memory queue)
import pytest
from queue import Queue

class InMemoryQueue:
    def __init__(self):
        self.queue = Queue()

    def publish(self, message):
        self.queue.put(message)

    def consume(self, timeout=1):
        return self.queue.get(timeout=timeout)

@pytest.fixture
def message_queue():
    return InMemoryQueue()

def test_order_processing(message_queue):
    # Arrange
    order_service = OrderService(message_queue)
    payment_processor = PaymentProcessor(message_queue)

    # Act
    order_service.create_order(user_id=1, items=["item1"])

    # Assert: Message published
    message = message_queue.consume(timeout=1)
    assert message["type"] == "order_created"
    assert message["user_id"] == 1

    # Act: Process payment
    payment_processor.process(message)

    # Assert: Payment message published
    payment_message = message_queue.consume(timeout=1)
    assert payment_message["type"] == "payment_processed"
```

### Testing External Service Integrations

```python
# Python (using requests-mock)
import pytest
import requests_mock

def test_weather_api_integration():
    with requests_mock.Mocker() as m:
        # Mock external API
        m.get(
            "https://api.weather.com/forecast",
            json={"temperature": 72, "condition": "sunny"}
        )

        # Test service that calls API
        service = WeatherService()
        forecast = service.get_forecast(zip_code="94102")

        assert forecast.temperature == 72
        assert forecast.condition == "sunny"

def test_api_timeout_handling():
    with requests_mock.Mocker() as m:
        m.get("https://api.weather.com/forecast", exc=requests.Timeout)

        service = WeatherService()
        with pytest.raises(WeatherServiceError, match="timeout"):
            service.get_forecast(zip_code="94102")
```

```typescript
// TypeScript (MSW - Mock Service Worker)
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('https://api.weather.com/forecast', (req, res, ctx) => {
    return res(ctx.json({ temperature: 72, condition: 'sunny' }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('WeatherService', () => {
  it('fetches forecast from API', async () => {
    const service = new WeatherService();
    const forecast = await service.getForecast('94102');

    expect(forecast.temperature).toBe(72);
    expect(forecast.condition).toBe('sunny');
  });

  it('handles API errors', async () => {
    server.use(
      rest.get('https://api.weather.com/forecast', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    const service = new WeatherService();
    await expect(service.getForecast('94102')).rejects.toThrow();
  });
});
```

## Examples by Language

### Python (pytest + SQLAlchemy)

```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:16") as container:
        yield container

@pytest.fixture(scope="session")
def engine(postgres):
    engine = create_engine(postgres.get_connection_url())
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

# test_user_repository.py
def test_create_and_find_user(db_session):
    repo = UserRepository(db_session)

    user = repo.create(name="Alice", email="alice@example.com")
    assert user.id is not None

    found = repo.find_by_email("alice@example.com")
    assert found.name == "Alice"

def test_user_unique_email_constraint(db_session):
    repo = UserRepository(db_session)

    repo.create(name="Alice", email="alice@example.com")

    with pytest.raises(IntegrityError):
        repo.create(name="Bob", email="alice@example.com")
```

### Go (testcontainers-go)

```go
// integration_test.go
package repository_test

import (
    "context"
    "testing"

    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
    "github.com/testcontainers/testcontainers-go"
    "github.com/testcontainers/testcontainers-go/wait"
)

func setupPostgres(t *testing.T) *sql.DB {
    ctx := context.Background()

    req := testcontainers.ContainerRequest{
        Image:        "postgres:16",
        ExposedPorts: []string{"5432/tcp"},
        Env: map[string]string{
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_DB":       "testdb",
        },
        WaitingFor: wait.ForLog("database system is ready"),
    }

    container, err := testcontainers.GenericContainer(ctx, testcontainers.GenericContainerRequest{
        ContainerRequest: req,
        Started:          true,
    })
    require.NoError(t, err)

    t.Cleanup(func() {
        container.Terminate(ctx)
    })

    host, _ := container.Host(ctx)
    port, _ := container.MappedPort(ctx, "5432")

    dsn := fmt.Sprintf("host=%s port=%s user=postgres password=test dbname=testdb sslmode=disable",
        host, port.Port())

    db, err := sql.Open("postgres", dsn)
    require.NoError(t, err)

    return db
}

func TestUserRepository(t *testing.T) {
    db := setupPostgres(t)
    defer db.Close()

    repo := NewUserRepository(db)

    user, err := repo.Create("Alice", "alice@example.com")
    require.NoError(t, err)
    assert.NotZero(t, user.ID)

    found, err := repo.FindByEmail("alice@example.com")
    require.NoError(t, err)
    assert.Equal(t, "Alice", found.Name)
}
```

### TypeScript (Vitest + TypeORM)

```typescript
// test-setup.ts
import { DataSource } from 'typeorm';
import { PostgreSqlContainer } from '@testcontainers/postgresql';

export async function setupTestDB(): Promise<DataSource> {
  const container = await new PostgreSqlContainer('postgres:16').start();

  const dataSource = new DataSource({
    type: 'postgres',
    host: container.getHost(),
    port: container.getPort(),
    username: container.getUsername(),
    password: container.getPassword(),
    database: container.getDatabase(),
    entities: [User, Post],
    synchronize: true,
  });

  await dataSource.initialize();

  return dataSource;
}

// user-repository.test.ts
describe('UserRepository', () => {
  let dataSource: DataSource;
  let repository: Repository<User>;

  beforeAll(async () => {
    dataSource = await setupTestDB();
    repository = dataSource.getRepository(User);
  });

  afterAll(async () => {
    await dataSource.destroy();
  });

  afterEach(async () => {
    await repository.clear();
  });

  it('creates and retrieves user', async () => {
    const user = await repository.save({
      name: 'Alice',
      email: 'alice@example.com'
    });

    const found = await repository.findOneBy({ email: 'alice@example.com' });
    expect(found?.name).toBe('Alice');
  });
});
```

## Checklist

**Before Writing Integration Tests**:
- [ ] Identify components to test together
- [ ] Choose test database strategy (in-memory, containers, rollback)
- [ ] Plan test data setup and teardown
- [ ] Decide on test isolation level (per-test, per-suite)

**Setting Up Infrastructure**:
- [ ] Use test containers for real infrastructure
- [ ] Configure test database with migrations
- [ ] Set up test API server/client
- [ ] Mock external services (or use contract tests)

**Writing Tests**:
- [ ] Clean state before each test (rollback or cleanup)
- [ ] Test realistic workflows (multiple operations)
- [ ] Verify data persistence across operations
- [ ] Test error conditions and rollback scenarios
- [ ] Keep tests independent (no order dependencies)

**Performance**:
- [ ] Tests complete in reasonable time (< 5s each)
- [ ] Use transactions for faster rollback
- [ ] Share expensive resources (DB, containers) across tests
- [ ] Parallelize when possible

**After Writing Tests**:
- [ ] Tests pass consistently (no flakiness)
- [ ] Tests fail when integration breaks
- [ ] Clean shutdown of resources (no port conflicts)
- [ ] Tests run in CI/CD pipeline

## Anti-Patterns

```
❌ NEVER: Share state between tests without cleanup
   → Flaky tests, order dependencies

❌ NEVER: Use production database for tests
   → Data corruption, slow tests

❌ NEVER: Skip transaction rollback in teardown
   → Polluted database state

❌ NEVER: Test too many layers at once
   → Slow, hard to debug failures

❌ NEVER: Ignore test performance
   → Slow feedback loop, developers skip tests

❌ NEVER: Mock everything in integration tests
   → Defeats purpose of integration testing

❌ NEVER: Leave containers running after tests
   → Resource leaks, port conflicts
```

## Level 3: Resources

### Comprehensive Reference
See `/resources/REFERENCE.md` for in-depth coverage:
- Testing pyramid and integration test positioning (958 lines)
- Test scopes and boundaries (narrow, medium, broad)
- Test doubles (dummies, stubs, fakes, mocks, spies) with detailed examples
- Contract testing with Pact and Spring Cloud Contract
- Service virtualization with WireMock and MockServer
- Database testing strategies (in-memory, Docker, transactions, migrations)
- External service testing (HTTP APIs, GraphQL, message queues)
- API integration testing patterns (REST, authentication, performance)
- Message queue testing (RabbitMQ, Kafka, event-driven systems)
- CI/CD integration patterns (GitHub Actions, GitLab CI, Docker Compose)
- Performance and load testing (response times, Locust, concurrency)
- Common anti-patterns and solutions (12 detailed patterns)
- Best practices (10 comprehensive guidelines)

### Executable Scripts

**`/resources/scripts/run_integration_tests.sh`**
Orchestrates integration tests with automatic setup/teardown:
- Starts Docker services (PostgreSQL, Redis, RabbitMQ, etc.)
- Waits for health checks
- Runs tests with multiple frameworks (pytest, vitest, jest, go)
- Generates reports with coverage
- Cleans up infrastructure
- Supports parallel execution, custom patterns, timeouts
- Usage: `./run_integration_tests.sh --coverage --parallel`

**`/resources/scripts/analyze_test_coverage.py`**
Analyzes integration test coverage across multiple dimensions:
- Discovers test files and categorizes by type
- Identifies tested vs untested components (endpoints, models, services, repositories)
- Analyzes integration types (database, cache, queue, email, storage, API)
- Generates actionable recommendations prioritized by impact
- Outputs text or JSON reports
- Usage: `./analyze_test_coverage.py --test-dir tests/integration --src-dir src`

**`/resources/scripts/generate_test_report.py`**
Generates comprehensive HTML/JSON reports from test results:
- Parses JUnit XML and pytest JSON formats
- Includes test execution details, durations, failures
- Visualizes coverage data with progress bars
- Provides interactive HTML reports with test filtering
- Outputs JSON for CI/CD pipeline integration
- Usage: `./generate_test_report.py --input results.xml --coverage coverage.xml --output report.html`

### Runnable Examples

**Python Examples** (`/resources/examples/python/`):
- `test_api_integration.py`: FastAPI testing with TestClient, PostgreSQL testcontainers, full CRUD lifecycle, authentication, performance tests (300+ lines)
- `test_database_integration.py`: Repository pattern testing, transactions, relationships, cascade deletes, constraint testing (400+ lines)

**TypeScript Examples** (`/resources/examples/typescript/`):
- `test_api_integration.test.ts`: Express API testing with Supertest, PostgreSQL Pool, CRUD operations, pagination, performance tests (350+ lines)

**Docker Infrastructure** (`/resources/examples/docker/`):
- `docker-compose-test.yml`: Complete test infrastructure with PostgreSQL, Redis, RabbitMQ, MongoDB, MySQL, MinIO, Elasticsearch, Mailhog, WireMock - all with health checks

All scripts are production-ready with:
- Comprehensive --help documentation
- JSON output support for CI/CD
- Error handling and exit codes
- Verbose logging options
- Cross-platform compatibility

## Related Skills

**Foundation**:
- `unit-testing-patterns.md` - Testing individual components
- `test-driven-development.md` - TDD workflow

**Database Testing**:
- `database-migrations.md` - Migration testing patterns
- `database-testing-patterns.md` - Advanced DB testing

**API Testing**:
- `e2e-testing.md` - Full system testing
- `api-testing.md` - REST/GraphQL testing patterns

**Infrastructure**:
- `test-containers.md` - Docker container testing
- `testing-microservices.md` - Service integration testing

**Tools**:
- Python: pytest, testcontainers, requests-mock
- TypeScript: Vitest, Supertest, MSW, testcontainers
- Go: testify, testcontainers-go
- Rust: sqlx with test macros
