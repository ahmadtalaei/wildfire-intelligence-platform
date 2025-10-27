"""
Test Critical Alert Handler for <1s Latency
Verifies direct WebSocket → Kafka streaming bypasses queue
"""

import asyncio
import json
import time
from datetime import datetime, timezone
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.streaming.critical_alert_handler import CriticalAlertHandler


async def test_critical_alert_latency():
    """Test that critical alerts achieve <100ms latency"""
    print("\n" + "="*60)
    print("CRITICAL ALERT HANDLER TEST")
    print("Testing <1s latency for life-critical alerts")
    print("="*60 + "\n")

    # Initialize handler
    handler = CriticalAlertHandler(
        kafka_bootstrap_servers="localhost:9092",
        alert_topic="wildfire-critical-alerts",
        max_latency_ms=100,
        heartbeat_interval=30
    )

    try:
        # Start handler
        print("[1/5] Starting critical alert handler...")
        await handler.start()
        print("✓ Handler started successfully\n")

        # Test alert 1: Evacuation Order
        print("[2/5] Sending evacuation order alert...")
        start_time = time.time() * 1000

        evacuation_alert = {
            'alert_id': 'EVAC-001',
            'alert_type': 'EVACUATION_ORDER',
            'severity': 'CRITICAL',
            'location': 'Paradise, CA',
            'latitude': 39.7596,
            'longitude': -121.6219,
            'message': 'IMMEDIATE EVACUATION ORDERED - Paradise area',
            'affected_population': 26000,
            'fire_name': 'Test Fire',
            'evacuation_zones': ['Zone A', 'Zone B', 'Zone C'],
            'evacuation_routes': ['Skyway', 'Clark Road', 'Pentz Road'],
            'shelter_locations': [
                {'name': 'Silver Dollar Fairgrounds', 'address': 'Chico, CA'},
                {'name': 'Neighborhood Church', 'address': 'Chico, CA'}
            ],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        success = await handler.send_critical_alert(evacuation_alert, source_id="evacuation_system")
        end_time = time.time() * 1000
        latency = end_time - start_time

        if success:
            print(f"✓ Evacuation alert sent - Latency: {latency:.2f}ms")
        else:
            print(f"✗ Failed to send evacuation alert")
        print()

        # Test alert 2: First Responder Alert
        print("[3/5] Sending first responder alert...")
        start_time = time.time() * 1000

        responder_alert = {
            'alert_id': 'RESP-001',
            'alert_type': 'FIRST_RESPONDER_UPDATE',
            'severity': 'CRITICAL',
            'unit_id': 'ENGINE-47',
            'location': 'Concow, CA',
            'latitude': 39.7444,
            'longitude': -121.5428,
            'message': 'URGENT: Fire behavior change - crowning observed',
            'fire_behavior': {
                'rate_of_spread': '15 chains/hour',
                'flame_length': '100+ feet',
                'spotting_distance': '0.5 miles',
                'direction': 'Southwest'
            },
            'escape_routes': ['Concow Road North', 'Jordan Hill Road'],
            'safety_zones': ['Concow Reservoir', 'Cleared field at mile marker 12'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        success = await handler.send_critical_alert(responder_alert, source_id="responder_system")
        end_time = time.time() * 1000
        latency = end_time - start_time

        if success:
            print(f"✓ Responder alert sent - Latency: {latency:.2f}ms")
        else:
            print(f"✗ Failed to send responder alert")
        print()

        # Test alert 3: Life Safety Warning
        print("[4/5] Sending life safety warning...")
        start_time = time.time() * 1000

        safety_alert = {
            'alert_id': 'SAFETY-001',
            'alert_type': 'LIFE_SAFETY_WARNING',
            'severity': 'CRITICAL',
            'location': 'Pulga, CA',
            'latitude': 39.7939,
            'longitude': -121.4531,
            'message': 'TRAPPED RESIDENTS - Immediate rescue needed',
            'trapped_count': 5,
            'location_details': '1234 Pulga Road - Surrounded by fire',
            'rescue_resources': ['CalFire Helicopter 301', 'Ground crew Engine 22'],
            'medical_needs': 'Elderly resident requires oxygen',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        success = await handler.send_critical_alert(safety_alert, source_id="safety_system")
        end_time = time.time() * 1000
        latency = end_time - start_time

        if success:
            print(f"✓ Life safety alert sent - Latency: {latency:.2f}ms")
        else:
            print(f"✗ Failed to send life safety alert")
        print()

        # Get metrics
        print("[5/5] Retrieving metrics...")
        metrics = handler.get_metrics()

        print("\n" + "="*60)
        print("TEST RESULTS")
        print("="*60)
        print(f"Total alerts sent: {metrics['alerts_sent']}")
        print(f"Total alerts failed: {metrics['alerts_failed']}")
        print(f"Average latency: {metrics['avg_latency_ms']:.2f}ms")
        print(f"Max latency: {metrics['max_latency_ms']:.2f}ms")
        print(f"Min latency: {metrics['min_latency_ms']:.2f}ms")

        if 'latency_percentiles' in metrics and metrics['latency_percentiles']:
            print(f"P50 latency: {metrics['latency_percentiles']['p50']:.2f}ms")
            print(f"P95 latency: {metrics['latency_percentiles']['p95']:.2f}ms")
            print(f"P99 latency: {metrics['latency_percentiles']['p99']:.2f}ms")

        # Check if we met the target
        if metrics['avg_latency_ms'] < 100:
            print(f"\n✓ SUCCESS: Average latency {metrics['avg_latency_ms']:.2f}ms < 100ms target")
        else:
            print(f"\n✗ WARNING: Average latency {metrics['avg_latency_ms']:.2f}ms exceeds 100ms target")

        # Health check
        is_healthy = handler.is_healthy()
        print(f"\nHandler health: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean shutdown
        print("\nShutting down handler...")
        await handler.stop()
        print("✓ Handler stopped successfully")


async def test_websocket_simulation():
    """Simulate WebSocket streaming for critical alerts"""
    print("\n" + "="*60)
    print("WEBSOCKET SIMULATION TEST")
    print("Simulating real-time WebSocket → Kafka streaming")
    print("="*60 + "\n")

    handler = CriticalAlertHandler(
        kafka_bootstrap_servers="localhost:9092",
        alert_topic="wildfire-critical-alerts",
        max_latency_ms=100
    )

    try:
        await handler.start()
        print("Handler started, simulating WebSocket stream...\n")

        # Simulate rapid-fire alerts
        latencies = []
        for i in range(10):
            start_time = time.time() * 1000

            alert = {
                'alert_id': f'WS-{i:03d}',
                'alert_type': 'WEBSOCKET_TEST',
                'severity': 'CRITICAL',
                'sequence': i,
                'message': f'WebSocket alert {i}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            success = await handler.send_critical_alert(alert, source_id="websocket_test")
            end_time = time.time() * 1000
            latency = end_time - start_time
            latencies.append(latency)

            print(f"Alert {i:2d}: {'✓' if success else '✗'} - Latency: {latency:.2f}ms")

            # Simulate WebSocket message interval
            await asyncio.sleep(0.1)  # 100ms between messages

        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)

        print("\n" + "-"*40)
        print(f"WebSocket simulation complete")
        print(f"Average latency: {avg_latency:.2f}ms")
        print(f"Max latency: {max_latency:.2f}ms")
        print(f"Min latency: {min_latency:.2f}ms")
        print(f"All under 100ms: {'✓ Yes' if max_latency < 100 else '✗ No'}")

    finally:
        await handler.stop()


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CRITICAL ALERT HANDLER TEST SUITE")
    print("Testing Priority 1 Enhancement: <1s Latency Alerts")
    print("="*60)

    # Test 1: Basic latency test
    await test_critical_alert_latency()

    print("\n" + "="*60 + "\n")

    # Test 2: WebSocket simulation
    await test_websocket_simulation()

    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Check if Kafka is available
    print("Note: This test requires Kafka to be running on localhost:9092")
    print("Run 'docker-compose up -d' if not already running\n")

    asyncio.run(main())