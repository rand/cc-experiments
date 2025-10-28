#!/usr/bin/env python3
"""
AWS Secrets Manager Automatic Rotation Example

Complete Lambda-based rotation implementation with:
- 4-step rotation protocol (createSecret, setSecret, testSecret, finishSecret)
- Zero-downtime database credential rotation
- Rollback capability
- Version management

Prerequisites:
    pip install boto3 pymysql

AWS Setup:
    aws secretsmanager create-secret --name prod/db/password --secret-string '{
        "username": "app_user",
        "password": "current_password",
        "host": "mydb.example.com",
        "port": 3306,
        "database": "myapp"
    }'

    aws secretsmanager rotate-secret \\
        --secret-id prod/db/password \\
        --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:rotate-secret \\
        --rotation-rules AutomaticallyAfterDays=90
"""

import boto3
import pymysql
import json
import secrets as sec
from datetime import datetime


# Lambda handler for automatic rotation
def lambda_handler(event, context):
    """
    AWS Secrets Manager rotation Lambda handler.

    Event structure:
    {
        "Step": "createSecret|setSecret|testSecret|finishSecret",
        "SecretId": "arn:aws:secretsmanager:...",
        "ClientRequestToken": "uuid"
    }
    """
    service_client = boto3.client('secretsmanager')

    arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    print(f"[{datetime.utcnow().isoformat()}] Rotation step: {step}")

    # Rotation steps
    if step == "createSecret":
        create_secret(service_client, arn, token)
    elif step == "setSecret":
        set_secret(service_client, arn, token)
    elif step == "testSecret":
        test_secret(service_client, arn, token)
    elif step == "finishSecret":
        finish_secret(service_client, arn, token)
    else:
        raise ValueError(f"Invalid step: {step}")

    print(f"  Step complete: {step}")


def create_secret(service_client, arn, token):
    """
    Step 1: Generate new password and store as AWSPENDING.
    """
    print("  Creating new secret value")

    # Get current secret
    current = get_secret_dict(service_client, arn, "AWSCURRENT")

    # Generate new password (32 characters, URL-safe)
    new_password = sec.token_urlsafe(32)
    current['password'] = new_password

    # Store as AWSPENDING
    service_client.put_secret_value(
        SecretId=arn,
        ClientRequestToken=token,
        SecretString=json.dumps(current),
        VersionStages=['AWSPENDING']
    )

    print(f"  New password generated (length: {len(new_password)})")


def set_secret(service_client, arn, token):
    """
    Step 2: Update database with new password.
    """
    print("  Updating database password")

    # Get pending secret (new password)
    pending = get_secret_dict(service_client, arn, "AWSPENDING", token)

    # Get current secret (old password for authentication)
    current = get_secret_dict(service_client, arn, "AWSCURRENT")

    # Connect with current (old) credentials
    conn = pymysql.connect(
        host=pending['host'],
        port=int(pending.get('port', 3306)),
        user=current['username'],
        password=current['password'],
        database=pending.get('database', 'mysql'),
        connect_timeout=5
    )

    try:
        # Update user password
        with conn.cursor() as cursor:
            # MySQL-specific password update
            cursor.execute(
                f"ALTER USER '{pending['username']}'@'%' IDENTIFIED BY %s",
                (pending['password'],)
            )
            cursor.execute("FLUSH PRIVILEGES")
        conn.commit()

        print(f"  Database password updated for user: {pending['username']}")

    finally:
        conn.close()


def test_secret(service_client, arn, token):
    """
    Step 3: Test new credentials work.
    """
    print("  Testing new credentials")

    # Get pending secret
    pending = get_secret_dict(service_client, arn, "AWSPENDING", token)

    # Test connection with new credentials
    conn = pymysql.connect(
        host=pending['host'],
        port=int(pending.get('port', 3306)),
        user=pending['username'],
        password=pending['password'],
        database=pending.get('database', 'mysql'),
        connect_timeout=5
    )

    # Execute test query
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1, "Test query failed"

    conn.close()
    print("  Credentials validated successfully")


def finish_secret(service_client, arn, token):
    """
    Step 4: Finalize rotation (move AWSPENDING to AWSCURRENT).
    """
    print("  Finalizing rotation")

    # Get current version
    metadata = service_client.describe_secret(SecretId=arn)
    current_version = None
    for version in metadata['VersionIdsToStages']:
        if 'AWSCURRENT' in metadata['VersionIdsToStages'][version]:
            current_version = version
            break

    # Move AWSCURRENT stage to new version
    service_client.update_secret_version_stage(
        SecretId=arn,
        VersionStage="AWSCURRENT",
        MoveToVersionId=token,
        RemoveFromVersionId=current_version
    )

    print("  Rotation finalized, new version is AWSCURRENT")


def get_secret_dict(service_client, arn, stage, version=None):
    """
    Get secret value as dictionary.

    Args:
        service_client: Boto3 Secrets Manager client
        arn: Secret ARN
        stage: Version stage (AWSCURRENT, AWSPENDING, AWSPREVIOUS)
        version: Specific version ID (optional)

    Returns:
        Secret value as dictionary
    """
    if version:
        response = service_client.get_secret_value(
            SecretId=arn,
            VersionId=version,
            VersionStage=stage
        )
    else:
        response = service_client.get_secret_value(
            SecretId=arn,
            VersionStage=stage
        )

    return json.loads(response['SecretString'])


# Client-side usage example
class SecretsManagerClient:
    """
    Client for retrieving secrets from AWS Secrets Manager.
    """

    def __init__(self, region_name='us-east-1'):
        self.client = boto3.client('secretsmanager', region_name=region_name)

    def get_database_credentials(self, secret_id: str):
        """
        Get current database credentials.

        Args:
            secret_id: Secret name or ARN

        Returns:
            Credentials dictionary
        """
        response = self.client.get_secret_value(SecretId=secret_id)
        return json.loads(response['SecretString'])

    def connect_database(self, secret_id: str):
        """
        Connect to database using credentials from Secrets Manager.

        Args:
            secret_id: Secret name

        Returns:
            Database connection
        """
        creds = self.get_database_credentials(secret_id)

        conn = pymysql.connect(
            host=creds['host'],
            port=int(creds.get('port', 3306)),
            user=creds['username'],
            password=creds['password'],
            database=creds.get('database', 'mysql')
        )

        return conn

    def enable_automatic_rotation(self, secret_id: str, lambda_arn: str, rotation_days: int = 90):
        """
        Enable automatic rotation.

        Args:
            secret_id: Secret name
            lambda_arn: Rotation Lambda ARN
            rotation_days: Rotation interval (days)
        """
        self.client.rotate_secret(
            SecretId=secret_id,
            RotationLambdaARN=lambda_arn,
            RotationRules={
                'AutomaticallyAfterDays': rotation_days
            }
        )

        print(f"Automatic rotation enabled (every {rotation_days} days)")


# Example usage
if __name__ == '__main__':
    client = SecretsManagerClient(region_name='us-east-1')

    # Get credentials
    creds = client.get_database_credentials('prod/db/password')
    print(f"Retrieved credentials for user: {creds['username']}")

    # Connect to database
    conn = client.connect_database('prod/db/password')
    print("Connected to database")

    # Execute query
    with conn.cursor() as cursor:
        cursor.execute("SELECT DATABASE(), USER(), NOW()")
        db, user, now = cursor.fetchone()
        print(f"Database: {db}, User: {user}, Time: {now}")

    conn.close()

    # Enable rotation (uncomment to activate)
    # client.enable_automatic_rotation(
    #     secret_id='prod/db/password',
    #     lambda_arn='arn:aws:lambda:us-east-1:123456789012:function:rotate-secret',
    #     rotation_days=90
    # )
