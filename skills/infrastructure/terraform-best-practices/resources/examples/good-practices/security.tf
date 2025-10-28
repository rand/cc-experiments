# Good Security Practices
#
# This file demonstrates secure Terraform configurations

# 1. Encrypted S3 Bucket with Versioning and Lifecycle
resource "aws_s3_bucket" "secure_data" {
  bucket = "mycompany-secure-data-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "secure-data-bucket"
    Environment = "production"
    Compliance  = "required"
  }
}

resource "aws_s3_bucket_versioning" "secure_data" {
  bucket = aws_s3_bucket.secure_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "secure_data" {
  bucket = aws_s3_bucket.secure_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "secure_data" {
  bucket = aws_s3_bucket.secure_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "secure_data" {
  bucket = aws_s3_bucket.secure_data.id

  rule {
    id     = "transition-old-versions"
    status = "Enabled"

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}

# KMS Key for Encryption
resource "aws_kms_key" "s3" {
  description             = "KMS key for S3 bucket encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name        = "s3-encryption-key"
    Environment = "production"
  }
}

resource "aws_kms_alias" "s3" {
  name          = "alias/s3-encryption"
  target_key_id = aws_kms_key.s3.key_id
}

# 2. Secure RDS Instance
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "production/database/master-password"
}

resource "aws_db_instance" "secure" {
  identifier = "secure-database"

  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"

  allocated_storage = 100
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn

  # Use Secrets Manager for password
  username = "dbadmin"
  password = jsondecode(data.aws_secretsmanager_secret_version.db_password.secret_string)["password"]

  # Network security
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false

  # Backup and maintenance
  backup_retention_period = 30
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval             = 60
  monitoring_role_arn             = aws_iam_role.rds_monitoring.arn

  # Additional security
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "secure-database-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  tags = {
    Name        = "secure-database"
    Environment = "production"
  }
}

resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name        = "rds-encryption-key"
    Environment = "production"
  }
}

# 3. Restrictive Security Group
resource "aws_security_group" "app_restrictive" {
  name        = "app-restrictive-sg"
  description = "Restrictive security group for application"
  vpc_id      = data.aws_vpc.main.id

  tags = {
    Name        = "app-restrictive-sg"
    Environment = "production"
  }
}

# Define rules separately for better management
resource "aws_security_group_rule" "app_https_from_alb" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  description              = "HTTPS from ALB"

  security_group_id = aws_security_group.app_restrictive.id
}

resource "aws_security_group_rule" "app_egress_https" {
  type        = "egress"
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
  description = "HTTPS to internet for API calls"

  security_group_id = aws_security_group.app_restrictive.id
}

resource "aws_security_group_rule" "app_egress_db" {
  type                     = "egress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.database.id
  description              = "PostgreSQL to database"

  security_group_id = aws_security_group.app_restrictive.id
}

# 4. IAM Role with Least Privilege
resource "aws_iam_role" "app_least_privilege" {
  name = "app-least-privilege-role"

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

  tags = {
    Name        = "app-least-privilege-role"
    Environment = "production"
  }
}

# Specific permissions only
resource "aws_iam_role_policy" "app_s3_access" {
  name = "s3-access"
  role = aws_iam_role.app_least_privilege.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.secure_data.arn}/app-data/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.secure_data.arn
        Condition = {
          StringLike = {
            "s3:prefix" = ["app-data/*"]
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "app_secrets_access" {
  name = "secrets-access"
  role = aws_iam_role.app_least_privilege.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue"
      ]
      Resource = [
        "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:production/app/*"
      ]
    }]
  })
}

# 5. VPC Flow Logs for Network Monitoring
resource "aws_flow_log" "main" {
  iam_role_arn    = aws_iam_role.flow_logs.arn
  log_destination = aws_cloudwatch_log_group.flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = data.aws_vpc.main.id

  tags = {
    Name        = "vpc-flow-logs"
    Environment = "production"
  }
}

resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/aws/vpc/flow-logs"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = {
    Name        = "vpc-flow-logs"
    Environment = "production"
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_vpc" "main" {
  id = var.vpc_id
}
