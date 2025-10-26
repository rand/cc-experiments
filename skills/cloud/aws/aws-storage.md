---
name: cloud-aws-storage
description: AWS storage services - S3, EBS, EFS, Glacier, lifecycle policies, encryption, and data transfer
---

# AWS Storage

**Scope**: AWS storage - S3 buckets, EBS volumes, EFS file systems, Glacier archival, lifecycle policies, encryption
**Lines**: ~300
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Storing objects, files, or backups in S3
- Attaching block storage to EC2 with EBS
- Sharing file systems across instances with EFS
- Archiving data long-term with Glacier
- Configuring S3 lifecycle policies for cost optimization
- Setting up S3 event notifications for processing
- Implementing encryption at rest and in transit
- Optimizing data transfer with S3 Transfer Acceleration

## Core Concepts

### Concept 1: S3 Buckets and Storage Classes

**S3 storage classes**:
- **S3 Standard**: Frequent access, low latency ($0.023/GB)
- **S3 Intelligent-Tiering**: Auto-moves between tiers
- **S3 Standard-IA**: Infrequent access ($0.0125/GB)
- **S3 One Zone-IA**: Single AZ, infrequent ($0.01/GB)
- **S3 Glacier Instant**: Archive with instant retrieval
- **S3 Glacier Flexible**: Archive with 1-5 min retrieval
- **S3 Glacier Deep Archive**: Cheapest, 12hr retrieval ($0.00099/GB)

```python
import boto3

s3 = boto3.client('s3')

def create_bucket(bucket_name, region='us-east-1'):
    """Create S3 bucket with versioning and encryption"""

    # Create bucket
    if region == 'us-east-1':
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )

    # Enable versioning
    s3.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Enabled'}
    )

    # Enable default encryption
    s3.put_bucket_encryption(
        Bucket=bucket_name,
        ServerSideEncryptionConfiguration={
            'Rules': [
                {
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'AES256'
                    },
                    'BucketKeyEnabled': True
                }
            ]
        }
    )

    # Block public access
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
    )

    print(f"Created bucket: {bucket_name}")

def upload_object(bucket, key, file_path, storage_class='STANDARD'):
    """Upload file to S3 with storage class"""

    s3.upload_file(
        file_path,
        bucket,
        key,
        ExtraArgs={
            'StorageClass': storage_class,
            'ServerSideEncryption': 'AES256',
            'Metadata': {
                'uploaded-by': 'automation',
                'environment': 'production'
            }
        }
    )

    print(f"Uploaded {key} to {bucket} ({storage_class})")
```

### Concept 2: EBS Volumes

**EBS volume types**:
- **gp3**: General purpose SSD (3,000-16,000 IOPS)
- **io2**: Provisioned IOPS SSD (64,000+ IOPS)
- **st1**: Throughput-optimized HDD (for big data)
- **sc1**: Cold HDD (lowest cost)

```python
import boto3

ec2 = boto3.client('ec2')

def create_and_attach_volume(instance_id, size_gb=100, volume_type='gp3'):
    """Create EBS volume and attach to instance"""

    # Get instance AZ
    response = ec2.describe_instances(InstanceIds=[instance_id])
    az = response['Reservations'][0]['Instances'][0]['Placement']['AvailabilityZone']

    # Create volume
    volume_response = ec2.create_volume(
        AvailabilityZone=az,
        Size=size_gb,
        VolumeType=volume_type,
        Iops=3000 if volume_type == 'gp3' else None,  # gp3 baseline
        Throughput=125 if volume_type == 'gp3' else None,  # MB/s
        Encrypted=True,
        TagSpecifications=[
            {
                'ResourceType': 'volume',
                'Tags': [
                    {'Key': 'Name', 'Value': f'data-volume-{instance_id}'},
                    {'Key': 'ManagedBy', 'Value': 'automation'}
                ]
            }
        ]
    )

    volume_id = volume_response['VolumeId']
    print(f"Created volume: {volume_id}")

    # Wait for volume to be available
    waiter = ec2.get_waiter('volume_available')
    waiter.wait(VolumeIds=[volume_id])

    # Attach volume
    ec2.attach_volume(
        Device='/dev/sdf',
        InstanceId=instance_id,
        VolumeId=volume_id
    )

    print(f"Attached {volume_id} to {instance_id}")

    return volume_id

def create_snapshot(volume_id, description):
    """Create EBS snapshot for backup"""

    response = ec2.create_snapshot(
        VolumeId=volume_id,
        Description=description,
        TagSpecifications=[
            {
                'ResourceType': 'snapshot',
                'Tags': [
                    {'Key': 'BackupType', 'Value': 'automated'},
                    {'Key': 'CreatedBy', 'Value': 'backup-lambda'}
                ]
            }
        ]
    )

    snapshot_id = response['SnapshotId']
    print(f"Creating snapshot: {snapshot_id}")

    return snapshot_id
```

### Concept 3: EFS (Elastic File System)

**EFS use cases**:
- Shared storage across multiple EC2 instances
- Container persistent volumes
- Content management systems
- Development environments

```python
import boto3

efs = boto3.client('efs')

def create_efs_file_system():
    """Create EFS file system with mount targets"""

    # Create file system
    response = efs.create_file_system(
        PerformanceMode='generalPurpose',  # or 'maxIO'
        ThroughputMode='bursting',  # or 'provisioned'
        Encrypted=True,
        Tags=[
            {'Key': 'Name', 'Value': 'shared-storage'},
            {'Key': 'Environment', 'Value': 'production'}
        ]
    )

    fs_id = response['FileSystemId']
    print(f"Created EFS: {fs_id}")

    # Wait for file system to be available
    waiter = efs.get_waiter('file_system_available')
    waiter.wait(FileSystemId=fs_id)

    # Create mount targets in each subnet (AZ)
    subnets = ['subnet-abc123', 'subnet-def456']
    security_group = 'sg-0123456789abcdef0'

    for subnet in subnets:
        efs.create_mount_target(
            FileSystemId=fs_id,
            SubnetId=subnet,
            SecurityGroups=[security_group]
        )

    print(f"Created mount targets for {fs_id}")

    return fs_id

# Mount EFS on EC2 instance (user data script)
EFS_MOUNT_SCRIPT = """#!/bin/bash
# Install EFS utilities
yum install -y amazon-efs-utils

# Create mount point
mkdir -p /mnt/efs

# Mount EFS
mount -t efs -o tls {fs_id}:/ /mnt/efs

# Add to fstab for persistence
echo "{fs_id}:/ /mnt/efs efs defaults,_netdev,tls 0 0" >> /etc/fstab
"""
```

---

## Patterns

### Pattern 1: S3 Lifecycle Policies

**When to use**: Automatic transition to cheaper storage classes

```python
def configure_lifecycle_policy(bucket_name):
    """Configure S3 lifecycle transitions and expiration"""

    s3.put_bucket_lifecycle_configuration(
        Bucket=bucket_name,
        LifecycleConfiguration={
            'Rules': [
                {
                    'Id': 'archive-old-logs',
                    'Status': 'Enabled',
                    'Filter': {'Prefix': 'logs/'},
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'STANDARD_IA'
                        },
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER_FLEXIBLE_RETRIEVAL'
                        },
                        {
                            'Days': 365,
                            'StorageClass': 'DEEP_ARCHIVE'
                        }
                    ],
                    'Expiration': {
                        'Days': 2555  # 7 years
                    }
                },
                {
                    'Id': 'cleanup-temp-files',
                    'Status': 'Enabled',
                    'Filter': {'Prefix': 'temp/'},
                    'Expiration': {
                        'Days': 7
                    },
                    'AbortIncompleteMultipartUpload': {
                        'DaysAfterInitiation': 1
                    }
                },
                {
                    'Id': 'intelligent-tiering',
                    'Status': 'Enabled',
                    'Filter': {'Prefix': 'data/'},
                    'Transitions': [
                        {
                            'Days': 0,
                            'StorageClass': 'INTELLIGENT_TIERING'
                        }
                    ]
                }
            ]
        }
    )

    print(f"Configured lifecycle policy for {bucket_name}")
```

**Benefits**:
- Automatic cost optimization
- No manual intervention
- Compliance retention policies

### Pattern 2: S3 Event Notifications

**Use case**: Trigger Lambda on file upload

```python
def configure_s3_notifications(bucket_name, lambda_arn):
    """Configure S3 to trigger Lambda on object creation"""

    # Grant S3 permission to invoke Lambda
    lambda_client = boto3.client('lambda')
    lambda_client.add_permission(
        FunctionName=lambda_arn.split(':')[-1],
        StatementId='s3-invoke-permission',
        Action='lambda:InvokeFunction',
        Principal='s3.amazonaws.com',
        SourceArn=f'arn:aws:s3:::{bucket_name}'
    )

    # Configure notification
    s3.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={
            'LambdaFunctionConfigurations': [
                {
                    'LambdaFunctionArn': lambda_arn,
                    'Events': ['s3:ObjectCreated:*'],
                    'Filter': {
                        'Key': {
                            'FilterRules': [
                                {'Name': 'prefix', 'Value': 'uploads/'},
                                {'Name': 'suffix', 'Value': '.jpg'}
                            ]
                        }
                    }
                }
            ]
        }
    )

    print(f"Configured S3 notifications for {bucket_name}")
```

### Pattern 3: Presigned URLs

**Use case**: Temporary access to private objects

```python
from botocore.exceptions import ClientError

def generate_presigned_url(bucket, key, expiration=3600):
    """Generate presigned URL for temporary access"""

    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': key
            },
            ExpiresIn=expiration  # Seconds
        )

        return url

    except ClientError as e:
        print(f"Error generating URL: {e}")
        return None

def generate_presigned_upload_url(bucket, key, expiration=3600):
    """Generate presigned URL for upload"""

    url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': bucket,
            'Key': key,
            'ContentType': 'image/jpeg'
        },
        ExpiresIn=expiration,
        HttpMethod='PUT'
    )

    return url

# Usage
download_url = generate_presigned_url('my-bucket', 'private/file.pdf', 300)
upload_url = generate_presigned_upload_url('my-bucket', 'uploads/new.jpg', 600)
```

### Pattern 4: S3 Transfer Acceleration

**Use case**: Fast uploads from distant locations

```bash
# Enable Transfer Acceleration
aws s3api put-bucket-accelerate-configuration \
  --bucket my-bucket \
  --accelerate-configuration Status=Enabled
```

```python
def upload_with_acceleration(bucket, key, file_path):
    """Upload using S3 Transfer Acceleration endpoint"""

    # Create client with accelerate endpoint
    s3_accelerate = boto3.client(
        's3',
        config=boto3.session.Config(
            s3={'use_accelerate_endpoint': True}
        )
    )

    # Upload file
    s3_accelerate.upload_file(file_path, bucket, key)

    print(f"Uploaded {key} using Transfer Acceleration")
```

### Pattern 5: EBS Snapshot Automation

**Use case**: Automated backup strategy

```python
from datetime import datetime, timedelta

def backup_ebs_volumes(tag_key='Backup', tag_value='true'):
    """Create snapshots of tagged volumes"""

    # Find volumes with backup tag
    response = ec2.describe_volumes(
        Filters=[
            {'Name': f'tag:{tag_key}', 'Values': [tag_value]}
        ]
    )

    for volume in response['Volumes']:
        volume_id = volume['VolumeId']

        # Create snapshot
        snapshot = ec2.create_snapshot(
            VolumeId=volume_id,
            Description=f'Automated backup {datetime.utcnow().isoformat()}',
            TagSpecifications=[
                {
                    'ResourceType': 'snapshot',
                    'Tags': [
                        {'Key': 'BackupDate', 'Value': datetime.utcnow().strftime('%Y-%m-%d')},
                        {'Key': 'VolumeId', 'Value': volume_id}
                    ]
                }
            ]
        )

        print(f"Created snapshot {snapshot['SnapshotId']} for {volume_id}")

def cleanup_old_snapshots(retention_days=30):
    """Delete snapshots older than retention period"""

    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    # Find old snapshots
    response = ec2.describe_snapshots(OwnerIds=['self'])

    for snapshot in response['Snapshots']:
        start_time = snapshot['StartTime'].replace(tzinfo=None)

        if start_time < cutoff_date:
            snapshot_id = snapshot['SnapshotId']
            print(f"Deleting old snapshot: {snapshot_id}")

            try:
                ec2.delete_snapshot(SnapshotId=snapshot_id)
            except ClientError as e:
                print(f"Failed to delete {snapshot_id}: {e}")
```

---

## Quick Reference

### Storage Service Selection

| Use Case | Service | Type | Access Pattern |
|----------|---------|------|----------------|
| Objects, files, backups | S3 | Object | API/HTTP |
| Block storage for EC2 | EBS | Block | Attached volume |
| Shared file system | EFS | File | NFS mount |
| Long-term archive | Glacier | Object | Rare retrieval |

### S3 Storage Class Costs (per GB/month)

```
Storage Class              | Cost      | Retrieval    | Use Case
---------------------------|-----------|--------------|------------------
S3 Standard                | $0.023    | Free         | Active data
S3 Intelligent-Tiering     | $0.023+   | Free         | Unknown pattern
S3 Standard-IA             | $0.0125   | $0.01/GB     | Infrequent access
S3 Glacier Instant         | $0.004    | $0.03/GB     | Archive (instant)
S3 Glacier Flexible        | $0.0036   | $0.01/GB     | Archive (mins)
S3 Deep Archive            | $0.00099  | $0.02/GB     | Long-term (hours)
```

### Key Guidelines

```
✅ DO: Enable versioning for critical data
✅ DO: Enable default encryption on all buckets
✅ DO: Use lifecycle policies to reduce costs
✅ DO: Block public access unless explicitly needed
✅ DO: Use presigned URLs for temporary access
✅ DO: Encrypt EBS volumes (especially production)

❌ DON'T: Make buckets public without justification
❌ DON'T: Store sensitive data without encryption
❌ DON'T: Use S3 Standard for infrequent access data
❌ DON'T: Forget to clean up old snapshots
❌ DON'T: Attach EBS volumes across AZs (not possible)
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Create public bucket without justification
s3.create_bucket(Bucket='my-bucket')
s3.put_bucket_acl(Bucket='my-bucket', ACL='public-read')
# All objects publicly accessible!

# ✅ CORRECT: Block public access by default
s3.put_public_access_block(
    Bucket='my-bucket',
    PublicAccessBlockConfiguration={
        'BlockPublicAcls': True,
        'IgnorePublicAcls': True,
        'BlockPublicPolicy': True,
        'RestrictPublicBuckets': True
    }
)
# Use presigned URLs for temporary access
```

❌ **Public buckets**: Data breaches, compliance violations, security incidents

✅ **Correct approach**: Block public access, use presigned URLs or CloudFront

### Common Mistakes

```python
# ❌ Don't use S3 Standard for all data
s3.upload_file('archive.zip', 'my-bucket', 'data/archive.zip')
# Paying $0.023/GB for rarely accessed data

# ✅ Correct: Use appropriate storage class
s3.upload_file(
    'archive.zip',
    'my-bucket',
    'data/archive.zip',
    ExtraArgs={'StorageClass': 'GLACIER_FLEXIBLE_RETRIEVAL'}
)
# Paying $0.0036/GB for archival data
```

❌ **Wrong storage class**: Overpaying for storage based on access patterns

✅ **Better**: Match storage class to access frequency, use lifecycle policies

---

## Related Skills

- `aws-lambda-functions.md` - Process S3 events with Lambda
- `aws-ec2-compute.md` - Attach EBS volumes to EC2 instances
- `aws-databases.md` - Storage for database backups
- `aws-networking.md` - S3 access through VPC endpoints
- `aws-iam-security.md` - S3 bucket policies and IAM permissions

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
