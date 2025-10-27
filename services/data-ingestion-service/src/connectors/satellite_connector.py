"""
Satellite Data Connector
Handles data ingestion from various satellite sources (MODIS, VIIRS, Landsat, Sentinel)
"""

import asyncio
import aiohttp
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, AsyncGenerator
import structlog
from pathlib import Path
import time

# Import centralized conversion utilities
from .timezone_converter import utc_to_pacific, utcnow_pacific
from .unit_converter import convert_temperature
from .metrics import INGESTION_LATENCY, VALIDATION_TOTAL, VALIDATION_PASSED, RECORDS_PROCESSED

from ..models.ingestion import DataSource, StreamingConfig, BatchConfig
# NOTE: Satellite API clients would be imported here when implemented
# from utils.satellite_apis import MODISClient, VIIRSClient, LandsatClient, SentinelClient

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

logger = structlog.get_logger()


class SatelliteDataConnector:
    """Advanced satellite data connector with support for multiple providers"""

    def __init__(self, kafka_producer=None):
        self.active_streams: Dict[str, Dict] = {}
        self.kafka_producer = kafka_producer
        # Initialize satellite API clients when credentials are available
        self.clients = {}

        # API endpoint configuration
        self.usgs_api_host = "earthexplorer.usgs.gov"
        self.esa_copernicus_host = "scihub.copernicus.eu"
        self.esa_copernicus_path = "dhus"

        self._initialize_api_clients()
        self.data_sources = []
        self._initialize_default_sources()
    
    def _initialize_api_clients(self):
        """Initialize satellite API clients based on available credentials"""
        # Check for USGS credentials
        if os.getenv('USGS_USERNAME') and os.getenv('USGS_PASSWORD'):
            logger.info("USGS credentials found - Landsat access available")
            # self.clients['landsat'] = LandsatClient() # Would initialize when implemented

        # Check for Copernicus OAuth2 credentials
        if os.getenv('COPERNICUS_CLIENT_ID') and os.getenv('COPERNICUS_CLIENT_SECRET'):
            try:
                from ..utils.sentinel_client import SentinelClient
                self.clients['sentinel'] = SentinelClient()
                logger.info("Copernicus OAuth2 credentials found - Sentinel access enabled")
            except Exception as e:
                logger.error("Failed to initialize Sentinel client", error=str(e))
    
    def _initialize_default_sources(self):
        """Initialize satellite data sources (excluding fire detection - handled by nasa_firms_connector)"""
        self.data_sources = [
            # NOTE: MODIS/VIIRS fire detection moved to nasa_firms_connector.py to avoid duplication
            DataSource(
                id="sat_landsat_thermal",
                name="Landsat Thermal Infrared",
                source_type="satellite",
                description="Thermal infrared imagery from Landsat satellites for fire detection and monitoring",
                provider="USGS Landsat",
                formats=["geotiff", "hdf", "netcdf"],
                update_frequency="16-day revisit cycle",
                spatial_resolution="30m (thermal: 100m resampled to 30m)",
                temporal_resolution="16 days",
                is_active=True,
                api_endpoint=f"https://{self.usgs_api_host}",
                authentication_required=True
            ),
            DataSource(
                id="sat_sentinel2_msi",
                name="Sentinel-2 MSI",
                source_type="satellite",
                description="High-resolution multispectral imagery from Sentinel-2 MultiSpectral Instrument",
                provider="ESA Copernicus",
                formats=["safe", "geotiff", "jp2"],
                update_frequency="5-day revisit cycle",
                spatial_resolution="10m, 20m, 60m (band dependent)",
                temporal_resolution="5 days",
                is_active=True,
                api_endpoint=f"https://{self.esa_copernicus_host}/{self.esa_copernicus_path}",
                authentication_required=True
            ),
            DataSource(
                id="sat_sentinel3_slstr",
                name="Sentinel-3 SLSTR",
                source_type="satellite",
                description="Sea and Land Surface Temperature Radiometer data for thermal monitoring",
                provider="ESA Copernicus",
                formats=["netcdf", "safe"],
                update_frequency="Daily (< 1 day revisit)",
                spatial_resolution="500m (thermal), 1km (fire)",
                temporal_resolution="Daily",
                is_active=True,
                api_endpoint=f"https://{self.esa_copernicus_host}/{self.esa_copernicus_path}",
                authentication_required=True
            )
        ]
    
    def _get_firms_source_id(self, satellite: str, instrument: str) -> str:
        """
        Generate source_id for FIRMS data based on satellite/instrument
        
        Args:
            satellite: Satellite name (e.g., 'Aqua', 'Terra', 'Suomi NPP', 'NOAA-20', 'NOAA-21')
            instrument: Instrument name ('MODIS' or 'VIIRS')
        
        Returns:
            source_id for TableRouter
        """
        if not satellite or not instrument:
            return 'fire_incidents'  # Fallback
        
        satellite_lower = satellite.lower().replace(' ', '').replace('-', '')
        instrument_lower = instrument.lower()
        
        if instrument_lower == 'modis':
            if 'aqua' in satellite_lower:
                return 'firms_modis_aqua'
            elif 'terra' in satellite_lower:
                return 'firms_modis_terra'
        elif instrument_lower == 'viirs':
            if 'suomi' in satellite_lower or 'snpp' in satellite_lower:
                return 'firms_viirs_snpp'
            elif 'noaa20' in satellite_lower or 'noaa-20' in satellite:
                return 'firms_viirs_noaa20'
            elif 'noaa21' in satellite_lower or 'noaa-21' in satellite:
                return 'firms_viirs_noaa21'
        
        return 'fire_incidents'  # Fallback
    
    async def health_check(self) -> bool:
        """Check connectivity to satellite data providers"""
        try:
            # Check NASA FIRMS API
            async with aiohttp.ClientSession() as session:
                async with session.get("https://firms.modaps.eosdis.nasa.gov/api/") as response:
                    if response.status != 200:
                        return False
            
            # Check USGS services
            async with aiohttp.ClientSession() as session:
                async with session.get("https://earthexplorer.usgs.gov/inventory/json/v/1.4.1/") as response:
                    if response.status not in [200, 405]:  # 405 is expected for GET on this endpoint
                        return False
            
            logger.info("Satellite connector health check passed")
            return True
            
        except Exception as e:
            logger.error("Satellite connector health check failed", error=str(e))
            return False
    
    async def get_sources(self) -> List[DataSource]:
        """Get list of available satellite data sources"""
        return self.data_sources
    
    async def add_source(self, source: DataSource) -> DataSource:
        """Add new satellite data source"""
        # Generate ID if not provided
        if not source.id:
            source.id = f"sat_{source.name.lower().replace(' ', '_')}"
        
        # Add to sources list
        self.data_sources.append(source)
        
        logger.info("Added new satellite data source", source_id=source.id, name=source.name)
        return source
    
    async def fetch_batch_data(self, config: BatchConfig) -> List[Dict[str, Any]]:
        """
        Fetch batch satellite data based on configuration
        
        Supports multiple formats and time ranges:
        - MODIS/VIIRS active fire data
        - Landsat thermal imagery
        - Sentinel multispectral data
        """
        try:
            logger.info("Fetching batch satellite data", 
                       source_id=config.source_id,
                       date_range=f"{config.start_date} to {config.end_date}")
            
            # Get data source configuration
            source = next((s for s in self.data_sources if s.id == config.source_id), None)
            if not source:
                raise ValueError(f"Unknown source ID: {config.source_id}")
            
            # Route to appropriate client based on source
            if "modis" in config.source_id:
                data = await self._fetch_modis_data(config, source)
            elif "viirs" in config.source_id:
                data = await self._fetch_viirs_data(config, source)
            elif "landsat" in config.source_id:
                data = await self._fetch_landsat_data(config, source)
            elif "sentinel" in config.source_id:
                data = await self._fetch_sentinel_data(config, source)
            else:
                raise ValueError(f"Unsupported satellite source: {config.source_id}")
            
            logger.info("Batch satellite data fetched successfully", 
                       source_id=config.source_id,
                       records=len(data))
            
            return data
            
        except Exception as e:
            logger.error("Failed to fetch batch satellite data", 
                        source_id=config.source_id, error=str(e))
            raise
    
    async def start_streaming(self, config: StreamingConfig) -> str:
        """
        Start real-time streaming of satellite data
        
        Establishes continuous monitoring of satellite data feeds with
        configurable polling intervals and data filters.
        """
        try:
            stream_id = f"stream_{config.source_id}_{datetime.now().timestamp()}"
            
            logger.info("Starting satellite data stream", 
                       stream_id=stream_id,
                       source_id=config.source_id)
            
            # Create stream configuration
            stream_config = {
                'stream_id': stream_id,
                'source_id': config.source_id,
                'config': config,
                'status': 'active',
                'start_time': datetime.now(),
                'last_update': None,
                'records_streamed': 0
            }
            
            self.active_streams[stream_id] = stream_config
            
            # Start background streaming task
            asyncio.create_task(self._run_stream(stream_config))
            
            logger.info("Satellite data stream started", stream_id=stream_id)
            return stream_id
            
        except Exception as e:
            logger.error("Failed to start satellite data stream", error=str(e))
            raise
    
    async def stop_streaming(self, stream_id: str) -> bool:
        """Stop satellite data streaming"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id]['status'] = 'stopped'
            del self.active_streams[stream_id]
            logger.info("Satellite data stream stopped", stream_id=stream_id)
            return True
        return False
    
    async def get_active_streams(self) -> List[Dict[str, Any]]:
        """Get list of active satellite data streams"""
        return [
            {
                'stream_id': stream_id,
                'source_id': config['source_id'],
                'status': config['status'],
                'start_time': config['start_time'].isoformat(),
                'records_streamed': config['records_streamed']
            }
            for stream_id, config in self.active_streams.items()
        ]
    
    async def get_data_rate(self) -> Dict[str, float]:
        """Get current data ingestion rate"""
        total_records = sum(stream['records_streamed'] for stream in self.active_streams.values())
        active_duration = sum(
            (datetime.now() - stream['start_time']).total_seconds() / 3600
            for stream in self.active_streams.values()
        )
        
        return {
            'records_per_hour': total_records / max(active_duration, 1),
            'active_streams': len(self.active_streams),
            'total_records': total_records
        }
    
    async def _run_stream(self, stream_config: Dict[str, Any]):
        """Background task for continuous satellite data streaming"""
        stream_id = stream_config['stream_id']
        config = stream_config['config']

        logger.info("Starting stream processing loop", stream_id=stream_id)

        try:
            while stream_config['status'] == 'active':
                # Start timing for latency measurement
                start_time = time.time()

                # Fetch latest data
                # For satellite data, query last 7 days to account for processing delays
                # Sentinel data typically has 1-5 day delay
                end_date = date.today()
                start_date = end_date - timedelta(days=7)

                batch_config = BatchConfig(
                    source_id=config.source_id,
                    start_date=start_date,
                    end_date=end_date,
                    spatial_bounds=config.spatial_bounds,
                    format=config.preferred_format or "json"
                )

                try:
                    data = await self.fetch_batch_data(batch_config)

                    # Record ingestion latency
                    latency = time.time() - start_time
                    INGESTION_LATENCY.labels(source=config.source_id, job='data-ingestion-service').observe(latency)

                    if data:
                        # Validate data and record metrics
                        for record in data:
                            VALIDATION_TOTAL.labels(source=config.source_id, job='data-ingestion-service').inc()

                            # Quality check - records with valid coordinates are valid
                            if (record.get('latitude') is not None and
                                record.get('longitude') is not None):
                                VALIDATION_PASSED.labels(source=config.source_id, job='data-ingestion-service').inc()

                        # Record processed records
                        RECORDS_PROCESSED.labels(source=config.source_id, job='data-ingestion-service').inc(len(data))

                        # Send data to Kafka
                        if self.kafka_producer:
                            try:
                                await self.kafka_producer.send_batch_data(
                                    source_id=config.source_id,
                                    data=data
                                )
                                logger.info("Satellite data sent to Kafka",
                                          stream_id=stream_id,
                                          source_id=config.source_id,
                                          records=len(data),
                                          latency_seconds=latency)
                            except Exception as kafka_error:
                                logger.error("Failed to send satellite data to Kafka",
                                           stream_id=stream_id,
                                           error=str(kafka_error))

                        stream_config['records_streamed'] += len(data)
                        stream_config['last_update'] = datetime.now()

                        logger.info("Stream data processed",
                                   stream_id=stream_id,
                                   records=len(data),
                                   latency_seconds=latency)

                except Exception as e:
                    logger.error("Stream processing error",
                                stream_id=stream_id, error=str(e))

                # Wait for next polling interval
                await asyncio.sleep(config.polling_interval_seconds)

        except asyncio.CancelledError:
            logger.info("Stream cancelled", stream_id=stream_id)
        except Exception as e:
            logger.error("Stream processing failed", stream_id=stream_id, error=str(e))
            stream_config['status'] = 'error'
    
    async def _fetch_modis_data(self, config: BatchConfig, source: DataSource) -> List[Dict[str, Any]]:
        """Fetch MODIS active fire data using FIRMS API"""
        try:
            client = self.clients['firms']
            
            # Configure spatial bounds (California by default)
            bounds = config.spatial_bounds or CALIFORNIA_BOUNDS.copy()
            
            # Calculate days back from date range
            days_back = min((config.end_date - config.start_date).days + 1, 10)  # FIRMS max 10 days
            
            # Use USA-optimized data access for real-time MODIS data
            # This provides better performance and real-time updates for US data
            try:
                data = await client.get_usa_fire_data(
                    source='MODIS_C6_1',  # Use MODIS Collection 6.1
                    start_date=config.end_date,
                    days_back=days_back
                )
            except Exception as e:
                logger.warning("USA fire data access failed, falling back to area API", error=str(e))
                # Fallback to area-based API if USA method fails
                data = await client.get_active_fire_data_by_area(
                    source='MODIS_C6_1',  # Use MODIS Collection 6.1 NRT
                    area=bounds,
                    start_date=config.end_date,  # FIRMS uses end date as reference
                    days_back=days_back,
                    format='csv'
                )
            
            # Transform to standard format
            standardized_data = []
            for record in data:
                standardized_record = {
                    'timestamp': self._parse_modis_datetime(record.get('acq_date', ''), record.get('acq_time', '')),
                    'latitude': float(record.get('latitude', 0)),
                    'longitude': float(record.get('longitude', 0)),
                    'confidence': int(record.get('confidence', 0)),
                    'brightness': float(record.get('brightness', 0)),
                    'fire_radiative_power': float(record.get('frp', 0)),
                    'satellite': record.get('satellite', ''),
                    'instrument': 'MODIS',
                    'scan': int(record.get('scan', 0)),
                    'track': int(record.get('track', 0)),
                    'acquisition_date': record.get('acq_date', ''),
                    'acquisition_time': record.get('acq_time', ''),
                    'daynight': record.get('daynight', ''),
                    'source': 'MODIS_FIRMS',
                    'source_id': self._get_firms_source_id(record.get('satellite', ''), 'MODIS'),  # For TableRouter routing
                    'provider': 'NASA FIRMS',
                    'data_quality': self._assess_data_quality(record)
                }
                standardized_data.append(standardized_record)
            
            logger.info("MODIS FIRMS data processed", 
                       source="MODIS_C6_1", records=len(standardized_data))
            return standardized_data
            
        except Exception as e:
            logger.error("MODIS FIRMS data fetch failed", error=str(e))
            raise
    
    async def _fetch_viirs_data(self, config: BatchConfig, source: DataSource) -> List[Dict[str, Any]]:
        """Fetch VIIRS active fire data using FIRMS API"""
        try:
            client = self.clients['firms']
            
            bounds = config.spatial_bounds or CALIFORNIA_BOUNDS.copy()
            
            # Calculate days back from date range
            days_back = min((config.end_date - config.start_date).days + 1, 10)  # FIRMS max 10 days
            
            # Use USA-optimized data access for real-time VIIRS data
            # This provides better performance and real-time updates for US data
            data = await client.get_usa_fire_data(
                source='VIIRS_SNPP_C2',  # Use VIIRS S-NPP Collection 2
                start_date=config.end_date,
                days_back=days_back
            )
            
            # Transform to standard format
            standardized_data = []
            for record in data:
                standardized_record = {
                    'timestamp': self._parse_modis_datetime(record.get('acq_date', ''), record.get('acq_time', '')),
                    'latitude': float(record.get('latitude', 0)),
                    'longitude': float(record.get('longitude', 0)),
                    'confidence': record.get('confidence', ''),  # VIIRS confidence is categorical (low/nominal/high)
                    'brightness_ti4': float(record.get('bright_ti4', 0)),  # Channel I-4 brightness temperature
                    'brightness_ti5': float(record.get('bright_ti5', 0)),  # Channel I-5 brightness temperature
                    'fire_radiative_power': float(record.get('frp', 0)),
                    'satellite': record.get('satellite', ''),
                    'instrument': 'VIIRS',
                    'scan': float(record.get('scan', 0)),
                    'track': float(record.get('track', 0)),
                    'acquisition_date': record.get('acq_date', ''),
                    'acquisition_time': record.get('acq_time', ''),
                    'daynight': record.get('daynight', ''),
                    'type': record.get('type', ''),  # VIIRS detection type
                    'source': 'VIIRS_FIRMS',
                    'source_id': self._get_firms_source_id(record.get('satellite', ''), 'VIIRS'),  # For TableRouter routing
                    'provider': 'NASA FIRMS',
                    'data_quality': self._assess_data_quality(record)
                }
                standardized_data.append(standardized_record)
            
            logger.info("VIIRS FIRMS data processed", 
                       source="VIIRS_SNPP_C2", records=len(standardized_data))
            return standardized_data
            
        except Exception as e:
            logger.error("VIIRS FIRMS data fetch failed", error=str(e))
            raise
    
    async def _fetch_landsat_data(self, config: BatchConfig, source: DataSource) -> List[Dict[str, Any]]:
        """Fetch Landsat thermal imagery data"""
        try:
            # Check if Landsat client is configured
            if 'landsat' not in self.clients:
                logger.info("Landsat API client not configured - requires USGS_USERNAME and USGS_PASSWORD",
                           source_id=config.source_id)
                return []

            client = self.clients['landsat']
            
            # Use simplified STAC API for Landsat thermal data
            # Use CALIFORNIA_BOUNDS in consistent lat/lon format
            if config.spatial_bounds:
                bounds = config.spatial_bounds
            else:
                bounds = CALIFORNIA_BOUNDS.copy()
            
            scenes = await client.search_scenes(
                bounds=bounds,
                start_date=config.start_date,
                end_date=config.end_date,
                collection='landsat-c2l2-st',  # Use Surface Temperature for fire detection
                cloud_cover_max=20
            )
            
            # Return scene metadata with thermal band information
            standardized_data = []
            for scene in scenes:
                standardized_record = {
                    'timestamp': utc_to_pacific(scene.get('acquisition_date')) if scene.get('acquisition_date') else utcnow_pacific(),
                    'scene_id': scene.get('scene_id', ''),
                    'satellite': scene.get('satellite', 'Landsat'),
                    'collection': scene.get('collection', ''),
                    'path': scene.get('path', 0),
                    'row': scene.get('row', 0),
                    'cloud_cover': float(scene.get('cloud_cover', 0)),
                    'processing_level': scene.get('processing_level', ''),
                    'thermal_bands': scene.get('thermal_bands', []),
                    'download_urls': scene.get('download_urls', {}),
                    'scene_bounds': scene.get('scene_bounds', {}),
                    'source': 'Landsat_STAC',
                    'source_id': 'sat_landsat_thermal',  # For TableRouter routing to landsat_thermal_imagery table
                    'provider': 'USGS Landsat',
                    'access_method': scene.get('access_method', 'STAC_API'),
                    'data_type': 'thermal_imagery'
                }
                standardized_data.append(standardized_record)
            
            return standardized_data
            
        except Exception as e:
            logger.error("Landsat data fetch failed", error=str(e))
            raise
    
    async def _fetch_sentinel_data(self, config: BatchConfig, source: DataSource) -> List[Dict[str, Any]]:
        """Fetch Sentinel satellite data using OAuth2"""
        try:
            # Check if Sentinel client is configured
            if 'sentinel' not in self.clients:
                logger.info("Sentinel API client not configured - requires COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET",
                           source_id=config.source_id)
                return []

            client = self.clients['sentinel']
            bounds = config.spatial_bounds or CALIFORNIA_BOUNDS.copy()

            if "sentinel2" in config.source_id:
                # Search for Sentinel-2 MSI products
                products = await client.search_sentinel2(
                    start_date=config.start_date,
                    end_date=config.end_date,
                    bounds=bounds,
                    cloud_cover_max=30
                )

                standardized_data = []
                for product in products:
                    # Parse ContentDate for timestamp
                    content_date = product.get('ContentDate', {})
                    timestamp = content_date.get('Start', '')

                    # Extract cloud cover from Attributes
                    cloud_cover = 0.0
                    for attr in product.get('Attributes', []):
                        if attr.get('Name') == 'cloudCover':
                            cloud_cover = float(attr.get('Value', 0))
                            break

                    standardized_record = {
                        'timestamp': utc_to_pacific(timestamp) if timestamp else utcnow_pacific(),
                        'product_id': product.get('Id', ''),
                        'product_name': product.get('Name', ''),
                        'satellite': 'Sentinel-2',
                        'instrument': 'MSI',
                        'cloud_cover': cloud_cover,
                        'size_mb': product.get('ContentLength', 0) / (1024 * 1024),
                        'footprint': product.get('GeoFootprint', {}).get('coordinates', []),
                        'download_url': f"{self.esa_copernicus_host}/odata/v1/Products({product.get('Id')})",
                        'source': 'Sentinel-2_MSI',
                        'source_id': 'sat_sentinel2_msi',  # Add source_id for consumer routing
                        'provider': 'ESA Copernicus',
                        'data_type': 'multispectral_imagery'
                    }

                    # Selectively download and store imagery to S3
                    if await client.should_download_product(product, 'sentinel-2'):
                        s3_path = await client.download_product(product.get('Id'), product.get('Name'))
                        if s3_path:
                            standardized_record['s3_path'] = s3_path
                            logger.info("Sentinel-2 product downloaded",
                                       product_id=product.get('Id'),
                                       s3_path=s3_path)

                    standardized_data.append(standardized_record)

                logger.info("Sentinel-2 data processed", records=len(standardized_data))
                return standardized_data

            elif "sentinel3" in config.source_id:
                # Search for Sentinel-3 SLSTR thermal products
                products = await client.search_sentinel3(
                    start_date=config.start_date,
                    end_date=config.end_date,
                    bounds=bounds,
                    product_type='SL_2_LST___'  # Land Surface Temperature
                )

                standardized_data = []
                for product in products:
                    # Parse ContentDate for timestamp
                    content_date = product.get('ContentDate', {})
                    timestamp = content_date.get('Start', '')

                    standardized_record = {
                        'timestamp': utc_to_pacific(timestamp) if timestamp else utcnow_pacific(),
                        'product_id': product.get('Id', ''),
                        'product_name': product.get('Name', ''),
                        'satellite': 'Sentinel-3',
                        'instrument': 'SLSTR',
                        'size_mb': product.get('ContentLength', 0) / (1024 * 1024),
                        'footprint': product.get('GeoFootprint', {}).get('coordinates', []),
                        'download_url': f"{self.esa_copernicus_host}/odata/v1/Products({product.get('Id')})",
                        'source': 'Sentinel-3_SLSTR',
                        'source_id': 'sat_sentinel3_slstr',  # Add source_id for consumer routing
                        'provider': 'ESA Copernicus',
                        'data_type': 'thermal_imagery'
                    }

                    # Selectively download and store imagery to S3
                    # All Sentinel-3 thermal data is valuable for fire detection
                    if await client.should_download_product(product, 'sentinel-3'):
                        s3_path = await client.download_product(product.get('Id'), product.get('Name'))
                        if s3_path:
                            standardized_record['s3_path'] = s3_path
                            logger.info("Sentinel-3 product downloaded",
                                       product_id=product.get('Id'),
                                       s3_path=s3_path)

                    standardized_data.append(standardized_record)

                logger.info("Sentinel-3 data processed", records=len(standardized_data))
                return standardized_data

        except Exception as e:
            logger.error("Sentinel data fetch failed", error=str(e))
            raise
    
    async def fetch_fire_data(self, config: BatchConfig) -> List[Dict[str, Any]]:
        """
        Fetch fire detection data from satellite sources
        Note: This method delegates to fetch_batch_data for consistency
        """
        logger.info("Fetching fire detection data from satellite sources", source_id=config.source_id)
        return await self.fetch_batch_data(config)

    def _parse_modis_datetime(self, acq_date: str, acq_time: str) -> str:
        """Parse MODIS date/time format to ISO format in PST timezone
        
        Args:
            acq_date: YYYY-MM-DD format
            acq_time: HHMM format (e.g., "0902" or "1643")
        
        Returns:
            ISO format timestamp string in Pacific Time
        """
        try:
            from datetime import datetime
            from .timezone_converter import datetime_to_pacific_str
            
            # Pad time to 4 characters if needed
            padded_time = str(acq_time).zfill(4)
            
            # Parse as UTC datetime
            utc_dt = datetime.strptime(f"{acq_date} {padded_time[:2]}:{padded_time[2:]}", '%Y-%m-%d %H:%M')
            
            # Convert UTC to Pacific Time
            pacific_str = datetime_to_pacific_str(utc_dt)
            
            return pacific_str
        except Exception as e:
            logger.error("Failed to parse MODIS datetime", acq_date=acq_date, acq_time=acq_time, error=str(e))
            from .timezone_converter import utcnow_pacific
            return utcnow_pacific()

    def _assess_data_quality(self, record: Dict[str, Any]) -> float:
        """Assess data quality score for satellite record"""
        quality_score = 1.0

        # Check for missing critical fields
        critical_fields = ['latitude', 'longitude', 'confidence']
        for field in critical_fields:
            if not record.get(field):
                quality_score -= 0.2

        # Check confidence level
        confidence = record.get('confidence', 0)
        if confidence < 50:
            quality_score -= 0.3
        elif confidence < 75:
            quality_score -= 0.1

        # Check for reasonable coordinate values
        lat = record.get('latitude', 0)
        lon = record.get('longitude', 0)
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            quality_score -= 0.4

        return max(0.0, quality_score)