#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Collection Status Checker
Quick status check for all wildfire data collection components
"""

import requests
import psutil
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Fix Windows console encoding issues
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):  
        sys.stderr.reconfigure(encoding='utf-8')

def check_platform_health():
    """Check if the main platform is running"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def check_grafana_health():
    """Check if Grafana monitoring is running"""
    try:
        response = requests.get("http://localhost:3010/api/health", timeout=5)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def check_database_data():
    """Check recent data in database"""
    try:
        # Check platform stats
        response = requests.get("http://localhost:8001/api/v1/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            return True, stats
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def check_running_processes():
    """Check for data collection processes"""
    collectors = {
        'satellite': 'realtime_satellite_collector.py',
        'weather': 'realtime_weather_collector.py', 
        'calfire': 'realtime_calfire_collector.py',
        'iot': 'realtime_iot_collector.py',
        'auto_manager': 'auto_start_all_collectors.py',
        'continuous_data': 'continuous_live_data.py'
    }
    
    running = {}
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            for collector_name, script_name in collectors.items():
                if script_name in cmdline and 'python' in cmdline.lower():
                    running[collector_name] = {
                        'pid': proc.info['pid'],
                        'script': script_name,
                        'cpu_percent': proc.cpu_percent(),
                        'memory_mb': proc.memory_info().rss / 1024 / 1024
                    }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return running

def format_datetime(dt_str):
    """Format datetime string for display"""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo)
        diff = now - dt
        
        if diff.total_seconds() < 60:
            return f"{int(diff.total_seconds())}s ago"
        elif diff.total_seconds() < 3600:
            return f"{int(diff.total_seconds() / 60)}m ago"
        else:
            return f"{int(diff.total_seconds() / 3600)}h ago"
    except:
        return dt_str

def main():
    """Main status check"""
    print("\n" + "=" * 70)
    print("[FIRE] WILDFIRE INTELLIGENCE PLATFORM - STATUS CHECK")
    print("=" * 70)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check main platform
    print("[DESKTOP]  CORE PLATFORM")
    print("-" * 50)
    platform_ok, platform_info = check_platform_health()
    if platform_ok:
        print("[CHECK] Platform API: RUNNING")
        if isinstance(platform_info, dict):
            version = platform_info.get('version', 'Unknown')
            print(f"   Version: {version}")
    else:
        print("[X] Platform API: OFFLINE")
        print(f"   Error: {platform_info}")
    print()
    
    # Check Grafana
    print("[BAR_CHART] MONITORING DASHBOARD")
    print("-" * 50) 
    grafana_ok, grafana_info = check_grafana_health()
    if grafana_ok:
        print("[CHECK] Grafana: RUNNING")
        print("   URL: http://localhost:3010")
        if isinstance(grafana_info, dict):
            version = grafana_info.get('version', 'Unknown')
            print(f"   Version: {version}")
    else:
        print("[X] Grafana: OFFLINE")
        print(f"   Error: {grafana_info}")
    print()
    
    # Check data freshness
    print("[LINE_CHART] DATA STATUS")
    print("-" * 50)
    data_ok, data_info = check_database_data()
    if data_ok and isinstance(data_info, dict):
        print("[CHECK] Database: CONNECTED")
        
        # Show data counts
        if 'fire_incidents' in data_info:
            fire_count = data_info['fire_incidents']
            print(f"   [FIRE] Fire Incidents: {fire_count}")
            
        if 'weather_readings' in data_info:
            weather_count = data_info['weather_readings'] 
            print(f"   [SUN_CLOUD] Weather Readings: {weather_count}")
            
        if 'sensor_readings' in data_info:
            sensor_count = data_info['sensor_readings']
            print(f"   [SATELLITE_ANTENNA] Sensor Readings: {sensor_count}")
        
        # Show last update times
        if 'last_updated' in data_info:
            last_update = format_datetime(data_info['last_updated'])
            print(f"   ⏱️ Last Update: {last_update}")
            
    else:
        print("[X] Database: OFFLINE or NO DATA")
        if data_info:
            print(f"   Error: {data_info}")
    print()
    
    # Check running collectors
    print("[ROBOT] DATA COLLECTORS")
    print("-" * 50)
    running_procs = check_running_processes()
    
    expected_collectors = {
        'satellite': '[SATELLITE] NASA FIRMS Satellite',
        'weather': '[SUN_CLOUD] NOAA Weather', 
        'calfire': '[FIRE] CAL FIRE Incidents',
        'iot': '[SATELLITE_ANTENNA] IoT Sensors',
        'auto_manager': '[DART] Auto Manager',
        'continuous_data': '🔄 Live Data Generator'
    }
    
    active_count = 0
    for collector_name, description in expected_collectors.items():
        if collector_name in running_procs:
            proc_info = running_procs[collector_name]
            print(f"[CHECK] {description}: RUNNING")
            print(f"   PID: {proc_info['pid']}, CPU: {proc_info['cpu_percent']:.1f}%, Memory: {proc_info['memory_mb']:.0f}MB")
            active_count += 1
        else:
            print(f"[X] {description}: STOPPED")
    
    print(f"\n[BAR_CHART] Summary: {active_count}/{len(expected_collectors)} collectors running")
    print()
    
    # Overall status
    print("[DART] OVERALL STATUS")
    print("-" * 50)
    
    issues = []
    if not platform_ok:
        issues.append("Platform API offline")
    if not grafana_ok:
        issues.append("Grafana monitoring offline") 
    if not data_ok:
        issues.append("Database connection issues")
    if active_count == 0:
        issues.append("No data collectors running")
    elif active_count < 3:
        issues.append("Some data collectors offline")
        
    if not issues:
        print("[CHECK] ALL SYSTEMS OPERATIONAL")
        print("[PARTY] Your wildfire intelligence platform is running perfectly!")
        print()
        print("🔗 Quick Links:")
        print("   [BAR_CHART] Grafana Dashboard: http://localhost:3010")
        print("   [WRENCH] Platform API: http://localhost:8001/docs") 
        print("   [LINE_CHART] Data Stats: http://localhost:8001/api/v1/stats")
    else:
        print("[WARNING] ISSUES DETECTED:")
        for issue in issues:
            print(f"   * {issue}")
        print()
        print("[WRENCH] Troubleshooting:")
        if not platform_ok:
            print("   * Start platform: docker-compose up -d")
        if active_count == 0:
            print("   * Start collectors: python auto_start_data_collection.bat")
        if not grafana_ok:
            print("   * Restart Grafana: docker-compose restart grafana")
    
    print("\n" + "=" * 70)
    
    # Return exit code for automation
    return 0 if not issues else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Status check cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] Status check error: {e}")
        sys.exit(1)