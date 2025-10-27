"""
Sentinel OAuth2 Client for Copernicus Data Space
Provides OAuth2 authentication and query utilities for Sentinel-2 and Sentinel-3 data
"""

import os
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import structlog
from minio import Minio
from minio.error import S3Error
from io import BytesIO
import asyncio

# Import centralized geographic bounds
try:
    from ..geo_config.geographic_bounds import CALIFORNIA_BOUNDS
except ImportError:
    try:
        from geo_config.geographic_bounds import CALIFORNIA_BOUNDS
    except ImportError:
        # Fallback bounds
        CALIFORNIA_BOUNDS = {
            'lat_min': 32.534156,
            'lat_max': 42.009518,
            'lon_min': -124.482003,
            'lon_max': -114.131211
        }

logger = structlog.get_logger()


class SentinelClient:
    """Client for Copernicus Data Space Sentinel API with OAuth2 authentication"""

    # OAuth2 token endpoint
    TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

    # OData API base URL
    ODATA_BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1"

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, enable_s3: bool = True):
        """
        Initialize Sentinel client with OAuth2 credentials

        Args:
            client_id: OAuth2 client ID (defaults to COPERNICUS_CLIENT_ID env var)
            client_secret: OAuth2 client secret (defaults to COPERNICUS_CLIENT_SECRET env var)
            enable_s3: Whether to enable S3/MinIO storage (default: True)
        """
        # Client credentials for catalogue queries
        self.client_id = client_id or os.getenv('COPERNICUS_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('COPERNICUS_CLIENT_SECRET')

        # Username/password for downloads
        self.username = os.getenv('COPERNICUS_USERNAME')
        self.password = os.getenv('COPERNICUS_PASSWORD')

        if not self.client_id or not self.client_secret:
            raise ValueError("COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET must be set")

        # Separate tokens for different grant types
        self._catalogue_token = None  # client_credentials token for queries
        self._catalogue_token_expiry = None
        self._download_token = None   # password grant token for downloads
        self._download_token_expiry = None

        # Initialize MinIO client for S3 storage
        self.s3_client = None
        self.s3_bucket = None
        if enable_s3:
            self._initialize_s3_client()

        # Check which auth methods are available
        has_download_auth = bool(self.username and self.password and
                                self.username != 'configured_via_oauth' and
                                self.password != 'configured_via_oauth')

        logger.info("Sentinel client initialized with OAuth2 credentials",
                   s3_enabled=self.s3_client is not None,
                   download_auth_available=has_download_auth)

    def _initialize_s3_client(self):
        """Initialize MinIO/S3 client for object storage"""
        try:
            s3_endpoint = os.getenv('S3_ENDPOINT', 'localhost:9000')
            # Remove http:// or https:// prefix if present
            s3_endpoint = s3_endpoint.replace('http://', '').replace('https://', '')

            self.s3_client = Minio(
                s3_endpoint,
                access_key=os.getenv('S3_ACCESS_KEY', 'minioadmin'),
                secret_key=os.getenv('S3_SECRET_KEY', 'minioadminpassword'),
                secure=False  # Use HTTP for local MinIO
            )

            self.s3_bucket = os.getenv('S3_BUCKET', 'wildfire-data')

            # Create bucket if it doesn't exist
            if not self.s3_client.bucket_exists(self.s3_bucket):
                self.s3_client.make_bucket(self.s3_bucket)
                logger.info("Created S3 bucket", bucket=self.s3_bucket)

            logger.info("S3 client initialized successfully", endpoint=s3_endpoint, bucket=self.s3_bucket)
        except Exception as e:
            logger.error("Failed to initialize S3 client", error=str(e))
            self.s3_client = None

    async def _get_catalogue_token(self) -> str:
        """
        Get OAuth2 access token for catalogue queries (client_credentials grant)

        Returns:
            str: Valid access token for catalogue access
        """
        # Return cached token if still valid
        if self._catalogue_token and self._catalogue_token_expiry and datetime.now() < self._catalogue_token_expiry:
            return self._catalogue_token

        logger.info("Requesting new catalogue OAuth2 token (client_credentials)")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if response.status_code != 200:
                logger.error("Catalogue token request failed",
                           status=response.status_code,
                           response=response.text)
                raise Exception(f"Catalogue OAuth2 authentication failed: {response.status_code}")

            token_data = response.json()
            self._catalogue_token = token_data['access_token']

            # Set expiry to 5 minutes before actual expiry for safety
            expires_in = token_data.get('expires_in', 600)
            self._catalogue_token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)

            logger.info("Catalogue OAuth2 token obtained successfully", expires_in=expires_in)
            return self._catalogue_token

    async def _get_download_token(self) -> Optional[str]:
        """
        Get OAuth2 access token for downloads (password grant)

        Returns:
            str: Valid access token for downloads, or None if credentials not configured
        """
        # Check if username/password are configured
        if not self.username or not self.password or \
           self.username == 'configured_via_oauth' or self.password == 'configured_via_oauth':
            logger.warning("Download credentials not configured - username/password required",
                         note="Set COPERNICUS_USERNAME and COPERNICUS_PASSWORD in .env")
            return None

        # Return cached token if still valid
        if self._download_token and self._download_token_expiry and datetime.now() < self._download_token_expiry:
            return self._download_token

        logger.info("Requesting new download OAuth2 token (password grant)")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    'grant_type': 'password',
                    'client_id': 'cdse-public',  # Public client ID for password grant
                    'username': self.username,
                    'password': self.password
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if response.status_code != 200:
                logger.error("Download token request failed",
                           status=response.status_code,
                           response=response.text[:200],
                           note="Check COPERNICUS_USERNAME and COPERNICUS_PASSWORD")
                return None

            token_data = response.json()
            self._download_token = token_data['access_token']

            # Set expiry to 5 minutes before actual expiry for safety
            expires_in = token_data.get('expires_in', 600)
            self._download_token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)

            logger.info("Download OAuth2 token obtained successfully", expires_in=expires_in)
            return self._download_token

    def _format_wkt_polygon(self, bounds: Dict[str, float]) -> str:
        """
        Format bounding box as WKT POLYGON for OData query

        Args:
            bounds: Dict with lat_min, lat_max, lon_min, lon_max

        Returns:
            str: WKT POLYGON string
        """
        return (
            f"POLYGON(("
            f"{bounds['lon_min']} {bounds['lat_min']},"
            f"{bounds['lon_max']} {bounds['lat_min']},"
            f"{bounds['lon_max']} {bounds['lat_max']},"
            f"{bounds['lon_min']} {bounds['lat_max']},"
            f"{bounds['lon_min']} {bounds['lat_min']}"
            f"))"
        )

    async def search_sentinel2(
        self,
        start_date: datetime,
        end_date: datetime,
        bounds: Optional[Dict[str, float]] = None,
        cloud_cover_max: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for Sentinel-2 MSI products

        Args:
            start_date: Start date for query
            end_date: End date for query
            bounds: Spatial bounds (defaults to California)
            cloud_cover_max: Maximum cloud cover percentage
            limit: Maximum number of results

        Returns:
            List of Sentinel-2 products
        """
        token = await self._get_catalogue_token()
        bounds = bounds or CALIFORNIA_BOUNDS.copy()
        wkt_polygon = self._format_wkt_polygon(bounds)

        # Build OData filter
        odata_filter = (
            f"Collection/Name eq 'SENTINEL-2' and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt_polygon}') and "
            f"ContentDate/Start ge {start_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z and "
            f"ContentDate/Start le {end_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z and "
            f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {cloud_cover_max})"
        )

        url = f"{self.ODATA_BASE_URL}/Products?$filter={odata_filter}&$top={limit}&$orderby=ContentDate/Start desc"

        logger.info("Querying Sentinel-2 products",
                   start_date=start_date.isoformat(),
                   end_date=end_date.isoformat(),
                   cloud_cover_max=cloud_cover_max)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                url,
                headers={'Authorization': f'Bearer {token}'}
            )

            if response.status_code != 200:
                logger.error("Sentinel-2 query failed",
                           status=response.status_code,
                           response=response.text)
                raise Exception(f"Sentinel-2 query failed: {response.status_code}")

            data = response.json()
            products = data.get('value', [])

            logger.info("Sentinel-2 query successful", products_found=len(products))
            return products

    async def search_sentinel3(
        self,
        start_date: datetime,
        end_date: datetime,
        bounds: Optional[Dict[str, float]] = None,
        product_type: str = 'SL_2_LST___',
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for Sentinel-3 SLSTR products

        Args:
            start_date: Start date for query
            end_date: End date for query
            bounds: Spatial bounds (defaults to California)
            product_type: Product type (SL_2_LST___ for Land Surface Temperature)
            limit: Maximum number of results

        Returns:
            List of Sentinel-3 products
        """
        token = await self._get_catalogue_token()
        bounds = bounds or CALIFORNIA_BOUNDS.copy()
        wkt_polygon = self._format_wkt_polygon(bounds)

        # Build OData filter for Sentinel-3 SLSTR
        odata_filter = (
            f"Collection/Name eq 'SENTINEL-3' and "
            f"contains(Name,'{product_type}') and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt_polygon}') and "
            f"ContentDate/Start ge {start_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z and "
            f"ContentDate/Start le {end_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z"
        )

        url = f"{self.ODATA_BASE_URL}/Products?$filter={odata_filter}&$top={limit}&$orderby=ContentDate/Start desc"

        logger.info("Querying Sentinel-3 products",
                   start_date=start_date.isoformat(),
                   end_date=end_date.isoformat(),
                   product_type=product_type)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                url,
                headers={'Authorization': f'Bearer {token}'}
            )

            if response.status_code != 200:
                logger.error("Sentinel-3 query failed",
                           status=response.status_code,
                           response=response.text)
                raise Exception(f"Sentinel-3 query failed: {response.status_code}")

            data = response.json()
            products = data.get('value', [])

            logger.info("Sentinel-3 query successful", products_found=len(products))
            return products

    async def download_product(self, product_id: str, product_name: str) -> Optional[str]:
        """
        Download Sentinel product to MinIO storage using password grant OAuth

        Args:
            product_id: Product UUID from Copernicus
            product_name: Product name for reference

        Returns:
            S3 path to downloaded product, or None if download fails
        """
        try:
            # Get download token (password grant)
            token = await self._get_download_token()
            if not token:
                logger.error("Cannot download product - no download token available",
                           product_id=product_id,
                           note="Set COPERNICUS_USERNAME and COPERNICUS_PASSWORD in .env")
                return None

            # Determine satellite type from product name
            if product_name.startswith('S2'):
                satellite = 'sentinel-2'
            elif product_name.startswith('S3'):
                satellite = 'sentinel-3'
            else:
                satellite = 'unknown'

            # Extract date from product name (format: S2A_MSIL1C_YYYYMMDD...)
            date_str = product_name.split('_')[2][:8]  # YYYYMMDD
            date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            # Build download URL
            download_url = f"{self.ODATA_BASE_URL}/Products({product_id})/$value"

            logger.info("Starting Sentinel product download",
                       product_id=product_id,
                       product_name=product_name,
                       satellite=satellite,
                       date=date)

            # Download file with streaming
            # Note: We must handle redirects manually to preserve Authorization header
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=False) as client:
                # First request - will redirect to download server
                initial_response = await client.get(download_url,
                                                   headers={'Authorization': f'Bearer {token}'})

                # Determine final URL to stream from
                final_url = download_url
                if initial_response.status_code in (301, 302):
                    final_url = initial_response.headers['Location']
                    logger.info("Following redirect to download server",
                               product_id=product_id,
                               redirect_url=final_url[:100])
                elif initial_response.status_code != 200:
                    logger.error("Unexpected response from catalogue",
                               status=initial_response.status_code,
                               product_id=product_id,
                               response_text=initial_response.text[:500])
                    return None

                # Stream the actual file
                async with client.stream('GET', final_url,
                                        headers={'Authorization': f'Bearer {token}'}) as response:
                    if response.status_code != 200:
                        logger.error("Download failed",
                                   status=response.status_code,
                                   product_id=product_id,
                                   response_text=(await response.aread()).decode('utf-8', errors='ignore')[:500])
                        return None

                    # Read file content in chunks
                    file_data = BytesIO()
                    total_size = 0
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        file_data.write(chunk)
                        total_size += len(chunk)

                    file_data.seek(0)

                    logger.info("Download completed",
                               product_id=product_id,
                               size_mb=round(total_size / 1024 / 1024, 2))

                    # Upload to MinIO if S3 client is available
                    if self.s3_client:
                        s3_key = f"sentinel/{satellite}/{date}/{product_id}.zip"

                        try:
                            self.s3_client.put_object(
                                self.s3_bucket,
                                s3_key,
                                file_data,
                                length=total_size,
                                content_type='application/zip'
                            )

                            s3_path = f"s3://{self.s3_bucket}/{s3_key}"
                            logger.info("Uploaded to MinIO",
                                       product_id=product_id,
                                       s3_path=s3_path,
                                       size_mb=round(total_size / 1024 / 1024, 2))

                            return s3_path

                        except S3Error as e:
                            logger.error("Failed to upload to MinIO",
                                       product_id=product_id,
                                       error=str(e))
                            return None
                    else:
                        logger.warning("S3 client not available - cannot store product",
                                     product_id=product_id)
                        return None

        except Exception as e:
            logger.error("Failed to download product",
                       product_id=product_id,
                       error=str(e))
            return None

    async def should_download_product(self, product: Dict[str, Any], product_type: str) -> bool:
        """
        Determine if a product should be recorded based on selective criteria

        Args:
            product: Product metadata from API
            product_type: 'sentinel-2' or 'sentinel-3'

        Returns:
            bool: True if product metadata should be recorded
        """
        if product_type == 'sentinel-2':
            # Record all Sentinel-2 products (metadata only, no download)
            # Filtering can be done at query time based on cloud cover
            return True

        elif product_type == 'sentinel-3':
            # Record all Sentinel-3 SLSTR thermal data (always useful for fire detection)
            product_name = product.get('Name', '')
            if 'SL_2_LST' in product_name:
                return True

            logger.debug("Skipping Sentinel-3 product - not thermal data",
                       product_id=product.get('Id'))
            return False

        return False

    async def health_check(self) -> bool:
        """
        Verify OAuth2 credentials and API connectivity

        Returns:
            bool: True if credentials are valid
        """
        try:
            await self._get_catalogue_token()
            logger.info("Sentinel client health check passed (catalogue access)")
            return True
        except Exception as e:
            logger.error("Sentinel client health check failed", error=str(e))
            return False
