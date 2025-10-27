-- Create databases for different services
CREATE DATABASE fire_risk_db;
CREATE DATABASE data_catalog_db;
CREATE DATABASE user_management_db;
CREATE DATABASE notification_db;

-- Create users with appropriate permissions
CREATE USER fire_risk_user WITH PASSWORD 'fire_risk_password';
CREATE USER catalog_user WITH PASSWORD 'catalog_password';
CREATE USER auth_user WITH PASSWORD 'auth_password';
CREATE USER notification_user WITH PASSWORD 'notification_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE fire_risk_db TO fire_risk_user;
GRANT ALL PRIVILEGES ON DATABASE data_catalog_db TO catalog_user;
GRANT ALL PRIVILEGES ON DATABASE user_management_db TO auth_user;
GRANT ALL PRIVILEGES ON DATABASE notification_db TO notification_user;

-- Connect to wildfire_db and create initial schema
\c wildfire_db;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'analyst',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Data sources table
CREATE TABLE IF NOT EXISTS data_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    url VARCHAR(500),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Fire events table
CREATE TABLE IF NOT EXISTS fire_events (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    confidence INTEGER,
    brightness DECIMAL(6,2),
    frp DECIMAL(8,2),
    acquisition_date DATE NOT NULL,
    acquisition_time TIME,
    satellite VARCHAR(50),
    instrument VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_fire_events_date ON fire_events(acquisition_date);
CREATE INDEX IF NOT EXISTS idx_fire_events_location ON fire_events(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Insert sample data
INSERT INTO users (username, email, password_hash, role) VALUES
('fire_chief', 'chief@calfire.gov', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewVyLDvvOmVRhPYm', 'fire_chief'),
('data_analyst', 'analyst@calfire.gov', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewVyLDvvOmVRhPYm', 'analyst'),
('data_scientist', 'scientist@calfire.gov', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewVyLDvvOmVRhPYm', 'scientist'),
('field_team', 'field@calfire.gov', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewVyLDvvOmVRhPYm', 'field_team');

INSERT INTO data_sources (name, type, url, description) VALUES
('MODIS Active Fire', 'satellite', 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/', 'MODIS active fire detection data'),
('ERA5 Weather', 'weather', 'https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels', 'ERA5 weather reanalysis data'),
('VIIRS Fire Data', 'satellite', 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/', 'VIIRS active fire detection data');
