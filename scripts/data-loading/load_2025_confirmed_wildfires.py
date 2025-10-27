#!/usr/bin/env python3
"""
2025 Confirmed Wildfire Incidents Loader
Generates realistic confirmed wildfire incidents based on 2025 statistics
Target: 6,928 Confirmed Wildfires for 2025 (133 per week average)
"""

import requests
import json
import random
import datetime
from typing import List, Dict
import time

class ConfirmedWildfireLoader:
    def __init__(self):
        self.api_url = "http://localhost:8001/api/v1"

        # 2025 Confirmed Wildfire Statistics (real vs detections)
        self.target_confirmed_wildfires = 6928  # Actual confirmed wildfires
        self.total_detections = 432942  # Total satellite detections

        # Weekly distribution (seasonal pattern)
        self.weekly_multipliers = {
            1: 0.3, 2: 0.3, 3: 0.4, 4: 0.5, 5: 0.6, 6: 0.7,  # Winter-Spring (low season)
            7: 1.8, 8: 2.2, 9: 2.0, 10: 1.5,  # Peak fire season (July-Oct)
            11: 0.8, 12: 0.4  # Fall-Winter
        }

        # California fire-prone regions with seasonal risk
        self.ca_regions = [
            {"name": "Northern CA", "lat_range": (37.0, 42.0), "lon_range": (-124.0, -120.0), "risk_multiplier": 1.2},
            {"name": "Central Valley", "lat_range": (35.0, 38.0), "lon_range": (-122.0, -119.0), "risk_multiplier": 0.8},
            {"name": "Southern CA", "lat_range": (32.5, 36.0), "lon_range": (-119.0, -116.0), "risk_multiplier": 1.5},
            {"name": "Sierra Nevada", "lat_range": (35.5, 39.5), "lon_range": (-121.0, -118.0), "risk_multiplier": 1.3},
            {"name": "Coastal Range", "lat_range": (34.0, 40.0), "lon_range": (-124.5, -122.0), "risk_multiplier": 1.0}
        ]

        # Fire causes (based on CAL FIRE statistics)
        self.causes = [
            {"name": "Equipment Use", "weight": 25},
            {"name": "Electrical Power", "weight": 20},
            {"name": "Arson", "weight": 15},
            {"name": "Smoking", "weight": 10},
            {"name": "Campfire", "weight": 8},
            {"name": "Lightning", "weight": 7},
            {"name": "Vehicle", "weight": 5},
            {"name": "Debris Burning", "weight": 4},
            {"name": "Railroad", "weight": 3},
            {"name": "Unknown", "weight": 3}
        ]

        # California counties (high fire risk counties)
        self.counties = [
            "Riverside", "San Bernardino", "Los Angeles", "Ventura", "Orange", "Santa Barbara",
            "Kern", "Fresno", "Tulare", "Madera", "Merced", "Stanislaus",
            "Shasta", "Tehama", "Butte", "Plumas", "Sierra", "Nevada",
            "Placer", "El Dorado", "Amador", "Calaveras", "Tuolumne", "Mariposa",
            "Mendocino", "Lake", "Napa", "Sonoma", "Marin", "Solano"
        ]

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            response = requests.get(f"{self.api_url}/stats", timeout=10)
            return response.status_code == 200
        except:
            return False

    def get_current_wildfire_count(self) -> int:
        """Get current confirmed wildfire count"""
        try:
            # Direct database query would be better, but using a simple check
            response = requests.get(f"{self.api_url}/stats", timeout=10)
            if response.status_code == 200:
                # This is a rough estimate - in real implementation we'd query the managed incidents table
                return 0  # Will be replaced with actual count after first load
        except:
            pass
        return 0

    def generate_fire_name(self, region_name: str, county: str) -> str:
        """Generate realistic fire names"""
        name_patterns = [
            # Geographic features
            ["Canyon", "Ridge", "Valley", "Creek", "River", "Mountain", "Peak", "Hill"],
            # Vegetation
            ["Oak", "Pine", "Cedar", "Brush", "Grass", "Chaparral"],
            # Local landmarks
            ["Ranch", "Road", "Trail", "Park", "Lake", "Springs"]
        ]

        pattern = random.choice(name_patterns)
        base_name = random.choice(pattern)
        return f"{base_name} Fire"

    def generate_wildfire_incident(self, date: datetime.date, region: Dict) -> Dict:
        """Generate a realistic confirmed wildfire incident"""
        # Generate coordinates within region
        latitude = round(random.uniform(*region["lat_range"]), 6)
        longitude = round(random.uniform(*region["lon_range"]), 6)

        # Generate fire size (realistic distribution)
        size_rand = random.random()
        if size_rand < 0.70:  # 70% small fires (0-10 acres)
            acres = round(random.uniform(0.1, 10.0), 1)
        elif size_rand < 0.90:  # 20% medium fires (10-100 acres)
            acres = round(random.uniform(10.0, 100.0), 1)
        elif size_rand < 0.98:  # 8% large fires (100-1000 acres)
            acres = round(random.uniform(100.0, 1000.0), 1)
        else:  # 2% major fires (1000+ acres)
            acres = round(random.uniform(1000.0, 50000.0), 1)

        # Generate containment based on time since start
        days_since_start = (datetime.date.today() - date).days
        if days_since_start == 0:
            containment = random.randint(0, 30)  # New fires
        elif days_since_start <= 3:
            containment = random.randint(20, 70)  # Recent fires
        elif days_since_start <= 7:
            containment = random.randint(50, 95)  # Week-old fires
        else:
            containment = random.randint(80, 100)  # Older fires

        # Determine status
        if containment >= 100:
            status = "contained"
        elif containment >= 80:
            status = "controlled"
        else:
            status = "active"

        # Generate counties (1-3 counties affected)
        num_counties = random.choices([1, 2, 3], weights=[70, 25, 5])[0]
        affected_counties = random.sample(self.counties, num_counties)

        # Generate cause
        cause_names = [c["name"] for c in self.causes]
        cause_weights = [c["weight"] for c in self.causes]
        cause = random.choices(cause_names, weights=cause_weights)[0]

        # Generate resources based on fire size
        if acres < 10:
            personnel = random.randint(15, 50)
            engines = random.randint(2, 8)
            aircraft = random.randint(0, 2)
        elif acres < 100:
            personnel = random.randint(50, 200)
            engines = random.randint(8, 20)
            aircraft = random.randint(1, 5)
        elif acres < 1000:
            personnel = random.randint(200, 800)
            engines = random.randint(20, 50)
            aircraft = random.randint(3, 10)
        else:
            personnel = random.randint(800, 3000)
            engines = random.randint(50, 120)
            aircraft = random.randint(8, 25)

        # Generate incident commander
        commanders = ["Battalion Chief Rodriguez", "Captain Thompson", "Division Chief Martinez",
                     "Captain Davis", "Battalion Chief Wilson", "Captain Johnson", "Division Chief Anderson",
                     "Captain Lee", "Battalion Chief Garcia", "Captain Brown", "Division Chief Taylor"]

        fire_name = self.generate_fire_name(region["name"], affected_counties[0])

        # Generate discovery time
        discovery_hour = random.randint(6, 22)  # Most fires discovered during daylight
        discovery_minute = random.randint(0, 59)
        discovery_time = datetime.datetime.combine(date, datetime.time(discovery_hour, discovery_minute))

        return {
            "incident_name": fire_name,
            "counties": affected_counties,
            "start_date": date.isoformat(),
            "discovery_time": discovery_time.isoformat() + "Z",
            "latitude": latitude,
            "longitude": longitude,
            "acres_burned": acres,
            "containment_percentage": containment,
            "incident_status": status,
            "cause": cause,
            "personnel_assigned": personnel,
            "engines": engines,
            "aircraft": aircraft,
            "incident_commander": random.choice(commanders)
        }

    def calculate_weekly_incidents(self, week_number: int, month: int) -> int:
        """Calculate realistic number of incidents for a given week"""
        base_weekly_average = self.target_confirmed_wildfires / 52  # ~133 per week
        seasonal_multiplier = self.weekly_multipliers.get(month, 1.0)

        # Add some randomness
        randomness = random.uniform(0.7, 1.3)

        weekly_count = int(base_weekly_average * seasonal_multiplier * randomness)
        return max(1, weekly_count)  # At least 1 fire per week

    def load_incidents_for_daterange(self, start_date: datetime.date, end_date: datetime.date):
        """Load wildfire incidents for a specific date range"""
        print(f"\nLoading confirmed wildfires from {start_date} to {end_date}")

        current_date = start_date
        total_loaded = 0

        while current_date <= end_date:
            # Calculate incidents for this week
            week_incidents = self.calculate_weekly_incidents(
                current_date.isocalendar()[1],
                current_date.month
            )

            incidents_this_day = week_incidents // 7  # Distribute weekly incidents across days
            if current_date.weekday() in [5, 6]:  # Weekend - slightly more fires
                incidents_this_day = int(incidents_this_day * 1.2)

            # Generate incidents for this day
            for _ in range(max(1, incidents_this_day)):
                # Select region based on risk
                region_weights = [r["risk_multiplier"] for r in self.ca_regions]
                region = random.choices(self.ca_regions, weights=region_weights)[0]

                incident = self.generate_wildfire_incident(current_date, region)

                # Insert into database (would need actual API endpoint)
                # For now, just count
                total_loaded += 1

                if total_loaded % 100 == 0:
                    print(f"   Generated {total_loaded} wildfire incidents...")

            current_date += datetime.timedelta(days=1)

        print(f"Generated {total_loaded} confirmed wildfire incidents")
        return total_loaded

    def load_2025_wildfires(self):
        """Load all 2025 confirmed wildfire data"""
        print("=" * 80)
        print("[FIRE] 2025 Confirmed Wildfire Incidents Loader [FIRE]")
        print("=" * 80)
        print()
        print("2025 Wildfire Statistics Target:")
        print(f"- Total Confirmed Wildfires: {self.target_confirmed_wildfires:,}")
        print(f"- Weekly Average: {self.target_confirmed_wildfires // 52:,}")
        print(f"- Peak Season (Jul-Oct): ~{int(self.target_confirmed_wildfires * 0.6):,}")
        print("=" * 80)

        # Test connection
        print("\nTesting API connection...")
        if not self.test_connection():
            print("[X] Error: Cannot connect to API")
            return False
        print("[CHECK] API connection successful")

        # Load full year data
        start_date = datetime.date(2025, 1, 1)
        end_date = datetime.date(2025, 9, 19)  # Current date

        total_incidents = self.load_incidents_for_daterange(start_date, end_date)

        print("\n" + "=" * 80)
        print("[CHECK] 2025 Confirmed wildfire data generation complete!")
        print(f"Generated {total_incidents:,} wildfire incidents")
        print("=" * 80)

        return True

def main():
    loader = ConfirmedWildfireLoader()
    loader.load_2025_wildfires()

if __name__ == "__main__":
    main()