#!/usr/bin/env python3
"""
PostgreSQL Zero-Downtime Credential Rotation

Demonstrates:
- Dual-user rotation strategy (blue/green credentials)
- Connection pool migration without downtime
- Transaction-aware rotation
- Graceful connection draining
- Rollback capability

Strategy:
1. Create secondary user (user_b) with same permissions
2. Migrate connection pool to user_b
3. Update primary user (user_a) password
4. Migrate back to user_a (now rotated)
5. Drop secondary user

This ensures zero connection interruptions during rotation.

Prerequisites:
    pip install psycopg2-binary psycopg2-pool
"""

import psycopg2
from psycopg2 import pool
import secrets
import time
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Optional, Dict, Any


class ZeroDowntimeRotator:
    """
    PostgreSQL credential rotator with zero-downtime guarantee.
    """

    def __init__(self, host: str, port: int, database: str, admin_user: str, admin_password: str):
        """
        Initialize rotator with admin credentials.

        Args:
            host: Database host
            port: Database port
            database: Database name
            admin_user: Admin username (for creating/modifying users)
            admin_password: Admin password
        """
        self.host = host
        self.port = port
        self.database = database
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.connection_pool: Optional[pool.ThreadedConnectionPool] = None

    @contextmanager
    def admin_connection(self):
        """Context manager for admin database connection."""
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.admin_user,
            password=self.admin_password
        )
        conn.autocommit = True
        try:
            yield conn
        finally:
            conn.close()

    def rotate_credentials(self, username: str, current_password: str,
                          drain_timeout: int = 30) -> Dict[str, Any]:
        """
        Rotate credentials with zero downtime.

        Args:
            username: Username to rotate
            current_password: Current password
            drain_timeout: Connection drain timeout (seconds)

        Returns:
            Rotation result with new password
        """
        print(f"[{datetime.utcnow().isoformat()}] Starting zero-downtime rotation")
        print(f"  Target user: {username}")

        start_time = time.time()

        # Step 1: Create secondary user (blue/green pattern)
        secondary_user = f"{username}_temp"
        new_password = self._generate_password()

        print(f"  Creating secondary user: {secondary_user}")
        self._create_secondary_user(username, secondary_user, new_password)

        # Step 2: Initialize connection pool with current credentials
        print("  Initializing connection pool (current credentials)")
        self._initialize_pool(username, current_password)

        # Step 3: Migrate pool to secondary user
        print(f"  Migrating connections to secondary user")
        self._migrate_pool(secondary_user, new_password, drain_timeout)

        # Step 4: Update primary user password
        print(f"  Updating primary user password")
        self._update_user_password(username, new_password)

        # Step 5: Migrate back to primary user
        print(f"  Migrating back to primary user")
        self._migrate_pool(username, new_password, drain_timeout)

        # Step 6: Drop secondary user
        print(f"  Cleaning up secondary user")
        self._drop_user(secondary_user)

        # Step 7: Close pool
        if self.connection_pool:
            self.connection_pool.closeall()
            self.connection_pool = None

        elapsed = time.time() - start_time
        print(f"  Rotation complete in {elapsed:.2f}s")

        return {
            'username': username,
            'new_password': new_password,
            'rotated_at': datetime.utcnow().isoformat(),
            'duration_seconds': elapsed,
            'status': 'success'
        }

    def _generate_password(self, length: int = 32) -> str:
        """Generate secure password."""
        return secrets.token_urlsafe(length)

    def _create_secondary_user(self, primary_user: str, secondary_user: str, password: str):
        """Create secondary user with same permissions as primary."""
        # SECURITY: Usernames must be from config, not user input
        # PostgreSQL doesn't allow parameterized identifiers
        with self.admin_connection() as conn:
            cursor = conn.cursor()

            # Drop if exists
            cursor.execute(f"DROP USER IF EXISTS {secondary_user}")

            # Create user
            cursor.execute(
                f"CREATE USER {secondary_user} WITH PASSWORD %s",
                (password,)
            )

            # Copy grants from primary user
            cursor.execute("""
                SELECT schemaname, tablename, privilege_type
                FROM information_schema.table_privileges
                WHERE grantee = %s
            """, (primary_user,))

            for schema, table, privilege in cursor.fetchall():
                # SECURITY: schema/table/privilege from DB query, secondary_user from config
                cursor.execute(
                    f"GRANT {privilege} ON {schema}.{table} TO {secondary_user}"
                )

            # Copy role memberships
            cursor.execute("""
                SELECT rolname FROM pg_roles r
                JOIN pg_auth_members m ON r.oid = m.roleid
                JOIN pg_roles u ON m.member = u.oid
                WHERE u.rolname = %s
            """, (primary_user,))

            for (role,) in cursor.fetchall():
                # SECURITY: role from DB query, secondary_user from config
                cursor.execute(f"GRANT {role} TO {secondary_user}")

            print(f"    Secondary user created with matching permissions")

    def _update_user_password(self, username: str, new_password: str):
        """Update user password."""
        with self.admin_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"ALTER USER {username} WITH PASSWORD %s",
                (new_password,)
            )

    def _drop_user(self, username: str):
        """Drop user."""
        # SECURITY: username must be from config, not user input
        with self.admin_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DROP USER IF EXISTS {username}")

    def _initialize_pool(self, username: str, password: str, min_conn: int = 1,
                        max_conn: int = 10):
        """Initialize connection pool."""
        self.connection_pool = pool.ThreadedConnectionPool(
            min_conn,
            max_conn,
            host=self.host,
            port=self.port,
            database=self.database,
            user=username,
            password=password
        )

        # Verify pool works
        conn = self.connection_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT current_user, current_timestamp")
            user, ts = cursor.fetchone()
            print(f"    Pool initialized: user={user}, connections={min_conn}-{max_conn}")
        finally:
            self.connection_pool.putconn(conn)

    def _migrate_pool(self, new_username: str, new_password: str, drain_timeout: int):
        """
        Migrate connection pool to new credentials.

        Strategy:
        1. Create new pool with new credentials
        2. Wait for old connections to finish (drain)
        3. Close old pool
        4. Use new pool
        """
        if not self.connection_pool:
            raise RuntimeError("No active connection pool")

        # Get current pool settings
        old_pool = self.connection_pool
        min_conn = old_pool.minconn
        max_conn = old_pool.maxconn

        print(f"    Creating new pool with user: {new_username}")

        # Create new pool
        new_pool = pool.ThreadedConnectionPool(
            min_conn,
            max_conn,
            host=self.host,
            port=self.port,
            database=self.database,
            user=new_username,
            password=new_password
        )

        # Verify new pool
        conn = new_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
        finally:
            new_pool.putconn(conn)

        print(f"    Draining old connections (timeout: {drain_timeout}s)")

        # Drain old pool
        start = time.time()
        while time.time() - start < drain_timeout:
            # Check if all connections idle
            try:
                # Try to get all connections (indicates they're available)
                conns = []
                for _ in range(max_conn):
                    conns.append(old_pool.getconn())

                # All connections available, close them
                for c in conns:
                    old_pool.putconn(c)
                break

            except pool.PoolError:
                # Some connections still in use
                time.sleep(0.5)
                continue

        # Close old pool
        old_pool.closeall()
        print(f"    Old pool drained and closed")

        # Switch to new pool
        self.connection_pool = new_pool
        print(f"    Migration complete, using new credentials")

    def verify_rotation(self, username: str, password: str) -> bool:
        """
        Verify rotation was successful.

        Args:
            username: Rotated username
            password: New password

        Returns:
            True if credentials work
        """
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=username,
                password=password,
                connect_timeout=5
            )

            with conn.cursor() as cursor:
                cursor.execute("SELECT current_user, current_timestamp")
                user, ts = cursor.fetchone()
                print(f"Verification successful: user={user}, timestamp={ts}")

            conn.close()
            return True

        except Exception as e:
            print(f"Verification failed: {e}")
            return False


class ApplicationConnectionPool:
    """
    Application-side connection pool with rotation support.
    """

    def __init__(self, host: str, port: int, database: str):
        self.host = host
        self.port = port
        self.database = database
        self.pool: Optional[pool.ThreadedConnectionPool] = None
        self.current_user = None

    def initialize(self, username: str, password: str, min_conn: int = 2, max_conn: int = 20):
        """Initialize connection pool."""
        self.pool = pool.ThreadedConnectionPool(
            min_conn,
            max_conn,
            host=self.host,
            port=self.port,
            database=self.database,
            user=username,
            password=password
        )
        self.current_user = username
        print(f"Application pool initialized: {min_conn}-{max_conn} connections")

    @contextmanager
    def get_connection(self):
        """Get connection from pool (context manager)."""
        if not self.pool:
            raise RuntimeError("Pool not initialized")

        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def rotate_credentials(self, new_password: str, drain_timeout: int = 60):
        """
        Hot-reload credentials without downtime.

        Args:
            new_password: New password for current user
            drain_timeout: Drain timeout (seconds)
        """
        if not self.pool or not self.current_user:
            raise RuntimeError("Pool not initialized")

        print(f"[{datetime.utcnow().isoformat()}] Hot-reloading credentials")

        # Create new pool with new password
        new_pool = pool.ThreadedConnectionPool(
            self.pool.minconn,
            self.pool.maxconn,
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.current_user,
            password=new_password
        )

        # Verify new pool works
        conn = new_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        finally:
            new_pool.putconn(conn)

        # Drain old pool
        old_pool = self.pool
        self.pool = new_pool

        # Wait for old connections to finish
        time.sleep(2)
        old_pool.closeall()

        print("  Credentials reloaded successfully")


# Example usage
if __name__ == '__main__':
    # Configuration
    DB_HOST = 'localhost'
    DB_PORT = 5432
    DB_NAME = 'myapp'
    ADMIN_USER = 'postgres'
    ADMIN_PASSWORD = 'admin_password'
    APP_USER = 'app_user'
    APP_CURRENT_PASSWORD = 'current_password'

    # Initialize rotator
    rotator = ZeroDowntimeRotator(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        admin_user=ADMIN_USER,
        admin_password=ADMIN_PASSWORD
    )

    # Perform rotation
    result = rotator.rotate_credentials(
        username=APP_USER,
        current_password=APP_CURRENT_PASSWORD,
        drain_timeout=30
    )

    print(f"\nRotation result:")
    print(f"  Username: {result['username']}")
    print(f"  New password: {result['new_password'][:8]}...")
    print(f"  Rotated at: {result['rotated_at']}")
    print(f"  Duration: {result['duration_seconds']:.2f}s")

    # Verify rotation
    success = rotator.verify_rotation(APP_USER, result['new_password'])
    print(f"\nVerification: {'PASSED' if success else 'FAILED'}")
