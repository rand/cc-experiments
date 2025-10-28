"""
Integration tests for API endpoints with Docker testcontainers.

Demonstrates testing REST API endpoints with real database and external dependencies.
"""

import pytest
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import time


# Example application (would be in your actual codebase)
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

# Models
Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Schemas
class UserCreate(BaseModel):
    name: str
    email: str


class User(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# Application
app = FastAPI()

# Database dependency
_engine = None
_SessionLocal = None


def get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users", response_model=User, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check for duplicate email
    existing = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    db_user = UserModel(name=user.name, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users", response_model=list[User])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(UserModel).offset(skip).limit(limit).all()
    return users


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()


@app.patch("/users/{user_id}", response_model=User)
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.name = user.name
    db_user.email = user.email
    db.commit()
    db.refresh(db_user)
    return db_user


# Fixtures
@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for testing."""
    with PostgresContainer("postgres:15") as postgres:
        # Wait for PostgreSQL to be ready
        time.sleep(2)
        yield postgres


@pytest.fixture(scope="session")
def database_engine(postgres_container):
    """Create database engine connected to test container."""
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(database_engine):
    """Create a new database session for each test."""
    connection = database_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_client(db_session, database_engine):
    """Create test client with test database."""
    global _engine, _SessionLocal
    _engine = database_engine
    _SessionLocal = sessionmaker(bind=database_engine)

    # Override database dependency
    app.dependency_overrides[get_db] = lambda: db_session

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


# Integration Tests
class TestUserAPI:
    """Integration tests for User API endpoints."""

    def test_create_user_success(self, test_client):
        """Test successful user creation."""
        response = test_client.post("/users", json={
            "name": "Alice Smith",
            "email": "alice@example.com"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Alice Smith"
        assert data["email"] == "alice@example.com"
        assert "id" in data
        assert "created_at" in data

    def test_create_user_with_duplicate_email_fails(self, test_client):
        """Test that creating user with duplicate email returns 409."""
        # Create first user
        test_client.post("/users", json={
            "name": "Alice Smith",
            "email": "alice@example.com"
        })

        # Try to create duplicate
        response = test_client.post("/users", json={
            "name": "Alice Jones",
            "email": "alice@example.com"
        })

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_get_user_success(self, test_client):
        """Test retrieving existing user."""
        # Create user
        create_response = test_client.post("/users", json={
            "name": "Bob Johnson",
            "email": "bob@example.com"
        })
        user_id = create_response.json()["id"]

        # Get user
        response = test_client.get(f"/users/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["name"] == "Bob Johnson"
        assert data["email"] == "bob@example.com"

    def test_get_nonexistent_user_returns_404(self, test_client):
        """Test that getting non-existent user returns 404."""
        response = test_client.get("/users/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_users(self, test_client):
        """Test listing all users."""
        # Create multiple users
        test_client.post("/users", json={"name": "User 1", "email": "user1@example.com"})
        test_client.post("/users", json={"name": "User 2", "email": "user2@example.com"})
        test_client.post("/users", json={"name": "User 3", "email": "user3@example.com"})

        # List users
        response = test_client.get("/users")

        assert response.status_code == 200
        users = response.json()
        assert len(users) >= 3
        assert all("id" in user for user in users)
        assert all("name" in user for user in users)

    def test_list_users_with_pagination(self, test_client):
        """Test listing users with pagination parameters."""
        # Create users
        for i in range(5):
            test_client.post("/users", json={
                "name": f"User {i}",
                "email": f"user{i}@example.com"
            })

        # Get first page
        response = test_client.get("/users?skip=0&limit=2")
        assert response.status_code == 200
        users = response.json()
        assert len(users) == 2

        # Get second page
        response = test_client.get("/users?skip=2&limit=2")
        assert response.status_code == 200
        users = response.json()
        assert len(users) == 2

    def test_update_user(self, test_client):
        """Test updating existing user."""
        # Create user
        create_response = test_client.post("/users", json={
            "name": "Charlie Brown",
            "email": "charlie@example.com"
        })
        user_id = create_response.json()["id"]

        # Update user
        response = test_client.patch(f"/users/{user_id}", json={
            "name": "Charles Brown",
            "email": "charles@example.com"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Charles Brown"
        assert data["email"] == "charles@example.com"

        # Verify update persisted
        get_response = test_client.get(f"/users/{user_id}")
        assert get_response.json()["name"] == "Charles Brown"

    def test_update_nonexistent_user_returns_404(self, test_client):
        """Test that updating non-existent user returns 404."""
        response = test_client.patch("/users/99999", json={
            "name": "Nobody",
            "email": "nobody@example.com"
        })

        assert response.status_code == 404

    def test_delete_user(self, test_client):
        """Test deleting existing user."""
        # Create user
        create_response = test_client.post("/users", json={
            "name": "Diana Prince",
            "email": "diana@example.com"
        })
        user_id = create_response.json()["id"]

        # Delete user
        response = test_client.delete(f"/users/{user_id}")
        assert response.status_code == 204

        # Verify deletion
        get_response = test_client.get(f"/users/{user_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_user_returns_404(self, test_client):
        """Test that deleting non-existent user returns 404."""
        response = test_client.delete("/users/99999")
        assert response.status_code == 404

    def test_complete_user_lifecycle(self, test_client):
        """Test complete CRUD lifecycle for a user."""
        # Create
        create_response = test_client.post("/users", json={
            "name": "Eva Green",
            "email": "eva@example.com"
        })
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]

        # Read
        get_response = test_client.get(f"/users/{user_id}")
        assert get_response.status_code == 200
        assert get_response.json()["email"] == "eva@example.com"

        # Update
        update_response = test_client.patch(f"/users/{user_id}", json={
            "name": "Eva Green Updated",
            "email": "eva.updated@example.com"
        })
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Eva Green Updated"

        # Delete
        delete_response = test_client.delete(f"/users/{user_id}")
        assert delete_response.status_code == 204

        # Verify deleted
        get_after_delete = test_client.get(f"/users/{user_id}")
        assert get_after_delete.status_code == 404


class TestAPIPerformance:
    """Integration tests for API performance."""

    def test_create_user_response_time(self, test_client):
        """Test that user creation completes within acceptable time."""
        import time

        start = time.time()
        response = test_client.post("/users", json={
            "name": "Fast User",
            "email": "fast@example.com"
        })
        duration = time.time() - start

        assert response.status_code == 201
        assert duration < 1.0  # Should complete in under 1 second

    def test_list_users_response_time(self, test_client):
        """Test that listing users completes within acceptable time."""
        # Create some users
        for i in range(10):
            test_client.post("/users", json={
                "name": f"User {i}",
                "email": f"user{i}@perf.com"
            })

        import time
        start = time.time()
        response = test_client.get("/users")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.5  # Should complete in under 500ms


# Run tests with: pytest test_api_integration.py -v
# Run with coverage: pytest test_api_integration.py -v --cov=. --cov-report=html
