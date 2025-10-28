# Terraform Secret Rotation Configuration
#
# Demonstrates:
# - Automated secret rotation with Terraform
# - AWS Secrets Manager rotation configuration
# - Lambda-based rotation function
# - IAM roles and permissions
# - CloudWatch monitoring and alerting
# - Multi-region deployment
#
# Prerequisites:
#   terraform >= 1.0
#   aws provider >= 4.0
#
# Usage:
#   terraform init
#   terraform plan
#   terraform apply

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "rotation_days" {
  description = "Automatic rotation interval (days)"
  type        = number
  default     = 90
}

# Database credentials secret
resource "aws_secretsmanager_secret" "database_credentials" {
  name                    = "${var.environment}/database/credentials"
  description             = "Database credentials with automatic rotation"
  recovery_window_in_days = 7

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Rotation    = "enabled"
  }
}

# Initial secret value
resource "aws_secretsmanager_secret_version" "database_credentials_initial" {
  secret_id = aws_secretsmanager_secret.database_credentials.id

  secret_string = jsonencode({
    username = "app_user"
    password = random_password.initial_db_password.result
    host     = aws_db_instance.main.endpoint
    port     = aws_db_instance.main.port
    database = aws_db_instance.main.name
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# Generate initial password
resource "random_password" "initial_db_password" {
  length  = 32
  special = true
}

# Lambda rotation function
data "archive_file" "rotation_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/rotation"
  output_path = "${path.module}/builds/rotation-lambda.zip"
}

resource "aws_lambda_function" "rotation" {
  filename         = data.archive_file.rotation_lambda.output_path
  function_name    = "${var.environment}-secret-rotation"
  role            = aws_iam_role.rotation_lambda.arn
  handler         = "handler.lambda_handler"
  source_code_hash = data.archive_file.rotation_lambda.output_base64sha256
  runtime         = "python3.11"
  timeout         = 300

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.rotation_lambda.id]
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Lambda IAM role
resource "aws_iam_role" "rotation_lambda" {
  name = "${var.environment}-rotation-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Lambda permissions policy
resource "aws_iam_role_policy" "rotation_lambda" {
  name = "${var.environment}-rotation-lambda-policy"
  role = aws_iam_role.rotation_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:DescribeSecret",
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:UpdateSecretVersionStage"
        ]
        Resource = aws_secretsmanager_secret.database_credentials.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      }
    ]
  })
}

# Allow Secrets Manager to invoke Lambda
resource "aws_lambda_permission" "secrets_manager" {
  statement_id  = "AllowSecretsManagerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rotation.function_name
  principal     = "secretsmanager.amazonaws.com"
  source_arn    = aws_secretsmanager_secret.database_credentials.arn
}

# Enable automatic rotation
resource "aws_secretsmanager_secret_rotation" "database_credentials" {
  secret_id           = aws_secretsmanager_secret.database_credentials.id
  rotation_lambda_arn = aws_lambda_function.rotation.arn

  rotation_rules {
    automatically_after_days = var.rotation_days
  }

  depends_on = [aws_lambda_permission.secrets_manager]
}

# CloudWatch log group for rotation Lambda
resource "aws_cloudwatch_log_group" "rotation_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.rotation.function_name}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# CloudWatch alarm for rotation failures
resource "aws_cloudwatch_metric_alarm" "rotation_failures" {
  alarm_name          = "${var.environment}-rotation-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alert on secret rotation failures"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.rotation.function_name
  }

  alarm_actions = [aws_sns_topic.rotation_alerts.arn]

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# SNS topic for rotation alerts
resource "aws_sns_topic" "rotation_alerts" {
  name = "${var.environment}-rotation-alerts"

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_sns_topic_subscription" "rotation_alerts_email" {
  topic_arn = aws_sns_topic.rotation_alerts.arn
  protocol  = "email"
  endpoint  = "security-team@example.com"
}

# Security group for rotation Lambda
resource "aws_security_group" "rotation_lambda" {
  name        = "${var.environment}-rotation-lambda"
  description = "Security group for rotation Lambda function"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# RDS database instance
resource "aws_db_instance" "main" {
  identifier           = "${var.environment}-database"
  engine              = "postgres"
  engine_version      = "15.3"
  instance_class      = "db.t3.medium"
  allocated_storage   = 100
  storage_encrypted   = true

  db_name  = "myapp"
  username = "app_user"
  password = random_password.initial_db_password.result

  vpc_security_group_ids = [aws_security_group.database.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  skip_final_snapshot    = false
  final_snapshot_identifier = "${var.environment}-db-final-snapshot"

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Database security group
resource "aws_security_group" "database" {
  name        = "${var.environment}-database"
  description = "Security group for database"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow from rotation Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.rotation_lambda.id]
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# VPC resources (simplified)
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.environment}-vpc"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "${var.environment}-private-${count.index + 1}"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.environment}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

# Outputs
output "secret_arn" {
  description = "ARN of the secret"
  value       = aws_secretsmanager_secret.database_credentials.arn
}

output "rotation_lambda_arn" {
  description = "ARN of the rotation Lambda function"
  value       = aws_lambda_function.rotation.arn
}

output "rotation_enabled" {
  description = "Whether automatic rotation is enabled"
  value       = aws_secretsmanager_secret_rotation.database_credentials.rotation_enabled
}

output "rotation_interval_days" {
  description = "Rotation interval in days"
  value       = var.rotation_days
}

output "database_endpoint" {
  description = "Database endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

# Example: Application ECS task using rotated secret
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.environment}-app"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
  cpu                     = 256
  memory                  = 512

  container_definitions = jsonencode([
    {
      name  = "app"
      image = "example/app:latest"

      secrets = [
        {
          name      = "DB_USERNAME"
          valueFrom = "${aws_secretsmanager_secret.database_credentials.arn}:username::"
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.database_credentials.arn}:password::"
        },
        {
          name      = "DB_HOST"
          valueFrom = "${aws_secretsmanager_secret.database_credentials.arn}:host::"
        },
        {
          name      = "DB_PORT"
          valueFrom = "${aws_secretsmanager_secret.database_credentials.arn}:port::"
        },
        {
          name      = "DB_DATABASE"
          valueFrom = "${aws_secretsmanager_secret.database_credentials.arn}:database::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/${var.environment}/app"
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "app"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
