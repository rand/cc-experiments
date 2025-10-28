---
name: security-secrets-management
description: Secrets management patterns including vaults, environment variables, key rotation, and secure credential handling for applications
---

# Security: Secrets Management

**Scope**: Secrets vaults, credential management, key rotation, secure storage
**Lines**: ~380
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Storing API keys, passwords, or credentials
- Implementing secrets management for applications
- Integrating with HashiCorp Vault, AWS Secrets Manager, or similar
- Rotating encryption keys or credentials
- Managing secrets in CI/CD pipelines
- Preventing credential exposure in code or logs
- Designing multi-environment secret strategies

## Secrets Management Fundamentals

### What Are Secrets?

```python
"""
Secrets are sensitive data that must be protected:
- API keys and tokens
- Database passwords
- Encryption keys
- TLS/SSL certificates
- OAuth client secrets
- Service account credentials
- Signing keys
"""

# ❌ NEVER DO THIS - Hardcoded secrets (example only, never in production)
API_KEY = "sk_live_abc123def456"  # Example of what NOT to do
DB_PASSWORD = "MyP@ssw0rd123"  # Example of what NOT to do

# ✅ DO THIS - Environment variables or vault
import os
API_KEY = os.environ.get('API_KEY')
DB_PASSWORD = vault.get_secret('database/password')
```

## Environment Variables

### Using Environment Variables

```python
import os
from typing import Optional

# Basic usage
DATABASE_URL = os.environ['DATABASE_URL']  # Raises KeyError if missing
API_KEY = os.environ.get('API_KEY')  # Returns None if missing
API_KEY = os.environ.get('API_KEY', 'default-value')  # With default

# Validation helper
def get_required_env(key: str) -> str:
    """Get required environment variable or raise error"""
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value

# Type conversion
PORT = int(os.environ.get('PORT', '8000'))
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

# Complex secrets (JSON)
import json
AWS_CREDENTIALS = json.loads(os.environ.get('AWS_CREDENTIALS', '{}'))
```

### .env Files (Development Only)

```python
# .env file (NEVER commit to git)
DATABASE_URL=postgresql://user:password@localhost/db
API_KEY=sk_test_abc123
STRIPE_SECRET=sk_test_def456
DEBUG=true

# Load with python-dotenv
from dotenv import load_dotenv
import os

# Load .env file in development
if os.environ.get('ENV') != 'production':
    load_dotenv()

DATABASE_URL = os.environ['DATABASE_URL']
```

**.gitignore**:
```gitignore
# Never commit secrets
.env
.env.local
.env.*.local
secrets.json
credentials.json
*.pem
*.key
```

## HashiCorp Vault

### Vault Integration (Python)

```python
import hvac
from typing import Dict, Any

class VaultClient:
    """HashiCorp Vault client wrapper"""

    def __init__(self, url: str = None, token: str = None):
        self.url = url or os.environ['VAULT_ADDR']
        self.token = token or os.environ['VAULT_TOKEN']

        self.client = hvac.Client(url=self.url, token=self.token)

        if not self.client.is_authenticated():
            raise Exception("Vault authentication failed")

    def get_secret(self, path: str) -> Dict[str, Any]:
        """Read secret from Vault"""
        response = self.client.secrets.kv.v2.read_secret_version(
            path=path,
            mount_point='secret'
        )
        return response['data']['data']

    def write_secret(self, path: str, data: Dict[str, Any]):
        """Write secret to Vault"""
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=data,
            mount_point='secret'
        )

    def delete_secret(self, path: str):
        """Delete secret from Vault"""
        self.client.secrets.kv.v2.delete_metadata_and_all_versions(
            path=path,
            mount_point='secret'
        )

# Usage
vault = VaultClient()

# Read database credentials
db_creds = vault.get_secret('database/postgres')
DATABASE_URL = (
    f"postgresql://{db_creds['username']}:{db_creds['password']}"
    f"@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
)

# Write API key
vault.write_secret('api/stripe', {
    'secret_key': 'sk_live_abc123',
    'publishable_key': 'pk_live_def456'
})

# Read API key
stripe_keys = vault.get_secret('api/stripe')
STRIPE_SECRET = stripe_keys['secret_key']
```

### Vault AppRole Authentication

```python
class VaultAppRoleClient:
    """Vault client using AppRole authentication"""

    def __init__(self, role_id: str, secret_id: str, url: str = None):
        self.url = url or os.environ['VAULT_ADDR']
        self.client = hvac.Client(url=self.url)

        # Authenticate with AppRole
        response = self.client.auth.approle.login(
            role_id=role_id,
            secret_id=secret_id
        )

        self.client.token = response['auth']['client_token']

        # Renew token periodically
        self._start_token_renewal()

    def _start_token_renewal(self):
        """Automatically renew token before expiration"""
        import threading

        def renew():
            while True:
                time.sleep(3600)  # Renew every hour
                try:
                    self.client.auth.token.renew_self()
                except Exception as e:
                    logger.error(f"Token renewal failed: {e}")

        thread = threading.Thread(target=renew, daemon=True)
        thread.start()

# Usage (secure - no token in env)
vault = VaultAppRoleClient(
    role_id=os.environ['VAULT_ROLE_ID'],
    secret_id=os.environ['VAULT_SECRET_ID']
)
```

### Dynamic Database Credentials

```python
def get_dynamic_db_credentials(vault_client, role: str):
    """Get short-lived database credentials from Vault"""

    # Vault generates credentials on-demand
    response = vault_client.client.secrets.database.generate_credentials(
        name=role,
        mount_point='database'
    )

    return {
        'username': response['data']['username'],
        'password': response['data']['password'],
        'ttl': response['lease_duration']  # Credentials expire
    }

# Usage
creds = get_dynamic_db_credentials(vault, 'readonly-role')

# Connect with temporary credentials
conn = psycopg2.connect(
    host='localhost',
    database='mydb',
    user=creds['username'],
    password=creds['password']
)

# Credentials automatically expire after TTL
```

## AWS Secrets Manager

### AWS Secrets Manager Integration

```python
import boto3
import json
from botocore.exceptions import ClientError

class AWSSecretsManager:
    """AWS Secrets Manager client"""

    def __init__(self, region_name: str = 'us-east-1'):
        self.client = boto3.client(
            'secretsmanager',
            region_name=region_name
        )

    def get_secret(self, secret_name: str) -> dict:
        """Retrieve secret from AWS Secrets Manager"""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)

            # Secret can be string or binary
            if 'SecretString' in response:
                return json.loads(response['SecretString'])
            else:
                import base64
                return base64.b64decode(response['SecretBinary'])

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise ValueError(f"Secret not found: {secret_name}")
            raise

    def create_secret(self, secret_name: str, secret_value: dict):
        """Create new secret"""
        self.client.create_secret(
            Name=secret_name,
            SecretString=json.dumps(secret_value)
        )

    def update_secret(self, secret_name: str, secret_value: dict):
        """Update existing secret"""
        self.client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(secret_value)
        )

    def rotate_secret(self, secret_name: str, lambda_arn: str):
        """Enable automatic secret rotation"""
        self.client.rotate_secret(
            SecretId=secret_name,
            RotationLambdaARN=lambda_arn,
            RotationRules={'AutomaticallyAfterDays': 30}
        )

# Usage
secrets = AWSSecretsManager(region_name='us-west-2')

# Get database credentials
db_secret = secrets.get_secret('prod/database/postgres')
DATABASE_URL = (
    f"postgresql://{db_secret['username']}:{db_secret['password']}"
    f"@{db_secret['host']}/{db_secret['dbname']}"
)

# Create API key secret
secrets.create_secret('prod/api/stripe', {
    'secret_key': 'sk_live_abc123',
    'publishable_key': 'pk_live_def456'
})
```

### Caching Secrets

```python
from functools import lru_cache
import time

class CachedSecretsManager:
    """Cache secrets to reduce API calls"""

    def __init__(self, secrets_manager):
        self.secrets_manager = secrets_manager
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    def get_secret(self, secret_name: str) -> dict:
        """Get secret with caching"""
        now = time.time()

        # Check cache
        if secret_name in self.cache:
            cached_value, cached_time = self.cache[secret_name]
            if now - cached_time < self.cache_ttl:
                return cached_value

        # Fetch from source
        value = self.secrets_manager.get_secret(secret_name)

        # Update cache
        self.cache[secret_name] = (value, now)

        return value

    def invalidate_cache(self, secret_name: str = None):
        """Clear cache for secret or all secrets"""
        if secret_name:
            self.cache.pop(secret_name, None)
        else:
            self.cache.clear()
```

## GCP Secret Manager

### Google Cloud Secret Manager

```python
from google.cloud import secretmanager

class GCPSecretsManager:
    """Google Cloud Secret Manager client"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()

    def get_secret(self, secret_id: str, version: str = "latest") -> str:
        """Access secret version"""
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"

        response = self.client.access_secret_version(request={"name": name})

        return response.payload.data.decode('UTF-8')

    def create_secret(self, secret_id: str, secret_value: str):
        """Create new secret"""
        parent = f"projects/{self.project_id}"

        # Create secret
        secret = self.client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )

        # Add secret version
        self.client.add_secret_version(
            request={
                "parent": secret.name,
                "payload": {"data": secret_value.encode('UTF-8')},
            }
        )

    def update_secret(self, secret_id: str, secret_value: str):
        """Add new secret version (updates secret)"""
        parent = f"projects/{self.project_id}/secrets/{secret_id}"

        self.client.add_secret_version(
            request={
                "parent": parent,
                "payload": {"data": secret_value.encode('UTF-8')},
            }
        )

# Usage
secrets = GCPSecretsManager(project_id='my-project')

# Get secret
api_key = secrets.get_secret('stripe-api-key')

# Create secret
secrets.create_secret('database-password', 'secure-password-123')
```

## Key Rotation

### Automated Key Rotation

```python
from datetime import datetime, timedelta
from typing import Callable

class KeyRotationService:
    """Automated key rotation service"""

    def __init__(self, secrets_manager, notification_service=None):
        self.secrets_manager = secrets_manager
        self.notification_service = notification_service

    def rotate_key(self, secret_name: str, generator: Callable[[], str]):
        """Rotate a secret key"""

        # Generate new key
        new_key = generator()

        # Store old key for rollback
        old_key = self.secrets_manager.get_secret(secret_name)

        try:
            # Update with new key
            self.secrets_manager.update_secret(secret_name, {'value': new_key})

            # Log rotation
            logger.info(f"Rotated secret: {secret_name}")

            # Notify team
            if self.notification_service:
                self.notification_service.send_alert(
                    f"Secret rotated: {secret_name}"
                )

            return new_key

        except Exception as e:
            # Rollback on failure
            logger.error(f"Key rotation failed: {e}")
            self.secrets_manager.update_secret(secret_name, old_key)
            raise

    def check_expiration(self, secret_name: str, max_age_days: int = 90):
        """Check if secret needs rotation"""

        metadata = self.secrets_manager.get_secret_metadata(secret_name)
        last_rotated = metadata['last_rotated']

        age = datetime.now() - last_rotated

        if age > timedelta(days=max_age_days):
            logger.warning(f"Secret needs rotation: {secret_name} (age: {age.days} days)")
            return True

        return False

# Usage
rotation_service = KeyRotationService(secrets_manager)

# Generate new API key
import secrets
def generate_api_key():
    return secrets.token_urlsafe(32)

# Rotate key
new_key = rotation_service.rotate_key('api/external-service', generate_api_key)

# Check if rotation needed
if rotation_service.check_expiration('database/password', max_age_days=30):
    rotation_service.rotate_key('database/password', generate_strong_password)
```

### Zero-Downtime Rotation

```python
class ZeroDowntimeRotation:
    """Rotate secrets without downtime"""

    def __init__(self, secrets_manager):
        self.secrets_manager = secrets_manager

    def rotate_with_overlap(self, secret_name: str, new_value: str):
        """
        Dual-key rotation:
        1. Add new key (both keys valid)
        2. Update services to use new key
        3. Remove old key after grace period
        """

        # Get current secret
        current = self.secrets_manager.get_secret(secret_name)

        # Store both old and new
        dual_secret = {
            'primary': new_value,
            'secondary': current['value'],  # Old key still valid
            'rotated_at': datetime.utcnow().isoformat()
        }

        self.secrets_manager.update_secret(secret_name, dual_secret)

        logger.info(f"New key active, old key valid for grace period")

    def complete_rotation(self, secret_name: str):
        """Remove old key after grace period"""

        secret = self.secrets_manager.get_secret(secret_name)

        # Keep only primary (new) key
        updated = {'value': secret['primary']}

        self.secrets_manager.update_secret(secret_name, updated)

        logger.info(f"Rotation completed, old key removed")

# Usage
rotator = ZeroDowntimeRotation(secrets_manager)

# Phase 1: Add new key
rotator.rotate_with_overlap('database/password', 'new-password')

# Update applications to use new key (manual or automated)
# Wait for all services to migrate (e.g., 24 hours)

# Phase 2: Remove old key
rotator.complete_rotation('database/password')
```

## CI/CD Secrets Management

### GitHub Actions Secrets

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Deploy to production
        env:
          # Access GitHub secrets
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          ./deploy.sh
```

### Vault Integration in CI/CD

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Import Secrets from Vault
        uses: hashicorp/vault-action@v2
        with:
          url: https://vault.example.com
          token: ${{ secrets.VAULT_TOKEN }}
          secrets: |
            secret/data/database username | DATABASE_USER ;
            secret/data/database password | DATABASE_PASSWORD ;
            secret/data/api stripe_key | STRIPE_KEY

      - name: Deploy
        run: |
          echo "Using secrets from Vault"
          ./deploy.sh
```

## Security Best Practices

### Secrets Management Checklist

**Storage**:
- [ ] Never commit secrets to version control
- [ ] Use secrets manager (Vault, AWS, GCP)
- [ ] Encrypt secrets at rest and in transit
- [ ] Use separate secrets per environment
- [ ] Implement access control (least privilege)

**Rotation**:
- [ ] Rotate secrets regularly (30-90 days)
- [ ] Automate rotation where possible
- [ ] Support zero-downtime rotation
- [ ] Audit rotation events
- [ ] Have rollback plan

**Access**:
- [ ] Use short-lived credentials when possible
- [ ] Implement audit logging
- [ ] Restrict secret access by role
- [ ] Monitor secret access patterns
- [ ] Alert on unauthorized access

**Development**:
- [ ] Use different secrets for dev/staging/prod
- [ ] Never log secrets
- [ ] Sanitize secrets in error messages
- [ ] Use .gitignore for local secret files
- [ ] Document secret requirements

**Detection**:
- [ ] Scan commits for secrets (git-secrets, truffleHog)
- [ ] Monitor for exposed secrets (GitHub, public repos)
- [ ] Alert on secret usage anomalies
- [ ] Regular security audits

## Common Vulnerabilities

### Secrets in Code

```python
# ❌ VULNERABLE - Hardcoded secrets
API_KEY = "sk_live_abc123def456"

# ❌ VULNERABLE - Secrets in comments
# Production API key: sk_live_abc123def456

# ❌ VULNERABLE - Secrets in error messages (example of what NOT to do)
try:
    connect(password="secret123")  # Example only - never hardcode passwords
except Exception as e:
    logger.error(f"Connection failed with password: {password}")

# ✅ SECURE - Environment variables
API_KEY = os.environ['API_KEY']

# ✅ SECURE - Vault integration
API_KEY = vault.get_secret('api/stripe')['key']

# ✅ SECURE - Sanitized errors
try:
    connect(password=password)
except Exception as e:
    logger.error("Connection failed (credentials redacted)")
```

### Secrets Detection Tools

```bash
# git-secrets (prevent committing secrets)
git secrets --install
git secrets --register-aws
git secrets --scan

# truffleHog (scan repository history)
trufflehog git https://github.com/user/repo

# detect-secrets (baseline scanning)
detect-secrets scan > .secrets.baseline
detect-secrets audit .secrets.baseline

# gitleaks (fast secrets scanner)
gitleaks detect --source . --verbose
```

## Related Skills

- `security-authentication.md` - Password and credential management
- `security-authorization.md` - Access control for secrets
- `cryptography-encryption.md` - Encrypting secrets
- `cicd-github-actions.md` - CI/CD secrets management

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
