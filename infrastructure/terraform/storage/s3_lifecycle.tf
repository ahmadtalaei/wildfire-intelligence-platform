# AWS S3 Buckets with Lifecycle Policies
# Implements Hot → Warm → Cold → Archive tiering strategy

# Data Lake Bucket (Multi-tier storage)
resource "aws_s3_bucket" "wildfire_data_lake" {
  bucket = "wildfire-data-lake-${var.environment}"

  tags = merge(local.common_tags, {
    Name        = "wildfire-data-lake"
    StorageTier = "multi-tier"
    Purpose     = "Primary data lake for fire intelligence"
  })
}

# Enable versioning for data protection
resource "aws_s3_bucket_versioning" "wildfire_data_lake" {
  bucket = aws_s3_bucket.wildfire_data_lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-Side Encryption with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "wildfire_data_lake" {
  bucket = aws_s3_bucket.wildfire_data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.wildfire_data_key.arn
    }
    bucket_key_enabled = true
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "wildfire_data_lake" {
  bucket = aws_s3_bucket.wildfire_data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle Policy: Hot → Warm → Cold → Archive
resource "aws_s3_bucket_lifecycle_configuration" "wildfire_data_lake" {
  bucket = aws_s3_bucket.wildfire_data_lake.id

  # Rule 1: Internal fire detection data (7 years retention)
  rule {
    id     = "fire-detection-lifecycle"
    status = "Enabled"

    filter {
      prefix = "internal/firms/"
    }

    # Transition to Warm tier after 7 days
    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    # Transition to Cold tier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER_IR" # Glacier Instant Retrieval
    }

    # Transition to Archive tier after 365 days
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    # Delete after 7 years (2555 days)
    expiration {
      days = 2555
    }

    # Handle non-current versions
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "GLACIER_IR"
    }

    noncurrent_version_expiration {
      noncurrent_days = 2555
    }
  }

  # Rule 2: Restricted data (Permanent retention)
  rule {
    id     = "restricted-data-lifecycle"
    status = "Enabled"

    filter {
      and {
        prefix = "restricted/"
        tags = {
          Classification = "restricted"
        }
      }
    }

    # Transition to Warm tier after 30 days
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    # Transition to Cold tier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    # Transition to Archive tier after 365 days (no expiration)
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    # No expiration for restricted data
  }

  # Rule 3: Public weather data (1 year retention)
  rule {
    id     = "public-weather-lifecycle"
    status = "Enabled"

    filter {
      prefix = "public/weather/"
    }

    # Transition to Warm tier after 7 days
    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    # Transition to Archive after 30 days
    transition {
      days          = 30
      storage_class = "DEEP_ARCHIVE"
    }

    # Delete after 1 year
    expiration {
      days = 365
    }
  }

  # Rule 4: Satellite imagery (7 years retention)
  rule {
    id     = "satellite-imagery-lifecycle"
    status = "Enabled"

    filter {
      and {
        prefix = "internal/imagery/"
        tags = {
          DataType = "satellite"
        }
      }
    }

    # Keep in Hot tier for 7 days
    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    # Transition to Cold tier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    # Transition to Archive after 365 days
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    # Delete after 7 years
    expiration {
      days = 2555
    }
  }

  # Rule 5: Compliance data (Permanent - legal hold)
  rule {
    id     = "compliance-lifecycle"
    status = "Enabled"

    filter {
      and {
        prefix = "compliance/"
        tags = {
          LegalHold = "true"
        }
      }
    }

    # Keep in Standard tier for 365 days
    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    # No expiration - permanent retention
  }

  # Rule 6: Abort incomplete multipart uploads
  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Rule 7: Delete expired object delete markers
  rule {
    id     = "delete-expired-markers"
    status = "Enabled"

    expiration {
      expired_object_delete_marker = true
    }
  }
}

# Object Lock for compliance (WORM - Write Once Read Many)
resource "aws_s3_bucket_object_lock_configuration" "wildfire_audit_logs" {
  bucket = aws_s3_bucket.wildfire_audit_logs.id

  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = 2555 # 7 years
    }
  }
}

# Audit Logs Bucket (separate for compliance)
resource "aws_s3_bucket" "wildfire_audit_logs" {
  bucket = "wildfire-audit-logs-${var.environment}"

  tags = merge(local.common_tags, {
    Name    = "wildfire-audit-logs"
    Purpose = "FISMA compliance audit logs"
  })
}

resource "aws_s3_bucket_versioning" "wildfire_audit_logs" {
  bucket = aws_s3_bucket.wildfire_audit_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "wildfire_audit_logs" {
  bucket = aws_s3_bucket.wildfire_audit_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.wildfire_audit_key.arn
    }
    bucket_key_enabled = true
  }
}

# Audit logs lifecycle (7 years retention)
resource "aws_s3_bucket_lifecycle_configuration" "wildfire_audit_logs" {
  bucket = aws_s3_bucket.wildfire_audit_logs.id

  rule {
    id     = "audit-logs-lifecycle"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    transition {
      days          = 730
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 2555 # 7 years FISMA requirement
    }
  }
}

# Replication for disaster recovery
resource "aws_s3_bucket" "wildfire_data_lake_replica" {
  provider = aws.us_east_1
  bucket   = "wildfire-data-lake-replica-${var.environment}"

  tags = merge(local.common_tags, {
    Name    = "wildfire-data-lake-replica"
    Purpose = "Disaster recovery replica"
    Region  = "us-east-1"
  })
}

resource "aws_s3_bucket_versioning" "wildfire_data_lake_replica" {
  provider = aws.us_east_1
  bucket   = aws_s3_bucket.wildfire_data_lake_replica.id

  versioning_configuration {
    status = "Enabled"
  }
}

# IAM role for S3 replication
resource "aws_iam_role" "s3_replication" {
  name = "wildfire-s3-replication-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_policy" "s3_replication" {
  name = "wildfire-s3-replication-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.wildfire_data_lake.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Resource = "${aws_s3_bucket.wildfire_data_lake.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Resource = "${aws_s3_bucket.wildfire_data_lake_replica.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "s3_replication" {
  role       = aws_iam_role.s3_replication.name
  policy_arn = aws_iam_policy.s3_replication.arn
}

# S3 replication configuration
resource "aws_s3_bucket_replication_configuration" "wildfire_data_lake" {
  depends_on = [aws_s3_bucket_versioning.wildfire_data_lake]

  role   = aws_iam_role.s3_replication.arn
  bucket = aws_s3_bucket.wildfire_data_lake.id

  rule {
    id     = "replicate-all"
    status = "Enabled"

    filter {
      prefix = ""
    }

    destination {
      bucket        = aws_s3_bucket.wildfire_data_lake_replica.arn
      storage_class = "STANDARD_IA"

      encryption_configuration {
        replica_kms_key_id = aws_kms_key.wildfire_data_key_replica.arn
      }
    }
  }
}

# S3 Intelligent-Tiering (optional optimization)
resource "aws_s3_bucket_intelligent_tiering_configuration" "wildfire_data_lake" {
  bucket = aws_s3_bucket.wildfire_data_lake.id
  name   = "intelligent-tiering-config"

  status = "Enabled"

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}

# CloudWatch metric alarm for storage costs
resource "aws_cloudwatch_metric_alarm" "s3_storage_cost" {
  alarm_name          = "wildfire-s3-storage-cost-alert"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400" # 1 day
  statistic           = "Maximum"
  threshold           = var.storage_cost_alert_threshold
  alarm_description   = "Alert when S3 storage costs exceed threshold"
  alarm_actions       = [aws_sns_topic.storage_alerts.arn]

  dimensions = {
    ServiceName = "Amazon Simple Storage Service"
    Currency    = "USD"
  }
}

# SNS topic for alerts
resource "aws_sns_topic" "storage_alerts" {
  name = "wildfire-storage-alerts"

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "storage_alerts_email" {
  topic_arn = aws_sns_topic.storage_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# S3 access logging
resource "aws_s3_bucket_logging" "wildfire_data_lake" {
  bucket = aws_s3_bucket.wildfire_data_lake.id

  target_bucket = aws_s3_bucket.wildfire_audit_logs.id
  target_prefix = "s3-access-logs/"
}

# Bucket inventory for cost analysis
resource "aws_s3_bucket_inventory" "wildfire_data_lake" {
  bucket = aws_s3_bucket.wildfire_data_lake.id
  name   = "weekly-inventory"

  included_object_versions = "All"

  schedule {
    frequency = "Weekly"
  }

  destination {
    bucket {
      format     = "CSV"
      bucket_arn = aws_s3_bucket.wildfire_audit_logs.arn
      prefix     = "inventory/"
    }
  }

  optional_fields = [
    "Size",
    "LastModifiedDate",
    "StorageClass",
    "ETag",
    "IsMultipartUploaded",
    "ReplicationStatus",
    "EncryptionStatus"
  ]
}
