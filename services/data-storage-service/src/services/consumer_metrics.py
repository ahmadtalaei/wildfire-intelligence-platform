"""
Prometheus metrics for Kafka consumer service
"""

from prometheus_client import Counter, Histogram, Gauge

# Message throughput metrics
MESSAGES_CONSUMED_TOTAL = Counter(
    'messages_consumed_total',
    'Total number of messages consumed from Kafka',
    ['topic', 'source', 'job']
)

MESSAGES_PROCESSED_SUCCESS = Counter(
    'messages_processed_success_total',
    'Number of successfully processed messages',
    ['topic', 'source', 'job']
)

MESSAGES_PROCESSED_FAILED = Counter(
    'messages_processed_failed_total',
    'Number of failed message processing attempts',
    ['topic', 'source', 'error_type', 'job']
)

# Processing latency
MESSAGE_PROCESSING_LATENCY = Histogram(
    'message_processing_latency_seconds',
    'Time taken to process a message',
    ['topic', 'source', 'job'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Consumer lag
CONSUMER_LAG = Gauge(
    'kafka_consumer_lag_messages',
    'Number of messages behind the latest offset',
    ['topic', 'partition', 'job']
)

# Duplicate detection
DUPLICATE_MESSAGES = Counter(
    'duplicate_messages_total',
    'Number of duplicate messages detected',
    ['topic', 'source', 'job']
)

# Data quality
DATA_QUALITY_SCORE = Gauge(
    'data_quality_score',
    'Data quality score for processed messages (0-1)',
    ['source', 'job']
)

# Database operations
DB_INSERT_SUCCESS = Counter(
    'db_insert_success_total',
    'Number of successful database inserts',
    ['table', 'source', 'job']
)

DB_INSERT_FAILED = Counter(
    'db_insert_failed_total',
    'Number of failed database inserts',
    ['table', 'source', 'error_type', 'job']
)

# Records ingested (for SLA tracking)
RECORDS_INGESTED_SUCCESS = Counter(
    'records_ingested_success_total',
    'Total records successfully ingested and stored',
    ['source', 'job']
)

# Ingestion throughput (for dashboard compatibility)
INGESTION_THROUGHPUT = Counter(
    'ingestion_throughput_total',
    'Total records ingested (throughput tracking)',
    ['source', 'job']
)

# Ingestion failures
INGESTION_FAILED = Counter(
    'ingestion_failed_total',
    'Total failed ingestion attempts',
    ['source', 'error_type', 'job']
)

# Duplicate detections (for SLA)
DUPLICATE_DETECTIONS = Counter(
    'duplicate_detections_total',
    'Number of duplicate records detected',
    ['source', 'job']
)

# Anomaly detection
ANOMALIES_DETECTED = Counter(
    'anomalies_detected_total',
    'Number of anomalies detected in data',
    ['source', 'anomaly_type', 'job']
)

# Kafka consumer lag (renamed for dashboard compatibility)
KAFKA_CONSUMER_LAG = Gauge(
    'kafka_consumer_lag',
    'Kafka consumer lag in messages',
    ['topic', 'partition', 'job']
)
