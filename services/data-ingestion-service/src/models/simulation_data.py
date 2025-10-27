"""
Simulation Data Models for Google Research Integration

Models for handling FireBench simulation data, FireSat satellite data,
and other Google Research wildfire intelligence tools.

Author: Wildfire Intelligence Team
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, Text, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum
import uuid

Base = declarative_base()


class SimulationSourceType(str, Enum):
    """Types of simulation data sources"""
    FIREBENCH = "firebench"
    FIRESAT = "firesat" 
    BOUNDARY_TRACKING = "boundary_tracking"
    WILDFIRE_SIMULATION = "wildfire_simulation"
    CUSTOM = "custom"


# Pydantic models for API and data validation
class WindSlopeScenario(BaseModel):
    """Wind and slope scenario configuration"""
    
    wind_speed: float = Field(..., description="Wind speed in m/s", ge=0.0, le=50.0)
    slope: float = Field(..., description="Terrain slope in degrees", ge=0.0, le=90.0)
    scenario_id: str = Field(..., description="Unique scenario identifier")
    description: Optional[str] = Field(None, description="Human-readable description")
    
    @validator('scenario_id')
    def validate_scenario_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('scenario_id cannot be empty')
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "wind_speed": 15.0,
                "slope": 30.0,
                "scenario_id": "ws15_s30",
                "description": "High wind, steep slope scenario"
            }
        }


class VelocityComponents(BaseModel):
    """3D velocity field components"""
    
    x: float = Field(..., description="X-component velocity (m/s)")
    y: float = Field(..., description="Y-component velocity (m/s)")  
    z: float = Field(..., description="Z-component velocity (m/s)")
    
    @property
    def magnitude(self) -> float:
        """Calculate velocity magnitude"""
        return (self.x**2 + self.y**2 + self.z**2)**0.5
    
    @property
    def horizontal_magnitude(self) -> float:
        """Calculate horizontal velocity magnitude"""
        return (self.x**2 + self.y**2)**0.5


class SimulationDataPoint(BaseModel):
    """Individual simulation data point from FireBench or other sources"""
    
    # Scenario identification
    scenario_id: str = Field(..., description="Scenario identifier")
    wind_speed: float = Field(..., description="Wind speed (m/s)")
    slope: float = Field(..., description="Terrain slope (degrees)")
    
    # Spatial coordinates
    grid_point_x: float = Field(..., description="X coordinate (meters)")
    grid_point_y: float = Field(..., description="Y coordinate (meters)")
    grid_point_z: float = Field(..., description="Z coordinate (meters)")
    
    # Flow field variables (FireBench 11 variables)
    velocity_components: VelocityComponents = Field(..., description="3D velocity field")
    temperature: float = Field(..., description="Temperature (K)")
    density: float = Field(..., description="Air density (kg/m³)")
    pressure: float = Field(..., description="Pressure (Pa)")
    fuel_density: float = Field(..., description="Fuel density (kg/m³)")
    reaction_rate: float = Field(..., description="Chemical reaction rate")
    heat_release: float = Field(..., description="Heat release rate (W/m³)")
    mixture_fraction: float = Field(..., description="Fuel mixture fraction")
    progress_variable: float = Field(..., description="Combustion progress variable")
    
    # Metadata
    simulation_timestamp: datetime = Field(..., description="Simulation timestamp")
    source: SimulationSourceType = Field(..., description="Data source type")
    quality_score: Optional[float] = Field(None, description="Data quality score (0-1)")
    
    # Additional computed fields
    fire_risk_indicator: Optional[float] = Field(None, description="Computed fire risk (0-1)")
    turbulence_intensity: Optional[float] = Field(None, description="Turbulence intensity")
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if v < 200 or v > 2000:  # Reasonable temperature range in Kelvin
            raise ValueError(f'Temperature {v}K is outside reasonable range (200-2000K)')
        return v
    
    @validator('quality_score', pre=True)
    def validate_quality_score(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Quality score must be between 0 and 1')
        return v

    class Config:
        schema_extra = {
            "example": {
                "scenario_id": "ws15_s30",
                "wind_speed": 15.0,
                "slope": 30.0,
                "grid_point_x": 500.0,
                "grid_point_y": 750.0,
                "grid_point_z": 25.0,
                "velocity_components": {"x": 12.5, "y": 3.2, "z": -1.1},
                "temperature": 450.0,
                "density": 1.1,
                "pressure": 101325.0,
                "fuel_density": 0.8,
                "reaction_rate": 0.05,
                "heat_release": 1500.0,
                "mixture_fraction": 0.3,
                "progress_variable": 0.7,
                "source": "firebench"
            }
        }


class FireSatDetection(BaseModel):
    """FireSat satellite fire detection data"""
    
    detection_id: str = Field(..., description="Unique detection identifier")
    latitude: float = Field(..., description="Latitude (decimal degrees)", ge=-90, le=90)
    longitude: float = Field(..., description="Longitude (decimal degrees)", ge=-180, le=180)
    
    # Detection properties
    confidence: float = Field(..., description="Detection confidence (0-1)", ge=0, le=1)
    fire_size_estimate: Optional[float] = Field(None, description="Estimated fire size (hectares)")
    temperature_estimate: Optional[float] = Field(None, description="Fire temperature (K)")
    
    # Satellite metadata
    satellite_name: str = Field(..., description="Satellite identifier")
    detection_time: datetime = Field(..., description="Detection timestamp")
    image_resolution: float = Field(..., description="Image resolution (meters/pixel)")
    
    # Environmental context
    weather_conditions: Optional[Dict[str, Any]] = Field(None, description="Weather at detection")
    terrain_info: Optional[Dict[str, Any]] = Field(None, description="Terrain characteristics")
    
    class Config:
        schema_extra = {
            "example": {
                "detection_id": "firesat_20240315_001234",
                "latitude": 34.0522,
                "longitude": -118.2437,
                "confidence": 0.95,
                "fire_size_estimate": 2.5,
                "temperature_estimate": 800.0,
                "satellite_name": "FireSat-1",
                "detection_time": "2024-03-15T14:30:00Z",
                "image_resolution": 10.0
            }
        }


class BoundaryTrackingData(BaseModel):
    """AI-powered fire boundary tracking data"""
    
    boundary_id: str = Field(..., description="Unique boundary identifier")
    fire_perimeter: Dict[str, Any] = Field(..., description="GeoJSON fire perimeter")
    
    # Boundary analysis
    total_area: float = Field(..., description="Total fire area (hectares)")
    perimeter_length: float = Field(..., description="Perimeter length (meters)")
    growth_rate: Optional[float] = Field(None, description="Area growth rate (hectares/hour)")
    
    # AI model metadata
    model_version: str = Field(..., description="AI model version")
    analysis_timestamp: datetime = Field(..., description="Analysis timestamp")
    confidence_map: Optional[Dict[str, float]] = Field(None, description="Spatial confidence map")
    
    # Change detection
    previous_boundary_id: Optional[str] = Field(None, description="Previous boundary for comparison")
    area_change: Optional[float] = Field(None, description="Area change since previous (hectares)")
    expansion_directions: Optional[List[str]] = Field(None, description="Primary expansion directions")
    
    class Config:
        schema_extra = {
            "example": {
                "boundary_id": "boundary_20240315_1430",
                "fire_perimeter": {"type": "Polygon", "coordinates": [[]]},
                "total_area": 1250.0,
                "perimeter_length": 15000.0,
                "growth_rate": 50.0,
                "model_version": "v2.1",
                "analysis_timestamp": "2024-03-15T14:30:00Z"
            }
        }


# SQLAlchemy database models
class SimulationDataDB(Base):
    """Database model for simulation data storage"""
    
    __tablename__ = "simulation_data"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Scenario identification
    scenario_id = Column(String(100), nullable=False, index=True)
    wind_speed = Column(Float, nullable=False)
    slope = Column(Float, nullable=False)
    
    # Spatial coordinates
    grid_point_x = Column(Float, nullable=False)
    grid_point_y = Column(Float, nullable=False)
    grid_point_z = Column(Float, nullable=False)
    
    # Flow field variables
    velocity_x = Column(Float, nullable=False)
    velocity_y = Column(Float, nullable=False)
    velocity_z = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    density = Column(Float, nullable=False)
    pressure = Column(Float, nullable=False)
    fuel_density = Column(Float, nullable=False)
    reaction_rate = Column(Float, nullable=False)
    heat_release = Column(Float, nullable=False)
    mixture_fraction = Column(Float, nullable=False)
    progress_variable = Column(Float, nullable=False)
    
    # Computed fields
    velocity_magnitude = Column(Float)
    fire_risk_indicator = Column(Float)
    turbulence_intensity = Column(Float)
    
    # Metadata
    simulation_timestamp = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(50), nullable=False)
    quality_score = Column(Float)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for query optimization
    __table_args__ = (
        Index('idx_scenario_location', 'scenario_id', 'grid_point_x', 'grid_point_y'),
        Index('idx_wind_slope', 'wind_speed', 'slope'),
        Index('idx_fire_risk', 'fire_risk_indicator'),
        Index('idx_timestamp', 'simulation_timestamp'),
    )


class FireSatDetectionDB(Base):
    """Database model for FireSat detection data"""
    
    __tablename__ = "firesat_detections"
    
    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Detection properties
    confidence = Column(Float, nullable=False)
    fire_size_estimate = Column(Float)
    temperature_estimate = Column(Float)
    
    # Satellite metadata
    satellite_name = Column(String(50), nullable=False)
    detection_time = Column(DateTime(timezone=True), nullable=False, index=True)
    image_resolution = Column(Float)
    
    # Environmental context (JSON fields)
    weather_conditions = Column(JSONB)
    terrain_info = Column(JSONB)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    processed = Column(Boolean, default=False, index=True)
    
    __table_args__ = (
        Index('idx_detection_location', 'latitude', 'longitude'),
        Index('idx_detection_time', 'detection_time'),
        Index('idx_confidence', 'confidence'),
    )


class BoundaryTrackingDB(Base):
    """Database model for boundary tracking data"""
    
    __tablename__ = "boundary_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    boundary_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Boundary data
    fire_perimeter = Column(JSONB, nullable=False)  # GeoJSON
    total_area = Column(Float, nullable=False)
    perimeter_length = Column(Float, nullable=False)
    growth_rate = Column(Float)
    
    # AI model metadata
    model_version = Column(String(20), nullable=False)
    analysis_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    confidence_map = Column(JSONB)
    
    # Change detection
    previous_boundary_id = Column(String(100), index=True)
    area_change = Column(Float)
    expansion_directions = Column(JSONB)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_boundary_time', 'analysis_timestamp'),
        Index('idx_area', 'total_area'),
    )


class SimulationScenarioDB(Base):
    """Database model for simulation scenario metadata"""
    
    __tablename__ = "simulation_scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Scenario parameters
    wind_speed = Column(Float, nullable=False)
    slope = Column(Float, nullable=False)
    description = Column(Text)
    
    # Dataset metadata
    source_dataset = Column(String(50), nullable=False)  # e.g., "firebench"
    data_points_count = Column(Integer)
    file_size_mb = Column(Float)
    
    # Processing status
    download_status = Column(String(20), default="pending", index=True)
    processing_status = Column(String(20), default="pending", index=True)
    last_processed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    
    # Quality metrics
    data_quality_score = Column(Float)
    validation_passed = Column(Boolean)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_scenario_params', 'wind_speed', 'slope'),
        Index('idx_processing_status', 'processing_status'),
    )


# Response models for APIs
class SimulationDataResponse(BaseModel):
    """API response model for simulation data"""
    
    data_points: List[SimulationDataPoint]
    total_count: int
    scenario_metadata: WindSlopeScenario
    processing_info: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "data_points": [],
                "total_count": 1500,
                "scenario_metadata": {
                    "wind_speed": 15.0,
                    "slope": 30.0,
                    "scenario_id": "ws15_s30"
                },
                "processing_info": {
                    "processed_at": "2024-03-15T14:30:00Z",
                    "quality_score": 0.95,
                    "source": "firebench"
                }
            }
        }


class FireSatDetectionResponse(BaseModel):
    """API response model for FireSat detections"""
    
    detections: List[FireSatDetection]
    total_count: int
    time_range: Dict[str, datetime]
    coverage_area: Optional[Dict[str, Any]] = None  # GeoJSON bounds
    
    class Config:
        schema_extra = {
            "example": {
                "detections": [],
                "total_count": 25,
                "time_range": {
                    "start": "2024-03-15T00:00:00Z",
                    "end": "2024-03-15T23:59:59Z"
                }
            }
        }


class BoundaryTrackingResponse(BaseModel):
    """API response model for boundary tracking"""
    
    boundaries: List[BoundaryTrackingData]
    total_count: int
    time_series_data: Optional[List[Dict[str, Any]]] = None
    growth_analysis: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "boundaries": [],
                "total_count": 10,
                "growth_analysis": {
                    "average_growth_rate": 25.5,
                    "peak_growth_period": "2024-03-15T12:00:00Z",
                    "total_area_change": 500.0
                }
            }
        }


# Utility functions for data conversion
def simulation_data_to_db(data_point: SimulationDataPoint) -> SimulationDataDB:
    """Convert Pydantic model to SQLAlchemy model"""
    
    return SimulationDataDB(
        scenario_id=data_point.scenario_id,
        wind_speed=data_point.wind_speed,
        slope=data_point.slope,
        grid_point_x=data_point.grid_point_x,
        grid_point_y=data_point.grid_point_y,
        grid_point_z=data_point.grid_point_z,
        velocity_x=data_point.velocity_components.x,
        velocity_y=data_point.velocity_components.y,
        velocity_z=data_point.velocity_components.z,
        velocity_magnitude=data_point.velocity_components.magnitude,
        temperature=data_point.temperature,
        density=data_point.density,
        pressure=data_point.pressure,
        fuel_density=data_point.fuel_density,
        reaction_rate=data_point.reaction_rate,
        heat_release=data_point.heat_release,
        mixture_fraction=data_point.mixture_fraction,
        progress_variable=data_point.progress_variable,
        fire_risk_indicator=data_point.fire_risk_indicator,
        turbulence_intensity=data_point.turbulence_intensity,
        simulation_timestamp=data_point.simulation_timestamp,
        source=data_point.source,
        quality_score=data_point.quality_score
    )


def db_to_simulation_data(db_record: SimulationDataDB) -> SimulationDataPoint:
    """Convert SQLAlchemy model to Pydantic model"""
    
    return SimulationDataPoint(
        scenario_id=db_record.scenario_id,
        wind_speed=db_record.wind_speed,
        slope=db_record.slope,
        grid_point_x=db_record.grid_point_x,
        grid_point_y=db_record.grid_point_y,
        grid_point_z=db_record.grid_point_z,
        velocity_components=VelocityComponents(
            x=db_record.velocity_x,
            y=db_record.velocity_y,
            z=db_record.velocity_z
        ),
        temperature=db_record.temperature,
        density=db_record.density,
        pressure=db_record.pressure,
        fuel_density=db_record.fuel_density,
        reaction_rate=db_record.reaction_rate,
        heat_release=db_record.heat_release,
        mixture_fraction=db_record.mixture_fraction,
        progress_variable=db_record.progress_variable,
        fire_risk_indicator=db_record.fire_risk_indicator,
        turbulence_intensity=db_record.turbulence_intensity,
        simulation_timestamp=db_record.simulation_timestamp,
        source=SimulationSourceType(db_record.source),
        quality_score=db_record.quality_score
    )