-- ============================================================================
-- INITIALIZE POSTGRESQL EXTENSIONS
-- This script runs FIRST to ensure all necessary extensions are available
-- ============================================================================

-- Create required databases for services
-- Check if airflow_db exists, create if it doesn't
SELECT 'CREATE DATABASE airflow_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow_db')\gexec

-- Enable PostGIS for geospatial data
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Enable TimescaleDB for time-series data (if available)
-- Note: Commented out if not using TimescaleDB image
-- CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable foreign data wrapper for external sources
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

-- Enable full text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable JSON indexing
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Grant permissions to wildfire_user
GRANT ALL PRIVILEGES ON SCHEMA public TO wildfire_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO wildfire_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO wildfire_user;

-- Create topology schema if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'topology') THEN
        CREATE SCHEMA topology;
        GRANT ALL ON SCHEMA topology TO wildfire_user;
    END IF;
END
$$;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Extensions initialized successfully at %', NOW();
END
$$;