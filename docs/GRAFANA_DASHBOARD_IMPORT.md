# Grafana Dashboard Import Guide
## Challenge 1: Data Ingestion Latency & Fidelity Dashboard

**Quick Reference** - 5 minute setup

---

## Prerequisites

```bash
# 1. Ensure all services are running
docker-compose ps

# Expected output: All services "Up (healthy)"
# If not, start services:
docker-compose up -d
```

---

## Step-by-Step Import

### Step 1: Access Grafana

```
URL: http://localhost:3010
```

### Step 2: Login

```
Username: admin
Password: admin
```

(You may be prompted to change password - you can skip this for testing)

### Step 3: Import Dashboard

1. **Click the "+" icon** in the left sidebar (or "Dashboards" → "Import")
2. **Click "Import"**
3. **Click "Upload JSON file"** button
4. **Navigate to and select**:
   ```
   C:\dev\wildfire\docs\grafana\challenge1_latency_dashboard.json
   ```
5. **Click "Load"**
6. **Verify settings**:
   - Name: "Challenge 1: Data Ingestion Latency & Fidelity"
   - UID: challenge1-ingestion
   - Folder: General (or create new folder)
7. **Click "Import"**

### Step 4: Verify Dashboard

```
URL: http://localhost:3010/d/challenge1-ingestion
```

**Expected**: Dashboard with 10 panels showing metrics

---

## Dashboard Panels Overview

The imported dashboard contains 10 panels:

| Panel # | Title | Type | Metric |
|---------|-------|------|--------|
| 1 | Ingestion Latency (p50/p95/p99) by Source | Time Series | Histogram percentiles |
| 2 | Validation Pass Rate by Source (%) | Gauge | Success rate |
| 3 | Ingestion Throughput (records/sec) | Bar Chart | Records per second |
| 4 | Kafka Consumer Lag (messages) | Gauge | Lag count |
| 5 | SLA: Messages Ingested Successfully | Stat | Success % |
| 6 | SLA: p95 Latency < 5 minutes | Stat | Latency seconds |
| 7 | SLA: Duplicate Rate < 1% | Stat | Duplicate % |
| 8 | Recent Failed Messages (Top 20) | Table | Error details |
| 9 | Data Quality Score by Source (0-1) | Time Series | Quality score |
| 10 | Anomalies Detected by Source & Type | Stacked Area | Anomaly count |

---

## Troubleshooting

### Issue: "Dashboard not found" after import

**Solution 1 - Verify UID**:
```bash
# Check dashboard UID in JSON
grep '"uid"' C:\dev\wildfire\docs\grafana\challenge1_latency_dashboard.json

# Should show: "uid": "challenge1-ingestion"
```

**Solution 2 - Check Grafana dashboards list**:
1. Go to: http://localhost:3010/dashboards
2. Look for "Challenge 1: Data Ingestion Latency & Fidelity"
3. Click on it to open

### Issue: Panels show "No data"

**Solution - Verify Prometheus is collecting metrics**:
```bash
# 1. Check Prometheus is up
curl http://localhost:9090/-/healthy
# Expected: Prometheus is Healthy.

# 2. Check if metrics exist
curl "http://localhost:9090/api/v1/query?query=ingestion_latency_seconds_count"
# Expected: JSON with results

# 3. Trigger data ingestion to generate metrics
curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger

# 4. Wait 30 seconds, then refresh Grafana dashboard
```

### Issue: Prometheus datasource not found

**Solution - Configure Prometheus datasource**:
1. In Grafana, go to: **Configuration** → **Data Sources**
2. Click **"Add data source"**
3. Select **"Prometheus"**
4. Configure:
   - Name: `Prometheus`
   - URL: `http://prometheus:9090`
5. Click **"Save & Test"**
6. Expected: "Data source is working"
7. Re-import dashboard

### Issue: Grafana container not running

**Solution - Restart Grafana**:
```bash
# Check Grafana status
docker-compose ps grafana

# If not running, start it
docker-compose up -d grafana

# Check logs for errors
docker-compose logs grafana | tail -50
```

---

## Verification Checklist

After import, verify:

- [ ] Dashboard accessible at: http://localhost:3010/d/challenge1-ingestion
- [ ] All 10 panels visible
- [ ] Panels show data (not "No data" errors)
- [ ] Time range selector in top-right (default: Last 1 hour)
- [ ] Refresh interval selector (default: 10s)
- [ ] Dashboard title: "Challenge 1: Data Ingestion Latency & Fidelity"

---

## Quick Commands Reference

```bash
# Access Grafana
http://localhost:3010

# Access dashboard directly
http://localhost:3010/d/challenge1-ingestion

# Check Grafana logs
docker-compose logs grafana

# Restart Grafana
docker-compose restart grafana

# Reset admin password
docker-compose exec grafana grafana-cli admin reset-admin-password admin

# Check Prometheus
curl http://localhost:9090/-/healthy

# Trigger test data ingestion
curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger
```

---

## Dashboard Features

### Time Range Selection
- Top-right corner dropdown
- Options: Last 5m, 15m, 1h, 6h, 24h, 7d, 30d
- Custom range picker available

### Auto-Refresh
- Top-right dropdown (next to time range)
- Options: Off, 5s, 10s, 30s, 1m, 5m
- Default: 10s (for real-time monitoring)

### Panel Interactions
- **Click panel title** → View, Edit, Share, Inspect
- **Hover on chart** → See values in tooltip
- **Click & drag** → Zoom into time range
- **Double-click** → Reset zoom

### Filtering
- Some panels have variable filters (top of dashboard)
- Filter by source, time range, or other dimensions

---

## Export Dashboard (for backup)

If you need to export the dashboard:

1. Open dashboard: http://localhost:3010/d/challenge1-ingestion
2. Click **⚙️ (gear icon)** in top-right
3. Select **"JSON Model"**
4. Click **"Copy to Clipboard"** or **"Save to file"**
5. Save as: `challenge1_latency_dashboard_backup.json`

---

## Next Steps

After importing the dashboard:

1. ✅ **Capture screenshots** using `docs/CHALLENGE1_SCREENSHOT_GUIDE.md`
2. ✅ **Run tests** using `docs/CHALLENGE1_TESTING_GUIDE.md`
3. ✅ **Verify SLA compliance** (all panels should show green)
4. ✅ **Document visual evidence** for Challenge 1 submission

---

**Dashboard Version**: 1.0
**Grafana Version**: 9.x or higher
**Prometheus Datasource**: Required
**Import Time**: ~5 minutes
**Last Updated**: January 2025
