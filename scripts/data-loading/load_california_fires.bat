@echo off
REM =============================================================================
REM California Historical Fire Data Loader
REM Loads realistic fire incident data based on major California fires
REM =============================================================================

echo ============================================================
echo [FIRE] Loading California Historical Fire Data [FIRE]
echo ============================================================

set API_URL=http://localhost:8001/api/v1/fires
set "TIMESTAMP=2023-08-15T14:30:00Z"

echo.
echo Testing API connection...
curl -s %API_URL% >nul
if %ERRORLEVEL% neq 0 (
    echo [X] Error: Cannot connect to API at %API_URL%
    echo Make sure the platform is running: docker-compose -f docker-compose-simple.yml up -d
    pause
    exit /b 1
)
echo [CHECK] API connection successful

echo.
echo Loading major California fire incidents...

REM Camp Fire (Paradise, 2018 - deadliest fire)
echo Loading Camp Fire data...
curl -X POST %API_URL% ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": 39.7596, \"longitude\": -121.6219, \"confidence\": 0.95, \"temperature\": 850.0, \"source\": \"Camp_Fire_2018\", \"timestamp\": \"2018-11-08T06:30:00Z\"}"

REM Thomas Fire (Ventura County, 2017)
echo Loading Thomas Fire data...
curl -X POST %API_URL% ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": 34.4208, \"longitude\": -119.1391, \"confidence\": 0.92, \"temperature\": 780.0, \"source\": \"Thomas_Fire_2017\", \"timestamp\": \"2017-12-04T18:45:00Z\"}"

REM Tubbs Fire (Napa County, 2017)
echo Loading Tubbs Fire data...
curl -X POST %API_URL% ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": 38.5125, \"longitude\": -122.5572, \"confidence\": 0.89, \"temperature\": 720.0, \"source\": \"Tubbs_Fire_2017\", \"timestamp\": \"2017-10-08T21:00:00Z\"}"

REM Carr Fire (Redding, 2018)
echo Loading Carr Fire data...
curl -X POST %API_URL% ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": 40.5865, \"longitude\": -122.3917, \"confidence\": 0.91, \"temperature\": 800.0, \"source\": \"Carr_Fire_2018\", \"timestamp\": \"2018-07-23T13:15:00Z\"}"

REM Woolsey Fire (Malibu, 2018)
echo Loading Woolsey Fire data...
curl -X POST %API_URL% ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": 34.0259, \"longitude\": -118.7798, \"confidence\": 0.88, \"temperature\": 760.0, \"source\": \"Woolsey_Fire_2018\", \"timestamp\": \"2018-11-08T14:24:00Z\"}"

REM Glass Fire (Napa Valley, 2020)
echo Loading Glass Fire data...
curl -X POST %API_URL% ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": 38.5574, \"longitude\": -122.5047, \"confidence\": 0.87, \"temperature\": 740.0, \"source\": \"Glass_Fire_2020\", \"timestamp\": \"2020-09-27T03:50:00Z\"}"

REM August Complex (Mendocino, 2020 - largest fire)
echo Loading August Complex data...
curl -X POST %API_URL% ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": 39.7128, \"longitude\": -122.8414, \"confidence\": 0.93, \"temperature\": 820.0, \"source\": \"August_Complex_2020\", \"timestamp\": \"2020-08-17T08:30:00Z\"}"

REM Creek Fire (Fresno County, 2020)
echo Loading Creek Fire data...
curl -X POST %API_URL% ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": 37.2431, \"longitude\": -119.2681, \"confidence\": 0.90, \"temperature\": 790.0, \"source\": \"Creek_Fire_2020\", \"timestamp\": \"2020-09-04T18:20:00Z\"}"

REM Dixie Fire (Butte County, 2021)
echo Loading Dixie Fire data...
curl -X POST %API_URL% ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": 40.0171, \"longitude\": -121.0186, \"confidence\": 0.94, \"temperature\": 830.0, \"source\": \"Dixie_Fire_2021\", \"timestamp\": \"2021-07-13T17:00:00Z\"}"

REM Caldor Fire (El Dorado County, 2021)
echo Loading Caldor Fire data...
curl -X POST %API_URL% ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": 38.7652, \"longitude\": -120.3458, \"confidence\": 0.86, \"temperature\": 770.0, \"source\": \"Caldor_Fire_2021\", \"timestamp\": \"2021-08-14T19:45:00Z\"}"

echo.
echo Loading additional 2023 fire season data...

REM Generate realistic 2023 data based on typical fire locations
for /L %%i in (1,1,20) do (
    call :GenerateRandomFire %%i
)

echo.
echo ============================================================
echo [CHECK] Historical fire data loading complete!
echo ============================================================

REM Check loaded data
echo.
echo Checking loaded data...
curl -s %API_URL%?limit=5
echo.

echo.
echo [BAR_CHART] To view all loaded data:
echo curl http://localhost:8001/api/v1/fires
echo.
echo [LINE_CHART] To view statistics:
echo curl http://localhost:8001/api/v1/stats
echo.
pause
exit /b 0

:GenerateRandomFire
set /a "lat_base=34 + %RANDOM% %% 8"
set /a "lat_dec=%RANDOM% %% 9999"
set /a "lon_base=117 + %RANDOM% %% 8"
set /a "lon_dec=%RANDOM% %% 9999"
set /a "conf_val=75 + %RANDOM% %% 25"
set /a "temp_val=600 + %RANDOM% %% 400"

curl -X POST %API_URL% ^
  -H "Content-Type: application/json" ^
  -d "{\"latitude\": %lat_base%.%lat_dec%, \"longitude\": -%lon_base%.%lon_dec%, \"confidence\": 0.%conf_val%, \"temperature\": %temp_val%.0, \"source\": \"2023_fire_season\"}" >nul

echo   Fire incident %1 loaded
exit /b 0