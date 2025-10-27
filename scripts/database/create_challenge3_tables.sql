-- Challenge 3: Analytics Platform & Data Clearing House Tables
-- Creates tables and views for tracking user activity, queries, sessions, reports, and exports

-- ============================================================================
-- USER SESSIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,
    user_role VARCHAR(50) NOT NULL, -- fire_chief, data_analyst, data_scientist, admin, field_responder
    session_start TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    session_end TIMESTAMP WITH TIME ZONE,
    ip_address VARCHAR(50),
    user_agent TEXT,
    dashboard_accessed VARCHAR(100), -- fire-chief, analyst, scientist, admin
    is_active BOOLEAN DEFAULT TRUE,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_role ON user_sessions(user_role);
CREATE INDEX IF NOT EXISTS idx_user_sessions_start ON user_sessions(session_start);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active, last_activity);

-- ============================================================================
-- ANALYTICS QUERIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics_queries (
    query_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES user_sessions(session_id),
    user_id VARCHAR(100) NOT NULL,
    user_role VARCHAR(50) NOT NULL,
    query_type VARCHAR(50) NOT NULL, -- sql, rest_api, graphql, export, visualization
    query_text TEXT,
    query_status VARCHAR(20) NOT NULL, -- success, failed, timeout
    response_time_ms INT NOT NULL,
    rows_returned INT,
    data_source VARCHAR(50), -- postgresql, minio, s3, cache
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_queries_user_role ON analytics_queries(user_role);
CREATE INDEX IF NOT EXISTS idx_analytics_queries_executed ON analytics_queries(executed_at);
CREATE INDEX IF NOT EXISTS idx_analytics_queries_status ON analytics_queries(query_status);

-- ============================================================================
-- REPORTS GENERATED TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS reports_generated (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES user_sessions(session_id),
    user_id VARCHAR(100) NOT NULL,
    user_role VARCHAR(50) NOT NULL,
    report_name VARCHAR(200) NOT NULL,
    report_type VARCHAR(50) NOT NULL, -- summary, detailed, statistical, geospatial, ml_model
    output_format VARCHAR(20) NOT NULL, -- pdf, excel, csv, html, json
    file_size_bytes BIGINT,
    generation_time_ms INT NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_user_role ON reports_generated(user_role);
CREATE INDEX IF NOT EXISTS idx_reports_generated ON reports_generated(generated_at);

-- ============================================================================
-- DATA EXPORTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS data_exports (
    export_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES user_sessions(session_id),
    user_id VARCHAR(100) NOT NULL,
    user_role VARCHAR(50) NOT NULL,
    export_type VARCHAR(50) NOT NULL, -- csv, json, geojson, parquet, shapefile
    dataset_name VARCHAR(200) NOT NULL,
    row_count INT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    export_status VARCHAR(20) NOT NULL, -- completed, failed, in_progress
    export_time_ms INT NOT NULL,
    exported_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exports_user_role ON data_exports(user_role);
CREATE INDEX IF NOT EXISTS idx_exports_exported ON data_exports(exported_at);
CREATE INDEX IF NOT EXISTS idx_exports_status ON data_exports(export_status);

-- ============================================================================
-- API USAGE TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_usage (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES user_sessions(session_id),
    user_id VARCHAR(100),
    user_role VARCHAR(50),
    endpoint VARCHAR(200) NOT NULL,
    http_method VARCHAR(10) NOT NULL, -- GET, POST, PUT, DELETE
    status_code INT NOT NULL,
    response_time_ms INT NOT NULL,
    request_size_bytes INT,
    response_size_bytes INT,
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_usage_requested ON api_usage(requested_at);
CREATE INDEX IF NOT EXISTS idx_api_usage_status ON api_usage(status_code);

-- ============================================================================
-- DASHBOARD INTERACTIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS dashboard_interactions (
    interaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES user_sessions(session_id),
    user_id VARCHAR(100) NOT NULL,
    user_role VARCHAR(50) NOT NULL,
    dashboard_name VARCHAR(100) NOT NULL,
    widget_name VARCHAR(100),
    interaction_type VARCHAR(50) NOT NULL, -- view, filter, drill_down, export, refresh
    interaction_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dashboard_interactions_user ON dashboard_interactions(user_role);
CREATE INDEX IF NOT EXISTS idx_dashboard_interactions_time ON dashboard_interactions(interaction_timestamp);

-- ============================================================================
-- VIEWS FOR GRAFANA
-- ============================================================================

-- Active user sessions by role
CREATE OR REPLACE VIEW v_active_user_sessions AS
SELECT
    user_role,
    COUNT(*) as active_sessions,
    COUNT(DISTINCT user_id) as unique_users,
    MAX(last_activity) as last_activity_time
FROM user_sessions
WHERE is_active = TRUE
  AND last_activity > NOW() - INTERVAL '1 hour'
GROUP BY user_role;

-- Analytics query metrics by role
CREATE OR REPLACE VIEW v_analytics_query_metrics AS
SELECT
    user_role,
    COUNT(*) as total_queries,
    AVG(response_time_ms) as avg_response_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_response_ms,
    COUNT(*) FILTER (WHERE query_status = 'success') as successful_queries,
    COUNT(*) FILTER (WHERE query_status = 'failed') as failed_queries,
    SUM(rows_returned) as total_rows_returned,
    MAX(executed_at) as last_query_time
FROM analytics_queries
WHERE executed_at > NOW() - INTERVAL '1 hour'
GROUP BY user_role;

-- Reports generated by role
CREATE OR REPLACE VIEW v_reports_by_role AS
SELECT
    user_role,
    COUNT(*) as total_reports,
    COUNT(DISTINCT report_type) as unique_report_types,
    AVG(generation_time_ms) as avg_generation_ms,
    SUM(file_size_bytes) as total_size_bytes,
    MAX(generated_at) as last_report_time
FROM reports_generated
WHERE generated_at > NOW() - INTERVAL '1 hour'
GROUP BY user_role;

-- Data exports by role
CREATE OR REPLACE VIEW v_exports_by_role AS
SELECT
    user_role,
    COUNT(*) as total_exports,
    COUNT(DISTINCT export_type) as unique_export_types,
    SUM(row_count) as total_rows_exported,
    SUM(file_size_bytes) as total_size_bytes,
    MAX(exported_at) as last_export_time
FROM data_exports
WHERE exported_at > NOW() - INTERVAL '1 hour'
  AND export_status = 'completed'
GROUP BY user_role;

-- Platform usage summary
CREATE OR REPLACE VIEW v_platform_usage_summary AS
SELECT
    DATE_TRUNC('minute', interaction_timestamp) as time_bucket,
    user_role,
    dashboard_name,
    COUNT(*) as interaction_count
FROM dashboard_interactions
WHERE interaction_timestamp > NOW() - INTERVAL '6 hours'
GROUP BY DATE_TRUNC('minute', interaction_timestamp), user_role, dashboard_name
ORDER BY time_bucket DESC;

-- API endpoint usage
CREATE OR REPLACE VIEW v_api_endpoint_usage AS
SELECT
    endpoint,
    COUNT(*) as request_count,
    AVG(response_time_ms) as avg_response_ms,
    COUNT(*) FILTER (WHERE status_code >= 200 AND status_code < 300) as successful_requests,
    COUNT(*) FILTER (WHERE status_code >= 400) as failed_requests,
    MAX(requested_at) as last_request_time
FROM api_usage
WHERE requested_at > NOW() - INTERVAL '1 hour'
GROUP BY endpoint
ORDER BY request_count DESC;

-- Overall Challenge 3 metrics
CREATE OR REPLACE VIEW v_challenge3_overall_metrics AS
SELECT
    (SELECT COUNT(DISTINCT user_id) FROM user_sessions WHERE is_active = TRUE AND last_activity > NOW() - INTERVAL '1 hour') as active_users,
    (SELECT COUNT(*) FROM analytics_queries WHERE executed_at > NOW() - INTERVAL '1 hour') as total_queries,
    (SELECT AVG(response_time_ms) FROM analytics_queries WHERE executed_at > NOW() - INTERVAL '1 hour') as avg_query_response_ms,
    (SELECT COUNT(*) FROM reports_generated WHERE generated_at > NOW() - INTERVAL '1 hour') as reports_generated,
    (SELECT COUNT(*) FROM data_exports WHERE exported_at > NOW() - INTERVAL '1 hour' AND export_status = 'completed') as data_exports,
    (SELECT COUNT(*) FROM api_usage WHERE requested_at > NOW() - INTERVAL '1 hour') as api_requests;

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO wildfire_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO wildfire_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO wildfire_user;

COMMENT ON TABLE user_sessions IS 'Challenge 3: Tracks user sessions across all role-based dashboards';
COMMENT ON TABLE analytics_queries IS 'Challenge 3: Logs all analytical queries executed through the platform';
COMMENT ON TABLE reports_generated IS 'Challenge 3: Tracks report generation activity';
COMMENT ON TABLE data_exports IS 'Challenge 3: Logs all data export operations';
COMMENT ON TABLE api_usage IS 'Challenge 3: Tracks API endpoint usage for the data clearing house';
COMMENT ON TABLE dashboard_interactions IS 'Challenge 3: Records user interactions with dashboards';
