# =====================================================================
# Wildfire Intelligence Platform - Terraform Infrastructure
# Challenge 2: Multi-Tier Storage Architecture
# =====================================================================
# This Terraform configuration provisions a hybrid cloud storage system:
# - On-Premises: PostgreSQL (HOT) + MinIO (WARM)
# - AWS: S3 Standard-IA (COLD) + S3 Glacier Deep Archive (ARCHIVE)
# =====================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "wildfire-terraform-state"
    key            = "challenge2/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "wildfire-terraform-locks"
  }
}

# =====================================================================
# Provider Configuration
# =====================================================================

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Wildfire Intelligence Platform"
      Challenge   = "Challenge 2 - Storage"
      Environment = var.environment
      ManagedBy   = "Terraform"
      CostCenter  = "CAL-FIRE-IT"
    }
  }
}

# =====================================================================
# Variables
# =====================================================================

variable "aws_region" {
  description = "AWS region for cloud storage tiers"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "wildfire"
}

variable "hot_retention_days" {
  description = "Days to retain data in HOT tier (PostgreSQL)"
  type        = number
  default     = 7
}

variable "warm_retention_days" {
  description = "Days to retain data in WARM tier (MinIO/S3 Standard)"
  type        = number
  default     = 90
}

variable "cold_retention_days" {
  description = "Days to retain data in COLD tier (S3 Standard-IA)"
  type        = number
  default     = 365
}

variable "archive_retention_years" {
  description = "Years to retain data in ARCHIVE tier (S3 Glacier)"
  type        = number
  default     = 7
}

variable "enable_replication" {
  description = "Enable cross-region replication for disaster recovery"
  type        = bool
  default     = true
}

variable "kms_key_deletion_window" {
  description = "KMS key deletion window in days"
  type        = number
  default     = 30
}

# =====================================================================
# Data Sources
# =====================================================================

data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

# =====================================================================
# KMS Encryption Keys
# =====================================================================

resource "aws_kms_key" "storage_encryption" {
  description             = "KMS key for wildfire storage encryption"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  tags = {
    Name = "${var.project_name}-storage-kms-${var.environment}"
  }
}

resource "aws_kms_alias" "storage_encryption" {
  name          = "alias/${var.project_name}-storage-${var.environment}"
  target_key_id = aws_kms_key.storage_encryption.key_id
}

# =====================================================================
# S3 Buckets - Multi-Tier Storage
# =====================================================================

# WARM Tier - S3 Standard (transition from on-prem MinIO)
resource "aws_s3_bucket" "warm_tier" {
  bucket = "${var.project_name}-warm-${var.aws_region}-${var.environment}"

  tags = {
    Name        = "Wildfire WARM Tier"
    StorageTier = "WARM"
    Retention   = "${var.warm_retention_days} days"
  }
}

resource "aws_s3_bucket_versioning" "warm_tier" {
  bucket = aws_s3_bucket.warm_tier.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "warm_tier" {
  bucket = aws_s3_bucket.warm_tier.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.storage_encryption.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "warm_tier" {
  bucket = aws_s3_bucket.warm_tier.id

  rule {
    id     = "transition-to-cold"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = var.warm_retention_days
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
  }
}

# COLD Tier - S3 Standard-IA
resource "aws_s3_bucket" "cold_tier" {
  bucket = "${var.project_name}-cold-${var.aws_region}-${var.environment}"

  tags = {
    Name        = "Wildfire COLD Tier"
    StorageTier = "COLD"
    Retention   = "${var.cold_retention_days} days"
  }
}

resource "aws_s3_bucket_versioning" "cold_tier" {
  bucket = aws_s3_bucket.cold_tier.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cold_tier" {
  bucket = aws_s3_bucket.cold_tier.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.storage_encryption.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "cold_tier" {
  bucket = aws_s3_bucket.cold_tier.id

  rule {
    id     = "transition-to-archive"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = var.cold_retention_days
      storage_class = "GLACIER_IR"
    }

    transition {
      days          = var.cold_retention_days + 90
      storage_class = "DEEP_ARCHIVE"
    }

    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER_IR"
    }

    expiration {
      days = var.archive_retention_years * 365
    }
  }
}

# ARCHIVE Tier - S3 Glacier Deep Archive
resource "aws_s3_bucket" "archive_tier" {
  bucket = "${var.project_name}-archive-${var.aws_region}-${var.environment}"

  tags = {
    Name        = "Wildfire ARCHIVE Tier"
    StorageTier = "ARCHIVE"
    Retention   = "${var.archive_retention_years} years"
  }
}

resource "aws_s3_bucket_versioning" "archive_tier" {
  bucket = aws_s3_bucket.archive_tier.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "archive_tier" {
  bucket = aws_s3_bucket.archive_tier.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.storage_encryption.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "archive_tier" {
  bucket = aws_s3_bucket.archive_tier.id

  rule {
    id     = "permanent-retention"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 0
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = var.archive_retention_years * 365
    }
  }
}

# Object Lock for Archive Compliance (WORM)
resource "aws_s3_bucket_object_lock_configuration" "archive_tier" {
  bucket = aws_s3_bucket.archive_tier.id

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.archive_retention_years * 365
    }
  }
}

# =====================================================================
# S3 Bucket Policies - Least Privilege Access
# =====================================================================

data "aws_iam_policy_document" "warm_tier_policy" {
  statement {
    sid    = "DenyUnencryptedObjectUploads"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = ["s3:PutObject"]

    resources = ["${aws_s3_bucket.warm_tier.arn}/*"]

    condition {
      test     = "StringNotEquals"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["aws:kms"]
    }
  }

  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = ["s3:*"]

    resources = [
      aws_s3_bucket.warm_tier.arn,
      "${aws_s3_bucket.warm_tier.arn}/*"
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "warm_tier" {
  bucket = aws_s3_bucket.warm_tier.id
  policy = data.aws_iam_policy_document.warm_tier_policy.json
}

# =====================================================================
# IAM Roles for Airflow/Data Pipeline
# =====================================================================

resource "aws_iam_role" "airflow_s3_access" {
  name = "${var.project_name}-airflow-s3-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "Airflow S3 Access Role"
  }
}

resource "aws_iam_policy" "airflow_s3_access" {
  name        = "${var.project_name}-airflow-s3-policy-${var.environment}"
  description = "Policy for Airflow to access S3 storage tiers"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.warm_tier.arn,
          "${aws_s3_bucket.warm_tier.arn}/*",
          aws_s3_bucket.cold_tier.arn,
          "${aws_s3_bucket.cold_tier.arn}/*",
          aws_s3_bucket.archive_tier.arn,
          "${aws_s3_bucket.archive_tier.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [aws_kms_key.storage_encryption.arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "airflow_s3_access" {
  role       = aws_iam_role.airflow_s3_access.name
  policy_arn = aws_iam_policy.airflow_s3_access.arn
}

# =====================================================================
# CloudWatch Alarms for Storage Monitoring
# =====================================================================

resource "aws_cloudwatch_metric_alarm" "warm_tier_size" {
  alarm_name          = "${var.project_name}-warm-tier-size-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "BucketSizeBytes"
  namespace           = "AWS/S3"
  period              = 86400
  statistic           = "Average"
  threshold           = 1099511627776 # 1 TB
  alarm_description   = "Warm tier storage exceeds 1TB"
  alarm_actions       = []

  dimensions = {
    BucketName  = aws_s3_bucket.warm_tier.bucket
    StorageType = "StandardStorage"
  }
}

# =====================================================================
# Disaster Recovery - Cross-Region Replication
# =====================================================================

resource "aws_s3_bucket" "dr_replica" {
  count    = var.enable_replication ? 1 : 0
  provider = aws
  bucket   = "${var.project_name}-dr-replica-us-east-1-${var.environment}"

  tags = {
    Name = "Wildfire DR Replica"
    Role = "Disaster Recovery"
  }
}

resource "aws_s3_bucket_versioning" "dr_replica" {
  count  = var.enable_replication ? 1 : 0
  bucket = aws_s3_bucket.dr_replica[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_iam_role" "replication" {
  count = var.enable_replication ? 1 : 0
  name  = "${var.project_name}-s3-replication-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_s3_bucket_replication_configuration" "warm_tier" {
  count = var.enable_replication ? 1 : 0

  depends_on = [aws_s3_bucket_versioning.warm_tier]

  role   = aws_iam_role.replication[0].arn
  bucket = aws_s3_bucket.warm_tier.id

  rule {
    id     = "replicate-to-dr"
    status = "Enabled"

    filter {
      prefix = ""
    }

    destination {
      bucket        = aws_s3_bucket.dr_replica[0].arn
      storage_class = "STANDARD_IA"

      encryption_configuration {
        replica_kms_key_id = aws_kms_key.storage_encryption.arn
      }
    }
  }
}

# =====================================================================
# Outputs
# =====================================================================

output "warm_tier_bucket" {
  description = "WARM tier S3 bucket name"
  value       = aws_s3_bucket.warm_tier.id
}

output "cold_tier_bucket" {
  description = "COLD tier S3 bucket name"
  value       = aws_s3_bucket.cold_tier.id
}

output "archive_tier_bucket" {
  description = "ARCHIVE tier S3 bucket name"
  value       = aws_s3_bucket.archive_tier.id
}

output "kms_key_id" {
  description = "KMS key ID for encryption"
  value       = aws_kms_key.storage_encryption.key_id
  sensitive   = true
}

output "kms_key_arn" {
  description = "KMS key ARN for encryption"
  value       = aws_kms_key.storage_encryption.arn
}

output "airflow_role_arn" {
  description = "IAM role ARN for Airflow S3 access"
  value       = aws_iam_role.airflow_s3_access.arn
}

output "dr_replica_bucket" {
  description = "DR replica bucket name (if enabled)"
  value       = var.enable_replication ? aws_s3_bucket.dr_replica[0].id : "Replication disabled"
}

output "estimated_monthly_cost" {
  description = "Estimated monthly cost for cloud storage tiers"
  value       = <<-EOT
    Estimated Monthly Costs (based on 10TB total):
    - S3 Standard (WARM): $230/month (1TB @ $0.023/GB)
    - S3 Standard-IA (COLD): $125/month (5TB @ $0.0125/GB)
    - S3 Glacier Deep Archive: $4/month (4TB @ $0.00099/GB)
    - KMS: $1/month
    - Data Transfer: $45/month (500GB egress @ $0.09/GB)
    Total: ~$405/month
  EOT
}
