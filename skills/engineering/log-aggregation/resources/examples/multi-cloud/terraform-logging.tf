# Multi-Cloud Log Aggregation with Terraform
# Configures centralized logging across AWS, GCP, and Azure
#
# Apply:
#   terraform init
#   terraform plan
#   terraform apply

# ============================================================================
# VARIABLES
# ============================================================================

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "log_retention_days" {
  description = "Log retention period in days"
  type        = number
  default     = 30
}

variable "elasticsearch_endpoint" {
  description = "Centralized Elasticsearch endpoint"
  type        = string
}

# ============================================================================
# AWS CloudWatch Logs
# ============================================================================

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/application/${var.environment}"
  retention_in_days = var.log_retention_days

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# CloudWatch Logs Subscription Filter to Lambda
resource "aws_cloudwatch_log_subscription_filter" "log_forwarder" {
  name            = "${var.environment}-log-forwarder"
  log_group_name  = aws_cloudwatch_log_group.app_logs.name
  filter_pattern  = ""  # Forward all logs
  destination_arn = aws_lambda_function.log_forwarder.arn

  depends_on = [aws_lambda_permission.allow_cloudwatch]
}

# Lambda function to forward logs to Elasticsearch
resource "aws_lambda_function" "log_forwarder" {
  filename      = "log_forwarder.zip"
  function_name = "${var.environment}-log-forwarder"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 60

  environment {
    variables = {
      ELASTICSEARCH_ENDPOINT = var.elasticsearch_endpoint
      ENVIRONMENT            = var.environment
    }
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "${var.environment}-lambda-log-forwarder"

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

# Lambda CloudWatch Logs policy
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Permission for CloudWatch to invoke Lambda
resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.log_forwarder.function_name
  principal     = "logs.amazonaws.com"
  source_arn    = "${aws_cloudwatch_log_group.app_logs.arn}:*"
}

# S3 bucket for log archive
resource "aws_s3_bucket" "log_archive" {
  bucket = "${var.environment}-log-archive"

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# S3 bucket lifecycle policy
resource "aws_s3_bucket_lifecycle_configuration" "log_archive" {
  bucket = aws_s3_bucket.log_archive.id

  rule {
    id     = "archive-old-logs"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = 90
    }
  }
}

# ============================================================================
# GCP Cloud Logging
# ============================================================================

# GCP Log Sink to Pub/Sub
resource "google_logging_project_sink" "log_sink" {
  name        = "${var.environment}-log-sink"
  destination = "pubsub.googleapis.com/${google_pubsub_topic.logs.id}"

  filter = "resource.type=gce_instance OR resource.type=k8s_container"

  unique_writer_identity = true
}

# Pub/Sub topic for logs
resource "google_pubsub_topic" "logs" {
  name = "${var.environment}-logs"

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

# Pub/Sub subscription
resource "google_pubsub_subscription" "logs" {
  name  = "${var.environment}-logs-subscription"
  topic = google_pubsub_topic.logs.name

  ack_deadline_seconds = 20

  push_config {
    push_endpoint = var.elasticsearch_endpoint

    attributes = {
      x-goog-version = "v1"
    }
  }
}

# IAM binding for log sink
resource "google_pubsub_topic_iam_binding" "log_sink_writer" {
  topic = google_pubsub_topic.logs.name
  role  = "roles/pubsub.publisher"

  members = [
    google_logging_project_sink.log_sink.writer_identity
  ]
}

# GCS bucket for archive
resource "google_storage_bucket" "log_archive" {
  name     = "${var.environment}-gcp-log-archive"
  location = "US"

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }

    condition {
      age = 30
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }

    condition {
      age = 90
    }
  }
}

# ============================================================================
# Azure Monitor Logs
# ============================================================================

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.environment}-log-analytics"
  location            = "East US"
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${var.environment}-logging"
  location = "East US"

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Event Hub for log streaming
resource "azurerm_eventhub_namespace" "logs" {
  name                = "${var.environment}-logs-eventhub"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"
  capacity            = 1

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "azurerm_eventhub" "logs" {
  name                = "logs"
  namespace_name      = azurerm_eventhub_namespace.logs.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = 2
  message_retention   = 1
}

# Diagnostic setting to send logs to Event Hub
resource "azurerm_monitor_diagnostic_setting" "logs" {
  name                       = "${var.environment}-diagnostic-logs"
  target_resource_id         = azurerm_log_analytics_workspace.main.id
  eventhub_name              = azurerm_eventhub.logs.name
  eventhub_authorization_rule_id = azurerm_eventhub_namespace_authorization_rule.logs.id

  enabled_log {
    category = "Audit"
  }

  metric {
    category = "AllMetrics"
  }
}

resource "azurerm_eventhub_namespace_authorization_rule" "logs" {
  name                = "log-sender"
  namespace_name      = azurerm_eventhub_namespace.logs.name
  resource_group_name = azurerm_resource_group.main.name

  listen = false
  send   = true
  manage = false
}

# Storage account for archive
resource "azurerm_storage_account" "log_archive" {
  name                     = "${var.environment}logarchive"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "aws_log_group_name" {
  description = "AWS CloudWatch Log Group name"
  value       = aws_cloudwatch_log_group.app_logs.name
}

output "aws_log_archive_bucket" {
  description = "AWS S3 bucket for log archive"
  value       = aws_s3_bucket.log_archive.id
}

output "gcp_log_sink_name" {
  description = "GCP Log Sink name"
  value       = google_logging_project_sink.log_sink.name
}

output "gcp_pubsub_topic" {
  description = "GCP Pub/Sub topic for logs"
  value       = google_pubsub_topic.logs.name
}

output "azure_log_analytics_workspace_id" {
  description = "Azure Log Analytics Workspace ID"
  value       = azurerm_log_analytics_workspace.main.workspace_id
}

output "azure_eventhub_name" {
  description = "Azure Event Hub name for logs"
  value       = azurerm_eventhub.logs.name
}
