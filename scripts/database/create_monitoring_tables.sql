-- Create Monitoring Tables for Challenge 2 Storage Dashboard
-- These tables track real-time metrics for SLA compliance

-- ============================================================================
-- 1. QUERY PERFORMANCE LOG - Track query latency by storage tier
-- ============================================================================
CREATE TABLE IF NOT EXISTS query_performance_log (
    id SERIAL PRIMARY KEY,
    storage_tier VARCHAR(20) NOT NULL CHECK (storage_tier IN ('HOT', 'WARM', 'COLD', 'ARCHIVE')),
    query_type VARCHAR(50) NOT NULL,  -- SELECT, INSERT, UPDATE, DELETE, MIGRATION
    duration_ms NUMERIC(10, 2) NOT NULL,  -- Query execution time in milliseconds
    rows_affected INTEGER DEFAULT 0,
    query_text TEXT,
    executed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    user_id VARCHAR(100),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_query_perf_tier_time ON query_performance_log(storage_tier, executed_at DESC);
CREATE INDEX idx_query_perf_executed ON query_performance_log(executed_at DESC);

-- ============================================================================
-- 2. BACKUP LOG - Track Veeam backup jobs
-- ============================================================================
CREATE TABLE IF NOT EXISTS backup_log (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(200) NOT NULL,  -- e.g., 'PostgreSQL_HOT_Backup', 'MinIO_WARM_Backup'
    job_type VARCHAR(50) NOT NULL,  -- FULL, INCREMENTAL, DIFFERENTIAL
    storage_tier VARCHAR(20) CHECK (storage_tier IN ('HOT', 'WARM', 'COLD', 'ARCHIVE', 'ALL')),
    backup_size_bytes BIGINT,
    compressed_size_bytes BIGINT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    status VARCHAR(20) NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'RUNNING', 'CANCELLED', 'WARNING')),
    success_rate NUMERIC(5, 2),  -- Percentage of files successfully backed up
    files_total INTEGER,
    files_backed_up INTEGER,
    files_failed INTEGER,
    error_message TEXT,
    backup_location VARCHAR(500),  -- S3 path, MinIO path, or local path
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_backup_log_status_time ON backup_log(status, completed_at DESC);
CREATE INDEX idx_backup_log_tier ON backup_log(storage_tier, completed_at DESC);

-- ============================================================================
-- 3. AUDIT LOG - Track security events (auth, API, compliance)
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,  -- AUTH_FAILURE, AUTH_SUCCESS, API_CALL, API_VIOLATION, COMPLIANCE_CHECK, DATA_ACCESS
    event_category VARCHAR(30) NOT NULL CHECK (event_category IN ('AUTHENTICATION', 'AUTHORIZATION', 'API', 'COMPLIANCE', 'DATA_ACCESS', 'CONFIGURATION')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    user_id VARCHAR(100),
    username VARCHAR(100),
    source_ip VARCHAR(45),  -- IPv4 or IPv6
    resource_accessed VARCHAR(500),  -- Table, API endpoint, file path
    action_performed VARCHAR(100),  -- LOGIN, QUERY, UPDATE, DELETE, EXPORT, etc.
    result VARCHAR(20) CHECK (result IN ('SUCCESS', 'FAILURE', 'BLOCKED', 'WARNING')),
    error_code VARCHAR(50),
    error_message TEXT,
    metadata JSONB,  -- Additional context (e.g., API rate limit details, compliance rule violated)
    event_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_log_event_type ON audit_log(event_type, event_timestamp DESC);
CREATE INDEX idx_audit_log_category ON audit_log(event_category, event_timestamp DESC);
CREATE INDEX idx_audit_log_user ON audit_log(user_id, event_timestamp DESC);
CREATE INDEX idx_audit_log_severity ON audit_log(severity, event_timestamp DESC);

-- ============================================================================
-- 4. KMS KEY ROTATION LOG - Track encryption key rotations
-- ============================================================================
CREATE TABLE IF NOT EXISTS kms_key_rotation_log (
    id SERIAL PRIMARY KEY,
    key_id VARCHAR(200) NOT NULL,  -- AWS KMS Key ID or local key identifier
    key_alias VARCHAR(200),  -- Human-readable key alias
    key_type VARCHAR(50) NOT NULL,  -- AES-256, RSA-2048, etc.
    storage_tier VARCHAR(20) CHECK (storage_tier IN ('HOT', 'WARM', 'COLD', 'ARCHIVE', 'ALL')),
    rotation_type VARCHAR(50) NOT NULL CHECK (rotation_type IN ('AUTOMATIC', 'MANUAL', 'EMERGENCY', 'COMPLIANCE')),
    old_key_version INTEGER,
    new_key_version INTEGER NOT NULL,
    rotated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    rotated_by VARCHAR(100),  -- User or system that triggered rotation
    reason TEXT,  -- e.g., 'Scheduled 90-day rotation', 'Suspected key compromise'
    re_encryption_required BOOLEAN DEFAULT FALSE,
    re_encryption_progress NUMERIC(5, 2) DEFAULT 0.0,  -- Percentage of data re-encrypted
    status VARCHAR(20) NOT NULL CHECK (status IN ('COMPLETED', 'IN_PROGRESS', 'FAILED', 'ROLLED_BACK')),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_kms_rotation_key ON kms_key_rotation_log(key_id, rotated_at DESC);
CREATE INDEX idx_kms_rotation_tier ON kms_key_rotation_log(storage_tier, rotated_at DESC);

-- ============================================================================
-- 5. REPLICATION LAG TRACKING - Track PostgreSQL replication lag
-- ============================================================================
CREATE TABLE IF NOT EXISTS replication_lag_log (
    id SERIAL PRIMARY KEY,
    primary_host VARCHAR(255) NOT NULL,
    replica_host VARCHAR(255) NOT NULL,
    replication_lag_seconds NUMERIC(10, 2) NOT NULL,
    replication_lag_bytes BIGINT,
    replay_lag_seconds NUMERIC(10, 2),
    write_lag_seconds NUMERIC(10, 2),
    flush_lag_seconds NUMERIC(10, 2),
    sync_state VARCHAR(20),  -- async, potential, sync, quorum
    sync_priority INTEGER,
    replica_status VARCHAR(20) CHECK (replica_status IN ('STREAMING', 'CATCHUP', 'STOPPED', 'FAILED')),
    measured_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_replication_lag_time ON replication_lag_log(measured_at DESC);
CREATE INDEX idx_replication_lag_replica ON replication_lag_log(replica_host, measured_at DESC);

-- ============================================================================
-- 6. COST TRACKING - Track actual monthly spend
-- ============================================================================
CREATE TABLE IF NOT EXISTS cost_tracking (
    id SERIAL PRIMARY KEY,
    cost_period DATE NOT NULL,  -- First day of month
    storage_tier VARCHAR(20) NOT NULL CHECK (storage_tier IN ('HOT', 'WARM', 'COLD', 'ARCHIVE')),
    storage_gb NUMERIC(15, 2) NOT NULL,
    cost_usd NUMERIC(10, 4) NOT NULL,
    budget_usd NUMERIC(10, 4),
    variance_percent NUMERIC(6, 2),  -- (actual - budget) / budget * 100
    cost_type VARCHAR(50) NOT NULL CHECK (cost_type IN ('STORAGE', 'DATA_TRANSFER', 'API_REQUESTS', 'KMS', 'REPLICATION', 'BACKUP')),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(cost_period, storage_tier, cost_type)
);

CREATE INDEX idx_cost_tracking_period ON cost_tracking(cost_period DESC, storage_tier);

-- ============================================================================
-- Create Views for Easy Dashboard Queries
-- ============================================================================

-- View: Latest query latency percentiles by tier
CREATE OR REPLACE VIEW v_query_latency_percentiles AS
SELECT
    storage_tier,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms) as p50_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99_ms,
    AVG(duration_ms) as avg_ms,
    COUNT(*) as query_count,
    MAX(executed_at) as last_measured
FROM query_performance_log
WHERE executed_at >= NOW() - INTERVAL '1 hour'
  AND success = TRUE
GROUP BY storage_tier;

-- View: Backup success rate (last 24 hours)
CREATE OR REPLACE VIEW v_backup_success_rate AS
SELECT
    COUNT(*) as total_backups,
    COUNT(*) FILTER (WHERE status = 'SUCCESS') as successful_backups,
    COUNT(*) FILTER (WHERE status = 'FAILED') as failed_backups,
    ROUND(COUNT(*) FILTER (WHERE status = 'SUCCESS')::numeric / NULLIF(COUNT(*), 0) * 100, 2) as success_rate_percent,
    SUM(backup_size_bytes) as total_backup_size
FROM backup_log
WHERE completed_at >= NOW() - INTERVAL '24 hours';

-- View: Security events summary (last hour)
CREATE OR REPLACE VIEW v_security_events_hourly AS
SELECT
    event_category,
    event_type,
    COUNT(*) as event_count,
    COUNT(*) FILTER (WHERE result = 'FAILURE') as failure_count,
    COUNT(*) FILTER (WHERE result = 'BLOCKED') as blocked_count
FROM audit_log
WHERE event_timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY event_category, event_type;

-- View: Latest KMS key rotation info
CREATE OR REPLACE VIEW v_kms_rotation_status AS
SELECT
    storage_tier,
    key_alias,
    rotated_at,
    EXTRACT(DAY FROM NOW() - rotated_at) as days_since_rotation,
    rotation_type,
    status
FROM kms_key_rotation_log
WHERE id IN (
    SELECT MAX(id)
    FROM kms_key_rotation_log
    WHERE status = 'COMPLETED'
    GROUP BY storage_tier
);

-- View: Latest replication lag
CREATE OR REPLACE VIEW v_replication_lag_current AS
SELECT
    replica_host,
    replication_lag_seconds,
    replay_lag_seconds,
    sync_state,
    replica_status,
    measured_at
FROM replication_lag_log
WHERE id IN (
    SELECT MAX(id)
    FROM replication_lag_log
    GROUP BY replica_host
);

-- View: Monthly cost summary
CREATE OR REPLACE VIEW v_monthly_cost_summary AS
SELECT
    cost_period,
    SUM(cost_usd) as total_cost_usd,
    SUM(budget_usd) as total_budget_usd,
    ROUND((SUM(cost_usd) - SUM(budget_usd)) / NULLIF(SUM(budget_usd), 0) * 100, 2) as variance_percent,
    SUM(storage_gb) as total_storage_gb
FROM cost_tracking
WHERE cost_period = DATE_TRUNC('month', NOW())
GROUP BY cost_period;

COMMENT ON TABLE query_performance_log IS 'Tracks query execution times for SLA latency monitoring';
COMMENT ON TABLE backup_log IS 'Tracks Veeam backup job status and success rates';
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for security and compliance';
COMMENT ON TABLE kms_key_rotation_log IS 'Tracks encryption key rotation for compliance';
COMMENT ON TABLE replication_lag_log IS 'Tracks PostgreSQL streaming replication lag';
COMMENT ON TABLE cost_tracking IS 'Tracks monthly storage costs and budget variance';
