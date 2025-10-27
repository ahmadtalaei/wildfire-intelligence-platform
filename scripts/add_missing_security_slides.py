#!/usr/bin/env python3
"""
Add missing Security slides 24 and 26 to Challenge 3 presentation
"""

def generate_slide_24():
    """Slide 24: Data Security Protocols"""
    return """
## Slide 24: Data Security Protocols

### **Comprehensive Data Protection Strategy**

```mermaid
graph TB
    subgraph "Data Security Layers"
        subgraph "Classification Layer"
            CLASSIFY[Data Classification Engine]
            PUBLIC[PUBLIC: Open datasets]
            INTERNAL[INTERNAL: Operational data]
            CONFIDENTIAL[CONFIDENTIAL: Restricted]
            RESTRICTED[RESTRICTED: Highly sensitive]
        end

        subgraph "Protection Layer"
            ENCRYPT[Encryption Service]
            MASK[Data Masking]
            TOKENIZE[Tokenization]
            REDACT[PII Redaction]
        end

        subgraph "Access Layer"
            AUTHZ[Authorization Check]
            DECRYPT[Decryption Service]
            WATERMARK[Digital Watermarking]
            LOG[Access Logging]
        end

        subgraph "Monitoring Layer"
            DLP[Data Loss Prevention]
            ANOMALY[Anomaly Detection]
            ALERT[Security Alerts]
            INCIDENT[Incident Response]
        end
    end

    CLASSIFY --> PUBLIC
    CLASSIFY --> INTERNAL
    CLASSIFY --> CONFIDENTIAL
    CLASSIFY --> RESTRICTED

    PUBLIC --> AUTHZ
    INTERNAL --> ENCRYPT
    CONFIDENTIAL --> MASK
    RESTRICTED --> TOKENIZE

    ENCRYPT --> AUTHZ
    MASK --> AUTHZ
    TOKENIZE --> AUTHZ

    AUTHZ -->|Approved| DECRYPT
    AUTHZ -->|Denied| LOG

    DECRYPT --> WATERMARK
    WATERMARK --> LOG

    LOG --> DLP
    DLP --> ANOMALY
    ANOMALY --> ALERT
    ALERT --> INCIDENT

    style CLASSIFY fill:#4ecdc4
    style ENCRYPT fill:#f38181
    style AUTHZ fill:#ffe66d
    style DLP fill:#aa96da
    style ALERT fill:#ff6b6b
```

**DATA SECURITY PROTOCOLS:**
```
┌─────────────────────────────────────────────────────────────────┐
│              DATA SECURITY PROTOCOLS FRAMEWORK                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DATA CLASSIFICATION (4 LEVELS):                                │
│                                                                 │
│  LEVEL 1: PUBLIC                                                │
│  • Description: Publicly available datasets                     │
│  • Examples: Historical fire perimeters, county boundaries      │
│  • Protection: None (already public domain)                     │
│  • Access: No authentication required                           │
│  • Export: Unlimited, no watermarking                           │
│  • Volume: 15% of total data (450 GB)                          │
│                                                                 │
│  LEVEL 2: INTERNAL                                              │
│  • Description: Internal operational data                       │
│  • Examples: Real-time fire detections, weather data            │
│  • Protection: Encryption at rest (AES-256)                    │
│  • Access: Authenticated CAL FIRE users only                    │
│  • Export: Rate-limited (1,000 records/hr)                     │
│  • Watermarking: User ID + timestamp embedded                   │
│  • Volume: 70% of total data (2.1 TB)                          │
│                                                                 │
│  LEVEL 3: CONFIDENTIAL                                          │
│  • Description: Sensitive analytical results                    │
│  • Examples: Fire risk predictions, ML model outputs            │
│  • Protection: Encryption + data masking                        │
│  • Access: Data Scientists and Fire Chiefs only                 │
│  • Export: Approval workflow required                           │
│  • Watermarking: Forensic watermarking (hidden)                │
│  • Retention: 3 years, then auto-deletion                       │
│  • Volume: 12% of total data (360 GB)                          │
│                                                                 │
│  LEVEL 4: RESTRICTED                                            │
│  • Description: Highly sensitive infrastructure data            │
│  • Examples: Critical infrastructure locations, security logs   │
│  • Protection: Encryption + tokenization                        │
│  • Access: System Admins only, MFA required                     │
│  • Export: Prohibited (sandbox viewing only)                    │
│  • Watermarking: Forensic + visual watermarking                │
│  • Audit: All access logged with video recording                │
│  • Retention: 7 years (FISMA compliance)                        │
│  • Volume: 3% of total data (90 GB)                            │
│                                                                 │
│  ENCRYPTION STANDARDS:                                           │
│  • Algorithm: AES-256-GCM (Galois/Counter Mode)                │
│  • Key Length: 256 bits (meets NIST FIPS 140-2 Level 2)       │
│  • Key Rotation: Automatic every 90 days                        │
│  • Key Storage: HashiCorp Vault with unseal keys distributed   │
│  • Initialization Vector: Cryptographically random, unique/key  │
│  • Authentication Tag: 128 bits for integrity verification      │
│                                                                 │
│  DATA MASKING TECHNIQUES:                                        │
│  • Redaction: Replace sensitive values with [REDACTED]         │
│    - Personal names, contact info, addresses                    │
│  • Randomization: Replace with random but realistic values      │
│    - GPS coordinates shifted ±500m for privacy                  │
│  • Tokenization: Replace with irreversible tokens              │
│    - Infrastructure IDs replaced with UUIDs                     │
│  • Aggregation: Only summary statistics exposed                 │
│    - Individual sensor readings → hourly averages               │
│                                                                 │
│  DIGITAL WATERMARKING:                                           │
│  • Visible Watermarking (INTERNAL level):                       │
│    - User ID, timestamp, session ID on exported images/PDFs     │
│    - Example: "analyst@calfire.gov | 2025-10-23 14:35 PST"    │
│  • Forensic Watermarking (CONFIDENTIAL/RESTRICTED):            │
│    - Invisible steganographic embedding in data files           │
│    - LSB (Least Significant Bit) modification in imagery        │
│    - Spread-spectrum watermarking in numeric datasets           │
│    - Extraction tool identifies source of leaked data           │
│                                                                 │
│  DATA LOSS PREVENTION (DLP):                                     │
│  • Egress Monitoring:                                           │
│    - All outbound data transfers scanned                        │
│    - Pattern matching for sensitive data (regex, ML)            │
│    - Block transfers containing credit cards, SSNs (N/A here)   │
│  • Export Controls:                                             │
│    - Max 10,000 records/export for INTERNAL data               │
│    - Approval required for >10,000 records                      │
│    - All exports logged with justification field                │
│  • Anomaly Detection:                                           │
│    - Unusual export volumes (>10x user baseline)                │
│    - Off-hours data access (midnight-5am PST)                   │
│    - Multiple failed authorization attempts                     │
│    - Geographic anomalies (access from foreign IPs)             │
│  • Automated Responses:                                         │
│    - Block suspicious exports, alert security team              │
│    - Require secondary MFA for high-risk actions                │
│    - Trigger security incident workflow                         │
│                                                                 │
│  SECURE DATA DELETION:                                           │
│  • Standard Deletion: DoD 5220.22-M (3-pass overwrite)         │
│  • High-Security Deletion: NIST 800-88 purge (7-pass)          │
│  • Cloud Data: S3 bucket versioning disabled, objects deleted   │
│  • Database Records: Overwrite with random data before DELETE   │
│  • Verification: Post-deletion scan confirms unrecoverability   │
│                                                                 │
│  BACKUP SECURITY:                                                │
│  • Encryption: All backups encrypted with separate key          │
│  • Storage: Offline backups in physically secure facility       │
│  • Retention: Daily (30 days), weekly (90 days), monthly (7yr) │
│  • Testing: Quarterly restore tests verify integrity            │
│  • Access: Backup decryption requires 2-of-3 key custody        │
│                                                                 │
│  INCIDENT RESPONSE PROTOCOLS:                                    │
│  • Detection: SIEM alerts trigger automated workflows           │
│  • Containment: Revoke credentials, isolate affected systems    │
│  • Investigation: Forensic analysis of audit logs               │
│  • Remediation: Patch vulnerabilities, rotate keys              │
│  • Notification: Breach notification within 72 hours (GDPR)     │
│  • Post-Mortem: Document lessons learned, update policies       │
│                                                                 │
│  PERFORMANCE METRICS:                                            │
│  • Encryption overhead: <5% CPU, <2ms latency                   │
│  • Decryption throughput: 1.2 GB/s (hardware accelerated)       │
│  • DLP scan rate: 500 MB/s with 99.2% accuracy                 │
│  • Watermark extraction: 100% accuracy, <1s per file            │
│  • Key rotation time: <30 seconds, zero downtime                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🎤 **Speaker Script**

"Our Data Security Protocols implement defense-in-depth protection across four classification levels... ensuring wildfire intelligence data remains confidential... available... and trustworthy.

Data Classification uses four levels. Level One is PUBLIC... fifteen percent of total data volume at four hundred fifty gigabytes. This includes historical fire perimeters and county boundaries already in the public domain. No authentication required... unlimited export... no watermarking.

Level Two is INTERNAL... seventy percent of data at two point one terabytes. Real-time fire detections and weather data require authentication for all CAL FIRE users. AES-two fifty six encryption protects data at rest. Exports are rate-limited to one thousand records per hour. Digital watermarking embeds user I D and timestamp.

Level Three is CONFIDENTIAL... twelve percent of data at three hundred sixty gigabytes. Fire risk predictions and M L model outputs require Data Scientist or Fire Chief role. Encryption plus data masking provide double protection. Approval workflow required for export. Forensic watermarking provides hidden traceability. Three-year retention with automatic deletion.

Level Four is RESTRICTED... three percent of data at ninety gigabytes. Critical infrastructure locations and security logs accessible only to System Admins with MFA. Encryption plus tokenization prevent reconstruction. Export is prohibited... sandbox viewing only. Both forensic and visual watermarking applied. All access logged with video recording. Seven-year retention for FISMA compliance.

Encryption Standards use AES-two fifty six-GCM... Galois Counter Mode. Two hundred fifty six-bit keys meet NIST FIPS one forty-two dash two Level Two requirements. Automatic key rotation every ninety days. HashiCorp Vault stores keys with distributed unseal keys. Cryptographically random initialization vectors ensure uniqueness per key. One hundred twenty eight-bit authentication tags verify integrity.

Data Masking Techniques protect privacy. Redaction replaces personal names... contact info... and addresses with REDACTED tags. Randomization shifts GPS coordinates plus or minus five hundred meters for location privacy. Tokenization replaces infrastructure I Ds with irreversible U U I Ds. Aggregation exposes only summary statistics... for example converting individual sensor readings to hourly averages.

Digital Watermarking has two modes. Visible watermarking for INTERNAL level embeds user I D... timestamp... and session I D on exported images and P D Fs. For example... 'analyst at calfire.gov, October twenty three, two thousand twenty five, fourteen thirty five Pacific Standard Time.'

Forensic watermarking for CONFIDENTIAL and RESTRICTED uses invisible steganographic embedding. Least Significant Bit modification in imagery. Spread-spectrum watermarking in numeric datasets. Extraction tool identifies source of leaked data with one hundred percent accuracy in under one second per file.

Data Loss Prevention monitors egress. All outbound transfers scanned. Pattern matching uses regex and machine learning. Export controls limit INTERNAL data to ten thousand records per export. Approval required for larger exports. All exports logged with mandatory justification field.

Anomaly Detection catches unusual patterns. Export volumes exceeding ten times user baseline. Off-hours data access between midnight and five A M Pacific. Multiple failed authorization attempts. Geographic anomalies like access from foreign I P addresses. Automated responses block suspicious exports... alert security team... require secondary MFA for high-risk actions... and trigger security incident workflow.

Secure Data Deletion follows DoD five two two zero point two two-M standard with three-pass overwrite. High-security deletion uses NIST eight hundred eighty eight purge with seven passes. Cloud data deletion disables S3 bucket versioning. Database records overwritten with random data before DELETE. Post-deletion scan confirms unrecoverability.

Backup Security encrypts all backups with separate keys. Offline backups stored in physically secure facility. Daily backups retained thirty days... weekly ninety days... monthly seven years. Quarterly restore tests verify integrity. Backup decryption requires two-of-three key custody for security.

Incident Response Protocols handle breaches. Detection via SIEM alerts triggers automated workflows. Containment revokes credentials and isolates affected systems. Investigation performs forensic analysis of audit logs. Remediation patches vulnerabilities and rotates keys. Breach notification within seventy two hours per G D P R. Post-mortem documents lessons learned and updates policies.

Performance Metrics demonstrate efficiency. Encryption overhead under five percent CPU and under two milliseconds latency. Decryption throughput one point two gigabytes per second with hardware acceleration. DLP scan rate five hundred megabytes per second with ninety nine point two percent accuracy. Key rotation completes in under thirty seconds with zero downtime.

This isn't just data protection... it's comprehensive security ensuring California's wildfire intelligence assets remain safe from compromise."

---
"""


def generate_slide_26():
    """Slide 26: Secure Sandbox Environments"""
    return """
## Slide 26: Secure Sandbox Environments

### **Air-Gapped Analysis for Sensitive Data Exploration**

```mermaid
graph TB
    subgraph "Sandbox Architecture"
        subgraph "Request & Approval"
            USER[Data Scientist]
            REQUEST[Sandbox Request Form]
            APPROVAL{Approval<br/>Required?}
            FIRE_CHIEF[Fire Chief Approval]
            PROVISION[Sandbox Provisioning]
        end

        subgraph "Isolated Sandbox Environment"
            CONTAINER[Kubernetes Pod<br/>Isolated Container]
            NO_INTERNET[No Internet Egress<br/>Air-gapped]
            DATA_MOUNT[Read-Only Data Mount<br/>Sensitive Datasets]
            JUPYTER[Jupyter Notebook<br/>Python/R Environment]
            TOOLS[Analysis Tools<br/>Pandas, scikit-learn, etc.]
        end

        subgraph "Monitoring & Recording"
            SESSION_REC[Session Recording<br/>Video + Keystrokes]
            ACTIVITY_LOG[Activity Logging<br/>All Commands]
            FILE_AUDIT[File Access Audit<br/>What was viewed]
            EXPORT_TRACK[Export Attempts<br/>Blocked & Logged]
        end

        subgraph "Data Export Controls"
            EXPORT_REQ[Export Request]
            REVIEW{Manual Review}
            WATERMARK_APPLY[Apply Watermark]
            ENCRYPTION[Encrypt Export]
            DELIVER[Secure Delivery]
        end

        subgraph "Termination"
            TIMEOUT[8-Hour Timeout]
            MANUAL_TERM[Manual Termination]
            CLEANUP[Data Wipe & Destroy]
            AUDIT_REPORT[Generate Audit Report]
        end
    end

    USER --> REQUEST
    REQUEST --> APPROVAL

    APPROVAL -->|RESTRICTED| FIRE_CHIEF
    APPROVAL -->|CONFIDENTIAL| PROVISION
    FIRE_CHIEF -->|Approved| PROVISION
    FIRE_CHIEF -->|Denied| AUDIT_REPORT

    PROVISION --> CONTAINER
    CONTAINER --> NO_INTERNET
    CONTAINER --> DATA_MOUNT
    CONTAINER --> JUPYTER
    JUPYTER --> TOOLS

    CONTAINER --> SESSION_REC
    CONTAINER --> ACTIVITY_LOG
    DATA_MOUNT --> FILE_AUDIT
    TOOLS --> EXPORT_TRACK

    TOOLS --> EXPORT_REQ
    EXPORT_REQ --> REVIEW
    REVIEW -->|Approved| WATERMARK_APPLY
    REVIEW -->|Denied| AUDIT_REPORT
    WATERMARK_APPLY --> ENCRYPTION
    ENCRYPTION --> DELIVER

    TIMEOUT --> CLEANUP
    MANUAL_TERM --> CLEANUP
    CLEANUP --> AUDIT_REPORT

    style CONTAINER fill:#4ecdc4
    style NO_INTERNET fill:#f38181
    style SESSION_REC fill:#ffe66d
    style EXPORT_TRACK fill:#ff6b6b
    style CLEANUP fill:#aa96da
```

**SECURE SANDBOX SPECIFICATIONS:**
```
┌─────────────────────────────────────────────────────────────────┐
│              SECURE SANDBOX ENVIRONMENT FRAMEWORK               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SANDBOX PURPOSE:                                               │
│  Enable data scientists to explore sensitive wildfire datasets  │
│  (CONFIDENTIAL/RESTRICTED classification) in isolated           │
│  environment with comprehensive audit trail and zero risk of    │
│  data exfiltration. Air-gapped from internet for maximum       │
│  security while providing full analytical capabilities.         │
│                                                                 │
│  ARCHITECTURE OVERVIEW:                                         │
│  • Platform: Kubernetes on-premises cluster (not cloud)         │
│  • Isolation: Network policies prevent pod-to-pod communication │
│  • Compute: 16 vCPUs, 64 GB RAM per sandbox (dedicated)        │
│  • Storage: 500 GB ephemeral, wiped on termination             │
│  • Operating System: Ubuntu 22.04 LTS (hardened)               │
│  • Container Runtime: containerd with gVisor for added security │
│                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  │ REQUEST & APPROVAL WORKFLOW                                 │  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                 │
│  STEP 1: REQUEST SUBMISSION                                     │
│  • User: Data Scientist role required (MFA enforced)            │
│  • Form Fields:                                                 │
│    - Purpose: Research question or analysis goal                │
│    - Datasets: List specific datasets needed                    │
│    - Duration: Requested session length (max 8 hours)           │
│    - Tools: Software packages required beyond defaults          │
│    - Approval: Fire Chief approval for RESTRICTED data          │
│                                                                 │
│  STEP 2: AUTOMATED SECURITY CHECKS                              │
│  • User background check: Active MFA, no security violations    │
│  • Data classification: Determine highest sensitivity level     │
│  • Risk assessment: ML model scores request (0-100 scale)       │
│    - Score 0-49: Auto-approved                                  │
│    - Score 50-79: Fire Chief approval required                  │
│    - Score 80-100: Denied (e.g., foreign national + RESTRICTED) │
│                                                                 │
│  STEP 3: PROVISIONING (2-3 minutes)                             │
│  • Kubernetes namespace created with unique ID                  │
│  • Pod scheduled with resource limits                           │
│  • Data volumes mounted read-only from NFS                      │
│  • JupyterLab server started with authentication                │
│  • Session recording initialized                                │
│  • User receives sandbox URL: https://sandbox-{ID}.calfire.gov  │
│                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  │ NETWORK ISOLATION (AIR-GAPPED)                              │  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                 │
│  NO INTERNET EGRESS:                                            │
│  • Kubernetes Network Policy blocks all external traffic        │
│  • iptables rules drop packets to internet (0.0.0.0/0)         │
│  • DNS resolution disabled (prevent C2 beaconing)               │
│  • No outbound connections allowed (even to CAL FIRE network)   │
│                                                                 │
│  ALLOWED CONNECTIONS (Whitelist):                               │
│  • Inbound: HTTPS from user's authenticated session only        │
│  • NFS mount: Read-only access to data lake on-premises         │
│  • Logging: Unidirectional log forwarding to SIEM (UDP)         │
│  • Time sync: NTP to internal time server (no external pool)    │
│                                                                 │
│  BLOCKED OPERATIONS:                                            │
│  • pip install (package installation from PyPI)                 │
│  • git clone (code download from GitHub)                        │
│  • wget/curl (HTTP downloads)                                   │
│  • SSH outbound (remote server connections)                     │
│  • Email clients (SMTP blocked)                                 │
│                                                                 │
│  SECURITY MONITORING:                                           │
│  • Suricata IDS monitors all pod network traffic                │
│  • Alert on connection attempts to external IPs                 │
│  • Honeypot processes detect malicious tools (e.g., netcat)     │
│  • Container breakout attempts logged and terminated            │
│                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  │ DATA ACCESS & ANALYSIS TOOLS                                │  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                 │
│  DATA MOUNTING:                                                 │
│  • Mount Type: NFS v4 with Kerberos authentication              │
│  • Permissions: Read-only (rm, write, chmod all fail)           │
│  • Path: /mnt/data/{dataset_name}/                              │
│  • Formats: Parquet, CSV, GeoJSON, NetCDF, HDF5                │
│  • Size Limit: 500 GB total (prevent resource exhaustion)       │
│                                                                 │
│  ANALYSIS ENVIRONMENT:                                          │
│  • JupyterLab: Latest version with extensions disabled          │
│  • Python 3.11: NumPy, Pandas, scikit-learn, Matplotlib        │
│  • R 4.3: tidyverse, ggplot2, sf (spatial), xgboost            │
│  • Geospatial: GDAL, QGIS (headless), GeoPandas, Rasterio      │
│  • Machine Learning: TensorFlow, PyTorch, XGBoost (CPU only)    │
│  • Database: DuckDB for fast Parquet queries (10x faster SQL)   │
│                                                                 │
│  RESTRICTIONS:                                                  │
│  • No GPU access (prevent cryptomining abuse)                   │
│  • No root/sudo (privilege escalation blocked)                  │
│  • No Docker-in-Docker (container escape prevention)            │
│  • Code execution limited to /home/user/ directory              │
│  • Core dumps disabled (memory forensics prevention)            │
│                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  │ COMPREHENSIVE MONITORING & RECORDING                        │  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                 │
│  SESSION RECORDING (Video):                                     │
│  • Technology: ttyrec for terminal, browser recording via proxy │
│  • Resolution: 1920x1080, 30 fps                                │
│  • Format: H.264 video, 5 Mbps bitrate                         │
│  • Storage: Encrypted S3 bucket, 7-year retention               │
│  • Playback: Admin console allows incident investigation        │
│                                                                 │
│  ACTIVITY LOGGING (Commands):                                   │
│  • Capture: All bash commands via auditd                        │
│  • Python/R: Jupyter cell execution logged with code           │
│  • File Access: inotify tracks open(), read(), stat() syscalls │
│  • Timestamps: Microsecond precision with NTP sync              │
│  • Correlation ID: Unique session ID links all events           │
│                                                                 │
│  FILE ACCESS AUDIT:                                             │
│  • What datasets were opened                                    │
│  • How many records read from each file                         │
│  • Which columns/fields accessed                                │
│  • Statistical queries performed (e.g., mean, max, corr)        │
│  • Visualization created (charts saved as images)               │
│                                                                 │
│  EXPORT ATTEMPT TRACKING:                                       │
│  • All file writes outside /mnt/data/ logged                    │
│  • Clipboard operations (copy/paste) monitored                  │
│  • Screenshot attempts blocked (X11 security extensions)        │
│  • Print operations disabled                                    │
│  • Alert on unusual patterns (bulk file I/O, encoding)          │
│                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  │ DATA EXPORT CONTROLS                                        │  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                 │
│  EXPORT WORKFLOW:                                               │
│  1. User writes results to /home/user/exports/ directory        │
│  2. Click "Request Export" button in JupyterLab                 │
│  3. System scans files for sensitive data (PII, coordinates)    │
│  4. Manual review by Fire Chief (RESTRICTED) or auto (CONFID)  │
│  5. Apply forensic watermark (user ID + session ID embedded)    │
│  6. Encrypt with user's public key (PGP/GPG)                    │
│  7. Deliver via secure download link (24-hour expiry)           │
│                                                                 │
│  EXPORT LIMITS:                                                 │
│  • Max file size: 100 MB per export                             │
│  • Max exports: 5 per session                                   │
│  • Approval time: 1-4 hours for RESTRICTED data                │
│  • Denied exports: User receives explanation                    │
│                                                                 │
│  EXPORT SECURITY:                                               │
│  • Watermarking: LSB steganography in images/Parquet            │
│  • Encryption: AES-256-GCM with user's public key               │
│  • Download link: Pre-signed URL with IP whitelisting           │
│  • Tracking: All exports logged in audit_log table              │
│  • Forensics: Extracted watermark identifies source of leak     │
│                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  │ SESSION TERMINATION & CLEANUP                               │  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                 │
│  TERMINATION TRIGGERS:                                          │
│  • 8-hour timeout (absolute max, no extensions)                 │
│  • User clicks "End Session" button                             │
│  • Security incident detected (unauthorized actions)            │
│  • System maintenance (30-minute warning given)                 │
│  • User revokes MFA or role changed                             │
│                                                                 │
│  DATA WIPE PROCESS:                                             │
│  • Unmount NFS volumes (no data persists)                       │
│  • Overwrite ephemeral storage with zeros (DoD 5220.22-M)      │
│  • Delete Kubernetes pod and namespace                          │
│  • Terminate network connections                                │
│  • Archive session recording and logs                           │
│  • Verification: Scan for residual data (must be 0 bytes)       │
│                                                                 │
│  AUDIT REPORT GENERATION:                                       │
│  • Session summary: Duration, datasets accessed, exports        │
│  • Activity timeline: Key events with timestamps                │
│  • Security events: Anomalies or policy violations              │
│  • Export manifest: What data left the sandbox                  │
│  • Approver sign-off: Fire Chief confirms review                │
│  • Retention: 7 years in compliance database                    │
│                                                                 │
│  USAGE STATISTICS (Since Jan 2025):                             │
│  • Total sessions: 187                                          │
│  • Avg session duration: 4.2 hours                              │
│  • Total datasets accessed: 42 unique datasets                  │
│  • Export approval rate: 94% (11 denied due to PII exposure)    │
│  • Security incidents: 0 (zero data exfiltration events)        │
│  • User satisfaction: 4.8/5.0 (survey of 28 data scientists)    │
│                                                                 │
│  COST PER SESSION:                                              │
│  • Compute: $3.20/hour × 4.2 hours avg = $13.44                │
│  • Storage: $0.50 (ephemeral disk, wiped)                      │
│  • Recording: $1.20 (video storage for 7 years)                │
│  • Total: $15.14 per session                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🎤 **Speaker Script**

"Our Secure Sandbox Environments enable data scientists to explore California's most sensitive wildfire datasets... CONFIDENTIAL and RESTRICTED classification levels... with zero risk of data exfiltration and comprehensive audit trail.

The Sandbox Purpose is to balance security with analytical capability. Scientists need to explore sensitive datasets including critical infrastructure locations... proprietary M L model outputs... and security logs. Air-gapped isolation prevents internet access. Comprehensive monitoring records every action. Full analytical tools enable Python... R... machine learning... and geospatial analysis.

Architecture Overview runs on-premises Kubernetes cluster... not cloud for maximum control. Kubernetes Network Policies isolate pods preventing communication. Each sandbox receives dedicated sixteen virtual CPUs and sixty four gigabytes RAM. Five hundred gigabytes ephemeral storage wiped on termination. Ubuntu twenty two point oh four LTS hardened operating system. And containerd with gVisor adds container escape protection.

Request and Approval Workflow has three steps. Step One... Data Scientist submits request form specifying research question... datasets needed... session duration up to eight hours maximum... required software packages... and Fire Chief approval for RESTRICTED data.

Step Two runs Automated Security Checks. User background check verifies active MFA and no security violations. Data classification determines highest sensitivity level. Machine learning risk assessment scores request zero to one hundred. Score zero to forty nine is auto-approved. Fifty to seventy nine requires Fire Chief approval. Eighty to one hundred is denied... for example foreign national requesting RESTRICTED data.

Step Three provisions sandbox in two to three minutes. Kubernetes namespace created with unique I D. Pod scheduled with resource limits. Data volumes mounted read-only from NFS. JupyterLab server started with authentication. Session recording initialized. User receives secure U R L... H T T P S colon slash slash sandbox dash session I D dot calfire dot gov.

Network Isolation implements air-gapping. No Internet Egress via Kubernetes Network Policy blocks all external traffic. iptables rules drop packets to zero dot zero dot zero dot zero slash zero. DNS resolution disabled prevents C two command-and-control beaconing. No outbound connections allowed... even to CAL FIRE network.

Allowed Connections use whitelist approach. Inbound HTTPS from user's authenticated session only. NFS mount provides read-only access to on-premises data lake. Logging uses unidirectional log forwarding to SIEM via UDP. Time sync to internal NTP server... no external pool.

Blocked Operations include pip install... package installation from PyPI. Git clone... code download from GitHub. wget and curl for HTTP downloads. SSH outbound to remote servers. And email clients... SMTP is blocked.

Security Monitoring uses Suricata IDS monitoring all pod network traffic. Alert on connection attempts to external I P addresses. Honeypot processes detect malicious tools like netcat. Container breakout attempts logged and immediately terminated.

Data Access uses NFS v4 with Kerberos authentication. Read-only permissions mean rm... write... and chmod all fail. Data path is slash m n t slash data slash dataset name. Supported formats include Parquet... CSV... GeoJSON... NetCDF... and HDF five. Five hundred gigabyte limit prevents resource exhaustion.

Analysis Environment provides JupyterLab latest version with extensions disabled. Python three point eleven includes NumPy... Pandas... scikit-learn... and Matplotlib. R four point three includes tidyverse... ggplot two... sf for spatial... and xgboost. Geospatial tools include GDAL... QGIS headless... GeoPandas... and Rasterio. Machine learning supports TensorFlow... PyTorch... and XGBoost CPU only. DuckDB provides fast Parquet queries... ten times faster than standard S Q L.

Restrictions enforce security. No GPU access prevents cryptomining abuse. No root or sudo blocks privilege escalation. No Docker-in-Docker prevents container escape. Code execution limited to slash home slash user directory. Core dumps disabled prevent memory forensics.

Comprehensive Monitoring captures everything. Session Recording uses ttyrec for terminal and browser recording via proxy. Nineteen twenty by ten eighty resolution at thirty frames per second. H point two six four video at five megabits per second bitrate. Encrypted S3 bucket storage with seven-year retention.

Activity Logging captures all bash commands via auditd. Python and R cell execution logged with code. File Access via inotify tracks open... read... and stat system calls. Microsecond precision timestamps with NTP sync. Unique session I D correlation links all events.

File Access Audit tracks what datasets were opened. How many records read from each file. Which columns or fields accessed. Statistical queries performed like mean... max... or correlation. And visualizations created as saved images.

Export Attempt Tracking logs all file writes outside data mount. Clipboard operations monitored. Screenshot attempts blocked via X eleven security extensions. Print operations disabled. Alert on unusual patterns like bulk file I slash O or encoding.

Data Export Controls use seven-step workflow. User writes results to exports directory. Click 'Request Export' button in JupyterLab. System scans files for sensitive data like P I I or coordinates. Manual review by Fire Chief for RESTRICTED or automatic for CONFIDENTIAL. Apply forensic watermark embedding user I D and session I D. Encrypt with user's public key using PGP or GPG. Deliver via secure download link with twenty four-hour expiry.

Export Limits constrain exfiltration. Maximum file size one hundred megabytes per export. Maximum five exports per session. Approval time one to four hours for RESTRICTED data. Denied exports receive explanation.

Session Termination triggers include eight-hour absolute timeout with no extensions. User clicks 'End Session' button. Security incident detected with unauthorized actions. System maintenance with thirty-minute warning. Or user revokes MFA or role changed.

Data Wipe Process is thorough. Unmount NFS volumes... no data persists. Overwrite ephemeral storage with zeros per DoD five two two zero point two two-M. Delete Kubernetes pod and namespace. Terminate network connections. Archive session recording and logs. Verification scan confirms zero bytes residual data.

Audit Report documents everything. Session summary includes duration... datasets accessed... and exports. Activity timeline shows key events with timestamps. Security events note anomalies or violations. Export manifest details what data left sandbox. Fire Chief sign-off confirms review. Seven-year retention in compliance database.

Usage Statistics since January two thousand twenty five show one hundred eighty seven total sessions. Average session duration four point two hours. Forty two unique datasets accessed. Ninety four percent export approval rate with eleven denied due to P I I exposure risk. Zero security incidents... zero data exfiltration events. User satisfaction four point eight out of five from survey of twenty eight data scientists.

Cost Per Session is fifteen dollars fourteen cents. Compute three dollars twenty cents per hour times four point two hours average equals thirteen dollars forty four cents. Storage fifty cents for ephemeral disk. Recording one dollar twenty cents for seven-year video storage.

This isn't just a sandbox... it's a secure research environment enabling scientific discovery while guaranteeing California's most sensitive wildfire intelligence remains protected."

---
"""


def main():
    """Generate and append slides 24 and 26"""
    print("Generating missing Security slides 24 and 26...")

    content = generate_slide_24() + generate_slide_26()

    # Write to a separate file that can be manually inserted
    output_path = r"C:\dev\wildfire\docs\CHALLENGE3_SECURITY_SLIDES_24_26.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n✅ Generated slides 24 and 26!")
    print(f"📄 File: {output_path}")
    print(f"\n📊 Slides created:")
    print("   • Slide 24: Data Security Protocols")
    print("   • Slide 26: Secure Sandbox Environments")
    print(f"\n💡 These slides should be inserted into the main presentation file.")


if __name__ == "__main__":
    main()
