"""
Performance Benchmarking for Fire Risk Prediction Service
Measures throughput, latency, and resource usage
"""

import asyncio
import httpx
import time
import statistics
from typing import List, Dict, Any
import json


class FireRiskBenchmark:
    """Performance benchmark suite for fire risk prediction"""

    def __init__(self, api_base_url: str = "http://localhost:8003"):
        self.api_base_url = api_base_url
        self.results = {}

    async def benchmark_single_prediction_latency(self, num_requests: int = 100):
        """
        Benchmark single prediction latency

        Measures:
        - Min, max, average, p50, p95, p99 latencies
        - Requests per second
        """
        print(f"\n🔥 Benchmarking Single Prediction Latency ({num_requests} requests)")

        latencies = []
        errors = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(num_requests):
                request = {
                    "latitude": 38.5816 + (i % 10) * 0.1,
                    "longitude": -121.4944 + (i % 10) * 0.1,
                    "temperature_c": 30.0,
                    "relative_humidity": 20.0,
                    "wind_speed": 15.0,
                    "precipitation_mm": 0.0
                }

                start = time.time()
                try:
                    response = await client.post(
                        f"{self.api_base_url}/predict",
                        json=request
                    )
                    if response.status_code == 200:
                        latency = (time.time() - start) * 1000  # ms
                        latencies.append(latency)
                    else:
                        errors += 1
                except Exception as e:
                    errors += 1

        # Calculate statistics
        if latencies:
            self.results["single_prediction"] = {
                "total_requests": num_requests,
                "successful": len(latencies),
                "errors": errors,
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "avg_latency_ms": statistics.mean(latencies),
                "median_latency_ms": statistics.median(latencies),
                "p95_latency_ms": self._percentile(latencies, 95),
                "p99_latency_ms": self._percentile(latencies, 99),
                "requests_per_second": len(latencies) / (sum(latencies) / 1000)
            }

            self._print_results("Single Prediction Latency", self.results["single_prediction"])

    async def benchmark_concurrent_load(self, concurrent_users: int = 50, requests_per_user: int = 10):
        """
        Benchmark concurrent load handling

        Simulates multiple concurrent users making predictions
        """
        print(f"\n🔥 Benchmarking Concurrent Load ({concurrent_users} users, {requests_per_user} req/user)")

        latencies = []
        errors = 0

        async def user_session(user_id: int):
            """Simulate a single user making multiple requests"""
            session_latencies = []
            session_errors = 0

            async with httpx.AsyncClient(timeout=30.0) as client:
                for req_num in range(requests_per_user):
                    request = {
                        "latitude": 38.5 + user_id * 0.05,
                        "longitude": -121.5 + req_num * 0.05,
                        "temperature_c": 25.0 + user_id % 20,
                        "relative_humidity": 15.0 + req_num % 30,
                        "wind_speed": 10.0 + (user_id + req_num) % 15
                    }

                    start = time.time()
                    try:
                        response = await client.post(
                            f"{self.api_base_url}/predict",
                            json=request
                        )
                        if response.status_code == 200:
                            latency = (time.time() - start) * 1000
                            session_latencies.append(latency)
                        else:
                            session_errors += 1
                    except:
                        session_errors += 1

            return session_latencies, session_errors

        # Run concurrent user sessions
        start_time = time.time()
        tasks = [user_session(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Aggregate results
        for session_latencies, session_errors in results:
            latencies.extend(session_latencies)
            errors += session_errors

        if latencies:
            self.results["concurrent_load"] = {
                "concurrent_users": concurrent_users,
                "requests_per_user": requests_per_user,
                "total_requests": concurrent_users * requests_per_user,
                "successful": len(latencies),
                "errors": errors,
                "total_time_seconds": total_time,
                "avg_latency_ms": statistics.mean(latencies),
                "median_latency_ms": statistics.median(latencies),
                "p95_latency_ms": self._percentile(latencies, 95),
                "p99_latency_ms": self._percentile(latencies, 99),
                "throughput_rps": len(latencies) / total_time
            }

            self._print_results("Concurrent Load", self.results["concurrent_load"])

    async def benchmark_firesat_integration(self, num_requests: int = 50):
        """
        Benchmark prediction with FireSat data integration

        Measures impact of real-time satellite data on latency
        """
        print(f"\n🛰️ Benchmarking FireSat Integration ({num_requests} requests)")

        latencies_with_firesat = []
        errors = 0

        # California wildfire-prone locations
        test_locations = [
            (38.5816, -121.4944),  # Sacramento
            (34.0522, -118.2437),  # Los Angeles
            (37.7749, -122.4194),  # San Francisco
            (32.7157, -117.1611),  # San Diego
            (36.7783, -119.4179),  # Fresno
        ]

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(num_requests):
                lat, lon = test_locations[i % len(test_locations)]

                request = {
                    "latitude": lat,
                    "longitude": lon,
                    "temperature_c": 32.0,
                    "relative_humidity": 12.0,
                    "wind_speed": 25.0
                }

                start = time.time()
                try:
                    response = await client.post(
                        f"{self.api_base_url}/predict",
                        json=request
                    )
                    if response.status_code == 200:
                        latency = (time.time() - start) * 1000
                        latencies_with_firesat.append(latency)

                        # Check if FireSat data was used
                        data = response.json()
                        nearby_fires = data.get("nearby_fires_count", 0)
                    else:
                        errors += 1
                except:
                    errors += 1

        if latencies_with_firesat:
            self.results["firesat_integration"] = {
                "total_requests": num_requests,
                "successful": len(latencies_with_firesat),
                "errors": errors,
                "avg_latency_ms": statistics.mean(latencies_with_firesat),
                "median_latency_ms": statistics.median(latencies_with_firesat),
                "p95_latency_ms": self._percentile(latencies_with_firesat, 95)
            }

            self._print_results("FireSat Integration", self.results["firesat_integration"])

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _print_results(self, title: str, results: Dict[str, Any]):
        """Pretty print benchmark results"""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")

        for key, value in results.items():
            if isinstance(value, float):
                print(f"  {key:30s}: {value:>10.2f}")
            else:
                print(f"  {key:30s}: {value:>10}")

        print(f"{'='*60}\n")

    def save_results(self, filename: str = "benchmark_results.json"):
        """Save benchmark results to JSON file"""
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"✓ Results saved to {filename}")


async def main():
    """Run all benchmarks"""
    benchmark = FireRiskBenchmark()

    print("🔥 Fire Risk Service Performance Benchmark")
    print("=" * 60)

    # Run benchmarks
    await benchmark.benchmark_single_prediction_latency(num_requests=100)
    await benchmark.benchmark_concurrent_load(concurrent_users=25, requests_per_user=10)
    await benchmark.benchmark_firesat_integration(num_requests=50)

    # Save results
    benchmark.save_results()

    print("\n✓ All benchmarks completed!")


if __name__ == "__main__":
    asyncio.run(main())
