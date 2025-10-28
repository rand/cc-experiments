#!/usr/bin/env python3
"""
GraphQL Server Example using Strawberry

Demonstrates best practices for GraphQL schema design including:
- Type safety with Python type hints
- Connection-based pagination
- Error handling with union types
- DataLoader for N+1 prevention
- Input types for mutations
- Authentication and authorization
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import strawberry
from strawberry.types import Info
from strawberry.scalars import JSON


# Custom Scalars
@strawberry.scalar(
    serialize=lambda v: v.isoformat(),
    parse_value=lambda v: datetime.fromisoformat(v)
)
class DateTime:
    """ISO 8601 datetime with timezone"""


# Enums
@strawberry.enum
class UserRole(str):
    """User role enumeration"""
    ADMIN = "ADMIN"
    USER = "USER"
    GUEST = "GUEST"


@strawberry.enum
class PostStatus(str):
    """Post publication status"""
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


# Domain Models (simulated database)
@dataclass
class UserModel:
    id: str
    username: str
    email: str
    display_name: str
    role: UserRole
    created_at: datetime


@dataclass
class PostModel:
    id: str
    title: str
    content: str
    author_id: str
    status: PostStatus
    created_at: datetime


# In-memory "database"
USERS = [
    UserModel(
        id="1",
        username="alice",
        email="alice@example.com",
        display_name="Alice Smith",
        role=UserRole.ADMIN,
        created_at=datetime(2024, 1, 1),
    ),
    UserModel(
        id="2",
        username="bob",
        email="bob@example.com",
        display_name="Bob Jones",
        role=UserRole.USER,
        created_at=datetime(2024, 1, 15),
    ),
]

POSTS = [
    PostModel(
        id="1",
        title="First Post",
        content="Hello, GraphQL!",
        author_id="1",
        status=PostStatus.PUBLISHED,
        created_at=datetime(2024, 2, 1),
    ),
    PostModel(
        id="2",
        title="Draft Post",
        content="Work in progress...",
        author_id="1",
        status=PostStatus.DRAFT,
        created_at=datetime(2024, 2, 5),
    ),
]


# DataLoader for batching
class UserLoader:
    """Batch load users to prevent N+1 queries"""

    def __init__(self):
        self.cache = {}

    async def load(self, user_id: str) -> Optional[UserModel]:
        if user_id not in self.cache:
            # Simulate database query
            await asyncio.sleep(0.01)
            user = next((u for u in USERS if u.id == user_id), None)
            self.cache[user_id] = user
        return self.cache.get(user_id)

    async def load_many(self, user_ids: list[str]) -> list[Optional[UserModel]]:
        # Batch load multiple users in one query
        await asyncio.sleep(0.01)
        user_map = {u.id: u for u in USERS if u.id in user_ids}
        return [user_map.get(uid) for uid in user_ids]


# Context
@dataclass
class Context:
    """Request context"""
    current_user: Optional[UserModel]
    loaders: dict


def get_context() -> Context:
    """Create request context"""
    return Context(
        current_user=USERS[0],  # Simulate authenticated user
        loaders={"user": UserLoader()}
    )


# GraphQL Types
@strawberry.interface
class Node:
    """Global object identification"""
    id: strawberry.ID


@strawberry.type
class User(Node):
    """User entity"""
    id: strawberry.ID
    username: str
    email: str
    display_name: str
    role: UserRole
    created_at: DateTime

    @strawberry.field
    async def posts(
        self,
        info: Info,
        status: Optional[PostStatus] = None
    ) -> list["Post"]:
        """User's posts with optional filtering"""
        posts = [p for p in POSTS if p.author_id == self.id]

        if status:
            posts = [p for p in posts if p.status == status]

        return [Post.from_model(p) for p in posts]

    @classmethod
    def from_model(cls, model: UserModel) -> "User":
        return cls(
            id=strawberry.ID(model.id),
            username=model.username,
            email=model.email,
            display_name=model.display_name,
            role=model.role,
            created_at=model.created_at,
        )


@strawberry.type
class Post(Node):
    """Post entity"""
    id: strawberry.ID
    title: str
    content: str
    status: PostStatus
    created_at: DateTime

    @strawberry.field
    async def author(self, info: Info) -> User:
        """Post author (uses DataLoader)"""
        post_model = next(p for p in POSTS if p.id == str(self.id))
        loader = info.context.loaders["user"]
        user_model = await loader.load(post_model.author_id)
        return User.from_model(user_model)

    @classmethod
    def from_model(cls, model: PostModel) -> "Post":
        return cls(
            id=strawberry.ID(model.id),
            title=model.title,
            content=model.content,
            status=model.status,
            created_at=model.created_at,
        )


# Pagination Types (Relay Connection Pattern)
@strawberry.type
class PageInfo:
    """Pagination information"""
    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str]
    end_cursor: Optional[str]


@strawberry.type
class PostEdge:
    """Post edge in connection"""
    cursor: str
    node: Post


@strawberry.type
class PostConnection:
    """Paginated posts"""
    edges: list[PostEdge]
    page_info: PageInfo
    total_count: int


# Input Types
@strawberry.input
class CreatePostInput:
    """Input for creating a post"""
    title: str
    content: str
    status: PostStatus = PostStatus.DRAFT


@strawberry.input
class UpdatePostInput:
    """Input for updating a post"""
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[PostStatus] = None


# Error Types
@strawberry.interface
class Error:
    """Base error interface"""
    message: str
    code: str


@strawberry.type
class NotFoundError(Error):
    """Entity not found error"""
    message: str
    code: str
    entity_type: str
    entity_id: str


@strawberry.type
class ValidationError(Error):
    """Validation error"""
    message: str
    code: str
    field: str


# Payload Types
@strawberry.type
class CreatePostPayload:
    """Result of creating a post"""
    success: bool
    errors: list[Error]
    post: Optional[Post]

    @classmethod
    def success_payload(cls, post: Post) -> "CreatePostPayload":
        return cls(success=True, errors=[], post=post)

    @classmethod
    def error_payload(cls, errors: list[Error]) -> "CreatePostPayload":
        return cls(success=False, errors=errors, post=None)


@strawberry.type
class UpdatePostPayload:
    """Result of updating a post"""
    success: bool
    errors: list[Error]
    post: Optional[Post]


# Query
@strawberry.type
class Query:
    """Root query type"""

    @strawberry.field
    def viewer(self, info: Info) -> Optional[User]:
        """Current authenticated user"""
        if info.context.current_user:
            return User.from_model(info.context.current_user)
        return None

    @strawberry.field
    def user(self, id: strawberry.ID) -> Optional[User]:
        """Get user by ID"""
        user_model = next((u for u in USERS if u.id == str(id)), None)
        if user_model:
            return User.from_model(user_model)
        return None

    @strawberry.field
    def users(self, role: Optional[UserRole] = None) -> list[User]:
        """List users with optional filtering"""
        users = USERS
        if role:
            users = [u for u in users if u.role == role]
        return [User.from_model(u) for u in users]

    @strawberry.field
    def post(self, id: strawberry.ID) -> Optional[Post]:
        """Get post by ID"""
        post_model = next((p for p in POSTS if p.id == str(id)), None)
        if post_model:
            return Post.from_model(post_model)
        return None

    @strawberry.field
    def posts(
        self,
        first: int = 10,
        after: Optional[str] = None,
        status: Optional[PostStatus] = None
    ) -> PostConnection:
        """List posts with cursor-based pagination"""
        posts = POSTS

        # Filter by status
        if status:
            posts = [p for p in posts if p.status == status]

        # Simple cursor pagination (in production, use proper implementation)
        start_index = 0
        if after:
            try:
                start_index = int(after) + 1
            except ValueError:
                pass

        end_index = start_index + first
        page_posts = posts[start_index:end_index]

        edges = [
            PostEdge(
                cursor=str(start_index + i),
                node=Post.from_model(p)
            )
            for i, p in enumerate(page_posts)
        ]

        return PostConnection(
            edges=edges,
            page_info=PageInfo(
                has_next_page=end_index < len(posts),
                has_previous_page=start_index > 0,
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None,
            ),
            total_count=len(posts)
        )


# Mutation
@strawberry.type
class Mutation:
    """Root mutation type"""

    @strawberry.mutation
    def create_post(
        self,
        info: Info,
        input: CreatePostInput
    ) -> CreatePostPayload:
        """Create a new post"""
        # Validate
        if not input.title.strip():
            return CreatePostPayload.error_payload([
                ValidationError(
                    message="Title cannot be empty",
                    code="VALIDATION_ERROR",
                    field="title"
                )
            ])

        if not info.context.current_user:
            return CreatePostPayload.error_payload([
                Error(
                    message="Authentication required",
                    code="UNAUTHORIZED"
                )
            ])

        # Create post
        post_model = PostModel(
            id=str(len(POSTS) + 1),
            title=input.title,
            content=input.content,
            author_id=info.context.current_user.id,
            status=input.status,
            created_at=datetime.now(),
        )
        POSTS.append(post_model)

        return CreatePostPayload.success_payload(Post.from_model(post_model))

    @strawberry.mutation
    def update_post(
        self,
        info: Info,
        id: strawberry.ID,
        input: UpdatePostInput
    ) -> UpdatePostPayload:
        """Update an existing post"""
        # Find post
        post_model = next((p for p in POSTS if p.id == str(id)), None)

        if not post_model:
            return UpdatePostPayload(
                success=False,
                errors=[
                    NotFoundError(
                        message=f"Post not found: {id}",
                        code="NOT_FOUND",
                        entity_type="Post",
                        entity_id=str(id)
                    )
                ],
                post=None
            )

        # Check authorization
        if info.context.current_user.id != post_model.author_id:
            return UpdatePostPayload(
                success=False,
                errors=[
                    Error(message="Not authorized", code="FORBIDDEN")
                ],
                post=None
            )

        # Update fields
        if input.title is not None:
            post_model.title = input.title
        if input.content is not None:
            post_model.content = input.content
        if input.status is not None:
            post_model.status = input.status

        return UpdatePostPayload(
            success=True,
            errors=[],
            post=Post.from_model(post_model)
        )


# Schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)


# Run server
if __name__ == "__main__":
    import uvicorn
    from strawberry.fastapi import GraphQLRouter

    from fastapi import FastAPI

    app = FastAPI()

    graphql_app = GraphQLRouter(
        schema,
        context_getter=get_context,
    )

    app.include_router(graphql_app, prefix="/graphql")

    print("GraphQL server running at http://localhost:8000/graphql")
    print("\nExample queries:")
    print("  { viewer { username } }")
    print("  { posts(first: 5) { edges { node { title author { username } } } } }")

    uvicorn.run(app, host="0.0.0.0", port=8000)
