"""
Challenge 3 Deliverable: Data Visualization Tools
Built-in charting, geospatial mapping, and time-series analysis with platform integrations
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime, timezone
import math
import statistics

class ChartType(Enum):
    """Supported chart types"""
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    PIE = "pie"
    AREA = "area"
    BUBBLE = "bubble"
    CORRELATION_MATRIX = "correlation_matrix"
    TIME_SERIES = "time_series"

class MapType(Enum):
    """Supported map types"""
    SATELLITE = "satellite"
    TERRAIN = "terrain"
    STREET = "street"
    HYBRID = "hybrid"
    HEAT_MAP = "heat_map"
    CLUSTER_MAP = "cluster_map"

class VisualizationType(Enum):
    """Types of visualizations"""
    CHART = "chart"
    MAP = "map"
    TIME_SERIES = "time_series"
    STATISTICAL = "statistical"
    GEOSPATIAL = "geospatial"

@dataclass
class ChartConfiguration:
    """Configuration for chart visualization"""
    chart_id: str
    chart_type: ChartType
    title: str
    x_axis: Dict[str, Any]
    y_axis: Dict[str, Any]
    data_series: List[Dict[str, Any]]
    styling: Dict[str, Any]
    interactive_features: List[str]

@dataclass
class MapConfiguration:
    """Configuration for map visualization"""
    map_id: str
    map_type: MapType
    title: str
    center_coordinates: Tuple[float, float]
    zoom_level: int
    layers: List[Dict[str, Any]]
    controls: List[str]
    styling: Dict[str, Any]

@dataclass
class TimeSeriesConfiguration:
    """Configuration for time series analysis"""
    series_id: str
    title: str
    time_column: str
    value_columns: List[str]
    aggregation_period: str
    analysis_methods: List[str]
    forecasting: bool

class DataVisualizationTools:
    """Comprehensive data visualization toolkit"""

    def __init__(self):
        self.supported_integrations = {
            "power_bi": "Microsoft Power BI",
            "esri": "Esri ArcGIS",
            "plotly": "Plotly Dash",
            "d3": "D3.js",
            "leaflet": "Leaflet Maps",
            "mapbox": "Mapbox GL",
            "grafana": "Grafana Dashboards"
        }
        self.created_visualizations = {}

    def create_fire_detection_map(self, fire_data: List[Dict[str, Any]],
                                 config_overrides: Optional[Dict[str, Any]] = None) -> MapConfiguration:
        """Create interactive fire detection map"""

        # Default configuration
        default_config = {
            "map_type": MapType.SATELLITE,
            "title": "Real-time Fire Detection Map",
            "center_coordinates": (37.5, -119.5),  # California center
            "zoom_level": 7,
            "controls": ["zoom", "pan", "layers", "fullscreen", "measure"],
            "styling": {
                "fire_point_color": "#FF4444",
                "fire_point_size": "confidence_based",
                "cluster_colors": ["#FFFF00", "#FF8800", "#FF0000"],
                "heat_map_gradient": ["#FFFF00", "#FF8800", "#FF4444", "#AA0000"]
            }
        }

        # Apply overrides
        if config_overrides:
            default_config.update(config_overrides)

        # Create layers
        layers = [
            {
                "layer_id": "fire_detections",
                "type": "point",
                "data_source": "fire_data",
                "style": {
                    "marker_type": "circle",
                    "size_property": "brightness",
                    "color_property": "confidence",
                    "popup_template": "Fire Detection<br>Confidence: {confidence}%<br>Brightness: {brightness}K<br>Time: {acq_time}"
                }
            },
            {
                "layer_id": "fire_clusters",
                "type": "cluster",
                "data_source": "fire_data",
                "cluster_radius": 50,
                "style": {
                    "cluster_colors": default_config["styling"]["cluster_colors"]
                }
            },
            {
                "layer_id": "fire_heat_map",
                "type": "heatmap",
                "data_source": "fire_data",
                "intensity_property": "brightness",
                "style": {
                    "gradient": default_config["styling"]["heat_map_gradient"],
                    "radius": 20,
                    "opacity": 0.6
                }
            }
        ]

        map_config = MapConfiguration(
            map_id=f"fire_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            map_type=default_config["map_type"],
            title=default_config["title"],
            center_coordinates=default_config["center_coordinates"],
            zoom_level=default_config["zoom_level"],
            layers=layers,
            controls=default_config["controls"],
            styling=default_config["styling"]
        )

        self.created_visualizations[map_config.map_id] = map_config
        return map_config

    def create_weather_chart(self, weather_data: List[Dict[str, Any]],
                           chart_type: ChartType = ChartType.TIME_SERIES,
                           variables: List[str] = None) -> ChartConfiguration:
        """Create weather data visualization chart"""

        if variables is None:
            variables = ["temperature", "humidity", "wind_speed", "pressure"]

        # Create data series for each variable
        data_series = []
        for variable in variables:
            series_data = [
                {"x": record.get("timestamp"), "y": record.get(variable)}
                for record in weather_data
                if record.get(variable) is not None
            ]

            data_series.append({
                "name": variable.replace("_", " ").title(),
                "data": series_data,
                "type": "line",
                "color": self._get_variable_color(variable),
                "axis": "left" if variable in ["temperature", "humidity"] else "right"
            })

        chart_config = ChartConfiguration(
            chart_id=f"weather_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            chart_type=chart_type,
            title="Weather Conditions Analysis",
            x_axis={
                "type": "datetime",
                "title": "Time",
                "format": "%Y-%m-%d %H:%M"
            },
            y_axis={
                "left": {
                    "title": "Temperature (°C) / Humidity (%)",
                    "min": 0,
                    "max": 100
                },
                "right": {
                    "title": "Wind Speed (m/s) / Pressure (hPa)",
                    "min": 0
                }
            },
            data_series=data_series,
            styling={
                "grid": True,
                "legend": True,
                "tooltip": True,
                "zoom": True,
                "colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
            },
            interactive_features=["zoom", "pan", "hover", "legend_toggle", "export"]
        )

        self.created_visualizations[chart_config.chart_id] = chart_config
        return chart_config

    def create_correlation_matrix(self, data: List[Dict[str, Any]],
                                variables: List[str]) -> ChartConfiguration:
        """Create correlation matrix heatmap"""

        # Calculate correlation matrix
        correlation_matrix = self._calculate_correlation_matrix(data, variables)

        # Convert to heatmap data format
        heatmap_data = []
        for i, var1 in enumerate(variables):
            for j, var2 in enumerate(variables):
                heatmap_data.append({
                    "x": var1,
                    "y": var2,
                    "value": correlation_matrix[i][j]
                })

        chart_config = ChartConfiguration(
            chart_id=f"correlation_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            chart_type=ChartType.HEATMAP,
            title="Variable Correlation Matrix",
            x_axis={
                "type": "category",
                "categories": variables,
                "title": "Variables"
            },
            y_axis={
                "type": "category",
                "categories": variables,
                "title": "Variables"
            },
            data_series=[{
                "name": "Correlation",
                "data": heatmap_data,
                "colorScale": {
                    "min": -1,
                    "max": 1,
                    "colors": ["#0000FF", "#FFFFFF", "#FF0000"]
                }
            }],
            styling={
                "cell_labels": True,
                "colorbar": True,
                "symmetric": True
            },
            interactive_features=["hover", "export", "zoom"]
        )

        self.created_visualizations[chart_config.chart_id] = chart_config
        return chart_config

    def create_time_series_analysis(self, data: List[Dict[str, Any]],
                                   time_column: str, value_column: str,
                                   analysis_type: str = "trend") -> TimeSeriesConfiguration:
        """Create comprehensive time series analysis"""

        analysis_methods = []
        if analysis_type == "full":
            analysis_methods = ["trend", "seasonality", "autocorrelation", "forecast"]
        else:
            analysis_methods = [analysis_type]

        time_series_config = TimeSeriesConfiguration(
            series_id=f"timeseries_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=f"Time Series Analysis: {value_column.replace('_', ' ').title()}",
            time_column=time_column,
            value_columns=[value_column],
            aggregation_period="daily",
            analysis_methods=analysis_methods,
            forecasting="forecast" in analysis_methods
        )

        return time_series_config

    def create_geospatial_analysis(self, data: List[Dict[str, Any]],
                                 analysis_type: str = "density") -> MapConfiguration:
        """Create geospatial analysis visualization"""

        if analysis_type == "density":
            return self._create_density_map(data)
        elif analysis_type == "hotspot":
            return self._create_hotspot_map(data)
        elif analysis_type == "cluster":
            return self._create_cluster_map(data)
        else:
            return self._create_basic_point_map(data)

    def create_statistical_summary(self, data: List[Dict[str, Any]],
                                 numeric_columns: List[str]) -> Dict[str, Any]:
        """Create statistical summary visualization"""

        summary_stats = {}
        for column in numeric_columns:
            values = [record[column] for record in data if record.get(column) is not None]
            if values:
                summary_stats[column] = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                    "quartiles": {
                        "q1": self._percentile(values, 25),
                        "q3": self._percentile(values, 75)
                    }
                }

        return {
            "summary_id": f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": "Statistical Summary",
            "statistics": summary_stats,
            "visualization_type": "box_plot",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    def integrate_with_power_bi(self, visualization_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Power BI compatible configuration"""

        power_bi_config = {
            "version": "1.0",
            "type": "custom_visual",
            "data_roles": [
                {
                    "displayName": "Category",
                    "name": "category",
                    "kind": "Grouping"
                },
                {
                    "displayName": "Values",
                    "name": "values",
                    "kind": "Measure"
                }
            ],
            "dataViewMappings": [
                {
                    "categorical": {
                        "categories": {
                            "for": {"in": "category"}
                        },
                        "values": {
                            "for": {"in": "values"}
                        }
                    }
                }
            ],
            "objects": {
                "general": {
                    "displayName": "General",
                    "properties": {
                        "responsive": {"type": {"bool": True}},
                        "keepLayerOrder": {"type": {"bool": True}}
                    }
                }
            }
        }

        return power_bi_config

    def integrate_with_esri(self, map_config: MapConfiguration) -> Dict[str, Any]:
        """Generate Esri ArcGIS compatible configuration"""

        esri_config = {
            "version": "4.x",
            "map": {
                "basemap": self._convert_to_esri_basemap(map_config.map_type),
                "center": list(map_config.center_coordinates),
                "zoom": map_config.zoom_level
            },
            "layers": [],
            "widgets": [
                "legend",
                "layerlist",
                "basemapgallery",
                "search",
                "zoom"
            ]
        }

        # Convert layers to Esri format
        for layer in map_config.layers:
            esri_layer = {
                "type": self._convert_to_esri_layer_type(layer["type"]),
                "url": f"data_service/{layer['data_source']}",
                "renderer": self._create_esri_renderer(layer.get("style", {}))
            }
            esri_config["layers"].append(esri_layer)

        return esri_config

    def export_to_plotly(self, chart_config: ChartConfiguration) -> Dict[str, Any]:
        """Export chart configuration to Plotly format"""

        plotly_config = {
            "data": [],
            "layout": {
                "title": chart_config.title,
                "xaxis": {
                    "title": chart_config.x_axis.get("title", ""),
                    "type": chart_config.x_axis.get("type", "linear")
                },
                "yaxis": {
                    "title": chart_config.y_axis.get("title", ""),
                    "type": chart_config.y_axis.get("type", "linear")
                },
                "showlegend": chart_config.styling.get("legend", True),
                "hovermode": "closest"
            },
            "config": {
                "responsive": True,
                "displayModeBar": True,
                "modeBarButtonsToAdd": ["downloadSVG"]
            }
        }

        # Convert data series to Plotly format
        for series in chart_config.data_series:
            plotly_trace = {
                "name": series["name"],
                "type": self._convert_to_plotly_type(chart_config.chart_type),
                "x": [point["x"] for point in series["data"]],
                "y": [point["y"] for point in series["data"]],
                "line": {"color": series.get("color", "#1f77b4")}
            }
            plotly_config["data"].append(plotly_trace)

        return plotly_config

    def _calculate_correlation_matrix(self, data: List[Dict[str, Any]],
                                    variables: List[str]) -> List[List[float]]:
        """Calculate correlation matrix for given variables"""

        # Extract values for each variable
        variable_data = {}
        for var in variables:
            variable_data[var] = [record.get(var) for record in data if record.get(var) is not None]

        # Calculate correlations
        matrix = []
        for var1 in variables:
            row = []
            for var2 in variables:
                if var1 == var2:
                    correlation = 1.0
                else:
                    correlation = self._pearson_correlation(variable_data[var1], variable_data[var2])
                row.append(correlation)
            matrix.append(row)

        return matrix

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x) != len(y) or len(x) == 0:
            return 0.0

        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
        sum_sq_x = sum((x[i] - mean_x) ** 2 for i in range(len(x)))
        sum_sq_y = sum((y[i] - mean_y) ** 2 for i in range(len(y)))

        denominator = math.sqrt(sum_sq_x * sum_sq_y)

        return numerator / denominator if denominator != 0 else 0.0

    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)

        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    def _get_variable_color(self, variable: str) -> str:
        """Get color for weather variable"""
        color_map = {
            "temperature": "#ff7f0e",
            "humidity": "#2ca02c",
            "wind_speed": "#1f77b4",
            "pressure": "#d62728",
            "precipitation": "#9467bd"
        }
        return color_map.get(variable, "#17becf")

    def _create_density_map(self, data: List[Dict[str, Any]]) -> MapConfiguration:
        """Create density map visualization"""
        return MapConfiguration(
            map_id=f"density_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            map_type=MapType.HEAT_MAP,
            title="Data Density Analysis",
            center_coordinates=(37.5, -119.5),
            zoom_level=7,
            layers=[{
                "layer_id": "density_layer",
                "type": "heatmap",
                "data_source": "analysis_data",
                "style": {
                    "gradient": ["#0000FF", "#00FF00", "#FFFF00", "#FF0000"],
                    "radius": 15,
                    "opacity": 0.8
                }
            }],
            controls=["zoom", "pan", "layers"],
            styling={"theme": "dark"}
        )

    def _create_hotspot_map(self, data: List[Dict[str, Any]]) -> MapConfiguration:
        """Create hotspot analysis map"""
        return MapConfiguration(
            map_id=f"hotspot_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            map_type=MapType.SATELLITE,
            title="Hotspot Analysis",
            center_coordinates=(37.5, -119.5),
            zoom_level=7,
            layers=[{
                "layer_id": "hotspot_layer",
                "type": "hotspot",
                "data_source": "analysis_data",
                "analysis_method": "getis_ord_gi",
                "style": {
                    "hot_color": "#FF0000",
                    "cold_color": "#0000FF",
                    "confidence_intervals": [90, 95, 99]
                }
            }],
            controls=["zoom", "pan", "layers", "legend"],
            styling={"theme": "satellite"}
        )

    def _create_cluster_map(self, data: List[Dict[str, Any]]) -> MapConfiguration:
        """Create cluster analysis map"""
        return MapConfiguration(
            map_id=f"cluster_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            map_type=MapType.CLUSTER_MAP,
            title="Cluster Analysis",
            center_coordinates=(37.5, -119.5),
            zoom_level=7,
            layers=[{
                "layer_id": "cluster_layer",
                "type": "cluster",
                "data_source": "analysis_data",
                "cluster_method": "dbscan",
                "style": {
                    "cluster_colors": ["#FF0000", "#00FF00", "#0000FF", "#FFFF00"],
                    "noise_color": "#888888"
                }
            }],
            controls=["zoom", "pan", "layers", "legend"],
            styling={"theme": "terrain"}
        )

    def _create_basic_point_map(self, data: List[Dict[str, Any]]) -> MapConfiguration:
        """Create basic point map"""
        return MapConfiguration(
            map_id=f"point_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            map_type=MapType.STREET,
            title="Point Data Visualization",
            center_coordinates=(37.5, -119.5),
            zoom_level=7,
            layers=[{
                "layer_id": "point_layer",
                "type": "point",
                "data_source": "analysis_data",
                "style": {
                    "marker_color": "#FF4444",
                    "marker_size": 8,
                    "marker_opacity": 0.8
                }
            }],
            controls=["zoom", "pan"],
            styling={"theme": "light"}
        )

    def _convert_to_esri_basemap(self, map_type: MapType) -> str:
        """Convert internal map type to Esri basemap"""
        conversion_map = {
            MapType.SATELLITE: "satellite",
            MapType.TERRAIN: "terrain",
            MapType.STREET: "streets",
            MapType.HYBRID: "hybrid"
        }
        return conversion_map.get(map_type, "streets")

    def _convert_to_esri_layer_type(self, layer_type: str) -> str:
        """Convert internal layer type to Esri layer type"""
        conversion_map = {
            "point": "FeatureLayer",
            "heatmap": "HeatmapRenderer",
            "cluster": "ClusterRenderer"
        }
        return conversion_map.get(layer_type, "FeatureLayer")

    def _create_esri_renderer(self, style: Dict[str, Any]) -> Dict[str, Any]:
        """Create Esri renderer from style configuration"""
        return {
            "type": "simple",
            "symbol": {
                "type": "simple-marker",
                "color": style.get("marker_color", "#FF0000"),
                "size": style.get("marker_size", 8),
                "outline": {
                    "color": "#FFFFFF",
                    "width": 1
                }
            }
        }

    def _convert_to_plotly_type(self, chart_type: ChartType) -> str:
        """Convert internal chart type to Plotly type"""
        conversion_map = {
            ChartType.LINE: "scatter",
            ChartType.BAR: "bar",
            ChartType.SCATTER: "scatter",
            ChartType.HISTOGRAM: "histogram",
            ChartType.HEATMAP: "heatmap",
            ChartType.PIE: "pie",
            ChartType.AREA: "scatter"
        }
        return conversion_map.get(chart_type, "scatter")

    def get_visualization_summary(self) -> Dict[str, Any]:
        """Get summary of all created visualizations"""
        return {
            "total_visualizations": len(self.created_visualizations),
            "visualizations_by_type": {
                "charts": len([v for v in self.created_visualizations.values() if isinstance(v, ChartConfiguration)]),
                "maps": len([v for v in self.created_visualizations.values() if isinstance(v, MapConfiguration)])
            },
            "supported_integrations": list(self.supported_integrations.keys()),
            "created_visualizations": list(self.created_visualizations.keys())
        }

# Global visualization tools instance
visualization_tools = DataVisualizationTools()

def get_visualization_tools() -> DataVisualizationTools:
    """Get the global visualization tools instance"""
    return visualization_tools