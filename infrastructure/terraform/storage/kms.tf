# AWS KMS Keys for Data Encryption
# Implements encryption at rest for all storage tiers

# Primary data encryption key (us-west-2)
resource "aws_kms_key" "wildfire_data_key" {
  description             = "Wildfire Data Lake Encryption Key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  multi_region            = false

  tags = merge(local.common_tags, {
    Name    = "wildfire-data-key"
    Purpose = "S3 data encryption"
  })
}

resource "aws_kms_alias" "wildfire_data_key" {
  name          = "alias/wildfire-data-key"
  target_key_id = aws_kms_key.wildfire_data_key.key_id
}

# Key policy for data encryption key
resource "aws_kms_key_policy" "wildfire_data_key" {
  key_id = aws_kms_key.wildfire_data_key.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow S3 to use the key"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "s3.${var.aws_region}.amazonaws.com"
          }
        }
      },
      {
        Sid    = "Allow data ingestion service to encrypt data"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.data_ingestion_service.arn
        }
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "Allow CloudWatch Logs to use the key"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })
}

# Audit log encryption key
resource "aws_kms_key" "wildfire_audit_key" {
  description             = "Wildfire Audit Logs Encryption Key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name    = "wildfire-audit-key"
    Purpose = "Audit log encryption"
  })
}

resource "aws_kms_alias" "wildfire_audit_key" {
  name          = "alias/wildfire-audit-key"
  target_key_id = aws_kms_key.wildfire_audit_key.key_id
}

# Replica key for disaster recovery (us-east-1)
resource "aws_kms_key" "wildfire_data_key_replica" {
  provider                = aws.us_east_1
  description             = "Wildfire Data Lake Encryption Key (Replica)"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name    = "wildfire-data-key-replica"
    Purpose = "S3 replication encryption"
    Region  = "us-east-1"
  })
}

resource "aws_kms_alias" "wildfire_data_key_replica" {
  provider      = aws.us_east_1
  name          = "alias/wildfire-data-key-replica"
  target_key_id = aws_kms_key.wildfire_data_key_replica.key_id
}

# CloudWatch alarm for KMS key rotation
resource "aws_cloudwatch_metric_alarm" "kms_key_rotation_overdue" {
  alarm_name          = "wildfire-kms-rotation-overdue"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "DaysSinceRotation"
  namespace           = "AWS/KMS"
  period              = "86400"
  statistic           = "Maximum"
  threshold           = 365
  alarm_description   = "Alert when KMS key rotation is overdue (>365 days)"
  alarm_actions       = [aws_sns_topic.storage_alerts.arn]
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
