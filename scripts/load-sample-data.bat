@echo off
REM Load sample data for testing/demo purposes
REM This is OPTIONAL and only for testing - not for production!

echo.
echo ==============================================================================
echo   SAMPLE DATA LOADER - FOR TESTING ONLY
echo ==============================================================================
echo.
echo WARNING: This will load FAKE sample data into your database!
echo          Only use this for testing and demonstrations.
echo.
echo Press Ctrl+C to cancel, or any other key to continue...
pause >nul

echo.
echo Checking if PostgreSQL is running...
docker ps --filter "name=wildfire-postgres" --format "{{.Names}}" 2>nul | findstr wildfire-postgres >nul
if errorlevel 1 (
    echo [ERROR] PostgreSQL is not running.
    echo Please run: docker-compose up -d postgres
    pause
    exit /b 1
)

echo [OK] PostgreSQL is running
echo.

echo Loading sample data files...
echo.

echo [1/2] Loading monitoring sample data...
docker exec -i wildfire-postgres psql -U wildfire_user -d wildfire_db < scripts/database-samples/populate_monitoring_data.sql 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to load monitoring data
) else (
    echo [OK] Monitoring sample data loaded
)

echo.
echo [2/2] Adding recent activity data...
docker exec -i wildfire-postgres psql -U wildfire_user -d wildfire_db < scripts/database-samples/add_recent_activity.sql 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to load recent activity
) else (
    echo [OK] Recent activity data loaded
)

echo.
echo ==============================================================================
echo   SAMPLE DATA LOADING COMPLETE
echo ==============================================================================
echo.
echo The following sample data has been loaded:
echo.
echo - Query performance metrics (last 7 days)
echo - Storage metrics history
echo - Migration history
echo - Security audit logs
echo - Recent activity (last 24 hours)
echo.
echo You can now view this data in:
echo - Grafana dashboards: http://localhost:3010
echo - pgAdmin: http://localhost:5050
echo - Monitoring script: monitor-streaming.bat
echo.
pause