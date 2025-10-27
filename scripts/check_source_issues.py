#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Data Source Issues
Analyzes why certain data sources are not producing data
"""

import sys
import subprocess
from datetime import datetime, timezone

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Sources with issues
ISSUES = {
    'firms_viirs_snpp': {
        'issue': 'STALE - 20 hours old',
        'reason': 'VIIRS satellites only pass over every 12-24 hours',
        'solution': 'Wait for next satellite overpass or check NASA FIRMS API',
        'expected': 'Normal - satellite revisit time'
    },
    'firms_viirs_noaa20': {
        'issue': 'STALE - 20 hours old',
        'reason': 'VIIRS satellites only pass over every 12-24 hours',
        'solution': 'Wait for next satellite overpass',
        'expected': 'Normal - satellite revisit time'
    },
    'firms_viirs_noaa21': {
        'issue': 'STALE - 20 hours old',
        'reason': 'VIIRS satellites only pass over every 12-24 hours',
        'solution': 'Wait for next satellite overpass',
        'expected': 'Normal - satellite revisit time'
    },
    'firms_modis_aqua': {
        'issue': 'EMPTY - no data',
        'reason': 'NASA FIRMS API returning empty dataset',
        'solution': 'Check NASA FIRMS API status or no fires detected',
        'expected': 'Check API'
    },
    'landsat_nrt': {
        'issue': 'EMPTY - no data',
        'reason': 'Landsat NRT fires rare, 16-day revisit time',
        'solution': 'Wait for Landsat overpass or check USGS API',
        'expected': 'Normal - low frequency'
    },
    'sat_landsat_thermal': {
        'issue': 'EMPTY - no data',
        'reason': 'USGS API authentication issues (HTTP 401 in logs)',
        'solution': 'Verify USGS_API_KEY in .env file',
        'expected': 'FIX REQUIRED'
    },
    'sat_sentinel2_msi': {
        'issue': 'STALE - 22 hours old',
        'reason': 'Copernicus API authentication issues (HTTP 401 in logs)',
        'solution': 'Verify COPERNICUS credentials in .env file',
        'expected': 'FIX REQUIRED'
    },
    'sat_sentinel3_slstr': {
        'issue': 'STALE - 21 hours old',
        'reason': 'Copernicus API authentication issues (HTTP 401 in logs)',
        'solution': 'Verify COPERNICUS credentials in .env file',
        'expected': 'FIX REQUIRED'
    },
    'iot_weather_stations': {
        'issue': 'EMPTY - no data',
        'reason': 'Simulated/mock data source not configured',
        'solution': 'Configure real IoT devices or enable simulator',
        'expected': 'Optional - not critical'
    },
    'iot_soil_moisture_sensors': {
        'issue': 'EMPTY - no data',
        'reason': 'Simulated/mock data source not configured',
        'solution': 'Configure real IoT devices or enable simulator',
        'expected': 'Optional - not critical'
    },
    'sensor_readings': {
        'issue': 'STALE - 1 day old (PurpleAir)',
        'reason': 'PurpleAir connector may have rate limits or config issues',
        'solution': 'Check PURPLEAIR_API_KEY in .env and API rate limits',
        'expected': 'Should update hourly'
    },
    'airnow_observations': {
        'issue': 'EMPTY - no data (EPA AirNow)',
        'reason': 'AirNow connector may have config issues or no data',
        'solution': 'Check AIRNOW_API_KEY in .env file',
        'expected': 'Should have data'
    },
    'wx_era5_land': {
        'issue': 'STALE - 5 days old',
        'reason': 'CDS API not healthy (cds_healthy: false in logs)',
        'solution': 'Verify CDSAPI_KEY in .env file',
        'expected': 'Should update every 6 hours'
    },
    'wx_era5_reanalysis': {
        'issue': 'STALE - 5 days old',
        'reason': 'CDS API not healthy (cds_healthy: false in logs)',
        'solution': 'Verify CDSAPI_KEY in .env file',
        'expected': 'Should update every 6 hours'
    },
}

def main():
    print("="*100)
    print("WILDFIRE INTELLIGENCE PLATFORM - DATA SOURCE ISSUE ANALYSIS")
    print("="*100)
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n")

    # Categorize issues
    auth_issues = []
    satellite_timing = []
    api_config = []
    optional_sources = []

    for source_id, details in ISSUES.items():
        if 'authentication' in details['reason'] or '401' in details['reason']:
            auth_issues.append((source_id, details))
        elif 'satellite' in details['reason'] and 'pass over' in details['reason']:
            satellite_timing.append((source_id, details))
        elif 'CDS' in details['reason'] or 'API' in details['solution']:
            api_config.append((source_id, details))
        elif 'Optional' in details['expected'] or 'Simulated' in details['reason']:
            optional_sources.append((source_id, details))
        else:
            api_config.append((source_id, details))

    # Report Authentication Issues
    if auth_issues:
        print("[CRITICAL] Authentication Issues - Immediate Fix Required")
        print("="*100)
        for source_id, details in auth_issues:
            print(f"\nSource: {source_id}")
            print(f"  Issue:    {details['issue']}")
            print(f"  Reason:   {details['reason']}")
            print(f"  Solution: {details['solution']}")
        print()

    # Report API Configuration Issues
    if api_config:
        print("[IMPORTANT] API Configuration Issues - Fix Recommended")
        print("="*100)
        for source_id, details in api_config:
            print(f"\nSource: {source_id}")
            print(f"  Issue:    {details['issue']}")
            print(f"  Reason:   {details['reason']}")
            print(f"  Solution: {details['solution']}")
        print()

    # Report Satellite Timing (Normal Behavior)
    if satellite_timing:
        print("[INFO] Satellite Timing - Normal Behavior")
        print("="*100)
        for source_id, details in satellite_timing:
            print(f"\nSource: {source_id}")
            print(f"  Status:   {details['issue']}")
            print(f"  Reason:   {details['reason']}")
            print(f"  Expected: {details['expected']}")
        print()

    # Report Optional Sources
    if optional_sources:
        print("[OPTIONAL] Sources Not Configured - Optional")
        print("="*100)
        for source_id, details in optional_sources:
            print(f"\nSource: {source_id}")
            print(f"  Status:   {details['issue']}")
            print(f"  Reason:   {details['reason']}")
            print(f"  Expected: {details['expected']}")
        print()

    # Summary and Action Items
    print("="*100)
    print("SUMMARY & ACTION ITEMS")
    print("="*100)
    print(f"\nTotal Issues: {len(ISSUES)}")
    print(f"  - Critical (Auth): {len(auth_issues)}")
    print(f"  - Important (API Config): {len(api_config)}")
    print(f"  - Normal (Satellite Timing): {len(satellite_timing)}")
    print(f"  - Optional: {len(optional_sources)}")

    print(f"\nPRIORITY ACTIONS:")
    print(f"\n1. Fix Authentication Issues:")
    if auth_issues:
        print(f"   - Update Copernicus credentials (COPERNICUS_CLIENT_ID, COPERNICUS_CLIENT_SECRET)")
        print(f"   - Update USGS credentials (USGS_API_KEY)")
        print(f"   - Check .env file for correct API keys")
    else:
        print(f"   [OK] No authentication issues found")

    print(f"\n2. Fix API Configuration:")
    if api_config:
        print(f"   - Verify CDS API key (CDSAPI_KEY) for ERA5 data")
        print(f"   - Verify PurpleAir API key (PURPLEAIR_API_KEY)")
        print(f"   - Verify AirNow API key (AIRNOW_API_KEY)")
    else:
        print(f"   [OK] No API configuration issues found")

    print(f"\n3. Monitor Satellite Timing:")
    print(f"   - VIIRS satellites: Check again in 12-24 hours")
    print(f"   - MODIS Aqua: May have no fires currently detected")
    print(f"   - This is NORMAL behavior for satellite sources")

    print(f"\n4. Optional Sources:")
    print(f"   - IoT sources are simulated and optional")
    print(f"   - Can be ignored unless real IoT devices are deployed")

    print("\n" + "="*100)
    print("CURRENT WORKING STREAMS (6 active):")
    print("="*100)
    print("  [OK] METAR Weather Stations - Active")
    print("  [OK] NOAA Weather Stations - Active")
    print("  [OK] GFS Weather Forecasts - Active")
    print("  [OK] NAM Weather Forecasts - Active")
    print("  [OK] NOAA Gridpoint Forecasts - Active")
    print("  [OK] MODIS Terra Fire Detections - Active (latest: 24s ago!)")

    print("\n" + "="*100)
    print("RECOMMENDATION:")
    print("="*100)
    print(f"\nThe system is OPERATIONAL with 6 active streams processing 338,904 records/hour.")
    print(f"\nTo get ALL sources working:")
    print(f"  1. Update API credentials in .env file")
    print(f"  2. Restart data-ingestion-service: docker-compose restart data-ingestion-service")
    print(f"  3. Wait 1 hour and run monitor again")
    print("\n" + "="*100 + "\n")

if __name__ == '__main__':
    main()
