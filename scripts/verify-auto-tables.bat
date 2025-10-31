@echo off
REM Verify that auto-table creation is working properly

echo.
echo ==============================================================================
echo   VERIFYING AUTO-TABLE CREATION SETUP
echo ==============================================================================
echo.

echo [1/5] Checking if PostgreSQL initialization includes specialized tables...
if exist "scripts\database\01_create_specialized_tables.sql" (
    echo [OK] Specialized tables SQL found in initialization directory
) else (
    echo [ERROR] Missing specialized tables SQL in scripts\database\
)

echo.
echo [2/5] Checking if extensions initialization script exists...
if exist "scripts\database\00_init_extensions.sql" (
    echo [OK] Extensions initialization script found
) else (
    echo [ERROR] Missing extensions initialization script
)

echo.
echo [3/5] Checking if table generator script exists...
if exist "services\data-ingestion-service\src\utils\generate_tables.py" (
    echo [OK] Table generator Python script found
) else (
    echo [ERROR] Missing table generator script
)

echo.
echo [4/5] Checking if entrypoint script exists...
if exist "services\data-ingestion-service\entrypoint.sh" (
    echo [OK] Entrypoint script found for auto-creation
) else (
    echo [ERROR] Missing entrypoint script
)

echo.
echo [5/5] Checking database for data source tables...
docker exec wildfire-postgres psql -U wildfire_user -d wildfire_db -c "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public' AND (table_name LIKE 'firms%%' OR table_name LIKE 'noaa%%' OR table_name LIKE 'era5%%' OR table_name LIKE 'gfs%%' OR table_name LIKE 'iot%%');" 2>nul

echo.
echo ==============================================================================
echo   SETUP SUMMARY
echo ==============================================================================
echo.
echo The system is now configured to:
echo.
echo 1. AUTOMATICALLY create tables during PostgreSQL initialization
echo    - Scripts in scripts/database/ run when container first starts
echo    - Tables for all data sources are created immediately
echo.
echo 2. DYNAMICALLY discover connectors and create tables
echo    - When data-ingestion-service starts, it scans connectors/
echo    - Missing tables are created automatically
echo    - New connectors automatically get their tables
echo.
echo 3. TABLES CREATED FOR THESE DATA SOURCES:
echo    - NASA FIRMS (5 satellites: VIIRS S-NPP, NOAA-20/21, MODIS Terra/Aqua)
echo    - NOAA Weather (stations, alerts, forecasts)
echo    - ERA5 Reanalysis (land and atmospheric)
echo    - GFS/NAM Forecasts
echo    - AirNow Air Quality
echo    - PurpleAir Sensors
echo    - IoT MQTT Devices
echo    - Satellite Imagery Metadata
echo.
echo ==============================================================================
echo   TO APPLY CHANGES
echo ==============================================================================
echo.
echo 1. Rebuild the data-ingestion-service:
echo    docker-compose build data-ingestion-service
echo.
echo 2. For fresh start with all tables:
echo    docker-compose down -v
echo    docker-compose up -d
echo.
echo 3. Or just restart to apply:
echo    docker-compose restart data-ingestion-service postgres
echo.
echo ==============================================================================
echo.
pause