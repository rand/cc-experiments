"""
Integration tests for database operations with PostgreSQL testcontainers.

Demonstrates testing repository layer, transactions, constraints, and complex queries.
"""

import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import List, Optional


# Models
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")


# Repository classes
class UserRepository:
    """Repository for user operations."""

    def __init__(self, session):
        self.session = session

    def create(self, username: str, email: str) -> User:
        user = User(username=username, email=email)
        self.session.add(user)
        self.session.flush()
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.session.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.query(User).filter(User.email == email).first()

    def list_active(self) -> List[User]:
        return self.session.query(User).filter(User.is_active == True).all()

    def deactivate(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.session.flush()
            return True
        return False

    def delete(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.flush()
            return True
        return False


class PostRepository:
    """Repository for post operations."""

    def __init__(self, session):
        self.session = session

    def create(self, title: str, content: str, author_id: int) -> Post:
        post = Post(title=title, content=content, author_id=author_id)
        self.session.add(post)
        self.session.flush()
        return post

    def get_by_id(self, post_id: int) -> Optional[Post]:
        return self.session.query(Post).filter(Post.id == post_id).first()

    def list_by_author(self, author_id: int) -> List[Post]:
        return self.session.query(Post).filter(Post.author_id == author_id).all()

    def list_published(self) -> List[Post]:
        return self.session.query(Post).filter(Post.published == True).all()

    def publish(self, post_id: int) -> bool:
        post = self.get_by_id(post_id)
        if post:
            post.published = True
            self.session.flush()
            return True
        return False

    def update(self, post_id: int, title: str = None, content: str = None) -> Optional[Post]:
        post = self.get_by_id(post_id)
        if post:
            if title:
                post.title = title
            if content:
                post.content = content
            post.updated_at = datetime.utcnow()
            self.session.flush()
            return post
        return None


class CommentRepository:
    """Repository for comment operations."""

    def __init__(self, session):
        self.session = session

    def create(self, content: str, author_id: int, post_id: int) -> Comment:
        comment = Comment(content=content, author_id=author_id, post_id=post_id)
        self.session.add(comment)
        self.session.flush()
        return comment

    def list_by_post(self, post_id: int) -> List[Comment]:
        return self.session.query(Comment).filter(Comment.post_id == post_id).all()

    def count_by_post(self, post_id: int) -> int:
        return self.session.query(Comment).filter(Comment.post_id == post_id).count()


# Fixtures
@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for testing."""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def database_engine(postgres_container):
    """Create database engine and tables."""
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(database_engine):
    """Create a new database session for each test with transaction rollback."""
    connection = database_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def user_repo(db_session):
    """Create user repository."""
    return UserRepository(db_session)


@pytest.fixture
def post_repo(db_session):
    """Create post repository."""
    return PostRepository(db_session)


@pytest.fixture
def comment_repo(db_session):
    """Create comment repository."""
    return CommentRepository(db_session)


# Integration Tests
class TestUserRepository:
    """Integration tests for UserRepository."""

    def test_create_user(self, user_repo, db_session):
        """Test creating a new user."""
        user = user_repo.create(username="alice", email="alice@example.com")
        db_session.commit()

        assert user.id is not None
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.is_active is True
        assert user.created_at is not None

    def test_create_user_with_duplicate_username_fails(self, user_repo, db_session):
        """Test that creating user with duplicate username raises IntegrityError."""
        user_repo.create(username="alice", email="alice1@example.com")
        db_session.commit()

        user_repo.create(username="alice", email="alice2@example.com")
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_user_with_duplicate_email_fails(self, user_repo, db_session):
        """Test that creating user with duplicate email raises IntegrityError."""
        user_repo.create(username="alice1", email="alice@example.com")
        db_session.commit()

        user_repo.create(username="alice2", email="alice@example.com")
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_get_user_by_id(self, user_repo, db_session):
        """Test retrieving user by ID."""
        user = user_repo.create(username="bob", email="bob@example.com")
        db_session.commit()

        found = user_repo.get_by_id(user.id)

        assert found is not None
        assert found.id == user.id
        assert found.username == "bob"

    def test_get_user_by_username(self, user_repo, db_session):
        """Test retrieving user by username."""
        user_repo.create(username="charlie", email="charlie@example.com")
        db_session.commit()

        found = user_repo.get_by_username("charlie")

        assert found is not None
        assert found.username == "charlie"

    def test_get_nonexistent_user_returns_none(self, user_repo):
        """Test that getting non-existent user returns None."""
        assert user_repo.get_by_id(99999) is None
        assert user_repo.get_by_username("nonexistent") is None

    def test_list_active_users(self, user_repo, db_session):
        """Test listing only active users."""
        user1 = user_repo.create(username="user1", email="user1@example.com")
        user2 = user_repo.create(username="user2", email="user2@example.com")
        user3 = user_repo.create(username="user3", email="user3@example.com")
        db_session.commit()

        # Deactivate one user
        user_repo.deactivate(user2.id)
        db_session.commit()

        active_users = user_repo.list_active()

        assert len(active_users) == 2
        assert user1.id in [u.id for u in active_users]
        assert user3.id in [u.id for u in active_users]
        assert user2.id not in [u.id for u in active_users]

    def test_delete_user(self, user_repo, db_session):
        """Test deleting a user."""
        user = user_repo.create(username="diana", email="diana@example.com")
        db_session.commit()
        user_id = user.id

        assert user_repo.delete(user_id) is True
        db_session.commit()

        assert user_repo.get_by_id(user_id) is None


class TestPostRepository:
    """Integration tests for PostRepository."""

    def test_create_post(self, user_repo, post_repo, db_session):
        """Test creating a new post."""
        user = user_repo.create(username="author", email="author@example.com")
        db_session.commit()

        post = post_repo.create(
            title="Test Post",
            content="This is a test post",
            author_id=user.id
        )
        db_session.commit()

        assert post.id is not None
        assert post.title == "Test Post"
        assert post.author_id == user.id
        assert post.published is False

    def test_create_post_with_invalid_author_fails(self, post_repo, db_session):
        """Test that creating post with non-existent author fails."""
        post_repo.create(
            title="Invalid Post",
            content="This should fail",
            author_id=99999
        )

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_list_posts_by_author(self, user_repo, post_repo, db_session):
        """Test listing posts by author."""
        user1 = user_repo.create(username="author1", email="author1@example.com")
        user2 = user_repo.create(username="author2", email="author2@example.com")
        db_session.commit()

        post_repo.create("Post 1", "Content 1", user1.id)
        post_repo.create("Post 2", "Content 2", user1.id)
        post_repo.create("Post 3", "Content 3", user2.id)
        db_session.commit()

        user1_posts = post_repo.list_by_author(user1.id)
        user2_posts = post_repo.list_by_author(user2.id)

        assert len(user1_posts) == 2
        assert len(user2_posts) == 1

    def test_publish_post(self, user_repo, post_repo, db_session):
        """Test publishing a post."""
        user = user_repo.create(username="author", email="author@example.com")
        post = post_repo.create("Draft Post", "Content", user.id)
        db_session.commit()

        assert post.published is False

        post_repo.publish(post.id)
        db_session.commit()

        updated_post = post_repo.get_by_id(post.id)
        assert updated_post.published is True

    def test_update_post(self, user_repo, post_repo, db_session):
        """Test updating a post."""
        user = user_repo.create(username="author", email="author@example.com")
        post = post_repo.create("Original Title", "Original Content", user.id)
        db_session.commit()

        original_updated_at = post.updated_at

        # Update post
        updated = post_repo.update(post.id, title="New Title", content="New Content")
        db_session.commit()

        assert updated.title == "New Title"
        assert updated.content == "New Content"
        assert updated.updated_at > original_updated_at


class TestCommentRepository:
    """Integration tests for CommentRepository."""

    def test_create_comment(self, user_repo, post_repo, comment_repo, db_session):
        """Test creating a comment."""
        user = user_repo.create(username="commenter", email="commenter@example.com")
        author = user_repo.create(username="author", email="author@example.com")
        post = post_repo.create("Post", "Content", author.id)
        db_session.commit()

        comment = comment_repo.create("Great post!", user.id, post.id)
        db_session.commit()

        assert comment.id is not None
        assert comment.content == "Great post!"
        assert comment.author_id == user.id
        assert comment.post_id == post.id

    def test_list_comments_by_post(self, user_repo, post_repo, comment_repo, db_session):
        """Test listing comments for a post."""
        user1 = user_repo.create(username="user1", email="user1@example.com")
        user2 = user_repo.create(username="user2", email="user2@example.com")
        author = user_repo.create(username="author", email="author@example.com")
        post = post_repo.create("Post", "Content", author.id)
        db_session.commit()

        comment_repo.create("Comment 1", user1.id, post.id)
        comment_repo.create("Comment 2", user2.id, post.id)
        comment_repo.create("Comment 3", user1.id, post.id)
        db_session.commit()

        comments = comment_repo.list_by_post(post.id)

        assert len(comments) == 3

    def test_count_comments_by_post(self, user_repo, post_repo, comment_repo, db_session):
        """Test counting comments for a post."""
        user = user_repo.create(username="user", email="user@example.com")
        author = user_repo.create(username="author", email="author@example.com")
        post = post_repo.create("Post", "Content", author.id)
        db_session.commit()

        for i in range(5):
            comment_repo.create(f"Comment {i}", user.id, post.id)
        db_session.commit()

        count = comment_repo.count_by_post(post.id)

        assert count == 5


class TestRelationships:
    """Integration tests for model relationships."""

    def test_user_posts_relationship(self, user_repo, post_repo, db_session):
        """Test that user.posts relationship works."""
        user = user_repo.create(username="author", email="author@example.com")
        db_session.commit()

        post_repo.create("Post 1", "Content 1", user.id)
        post_repo.create("Post 2", "Content 2", user.id)
        db_session.commit()

        # Refresh user to load relationships
        db_session.refresh(user)

        assert len(user.posts) == 2
        assert all(post.author_id == user.id for post in user.posts)

    def test_post_comments_relationship(self, user_repo, post_repo, comment_repo, db_session):
        """Test that post.comments relationship works."""
        user = user_repo.create(username="user", email="user@example.com")
        author = user_repo.create(username="author", email="author@example.com")
        post = post_repo.create("Post", "Content", author.id)
        db_session.commit()

        comment_repo.create("Comment 1", user.id, post.id)
        comment_repo.create("Comment 2", user.id, post.id)
        db_session.commit()

        # Refresh post to load relationships
        db_session.refresh(post)

        assert len(post.comments) == 2

    def test_cascade_delete_user_deletes_posts(self, user_repo, post_repo, db_session):
        """Test that deleting user cascades to delete posts."""
        user = user_repo.create(username="author", email="author@example.com")
        db_session.commit()

        post1 = post_repo.create("Post 1", "Content 1", user.id)
        post2 = post_repo.create("Post 2", "Content 2", user.id)
        db_session.commit()

        user_repo.delete(user.id)
        db_session.commit()

        assert post_repo.get_by_id(post1.id) is None
        assert post_repo.get_by_id(post2.id) is None


class TestTransactions:
    """Integration tests for transaction handling."""

    def test_transaction_rollback_on_error(self, user_repo, db_session):
        """Test that transaction rolls back on error."""
        # Create first user
        user_repo.create(username="user1", email="user1@example.com")
        db_session.commit()

        # Start new transaction
        user_repo.create(username="user2", email="user2@example.com")

        # Try to create duplicate (should fail)
        user_repo.create(username="user1", email="user3@example.com")

        try:
            db_session.commit()
        except IntegrityError:
            db_session.rollback()

        # Verify only first user exists
        assert user_repo.get_by_username("user1") is not None
        assert user_repo.get_by_username("user2") is None

    def test_nested_transaction_with_savepoint(self, user_repo, db_session):
        """Test nested transactions with savepoints."""
        user_repo.create(username="user1", email="user1@example.com")

        # Create savepoint
        savepoint = db_session.begin_nested()

        user_repo.create(username="user2", email="user2@example.com")

        # Rollback to savepoint
        savepoint.rollback()

        db_session.commit()

        # Only user1 should exist
        assert user_repo.get_by_username("user1") is not None
        assert user_repo.get_by_username("user2") is None


# Run tests with: pytest test_database_integration.py -v
# Run with coverage: pytest test_database_integration.py -v --cov=. --cov-report=html
