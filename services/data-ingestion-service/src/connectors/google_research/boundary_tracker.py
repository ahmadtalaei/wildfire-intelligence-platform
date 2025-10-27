"""
AI-Powered Fire Boundary Tracking

Implementation of Google's AI boundary tracking methodology for real-time
wildfire perimeter mapping using satellite imagery and machine learning.

Features:
- Continent-scale satellite imagery analysis
- Neural network fire boundary detection
- Real-time perimeter updates
- Area and growth rate calculations
- Multi-satellite data integration

Author: Wildfire Intelligence Team  
Integration: Google Research Boundary Tracking AI
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from pathlib import Path
import cv2
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import geopandas as gpd
import rasterio
from rasterio.features import shapes
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler

from ...config import get_settings
from ...utils.logging import get_logger
from ...utils.kafka_producer import KafkaProducerManager
from ...models.simulation_data import (
    BoundaryTrackingData,
    BoundaryTrackingResponse,
    BoundaryTrackingDB
)

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class SatelliteImagery:
    """Satellite imagery data for boundary tracking"""
    
    image_id: str
    satellite_name: str
    acquisition_time: datetime
    
    # Imagery data
    image_data: np.ndarray  # Multi-band satellite image
    geotransform: Tuple[float, ...]  # Geospatial transformation
    projection: str  # Spatial reference system
    
    # Image properties
    resolution_meters: float
    bands: List[str]  # Band names (e.g., ['red', 'green', 'blue', 'nir', 'swir'])
    cloud_cover_percent: float
    quality_score: float
    
    # Geographic bounds
    bounds: Dict[str, float]  # min_lat, max_lat, min_lon, max_lon


@dataclass 
class BoundaryDetectionResult:
    """Result of AI boundary detection"""
    
    detection_id: str
    timestamp: datetime
    model_version: str
    
    # Detected boundaries
    fire_boundaries: List[Dict[str, Any]]  # List of GeoJSON polygons
    confidence_map: np.ndarray  # Spatial confidence scores
    
    # Analysis results
    total_burned_area_hectares: float
    active_fire_perimeter_km: float
    boundary_confidence: float
    
    # Change detection
    area_change_hectares: Optional[float] = None
    growth_rate_hectares_per_hour: Optional[float] = None
    expansion_directions: List[str] = None
    
    # Processing metadata
    input_images: List[str] = None
    processing_time_seconds: float = 0.0
    quality_flags: List[str] = None


class BoundaryTracker:
    """
    AI-powered fire boundary tracking system
    
    Implements Google's methodology for:
    - Multi-satellite imagery analysis
    - Deep learning boundary detection
    - Real-time perimeter tracking
    - Change detection and growth analysis
    - Confidence assessment and quality control
    """
    
    def __init__(self, model_config: Optional[Dict[str, Any]] = None):
        self.config = model_config or {}
        self.model_version = "boundary-tracker-v2.1-google"
        
        # Model components
        self.boundary_detection_model = None
        self.change_detection_model = None
        self.confidence_model = None
        
        # Image preprocessing
        self.image_preprocessor = ImagePreprocessor()
        self.scaler = MinMaxScaler()
        
        # Model paths
        self.model_dir = Path(settings.MODEL_STORAGE_PATH) / "boundary_tracking_models"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # External services
        self.kafka_producer = KafkaProducerManager()
        
        # State management
        self.tracking_history = []
        self.satellite_sources = {}
        self.active_fires = {}
        
        # Performance metrics
        self.metrics = {
            'total_detections': 0,
            'successful_detections': 0,
            'average_confidence': 0.0,
            'average_processing_time_ms': 0.0,
            'satellite_sources_active': 0,
            'last_detection_time': None
        }
        
        # Configuration
        self.detection_config = {
            'min_fire_area_hectares': 0.5,
            'confidence_threshold': 0.7,
            'max_cloud_cover_percent': 30,
            'image_resolution_limit_m': 50,
            'change_detection_hours': 24,
            'growth_rate_smoothing_hours': 6
        }
        
        logger.info("AI boundary tracker initialized")

    async def initialize(self):
        """Initialize boundary tracking models and services"""
        
        try:
            logger.info("Initializing AI boundary tracking system")
            
            # Initialize Kafka producer
            await self.kafka_producer.initialize()
            
            # Load or create AI models
            await self._initialize_boundary_detection_model()
            await self._initialize_change_detection_model()
            await self._initialize_confidence_model()
            
            # Initialize satellite data sources
            await self._initialize_satellite_sources()
            
            logger.info("AI boundary tracking system initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing boundary tracker: {e}")
            raise

    async def _initialize_boundary_detection_model(self):
        """Initialize deep learning model for fire boundary detection"""
        
        model_path = self.model_dir / "fire_boundary_detection.h5"
        
        if model_path.exists():
            # Load existing model
            self.boundary_detection_model = tf.keras.models.load_model(str(model_path))
            logger.info("Loaded existing boundary detection model")
        else:
            # Create new model architecture based on Google's approach
            self.boundary_detection_model = self._create_boundary_detection_model()
            logger.info("Created new boundary detection model")

    def _create_boundary_detection_model(self) -> tf.keras.Model:
        """Create CNN model for fire boundary detection"""
        
        # Model architecture based on semantic segmentation
        # Input: Multi-band satellite imagery (typically 6-8 bands)
        input_shape = (256, 256, 6)  # Height, Width, Bands
        
        inputs = tf.keras.Input(shape=input_shape)
        
        # Encoder (Downsampling path)
        conv1 = tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same')(inputs)
        conv1 = tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same')(conv1)
        pool1 = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(conv1)
        
        conv2 = tf.keras.layers.Conv2D(128, 3, activation='relu', padding='same')(pool1)
        conv2 = tf.keras.layers.Conv2D(128, 3, activation='relu', padding='same')(conv2)
        pool2 = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(conv2)
        
        conv3 = tf.keras.layers.Conv2D(256, 3, activation='relu', padding='same')(pool2)
        conv3 = tf.keras.layers.Conv2D(256, 3, activation='relu', padding='same')(conv3)
        pool3 = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(conv3)
        
        conv4 = tf.keras.layers.Conv2D(512, 3, activation='relu', padding='same')(pool3)
        conv4 = tf.keras.layers.Conv2D(512, 3, activation='relu', padding='same')(conv4)
        drop4 = tf.keras.layers.Dropout(0.5)(conv4)
        pool4 = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(drop4)
        
        # Bottleneck
        conv5 = tf.keras.layers.Conv2D(1024, 3, activation='relu', padding='same')(pool4)
        conv5 = tf.keras.layers.Conv2D(1024, 3, activation='relu', padding='same')(conv5)
        drop5 = tf.keras.layers.Dropout(0.5)(conv5)
        
        # Decoder (Upsampling path)
        up6 = tf.keras.layers.Conv2D(512, 2, activation='relu', padding='same')(
            tf.keras.layers.UpSampling2D(size=(2, 2))(drop5)
        )
        merge6 = tf.keras.layers.concatenate([drop4, up6], axis=3)
        conv6 = tf.keras.layers.Conv2D(512, 3, activation='relu', padding='same')(merge6)
        conv6 = tf.keras.layers.Conv2D(512, 3, activation='relu', padding='same')(conv6)
        
        up7 = tf.keras.layers.Conv2D(256, 2, activation='relu', padding='same')(
            tf.keras.layers.UpSampling2D(size=(2, 2))(conv6)
        )
        merge7 = tf.keras.layers.concatenate([conv3, up7], axis=3)
        conv7 = tf.keras.layers.Conv2D(256, 3, activation='relu', padding='same')(merge7)
        conv7 = tf.keras.layers.Conv2D(256, 3, activation='relu', padding='same')(conv7)
        
        up8 = tf.keras.layers.Conv2D(128, 2, activation='relu', padding='same')(
            tf.keras.layers.UpSampling2D(size=(2, 2))(conv7)
        )
        merge8 = tf.keras.layers.concatenate([conv2, up8], axis=3)
        conv8 = tf.keras.layers.Conv2D(128, 3, activation='relu', padding='same')(merge8)
        conv8 = tf.keras.layers.Conv2D(128, 3, activation='relu', padding='same')(conv8)
        
        up9 = tf.keras.layers.Conv2D(64, 2, activation='relu', padding='same')(
            tf.keras.layers.UpSampling2D(size=(2, 2))(conv8)
        )
        merge9 = tf.keras.layers.concatenate([conv1, up9], axis=3)
        conv9 = tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same')(merge9)
        conv9 = tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same')(conv9)
        
        # Output layers
        # Fire boundary segmentation (binary classification)
        boundary_output = tf.keras.layers.Conv2D(1, 1, activation='sigmoid', name='boundary')(conv9)
        
        # Confidence map
        confidence_output = tf.keras.layers.Conv2D(1, 1, activation='sigmoid', name='confidence')(conv9)
        
        # Create model
        model = tf.keras.Model(inputs=inputs, outputs=[boundary_output, confidence_output])
        
        # Compile model
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss={
                'boundary': self._fire_boundary_loss,
                'confidence': 'binary_crossentropy'
            },
            loss_weights={'boundary': 1.0, 'confidence': 0.5},
            metrics={
                'boundary': ['accuracy', self._fire_iou_metric],
                'confidence': ['accuracy']
            }
        )
        
        return model

    def _fire_boundary_loss(self, y_true, y_pred):
        """Custom loss function for fire boundary detection"""
        
        # Focal loss to handle class imbalance (fire vs non-fire pixels)
        alpha = 0.25
        gamma = 2.0
        
        # Calculate focal loss
        ce_loss = tf.keras.losses.binary_crossentropy(y_true, y_pred)
        p_t = y_true * y_pred + (1 - y_true) * (1 - y_pred)
        alpha_t = y_true * alpha + (1 - y_true) * (1 - alpha)
        focal_loss = alpha_t * tf.pow(1 - p_t, gamma) * ce_loss
        
        # Add boundary-specific penalty for edge accuracy
        boundary_penalty = self._boundary_edge_penalty(y_true, y_pred)
        
        return tf.reduce_mean(focal_loss) + 0.1 * boundary_penalty

    def _boundary_edge_penalty(self, y_true, y_pred):
        """Penalty for inaccurate fire boundary edges"""
        
        # Sobel edge detection on true and predicted boundaries
        true_edges = tf.image.sobel_edges(y_true)
        pred_edges = tf.image.sobel_edges(y_pred)
        
        # L2 loss on edge differences
        edge_loss = tf.reduce_mean(tf.square(true_edges - pred_edges))
        
        return edge_loss

    def _fire_iou_metric(self, y_true, y_pred):
        """Intersection over Union (IoU) metric for fire boundaries"""
        
        # Threshold predictions
        y_pred_thresh = tf.cast(y_pred > 0.5, tf.float32)
        
        # Calculate IoU
        intersection = tf.reduce_sum(y_true * y_pred_thresh)
        union = tf.reduce_sum(y_true) + tf.reduce_sum(y_pred_thresh) - intersection
        
        iou = intersection / (union + tf.keras.backend.epsilon())
        return iou

    async def _initialize_change_detection_model(self):
        """Initialize model for detecting boundary changes over time"""
        
        # Simplified change detection model
        self.change_detection_model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(256, 256, 12)),  # 2 time steps x 6 bands
            tf.keras.layers.Conv2D(32, 3, activation='relu', padding='same'),
            tf.keras.layers.Conv2D(32, 3, activation='relu', padding='same'),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same'),
            tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same'),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Conv2D(128, 3, activation='relu', padding='same'),
            tf.keras.layers.GlobalAveragePooling2D(),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(3, activation='softmax', name='change_class')  # No change, Growth, Shrinkage
        ])
        
        self.change_detection_model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        logger.info("Change detection model initialized")

    async def _initialize_confidence_model(self):
        """Initialize model for assessing boundary detection confidence"""
        
        # Simple confidence assessment model
        self.confidence_model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(256, 256, 7)),  # 6 bands + boundary prediction
            tf.keras.layers.Conv2D(16, 5, activation='relu', padding='same'),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Conv2D(32, 5, activation='relu', padding='same'),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same'),
            tf.keras.layers.GlobalAveragePooling2D(),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid', name='confidence_score')
        ])
        
        self.confidence_model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['mae']
        )
        
        logger.info("Confidence assessment model initialized")

    async def _initialize_satellite_sources(self):
        """Initialize available satellite data sources"""
        
        # Configure satellite sources (in production, these would be real APIs)
        self.satellite_sources = {
            'GOES-16': {
                'name': 'GOES-16 East',
                'type': 'geostationary',
                'bands': ['red', 'green', 'blue', 'nir', 'swir1', 'swir2'],
                'resolution_m': 500,
                'revisit_minutes': 10,
                'coverage': 'Americas',
                'api_endpoint': 'https://api.goes.noaa.gov/v1/',
                'active': True
            },
            'GOES-18': {
                'name': 'GOES-18 West',
                'type': 'geostationary',
                'bands': ['red', 'green', 'blue', 'nir', 'swir1', 'swir2'],
                'resolution_m': 500,
                'revisit_minutes': 10,
                'coverage': 'Pacific',
                'api_endpoint': 'https://api.goes.noaa.gov/v1/',
                'active': True
            },
            'Himawari-9': {
                'name': 'Himawari-9',
                'type': 'geostationary',
                'bands': ['red', 'green', 'blue', 'nir', 'swir1', 'swir2'],
                'resolution_m': 1000,
                'revisit_minutes': 10,
                'coverage': 'Asia-Pacific',
                'api_endpoint': 'https://api.himawari.jma.go.jp/v1/',
                'active': True
            },
            'Landsat-9': {
                'name': 'Landsat-9',
                'type': 'polar',
                'bands': ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'thermal'],
                'resolution_m': 30,
                'revisit_days': 16,
                'coverage': 'Global',
                'api_endpoint': 'https://api.usgs.gov/landsat/v1/',
                'active': True
            },
            'Sentinel-2': {
                'name': 'Sentinel-2',
                'type': 'polar',
                'bands': ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'],
                'resolution_m': 20,
                'revisit_days': 5,
                'coverage': 'Global',
                'api_endpoint': 'https://api.copernicus.eu/sentinel2/v1/',
                'active': True
            }
        }
        
        active_sources = len([s for s in self.satellite_sources.values() if s['active']])
        self.metrics['satellite_sources_active'] = active_sources
        
        logger.info(f"Initialized {active_sources} satellite data sources")

    async def track_fire_boundary(
        self, 
        fire_location: Dict[str, float],
        search_radius_km: float = 25,
        satellite_sources: Optional[List[str]] = None,
        include_change_detection: bool = True
    ) -> BoundaryDetectionResult:
        """
        Track fire boundary using AI analysis of satellite imagery
        
        Args:
            fire_location: Center location for boundary tracking (lat, lon)
            search_radius_km: Search radius for satellite imagery
            satellite_sources: List of satellite sources to use
            include_change_detection: Whether to perform change detection
            
        Returns:
            Boundary detection results with confidence assessment
        """
        try:
            start_time = datetime.now(timezone.utc)
            detection_id = f"boundary-{start_time.strftime('%Y%m%d%H%M%S')}"
            
            logger.info(f"Starting boundary tracking for location {fire_location}")
            
            # Get satellite imagery for the area
            imagery_data = await self._acquire_satellite_imagery(
                fire_location, 
                search_radius_km,
                satellite_sources
            )
            
            if not imagery_data:
                raise ValueError("No suitable satellite imagery available")
            
            # Preprocess imagery for AI model
            processed_images = []
            for imagery in imagery_data:
                processed_img = await self._preprocess_imagery(imagery)
                processed_images.append(processed_img)
            
            # Run boundary detection AI model
            boundary_predictions = []
            confidence_maps = []
            
            for processed_img in processed_images:
                boundary_pred, confidence_map = self.boundary_detection_model.predict(
                    np.expand_dims(processed_img, axis=0),
                    verbose=0
                )
                boundary_predictions.append(boundary_pred[0])
                confidence_maps.append(confidence_map[0])
            
            # Combine predictions from multiple images
            combined_boundary = np.mean(boundary_predictions, axis=0)
            combined_confidence = np.mean(confidence_maps, axis=0)
            
            # Convert pixel predictions to geographic boundaries
            fire_boundaries = await self._extract_fire_polygons(
                combined_boundary,
                imagery_data[0].geotransform,
                imagery_data[0].projection,
                confidence_threshold=self.detection_config['confidence_threshold']
            )
            
            # Calculate area and perimeter metrics
            total_area_ha, perimeter_km = self._calculate_fire_metrics(fire_boundaries)
            
            # Assess boundary confidence
            overall_confidence = float(np.mean(combined_confidence))
            
            # Perform change detection if requested
            area_change = None
            growth_rate = None
            expansion_directions = None
            
            if include_change_detection:
                change_results = await self._detect_boundary_changes(
                    fire_location,
                    fire_boundaries,
                    search_radius_km
                )
                area_change = change_results.get('area_change_hectares')
                growth_rate = change_results.get('growth_rate_hectares_per_hour')
                expansion_directions = change_results.get('expansion_directions', [])
            
            # Create detection result
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            result = BoundaryDetectionResult(
                detection_id=detection_id,
                timestamp=start_time,
                model_version=self.model_version,
                fire_boundaries=fire_boundaries,
                confidence_map=combined_confidence,
                total_burned_area_hectares=total_area_ha,
                active_fire_perimeter_km=perimeter_km,
                boundary_confidence=overall_confidence,
                area_change_hectares=area_change,
                growth_rate_hectares_per_hour=growth_rate,
                expansion_directions=expansion_directions,
                input_images=[img.image_id for img in imagery_data],
                processing_time_seconds=processing_time,
                quality_flags=self._assess_quality_flags(imagery_data, overall_confidence)
            )
            
            # Update metrics
            self.metrics['total_detections'] += 1
            self.metrics['successful_detections'] += 1
            self.metrics['average_confidence'] = (
                (self.metrics['average_confidence'] * (self.metrics['successful_detections'] - 1) + overall_confidence)
                / self.metrics['successful_detections']
            )
            self.metrics['average_processing_time_ms'] = (
                (self.metrics['average_processing_time_ms'] * (self.metrics['successful_detections'] - 1) + processing_time * 1000)
                / self.metrics['successful_detections']
            )
            self.metrics['last_detection_time'] = start_time
            
            # Store in tracking history
            self.tracking_history.append(result)
            
            # Keep history manageable (last 48 hours)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)
            self.tracking_history = [
                r for r in self.tracking_history 
                if r.timestamp > cutoff_time
            ]
            
            logger.info(f"Boundary tracking completed in {processing_time:.1f}s, "
                       f"confidence: {overall_confidence:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in boundary tracking: {e}")
            self.metrics['total_detections'] += 1
            raise

    async def _acquire_satellite_imagery(
        self, 
        location: Dict[str, float],
        radius_km: float,
        sources: Optional[List[str]] = None
    ) -> List[SatelliteImagery]:
        """Acquire satellite imagery for boundary analysis"""
        
        # In production, this would fetch real satellite imagery
        # For now, generate simulated imagery data
        
        if not sources:
            sources = ['GOES-16', 'GOES-18']  # Use geostationary satellites for frequent updates
        
        imagery_data = []
        
        for source in sources:
            if source not in self.satellite_sources or not self.satellite_sources[source]['active']:
                continue
            
            satellite_info = self.satellite_sources[source]
            
            # Generate simulated satellite image
            image_size = 256
            num_bands = len(satellite_info['bands'])
            
            # Simulate multi-band satellite data
            image_data = np.random.random((image_size, image_size, num_bands)).astype(np.float32)
            
            # Add some realistic patterns for fire areas
            # Simulate hot spots with high SWIR values
            if 'swir1' in satellite_info['bands'] or 'swir2' in satellite_info['bands']:
                fire_center_x, fire_center_y = image_size // 2, image_size // 2
                y, x = np.ogrid[:image_size, :image_size]
                fire_mask = (x - fire_center_x)**2 + (y - fire_center_y)**2 < (image_size // 8)**2
                
                # Enhance SWIR bands for fire simulation
                swir_band_idx = len(satellite_info['bands']) - 1  # Assume last band is SWIR
                image_data[fire_mask, swir_band_idx] = np.random.uniform(0.7, 1.0, fire_mask.sum())
            
            # Create geotransform (pixel to geographic coordinates)
            lat, lon = location['latitude'], location['longitude']
            pixel_size_deg = (radius_km * 2) / (image_size * 111.0)  # Approximate degrees per pixel
            
            geotransform = (
                lon - radius_km / 111.0,  # Top-left longitude
                pixel_size_deg,           # Pixel width
                0,                        # Rotation
                lat + radius_km / 111.0,  # Top-left latitude  
                0,                        # Rotation
                -pixel_size_deg           # Pixel height (negative)
            )
            
            # Calculate bounds
            bounds = {
                'min_lat': lat - radius_km / 111.0,
                'max_lat': lat + radius_km / 111.0,
                'min_lon': lon - radius_km / 111.0,
                'max_lon': lon + radius_km / 111.0
            }
            
            imagery = SatelliteImagery(
                image_id=f"{source.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                satellite_name=satellite_info['name'],
                acquisition_time=datetime.now(timezone.utc) - timedelta(minutes=np.random.randint(5, 30)),
                image_data=image_data,
                geotransform=geotransform,
                projection="EPSG:4326",  # WGS84
                resolution_meters=satellite_info['resolution_m'],
                bands=satellite_info['bands'],
                cloud_cover_percent=np.random.uniform(0, 20),  # Low cloud cover
                quality_score=np.random.uniform(0.8, 1.0),
                bounds=bounds
            )
            
            imagery_data.append(imagery)
        
        logger.debug(f"Acquired {len(imagery_data)} satellite images from {len(sources)} sources")
        return imagery_data

    async def _preprocess_imagery(self, imagery: SatelliteImagery) -> np.ndarray:
        """Preprocess satellite imagery for AI model input"""
        
        # Apply preprocessing pipeline
        processed_image = imagery.image_data.copy()
        
        # Normalize pixel values to [0, 1] range
        processed_image = self.scaler.fit_transform(
            processed_image.reshape(-1, processed_image.shape[-1])
        ).reshape(processed_image.shape)
        
        # Apply atmospheric correction (simplified)
        processed_image = self._apply_atmospheric_correction(processed_image, imagery.satellite_name)
        
        # Enhance fire-relevant spectral indices
        processed_image = self._calculate_fire_indices(processed_image, imagery.bands)
        
        # Ensure correct input shape for model
        if processed_image.shape[:2] != (256, 256):
            processed_image = cv2.resize(processed_image, (256, 256))
        
        # Ensure 6 bands (pad or truncate as needed)
        if processed_image.shape[-1] > 6:
            processed_image = processed_image[:, :, :6]
        elif processed_image.shape[-1] < 6:
            padding = np.zeros((256, 256, 6 - processed_image.shape[-1]))
            processed_image = np.concatenate([processed_image, padding], axis=-1)
        
        return processed_image.astype(np.float32)

    def _apply_atmospheric_correction(self, image: np.ndarray, satellite_name: str) -> np.ndarray:
        """Apply atmospheric correction to satellite imagery"""
        
        # Simplified atmospheric correction
        # In production, this would use proper atmospheric correction algorithms
        
        correction_factors = {
            'GOES-16': [0.95, 0.96, 0.97, 0.98, 0.99, 0.99],
            'GOES-18': [0.95, 0.96, 0.97, 0.98, 0.99, 0.99],
            'Himawari-9': [0.94, 0.95, 0.96, 0.97, 0.98, 0.98],
            'Landsat-9': [0.96, 0.97, 0.98, 0.99, 0.99, 1.00],
            'Sentinel-2': [0.97, 0.98, 0.99, 0.99, 1.00, 1.00]
        }
        
        factors = correction_factors.get(satellite_name, [1.0] * image.shape[-1])
        
        corrected_image = image.copy()
        for i, factor in enumerate(factors[:image.shape[-1]]):
            corrected_image[:, :, i] *= factor
        
        return np.clip(corrected_image, 0, 1)

    def _calculate_fire_indices(self, image: np.ndarray, bands: List[str]) -> np.ndarray:
        """Calculate fire-relevant spectral indices"""
        
        # Add fire detection indices if appropriate bands are available
        enhanced_image = image.copy()
        
        try:
            # Normalized Burn Ratio (NBR) if NIR and SWIR available
            if 'nir' in bands and 'swir2' in bands:
                nir_idx = bands.index('nir')
                swir_idx = bands.index('swir2')
                
                nir = image[:, :, nir_idx]
                swir = image[:, :, swir_idx]
                
                # NBR = (NIR - SWIR) / (NIR + SWIR)
                nbr = (nir - swir) / (nir + swir + 1e-8)
                
                # Add as additional band if space allows
                if enhanced_image.shape[-1] < 6:
                    enhanced_image = np.concatenate([enhanced_image, nbr[:, :, np.newaxis]], axis=-1)
            
            # Fire Temperature Index using thermal bands
            if 'thermal' in bands:
                thermal_idx = bands.index('thermal')
                thermal = image[:, :, thermal_idx]
                
                # Simple fire temperature enhancement
                fire_temp_index = np.where(thermal > 0.7, 1.0, thermal)
                
                if enhanced_image.shape[-1] < 6:
                    enhanced_image = np.concatenate([enhanced_image, fire_temp_index[:, :, np.newaxis]], axis=-1)
            
        except Exception as e:
            logger.debug(f"Error calculating fire indices: {e}")
        
        return enhanced_image

    async def _extract_fire_polygons(
        self, 
        boundary_prediction: np.ndarray,
        geotransform: Tuple[float, ...],
        projection: str,
        confidence_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Extract fire boundary polygons from AI predictions"""
        
        try:
            # Threshold the prediction to get binary mask
            binary_mask = (boundary_prediction[:, :, 0] > confidence_threshold).astype(np.uint8)
            
            # Apply morphological operations to clean up the mask
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
            binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            fire_polygons = []
            
            for i, contour in enumerate(contours):
                # Filter small contours
                area_pixels = cv2.contourArea(contour)
                if area_pixels < 100:  # Minimum 100 pixels
                    continue
                
                # Convert pixel coordinates to geographic coordinates
                geo_coordinates = []
                for point in contour.reshape(-1, 2):
                    x_pixel, y_pixel = point
                    
                    # Apply geotransform
                    geo_x = geotransform[0] + x_pixel * geotransform[1] + y_pixel * geotransform[2]
                    geo_y = geotransform[3] + x_pixel * geotransform[4] + y_pixel * geotransform[5]
                    
                    geo_coordinates.append([geo_x, geo_y])  # [longitude, latitude]
                
                # Close the polygon
                if len(geo_coordinates) > 2:
                    geo_coordinates.append(geo_coordinates[0])
                    
                    # Create GeoJSON polygon
                    polygon = {
                        "type": "Polygon",
                        "coordinates": [geo_coordinates],
                        "properties": {
                            "fire_boundary_id": f"boundary_{i}",
                            "area_pixels": float(area_pixels),
                            "confidence": float(np.mean(boundary_prediction[binary_mask == 1])),
                            "detection_method": "ai_boundary_tracking",
                            "model_version": self.model_version
                        }
                    }
                    
                    fire_polygons.append(polygon)
            
            logger.debug(f"Extracted {len(fire_polygons)} fire boundary polygons")
            return fire_polygons
            
        except Exception as e:
            logger.error(f"Error extracting fire polygons: {e}")
            return []

    def _calculate_fire_metrics(self, fire_boundaries: List[Dict[str, Any]]) -> Tuple[float, float]:
        """Calculate total fire area and perimeter metrics"""
        
        total_area_ha = 0.0
        total_perimeter_km = 0.0
        
        try:
            for boundary in fire_boundaries:
                if boundary['type'] == 'Polygon':
                    coords = boundary['coordinates'][0]
                    
                    # Create shapely polygon
                    polygon = Polygon([(lon, lat) for lon, lat in coords])
                    
                    # Calculate area in hectares (approximate)
                    # This is a rough calculation; in production, use proper geodesic area calculation
                    area_deg2 = polygon.area
                    area_km2 = area_deg2 * (111.0 ** 2)  # Rough conversion
                    area_ha = area_km2 * 100  # Convert to hectares
                    
                    total_area_ha += area_ha
                    
                    # Calculate perimeter in km
                    perimeter_deg = polygon.length
                    perimeter_km = perimeter_deg * 111.0  # Rough conversion
                    
                    total_perimeter_km += perimeter_km
            
        except Exception as e:
            logger.error(f"Error calculating fire metrics: {e}")
        
        return total_area_ha, total_perimeter_km

    async def _detect_boundary_changes(
        self, 
        location: Dict[str, float],
        current_boundaries: List[Dict[str, Any]],
        radius_km: float
    ) -> Dict[str, Any]:
        """Detect changes in fire boundaries over time"""
        
        change_results = {
            'area_change_hectares': None,
            'growth_rate_hectares_per_hour': None,
            'expansion_directions': []
        }
        
        try:
            # Find historical detections for this location
            historical_detections = self._find_historical_detections(location, radius_km)
            
            if not historical_detections:
                return change_results
            
            # Compare with most recent historical detection
            recent_detection = max(historical_detections, key=lambda x: x.timestamp)
            
            # Calculate time difference
            time_diff_hours = (datetime.now(timezone.utc) - recent_detection.timestamp).total_seconds() / 3600
            
            if time_diff_hours > self.detection_config['change_detection_hours']:
                return change_results
            
            # Calculate area change
            current_area = sum(self._calculate_fire_metrics([boundary])[0] for boundary in current_boundaries)
            previous_area = recent_detection.total_burned_area_hectares
            
            area_change = current_area - previous_area
            growth_rate = area_change / time_diff_hours if time_diff_hours > 0 else 0
            
            change_results['area_change_hectares'] = area_change
            change_results['growth_rate_hectares_per_hour'] = growth_rate
            
            # Determine expansion directions (simplified)
            if area_change > 0:
                # Analyze spatial differences to determine expansion directions
                # This is simplified; in production, use proper geometric analysis
                change_results['expansion_directions'] = ['northeast', 'southwest']  # Example
            
            logger.debug(f"Boundary change detected: {area_change:.1f} ha over {time_diff_hours:.1f} hours")
            
        except Exception as e:
            logger.error(f"Error detecting boundary changes: {e}")
        
        return change_results

    def _find_historical_detections(
        self, 
        location: Dict[str, float], 
        radius_km: float
    ) -> List[BoundaryDetectionResult]:
        """Find historical boundary detections near location"""
        
        historical_detections = []
        
        lat, lon = location['latitude'], location['longitude']
        
        for detection in self.tracking_history:
            # Simple distance check (should use proper geodesic distance)
            for boundary in detection.fire_boundaries:
                if boundary['type'] == 'Polygon':
                    coords = boundary['coordinates'][0]
                    
                    # Check if any coordinate is within radius
                    for coord_lon, coord_lat in coords:
                        lat_diff = abs(coord_lat - lat)
                        lon_diff = abs(coord_lon - lon)
                        distance_km = np.sqrt((lat_diff * 111)**2 + (lon_diff * 111)**2)
                        
                        if distance_km <= radius_km:
                            historical_detections.append(detection)
                            break
                    else:
                        continue
                    break
        
        return historical_detections

    def _assess_quality_flags(self, imagery_data: List[SatelliteImagery], confidence: float) -> List[str]:
        """Assess quality flags for the boundary detection"""
        
        quality_flags = []
        
        # Check cloud cover
        avg_cloud_cover = np.mean([img.cloud_cover_percent for img in imagery_data])
        if avg_cloud_cover > self.detection_config['max_cloud_cover_percent']:
            quality_flags.append('high_cloud_cover')
        
        # Check image quality
        avg_quality = np.mean([img.quality_score for img in imagery_data])
        if avg_quality < 0.7:
            quality_flags.append('low_image_quality')
        
        # Check detection confidence
        if confidence < self.detection_config['confidence_threshold']:
            quality_flags.append('low_confidence')
        
        # Check image resolution
        best_resolution = min(img.resolution_meters for img in imagery_data)
        if best_resolution > self.detection_config['image_resolution_limit_m']:
            quality_flags.append('low_resolution')
        
        # Check number of images
        if len(imagery_data) < 2:
            quality_flags.append('limited_imagery')
        
        return quality_flags

    async def stream_boundary_data_to_kafka(self, result: BoundaryDetectionResult) -> bool:
        """Stream boundary tracking results to Kafka"""
        
        try:
            topic_name = "fire-boundary-tracking"
            
            message = {
                'key': result.detection_id,
                'value': {
                    'detection_result': asdict(result),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'ai_boundary_tracker',
                    'version': self.model_version
                }
            }
            
            await self.kafka_producer.send_message(topic_name, message)
            
            logger.debug(f"Streamed boundary tracking result {result.detection_id} to Kafka")
            return True
            
        except Exception as e:
            logger.error(f"Error streaming boundary data to Kafka: {e}")
            return False

    async def save_models(self):
        """Save trained AI models to disk"""
        
        try:
            # Save boundary detection model
            if self.boundary_detection_model:
                model_path = self.model_dir / "fire_boundary_detection.h5"
                self.boundary_detection_model.save(model_path)
                logger.info("Saved boundary detection model")
            
            # Save change detection model
            if self.change_detection_model:
                model_path = self.model_dir / "change_detection.h5"
                self.change_detection_model.save(model_path)
                logger.info("Saved change detection model")
            
            # Save confidence model
            if self.confidence_model:
                model_path = self.model_dir / "confidence_assessment.h5"
                self.confidence_model.save(model_path)
                logger.info("Saved confidence assessment model")
            
            # Save model metadata
            metadata = {
                'model_version': self.model_version,
                'save_timestamp': datetime.now(timezone.utc).isoformat(),
                'metrics': self.metrics,
                'config': self.detection_config
            }
            
            metadata_path = self.model_dir / "boundary_tracker_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("Boundary tracking models saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving boundary tracking models: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check boundary tracker health status"""
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'model_version': self.model_version,
            'components': {},
            'metrics': self.metrics.copy()
        }
        
        try:
            # Check AI models
            health_status['components']['boundary_detection_model'] = (
                'loaded' if self.boundary_detection_model else 'not_loaded'
            )
            health_status['components']['change_detection_model'] = (
                'loaded' if self.change_detection_model else 'not_loaded'
            )
            health_status['components']['confidence_model'] = (
                'loaded' if self.confidence_model else 'not_loaded'
            )
            
            # Check satellite sources
            active_sources = len([s for s in self.satellite_sources.values() if s['active']])
            health_status['components']['satellite_sources'] = f'{active_sources} active'
            
            # Check Kafka connectivity
            kafka_health = await self.kafka_producer.health_check()
            health_status['components']['kafka'] = kafka_health.get('status', 'unknown')
            
            # Overall health assessment
            if not self.boundary_detection_model:
                health_status['status'] = 'degraded'
            if active_sources == 0:
                health_status['status'] = 'degraded'
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status


class ImagePreprocessor:
    """Image preprocessing utilities for satellite imagery"""
    
    @staticmethod
    def normalize_bands(image: np.ndarray, method: str = 'minmax') -> np.ndarray:
        """Normalize image bands"""
        
        if method == 'minmax':
            return (image - image.min()) / (image.max() - image.min() + 1e-8)
        elif method == 'zscore':
            return (image - image.mean()) / (image.std() + 1e-8)
        else:
            return image
    
    @staticmethod
    def apply_cloud_mask(image: np.ndarray, cloud_mask: np.ndarray) -> np.ndarray:
        """Apply cloud mask to remove cloudy pixels"""
        
        masked_image = image.copy()
        masked_image[cloud_mask] = 0
        return masked_image
    
    @staticmethod
    def enhance_fire_signature(image: np.ndarray, bands: List[str]) -> np.ndarray:
        """Enhance fire spectral signature in satellite imagery"""
        
        enhanced = image.copy()
        
        # Apply fire enhancement algorithms based on available bands
        if 'swir1' in bands and 'swir2' in bands:
            swir1_idx = bands.index('swir1')
            swir2_idx = bands.index('swir2')
            
            # Enhance short-wave infrared for active fires
            enhanced[:, :, swir1_idx] = np.clip(enhanced[:, :, swir1_idx] * 1.2, 0, 1)
            enhanced[:, :, swir2_idx] = np.clip(enhanced[:, :, swir2_idx] * 1.2, 0, 1)
        
        return enhanced


if __name__ == "__main__":
    # Example usage for testing
    async def test_boundary_tracker():
        tracker = BoundaryTracker()
        
        # Initialize tracker
        await tracker.initialize()
        
        # Test fire location (California example)
        fire_location = {'latitude': 34.0522, 'longitude': -118.2437}
        
        # Track fire boundary
        result = await tracker.track_fire_boundary(
            fire_location=fire_location,
            search_radius_km=25,
            include_change_detection=True
        )
        
        print(f"Boundary Detection Results:")
        print(f"  Detection ID: {result.detection_id}")
        print(f"  Total Area: {result.total_burned_area_hectares:.1f} hectares")
        print(f"  Perimeter: {result.active_fire_perimeter_km:.1f} km")
        print(f"  Confidence: {result.boundary_confidence:.3f}")
        print(f"  Processing Time: {result.processing_time_seconds:.1f} seconds")
        print(f"  Number of Boundaries: {len(result.fire_boundaries)}")
        
        if result.area_change_hectares:
            print(f"  Area Change: {result.area_change_hectares:.1f} hectares")
            print(f"  Growth Rate: {result.growth_rate_hectares_per_hour:.1f} ha/hour")
        
        # Health check
        health = await tracker.health_check()
        print(f"Health Status: {health['status']}")
    
    # Run test
    asyncio.run(test_boundary_tracker())