"""
Shared Prometheus metrics for data ingestion connectors
"""

from prometheus_client import Histogram, Counter

# Ingestion latency histogram
INGESTION_LATENCY = Histogram(
    'ingestion_latency_seconds',
    'Data ingestion latency in seconds',
    ['source', 'job'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# Validation counters
VALIDATION_TOTAL = Counter(
    'validation_total',
    'Total number of validation attempts',
    ['source', 'job']
)

VALIDATION_PASSED = Counter(
    'validation_passed_total',
    'Number of successful validations',
    ['source', 'job']
)

# Records processed counter
RECORDS_PROCESSED = Counter(
    'records_processed_total',
    'Total number of records processed',
    ['source', 'job']
)
