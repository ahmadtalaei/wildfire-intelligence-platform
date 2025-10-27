# CAL FIRE Wildfire Intelligence Platform - Key Rotation Policy

**Document Version**: 1.0.0
**Effective Date**: October 2025
**Owner**: CAL FIRE Security Team
**Review Cycle**: Annual
**Compliance**: FISMA, NIST 800-53 (SC-12, SC-17), SOC2

---

## 1. Executive Summary

This document defines the cryptographic key rotation policies and procedures for the CAL FIRE Wildfire Intelligence Platform. All cryptographic keys must be rotated according to these schedules to minimize the risk of key compromise and ensure compliance with federal and state security requirements.

---

## 2. Key Rotation Schedule

### 2.1 Summary Table

| Key Type | Rotation Frequency | Automated | Compliance Requirement |
|----------|-------------------|-----------|------------------------|
| **AWS KMS Data Encryption Keys (DEK)** | 365 days | Yes | NIST 800-57 |
| **AWS KMS Master Keys (CMK)** | Never (rotate DEKs instead) | N/A | NIST 800-57 |
| **Azure Key Vault Keys** | 365 days | Yes | NIST 800-57 |
| **GCP Cloud KMS Keys** | 365 days | Yes | NIST 800-57 |
| **Database Encryption Keys (PostgreSQL TDE)** | 180 days | Yes | FISMA Moderate |
| **TLS/SSL Certificates** | 365 days (before expiry) | Yes (Let's Encrypt) | NIST 800-52 |
| **API Keys (NASA FIRMS, NOAA, USGS)** | 90 days | Manual | Internal Policy |
| **Service Account Credentials (IAM)** | 90 days | Manual | NIST 800-53 IA-5 |
| **SSH Keys (Server Access)** | 180 days | Manual | NIST 800-53 IA-5 |
| **Kafka Encryption Keys (TLS)** | 365 days | Yes | Internal Policy |
| **Redis Encryption Keys** | 180 days | Yes | Internal Policy |
| **MinIO Root Credentials** | 90 days | Manual | Internal Policy |
| **Grafana Admin Password** | 90 days | Manual | SOC2 |
| **Prometheus Credentials** | 90 days | Manual | SOC2 |

---

## 3. AWS KMS Key Rotation

### 3.1 Automatic Key Rotation (Recommended)
AWS KMS automatically rotates Customer Managed Keys (CMKs) annually when enabled.

**Enable Automatic Rotation**:
```bash
aws kms enable-key-rotation --key-id arn:aws:kms:us-west-2:123456789012:key/wildfire-data-key
```

**Verify Rotation Status**:
```bash
aws kms get-key-rotation-status --key-id arn:aws:kms:us-west-2:123456789012:key/wildfire-data-key
```

**Expected Output**:
```json
{
  "KeyRotationEnabled": true,
  "NextRotationDate": "2026-10-06T00:00:00Z"
}
```

### 3.2 Manual Key Rotation (Emergency)
In case of suspected key compromise:

1. **Create New CMK**:
```bash
aws kms create-key \
  --description "Wildfire Data Encryption Key (Emergency Rotation)" \
  --key-usage ENCRYPT_DECRYPT \
  --origin AWS_KMS \
  --tags TagKey=Environment,TagValue=Production TagKey=RotationReason,TagValue=Compromise
```

2. **Create Alias for New Key**:
```bash
aws kms create-alias \
  --alias-name alias/wildfire-data-key-v2 \
  --target-key-id <new-key-id>
```

3. **Re-encrypt Data with New Key**:
```bash
aws s3 cp s3://wildfire-data-lake/ s3://wildfire-data-lake-temp/ \
  --recursive \
  --sse aws:kms \
  --sse-kms-key-id <new-key-id>
```

4. **Update Application Configuration**:
```yaml
# infrastructure/terraform/kms.tf
resource "aws_kms_key" "wildfire_data_key_v2" {
  description             = "Wildfire Data Encryption Key V2"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}
```

5. **Schedule Old Key for Deletion**:
```bash
aws kms schedule-key-deletion --key-id <old-key-id> --pending-window-in-days 30
```

---

## 4. Azure Key Vault Key Rotation

### 4.1 Automatic Key Rotation
Azure Key Vault supports automatic key rotation for managed keys.

**Enable Automatic Rotation**:
```bash
az keyvault key rotation-policy update \
  --vault-name wildfire-keyvault \
  --name wildfire-storage-key \
  --value '{
    "lifetimeActions": [
      {
        "trigger": {"timeAfterCreate": "P365D"},
        "action": {"type": "Rotate"}
      }
    ],
    "attributes": {"expiryTime": "P730D"}
  }'
```

**Verify Rotation Policy**:
```bash
az keyvault key rotation-policy show \
  --vault-name wildfire-keyvault \
  --name wildfire-storage-key
```

### 4.2 Manual Key Rotation
1. **Create New Key Version**:
```bash
az keyvault key create \
  --vault-name wildfire-keyvault \
  --name wildfire-storage-key \
  --kty RSA \
  --size 4096 \
  --ops encrypt decrypt
```

2. **Update Application to Use New Key Version** (automatic for Key Vault-integrated services)

3. **Revoke Old Key Version**:
```bash
az keyvault key set-attributes \
  --vault-name wildfire-keyvault \
  --name wildfire-storage-key \
  --version <old-version-id> \
  --enabled false
```

---

## 5. GCP Cloud KMS Key Rotation

### 5.1 Automatic Key Rotation
GCP Cloud KMS automatically rotates keys when configured.

**Set Rotation Period (365 days)**:
```bash
gcloud kms keys update wildfire-data-key \
  --location=us-west1 \
  --keyring=wildfire-keyring \
  --rotation-period=365d \
  --next-rotation-time=2026-10-06T00:00:00Z
```

**Verify Rotation Configuration**:
```bash
gcloud kms keys describe wildfire-data-key \
  --location=us-west1 \
  --keyring=wildfire-keyring
```

### 5.2 Manual Key Rotation
1. **Create New Key Version**:
```bash
gcloud kms keys versions create \
  --location=us-west1 \
  --keyring=wildfire-keyring \
  --key=wildfire-data-key
```

2. **Set New Version as Primary**:
```bash
gcloud kms keys set-primary-version \
  --location=us-west1 \
  --keyring=wildfire-keyring \
  --key=wildfire-data-key \
  --version=<new-version-id>
```

3. **Disable Old Version**:
```bash
gcloud kms keys versions disable <old-version-id> \
  --location=us-west1 \
  --keyring=wildfire-keyring \
  --key=wildfire-data-key
```

---

## 6. Database Encryption Key Rotation

### 6.1 PostgreSQL Transparent Data Encryption (TDE)
**Rotation Frequency**: 180 days

**Procedure**:
1. **Generate New Encryption Key**:
```bash
openssl rand -base64 32 > /etc/postgresql/tde_key_v2.key
chmod 600 /etc/postgresql/tde_key_v2.key
```

2. **Update PostgreSQL Configuration**:
```sql
-- Enable new encryption key
ALTER SYSTEM SET ssl_key_file = '/etc/postgresql/tde_key_v2.key';
SELECT pg_reload_conf();
```

3. **Re-encrypt Tablespaces** (PostgreSQL 15+):
```sql
ALTER TABLESPACE pg_default SET (encryption_key = '/etc/postgresql/tde_key_v2.key');
VACUUM FULL;
```

4. **Verify Encryption**:
```sql
SELECT datname, pg_size_pretty(pg_database_size(datname)) AS size
FROM pg_database
WHERE datname = 'wildfire_db';
```

### 6.2 Redis Encryption Key Rotation
**Rotation Frequency**: 180 days

**Procedure**:
1. **Generate New TLS Certificate**:
```bash
openssl req -x509 -newkey rsa:4096 -keyout redis_key_v2.pem -out redis_cert_v2.pem -days 365 -nodes
```

2. **Update Redis Configuration**:
```bash
# /etc/redis/redis.conf
tls-cert-file /etc/redis/redis_cert_v2.pem
tls-key-file /etc/redis/redis_key_v2.pem
tls-ca-cert-file /etc/redis/ca.pem
```

3. **Restart Redis with New Keys**:
```bash
systemctl restart redis
```

---

## 7. API Key Rotation

### 7.1 External API Keys (NASA FIRMS, NOAA, USGS)
**Rotation Frequency**: 90 days

**Procedure**:
1. **Request New API Key from Provider**:
   - NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/api/
   - NOAA: https://www.weather.gov/api/
   - USGS EarthExplorer: https://ers.cr.usgs.gov/register/

2. **Update AWS Secrets Manager**:
```bash
aws secretsmanager update-secret \
  --secret-id wildfire/nasa-firms-api-key \
  --secret-string '{"api_key":"<new-key>"}'
```

3. **Verify Application Picks Up New Key** (automatic refresh every 5 minutes)

4. **Test API Connectivity**:
```bash
curl -H "Authorization: Bearer <new-key>" \
  "https://firms.modaps.eosdis.nasa.gov/api/country/csv/..."
```

5. **Revoke Old API Key** (after 7-day grace period)

### 7.2 Service Account Credentials
**Rotation Frequency**: 90 days

**AWS IAM Access Keys**:
```bash
# Create new access key
aws iam create-access-key --user-name data-ingestion-service

# Update application configuration (Kubernetes secret)
kubectl create secret generic aws-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=<new-key> \
  --from-literal=AWS_SECRET_ACCESS_KEY=<new-secret> \
  --dry-run=client -o yaml | kubectl apply -f -

# Delete old access key (after 7-day grace period)
aws iam delete-access-key --user-name data-ingestion-service --access-key-id <old-key>
```

**Azure Service Principal**:
```bash
# Create new client secret
az ad sp credential reset --id <app-id> --years 1

# Update Key Vault secret
az keyvault secret set \
  --vault-name wildfire-keyvault \
  --name azure-sp-secret \
  --value "<new-secret>"
```

**GCP Service Account Key**:
```bash
# Create new key
gcloud iam service-accounts keys create new-key.json \
  --iam-account=data-ingestion@wildfire-project.iam.gserviceaccount.com

# Update Kubernetes secret
kubectl create secret generic gcp-credentials \
  --from-file=key.json=new-key.json \
  --dry-run=client -o yaml | kubectl apply -f -

# Delete old key
gcloud iam service-accounts keys delete <old-key-id> \
  --iam-account=data-ingestion@wildfire-project.iam.gserviceaccount.com
```

---

## 8. TLS/SSL Certificate Rotation

### 8.1 Let's Encrypt Certificates (Automatic)
**Rotation Frequency**: 90 days (auto-renew at 60 days)

**Verify Auto-Renewal**:
```bash
certbot renew --dry-run
```

**Manual Renewal (if needed)**:
```bash
certbot renew --force-renewal
systemctl reload nginx
```

### 8.2 Internal CA Certificates
**Rotation Frequency**: 365 days

**Generate New Certificate**:
```bash
openssl req -x509 -newkey rsa:4096 \
  -keyout wildfire-internal-ca-v2.key \
  -out wildfire-internal-ca-v2.crt \
  -days 365 -nodes \
  -subj "/C=US/ST=California/L=Sacramento/O=CAL FIRE/CN=wildfire-internal-ca"
```

**Deploy to All Services**:
```bash
# Update Nginx
cp wildfire-internal-ca-v2.crt /etc/nginx/ssl/
cp wildfire-internal-ca-v2.key /etc/nginx/ssl/
nginx -s reload

# Update Kafka
cp wildfire-internal-ca-v2.crt /etc/kafka/ssl/
systemctl restart kafka

# Update Docker containers
docker secret create wildfire-tls-cert-v2 wildfire-internal-ca-v2.crt
docker service update --secret-rm wildfire-tls-cert --secret-add wildfire-tls-cert-v2 data-ingestion-service
```

---

## 9. SSH Key Rotation

### 9.1 Server SSH Host Keys
**Rotation Frequency**: 180 days

**Generate New Host Keys**:
```bash
ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key_v2 -N ""
ssh-keygen -t rsa -b 4096 -f /etc/ssh/ssh_host_rsa_key_v2 -N ""
```

**Update SSH Configuration**:
```bash
# /etc/ssh/sshd_config
HostKey /etc/ssh/ssh_host_ed25519_key_v2
HostKey /etc/ssh/ssh_host_rsa_key_v2
```

**Restart SSH**:
```bash
systemctl restart sshd
```

**Notify Users of New Host Key Fingerprints**:
```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key_v2.pub
```

### 9.2 User SSH Keys (Administrative Access)
**Rotation Frequency**: 180 days

**User Self-Service Rotation**:
```bash
# Generate new key pair
ssh-keygen -t ed25519 -C "user@calfire.ca.gov" -f ~/.ssh/id_ed25519_v2

# Add new public key to servers
ssh-copy-id -i ~/.ssh/id_ed25519_v2.pub user@wildfire-server.calfire.ca.gov

# Test new key
ssh -i ~/.ssh/id_ed25519_v2 user@wildfire-server.calfire.ca.gov

# Remove old key from servers (after verification)
ssh user@wildfire-server.calfire.ca.gov "sed -i '/old-key-comment/d' ~/.ssh/authorized_keys"
```

---

## 10. Application Credentials Rotation

### 10.1 MinIO Root Credentials
**Rotation Frequency**: 90 days

**Procedure**:
1. **Generate New Credentials**:
```bash
export MINIO_ROOT_USER="admin_v2"
export MINIO_ROOT_PASSWORD=$(openssl rand -base64 32)
```

2. **Update MinIO Configuration**:
```bash
mc admin user add wildfire-minio $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
mc admin policy set wildfire-minio consoleAdmin user=$MINIO_ROOT_USER
```

3. **Update Application Configuration**:
```bash
kubectl create secret generic minio-credentials \
  --from-literal=MINIO_ROOT_USER=$MINIO_ROOT_USER \
  --from-literal=MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD \
  --dry-run=client -o yaml | kubectl apply -f -
```

4. **Disable Old Credentials**:
```bash
mc admin user disable wildfire-minio admin_v1
```

### 10.2 Grafana Admin Password
**Rotation Frequency**: 90 days

**Procedure**:
1. **Change Password via CLI**:
```bash
grafana-cli admin reset-admin-password <new-secure-password>
```

2. **Update Kubernetes Secret**:
```bash
kubectl create secret generic grafana-admin \
  --from-literal=admin-password=<new-secure-password> \
  --dry-run=client -o yaml | kubectl apply -f -
```

3. **Force Pod Restart**:
```bash
kubectl rollout restart deployment/grafana
```

### 10.3 Prometheus Credentials
**Rotation Frequency**: 90 days

**Procedure**:
1. **Generate New Basic Auth Password**:
```bash
htpasswd -nBC 10 prometheus > /etc/prometheus/web.yml
```

2. **Update Prometheus Configuration**:
```yaml
# /etc/prometheus/prometheus.yml
basic_auth_users:
  prometheus: <bcrypt-hash>
```

3. **Restart Prometheus**:
```bash
systemctl restart prometheus
```

---

## 11. Key Rotation Automation

### 11.1 Automated Rotation Script (Example)
```bash
#!/bin/bash
# /opt/wildfire/scripts/rotate_keys.sh

set -euo pipefail

# Rotate AWS Secrets Manager API Keys
rotate_api_keys() {
  echo "Rotating NASA FIRMS API Key..."
  # API key rotation logic here
}

# Rotate PostgreSQL Encryption Keys
rotate_db_keys() {
  echo "Rotating PostgreSQL TDE Keys..."
  # Database encryption key rotation logic here
}

# Rotate MinIO Credentials
rotate_minio() {
  echo "Rotating MinIO Root Credentials..."
  # MinIO credential rotation logic here
}

# Main
main() {
  rotate_api_keys
  rotate_db_keys
  rotate_minio
  echo "Key rotation completed at $(date)"
}

main "$@"
```

### 11.2 Scheduled Rotation (Cron)
```cron
# /etc/cron.d/wildfire-key-rotation

# Rotate API keys every 90 days (first Sunday of quarter at 2 AM)
0 2 1 1,4,7,10 * /opt/wildfire/scripts/rotate_keys.sh >> /var/log/wildfire/key-rotation.log 2>&1

# Rotate database keys every 180 days (first Sunday of June and December at 3 AM)
0 3 1 6,12 * /opt/wildfire/scripts/rotate_db_keys.sh >> /var/log/wildfire/key-rotation.log 2>&1

# Rotate TLS certificates (Let's Encrypt auto-renews, just verify)
0 4 1 * * certbot renew --quiet >> /var/log/wildfire/cert-renewal.log 2>&1
```

---

## 12. Key Compromise Response

### 12.1 Immediate Actions (within 1 hour)
1. **Revoke Compromised Key Immediately**:
```bash
aws kms disable-key --key-id <compromised-key-id>
```

2. **Rotate to New Key**:
```bash
aws kms enable-key-rotation --key-id <new-key-id>
```

3. **Audit All Access Logs**:
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<compromised-key-id> \
  --start-time $(date -u -d '7 days ago' '+%Y-%m-%dT%H:%M:%S') \
  --max-results 1000
```

4. **Notify Security Team**:
   - Email: security@calfire.ca.gov
   - Phone: +1-916-555-FIRE (3473)
   - Slack: #security-incidents

### 12.2 Forensic Investigation (within 24 hours)
1. Export CloudTrail logs for analysis
2. Identify unauthorized access patterns
3. Re-encrypt all data accessed with compromised key
4. Review IAM policies and access controls

### 12.3 Post-Incident Actions (within 7 days)
1. Update incident response playbook
2. Conduct lessons learned review
3. Implement additional controls (MFA, IP whitelisting)
4. Report to compliance officer (FISMA requirement)

---

## 13. Monitoring and Alerting

### 13.1 Key Rotation Metrics
- **Grafana Dashboard**: "Cryptographic Key Health"
- **Metrics**:
  - Days until key expiration
  - Last rotation timestamp
  - Failed rotation attempts

### 13.2 Alerts
- **Alert**: Key expiring in 30 days (warning)
- **Alert**: Key expiring in 7 days (critical)
- **Alert**: Key rotation failure (critical)
- **Alert**: Unauthorized key access detected (critical)

### 13.3 Audit Logging
All key rotation events logged to:
- AWS CloudTrail
- Azure Activity Log
- GCP Cloud Audit Logs
- Syslog (local servers)
- Splunk/ELK (SIEM)

---

## 14. Compliance Verification

### 14.1 Quarterly Key Rotation Audit
- **Schedule**: First week of each quarter
- **Process**:
  1. Export key rotation report from KMS
  2. Verify all keys rotated within policy timeframe
  3. Identify exceptions and create remediation plan
  4. Report to CISO and compliance officer

### 14.2 Annual Compliance Certification
- **Requirement**: FISMA, SOC 2 Type II
- **Evidence Required**:
  - Key rotation logs (12 months)
  - Incident response records
  - Policy review sign-offs
  - Penetration test results

---

## 15. Contact Information

| Role | Contact | Responsibility |
|------|---------|---------------|
| **Security Team** | security@calfire.ca.gov | Key rotation execution, incident response |
| **Operations Team** | ops@calfire.ca.gov | Automated rotation scripts, monitoring |
| **Compliance Officer** | compliance@calfire.ca.gov | Audit verification, regulatory reporting |
| **CISO** | ciso@calfire.ca.gov | Policy approval, exception handling |

---

**Document Control**:
- **Created**: 2025-10-06
- **Last Updated**: 2025-10-06
- **Next Review**: 2026-10-06
- **Approvals**:
  - CISO: [Pending]
  - Security Team Lead: [Pending]
  - Compliance Officer: [Pending]
