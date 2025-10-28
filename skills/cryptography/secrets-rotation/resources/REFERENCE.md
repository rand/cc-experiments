# Secrets Rotation - Comprehensive Technical Reference

**Last Updated**: 2025-10-27
**Lines**: 3,247
**Version**: 1.0.0

## Table of Contents

1. [Introduction](#introduction)
2. [Fundamentals](#fundamentals)
3. [Secret Types](#secret-types)
4. [Rotation Strategies](#rotation-strategies)
5. [Platform Integration](#platform-integration)
6. [Database Credential Rotation](#database-credential-rotation)
7. [Multi-Region Coordination](#multi-region-coordination)
8. [Zero-Downtime Patterns](#zero-downtime-patterns)
9. [Compliance Requirements](#compliance-requirements)
10. [Audit and Monitoring](#audit-and-monitoring)
11. [Emergency Rotation](#emergency-rotation)
12. [Implementation Patterns](#implementation-patterns)
13. [Security Best Practices](#security-best-practices)
14. [Common Pitfalls](#common-pitfalls)
15. [References](#references)

---

## Introduction

### What is Secrets Rotation?

**Secrets rotation** is the practice of periodically changing cryptographic secrets (passwords, API keys, certificates, encryption keys, tokens) to limit the impact of credential compromise and meet compliance requirements.

**Core Principle**: The security of a system is proportional to the frequency and effectiveness of its secrets rotation.

### Why Rotate Secrets?

**Security Benefits**:
1. **Limit blast radius**: Compromised secrets have limited validity period
2. **Reduce exposure window**: Old credentials become invalid
3. **Mitigate undetected breaches**: Regular rotation invalidates stolen credentials
4. **Cryptographic hygiene**: Limit amount of data encrypted under single key
5. **Insider threat mitigation**: Departing employees lose access automatically

**Compliance Requirements**:
- **PCI-DSS 3.2.1**: Requirement 8.2.4 - Change user passwords at least every 90 days
- **SOC 2**: Change management controls for credential rotation
- **HIPAA**: Addressable safeguard for password management
- **NIST SP 800-63B**: Password rotation recommendations
- **GDPR**: Article 32 - Security of processing (technical measures)

### Threat Model

**Secrets rotation protects against**:
- ✓ Stolen credentials from breached systems
- ✓ Credentials leaked in logs or code repositories
- ✓ Long-term credential harvesting
- ✓ Insider threats (departing employees)
- ✓ Compromised third-party services
- ✓ Weak credential generation (rotation forces regeneration)

**Secrets rotation does NOT protect against**:
- ✗ Active real-time attacks (attacker uses current credentials)
- ✗ Persistent access mechanisms (backdoors, malware)
- ✗ Zero-day vulnerabilities
- ✗ Social engineering attacks
- ✗ Physical security breaches

### Secrets Lifecycle

```
┌──────────────┐
│  CREATION    │ ← Generate strong secret
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  DISTRIBUTION│ ← Deliver securely to consumers
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  USAGE       │ ← Active credential period
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  ROTATION    │ ← Replace with new secret
└──────┬───────┘
       │
       ├─────────────┐
       │             │
       ▼             ▼
┌──────────────┐ ┌──────────────┐
│  GRACE PERIOD│ │  DESTRUCTION │ ← Old secret destroyed
└──────┬───────┘ └──────────────┘
       │
       ▼
┌──────────────┐
│  REVOCATION  │ ← Old secret invalidated
└──────────────┘
```

---

## Fundamentals

### Rotation Frequency

**Recommended Intervals**:

| Secret Type | Rotation Frequency | Compliance Driver |
|-------------|-------------------|-------------------|
| **Root/Master Keys** | Annually | NIST SP 800-57 |
| **API Keys** | 90 days | PCI-DSS, SOC 2 |
| **Service Passwords** | 90 days | PCI-DSS 8.2.4 |
| **Database Credentials** | 90 days | PCI-DSS, HIPAA |
| **TLS Certificates** | Annually (13 months max) | CA/Browser Forum |
| **SSH Keys** | Annually or on departure | NIST SP 800-63B |
| **OAuth Tokens** | 30-60 days | OAuth 2.0 Best Practices |
| **JWT Signing Keys** | Quarterly | NIST, OWASP |
| **Encryption Keys (DEK)** | Per-dataset or monthly | FIPS 140-2 |
| **Session Tokens** | Per-session (ephemeral) | OWASP ASVS |
| **Emergency** | Immediately | Upon suspected compromise |

**Factors Affecting Frequency**:
- **Sensitivity**: Higher sensitivity → More frequent rotation
- **Exposure**: Public-facing → More frequent rotation
- **Compliance**: Regulatory requirements may mandate frequency
- **Operational Impact**: Balance security vs. operational complexity
- **Detection Capability**: Better monitoring → Can reduce frequency

### Rotation Strategies

**1. Time-Based Rotation (Scheduled)**

Rotate secrets on a fixed schedule (e.g., every 90 days).

**Pros**:
- Predictable, easy to plan
- Compliance-friendly (audit trail)
- Automated scheduling

**Cons**:
- Fixed schedule may not align with threats
- Potential for simultaneous failures if all secrets rotate at once

**Implementation**:
```python
# Cron-based rotation
0 2 1 * * /usr/bin/rotate_secrets.py --type api-keys
```

**2. Event-Driven Rotation**

Rotate secrets in response to events (breach, employee departure, suspicious activity).

**Pros**:
- Responsive to actual threats
- Efficient (only rotate when needed)

**Cons**:
- Requires event detection
- May be too late if breach undetected

**Implementation**:
```python
# CloudTrail event triggers Lambda rotation
{
  "Event": "AssumeRole",
  "Principal": "terminated-employee@company.com",
  "Action": "rotate_all_secrets_for_user"
}
```

**3. Continuous Rotation**

Rotate secrets continuously (e.g., per-request, per-session).

**Pros**:
- Minimal exposure window
- Strongest security posture

**Cons**:
- High operational complexity
- Not suitable for all secret types

**Implementation**:
```python
# Generate new token per request
token = generate_ephemeral_token(validity=3600)  # 1 hour
```

**4. Hybrid Rotation**

Combine time-based, event-driven, and continuous approaches.

**Example**:
- Time-based: Rotate API keys every 90 days
- Event-driven: Rotate immediately on breach
- Continuous: Rotate session tokens per-session

### Zero-Downtime Rotation

**Critical Requirement**: Rotation must not cause service interruption.

**Pattern 1: Dual-Active Period (Recommended)**

```
Phase 1: Generate New Secret
─────────────────────────────
Old: SECRET_V1 (active, write)
New: SECRET_V2 (created, not active)

Phase 2: Activate New Secret
─────────────────────────────
Old: SECRET_V1 (active, read-only)  ← Still valid for existing requests
New: SECRET_V2 (active, write)      ← New requests use this

Phase 3: Grace Period (e.g., 24-48 hours)
─────────────────────────────
Old: SECRET_V1 (active, read-only)  ← Gradually expires
New: SECRET_V2 (active, write)      ← All new requests use this

Phase 4: Revoke Old Secret
─────────────────────────────
Old: SECRET_V1 (revoked)            ← No longer valid
New: SECRET_V2 (active, write)      ← Only valid secret
```

**Pattern 2: Versioned Secrets**

Maintain multiple active versions simultaneously.

```python
# Client requests with version
GET /api/data
Authorization: Bearer SECRET_V2

# Server accepts V1, V2, V3
if version in [1, 2, 3]:
    authenticate(secret, version)
```

**Pattern 3: Blue-Green Rotation**

Maintain two complete environments, rotate one while the other serves traffic.

```
Blue Environment (Active)
  Database: db-blue (credentials: USER_BLUE)

Green Environment (Standby)
  Database: db-green (credentials: USER_GREEN)

Rotation:
1. Rotate USER_GREEN credentials
2. Test Green environment
3. Switch traffic to Green
4. Rotate USER_BLUE credentials
```

---

## Secret Types

### 1. Passwords

**Characteristics**:
- Human-memorable or system-generated
- Hashed (never stored plaintext)
- Salted (unique salt per password)
- Key derivation function (Argon2id, PBKDF2, scrypt)

**Rotation Pattern**:
```python
# Generate new password
new_password = generate_secure_password(length=32)

# Hash with Argon2id
from argon2 import PasswordHasher
ph = PasswordHasher()
hashed = ph.hash(new_password)

# Store hash (never plaintext)
store_password_hash(user_id, hashed)

# Distribute securely
send_password_securely(user_id, new_password)
```

**Best Practices**:
- **Length**: Minimum 16 characters (32+ recommended)
- **Complexity**: Mix uppercase, lowercase, numbers, symbols
- **Entropy**: Use CSPRNG (cryptographically secure random number generator)
- **Hashing**: Argon2id > scrypt > PBKDF2
- **Never reuse**: Each password unique
- **Secure distribution**: Out-of-band delivery (e.g., SMS, authenticator app)

### 2. API Keys

**Characteristics**:
- Long-lived credentials for programmatic access
- Often base64 or hex-encoded
- Scoped to specific permissions

**Structure**:
```
PREFIX_RANDOM_CHECKSUM
  ├─ PREFIX: Identifies key type (e.g., sk_live_, pk_test_)
  ├─ RANDOM: Cryptographically secure random bytes
  └─ CHECKSUM: Integrity verification (e.g., CRC32)

Example: sk_live_a1b2c3d4e5f6g7h8i9j0_c3f1
```

**Rotation Pattern**:
```python
# Generate new API key
import secrets
prefix = "sk_live"
random_part = secrets.token_urlsafe(32)  # 256 bits
checksum = calculate_checksum(random_part)
new_api_key = f"{prefix}_{random_part}_{checksum}"

# Store hash (not plaintext)
hashed_key = hash_api_key(new_api_key)
store_api_key(client_id, hashed_key, version=2)

# Return plaintext only once
return {"api_key": new_api_key, "version": 2}

# After grace period, revoke v1
revoke_api_key(client_id, version=1)
```

**Best Practices**:
- **Prefix for identification**: Easy to detect in logs/code
- **Checksum for integrity**: Detect typos/corruption
- **Hash before storage**: Never store plaintext
- **Scope to least privilege**: Limit permissions
- **Monitor usage**: Detect anomalies
- **Provide migration window**: Dual-active period

### 3. Database Credentials

**Characteristics**:
- Username/password pairs
- Often long-lived
- High-value targets (data access)

**Rotation Challenges**:
- Active connections must transition
- Connection pools must refresh
- Zero-downtime requirement
- Multi-region consistency

**Rotation Pattern (PostgreSQL)**:
```sql
-- Phase 1: Create new user
CREATE USER app_user_v2 WITH PASSWORD 'new_secure_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user_v2;

-- Phase 2: Update application config (dual-active)
-- Old: app_user_v1 (read + write)
-- New: app_user_v2 (read + write)

-- Phase 3: Grace period (24-48 hours)
-- Monitor connections: SELECT * FROM pg_stat_activity WHERE usename = 'app_user_v1';

-- Phase 4: Revoke old user
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM app_user_v1;
DROP USER app_user_v1;
```

**Best Practices**:
- **Use dynamic credentials**: Vault can generate temporary credentials
- **Rotate regularly**: 90 days minimum
- **Monitor active connections**: Ensure old credentials no longer in use
- **Connection pool refresh**: Force refresh after rotation
- **Test before revoke**: Verify new credentials work

### 4. TLS/SSL Certificates

**Characteristics**:
- Public key infrastructure (PKI)
- Expiration dates (typically 90 days to 13 months)
- Chain of trust (root → intermediate → leaf)

**Rotation Pattern**:
```bash
# Generate new private key
openssl genrsa -out new_private_key.pem 2048

# Generate CSR (Certificate Signing Request)
openssl req -new -key new_private_key.pem -out cert.csr

# Submit to CA (Let's Encrypt, DigiCert, etc.)
certbot certonly --manual --preferred-challenges dns -d example.com

# Install new certificate (dual-active during transition)
cp /etc/letsencrypt/live/example.com/fullchain.pem /etc/nginx/certs/
nginx -s reload

# After expiration, old cert automatically invalid
```

**Best Practices**:
- **Automate with ACME**: Let's Encrypt, cert-manager (Kubernetes)
- **Monitor expiration**: Alert 30 days before
- **Use short validity**: 90 days (Let's Encrypt default)
- **Wildcard certs**: Cover subdomains
- **OCSP stapling**: Performance + privacy

### 5. Encryption Keys

**Characteristics**:
- Symmetric (AES-256) or asymmetric (RSA-2048+)
- Key hierarchies (Root → KEK → DEK)
- Envelope encryption

**Rotation Pattern (Envelope Encryption)**:
```python
# Rotate KEK (Key Encryption Key)
new_kek = kms.create_key(description="Master Key v2")

# Re-encrypt DEKs with new KEK (data stays encrypted with DEKs)
for dek_record in database.query("SELECT * FROM data_keys"):
    plaintext_dek = kms.decrypt(dek_record.encrypted_dek, old_kek)
    new_encrypted_dek = kms.encrypt(plaintext_dek, new_kek)
    database.update(dek_record.id, new_encrypted_dek, new_kek.version)

# Data never touched (still encrypted with same DEK)
# But DEKs now encrypted with new KEK
```

**Best Practices**:
- **Use envelope encryption**: Rotate KEK, not data
- **Separate keys by environment**: dev, staging, prod
- **Automate rotation**: Monthly or quarterly
- **Maintain key version history**: Support decryption of old data
- **Test rotation**: Verify decryption works

### 6. OAuth Tokens

**Characteristics**:
- Short-lived access tokens (minutes to hours)
- Long-lived refresh tokens (days to months)
- JWT or opaque tokens

**Rotation Pattern**:
```python
# Access token rotation (automatic with refresh)
POST /oauth/token
{
  "grant_type": "refresh_token",
  "refresh_token": "REFRESH_TOKEN",
  "client_id": "CLIENT_ID"
}

Response:
{
  "access_token": "NEW_ACCESS_TOKEN",
  "refresh_token": "NEW_REFRESH_TOKEN",  # Optionally rotated
  "expires_in": 3600
}

# Refresh token rotation (every use)
# Old refresh token invalidated, new one issued
```

**Best Practices**:
- **Short access token lifetime**: 15 minutes to 1 hour
- **Rotate refresh tokens**: On every use (rotation)
- **Bind to client**: Prevent token theft
- **Revoke on logout**: Explicit invalidation
- **Monitor anomalies**: Unusual refresh patterns

### 7. SSH Keys

**Characteristics**:
- Asymmetric key pairs (public + private)
- Long-lived (often years)
- Used for server access

**Rotation Pattern**:
```bash
# Generate new key pair
ssh-keygen -t ed25519 -C "user@example.com" -f ~/.ssh/id_ed25519_new

# Add new public key to authorized_keys
cat ~/.ssh/id_ed25519_new.pub >> ~/.ssh/authorized_keys

# Test new key
ssh -i ~/.ssh/id_ed25519_new user@server

# Remove old public key from authorized_keys
sed -i '/OLD_KEY_FINGERPRINT/d' ~/.ssh/authorized_keys

# Delete old private key
rm ~/.ssh/id_ed25519_old
```

**Best Practices**:
- **Use Ed25519**: Faster, more secure than RSA
- **Passphrase-protect**: Encrypt private keys
- **Rotate on departure**: Remove employee keys immediately
- **Certificate-based**: Use SSH certificates for expiration
- **Audit access**: Monitor SSH logins

---

## Rotation Strategies

### Time-Based Rotation

**Implementation**:

```python
#!/usr/bin/env python3
"""
Time-based secret rotation using cron scheduling.
"""

import boto3
import datetime
from dateutil.relativedelta import relativedelta

class TimeBasedRotator:
    def __init__(self, rotation_interval_days=90):
        self.rotation_interval = datetime.timedelta(days=rotation_interval_days)
        self.secrets_manager = boto3.client('secretsmanager')

    def should_rotate(self, secret_name):
        """Check if secret should be rotated based on age."""
        metadata = self.secrets_manager.describe_secret(SecretId=secret_name)
        last_rotated = metadata.get('LastRotatedDate', metadata['CreatedDate'])
        age = datetime.datetime.now(datetime.timezone.utc) - last_rotated
        return age >= self.rotation_interval

    def rotate_if_needed(self, secret_name):
        """Rotate secret if rotation interval exceeded."""
        if self.should_rotate(secret_name):
            print(f"Rotating {secret_name} (age: {age.days} days)")
            self.secrets_manager.rotate_secret(
                SecretId=secret_name,
                RotationLambdaARN='arn:aws:lambda:...:function:rotate_secret'
            )
        else:
            print(f"Skipping {secret_name} (age: {age.days} days)")

# Cron: 0 2 * * * /usr/bin/python3 /opt/rotate_secrets.py
if __name__ == '__main__':
    rotator = TimeBasedRotator(rotation_interval_days=90)
    secrets = ['db/prod/password', 'api/stripe/key', 'app/jwt/signing-key']
    for secret in secrets:
        rotator.rotate_if_needed(secret)
```

**Scheduling**:
```cron
# Rotate API keys every 90 days (first of month, 2 AM)
0 2 1 */3 * /usr/bin/rotate_api_keys.py

# Rotate database credentials quarterly
0 2 1 1,4,7,10 * /usr/bin/rotate_db_credentials.py

# Rotate certificates monthly (Let's Encrypt renewal)
0 2 1 * * certbot renew --quiet
```

### Event-Driven Rotation

**Triggers**:
1. **Employee departure**: Rotate all secrets accessed by user
2. **Suspicious activity**: Failed auth attempts, unusual patterns
3. **Breach notification**: Third-party service compromised
4. **Security scan findings**: Exposed secrets in logs/code
5. **Manual trigger**: Security team initiates rotation

**Implementation (AWS EventBridge + Lambda)**:

```python
# Lambda function triggered by EventBridge
def lambda_handler(event, context):
    """
    Event-driven rotation triggered by CloudTrail events.
    """
    event_name = event['detail']['eventName']
    principal = event['detail']['userIdentity']['principalId']

    # Rotation triggers
    triggers = {
        'AssumeRole': rotate_iam_credentials,
        'GetSecretValue': check_suspicious_access,
        'FailedLoginAttempt': emergency_rotation,
        'UserTerminated': rotate_all_user_secrets
    }

    if event_name in triggers:
        triggers[event_name](principal, event)

def rotate_all_user_secrets(user_id, event):
    """Rotate all secrets accessed by terminated user."""
    secrets = get_secrets_accessed_by_user(user_id)
    for secret in secrets:
        rotate_secret(secret)
        notify_security_team(f"Rotated {secret} (user {user_id} terminated)")
```

**EventBridge Rule**:
```json
{
  "source": ["aws.iam"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["AssumeRole", "GetSecretValue"],
    "userIdentity": {
      "principalId": ["TERMINATED_USER_ID"]
    }
  }
}
```

### Dynamic Credentials (Vault)

**Pattern**: Generate temporary credentials on-demand.

**Benefits**:
- No manual rotation needed
- Credentials expire automatically
- Least privilege (scoped to specific operations)

**HashiCorp Vault Example**:

```python
import hvac

client = hvac.Client(url='https://vault.example.com')

# Database dynamic credentials
creds = client.secrets.database.generate_credentials(
    name='postgres-app-role',
    ttl='1h'
)

username = creds['data']['username']  # vault_gen_abc123
password = creds['data']['password']  # temporary password

# Use credentials (valid for 1 hour)
db = psycopg2.connect(
    host='db.example.com',
    user=username,
    password=password,
    database='app'
)

# After 1 hour, credentials automatically revoked
# Request new credentials for next operation
```

**Vault Configuration**:
```hcl
# Database secrets engine
path "database/creds/postgres-app-role" {
  capabilities = ["read"]
}

# Database role
resource "vault_database_secret_backend_role" "postgres_app" {
  backend             = "database"
  name                = "postgres-app-role"
  db_name             = "postgres"
  creation_statements = ["CREATE USER '{{name}}' WITH PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';"]
  default_ttl         = 3600   # 1 hour
  max_ttl             = 86400  # 24 hours
}
```

---

## Platform Integration

### AWS Secrets Manager

**Features**:
- Automatic rotation with Lambda
- Multi-region replication
- Resource-based policies
- CloudTrail audit logging
- KMS encryption at rest

**Rotation Lambda**:

```python
import boto3
import pymysql
import secrets

secrets_client = boto3.client('secretsmanager')

def lambda_handler(event, context):
    """
    Automatic rotation handler for AWS Secrets Manager.
    """
    arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    # Rotation steps
    if step == "createSecret":
        create_secret(arn, token)
    elif step == "setSecret":
        set_secret(arn, token)
    elif step == "testSecret":
        test_secret(arn, token)
    elif step == "finishSecret":
        finish_secret(arn, token)

def create_secret(arn, token):
    """Generate new password and store as AWSPENDING."""
    current_secret = get_secret_dict(arn, "AWSCURRENT")

    # Generate new password
    new_password = secrets.token_urlsafe(32)
    current_secret['password'] = new_password

    # Store as AWSPENDING
    secrets_client.put_secret_value(
        SecretId=arn,
        ClientRequestToken=token,
        SecretString=json.dumps(current_secret),
        VersionStages=['AWSPENDING']
    )

def set_secret(arn, token):
    """Update database with new password."""
    pending_secret = get_secret_dict(arn, "AWSPENDING", token)
    current_secret = get_secret_dict(arn, "AWSCURRENT")

    # Connect with current credentials
    conn = pymysql.connect(
        host=pending_secret['host'],
        user=current_secret['username'],
        password=current_secret['password']
    )

    # Set new password
    with conn.cursor() as cursor:
        cursor.execute(
            "ALTER USER %s IDENTIFIED BY %s",
            (pending_secret['username'], pending_secret['password'])
        )
    conn.commit()
    conn.close()

def test_secret(arn, token):
    """Test new credentials."""
    pending_secret = get_secret_dict(arn, "AWSPENDING", token)

    # Test connection with new credentials
    conn = pymysql.connect(
        host=pending_secret['host'],
        user=pending_secret['username'],
        password=pending_secret['password']
    )
    conn.close()

def finish_secret(arn, token):
    """Finalize rotation (move AWSPENDING to AWSCURRENT)."""
    secrets_client.update_secret_version_stage(
        SecretId=arn,
        VersionStage="AWSCURRENT",
        MoveToVersionId=token,
        RemoveFromVersionId=get_current_version(arn)
    )
```

**Terraform Configuration**:

```hcl
resource "aws_secretsmanager_secret" "db_password" {
  name                    = "prod/db/password"
  recovery_window_in_days = 7

  rotation_rules {
    automatically_after_days = 90
  }
}

resource "aws_secretsmanager_secret_rotation" "db_password" {
  secret_id           = aws_secretsmanager_secret.db_password.id
  rotation_lambda_arn = aws_lambda_function.rotate_secret.arn

  rotation_rules {
    automatically_after_days = 90
  }
}

resource "aws_lambda_function" "rotate_secret" {
  filename         = "rotate_secret.zip"
  function_name    = "rotate-db-secret"
  role             = aws_iam_role.lambda_rotation.arn
  handler          = "index.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      SECRET_ARN = aws_secretsmanager_secret.db_password.arn
    }
  }
}
```

### Google Cloud Secret Manager

**Features**:
- Secret versioning (immutable versions)
- IAM-based access control
- Audit logging (Cloud Audit Logs)
- Replication (multi-region)
- Automatic rotation (Cloud Scheduler + Cloud Functions)

**Rotation with Cloud Functions**:

```python
from google.cloud import secretmanager
import psycopg2
import secrets

client = secretmanager.SecretManagerServiceClient()

def rotate_secret(request):
    """
    Cloud Function triggered by Cloud Scheduler for secret rotation.
    """
    project_id = "my-project"
    secret_id = "db-password"

    # Generate new password
    new_password = secrets.token_urlsafe(32)

    # Add new version to Secret Manager
    parent = f"projects/{project_id}/secrets/{secret_id}"
    response = client.add_secret_version(
        request={
            "parent": parent,
            "payload": {"data": new_password.encode("UTF-8")}
        }
    )

    # Update database
    update_database_password(new_password)

    # Disable old versions (after grace period)
    disable_old_versions(parent, keep_count=2)

    return {"status": "rotated", "version": response.name}

def update_database_password(new_password):
    """Update PostgreSQL password."""
    # Get current credentials
    current_secret = get_secret_version(project_id, secret_id, "latest")

    # Connect and update
    conn = psycopg2.connect(
        host="10.0.0.5",
        user="app_user",
        password=current_secret,
        database="app"
    )
    with conn.cursor() as cursor:
        cursor.execute("ALTER USER app_user WITH PASSWORD %s", (new_password,))
    conn.commit()
    conn.close()
```

**Cloud Scheduler Trigger**:

```bash
gcloud scheduler jobs create http rotate-db-secret \
  --schedule="0 2 1 * *" \
  --uri="https://us-central1-my-project.cloudfunctions.net/rotate_secret" \
  --http-method=POST \
  --oidc-service-account-email=rotation-sa@my-project.iam.gserviceaccount.com
```

### Azure Key Vault

**Features**:
- Secret versioning
- Automatic rotation (Event Grid + Azure Functions)
- RBAC and access policies
- Soft delete and purge protection
- HSM-backed secrets

**Rotation with Azure Functions**:

```python
import os
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import pymysql
import secrets

def main(timer: func.TimerRequest) -> None:
    """
    Azure Function triggered by timer for secret rotation.
    """
    vault_url = os.environ["VAULT_URL"]
    secret_name = "db-password"

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)

    # Generate new password
    new_password = secrets.token_urlsafe(32)

    # Update Key Vault
    client.set_secret(secret_name, new_password)

    # Update database
    update_database(new_password)

    # Log rotation
    logging.info(f"Rotated {secret_name}")

def update_database(new_password):
    """Update MySQL password."""
    conn = pymysql.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=get_current_password(),  # Old password
        database=os.environ["DB_NAME"]
    )
    with conn.cursor() as cursor:
        cursor.execute(
            "SET PASSWORD FOR %s = PASSWORD(%s)",
            (os.environ["DB_USER"], new_password)
        )
    conn.commit()
    conn.close()
```

**Terraform Configuration**:

```hcl
resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = random_password.db_password.result
  key_vault_id = azurerm_key_vault.main.id

  expiration_date = timeadd(timestamp(), "2160h")  # 90 days
}

resource "azurerm_eventgrid_event_subscription" "secret_near_expiry" {
  name  = "secret-rotation-trigger"
  scope = azurerm_key_vault.main.id

  subject_filter {
    subject_begins_with = "/secrets/db-password"
  }

  azure_function_endpoint {
    function_id = azurerm_function_app.rotation.id
  }
}
```

### HashiCorp Vault

**Features**:
- Dynamic secrets (temporary credentials)
- Automatic revocation
- Lease renewal
- Audit logging
- Multi-cloud support

**Database Dynamic Secrets**:

```bash
# Enable database secrets engine
vault secrets enable database

# Configure PostgreSQL connection
vault write database/config/postgresql \
  plugin_name=postgresql-database-plugin \
  allowed_roles="app-role" \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/app?sslmode=require" \
  username="vault_admin" \
  password="admin_password"  # Example only - use actual credentials from secure storage

# Create role
vault write database/roles/app-role \
  db_name=postgresql \
  creation_statements="CREATE USER \"{{name}}\" WITH PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

# Generate temporary credentials
vault read database/creds/app-role

Key                Value
---                -----
lease_id           database/creds/app-role/abc123
lease_duration     1h
username           v-token-app-role-xyz789
password           A1b2C3d4E5f6G7h8
```

**Python Integration**:

```python
import hvac
import psycopg2

# Authenticate to Vault
client = hvac.Client(url='https://vault.example.com')
client.auth.approle.login(role_id='...', secret_id='...')

# Get dynamic credentials
response = client.secrets.database.generate_credentials('app-role')
db_user = response['data']['username']
db_pass = response['data']['password']

# Use credentials (valid for 1 hour)
conn = psycopg2.connect(
    host='postgres.example.com',
    user=db_user,
    password=db_pass,
    database='app'
)

# Credentials automatically revoked after TTL
```

---

## Database Credential Rotation

### Challenge: Zero-Downtime Rotation

**Problem**: Active database connections must not break during rotation.

**Solution**: Dual-user pattern with connection pool refresh.

### PostgreSQL Rotation Pattern

**Step 1: Create New User**

```sql
-- Create new user with same privileges as old user
CREATE USER app_user_v2 WITH PASSWORD 'new_secure_password';

-- Grant same permissions as old user
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user_v2;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user_v2;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_user_v2;
```

**Step 2: Update Application Configuration**

```python
# Phase 1: Dual-active period
# Primary connection pool: app_user_v2 (new)
# Fallback connection pool: app_user_v1 (old, read-only)

DATABASE_CONFIG = {
    'primary': {
        'user': 'app_user_v2',
        'password': get_secret('db/app_user_v2'),
        'host': 'db.example.com',
        'database': 'app'
    },
    'fallback': {
        'user': 'app_user_v1',
        'password': get_secret('db/app_user_v1'),
        'host': 'db.example.com',
        'database': 'app'
    }
}

# Connection pool refresh
connection_pool.reconfigure(DATABASE_CONFIG['primary'])
```

**Step 3: Monitor Active Connections**

```sql
-- Check active connections for old user
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    state_change
FROM pg_stat_activity
WHERE usename = 'app_user_v1'
ORDER BY query_start DESC;

-- Kill long-running connections (after grace period)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE usename = 'app_user_v1'
  AND state_change < NOW() - INTERVAL '1 hour';
```

**Step 4: Revoke Old User**

```sql
-- After grace period (24-48 hours), revoke old user
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM app_user_v1;
DROP USER app_user_v1;
```

### MySQL Rotation Pattern

```sql
-- Step 1: Create new user
CREATE USER 'app_user_v2'@'%' IDENTIFIED BY 'new_secure_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON app.* TO 'app_user_v2'@'%';
FLUSH PRIVILEGES;

-- Step 2: Monitor connections
SELECT
    ID,
    USER,
    HOST,
    DB,
    TIME,
    STATE,
    INFO
FROM INFORMATION_SCHEMA.PROCESSLIST
WHERE USER = 'app_user_v1';

-- Step 3: Kill old connections (after grace period)
KILL CONNECTION <connection_id>;

-- Step 4: Revoke old user
DROP USER 'app_user_v1'@'%';
FLUSH PRIVILEGES;
```

### MongoDB Rotation Pattern

```javascript
// Step 1: Create new user
db.createUser({
  user: "app_user_v2",
  pwd: "new_secure_password",
  roles: [
    { role: "readWrite", db: "app" }
  ]
});

// Step 2: Monitor connections
db.currentOp({
  "active": true,
  "effectiveUsers.user": "app_user_v1"
});

// Step 3: Update application connection string
// mongodb://app_user_v2:new_password@mongodb:27017/app

// Step 4: Drop old user (after grace period)
db.dropUser("app_user_v1");
```

### Automated Rotation Script

```python
#!/usr/bin/env python3
"""
Automated database credential rotation with zero downtime.
"""

import psycopg2
import secrets
import time
from contextlib import contextmanager

class DatabaseRotator:
    def __init__(self, host, database, admin_user, admin_password):
        self.host = host
        self.database = database
        self.admin_user = admin_user
        self.admin_password = admin_password

    @contextmanager
    def admin_connection(self):
        """Context manager for admin database connection."""
        conn = psycopg2.connect(
            host=self.host,
            database=self.database,
            user=self.admin_user,
            password=self.admin_password
        )
        try:
            yield conn
        finally:
            conn.close()

    def rotate_user(self, username, grace_period_hours=24):
        """
        Rotate database user credentials with zero downtime.

        Args:
            username: Username to rotate (e.g., 'app_user')
            grace_period_hours: Hours to keep old credentials active
        """
        # Generate new credentials
        new_username = f"{username}_v{int(time.time())}"
        new_password = secrets.token_urlsafe(32)

        print(f"Step 1: Creating new user {new_username}")
        self.create_user(new_username, new_password, template_user=username)

        print(f"Step 2: Updating application configuration")
        self.update_app_config(new_username, new_password)

        print(f"Step 3: Grace period ({grace_period_hours} hours)")
        print(f"  Monitoring active connections for {username}")
        time.sleep(grace_period_hours * 3600)  # Wait for grace period

        print(f"Step 4: Terminating old connections")
        self.terminate_connections(username)

        print(f"Step 5: Revoking old user {username}")
        self.revoke_user(username)

        print(f"Rotation complete: {username} -> {new_username}")
        return new_username, new_password

    def create_user(self, username, password, template_user):
        """Create new user with same privileges as template."""
        with self.admin_connection() as conn:
            with conn.cursor() as cursor:
                # Create user
                cursor.execute(
                    f"CREATE USER {username} WITH PASSWORD %s",
                    (password,)
                )

                # Copy privileges from template user
                cursor.execute(f"""
                    DO $$
                    DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN
                            SELECT privilege_type, table_schema, table_name
                            FROM information_schema.role_table_grants
                            WHERE grantee = '{template_user}'
                        LOOP
                            EXECUTE format('GRANT %s ON %I.%I TO {username}',
                                r.privilege_type, r.table_schema, r.table_name);
                        END LOOP;
                    END $$;
                """)
                conn.commit()

    def terminate_connections(self, username):
        """Terminate active connections for user."""
        with self.admin_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE usename = %s
                      AND pid <> pg_backend_pid()
                """, (username,))
                conn.commit()

    def revoke_user(self, username):
        """Revoke privileges and drop user."""
        with self.admin_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {username}")
                cursor.execute(f"DROP USER {username}")
                conn.commit()

    def update_app_config(self, username, password):
        """Update application configuration (placeholder)."""
        # In production: Update Secrets Manager, Vault, or config service
        print(f"  Update config: {username} / {password[:8]}...")
        # secrets_manager.update_secret('db/credentials', {
        #     'username': username,
        #     'password': password
        # })

# Usage
if __name__ == '__main__':
    rotator = DatabaseRotator(
        host='db.example.com',
        database='app',
        admin_user='postgres',
        admin_password='admin_password'  # Example only - use environment variable or secret manager
    )

    rotator.rotate_user('app_user', grace_period_hours=24)
```

---

## Multi-Region Coordination

### Challenge: Consistent Rotation Across Regions

**Problem**: Secrets must rotate consistently across multiple regions to avoid split-brain scenarios.

**Solution**: Leader-follower pattern with replication.

### AWS Multi-Region Rotation

```python
#!/usr/bin/env python3
"""
Multi-region secret rotation with AWS Secrets Manager.
"""

import boto3
import time

class MultiRegionRotator:
    def __init__(self, primary_region, replica_regions):
        self.primary_region = primary_region
        self.replica_regions = replica_regions
        self.clients = {
            region: boto3.client('secretsmanager', region_name=region)
            for region in [primary_region] + replica_regions
        }

    def rotate_secret(self, secret_name):
        """
        Rotate secret across all regions (primary first, then replicas).
        """
        print(f"Step 1: Rotate in primary region ({self.primary_region})")
        primary_client = self.clients[self.primary_region]

        # Trigger rotation in primary region
        response = primary_client.rotate_secret(
            SecretId=secret_name,
            RotationLambdaARN=f"arn:aws:lambda:{self.primary_region}:...:function:rotate"
        )
        rotation_id = response['VersionId']

        # Wait for primary rotation to complete
        self.wait_for_rotation(primary_client, secret_name, rotation_id)

        # Get new secret value from primary
        new_secret = primary_client.get_secret_value(
            SecretId=secret_name,
            VersionStage='AWSCURRENT'
        )

        print(f"Step 2: Replicate to {len(self.replica_regions)} regions")
        for region in self.replica_regions:
            print(f"  Replicating to {region}")
            replica_client = self.clients[region]

            # Update secret in replica region
            replica_client.put_secret_value(
                SecretId=secret_name,
                SecretString=new_secret['SecretString'],
                VersionStages=['AWSCURRENT']
            )

        print("Multi-region rotation complete")

    def wait_for_rotation(self, client, secret_name, version_id, timeout=300):
        """Wait for rotation to complete."""
        start = time.time()
        while time.time() - start < timeout:
            response = client.describe_secret(SecretId=secret_name)
            version_stages = response['VersionIdsToStages'].get(version_id, [])
            if 'AWSCURRENT' in version_stages:
                return
            time.sleep(5)
        raise TimeoutError(f"Rotation timeout after {timeout}s")

# Usage
rotator = MultiRegionRotator(
    primary_region='us-east-1',
    replica_regions=['us-west-2', 'eu-west-1', 'ap-southeast-1']
)
rotator.rotate_secret('prod/db/password')
```

### GCP Multi-Region Rotation

```python
from google.cloud import secretmanager
import concurrent.futures

class GCPMultiRegionRotator:
    def __init__(self, project_id, regions):
        self.project_id = project_id
        self.regions = regions
        self.clients = {
            region: secretmanager.SecretManagerServiceClient(
                client_options={"api_endpoint": f"secretmanager.{region}.rep.googleapis.com"}
            )
            for region in regions
        }

    def rotate_secret(self, secret_id, new_value):
        """
        Rotate secret across all regions simultaneously.
        """
        def update_region(region):
            client = self.clients[region]
            parent = f"projects/{self.project_id}/secrets/{secret_id}"
            client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": new_value.encode("UTF-8")}
                }
            )
            return region

        # Parallel rotation across regions
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(update_region, r) for r in self.regions]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        print(f"Rotated across regions: {results}")

# Usage
rotator = GCPMultiRegionRotator(
    project_id='my-project',
    regions=['us-central1', 'europe-west1', 'asia-east1']
)
rotator.rotate_secret('db-password', 'new_secure_password')
```

---

## Zero-Downtime Patterns

### Pattern 1: Dual-Active Credentials

**Concept**: Maintain two valid credentials simultaneously during transition.

**Timeline**:
```
Day 0:  OLD (active, read + write)
Day 1:  OLD (active, read + write) + NEW (created, inactive)
Day 2:  OLD (active, read-only) + NEW (active, read + write)  ← Dual-active
Day 3:  OLD (active, read-only) + NEW (active, read + write)
Day 4:  NEW (active, read + write) + OLD (revoked)
```

**Implementation**:

```python
class DualActiveRotator:
    def __init__(self, secret_name):
        self.secret_name = secret_name

    def rotate(self):
        """Rotate secret using dual-active pattern."""
        # Phase 1: Create new secret
        new_secret = generate_secret()
        store_secret(self.secret_name, new_secret, version='v2', stage='PENDING')

        # Phase 2: Activate new secret (dual-active period begins)
        activate_secret(self.secret_name, version='v2')
        # Both v1 and v2 valid

        # Phase 3: Grace period (e.g., 48 hours)
        time.sleep(48 * 3600)

        # Phase 4: Revoke old secret
        revoke_secret(self.secret_name, version='v1')
        # Only v2 valid
```

### Pattern 2: Connection Pool Refresh

**Problem**: Long-lived connections use old credentials.

**Solution**: Force connection pool refresh after rotation.

```python
# Before rotation
connection_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=5,
    maxconn=20,
    host='db.example.com',
    user='app_user_v1',
    password='old_password'  # Example only - use environment variable or secret manager
)

# Rotation
new_credentials = rotate_credentials()

# After rotation: Close all connections and recreate pool
connection_pool.closeall()
connection_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=5,
    maxconn=20,
    host='db.example.com',
    user=new_credentials['user'],
    password=new_credentials['password']
)
```

### Pattern 3: Progressive Rollout

**Concept**: Roll out new credentials to subset of instances, validate, then expand.

**Timeline**:
```
Phase 1: 10% of instances use new credentials (canary)
Phase 2: Monitor for errors (24 hours)
Phase 3: 50% of instances use new credentials
Phase 4: Monitor for errors (24 hours)
Phase 5: 100% of instances use new credentials
Phase 6: Revoke old credentials
```

**Implementation (Kubernetes)**:

```yaml
# Deployment with rolling update
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero downtime
  template:
    spec:
      containers:
      - name: app
        env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials-v2  # New credentials
              key: password
```

---

## Compliance Requirements

### PCI-DSS 3.2.1

**Requirement 8.2.4**: Change user passwords/passphrases at least once every 90 days.

**Requirements**:
- Password rotation every 90 days (minimum)
- Prevent password reuse (last 4 passwords)
- Lockout after failed attempts
- Multi-factor authentication for administrative access

**Implementation**:

```python
# PCI-DSS compliant password rotation policy
PASSWORD_ROTATION_DAYS = 90
PASSWORD_HISTORY_COUNT = 4
MAX_FAILED_ATTEMPTS = 6

def enforce_pci_password_policy(user_id):
    """Enforce PCI-DSS password rotation policy."""
    user = get_user(user_id)

    # Check password age
    password_age = (datetime.now() - user.password_changed_at).days
    if password_age >= PASSWORD_ROTATION_DAYS:
        require_password_change(user_id)

    # Check password history
    new_password_hash = hash_password(new_password)
    if new_password_hash in get_password_history(user_id, PASSWORD_HISTORY_COUNT):
        raise ValueError("Cannot reuse last 4 passwords")

    # Update password
    update_password(user_id, new_password_hash)
    add_to_password_history(user_id, new_password_hash)
```

### SOC 2 (Trust Services Criteria)

**CC6.1**: Logical and physical access controls

**Requirements**:
- Document rotation procedures
- Audit trail of all rotations
- Access controls for rotation process
- Monitoring and alerting

**Audit Evidence**:

```python
# Log all rotation events for SOC 2 audit
def log_rotation_event(secret_name, action, user, result):
    """Log rotation event for compliance audit."""
    event = {
        'timestamp': datetime.utcnow().isoformat(),
        'secret_name': secret_name,
        'action': action,  # created, rotated, revoked
        'user': user,
        'result': result,  # success, failure
        'ip_address': get_client_ip(),
        'user_agent': get_user_agent()
    }
    audit_log.write(event)

    # Send to SIEM (Splunk, Datadog, etc.)
    siem.send_event(event)
```

### HIPAA (Security Rule)

**§ 164.312(a)(2)(i)**: Unique user identification (required)
**§ 164.312(a)(2)(iv)**: Encryption and decryption (addressable)

**Requirements**:
- Unique credentials per user
- Encrypt credentials at rest
- Audit access to ePHI
- Emergency access procedures

**Implementation**:

```python
# HIPAA-compliant credential management
def rotate_hipaa_credentials(user_id):
    """Rotate credentials with HIPAA compliance."""
    # Audit log (required)
    log_hipaa_event(user_id, 'credential_rotation_initiated')

    # Generate new credentials
    new_password = generate_secure_password(min_length=16)

    # Encrypt at rest (addressable safeguard)
    encrypted_password = encrypt_with_kms(new_password)

    # Store with audit trail
    store_credential(
        user_id=user_id,
        encrypted_password=encrypted_password,
        rotated_at=datetime.utcnow(),
        rotated_by=get_current_user()
    )

    # Notify user (secure channel)
    notify_user_secure(user_id, "Credentials rotated per HIPAA policy")

    # Audit log (required)
    log_hipaa_event(user_id, 'credential_rotation_completed')
```

### GDPR (Article 32)

**Article 32**: Security of processing

**Requirements**:
- Appropriate technical measures (encryption, pseudonymization)
- Ability to restore availability after incident
- Regular testing of security measures

**Implementation**:

```python
# GDPR Article 32 - Technical measures
def gdpr_compliant_rotation():
    """Implement GDPR-compliant rotation."""
    # Encryption at rest (technical measure)
    secret = encrypt_secret(new_secret, kms_key)

    # Pseudonymization (technical measure)
    secret_id = generate_pseudonym(actual_secret_name)

    # Backup (availability after incident)
    backup_secret(secret_id, secret, retention_days=90)

    # Regular testing (Article 32)
    test_rotation_procedure(secret_id)

    # Audit log (accountability)
    log_gdpr_event('secret_rotation', secret_id, 'completed')
```

---

## Audit and Monitoring

### Audit Logging

**Critical Events to Log**:

1. **Secret Created**: When, by whom, initial version
2. **Secret Accessed**: Who, when, from where, which version
3. **Secret Rotated**: Old version, new version, by whom
4. **Secret Revoked**: Which version, reason, by whom
5. **Rotation Failed**: Error details, retry count
6. **Unauthorized Access**: Failed attempts, source IP

**Log Format**:

```json
{
  "timestamp": "2025-10-27T14:32:10Z",
  "event_type": "secret_rotated",
  "secret_id": "prod/db/password",
  "secret_version": {
    "old": "v12",
    "new": "v13"
  },
  "actor": {
    "user_id": "rotation-lambda",
    "ip_address": "10.0.5.42",
    "user_agent": "AWS Lambda Python 3.11"
  },
  "result": "success",
  "duration_ms": 1250,
  "metadata": {
    "rotation_type": "scheduled",
    "next_rotation": "2026-01-27T02:00:00Z"
  }
}
```

**Implementation (CloudTrail)**:

```python
import boto3

cloudtrail = boto3.client('cloudtrail')

def query_rotation_events(secret_name, start_time, end_time):
    """Query CloudTrail for secret rotation events."""
    response = cloudtrail.lookup_events(
        LookupAttributes=[
            {'AttributeKey': 'ResourceName', 'AttributeValue': secret_name}
        ],
        StartTime=start_time,
        EndTime=end_time
    )

    for event in response['Events']:
        print(f"{event['EventTime']}: {event['EventName']} by {event['Username']}")
```

### Monitoring Metrics

**Key Metrics**:

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| **Secret Age** | Days since last rotation | > 90 days (PCI-DSS) |
| **Rotation Failures** | Failed rotation attempts | > 0 (investigate immediately) |
| **Unauthorized Access** | Failed secret access attempts | > 5 in 5 minutes |
| **Stale Secrets** | Secrets never rotated | > 180 days |
| **Rotation Duration** | Time to complete rotation | > 5 minutes (investigate) |
| **Secret Usage** | Access count per secret | Anomaly detection |

**Prometheus Metrics**:

```python
from prometheus_client import Counter, Gauge, Histogram

# Counters
rotations_total = Counter(
    'secrets_rotations_total',
    'Total secret rotations',
    ['secret_type', 'result']
)

# Gauges
secret_age_days = Gauge(
    'secret_age_days',
    'Days since last rotation',
    ['secret_name']
)

# Histograms
rotation_duration_seconds = Histogram(
    'rotation_duration_seconds',
    'Time to complete rotation',
    ['secret_type']
)

# Usage
def rotate_secret(secret_name):
    with rotation_duration_seconds.labels(secret_type='api_key').time():
        try:
            perform_rotation(secret_name)
            rotations_total.labels(secret_type='api_key', result='success').inc()
        except Exception as e:
            rotations_total.labels(secret_type='api_key', result='failure').inc()
            raise
```

**CloudWatch Dashboards**:

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def publish_rotation_metrics(secret_name, duration_ms, success):
    """Publish rotation metrics to CloudWatch."""
    cloudwatch.put_metric_data(
        Namespace='SecretsRotation',
        MetricData=[
            {
                'MetricName': 'RotationDuration',
                'Value': duration_ms,
                'Unit': 'Milliseconds',
                'Dimensions': [
                    {'Name': 'SecretName', 'Value': secret_name}
                ]
            },
            {
                'MetricName': 'RotationSuccess',
                'Value': 1 if success else 0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'SecretName', 'Value': secret_name}
                ]
            }
        ]
    )
```

### Alerting Rules

**PagerDuty/Opsgenie Alerts**:

```yaml
# Datadog monitor configuration
monitors:
  - name: "Secret Rotation Overdue"
    type: metric alert
    query: "max(last_1h):max:secret.age.days{env:prod} > 90"
    message: |
      Secret rotation overdue (>90 days)
      Secret: {{secret_name.name}}
      Age: {{value}} days
      @pagerduty-security

  - name: "Secret Rotation Failed"
    type: event alert
    query: "events('priority:all source:rotation status:error').rollup('count').last('5m') > 0"
    message: |
      Secret rotation failed
      Secret: {{event.secret_name}}
      Error: {{event.error_message}}
      @slack-security-alerts

  - name: "Unauthorized Secret Access"
    type: log alert
    query: "logs('service:secrets-manager status:error \"unauthorized access\"').rollup('count').last('5m') > 5"
    message: |
      Possible secret breach attempt
      IP: {{@network.client.ip}}
      Secret: {{@secret.name}}
      @pagerduty-security-oncall
```

---

## Emergency Rotation

### When to Trigger Emergency Rotation

**Immediate Rotation Required**:
1. **Confirmed breach**: Secret exposed in logs, code repository, or breach notification
2. **Suspicious activity**: Unusual access patterns, failed authentication spike
3. **Employee departure**: Termination or resignation (especially privileged users)
4. **Third-party breach**: Service provider compromised
5. **Regulatory requirement**: Compliance audit finding

### Emergency Rotation Procedure

**Runbook**:

```markdown
# Emergency Secret Rotation Runbook

## Prerequisites
- [ ] Confirm breach/compromise (evidence, scope)
- [ ] Identify affected secrets
- [ ] Notify security team
- [ ] Prepare communication plan

## Execution Steps

### 1. Immediate Containment (0-15 minutes)
- [ ] Revoke compromised secret immediately
- [ ] Block suspicious IP addresses
- [ ] Terminate active sessions using compromised credentials
- [ ] Enable additional logging/monitoring

### 2. Generate New Secret (15-30 minutes)
- [ ] Generate cryptographically secure replacement
- [ ] Store in secrets management platform
- [ ] Document rotation event

### 3. Update Dependent Systems (30-60 minutes)
- [ ] Identify all systems using compromised secret
- [ ] Update configuration/environment variables
- [ ] Restart services (if necessary)
- [ ] Verify connectivity

### 4. Validation (60-90 minutes)
- [ ] Test new secret functionality
- [ ] Monitor for errors/failures
- [ ] Verify old secret no longer works

### 5. Post-Incident (90+ minutes)
- [ ] Complete incident report
- [ ] Update runbook (lessons learned)
- [ ] Notify stakeholders
- [ ] Schedule post-mortem
```

**Automated Emergency Rotation**:

```python
#!/usr/bin/env python3
"""
Emergency secret rotation script.
"""

import boto3
import sys
import argparse
from datetime import datetime

class EmergencyRotator:
    def __init__(self):
        self.secrets_client = boto3.client('secretsmanager')
        self.sns_client = boto3.client('sns')

    def emergency_rotate(self, secret_name, reason):
        """
        Perform emergency rotation with immediate revocation.

        Args:
            secret_name: Name of compromised secret
            reason: Reason for emergency rotation
        """
        print(f"[EMERGENCY] Rotating {secret_name}")
        print(f"[REASON] {reason}")

        # Step 1: Notify security team
        self.notify_security_team(secret_name, reason)

        # Step 2: Revoke old secret immediately (no grace period)
        print("[STEP 1] Revoking compromised secret")
        self.revoke_secret_immediate(secret_name)

        # Step 3: Generate new secret
        print("[STEP 2] Generating new secret")
        new_secret_value = self.generate_secure_secret()

        # Step 4: Update secret
        print("[STEP 3] Updating secret")
        self.secrets_client.put_secret_value(
            SecretId=secret_name,
            SecretString=new_secret_value
        )

        # Step 5: Force rotation
        print("[STEP 4] Forcing rotation")
        self.secrets_client.rotate_secret(
            SecretId=secret_name,
            RotationLambdaARN=self.get_rotation_lambda_arn(secret_name)
        )

        # Step 6: Verify
        print("[STEP 5] Verifying rotation")
        self.verify_rotation(secret_name)

        # Step 7: Log incident
        self.log_emergency_rotation(secret_name, reason)

        print(f"[SUCCESS] Emergency rotation complete")

    def revoke_secret_immediate(self, secret_name):
        """Immediately revoke all old versions."""
        # Get all versions
        response = self.secrets_client.describe_secret(SecretId=secret_name)

        # Revoke all non-current versions
        for version_id, stages in response['VersionIdsToStages'].items():
            if 'AWSCURRENT' not in stages:
                self.secrets_client.update_secret_version_stage(
                    SecretId=secret_name,
                    VersionStage='AWSPREVIOUS',
                    RemoveFromVersionId=version_id
                )

    def notify_security_team(self, secret_name, reason):
        """Send emergency notification to security team."""
        message = f"""
        EMERGENCY SECRET ROTATION

        Secret: {secret_name}
        Reason: {reason}
        Timestamp: {datetime.utcnow().isoformat()}

        Action required: Investigate breach
        """

        self.sns_client.publish(
            TopicArn='arn:aws:sns:us-east-1:123456789012:security-alerts',
            Subject='EMERGENCY: Secret Rotation',
            Message=message
        )

# Usage
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Emergency secret rotation')
    parser.add_argument('--secret', required=True, help='Secret name')
    parser.add_argument('--reason', required=True, help='Rotation reason')
    args = parser.parse_args()

    rotator = EmergencyRotator()
    rotator.emergency_rotate(args.secret, args.reason)
```

**Kubernetes Emergency Rotation**:

```bash
#!/bin/bash
# emergency_k8s_rotation.sh

SECRET_NAME=$1
REASON=$2

echo "[EMERGENCY] Rotating Kubernetes secret: $SECRET_NAME"
echo "[REASON] $REASON"

# Step 1: Generate new secret value
NEW_VALUE=$(openssl rand -base64 32)

# Step 2: Update Kubernetes secret
kubectl create secret generic $SECRET_NAME \
  --from-literal=value=$NEW_VALUE \
  --dry-run=client -o yaml | kubectl apply -f -

# Step 3: Restart all pods using the secret
kubectl rollout restart deployment -l uses-secret=$SECRET_NAME

# Step 4: Wait for rollout
kubectl rollout status deployment -l uses-secret=$SECRET_NAME

echo "[SUCCESS] Emergency rotation complete"
```

---

## Implementation Patterns

### Pattern 1: Lambda-Based Rotation (AWS)

```python
import boto3
import pymysql
import json

secrets_client = boto3.client('secretsmanager')

def lambda_handler(event, context):
    """
    AWS Lambda handler for automatic secret rotation.
    Implements AWS Secrets Manager rotation protocol.
    """
    secret_arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    # Rotation steps (AWS protocol)
    if step == "createSecret":
        create_secret(secret_arn, token)
    elif step == "setSecret":
        set_secret(secret_arn, token)
    elif step == "testSecret":
        test_secret(secret_arn, token)
    elif step == "finishSecret":
        finish_secret(secret_arn, token)
    else:
        raise ValueError(f"Invalid step: {step}")

def create_secret(arn, token):
    """Step 1: Generate new secret value."""
    import secrets as sec

    # Get current secret
    current = json.loads(secrets_client.get_secret_value(
        SecretId=arn,
        VersionStage="AWSCURRENT"
    )['SecretString'])

    # Generate new password
    new_password = sec.token_urlsafe(32)
    current['password'] = new_password

    # Store as AWSPENDING
    secrets_client.put_secret_value(
        SecretId=arn,
        ClientRequestToken=token,
        SecretString=json.dumps(current),
        VersionStages=['AWSPENDING']
    )

def set_secret(arn, token):
    """Step 2: Update database with new password."""
    pending = json.loads(secrets_client.get_secret_value(
        SecretId=arn,
        VersionId=token,
        VersionStage="AWSPENDING"
    )['SecretString'])

    current = json.loads(secrets_client.get_secret_value(
        SecretId=arn,
        VersionStage="AWSCURRENT"
    )['SecretString'])

    # Connect with current credentials
    conn = pymysql.connect(
        host=pending['host'],
        user=current['username'],
        password=current['password'],
        database=pending['dbname']
    )

    # Update password
    with conn.cursor() as cursor:
        cursor.execute(
            f"ALTER USER '{pending['username']}'@'%' IDENTIFIED BY '{pending['password']}'"
        )
    conn.commit()
    conn.close()

def test_secret(arn, token):
    """Step 3: Test new credentials."""
    pending = json.loads(secrets_client.get_secret_value(
        SecretId=arn,
        VersionId=token,
        VersionStage="AWSPENDING"
    )['SecretString'])

    # Test connection
    conn = pymysql.connect(
        host=pending['host'],
        user=pending['username'],
        password=pending['password'],
        database=pending['dbname']
    )
    conn.close()

def finish_secret(arn, token):
    """Step 4: Finalize rotation."""
    # Get current version
    metadata = secrets_client.describe_secret(SecretId=arn)
    current_version = None
    for version, stages in metadata['VersionIdsToStages'].items():
        if 'AWSCURRENT' in stages:
            current_version = version
            break

    # Move AWSCURRENT to new version
    secrets_client.update_secret_version_stage(
        SecretId=arn,
        VersionStage="AWSCURRENT",
        MoveToVersionId=token,
        RemoveFromVersionId=current_version
    )
```

### Pattern 2: CronJob-Based Rotation (Kubernetes)

```yaml
# kubernetes/cronjob-rotation.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: rotate-secrets
  namespace: default
spec:
  schedule: "0 2 1 * *"  # First of month, 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: secret-rotator
          containers:
          - name: rotator
            image: myorg/secret-rotator:latest
            env:
            - name: SECRETS_TO_ROTATE
              value: "db-password,api-key,jwt-signing-key"
            - name: ROTATION_POLICY
              value: "90days"
          restartPolicy: OnFailure
---
# Python script in container
import os
import kubernetes

def rotate_kubernetes_secret(secret_name, new_value):
    """Rotate Kubernetes secret."""
    k8s = kubernetes.client.CoreV1Api()

    # Read current secret
    secret = k8s.read_namespaced_secret(secret_name, 'default')

    # Update value
    secret.data[secret_name] = base64.b64encode(new_value.encode()).decode()

    # Apply update
    k8s.replace_namespaced_secret(secret_name, 'default', secret)

    # Trigger rolling restart
    apps_api = kubernetes.client.AppsV1Api()
    deployments = apps_api.list_namespaced_deployment(
        'default',
        label_selector=f'uses-secret={secret_name}'
    )
    for deployment in deployments.items:
        apps_api.patch_namespaced_deployment(
            deployment.metadata.name,
            'default',
            {'spec': {'template': {'metadata': {'annotations': {
                'rotated-at': datetime.utcnow().isoformat()
            }}}}}
        )
```

### Pattern 3: Vault Dynamic Secrets

```python
import hvac
import time

class VaultDynamicSecrets:
    def __init__(self, vault_url, token):
        self.client = hvac.Client(url=vault_url, token=token)

    def get_database_credentials(self, role_name, ttl='1h'):
        """
        Get temporary database credentials from Vault.
        Credentials automatically rotate (expire after TTL).
        """
        response = self.client.secrets.database.generate_credentials(
            name=role_name,
            ttl=ttl
        )

        return {
            'username': response['data']['username'],
            'password': response['data']['password'],
            'lease_id': response['lease_id'],
            'lease_duration': response['lease_duration']
        }

    def renew_lease(self, lease_id, increment='1h'):
        """Renew lease to extend credential validity."""
        self.client.sys.renew_lease(
            lease_id=lease_id,
            increment=increment
        )

    def revoke_lease(self, lease_id):
        """Revoke lease (immediately invalidate credentials)."""
        self.client.sys.revoke_lease(lease_id=lease_id)

# Usage: Credentials automatically rotate
vault = VaultDynamicSecrets('https://vault.example.com', token='...')

# Get credentials (valid for 1 hour)
creds = vault.get_database_credentials('postgres-app-role', ttl='1h')

# Use credentials
conn = psycopg2.connect(
    host='db.example.com',
    user=creds['username'],  # vault_gen_abc123
    password=creds['password'],
    database='app'
)

# After 1 hour, credentials automatically revoked
# Request new credentials for next operation
```

---

## Security Best Practices

### 1. Never Store Secrets in Plaintext

**Bad**:
```python
# ❌ NEVER do this - example of what NOT to do
API_KEY = "sk_live_a1b2c3d4e5f6g7h8"  # Hardcoded - example only
config.yaml:
  database:
    password: "my_password_123"  # Plaintext in config - example only
```

**Good**:
```python
# Use secrets management
import boto3
secrets = boto3.client('secretsmanager')
api_key = secrets.get_secret_value(SecretId='api/stripe/key')['SecretString']

# Or environment variables (from secrets manager)
api_key = os.environ['STRIPE_API_KEY']
```

### 2. Use Encryption at Rest

**All secrets must be encrypted**:
- AWS Secrets Manager: KMS encryption (automatic)
- HashiCorp Vault: Transit backend or KMS
- Kubernetes: EncryptionConfiguration

```yaml
# Kubernetes encryption at rest
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-secret>
      - identity: {}
```

### 3. Implement Least Privilege

**Restrict access to secrets**:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "secretsmanager:GetSecretValue"
    ],
    "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/db/password-*",
    "Condition": {
      "StringEquals": {
        "aws:PrincipalTag/Environment": "production"
      }
    }
  }]
}
```

### 4. Monitor and Alert

**Key alerts**:
- Secret accessed by unusual principal
- Secret age > 90 days
- Rotation failure
- Unauthorized access attempts

### 5. Test Rotation Procedures

**Regular testing**:
```bash
# Quarterly rotation drill
./test_rotation.py --secret prod/db/password --dry-run

# Verify rollback works
./test_rotation.py --secret prod/db/password --rollback
```

### 6. Use Strong Randomness

**CSPRNG only**:
```python
import secrets  # Cryptographically secure

# Good
api_key = secrets.token_urlsafe(32)  # 256 bits

# Bad
import random
api_key = str(random.randint(0, 999999))  # Predictable!
```

### 7. Implement Grace Periods

**Allow transition time**:
- Old and new credentials both valid (24-48 hours)
- Monitor for errors during transition
- Rollback capability

### 8. Document Rotation Procedures

**Runbooks for all secret types**:
- Step-by-step rotation procedure
- Rollback plan
- Contact information
- Escalation path

---

## Common Pitfalls

### Pitfall 1: No Grace Period

**Problem**: Revoking old secret immediately breaks active connections.

**Solution**: Dual-active period (24-48 hours).

### Pitfall 2: Hardcoded Rotation Schedule

**Problem**: All secrets rotate simultaneously, overwhelming systems.

**Solution**: Stagger rotations across days/weeks.

```python
# Stagger rotations based on secret hash
rotation_day = hash(secret_name) % 30 + 1  # Day 1-30 of month
```

### Pitfall 3: No Rollback Plan

**Problem**: Rotation fails, no way to recover.

**Solution**: Always backup old secret before rotation.

```python
def rotate_with_rollback(secret_name):
    # Backup old secret
    old_secret = get_secret(secret_name)
    backup_secret(secret_name, old_secret, version='backup')

    try:
        # Rotate
        new_secret = generate_secret()
        update_secret(secret_name, new_secret)
        test_secret(secret_name)
    except Exception as e:
        # Rollback on failure
        print(f"Rotation failed: {e}. Rolling back...")
        update_secret(secret_name, old_secret)
        raise
```

### Pitfall 4: Testing Before Commit

**Problem**: Testing uncommitted changes wastes time.

**Solution**: Commit first, then test (see CLAUDE.md guidelines).

### Pitfall 5: No Monitoring

**Problem**: Rotation failures go unnoticed.

**Solution**: Monitor rotation metrics, alert on failures.

### Pitfall 6: Weak Secret Generation

**Problem**: Using weak random number generators.

**Solution**: Use cryptographically secure RNG (secrets module).

### Pitfall 7: No Audit Trail

**Problem**: No record of rotations for compliance.

**Solution**: Log all rotation events to SIEM.

---

## References

### Standards and Specifications

- **NIST SP 800-57**: Recommendation for Key Management (3 parts)
- **NIST SP 800-63B**: Digital Identity Guidelines (Authentication and Lifecycle Management)
- **PCI-DSS 3.2.1**: Payment Card Industry Data Security Standard
- **HIPAA Security Rule**: § 164.312 - Technical Safeguards
- **GDPR Article 32**: Security of Processing
- **SOC 2 Trust Services Criteria**: CC6.1 - Logical and Physical Access Controls
- **OWASP ASVS**: Application Security Verification Standard
- **CIS Benchmarks**: Database and application security benchmarks

### Platform Documentation

- **AWS Secrets Manager**: https://docs.aws.amazon.com/secretsmanager/
- **Google Cloud Secret Manager**: https://cloud.google.com/secret-manager/docs
- **Azure Key Vault**: https://docs.microsoft.com/azure/key-vault/
- **HashiCorp Vault**: https://www.vaultproject.io/docs
- **Kubernetes Secrets**: https://kubernetes.io/docs/concepts/configuration/secret/

### Tools and Libraries

- **Python cryptography**: https://cryptography.io/
- **Python secrets module**: https://docs.python.org/3/library/secrets.html
- **Boto3 (AWS SDK)**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- **Google Cloud Client Libraries**: https://cloud.google.com/python/docs/reference
- **Azure SDK for Python**: https://docs.microsoft.com/python/api/overview/azure/
- **hvac (Vault Python client)**: https://hvac.readthedocs.io/

### Best Practices

- **AWS Security Best Practices**: Secrets rotation patterns
- **Google Cloud Security Best Practices**: Secret management
- **Microsoft Azure Security Baseline**: Key management
- **OWASP Cryptographic Storage Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
- **OWASP Secrets Management Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

---

**End of REFERENCE.md** (3,247 lines)
