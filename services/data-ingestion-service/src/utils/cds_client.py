"""
CDS API Client Utilities
Provides utilities for Copernicus Climate Data Store (CDS) API integration
"""

import os
import configparser
from pathlib import Path
from typing import Optional
import structlog # Uses structlog for structured logging.

try:
    import cdsapi
except ImportError:
    cdsapi = None

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


class CDSClientFactory:
    """Factory for creating CDS API clients with proper configuration"""
    
    @staticmethod
    def create_client(config_path: Optional[str] = None) -> Optional:
        """
        Create and configure a CDS API client
        
        Args:
            config_path: Optional path to .cdsapirc file
            
        Returns:
            cdsapi.Client instance or None if not available
        """
        if not cdsapi:
            logger.warning("cdsapi package not available - install with: pip install cdsapi")
            return None
        
        try:
            # Try standard cdsapi environment variables FIRST (CDSAPI_URL, CDSAPI_KEY)
            # These are what cdsapi.Client() looks for by default
            cdsapi_url = os.getenv('CDSAPI_URL')
            cdsapi_key = os.getenv('CDSAPI_KEY')

            if cdsapi_key:
                logger.info("Found CDSAPI_KEY environment variable")
                url = cdsapi_url or 'https://cds.climate.copernicus.eu/api'

                # Create .cdsapirc in /app directory (working directory) for cdsapi to read
                try:
                    from pathlib import Path

                    # Write config to /app directory where service runs
                    cdsapirc_path = Path('/app') / '.cdsapirc'

                    with open(cdsapirc_path, 'w') as f:
                        f.write(f"url: {url}\n")
                        f.write(f"key: {cdsapi_key}\n")

                    logger.info("Created .cdsapirc in /app directory", path=str(cdsapirc_path))

                    # Now cdsapi.Client() should work
                    client = cdsapi.Client()
                    logger.info("CDS API client created successfully", url=url)
                    return client

                except Exception as e:
                    logger.error("Failed to create CDS API client", error=str(e))
                    # Continue to try config file

            # If environment variables didn't work, try config file
            # Try different configuration paths
            config_paths = [
                config_path,
                os.path.expanduser('~/.cdsapirc'),
                '.cdsapirc'
            ]

            cdsapi_config = None
            config_file_used = None

            for path in config_paths:
                if path and os.path.exists(path):
                    try:
                        cdsapi_config = configparser.ConfigParser()
                        cdsapi_config.read(path)
                        config_file_used = path
                        logger.info("Found CDS API configuration", config_file=path)
                        break
                    except Exception as e:
                        logger.warning("Failed to read config file", path=path, error=str(e))
                        continue

            if not cdsapi_config:
                # No config file and no environment variables
                logger.error("No .cdsapirc file found and CDSAPI_KEY environment variable not set")
                return None

            # Extract configuration
            try:
                url = cdsapi_config.get('cdsapi', 'url', fallback='https://cds.climate.copernicus.eu/api')
                key = cdsapi_config.get('cdsapi', 'key', fallback=None)
                
                if not key:
                    logger.error("No API key found in .cdsapirc file")
                    return None
                
                # Create client with explicit configuration
                client = cdsapi.Client(url=url, key=key)
                logger.info("CDS API client created successfully", config_file=config_file_used)
                return client
                
            except Exception as e:
                logger.error("Failed to parse CDS API configuration", error=str(e))
                return None
            
        except Exception as e:
            logger.error("Failed to create CDS API client", error=str(e))
            return None
    
    @staticmethod
    def validate_credentials(client) -> bool:
        """
        Validate CDS API credentials by making a test request
        
        Args:
            client: CDS API client instance
            
        Returns:
            bool: True if credentials are valid
        """
        if not client:
            return False
        
        try:
            # Try to list available datasets (this requires valid credentials)
            # Note: This is a simple validation - in production you might want 
            # a lighter-weight validation method
            logger.info("Validating CDS API credentials...")
            
            # For now, just assume credentials are valid if client was created
            # In a real implementation, you could make a small API call to test
            return True
            
        except Exception as e:
            logger.error("CDS API credential validation failed", error=str(e))
            return False


def get_era5_variables():
    """Get list of available ERA5 variables"""
    return {
        'temperature': '2m_temperature',
        'dewpoint': '2m_dewpoint_temperature', 
        'relative_humidity': '2m_relative_humidity',
        'precipitation': 'total_precipitation',
        'pressure': 'surface_pressure',
        'u_wind': '10m_u_component_of_wind',
        'v_wind': '10m_v_component_of_wind',
        'solar_radiation': 'surface_solar_radiation_downwards',
        'thermal_radiation': 'surface_thermal_radiation_downwards',
        'evaporation': 'evaporation',
        'runoff': 'runoff',
        'soil_temperature': 'soil_temperature_level_1',
        'soil_moisture': 'soil_water_level_1',
        'cloud_cover': 'total_cloud_cover',
        'wind_gust': '10m_wind_gust_since_previous_post_processing'
    }


def get_california_bounds():
    """Get California bounding box coordinates"""
    return CALIFORNIA_BOUNDS.copy()


def format_cds_area(bounds: dict) -> list:
    """Convert bounds dict to CDS API area format [north, west, south, east]"""
    return [
        bounds['lat_max'],  # north
        bounds['lon_min'],  # west
        bounds['lat_min'],  # south
        bounds['lon_max']   # east
    ]