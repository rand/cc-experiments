# Anti-Patterns and Bad Practices
#
# This file demonstrates what NOT to do in Terraform
# Each bad example is commented with the issue and how to fix it

# ❌ BAD: Hardcoded credentials
resource "aws_db_instance" "bad_credentials" {
  identifier = "bad-database"

  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"

  username = "admin"                    # BAD: Hardcoded username
  password = "SuperSecret123!"          # CRITICAL: Hardcoded password in code!

  # Issue: Credentials visible in code, state, and version control
  # Fix: Use AWS Secrets Manager or SSM Parameter Store
  #
  # data "aws_secretsmanager_secret_version" "db_password" {
  #   secret_id = "production/database/password"
  # }
  # password = jsondecode(data.aws_secretsmanager_secret_version.db_password.secret_string)["password"]
}

# ❌ BAD: Unencrypted S3 bucket
resource "aws_s3_bucket" "bad_no_encryption" {
  bucket = "my-unencrypted-bucket"

  # Issue: No encryption, no versioning, no public access block
  # Fix: Add encryption, versioning, and block public access
  #
  # resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  #   bucket = aws_s3_bucket.this.id
  #   rule {
  #     apply_server_side_encryption_by_default {
  #       sse_algorithm = "aws:kms"
  #     }
  #   }
  # }
}

# ❌ BAD: Publicly accessible database
resource "aws_db_instance" "bad_public" {
  identifier = "public-database"

  engine         = "postgres"
  instance_class = "db.t3.medium"

  publicly_accessible = true  # CRITICAL: Database exposed to internet!

  # Issue: Security risk - database accessible from anywhere
  # Fix: Set publicly_accessible = false and use VPN/bastion
}

# ❌ BAD: Overly permissive security group
resource "aws_security_group" "bad_wide_open" {
  name        = "bad-wide-open-sg"
  description = "Wide open security group"
  vpc_id      = var.vpc_id

  ingress {
    description = "All traffic from anywhere"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]  # CRITICAL: Open to the world!
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Issue: Allows all traffic from anywhere
  # Fix: Restrict to specific ports and sources
  #
  # ingress {
  #   description     = "HTTPS from ALB"
  #   from_port       = 443
  #   to_port         = 443
  #   protocol        = "tcp"
  #   security_groups = [aws_security_group.alb.id]
  # }
}

# ❌ BAD: Overly permissive IAM policy
resource "aws_iam_role_policy" "bad_admin" {
  name = "admin-policy"
  role = aws_iam_role.bad_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"           # CRITICAL: All actions allowed!
      Resource = "*"           # CRITICAL: On all resources!
    }]
  })

  # Issue: Violates least privilege principle
  # Fix: Specify only required actions and resources
  #
  # Statement = [{
  #   Effect = "Allow"
  #   Action = [
  #     "s3:GetObject",
  #     "s3:PutObject"
  #   ]
  #   Resource = "arn:aws:s3:::specific-bucket/*"
  # }]
}

# ❌ BAD: Hardcoded values instead of data sources
resource "aws_instance" "bad_hardcoded" {
  ami           = "ami-0c55b159cbfafe1f0"  # BAD: Hardcoded AMI ID
  instance_type = "t3.medium"
  subnet_id     = "subnet-12345678"        # BAD: Hardcoded subnet ID

  # Issue: AMI IDs vary by region, subnet may not exist
  # Fix: Use data sources
  #
  # data "aws_ami" "ubuntu" {
  #   most_recent = true
  #   owners      = ["099720109477"]
  #   filter {
  #     name   = "name"
  #     values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  #   }
  # }
  # ami       = data.aws_ami.ubuntu.id
  # subnet_id = data.aws_subnet.private.id
}

# ❌ BAD: Using count instead of for_each
variable "bad_subnet_list" {
  default = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

resource "aws_subnet" "bad_count" {
  count = length(var.bad_subnet_list)

  vpc_id     = var.vpc_id
  cidr_block = var.bad_subnet_list[count.index]

  # Issue: Removing middle element shifts indices, causing recreations
  # Fix: Use for_each with map
  #
  # variable "subnets" {
  #   default = {
  #     "private-a" = "10.0.1.0/24"
  #     "private-b" = "10.0.2.0/24"
  #     "private-c" = "10.0.3.0/24"
  #   }
  # }
  #
  # resource "aws_subnet" "good" {
  #   for_each   = var.subnets
  #   vpc_id     = var.vpc_id
  #   cidr_block = each.value
  # }
}

# ❌ BAD: No tags
resource "aws_instance" "bad_no_tags" {
  ami           = var.ami_id
  instance_type = "t3.medium"

  # Issue: No tags for cost tracking or resource management
  # Fix: Add comprehensive tags
  #
  # tags = {
  #   Name        = "app-server"
  #   Environment = "production"
  #   ManagedBy   = "Terraform"
  #   CostCenter  = "engineering"
  #   Owner       = "team@example.com"
  # }
}

# ❌ BAD: Inline policy instead of managed policy
resource "aws_iam_user" "bad_inline_policy" {
  name = "app-user"

  # Inline policy directly on user
  inline_policy {
    name = "s3-access"

    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Effect   = "Allow"
        Action   = "s3:*"
        Resource = "*"
      }]
    })
  }

  # Issue: Hard to manage, not reusable, overly permissive
  # Fix: Use separate policy resource with specific permissions
  #
  # resource "aws_iam_policy" "s3_access" {
  #   name = "s3-specific-access"
  #   policy = jsonencode({...})
  # }
  # resource "aws_iam_user_policy_attachment" "this" {
  #   user       = aws_iam_user.this.name
  #   policy_arn = aws_iam_policy.s3_access.arn
  # }
}

# ❌ BAD: No backend configuration
# terraform {
#   # No backend block - using local state
# }
#
# Issue: State stored locally, no locking, no collaboration
# Fix: Configure remote backend
#
# terraform {
#   backend "s3" {
#     bucket         = "terraform-state"
#     key            = "production/terraform.tfstate"
#     region         = "us-east-1"
#     encrypt        = true
#     dynamodb_table = "terraform-locks"
#   }
# }

# ❌ BAD: No provider version constraints
# provider "aws" {
#   region = "us-east-1"
#   # No version specified
# }
#
# Issue: Provider may auto-upgrade and break configuration
# Fix: Pin provider versions
#
# terraform {
#   required_providers {
#     aws = {
#       source  = "hashicorp/aws"
#       version = "~> 5.0"
#     }
#   }
# }

# ❌ BAD: Single character resource names
resource "aws_vpc" "v" {  # BAD: Unclear name
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "s" {  # BAD: Unclear name
  vpc_id     = aws_vpc.v.id
  cidr_block = "10.0.1.0/24"
}

# Issue: Unclear what resources are for
# Fix: Use descriptive names
#
# resource "aws_vpc" "main" {
#   cidr_block = "10.0.0.0/16"
# }
#
# resource "aws_subnet" "private_app" {
#   vpc_id     = aws_vpc.main.id
#   cidr_block = "10.0.1.0/24"
# }

# ❌ BAD: No validation on variables
variable "bad_no_validation" {
  type    = string
  default = "10.0.0.0/16"

  # Issue: No validation - could accept invalid CIDR
  # Fix: Add validation
  #
  # validation {
  #   condition     = can(cidrhost(var.cidr_block, 0))
  #   error_message = "Must be valid IPv4 CIDR."
  # }
}

# ❌ BAD: RDS without encryption at rest
resource "aws_db_instance" "bad_no_encryption" {
  identifier = "unencrypted-db"

  engine         = "postgres"
  instance_class = "db.t3.medium"

  storage_encrypted = false  # BAD: No encryption

  # Issue: Data at rest not encrypted
  # Fix: Enable encryption
  #
  # storage_encrypted = true
  # kms_key_id        = aws_kms_key.rds.arn
}

# ❌ BAD: No backup retention
resource "aws_db_instance" "bad_no_backups" {
  identifier = "no-backups-db"

  engine         = "postgres"
  instance_class = "db.t3.medium"

  backup_retention_period = 0  # BAD: No backups!

  # Issue: No automated backups, data loss risk
  # Fix: Enable backups
  #
  # backup_retention_period = 30
  # backup_window           = "03:00-04:00"
}

# ❌ BAD: Large monolithic configuration
# Issue: Everything in one file becomes unmaintainable
# Fix: Split into logical files
#
# network.tf       - VPC, subnets, routing
# security.tf      - Security groups, NACLs
# compute.tf       - EC2, ASG, Launch Templates
# database.tf      - RDS, DynamoDB
# monitoring.tf    - CloudWatch, alarms

# ❌ BAD: No lifecycle rules
resource "aws_instance" "bad_no_lifecycle" {
  ami           = var.ami_id
  instance_type = "t3.medium"

  # Issue: Changing AMI destroys and recreates instance
  # Fix: Use create_before_destroy
  #
  # lifecycle {
  #   create_before_destroy = true
  # }
}

# Helper resources for examples
resource "aws_iam_role" "bad_role" {
  name = "bad-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}
