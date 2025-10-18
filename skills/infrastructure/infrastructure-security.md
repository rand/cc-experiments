---
name: infrastructure-infrastructure-security
description: Setting up IAM roles and policies
---


# Infrastructure Security

**Scope**: Security best practices - IAM, security groups, secrets management, encryption
**Lines**: 381
**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

**Activate when**:
- Setting up IAM roles and policies
- Configuring network security (security groups, NACLs)
- Managing secrets and credentials
- Implementing encryption at rest and in transit
- Establishing least privilege access
- Securing API endpoints and services

**Prerequisites**:
- Understanding of cloud provider (AWS, GCP, Azure)
- Basic networking knowledge (CIDR, ports, protocols)
- Familiarity with cryptography concepts
- Access to cloud provider console/CLI
- Understanding of compliance requirements (if applicable)

**Common scenarios**:
- Securing serverless applications
- Multi-tier application security
- Database encryption and access control
- API authentication and authorization
- Secrets rotation and management
- Compliance with SOC2, HIPAA, PCI-DSS

---

## Core Concepts

### 1. IAM Policies (AWS)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaDynamoDBAccess",
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
    },
    {
      "Sid": "S3ReadAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ],
      "Condition": {
        "StringLike": {
          "s3:prefix": ["public/*"]
        }
      }
    },
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-credentials-*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### 2. IAM Roles and Trust Policies

```json
// Trust policy - who can assume this role
{
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

// Cross-account access trust policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::987654321098:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "unique-external-id-12345"
        }
      }
    }
  ]
}
```

### 3. Security Groups

```hcl
# Terraform - Web tier security group
resource "aws_security_group" "web" {
  name        = "web-tier-sg"
  description = "Security group for web tier"
  vpc_id      = var.vpc_id

  # Inbound rules
  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound rules
  egress {
    description     = "To app tier"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    description = "HTTPS to internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "web-tier-sg"
    Tier = "web"
  }
}

# Application tier security group
resource "aws_security_group" "app" {
  name        = "app-tier-sg"
  description = "Security group for app tier"
  vpc_id      = var.vpc_id

  ingress {
    description     = "From web tier"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }

  egress {
    description     = "To database"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.database.id]
  }

  tags = {
    Name = "app-tier-sg"
    Tier = "app"
  }
}

# Database tier security group
resource "aws_security_group" "database" {
  name        = "database-tier-sg"
  description = "Security group for database tier"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from app tier"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  # No outbound rules - database doesn't initiate connections

  tags = {
    Name = "database-tier-sg"
    Tier = "database"
  }
}
```

### 4. Secrets Management

```python
# AWS Secrets Manager
import boto3
import json
from botocore.exceptions import ClientError

def get_secret(secret_name, region_name="us-east-1"):
    """Retrieve secret from AWS Secrets Manager"""
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        response = client.get_secret_value(SecretId=secret_name)

        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        else:
            # Binary secret
            return response['SecretBinary']

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"Secret {secret_name} not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            print(f"Invalid request for secret {secret_name}")
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            print(f"Invalid parameter for secret {secret_name}")
        raise e

# Lambda function using secrets
import os

def lambda_handler(event, context):
    # Get database credentials
    db_secret = get_secret(os.environ['DB_SECRET_NAME'])

    # Use credentials
    db_host = db_secret['host']
    db_user = db_secret['username']
    db_password = db_secret['password']

    # Connect to database
    # ...

# Create/update secret
def create_secret(secret_name, secret_value, region_name="us-east-1"):
    """Create or update a secret"""
    client = boto3.client('secretsmanager', region_name=region_name)

    try:
        response = client.create_secret(
            Name=secret_name,
            SecretString=json.dumps(secret_value),
            Tags=[
                {'Key': 'Environment', 'Value': 'production'},
                {'Key': 'ManagedBy', 'Value': 'terraform'}
            ]
        )
        return response['ARN']
    except client.exceptions.ResourceExistsException:
        # Update existing secret
        response = client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(secret_value)
        )
        return response['ARN']

# Rotate secret
def rotate_secret(secret_name):
    """Rotate secret (requires Lambda rotation function)"""
    client = boto3.client('secretsmanager')

    response = client.rotate_secret(
        SecretId=secret_name,
        RotationLambdaARN='arn:aws:lambda:us-east-1:123456789012:function:rotate-secret',
        RotationRules={
            'AutomaticallyAfterDays': 30
        }
    )
    return response
```

### 5. Encryption

```python
# S3 encryption at rest
import boto3

s3 = boto3.client('s3')

# Server-side encryption with S3-managed keys (SSE-S3)
s3.put_object(
    Bucket='my-bucket',
    Key='file.txt',
    Body=b'data',
    ServerSideEncryption='AES256'
)

# Server-side encryption with KMS (SSE-KMS)
s3.put_object(
    Bucket='my-bucket',
    Key='file.txt',
    Body=b'data',
    ServerSideEncryption='aws:kms',
    SSEKMSKeyId='arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012'
)

# Client-side encryption
from cryptography.fernet import Fernet

# Generate key (store in Secrets Manager)
key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt data
plaintext = b"sensitive data"
ciphertext = cipher.encrypt(plaintext)

# Upload encrypted data
s3.put_object(
    Bucket='my-bucket',
    Key='encrypted-file.txt',
    Body=ciphertext
)

# Decrypt data
encrypted_data = s3.get_object(Bucket='my-bucket', Key='encrypted-file.txt')['Body'].read()
decrypted_data = cipher.decrypt(encrypted_data)
```

### 6. Network ACLs

```hcl
# Terraform - Network ACL for public subnet
resource "aws_network_acl" "public" {
  vpc_id     = var.vpc_id
  subnet_ids = var.public_subnet_ids

  # Inbound rules
  ingress {
    rule_no    = 100
    protocol   = "tcp"
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 443
    to_port    = 443
  }

  ingress {
    rule_no    = 110
    protocol   = "tcp"
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 80
    to_port    = 80
  }

  ingress {
    rule_no    = 120
    protocol   = "tcp"
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 1024
    to_port    = 65535  # Ephemeral ports for return traffic
  }

  # Deny all other inbound
  ingress {
    rule_no    = 32767
    protocol   = "-1"
    action     = "deny"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  # Outbound rules
  egress {
    rule_no    = 100
    protocol   = "-1"
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  tags = {
    Name = "public-nacl"
  }
}
```

---

## Patterns

### Least Privilege IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SpecificResourceAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/Users",
      "Condition": {
        "ForAllValues:StringEquals": {
          "dynamodb:LeadingKeys": ["${aws:username}"]
        }
      }
    },
    {
      "Sid": "DenyUnencryptedUploads",
      "Effect": "Deny",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    }
  ]
}
```

### Multi-Factor Authentication

```json
// Require MFA for sensitive operations
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowViewAccountInfo",
      "Effect": "Allow",
      "Action": [
        "iam:GetAccountPasswordPolicy",
        "iam:ListVirtualMFADevices"
      ],
      "Resource": "*"
    },
    {
      "Sid": "RequireMFAForSensitiveOperations",
      "Effect": "Allow",
      "Action": [
        "ec2:TerminateInstances",
        "rds:DeleteDBInstance",
        "s3:DeleteBucket"
      ],
      "Resource": "*",
      "Condition": {
        "Bool": {
          "aws:MultiFactorAuthPresent": "true"
        },
        "NumericLessThan": {
          "aws:MultiFactorAuthAge": "3600"
        }
      }
    }
  ]
}
```

### VPC Endpoints for Private Access

```hcl
# Private access to AWS services without internet gateway
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = var.vpc_id
  service_name = "com.amazonaws.us-east-1.s3"

  route_table_ids = var.private_route_table_ids

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowS3Access"
        Effect = "Allow"
        Principal = "*"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "arn:aws:s3:::my-private-bucket/*"
      }
    ]
  })

  tags = {
    Name = "s3-vpc-endpoint"
  }
}

# Interface endpoint for other services
resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.us-east-1.secretsmanager"
  vpc_endpoint_type   = "Interface"

  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [aws_security_group.vpc_endpoint.id]

  private_dns_enabled = true

  tags = {
    Name = "secretsmanager-vpc-endpoint"
  }
}
```

### Certificate Management

```python
# AWS Certificate Manager
import boto3

acm = boto3.client('acm')

# Request certificate
response = acm.request_certificate(
    DomainName='example.com',
    SubjectAlternativeNames=[
        '*.example.com',
        'www.example.com'
    ],
    ValidationMethod='DNS',
    Tags=[
        {'Key': 'Environment', 'Value': 'production'}
    ]
)

certificate_arn = response['CertificateArn']

# Get certificate validation records
response = acm.describe_certificate(CertificateArn=certificate_arn)
validation_options = response['Certificate']['DomainValidationOptions']

# Create Route53 validation records automatically
route53 = boto3.client('route53')
for option in validation_options:
    route53.change_resource_record_sets(
        HostedZoneId='Z1234567890ABC',
        ChangeBatch={
            'Changes': [{
                'Action': 'CREATE',
                'ResourceRecordSet': {
                    'Name': option['ResourceRecord']['Name'],
                    'Type': option['ResourceRecord']['Type'],
                    'TTL': 300,
                    'ResourceRecords': [{'Value': option['ResourceRecord']['Value']}]
                }
            }]
        }
    )
```

### API Authentication

```python
# Lambda authorizer for API Gateway
import json

def lambda_handler(event, context):
    """
    Custom authorizer for API Gateway
    Validates JWT or API key
    """
    token = event['authorizationToken']  # Bearer token
    method_arn = event['methodArn']

    # Validate token (check signature, expiration, etc.)
    if validate_token(token):
        principal_id = extract_user_id(token)
        policy = generate_policy(principal_id, 'Allow', method_arn)

        # Add context to pass to Lambda function
        policy['context'] = {
            'userId': principal_id,
            'role': extract_role(token)
        }

        return policy
    else:
        raise Exception('Unauthorized')

def generate_policy(principal_id, effect, resource):
    """Generate IAM policy"""
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': resource
            }]
        }
    }
    return policy

def validate_token(token):
    """Validate JWT token"""
    # Implementation depends on your token type
    # For JWT: decode, verify signature, check expiration
    return True  # Simplified

def extract_user_id(token):
    """Extract user ID from token"""
    return "user123"  # Simplified

def extract_role(token):
    """Extract role from token"""
    return "admin"  # Simplified
```

---

## Quick Reference

### AWS IAM Best Practices

```bash
# Enable MFA for root account
# Create IAM users instead of using root
# Use groups to assign permissions
# Grant least privilege
# Use roles for applications
# Rotate credentials regularly
# Enable CloudTrail for auditing

# AWS CLI
aws iam create-user --user-name developer
aws iam create-group --group-name developers
aws iam add-user-to-group --user-name developer --group-name developers
aws iam attach-group-policy --group-name developers --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# Create access key
aws iam create-access-key --user-name developer

# Rotate access key
aws iam update-access-key --access-key-id AKIAIOSFODNN7EXAMPLE --status Inactive --user-name developer
aws iam delete-access-key --access-key-id AKIAIOSFODNN7EXAMPLE --user-name developer
```

### Security Checklist

```
[ ] IAM users have MFA enabled
[ ] Root account not used for daily tasks
[ ] Least privilege policies applied
[ ] Security groups follow principle of least access
[ ] Encryption at rest enabled (S3, EBS, RDS)
[ ] Encryption in transit enforced (HTTPS, TLS)
[ ] Secrets stored in Secrets Manager/Parameter Store
[ ] CloudTrail enabled for audit logging
[ ] VPC Flow Logs enabled
[ ] Regular security scans (AWS Inspector, GuardDuty)
[ ] Backup and disaster recovery plan
[ ] Network segmentation (public/private subnets)
[ ] WAF configured for web applications
[ ] Regular security patches applied
```

---

## Anti-Patterns

### Critical Violations

```json
// ❌ NEVER: Use wildcard permissions in production
{
  "Effect": "Allow",
  "Action": "*",
  "Resource": "*"
}

// ✅ CORRECT: Specific permissions
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": "arn:aws:s3:::my-bucket/path/*"
}
```

```python
# ❌ NEVER: Hardcode credentials
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# ✅ CORRECT: Use IAM roles or environment variables
import boto3
# Uses IAM role credentials automatically
s3 = boto3.client('s3')

# Or environment variables
import os
access_key = os.environ['AWS_ACCESS_KEY_ID']
```

```hcl
# ❌ NEVER: Open security groups to 0.0.0.0/0 for SSH
resource "aws_security_group_rule" "ssh" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]  # Dangerous!
  security_group_id = aws_security_group.example.id
}

# ✅ CORRECT: Restrict to specific IPs or use bastion
resource "aws_security_group_rule" "ssh" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["10.0.0.0/16"]  # Internal only
  security_group_id = aws_security_group.example.id
}
```

---

## Related Skills

**Infrastructure**:
- `aws-serverless.md` - IAM roles for Lambda, API Gateway authorizers
- `terraform-patterns.md` - Infrastructure as Code for security resources
- `kubernetes-basics.md` - RBAC, network policies, secrets

**Networking**:
- `mtls-implementation.md` - Mutual TLS for service-to-service auth
- `tailscale-vpn.md` - Zero-trust networking

**Standards from CLAUDE.md**:
- Never hardcode credentials
- Use IAM roles for services
- Principle of least privilege
- Encryption at rest and in transit
- Secrets in Secrets Manager
- MFA for sensitive operations

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
