
# CAL FIRE Wildfire Intelligence Platform: Presentation Guide
## Visual Evidence for Challenge 1 & Challenge 2

**Purpose**: Capture visual evidence and presentation slides for Challenge 1 (Data Ingestion) and Challenge 2 (Data Storage) deliverables

**Tools Required**:
- Windows Snipping Tool (Win + Shift + S)
- Or: Greenshot (free screenshot tool)
- Or: Browser developer tools for full-page screenshots

---

## IMPORTANT: Import Dashboard First!

**Before capturing screenshots, you MUST import the Grafana dashboard:**

```bash
# 1. Ensure all services are running
docker-compose ps
# All services should show "Up (healthy)"

# 2. Open Grafana
http://localhost:3010

# 3. Login with default credentials
Username: admin
Password: admin

# 4. Import the Challenge 1 dashboard
- Click the "+" icon in left sidebar
- Select "Import"
- Click "Upload JSON file"
- Navigate to: C:\dev\wildfire\docs\grafana\challenge1_latency_dashboard.json
- Click "Import"

# 5. Verify dashboard is accessible
http://localhost:3010/d/challenge1-ingestion
```

**If you get "Dashboard not found":**
- Make sure you completed step 4 above to import the JSON file
- The dashboard UID is: `challenge1-ingestion`
- Check Grafana logs: `docker-compose logs grafana`

---

## Screenshot Checklist

### 1. Grafana Dashboard Screenshots

#### Screenshot 1: Full Dashboard Overview
**File**: `grafana_dashboard_full.png`
**URL**: http://localhost:3010/d/challenge1-ingestion (after importing dashboard)
**Instructions**:
1. **FIRST**: Import dashboard using instructions above
2. Open Grafana in browser at http://localhost:3010
3. Navigate to Challenge 1 dashboard: http://localhost:3010/d/challenge1-ingestion
4. Wait for all panels to load data (may take 30-60 seconds)
5. Press F11 for fullscreen mode
6. Capture full page using browser extension or scrolling screenshot
7. Save to: `C:\dev\wildfire\docs\screenshots\challenge1\grafana_dashboard_full.png`

**What to Show**:
- All 10 panels visible
- Data populating charts
- Green SLA indicators
- Recent timeframe (last 1 hour)

---

#### Screenshot 2: Ingestion Latency Chart
**File**: `grafana_latency_p50_p95_p99.png`
**Focus**: Panel #1 - "Ingestion Latency (p50/p95/p99) by Source"
**Instructions**:
1. Click on panel title
2. Select "View"
3. Capture the expanded chart
4. Ensure legend shows all sources (NASA_FIRMS, historical_fires, sensor_readings)
5. Save screenshot

**What to Show**:
- Multiple colored lines (one per source)
- Legend with p50/p95/p99 values
- Y-axis in seconds
- Data points showing latency over time

---

#### Screenshot 3: Validation Pass Rate
**File**: `grafana_validation_pass_rate.png`
**Focus**: Panel #2 - "Validation Pass Rate by Source (%)"
**What to Show**:
- Gauge charts showing > 95% for all sources
- Green color indicators
- Source names labeled

---

#### Screenshot 4: SLA Compliance Widgets
**File**: `grafana_sla_widgets.png`
**Focus**: Panels #5, #6, #7 - SLA widgets
**What to Show**:
- "Messages Ingested Successfully" (green, > 95%)
- "p95 Latency < 5 minutes" (value in seconds)
- "Duplicate Rate < 1%" (green, < 0.01)

---

#### Screenshot 5: Failed Messages Table
**File**: `grafana_failed_messages_table.png`
**Focus**: Panel #8 - "Recent Failed Messages (Top 20)"
**What to Show**:
- Table with columns: Source, Error Type, Count
- Rows showing recent failures (if any)
- Note: May be empty if no failures - that's OK!

---

### 2. Prometheus Metrics Screenshots

#### Screenshot 6: Prometheus Targets
**File**: `prometheus_targets_up.png`
**URL**: http://localhost:9090/targets
**Instructions**:
1. Open Prometheus targets page
2. Scroll to show all data-ingestion-service targets
3. Verify all targets show "UP" (green)
4. Capture screenshot

**What to Show**:
- List of scrape targets
- All targets with "UP" status (green)
- Last scrape time < 1 minute ago
- Endpoint URLs visible

---

#### Screenshot 7: Prometheus Query - Latency Metrics
**File**: `prometheus_latency_query.png`
**URL**: http://localhost:9090/graph
**Instructions**:
1. Enter query: `histogram_quantile(0.95, sum(rate(ingestion_latency_seconds_bucket[5m])) by (le, source))`
2. Click "Execute"
3. Switch to "Graph" tab
4. Capture chart showing latency by source
5. Also capture "Console" tab showing values

**What to Show**:
- Query box with expression
- Graph with multiple lines (one per source)
- Legend with source names
- Y-axis values (latency in seconds)

---

### 3. Service Health Screenshots

#### Screenshot 8: Docker Compose Services
**File**: `docker_compose_ps_healthy.png`
**Command**: `docker-compose ps`
**Instructions**:
```bash
# Run command and capture terminal output
docker-compose ps > C:\dev\wildfire\docs\screenshots\challenge1\docker_ps_output.txt

# Or use terminal screenshot tool
```

**What to Show**:
- All services listed
- Status column showing "Up" or "Up (healthy)"
- Ports column showing exposed ports
- Services: kafka, zookeeper, postgres, prometheus, grafana, data-ingestion, etc.

---

#### Screenshot 9: Data Ingestion Service Health
**File**: `data_ingestion_health_check.png`
**URL**: http://localhost:8003/health
**What to Show**:
JSON response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-05T12:45:00Z",
  "services": {
    "kafka": "connected",
    "postgres": "connected",
    "redis": "connected"
  },
  "connectors": {
    "nasa_firms": "ready",
    "firesat": "ready",
    "mqtt": "ready"
  }
}
```

---

### 4. API Documentation Screenshots

#### Screenshot 10: Swagger UI - Ingestion Endpoints
**File**: `swagger_ui_ingestion_endpoints.png`
**URL**: http://localhost:8003/docs
**Instructions**:
1. Open Swagger UI
2. Expand "Ingestion" tag
3. Show all ingestion endpoints
4. Capture screenshot

**What to Show**:
- List of endpoints: /ingest/firms/trigger, /ingest/historical-fires/batch, etc.
- HTTP methods (POST, GET)
- Endpoint descriptions
- Interactive "Try it out" buttons

---

### 5. Database Query Screenshots

#### Screenshot 11: PostgreSQL Fire Detections
**File**: `postgres_fire_detections_sample.png`
**Command**:
```bash
docker exec wildfire-postgres psql -U postgres -d wildfire -c \
  "SELECT source, COUNT(*) as count, MIN(detection_time_pst) as earliest, MAX(detection_time_pst) as latest
   FROM fire_detections
   GROUP BY source
   ORDER BY count DESC;"
```

**What to Show**:
- Table output showing:
  - source | count | earliest | latest
  - NASA_FIRMS | 1247 | 2025-01-04... | 2025-01-05...
  - FireSat | 523 | ...
  - etc.

---

#### Screenshot 12: Data Quality Metrics
**File**: `postgres_quality_metrics.png`
**Command**:
```bash
docker exec wildfire-postgres psql -U postgres -d wildfire -c \
  "SELECT source, AVG(quality_score) as avg_quality, COUNT(*) as total_records
   FROM data_quality_checks
   WHERE checked_at > NOW() - INTERVAL '1 hour'
   GROUP BY source;"
```

**What to Show**:
- Quality scores by source
- All scores > 0.95
- Record counts

---

### 6. Kafka Topics Screenshots

#### Screenshot 13: Kafka Topics List
**File**: `kafka_topics_list.png`
**Command**:
```bash
docker exec wildfire-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --list
```

**What to Show**:
- List of topics:
  wildfire-incidents
  wildfire-iot-sensors
  wildfire-nasa-firms
  wildfire-satellite-data
  wildfire-satellite-imagery
  wildfire-sensor-data
  wildfire-weather-alerts
  wildfire-weather-bulk
  wildfire-weather-data
---

#### Screenshot 14: Kafka Consumer Groups
**File**: `kafka_consumer_groups.png`
**Command**:
```bash
docker exec wildfire-kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --list
```

**What to Show**:
- Consumer group names
- Active consumer groups
    data-storage-consumer

---

### 7. Sample Data Screenshots

#### Screenshot 15: Sample FIRMS CSV
**File**: `sample_firms_data_excel.png`
**Instructions**:
1. Open `C:\dev\wildfire\data\sample_inputs\sample_firms_data.csv` in Excel
2. Format as table
3. Capture first 10 rows
4. Show column headers: latitude, longitude, brightness, confidence, frp, acq_date, acq_time

---

#### Screenshot 16: Sample MQTT JSON
**File**: `sample_mqtt_payload_formatted.png`
**Instructions**:
1. Open `C:\dev\wildfire\data\sample_inputs\sample_mqtt_payload.json` in VS Code
2. Format JSON (Alt + Shift + F)
3. Capture formatted JSON
4. Show structure: sensor_id, measurements, location, device_info

---

### 8. Monitoring Dashboards

#### Screenshot 17: MinIO Console
**File**: `minio_console_buckets.png`
**URL**: http://localhost:9001
**Login**: minioadmin / minioadmin
**Instructions**:
1. Login to MinIO console
2. Navigate to "Buckets"
3. Show list of buckets:
   - wildfire-raw-data
   - wildfire-processed-data
   - wildfire-backups
4. Capture screenshot

**What to Show**:
- Bucket names
- Object counts
- Total size
- Creation dates

---

### 9. Architecture Diagram Screenshot

#### Screenshot 18: System Architecture Diagram
**File**: `architecture_diagram.png`
**Source**: Create diagram using:
- draw.io
- Lucidchart
- Or ASCII art from README.md

**What to Show**:
- Data sources on left
- Kafka in middle
- Storage on right
- APIs at bottom
- Arrows showing data flow

---

### 10. Test Results Screenshot

#### Screenshot 19: Test Execution Output
**File**: `test_execution_output.png`
**Instructions**:
1. Run test command:
```bash
curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger
```
2. Capture terminal showing:
   - Command executed
   - JSON response
   - Success status

---

## Screenshot Organization

Save all screenshots to:
```
C:\dev\wildfire\docs\screenshots\challenge1\
│
├── grafana_dashboard_full.png
├── grafana_latency_p50_p95_p99.png
├── grafana_validation_pass_rate.png
├── grafana_sla_widgets.png
├── grafana_failed_messages_table.png
├── prometheus_targets_up.png
├── prometheus_latency_query.png
├── docker_compose_ps_healthy.png
├── data_ingestion_health_check.png
├── swagger_ui_ingestion_endpoints.png
├── postgres_fire_detections_sample.png
├── postgres_quality_metrics.png
├── kafka_topics_list.png
├── kafka_consumer_groups.png
├── sample_firms_data_excel.png
├── sample_mqtt_payload_formatted.png
├── minio_console_buckets.png
├── architecture_diagram.png
└── test_execution_output.png
```

---

## Automated Screenshot Capture

For consistency, you can use PowerShell to automate some screenshots:

```powershell
# Install required module
Install-Module -Name Selenium

# Script to capture screenshots
$screenshots = @(
    @{URL="http://localhost:3010/d/challenge1-ingestion"; File="grafana_dashboard_full.png"},
    @{URL="http://localhost:9090/targets"; File="prometheus_targets_up.png"},
    @{URL="http://localhost:8003/docs"; File="swagger_ui_ingestion_endpoints.png"}
)

foreach ($shot in $screenshots) {
    Start-Process chrome $shot.URL
    Start-Sleep -Seconds 5
    # Use Snipping Tool or third-party tool to capture
    # Save as $shot.File
}
```

---

## Screenshot Quality Guidelines

### Resolution
- Minimum: 1920x1080
- Preferred: 2560x1440 or higher
- Format: PNG (lossless)

### Content
- **Include timestamps** where visible
- **Show full context** (entire panel, not just data)
- **Readable text** (zoom in if needed)
- **No personal information** (API keys, passwords)

### Annotations (Optional)
- Use arrows to highlight key metrics
- Add text boxes to explain what's shown
- Circle important values (e.g., latency < SLA)

---

## Final Checklist

Before submission, verify you have:

- [ ] All 19 screenshots captured
- [ ] Screenshots saved in PNG format
- [ ] File names match guide exactly
- [ ] All text is readable
- [ ] Timestamps are visible and recent
- [ ] No sensitive information visible
- [ ] Screenshots demonstrate working system
- [ ] Quality scores visible (> 95%)
- [ ] Latency values meet SLAs
- [ ] All services showing healthy status

---

## Creating a Screenshot Compilation Document

After capturing all screenshots, create a Word or PDF document:

```markdown
# Challenge 1: Visual Evidence
## Data Ingestion Latency & Fidelity

### 1. Grafana Dashboard
![Grafana Dashboard](screenshots/challenge1/grafana_dashboard_full.png)
*Figure 1: Complete Challenge 1 dashboard showing all metrics*

### 2. Latency Metrics
![Latency Chart](screenshots/challenge1/grafana_latency_p50_p95_p99.png)
*Figure 2: Ingestion latency (p50/p95/p99) by source - all sources < 5 min SLA*

[... continue for all screenshots ...]
```

Save as: `CHALLENGE1_VISUAL_EVIDENCE.pdf`

---

---

## Troubleshooting

### Issue: "Dashboard not found" error

**Problem**: Opening http://localhost:3010/d/challenge1-ingestion shows "Dashboard not found"

**Solutions**:
1. **Import the dashboard first**:
   ```bash
   # In Grafana UI:
   # + → Import → Upload JSON file → Select challenge1_latency_dashboard.json
   ```

2. **Check if Grafana is running**:
   ```bash
   docker-compose ps grafana
   # Should show "Up (healthy)"
   ```

3. **Check Grafana logs**:
   ```bash
   docker-compose logs grafana | grep -i error
   ```

4. **Manually verify dashboard UID**:
   ```bash
   grep '"uid"' C:\dev\wildfire\docs\grafana\challenge1_latency_dashboard.json
   # Should show: "uid": "challenge1-ingestion"
   ```

### Issue: Dashboard panels show "No data"

**Problem**: Dashboard loads but panels are empty

**Solutions**:
1. **Check Prometheus is running**:
   ```bash
   docker-compose ps prometheus
   curl http://localhost:9090/-/healthy
   ```

2. **Verify metrics are being collected**:
   ```bash
   curl http://localhost:9090/api/v1/query?query=ingestion_latency_seconds_count
   # Should return data
   ```

3. **Check data-ingestion-service is running**:
   ```bash
   docker-compose ps data-ingestion-service
   curl http://localhost:8003/health
   ```

4. **Trigger manual data ingestion**:
   ```bash
   curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger
   # Wait 30 seconds, then refresh dashboard
   ```

### Issue: Grafana login fails

**Problem**: Cannot login with admin/admin

**Solutions**:
1. **Reset Grafana admin password**:
   ```bash
   docker-compose exec grafana grafana-cli admin reset-admin-password admin
   ```

2. **Check Grafana container logs**:
   ```bash
   docker-compose logs grafana | tail -50
   ```

3. **Restart Grafana**:
   ```bash
   docker-compose restart grafana
   # Wait 10 seconds, then try login again
   ```
