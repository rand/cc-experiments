---
name: cloud-aws-ec2-compute
description: AWS EC2 instances, Auto Scaling, Load Balancing, AMIs, and instance lifecycle management
---

# AWS EC2 Compute

**Scope**: EC2 instances - instance types, Auto Scaling Groups, Elastic Load Balancing, AMIs, user data, spot instances
**Lines**: ~350
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Deploying applications on EC2 instances
- Configuring Auto Scaling for dynamic capacity
- Setting up load balancers (ALB, NLB, CLB)
- Creating and managing AMIs for deployment
- Implementing immutable infrastructure patterns
- Optimizing compute costs with spot instances
- Configuring user data scripts for instance initialization
- Troubleshooting EC2 performance or connectivity issues

## Core Concepts

### Concept 1: EC2 Instance Types and Sizing

**Instance families**:
- **T3/T4g**: Burstable, cost-effective for variable workloads
- **M5/M6i**: General purpose, balanced CPU/memory
- **C5/C6i**: Compute-optimized for CPU-intensive tasks
- **R5/R6i**: Memory-optimized for large datasets
- **I3/I4i**: Storage-optimized for high IOPS

```bash
# Launch t3.medium instance (2 vCPU, 4 GB RAM)
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type t3.medium \
  --key-name my-key-pair \
  --security-group-ids sg-0123456789abcdef0 \
  --subnet-id subnet-0bb1c79de3EXAMPLE

# Launch c5.xlarge for CPU-intensive workload
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type c5.xlarge \
  --count 2 \
  --key-name my-key-pair
```

```python
import boto3

ec2 = boto3.client('ec2')

def launch_instance(instance_type, ami_id, key_name, security_group_ids):
    """Launch EC2 instance with configuration"""

    response = ec2.run_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        KeyName=key_name,
        SecurityGroupIds=security_group_ids,
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': 'my-app-server'},
                    {'Key': 'Environment', 'Value': 'production'}
                ]
            }
        ]
    )

    instance_id = response['Instances'][0]['InstanceId']
    print(f"Launched instance: {instance_id}")

    return instance_id
```

### Concept 2: Auto Scaling Groups

**Auto Scaling benefits**:
- Automatic capacity adjustment
- Health checks and replacement
- Multi-AZ high availability
- Integration with load balancers

```python
import boto3

autoscaling = boto3.client('autoscaling')

def create_auto_scaling_group():
    """Create Auto Scaling Group with launch template"""

    # Create launch template
    ec2 = boto3.client('ec2')
    template_response = ec2.create_launch_template(
        LaunchTemplateName='my-app-template',
        LaunchTemplateData={
            'ImageId': 'ami-0abcdef1234567890',
            'InstanceType': 't3.medium',
            'KeyName': 'my-key-pair',
            'SecurityGroupIds': ['sg-0123456789abcdef0'],
            'UserData': base64.b64encode(USER_DATA.encode()).decode(),
            'IamInstanceProfile': {'Name': 'my-ec2-role'},
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'my-app-asg'},
                        {'Key': 'ManagedBy', 'Value': 'AutoScaling'}
                    ]
                }
            ]
        }
    )

    # Create Auto Scaling Group
    autoscaling.create_auto_scaling_group(
        AutoScalingGroupName='my-app-asg',
        LaunchTemplate={
            'LaunchTemplateName': 'my-app-template',
            'Version': '$Latest'
        },
        MinSize=2,
        MaxSize=10,
        DesiredCapacity=3,
        HealthCheckType='ELB',  # Use load balancer health checks
        HealthCheckGracePeriod=300,
        VPCZoneIdentifier='subnet-abc123,subnet-def456',  # Multi-AZ
        TargetGroupARNs=['arn:aws:elasticloadbalancing:...'],
        Tags=[
            {
                'Key': 'Environment',
                'Value': 'production',
                'PropagateAtLaunch': True
            }
        ]
    )

    print("Created Auto Scaling Group")

# Scaling policies
def create_scaling_policies(asg_name):
    """Create target tracking scaling policy"""

    # Scale based on CPU utilization
    autoscaling.put_scaling_policy(
        AutoScalingGroupName=asg_name,
        PolicyName='cpu-target-tracking',
        PolicyType='TargetTrackingScaling',
        TargetTrackingConfiguration={
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'ASGAverageCPUUtilization'
            },
            'TargetValue': 70.0  # Scale when CPU > 70%
        }
    )

    # Scale based on request count
    autoscaling.put_scaling_policy(
        AutoScalingGroupName=asg_name,
        PolicyName='request-count-tracking',
        PolicyType='TargetTrackingScaling',
        TargetTrackingConfiguration={
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'ALBRequestCountPerTarget',
                'ResourceLabel': 'app/my-alb/abc123/targetgroup/my-tg/def456'
            },
            'TargetValue': 1000.0  # Scale when requests/target > 1000
        }
    )
```

### Concept 3: Elastic Load Balancing

**Load balancer types**:
- **ALB**: Layer 7 (HTTP/HTTPS), host/path routing, WebSocket
- **NLB**: Layer 4 (TCP/UDP), high throughput, static IPs
- **CLB**: Legacy, basic load balancing (deprecated)

```python
import boto3

elbv2 = boto3.client('elbv2')

def create_application_load_balancer():
    """Create Application Load Balancer with target group"""

    # Create ALB
    alb_response = elbv2.create_load_balancer(
        Name='my-app-alb',
        Subnets=['subnet-abc123', 'subnet-def456'],  # Multi-AZ
        SecurityGroups=['sg-0123456789abcdef0'],
        Scheme='internet-facing',
        Type='application',
        IpAddressType='ipv4',
        Tags=[
            {'Key': 'Name', 'Value': 'my-app-alb'},
            {'Key': 'Environment', 'Value': 'production'}
        ]
    )

    alb_arn = alb_response['LoadBalancers'][0]['LoadBalancerArn']
    dns_name = alb_response['LoadBalancers'][0]['DNSName']

    print(f"Created ALB: {dns_name}")

    # Create target group
    tg_response = elbv2.create_target_group(
        Name='my-app-targets',
        Protocol='HTTP',
        Port=80,
        VpcId='vpc-0123456789abcdef0',
        HealthCheckProtocol='HTTP',
        HealthCheckPath='/health',
        HealthCheckIntervalSeconds=30,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=2,
        UnhealthyThresholdCount=3,
        Matcher={'HttpCode': '200'}
    )

    tg_arn = tg_response['TargetGroups'][0]['TargetGroupArn']

    # Create listener
    elbv2.create_listener(
        LoadBalancerArn=alb_arn,
        Protocol='HTTP',
        Port=80,
        DefaultActions=[
            {
                'Type': 'forward',
                'TargetGroupArn': tg_arn
            }
        ]
    )

    return alb_arn, tg_arn

def create_alb_listener_rules(listener_arn, tg_arn_api, tg_arn_web):
    """Create path-based routing rules"""

    # Route /api/* to API target group
    elbv2.create_rule(
        ListenerArn=listener_arn,
        Priority=10,
        Conditions=[
            {
                'Field': 'path-pattern',
                'Values': ['/api/*']
            }
        ],
        Actions=[
            {
                'Type': 'forward',
                'TargetGroupArn': tg_arn_api
            }
        ]
    )

    # Route specific host to different target group
    elbv2.create_rule(
        ListenerArn=listener_arn,
        Priority=20,
        Conditions=[
            {
                'Field': 'host-header',
                'Values': ['admin.example.com']
            }
        ],
        Actions=[
            {
                'Type': 'forward',
                'TargetGroupArn': tg_arn_web
            }
        ]
    )
```

### Concept 4: AMIs and Immutable Infrastructure

**AMI workflow**:
- Build golden image with application
- Launch instances from AMI
- Replace instances instead of patching
- Faster deployments, consistent state

```bash
# Create AMI from running instance
aws ec2 create-image \
  --instance-id i-0123456789abcdef0 \
  --name "my-app-v1.2.3-$(date +%Y%m%d)" \
  --description "My app version 1.2.3" \
  --no-reboot

# Copy AMI to another region
aws ec2 copy-image \
  --source-region us-east-1 \
  --source-image-id ami-0abcdef1234567890 \
  --name "my-app-v1.2.3" \
  --region us-west-2

# Share AMI with another account
aws ec2 modify-image-attribute \
  --image-id ami-0abcdef1234567890 \
  --launch-permission "Add=[{UserId=123456789012}]"
```

```python
import boto3

ec2 = boto3.client('ec2')

def create_ami(instance_id, name, description):
    """Create AMI from instance"""

    response = ec2.create_image(
        InstanceId=instance_id,
        Name=name,
        Description=description,
        NoReboot=True,  # Don't reboot (faster but less consistent)
        TagSpecifications=[
            {
                'ResourceType': 'image',
                'Tags': [
                    {'Key': 'Name', 'Value': name},
                    {'Key': 'CreatedBy', 'Value': 'automation'}
                ]
            }
        ]
    )

    ami_id = response['ImageId']
    print(f"Creating AMI: {ami_id}")

    # Wait for AMI to be available
    waiter = ec2.get_waiter('image_available')
    waiter.wait(ImageIds=[ami_id])

    print(f"AMI ready: {ami_id}")
    return ami_id

def cleanup_old_amis(name_prefix, keep_count=5):
    """Delete old AMIs, keep only recent versions"""

    # List AMIs
    response = ec2.describe_images(
        Owners=['self'],
        Filters=[
            {'Name': 'name', 'Values': [f'{name_prefix}*']},
            {'Name': 'state', 'Values': ['available']}
        ]
    )

    # Sort by creation date
    images = sorted(
        response['Images'],
        key=lambda x: x['CreationDate'],
        reverse=True
    )

    # Delete old images
    for image in images[keep_count:]:
        ami_id = image['ImageId']
        print(f"Deregistering AMI: {ami_id}")

        # Delete snapshots
        for mapping in image.get('BlockDeviceMappings', []):
            if 'Ebs' in mapping:
                snapshot_id = mapping['Ebs']['SnapshotId']
                ec2.delete_snapshot(SnapshotId=snapshot_id)

        # Deregister AMI
        ec2.deregister_image(ImageId=ami_id)
```

---

## Patterns

### Pattern 1: User Data for Instance Initialization

**When to use**: Bootstrap instances on launch

```bash
#!/bin/bash
# User data script - runs on first boot

# Update packages
yum update -y

# Install application dependencies
yum install -y docker git

# Start Docker
systemctl start docker
systemctl enable docker

# Pull and run application
docker pull myregistry/myapp:latest
docker run -d -p 80:8080 --name myapp myregistry/myapp:latest

# Configure CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Signal Auto Scaling that instance is ready
aws autoscaling complete-lifecycle-action \
  --lifecycle-action-result CONTINUE \
  --lifecycle-hook-name my-launch-hook \
  --auto-scaling-group-name my-asg \
  --lifecycle-action-token $TOKEN \
  --region us-east-1
```

```python
import base64

# User data in Python
USER_DATA = """#!/bin/bash
set -e

# Install dependencies
yum update -y
yum install -y python3 pip3

# Clone application
cd /opt
git clone https://github.com/myorg/myapp.git
cd myapp

# Install requirements
pip3 install -r requirements.txt

# Start application
python3 app.py &

# Health check endpoint
echo "Instance ready" > /var/www/html/health
"""

# Launch instance with user data
ec2.run_instances(
    ImageId='ami-0abcdef1234567890',
    InstanceType='t3.medium',
    UserData=base64.b64encode(USER_DATA.encode()).decode(),
    IamInstanceProfile={'Name': 'my-ec2-role'}
)
```

### Pattern 2: Spot Instances for Cost Savings

**Use case**: Non-critical workloads, batch processing, CI/CD

```python
def request_spot_instances():
    """Request spot instances at target price"""

    ec2 = boto3.client('ec2')

    response = ec2.request_spot_instances(
        SpotPrice='0.05',  # Max price per hour
        InstanceCount=5,
        Type='one-time',  # or 'persistent'
        LaunchSpecification={
            'ImageId': 'ami-0abcdef1234567890',
            'InstanceType': 'c5.xlarge',
            'KeyName': 'my-key-pair',
            'SecurityGroupIds': ['sg-0123456789abcdef0'],
            'UserData': base64.b64encode(BATCH_JOB_SCRIPT.encode()).decode(),
            'IamInstanceProfile': {'Name': 'batch-job-role'}
        }
    )

    for request in response['SpotInstanceRequests']:
        print(f"Spot request: {request['SpotInstanceRequestId']}")

# Mix on-demand and spot in Auto Scaling Group
def create_mixed_instance_asg():
    """Create ASG with on-demand and spot instances"""

    autoscaling.create_auto_scaling_group(
        AutoScalingGroupName='mixed-asg',
        MixedInstancesPolicy={
            'LaunchTemplate': {
                'LaunchTemplateSpecification': {
                    'LaunchTemplateName': 'my-template',
                    'Version': '$Latest'
                },
                'Overrides': [
                    {'InstanceType': 't3.medium'},
                    {'InstanceType': 't3.large'},
                    {'InstanceType': 't3a.medium'},  # AMD variant
                ]
            },
            'InstancesDistribution': {
                'OnDemandBaseCapacity': 2,  # Always 2 on-demand
                'OnDemandPercentageAboveBaseCapacity': 20,  # 20% on-demand
                'SpotAllocationStrategy': 'lowest-price',
                'SpotInstancePools': 3
            }
        },
        MinSize=2,
        MaxSize=20,
        VPCZoneIdentifier='subnet-abc123,subnet-def456'
    )
```

### Pattern 3: Instance Metadata Service

**Use case**: Access instance info, credentials, user data

```python
import requests

METADATA_URL = "http://169.254.169.254/latest/meta-data/"
TOKEN_URL = "http://169.254.169.254/latest/api/token"

def get_instance_metadata(path):
    """Fetch instance metadata using IMDSv2 (secure)"""

    # Get session token (IMDSv2 requirement)
    token_response = requests.put(
        TOKEN_URL,
        headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'}
    )
    token = token_response.text

    # Fetch metadata
    response = requests.get(
        f"{METADATA_URL}{path}",
        headers={'X-aws-ec2-metadata-token': token}
    )

    return response.text

# Usage
instance_id = get_instance_metadata('instance-id')
availability_zone = get_instance_metadata('placement/availability-zone')
instance_type = get_instance_metadata('instance-type')
public_ip = get_instance_metadata('public-ipv4')

print(f"Instance {instance_id} ({instance_type}) in {availability_zone}")
print(f"Public IP: {public_ip}")

# Get IAM role credentials
iam_role = get_instance_metadata('iam/security-credentials/')
credentials = get_instance_metadata(f'iam/security-credentials/{iam_role}')
```

---

## Quick Reference

### Instance Type Selection

| Workload | Instance Family | Example | Notes |
|----------|----------------|---------|-------|
| Web servers | T3, T4g | t3.medium | Burstable, cost-effective |
| APIs, microservices | M5, M6i | m5.large | Balanced CPU/memory |
| Batch processing | C5, C6i | c5.2xlarge | Compute-optimized |
| Databases, caching | R5, R6i | r5.xlarge | Memory-optimized |
| Data analytics | I3, I4i | i3.2xlarge | Storage-optimized (NVMe) |

### Load Balancer Selection

```
Use Case                    | ALB | NLB | CLB
----------------------------|-----|-----|-----
HTTP/HTTPS APIs             | ✅  | ❌  | ✅
Path-based routing          | ✅  | ❌  | ❌
WebSocket                   | ✅  | ✅  | ❌
TCP/UDP (non-HTTP)          | ❌  | ✅  | ✅
High throughput (millions)  | ❌  | ✅  | ❌
Static IP required          | ❌  | ✅  | ❌
```

### Key Guidelines

```
✅ DO: Use Auto Scaling for variable load
✅ DO: Deploy across multiple AZs for high availability
✅ DO: Create AMIs for consistent deployments
✅ DO: Use spot instances for non-critical workloads
✅ DO: Tag instances for cost tracking
✅ DO: Use IMDSv2 for instance metadata (secure)

❌ DON'T: Run single instance in production (no HA)
❌ DON'T: Manually patch instances (use AMIs instead)
❌ DON'T: Use CLB for new applications (deprecated)
❌ DON'T: Skip health checks in Auto Scaling Groups
❌ DON'T: Use large instance types without monitoring (cost)
```

---

## Anti-Patterns

### Critical Violations

```bash
# ❌ NEVER: Store credentials in user data
#!/bin/bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG
# Visible in console, metadata, logs

# ✅ CORRECT: Use IAM instance profile
# Attach role to instance, no credentials needed
aws ec2 run-instances \
  --iam-instance-profile Name=my-ec2-role \
  ...
```

❌ **Credentials in user data**: Exposed in EC2 console, metadata service, CloudTrail logs

✅ **Correct approach**: Use IAM roles attached to instances

### Common Mistakes

```python
# ❌ Don't run single instance without Auto Scaling
ec2.run_instances(
    ImageId='ami-123',
    InstanceType='t3.medium',
    MinCount=1,
    MaxCount=1
)
# Instance failure = downtime

# ✅ Correct: Use Auto Scaling Group with min=1
autoscaling.create_auto_scaling_group(
    AutoScalingGroupName='my-app',
    MinSize=1,
    MaxSize=3,
    DesiredCapacity=1,
    HealthCheckType='ELB'
)
# Instance failure = automatic replacement
```

❌ **Single instance without HA**: No recovery from failures

✅ **Better**: Even for small apps, use ASG with min=1 for auto-recovery

---

## Related Skills

- `aws-storage.md` - EBS volumes, snapshots, and instance storage
- `aws-networking.md` - VPC, security groups, and network configuration
- `aws-iam-security.md` - IAM roles and instance profiles
- `aws-lambda-functions.md` - Serverless alternative to EC2
- `infrastructure/aws-serverless.md` - When to use Lambda vs EC2

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
