"""
S3 Reference Handler for Very Large Satellite Images
Manages upload and reference generation for images >100MB
Uses MinIO/S3 for storage with pre-signed URLs for secure access
"""

import os
import hashlib
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from urllib.parse import urlparse
import structlog

# MinIO client
try:
    from minio import Minio
    from minio.error import S3Error
    HAS_MINIO = True
except ImportError:
    HAS_MINIO = False

# Boto3 for AWS S3
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

logger = structlog.get_logger()


class S3ReferenceHandler:
    """
    Handles storage of very large satellite images in S3/MinIO

    Features:
    - Automatic upload for images >100MB
    - Pre-signed URL generation for secure access
    - Metadata storage alongside images
    - Support for both MinIO and AWS S3
    - Multipart upload for large files
    - Compression before upload (optional)
    """

    # Size thresholds
    DIRECT_KAFKA_MAX_SIZE = 20 * 1024 * 1024  # 20MB - use chunking
    CHUNKED_KAFKA_MAX_SIZE = 100 * 1024 * 1024  # 100MB - use S3 beyond this
    MULTIPART_THRESHOLD = 50 * 1024 * 1024  # 50MB - use multipart upload

    def __init__(
        self,
        storage_type: str = 'minio',  # 'minio' or 's3'
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: str = 'wildfire-satellite-imagery',
        region: str = 'us-east-1',
        secure: bool = True,
        compress_before_upload: bool = True,
        presigned_url_expiry_seconds: int = 3600  # 1 hour
    ):
        """
        Initialize S3 reference handler

        Args:
            storage_type: Type of storage ('minio' or 's3')
            endpoint: S3/MinIO endpoint URL
            access_key: Access key ID
            secret_key: Secret access key
            bucket_name: Bucket for storing images
            region: AWS region (for S3)
            secure: Use HTTPS
            compress_before_upload: Compress images before uploading
            presigned_url_expiry_seconds: Expiry time for pre-signed URLs
        """
        self.storage_type = storage_type
        self.bucket_name = bucket_name
        self.compress_before_upload = compress_before_upload
        self.presigned_url_expiry = presigned_url_expiry_seconds

        # Get credentials from environment if not provided
        self.access_key = access_key or os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        self.secret_key = secret_key or os.getenv('MINIO_SECRET_KEY', 'minioadminpassword')

        # Initialize client based on storage type
        if storage_type == 'minio':
            if not HAS_MINIO:
                raise ImportError("minio package not installed")

            self.endpoint = endpoint or os.getenv('MINIO_ENDPOINT', 'localhost:9000')
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=secure
            )
            self.s3_client = None

        elif storage_type == 's3':
            if not HAS_BOTO3:
                raise ImportError("boto3 package not installed")

            self.endpoint = endpoint  # Optional for AWS S3
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=region,
                endpoint_url=endpoint  # For S3-compatible services
            )
            self.client = None

        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")

        # Statistics
        self.stats = {
            'images_uploaded': 0,
            'images_downloaded': 0,
            'total_bytes_uploaded': 0,
            'total_bytes_downloaded': 0,
            'presigned_urls_generated': 0,
            'upload_failures': 0
        }

        # Ensure bucket exists
        asyncio.create_task(self._ensure_bucket_exists())

    async def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if not"""
        try:
            if self.storage_type == 'minio':
                if not self.client.bucket_exists(self.bucket_name):
                    self.client.make_bucket(self.bucket_name)
                    logger.info(f"Created bucket: {self.bucket_name}")
            elif self.storage_type == 's3':
                try:
                    self.s3_client.head_bucket(Bucket=self.bucket_name)
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                        logger.info(f"Created S3 bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to ensure bucket exists: {e}")

    def should_use_s3(self, data_size: int) -> bool:
        """
        Determine if data should be stored in S3 instead of Kafka

        Args:
            data_size: Size of data in bytes

        Returns:
            True if S3 should be used, False for Kafka
        """
        return data_size > self.CHUNKED_KAFKA_MAX_SIZE

    def should_use_chunking(self, data_size: int) -> bool:
        """
        Determine if data should be chunked for Kafka

        Args:
            data_size: Size of data in bytes

        Returns:
            True if chunking should be used, False for direct transmission
        """
        return (
            data_size > self.DIRECT_KAFKA_MAX_SIZE and
            data_size <= self.CHUNKED_KAFKA_MAX_SIZE
        )

    async def upload_image(
        self,
        image_data: bytes,
        metadata: Dict[str, Any],
        image_id: Optional[str] = None,
        content_type: str = 'application/octet-stream'
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Upload image to S3/MinIO

        Args:
            image_data: Raw image bytes
            metadata: Image metadata
            image_id: Optional image ID (generated if not provided)
            content_type: MIME type of image

        Returns:
            Tuple of (s3_url, enhanced_metadata)
        """
        try:
            # Generate image ID if not provided
            if not image_id:
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                data_hash = hashlib.md5(image_data[:1024]).hexdigest()[:8]
                image_id = f"{timestamp}_{data_hash}"

            # Determine object key
            date_path = datetime.utcnow().strftime('%Y/%m/%d')
            object_key = f"satellite-imagery/{date_path}/{image_id}"

            # Compress if configured and beneficial
            upload_data = image_data
            if self.compress_before_upload:
                compressed_data = self._compress_data(image_data)
                if len(compressed_data) < len(image_data) * 0.9:  # >10% savings
                    upload_data = compressed_data
                    object_key += '.zst'
                    metadata['compressed'] = True
                    metadata['original_size'] = len(image_data)

            # Calculate checksum
            checksum = hashlib.sha256(upload_data).hexdigest()

            # Prepare metadata for S3
            s3_metadata = {
                'image_id': image_id,
                'checksum': checksum,
                'size_bytes': str(len(upload_data)),
                'original_size_bytes': str(len(image_data)),
                'upload_timestamp': datetime.utcnow().isoformat(),
                'content_type': content_type
            }

            # Add custom metadata (S3 has limits, so we stringify complex values)
            for key, value in metadata.items():
                if key not in s3_metadata:
                    s3_metadata[f'x-amz-meta-{key}'] = str(value) if not isinstance(value, str) else value

            # Upload based on storage type
            if self.storage_type == 'minio':
                await self._upload_to_minio(object_key, upload_data, content_type, s3_metadata)
            else:
                await self._upload_to_s3(object_key, upload_data, content_type, s3_metadata)

            # Generate S3 URL
            if self.storage_type == 'minio':
                s3_url = f"minio://{self.bucket_name}/{object_key}"
            else:
                s3_url = f"s3://{self.bucket_name}/{object_key}"

            # Update statistics
            self.stats['images_uploaded'] += 1
            self.stats['total_bytes_uploaded'] += len(upload_data)

            # Prepare enhanced metadata
            enhanced_metadata = {
                **metadata,
                's3_url': s3_url,
                's3_bucket': self.bucket_name,
                's3_key': object_key,
                'storage_type': self.storage_type,
                'upload_size_bytes': len(upload_data),
                'original_size_bytes': len(image_data),
                'checksum': checksum,
                'upload_timestamp': datetime.utcnow().isoformat()
            }

            logger.info(
                "Image uploaded to S3",
                image_id=image_id,
                bucket=self.bucket_name,
                key=object_key,
                size=len(upload_data),
                compressed=metadata.get('compressed', False)
            )

            return s3_url, enhanced_metadata

        except Exception as e:
            self.stats['upload_failures'] += 1
            logger.error(f"Failed to upload image to S3: {e}", exc_info=True)
            raise

    async def _upload_to_minio(
        self,
        object_key: str,
        data: bytes,
        content_type: str,
        metadata: Dict[str, str]
    ):
        """Upload to MinIO"""
        import io

        # Use multipart for large files
        if len(data) > self.MULTIPART_THRESHOLD:
            # MinIO client handles multipart automatically
            pass

        # Upload
        self.client.put_object(
            self.bucket_name,
            object_key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
            metadata=metadata
        )

    async def _upload_to_s3(
        self,
        object_key: str,
        data: bytes,
        content_type: str,
        metadata: Dict[str, str]
    ):
        """Upload to AWS S3"""
        # Use multipart for large files
        if len(data) > self.MULTIPART_THRESHOLD:
            # Boto3 handles multipart automatically with upload_fileobj
            import io
            self.s3_client.upload_fileobj(
                io.BytesIO(data),
                self.bucket_name,
                object_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': metadata
                }
            )
        else:
            # Direct upload for smaller files
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=data,
                ContentType=content_type,
                Metadata=metadata
            )

    def generate_presigned_url(
        self,
        s3_url: str,
        expiry_seconds: Optional[int] = None
    ) -> str:
        """
        Generate pre-signed URL for secure access

        Args:
            s3_url: S3 URL (s3://bucket/key or minio://bucket/key)
            expiry_seconds: URL expiry time (uses default if not provided)

        Returns:
            Pre-signed URL for downloading
        """
        try:
            # Parse S3 URL
            parsed = urlparse(s3_url)
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')

            expiry = expiry_seconds or self.presigned_url_expiry

            if self.storage_type == 'minio':
                # Generate MinIO pre-signed URL
                url = self.client.presigned_get_object(
                    bucket,
                    key,
                    expires=timedelta(seconds=expiry)
                )
            else:
                # Generate AWS S3 pre-signed URL
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=expiry
                )

            self.stats['presigned_urls_generated'] += 1

            logger.debug(
                "Generated pre-signed URL",
                bucket=bucket,
                key=key,
                expiry_seconds=expiry
            )

            return url

        except Exception as e:
            logger.error(f"Failed to generate pre-signed URL: {e}")
            raise

    async def download_image(self, s3_url: str) -> Tuple[bytes, Dict[str, Any]]:
        """
        Download image from S3/MinIO

        Args:
            s3_url: S3 URL of image

        Returns:
            Tuple of (image_data, metadata)
        """
        try:
            # Parse S3 URL
            parsed = urlparse(s3_url)
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')

            if self.storage_type == 'minio':
                # Download from MinIO
                response = self.client.get_object(bucket, key)
                data = response.read()
                metadata = response.metadata
            else:
                # Download from S3
                response = self.s3_client.get_object(Bucket=bucket, Key=key)
                data = response['Body'].read()
                metadata = response.get('Metadata', {})

            # Decompress if needed
            if metadata.get('compressed') == 'true' or key.endswith('.zst'):
                data = self._decompress_data(data)

            # Update statistics
            self.stats['images_downloaded'] += 1
            self.stats['total_bytes_downloaded'] += len(data)

            logger.info(
                "Image downloaded from S3",
                bucket=bucket,
                key=key,
                size=len(data)
            )

            return data, metadata

        except Exception as e:
            logger.error(f"Failed to download image from S3: {e}")
            raise

    def _compress_data(self, data: bytes) -> bytes:
        """Compress data using zstandard"""
        try:
            import zstandard as zstd
            compressor = zstd.ZstdCompressor(level=3)
            return compressor.compress(data)
        except ImportError:
            import zlib
            return zlib.compress(data, level=6)

    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress data"""
        try:
            import zstandard as zstd
            decompressor = zstd.ZstdDecompressor()
            return decompressor.decompress(data)
        except (ImportError, zstd.ZstdError):
            import zlib
            return zlib.decompress(data)

    def create_reference_metadata(
        self,
        s3_url: str,
        original_metadata: Dict[str, Any],
        image_size: int,
        checksum: str
    ) -> Dict[str, Any]:
        """
        Create metadata for Kafka when image is stored in S3

        Args:
            s3_url: S3 URL of stored image
            original_metadata: Original image metadata
            image_size: Size of image in bytes
            checksum: SHA256 checksum of image

        Returns:
            Metadata dict for Kafka transmission
        """
        # Generate pre-signed URL for immediate access
        presigned_url = self.generate_presigned_url(s3_url)

        return {
            **original_metadata,
            'storage_type': 's3_reference',
            's3_url': s3_url,
            'presigned_url': presigned_url,
            'presigned_url_expiry': datetime.utcnow() + timedelta(seconds=self.presigned_url_expiry),
            'image_size_bytes': image_size,
            'checksum': checksum,
            'reference_timestamp': datetime.utcnow().isoformat()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get S3 handler statistics"""
        return {
            **self.stats,
            'storage_type': self.storage_type,
            'bucket': self.bucket_name,
            'compression_enabled': self.compress_before_upload
        }