#!/usr/bin/env python3
"""
Generate realistic confirmed wildfire incidents directly to database
"""

import psycopg2
import random
import datetime
from typing import List

def generate_wildfire_incidents():
    # Database connection
    conn = psycopg2.connect(
        host="localhost",
        port="5432",
        database="wildfire_db",
        user="wildfire_user",
        password="wildfire_password"
    )
    cur = conn.cursor()

    # Clear existing hardcoded data
    cur.execute("DELETE FROM fire_incidents_managed")
    print("Cleared existing wildfire incidents")

    # Fire data arrays
    fire_bases = ['Canyon', 'Ridge', 'Valley', 'Creek', 'River', 'Mountain', 'Peak', 'Hill',
                  'Oak', 'Pine', 'Cedar', 'Brush', 'Ranch', 'Road', 'Trail', 'Park', 'Lake', 'Springs']

    causes = ['Equipment Use', 'Electrical Power', 'Arson', 'Smoking', 'Campfire',
              'Lightning', 'Vehicle', 'Debris Burning', 'Railroad', 'Unknown']

    counties = ['Riverside', 'San Bernardino', 'Los Angeles', 'Ventura', 'Orange', 'Santa Barbara',
                'Kern', 'Fresno', 'Tulare', 'Madera', 'Shasta', 'Tehama', 'Butte', 'Plumas',
                'Nevada', 'Placer', 'El Dorado', 'Napa', 'Sonoma', 'Marin', 'Mendocino', 'Lake']

    commanders = ['Battalion Chief Rodriguez', 'Captain Thompson', 'Division Chief Martinez',
                  'Captain Davis', 'Battalion Chief Wilson', 'Captain Johnson', 'Division Chief Anderson',
                  'Captain Lee', 'Battalion Chief Garcia', 'Captain Brown', 'Division Chief Taylor']

    # Date range: January 1, 2025 to September 19, 2025
    start_date = datetime.date(2025, 1, 1)
    end_date = datetime.date(2025, 9, 19)

    current_date = start_date
    incident_count = 0

    while current_date <= end_date:
        # Seasonal incident distribution
        month = current_date.month
        if month in [1, 2, 3, 11, 12]:  # Winter: low season
            daily_incidents = random.randint(5, 15)
        elif month in [4, 5, 6]:  # Spring: medium season
            daily_incidents = random.randint(10, 25)
        else:  # Summer/Fall: peak season (July-October)
            daily_incidents = random.randint(25, 45)

        # Weekend variance (slightly more incidents)
        if current_date.weekday() in [5, 6]:
            daily_incidents = int(daily_incidents * 1.2)

        # Generate incidents for this day
        for i in range(daily_incidents):
            incident_count += 1

            # Generate random location (California bounds)
            latitude = round(32.5 + random.uniform(0, 9.5), 6)  # 32.5 to 42.0
            longitude = round(-124.5 + random.uniform(0, 8.5), 6)  # -124.5 to -116.0

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

            # Generate containment based on days since start
            days_since = (end_date - current_date).days
            if days_since <= 1:  # Very recent fires
                containment = random.randint(0, 30)
            elif days_since <= 3:  # Recent fires
                containment = random.randint(20, 70)
            elif days_since <= 7:  # Week-old fires
                containment = random.randint(50, 95)
            else:  # Older fires
                containment = random.randint(80, 100)

            # Determine status
            if containment >= 100:
                status = 'contained'
                containment = 100
            elif containment >= 80:
                status = 'controlled'
            else:
                status = 'active'

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

            # For contained fires, set resources to 0
            if status == 'contained':
                personnel = 0
                engines = 0
                aircraft = 0

            # Generate incident details
            fire_name = f"{random.choice(fire_bases)} Fire {incident_count}"
            cause = random.choice(causes)
            commander = random.choice(commanders)

            # Generate counties (1-2 counties typically)
            affected_counties = [random.choice(counties)]
            if random.random() < 0.3:  # 30% chance of multi-county fire
                second_county = random.choice(counties)
                if second_county != affected_counties[0]:
                    affected_counties.append(second_county)

            # Generate discovery time (6 AM to 10 PM typical)
            discovery_hour = random.randint(6, 22)
            discovery_minute = random.randint(0, 59)
            discovery_time = datetime.datetime.combine(
                current_date,
                datetime.time(discovery_hour, discovery_minute)
            )

            # Insert into database
            cur.execute("""
                INSERT INTO fire_incidents_managed (
                    incident_name, counties, start_date, discovery_time, latitude, longitude,
                    acres_burned, containment_percentage, incident_status, cause,
                    personnel_assigned, engines, aircraft, incident_commander, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                )
            """, (
                fire_name, affected_counties, current_date, discovery_time, latitude, longitude,
                acres, containment, status, cause, personnel, engines, aircraft, commander
            ))

            if incident_count % 500 == 0:
                print(f"Generated {incident_count} wildfire incidents...")
                conn.commit()  # Commit every 500 records

        current_date += datetime.timedelta(days=1)

    # Final commit
    conn.commit()

    # Verify the data
    cur.execute("""
        SELECT
            COUNT(*) as total_incidents,
            COUNT(*) FILTER (WHERE incident_status = 'active') as active_incidents,
            COUNT(*) FILTER (WHERE start_date >= CURRENT_DATE - INTERVAL '7 days') as last_7_days,
            COUNT(*) FILTER (WHERE start_date >= CURRENT_DATE - INTERVAL '30 days') as last_30_days
        FROM fire_incidents_managed
    """)

    result = cur.fetchone()
    print(f"\nWildfire incidents generated successfully!")
    print(f"Total incidents: {result[0]:,}")
    print(f"Currently active: {result[1]:,}")
    print(f"Started in last 7 days: {result[2]:,}")
    print(f"Started in last 30 days: {result[3]:,}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    generate_wildfire_incidents()