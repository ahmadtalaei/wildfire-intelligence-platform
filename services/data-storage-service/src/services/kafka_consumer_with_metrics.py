# Comprehensive instrumentation with Prometheus metrics
# This is a targeted patch - add these imports at the top after existing imports

import time
from .consumer_metrics import (
    MESSAGES_CONSUMED_TOTAL, MESSAGES_PROCESSED_SUCCESS, MESSAGES_PROCESSED_FAILED,
    MESSAGE_PROCESSING_LATENCY, DB_INSERT_SUCCESS, DB_INSERT_FAILED, RECORDS_INGESTED_SUCCESS
)
