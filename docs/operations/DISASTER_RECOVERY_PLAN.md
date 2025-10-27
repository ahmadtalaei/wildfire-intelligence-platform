# 🚨 Disaster Recovery Plan - Wildfire Intelligence Platform

## Executive Summary

This document outlines the disaster recovery (DR) procedures for the Wildfire Intelligence Platform, ensuring business continuity during system failures, data corruption, or infrastructure outages.

**Recovery Objectives:**
- **RTO (Recovery Time Objective)**: 4 hours for critical services
- **RPO (Recovery Point Objective)**: 15 minutes for real-time data, 1 hour for historical data

---

## 📋 Table of Contents

1. [Backup Strategy](#backup-strategy)
2. [Recovery Procedures](#recovery-procedures)
3. [Failover Scenarios](#failover-scenarios)
4. [Data Restoration](#data-restoration)
5. [Communication Plan](#communication-plan)
6. [Testing Schedule](#testing-schedule)

---

## 1. Backup Strategy

### 1.1 PostgreSQL Database Backups

**Automated Backups:**
```bash
# Daily full backup (via cron at 02:00 UTC)
0 2 * * * /usr/local/bin/pg_dump -h postgres -U wildfire_user wildfire_db | gzip > /backups/postgres/wildfire_db_$(date +\%Y\%m\%d).sql.gz

# Hourly WAL archiving for Point-in-Time Recovery
*/60 * * * * /usr/local/bin/pg_basebackup -h postgres -D /backups/postgres/wal_archive -Ft -z -P
```

**Retention Policy:**
- Daily backups: 30 days
- Weekly backups: 6 months
- Monthly backups: 7 years (compliance)

**Backup Locations:**
1. Primary: Local disk (`/backups/postgres/`)
2. Secondary: MinIO bucket (`s3://wildfire-backups/postgres/`)
3. Tertiary: Cloud S3 (AWS/Azure for off-site)

### 1.2 Metadata Catalog Backups

```sql
-- Automated PostgreSQL backup job
CREATE OR REPLACE FUNCTION backup_metadata_catalog()
RETURNS void AS $$
BEGIN
    -- Export critical tables
    COPY data_catalog TO '/backups/metadata/data_catalog.csv' CSV HEADER;
    COPY storage_metrics TO '/backups/metadata/storage_metrics.csv' CSV HEADER;
    COPY data_lineage TO '/backups/metadata/data_lineage.csv' CSV HEADER;
    COPY satellite_scenes TO '/backups/metadata/satellite_scenes.csv' CSV HEADER;

    RAISE NOTICE 'Metadata catalog backup completed';
END;
$$ LANGUAGE plpgsql;

-- Schedule via pg_cron
SELECT cron.schedule('metadata-backup', '0 3 * * *', 'SELECT backup_metadata_catalog()');
```

### 1.3 MinIO Object Storage Backups

**Replication Strategy:**
```yaml
# MinIO replication to secondary region
mc admin replicate add minio/wildfire-data \
  --remote-bucket wildfire-data-replica \
  --priority 1 \
  --path "fires/*,weather/*,sensors/*"
```

**Versioning:**
```bash
# Enable versioning for all buckets
mc version enable minio/wildfire-data
mc version enable minio/wildfire-backups
mc version enable minio/wildfire-models
```

### 1.4 Kafka Topics Backup

**Mirror Maker 2 Configuration:**
```properties
# Replicate critical topics to DR cluster
clusters = source, dr
source.bootstrap.servers = kafka:9092
dr.bootstrap.servers = kafka-dr:9092

source->dr.enabled = true
source->dr.topics = wildfire-fire-detections, wildfire-weather, wildfire-alerts-high

replication.factor = 3
offset.sync.interval.ms = 30000
```

### 1.5 Airflow DAG Backups

**Git-based Version Control:**
```bash
# Automated commit and push of DAG changes
#!/bin/bash
cd /opt/airflow/dags
git add .
git commit -m "Automated DAG backup $(date +%Y-%m-%d)"
git push origin main
```

---

## 2. Recovery Procedures

### 2.1 PostgreSQL Database Recovery

#### Scenario 1: Full Database Restore

```bash
# 1. Stop application services
docker-compose stop data-ingestion-service data-storage-service

# 2. Drop existing database
psql -h postgres -U postgres -c "DROP DATABASE wildfire_db;"

# 3. Restore from latest backup
gunzip -c /backups/postgres/wildfire_db_20251008.sql.gz | psql -h postgres -U wildfire_user -d wildfire_db

# 4. Restart services
docker-compose start data-ingestion-service data-storage-service
```

#### Scenario 2: Point-in-Time Recovery (PITR)

```bash
# Restore to specific timestamp (e.g., before data corruption)
pg_basebackup -h postgres -D /var/lib/postgresql/data_restored -R

# Create recovery.conf
cat > /var/lib/postgresql/data_restored/recovery.conf <<EOF
restore_command = 'cp /backups/postgres/wal_archive/%f %p'
recovery_target_time = '2025-10-08 14:30:00'
recovery_target_action = 'promote'
EOF

# Start PostgreSQL with restored data
docker-compose up -d postgres
```

### 2.2 MinIO Data Recovery

#### Restore from Snapshot

```bash
# 1. List available snapshots
mc admin snapshot list minio/

# 2. Restore from specific snapshot
mc admin snapshot restore minio/wildfire-data \
  --snapshot snapshot-20251008-0200 \
  --target minio/wildfire-data-restored

# 3. Sync restored data back
mc mirror minio/wildfire-data-restored minio/wildfire-data
```

#### Restore from Cloud S3 Backup

```bash
# Restore from AWS S3 to MinIO
aws s3 sync s3://wildfire-dr-backups/data/ s3://wildfire-data/ \
  --endpoint-url http://localhost:9000
```

### 2.3 Kafka Topic Recovery

```bash
# 1. Stop consumers
docker-compose stop data-storage-service fire-risk-service

# 2. Restore topic from backup
kafka-topics --bootstrap-server kafka:9092 --delete --topic wildfire-fire-detections
kafka-topics --bootstrap-server kafka:9092 --create --topic wildfire-fire-detections --partitions 4 --replication-factor 3

# 3. Replay messages from DR cluster
kafka-mirror-maker \
  --consumer.config consumer.config \
  --producer.config producer.config \
  --whitelist wildfire-fire-detections

# 4. Restart consumers
docker-compose start data-storage-service fire-risk-service
```

### 2.4 Airflow State Recovery

```bash
# 1. Restore Airflow metadata DB
docker-compose exec airflow-webserver airflow db reset

# 2. Restore from backup
gunzip -c /backups/airflow/airflow_db_backup.sql.gz | \
  psql -h postgres -U airflow -d airflow_db

# 3. Restore DAGs from Git
cd /opt/airflow/dags
git pull origin main

# 4. Restart Airflow
docker-compose restart airflow-webserver airflow-scheduler
```

---

## 3. Failover Scenarios

### 3.1 Primary PostgreSQL Failure

**Automatic Failover with Patroni:**

```yaml
# patroni.yml configuration
scope: wildfire-postgres
name: postgres-node1

postgresql:
  pg_hba:
    - host replication replicator 0.0.0.0/0 md5

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576

  initdb:
    - encoding: UTF8
    - data-checksums

patroni:
  tags:
    failover_priority: 1
```

**Manual Failover:**
```bash
# Promote standby to primary
patronictl -c /etc/patroni/patroni.yml failover wildfire-postgres \
  --master postgres-node1 --candidate postgres-node2
```

### 3.2 Kafka Broker Failure

**Partition Reassignment:**
```bash
# Generate reassignment plan
kafka-reassign-partitions --bootstrap-server kafka:9092 \
  --topics-to-move-json-file topics.json \
  --broker-list "1,2,3" \
  --generate > reassignment.json

# Execute reassignment
kafka-reassign-partitions --bootstrap-server kafka:9092 \
  --reassignment-json-file reassignment.json \
  --execute
```

### 3.3 MinIO Node Failure

**Erasure Coding Recovery:**
```bash
# MinIO automatically recovers with erasure coding (EC:4)
# Manually trigger heal if needed
mc admin heal -r minio/wildfire-data
```

### 3.4 Complete Data Center Failure

**Geographic Failover to DR Site:**

```bash
#!/bin/bash
# Failover script for complete site failure

# 1. Update DNS to point to DR site
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://dns-failover.json

# 2. Promote DR databases
patronictl -c /etc/patroni/patroni-dr.yml failover wildfire-postgres-dr

# 3. Start DR services
ssh dr-host "cd /opt/wildfire && docker-compose up -d"

# 4. Verify services
curl -f http://dr-site.wildfire.gov/health || exit 1

echo "DR failover completed successfully"
```

---

## 4. Data Restoration

### 4.1 Metadata Catalog Restoration

```sql
-- Restore metadata catalog from CSV backups
BEGIN;

TRUNCATE data_catalog, storage_metrics, data_lineage, satellite_scenes;

COPY data_catalog FROM '/backups/metadata/data_catalog.csv' CSV HEADER;
COPY storage_metrics FROM '/backups/metadata/storage_metrics.csv' CSV HEADER;
COPY data_lineage FROM '/backups/metadata/data_lineage.csv' CSV HEADER;
COPY satellite_scenes FROM '/backups/metadata/satellite_scenes.csv' CSV HEADER;

-- Rebuild indexes
REINDEX DATABASE wildfire_db;

-- Update sequences
SELECT setval('data_catalog_id_seq', (SELECT MAX(id) FROM data_catalog));
SELECT setval('storage_metrics_id_seq', (SELECT MAX(id) FROM storage_metrics));

COMMIT;
```

### 4.2 Parquet File Restoration

```bash
# Restore Parquet files from cloud backup
aws s3 sync s3://wildfire-dr-backups/parquet/ \
  s3://wildfire-data/parquet/ \
  --endpoint-url http://localhost:9000 \
  --exclude "*.tmp" \
  --include "year=*/month=*/day=*/*.parquet"

# Verify file integrity with checksums
for file in $(mc ls -r minio/wildfire-data/parquet/ | awk '{print $6}'); do
  actual_hash=$(mc cat minio/wildfire-data/$file | sha256sum | awk '{print $1}')
  expected_hash=$(psql -t -c "SELECT checksum FROM data_catalog WHERE file_path='$file'")

  if [ "$actual_hash" != "$expected_hash" ]; then
    echo "CHECKSUM MISMATCH: $file"
  fi
done
```

### 4.3 Real-time Stream Recovery

```bash
# Re-ingest recent data from source APIs
python3 <<EOF
from datetime import datetime, timedelta
import asyncio
from src.connectors.nasa_firms_connector import NASAFirmsConnector

async def reingest_recent_fires():
    connector = NASAFirmsConnector(kafka_producer=None)

    # Re-fetch last 24 hours of fire detections
    cutoff = datetime.now() - timedelta(hours=24)

    for source_id in ["firms_viirs_noaa20", "firms_modis_terra"]:
        print(f"Re-ingesting {source_id}...")
        await connector.fetch_historical_data(source_id, start_date=cutoff)

asyncio.run(reingest_recent_fires())
EOF
```

---

## 5. Communication Plan

### 5.1 Incident Response Team

| Role | Primary | Secondary | Contact |
|------|---------|-----------|---------|
| Incident Commander | John Doe | Jane Smith | +1-555-0100 |
| Database Admin | Bob Johnson | Alice Lee | +1-555-0101 |
| Infrastructure Lead | Chris Wilson | Dana Martinez | +1-555-0102 |
| Application Lead | Alex Brown | Sam Taylor | +1-555-0103 |

### 5.2 Escalation Matrix

1. **Level 1 (Minor)**: Service degradation, <10% users affected
   - Response: On-call engineer
   - Notification: Slack #incidents

2. **Level 2 (Major)**: Service outage, 10-50% users affected
   - Response: Incident Commander + Team Leads
   - Notification: Email + SMS to stakeholders

3. **Level 3 (Critical)**: Complete outage, data loss risk
   - Response: Full DR team activation
   - Notification: Emergency call + Status page

### 5.3 Status Page Updates

```bash
# Update status page during incident
curl -X POST https://status.wildfire.gov/api/incidents \
  -H "Authorization: Bearer $STATUS_API_KEY" \
  -d '{
    "name": "Database Failover in Progress",
    "status": "investigating",
    "message": "We are experiencing issues with our primary database. Failover to DR is in progress.",
    "components": ["data-ingestion", "fire-risk-service"]
  }'
```

---

## 6. Testing Schedule

### 6.1 Regular DR Drills

| Test Type | Frequency | Last Executed | Next Scheduled |
|-----------|-----------|---------------|----------------|
| Backup Restoration Test | Monthly | 2025-09-15 | 2025-10-15 |
| Database Failover Drill | Quarterly | 2025-07-20 | 2025-10-20 |
| Full DR Site Failover | Semi-Annual | 2025-06-01 | 2025-12-01 |
| Chaos Engineering | Monthly | 2025-09-22 | 2025-10-22 |

### 6.2 DR Drill Procedure

```bash
#!/bin/bash
# DR Drill Script - Execute quarterly

echo "=== WILDFIRE DR DRILL STARTED: $(date) ==="

# 1. Verify backups
echo "1. Verifying backups..."
./scripts/verify-backups.sh || exit 1

# 2. Test database restore (to staging)
echo "2. Testing database restore..."
./scripts/restore-db-staging.sh || exit 1

# 3. Test Kafka replay
echo "3. Testing Kafka message replay..."
./scripts/test-kafka-replay.sh || exit 1

# 4. Simulate failover
echo "4. Simulating failover..."
./scripts/simulate-failover.sh || exit 1

# 5. Verify data integrity
echo "5. Verifying data integrity..."
./scripts/verify-data-integrity.sh || exit 1

# 6. Generate report
echo "6. Generating DR drill report..."
./scripts/generate-dr-report.sh

echo "=== WILDFIRE DR DRILL COMPLETED: $(date) ==="
```

### 6.3 Post-Drill Review

After each DR drill, document:
- **What worked**: Successful recovery procedures
- **What failed**: Issues encountered
- **Lessons learned**: Process improvements
- **Action items**: Updates to runbooks

---

## 7. Recovery Time Estimates

| Component | Recovery Time | Recovery Point |
|-----------|--------------|----------------|
| PostgreSQL (from backup) | 30 minutes | Last hourly backup |
| PostgreSQL (PITR) | 15 minutes | Any point in last 7 days |
| MinIO (from replica) | 10 minutes | Real-time replication |
| Kafka (from mirror) | 20 minutes | Last 5 minutes |
| Airflow DAGs | 5 minutes | Latest Git commit |
| Full System (DR site) | 4 hours | 15 minutes |

---

## 8. Monitoring and Alerts

### 8.1 Backup Health Monitoring

```yaml
# Prometheus alert rules for backup failures
groups:
  - name: backup_alerts
    rules:
      - alert: PostgreSQLBackupFailed
        expr: backup_postgres_success == 0
        for: 1h
        annotations:
          summary: "PostgreSQL backup failed"

      - alert: MinIOReplicationLag
        expr: minio_replication_lag_seconds > 3600
        for: 30m
        annotations:
          summary: "MinIO replication lagging"

      - alert: BackupStorageAlmostFull
        expr: (backup_storage_used / backup_storage_total) > 0.85
        for: 1h
        annotations:
          summary: "Backup storage >85% full"
```

### 8.2 DR Site Health Check

```bash
# Automated DR site health check (runs every 15 minutes)
#!/bin/bash
DR_ENDPOINTS=(
  "http://dr-postgres:5432"
  "http://dr-minio:9000/minio/health/live"
  "http://dr-kafka:9092"
)

for endpoint in "${DR_ENDPOINTS[@]}"; do
  if ! curl -sf "$endpoint" > /dev/null; then
    echo "DR SITE DOWN: $endpoint"
    # Send alert
    curl -X POST $SLACK_WEBHOOK -d "{\"text\":\"DR Site Down: $endpoint\"}"
  fi
done
```

---

## 9. Contacts and Resources

### Emergency Contacts
- **CAL FIRE Emergency Operations**: 1-800-555-FIRE
- **AWS Support (Premium)**: 1-877-AWS-HELP
- **Database Vendor Support**: enterprise-support@postgresql.org

### Documentation Links
- [Backup Scripts](../scripts/backup/)
- [Recovery Runbooks](../runbooks/)
- [Infrastructure Diagrams](../architecture/INFRASTRUCTURE.md)

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-08 | DevOps Team | Initial DR plan |

---

**Last Reviewed**: 2025-10-08
**Next Review**: 2026-01-08
**Owner**: Infrastructure Team
