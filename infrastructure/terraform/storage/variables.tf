# Terraform Variables for Storage Infrastructure

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "aws_region" {
  description = "Primary AWS region for storage infrastructure"
  type        = string
  default     = "us-west-2"
}

variable "aws_region_replica" {
  description = "Secondary AWS region for disaster recovery"
  type        = string
  default     = "us-east-1"
}

variable "gcp_project_id" {
  description = "GCP project ID for multi-cloud storage"
  type        = string
  default     = "wildfire-project"
}

variable "gcp_region" {
  description = "GCP region for storage buckets"
  type        = string
  default     = "us-west1"
}

variable "azure_location" {
  description = "Azure location for blob storage"
  type        = string
  default     = "West US"
}

variable "storage_cost_alert_threshold" {
  description = "Monthly storage cost alert threshold (USD)"
  type        = number
  default     = 5000
}

variable "alert_email" {
  description = "Email address for storage alerts"
  type        = string
  default     = "ops@calfire.ca.gov"
}

variable "enable_s3_intelligent_tiering" {
  description = "Enable S3 Intelligent-Tiering for cost optimization"
  type        = bool
  default     = true
}

variable "enable_cross_region_replication" {
  description = "Enable cross-region replication for disaster recovery"
  type        = bool
  default     = true
}

variable "lifecycle_policy_enabled" {
  description = "Enable lifecycle policies for automatic tier transitions"
  type        = bool
  default     = true
}

variable "object_lock_enabled" {
  description = "Enable S3 Object Lock for compliance (WORM)"
  type        = bool
  default     = true
}

variable "retention_days_hot" {
  description = "Retention period for hot tier (days)"
  type        = number
  default     = 7

  validation {
    condition     = var.retention_days_hot >= 1 && var.retention_days_hot <= 30
    error_message = "Hot tier retention must be between 1 and 30 days."
  }
}

variable "retention_days_warm" {
  description = "Retention period for warm tier (days)"
  type        = number
  default     = 90

  validation {
    condition     = var.retention_days_warm >= 30 && var.retention_days_warm <= 365
    error_message = "Warm tier retention must be between 30 and 365 days."
  }
}

variable "retention_days_cold" {
  description = "Retention period for cold tier (days)"
  type        = number
  default     = 365

  validation {
    condition     = var.retention_days_cold >= 90 && var.retention_days_cold <= 2555
    error_message = "Cold tier retention must be between 90 and 2555 days."
  }
}

variable "retention_days_archive" {
  description = "Retention period for archive tier (days, 0 = permanent)"
  type        = number
  default     = 2555 # 7 years for FISMA compliance
}

variable "enable_versioning" {
  description = "Enable S3 bucket versioning"
  type        = bool
  default     = true
}

variable "enable_encryption" {
  description = "Enable server-side encryption with KMS"
  type        = bool
  default     = true
}

variable "kms_key_rotation_enabled" {
  description = "Enable automatic KMS key rotation (365 days)"
  type        = bool
  default     = true
}

variable "enable_access_logging" {
  description = "Enable S3 access logging for audit trail"
  type        = bool
  default     = true
}

variable "enable_inventory" {
  description = "Enable S3 inventory for cost analysis"
  type        = bool
  default     = true
}

variable "inventory_frequency" {
  description = "S3 inventory frequency (Daily or Weekly)"
  type        = string
  default     = "Weekly"

  validation {
    condition     = contains(["Daily", "Weekly"], var.inventory_frequency)
    error_message = "Inventory frequency must be Daily or Weekly."
  }
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}

variable "data_classification_tags" {
  description = "Data classification tags for governance"
  type        = map(string)
  default = {
    public     = "Public"
    internal   = "Internal"
    restricted = "Restricted"
    regulated  = "Regulated"
  }
}
