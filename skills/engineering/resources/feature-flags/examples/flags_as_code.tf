# Feature Flags as Code - Terraform Configuration
#
# Production-ready Terraform configuration for managing feature flags
# Supports LaunchDarkly, Split, and custom providers

terraform {
  required_version = ">= 1.0"

  required_providers {
    launchdarkly = {
      source  = "launchdarkly/launchdarkly"
      version = "~> 2.0"
    }
  }
}

# Provider configuration
provider "launchdarkly" {
  access_token = var.launchdarkly_access_token
}

# Variables
variable "launchdarkly_access_token" {
  description = "LaunchDarkly API access token"
  type        = string
  sensitive   = true
}

variable "project_key" {
  description = "LaunchDarkly project key"
  type        = string
  default     = "default"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

# Data sources
data "launchdarkly_project" "main" {
  key = var.project_key
}

data "launchdarkly_environment" "main" {
  key        = var.environment
  project_key = data.launchdarkly_project.main.key
}

# Feature Flag: Release Toggle
resource "launchdarkly_feature_flag" "new_dashboard" {
  project_key = data.launchdarkly_project.main.key
  key         = "new-dashboard"
  name        = "New Dashboard"
  description = "Enable new dashboard UI"

  variation_type = "boolean"
  variations {
    value       = true
    name        = "Enabled"
    description = "Show new dashboard"
  }
  variations {
    value       = false
    name        = "Disabled"
    description = "Show legacy dashboard"
  }

  defaults {
    on_variation  = 0
    off_variation = 1
  }

  tags = [
    "frontend",
    "ui",
    "release"
  ]

  maintainer_id = "team-frontend"
}

# Feature Flag Environment Configuration
resource "launchdarkly_feature_flag_environment" "new_dashboard_prod" {
  flag_id = launchdarkly_feature_flag.new_dashboard.id
  env_key = data.launchdarkly_environment.main.key

  on = true

  targets {
    values = [
      "user-admin-1",
      "user-admin-2"
    ]
    variation = 0
  }

  fallthrough {
    rollout_weights = [25, 75]  # 25% enabled, 75% disabled
  }

  off_variation = 1
}

# Feature Flag: Experiment with Multiple Variations
resource "launchdarkly_feature_flag" "checkout_flow" {
  project_key = data.launchdarkly_project.main.key
  key         = "checkout-flow-variant"
  name        = "Checkout Flow Variant"
  description = "A/B test for checkout flow"

  variation_type = "string"
  variations {
    value       = "control"
    name        = "Control"
    description = "Current checkout flow"
  }
  variations {
    value       = "variant-a"
    name        = "Variant A"
    description = "Single-page checkout"
  }
  variations {
    value       = "variant-b"
    name        = "Variant B"
    description = "Express checkout"
  }

  defaults {
    on_variation  = 0
    off_variation = 0
  }

  tags = [
    "experiment",
    "checkout",
    "conversion"
  ]
}

resource "launchdarkly_feature_flag_environment" "checkout_flow_prod" {
  flag_id = launchdarkly_feature_flag.checkout_flow.id
  env_key = data.launchdarkly_environment.main.key

  on = true

  # Rule: Premium users get variant B
  rules {
    clauses {
      attribute = "plan"
      op        = "in"
      values    = ["premium", "enterprise"]
      negate    = false
    }
    variation = 2  # variant-b
  }

  # Rule: 50/50 split for remaining users
  fallthrough {
    rollout_weights = [50, 50, 0]  # 50% control, 50% variant-a, 0% variant-b
  }

  off_variation = 0
}

# Feature Flag: JSON Configuration
resource "launchdarkly_feature_flag" "api_config" {
  project_key = data.launchdarkly_project.main.key
  key         = "api-rate-limits"
  name        = "API Rate Limits"
  description = "Configure API rate limits per plan"

  variation_type = "json"
  variations {
    value = jsonencode({
      requests_per_minute = 60
      burst_limit         = 100
    })
    name        = "Free Tier"
    description = "Rate limits for free users"
  }
  variations {
    value = jsonencode({
      requests_per_minute = 600
      burst_limit         = 1000
    })
    name        = "Premium Tier"
    description = "Rate limits for premium users"
  }
  variations {
    value = jsonencode({
      requests_per_minute = 6000
      burst_limit         = 10000
    })
    name        = "Enterprise Tier"
    description = "Rate limits for enterprise users"
  }

  defaults {
    on_variation  = 0
    off_variation = 0
  }

  tags = ["backend", "api", "ops"]
}

resource "launchdarkly_feature_flag_environment" "api_config_prod" {
  flag_id = launchdarkly_feature_flag.api_config.id
  env_key = data.launchdarkly_environment.main.key

  on = true

  # Enterprise users
  rules {
    clauses {
      attribute = "plan"
      op        = "equals"
      values    = ["enterprise"]
      negate    = false
    }
    variation = 2
  }

  # Premium users
  rules {
    clauses {
      attribute = "plan"
      op        = "equals"
      values    = ["premium"]
      negate    = false
    }
    variation = 1
  }

  # Default to free tier
  fallthrough {
    variation = 0
  }

  off_variation = 0
}

# Feature Flag: Kill Switch
resource "launchdarkly_feature_flag" "ml_recommendations" {
  project_key = data.launchdarkly_project.main.key
  key         = "ml-recommendations"
  name        = "ML Recommendations"
  description = "Kill switch for ML recommendation engine"

  variation_type = "boolean"
  variations {
    value = true
    name  = "Enabled"
  }
  variations {
    value = false
    name  = "Disabled"
  }

  defaults {
    on_variation  = 0
    off_variation = 1
  }

  tags = [
    "kill-switch",
    "ml",
    "performance"
  ]

  temporary = false
}

resource "launchdarkly_feature_flag_environment" "ml_recommendations_prod" {
  flag_id = launchdarkly_feature_flag.ml_recommendations.id
  env_key = data.launchdarkly_environment.main.key

  on = true

  fallthrough {
    variation = 0  # Enabled by default
  }

  off_variation = 1
}

# Segment: Beta Users
resource "launchdarkly_segment" "beta_users" {
  key         = "beta-users"
  project_key = data.launchdarkly_project.main.key
  env_key     = data.launchdarkly_environment.main.key
  name        = "Beta Users"
  description = "Users who opted into beta program"

  included = [
    "user-beta-1",
    "user-beta-2"
  ]

  rules {
    clauses {
      attribute = "beta_opted_in"
      op        = "equals"
      values    = ["true"]
      negate    = false
    }
  }

  tags = ["beta", "early-access"]
}

# Feature Flag using Segment
resource "launchdarkly_feature_flag" "beta_features" {
  project_key = data.launchdarkly_project.main.key
  key         = "beta-features"
  name        = "Beta Features"
  description = "Enable beta features for beta users"

  variation_type = "boolean"
  variations {
    value = true
    name  = "Enabled"
  }
  variations {
    value = false
    name  = "Disabled"
  }

  defaults {
    on_variation  = 0
    off_variation = 1
  }

  tags = ["beta"]
}

resource "launchdarkly_feature_flag_environment" "beta_features_prod" {
  flag_id = launchdarkly_feature_flag.beta_features.id
  env_key = data.launchdarkly_environment.main.key

  on = true

  # Enable for beta segment
  rules {
    clauses {
      attribute = ""
      op        = "segmentMatch"
      values    = [launchdarkly_segment.beta_users.key]
      negate    = false
    }
    variation = 0
  }

  fallthrough {
    variation = 1  # Disabled by default
  }

  off_variation = 1
}

# Outputs
output "new_dashboard_flag_key" {
  description = "New dashboard flag key"
  value       = launchdarkly_feature_flag.new_dashboard.key
}

output "checkout_flow_flag_key" {
  description = "Checkout flow flag key"
  value       = launchdarkly_feature_flag.checkout_flow.key
}

output "beta_segment_key" {
  description = "Beta users segment key"
  value       = launchdarkly_segment.beta_users.key
}

# Module: Flag Group
module "feature_flags_group" {
  source = "./modules/flag-group"

  project_key = data.launchdarkly_project.main.key
  env_key     = data.launchdarkly_environment.main.key

  flags = {
    "feature-a" = {
      name        = "Feature A"
      description = "First feature"
      enabled     = true
      rollout_pct = 50
      tags        = ["group-1"]
    }
    "feature-b" = {
      name        = "Feature B"
      description = "Second feature"
      enabled     = true
      rollout_pct = 25
      tags        = ["group-1"]
    }
  }
}

# Data Export: All Flags
data "launchdarkly_feature_flag" "all" {
  for_each = toset([
    "new-dashboard",
    "checkout-flow-variant",
    "api-rate-limits"
  ])

  key         = each.key
  project_key = data.launchdarkly_project.main.key
}

# Output all flag configurations
output "all_flags" {
  description = "All feature flag configurations"
  value = {
    for key, flag in data.launchdarkly_feature_flag.all : key => {
      name        = flag.name
      description = flag.description
      tags        = flag.tags
    }
  }
}
