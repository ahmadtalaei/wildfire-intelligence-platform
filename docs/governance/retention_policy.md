# CAL FIRE Wildfire Intelligence Platform - Data Retention Policy

**Document Version**: 1.0.0
**Effective Date**: October 2025
**Owner**: CAL FIRE Data Governance Team
**Review Cycle**: Annual

---

## 1. Executive Summary

This document defines the data retention and lifecycle management policies for the CAL FIRE Wildfire Intelligence Platform. All data assets must adhere to these retention schedules to ensure compliance with regulatory requirements, optimize storage costs, and maintain operational efficiency.

---

## 2. Retention Schedules by Classification

| Classification | Retention Period | Storage Tier Progression | Legal Basis |
|---------------|------------------|--------------------------|-------------|
| **Public** | 90 days → Archive 7 years | Hot (7d) → Warm (90d) → Archive (7y) | FISMA, NIST 800-53 |
| **Internal** | 90 days → Archive 7 years | Hot (7d) → Warm (90d) → Archive (7y) | FISMA, NIST 800-53, SOC2 |
| **Restricted** | 365 days → Archive 7 years | Hot (30d) → Warm (90d) → Cold (365d) → Archive (7y) | FISMA, NIST 800-53, SOC2, CCPA |
| **Regulated** | Permanent + Legal Hold | Hot (30d) → Archive (Permanent) | FISMA, CCPA, Legal Requirements |

---

## 3. Storage Tier Transition Rules

### 3.1 Hot Storage (0-7 days for standard data, 0-30 days for restricted)
- **Technology**: PostgreSQL, Redis, InfluxDB
- **Access Pattern**: Real-time, low-latency (<100ms)
- **Transition Trigger**: Age-based (7 days for public/internal, 30 days for restricted)
- **Cost**: ~$0.023/GB/month

**Data Types**:
- Active fire detections (FIRMS MODIS, VIIRS, FireSat)
- Real-time weather observations (NOAA METAR)
- Live sensor readings (IoT weather stations, air quality)
- Near real-time satellite imagery (Landsat NRT, Sentinel-3)

### 3.2 Warm Storage (7-90 days)
- **Technology**: MinIO, S3 Standard
- **Access Pattern**: Frequent access (1-10 queries/hour)
- **Transition Trigger**: Automated at day 7 (or day 30 for restricted)
- **Cost**: ~$0.021/GB/month

**Data Types**:
- Historical fire perimeters (7-90 days old)
- Weather forecast archives (NOAA GFS/NAM)
- Aggregated sensor data
- Dashboard query cache

### 3.3 Cold Storage (90-365 days)
- **Technology**: S3 Glacier Instant Retrieval, Azure Cool Blob
- **Access Pattern**: Infrequent access (monthly reports, audits)
- **Transition Trigger**: Automated at day 90
- **Cost**: ~$0.004/GB/month

**Data Types**:
- Seasonal fire analysis datasets
- Annual compliance reports
- Long-term trend analysis data
- Decommissioned sensor archives

### 3.4 Archive Storage (7+ years)
- **Technology**: S3 Glacier Deep Archive, Azure Archive Blob
- **Access Pattern**: Rare access (legal/regulatory requests only)
- **Transition Trigger**: Automated at day 365
- **Retrieval Time**: 12-48 hours
- **Cost**: ~$0.00099/GB/month

**Data Types**:
- Historical incident records (7+ years)
- Regulatory compliance archives
- Legal discovery datasets
- Long-term climate research data

---

## 4. Retention Policies by Data Source

| Source ID | Classification | Hot Period | Warm Period | Cold Period | Archive Period | Notes |
|-----------|---------------|------------|-------------|-------------|----------------|-------|
| `firms_modis_terra` | Internal | 7 days | 90 days | 365 days | 7 years | Fire detection - mission critical |
| `firms_modis_aqua` | Internal | 7 days | 90 days | 365 days | 7 years | Fire detection - mission critical |
| `firms_viirs_snpp` | Internal | 7 days | 90 days | 365 days | 7 years | Fire detection - mission critical |
| `firms_viirs_noaa20` | Internal | 7 days | 90 days | 365 days | 7 years | Fire detection - mission critical |
| `firms_viirs_noaa21` | Internal | 7 days | 90 days | 365 days | 7 years | Fire detection - mission critical |
| `firesat_detections` | Internal | 7 days | 90 days | 365 days | 7 years | High-resolution fire detection |
| `firesat_perimeters` | Restricted | 30 days | 90 days | 365 days | Permanent | Incident response data |
| `firesat_thermal` | Internal | 7 days | 90 days | 365 days | 7 years | Thermal imagery analysis |
| `landsat_nrt` | Internal | 7 days | 90 days | 365 days | 7 years | Satellite imagery |
| `sentinel3_slstr` | Internal | 7 days | 90 days | 365 days | 7 years | Satellite thermal data |
| `noaa_gfs_forecast` | Public | 7 days | 30 days | N/A | 1 year | Weather forecast archive |
| `noaa_nam_forecast` | Public | 7 days | 30 days | N/A | 1 year | Regional forecast archive |
| `noaa_alerts_active` | Restricted | 30 days | 90 days | 365 days | Permanent | Emergency alerts |
| `era5_reanalysis` | Public | 7 days | 90 days | 365 days | Permanent | Climate research |
| `metar_observations` | Public | 7 days | 30 days | 90 days | 1 year | Weather observations |
| `airnow_observations` | Public | 7 days | 30 days | 90 days | 1 year | Air quality monitoring |
| `purpleair_sensors` | Internal | 7 days | 30 days | 90 days | 1 year | Community sensor data |
| `iot_weather_stations` | Internal | 7 days | 30 days | 90 days | 1 year | IoT sensor telemetry |
| `iot_soil_moisture` | Internal | 7 days | 30 days | 90 days | 1 year | IoT sensor telemetry |

---

## 5. Legal Hold Procedures

### 5.1 Legal Hold Activation
When a legal hold is placed on data:
1. **Immediate Actions**:
   - Flag asset with `retention_legal_hold: true` in metadata
   - Suspend all automated deletion policies
   - Move to dedicated legal hold storage bucket
   - Notify data steward and legal team

2. **Storage Tier Override**:
   - Keep data in current tier (do not archive)
   - If already in archive, restore to warm storage
   - Maintain access logs for all legal hold data

3. **Access Control**:
   - Restrict access to authorized legal team only
   - Require multi-factor authentication
   - Log all access events with user attribution

### 5.2 Legal Hold Release
When legal hold is lifted:
1. Remove `retention_legal_hold: true` flag
2. Re-evaluate retention schedule based on data age
3. Apply appropriate tier transition immediately
4. Document hold duration and release authorization

---

## 6. Data Deletion Procedures

### 6.1 Automated Deletion
- **Trigger**: Retention period expiration
- **Process**: S3 Lifecycle policies, PostgreSQL scheduled jobs
- **Verification**: Checksum validation before deletion
- **Logging**: Deletion events logged to audit trail

### 6.2 Manual Deletion (Restricted Access Only)
- **Authorization**: Requires data steward approval
- **Process**:
  1. Submit deletion request via ServiceNow ticket
  2. Data steward reviews and approves
  3. Execute deletion with `DELETE_RETENTION_OVERRIDE` privilege
  4. Log deletion event with justification
  5. Verify deletion completion

### 6.3 Secure Deletion Standards
- **Cloud Storage**: Use `aws s3 rm --delete-marker` (S3) or `az storage blob delete --soft-delete` (Azure)
- **Database**: `DELETE FROM table WHERE id IN (...); VACUUM FULL;`
- **Object Storage**: MinIO with versioning disabled ensures permanent deletion
- **Compliance**: NIST 800-88 media sanitization guidelines

---

## 7. Compliance Requirements

### 7.1 FISMA (Federal Information Security Management Act)
- **Requirement**: Retain security audit logs for 7 years
- **Implementation**: All access logs, system events archived to Glacier Deep Archive
- **Verification**: Annual compliance audit

### 7.2 NIST 800-53 (Security and Privacy Controls)
- **Requirement**: Audit trail retention (AU-11)
- **Implementation**: Immutable audit logs in S3 with Object Lock
- **Verification**: Quarterly security review

### 7.3 SOC 2 (Service Organization Control 2)
- **Requirement**: Demonstrate data lifecycle management
- **Implementation**: Automated tier transitions with audit trail
- **Verification**: Annual SOC 2 Type II audit

### 7.4 CCPA (California Consumer Privacy Act)
- **Requirement**: Delete consumer data upon request (if PII present)
- **Implementation**: Data classification scan for PII, manual deletion workflow
- **Verification**: 30-day deletion SLA monitoring

---

## 8. Monitoring and Reporting

### 8.1 Key Metrics
- **Storage Distribution**: % of data in each tier (Hot/Warm/Cold/Archive)
- **Retention Compliance**: % of assets following retention schedule
- **Cost Efficiency**: $/GB by tier, monthly trend
- **Legal Hold Count**: Active legal holds by data source

### 8.2 Dashboards
- **Grafana Panel**: "Storage Tier Distribution" (pie chart)
- **Grafana Panel**: "Retention Policy Compliance" (gauge, target 95%)
- **Grafana Panel**: "Storage Cost by Tier" (timeseries)

### 8.3 Alerts
- **Alert**: Legal hold data approaching 1 year (manual review required)
- **Alert**: Retention policy violation detected (auto-remediate)
- **Alert**: Storage tier transition failure (ops team notification)

---

## 9. Exceptions and Approvals

### 9.1 Retention Extension Request
- **Process**: Submit to data governance committee
- **Approval**: Requires 2/3 committee vote
- **Documentation**: Must include business justification and cost analysis

### 9.2 Early Deletion Request
- **Process**: Submit to data steward with legal review
- **Approval**: Requires legal sign-off + data owner approval
- **Documentation**: Retention override logged in audit trail

---

## 10. Review and Update Cycle

- **Annual Review**: October (start of California fire season)
- **Trigger for Ad-Hoc Review**:
  - New regulatory requirements
  - Major incident response (wildfire disaster)
  - Significant cost variance (>20% deviation)
  - Technology stack changes (new storage platform)

---

## 11. Contact Information

| Role | Contact | Responsibility |
|------|---------|---------------|
| **Data Governance Lead** | governance@calfire.ca.gov | Policy updates, exception approvals |
| **Data Steward** | steward@calfire.ca.gov | Daily retention monitoring, access requests |
| **Legal Team** | legal@calfire.ca.gov | Legal holds, compliance interpretation |
| **Operations Team** | ops@calfire.ca.gov | Storage tier management, technical execution |

---

**Document Control**:
- **Created**: 2025-10-06
- **Last Updated**: 2025-10-06
- **Next Review**: 2026-10-06
- **Approvals**:
  - Data Governance Lead: [Pending]
  - Legal Counsel: [Pending]
  - CISO: [Pending]
