#!/usr/bin/env python3
"""
Quick script to consume ALL fire messages from Kafka and insert into PostgreSQL
This will clear the backlog and get current fire data into the database
"""

import json
import psycopg2
from kafka import KafkaConsumer
from datetime import datetime

# Database connection
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='wildfire_db',
    user='wildfire_user',
    password='wildfire_password'
)
cur = conn.cursor()

# Kafka consumer - start from beginning to get all messages
consumer = KafkaConsumer(
    'wildfire-nasa-firms',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='bulk-fire-import',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    consumer_timeout_ms=10000  # Stop after 10 seconds of no messages
)

print("Starting to consume fire messages from Kafka...")

inserted = 0
skipped = 0

for message in consumer:
    try:
        fire_data = message.value

        # Extract fields from Kafka message
        timestamp = fire_data.get('timestamp')
        latitude = fire_data.get('latitude')
        longitude = fire_data.get('longitude')
        confidence = fire_data.get('confidence')
        bright_ti4 = fire_data.get('bright_ti4')
        frp = fire_data.get('frp')
        satellite = fire_data.get('satellite')
        instrument = fire_data.get('instrument')
        source = fire_data.get('source', 'NASA FIRMS')
        detection_id = fire_data.get('detection_id')

        # Generate incident_id if not present
        if not detection_id:
            detection_id = f"firms_{satellite}_{timestamp}_{latitude}_{longitude}"

        # Insert into database (ignore duplicates)
        try:
            cur.execute("""
                INSERT INTO fire_incidents (
                    incident_id, latitude, longitude, confidence, brightness,
                    frp, satellite, instrument, source, timestamp, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (incident_id) DO NOTHING
            """, (
                detection_id, latitude, longitude, confidence, bright_ti4,
                frp, satellite, instrument, source, timestamp
            ))

            if cur.rowcount > 0:
                inserted += 1
                if inserted % 100 == 0:
                    conn.commit()
                    print(f"Inserted {inserted} fire incidents so far...")
            else:
                skipped += 1

        except Exception as e:
            print(f"Error inserting record: {e}")
            skipped += 1

    except Exception as e:
        print(f"Error processing message: {e}")
        skipped += 1

# Final commit
conn.commit()

print(f"\n=== BULK IMPORT COMPLETE ===")
print(f"Inserted: {inserted} new fire incidents")
print(f"Skipped: {skipped} duplicates or errors")

# Verify data in database
cur.execute("SELECT COUNT(*) FROM fire_incidents")
total = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM fire_incidents WHERE created_at >= NOW() - INTERVAL '7 days'")
recent = cur.fetchone()[0]

cur.execute("SELECT MAX(timestamp), MAX(created_at) FROM fire_incidents")
latest_fire, latest_insert = cur.fetchone()

print(f"\nDatabase state:")
print(f"  Total fire incidents: {total}")
print(f"  Incidents (last 7 days): {recent}")
print(f"  Latest fire timestamp: {latest_fire}")
print(f"  Latest database insert: {latest_insert}")

cur.close()
conn.close()
consumer.close()

print("\n✅ Done! Fire data is now live in the database.")
