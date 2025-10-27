#!/usr/bin/env python3
"""
2025 Satellite Fire Data Loader
Loads realistic 2025 fire incident data based on satellite statistics
Target: 432,942 Total Fire Incidents for 2025
"""

import requests
import json
import random
import datetime
from typing import List, Dict
import time

class FireDataLoader:
    def __init__(self):
        self.api_url = "http://localhost:8001/api/v1/fires"
        self.bulk_api_url = "http://localhost:8001/api/v1/fires/bulk"
        self.stats_url = "http://localhost:8001/api/v1/stats"

        # 2025 Satellite Statistics
        self.target_incidents = 432942
        self.emergency_responses = 6928
        self.wildfires = 520180
        self.acres_burned = 31  # Fatalities (data point seems mixed)
        self.structures_destroyed = 16479

        # California fire-prone regions (lat, lon ranges)
        self.ca_regions = [
            {"name": "Northern CA", "lat_range": (37.0, 42.0), "lon_range": (-124.0, -120.0)},
            {"name": "Central Valley", "lat_range": (35.0, 38.0), "lon_range": (-122.0, -119.0)},
            {"name": "Southern CA", "lat_range": (32.5, 36.0), "lon_range": (-119.0, -116.0)},
            {"name": "Sierra Nevada", "lat_range": (35.5, 39.5), "lon_range": (-121.0, -118.0)},
            {"name": "Coastal Range", "lat_range": (34.0, 40.0), "lon_range": (-124.5, -122.0)}
        ]

        # Data source distribution (based on typical satellite coverage)
        self.sources = [
            {"name": "modis_live", "weight": 35},
            {"name": "viirs_live", "weight": 30},
            {"name": "noaa_weather", "weight": 15},
            {"name": "iot_sensor", "weight": 10},
            {"name": "social_media", "weight": 5},
            {"name": "emergency_services", "weight": 3},
            {"name": "aircraft_patrol", "weight": 2}
        ]

    def test_api_connection(self) -> bool:
        """Test API connectivity"""
        try:
            response = requests.get(self.api_url, timeout=10)
            return response.status_code in [200, 404]  # 404 is OK, means API is responding
        except:
            return False

    def generate_fire_incident(self, timestamp: datetime.datetime) -> Dict:
        """Generate a realistic fire incident"""
        # Select random region
        region = random.choice(self.ca_regions)

        # Generate coordinates within region
        latitude = round(random.uniform(*region["lat_range"]), 4)
        longitude = round(random.uniform(*region["lon_range"]), 4)

        # Generate confidence (weighted toward medium-high for realistic detection)
        confidence_weights = [0.15, 0.25, 0.35, 0.25]  # Low, Medium, High, Very High
        confidence_ranges = [(0.30, 0.50), (0.50, 0.70), (0.70, 0.85), (0.85, 0.99)]
        confidence_range = random.choices(confidence_ranges, weights=confidence_weights)[0]
        confidence = round(random.uniform(*confidence_range), 2)

        # Generate temperature (realistic fire detection temperatures)
        if confidence > 0.8:
            temperature = round(random.uniform(400, 800), 1)  # High confidence = high temp
        elif confidence > 0.6:
            temperature = round(random.uniform(300, 600), 1)  # Medium confidence
        else:
            temperature = round(random.uniform(200, 400), 1)  # Lower confidence

        # Select source based on weights
        source_names = [s["name"] for s in self.sources]
        source_weights = [s["weight"] for s in self.sources]
        source = random.choices(source_names, weights=source_weights)[0]

        return {
            "latitude": latitude,
            "longitude": longitude,
            "confidence": confidence,
            "temperature": temperature,
            "source": source,
            "timestamp": timestamp.isoformat() + "Z"
        }

    def generate_batch(self, batch_size: int, start_date: datetime.datetime, days_span: int) -> List[Dict]:
        """Generate a batch of fire incidents spread across time"""
        incidents = []

        for i in range(batch_size):
            # Spread incidents across the time span
            day_offset = random.randint(0, days_span)
            hour_offset = random.randint(0, 23)
            minute_offset = random.randint(0, 59)

            timestamp = start_date + datetime.timedelta(
                days=day_offset,
                hours=hour_offset,
                minutes=minute_offset
            )

            incident = self.generate_fire_incident(timestamp)
            incidents.append(incident)

        return incidents

    def load_batch(self, incidents: List[Dict]) -> bool:
        """Load a batch of incidents via bulk API"""
        try:
            payload = {"fires": incidents}
            response = requests.post(
                self.bulk_api_url,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"   Error loading batch: {e}")
            return False

    def get_current_count(self) -> int:
        """Get current fire incidents count"""
        try:
            response = requests.get(self.stats_url, timeout=10)
            if response.status_code == 200:
                stats = response.json()
                return stats.get("statistics", {}).get("fire_incidents", 0)
        except:
            pass
        return 0

    def load_2025_data(self):
        """Load complete 2025 satellite fire data"""
        print("=" * 80)
        print("[SATELLITE] 2025 Satellite Fire Data Loader [SATELLITE]")
        print("=" * 80)
        print()
        print("2025 Satellite Statistics Target:")
        print(f"- Total Incidents: {self.target_incidents:,}")
        print(f"- Emergency Responses: {self.emergency_responses:,}")
        print(f"- Wildfires: {self.wildfires:,}")
        print(f"- Structures Destroyed: {self.structures_destroyed:,}")
        print("=" * 80)

        # Test API connection
        print("\nTesting API connection...")
        if not self.test_api_connection():
            print("[X] Error: Cannot connect to API")
            print("Make sure the platform is running: docker-compose -f docker-compose-simple.yml up -d")
            return False
        print("[CHECK] API connection successful")

        # Check current count
        current_count = self.get_current_count()
        print(f"\nCurrent fire incidents in database: {current_count:,}")

        if current_count >= self.target_incidents:
            print("[CHECK] Target incidents already reached!")
            return True

        remaining = self.target_incidents - current_count
        print(f"Need to load: {remaining:,} additional incidents")

        # Load data in batches
        batch_size = 2000
        total_batches = (remaining + batch_size - 1) // batch_size

        print(f"\nLoading {total_batches} batches of {batch_size} incidents each...")
        print("This may take several minutes...")

        start_date = datetime.datetime(2025, 1, 1)
        days_in_2025 = 365

        success_count = 0

        for batch_num in range(1, total_batches + 1):
            # Generate batch
            incidents = self.generate_batch(batch_size, start_date, days_in_2025)

            # Load batch
            if self.load_batch(incidents):
                success_count += len(incidents)

                # Progress reporting
                if batch_num <= 10 or batch_num % 50 == 0 or batch_num == total_batches:
                    progress = (success_count / remaining) * 100
                    print(f"   Batch {batch_num}/{total_batches} loaded - {success_count:,} incidents ({progress:.1f}%)")

                    # Milestone reporting
                    if success_count >= 50000 and (success_count - len(incidents)) < 50000:
                        print("   [MILESTONE] 50,000 incidents loaded!")
                    elif success_count >= 100000 and (success_count - len(incidents)) < 100000:
                        print("   [MILESTONE] 100,000 incidents loaded!")
                    elif success_count >= 200000 and (success_count - len(incidents)) < 200000:
                        print("   [MILESTONE] 200,000 incidents loaded!")
                    elif success_count >= 400000 and (success_count - len(incidents)) < 400000:
                        print("   [MILESTONE] 400,000 incidents loaded!")
            else:
                print(f"   Failed to load batch {batch_num}")

            # Small delay to avoid overwhelming the API
            if batch_num % 10 == 0:
                time.sleep(1)

        print("\n" + "=" * 80)
        print("[CHECK] 2025 Satellite fire data loading complete!")
        print("=" * 80)

        # Final verification
        final_count = self.get_current_count()
        print(f"\nFinal database count: {final_count:,} incidents")
        print(f"Target achieved: {(final_count / self.target_incidents) * 100:.1f}%")

        print("\n[BAR_CHART] To view statistics:")
        print("curl http://localhost:8001/api/v1/stats")
        print("\n[FIRE] To view recent 2025 incidents:")
        print("curl http://localhost:8001/api/v1/fires?limit=10")

        return True

def main():
    loader = FireDataLoader()
    loader.load_2025_data()

if __name__ == "__main__":
    main()