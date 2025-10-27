"""
Data Storage Service - Blob Storage Manager
S3/MinIO integration for storing large objects (satellite images, model files, archives)
"""

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, BinaryIO
from pathlib import Path
import structlog

from aiobotocore.session import get_session
from botocore.exceptions import ClientError, NoCredentialsError
from minio import Minio
from minio.error import S3Error

from ..config import get_settings
from .data_models import (
    StorageRequest, StorageResponse, QueryRequest, QueryResponse,
    BulkStorageRequest, DataType, StorageBackend
)

logger = structlog.get_logger()

class BlobStorageManager:
    """
    Manages blob storage operations using S3/MinIO
    
    Handles large object storage with features:
    - Multi-part uploads for large files
    - Content deduplication using SHA-256 hashing
    - Automatic compression for supported formats
    - Metadata tagging and lifecycle management
    - Presigned URLs for direct client uploads/downloads
    - Cross-region replication support
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.session = get_session()
        self.client = None
        self.minio_client = None
        self.bucket_name = self.settings.s3_bucket_name
        
        # Storage configuration
        self.multipart_threshold = 100 * 1024 * 1024  # 100MB
        self.multipart_chunksize = 10 * 1024 * 1024   # 10MB chunks
        self.presigned_url_expiry = 3600  # 1 hour
        
        # Content type mapping
        self.content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg', 
            '.png': 'image/png',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.geotiff': 'image/tiff',
            '.nc': 'application/x-netcdf',
            '.h5': 'application/x-hdf5',
            '.hdf5': 'application/x-hdf5',
            '.json': 'application/json',
            '.pkl': 'application/octet-stream',
            '.joblib': 'application/octet-stream',
            '.zip': 'application/zip',
            '.tar.gz': 'application/gzip'
        }

    async def initialize(self):
        """Initialize blob storage connections and create bucket if needed"""
        try:
            # Initialize aiobotocore client
            session = get_session()
            self.client = session.create_client(
                's3',
                endpoint_url=self.settings.s3_endpoint,
                aws_access_key_id=self.settings.s3_access_key,
                aws_secret_access_key=self.settings.s3_secret_key,
                region_name=self.settings.s3_region
            )
            
            # Initialize MinIO client for sync operations
            self.minio_client = Minio(
                self.settings.s3_endpoint.replace('http://', '').replace('https://', ''),
                access_key=self.settings.s3_access_key,
                secret_key=self.settings.s3_secret_key,
                secure=self.settings.s3_endpoint.startswith('https')
            )
            
            # Create bucket if it doesn't exist
            await self._ensure_bucket_exists()
            
            # Setup lifecycle policies - temporarily disabled due to async issues
            # await self._setup_lifecycle_policies()
            
            logger.info("Blob storage manager initialized successfully",
                       bucket=self.bucket_name,
                       endpoint=self.settings.s3_endpoint)
                       
        except Exception as e:
            logger.error("Failed to initialize blob storage", error=str(e))
            raise

    async def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            async with self.client as client:
                try:
                    await client.head_bucket(Bucket=self.bucket_name)
                    logger.info("Bucket exists", bucket=self.bucket_name)
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        await client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={
                                'LocationConstraint': self.settings.s3_region
                            }
                        )
                        logger.info("Created bucket", bucket=self.bucket_name)
                    else:
                        raise
        except Exception as e:
            logger.error("Failed to ensure bucket exists", error=str(e))
            raise

    async def _setup_lifecycle_policies(self):
        """Setup S3 lifecycle policies for automatic data management"""
        try:
            lifecycle_policy = {
                'Rules': [
                    {
                        'ID': 'ArchiveOldData',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': 'archive/'},
                        'Transitions': [
                            {
                                'Days': 30,
                                'StorageClass': 'STANDARD_IA'
                            },
                            {
                                'Days': 90, 
                                'StorageClass': 'GLACIER'
                            },
                            {
                                'Days': 365,
                                'StorageClass': 'DEEP_ARCHIVE'
                            }
                        ]
                    },
                    {
                        'ID': 'DeleteIncompleteUploads',
                        'Status': 'Enabled',
                        'Filter': {},
                        'AbortIncompleteMultipartUpload': {
                            'DaysAfterInitiation': 7
                        }
                    }
                ]
            }
            
            async with self.client as client:
                await client.put_bucket_lifecycle_configuration(
                    Bucket=self.bucket_name,
                    LifecycleConfiguration=lifecycle_policy
                )
                
            logger.info("Lifecycle policies configured")
            
        except Exception as e:
            logger.warning("Failed to setup lifecycle policies", error=str(e))

    async def store(self, request: StorageRequest) -> StorageResponse:
        """
        Store blob data with automatic routing and optimization
        
        Handles different data types:
        - satellite_image: Geospatial image data with metadata
        - model_file: ML models with versioning
        - archive: Compressed historical data
        """
        try:
            storage_id = str(uuid.uuid4())
            timestamp = request.timestamp or datetime.now()
            
            # Generate object key based on data type and timestamp  
            object_key = self._generate_object_key(
                data_type=request.data_type,
                storage_id=storage_id,
                timestamp=timestamp,
                source_id=request.source_id
            )
            
            # Prepare metadata
            metadata = self._prepare_metadata(request, storage_id, timestamp)
            
            # Handle different data formats
            if isinstance(request.data, dict):
                # JSON data
                content = json.dumps(request.data, default=str).encode('utf-8')
                content_type = 'application/json'
            elif isinstance(request.data, (bytes, bytearray)):
                # Binary data
                content = bytes(request.data)
                content_type = self._get_content_type(object_key)
            elif isinstance(request.data, str):
                # String data (file path or content)
                if Path(request.data).exists():
                    # File path
                    with open(request.data, 'rb') as f:
                        content = f.read()
                    content_type = self._get_content_type(request.data)
                else:
                    # String content
                    content = request.data.encode('utf-8')
                    content_type = 'text/plain'
            else:
                raise ValueError(f"Unsupported data type: {type(request.data)}")
            
            # Calculate content hash for deduplication
            content_hash = hashlib.sha256(content).hexdigest()
            
            # Check for existing content with same hash
            existing_object = await self._find_by_hash(content_hash)
            if existing_object and request.data_type != DataType.MODEL_FILE:
                # Return reference to existing object (except for model files which need versioning)
                logger.info("Found existing content, returning reference",
                           storage_id=storage_id,
                           existing_key=existing_object)
                
                return StorageResponse(
                    storage_id=existing_object,
                    data_type=request.data_type,
                    backend=StorageBackend.S3_MINIO,
                    size_bytes=len(content),
                    timestamp=timestamp,
                    status="deduplicated"
                )
            
            # Store metadata in object tags
            metadata['content_hash'] = content_hash
            metadata['original_size'] = str(len(content))
            
            # Upload to S3/MinIO
            if len(content) > self.multipart_threshold:
                await self._multipart_upload(object_key, content, content_type, metadata)
            else:
                await self._simple_upload(object_key, content, content_type, metadata)
            
            logger.info("Blob stored successfully",
                       storage_id=storage_id,
                       object_key=object_key,
                       size_bytes=len(content),
                       data_type=request.data_type)
            
            return StorageResponse(
                storage_id=object_key,
                data_type=request.data_type,
                backend=StorageBackend.S3_MINIO,
                size_bytes=len(content),
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error("Failed to store blob", error=str(e), data_type=request.data_type)
            raise

    async def _simple_upload(self, object_key: str, content: bytes, content_type: str, metadata: Dict[str, str]):
        """Simple upload for smaller files"""
        async with self.client as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=content,
                ContentType=content_type,
                Metadata=metadata,
                ServerSideEncryption='AES256'
            )

    async def _multipart_upload(self, object_key: str, content: bytes, content_type: str, metadata: Dict[str, str]):
        """Multipart upload for larger files"""
        async with self.client as client:
            # Initiate multipart upload
            response = await client.create_multipart_upload(
                Bucket=self.bucket_name,
                Key=object_key,
                ContentType=content_type,
                Metadata=metadata,
                ServerSideEncryption='AES256'
            )
            
            upload_id = response['UploadId']
            parts = []
            
            try:
                # Upload parts in chunks
                chunk_size = self.multipart_chunksize
                part_number = 1
                
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i + chunk_size]
                    
                    part_response = await client.upload_part(
                        Bucket=self.bucket_name,
                        Key=object_key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=chunk
                    )
                    
                    parts.append({
                        'ETag': part_response['ETag'],
                        'PartNumber': part_number
                    })
                    
                    part_number += 1
                
                # Complete multipart upload
                await client.complete_multipart_upload(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    UploadId=upload_id,
                    MultipartUpload={'Parts': parts}
                )
                
            except Exception as e:
                # Abort multipart upload on failure
                await client.abort_multipart_upload(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    UploadId=upload_id
                )
                raise

    async def query(self, request: QueryRequest) -> QueryResponse:
        """Query blob storage with filtering and metadata search"""
        try:
            start_time = datetime.now()
            
            # Build S3 prefix based on data type and time range
            prefix = self._build_query_prefix(request)
            
            objects = []
            async with self.client as client:
                paginator = client.get_paginator('list_objects_v2')
                
                async for page in paginator.paginate(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    MaxKeys=request.limit or 1000
                ):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            # Apply time filtering
                            if not self._matches_time_filter(obj['LastModified'], request):
                                continue
                            
                            # Get object metadata if requested
                            if request.include_metadata:
                                metadata = await self._get_object_metadata(client, obj['Key'])
                                obj['Metadata'] = metadata
                            
                            objects.append({
                                'storage_id': obj['Key'],
                                'size_bytes': obj['Size'],
                                'last_modified': obj['LastModified'].isoformat(),
                                'etag': obj['ETag'].strip('"'),
                                'metadata': obj.get('Metadata', {})
                            })
            
            # Apply additional filters
            filtered_objects = self._apply_filters(objects, request.filters or {})
            
            # Apply offset and limit
            offset = request.offset or 0
            limit = request.limit or 1000
            paginated_objects = filtered_objects[offset:offset + limit]
            
            query_time = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.info("Blob query completed",
                       total_objects=len(filtered_objects),
                       returned_objects=len(paginated_objects),
                       query_time_ms=query_time)
            
            return QueryResponse(
                data=paginated_objects,
                total_records=len(filtered_objects),
                data_type=request.data_type,
                query_time_ms=query_time
            )
            
        except Exception as e:
            logger.error("Blob query failed", error=str(e))
            raise

    async def get_by_id(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve blob object by storage ID (object key)"""
        try:
            async with self.client as client:
                try:
                    # Get object metadata
                    head_response = await client.head_object(
                        Bucket=self.bucket_name,
                        Key=storage_id
                    )
                    
                    # Get object content
                    get_response = await client.get_object(
                        Bucket=self.bucket_name,
                        Key=storage_id
                    )
                    
                    content = await get_response['Body'].read()
                    
                    return {
                        'storage_id': storage_id,
                        'content': content,
                        'content_type': head_response.get('ContentType'),
                        'size_bytes': head_response.get('ContentLength'),
                        'last_modified': head_response.get('LastModified'),
                        'metadata': head_response.get('Metadata', {})
                    }
                    
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchKey':
                        return None
                    raise
                    
        except Exception as e:
            logger.error("Failed to get blob by ID", storage_id=storage_id, error=str(e))
            raise

    async def delete(self, storage_id: str) -> bool:
        """Delete blob object by storage ID"""
        try:
            async with self.client as client:
                try:
                    await client.delete_object(
                        Bucket=self.bucket_name,
                        Key=storage_id
                    )
                    logger.info("Blob deleted successfully", storage_id=storage_id)
                    return True
                    
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchKey':
                        return False
                    raise
                    
        except Exception as e:
            logger.error("Failed to delete blob", storage_id=storage_id, error=str(e))
            raise

    async def generate_presigned_url(self, storage_id: str, expires_in: int = None, operation: str = 'get') -> str:
        """Generate presigned URL for direct client access"""
        try:
            expires_in = expires_in or self.presigned_url_expiry
            
            async with self.client as client:
                if operation == 'get':
                    url = await client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': self.bucket_name, 'Key': storage_id},
                        ExpiresIn=expires_in
                    )
                elif operation == 'put':
                    url = await client.generate_presigned_url(
                        'put_object',
                        Params={'Bucket': self.bucket_name, 'Key': storage_id},
                        ExpiresIn=expires_in
                    )
                else:
                    raise ValueError(f"Unsupported operation: {operation}")
                
                logger.info("Generated presigned URL", 
                           storage_id=storage_id, 
                           operation=operation,
                           expires_in=expires_in)
                
                return url
                
        except Exception as e:
            logger.error("Failed to generate presigned URL", error=str(e))
            raise

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get blob storage statistics and usage metrics"""
        try:
            stats = {
                'total_objects': 0,
                'total_size_bytes': 0,
                'data_type_breakdown': {},
                'storage_classes': {},
                'oldest_object': None,
                'newest_object': None
            }
            
            async with self.client as client:
                paginator = client.get_paginator('list_objects_v2')
                
                async for page in paginator.paginate(Bucket=self.bucket_name):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            stats['total_objects'] += 1
                            stats['total_size_bytes'] += obj['Size']
                            
                            # Track oldest and newest objects
                            if not stats['oldest_object'] or obj['LastModified'] < stats['oldest_object']:
                                stats['oldest_object'] = obj['LastModified']
                            if not stats['newest_object'] or obj['LastModified'] > stats['newest_object']:
                                stats['newest_object'] = obj['LastModified']
                            
                            # Extract data type from object key
                            data_type = obj['Key'].split('/')[0] if '/' in obj['Key'] else 'unknown'
                            stats['data_type_breakdown'][data_type] = stats['data_type_breakdown'].get(data_type, 0) + 1
            
            # Convert datetime objects to ISO strings
            if stats['oldest_object']:
                stats['oldest_object'] = stats['oldest_object'].isoformat()
            if stats['newest_object']:
                stats['newest_object'] = stats['newest_object'].isoformat()
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get storage stats", error=str(e))
            raise

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.client:
                await self.client.close()
            logger.info("Blob storage manager cleanup completed")
        except Exception as e:
            logger.error("Error during blob storage cleanup", error=str(e))

    def _generate_object_key(self, data_type: DataType, storage_id: str, timestamp: datetime, source_id: Optional[str] = None) -> str:
        """Generate hierarchical object key for S3 storage"""
        date_prefix = timestamp.strftime("%Y/%m/%d")
        
        if source_id:
            return f"{data_type.value}/{date_prefix}/{source_id}/{storage_id}"
        else:
            return f"{data_type.value}/{date_prefix}/{storage_id}"

    def _prepare_metadata(self, request: StorageRequest, storage_id: str, timestamp: datetime) -> Dict[str, str]:
        """Prepare metadata for S3 object"""
        metadata = {
            'storage-id': storage_id,
            'data-type': request.data_type.value,
            'timestamp': timestamp.isoformat(),
            'service': 'wildfire-intelligence-platform'
        }
        
        if request.source_id:
            metadata['source-id'] = request.source_id
        
        if request.tags:
            metadata['tags'] = ','.join(request.tags)
        
        if request.metadata:
            # Flatten additional metadata (S3 metadata keys must be strings)
            for key, value in request.metadata.items():
                metadata[f'custom-{key}'] = str(value)
        
        return metadata

    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension"""
        suffix = Path(filename).suffix.lower()
        return self.content_types.get(suffix, 'application/octet-stream')

    def _build_query_prefix(self, request: QueryRequest) -> str:
        """Build S3 prefix for query optimization"""
        prefix = f"{request.data_type.value}/"
        
        if request.start_time:
            # Add date-based prefix for time range queries
            prefix += request.start_time.strftime("%Y/%m/")
        
        return prefix

    def _matches_time_filter(self, last_modified: datetime, request: QueryRequest) -> bool:
        """Check if object matches time filter criteria"""
        if request.start_time and last_modified < request.start_time:
            return False
        if request.end_time and last_modified > request.end_time:
            return False
        return True

    def _apply_filters(self, objects: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply additional filters to object list"""
        if not filters:
            return objects
        
        filtered = []
        for obj in objects:
            matches = True
            
            for key, value in filters.items():
                if key in obj and obj[key] != value:
                    matches = False
                    break
                elif key in obj.get('metadata', {}) and obj['metadata'][key] != str(value):
                    matches = False
                    break
            
            if matches:
                filtered.append(obj)
        
        return filtered

    async def _get_object_metadata(self, client, object_key: str) -> Dict[str, Any]:
        """Get detailed metadata for an object"""
        try:
            response = await client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return response.get('Metadata', {})
        except Exception:
            return {}

    async def _find_by_hash(self, content_hash: str) -> Optional[str]:
        """Find existing object with same content hash"""
        try:
            # This would require a metadata index in production
            # For now, we'll skip deduplication to avoid performance issues
            return None
        except Exception:
            return None