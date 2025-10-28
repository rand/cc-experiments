#!/usr/bin/env python3
"""
GCP Secret Manager Rotation with Cloud Functions

Demonstrates:
- GCP Secret Manager secret rotation
- Cloud Function-based rotation handler
- Cloud Scheduler for automatic rotation
- Version management and rollback
- Integration with Cloud SQL

Prerequisites:
    pip install google-cloud-secret-manager google-cloud-scheduler pg8000

GCP Setup:
    # Enable APIs
    gcloud services enable secretmanager.googleapis.com
    gcloud services enable cloudscheduler.googleapis.com
    gcloud services enable cloudfunctions.googleapis.com

    # Create secret
    echo -n '{"username":"app_user","password":"initial_pass","host":"10.0.0.1","database":"mydb"}' | \\
        gcloud secrets create db-credentials --data-file=-

    # Grant Cloud Function access
    gcloud secrets add-iam-policy-binding db-credentials \\
        --member="serviceAccount:rotation-function@project.iam.gserviceaccount.com" \\
        --role="roles/secretmanager.secretVersionManager"
"""

import base64
import json
import secrets
import pg8000
from datetime import datetime, timedelta
from typing import Dict, Any
from google.cloud import secretmanager
from google.cloud import scheduler_v1


class GCPSecretRotation:
    """
    GCP Secret Manager rotation implementation.
    """

    def __init__(self, project_id: str):
        """
        Initialize GCP clients.

        Args:
            project_id: GCP project ID
        """
        self.project_id = project_id
        self.sm_client = secretmanager.SecretManagerServiceClient()

    def rotate_database_secret(self, secret_id: str) -> Dict[str, Any]:
        """
        Rotate database credentials in Secret Manager.

        Args:
            secret_id: Secret name (e.g., 'db-credentials')

        Returns:
            Rotation result with new version info
        """
        print(f"[{datetime.utcnow().isoformat()}] Starting rotation for: {secret_id}")

        # Step 1: Get current secret
        current_secret = self._get_current_secret(secret_id)
        print(f"  Current version: {current_secret['version']}")

        # Step 2: Generate new password
        new_password = self._generate_password()
        new_secret = current_secret['data'].copy()
        new_secret['password'] = new_password
        print(f"  Generated new password (length: {len(new_password)})")

        # Step 3: Update database with new password
        self._update_database_password(
            host=current_secret['data']['host'],
            database=current_secret['data']['database'],
            username=current_secret['data']['username'],
            current_password=current_secret['data']['password'],
            new_password=new_password
        )
        print("  Database password updated")

        # Step 4: Test new credentials
        self._test_credentials(
            host=new_secret['host'],
            database=new_secret['database'],
            username=new_secret['username'],
            password=new_secret['password']
        )
        print("  New credentials validated")

        # Step 5: Create new secret version
        new_version = self._add_secret_version(secret_id, new_secret)
        print(f"  New version created: {new_version}")

        # Step 6: Disable old versions (keep last 3)
        self._cleanup_old_versions(secret_id, keep_count=3)
        print("  Old versions cleaned up")

        return {
            'secret_id': secret_id,
            'old_version': current_secret['version'],
            'new_version': new_version,
            'rotated_at': datetime.utcnow().isoformat(),
            'status': 'success'
        }

    def _get_current_secret(self, secret_id: str) -> Dict[str, Any]:
        """Get current secret version."""
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
        response = self.sm_client.access_secret_version(request={"name": name})

        return {
            'version': response.name.split('/')[-1],
            'data': json.loads(response.payload.data.decode('UTF-8'))
        }

    def _generate_password(self, length: int = 32) -> str:
        """Generate secure random password."""
        # Use URL-safe characters (alphanumeric + - and _)
        return secrets.token_urlsafe(length)

    def _update_database_password(self, host: str, database: str, username: str,
                                   current_password: str, new_password: str):
        """Update database user password."""
        # Connect with current credentials
        conn = pg8000.connect(
            host=host,
            database=database,
            user=username,
            password=current_password,
            timeout=10
        )

        try:
            # Update password (PostgreSQL)
            cursor = conn.cursor()
            cursor.execute(
                f"ALTER USER {username} WITH PASSWORD %s",
                (new_password,)
            )
            conn.commit()

        finally:
            conn.close()

    def _test_credentials(self, host: str, database: str, username: str, password: str):
        """Test new credentials work."""
        conn = pg8000.connect(
            host=host,
            database=database,
            user=username,
            password=password,
            timeout=10
        )

        # Execute test query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()

        conn.close()

        if result[0] != 1:
            raise RuntimeError("Credential test failed")

    def _add_secret_version(self, secret_id: str, secret_data: Dict[str, Any]) -> str:
        """Add new secret version."""
        parent = f"projects/{self.project_id}/secrets/{secret_id}"

        payload = json.dumps(secret_data).encode('UTF-8')
        response = self.sm_client.add_secret_version(
            request={
                "parent": parent,
                "payload": {"data": payload}
            }
        )

        return response.name.split('/')[-1]

    def _cleanup_old_versions(self, secret_id: str, keep_count: int = 3):
        """Disable old secret versions (keep most recent N)."""
        parent = f"projects/{self.project_id}/secrets/{secret_id}"

        # List all versions
        versions = self.sm_client.list_secret_versions(request={"parent": parent})
        version_list = []

        for version in versions:
            if version.state == secretmanager.SecretVersion.State.ENABLED:
                version_list.append({
                    'name': version.name,
                    'created': version.create_time
                })

        # Sort by creation time (newest first)
        version_list.sort(key=lambda x: x['created'], reverse=True)

        # Disable old versions
        for version in version_list[keep_count:]:
            self.sm_client.disable_secret_version(
                request={"name": version['name']}
            )
            print(f"    Disabled: {version['name'].split('/')[-1]}")

    def rollback_to_version(self, secret_id: str, version_id: str):
        """
        Rollback to previous secret version.

        Args:
            secret_id: Secret name
            version_id: Version to rollback to
        """
        print(f"[{datetime.utcnow().isoformat()}] Rolling back to version: {version_id}")

        # Get target version
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"
        version = self.sm_client.get_secret_version(request={"name": name})

        if version.state != secretmanager.SecretVersion.State.ENABLED:
            # Re-enable version
            self.sm_client.enable_secret_version(request={"name": name})
            print(f"  Enabled version: {version_id}")

        secret_data = json.loads(version.payload.data.decode('UTF-8'))

        # Update database with rollback credentials
        self._test_credentials(
            host=secret_data['host'],
            database=secret_data['database'],
            username=secret_data['username'],
            password=secret_data['password']
        )

        print("  Rollback validated")


# Cloud Function handler
def rotate_secret_handler(request):
    """
    Cloud Function entry point for secret rotation.

    Triggered by Cloud Scheduler or HTTP request.

    Request body:
    {
        "secret_id": "db-credentials",
        "project_id": "my-project"
    }
    """
    try:
        # Parse request
        request_json = request.get_json(silent=True)
        if not request_json:
            return {'error': 'Invalid request'}, 400

        secret_id = request_json.get('secret_id')
        project_id = request_json.get('project_id')

        if not secret_id or not project_id:
            return {'error': 'Missing required fields'}, 400

        # Perform rotation
        rotator = GCPSecretRotation(project_id)
        result = rotator.rotate_database_secret(secret_id)

        return result, 200

    except Exception as e:
        print(f"ERROR: Rotation failed: {e}")
        return {'error': str(e)}, 500


class RotationScheduler:
    """
    Manage automatic rotation schedule with Cloud Scheduler.
    """

    def __init__(self, project_id: str, location: str = 'us-central1'):
        """
        Initialize scheduler client.

        Args:
            project_id: GCP project ID
            location: Cloud Scheduler location
        """
        self.project_id = project_id
        self.location = location
        self.client = scheduler_v1.CloudSchedulerClient()

    def create_rotation_schedule(self, secret_id: str, function_url: str,
                                  rotation_days: int = 90):
        """
        Create Cloud Scheduler job for automatic rotation.

        Args:
            secret_id: Secret to rotate
            function_url: Cloud Function URL
            rotation_days: Rotation interval (days)
        """
        parent = f"projects/{self.project_id}/locations/{self.location}"
        job_name = f"{parent}/jobs/rotate-{secret_id}"

        # Create job payload
        payload = json.dumps({
            'secret_id': secret_id,
            'project_id': self.project_id
        })

        # Schedule (cron expression for every N days at 2 AM UTC)
        schedule = f"0 2 */{rotation_days} * *"

        job = scheduler_v1.Job(
            name=job_name,
            description=f"Rotate secret: {secret_id}",
            schedule=schedule,
            time_zone="UTC",
            http_target=scheduler_v1.HttpTarget(
                uri=function_url,
                http_method=scheduler_v1.HttpMethod.POST,
                headers={'Content-Type': 'application/json'},
                body=payload.encode('utf-8')
            )
        )

        try:
            # Create job
            created_job = self.client.create_job(
                request={"parent": parent, "job": job}
            )
            print(f"Created rotation schedule: {created_job.name}")
            print(f"  Schedule: Every {rotation_days} days at 2 AM UTC")

        except Exception as e:
            print(f"Failed to create schedule: {e}")
            raise


# Example usage
if __name__ == '__main__':
    PROJECT_ID = 'my-gcp-project'
    SECRET_ID = 'db-credentials'

    # Initialize rotator
    rotator = GCPSecretRotation(PROJECT_ID)

    # Manual rotation
    result = rotator.rotate_database_secret(SECRET_ID)
    print(f"\nRotation result: {json.dumps(result, indent=2)}")

    # Setup automatic rotation (uncomment to activate)
    # scheduler = RotationScheduler(PROJECT_ID)
    # scheduler.create_rotation_schedule(
    #     secret_id=SECRET_ID,
    #     function_url='https://us-central1-my-project.cloudfunctions.net/rotate-secret',
    #     rotation_days=90
    # )

    # Rollback example (if needed)
    # rotator.rollback_to_version(SECRET_ID, version_id='2')
