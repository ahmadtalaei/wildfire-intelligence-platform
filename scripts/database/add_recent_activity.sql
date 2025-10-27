-- Add Recent Activity to Make Dashboard More Realistic
-- This simulates migrations and security events from the last 24 hours

-- ============================================================================
-- 1. UPDATE DATA_CATALOG: Add recent migrations
-- ============================================================================

-- Mark 3 HOT tier files as migrated to WARM in the last 24 hours
UPDATE data_catalog
SET
    migrated_to_warm_at = NOW() - (random() * INTERVAL '20 hours'),
    storage_tier = 'WARM'
WHERE id IN (
    SELECT id FROM data_catalog
    WHERE storage_tier = 'HOT'
    AND migrated_to_warm_at IS NULL
    LIMIT 3
);

-- Mark 2 WARM tier files as migrated to COLD in the last 24 hours
UPDATE data_catalog
SET
    migrated_to_cold_at = NOW() - (random() * INTERVAL '18 hours'),
    storage_tier = 'COLD'
WHERE id IN (
    SELECT id FROM data_catalog
    WHERE storage_tier = 'WARM'
    AND migrated_to_cold_at IS NULL
    LIMIT 2
);

-- Mark 1 COLD tier file as migrated to ARCHIVE in the last 24 hours
UPDATE data_catalog
SET
    migrated_to_archive_at = NOW() - (random() * INTERVAL '12 hours'),
    storage_tier = 'ARCHIVE'
WHERE id IN (
    SELECT id FROM data_catalog
    WHERE storage_tier = 'COLD'
    AND migrated_to_archive_at IS NULL
    LIMIT 1
);

-- ============================================================================
-- 2. ADD RECENT SECURITY EVENTS (Last 1 hour)
-- ============================================================================

-- Add 8 recent failed authentication attempts (last hour)
INSERT INTO audit_log (event_type, event_category, severity, user_id, username, source_ip, resource_accessed, action_performed, result, error_code, error_message, event_timestamp)
SELECT
    'AUTH_FAILURE' as event_type,
    'AUTHENTICATION' as event_category,
    'WARNING' as severity,
    'user_' || floor(random() * 20 + 1) as user_id,
    'analyst_' || floor(random() * 20 + 1) as username,
    '10.0.' || floor(random() * 255) || '.' || floor(random() * 255) as source_ip,
    '/api/auth/login' as resource_accessed,
    'LOGIN' as action_performed,
    'FAILURE' as result,
    (ARRAY['AUTH_INVALID_PASSWORD', 'AUTH_INVALID_USERNAME', 'AUTH_ACCOUNT_LOCKED'])[floor(random() * 3 + 1)] as error_code,
    'Authentication failed' as error_message,
    NOW() - ((55 - generate_series * 5) * INTERVAL '1 minute') as event_timestamp
FROM generate_series(1, 8);

-- Add 2 recent API rate limit violations (last hour)
INSERT INTO audit_log (event_type, event_category, severity, user_id, username, source_ip, resource_accessed, action_performed, result, error_code, error_message, metadata, event_timestamp)
SELECT
    'API_VIOLATION' as event_type,
    'API' as event_category,
    'WARNING' as severity,
    'user_' || floor(random() * 5 + 1) as user_id,
    'analyst_' || floor(random() * 5 + 1) as username,
    '10.0.' || floor(random() * 255) || '.' || floor(random() * 255) as source_ip,
    '/api/v1/data/export' as resource_accessed,
    'EXPORT' as action_performed,
    'BLOCKED' as result,
    'RATE_LIMIT_EXCEEDED' as error_code,
    'API rate limit exceeded: 1000 requests per hour' as error_message,
    jsonb_build_object('limit', 1000, 'window_seconds', 3600, 'requests_made', 1000 + floor(random() * 100)) as metadata,
    NOW() - ((50 - generate_series * 25) * INTERVAL '1 minute') as event_timestamp
FROM generate_series(1, 2);

-- Add successful auth events (last hour) for context
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
    NOW() - (random() * INTERVAL '60 minutes') as event_timestamp
FROM generate_series(1, 50);

-- ============================================================================
-- 3. VERIFY RESULTS
-- ============================================================================

-- Show migration counts
SELECT
    'Hot → Warm (24hr)' as metric,
    COUNT(*) as count
FROM data_catalog
WHERE migrated_to_warm_at >= NOW() - INTERVAL '24 hours'
UNION ALL
SELECT
    'Warm → Cold (24hr)',
    COUNT(*)
FROM data_catalog
WHERE migrated_to_cold_at >= NOW() - INTERVAL '24 hours'
UNION ALL
SELECT
    'Cold → Archive (24hr)',
    COUNT(*)
FROM data_catalog
WHERE migrated_to_archive_at >= NOW() - INTERVAL '24 hours';

-- Show security events
SELECT
    'Failed Auth (1hr)' as metric,
    COUNT(*) as count
FROM audit_log
WHERE event_type = 'AUTH_FAILURE'
AND event_timestamp >= NOW() - INTERVAL '1 hour'
UNION ALL
SELECT
    'API Violations (1hr)',
    COUNT(*)
FROM audit_log
WHERE event_type = 'API_VIOLATION'
AND event_timestamp >= NOW() - INTERVAL '1 hour';

-- Show updated file distribution
SELECT
    storage_tier,
    COUNT(*) as file_count,
    pg_size_pretty(SUM(size_bytes)::bigint) as total_size
FROM data_catalog
WHERE deleted_at IS NULL
GROUP BY storage_tier
ORDER BY CASE storage_tier WHEN 'HOT' THEN 1 WHEN 'WARM' THEN 2 WHEN 'COLD' THEN 3 WHEN 'ARCHIVE' THEN 4 END;
