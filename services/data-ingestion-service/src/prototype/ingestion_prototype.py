"""
Challenge 1 Deliverable: Data Ingestion Prototype
Working prototype demonstrating real-time, batch, and streaming ingestion capabilities
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import json
import logging
from dataclasses import dataclass

# Import our existing components
from ..validation.error_handling import get_error_framework
from ..metrics.latency_dashboard import get_dashboard
from ..architecture.blueprint import get_architecture, IngestionMode, DataSourceType

class IngestionPrototype:
    """Working prototype for wildfire data ingestion system"""

    def __init__(self):
        self.error_framework = get_error_framework()
        self.dashboard = get_dashboard()
        self.architecture = get_architecture()
        self.logger = logging.getLogger(__name__)

        # Configure logging
        logging.basicConfig(level=logging.INFO)

    async def demonstrate_real_time_ingestion(self) -> Dict[str, Any]:
        """Demonstrate real-time fire detection data ingestion"""
        print("\n🔥 CHALLENGE 1 PROTOTYPE: Real-Time Fire Detection Ingestion")
        print("=" * 70)

        # Record start time for latency metrics
        start_time = self.dashboard.record_ingestion_start("nasa_firms", "real-time")

        # Simulate real-time NASA FIRMS data
        sample_data = [
            {
                'latitude': 37.7749,
                'longitude': -122.4194,
                'brightness': 325.5,
                'confidence': 85,
                'acq_date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'acq_time': datetime.now(timezone.utc).strftime('%H%M'),
                'satellite': 'Aqua',
                'version': '6.1',
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            {
                'latitude': 34.0522,
                'longitude': -118.2437,
                'brightness': 298.2,
                'confidence': 92,
                'acq_date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'acq_time': datetime.now(timezone.utc).strftime('%H%M'),
                'satellite': 'Terra',
                'version': '6.1',
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            {
                'latitude': 38.5816,
                'longitude': -121.4944,
                'brightness': 'invalid',  # Intentional error for validation testing
                'confidence': 78,
                'acq_date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'acq_time': datetime.now(timezone.utc).strftime('%H%M'),
                'satellite': 'NOAA-20',
                'version': '6.1',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        ]

        print(f"📊 Processing {len(sample_data)} fire detection records...")

        # Process batch with error handling framework
        validation_results = await self.error_framework.process_batch(sample_data, 'nasa_firms')

        # Record completion metrics
        metrics = self.dashboard.record_ingestion_complete(
            source_type="nasa_firms",
            ingestion_mode="real-time",
            start_time=start_time,
            record_count=len(sample_data),
            success_count=len(validation_results['valid_records']),
            validation_results=validation_results['validation_summary']
        )

        print(f"✅ Real-time ingestion completed:")
        print(f"   📈 Latency: {metrics.latency_ms:.2f}ms")
        print(f"   🎯 Fidelity: {metrics.fidelity_score:.2%}")
        print(f"   📊 Success Rate: {len(validation_results['valid_records'])}/{len(sample_data)}")

        return {
            'mode': 'real-time',
            'source': 'nasa_firms',
            'metrics': metrics,
            'validation_results': validation_results
        }

    async def demonstrate_streaming_ingestion(self) -> Dict[str, Any]:
        """Demonstrate streaming weather data ingestion"""
        print("\n🌦️  CHALLENGE 1 PROTOTYPE: Streaming Weather Data Ingestion")
        print("=" * 70)

        start_time = self.dashboard.record_ingestion_start("noaa_weather", "streaming")

        # Simulate streaming weather data
        weather_stream = [
            {
                'station_id': 'KSAN',
                'latitude': 32.7335,
                'longitude': -117.1896,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'temperature': 22.5,
                'humidity': 65.2,
                'wind_speed': 8.3,
                'pressure': 1013.2,
                'precipitation': 0.0
            },
            {
                'station_id': 'KLAX',
                'latitude': 33.9425,
                'longitude': -118.4081,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'temperature': 24.1,
                'humidity': 58.7,
                'wind_speed': 12.1,
                'pressure': 1015.8,
                'precipitation': 0.2
            },
            {
                'station_id': 'INVALID',  # Test station validation
                'latitude': 'bad_value',
                'longitude': -121.4944,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'temperature': 19.8,
                'humidity': 72.1,
                'wind_speed': 6.5,
                'pressure': 1012.1,
                'precipitation': 0.0
            }
        ]

        print(f"📡 Processing {len(weather_stream)} weather records...")

        # Simulate streaming delay
        await asyncio.sleep(0.5)

        # Process streaming data
        validation_results = await self.error_framework.process_batch(weather_stream, 'noaa_weather')

        # Record metrics
        metrics = self.dashboard.record_ingestion_complete(
            source_type="noaa_weather",
            ingestion_mode="streaming",
            start_time=start_time,
            record_count=len(weather_stream),
            success_count=len(validation_results['valid_records']),
            validation_results=validation_results['validation_summary']
        )

        print(f"✅ Streaming ingestion completed:")
        print(f"   📈 Latency: {metrics.latency_ms:.2f}ms")
        print(f"   🎯 Fidelity: {metrics.fidelity_score:.2%}")
        print(f"   📊 Success Rate: {len(validation_results['valid_records'])}/{len(weather_stream)}")

        return {
            'mode': 'streaming',
            'source': 'noaa_weather',
            'metrics': metrics,
            'validation_results': validation_results
        }

    async def demonstrate_batch_ingestion(self) -> Dict[str, Any]:
        """Demonstrate batch IoT sensor data ingestion"""
        print("\n📡 CHALLENGE 1 PROTOTYPE: Batch IoT Sensor Ingestion")
        print("=" * 70)

        start_time = self.dashboard.record_ingestion_start("iot_sensors", "batch")

        # Simulate batch IoT sensor data
        iot_batch = []
        for i in range(10):
            iot_batch.append({
                'sensor_id': f'sensor_{1000 + i}',
                'latitude': 37.0 + (i * 0.1),
                'longitude': -122.0 - (i * 0.1),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'temperature': 25.0 + (i * 2),
                'humidity': 60.0 + (i * 3),
                'smoke_level': i * 10,
                'pm25': 15.0 + (i * 5),
                'battery_level': 90 - (i * 2)
            })

        # Add some problematic records for testing
        iot_batch.append({
            'sensor_id': 'sensor_bad',
            'latitude': 200,  # Invalid latitude
            'longitude': -122.5,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'temperature': 28.5,
            'humidity': 150,  # Invalid humidity
            'smoke_level': 25,
            'pm25': 18.5,
            'battery_level': 75
        })

        print(f"📦 Processing batch of {len(iot_batch)} IoT sensor records...")

        # Simulate batch processing delay
        await asyncio.sleep(1.0)

        # Process batch data
        validation_results = await self.error_framework.process_batch(iot_batch, 'iot_sensor')

        # Record metrics
        metrics = self.dashboard.record_ingestion_complete(
            source_type="iot_sensors",
            ingestion_mode="batch",
            start_time=start_time,
            record_count=len(iot_batch),
            success_count=len(validation_results['valid_records']),
            validation_results=validation_results['validation_summary']
        )

        print(f"✅ Batch ingestion completed:")
        print(f"   📈 Latency: {metrics.latency_ms:.2f}ms")
        print(f"   🎯 Fidelity: {metrics.fidelity_score:.2%}")
        print(f"   📊 Success Rate: {len(validation_results['valid_records'])}/{len(iot_batch)}")

        return {
            'mode': 'batch',
            'source': 'iot_sensors',
            'metrics': metrics,
            'validation_results': validation_results
        }

    async def demonstrate_error_handling(self) -> Dict[str, Any]:
        """Demonstrate comprehensive error handling capabilities"""
        print("\n⚠️  CHALLENGE 1 PROTOTYPE: Error Handling & Recovery")
        print("=" * 70)

        # Create problematic data to test error handling
        problematic_data = [
            {
                'latitude': 'not_a_number',
                'longitude': -119.5,
                'brightness': -50,  # Invalid brightness
                'confidence': 150,  # Invalid confidence
                'acq_date': 'invalid_date',
                'satellite': 'Unknown'
            },
            {
                # Missing required fields
                'brightness': 320,
                'confidence': 85
            },
            {
                'latitude': 91,  # Out of range
                'longitude': -181,  # Out of range
                'brightness': 1500,  # Out of range
                'confidence': 95,
                'acq_date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'satellite': 'Terra'
            }
        ]

        print(f"🚨 Testing error handling with {len(problematic_data)} problematic records...")

        start_time = time.time()
        validation_results = await self.error_framework.process_batch(problematic_data, 'nasa_firms')
        processing_time = (time.time() - start_time) * 1000

        # Display error analysis
        print(f"📊 Error Handling Results:")
        print(f"   Total Records: {len(problematic_data)}")
        print(f"   Valid Records: {len(validation_results['valid_records'])}")
        print(f"   Invalid Records: {len(validation_results['invalid_records'])}")
        print(f"   Corrected Records: {len(validation_results['corrected_records'])}")
        print(f"   Processing Time: {processing_time:.2f}ms")

        # Show specific errors
        if validation_results['invalid_records']:
            print(f"\n🔍 Error Details:")
            for invalid in validation_results['invalid_records'][:3]:  # Show first 3
                print(f"   Record {invalid['index']}:")
                for error in invalid['errors'][:2]:  # Show first 2 errors per record
                    print(f"     - {error['field']}: {error['message']}")

        return {
            'mode': 'error_handling',
            'total_records': len(problematic_data),
            'results': validation_results,
            'processing_time_ms': processing_time
        }

    async def run_complete_prototype(self) -> Dict[str, Any]:
        """Run complete Challenge 1 prototype demonstration"""
        print("\n🎯 CHALLENGE 1 COMPLETE PROTOTYPE DEMONSTRATION")
        print("🏆 CAL FIRE Data Sources and Ingestion Mechanisms")
        print("=" * 80)

        results = {}

        # Run all ingestion mode demonstrations
        results['real_time'] = await self.demonstrate_real_time_ingestion()
        await asyncio.sleep(1)

        results['streaming'] = await self.demonstrate_streaming_ingestion()
        await asyncio.sleep(1)

        results['batch'] = await self.demonstrate_batch_ingestion()
        await asyncio.sleep(1)

        results['error_handling'] = await self.demonstrate_error_handling()

        # Generate final dashboard summary
        print("\n📊 FINAL PROTOTYPE DASHBOARD")
        self.dashboard.print_dashboard()

        # Export metrics and architecture
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = f"C:/dev/wildfire/services/data-ingestion-service/prototype_metrics_{timestamp}.json"
        blueprint_file = f"C:/dev/wildfire/services/data-ingestion-service/architecture_blueprint_{timestamp}.json"

        self.dashboard.export_metrics(metrics_file)
        self.architecture.export_blueprint(blueprint_file)

        # Generate prototype summary
        prototype_summary = {
            'challenge': 'CAL FIRE Challenge 1 - Data Sources and Ingestion Mechanisms',
            'prototype_completed_at': datetime.now(timezone.utc).isoformat(),
            'capabilities_demonstrated': [
                'Real-time fire detection data ingestion',
                'Streaming weather data processing',
                'Batch IoT sensor data ingestion',
                'Comprehensive error handling and validation',
                'Latency and fidelity metrics tracking',
                'Data deduplication and quality assurance',
                'Multi-mode ingestion pipeline architecture'
            ],
            'ingestion_modes_tested': ['real-time', 'streaming', 'batch'],
            'data_sources_simulated': ['nasa_firms', 'noaa_weather', 'iot_sensors'],
            'metrics_generated': True,
            'architecture_documented': True,
            'results': results
        }

        summary_file = f"C:/dev/wildfire/services/data-ingestion-service/prototype_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(prototype_summary, f, indent=2, default=str)

        print(f"\n🎉 CHALLENGE 1 PROTOTYPE COMPLETED SUCCESSFULLY!")
        print(f"📊 Metrics exported: {metrics_file}")
        print(f"🏗️ Blueprint exported: {blueprint_file}")
        print(f"📋 Summary exported: {summary_file}")

        return prototype_summary

# Global prototype instance
prototype = IngestionPrototype()

def get_prototype() -> IngestionPrototype:
    """Get the global prototype instance"""
    return prototype

async def run_challenge_1_demo():
    """Run the complete Challenge 1 demonstration"""
    demo_prototype = get_prototype()
    return await demo_prototype.run_complete_prototype()

if __name__ == "__main__":
    # Run the prototype demonstration
    result = asyncio.run(run_challenge_1_demo())
    print(f"\n✅ Challenge 1 Prototype completed with {len(result['results'])} demonstrations")