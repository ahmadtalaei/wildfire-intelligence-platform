"""
Fire Risk Prediction Models and Schemas
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import structlog

from ..data_sources import FireSatDataSource
logger = structlog.get_logger()


class PredictionRequest(BaseModel):
    """Request model for fire risk prediction"""
    
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    date: Optional[date] = Field(default_factory=date.today, description="Prediction date")
    
    # Weather conditions (optional - will be fetched if not provided)
    temperature_c: Optional[float] = Field(None, description="Temperature in Celsius")
    relative_humidity: Optional[float] = Field(None, ge=0, le=100, description="Relative humidity percentage")
    wind_speed: Optional[float] = Field(None, ge=0, description="Wind speed in m/s")
    precipitation_mm: Optional[float] = Field(None, ge=0, description="Precipitation in mm")
    
    # Additional context (optional)
    elevation_m: Optional[float] = Field(None, description="Elevation in meters")
    vegetation_index: Optional[float] = Field(None, description="NDVI or similar vegetation index")
    drought_index: Optional[float] = Field(None, description="Drought severity index")
    
# Validation removed for demo - coordinates validated by Field constraints


class PredictionResponse(BaseModel):
    """Response model for fire risk prediction"""
    
    request_id: str = Field(..., description="Unique request identifier")
    latitude: float
    longitude: float
    date: date
    
    # Core prediction results
    risk_level: str = Field(..., description="Risk level: low, medium, high, extreme")
    risk_score: float = Field(..., ge=0, le=1, description="Risk probability score (0-1)")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence score (0-1)")
    
    # Model details
    model_version: str = Field(..., description="Model version used")
    prediction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Contributing factors
    weather_risk: float = Field(..., description="Weather-based risk component")
    historical_risk: float = Field(..., description="Historical fire frequency component")
    vegetation_risk: float = Field(..., description="Vegetation condition component")
    topography_risk: float = Field(..., description="Topographical risk component")
    
    # Additional context
    nearby_fires_count: int = Field(default=0, description="Number of active fires within 50km")
    fire_season_factor: float = Field(..., description="Seasonal fire risk factor")
    
    # Data quality indicators
    data_completeness: float = Field(..., ge=0, le=1, description="Input data completeness score")
    model_applicability: float = Field(..., ge=0, le=1, description="Model applicability for this location")


class FireRiskPredictor:
    """Advanced fire risk prediction engine"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.scaler = StandardScaler()
        self.firesat_source = FireSatDataSource()
        self.risk_thresholds = {
            'low': 0.2,
            'medium': 0.5,
            'high': 0.8,
            'extreme': 1.0
        }
        
    async def predict(self, request: PredictionRequest) -> PredictionResponse:
        """Generate fire risk prediction for a single location"""
        
        try:
            # Generate unique request ID
            request_id = self._generate_request_id()
            
            # Gather all required features
            features = await self._collect_features(request)
            
            # Generate predictions from ensemble models
            predictions = await self._run_ensemble_prediction(features)
            
            # Calculate risk level and confidence
            risk_score = np.mean(predictions['risk_scores'])
            confidence = self._calculate_confidence(predictions)
            risk_level = self._classify_risk_level(risk_score)
            
            # Analyze contributing factors
            factors = await self._analyze_risk_factors(features, predictions)
            
            # Get contextual information
            context = await self._get_contextual_info(request)
            
            # Create response
            response = PredictionResponse(
                request_id=request_id,
                latitude=request.latitude,
                longitude=request.longitude,
                date=request.date,
                risk_level=risk_level,
                risk_score=risk_score,
                confidence=confidence,
                model_version=self.model_manager.get_version(),
                weather_risk=factors['weather_risk'],
                historical_risk=factors['historical_risk'],
                vegetation_risk=factors['vegetation_risk'],
                topography_risk=factors['topography_risk'],
                nearby_fires_count=context['nearby_fires_count'],
                fire_season_factor=context['fire_season_factor'],
                data_completeness=features['completeness_score'],
                model_applicability=features['applicability_score']
            )
            
            logger.info("Fire risk prediction completed",
                       request_id=request_id,
                       risk_level=risk_level,
                       confidence=confidence)
            
            return response
            
        except Exception as e:
            logger.error("Fire risk prediction failed", error=str(e))
            raise
    
    async def predict_batch(self, requests: List[PredictionRequest]) -> List[PredictionResponse]:
        """Generate fire risk predictions for multiple locations efficiently"""
        
        try:
            logger.info("Starting batch prediction", batch_size=len(requests))
            
            # Collect features for all requests
            all_features = []
            for request in requests:
                features = await self._collect_features(request)
                all_features.append(features)
            
            # Run batch prediction
            batch_predictions = await self._run_batch_ensemble_prediction(all_features)
            
            # Generate responses
            responses = []
            for i, (request, features, predictions) in enumerate(zip(requests, all_features, batch_predictions)):
                request_id = self._generate_request_id()
                
                risk_score = np.mean(predictions['risk_scores'])
                confidence = self._calculate_confidence(predictions)
                risk_level = self._classify_risk_level(risk_score)
                
                factors = await self._analyze_risk_factors(features, predictions)
                context = await self._get_contextual_info(request)
                
                response = PredictionResponse(
                    request_id=request_id,
                    latitude=request.latitude,
                    longitude=request.longitude,
                    date=request.date,
                    risk_level=risk_level,
                    risk_score=risk_score,
                    confidence=confidence,
                    model_version=self.model_manager.get_version(),
                    weather_risk=factors['weather_risk'],
                    historical_risk=factors['historical_risk'],
                    vegetation_risk=factors['vegetation_risk'],
                    topography_risk=factors['topography_risk'],
                    nearby_fires_count=context['nearby_fires_count'],
                    fire_season_factor=context['fire_season_factor'],
                    data_completeness=features['completeness_score'],
                    model_applicability=features['applicability_score']
                )
                
                responses.append(response)
            
            logger.info("Batch prediction completed", batch_size=len(responses))
            return responses
            
        except Exception as e:
            logger.error("Batch prediction failed", error=str(e))
            raise
    
    async def analyze_region(self, region_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze fire risk for a geographic region"""
        # Implementation would include:
        # - Grid-based sampling of the region
        # - Spatial interpolation of risk
        # - Hotspot identification
        # - Risk distribution analysis
        pass
    
    async def get_hotspots(self, bounds: str, min_risk: str, limit: int) -> List[Dict[str, Any]]:
        """Get fire risk hotspots within specified bounds"""
        # Implementation would include:
        # - Query active high-risk locations
        # - Filter by minimum risk level
        # - Sort by risk score
        # - Return top locations
        pass
    
    def _generate_request_id(self) -> str:
        """Generate unique request identifier"""
        import uuid
        return str(uuid.uuid4())
    
    async def _collect_features(self, request: PredictionRequest) -> Dict[str, Any]:
        """Collect all features required for prediction"""
        
        features = {
            'latitude': request.latitude,
            'longitude': request.longitude,
            'day_of_year': request.date.timetuple().tm_yday,
            'completeness_score': 1.0,
            'applicability_score': 1.0
        }
        
        # Weather features (fetch if not provided)
        if request.temperature_c is not None:
            features['temperature_c'] = request.temperature_c
        else:
            # Fetch from weather service
            features['temperature_c'] = await self._fetch_weather_data(request, 'temperature')
            features['completeness_score'] *= 0.9
        
        if request.relative_humidity is not None:
            features['relative_humidity'] = request.relative_humidity
        else:
            features['relative_humidity'] = await self._fetch_weather_data(request, 'humidity')
            features['completeness_score'] *= 0.9
        
        if request.wind_speed is not None:
            features['wind_speed'] = request.wind_speed
        else:
            features['wind_speed'] = await self._fetch_weather_data(request, 'wind_speed')
            features['completeness_score'] *= 0.9
        
        if request.precipitation_mm is not None:
            features['precipitation_mm'] = request.precipitation_mm
        else:
            features['precipitation_mm'] = await self._fetch_weather_data(request, 'precipitation')
            features['completeness_score'] *= 0.9
        
        # Derived weather features
        features['temperature_humidity_index'] = self._calculate_thi(features['temperature_c'], features['relative_humidity'])
        features['fire_weather_index'] = self._calculate_fwi(features)
        
        # Historical features
        features['historical_fire_frequency'] = await self._get_historical_fire_frequency(request.latitude, request.longitude)
        features['seasonal_fire_risk'] = await self._get_seasonal_fire_risk(request.date)
        
        # Topographical features
        if request.elevation_m is not None:
            features['elevation_m'] = request.elevation_m
        else:
            features['elevation_m'] = await self._fetch_elevation(request.latitude, request.longitude)
        
        features['slope'] = await self._fetch_slope(request.latitude, request.longitude)
        features['aspect'] = await self._fetch_aspect(request.latitude, request.longitude)
        
        # Vegetation features
        if request.vegetation_index is not None:
            features['ndvi'] = request.vegetation_index
        else:
            features['ndvi'] = await self._fetch_vegetation_index(request.latitude, request.longitude, request.date)
        
        features['fuel_moisture'] = await self._estimate_fuel_moisture(features)
        features['vegetation_type'] = await self._get_vegetation_type(request.latitude, request.longitude)
        
        # Drought features
        if request.drought_index is not None:
            features['drought_index'] = request.drought_index
        else:
            features['drought_index'] = await self._fetch_drought_index(request.latitude, request.longitude)

        # FireSat satellite features
        try:
            firesat_factors = await self.firesat_source.calculate_firesat_risk_factors(
                request.latitude, request.longitude
            )
            features['firesat_proximity_risk'] = firesat_factors['proximity_risk_score']
            features['firesat_spread_rate'] = firesat_factors['fire_spread_rate']
            features['firesat_max_frp'] = firesat_factors['max_frp']
            features['firesat_nearby_count'] = firesat_factors['nearby_fires_count']
        except Exception as e:
            logger.warning("Failed to fetch FireSat features", error=str(e))
            features['firesat_proximity_risk'] = 0.0
            features['firesat_spread_rate'] = 0.0
            features['firesat_max_frp'] = 0.0
            features['firesat_nearby_count'] = 0

        return features
    
    async def _run_ensemble_prediction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Run ensemble prediction using multiple models"""
        
        models = await self.model_manager.get_models()
        predictions = {
            'risk_scores': [],
            'model_predictions': {},
            'feature_importance': {}
        }
        
        # Prepare feature vector
        feature_vector = self._prepare_feature_vector(features)
        
        # Get predictions from each model
        for model_name, model in models.items():
            try:
                if hasattr(model, 'predict_proba'):
                    # For classifiers that support probability
                    prob = model.predict_proba(feature_vector.reshape(1, -1))[0]
                    risk_score = prob[1] if len(prob) > 1 else prob[0]  # Assume binary classification
                else:
                    # For regression models
                    risk_score = model.predict(feature_vector.reshape(1, -1))[0]
                
                predictions['risk_scores'].append(risk_score)
                predictions['model_predictions'][model_name] = risk_score
                
                # Get feature importance if available
                if hasattr(model, 'feature_importances_'):
                    predictions['feature_importance'][model_name] = model.feature_importances_
                    
            except Exception as e:
                logger.warning(f"Model {model_name} prediction failed", error=str(e))
                continue
        
        return predictions
    
    async def _run_batch_ensemble_prediction(self, all_features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run ensemble prediction for batch of features"""
        
        models = await self.model_manager.get_models()
        batch_predictions = []
        
        # Prepare all feature vectors
        feature_matrix = np.array([self._prepare_feature_vector(features) for features in all_features])
        
        # Get predictions from each model
        model_results = {}
        for model_name, model in models.items():
            try:
                if hasattr(model, 'predict_proba'):
                    probs = model.predict_proba(feature_matrix)
                    risk_scores = probs[:, 1] if probs.shape[1] > 1 else probs[:, 0]
                else:
                    risk_scores = model.predict(feature_matrix)
                
                model_results[model_name] = risk_scores
                
            except Exception as e:
                logger.warning(f"Batch model {model_name} prediction failed", error=str(e))
                continue
        
        # Combine results for each sample
        for i in range(len(all_features)):
            predictions = {
                'risk_scores': [],
                'model_predictions': {},
                'feature_importance': {}
            }
            
            for model_name, scores in model_results.items():
                predictions['risk_scores'].append(scores[i])
                predictions['model_predictions'][model_name] = scores[i]
            
            batch_predictions.append(predictions)
        
        return batch_predictions
    
    def _prepare_feature_vector(self, features: Dict[str, Any]) -> np.ndarray:
        """Convert feature dictionary to numpy array for model input"""
        
        # Define feature order (must match training data)
        feature_names = [
            'latitude', 'longitude', 'day_of_year',
            'temperature_c', 'relative_humidity', 'wind_speed', 'precipitation_mm',
            'temperature_humidity_index', 'fire_weather_index',
            'historical_fire_frequency', 'seasonal_fire_risk',
            'elevation_m', 'slope', 'aspect',
            'ndvi', 'fuel_moisture', 'vegetation_type',
            'drought_index',
            'firesat_proximity_risk', 'firesat_spread_rate', 'firesat_max_frp', 'firesat_nearby_count'
        ]
        
        feature_vector = []
        for name in feature_names:
            value = features.get(name, 0.0)  # Default to 0 if missing
            feature_vector.append(value)
        
        return np.array(feature_vector)
    
    def _calculate_confidence(self, predictions: Dict[str, Any]) -> float:
        """Calculate confidence score based on model agreement"""
        
        risk_scores = predictions['risk_scores']
        if not risk_scores:
            return 0.0
        
        # Calculate standard deviation as inverse confidence measure
        std_dev = np.std(risk_scores)
        max_std = 0.5  # Maximum expected standard deviation
        
        # Convert to confidence (higher std = lower confidence)
        confidence = max(0.0, 1.0 - (std_dev / max_std))
        
        return confidence
    
    def _classify_risk_level(self, risk_score: float) -> str:
        """Classify risk score into categorical risk level"""
        
        if risk_score < self.risk_thresholds['low']:
            return 'low'
        elif risk_score < self.risk_thresholds['medium']:
            return 'medium'
        elif risk_score < self.risk_thresholds['high']:
            return 'high'
        else:
            return 'extreme'
    
    async def _analyze_risk_factors(self, features: Dict[str, Any], predictions: Dict[str, Any]) -> Dict[str, float]:
        """Analyze contribution of different risk factors"""

        # Simplified factor analysis - in practice this would use SHAP or similar
        factors = {
            'weather_risk': 0.0,
            'historical_risk': 0.0,
            'vegetation_risk': 0.0,
            'topography_risk': 0.0
        }

        # Weather risk (normalized temperature, humidity, wind)
        temp_risk = min(features['temperature_c'] / 40.0, 1.0) if features['temperature_c'] > 25 else 0.0
        humidity_risk = max(0.0, (30 - features['relative_humidity']) / 30.0) if features['relative_humidity'] < 30 else 0.0
        wind_risk = min(features['wind_speed'] / 20.0, 1.0)
        factors['weather_risk'] = (temp_risk + humidity_risk + wind_risk) / 3.0

        # Historical risk (boosted by FireSat proximity risk)
        base_historical = min(features['historical_fire_frequency'] / 10.0, 1.0)
        firesat_proximity = features.get('firesat_proximity_risk', 0.0)
        factors['historical_risk'] = min((base_historical + firesat_proximity) / 2.0, 1.0)

        # Vegetation risk (based on NDVI and fuel moisture)
        ndvi_risk = max(0.0, (0.8 - features['ndvi']) / 0.8) if features['ndvi'] < 0.8 else 0.0
        fuel_risk = max(0.0, (0.3 - features.get('fuel_moisture', 0.3)) / 0.3)
        factors['vegetation_risk'] = (ndvi_risk + fuel_risk) / 2.0

        # Topography risk (elevation and slope)
        elevation_risk = features['elevation_m'] / 3000.0 if features['elevation_m'] > 1000 else 0.0
        slope_risk = features.get('slope', 0) / 45.0  # Normalize by 45 degrees
        factors['topography_risk'] = (elevation_risk + slope_risk) / 2.0

        return factors
    
    async def _get_contextual_info(self, request: PredictionRequest) -> Dict[str, Any]:
        """Get contextual information for the prediction"""

        context = {
            'nearby_fires_count': 0,
            'fire_season_factor': 1.0,
            'firesat_risk_factors': {}
        }

        # Count nearby active fires using FireSat
        context['nearby_fires_count'] = await self._count_nearby_fires(request.latitude, request.longitude)

        # Get comprehensive FireSat risk factors
        try:
            firesat_factors = await self.firesat_source.calculate_firesat_risk_factors(
                request.latitude, request.longitude
            )
            context['firesat_risk_factors'] = firesat_factors
        except Exception as e:
            logger.warning("Failed to get FireSat risk factors", error=str(e))

        # Calculate fire season factor based on date and location
        context['fire_season_factor'] = await self._calculate_fire_season_factor(request.date, request.latitude, request.longitude)

        return context
    
    # Helper methods (implementations would fetch from actual data sources)
    
    async def _fetch_weather_data(self, request: PredictionRequest, parameter: str) -> float:
        """Fetch weather data from external service"""
        # Implementation would fetch from ERA5, GFS, or other weather service
        default_values = {
            'temperature': 20.0,
            'humidity': 50.0, 
            'wind_speed': 5.0,
            'precipitation': 0.0
        }
        return default_values.get(parameter, 0.0)
    
    def _calculate_thi(self, temp_c: float, humidity: float) -> float:
        """Calculate Temperature-Humidity Index"""
        return temp_c - (0.55 - 0.0055 * humidity) * (temp_c - 14.5)
    
    def _calculate_fwi(self, features: Dict[str, Any]) -> float:
        """Calculate Fire Weather Index (simplified)"""
        temp = features['temperature_c']
        humidity = features['relative_humidity']
        wind = features['wind_speed']
        precip = features['precipitation_mm']
        
        # Simplified FWI calculation
        fwi = (temp * wind) / (humidity + 10) - precip
        return max(0.0, fwi)
    
    async def _get_historical_fire_frequency(self, lat: float, lon: float) -> float:
        """Get historical fire frequency for location"""
        # Implementation would query historical fire database
        return 2.0  # Default value
    
    async def _get_seasonal_fire_risk(self, date: date) -> float:
        """Get seasonal fire risk factor"""
        # Implementation would use seasonal fire patterns
        month = date.month
        if 6 <= month <= 9:  # Summer/fire season
            return 1.5
        elif month in [5, 10]:  # Shoulder months
            return 1.2
        else:
            return 0.8
    
    async def _fetch_elevation(self, lat: float, lon: float) -> float:
        """Fetch elevation data"""
        # Implementation would use DEM data
        return 500.0  # Default value
    
    async def _fetch_slope(self, lat: float, lon: float) -> float:
        """Fetch slope data"""
        # Implementation would calculate from DEM
        return 10.0  # Default value
    
    async def _fetch_aspect(self, lat: float, lon: float) -> float:
        """Fetch aspect data"""
        # Implementation would calculate from DEM
        return 180.0  # Default value (south-facing)
    
    async def _fetch_vegetation_index(self, lat: float, lon: float, date: date) -> float:
        """Fetch NDVI or other vegetation index"""
        # Implementation would use satellite data (MODIS, Landsat, Sentinel)
        return 0.6  # Default value
    
    async def _estimate_fuel_moisture(self, features: Dict[str, Any]) -> float:
        """Estimate fuel moisture content"""
        # Implementation would use weather and vegetation data
        return 0.15  # Default 15% moisture content
    
    async def _get_vegetation_type(self, lat: float, lon: float) -> float:
        """Get vegetation type (encoded as numeric)"""
        # Implementation would use land cover data
        return 3.0  # Default vegetation type
    
    async def _fetch_drought_index(self, lat: float, lon: float) -> float:
        """Fetch drought index (Palmer Drought Severity Index, etc.)"""
        # Implementation would use drought monitoring data
        return 0.0  # Default (no drought)
    
    async def _count_nearby_fires(self, lat: float, lon: float) -> int:
        """Count active fires within 50km radius using FireSat data"""
        try:
            detections = await self.firesat_source.get_nearby_firesat_detections(lat, lon)
            # Filter for high-confidence detections only
            high_confidence = [d for d in detections if d.get('confidence', 0) >= 0.7]
            return len(high_confidence)
        except Exception as e:
            logger.warning("Failed to count nearby fires from FireSat", error=str(e))
            return 0
    
    async def _calculate_fire_season_factor(self, date: date, lat: float, lon: float) -> float:
        """Calculate fire season factor based on location and date"""
        # Implementation would use historical fire season data
        return 1.0