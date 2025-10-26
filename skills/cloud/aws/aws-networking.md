---
name: cloud-aws-networking
description: AWS networking - VPC, subnets, security groups, NACLs, Route53, CloudFront, Transit Gateway
---

# AWS Networking

**Scope**: AWS networking - VPC, subnets, route tables, security groups, NACLs, Route53, CloudFront, VPN, Direct Connect
**Lines**: ~320
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Creating VPCs and subnet architecture
- Configuring security groups and network ACLs
- Setting up DNS with Route53 routing policies
- Implementing CDN with CloudFront
- Connecting multiple VPCs with Transit Gateway
- Setting up VPN or Direct Connect to on-premises
- Troubleshooting network connectivity issues
- Implementing network segmentation and isolation

## Core Concepts

### Concept 1: VPC Architecture

**VPC components**:
- **Subnets**: Public (internet access) vs Private (no direct internet)
- **Route tables**: Direct traffic between subnets and gateways
- **Internet Gateway**: Public subnet internet access
- **NAT Gateway**: Private subnet outbound internet access

```python
import boto3

ec2 = boto3.client('ec2')

def create_vpc_architecture():
    """Create VPC with public and private subnets"""

    # Create VPC
    vpc_response = ec2.create_vpc(
        CidrBlock='10.0.0.0/16',
        TagSpecifications=[
            {
                'ResourceType': 'vpc',
                'Tags': [
                    {'Key': 'Name', 'Value': 'myapp-vpc'},
                    {'Key': 'Environment', 'Value': 'production'}
                ]
            }
        ]
    )

    vpc_id = vpc_response['Vpc']['VpcId']

    # Enable DNS hostnames
    ec2.modify_vpc_attribute(
        VpcId=vpc_id,
        EnableDnsHostnames={'Value': True}
    )

    # Create Internet Gateway
    igw_response = ec2.create_internet_gateway(
        TagSpecifications=[
            {
                'ResourceType': 'internet-gateway',
                'Tags': [{'Key': 'Name', 'Value': 'myapp-igw'}]
            }
        ]
    )

    igw_id = igw_response['InternetGateway']['InternetGatewayId']

    # Attach Internet Gateway to VPC
    ec2.attach_internet_gateway(
        InternetGatewayId=igw_id,
        VpcId=vpc_id
    )

    # Create public subnets (one per AZ)
    public_subnet_1 = ec2.create_subnet(
        VpcId=vpc_id,
        CidrBlock='10.0.1.0/24',
        AvailabilityZone='us-east-1a',
        TagSpecifications=[
            {
                'ResourceType': 'subnet',
                'Tags': [{'Key': 'Name', 'Value': 'public-subnet-1a'}]
            }
        ]
    )['Subnet']['SubnetId']

    public_subnet_2 = ec2.create_subnet(
        VpcId=vpc_id,
        CidrBlock='10.0.2.0/24',
        AvailabilityZone='us-east-1b',
        TagSpecifications=[
            {
                'ResourceType': 'subnet',
                'Tags': [{'Key': 'Name', 'Value': 'public-subnet-1b'}]
            }
        ]
    )['Subnet']['SubnetId']

    # Create private subnets
    private_subnet_1 = ec2.create_subnet(
        VpcId=vpc_id,
        CidrBlock='10.0.11.0/24',
        AvailabilityZone='us-east-1a',
        TagSpecifications=[
            {
                'ResourceType': 'subnet',
                'Tags': [{'Key': 'Name', 'Value': 'private-subnet-1a'}]
            }
        ]
    )['Subnet']['SubnetId']

    private_subnet_2 = ec2.create_subnet(
        VpcId=vpc_id,
        CidrBlock='10.0.12.0/24',
        AvailabilityZone='us-east-1b',
        TagSpecifications=[
            {
                'ResourceType': 'subnet',
                'Tags': [{'Key': 'Name', 'Value': 'private-subnet-1b'}]
            }
        ]
    )['Subnet']['SubnetId']

    # Create NAT Gateway in public subnet
    eip_response = ec2.allocate_address(Domain='vpc')
    eip_id = eip_response['AllocationId']

    nat_response = ec2.create_nat_gateway(
        SubnetId=public_subnet_1,
        AllocationId=eip_id,
        TagSpecifications=[
            {
                'ResourceType': 'nat-gateway',
                'Tags': [{'Key': 'Name', 'Value': 'myapp-nat'}]
            }
        ]
    )

    nat_id = nat_response['NatGateway']['NatGatewayId']

    # Wait for NAT Gateway to be available
    waiter = ec2.get_waiter('nat_gateway_available')
    waiter.wait(NatGatewayIds=[nat_id])

    # Create route tables
    public_rt = ec2.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'route-table',
                'Tags': [{'Key': 'Name', 'Value': 'public-rt'}]
            }
        ]
    )['RouteTable']['RouteTableId']

    private_rt = ec2.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'route-table',
                'Tags': [{'Key': 'Name', 'Value': 'private-rt'}]
            }
        ]
    )['RouteTable']['RouteTableId']

    # Add routes
    ec2.create_route(
        RouteTableId=public_rt,
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=igw_id
    )

    ec2.create_route(
        RouteTableId=private_rt,
        DestinationCidrBlock='0.0.0.0/0',
        NatGatewayId=nat_id
    )

    # Associate route tables with subnets
    ec2.associate_route_table(RouteTableId=public_rt, SubnetId=public_subnet_1)
    ec2.associate_route_table(RouteTableId=public_rt, SubnetId=public_subnet_2)
    ec2.associate_route_table(RouteTableId=private_rt, SubnetId=private_subnet_1)
    ec2.associate_route_table(RouteTableId=private_rt, SubnetId=private_subnet_2)

    print(f"Created VPC architecture: {vpc_id}")

    return {
        'vpc_id': vpc_id,
        'public_subnets': [public_subnet_1, public_subnet_2],
        'private_subnets': [private_subnet_1, private_subnet_2]
    }
```

### Concept 2: Security Groups vs Network ACLs

**Security Groups** (stateful):
- Instance-level firewall
- Allow rules only (implicit deny)
- Stateful (return traffic automatic)

**Network ACLs** (stateless):
- Subnet-level firewall
- Allow and deny rules
- Stateless (must configure both directions)

```python
def create_security_groups(vpc_id):
    """Create security groups for web tier and database tier"""

    # Web tier security group
    web_sg = ec2.create_security_group(
        GroupName='web-tier-sg',
        Description='Security group for web servers',
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'security-group',
                'Tags': [{'Key': 'Name', 'Value': 'web-tier-sg'}]
            }
        ]
    )['GroupId']

    # Allow HTTP from anywhere
    ec2.authorize_security_group_ingress(
        GroupId=web_sg,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP from anywhere'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 443,
                'ToPort': 443,
                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTPS from anywhere'}]
            }
        ]
    )

    # Database tier security group
    db_sg = ec2.create_security_group(
        GroupName='database-tier-sg',
        Description='Security group for databases',
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'security-group',
                'Tags': [{'Key': 'Name', 'Value': 'database-tier-sg'}]
            }
        ]
    )['GroupId']

    # Allow PostgreSQL only from web tier
    ec2.authorize_security_group_ingress(
        GroupId=db_sg,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 5432,
                'ToPort': 5432,
                'UserIdGroupPairs': [
                    {
                        'GroupId': web_sg,
                        'Description': 'PostgreSQL from web tier'
                    }
                ]
            }
        ]
    )

    return {'web_sg': web_sg, 'db_sg': db_sg}
```

### Concept 3: Route53 DNS

**Routing policies**:
- **Simple**: Single resource
- **Weighted**: Traffic distribution (A/B testing)
- **Latency**: Route to lowest latency region
- **Failover**: Active-passive failover
- **Geolocation**: Route based on user location

```python
import boto3

route53 = boto3.client('route53')

def create_weighted_routing():
    """Create weighted routing for A/B testing"""

    hosted_zone_id = 'Z1234567890ABC'

    # Version A (80% traffic)
    route53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': 'api.example.com',
                        'Type': 'A',
                        'SetIdentifier': 'version-a',
                        'Weight': 80,
                        'TTL': 60,
                        'ResourceRecords': [{'Value': '192.0.2.1'}]
                    }
                }
            ]
        }
    )

    # Version B (20% traffic)
    route53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': 'api.example.com',
                        'Type': 'A',
                        'SetIdentifier': 'version-b',
                        'Weight': 20,
                        'TTL': 60,
                        'ResourceRecords': [{'Value': '192.0.2.2'}]
                    }
                }
            ]
        }
    )

def create_failover_routing():
    """Create active-passive failover"""

    hosted_zone_id = 'Z1234567890ABC'

    # Primary
    route53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': 'www.example.com',
                        'Type': 'A',
                        'SetIdentifier': 'primary',
                        'Failover': 'PRIMARY',
                        'TTL': 60,
                        'ResourceRecords': [{'Value': '192.0.2.1'}],
                        'HealthCheckId': 'health-check-id-1'
                    }
                }
            ]
        }
    )

    # Secondary
    route53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': 'www.example.com',
                        'Type': 'A',
                        'SetIdentifier': 'secondary',
                        'Failover': 'SECONDARY',
                        'TTL': 60,
                        'ResourceRecords': [{'Value': '192.0.2.2'}]
                    }
                }
            ]
        }
    )
```

---

## Patterns

### Pattern 1: CloudFront CDN

**When to use**: Global content delivery, edge caching

```python
import boto3

cloudfront = boto3.client('cloudfront')

def create_cloudfront_distribution(origin_domain, certificate_arn):
    """Create CloudFront distribution for S3 or ALB origin"""

    response = cloudfront.create_distribution(
        DistributionConfig={
            'CallerReference': str(datetime.utcnow().timestamp()),
            'Comment': 'My app CDN',
            'Enabled': True,
            'Origins': {
                'Quantity': 1,
                'Items': [
                    {
                        'Id': 'my-origin',
                        'DomainName': origin_domain,
                        'CustomOriginConfig': {
                            'HTTPPort': 80,
                            'HTTPSPort': 443,
                            'OriginProtocolPolicy': 'https-only',
                            'OriginSslProtocols': {
                                'Quantity': 1,
                                'Items': ['TLSv1.2']
                            }
                        }
                    }
                ]
            },
            'DefaultCacheBehavior': {
                'TargetOriginId': 'my-origin',
                'ViewerProtocolPolicy': 'redirect-to-https',
                'AllowedMethods': {
                    'Quantity': 7,
                    'Items': ['GET', 'HEAD', 'OPTIONS', 'PUT', 'POST', 'PATCH', 'DELETE'],
                    'CachedMethods': {
                        'Quantity': 2,
                        'Items': ['GET', 'HEAD']
                    }
                },
                'ForwardedValues': {
                    'QueryString': True,
                    'Cookies': {'Forward': 'all'},
                    'Headers': {
                        'Quantity': 1,
                        'Items': ['Authorization']
                    }
                },
                'MinTTL': 0,
                'DefaultTTL': 86400,  # 1 day
                'MaxTTL': 31536000,  # 1 year
                'Compress': True
            },
            'Aliases': {
                'Quantity': 1,
                'Items': ['cdn.example.com']
            },
            'ViewerCertificate': {
                'ACMCertificateArn': certificate_arn,
                'SSLSupportMethod': 'sni-only',
                'MinimumProtocolVersion': 'TLSv1.2_2021'
            },
            'PriceClass': 'PriceClass_100'  # US, Canada, Europe
        }
    )

    distribution_id = response['Distribution']['Id']
    domain_name = response['Distribution']['DomainName']

    print(f"Created CloudFront distribution: {domain_name}")

    return distribution_id
```

### Pattern 2: VPC Endpoints

**Use case**: Private access to AWS services without internet gateway

```python
def create_vpc_endpoints(vpc_id, route_table_ids, subnet_ids):
    """Create VPC endpoints for S3 and DynamoDB"""

    # Gateway endpoint for S3 (free)
    s3_endpoint = ec2.create_vpc_endpoint(
        VpcId=vpc_id,
        ServiceName='com.amazonaws.us-east-1.s3',
        RouteTableIds=route_table_ids,
        VpcEndpointType='Gateway',
        TagSpecifications=[
            {
                'ResourceType': 'vpc-endpoint',
                'Tags': [{'Key': 'Name', 'Value': 's3-endpoint'}]
            }
        ]
    )

    # Interface endpoint for Secrets Manager (hourly charge)
    secrets_endpoint = ec2.create_vpc_endpoint(
        VpcId=vpc_id,
        ServiceName='com.amazonaws.us-east-1.secretsmanager',
        VpcEndpointType='Interface',
        SubnetIds=subnet_ids,
        SecurityGroupIds=['sg-0123456789abcdef0'],
        PrivateDnsEnabled=True,
        TagSpecifications=[
            {
                'ResourceType': 'vpc-endpoint',
                'Tags': [{'Key': 'Name', 'Value': 'secrets-endpoint'}]
            }
        ]
    )

    print("Created VPC endpoints for S3 and Secrets Manager")
```

### Pattern 3: Transit Gateway for Multi-VPC

**Use case**: Connect multiple VPCs, on-premises networks

```python
def create_transit_gateway():
    """Create Transit Gateway and attach VPCs"""

    ec2 = boto3.client('ec2')

    # Create Transit Gateway
    tgw_response = ec2.create_transit_gateway(
        Description='Multi-VPC connectivity',
        Options={
            'AmazonSideAsn': 64512,
            'DefaultRouteTableAssociation': 'enable',
            'DefaultRouteTablePropagation': 'enable',
            'DnsSupport': 'enable',
            'VpnEcmpSupport': 'enable'
        },
        TagSpecifications=[
            {
                'ResourceType': 'transit-gateway',
                'Tags': [{'Key': 'Name', 'Value': 'myapp-tgw'}]
            }
        ]
    )

    tgw_id = tgw_response['TransitGateway']['TransitGatewayId']

    # Wait for Transit Gateway to be available
    waiter = ec2.get_waiter('transit_gateway_available')
    waiter.wait(TransitGatewayIds=[tgw_id])

    # Attach VPCs
    vpc_ids = ['vpc-111', 'vpc-222', 'vpc-333']

    for vpc_id in vpc_ids:
        # Get subnet IDs for VPC
        subnets = ec2.describe_subnets(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )['Subnets']

        subnet_ids = [s['SubnetId'] for s in subnets[:2]]  # One per AZ

        # Create attachment
        ec2.create_transit_gateway_vpc_attachment(
            TransitGatewayId=tgw_id,
            VpcId=vpc_id,
            SubnetIds=subnet_ids,
            TagSpecifications=[
                {
                    'ResourceType': 'transit-gateway-attachment',
                    'Tags': [{'Key': 'Name', 'Value': f'{vpc_id}-attachment'}]
                }
            ]
        )

    print(f"Created Transit Gateway: {tgw_id}")

    return tgw_id
```

---

## Quick Reference

### CIDR Block Sizing

```
Subnet Size  | CIDR       | Usable IPs | Use Case
-------------|------------|------------|------------------
/28          | x.x.x.0/28 | 11         | Small (Lambda VPC)
/24          | x.x.x.0/24 | 251        | Standard subnet
/20          | x.x.0.0/20 | 4,091      | Large subnet
/16          | x.x.0.0/16 | 65,531     | VPC
```

### Security Group vs NACL

```
Feature              | Security Group  | Network ACL
---------------------|-----------------|------------------
Level                | Instance        | Subnet
State                | Stateful        | Stateless
Rules                | Allow only      | Allow and Deny
Rule evaluation      | All rules       | Ordered (lowest #)
Default              | Deny all        | Allow all
```

### Route53 Routing Policies

```
Policy       | Use Case                      | Example
-------------|-------------------------------|------------------
Simple       | Single resource               | One web server
Weighted     | A/B testing, gradual rollout  | 80% old, 20% new
Latency      | Global users, lowest latency  | US-East vs EU-West
Failover     | Active-passive HA             | Primary + backup
Geolocation  | Region-specific content       | EU users → EU server
```

### Key Guidelines

```
✅ DO: Use multiple Availability Zones for high availability
✅ DO: Separate public and private subnets
✅ DO: Use security groups for instance-level firewall
✅ DO: Use VPC endpoints for AWS service access (cost, security)
✅ DO: Enable VPC flow logs for troubleshooting
✅ DO: Use CloudFront for global content delivery

❌ DON'T: Use 0.0.0.0/0 in security groups unless necessary
❌ DON'T: Expose databases publicly (use private subnets)
❌ DON'T: Hardcode IP addresses (use DNS)
❌ DON'T: Use default VPC for production
❌ DON'T: Forget to configure return traffic in NACLs (stateless)
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Expose database to internet
ec2.authorize_security_group_ingress(
    GroupId=db_sg,
    IpPermissions=[
        {
            'IpProtocol': 'tcp',
            'FromPort': 5432,
            'ToPort': 5432,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]  # NEVER!
        }
    ]
)

# ✅ CORRECT: Allow only from application tier
ec2.authorize_security_group_ingress(
    GroupId=db_sg,
    IpPermissions=[
        {
            'IpProtocol': 'tcp',
            'FromPort': 5432,
            'ToPort': 5432,
            'UserIdGroupPairs': [{'GroupId': app_sg}]
        }
    ]
)
```

❌ **Public database**: Security vulnerability, data breach risk

✅ **Correct approach**: Private subnets, security group from app tier only

### Common Mistakes

```bash
# ❌ Don't use default VPC for production
# Default VPC has public subnets, less isolation

# ✅ Correct: Create custom VPC with proper subnet architecture
aws ec2 create-vpc --cidr-block 10.0.0.0/16
# Design public/private subnets, NAT gateways, etc.
```

❌ **Default VPC**: Less control, public subnets, harder to secure

✅ **Better**: Custom VPC with planned architecture, network segmentation

---

## Related Skills

- `aws-ec2-compute.md` - Launch instances in VPC subnets
- `aws-databases.md` - RDS in private subnets
- `aws-iam-security.md` - Security groups and IAM for networking
- `aws-lambda-functions.md` - Lambda VPC configuration

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
