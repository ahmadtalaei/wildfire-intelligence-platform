"""Data storage management for wildfire intelligence platform"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import uuid

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    import pymongo
    from motor import motor_asyncio
except ImportError:
    pymongo = None
    motor_asyncio = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StorageConfig:
    """Storage configuration settings"""
    
    def __init__(self, config: Dict[str, Any]):
        self.storage_type = config.get('type', 'file')
        self.connection_string = config.get('connection_string', '')
        self.database_name = config.get('database_name', 'wildfire_intelligence')
        self.file_base_path = config.get('file_base_path', './data/storage')
        self.retention_days = config.get('retention_days', 30)
        self.compression = config.get('compression', True)
        
        # Ensure storage directory exists
        if self.storage_type == 'file':
            Path(self.file_base_path).mkdir(parents=True, exist_ok=True)

class FileStorage:
    """File-based storage for wildfire data"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.base_path = Path(config.file_base_path)
        
    async def store_processed_data(self, processed_data, source_type: str = None) -> bool:
        """Store processed data to files organized by type and date"""
        try:
            # Extract data from ProcessedData object
            if hasattr(processed_data, 'geospatial_data'):
                data = processed_data.geospatial_data
                source_type = processed_data.source_type
                source_id = processed_data.source_id
                timestamp = processed_data.timestamp
                metadata = processed_data.metadata
                quality_metrics = processed_data.quality_metrics
            else:
                data = processed_data
                source_id = 'unknown'
                timestamp = datetime.now(timezone.utc)
                metadata = {}
                quality_metrics = {}
            
            # Create organized directory structure
            date_str = timestamp.strftime('%Y/%m/%d')
            storage_dir = self.base_path / source_type / date_str
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp_str = timestamp.strftime('%H%M%S')
            batch_id = str(uuid.uuid4())[:8]
            filename = f"{source_id}_{timestamp_str}_{batch_id}.json"
            file_path = storage_dir / filename
            
            # Prepare storage record
            storage_record = {
                'metadata': {
                    'source_type': source_type,
                    'source_id': source_id,
                    'timestamp': timestamp.isoformat(),
                    'record_count': len(data) if isinstance(data, list) else 1,
                    'storage_timestamp': datetime.now(timezone.utc).isoformat(),
                    'file_path': str(file_path),
                    'quality_metrics': quality_metrics,
                    'original_metadata': metadata
                },
                'data': data
            }
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(storage_record, f, default=str, indent=2)
            
            # Create index entry
            await self._update_index(source_type, source_id, file_path, timestamp, len(data) if isinstance(data, list) else 1)
            
            logger.info(f"Stored {len(data) if isinstance(data, list) else 1} records to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store data to file: {e}")
            return False
    
    async def store_raw_data(self, raw_data: List[Dict[str, Any]], source_type: str, source_id: str) -> bool:
        """Store raw data before processing"""
        try:
            timestamp = datetime.now(timezone.utc)
            date_str = timestamp.strftime('%Y/%m/%d')
            storage_dir = self.base_path / 'raw' / source_type / date_str
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp_str = timestamp.strftime('%H%M%S')
            batch_id = str(uuid.uuid4())[:8]
            filename = f"raw_{source_id}_{timestamp_str}_{batch_id}.json"
            file_path = storage_dir / filename
            
            storage_record = {
                'metadata': {
                    'source_type': source_type,
                    'source_id': source_id,
                    'timestamp': timestamp.isoformat(),
                    'record_count': len(raw_data),
                    'data_type': 'raw'
                },
                'data': raw_data
            }
            
            with open(file_path, 'w') as f:
                json.dump(storage_record, f, default=str, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store raw data: {e}")
            return False
    
    async def retrieve_data(self, source_type: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Retrieve stored data by type and date range"""
        try:
            results = []
            current_date = start_date.date()
            end_date_only = end_date.date()
            
            while current_date <= end_date_only:
                date_str = current_date.strftime('%Y/%m/%d')
                date_dir = self.base_path / source_type / date_str
                
                if date_dir.exists():
                    for file_path in date_dir.glob('*.json'):
                        try:
                            with open(file_path, 'r') as f:
                                stored_record = json.load(f)
                                file_timestamp = datetime.fromisoformat(stored_record['metadata']['timestamp'])
                                
                                if start_date <= file_timestamp <= end_date:
                                    results.extend(stored_record['data'] if isinstance(stored_record['data'], list) else [stored_record['data']])
                        except Exception as e:
                            logger.warning(f"Failed to read file {file_path}: {e}")
                
                current_date = pd.date_range(current_date, periods=2, freq='D')[1].date()
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve data: {e}")
            return []
    
    async def _update_index(self, source_type: str, source_id: str, file_path: Path, timestamp: datetime, record_count: int):
        """Update file index for faster queries"""
        try:
            index_file = self.base_path / f"{source_type}_index.json"
            
            # Load existing index
            if index_file.exists():
                with open(index_file, 'r') as f:
                    index = json.load(f)
            else:
                index = {'files': []}
            
            # Add new entry
            index['files'].append({
                'file_path': str(file_path),
                'source_id': source_id,
                'timestamp': timestamp.isoformat(),
                'record_count': record_count,
                'indexed_at': datetime.now(timezone.utc).isoformat()
            })
            
            # Keep only recent entries (based on retention policy)
            retention_cutoff = datetime.now(timezone.utc).replace(day=1) - pd.Timedelta(days=self.config.retention_days)
            index['files'] = [
                entry for entry in index['files']
                if datetime.fromisoformat(entry['timestamp']) > retention_cutoff
            ]
            
            # Write updated index
            with open(index_file, 'w') as f:
                json.dump(index, f, default=str, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to update index: {e}")
    
    async def cleanup_old_data(self) -> int:
        """Clean up data older than retention period"""
        try:
            cleanup_count = 0
            retention_cutoff = datetime.now(timezone.utc) - pd.Timedelta(days=self.config.retention_days)
            
            for source_dir in self.base_path.iterdir():
                if source_dir.is_dir() and source_dir.name != 'raw':
                    for year_dir in source_dir.iterdir():
                        if year_dir.is_dir():
                            for month_dir in year_dir.iterdir():
                                if month_dir.is_dir():
                                    for day_dir in month_dir.iterdir():
                                        if day_dir.is_dir():
                                            try:
                                                dir_date = datetime.strptime(str(day_dir).split(os.sep)[-3:], ['%Y', '%m', '%d'])
                                                if dir_date.replace(tzinfo=timezone.utc) < retention_cutoff:
                                                    # Remove old directory
                                                    import shutil
                                                    shutil.rmtree(day_dir)
                                                    cleanup_count += 1
                                            except Exception:
                                                continue
            
            logger.info(f"Cleaned up {cleanup_count} old data directories")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0

class SQLiteStorage:
    """SQLite-based storage for wildfire data"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.db_path = Path(config.file_base_path) / f"{config.database_name}.db"
        Path(config.file_base_path).mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """Initialize SQLite database and tables"""
        if not aiosqlite:
            logger.error("aiosqlite not available - install with: pip install aiosqlite")
            return False
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Create processed data table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS processed_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_type TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        data_type TEXT,
                        timestamp DATETIME NOT NULL,
                        latitude REAL,
                        longitude REAL,
                        data_json TEXT NOT NULL,
                        quality_score REAL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_source_type (source_type),
                        INDEX idx_timestamp (timestamp),
                        INDEX idx_location (latitude, longitude)
                    )
                ''')
                
                # Create raw data table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS raw_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_type TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        batch_id TEXT,
                        timestamp DATETIME NOT NULL,
                        record_count INTEGER,
                        data_json TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_batch_id (batch_id),
                        INDEX idx_source_timestamp (source_type, timestamp)
                    )
                ''')
                
                # Create metrics table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS ingestion_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_type TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        records_processed INTEGER,
                        records_stored INTEGER,
                        processing_time_ms INTEGER,
                        quality_score REAL,
                        errors_count INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                await db.commit()
                
            logger.info("SQLite database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
            return False
    
    async def store_processed_data(self, processed_data, source_type: str = None) -> bool:
        """Store processed data to SQLite"""
        if not aiosqlite:
            return False
        
        try:
            # Extract data from ProcessedData object
            if hasattr(processed_data, 'geospatial_data'):
                data = processed_data.geospatial_data
                source_type = processed_data.source_type
                source_id = processed_data.source_id
                timestamp = processed_data.timestamp
                quality_metrics = processed_data.quality_metrics
            else:
                data = processed_data
                source_id = 'unknown'
                timestamp = datetime.now(timezone.utc)
                quality_metrics = {}
            
            async with aiosqlite.connect(self.db_path) as db:
                for record in (data if isinstance(data, list) else [data]):
                    await db.execute('''
                        INSERT INTO processed_data 
                        (source_type, source_id, data_type, timestamp, latitude, longitude, 
                         data_json, quality_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        source_type,
                        source_id,
                        record.get('data_type'),
                        timestamp.isoformat(),
                        record.get('latitude'),
                        record.get('longitude'),
                        json.dumps(record, default=str),
                        record.get('quality_score', quality_metrics.get('average_quality_score'))
                    ))
                
                await db.commit()
            
            logger.info(f"Stored {len(data) if isinstance(data, list) else 1} records to SQLite")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store data to SQLite: {e}")
            return False
    
    async def retrieve_data(self, source_type: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Retrieve data from SQLite"""
        if not aiosqlite:
            return []
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute('''
                    SELECT * FROM processed_data 
                    WHERE source_type = ? AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                ''', (source_type, start_date.isoformat(), end_date.isoformat()))
                
                rows = await cursor.fetchall()
                
                results = []
                for row in rows:
                    record = json.loads(row['data_json'])
                    record['_storage_id'] = row['id']
                    record['_stored_at'] = row['created_at']
                    results.append(record)
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to retrieve data from SQLite: {e}")
            return []
    
    async def get_storage_metrics(self) -> Dict[str, Any]:
        """Get storage metrics"""
        if not aiosqlite:
            return {}
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Total records
                cursor = await db.execute('SELECT COUNT(*) as count FROM processed_data')
                total_records = (await cursor.fetchone())[0]
                
                # Records by source type
                cursor = await db.execute('''
                    SELECT source_type, COUNT(*) as count 
                    FROM processed_data 
                    GROUP BY source_type
                ''')
                source_counts = dict(await cursor.fetchall())
                
                # Recent activity
                cursor = await db.execute('''
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM processed_data 
                    WHERE created_at >= datetime('now', '-7 days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                ''')
                recent_activity = dict(await cursor.fetchall())
                
                return {
                    'total_records': total_records,
                    'records_by_source': source_counts,
                    'recent_activity': recent_activity,
                    'database_path': str(self.db_path)
                }
                
        except Exception as e:
            logger.error(f"Failed to get storage metrics: {e}")
            return {}

class DataStorageManager:
    """Main storage manager that coordinates different storage backends"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = StorageConfig(config)
        self.storage_backend = None
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize the appropriate storage backend"""
        try:
            if self.config.storage_type == 'file':
                self.storage_backend = FileStorage(self.config)
            elif self.config.storage_type == 'sqlite':
                self.storage_backend = SQLiteStorage(self.config)
            else:
                logger.warning(f"Unknown storage type: {self.config.storage_type}, falling back to file storage")
                self.storage_backend = FileStorage(self.config)
            
            logger.info(f"Initialized {self.config.storage_type} storage backend")
            
        except Exception as e:
            logger.error(f"Failed to initialize storage backend: {e}")
            # Fallback to file storage
            self.storage_backend = FileStorage(self.config)
    
    async def initialize(self) -> bool:
        """Initialize storage system"""
        try:
            if hasattr(self.storage_backend, 'initialize'):
                return await self.storage_backend.initialize()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
            return False
    
    async def store_processed_data(self, processed_data, source_type: str = None) -> bool:
        """Store processed data"""
        try:
            return await self.storage_backend.store_processed_data(processed_data, source_type)
        except Exception as e:
            logger.error(f"Failed to store processed data: {e}")
            return False
    
    async def store_raw_data(self, raw_data: List[Dict[str, Any]], source_type: str, source_id: str) -> bool:
        """Store raw data"""
        try:
            if hasattr(self.storage_backend, 'store_raw_data'):
                return await self.storage_backend.store_raw_data(raw_data, source_type, source_id)
            else:
                logger.warning("Raw data storage not supported by current backend")
                return False
        except Exception as e:
            logger.error(f"Failed to store raw data: {e}")
            return False
    
    async def retrieve_data(self, source_type: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Retrieve data by criteria"""
        try:
            return await self.storage_backend.retrieve_data(source_type, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to retrieve data: {e}")
            return []
    
    async def cleanup_old_data(self) -> int:
        """Clean up old data based on retention policy"""
        try:
            if hasattr(self.storage_backend, 'cleanup_old_data'):
                return await self.storage_backend.cleanup_old_data()
            else:
                logger.warning("Data cleanup not supported by current backend")
                return 0
        except Exception as e:
            logger.error(f"Failed to cleanup data: {e}")
            return 0
    
    async def get_storage_metrics(self) -> Dict[str, Any]:
        """Get comprehensive storage metrics"""
        try:
            base_metrics = {
                'storage_type': self.config.storage_type,
                'retention_days': self.config.retention_days,
                'compression_enabled': self.config.compression
            }
            
            if hasattr(self.storage_backend, 'get_storage_metrics'):
                backend_metrics = await self.storage_backend.get_storage_metrics()
                base_metrics.update(backend_metrics)
            
            return base_metrics
            
        except Exception as e:
            logger.error(f"Failed to get storage metrics: {e}")
            return {'error': str(e)}
    
    async def health_check(self) -> bool:
        """Check storage system health"""
        try:
            # Try a simple operation to verify storage is working
            test_data = [{
                'test': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }]
            
            if hasattr(self.storage_backend, 'store_raw_data'):
                result = await self.storage_backend.store_raw_data(test_data, 'health_check', 'test')
            else:
                # For backends that don't support raw data storage
                from ..processors.data_processor import ProcessedData
                test_processed = ProcessedData(
                    source_id='health_check',
                    source_type='test',
                    timestamp=datetime.now(timezone.utc),
                    geospatial_data=test_data,
                    metadata={},
                    quality_metrics={},
                    processing_info={}
                )
                result = await self.storage_backend.store_processed_data(test_processed)
            
            return result
            
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return False