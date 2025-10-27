#!/usr/bin/env python3
"""
Authentication Interceptor Example

Demonstrates server-side and client-side interceptors for authentication.
"""

import grpc
import jwt
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServerAuthInterceptor(grpc.ServerInterceptor):
    """
    Server-side interceptor for JWT authentication

    Validates JWT tokens from client metadata and aborts
    unauthenticated requests.
    """

    def __init__(self, secret_key, public_methods=None):
        """
        Initialize auth interceptor

        Args:
            secret_key: Secret key for JWT validation
            public_methods: List of methods that don't require auth
        """
        self.secret_key = secret_key
        self.public_methods = public_methods or []

    def intercept_service(self, continuation, handler_call_details):
        """
        Intercept all service calls for authentication

        Args:
            continuation: Function to continue to actual RPC
            handler_call_details: Details about the RPC call

        Returns:
            RPC handler or aborted call
        """
        method = handler_call_details.method
        logger.info(f"[Auth] Intercepting: {method}")

        # Check if method is public (no auth required)
        if method in self.public_methods:
            logger.info(f"[Auth] Public method, skipping auth: {method}")
            return continuation(handler_call_details)

        # Extract metadata
        metadata = dict(handler_call_details.invocation_metadata())
        auth_header = metadata.get('authorization', '')

        if not auth_header.startswith('Bearer '):
            logger.warning(f"[Auth] Missing or invalid auth header: {method}")
            return self._abort_unauthenticated('Missing or invalid authorization header')

        # Extract token
        token = auth_header[7:]  # Remove 'Bearer '

        # Validate token
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            logger.info(f"[Auth] Authenticated user: {user_id} for {method}")

            # Add user context to metadata (accessible in service methods)
            # Note: In production, you'd add this to context
            return continuation(handler_call_details)

        except jwt.ExpiredSignatureError:
            logger.warning(f"[Auth] Expired token: {method}")
            return self._abort_unauthenticated('Token has expired')

        except jwt.InvalidTokenError as e:
            logger.warning(f"[Auth] Invalid token: {method} - {e}")
            return self._abort_unauthenticated('Invalid authentication token')

    def _abort_unauthenticated(self, message):
        """
        Return unauthenticated error

        Args:
            message: Error message

        Returns:
            RPC method handler that aborts with UNAUTHENTICATED
        """
        def abort(request, context):
            context.abort(grpc.StatusCode.UNAUTHENTICATED, message)

        return grpc.unary_unary_rpc_method_handler(
            abort,
            request_deserializer=lambda x: x,
            response_serializer=lambda x: x
        )


class ClientAuthInterceptor(grpc.UnaryUnaryClientInterceptor):
    """
    Client-side interceptor for adding authentication tokens

    Automatically adds JWT token to all outgoing requests.
    """

    def __init__(self, token):
        """
        Initialize client auth interceptor

        Args:
            token: JWT token to add to requests
        """
        self.token = token

    def intercept_unary_unary(self, continuation, client_call_details, request):
        """
        Intercept unary-unary calls to add auth token

        Args:
            continuation: Function to continue with the call
            client_call_details: Details about the call
            request: Request message

        Returns:
            Response from server
        """
        # Get existing metadata
        metadata = []
        if client_call_details.metadata:
            metadata = list(client_call_details.metadata)

        # Add authorization header
        metadata.append(('authorization', f'Bearer {self.token}'))

        logger.info(f"[Client Auth] Adding token to: {client_call_details.method}")

        # Create new call details with updated metadata
        new_details = client_call_details._replace(metadata=metadata)

        # Continue with modified metadata
        return continuation(new_details, request)


class ClientStreamAuthInterceptor(grpc.StreamUnaryClientInterceptor):
    """
    Client-side interceptor for client streaming RPCs with auth
    """

    def __init__(self, token):
        self.token = token

    def intercept_stream_unary(self, continuation, client_call_details, request_iterator):
        """Add auth to client streaming calls"""
        metadata = []
        if client_call_details.metadata:
            metadata = list(client_call_details.metadata)

        metadata.append(('authorization', f'Bearer {self.token}'))

        logger.info(f"[Client Auth] Adding token to stream: {client_call_details.method}")

        new_details = client_call_details._replace(metadata=metadata)
        return continuation(new_details, request_iterator)


def generate_jwt_token(user_id, secret_key, expires_in_hours=24):
    """
    Generate JWT token for user

    Args:
        user_id: User ID to encode in token
        secret_key: Secret key for signing
        expires_in_hours: Token expiration time

    Returns:
        JWT token string
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
        'iat': datetime.utcnow()
    }

    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token


# Example usage for server
def create_authenticated_server(servicer, secret_key):
    """
    Create gRPC server with authentication

    Args:
        servicer: Service implementation
        secret_key: JWT secret key

    Returns:
        gRPC server with auth interceptor
    """
    from concurrent import futures

    # Define public methods (no auth required)
    public_methods = [
        '/users.UserService/HealthCheck',
    ]

    # Create server with auth interceptor
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[ServerAuthInterceptor(secret_key, public_methods)]
    )

    # Add service
    # service_pb2_grpc.add_UserServiceServicer_to_server(servicer, server)

    return server


# Example usage for client
def create_authenticated_client(address, token):
    """
    Create gRPC client with authentication

    Args:
        address: Server address
        token: JWT token

    Returns:
        Authenticated gRPC stub
    """
    # Create channel
    channel = grpc.insecure_channel(address)

    # Create intercepted channel with auth
    intercepted_channel = grpc.intercept_channel(
        channel,
        ClientAuthInterceptor(token),
        ClientStreamAuthInterceptor(token)
    )

    # Create stub with intercepted channel
    # stub = service_pb2_grpc.UserServiceStub(intercepted_channel)

    return None  # stub


if __name__ == '__main__':
    # Example: Generate token
    secret_key = 'your-secret-key-here'
    user_id = 'user123'

    token = generate_jwt_token(user_id, secret_key)
    print(f"Generated token: {token}")

    # Validate token
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        print(f"Token valid for user: {payload['user_id']}")
    except Exception as e:
        print(f"Token validation failed: {e}")
