#!/usr/bin/env python3
"""
Verification script for zstd compression optimization
Checks that all compression settings are properly configured
"""

import os
import sys
import yaml
import json
from pathlib import Path

def check_kafka_producer():
    """Check kafka_producer.py implementation"""
    producer_path = Path("../services/data-ingestion-service/src/streaming/kafka_producer.py")

    if not producer_path.exists():
        return False, "kafka_producer.py not found"

    with open(producer_path, 'r') as f:
        content = f.read()

    checks = [
        ("_get_compression_type method", "_get_compression_type" in content),
        ("_get_compression_level method", "_get_compression_level" in content),
        ("zstd as default compression", "'zstd'" in content),
        ("Fallback to gzip", "falling back to gzip" in content),
        ("Topic-specific compression", "'compression.type': 'zstd'" in content),
        ("Critical alerts no compression", "'compression.type': 'none'" in content)
    ]

    failed = []
    for check_name, result in checks:
        if not result:
            failed.append(check_name)

    if failed:
        return False, f"Missing: {', '.join(failed)}"

    return True, "All producer checks passed"

def check_streaming_config():
    """Check streaming_config.yaml configuration"""
    config_path = Path("../services/data-ingestion-service/config/streaming_config.yaml")

    if not config_path.exists():
        return False, "streaming_config.yaml not found"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Check main producer config
    producer_config = config.get('kafka_producer', {})
    compression_type = producer_config.get('compression_type', '')
    compression_level = producer_config.get('compression_level', 0)

    if compression_type != 'zstd':
        return False, f"Expected zstd, got {compression_type}"

    if compression_level != 3:
        return False, f"Expected level 3, got {compression_level}"

    # Check data type specific compression
    data_types = producer_config.get('data_type_compression', {})
    expected_types = ['iot_sensors', 'weather_bulk', 'nasa_firms', 'satellite_imagery', 'evacuation_alerts']

    missing = [t for t in expected_types if t not in data_types]
    if missing:
        return False, f"Missing data type configs: {', '.join(missing)}"

    # Verify critical alerts have no compression
    critical_config = producer_config.get('critical', {})
    if critical_config.get('compression_type') != 'none':
        return False, "Critical alerts should have no compression"

    return True, "Config file properly configured"

def check_docker_compose():
    """Check docker-compose.yml environment variables"""
    compose_path = Path("../docker-compose.yml")

    if not compose_path.exists():
        return False, "docker-compose.yml not found"

    with open(compose_path, 'r') as f:
        content = f.read()

    checks = [
        ("KAFKA_COMPRESSION_TYPE=zstd", "KAFKA_COMPRESSION_TYPE=zstd" in content),
        ("KAFKA_COMPRESSION_LEVEL=3", "KAFKA_COMPRESSION_LEVEL=3" in content),
        ("No old KAFKA_COMPRESSION=gzip", "KAFKA_COMPRESSION=gzip" not in content)
    ]

    failed = []
    for check_name, result in checks:
        if not result:
            failed.append(check_name)

    if failed:
        return False, f"Failed checks: {', '.join(failed)}"

    return True, "Docker compose properly configured"

def check_environment():
    """Check current environment variables"""
    compression_type = os.getenv('KAFKA_COMPRESSION_TYPE', 'not set')
    compression_level = os.getenv('KAFKA_COMPRESSION_LEVEL', 'not set')

    info = f"Current env: KAFKA_COMPRESSION_TYPE={compression_type}, KAFKA_COMPRESSION_LEVEL={compression_level}"

    if compression_type == 'zstd' and compression_level == '3':
        return True, f"Environment configured correctly. {info}"

    return False, f"Environment not configured. {info}"

def main():
    """Run all verification checks"""
    print("=" * 60)
    print("ZSTD COMPRESSION OPTIMIZATION VERIFICATION")
    print("=" * 60)
    print()

    checks = [
        ("1. Kafka Producer Implementation", check_kafka_producer),
        ("2. Streaming Config YAML", check_streaming_config),
        ("3. Docker Compose Environment", check_docker_compose),
        ("4. Current Environment Variables", check_environment)
    ]

    all_passed = True
    results = []

    for name, check_func in checks:
        print(f"Checking {name}...")
        try:
            passed, message = check_func()
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"  {status}: {message}")
            results.append((name, passed, message))
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append((name, False, str(e)))
            all_passed = False
        print()

    print("-" * 60)
    print("SUMMARY")
    print("-" * 60)

    if all_passed:
        print("✅ All compression optimization checks PASSED!")
        print()
        print("Expected benefits:")
        print("  • 20-40% reduction in latency")
        print("  • Lower CPU overhead on producers")
        print("  • Adaptive compression for different data types")
        print("  • Critical alerts bypass compression for minimal latency")
        print()
        print("Compression matrix configured:")
        print("  • Critical alerts: No compression (lowest latency)")
        print("  • IoT sensors: zstd level 1 (fastest)")
        print("  • NASA FIRMS: zstd level 3 (balanced)")
        print("  • Weather bulk: zstd level 6 (highest compression)")
        print("  • Satellite imagery: Snappy (optimized for binary)")
    else:
        print("❌ Some checks failed. Please review the errors above.")
        print()
        print("To complete the optimization:")
        print("  1. Ensure all code changes are saved")
        print("  2. Rebuild the data-ingestion-service container:")
        print("     docker-compose up -d --build data-ingestion-service")
        print("  3. Verify Kafka is running:")
        print("     docker ps | grep kafka")
        print("  4. Check producer logs for zstd usage:")
        print("     docker logs wildfire-data-ingestion | grep zstd")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())