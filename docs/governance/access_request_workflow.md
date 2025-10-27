# CAL FIRE Wildfire Intelligence Platform - Data Access Request Workflow

**Document Version**: 1.0.0
**Effective Date**: October 2025
**Owner**: CAL FIRE Data Governance Team
**SLA**: 24 hours for standard requests, 4 hours for emergency requests

---

## 1. Executive Summary

This document defines the standardized workflow for requesting and granting access to wildfire intelligence data assets. All access requests must follow this process to ensure compliance with security policies, regulatory requirements, and operational best practices.

---

## 2. Access Request Types

### 2.1 Standard Access Request
- **Use Case**: Routine data access for analysis, reporting, dashboard creation
- **SLA**: 24 hours for approval
- **Approval Chain**: Data Steward → Data Owner

### 2.2 Emergency Access Request
- **Use Case**: Active wildfire incident response, life-safety situations
- **SLA**: 4 hours for approval (verbal approval, written confirmation within 24 hours)
- **Approval Chain**: Incident Commander → Data Steward (concurrent)

### 2.3 Elevated Privilege Request
- **Use Case**: Write access, delete permissions, admin rights
- **SLA**: 48 hours for approval
- **Approval Chain**: Data Steward → Data Owner → Security Team → CISO

### 2.4 External Partner Request
- **Use Case**: University researchers, federal agencies (FEMA, NOAA, USFS)
- **SLA**: 5 business days for approval
- **Approval Chain**: Data Steward → Legal Team → Data Owner → External Relations

---

## 3. Access Request Workflow

```
┌─────────────────┐
│  User Submits   │
│  Access Request │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Auto-Validation │
│ (Identity, Role)│
└────────┬────────┘
         │
         ▼
    ┌────────┐
    │Valid?  │───No───► Reject & Notify User
    └────┬───┘
         │Yes
         ▼
┌─────────────────┐
│ Classification  │
│ Check           │
└────────┬────────┘
         │
         ▼
    ┌──────────────┐
    │ Public Data? │───Yes───► Auto-Approve (Log Only)
    └──────┬───────┘
           │No
           ▼
    ┌─────────────────┐
    │ Internal Data?  │───Yes───► Data Steward Review
    └──────┬──────────┘
           │No
           ▼
    ┌─────────────────┐
    │ Restricted Data?│───Yes───► Data Steward + Owner Review
    └──────┬──────────┘
           │No
           ▼
    ┌─────────────────┐
    │ Regulated Data? │───Yes───► Full Approval Chain + Legal
    └──────┬──────────┘
           │
           ▼
    ┌─────────────────┐
    │ Approval        │
    │ Decision        │
    └──────┬──────────┘
           │
           ▼
    ┌────────────┐
    │ Approved?  │───No───► Reject & Notify with Reason
    └──────┬─────┘
           │Yes
           ▼
    ┌─────────────────┐
    │ Grant Access    │
    │ (IAM Policy)    │
    └──────┬──────────┘
           │
           ▼
    ┌─────────────────┐
    │ Notify User     │
    │ & Log Event     │
    └─────────────────┘
```

---

## 4. Access Request Form

### 4.1 Required Information

**Section 1: Requester Information**
- Full Name
- CAL FIRE Email Address
- Department/Unit
- Manager/Supervisor Name
- Employee ID / Badge Number
- Phone Number (for emergency requests)

**Section 2: Access Details**
- Data Source(s) Requested (select from catalog)
- Classification Level (auto-populated based on source)
- Access Type: [ ] Read-Only [ ] Read-Write [ ] Admin
- Date Range Needed (if time-bound access)
- Access Duration: [ ] Temporary (30/60/90 days) [ ] Permanent

**Section 3: Business Justification**
- Use Case Description (minimum 50 words)
- Expected Query Frequency (queries/day)
- Downstream Systems/Tools (Grafana, Jupyter, Excel, etc.)
- Business Impact if Access Denied: [ ] Low [ ] Medium [ ] High [ ] Critical

**Section 4: Security Acknowledgements**
- [ ] I have completed Data Security Training (annual requirement)
- [ ] I understand data classification restrictions
- [ ] I will not share credentials or export restricted data
- [ ] I acknowledge access logs are monitored and audited

**Section 5: Emergency Access Only**
- Incident Number/Name
- Incident Commander Contact
- Life-Safety Risk Assessment: [ ] Yes [ ] No
- Expected Resolution Date

---

## 5. Approval Matrix

| Classification | Access Type | Approvers Required | SLA |
|---------------|-------------|-------------------|-----|
| **Public** | Read-Only | Auto-Approve (log only) | Immediate |
| **Public** | Read-Write | Data Steward | 24 hours |
| **Internal** | Read-Only | Data Steward | 24 hours |
| **Internal** | Read-Write | Data Steward + Owner | 48 hours |
| **Restricted** | Read-Only | Data Steward + Owner | 48 hours |
| **Restricted** | Read-Write | Data Steward + Owner + Security | 72 hours |
| **Restricted** | Admin | Data Steward + Owner + Security + CISO | 5 business days |
| **Regulated** | Any Access | Data Steward + Owner + Legal + CISO | 5 business days |

### Emergency Override
- Incident Commander can grant **temporary read-only access** to Internal/Restricted data
- Access expires in 72 hours unless extended by Data Steward
- Verbal approval acceptable, written confirmation required within 24 hours

---

## 6. Access Provisioning Process

### 6.1 IAM Policy Creation
Once approved, access is granted via AWS IAM / Azure AD policy:

**Example IAM Policy (Read-Only Internal Data)**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::wildfire-data-lake/internal/*"
      ],
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": "192.0.2.0/24"
        }
      }
    }
  ]
}
```

### 6.2 Database Access Provisioning
For PostgreSQL access:
```sql
-- Create role for user
CREATE ROLE analyst_john_doe LOGIN PASSWORD 'secure_password';

-- Grant schema access
GRANT USAGE ON SCHEMA public TO analyst_john_doe;

-- Grant read-only access to internal tables
GRANT SELECT ON firms_modis_terra_detections TO analyst_john_doe;
GRANT SELECT ON firesat_perimeters TO analyst_john_doe;

-- Row-level security (RLS) for restricted data
CREATE POLICY analyst_rls ON firesat_perimeters
  FOR SELECT
  TO analyst_john_doe
  USING (classification = 'internal' OR classification = 'public');
```

### 6.3 MinIO Access (Object Storage)
For MinIO bucket access:
```bash
# Create MinIO user
mc admin user add wildfire-minio analyst_john_doe secure_password

# Attach read-only policy
mc admin policy set wildfire-minio readonly user=analyst_john_doe

# Restrict to specific bucket
mc admin policy add wildfire-minio analyst-policy policy.json
mc admin policy set wildfire-minio analyst-policy user=analyst_john_doe
```

---

## 7. Access Review and Recertification

### 7.1 Quarterly Access Review
- **Schedule**: 1st business day of each quarter (Jan, Apr, Jul, Oct)
- **Process**:
  1. Data Steward exports active access list
  2. Each Data Owner reviews their domain (30-day window)
  3. Inactive users (90+ days no queries) flagged for removal
  4. Managers re-certify active users

### 7.2 Annual Recertification
- **Requirement**: All users must re-certify access annually
- **Process**:
  1. User receives email notification 30 days before expiration
  2. User re-submits access request form
  3. Manager approval required (even if previously approved)
  4. Data Security Training must be current

### 7.3 Automatic Revocation Triggers
- **90 Days Inactive**: Read-only access suspended, notification sent
- **180 Days Inactive**: Access fully revoked
- **Employee Termination**: Access revoked within 1 hour (HR system integration)
- **Role Change**: Access re-evaluated within 5 business days
- **Security Incident**: Access suspended immediately pending investigation

---

## 8. Access Monitoring and Auditing

### 8.1 Real-Time Monitoring
- **CloudTrail Logs**: All S3/RDS/MinIO access logged
- **PostgreSQL Audit**: `pgaudit` extension tracks all queries
- **SIEM Integration**: Logs forwarded to Splunk/ELK for anomaly detection

### 8.2 Alerting Rules
- **Alert**: User accessing >10,000 records in single query (potential data exfiltration)
- **Alert**: Access from unexpected IP/country (geolocation check)
- **Alert**: Failed authentication attempts >5 in 10 minutes (brute force)
- **Alert**: Bulk download detected (>1GB in 1 hour)

### 8.3 Audit Reports
- **Weekly**: Access request metrics (approved/rejected/pending)
- **Monthly**: Top 10 users by query volume
- **Quarterly**: Access review completion status
- **Annual**: Compliance audit report (SOC 2, FISMA)

---

## 9. Access Request Templates

### 9.1 ServiceNow Ticket Template
```
Title: Data Access Request - [Data Source Name]

Category: Data Access
Priority: [Standard / Emergency]
Requester: [Full Name]
Department: [Unit/Division]

Description:
I am requesting [Read-Only / Read-Write / Admin] access to [Data Source Name]
for the following business purpose:

[Insert business justification - minimum 50 words]

Expected Usage:
- Query Frequency: [X queries/day]
- Tools: [Grafana / Jupyter / Excel / etc.]
- Duration: [30/60/90 days / Permanent]

I have completed Data Security Training: [Yes / No]
Training Completion Date: [YYYY-MM-DD]

Manager Approval: [Manager Name / Email]

For Emergency Requests Only:
- Incident Number: [INC-YYYY-XXXXX]
- Incident Commander: [Name / Contact]
```

### 9.2 Email Request Template (Emergency Only)
```
Subject: URGENT: Emergency Data Access Request - [Incident Name]

To: data-steward@calfire.ca.gov
CC: [Incident Commander Email]

Incident: [Incident Number/Name]
Requester: [Full Name / Badge ID]
Data Source Needed: [Source Name]
Access Type: Read-Only (emergency override)

Justification:
[Describe life-safety or incident response need]

Incident Commander Verbal Approval: [Yes / No]
Expected Access Duration: [Hours/Days]

I acknowledge this access will be logged and reviewed.
Written confirmation to follow within 24 hours.

[Name]
[Contact Number]
```

---

## 10. Denial and Appeal Process

### 10.1 Denial Reasons
Common reasons for access denial:
- Insufficient business justification
- Data Security Training not current
- Role does not require access (principle of least privilege)
- Classification level exceeds user clearance
- Technical constraints (data not yet available)

### 10.2 Appeal Process
1. User receives denial notification with reason
2. User can appeal to Data Governance Committee within 10 business days
3. Committee reviews appeal at next scheduled meeting (bi-weekly)
4. Decision is final, logged in audit trail
5. User notified within 48 hours of committee decision

---

## 11. Temporary Access and Expiration

### 11.1 Temporary Access Grants
- **Default Duration**: 90 days for project-based access
- **Reminder**: User notified 14 days before expiration
- **Extension Request**: Must be submitted 7 days before expiration
- **Auto-Revocation**: Access removed automatically at expiration

### 11.2 Time-Bound Access for External Partners
- **Duration**: Defined in data sharing agreement (typically 12 months)
- **Review**: 30-day review before renewal
- **Legal Approval**: Required for any extension beyond initial term

---

## 12. Contact Information

| Function | Contact | Hours |
|----------|---------|-------|
| **Access Requests** | access-request@calfire.ca.gov | 24/7 (monitored) |
| **Data Steward** | steward@calfire.ca.gov | M-F 8am-5pm PT |
| **Emergency Access** | +1-916-555-FIRE (3473) | 24/7 |
| **Security Team** | security@calfire.ca.gov | 24/7 |
| **Help Desk** | helpdesk@calfire.ca.gov | 24/7 |

---

## 13. Appendix: Access Request Decision Tree

```
START: User needs data access
│
├─ Is data classification PUBLIC?
│  ├─ YES → Is access Read-Only?
│  │       ├─ YES → AUTO-APPROVE (log only)
│  │       └─ NO → Data Steward Review
│  └─ NO → Continue
│
├─ Is data classification INTERNAL?
│  ├─ YES → Is access Read-Only?
│  │       ├─ YES → Data Steward Review (24hr SLA)
│  │       └─ NO → Data Steward + Owner Review (48hr SLA)
│  └─ NO → Continue
│
├─ Is data classification RESTRICTED?
│  ├─ YES → Is this an emergency (incident response)?
│  │       ├─ YES → Incident Commander Approval (4hr SLA)
│  │       └─ NO → Data Steward + Owner + Security (72hr SLA)
│  └─ NO → Continue
│
└─ Data classification REGULATED
   └─ Full approval chain required:
      1. Data Steward
      2. Data Owner
      3. Legal Team
      4. CISO
      SLA: 5 business days
```

---

**Document Control**:
- **Created**: 2025-10-06
- **Last Updated**: 2025-10-06
- **Next Review**: 2026-04-06 (semi-annual)
- **Approvals**:
  - Data Governance Lead: [Pending]
  - Security Team: [Pending]
  - Legal Counsel: [Pending]
