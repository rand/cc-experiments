---
name: infrastructure-terraform-patterns
description: Provisioning cloud infrastructure (AWS, GCP, Azure, Cloudflare)
---


# Terraform Patterns

**Scope**: Infrastructure as Code with Terraform - modules, state management, workspaces, backends
**Lines**: 387
**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

**Activate when**:
- Provisioning cloud infrastructure (AWS, GCP, Azure, Cloudflare)
- Managing infrastructure state across environments
- Creating reusable infrastructure modules
- Implementing infrastructure as code workflows
- Managing multi-environment deployments
- Migrating from manual infrastructure management

**Prerequisites**:
- Terraform CLI installed (`brew install terraform` or download from terraform.io)
- Cloud provider credentials configured
- Basic understanding of target cloud platform
- Version control system (Git) for state tracking

**Common scenarios**:
- Setting up staging/production environments
- Creating repeatable infrastructure patterns
- Managing infrastructure across multiple regions
- Implementing infrastructure versioning and rollback
- Collaborating on infrastructure changes with teams

---

## Core Concepts

### 1. Provider Configuration

```hcl
# versions.tf
terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Project     = var.project_name
    }
  }
}
```

### 2. Variable Definitions

```hcl
# variables.tf
variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production"
  }
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "instance_config" {
  description = "EC2 instance configuration"
  type = object({
    instance_type = string
    volume_size   = number
    enable_monitoring = bool
  })
  default = {
    instance_type     = "t3.micro"
    volume_size       = 20
    enable_monitoring = false
  }
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
```

### 3. State Management

```hcl
# Remote state with S3 backend
terraform {
  backend "s3" {
    bucket         = "company-terraform-state"
    key            = "env/${var.environment}/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"

    # Enable versioning for state file recovery
    versioning = true
  }
}

# State locking with DynamoDB
resource "aws_dynamodb_table" "terraform_lock" {
  name         = "terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name = "Terraform State Lock"
  }
}
```

### 4. Data Sources

```hcl
# Fetch existing resources
data "aws_vpc" "main" {
  id = var.vpc_id
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }

  tags = {
    Tier = "private"
  }
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# Remote state data source
data "terraform_remote_state" "networking" {
  backend = "s3"

  config = {
    bucket = "company-terraform-state"
    key    = "networking/terraform.tfstate"
    region = "us-east-1"
  }
}
```

---

## Patterns

### Module Structure

```hcl
# modules/web-app/main.tf
resource "aws_security_group" "web" {
  name        = "${var.name}-web-sg"
  description = "Security group for ${var.name} web tier"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.name}-web-sg"
    }
  )
}

resource "aws_lb" "web" {
  name               = "${var.name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.web.id]
  subnets            = var.subnet_ids

  enable_deletion_protection = var.environment == "production"

  tags = merge(
    var.tags,
    {
      Name = "${var.name}-alb"
    }
  )
}

# modules/web-app/variables.tf
variable "name" {
  description = "Application name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for load balancer"
  type        = list(string)
}

variable "allowed_cidrs" {
  description = "Allowed CIDR blocks for ingress"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}

# modules/web-app/outputs.tf
output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.web.dns_name
}

output "alb_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.web.arn
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.web.id
}
```

### Using Modules

```hcl
# main.tf
module "web_app" {
  source = "./modules/web-app"

  name        = "my-app"
  environment = var.environment
  vpc_id      = data.aws_vpc.main.id
  subnet_ids  = data.aws_subnets.public.ids

  allowed_cidrs = var.environment == "production" ? var.allowed_cidrs : ["0.0.0.0/0"]

  tags = {
    Team  = "Platform"
    Owner = "DevOps"
  }
}

# Use module outputs
resource "aws_route53_record" "web" {
  zone_id = var.route53_zone_id
  name    = "app.${var.domain}"
  type    = "A"

  alias {
    name                   = module.web_app.alb_dns_name
    zone_id                = module.web_app.alb_zone_id
    evaluate_target_health = true
  }
}
```

### Workspace Management

```bash
# Create workspaces for environments
terraform workspace new dev
terraform workspace new staging
terraform workspace new production

# Switch between workspaces
terraform workspace select dev

# List workspaces
terraform workspace list

# Use workspace in configuration
locals {
  environment = terraform.workspace

  instance_counts = {
    dev        = 1
    staging    = 2
    production = 5
  }

  instance_count = local.instance_counts[terraform.workspace]
}

resource "aws_instance" "app" {
  count         = local.instance_count
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type

  tags = {
    Name        = "${terraform.workspace}-app-${count.index + 1}"
    Environment = terraform.workspace
  }
}
```

### Dynamic Blocks

```hcl
# Dynamic ingress rules
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
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTPS"
    },
    {
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTP"
    }
  ]
}

resource "aws_security_group" "dynamic" {
  name        = "dynamic-sg"
  description = "Security group with dynamic rules"
  vpc_id      = var.vpc_id

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
```

### For Each Patterns

```hcl
# Create resources from map
variable "s3_buckets" {
  type = map(object({
    versioning = bool
    encryption = bool
  }))
  default = {
    "logs" = {
      versioning = true
      encryption = true
    }
    "backups" = {
      versioning = true
      encryption = true
    }
    "assets" = {
      versioning = false
      encryption = false
    }
  }
}

resource "aws_s3_bucket" "buckets" {
  for_each = var.s3_buckets

  bucket = "${var.project}-${each.key}-${var.environment}"

  tags = {
    Name = each.key
    Type = each.key
  }
}

resource "aws_s3_bucket_versioning" "buckets" {
  for_each = {
    for k, v in var.s3_buckets : k => v if v.versioning
  }

  bucket = aws_s3_bucket.buckets[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}
```

### Conditional Resources

```hcl
# Create resource only in production
resource "aws_cloudwatch_dashboard" "main" {
  count          = var.environment == "production" ? 1 : 0
  dashboard_name = "${var.project}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations"]
          ]
        }
      }
    ]
  })
}

# Conditional values
locals {
  instance_type = var.environment == "production" ? "t3.large" : "t3.micro"

  backup_retention = {
    dev        = 7
    staging    = 14
    production = 30
  }[var.environment]
}
```

---

## Quick Reference

### Essential Commands

```bash
# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Format configuration
terraform fmt -recursive

# Plan changes
terraform plan -out=tfplan

# Apply changes
terraform apply tfplan

# Destroy infrastructure
terraform destroy

# Show current state
terraform show

# List resources in state
terraform state list

# Remove resource from state
terraform state rm aws_instance.example

# Import existing resource
terraform import aws_instance.example i-1234567890abcdef0

# Refresh state
terraform refresh

# Output values
terraform output
terraform output -json
```

### State Management

```bash
# Pull remote state
terraform state pull > terraform.tfstate.backup

# Push local state to remote
terraform state push terraform.tfstate

# Move resource in state
terraform state mv aws_instance.old aws_instance.new

# Replace provider in state
terraform state replace-provider hashicorp/aws registry.terraform.io/hashicorp/aws
```

### Workspace Commands

```bash
# Create workspace
terraform workspace new staging

# Select workspace
terraform workspace select production

# List workspaces
terraform workspace list

# Show current workspace
terraform workspace show

# Delete workspace
terraform workspace delete dev
```

### Module Commands

```bash
# Initialize and download modules
terraform init

# Update modules
terraform get -update

# Show module tree
terraform providers
```

---

## Anti-Patterns

### Critical Violations

```hcl
# ❌ NEVER: Hardcode credentials
provider "aws" {
  access_key = "AKIAIOSFODNN7EXAMPLE"  # NEVER do this
  secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}

# ✅ CORRECT: Use environment variables or instance profiles
provider "aws" {
  # Uses AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
  region = var.aws_region
}
```

```hcl
# ❌ NEVER: Store state locally for team projects
terraform {
  # No backend configuration - uses local state
}

# ✅ CORRECT: Use remote backend with locking
terraform {
  backend "s3" {
    bucket         = "terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}
```

```hcl
# ❌ NEVER: Use count for resources that might be reordered
resource "aws_instance" "app" {
  count = 3  # Risky - reordering changes indices
  # ...
}

# ✅ CORRECT: Use for_each with stable keys
resource "aws_instance" "app" {
  for_each = toset(["web-1", "web-2", "web-3"])

  tags = {
    Name = each.key
  }
}
```

### Common Mistakes

```hcl
# ❌ Don't ignore .terraform directory in git
# .gitignore missing .terraform/

# ✅ CORRECT: Proper .gitignore
# .gitignore
.terraform/
*.tfstate
*.tfstate.backup
.terraform.lock.hcl  # or commit for version locking
tfplan
```

```hcl
# ❌ Don't create circular dependencies
resource "aws_security_group" "a" {
  ingress {
    security_groups = [aws_security_group.b.id]
  }
}

resource "aws_security_group" "b" {
  ingress {
    security_groups = [aws_security_group.a.id]
  }
}

# ✅ CORRECT: Use separate rules
resource "aws_security_group_rule" "a_to_b" {
  type                     = "ingress"
  security_group_id        = aws_security_group.b.id
  source_security_group_id = aws_security_group.a.id
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
}
```

### Best Practices

```hcl
# Use consistent naming
locals {
  name_prefix = "${var.project}-${var.environment}"

  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "Terraform"
    Timestamp   = timestamp()
  }
}

# Version pin providers
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"  # Allow minor updates only
    }
  }
}

# Use lifecycle rules for safety
resource "aws_db_instance" "main" {
  # ...

  lifecycle {
    prevent_destroy = true  # Prevent accidental deletion
    create_before_destroy = true  # Zero-downtime updates
    ignore_changes = [
      tags["LastModified"]  # Ignore external changes
    ]
  }
}
```

---

## Level 3: Resources

**Location**: `/Users/rand/src/cc-polymath/skills/infrastructure/terraform-best-practices/resources/`

### Comprehensive Reference

**`REFERENCE.md`** (1,875 lines)
- Complete Terraform best practices guide
- State management strategies and troubleshooting
- Module design patterns and composition
- Variable management and validation
- Security best practices and encryption
- Cost optimization techniques
- CI/CD integration patterns
- Multi-environment strategies
- Performance optimization
- Disaster recovery procedures

### Executable Scripts

**`scripts/analyze_terraform.py`** - Terraform code analyzer
- Detects security vulnerabilities and anti-patterns
- Checks for hardcoded secrets, unencrypted resources
- Validates naming conventions and tagging
- Identifies overly permissive IAM policies and security groups
- Suggests improvements and best practices
- Supports JSON and table output formats

```bash
./analyze_terraform.py .
./analyze_terraform.py --json --output report.json terraform/
./analyze_terraform.py --severity high --format table .
```

**`scripts/validate_state.py`** - State file health checker
- Validates state file integrity and structure
- Detects orphaned resources and duplicates
- Checks for circular dependencies
- Analyzes state lineage and serial numbers
- Identifies sensitive data exposure
- Optionally checks for infrastructure drift

```bash
./validate_state.py
./validate_state.py --remote --json
./validate_state.py --check-drift --output state-report.json
```

**`scripts/cost_estimate.sh`** - Infrastructure cost estimator
- Estimates monthly costs from Terraform plans
- Integrates with Infracost for accurate pricing
- Provides cost breakdowns by resource type
- Compares costs across environments
- Supports budget limits and threshold alerts
- Outputs in table, JSON, or CSV formats

```bash
./cost_estimate.sh
./cost_estimate.sh --json --output costs.json
./cost_estimate.sh --budget 5000 --threshold 80
./cost_estimate.sh --compare production-costs.json
```

### Production Examples

**Reusable Modules**:
- `examples/modules/vpc/` - Production-ready VPC with multi-AZ, NAT gateways, flow logs
- `examples/modules/eks/` - EKS cluster with node groups and IRSA
- `examples/modules/rds/` - RDS with encryption, backups, monitoring

**Environment Configurations**:
- `examples/environments/dev/` - Development environment (cost-optimized)
- `examples/environments/prod/` - Production environment (HA, redundant)

**Best Practices Examples**:
- `examples/good-practices/security.tf` - Encryption, least privilege IAM, secure networking
- `examples/bad-practices/anti-patterns.tf` - Common mistakes with explanations and fixes

### Usage

1. **Code Quality Analysis**:
   ```bash
   cd /path/to/terraform/project
   /path/to/analyze_terraform.py . --severity high
   ```

2. **State Validation**:
   ```bash
   cd /path/to/terraform/project
   /path/to/validate_state.py --check-drift
   ```

3. **Cost Estimation**:
   ```bash
   cd /path/to/terraform/project
   /path/to/cost_estimate.sh --budget 10000 --json
   ```

4. **Module Reuse**:
   ```hcl
   module "vpc" {
     source = "/path/to/terraform-best-practices/resources/examples/modules/vpc"

     name               = "production"
     cidr_block         = "10.0.0.0/16"
     availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
   }
   ```

All scripts support `--help` for detailed usage information.

---

## Related Skills

**Infrastructure**:
- `aws-serverless.md` - AWS Lambda, API Gateway, DynamoDB integration
- `kubernetes-basics.md` - Container orchestration with Terraform Kubernetes provider
- `infrastructure-security.md` - IAM roles, security groups, secrets management
- `cost-optimization.md` - Resource sizing, reserved instances

**Development**:
- `modal-functions-basics.md` - Alternative serverless platform
- `cloudflare-workers.md` - Edge computing with Terraform Cloudflare provider

**Standards from CLAUDE.md**:
- Use Terraform for infrastructure as code
- Remote state with S3 backend mandatory for team projects
- Version pin all providers
- Tag all resources consistently
- Enable state locking with DynamoDB

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
