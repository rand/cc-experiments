---
name: cloud-gcp-iam-security
description: Google Cloud IAM, service accounts, Secret Manager, and Cloud KMS security practices
---

# GCP IAM and Security

**Scope**: IAM policies, service accounts, authentication, Secret Manager, and Cloud KMS encryption
**Lines**: ~330
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Configuring IAM roles and permissions for users and services
- Creating and managing service accounts for workloads
- Implementing authentication with Identity Platform
- Storing secrets and credentials in Secret Manager
- Managing encryption keys with Cloud KMS
- Setting up organization policies and constraints
- Implementing least privilege access control
- Rotating service account keys and secrets

## Core Concepts

### Concept 1: IAM Roles and Policies

**Role types**:
- **Basic roles**: Owner, Editor, Viewer (legacy, too broad)
- **Predefined roles**: Curated by Google (e.g., Storage Admin, Compute Instance Admin)
- **Custom roles**: User-defined with specific permissions

```bash
# Grant user a predefined role at project level
gcloud projects add-iam-policy-binding my-project \
  --member=user:alice@example.com \
  --role=roles/compute.instanceAdmin.v1

# Grant service account a role at resource level
gcloud storage buckets add-iam-policy-binding gs://my-bucket \
  --member=serviceAccount:app@my-project.iam.gserviceaccount.com \
  --role=roles/storage.objectViewer

# Create custom role with specific permissions
gcloud iam roles create customStorageRole \
  --project=my-project \
  --title="Custom Storage Role" \
  --description="Read objects and list buckets" \
  --permissions=storage.objects.get,storage.objects.list,storage.buckets.list \
  --stage=GA
```

### Concept 2: Service Accounts

**Service account types**:
- **User-managed**: Created by users for applications
- **Default**: Automatically created by Google (Compute, App Engine)
- **Google-managed**: Used internally by Google services

```python
from google.cloud import iam_admin_v1
from google.oauth2 import service_account

# Create service account
def create_service_account(project_id, account_id, display_name):
    client = iam_admin_v1.IAMClient()

    service_account = iam_admin_v1.ServiceAccount(
        display_name=display_name
    )

    request = iam_admin_v1.CreateServiceAccountRequest(
        name=f"projects/{project_id}",
        account_id=account_id,
        service_account=service_account
    )

    account = client.create_service_account(request=request)
    return account

# Use service account credentials in application
credentials = service_account.Credentials.from_service_account_file(
    'path/to/service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# Best practice: Use Workload Identity instead of key files
# See Pattern 5 below
```

### Concept 3: Secret Manager

**Features**:
- Store API keys, passwords, certificates securely
- Automatic encryption at rest
- Version management and rotation
- IAM-based access control

```python
from google.cloud import secretmanager

def create_secret(project_id, secret_id, secret_value):
    client = secretmanager.SecretManagerServiceClient()

    # Create secret
    parent = f"projects/{project_id}"
    secret = client.create_secret(
        request={
            "parent": parent,
            "secret_id": secret_id,
            "secret": {"replication": {"automatic": {}}},
        }
    )

    # Add secret version
    payload = secret_value.encode("UTF-8")
    version = client.add_secret_version(
        request={
            "parent": secret.name,
            "payload": {"data": payload}
        }
    )

    return version.name

def access_secret(project_id, secret_id, version_id="latest"):
    client = secretmanager.SecretManagerServiceClient()

    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})

    return response.payload.data.decode("UTF-8")

# Example usage
api_key = access_secret("my-project", "third-party-api-key")
```

### Concept 4: Cloud KMS Encryption

**Key types**:
- **Symmetric**: Same key for encryption/decryption (AEAD)
- **Asymmetric**: Public/private key pairs (signing, decryption)
- **Key rings**: Logical grouping of keys in a location

```python
from google.cloud import kms

def create_key_ring_and_key(project_id, location_id, key_ring_id, key_id):
    client = kms.KeyManagementServiceClient()

    # Create key ring
    location_name = f"projects/{project_id}/locations/{location_id}"
    key_ring = client.create_key_ring(
        request={
            "parent": location_name,
            "key_ring_id": key_ring_id
        }
    )

    # Create crypto key
    key = client.create_crypto_key(
        request={
            "parent": key_ring.name,
            "crypto_key_id": key_id,
            "crypto_key": {
                "purpose": kms.CryptoKey.CryptoKeyPurpose.ENCRYPT_DECRYPT,
                "version_template": {
                    "algorithm": kms.CryptoKeyVersion.CryptoKeyVersionAlgorithm.GOOGLE_SYMMETRIC_ENCRYPTION
                }
            }
        }
    )

    return key

def encrypt_symmetric(project_id, location_id, key_ring_id, key_id, plaintext):
    client = kms.KeyManagementServiceClient()

    key_name = f"projects/{project_id}/locations/{location_id}/keyRings/{key_ring_id}/cryptoKeys/{key_id}"
    plaintext_bytes = plaintext.encode("utf-8")

    response = client.encrypt(
        request={"name": key_name, "plaintext": plaintext_bytes}
    )

    return response.ciphertext

def decrypt_symmetric(project_id, location_id, key_ring_id, key_id, ciphertext):
    client = kms.KeyManagementServiceClient()

    key_name = f"projects/{project_id}/locations/{location_id}/keyRings/{key_ring_id}/cryptoKeys/{key_id}"

    response = client.decrypt(
        request={"name": key_name, "ciphertext": ciphertext}
    )

    return response.plaintext.decode("utf-8")
```

---

## Patterns

### Pattern 1: Least Privilege with Conditional IAM

**When to use**:
- Grant access only when specific conditions are met
- Time-based access, IP-based restrictions

```python
# ❌ Bad: Grant broad access without conditions
# Member can access from anywhere, anytime
gcloud projects add-iam-policy-binding my-project \
  --member=user:contractor@example.com \
  --role=roles/compute.admin

# ✅ Good: Conditional access with time and IP restrictions
from google.cloud import iam_v1

def add_conditional_binding(project_id, member, role):
    client = iam_v1.IAMPolicyClient()

    policy = client.get_iam_policy(request={"resource": f"projects/{project_id}"})

    # Add conditional binding
    binding = iam_v1.Binding(
        role=role,
        members=[member],
        condition=iam_v1.Expr(
            title="Temporary access during business hours",
            description="Access granted Mon-Fri 9am-5pm from office IP",
            expression="""
                request.time.getHours("America/Los_Angeles") >= 9 &&
                request.time.getHours("America/Los_Angeles") < 17 &&
                request.time.getDayOfWeek("America/Los_Angeles") >= 1 &&
                request.time.getDayOfWeek("America/Los_Angeles") <= 5 &&
                inIpRange(request.ip, '203.0.113.0/24')
            """
        )
    )

    policy.bindings.append(binding)
    client.set_iam_policy(request={"resource": f"projects/{project_id}", "policy": policy})
```

**Benefits**:
- Enforce time-based access for contractors
- Restrict access to specific IP ranges (VPN, office)
- Reduce attack surface and unauthorized access

### Pattern 2: Service Account Impersonation

**Use case**: Developers test with service account permissions without downloading keys

```bash
# ❌ Bad: Download service account key and share with developers
gcloud iam service-accounts keys create key.json \
  --iam-account=app@my-project.iam.gserviceaccount.com
# Key can be leaked, no audit trail

# ✅ Good: Grant impersonation permission to developer
gcloud iam service-accounts add-iam-policy-binding \
  app@my-project.iam.gserviceaccount.com \
  --member=user:dev@example.com \
  --role=roles/iam.serviceAccountTokenCreator

# Developer impersonates service account
gcloud compute instances list \
  --impersonate-service-account=app@my-project.iam.gserviceaccount.com

# Or in code
from google.auth import impersonated_credentials
import google.auth

source_credentials, project_id = google.auth.default()

target_scopes = ['https://www.googleapis.com/auth/cloud-platform']
target_credentials = impersonated_credentials.Credentials(
    source_credentials=source_credentials,
    target_principal='app@my-project.iam.gserviceaccount.com',
    target_scopes=target_scopes
)
```

### Pattern 3: Secret Rotation with Versions

**Use case**: Rotate secrets without downtime

```python
from google.cloud import secretmanager

def rotate_secret(project_id, secret_id, new_value):
    client = secretmanager.SecretManagerServiceClient()

    # Add new version
    secret_name = f"projects/{project_id}/secrets/{secret_id}"
    payload = new_value.encode("UTF-8")

    new_version = client.add_secret_version(
        request={
            "parent": secret_name,
            "payload": {"data": payload}
        }
    )

    # Application automatically uses latest version
    # After verifying new version works:

    # Disable old versions (don't delete immediately)
    versions = client.list_secret_versions(request={"parent": secret_name})
    for version in versions:
        if version.name != new_version.name:
            client.disable_secret_version(request={"name": version.name})

    # After grace period (e.g., 30 days), destroy old versions
    # client.destroy_secret_version(request={"name": old_version.name})

    return new_version
```

### Pattern 4: Organization Policies

**Use case**: Enforce security constraints across entire organization

```bash
# Disable service account key creation organization-wide
gcloud resource-manager org-policies set-policy \
  --organization=ORGANIZATION_ID \
  policy.yaml

# policy.yaml
constraint: constraints/iam.disableServiceAccountKeyCreation
listPolicy:
  allValues: DENY

# Restrict VM external IPs to specific projects
constraint: constraints/compute.vmExternalIpAccess
listPolicy:
  allowedValues:
    - projects/production-project
    - projects/staging-project
  deniedValues:
    - projects/dev-project

# Require CMEK encryption for Cloud Storage
constraint: constraints/storage.requireCMEK
booleanPolicy:
  enforced: true
```

### Pattern 5: Workload Identity for GKE

**Use case**: Pods authenticate as GCP service accounts without key files

```bash
# ❌ Bad: Mount service account key as Kubernetes secret
kubectl create secret generic gcp-key \
  --from-file=key.json=./service-account-key.json
# Key can be extracted from cluster

# ✅ Good: Use Workload Identity
# Enable Workload Identity on cluster
gcloud container clusters create prod-cluster \
  --workload-pool=my-project.svc.id.goog \
  --zone=us-central1-a

# Create Kubernetes service account
kubectl create serviceaccount app-sa

# Create GCP service account
gcloud iam service-accounts create app-gsa

# Grant GCP permissions to service account
gcloud projects add-iam-policy-binding my-project \
  --member=serviceAccount:app-gsa@my-project.iam.gserviceaccount.com \
  --role=roles/storage.objectViewer

# Bind Kubernetes SA to GCP SA
gcloud iam service-accounts add-iam-policy-binding \
  app-gsa@my-project.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:my-project.svc.id.goog[default/app-sa]"

# Annotate Kubernetes service account
kubectl annotate serviceaccount app-sa \
  iam.gke.io/gcp-service-account=app-gsa@my-project.iam.gserviceaccount.com

# Pods using app-sa automatically get GCP credentials
```

### Pattern 6: Audit Logging

**Use case**: Track who did what, when, and from where

```python
from google.cloud import logging

def query_admin_activity_logs(project_id, hours=24):
    client = logging.Client(project=project_id)

    # Query admin activity logs
    filter_str = f"""
        logName="projects/{project_id}/logs/cloudaudit.googleapis.com%2Factivity"
        AND timestamp >= "{hours}h"
        AND protoPayload.methodName:"compute.instances.delete"
    """

    entries = client.list_entries(filter_=filter_str)

    for entry in entries:
        print(f"User: {entry.payload.get('authenticationInfo', {}).get('principalEmail')}")
        print(f"Action: {entry.payload.get('methodName')}")
        print(f"Resource: {entry.payload.get('resourceName')}")
        print(f"Time: {entry.timestamp}")
        print(f"IP: {entry.payload.get('requestMetadata', {}).get('callerIp')}")
        print("---")
```

```bash
# Create log sink to export logs to Cloud Storage
gcloud logging sinks create audit-logs-sink \
  storage.googleapis.com/audit-logs-bucket \
  --log-filter='logName:"cloudaudit.googleapis.com"'
```

### Pattern 7: VPC Service Controls

**Use case**: Create security perimeters to prevent data exfiltration

```bash
# Create access policy
gcloud access-context-manager policies create \
  --organization=ORGANIZATION_ID \
  --title="Corporate Policy"

# Create access level (who can access)
gcloud access-context-manager levels create corporate_network \
  --policy=POLICY_ID \
  --title="Corporate Network" \
  --basic-level-spec=access_level.yaml

# access_level.yaml
ipSubnetworks:
  - 203.0.113.0/24  # Office IP range

# Create service perimeter (what resources are protected)
gcloud access-context-manager perimeters create production_perimeter \
  --policy=POLICY_ID \
  --title="Production Data" \
  --resources=projects/123456789 \
  --restricted-services=storage.googleapis.com,bigquery.googleapis.com \
  --access-levels=corporate_network

# Now Cloud Storage and BigQuery in project can only be accessed from office IP
```

### Pattern 8: IAM Recommender

**Use case**: Identify and remove excessive permissions

```bash
# List IAM recommendations
gcloud recommender recommendations list \
  --project=my-project \
  --location=global \
  --recommender=google.iam.policy.Recommender

# Apply recommendation to remove unused permissions
gcloud recommender recommendations mark-claimed \
  RECOMMENDATION_ID \
  --project=my-project \
  --location=global \
  --recommender=google.iam.policy.Recommender

# After testing, mark as succeeded
gcloud recommender recommendations mark-succeeded \
  RECOMMENDATION_ID \
  --project=my-project \
  --location=global \
  --recommender=google.iam.policy.Recommender
```

---

## Quick Reference

### IAM Role Types

```
Role Type     | Example                        | Use Case
--------------|--------------------------------|----------------------------
Basic         | Owner, Editor, Viewer          | Avoid in production (too broad)
Predefined    | roles/compute.instanceAdmin.v1 | Use for common scenarios
Custom        | customStorageRole              | Fine-grained permissions
```

### Key gcloud Commands

```bash
# IAM
gcloud projects add-iam-policy-binding PROJECT --member=MEMBER --role=ROLE
gcloud projects get-iam-policy PROJECT
gcloud projects remove-iam-policy-binding PROJECT --member=MEMBER --role=ROLE

# Service Accounts
gcloud iam service-accounts create SA_ID --display-name=NAME
gcloud iam service-accounts list
gcloud iam service-accounts keys create key.json --iam-account=SA_EMAIL

# Secrets
gcloud secrets create SECRET_ID --replication-policy=automatic
gcloud secrets versions add SECRET_ID --data-file=secret.txt
gcloud secrets versions access latest --secret=SECRET_ID

# KMS
gcloud kms keyrings create KEYRING --location=LOCATION
gcloud kms keys create KEY --keyring=KEYRING --location=LOCATION --purpose=encryption
```

### Security Best Practices

```
✅ DO: Use predefined roles over basic roles (Owner/Editor/Viewer)
✅ DO: Rotate service account keys every 90 days (or use Workload Identity)
✅ DO: Enable audit logging for all projects
✅ DO: Use Secret Manager for sensitive data (never hardcode)
✅ DO: Implement VPC Service Controls for sensitive data
✅ DO: Review IAM Recommender suggestions monthly

❌ DON'T: Use basic roles in production (too broad)
❌ DON'T: Download service account keys (use Workload Identity)
❌ DON'T: Store secrets in environment variables or code
❌ DON'T: Grant project-level permissions when resource-level suffices
❌ DON'T: Ignore audit logs (monitor for anomalies)
```

---

## Anti-Patterns

### Critical Violations

```bash
# ❌ NEVER: Grant Owner role to service accounts
gcloud projects add-iam-policy-binding my-project \
  --member=serviceAccount:app@my-project.iam.gserviceaccount.com \
  --role=roles/owner
# Service account can delete entire project!

# ✅ CORRECT: Grant minimal permissions needed
gcloud projects add-iam-policy-binding my-project \
  --member=serviceAccount:app@my-project.iam.gserviceaccount.com \
  --role=roles/storage.objectViewer

gcloud storage buckets add-iam-policy-binding gs://specific-bucket \
  --member=serviceAccount:app@my-project.iam.gserviceaccount.com \
  --role=roles/storage.objectAdmin
```

❌ **Overly broad service account permissions**: Granting Owner or Editor to service accounts creates massive security risk.
✅ **Correct approach**: Grant specific predefined roles at resource level, not project level.

### Common Mistakes

```python
# ❌ Don't: Hardcode secrets in code (example of what NOT to do)
DATABASE_PASSWORD = "super_secret_password"  # Exposed in source control! Example only

# ✅ Correct: Load from Secret Manager
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
name = f"projects/my-project/secrets/db-password/versions/latest"
response = client.access_secret_version(request={"name": name})
DATABASE_PASSWORD = response.payload.data.decode("UTF-8")
```

❌ **Hardcoded secrets**: Secrets in code are exposed via source control, logs, and error messages.
✅ **Better**: Store all secrets in Secret Manager and retrieve at runtime.

```bash
# ❌ Don't: Create service account keys unnecessarily
gcloud iam service-accounts keys create key.json \
  --iam-account=app@my-project.iam.gserviceaccount.com
# Keys can be leaked, hard to rotate

# ✅ Correct: Use Workload Identity (GKE) or Application Default Credentials
# On GCE/GKE/Cloud Run: Automatically uses instance/pod service account
# On local dev: Use impersonation
gcloud auth application-default login \
  --impersonate-service-account=app@my-project.iam.gserviceaccount.com
```

❌ **Service account key files**: Keys are long-lived credentials that can be leaked and are difficult to rotate.
✅ **Better**: Use Workload Identity for GKE, instance service accounts for GCE, or impersonation for development.

```bash
# ❌ Don't: Disable organization policies to "get things working"
gcloud resource-manager org-policies disable-enforce \
  constraints/compute.requireOsLogin \
  --organization=ORG_ID
# Opens security hole across entire organization

# ✅ Correct: Understand policy and create exception if needed
gcloud resource-manager org-policies set-policy \
  --organization=ORG_ID \
  policy.yaml

# policy.yaml - Allow exception for specific project
constraint: constraints/compute.requireOsLogin
listPolicy:
  deniedValues:
    - projects/legacy-project  # Exception for legacy system
```

❌ **Disabling org policies**: Disabling organization-wide policies creates security vulnerabilities.
✅ **Better**: Understand the policy requirement and create targeted exceptions if absolutely necessary.

---

## Related Skills

- `gcp-compute.md` - Service accounts for Compute Engine instances
- `gcp-databases.md` - Database user management and IAM authentication
- `gcp-storage.md` - Bucket IAM policies and signed URLs
- `gcp-networking.md` - Firewall rules and network security

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
