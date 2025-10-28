# Integration Testing Reference

## Table of Contents
1. [Testing Pyramid and Integration Testing](#testing-pyramid-and-integration-testing)
2. [Test Scopes and Boundaries](#test-scopes-and-boundaries)
3. [Test Doubles](#test-doubles)
4. [Contract Testing](#contract-testing)
5. [Service Virtualization](#service-virtualization)
6. [Database Testing Strategies](#database-testing-strategies)
7. [External Service Testing](#external-service-testing)
8. [API Integration Testing](#api-integration-testing)
9. [Message Queue Testing](#message-queue-testing)
10. [CI/CD Integration Patterns](#cicd-integration-patterns)
11. [Performance and Load Testing](#performance-and-load-testing)
12. [Common Anti-Patterns](#common-anti-patterns)
13. [Best Practices](#best-practices)

---

## Testing Pyramid and Integration Testing

### The Testing Pyramid

```
       /\
      /  \     E2E Tests (Few)
     /____\
    /      \   Integration Tests (Some)
   /________\
  /          \ Unit Tests (Many)
 /____________\
```

**Principle**: Write tests at the lowest level possible that gives you confidence.

### Integration Test Position

Integration tests sit between unit tests and E2E tests:

- **Unit Tests**: Test individual functions/methods in isolation
- **Integration Tests**: Test interactions between components/modules/services
- **E2E Tests**: Test complete user workflows through the entire system

### When to Use Integration Tests

**Use integration tests when**:
- Testing interactions between your code and external systems (databases, APIs, message queues)
- Verifying that multiple components work together correctly
- Testing adapter/integration layer logic
- Validating data transformations across boundaries
- Testing infrastructure configuration (connection pools, retry logic, circuit breakers)

**Don't use integration tests when**:
- Pure business logic can be tested in isolation (use unit tests)
- Testing complete user workflows (use E2E tests)
- Testing UI rendering (use component tests)

### Cost-Benefit Analysis

**Integration tests are**:
- **Slower** than unit tests (seconds vs milliseconds)
- **More complex** to set up (require test infrastructure)
- **More brittle** (more things can break)
- **Higher value** than unit tests (catch integration bugs)
- **Lower cost** than E2E tests (faster, more stable)

---

## Test Scopes and Boundaries

### Narrow Integration Tests

Test interactions with a single external system in isolation.

**Example**: Testing database repository layer
```python
# Test your repository code against a real database
def test_user_repository_save_and_find(test_db):
    repo = UserRepository(test_db)
    user = User(id=1, name="Alice", email="alice@example.com")

    repo.save(user)
    found = repo.find_by_id(1)

    assert found.name == "Alice"
    assert found.email == "alice@example.com"
```

**Characteristics**:
- Fast (< 100ms typical)
- Tests single integration point
- Easy to debug
- Good for adapter/port testing

### Medium Integration Tests

Test interactions between 2-3 internal components with minimal external dependencies.

**Example**: Testing service layer with repository
```python
def test_user_service_create_user(test_db):
    repo = UserRepository(test_db)
    service = UserService(repo, email_validator=RealEmailValidator())

    result = service.create_user(
        name="Bob",
        email="bob@example.com"
    )

    assert result.success
    assert repo.find_by_email("bob@example.com") is not None
```

**Characteristics**:
- Moderate speed (100-500ms)
- Tests multiple components
- May use real external dependencies
- Good for workflow testing

### Broad Integration Tests

Test complete subsystems with multiple external dependencies.

**Example**: Testing API endpoint with database and cache
```python
def test_api_get_user_caches_result(test_client, test_db, test_cache):
    # Create user
    response = test_client.post("/users", json={
        "name": "Charlie",
        "email": "charlie@example.com"
    })
    user_id = response.json()["id"]

    # First request hits database
    response1 = test_client.get(f"/users/{user_id}")
    assert response1.status_code == 200
    assert test_db.query_count == 1

    # Second request hits cache
    response2 = test_client.get(f"/users/{user_id}")
    assert response2.status_code == 200
    assert test_db.query_count == 1  # No additional query
    assert test_cache.hit_count == 1
```

**Characteristics**:
- Slower (500ms-5s)
- Tests complete subsystems
- Uses multiple real dependencies
- Good for smoke testing critical paths

### Choosing Test Scope

**Decision tree**:
```
Can I test this with unit tests? → Yes → Use unit tests
    ↓ No
Does it involve one external system? → Yes → Narrow integration test
    ↓ No
Does it involve 2-3 components? → Yes → Medium integration test
    ↓ No
Does it involve complete subsystem? → Yes → Broad integration test
    ↓ No
Consider E2E test instead
```

---

## Test Doubles

Test doubles are fake implementations used to replace real dependencies in tests.

### Types of Test Doubles

#### 1. Dummy
Objects passed around but never used (satisfy parameter requirements).

```python
class DummyLogger:
    def log(self, message: str) -> None:
        pass  # Does nothing

def test_user_service():
    service = UserService(logger=DummyLogger())
    # Logger is required but not used in this test
```

**When to use**: When you need to satisfy interface requirements but don't care about the behavior.

#### 2. Stub
Returns predefined responses to calls.

```python
class StubUserRepository:
    def find_by_id(self, user_id: int) -> User:
        return User(id=user_id, name="Test User", email="test@example.com")

def test_user_service_find():
    repo = StubUserRepository()
    service = UserService(repo)

    user = service.get_user(1)
    assert user.name == "Test User"
```

**When to use**: When you need consistent, predictable responses for testing specific scenarios.

#### 3. Fake
Working implementation with shortcuts (in-memory database, simplified logic).

```python
class FakeUserRepository:
    def __init__(self):
        self.users = {}
        self.next_id = 1

    def save(self, user: User) -> User:
        if user.id is None:
            user.id = self.next_id
            self.next_id += 1
        self.users[user.id] = user
        return user

    def find_by_id(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)

def test_user_service_workflow():
    repo = FakeUserRepository()
    service = UserService(repo)

    user1 = service.create_user("Alice", "alice@example.com")
    user2 = service.get_user(user1.id)

    assert user1.id == user2.id
    assert user1.name == user2.name
```

**When to use**: When you need realistic behavior without external dependencies. Great for complex workflows.

#### 4. Mock
Records calls and verifies interactions.

```python
from unittest.mock import Mock

def test_user_service_sends_welcome_email():
    email_service = Mock()
    repo = FakeUserRepository()
    service = UserService(repo, email_service)

    service.create_user("Dave", "dave@example.com")

    email_service.send_welcome_email.assert_called_once()
    call_args = email_service.send_welcome_email.call_args
    assert call_args[0][0] == "dave@example.com"
```

**When to use**: When you need to verify that specific interactions occurred.

#### 5. Spy
Records information about calls while delegating to real implementation.

```python
class SpyEmailService:
    def __init__(self, real_service):
        self.real_service = real_service
        self.calls = []

    def send_welcome_email(self, email: str) -> None:
        self.calls.append(("send_welcome_email", email))
        self.real_service.send_welcome_email(email)

def test_user_service_integration():
    email_spy = SpyEmailService(RealEmailService())
    repo = RealUserRepository(test_db)
    service = UserService(repo, email_spy)

    service.create_user("Eve", "eve@example.com")

    assert len(email_spy.calls) == 1
    assert email_spy.calls[0][1] == "eve@example.com"
    # Also verifies real email was sent
```

**When to use**: When you need to verify interactions while still using real implementations.

### Test Double Strategy

**In integration tests**:
- Use **real implementations** for the component under test
- Use **test doubles** for external dependencies that are:
  - Slow (third-party APIs)
  - Unreliable (external services)
  - Costly (payment processors)
  - Difficult to set up (legacy systems)

**Example**:
```python
# Testing payment service integration
def test_payment_service_charges_card(test_db):
    # Real database (what we're testing)
    repo = PaymentRepository(test_db)

    # Fake payment gateway (external dependency)
    gateway = FakePaymentGateway()

    # Real email service with spy (to verify interactions)
    email_spy = SpyEmailService(RealEmailService())

    service = PaymentService(repo, gateway, email_spy)

    result = service.charge_customer(
        customer_id=123,
        amount=1000,
        currency="USD"
    )

    assert result.success
    assert repo.find_transaction(result.transaction_id) is not None
    assert gateway.charged_amount == 1000
    assert len(email_spy.calls) == 1
```

---

## Contract Testing

Contract testing verifies that services can communicate correctly without testing them together.

### Consumer-Driven Contracts

**Principle**: Consumers define the contracts they need from providers.

### Pact Framework

**Consumer side** (defines expectations):
```python
import pytest
from pact import Consumer, Provider

pact = Consumer('UserService').has_pact_with(Provider('AuthService'))

def test_auth_service_validates_token():
    expected = {
        'user_id': 123,
        'username': 'alice',
        'roles': ['user', 'admin']
    }

    (pact
     .given('token abc123 is valid')
     .upon_receiving('a request to validate token')
     .with_request('post', '/auth/validate', body={'token': 'abc123'})
     .will_respond_with(200, body=expected))

    with pact:
        # Make real HTTP request
        client = AuthClient(pact.uri)
        result = client.validate_token('abc123')

        assert result['user_id'] == 123
        assert 'admin' in result['roles']
```

**Provider side** (verifies it can fulfill contracts):
```python
from pact import Verifier

def test_auth_service_honors_contracts():
    verifier = Verifier(provider='AuthService', provider_base_url='http://localhost:8080')

    # Point to consumer's contract files
    verifier.verify_pacts('/path/to/pacts/userservice-authservice.json')
```

### Contract Testing Benefits

**Advantages**:
- Tests services independently
- Faster than integration tests
- Clear API contracts
- Catches breaking changes early
- Enables parallel development

**Disadvantages**:
- Requires coordination between teams
- Additional tooling complexity
- May miss integration issues
- Requires contract maintenance

### When to Use Contract Testing

**Use contract testing when**:
- Multiple teams own different services
- Services are deployed independently
- You want to test API compatibility
- Integration tests are too slow/complex

**Example workflow**:
```
1. Consumer defines contract (what it needs)
2. Consumer tests verify contract
3. Contract published to broker
4. Provider retrieves contract
5. Provider tests verify it satisfies contract
6. If provider changes, contract tests fail
7. Teams discuss breaking changes
```

### Spring Cloud Contract

For Spring Boot applications:

```java
// Contract definition (Groovy DSL)
Contract.make {
    request {
        method 'GET'
        url '/users/123'
    }
    response {
        status 200
        body([
            id: 123,
            name: 'Alice',
            email: 'alice@example.com'
        ])
        headers {
            contentType('application/json')
        }
    }
}
```

```java
// Auto-generated test
@Test
public void validate_get_user() {
    given()
        .when()
            .get("/users/123")
        .then()
            .statusCode(200)
            .body("id", equalTo(123))
            .body("name", equalTo("Alice"));
}
```

---

## Service Virtualization

Service virtualization creates simulated versions of dependent services.

### WireMock

**Setup**:
```python
from wiremock import WireMock

def test_api_client_with_wiremock():
    wiremock = WireMock(host='localhost', port=8080)

    # Record responses
    wiremock.stub_for({
        'request': {
            'method': 'GET',
            'url': '/api/users/123'
        },
        'response': {
            'status': 200,
            'body': '{"id": 123, "name": "Alice"}',
            'headers': {'Content-Type': 'application/json'}
        }
    })

    # Test your client
    client = ApiClient(base_url='http://localhost:8080')
    user = client.get_user(123)

    assert user['name'] == 'Alice'

    # Verify request was made
    wiremock.verify({
        'method': 'GET',
        'url': '/api/users/123'
    })
```

**Advanced scenarios**:
```python
# Simulate delays
wiremock.stub_for({
    'request': {'method': 'GET', 'url': '/api/slow'},
    'response': {
        'status': 200,
        'fixedDelayMilliseconds': 5000
    }
})

# Simulate failures
wiremock.stub_for({
    'request': {'method': 'POST', 'url': '/api/unstable'},
    'response': {
        'status': 503,
        'statusMessage': 'Service Unavailable'
    }
})

# Stateful behavior
wiremock.stub_for({
    'request': {'method': 'POST', 'url': '/api/counter'},
    'response': {
        'status': 200,
        'body': '{"count": {{request.counter}}}',
        'transformers': ['response-template']
    },
    'scenarioName': 'counter',
    'requiredScenarioState': 'Started',
    'newScenarioState': 'Incremented'
})
```

### MockServer

```typescript
import { mockServer } from 'mockserver-client';

describe('API Integration', () => {
  const mockServerClient = mockServer('localhost', 1080);

  beforeEach(() => {
    mockServerClient
      .mockAnyResponse({
        httpRequest: {
          method: 'GET',
          path: '/api/users/.*'
        },
        httpResponse: {
          statusCode: 200,
          body: JSON.stringify({
            id: 123,
            name: 'Alice'
          })
        },
        times: {
          remainingTimes: 1,
          unlimited: false
        }
      });
  });

  it('should fetch user data', async () => {
    const client = new ApiClient('http://localhost:1080');
    const user = await client.getUser(123);

    expect(user.name).toBe('Alice');
  });
});
```

### Service Virtualization Patterns

#### 1. Record and Replay
Record real service interactions and replay in tests.

```python
# Record mode
wiremock.start_recording(target_url='https://api.production.com')
# ... make real requests ...
wiremock.stop_recording()
wiremock.save_mappings('/path/to/stubs')

# Replay mode
wiremock.load_mappings('/path/to/stubs')
# ... tests use recorded responses ...
```

#### 2. Dynamic Stubs
Generate responses based on request content.

```python
wiremock.stub_for({
    'request': {
        'method': 'POST',
        'url': '/api/users',
        'bodyPatterns': [{'matchesJsonPath': '$.email'}]
    },
    'response': {
        'status': 201,
        'body': '{"id": {{randomValue type="UUID"}}, "email": "{{jsonPath request.body "$.email"}}"}',
        'transformers': ['response-template']
    }
})
```

#### 3. Chaos Engineering
Simulate failures and edge cases.

```python
# Random failures
wiremock.stub_for({
    'request': {'method': 'GET', 'url': '/api/flaky'},
    'response': {
        'status': 200,
        'fault': 'RANDOM_DATA_THEN_CLOSE'
    }
})

# Connection reset
wiremock.stub_for({
    'request': {'method': 'GET', 'url': '/api/unreliable'},
    'response': {
        'fault': 'CONNECTION_RESET_BY_PEER'
    }
})
```

---

## Database Testing Strategies

### In-Memory Databases

**SQLite** (for PostgreSQL/MySQL tests):
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def test_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    engine.dispose()

def test_user_repository(test_db):
    repo = UserRepository(test_db)
    user = User(name="Alice", email="alice@example.com")

    repo.save(user)
    found = repo.find_by_email("alice@example.com")

    assert found.name == "Alice"
```

**Benefits**:
- Fast (microseconds)
- No external dependencies
- Isolated tests

**Limitations**:
- May not match production database exactly
- Missing database-specific features
- Different SQL dialect

### Docker Test Containers

**Testcontainers** (Python):
```python
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine

@pytest.fixture(scope='session')
def postgres_container():
    with PostgresContainer('postgres:15') as postgres:
        yield postgres

@pytest.fixture
def test_db(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.rollback()
    session.close()

def test_user_repository_with_postgres(test_db):
    repo = UserRepository(test_db)
    user = User(name="Bob", email="bob@example.com")

    repo.save(user)

    # Test PostgreSQL-specific features
    users = repo.search_by_name_pattern("B%")
    assert len(users) == 1
```

**Benefits**:
- Real database engine
- Tests production features
- Reproducible environment

**Limitations**:
- Slower (seconds to start)
- Requires Docker
- More complex setup

### Transaction Rollback Pattern

```python
@pytest.fixture
def test_db(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    # Rollback transaction (undo all changes)
    transaction.rollback()
    connection.close()

def test_user_creation(test_db):
    repo = UserRepository(test_db)
    repo.save(User(name="Test", email="test@example.com"))

    assert repo.count() == 1
    # Changes automatically rolled back after test
```

**Benefits**:
- Fast cleanup
- Isolated tests
- No manual cleanup code

### Database Migration Testing

```python
def test_migrations_apply_cleanly(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())

    # Apply all migrations
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option(
        "sqlalchemy.url",
        postgres_container.get_connection_url()
    )
    command.upgrade(alembic_config, "head")

    # Verify schema
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "users" in tables
    assert "orders" in tables

    # Test rollback
    command.downgrade(alembic_config, "-1")
    tables = inspector.get_table_names()
    assert "orders" not in tables
```

### Seeding Test Data

```python
class DatabaseSeeder:
    def __init__(self, session):
        self.session = session

    def seed_users(self, count=10):
        users = [
            User(
                name=f"User {i}",
                email=f"user{i}@example.com",
                created_at=datetime.now() - timedelta(days=i)
            )
            for i in range(count)
        ]
        self.session.add_all(users)
        self.session.commit()
        return users

    def seed_orders(self, user_ids, count_per_user=5):
        orders = []
        for user_id in user_ids:
            for i in range(count_per_user):
                orders.append(Order(
                    user_id=user_id,
                    total=100 + (i * 10),
                    status='completed'
                ))
        self.session.add_all(orders)
        self.session.commit()
        return orders

@pytest.fixture
def seeded_db(test_db):
    seeder = DatabaseSeeder(test_db)
    users = seeder.seed_users(10)
    seeder.seed_orders([u.id for u in users], 5)
    return test_db

def test_order_statistics(seeded_db):
    repo = OrderRepository(seeded_db)

    stats = repo.get_statistics()

    assert stats['total_orders'] == 50
    assert stats['total_revenue'] == 7250
```

---

## External Service Testing

### HTTP API Testing

**Using real API in tests**:
```python
import pytest
import requests

@pytest.fixture
def api_client():
    return requests.Session()

def test_github_api_get_user(api_client):
    response = api_client.get('https://api.github.com/users/octocat')

    assert response.status_code == 200
    data = response.json()
    assert data['login'] == 'octocat'
    assert 'id' in data
```

**Issues with real APIs**:
- Slow
- Rate limited
- May change
- Requires authentication
- Not isolated

**Using test API server**:
```python
from flask import Flask, jsonify
import pytest
from multiprocessing import Process

def create_test_api():
    app = Flask(__name__)

    @app.route('/users/<int:user_id>')
    def get_user(user_id):
        return jsonify({
            'id': user_id,
            'name': f'User {user_id}',
            'email': f'user{user_id}@example.com'
        })

    return app

@pytest.fixture(scope='session')
def test_api_server():
    app = create_test_api()
    process = Process(target=lambda: app.run(port=5555))
    process.start()

    yield 'http://localhost:5555'

    process.terminate()

def test_api_client(test_api_server):
    client = ApiClient(base_url=test_api_server)
    user = client.get_user(123)

    assert user['id'] == 123
    assert user['name'] == 'User 123'
```

### REST API Testing Patterns

```python
class TestUserAPI:
    def test_create_user_returns_201(self, test_client):
        response = test_client.post('/users', json={
            'name': 'Alice',
            'email': 'alice@example.com'
        })

        assert response.status_code == 201
        data = response.json()
        assert 'id' in data
        assert data['name'] == 'Alice'

    def test_create_user_with_duplicate_email_returns_409(self, test_client):
        # Create first user
        test_client.post('/users', json={
            'name': 'Alice',
            'email': 'alice@example.com'
        })

        # Try to create duplicate
        response = test_client.post('/users', json={
            'name': 'Alice2',
            'email': 'alice@example.com'
        })

        assert response.status_code == 409
        assert 'already exists' in response.json()['error']

    def test_get_nonexistent_user_returns_404(self, test_client):
        response = test_client.get('/users/99999')

        assert response.status_code == 404

    def test_update_user(self, test_client):
        # Create user
        create_response = test_client.post('/users', json={
            'name': 'Bob',
            'email': 'bob@example.com'
        })
        user_id = create_response.json()['id']

        # Update user
        update_response = test_client.patch(f'/users/{user_id}', json={
            'name': 'Robert'
        })

        assert update_response.status_code == 200
        assert update_response.json()['name'] == 'Robert'

        # Verify update persisted
        get_response = test_client.get(f'/users/{user_id}')
        assert get_response.json()['name'] == 'Robert'

    def test_delete_user(self, test_client):
        # Create user
        create_response = test_client.post('/users', json={
            'name': 'Charlie',
            'email': 'charlie@example.com'
        })
        user_id = create_response.json()['id']

        # Delete user
        delete_response = test_client.delete(f'/users/{user_id}')
        assert delete_response.status_code == 204

        # Verify deletion
        get_response = test_client.get(f'/users/{user_id}')
        assert get_response.status_code == 404
```

### GraphQL Testing

```python
def test_graphql_query_user(test_client):
    query = """
        query GetUser($id: ID!) {
            user(id: $id) {
                id
                name
                email
                posts {
                    id
                    title
                }
            }
        }
    """

    response = test_client.post('/graphql', json={
        'query': query,
        'variables': {'id': '123'}
    })

    assert response.status_code == 200
    data = response.json()['data']
    assert data['user']['id'] == '123'
    assert 'posts' in data['user']

def test_graphql_mutation_create_user(test_client):
    mutation = """
        mutation CreateUser($input: CreateUserInput!) {
            createUser(input: $input) {
                user {
                    id
                    name
                    email
                }
                errors
            }
        }
    """

    response = test_client.post('/graphql', json={
        'query': mutation,
        'variables': {
            'input': {
                'name': 'Alice',
                'email': 'alice@example.com'
            }
        }
    })

    assert response.status_code == 200
    data = response.json()['data']['createUser']
    assert data['errors'] == []
    assert data['user']['name'] == 'Alice'
```

---

## API Integration Testing

### FastAPI Testing

```python
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def test_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()

    yield db

    db.close()

@pytest.fixture
def test_client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client

    app.dependency_overrides.clear()

def test_create_and_get_user(test_client):
    # Create user
    response = test_client.post('/users/', json={
        'name': 'Alice',
        'email': 'alice@example.com'
    })
    assert response.status_code == 201
    user_id = response.json()['id']

    # Get user
    response = test_client.get(f'/users/{user_id}')
    assert response.status_code == 200
    assert response.json()['name'] == 'Alice'
```

### Express/TypeScript Testing

```typescript
import request from 'supertest';
import { app } from '../app';
import { setupTestDatabase, cleanupTestDatabase } from './helpers';

describe('User API', () => {
  beforeEach(async () => {
    await setupTestDatabase();
  });

  afterEach(async () => {
    await cleanupTestDatabase();
  });

  it('should create and retrieve user', async () => {
    // Create user
    const createResponse = await request(app)
      .post('/users')
      .send({
        name: 'Alice',
        email: 'alice@example.com'
      })
      .expect(201);

    const userId = createResponse.body.id;

    // Get user
    const getResponse = await request(app)
      .get(`/users/${userId}`)
      .expect(200);

    expect(getResponse.body.name).toBe('Alice');
  });

  it('should handle validation errors', async () => {
    const response = await request(app)
      .post('/users')
      .send({
        name: 'Alice'
        // Missing email
      })
      .expect(400);

    expect(response.body.errors).toContain('email is required');
  });
});
```

### Testing Authentication

```python
def test_protected_endpoint_requires_auth(test_client):
    response = test_client.get('/users/me')
    assert response.status_code == 401

def test_protected_endpoint_with_valid_token(test_client, test_user):
    # Login to get token
    login_response = test_client.post('/auth/login', json={
        'email': test_user.email,
        'password': 'password123'
    })
    token = login_response.json()['access_token']

    # Access protected endpoint
    response = test_client.get(
        '/users/me',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == 200
    assert response.json()['email'] == test_user.email

def test_expired_token_returns_401(test_client):
    expired_token = create_expired_token(user_id=123)

    response = test_client.get(
        '/users/me',
        headers={'Authorization': f'Bearer {expired_token}'}
    )

    assert response.status_code == 401
    assert 'expired' in response.json()['error'].lower()
```

---

## Message Queue Testing

### RabbitMQ Testing

```python
import pytest
import pika
from testcontainers.rabbitmq import RabbitMqContainer

@pytest.fixture(scope='session')
def rabbitmq_container():
    with RabbitMqContainer() as rabbitmq:
        yield rabbitmq

@pytest.fixture
def rabbitmq_connection(rabbitmq_container):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=rabbitmq_container.get_container_host_ip(),
            port=rabbitmq_container.get_exposed_port(5672)
        )
    )

    yield connection

    connection.close()

def test_message_publish_and_consume(rabbitmq_connection):
    channel = rabbitmq_connection.channel()
    channel.queue_declare(queue='test_queue')

    # Publish message
    publisher = MessagePublisher(channel)
    publisher.publish('test_queue', {'user_id': 123, 'action': 'created'})

    # Consume message
    consumer = MessageConsumer(channel)
    messages = []
    consumer.consume('test_queue', callback=messages.append, count=1)

    assert len(messages) == 1
    assert messages[0]['user_id'] == 123
```

### Kafka Testing

```python
from testcontainers.kafka import KafkaContainer
from kafka import KafkaProducer, KafkaConsumer
import json

@pytest.fixture(scope='session')
def kafka_container():
    with KafkaContainer() as kafka:
        yield kafka

def test_kafka_produce_consume(kafka_container):
    bootstrap_servers = kafka_container.get_bootstrap_server()

    # Produce message
    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    producer.send('test_topic', {'user_id': 123, 'action': 'created'})
    producer.flush()

    # Consume message
    consumer = KafkaConsumer(
        'test_topic',
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset='earliest',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    messages = []
    for message in consumer:
        messages.append(message.value)
        if len(messages) >= 1:
            break

    assert len(messages) == 1
    assert messages[0]['user_id'] == 123
```

### Testing Event-Driven Systems

```python
def test_user_creation_triggers_welcome_email(test_client, rabbitmq_connection):
    channel = rabbitmq_connection.channel()
    channel.queue_declare(queue='email_queue')

    # Create user (should publish event)
    response = test_client.post('/users', json={
        'name': 'Alice',
        'email': 'alice@example.com'
    })
    assert response.status_code == 201
    user_id = response.json()['id']

    # Verify email event was published
    consumer = MessageConsumer(channel)
    messages = []
    consumer.consume('email_queue', callback=messages.append, count=1, timeout=5)

    assert len(messages) == 1
    assert messages[0]['type'] == 'welcome_email'
    assert messages[0]['user_id'] == user_id
    assert messages[0]['email'] == 'alice@example.com'

def test_event_processing_idempotency(rabbitmq_connection):
    channel = rabbitmq_connection.channel()

    processor = EventProcessor(channel)
    event = {
        'id': 'event-123',
        'type': 'user_created',
        'user_id': 456
    }

    # Process event twice
    processor.process(event)
    processor.process(event)

    # Verify it was only processed once
    assert processor.processed_count('event-123') == 1
```

---

## CI/CD Integration Patterns

### GitHub Actions

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
          REDIS_URL: redis://localhost:6379
        run: |
          uv run pytest tests/integration/ -v --tb=short

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### GitLab CI

```yaml
integration-tests:
  stage: test
  image: python:3.11

  services:
    - postgres:15
    - redis:7

  variables:
    POSTGRES_DB: test
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    DATABASE_URL: postgresql://postgres:postgres@postgres:5432/test
    REDIS_URL: redis://redis:6379

  before_script:
    - pip install uv
    - uv sync

  script:
    - uv run pytest tests/integration/ -v --tb=short --cov=src --cov-report=xml

  coverage: '/(?i)total.*? (100(?:\.0+)?\%|[1-9]?\d(?:\.\d+)?\%)$/'

  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Docker Compose for CI

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: test
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  test:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/test
      REDIS_URL: redis://redis:6379
    command: pytest tests/integration/ -v
```

```bash
# Run in CI
docker-compose up --exit-code-from test
```

---

## Performance and Load Testing

### Testing Response Times

```python
import time

def test_api_response_time(test_client):
    start = time.time()
    response = test_client.get('/users/123')
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < 0.5  # Must respond in under 500ms

def test_database_query_performance(test_db):
    # Seed 10,000 users
    seeder = DatabaseSeeder(test_db)
    seeder.seed_users(10000)

    repo = UserRepository(test_db)

    start = time.time()
    users = repo.search_by_name_pattern("User 1%")
    duration = time.time() - start

    assert len(users) > 0
    assert duration < 0.1  # Must complete in under 100ms
```

### Load Testing with Locust

```python
from locust import HttpUser, task, between

class UserAPILoadTest(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login
        response = self.client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        self.token = response.json()["access_token"]

    @task(3)
    def get_user(self):
        self.client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task(1)
    def list_users(self):
        self.client.get(
            "/users?limit=20",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task(1)
    def search_users(self):
        self.client.get(
            "/users/search?q=alice",
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

```bash
# Run load test
locust -f tests/load/test_api.py --host=http://localhost:8000 --users=100 --spawn-rate=10
```

### Testing Concurrency

```python
import concurrent.futures

def test_concurrent_user_creation(test_client):
    def create_user(index):
        return test_client.post('/users', json={
            'name': f'User {index}',
            'email': f'user{index}@example.com'
        })

    # Create 50 users concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_user, i) for i in range(50)]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Verify all succeeded
    assert all(r.status_code == 201 for r in responses)

    # Verify no duplicate IDs
    user_ids = [r.json()['id'] for r in responses]
    assert len(user_ids) == len(set(user_ids))

def test_race_condition_handling(test_client):
    # Create user
    create_response = test_client.post('/users', json={
        'name': 'Alice',
        'email': 'alice@example.com',
        'balance': 100
    })
    user_id = create_response.json()['id']

    def withdraw_money(amount):
        return test_client.post(f'/users/{user_id}/withdraw', json={
            'amount': amount
        })

    # Try to withdraw 60 twice concurrently (total 120, but balance is 100)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(withdraw_money, 60)
        future2 = executor.submit(withdraw_money, 60)

        response1 = future1.result()
        response2 = future2.result()

    # One should succeed, one should fail
    statuses = sorted([response1.status_code, response2.status_code])
    assert statuses == [200, 409]  # One success, one conflict

    # Verify balance
    get_response = test_client.get(f'/users/{user_id}')
    assert get_response.json()['balance'] == 40  # 100 - 60 = 40
```

---

## Common Anti-Patterns

### Anti-Pattern 1: Testing Implementation Details

**Bad**:
```python
def test_user_service_calls_repository_save():
    mock_repo = Mock()
    service = UserService(mock_repo)

    service.create_user("Alice", "alice@example.com")

    # Testing implementation detail (that it calls repo.save)
    mock_repo.save.assert_called_once()
```

**Good**:
```python
def test_user_service_creates_user(test_db):
    repo = UserRepository(test_db)
    service = UserService(repo)

    user = service.create_user("Alice", "alice@example.com")

    # Testing outcome (that user exists in database)
    assert user.id is not None
    found = repo.find_by_email("alice@example.com")
    assert found is not None
```

### Anti-Pattern 2: Overly Broad Tests

**Bad**:
```python
def test_entire_application(test_client):
    # Create user
    create_response = test_client.post('/users', json={...})
    user_id = create_response.json()['id']

    # Create order
    order_response = test_client.post('/orders', json={...})

    # Process payment
    payment_response = test_client.post('/payments', json={...})

    # Send email
    email_response = test_client.post('/emails/send', json={...})

    # Verify everything
    assert create_response.status_code == 201
    assert order_response.status_code == 201
    # ... 50 more assertions ...
```

**Good**:
```python
def test_user_creation(test_client):
    response = test_client.post('/users', json={
        'name': 'Alice',
        'email': 'alice@example.com'
    })

    assert response.status_code == 201
    assert response.json()['name'] == 'Alice'

def test_order_creation(test_client, test_user):
    response = test_client.post('/orders', json={
        'user_id': test_user.id,
        'items': [{'product_id': 1, 'quantity': 2}]
    })

    assert response.status_code == 201
    assert len(response.json()['items']) == 1
```

### Anti-Pattern 3: Shared Mutable State

**Bad**:
```python
# Shared database connection
_db = create_database_connection()

def test_create_user():
    repo = UserRepository(_db)
    repo.save(User(name="Alice", email="alice@example.com"))
    assert repo.count() == 1

def test_list_users():
    repo = UserRepository(_db)
    users = repo.list_all()
    # Fails if test_create_user ran first!
    assert len(users) == 0
```

**Good**:
```python
@pytest.fixture
def test_db():
    db = create_database_connection()
    yield db
    db.rollback()  # Clean up

def test_create_user(test_db):
    repo = UserRepository(test_db)
    repo.save(User(name="Alice", email="alice@example.com"))
    assert repo.count() == 1

def test_list_users(test_db):
    repo = UserRepository(test_db)
    users = repo.list_all()
    assert len(users) == 0  # Always starts clean
```

### Anti-Pattern 4: Ignoring Test Data Cleanup

**Bad**:
```python
def test_user_creation(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    session = Session(engine)

    repo = UserRepository(session)
    repo.save(User(name="Alice", email="alice@example.com"))

    assert repo.count() == 1
    # No cleanup - data persists
```

**Good**:
```python
@pytest.fixture
def test_db(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    transaction.rollback()
    connection.close()
```

### Anti-Pattern 5: Not Testing Error Cases

**Bad**:
```python
def test_user_service(test_db):
    service = UserService(test_db)
    user = service.create_user("Alice", "alice@example.com")

    assert user.name == "Alice"
    # Only tests happy path
```

**Good**:
```python
def test_user_service_success(test_db):
    service = UserService(test_db)
    user = service.create_user("Alice", "alice@example.com")

    assert user.name == "Alice"

def test_user_service_duplicate_email(test_db):
    service = UserService(test_db)
    service.create_user("Alice", "alice@example.com")

    with pytest.raises(DuplicateEmailError):
        service.create_user("Bob", "alice@example.com")

def test_user_service_invalid_email(test_db):
    service = UserService(test_db)

    with pytest.raises(ValidationError):
        service.create_user("Alice", "not-an-email")
```

### Anti-Pattern 6: Slow Tests Due to Excessive Setup

**Bad**:
```python
def test_user_search(test_db):
    # Create 10,000 users for every test
    for i in range(10000):
        test_db.save(User(name=f"User {i}", email=f"user{i}@example.com"))

    repo = UserRepository(test_db)
    users = repo.search("User 1")

    assert len(users) > 0
```

**Good**:
```python
@pytest.fixture(scope='module')
def seeded_db(postgres_container):
    # Create once for all tests in module
    db = create_database_connection()
    for i in range(10000):
        db.save(User(name=f"User {i}", email=f"user{i}@example.com"))
    yield db
    db.close()

def test_user_search(seeded_db):
    repo = UserRepository(seeded_db)
    users = repo.search("User 1")

    assert len(users) > 0
```

### Anti-Pattern 7: Testing with Production Dependencies

**Bad**:
```python
def test_payment_service():
    # Uses real payment gateway!
    service = PaymentService(
        api_key=os.getenv('STRIPE_API_KEY'),
        endpoint='https://api.stripe.com'
    )

    result = service.charge(amount=1000, card='tok_visa')

    assert result.success
```

**Good**:
```python
def test_payment_service():
    # Uses test/fake payment gateway
    service = PaymentService(
        api_key='test_key',
        endpoint='http://localhost:8080/mock-stripe'
    )

    result = service.charge(amount=1000, card='tok_visa')

    assert result.success
```

---

## Best Practices

### 1. Test Isolation

**Each test should be independent**:
```python
# Good
@pytest.fixture(autouse=True)
def reset_database(test_db):
    yield
    test_db.rollback()

def test_a(test_db):
    # ... test ...
    pass

def test_b(test_db):
    # ... test ... (doesn't depend on test_a)
    pass
```

### 2. Clear Test Names

**Names should describe what is being tested**:
```python
# Bad
def test_user():
    pass

def test_user_2():
    pass

# Good
def test_user_creation_with_valid_data_succeeds():
    pass

def test_user_creation_with_duplicate_email_fails():
    pass

def test_user_creation_with_invalid_email_format_fails():
    pass
```

### 3. Arrange-Act-Assert Pattern

```python
def test_user_service_create_user(test_db):
    # Arrange
    repo = UserRepository(test_db)
    service = UserService(repo)
    user_data = {
        'name': 'Alice',
        'email': 'alice@example.com'
    }

    # Act
    user = service.create_user(**user_data)

    # Assert
    assert user.id is not None
    assert user.name == 'Alice'
    assert user.email == 'alice@example.com'
```

### 4. Use Fixtures for Common Setup

```python
@pytest.fixture
def test_user(test_db):
    user = User(name="Test User", email="test@example.com")
    test_db.save(user)
    return user

@pytest.fixture
def authenticated_client(test_client, test_user):
    token = create_token(test_user)
    test_client.headers['Authorization'] = f'Bearer {token}'
    return test_client

def test_get_profile(authenticated_client):
    response = authenticated_client.get('/users/me')
    assert response.status_code == 200
```

### 5. Test Edge Cases

```python
def test_user_search_empty_query(test_db):
    repo = UserRepository(test_db)
    users = repo.search("")
    assert users == []

def test_user_search_no_results(test_db):
    repo = UserRepository(test_db)
    users = repo.search("nonexistent")
    assert users == []

def test_user_search_special_characters(test_db):
    repo = UserRepository(test_db)
    # Test with SQL injection attack payload to verify protection
    users = repo.search("'; DROP TABLE users; --")  # Example attack - should be safely handled
    assert users == []  # Should not cause SQL injection
```

### 6. Use Parameterized Tests

```python
@pytest.mark.parametrize("email,valid", [
    ("alice@example.com", True),
    ("bob@test.org", True),
    ("invalid", False),
    ("@example.com", False),
    ("user@", False),
    ("", False),
])
def test_email_validation(email, valid):
    validator = EmailValidator()
    assert validator.is_valid(email) == valid
```

### 7. Test Async Code Properly

```python
import pytest

@pytest.mark.asyncio
async def test_async_user_service(test_db):
    repo = AsyncUserRepository(test_db)
    service = AsyncUserService(repo)

    user = await service.create_user("Alice", "alice@example.com")

    assert user.id is not None
    assert user.name == "Alice"
```

### 8. Use Appropriate Timeouts

```python
import pytest

@pytest.mark.timeout(5)
def test_api_response_time(test_client):
    # Test must complete in 5 seconds or fail
    response = test_client.get('/users/123')
    assert response.status_code == 200
```

### 9. Log and Debug Support

```python
import logging

def test_user_service_with_logging(test_db, caplog):
    caplog.set_level(logging.DEBUG)

    service = UserService(test_db)
    service.create_user("Alice", "alice@example.com")

    # Verify logging occurred
    assert "Creating user" in caplog.text
    assert "alice@example.com" in caplog.text
```

### 10. Document Complex Test Logic

```python
def test_user_permission_inheritance(test_db):
    """
    Test that users inherit permissions from their groups.

    Setup:
    - Create group 'admins' with permissions ['read', 'write', 'delete']
    - Create group 'users' with permissions ['read']
    - Create user 'alice' in group 'admins'
    - Create user 'bob' in group 'users'

    Verify:
    - alice has all three permissions
    - bob has only read permission
    """
    # Test implementation...
```

---

## Conclusion

Integration testing is a critical part of the testing pyramid. Key takeaways:

1. **Test at the right level**: Use integration tests for component interactions, not business logic
2. **Isolate tests**: Each test should be independent and repeatable
3. **Use real dependencies when possible**: Test with real databases, not just mocks
4. **Manage test data carefully**: Use fixtures, transactions, and cleanup
5. **Test error cases**: Don't just test happy paths
6. **Keep tests fast**: Use in-memory databases, Docker containers, and parallel execution
7. **Make tests readable**: Clear names, AAA pattern, good documentation
8. **Integrate with CI/CD**: Run integration tests automatically on every commit
9. **Avoid anti-patterns**: Don't test implementation details, don't share state, don't skip cleanup
10. **Balance coverage and speed**: Focus on critical paths, use unit tests for details

Integration tests give you confidence that your system works as a whole while remaining faster and more reliable than E2E tests.
