-- Enhanced Fire Incidents Management Schema
-- This adds proper fire incident tracking with containment status

-- Fire Incidents table (managed fire events with status)
CREATE TABLE IF NOT EXISTS fire_incidents_managed (
    id SERIAL PRIMARY KEY,
    incident_name VARCHAR(255) NOT NULL,
    counties TEXT[] DEFAULT '{}',
    start_date DATE NOT NULL,
    discovery_time TIMESTAMP WITH TIME ZONE,
    contained_date DATE,
    contained_time TIMESTAMP WITH TIME ZONE,

    -- Location
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,

    -- Size and impact
    acres_burned DECIMAL(12,2) DEFAULT 0,
    structures_threatened INTEGER DEFAULT 0,
    structures_destroyed INTEGER DEFAULT 0,

    -- Status tracking
    containment_percentage INTEGER DEFAULT 0 CHECK (containment_percentage >= 0 AND containment_percentage <= 100),
    incident_status VARCHAR(50) DEFAULT 'active' CHECK (incident_status IN ('active', 'contained', 'controlled', 'out')),
    cause VARCHAR(100),

    -- Resources
    personnel_assigned INTEGER DEFAULT 0,
    engines INTEGER DEFAULT 0,
    aircraft INTEGER DEFAULT 0,

    -- Administrative
    incident_commander VARCHAR(255),
    cooperating_agencies TEXT[],
    cost_to_date DECIMAL(15,2),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data_source VARCHAR(100) DEFAULT 'calfire'
);

-- Link table between detections and managed incidents
CREATE TABLE IF NOT EXISTS fire_detection_to_incident (
    id SERIAL PRIMARY KEY,
    detection_id UUID NOT NULL, -- Links to fire_incidents.incident_id
    managed_incident_id INTEGER NOT NULL REFERENCES fire_incidents_managed(id),
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_fire_incidents_managed_status ON fire_incidents_managed(incident_status);
CREATE INDEX IF NOT EXISTS idx_fire_incidents_managed_date ON fire_incidents_managed(start_date);
CREATE INDEX IF NOT EXISTS idx_fire_incidents_managed_location ON fire_incidents_managed(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_fire_incidents_managed_containment ON fire_incidents_managed(containment_percentage);

-- Insert sample active fire incidents for 2025
INSERT INTO fire_incidents_managed (
    incident_name, counties, start_date, discovery_time, latitude, longitude,
    acres_burned, containment_percentage, incident_status, cause,
    personnel_assigned, engines, aircraft, incident_commander
) VALUES
-- Currently Active Fires (< 100% containment)
('Garnet Fire', ARRAY['Fresno'], '2025-08-24', '2025-08-24 14:30:00', 37.2431, -119.1871, 60263, 91, 'active', 'Unknown', 2847, 89, 12, 'Battalion Chief Rodriguez'),
('Meadow Fire', ARRAY['Riverside'], '2025-09-15', '2025-09-15 16:45:00', 33.8734, -116.9058, 8420, 65, 'active', 'Equipment Use', 1205, 45, 8, 'Captain Thompson'),
('Ridge Complex', ARRAY['Shasta', 'Tehama'], '2025-09-12', '2025-09-12 11:20:00', 40.3628, -121.5555, 15680, 78, 'active', 'Lightning', 1890, 67, 15, 'Division Chief Martinez'),
('Canyon Fire', ARRAY['Orange'], '2025-09-18', '2025-09-18 19:15:00', 33.7175, -117.8311, 2840, 25, 'active', 'Arson', 856, 32, 6, 'Captain Davis'),
('Valley Fire', ARRAY['Napa'], '2025-09-16', '2025-09-16 08:30:00', 38.4404, -122.2711, 4250, 45, 'active', 'Powerlines', 967, 38, 9, 'Battalion Chief Wilson'),
('Summit Fire', ARRAY['San Bernardino'], '2025-09-17', '2025-09-17 13:45:00', 34.2839, -117.3281, 12900, 82, 'active', 'Unknown', 1634, 58, 11, 'Captain Johnson'),

-- Recently Contained Fires (100% containment in last 30 days)
('Oak Fire', ARRAY['Mariposa'], '2025-08-28', '2025-08-28 15:20:00', 37.4419, -120.0430, 19244, 100, 'contained', 'Equipment Use', 0, 0, 0, 'Division Chief Anderson'),
('Creek Fire', ARRAY['Tulare'], '2025-08-20', '2025-08-20 10:15:00', 36.7783, -118.9717, 8965, 100, 'contained', 'Lightning', 0, 0, 0, 'Captain Lee'),
('Brush Fire', ARRAY['Los Angeles'], '2025-09-10', '2025-09-10 21:30:00', 34.1478, -118.1445, 1250, 100, 'contained', 'Smoking', 0, 0, 0, 'Battalion Chief Garcia');

-- Update timestamps
UPDATE fire_incidents_managed SET updated_at = NOW() WHERE incident_status = 'active';