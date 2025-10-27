# IAM Roles and Policies for Storage Access

# Data Ingestion Service Role
resource "aws_iam_role" "data_ingestion_service" {
  name = "wildfire-data-ingestion-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "data-ingestion-service-role"
  })
}

# Policy for data ingestion (write to S3)
resource "aws_iam_policy" "data_ingestion_write" {
  name        = "wildfire-data-ingestion-write-policy"
  description = "Allow data ingestion service to write to S3 data lake"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "WriteToDataLake"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:PutObjectTagging"
        ]
        Resource = [
          "${aws_s3_bucket.wildfire_data_lake.arn}/internal/*",
          "${aws_s3_bucket.wildfire_data_lake.arn}/public/*"
        ]
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
            "s3:x-amz-server-side-encryption-aws-kms-key-id" = aws_kms_key.wildfire_data_key.arn
          }
        }
      },
      {
        Sid    = "KMSEncryptDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.wildfire_data_key.arn
      },
      {
        Sid    = "ListBuckets"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = aws_s3_bucket.wildfire_data_lake.arn
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "data_ingestion_write" {
  role       = aws_iam_role.data_ingestion_service.name
  policy_arn = aws_iam_policy.data_ingestion_write.arn
}

# Fire Analyst Read-Only Role
resource "aws_iam_role" "fire_analyst_readonly" {
  name = "wildfire-fire-analyst-readonly-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = "calfire-analyst"
          }
        }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "fire-analyst-readonly-role"
  })
}

# Policy for fire analyst (read from internal data)
resource "aws_iam_policy" "fire_analyst_readonly" {
  name        = "wildfire-fire-analyst-readonly-policy"
  description = "Read-only access to internal fire detection data"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadInternalData"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.wildfire_data_lake.arn,
          "${aws_s3_bucket.wildfire_data_lake.arn}/internal/firms/*",
          "${aws_s3_bucket.wildfire_data_lake.arn}/internal/firesat/*",
          "${aws_s3_bucket.wildfire_data_lake.arn}/internal/landsat/*",
          "${aws_s3_bucket.wildfire_data_lake.arn}/public/*"
        ]
        Condition = {
          IpAddress = {
            "aws:SourceIp" = var.calfire_office_ip_ranges
          }
        }
      },
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.wildfire_data_key.arn
      },
      {
        Sid    = "DenyUnencryptedObjectUploads"
        Effect = "Deny"
        Action = "s3:PutObject"
        Resource = "${aws_s3_bucket.wildfire_data_lake.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "fire_analyst_readonly" {
  role       = aws_iam_role.fire_analyst_readonly.name
  policy_arn = aws_iam_policy.fire_analyst_readonly.arn
}

# Fire Chief Dashboard Role (restricted data access)
resource "aws_iam_role" "fire_chief_dashboard" {
  name = "wildfire-fire-chief-dashboard-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "fire-chief-dashboard-role"
  })
}

# Policy for fire chief dashboard (restricted data access)
resource "aws_iam_policy" "fire_chief_dashboard" {
  name        = "wildfire-fire-chief-dashboard-policy"
  description = "Access for Fire Chief dashboard to restricted data"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadRestrictedData"
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.wildfire_data_lake.arn}/restricted/*",
          "${aws_s3_bucket.wildfire_data_lake.arn}/internal/firms/*"
        ]
      },
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.wildfire_data_key.arn
      },
      {
        Sid    = "CloudWatchMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "fire_chief_dashboard" {
  role       = aws_iam_role.fire_chief_dashboard.name
  policy_arn = aws_iam_policy.fire_chief_dashboard.arn
}

# Lifecycle Management Lambda Role
resource "aws_iam_role" "lifecycle_management_lambda" {
  name = "wildfire-lifecycle-management-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "lifecycle-management-lambda-role"
  })
}

# Policy for lifecycle management Lambda
resource "aws_iam_policy" "lifecycle_management_lambda" {
  name        = "wildfire-lifecycle-management-lambda-policy"
  description = "Allow Lambda to manage S3 lifecycle transitions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3LifecycleManagement"
        Effect = "Allow"
        Action = [
          "s3:GetLifecycleConfiguration",
          "s3:PutLifecycleConfiguration",
          "s3:GetBucketTagging",
          "s3:PutObjectTagging",
          "s3:GetObjectTagging"
        ]
        Resource = [
          aws_s3_bucket.wildfire_data_lake.arn,
          "${aws_s3_bucket.wildfire_data_lake.arn}/*"
        ]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "EventBridge"
        Effect = "Allow"
        Action = [
          "events:PutRule",
          "events:PutTargets"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lifecycle_management_lambda" {
  role       = aws_iam_role.lifecycle_management_lambda.name
  policy_arn = aws_iam_policy.lifecycle_management_lambda.arn
}

# Security Audit Read-Only Role
resource "aws_iam_role" "security_audit_readonly" {
  name = "wildfire-security-audit-readonly-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = "calfire-security-audit"
          }
        }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "security-audit-readonly-role"
  })
}

# Policy for security audit (read all buckets)
resource "aws_iam_policy" "security_audit_readonly" {
  name        = "wildfire-security-audit-readonly-policy"
  description = "Security team read-only access for compliance audits"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadAllBuckets"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetBucketPolicy",
          "s3:GetBucketAcl",
          "s3:GetEncryptionConfiguration",
          "s3:GetBucketVersioning",
          "s3:GetBucketLogging"
        ]
        Resource = [
          "arn:aws:s3:::wildfire-*",
          "arn:aws:s3:::wildfire-*/*"
        ]
      },
      {
        Sid    = "CloudTrailLogsAccess"
        Effect = "Allow"
        Action = [
          "cloudtrail:LookupEvents",
          "cloudtrail:GetTrail",
          "cloudtrail:GetTrailStatus"
        ]
        Resource = "*"
      },
      {
        Sid    = "KMSKeyInspection"
        Effect = "Allow"
        Action = [
          "kms:DescribeKey",
          "kms:GetKeyPolicy",
          "kms:GetKeyRotationStatus",
          "kms:ListKeys"
        ]
        Resource = "*"
      },
      {
        Sid    = "IAMReadOnly"
        Effect = "Allow"
        Action = [
          "iam:GetUser",
          "iam:GetRole",
          "iam:GetPolicy",
          "iam:GetPolicyVersion",
          "iam:ListAttachedUserPolicies",
          "iam:ListAttachedRolePolicies"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "security_audit_readonly" {
  role       = aws_iam_role.security_audit_readonly.name
  policy_arn = aws_iam_policy.security_audit_readonly.arn
}

# Instance profile for EC2 instances
resource "aws_iam_instance_profile" "data_ingestion_service" {
  name = "wildfire-data-ingestion-service-instance-profile"
  role = aws_iam_role.data_ingestion_service.name

  tags = local.common_tags
}

# Variable for CAL FIRE office IP ranges
variable "calfire_office_ip_ranges" {
  description = "IP ranges for CAL FIRE offices (CIDR notation)"
  type        = list(string)
  default     = ["192.0.2.0/24", "198.51.100.0/24"] # Example IP ranges
}
