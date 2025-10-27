"""Kafka producer for wildfire intelligence real-time data streaming"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Tuple, Union
import uuid
import time

# Import Prometheus metrics
try:
    from ..connectors.metrics import (
        INGESTION_LATENCY,
        VALIDATION_TOTAL,
        VALIDATION_PASSED,
        RECORDS_PROCESSED
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("Prometheus metrics not available")

try:
    import aiokafka
    from aiokafka import AIOKafkaProducer
    from aiokafka.errors import KafkaError
except ImportError:
    aiokafka = None
    AIOKafkaProducer = None
    KafkaError = Exception

# Import binary serialization components
try:
    from .binary_serializer import BinaryImageSerializer
    from .image_chunk_manager import ImageChunkManager
    from .s3_reference_handler import S3ReferenceHandler
except ImportError:
    BinaryImageSerializer = None
    ImageChunkManager = None
    S3ReferenceHandler = None

# Import centralized geographic bounds with configuration fallback
try:
    from ..geo_config.geographic_bounds import CALIFORNIA_BOUNDS
except ImportError:
    try:
        from geo_config.geographic_bounds import CALIFORNIA_BOUNDS
    except ImportError:
        # Fallback bounds - use hardcoded USGS values if config not available
        CALIFORNIA_BOUNDS = {
            'lat_min': 32.534156,   # Southern border (Imperial County)
            'lat_max': 42.009518,   # Northern border (Modoc County)
            'lon_min': -124.482003, # Western border (Del Norte County)
            'lon_max': -114.131211  # Eastern border (Imperial County)
        }

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaDataProducer:
    """Enhanced Kafka producer for wildfire intelligence platform"""

    def __init__(self, bootstrap_servers: str, client_id: str = None):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id or f"wildfire-ingestion-{uuid.uuid4().hex[:8]}"
        self.producer = None
        self.binary_producer = None  # Separate producer for binary data
        self.is_started = False

        # Get compression type from environment or use snappy as default
        self.compression_type = self._get_compression_type()

        # Initialize binary handling components if available
        self.binary_serializer = BinaryImageSerializer() if BinaryImageSerializer else None
        self.chunk_manager = None  # Initialized on start
        self.s3_handler = None  # Initialized on start

        # OPTIMIZED PARTITION CONFIGURATION
        # Based on analysis of data patterns and 10,000-20,000 events/sec target
        # Total partitions: ~85 (within single-broker comfort zone)

        # Binary data topic configuration (Special handling for large files)
        self.binary_topics = {
            'wildfire-satellite-imagery-metadata': {
                'partitions': 4,  # Small JSON metadata only
                'config': {'compression.type': 'gzip', 'compression.level': '3', 'max.message.bytes': '1048576'}  # 1MB
            },
            'wildfire-satellite-imagery-binary': {
                'partitions': 10,  # Increased for parallel processing of large images
                'config': {'compression.type': 'gzip', 'compression.level': '1', 'max.message.bytes': '20971520'}  # 20MB
            },
            'wildfire-satellite-imagery-chunks': {
                'partitions': 8,  # Increased for better reassembly parallelism
                'config': {'compression.type': 'gzip', 'compression.level': '1', 'max.message.bytes': '10485760'}  # 10MB
            }
        }

        # Dynamic topic configuration based on data patterns
        self.default_topic_config = {
            'partitions': 4,
            'replication_factor': 1,  # Single broker deployment
            'config': {'compression.type': self.compression_type}
        }

        # Topic-specific overrides with OPTIMIZED partitions and compression
        self.topic_overrides = {
            # Critical Alert Topics (Low latency, ordered processing)
            'critical_alerts': {
                'partitions': 3,  # Small for ordered processing within incidents
                'config': {'compression.type': 'none', 'max.message.bytes': '1048576'}
            },
            'evacuation_orders': {
                'partitions': 3,
                'config': {'compression.type': 'none', 'max.message.bytes': '1048576'}
            },

            # High-Volume Streaming Topics
            'iot_sensors': {
                'partitions': 16,  # INCREASED from 12 - Highest volume, thousands of sensors
                'config': {'compression.type': 'gzip', 'compression.level': '1', 'segment.ms': '3600000'}
            },
            'weather_data': {
                'partitions': 12,  # INCREASED from 8 - Multiple sources, 30-sec updates
                'config': {'compression.type': 'gzip', 'compression.level': '3', 'segment.ms': '3600000'}
            },
            'weather_processed': {
                'partitions': 12,  # Match weather_data for pipeline consistency
                'config': {'compression.type': 'gzip', 'compression.level': '3'}
            },

            # Moderate-Volume Topics
            'nasa_firms': {
                'partitions': 6,  # INCREASED from 4 - Satellite passes every 15 min
                'config': {'compression.type': 'gzip', 'compression.level': '3', 'retention.ms': '604800000'}
            },
            'weather_bulk': {
                'partitions': 8,  # INCREASED from 6 - Large GRIB files, parallel processing
                'config': {'compression.type': 'gzip', 'compression.level': '6', 'max.message.bytes': '10485760'}
            },
            'air_quality': {
                'partitions': 6,  # Air quality sensors (PurpleAir, AirNow)
                'config': {'compression.type': 'gzip', 'compression.level': '3'}
            },

            # Satellite/Imagery Topics
            'satellite_raw': {
                'partitions': 8,  # Raw satellite data ingestion
                'config': {'compression.type': 'gzip', 'compression.level': '1', 'max.message.bytes': '52428800'}
            },
            'satellite_processed': {
                'partitions': 6,  # Processed satellite data
                'config': {'compression.type': 'gzip', 'compression.level': '3'}
            },

            # Processing Pipeline Topics
            'sensors_processed': {
                'partitions': 8,  # Processed sensor data
                'config': {'compression.type': 'gzip', 'compression.level': '3'}
            },
            'alerts_generated': {
                'partitions': 4,  # System-generated alerts
                'config': {'compression.type': 'gzip', 'compression.level': '3'}
            },
            'fire_predictions': {
                'partitions': 6,  # ML model predictions
                'config': {'compression.type': 'gzip', 'compression.level': '3'}
            },

            # Dead Letter Queue Topics
            'dlq_failed_messages': {
                'partitions': 3,  # Error handling
                'config': {'compression.type': 'gzip', 'compression.level': '3', 'retention.ms': '2592000000'}
            },
            'dlq_retry_queue': {
                'partitions': 3,  # Retry queue
                'config': {'compression.type': 'gzip', 'compression.level': '3', 'retention.ms': '604800000'}
            },

            # Social Media Topics
            'social_raw': {
                'partitions': 4,  # Raw social media data
                'config': {'compression.type': 'gzip', 'compression.level': '3'}
            },
            'social_processed': {
                'partitions': 4,  # Processed social data
                'config': {'compression.type': 'gzip', 'compression.level': '3'}
            }
        }

        # Partition count mapping for runtime topic determination
        self.topic_partition_map = {
            'wildfire-critical-alerts': 3,
            'wildfire-evacuation-orders': 3,
            'wildfire-iot-sensors': 16,
            'wildfire-weather-data': 12,
            'wildfire-weather-processed': 12,
            'wildfire-nasa-firms': 6,
            'wildfire-weather-bulk': 8,
            'wildfire-air-quality': 6,
            'wildfire-satellite-raw': 8,
            'wildfire-satellite-processed': 6,
            'wildfire-sensors-processed': 8,
            'wildfire-alerts-generated': 4,
            'wildfire-fire-predictions': 6,
            'wildfire-satellite-imagery-binary': 10,
            'wildfire-satellite-imagery-chunks': 8,
            'wildfire-satellite-imagery-metadata': 4,
            'wildfire-dlq-failed-messages': 3,
            'wildfire-dlq-retry-queue': 3,
            'wildfire-social-raw': 4,
            'wildfire-social-processed': 4
        }

    def _get_compression_type(self):
        """Get Kafka compression type with gzip as default (only reliable option)

        Note: aiokafka requires compression codec libraries at C level, not just Python wrappers.
        While Python packages like python-snappy, lz4, and zstandard are available,
        aiokafka cannot find their codecs. Only gzip works reliably as it's built into Python.

        Users can set KAFKA_COMPRESSION_TYPE env var to try other codecs (lz4, snappy, none).
        """
        import os

        # Check environment variable first - allows users to try other codecs
        env_compression = os.getenv('KAFKA_COMPRESSION_TYPE', '').lower()
        supported_types = ['gzip', 'lz4', 'snappy', 'none']

        if env_compression in supported_types:
            logger.info(f"Using {env_compression} compression from environment variable")
            return env_compression

        # Default to gzip - only compression that reliably works with aiokafka
        # Built-in to Python, no external codec libraries required
        # Compression ratio: 60-70%, Speed: moderate (acceptable for most use cases)
        logger.info("Using gzip compression (built-in, reliable, 60-70% compression ratio)")
        return 'gzip'

    def _get_compression_level(self):
        """Get zstd compression level (1-22, default 3 for balance)"""
        import os
        level = os.getenv('KAFKA_COMPRESSION_LEVEL', '3')
        try:
            level_int = int(level)
            # Clamp to valid range
            return max(1, min(22, level_int))
        except ValueError:
            return 3  # Default balanced level

    def _is_zstd_available(self) -> bool:
        """Check if zstd compression is available"""
        try:
            import zstandard
            return True
        except ImportError:
            return False

    async def start(self):
        """Start the Kafka producer"""
        if not aiokafka:
            logger.error("aiokafka not available - install with: pip install aiokafka")
            return False

        try:
            # Start main JSON producer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=self._serialize_value,
                key_serializer=self._serialize_key,
                compression_type=self.compression_type,
                max_batch_size=32768,  # Increased from 16384 for large batches
                linger_ms=100,  # Increased from 10ms to allow better batching
                max_request_size=2097152,  # Increased to 2MB from 1MB
                retry_backoff_ms=100,
                request_timeout_ms=120000,  # Increased from 30s to 120s for large ERA5 batches
                acks='all',  # Wait for all replicas
                enable_idempotence=True  # Prevent duplicates
            )

            await self.producer.start()

            # Start binary producer for images (no JSON serializer)
            if self.binary_serializer:
                self.binary_producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    client_id=f"{self.client_id}-binary",
                    value_serializer=None,  # No serializer - raw bytes
                    key_serializer=self._serialize_key,
                    compression_type=self.compression_type,  # Use same compression as main producer
                    max_batch_size=65536,  # Larger batch for images
                    linger_ms=200,  # More batching for efficiency
                    max_request_size=20971520,  # 20MB for large images
                    retry_backoff_ms=100,
                    request_timeout_ms=180000,  # 3 minutes for large images
                    acks='all',
                    enable_idempotence=True
                )
                await self.binary_producer.start()
                logger.info("Binary Kafka producer started for image handling")

            # Initialize chunk manager if available
            if ImageChunkManager:
                self.chunk_manager = ImageChunkManager(
                    chunk_size_bytes=5 * 1024 * 1024,  # 5MB chunks
                    reassembly_timeout_seconds=300  # 5 minutes
                )
                await self.chunk_manager.start()
                logger.info("Image chunk manager initialized")

            # Initialize S3 handler if available (requires minio/boto3 packages)
            if S3ReferenceHandler:
                try:
                    import os
                    # Only initialize if MinIO endpoint is configured
                    if os.getenv('MINIO_ENDPOINT'):
                        self.s3_handler = S3ReferenceHandler(
                            storage_type='minio',
                            bucket_name='wildfire-satellite-imagery',
                            compress_before_upload=True
                        )
                        logger.info("S3 reference handler initialized for MinIO")
                    else:
                        logger.info("S3 handler skipped - no MINIO_ENDPOINT configured")
                        self.s3_handler = None
                except Exception as e:
                    logger.warning(f"Failed to initialize S3 handler: {e} - Large images will use chunking instead")
                    self.s3_handler = None

            self.is_started = True
            logger.info(f"Kafka producer started successfully: {self.client_id}, bootstrap_servers={self.bootstrap_servers}")
            return True

        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            return False
    
    async def stop(self):
        """Stop the Kafka producer"""
        try:
            if self.producer and self.is_started:
                await self.producer.stop()
                logger.info("Main Kafka producer stopped")

            if self.binary_producer:
                await self.binary_producer.stop()
                logger.info("Binary Kafka producer stopped")

            if self.chunk_manager:
                await self.chunk_manager.stop()
                logger.info("Chunk manager stopped")

            self.is_started = False
            logger.info("All Kafka producers stopped")
        except Exception as e:
            logger.error(f"Error stopping Kafka producer: {e}")
    
    async def health_check(self) -> bool:
        """Check if Kafka producer is healthy"""
        if not self.is_started or not self.producer:
            return False

        try:
            # Check if producer client is connected
            return self.producer.client.bootstrap_connected()
        except Exception as e:
            logger.debug(f"Kafka health check failed: {e}")
            # If the producer is started and can send messages, consider it healthy
            return self.is_started and self.producer is not None
    
    async def send_batch_data(self, data: List[Dict[str, Any]], source_type: str = None, source_id: str = None) -> bool:
        """Send batch data to appropriate Kafka topics using chunked sending for large batches"""
        if not self.is_started:
            logger.error("Kafka producer not started")
            return False

        batch_start_time = time.time()

        try:
            # Separate image data from regular data
            image_records = []
            regular_records = []

            for record in data:
                # Check if record contains image data
                if self.binary_serializer and self.binary_serializer.is_image_data(record):
                    image_records.append(record)
                else:
                    regular_records.append(record)

            # Send image records via binary pipeline
            if image_records:
                for img_record in image_records:
                    image_data = img_record.get('image_data') or img_record.get('image_bytes') or img_record.get('binary_data')
                    # Remove binary data from metadata
                    metadata = {k: v for k, v in img_record.items()
                               if k not in ['image_data', 'image_bytes', 'binary_data']}
                    await self.send_satellite_image(image_data, metadata, source_id)

            # Send regular records normally
            if not regular_records:
                return True  # All were images

            # For large batches, send in chunks to avoid overwhelming Kafka
            CHUNK_SIZE = 500  # Send 500 records at a time
            total_records = len(regular_records)
            total_failed = 0

            for chunk_start in range(0, total_records, CHUNK_SIZE):
                chunk_end = min(chunk_start + CHUNK_SIZE, total_records)
                chunk = regular_records[chunk_start:chunk_end]

                send_tasks = []
                for record in chunk:
                    topic = self._determine_topic(record, source_type, source_id)
                    key = self._generate_partition_key(record)

                    # Add metadata
                    enriched_record = self._enrich_record(record, source_type, source_id)

                    # Send async
                    send_task = self.producer.send(
                        topic=topic,
                        value=enriched_record,
                        key=key
                    )
                    send_tasks.append(send_task)

                # Wait for chunk to complete
                results = await asyncio.gather(*send_tasks, return_exceptions=True)

                # Check for exceptions in this chunk
                chunk_failed = 0
                chunk_succeeded = 0
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to send record {chunk_start + i} to Kafka: {result}")
                        chunk_failed += 1

                        # Record failed validation
                        if METRICS_AVAILABLE and source_id:
                            try:
                                VALIDATION_TOTAL.labels(source=source_id, job='data-ingestion-service').inc()
                                # Don't increment VALIDATION_PASSED for failures
                            except Exception:
                                pass
                    else:
                        chunk_succeeded += 1

                        # Record metrics for successfully sent records
                        if METRICS_AVAILABLE and source_id:
                            try:
                                # Calculate latency from ingestion_timestamp to now
                                record_with_meta = chunk[i]
                                ingestion_ts = record_with_meta.get('ingestion_metadata', {}).get('ingestion_timestamp')
                                if ingestion_ts:
                                    try:
                                        ingest_time = datetime.fromisoformat(ingestion_ts.replace('Z', '+00:00'))
                                        latency = (datetime.now(timezone.utc) - ingest_time).total_seconds()
                                        INGESTION_LATENCY.labels(source=source_id, job='data-ingestion-service').observe(latency)
                                    except Exception:
                                        pass  # Skip if timestamp parsing fails

                                # Count records processed and validated (success)
                                RECORDS_PROCESSED.labels(source=source_id, job='data-ingestion-service').inc()
                                VALIDATION_TOTAL.labels(source=source_id, job='data-ingestion-service').inc()
                                VALIDATION_PASSED.labels(source=source_id, job='data-ingestion-service').inc()
                            except Exception as e:
                                logger.debug(f"Failed to record metrics: {e}")

                total_failed += chunk_failed

                # Flush after each chunk
                await self.producer.flush()

                if chunk_failed == 0:
                    logger.info(f"Successfully sent chunk {chunk_start}-{chunk_end-1} ({len(chunk)} records) to Kafka")
                else:
                    logger.warning(f"Sent chunk {chunk_start}-{chunk_end-1} with {chunk_failed}/{len(chunk)} failures")

            if total_failed > 0:
                logger.error(f"Failed to send {total_failed}/{total_records} total records to Kafka")
                return False

            logger.info(f"Successfully sent all {total_records} records to Kafka")

            # Record batch-level metrics
            if METRICS_AVAILABLE and source_id:
                try:
                    batch_duration = time.time() - batch_start_time
                    # Record overall batch latency
                    INGESTION_LATENCY.labels(source=source_id, job='data-ingestion-service').observe(batch_duration)
                except Exception as e:
                    logger.debug(f"Failed to record batch metrics: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to send batch data to Kafka: {e}")
            return False
    
    async def send_file_data(self, data: List[Dict[str, Any]], filename: str, file_type: str = None) -> bool:
        """Send file-based data to Kafka with file metadata"""
        if not self.is_started:
            logger.error("Kafka producer not started")
            return False
        
        try:
            # Determine file type from filename if not provided
            if not file_type:
                file_type = self._detect_file_type(filename)
            
            send_tasks = []
            batch_id = str(uuid.uuid4())
            
            for i, record in enumerate(data):
                topic = self._determine_topic_for_file(record, file_type, filename)
                key = f"{filename}_{i}"
                
                # Add file metadata
                enriched_record = self._enrich_file_record(
                    record, filename, file_type, batch_id, i, len(data)
                )
                
                send_task = self.producer.send(
                    topic=topic,
                    value=enriched_record,
                    key=key
                )
                send_tasks.append(send_task)
            
            # Wait for all sends
            await asyncio.gather(*send_tasks, return_exceptions=True)
            await self.producer.flush()
            
            logger.info(f"Successfully sent file data: {filename} ({len(data)} records)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send file data to Kafka: {e}")
            return False
    
    async def send_real_time_data(self, record: Dict[str, Any], source_type: str, source_id: str) -> bool:
        """Send single real-time record to Kafka"""
        if not self.is_started:
            logger.error("Kafka producer not started")
            return False
        
        try:
            topic = self._determine_topic(record, source_type, source_id)
            key = self._generate_partition_key(record)
            enriched_record = self._enrich_record(record, source_type, source_id, real_time=True)
            
            await self.producer.send(
                topic=topic,
                value=enriched_record,
                key=key
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send real-time data to Kafka: {e}")
            return False
    
    async def send_satellite_image(
        self,
        image_data: Union[bytes, Dict[str, Any]],
        metadata: Dict[str, Any],
        source_id: str,
        force_s3: bool = False
    ) -> bool:
        """
        Send satellite image data with intelligent routing based on size

        Args:
            image_data: Raw image bytes or dict containing image data
            metadata: Image metadata (location, timestamp, sensor info)
            source_id: Source identifier
            force_s3: Force upload to S3 regardless of size

        Returns:
            True if successful, False otherwise
        """
        if not self.is_started:
            logger.error("Kafka producer not started")
            return False

        if not self.binary_serializer:
            logger.warning("Binary serializer not available, falling back to JSON")
            return await self.send_batch_data([{'image_data': image_data, **metadata}], 'satellite', source_id)

        try:
            # Extract image bytes if in dict format
            if isinstance(image_data, dict):
                image_bytes = image_data.get('image_data') or image_data.get('image_bytes') or image_data.get('binary_data')
                if not image_bytes:
                    logger.error("No image data found in dict")
                    return False
            else:
                image_bytes = image_data

            # Ensure we have bytes
            if not isinstance(image_bytes, bytes):
                logger.error(f"Image data must be bytes, got {type(image_bytes)}")
                return False

            image_size = len(image_bytes)
            logger.info(f"Processing satellite image: {image_size} bytes from {source_id}")

            # Determine routing strategy based on size
            if force_s3 or (self.s3_handler and self.s3_handler.should_use_s3(image_size)):
                # Very large image (>100MB) - upload to S3
                return await self._send_image_via_s3(image_bytes, metadata, source_id)

            elif self.chunk_manager and self.s3_handler and self.s3_handler.should_use_chunking(image_size):
                # Large image (20-100MB) - use chunking
                return await self._send_image_via_chunks(image_bytes, metadata, source_id)

            else:
                # Small/medium image (<20MB) - send directly
                return await self._send_image_directly(image_bytes, metadata, source_id)

        except Exception as e:
            logger.error(f"Failed to send satellite image: {e}", exc_info=True)
            return False

    async def _send_image_directly(
        self,
        image_data: bytes,
        metadata: Dict[str, Any],
        source_id: str
    ) -> bool:
        """Send image directly through Kafka (for images <20MB)"""
        try:
            # Serialize image and metadata
            metadata_bytes, image_packet, correlation_id = self.binary_serializer.serialize_image(
                image_data, metadata
            )

            # Send metadata to metadata topic
            metadata_topic = 'wildfire-satellite-imagery-metadata'
            await self.producer.send(
                topic=metadata_topic,
                value={'metadata': json.loads(metadata_bytes), 'correlation_id': correlation_id},
                key=correlation_id
            )

            # Send binary data to binary topic
            binary_topic = 'wildfire-satellite-imagery-binary'
            await self.binary_producer.send(
                topic=binary_topic,
                value=image_packet,
                key=correlation_id
            )

            await self.producer.flush()
            await self.binary_producer.flush()

            logger.info(
                f"Sent image directly: {len(image_data)} bytes, "
                f"correlation_id: {correlation_id}, source: {source_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send image directly: {e}")
            return False

    async def _send_image_via_chunks(
        self,
        image_data: bytes,
        metadata: Dict[str, Any],
        source_id: str
    ) -> bool:
        """Send image via chunks (for images 20-100MB)"""
        try:
            # Create chunks
            chunks = self.chunk_manager.create_chunks(image_data, metadata)

            # Send metadata first
            metadata_topic = 'wildfire-satellite-imagery-metadata'
            await self.producer.send(
                topic=metadata_topic,
                value={
                    'metadata': metadata,
                    'chunked': True,
                    'total_chunks': len(chunks),
                    'image_id': chunks[0].image_id,
                    'source_id': source_id
                },
                key=chunks[0].image_id
            )

            # Send chunks to chunks topic
            chunks_topic = 'wildfire-satellite-imagery-chunks'
            for chunk in chunks:
                chunk_bytes = self.chunk_manager.serialize_chunk(chunk)
                await self.binary_producer.send(
                    topic=chunks_topic,
                    value=chunk_bytes,
                    key=f"{chunk.image_id}_{chunk.sequence}"
                )

            await self.producer.flush()
            await self.binary_producer.flush()

            logger.info(
                f"Sent image via {len(chunks)} chunks: {len(image_data)} bytes, "
                f"image_id: {chunks[0].image_id}, source: {source_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send image via chunks: {e}")
            return False

    async def _send_image_via_s3(
        self,
        image_data: bytes,
        metadata: Dict[str, Any],
        source_id: str
    ) -> bool:
        """Upload image to S3 and send reference (for images >100MB)"""
        try:
            # Upload to S3
            s3_url, enhanced_metadata = await self.s3_handler.upload_image(
                image_data, metadata
            )

            # Create reference metadata for Kafka
            reference_metadata = self.s3_handler.create_reference_metadata(
                s3_url, metadata, len(image_data),
                enhanced_metadata['checksum']
            )

            # Send only metadata with S3 reference
            metadata_topic = 'wildfire-satellite-imagery-metadata'
            await self.producer.send(
                topic=metadata_topic,
                value=reference_metadata,
                key=reference_metadata.get('image_id', str(uuid.uuid4()))
            )

            await self.producer.flush()

            logger.info(
                f"Uploaded image to S3: {len(image_data)} bytes, "
                f"s3_url: {s3_url}, source: {source_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send image via S3: {e}")
            return False

    async def send_alert(self, alert_data: Dict[str, Any], severity: str = 'medium') -> bool:
        """Send wildfire alert to appropriate alert topic"""
        if not self.is_started:
            logger.error("Kafka producer not started")
            return False
        
        try:
            topic = f"wildfire-alerts-{severity.lower()}"
            key = alert_data.get('alert_id', str(uuid.uuid4()))
            
            # Add alert metadata
            alert_record = {
                **alert_data,
                'alert_id': key,
                'severity': severity,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'producer_id': self.client_id
            }
            
            await self.producer.send(
                topic=topic,
                value=alert_record,
                key=key
            )
            
            logger.info(f"Sent {severity} severity alert: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert to Kafka: {e}")
            return False
    
    def _determine_topic(self, record: Dict[str, Any], source_type: str = None, source_id: str = None) -> str:
        """Determine the appropriate Kafka topic for the record based on EXACT source_id patterns"""
        try:
            # Check record data type first
            data_type = record.get('data_type', '').lower()

            # Satellite imagery routing (PNG/binary data)
            if data_type == 'satellite_image' or data_type == 'satellite_imagery':
                return 'wildfire-satellite-imagery'

            # PRIORITY 1: Weather alerts get dedicated topic for parallel processing (time-critical)
            if record.get('alert_id') or record.get('event'):
                # Detected weather alert - send to dedicated alerts topic
                return 'wildfire-weather-alerts'

            # PRIORITY 2: High-volume bulk weather data gets separate topic to avoid blocking alerts
            # ERA5, GFS, NAM forecasts create massive backlogs - process separately
            if source_id:
                source_lower = source_id.lower()
                # High-volume bulk data sources
                if any(keyword in source_lower for keyword in ['era5', 'gfs', 'nam', 'gridpoint']):
                    return 'wildfire-weather-bulk'

            # Route based on EXACT source_id patterns to match connector routing
            if source_id:
                source_lower = source_id.lower()

                # NASA FIRMS sources: firms_*, landsat_nrt
                if source_lower.startswith(('firms_', 'landsat_nrt')):
                    if data_type == 'satellite_image':
                        return 'wildfire-satellite-imagery'
                    else:
                        return 'wildfire-nasa-firms'

                # Satellite sources: sat_*
                elif source_lower.startswith('sat_'):
                    if data_type == 'satellite_image':
                        return 'wildfire-satellite-imagery'
                    else:
                        return 'wildfire-satellite-data'

                # NOAA weather sources: noaa_* (real-time station data, not bulk)
                elif source_lower.startswith('noaa_'):
                    return 'wildfire-weather-data'

                # Weather sources: wx_* (real-time, not bulk)
                elif source_lower.startswith('wx_'):
                    return 'wildfire-weather-data'

                # IoT sources: iot_*
                elif source_lower.startswith('iot_'):
                    return 'wildfire-iot-sensors'

                # FireSat sources: firesat_*
                elif source_lower.startswith('firesat_'):
                    return 'wildfire-nasa-firms'  # Use same topic as other fire detection satellites

                # AirNow air quality: airnow_*, purpleair_*
                elif source_lower.startswith(('airnow_', 'purpleair_')):
                    return 'wildfire-sensor-data'

            # Fallback to data_type or source_type routing (legacy support)
            if data_type == 'weather' or source_type == 'weather':
                return 'wildfire-weather-data'
            elif data_type == 'iot_sensor' or source_type == 'sensor':
                return 'wildfire-iot-sensors'
            elif data_type == 'fire_incident' or source_type == 'nasa_firms':
                return 'wildfire-incidents'
            elif data_type == 'air_quality' or source_type == 'air_quality':
                return 'wildfire-sensor-data'

            # Default topic
            return 'wildfire-nasa-firms'

        except Exception:
            return 'wildfire-nasa-firms'  # Safe default
    
    def _determine_topic_for_file(self, record: Dict[str, Any], file_type: str, filename: str) -> str:
        """Determine topic for file-based data using exact pattern matching"""
        filename_lower = filename.lower()

        # Weather data files (GRIB format, GFS model data)
        if file_type in ['grib', 'grib2'] or filename_lower.startswith('gfs_'):
            return 'wildfire-weather-data'

        # Satellite/FIRMS data files
        elif file_type in ['hdf', 'netcdf']:
            # NASA FIRMS fire detection files
            if (filename_lower.startswith(('firms_', 'viirs_', 'modis_')) or
                'firms' in filename_lower or 'fire' in filename_lower):
                return 'wildfire-nasa-firms'
            # General satellite data files
            elif (filename_lower.startswith(('landsat_', 'sentinel_', 'sat_')) or
                  'satellite' in filename_lower):
                return 'wildfire-satellite-data'
            else:
                return 'wildfire-satellite-data'  # Default for HDF/NetCDF

        # Use main topic determination logic as fallback
        else:
            return self._determine_topic(record)
    
    def _generate_partition_key(self, record: Dict[str, Any]) -> str:
        """Generate partition key for balanced distribution"""
        try:
            # Use geographic location for spatial locality
            lat = record.get('latitude') or record.get('lat')
            lon = record.get('longitude') or record.get('lon')
            
            if lat is not None and lon is not None:
                # Create geographic grid for partitioning
                lat_grid = int(float(lat) * 10) % 100  # 0.1 degree resolution
                lon_grid = int(abs(float(lon)) * 10) % 100
                return f"geo_{lat_grid}_{lon_grid}"
            
            # Use sensor/source ID if available
            sensor_id = record.get('sensor_id') or record.get('source_id')
            if sensor_id:
                return f"sensor_{hash(str(sensor_id)) % 1000}"
            
            # Use timestamp-based partitioning as fallback
            timestamp = record.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    return f"time_{hash(timestamp) % 1000}"
                elif hasattr(timestamp, 'hour'):
                    return f"time_{timestamp.hour}_{timestamp.minute // 10}"
            
            # Default random partition
            return f"default_{uuid.uuid4().hex[:8]}"
            
        except Exception:
            return f"error_{uuid.uuid4().hex[:8]}"
    
    def _enrich_record(self, record: Dict[str, Any], source_type: str = None,
                      source_id: str = None, source_name: str = None, real_time: bool = False) -> Dict[str, Any]:
        """Add metadata to record for streaming

        IMPORTANT: Preserves per-record source_id if present in the record.
        This prevents overwriting source_id when batches contain mixed data types
        (e.g., NOAA station observations + weather alerts).

        Args:
            record: Data record to enrich
            source_type: Source type (used if record doesn't have one)
            source_id: Source ID (used if record doesn't have one)
            source_name: Source name override
            real_time: Whether this is real-time data

        Returns:
            Enriched record with ingestion_metadata
        """
        # ✅ Use record's own source_id if present, don't override
        # This fixes the bug where mixed batches (stations + alerts) got wrong source_id
        effective_source_id = record.get('source_id') or source_id
        effective_source_type = record.get('source_type') or source_type

        enriched = {
            **record,
            'ingestion_metadata': {
                'producer_id': self.client_id,
                'ingestion_timestamp': datetime.now(timezone.utc).isoformat(),
                'source_type': effective_source_type,
                'source_id': effective_source_id,  # ✅ Respects per-record source_id
                'source_name': source_name or self._get_provider_name(effective_source_id),
                'real_time': real_time,
                'processing_stage': 'streaming'
            }
        }

        # Add California wildfire context
        if self._is_california_relevant(record):
            enriched['california_relevance'] = True
            enriched['wildfire_context'] = self._extract_wildfire_context(record)

        return enriched
    
    def _enrich_file_record(self, record: Dict[str, Any], filename: str, file_type: str,
                           batch_id: str, sequence: int, total_records: int) -> Dict[str, Any]:
        """Add file-specific metadata to record"""
        enriched = {
            **record,
            'file_metadata': {
                'filename': filename,
                'file_type': file_type,
                'batch_id': batch_id,
                'sequence': sequence,
                'total_records': total_records,
                'processing_timestamp': datetime.now(timezone.utc).isoformat()
            },
            'ingestion_metadata': {
                'producer_id': self.client_id,
                'ingestion_timestamp': datetime.now(timezone.utc).isoformat(),
                'processing_stage': 'file_streaming'
            }
        }
        
        return enriched

    def _get_provider_name(self, source_id: str) -> str:
        """Map source ID to provider name using exact pattern matching"""
        if not source_id:
            return "Unknown"

        source_lower = source_id.lower()

        # NASA FIRMS: firms_*, landsat_nrt
        if source_lower.startswith(('firms_', 'landsat_nrt')):
            return "NASA FIRMS"
        # Satellite: sat_*
        elif source_lower.startswith('sat_'):
            return "Satellite Data"
        # NOAA Weather: noaa_*
        elif source_lower.startswith('noaa_'):
            return "NOAA"
        # Weather: wx_*
        elif source_lower.startswith('wx_'):
            return "Weather Services"
        # IoT: iot_*
        elif source_lower.startswith('iot_'):
            return "IoT Network"
        else:
            # Fallback to formatted source_id
            return source_id.replace('_', ' ').title()

    def _is_california_relevant(self, record: Dict[str, Any]) -> bool:
        """Check if record is relevant to California wildfires"""
        try:
            lat = record.get('latitude') or record.get('lat')
            lon = record.get('longitude') or record.get('lon')
            
            if lat is not None and lon is not None:
                # Use centralized California bounds
                bounds = CALIFORNIA_BOUNDS
                return (bounds['lat_min'] <= float(lat) <= bounds['lat_max'] and
                       bounds['lon_min'] <= float(lon) <= bounds['lon_max'])
            
            return True  # Include if no geospatial data
            
        except:
            return True
    
    def _extract_wildfire_context(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Extract wildfire-relevant context from record"""
        context = {}
        
        # Fire detection indicators
        if record.get('fire_confidence'):
            context['fire_detected'] = record['fire_confidence'] > 50
            context['fire_confidence'] = record['fire_confidence']
        
        # Weather risk factors
        if record.get('fire_weather_index'):
            context['fire_weather_risk'] = record['fire_weather_index']
            context['high_fire_risk'] = record['fire_weather_index'] > 70
        
        # Air quality/smoke indicators
        if record.get('pm25'):
            context['smoke_detected'] = record['pm25'] > 35.0
            context['air_quality_level'] = 'unhealthy' if record['pm25'] > 55 else 'moderate'
        
        # Drought indicators
        if record.get('soil_moisture'):
            context['drought_indicator'] = record['soil_moisture'] < 20.0
        
        return context
    
    def _detect_file_type(self, filename: str) -> str:
        """Detect file type from filename extension"""
        suffix = filename.lower().split('.')[-1]
        type_mapping = {
            'grib': 'grib', 'grib2': 'grib',
            'nc': 'netcdf', 'netcdf': 'netcdf',
            'hdf': 'hdf', 'h5': 'hdf',
            'tif': 'geotiff', 'tiff': 'geotiff',
            'json': 'json', 'csv': 'csv'
        }
        return type_mapping.get(suffix, 'unknown')
    
    def _serialize_value(self, value: Dict[str, Any]) -> bytes:
        """Serialize record value to JSON bytes"""
        try:
            return json.dumps(value, default=str, ensure_ascii=False).encode('utf-8')
        except Exception as e:
            logger.error(f"Failed to serialize value: {e}")
            return json.dumps({'error': 'serialization_failed'}).encode('utf-8')
    
    def _serialize_key(self, key: str) -> bytes:
        """Serialize partition key to bytes"""
        return str(key).encode('utf-8') if key else None
    
    async def get_producer_metrics(self) -> Dict[str, Any]:
        """Get producer performance metrics"""
        if not self.producer:
            return {}
        
        try:
            # Note: aiokafka doesn't expose detailed metrics like kafka-python
            # This is a simplified implementation
            return {
                'is_started': self.is_started,
                'client_id': self.client_id,
                'bootstrap_servers': self.bootstrap_servers,
                'health_status': await self.health_check()
            }
        except Exception as e:
            logger.error(f"Failed to get producer metrics: {e}")
            return {'error': str(e)}
    
    async def create_topics_if_needed(self) -> bool:
        """Create Kafka topics if they don't exist (requires admin permissions)"""
        try:
            # This would require kafka-admin functionality
            # For now, we'll log the topic configuration
            logger.info("Topic configuration for wildfire platform:")
            for topic, config in self.topic_config.items():
                logger.info(f"  {topic}: {config}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create topics: {e}")
            return False

class StreamingDataManager:
    """High-level manager for streaming wildfire data"""
    
    def __init__(self, kafka_config: Dict[str, Any]):
        self.kafka_producer = KafkaDataProducer(
            bootstrap_servers=kafka_config.get('bootstrap_servers', 'localhost:9092'),
            client_id=kafka_config.get('client_id')
        )
        self.is_running = False
        self.stream_handlers = {}
    
    async def start(self) -> bool:
        """Start the streaming data manager"""
        success = await self.kafka_producer.start()
        if success:
            self.is_running = True
            logger.info("Streaming data manager started")
        return success
    
    async def stop(self):
        """Stop the streaming data manager"""
        await self.kafka_producer.stop()
        self.is_running = False
        logger.info("Streaming data manager stopped")
    
    async def stream_processed_data(self, processed_data, source_type: str = None) -> bool:
        """Stream processed data to Kafka"""
        if not self.is_running:
            return False
        
        try:
            # Extract data from ProcessedData object
            if hasattr(processed_data, 'geospatial_data'):
                data = processed_data.geospatial_data
                source_type = processed_data.source_type
                source_id = processed_data.source_id
            else:
                data = processed_data
                source_id = 'unknown'
            
            return await self.kafka_producer.send_batch_data(
                data=data,
                source_type=source_type,
                source_id=source_id
            )
            
        except Exception as e:
            logger.error(f"Failed to stream processed data: {e}")
            return False
    
    async def stream_file_data(self, file_data: List[Dict[str, Any]], filename: str) -> bool:
        """Stream file-based data to Kafka"""
        if not self.is_running:
            return False
        
        return await self.kafka_producer.send_file_data(file_data, filename)
    
    async def send_wildfire_alert(self, alert_data: Dict[str, Any], severity: str = 'medium') -> bool:
        """Send wildfire alert"""
        if not self.is_running:
            return False
        
        return await self.kafka_producer.send_alert(alert_data, severity)
    
    def register_stream_handler(self, source_type: str, handler: Callable):
        """Register custom stream handler for specific source types"""
        self.stream_handlers[source_type] = handler
        logger.info(f"Registered stream handler for {source_type}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        return {
            'streaming_manager': self.is_running,
            'kafka_producer': await self.kafka_producer.health_check(),
            'registered_handlers': list(self.stream_handlers.keys()),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }