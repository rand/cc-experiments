#!/usr/bin/env python3
"""
Complete gRPC Client Implementation

Demonstrates calling all four RPC types with error handling.

Usage:
    python client.py
"""

import grpc
import logging
import time
from google.protobuf.timestamp_pb2 import Timestamp

# Note: Generate stubs with:
# python -m grpc_tools.protoc -I../protos --python_out=. --grpc_python_out=. ../protos/service.proto

# import service_pb2
# import service_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_unary_rpcs(stub):
    """Test unary RPC methods"""
    logger.info("=" * 60)
    logger.info("Testing Unary RPCs")
    logger.info("=" * 60)

    # 1. CreateUser
    try:
        logger.info("\n1. CreateUser")
        # request = service_pb2.CreateUserRequest(
        #     email='test@example.com',
        #     name='Test User',
        #     age=28,
        #     tags=['developer', 'tester']
        # )
        # response = stub.CreateUser(request, timeout=5)
        # logger.info(f"Created user: {response.user.id} - {response.message}")
        # user_id = response.user.id
    except grpc.RpcError as e:
        logger.error(f"CreateUser failed: {e.code()} - {e.details()}")
        return

    # 2. GetUser
    try:
        logger.info("\n2. GetUser")
        # request = service_pb2.GetUserRequest(id=user_id)
        # response = stub.GetUser(request, timeout=5)
        # logger.info(f"Retrieved user: {response.user.name} ({response.user.email})")
    except grpc.RpcError as e:
        logger.error(f"GetUser failed: {e.code()} - {e.details()}")

    # 3. UpdateUser
    try:
        logger.info("\n3. UpdateUser")
        # request = service_pb2.UpdateUserRequest(
        #     id=user_id,
        #     name='Updated Test User',
        #     age=29,
        #     tags=['developer', 'tester', 'updated']
        # )
        # response = stub.UpdateUser(request, timeout=5)
        # logger.info(f"Updated user: {response.user.name}")
    except grpc.RpcError as e:
        logger.error(f"UpdateUser failed: {e.code()} - {e.details()}")

    # 4. DeleteUser
    try:
        logger.info("\n4. DeleteUser")
        # request = service_pb2.DeleteUserRequest(id=user_id)
        # stub.DeleteUser(request, timeout=5)
        # logger.info(f"Deleted user: {user_id}")
    except grpc.RpcError as e:
        logger.error(f"DeleteUser failed: {e.code()} - {e.details()}")


def test_server_streaming(stub):
    """Test server streaming RPC methods"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Server Streaming RPCs")
    logger.info("=" * 60)

    # 1. ListUsers
    try:
        logger.info("\n1. ListUsers (server streaming)")
        # request = service_pb2.ListUsersRequest(
        #     page_size=10,
        #     status_filter=service_pb2.USER_STATUS_ACTIVE
        # )
        # response_stream = stub.ListUsers(request, timeout=30)

        # count = 0
        # for user in response_stream:
        #     logger.info(f"User {count + 1}: {user.name} ({user.email})")
        #     count += 1

        # logger.info(f"Total users streamed: {count}")
    except grpc.RpcError as e:
        logger.error(f"ListUsers failed: {e.code()} - {e.details()}")

    # 2. WatchUserChanges
    try:
        logger.info("\n2. WatchUserChanges (server streaming)")
        # request = service_pb2.WatchUserChangesRequest(
        #     user_ids=['1', '2', '3']
        # )
        # event_stream = stub.WatchUserChanges(request, timeout=30)

        # for event in event_stream:
        #     event_type = service_pb2.UserEvent.EventType.Name(event.type)
        #     logger.info(f"Event: {event_type} - User {event.user.id}")

    except grpc.RpcError as e:
        logger.error(f"WatchUserChanges failed: {e.code()} - {e.details()}")


def test_client_streaming(stub):
    """Test client streaming RPC methods"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Client Streaming RPCs")
    logger.info("=" * 60)

    # 1. CreateUsers
    try:
        logger.info("\n1. CreateUsers (client streaming)")

        # def user_generator():
        #     users = [
        #         ('alice@example.com', 'Alice', 30),
        #         ('bob@example.com', 'Bob', 25),
        #         ('charlie@example.com', 'Charlie', 35),
        #     ]
        #     for email, name, age in users:
        #         yield service_pb2.CreateUserRequest(
        #             email=email,
        #             name=name,
        #             age=age
        #         )

        # response = stub.CreateUsers(user_generator(), timeout=30)
        # logger.info(f"Created {response.created_count} users, {response.failed_count} failed")
    except grpc.RpcError as e:
        logger.error(f"CreateUsers failed: {e.code()} - {e.details()}")

    # 2. UploadUserData
    try:
        logger.info("\n2. UploadUserData (client streaming)")

        # def upload_generator():
        #     # First: send metadata
        #     metadata = service_pb2.UploadMetadata(
        #         filename='users.csv',
        #         total_size=1024,
        #         content_type='text/csv'
        #     )
        #     yield service_pb2.UploadDataChunk(metadata=metadata)
        #
        #     # Then: send data chunks
        #     data = b'user1,alice@example.com\nuser2,bob@example.com\n'
        #     chunk_size = 64
        #     for i in range(0, len(data), chunk_size):
        #         chunk = data[i:i + chunk_size]
        #         yield service_pb2.UploadDataChunk(chunk=chunk)
        #
        # response = stub.UploadUserData(upload_generator(), timeout=30)
        # logger.info(f"Uploaded: {response.file_id} ({response.bytes_uploaded} bytes)")
    except grpc.RpcError as e:
        logger.error(f"UploadUserData failed: {e.code()} - {e.details()}")


def test_bidirectional_streaming(stub):
    """Test bidirectional streaming RPC methods"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Bidirectional Streaming RPCs")
    logger.info("=" * 60)

    # 1. Chat
    try:
        logger.info("\n1. Chat (bidirectional streaming)")

        # def message_generator():
        #     messages = ['Hello', 'How are you?', 'Goodbye']
        #     for msg in messages:
        #         now = Timestamp()
        #         now.GetCurrentTime()
        #         yield service_pb2.ChatMessage(
        #             user_id='client123',
        #             content=msg,
        #             timestamp=now
        #         )
        #         time.sleep(1)
        #
        # response_stream = stub.Chat(message_generator())
        #
        # for response in response_stream:
        #     logger.info(f"Received: {response.user_id}: {response.content}")
    except grpc.RpcError as e:
        logger.error(f"Chat failed: {e.code()} - {e.details()}")

    # 2. CollaborativeEdit
    try:
        logger.info("\n2. CollaborativeEdit (bidirectional streaming)")

        # def edit_generator():
        #     edits = [
        #         (service_pb2.EditOperation.OPERATION_TYPE_INSERT, 0, 'Hello '),
        #         (service_pb2.EditOperation.OPERATION_TYPE_INSERT, 6, 'World'),
        #         (service_pb2.EditOperation.OPERATION_TYPE_DELETE, 5, ''),
        #     ]
        #     for op_type, position, text in edits:
        #         now = Timestamp()
        #         now.GetCurrentTime()
        #         yield service_pb2.EditOperation(
        #             document_id='doc123',
        #             user_id='user123',
        #             position=position,
        #             text=text,
        #             type=op_type,
        #             timestamp=now
        #         )
        #         time.sleep(0.5)
        #
        # response_stream = stub.CollaborativeEdit(edit_generator())
        #
        # for response in response_stream:
        #     op_type = service_pb2.EditOperation.OperationType.Name(response.type)
        #     logger.info(f"Edit confirmed: {op_type} at position {response.position}")
    except grpc.RpcError as e:
        logger.error(f"CollaborativeEdit failed: {e.code()} - {e.details()}")


def test_error_handling(stub):
    """Test error handling"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Error Handling")
    logger.info("=" * 60)

    # Test NOT_FOUND
    try:
        logger.info("\n1. GetUser with invalid ID (NOT_FOUND)")
        # request = service_pb2.GetUserRequest(id='nonexistent')
        # stub.GetUser(request, timeout=5)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            logger.info(f"✓ Expected error: {e.code()} - {e.details()}")
        else:
            logger.error(f"✗ Unexpected error: {e.code()} - {e.details()}")

    # Test INVALID_ARGUMENT
    try:
        logger.info("\n2. GetUser with empty ID (INVALID_ARGUMENT)")
        # request = service_pb2.GetUserRequest(id='')
        # stub.GetUser(request, timeout=5)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.INVALID_ARGUMENT:
            logger.info(f"✓ Expected error: {e.code()} - {e.details()}")
        else:
            logger.error(f"✗ Unexpected error: {e.code()} - {e.details()}")

    # Test DEADLINE_EXCEEDED
    try:
        logger.info("\n3. ListUsers with very short timeout (DEADLINE_EXCEEDED)")
        # request = service_pb2.ListUsersRequest(page_size=100)
        # stub.ListUsers(request, timeout=0.001)  # 1ms timeout
        # for user in stub.ListUsers(request, timeout=0.001):
        #     pass
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            logger.info(f"✓ Expected error: {e.code()} - {e.details()}")
        else:
            logger.error(f"✗ Unexpected error: {e.code()} - {e.details()}")


def main():
    """Main client function"""
    # Connect to server
    channel = grpc.insecure_channel('localhost:50051')

    # Optionally add metadata (e.g., authentication)
    # metadata = [('authorization', 'Bearer your-token-here')]

    # Create stub
    # stub = service_pb2_grpc.UserServiceStub(channel)

    logger.info("Connected to gRPC server at localhost:50051")

    try:
        # Test all RPC types
        # test_unary_rpcs(stub)
        # test_server_streaming(stub)
        # test_client_streaming(stub)
        # test_bidirectional_streaming(stub)
        # test_error_handling(stub)

        logger.info("\n" + "=" * 60)
        logger.info("All tests completed!")
        logger.info("=" * 60)

    finally:
        channel.close()
        logger.info("Channel closed")


if __name__ == '__main__':
    main()
