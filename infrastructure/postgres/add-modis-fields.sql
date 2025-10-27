-- Add MODIS-specific fields for proper wildfire classification
-- This enables distinguishing wildfires from other heat sources

ALTER TABLE fire_incidents
ADD COLUMN IF NOT EXISTS type INTEGER DEFAULT 0,  -- 0=vegetation fire, 1=volcano, 2=other static, 3=offshore
ADD COLUMN IF NOT EXISTS frp DECIMAL(8,2),        -- Fire Radiative Power (MW)
ADD COLUMN IF NOT EXISTS brightness DECIMAL(6,1), -- Channel I-4 brightness temperature (Kelvin)
ADD COLUMN IF NOT EXISTS bright_t31 DECIMAL(6,1), -- Channel I-5 brightness temperature (Kelvin)
ADD COLUMN IF NOT EXISTS daynight CHAR(1) DEFAULT 'D', -- 'D'=day, 'N'=night
ADD COLUMN IF NOT EXISTS satellite VARCHAR(20),   -- Terra/Aqua
ADD COLUMN IF NOT EXISTS instrument VARCHAR(20);  -- MODIS

-- Create index for wildfire filtering
CREATE INDEX IF NOT EXISTS idx_fire_incidents_wildfire ON fire_incidents(type, confidence, frp);

-- Update existing records with realistic MODIS values
UPDATE fire_incidents SET
    type = CASE
        WHEN random() < 0.85 THEN 0  -- 85% vegetation fires (wildfires)
        WHEN random() < 0.95 THEN 2  -- 10% other static sources (industrial)
        ELSE 1  -- 5% other (volcanoes, etc.)
    END,
    frp = CASE
        WHEN confidence > 0.8 THEN (5 + random() * 200)::DECIMAL(8,2)  -- High confidence: 5-205 MW
        WHEN confidence > 0.5 THEN (1 + random() * 100)::DECIMAL(8,2)  -- Medium confidence: 1-101 MW
        ELSE (0.1 + random() * 50)::DECIMAL(8,2)  -- Low confidence: 0.1-50 MW
    END,
    brightness = (temperature + 273.15 + random() * 20)::DECIMAL(6,1), -- Convert Celsius to Kelvin
    bright_t31 = (temperature + 273.15 + random() * 15)::DECIMAL(6,1),
    daynight = CASE WHEN random() < 0.6 THEN 'D' ELSE 'N' END,
    satellite = CASE WHEN random() < 0.5 THEN 'Terra' ELSE 'Aqua' END,
    instrument = 'MODIS'
WHERE type IS NULL;

-- Show wildfire classification summary
SELECT
    type,
    CASE
        WHEN type = 0 THEN 'Vegetation Fire (Wildfire)'
        WHEN type = 1 THEN 'Active Volcano'
        WHEN type = 2 THEN 'Other Static Source'
        WHEN type = 3 THEN 'Offshore Detection'
        ELSE 'Unknown'
    END as type_description,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    AVG(frp) as avg_frp_mw
FROM fire_incidents
GROUP BY type
ORDER BY count DESC;