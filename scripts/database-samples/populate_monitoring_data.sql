-- Populate Monitoring Tables with Realistic Sample Data
-- This creates a realistic monitoring dataset for the last 7 days

-- ============================================================================
-- 1. QUERY PERFORMANCE LOG - Generate realistic query latencies
-- ============================================================================

-- HOT tier queries (PostgreSQL) - Fast, < 100ms p95
INSERT INTO query_performance_log (storage_tier, query_type, duration_ms, rows_affected, executed_at, user_id, success)
SELECT
    'HOT' as storage_tier,
    (ARRAY['SELECT', 'INSERT', 'UPDATE', 'SELECT', 'SELECT'])[floor(random() * 5 + 1)] as query_type,
    -- Generate latencies: mostly 20-80ms, some spikes to 120ms
    CASE
        WHEN random() < 0.90 THEN 20 + random() * 60  -- 90% fast queries (20-80ms)
        WHEN random() < 0.95 THEN 80 + random() * 30  -- 5% slower (80-110ms)
        ELSE 110 + random() * 40  -- 5% outliers (110-150ms)
    END as duration_ms,
    floor(random() * 1000 + 1)::INTEGER as rows_affected,
    NOW() - (random() * INTERVAL '7 days') as executed_at,
    'user_' || floor(random() * 20 + 1) as user_id,
    random() > 0.02 as success  -- 98% success rate
FROM generate_series(1, 5000);

-- WARM tier queries (MinIO Parquet) - Slower, < 500ms p95
INSERT INTO query_performance_log (storage_tier, query_type, duration_ms, rows_affected, executed_at, user_id, success)
SELECT
    'WARM' as storage_tier,
    (ARRAY['SELECT', 'MIGRATION', 'SELECT'])[floor(random() * 3 + 1)] as query_type,
    CASE
        WHEN random() < 0.85 THEN 150 + random() * 200  -- 85% fast (150-350ms)
        WHEN random() < 0.95 THEN 350 + random() * 150  -- 10% slower (350-500ms)
        ELSE 500 + random() * 300  -- 5% outliers (500-800ms)
    END as duration_ms,
    floor(random() * 10000 + 100)::INTEGER as rows_affected,
    NOW() - (random() * INTERVAL '7 days') as executed_at,
    'user_' || floor(random() * 20 + 1) as user_id,
    random() > 0.03 as success  -- 97% success rate
FROM generate_series(1, 3000);

-- COLD tier queries (S3) - Much slower, < 5000ms p95
INSERT INTO query_performance_log (storage_tier, query_type, duration_ms, rows_affected, executed_at, user_id, success)
SELECT
    'COLD' as storage_tier,
    (ARRAY['SELECT', 'MIGRATION', 'SELECT'])[floor(random() * 3 + 1)] as query_type,
    CASE
        WHEN random() < 0.80 THEN 1000 + random() * 2000  -- 80% reasonable (1-3s)
        WHEN random() < 0.95 THEN 3000 + random() * 2000  -- 15% slower (3-5s)
        ELSE 5000 + random() * 3000  -- 5% outliers (5-8s)
    END as duration_ms,
    floor(random() * 50000 + 1000)::INTEGER as rows_affected,
    NOW() - (random() * INTERVAL '7 days') as executed_at,
    'user_' || floor(random() * 20 + 1) as user_id,
    random() > 0.05 as success  -- 95% success rate
FROM generate_series(1, 1000);

-- ARCHIVE tier queries (Glacier) - Very slow, 12-hour retrieval
INSERT INTO query_performance_log (storage_tier, query_type, duration_ms, rows_affected, executed_at, user_id, success)
SELECT
    'ARCHIVE' as storage_tier,
    'SELECT' as query_type,
    30000 + random() * 20000 as duration_ms,  -- 30-50 seconds (actual retrieval takes hours, this is just metadata query)
    floor(random() * 100000 + 10000)::INTEGER as rows_affected,
    NOW() - (random() * INTERVAL '7 days') as executed_at,
    'user_' || floor(random() * 20 + 1) as user_id,
    random() > 0.08 as success  -- 92% success rate
FROM generate_series(1, 200);

-- ============================================================================
-- 2. BACKUP LOG - Generate realistic backup jobs
-- ============================================================================

-- Daily PostgreSQL HOT tier backups (last 7 days)
INSERT INTO backup_log (job_name, job_type, storage_tier, backup_size_bytes, compressed_size_bytes, started_at, completed_at, duration_seconds, status, success_rate, files_total, files_backed_up, files_failed, backup_location)
SELECT
    'PostgreSQL_HOT_Daily_Backup' as job_name,
    'INCREMENTAL' as job_type,
    'HOT' as storage_tier,
    174000000 + (random() * 50000000)::BIGINT as backup_size_bytes,
    52000000 + (random() * 15000000)::BIGINT as compressed_size_bytes,  -- ~70% compression
    (NOW() - (generate_series * INTERVAL '1 day')) + INTERVAL '2 hours' as started_at,
    (NOW() - (generate_series * INTERVAL '1 day')) + INTERVAL '2 hours 15 minutes' as completed_at,
    900 + floor(random() * 300)::INTEGER as duration_seconds,
    CASE WHEN random() > 0.02 THEN 'SUCCESS' ELSE 'WARNING' END as status,
    95.0 + random() * 5.0 as success_rate,
    5 as files_total,
    CASE WHEN random() > 0.02 THEN 5 ELSE 4 END as files_backed_up,
    CASE WHEN random() > 0.02 THEN 0 ELSE 1 END as files_failed,
    's3://wildfire-backup-east/postgresql/' || (NOW() - (generate_series * INTERVAL '1 day'))::DATE as backup_location
FROM generate_series(0, 6);

-- Weekly MinIO WARM tier backups
INSERT INTO backup_log (job_name, job_type, storage_tier, backup_size_bytes, compressed_size_bytes, started_at, completed_at, duration_seconds, status, success_rate, files_total, files_backed_up, files_failed, backup_location)
SELECT
    'MinIO_WARM_Weekly_Backup' as job_name,
    'FULL' as job_type,
    'WARM' as storage_tier,
    2100000000 + (random() * 300000000)::BIGINT as backup_size_bytes,
    1680000000 + (random() * 240000000)::BIGINT as compressed_size_bytes,  -- ~80% compression for Parquet
    (NOW() - (generate_series * INTERVAL '7 days')) + INTERVAL '3 hours' as started_at,
    (NOW() - (generate_series * INTERVAL '7 days')) + INTERVAL '5 hours 30 minutes' as completed_at,
    9000 + floor(random() * 1800)::INTEGER as duration_seconds,
    'SUCCESS' as status,
    99.0 + random() * 1.0 as success_rate,
    11 as files_total,
    11 as files_backed_up,
    0 as files_failed,
    's3://wildfire-backup-east/minio/' || (NOW() - (generate_series * INTERVAL '7 days'))::DATE as backup_location
FROM generate_series(0, 1);

-- Daily S3 COLD tier replication checks
INSERT INTO backup_log (job_name, job_type, storage_tier, backup_size_bytes, compressed_size_bytes, started_at, completed_at, duration_seconds, status, success_rate, files_total, files_backed_up, files_failed, backup_location)
SELECT
    'S3_COLD_Replication_Check' as job_name,
    'INCREMENTAL' as job_type,
    'COLD' as storage_tier,
    2200000000 + (random() * 200000000)::BIGINT as backup_size_bytes,
    2200000000 + (random() * 200000000)::BIGINT as compressed_size_bytes,  -- Already compressed
    (NOW() - (generate_series * INTERVAL '1 day')) + INTERVAL '4 hours' as started_at,
    (NOW() - (generate_series * INTERVAL '1 day')) + INTERVAL '4 hours 45 minutes' as completed_at,
    2700 + floor(random() * 600)::INTEGER as duration_seconds,
    'SUCCESS' as status,
    100.0 as success_rate,
    6 as files_total,
    6 as files_backed_up,
    0 as files_failed,
    's3://wildfire-backup-west/cold-replica/' || (NOW() - (generate_series * INTERVAL '1 day'))::DATE as backup_location
FROM generate_series(0, 6);

-- ============================================================================
-- 3. AUDIT LOG - Generate security events
-- ============================================================================

-- Successful authentication events (thousands per day)
INSERT INTO audit_log (event_type, event_category, severity, user_id, username, source_ip, resource_accessed, action_performed, result, event_timestamp)
SELECT
    'AUTH_SUCCESS' as event_type,
    'AUTHENTICATION' as event_category,
    'INFO' as severity,
    'user_' || floor(random() * 50 + 1) as user_id,
    'analyst_' || floor(random() * 50 + 1) as username,
    '10.0.' || floor(random() * 255) || '.' || floor(random() * 255) as source_ip,
    '/api/auth/login' as resource_accessed,
    'LOGIN' as action_performed,
    'SUCCESS' as result,
    NOW() - (random() * INTERVAL '7 days') as event_timestamp
FROM generate_series(1, 3000);

-- Failed authentication attempts (smaller number, expected)
INSERT INTO audit_log (event_type, event_category, severity, user_id, username, source_ip, resource_accessed, action_performed, result, error_code, error_message, event_timestamp)
SELECT
    'AUTH_FAILURE' as event_type,
    'AUTHENTICATION' as event_category,
    CASE WHEN random() < 0.8 THEN 'WARNING' ELSE 'ERROR' END as severity,
    'user_' || floor(random() * 100 + 1) as user_id,
    'user_' || floor(random() * 100 + 1) as username,
    '10.0.' || floor(random() * 255) || '.' || floor(random() * 255) as source_ip,
    '/api/auth/login' as resource_accessed,
    'LOGIN' as action_performed,
    'FAILURE' as result,
    'AUTH_' || (ARRAY['INVALID_PASSWORD', 'INVALID_USERNAME', 'ACCOUNT_LOCKED', 'MFA_FAILED'])[floor(random() * 4 + 1)] as error_code,
    'Authentication failed' as error_message,
    NOW() - (random() * INTERVAL '7 days') as event_timestamp
FROM generate_series(1, 150);

-- API calls (successful)
INSERT INTO audit_log (event_type, event_category, severity, user_id, username, source_ip, resource_accessed, action_performed, result, event_timestamp)
SELECT
    'API_CALL' as event_type,
    'API' as event_category,
    'INFO' as severity,
    'user_' || floor(random() * 50 + 1) as user_id,
    'analyst_' || floor(random() * 50 + 1) as username,
    '10.0.' || floor(random() * 255) || '.' || floor(random() * 255) as source_ip,
    '/api/v1/data/' || (ARRAY['query', 'export', 'stats', 'catalog'])[floor(random() * 4 + 1)] as resource_accessed,
    (ARRAY['QUERY', 'EXPORT', 'READ', 'LIST'])[floor(random() * 4 + 1)] as action_performed,
    'SUCCESS' as result,
    NOW() - (random() * INTERVAL '7 days') as event_timestamp
FROM generate_series(1, 5000);

-- API rate limit violations (small number, within normal range)
INSERT INTO audit_log (event_type, event_category, severity, user_id, username, source_ip, resource_accessed, action_performed, result, error_code, error_message, metadata, event_timestamp)
SELECT
    'API_VIOLATION' as event_type,
    'API' as event_category,
    'WARNING' as severity,
    'user_' || floor(random() * 10 + 1) as user_id,
    'analyst_' || floor(random() * 10 + 1) as username,
    '10.0.' || floor(random() * 255) || '.' || floor(random() * 255) as source_ip,
    '/api/v1/data/export' as resource_accessed,
    'EXPORT' as action_performed,
    'BLOCKED' as result,
    'RATE_LIMIT_EXCEEDED' as error_code,
    'API rate limit exceeded: 1000 requests per hour' as error_message,
    jsonb_build_object('limit', 1000, 'window_seconds', 3600, 'requests_made', 1000 + floor(random() * 50)) as metadata,
    NOW() - (random() * INTERVAL '7 days') as event_timestamp
FROM generate_series(1, 25);

-- Compliance checks (all passing)
INSERT INTO audit_log (event_type, event_category, severity, user_id, resource_accessed, action_performed, result, metadata, event_timestamp)
SELECT
    'COMPLIANCE_CHECK' as event_type,
    'COMPLIANCE' as event_category,
    'INFO' as severity,
    'system' as user_id,
    'data_catalog' as resource_accessed,
    (ARRAY['ENCRYPTION_CHECK', 'RETENTION_CHECK', 'ACCESS_CONTROL_CHECK', 'AUDIT_LOG_CHECK'])[floor(random() * 4 + 1)] as action_performed,
    'SUCCESS' as result,
    jsonb_build_object('rule', 'FISMA', 'standard', 'NIST-800-53', 'compliant', true) as metadata,
    NOW() - (random() * INTERVAL '7 days') as event_timestamp
FROM generate_series(1, 500);

-- ============================================================================
-- 4. KMS KEY ROTATION LOG - Rotation events
-- ============================================================================

-- HOT tier key rotation (45 days ago)
INSERT INTO kms_key_rotation_log (key_id, key_alias, key_type, storage_tier, rotation_type, old_key_version, new_key_version, rotated_at, rotated_by, reason, re_encryption_required, re_encryption_progress, status)
VALUES
('arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012', 'wildfire-hot-tier-key', 'AES-256', 'HOT', 'AUTOMATIC', 3, 4, NOW() - INTERVAL '45 days', 'system', 'Scheduled 90-day automatic rotation', TRUE, 100.0, 'COMPLETED');

-- WARM tier key rotation (38 days ago)
INSERT INTO kms_key_rotation_log (key_id, key_alias, key_type, storage_tier, rotation_type, old_key_version, new_key_version, rotated_at, rotated_by, reason, re_encryption_required, re_encryption_progress, status)
VALUES
('arn:aws:kms:us-west-2:123456789012:key/22345678-2234-2234-2234-223456789012', 'wildfire-warm-tier-key', 'AES-256', 'WARM', 'AUTOMATIC', 2, 3, NOW() - INTERVAL '38 days', 'system', 'Scheduled 90-day automatic rotation', TRUE, 100.0, 'COMPLETED');

-- COLD tier key rotation (52 days ago)
INSERT INTO kms_key_rotation_log (key_id, key_alias, key_type, storage_tier, rotation_type, old_key_version, new_key_version, rotated_at, rotated_by, reason, re_encryption_required, re_encryption_progress, status)
VALUES
('arn:aws:kms:us-west-2:123456789012:key/32345678-3234-3234-3234-323456789012', 'wildfire-cold-tier-key', 'AES-256', 'COLD', 'AUTOMATIC', 5, 6, NOW() - INTERVAL '52 days', 'system', 'Scheduled 90-day automatic rotation', TRUE, 100.0, 'COMPLETED');

-- ARCHIVE tier key rotation (60 days ago)
INSERT INTO kms_key_rotation_log (key_id, key_alias, key_type, storage_tier, rotation_type, old_key_version, new_key_version, rotated_at, rotated_by, reason, re_encryption_required, re_encryption_progress, status)
VALUES
('arn:aws:kms:us-west-2:123456789012:key/42345678-4234-4234-4234-423456789012', 'wildfire-archive-tier-key', 'AES-256', 'ARCHIVE', 'AUTOMATIC', 1, 2, NOW() - INTERVAL '60 days', 'system', 'Scheduled 90-day automatic rotation', TRUE, 100.0, 'COMPLETED');

-- ============================================================================
-- 5. REPLICATION LAG LOG - PostgreSQL streaming replication
-- ============================================================================

-- Generate replication lag measurements for last 7 days (every 10 minutes)
INSERT INTO replication_lag_log (primary_host, replica_host, replication_lag_seconds, replication_lag_bytes, replay_lag_seconds, write_lag_seconds, flush_lag_seconds, sync_state, sync_priority, replica_status, measured_at)
SELECT
    'pg-primary-01.wildfire.local' as primary_host,
    'pg-standby-01.wildfire.local' as replica_host,
    -- Simulate realistic lag: mostly 15-35s, occasional spikes to 60s
    CASE
        WHEN random() < 0.85 THEN 15 + random() * 20  -- 85% low lag (15-35s)
        WHEN random() < 0.95 THEN 35 + random() * 20  -- 10% medium lag (35-55s)
        ELSE 55 + random() * 25  -- 5% high lag (55-80s)
    END as replication_lag_seconds,
    floor(random() * 50000000 + 1000000)::BIGINT as replication_lag_bytes,
    CASE
        WHEN random() < 0.90 THEN 10 + random() * 15
        ELSE 25 + random() * 20
    END as replay_lag_seconds,
    5 + random() * 10 as write_lag_seconds,
    8 + random() * 12 as flush_lag_seconds,
    'async' as sync_state,
    1 as sync_priority,
    CASE WHEN random() > 0.02 THEN 'STREAMING' ELSE 'CATCHUP' END as replica_status,
    NOW() - ((generate_series * 10) * INTERVAL '1 minute') as measured_at
FROM generate_series(0, 1000);

-- ============================================================================
-- 6. COST TRACKING - Monthly cost data
-- ============================================================================

-- Current month costs (October 2025)
INSERT INTO cost_tracking (cost_period, storage_tier, storage_gb, cost_usd, budget_usd, variance_percent, cost_type)
VALUES
    ('2025-10-01', 'HOT', 162.0, 3.73, 4.50, -17.1, 'STORAGE'),
    ('2025-10-01', 'WARM', 1998.0, 41.96, 45.00, -6.8, 'STORAGE'),
    ('2025-10-01', 'COLD', 1997.0, 7.99, 10.00, -20.1, 'STORAGE'),
    ('2025-10-01', 'ARCHIVE', 3118.0, 3.09, 5.00, -38.2, 'STORAGE'),
    ('2025-10-01', 'HOT', 0, 0.50, 1.00, -50.0, 'DATA_TRANSFER'),
    ('2025-10-01', 'WARM', 0, 1.20, 2.00, -40.0, 'DATA_TRANSFER'),
    ('2025-10-01', 'COLD', 0, 0.80, 1.50, -46.7, 'DATA_TRANSFER'),
    ('2025-10-01', 'HOT', 0, 0.30, 0.50, -40.0, 'KMS'),
    ('2025-10-01', 'WARM', 0, 0.25, 0.40, -37.5, 'KMS');

-- Previous month (September 2025)
INSERT INTO cost_tracking (cost_period, storage_tier, storage_gb, cost_usd, budget_usd, variance_percent, cost_type)
VALUES
    ('2025-09-01', 'HOT', 155.0, 3.57, 4.50, -20.7, 'STORAGE'),
    ('2025-09-01', 'WARM', 1850.0, 38.85, 45.00, -13.7, 'STORAGE'),
    ('2025-09-01', 'COLD', 1920.0, 7.68, 10.00, -23.2, 'STORAGE'),
    ('2025-09-01', 'ARCHIVE', 2980.0, 2.95, 5.00, -41.0, 'STORAGE');

-- Refresh materialized views (if any)
ANALYZE query_performance_log;
ANALYZE backup_log;
ANALYZE audit_log;
ANALYZE kms_key_rotation_log;
ANALYZE replication_lag_log;
ANALYZE cost_tracking;

-- Print summary statistics
SELECT 'Query Performance Log' as table_name, COUNT(*) as row_count FROM query_performance_log
UNION ALL
SELECT 'Backup Log', COUNT(*) FROM backup_log
UNION ALL
SELECT 'Audit Log', COUNT(*) FROM audit_log
UNION ALL
SELECT 'KMS Rotation Log', COUNT(*) FROM kms_key_rotation_log
UNION ALL
SELECT 'Replication Lag Log', COUNT(*) FROM replication_lag_log
UNION ALL
SELECT 'Cost Tracking', COUNT(*) FROM cost_tracking;
