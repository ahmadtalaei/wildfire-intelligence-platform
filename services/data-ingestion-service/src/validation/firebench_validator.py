"""
FireBench Data Validation Module

Validates data quality and consistency for Google Research FireBench simulation data
and other integrated wildfire intelligence sources.

Author: Wildfire Intelligence Team
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pydantic import ValidationError

from ..models.simulation_data import (
    SimulationDataPoint, 
    WindSlopeScenario,
    FireSatDetection,
    BoundaryTrackingData,
    VelocityComponents
)
from ..utils.logging import get_logger

logger = get_logger(__name__)


class FireBenchDataValidator:
    """
    Comprehensive data validation for FireBench and Google Research integration
    
    Validates:
    - Physical consistency of flow field variables
    - Spatial and temporal data integrity
    - Data quality metrics and outlier detection
    - Cross-validation with known fire behavior patterns
    """
    
    def __init__(self):
        # Physical constants and reasonable ranges
        self.validation_ranges = {
            'temperature': (200.0, 2000.0),  # Kelvin
            'density': (0.5, 5.0),  # kg/m³ (altitude variations)
            'pressure': (50000.0, 150000.0),  # Pa (altitude variations)
            'fuel_density': (0.0, 10.0),  # kg/m³
            'velocity_magnitude': (0.0, 100.0),  # m/s
            'reaction_rate': (0.0, 1.0),  # normalized
            'heat_release': (0.0, 50000.0),  # W/m³
            'mixture_fraction': (0.0, 1.0),  # normalized
            'progress_variable': (0.0, 1.0),  # normalized
        }
        
        # Quality thresholds
        self.quality_thresholds = {
            'min_data_points': 100,
            'max_outlier_percentage': 0.05,  # 5%
            'min_spatial_coverage': 0.8,  # 80% grid coverage
            'consistency_threshold': 0.95
        }
        
        logger.info("FireBench data validator initialized")

    async def validate_scenario_data(self, data_points: List[SimulationDataPoint]) -> Dict[str, Any]:
        """
        Comprehensive validation of simulation scenario data
        
        Args:
            data_points: List of simulation data points to validate
            
        Returns:
            Validation results with detailed metrics and error information
        """
        validation_results = {
            'is_valid': True,
            'quality_score': 0.0,
            'errors': [],
            'warnings': [],
            'metrics': {},
            'validation_timestamp': datetime.now(timezone.utc)
        }
        
        try:
            logger.info(f"Validating {len(data_points)} simulation data points")
            
            if not data_points:
                validation_results['is_valid'] = False
                validation_results['errors'].append("No data points provided for validation")
                return validation_results
            
            # Convert to DataFrame for efficient analysis
            df_data = []
            for point in data_points:
                try:
                    df_data.append({
                        'scenario_id': point.scenario_id,
                        'wind_speed': point.wind_speed,
                        'slope': point.slope,
                        'x': point.grid_point_x,
                        'y': point.grid_point_y,
                        'z': point.grid_point_z,
                        'vel_x': point.velocity_components.x,
                        'vel_y': point.velocity_components.y,
                        'vel_z': point.velocity_components.z,
                        'vel_mag': point.velocity_components.magnitude,
                        'temperature': point.temperature,
                        'density': point.density,
                        'pressure': point.pressure,
                        'fuel_density': point.fuel_density,
                        'reaction_rate': point.reaction_rate,
                        'heat_release': point.heat_release,
                        'mixture_fraction': point.mixture_fraction,
                        'progress_variable': point.progress_variable,
                        'source': point.source
                    })
                except Exception as e:
                    validation_results['errors'].append(f"Error processing data point: {e}")
            
            df = pd.DataFrame(df_data)
            
            # Run validation checks
            validation_checks = [
                self._validate_data_completeness,
                self._validate_physical_consistency,
                self._validate_spatial_distribution,
                self._validate_flow_field_physics,
                self._validate_combustion_variables,
                self._detect_outliers,
                self._validate_scenario_consistency
            ]
            
            check_scores = []
            for check_func in validation_checks:
                try:
                    check_result = await check_func(df, validation_results)
                    check_scores.append(check_result['score'])
                    
                    # Merge errors and warnings
                    validation_results['errors'].extend(check_result.get('errors', []))
                    validation_results['warnings'].extend(check_result.get('warnings', []))
                    
                    # Add check-specific metrics
                    check_name = check_func.__name__.replace('_validate_', '').replace('_detect_', 'detect_')
                    validation_results['metrics'][check_name] = check_result.get('metrics', {})
                    
                except Exception as e:
                    logger.error(f"Validation check {check_func.__name__} failed: {e}")
                    validation_results['errors'].append(f"Validation check failed: {check_func.__name__}")
                    check_scores.append(0.0)
            
            # Calculate overall quality score
            validation_results['quality_score'] = np.mean(check_scores) if check_scores else 0.0
            
            # Determine overall validity
            validation_results['is_valid'] = (
                validation_results['quality_score'] >= 0.7 and
                len(validation_results['errors']) == 0
            )
            
            # Add summary metrics
            validation_results['metrics']['summary'] = {
                'total_data_points': len(data_points),
                'unique_scenarios': len(df['scenario_id'].unique()),
                'spatial_coverage': len(df[['x', 'y', 'z']].drop_duplicates()),
                'error_count': len(validation_results['errors']),
                'warning_count': len(validation_results['warnings'])
            }
            
            logger.info(f"Validation completed. Quality score: {validation_results['quality_score']:.3f}, "
                       f"Valid: {validation_results['is_valid']}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Validation process failed: {e}")
            validation_results['is_valid'] = False
            validation_results['errors'].append(f"Validation process error: {str(e)}")
            return validation_results

    async def _validate_data_completeness(self, df: pd.DataFrame, results: Dict) -> Dict[str, Any]:
        """Validate data completeness and required fields"""
        
        check_result = {
            'score': 1.0,
            'errors': [],
            'warnings': [],
            'metrics': {}
        }
        
        try:
            # Check for missing values
            missing_data = df.isnull().sum()
            total_cells = len(df) * len(df.columns)
            missing_percentage = missing_data.sum() / total_cells
            
            check_result['metrics']['missing_percentage'] = float(missing_percentage)
            check_result['metrics']['missing_by_column'] = missing_data.to_dict()
            
            if missing_percentage > 0.01:  # More than 1% missing
                check_result['warnings'].append(f"Missing data: {missing_percentage:.2%} of total values")
                check_result['score'] *= 0.9
            
            # Check minimum data points
            if len(df) < self.quality_thresholds['min_data_points']:
                check_result['errors'].append(
                    f"Insufficient data points: {len(df)} < {self.quality_thresholds['min_data_points']}"
                )
                check_result['score'] *= 0.5
            
            # Check for duplicate data points
            duplicates = df.duplicated(['scenario_id', 'x', 'y', 'z']).sum()
            if duplicates > 0:
                check_result['warnings'].append(f"Found {duplicates} duplicate spatial points")
                check_result['score'] *= 0.95
            
            check_result['metrics']['duplicate_points'] = int(duplicates)
            
        except Exception as e:
            check_result['errors'].append(f"Data completeness check failed: {e}")
            check_result['score'] = 0.0
        
        return check_result

    async def _validate_physical_consistency(self, df: pd.DataFrame, results: Dict) -> Dict[str, Any]:
        """Validate physical consistency of variables"""
        
        check_result = {
            'score': 1.0,
            'errors': [],
            'warnings': [],
            'metrics': {'range_violations': {}}
        }
        
        try:
            # Check value ranges
            range_violations = 0
            for variable, (min_val, max_val) in self.validation_ranges.items():
                if variable == 'velocity_magnitude':
                    values = df['vel_mag']
                else:
                    values = df.get(variable)
                
                if values is not None:
                    violations = ((values < min_val) | (values > max_val)).sum()
                    violation_percentage = violations / len(values)
                    
                    check_result['metrics']['range_violations'][variable] = {
                        'count': int(violations),
                        'percentage': float(violation_percentage)
                    }
                    
                    if violation_percentage > 0.01:  # More than 1% violations
                        check_result['warnings'].append(
                            f"{variable}: {violation_percentage:.1%} values outside range "
                            f"[{min_val}, {max_val}]"
                        )
                        range_violations += violations
            
            # Penalty for range violations
            if range_violations > 0:
                violation_rate = range_violations / (len(df) * len(self.validation_ranges))
                check_result['score'] *= max(0.1, 1.0 - violation_rate * 2)
            
            # Check for infinite or NaN values
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            inf_count = np.isinf(df[numeric_cols]).sum().sum()
            nan_count = np.isnan(df[numeric_cols]).sum().sum()
            
            if inf_count > 0:
                check_result['errors'].append(f"Found {inf_count} infinite values")
                check_result['score'] *= 0.5
            
            if nan_count > 0:
                check_result['warnings'].append(f"Found {nan_count} NaN values")
                check_result['score'] *= 0.9
            
            check_result['metrics']['infinite_values'] = int(inf_count)
            check_result['metrics']['nan_values'] = int(nan_count)
            
        except Exception as e:
            check_result['errors'].append(f"Physical consistency check failed: {e}")
            check_result['score'] = 0.0
        
        return check_result

    async def _validate_spatial_distribution(self, df: pd.DataFrame, results: Dict) -> Dict[str, Any]:
        """Validate spatial distribution and coverage"""
        
        check_result = {
            'score': 1.0,
            'errors': [],
            'warnings': [],
            'metrics': {}
        }
        
        try:
            # Check spatial coverage
            unique_locations = len(df[['x', 'y', 'z']].drop_duplicates())
            total_points = len(df)
            coverage_ratio = unique_locations / total_points
            
            check_result['metrics']['spatial_coverage_ratio'] = float(coverage_ratio)
            check_result['metrics']['unique_locations'] = int(unique_locations)
            
            if coverage_ratio < self.quality_thresholds['min_spatial_coverage']:
                check_result['warnings'].append(
                    f"Low spatial coverage: {coverage_ratio:.1%} unique locations"
                )
                check_result['score'] *= 0.8
            
            # Check for spatial clustering
            x_std = df['x'].std()
            y_std = df['y'].std()
            z_std = df['z'].std()
            
            check_result['metrics']['spatial_distribution'] = {
                'x_std': float(x_std),
                'y_std': float(y_std), 
                'z_std': float(z_std)
            }
            
            # Check grid regularity (for structured simulation data)
            x_unique = sorted(df['x'].unique())
            if len(x_unique) > 1:
                x_spacing = np.diff(x_unique)
                x_regular = np.std(x_spacing) / np.mean(x_spacing) < 0.1  # 10% variation
                check_result['metrics']['grid_regularity_x'] = bool(x_regular)
            
        except Exception as e:
            check_result['errors'].append(f"Spatial distribution check failed: {e}")
            check_result['score'] = 0.0
        
        return check_result

    async def _validate_flow_field_physics(self, df: pd.DataFrame, results: Dict) -> Dict[str, Any]:
        """Validate flow field physics and relationships"""
        
        check_result = {
            'score': 1.0,
            'errors': [],
            'warnings': [],
            'metrics': {}
        }
        
        try:
            # Validate velocity magnitude calculation
            calculated_vel_mag = np.sqrt(df['vel_x']**2 + df['vel_y']**2 + df['vel_z']**2)
            vel_mag_error = np.abs(calculated_vel_mag - df['vel_mag']).mean()
            
            check_result['metrics']['velocity_magnitude_error'] = float(vel_mag_error)
            
            if vel_mag_error > 0.1:  # 0.1 m/s average error
                check_result['warnings'].append(f"Velocity magnitude calculation error: {vel_mag_error:.3f} m/s")
                check_result['score'] *= 0.9
            
            # Check continuity equation consistency (approximate)
            # For structured grid, check divergence
            if len(df) > 100:  # Enough points for gradient calculation
                try:
                    # Simple finite difference approximation
                    df_sorted = df.sort_values(['x', 'y', 'z'])
                    
                    # Check if velocities are correlated with pressure gradients
                    pressure_vel_corr = np.corrcoef(df['pressure'], df['vel_mag'])[0, 1]
                    check_result['metrics']['pressure_velocity_correlation'] = float(pressure_vel_corr)
                    
                    # Temperature-density relationship (ideal gas approximation)
                    if not df['temperature'].isna().all() and not df['density'].isna().all():
                        temp_density_product = df['temperature'] * df['density']
                        product_std = temp_density_product.std() / temp_density_product.mean()
                        check_result['metrics']['temperature_density_consistency'] = float(product_std)
                        
                        if product_std > 0.2:  # High variation in T*rho
                            check_result['warnings'].append(
                                f"Temperature-density relationship inconsistent: CV = {product_std:.2f}"
                            )
                            check_result['score'] *= 0.95
                    
                except Exception as e:
                    logger.debug(f"Flow physics detailed check failed: {e}")
            
        except Exception as e:
            check_result['errors'].append(f"Flow field physics check failed: {e}")
            check_result['score'] = 0.0
        
        return check_result

    async def _validate_combustion_variables(self, df: pd.DataFrame, results: Dict) -> Dict[str, Any]:
        """Validate combustion-related variables"""
        
        check_result = {
            'score': 1.0,
            'errors': [],
            'warnings': [],
            'metrics': {}
        }
        
        try:
            # Check combustion variable relationships
            combustion_vars = ['fuel_density', 'reaction_rate', 'heat_release', 
                             'mixture_fraction', 'progress_variable', 'temperature']
            
            available_vars = [var for var in combustion_vars if var in df.columns]
            check_result['metrics']['available_combustion_vars'] = available_vars
            
            if len(available_vars) < 4:
                check_result['warnings'].append(
                    f"Limited combustion variables: {len(available_vars)}/{len(combustion_vars)}"
                )
                check_result['score'] *= 0.9
            
            # Validate combustion physics relationships
            if 'fuel_density' in df.columns and 'reaction_rate' in df.columns:
                # Where there's no fuel, there should be no reaction
                no_fuel_reaction = ((df['fuel_density'] == 0) & (df['reaction_rate'] > 0.01)).sum()
                if no_fuel_reaction > 0:
                    check_result['warnings'].append(
                        f"Found {no_fuel_reaction} points with reaction but no fuel"
                    )
                    check_result['score'] *= 0.95
                
                check_result['metrics']['no_fuel_reaction_count'] = int(no_fuel_reaction)
            
            # Heat release should correlate with reaction rate
            if 'heat_release' in df.columns and 'reaction_rate' in df.columns:
                heat_reaction_corr = np.corrcoef(df['heat_release'], df['reaction_rate'])[0, 1]
                check_result['metrics']['heat_release_reaction_correlation'] = float(heat_reaction_corr)
                
                if abs(heat_reaction_corr) < 0.5:
                    check_result['warnings'].append(
                        f"Weak heat release-reaction rate correlation: {heat_reaction_corr:.2f}"
                    )
                    check_result['score'] *= 0.95
            
            # Progress variable should be between 0 and 1
            if 'progress_variable' in df.columns:
                invalid_progress = ((df['progress_variable'] < 0) | (df['progress_variable'] > 1)).sum()
                if invalid_progress > 0:
                    check_result['errors'].append(
                        f"Invalid progress variable values: {invalid_progress} points outside [0,1]"
                    )
                    check_result['score'] *= 0.8
                
                check_result['metrics']['invalid_progress_variable_count'] = int(invalid_progress)
            
        except Exception as e:
            check_result['errors'].append(f"Combustion variables check failed: {e}")
            check_result['score'] = 0.0
        
        return check_result

    async def _detect_outliers(self, df: pd.DataFrame, results: Dict) -> Dict[str, Any]:
        """Detect statistical outliers in the data"""
        
        check_result = {
            'score': 1.0,
            'errors': [],
            'warnings': [],
            'metrics': {'outliers_by_variable': {}}
        }
        
        try:
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            total_outliers = 0
            
            for col in numeric_columns:
                if col in ['x', 'y', 'z']:  # Skip spatial coordinates
                    continue
                
                # Use IQR method for outlier detection
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
                outlier_percentage = outliers / len(df)
                
                check_result['metrics']['outliers_by_variable'][col] = {
                    'count': int(outliers),
                    'percentage': float(outlier_percentage),
                    'bounds': [float(lower_bound), float(upper_bound)]
                }
                
                total_outliers += outliers
                
                if outlier_percentage > 0.1:  # More than 10% outliers
                    check_result['warnings'].append(
                        f"{col}: {outlier_percentage:.1%} outlier values"
                    )
            
            # Overall outlier assessment
            overall_outlier_rate = total_outliers / (len(df) * len(numeric_columns))
            check_result['metrics']['overall_outlier_rate'] = float(overall_outlier_rate)
            
            if overall_outlier_rate > self.quality_thresholds['max_outlier_percentage']:
                check_result['warnings'].append(
                    f"High outlier rate: {overall_outlier_rate:.1%}"
                )
                check_result['score'] *= max(0.5, 1.0 - overall_outlier_rate * 2)
            
        except Exception as e:
            check_result['errors'].append(f"Outlier detection failed: {e}")
            check_result['score'] = 0.0
        
        return check_result

    async def _validate_scenario_consistency(self, df: pd.DataFrame, results: Dict) -> Dict[str, Any]:
        """Validate consistency within scenarios"""
        
        check_result = {
            'score': 1.0,
            'errors': [],
            'warnings': [],
            'metrics': {}
        }
        
        try:
            scenarios = df['scenario_id'].unique()
            check_result['metrics']['scenario_count'] = len(scenarios)
            
            consistency_issues = 0
            
            for scenario in scenarios:
                scenario_data = df[df['scenario_id'] == scenario]
                
                # Check that wind_speed and slope are consistent within scenario
                unique_wind_speeds = scenario_data['wind_speed'].nunique()
                unique_slopes = scenario_data['slope'].nunique()
                
                if unique_wind_speeds > 1:
                    check_result['warnings'].append(
                        f"Scenario {scenario}: Multiple wind speeds ({unique_wind_speeds})"
                    )
                    consistency_issues += 1
                
                if unique_slopes > 1:
                    check_result['warnings'].append(
                        f"Scenario {scenario}: Multiple slopes ({unique_slopes})"
                    )
                    consistency_issues += 1
                
                # Check data point distribution
                point_count = len(scenario_data)
                if point_count < 50:  # Minimum expected points per scenario
                    check_result['warnings'].append(
                        f"Scenario {scenario}: Low data point count ({point_count})"
                    )
                    consistency_issues += 1
            
            check_result['metrics']['consistency_issues'] = consistency_issues
            
            if consistency_issues > len(scenarios) * 0.1:  # More than 10% of scenarios have issues
                check_result['score'] *= 0.8
            
        except Exception as e:
            check_result['errors'].append(f"Scenario consistency check failed: {e}")
            check_result['score'] = 0.0
        
        return check_result

    async def validate_firesat_detection(self, detection: FireSatDetection) -> Dict[str, Any]:
        """Validate individual FireSat detection data"""
        
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'quality_score': 1.0
        }
        
        try:
            # Validate coordinates
            if not (-90 <= detection.latitude <= 90):
                validation_results['errors'].append(f"Invalid latitude: {detection.latitude}")
                validation_results['is_valid'] = False
            
            if not (-180 <= detection.longitude <= 180):
                validation_results['errors'].append(f"Invalid longitude: {detection.longitude}")
                validation_results['is_valid'] = False
            
            # Validate confidence
            if not (0 <= detection.confidence <= 1):
                validation_results['errors'].append(f"Invalid confidence: {detection.confidence}")
                validation_results['is_valid'] = False
            
            # Check reasonable fire size
            if detection.fire_size_estimate and detection.fire_size_estimate > 100000:  # 100,000 hectares
                validation_results['warnings'].append(
                    f"Unusually large fire size estimate: {detection.fire_size_estimate} hectares"
                )
                validation_results['quality_score'] *= 0.9
            
            # Check reasonable temperature
            if detection.temperature_estimate:
                if detection.temperature_estimate < 400 or detection.temperature_estimate > 1500:
                    validation_results['warnings'].append(
                        f"Fire temperature outside typical range: {detection.temperature_estimate}K"
                    )
                    validation_results['quality_score'] *= 0.95
            
        except Exception as e:
            validation_results['errors'].append(f"FireSat validation error: {e}")
            validation_results['is_valid'] = False
            validation_results['quality_score'] = 0.0
        
        return validation_results

    async def validate_boundary_tracking(self, boundary_data: BoundaryTrackingData) -> Dict[str, Any]:
        """Validate boundary tracking data"""
        
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'quality_score': 1.0
        }
        
        try:
            # Validate GeoJSON structure
            perimeter = boundary_data.fire_perimeter
            if not isinstance(perimeter, dict) or 'type' not in perimeter:
                validation_results['errors'].append("Invalid GeoJSON structure")
                validation_results['is_valid'] = False
                return validation_results
            
            # Check area consistency
            if boundary_data.total_area <= 0:
                validation_results['errors'].append(f"Invalid total area: {boundary_data.total_area}")
                validation_results['is_valid'] = False
            
            # Check perimeter length
            if boundary_data.perimeter_length <= 0:
                validation_results['errors'].append(f"Invalid perimeter length: {boundary_data.perimeter_length}")
                validation_results['is_valid'] = False
            
            # Geometric consistency check (approximate)
            if boundary_data.total_area > 0 and boundary_data.perimeter_length > 0:
                # For circular area: A = pir², P = 2pir, so P² / (4pi) should be roughly equal to A
                shape_factor = (boundary_data.perimeter_length ** 2) / (4 * np.pi * boundary_data.total_area)
                
                if shape_factor < 0.8 or shape_factor > 10:  # Very elongated or complex shape
                    validation_results['warnings'].append(
                        f"Unusual shape factor: {shape_factor:.2f} (circular = 1.0)"
                    )
                    validation_results['quality_score'] *= 0.95
            
            # Check growth rate reasonableness
            if boundary_data.growth_rate:
                if abs(boundary_data.growth_rate) > 1000:  # 1000 hectares/hour seems extreme
                    validation_results['warnings'].append(
                        f"Extreme growth rate: {boundary_data.growth_rate} hectares/hour"
                    )
                    validation_results['quality_score'] *= 0.9
            
        except Exception as e:
            validation_results['errors'].append(f"Boundary tracking validation error: {e}")
            validation_results['is_valid'] = False
            validation_results['quality_score'] = 0.0
        
        return validation_results

    async def generate_quality_report(self, validation_results: Dict[str, Any]) -> str:
        """Generate a human-readable quality report"""
        
        try:
            report_lines = [
                "=== FireBench Data Quality Report ===",
                f"Validation Timestamp: {validation_results['validation_timestamp']}",
                f"Overall Quality Score: {validation_results['quality_score']:.3f}",
                f"Data Valid: {'✓' if validation_results['is_valid'] else '✗'}",
                ""
            ]
            
            # Summary metrics
            if 'metrics' in validation_results and 'summary' in validation_results['metrics']:
                summary = validation_results['metrics']['summary']
                report_lines.extend([
                    "=== Summary ===",
                    f"Total Data Points: {summary.get('total_data_points', 'N/A')}",
                    f"Unique Scenarios: {summary.get('unique_scenarios', 'N/A')}",
                    f"Spatial Coverage: {summary.get('spatial_coverage', 'N/A')} unique locations",
                    f"Errors: {summary.get('error_count', 0)}",
                    f"Warnings: {summary.get('warning_count', 0)}",
                    ""
                ])
            
            # Errors
            if validation_results['errors']:
                report_lines.append("=== Errors ===")
                for error in validation_results['errors']:
                    report_lines.append(f"[X] {error}")
                report_lines.append("")
            
            # Warnings  
            if validation_results['warnings']:
                report_lines.append("=== Warnings ===")
                for warning in validation_results['warnings']:
                    report_lines.append(f"[WARNING]  {warning}")
                report_lines.append("")
            
            # Detailed metrics
            if 'metrics' in validation_results:
                report_lines.append("=== Detailed Metrics ===")
                for check_name, metrics in validation_results['metrics'].items():
                    if check_name != 'summary' and isinstance(metrics, dict):
                        report_lines.append(f"{check_name.replace('_', ' ').title()}:")
                        for key, value in metrics.items():
                            if isinstance(value, (int, float)):
                                report_lines.append(f"  {key}: {value}")
                            elif isinstance(value, dict):
                                report_lines.append(f"  {key}:")
                                for subkey, subvalue in value.items():
                                    report_lines.append(f"    {subkey}: {subvalue}")
                        report_lines.append("")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Error generating quality report: {e}")
            return f"Error generating quality report: {e}"


# Utility functions for batch validation
async def validate_simulation_batch(
    data_points: List[SimulationDataPoint],
    validator: FireBenchDataValidator = None
) -> Dict[str, Any]:
    """Validate a batch of simulation data points"""
    
    if not validator:
        validator = FireBenchDataValidator()
    
    return await validator.validate_scenario_data(data_points)


async def validate_firesat_batch(
    detections: List[FireSatDetection],
    validator: FireBenchDataValidator = None
) -> List[Dict[str, Any]]:
    """Validate a batch of FireSat detections"""
    
    if not validator:
        validator = FireBenchDataValidator()
    
    results = []
    for detection in detections:
        result = await validator.validate_firesat_detection(detection)
        result['detection_id'] = detection.detection_id
        results.append(result)
    
    return results