# Terraform Outputs for Storage Infrastructure

# S3 Bucket Outputs
output "data_lake_bucket_name" {
  description = "Name of the primary data lake S3 bucket"
  value       = aws_s3_bucket.wildfire_data_lake.id
}

output "data_lake_bucket_arn" {
  description = "ARN of the primary data lake S3 bucket"
  value       = aws_s3_bucket.wildfire_data_lake.arn
}

output "data_lake_bucket_domain_name" {
  description = "Domain name of the data lake S3 bucket"
  value       = aws_s3_bucket.wildfire_data_lake.bucket_domain_name
}

output "audit_logs_bucket_name" {
  description = "Name of the audit logs S3 bucket"
  value       = aws_s3_bucket.wildfire_audit_logs.id
}

output "audit_logs_bucket_arn" {
  description = "ARN of the audit logs S3 bucket"
  value       = aws_s3_bucket.wildfire_audit_logs.arn
}

output "replica_bucket_name" {
  description = "Name of the replica S3 bucket (disaster recovery)"
  value       = aws_s3_bucket.wildfire_data_lake_replica.id
}

# KMS Key Outputs
output "data_encryption_key_id" {
  description = "ID of the KMS key for data encryption"
  value       = aws_kms_key.wildfire_data_key.key_id
}

output "data_encryption_key_arn" {
  description = "ARN of the KMS key for data encryption"
  value       = aws_kms_key.wildfire_data_key.arn
}

output "audit_encryption_key_id" {
  description = "ID of the KMS key for audit log encryption"
  value       = aws_kms_key.wildfire_audit_key.key_id
}

output "audit_encryption_key_arn" {
  description = "ARN of the KMS key for audit log encryption"
  value       = aws_kms_key.wildfire_audit_key.arn
}

# IAM Role Outputs
output "s3_replication_role_arn" {
  description = "ARN of the S3 replication IAM role"
  value       = aws_iam_role.s3_replication.arn
}

# SNS Topic Outputs
output "storage_alerts_topic_arn" {
  description = "ARN of the SNS topic for storage alerts"
  value       = aws_sns_topic.storage_alerts.arn
}

# CloudWatch Alarm Outputs
output "storage_cost_alarm_name" {
  description = "Name of the CloudWatch alarm for storage costs"
  value       = aws_cloudwatch_metric_alarm.s3_storage_cost.alarm_name
}

# Lifecycle Configuration Summary
output "lifecycle_rules_summary" {
  description = "Summary of lifecycle rules configured"
  value = {
    fire_detection = {
      hot_days    = var.retention_days_hot
      warm_days   = var.retention_days_warm
      cold_days   = var.retention_days_cold
      archive_days = var.retention_days_archive
    }
    restricted_data = {
      retention = "permanent"
    }
    public_weather = {
      retention_days = 365
    }
  }
}

# Storage Tier Cost Estimates (monthly)
output "estimated_monthly_costs" {
  description = "Estimated monthly storage costs by tier (USD)"
  value = {
    hot_tier_standard     = "~$23 per TB"
    warm_tier_ia          = "~$21 per TB"
    cold_tier_glacier_ir  = "~$4 per TB"
    archive_tier_deep     = "~$0.99 per TB"
  }
}

# Configuration Status
output "configuration_status" {
  description = "Status of key configuration settings"
  value = {
    versioning_enabled           = var.enable_versioning
    encryption_enabled           = var.enable_encryption
    intelligent_tiering_enabled  = var.enable_s3_intelligent_tiering
    cross_region_replication     = var.enable_cross_region_replication
    object_lock_enabled          = var.object_lock_enabled
    kms_key_rotation_enabled     = var.kms_key_rotation_enabled
    access_logging_enabled       = var.enable_access_logging
    inventory_enabled            = var.enable_inventory
  }
}

# Connection Strings for Applications
output "s3_connection_strings" {
  description = "S3 connection strings for application configuration"
  value = {
    data_lake_uri = "s3://${aws_s3_bucket.wildfire_data_lake.id}"
    audit_logs_uri = "s3://${aws_s3_bucket.wildfire_audit_logs.id}"
    replica_uri = "s3://${aws_s3_bucket.wildfire_data_lake_replica.id}"
  }
}

# Lifecycle Transition Timeline
output "lifecycle_transition_timeline" {
  description = "Timeline for data lifecycle transitions"
  value = {
    day_0_to_7    = "Hot Tier (S3 Standard) - Real-time access"
    day_7_to_90   = "Warm Tier (S3 Standard-IA) - Frequent access"
    day_90_to_365 = "Cold Tier (S3 Glacier Instant Retrieval) - Infrequent access"
    day_365_plus  = "Archive Tier (S3 Glacier Deep Archive) - Rare access"
    expiration    = "${var.retention_days_archive} days (${var.retention_days_archive / 365} years)"
  }
}

# Compliance Information
output "compliance_information" {
  description = "Compliance and regulatory information"
  value = {
    fisma_moderate = "7-year retention for audit logs"
    nist_800_53 = "Encryption at rest (SC-28), in transit (SC-8)"
    soc2_type_ii = "Data lifecycle management, versioning, encryption"
    object_lock = "WORM compliance for regulatory data"
  }
}
