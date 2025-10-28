#!/usr/bin/env python3
"""
HashiCorp Vault Dynamic Database Credentials Example

Demonstrates:
- Dynamic credential generation with Vault
- Automatic credential expiration
- Lease renewal
- Zero manual rotation required

Vault automatically generates temporary database credentials with TTL.
Credentials are revoked automatically after expiration.

Prerequisites:
    pip install hvac psycopg2-binary

Vault Setup:
    vault secrets enable database
    vault write database/config/postgresql \\
        plugin_name=postgresql-database-plugin \\
        allowed_roles="app-role" \\
        connection_url="postgresql://{{username}}:{{password}}@localhost:5432/mydb" \\
        username="vault_admin" \\
        password="vault_admin_password"

    vault write database/roles/app-role \\
        db_name=postgresql \\
        creation_statements="CREATE USER \\\"{{name}}\\\" WITH PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT ON ALL TABLES IN SCHEMA public TO \\\"{{name}}\\\";" \\
        default_ttl="1h" \\
        max_ttl="24h"
"""

import hvac
import psycopg2
import time
from datetime import datetime


class VaultDatabaseClient:
    """
    Database client using Vault dynamic credentials.
    """

    def __init__(self, vault_url: str, token: str, role_name: str):
        """
        Initialize Vault client.

        Args:
            vault_url: Vault server URL
            token: Vault authentication token
            role_name: Database role name
        """
        self.vault_client = hvac.Client(url=vault_url, token=token)
        self.role_name = role_name
        self.current_creds = None
        self.lease_id = None

    def get_credentials(self, ttl: str = '1h'):
        """
        Get temporary database credentials from Vault.

        Args:
            ttl: Time to live (e.g., '1h', '30m', '24h')

        Returns:
            Credentials dictionary
        """
        print(f"[{datetime.utcnow().isoformat()}] Requesting credentials from Vault")

        response = self.vault_client.secrets.database.generate_credentials(
            name=self.role_name,
            ttl=ttl
        )

        self.current_creds = {
            'username': response['data']['username'],
            'password': response['data']['password']
        }
        self.lease_id = response['lease_id']
        self.lease_duration = response['lease_duration']

        print(f"  Username: {self.current_creds['username']}")
        print(f"  Lease ID: {self.lease_id}")
        print(f"  Expires in: {self.lease_duration} seconds")

        return self.current_creds

    def renew_lease(self, increment: str = '1h'):
        """
        Renew credential lease to extend validity.

        Args:
            increment: Lease increment (e.g., '1h')
        """
        if not self.lease_id:
            raise ValueError("No active lease to renew")

        print(f"[{datetime.utcnow().isoformat()}] Renewing lease: {self.lease_id}")

        response = self.vault_client.sys.renew_lease(
            lease_id=self.lease_id,
            increment=increment
        )

        self.lease_duration = response['lease_duration']
        print(f"  Lease renewed, expires in: {self.lease_duration} seconds")

    def revoke_lease(self):
        """
        Revoke credential lease (immediately invalidate credentials).
        """
        if not self.lease_id:
            return

        print(f"[{datetime.utcnow().isoformat()}] Revoking lease: {self.lease_id}")

        self.vault_client.sys.revoke_lease(lease_id=self.lease_id)
        self.current_creds = None
        self.lease_id = None

        print("  Lease revoked, credentials invalidated")

    def connect_database(self, host: str, database: str):
        """
        Connect to database using current credentials.

        Args:
            host: Database host
            database: Database name

        Returns:
            Database connection
        """
        if not self.current_creds:
            self.get_credentials()

        print(f"[{datetime.utcnow().isoformat()}] Connecting to database")

        conn = psycopg2.connect(
            host=host,
            database=database,
            user=self.current_creds['username'],
            password=self.current_creds['password']
        )

        print("  Connected successfully")
        return conn


# Example usage
if __name__ == '__main__':
    # Configuration
    VAULT_URL = 'http://localhost:8200'
    VAULT_TOKEN = 'your-vault-token'
    ROLE_NAME = 'app-role'
    DB_HOST = 'localhost'
    DB_NAME = 'mydb'

    # Initialize client
    client = VaultDatabaseClient(VAULT_URL, VAULT_TOKEN, ROLE_NAME)

    try:
        # Get temporary credentials (valid for 1 hour)
        credentials = client.get_credentials(ttl='1h')

        # Connect to database
        conn = client.connect_database(DB_HOST, DB_NAME)

        # Execute query
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_user, current_timestamp;")
            user, timestamp = cursor.fetchone()
            print(f"\nQuery result:")
            print(f"  Current user: {user}")
            print(f"  Timestamp: {timestamp}")

        conn.close()

        # Simulate long-running application
        print("\nSimulating application work...")
        time.sleep(5)

        # Renew lease before expiration
        client.renew_lease(increment='1h')

        # Continue work
        conn = client.connect_database(DB_HOST, DB_NAME)
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"\nDatabase version: {version}")
        conn.close()

    finally:
        # Revoke credentials on application shutdown
        print("\nApplication shutting down...")
        client.revoke_lease()
        print("Credentials revoked")


# Advanced pattern: Automatic lease renewal
class AutoRenewingDatabaseClient(VaultDatabaseClient):
    """
    Database client with automatic lease renewal.
    """

    def __init__(self, vault_url: str, token: str, role_name: str):
        super().__init__(vault_url, token, role_name)
        self.renew_thread = None
        self.stop_renewal = False

    def start_auto_renewal(self, renew_before_seconds: int = 300):
        """
        Start automatic lease renewal.

        Args:
            renew_before_seconds: Renew lease this many seconds before expiration
        """
        import threading

        def renewal_loop():
            while not self.stop_renewal:
                if self.lease_id and self.lease_duration:
                    # Calculate sleep time
                    sleep_time = max(self.lease_duration - renew_before_seconds, 60)
                    print(f"[{datetime.utcnow().isoformat()}] Next renewal in {sleep_time}s")

                    time.sleep(sleep_time)

                    if not self.stop_renewal:
                        try:
                            self.renew_lease()
                        except Exception as e:
                            print(f"ERROR: Failed to renew lease: {e}")
                            # Get new credentials
                            self.get_credentials()

        self.renew_thread = threading.Thread(target=renewal_loop, daemon=True)
        self.renew_thread.start()
        print("Auto-renewal started")

    def stop_auto_renewal(self):
        """Stop automatic lease renewal."""
        self.stop_renewal = True
        if self.renew_thread:
            self.renew_thread.join(timeout=5)
        print("Auto-renewal stopped")


# Example with auto-renewal
if __name__ == '__main__' and False:  # Set to True to run
    client = AutoRenewingDatabaseClient(VAULT_URL, VAULT_TOKEN, ROLE_NAME)

    try:
        # Get initial credentials
        client.get_credentials(ttl='5m')  # Short TTL for demo

        # Start auto-renewal
        client.start_auto_renewal(renew_before_seconds=60)

        # Long-running application (credentials auto-renewed)
        for i in range(10):
            conn = client.connect_database(DB_HOST, DB_NAME)
            with conn.cursor() as cursor:
                cursor.execute("SELECT NOW();")
                print(f"Iteration {i+1}: {cursor.fetchone()[0]}")
            conn.close()
            time.sleep(30)

    finally:
        client.stop_auto_renewal()
        client.revoke_lease()
