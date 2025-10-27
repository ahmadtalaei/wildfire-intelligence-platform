#!/usr/bin/env python3
"""
Auto-Start All Data Collectors
Automatically starts and manages all real-time data collection processes
"""

import asyncio
import subprocess
import psutil
import time
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
COLLECTORS = {
    'satellite': {
        'script': 'realtime_satellite_collector.py',
        'description': 'NASA FIRMS Satellite Fire Detection',
        'priority': 1,
        'restart_on_fail': True
    },
    'weather': {
        'script': 'realtime_weather_collector.py', 
        'description': 'NOAA Weather Data Collection',
        'priority': 2,
        'restart_on_fail': True
    },
    'calfire': {
        'script': 'realtime_calfire_collector.py',
        'description': 'CAL FIRE Incident Tracking',
        'priority': 3,
        'restart_on_fail': True
    },
    'iot': {
        'script': 'realtime_iot_collector.py',
        'description': 'IoT Sensor Network Monitoring',
        'priority': 4,
        'restart_on_fail': True
    }
}

HEALTH_CHECK_INTERVAL = 300  # 5 minutes
MAX_RESTART_ATTEMPTS = 3
RESTART_DELAY = 60  # 1 minute between restarts

class CollectorManager:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_health_check = {}
        self.script_dir = Path(__file__).parent.absolute()
        
    def start_collector(self, name: str, config: dict) -> bool:
        """Start a single data collector"""
        try:
            script_path = self.script_dir / config['script']
            if not script_path.exists():
                logger.error(f"Script not found: {script_path}")
                return False
                
            logger.info(f"[ROCKET] Starting {config['description']}...")
            
            # Start process
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.script_dir),
                text=True
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            if process.poll() is None:  # Process is running
                self.processes[name] = process
                self.restart_counts[name] = 0
                logger.info(f"[CHECK] {config['description']} started (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"[X] {config['description']} failed to start:")
                logger.error(f"   STDOUT: {stdout[:200]}...")
                logger.error(f"   STDERR: {stderr[:200]}...")
                return False
                
        except Exception as e:
            logger.error(f"[X] Error starting {name}: {e}")
            return False
    
    def stop_collector(self, name: str) -> bool:
        """Stop a data collector"""
        if name in self.processes:
            process = self.processes[name]
            try:
                logger.info(f"🛑 Stopping {name}...")
                process.terminate()
                
                # Wait up to 10 seconds for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"[WARNING] Force killing {name}...")
                    process.kill()
                    process.wait()
                
                del self.processes[name]
                logger.info(f"[CHECK] {name} stopped")
                return True
                
            except Exception as e:
                logger.error(f"[X] Error stopping {name}: {e}")
                return False
        return True
    
    def check_collector_health(self, name: str, config: dict) -> bool:
        """Check if a collector is healthy"""
        if name not in self.processes:
            return False
            
        process = self.processes[name]
        
        # Check if process is still running
        if process.poll() is not None:
            logger.warning(f"[WARNING] {config['description']} process has died (exit code: {process.returncode})")
            return False
            
        # Check CPU/memory usage
        try:
            proc_info = psutil.Process(process.pid)
            cpu_percent = proc_info.cpu_percent()
            memory_mb = proc_info.memory_info().rss / 1024 / 1024
            
            # Log health status every 30 minutes
            now = datetime.now()
            last_log = self.last_health_check.get(name, datetime.min)
            if (now - last_log).total_seconds() > 1800:  # 30 minutes
                logger.info(f"💓 {config['description']} healthy - CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.0f}MB")
                self.last_health_check[name] = now
            
            # Alert if resource usage is too high
            if cpu_percent > 50:
                logger.warning(f"[WARNING] {config['description']} high CPU usage: {cpu_percent:.1f}%")
            if memory_mb > 500:
                logger.warning(f"[WARNING] {config['description']} high memory usage: {memory_mb:.0f}MB")
                
            return True
            
        except psutil.NoSuchProcess:
            logger.warning(f"[WARNING] {config['description']} process not found")
            return False
        except Exception as e:
            logger.error(f"[X] Error checking {name} health: {e}")
            return True  # Don't restart on health check errors
    
    def restart_collector(self, name: str, config: dict) -> bool:
        """Restart a failed collector"""
        if self.restart_counts.get(name, 0) >= MAX_RESTART_ATTEMPTS:
            logger.error(f"[X] {config['description']} exceeded max restart attempts ({MAX_RESTART_ATTEMPTS})")
            return False
            
        logger.warning(f"🔄 Restarting {config['description']}...")
        self.restart_counts[name] = self.restart_counts.get(name, 0) + 1
        
        # Stop if running
        self.stop_collector(name)
        
        # Wait before restarting
        logger.info(f"⏳ Waiting {RESTART_DELAY}s before restart...")
        time.sleep(RESTART_DELAY)
        
        # Start again
        return self.start_collector(name, config)
    
    def start_all_collectors(self):
        """Start all data collectors"""
        logger.info("[ROCKET] Starting Wildfire Intelligence Data Collection System...")
        logger.info(f"📁 Working directory: {self.script_dir}")
        
        # Start collectors in priority order
        sorted_collectors = sorted(COLLECTORS.items(), key=lambda x: x[1]['priority'])
        
        success_count = 0
        for name, config in sorted_collectors:
            if self.start_collector(name, config):
                success_count += 1
                time.sleep(5)  # Stagger starts
        
        logger.info(f"[CHECK] Started {success_count}/{len(COLLECTORS)} collectors")
        
        if success_count == 0:
            logger.error("[X] No collectors started successfully!")
            return False
            
        return True
    
    def monitor_collectors(self):
        """Monitor and restart failed collectors"""
        logger.info("👀 Starting collector monitoring...")
        
        while True:
            try:
                logger.debug(f"[MAGNIFYING_GLASS] Health check at {datetime.now().strftime('%H:%M:%S')}")
                
                for name, config in COLLECTORS.items():
                    if not self.check_collector_health(name, config):
                        if config.get('restart_on_fail', True):
                            logger.warning(f"🚨 {config['description']} unhealthy, attempting restart...")
                            self.restart_collector(name, config)
                        else:
                            logger.warning(f"[WARNING] {config['description']} unhealthy but restart disabled")
                
                # Sleep until next health check
                time.sleep(HEALTH_CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"[X] Monitoring error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def stop_all_collectors(self):
        """Stop all running collectors"""
        logger.info("🛑 Stopping all collectors...")
        
        for name in list(self.processes.keys()):
            self.stop_collector(name)
        
        logger.info("[CHECK] All collectors stopped")
    
    def status_report(self):
        """Print current status of all collectors"""
        print(f"\n{'='*60}")
        print(f"[FIRE] Wildfire Data Collection System Status")
        print(f"{'='*60}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Collectors: {len(COLLECTORS)} configured")
        print(f"Running: {len(self.processes)}")
        print()
        
        for name, config in COLLECTORS.items():
            if name in self.processes:
                process = self.processes[name]
                try:
                    proc_info = psutil.Process(process.pid)
                    cpu = proc_info.cpu_percent()
                    mem_mb = proc_info.memory_info().rss / 1024 / 1024
                    status = f"[CHECK] RUNNING (PID: {process.pid}, CPU: {cpu:.1f}%, Mem: {mem_mb:.0f}MB)"
                except:
                    status = f"[CHECK] RUNNING (PID: {process.pid})"
            else:
                status = "[X] STOPPED"
                
            restarts = self.restart_counts.get(name, 0)
            restart_info = f" | Restarts: {restarts}" if restarts > 0 else ""
            
            print(f"{name.ljust(15)}: {status}{restart_info}")
            print(f"{''.ljust(15)}  {config['description']}")
            print()
        
        print(f"{'='*60}\n")

async def main():
    """Main function"""
    manager = CollectorManager()
    
    try:
        # Start all collectors
        if not manager.start_all_collectors():
            logger.error("[X] Failed to start collectors")
            return
        
        # Show initial status
        manager.status_report()
        
        # Start monitoring
        logger.info("[DART] Data collection system is now running!")
        logger.info("[BAR_CHART] Check Grafana dashboard: http://localhost:3010")
        logger.info("[WRENCH] Press Ctrl+C to stop all collectors")
        
        # Monitor collectors
        manager.monitor_collectors()
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutdown requested...")
    finally:
        manager.stop_all_collectors()
        logger.info("[CHECK] Data collection system stopped")

if __name__ == "__main__":
    print("[FIRE] Wildfire Intelligence - Auto Data Collection Manager")
    print("=" * 60)
    asyncio.run(main())