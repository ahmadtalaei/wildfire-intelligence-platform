"""
Comprehensive data processor for wildfire intelligence data

data_processor is the transformation layer — it makes sure any ingested data (API, file, or stream) is standardized, validated, and ready for Kafka + downstream services.

Key methods:
1. process_batch(raw_data, config):
    - Iterates over records, runs appropriate sub-processor.
    - Filters to California region.
    - Computes quality metrics.
    - Returns a ProcessedData object.

2. Sub-processors:
_process_satellite_data: interprets fire detection (MODIS/VIIRS), cloud cover, NDVI, surface temperature.
_process_weather_data: extracts temp, humidity, winds, precipitation, calculates fire weather index.
_process_iot_data: processes air quality, weather stations, soil moisture from sensors.
_process_fire_data: parses fire incidents (acres burned, containment, cause, status).
_process_generic_data: fallback for unknown types.
_parse_timestamp: robust timestamp parser (supports many formats, Unix timestamps).
_calculate_fire_weather_index: simplified risk score (0–100) based on temperature, humidity, wind, and precipitation.
get_file_processor(filename): returns a FileProcessor.

3. FileProcessor:
Handles file ingestion for different formats:
process_file(file_path): routes to appropriate file handler.
_process_json_file: loads JSON dict/list.
_process_csv_file: converts CSV to records.
_process_geotiff_file: extracts raster statistics (min, max, mean).
_process_netcdf_file: extracts dimensions, variables, sample data points.
_process_grib_file: extracts weather fields for California subregion, samples grid points.
_process_hdf_file: extracts keys, attributes, sample dataset values.
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import geopandas as gpd
from shapely.geometry import Point, Polygon
import xarray as xr

try:
    import rasterio
    from rasterio.features import rasterize
except ImportError:
    rasterio = None

try:
    from ..geo_config.geographic_bounds import CALIFORNIA_BOUNDS_MINMAX
except ImportError:
    try:
        from geo_config.geographic_bounds import CALIFORNIA_BOUNDS_MINMAX
    except ImportError:
        # Fallback bounds if config is not available
        CALIFORNIA_BOUNDS_MINMAX = {
            'lat_min': 32.0, 'lat_max': 42.0,
            'lon_min': -124.0, 'lon_max': -114.0
        }

try:
    import h5py
except ImportError:
    h5py = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProcessedData:
    """Standardized processed data format"""
    source_id: str
    source_type: str
    timestamp: datetime
    geospatial_data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    quality_metrics: Dict[str, float]
    processing_info: Dict[str, Any]

class DataProcessor:
    """Main data processor for wildfire intelligence platform"""
    
    def __init__(self):
        self.california_bounds = CALIFORNIA_BOUNDS_MINMAX
        self.processors = {
            'satellite': self._process_satellite_data,
            'weather': self._process_weather_data,
            'iot': self._process_iot_data,
            'sensor': self._process_iot_data,
            'fire': self._process_fire_data
        }
    
    async def process_batch(self, raw_data: List[Dict[str, Any]], config) -> ProcessedData:
        """Process batch data with wildfire intelligence focus"""
        try:
            source_type = getattr(config, 'source_type', 'unknown')
            source_id = getattr(config, 'source_id', 'unknown')
            
            logger.info(f"Processing {len(raw_data)} records from {source_type}/{source_id}")
            
            # Get appropriate processor
            processor = self.processors.get(source_type, self._process_generic_data)
            
            # Process data
            processed_records = []
            quality_scores = []
            
            for record in raw_data:
                try:
                    processed_record = await processor(record, config)
                    if processed_record:
                        # Apply geospatial filtering for California
                        if self._is_in_california(processed_record):
                            processed_records.append(processed_record)
                            quality_scores.append(processed_record.get('quality_score', 1.0))
                except Exception as e:
                    logger.warning(f"Failed to process record: {e}")
                    continue
            
            # Calculate aggregate quality metrics
            quality_metrics = {
                'total_records': len(raw_data),
                'processed_records': len(processed_records),
                'processing_success_rate': len(processed_records) / len(raw_data) if raw_data else 0,
                'average_quality_score': np.mean(quality_scores) if quality_scores else 0,
                'california_filtered': True
            }
            
            return ProcessedData(
                source_id=source_id,
                source_type=source_type,
                timestamp=datetime.now(timezone.utc),
                geospatial_data=processed_records,
                metadata={
                    'processing_timestamp': datetime.now(timezone.utc).isoformat(),
                    'original_record_count': len(raw_data),
                    'filtered_record_count': len(processed_records),
                    'spatial_bounds': self.california_bounds
                },
                quality_metrics=quality_metrics,
                processing_info={
                    'processor_version': '1.0.0',
                    'config': config.__dict__ if hasattr(config, '__dict__') else str(config)
                }
            )
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise
    
    def _is_in_california(self, record: Dict[str, Any]) -> bool:
        """Check if record is within California bounds"""
        try:
            lat = record.get('latitude') or record.get('lat')
            lon = record.get('longitude') or record.get('lon')
            
            if lat is None or lon is None:
                return True  # Include if no geospatial data
            
            return (self.california_bounds['min_lat'] <= lat <= self.california_bounds['max_lat'] and
                   self.california_bounds['min_lon'] <= lon <= self.california_bounds['max_lon'])
        except:
            return True  # Include if geospatial check fails
    
    async def _process_satellite_data(self, record: Dict[str, Any], config) -> Optional[Dict[str, Any]]:
        """Process satellite data (MODIS, VIIRS, Landsat, Sentinel)"""
        try:
            processed = {
                'data_type': 'satellite',
                'sensor': record.get('sensor', 'unknown'),
                'timestamp': self._parse_timestamp(record.get('timestamp') or record.get('acquisition_date')),
                'latitude': float(record.get('latitude', record.get('lat', 0))),
                'longitude': float(record.get('longitude', record.get('lon', 0))),
                'quality_score': 1.0
            }
            
            # MODIS/VIIRS fire detection data
            if 'confidence' in record:
                processed.update({
                    'fire_confidence': record['confidence'],
                    'brightness': record.get('brightness'),
                    'bright_t31': record.get('bright_t31'),
                    'frp': record.get('frp'),  # Fire Radiative Power
                    'quality_score': min(record['confidence'] / 100.0, 1.0)
                })
            
            # Landsat/Sentinel imagery
            if 'cloud_cover' in record:
                processed.update({
                    'cloud_cover': record['cloud_cover'],
                    'quality_score': max(0, 1.0 - record['cloud_cover'] / 100.0)
                })
            
            # Add wildfire risk indicators
            if 'ndvi' in record:
                processed['vegetation_index'] = record['ndvi']
            if 'surface_temperature' in record:
                processed['surface_temperature'] = record['surface_temperature']
            
            return processed
            
        except Exception as e:
            logger.warning(f"Failed to process satellite record: {e}")
            return None
    
    async def _process_weather_data(self, record: Dict[str, Any], config) -> Optional[Dict[str, Any]]:
        """Process weather data (GFS, ERA5, NWS)"""
        try:
            processed = {
                'data_type': 'weather',
                'model': record.get('model', 'unknown'),
                'timestamp': self._parse_timestamp(record.get('timestamp') or record.get('valid_time')),
                'latitude': float(record.get('latitude', record.get('lat', 0))),
                'longitude': float(record.get('longitude', record.get('lon', 0))),
                'quality_score': 1.0
            }
            
            # Core weather variables for fire risk
            weather_vars = {
                'temperature': record.get('temperature', record.get('temp')),
                'relative_humidity': record.get('relative_humidity', record.get('rh')),
                'wind_speed': record.get('wind_speed'),
                'wind_direction': record.get('wind_direction'),
                'wind_gust': record.get('wind_gust'),
                'precipitation': record.get('precipitation', record.get('precip')),
                'pressure': record.get('pressure'),
                'dewpoint': record.get('dewpoint')
            }
            
            # Filter out None values
            processed.update({k: v for k, v in weather_vars.items() if v is not None})
            
            # Calculate fire weather indices if enough data available
            if all(k in processed for k in ['temperature', 'relative_humidity', 'wind_speed']):
                processed['fire_weather_index'] = self._calculate_fire_weather_index(
                    processed['temperature'], 
                    processed['relative_humidity'], 
                    processed['wind_speed'],
                    processed.get('precipitation', 0)
                )
            
            return processed
            
        except Exception as e:
            logger.warning(f"Failed to process weather record: {e}")
            return None
    
    async def _process_iot_data(self, record: Dict[str, Any], config) -> Optional[Dict[str, Any]]:
        """Process IoT sensor data"""
        try:
            processed = {
                'data_type': 'iot_sensor',
                'sensor_id': record.get('sensor_id', record.get('device_id')),
                'sensor_type': record.get('sensor_type', 'unknown'),
                'timestamp': self._parse_timestamp(record.get('timestamp')),
                'latitude': float(record.get('latitude', record.get('lat', 0))),
                'longitude': float(record.get('longitude', record.get('lon', 0))),
                'quality_score': 1.0
            }
            
            # Air quality sensors
            if 'pm25' in record or 'pm10' in record:
                processed.update({
                    'pm25': record.get('pm25'),
                    'pm10': record.get('pm10'),
                    'aqi': record.get('aqi'),
                    'smoke_detected': record.get('pm25', 0) > 35.0 if record.get('pm25') else False
                })
            
            # Weather station data
            if 'temperature' in record:
                processed.update({
                    'temperature': record.get('temperature'),
                    'humidity': record.get('humidity'),
                    'wind_speed': record.get('wind_speed'),
                    'wind_direction': record.get('wind_direction')
                })
            
            # Soil moisture sensors
            if 'soil_moisture' in record:
                processed.update({
                    'soil_moisture': record.get('soil_moisture'),
                    'soil_temperature': record.get('soil_temperature'),
                    'drought_indicator': record.get('soil_moisture', 100) < 20.0 if record.get('soil_moisture') else False
                })
            
            return processed
            
        except Exception as e:
            logger.warning(f"Failed to process IoT record: {e}")
            return None
    
    async def _process_fire_data(self, record: Dict[str, Any], config) -> Optional[Dict[str, Any]]:
        """Process fire incident data"""
        try:
            processed = {
                'data_type': 'fire_incident',
                'incident_id': record.get('incident_id', record.get('id')),
                'fire_name': record.get('fire_name', record.get('incident_name')),
                'timestamp': self._parse_timestamp(record.get('timestamp') or record.get('start_date')),
                'latitude': float(record.get('latitude', record.get('lat', 0))),
                'longitude': float(record.get('longitude', record.get('lon', 0))),
                'quality_score': 1.0
            }
            
            # Fire characteristics
            fire_attrs = {
                'acres_burned': record.get('acres_burned', record.get('size_acres')),
                'containment_percent': record.get('containment_percent', record.get('percent_contained')),
                'fire_cause': record.get('fire_cause', record.get('cause')),
                'fire_status': record.get('fire_status', record.get('status')),
                'evacuation_zones': record.get('evacuation_zones', [])
            }
            
            processed.update({k: v for k, v in fire_attrs.items() if v is not None})
            
            return processed
            
        except Exception as e:
            logger.warning(f"Failed to process fire record: {e}")
            return None
    
    async def _process_generic_data(self, record: Dict[str, Any], config) -> Optional[Dict[str, Any]]:
        """Generic data processor for unknown types"""
        try:
            return {
                'data_type': 'generic',
                'timestamp': self._parse_timestamp(record.get('timestamp')),
                'raw_data': record,
                'quality_score': 0.5  # Lower score for generic data
            }
        except Exception as e:
            logger.warning(f"Failed to process generic record: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: Union[str, datetime, None]) -> datetime:
        """Parse various timestamp formats"""
        if isinstance(timestamp_str, datetime):
            return timestamp_str.replace(tzinfo=timezone.utc) if timestamp_str.tzinfo is None else timestamp_str
        
        if timestamp_str is None:
            return datetime.now(timezone.utc)
        
        try:
            # Try common formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%d',
                '%Y%m%d_%H%M%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(str(timestamp_str), fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            
            # Try parsing as Unix timestamp
            try:
                return datetime.fromtimestamp(float(timestamp_str), tz=timezone.utc)
            except (ValueError, TypeError):
                pass
            
            # Default to current time if parsing fails
            logger.warning(f"Could not parse timestamp: {timestamp_str}")
            return datetime.now(timezone.utc)
            
        except Exception:
            return datetime.now(timezone.utc)
    
    def _calculate_fire_weather_index(self, temp: float, rh: float, wind_speed: float, precip: float = 0) -> float:
        """Calculate simplified fire weather index (0-100 scale)"""
        try:
            # Simplified fire weather calculation
            # Higher temperature, lower humidity, higher wind = higher fire risk
            temp_factor = min(temp / 40.0, 1.0)  # Normalize to 40degC
            humidity_factor = max(0, 1.0 - rh / 100.0)  # Invert humidity (lower = higher risk)
            wind_factor = min(wind_speed / 25.0, 1.0)  # Normalize to 25 m/s
            precip_factor = max(0, 1.0 - precip / 10.0)  # Recent precipitation reduces risk
            
            fire_index = (temp_factor * 0.3 + humidity_factor * 0.4 + wind_factor * 0.2 + precip_factor * 0.1) * 100
            return round(fire_index, 2)
            
        except Exception:
            return 50.0  # Default moderate risk
    
    async def get_file_processor(self, filename: str) -> 'FileProcessor':
        """Get appropriate file processor based on filename"""
        return FileProcessor(filename)

class FileProcessor:
    """File-specific data processor"""
    
    def __init__(self, filename: str = None):
        self.filename = filename
        self.file_path = None
        
    async def process_file(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """Process various file formats for wildfire data"""
        self.file_path = Path(file_path)
        
        try:
            suffix = self.file_path.suffix.lower()
            
            if suffix == '.json':
                return await self._process_json_file()
            elif suffix == '.csv':
                return await self._process_csv_file()
            elif suffix in ['.tif', '.tiff']:
                return await self._process_geotiff_file()
            elif suffix == '.nc':
                return await self._process_netcdf_file()
            elif suffix == '.grib' or suffix == '.grib2':
                return await self._process_grib_file()
            elif suffix == '.hdf' or suffix == '.h5':
                return await self._process_hdf_file()
            else:
                logger.warning(f"Unsupported file format: {suffix}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            return []
    
    async def _process_json_file(self) -> List[Dict[str, Any]]:
        """Process JSON file"""
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
            else:
                return [{'data': data}]
                
        except Exception as e:
            logger.error(f"Failed to process JSON file: {e}")
            return []
    
    async def _process_csv_file(self) -> List[Dict[str, Any]]:
        """Process CSV file"""
        try:
            df = pd.read_csv(self.file_path)
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to process CSV file: {e}")
            return []
    
    async def _process_geotiff_file(self) -> List[Dict[str, Any]]:
        """Process GeoTIFF raster file"""
        if not rasterio:
            logger.error("rasterio not available for GeoTIFF processing")
            return []
        
        try:
            with rasterio.open(self.file_path) as src:
                # Read raster data
                data = src.read(1)  # Read first band
                transform = src.transform
                crs = src.crs
                
                # Sample key points or create summary statistics
                records = [{
                    'file_type': 'geotiff',
                    'crs': str(crs),
                    'bounds': src.bounds,
                    'width': src.width,
                    'height': src.height,
                    'data_summary': {
                        'min': float(np.nanmin(data)),
                        'max': float(np.nanmax(data)),
                        'mean': float(np.nanmean(data)),
                        'nodata_value': src.nodata
                    }
                }]
                
                return records
                
        except Exception as e:
            logger.error(f"Failed to process GeoTIFF file: {e}")
            return []
    
    async def _process_netcdf_file(self) -> List[Dict[str, Any]]:
        """Process NetCDF file"""
        try:
            ds = xr.open_dataset(self.file_path)
            
            records = []
            
            # Extract metadata
            metadata = {
                'file_type': 'netcdf',
                'dimensions': dict(ds.dims),
                'variables': list(ds.data_vars.keys()),
                'coordinates': list(ds.coords.keys()),
                'attrs': dict(ds.attrs)
            }
            records.append(metadata)
            
            # Sample data points if it's a gridded dataset
            if 'latitude' in ds.coords or 'lat' in ds.coords:
                lat_name = 'latitude' if 'latitude' in ds.coords else 'lat'
                lon_name = 'longitude' if 'longitude' in ds.coords else 'lon'
                
                # Sample a few grid points
                lats = ds[lat_name].values
                lons = ds[lon_name].values
                
                sample_indices = np.linspace(0, len(lats)-1, min(10, len(lats)), dtype=int)
                
                for i in sample_indices:
                    try:
                        sample_record = {
                            'file_type': 'netcdf_sample',
                            'latitude': float(lats[i]),
                            'longitude': float(lons[i]),
                        }
                        
                        # Extract variable values at this location
                        for var in ds.data_vars:
                            try:
                                value = ds[var].isel({lat_name: i, lon_name: i}).values
                                if np.isscalar(value):
                                    sample_record[var] = float(value)
                                else:
                                    sample_record[var] = float(value.item()) if value.size == 1 else value.tolist()
                            except Exception:
                                continue
                        
                        records.append(sample_record)
                    except Exception:
                        continue
            
            ds.close()
            return records
            
        except Exception as e:
            logger.error(f"Failed to process NetCDF file: {e}")
            return []
    
    async def _process_grib_file(self) -> List[Dict[str, Any]]:
        """Process GRIB file"""
        try:
            # Try xarray with cfgrib first
            ds = xr.open_dataset(self.file_path, engine='cfgrib')
            
            records = []
            
            # Extract metadata
            metadata = {
                'file_type': 'grib',
                'variables': list(ds.data_vars.keys()),
                'coordinates': list(ds.coords.keys()),
                'attrs': dict(ds.attrs)
            }
            records.append(metadata)
            
            # Sample grid points
            if 'latitude' in ds.coords and 'longitude' in ds.coords:
                # Sample California region using centralized bounds
                ca_data = ds.sel(
                    latitude=slice(CALIFORNIA_BOUNDS_MINMAX['max_lat'], CALIFORNIA_BOUNDS_MINMAX['min_lat']),
                    longitude=slice(CALIFORNIA_BOUNDS_MINMAX['min_lon'], CALIFORNIA_BOUNDS_MINMAX['max_lon'])
                )
                
                # Extract sample points
                lats = ca_data.latitude.values[::5]  # Every 5th point
                lons = ca_data.longitude.values[::5]
                
                for lat in lats[:5]:  # Limit to 5 points
                    for lon in lons[:5]:
                        try:
                            sample_record = {
                                'file_type': 'grib_sample',
                                'latitude': float(lat),
                                'longitude': float(lon)
                            }
                            
                            # Extract variable values
                            for var in ca_data.data_vars:
                                try:
                                    value = ca_data[var].sel(latitude=lat, longitude=lon, method='nearest').values
                                    sample_record[var] = float(value)
                                except Exception:
                                    continue
                            
                            records.append(sample_record)
                        except Exception:
                            continue
            
            ds.close()
            return records
            
        except Exception as e:
            logger.error(f"Failed to process GRIB file: {e}")
            return []
    
    async def _process_hdf_file(self) -> List[Dict[str, Any]]:
        """Process HDF file"""
        if not h5py:
            logger.error("h5py not available for HDF processing")
            return []
        
        try:
            records = []
            
            with h5py.File(self.file_path, 'r') as f:
                # Extract file structure
                metadata = {
                    'file_type': 'hdf',
                    'keys': list(f.keys()),
                    'attrs': dict(f.attrs)
                }
                records.append(metadata)
                
                # Sample data from datasets
                def extract_datasets(name, obj):
                    if isinstance(obj, h5py.Dataset):
                        try:
                            # Sample small datasets completely, large ones partially
                            if obj.size < 1000:
                                data = obj[:]
                            else:
                                # Sample first few elements
                                data = obj[:min(10, obj.shape[0])] if len(obj.shape) > 0 else obj[()]
                            
                            dataset_record = {
                                'file_type': 'hdf_dataset',
                                'dataset_name': name,
                                'shape': obj.shape,
                                'dtype': str(obj.dtype),
                                'attrs': dict(obj.attrs),
                                'sample_data': data.tolist() if hasattr(data, 'tolist') else str(data)
                            }
                            records.append(dataset_record)
                        except Exception as e:
                            logger.warning(f"Failed to extract dataset {name}: {e}")
                
                f.visititems(extract_datasets)
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to process HDF file: {e}")
            return []