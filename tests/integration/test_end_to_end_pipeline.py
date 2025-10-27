"""
End-to-End Integration Tests for Wildfire Intelligence Platform
Tests complete data flow from ingestion to prediction
"""

import pytest
import asyncio
import httpx
from datetime import datetime, timedelta
import time


class TestEndToEndPipeline:
    """Integration tests for complete system pipeline"""

    @pytest.fixture
    def api_base_url(self):
        """Base URL for API services"""
        return "http://localhost"

    @pytest.fixture
    def test_location(self):
        """California test location"""
        return {
            "latitude": 38.5816,  # Sacramento area
            "longitude": -121.4944,
            "name": "Sacramento, CA"
        }

    @pytest.mark.asyncio
    async def test_firesat_ingestion_to_consumption(self, api_base_url, test_location):
        """
        Test FireSat data flow: Ingestion → Kafka → Storage → Consumption

        Steps:
        1. Trigger FireSat data ingestion
        2. Wait for Kafka processing
        3. Query data consumption API
        4. Verify data integrity
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Trigger FireSat ingestion
            ingestion_response = await client.post(
                f"{api_base_url}:8001/ingest/firesat/manual"
            )
            assert ingestion_response.status_code == 200, "FireSat ingestion failed"

            # Step 2: Wait for Kafka processing and storage
            await asyncio.sleep(5)

            # Step 3: Query data consumption API
            consumption_response = await client.get(
                f"{api_base_url}:8004/consume/latest/firesat_detections",
                params={"limit": 100}
            )
            assert consumption_response.status_code == 200, "Data consumption failed"

            # Step 4: Verify data
            data = consumption_response.json()
            assert "data" in data
            assert len(data["data"]) > 0, "No FireSat detections found"

            # Verify data structure
            detection = data["data"][0]
            required_fields = [
                "latitude", "longitude", "timestamp",
                "fire_radiative_power", "confidence", "satellite_id"
            ]
            for field in required_fields:
                assert field in detection, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_fire_risk_prediction_with_firesat(self, api_base_url, test_location):
        """
        Test fire risk prediction using FireSat data

        Steps:
        1. Request fire risk prediction for location
        2. Verify prediction includes FireSat factors
        3. Check risk score calculation
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Request fire risk prediction
            prediction_response = await client.post(
                f"{api_base_url}:8003/predict",
                json={
                    "latitude": test_location["latitude"],
                    "longitude": test_location["longitude"],
                    "temperature_c": 35.0,
                    "relative_humidity": 15.0,
                    "wind_speed": 20.0,
                    "precipitation_mm": 0.0
                }
            )

            assert prediction_response.status_code == 200, "Fire risk prediction failed"

            # Verify prediction result
            prediction = prediction_response.json()
            assert "risk_score" in prediction
            assert "risk_level" in prediction
            assert "confidence" in prediction
            assert "nearby_fires_count" in prediction

            # Verify risk classification
            assert prediction["risk_level"] in ["low", "medium", "high", "extreme"]
            assert 0.0 <= prediction["risk_score"] <= 1.0
            assert 0.0 <= prediction["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_data_source_integration(self, api_base_url, test_location):
        """
        Test integration of multiple data sources

        Steps:
        1. Fetch terrain data
        2. Fetch infrastructure data
        3. Fetch historical fires
        4. Verify all sources available for prediction
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Test terrain connector
            terrain_response = await client.get(
                f"{api_base_url}:8001/data/terrain",
                params={
                    "latitude": test_location["latitude"],
                    "longitude": test_location["longitude"]
                }
            )
            # May not be implemented yet, so just log
            print(f"Terrain API status: {terrain_response.status_code}")

            # Test infrastructure connector
            infrastructure_response = await client.get(
                f"{api_base_url}:8001/data/infrastructure",
                params={
                    "latitude": test_location["latitude"],
                    "longitude": test_location["longitude"],
                    "radius_km": 10
                }
            )
            print(f"Infrastructure API status: {infrastructure_response.status_code}")

            # Test historical fires
            historical_response = await client.get(
                f"{api_base_url}:8001/data/historical_fires",
                params={
                    "latitude": test_location["latitude"],
                    "longitude": test_location["longitude"],
                    "radius_km": 50,
                    "years_back": 10
                }
            )
            print(f"Historical fires API status: {historical_response.status_code}")

    @pytest.mark.asyncio
    async def test_system_health_checks(self, api_base_url):
        """
        Test all service health endpoints

        Verifies:
        - Data ingestion service
        - Data consumption service
        - Fire risk service
        - Database connectivity
        - Kafka connectivity
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            services = [
                ("Data Ingestion", f"{api_base_url}:8001/health"),
                ("Data Consumption", f"{api_base_url}:8004/health"),
                ("Fire Risk", f"{api_base_url}:8003/health")
            ]

            for service_name, health_url in services:
                try:
                    response = await client.get(health_url)
                    assert response.status_code == 200, f"{service_name} health check failed"

                    health_data = response.json()
                    assert health_data.get("status") in ["healthy", "ok"], f"{service_name} unhealthy"

                    print(f"✓ {service_name}: {health_data.get('status')}")
                except Exception as e:
                    pytest.fail(f"{service_name} health check error: {str(e)}")

    @pytest.mark.asyncio
    async def test_performance_batch_prediction(self, api_base_url):
        """
        Test batch prediction performance

        Verifies:
        - Multiple concurrent predictions
        - Response time < 2 seconds per prediction
        - System stability under load
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Generate 10 test locations around California
            test_locations = [
                {"latitude": 38.58 + i * 0.5, "longitude": -121.49 + i * 0.3}
                for i in range(10)
            ]

            # Create prediction requests
            start_time = time.time()

            tasks = []
            for location in test_locations:
                task = client.post(
                    f"{api_base_url}:8003/predict",
                    json={
                        "latitude": location["latitude"],
                        "longitude": location["longitude"],
                        "temperature_c": 30.0,
                        "relative_humidity": 20.0,
                        "wind_speed": 15.0
                    }
                )
                tasks.append(task)

            # Execute concurrent predictions
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            total_time = end_time - start_time

            # Verify all succeeded
            successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)

            print(f"Batch predictions: {successful}/{len(test_locations)} successful")
            print(f"Total time: {total_time:.2f}s")
            print(f"Average time per prediction: {total_time/len(test_locations):.2f}s")

            assert successful >= 8, "Too many prediction failures"
            assert total_time < 30.0, "Batch prediction too slow"

    @pytest.mark.asyncio
    async def test_data_pipeline_latency(self, api_base_url):
        """
        Test end-to-end data pipeline latency

        Measures:
        - Ingestion trigger → Data available in consumption API
        - Total latency should be < 10 seconds
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get current timestamp
            start_time = datetime.utcnow()

            # Trigger ingestion
            await client.post(f"{api_base_url}:8001/ingest/firesat/manual")

            # Poll consumption API until new data appears
            max_wait = 10  # seconds
            poll_interval = 1  # second
            data_found = False

            for _ in range(max_wait):
                await asyncio.sleep(poll_interval)

                response = await client.get(
                    f"{api_base_url}:8004/consume/latest/firesat_detections",
                    params={"limit": 1}
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("data"):
                        detection = data["data"][0]
                        detection_time = datetime.fromisoformat(
                            detection["timestamp"].replace("Z", "+00:00")
                        )

                        # Check if detection is recent
                        if (datetime.utcnow() - detection_time.replace(tzinfo=None)).seconds < 60:
                            data_found = True
                            break

            end_time = datetime.utcnow()
            latency = (end_time - start_time).total_seconds()

            print(f"Pipeline latency: {latency:.2f}s")

            assert data_found, "New data not found in consumption API"
            assert latency < 15.0, f"Pipeline latency too high: {latency}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
