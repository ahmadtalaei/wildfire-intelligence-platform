#!/usr/bin/env python3
"""
Real-Time CAL FIRE Incident Database Collector
Continuously monitors CAL FIRE incident databases and loads data into the platform.

Features:
- Real-time polling every 5 minutes
- JSON and CSV data source support
- Automatic incident tracking and updates
- Error handling and retry logic
- Incident status monitoring (active/inactive)
"""

import asyncio
import aiohttp
import csv
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
import logging
import io

# Import configuration
from config import (
    USER_AGENT, PLATFORM_API_FIRES, CALFIRE_INCIDENTS_POLL_INTERVAL,
    MAX_RETRIES, REQUEST_TIMEOUT
)

# Configuration
CALFIRE_JSON_API = "https://incidents.fire.ca.gov/umbraco/api/IncidentApi/List"
CALFIRE_CSV_API = "https://incidents.fire.ca.gov/imapdata/mapdataall.csv"
CALFIRE_GEOJSON_API = "https://incidents.fire.ca.gov/umbraco/api/IncidentApi/GeoJsonList"

# Polling configuration
POLL_INTERVAL_SECONDS = CALFIRE_INCIDENTS_POLL_INTERVAL
DEDUPE_HOURS = 24  # Track incidents for 24 hours

class RealTimeCalFireCollector:
    def __init__(self):
        self.platform_url = PLATFORM_API_FIRES
        self.seen_incidents: Set[str] = set()
        self.incident_status: Dict[str, dict] = {}  # Track incident changes
        self.stats = {
            'total_incidents_processed': 0,
            'new_incidents_sent': 0,
            'updated_incidents_sent': 0,
            'inactive_incidents_found': 0,
            'api_errors': 0,
            'last_successful_poll': None,
            'polling_started': datetime.now()
        }
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def create_incident_id(self, incident):
        """Create unique ID for incident"""
        # Use official incident ID if available, otherwise create from location/name
        if 'UniqueId' in incident:
            return str(incident['UniqueId'])
        elif 'IncidentName' in incident:
            key = f"{incident.get('IncidentName', '')}_{incident.get('County', '')}"
            return hashlib.md5(key.encode()).hexdigest()[:12]
        else:
            # Fallback to coordinates if available
            lat = incident.get('Latitude', incident.get('lat', 0))
            lon = incident.get('Longitude', incident.get('lon', 0))
            key = f"{lat}_{lon}_{incident.get('Name', 'unknown')}"
            return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def parse_calfire_datetime(self, date_str):
        """Parse CAL FIRE date/time formats"""
        if not date_str:
            return datetime.now().isoformat() + "Z"
        
        try:
            # Handle different CAL FIRE date formats
            if 'T' in date_str:
                # ISO format: 2025-09-11T14:30:00
                if date_str.endswith('Z'):
                    return date_str
                else:
                    return date_str + "Z"
            else:
                # Date only: 2025-09-11
                return date_str + "T12:00:00Z"
        except:
            return datetime.now().isoformat() + "Z"
    
    def normalize_incident_data(self, incident, source_format):
        """Normalize incident data from different CAL FIRE formats"""
        try:
            if source_format == "json":
                # JSON API format
                return {
                    'incident_id': self.create_incident_id(incident),
                    'name': incident.get('Name', 'Unknown Incident'),
                    'latitude': float(incident.get('Latitude', 0)),
                    'longitude': float(incident.get('Longitude', 0)),
                    'acres_burned': float(incident.get('AcresBurned', 0)),
                    'containment_percent': float(incident.get('PercentContained', 0)),
                    'county': incident.get('County', 'Unknown'),
                    'administrative_unit': incident.get('AdminUnit', ''),
                    'started_date': self.parse_calfire_datetime(incident.get('Started')),
                    'updated_date': self.parse_calfire_datetime(incident.get('Updated')),
                    'is_active': not incident.get('IsActive', True) == False,
                    'incident_types': incident.get('IncidentTypeCategory', 'Wildfire'),
                    'injuries': int(incident.get('Injuries', 0)),
                    'fatalities': int(incident.get('Fatalities', 0)),
                    'structures_threatened': int(incident.get('StructuresThreatened', 0)),
                    'structures_damaged': int(incident.get('StructuresDamaged', 0)),
                    'structures_destroyed': int(incident.get('StructuresDestroyed', 0)),
                    'source': 'CAL_FIRE_JSON',
                    'confidence': 0.9,  # High confidence for official CAL FIRE data
                    'temperature': 25.0  # Default temperature
                }
                
            elif source_format == "csv":
                # CSV format
                return {
                    'incident_id': self.create_incident_id(incident),
                    'name': incident.get('incident_name', incident.get('name', 'Unknown Incident')),
                    'latitude': float(incident.get('incident_latitude', incident.get('lat', 0))),
                    'longitude': float(incident.get('incident_longitude', incident.get('lon', 0))),
                    'acres_burned': float(incident.get('incident_acres_burned', incident.get('acres', 0))),
                    'containment_percent': float(incident.get('incident_containment', 0)),
                    'county': incident.get('incident_county', 'Unknown'),
                    'administrative_unit': incident.get('incident_administrative_unit', ''),
                    'started_date': self.parse_calfire_datetime(incident.get('incident_date_created')),
                    'updated_date': self.parse_calfire_datetime(incident.get('incident_date_last_update')),
                    'is_active': incident.get('incident_is_active', 'true').lower() == 'true',
                    'incident_types': 'Wildfire',
                    'source': 'CAL_FIRE_CSV',
                    'confidence': 0.9,
                    'temperature': 25.0
                }
            
            else:
                self.logger.warning(f"Unknown source format: {source_format}")
                return None
                
        except (ValueError, KeyError, TypeError) as e:
            self.logger.warning(f"Error normalizing incident data: {e}")
            return None
    
    async def fetch_json_incidents(self, session):
        """Fetch incidents from CAL FIRE JSON API"""
        headers = {"User-Agent": USER_AGENT}
        
        try:
            # Get active incidents
            active_url = f"{CALFIRE_JSON_API}?inactive=false"
            async with session.get(active_url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    active_data = await response.json()
                    active_incidents = active_data if isinstance(active_data, list) else []
                else:
                    self.logger.error(f"Failed to fetch active incidents: {response.status}")
                    active_incidents = []
            
            # Get inactive incidents (recent)
            inactive_url = f"{CALFIRE_JSON_API}?inactive=true"
            async with session.get(inactive_url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    inactive_data = await response.json()
                    inactive_incidents = inactive_data if isinstance(inactive_data, list) else []
                else:
                    self.logger.error(f"Failed to fetch inactive incidents: {response.status}")
                    inactive_incidents = []
            
            # Combine and normalize
            all_incidents = []
            for incident in active_incidents:
                normalized = self.normalize_incident_data(incident, "json")
                if normalized:
                    normalized['is_active'] = True
                    all_incidents.append(normalized)
            
            for incident in inactive_incidents[:10]:  # Limit recent inactive incidents
                normalized = self.normalize_incident_data(incident, "json")
                if normalized:
                    normalized['is_active'] = False
                    all_incidents.append(normalized)
            
            self.logger.info(f"Fetched {len(active_incidents)} active + {len(inactive_incidents[:10])} recent inactive incidents from JSON API")
            return all_incidents
            
        except Exception as e:
            self.logger.error(f"Error fetching JSON incidents: {e}")
            return []
    
    async def fetch_csv_incidents(self, session):
        """Fetch incidents from CAL FIRE CSV API (backup method)"""
        headers = {"User-Agent": USER_AGENT}
        
        try:
            async with session.get(CALFIRE_CSV_API, headers=headers, timeout=30) as response:
                if response.status == 200:
                    csv_text = await response.text()
                    
                    incidents = []
                    csv_reader = csv.DictReader(io.StringIO(csv_text))
                    
                    for row in csv_reader:
                        normalized = self.normalize_incident_data(row, "csv")
                        if normalized:
                            incidents.append(normalized)
                    
                    self.logger.info(f"Fetched {len(incidents)} incidents from CSV API")
                    return incidents
                else:
                    self.logger.error(f"CSV API error: {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error fetching CSV incidents: {e}")
            return []
    
    async def send_to_platform(self, incident, session):
        """Send incident to platform"""
        try:
            # Format for platform API
            platform_data = {
                "latitude": incident['latitude'],
                "longitude": incident['longitude'],
                "confidence": incident['confidence'],
                "temperature": incident['temperature'],
                "source": incident['source'],
                "timestamp": incident['started_date'],
                "incident_name": incident['name'],
                "acres_burned": incident['acres_burned'],
                "containment_percent": incident['containment_percent'],
                "county": incident['county'],
                "is_active": incident['is_active']
            }
            
            async with session.post(self.platform_url, json=platform_data, timeout=10) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('incident_id')
                else:
                    error_text = await response.text()
                    self.logger.error(f"Platform API error: {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error sending to platform: {e}")
            return None
    
    async def process_incidents(self, all_incidents):
        """Process and track incident changes"""
        new_incidents = []
        updated_incidents = []
        
        for incident in all_incidents:
            incident_id = incident['incident_id']
            
            if incident_id not in self.seen_incidents:
                new_incidents.append(incident)
                self.seen_incidents.add(incident_id)
                self.incident_status[incident_id] = incident
            else:
                # Check if incident has been updated
                previous_incident = self.incident_status.get(incident_id, {})
                
                # Check for significant changes
                significant_change = False
                if abs(incident.get('acres_burned', 0) - previous_incident.get('acres_burned', 0)) > 10:
                    significant_change = True
                if abs(incident.get('containment_percent', 0) - previous_incident.get('containment_percent', 0)) > 5:
                    significant_change = True
                if incident.get('is_active') != previous_incident.get('is_active'):
                    significant_change = True
                
                if significant_change:
                    updated_incidents.append(incident)
                    self.incident_status[incident_id] = incident
        
        # Track inactive incidents
        inactive_count = sum(1 for inc in all_incidents if not inc.get('is_active', True))
        self.stats['inactive_incidents_found'] = inactive_count
        
        self.logger.info(f"Found {len(new_incidents)} new incidents, {len(updated_incidents)} updated incidents")
        return new_incidents, updated_incidents
    
    async def poll_calfire_incidents(self):
        """Poll CAL FIRE for current incidents"""
        self.logger.info("Starting CAL FIRE incident polling cycle...")
        
        async with aiohttp.ClientSession() as session:
            # Try JSON API first (primary)
            incidents = await self.fetch_json_incidents(session)
            
            # If JSON fails, try CSV backup
            if not incidents:
                self.logger.info("JSON API failed, trying CSV backup...")
                incidents = await self.fetch_csv_incidents(session)
            
            if not incidents:
                self.logger.warning("No incident data retrieved from any source")
                self.stats['api_errors'] += 1
                return
            
            self.stats['total_incidents_processed'] += len(incidents)
            
            # Process incidents for changes
            new_incidents, updated_incidents = await self.process_incidents(incidents)
            
            # Send new incidents to platform
            for incident in new_incidents:
                platform_id = await self.send_to_platform(incident, session)
                if platform_id:
                    self.stats['new_incidents_sent'] += 1
                    acres = incident.get('acres_burned', 0)
                    containment = incident.get('containment_percent', 0)
                    status = "ACTIVE" if incident.get('is_active') else "INACTIVE"
                    self.logger.info(f"NEW: {incident['name']} ({acres} acres, {containment}% contained, {status}) -> {platform_id}")
            
            # Send updated incidents to platform
            for incident in updated_incidents:
                platform_id = await self.send_to_platform(incident, session)
                if platform_id:
                    self.stats['updated_incidents_sent'] += 1
                    acres = incident.get('acres_burned', 0)
                    containment = incident.get('containment_percent', 0)
                    status = "ACTIVE" if incident.get('is_active') else "INACTIVE"
                    self.logger.info(f"UPDATE: {incident['name']} ({acres} acres, {containment}% contained, {status}) -> {platform_id}")
            
            self.stats['last_successful_poll'] = datetime.now()
    
    def cleanup_old_incidents(self):
        """Remove old incident tracking data"""
        if len(self.incident_status) > 500:  # Arbitrary limit
            # Keep most recent 250 incidents
            sorted_incidents = sorted(
                self.incident_status.items(), 
                key=lambda x: x[1].get('updated_date', ''), 
                reverse=True
            )
            
            old_size = len(self.incident_status)
            self.incident_status = dict(sorted_incidents[:250])
            
            # Update seen incidents set
            self.seen_incidents = set(self.incident_status.keys())
            
            self.logger.info(f"Cleaned up incident cache: {old_size} -> {len(self.incident_status)}")
    
    def print_stats(self):
        """Print current statistics"""
        runtime = datetime.now() - self.stats['polling_started']
        print(f"\n{'='*60}")
        print(f"CAL FIRE Real-Time Incident Collector Stats")
        print(f"{'='*60}")
        print(f"Runtime: {runtime}")
        print(f"Total incidents processed: {self.stats['total_incidents_processed']}")
        print(f"New incidents sent: {self.stats['new_incidents_sent']}")
        print(f"Updated incidents sent: {self.stats['updated_incidents_sent']}")
        print(f"Inactive incidents tracked: {self.stats['inactive_incidents_found']}")
        print(f"API errors: {self.stats['api_errors']}")
        print(f"Last successful poll: {self.stats['last_successful_poll']}")
        print(f"Incident cache size: {len(self.incident_status)}")
        print(f"{'='*60}\n")
    
    async def run_continuous(self):
        """Run continuous CAL FIRE incident monitoring"""
        self.logger.info(f"Starting Real-Time CAL FIRE Incident Collector")
        self.logger.info(f"JSON API: {CALFIRE_JSON_API}")
        self.logger.info(f"CSV API: {CALFIRE_CSV_API}")
        self.logger.info(f"Platform: {self.platform_url}")
        self.logger.info(f"Poll Interval: {POLL_INTERVAL_SECONDS} seconds")
        
        poll_count = 0
        while True:
            try:
                poll_count += 1
                self.logger.info(f"\n--- CAL FIRE Polling Cycle #{poll_count} ---")
                
                await self.poll_calfire_incidents()
                
                # Print stats every 12 polls or on first poll
                if poll_count == 1 or poll_count % 12 == 0:
                    self.print_stats()
                
                # Cleanup old incidents periodically
                if poll_count % 48 == 0:
                    self.cleanup_old_incidents()
                
                # Wait for next poll
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                
            except KeyboardInterrupt:
                self.logger.info("Stopping CAL FIRE incident collector...")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in polling cycle: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

async def main():
    """Main function"""
    collector = RealTimeCalFireCollector()
    await collector.run_continuous()

if __name__ == "__main__":
    print("CAL FIRE Real-Time Incident Database Collector")
    print("Press Ctrl+C to stop")
    asyncio.run(main())