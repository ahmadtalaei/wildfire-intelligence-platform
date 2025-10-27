# CAL FIRE Wildfire Intelligence Platform - Security Audit and Logging Plan

**Document Version**: 1.0.0
**Effective Date**: October 2025
**Owner**: CAL FIRE Security Team
**Compliance**: FISMA, NIST 800-53 (AU family), SOC2, CCPA

---

## 1. Executive Summary

This document defines the comprehensive audit logging, monitoring, and compliance verification strategy for the CAL FIRE Wildfire Intelligence Platform. All security-relevant events must be logged, retained, and analyzed according to these standards to ensure accountability, incident detection, and regulatory compliance.

**Audit Objectives**:
- **Accountability**: Track all user and system actions for forensic analysis
- **Threat Detection**: Identify anomalous behavior and security incidents in real-time
- **Compliance**: Meet FISMA, NIST 800-53 AU controls, SOC 2, and CCPA requirements
- **Incident Response**: Provide audit trail for security investigations

---

## 2. Audit Logging Requirements

### 2.1 Events to be Logged

| Event Category | Examples | Log Level | Retention |
|---------------|----------|-----------|-----------|
| **Authentication** | Login success/failure, MFA challenges, session creation | INFO/WARNING | 7 years |
| **Authorization** | Permission grants/denials, role changes, policy updates | INFO | 7 years |
| **Data Access** | Read/write to sensitive data, query execution, file downloads | INFO | 7 years |
| **Data Modification** | INSERT/UPDATE/DELETE operations, schema changes | INFO | 7 years |
| **Configuration Changes** | Firewall rule updates, encryption config, service restarts | WARNING | 7 years |
| **Security Events** | IDS/IPS alerts, malware detection, brute force attempts | ERROR/CRITICAL | 7 years |
| **Cryptographic Operations** | Key creation/deletion, encryption/decryption, signature verification | INFO | 7 years |
| **Network Activity** | Connection attempts, firewall blocks, VPN sessions | INFO | 90 days |
| **System Events** | Service starts/stops, resource exhaustion, crashes | WARNING/ERROR | 365 days |
| **Compliance Events** | Data deletion requests (CCPA), legal holds, audit queries | INFO | Permanent |

### 2.2 Minimum Log Fields

All audit logs must include:
```json
{
  "timestamp": "2025-10-06T14:30:45.123Z",
  "event_id": "AUTH-20251006-143045-001",
  "event_type": "authentication.login.success",
  "severity": "INFO",
  "user_id": "analyst@calfire.ca.gov",
  "source_ip": "192.0.2.45",
  "user_agent": "Mozilla/5.0...",
  "resource": "arn:aws:s3:::wildfire-data-lake/internal/firms/...",
  "action": "s3:GetObject",
  "result": "success",
  "session_id": "sess-a7f8d9e2-4c1b",
  "geo_location": {
    "country": "US",
    "region": "California",
    "city": "Sacramento"
  },
  "compliance_flags": ["FISMA", "SOC2"],
  "metadata": {
    "file_size_bytes": 1048576,
    "classification": "internal",
    "data_source": "firms_modis_terra"
  }
}
```

---

## 3. Audit Log Sources

### 3.1 AWS CloudTrail
**Purpose**: Track all AWS API calls (S3, RDS, KMS, IAM, EC2)

**Configuration**:
```bash
aws cloudtrail create-trail \
  --name wildfire-audit-trail \
  --s3-bucket-name wildfire-audit-logs \
  --include-global-service-events \
  --is-multi-region-trail \
  --enable-log-file-validation \
  --kms-key-id arn:aws:kms:us-west-2:123456789012:key/cloudtrail-key

aws cloudtrail start-logging --name wildfire-audit-trail
```

**Log Delivery**:
- **Primary**: S3 bucket `s3://wildfire-audit-logs/cloudtrail/`
- **Backup**: Glacier Deep Archive after 90 days
- **SIEM Integration**: CloudWatch Logs → Lambda → Splunk

**Events Logged**:
- S3 object access (GetObject, PutObject, DeleteObject)
- KMS key operations (Encrypt, Decrypt, GenerateDataKey)
- IAM changes (CreateUser, AttachUserPolicy, DeleteAccessKey)
- RDS authentication (Connect, Disconnect)

**Verification**:
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --max-results 10
```

### 3.2 Azure Activity Log
**Purpose**: Track Azure resource operations (Blob Storage, Key Vault, SQL Database)

**Configuration**:
```bash
az monitor log-profiles create \
  --name wildfire-audit-profile \
  --location global \
  --locations eastus westus \
  --categories Write Delete Action \
  --enabled true \
  --storage-account-id /subscriptions/.../resourceGroups/wildfire-rg/providers/Microsoft.Storage/storageAccounts/wildfireaudit
```

**Log Delivery**:
- **Primary**: Azure Storage Account `wildfireaudit`
- **SIEM Integration**: Event Hub → Azure Sentinel

**Events Logged**:
- Blob storage access (List, Read, Write, Delete)
- Key Vault operations (GetSecret, CreateKey, DeleteKey)
- SQL Database queries (via Azure SQL Auditing)

### 3.3 GCP Cloud Audit Logs
**Purpose**: Track GCP resource operations (Cloud Storage, BigQuery, Cloud KMS)

**Configuration**:
```bash
gcloud logging sinks create wildfire-audit-sink \
  storage.googleapis.com/wildfire-audit-logs \
  --log-filter='protoPayload.serviceName="storage.googleapis.com" OR protoPayload.serviceName="cloudkms.googleapis.com"'
```

**Log Types**:
- **Admin Activity Logs**: Resource configuration changes (always enabled)
- **Data Access Logs**: Read/write operations (enabled for wildfire project)
- **System Event Logs**: GCP-initiated actions (automatic)

### 3.4 PostgreSQL Audit (pgaudit)
**Purpose**: Track all database queries, authentication, schema changes

**Installation**:
```bash
apt-get install postgresql-15-pgaudit
```

**Configuration** (`/etc/postgresql/15/main/postgresql.conf`):
```conf
shared_preload_libraries = 'pgaudit'
pgaudit.log = 'read,write,ddl,role'
pgaudit.log_catalog = on
pgaudit.log_client = off
pgaudit.log_level = log
pgaudit.log_parameter = on
pgaudit.log_relation = on
pgaudit.log_statement_once = off
log_connections = on
log_disconnections = on
log_duration = on
log_line_prefix = '%t [%p]: user=%u,db=%d,app=%a,client=%h '
```

**Example Audit Log**:
```
2025-10-06 14:30:45 [12345]: user=analyst@calfire.ca.gov,db=wildfire_db,app=psql,client=192.0.2.45
LOG: AUDIT: SESSION,1,1,READ,SELECT,TABLE,public.firms_modis_terra_detections,
"SELECT * FROM firms_modis_terra_detections WHERE timestamp > '2025-10-01' LIMIT 100",<not logged>
```

**Log Rotation**:
```bash
# /etc/logrotate.d/postgresql-audit
/var/log/postgresql/postgresql-15-audit.log {
  daily
  rotate 365
  compress
  delaycompress
  notifempty
  create 0640 postgres postgres
  sharedscripts
  postrotate
    systemctl reload postgresql
  endscript
}
```

### 3.5 Kafka Audit Logs
**Purpose**: Track message production/consumption, topic access, ACL changes

**Configuration** (`/etc/kafka/server.properties`):
```properties
# Enable audit logging
authorizer.class.name=kafka.security.authorizer.AclAuthorizer
log.message.format.version=3.0

# Audit log configuration
audit.logger.name=kafka.audit
audit.logger.level=INFO
audit.log.dir=/var/log/kafka/audit
audit.log.retention.hours=8760  # 365 days

# Events to log
audit.log.authentication=true
audit.log.authorization=true
audit.log.metadata=true
audit.log.produce=true
audit.log.consume=true
```

**Example Audit Event**:
```json
{
  "timestamp": "2025-10-06T14:30:45.123Z",
  "event_type": "kafka.produce",
  "principal": "User:data-ingestion-service",
  "resource": "Topic:fire-detections",
  "operation": "WRITE",
  "result": "ALLOWED",
  "client_id": "data-ingestion-producer-1",
  "client_address": "192.0.2.50",
  "message_count": 152,
  "bytes_written": 524288
}
```

### 3.6 MinIO Audit Logs
**Purpose**: Track object storage access (GET, PUT, DELETE)

**Configuration**:
```bash
mc admin config set wildfire-minio audit \
  webhook_enable="on" \
  webhook_endpoint="https://siem.calfire.ca.gov/api/ingest" \
  webhook_auth_token="<auth-token>" \
  webhook_client_cert="" \
  webhook_client_key=""

# Enable audit logging
mc admin config set wildfire-minio logger_webhook:siem \
  endpoint="https://siem.calfire.ca.gov/api/ingest" \
  auth_token="<token>"
```

**Example Audit Event**:
```json
{
  "timestamp": "2025-10-06T14:30:45.123Z",
  "api": {
    "name": "GetObject",
    "bucket": "wildfire-backup",
    "object": "firms/2025/10/06/sample.json",
    "status": "200 OK",
    "statusCode": 200,
    "timeToFirstByte": "12ms",
    "timeToResponse": "45ms"
  },
  "requestID": "req-7a3f8d9e",
  "remotehost": "192.0.2.60",
  "userAgent": "MinIO (linux; amd64) minio-go/v7.0.45",
  "requestHeader": {
    "Authorization": "AWS4-HMAC-SHA256 ...",
    "X-Amz-Content-Sha256": "UNSIGNED-PAYLOAD",
    "X-Forwarded-For": "192.0.2.60"
  }
}
```

### 3.7 Nginx Access Logs
**Purpose**: Track HTTP/HTTPS requests to web applications

**Configuration** (`/etc/nginx/nginx.conf`):
```nginx
http {
  log_format audit_format '{'
    '"timestamp":"$time_iso8601",'
    '"remote_addr":"$remote_addr",'
    '"remote_user":"$remote_user",'
    '"request":"$request",'
    '"status":$status,'
    '"body_bytes_sent":$body_bytes_sent,'
    '"http_referer":"$http_referer",'
    '"http_user_agent":"$http_user_agent",'
    '"http_x_forwarded_for":"$http_x_forwarded_for",'
    '"request_time":$request_time,'
    '"upstream_response_time":"$upstream_response_time",'
    '"ssl_protocol":"$ssl_protocol",'
    '"ssl_cipher":"$ssl_cipher"'
  '}';

  access_log /var/log/nginx/access-audit.log audit_format;
  error_log /var/log/nginx/error-audit.log warn;
}
```

### 3.8 Operating System Audit (auditd)
**Purpose**: Track system-level events (file access, process execution, network)

**Configuration** (`/etc/audit/rules.d/wildfire.rules`):
```bash
# Watch sensitive directories
-w /etc/postgresql/ -p wa -k postgresql_config_change
-w /etc/kafka/ -p wa -k kafka_config_change
-w /etc/ssl/private/ -p ra -k tls_key_access
-w /var/lib/postgresql/data/ -p wa -k postgresql_data_access

# Watch authentication
-w /var/log/auth.log -p wa -k auth_log_modification

# Watch encryption keys
-w /etc/encryption/ -p ra -k encryption_key_access

# Audit all commands by privileged users
-a always,exit -F arch=b64 -F euid=0 -S execve -k root_commands

# Network connections
-a always,exit -F arch=b64 -S socket -S connect -k network_connection
```

**Restart auditd**:
```bash
systemctl restart auditd
```

---

## 4. Centralized Logging (SIEM Integration)

### 4.1 Log Aggregation Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Log Sources                              │
│  AWS CloudTrail │ Azure Activity │ GCP Audit │ PostgreSQL       │
│  Kafka Audit    │ MinIO Audit    │ Nginx     │ auditd           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Log Shippers / Forwarders                      │
│  Fluentd  │  Filebeat  │  CloudWatch Agent  │  Logstash         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Message Queue (Kafka)                         │
│  Topic: security-audit-logs                                      │
│  Retention: 90 days, Replication: 3                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          SIEM Platform                           │
│  Splunk / ELK Stack / Azure Sentinel                             │
│  - Real-time correlation                                         │
│  - Anomaly detection                                             │
│  - Alerting                                                      │
│  - Compliance reporting                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Long-Term Archive (S3 Glacier)                │
│  Retention: 7 years (FISMA requirement)                          │
│  Encryption: SSE-KMS, Object Lock (WORM)                         │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Fluentd Configuration
**Purpose**: Collect and forward logs from all services

**Configuration** (`/etc/fluent/fluent.conf`):
```xml
<source>
  @type tail
  path /var/log/postgresql/postgresql-15-audit.log
  pos_file /var/log/fluentd/postgresql-audit.pos
  tag security.postgresql
  <parse>
    @type regexp
    expression /^(?<timestamp>[^ ]+ [^ ]+) \[(?<pid>\d+)\]: user=(?<user>[^,]+),db=(?<database>[^,]+),app=(?<application>[^,]+),client=(?<client_ip>[^ ]+) (?<severity>[A-Z]+): AUDIT: (?<session_id>[^,]+),(?<object_id>[^,]+),(?<substatement_id>[^,]+),(?<operation>[^,]+),(?<command>[^,]+),(?<object_type>[^,]+),(?<object_name>[^,]+),"(?<statement>[^"]+)",(?<params>.*)$/
  </parse>
</source>

<source>
  @type tail
  path /var/log/kafka/audit/*.log
  pos_file /var/log/fluentd/kafka-audit.pos
  tag security.kafka
  <parse>
    @type json
  </parse>
</source>

<match security.**>
  @type kafka2
  brokers kafka.wildfire.internal:9093
  topic_key security-audit-logs
  default_topic security-audit-logs
  <format>
    @type json
  </format>
  <buffer>
    @type file
    path /var/log/fluentd/buffer/security
    flush_interval 10s
  </buffer>
</match>
```

### 4.3 Splunk Integration
**Purpose**: Centralized SIEM for correlation, alerting, compliance reporting

**Splunk HTTP Event Collector (HEC)**:
```bash
# Create HEC token
curl -k -u admin:password https://splunk.calfire.ca.gov:8089/servicesNS/admin/splunk_httpinput/data/inputs/http \
  -d name=wildfire-audit-hec \
  -d index=security_audit \
  -d sourcetype=_json

# Configure Fluentd to send to Splunk
<match security.**>
  @type splunk_hec
  hec_host splunk.calfire.ca.gov
  hec_port 8088
  hec_token <hec-token>
  index security_audit
  sourcetype wildfire_audit
</match>
```

**Splunk Search Examples**:
```spl
# Failed login attempts (brute force detection)
index=security_audit event_type="authentication.login.failure"
| stats count by user_id, source_ip
| where count > 5

# Sensitive data access anomalies
index=security_audit action="s3:GetObject" resource="*restricted*"
| stats count by user_id, hour
| where count > 100

# Privilege escalation detection
index=security_audit event_type="authorization.role.change"
| where new_role="admin" AND old_role!="admin"
```

---

## 5. Audit Log Retention

### 5.1 Retention Schedule

| Log Source | Hot Storage (S3 Standard) | Warm Storage (S3 IA) | Cold Storage (Glacier) | Permanent Archive |
|-----------|--------------------------|---------------------|------------------------|-------------------|
| **CloudTrail** | 90 days | 1 year | 7 years | Delete after 7y |
| **PostgreSQL Audit** | 90 days | 1 year | 7 years | Delete after 7y |
| **Kafka Audit** | 90 days | N/A | 365 days | Delete after 1y |
| **Nginx Access** | 30 days | 90 days | 365 days | Delete after 1y |
| **OS Audit (auditd)** | 90 days | 1 year | 7 years | Delete after 7y |
| **SIEM Alerts** | 365 days | N/A | 7 years | Delete after 7y |
| **Compliance Events** | 365 days | 7 years | Permanent | Never delete |

### 5.2 S3 Lifecycle Policy (Audit Logs)
```json
{
  "Rules": [
    {
      "Id": "AuditLogLifecycle",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "cloudtrail/"
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 365,
          "StorageClass": "GLACIER"
        },
        {
          "Days": 2555,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ],
      "Expiration": {
        "Days": 2555
      }
    },
    {
      "Id": "ComplianceEventsPermanent",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "compliance/"
      },
      "Transitions": [
        {
          "Days": 365,
          "StorageClass": "GLACIER"
        }
      ],
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 2555
      }
    }
  ]
}
```

### 5.3 Object Lock (WORM - Write Once Read Many)
**Purpose**: Prevent deletion or modification of audit logs (compliance requirement)

```bash
aws s3api put-object-lock-configuration \
  --bucket wildfire-audit-logs \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "GOVERNANCE",
        "Days": 2555
      }
    }
  }'
```

---

## 6. Real-Time Alerting

### 6.1 Security Alerts

| Alert Name | Condition | Severity | Action |
|-----------|-----------|----------|--------|
| **Brute Force Login** | >5 failed logins in 10 min | CRITICAL | Block IP, notify SOC |
| **Privilege Escalation** | User role changed to admin | CRITICAL | Notify CISO, freeze account |
| **Unusual Data Access** | >10,000 records accessed by single user | WARNING | Notify manager, DLP scan |
| **Encryption Disabled** | S3 bucket encryption disabled | CRITICAL | Re-enable, notify security team |
| **Key Deletion** | KMS key scheduled for deletion | CRITICAL | Cancel deletion, notify CISO |
| **Geographic Anomaly** | Login from unexpected country | WARNING | Require MFA re-auth |
| **After-Hours Access** | Access to restricted data outside 8am-5pm PT | INFO | Log for review |
| **Bulk Download** | >1 GB downloaded in 1 hour | WARNING | DLP scan, notify manager |

### 6.2 Prometheus Alerting Rules
```yaml
groups:
  - name: security_audit_alerts
    interval: 30s
    rules:
      - alert: BruteForceLogin
        expr: |
          sum(rate(authentication_failure_total[5m])) by (user_id, source_ip) > 1
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Brute force login detected: {{ $labels.user_id }} from {{ $labels.source_ip }}"
          description: "More than 5 failed login attempts detected in 10 minutes"

      - alert: UnauthorizedDataAccess
        expr: |
          sum(rate(data_access_total{classification="restricted"}[1h])) by (user_id) > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Unusual data access pattern: {{ $labels.user_id }}"
          description: "User accessed more than 10,000 restricted records in 1 hour"

      - alert: EncryptionDisabled
        expr: |
          encryption_enabled{service="s3"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Encryption disabled on {{ $labels.bucket }}"
          description: "S3 bucket encryption has been disabled, immediate action required"
```

---

## 7. Compliance Auditing

### 7.1 FISMA Continuous Monitoring
**Frequency**: Real-time + Weekly Reports

**Automated Checks**:
```bash
#!/bin/bash
# /opt/wildfire/scripts/fisma-compliance-check.sh

# Check 1: All S3 buckets encrypted
aws s3api list-buckets --query 'Buckets[*].Name' --output text | while read bucket; do
  encryption=$(aws s3api get-bucket-encryption --bucket $bucket 2>/dev/null)
  if [ -z "$encryption" ]; then
    echo "FAIL: Bucket $bucket is not encrypted"
  fi
done

# Check 2: CloudTrail enabled
trails=$(aws cloudtrail list-trails --query 'Trails[*].Name' --output text)
if [ -z "$trails" ]; then
  echo "FAIL: No CloudTrail trails configured"
fi

# Check 3: PostgreSQL audit logging enabled
psql -U wildfire_user -d wildfire_db -c "SHOW shared_preload_libraries;" | grep pgaudit
if [ $? -ne 0 ]; then
  echo "FAIL: PostgreSQL audit logging not enabled"
fi

# Check 4: TLS 1.2+ enforced
openssl s_client -connect dashboard.wildfire.calfire.ca.gov:443 -tls1_1 2>&1 | grep "no protocols available"
if [ $? -ne 0 ]; then
  echo "FAIL: TLS 1.1 is still enabled (should be disabled)"
fi
```

### 7.2 SOC 2 Type II Evidence Collection
**Frequency**: Quarterly

**Evidence Artifacts**:
1. **Access Review Report** (from access_request_workflow.md)
2. **Encryption Verification** (from encryption_plan.md)
3. **Key Rotation Log** (from key_rotation_policy.md)
4. **Audit Log Samples** (CloudTrail, PostgreSQL, Kafka)
5. **Incident Response Records** (Jira tickets, post-mortems)

**Automated Evidence Export**:
```bash
# Export last 90 days of CloudTrail logs
aws cloudtrail lookup-events \
  --start-time $(date -u -d '90 days ago' '+%Y-%m-%dT%H:%M:%S') \
  --max-results 10000 \
  --output json > /tmp/soc2-cloudtrail-evidence.json

# Export PostgreSQL audit log
psql -U wildfire_user -d wildfire_db -c "
  COPY (
    SELECT * FROM pg_log
    WHERE log_time > NOW() - INTERVAL '90 days'
    AND message LIKE '%AUDIT%'
  ) TO '/tmp/soc2-postgresql-evidence.csv' CSV HEADER;
"
```

### 7.3 CCPA Data Subject Request Auditing
**Purpose**: Track all data access/deletion requests from California residents

**Audit Procedure**:
```sql
-- Log data subject access request
INSERT INTO compliance_audit_log (
  request_id,
  request_type,
  subject_email,
  subject_ip,
  timestamp,
  data_accessed,
  compliance_regulation
) VALUES (
  'DSR-2025-10-06-001',
  'DATA_ACCESS_REQUEST',
  'user@example.com',
  '192.0.2.100',
  NOW(),
  'firms_modis_terra_detections, airnow_observations',
  'CCPA'
);

-- Log data deletion request
INSERT INTO compliance_audit_log (
  request_id,
  request_type,
  subject_email,
  deletion_timestamp,
  records_deleted,
  compliance_regulation
) VALUES (
  'DSR-2025-10-06-002',
  'DATA_DELETION_REQUEST',
  'user@example.com',
  NOW(),
  152,
  'CCPA'
);
```

---

## 8. Audit Log Analysis and Forensics

### 8.1 Common Forensic Queries

**Query 1: Identify all actions by a specific user**
```bash
# CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=analyst@calfire.ca.gov \
  --max-results 1000

# PostgreSQL
psql -c "SELECT * FROM pg_log WHERE user_name = 'analyst@calfire.ca.gov' ORDER BY log_time DESC LIMIT 100;"
```

**Query 2: Detect privilege escalation attempts**
```sql
SELECT
  timestamp,
  user_id,
  old_role,
  new_role,
  source_ip
FROM iam_audit_log
WHERE new_role = 'admin'
  AND old_role != 'admin'
  AND timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
```

**Query 3: Identify data exfiltration (bulk downloads)**
```spl
index=security_audit action="s3:GetObject"
| stats sum(file_size_bytes) as total_bytes by user_id, _time
| where total_bytes > 1073741824  # 1 GB
| convert ctime(_time) as download_time
```

### 8.2 Automated Anomaly Detection
**Machine Learning Model**: Isolation Forest (scikit-learn)

```python
from sklearn.ensemble import IsolationForest
import pandas as pd

# Load audit logs
df = pd.read_csv('/var/log/security/audit-aggregated.csv')

# Feature engineering
features = df[['login_count', 'data_access_count', 'unique_ip_count', 'hour_of_day']]

# Train model
model = IsolationForest(contamination=0.01, random_state=42)
model.fit(features)

# Predict anomalies
df['anomaly_score'] = model.decision_function(features)
df['is_anomaly'] = model.predict(features)

# Alert on anomalies
anomalies = df[df['is_anomaly'] == -1]
for idx, row in anomalies.iterrows():
    print(f"ALERT: Anomalous behavior detected for user {row['user_id']} at {row['timestamp']}")
```

---

## 9. Audit Plan Verification

### 9.1 Weekly Audit Checklist
- [ ] CloudTrail logs flowing to S3 (check last 24 hours)
- [ ] PostgreSQL audit logs rotated successfully
- [ ] Kafka audit logs forwarded to SIEM
- [ ] No unencrypted audit logs detected
- [ ] All critical alerts reviewed and closed
- [ ] Compliance events logged (CCPA/FISMA)

### 9.2 Monthly Compliance Report
```bash
#!/bin/bash
# /opt/wildfire/scripts/monthly-audit-report.sh

echo "=== CAL FIRE Wildfire Platform - Monthly Audit Report ==="
echo "Report Date: $(date)"
echo ""

# 1. Total audit events logged
echo "1. Total Audit Events (Last 30 Days):"
aws cloudtrail lookup-events --max-results 10000 --start-time $(date -u -d '30 days ago' '+%Y-%m-%dT%H:%M:%S') | jq '.Events | length'

# 2. Failed login attempts
echo "2. Failed Login Attempts:"
psql -U wildfire_user -d wildfire_db -t -c "SELECT COUNT(*) FROM pg_log WHERE message LIKE '%authentication failed%' AND log_time > NOW() - INTERVAL '30 days';"

# 3. Data access by classification
echo "3. Data Access by Classification:"
aws athena start-query-execution --query-string "
  SELECT classification, COUNT(*) as access_count
  FROM cloudtrail_logs
  WHERE eventtime > DATE_SUB(CURRENT_DATE, 30)
    AND eventname = 'GetObject'
  GROUP BY classification
" --result-configuration OutputLocation=s3://wildfire-athena-results/

# 4. Encryption compliance
echo "4. Encryption Compliance (S3 Buckets):"
aws s3api list-buckets --query 'Buckets[*].Name' --output text | while read bucket; do
  encryption=$(aws s3api get-bucket-encryption --bucket $bucket 2>/dev/null)
  if [ -z "$encryption" ]; then
    echo "  FAIL: $bucket"
  else
    echo "  PASS: $bucket"
  fi
done

# 5. Top 10 users by data access
echo "5. Top 10 Users by Data Access:"
psql -U wildfire_user -d wildfire_db -c "
  SELECT user_name, COUNT(*) as query_count
  FROM pg_log
  WHERE log_time > NOW() - INTERVAL '30 days'
    AND command_tag = 'SELECT'
  GROUP BY user_name
  ORDER BY query_count DESC
  LIMIT 10;
"
```

---

## 10. Contact Information

| Role | Contact | Responsibility |
|------|---------|---------------|
| **Security Operations Center (SOC)** | soc@calfire.ca.gov | 24/7 incident monitoring, alert response |
| **Security Audit Team** | audit@calfire.ca.gov | Compliance verification, log analysis |
| **Compliance Officer** | compliance@calfire.ca.gov | Regulatory reporting, audit coordination |
| **CISO** | ciso@calfire.ca.gov | Audit policy approval, incident escalation |

---

**Document Control**:
- **Created**: 2025-10-06
- **Last Updated**: 2025-10-06
- **Next Review**: 2026-01-06 (quarterly)
- **Approvals**:
  - CISO: [Pending]
  - SOC Manager: [Pending]
  - Compliance Officer: [Pending]
