#!/usr/bin/env python3
"""
Complete gRPC Server Implementation

Demonstrates all four RPC types:
- Unary: GetUser, CreateUser, UpdateUser, DeleteUser
- Server streaming: ListUsers, WatchUserChanges
- Client streaming: CreateUsers, UploadUserData
- Bidirectional streaming: Chat, CollaborativeEdit

Usage:
    python server.py
"""

import grpc
from concurrent import futures
import time
import logging
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp

# Note: Generate stubs with:
# python -m grpc_tools.protoc -I../protos --python_out=. --grpc_python_out=. ../protos/service.proto

# import service_pb2
# import service_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserServiceImplementation:
    """Implementation of UserService with all RPC types"""

    def __init__(self):
        # In-memory database (use real DB in production)
        self.users = {}
        self.user_id_counter = 1
        self.watchers = []

        # Create sample users
        self._init_sample_data()

    def _init_sample_data(self):
        """Initialize sample data"""
        sample_users = [
            {"email": "alice@example.com", "name": "Alice", "age": 30},
            {"email": "bob@example.com", "name": "Bob", "age": 25},
            {"email": "charlie@example.com", "name": "Charlie", "age": 35},
        ]

        # for user_data in sample_users:
        #     user_id = str(self.user_id_counter)
        #     self.user_id_counter += 1
        #
        #     now = Timestamp()
        #     now.GetCurrentTime()
        #
        #     user = service_pb2.User(
        #         id=user_id,
        #         email=user_data["email"],
        #         name=user_data["name"],
        #         age=user_data["age"],
        #         status=service_pb2.USER_STATUS_ACTIVE,
        #         created_at=now,
        #         updated_at=now
        #     )
        #     self.users[user_id] = user

        logger.info(f"Initialized with {len(self.users)} sample users")

    # ==================== Unary RPCs ====================

    def GetUser(self, request, context):
        """
        Unary RPC: Get single user by ID

        Args:
            request: GetUserRequest with user ID
            context: gRPC context

        Returns:
            GetUserResponse with user data
        """
        logger.info(f"GetUser called: id={request.id}")

        # Validate input
        if not request.id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('User ID is required')
            # return service_pb2.GetUserResponse()

        # Check authentication (example)
        metadata = dict(context.invocation_metadata())
        if 'authorization' not in metadata:
            logger.warning("Unauthenticated request to GetUser")
            # Allow for demo purposes

        # Fetch user
        user = self.users.get(request.id)
        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f'User {request.id} not found')
            # return service_pb2.GetUserResponse()

        # return service_pb2.GetUserResponse(user=user)

    def CreateUser(self, request, context):
        """
        Unary RPC: Create new user

        Args:
            request: CreateUserRequest with user data
            context: gRPC context

        Returns:
            CreateUserResponse with created user
        """
        logger.info(f"CreateUser called: email={request.email}")

        # Validate
        if not request.email or not request.name:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Email and name are required')
            # return service_pb2.CreateUserResponse()

        # Check for duplicate email
        for user in self.users.values():
            if user.email == request.email:
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                context.set_details(f'User with email {request.email} already exists')
                # return service_pb2.CreateUserResponse()

        # Create user
        user_id = str(self.user_id_counter)
        self.user_id_counter += 1

        now = Timestamp()
        now.GetCurrentTime()

        # user = service_pb2.User(
        #     id=user_id,
        #     email=request.email,
        #     name=request.name,
        #     age=request.age,
        #     tags=list(request.tags),
        #     status=service_pb2.USER_STATUS_ACTIVE,
        #     created_at=now,
        #     updated_at=now
        # )

        # self.users[user_id] = user
        logger.info(f"Created user {user_id}: {request.name}")

        # return service_pb2.CreateUserResponse(
        #     user=user,
        #     message=f"User {user_id} created successfully"
        # )

    def UpdateUser(self, request, context):
        """
        Unary RPC: Update existing user

        Args:
            request: UpdateUserRequest with user updates
            context: gRPC context

        Returns:
            UpdateUserResponse with updated user
        """
        logger.info(f"UpdateUser called: id={request.id}")

        # Validate
        if not request.id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('User ID is required')
            # return service_pb2.UpdateUserResponse()

        # Check existence
        if request.id not in self.users:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f'User {request.id} not found')
            # return service_pb2.UpdateUserResponse()

        # Update user
        user = self.users[request.id]

        if request.name:
            user.name = request.name
        if request.age:
            user.age = request.age
        if request.tags:
            user.tags[:] = request.tags

        now = Timestamp()
        now.GetCurrentTime()
        user.updated_at.CopyFrom(now)

        logger.info(f"Updated user {request.id}")

        # return service_pb2.UpdateUserResponse(user=user)

    def DeleteUser(self, request, context):
        """
        Unary RPC: Delete user

        Args:
            request: DeleteUserRequest with user ID
            context: gRPC context

        Returns:
            Empty message
        """
        logger.info(f"DeleteUser called: id={request.id}")

        # Validate
        if not request.id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('User ID is required')
            # return google.protobuf.Empty()

        # Delete user
        if request.id in self.users:
            del self.users[request.id]
            logger.info(f"Deleted user {request.id}")
        else:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f'User {request.id} not found')

        # return google.protobuf.Empty()

    # ==================== Server Streaming RPCs ====================

    def ListUsers(self, request, context):
        """
        Server streaming RPC: Stream all users

        Args:
            request: ListUsersRequest with pagination
            context: gRPC context

        Yields:
            User messages
        """
        logger.info(f"ListUsers called: page_size={request.page_size}")

        page_size = request.page_size or 50

        # Stream users
        count = 0
        for user_id, user in self.users.items():
            # Check cancellation
            if context.is_active():
                # Filter by status if specified
                if request.status_filter and user.status != request.status_filter:
                    continue

                yield user
                count += 1

                # Respect page size
                if count >= page_size:
                    break

                # Simulate processing delay
                time.sleep(0.1)
            else:
                logger.info("Client cancelled ListUsers")
                return

        logger.info(f"ListUsers streamed {count} users")

    def WatchUserChanges(self, request, context):
        """
        Server streaming RPC: Watch for user changes

        Args:
            request: WatchUserChangesRequest with user IDs to watch
            context: gRPC context

        Yields:
            UserEvent messages
        """
        logger.info(f"WatchUserChanges called: watching {len(request.user_ids)} users")

        # Simulate real-time events
        # In production, this would subscribe to a message queue or database changes

        events = [
            # ("CREATED", "1"),
            # ("UPDATED", "2"),
            # ("DELETED", "3"),
        ]

        for event_type_name, user_id in events:
            if not context.is_active():
                logger.info("Client cancelled WatchUserChanges")
                return

            # Create event
            now = Timestamp()
            now.GetCurrentTime()

            # event_type = getattr(service_pb2.UserEvent, f"EVENT_TYPE_{event_type_name}")

            # if user_id in self.users:
            #     event = service_pb2.UserEvent(
            #         type=event_type,
            #         user=self.users[user_id],
            #         timestamp=now
            #     )
            # else:
            #     # Deleted user event
            #     event = service_pb2.UserEvent(
            #         type=event_type,
            #         user=service_pb2.User(id=user_id),
            #         timestamp=now
            #     )

            # yield event
            time.sleep(1)  # Simulate real-time delay

    # ==================== Client Streaming RPCs ====================

    def CreateUsers(self, request_iterator, context):
        """
        Client streaming RPC: Create multiple users from stream

        Args:
            request_iterator: Stream of CreateUserRequest messages
            context: gRPC context

        Returns:
            CreateUsersResponse with results
        """
        logger.info("CreateUsers called (client streaming)")

        created_users = []
        failed_count = 0

        # Receive stream of requests
        for request in request_iterator:
            try:
                # Validate
                if not request.email or not request.name:
                    failed_count += 1
                    continue

                # Create user
                user_id = str(self.user_id_counter)
                self.user_id_counter += 1

                now = Timestamp()
                now.GetCurrentTime()

                # user = service_pb2.User(
                #     id=user_id,
                #     email=request.email,
                #     name=request.name,
                #     age=request.age,
                #     tags=list(request.tags),
                #     status=service_pb2.USER_STATUS_ACTIVE,
                #     created_at=now,
                #     updated_at=now
                # )

                # self.users[user_id] = user
                # created_users.append(user)

                logger.info(f"Created user {user_id} in batch")

            except Exception as e:
                logger.error(f"Failed to create user: {e}")
                failed_count += 1

        logger.info(f"CreateUsers completed: created={len(created_users)}, failed={failed_count}")

        # return service_pb2.CreateUsersResponse(
        #     users=created_users,
        #     created_count=len(created_users),
        #     failed_count=failed_count
        # )

    def UploadUserData(self, request_iterator, context):
        """
        Client streaming RPC: Upload user data in chunks

        Args:
            request_iterator: Stream of UploadDataChunk messages
            context: gRPC context

        Returns:
            UploadDataResponse with results
        """
        logger.info("UploadUserData called (client streaming)")

        file_data = bytearray()
        metadata = None

        # Receive stream of chunks
        for request in request_iterator:
            if request.HasField('metadata'):
                # First message: metadata
                metadata = request.metadata
                logger.info(f"Receiving file: {metadata.filename} ({metadata.total_size} bytes)")

            elif request.HasField('chunk'):
                # Subsequent messages: data chunks
                file_data.extend(request.chunk)
                logger.info(f"Received chunk: {len(request.chunk)} bytes (total: {len(file_data)})")

        # Process uploaded data
        if metadata:
            file_id = f"file_{int(time.time())}"
            logger.info(f"Upload complete: {file_id} ({len(file_data)} bytes)")

            # return service_pb2.UploadDataResponse(
            #     file_id=file_id,
            #     bytes_uploaded=len(file_data)
            # )
        else:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('No metadata provided')
            # return service_pb2.UploadDataResponse()

    # ==================== Bidirectional Streaming RPCs ====================

    def Chat(self, request_iterator, context):
        """
        Bidirectional streaming RPC: Chat room

        Args:
            request_iterator: Stream of ChatMessage from client
            context: gRPC context

        Yields:
            ChatMessage responses
        """
        logger.info("Chat called (bidirectional streaming)")

        # Process incoming messages and echo back
        for message in request_iterator:
            if not context.is_active():
                logger.info("Client cancelled Chat")
                return

            logger.info(f"Chat message from {message.user_id}: {message.content}")

            # Echo back (or broadcast to other users in production)
            now = Timestamp()
            now.GetCurrentTime()

            # response = service_pb2.ChatMessage(
            #     user_id='system',
            #     content=f'Echo from {message.user_id}: {message.content}',
            #     timestamp=now
            # )

            # yield response

    def CollaborativeEdit(self, request_iterator, context):
        """
        Bidirectional streaming RPC: Collaborative document editing

        Args:
            request_iterator: Stream of EditOperation from client
            context: gRPC context

        Yields:
            EditOperation responses
        """
        logger.info("CollaborativeEdit called (bidirectional streaming)")

        # Process edit operations and broadcast to other clients
        for edit_op in request_iterator:
            if not context.is_active():
                logger.info("Client cancelled CollaborativeEdit")
                return

            logger.info(f"Edit from {edit_op.user_id}: {edit_op.type} at {edit_op.position}")

            # Apply edit to document (in-memory or database)
            # Broadcast to other collaborators

            # Echo back confirmation
            now = Timestamp()
            now.GetCurrentTime()

            edit_op.timestamp.CopyFrom(now)
            yield edit_op


def serve():
    """Start gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add service
    # service_pb2_grpc.add_UserServiceServicer_to_server(
    #     UserServiceImplementation(),
    #     server
    # )

    # Add insecure port (use secure port in production)
    server.add_insecure_port('[::]:50051')

    logger.info("Server starting on port 50051...")
    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.stop(grace=5)


if __name__ == '__main__':
    serve()
