# Terraform Best Practices - Comprehensive Reference

## Table of Contents
1. [Terraform Fundamentals](#terraform-fundamentals)
2. [State Management](#state-management)
3. [Module Design Patterns](#module-design-patterns)
4. [Variable Management](#variable-management)
5. [Resource Naming Conventions](#resource-naming-conventions)
6. [Code Organization](#code-organization)
7. [DRY Principles](#dry-principles)
8. [Testing Strategies](#testing-strategies)
9. [CI/CD Integration](#cicd-integration)
10. [Security Best Practices](#security-best-practices)
11. [Cost Optimization](#cost-optimization)
12. [Common Anti-Patterns](#common-anti-patterns)
13. [Multi-Environment Strategies](#multi-environment-strategies)
14. [Performance Optimization](#performance-optimization)
15. [Disaster Recovery](#disaster-recovery)

---

## Terraform Fundamentals

### Core Concepts

#### Infrastructure as Code (IaC)
Terraform enables declarative infrastructure management through code:

```hcl
# Declarative approach - describe desired state
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  tags = {
    Name        = "web-server"
    Environment = "production"
  }
}
```

**Key Principles:**
- Idempotency: Running the same configuration multiple times produces the same result
- Declarative: Define what you want, not how to create it
- Version Control: Infrastructure changes tracked like code
- Reproducibility: Same configuration creates identical infrastructure

#### Terraform Workflow

**1. Write Phase:**
```bash
# Create configuration files
touch main.tf variables.tf outputs.tf
```

**2. Initialize Phase:**
```bash
# Download providers and modules
terraform init

# Upgrade providers
terraform init -upgrade

# Reconfigure backend
terraform init -reconfigure
```

**3. Plan Phase:**
```bash
# Preview changes
terraform plan

# Save plan to file
terraform plan -out=tfplan

# Plan specific target
terraform plan -target=aws_instance.web
```

**4. Apply Phase:**
```bash
# Apply changes
terraform apply

# Apply saved plan
terraform apply tfplan

# Auto-approve (CI/CD)
terraform apply -auto-approve

# Apply with parallelism control
terraform apply -parallelism=10
```

**5. Destroy Phase:**
```bash
# Destroy all resources
terraform destroy

# Destroy specific resource
terraform destroy -target=aws_instance.web
```

### Terraform State Lifecycle

#### State File Structure
```json
{
  "version": 4,
  "terraform_version": "1.5.0",
  "serial": 42,
  "lineage": "unique-uuid",
  "outputs": {},
  "resources": [
    {
      "mode": "managed",
      "type": "aws_instance",
      "name": "web",
      "provider": "provider[\"registry.terraform.io/hashicorp/aws\"]",
      "instances": [
        {
          "schema_version": 1,
          "attributes": {
            "id": "i-1234567890abcdef0",
            "ami": "ami-0c55b159cbfafe1f0"
          }
        }
      ]
    }
  ]
}
```

**State Operations:**
```bash
# List resources in state
terraform state list

# Show specific resource
terraform state show aws_instance.web

# Move resource in state
terraform state mv aws_instance.old aws_instance.new

# Remove resource from state
terraform state rm aws_instance.deprecated

# Pull remote state
terraform state pull > terraform.tfstate

# Push state to remote
terraform state push terraform.tfstate

# Replace provider
terraform state replace-provider old.com/provider new.com/provider
```

### Provider Configuration

#### Single Provider
```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.5.0"
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      ManagedBy   = "Terraform"
      Environment = var.environment
      Project     = var.project_name
    }
  }
}
```

#### Multiple Provider Instances
```hcl
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

provider "aws" {
  alias  = "us_west_2"
  region = "us-west-2"
}

# Use specific provider
resource "aws_instance" "east" {
  provider = aws.us_east_1
  # ...
}

resource "aws_instance" "west" {
  provider = aws.us_west_2
  # ...
}
```

#### Provider Authentication
```hcl
# Method 1: Environment variables (recommended)
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

# Method 2: Shared credentials file
provider "aws" {
  shared_credentials_files = ["~/.aws/credentials"]
  profile                  = "production"
}

# Method 3: IAM role (ECS, EC2, Lambda)
provider "aws" {
  # Automatically uses instance role
}

# Method 4: Assume role
provider "aws" {
  assume_role {
    role_arn     = "arn:aws:iam::123456789012:role/TerraformRole"
    session_name = "terraform-session"
  }
}
```

### Resource Dependencies

#### Implicit Dependencies
```hcl
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "private" {
  vpc_id     = aws_vpc.main.id  # Implicit dependency
  cidr_block = "10.0.1.0/24"
}
```

#### Explicit Dependencies
```hcl
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  depends_on = [
    aws_iam_role_policy.web_policy,
    aws_security_group.web_sg
  ]
}
```

#### Dependency Graph
```bash
# Generate dependency graph
terraform graph | dot -Tsvg > graph.svg

# Generate visual representation
terraform graph -type=plan | dot -Tpng > plan-graph.png
```

### Data Sources

#### Using Data Sources
```hcl
# Fetch existing VPC
data "aws_vpc" "existing" {
  filter {
    name   = "tag:Name"
    values = ["production-vpc"]
  }
}

# Use data source output
resource "aws_subnet" "new" {
  vpc_id     = data.aws_vpc.existing.id
  cidr_block = "10.0.5.0/24"
}

# Fetch AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
}

# Fetch availability zones
data "aws_availability_zones" "available" {
  state = "available"

  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}
```

### Resource Meta-Arguments

#### count
```hcl
resource "aws_instance" "server" {
  count = 3

  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  tags = {
    Name = "server-${count.index}"
  }
}

# Reference: aws_instance.server[0].id
```

#### for_each
```hcl
locals {
  subnets = {
    "private-a" = { cidr = "10.0.1.0/24", az = "us-east-1a" }
    "private-b" = { cidr = "10.0.2.0/24", az = "us-east-1b" }
    "public-a"  = { cidr = "10.0.3.0/24", az = "us-east-1a" }
  }
}

resource "aws_subnet" "main" {
  for_each = local.subnets

  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az

  tags = {
    Name = each.key
  }
}

# Reference: aws_subnet.main["private-a"].id
```

#### lifecycle
```hcl
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  lifecycle {
    # Prevent resource destruction
    prevent_destroy = true

    # Create before destroy
    create_before_destroy = true

    # Ignore changes to specific attributes
    ignore_changes = [
      ami,
      user_data,
    ]

    # Condition-based lifecycle
    replace_triggered_by = [
      aws_security_group.web.id
    ]
  }
}
```

#### provisioner
```hcl
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  # Local-exec provisioner
  provisioner "local-exec" {
    command = "echo ${self.private_ip} >> private_ips.txt"
  }

  # Remote-exec provisioner
  provisioner "remote-exec" {
    inline = [
      "sudo apt-get update",
      "sudo apt-get install -y nginx",
    ]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = file("~/.ssh/id_rsa")
      host        = self.public_ip
    }
  }

  # Destroy-time provisioner
  provisioner "local-exec" {
    when    = destroy
    command = "echo 'Destroying ${self.id}' >> destroy.log"
  }
}
```

---

## State Management

### Remote State Backends

#### S3 Backend
```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"

    # Optional: State versioning
    versioning = true

    # Optional: KMS encryption
    kms_key_id = "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  }
}
```

**S3 Backend Setup:**
```bash
# Create S3 bucket
aws s3 mb s3://my-terraform-state --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket my-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Create DynamoDB table for locking
aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

#### Terraform Cloud Backend
```hcl
terraform {
  cloud {
    organization = "my-org"

    workspaces {
      name = "production"
    }
  }
}
```

#### Azure Backend
```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstate12345"
    container_name       = "tfstate"
    key                  = "production.terraform.tfstate"
  }
}
```

#### GCS Backend
```hcl
terraform {
  backend "gcs" {
    bucket = "my-terraform-state"
    prefix = "production"
  }
}
```

### State Locking

#### Why State Locking Matters
```bash
# Without locking:
# User A: terraform apply (starts)
# User B: terraform apply (starts) <- CONFLICT!
# Result: Corrupted state, race conditions

# With locking:
# User A: terraform apply (acquires lock)
# User B: terraform apply (waits for lock)
# Result: Safe sequential execution
```

#### DynamoDB Locking Configuration
```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"  # Enables locking
  }
}
```

**Lock Table Structure:**
```json
{
  "LockID": "my-terraform-state/terraform.tfstate",
  "Info": {
    "ID": "12345678-1234-1234-1234-123456789012",
    "Operation": "OperationTypeApply",
    "Who": "user@example.com",
    "Version": "1.5.0",
    "Created": "2024-01-15T10:30:00Z",
    "Path": "terraform.tfstate"
  }
}
```

#### Force Unlock (Emergency)
```bash
# Get lock ID from error message
terraform force-unlock <LOCK_ID>

# Example
terraform force-unlock 12345678-1234-1234-1234-123456789012
```

### State File Best Practices

#### State File Security
```hcl
# 1. Enable encryption at rest
terraform {
  backend "s3" {
    encrypt    = true
    kms_key_id = "arn:aws:kms:us-east-1:123456789012:key/..."
  }
}

# 2. Restrict access with IAM policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-terraform-state/*",
      "Condition": {
        "StringEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    }
  ]
}
```

#### State File Versioning
```bash
# List state versions
aws s3api list-object-versions \
  --bucket my-terraform-state \
  --prefix terraform.tfstate

# Restore previous version
aws s3api get-object \
  --bucket my-terraform-state \
  --key terraform.tfstate \
  --version-id <VERSION_ID> \
  terraform.tfstate.backup
```

#### State Backup Strategy
```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="./state-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Pull current state
terraform state pull > "$BACKUP_DIR/terraform.tfstate.$TIMESTAMP"

# Compress old backups
find $BACKUP_DIR -name "*.tfstate.*" -mtime +30 -exec gzip {} \;

# Delete backups older than 90 days
find $BACKUP_DIR -name "*.tfstate.*.gz" -mtime +90 -delete
```

### State Migration

#### Migrating from Local to Remote
```bash
# 1. Backup local state
cp terraform.tfstate terraform.tfstate.backup

# 2. Add backend configuration
cat > backend.tf <<EOF
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}
EOF

# 3. Initialize backend
terraform init -migrate-state

# 4. Verify migration
terraform state list
aws s3 ls s3://my-terraform-state/
```

#### Changing Backend Configuration
```bash
# 1. Update backend configuration
# 2. Reinitialize
terraform init -reconfigure

# OR with migration
terraform init -migrate-state
```

#### Splitting State Files
```bash
# Scenario: Split monolithic state into multiple workspaces

# 1. Pull current state
terraform state pull > full-state.json

# 2. Create new workspace
terraform workspace new database

# 3. Import resources
terraform import aws_db_instance.main <id>
terraform import aws_db_subnet_group.main <name>

# 4. Remove from original state
terraform workspace select default
terraform state rm aws_db_instance.main
terraform state rm aws_db_subnet_group.main
```

### Remote State Data Source

#### Reading Remote State
```hcl
# Network infrastructure (separate state)
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = "my-terraform-state"
    key    = "network/terraform.tfstate"
    region = "us-east-1"
  }
}

# Use outputs from remote state
resource "aws_instance" "app" {
  subnet_id = data.terraform_remote_state.network.outputs.private_subnet_id
  vpc_security_group_ids = [
    data.terraform_remote_state.network.outputs.app_security_group_id
  ]
}
```

#### Output Design for Remote State
```hcl
# In network module outputs.tf
output "private_subnet_id" {
  description = "ID of private subnet for applications"
  value       = aws_subnet.private.id
}

output "app_security_group_id" {
  description = "Security group ID for application tier"
  value       = aws_security_group.app.id
}

output "vpc_cidr_block" {
  description = "CIDR block of VPC"
  value       = aws_vpc.main.cidr_block
}
```

### State File Troubleshooting

#### Common State Issues

**Issue 1: State Drift**
```bash
# Detect drift
terraform plan -detailed-exitcode
# Exit code 0: No changes
# Exit code 1: Error
# Exit code 2: Changes detected

# Reconcile drift
terraform apply -refresh-only

# Ignore specific attributes
resource "aws_instance" "web" {
  lifecycle {
    ignore_changes = [ami, user_data]
  }
}
```

**Issue 2: Resource Already Exists**
```bash
# Import existing resource
terraform import aws_instance.web i-1234567890abcdef0

# Verify import
terraform plan
```

**Issue 3: State Lock Timeout**
```bash
# Increase timeout
terraform apply -lock-timeout=10m

# Force unlock (use carefully)
terraform force-unlock <LOCK_ID>
```

**Issue 4: Corrupted State**
```bash
# Restore from backup
aws s3 cp s3://my-terraform-state/terraform.tfstate.backup ./

# Push backup as current state
terraform state push terraform.tfstate.backup

# Verify
terraform plan
```

---

## Module Design Patterns

### Module Structure

#### Standard Module Layout
```
terraform-aws-vpc/
├── README.md
├── main.tf
├── variables.tf
├── outputs.tf
├── versions.tf
├── examples/
│   ├── complete/
│   │   ├── main.tf
│   │   └── README.md
│   └── simple/
│       ├── main.tf
│       └── README.md
└── tests/
    └── vpc_test.go
```

#### Module main.tf
```hcl
# terraform-aws-vpc/main.tf

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# VPC
resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = var.enable_dns_hostnames
  enable_dns_support   = var.enable_dns_support

  tags = merge(
    var.tags,
    {
      Name = var.name
    }
  )
}

# Subnets
resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(
    var.tags,
    {
      Name = "${var.name}-public-${var.availability_zones[count.index]}"
      Tier = "Public"
    }
  )
}

resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(
    var.tags,
    {
      Name = "${var.name}-private-${var.availability_zones[count.index]}"
      Tier = "Private"
    }
  )
}

# Internet Gateway
resource "aws_internet_gateway" "this" {
  count = length(var.public_subnet_cidrs) > 0 ? 1 : 0

  vpc_id = aws_vpc.this.id

  tags = merge(
    var.tags,
    {
      Name = "${var.name}-igw"
    }
  )
}

# NAT Gateways
resource "aws_eip" "nat" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.public_subnet_cidrs)) : 0

  domain = "vpc"

  tags = merge(
    var.tags,
    {
      Name = "${var.name}-nat-${count.index}"
    }
  )

  depends_on = [aws_internet_gateway.this]
}

resource "aws_nat_gateway" "this" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.public_subnet_cidrs)) : 0

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(
    var.tags,
    {
      Name = "${var.name}-nat-${count.index}"
    }
  )

  depends_on = [aws_internet_gateway.this]
}

# Route Tables
resource "aws_route_table" "public" {
  count = length(var.public_subnet_cidrs) > 0 ? 1 : 0

  vpc_id = aws_vpc.this.id

  tags = merge(
    var.tags,
    {
      Name = "${var.name}-public"
      Tier = "Public"
    }
  )
}

resource "aws_route" "public_internet_gateway" {
  count = length(var.public_subnet_cidrs) > 0 ? 1 : 0

  route_table_id         = aws_route_table.public[0].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this[0].id
}

resource "aws_route_table_association" "public" {
  count = length(var.public_subnet_cidrs)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_route_table" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id = aws_vpc.this.id

  tags = merge(
    var.tags,
    {
      Name = "${var.name}-private-${count.index}"
      Tier = "Private"
    }
  )
}

resource "aws_route" "private_nat_gateway" {
  count = var.enable_nat_gateway ? length(var.private_subnet_cidrs) : 0

  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = var.single_nat_gateway ? aws_nat_gateway.this[0].id : aws_nat_gateway.this[count.index].id
}

resource "aws_route_table_association" "private" {
  count = length(var.private_subnet_cidrs)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}
```

#### Module variables.tf
```hcl
# terraform-aws-vpc/variables.tf

variable "name" {
  description = "Name to be used on all resources as prefix"
  type        = string
}

variable "cidr_block" {
  description = "CIDR block for VPC"
  type        = string

  validation {
    condition     = can(cidrhost(var.cidr_block, 0))
    error_message = "Must be valid IPv4 CIDR."
  }
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for cidr in var.public_subnet_cidrs : can(cidrhost(cidr, 0))
    ])
    error_message = "All CIDRs must be valid IPv4 CIDR blocks."
  }
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = []
}

variable "enable_dns_hostnames" {
  description = "Enable DNS hostnames in VPC"
  type        = bool
  default     = true
}

variable "enable_dns_support" {
  description = "Enable DNS support in VPC"
  type        = bool
  default     = true
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use single NAT Gateway for all private subnets"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
```

#### Module outputs.tf
```hcl
# terraform-aws-vpc/outputs.tf

output "vpc_id" {
  description = "ID of VPC"
  value       = aws_vpc.this.id
}

output "vpc_cidr_block" {
  description = "CIDR block of VPC"
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "nat_gateway_ids" {
  description = "IDs of NAT Gateways"
  value       = aws_nat_gateway.this[*].id
}

output "internet_gateway_id" {
  description = "ID of Internet Gateway"
  value       = try(aws_internet_gateway.this[0].id, null)
}

output "public_route_table_id" {
  description = "ID of public route table"
  value       = try(aws_route_table.public[0].id, null)
}

output "private_route_table_ids" {
  description = "IDs of private route tables"
  value       = aws_route_table.private[*].id
}
```

### Module Composition

#### Nested Modules
```hcl
# Root module using child modules

module "vpc" {
  source = "./modules/vpc"

  name               = "production"
  cidr_block         = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
}

module "eks" {
  source = "./modules/eks"

  cluster_name    = "production-eks"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnet_ids
  cluster_version = "1.28"
}

module "rds" {
  source = "./modules/rds"

  identifier     = "production-db"
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_subnet_ids
  engine_version = "15.4"
}
```

#### Module Dependencies
```hcl
# Explicit dependencies between modules

module "network" {
  source = "./modules/network"
}

module "security" {
  source = "./modules/security"

  vpc_id = module.network.vpc_id

  depends_on = [module.network]
}

module "compute" {
  source = "./modules/compute"

  vpc_id             = module.network.vpc_id
  subnet_ids         = module.network.subnet_ids
  security_group_ids = module.security.security_group_ids

  depends_on = [module.network, module.security]
}
```

### Module Versioning

#### Git-based Versioning
```hcl
# Using Git tags
module "vpc" {
  source = "git::https://github.com/myorg/terraform-aws-vpc.git?ref=v1.2.3"
}

# Using Git branch
module "vpc" {
  source = "git::https://github.com/myorg/terraform-aws-vpc.git?ref=main"
}

# Using Git commit
module "vpc" {
  source = "git::https://github.com/myorg/terraform-aws-vpc.git?ref=abc123"
}
```

#### Terraform Registry Versioning
```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"  # Any 5.x version
}

# Exact version
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.1.0"
}

# Version constraints
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = ">= 5.0, < 6.0"
}
```

#### Semantic Versioning
```
MAJOR.MINOR.PATCH

MAJOR: Breaking changes
MINOR: New features, backward compatible
PATCH: Bug fixes, backward compatible

Examples:
1.0.0 -> 1.0.1 (bug fix)
1.0.1 -> 1.1.0 (new feature)
1.1.0 -> 2.0.0 (breaking change)
```

### Module Testing

#### Terratest Example
```go
// tests/vpc_test.go
package test

import (
	"testing"

	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestVPCModule(t *testing.T) {
	terraformOptions := &terraform.Options{
		TerraformDir: "../examples/complete",
		Vars: map[string]interface{}{
			"name":       "test-vpc",
			"cidr_block": "10.0.0.0/16",
		},
	}

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	vpcID := terraform.Output(t, terraformOptions, "vpc_id")
	assert.NotEmpty(t, vpcID)

	publicSubnetIDs := terraform.OutputList(t, terraformOptions, "public_subnet_ids")
	assert.Equal(t, 3, len(publicSubnetIDs))
}
```

---

## Variable Management

### Variable Types

#### Primitive Types
```hcl
# String
variable "region" {
  type    = string
  default = "us-east-1"
}

# Number
variable "instance_count" {
  type    = number
  default = 3
}

# Bool
variable "enable_monitoring" {
  type    = bool
  default = true
}
```

#### Collection Types
```hcl
# List
variable "availability_zones" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

# Set (unique values)
variable "allowed_cidr_blocks" {
  type    = set(string)
  default = ["10.0.0.0/8", "172.16.0.0/12"]
}

# Map
variable "tags" {
  type = map(string)
  default = {
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}
```

#### Structural Types
```hcl
# Object
variable "database_config" {
  type = object({
    engine         = string
    engine_version = string
    instance_class = string
    allocated_storage = number
  })

  default = {
    engine         = "postgres"
    engine_version = "15.4"
    instance_class = "db.t3.medium"
    allocated_storage = 100
  }
}

# Tuple
variable "subnet_config" {
  type = tuple([string, string, number])
  default = ["us-east-1a", "10.0.1.0/24", 256]
}

# Complex nested types
variable "vpc_config" {
  type = object({
    cidr_block = string
    subnets = list(object({
      cidr_block = string
      availability_zone = string
      public = bool
    }))
    tags = map(string)
  })
}
```

### Variable Validation

#### Built-in Validation
```hcl
variable "environment" {
  type        = string
  description = "Environment name"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "cidr_block" {
  type = string

  validation {
    condition     = can(cidrhost(var.cidr_block, 0))
    error_message = "Must be valid IPv4 CIDR block."
  }
}

variable "instance_count" {
  type = number

  validation {
    condition     = var.instance_count >= 1 && var.instance_count <= 10
    error_message = "Instance count must be between 1 and 10."
  }
}

variable "tags" {
  type = map(string)

  validation {
    condition     = contains(keys(var.tags), "Environment")
    error_message = "Tags must include Environment key."
  }
}
```

#### Complex Validation
```hcl
variable "subnets" {
  type = list(object({
    cidr_block        = string
    availability_zone = string
  }))

  validation {
    condition = alltrue([
      for subnet in var.subnets : can(cidrhost(subnet.cidr_block, 0))
    ])
    error_message = "All subnet CIDR blocks must be valid."
  }

  validation {
    condition = length(var.subnets) >= 2
    error_message = "At least 2 subnets required for high availability."
  }
}
```

### Sensitive Variables

#### Marking Variables Sensitive
```hcl
variable "database_password" {
  type      = string
  sensitive = true
}

variable "api_keys" {
  type = map(string)
  sensitive = true
}

# Usage in resources
resource "aws_db_instance" "main" {
  password = var.database_password  # Value hidden in logs
}

# Sensitive outputs
output "db_password" {
  value     = aws_db_instance.main.password
  sensitive = true
}
```

#### Sensitive Data Management
```hcl
# Method 1: AWS Secrets Manager
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "production/database/password"
}

locals {
  db_password = jsondecode(data.aws_secretsmanager_secret_version.db_password.secret_string)["password"]
}

# Method 2: AWS Systems Manager Parameter Store
data "aws_ssm_parameter" "db_password" {
  name = "/production/database/password"
}

resource "aws_db_instance" "main" {
  password = data.aws_ssm_parameter.db_password.value
}

# Method 3: HashiCorp Vault
data "vault_generic_secret" "db_password" {
  path = "secret/database"
}

resource "aws_db_instance" "main" {
  password = data.vault_generic_secret.db_password.data["password"]
}
```

### Variable Files

#### terraform.tfvars
```hcl
# terraform.tfvars (auto-loaded)
region      = "us-east-1"
environment = "production"

tags = {
  Project   = "MyApp"
  ManagedBy = "Terraform"
}

vpc_config = {
  cidr_block = "10.0.0.0/16"
  subnets = [
    {
      cidr_block        = "10.0.1.0/24"
      availability_zone = "us-east-1a"
      public            = true
    },
    {
      cidr_block        = "10.0.2.0/24"
      availability_zone = "us-east-1b"
      public            = false
    }
  ]
}
```

#### Environment-specific Variable Files
```bash
# Directory structure
terraform/
├── terraform.tfvars       # Common defaults
├── dev.tfvars            # Development
├── staging.tfvars        # Staging
└── production.tfvars     # Production

# Use specific file
terraform apply -var-file="production.tfvars"

# Multiple var files
terraform apply -var-file="common.tfvars" -var-file="production.tfvars"
```

#### Auto-loaded Variable Files
```bash
# Terraform automatically loads (in order):
1. terraform.tfvars
2. terraform.tfvars.json
3. *.auto.tfvars
4. *.auto.tfvars.json

# Example auto-loaded files
terraform/
├── terraform.tfvars
├── common.auto.tfvars
└── tags.auto.tfvars
```

### Variable Precedence

```
1. Environment variables (TF_VAR_*)
2. terraform.tfvars
3. terraform.tfvars.json
4. *.auto.tfvars (alphabetical)
5. *.auto.tfvars.json (alphabetical)
6. -var and -var-file (command line)

Lower numbers are overridden by higher numbers
```

#### Example
```bash
# 1. Environment variable
export TF_VAR_region="us-west-1"

# 2. terraform.tfvars
region = "us-east-1"

# 3. Command line (highest precedence)
terraform apply -var="region=eu-west-1"

# Result: region = "eu-west-1"
```

---

## Resource Naming Conventions

### Naming Standards

#### Resource Naming Pattern
```
<org>-<environment>-<region>-<resource-type>-<purpose>-<counter>

Examples:
mycompany-prod-use1-vpc-main
mycompany-prod-use1-eks-cluster-01
mycompany-dev-usw2-rds-postgres-users
```

#### Terraform Resource Names
```hcl
# Use descriptive, consistent names
resource "aws_vpc" "main" {           # Good
  name = "mycompany-prod-use1-vpc-main"
}

resource "aws_vpc" "v" {              # Bad
  name = "vpc1"
}

# Consistent naming across resources
resource "aws_subnet" "public" {
  count = 3
  name  = "mycompany-prod-use1-subnet-public-${count.index + 1}"
}

resource "aws_subnet" "private" {
  count = 3
  name  = "mycompany-prod-use1-subnet-private-${count.index + 1}"
}
```

### Tagging Strategy

#### Mandatory Tags
```hcl
locals {
  mandatory_tags = {
    ManagedBy   = "Terraform"
    Environment = var.environment
    Project     = var.project_name
    Owner       = var.owner_email
    CostCenter  = var.cost_center
    CreatedDate = formatdate("YYYY-MM-DD", timestamp())
  }
}

resource "aws_instance" "web" {
  ami           = var.ami_id
  instance_type = var.instance_type

  tags = merge(
    local.mandatory_tags,
    var.additional_tags,
    {
      Name = "mycompany-prod-web-01"
      Role = "WebServer"
    }
  )
}
```

#### Tag Inheritance
```hcl
# Provider-level default tags (AWS)
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      ManagedBy   = "Terraform"
      Environment = var.environment
      Project     = var.project_name
    }
  }
}

# Resources automatically inherit default tags
resource "aws_instance" "web" {
  ami           = var.ami_id
  instance_type = var.instance_type

  # Additional resource-specific tags
  tags = {
    Name = "web-server"
    Role = "Application"
  }
}
```

#### Tag Validation
```hcl
variable "tags" {
  type = map(string)

  validation {
    condition = alltrue([
      contains(keys(var.tags), "Environment"),
      contains(keys(var.tags), "Owner"),
      contains(keys(var.tags), "CostCenter")
    ])
    error_message = "Tags must include Environment, Owner, and CostCenter."
  }
}
```

### Naming Functions

#### String Manipulation
```hcl
locals {
  # Lowercase
  vpc_name = lower("${var.project_name}-${var.environment}-vpc")

  # Uppercase
  region_code = upper(var.region)

  # Title case
  env_display = title(var.environment)

  # Replace
  bucket_name = replace(lower("${var.project_name}-${var.environment}"), "_", "-")

  # Trim
  sanitized_name = trimspace(var.user_input)

  # Substring
  short_region = substr(var.region, 0, 3)
}
```

#### Format and Join
```hcl
locals {
  # Format
  instance_name = format("%s-%s-instance-%02d", var.project, var.env, var.index)

  # Join
  security_group_name = join("-", [var.project, var.environment, "sg", var.tier])

  # Concat
  all_cidrs = concat(var.public_cidrs, var.private_cidrs)
}
```

---

## Code Organization

### File Structure

#### Small Project
```
terraform/
├── main.tf           # Main resources
├── variables.tf      # Input variables
├── outputs.tf        # Output values
├── versions.tf       # Provider versions
├── terraform.tfvars  # Variable values
└── README.md         # Documentation
```

#### Medium Project
```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── versions.tf
├── data.tf          # Data sources
├── locals.tf        # Local values
├── providers.tf     # Provider configuration
├── backend.tf       # Backend configuration
├── terraform.tfvars
└── README.md
```

#### Large Project
```
terraform/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   ├── staging/
│   │   ├── main.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   └── production/
│       ├── main.tf
│       ├── terraform.tfvars
│       └── backend.tf
├── modules/
│   ├── networking/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── compute/
│   └── database/
├── shared/
│   ├── variables.tf  # Common variables
│   └── locals.tf     # Common locals
└── README.md
```

### Resource Grouping

#### Logical Grouping
```hcl
# network.tf - Networking resources
resource "aws_vpc" "main" { }
resource "aws_subnet" "public" { }
resource "aws_subnet" "private" { }
resource "aws_route_table" "main" { }

# security.tf - Security resources
resource "aws_security_group" "web" { }
resource "aws_security_group" "db" { }
resource "aws_iam_role" "app" { }

# compute.tf - Compute resources
resource "aws_instance" "web" { }
resource "aws_autoscaling_group" "web" { }
resource "aws_launch_template" "web" { }

# database.tf - Database resources
resource "aws_db_instance" "main" { }
resource "aws_db_subnet_group" "main" { }
resource "aws_db_parameter_group" "main" { }

# monitoring.tf - Monitoring resources
resource "aws_cloudwatch_metric_alarm" "cpu" { }
resource "aws_sns_topic" "alerts" { }
```

### Locals Usage

#### Computed Values
```hcl
locals {
  # Environment-specific configuration
  is_production = var.environment == "production"

  instance_type = local.is_production ? "t3.large" : "t3.small"

  instance_count = local.is_production ? 3 : 1

  # Common resource naming
  name_prefix = "${var.project_name}-${var.environment}"

  vpc_name     = "${local.name_prefix}-vpc"
  cluster_name = "${local.name_prefix}-eks"

  # Tag composition
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Repository  = "github.com/myorg/myrepo"
  }

  # CIDR calculations
  vpc_cidr = "10.${var.environment_number}.0.0/16"

  public_subnets = [
    for i in range(3) :
    cidrsubnet(local.vpc_cidr, 8, i)
  ]

  private_subnets = [
    for i in range(3) :
    cidrsubnet(local.vpc_cidr, 8, i + 10)
  ]
}
```

#### Complex Transformations
```hcl
locals {
  # Flatten nested structures
  all_subnets = flatten([
    for az_key, az_value in var.availability_zones : [
      for subnet_key, subnet_value in var.subnets : {
        az     = az_value
        cidr   = subnet_value.cidr
        public = subnet_value.public
        name   = "${local.name_prefix}-${az_key}-${subnet_key}"
      }
    ]
  ])

  # Convert list to map
  subnet_map = {
    for subnet in local.all_subnets :
    subnet.name => subnet
  }

  # Filter and transform
  public_subnet_cidrs = [
    for subnet in local.all_subnets :
    subnet.cidr
    if subnet.public
  ]

  # Conditional logic
  monitoring_config = {
    enabled            = local.is_production
    retention_days     = local.is_production ? 365 : 30
    detailed_monitoring = local.is_production
  }
}
```

### Comments and Documentation

#### Code Comments
```hcl
# VPC Configuration
# Creates a VPC with public and private subnets across multiple AZs
# NAT Gateways are deployed in public subnets for private subnet internet access

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    local.common_tags,
    {
      Name = local.vpc_name
    }
  )
}

# Public Subnets
# These subnets have direct internet access via Internet Gateway
# Used for: Load Balancers, NAT Gateways, Bastion Hosts
resource "aws_subnet" "public" {
  count = length(local.public_subnets)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_subnets[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-public-${count.index + 1}"
      Tier = "Public"
      # Required for EKS
      "kubernetes.io/role/elb" = "1"
    }
  )
}
```

#### Module Documentation
```hcl
# Module: AWS VPC with Multi-AZ High Availability
#
# Purpose:
#   Creates a production-ready VPC with:
#   - Public and private subnets across 3 AZs
#   - NAT Gateways for private subnet internet access
#   - VPC Flow Logs for network monitoring
#   - Tags for EKS cluster integration
#
# Usage:
#   module "vpc" {
#     source = "./modules/vpc"
#
#     name               = "production"
#     cidr_block         = "10.0.0.0/16"
#     availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
#   }
#
# Outputs:
#   - vpc_id: VPC identifier
#   - public_subnet_ids: List of public subnet IDs
#   - private_subnet_ids: List of private subnet IDs
#
# Dependencies:
#   - AWS Provider >= 5.0
#   - Terraform >= 1.5.0
```

---

## DRY Principles

### for_each vs count

#### When to Use count
```hcl
# Simple repetition with identical resources
resource "aws_instance" "web" {
  count = 3

  ami           = var.ami_id
  instance_type = "t3.micro"

  tags = {
    Name = "web-${count.index + 1}"
  }
}

# Conditional resource creation
resource "aws_eip" "nat" {
  count = var.enable_nat_gateway ? 1 : 0

  domain = "vpc"
}
```

#### When to Use for_each
```hcl
# Different configurations per resource
locals {
  instances = {
    web = {
      instance_type = "t3.small"
      ami           = "ami-12345"
    }
    api = {
      instance_type = "t3.medium"
      ami           = "ami-67890"
    }
  }
}

resource "aws_instance" "app" {
  for_each = local.instances

  ami           = each.value.ami
  instance_type = each.value.instance_type

  tags = {
    Name = each.key
  }
}

# Reference: aws_instance.app["web"].id
```

#### Converting from count to for_each
```hcl
# Before (count)
resource "aws_subnet" "private" {
  count = 3

  cidr_block = var.private_subnet_cidrs[count.index]
}

# After (for_each) - more stable
locals {
  private_subnets = {
    "private-a" = { cidr = "10.0.1.0/24", az = "us-east-1a" }
    "private-b" = { cidr = "10.0.2.0/24", az = "us-east-1b" }
    "private-c" = { cidr = "10.0.3.0/24", az = "us-east-1c" }
  }
}

resource "aws_subnet" "private" {
  for_each = local.private_subnets

  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az

  tags = {
    Name = each.key
  }
}
```

### Dynamic Blocks

#### Basic Dynamic Block
```hcl
resource "aws_security_group" "web" {
  name   = "web-sg"
  vpc_id = aws_vpc.main.id

  dynamic "ingress" {
    for_each = var.ingress_rules

    content {
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidr_blocks
      description = ingress.value.description
    }
  }
}

# Variable
variable "ingress_rules" {
  type = list(object({
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_blocks = list(string)
    description = string
  }))

  default = [
    {
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTP from anywhere"
    },
    {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTPS from anywhere"
    }
  ]
}
```

#### Nested Dynamic Blocks
```hcl
resource "aws_ecs_task_definition" "app" {
  family = "app"

  dynamic "volume" {
    for_each = var.volumes

    content {
      name = volume.value.name

      dynamic "efs_volume_configuration" {
        for_each = volume.value.efs_config != null ? [volume.value.efs_config] : []

        content {
          file_system_id     = efs_volume_configuration.value.file_system_id
          root_directory     = efs_volume_configuration.value.root_directory
          transit_encryption = efs_volume_configuration.value.transit_encryption
        }
      }
    }
  }
}
```

### Data Source Reuse

#### Shared Data Sources
```hcl
# data.tf - Centralized data sources

# Current AWS account
data "aws_caller_identity" "current" {}

# Current region
data "aws_region" "current" {}

# Available AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# Latest AMI
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# Usage in resources
resource "aws_instance" "web" {
  ami               = data.aws_ami.amazon_linux_2.id
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Owner     = data.aws_caller_identity.current.arn
    Region    = data.aws_region.current.name
    AccountId = data.aws_caller_identity.current.account_id
  }
}
```

### Template Files

#### Using templatefile()
```hcl
# user_data.sh.tpl
#!/bin/bash
yum update -y
yum install -y ${package_name}

echo "Environment: ${environment}" > /etc/app/config
echo "Database: ${database_endpoint}" >> /etc/app/config

# main.tf
resource "aws_instance" "web" {
  ami           = var.ami_id
  instance_type = "t3.micro"

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    package_name      = "nginx"
    environment       = var.environment
    database_endpoint = aws_db_instance.main.endpoint
  })
}
```

#### Cloud-init Configuration
```hcl
# cloud-init.yaml.tpl
#cloud-config
packages:
  - ${package_name}
  - aws-cli

write_files:
  - path: /etc/app/config.json
    content: |
      {
        "environment": "${environment}",
        "database": "${database_endpoint}",
        "region": "${region}"
      }

runcmd:
  - systemctl start ${service_name}
  - systemctl enable ${service_name}

# main.tf
data "cloudinit_config" "web" {
  gzip          = true
  base64_encode = true

  part {
    content_type = "text/cloud-config"
    content = templatefile("${path.module}/cloud-init.yaml.tpl", {
      package_name      = "nginx"
      service_name      = "nginx"
      environment       = var.environment
      database_endpoint = aws_db_instance.main.endpoint
      region            = var.region
    })
  }
}

resource "aws_instance" "web" {
  user_data = data.cloudinit_config.web.rendered
}
```

---

## Testing Strategies

### Terraform Validate

#### Basic Validation
```bash
# Validate configuration syntax
terraform validate

# Validate with JSON output
terraform validate -json

# Expected output
{
  "valid": true,
  "error_count": 0,
  "warning_count": 0
}
```

#### Pre-commit Hook
```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running terraform fmt..."
terraform fmt -check -recursive

if [ $? -ne 0 ]; then
  echo "Terraform formatting issues found. Run 'terraform fmt -recursive'"
  exit 1
fi

echo "Running terraform validate..."
terraform validate

if [ $? -ne 0 ]; then
  echo "Terraform validation failed"
  exit 1
fi

echo "All checks passed!"
exit 0
```

### TFLint

#### Installation and Configuration
```bash
# Install tflint
curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash

# Create .tflint.hcl
cat > .tflint.hcl <<EOF
plugin "aws" {
  enabled = true
  version = "0.27.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

rule "terraform_naming_convention" {
  enabled = true
}

rule "terraform_deprecated_interpolation" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}
EOF

# Run tflint
tflint --init
tflint
```

#### Custom Rules
```hcl
# .tflint.hcl

rule "aws_instance_invalid_type" {
  enabled = true
}

rule "aws_db_instance_invalid_type" {
  enabled = true
}

rule "terraform_required_providers" {
  enabled = true
}

rule "terraform_required_version" {
  enabled = true
}
```

### Terratest

#### Basic Test Structure
```go
// test/vpc_test.go
package test

import (
	"testing"

	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestVPCCreation(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../examples/vpc",

		Vars: map[string]interface{}{
			"name":       "test-vpc",
			"cidr_block": "10.0.0.0/16",
		},

		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": "us-east-1",
		},
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	vpcID := terraform.Output(t, terraformOptions, "vpc_id")
	assert.NotEmpty(t, vpcID)
	assert.Regexp(t, "^vpc-", vpcID)

	subnetIDs := terraform.OutputList(t, terraformOptions, "subnet_ids")
	assert.Equal(t, 3, len(subnetIDs))
}
```

#### Integration Tests
```go
func TestWebServerIntegration(t *testing.T) {
	t.Parallel()

	terraformOptions := &terraform.Options{
		TerraformDir: "../",
	}

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Get outputs
	albDNS := terraform.Output(t, terraformOptions, "alb_dns_name")

	// Test HTTP endpoint
	http_helper.HttpGetWithRetry(
		t,
		fmt.Sprintf("http://%s", albDNS),
		nil,
		200,
		"Hello World",
		30,
		10*time.Second,
	)
}
```

### Policy as Code

#### OPA (Open Policy Agent)
```rego
# policy/terraform.rego

package terraform

# Deny if instance type is not allowed
deny[msg] {
	resource := input.resource_changes[_]
	resource.type == "aws_instance"
	not allowed_instance_type(resource.change.after.instance_type)

	msg := sprintf("Instance type %s is not allowed", [resource.change.after.instance_type])
}

allowed_instance_type(type) {
	allowed_types := ["t3.micro", "t3.small", "t3.medium"]
	allowed_types[_] == type
}

# Require encryption for RDS
deny[msg] {
	resource := input.resource_changes[_]
	resource.type == "aws_db_instance"
	resource.change.after.storage_encrypted == false

	msg := "RDS instances must have storage encryption enabled"
}

# Require tags
deny[msg] {
	resource := input.resource_changes[_]
	not resource.change.after.tags.Environment

	msg := sprintf("Resource %s must have Environment tag", [resource.address])
}
```

#### Running OPA Tests
```bash
# Generate plan in JSON
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json

# Run OPA evaluation
opa eval -i tfplan.json -d policy/terraform.rego "data.terraform.deny"

# CI/CD integration
opa test policy/ -v
```

#### Sentinel (Terraform Cloud)
```hcl
# sentinel/require-tags.sentinel

import "tfplan/v2" as tfplan

required_tags = ["Environment", "Owner", "CostCenter"]

main = rule {
	all tfplan.resource_changes as _, rc {
		rc.mode is "managed" and
		rc.type not in ["terraform_data"] and
		all required_tags as tag {
			rc.change.after.tags[tag] exists
		}
	}
}
```

---

## CI/CD Integration

### GitHub Actions

#### Basic Workflow
```yaml
# .github/workflows/terraform.yml

name: Terraform CI/CD

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

env:
  TF_VERSION: '1.5.0'
  AWS_REGION: 'us-east-1'

jobs:
  validate:
    name: Validate
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform Format
        run: terraform fmt -check -recursive

      - name: Terraform Init
        run: terraform init -backend=false

      - name: Terraform Validate
        run: terraform validate

      - name: TFLint
        uses: terraform-linters/setup-tflint@v3
        with:
          tflint_version: latest

      - name: Run TFLint
        run: |
          tflint --init
          tflint -f compact

  plan:
    name: Plan
    runs-on: ubuntu-latest
    needs: validate
    if: github.event_name == 'pull_request'

    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform Init
        run: terraform init

      - name: Terraform Plan
        id: plan
        run: |
          terraform plan -no-color -out=tfplan
          terraform show -no-color tfplan > plan.txt

      - name: Comment PR
        uses: actions/github-script@v6
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          script: |
            const fs = require('fs');
            const plan = fs.readFileSync('plan.txt', 'utf8');
            const output = `#### Terraform Plan\n\`\`\`\n${plan}\n\`\`\``;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: output
            });

  apply:
    name: Apply
    runs-on: ubuntu-latest
    needs: validate
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production

    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform Init
        run: terraform init

      - name: Terraform Apply
        run: terraform apply -auto-approve
```

### GitLab CI

#### .gitlab-ci.yml
```yaml
image:
  name: hashicorp/terraform:1.5.0
  entrypoint: [""]

variables:
  TF_ROOT: ${CI_PROJECT_DIR}
  TF_STATE_NAME: default

cache:
  paths:
    - ${TF_ROOT}/.terraform

stages:
  - validate
  - plan
  - apply

before_script:
  - cd ${TF_ROOT}
  - terraform --version
  - terraform init

validate:
  stage: validate
  script:
    - terraform fmt -check -recursive
    - terraform validate

plan:
  stage: plan
  script:
    - terraform plan -out=tfplan
    - terraform show -json tfplan > tfplan.json
  artifacts:
    paths:
      - ${TF_ROOT}/tfplan
      - ${TF_ROOT}/tfplan.json
    expire_in: 1 week
  only:
    - merge_requests
    - main

apply:
  stage: apply
  script:
    - terraform apply -auto-approve tfplan
  dependencies:
    - plan
  only:
    - main
  when: manual
  environment:
    name: production
```

### Atlantis

#### atlantis.yaml
```yaml
version: 3

automerge: true
delete_source_branch_on_merge: true

projects:
  - name: production
    dir: environments/production
    workspace: production
    terraform_version: v1.5.0
    autoplan:
      when_modified:
        - "**/*.tf"
        - "**/*.tfvars"
      enabled: true
    apply_requirements:
      - approved
      - mergeable
    workflow: production

  - name: staging
    dir: environments/staging
    workspace: staging
    terraform_version: v1.5.0
    autoplan:
      when_modified:
        - "**/*.tf"
        - "**/*.tfvars"
      enabled: true
    workflow: staging

workflows:
  production:
    plan:
      steps:
        - init
        - plan:
            extra_args: ["-var-file=production.tfvars"]
    apply:
      steps:
        - apply

  staging:
    plan:
      steps:
        - init
        - plan:
            extra_args: ["-var-file=staging.tfvars"]
    apply:
      steps:
        - apply
```

### Terraform Cloud

#### CLI Configuration
```hcl
# main.tf

terraform {
  cloud {
    organization = "my-org"

    workspaces {
      name = "production"
    }
  }

  required_version = ">= 1.5.0"
}
```

#### Workspace Configuration (Terraform Cloud UI)
```
Workspace Settings:
  - Execution Mode: Remote
  - Terraform Version: 1.5.0
  - Apply Method: Manual
  - Auto Apply: Disabled (production)

Variables:
  - AWS_ACCESS_KEY_ID (sensitive)
  - AWS_SECRET_ACCESS_KEY (sensitive)
  - AWS_DEFAULT_REGION

Notifications:
  - Slack: #terraform-alerts
  - Email: ops@example.com

Run Triggers:
  - Workspace: network-infrastructure
```

---

## Security Best Practices

### Secrets Management

#### Never Hardcode Secrets
```hcl
# BAD - Hardcoded credentials
resource "aws_db_instance" "bad" {
  username = "admin"
  password = "Password123!"  # NEVER DO THIS
}

# GOOD - Use AWS Secrets Manager
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "production/database/password"
}

resource "aws_db_instance" "good" {
  username = "admin"
  password = jsondecode(data.aws_secretsmanager_secret_version.db_password.secret_string)["password"]
}

# GOOD - Use AWS Systems Manager Parameter Store
data "aws_ssm_parameter" "db_password" {
  name            = "/production/database/password"
  with_decryption = true
}

resource "aws_db_instance" "good" {
  username = "admin"
  password = data.aws_ssm_parameter.db_password.value
}
```

#### Generate Secrets with Terraform
```hcl
# Generate random password
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store in Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name = "production/database/password"

  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = jsonencode({
    username = "admin"
    password = random_password.db_password.result
  })
}

# Use in RDS
resource "aws_db_instance" "main" {
  username = jsondecode(aws_secretsmanager_secret_version.db_password.secret_string)["username"]
  password = jsondecode(aws_secretsmanager_secret_version.db_password.secret_string)["password"]
}
```

### IAM Best Practices

#### Least Privilege
```hcl
# BAD - Overly permissive
resource "aws_iam_role_policy" "bad" {
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

# GOOD - Specific permissions
resource "aws_iam_role_policy" "good" {
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.app_data.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.app_data.arn
      }
    ]
  })
}
```

#### Assume Role Policies
```hcl
# Service assume role
resource "aws_iam_role" "ecs_task" {
  name = "ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# Cross-account assume role
resource "aws_iam_role" "cross_account" {
  name = "cross-account-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = "arn:aws:iam::123456789012:root"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "sts:ExternalId" = "unique-external-id"
        }
      }
    }]
  })
}
```

### Encryption

#### S3 Encryption
```hcl
# Server-side encryption
resource "aws_s3_bucket" "encrypted" {
  bucket = "my-encrypted-bucket"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "encrypted" {
  bucket = aws_s3_bucket.encrypted.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "encrypted" {
  bucket = aws_s3_bucket.encrypted.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Require secure transport
resource "aws_s3_bucket_policy" "encrypted" {
  bucket = aws_s3_bucket.encrypted.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "DenyInsecureTransport"
      Effect = "Deny"
      Principal = "*"
      Action = "s3:*"
      Resource = [
        aws_s3_bucket.encrypted.arn,
        "${aws_s3_bucket.encrypted.arn}/*"
      ]
      Condition = {
        Bool = {
          "aws:SecureTransport" = "false"
        }
      }
    }]
  })
}
```

#### RDS Encryption
```hcl
resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_db_instance" "encrypted" {
  identifier = "encrypted-db"

  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"

  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn

  # Encrypted automated backups
  backup_retention_period = 7

  # Enable encryption in transit
  ca_cert_identifier = "rds-ca-rsa2048-g1"
}
```

### Network Security

#### Security Groups
```hcl
# Restrictive security groups
resource "aws_security_group" "web" {
  name        = "web-sg"
  description = "Security group for web servers"
  vpc_id      = aws_vpc.main.id

  # Allow HTTPS from ALB only
  ingress {
    description     = "HTTPS from ALB"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # No direct SSH access (use Session Manager)

  # Allow all outbound (could be more restrictive)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Database security group
resource "aws_security_group" "database" {
  name        = "database-sg"
  description = "Security group for database"
  vpc_id      = aws_vpc.main.id

  # Allow PostgreSQL from application tier only
  ingress {
    description     = "PostgreSQL from app tier"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  # No egress rules for database
}
```

#### VPC Flow Logs
```hcl
resource "aws_flow_log" "main" {
  iam_role_arn    = aws_iam_role.flow_logs.arn
  log_destination = aws_cloudwatch_log_group.flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id

  tags = {
    Name = "main-vpc-flow-logs"
  }
}

resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/aws/vpc/flow-logs"
  retention_in_days = 30
}

resource "aws_iam_role" "flow_logs" {
  name = "vpc-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "vpc-flow-logs.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "flow_logs" {
  role = aws_iam_role.flow_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ]
      Resource = "*"
    }]
  })
}
```

---

## Cost Optimization

### Resource Sizing

#### Right-sizing Instances
```hcl
locals {
  # Environment-based sizing
  instance_size = {
    dev     = "t3.micro"
    staging = "t3.small"
    prod    = "t3.large"
  }

  instance_type = local.instance_size[var.environment]
}

resource "aws_instance" "app" {
  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = local.instance_type

  # Enable detailed monitoring for production
  monitoring = var.environment == "prod"
}
```

#### Auto Scaling
```hcl
resource "aws_autoscaling_group" "app" {
  name                = "app-asg"
  vpc_zone_identifier = aws_subnet.private[*].id
  target_group_arns   = [aws_lb_target_group.app.arn]
  health_check_type   = "ELB"

  min_size         = var.environment == "prod" ? 3 : 1
  max_size         = var.environment == "prod" ? 10 : 3
  desired_capacity = var.environment == "prod" ? 3 : 1

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  # Scale down during off-hours
  dynamic "tag" {
    for_each = var.enable_scheduled_scaling ? [1] : []

    content {
      key                 = "Schedule"
      value               = "business-hours"
      propagate_at_launch = true
    }
  }
}

# Scheduled scaling
resource "aws_autoscaling_schedule" "scale_down" {
  count = var.enable_scheduled_scaling ? 1 : 0

  scheduled_action_name  = "scale-down"
  min_size               = 1
  max_size               = 3
  desired_capacity       = 1
  recurrence             = "0 20 * * MON-FRI"
  autoscaling_group_name = aws_autoscaling_group.app.name
}

resource "aws_autoscaling_schedule" "scale_up" {
  count = var.enable_scheduled_scaling ? 1 : 0

  scheduled_action_name  = "scale-up"
  min_size               = 3
  max_size               = 10
  desired_capacity       = 3
  recurrence             = "0 8 * * MON-FRI"
  autoscaling_group_name = aws_autoscaling_group.app.name
}
```

### Storage Optimization

#### S3 Lifecycle Policies
```hcl
resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "transition-old-objects"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 730
    }
  }

  rule {
    id     = "delete-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
```

#### EBS Volume Optimization
```hcl
resource "aws_ebs_volume" "data" {
  availability_zone = var.availability_zone

  # Use gp3 instead of gp2 for better price/performance
  type = "gp3"
  size = 100

  # Provision IOPS only if needed
  iops       = var.require_high_iops ? 3000 : null
  throughput = var.require_high_iops ? 125 : null

  encrypted  = true
  kms_key_id = aws_kms_key.ebs.arn

  tags = {
    Name        = "app-data"
    Environment = var.environment
  }
}

# Snapshot lifecycle
resource "aws_dlm_lifecycle_policy" "ebs_snapshots" {
  description        = "EBS snapshot lifecycle policy"
  execution_role_arn = aws_iam_role.dlm.arn
  state              = "ENABLED"

  policy_details {
    resource_types = ["VOLUME"]

    schedule {
      name = "daily-snapshots"

      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["03:00"]
      }

      retain_rule {
        count = 7
      }

      tags_to_add = {
        SnapshotCreator = "DLM"
      }

      copy_tags = true
    }

    target_tags = {
      Backup = "true"
    }
  }
}
```

### Reserved Instances

#### Tagging for RI Tracking
```hcl
locals {
  ri_tags = {
    RIType     = "standard"  # standard, convertible
    RITerm     = "1-year"    # 1-year, 3-year
    RIPayment  = "partial"   # no-upfront, partial, all-upfront
    CostCenter = var.cost_center
  }
}

resource "aws_instance" "app" {
  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = "t3.medium"

  tags = merge(
    local.common_tags,
    local.ri_tags,
    {
      Name = "app-server"
    }
  )
}
```

### Cost Monitoring

#### AWS Budgets
```hcl
resource "aws_budgets_budget" "monthly" {
  name              = "monthly-budget"
  budget_type       = "COST"
  limit_amount      = "1000"
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = "2024-01-01_00:00"

  cost_filter {
    name = "TagKeyValue"
    values = [
      "Environment$production"
    ]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = ["ops@example.com"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = ["ops@example.com", "finance@example.com"]
  }
}
```

#### Cost Allocation Tags
```hcl
# Enable cost allocation tags
resource "aws_ce_cost_allocation_tag" "environment" {
  tag_key = "Environment"
  status  = "Active"
}

resource "aws_ce_cost_allocation_tag" "project" {
  tag_key = "Project"
  status  = "Active"
}

resource "aws_ce_cost_allocation_tag" "cost_center" {
  tag_key = "CostCenter"
  status  = "Active"
}
```

---

## Common Anti-Patterns

### Anti-Pattern 1: Monolithic State Files

**Problem:**
```hcl
# Everything in one state file
# main.tf contains 1000+ resources
resource "aws_vpc" "main" { }
resource "aws_eks_cluster" "main" { }
resource "aws_rds_instance" "main" { }
# ... 997 more resources
```

**Solution:**
```
# Split into separate state files
terraform/
├── network/
│   └── main.tf         # VPC, subnets, etc.
├── compute/
│   └── main.tf         # EKS, EC2, etc.
└── database/
    └── main.tf         # RDS, DynamoDB, etc.
```

### Anti-Pattern 2: Hardcoded Values

**Problem:**
```hcl
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"  # Hardcoded
  instance_type = "t3.medium"               # Hardcoded
  subnet_id     = "subnet-12345"            # Hardcoded
}
```

**Solution:**
```hcl
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*"]
  }
}

resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = var.instance_type
  subnet_id     = aws_subnet.private[0].id
}
```

### Anti-Pattern 3: count When for_each is Better

**Problem:**
```hcl
# Removing middle element requires destroying and recreating
variable "subnets" {
  default = ["subnet-1", "subnet-2", "subnet-3"]
}

resource "aws_instance" "app" {
  count     = length(var.subnets)
  subnet_id = var.subnets[count.index]
}

# Removing "subnet-2" shifts all indices
# app[2] becomes app[1], causing recreation
```

**Solution:**
```hcl
variable "subnets" {
  default = {
    "az-a" = "subnet-1"
    "az-b" = "subnet-2"
    "az-c" = "subnet-3"
  }
}

resource "aws_instance" "app" {
  for_each  = var.subnets
  subnet_id = each.value
}

# Removing "az-b" only destroys app["az-b"]
```

### Anti-Pattern 4: Missing depends_on

**Problem:**
```hcl
# Race condition - IAM role may not be ready
resource "aws_iam_role" "lambda" {
  name = "lambda-role"
  # ...
}

resource "aws_iam_role_policy_attachment" "lambda" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "main" {
  role = aws_iam_role.lambda.arn
  # May execute before policy attachment
}
```

**Solution:**
```hcl
resource "aws_lambda_function" "main" {
  role = aws_iam_role.lambda.arn

  depends_on = [
    aws_iam_role_policy_attachment.lambda
  ]
}
```

### Anti-Pattern 5: Not Using Modules

**Problem:**
```hcl
# Duplicated code across environments
# dev/main.tf
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  # ... 50 lines of configuration
}

# staging/main.tf
resource "aws_vpc" "main" {
  cidr_block = "10.1.0.0/16"
  # ... same 50 lines
}

# production/main.tf
resource "aws_vpc" "main" {
  cidr_block = "10.2.0.0/16"
  # ... same 50 lines again
}
```

**Solution:**
```hcl
# modules/vpc/main.tf
# ... VPC module code

# dev/main.tf
module "vpc" {
  source     = "../modules/vpc"
  cidr_block = "10.0.0.0/16"
}

# staging/main.tf
module "vpc" {
  source     = "../modules/vpc"
  cidr_block = "10.1.0.0/16"
}
```

### Anti-Pattern 6: Overly Permissive Security

**Problem:**
```hcl
resource "aws_security_group" "bad" {
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]  # Open to world
  }
}

resource "aws_s3_bucket_policy" "bad" {
  policy = jsonencode({
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "*"
      Resource  = "*"
    }]
  })
}
```

**Solution:**
```hcl
resource "aws_security_group" "good" {
  ingress {
    description = "HTTPS from ALB"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
}

resource "aws_s3_bucket_policy" "good" {
  policy = jsonencode({
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = aws_iam_role.app.arn
      }
      Action = [
        "s3:GetObject",
        "s3:PutObject"
      ]
      Resource = "${aws_s3_bucket.app.arn}/*"
    }]
  })
}
```

---

## Multi-Environment Strategies

### Workspaces

#### Using Workspaces
```bash
# Create workspaces
terraform workspace new dev
terraform workspace new staging
terraform workspace new production

# List workspaces
terraform workspace list

# Switch workspace
terraform workspace select dev

# Current workspace
terraform workspace show
```

#### Workspace-aware Configuration
```hcl
locals {
  workspace_config = {
    dev = {
      instance_type = "t3.micro"
      instance_count = 1
      enable_monitoring = false
    }
    staging = {
      instance_type = "t3.small"
      instance_count = 2
      enable_monitoring = false
    }
    production = {
      instance_type = "t3.large"
      instance_count = 3
      enable_monitoring = true
    }
  }

  config = local.workspace_config[terraform.workspace]
}

resource "aws_instance" "app" {
  count = local.config.instance_count

  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = local.config.instance_type
  monitoring    = local.config.enable_monitoring

  tags = {
    Name        = "${terraform.workspace}-app-${count.index}"
    Environment = terraform.workspace
  }
}
```

#### Workspace State Storage
```hcl
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    # State files: dev/terraform.tfstate, staging/terraform.tfstate, production/terraform.tfstate
    key    = "${terraform.workspace}/terraform.tfstate"
    region = "us-east-1"
  }
}
```

### Separate State Files

#### Directory Structure
```
terraform/
├── modules/
│   ├── vpc/
│   ├── eks/
│   └── rds/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   ├── staging/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   └── production/
│       ├── main.tf
│       ├── variables.tf
│       ├── terraform.tfvars
│       └── backend.tf
└── README.md
```

#### Environment-specific Configuration
```hcl
# environments/production/main.tf

module "vpc" {
  source = "../../modules/vpc"

  name               = "production"
  cidr_block         = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
  enable_nat_gateway = true
  single_nat_gateway = false
}

module "eks" {
  source = "../../modules/eks"

  cluster_name    = "production-eks"
  cluster_version = "1.28"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnet_ids

  node_groups = {
    general = {
      desired_size   = 3
      min_size       = 3
      max_size       = 10
      instance_types = ["t3.large"]
    }
  }
}

# environments/production/backend.tf

terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
```

### Terragrunt

#### Directory Structure
```
terragrunt/
├── terragrunt.hcl          # Root configuration
├── modules/
│   ├── vpc/
│   ├── eks/
│   └── rds/
└── environments/
    ├── dev/
    │   ├── vpc/
    │   │   └── terragrunt.hcl
    │   ├── eks/
    │   │   └── terragrunt.hcl
    │   └── rds/
    │       └── terragrunt.hcl
    └── production/
        ├── vpc/
        │   └── terragrunt.hcl
        ├── eks/
        │   └── terragrunt.hcl
        └── rds/
            └── terragrunt.hcl
```

#### Root terragrunt.hcl
```hcl
# terragrunt.hcl

remote_state {
  backend = "s3"

  config = {
    bucket         = "my-terraform-state"
    key            = "${path_relative_to_include()}/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }

  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite_terragrunt"

  contents = <<EOF
provider "aws" {
  region = "${local.aws_region}"

  default_tags {
    tags = {
      Environment = "${local.environment}"
      ManagedBy   = "Terragrunt"
    }
  }
}
EOF
}

locals {
  environment = basename(dirname(get_terragrunt_dir()))
  aws_region  = "us-east-1"
}
```

#### Environment terragrunt.hcl
```hcl
# environments/production/vpc/terragrunt.hcl

include "root" {
  path = find_in_parent_folders()
}

terraform {
  source = "../../../modules/vpc"
}

inputs = {
  name               = "production"
  cidr_block         = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = false
}
```

#### Terragrunt Commands
```bash
# Run in single environment
cd environments/production/vpc
terragrunt init
terragrunt plan
terragrunt apply

# Run all modules in environment
cd environments/production
terragrunt run-all init
terragrunt run-all plan
terragrunt run-all apply

# With dependencies
terragrunt apply --terragrunt-include-dependencies
```

---

## Performance Optimization

### Parallelism

#### Adjust Parallelism
```bash
# Default parallelism: 10
terraform apply

# Increase for faster operations
terraform apply -parallelism=20

# Decrease to avoid rate limits
terraform apply -parallelism=5

# In CI/CD
export TF_CLI_ARGS_apply="-parallelism=20"
terraform apply
```

### Targeted Operations

#### Target Specific Resources
```bash
# Apply single resource
terraform apply -target=aws_instance.web

# Apply multiple resources
terraform apply \
  -target=aws_instance.web \
  -target=aws_security_group.web

# Apply module
terraform apply -target=module.vpc

# Destroy single resource
terraform destroy -target=aws_instance.web
```

### Refresh Optimization

#### Disable Refresh When Not Needed
```bash
# Skip refresh during plan
terraform plan -refresh=false

# Refresh only (no plan)
terraform apply -refresh-only

# Target refresh
terraform apply -refresh-only -target=aws_instance.web
```

### Provider Caching

#### Shared Plugin Cache
```bash
# Set plugin cache directory
export TF_PLUGIN_CACHE_DIR="$HOME/.terraform.d/plugin-cache"
mkdir -p $TF_PLUGIN_CACHE_DIR

# In .terraformrc
plugin_cache_dir = "$HOME/.terraform.d/plugin-cache"

# Disk space savings: Multiple projects share providers
```

---

## Disaster Recovery

### State File Recovery

#### Regular Backups
```bash
# Automated backup script
#!/bin/bash

BACKUP_DIR="./state-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Pull and backup state
terraform state pull > "$BACKUP_DIR/terraform.tfstate.$TIMESTAMP"

# Compress old backups
find $BACKUP_DIR -name "*.tfstate.*" -mtime +7 -exec gzip {} \;

# Delete old compressed backups
find $BACKUP_DIR -name "*.tfstate.*.gz" -mtime +30 -delete
```

#### S3 Versioning
```bash
# Enable versioning on state bucket
aws s3api put-bucket-versioning \
  --bucket my-terraform-state \
  --versioning-configuration Status=Enabled

# List versions
aws s3api list-object-versions \
  --bucket my-terraform-state \
  --prefix terraform.tfstate

# Restore previous version
aws s3api get-object \
  --bucket my-terraform-state \
  --key terraform.tfstate \
  --version-id <VERSION_ID> \
  terraform.tfstate.restored
```

### Import Existing Resources

#### Basic Import
```bash
# Import EC2 instance
terraform import aws_instance.web i-1234567890abcdef0

# Import S3 bucket
terraform import aws_s3_bucket.data my-bucket-name

# Import VPC
terraform import aws_vpc.main vpc-12345678

# Verify import
terraform plan
```

#### Bulk Import Script
```bash
#!/bin/bash

# Import multiple resources
while IFS=, read -r resource_address resource_id; do
  echo "Importing $resource_address with ID $resource_id"
  terraform import "$resource_address" "$resource_id"
done < resources.csv

# resources.csv format:
# aws_instance.web,i-1234567890abcdef0
# aws_s3_bucket.data,my-bucket-name
```

### State Corruption Recovery

#### Validate State
```bash
# Check state integrity
terraform state pull | jq . > /dev/null

if [ $? -eq 0 ]; then
  echo "State is valid JSON"
else
  echo "State is corrupted"
fi
```

#### Restore from Backup
```bash
# List available backups
aws s3api list-object-versions \
  --bucket my-terraform-state \
  --prefix terraform.tfstate

# Download backup
aws s3api get-object \
  --bucket my-terraform-state \
  --key terraform.tfstate \
  --version-id <GOOD_VERSION_ID> \
  terraform.tfstate.backup

# Push restored state
terraform state push terraform.tfstate.backup

# Verify
terraform plan
```

### Drift Detection

#### Detect Drift
```bash
# Detect drift without changes
terraform plan -detailed-exitcode -out=tfplan

# Exit codes:
# 0: No changes
# 1: Error
# 2: Changes detected (drift)

# Refresh to reconcile
terraform apply -refresh-only

# Or import drifted resources
terraform import aws_instance.drifted i-1234567890abcdef0
```

---

This comprehensive reference covers Terraform best practices from fundamentals to advanced topics. Use it as a guide for building maintainable, secure, and scalable infrastructure as code.
