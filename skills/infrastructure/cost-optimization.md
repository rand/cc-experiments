---
name: infrastructure-cost-optimization
description: Cloud costs are growing unexpectedly
---


# Cost Optimization

**Scope**: Cloud cost optimization - Resource right-sizing, reserved instances, spot instances, monitoring
**Lines**: 394
**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

**Activate when**:
- Cloud costs are growing unexpectedly
- Planning infrastructure budgets
- Optimizing existing workloads
- Implementing cost-aware architectures
- Setting up cost monitoring and alerts
- Choosing between deployment options

**Prerequisites**:
- Access to cloud provider billing console
- Understanding of current infrastructure
- CloudWatch/monitoring access (AWS)
- Billing reports enabled
- Cost allocation tags implemented

**Common scenarios**:
- Monthly cost exceeded budget
- Idle resources consuming budget
- Over-provisioned instances
- Inefficient storage patterns
- Unoptimized database usage
- Poor auto-scaling configuration

---

## Core Concepts

### 1. Resource Right-Sizing

```python
# AWS Lambda optimization
# Problem: Over-provisioned memory

# ❌ Expensive: 3008 MB memory
def lambda_handler(event, context):
    # Function uses ~512 MB
    process_data(event)
    return {'statusCode': 200}

# Memory: 3008 MB
# Cost: ~$0.0000166667 per 100ms
# Actual usage: 512 MB

# ✅ Optimized: Right-sized memory
def lambda_handler(event, context):
    process_data(event)
    return {'statusCode': 200}

# Memory: 512 MB
# Cost: ~$0.0000008333 per 100ms
# Savings: ~95% reduction

# Testing different memory configurations
import json

def test_memory_configs():
    """Test Lambda with different memory configs"""
    configs = [128, 256, 512, 1024, 2048, 3008]
    results = {}

    for memory_mb in configs:
        # Update Lambda configuration
        lambda_client.update_function_configuration(
            FunctionName='my-function',
            MemorySize=memory_mb
        )

        # Run performance test
        execution_time, cost = run_test()
        results[memory_mb] = {
            'execution_time': execution_time,
            'cost': cost,
            'cost_per_invocation': cost / 1000
        }

    return results
```

### 2. EC2 Right-Sizing

```bash
# Analyze CloudWatch metrics for right-sizing
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-31T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum

# If average CPU < 30%, consider smaller instance type
# If max memory < 50%, consider less memory

# Current: t3.xlarge (4 vCPU, 16 GB RAM) - $0.1664/hour
# Average CPU: 20%, Memory: 6 GB
# Recommendation: t3.large (2 vCPU, 8 GB RAM) - $0.0832/hour
# Savings: ~50% reduction
```

### 3. Reserved Instances and Savings Plans

```python
# Calculate savings with Reserved Instances
def calculate_ri_savings(instance_type, hours_per_month=730):
    """
    Calculate potential savings with Reserved Instances

    Pricing examples (us-east-1):
    t3.medium: $0.0416/hour on-demand
    t3.medium: $0.0250/hour 1-year RI (40% savings)
    t3.medium: $0.0166/hour 3-year RI (60% savings)
    """

    on_demand_cost = {
        't3.micro': 0.0104,
        't3.small': 0.0208,
        't3.medium': 0.0416,
        't3.large': 0.0832,
        't3.xlarge': 0.1664,
    }

    # 1-year Reserved Instance (40% discount)
    ri_1yr_cost = on_demand_cost[instance_type] * 0.6

    # 3-year Reserved Instance (60% discount)
    ri_3yr_cost = on_demand_cost[instance_type] * 0.4

    monthly_on_demand = on_demand_cost[instance_type] * hours_per_month
    monthly_ri_1yr = ri_1yr_cost * hours_per_month
    monthly_ri_3yr = ri_3yr_cost * hours_per_month

    return {
        'on_demand': monthly_on_demand,
        'ri_1yr': monthly_ri_1yr,
        'ri_3yr': monthly_ri_3yr,
        'savings_1yr': monthly_on_demand - monthly_ri_1yr,
        'savings_3yr': monthly_on_demand - monthly_ri_3yr,
        'savings_1yr_percent': ((monthly_on_demand - monthly_ri_1yr) / monthly_on_demand) * 100,
        'savings_3yr_percent': ((monthly_on_demand - monthly_ri_3yr) / monthly_on_demand) * 100,
    }

# Example: 5 x t3.large instances running 24/7
savings = calculate_ri_savings('t3.large', 730)
print(f"Monthly cost - On-Demand: ${savings['on_demand']:.2f}")
print(f"Monthly cost - 1-year RI: ${savings['ri_1yr']:.2f}")
print(f"Monthly savings with RI: ${savings['savings_1yr']:.2f} ({savings['savings_1yr_percent']:.1f}%)")
```

### 4. Spot Instances

```python
# Use Spot Instances for fault-tolerant workloads
import boto3

ec2 = boto3.client('ec2')

# Request Spot Instances
response = ec2.request_spot_instances(
    InstanceCount=5,
    LaunchSpecification={
        'ImageId': 'ami-0c55b159cbfafe1f0',
        'InstanceType': 't3.medium',
        'KeyName': 'my-key',
        'SecurityGroupIds': ['sg-12345678'],
        'IamInstanceProfile': {
            'Arn': 'arn:aws:iam::123456789012:instance-profile/worker-role'
        },
        'UserData': base64.b64encode(user_data.encode()).decode()
    },
    SpotPrice='0.0200',  # Max price (70% of on-demand)
    Type='one-time'
)

# Spot Instances savings:
# t3.medium on-demand: $0.0416/hour
# t3.medium spot (average): ~$0.0125/hour
# Savings: ~70%

# Use Cases:
# - Batch processing
# - CI/CD workers
# - Data analysis
# - Machine learning training
# - Stateless web workers

# NOT suitable for:
# - Databases
# - Long-running stateful services
# - Time-critical applications
```

### 5. Auto-Scaling Optimization

```python
# Auto Scaling policy for cost optimization
import boto3

autoscaling = boto3.client('autoscaling')

# Target tracking scaling policy
response = autoscaling.put_scaling_policy(
    AutoScalingGroupName='web-asg',
    PolicyName='target-tracking-cpu',
    PolicyType='TargetTrackingScaling',
    TargetTrackingConfiguration={
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'ASGAverageCPUUtilization'
        },
        'TargetValue': 70.0,  # Target 70% CPU utilization
        'ScaleInCooldown': 300,  # Wait 5 min before scaling down
        'ScaleOutCooldown': 60   # Wait 1 min before scaling up
    }
)

# Scheduled scaling for predictable patterns
autoscaling.put_scheduled_action(
    AutoScalingGroupName='web-asg',
    ScheduledActionName='scale-down-evening',
    Recurrence='0 18 * * *',  # 6 PM UTC
    MinSize=2,
    MaxSize=5,
    DesiredCapacity=2
)

autoscaling.put_scheduled_action(
    AutoScalingGroupName='web-asg',
    ScheduledActionName='scale-up-morning',
    Recurrence='0 6 * * *',  # 6 AM UTC
    MinSize=5,
    MaxSize=20,
    DesiredCapacity=10
)
```

### 6. Storage Optimization

```python
# S3 Lifecycle policies for cost optimization
import boto3

s3 = boto3.client('s3')

lifecycle_config = {
    'Rules': [
        {
            'Id': 'archive-old-logs',
            'Status': 'Enabled',
            'Prefix': 'logs/',
            'Transitions': [
                {
                    'Days': 30,
                    'StorageClass': 'STANDARD_IA'  # Infrequent Access
                },
                {
                    'Days': 90,
                    'StorageClass': 'GLACIER_IR'  # Glacier Instant Retrieval
                },
                {
                    'Days': 365,
                    'StorageClass': 'DEEP_ARCHIVE'  # Deep Archive
                }
            ],
            'Expiration': {
                'Days': 2555  # Delete after 7 years
            }
        },
        {
            'Id': 'delete-temp-files',
            'Status': 'Enabled',
            'Prefix': 'temp/',
            'Expiration': {
                'Days': 7
            }
        },
        {
            'Id': 'abort-incomplete-multipart',
            'Status': 'Enabled',
            'Prefix': '',
            'AbortIncompleteMultipartUpload': {
                'DaysAfterInitiation': 7
            }
        }
    ]
}

s3.put_bucket_lifecycle_configuration(
    Bucket='my-bucket',
    LifecycleConfiguration=lifecycle_config
)

# S3 Storage Costs (per GB/month):
# Standard: $0.023
# Standard-IA: $0.0125 (45% savings)
# Glacier Instant Retrieval: $0.004 (83% savings)
# Glacier Flexible Retrieval: $0.0036 (84% savings)
# Glacier Deep Archive: $0.00099 (96% savings)
```

### 7. Database Cost Optimization

```python
# RDS optimization strategies

# 1. Right-size instance
# Current: db.r5.2xlarge (8 vCPU, 64 GB) - $1.344/hour
# If CPU < 30% and memory < 40GB
# Recommended: db.r5.xlarge (4 vCPU, 32 GB) - $0.672/hour
# Savings: 50%

# 2. Use Aurora Serverless v2 for variable workloads
import boto3

rds = boto3.client('rds')

# Aurora Serverless v2
response = rds.create_db_cluster(
    DBClusterIdentifier='my-cluster',
    Engine='aurora-postgresql',
    EngineVersion='14.6',
    ServerlessV2ScalingConfiguration={
        'MinCapacity': 0.5,  # Min ACUs (Aurora Capacity Units)
        'MaxCapacity': 16.0   # Max ACUs
    }
)

# Savings example:
# Traditional RDS: db.r5.large 24/7 = $0.336/hour * 730 = $245/month
# Aurora Serverless v2: Average 2 ACU * $0.12/ACU/hour * 730 = $175/month
# Savings: ~29%

# 3. Schedule stop/start for dev/test databases
def schedule_database_stop_start():
    """Stop dev databases outside business hours"""

    # Stop at 6 PM
    lambda_client.create_rule(
        Name='stop-dev-databases',
        ScheduleExpression='cron(0 18 * * ? *)',
        State='ENABLED',
        Targets=[{
            'Arn': 'arn:aws:lambda:us-east-1:123456789012:function:stop-databases',
            'Id': 'stop-dev-dbs'
        }]
    )

    # Start at 8 AM
    lambda_client.create_rule(
        Name='start-dev-databases',
        ScheduleExpression='cron(0 8 * * ? *)',
        State='ENABLED',
        Targets=[{
            'Arn': 'arn:aws:lambda:us-east-1:123456789012:function:start-databases',
            'Id': 'start-dev-dbs'
        }]
    )

    # Savings: 14 hours/day * 5 days/week = ~40% reduction
```

---

## Patterns

### Cost Monitoring with CloudWatch

```python
# Set up billing alerts
import boto3

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')  # Must be us-east-1
sns = boto3.client('sns')

# Create SNS topic for alerts
topic_response = sns.create_topic(Name='billing-alerts')
topic_arn = topic_response['TopicArn']

# Subscribe email
sns.subscribe(
    TopicArn=topic_arn,
    Protocol='email',
    Endpoint='ops@example.com'
)

# Create billing alarm
cloudwatch.put_metric_alarm(
    AlarmName='MonthlyBillingExceeds1000',
    AlarmDescription='Alert when monthly bill exceeds $1000',
    ActionsEnabled=True,
    AlarmActions=[topic_arn],
    MetricName='EstimatedCharges',
    Namespace='AWS/Billing',
    Statistic='Maximum',
    Dimensions=[
        {
            'Name': 'Currency',
            'Value': 'USD'
        }
    ],
    Period=21600,  # 6 hours
    EvaluationPeriods=1,
    Threshold=1000.0,
    ComparisonOperator='GreaterThanThreshold'
)
```

### Cost Allocation Tags

```python
# Implement comprehensive tagging strategy
import boto3

def tag_resources():
    """Apply cost allocation tags to all resources"""

    ec2 = boto3.client('ec2')

    # Tag EC2 instances
    ec2.create_tags(
        Resources=['i-1234567890abcdef0'],
        Tags=[
            {'Key': 'Environment', 'Value': 'production'},
            {'Key': 'Project', 'Value': 'web-app'},
            {'Key': 'Team', 'Value': 'platform'},
            {'Key': 'CostCenter', 'Value': '12345'},
            {'Key': 'Owner', 'Value': 'engineering@example.com'}
        ]
    )

    # Enable cost allocation tags in AWS Billing Console
    # This allows filtering and grouping costs by tag

# Cost allocation reports by tag
def generate_cost_report_by_tag(tag_key='Project'):
    """Generate cost report grouped by tag"""

    ce = boto3.client('ce')  # Cost Explorer

    response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': '2024-01-01',
            'End': '2024-01-31'
        },
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        GroupBy=[
            {
                'Type': 'TAG',
                'Key': tag_key
            }
        ]
    )

    return response['ResultsByTime']
```

### Lambda Cost Optimization

```python
# Optimize Lambda for cost
def optimize_lambda_cost():
    """Best practices for Lambda cost optimization"""

    # 1. Right-size memory (affects CPU allocation)
    # Test different configurations to find optimal

    # 2. Reduce package size
    # - Use Lambda Layers for shared dependencies
    # - Remove unused dependencies
    # - Use tree-shaking for Node.js

    # 3. Minimize cold starts
    # - Keep functions warm with scheduled invocations (if cost-effective)
    # - Use provisioned concurrency for critical functions

    # 4. Connection reuse
    # Initialize clients outside handler
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('users')

    def lambda_handler(event, context):
        # Connection is reused across warm invocations
        table.put_item(Item={'id': '123', 'name': 'Alice'})

    # 5. Batch operations
    # Process multiple records per invocation
    # Reduces number of invocations

    # 6. Use appropriate timeout
    # Don't set timeout higher than needed
    # Default: 3 seconds (adjust based on actual needs)

# Lambda pricing:
# $0.20 per 1M requests
# $0.0000166667 per GB-second

# Example savings:
# 10M requests/month at 128 MB, 200ms avg
# Current cost: 10M * $0.20/1M + 10M * 0.2s * 0.125GB * $0.0000166667/GB-s = $2 + $4.17 = $6.17
# With optimization (100ms): $2 + $2.08 = $4.08
# Savings: ~34%
```

### Multi-Region Cost Optimization

```python
# Choose cost-effective regions
REGIONAL_PRICING = {
    'us-east-1': {  # N. Virginia (cheapest)
        'ec2_t3_medium': 0.0416,
        'lambda_gb_second': 0.0000166667,
        's3_standard': 0.023
    },
    'us-west-2': {  # Oregon
        'ec2_t3_medium': 0.0416,
        'lambda_gb_second': 0.0000166667,
        's3_standard': 0.023
    },
    'eu-west-1': {  # Ireland
        'ec2_t3_medium': 0.0456,  # ~10% more expensive
        'lambda_gb_second': 0.0000166667,
        's3_standard': 0.023
    },
    'ap-southeast-1': {  # Singapore
        'ec2_t3_medium': 0.0528,  # ~27% more expensive
        'lambda_gb_second': 0.0000185185,
        's3_standard': 0.025
    }
}

def calculate_regional_savings(instances_count, region_from, region_to):
    """Calculate savings by switching regions"""

    current_cost = REGIONAL_PRICING[region_from]['ec2_t3_medium'] * 730 * instances_count
    new_cost = REGIONAL_PRICING[region_to]['ec2_t3_medium'] * 730 * instances_count

    savings = current_cost - new_cost
    savings_percent = (savings / current_cost) * 100

    return {
        'current_monthly_cost': current_cost,
        'new_monthly_cost': new_cost,
        'monthly_savings': savings,
        'savings_percent': savings_percent
    }

# Example: Moving 10 t3.medium instances from Singapore to N. Virginia
savings = calculate_regional_savings(10, 'ap-southeast-1', 'us-east-1')
print(f"Monthly savings: ${savings['monthly_savings']:.2f} ({savings['savings_percent']:.1f}%)")
```

### Idle Resource Detection

```python
# Identify and terminate idle resources
import boto3
from datetime import datetime, timedelta

def find_idle_resources():
    """Identify idle resources consuming costs"""

    ec2 = boto3.client('ec2')
    cloudwatch = boto3.client('cloudwatch')

    # Find EC2 instances with low CPU usage
    instances = ec2.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )

    idle_instances = []
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)

    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']

            # Get average CPU over last 7 days
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,  # 1 day
                Statistics=['Average']
            )

            if response['Datapoints']:
                avg_cpu = sum(d['Average'] for d in response['Datapoints']) / len(response['Datapoints'])

                if avg_cpu < 5:  # Less than 5% CPU
                    idle_instances.append({
                        'instance_id': instance_id,
                        'avg_cpu': avg_cpu,
                        'instance_type': instance['InstanceType'],
                        'tags': {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                    })

    return idle_instances

# Find unused EBS volumes
def find_unattached_volumes():
    """Find EBS volumes not attached to instances"""

    ec2 = boto3.client('ec2')

    volumes = ec2.describe_volumes(
        Filters=[{'Name': 'status', 'Values': ['available']}]
    )

    unattached = []
    for volume in volumes['Volumes']:
        unattached.append({
            'volume_id': volume['VolumeId'],
            'size': volume['Size'],
            'type': volume['VolumeType'],
            'monthly_cost': volume['Size'] * 0.10  # ~$0.10/GB/month for gp3
        })

    return unattached
```

---

## Quick Reference

### AWS Cost Optimization Checklist

```
[ ] Right-size EC2 instances based on CloudWatch metrics
[ ] Purchase Reserved Instances for steady-state workloads
[ ] Use Spot Instances for fault-tolerant workloads
[ ] Implement S3 lifecycle policies
[ ] Delete unattached EBS volumes
[ ] Delete old snapshots
[ ] Use S3 Intelligent-Tiering for unpredictable access patterns
[ ] Enable S3 Transfer Acceleration only when needed
[ ] Use CloudFront for content delivery
[ ] Optimize Lambda memory allocation
[ ] Use DynamoDB On-Demand for unpredictable workloads
[ ] Schedule stop/start for dev/test resources
[ ] Set up billing alerts
[ ] Implement cost allocation tags
[ ] Review and delete unused resources monthly
[ ] Use AWS Cost Explorer for analysis
[ ] Enable AWS Compute Optimizer recommendations
```

### Quick Cost Comparison

```
Compute:
- Lambda: $0.20/1M requests + $0.0000166667/GB-second
- Fargate: $0.04048/vCPU/hour + $0.004445/GB/hour
- EC2 t3.medium: $0.0416/hour (on-demand), $0.025/hour (RI)
- EC2 Spot: ~70% discount from on-demand

Storage:
- S3 Standard: $0.023/GB/month
- S3 Intelligent-Tiering: $0.023/GB + $0.0025/1000 objects
- S3 Glacier: $0.004/GB/month
- EBS gp3: $0.08/GB/month

Database:
- RDS db.t3.medium: $0.068/hour
- Aurora Serverless v2: $0.12/ACU/hour
- DynamoDB: On-Demand $1.25/million writes, $0.25/million reads
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Leave resources running 24/7 in dev/test
# Cost: t3.medium * 730 hours = $30.37/month
# If only used 8 hours/day, 5 days/week = ~$9/month
# Waste: ~$21/month per instance

# ✅ CORRECT: Schedule stop/start
def lambda_handler(event, context):
    ec2 = boto3.client('ec2')

    if event['action'] == 'stop':
        ec2.stop_instances(InstanceIds=event['instance_ids'])
    elif event['action'] == 'start':
        ec2.start_instances(InstanceIds=event['instance_ids'])
```

```python
# ❌ NEVER: Store everything in S3 Standard
# If 1 TB of logs accessed once per month
# S3 Standard: $23/month
# S3 Glacier: $4/month + retrieval costs
# Waste: ~$19/month

# ✅ CORRECT: Use lifecycle policies
# See Storage Optimization section above
```

```python
# ❌ NEVER: Over-provision Lambda memory
# 3008 MB when function uses 512 MB
# Waste: ~95% of memory cost

# ✅ CORRECT: Use AWS Lambda Power Tuning
# https://github.com/alexcasalboni/aws-lambda-power-tuning
```

---

## Related Skills

**Infrastructure**:
- `aws-serverless.md` - Lambda, DynamoDB cost optimization
- `terraform-patterns.md` - Infrastructure as Code for cost tracking
- `kubernetes-basics.md` - Resource requests/limits for cost control
- `cloudflare-workers.md` - Low-cost edge computing alternative

**Monitoring**:
- CloudWatch for metrics and billing alerts
- AWS Cost Explorer for detailed analysis
- AWS Budgets for spending limits

**Standards from CLAUDE.md**:
- Always define resource limits
- Use cost allocation tags
- Monitor costs proactively
- Right-size before deploying
- Use serverless when appropriate
- Schedule dev/test resources

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
