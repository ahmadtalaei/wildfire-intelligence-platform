# CAL FIRE Wildfire Intelligence Platform - Disaster Recovery Failover Runbook

**Document Version**: 1.0.0
**Last Updated**: October 2025
**Owner**: CAL FIRE Operations Team
**RTO (Recovery Time Objective)**: 4 hours
**RPO (Recovery Point Objective)**: 15 minutes

---

## 1. Executive Summary

This runbook provides step-by-step procedures for disaster recovery failover of the CAL FIRE Wildfire Intelligence Platform storage infrastructure. It covers PostgreSQL failover, S3 replication, MinIO disaster recovery, and full system recovery procedures.

**Critical Contacts**:
- **Operations Lead**: +1-916-555-FIRE (3473)
- **Database Administrator**: dba@calfire.ca.gov
- **Security Team**: security@calfire.ca.gov
- **AWS Support**: (Premium Support) 1-800-AWSHELP

---

## 2. Failover Scenarios

| Scenario | Impact | RTO | RPO | Procedure |
|----------|--------|-----|-----|-----------|
| **PostgreSQL Primary Failure** | Write operations fail | 30 minutes | 5 minutes | Section 3 |
| **S3 Region Outage** | Hot/Warm tier inaccessible | 2 hours | 15 minutes | Section 4 |
| **MinIO Cluster Failure** | On-prem storage unavailable | 1 hour | 5 minutes | Section 5 |
| **Complete Data Center Outage** | All on-prem services down | 4 hours | 15 minutes | Section 6 |
| **Corruption/Ransomware** | Data integrity compromised | 8 hours | Point-in-time restore | Section 7 |

---

## 3. PostgreSQL Failover (Primary → Read Replica)

### 3.1 Symptoms of PostgreSQL Primary Failure
- ✅ **Check 1**: Connection timeouts to primary (wildfire-postgres:5432)
- ✅ **Check 2**: Grafana dashboard shows "PostgreSQL Down" alert
- ✅ **Check 3**: Prometheus metric `pg_up{instance="wildfire-postgres"}` == 0
- ✅ **Check 4**: Application logs show `psycopg2.OperationalError: could not connect to server`

### 3.2 Pre-Failover Verification
```bash
# Step 1: Verify read replicas are healthy
psql -h wildfire-postgres-replica-1 -U wildfire_user -d wildfire_db -c "SELECT pg_is_in_recovery();"
# Expected output: t (true = replica mode)

# Step 2: Check replication lag
psql -h wildfire-postgres-replica-1 -U wildfire_user -d wildfire_db -c "
  SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds;
"
# Expected output: < 5 seconds

# Step 3: Verify data consistency
psql -h wildfire-postgres-replica-1 -U wildfire_user -d wildfire_db -c "
  SELECT COUNT(*) FROM firms_modis_terra_detections WHERE created_at > NOW() - INTERVAL '1 hour';
"
# Compare with known count from Prometheus
```

### 3.3 Promote Read Replica to Primary

**WARNING**: This is a destructive operation. Old primary cannot be re-added without full resync.

```bash
# Step 1: SSH into replica server
ssh admin@wildfire-postgres-replica-1

# Step 2: Promote replica to primary
sudo su - postgres
pg_ctl promote -D /var/lib/postgresql/15/main

# Expected output: "server promoting"

# Step 3: Verify promotion succeeded
psql -c "SELECT pg_is_in_recovery();"
# Expected output: f (false = primary mode)

# Step 4: Verify write operations work
psql -d wildfire_db -c "CREATE TABLE failover_test (id SERIAL, test_time TIMESTAMP DEFAULT NOW());"
psql -d wildfire_db -c "INSERT INTO failover_test VALUES (DEFAULT);"
psql -d wildfire_db -c "SELECT * FROM failover_test;"
# Should show inserted row

# Step 5: Drop test table
psql -d wildfire_db -c "DROP TABLE failover_test;"
```

### 3.4 Update Application Configuration

**Docker Compose** (`docker-compose.yml`):
```yaml
# Update POSTGRES_HOST environment variable
services:
  data-storage-service:
    environment:
      - POSTGRES_HOST=wildfire-postgres-replica-1  # Changed from wildfire-postgres
      - POSTGRES_PORT=5432
```

**Restart affected services**:
```bash
docker-compose restart data-storage-service
docker-compose restart data-ingestion-service
```

### 3.5 Verify Service Recovery
```bash
# Check service health
curl http://localhost:8001/health
# Expected: {"status": "healthy", "database": "connected"}

# Check Grafana dashboard
# Navigate to Challenge 1 Dashboard
# Verify "Data Ingestion Rate" panel shows traffic

# Check PostgreSQL logs
docker logs data-storage-service | tail -50
# Should not show connection errors
```

### 3.6 Post-Failover Actions
- ✅ **Update DNS** (if using Route 53): Point `wildfire-postgres.calfire.ca.gov` to new primary
- ✅ **Update monitoring**: Update Prometheus scrape config with new target
- ✅ **Rebuild old primary**: Re-provision failed server as new replica
- ✅ **Document incident**: Create Jira ticket with timeline and root cause

**Estimated Recovery Time**: **30 minutes**
**Estimated Data Loss**: **< 5 minutes** (replication lag)

---

## 4. S3 Cross-Region Failover (us-west-2 → us-east-1)

### 4.1 Symptoms of S3 Region Outage
- ✅ **Check 1**: AWS Status Dashboard shows us-west-2 outage
- ✅ **Check 2**: S3 API returns `503 Service Unavailable`
- ✅ **Check 3**: Grafana shows "S3 Request Errors" spike
- ✅ **Check 4**: Application logs show `boto3.exceptions.S3UploadFailedError`

### 4.2 Verify Replica Bucket Status
```bash
# Check replica bucket health
aws s3api head-bucket \
  --bucket wildfire-data-lake-replica-production \
  --region us-east-1

# Check replication status
aws s3api get-bucket-replication \
  --bucket wildfire-data-lake-production \
  --region us-west-2

# List recent objects in replica
aws s3 ls s3://wildfire-data-lake-replica-production/internal/firms/ \
  --region us-east-1 \
  --recursive \
  --human-readable \
  --summarize | head -20
```

### 4.3 Failover to Replica Bucket

**Update Application Configuration**:
```python
# services/data-storage-service/src/config.py

# Change S3 bucket and region
S3_BUCKET = "wildfire-data-lake-replica-production"  # Changed from wildfire-data-lake-production
S3_REGION = "us-east-1"  # Changed from us-west-2

# Update boto3 client
s3_client = boto3.client('s3', region_name='us-east-1')
```

**Restart Services**:
```bash
kubectl rollout restart deployment/data-storage-service
kubectl rollout restart deployment/data-ingestion-service

# Verify pods restarted
kubectl get pods -l app=data-storage-service
```

### 4.4 Update Route 53 DNS (Optional)
```bash
# If using S3 website endpoint, update Route 53 to point to replica
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "data-lake.wildfire.calfire.ca.gov",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [
          {"Value": "wildfire-data-lake-replica-production.s3-website-us-east-1.amazonaws.com"}
        ]
      }
    }]
  }'
```

### 4.5 Verify Recovery
```bash
# Test S3 write
echo "failover-test-$(date +%s)" > /tmp/failover-test.txt
aws s3 cp /tmp/failover-test.txt s3://wildfire-data-lake-replica-production/test/failover-test.txt --region us-east-1

# Test S3 read
aws s3 cp s3://wildfire-data-lake-replica-production/test/failover-test.txt /tmp/failover-test-retrieved.txt --region us-east-1

# Verify content matches
diff /tmp/failover-test.txt /tmp/failover-test-retrieved.txt
# Should show no differences

# Check application health
curl http://localhost:8001/health
# Expected: {"status": "healthy", "s3": "connected"}
```

### 4.6 Post-Failover Actions
- ✅ **Monitor replication lag**: Once us-west-2 recovers, verify replication catches up
- ✅ **Fail back to primary**: Once us-west-2 is stable for 24+ hours, reverse failover
- ✅ **Update incident log**: Document outage duration and impact

**Estimated Recovery Time**: **2 hours**
**Estimated Data Loss**: **< 15 minutes** (replication lag + DNS TTL)

---

## 5. MinIO Cluster Failover

### 5.1 Symptoms of MinIO Failure
- ✅ **Check 1**: MinIO console (http://wildfire-minio:9001) unreachable
- ✅ **Check 2**: `mc admin info wildfire-minio` returns connection error
- ✅ **Check 3**: Grafana shows "MinIO Down" alert
- ✅ **Check 4**: Application logs show `minio.error.ServerError`

### 5.2 Check MinIO Cluster Status
```bash
# Check individual nodes
for node in minio-node-{1..4}; do
  echo "Checking $node..."
  mc admin info wildfire-minio/$node || echo "FAILED: $node"
done

# Check disk health
mc admin heal wildfire-minio --recursive --dry-run

# Check replication status
mc stat wildfire-minio/wildfire-hot-tier/firms/2025/10/06/
```

### 5.3 Restart Failed MinIO Nodes
```bash
# Restart individual node
ssh admin@minio-node-1
sudo systemctl restart minio

# Verify node rejoined cluster
mc admin info wildfire-minio

# Check healing status
mc admin heal wildfire-minio --recursive
```

### 5.4 Full Cluster Restart (Last Resort)
```bash
# Stop all nodes in reverse order
for node in minio-node-{4..1}; do
  ssh admin@$node "sudo systemctl stop minio"
  sleep 5
done

# Start all nodes in forward order
for node in minio-node-{1..4}; do
  ssh admin@$node "sudo systemctl start minio"
  sleep 10
done

# Verify cluster health
mc admin info wildfire-minio
```

### 5.5 Failover to S3 (If MinIO Unrecoverable)
```python
# Update application to bypass MinIO and write directly to S3
# services/data-storage-service/src/config.py

USE_MINIO = False  # Changed from True
S3_ENDPOINT = None  # Changed from http://wildfire-minio:9000
```

**Restart Services**:
```bash
kubectl rollout restart deployment/data-storage-service
```

### 5.6 Verify Recovery
```bash
# Test MinIO write
echo "minio-failover-test-$(date +%s)" > /tmp/minio-test.txt
mc cp /tmp/minio-test.txt wildfire-minio/wildfire-hot-tier/test/minio-test.txt

# Test MinIO read
mc cat wildfire-minio/wildfire-hot-tier/test/minio-test.txt

# Check cluster status
mc admin info wildfire-minio
# All nodes should show "online"
```

**Estimated Recovery Time**: **1 hour**
**Estimated Data Loss**: **< 5 minutes** (in-memory buffer)

---

## 6. Complete Data Center Failover (On-Prem → Cloud)

### 6.1 Disaster Scenario: California Wildfire Destroys Data Center

**Trigger Criteria**:
- Primary data center offline > 2 hours
- No ETA for recovery
- Critical fire intelligence operations must continue

### 6.2 Emergency Failover Procedure

**Phase 1: Activate AWS DR Environment** (30 minutes)
```bash
# 1. Deploy PostgreSQL on RDS (pre-provisioned standby)
aws rds start-db-instance --db-instance-identifier wildfire-postgres-dr

# Wait for availability
aws rds wait db-instance-available --db-instance-identifier wildfire-postgres-dr

# 2. Restore latest snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier wildfire-postgres-dr-restore \
  --db-snapshot-identifier wildfire-postgres-snapshot-latest

# 3. Update connection strings
export POSTGRES_HOST=$(aws rds describe-db-instances \
  --db-instance-identifier wildfire-postgres-dr \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo $POSTGRES_HOST  # e.g., wildfire-postgres-dr.abc123.us-west-2.rds.amazonaws.com
```

**Phase 2: Deploy Application on AWS EKS** (1 hour)
```bash
# 1. Deploy Kubernetes cluster (pre-provisioned)
kubectl config use-context wildfire-eks-dr

# 2. Deploy services
kubectl apply -f kubernetes/dr/data-storage-service.yaml
kubectl apply -f kubernetes/dr/data-ingestion-service.yaml
kubectl apply -f kubernetes/dr/grafana.yaml

# 3. Verify deployments
kubectl get pods --namespace wildfire-dr
# All pods should be "Running"
```

**Phase 3: Update DNS and Traffic Routing** (30 minutes)
```bash
# Update Route 53 to point to EKS load balancer
EKS_LB=$(kubectl get svc data-ingestion-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.wildfire.calfire.ca.gov",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{"Value": "'$EKS_LB'"}]
      }
    }]
  }'

# Wait for DNS propagation (1-5 minutes)
dig api.wildfire.calfire.ca.gov +short
```

**Phase 4: Verify Full System Recovery** (30 minutes)
```bash
# 1. Test data ingestion
curl -X POST https://api.wildfire.calfire.ca.gov/v1/ingest/firms \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.5,
    "longitude": -121.5,
    "brightness": 320.0,
    "frp": 4.5,
    "satellite": "Terra",
    "timestamp": "'$(date -Iseconds)'"
  }'

# Expected: {"status": "success", "id": "..."}

# 2. Query latest fire detections
curl https://api.wildfire.calfire.ca.gov/v1/query/firms?limit=10

# 3. Check Grafana dashboard
open https://dashboard.wildfire.calfire.ca.gov

# 4. Verify all panels showing data
```

### 6.3 Fallback Plan (If DR Fails)
If AWS DR environment fails, fall back to manual operations:

1. **Fire Chief Dashboard**: Use NOAA website directly (https://fire.airnow.gov)
2. **Fire Detection**: Monitor NASA FIRMS website (https://firms.modaps.eosdis.nasa.gov)
3. **Weather Data**: Use NOAA NWS website (https://www.weather.gov)
4. **Communication**: Use phone/email (no automated alerts)

**Estimated Recovery Time**: **4 hours** (full DR)
**Estimated Data Loss**: **< 15 minutes** (last database backup)

---

## 7. Data Corruption / Ransomware Recovery

### 7.1 Symptoms of Data Corruption
- ✅ **Check 1**: Checksums don't match (SHA-256 verification fails)
- ✅ **Check 2**: Unexpected file modifications in S3 (versioning shows unauthorized changes)
- ✅ **Check 3**: Database queries return corrupted results
- ✅ **Check 4**: Ransomware note found on servers

### 7.2 Immediate Actions (Incident Response)
```bash
# STEP 1: ISOLATE AFFECTED SYSTEMS
# Disconnect from network to prevent spread
sudo iptables -A INPUT -j DROP
sudo iptables -A OUTPUT -j DROP

# STEP 2: PRESERVE EVIDENCE
# Take filesystem snapshot for forensics
sudo dd if=/dev/sda of=/mnt/external/evidence.img bs=4M status=progress

# STEP 3: NOTIFY SECURITY TEAM
# Send encrypted email to security@calfire.ca.gov with PGP key
echo "DATA CORRUPTION DETECTED - Initiating recovery from backup" | \
  gpg --encrypt --recipient security@calfire.ca.gov | \
  mail -s "CRITICAL: Ransomware Incident" security@calfire.ca.gov

# STEP 4: ACTIVATE INCIDENT RESPONSE PLAN
# Contact FBI Cyber Division: 1-800-CALL-FBI
```

### 7.3 Point-in-Time Recovery (PostgreSQL)
```bash
# Restore from last known good backup
pg_restore \
  --host=wildfire-postgres \
  --port=5432 \
  --username=wildfire_user \
  --dbname=wildfire_db \
  --clean \
  --if-exists \
  --verbose \
  /backups/postgresql/wildfire_db_20251006_020000.dump

# Verify restoration
psql -h wildfire-postgres -U wildfire_user -d wildfire_db -c "
  SELECT COUNT(*) FROM firms_modis_terra_detections WHERE created_at < '2025-10-06 02:00:00';
"
```

### 7.4 S3 Object Versioning Recovery
```bash
# List all versions of corrupted object
aws s3api list-object-versions \
  --bucket wildfire-data-lake-production \
  --prefix internal/firms/2025/10/06/data.json

# Restore previous version
aws s3api copy-object \
  --bucket wildfire-data-lake-production \
  --copy-source wildfire-data-lake-production/internal/firms/2025/10/06/data.json?versionId=<previous-version-id> \
  --key internal/firms/2025/10/06/data.json
```

### 7.5 Verify Data Integrity
```bash
# Run checksum verification
find /data -type f -exec sha256sum {} \; > /tmp/checksums.txt

# Compare with known good checksums
diff /tmp/checksums.txt /backups/checksums_20251006.txt

# Verify database consistency
vacuumdb --analyze --verbose --all
```

**Estimated Recovery Time**: **8 hours** (forensic investigation + restoration)
**Estimated Data Loss**: **Point-in-time to last backup** (up to 24 hours)

---

## 8. Failover Testing Schedule

### 8.1 Monthly Drills
- **First Monday of Month**: PostgreSQL failover test (non-production hours)
- **Second Monday of Month**: S3 cross-region failover test
- **Third Monday of Month**: MinIO cluster restart test
- **Fourth Monday of Month**: Full DR simulation (AWS EKS deployment)

### 8.2 Test Checklist
- [ ] Document start time
- [ ] Execute failover procedure
- [ ] Measure actual RTO/RPO
- [ ] Document any deviations from runbook
- [ ] Update runbook based on lessons learned
- [ ] Present results to leadership

---

## 9. Contact Information

| Role | Name | Contact | Hours |
|------|------|---------|-------|
| **Operations Lead** | On-Call | +1-916-555-FIRE (3473) | 24/7 |
| **Database Administrator** | DBA Team | dba@calfire.ca.gov | 24/7 |
| **Security Team** | SOC | security@calfire.ca.gov | 24/7 |
| **AWS Support** | Premium Support | 1-800-AWS-HELP | 24/7 |
| **Network Team** | NetOps | netops@calfire.ca.gov | M-F 8am-5pm PT |
| **CISO** | Chief Security Officer | ciso@calfire.ca.gov | Business hours |

---

## 10. Post-Incident Reporting

After any failover event, create incident report with:
- **Timeline**: Minute-by-minute chronology
- **Root Cause**: What triggered the failure
- **Impact**: Services affected, users impacted, data loss
- **Recovery Actions**: Steps taken to restore service
- **Lessons Learned**: What went well, what needs improvement
- **Action Items**: Runbook updates, infrastructure improvements

**Template**: `docs/incident_reports/YYYY-MM-DD_failover_incident.md`

---

**Document Control**:
- **Created**: 2025-10-06
- **Last Tested**: [Pending - Schedule first drill]
- **Next Review**: 2025-11-06 (monthly)
- **Version History**: v1.0.0 (Initial release)
