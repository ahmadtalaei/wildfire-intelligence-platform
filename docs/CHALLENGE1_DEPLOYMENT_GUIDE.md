# Challenge 1: Step-by-Step Deployment Guide
## Wildfire Intelligence Platform - Data Ingestion System

**Purpose**: Complete deployment instructions for judges and operations team
**Platform**: Windows 10/11, Docker Desktop
**Time Required**: 15 minutes (including downloads)
**Last Updated**: 2025-01-05

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Steps](#installation-steps)
3. [Verification](#verification)
4. [Testing Data Ingestion](#testing-data-ingestion)
5. [Viewing Dashboards](#viewing-dashboards)
6. [Troubleshooting](#troubleshooting)
7. [Screenshot Locations](#screenshot-locations)

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 10 64-bit | Windows 11 |
| **RAM** | 8 GB | 16 GB |
| **Disk Space** | 20 GB free | 50 GB free |
| **CPU** | 4 cores | 8 cores |
| **Internet** | Required for initial setup | - |

### Required Software

1. **Docker Desktop for Windows**
   - Download: https://www.docker.com/products/docker-desktop
   - Version: 4.25+ (with Docker Compose V2)
   - **Screenshot Placeholder**: `docker_desktop_version.png`

2. **Git for Windows** (optional, for cloning repository)
   - Download: https://git-scm.com/download/win
   - Alternatively, download ZIP from GitHub

3. **Text Editor** (for viewing logs)
   - VS Code: https://code.visualstudio.com/
   - Or Notepad++ (included with Windows)

### Pre-Installation Checks

```powershell
# Check Docker version
docker --version
# Expected: Docker version 24.0.0 or higher

# Check Docker Compose version
docker compose version
# Expected: Docker Compose version v2.23.0 or higher

# Check available disk space
Get-PSDrive C | Select-Object Used,Free,Name
# Expected: At least 20 GB free
```

**Screenshot Placeholder**: `prerequisites_check.png`

---

## Installation Steps

### Step 1: Obtain Source Code

**Option A: Clone from GitHub**
```powershell
# Open PowerShell
cd C:\dev

# Clone repository
git clone https://github.com/[your-org]/wildfire-intelligence-platform wildfire
cd wildfire
```

**Option B: Extract ZIP file**
```powershell
# Extract wildfire-intelligence-platform.zip to C:\dev\wildfire
# Open PowerShell and navigate
cd C:\dev\wildfire
```

**Screenshot Placeholder**: `source_code_directory.png`

---

### Step 2: Verify Directory Structure

```powershell
# List key directories
ls -Name

# Expected output:
# services/
# airflow/
# monitoring/
# scripts/
# docker-compose.yml
# .env
# README.md
```

**Screenshot Placeholder**: `directory_structure.png`

---

### Step 3: Review Environment Variables

```powershell
# Open .env file in text editor
notepad .env

# Verify key variables:
# - FIRMS_MAP_KEY=75ced0840b668216396df605281f8ab5
# - GRAFANA_ADMIN_USER=admin
# - GRAFANA_ADMIN_PASSWORD=admin
# - DATABASE_URL=postgresql://wildfire_user:wildfire_password@localhost:5432/wildfire_db
```

**Screenshot Placeholder**: `env_file_content.png`

**Note**: These are development credentials. Change for production.

---

### Step 4: Start Docker Desktop

1. Open Docker Desktop application
2. Wait for "Docker is running" status (green indicator)
3. Verify resources:
   - Settings → Resources → Advanced
   - Memory: At least 8 GB
   - CPUs: At least 4
   - Disk image size: At least 40 GB

**Screenshot Placeholder**: `docker_desktop_running.png`

---

### Step 5: Start All Services

```powershell
# From C:\dev\wildfire directory
docker compose up -d

# Expected output:
# [+] Running 25/25
#  ✔ Container wildfire-postgres     Started
#  ✔ Container wildfire-redis        Started
#  ✔ Container wildfire-zookeeper    Started
#  ✔ Container wildfire-kafka        Started
#  ✔ Container wildfire-mosquitto    Started
#  ✔ Container wildfire-minio        Started
#  ✔ Container wildfire-prometheus   Started
#  ✔ Container wildfire-grafana      Started
#  ✔ Container wildfire-elasticsearch Started
#  ✔ Container wildfire-kibana       Started
#  ✔ Container wildfire-kong         Started
#  ✔ Container wildfire-airflow-scheduler Started
#  ✔ Container wildfire-airflow-webserver Started
#  ✔ Container wildfire-data-ingestion-service Started
#  ... (25 total containers)
```

**Screenshot Placeholder**: `docker_compose_up.png`

**Time**: This step takes 2-3 minutes for first-time startup

---

### Step 6: Monitor Container Health

```powershell
# Check container status
docker compose ps

# Wait until all containers show "healthy" or "Up"
# This may take 2-3 minutes
```

**Expected Output**:
```
NAME                            STATUS
wildfire-postgres               Up (healthy)
wildfire-redis                  Up (healthy)
wildfire-kafka                  Up (healthy)
wildfire-grafana                Up (healthy)
wildfire-data-ingestion-service Up (healthy)
... (25 containers total)
```

**Screenshot Placeholder**: `docker_compose_ps_healthy.png`

**Tip**: If any container shows "unhealthy" or "Exited", see [Troubleshooting](#troubleshooting) section.

---

## Verification

### Step 7: Verify Service URLs

Open browser and test each URL:

| Service | URL | Expected | Screenshot |
|---------|-----|----------|------------|
| **Grafana** | http://localhost:3010 | Login page | `grafana_login_page.png` |
| **Airflow** | http://localhost:8090 | Login page (admin/admin123) | `airflow_login_page.png` |
| **Data Ingestion API** | http://localhost:8003/docs | Swagger UI | `swagger_ui_page.png` |
| **MinIO Console** | http://localhost:9001 | Login page (minioadmin/minioadminpassword) | `minio_login_page.png` |
| **Prometheus** | http://localhost:9090 | Prometheus UI | `prometheus_ui.png` |
| **Fire Chief Dashboard** | http://localhost:3001 | Dashboard (may load slowly first time) | `fire_chief_dashboard.png` |

**If any URL fails to load**: Wait 1 minute and retry. Services take time to fully initialize.

---

### Step 8: Import Grafana Dashboard

**IMPORTANT**: This step is required to view Challenge 1 metrics.

1. Open Grafana: http://localhost:3010
2. Login: `admin` / `admin` (skip password change for demo)
   **Screenshot Placeholder**: `grafana_logged_in.png`

3. Click **"+"** icon in left sidebar → **"Import"**
   **Screenshot Placeholder**: `grafana_import_menu.png`

4. Click **"Upload JSON file"**
5. Navigate to: `C:\dev\wildfire\monitoring\grafana\dashboards\challenge-1-latency-fidelity.json`
   **Screenshot Placeholder**: `grafana_upload_json.png`

6. Click **"Import"**
7. Dashboard appears: **"[TROPHY] Challenge 1: Data Sources Latency & Fidelity Metrics"**
   **Screenshot Placeholder**: `grafana_challenge1_dashboard_imported.png`

8. Verify URL: http://localhost:3010/d/challenge1-ingestion
   **Screenshot Placeholder**: `grafana_dashboard_empty.png` (no data yet, expected)

---

## Testing Data Ingestion

### Step 9: Trigger NASA FIRMS Ingestion

```powershell
# Trigger ingestion via API
curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger `
  -H "Content-Type: application/json" `
  -d '{"area": "california", "lookback_hours": 24}'

# Expected response:
# {
#   "status": "success",
#   "detections_fetched": 127,
#   "processing_time_ms": 847
# }
```

**Screenshot Placeholder**: `curl_firms_trigger_response.png`

**Alternative (using browser)**:
1. Open Swagger UI: http://localhost:8003/docs
2. Expand **POST /api/v1/ingest/firms/trigger**
3. Click **"Try it out"**
4. Click **"Execute"**
5. View response

**Screenshot Placeholder**: `swagger_firms_trigger.png`

---

### Step 10: Verify Data in PostgreSQL

```powershell
# Connect to PostgreSQL
docker exec wildfire-postgres psql -U wildfire_user -d wildfire_db

# Query fire detections
SELECT COUNT(*) FROM fire_detections;

# Expected: At least 100 records
# If 0 records, wait 30 seconds and retry (ingestion is async)
```

**Screenshot Placeholder**: `postgres_fire_detections_count.png`

**Query with details**:
```sql
SELECT
    source,
    COUNT(*) as count,
    MIN(detection_time_pst) as earliest,
    MAX(detection_time_pst) as latest
FROM fire_detections
GROUP BY source
ORDER BY count DESC;

-- Exit psql
\q
```

**Screenshot Placeholder**: `postgres_fire_detections_by_source.png`

---

### Step 11: Run PoC Demo DAG (Optional)

**Purpose**: Demonstrate complete data lifecycle in 3 minutes

1. Open Airflow: http://localhost:8090
2. Login: `admin` / `admin123`
   **Screenshot Placeholder**: `airflow_logged_in.png`

3. Find DAG: **`poc_minimal_lifecycle`**
   **Screenshot Placeholder**: `airflow_dag_list.png`

4. Click **Play button (▶️)** → **"Trigger DAG"**
   **Screenshot Placeholder**: `airflow_trigger_dag.png`

5. Watch DAG run (refresh page every 30 seconds)
6. After 3 minutes, all tasks show **green checkmarks**
   **Screenshot Placeholder**: `airflow_dag_success.png`

**What it does**:
- Generates 1,000 realistic fire detections
- Ingests to PostgreSQL HOT tier
- Exports to Parquet WARM tier (78% compression)
- Updates data catalog
- Generates cost/performance metrics

---

## Viewing Dashboards

### Step 12: View Challenge 1 Grafana Dashboard

1. Open Grafana: http://localhost:3010/d/challenge1-ingestion
2. Wait 30 seconds for data to populate (after Step 9 ingestion)
3. Dashboard shows **10 panels**:

**Expected Metrics**:
| Panel | Metric | Expected Value |
|-------|--------|----------------|
| **Ingestion Latency (p95)** | Latency | <5 minutes (expect ~870ms) ✅ |
| **Validation Pass Rate** | Pass rate | >95% (expect ~99.9%) ✅ |
| **Duplicate Detection Rate** | Duplicate % | <1% (expect ~0.02%) ✅ |
| **Active Data Sources** | Count | 3+ sources |
| **Success Rate** | % | >99% |

**Screenshot Placeholder**: `grafana_dashboard_full.png` ⭐ **KEY SCREENSHOT**

**Individual Panel Screenshots**:
- `grafana_latency_panel.png` (Panel #1: Latency by source)
- `grafana_validation_panel.png` (Panel #2: Validation pass rate)
- `grafana_sla_widgets.png` (Panels #5, #6, #7: SLA compliance)
- `grafana_failed_messages.png` (Panel #8: DLQ messages)

---

### Step 13: View Prometheus Metrics

1. Open Prometheus: http://localhost:9090
2. Click **"Status" → "Targets"**
3. Verify all targets show **"UP"** (green)
   **Screenshot Placeholder**: `prometheus_targets_up.png`

4. Click **"Graph"** tab
5. Enter query: `histogram_quantile(0.95, sum(rate(ingestion_latency_seconds_bucket[5m])) by (le, source))`
6. Click **"Execute"**
7. Switch to **"Graph"** view
   **Screenshot Placeholder**: `prometheus_latency_query.png`

---

### Step 14: Verify MinIO Object Storage

1. Open MinIO Console: http://localhost:9001
2. Login: `minioadmin` / `minioadminpassword`
   **Screenshot Placeholder**: `minio_logged_in.png`

3. Click **"Buckets"** in left sidebar
4. Verify buckets exist:
   - `wildfire-raw-data`
   - `wildfire-processed-data`
   - `wildfire-backups`
   **Screenshot Placeholder**: `minio_buckets_list.png`

5. Click **`wildfire-processed-data`** bucket
6. Navigate to files (may be empty if PoC DAG not run)
   **Screenshot Placeholder**: `minio_bucket_contents.png`

---

## Troubleshooting

### Issue: Container Fails to Start

**Symptom**: `docker compose ps` shows "Exited" or "Restarting"

```powershell
# Check container logs
docker logs wildfire-postgres --tail 50

# Common errors:
# - "port already allocated" → Kill process using port
# - "disk space" → Free up disk space
# - "out of memory" → Increase Docker memory in Docker Desktop settings
```

**Solution for port conflicts**:
```powershell
# Find process using port 5432 (PostgreSQL example)
netstat -ano | findstr :5432

# Kill process (replace 1234 with actual PID)
taskkill /PID 1234 /F

# Restart containers
docker compose restart
```

---

### Issue: Grafana Dashboard Shows "No Data"

**Symptom**: Dashboard imported but panels are empty

**Solution**:
1. Verify data was ingested (Step 9)
2. Check Prometheus is scraping metrics:
   ```powershell
   curl http://localhost:9090/-/healthy
   # Expected: Prometheus is Healthy
   ```
3. Trigger ingestion again (Step 9)
4. Wait 30 seconds, refresh Grafana dashboard

**Screenshot Placeholder**: `grafana_dashboard_no_data_vs_with_data.png`

---

### Issue: API Returns 503 "Service Unavailable"

**Symptom**: `curl http://localhost:8003/health` returns error

**Solution**:
```powershell
# Check data-ingestion-service logs
docker logs wildfire-data-ingestion-service --tail 100

# Restart service
docker compose restart data-ingestion-service

# Wait 30 seconds, retry health check
curl http://localhost:8003/health
```

---

### Issue: Airflow DAG Not Showing

**Symptom**: Airflow UI shows no DAGs or "Import Error"

**Solution**:
```powershell
# Check Airflow scheduler logs
docker logs wildfire-airflow-scheduler --tail 50

# Restart Airflow services
docker compose restart airflow-scheduler airflow-webserver

# Wait 1 minute, refresh Airflow UI
```

---

### Issue: Out of Disk Space

**Symptom**: Docker error: "no space left on device"

**Solution**:
```powershell
# Remove unused Docker images and volumes
docker system prune -a --volumes

# Warning: This deletes ALL unused Docker data
# Free space: typically 10-20 GB recovered
```

---

## Screenshot Locations

### Where to Save Screenshots

All screenshots should be saved to:
```
C:\dev\wildfire\docs\screenshots\challenge1\
```

### Screenshot Checklist (19 screenshots)

Refer to: `docs/CHALLENGE1_SCREENSHOT_GUIDE.md` for detailed instructions.

**Quick list**:
1. ✅ `docker_compose_ps_healthy.png` - Step 6
2. ✅ `grafana_dashboard_full.png` - Step 12 ⭐ **MOST IMPORTANT**
3. ✅ `grafana_latency_panel.png` - Step 12
4. ✅ `grafana_validation_panel.png` - Step 12
5. ✅ `prometheus_targets_up.png` - Step 13
6. ✅ `swagger_ui_page.png` - Step 7
7. ✅ `airflow_dag_success.png` - Step 11
8. ✅ `postgres_fire_detections_by_source.png` - Step 10
9. ✅ `minio_buckets_list.png` - Step 14

... (10 more screenshots, see CHALLENGE1_SCREENSHOT_GUIDE.md)

---

## Next Steps

After completing deployment:

1. **Capture Screenshots**: Follow `docs/CHALLENGE1_SCREENSHOT_GUIDE.md`
2. **Run Benchmarks**: Execute `scripts/quick_benchmark.bat`
3. **Review Documentation**: Read `docs/CHALLENGE1_USER_GUIDE.md`
4. **Create Presentation**: Use `docs/CHALLENGE1_PRESENTATION_TEMPLATE.md`

---

## Quick Reference Card

**Essential Commands**:
```powershell
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs for specific service
docker logs wildfire-data-ingestion-service --tail 100

# Restart specific service
docker compose restart data-ingestion-service

# Check service health
curl http://localhost:8003/health

# Trigger FIRMS ingestion
curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger

# Connect to PostgreSQL
docker exec -it wildfire-postgres psql -U wildfire_user -d wildfire_db

# View all containers
docker compose ps
```

**Essential URLs**:
- Grafana: http://localhost:3010 (`admin` / `admin`)
- Airflow: http://localhost:8090 (`admin` / `admin123`)
- Swagger API: http://localhost:8003/docs
- Prometheus: http://localhost:9090
- MinIO: http://localhost:9001 (`minioadmin` / `minioadminpassword`)

**Screenshot Save Location**:
```
C:\dev\wildfire\docs\screenshots\challenge1\
```

---

## Support

### Documentation
- **Full Documentation**: `docs/` directory
- **Screenshot Guide**: `docs/CHALLENGE1_SCREENSHOT_GUIDE.md`
- **API Reference**: `docs/CHALLENGE1_API_REFERENCE.md`
- **Architecture Diagrams**: `docs/CHALLENGE1_ARCHITECTURE_DIAGRAMS.md`

### Common Questions

**Q: How long does initial startup take?**
A: 2-3 minutes for first-time Docker image downloads, ~30 seconds for subsequent starts.

**Q: Can I run this on Linux/Mac?**
A: Yes! Use `docker-compose` (with hyphen) instead of `docker compose` on older systems.

**Q: How much internet bandwidth is required?**
A: Initial Docker image download: ~5 GB. Runtime (NASA FIRMS API calls): ~50 MB/day.

**Q: Can I pause/resume the system?**
A: Yes. `docker compose stop` to pause, `docker compose start` to resume. No data loss.

---

**Prepared by**: CAL FIRE Wildfire Intelligence Platform Team
**Challenge**: Challenge 1 - Data Sources & Ingestion Mechanisms
**Document Version**: 1.0
**Deployment Time**: 15 minutes (tested on Windows 11, 16 GB RAM)
