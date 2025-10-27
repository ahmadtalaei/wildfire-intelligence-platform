"""
Image Chunk Manager for Large Satellite Images
Handles splitting and reassembly of images >10MB for Kafka transmission
Supports reliable chunk delivery with ordering and integrity checks
"""

import hashlib
import struct
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import structlog

logger = structlog.get_logger()


@dataclass
class ImageChunk:
    """Represents a single chunk of an image"""
    chunk_id: str
    image_id: str
    sequence: int
    total_chunks: int
    data: bytes
    checksum: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkReassemblyState:
    """Tracks the state of chunk reassembly"""
    image_id: str
    total_chunks: int
    received_chunks: Dict[int, ImageChunk] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    expected_checksum: Optional[str] = None
    expected_size: Optional[int] = None

    def is_complete(self) -> bool:
        """Check if all chunks have been received"""
        return len(self.received_chunks) == self.total_chunks

    def get_missing_sequences(self) -> List[int]:
        """Get list of missing chunk sequences"""
        expected = set(range(self.total_chunks))
        received = set(self.received_chunks.keys())
        return sorted(list(expected - received))

    def elapsed_time(self) -> float:
        """Get elapsed time since reassembly started"""
        return time.time() - self.start_time


class ImageChunkManager:
    """
    Manages chunking and reassembly of large satellite images

    Features:
    - Configurable chunk size (default 5MB for safety with 10MB Kafka limit)
    - Ordered chunk delivery with sequence numbers
    - Integrity verification with checksums
    - Timeout handling for incomplete reassemblies
    - Memory-efficient streaming
    """

    # Chunk header format: magic(4) + version(1) + image_id(36) + seq(2) + total(2) + size(4) + checksum(32)
    CHUNK_HEADER_FORMAT = '!4s B 36s H H I 32s'  # 81 bytes
    CHUNK_HEADER_SIZE = struct.calcsize(CHUNK_HEADER_FORMAT)
    CHUNK_MAGIC = b'IMGC'  # Image Chunk magic bytes
    CHUNK_VERSION = 1

    def __init__(
        self,
        chunk_size_bytes: int = 5 * 1024 * 1024,  # 5MB default
        max_chunk_size_bytes: int = 9 * 1024 * 1024,  # 9MB max (safe for 10MB Kafka limit)
        reassembly_timeout_seconds: int = 300,  # 5 minutes
        max_concurrent_reassemblies: int = 10
    ):
        """
        Initialize the chunk manager

        Args:
            chunk_size_bytes: Target size for each chunk
            max_chunk_size_bytes: Maximum allowed chunk size
            reassembly_timeout_seconds: Timeout for incomplete reassemblies
            max_concurrent_reassemblies: Maximum concurrent reassembly operations
        """
        self.chunk_size = min(chunk_size_bytes, max_chunk_size_bytes)
        self.max_chunk_size = max_chunk_size_bytes
        self.reassembly_timeout = reassembly_timeout_seconds
        self.max_concurrent = max_concurrent_reassemblies

        # Reassembly state tracking
        self.reassembly_states: Dict[str, ChunkReassemblyState] = {}
        self.reassembly_lock = asyncio.Lock()

        # Statistics
        self.stats = {
            'images_chunked': 0,
            'images_reassembled': 0,
            'chunks_sent': 0,
            'chunks_received': 0,
            'reassembly_timeouts': 0,
            'reassembly_failures': 0,
            'total_bytes_chunked': 0,
            'total_bytes_reassembled': 0
        }

        # Start cleanup task
        self.cleanup_task = None

    async def start(self):
        """Start the chunk manager and cleanup task"""
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_reassemblies())
            logger.info("Image chunk manager started", chunk_size=self.chunk_size)

    async def stop(self):
        """Stop the chunk manager"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Image chunk manager stopped")

    def create_chunks(
        self,
        image_data: bytes,
        metadata: Dict[str, Any],
        image_id: Optional[str] = None
    ) -> List[ImageChunk]:
        """
        Split image into chunks for transmission

        Args:
            image_data: Raw image bytes
            metadata: Image metadata to include with first chunk
            image_id: Optional image ID (generated if not provided)

        Returns:
            List of ImageChunk objects ready for transmission
        """
        if not image_id:
            image_id = str(uuid.uuid4())

        # Calculate total chunks needed
        data_size = len(image_data)
        num_chunks = (data_size + self.chunk_size - 1) // self.chunk_size

        # Calculate full image checksum
        full_checksum = hashlib.sha256(image_data).hexdigest()

        # Add chunking metadata
        chunk_metadata = {
            **metadata,
            'chunked': True,
            'chunk_size': self.chunk_size,
            'total_size': data_size,
            'total_chunks': num_chunks,
            'full_checksum': full_checksum,
            'chunking_timestamp': datetime.utcnow().isoformat()
        }

        chunks = []
        for i in range(num_chunks):
            start_idx = i * self.chunk_size
            end_idx = min(start_idx + self.chunk_size, data_size)
            chunk_data = image_data[start_idx:end_idx]

            # Calculate chunk checksum
            chunk_checksum = hashlib.md5(chunk_data).hexdigest()

            # Create chunk object
            chunk = ImageChunk(
                chunk_id=f"{image_id}_chunk_{i}",
                image_id=image_id,
                sequence=i,
                total_chunks=num_chunks,
                data=chunk_data,
                checksum=chunk_checksum,
                metadata=chunk_metadata if i == 0 else {}  # Only first chunk gets metadata
            )

            chunks.append(chunk)

        # Update statistics
        self.stats['images_chunked'] += 1
        self.stats['chunks_sent'] += num_chunks
        self.stats['total_bytes_chunked'] += data_size

        logger.info(
            "Image chunked",
            image_id=image_id,
            size=data_size,
            chunks=num_chunks,
            chunk_size=self.chunk_size
        )

        return chunks

    def serialize_chunk(self, chunk: ImageChunk) -> bytes:
        """
        Serialize chunk for Kafka transmission

        Returns:
            Binary representation of chunk with header
        """
        # Pack header
        header = struct.pack(
            self.CHUNK_HEADER_FORMAT,
            self.CHUNK_MAGIC,
            self.CHUNK_VERSION,
            chunk.image_id.encode('utf-8'),
            chunk.sequence,
            chunk.total_chunks,
            len(chunk.data),
            bytes.fromhex(chunk.checksum)
        )

        # Combine header and data
        return header + chunk.data

    def deserialize_chunk(self, chunk_bytes: bytes) -> ImageChunk:
        """
        Deserialize chunk from Kafka message

        Args:
            chunk_bytes: Raw bytes from Kafka

        Returns:
            ImageChunk object

        Raises:
            ValueError: If chunk format is invalid
        """
        if len(chunk_bytes) < self.CHUNK_HEADER_SIZE:
            raise ValueError("Chunk data too small for header")

        # Unpack header
        header = chunk_bytes[:self.CHUNK_HEADER_SIZE]
        magic, version, image_id_bytes, seq, total, size, checksum_bytes = struct.unpack(
            self.CHUNK_HEADER_FORMAT, header
        )

        # Verify magic bytes
        if magic != self.CHUNK_MAGIC:
            raise ValueError(f"Invalid chunk magic bytes: {magic}")

        # Verify version
        if version != self.CHUNK_VERSION:
            raise ValueError(f"Unsupported chunk version: {version}")

        # Extract data
        data = chunk_bytes[self.CHUNK_HEADER_SIZE:self.CHUNK_HEADER_SIZE + size]

        # Verify checksum
        calculated_checksum = hashlib.md5(data).hexdigest()
        provided_checksum = checksum_bytes.hex()

        if calculated_checksum != provided_checksum:
            logger.warning(
                "Chunk checksum mismatch",
                calculated=calculated_checksum,
                provided=provided_checksum
            )

        # Create chunk object
        image_id = image_id_bytes.decode('utf-8').rstrip('\x00')

        return ImageChunk(
            chunk_id=f"{image_id}_chunk_{seq}",
            image_id=image_id,
            sequence=seq,
            total_chunks=total,
            data=data,
            checksum=provided_checksum
        )

    async def add_chunk_for_reassembly(
        self,
        chunk: ImageChunk,
        expected_checksum: Optional[str] = None,
        expected_size: Optional[int] = None
    ) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Add a received chunk for reassembly

        Args:
            chunk: Received chunk
            expected_checksum: Optional expected checksum of full image
            expected_size: Optional expected size of full image

        Returns:
            Tuple of (complete_image, metadata) if reassembly is complete, None otherwise
        """
        async with self.reassembly_lock:
            image_id = chunk.image_id

            # Create or get reassembly state
            if image_id not in self.reassembly_states:
                if len(self.reassembly_states) >= self.max_concurrent:
                    # Remove oldest reassembly to make room
                    oldest_id = min(
                        self.reassembly_states.keys(),
                        key=lambda k: self.reassembly_states[k].start_time
                    )
                    del self.reassembly_states[oldest_id]
                    logger.warning("Evicted oldest reassembly to make room", evicted_id=oldest_id)

                self.reassembly_states[image_id] = ChunkReassemblyState(
                    image_id=image_id,
                    total_chunks=chunk.total_chunks,
                    expected_checksum=expected_checksum,
                    expected_size=expected_size
                )

            state = self.reassembly_states[image_id]

            # Add chunk if not duplicate
            if chunk.sequence not in state.received_chunks:
                state.received_chunks[chunk.sequence] = chunk
                self.stats['chunks_received'] += 1

                # Extract metadata from first chunk
                if chunk.sequence == 0 and chunk.metadata:
                    state.metadata = chunk.metadata

                logger.debug(
                    "Chunk received",
                    image_id=image_id,
                    sequence=chunk.sequence,
                    total=chunk.total_chunks,
                    received=len(state.received_chunks)
                )

            # Check if reassembly is complete
            if state.is_complete():
                try:
                    # Reassemble image
                    image_data, metadata = self._reassemble_image(state)

                    # Clean up state
                    del self.reassembly_states[image_id]

                    # Update statistics
                    self.stats['images_reassembled'] += 1
                    self.stats['total_bytes_reassembled'] += len(image_data)

                    logger.info(
                        "Image reassembled",
                        image_id=image_id,
                        size=len(image_data),
                        elapsed_seconds=state.elapsed_time()
                    )

                    return image_data, metadata

                except Exception as e:
                    logger.error(
                        "Reassembly failed",
                        image_id=image_id,
                        error=str(e),
                        exc_info=True
                    )
                    self.stats['reassembly_failures'] += 1
                    del self.reassembly_states[image_id]
                    raise

            # Return None if not complete yet
            missing = state.get_missing_sequences()
            if missing and len(missing) <= 5:  # Log only if few chunks missing
                logger.debug(
                    "Awaiting chunks",
                    image_id=image_id,
                    missing_sequences=missing
                )

            return None

    def _reassemble_image(self, state: ChunkReassemblyState) -> Tuple[bytes, Dict[str, Any]]:
        """
        Reassemble image from complete chunk set

        Args:
            state: Complete reassembly state

        Returns:
            Tuple of (image_data, metadata)

        Raises:
            ValueError: If reassembly validation fails
        """
        # Sort chunks by sequence
        sorted_chunks = sorted(
            state.received_chunks.values(),
            key=lambda c: c.sequence
        )

        # Concatenate data
        image_data = b''.join(chunk.data for chunk in sorted_chunks)

        # Verify size if expected
        if state.expected_size and len(image_data) != state.expected_size:
            raise ValueError(
                f"Size mismatch: expected {state.expected_size}, got {len(image_data)}"
            )

        # Verify checksum if expected
        if state.expected_checksum:
            calculated = hashlib.sha256(image_data).hexdigest()
            if calculated != state.expected_checksum:
                raise ValueError(f"Checksum mismatch in reassembled image")

        # Also check against metadata checksum if available
        if 'full_checksum' in state.metadata:
            calculated = hashlib.sha256(image_data).hexdigest()
            if calculated != state.metadata['full_checksum']:
                raise ValueError("Checksum mismatch with metadata")

        return image_data, state.metadata

    async def _cleanup_expired_reassemblies(self):
        """Background task to clean up expired reassembly operations"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                async with self.reassembly_lock:
                    expired = []
                    current_time = time.time()

                    for image_id, state in self.reassembly_states.items():
                        if state.elapsed_time() > self.reassembly_timeout:
                            expired.append(image_id)

                    for image_id in expired:
                        state = self.reassembly_states[image_id]
                        logger.warning(
                            "Reassembly timeout",
                            image_id=image_id,
                            received=len(state.received_chunks),
                            total=state.total_chunks,
                            missing=state.get_missing_sequences()
                        )
                        del self.reassembly_states[image_id]
                        self.stats['reassembly_timeouts'] += 1

                    if expired:
                        logger.info(f"Cleaned up {len(expired)} expired reassemblies")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cleanup task", error=str(e))

    def get_reassembly_status(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Get status of ongoing reassembly"""
        if image_id not in self.reassembly_states:
            return None

        state = self.reassembly_states[image_id]
        return {
            'image_id': image_id,
            'total_chunks': state.total_chunks,
            'received_chunks': len(state.received_chunks),
            'missing_sequences': state.get_missing_sequences(),
            'elapsed_seconds': state.elapsed_time(),
            'is_complete': state.is_complete()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get chunk manager statistics"""
        return {
            **self.stats,
            'active_reassemblies': len(self.reassembly_states),
            'chunk_size_bytes': self.chunk_size,
            'reassembly_timeout_seconds': self.reassembly_timeout
        }