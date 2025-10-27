"""
Integration Tests for Priority 1 Enhancements
Tests critical alert handling (<1s latency) and offline buffering
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.streaming.critical_alert_handler import CriticalAlertHandler
from src.streaming.buffer_manager import get_buffer_manager, BufferManager
from src.streaming.stream_manager import StreamManager
from src.connectors.iot_mqtt_connector import IoTMQTTConnector


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.metrics = {}

    def record(self, test_name: str, passed: bool, details: str = ""):
        if passed:
            self.passed.append(test_name)
            print(f"✓ {test_name}: PASSED {details}")
        else:
            self.failed.append((test_name, details))
            print(f"✗ {test_name}: FAILED - {details}")

    def summary(self):
        total = len(self.passed) + len(self.failed)
        print("\n" + "="*60)
        print(f"TEST SUMMARY: {len(self.passed)}/{total} passed")
        if self.failed:
            print("\nFailed tests:")
            for name, reason in self.failed:
                print(f"  - {name}: {reason}")
        print("="*60 + "\n")


async def test_critical_alert_latency(results: TestResults):
    """Test 1: Verify critical alerts achieve <100ms latency"""
    print("\n" + "-"*50)
    print("TEST 1: Critical Alert Latency (<100ms)")
    print("-"*50)

    handler = CriticalAlertHandler(
        kafka_bootstrap_servers="localhost:9092",
        alert_topic="wildfire-critical-alerts",
        max_latency_ms=100
    )

    try:
        await handler.start()

        # Send 10 test alerts and measure latency
        latencies = []
        for i in range(10):
            start_time = time.time() * 1000

            alert = {
                'alert_id': f'TEST-{i:03d}',
                'alert_type': 'EVACUATION_ORDER',
                'severity': 'CRITICAL',
                'location': f'Test Location {i}',
                'message': f'Test evacuation order {i}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            success = await handler.send_critical_alert(alert, source_id="test")
            end_time = time.time() * 1000
            latency = end_time - start_time
            latencies.append(latency)

            if not success:
                results.record("Critical alert send", False, f"Alert {i} failed")
                return

            await asyncio.sleep(0.1)  # Small delay between alerts

        # Analyze latencies
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)

        results.metrics['critical_alert_latencies'] = latencies
        results.metrics['critical_alert_avg_ms'] = avg_latency
        results.metrics['critical_alert_max_ms'] = max_latency

        # Check if we met the target
        if avg_latency < 100:
            results.record(
                "Critical alert latency",
                True,
                f"(avg: {avg_latency:.2f}ms, max: {max_latency:.2f}ms)"
            )
        else:
            results.record(
                "Critical alert latency",
                False,
                f"Average {avg_latency:.2f}ms exceeds 100ms target"
            )

        # Check handler health
        is_healthy = handler.is_healthy()
        results.record("Critical handler health", is_healthy)

    except Exception as e:
        results.record("Critical alert test", False, str(e))

    finally:
        await handler.stop()


async def test_offline_buffering(results: TestResults):
    """Test 2: Verify offline buffering works correctly"""
    print("\n" + "-"*50)
    print("TEST 2: Offline Buffering")
    print("-"*50)

    buffer_manager = get_buffer_manager()
    await buffer_manager.start()

    try:
        # Create a test buffer
        flushed_messages = []

        async def mock_flush_callback(messages: List[Dict[str, Any]]) -> bool:
            """Mock flush callback that simulates Kafka send"""
            flushed_messages.extend(messages)
            return True

        buffer_id = buffer_manager.create_buffer(
            connector_id="test_001",
            connector_type="test",
            max_size=100,
            flush_callback=mock_flush_callback
        )

        # Test 2.1: Add messages to buffer
        test_messages = []
        for i in range(50):
            message = {
                'data': f'Test message {i}',
                'timestamp': datetime.now().isoformat(),
                'sequence': i
            }
            test_messages.append(message)
            success = buffer_manager.add_message(buffer_id, message.copy())

            if not success:
                results.record("Buffer add message", False, f"Failed at message {i}")
                return

        results.record("Buffer add messages", True, "50 messages added")

        # Test 2.2: Check buffer metrics
        metrics = buffer_manager.get_buffer_metrics(buffer_id)
        if metrics['current_size'] == 50:
            results.record("Buffer size tracking", True, f"Size: {metrics['current_size']}")
        else:
            results.record("Buffer size tracking", False, f"Expected 50, got {metrics['current_size']}")

        # Test 2.3: Flush buffer
        flushed_count = await buffer_manager.flush_buffer(buffer_id)
        if flushed_count == 50:
            results.record("Buffer flush", True, f"Flushed {flushed_count} messages")
        else:
            results.record("Buffer flush", False, f"Expected 50, flushed {flushed_count}")

        # Test 2.4: Verify flushed messages
        if len(flushed_messages) == 50:
            # Check message integrity
            for i, msg in enumerate(flushed_messages):
                if msg.get('sequence') != i:
                    results.record("Buffer message order", False, f"Wrong sequence at {i}")
                    return
            results.record("Buffer message integrity", True, "All messages in correct order")
        else:
            results.record("Buffer message integrity", False, f"Expected 50, got {len(flushed_messages)}")

        # Test 2.5: Buffer overflow handling
        overflow_buffer_id = buffer_manager.create_buffer(
            connector_id="overflow_test",
            connector_type="test",
            max_size=10,
            flush_callback=mock_flush_callback
        )

        # Add more than max_size messages
        for i in range(15):
            buffer_manager.add_message(overflow_buffer_id, {'data': f'Overflow {i}'})

        overflow_metrics = buffer_manager.get_buffer_metrics(overflow_buffer_id)
        if overflow_metrics['current_size'] == 10:
            results.record("Buffer overflow handling", True, "Maintained max size")
        else:
            results.record("Buffer overflow handling", False, f"Size {overflow_metrics['current_size']} exceeds max 10")

        if overflow_metrics['messages_dropped'] >= 5:
            results.record("Buffer drop tracking", True, f"Dropped {overflow_metrics['messages_dropped']} messages")
        else:
            results.record("Buffer drop tracking", False, f"Should have dropped 5+, got {overflow_metrics['messages_dropped']}")

    except Exception as e:
        results.record("Offline buffering test", False, str(e))

    finally:
        await buffer_manager.stop()


async def test_iot_connector_buffering(results: TestResults):
    """Test 3: Verify IoT MQTT connector buffering integration"""
    print("\n" + "-"*50)
    print("TEST 3: IoT Connector with Buffering")
    print("-"*50)

    # Create IoT connector with buffering enabled
    connector = IoTMQTTConnector(
        broker_host="localhost",
        broker_port=1883,
        enable_offline_buffer=True,
        buffer_max_size=100
    )

    try:
        # Test 3.1: Buffer initialization
        if connector.enable_offline_buffer:
            results.record("IoT buffer enabled", True)
        else:
            results.record("IoT buffer enabled", False, "Buffer not enabled")

        # Test 3.2: Simulate offline message buffering
        test_message = {
            'data': {'temperature': 25.5, 'humidity': 60},
            'topic': 'weather/station1/data',
            'source_id': 'iot_weather_stations'
        }

        # Simulate offline state
        connector.is_connected = False

        # Buffer message
        buffered = connector._buffer_message(test_message)
        if buffered:
            results.record("IoT message buffering", True)
        else:
            results.record("IoT message buffering", False, "Failed to buffer message")

        # Test 3.3: Check buffer metrics
        metrics = connector.get_buffer_metrics()
        if metrics['buffer_current_size'] == 1:
            results.record("IoT buffer metrics", True, f"Size: {metrics['buffer_current_size']}")
        else:
            results.record("IoT buffer metrics", False, f"Expected 1, got {metrics['buffer_current_size']}")

        # Test 3.4: Simulate connection restoration
        connector.is_connected = True
        connector.last_disconnection_time = datetime.now()

        # Mock Kafka producer for flush
        class MockKafkaProducer:
            async def send_batch_data(self, data, source_type, source_id):
                return True

        connector.kafka_producer = MockKafkaProducer()

        # Flush buffer
        flushed = await connector._flush_buffer()
        if flushed == 1:
            results.record("IoT buffer flush", True, f"Flushed {flushed} message")
        else:
            results.record("IoT buffer flush", False, f"Expected 1, flushed {flushed}")

        # Test 3.5: Buffer health check
        is_healthy = connector.is_buffer_healthy()
        results.record("IoT buffer health", is_healthy)

    except Exception as e:
        results.record("IoT connector buffering test", False, str(e))


async def test_stream_manager_routing(results: TestResults):
    """Test 4: Verify StreamManager routes critical alerts correctly"""
    print("\n" + "-"*50)
    print("TEST 4: StreamManager Critical Alert Routing")
    print("-"*50)

    manager = StreamManager()

    try:
        # Test 4.1: Critical source detection
        critical_sources = [
            "evacuation_system",
            "emergency_broadcast",
            "critical_fire_alerts",
            "life_safety_warnings"
        ]

        for source in critical_sources:
            is_critical = manager._is_critical_alert_source(source)
            if is_critical:
                results.record(f"Critical source detection ({source})", True)
            else:
                results.record(f"Critical source detection ({source})", False, "Not detected as critical")

        # Test 4.2: Non-critical source detection
        normal_sources = ["weather_station", "satellite_imagery", "historical_data"]

        for source in normal_sources:
            is_critical = manager._is_critical_alert_source(source)
            if not is_critical:
                results.record(f"Normal source detection ({source})", True)
            else:
                results.record(f"Normal source detection ({source})", False, "Wrongly detected as critical")

    except Exception as e:
        results.record("Stream manager routing test", False, str(e))


async def test_end_to_end_latency(results: TestResults):
    """Test 5: End-to-end latency test with all components"""
    print("\n" + "-"*50)
    print("TEST 5: End-to-End System Test")
    print("-"*50)

    try:
        # This would require full system setup
        # For now, we'll do a simplified version

        # Test 5.1: System components availability
        components_available = True
        reasons = []

        # Check if Kafka is available
        try:
            from aiokafka import AIOKafkaProducer
            producer = AIOKafkaProducer(bootstrap_servers="localhost:9092")
            await producer.start()
            await producer.stop()
        except:
            components_available = False
            reasons.append("Kafka not available")

        if components_available:
            results.record("System components", True, "All components available")
        else:
            results.record("System components", False, f"Missing: {', '.join(reasons)}")

        # Test 5.2: Configuration validation
        from pathlib import Path
        config_files = [
            Path("./config/critical_sources.yaml"),
            Path("./config/streaming_config.yaml")
        ]

        all_configs_exist = all(f.exists() for f in config_files)
        if all_configs_exist:
            results.record("Configuration files", True)
        else:
            missing = [str(f) for f in config_files if not f.exists()]
            results.record("Configuration files", False, f"Missing: {missing}")

    except Exception as e:
        results.record("End-to-end test", False, str(e))


async def run_all_tests():
    """Run all priority enhancement tests"""
    print("\n" + "="*60)
    print("PRIORITY 1 ENHANCEMENT TEST SUITE")
    print("Testing Critical Alerts and Offline Buffering")
    print("="*60)

    results = TestResults()

    # Run tests
    await test_critical_alert_latency(results)
    await test_offline_buffering(results)
    await test_iot_connector_buffering(results)
    await test_stream_manager_routing(results)
    await test_end_to_end_latency(results)

    # Print summary
    results.summary()

    # Print performance metrics
    if results.metrics:
        print("Performance Metrics:")
        print("-"*30)
        for key, value in results.metrics.items():
            if isinstance(value, list):
                print(f"  {key}: {len(value)} samples")
            elif isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")

    return len(results.failed) == 0


if __name__ == "__main__":
    print("\nNote: Some tests require Kafka (localhost:9092) and MQTT (localhost:1883)")
    print("Run 'docker-compose up -d' if not already running\n")

    # Run tests
    success = asyncio.run(run_all_tests())

    # Exit with appropriate code
    sys.exit(0 if success else 1)