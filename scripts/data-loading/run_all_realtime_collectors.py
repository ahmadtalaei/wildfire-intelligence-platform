#!/usr/bin/env python3
"""
Master Real-Time Data Collector
Runs all real-time data collectors in parallel for comprehensive wildfire intelligence.

Collectors:
1. NASA FIRMS Satellite Data Collector (5 min intervals)
2. NOAA Weather Data Collector (10 min intervals)  
3. CAL FIRE Incident Database Collector (5 min intervals)
4. IoT Sensor Network Collector (2 min intervals)
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import List, Dict, Any

# Import all collector classes
try:
    from realtime_satellite_collector import RealTimeSatelliteCollector
    from realtime_weather_collector import RealTimeWeatherCollector
    from realtime_calfire_collector import RealTimeCalFireCollector
    from realtime_iot_collector import RealTimeIoTCollector
except ImportError as e:
    print(f"Error importing collectors: {e}")
    print("Make sure all collector files are in the same directory")
    sys.exit(1)

class MasterDataCollector:
    def __init__(self):
        self.collectors = {}
        self.tasks = []
        self.running = False
        self.stats = {
            'started': datetime.now(),
            'total_uptime': None,
            'collectors_running': 0,
            'total_errors': 0
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown on Ctrl+C"""
        def signal_handler(signum, frame):
            self.logger.info("Received shutdown signal, stopping all collectors...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run_collector_with_monitoring(self, collector_name, collector_instance):
        """Run a collector with error monitoring and restart logic"""
        restart_count = 0
        max_restarts = 5
        
        while self.running and restart_count < max_restarts:
            try:
                self.logger.info(f"Starting {collector_name} collector...")
                await collector_instance.run_continuous()
                
            except Exception as e:
                restart_count += 1
                self.stats['total_errors'] += 1
                self.logger.error(f"Error in {collector_name} collector: {e}")
                
                if restart_count < max_restarts:
                    wait_time = min(60 * restart_count, 300)  # Exponential backoff, max 5 minutes
                    self.logger.info(f"Restarting {collector_name} in {wait_time} seconds (attempt {restart_count}/{max_restarts})...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"{collector_name} collector failed {max_restarts} times, giving up")
                    break
        
        self.logger.info(f"{collector_name} collector stopped")
    
    async def print_master_stats(self):
        """Print combined statistics from all collectors"""
        while self.running:
            await asyncio.sleep(600)  # Print stats every 10 minutes
            
            try:
                uptime = datetime.now() - self.stats['started']
                print(f"\n{'='*80}")
                print(f"[FIRE] WILDFIRE INTELLIGENCE PLATFORM - REAL-TIME DATA COLLECTORS")
                print(f"{'='*80}")
                print(f"⏱️  Master Uptime: {uptime}")
                print(f"[WRENCH] Collectors Running: {len([t for t in self.tasks if not t.done()])}/4")
                print(f"[X] Total Errors: {self.stats['total_errors']}")
                print(f"{'='*80}")
                
                # Print individual collector stats if available
                for name, collector in self.collectors.items():
                    if hasattr(collector, 'stats') and collector.stats:
                        stats = collector.stats
                        print(f"\n[BAR_CHART] {name.upper()} STATS:")
                        
                        if 'new_detections_sent' in stats:
                            # Satellite collector
                            print(f"   [SATELLITE]  Total detections processed: {stats.get('total_detections_processed', 0)}")
                            print(f"   🆕 New detections sent: {stats.get('new_detections_sent', 0)}")
                            print(f"   🔄 Duplicates skipped: {stats.get('duplicate_detections_skipped', 0)}")
                        
                        elif 'new_readings_sent' in stats:
                            # Weather or IoT collector
                            print(f"   [SATELLITE_ANTENNA] Total readings processed: {stats.get('total_readings_processed', 0)}")
                            print(f"   🆕 New readings sent: {stats.get('new_readings_sent', 0)}")
                            
                            if 'total_sensors_monitored' in stats:
                                print(f"   🔌 Sensors monitored: {stats.get('total_sensors_monitored', 0)}")
                        
                        elif 'new_incidents_sent' in stats:
                            # CAL FIRE collector
                            print(f"   [FIRE] Total incidents processed: {stats.get('total_incidents_processed', 0)}")
                            print(f"   🆕 New incidents sent: {stats.get('new_incidents_sent', 0)}")
                            print(f"   🔄 Updated incidents sent: {stats.get('updated_incidents_sent', 0)}")
                        
                        print(f"   [X] API errors: {stats.get('api_errors', 0)}")
                        print(f"   🕐 Last poll: {stats.get('last_successful_poll', 'Never')}")
                
                print(f"\n{'='*80}\n")
                
            except Exception as e:
                self.logger.error(f"Error printing stats: {e}")
    
    async def run_all_collectors(self):
        """Run all data collectors in parallel"""
        self.logger.info("[ROCKET] Starting Wildfire Intelligence Platform Real-Time Data Collection")
        self.logger.info("[SATELLITE_ANTENNA] Initializing all data collectors...")
        
        # Initialize all collectors
        try:
            self.collectors = {
                'nasa_firms': RealTimeSatelliteCollector(),
                'noaa_weather': RealTimeWeatherCollector(),
                'calfire_incidents': RealTimeCalFireCollector(),
                'iot_sensors': RealTimeIoTCollector()
            }
            
            self.logger.info(f"[CHECK] Initialized {len(self.collectors)} collectors")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize collectors: {e}")
            return
        
        # Setup signal handlers for graceful shutdown
        self.setup_signal_handlers()
        self.running = True
        
        # Start all collectors as parallel tasks
        self.tasks = []
        for name, collector in self.collectors.items():
            task = asyncio.create_task(
                self.run_collector_with_monitoring(name, collector)
            )
            self.tasks.append(task)
        
        # Start stats monitoring task
        stats_task = asyncio.create_task(self.print_master_stats())
        self.tasks.append(stats_task)
        
        self.logger.info(f"[FIRE] All collectors started! Monitoring {len(self.collectors)} data sources...")
        self.logger.info("[BAR_CHART] Real-time data flowing to platform:")
        self.logger.info("   [SATELLITE]  NASA FIRMS: Satellite fire detections (5 sources)")
        self.logger.info("   [SUN_CLOUD]  NOAA Weather: Weather stations (10 locations)")
        self.logger.info("   🚨 CAL FIRE: Official incident database")
        self.logger.info("   🔌 IoT Sensors: Sensor networks (4 networks)")
        self.logger.info("\n[BULB] Press Ctrl+C to stop all collectors gracefully")
        
        # Wait for all tasks to complete or be cancelled
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        
        self.running = False
        self.logger.info("🛑 All data collectors stopped")
        
        # Print final summary
        uptime = datetime.now() - self.stats['started']
        print(f"\n{'='*80}")
        print(f"[BAR_CHART] FINAL COLLECTION SUMMARY")
        print(f"{'='*80}")
        print(f"⏱️  Total Runtime: {uptime}")
        print(f"[X] Total Errors: {self.stats['total_errors']}")
        print(f"[WRENCH] Collectors: {len(self.collectors)} initialized")
        print(f"[CHECK] Platform Ready: http://localhost:8001/docs")
        print(f"{'='*80}")

async def main():
    """Main function"""
    print("[FIRE] Wildfire Intelligence Platform - Real-Time Data Collectors")
    print("=" * 80)
    print("Starting comprehensive real-time data collection from:")
    print("  [SATELLITE]  NASA FIRMS Satellite Data")
    print("  [SUN_CLOUD]  NOAA Weather Stations") 
    print("  🚨 CAL FIRE Incident Database")
    print("  🔌 IoT Sensor Networks")
    print("=" * 80)
    
    master_collector = MasterDataCollector()
    await master_collector.run_all_collectors()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"[X] Fatal error: {e}")
        sys.exit(1)