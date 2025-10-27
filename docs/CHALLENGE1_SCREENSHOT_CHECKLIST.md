# Challenge 1: Screenshot Capture Checklist
## Quick Reference for All 19 Required Screenshots

**Purpose**: Quick checklist for capturing all Challenge 1 visual evidence
**Save Location**: `C:\dev\wildfire\docs\screenshots\challenge1\`
**Total Screenshots**: 19
**Time Required**: 30-45 minutes
**Last Updated**: 2025-01-05

---

## Prerequisites

Before capturing screenshots:

- [ ] All Docker containers running: `docker compose ps` (all show "healthy")
- [ ] Grafana dashboard imported: `docs/grafana/challenge1_latency_dashboard.json`
- [ ] Data ingested: Run `curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger`
- [ ] Wait 2 minutes for data to populate in dashboard
- [ ] Screenshot tool ready: Windows Snipping Tool (Win + Shift + S) or Greenshot

---

## Screenshot Checklist

### 1. Grafana Dashboards (5 screenshots)

- [ ] **1. grafana_dashboard_full.png** ⭐ **MOST IMPORTANT**
  - URL: http://localhost:3010/d/challenge1-ingestion
  - Wait for all panels to load (30-60 seconds)
  - Press F11 for fullscreen
  - Capture full page (use scrolling screenshot tool)
  - Shows: All 10 panels with data

- [ ] **2. grafana_latency_p50_p95_p99.png**
  - Same URL, focus on Panel #1
  - Click panel title → "View" for expanded view
  - Shows: Latency chart with 3 lines (p50/p95/p99)

- [ ] **3. grafana_validation_pass_rate.png**
  - Focus on Panel #2
  - Shows: Gauge charts showing >95% for all sources

- [ ] **4. grafana_sla_widgets.png**
  - Focus on Panels #5, #6, #7
  - Shows: Three SLA compliance widgets (all green)

- [ ] **5. grafana_failed_messages_table.png**
  - Focus on Panel #8
  - Shows: Table of failed messages (may be empty - OK)

---

### 2. Prometheus (2 screenshots)

- [ ] **6. prometheus_targets_up.png**
  - URL: http://localhost:9090/targets
  - Shows: All targets with "UP" status (green)

- [ ] **7. prometheus_latency_query.png**
  - URL: http://localhost:9090/graph
  - Query: `histogram_quantile(0.95, sum(rate(ingestion_latency_seconds_bucket[5m])) by (le, source))`
  - Click "Execute" → "Graph" tab
  - Shows: Latency graph with multiple lines

---

### 3. Service Health (3 screenshots)

- [ ] **8. docker_compose_ps_healthy.png**
  - Command: `docker compose ps`
  - Capture terminal output
  - Shows: All 25 containers with "Up (healthy)" status

- [ ] **9. data_ingestion_health_check.png**
  - URL: http://localhost:8003/health
  - Shows: JSON response with status: "healthy"

- [ ] **10. swagger_ui_ingestion_endpoints.png**
  - URL: http://localhost:8003/docs
  - Expand "Ingestion" tag
  - Shows: All ingestion endpoints listed

---

### 4. Database (2 screenshots)

- [ ] **11. postgres_fire_detections_sample.png**
  - Command: `docker exec wildfire-postgres psql -U wildfire_user -d wildfire_db -c "SELECT source, COUNT(*) as count, MIN(detection_time_pst) as earliest, MAX(detection_time_pst) as latest FROM fire_detections GROUP BY source ORDER BY count DESC;"`
  - Shows: Query results with row counts by source

- [ ] **12. postgres_quality_metrics.png**
  - Command: `docker exec wildfire-postgres psql -U wildfire_user -d wildfire_db -c "SELECT source, AVG(quality_score) as avg_quality, COUNT(*) as total_records FROM data_quality_checks WHERE checked_at > NOW() - INTERVAL '1 hour' GROUP BY source;"`
  - Shows: Quality scores (all >0.95)
  - **Note**: Table may not exist yet, can skip if error

---

### 5. Kafka (2 screenshots)

- [ ] **13. kafka_topics_list.png**
  - Command: `docker exec wildfire-kafka kafka-topics --bootstrap-server localhost:9092 --list`
  - Shows: List of wildfire-* topics

- [ ] **14. kafka_consumer_groups.png**
  - Command: `docker exec wildfire-kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list`
  - Shows: Consumer group names

---

### 6. Sample Data (2 screenshots)

- [ ] **15. sample_firms_data_excel.png**
  - Open: `C:\dev\wildfire\services\data-ingestion-service\examples\input\sample_firms.csv`
  - Use Excel or VS Code
  - Shows: First 10 rows with column headers

- [ ] **16. sample_mqtt_payload_formatted.png**
  - Open: `C:\dev\wildfire\services\data-ingestion-service\examples\input\sample_mqtt_sensor.json`
  - Use VS Code, format with Alt + Shift + F
  - Shows: Formatted JSON structure

---

### 7. MinIO (1 screenshot)

- [ ] **17. minio_console_buckets.png**
  - URL: http://localhost:9001
  - Login: minioadmin / minioadminpassword
  - Navigate to "Buckets"
  - Shows: List of buckets (wildfire-raw-data, wildfire-processed-data, wildfire-backups)

---

### 8. Architecture Diagram (1 screenshot)

- [ ] **18. architecture_diagram.png**
  - Open: `docs/CHALLENGE1_ARCHITECTURE_DIAGRAMS.md`
  - Copy Mermaid code for Diagram #1 (System Overview)
  - Paste to https://mermaid.live
  - Export as PNG (2000x1500 resolution)
  - Or: Use VS Code with Mermaid preview extension

---

### 9. Test Execution (1 screenshot)

- [ ] **19. test_execution_output.png**
  - Command: `curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger -H "Content-Type: application/json" -d '{"area": "california", "lookback_hours": 24}'`
  - Capture terminal showing command + JSON response
  - Shows: Success message with detections_fetched count

---

## Screenshot Quality Guidelines

### Resolution
- **Minimum**: 1920x1080
- **Preferred**: 2560x1440 or higher
- **Format**: PNG (lossless compression)

### Content
- ✅ Include timestamps where visible
- ✅ Show full context (entire window, not cropped)
- ✅ Ensure text is readable (zoom if needed)
- ❌ No personal information (API keys already in .env, safe to show)

### File Naming
- Use exact names from checklist (case-sensitive)
- Save to: `C:\dev\wildfire\docs\screenshots\challenge1\`
- Example: `C:\dev\wildfire\docs\screenshots\challenge1\grafana_dashboard_full.png`

---

## Verification

After capturing all screenshots:

```powershell
# Count screenshots
(Get-ChildItem "C:\dev\wildfire\docs\screenshots\challenge1\" -Filter *.png).Count

# Expected: 19 files
```

---

## Quick Capture Script (PowerShell)

```powershell
# Create screenshots directory
New-Item -Path "C:\dev\wildfire\docs\screenshots\challenge1" -ItemType Directory -Force

# Open all URLs in browser (for easy capture)
Start-Process "http://localhost:3010/d/challenge1-ingestion"
Start-Sleep -Seconds 2
Start-Process "http://localhost:9090/targets"
Start-Sleep -Seconds 2
Start-Process "http://localhost:8003/docs"
Start-Sleep -Seconds 2
Start-Process "http://localhost:9001"

Write-Host "✅ All URLs opened in browser"
Write-Host "📸 Use Win+Shift+S to capture screenshots"
Write-Host "💾 Save to: C:\dev\wildfire\docs\screenshots\challenge1\"
```

---

## Troubleshooting

### Issue: Dashboard Shows "No Data"

**Solution**:
1. Trigger ingestion: `curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger`
2. Wait 30 seconds
3. Refresh Grafana dashboard (Ctrl + R)
4. Check data exists: `docker exec wildfire-postgres psql -U wildfire_user -d wildfire_db -c "SELECT COUNT(*) FROM fire_detections;"`

### Issue: Container Not Healthy

**Solution**:
```powershell
# Check logs
docker logs wildfire-data-ingestion-service --tail 50

# Restart container
docker compose restart data-ingestion-service

# Wait 30 seconds
Start-Sleep -Seconds 30
```

### Issue: Can't Access URL

**Solution**:
```powershell
# Verify container is running
docker compose ps | Select-String "grafana"

# Check port mapping
docker ps | Select-String "3010"

# Restart all services
docker compose restart
```

---

## Next Steps

After capturing all 19 screenshots:

1. **Review Quality**: Open each screenshot, ensure text is readable
2. **Insert into Presentation**: Use `CHALLENGE1_PRESENTATION_SLIDES.md` template
3. **Create PowerPoint**: Import screenshots into slide deck
4. **Generate PDF**: Export presentation as PDF for submission

---

## Screenshot Mapping to Deliverables

| Deliverable | Screenshots | Count |
|-------------|-------------|-------|
| #1: Architectural Blueprint | architecture_diagram.png | 1 |
| #2: Data Ingestion Prototype | test_execution_output.png, postgres_fire_detections_sample.png | 2 |
| #3-6: Data Sources | sample_firms_data_excel.png, sample_mqtt_payload_formatted.png | 2 |
| #7: Schema Validation | grafana_validation_pass_rate.png | 1 |
| #10: DLQ | grafana_failed_messages_table.png | 1 |
| #12: Monitoring Dashboard | grafana_* (5 screenshots), prometheus_* (2 screenshots) | 7 |
| #13: API Documentation | swagger_ui_ingestion_endpoints.png, data_ingestion_health_check.png | 2 |
| #14: User Guide | All screenshots | 19 (all used) |

---

## Time Estimate

| Task | Time |
|------|------|
| Start services (if stopped) | 3 min |
| Trigger data ingestion | 2 min |
| Wait for data to populate | 2 min |
| Capture 19 screenshots | 20 min |
| Verify quality | 5 min |
| **Total** | **~30 minutes** |

---

## Quick Reference Card

**Essential Commands**:
```powershell
# Start services
docker compose up -d

# Trigger ingestion
curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger

# Check data
docker exec wildfire-postgres psql -U wildfire_user -d wildfire_db -c "SELECT COUNT(*) FROM fire_detections;"

# Create screenshot directory
New-Item -Path "C:\dev\wildfire\docs\screenshots\challenge1" -ItemType Directory -Force
```

**Essential URLs**:
- Grafana: http://localhost:3010/d/challenge1-ingestion
- Prometheus: http://localhost:9090
- Swagger: http://localhost:8003/docs
- MinIO: http://localhost:9001

**Screenshot Save Location**:
```
C:\dev\wildfire\docs\screenshots\challenge1\
```

---

**Prepared by**: CAL FIRE Wildfire Intelligence Platform Team
**Challenge**: Challenge 1 - Data Sources & Ingestion Mechanisms
**Screenshots**: 19 required
**Time**: ~30 minutes
**Document Version**: 1.0
