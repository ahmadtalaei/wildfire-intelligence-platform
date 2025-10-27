# 🔄 Data Lifecycle Automation - Deployment Guide

## Overview

This guide walks you through deploying the automated data lifecycle management system that prevents storage bloat and optimizes costs through intelligent tiering.

---

## 📋 Prerequisites

- Docker Desktop running
- PostgreSQL database accessible
- MinIO object storage running
- At least 16GB RAM available
- Sufficient disk space for Airflow (5GB+)

---

## 🚀 Quick Start Deployment

### Step 1: Initialize Metadata Catalog Schema

```bash
# Navigate to wildfire project
cd C:\dev\wildfire

# Run the metadata catalog schema creation
docker exec wildfire-postgres psql -U wildfire_user -d wildfire_db -f /scripts/database/create_metadata_catalog.sql
```

**Expected Output:**
```
✅ Metadata catalog schema created successfully!
📊 Tables: data_catalog, storage_metrics, data_lineage, satellite_scenes, retention_audit_log
📈 Views: v_storage_distribution, v_files_for_migration, v_sentinel_cleanup_candidates
⚡ Functions: calculate_storage_cost(), get_catalog_summary()
```

---

### Step 2: Mount the SQL Script into PostgreSQL Container

```bash
# Copy the SQL script to a location accessible by the container
docker cp scripts/database/create_metadata_catalog.sql wildfire-postgres:/tmp/

# Execute the script
docker exec wildfire-postgres psql -U wildfire_user -d wildfire_db -f /tmp/create_metadata_catalog.sql
```

---

### Step 3: Start Airflow Services

```bash
# Start Airflow webserver and scheduler
docker-compose up -d airflow-webserver airflow-scheduler

# Wait for Airflow to initialize (30-60 seconds)
docker logs -f wildfire-airflow-webserver

# Look for: "Airflow is ready"
```

---

### Step 4: Access Airflow Web UI

1. Open browser to: `http://localhost:8090`
2. Login with:
   - **Username:** `admin`
   - **Password:** `admin123`

3. Verify DAGs are loaded:
   - `daily_hot_to_warm_migration`
   - `weekly_warm_to_cold_migration`

---

### Step 5: Configure Airflow Connections

#### PostgreSQL Connection

1. Go to **Admin → Connections**
2. Edit `postgres_default`:
   - **Connection Type:** Postgres
   - **Host:** `postgres`
   - **Schema:** `wildfire_db`
   - **Login:** `wildfire_user`
   - **Password:** `wildfire_password`
   - **Port:** `5432`

#### MinIO S3 Connection

1. Add new connection `minio_default`:
   - **Connection Type:** Amazon Web Services
   - **Extra:**
   ```json
   {
     "aws_access_key_id": "minioadmin",
     "aws_secret_access_key": "minioadminpassword",
     "host": "http://minio:9000"
   }
   ```

---

### Step 6: Install Required Python Packages

```bash
# Exec into Airflow container
docker exec -it wildfire-airflow-scheduler bash

# Install required packages
pip install pyarrow pandas sqlalchemy psycopg2-binary boto3

# Exit container
exit
```

---

### Step 7: Test DAGs

#### Test Daily Migration DAG

```bash
# Trigger manual run from Airflow UI or CLI
docker exec wildfire-airflow-scheduler airflow dags test daily_hot_to_warm_migration
```

#### Test Weekly Migration DAG

```bash
docker exec wildfire-airflow-scheduler airflow dags test weekly_warm_to_cold_migration
```

---

### Step 8: Enable DAGs for Production

1. In Airflow UI, toggle DAGs to **ON**:
   - `daily_hot_to_warm_migration` - Runs daily at midnight PST
   - `weekly_warm_to_cold_migration` - Runs Sundays at 2 AM PST

---

### Step 9: Import Grafana Dashboard

1. Open Grafana: `http://localhost:3010`
2. Login (admin/admin)
3. Go to **Dashboards → Import**
4. Upload: `monitoring/grafana/dashboards/storage_lifecycle_dashboard.json`
5. Select PostgreSQL datasource
6. Click **Import**

---

## 🔍 Verification Checklist

- [ ] PostgreSQL metadata catalog tables created
- [ ] Airflow webserver accessible at http://localhost:8090
- [ ] Both DAGs visible in Airflow UI
- [ ] Airflow connections configured (postgres_default, minio_default)
- [ ] Python packages installed (pyarrow, pandas, boto3)
- [ ] Grafana dashboard imported successfully
- [ ] Test DAG run completed without errors

---

## 📊 Monitoring & Operations

### Check Lifecycle Job Status

```sql
-- View recent migration jobs
SELECT * FROM data_lineage
ORDER BY job_start_time DESC
LIMIT 10;

-- View storage distribution
SELECT * FROM v_storage_distribution;

-- Calculate current costs
SELECT * FROM calculate_storage_cost();
```

### View Airflow Logs

```bash
# Webserver logs
docker logs wildfire-airflow-webserver

# Scheduler logs
docker logs wildfire-airflow-scheduler

# DAG task logs (from Airflow UI)
# Navigate to DAG → Task Instance → Log
```

### Monitor Storage Metrics

- **Grafana:** http://localhost:3010/d/storage-lifecycle
- **Airflow:** http://localhost:8090/dags
- **MinIO Console:** http://localhost:9001

---

## 🔧 Configuration

### Retention Policy Customization

Edit `config/retention_policies.yaml`:

```yaml
# Example: Change fire detection retention
policies:
  fire_detections:
    firms_viirs_noaa20:
      hot_tier_days: 14  # Change from 7 to 14 days
      warm_tier_days: 180  # Change from 90 to 180 days
```

**After changes, restart Airflow:**
```bash
docker-compose restart airflow-scheduler
```

---

## 🐛 Troubleshooting

### Issue: Airflow DAGs not appearing

**Solution:**
```bash
# Check DAG folder is mounted
docker exec wildfire-airflow-scheduler ls -la /opt/airflow/dags

# Restart scheduler
docker-compose restart airflow-scheduler
```

### Issue: Migration fails with "table does not exist"

**Solution:**
```bash
# Re-run metadata catalog schema
docker exec wildfire-postgres psql -U wildfire_user -d wildfire_db -f /tmp/create_metadata_catalog.sql
```

### Issue: MinIO connection fails

**Solution:**
```bash
# Verify MinIO is running
docker ps | grep minio

# Test connection from Airflow
docker exec wildfire-airflow-scheduler python -c "from airflow.providers.amazon.aws.hooks.s3 import S3Hook; hook = S3Hook(aws_conn_id='minio_default'); print(hook.list_buckets())"
```

### Issue: Large Parquet files not created

**Solution:**
Check if data exists in PostgreSQL:
```sql
SELECT COUNT(*) FROM firms_viirs_noaa20_detections WHERE timestamp < NOW() - INTERVAL '7 days';
```

If 0 rows, wait for data ingestion to populate tables first.

---

## 📈 Performance Tuning

### Optimize Parquet Compression

Edit DAG files (`airflow/dags/*.py`):

```python
# Change compression algorithm
pq.write_table(table, parquet_buffer, compression='gzip')  # Better compression, slower
pq.write_table(table, parquet_buffer, compression='lz4')   # Faster, less compression
```

### Parallel Processing

Edit `config/retention_policies.yaml`:

```yaml
automation:
  daily_hot_to_warm:
    parallel_workers: 8  # Increase from 4 to 8
    batch_size: 20000   # Increase batch size
```

---

## 🔒 Security Hardening

### Change Default Passwords

1. **Airflow:**
   ```bash
   # In docker-compose.yml
   - _AIRFLOW_WWW_USER_PASSWORD=YOUR_SECURE_PASSWORD
   ```

2. **PostgreSQL:**
   ```bash
   # In .env file
   POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD
   ```

3. **MinIO:**
   ```bash
   # In docker-compose.yml
   MINIO_ROOT_PASSWORD=YOUR_SECURE_PASSWORD
   ```

### Enable SSL/TLS

For production, configure:
- Airflow webserver HTTPS
- PostgreSQL SSL connections
- MinIO TLS encryption

See `docs/security/encryption_plan.md` for details.

---

## 📅 Maintenance Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| Check DAG health | Daily | Airflow UI → Browse → DAG Runs |
| Review storage metrics | Weekly | Grafana Storage Dashboard |
| Audit retention logs | Monthly | `SELECT * FROM retention_audit_log WHERE executed_at > NOW() - INTERVAL '30 days'` |
| Update retention policies | Quarterly | Edit `config/retention_policies.yaml` |
| Backup metadata catalog | Weekly | `pg_dump wildfire_db > backup.sql` |

---

## 🎯 Success Criteria

After deployment, you should see:

✅ **Automated Daily Migrations**
   - PostgreSQL HOT tier stays < 20GB
   - MinIO WARM tier grows steadily (compressed Parquet files)

✅ **Weekly Cleanups**
   - Old Sentinel imagery deleted (>30% cloud, >90 days)
   - Storage costs remain predictable

✅ **Monitoring Dashboards**
   - Grafana shows tier distribution
   - Cost estimates track within budget

✅ **No Manual Intervention**
   - No more 205GB MinIO explosions!
   - System self-manages storage lifecycle

---

## 📞 Support

For issues or questions:
- **Documentation:** `docs/architecture/STREAMING_DATA_ARCHITECTURE.md`
- **Runbooks:** `docs/operations/`
- **GitHub Issues:** https://github.com/your-org/wildfire-platform/issues

---

**🎉 Congratulations! Your data lifecycle automation is now deployed and operational!**
