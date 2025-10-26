---
name: cloud-aws-iam-security
description: AWS IAM policies, roles, Cognito authentication, Secrets Manager, KMS encryption, and security best practices
---

# AWS IAM Security

**Scope**: AWS security - IAM policies, roles, Cognito, Secrets Manager, KMS, STS, least privilege, credential management
**Lines**: ~340
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Creating IAM policies and roles for AWS services
- Implementing user authentication with Cognito
- Managing secrets with Secrets Manager or Parameter Store
- Configuring encryption with KMS
- Setting up temporary credentials with STS
- Implementing least privilege access control
- Troubleshooting permission errors or access denied issues
- Auditing security configurations and credentials

## Core Concepts

### Concept 1: IAM Policies

**Policy types**:
- **Identity-based**: Attached to users, groups, roles
- **Resource-based**: Attached to resources (S3, Lambda)
- **Permission boundaries**: Maximum permissions
- **Service control policies**: Organization-level restrictions

```python
import boto3
import json

iam = boto3.client('iam')

def create_lambda_execution_role():
    """Create IAM role for Lambda with least privilege"""

    # Trust policy - who can assume this role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    # Create role
    role_response = iam.create_role(
        RoleName='lambda-execution-role',
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description='Execution role for Lambda functions',
        Tags=[
            {'Key': 'Purpose', 'Value': 'Lambda'},
            {'Key': 'ManagedBy', 'Value': 'automation'}
        ]
    )

    role_arn = role_response['Role']['Arn']

    # Attach AWS managed policy for CloudWatch Logs
    iam.attach_role_policy(
        RoleName='lambda-execution-role',
        PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
    )

    # Create custom policy for DynamoDB access
    dynamodb_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query"
                ],
                "Resource": [
                    "arn:aws:dynamodb:us-east-1:123456789012:table/Users",
                    "arn:aws:dynamodb:us-east-1:123456789012:table/Users/index/*"
                ]
            }
        ]
    }

    # Create and attach custom policy
    policy_response = iam.create_policy(
        PolicyName='lambda-dynamodb-access',
        PolicyDocument=json.dumps(dynamodb_policy),
        Description='Allow Lambda to access DynamoDB Users table'
    )

    iam.attach_role_policy(
        RoleName='lambda-execution-role',
        PolicyArn=policy_response['Policy']['Arn']
    )

    print(f"Created Lambda execution role: {role_arn}")

    return role_arn

def create_s3_readonly_policy(bucket_name):
    """Create policy for read-only S3 access"""

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*"
                ]
            }
        ]
    }

    response = iam.create_policy(
        PolicyName=f'{bucket_name}-readonly',
        PolicyDocument=json.dumps(policy)
    )

    return response['Policy']['Arn']
```

### Concept 2: Cognito User Authentication

**Cognito components**:
- **User Pools**: User directory, sign-up/sign-in
- **Identity Pools**: AWS credentials for users
- **Authentication flows**: Username/password, OAuth, SAML

```python
import boto3

cognito = boto3.client('cognito-idp')

def create_user_pool():
    """Create Cognito User Pool for authentication"""

    response = cognito.create_user_pool(
        PoolName='myapp-users',
        Policies={
            'PasswordPolicy': {
                'MinimumLength': 12,
                'RequireUppercase': True,
                'RequireLowercase': True,
                'RequireNumbers': True,
                'RequireSymbols': True
            }
        },
        AutoVerifiedAttributes=['email'],
        EmailConfiguration={
            'EmailSendingAccount': 'COGNITO_DEFAULT'
        },
        Schema=[
            {
                'Name': 'email',
                'AttributeDataType': 'String',
                'Required': True,
                'Mutable': False
            },
            {
                'Name': 'name',
                'AttributeDataType': 'String',
                'Required': True,
                'Mutable': True
            }
        ],
        MfaConfiguration='OPTIONAL',
        UserAttributeUpdateSettings={
            'AttributesRequireVerificationBeforeUpdate': ['email']
        }
    )

    user_pool_id = response['UserPool']['Id']

    # Create app client
    app_response = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName='myapp-web',
        GenerateSecret=False,  # Public client (SPA)
        RefreshTokenValidity=30,  # Days
        AccessTokenValidity=60,  # Minutes
        IdTokenValidity=60,
        TokenValidityUnits={
            'RefreshToken': 'days',
            'AccessToken': 'minutes',
            'IdToken': 'minutes'
        },
        ExplicitAuthFlows=[
            'ALLOW_USER_PASSWORD_AUTH',
            'ALLOW_REFRESH_TOKEN_AUTH'
        ]
    )

    client_id = app_response['UserPoolClient']['ClientId']

    print(f"Created User Pool: {user_pool_id}")
    print(f"App Client ID: {client_id}")

    return user_pool_id, client_id

def authenticate_user(username, password, client_id):
    """Authenticate user and get tokens"""

    response = cognito.initiate_auth(
        ClientId=client_id,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password
        }
    )

    # Get tokens
    id_token = response['AuthenticationResult']['IdToken']
    access_token = response['AuthenticationResult']['AccessToken']
    refresh_token = response['AuthenticationResult']['RefreshToken']

    return {
        'id_token': id_token,
        'access_token': access_token,
        'refresh_token': refresh_token
    }
```

### Concept 3: Secrets Manager

**Secrets Manager vs Parameter Store**:
- **Secrets Manager**: Automatic rotation, audit, encryption ($0.40/secret/month)
- **Parameter Store**: Simple key-value, cheaper (free tier available)

```python
import boto3
import json

secrets = boto3.client('secretsmanager')

def create_database_secret(db_username, db_password, db_host, db_name):
    """Store database credentials in Secrets Manager"""

    secret_value = {
        'username': db_username,
        'password': db_password,
        'host': db_host,
        'database': db_name,
        'port': 5432
    }

    response = secrets.create_secret(
        Name='myapp/database/credentials',
        Description='Database credentials for myapp',
        SecretString=json.dumps(secret_value),
        Tags=[
            {'Key': 'Environment', 'Value': 'production'},
            {'Key': 'Application', 'Value': 'myapp'}
        ]
    )

    print(f"Created secret: {response['ARN']}")

    return response['ARN']

def get_database_secret():
    """Retrieve database credentials"""

    response = secrets.get_secret_value(
        SecretId='myapp/database/credentials'
    )

    secret_data = json.loads(response['SecretString'])

    return {
        'username': secret_data['username'],
        'password': secret_data['password'],
        'host': secret_data['host'],
        'database': secret_data['database'],
        'port': secret_data['port']
    }

def rotate_secret(secret_id, lambda_arn):
    """Configure automatic rotation"""

    secrets.rotate_secret(
        SecretId=secret_id,
        RotationLambdaARN=lambda_arn,
        RotationRules={
            'AutomaticallyAfterDays': 30
        }
    )

    print(f"Configured rotation for {secret_id}")
```

### Concept 4: KMS Encryption

**KMS key types**:
- **AWS managed**: Created by AWS services (free)
- **Customer managed**: Full control, custom policies
- **Symmetric**: Same key for encrypt/decrypt
- **Asymmetric**: Public/private key pair

```python
import boto3
import base64

kms = boto3.client('kms')

def create_kms_key():
    """Create customer-managed KMS key"""

    response = kms.create_key(
        Description='Application data encryption key',
        KeyUsage='ENCRYPT_DECRYPT',
        Origin='AWS_KMS',
        MultiRegion=False,
        Tags=[
            {'TagKey': 'Application', 'TagValue': 'myapp'},
            {'TagKey': 'Purpose', 'TagValue': 'data-encryption'}
        ]
    )

    key_id = response['KeyMetadata']['KeyId']

    # Create alias
    kms.create_alias(
        AliasName='alias/myapp-data-key',
        TargetKeyId=key_id
    )

    print(f"Created KMS key: {key_id}")

    return key_id

def encrypt_data(plaintext, key_id):
    """Encrypt data with KMS key"""

    response = kms.encrypt(
        KeyId=key_id,
        Plaintext=plaintext.encode('utf-8')
    )

    # Return base64-encoded ciphertext
    ciphertext_blob = response['CiphertextBlob']
    encrypted = base64.b64encode(ciphertext_blob).decode('utf-8')

    return encrypted

def decrypt_data(encrypted_data):
    """Decrypt data (KMS determines key automatically)"""

    # Decode base64
    ciphertext_blob = base64.b64decode(encrypted_data)

    response = kms.decrypt(
        CiphertextBlob=ciphertext_blob
    )

    plaintext = response['Plaintext'].decode('utf-8')

    return plaintext

def envelope_encryption(plaintext, key_id):
    """Encrypt large data using envelope encryption"""

    # Generate data key
    response = kms.generate_data_key(
        KeyId=key_id,
        KeySpec='AES_256'
    )

    plaintext_key = response['Plaintext']
    encrypted_key = response['CiphertextBlob']

    # Encrypt data with plaintext key (client-side)
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    import os

    iv = os.urandom(16)
    cipher = Cipher(
        algorithms.AES(plaintext_key),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()

    # Pad plaintext to block size
    padded = plaintext + ' ' * (16 - len(plaintext) % 16)
    ciphertext = encryptor.update(padded.encode()) + encryptor.finalize()

    return {
        'encrypted_data': base64.b64encode(ciphertext).decode(),
        'encrypted_key': base64.b64encode(encrypted_key).decode(),
        'iv': base64.b64encode(iv).decode()
    }
```

---

## Patterns

### Pattern 1: Cross-Account Access with STS

**When to use**: Grant temporary access to resources in another account

```python
import boto3

sts = boto3.client('sts')

def assume_role(role_arn, session_name):
    """Assume role in another account"""

    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name,
        DurationSeconds=3600  # 1 hour
    )

    credentials = response['Credentials']

    # Create client with assumed role credentials
    s3_client = boto3.client(
        's3',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )

    return s3_client

# Trust policy for cross-account role
cross_account_trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::123456789012:root"  # Trusting account
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": "unique-external-id"
                }
            }
        }
    ]
}
```

### Pattern 2: Service-to-Service Authentication

**Use case**: EC2 instance accessing S3 without credentials

```python
# No credentials needed - use IAM instance profile

def create_ec2_instance_profile():
    """Create instance profile for EC2"""

    # Create role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    role_response = iam.create_role(
        RoleName='ec2-s3-access-role',
        AssumeRolePolicyDocument=json.dumps(trust_policy)
    )

    # Attach S3 read policy
    iam.attach_role_policy(
        RoleName='ec2-s3-access-role',
        PolicyArn='arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess'
    )

    # Create instance profile
    iam.create_instance_profile(
        InstanceProfileName='ec2-s3-profile'
    )

    # Add role to profile
    iam.add_role_to_instance_profile(
        InstanceProfileName='ec2-s3-profile',
        RoleName='ec2-s3-access-role'
    )

    print("Created instance profile: ec2-s3-profile")

# EC2 instance code - no credentials needed
s3 = boto3.client('s3')  # Automatically uses instance profile
buckets = s3.list_buckets()
```

### Pattern 3: Multi-Factor Authentication (MFA)

**Use case**: Require MFA for sensitive operations

```python
def enforce_mfa_policy():
    """Create policy requiring MFA for sensitive actions"""

    mfa_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowAllActionsWithMFA",
                "Effect": "Allow",
                "Action": "*",
                "Resource": "*",
                "Condition": {
                    "BoolIfExists": {
                        "aws:MultiFactorAuthPresent": "true"
                    }
                }
            },
            {
                "Sid": "DenyAllActionsWithoutMFA",
                "Effect": "Deny",
                "Action": [
                    "ec2:TerminateInstances",
                    "rds:DeleteDBInstance",
                    "s3:DeleteBucket"
                ],
                "Resource": "*",
                "Condition": {
                    "BoolIfExists": {
                        "aws:MultiFactorAuthPresent": "false"
                    }
                }
            }
        ]
    }

    response = iam.create_policy(
        PolicyName='require-mfa-for-sensitive-ops',
        PolicyDocument=json.dumps(mfa_policy)
    )

    return response['Policy']['Arn']
```

### Pattern 4: Least Privilege with Permission Boundaries

**Use case**: Limit maximum permissions for developers

```python
def create_developer_role_with_boundary():
    """Create developer role with permission boundary"""

    # Permission boundary - maximum allowed permissions
    boundary_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:*",
                    "dynamodb:*",
                    "lambda:*",
                    "logs:*",
                    "cloudwatch:*"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Deny",
                "Action": [
                    "iam:*",
                    "organizations:*",
                    "account:*"
                ],
                "Resource": "*"
            }
        ]
    }

    # Create boundary policy
    boundary_response = iam.create_policy(
        PolicyName='developer-boundary',
        PolicyDocument=json.dumps(boundary_policy)
    )

    # Create developer role with boundary
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    iam.create_role(
        RoleName='developer-role',
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        PermissionsBoundary=boundary_response['Policy']['Arn']
    )

    # Developer can only create resources within boundary limits
    print("Created developer role with permission boundary")
```

---

## Quick Reference

### IAM Policy Structure

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DescriptiveStatementId",
      "Effect": "Allow",  // or "Deny"
      "Principal": {"AWS": "arn:aws:iam::123456789012:user/Alice"},
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "IpAddress": {"aws:SourceIp": "192.0.2.0/24"}
      }
    }
  ]
}
```

### Common IAM Actions

```
Service    | Common Actions
-----------|----------------------------------
S3         | s3:GetObject, s3:PutObject, s3:DeleteObject
DynamoDB   | dynamodb:GetItem, dynamodb:PutItem, dynamodb:Query
Lambda     | lambda:InvokeFunction, lambda:UpdateFunctionCode
EC2        | ec2:RunInstances, ec2:TerminateInstances
RDS        | rds:CreateDBInstance, rds:DeleteDBInstance
```

### Key Guidelines

```
✅ DO: Follow principle of least privilege
✅ DO: Use IAM roles instead of access keys
✅ DO: Enable MFA for privileged users
✅ DO: Rotate credentials regularly
✅ DO: Use Secrets Manager for sensitive data
✅ DO: Encrypt data at rest with KMS
✅ DO: Use resource-based policies when possible

❌ DON'T: Hardcode credentials in code
❌ DON'T: Use root account for daily operations
❌ DON'T: Grant full access (*:*) unless absolutely necessary
❌ DON'T: Share IAM user credentials
❌ DON'T: Leave unused access keys active
❌ DON'T: Disable CloudTrail logging
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Hardcode credentials
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# ✅ CORRECT: Use IAM roles (EC2, Lambda) or environment variables
s3 = boto3.client('s3')  # Automatically uses IAM role

# Or for local development
# Use AWS CLI: aws configure
# Or environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
```

❌ **Hardcoded credentials**: Security breach, exposed in code, logs, version control

✅ **Correct approach**: IAM roles for services, AWS CLI config for local, Secrets Manager for apps

### Common Mistakes

```json
// ❌ Don't grant overly broad permissions
{
  "Effect": "Allow",
  "Action": "*",
  "Resource": "*"
}

// ✅ Correct: Specific actions and resources
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": "arn:aws:s3:::my-bucket/data/*"
}
```

❌ **Overly broad permissions**: Security risk, violates least privilege

✅ **Better**: Specific actions, specific resources, conditions when appropriate

---

## Related Skills

- `aws-lambda-functions.md` - IAM execution roles for Lambda
- `aws-ec2-compute.md` - IAM instance profiles for EC2
- `aws-databases.md` - IAM database authentication
- `aws-networking.md` - Security groups and network security

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
